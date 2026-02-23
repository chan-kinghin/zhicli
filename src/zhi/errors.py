"""Structured error catalog for zhi.

Every user-facing error has three parts: what happened, why, and what to try.
Errors are rendered via Rich Panel (red border for errors, yellow for warnings).
Stack traces go to ~/.zhi/logs/, never shown unless --debug.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ZhiError(Exception):
    """Base structured error with code, message, and suggestions."""

    code: str
    message: str
    suggestions: list[str] = field(default_factory=list)
    log_details: str | None = None

    def __str__(self) -> str:
        return self.message


class ConfigError(ZhiError):
    """Configuration-related errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "CONFIG_ERROR",
        suggestions: list[str] | None = None,
        log_details: str | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            suggestions=suggestions or [],
            log_details=log_details,
        )


class ApiError(ZhiError):
    """API communication errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "API_ERROR",
        suggestions: list[str] | None = None,
        log_details: str | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            suggestions=suggestions or [],
            log_details=log_details,
        )


class ToolError(ZhiError):
    """Tool execution errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "TOOL_ERROR",
        suggestions: list[str] | None = None,
        log_details: str | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            suggestions=suggestions or [],
            log_details=log_details,
        )


class SkillError(ZhiError):
    """Skill loading/execution errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "SKILL_ERROR",
        suggestions: list[str] | None = None,
        log_details: str | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            suggestions=suggestions or [],
            log_details=log_details,
        )


class FileError(ZhiError):
    """File operation errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "FILE_ERROR",
        suggestions: list[str] | None = None,
        log_details: str | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            suggestions=suggestions or [],
            log_details=log_details,
        )


def format_error(error: ZhiError) -> str:
    """Format a ZhiError into a human-readable string with what/why/try sections."""
    lines = [f"Error: {error.message}"]
    if error.log_details:
        lines.append(f"  Reason: {error.log_details}")
    if error.suggestions:
        lines.append("  Try:")
        for i, suggestion in enumerate(error.suggestions, 1):
            lines.append(f"    {i}. {suggestion}")
    return "\n".join(lines)


# Error catalog: templates for common errors, keyed by error code.
ERROR_CATALOG: dict[str, ZhiError] = {
    "AUTH_INVALID_KEY": ApiError(
        "Invalid API key",
        code="AUTH_INVALID_KEY",
        suggestions=[
            "Keys start with 'sk-'. Check for typos.",
            "Regenerate your key at open.bigmodel.cn",
            "Run `zhi --setup` to reconfigure",
        ],
    ),
    "AUTH_MISSING_KEY": ConfigError(
        "API key is not configured",
        code="AUTH_MISSING_KEY",
        suggestions=[
            "Run `zhi --setup` to configure your API key",
            "Set the ZHI_API_KEY environment variable",
        ],
    ),
    "API_TIMEOUT": ApiError(
        "Could not connect to Zhipu API",
        code="API_TIMEOUT",
        suggestions=[
            "Check your internet connection",
            "Verify API status at status.bigmodel.cn",
            "Run `zhi config show` to confirm your API key",
        ],
        log_details="Connection timed out after 30s",
    ),
    "API_RATE_LIMIT": ApiError(
        "Rate limit exceeded",
        code="API_RATE_LIMIT",
        suggestions=[
            "Wait a moment and try again",
            "Reduce request frequency",
            "Check your plan limits at open.bigmodel.cn",
        ],
    ),
    "API_SERVER_ERROR": ApiError(
        "Zhipu API returned a server error",
        code="API_SERVER_ERROR",
        suggestions=[
            "This is usually temporary. Try again in a few seconds.",
            "Check API status at status.bigmodel.cn",
        ],
    ),
    "FILE_NOT_FOUND": FileError(
        "File not found",
        code="FILE_NOT_FOUND",
        suggestions=[
            "Check the file path for typos",
            "Use an absolute path or path relative to current directory",
        ],
    ),
    "FILE_TOO_LARGE": FileError(
        "File is too large",
        code="FILE_TOO_LARGE",
        suggestions=[
            "Try a smaller file",
            "Split the file into smaller parts",
        ],
    ),
    "FILE_PERMISSION_DENIED": FileError(
        "Permission denied",
        code="FILE_PERMISSION_DENIED",
        suggestions=[
            "Check file permissions",
            "Run with appropriate access rights",
        ],
    ),
    "FILE_PATH_TRAVERSAL": FileError(
        "Path traversal rejected",
        code="FILE_PATH_TRAVERSAL",
        suggestions=[
            "Output files must be within the output directory",
            "Remove '..' from the file path",
        ],
    ),
    "TOOL_UNKNOWN": ToolError(
        "Unknown tool",
        code="TOOL_UNKNOWN",
        suggestions=[
            "Check available tools with /help",
        ],
    ),
    "TOOL_EXECUTION_FAILED": ToolError(
        "Tool execution failed",
        code="TOOL_EXECUTION_FAILED",
        suggestions=[
            "Check the tool's input parameters",
            "Try the operation again",
        ],
    ),
    "SKILL_NOT_FOUND": SkillError(
        "Skill not found",
        code="SKILL_NOT_FOUND",
        suggestions=[
            "List available skills with /skill list",
            "Create a new skill with /skill new",
        ],
    ),
    "SKILL_INVALID_YAML": SkillError(
        "Invalid skill YAML",
        code="SKILL_INVALID_YAML",
        suggestions=[
            "Check the skill file for syntax errors",
            "Use /skill show <name> to inspect the file",
        ],
    ),
    "SKILL_INVALID_NAME": SkillError(
        "Invalid skill name",
        code="SKILL_INVALID_NAME",
        suggestions=[
            "Skill names must match [a-zA-Z0-9][a-zA-Z0-9_-]* (max 64 chars)",
            "Avoid spaces, slashes, and special characters",
        ],
    ),
    "CONFIG_CORRUPT": ConfigError(
        "Config file is corrupted",
        code="CONFIG_CORRUPT",
        suggestions=[
            "Run `zhi --setup` to reconfigure",
            "Delete the config file and restart",
        ],
    ),
    "MAX_TURNS_REACHED": ApiError(
        "Maximum turns reached",
        code="MAX_TURNS_REACHED",
        suggestions=[
            "The agent reached its turn limit without completing",
            "Try breaking the task into smaller steps",
            "Increase max_turns in config if needed",
        ],
    ),
}
