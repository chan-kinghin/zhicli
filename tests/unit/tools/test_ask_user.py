"""Tests for AskUserTool — interactive user questioning."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from zhi.tools.ask_user import AskUserTool
from zhi.tools.base import Registrable

# -- Construction & metadata ---------------------------------------------------


class TestAskUserToolMetadata:
    def test_name(self) -> None:
        tool = AskUserTool()
        assert tool.name == "ask_user"

    def test_description_is_nonempty(self) -> None:
        tool = AskUserTool()
        assert len(tool.description) > 10

    def test_risky_is_false(self) -> None:
        tool = AskUserTool()
        assert tool.risky is False

    def test_satisfies_registrable_protocol(self) -> None:
        tool = AskUserTool()
        assert isinstance(tool, Registrable)

    def test_schema_structure(self) -> None:
        tool = AskUserTool()
        schema = tool.to_function_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "ask_user"
        props = schema["function"]["parameters"]["properties"]
        assert "question" in props
        assert "options" in props
        assert "question" in schema["function"]["parameters"]["required"]

    def test_schema_options_not_required(self) -> None:
        tool = AskUserTool()
        schema = tool.to_function_schema()
        assert "options" not in schema["function"]["parameters"]["required"]


# -- Execution with callback ---------------------------------------------------


class TestAskUserToolExecution:
    def test_returns_user_answer(self) -> None:
        cb = MagicMock(return_value="yes")
        tool = AskUserTool(callback=cb)
        result = tool.execute(question="Continue?")
        assert result == "yes"
        cb.assert_called_once_with("Continue?", None)

    def test_passes_options_to_callback(self) -> None:
        cb = MagicMock(return_value="option B")
        tool = AskUserTool(callback=cb)
        result = tool.execute(question="Pick one", options=["A", "B", "C"])
        assert result == "option B"
        cb.assert_called_once_with("Pick one", ["A", "B", "C"])

    def test_empty_answer_returns_no_response(self) -> None:
        cb = MagicMock(return_value="")
        tool = AskUserTool(callback=cb)
        result = tool.execute(question="Anything?")
        assert result == "(no response)"

    def test_none_answer_returns_no_response(self) -> None:
        cb = MagicMock(return_value=None)
        tool = AskUserTool(callback=cb)
        result = tool.execute(question="Anything?")
        assert result == "(no response)"

    def test_no_options_passes_none(self) -> None:
        cb = MagicMock(return_value="answer")
        tool = AskUserTool(callback=cb)
        tool.execute(question="What?")
        cb.assert_called_once_with("What?", None)


# -- Error cases ---------------------------------------------------------------


class TestAskUserToolErrors:
    def test_no_callback_returns_error(self) -> None:
        tool = AskUserTool(callback=None)
        result = tool.execute(question="Hello?")
        assert "Error" in result
        assert "not available" in result

    def test_empty_question_returns_error(self) -> None:
        cb = MagicMock(return_value="answer")
        tool = AskUserTool(callback=cb)
        result = tool.execute(question="")
        assert "Error" in result
        assert "No question" in result
        cb.assert_not_called()

    def test_missing_question_returns_error(self) -> None:
        cb = MagicMock(return_value="answer")
        tool = AskUserTool(callback=cb)
        result = tool.execute()
        assert "Error" in result
        assert "No question" in result
        cb.assert_not_called()

    def test_callback_exception_returns_error(self) -> None:
        cb = MagicMock(side_effect=RuntimeError("input broken"))
        tool = AskUserTool(callback=cb)
        result = tool.execute(question="Crash?")
        assert "Error getting user input" in result
        assert "input broken" in result


# -- Registry integration -----------------------------------------------------


class TestAskUserToolRegistry:
    def test_registered_in_default_registry(self) -> None:
        from zhi.tools import create_default_registry

        registry = create_default_registry()
        tool = registry.get("ask_user")
        assert tool is not None
        assert tool.name == "ask_user"

    def test_registered_with_callback(self) -> None:
        from zhi.tools import create_default_registry

        cb = MagicMock(return_value="hi")
        registry = create_default_registry(ask_user_callback=cb)
        tool = registry.get("ask_user")
        assert tool is not None
        result = tool.execute(question="test")
        assert result == "hi"

    def test_registered_without_callback(self) -> None:
        from zhi.tools import create_default_registry

        registry = create_default_registry()
        tool = registry.get("ask_user")
        assert tool is not None
        result = tool.execute(question="test")
        assert "not available" in result


# -- SkillTool propagation ----------------------------------------------------


class TestAskUserToolInSkillTool:
    def test_on_ask_user_propagated_to_nested_context(self) -> None:
        """on_ask_user callback reaches nested Context when SkillTool runs."""
        from dataclasses import dataclass, field

        from zhi.skills.loader import SkillConfig
        from zhi.tools import ToolRegistry
        from zhi.tools.skill_tool import SkillTool

        @dataclass
        class FakeResponse:
            content: str = "done"
            tool_calls: list[Any] = field(default_factory=list)
            thinking: str | None = None
            total_tokens: int = 10

        client = MagicMock()
        client.chat.return_value = FakeResponse()

        cb = MagicMock(return_value="user answer")
        skill = SkillConfig(
            name="interviewer",
            description="Ask questions",
            system_prompt="You ask questions.",
            tools=["ask_user"],
            model="glm-4-flash",
            max_turns=3,
            input_args=[],
        )
        registry = ToolRegistry()
        tool = SkillTool(
            skill=skill,
            client=client,
            registry=registry,
            on_ask_user=cb,
        )

        with patch("zhi.tools.skill_tool.agent_run", return_value="ok") as mock_run:
            tool.execute(input="interview me")

        ctx_arg = mock_run.call_args.args[0]
        assert ctx_arg.on_ask_user is cb
        # ask_user tool should be in inner_tools
        assert "ask_user" in ctx_arg.tools
        assert ctx_arg.tools["ask_user"]._callback is cb

    def test_on_ask_user_propagated_to_child_skill(self) -> None:
        """on_ask_user propagates through nested SkillTool re-wrapping."""
        from dataclasses import dataclass, field

        from zhi.skills.loader import SkillConfig
        from zhi.tools import ToolRegistry
        from zhi.tools.skill_tool import SkillTool

        @dataclass
        class FakeResponse:
            content: str = "done"
            tool_calls: list[Any] = field(default_factory=list)
            thinking: str | None = None
            total_tokens: int = 10

        client = MagicMock()
        client.chat.return_value = FakeResponse()

        cb = MagicMock(return_value="answer")

        # Parent skill calls child skill
        child_skill = SkillConfig(
            name="child",
            description="Child skill",
            system_prompt="You are child.",
            tools=[],
            model="glm-4-flash",
            max_turns=3,
            input_args=[],
        )
        parent_skill = SkillConfig(
            name="parent",
            description="Parent skill",
            system_prompt="You are parent.",
            tools=["child"],
            model="glm-4-flash",
            max_turns=3,
            input_args=[],
        )

        registry = ToolRegistry()
        child_tool = SkillTool(
            skill=child_skill,
            client=client,
            registry=registry,
            on_ask_user=cb,
        )
        registry.register(child_tool)

        parent_tool = SkillTool(
            skill=parent_skill,
            client=client,
            registry=registry,
            on_ask_user=cb,
        )

        with patch("zhi.tools.skill_tool.agent_run", return_value="ok") as mock_run:
            parent_tool.execute(input="test")

        ctx_arg = mock_run.call_args.args[0]
        # The re-wrapped child should have on_ask_user
        child_in_ctx = ctx_arg.tools.get("skill_child")
        assert child_in_ctx is not None
        assert child_in_ctx._on_ask_user is cb

    def test_register_skill_tools_passes_on_ask_user(self) -> None:
        """register_skill_tools forwards on_ask_user to SkillTool."""
        from zhi.skills.loader import SkillConfig
        from zhi.tools import ToolRegistry, register_skill_tools
        from zhi.tools.skill_tool import SkillTool

        registry = ToolRegistry()
        cb = MagicMock(return_value="answer")
        skill = SkillConfig(
            name="demo",
            description="Demo",
            system_prompt="Demo",
            tools=[],
            model="glm-4-flash",
            max_turns=3,
            input_args=[],
        )
        register_skill_tools(registry, {"demo": skill}, MagicMock(), on_ask_user=cb)
        tool = registry.get("skill_demo")
        assert isinstance(tool, SkillTool)
        assert tool._on_ask_user is cb
