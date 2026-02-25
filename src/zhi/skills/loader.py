"""Parse and validate skill YAML files."""

from __future__ import annotations

import logging
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from zhi.errors import SkillError

logger = logging.getLogger(__name__)

SKILL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
MAX_SKILL_NAME_LENGTH = 64

REQUIRED_FIELDS = {"name", "description", "system_prompt", "tools"}


@dataclass
class SkillConfig:
    """Parsed and validated skill configuration."""

    name: str
    description: str
    system_prompt: str
    tools: list[str]
    model: str = "glm-4-flash"
    max_turns: int = 15
    input_args: list[dict[str, Any]] = field(default_factory=list)
    output_description: str = ""
    output_directory: str = "zhi-output"
    source: str = ""
    version: str = ""
    disable_model_invocation: bool = False


def validate_skill_name(name: str) -> bool:
    """Validate a skill name against the allowed pattern.

    Names must match ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ and be at most 64 chars.
    Path separators and traversal patterns are rejected.
    """
    if not isinstance(name, str):
        return False
    if len(name) == 0 or len(name) > MAX_SKILL_NAME_LENGTH:
        return False
    return bool(SKILL_NAME_PATTERN.match(name))


def load_skill(path: Path, *, source: str = "") -> SkillConfig:
    """Load and validate a skill YAML file.

    Args:
        path: Path to the YAML file.
        source: Origin label (e.g. "builtin", "user"). Stored in the config.

    Returns:
        A validated SkillConfig.

    Raises:
        SkillError: If the file is missing, empty, malformed, or invalid.
    """
    if not path.exists():
        raise SkillError(
            f"Skill file not found: {path}",
            code="SKILL_NOT_FOUND",
            suggestions=["Check the file path"],
        )

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SkillError(
            f"Cannot read skill file: {path}",
            code="SKILL_READ_ERROR",
            suggestions=["Check file permissions"],
            log_details=str(exc),
        ) from exc

    if not raw:
        raise SkillError(
            f"Skill file is empty: {path}",
            code="SKILL_INVALID_YAML",
            suggestions=["Add skill configuration to the file"],
        )

    # Reject likely binary files (check for null bytes)
    if b"\x00" in raw:
        raise SkillError(
            f"Skill file appears to be binary: {path}",
            code="SKILL_INVALID_YAML",
            suggestions=["Skill files must be valid YAML text files"],
        )

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise SkillError(
            f"Malformed YAML in skill file: {path}",
            code="SKILL_INVALID_YAML",
            suggestions=[
                "Check the file for syntax errors",
                "Ensure proper YAML indentation",
            ],
            log_details=str(exc),
        ) from exc

    if not isinstance(data, dict):
        raise SkillError(
            f"Skill file must contain a YAML mapping: {path}",
            code="SKILL_INVALID_YAML",
            suggestions=["The top-level structure must be a key-value mapping"],
        )

    # Check required fields
    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        raise SkillError(
            f"Missing required fields in {path}: {', '.join(sorted(missing))}",
            code="SKILL_INVALID_YAML",
            suggestions=[f"Add the following fields: {', '.join(sorted(missing))}"],
        )

    # Validate skill name
    name = data["name"]
    if not validate_skill_name(name):
        raise SkillError(
            f"Invalid skill name: {name!r}",
            code="SKILL_INVALID_NAME",
            suggestions=[
                "Skill names must match [a-zA-Z0-9][a-zA-Z0-9_-]* (max 64 chars)",
                "Avoid spaces, slashes, and special characters",
            ],
        )

    # Validate description is a string (Bug 16)
    if not isinstance(data["description"], str):
        raise SkillError(
            f"'description' must be a string in {path}",
            code="SKILL_INVALID_YAML",
            suggestions=["Provide a text description for the skill"],
        )

    # Validate system_prompt is a string (Bug 16)
    if not isinstance(data["system_prompt"], str):
        raise SkillError(
            f"'system_prompt' must be a string in {path}",
            code="SKILL_INVALID_YAML",
            suggestions=["Provide a text system prompt for the skill"],
        )

    # Validate tools is a list
    tools = data["tools"]
    if not isinstance(tools, list):
        raise SkillError(
            f"'tools' must be a list in {path}",
            code="SKILL_INVALID_YAML",
            suggestions=["Specify tools as a YAML list: tools: [file_read]"],
        )

    # Warn about unknown fields
    known_fields = {
        "name",
        "description",
        "system_prompt",
        "tools",
        "model",
        "max_turns",
        "input",
        "output",
        "version",
        "disable-model-invocation",
    }
    unknown = set(data.keys()) - known_fields
    if unknown:
        warnings.warn(
            f"Unknown fields in {path} will be ignored: {', '.join(sorted(unknown))}",
            stacklevel=2,
        )

    # Extract optional input/output sections
    input_section = data.get("input", {})
    input_args: list[dict[str, Any]] = []
    if isinstance(input_section, dict):
        input_args = input_section.get("args", [])
        if not isinstance(input_args, list):
            input_args = []

    output_section = data.get("output", {})
    output_description = ""
    output_directory = "zhi-output"
    if isinstance(output_section, dict):
        output_description = output_section.get("description", "")
        output_directory = output_section.get("directory", "zhi-output")

    # Validate and clamp max_turns (Bug 10)
    raw_turns = data.get("max_turns", 15)
    if not isinstance(raw_turns, int):
        raw_turns = 15
    max_turns = max(1, min(raw_turns, 50))

    return SkillConfig(
        name=name,
        description=data["description"],
        system_prompt=data["system_prompt"],
        tools=[str(t) for t in tools],
        model=data.get("model", "glm-4-flash"),
        max_turns=max_turns,
        input_args=input_args,
        output_description=output_description,
        output_directory=output_directory,
        source=source,
        version=data.get("version", ""),
        disable_model_invocation=bool(data.get("disable-model-invocation", False)),
    )
