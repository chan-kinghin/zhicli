"""Tests for shell tool."""

from __future__ import annotations

import pytest

from zhi.tools.shell import ShellTool


def _allow_all(command: str, is_destructive: bool) -> bool:
    return True


def _deny_all(command: str, is_destructive: bool) -> bool:
    return False


class TestShellSimpleCommand:
    def test_echo_command(self) -> None:
        tool = ShellTool(permission_callback=_allow_all)
        result = tool.execute(command="echo hello")
        assert "hello" in result

    def test_no_output_command(self) -> None:
        tool = ShellTool(permission_callback=_allow_all)
        result = tool.execute(command="true")
        assert result == "(no output)"


class TestShellExitCode:
    def test_nonzero_exit(self) -> None:
        tool = ShellTool(permission_callback=_allow_all)
        result = tool.execute(command="false")
        assert "exit code" in result

    def test_exit_code_reported(self) -> None:
        tool = ShellTool(permission_callback=_allow_all)
        result = tool.execute(command="exit 42")
        assert "exit code: 42" in result


class TestShellTimeout:
    def test_timeout_kills_process(self) -> None:
        tool = ShellTool(permission_callback=_allow_all)
        result = tool.execute(command="sleep 60", timeout=1)
        assert "timed out" in result.lower()


class TestShellRiskyFlag:
    def test_shell_is_risky(self) -> None:
        tool = ShellTool()
        assert tool.risky is True


class TestShellAlwaysRequiresConfirmation:
    def test_no_callback_means_denied(self) -> None:
        tool = ShellTool(permission_callback=None)
        result = tool.execute(command="echo hello")
        assert "Error" in result
        assert "confirmation" in result.lower() or "permission" in result.lower()

    def test_denied_by_callback(self) -> None:
        tool = ShellTool(permission_callback=_deny_all)
        result = tool.execute(command="echo hello")
        assert "denied" in result.lower()


class TestShellDestructiveCommandWarning:
    def test_destructive_callback_receives_flag(self) -> None:
        received: list[tuple[str, bool]] = []

        def track(command: str, is_destructive: bool) -> bool:
            received.append((command, is_destructive))
            return True

        tool = ShellTool(permission_callback=track)
        tool.execute(command="rm somefile.txt")
        assert len(received) == 1
        assert received[0][1] is True  # is_destructive

    def test_safe_command_not_flagged_destructive(self) -> None:
        received: list[tuple[str, bool]] = []

        def track(command: str, is_destructive: bool) -> bool:
            received.append((command, is_destructive))
            return True

        tool = ShellTool(permission_callback=track)
        tool.execute(command="echo hello")
        assert len(received) == 1
        assert received[0][1] is False


class TestShellCommandBlocklist:
    @pytest.mark.parametrize(
        "command",
        [
            "rm -rf /",
            "rm -rf ~",
            "rm -rf /*",
            "rm -rf ~/",
            "mkfs /dev/sda",
            ":(){ :|:& };:",
            "dd if=/dev/zero of=/dev/sda",
        ],
    )
    def test_blocked_command(self, command: str) -> None:
        tool = ShellTool(permission_callback=_allow_all)
        result = tool.execute(command=command)
        assert "Error" in result
        assert "blocked" in result.lower()


class TestShellOutputLimit:
    def test_truncates_large_output(self) -> None:
        tool = ShellTool(permission_callback=_allow_all)
        # Generate ~200KB of output
        cmd = "python3 -c \"print('x' * 200000)\""
        result = tool.execute(command=cmd)
        assert len(result) <= 110 * 1024  # some overhead for truncation message
        # The truncation message might be present
        if len(result) > 100 * 1024:
            assert "truncated" in result


class TestShellEmptyCommand:
    def test_empty_command(self) -> None:
        tool = ShellTool(permission_callback=_allow_all)
        result = tool.execute(command="")
        assert "Error" in result


class TestShellWindowsBlocklist:
    @pytest.mark.parametrize(
        "command",
        [
            "del /s /q c:\\",
            "del /s /q c:\\windows",
            "rd /s /q c:\\",
            "rd /s /q c:\\users",
            "format c:",
            "format d:",
        ],
    )
    def test_windows_blocked_command(self, command: str) -> None:
        tool = ShellTool(permission_callback=_allow_all)
        result = tool.execute(command=command)
        assert "Error" in result
        assert "blocked" in result.lower()


class TestShellWindowsDestructive:
    @pytest.mark.parametrize(
        "command",
        [
            "del /f myfile.txt",
            "rd /s mydir",
            "reg delete HKLM\\Software\\foo",
            "icacls myfile /grant Everyone:F",
        ],
    )
    def test_windows_destructive_flagged(self, command: str) -> None:
        received: list[tuple[str, bool]] = []

        def track(command: str, is_destructive: bool) -> bool:
            received.append((command, is_destructive))
            return True

        tool = ShellTool(permission_callback=track)
        tool.execute(command=command)
        assert len(received) == 1
        assert received[0][1] is True
