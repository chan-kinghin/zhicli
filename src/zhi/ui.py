"""Rich-based terminal UI for zhi.

Handles streaming output, thinking blocks, tool progress, spinners,
permission prompts, structured error rendering, and no-color fallback.
"""

from __future__ import annotations

import os
import time
from typing import Any

from zhi.errors import ZhiError, format_error
from zhi.i18n import t


def _no_color() -> bool:
    """Check if color output should be disabled."""
    return bool(os.environ.get("NO_COLOR"))


def _format_tokens(tokens: int) -> str:
    """Format a token count compactly: 1500 → '1.5k', 12300 → '12.3k'."""
    if tokens < 1000:
        return str(tokens)
    value = tokens / 1000
    if value >= 100:
        return f"{value:.0f}k"
    return f"{value:.1f}k"


def _build_metrics(tool_count: int = 0, tokens: int = 0, elapsed: float = 0.0) -> str:
    """Build a compact metrics string like '5 tools · 8.2k tokens · 4.5s'."""
    parts: list[str] = []
    if tool_count > 0:
        parts.append(t("ui.tools_metric", count=tool_count))
    if tokens > 0:
        parts.append(t("ui.tokens_metric", tokens=_format_tokens(tokens)))
    if elapsed > 0:
        parts.append(f"{elapsed:.1f}s")
    return " \u00b7 ".join(parts)


