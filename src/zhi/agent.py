"""Agent loop -- the core of zhi's agentic behavior.

The agent loop sends messages to the LLM, dispatches tool calls,
accumulates results, and repeats until the model returns a text-only response
or max_turns is reached.
"""

from __future__ import annotations

import json
import logging
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
    # Callbacks
    on_stream: Callable[[str], None] | None = None
    on_thinking: Callable[[str], None] | None = None
    on_tool_start: Callable[[str, dict[str, Any]], None] | None = None
    on_tool_end: Callable[[str, str], None] | None = None
    on_permission: Callable[[ToolLike, dict[str, Any]], bool] | None = None


class AgentInterruptedError(Exception):
    """Raised when the agent loop is interrupted by the user."""


def run(context: Context) -> str | None:
    """Run the agent loop until text response or max_turns.

    Returns the final text content, or None if max_turns reached.
    """
    for turn in range(context.max_turns):
        logger.debug("Agent turn %d/%d", turn + 1, context.max_turns)

        response = context.client.chat(
            messages=context.conversation,
            model=context.model,
            tools=context.tool_schemas or None,
            thinking=context.thinking_enabled,
        )

        # Track tokens
        total_tokens = getattr(response, "total_tokens", 0)
        context.session_tokens += total_tokens

        # Show thinking
        thinking = getattr(response, "thinking", None)
        if thinking and context.on_thinking:
            context.on_thinking(thinking)

        # Show content
        content = getattr(response, "content", None)
        if content and context.on_stream:
            context.on_stream(content)

        # Get tool calls
        tool_calls = getattr(response, "tool_calls", None) or []

        # No tool calls -- we're done
        if not tool_calls:
            return content

        # Build assistant message with tool calls
        assistant_msg: dict[str, Any] = {
            "role": Role.ASSISTANT.value,
            "content": content or "",
            "tool_calls": tool_calls,
        }
        context.conversation.append(assistant_msg)

        # Execute each tool call
        for call in tool_calls:
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
                        + f"\n[truncated, showing first 50KB of {truncated_size} bytes]"
                    )
            except Exception as e:
                logger.exception("Tool %s failed", func_name)
                result = f"Error executing {func_name}: {e}"

            # Notify tool end
            if context.on_tool_end:
                context.on_tool_end(func_name, result)

            # Append tool result to conversation
            context.conversation.append(
                {
                    "role": Role.TOOL.value,
                    "tool_call_id": call_id,
                    "content": result,
                }
            )

    # Max turns reached
    logger.warning("Agent reached max_turns (%d)", context.max_turns)
    return None
