"""File read tool for zhi."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from zhi.tools.base import BaseTool

_MAX_FILE_SIZE = 100 * 1024  # 100KB


class FileReadTool(BaseTool):
    """Read the contents of a text file."""

    name: ClassVar[str] = "file_read"
    description: ClassVar[str] = (
        "Read the contents of a text file. "
        "Only relative paths within the working directory are allowed. "
        "Maximum file size: 100KB (truncated with warning if larger)."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file to read.",
            },
        },
        "required": ["path"],
    }
    risky: ClassVar[bool] = False

    def __init__(self, working_dir: Path | None = None) -> None:
        self._working_dir = working_dir or Path.cwd()

    def execute(self, **kwargs: Any) -> str:
        path_str: str = kwargs.get("path", "")
        if not path_str:
            return "Error: 'path' parameter is required."

        file_path = Path(path_str)

        # Reject absolute paths
        if file_path.is_absolute():
            return "Error: Absolute paths are not allowed. Use a relative path."

        # Reject path traversal
        try:
            resolved = (self._working_dir / file_path).resolve()
            working_resolved = self._working_dir.resolve()
            if resolved != working_resolved and not resolved.is_relative_to(
                working_resolved
            ):
                return (
                    "Error: Path traversal is not allowed. "
                    "Stay within the working directory."
                )
        except (OSError, ValueError):
            return "Error: Invalid file path."

        # Check existence
        if not resolved.exists():
            return f"Error: File not found: {path_str}"

        if not resolved.is_file():
            return f"Error: Not a file: {path_str}"

        # Try to read the file
        try:
            # Check for binary content by reading a small sample
            with open(resolved, "rb") as f:
                sample = f.read(8192)
            if b"\x00" in sample:
                return f"Error: File appears to be binary: {path_str}"

            file_size = resolved.stat().st_size
            truncated = False

            # Read only what we need to avoid loading huge files into memory
            if file_size > _MAX_FILE_SIZE:
                with open(resolved, "rb") as f:
                    raw = f.read(_MAX_FILE_SIZE)
                try:
                    content = raw.decode("utf-8")
                except UnicodeDecodeError:
                    content = raw.decode("latin-1")
                truncated = True
            else:
                try:
                    content = resolved.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = resolved.read_text(encoding="latin-1")

            if truncated:
                return (
                    f"[truncated, showing first 100KB of "
                    f"{file_size / 1024:.1f}KB]\n{content}"
                )

            return content

        except PermissionError:
            return f"Error: Permission denied: {path_str}"
        except OSError as exc:
            return f"Error: Could not read file: {exc}"
