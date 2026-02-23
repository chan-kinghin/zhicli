"""Tests for zhi.agent module."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest

from zhi.agent import (
    ChatResponse,
    Context,
    PermissionMode,
    Role,
    run,
)
from zhi.config import ZhiConfig


# --- Test helpers ---


@dataclass
class MockResponse:
    """Mock response from client.chat()."""

    content: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    thinking: str | None = None
    total_tokens: int = 100


class MockTool:
    """Simple mock tool for testing."""

    def __init__(
        self,
        name: str = "mock_tool",
        risky: bool = False,
        result: str = "tool result",
        raises: Exception | None = None,
    ) -> None:
        self._name = name
        self._risky = risky
        self._result = result
        self._raises = raises
        self.call_count = 0
        self.last_kwargs: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def risky(self) -> bool:
        return self._risky

    def execute(self, **kwargs: Any) -> str:
        self.call_count += 1
        self.last_kwargs = kwargs
        if self._raises:
            raise self._raises
        return self._result


def _make_tool_call(
    name: str = "mock_tool",
    arguments: dict[str, Any] | None = None,
    call_id: str = "call_1",
) -> dict[str, Any]:
    """Create a tool call dict."""
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments or {}),
        },
    }


def _make_context(
    responses: list[MockResponse],
    tools: dict[str, MockTool] | None = None,
    permission_mode: PermissionMode = PermissionMode.APPROVE,
    max_turns: int = 30,
    on_permission: Any = None,
    on_stream: Any = None,
    on_thinking: Any = None,
    on_tool_start: Any = None,
    on_tool_end: Any = None,
) -> Context:
    """Create a Context with a mock client that returns given responses."""
    client = MagicMock()
    response_iter = iter(responses)
    client.chat.side_effect = lambda **kwargs: next(response_iter)

    if tools is None:
        tools = {}

    tool_schemas = [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": f"Mock {t.name}",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        for t in tools.values()
    ]

    return Context(
        config=ZhiConfig(),
        client=client,
        model="glm-5",
        tools=tools,
        tool_schemas=tool_schemas,
        permission_mode=permission_mode,
        max_turns=max_turns,
        on_stream=on_stream,
        on_thinking=on_thinking,
        on_tool_start=on_tool_start,
        on_tool_end=on_tool_end,
        on_permission=on_permission,
    )


# --- Tests ---


class TestAgentSingleTurn:
    """Test single-turn agent interactions."""

    def test_agent_single_turn_text(self) -> None:
        """Agent returns text response without tool calls."""
        responses = [MockResponse(content="Hello!")]
        ctx = _make_context(responses)

        result = run(ctx)

        assert result == "Hello!"
        ctx.client.chat.assert_called_once()

    def test_agent_empty_response(self) -> None:
        """Agent handles empty content with no tool calls."""
        responses = [MockResponse(content=None)]
        ctx = _make_context(responses)

        result = run(ctx)

        assert result is None


class TestAgentToolCalls:
    """Test tool call handling."""

    def test_agent_single_tool_call(self) -> None:
        """Agent executes a single tool call and returns final text."""
        tool = MockTool(name="file_read", result="file contents")
        responses = [
            MockResponse(
                content=None,
                tool_calls=[_make_tool_call("file_read", {"path": "test.txt"})],
            ),
            MockResponse(content="I read the file. It says: file contents"),
        ]
        ctx = _make_context(responses, tools={"file_read": tool})

        result = run(ctx)

        assert result == "I read the file. It says: file contents"
        assert tool.call_count == 1
        assert tool.last_kwargs == {"path": "test.txt"}

    def test_agent_multi_tool_calls(self) -> None:
        """Agent handles multiple tool calls in a single response."""
        tool_a = MockTool(name="tool_a", result="result_a")
        tool_b = MockTool(name="tool_b", result="result_b")
        responses = [
            MockResponse(
                content=None,
                tool_calls=[
                    _make_tool_call("tool_a", call_id="call_1"),
                    _make_tool_call("tool_b", call_id="call_2"),
                ],
            ),
            MockResponse(content="Both tools done"),
        ]
        ctx = _make_context(
            responses,
            tools={"tool_a": tool_a, "tool_b": tool_b},
        )

        result = run(ctx)

        assert result == "Both tools done"
        assert tool_a.call_count == 1
        assert tool_b.call_count == 1

    def test_agent_multi_turn_loop(self) -> None:
        """Agent handles multi-turn tool calling loop."""
        tool = MockTool(name="file_read")
        responses = [
            MockResponse(
                tool_calls=[_make_tool_call("file_read", call_id="c1")],
            ),
            MockResponse(
                tool_calls=[_make_tool_call("file_read", call_id="c2")],
            ),
            MockResponse(content="All done after 3 turns"),
        ]
        ctx = _make_context(responses, tools={"file_read": tool})

        result = run(ctx)

        assert result == "All done after 3 turns"
        assert tool.call_count == 2
        assert ctx.client.chat.call_count == 3


class TestAgentMaxTurns:
    """Test max_turns limit."""

    def test_agent_max_turns_limit(self) -> None:
        """Agent returns None when max_turns is reached."""
        tool = MockTool(name="file_read")
        # Create responses that always have tool calls (infinite loop)
        responses = [
            MockResponse(
                tool_calls=[_make_tool_call("file_read", call_id=f"c{i}")],
            )
            for i in range(5)
        ]
        ctx = _make_context(responses, tools={"file_read": tool}, max_turns=3)

        result = run(ctx)

        assert result is None
        assert ctx.client.chat.call_count == 3


class TestAgentPermissions:
    """Test permission handling."""

    def test_agent_permission_approve(self) -> None:
        """Agent proceeds when user approves risky tool."""
        tool = MockTool(name="file_write", risky=True, result="wrote file")
        on_permission = MagicMock(return_value=True)
        responses = [
            MockResponse(
                tool_calls=[_make_tool_call("file_write", {"path": "out.md"})],
            ),
            MockResponse(content="File written"),
        ]
        ctx = _make_context(
            responses,
            tools={"file_write": tool},
            on_permission=on_permission,
        )

        result = run(ctx)

        assert result == "File written"
        assert tool.call_count == 1
        on_permission.assert_called_once()

    def test_agent_permission_deny(self) -> None:
        """Agent skips tool when user denies permission."""
        tool = MockTool(name="file_write", risky=True)
        on_permission = MagicMock(return_value=False)
        responses = [
            MockResponse(
                tool_calls=[_make_tool_call("file_write", call_id="c1")],
            ),
            MockResponse(content="OK, I won't write the file"),
        ]
        ctx = _make_context(
            responses,
            tools={"file_write": tool},
            on_permission=on_permission,
        )

        result = run(ctx)

        assert result == "OK, I won't write the file"
        assert tool.call_count == 0
        # Verify "Permission denied" was added to conversation
        tool_msgs = [
            m
            for m in ctx.conversation
            if m.get("role") == "tool" and "Permission denied" in m.get("content", "")
        ]
        assert len(tool_msgs) == 1

    def test_agent_safe_tool_no_prompt(self) -> None:
        """Safe tools don't trigger permission prompt in approve mode."""
        tool = MockTool(name="file_read", risky=False, result="contents")
        on_permission = MagicMock(return_value=False)  # Should not be called
        responses = [
            MockResponse(
                tool_calls=[_make_tool_call("file_read")],
            ),
            MockResponse(content="Done"),
        ]
        ctx = _make_context(
            responses,
            tools={"file_read": tool},
            on_permission=on_permission,
        )

        result = run(ctx)

        assert result == "Done"
        assert tool.call_count == 1
        on_permission.assert_not_called()

    def test_agent_auto_mode(self) -> None:
        """In auto mode, risky tools execute without permission prompt."""
        tool = MockTool(name="file_write", risky=True, result="wrote it")
        on_permission = MagicMock(return_value=False)  # Should not be called
        responses = [
            MockResponse(
                tool_calls=[_make_tool_call("file_write")],
            ),
            MockResponse(content="Done"),
        ]
        ctx = _make_context(
            responses,
            tools={"file_write": tool},
            permission_mode=PermissionMode.AUTO,
            on_permission=on_permission,
        )

        result = run(ctx)

        assert result == "Done"
        assert tool.call_count == 1
        on_permission.assert_not_called()


