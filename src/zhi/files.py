"""File path detection and content extraction for chat input.

Detects absolute file paths in user messages, extracts their content,
and builds enriched messages for the LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Matches absolute paths (/...) or tilde paths (~/ ...) that end with a file extension.
# Handles backslash-escaped spaces (e.g., /path/to/file\ name.xlsx).
# Requires a `/` separator to avoid matching bare /word patterns.
_FILE_PATH_RE = re.compile(
    r"(?<!\w)"  # not preceded by a word char (avoids matching URLs like https://)
    r"(~?/(?:[^\s\\]|\\.)*\.\w{1,5})"  # path with extension
    r"(?=\s|$)"  # followed by whitespace or end
)


def find_file_paths(text: str) -> list[Path]:
    """Detect file paths in text that exist on disk.

    Returns a list of resolved Path objects for files that actually exist.
    Skips paths that look like slash commands (no directory separator after initial /).
    """
    paths: list[Path] = []
    seen: set[Path] = set()

    for match in _FILE_PATH_RE.finditer(text):
        raw = match.group(1)

        # Unescape backslash-escaped spaces
        cleaned = raw.replace("\\ ", " ")

        # Expand ~ to home directory
        if cleaned.startswith("~"):
            cleaned = str(Path.home()) + cleaned[1:]

        candidate = Path(cleaned)

        try:
            resolved = candidate.resolve()
            is_file = resolved.is_file()
        except (OSError, ValueError):
            continue

        if is_file and resolved not in seen:
            paths.append(resolved)
            seen.add(resolved)

    return paths


# Text-readable extensions that can be read directly (no API needed)
_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".log",
    ".py",
    ".js",
    ".ts",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".sh",
    ".bat",
}

# Extensions requiring Zhipu file-extract API
_EXTRACT_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".xls",
    ".xlsx",
    ".docx",
    ".doc",
    ".pptx",
}

_MAX_TEXT_SIZE = 50 * 1024  # 50KB per file


@dataclass
class FileAttachment:
    """A file detected in user input with its extracted content."""

    path: Path
    filename: str
    content: str
    error: str | None = None


def extract_files(
    text: str,
    client: Any,
) -> tuple[str, list[FileAttachment]]:
    """Detect file paths in text, extract content, and clean the text.

    Returns (cleaned_text, attachments) where cleaned_text has file paths
    replaced with [File N: filename] placeholders.
    """
    paths = find_file_paths(text)
    if not paths:
        return text, []

    attachments: list[FileAttachment] = []
    cleaned = text

    for i, path in enumerate(paths, 1):
        filename = path.name
        att = _extract_one(path, client)
        attachments.append(att)

        # Replace the path in text with a placeholder
        placeholder = f"[File {i}: {filename}]"
        # Replace escaped-space version first, then plain
        escaped = str(path).replace(" ", "\\ ")
        if escaped in cleaned:
            cleaned = cleaned.replace(escaped, placeholder, 1)
        elif str(path) in cleaned:
            cleaned = cleaned.replace(str(path), placeholder, 1)

    return cleaned, attachments


def _extract_one(path: Path, client: Any) -> FileAttachment:
    """Extract content from a single file."""
    filename = path.name
    ext = path.suffix.lower()

    try:
        if ext in _TEXT_EXTENSIONS:
            content = _read_text_file(path)
        elif ext in _EXTRACT_EXTENSIONS:
            content = client.file_extract(path)
        else:
            return FileAttachment(
                path=path,
                filename=filename,
                content="",
                error=f"Unsupported file type: {ext}",
            )

        # Truncate large content
        if len(content) > _MAX_TEXT_SIZE:
            content = (
                content[:_MAX_TEXT_SIZE]
                + f"\n[truncated, showing first 50KB of {len(content)} chars]"
            )

        return FileAttachment(path=path, filename=filename, content=content)

    except Exception as exc:
        return FileAttachment(
            path=path,
            filename=filename,
            content="",
            error=str(exc),
        )


def _read_text_file(path: Path) -> str:
    """Read a text file, handling encoding gracefully."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")
