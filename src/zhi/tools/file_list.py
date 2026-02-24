"""File list tool for zhi."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, ClassVar

from zhi.tools.base import BaseTool


def _human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size string."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"


class FileListTool(BaseTool):
    """List directory contents with metadata."""

    name: ClassVar[str] = "file_list"
    description: ClassVar[str] = (
        "List files and directories with name, size, and modification date. "
        "Only relative paths within the working directory are allowed."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to list. Defaults to current directory.",
                "default": ".",
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum depth to recurse. Defaults to 2.",
                "default": 2,
            },
        },
    }
    risky: ClassVar[bool] = False

    def __init__(self, working_dir: Path | None = None) -> None:
        self._working_dir = working_dir or Path.cwd()

    def execute(self, **kwargs: Any) -> str:
        path_str: str = kwargs.get("path", ".")
        max_depth: int = kwargs.get("max_depth", 2)

        # Clamp depth
        max_depth = max(1, min(max_depth, 10))

        target = Path(path_str)

        # Reject absolute paths
        if target.is_absolute():
            return "Error: Absolute paths are not allowed. Use a relative path."

        # Reject traversal
        if ".." in target.parts:
            return "Error: Path traversal ('..') is not allowed."

        resolved = (self._working_dir / target).resolve()
        working_resolved = self._working_dir.resolve()

        # Verify within working dir
        if resolved != working_resolved and not resolved.is_relative_to(
            working_resolved
        ):
            return "Error: Path is outside the working directory."

        if not resolved.exists():
            return f"Error: Directory not found: {path_str}"

        if not resolved.is_dir():
            return f"Error: Not a directory: {path_str}"

        lines: list[str] = []
        self._list_dir(resolved, "", max_depth, 0, lines)

        if not lines:
            return f"Directory is empty: {path_str}"

        return "\n".join(lines)

    def _list_dir(
        self,
        dir_path: Path,
        prefix: str,
        max_depth: int,
        current_depth: int,
        lines: list[str],
    ) -> None:
        if current_depth >= max_depth:
            return

        try:
            entries = sorted(
                dir_path.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except PermissionError:
            lines.append(f"{prefix}[permission denied]")
            return

        for entry in entries:
            try:
                stat = entry.stat()
                size = _human_readable_size(stat.st_size) if entry.is_file() else "-"
                mtime = datetime.datetime.fromtimestamp(
                    stat.st_mtime, tz=datetime.timezone.utc
                ).strftime("%Y-%m-%d %H:%M")
                kind = "d" if entry.is_dir() else "f"
                lines.append(f"{prefix}[{kind}] {entry.name:<30} {size:>10}  {mtime}")
            except OSError:
                lines.append(f"{prefix}[?] {entry.name}")
                continue

            if entry.is_dir():
                self._list_dir(
                    entry,
                    prefix + "  ",
                    max_depth,
                    current_depth + 1,
                    lines,
                )
