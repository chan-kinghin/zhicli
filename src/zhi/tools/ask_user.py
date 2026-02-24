"""AskUserTool -- lets the LLM ask the user a question mid-execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

from zhi.tools.base import BaseTool


class AskUserTool(BaseTool):
    """Ask the user a question and wait for their response.

    The tool pauses execution, presents the question to the user,
    and returns their answer as the tool result.
    """

    name: ClassVar[str] = "ask_user"
    description: ClassVar[str] = (
        "Ask the user a question and wait for their response. "
        "Use this to gather missing information, clarify requirements, "
        "or let the user choose between options."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question to ask the user",
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of choices for the user to pick from",
            },
        },
        "required": ["question"],
    }
    risky: ClassVar[bool] = False

    def __init__(
        self, callback: Callable[[str, list[str] | None], str] | None = None
    ) -> None:
        self._callback = callback

    def execute(self, **kwargs: Any) -> str:
        """Ask the user a question and return their answer."""
        question = kwargs.get("question", "")
        options = kwargs.get("options")

        if not question:
            return "Error: No question provided"

        if self._callback is None:
            return "Error: ask_user is not available in this context (no UI callback)"

        try:
            answer = self._callback(question, options)
            return answer if answer else "(no response)"
        except Exception as e:
            return f"Error getting user input: {e}"
