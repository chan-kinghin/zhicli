"""Skill discovery and management for zhi."""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

from zhi.skills.loader import SkillConfig, load_skill

logger = logging.getLogger(__name__)

# Path to builtin skills shipped with the package
BUILTIN_SKILLS_DIR = Path(__file__).parent / "builtin"


def _default_user_skills_dir() -> Path:
    """Return the platform-specific user skills directory."""
    import platformdirs

    return Path(platformdirs.user_config_dir("zhi")) / "skills"


def discover_skills(
    builtin_dir: Path | None = None,
    user_dir: Path | None = None,
) -> dict[str, SkillConfig]:
    """Discover skills from builtin and user directories.

    User skills override builtin skills with the same name.
    Corrupted YAML files are skipped with a warning.

    Args:
        builtin_dir: Path to builtin skills. Defaults to package builtin dir.
        user_dir: Path to user skills directory. Defaults to platform config dir.

    Returns:
        Dict mapping skill name to SkillConfig.
    """
    if builtin_dir is None:
        builtin_dir = BUILTIN_SKILLS_DIR
    if user_dir is None:
        user_dir = _default_user_skills_dir()

    skills: dict[str, SkillConfig] = {}

    # Load builtin skills
    skills.update(_scan_directory(builtin_dir, source="builtin"))

    # Load user skills (override builtins)
    skills.update(_scan_directory(user_dir, source="user"))

    return skills


def _scan_directory(directory: Path, source: str) -> dict[str, SkillConfig]:
    """Scan a directory for skill YAML files.

    Skips corrupted files with a warning instead of raising.
    """
    skills: dict[str, SkillConfig] = {}

    if not directory.is_dir():
        return skills

    try:
        yaml_paths = sorted(directory.glob("*.yaml"))
    except OSError as exc:
        logger.warning("Cannot scan skill directory %s: %s", directory, exc)
        return skills

    for yaml_path in yaml_paths:
        try:
            config = load_skill(yaml_path, source=source)
            skills[config.name] = config
        except Exception as exc:
            warnings.warn(
                f"Skipping corrupted skill file {yaml_path}: {exc}",
                stacklevel=2,
            )
            logger.debug("Failed to load skill %s: %s", yaml_path, exc)

    return skills
