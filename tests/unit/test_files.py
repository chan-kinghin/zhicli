"""Tests for zhi.files module — file path detection and extraction."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from zhi.files import extract_files, find_file_paths


class TestFindFilePaths:
    """Test file path detection in user input."""

    def test_single_absolute_path(self, tmp_path: Path) -> None:
        f = tmp_path / "test.xlsx"
        f.write_bytes(b"data")
        text = f"analyze {f}"
        paths = find_file_paths(text)
        assert paths == [f]

    def test_multiple_paths(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.xlsx"
        f2 = tmp_path / "b.pdf"
        f1.write_bytes(b"data")
        f2.write_bytes(b"data")
        text = f"compare {f1} and {f2}"
        paths = find_file_paths(text)
        assert set(paths) == {f1, f2}

    def test_nonexistent_path_skipped(self) -> None:
        text = "read /nonexistent/file.xlsx please"
        paths = find_file_paths(text)
        assert paths == []

    def test_slash_command_not_matched(self) -> None:
        text = "/help"
        paths = find_file_paths(text)
        assert paths == []

    def test_tilde_path(self, tmp_path: Path) -> None:
        f = tmp_path / "notes.md"
        f.write_text("hello")
        text = f"read {f} please"
        paths = find_file_paths(text)
        assert paths == [f]

    def test_path_with_escaped_spaces(self, tmp_path: Path) -> None:
        d = tmp_path / "my dir"
        d.mkdir()
        f = d / "file.xlsx"
        f.write_bytes(b"data")
        escaped = str(f).replace(" ", "\\ ")
        text = f"read {escaped}"
        paths = find_file_paths(text)
        assert paths == [f]

    def test_path_with_chinese_chars(self, tmp_path: Path) -> None:
        f = tmp_path / "价格表.xlsx"
        f.write_bytes(b"data")
        text = f"分析 {f}"
        paths = find_file_paths(text)
        assert paths == [f]

    def test_no_extension_not_matched(self, tmp_path: Path) -> None:
        d = tmp_path / "somedir"
        d.mkdir()
        text = f"look at {d}"
        paths = find_file_paths(text)
        assert paths == []

    def test_url_not_matched(self) -> None:
        text = "visit https://example.com/page.html"
        paths = find_file_paths(text)
        assert paths == []

    def test_is_file_oserror_skipped(self, tmp_path: Path) -> None:
        """Bug 7: OSError on is_file() should not crash find_file_paths."""
        f = tmp_path / "network.xlsx"
        f.write_bytes(b"data")
        text = f"read {f}"

        orig_is_file = Path.is_file

        def patched_is_file(self_path: Path) -> bool:
            if self_path.name == "network.xlsx":
                raise OSError("Network timeout")
            return orig_is_file(self_path)

        with patch.object(Path, "is_file", patched_is_file):
            paths = find_file_paths(text)

        assert paths == []  # Skipped gracefully, no crash


class TestExtractFiles:
    """Test full extraction pipeline."""

    def test_text_file_read_directly(self, tmp_path: Path) -> None:
        f = tmp_path / "notes.txt"
        f.write_text("hello world")
        text = f"summarize {f}"
        client = MagicMock()

        cleaned, attachments = extract_files(text, client)

        assert len(attachments) == 1
        assert attachments[0].content == "hello world"
        assert attachments[0].error is None
        assert attachments[0].filename == "notes.txt"
        assert "[File 1: notes.txt]" in cleaned
        client.file_extract.assert_not_called()

    def test_xlsx_uses_file_extract(self, tmp_path: Path) -> None:
        f = tmp_path / "prices.xlsx"
        f.write_bytes(b"PK data")
        client = MagicMock()
        client.file_extract.return_value = "Sheet1 content"

        text = f"analyze {f}"
        _cleaned, attachments = extract_files(text, client)

        assert len(attachments) == 1
        assert attachments[0].content == "Sheet1 content"
        client.file_extract.assert_called_once_with(f.resolve())

    def test_multiple_files(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.xlsx"
        f1.write_text("text content")
        f2.write_bytes(b"PK data")
        client = MagicMock()
        client.file_extract.return_value = "excel content"

        text = f"compare {f1} and {f2}"
        cleaned, attachments = extract_files(text, client)

        assert len(attachments) == 2
        assert "[File 1:" in cleaned
        assert "[File 2:" in cleaned

    def test_nonexistent_file_left_in_text(self) -> None:
        client = MagicMock()
        text = "read /nonexistent/file.xlsx"
        cleaned, attachments = extract_files(text, client)

        assert attachments == []
        assert cleaned == text  # unchanged

    def test_extraction_error_captured(self, tmp_path: Path) -> None:
        f = tmp_path / "broken.pdf"
        f.write_bytes(b"data")
        client = MagicMock()
        client.file_extract.side_effect = Exception("API timeout")

        text = f"read {f}"
        _cleaned, attachments = extract_files(text, client)

        assert len(attachments) == 1
        assert attachments[0].error is not None
        assert "API timeout" in attachments[0].error

    def test_no_files_returns_unchanged(self) -> None:
        client = MagicMock()
        text = "just a normal message"
        cleaned, attachments = extract_files(text, client)

        assert cleaned == text
        assert attachments == []

    def test_text_around_paths_preserved(self, tmp_path: Path) -> None:
        f = tmp_path / "data.csv"
        f.write_text("a,b,c")
        client = MagicMock()

        text = f"please analyze {f} and tell me the stats"
        cleaned, _attachments = extract_files(text, client)

        assert "please analyze" in cleaned
        assert "and tell me the stats" in cleaned
        assert str(f) not in cleaned
