"""Comparison tests: disable_model_invocation=True vs False.

Demonstrates the concrete improvements when a skill uses
disable_model_invocation — no API calls, no tool resolution,
deterministic output, and faster execution.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, ClassVar
from unittest.mock import MagicMock, call, patch

from zhi.skills.loader import SkillConfig
from zhi.tools import ToolRegistry
from zhi.tools.base import BaseTool
from zhi.tools.skill_tool import SkillTool

# ── Helpers ──────────────────────────────────────────────────────────

RECIPE_PROMPT = """\
# Git Commit Checklist

1. Run `git status` to see changed files.
2. Run `git diff --staged` to review staged changes.
3. Write a commit message following Conventional Commits.
4. Run `git commit -m "<message>"`.
5. Verify with `git log --oneline -1`."""


def _make_skill(
    disable_model_invocation: bool = False,
    system_prompt: str = RECIPE_PROMPT,
    **kwargs: Any,
) -> SkillConfig:
    return SkillConfig(
        name=kwargs.get("name", "git-commit-recipe"),
        description="Step-by-step git commit recipe",
        system_prompt=system_prompt,
        tools=kwargs.get("tools", ["file_read", "shell"]),
        model="glm-4-flash",
        max_turns=5,
        disable_model_invocation=disable_model_invocation,
    )


def _make_client() -> MagicMock:
    @dataclass
    class FakeResponse:
        content: str = "Mock LLM result"
        tool_calls: list[Any] = field(default_factory=list)
        thinking: str | None = None
        total_tokens: int = 42

    client = MagicMock()
    client.chat.return_value = FakeResponse()
    return client


def _make_registry() -> ToolRegistry:
    class FakeFileRead(BaseTool):
        name: ClassVar[str] = "file_read"
        description: ClassVar[str] = "Read a file."
        parameters: ClassVar[dict[str, Any]] = {
            "type": "object",
            "properties": {},
        }

        def execute(self, **kwargs: Any) -> str:
            return "file contents"

    class FakeShell(BaseTool):
        name: ClassVar[str] = "shell"
        description: ClassVar[str] = "Run shell command."
        parameters: ClassVar[dict[str, Any]] = {
            "type": "object",
            "properties": {},
        }

        def execute(self, **kwargs: Any) -> str:
            return "shell output"

    reg = ToolRegistry()
    reg.register(FakeFileRead())
    reg.register(FakeShell())
    return reg


# ── Comparison: API calls ────────────────────────────────────────────


class TestApiCallComparison:
    """The key improvement: disable_model_invocation skips the LLM entirely."""

    def test_normal_skill_makes_api_call(self) -> None:
        """Standard skill: sends request to LLM, consumes tokens."""
        client = _make_client()
        skill = _make_skill(disable_model_invocation=False)
        tool = SkillTool(skill=skill, client=client, registry=_make_registry())

        tool.execute(input="Commit my changes")

        # LLM was called — this costs tokens and adds latency
        client.chat.assert_called_once()

    def test_disabled_invocation_makes_zero_api_calls(self) -> None:
        """Disabled invocation: zero LLM calls, zero tokens consumed."""
        client = _make_client()
        skill = _make_skill(disable_model_invocation=True)
        tool = SkillTool(skill=skill, client=client, registry=_make_registry())

        tool.execute(input="Commit my changes")

        # No API call — zero cost, instant response
        client.chat.assert_not_called()


# ── Comparison: output determinism ───────────────────────────────────


class TestOutputDeterminism:
    """Disabled invocation returns the exact recipe text every time."""

    def test_normal_skill_output_depends_on_llm(self) -> None:
        """Standard skill: output is whatever the LLM generates."""
        client = _make_client()
        skill = _make_skill(disable_model_invocation=False)
        tool = SkillTool(skill=skill, client=client, registry=_make_registry())

        result = tool.execute(input="Commit my changes")

        # Output is LLM-dependent — may vary between runs
        assert result == "Mock LLM result"
        assert RECIPE_PROMPT not in result

    def test_disabled_invocation_output_is_deterministic(self) -> None:
        """Disabled invocation: output is always the recipe + user input."""
        skill = _make_skill(disable_model_invocation=True)
        tool = SkillTool(
            skill=skill, client=_make_client(), registry=_make_registry()
        )

        # Run it multiple times — always identical
        results = [tool.execute(input="Commit my changes") for _ in range(3)]

        assert all(r == results[0] for r in results)
        assert RECIPE_PROMPT in results[0]
        assert "Commit my changes" in results[0]

    def test_output_structure_is_prompt_then_input(self) -> None:
        """The returned text is system_prompt followed by user input."""
        skill = _make_skill(disable_model_invocation=True)
        tool = SkillTool(
            skill=skill, client=_make_client(), registry=_make_registry()
        )

        result = tool.execute(input="Please help")

        # system_prompt comes first, then double newline, then user input
        prompt_pos = result.index("# Git Commit Checklist")
        input_pos = result.index("Please help")
        assert prompt_pos < input_pos


# ── Comparison: tool resolution skipped ──────────────────────────────


class TestToolResolutionSkipped:
    """Disabled invocation skips the expensive tool-building step."""

    def test_normal_skill_resolves_tools(self) -> None:
        """Standard skill: looks up each tool in the registry."""
        client = _make_client()
        registry = _make_registry()
        skill = _make_skill(disable_model_invocation=False)
        tool = SkillTool(skill=skill, client=client, registry=registry)

        with patch("zhi.tools.skill_tool.agent_run", return_value="ok") as mock_run:
            tool.execute(input="test")

        # Tools were resolved and passed to the agent context
        ctx = mock_run.call_args.args[0]
        assert len(ctx.tools) > 0
        assert len(ctx.tool_schemas) > 0

    def test_disabled_invocation_skips_tool_resolution(self) -> None:
        """Disabled invocation: registry.get() is never called for tools."""
        client = _make_client()
        registry = _make_registry()
        # Spy on registry.get to count calls
        original_get = registry.get
        get_calls: list[str] = []

        def tracking_get(name: str) -> Any:
            get_calls.append(name)
            return original_get(name)

        registry.get = tracking_get  # type: ignore[assignment]

        skill = _make_skill(disable_model_invocation=True)
        tool = SkillTool(skill=skill, client=client, registry=registry)

        tool.execute(input="test")

        # No tool lookups happened — the entire resolution step was skipped
        assert len(get_calls) == 0


# ── Comparison: execution speed ──────────────────────────────────────


class TestExecutionSpeed:
    """Disabled invocation is measurably faster (no LLM round-trip)."""

    def test_disabled_is_faster_than_normal(self) -> None:
        """Direct return is faster than going through the agent loop."""
        client = _make_client()
        registry = _make_registry()

        # Time the normal path
        normal_skill = _make_skill(disable_model_invocation=False)
        normal_tool = SkillTool(
            skill=normal_skill, client=client, registry=registry
        )
        t0 = time.perf_counter()
        normal_tool.execute(input="test")
        normal_time = time.perf_counter() - t0

        # Time the disabled path
        disabled_skill = _make_skill(disable_model_invocation=True)
        disabled_tool = SkillTool(
            skill=disabled_skill, client=client, registry=registry
        )
        t0 = time.perf_counter()
        disabled_tool.execute(input="test")
        disabled_time = time.perf_counter() - t0

        # Disabled should be faster (no mock client overhead, no Context creation)
        # In production the difference is dramatic (no real API round-trip)
        assert disabled_time <= normal_time


# ── Safety: guards still apply ───────────────────────────────────────


class TestSafetyGuardsStillApply:
    """disable_model_invocation doesn't bypass any safety checks."""

    def test_cycle_detection_blocks_before_return(self) -> None:
        skill = _make_skill(name="self-ref", disable_model_invocation=True)
        tool = SkillTool(
            skill=skill,
            client=_make_client(),
            registry=_make_registry(),
            call_stack=frozenset({"self-ref"}),
        )
        result = tool.execute(input="test")
        assert "Recursion blocked" in result
        # The recipe text is NOT returned — safety took priority
        assert RECIPE_PROMPT not in result

    def test_depth_limit_blocks_before_return(self) -> None:
        skill = _make_skill(disable_model_invocation=True)
        tool = SkillTool(
            skill=skill,
            client=_make_client(),
            registry=_make_registry(),
            depth=99,
        )
        result = tool.execute(input="test")
        assert "max depth" in result.lower()
        assert RECIPE_PROMPT not in result

    def test_required_file_validation_still_fires(self) -> None:
        skill = SkillConfig(
            name="file-recipe",
            description="Recipe needing a file",
            system_prompt="Process the file.",
            tools=["file_read"],
            model="glm-4-flash",
            max_turns=5,
            input_args=[{"name": "file", "type": "file", "required": True}],
            disable_model_invocation=True,
        )
        tool = SkillTool(
            skill=skill, client=_make_client(), registry=_make_registry()
        )
        result = tool.execute(input="go", file="")
        assert "Error" in result
        assert "'file'" in result
