"""Tests for skill_create tool."""

from __future__ import annotations

from pathlib import Path

import yaml

from zhi.tools.skill_create import SkillCreateTool

# ── YAML format (legacy) ────────────────────────────────────────────


class TestSkillCreateYaml:
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
            format="yaml",
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
            format="yaml",
        )
        assert "created" in result.lower()

        data = yaml.safe_load(
            (skills_dir / "custom-skill.yaml").read_text(encoding="utf-8")
        )
        assert data["model"] == "glm-5"
        assert data["max_turns"] == 5


# ── SKILL.md format (default) ───────────────────────────────────────


class TestSkillCreateMd:
    def test_default_format_is_skill_md(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="my-skill",
            description="A test skill",
            system_prompt="# My Skill\n\nYou are helpful.",
            tools=["file_read"],
        )
        assert "created" in result.lower()
        assert "SKILL.md" in result
        assert (tmp_path / "my-skill" / "SKILL.md").exists()

    def test_creates_skill_md_directory(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="analyze",
            description="Analyze documents",
            system_prompt="# Analysis\n\nAnalyze the document.",
            tools=["file_read", "ask_user"],
            format="skill_md",
        )
        assert "created" in result.lower()

        skill_dir = tmp_path / "analyze"
        assert skill_dir.is_dir()
        skill_md = skill_dir / "SKILL.md"
        assert skill_md.exists()

        content = skill_md.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        assert "name: analyze" in content
        assert "description: Analyze documents" in content
        assert "# Analysis" in content
        assert "Analyze the document." in content

    def test_frontmatter_has_tools(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="multi-tool",
            description="desc",
            system_prompt="body",
            tools=["file_read", "shell", "ask_user"],
        )
        content = (tmp_path / "multi-tool" / "SKILL.md").read_text(encoding="utf-8")
        assert "file_read" in content
        assert "shell" in content
        assert "ask_user" in content

    def test_custom_model_in_frontmatter(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="glm5-skill",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            model="glm-5",
        )
        content = (tmp_path / "glm5-skill" / "SKILL.md").read_text(encoding="utf-8")
        assert "model: glm-5" in content

    def test_default_model_omitted_from_frontmatter(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="default-model",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
        )
        content = (tmp_path / "default-model" / "SKILL.md").read_text(encoding="utf-8")
        # Default model should not clutter the frontmatter
        assert "model:" not in content

    def test_custom_max_turns_in_frontmatter(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="long-skill",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            max_turns=30,
        )
        content = (tmp_path / "long-skill" / "SKILL.md").read_text(encoding="utf-8")
        assert "max_turns: 30" in content

    def test_default_max_turns_omitted(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="normal-skill",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
        )
        content = (tmp_path / "normal-skill" / "SKILL.md").read_text(encoding="utf-8")
        assert "max_turns:" not in content

    def test_input_args_in_frontmatter(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="file-skill",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            input_args=[
                {"name": "file", "type": "file", "required": True},
                {"name": "query", "type": "string", "required": False},
            ],
        )
        content = (tmp_path / "file-skill" / "SKILL.md").read_text(encoding="utf-8")
        assert "input:" in content
        assert "name: file" in content
        assert "type: file" in content


