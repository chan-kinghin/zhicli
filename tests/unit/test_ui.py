"""Tests for zhi.ui module."""

from __future__ import annotations

import io
from typing import Any
from unittest.mock import patch

import pytest


class TestUINoColor:
    """Test UI in no-color mode (plain text output)."""

    def _make_ui(self) -> Any:
        from zhi.ui import UI

        return UI(no_color=True)

    def test_stream_text(self) -> None:
        ui = self._make_ui()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.stream("Hello, world")
        assert "Hello, world" in mock_out.getvalue()

    def test_stream_end(self) -> None:
        ui = self._make_ui()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.stream_end()
        assert mock_out.getvalue() == "\n"

    def test_show_thinking(self) -> None:
        ui = self._make_ui()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_thinking("I need to think about this")
        output = mock_out.getvalue()
        assert "I need to think about this" in output

    def test_show_tool_start(self) -> None:
        ui = self._make_ui()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_tool_start("file_read", {"path": "test.txt"})
        output = mock_out.getvalue()
        assert "[TOOL]" in output
        assert "file_read" in output
        assert "test.txt" in output

    def test_show_tool_start_with_counter(self) -> None:
        ui = self._make_ui()
        ui.set_tool_total(3)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_tool_start("file_read", {"path": "a.txt"})
        output = mock_out.getvalue()
        assert "[1/3]" in output

    def test_show_tool_end_verbose(self) -> None:
        ui = self._make_ui()
        ui.verbose = True
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_tool_end("file_read", "file content here")
        output = mock_out.getvalue()
        assert "[DONE]" in output
        assert "file_read" in output

    def test_show_tool_end_not_verbose(self) -> None:
        ui = self._make_ui()
        ui.verbose = False
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_tool_end("file_read", "file content here")
        assert "done" in mock_out.getvalue().lower()

    def test_show_error(self) -> None:
        from zhi.errors import ApiError

        ui = self._make_ui()
        error = ApiError(
            "Connection failed",
            suggestions=["Check network", "Retry"],
            log_details="Timeout after 30s",
        )
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_error(error)
        output = mock_out.getvalue()
        assert "[ERROR]" in output
        assert "Connection failed" in output
        assert "Timeout after 30s" in output
        assert "Check network" in output

    def test_show_warning(self) -> None:
        ui = self._make_ui()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_warning("This is a warning")
        output = mock_out.getvalue()
        assert "[WARN]" in output
        assert "This is a warning" in output

    def test_show_summary(self) -> None:
        ui = self._make_ui()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_summary(files_read=2, files_written=1, elapsed=3.5)
        output = mock_out.getvalue()
        assert "[DONE]" in output
        assert "2 files read" in output
        assert "1 file written" in output
        assert "3.5s" in output

    def test_show_summary_empty(self) -> None:
        ui = self._make_ui()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_summary()
        output = mock_out.getvalue()
        assert "[DONE]" in output
        assert "done" in output

    def test_show_usage(self) -> None:
        ui = self._make_ui()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_usage(1500)
        output = mock_out.getvalue()
        assert "1,500" in output

    def test_ask_permission_yes(self) -> None:
        ui = self._make_ui()
        with patch("builtins.input", return_value="y"):
            result = ui.ask_permission("file_write", {"path": "out.md"})
        assert result is True

    def test_ask_permission_no(self) -> None:
        ui = self._make_ui()
        with patch("builtins.input", return_value="n"):
            result = ui.ask_permission("file_write", {"path": "out.md"})
        assert result is False

    def test_verbose_property(self) -> None:
        ui = self._make_ui()
        assert ui.verbose is False
        ui.verbose = True
        assert ui.verbose is True

    def test_print(self) -> None:
        ui = self._make_ui()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.print("Hello")
        assert "Hello" in mock_out.getvalue()

    def test_stream_rich_markup_not_interpreted(self) -> None:
        """Text with Rich markup chars should display literally."""
        ui = self._make_ui()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.stream("[bold]not bold[/bold]")
        assert "[bold]" in mock_out.getvalue()

    def test_show_thinking_has_prefix(self) -> None:
        ui = self._make_ui()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_thinking("deep thought")
        output = mock_out.getvalue()
        assert "thinking" in output.lower()
        assert "deep thought" in output

    def test_show_waiting(self) -> None:
        ui = self._make_ui()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_waiting("glm-5")
        assert "glm-5" in mock_out.getvalue()


class TestUIRich:
    """Test UI with Rich output (default mode)."""

    def _make_ui(self) -> Any:
        from zhi.ui import UI

        return UI(no_color=False)

    def test_stream_text_rich(self) -> None:
        ui = self._make_ui()
        # Rich output goes through console, just ensure no exception
        ui.stream("Hello")
        ui.stream_end()

    def test_show_thinking_rich(self) -> None:
        ui = self._make_ui()
        ui.show_thinking("I need to think")

    def test_show_tool_start_rich(self) -> None:
        ui = self._make_ui()
        ui.show_tool_start("file_read", {"path": "test.txt"})

    def test_show_error_rich(self) -> None:
        from zhi.errors import ToolError

        ui = self._make_ui()
        error = ToolError("Tool broke", suggestions=["Fix it"])
        ui.show_error(error)

    def test_show_warning_rich(self) -> None:
        ui = self._make_ui()
        ui.show_warning("Watch out")

    def test_show_summary_rich(self) -> None:
        ui = self._make_ui()
        ui.show_summary(files_read=1, elapsed=1.0)

    def test_show_usage_rich(self) -> None:
        ui = self._make_ui()
        ui.show_usage(500)

    def test_print_rich(self) -> None:
        ui = self._make_ui()
        ui.print("Hello")

    def test_spinner_returns_context_manager(self) -> None:
        ui = self._make_ui()
        ctx = ui.show_spinner("Loading...")
        assert hasattr(ctx, "__enter__")
        assert hasattr(ctx, "__exit__")


class TestUINoColorEnv:
    """Test NO_COLOR env var detection."""

    def test_no_color_env(self, monkeypatch: pytest.MonkeyPatch) -> None:

        monkeypatch.setenv("NO_COLOR", "1")
        from zhi.ui import _no_color

        assert _no_color() is True

    def test_color_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:

        monkeypatch.delenv("NO_COLOR", raising=False)
        from zhi.ui import _no_color

        assert _no_color() is False


class TestNoOpContext:
    """Test the no-op context manager for spinner fallback."""

    def test_noop_context(self) -> None:
        from zhi.ui import _NoOpContext

        ctx = _NoOpContext()
        with ctx:
            pass  # Should not raise
