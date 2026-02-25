"""Tests for zhi.client module.

All tests mock at the SDK boundary (zhipuai.ZhipuAI), never at HTTP level.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from zhi.client import (
    AuthenticationError,
    ChatResponse,
    Client,
    ClientError,
    ServerError,
)


def _make_choice(
    content: str | None = "Hello!",
    tool_calls: list[Any] | None = None,
    finish_reason: str = "stop",
) -> SimpleNamespace:
    """Build a mock choice object."""
    msg = SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
    )
    return SimpleNamespace(message=msg, finish_reason=finish_reason)


def _make_usage(
    prompt: int = 10, completion: int = 20, total: int = 30
) -> SimpleNamespace:
    return SimpleNamespace(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=total,
    )


def _make_response(
    content: str | None = "Hello!",
    tool_calls: list[Any] | None = None,
    finish_reason: str = "stop",
) -> SimpleNamespace:
    """Build a mock SDK response."""
    return SimpleNamespace(
        choices=[_make_choice(content, tool_calls, finish_reason)],
        usage=_make_usage(),
    )


def _make_tool_call(
    call_id: str = "call_1",
    name: str = "file_read",
    arguments: str = '{"path": "test.txt"}',
) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _make_stream_chunk(
    content: str = "",
    finish_reason: str | None = None,
    tool_calls: list[Any] | None = None,
) -> SimpleNamespace:
    """Build a mock streaming chunk."""
    delta = SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=delta, finish_reason=finish_reason)],
    )


class TestChatCompletion:
    """Test non-streaming chat completion."""

    @patch("zhi.client.ZhipuAI")
    def test_chat_completion_basic(self, mock_sdk_cls: MagicMock) -> None:
        mock_sdk = mock_sdk_cls.return_value
        mock_sdk.chat.completions.create.return_value = _make_response("Hello!")

        client = Client(api_key="sk-test")
        result = client.chat(
            messages=[{"role": "user", "content": "hi"}],
        )

        assert isinstance(result, ChatResponse)
        assert result.content == "Hello!"
        assert result.total_tokens == 30
        assert result.finish_reason == "stop"
        assert result.tool_calls == []

    @patch("zhi.client.ZhipuAI")
    def test_chat_completion_with_tools(self, mock_sdk_cls: MagicMock) -> None:
        tc = _make_tool_call()
        mock_sdk = mock_sdk_cls.return_value
        mock_sdk.chat.completions.create.return_value = _make_response(
            content=None,
            tool_calls=[tc],
            finish_reason="tool_calls",
        )

        client = Client(api_key="sk-test")
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "file_read",
                    "description": "Read a file",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        result = client.chat(
            messages=[{"role": "user", "content": "read file"}],
            tools=tools,
        )

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["function"]["name"] == "file_read"
        assert result.finish_reason == "tool_calls"

    @patch("zhi.client.ZhipuAI")
    def test_chat_streaming(self, mock_sdk_cls: MagicMock) -> None:
        chunks = [
            _make_stream_chunk("Hello"),
            _make_stream_chunk(" world"),
            _make_stream_chunk("!", finish_reason="stop"),
        ]
        mock_sdk = mock_sdk_cls.return_value
        mock_sdk.chat.completions.create.return_value = iter(chunks)

        client = Client(api_key="sk-test")
        result_chunks = list(
            client.chat_stream(
                messages=[{"role": "user", "content": "hi"}],
            )
        )

        assert len(result_chunks) == 3
        assert result_chunks[0].delta_content == "Hello"
        assert result_chunks[1].delta_content == " world"
        assert result_chunks[2].delta_content == "!"
        assert result_chunks[2].finish_reason == "stop"

    @patch("zhi.client.ZhipuAI")
    def test_chat_invalid_api_key(self, mock_sdk_cls: MagicMock) -> None:
        mock_sdk = mock_sdk_cls.return_value
        error = Exception("unauthorized")
        error.status_code = 401  # type: ignore[attr-defined]
        mock_sdk.chat.completions.create.side_effect = error

        client = Client(api_key="sk-bad")
        with pytest.raises(AuthenticationError):
            client.chat(
                messages=[{"role": "user", "content": "hi"}],
            )

    @patch("zhi.client.time")
    @patch("zhi.client.ZhipuAI")
    def test_chat_rate_limit_retry(
        self,
        mock_sdk_cls: MagicMock,
        mock_time: MagicMock,
    ) -> None:
        mock_time.sleep = MagicMock()

        mock_sdk = mock_sdk_cls.return_value
        rate_error = Exception("rate limit exceeded")
        rate_error.status_code = 429  # type: ignore[attr-defined]

        mock_sdk.chat.completions.create.side_effect = [
            rate_error,
            rate_error,
            _make_response("OK after retry"),
        ]

        client = Client(api_key="sk-test", max_retries=3)
        result = client.chat(
            messages=[{"role": "user", "content": "hi"}],
        )

        assert result.content == "OK after retry"
        assert mock_time.sleep.call_count == 2

    @patch("zhi.client.time")
    @patch("zhi.client.ZhipuAI")
    def test_chat_server_error_retry(
        self,
        mock_sdk_cls: MagicMock,
        mock_time: MagicMock,
    ) -> None:
        mock_time.sleep = MagicMock()

        mock_sdk = mock_sdk_cls.return_value
        server_error = Exception("server error")
        server_error.status_code = 500  # type: ignore[attr-defined]

        mock_sdk.chat.completions.create.side_effect = [
            server_error,
            _make_response("OK"),
        ]

        client = Client(api_key="sk-test", max_retries=3)
        result = client.chat(
            messages=[{"role": "user", "content": "hi"}],
        )

        assert result.content == "OK"

    @patch("zhi.client.time")
    @patch("zhi.client.ZhipuAI")
    def test_chat_max_retries_exceeded(
        self,
        mock_sdk_cls: MagicMock,
        mock_time: MagicMock,
    ) -> None:
        mock_time.sleep = MagicMock()

        mock_sdk = mock_sdk_cls.return_value
        server_error = Exception("server error")
        server_error.status_code = 500  # type: ignore[attr-defined]

        mock_sdk.chat.completions.create.side_effect = server_error

        client = Client(api_key="sk-test", max_retries=2)
        with pytest.raises(ServerError):
            client.chat(
                messages=[{"role": "user", "content": "hi"}],
            )

    @patch("zhi.client.ZhipuAI")
    def test_chat_network_timeout(self, mock_sdk_cls: MagicMock) -> None:
        mock_sdk = mock_sdk_cls.return_value
        mock_sdk.chat.completions.create.side_effect = Exception("request timed out")

        client = Client(api_key="sk-test", max_retries=0)
        with pytest.raises(ClientError) as exc_info:
            client.chat(
                messages=[{"role": "user", "content": "hi"}],
            )
        assert exc_info.value.code == "TIMEOUT"

    @patch("zhi.client.ZhipuAI")
    def test_chat_model_selection(self, mock_sdk_cls: MagicMock) -> None:
        mock_sdk = mock_sdk_cls.return_value
        mock_sdk.chat.completions.create.return_value = _make_response("OK")

        client = Client(api_key="sk-test")
        client.chat(
            messages=[{"role": "user", "content": "hi"}],
            model="glm-4-flash",
        )

        call_kwargs = mock_sdk.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "glm-4-flash"


class TestChatChunkParsing:
    """Test streaming chunk parsing."""

    @patch("zhi.client.ZhipuAI")
    def test_empty_choices_chunk(self, mock_sdk_cls: MagicMock) -> None:
        chunk = SimpleNamespace(choices=[], usage=None)
        mock_sdk = mock_sdk_cls.return_value
        mock_sdk.chat.completions.create.return_value = iter([chunk])

        client = Client(api_key="sk-test")
        chunks = list(
            client.chat_stream(
                messages=[{"role": "user", "content": "hi"}],
            )
        )

        assert len(chunks) == 1
        assert chunks[0].delta_content == ""


class TestValidateKey:
    """Test API key validation."""

    @patch("zhi.client.ZhipuAI")
    def test_validate_key_success(self, mock_sdk_cls: MagicMock) -> None:
        mock_sdk = mock_sdk_cls.return_value
        mock_sdk.chat.completions.create.return_value = _make_response("hi")

        client = Client(api_key="sk-test")
        assert client.validate_key() is True

    @patch("zhi.client.ZhipuAI")
    def test_validate_key_auth_failure(self, mock_sdk_cls: MagicMock) -> None:
        mock_sdk = mock_sdk_cls.return_value
        error = Exception("unauthorized")
        error.status_code = 401  # type: ignore[attr-defined]
        mock_sdk.chat.completions.create.side_effect = error

        client = Client(api_key="sk-bad")
        assert client.validate_key() is False

    @patch("zhi.client.time")
    @patch("zhi.client.ZhipuAI")
    def test_validate_key_non_auth_error_returns_true(
        self,
        mock_sdk_cls: MagicMock,
        mock_time: MagicMock,
    ) -> None:
        """Non-auth errors (server error) mean key is valid."""
        mock_time.sleep = MagicMock()
        mock_sdk = mock_sdk_cls.return_value
        error = Exception("server error")
        error.status_code = 500  # type: ignore[attr-defined]
        mock_sdk.chat.completions.create.side_effect = error

        client = Client(api_key="sk-test", max_retries=0)
        # ServerError is non-auth, so validate_key should catch it
        # and return True (key is valid, server just errored)
        assert client.validate_key() is True


class TestOCR:
    """Test OCR functionality."""

    @patch("zhi.client.ZhipuAI")
    def test_ocr_basic(self, mock_sdk_cls: MagicMock, tmp_path: Path) -> None:
        mock_sdk = mock_sdk_cls.return_value
        mock_file_result = SimpleNamespace(id="file-123")
        mock_content = SimpleNamespace(content="Extracted text from PDF")
        mock_sdk.files.create.return_value = mock_file_result
        mock_sdk.files.content.return_value = mock_content

        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 fake pdf content")

        client = Client(api_key="sk-test")
        result = client.ocr(test_file)

        assert result == "Extracted text from PDF"
        mock_sdk.files.create.assert_called_once()
        mock_sdk.files.content.assert_called_once_with(file_id="file-123")

    @patch("zhi.client.ZhipuAI")
    def test_ocr_file_too_large(self, mock_sdk_cls: MagicMock, tmp_path: Path) -> None:
        test_file = tmp_path / "large.pdf"
        # Create a file larger than 20MB
        test_file.write_bytes(b"x" * (21 * 1024 * 1024))

        client = Client(api_key="sk-test")
        with pytest.raises(ClientError) as exc_info:
            client.ocr(test_file)
        assert "too large" in str(exc_info.value).lower()
        assert exc_info.value.code == "FILE_TOO_LARGE"

    @patch("zhi.client.ZhipuAI")
    def test_ocr_file_not_found(self, mock_sdk_cls: MagicMock) -> None:
        client = Client(api_key="sk-test")
        with pytest.raises(ClientError):
            client.ocr(Path("/nonexistent/file.pdf"))

    @patch("zhi.client.ZhipuAI")
    def test_file_extract_oserror_on_exists(
        self, mock_sdk_cls: MagicMock, tmp_path: Path
    ) -> None:
        """Bug 11: OSError on exists()/stat() converted to ClientError."""
        test_file = tmp_path / "network.pdf"
        test_file.write_bytes(b"%PDF content")

        client = Client(api_key="sk-test")

        orig_exists = Path.exists

        def patched_exists(self_path: Path) -> bool:
            if self_path.name == "network.pdf":
                raise OSError("Network timeout")
            return orig_exists(self_path)

        with (
            patch.object(Path, "exists", patched_exists),
            pytest.raises(ClientError) as exc_info,
        ):
            client.file_extract(test_file)
        assert exc_info.value.code == "FILE_ACCESS_ERROR"

    @patch("zhi.client.ZhipuAI")
    def test_ocr_unsupported_format(
        self, mock_sdk_cls: MagicMock, tmp_path: Path
    ) -> None:
        test_file = tmp_path / "test.xyz"
        test_file.write_text("some content")

        client = Client(api_key="sk-test")
        with pytest.raises(ClientError) as exc_info:
            client.ocr(test_file)
        assert exc_info.value.code == "UNSUPPORTED_FORMAT"

    @patch("zhi.client.ZhipuAI")
    def test_file_extract_xlsx(self, mock_sdk_cls: MagicMock, tmp_path: Path) -> None:
        mock_sdk = mock_sdk_cls.return_value
        mock_file_result = SimpleNamespace(id="file-456")
        mock_content = SimpleNamespace(content="Sheet1 data here")
        mock_sdk.files.create.return_value = mock_file_result
        mock_sdk.files.content.return_value = mock_content

        test_file = tmp_path / "prices.xlsx"
        test_file.write_bytes(b"PK\x03\x04 fake xlsx")

        client = Client(api_key="sk-test")
        result = client.file_extract(test_file)

        assert result == "Sheet1 data here"
        mock_sdk.files.create.assert_called_once()

    @patch("zhi.client.ZhipuAI")
    def test_file_extract_docx(self, mock_sdk_cls: MagicMock, tmp_path: Path) -> None:
        mock_sdk = mock_sdk_cls.return_value
        mock_file_result = SimpleNamespace(id="file-789")
        mock_content = SimpleNamespace(content="Document text")
        mock_sdk.files.create.return_value = mock_file_result
        mock_sdk.files.content.return_value = mock_content

        test_file = tmp_path / "report.docx"
        test_file.write_bytes(b"PK\x03\x04 fake docx")

        client = Client(api_key="sk-test")
        result = client.file_extract(test_file)

        assert result == "Document text"

    @patch("zhi.client.ZhipuAI")
    def test_ocr_still_works_as_alias(
        self, mock_sdk_cls: MagicMock, tmp_path: Path
    ) -> None:
        """Ensure ocr() still works for backward compat."""
        mock_sdk = mock_sdk_cls.return_value
        mock_file_result = SimpleNamespace(id="file-111")
        mock_content = SimpleNamespace(content="PDF text")
        mock_sdk.files.create.return_value = mock_file_result
        mock_sdk.files.content.return_value = mock_content

        test_file = tmp_path / "doc.pdf"
        test_file.write_bytes(b"%PDF-1.4 content")

        client = Client(api_key="sk-test")
        result = client.ocr(test_file)
        assert result == "PDF text"


class TestFileExtractFallback:
    """Test file_extract str() fallback logging."""

    @patch("zhi.client.ZhipuAI")
    def test_file_extract_no_content_attr_logs_warning(
        self, mock_sdk_cls: MagicMock, tmp_path: Path
    ) -> None:
        """When result has no 'content' attr, a warning is logged."""
        mock_sdk = mock_sdk_cls.return_value
        mock_file_result = SimpleNamespace(id="file-999")
        # Return a plain string (no 'content' attribute)
        mock_sdk.files.create.return_value = mock_file_result
        mock_sdk.files.content.return_value = "raw string result"

        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 fake content")

        client = Client(api_key="sk-test")
        with patch("zhi.client.logger") as mock_logger:
            result = client.file_extract(test_file)

        assert result == "raw string result"
        mock_logger.warning.assert_called_once()
        warning_msg = mock_logger.warning.call_args.args[0]
        assert (
            "no 'content' attribute" in warning_msg.lower() or "content" in warning_msg
        )

    @patch("zhi.client.ZhipuAI")
    def test_file_extract_with_content_attr_no_warning(
        self, mock_sdk_cls: MagicMock, tmp_path: Path
    ) -> None:
        """When result has 'content' attr, no warning is logged."""
        mock_sdk = mock_sdk_cls.return_value
        mock_file_result = SimpleNamespace(id="file-888")
        mock_content = SimpleNamespace(content="Extracted text")
        mock_sdk.files.create.return_value = mock_file_result
        mock_sdk.files.content.return_value = mock_content

        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 fake content")

        client = Client(api_key="sk-test")
        with patch("zhi.client.logger") as mock_logger:
            result = client.file_extract(test_file)

        assert result == "Extracted text"
        mock_logger.warning.assert_not_called()


class TestErrorClassification:
    """Test error classification logic."""

    @patch("zhi.client.ZhipuAI")
    def test_connection_error(self, mock_sdk_cls: MagicMock) -> None:
        mock_sdk = mock_sdk_cls.return_value
        mock_sdk.chat.completions.create.side_effect = Exception("connection refused")

        client = Client(api_key="sk-test", max_retries=0)
        with pytest.raises(ClientError) as exc_info:
            client.chat(
                messages=[{"role": "user", "content": "hi"}],
            )
        assert exc_info.value.code == "CONNECTION"

    @patch("zhi.client.ZhipuAI")
    def test_unknown_error(self, mock_sdk_cls: MagicMock) -> None:
        mock_sdk = mock_sdk_cls.return_value
        mock_sdk.chat.completions.create.side_effect = Exception("something unexpected")

        client = Client(api_key="sk-test", max_retries=0)
        with pytest.raises(ClientError) as exc_info:
            client.chat(
                messages=[{"role": "user", "content": "hi"}],
            )
        assert exc_info.value.code == "CLIENT_ERROR"

    @patch("zhi.client.ZhipuAI")
    def test_status_code_zero_not_masked(self, mock_sdk_cls: MagicMock) -> None:
        """status_code=0 should be used as error_code, not skipped as falsy."""
        client = Client(api_key="sk-test", max_retries=0)
        error = Exception("some error")
        error.status_code = 0  # type: ignore[attr-defined]
        error.code = 429  # type: ignore[attr-defined]
        # With the old `or` logic, status_code=0 would be falsy and
        # error.code=429 would be used instead, causing a false RateLimitError.
        # With `is not None`, status_code=0 is preserved.
        classified = client._classify_error(error)
        # status_code=0 doesn't match any known codes, so it falls through
        # to the generic ClientError — NOT RateLimitError
        from zhi.client import RateLimitError

        assert not isinstance(classified, RateLimitError)
        assert classified.code == "CLIENT_ERROR"
