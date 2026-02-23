"""Skill creation tool for zhi."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import yaml

from zhi.skills.loader import MAX_SKILL_NAME_LENGTH, SKILL_NAME_PATTERN
from zhi.tools.base import BaseTool


class SkillCreateTool(BaseTool):
    """Create a new skill YAML file."""

    name: ClassVar[str] = "skill_create"
    description: ClassVar[str] = (
        "Create a new skill by generating a YAML configuration file. "
        "Skills define reusable agent workflows with specific tools and prompts."
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
                    "System prompt that guides the model's behavior for this skill."
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
        },
        "required": ["name", "description", "system_prompt", "tools"],
    }
    risky: ClassVar[bool] = True

    def __init__(
        self,
        skills_dir: Path,
        known_tool_names: list[str] | None = None,
    ) -> None:
        """Initialize skill_create tool.

        Args:
            skills_dir: Directory to save skill YAML files.
            known_tool_names: List of valid tool names for validation.
        """
        self._skills_dir = skills_dir
        self._known_tool_names = known_tool_names or []

    def execute(self, **kwargs: Any) -> str:
        skill_name: str = kwargs.get("name", "")
        description: str = kwargs.get("description", "")
        system_prompt: str = kwargs.get("system_prompt", "")
        tools: list[str] = kwargs.get("tools", [])
        model: str = kwargs.get("model", "glm-4-flash")
        max_turns: int = kwargs.get("max_turns", 15)

        # Validate name
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

        # Extra traversal checks
        if "/" in skill_name or "\\" in skill_name or ".." in skill_name:
            return "Error: Skill name contains invalid characters (path separators)."

        if not description:
            return "Error: 'description' parameter is required."
        if not system_prompt:
            return "Error: 'system_prompt' parameter is required."
        if not tools:
            return "Error: 'tools' parameter is required (at least one tool)."

        # Validate tools against known registry
        if self._known_tool_names:
            unknown = [t for t in tools if t not in self._known_tool_names]
            if unknown:
                return (
                    f"Error: Unknown tools: {', '.join(unknown)}. "
                    f"Available: {', '.join(self._known_tool_names)}"
                )

        # Clamp max_turns
        max_turns = max(1, min(max_turns, 50))

        # Build skill data
        skill_data: dict[str, Any] = {
            "name": skill_name,
            "description": description,
            "model": model,
            "system_prompt": system_prompt,
            "tools": tools,
            "max_turns": max_turns,
        }

        # Ensure skills directory exists
        self._skills_dir.mkdir(parents=True, exist_ok=True)

        skill_file = self._skills_dir / f"{skill_name}.yaml"

        if skill_file.exists():
            return (
                f"Error: Skill '{skill_name}' already exists at {skill_file}. "
                "Choose a different name or delete the existing skill first."
            )

        # Write YAML
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
