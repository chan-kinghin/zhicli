"""Tests for skill YAML loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from zhi.errors import SkillError
from zhi.skills.loader import (
    MAX_SKILL_NAME_LENGTH,
    SKILL_NAME_PATTERN,
    load_skill,
    validate_skill_name,
)


@pytest.fixture
def fixtures_skills() -> Path:
    return Path(__file__).parent.parent.parent / "fixtures" / "skills"


class TestValidateSkillName:
    def test_valid_simple(self) -> None:
        assert validate_skill_name("summarize") is True

    def test_valid_with_hyphens(self) -> None:
        assert validate_skill_name("compare-docs") is True

    def test_valid_with_underscores(self) -> None:
        assert validate_skill_name("my_skill") is True

    def test_valid_with_numbers(self) -> None:
        assert validate_skill_name("skill123") is True

    def test_valid_starts_with_number(self) -> None:
        assert validate_skill_name("1skill") is True

    def test_empty_name(self) -> None:
        assert validate_skill_name("") is False

    def test_too_long(self) -> None:
        assert validate_skill_name("a" * (MAX_SKILL_NAME_LENGTH + 1)) is False

    def test_max_length(self) -> None:
        assert validate_skill_name("a" * MAX_SKILL_NAME_LENGTH) is True

    def test_path_traversal_dots(self) -> None:
        assert validate_skill_name("../etc/passwd") is False

    def test_path_traversal_slash(self) -> None:
        assert validate_skill_name("foo/bar") is False

    def test_path_traversal_backslash(self) -> None:
        assert validate_skill_name("foo\\bar") is False

    def test_spaces_rejected(self) -> None:
        assert validate_skill_name("my skill") is False

    def test_special_chars_rejected(self) -> None:
        assert validate_skill_name("skill@home") is False
        assert validate_skill_name("skill!") is False
        assert validate_skill_name("skill.yaml") is False

    def test_starts_with_hyphen(self) -> None:
        assert validate_skill_name("-skill") is False

    def test_starts_with_underscore(self) -> None:
        assert validate_skill_name("_skill") is False

    def test_non_string(self) -> None:
        assert validate_skill_name(123) is False  # type: ignore[arg-type]


class TestLoadSkill:
    def test_load_valid_skill(self, fixtures_skills: Path) -> None:
        config = load_skill(fixtures_skills / "valid_skill.yaml")
        assert config.name == "test-skill"
        assert config.description == "A test skill for unit testing"
        assert config.model == "glm-4-flash"
        assert config.system_prompt.startswith("You are a test assistant.")
        assert config.tools == ["file_read", "file_write"]
        assert config.max_turns == 10
        assert len(config.input_args) == 1
        assert config.input_args[0]["name"] == "file"
        assert config.output_description == "Test output"
        assert config.output_directory == "zhi-output"

    def test_load_minimal_skill(self, fixtures_skills: Path) -> None:
        config = load_skill(fixtures_skills / "minimal_skill.yaml")
        assert config.name == "minimal"
        assert config.description == "A minimal skill with only required fields"
        assert config.tools == ["file_read"]

    def test_load_minimal_skill_defaults(self, fixtures_skills: Path) -> None:
        config = load_skill(fixtures_skills / "minimal_skill.yaml")
        assert config.model == "glm-4-flash"
        assert config.max_turns == 15
        assert config.input_args == []
        assert config.output_description == ""
        assert config.output_directory == "zhi-output"

    def test_load_malformed_yaml(self, fixtures_skills: Path) -> None:
        with pytest.raises(SkillError, match="Malformed YAML"):
            load_skill(fixtures_skills / "malformed_skill.yaml")

    def test_load_missing_required_fields(self, fixtures_skills: Path) -> None:
        with pytest.raises(SkillError, match="Missing required fields"):
            load_skill(fixtures_skills / "missing_fields.yaml")

    def test_load_missing_required_fields_lists_fields(
        self, fixtures_skills: Path
    ) -> None:
        with pytest.raises(SkillError) as exc_info:
            load_skill(fixtures_skills / "missing_fields.yaml")
        msg = str(exc_info.value)
        assert "system_prompt" in msg
        assert "tools" in msg

    def test_load_extra_fields_ignored(self, fixtures_skills: Path) -> None:
        with pytest.warns(UserWarning, match="Unknown fields"):
            config = load_skill(fixtures_skills / "extra_fields.yaml")
        assert config.name == "extra-fields"
        assert config.tools == ["file_read"]

    def test_load_empty_file(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        with pytest.raises(SkillError, match="empty"):
            load_skill(empty)

    def test_load_binary_file(self, tmp_path: Path) -> None:
        binary = tmp_path / "binary.yaml"
        binary.write_bytes(b"\x00\x01\x02\x03")
        with pytest.raises(SkillError, match="binary"):
            load_skill(binary)

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        with pytest.raises(SkillError, match="not found"):
            load_skill(tmp_path / "nonexistent.yaml")

    def test_skill_model_default(self, tmp_path: Path) -> None:
        skill_yaml = tmp_path / "no_model.yaml"
        skill_yaml.write_text(
            "name: nomodel\n"
            "description: No model specified\n"
            "system_prompt: test\n"
            "tools:\n  - file_read\n"
        )
        config = load_skill(skill_yaml)
        assert config.model == "glm-4-flash"

    def test_skill_max_turns_default(self, tmp_path: Path) -> None:
        skill_yaml = tmp_path / "no_turns.yaml"
        skill_yaml.write_text(
            "name: noturns\n"
            "description: No max_turns specified\n"
            "system_prompt: test\n"
            "tools:\n  - file_read\n"
        )
        config = load_skill(skill_yaml)
        assert config.max_turns == 15

    def test_skill_name_path_traversal_rejected(self, tmp_path: Path) -> None:
        skill_yaml = tmp_path / "traversal.yaml"
        skill_yaml.write_text(
            "name: '../etc/passwd'\n"
            "description: Path traversal attempt\n"
            "system_prompt: test\n"
            "tools:\n  - file_read\n"
        )
        with pytest.raises(SkillError, match="Invalid skill name"):
            load_skill(skill_yaml)

    def test_skill_name_special_chars_rejected(self, tmp_path: Path) -> None:
        skill_yaml = tmp_path / "special.yaml"
        skill_yaml.write_text(
            "name: 'skill@home!'\n"
            "description: Special chars\n"
            "system_prompt: test\n"
            "tools:\n  - file_read\n"
        )
        with pytest.raises(SkillError, match="Invalid skill name"):
            load_skill(skill_yaml)

    def test_load_unknown_tool_reference(self, tmp_path: Path) -> None:
        """Unknown tool references are loaded (validation happens at run time)."""
        skill_yaml = tmp_path / "unknown_tool.yaml"
        skill_yaml.write_text(
            "name: unknowntool\n"
            "description: Has unknown tool\n"
            "system_prompt: test\n"
            "tools:\n  - nonexistent_tool\n"
        )
        config = load_skill(skill_yaml)
        assert config.tools == ["nonexistent_tool"]

    def test_load_yaml_with_non_dict(self, tmp_path: Path) -> None:
        skill_yaml = tmp_path / "list.yaml"
        skill_yaml.write_text("- item1\n- item2\n")
        with pytest.raises(SkillError, match="YAML mapping"):
            load_skill(skill_yaml)

    def test_load_tools_not_list(self, tmp_path: Path) -> None:
        skill_yaml = tmp_path / "tools_str.yaml"
        skill_yaml.write_text(
            "name: badtools\n"
            "description: tools is a string\n"
            "system_prompt: test\n"
            "tools: file_read\n"
        )
        with pytest.raises(SkillError, match="must be a list"):
            load_skill(skill_yaml)

    def test_skill_custom_model(self, tmp_path: Path) -> None:
        skill_yaml = tmp_path / "custom_model.yaml"
        skill_yaml.write_text(
            "name: custommodel\n"
            "description: Custom model\n"
            "system_prompt: test\n"
            "tools:\n  - file_read\n"
            "model: glm-5\n"
        )
        config = load_skill(skill_yaml)
        assert config.model == "glm-5"

    def test_skill_custom_max_turns(self, tmp_path: Path) -> None:
        skill_yaml = tmp_path / "custom_turns.yaml"
        skill_yaml.write_text(
            "name: customturns\n"
            "description: Custom turns\n"
            "system_prompt: test\n"
            "tools:\n  - file_read\n"
            "max_turns: 30\n"
        )
        config = load_skill(skill_yaml)
        assert config.max_turns == 30


class TestSkillNamePattern:
    def test_pattern_matches_alphanumeric(self) -> None:
        assert SKILL_NAME_PATTERN.match("abc123")

    def test_pattern_matches_hyphens(self) -> None:
        assert SKILL_NAME_PATTERN.match("my-skill")

    def test_pattern_matches_underscores(self) -> None:
        assert SKILL_NAME_PATTERN.match("my_skill")

    def test_pattern_rejects_slash(self) -> None:
        assert not SKILL_NAME_PATTERN.match("a/b")

    def test_pattern_rejects_dot(self) -> None:
        assert not SKILL_NAME_PATTERN.match("a.b")