class TestAgentErrorHandling:
    """Test error handling in the agent loop."""

    def test_agent_unknown_tool(self) -> None:
        """Agent handles unknown tool names gracefully."""
        responses = [
            MockResponse(
                tool_calls=[_make_tool_call("nonexistent_tool")],
            ),
            MockResponse(content="Sorry, that tool doesn't exist"),
        ]
        ctx = _make_context(responses)

        result = run(ctx)

        assert result == "Sorry, that tool doesn't exist"
        # Verify error message was added to conversation
        tool_msgs = [
            m
            for m in ctx.conversation
            if m.get("role") == "tool" and "Unknown tool" in m.get("content", "")
        ]
        assert len(tool_msgs) == 1

    def test_agent_tool_execution_error(self) -> None:
        """Agent handles tool execution errors gracefully."""
        tool = MockTool(
            name="file_read",
            raises=FileNotFoundError("test.txt not found"),
        )
        responses = [
            MockResponse(
                tool_calls=[_make_tool_call("file_read")],
            ),
            MockResponse(content="File not found, trying something else"),
        ]
        ctx = _make_context(responses, tools={"file_read": tool})

        result = run(ctx)

        assert result == "File not found, trying something else"
        tool_msgs = [
            m
            for m in ctx.conversation
            if m.get("role") == "tool" and "Error executing" in m.get("content", "")
        ]
        assert len(tool_msgs) == 1


