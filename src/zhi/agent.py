"""Agent loop -- the core of zhi's agentic behavior.

The agent loop sends messages to the LLM, dispatches tool calls,
accumulates results, and repeats until the model returns a text-only response
or max_turns is reached.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# Max tool output size in bytes before truncation
_MAX_TOOL_OUTPUT = 50_000


class Role(str, Enum):
    """Message roles for the conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class PermissionMode(str, Enum):
    """Permission modes for tool execution."""

    APPROVE = "approve"
    AUTO = "auto"


class ToolLike(Protocol):
    """Minimal tool interface for the agent loop."""

    @property
    def name(self) -> str: ...

    @property
    def risky(self) -> bool: ...

    def execute(self, **kwargs: Any) -> str: ...


class ClientLike(Protocol):
    """Minimal client interface for the agent loop."""

    def chat(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None,
        thinking: bool,
    ) -> Any: ...


@dataclass
class Context:
    """Request-scoped state for the agent loop."""

    config: Any
    client: ClientLike
    model: str
    tools: dict[str, ToolLike]
    tool_schemas: list[dict[str, Any]]
    permission_mode: PermissionMode
    conversation: list[dict[str, Any]] = field(default_factory=list)
    session_tokens: int = 0
    max_turns: int = 30
    thinking_enabled: bool = True
    cancel_event: threading.Event = field(default_factory=threading.Event)
    # Callbacks
    on_stream_start: Callable[[], None] | None = None
    on_stream: Callable[[str], None] | None = None
    on_thinking: Callable[[str], None] | None = None
    on_tool_start: Callable[[str, dict[str, Any]], None] | None = None
    on_tool_end: Callable[[str, str], None] | None = None
    on_waiting: Callable[[str], None] | None = None
    on_waiting_done: Callable[[], None] | None = None
    on_tool_total: Callable[[int], None] | None = None
    on_permission: Callable[[ToolLike, dict[str, Any]], bool] | None = None
    # File counters for summary line
    files_read: int = 0
    files_written: int = 0
    # Streaming mode (use chat_stream when available)
    streaming: bool = True


def safe_parse_args(raw_args: Any) -> dict[str, Any]:
    """Safely parse tool call arguments, returning empty dict on failure."""
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            return json.loads(raw_args)
        except (json.JSONDecodeError, ValueError):
            return {"_raw": raw_args}
    return {}


class AgentInterruptedError(Exception):
    """Raised when the agent loop is interrupted by the user."""


def _can_stream(context: Context) -> bool:
    """Check if the client supports streaming and streaming is enabled."""
    return context.streaming and hasattr(context.client, "chat_stream")


@dataclass
class _TurnResult:
    """Result of a single agent turn (streaming or buffered)."""

    content: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0


def _do_turn_streaming(context: Context) -> _TurnResult:
    """Execute a single turn using streaming, displaying tokens live."""
    on_stream_start = getattr(context, "on_stream_start", None)
    if on_stream_start:
        on_stream_start()

    content_parts: list[str] = []
    thinking_parts: list[str] = []
    # Accumulate tool call deltas by index
    tc_accum: dict[int, dict[str, Any]] = {}
    total_tokens = 0

    for chunk in context.client.chat_stream(
        messages=context.conversation,
        model=context.model,
        tools=context.tool_schemas or None,
        thinking=context.thinking_enabled,
    ):
        # Check cancellation during streaming
        if context.cancel_event.is_set():
            raise AgentInterruptedError("Cancelled by user")

        # Thinking deltas
        delta_thinking = getattr(chunk, "delta_thinking", "")
        if delta_thinking:
            thinking_parts.append(delta_thinking)

        # Content deltas — stream each token to UI
        delta_content = getattr(chunk, "delta_content", "")
        if delta_content:
            content_parts.append(delta_content)
            if context.on_stream:
                context.on_stream(delta_content)

        # Tool call deltas — accumulate by index
        chunk_tool_calls = getattr(chunk, "tool_calls", None) or []
        for tc_delta in chunk_tool_calls:
            idx = tc_delta.get("index", 0)
            if idx not in tc_accum:
                tc_accum[idx] = {
                    "id": tc_delta.get("id", ""),
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                }
            entry = tc_accum[idx]
            if tc_delta.get("id"):
                entry["id"] = tc_delta["id"]
            fn = tc_delta.get("function", {})
            if fn.get("name"):
                entry["function"]["name"] += fn["name"]
            if fn.get("arguments"):
                entry["function"]["arguments"] += fn["arguments"]

        # Usage from final chunk
        usage = getattr(chunk, "usage", None)
        if usage and isinstance(usage, dict):
            total_tokens = usage.get("total_tokens", 0)

    # Show thinking if accumulated
    full_thinking = "".join(thinking_parts)
    if full_thinking and context.on_thinking:
        context.on_thinking(full_thinking)

    content = "".join(content_parts) or None
    tool_calls = [tc_accum[i] for i in sorted(tc_accum)]

    return _TurnResult(
        content=content,
        tool_calls=tool_calls,
        total_tokens=total_tokens,
    )


