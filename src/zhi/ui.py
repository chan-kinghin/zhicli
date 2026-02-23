"""Rich-based terminal UI for zhi.

Handles streaming output, thinking blocks, tool progress, spinners,
permission prompts, structured error rendering, and no-color fallback.
"""

from __future__ import annotations

import os
from typing import Any

from zhi.errors import ZhiError, format_error


def _no_color() -> bool:
    """Check if color output should be disabled."""
    return bool(os.environ.get("NO_COLOR"))


class UI:
    """Wraps all terminal output via Rich, with no-color fallback."""

    def __init__(self, *, no_color: bool = False, verbose: bool = False) -> None:
        self._no_color = no_color or _no_color()
        self._verbose = verbose
        self._tool_step = 0
        self._tool_total = 0

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

    def stream(self, text: str) -> None:
        """Display streamed text content."""
        if self._no_color:
            print(text, end="", flush=True)
            return
        self._console.print(text, end="")

    def stream_end(self) -> None:
        """End a streaming block with a newline."""
        if self._no_color:
            print()
        else:
            self._console.print()

    def show_thinking(self, text: str) -> None:
        """Display thinking text in dim/italic."""
        if self._no_color:
            for line in text.splitlines():
                print(f"  {line}")
            return
        from rich.text import Text

        styled = Text("Thinking...\n", style="dim italic")
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
        args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
        if len(args_str) > 80:
            args_str = args_str[:77] + "..."

        if self._no_color:
            if self._tool_total > 0:
                step = self._tool_step
                total = self._tool_total
                print(f"[TOOL] [{step}/{total}] {name}: {args_str}")
            else:
                print(f"[TOOL] {name}: {args_str}")
            return

        from rich.text import Text

        if self._tool_total > 0:
            prefix = f"[{self._tool_step}/{self._tool_total}] "
        else:
            prefix = ""

        text = Text(f"{prefix}{name}: ", style="bold cyan")
        text.append(args_str, style="dim")
        self._console.print(text)

    def show_tool_end(self, name: str, result: str) -> None:
        """Display tool execution result."""
        if self._verbose:
            display = result[:500] + "..." if len(result) > 500 else result
            if self._no_color:
                print(f"[DONE] {name}: {display}")
            else:
                from rich.text import Text

                text = Text(f"  {name}: ", style="green")
                text.append(display, style="dim")
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
        content.append(f"Error: {error.message}\n", style="bold red")
        if error.log_details:
            content.append(f"Reason: {error.log_details}\n", style="yellow")
        if error.suggestions:
            content.append("Try:\n", style="bold")
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
            print(f"[WARN] {message}")
            return

        from rich.panel import Panel

        panel = Panel(message, border_style="yellow", title="Warning", expand=False)
        self._console.print(panel)

    def ask_permission(self, tool_name: str, args: dict[str, Any]) -> bool:
        """Ask user for permission to execute a risky tool. Returns True if allowed."""
        args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
        if len(args_str) > 80:
            args_str = args_str[:77] + "..."

        if self._no_color:
            response = input(f"[CONFIRM] Allow {tool_name}({args_str})? [y/n]: ")
            return response.strip().lower() in ("y", "yes")

        from rich.prompt import Confirm

        return Confirm.ask(
            f"Allow [bold]{tool_name}[/bold]({args_str})?",
            console=self._console,
            default=False,
        )

    def show_summary(
        self,
        files_read: int = 0,
        files_written: int = 0,
        elapsed: float = 0.0,
    ) -> None:
        """Display session summary line."""
        parts = []
        if files_read:
            s = "s" if files_read != 1 else ""
            parts.append(f"{files_read} file{s} read")
        if files_written:
            s = "s" if files_written != 1 else ""
            parts.append(f"{files_written} file{s} written")
        summary = ", ".join(parts) if parts else "done"
        elapsed_str = f"({elapsed:.1f}s)" if elapsed > 0 else ""

        if self._no_color:
            print(f"[DONE] {summary} {elapsed_str}".strip())
            return

        from rich.text import Text

        text = Text("Done: ", style="bold green")
        text.append(f"{summary} {elapsed_str}".strip())
        self._console.print(text)

    def show_usage(self, tokens: int, cost: float) -> None:
        """Display token and cost usage."""
        if self._no_color:
            print(f"[USAGE] Session used {tokens:,} tokens (~${cost:.4f})")
            return

        from rich.text import Text

        text = Text("Session used ", style="dim")
        text.append(f"{tokens:,}", style="bold")
        text.append(f" tokens (~${cost:.4f})", style="dim")
        self._console.print(text)

    def print(self, message: str) -> None:
        """Print a plain message."""
        if self._no_color:
            print(message)
        else:
            self._console.print(message)


class _NoOpContext:
    """No-op context manager for spinner in no-color mode."""

    def __enter__(self) -> _NoOpContext:
        return self

    def __exit__(self, *args: object) -> None:
        pass