class TestAgentConversation:
    """Test conversation history management."""

    def test_agent_message_history(self) -> None:
        """Agent properly accumulates messages in conversation."""
        tool = MockTool(name="file_read", result="contents")
        responses = [
            MockResponse(
                content="Let me read that",
                tool_calls=[_make_tool_call("file_read", call_id="c1")],
            ),
            MockResponse(content="File says: contents"),
        ]
        ctx = _make_context(responses, tools={"file_read": tool})
        ctx.conversation = [
            {"role": "user", "content": "Read test.txt"},
        ]

        run(ctx)

        # Should have: user msg, assistant msg with tool_calls, tool result
        roles = [m["role"] for m in ctx.conversation]
        assert roles == ["user", "assistant", "tool"]

    def test_agent_token_tracking(self) -> None:
        """Agent tracks tokens across turns."""
        responses = [
            MockResponse(
                content=None, tool_calls=[_make_tool_call("t")], total_tokens=50
            ),
            MockResponse(content="Done", total_tokens=30),
        ]
        tool = MockTool(name="t")
        ctx = _make_context(responses, tools={"t": tool})

        run(ctx)

        assert ctx.session_tokens == 80


class TestAgentCallbacks:
    """Test callback invocations."""

    def test_agent_on_stream_called(self) -> None:
        """on_stream callback is called with content."""
        on_stream = MagicMock()
        responses = [MockResponse(content="Hello!")]
        ctx = _make_context(responses, on_stream=on_stream)

        run(ctx)

        on_stream.assert_called_once_with("Hello!")

    def test_agent_on_thinking_called(self) -> None:
        """on_thinking callback is called with thinking text."""
        on_thinking = MagicMock()
        responses = [MockResponse(content="Answer", thinking="Let me think...")]
        ctx = _make_context(responses, on_thinking=on_thinking)

        run(ctx)

        on_thinking.assert_called_once_with("Let me think...")

    def test_agent_on_tool_callbacks(self) -> None:
        """on_tool_start and on_tool_end callbacks are called."""
        on_tool_start = MagicMock()
        on_tool_end = MagicMock()
        tool = MockTool(name="file_read", result="data")
        responses = [
            MockResponse(
                tool_calls=[_make_tool_call("file_read", {"path": "f.txt"})],
            ),
            MockResponse(content="Done"),
        ]
        ctx = _make_context(
            responses,
            tools={"file_read": tool},
            on_tool_start=on_tool_start,
            on_tool_end=on_tool_end,
        )

        run(ctx)

        on_tool_start.assert_called_once_with("file_read", {"path": "f.txt"})
        on_tool_end.assert_called_once_with("file_read", "data")


class TestAgentOutputTruncation:
    """Test tool output truncation at 50KB."""

    def test_agent_output_truncation(self) -> None:
        """Tool output is truncated at 50KB."""
        large_result = "x" * 60_000
        tool = MockTool(name="file_read", result=large_result)
        responses = [
            MockResponse(
                tool_calls=[_make_tool_call("file_read")],
            ),
            MockResponse(content="Done"),
        ]
        ctx = _make_context(responses, tools={"file_read": tool})

        run(ctx)

        # Find the tool result message
        tool_msgs = [
            m
            for m in ctx.conversation
            if m.get("role") == "tool" and m.get("tool_call_id") == "call_1"
        ]
        assert len(tool_msgs) == 1
        result_content = tool_msgs[0]["content"]
        assert "[truncated" in result_content
        assert len(result_content) < 60_000

    def test_agent_output_not_truncated_under_limit(self) -> None:
        """Tool output under 50KB is not truncated."""
        small_result = "x" * 100
        tool = MockTool(name="file_read", result=small_result)
        responses = [
            MockResponse(
                tool_calls=[_make_tool_call("file_read")],
            ),
            MockResponse(content="Done"),
        ]
        ctx = _make_context(responses, tools={"file_read": tool})

        run(ctx)

        tool_msgs = [
            m
            for m in ctx.conversation
            if m.get("role") == "tool" and m.get("tool_call_id") == "call_1"
        ]
        assert tool_msgs[0]["content"] == small_result


class TestAgentArgParsing:
    """Test tool argument parsing edge cases."""

    def test_agent_dict_arguments(self) -> None:
        """Agent handles arguments already as dict."""
        tool = MockTool(name="t", result="ok")
        call = {
            "id": "c1",
            "type": "function",
            "function": {
                "name": "t",
                "arguments": {"key": "value"},  # Already a dict
            },
        }
        responses = [
            MockResponse(tool_calls=[call]),
            MockResponse(content="Done"),
        ]
        ctx = _make_context(responses, tools={"t": tool})

        run(ctx)

        assert tool.last_kwargs == {"key": "value"}

    def test_agent_malformed_json_arguments(self) -> None:
        """Agent handles malformed JSON arguments gracefully."""
        tool = MockTool(name="t", result="ok")
        call = {
            "id": "c1",
            "type": "function",
            "function": {
                "name": "t",
                "arguments": "not valid json{{{",
            },
        }
        responses = [
            MockResponse(tool_calls=[call]),
            MockResponse(content="Done"),
        ]
        ctx = _make_context(responses, tools={"t": tool})

        run(ctx)

        # Should fall back to empty args
        assert tool.last_kwargs == {}
