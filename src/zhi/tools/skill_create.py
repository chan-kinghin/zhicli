"""Skill creation tool for zhi.

Supports two output formats:
- **skill_md** (default): Creates a ``skill-name/SKILL.md`` directory with YAML
  frontmatter, markdown body, and optional ``references/`` directory.  Matches
  the Claude Code skill format.
- **yaml**: Creates a flat ``skill-name.yaml`` file (legacy format).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, ClassVar

import yaml

from zhi.skills.loader import MAX_SKILL_NAME_LENGTH, SKILL_NAME_PATTERN
from zhi.tools.base import BaseTool

_MAX_REFERENCES_SIZE = 50_000


class SkillCreateTool(BaseTool):
    """Create a new skill as a SKILL.md directory or YAML file."""

    name: ClassVar[str] = "skill_create"
    description: ClassVar[str] = (
        "Create a new skill. Default format is SKILL.md (a directory with "
        "markdown instructions and optional reference files). Use format='yaml' "
        "for a simpler flat YAML file."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": (
                    "Skill name. Alphanumeric with hyphens/underscores (max 64 chars)."
                ),
            },
            "description": {
                "type": "string",
                "description": "Human-readable description of what the skill does.",
            },
            "system_prompt": {
                "type": "string",
                "description": (
                    "Instructions for the skill. For skill_md format this becomes "
                    "the markdown body of SKILL.md. For yaml format this is the "
                    "system_prompt field."
                ),
            },
            "tools": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of tool names this skill is allowed to use.",
            },
            "model": {
                "type": "string",
                "description": (
                    "Model to use for skill execution. Default: glm-4-flash."
                ),
            },
            "max_turns": {
                "type": "integer",
                "description": "Maximum agent loop turns. Default: 15.",
            },
            "format": {
                "type": "string",
                "enum": ["skill_md", "yaml"],
                "description": (
                    "Output format. 'skill_md' (default) creates a directory "
                    "with SKILL.md; 'yaml' creates a flat YAML file."
                ),
            },
            "references": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "File paths to copy into the skill's references/ directory. "
                    "Only used with skill_md format."
                ),
            },
            "input_args": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "required": {"type": "boolean"},
                    },
                },
                "description": "Input argument definitions for the skill.",
            },
            "output": {
                "type": "object",
                "description": "Output configuration for the skill",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Description of the skill's output",
                    },
                    "directory": {
                        "type": "string",
                        "description": (
                            "Subdirectory name for output files (default: zhi-output)"
                        ),
                    },
                },
            },
        },
        "required": ["name", "description", "system_prompt", "tools"],
    }
    risky: ClassVar[bool] = True

    def __init__(
        self,
        skills_dir: Path,
        known_tool_names: list[str] | None = None,
        *,
        default_model: str = "glm-4-flash",
    ) -> None:
        self._skills_dir = skills_dir
        self._known_tool_names = known_tool_names or []
        self._default_model = default_model

    def execute(self, **kwargs: Any) -> str:
        skill_name: str = kwargs.get("name", "")
        description: str = kwargs.get("description", "")
        system_prompt: str = kwargs.get("system_prompt", "")
        tools: list[str] = kwargs.get("tools", [])
        model: str = kwargs.get("model", self._default_model)
        max_turns: int = kwargs.get("max_turns", 15)
        fmt: str = kwargs.get("format", "skill_md")
        references: list[str] = kwargs.get("references") or []
        input_args: list[dict[str, Any]] = kwargs.get("input_args") or []
        output: dict[str, Any] | None = kwargs.get("output")

        # ── Validate common fields ──────────────────────────────────
        error = self._validate(skill_name, description, system_prompt, tools)
        if error:
            return error

        # Clamp max_turns
        max_turns = max(1, min(max_turns, 50))

        # Validate format
        if fmt not in ("skill_md", "yaml"):
            return "Error: 'format' must be 'skill_md' or 'yaml'."

        # ── Check for existing skill (both formats) ─────────────────
        self._skills_dir.mkdir(parents=True, exist_ok=True)
        yaml_file = self._skills_dir / f"{skill_name}.yaml"
        md_dir = self._skills_dir / skill_name
        md_file = md_dir / "SKILL.md"

        if yaml_file.exists():
            return (
                f"Error: Skill '{skill_name}' already exists at {yaml_file}. "
                "Choose a different name or delete the existing skill first."
            )
        if md_file.exists():
            return (
                f"Error: Skill '{skill_name}' already exists at {md_dir}. "
                "Choose a different name or delete the existing skill first."
            )

        # ── Create skill ────────────────────────────────────────────
        if fmt == "skill_md":
            return self._create_skill_md(
                skill_name,
                description,
                system_prompt,
                tools,
                model,
                max_turns,
                references,
                input_args,
                output,
                md_dir,
            )
        return self._create_yaml(
            skill_name,
            description,
            system_prompt,
            tools,
            model,
            max_turns,
            output,
            yaml_file,
        )

    # ── Private helpers ─────────────────────────────────────────────

    def _validate(
        self,
        skill_name: str,
        description: str,
        system_prompt: str,
        tools: list[str],
    ) -> str | None:
        """Return an error string if validation fails, else None."""
        if not skill_name:
            return "Error: 'name' parameter is required."

        if len(skill_name) > MAX_SKILL_NAME_LENGTH:
            return (
                f"Error: Skill name too long "
                f"({len(skill_name)} chars). "
                f"Maximum: {MAX_SKILL_NAME_LENGTH}."
            )

        if not SKILL_NAME_PATTERN.match(skill_name):
            return (
                f"Error: Invalid skill name '{skill_name}'. "
                "Must start with alphanumeric and contain "
                "only letters, digits, hyphens, "
                "and underscores."
            )

        if "/" in skill_name or "\\" in skill_name or ".." in skill_name:
            return "Error: Skill name contains invalid characters (path separators)."

        if not description:
            return "Error: 'description' parameter is required."
        if not system_prompt:
            return "Error: 'system_prompt' parameter is required."
        if not tools:
            return "Error: 'tools' parameter is required (at least one tool)."

        if self._known_tool_names:
            unknown = [t for t in tools if t not in self._known_tool_names]
            if unknown:
                return (
                    f"Error: Unknown tools: {', '.join(unknown)}. "
                    f"Available: {', '.join(self._known_tool_names)}"
                )

        return None

    def _create_skill_md(
        self,
        skill_name: str,
        description: str,
        system_prompt: str,
        tools: list[str],
        model: str,
        max_turns: int,
        references: list[str],
        input_args: list[dict[str, Any]],
        output: dict[str, Any] | None,
        skill_dir: Path,
    ) -> str:
        """Create a SKILL.md directory with frontmatter + body + references."""
        # Build frontmatter
        frontmatter: dict[str, Any] = {
            "name": skill_name,
            "description": description,
            "tools": tools,
        }
        if model != self._default_model:
            frontmatter["model"] = model
        if max_turns != 15:
            frontmatter["max_turns"] = max_turns
        if input_args:
            frontmatter["input"] = {"args": input_args}
        if output:
            output_clean = {k: v for k, v in output.items() if v}
            if output_clean:
                frontmatter["output"] = output_clean

        frontmatter_str = yaml.dump(
            frontmatter,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        ).rstrip()

        content = f"---\n{frontmatter_str}\n---\n\n{system_prompt}\n"

        try:
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        except OSError as exc:
            return f"Error: Could not save skill: {exc}"

        # Copy reference files
        copied_refs: list[str] = []
        skipped_refs: list[str] = []
        if references:
            for ref_path_str in references:
                ref_path = Path(ref_path_str).expanduser().resolve()
                if not ref_path.is_file():
                    skipped_refs.append(f"{ref_path.name} (not found)")
                    continue
                try:
                    # Create refs dir lazily on first successful copy
                    refs_dir = skill_dir / "references"
                    refs_dir.mkdir(exist_ok=True)
                    shutil.copy2(ref_path, refs_dir / ref_path.name)
                    copied_refs.append(ref_path.name)
                except OSError:
                    skipped_refs.append(f"{ref_path.name} (read error)")

        result = f"Skill '{skill_name}' created at {skill_dir}/SKILL.md"
        if copied_refs:
            result += f" (references: {', '.join(copied_refs)})"

        # Warn if total reference size exceeds limit
        if copied_refs:
            refs_dir = skill_dir / "references"
            total_size = sum(
                f.stat().st_size for f in refs_dir.iterdir() if f.is_file()
            )
            if total_size > _MAX_REFERENCES_SIZE:
                size_kb = total_size / 1024
                result += (
                    f"\nWarning: Total reference size ({size_kb:.1f}KB) exceeds "
                    f"50KB limit. References will be truncated at load time."
                )

        if skipped_refs:
            result += (
                f"\nNote: {len(skipped_refs)} reference file(s) skipped: "
                + ", ".join(skipped_refs)
            )

        return result

    def _create_yaml(
        self,
        skill_name: str,
        description: str,
        system_prompt: str,
        tools: list[str],
        model: str,
        max_turns: int,
        output: dict[str, Any] | None,
        skill_file: Path,
    ) -> str:
        """Create a flat YAML skill file (legacy format)."""
        skill_data: dict[str, Any] = {
            "name": skill_name,
            "description": description,
            "model": model,
            "system_prompt": system_prompt,
            "tools": tools,
            "max_turns": max_turns,
        }
        if output:
            output_clean = {k: v for k, v in output.items() if v}
            if output_clean:
                skill_data["output"] = output_clean

        try:
            yaml_content = yaml.dump(
                skill_data,
                default_flow_style=False,
                allow_unicode=True,
            )
            skill_file.write_text(yaml_content, encoding="utf-8")
        except OSError as exc:
            return f"Error: Could not save skill: {exc}"

        return f"Skill '{skill_name}' created at {skill_file}"
