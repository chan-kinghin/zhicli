"""zhi - Agentic CLI powered by Zhipu GLM models."""

from __future__ import annotations

from importlib.metadata import version

__version__ = version("zhi")

# Public API
from zhi.client import Client
from zhi.config import ZhiConfig, load_config, save_config

__all__ = [
    "Client",
    "ZhiConfig",
    "__version__",
    "load_config",
    "save_config",
]
