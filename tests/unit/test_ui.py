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

    def test_show_tool_start_compact(self) -> None:
        """Non-verbose mode shows compact single-line output."""
        ui = self._make_ui()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_tool_start("file_read", {"path": "test.txt"})
        output = mock_out.getvalue()
        assert "file_read" in output
        assert "..." in output

    def test_show_tool_start_verbose(self) -> None:
        """Verbose mode shows trace-style output with args."""
        ui = self._make_ui()
        ui.verbose = True
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_tool_start("file_read", {"path": "test.txt"})
        output = mock_out.getvalue()
        assert "file_read" in output
        assert "test.txt" in output
        assert "*" in output  # no-color bullet

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
            ui.show_tool_start("file_read", {"path": "test.txt"})
            ui.show_tool_end("file_read", "file content here")
        output = mock_out.getvalue()
        assert "\u2713" in output  # checkmark
        assert "s" in output  # elapsed time

    def test_show_tool_end_not_verbose(self) -> None:
        ui = self._make_ui()
        ui.verbose = False
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_tool_start("file_read", {"path": "test.txt"})
            ui.show_tool_end("file_read", "file content here")
        output = mock_out.getvalue()
        assert "\u2713" in output  # checkmark
        assert "s" in output  # elapsed time

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


class TestUIStreamLive:
    """Test live stream start/end lifecycle."""

    def test_stream_start_creates_live(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NO_COLOR", raising=False)
        from zhi.ui import UI

        ui = UI(no_color=False)
        ui.stream_start()
        assert ui._stream_live is not None
        ui.stream_end()  # Cleanup

    def test_stream_end_clears_live(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NO_COLOR", raising=False)
        from zhi.ui import UI

        ui = UI(no_color=False)
        ui.stream_start()
        ui.stream("Hello")
        ui.stream_end()
        assert ui._stream_live is None

    def test_stream_without_live_buffers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NO_COLOR", raising=False)
        from zhi.ui import UI

        ui = UI(no_color=False)
        ui.stream("chunk1")
        ui.stream("chunk2")
        assert ui._stream_buffer == "chunk1chunk2"
        ui.stream_end()

    def test_stream_start_nocolor_noop(self) -> None:
        from zhi.ui import UI

        ui = UI(no_color=True)
        ui.stream_start()  # Should not raise
        assert ui._stream_live is None


class TestUISpinnerElapsed:
    """Test elapsed time spinner."""

    def test_show_waiting_creates_live_rich(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("NO_COLOR", raising=False)
        from zhi.ui import UI

        ui = UI(no_color=False)
        ui.show_waiting("glm-5")
        assert ui._waiting_live is not None
        ui.clear_waiting()

    def test_clear_waiting_stops_live(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NO_COLOR", raising=False)
        from zhi.ui import UI

        ui = UI(no_color=False)
        ui.show_waiting("glm-5")
        ui.clear_waiting()
        assert ui._waiting_live is None

    def test_show_waiting_nocolor_fallback(self) -> None:
        from zhi.ui import UI

        ui = UI(no_color=True)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_waiting("glm-5")
        assert "glm-5" in mock_out.getvalue()
        assert ui._waiting_live is None


class TestElapsedSpinner:
    """Test _ElapsedSpinner renderable."""

    def test_elapsed_spinner_format(self) -> None:
        import time as time_mod

        from rich.spinner import Spinner

        from zhi.ui import _ElapsedSpinner

        start = time_mod.monotonic() - 2.5  # Simulate 2.5s elapsed
        spinner = Spinner("dots", text="placeholder")
        es = _ElapsedSpinner("glm-5", start, spinner)

        # Verify the text gets updated when rendered
        from rich.console import Console

        console = Console(force_terminal=True, width=80)
        # Trigger __rich_console__ by iterating
        list(es.__rich_console__(console, console.options))
        assert "glm-5" in spinner.text
        assert "s" in spinner.text  # elapsed time suffix


class TestUIFormatTokens:
    """Test _format_tokens helper."""

    def test_under_1000(self) -> None:
        from zhi.ui import _format_tokens

        assert _format_tokens(500) == "500"
        assert _format_tokens(0) == "0"

    def test_thousands(self) -> None:
        from zhi.ui import _format_tokens

        assert _format_tokens(1500) == "1.5k"
        assert _format_tokens(8200) == "8.2k"

    def test_large(self) -> None:
        from zhi.ui import _format_tokens

        assert _format_tokens(123000) == "123k"


class TestUIBuildMetrics:
    """Test _build_metrics helper."""

    def test_all_metrics(self) -> None:
        from zhi.ui import _build_metrics

        result = _build_metrics(tool_count=5, tokens=8200, elapsed=4.5)
        assert "5 tools" in result
        assert "8.2k" in result
        assert "4.5s" in result
        assert "\u00b7" in result  # middle dot separator

    def test_only_tools(self) -> None:
        from zhi.ui import _build_metrics

        result = _build_metrics(tool_count=3)
        assert "3 tools" in result
        assert "\u00b7" not in result

    def test_empty(self) -> None:
        from zhi.ui import _build_metrics

        assert _build_metrics() == ""


class TestUITiming:
    """Test tool timing in show_tool_start/end."""

    def test_compact_timing_nocolor(self) -> None:
        """Compact mode shows timing in tool end."""
        from zhi.ui import UI

        ui = UI(no_color=True)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_tool_start("file_read", {"path": "test.txt"})
            ui.show_tool_end("file_read", "contents")
        output = mock_out.getvalue()
        assert "file_read" in output
        assert "\u2713" in output  # checkmark
        assert "s" in output  # elapsed time suffix

    def test_compact_error_symbol_nocolor(self) -> None:
        """Compact mode shows error symbol for failed tools."""
        from zhi.ui import UI

        ui = UI(no_color=True)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_tool_start("file_read", {"path": "x.txt"})
            ui.show_tool_end("file_read", "Error: not found")
        output = mock_out.getvalue()
        assert "\u2717" in output  # cross mark

    def test_verbose_trace_symbols_nocolor(self) -> None:
        """Verbose mode uses trace bullet/hook symbols."""
        from zhi.ui import UI

        ui = UI(no_color=True, verbose=True)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_tool_start("file_read", {"path": "a.txt"})
            ui.show_tool_end("file_read", "contents")
        output = mock_out.getvalue()
        assert "*" in output  # no-color bullet
        assert "|_" in output  # no-color result hook
        assert "\u2713" in output

    def test_verbose_nested_depth_nocolor(self) -> None:
        """Nested depth adds indentation in verbose mode."""
        from zhi.ui import UI

        ui = UI(no_color=True, verbose=True)
        ui.set_trace_depth(1)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_tool_start("file_read", {"path": "b.txt"})
        output = mock_out.getvalue()
        # Depth 1 = nested, should use hook and indentation
        assert "|_" in output
        assert "  " in output  # indentation from depth


class TestUITraceDepth:
    """Test trace depth management."""

    def test_set_trace_depth(self) -> None:
        from zhi.ui import UI

        ui = UI(no_color=True)
        assert ui._trace_depth == 0
        ui.set_trace_depth(2)
        assert ui._trace_depth == 2
        ui.set_trace_depth(0)
        assert ui._trace_depth == 0


class TestUISkillSummary:
    """Test show_skill_summary method."""

    def test_skill_summary_nocolor(self) -> None:
        from zhi.ui import UI

        ui = UI(no_color=True)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_skill_summary(tool_count=3, tokens=2400, elapsed=1.2)
        output = mock_out.getvalue()
        assert "3 tools" in output
        assert "2.4k" in output
        assert "1.2s" in output

    def test_skill_summary_with_depth(self) -> None:
        from zhi.ui import UI

        ui = UI(no_color=True)
        ui.set_trace_depth(1)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_skill_summary(tool_count=2, tokens=1000, elapsed=0.5)
        output = mock_out.getvalue()
        # Should have indentation from depth
        assert output.startswith("  ")


class TestUIEnhancedSummary:
    """Test enhanced show_summary with tool_count and tokens."""

    def test_summary_with_all_metrics(self) -> None:
        from zhi.ui import UI

        ui = UI(no_color=True)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_summary(
                files_read=2,
                files_written=1,
                elapsed=4.5,
                tool_count=5,
                tokens=8200,
            )
        output = mock_out.getvalue()
        assert "2 files read" in output
        assert "1 file written" in output
        assert "5 tools" in output
        assert "8.2k" in output
        assert "4.5s" in output

    def test_summary_with_only_elapsed(self) -> None:
        """When no tool_count or tokens, elapsed still shows."""
        from zhi.ui import UI

        ui = UI(no_color=True)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_summary(files_read=1, elapsed=2.0)
        output = mock_out.getvalue()
        assert "1 file read" in output
        assert "2.0s" in output

    def test_summary_without_files_but_with_tools(self) -> None:
        """Summary shows 'done' fallback text when no files, plus tool metrics."""
        from zhi.ui import UI

        ui = UI(no_color=True)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            ui.show_summary(tool_count=3, tokens=500, elapsed=1.0)
        output = mock_out.getvalue()
        assert "3 tools" in output
        assert "500 tokens" in output


class TestNoOpContext:
    """Test the no-op context manager for spinner fallback."""

    def test_noop_context(self) -> None:
        from zhi.ui import _NoOpContext

        ctx = _NoOpContext()
        with ctx:
            pass  # Should not raise
