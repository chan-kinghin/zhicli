"""Tests for SKILL.md loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from zhi.errors import SkillError
from zhi.skills.loader_md import _MAX_REFERENCES_SIZE, load_skill_md


def _write_skill_md(
    directory: Path,
    name: str,
    description: str = "Test",
    tools: str = "file_read",
    body: str = "",
    *,
    extra_frontmatter: str = "",
) -> Path:
    """Helper to write a minimal valid SKILL.md directory."""
    skill_dir = directory / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    if not body:
        body = f"# {name}\n\nYou are a {description} assistant."
    content = (
        f"---\nname: {name}\ndescription: {description}\ntools: [{tools}]\n"
        f"{extra_frontmatter}---\n\n{body}\n"
    )
    skill_md.write_text(content)
    return skill_dir


class TestLoadValidSkillMd:
    def test_load_valid_skill_md(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(tmp_path, "my-skill", "My test skill")
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.name == "my-skill"
        assert config.description == "My test skill"
        assert config.tools == ["file_read"]

    def test_body_becomes_system_prompt(self, tmp_path: Path) -> None:
        body = "# Instructions\n\nDo something useful."
        skill_dir = _write_skill_md(tmp_path, "body-test", body=body)
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.system_prompt == body

    def test_source_stored(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(tmp_path, "src-test")
        config = load_skill_md(skill_dir / "SKILL.md", source="user")
        assert config.source == "user"


class TestReferences:
    def test_references_appended_to_prompt(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(tmp_path, "ref-test", body="Main prompt.")
        refs = skill_dir / "references"
        refs.mkdir()
        (refs / "prices.txt").write_text("item1: $10\nitem2: $20")
        config = load_skill_md(skill_dir / "SKILL.md")
        assert "Main prompt." in config.system_prompt
        assert "### references/prices.txt" in config.system_prompt
        assert "item1: $10" in config.system_prompt

    def test_references_capped_at_max_size(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(tmp_path, "big-ref", body="Prompt.")
        refs = skill_dir / "references"
        refs.mkdir()
        # Write a file that exceeds the cap
        (refs / "a_big.txt").write_text("x" * (_MAX_REFERENCES_SIZE + 100))
        # The file itself is too big to fit, but since total_size starts at 0
        # and the first file exceeds the limit, it gets skipped with a warning.
        with pytest.warns(UserWarning, match="Reference files exceed"):
            config = load_skill_md(skill_dir / "SKILL.md")
        # Only the body remains (no reference content added)
        assert "### a_big.txt" not in config.system_prompt

    def test_no_references_dir(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(tmp_path, "no-refs", body="Just the body.")
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.system_prompt == "Just the body."

    def test_hidden_reference_files_skipped(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(tmp_path, "hidden-ref", body="Prompt.")
        refs = skill_dir / "references"
        refs.mkdir()
        (refs / ".hidden").write_text("secret")
        (refs / "visible.txt").write_text("visible content")
        config = load_skill_md(skill_dir / "SKILL.md")
        assert ".hidden" not in config.system_prompt
        assert "visible content" in config.system_prompt

    def test_multiple_references_sorted(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(tmp_path, "multi-ref", body="Prompt.")
        refs = skill_dir / "references"
        refs.mkdir()
        (refs / "b_second.txt").write_text("second")
        (refs / "a_first.txt").write_text("first")
        config = load_skill_md(skill_dir / "SKILL.md")
        a_pos = config.system_prompt.index("### references/a_first.txt")
        b_pos = config.system_prompt.index("### references/b_second.txt")
        assert a_pos < b_pos

    def test_binary_reference_file_skipped(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(tmp_path, "bin-ref", body="Prompt.")
        refs = skill_dir / "references"
        refs.mkdir()
        (refs / "binary.bin").write_bytes(b"\x80\x81\x82\xff")
        (refs / "good.txt").write_text("good content")
        config = load_skill_md(skill_dir / "SKILL.md")
        assert "good content" in config.system_prompt


class TestFrontmatterErrors:
    def test_missing_frontmatter(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "no-fm"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# No frontmatter here\n")
        with pytest.raises(SkillError, match="must start with YAML frontmatter"):
            load_skill_md(skill_dir / "SKILL.md")

    def test_malformed_frontmatter_yaml(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "bad-yaml"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: [broken yaml\n---\n\nBody.\n")
        with pytest.raises(SkillError, match="Malformed YAML frontmatter"):
            load_skill_md(skill_dir / "SKILL.md")

    def test_frontmatter_not_mapping(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "list-fm"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\n- item1\n- item2\n---\n\nBody.\n")
        with pytest.raises(SkillError, match="must be a YAML mapping"):
            load_skill_md(skill_dir / "SKILL.md")

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "missing-fields"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: incomplete\n---\n\nBody.\n")
        with pytest.raises(SkillError, match="Missing required frontmatter fields"):
            load_skill_md(skill_dir / "SKILL.md")

    def test_missing_required_fields_lists_which(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "which-fields"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: incomplete\n---\n\nBody.\n")
        with pytest.raises(SkillError) as exc_info:
            load_skill_md(skill_dir / "SKILL.md")
        msg = str(exc_info.value)
        assert "description" in msg


class TestNameValidation:
    def test_invalid_skill_name(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "bad-name"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: '../traversal'\n"
            "description: Bad\ntools: [file_read]\n---\n\nBody.\n"
        )
        with pytest.raises(SkillError, match="Invalid skill name"):
            load_skill_md(skill_dir / "SKILL.md")


class TestToolsValidation:
    def test_tools_not_list(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "tools-str"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: badtools\ndescription: Bad\ntools: file_read\n---\n\nBody.\n"
        )
        with pytest.raises(SkillError, match="must be a list"):
            load_skill_md(skill_dir / "SKILL.md")

    def test_description_not_string(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "desc-list"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: baddesc\n"
            "description:\n  - not a string\n"
            "tools: [file_read]\n---\n\nBody.\n"
        )
        with pytest.raises(SkillError, match="must be a string"):
            load_skill_md(skill_dir / "SKILL.md")


class TestFileErrors:
    def test_empty_file(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "empty"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("")
        with pytest.raises(SkillError, match="empty"):
            load_skill_md(skill_dir / "SKILL.md")

    def test_whitespace_only_file(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "whitespace"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("   \n\n  ")
        with pytest.raises(SkillError, match="empty"):
            load_skill_md(skill_dir / "SKILL.md")

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(SkillError, match="not found"):
            load_skill_md(tmp_path / "nonexistent" / "SKILL.md")


class TestDefaultsAndOptionalFields:
    def test_default_model(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(tmp_path, "default-model")
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.model == "glm-4-flash"

    def test_custom_model(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(
            tmp_path, "custom-model", extra_frontmatter="model: glm-5\n"
        )
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.model == "glm-5"

    def test_default_max_turns(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(tmp_path, "default-turns")
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.max_turns == 15

    def test_max_turns_clamped_high(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(
            tmp_path, "high-turns", extra_frontmatter="max_turns: 999\n"
        )
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.max_turns == 50

    def test_max_turns_clamped_low(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(
            tmp_path, "low-turns", extra_frontmatter="max_turns: 0\n"
        )
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.max_turns == 1

    def test_max_turns_non_int_defaults(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(
            tmp_path, "str-turns", extra_frontmatter='max_turns: "not a number"\n'
        )
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.max_turns == 15

    def test_input_args_parsed(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "input-test"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: input-test\n"
            "description: Test input\n"
            "tools: [file_read]\n"
            "input:\n"
            "  args:\n"
            "    - name: file\n"
            "      type: file\n"
            "      required: true\n"
            "---\n\n"
            "Body.\n"
        )
        config = load_skill_md(skill_dir / "SKILL.md")
        assert len(config.input_args) == 1
        assert config.input_args[0]["name"] == "file"
        assert config.input_args[0]["required"] is True

    def test_output_section_parsed(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "output-test"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: output-test\n"
            "description: Test output\n"
            "tools: [file_read]\n"
            "output:\n"
            "  description: A report\n"
            "  directory: reports\n"
            "---\n\n"
            "Body.\n"
        )
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.output_description == "A report"
        assert config.output_directory == "reports"

    def test_output_defaults(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(tmp_path, "output-default")
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.output_description == ""
        assert config.output_directory == "zhi-output"

    def test_empty_body(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "empty-body"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: empty-body\ndescription: No body\ntools: [file_read]\n---\n"
        )
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.system_prompt == ""

    def test_multiple_tools(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(
            tmp_path, "multi-tools", tools="file_read, shell, ask_user"
        )
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.tools == ["file_read", "shell", "ask_user"]


class TestVersionFieldMd:
    def test_version_field_parsed(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(
            tmp_path, "ver-test", extra_frontmatter="version: '2.0.1'\n"
        )
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.version == "2.0.1"

    def test_version_default(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(tmp_path, "no-ver")
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.version == ""


class TestDisableModelInvocationMd:
    def test_disable_model_invocation_parsed(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(
            tmp_path, "dmi-test", extra_frontmatter="disable-model-invocation: true\n"
        )
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.disable_model_invocation is True

    def test_disable_model_invocation_default(self, tmp_path: Path) -> None:
        skill_dir = _write_skill_md(tmp_path, "dmi-default")
        config = load_skill_md(skill_dir / "SKILL.md")
        assert config.disable_model_invocation is False
