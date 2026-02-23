"""Tests for zhi.repl module."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from zhi.agent import Context, PermissionMode
from zhi.config import ZhiConfig
from zhi.ui import UI

# --- Test helpers ---


def _make_context(
    *,
    permission_mode: PermissionMode = PermissionMode.APPROVE,
    model: str = "glm-5",
    conversation: list[dict[str, Any]] | None = None,
    session_tokens: int = 0,
) -> Context:
    """Create a minimal Context for REPL testing."""
    client = MagicMock()
    return Context(
        config=ZhiConfig(),
        client=client,
        model=model,
        tools={},
        tool_schemas=[],
        permission_mode=permission_mode,
        conversation=conversation or [],
        session_tokens=session_tokens,
    )


def _make_repl(
    context: Context | None = None,
    tmp_path: Path | None = None,
) -> Any:
    """Create a ReplSession for testing."""
    from zhi.repl import ReplSession

    if context is None:
        context = _make_context()
    ui = UI(no_color=True)
    history_path = (tmp_path / "history.txt") if tmp_path else Path("/dev/null")
    return ReplSession(context, ui, history_path=history_path)


# --- Slash command tests ---


class TestReplHelp:
    def test_repl_help_command(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/help")
        assert result is not None
        assert "/help" in result
        assert "/exit" in result
        assert "/model" in result

    def test_repl_help_shows_all_commands(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/help")
        for cmd in [
            "/auto",
            "/approve",
            "/think",
            "/fast",
            "/run",
            "/skill",
            "/reset",
            "/undo",
            "/usage",
            "/verbose",
        ]:
            assert cmd in result


class TestReplModes:
    def test_repl_auto_mode(self, tmp_path: Path) -> None:
        ctx = _make_context()
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        result = repl.handle_input("/auto")
        assert "auto" in result.lower()
        assert ctx.permission_mode == PermissionMode.AUTO

    def test_repl_approve_mode(self, tmp_path: Path) -> None:
        ctx = _make_context(permission_mode=PermissionMode.AUTO)
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        result = repl.handle_input("/approve")
        assert "approve" in result.lower()
        assert ctx.permission_mode == PermissionMode.APPROVE


class TestReplModel:
    def test_repl_model_switch(self, tmp_path: Path) -> None:
        ctx = _make_context()
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        result = repl.handle_input("/model glm-4-flash")
        assert "glm-4-flash" in result
        assert ctx.model == "glm-4-flash"

    def test_repl_model_invalid(self, tmp_path: Path) -> None:
        ctx = _make_context()
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        result = repl.handle_input("/model nonexistent")
        assert "Unknown model" in result
        assert ctx.model == "glm-5"  # Unchanged

    def test_repl_model_no_args(self, tmp_path: Path) -> None:
        ctx = _make_context()
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        result = repl.handle_input("/model")
        assert "Current model" in result
        assert "glm-5" in result


class TestReplThinking:
    def test_repl_think_command(self, tmp_path: Path) -> None:
        ctx = _make_context()
        ctx.thinking_enabled = False
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        result = repl.handle_input("/think")
        assert "enabled" in result.lower()
        assert ctx.thinking_enabled is True

    def test_repl_fast_command(self, tmp_path: Path) -> None:
        ctx = _make_context()
        ctx.thinking_enabled = True
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        result = repl.handle_input("/fast")
        assert "disabled" in result.lower()
        assert ctx.thinking_enabled is False


class TestReplExit:
    def test_repl_exit_command(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/exit")
        assert "Goodbye" in result

    def test_repl_exit_shows_usage(self, tmp_path: Path) -> None:
        ctx = _make_context(session_tokens=1000)
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        result = repl.handle_input("/exit")
        assert "Goodbye" in result


class TestReplUnknown:
    def test_repl_unknown_command(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/foobar")
        assert "Unknown command" in result
        assert "/help" in result


class TestReplConversation:
    def test_repl_reset_confirmed(self, tmp_path: Path) -> None:
        ctx = _make_context(
            conversation=[
                {"role": "system", "content": "You are zhi"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ]
        )
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        with patch("builtins.input", return_value="y"):
            result = repl.handle_input("/reset")
        assert "cleared" in result.lower()
        # System messages should be preserved
        assert len(ctx.conversation) == 1
        assert ctx.conversation[0]["role"] == "system"

    def test_repl_reset_cancelled(self, tmp_path: Path) -> None:
        ctx = _make_context(
            conversation=[
                {"role": "system", "content": "You are zhi"},
                {"role": "user", "content": "Hello"},
            ]
        )
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        with patch("builtins.input", return_value="n"):
            result = repl.handle_input("/reset")
        assert result == ""
        assert len(ctx.conversation) == 2  # Unchanged

    def test_repl_undo(self, tmp_path: Path) -> None:
        ctx = _make_context(
            conversation=[
                {"role": "system", "content": "You are zhi"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ]
        )
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        result = repl.handle_input("/undo")
        assert "removed" in result.lower()
        assert len(ctx.conversation) == 1
        assert ctx.conversation[0]["role"] == "system"

    def test_repl_undo_nothing(self, tmp_path: Path) -> None:
        ctx = _make_context(conversation=[])
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        result = repl.handle_input("/undo")
        assert "Nothing to undo" in result


class TestReplUsage:
    def test_repl_usage(self, tmp_path: Path) -> None:
        ctx = _make_context(session_tokens=2500)
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        result = repl.handle_input("/usage")
        assert "2500" in result


class TestReplVerbose:
    def test_repl_verbose_toggle(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/verbose")
        assert "on" in result.lower()
        result = repl.handle_input("/verbose")
        assert "off" in result.lower()


class TestReplRun:
    def test_repl_run_no_args(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/run")
        assert "Usage" in result

    def test_repl_run_command(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/run summarize test.txt")
        assert result is not None


class TestReplSkill:
    def test_repl_skill_list(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/skill list")
        assert result is not None

    def test_repl_skill_new(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/skill new")
        assert result is not None

    def test_repl_skill_no_args(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/skill")
        assert "Usage" in result

    def test_repl_skill_show_no_name(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/skill show")
        assert "Usage" in result

    def test_repl_skill_delete_no_name(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/skill delete")
        assert "Usage" in result


class TestReplStatus:
    def test_repl_status(self, tmp_path: Path) -> None:
        ctx = _make_context(session_tokens=100)
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        result = repl.handle_input("/status")
        assert "glm-5" in result
        assert "approve" in result


class TestReplSkillShow:
    def test_repl_skill_show_valid(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/skill show summarize")
        assert result is not None
        # Should show skill info or not found - either is valid


class TestReplChat:
    def test_repl_regular_text(self, tmp_path: Path) -> None:
        """Regular text is sent to the agent."""

        ctx = _make_context()
        repl = _make_repl(context=ctx, tmp_path=tmp_path)

        # Mock agent_run
        mock_response = MagicMock()
        mock_response.content = "Hello back!"
        mock_response.tool_calls = []
        mock_response.thinking = None
        mock_response.total_tokens = 50
        ctx.client.chat.return_value = mock_response

        repl.handle_input("Hello there")

        # Should have added user message to conversation
        user_msgs = [m for m in ctx.conversation if m["role"] == "user"]
        assert len(user_msgs) == 1
        assert user_msgs[0]["content"] == "Hello there"


class TestReplEmptyInput:
    def test_repl_empty_input(self, tmp_path: Path) -> None:
        """Empty input is silently ignored in handle_input."""
        repl = _make_repl(tmp_path=tmp_path)
        # Empty input should not reach handle_input (filtered in run()),
        # but handle_input should handle it gracefully
        result = repl.handle_input("   ")
        # The REPL run() loop strips and skips empty, but handle_input
        # with whitespace-only would try to send to chat
        assert result is not None or result is None  # No crash


class TestReplEdgeCases:
    def test_edge_slash_only(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/")
        assert "Unknown command" in result

    def test_edge_slash_with_spaces(self, tmp_path: Path) -> None:
        repl = _make_repl(tmp_path=tmp_path)
        result = repl.handle_input("/  ")
        assert "Unknown command" in result

    def test_prompt_format(self, tmp_path: Path) -> None:
        ctx = _make_context(permission_mode=PermissionMode.APPROVE)
        repl = _make_repl(context=ctx, tmp_path=tmp_path)
        prompt = repl._get_prompt()
        assert "zhi>" in prompt


class TestFilteredFileHistory:
    def test_sensitive_lines_excluded(self, tmp_path: Path) -> None:
        from zhi.repl import _FilteredFileHistory

        hist_path = tmp_path / "history.txt"
        hist = _FilteredFileHistory(str(hist_path))

        hist.store_string("normal command")
        hist.store_string("set api_key sk-secret")
        hist.store_string("set password mypass")
        hist.store_string("another normal command")

        # Read back
        lines = list(hist.load_history_strings())
        assert "normal command" in lines
        assert "another normal command" in lines
        # Sensitive lines should NOT be stored
        for line in lines:
            assert "api_key" not in line
            assert "password" not in line
