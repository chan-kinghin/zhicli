"""Tests for BaseTool ABC."""

from __future__ import annotations

from typing import Any, ClassVar

from zhi.tools.base import BaseTool


class DummyTool(BaseTool):
    """Concrete tool for testing."""

    name: ClassVar[str] = "dummy"
    description: ClassVar[str] = "A dummy tool for testing."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Input text.",
            },
        },
        "required": ["text"],
    }
    risky: ClassVar[bool] = False

    def execute(self, **kwargs: Any) -> str:
        return f"echo: {kwargs.get('text', '')}"


class RiskyDummyTool(BaseTool):
    """Risky tool for testing."""

    name: ClassVar[str] = "risky_dummy"
    description: ClassVar[str] = "A risky dummy tool."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {},
    }
    risky: ClassVar[bool] = True

    def execute(self, **kwargs: Any) -> str:
        return "done"


class TestBaseToolSchemaGeneration:
    def test_to_function_schema_structure(self) -> None:
        tool = DummyTool()
        schema = tool.to_function_schema()

        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "dummy"
        assert schema["function"]["description"] == "A dummy tool for testing."
        assert schema["function"]["parameters"]["type"] == "object"
        assert "text" in schema["function"]["parameters"]["properties"]

    def test_schema_has_required_fields(self) -> None:
        tool = DummyTool()
        schema = tool.to_function_schema()
        assert schema["function"]["parameters"]["required"] == ["text"]

    def test_schema_with_empty_parameters(self) -> None:
        tool = RiskyDummyTool()
        schema = tool.to_function_schema()
        assert schema["function"]["name"] == "risky_dummy"
        assert schema["function"]["parameters"]["type"] == "object"


class TestBaseToolRiskyFlag:
    def test_default_risky_is_false(self) -> None:
        tool = DummyTool()
        assert tool.risky is False

    def test_risky_true(self) -> None:
        tool = RiskyDummyTool()
        assert tool.risky is True


class TestBaseToolExecute:
    def test_execute_returns_string(self) -> None:
        tool = DummyTool()
        result = tool.execute(text="hello")
        assert result == "echo: hello"

    def test_execute_with_empty_kwargs(self) -> None:
        tool = DummyTool()
        result = tool.execute()
        assert result == "echo: "