class TestSkillCreateMdReferences:
    def test_copies_reference_files(self, tmp_path: Path) -> None:
        # Create source reference files
        ref1 = tmp_path / "ref1.md"
        ref1.write_text("# Reference 1\n\nSome knowledge.", encoding="utf-8")
        ref2 = tmp_path / "ref2.md"
        ref2.write_text("# Reference 2\n\nMore knowledge.", encoding="utf-8")

        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(skills_dir=skills_dir)
        result = tool.execute(
            name="with-refs",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            references=[str(ref1), str(ref2)],
        )
        assert "created" in result.lower()
        assert "ref1.md" in result
        assert "ref2.md" in result

        refs_dir = skills_dir / "with-refs" / "references"
        assert refs_dir.is_dir()
        assert (refs_dir / "ref1.md").exists()
        assert (refs_dir / "ref2.md").exists()
        assert (refs_dir / "ref1.md").read_text(
            encoding="utf-8"
        ) == "# Reference 1\n\nSome knowledge."

    def test_skips_nonexistent_reference_files(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(skills_dir=skills_dir)
        result = tool.execute(
            name="missing-refs",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            references=["/nonexistent/file.md"],
        )
        assert "created" in result.lower()
        # No references/ dir created when all references are skipped
        refs_dir = skills_dir / "missing-refs" / "references"
        assert not refs_dir.exists()

    def test_no_references_dir_when_none(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="no-refs",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
        )
        refs_dir = tmp_path / "no-refs" / "references"
        assert not refs_dir.exists()

    def test_references_ignored_for_yaml(self, tmp_path: Path) -> None:
        ref = tmp_path / "ref.md"
        ref.write_text("content", encoding="utf-8")

        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="yaml-refs",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
            format="yaml",
            references=[str(ref)],
        )
        # YAML format should not create a directory or copy refs
        assert (tmp_path / "yaml-refs.yaml").exists()
        assert not (tmp_path / "yaml-refs").exists()


# ── Duplicate detection (both formats) ──────────────────────────────


class TestSkillCreateDuplicateDetection:
    def test_rejects_when_yaml_exists(self, tmp_path: Path) -> None:
        (tmp_path / "existing.yaml").write_text("name: existing", encoding="utf-8")

        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="existing",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
        )
        assert "Error" in result
        assert "already exists" in result

    def test_rejects_when_skill_md_dir_exists(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "existing"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: existing\n---\nbody")

        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="existing",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
        )
        assert "Error" in result
        assert "already exists" in result

    def test_yaml_format_rejects_when_md_exists(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "taken"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: taken\n---\nbody")

        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="taken",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
            format="yaml",
        )
        assert "Error" in result
        assert "already exists" in result

    def test_md_format_rejects_when_yaml_exists(self, tmp_path: Path) -> None:
        (tmp_path / "taken.yaml").write_text("name: taken")

        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="taken",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
            format="skill_md",
        )
        assert "Error" in result
        assert "already exists" in result


# ── Validation (shared across formats) ──────────────────────────────


