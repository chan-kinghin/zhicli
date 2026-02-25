"""Tests for zhi.agent module."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest

from zhi.agent import (
    AgentInterruptedError,
    Context,
    PermissionMode,
    _can_stream,
    _do_turn_streaming,
    _prune_for_api,
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
    on_tool_total: Any = None,
    on_waiting: Any = None,
    streaming: bool = False,
) -> Context:
    """Create a Context with a mock client that returns given responses.

    streaming defaults to False so MagicMock's auto-attribute doesn't
    cause hasattr(client, 'chat_stream') to return True unexpectedly.
    """
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
        streaming=streaming,
        on_stream=on_stream,
        on_thinking=on_thinking,
        on_tool_start=on_tool_start,
        on_tool_end=on_tool_end,
        on_tool_total=on_tool_total,
        on_waiting=on_waiting,
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

        # Should have: user msg, assistant msg with tool_calls, tool result,
        # and final assistant response appended for multi-turn context
        roles = [m["role"] for m in ctx.conversation]
        assert roles == ["user", "assistant", "tool", "assistant"]

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

    def test_agent_on_waiting_called(self) -> None:
        """on_waiting callback is called before chat."""
        on_waiting = MagicMock()
        responses = [MockResponse(content="Hello!")]
        ctx = _make_context(responses, on_waiting=on_waiting)

        run(ctx)

        on_waiting.assert_called_once_with("glm-5")


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
        """Agent reports malformed JSON arguments back to LLM (Bug 12)."""
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

        # Tool should NOT be called — error reported as tool result instead
        assert tool.call_count == 0
        tool_msgs = [
            m
            for m in ctx.conversation
            if m.get("role") == "tool" and "Invalid JSON" in m.get("content", "")
        ]
        assert len(tool_msgs) == 1


class TestAgentToolTotal:
    """Test step counter callback."""

    def test_on_tool_total_called(self) -> None:
        """on_tool_total is called with number of tool calls."""
        on_tool_total = MagicMock()
        tool_a = MockTool(name="tool_a", result="ok")
        tool_b = MockTool(name="tool_b", result="ok")
        responses = [
            MockResponse(
                tool_calls=[
                    _make_tool_call("tool_a", call_id="c1"),
                    _make_tool_call("tool_b", call_id="c2"),
                ],
            ),
            MockResponse(content="Done"),
        ]
        ctx = _make_context(
            responses,
            tools={"tool_a": tool_a, "tool_b": tool_b},
            on_tool_total=on_tool_total,
        )

        run(ctx)

        on_tool_total.assert_called_once_with(2)

    def test_on_tool_total_not_called_without_tools(self) -> None:
        """on_tool_total is not called when there are no tool calls."""
        on_tool_total = MagicMock()
        responses = [MockResponse(content="Hello")]
        ctx = _make_context(responses, on_tool_total=on_tool_total)

        run(ctx)

        on_tool_total.assert_not_called()


class TestAgentFileCounting:
    """Test file counting for summary."""

    def test_file_read_counted(self) -> None:
        """Successful file_read increments files_read counter."""
        tool = MockTool(name="file_read", result="file contents")
        responses = [
            MockResponse(
                tool_calls=[_make_tool_call("file_read", {"path": "a.txt"})],
            ),
            MockResponse(content="Done"),
        ]
        ctx = _make_context(responses, tools={"file_read": tool})

        run(ctx)

        assert ctx.files_read == 1
        assert ctx.files_written == 0

    def test_file_write_counted(self) -> None:
        """Successful file_write increments files_written counter."""
        tool = MockTool(name="file_write", result="File written successfully")
        responses = [
            MockResponse(
                tool_calls=[_make_tool_call("file_write", {"path": "b.txt"})],
            ),
            MockResponse(content="Done"),
        ]
        ctx = _make_context(responses, tools={"file_write": tool})

        run(ctx)

        assert ctx.files_written == 1
        assert ctx.files_read == 0

    def test_failed_file_read_not_counted(self) -> None:
        """Failed file_read (result starts with Error) is not counted."""
        tool = MockTool(name="file_read", result="Error: File not found")
        responses = [
            MockResponse(
                tool_calls=[_make_tool_call("file_read")],
            ),
            MockResponse(content="Done"),
        ]
        ctx = _make_context(responses, tools={"file_read": tool})

        run(ctx)

        assert ctx.files_read == 0

    def test_multiple_files_counted(self) -> None:
        """Multiple file operations accumulate counters."""
        read_tool = MockTool(name="file_read", result="contents")
        write_tool = MockTool(name="file_write", result="File written ok")
        responses = [
            MockResponse(
                tool_calls=[
                    _make_tool_call("file_read", call_id="c1"),
                    _make_tool_call("file_write", call_id="c2"),
                    _make_tool_call("file_read", call_id="c3"),
                ],
            ),
            MockResponse(content="Done"),
        ]
        ctx = _make_context(
            responses,
            tools={"file_read": read_tool, "file_write": write_tool},
        )

        run(ctx)

        assert ctx.files_read == 2
        assert ctx.files_written == 1


class TestAgentStreaming:
    """Test streaming turn behavior."""

    def test_can_stream_false_by_default_mock(self) -> None:
        """_can_stream returns False when streaming=False."""
        ctx = _make_context([MockResponse(content="Hi")])
        assert not _can_stream(ctx)

    def test_can_stream_true_when_enabled(self) -> None:
        """_can_stream returns True when streaming=True and client has chat_stream."""
        ctx = _make_context([MockResponse(content="Hi")], streaming=True)
        assert _can_stream(ctx)

    def test_streaming_fallback_to_buffered(self) -> None:
        """When streaming=False, agent uses buffered chat()."""
        responses = [MockResponse(content="Hello!")]
        ctx = _make_context(responses, streaming=False)

        result = run(ctx)

        assert result == "Hello!"
        ctx.client.chat.assert_called_once()

    def test_streaming_content_chunks(self) -> None:
        """Streaming turn accumulates content from delta chunks."""

        @dataclass
        class MockChunk:
            delta_content: str = ""
            delta_thinking: str = ""
            tool_calls: list[dict[str, Any]] = field(default_factory=list)
            finish_reason: str | None = None
            usage: dict[str, int] | None = None

        chunks = [
            MockChunk(delta_content="Hel"),
            MockChunk(delta_content="lo!"),
            MockChunk(finish_reason="stop", usage={"total_tokens": 42}),
        ]

        client = MagicMock()
        client.chat_stream.return_value = iter(chunks)

        ctx = Context(
            config=ZhiConfig(),
            client=client,
            model="glm-5",
            tools={},
            tool_schemas=[],
            permission_mode=PermissionMode.APPROVE,
            streaming=True,
            conversation=[{"role": "user", "content": "hi"}],
        )

        result = _do_turn_streaming(ctx)

        assert result.content == "Hello!"
        assert result.total_tokens == 42
        assert result.tool_calls == []

    def test_streaming_tool_call_accumulation(self) -> None:
        """Streaming turn accumulates tool call deltas."""

        @dataclass
        class MockChunk:
            delta_content: str = ""
            delta_thinking: str = ""
            tool_calls: list[dict[str, Any]] = field(default_factory=list)
            finish_reason: str | None = None
            usage: dict[str, int] | None = None

        chunks = [
            MockChunk(
                tool_calls=[
                    {
                        "index": 0,
                        "id": "call_1",
                        "function": {"name": "file_", "arguments": '{"pa'},
                    }
                ]
            ),
            MockChunk(
                tool_calls=[
                    {
                        "index": 0,
                        "id": None,
                        "function": {"name": "read", "arguments": 'th":"a.txt"}'},
                    }
                ]
            ),
            MockChunk(finish_reason="tool_calls"),
        ]

        client = MagicMock()
        client.chat_stream.return_value = iter(chunks)

        ctx = Context(
            config=ZhiConfig(),
            client=client,
            model="glm-5",
            tools={},
            tool_schemas=[],
            permission_mode=PermissionMode.APPROVE,
            streaming=True,
            conversation=[{"role": "user", "content": "read a.txt"}],
        )

        result = _do_turn_streaming(ctx)

        assert len(result.tool_calls) == 1
        tc = result.tool_calls[0]
        assert tc["id"] == "call_1"
        assert tc["function"]["name"] == "file_read"
        assert tc["function"]["arguments"] == '{"path":"a.txt"}'

    def test_streaming_on_stream_called_per_chunk(self) -> None:
        """on_stream is called for each content delta."""

        @dataclass
        class MockChunk:
            delta_content: str = ""
            delta_thinking: str = ""
            tool_calls: list[dict[str, Any]] = field(default_factory=list)
            finish_reason: str | None = None
            usage: dict[str, int] | None = None

        chunks = [
            MockChunk(delta_content="a"),
            MockChunk(delta_content="b"),
            MockChunk(delta_content="c"),
            MockChunk(finish_reason="stop"),
        ]

        on_stream = MagicMock()
        client = MagicMock()
        client.chat_stream.return_value = iter(chunks)

        ctx = Context(
            config=ZhiConfig(),
            client=client,
            model="glm-5",
            tools={},
            tool_schemas=[],
            permission_mode=PermissionMode.APPROVE,
            streaming=True,
            on_stream=on_stream,
            conversation=[{"role": "user", "content": "hi"}],
        )

        _do_turn_streaming(ctx)

        assert on_stream.call_count == 3
        on_stream.assert_any_call("a")
        on_stream.assert_any_call("b")
        on_stream.assert_any_call("c")

    def test_full_streaming_run_with_tools(self) -> None:
        """Full agent run using streaming with tool calls and final response."""

        @dataclass
        class MockChunk:
            delta_content: str = ""
            delta_thinking: str = ""
            tool_calls: list[dict[str, Any]] = field(default_factory=list)
            finish_reason: str | None = None
            usage: dict[str, int] | None = None

        # First turn: tool call via streaming
        tool_chunks = [
            MockChunk(
                tool_calls=[
                    {
                        "index": 0,
                        "id": "call_1",
                        "function": {"name": "file_read", "arguments": "{}"},
                    }
                ]
            ),
            MockChunk(finish_reason="tool_calls", usage={"total_tokens": 20}),
        ]

        # Second turn: final text via streaming
        text_chunks = [
            MockChunk(delta_content="Done!"),
            MockChunk(finish_reason="stop", usage={"total_tokens": 10}),
        ]

        call_count = {"n": 0}
        chunk_lists = [tool_chunks, text_chunks]

        def mock_chat_stream(**kwargs: Any) -> Any:
            idx = call_count["n"]
            call_count["n"] += 1
            return iter(chunk_lists[idx])

        tool = MockTool(name="file_read", result="file data")

        client = MagicMock(spec=[])  # Empty spec so hasattr works correctly
        client.chat_stream = mock_chat_stream

        ctx = Context(
            config=ZhiConfig(),
            client=client,
            model="glm-5",
            tools={"file_read": tool},
            tool_schemas=[
                {
                    "type": "function",
                    "function": {
                        "name": "file_read",
                        "description": "Read a file",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            permission_mode=PermissionMode.APPROVE,
            streaming=True,
            conversation=[{"role": "user", "content": "read file"}],
        )

        result = run(ctx)

        assert result == "Done!"
        assert tool.call_count == 1
        assert ctx.session_tokens == 30


class TestAgentInterruptRollback:
    """Test conversation rollback on interrupt during tool execution (Bug 18)."""

    def test_conversation_rollback_on_interrupt(self) -> None:
        """When ESC interrupts mid-tool-execution, conversation rolls back.

        The assistant message (with tool_calls) and any partial tool results
        are removed, leaving the conversation in a valid state.
        """
        tool = MockTool(name="slow_tool", result="ok")

        # First turn: model wants to call a tool
        responses = [
            MockResponse(
                content=None,
                tool_calls=[
                    _make_tool_call("slow_tool", call_id="c1"),
                    _make_tool_call("slow_tool", call_id="c2"),
                ],
            ),
        ]
        ctx = _make_context(responses, tools={"slow_tool": tool})
        ctx.conversation = [{"role": "user", "content": "do work"}]

        # Set cancel_event after the first tool call completes
        original_execute = tool.execute

        def execute_with_cancel(**kwargs: Any) -> str:
            result = original_execute(**kwargs)
            # After first tool call, set cancel to interrupt second
            ctx.cancel_event.set()
            return result

        tool.execute = execute_with_cancel  # type: ignore[assignment]

        with pytest.raises(AgentInterruptedError):
            run(ctx)

        # Conversation should be rolled back to just the user message
        assert len(ctx.conversation) == 1
        assert ctx.conversation[0]["role"] == "user"
        assert ctx.conversation[0]["content"] == "do work"


class TestPruneForApi:
    """Test conversation sliding window pruning."""

    def _sys(self, content: str = "You are a bot") -> dict[str, Any]:
        return {"role": "system", "content": content}

    def _user(self, content: str = "Hello") -> dict[str, Any]:
        return {"role": "user", "content": content}

    def _asst(self, content: str = "", tool_calls: bool = False) -> dict[str, Any]:
        msg: dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = [{"id": "c1", "function": {"name": "t"}}]
        return msg

    def _tool(self, content: str = "ok") -> dict[str, Any]:
        return {"role": "tool", "tool_call_id": "c1", "content": content}

    def test_unlimited_returns_full_conversation(self) -> None:
        """max_context_messages=0 returns the full conversation."""
        conv = [self._sys(), self._user(), self._asst("hi")]
        ctx = _make_context([])
        ctx.conversation = conv
        ctx.max_context_messages = 0

        assert _prune_for_api(ctx) is conv

    def test_under_limit_returns_full_conversation(self) -> None:
        """Conversation under the limit is returned unchanged."""
        conv = [self._sys(), self._user(), self._asst("hi")]
        ctx = _make_context([])
        ctx.conversation = conv
        ctx.max_context_messages = 10

        assert _prune_for_api(ctx) is conv

    def test_prunes_old_turns(self) -> None:
        """Conversation exceeding limit drops old turn pairs."""
        conv = [
            self._sys(),  # 0 - keep
            self._user(),  # 1 - keep
            self._asst(tool_calls=True),  # 2 - old, drop
            self._tool("result1"),  # 3 - old, drop
            self._asst(tool_calls=True),  # 4 - keep (recent)
            self._tool("result2"),  # 5 - keep
            self._asst("final"),  # 6 - keep
        ]
        ctx = _make_context([])
        ctx.conversation = conv
        # limit=5: system + user + 3 recent = 5
        ctx.max_context_messages = 5

        result = _prune_for_api(ctx)

        assert len(result) == 5
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"
        assert result[2].get("tool_calls")  # the second assistant msg
        assert result[3]["content"] == "result2"
        assert result[4]["content"] == "final"

    def test_cut_snaps_to_assistant_boundary(self) -> None:
        """Cut point advances past orphaned tool results."""
        conv = [
            self._sys(),  # 0
            self._user(),  # 1
            self._asst(tool_calls=True),  # 2
            self._tool("r1"),  # 3 - would be cut here naively
            self._tool("r2"),  # 4 - but tool, so snap forward
            self._asst(tool_calls=True),  # 5 - actual cut point
            self._tool("r3"),  # 6
            self._asst("done"),  # 7
        ]
        ctx = _make_context([])
        ctx.conversation = conv
        # limit=5: prefix=2, want last 3 from rest, but rest[3]=tool so snap
        ctx.max_context_messages = 5

        result = _prune_for_api(ctx)

        # Should keep: sys, user, asst(tc), tool(r3), asst(done)
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"
        assert result[2].get("tool_calls")
        assert result[3]["content"] == "r3"
        assert result[4]["content"] == "done"

    def test_preserves_original_conversation(self) -> None:
        """Pruning does not mutate the original conversation list."""
        conv = [
            self._sys(),
            self._user(),
            self._asst(tool_calls=True),
            self._tool("r1"),
            self._asst(tool_calls=True),
            self._tool("r2"),
            self._asst("end"),
        ]
        original_len = len(conv)
        ctx = _make_context([])
        ctx.conversation = conv
        ctx.max_context_messages = 4

        _prune_for_api(ctx)

        assert len(conv) == original_len

    def test_no_system_prompt(self) -> None:
        """Works when conversation has no system prompt."""
        conv = [
            self._user("go"),
            self._asst(tool_calls=True),
            self._tool("r1"),
            self._asst(tool_calls=True),
            self._tool("r2"),
            self._asst("end"),
        ]
        ctx = _make_context([])
        ctx.conversation = conv
        ctx.max_context_messages = 4

        result = _prune_for_api(ctx)

        assert result[0]["role"] == "user"
        assert result[-1]["content"] == "end"
        assert len(result) <= 4
