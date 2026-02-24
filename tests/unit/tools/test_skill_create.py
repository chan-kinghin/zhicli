"""Tests for skill_create tool."""

from __future__ import annotations

from pathlib import Path

import yaml

from zhi.tools.skill_create import SkillCreateTool


class TestSkillCreateValid:
    def test_creates_skill_yaml(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(
            skills_dir=skills_dir,
            known_tool_names=["file_read", "file_write", "ocr"],
        )
        result = tool.execute(
            name="summarize",
            description="Summarize a document",
            system_prompt="You are a summarizer.",
            tools=["file_read"],
        )
        assert "created" in result.lower()
        skill_file = skills_dir / "summarize.yaml"
        assert skill_file.exists()

        data = yaml.safe_load(skill_file.read_text(encoding="utf-8"))
        assert data["name"] == "summarize"
        assert data["description"] == "Summarize a document"
        assert data["tools"] == ["file_read"]
        assert data["model"] == "glm-4-flash"
        assert data["max_turns"] == 15

    def test_creates_with_custom_model(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(
            skills_dir=skills_dir,
            known_tool_names=["file_read"],
        )
        result = tool.execute(
            name="custom-skill",
            description="A skill",
            system_prompt="prompt",
            tools=["file_read"],
            model="glm-5",
            max_turns=5,
        )
        assert "created" in result.lower()

        data = yaml.safe_load(
            (skills_dir / "custom-skill.yaml").read_text(encoding="utf-8")
        )
        assert data["model"] == "glm-5"
        assert data["max_turns"] == 5


class TestSkillCreateValidatesTools:
    def test_rejects_unknown_tool(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(
            skills_dir=skills_dir,
            known_tool_names=["file_read", "file_write"],
        )
        result = tool.execute(
            name="bad",
            description="desc",
            system_prompt="prompt",
            tools=["file_read", "nonexistent_tool"],
        )
        assert "Error" in result
        assert "Unknown tools" in result
        assert "nonexistent_tool" in result

    def test_skips_validation_when_no_known_tools(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(skills_dir=skills_dir)
        result = tool.execute(
            name="any-skill",
            description="desc",
            system_prompt="prompt",
            tools=["anything"],
        )
        assert "created" in result.lower()


class TestSkillCreateRiskyFlag:
    def test_skill_create_is_risky(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        assert tool.risky is True


class TestSkillCreateDuplicateName:
    def test_rejects_duplicate(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "existing.yaml").write_text("name: existing", encoding="utf-8")

        tool = SkillCreateTool(skills_dir=skills_dir)
        result = tool.execute(
            name="existing",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
        )
        assert "Error" in result
        assert "already exists" in result


class TestSkillCreateNameValidation:
    def test_rejects_empty_name(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
        )
        assert "Error" in result

    def test_rejects_invalid_characters(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="bad skill!",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
        )
        assert "Error" in result
        assert "Invalid skill name" in result

    def test_rejects_path_traversal_in_name(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="../evil",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
        )
        assert "Error" in result

    def test_rejects_long_name(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="a" * 65,
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
        )
        assert "Error" in result
        assert "too long" in result.lower()

    def test_accepts_valid_names(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        for name in ["my-skill", "skill_v2", "Translate01", "a"]:
            result = tool.execute(
                name=name,
                description="desc",
                system_prompt="prompt",
                tools=["tool"],
            )
            assert "created" in result.lower(), f"Failed for name: {name}"


class TestSkillCreateDefaultModel:
    def test_default_model_from_config(self, tmp_path: Path) -> None:
        """Bug 6: default_model param overrides hardcoded glm-4-flash."""
        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(
            skills_dir=skills_dir,
            known_tool_names=["file_read"],
            default_model="glm-5",
        )
        result = tool.execute(
            name="myskill",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
        )
        assert "created" in result.lower()

        data = yaml.safe_load((skills_dir / "myskill.yaml").read_text(encoding="utf-8"))
        assert data["model"] == "glm-5"

    def test_default_model_overridden_by_explicit_model(self, tmp_path: Path) -> None:
        """Explicit model kwarg takes precedence over default_model."""
        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(
            skills_dir=skills_dir,
            default_model="glm-5",
        )
        result = tool.execute(
            name="myskill2",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
            model="glm-4-air",
        )
        assert "created" in result.lower()

        data = yaml.safe_load(
            (skills_dir / "myskill2.yaml").read_text(encoding="utf-8")
        )
        assert data["model"] == "glm-4-air"


class TestSkillCreateMissingFields:
    def test_missing_description(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="test",
            description="",
            system_prompt="prompt",
            tools=["file_read"],
        )
        assert "Error" in result

    def test_missing_system_prompt(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="test",
            description="desc",
            system_prompt="",
            tools=["file_read"],
        )
        assert "Error" in result

    def test_missing_tools(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="test",
            description="desc",
            system_prompt="prompt",
            tools=[],
        )
        assert "Error" in result