class TestSkillCreateValidation:
    def test_rejects_unknown_tool(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(
            skills_dir=tmp_path,
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

    def test_skips_validation_when_no_known_tools(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="any-skill",
            description="desc",
            system_prompt="prompt",
            tools=["anything"],
        )
        assert "created" in result.lower()

    def test_rejects_empty_name(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="", description="desc", system_prompt="p", tools=["t"]
        )
        assert "Error" in result

    def test_rejects_invalid_characters(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="bad skill!", description="desc", system_prompt="p", tools=["t"]
        )
        assert "Error" in result
        assert "Invalid skill name" in result

    def test_rejects_path_traversal(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="../evil", description="desc", system_prompt="p", tools=["t"]
        )
        assert "Error" in result

    def test_rejects_long_name(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="a" * 65, description="desc", system_prompt="p", tools=["t"]
        )
        assert "Error" in result
        assert "too long" in result.lower()

    def test_accepts_valid_names(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        for name in ["my-skill", "skill_v2", "Translate01", "a"]:
            result = tool.execute(
                name=name, description="desc", system_prompt="p", tools=["t"]
            )
            assert "created" in result.lower(), f"Failed for name: {name}"

    def test_missing_description(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="test", description="", system_prompt="p", tools=["t"]
        )
        assert "Error" in result

    def test_missing_system_prompt(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="test", description="d", system_prompt="", tools=["t"]
        )
        assert "Error" in result

    def test_missing_tools(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(name="test", description="d", system_prompt="p", tools=[])
        assert "Error" in result

    def test_invalid_format(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="test",
            description="d",
            system_prompt="p",
            tools=["t"],
            format="invalid",
        )
        assert "Error" in result
        assert "format" in result.lower()


class TestSkillCreateDescriptions:
    def test_class_description_mentions_ask_user(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        assert "ask_user" in tool.description

    def test_tools_param_description_mentions_ask_user(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tools_desc = tool.parameters["properties"]["tools"]["description"]
        assert "ask_user" in tools_desc


class TestSkillCreateRiskyFlag:
    def test_skill_create_is_risky(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        assert tool.risky is True


class TestSkillCreateDefaultModel:
    def test_default_model_from_config(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(
            skills_dir=tmp_path,
            known_tool_names=["file_read"],
            default_model="glm-5",
        )
        result = tool.execute(
            name="myskill",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
            format="yaml",
        )
        assert "created" in result.lower()

        data = yaml.safe_load((tmp_path / "myskill.yaml").read_text(encoding="utf-8"))
        assert data["model"] == "glm-5"

    def test_default_model_overridden_by_explicit(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path, default_model="glm-5")
        result = tool.execute(
            name="myskill2",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
            model="glm-4-air",
            format="yaml",
        )
        assert "created" in result.lower()

        data = yaml.safe_load((tmp_path / "myskill2.yaml").read_text(encoding="utf-8"))
        assert data["model"] == "glm-4-air"

    def test_default_model_omitted_in_skill_md(self, tmp_path: Path) -> None:
        """When no explicit model is given, the default is omitted from frontmatter."""
        tool = SkillCreateTool(skills_dir=tmp_path, default_model="glm-5")
        tool.execute(
            name="md-skill",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
        )
        content = (tmp_path / "md-skill" / "SKILL.md").read_text(encoding="utf-8")
        assert "model:" not in content

    def test_explicit_model_in_skill_md(self, tmp_path: Path) -> None:
        """When an explicit model differs from default, it appears in frontmatter."""
        tool = SkillCreateTool(skills_dir=tmp_path, default_model="glm-4-flash")
        tool.execute(
            name="md-skill",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            model="glm-5",
        )
        content = (tmp_path / "md-skill" / "SKILL.md").read_text(encoding="utf-8")
        assert "model: glm-5" in content


class TestSkillCreateMaxTurns:
    def test_clamps_high(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="high-turns",
            description="desc",
            system_prompt="body",
            tools=["t"],
            max_turns=999,
        )
        content = (tmp_path / "high-turns" / "SKILL.md").read_text(encoding="utf-8")
        assert "max_turns: 50" in content

    def test_clamps_low(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="low-turns",
            description="desc",
            system_prompt="body",
            tools=["t"],
            max_turns=-5,
        )
        # max_turns=1 is the default (15), but clamped to 1 which differs,
        # so it should appear in frontmatter
        content = (tmp_path / "low-turns" / "SKILL.md").read_text(encoding="utf-8")
        assert "max_turns: 1" in content


class TestSkillCreateRoundTrip:
    """Verify created SKILL.md files can be loaded by loader_md."""

    def test_created_skill_md_is_loadable(self, tmp_path: Path) -> None:
        from zhi.skills.loader_md import load_skill_md

        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="roundtrip",
            description="A round-trip test skill",
            system_prompt="# Round Trip\n\nYou are a test assistant.",
            tools=["file_read", "ask_user"],
            model="glm-5",
            max_turns=20,
            input_args=[{"name": "file", "type": "file", "required": True}],
        )

        config = load_skill_md(tmp_path / "roundtrip" / "SKILL.md")
        assert config.name == "roundtrip"
        assert config.description == "A round-trip test skill"
        assert config.tools == ["file_read", "ask_user"]
        assert config.model == "glm-5"
        assert config.max_turns == 20
        assert len(config.input_args) == 1
        assert config.input_args[0]["name"] == "file"
        assert "# Round Trip" in config.system_prompt

    def test_created_with_refs_is_loadable(self, tmp_path: Path) -> None:
        from zhi.skills.loader_md import load_skill_md

        ref = tmp_path / "knowledge.md"
        ref.write_text("# Knowledge\n\nImportant facts.", encoding="utf-8")

        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(skills_dir=skills_dir)
        tool.execute(
            name="with-knowledge",
            description="A skill with references",
            system_prompt="# Smart Skill\n\nUse the references.",
            tools=["file_read"],
            references=[str(ref)],
        )

        config = load_skill_md(skills_dir / "with-knowledge" / "SKILL.md")
        assert config.name == "with-knowledge"
        assert "# Smart Skill" in config.system_prompt
        assert "# Knowledge" in config.system_prompt  # Reference injected
        assert "Important facts." in config.system_prompt


# ── Output parameter (C1) ─────────────────────────────────────────


class TestSkillCreateOutput:
    def test_skill_md_output_in_frontmatter(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="out-skill",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            output={"description": "Generated report", "directory": "reports"},
        )
        assert "created" in result.lower()

        content = (tmp_path / "out-skill" / "SKILL.md").read_text(encoding="utf-8")
        assert "output:" in content
        assert "description: Generated report" in content
        assert "directory: reports" in content

    def test_skill_md_output_omitted_when_not_provided(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="no-out",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
        )
        content = (tmp_path / "no-out" / "SKILL.md").read_text(encoding="utf-8")
        assert "output:" not in content

    def test_skill_md_output_empty_values_omitted(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="empty-out",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            output={"description": "", "directory": ""},
        )
        content = (tmp_path / "empty-out" / "SKILL.md").read_text(encoding="utf-8")
        assert "output:" not in content

    def test_yaml_output_in_config(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        result = tool.execute(
            name="yaml-out",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
            format="yaml",
            output={"description": "CSV files", "directory": "csv-output"},
        )
        assert "created" in result.lower()

        data = yaml.safe_load((tmp_path / "yaml-out.yaml").read_text(encoding="utf-8"))
        assert data["output"]["description"] == "CSV files"
        assert data["output"]["directory"] == "csv-output"

    def test_yaml_output_omitted_when_not_provided(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="yaml-no-out",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
            format="yaml",
        )
        data = yaml.safe_load(
            (tmp_path / "yaml-no-out.yaml").read_text(encoding="utf-8")
        )
        assert "output" not in data

    def test_output_roundtrip_with_loader(self, tmp_path: Path) -> None:
        from zhi.skills.loader_md import load_skill_md

        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="rt-out",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            output={"description": "Analysis results", "directory": "analysis"},
        )
        config = load_skill_md(tmp_path / "rt-out" / "SKILL.md")
        assert config.output_description == "Analysis results"
        assert config.output_directory == "analysis"


# ── Reference size warning (C2) ───────────────────────────────────


class TestSkillCreateReferenceSizeWarning:
    def test_reference_size_warning(self, tmp_path: Path) -> None:
        # Create a reference file larger than 50KB
        big_ref = tmp_path / "big.txt"
        big_ref.write_text("x" * 60_000, encoding="utf-8")

        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(skills_dir=skills_dir)
        result = tool.execute(
            name="big-refs",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            references=[str(big_ref)],
        )
        assert "Warning" in result
        assert "50KB limit" in result
        assert "truncated" in result.lower()

    def test_no_warning_under_limit(self, tmp_path: Path) -> None:
        small_ref = tmp_path / "small.txt"
        small_ref.write_text("x" * 100, encoding="utf-8")

        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(skills_dir=skills_dir)
        result = tool.execute(
            name="small-refs",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            references=[str(small_ref)],
        )
        assert "Warning" not in result


# ── Skipped references reported (C3) ──────────────────────────────


class TestSkillCreateSkippedReferences:
    def test_skipped_references_reported(self, tmp_path: Path) -> None:
        valid_ref = tmp_path / "valid.md"
        valid_ref.write_text("content", encoding="utf-8")

        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(skills_dir=skills_dir)
        result = tool.execute(
            name="mixed-refs",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            references=[str(valid_ref), "/nonexistent/missing.txt"],
        )
        assert "created" in result.lower()
        assert "valid.md" in result
        assert "Note:" in result
        assert "1 reference file(s) skipped" in result
        assert "missing.txt" in result
        assert "not found" in result

    def test_all_skipped_references_reported(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(skills_dir=skills_dir)
        result = tool.execute(
            name="all-skipped",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            references=["/nonexistent/a.txt", "/nonexistent/b.txt"],
        )
        assert "created" in result.lower()
        assert "Note:" in result
        assert "2 reference file(s) skipped" in result


# ── No empty references dir (C4) ──────────────────────────────────


# ── Version parameter ──────────────────────────────────────────────


class TestSkillCreateVersion:
    def test_version_in_frontmatter(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="ver-skill",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            version="1.0.0",
        )
        content = (tmp_path / "ver-skill" / "SKILL.md").read_text(encoding="utf-8")
        assert "version: 1.0.0" in content

    def test_version_omitted_when_empty(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="no-ver",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
        )
        content = (tmp_path / "no-ver" / "SKILL.md").read_text(encoding="utf-8")
        assert "version:" not in content

    def test_version_in_yaml(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="yaml-ver",
            description="desc",
            system_prompt="prompt",
            tools=["file_read"],
            format="yaml",
            version="2.0.0",
        )
        data = yaml.safe_load(
            (tmp_path / "yaml-ver.yaml").read_text(encoding="utf-8")
        )
        assert data["version"] == "2.0.0"

    def test_version_roundtrip(self, tmp_path: Path) -> None:
        from zhi.skills.loader_md import load_skill_md

        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="rt-ver",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            version="3.1.0",
        )
        config = load_skill_md(tmp_path / "rt-ver" / "SKILL.md")
        assert config.version == "3.1.0"


# ── Disable model invocation parameter ────────────────────────────


class TestSkillCreateDisableModelInvocation:
    def test_disable_model_invocation_in_frontmatter(self, tmp_path: Path) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="dmi-skill",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            disable_model_invocation=True,
        )
        content = (tmp_path / "dmi-skill" / "SKILL.md").read_text(encoding="utf-8")
        assert "disable-model-invocation: true" in content

    def test_disable_model_invocation_omitted_when_false(
        self, tmp_path: Path
    ) -> None:
        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="no-dmi",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
        )
        content = (tmp_path / "no-dmi" / "SKILL.md").read_text(encoding="utf-8")
        assert "disable-model-invocation" not in content

    def test_disable_model_invocation_roundtrip(self, tmp_path: Path) -> None:
        from zhi.skills.loader_md import load_skill_md

        tool = SkillCreateTool(skills_dir=tmp_path)
        tool.execute(
            name="rt-dmi",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            disable_model_invocation=True,
        )
        config = load_skill_md(tmp_path / "rt-dmi" / "SKILL.md")
        assert config.disable_model_invocation is True


# ── No empty references dir (C4) ──────────────────────────────────


class TestSkillCreateNoEmptyRefsDir:
    def test_no_empty_references_dir(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(skills_dir=skills_dir)
        tool.execute(
            name="no-refs-dir",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            references=["/nonexistent/file.md"],
        )
        refs_dir = skills_dir / "no-refs-dir" / "references"
        assert not refs_dir.exists()

    def test_refs_dir_created_when_valid_refs(self, tmp_path: Path) -> None:
        ref = tmp_path / "real.md"
        ref.write_text("content", encoding="utf-8")

        skills_dir = tmp_path / "skills"
        tool = SkillCreateTool(skills_dir=skills_dir)
        tool.execute(
            name="with-refs-dir",
            description="desc",
            system_prompt="body",
            tools=["file_read"],
            references=[str(ref)],
        )
        refs_dir = skills_dir / "with-refs-dir" / "references"
        assert refs_dir.is_dir()
        assert (refs_dir / "real.md").exists()
