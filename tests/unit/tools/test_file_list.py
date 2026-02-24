"""Tests for file_list tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from zhi.tools.file_list import _SKIP_DIRS, FileListTool


class TestFileListDirectory:
    def test_list_directory(self, tmp_path: Path) -> None:
        (tmp_path / "file1.txt").write_text("hello", encoding="utf-8")
        (tmp_path / "file2.txt").write_text("world", encoding="utf-8")
        tool = FileListTool(working_dir=tmp_path)
        result = tool.execute(path=".")
        assert "file1.txt" in result
        assert "file2.txt" in result

    def test_list_shows_type_indicators(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("data", encoding="utf-8")
        sub = tmp_path / "subdir"
        sub.mkdir()
        tool = FileListTool(working_dir=tmp_path)
        result = tool.execute(path=".")
        assert "[f]" in result
        assert "[d]" in result


class TestFileListEmpty:
    def test_empty_directory(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        tool = FileListTool(working_dir=tmp_path)
        result = tool.execute(path="empty")
        assert "empty" in result.lower()


class TestFileListNonexistent:
    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        tool = FileListTool(working_dir=tmp_path)
        result = tool.execute(path="nope")
        assert "Error" in result
        assert "not found" in result.lower()


class TestFileListNested:
    def test_nested_listing(self, tmp_path: Path) -> None:
        sub = tmp_path / "level1"
        sub.mkdir()
        deep = sub / "level2"
        deep.mkdir()
        (sub / "file_l1.txt").write_text("l1", encoding="utf-8")
        (deep / "file_l2.txt").write_text("l2", encoding="utf-8")

        tool = FileListTool(working_dir=tmp_path)
        result = tool.execute(path=".", max_depth=3)
        assert "level1" in result
        assert "file_l1.txt" in result
        assert "level2" in result
        assert "file_l2.txt" in result

    def test_max_depth_caps_recursion(self, tmp_path: Path) -> None:
        # Create 5 levels deep
        current = tmp_path
        for i in range(5):
            current = current / f"level{i}"
            current.mkdir()
            (current / f"file{i}.txt").write_text(f"l{i}", encoding="utf-8")

        tool = FileListTool(working_dir=tmp_path)
        result = tool.execute(path=".", max_depth=2)
        assert "level0" in result
        assert "file0.txt" in result
        # level2 should not appear at depth=2
        assert "level2" not in result


class TestFileListSecurity:
    def test_rejects_absolute_path(self, tmp_path: Path) -> None:
        tool = FileListTool(working_dir=tmp_path)
        result = tool.execute(path="/etc")
        assert "Error" in result

    def test_rejects_path_traversal(self, tmp_path: Path) -> None:
        tool = FileListTool(working_dir=tmp_path)
        result = tool.execute(path="../../")
        assert "Error" in result

    def test_rejects_not_a_directory(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("data", encoding="utf-8")
        tool = FileListTool(working_dir=tmp_path)
        result = tool.execute(path="file.txt")
        assert "Error" in result
        assert "Not a directory" in result


class TestFileListSkipDirs:
    def test_skips_git_directory(self, tmp_path: Path) -> None:
        """Directories in _SKIP_DIRS are silently excluded."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("data", encoding="utf-8")
        (tmp_path / "real.txt").write_text("hello", encoding="utf-8")

        tool = FileListTool(working_dir=tmp_path)
        result = tool.execute(path=".", max_depth=3)
        assert "real.txt" in result
        assert ".git" not in result

    def test_skips_node_modules(self, tmp_path: Path) -> None:
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "pkg").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.js").write_text("code", encoding="utf-8")

        tool = FileListTool(working_dir=tmp_path)
        result = tool.execute(path=".", max_depth=3)
        assert "src" in result
        assert "app.js" in result
        assert "node_modules" not in result

    def test_skip_dirs_constant_includes_trash(self) -> None:
        assert ".Trash" in _SKIP_DIRS


class TestFileListOSError:
    def test_handles_timeout_on_iterdir(self, tmp_path: Path) -> None:
        """TimeoutError on network-mounted directories is caught gracefully."""
        (tmp_path / "ok.txt").write_text("fine", encoding="utf-8")
        sub = tmp_path / "slow_mount"
        sub.mkdir()

        tool = FileListTool(working_dir=tmp_path)

        # Patch Path.iterdir to raise TimeoutError for the problematic dir
        orig_iterdir = Path.iterdir

        def patched_iterdir(self_path: Path) -> Any:
            if self_path.name == "slow_mount":
                raise TimeoutError("Operation timed out")
            return orig_iterdir(self_path)

        with patch.object(Path, "iterdir", patched_iterdir):
            result = tool.execute(path=".", max_depth=3)

        assert "ok.txt" in result
        assert "access error" in result

    def test_handles_permission_error_on_iterdir(self, tmp_path: Path) -> None:
        """PermissionError (subclass of OSError) is still handled."""
        (tmp_path / "visible.txt").write_text("data", encoding="utf-8")
        restricted = tmp_path / "restricted"
        restricted.mkdir()

        tool = FileListTool(working_dir=tmp_path)

        orig_iterdir = Path.iterdir

        def patched_iterdir(self_path: Path) -> Any:
            if self_path.name == "restricted":
                raise PermissionError("Permission denied")
            return orig_iterdir(self_path)

        with patch.object(Path, "iterdir", patched_iterdir):
            result = tool.execute(path=".", max_depth=3)

        assert "visible.txt" in result
        assert "access error" in result


class TestFileListCrossPlatform:
    def test_path_validation_uses_is_relative_to(self, tmp_path: Path) -> None:
        """Ensure path check works on all platforms (no hard-coded '/')."""
        (tmp_path / "hello.txt").write_text("hi", encoding="utf-8")
        tool = FileListTool(working_dir=tmp_path)
        result = tool.execute(path=".")
        assert "hello.txt" in result
        assert "Error" not in result
