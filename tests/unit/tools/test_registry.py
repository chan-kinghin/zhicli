"""Tests for ToolRegistry."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from zhi.tools import ToolRegistry, create_default_registry
from zhi.tools.base import BaseTool


class FakeTool(BaseTool):
    name: ClassVar[str] = "fake"
    description: ClassVar[str] = "Fake tool."
    parameters: ClassVar[dict[str, Any]] = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> str:
        return "fake"


class AnotherFakeTool(BaseTool):
    name: ClassVar[str] = "another"
    description: ClassVar[str] = "Another fake."
    parameters: ClassVar[dict[str, Any]] = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> str:
        return "another"


class DuplicateFakeTool(BaseTool):
    name: ClassVar[str] = "fake"
    description: ClassVar[str] = "Duplicate."
    parameters: ClassVar[dict[str, Any]] = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> str:
        return "dup"


class TestToolRegistryRegister:
    def test_register_and_get(self) -> None:
        reg = ToolRegistry()
        tool = FakeTool()
        reg.register(tool)
        assert reg.get("fake") is tool

    def test_get_unknown_returns_none(self) -> None:
        reg = ToolRegistry()
        assert reg.get("nonexistent") is None


class TestToolRegistryDuplicate:
    def test_duplicate_raises(self) -> None:
        reg = ToolRegistry()
        reg.register(FakeTool())
        with pytest.raises(ValueError, match="already registered"):
            reg.register(DuplicateFakeTool())


class TestToolRegistryList:
    def test_list_tools_empty(self) -> None:
        reg = ToolRegistry()
        assert reg.list_tools() == []

    def test_list_tools_returns_all(self) -> None:
        reg = ToolRegistry()
        reg.register(FakeTool())
        reg.register(AnotherFakeTool())
        names = [t.name for t in reg.list_tools()]
        assert "fake" in names
        assert "another" in names

    def test_list_names(self) -> None:
        reg = ToolRegistry()
        reg.register(FakeTool())
        reg.register(AnotherFakeTool())
        assert set(reg.list_names()) == {"fake", "another"}


class TestToolRegistryFilter:
    def test_filter_by_names(self) -> None:
        reg = ToolRegistry()
        reg.register(FakeTool())
        reg.register(AnotherFakeTool())
        filtered = reg.filter_by_names(["fake"])
        assert "fake" in filtered
        assert "another" not in filtered

    def test_filter_missing_name_ignored(self) -> None:
        reg = ToolRegistry()
        reg.register(FakeTool())
        filtered = reg.filter_by_names(["fake", "nonexistent"])
        assert len(filtered) == 1
        assert "fake" in filtered


class TestToolRegistrySchemas:
    def test_to_schemas(self) -> None:
        reg = ToolRegistry()
        reg.register(FakeTool())
        schemas = reg.to_schemas()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "fake"

    def test_to_schemas_filtered(self) -> None:
        reg = ToolRegistry()
        reg.register(FakeTool())
        reg.register(AnotherFakeTool())
        schemas = reg.to_schemas_filtered(["fake"])
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "fake"

    def test_to_schemas_filtered_unknown_ignored(self) -> None:
        reg = ToolRegistry()
        reg.register(FakeTool())
        schemas = reg.to_schemas_filtered(["fake", "nonexistent"])
        assert len(schemas) == 1


class TestCreateDefaultRegistry:
    def test_creates_registry_with_tools(self) -> None:
        reg = create_default_registry()
        names = reg.list_names()
        assert "file_read" in names
        assert "file_write" in names
        assert "file_list" in names
        assert "web_fetch" in names

    def test_default_registry_schemas(self) -> None:
        reg = create_default_registry()
        schemas = reg.to_schemas()
        assert len(schemas) >= 4
        for schema in schemas:
            assert schema["type"] == "function"
