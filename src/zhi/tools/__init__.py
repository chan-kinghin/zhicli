"""Tool registry for zhi."""

from __future__ import annotations

import logging
from typing import Any

from zhi.tools.base import BaseTool as BaseTool
from zhi.tools.base import Registrable

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing tool instances.

    Accepts any object satisfying the Registrable protocol —
    both BaseTool subclasses and SkillTool wrappers.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Registrable] = {}

    def register(self, tool: Registrable) -> None:
        """Register a tool. Raises ValueError on duplicate names."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Registrable | None:
        """Get a tool by name. Returns None if not found."""
        return self._tools.get(name)

    def list_tools(self) -> list[Registrable]:
        """List all registered tools."""
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def filter_by_names(self, names: list[str]) -> dict[str, Registrable]:
        """Filter tools by a list of names. Returns matching tools."""
        return {name: self._tools[name] for name in names if name in self._tools}

    def to_schemas(self) -> list[dict[str, Any]]:
        """Export all tools as OpenAI-format function schemas."""
        return [tool.to_function_schema() for tool in self._tools.values()]

    def to_schemas_filtered(self, names: list[str]) -> list[dict[str, Any]]:
        """Export schemas for a subset of tools by name."""
        return [
            self._tools[name].to_function_schema()
            for name in names
            if name in self._tools
        ]


def create_default_registry(
    *,
    output_dir: Any | None = None,
    ask_user_callback: Any | None = None,
) -> ToolRegistry:
    """Create a registry with all built-in tools.

    Note: Some tools require runtime dependencies (client, callbacks).
    This creates the file-based tools that don't need external deps.
    Tools requiring external deps (ocr, shell) must be registered separately.

    Args:
        output_dir: Optional output directory for FileWriteTool.
        ask_user_callback: Optional callback for AskUserTool.
    """
    from zhi.tools.ask_user import AskUserTool
    from zhi.tools.file_list import FileListTool
    from zhi.tools.file_read import FileReadTool
    from zhi.tools.file_write import FileWriteTool
    from zhi.tools.web_fetch import WebFetchTool

    registry = ToolRegistry()
    registry.register(FileReadTool())
    if output_dir is not None:
        from pathlib import Path

        registry.register(FileWriteTool(output_dir=Path(output_dir)))
    else:
        registry.register(FileWriteTool())
    registry.register(FileListTool())
    registry.register(WebFetchTool())
    registry.register(AskUserTool(callback=ask_user_callback))
    return registry


def register_skill_tools(
    registry: ToolRegistry,
    skills: dict[str, Any],
    client: Any,
    *,
    on_permission: Any | None = None,
    permission_mode_getter: Any | None = None,
    on_ask_user: Any | None = None,
    base_output_dir: Any | None = None,
) -> None:
    """Wrap each discovered SkillConfig as a SkillTool and register it.

    Skills become tools named ``skill_<name>`` in the registry,
    enabling the agent to call them during interactive chat.

    Args:
        registry: The tool registry to populate.
        skills: Dict mapping skill name to SkillConfig.
        client: The Zhipu API client (passed to nested agent loops).
        on_permission: Permission callback for risky tool checks in nested skills.
        permission_mode_getter: Callable returning current PermissionMode.
        on_ask_user: Callback for AskUserTool in nested skills.
        base_output_dir: Base output directory for skill-scoped file writes.
            Each skill will write to ``base_output_dir/<skill_name>/``.
    """
    from pathlib import Path

    from zhi.tools.skill_tool import SkillTool

    output_path = Path(base_output_dir) if base_output_dir is not None else None

    for _name, skill_config in skills.items():
        tool = SkillTool(
            skill=skill_config,
            client=client,
            registry=registry,
            on_permission=on_permission,
            permission_mode_getter=permission_mode_getter,
            on_ask_user=on_ask_user,
            base_output_dir=output_path,
        )
        try:
            registry.register(tool)
        except ValueError:
            logger.warning(
                "Skill tool '%s' collides with existing tool, skipping",
                tool.name,
            )
