"""SkillTool — wraps a SkillConfig so the agent can call it as a tool."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from zhi.agent import Context, PermissionMode, Role
from zhi.agent import run as agent_run
from zhi.i18n import prepend_preamble

if TYPE_CHECKING:
    from zhi.agent import ClientLike
    from zhi.skills.loader import SkillConfig
    from zhi.tools import ToolRegistry

logger = logging.getLogger(__name__)

_MAX_DEPTH = 3
_SKILL_TOOL_PREFIX = "skill_"


class SkillTool:
    """Wraps a SkillConfig into a callable tool for the agent loop.

    Unlike BaseTool (which uses ClassVar), SkillTool uses instance attributes
    so that each discovered skill gets its own name, description, and parameters.

    The tool satisfies the Registrable protocol defined in tools/base.py.
    """

    def __init__(
        self,
        skill: SkillConfig,
        client: ClientLike,
        registry: ToolRegistry,
        *,
        call_stack: frozenset[str] = frozenset(),
        depth: int = 0,
        permission_mode: PermissionMode = PermissionMode.APPROVE,
    ) -> None:
        self._skill = skill
        self._client = client
        self._registry = registry
        self._call_stack = call_stack
        self._depth = depth
        self._permission_mode = permission_mode

    # -- Registrable protocol --------------------------------------------------

    @property
    def name(self) -> str:
        return f"{_SKILL_TOOL_PREFIX}{self._skill.name}"

    @property
    def risky(self) -> bool:
        return False

    @property
    def description(self) -> str:
        return self._skill.description

    # -- Schema ----------------------------------------------------------------

    def to_function_schema(self) -> dict[str, Any]:
        """Generate OpenAI-compatible function schema."""
        properties: dict[str, Any] = {
            "input": {
                "type": "string",
                "description": "Instructions or query for the skill",
            },
        }
        required = ["input"]

        for arg in self._skill.input_args:
            arg_name = arg.get("name", "")
            if not arg_name:
                continue
            properties[arg_name] = {
                "type": arg.get("type", "string"),
                "description": arg.get("description", ""),
            }
            if arg.get("required", False):
                required.append(arg_name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self._skill.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    # -- Execution -------------------------------------------------------------

    def execute(self, **kwargs: Any) -> str:
        """Run the skill as a nested agent loop.

        Recursion prevention:
        1. Cycle detection — the skill's name must not appear in _call_stack.
        2. Depth limit — _depth must be < _MAX_DEPTH.
        3. max_turns — caps work per nesting level.
        """
        skill_name = self._skill.name

        # Guard: cycle detection
        if skill_name in self._call_stack:
            chain = sorted(self._call_stack)
            msg = f"Recursion blocked: '{skill_name}' already in call chain {chain}"
            logger.warning(msg)
            return f"Error: {msg}"

        # Guard: depth limit
        if self._depth >= _MAX_DEPTH:
            msg = f"Recursion blocked: max depth ({_MAX_DEPTH}) reached"
            logger.warning(msg)
            return f"Error: {msg}"

        # Build inner tool set from the skill's tool list
        inner_tools: dict[str, Any] = {}
        inner_schemas: list[dict[str, Any]] = []

        new_call_stack = self._call_stack | {skill_name}
        new_depth = self._depth + 1

        for tool_name in self._skill.tools:
            # Check if it's a skill tool reference (with or without prefix)
            resolved_name = tool_name
            if not tool_name.startswith(_SKILL_TOOL_PREFIX):
                # Try as a base tool first
                base_tool = self._registry.get(tool_name)
                if base_tool is not None:
                    inner_tools[tool_name] = base_tool
                    inner_schemas.append(base_tool.to_function_schema())
                    continue
                # Try with skill_ prefix
                resolved_name = f"{_SKILL_TOOL_PREFIX}{tool_name}"

            existing = self._registry.get(resolved_name)
            if existing is not None and isinstance(existing, SkillTool):
                # Re-wrap with updated call stack, depth, and permission mode
                child = SkillTool(
                    skill=existing._skill,
                    client=self._client,
                    registry=self._registry,
                    call_stack=new_call_stack,
                    depth=new_depth,
                    permission_mode=self._permission_mode,
                )
                inner_tools[child.name] = child
                inner_schemas.append(child.to_function_schema())
            elif existing is not None:
                inner_tools[resolved_name] = existing
                inner_schemas.append(existing.to_function_schema())
            else:
                logger.warning(
                    "Skill '%s' references unknown tool '%s'",
                    skill_name,
                    tool_name,
                )

        # Build user message from kwargs
        user_input = kwargs.get("input", "")
        extra_args = {k: v for k, v in kwargs.items() if k != "input"}
        if extra_args:
            user_input += f"\n\nAdditional arguments: {extra_args}"

        conversation: list[dict[str, Any]] = []
        if self._skill.system_prompt:
            conversation.append(
                {
                    "role": Role.SYSTEM.value,
                    "content": prepend_preamble(self._skill.system_prompt),
                }
            )
        conversation.append({"role": Role.USER.value, "content": user_input})

        context = Context(
            config=None,
            client=self._client,
            model=self._skill.model,
            tools=inner_tools,
            tool_schemas=inner_schemas,
            permission_mode=self._permission_mode,
            conversation=conversation,
            max_turns=self._skill.max_turns,
            thinking_enabled=False,
        )

        try:
            result = agent_run(context)
        except Exception as e:
            logger.exception("Skill '%s' execution failed", skill_name)
            return f"Error running skill '{skill_name}': {e}"

        if result is None:
            return f"Skill '{skill_name}' reached max turns without a final response."

        return result
