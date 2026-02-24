"""End-to-end regression tests for the 5 boundary-validation fixes.

Each test targets a specific bug that was silently failing before the fix:

1. CSV with non-list rows -- writerows() crashed on non-iterable
2. XLSX with non-dict sheet_data -- .get() crashed on non-dict
3. Empty required file arg -- API call wasted on empty context
4. Nameless input_args -- schema silently included bad entry
5. status_code=0 masked by ``or`` truthiness -- wrong error classification
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import MagicMock, patch

import pytest

from zhi.client import Client, RateLimitError
from zhi.skills.loader import SkillConfig
from zhi.tools.base import BaseTool
from zhi.tools.file_write import FileWriteTool
from zhi.tools.skill_tool import SkillTool

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill(
    name: str = "test-skill",
    tools: list[str] | None = None,
    input_args: list[dict[str, Any]] | None = None,
) -> SkillConfig:
    return SkillConfig(
        name=name,
        description="Test skill",
        system_prompt="You are a test assistant.",
        tools=tools or ["file_read"],
        model="glm-4-flash",
        max_turns=5,
        input_args=input_args or [],
    )


def _make_client() -> MagicMock:
    client = MagicMock()

    @dataclass
    class FakeResponse:
        content: str = "done"
        tool_calls: list[Any] = field(default_factory=list)
        thinking: str | None = None
        total_tokens: int = 10

    client.chat.return_value = FakeResponse()
    return client


def _make_registry() -> Any:
    from zhi.tools import ToolRegistry

    class FakeFileRead(BaseTool):
        name: ClassVar[str] = "file_read"
        description: ClassVar[str] = "Read a file."
        parameters: ClassVar[dict[str, Any]] = {
            "type": "object",
            "properties": {},
        }

        def execute(self, **kwargs: Any) -> str:
            return "contents"

    reg = ToolRegistry()
    reg.register(FakeFileRead())
    return reg


# ---------------------------------------------------------------------------
# Fix 1: CSV with non-list rows
# ---------------------------------------------------------------------------


class TestCsvNonListRows:
    """CSV content with non-list ``rows`` must return a clear error, not crash."""

    def test_rows_as_string_returns_error(self, tmp_path: Path) -> None:
        tool = FileWriteTool(output_dir=tmp_path / "out")
        result = tool.execute(
            path="bad.csv",
            content={"headers": ["Name", "Age"], "rows": "not a list"},
        )
        assert "Error" in result
        assert "rows" in result.lower()

    def test_rows_as_dict_returns_error(self, tmp_path: Path) -> None:
        tool = FileWriteTool(output_dir=tmp_path / "out")
        result = tool.execute(
            path="bad.csv",
            content={"headers": ["A"], "rows": {"a": 1}},
        )
        assert "Error" in result
        assert "rows" in result.lower()

    def test_rows_as_int_returns_error(self, tmp_path: Path) -> None:
        tool = FileWriteTool(output_dir=tmp_path / "out")
        result = tool.execute(
            path="bad.csv",
            content={"headers": ["X"], "rows": 42},
        )
        assert "Error" in result
        assert "rows" in result.lower()

    def test_valid_rows_still_work(self, tmp_path: Path) -> None:
        """Sanity check: valid rows produce a file."""
        tool = FileWriteTool(output_dir=tmp_path / "out")
        result = tool.execute(
            path="good.csv",
            content={"headers": ["Name"], "rows": [["Alice"]]},
        )
        assert "File written" in result


# ---------------------------------------------------------------------------
# Fix 2: XLSX with non-dict sheet_data
# ---------------------------------------------------------------------------


class TestXlsxNonDictSheetData:
    """XLSX with non-dict sheet entries must return a clear error."""

    def test_sheet_as_string_returns_error(self, tmp_path: Path) -> None:
        tool = FileWriteTool(output_dir=tmp_path / "out")
        result = tool.execute(
            path="bad.xlsx",
            content={"sheets": ["not a dict"]},
        )
        assert "Error" in result
        assert "Sheet 1" in result

    def test_sheet_as_list_returns_error(self, tmp_path: Path) -> None:
        tool = FileWriteTool(output_dir=tmp_path / "out")
        result = tool.execute(
            path="bad.xlsx",
            content={"sheets": [["nested", "list"]]},
        )
        assert "Error" in result
        assert "Sheet 1" in result

    def test_second_sheet_invalid_returns_error(self, tmp_path: Path) -> None:
        """Error references the correct sheet number."""
        tool = FileWriteTool(output_dir=tmp_path / "out")
        result = tool.execute(
            path="bad.xlsx",
            content={
                "sheets": [
                    {"name": "Good", "headers": ["A"], "rows": [["val"]]},
                    "bad",
                ]
            },
        )
        assert "Error" in result
        assert "Sheet 2" in result

    def test_valid_sheets_still_work(self, tmp_path: Path) -> None:
        tool = FileWriteTool(output_dir=tmp_path / "out")
        result = tool.execute(
            path="good.xlsx",
            content={
                "sheets": [{"name": "Data", "headers": ["Col"], "rows": [["val"]]}]
            },
        )
        assert "File written" in result


# ---------------------------------------------------------------------------
# Fix 3: Empty required file arg fails fast
# ---------------------------------------------------------------------------


class TestEmptyRequiredFileArg:
    """Empty required file arg must return error BEFORE making API call."""

    def test_empty_string_file_returns_error(self) -> None:
        client = _make_client()
        registry = _make_registry()
        skill = _make_skill(
            input_args=[{"name": "file", "type": "file", "required": True}]
        )
        tool = SkillTool(skill=skill, client=client, registry=registry)

        result = tool.execute(input="Analyze", file="")

        assert "Error" in result
        assert "'file'" in result
        assert "empty" in result.lower()
        client.chat.assert_not_called()

    def test_missing_file_kwarg_returns_error(self) -> None:
        """When the required file kwarg is not passed at all."""
        client = _make_client()
        registry = _make_registry()
        skill = _make_skill(
            input_args=[{"name": "doc", "type": "file", "required": True}]
        )
        tool = SkillTool(skill=skill, client=client, registry=registry)

        result = tool.execute(input="Analyze")

        assert "Error" in result
        assert "'doc'" in result
        client.chat.assert_not_called()

    def test_optional_file_arg_empty_is_ok(self) -> None:
        """Empty optional file arg should NOT trigger the error."""
        client = _make_client()
        registry = _make_registry()
        skill = _make_skill(
            input_args=[{"name": "file", "type": "file", "required": False}]
        )
        tool = SkillTool(skill=skill, client=client, registry=registry)

        result = tool.execute(input="test", file="")

        # Should proceed normally -- the client was called
        assert "Error" not in result or "empty" not in result.lower()
        client.chat.assert_called_once()


# ---------------------------------------------------------------------------
# Fix 4: Nameless input_args logged as warning and skipped
# ---------------------------------------------------------------------------


class TestNamelessInputArgs:
    """input_args with no ``name`` must be omitted from schema with a warning."""

    def test_nameless_arg_omitted_from_schema(self) -> None:
        skill = _make_skill(
            input_args=[
                {"description": "This has no name"},
                {"name": "good_arg", "type": "string", "description": "valid"},
            ]
        )
        client = _make_client()
        registry = _make_registry()
        tool = SkillTool(skill=skill, client=client, registry=registry)

        schema = tool.to_function_schema()
        props = schema["function"]["parameters"]["properties"]

        # Only 'input' and 'good_arg' should be present
        assert "good_arg" in props
        assert len(props) == 2  # input + good_arg

    def test_nameless_arg_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        skill = _make_skill(input_args=[{"description": "nameless"}])
        client = _make_client()
        registry = _make_registry()
        tool = SkillTool(skill=skill, client=client, registry=registry)

        with caplog.at_level(logging.WARNING, logger="zhi.tools.skill_tool"):
            tool.to_function_schema()

        assert any("no name" in record.message.lower() for record in caplog.records)

    def test_empty_name_string_also_skipped(self) -> None:
        """An arg with name='' should also be skipped."""
        skill = _make_skill(input_args=[{"name": "", "description": "empty name"}])
        client = _make_client()
        registry = _make_registry()
        tool = SkillTool(skill=skill, client=client, registry=registry)

        schema = tool.to_function_schema()
        props = schema["function"]["parameters"]["properties"]
        assert list(props.keys()) == ["input"]


# ---------------------------------------------------------------------------
# Fix 5: status_code=0 not masked by ``or`` truthiness
# ---------------------------------------------------------------------------


class TestStatusCodeZero:
    """status_code=0 must be used as error_code, not skipped as falsy."""

    @patch("zhi.client.ZhipuAI")
    def test_status_code_zero_not_classified_as_rate_limit(
        self, mock_sdk_cls: MagicMock
    ) -> None:
        """With status_code=0 and code=429, error should NOT be RateLimitError."""
        client = Client(api_key="sk-test", max_retries=0)
        error = Exception("some error")
        error.status_code = 0  # type: ignore[attr-defined]
        error.code = 429  # type: ignore[attr-defined]

        classified = client._classify_error(error)

        # status_code=0 is checked first (not falsy anymore);
        # 0 doesn't match any known code, so it falls to generic ClientError
        assert not isinstance(classified, RateLimitError)
        assert classified.code == "CLIENT_ERROR"

    @patch("zhi.client.ZhipuAI")
    def test_status_code_none_falls_through_to_code_attr(
        self, mock_sdk_cls: MagicMock
    ) -> None:
        """When status_code is None, code attribute should be used."""
        client = Client(api_key="sk-test", max_retries=0)
        error = Exception("rate limit exceeded")
        error.status_code = None  # type: ignore[attr-defined]
        error.code = 429  # type: ignore[attr-defined]

        classified = client._classify_error(error)

        # status_code is None, so code=429 is used -> RateLimitError
        assert isinstance(classified, RateLimitError)

    @patch("zhi.client.ZhipuAI")
    def test_status_code_401_still_auth_error(self, mock_sdk_cls: MagicMock) -> None:
        """Normal status_code=401 still correctly classified."""
        from zhi.client import AuthenticationError

        client = Client(api_key="sk-test", max_retries=0)
        error = Exception("unauthorized")
        error.status_code = 401  # type: ignore[attr-defined]

        classified = client._classify_error(error)
        assert isinstance(classified, AuthenticationError)


# ---------------------------------------------------------------------------
# Cross-fix integration: multiple boundaries together
# ---------------------------------------------------------------------------


class TestBoundaryIntegration:
    """Tests that combine multiple boundary conditions."""

    def test_csv_then_valid_write_works(self, tmp_path: Path) -> None:
        """After a bad CSV write returns error, a good write still works."""
        tool = FileWriteTool(output_dir=tmp_path / "out")
        bad = tool.execute(path="bad.csv", content={"headers": [], "rows": "nope"})
        assert "Error" in bad

        good = tool.execute(
            path="good.csv", content={"headers": ["A"], "rows": [["1"]]}
        )
        assert "File written" in good

    def test_skill_with_bad_and_good_args(self) -> None:
        """Skill with one nameless arg and one valid arg: valid arg preserved."""
        skill = _make_skill(
            input_args=[
                {"description": "no name"},
                {"name": "target", "type": "string", "description": "valid"},
            ]
        )
        tool = SkillTool(skill=skill, client=_make_client(), registry=_make_registry())
        schema = tool.to_function_schema()
        props = schema["function"]["parameters"]["properties"]
        assert "target" in props
        assert len(props) == 2  # input + target
