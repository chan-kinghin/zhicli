"""Base tool abstract class for zhi."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class BaseTool(ABC):
    """Abstract base class for all zhi tools.

    Subclasses must define class-level attributes:
      - name: unique tool identifier
      - description: human-readable description for the model
      - parameters: JSON Schema dict describing accepted parameters
      - risky: whether the tool requires user permission (default False)

    And implement the execute() method.
    """

    name: ClassVar[str]
    description: ClassVar[str]
    parameters: ClassVar[dict[str, Any]]
    risky: ClassVar[bool] = False

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        """Execute the tool with the given arguments.

        Returns a string result to be sent back to the model.
        """
        ...

    def to_function_schema(self) -> dict[str, Any]:
        """Generate OpenAI-compatible function schema for API calls."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
