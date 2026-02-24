"""zhi - Agentic CLI powered by Zhipu GLM models."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("zhicli")
except PackageNotFoundError:
    try:
        from zhi._version import __version__  # type: ignore[no-redef]
    except ImportError:
        __version__ = "0.0.0-dev"

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
