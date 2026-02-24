"""Tests for zhi.config module."""

from __future__ import annotations

import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from zhi.config import ZhiConfig, get_config_dir, load_config, run_wizard, save_config


class TestZhiConfig:
    """Test ZhiConfig dataclass."""

    def test_config_defaults(self) -> None:
        cfg = ZhiConfig()
        assert cfg.api_key == ""
        assert cfg.default_model == "glm-5"
        assert cfg.skill_model == "glm-4-flash"
        assert cfg.output_dir == "zhi-output"
        assert cfg.max_turns == 30
        assert cfg.log_level == "INFO"
        assert cfg.auto_update_check is True

    def test_has_api_key_false_when_empty(self) -> None:
        cfg = ZhiConfig()
        assert not cfg.has_api_key

    def test_has_api_key_true_when_set(self) -> None:
        cfg = ZhiConfig(api_key="sk-test")
        assert cfg.has_api_key

    def test_validate_missing_api_key(self) -> None:
        cfg = ZhiConfig()
        warnings = cfg.validate()
        assert any("API key" in w for w in warnings)

    def test_validate_max_turns_clamped(self) -> None:
        cfg = ZhiConfig(api_key="sk-test", max_turns=200)
        warnings = cfg.validate()
        assert any("max_turns" in w for w in warnings)
        assert cfg.max_turns == 100

    def test_validate_max_turns_negative_clamped(self) -> None:
        cfg = ZhiConfig(api_key="sk-test", max_turns=-5)
        warnings = cfg.validate()
        assert any("max_turns" in w for w in warnings)
        assert cfg.max_turns == 1

    def test_validate_invalid_log_level(self) -> None:
        cfg = ZhiConfig(api_key="sk-test", log_level="VERBOSE")
        warnings = cfg.validate()
        assert any("log_level" in w for w in warnings)
        assert cfg.log_level == "INFO"

    def test_validate_no_warnings_when_valid(self) -> None:
        cfg = ZhiConfig(api_key="sk-test")
        warnings = cfg.validate()
        assert warnings == []


class TestLoadConfig:
    """Test config loading from file and env vars."""

    def test_load_config_from_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump({"api_key": "sk-test123", "default_model": "glm-5"})
        )

        cfg = load_config(config_dir=tmp_path)
        assert cfg.api_key == "sk-test123"
        assert cfg.default_model == "glm-5"

    def test_load_config_env_var_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"api_key": "sk-fromfile"}))
        monkeypatch.setenv("ZHI_API_KEY", "sk-fromenv")

        cfg = load_config(config_dir=tmp_path)
        assert cfg.api_key == "sk-fromenv"

    def test_load_config_env_var_only(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ZHI_API_KEY", "sk-envonly")

        cfg = load_config(config_dir=tmp_path)
        assert cfg.api_key == "sk-envonly"

    def test_load_config_env_model_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"api_key": "sk-test"}))
        monkeypatch.setenv("ZHI_DEFAULT_MODEL", "glm-4-flash")

        cfg = load_config(config_dir=tmp_path)
        assert cfg.default_model == "glm-4-flash"

    def test_load_config_env_output_dir_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ZHI_OUTPUT_DIR", "/custom/output")

        cfg = load_config(config_dir=tmp_path)
        assert cfg.output_dir == "/custom/output"

    def test_load_config_env_log_level_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ZHI_LOG_LEVEL", "DEBUG")

        cfg = load_config(config_dir=tmp_path)
        assert cfg.log_level == "DEBUG"

    def test_load_config_missing_all(self, tmp_path: Path) -> None:
        cfg = load_config(config_dir=tmp_path)
        assert cfg.api_key == ""
        assert cfg.default_model == "glm-5"

    def test_config_yaml_parse_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text(":::invalid yaml{{{")

        cfg = load_config(config_dir=tmp_path)
        assert cfg.api_key == ""  # Falls back to defaults

    def test_config_partial_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"api_key": "sk-partial"}))

        cfg = load_config(config_dir=tmp_path)
        assert cfg.api_key == "sk-partial"
        assert cfg.default_model == "glm-5"  # Default
        assert cfg.output_dir == "zhi-output"  # Default

    def test_config_unknown_keys_ignored(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump({"api_key": "sk-test", "unknown_key": "value"})
        )

        cfg = load_config(config_dir=tmp_path)
        assert cfg.api_key == "sk-test"
        assert not hasattr(cfg, "unknown_key")

    def test_config_non_dict_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("just a string")

        cfg = load_config(config_dir=tmp_path)
        assert cfg.api_key == ""


