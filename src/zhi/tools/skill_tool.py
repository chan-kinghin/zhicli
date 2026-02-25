"""SkillTool — wraps a SkillConfig so the agent can call it as a tool."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from zhi.agent import Context, PermissionMode, Role, ToolLike
from zhi.agent import run as agent_run
from zhi.i18n import prepend_preamble
from zhi.models import get_model

if TYPE_CHECKING:
    from zhi.agent import ClientLike
    from zhi.skills.loader import SkillConfig
    from zhi.tools import ToolRegistry

logger = logging.getLogger(__name__)

_MAX_DEPTH = 3
_SKILL_TOOL_PREFIX = "skill_"
# Default sliding-window size for nested skill contexts.
# Keeps system prompt + user message + last 40 messages (~10 turn pairs).
_DEFAULT_SKILL_CONTEXT_MESSAGES = 40


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
        permission_mode_getter: Callable[[], PermissionMode] | None = None,
        on_permission: Callable[[ToolLike, dict[str, Any]], bool] | None = None,
        on_ask_user: Callable[[str, list[str] | None], str] | None = None,
        base_output_dir: Path | None = None,
    ) -> None:
        self._skill = skill
        self._client = client
        self._registry = registry
        self._call_stack = call_stack
        self._depth = depth
        self._permission_mode = permission_mode
        self._permission_mode_getter = permission_mode_getter
        self._on_permission = on_permission
        self._on_ask_user = on_ask_user
        self._base_output_dir = base_output_dir

    def _get_permission_mode(self) -> PermissionMode:
        """Read permission_mode from getter (live) or fall back to stored value."""
        if self._permission_mode_getter is not None:
            return self._permission_mode_getter()
        return self._permission_mode

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
                logger.warning(
                    "Skill '%s' has an input arg with no name — "
                    "it will be omitted from the schema",
                    self._skill.name,
                )
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

    # -- File helpers ----------------------------------------------------------

    def _read_file(self, path_str: str) -> Any:
        """Read a file for injection into the skill context.

        Uses the same extraction logic as chat file attachments — text files
        are read directly, xlsx/pdf/images go through the Zhipu API.
        """
        from zhi.files import FileAttachment, _extract_one

        try:
            path = Path(path_str).expanduser()
            if not path.is_absolute():
                path = Path.cwd() / path
            path = path.resolve()
        except (OSError, ValueError) as exc:
            return FileAttachment(
                path=Path(path_str),
                filename=Path(path_str).name,
                content="",
                error=f"Invalid path: {exc}",
            )

        return _extract_one(path, self._client)

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

        # Build user message from kwargs — inject file content for file-type args
        # (like Claude Code: read files at the infrastructure level, don't rely
        # on the LLM to forward paths correctly)
        user_input = kwargs.get("input", "")

        file_args = {
            arg["name"]: arg
            for arg in self._skill.input_args
            if arg.get("name") and arg.get("type") == "file"
        }

        # Fail fast: reject empty required file args before making API calls
        for arg_name, arg_def in file_args.items():
            value = kwargs.get(arg_name, "")
            if arg_def.get("required") and not value:
                return (
                    f"Error: Required file argument '{arg_name}' is empty. "
                    f"Please provide the full file path."
                )

        file_sections: list[str] = []
        non_file_extras: dict[str, Any] = {}

        for k, v in kwargs.items():
            if k == "input":
                continue
            if k in file_args:
                if v:  # Non-empty file path — read and inject content
                    att = self._read_file(str(v))
                    if att.error:
                        file_sections.append(
                            f"--- File ({k}): {att.filename} ---\n[Error: {att.error}]"
                        )
                    else:
                        file_sections.append(
                            f"--- File ({k}): {att.filename} ---\n{att.content}"
                        )
                # Skip empty optional file args — don't inject noise
            else:
                non_file_extras[k] = v

        if file_sections:
            user_input += "\n\n" + "\n\n".join(file_sections)
        if non_file_extras:
            user_input += f"\n\nAdditional arguments: {non_file_extras}"

        # Early return: disabled model invocation returns instructions directly
        if self._skill.disable_model_invocation:
            parts = []
            if self._skill.system_prompt:
                parts.append(self._skill.system_prompt)
            if user_input.strip():
                parts.append(user_input)
            return "\n\n".join(parts)

        # Read current permission mode (live, not frozen)
        current_permission_mode = self._get_permission_mode()

        # Build inner tool set from the skill's tool list
        inner_tools: dict[str, Any] = {}
        inner_schemas: list[dict[str, Any]] = []

        new_call_stack = self._call_stack | {skill_name}
        new_depth = self._depth + 1

        for tool_name in self._skill.tools:
            # Handle ask_user specially — create with current callback
            if tool_name == "ask_user":
                from zhi.tools.ask_user import AskUserTool

                ask_tool = AskUserTool(callback=self._on_ask_user)
                inner_tools["ask_user"] = ask_tool
                inner_schemas.append(ask_tool.to_function_schema())
                continue

            # Intercept file_write — create skill-scoped FileWriteTool
            if tool_name == "file_write" and self._base_output_dir is not None:
                from zhi.tools.file_write import FileWriteTool

                scoped_dir = self._base_output_dir / skill_name
                scoped_fw = FileWriteTool(output_dir=scoped_dir)
                inner_tools["file_write"] = scoped_fw
                inner_schemas.append(scoped_fw.to_function_schema())
                continue

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
                # Re-wrap with updated call stack, depth, and permission
                child = SkillTool(
                    skill=existing._skill,
                    client=self._client,
                    registry=self._registry,
                    call_stack=new_call_stack,
                    depth=new_depth,
                    permission_mode=current_permission_mode,
                    permission_mode_getter=self._permission_mode_getter,
                    on_permission=self._on_permission,
                    on_ask_user=self._on_ask_user,
                    base_output_dir=self._base_output_dir,
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

        conversation: list[dict[str, Any]] = []
        if self._skill.system_prompt:
            conversation.append(
                {
                    "role": Role.SYSTEM.value,
                    "content": prepend_preamble(
                        self._skill.system_prompt,
                        has_ask_user="ask_user" in self._skill.tools,
                    ),
                }
            )
        conversation.append({"role": Role.USER.value, "content": user_input})

        # Enable thinking for models that support it
        model_info = get_model(self._skill.model)
        thinking = model_info.supports_thinking if model_info else False

        context = Context(
            config=None,
            client=self._client,
            model=self._skill.model,
            tools=inner_tools,
            tool_schemas=inner_schemas,
            permission_mode=current_permission_mode,
            conversation=conversation,
            max_turns=self._skill.max_turns,
            thinking_enabled=thinking,
            streaming=False,  # Nested skills use buffered mode
            max_context_messages=_DEFAULT_SKILL_CONTEXT_MESSAGES,
            on_permission=self._on_permission,
            on_ask_user=self._on_ask_user,
        )

        try:
            result = agent_run(context)
        except Exception as e:
            logger.exception("Skill '%s' execution failed", skill_name)
            return f"Error running skill '{skill_name}': {e}"

        if result is None:
            return f"Skill '{skill_name}' reached max turns without a final response."

        return result
