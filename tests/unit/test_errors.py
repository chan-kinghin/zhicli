"""Tests for zhi.errors module."""

from __future__ import annotations


class TestZhiError:
    """Test structured error types and formatting."""

    def test_zhi_error_is_exception(self) -> None:
        from zhi.errors import ZhiError

        error = ZhiError(code="TEST", message="test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_zhi_error_fields(self) -> None:
        from zhi.errors import ZhiError

        error = ZhiError(
            code="TEST_CODE",
            message="Something went wrong",
            suggestions=["Try this", "Try that"],
            log_details="Connection refused",
        )
        assert error.code == "TEST_CODE"
        assert error.message == "Something went wrong"
        assert error.suggestions == ["Try this", "Try that"]
        assert error.log_details == "Connection refused"

    def test_config_error(self) -> None:
        from zhi.errors import ConfigError, ZhiError

        error = ConfigError("Bad config")
        assert isinstance(error, ZhiError)
        assert error.code == "CONFIG_ERROR"
        assert error.message == "Bad config"

    def test_api_error(self) -> None:
        from zhi.errors import ApiError, ZhiError

        error = ApiError("API down", code="CUSTOM_CODE")
        assert isinstance(error, ZhiError)
        assert error.code == "CUSTOM_CODE"

    def test_tool_error(self) -> None:
        from zhi.errors import ToolError

        error = ToolError("Tool failed", suggestions=["Retry"])
        assert error.suggestions == ["Retry"]

    def test_skill_error(self) -> None:
        from zhi.errors import SkillError

        error = SkillError("Skill broken", log_details="YAML parse error on line 5")
        assert error.log_details == "YAML parse error on line 5"

    def test_file_error(self) -> None:
        from zhi.errors import FileError

        error = FileError("File not found")
        assert error.code == "FILE_ERROR"

    def test_format_error_basic(self) -> None:
        from zhi.errors import ZhiError, format_error

        error = ZhiError(code="TEST", message="Something failed")
        result = format_error(error)
        assert "Error: Something failed" in result

    def test_format_error_with_reason(self) -> None:
        from zhi.errors import ZhiError, format_error

        error = ZhiError(
            code="TEST",
            message="Connection failed",
            log_details="Timeout after 30s",
        )
        result = format_error(error)
        assert "Reason: Timeout after 30s" in result

    def test_format_error_with_suggestions(self) -> None:
        from zhi.errors import ZhiError, format_error

        error = ZhiError(
            code="TEST",
            message="Failed",
            suggestions=["Check connection", "Retry"],
        )
        result = format_error(error)
        assert "Try:" in result
        assert "1. Check connection" in result
        assert "2. Retry" in result

    def test_format_error_full(self) -> None:
        from zhi.errors import ApiError, format_error

        error = ApiError(
            "Could not connect to Zhipu API",
            code="API_TIMEOUT",
            suggestions=[
                "Check your internet connection",
                "Verify API status",
            ],
            log_details="Connection timed out after 30s",
        )
        result = format_error(error)
        assert "Error: Could not connect to Zhipu API" in result
        assert "Reason: Connection timed out after 30s" in result
        assert "1. Check your internet connection" in result
        assert "2. Verify API status" in result

    def test_error_catalog_has_entries(self) -> None:
        from zhi.errors import ERROR_CATALOG

        assert len(ERROR_CATALOG) > 0
        assert "AUTH_INVALID_KEY" in ERROR_CATALOG
        assert "AUTH_MISSING_KEY" in ERROR_CATALOG
        assert "API_TIMEOUT" in ERROR_CATALOG

    def test_error_catalog_entries_are_zhi_errors(self) -> None:
        from zhi.errors import ERROR_CATALOG, ZhiError

        for code, error in ERROR_CATALOG.items():
            assert isinstance(error, ZhiError), f"{code} is not a ZhiError"
            assert error.code == code, f"{code} code mismatch"
