"""Tests for OCR tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from zhi.tools.ocr import OcrTool


class MockOcrClient:
    """Mock OCR client for testing."""

    def __init__(
        self,
        result: str = "Extracted text",
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.last_path: Path | None = None

    def ocr(self, file_path: Path) -> str:
        self.last_path = file_path
        if self.error:
            raise self.error
        return self.result


class TestOcrPdf:
    def test_ocr_pdf_success(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake content")
        client = MockOcrClient(result="Extracted from PDF")
        tool = OcrTool(client=client, working_dir=tmp_path)
        result = tool.execute(path="doc.pdf")
        assert result == "Extracted from PDF"
        assert client.last_path == pdf.resolve()


class TestOcrImage:
    def test_ocr_png(self, tmp_path: Path) -> None:
        img = tmp_path / "photo.png"
        img.write_bytes(b"\x89PNG fake image")
        client = MockOcrClient(result="Text in image")
        tool = OcrTool(client=client, working_dir=tmp_path)
        result = tool.execute(path="photo.png")
        assert result == "Text in image"

    def test_ocr_jpg(self, tmp_path: Path) -> None:
        img = tmp_path / "photo.jpg"
        img.write_bytes(b"\xff\xd8\xff fake jpg")
        client = MockOcrClient(result="JPG text")
        tool = OcrTool(client=client, working_dir=tmp_path)
        result = tool.execute(path="photo.jpg")
        assert result == "JPG text"


class TestOcrUnsupportedFormat:
    def test_rejects_txt(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("text", encoding="utf-8")
        client = MockOcrClient()
        tool = OcrTool(client=client, working_dir=tmp_path)
        result = tool.execute(path="file.txt")
        assert "Error" in result
        assert "Unsupported" in result

    def test_rejects_xlsx(self, tmp_path: Path) -> None:
        f = tmp_path / "file.xlsx"
        f.write_bytes(b"PK fake xlsx")
        client = MockOcrClient()
        tool = OcrTool(client=client, working_dir=tmp_path)
        result = tool.execute(path="file.xlsx")
        assert "Error" in result
        assert "Unsupported" in result


class TestOcrApiFailure:
    def test_ocr_api_error(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4 content")
        client = MockOcrClient(error=RuntimeError("API connection failed"))
        tool = OcrTool(client=client, working_dir=tmp_path)
        result = tool.execute(path="doc.pdf")
        assert "Error" in result
        assert "OCR failed" in result


class TestOcrEmptyResult:
    def test_ocr_empty_text(self, tmp_path: Path) -> None:
        pdf = tmp_path / "blank.pdf"
        pdf.write_bytes(b"%PDF-1.4 blank")
        client = MockOcrClient(result="")
        tool = OcrTool(client=client, working_dir=tmp_path)
        result = tool.execute(path="blank.pdf")
        assert "no text was extracted" in result.lower()


class TestOcrFileSize:
    def test_rejects_oversized_file(self, tmp_path: Path) -> None:
        huge = tmp_path / "huge.pdf"
        # Write just enough metadata to look valid, then check size via stat
        huge.write_bytes(b"%PDF-1.4 " + b"x" * 100)
        # Monkey-patch stat to report large size
        real_stat = huge.stat

        class FakeStat:
            def __init__(self) -> None:
                self._real = real_stat()

            def __getattr__(self, name: str) -> Any:
                return getattr(self._real, name)

            @property
            def st_size(self) -> int:
                return 25 * 1024 * 1024  # 25MB

        import unittest.mock

        client = MockOcrClient()
        tool = OcrTool(client=client, working_dir=tmp_path)
        with unittest.mock.patch.object(Path, "stat", return_value=FakeStat()):
            result = tool.execute(path="huge.pdf")
        assert "Error" in result
        assert "too large" in result.lower()


class TestOcrMissingFile:
    def test_file_not_found(self, tmp_path: Path) -> None:
        client = MockOcrClient()
        tool = OcrTool(client=client, working_dir=tmp_path)
        result = tool.execute(path="nonexistent.pdf")
        assert "Error" in result
        assert "not found" in result.lower()

    def test_empty_path(self, tmp_path: Path) -> None:
        client = MockOcrClient()
        tool = OcrTool(client=client, working_dir=tmp_path)
        result = tool.execute(path="")
        assert "Error" in result


class TestOcrOSError:
    """Bug 16: OSError on path operations should be handled gracefully."""

    def test_oserror_on_resolve(self, tmp_path: Path) -> None:
        """OSError during path resolution is caught."""
        client = MockOcrClient()
        tool = OcrTool(client=client, working_dir=tmp_path)

        orig_resolve = Path.resolve

        def patched_resolve(self_path: Path, *a: Any, **kw: Any) -> Path:
            if "network_mount" in str(self_path):
                raise OSError("Network timeout")
            return orig_resolve(self_path, *a, **kw)

        with patch.object(Path, "resolve", patched_resolve):
            result = tool.execute(path="network_mount/doc.pdf")

        assert "Error" in result
        assert "Cannot access" in result

    def test_oserror_on_exists(self, tmp_path: Path) -> None:
        """OSError during exists() is caught by the path access block."""
        client = MockOcrClient()
        tool = OcrTool(client=client, working_dir=tmp_path)

        orig_exists = Path.exists

        def patched_exists(self_path: Path, *a: Any, **kw: Any) -> bool:
            if self_path.name == "doc.pdf":
                raise OSError("I/O error")
            return orig_exists(self_path, *a, **kw)

        with patch.object(Path, "exists", patched_exists):
            result = tool.execute(path="doc.pdf")

        assert "Error" in result
        assert "Cannot access path" in result
