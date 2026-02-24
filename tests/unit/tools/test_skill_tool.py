"""Tests for SkillTool — skill-as-tool composition."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import MagicMock, patch

import pytest

from zhi.skills.loader import SkillConfig
from zhi.tools import ToolRegistry, register_skill_tools
from zhi.tools.base import BaseTool, Registrable
from zhi.tools.skill_tool import _MAX_DEPTH, SkillTool


def _make_skill(
    name: str = "summarize",
    description: str = "Summarize text",
    tools: list[str] | None = None,
    model: str = "glm-4-flash",
    max_turns: int = 5,
    input_args: list[dict[str, Any]] | None = None,
) -> SkillConfig:
    return SkillConfig(
        name=name,
        description=description,
        system_prompt="You are a summarizer.",
        tools=tools or ["file_read"],
        model=model,
        max_turns=max_turns,
        input_args=input_args or [],
    )


def _make_client() -> MagicMock:
    """Create a mock client whose chat() returns a text-only response."""
    client = MagicMock()

    @dataclass
    class FakeResponse:
        content: str = "Mock result"
        tool_calls: list[Any] = field(default_factory=list)
        thinking: str | None = None
        total_tokens: int = 10

    client.chat.return_value = FakeResponse()
    return client


def _make_registry_with_fake() -> ToolRegistry:
    """Registry containing a simple FakeTool for testing."""

    class FakeTool(BaseTool):
        name: ClassVar[str] = "file_read"
        description: ClassVar[str] = "Read a file."
        parameters: ClassVar[dict[str, Any]] = {
            "type": "object",
            "properties": {},
        }

        def execute(self, **kwargs: Any) -> str:
            return "file contents"

    reg = ToolRegistry()
    reg.register(FakeTool())
    return reg


# ── Construction ─────────────────────────────────────────────────────


class TestSkillToolConstruction:
    def test_name_has_prefix(self) -> None:
        skill = _make_skill(name="summarize")
        tool = SkillTool(skill=skill, client=_make_client(), registry=ToolRegistry())
        assert tool.name == "skill_summarize"

    def test_risky_is_false(self) -> None:
        tool = SkillTool(
            skill=_make_skill(), client=_make_client(), registry=ToolRegistry()
        )
        assert tool.risky is False

    def test_description_from_skill(self) -> None:
        tool = SkillTool(
            skill=_make_skill(description="Custom desc"),
            client=_make_client(),
            registry=ToolRegistry(),
        )
        assert tool.description == "Custom desc"

    def test_satisfies_registrable_protocol(self) -> None:
        tool = SkillTool(
            skill=_make_skill(), client=_make_client(), registry=ToolRegistry()
        )
        assert isinstance(tool, Registrable)


# ── Schema ───────────────────────────────────────────────────────────


class TestSkillToolSchema:
    def test_schema_structure(self) -> None:
        tool = SkillTool(
            skill=_make_skill(), client=_make_client(), registry=ToolRegistry()
        )
        schema = tool.to_function_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "skill_summarize"
        assert "input" in schema["function"]["parameters"]["properties"]
        assert "input" in schema["function"]["parameters"]["required"]

    def test_schema_includes_input_args(self) -> None:
        skill = _make_skill(
            input_args=[
                {
                    "name": "language",
                    "type": "string",
                    "description": "Target language",
                    "required": True,
                },
                {
                    "name": "verbose",
                    "type": "boolean",
                    "description": "Verbose output",
                },
            ]
        )
        tool = SkillTool(skill=skill, client=_make_client(), registry=ToolRegistry())
        schema = tool.to_function_schema()
        props = schema["function"]["parameters"]["properties"]
        assert "language" in props
        assert "verbose" in props
        assert props["language"]["type"] == "string"
        assert "language" in schema["function"]["parameters"]["required"]
        # verbose is not required
        assert "verbose" not in schema["function"]["parameters"]["required"]

    def test_schema_skips_nameless_args(self) -> None:
        skill = _make_skill(input_args=[{"description": "no name field"}])
        tool = SkillTool(skill=skill, client=_make_client(), registry=ToolRegistry())
        schema = tool.to_function_schema()
        # Only 'input' should be in properties
        assert list(schema["function"]["parameters"]["properties"].keys()) == ["input"]


# ── Execution ────────────────────────────────────────────────────────


class TestSkillToolExecution:
    def test_runs_nested_agent_loop(self) -> None:
        client = _make_client()
        registry = _make_registry_with_fake()
        tool = SkillTool(skill=_make_skill(), client=client, registry=registry)

        result = tool.execute(input="Summarize this")
        assert result == "Mock result"
        client.chat.assert_called_once()

    def test_uses_skill_model(self) -> None:
        client = _make_client()
        registry = _make_registry_with_fake()
        skill = _make_skill(model="glm-4-flash")
        tool = SkillTool(skill=skill, client=client, registry=registry)

        tool.execute(input="test")
        call_kwargs = client.chat.call_args
        assert call_kwargs.kwargs["model"] == "glm-4-flash"

    def test_returns_error_on_exception(self) -> None:
        client = _make_client()
        client.chat.side_effect = RuntimeError("API down")
        registry = _make_registry_with_fake()
        tool = SkillTool(skill=_make_skill(), client=client, registry=registry)

        result = tool.execute(input="test")
        assert "Error running skill" in result

    def test_returns_message_on_max_turns(self) -> None:
        """When agent.run returns None (max turns), SkillTool reports it."""
        client = _make_client()
        registry = _make_registry_with_fake()
        tool = SkillTool(skill=_make_skill(), client=client, registry=registry)

        with patch("zhi.tools.skill_tool.agent_run", return_value=None):
            result = tool.execute(input="test")
        assert "max turns" in result.lower()

    def test_extra_args_appended_to_input(self) -> None:
        client = _make_client()
        registry = _make_registry_with_fake()
        tool = SkillTool(skill=_make_skill(), client=client, registry=registry)

        tool.execute(input="Summarize", language="en")
        call_args = client.chat.call_args
        messages = call_args.kwargs["messages"]
        user_msg = next(m for m in messages if m["role"] == "user")
        assert "language" in user_msg["content"]

    def test_file_arg_content_injected(self, tmp_path: MagicMock) -> None:
        """File-type args get their content read and injected into the user message."""
        import tempfile

        with tempfile.NamedTemporaryFile(
            suffix=".txt", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write("Hello from file")
            fpath = f.name

        try:
            client = _make_client()
            registry = _make_registry_with_fake()
            skill = _make_skill(
                input_args=[
                    {"name": "file", "type": "file", "required": True},
                ]
            )
            tool = SkillTool(skill=skill, client=client, registry=registry)

            tool.execute(input="Analyze this", file=fpath)
            call_args = client.chat.call_args
            messages = call_args.kwargs["messages"]
            user_msg = next(m for m in messages if m["role"] == "user")
            assert "Hello from file" in user_msg["content"]
            assert "--- File (file):" in user_msg["content"]
        finally:
            import os

            os.unlink(fpath)

    def test_empty_file_arg_not_injected(self) -> None:
        """Empty file-type args are skipped — no 'Additional arguments: {file: }'."""
        client = _make_client()
        registry = _make_registry_with_fake()
        skill = _make_skill(
            input_args=[
                {"name": "file", "type": "file", "required": True},
            ]
        )
        tool = SkillTool(skill=skill, client=client, registry=registry)

        tool.execute(input="Analyze this", file="")
        call_args = client.chat.call_args
        messages = call_args.kwargs["messages"]
        user_msg = next(m for m in messages if m["role"] == "user")
        # Should NOT contain empty file args as noise
        assert "Additional arguments" not in user_msg["content"]
        assert "'file': ''" not in user_msg["content"]

    def test_read_file_oserror_returns_attachment_with_error(self) -> None:
        """Bug 15: OSError on path resolution returns FileAttachment with error."""
        client = _make_client()
        registry = _make_registry_with_fake()
        skill = _make_skill(
            input_args=[
                {"name": "file", "type": "file", "required": True},
            ]
        )
        tool = SkillTool(skill=skill, client=client, registry=registry)

        # Patch Path.resolve to raise OSError for our test path
        orig_resolve = Path.resolve

        def patched_resolve(self_path: Path, *a: Any, **kw: Any) -> Path:
            if "network_mount" in str(self_path):
                raise OSError("Network timeout")
            return orig_resolve(self_path, *a, **kw)

        with patch.object(Path, "resolve", patched_resolve):
            att = tool._read_file("/network_mount/data.xlsx")

        assert att.error is not None
        assert "Invalid path" in att.error


# ── Recursion Prevention ─────────────────────────────────────────────


class TestSkillToolRecursion:
    def test_direct_cycle_blocked(self) -> None:
        """A skill calling itself is blocked."""
        skill = _make_skill(name="self_ref", tools=["skill_self_ref"])
        registry = ToolRegistry()
        client = _make_client()

        tool = SkillTool(
            skill=skill,
            client=client,
            registry=registry,
            call_stack=frozenset({"self_ref"}),
        )
        result = tool.execute(input="test")
        assert "Recursion blocked" in result

    def test_indirect_cycle_blocked(self) -> None:
        """A→B→A cycle is blocked."""
        skill_b = _make_skill(name="B", tools=["skill_A"])
        registry = ToolRegistry()
        client = _make_client()

        # B is called while A is already in the stack
        tool = SkillTool(
            skill=skill_b,
            client=client,
            registry=registry,
            call_stack=frozenset({"A", "B"}),
        )
        result = tool.execute(input="test")
        assert "Recursion blocked" in result

    def test_depth_limit_enforced(self) -> None:
        """Nesting beyond _MAX_DEPTH is blocked."""
        skill = _make_skill(name="deep")
        registry = ToolRegistry()
        client = _make_client()

        tool = SkillTool(
            skill=skill,
            client=client,
            registry=registry,
            depth=_MAX_DEPTH,
        )
        result = tool.execute(input="test")
        assert "max depth" in result.lower()

    def test_permission_mode_getter_used_in_execute(self) -> None:
        """Bug 3: SkillTool reads live permission mode via getter."""
        from zhi.agent import PermissionMode

        client = _make_client()
        registry = _make_registry_with_fake()
        getter = MagicMock(return_value=PermissionMode.AUTO)
        tool = SkillTool(
            skill=_make_skill(),
            client=client,
            registry=registry,
            permission_mode_getter=getter,
        )
        assert tool._get_permission_mode() == PermissionMode.AUTO
        getter.assert_called_once()

    def test_on_permission_propagated_to_context(self) -> None:
        """Bug 1: on_permission callback reaches nested Context."""
        client = _make_client()
        registry = _make_registry_with_fake()
        cb = MagicMock(return_value=True)
        tool = SkillTool(
            skill=_make_skill(),
            client=client,
            registry=registry,
            on_permission=cb,
        )

        with patch("zhi.tools.skill_tool.agent_run", return_value="ok") as mock_run:
            tool.execute(input="test")

        # Check that the Context passed to agent_run has on_permission set
        ctx_arg = mock_run.call_args.args[0]
        assert ctx_arg.on_permission is cb

    def test_depth_within_limit_allowed(self) -> None:
        """Nesting at depth < _MAX_DEPTH proceeds normally."""
        client = _make_client()
        registry = _make_registry_with_fake()
        skill = _make_skill(name="nested")
        tool = SkillTool(
            skill=skill,
            client=client,
            registry=registry,
            depth=_MAX_DEPTH - 1,
        )
        result = tool.execute(input="test")
        assert result == "Mock result"


# ── Registry Integration ─────────────────────────────────────────────


class TestRegisterSkillTools:
    def test_registers_skill_tools(self) -> None:
        registry = _make_registry_with_fake()
        skills = {"summarize": _make_skill(name="summarize")}
        client = _make_client()

        register_skill_tools(registry, skills, client)
        assert registry.get("skill_summarize") is not None

    def test_no_name_collision_with_base_tools(self) -> None:
        registry = _make_registry_with_fake()
        skills = {"summarize": _make_skill(name="summarize")}
        client = _make_client()

        register_skill_tools(registry, skills, client)
        # Both file_read and skill_summarize coexist
        assert registry.get("file_read") is not None
        assert registry.get("skill_summarize") is not None

    def test_filter_by_names_finds_skill_tools(self) -> None:
        registry = _make_registry_with_fake()
        skills = {"summarize": _make_skill(name="summarize")}
        client = _make_client()

        register_skill_tools(registry, skills, client)
        filtered = registry.filter_by_names(["skill_summarize"])
        assert "skill_summarize" in filtered

    def test_schema_export_includes_skill_tools(self) -> None:
        registry = _make_registry_with_fake()
        skills = {"summarize": _make_skill(name="summarize")}
        client = _make_client()

        register_skill_tools(registry, skills, client)
        schemas = registry.to_schemas()
        names = [s["function"]["name"] for s in schemas]
        assert "skill_summarize" in names

    def test_passes_permission_callback(self) -> None:
        """Bug 1: register_skill_tools forwards on_permission."""
        registry = _make_registry_with_fake()
        skills = {"summarize": _make_skill(name="summarize")}
        client = _make_client()

        cb = MagicMock(return_value=True)
        register_skill_tools(registry, skills, client, on_permission=cb)

        tool = registry.get("skill_summarize")
        assert isinstance(tool, SkillTool)
        assert tool._on_permission is cb

    def test_passes_permission_mode_getter(self) -> None:
        """Bug 3: register_skill_tools forwards permission_mode_getter."""
        registry = _make_registry_with_fake()
        skills = {"summarize": _make_skill(name="summarize")}
        client = _make_client()

        getter = MagicMock(return_value=MagicMock())
        register_skill_tools(registry, skills, client, permission_mode_getter=getter)

        tool = registry.get("skill_summarize")
        assert isinstance(tool, SkillTool)
        assert tool._permission_mode_getter is getter

    def test_duplicate_skill_name_skipped(self) -> None:
        """If a skill tool name collides, it's skipped with a warning."""
        registry = _make_registry_with_fake()
        skills = {"summarize": _make_skill(name="summarize")}
        client = _make_client()

        # Register once
        register_skill_tools(registry, skills, client)
        # Register again — should not raise
        register_skill_tools(registry, skills, client)
        # Still only one skill_summarize
        count = sum(1 for n in registry.list_names() if n == "skill_summarize")
        assert count == 1


