"""Tests for zhi.cli module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestCliVersion:
    """Test --version flag."""

    def test_version_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        from zhi.cli import main

        main(["--version"])
        captured = capsys.readouterr()
        assert captured.out.startswith("zhi ")

    def test_help_flag(self) -> None:
        from zhi.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0


class TestCliSetup:
    """Test --setup flag."""

    def test_setup_calls_wizard(self) -> None:
        from zhi.cli import main

        with patch("zhi.config.run_wizard") as mock_wizard:
            main(["--setup"])
            mock_wizard.assert_called_once()


class TestCliNoColor:
    """Test --no-color flag."""

    def test_no_color_sets_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import os

        from zhi.cli import main

        monkeypatch.delenv("NO_COLOR", raising=False)
        # Use --setup (processed after --no-color) with a mock to exit cleanly
        with patch("zhi.config.run_wizard"):
            main(["--no-color", "--setup"])
        assert os.environ.get("NO_COLOR") == "1"


class TestCliOneShot:
    """Test -c one-shot mode."""

    def test_oneshot_requires_api_key(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from zhi.cli import main

        monkeypatch.delenv("ZHI_API_KEY", raising=False)
        with patch("zhi.config.load_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(has_api_key=False, log_level="INFO")
            with pytest.raises(SystemExit):
                main(["-c", "hello"])
            captured = capsys.readouterr()
            assert "No API key" in captured.out


class TestCliSkillRun:
    """Test 'run' subcommand."""

    def test_run_requires_api_key(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from zhi.cli import main

        monkeypatch.delenv("ZHI_API_KEY", raising=False)
        with patch("zhi.config.load_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(has_api_key=False, log_level="INFO")
            with pytest.raises(SystemExit):
                main(["run", "summarize"])
            captured = capsys.readouterr()
            assert "No API key" in captured.out

    def test_run_unknown_skill(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from zhi.cli import main

        monkeypatch.delenv("ZHI_API_KEY", raising=False)
        with (
            patch("zhi.config.load_config") as mock_cfg,
            patch("zhi.skills.discover_skills") as mock_discover,
        ):
            mock_cfg.return_value = MagicMock(
                has_api_key=True, api_key="sk-test", log_level="INFO"
            )
            mock_discover.return_value = {}
            with pytest.raises(SystemExit):
                main(["run", "nonexistent"])
            captured = capsys.readouterr()
            assert "Unknown skill" in captured.out


class TestCliBuildContext:
    """Test _build_context helper."""

    def test_build_context_creates_context(self) -> None:
        from zhi.cli import _build_context
        from zhi.config import ZhiConfig

        config = ZhiConfig(api_key="sk-test")
        ui = MagicMock()

        with patch("zhi.client.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()
            ctx = _build_context(config, ui, user_message="hello")

        assert ctx.model == "glm-5"
        assert len(ctx.conversation) == 1
        assert ctx.conversation[0]["content"] == "hello"

    def test_build_context_with_system_prompt(self) -> None:
        from zhi.cli import _build_context
        from zhi.config import ZhiConfig

        config = ZhiConfig(api_key="sk-test")
        ui = MagicMock()

        with patch("zhi.client.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()
            ctx = _build_context(
                config, ui, system_prompt="You are helpful", user_message="hi"
            )

        assert len(ctx.conversation) == 2
        assert ctx.conversation[0]["role"] == "system"
        assert ctx.conversation[1]["role"] == "user"


class TestCliUpdate:
    """Test 'update' subcommand."""

    def test_update_subcommand_calls_perform_update(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from zhi.cli import main

        with patch("zhi.updater.perform_update", return_value=(True, "Up to date")):
            main(["update"])
        captured = capsys.readouterr()
        assert "Up to date" in captured.out

    def test_update_subcommand_exits_1_on_failure(self) -> None:
        from zhi.cli import main

        with (
            patch(
                "zhi.updater.perform_update",
                return_value=(False, "Update failed"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main(["update"])
        assert exc_info.value.code == 1

    def test_update_no_api_key_needed(self, capsys: pytest.CaptureFixture[str]) -> None:
        """update subcommand should work without an API key."""
        from zhi.cli import main

        with patch("zhi.updater.perform_update", return_value=(True, "OK")):
            # No API key set, should still work
            main(["update"])
        captured = capsys.readouterr()
        assert "OK" in captured.out


class TestMaybeCheckUpdate:
    """Test startup update check."""

    def test_check_shows_notice_when_update_available(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from zhi.cli import _maybe_check_update

        config = MagicMock(auto_update_check=True)
        with (
            patch("zhi.__version__", "1.0.0"),
            patch(
                "zhi.updater.check_for_update",
                return_value={"current": "1.0.0", "latest": "2.0.0"},
            ),
            patch("zhi.updater.cleanup_old_exe"),
        ):
            _maybe_check_update(config)
        captured = capsys.readouterr()
        assert "2.0.0" in captured.out

    def test_check_silent_when_up_to_date(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from zhi.cli import _maybe_check_update

        config = MagicMock(auto_update_check=True)
        with (
            patch("zhi.__version__", "1.0.0"),
            patch("zhi.updater.check_for_update", return_value=None),
            patch("zhi.updater.cleanup_old_exe"),
        ):
            _maybe_check_update(config)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_check_skipped_by_env_var(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from zhi.cli import _maybe_check_update

        monkeypatch.setenv("ZHI_NO_UPDATE_CHECK", "1")
        config = MagicMock(auto_update_check=True)
        # Should not even import updater
        _maybe_check_update(config)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_check_skipped_by_config(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from zhi.cli import _maybe_check_update

        monkeypatch.delenv("ZHI_NO_UPDATE_CHECK", raising=False)
        config = MagicMock(auto_update_check=False)
        _maybe_check_update(config)
        captured = capsys.readouterr()
        assert captured.out == ""


class TestRequireApiKey:
    """Test _require_api_key helper."""

    def test_returns_true_with_key(self) -> None:
        from zhi.cli import _require_api_key

        config = MagicMock(has_api_key=True)
        assert _require_api_key(config) is True

    def test_returns_false_without_key(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from zhi.cli import _require_api_key

        config = MagicMock(has_api_key=False, log_level="INFO")
        assert _require_api_key(config) is False
        captured = capsys.readouterr()
        assert "No API key" in captured.out
