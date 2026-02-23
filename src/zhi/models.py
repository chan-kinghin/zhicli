"""Model registry for Zhipu GLM models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ModelTier(str, Enum):
    """Model pricing tier."""

    PREMIUM = "premium"
    ECONOMY = "economy"


@dataclass(frozen=True)
class ModelInfo:
    """Metadata for a GLM model."""

    name: str
    tier: ModelTier
    supports_thinking: bool
    supports_tools: bool


MODELS: dict[str, ModelInfo] = {
    "glm-5": ModelInfo(
        name="glm-5",
        tier=ModelTier.PREMIUM,
        supports_thinking=True,
        supports_tools=True,
    ),
    "glm-4-flash": ModelInfo(
        name="glm-4-flash",
        tier=ModelTier.ECONOMY,
        supports_thinking=False,
        supports_tools=True,
    ),
    "glm-4-air": ModelInfo(
        name="glm-4-air",
        tier=ModelTier.ECONOMY,
        supports_thinking=False,
        supports_tools=True,
    ),
}


def get_model(name: str) -> ModelInfo | None:
    """Get model info by name. Returns None if unknown."""
    return MODELS.get(name)


def is_valid_model(name: str) -> bool:
    """Check if a model name is known."""
    return name in MODELS


def list_models() -> list[ModelInfo]:
    """List all known models."""
    return list(MODELS.values())