# ── REPL Integration ─────────────────────────────────────────────────


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="prompt_toolkit requires a console on Windows",
)
class TestReplSkillCommands:
    def test_run_unknown_skill(self) -> None:
        """``/run unknown`` prints error with available skills."""
        from zhi.repl import ReplSession

        ctx = MagicMock()
        ctx.permission_mode = MagicMock()
        ctx.permission_mode.value = "approve"
        ui = MagicMock()

        session = ReplSession(context=ctx, ui=ui)

        with patch("zhi.skills.discover_skills", return_value={}):
            result = session._handle_run("nonexistent")

        assert "Unknown skill" in result

    def test_skill_list_shows_skills(self) -> None:
        """`/skill list` shows discovered skills."""
        from zhi.repl import ReplSession

        ctx = MagicMock()
        ctx.permission_mode = MagicMock()
        ctx.permission_mode.value = "approve"
        ui = MagicMock()

        session = ReplSession(context=ctx, ui=ui)
        skills = {"summarize": _make_skill(name="summarize")}

        with patch("zhi.skills.discover_skills", return_value=skills):
            result = session._handle_skill("list")

        assert "summarize" in result

    def test_skill_list_empty(self) -> None:
        """`/skill list` when no skills exist."""
        from zhi.repl import ReplSession

        ctx = MagicMock()
        ctx.permission_mode = MagicMock()
        ctx.permission_mode.value = "approve"
        ui = MagicMock()

        session = ReplSession(context=ctx, ui=ui)

        with patch("zhi.skills.discover_skills", return_value={}):
            result = session._handle_skill("list")

        assert "No skills installed" in result