def _do_turn_buffered(context: Context) -> _TurnResult:
    """Execute a single turn using buffered (non-streaming) API call."""
    response = context.client.chat(
        messages=context.conversation,
        model=context.model,
        tools=context.tool_schemas or None,
        thinking=context.thinking_enabled,
    )

    total_tokens = getattr(response, "total_tokens", 0)

    # Show thinking
    thinking = getattr(response, "thinking", None)
    if thinking and context.on_thinking:
        context.on_thinking(thinking)

    # Show content
    content = getattr(response, "content", None)
    if content and context.on_stream:
        context.on_stream(content)

    tool_calls = getattr(response, "tool_calls", None) or []

    return _TurnResult(
        content=content,
        tool_calls=tool_calls,
        total_tokens=total_tokens,
    )


def _execute_tool_calls(context: Context, tool_calls: list[dict[str, Any]]) -> None:
    """Execute tool calls and append results to conversation."""
    # Notify tool total for step counter
    if context.on_tool_total:
        context.on_tool_total(len(tool_calls))

    for call in tool_calls:
        # Check for cancellation between tool calls
        if context.cancel_event.is_set():
            raise AgentInterruptedError("Cancelled by user")

        func_name = call["function"]["name"]
        call_id = call["id"]

        # Unknown tool
        if func_name not in context.tools:
            logger.warning("Unknown tool requested: %s", func_name)
            context.conversation.append(
                {
                    "role": Role.TOOL.value,
                    "tool_call_id": call_id,
                    "content": f"Error: Unknown tool '{func_name}'",
                }
            )
            continue

        tool = context.tools[func_name]

        # Permission check
        if (
            tool.risky
            and context.permission_mode == PermissionMode.APPROVE
            and context.on_permission
            and not context.on_permission(tool, call)
        ):
            context.conversation.append(
                {
                    "role": Role.TOOL.value,
                    "tool_call_id": call_id,
                    "content": "Permission denied by user",
                }
            )
            continue

        # Parse arguments
        try:
            raw_args = call["function"]["arguments"]
            if isinstance(raw_args, str):
                args = json.loads(raw_args)
            elif isinstance(raw_args, dict):
                args = raw_args
            else:
                args = {}
        except (json.JSONDecodeError, TypeError):
            args = {}

        # Notify tool start
        if context.on_tool_start:
            context.on_tool_start(func_name, args)

        # Execute tool
        try:
            result = tool.execute(**args)
            # Cap output at 50KB
            if len(result) > _MAX_TOOL_OUTPUT:
                truncated_size = len(result)
                result = (
                    result[:_MAX_TOOL_OUTPUT]
                    + "\n[truncated, showing first "
                    + f"{_MAX_TOOL_OUTPUT} of {truncated_size} chars]"
                )
        except Exception as e:
            logger.exception("Tool %s failed", func_name)
            result = f"Error executing {func_name}: {e}"

        # Notify tool end
        if context.on_tool_end:
            context.on_tool_end(func_name, result)

        # Count files for summary
        if func_name == "file_read" and not result.startswith("Error"):
            context.files_read += 1
        elif func_name == "file_write" and "written" in result.lower():
            context.files_written += 1

        # Append tool result to conversation
        context.conversation.append(
            {
                "role": Role.TOOL.value,
                "tool_call_id": call_id,
                "content": result,
            }
        )


def run(context: Context) -> str | None:
    """Run the agent loop until text response or max_turns.

    Returns the final text content, or None if max_turns reached.
    Uses streaming when available for token-by-token display.
    """
    use_streaming = _can_stream(context)

    for turn in range(context.max_turns):
        logger.debug("Agent turn %d/%d", turn + 1, context.max_turns)

        # Check for cancellation at the start of each turn
        if context.cancel_event.is_set():
            raise AgentInterruptedError("Cancelled by user")

        if context.on_waiting:
            context.on_waiting(context.model)

        # Execute turn (streaming or buffered)
        if use_streaming:
            # Clear waiting before streaming starts (first token will arrive soon)
            if context.on_waiting_done:
                context.on_waiting_done()
            result = _do_turn_streaming(context)
        else:
            result = _do_turn_buffered(context)
            # Clear waiting indicator now that response has arrived
            if context.on_waiting_done:
                context.on_waiting_done()

        # Track tokens
        context.session_tokens += result.total_tokens

        content = result.content
        tool_calls = result.tool_calls

        # No tool calls -- we're done
        if not tool_calls:
            # Append assistant's final message to conversation for multi-turn context
            if content:
                context.conversation.append(
                    {
                        "role": Role.ASSISTANT.value,
                        "content": content,
                    }
                )
            return content

        # Build assistant message with tool calls
        assistant_msg: dict[str, Any] = {
            "role": Role.ASSISTANT.value,
            "content": content or "",
            "tool_calls": tool_calls,
        }
        context.conversation.append(assistant_msg)

        # Execute tool calls
        _execute_tool_calls(context, tool_calls)

    # Max turns reached
    logger.warning("Agent reached max_turns (%d)", context.max_turns)
    return None
