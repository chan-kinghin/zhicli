"""OCR tool for zhi."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Protocol

from zhi.tools.base import BaseTool

_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
_SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp"}


class OcrClient(Protocol):
    """Protocol for OCR client dependency."""

    def ocr(self, file_path: Path) -> str: ...


class OcrTool(BaseTool):
    """Extract text from images and PDFs via OCR."""

    name: ClassVar[str] = "ocr"
    description: ClassVar[str] = (
        "Extract text from images and PDFs using OCR. "
        "Supported formats: PDF, PNG, JPG, JPEG, GIF, WEBP. "
        "Maximum file size: 20MB."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the image or PDF file to OCR.",
            },
        },
        "required": ["path"],
    }
    risky: ClassVar[bool] = False

    def __init__(self, client: OcrClient, working_dir: Path | None = None) -> None:
        self._client = client
        self._working_dir = working_dir or Path.cwd()

    def execute(self, **kwargs: Any) -> str:
        path_str: str = kwargs.get("path", "")
        if not path_str:
            return "Error: 'path' parameter is required."

        file_path = Path(path_str)

        # Allow absolute paths for OCR (files might come from user input)
        if file_path.is_absolute():
            resolved = file_path.resolve()
        else:
            resolved = (self._working_dir / file_path).resolve()

        if not resolved.exists():
            return f"Error: File not found: {path_str}"

        if not resolved.is_file():
            return f"Error: Not a file: {path_str}"

        # Check extension
        ext = resolved.suffix.lower()
        if ext not in _SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(_SUPPORTED_EXTENSIONS))
            return (
                f"Error: Unsupported file format '{ext}'. "
                f"Supported formats: {supported}"
            )

        # Check file size
        file_size = resolved.stat().st_size
        if file_size > _MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            return f"Error: File too large for OCR ({size_mb:.1f}MB). Maximum: 20MB."

        # Call OCR client
        try:
            result = self._client.ocr(resolved)
        except Exception as exc:
            return f"Error: OCR failed: {exc}"

        if not result or not result.strip():
            return "OCR completed but no text was extracted from the file."

        # Cap output at 50KB
        if len(result) > 50 * 1024:
            result = result[: 50 * 1024] + "\n[truncated, showing first 50KB]"

        return result
