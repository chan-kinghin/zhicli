"""Zhipu API client with streaming, retry, and error handling."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from zhipuai import ZhipuAI

from zhi.errors import ApiError

logger = logging.getLogger(__name__)

_MAX_OCR_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@dataclass
class ChatResponse:
    """Parsed chat completion response."""

    content: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    thinking: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = ""
    raw: Any = None


@dataclass
class ChatChunk:
    """A single chunk from streaming response."""

    delta_content: str = ""
    delta_thinking: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str | None = None
    usage: dict[str, int] | None = None


class ClientError(ApiError):
    """Base error for client operations.

    Inherits from ApiError so callers catching ZhiError/ApiError
    also catch client-level errors.
    """

    def __init__(
        self,
        message: str,
        code: str = "CLIENT_ERROR",
        retryable: bool = False,
    ) -> None:
        super().__init__(message, code=code)
        self.retryable = retryable


class AuthenticationError(ClientError):
    """API key is invalid or missing."""

    def __init__(self, message: str = "Invalid API key") -> None:
        super().__init__(message, code="AUTH_ERROR", retryable=False)


class RateLimitError(ClientError):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message, code="RATE_LIMIT", retryable=True)


class ServerError(ClientError):
    """Server-side error."""

    def __init__(self, message: str = "Server error") -> None:
        super().__init__(message, code="SERVER_ERROR", retryable=True)


class Client:
    """Zhipu API client with retry and streaming support."""

    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
        timeout: float = 60.0,
    ) -> None:
        self._sdk = ZhipuAI(api_key=api_key)
        self._max_retries = max_retries
        self._timeout = timeout

    def chat(
        self,
        messages: list[dict[str, Any]],
        model: str = "glm-5",
        tools: list[dict[str, Any]] | None = None,
        thinking: bool = False,
    ) -> ChatResponse:
        """Non-streaming chat completion. Returns complete response."""

        def _call() -> Any:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools
            if thinking:
                kwargs["extra_body"] = {"thinking": True}
            return self._sdk.chat.completions.create(**kwargs)

        raw = self._call_with_retry(_call)
        return self._parse_response(raw)

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        model: str = "glm-5",
        tools: list[dict[str, Any]] | None = None,
        thinking: bool = False,
    ) -> Iterator[ChatChunk]:
        """Streaming chat completion. Yields chunks for live display."""

        def _call() -> Any:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "stream": True,
            }
            if tools:
                kwargs["tools"] = tools
            if thinking:
                kwargs["extra_body"] = {"thinking": True}
            return self._sdk.chat.completions.create(**kwargs)

        stream = self._call_with_retry(_call)
        for chunk_raw in stream:
            yield self._parse_chunk(chunk_raw)

    def validate_key(self) -> bool:
        """Quick validation of API key by making a minimal API call."""
        try:
            self.chat(
                messages=[{"role": "user", "content": "1"}],
                model="glm-4-flash",
            )
            return True
        except AuthenticationError:
            return False
        except ClientError:
            return True  # Non-auth errors mean the key is valid

    def ocr(self, file_path: Path) -> str:
        """OCR a file via Zhipu layout parsing API.

        Submits file, polls for async result, returns extracted text.
        Rejects files over 20MB. Uses streaming upload.
        """
        if not file_path.exists():
            raise ClientError(f"File not found: {file_path}")

        file_size = file_path.stat().st_size
        if file_size > _MAX_OCR_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            raise ClientError(
                f"File too large for OCR ({size_mb:.1f}MB). Maximum: 20MB.",
                code="FILE_TOO_LARGE",
            )

        supported = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp"}
        if file_path.suffix.lower() not in supported:
            raise ClientError(
                f"Unsupported file type for OCR: {file_path.suffix}. "
                f"Supported: {', '.join(sorted(supported))}",
                code="UNSUPPORTED_FORMAT",
            )

        def _call() -> Any:
            with open(file_path, "rb") as f:
                # Use the SDK's file upload for OCR
                result = self._sdk.files.create(
                    file=f,
                    purpose="file-extract",
                )
            # Extract content from the file
            content = self._sdk.files.content(file_id=result.id)
            return content

        try:
            result = self._call_with_retry(_call)
            if hasattr(result, "content"):
                return str(result.content)
            return str(result)
        except ClientError:
            raise
        except Exception as exc:
            raise ClientError(f"OCR failed: {exc}", code="OCR_ERROR") from exc

    def _call_with_retry(self, fn: Any) -> Any:
        """Execute with exponential backoff retry for transient errors."""
        for attempt in range(self._max_retries + 1):
            try:
                return fn()
            except ClientError:
                raise
            except Exception as exc:
                error = self._classify_error(exc)
                if not error.retryable or attempt == self._max_retries:
                    raise error from exc
                wait = min(2**attempt + random.uniform(0, 1), 30)
                logger.info(
                    "Retry %d/%d after %.1fs: %s",
                    attempt + 1,
                    self._max_retries,
                    wait,
                    error,
                )
                time.sleep(wait)
        raise ClientError("Max retries exceeded")  # pragma: no cover

    def _classify_error(self, error: Exception) -> ClientError:
        """Classify SDK/HTTP errors into typed errors."""
        error_str = str(error).lower()
        error_code = getattr(error, "status_code", None) or getattr(error, "code", None)

        if (
            error_code in (401, 403)
            or "unauthorized" in error_str
            or "invalid api key" in error_str
            or "authentication" in error_str
        ):
            return AuthenticationError()
        if error_code == 429 or "rate limit" in error_str:
            return RateLimitError()
        if error_code in (500, 502, 503) or "server error" in error_str:
            return ServerError()
        if "timeout" in error_str or "timed out" in error_str:
            return ClientError("Request timed out", code="TIMEOUT", retryable=True)
        if "connection" in error_str:
            return ClientError("Connection failed", code="CONNECTION", retryable=True)

        return ClientError(str(error))

    def _parse_response(self, raw: Any) -> ChatResponse:
        """Parse SDK response into ChatResponse."""
        if not raw.choices:
            raise ClientError(
                "API returned empty response (no choices)",
                code="EMPTY_RESPONSE",
                retryable=True,
            )
        choice = raw.choices[0]
        msg = choice.message
        usage = raw.usage

        tool_calls_raw: list[dict[str, Any]] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_raw.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                )

        thinking = None
        if hasattr(msg, "thinking") and msg.thinking:
            thinking = msg.thinking

        return ChatResponse(
            content=msg.content,
            tool_calls=tool_calls_raw,
            thinking=thinking,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            finish_reason=choice.finish_reason or "",
            raw=raw,
        )

    def _parse_chunk(self, chunk_raw: Any) -> ChatChunk:
        """Parse a single streaming chunk."""
        if not chunk_raw.choices:
            return ChatChunk(usage=getattr(chunk_raw, "usage", None))

        delta = chunk_raw.choices[0].delta

        tool_calls_raw: list[dict[str, Any]] = []
        if hasattr(delta, "tool_calls") and delta.tool_calls:
            for tc in delta.tool_calls:
                tool_calls_raw.append(
                    {
                        "index": tc.index if hasattr(tc, "index") else 0,
                        "id": getattr(tc, "id", None),
                        "type": "function",
                        "function": {
                            "name": (
                                getattr(tc.function, "name", "") if tc.function else ""
                            ),
                            "arguments": (
                                getattr(tc.function, "arguments", "")
                                if tc.function
                                else ""
                            ),
                        },
                    }
                )

        return ChatChunk(
            delta_content=delta.content or "",
            delta_thinking=getattr(delta, "thinking", "") or "",
            tool_calls=tool_calls_raw,
            finish_reason=chunk_raw.choices[0].finish_reason,
        )
