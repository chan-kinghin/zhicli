"""Parse SKILL.md files (markdown with YAML frontmatter) into SkillConfig."""

from __future__ import annotations

import logging
import re
import warnings
from pathlib import Path
from typing import Any

import yaml

from zhi.errors import SkillError
from zhi.skills.loader import SkillConfig, validate_skill_name

logger = logging.getLogger(__name__)

# Max total size of reference files to inject (100 KB).
_MAX_REFERENCES_SIZE = 100_000

# Frontmatter pattern: --- at start, YAML content, --- delimiter.
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)

# Required frontmatter fields (note: no system_prompt — the body is the prompt).
# tools is optional — skills without tools use disable_model_invocation mode.
_REQUIRED_FIELDS = {"name", "description"}


def load_skill_md(path: Path, *, source: str = "") -> SkillConfig:
    """Load a SKILL.md file and return a SkillConfig.

    The YAML frontmatter provides metadata (name, tools, model, etc.).
    The markdown body becomes the system_prompt.
    If a ``references/`` directory exists alongside the SKILL.md, reference
    file contents are appended to the system_prompt.

    Args:
        path: Path to the SKILL.md file.
        source: Origin label (e.g. "builtin", "user").

    Returns:
        A validated SkillConfig.

    Raises:
        SkillError: If the file is missing, malformed, or invalid.
    """
    if not path.exists():
        raise SkillError(
            f"Skill file not found: {path}",
            code="SKILL_NOT_FOUND",
        )

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SkillError(
            f"Cannot read skill file: {path}",
            code="SKILL_READ_ERROR",
            log_details=str(exc),
        ) from exc

    if not text.strip():
        raise SkillError(
            f"Skill file is empty: {path}",
            code="SKILL_INVALID_YAML",
        )

    # Parse frontmatter
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise SkillError(
            f"SKILL.md must start with YAML frontmatter (---): {path}",
            code="SKILL_INVALID_YAML",
            suggestions=["Add --- delimited YAML frontmatter at the top of the file"],
        )

    frontmatter_text = match.group(1)
    body = match.group(2).strip()

    try:
        data = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        raise SkillError(
            f"Malformed YAML frontmatter in {path}",
            code="SKILL_INVALID_YAML",
            log_details=str(exc),
        ) from exc

    if not isinstance(data, dict):
        raise SkillError(
            f"Frontmatter must be a YAML mapping in {path}",
            code="SKILL_INVALID_YAML",
        )

    # Check required fields
    missing = _REQUIRED_FIELDS - set(data.keys())
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise SkillError(
            f"Missing required frontmatter fields in {path}: {missing_str}",
            code="SKILL_INVALID_YAML",
        )

    # Validate name
    name = data["name"]
    if not validate_skill_name(name):
        raise SkillError(
            f"Invalid skill name: {name!r}",
            code="SKILL_INVALID_NAME",
        )

    # Validate tools (optional — defaults to empty list)
    tools = data.get("tools", [])
    if not isinstance(tools, list):
        raise SkillError(f"'tools' must be a list in {path}", code="SKILL_INVALID_YAML")

    # Validate description
    if not isinstance(data["description"], str):
        raise SkillError(
            f"'description' must be a string in {path}", code="SKILL_INVALID_YAML"
        )

    # Build system_prompt from body + references.
    # Scan for reference files: sibling .md files and all subdirectories
    # (references/, examples/, themes/, etc.)
    system_prompt = body
    ref_content = _load_all_references(path.parent)
    if ref_content:
        system_prompt += "\n\n---\n\n## Reference Files\n\n" + ref_content

    # Extract optional fields
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

    raw_turns = data.get("max_turns", 15)
    if not isinstance(raw_turns, int):
        raw_turns = 15
    max_turns = max(1, min(raw_turns, 50))

    return SkillConfig(
        name=name,
        description=data["description"],
        system_prompt=system_prompt,
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


def _load_all_references(skill_dir: Path) -> str:
    """Load reference files from the skill directory tree.

    Collects:
    - Sibling ``.md`` files next to SKILL.md (excluding SKILL.md itself)
    - All text files in subdirectories (references/, examples/, themes/, etc.)

    Total content is capped at ``_MAX_REFERENCES_SIZE`` bytes.
    """
    sections: list[str] = []
    total_size = 0
    hit_cap = False

    def _add_file(ref_path: Path, label: str) -> None:
        nonlocal total_size, hit_cap
        if hit_cap:
            return
        if ref_path.name.startswith("."):
            return
        try:
            content = ref_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            logger.warning("Cannot read reference file: %s", ref_path)
            return

        if total_size + len(content) > _MAX_REFERENCES_SIZE:
            warnings.warn(
                f"Reference files exceed {_MAX_REFERENCES_SIZE} bytes, "
                f"skipping remaining files after {ref_path.name}",
                stacklevel=2,
            )
            hit_cap = True
            return

        sections.append(f"### {label}\n\n{content}")
        total_size += len(content)

    try:
        # 1. Sibling .md files (exclude SKILL.md)
        for sibling in sorted(skill_dir.iterdir()):
            if not sibling.is_file():
                continue
            if sibling.name == "SKILL.md":
                continue
            if sibling.suffix in (".md", ".txt"):
                _add_file(sibling, sibling.name)

        # 2. All subdirectories (references/, examples/, themes/, etc.)
        for subdir in sorted(skill_dir.iterdir()):
            if not subdir.is_dir():
                continue
            if subdir.name.startswith("."):
                continue
            for ref_path in sorted(subdir.iterdir()):
                if not ref_path.is_file():
                    continue
                if ref_path.suffix in (".md", ".txt"):
                    label = f"{subdir.name}/{ref_path.name}"
                    _add_file(ref_path, label)
    except OSError:
        pass

    return "\n\n".join(sections)
