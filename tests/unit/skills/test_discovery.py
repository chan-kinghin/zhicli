"""Tests for skill discovery."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from zhi.skills import _scan_directory, discover_skills


def _write_skill(directory: Path, name: str, description: str = "Test") -> Path:
    """Helper to write a minimal valid skill YAML."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.yaml"
    path.write_text(
        f"name: {name}\n"
        f"description: {description}\n"
        f"system_prompt: You are a test assistant.\n"
        f"tools:\n  - file_read\n"
    )
    return path


class TestDiscoverSkills:
    def test_discover_builtin_skills(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        _write_skill(builtin, "summarize", "Summarize text")
        _write_skill(builtin, "translate", "Translate text")

        skills = discover_skills(builtin_dir=builtin, user_dir=None)
        assert "summarize" in skills
        assert "translate" in skills
        assert skills["summarize"].source == "builtin"

    def test_discover_user_skills(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        builtin.mkdir()
        user = tmp_path / "user"
        _write_skill(user, "my-skill", "My custom skill")

        skills = discover_skills(builtin_dir=builtin, user_dir=user)
        assert "my-skill" in skills
        assert skills["my-skill"].source == "user"

    def test_discover_merge_user_overrides_builtin(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        _write_skill(builtin, "summarize", "Builtin summarize")
        user = tmp_path / "user"
        _write_skill(user, "summarize", "User summarize")

        skills = discover_skills(builtin_dir=builtin, user_dir=user)
        assert skills["summarize"].description == "User summarize"
        assert skills["summarize"].source == "user"

    def test_discover_empty_user_dir(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        _write_skill(builtin, "summarize")
        user = tmp_path / "user"
        user.mkdir()

        skills = discover_skills(builtin_dir=builtin, user_dir=user)
        assert "summarize" in skills

    def test_discover_missing_user_dir(self, tmp_path: Path) -> None:
        """Missing user dir is not an error."""
        builtin = tmp_path / "builtin"
        _write_skill(builtin, "summarize")
        user = tmp_path / "nonexistent"

        skills = discover_skills(builtin_dir=builtin, user_dir=user)
        assert "summarize" in skills

    def test_discover_corrupted_skill_skipped(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        builtin.mkdir()
        _write_skill(builtin, "good-skill", "Good skill")
        bad = builtin / "bad.yaml"
        bad.write_text("this is: [malformed yaml\n")

        with pytest.warns(UserWarning, match="Skipping corrupted"):
            skills = discover_skills(builtin_dir=builtin, user_dir=None)
        assert "good-skill" in skills
        assert len(skills) == 1

    def test_discover_empty_builtin_dir(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        builtin.mkdir()

        skills = discover_skills(builtin_dir=builtin, user_dir=None)
        assert skills == {}

    def test_discover_both_dirs(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        _write_skill(builtin, "summarize", "Builtin summarize")
        user = tmp_path / "user"
        _write_skill(user, "my-custom", "Custom skill")

        skills = discover_skills(builtin_dir=builtin, user_dir=user)
        assert "summarize" in skills
        assert "my-custom" in skills

    def test_discover_real_builtins(self) -> None:
        """Test that the shipped builtin skills load correctly."""
        skills = discover_skills(user_dir=None)
        assert "summarize" in skills
        assert "translate" in skills
        assert skills["summarize"].model == "glm-4-flash"
        assert skills["translate"].model == "glm-4-flash"

    def test_scan_directory_oserror_on_glob(self, tmp_path: Path) -> None:
        """Bug 10: OSError on glob() should return empty dict, not crash."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _write_skill(skills_dir, "good-skill")

        orig_glob = Path.glob

        def patched_glob(self_path: Path, pattern: str) -> list[Path]:
            if self_path == skills_dir:
                raise PermissionError("Permission denied")
            return list(orig_glob(self_path, pattern))

        with patch.object(Path, "glob", patched_glob):
            result = _scan_directory(skills_dir, source="user")

        assert result == {}  # Graceful empty, no crash
