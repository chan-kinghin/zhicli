"""Configuration management for zhi.

Loads config from platform-specific config directory with env var fallback.
Priority: env vars > config file > defaults.
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import platformdirs
import yaml

from zhi.i18n import set_language, t

logger = logging.getLogger(__name__)

_APP_NAME = "zhi"


def get_config_dir() -> Path:
    """Get platform-specific config directory.

    macOS: ~/Library/Application Support/zhi/
    Windows: %APPDATA%/zhi/
    Linux: ~/.config/zhi/
    """
    return Path(platformdirs.user_config_dir(_APP_NAME))


@dataclass
class ZhiConfig:
    """Configuration for zhi CLI."""

    api_key: str = ""
    default_model: str = "glm-5"
    skill_model: str = "glm-4-flash"
    output_dir: str = "zhi-output"
    max_turns: int = 30
    log_level: str = "INFO"
    language: str = "auto"

    def validate(self) -> list[str]:
        """Validate config and return list of warnings."""
        warnings: list[str] = []
        if not self.api_key:
            warnings.append("API key is not set")
        if self.max_turns < 1 or self.max_turns > 100:
            warnings.append(f"max_turns should be 1-100, got {self.max_turns}")
            self.max_turns = max(1, min(100, self.max_turns))
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            warnings.append(f"Unknown log_level '{self.log_level}', using INFO")
            self.log_level = "INFO"
        return warnings

    @property
    def has_api_key(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)


def load_config(config_dir: Path | None = None) -> ZhiConfig:
    """Load config from YAML file with env var overrides.

    Priority: env vars > config file > defaults.
    """
    if config_dir is None:
        config_dir = get_config_dir()

    config_file = config_dir / "config.yaml"
    data: dict[str, object] = {}

    if config_file.exists():
        try:
            raw = yaml.safe_load(config_file.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data = raw
            else:
                logger.warning("Config file is not a YAML mapping, using defaults")
        except yaml.YAMLError as exc:
            logger.warning("Failed to parse config file: %s", exc)

    # Apply env var overrides
    env_mappings = {
        "ZHI_API_KEY": "api_key",
        "ZHI_DEFAULT_MODEL": "default_model",
        "ZHI_OUTPUT_DIR": "output_dir",
        "ZHI_LOG_LEVEL": "log_level",
        "ZHI_LANGUAGE": "language",
    }
    for env_var, config_key in env_mappings.items():
        value = os.environ.get(env_var)
        if value:
            data[config_key] = value

    # Build config, ignoring unknown keys
    known_fields = {f.name for f in ZhiConfig.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in known_fields}

    return ZhiConfig(**filtered)


def save_config(config: ZhiConfig, config_dir: Path | None = None) -> Path:
    """Save config to YAML file with restrictive permissions.

    Returns path to saved file.
    """
    if config_dir is None:
        config_dir = get_config_dir()

    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.yaml"

    data = asdict(config)
    config_file.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    # Set restrictive permissions (owner-only read/write)
    try:
        config_file.chmod(0o600)
    except OSError as exc:
        logger.warning(
            "Could not set restrictive permissions on %s: %s. "
            "API key may be readable by other users.",
            config_file,
            exc,
        )

    return config_file


def run_wizard(config_dir: Path | None = None) -> ZhiConfig:
    """Run the first-time setup wizard.

    Prompts for API key, defaults, and optionally runs a demo.
    Returns the configured ZhiConfig.
    """
    if config_dir is None:
        config_dir = get_config_dir()

    from zhi import __version__

    print(t("setup.welcome", version=__version__))
    print()
    print(t("setup.intro"))
    print()

    # Step 1: API Key
    print(t("setup.step1"))
    print(t("setup.step1_prompt"))
    api_key = input("  > ").strip()

    if not api_key:
        print(t("setup.no_key"))
        api_key = ""

    # Step 2: Defaults
    print()
    print(t("setup.step2"))
    default_model = input(t("setup.model_prompt")).strip() or "glm-5"
    skill_model = input(t("setup.skill_model_prompt")).strip() or "glm-4-flash"
    output_dir = input(t("setup.output_prompt")).strip() or "zhi-output"
    language = input(t("setup.language_prompt")).strip() or "auto"

    # Step 3: Demo
    print()
    print(t("setup.step3"))
    run_demo = input(t("setup.demo_prompt")).strip().lower()
    if run_demo in ("", "y", "yes"):
        print(t("setup.demo_skip"))

    config = ZhiConfig(
        api_key=api_key,
        default_model=default_model,
        skill_model=skill_model,
        output_dir=output_dir,
        language=language,
    )
    save_config(config, config_dir=config_dir)

    # Apply language setting immediately
    if language != "auto":
        set_language(language)

    print()
    print(t("setup.complete"))
    return config
