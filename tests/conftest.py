"""Shared test fixtures for zhi."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Temporary config directory."""
    d = tmp_path / "config"
    d.mkdir()
    return d


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Temporary output directory."""
    d = tmp_path / "zhi-output"
    d.mkdir()
    return d


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"
