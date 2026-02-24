"""Tests for file_read tool."""

from __future__ import annotations

from pathlib import Path

from zhi.tools.file_read import FileReadTool


class TestFileReadText:
    def test_read_text_file(self, tmp_path: Path) -> None:
        f = tmp_path / "hello.txt"
        f.write_text("Hello, world!", encoding="utf-8")
        tool = FileReadTool(working_dir=tmp_path)
        result = tool.execute(path="hello.txt")
        assert result == "Hello, world!"

    def test_read_multiline_file(self, tmp_path: Path) -> None:
        f = tmp_path / "multi.txt"
        f.write_text("line1\nline2\nline3", encoding="utf-8")
        tool = FileReadTool(working_dir=tmp_path)
        result = tool.execute(path="multi.txt")
        assert "line1" in result
        assert "line3" in result

    def test_read_file_in_subdirectory(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        f = sub / "nested.txt"
        f.write_text("nested content", encoding="utf-8")
        tool = FileReadTool(working_dir=tmp_path)
        result = tool.execute(path="sub/nested.txt")
        assert result == "nested content"


class TestFileReadNonexistent:
    def test_file_not_found(self, tmp_path: Path) -> None:
        tool = FileReadTool(working_dir=tmp_path)
        result = tool.execute(path="nope.txt")
        assert "Error" in result
        assert "not found" in result

    def test_empty_path(self, tmp_path: Path) -> None:
        tool = FileReadTool(working_dir=tmp_path)
        result = tool.execute(path="")
        assert "Error" in result


class TestFileReadBinary:
    def test_rejects_binary_file(self, tmp_path: Path) -> None:
        f = tmp_path / "binary.bin"
        f.write_bytes(b"\x00\x01\x02\x03")
        tool = FileReadTool(working_dir=tmp_path)
        result = tool.execute(path="binary.bin")
        assert "Error" in result
        assert "binary" in result.lower()


class TestFileReadLarge:
    def test_truncates_large_file(self, tmp_path: Path) -> None:
        f = tmp_path / "large.txt"
        # Write 200KB of text
        content = "x" * (200 * 1024)
        f.write_text(content, encoding="utf-8")
        tool = FileReadTool(working_dir=tmp_path)
        result = tool.execute(path="large.txt")
        assert "truncated" in result
        assert "100KB" in result


class TestFileReadEncoding:
    def test_read_utf8(self, tmp_path: Path) -> None:
        f = tmp_path / "utf8.txt"
        f.write_text("Hello, world!", encoding="utf-8")
        tool = FileReadTool(working_dir=tmp_path)
        result = tool.execute(path="utf8.txt")
        assert result == "Hello, world!"

    def test_read_latin1_fallback(self, tmp_path: Path) -> None:
        f = tmp_path / "latin.txt"
        # Write bytes that are valid latin-1 but not valid UTF-8
        f.write_bytes(b"caf\xe9")
        tool = FileReadTool(working_dir=tmp_path)
        result = tool.execute(path="latin.txt")
        assert "caf" in result


class TestFileReadSecurity:
    def test_rejects_absolute_path(self, tmp_path: Path) -> None:
        tool = FileReadTool(working_dir=tmp_path)
        result = tool.execute(path="/etc/passwd")
        assert "Error" in result
        assert "Absolute" in result

    def test_rejects_path_traversal(self, tmp_path: Path) -> None:
        tool = FileReadTool(working_dir=tmp_path)
        result = tool.execute(path="../../../etc/passwd")
        assert "Error" in result
        assert "traversal" in result.lower()

    def test_rejects_not_a_file(self, tmp_path: Path) -> None:
        sub = tmp_path / "subdir"
        sub.mkdir()
        tool = FileReadTool(working_dir=tmp_path)
        result = tool.execute(path="subdir")
        assert "Error" in result
        assert "Not a file" in result


class TestFileReadCrossPlatform:
    def test_path_validation_cross_platform(self, tmp_path: Path) -> None:
        """Ensure path check works on all platforms (no hard-coded '/')."""
        (tmp_path / "data.txt").write_text("content", encoding="utf-8")
        tool = FileReadTool(working_dir=tmp_path)
        result = tool.execute(path="data.txt")
        assert result == "content"
        assert "Error" not in result
