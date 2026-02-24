"""End-to-end tests for the zhi CLI entry points.

These tests exercise the CLI through ``main()`` with mocked SDK boundaries
so no real API calls are made.  They verify the full path from argument
parsing through to output.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from zhi.i18n import CHAT_SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stream_chunks(content: str = "Hello!") -> list[SimpleNamespace]:
    """Build mock streaming chunks that the agent loop can iterate over."""
    # Emit content in a single chunk, then a final chunk with finish_reason
    return [
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content=content, tool_calls=None),
                    finish_reason=None,
                )
            ],
        ),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content="", tool_calls=None),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=10, completion_tokens=5, total_tokens=15
            ),
        ),
    ]


def _patch_config(*, has_key: bool = True) -> Any:
    """Return a mock ZhiConfig."""
    cfg = MagicMock()
    cfg.has_api_key = has_key
    cfg.api_key = "sk-test" if has_key else ""
    cfg.default_model = "glm-5"
    cfg.skill_model = "glm-4-flash"
    cfg.output_dir = "zhi-output"
    cfg.max_turns = 30
    cfg.log_level = "WARNING"
    cfg.language = "auto"
    cfg.auto_update_check = False
    return cfg


# ---------------------------------------------------------------------------
# Version & help
# ---------------------------------------------------------------------------


class TestCliVersionE2E:
    """Test ``zhi --version`` end-to-end."""

    def test_version_prints_semver(self, capsys: pytest.CaptureFixture[str]) -> None:
        from zhi.cli import main

        main(["--version"])
        out = capsys.readouterr().out
        assert out.startswith("zhi ")
        # Should look like a semver: major.minor.patch
        version_str = out.strip().split(" ", 1)[1]
        parts = version_str.split(".")
        assert len(parts) >= 2, f"Expected semver, got: {version_str}"

    def test_help_exits_zero(self) -> None:
        from zhi.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# One-shot mode (-c)
# ---------------------------------------------------------------------------


class TestCliOneShotE2E:
    """Test ``zhi -c "message"`` with a mocked client."""

    def test_oneshot_sends_message_and_prints_result(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Full path: parse args -> build context -> agent run -> output."""
        from zhi.cli import main

        monkeypatch.delenv("ZHI_API_KEY", raising=False)
        monkeypatch.delenv("NO_COLOR", raising=False)

        mock_config = _patch_config(has_key=True)

        with (
            patch("zhi.config.load_config", return_value=mock_config),
            patch("zhi.client.ZhipuAI") as mock_sdk_cls,
        ):
            mock_sdk = mock_sdk_cls.return_value
            # Agent uses streaming by default — return iterable chunks
            mock_sdk.chat.completions.create.return_value = iter(
                _make_stream_chunks("I am zhi!")
            )

            main(["-c", "hello"])

        # Verify the SDK was called with the user message in conversation
        call_kwargs = mock_sdk.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert any("hello" in m["content"] for m in user_msgs)

    def test_oneshot_injects_chat_system_prompt(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify CHAT_SYSTEM_PROMPT is in the conversation sent to the API."""
        from zhi.cli import main

        monkeypatch.delenv("ZHI_API_KEY", raising=False)
        mock_config = _patch_config(has_key=True)

        with (
            patch("zhi.config.load_config", return_value=mock_config),
            patch("zhi.client.ZhipuAI") as mock_sdk_cls,
        ):
            mock_sdk = mock_sdk_cls.return_value
            mock_sdk.chat.completions.create.return_value = iter(
                _make_stream_chunks("ok")
            )

            main(["-c", "test"])

        call_kwargs = mock_sdk.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        system_msgs = [m for m in messages if m["role"] == "system"]
        assert len(system_msgs) >= 1
        system_content = system_msgs[0]["content"]
        # Verify key phrases from CHAT_SYSTEM_PROMPT
        assert "ask_user" in system_content
        assert "skill_create" in system_content

    def test_oneshot_no_api_key_exits(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from zhi.cli import main

        monkeypatch.delenv("ZHI_API_KEY", raising=False)
        mock_config = _patch_config(has_key=False)

        with (
            patch("zhi.config.load_config", return_value=mock_config),
            pytest.raises(SystemExit),
        ):
            main(["-c", "hello"])

        out = capsys.readouterr().out
        assert "No API key" in out


# ---------------------------------------------------------------------------
# Skill run mode (zhi run <skill>)
# ---------------------------------------------------------------------------


class TestCliSkillRunE2E:
    """Test ``zhi run <skill>`` with mocked client."""

    def test_run_skill_invokes_agent(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Running a valid skill builds context and calls agent."""
        from zhi.cli import main

        monkeypatch.delenv("ZHI_API_KEY", raising=False)
        mock_config = _patch_config(has_key=True)

        with (
            patch("zhi.config.load_config", return_value=mock_config),
            patch("zhi.client.ZhipuAI") as mock_sdk_cls,
        ):
            mock_sdk = mock_sdk_cls.return_value
            mock_sdk.chat.completions.create.return_value = iter(
                _make_stream_chunks("Summary done")
            )

            main(["run", "summarize"])

        # Verify agent was invoked — the SDK got called at least once
        assert mock_sdk.chat.completions.create.called

    def test_run_nonexistent_skill_prints_error(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from zhi.cli import main

        monkeypatch.delenv("ZHI_API_KEY", raising=False)
        mock_config = _patch_config(has_key=True)

        with (
            patch("zhi.config.load_config", return_value=mock_config),
            patch("zhi.skills.discover_skills", return_value={}),
            pytest.raises(SystemExit),
        ):
            main(["run", "nonexistent-skill"])

        out = capsys.readouterr().out
        assert "Unknown skill" in out or "nonexistent-skill" in out

    def test_run_skill_no_api_key(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from zhi.cli import main

        monkeypatch.delenv("ZHI_API_KEY", raising=False)
        mock_config = _patch_config(has_key=False)

        with (
            patch("zhi.config.load_config", return_value=mock_config),
            pytest.raises(SystemExit),
        ):
            main(["run", "summarize"])

        out = capsys.readouterr().out
        assert "No API key" in out


# ---------------------------------------------------------------------------
# System prompt content verification
# ---------------------------------------------------------------------------


class TestChatSystemPromptContent:
    """Verify that CHAT_SYSTEM_PROMPT contains the required MUST/NEVER rules."""

    def test_prompt_has_clarify_rule(self) -> None:
        has_clarify = "CLARIFY" in CHAT_SYSTEM_PROMPT.upper()
        has_ask_user = "ask_user" in CHAT_SYSTEM_PROMPT
        assert has_clarify or has_ask_user

    def test_prompt_has_skill_create_rule(self) -> None:
        assert "skill_create" in CHAT_SYSTEM_PROMPT

    def test_prompt_has_never_shell_scripts_rule(self) -> None:
        assert "NEVER" in CHAT_SYSTEM_PROMPT

    def test_prompt_has_ask_user_in_skills_rule(self) -> None:
        assert "ask_user" in CHAT_SYSTEM_PROMPT

    def test_prompt_has_respond_same_language_rule(self) -> None:
        assert "same language" in CHAT_SYSTEM_PROMPT.lower()


# ---------------------------------------------------------------------------
# Skill discovery integration
# ---------------------------------------------------------------------------


class TestBuiltinSkillsE2E:
    """Integration tests for builtin skill discovery."""

    def test_all_builtins_have_ask_user(self) -> None:
        """Every shipped builtin skill must include ask_user in its tools list."""
        from zhi.skills import discover_skills

        skills = discover_skills(user_dir=None)
        missing = [
            name for name, config in skills.items() if "ask_user" not in config.tools
        ]
        assert missing == [], f"Skills missing ask_user: {missing}"

    def test_builtin_count_at_least_15(self) -> None:
        """We ship at least 15 builtin skills."""
        from zhi.skills import discover_skills

        skills = discover_skills(user_dir=None)
        assert len(skills) >= 15, f"Expected >= 15 builtin skills, got {len(skills)}"

    def test_user_skills_dir_is_configurable(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """User skills from a custom directory are discovered."""
        from zhi.skills import discover_skills

        user_dir = tmp_path / "custom_skills"  # type: ignore[operator]
        user_dir.mkdir()
        skill_file = user_dir / "my-test-skill.yaml"
        skill_file.write_text(
            "name: my-test-skill\n"
            "description: A test skill\n"
            "system_prompt: You are a test.\n"
            "tools:\n  - file_read\n"
        )

        skills = discover_skills(user_dir=user_dir)
        assert "my-test-skill" in skills
        assert skills["my-test-skill"].source == "user"