class UI:
    """Wraps all terminal output via Rich, with no-color fallback."""

    def __init__(self, *, no_color: bool = False, verbose: bool = False) -> None:
        self._no_color = no_color or _no_color()
        self._verbose = verbose
        self._tool_step = 0
        self._tool_total = 0
        self._stream_buffer: str = ""
        self._waiting_live: Any = None
        self._waiting_start: float = 0.0
        self._stream_live: Any = None
        self._tool_start_time: float = 0.0
        self._trace_depth: int = 0

        if not self._no_color:
            from rich.console import Console

            self._console = Console()
        else:
            self._console = None  # type: ignore[assignment]

    @property
    def verbose(self) -> bool:
        return self._verbose

    @verbose.setter
    def verbose(self, value: bool) -> None:
        self._verbose = value

    def stream_start(self) -> None:
        """Begin a live-updating stream display (Rich mode only)."""
        if self._no_color:
            return

        from rich.live import Live
        from rich.text import Text

        self._stream_buffer = ""
        self._stream_live = Live(
            Text(""),
            console=self._console,
            refresh_per_second=8,
            vertical_overflow="visible",
        )
        self._stream_live.start()

    def stream(self, text: str) -> None:
        """Buffer streamed text, updating live display if active."""
        if self._no_color:
            print(text, end="", flush=True)
            return
        self._stream_buffer += text
        if self._stream_live is not None:
            try:
                from rich.markdown import Markdown

                self._stream_live.update(Markdown(self._stream_buffer))
            except Exception:
                from rich.text import Text

                self._stream_live.update(Text(self._stream_buffer))

    def stream_end(self) -> None:
        """Render buffered stream content as markdown, then clear buffer."""
        if self._no_color:
            print()
            return

        # Stop live display if active
        if self._stream_live is not None:
            self._stream_live.stop()
            self._stream_live = None

        buf = self._stream_buffer
        self._stream_buffer = ""

        if not buf:
            self._console.print()
            return

        try:
            from rich.markdown import Markdown

            md = Markdown(buf)
            self._console.print(md)
        except Exception:
            from rich.text import Text

            self._console.print(Text(buf))

    def show_thinking(self, text: str) -> None:
        """Display thinking text in dim/italic."""
        if self._no_color:
            prefix = t("ui.thinking_prefix")
            for line in text.splitlines():
                print(f"{prefix}{line}")
            return
        from rich.text import Text

        styled = Text("Thinking:\n", style="dim bold")
        for line in text.splitlines():
            styled.append(f"  {line}\n", style="dim italic")
        self._console.print(styled)

    def set_tool_total(self, total: int) -> None:
        """Set total number of tool calls for step counter."""
        self._tool_step = 0
        self._tool_total = total

    def show_tool_start(self, name: str, args: dict[str, Any]) -> None:
        """Display tool execution start with step counter."""
        self._tool_step += 1
        self._tool_start_time = time.monotonic()
        args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
        if len(args_str) > 80:
            args_str = args_str[:77] + "..."

        indent = "  " * self._trace_depth

        if self._verbose:
            # Verbose: trace-style output with symbols
            if self._no_color:
                bullet = t("ui.trace_bullet_nocolor")
                if self._trace_depth > 0:
                    hook = t("ui.trace_result_nocolor")
                    print(f"{indent}{hook} {name}({args_str})")
                else:
                    print(f"{indent}{bullet} {name}({args_str})")
                return
            from rich.text import Text

            if self._trace_depth > 0:
                hook = t("ui.trace_result")
                text = Text(f"{indent}{hook} ", style="dim")
                text.append(f"{name}", style="bold cyan")
                text.append(f"({args_str})", style="dim")
            else:
                bullet = t("ui.trace_bullet")
                text = Text(f"{indent}{bullet} ", style="cyan")
                text.append(f"{name}", style="bold cyan")
                text.append(f"({args_str})", style="dim")
            self._console.print(text)
        else:
            # Compact: single line, no newline yet (show_tool_end completes it)
            if self._tool_total > 0:
                prefix = f"[{self._tool_step}/{self._tool_total}] "
            else:
                prefix = ""
            if self._no_color:
                print(f"  {indent}{prefix}{name} ...", end="", flush=True)
            else:
                from rich.text import Text

                text = Text(f"  {indent}{prefix}{name} ...", style="dim cyan")
                self._console.print(text, end="")

    def show_tool_end(self, name: str, result: str) -> None:
        """Display tool execution result."""
        elapsed = time.monotonic() - self._tool_start_time
        elapsed_str = f"{elapsed:.1f}s"
        is_error = result.startswith("Error")

        indent = "  " * self._trace_depth

        if self._verbose:
            # Verbose: trace-style result line with timing
            ok_sym = t("ui.trace_fail") if is_error else t("ui.trace_ok")
            if self._no_color:
                hook = t("ui.trace_result_nocolor")
                ok_sym_nc = t("ui.trace_fail") if is_error else t("ui.trace_ok")
                print(f"{indent}  {hook} {ok_sym_nc} {elapsed_str}")
            else:
                from rich.text import Text

                hook = t("ui.trace_result")
                style = "red" if is_error else "green"
                text = Text(f"{indent}  {hook} ", style="dim")
                text.append(ok_sym, style=style)
                text.append(f" {elapsed_str}", style="dim")
                self._console.print(text)
        else:
            # Compact: complete the single line started by show_tool_start
            ok_sym = t("ui.trace_ok") if not is_error else t("ui.trace_fail")
            if self._no_color:
                print(f" {ok_sym} {elapsed_str}")
            else:
                from rich.text import Text

                style = "dim green" if not is_error else "dim red"
                text = Text(f" {ok_sym} {elapsed_str}", style=style)
                self._console.print(text)

    def show_spinner(self, message: str) -> Any:
        """Show a spinner with a message. Returns a context manager."""
        if self._no_color:
            print(f"[...] {message}")
            return _NoOpContext()

        from rich.live import Live
        from rich.spinner import Spinner

        spinner = Spinner("dots", text=message, style="cyan")
        return Live(spinner, console=self._console, refresh_per_second=10)

    def show_error(self, error: ZhiError) -> None:
        """Display structured error with Rich Panel (red border)."""
        if self._no_color:
            print(f"[ERROR] {format_error(error)}")
            return

        from rich.panel import Panel
        from rich.text import Text

        content = Text()
        content.append(
            t("ui.error_label", message=error.message) + "\n", style="bold red"
        )
        if error.log_details:
            content.append(
                t("ui.reason_label", details=error.log_details) + "\n", style="yellow"
            )
        if error.suggestions:
            content.append(t("ui.try_label") + "\n", style="bold")
            for i, suggestion in enumerate(error.suggestions, 1):
                content.append(f"  {i}. {suggestion}\n")

        panel = Panel(
            content,
            border_style="red",
            title=f"[{error.code}]",
            expand=False,
        )
        self._console.print(panel)

    def show_warning(self, message: str) -> None:
        """Display a warning message in yellow."""
        if self._no_color:
            print(f"[WARN] !! {message}")
            return

        from rich.panel import Panel

        panel = Panel(
            f"!! {message}",
            border_style="yellow",
            title=t("ui.warning_title"),
            expand=False,
        )
        self._console.print(panel)

    def ask_permission(self, tool_name: str, args: dict[str, Any]) -> bool:
        """Ask user for permission to execute a risky tool. Returns True if allowed."""
        args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
        if len(args_str) > 80:
            args_str = args_str[:77] + "..."

        if self._no_color:
            response = input(t("ui.confirm_nocolor", tool=tool_name, args=args_str))
            return response.strip().lower() in ("y", "yes")

        from rich.prompt import Confirm

        return Confirm.ask(
            t("ui.confirm_rich", tool=tool_name, args=args_str),
            console=self._console,
            default=False,
        )

    def set_trace_depth(self, depth: int) -> None:
        """Set the nesting depth for trace indentation."""
        self._trace_depth = depth

    def show_skill_summary(
        self,
        tool_count: int = 0,
        tokens: int = 0,
        elapsed: float = 0.0,
    ) -> None:
        """Display a summary line for a nested skill execution."""
        metrics = _build_metrics(tool_count, tokens, elapsed)
        summary = t("ui.skill_summary", metrics=metrics)
        indent = "  " * self._trace_depth

        if self._no_color:
            hook = t("ui.trace_result_nocolor")
            print(f"{indent}  {hook} {summary}")
            return

        from rich.text import Text

        hook = t("ui.trace_result")
        text = Text(f"{indent}  {hook} ", style="dim")
        text.append(summary, style="dim green")
        self._console.print(text)

    def show_summary(
        self,
        files_read: int = 0,
        files_written: int = 0,
        elapsed: float = 0.0,
        tool_count: int = 0,
        tokens: int = 0,
    ) -> None:
        """Display session summary line."""
        parts = []
        if files_read:
            s = "s" if files_read != 1 else ""
            parts.append(t("ui.files_read", count=files_read, s=s))
        if files_written:
            s = "s" if files_written != 1 else ""
            parts.append(t("ui.files_written", count=files_written, s=s))
        summary = ", ".join(parts) if parts else t("ui.done_fallback")

        # Build metrics suffix (tool count, tokens, elapsed)
        metrics = _build_metrics(tool_count, tokens, elapsed)
        if metrics:
            summary = f"{summary} ({metrics})"
        elif elapsed > 0:
            summary = f"{summary} ({elapsed:.1f}s)"

        if self._no_color:
            print(f"[DONE] {summary}")
            return

        from rich.text import Text

        text = Text(t("ui.done_prefix"), style="bold green")
        text.append(summary)
        self._console.print(text)

    def show_usage(self, tokens: int, cost: float = 0.0) -> None:
        """Display token usage."""
        if self._no_color:
            print(t("ui.usage_nocolor", tokens=f"{tokens:,}"))
            return

        from rich.text import Text

        text = Text(t("ui.session_used"), style="dim")
        text.append(f"{tokens:,}", style="bold")
        text.append(t("ui.tokens_suffix"), style="dim")
        self._console.print(text)

    def show_banner(self, version: str) -> None:
        """Display the startup banner with pixel-art-inspired logo."""
        if self._no_color:
            print(f"\n  zhi v{version}")
            print(f"  {t('banner.tagline')}")
            print(f"  {t('banner.hint')}\n")
            return

        c = self._console
        c.print()
        c.print("[dim]        · [bold yellow]☀[/bold yellow] ·[/dim]")
        c.print("[orange1]      ╱[yellow]━━━━━[/yellow]╲[/orange1]")
        c.print("[dark_orange3]    ╱[orange1]━━━━━━━━━[/orange1]╲[/dark_orange3]")
        c.print(
            "[steel_blue]  ╱╱╱[/steel_blue]  [bold]▐▌[/bold]  "
            "[steel_blue]╲╲╲[/steel_blue]"
            f"   [bold cyan]zhi[/bold cyan] [dim cyan]v{version}[/dim cyan]"
        )
        c.print(
            "[dark_blue]  ▔▔▔▔▔▔▔▔▔▔▔▔▔[/dark_blue]"
            f"   [dim]{t('banner.tagline_short')}[/dim]"
        )
        c.print(f"[dim]                  {t('banner.hint')}[/dim]")
        c.print()

    def show_waiting(self, model: str) -> None:
        """Display a spinner with elapsed time while waiting for API response."""
        if self._no_color:
            print(f"[...] {model}", end="", flush=True)
            return

        from rich.live import Live
        from rich.spinner import Spinner

        self._waiting_start = time.monotonic()
        spinner = Spinner("dots", text=f"  {model} ...", style="cyan")
        self._waiting_live = Live(
            _ElapsedSpinner(model, self._waiting_start, spinner),
            console=self._console,
            refresh_per_second=4,
            transient=True,
        )
        self._waiting_live.start()

    def clear_waiting(self) -> None:
        """Stop the waiting spinner."""
        if self._no_color:
            print("\r" + " " * 40 + "\r", end="", flush=True)
            return

        if self._waiting_live is not None:
            self._waiting_live.stop()
            self._waiting_live = None

    def print(self, message: str) -> None:
        """Print a plain message."""
        if self._no_color:
            print(message)
        else:
            self._console.print(message)


class _ElapsedSpinner:
    """Rich renderable that shows a spinner with elapsed time."""

    def __init__(self, model: str, start: float, spinner: Any) -> None:
        self._model = model
        self._start = start
        self._spinner = spinner

    def __rich_console__(self, console: Any, options: Any) -> Any:
        elapsed = time.monotonic() - self._start
        self._spinner.text = f"  {self._model} ... {elapsed:.1f}s"
        yield from self._spinner.__rich_console__(console, options)


class _NoOpContext:
    """No-op context manager for spinner in no-color mode."""

    def __enter__(self) -> _NoOpContext:
        return self

    def __exit__(self, *args: object) -> None:
        pass
