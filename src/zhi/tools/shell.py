"""Shell tool for zhi."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
from collections.abc import Callable
from typing import Any, ClassVar

from zhi.tools.base import BaseTool

_MAX_OUTPUT_SIZE = 100 * 1024  # 100KB

# Commands that are blocked outright (catastrophic patterns)
_BLOCKED_PATTERNS = [
    "rm -rf /",
    "rm -rf ~",
    "rm -rf /*",
    "rm -rf ~/",
    "mkfs /dev/",
    ":(){ :|:& };:",
    "dd if=/dev/zero of=/dev/",
    "dd if=/dev/random of=/dev/",
    # Windows catastrophic patterns
    "del /s /q c:\\",
    "rd /s /q c:\\",
    "format c:",
    "format d:",
]

# Patterns that trigger extra destructive warning
_DESTRUCTIVE_PATTERNS = [
    "rm ",
    "rm\t",
    "del ",
    "del\t",
    "rmdir ",
    "rmdir\t",
    "mv ",
    "mv\t",
    "chmod ",
    "chmod\t",
    "chown ",
    "chown\t",
    "mkfs ",
    "mkfs\t",
    "dd ",
    "dd\t",
    "shred ",
    "shred\t",
    "truncate ",
    "truncate\t",
    "sed -i",
    "git reset --hard",
    "git clean",
    # Windows destructive patterns
    "del /",
    "del \\",
    "rd /",
    "rd \\",
    "reg delete",
    "icacls ",
]


class ShellTool(BaseTool):
    """Execute shell commands with safety checks."""

    name: ClassVar[str] = "shell"
    description: ClassVar[str] = (
        "Execute a shell command. Every command requires explicit user confirmation. "
        "Destructive commands (rm, del, mv, etc.) show extra warnings. "
        "Output is capped at 100KB."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds. Default: 30.",
                "default": 30,
            },
        },
        "required": ["command"],
    }
    risky: ClassVar[bool] = True

    def __init__(
        self,
        permission_callback: Callable[[str, bool], bool] | None = None,
    ) -> None:
        """Initialize shell tool.

        Args:
            permission_callback: Function(command, is_destructive) -> bool.
                Must return True to allow execution. If None, all commands
                are denied.
        """
        self._permission_callback = permission_callback

    def execute(self, **kwargs: Any) -> str:
        command: str = kwargs.get("command", "")
        timeout: int = kwargs.get("timeout", 30)

        if not command:
            return "Error: 'command' parameter is required."

        # Clamp timeout
        timeout = max(1, min(timeout, 300))

        # Normalize: collapse whitespace, strip, lowercase
        cmd_normalized = re.sub(r"\s+", " ", command.lower().strip())

        # Check blocklist against normalized form
        for blocked in _BLOCKED_PATTERNS:
            if blocked in cmd_normalized:
                return (
                    f"Error: Command blocked for safety. "
                    f"Pattern '{blocked}' is not allowed."
                )

        # Also block common bypass patterns: shells with -c, scripting
        # language one-liners, and direct paths to rm
        if re.search(
            r"\beval\b"
            r"|\b(?:ba)?sh\s+-c\b"
            r"|\b(?:z|da|fi|k|c|tc)sh\s+-c\b"
            r"|\bperl\s+-e\b"
            r"|\bpython[0-9]*\s+-c\b"
            r"|\bruby\s+-e\b"
            r"|\bnode\s+-e\b"
            r"|/bin/rm\b|/usr/bin/rm\b",
            cmd_normalized,
        ):
            return (
                "Error: Command blocked for safety. "
                "Indirect execution patterns are not allowed."
            )

        # Check for destructive commands (against normalized form)
        is_destructive = any(pat in cmd_normalized for pat in _DESTRUCTIVE_PATTERNS)

        # Always require confirmation, regardless of mode
        if self._permission_callback is None:
            return (
                "Error: Shell commands require user "
                "confirmation but no permission handler "
                "is configured."
            )

        allowed = self._permission_callback(command, is_destructive)
        if not allowed:
            return "Command denied by user."

        # Execute the command
        try:
            is_windows = sys.platform == "win32"

            popen_kwargs: dict[str, Any] = {
                "shell": True,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "text": True,
            }

            if is_windows:
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                popen_kwargs["start_new_session"] = True

            proc = subprocess.Popen(command, **popen_kwargs)

            try:
                stdout, _ = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Kill the entire process group
                if not is_windows:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (OSError, ProcessLookupError):
                        proc.kill()
                else:
                    proc.kill()
                proc.wait()
                return f"Error: Command timed out after {timeout}s and was killed."

            output = stdout or ""

            # Truncate output
            if len(output) > _MAX_OUTPUT_SIZE:
                output = (
                    output[:_MAX_OUTPUT_SIZE]
                    + f"\n[truncated, showing first 100KB of {len(stdout)}B]"
                )

            exit_code = proc.returncode
            if exit_code != 0:
                return f"[exit code: {exit_code}]\n{output}"

            return output if output else "(no output)"

        except FileNotFoundError:
            return "Error: Shell not found."
        except OSError as exc:
            return f"Error: Could not execute command: {exc}"