class TestSaveConfig:
    """Test config saving."""

    def test_save_config(self, tmp_path: Path) -> None:
        cfg = ZhiConfig(api_key="sk-saved")
        save_config(cfg, config_dir=tmp_path)
        saved = yaml.safe_load((tmp_path / "config.yaml").read_text())
        assert saved["api_key"] == "sk-saved"

    def test_save_config_creates_dir(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "nested" / "config"
        cfg = ZhiConfig(api_key="sk-test")
        save_config(cfg, config_dir=config_dir)
        assert (config_dir / "config.yaml").exists()

    def test_save_config_permissions(self, tmp_path: Path) -> None:
        cfg = ZhiConfig(api_key="sk-test")
        path = save_config(cfg, config_dir=tmp_path)
        mode = path.stat().st_mode
        # Owner read/write only (0o600)
        assert mode & stat.S_IRUSR  # Owner can read
        assert mode & stat.S_IWUSR  # Owner can write
        assert not (mode & stat.S_IRGRP)  # Group cannot read
        assert not (mode & stat.S_IROTH)  # Others cannot read

    def test_save_config_returns_path(self, tmp_path: Path) -> None:
        cfg = ZhiConfig(api_key="sk-test")
        path = save_config(cfg, config_dir=tmp_path)
        assert path == tmp_path / "config.yaml"

    def test_save_config_all_fields(self, tmp_path: Path) -> None:
        cfg = ZhiConfig(
            api_key="sk-test",
            default_model="glm-4-flash",
            skill_model="glm-4-air",
            output_dir="custom-output",
            max_turns=10,
            log_level="DEBUG",
        )
        save_config(cfg, config_dir=tmp_path)
        saved = yaml.safe_load((tmp_path / "config.yaml").read_text())
        assert saved["api_key"] == "sk-test"
        assert saved["default_model"] == "glm-4-flash"
        assert saved["skill_model"] == "glm-4-air"
        assert saved["output_dir"] == "custom-output"
        assert saved["max_turns"] == 10
        assert saved["log_level"] == "DEBUG"


class TestGetConfigDir:
    """Test config directory resolution."""

    def test_get_config_dir_returns_path(self) -> None:
        result = get_config_dir()
        assert isinstance(result, Path)
        assert "zhi" in str(result)


class TestWizardDemo:
    """Test wizard demo Step 3 behavior."""

    def _run_wizard_with_inputs(
        self,
        tmp_path: Path,
        inputs: list[str],
        mock_client: Any = None,
    ) -> ZhiConfig:
        """Helper to run wizard with mocked inputs and optional mocked client."""
        input_iter = iter(inputs)

        with patch("builtins.input", side_effect=lambda _prompt="": next(input_iter)):
            if mock_client is not None:
                with patch("zhi.client.Client", return_value=mock_client):
                    return run_wizard(config_dir=tmp_path)
            else:
                # Patch Client to avoid real API calls even when not expecting one
                with patch("zhi.client.Client"):
                    return run_wizard(config_dir=tmp_path)

    def test_demo_success(self, tmp_path: Path) -> None:
        """Demo makes API call and shows response when key is provided."""

        @dataclass
        class FakeResponse:
            content: str = "Hello from GLM!"
            tool_calls: list[Any] = field(default_factory=list)

        mock_client = MagicMock()
        mock_client.chat.return_value = FakeResponse()

        # Inputs: api_key, model, skill_model, output_dir, language, demo (y)
        cfg = self._run_wizard_with_inputs(
            tmp_path,
            ["sk-test-key", "", "", "", "", "y"],
            mock_client=mock_client,
        )

        assert cfg.api_key == "sk-test-key"
        mock_client.chat.assert_called_once()

    def test_demo_no_key_skips(self, tmp_path: Path) -> None:
        """Demo is skipped when no API key is provided."""
        # Inputs: empty key, model, skill_model, output_dir, language, demo (y)
        cfg = self._run_wizard_with_inputs(
            tmp_path,
            ["", "", "", "", "", "y"],
        )

        assert cfg.api_key == ""

    def test_demo_declined(self, tmp_path: Path) -> None:
        """Demo is skipped when user declines."""
        cfg = self._run_wizard_with_inputs(
            tmp_path,
            ["sk-test", "", "", "", "", "n"],
        )

        assert cfg.api_key == "sk-test"

    def test_demo_api_error_handled(self, tmp_path: Path) -> None:
        """Demo handles API errors gracefully."""
        mock_client = MagicMock()
        mock_client.chat.side_effect = Exception("Connection refused")

        # Should not raise
        cfg = self._run_wizard_with_inputs(
            tmp_path,
            ["sk-test-key", "", "", "", "", "y"],
            mock_client=mock_client,
        )

        assert cfg.api_key == "sk-test-key"
