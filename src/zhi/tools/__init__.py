"""Tool registry for zhi."""

from __future__ import annotations

from typing import Any

from zhi.tools.base import BaseTool


class ToolRegistry:
    """Registry for managing tool instances."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool. Raises ValueError on duplicate names."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name. Returns None if not found."""
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """List all registered tools."""
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def filter_by_names(self, names: list[str]) -> dict[str, BaseTool]:
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


def create_default_registry() -> ToolRegistry:
    """Create a registry with all built-in tools.

    Note: Some tools require runtime dependencies (client, callbacks).
    This creates the file-based tools that don't need external deps.
    Tools requiring external deps (ocr, shell) must be registered separately.
    """
    from zhi.tools.file_list import FileListTool
    from zhi.tools.file_read import FileReadTool
    from zhi.tools.file_write import FileWriteTool
    from zhi.tools.web_fetch import WebFetchTool

    registry = ToolRegistry()
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(FileListTool())
    registry.register(WebFetchTool())
    return registry
