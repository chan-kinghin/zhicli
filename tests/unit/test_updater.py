"""Tests for zhi.updater module."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from zhi.updater import (
    _CACHE_TTL,
    _parse_version,
    _read_cache,
    _write_cache,
    check_for_update,
    cleanup_old_exe,
    is_frozen,
    is_newer,
    perform_update,
    update_pip,
)

# ---------------------------------------------------------------------------
# Version parsing
# ---------------------------------------------------------------------------


class TestParseVersion:
    """Test _parse_version helper."""

    def test_simple_version(self) -> None:
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_two_part_version(self) -> None:
        assert _parse_version("1.2") == (1, 2)

    def test_single_part_version(self) -> None:
        assert _parse_version("5") == (5,)

    def test_leading_v(self) -> None:
        assert _parse_version("v1.2.3") == (1, 2, 3)

    def test_dev_suffix(self) -> None:
        # "dev0" starts with non-digit, so parsing stops at (1, 2, 3)
        assert _parse_version("1.2.3.dev0") == (1, 2, 3)

    def test_alpha_suffix(self) -> None:
        assert _parse_version("1.2.3a1") == (1, 2, 3)

    def test_empty_string(self) -> None:
        assert _parse_version("") == (0,)

    def test_whitespace(self) -> None:
        assert _parse_version("  1.2.3  ") == (1, 2, 3)

    def test_non_numeric(self) -> None:
        assert _parse_version("abc") == (0,)


# ---------------------------------------------------------------------------
# is_newer
# ---------------------------------------------------------------------------


class TestIsNewer:
    """Test is_newer comparison."""

    def test_newer_patch(self) -> None:
        assert is_newer("1.0.1", "1.0.0") is True

    def test_newer_minor(self) -> None:
        assert is_newer("1.1.0", "1.0.9") is True

    def test_newer_major(self) -> None:
        assert is_newer("2.0.0", "1.9.9") is True

    def test_same_version(self) -> None:
        assert is_newer("1.0.0", "1.0.0") is False

    def test_older(self) -> None:
        assert is_newer("1.0.0", "1.0.1") is False

    def test_with_v_prefix(self) -> None:
        assert is_newer("v1.1.0", "v1.0.0") is True

    def test_different_lengths(self) -> None:
        assert is_newer("1.1", "1.0.9") is True


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


class TestCache:
    """Test update cache read/write."""

    def test_write_and_read_cache(self, tmp_path: Path) -> None:
        _write_cache("1.2.3", config_dir=tmp_path)
        cached = _read_cache(config_dir=tmp_path)
        assert cached is not None
        assert cached["version"] == "1.2.3"

    def test_read_cache_missing(self, tmp_path: Path) -> None:
        assert _read_cache(config_dir=tmp_path) is None

    def test_read_cache_expired(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "update_cache.json"
        data = {"version": "1.0.0", "checked_at": time.time() - _CACHE_TTL - 1}
        cache_file.write_text(json.dumps(data), encoding="utf-8")
        assert _read_cache(config_dir=tmp_path) is None

    def test_read_cache_not_expired(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "update_cache.json"
        data = {"version": "1.0.0", "checked_at": time.time()}
        cache_file.write_text(json.dumps(data), encoding="utf-8")
        cached = _read_cache(config_dir=tmp_path)
        assert cached is not None
        assert cached["version"] == "1.0.0"

    def test_read_cache_corrupt_json(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "update_cache.json"
        cache_file.write_text("not json!!!", encoding="utf-8")
        assert _read_cache(config_dir=tmp_path) is None

    def test_read_cache_missing_version(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "update_cache.json"
        data = {"checked_at": time.time()}
        cache_file.write_text(json.dumps(data), encoding="utf-8")
        assert _read_cache(config_dir=tmp_path) is None

    def test_read_cache_not_dict(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "update_cache.json"
        cache_file.write_text('"just a string"', encoding="utf-8")
        assert _read_cache(config_dir=tmp_path) is None

    def test_write_cache_creates_dir(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b"
        _write_cache("2.0.0", config_dir=nested)
        assert (nested / "update_cache.json").exists()


# ---------------------------------------------------------------------------
# check_for_update
# ---------------------------------------------------------------------------


class TestCheckForUpdate:
    """Test the cache-aware update check."""

    def test_returns_none_when_up_to_date(self, tmp_path: Path) -> None:
        with patch("zhi.updater._fetch_latest_version_pypi", return_value="1.0.0"):
            result = check_for_update("1.0.0", config_dir=tmp_path, force=True)
        assert result is None

    def test_returns_dict_when_update_available(self, tmp_path: Path) -> None:
        with patch("zhi.updater._fetch_latest_version_pypi", return_value="2.0.0"):
            result = check_for_update("1.0.0", config_dir=tmp_path, force=True)
        assert result is not None
        assert result["current"] == "1.0.0"
        assert result["latest"] == "2.0.0"

    def test_returns_none_on_fetch_failure(self, tmp_path: Path) -> None:
        with patch("zhi.updater._fetch_latest_version_pypi", return_value=None):
            result = check_for_update("1.0.0", config_dir=tmp_path, force=True)
        assert result is None

    def test_uses_cache_when_not_forced(self, tmp_path: Path) -> None:
        # Write a cache saying 2.0.0 is latest
        _write_cache("2.0.0", config_dir=tmp_path)
        with patch("zhi.updater._fetch_latest_version_pypi") as mock_fetch:
            result = check_for_update("1.0.0", config_dir=tmp_path, force=False)
        # Should NOT have called fetch — used cache
        mock_fetch.assert_not_called()
        assert result is not None
        assert result["latest"] == "2.0.0"

    def test_cache_hit_up_to_date(self, tmp_path: Path) -> None:
        _write_cache("1.0.0", config_dir=tmp_path)
        with patch("zhi.updater._fetch_latest_version_pypi") as mock_fetch:
            result = check_for_update("1.0.0", config_dir=tmp_path, force=False)
        mock_fetch.assert_not_called()
        assert result is None

    def test_force_bypasses_cache(self, tmp_path: Path) -> None:
        _write_cache("1.0.0", config_dir=tmp_path)
        with patch("zhi.updater._fetch_latest_version_pypi", return_value="2.0.0"):
            result = check_for_update("1.0.0", config_dir=tmp_path, force=True)
        assert result is not None
        assert result["latest"] == "2.0.0"

    def test_never_raises(self, tmp_path: Path) -> None:
        with patch(
            "zhi.updater._fetch_latest_version_pypi",
            side_effect=RuntimeError("boom"),
        ):
            result = check_for_update("1.0.0", config_dir=tmp_path, force=True)
        assert result is None

    def test_writes_cache_after_fetch(self, tmp_path: Path) -> None:
        with patch("zhi.updater._fetch_latest_version_pypi", return_value="1.5.0"):
            check_for_update("1.0.0", config_dir=tmp_path, force=True)
        cached = _read_cache(config_dir=tmp_path)
        assert cached is not None
        assert cached["version"] == "1.5.0"


# ---------------------------------------------------------------------------
# is_frozen
# ---------------------------------------------------------------------------


class TestIsFrozen:
    """Test PyInstaller frozen detection."""

    def test_not_frozen_normally(self) -> None:
        assert is_frozen() is False

    def test_frozen_when_attr_set(self) -> None:
        with patch.object(sys, "frozen", True, create=True):
            assert is_frozen() is True


# ---------------------------------------------------------------------------
# update_pip
# ---------------------------------------------------------------------------


class TestUpdatePip:
    """Test pip-based update."""

    def test_success(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert update_pip() is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "pip" in args
        assert "zhicli" in args

    def test_failure(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert update_pip() is False

    def test_exception(self) -> None:
        with patch("subprocess.run", side_effect=OSError("fail")):
            assert update_pip() is False


# ---------------------------------------------------------------------------
# cleanup_old_exe
# ---------------------------------------------------------------------------


class TestCleanupOldExe:
    """Test old exe cleanup."""

    def test_noop_when_not_frozen(self) -> None:
        # Should do nothing (and not crash) when not frozen
        cleanup_old_exe()

    def test_removes_old_file(self, tmp_path: Path) -> None:
        old_file = tmp_path / "zhi.old"
        old_file.write_text("old")
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "executable", str(tmp_path / "zhi.exe")),
        ):
            # sys.executable -> zhi.exe, so .old -> zhi.old
            # But Path.with_suffix works on the full path
            exe_path = Path(sys.executable)
            old_path = exe_path.with_suffix(".old")
            old_path.write_text("old data")
            cleanup_old_exe()
            assert not old_path.exists()


# ---------------------------------------------------------------------------
# perform_update
# ---------------------------------------------------------------------------


class TestPerformUpdate:
    """Test high-level perform_update."""

    def test_up_to_date(self) -> None:
        with (
            patch("zhi.updater.check_for_update", return_value=None),
            patch("zhi.__version__", "1.0.0"),
        ):
            success, msg = perform_update()
        assert success is True
        assert "1.0.0" in msg

    def test_pip_update_success(self) -> None:
        update_info = {"current": "1.0.0", "latest": "2.0.0"}
        with (
            patch("zhi.updater.check_for_update", return_value=update_info),
            patch("zhi.updater.is_frozen", return_value=False),
            patch("zhi.updater.update_pip", return_value=True),
            patch("zhi.__version__", "1.0.0"),
        ):
            success, msg = perform_update()
        assert success is True
        assert "2.0.0" in msg

    def test_pip_update_failure(self) -> None:
        update_info = {"current": "1.0.0", "latest": "2.0.0"}
        with (
            patch("zhi.updater.check_for_update", return_value=update_info),
            patch("zhi.updater.is_frozen", return_value=False),
            patch("zhi.updater.update_pip", return_value=False),
            patch("zhi.__version__", "1.0.0"),
        ):
            success, _msg = perform_update()
        assert success is False

    def test_exe_update_dispatched_when_frozen(self) -> None:
        update_info = {"current": "1.0.0", "latest": "2.0.0"}
        with (
            patch("zhi.updater.check_for_update", return_value=update_info),
            patch("zhi.updater.is_frozen", return_value=True),
            patch("zhi.updater.update_exe", return_value=True) as mock_exe,
            patch("zhi.__version__", "1.0.0"),
        ):
            success, _msg = perform_update()
        assert success is True
        mock_exe.assert_called_once()
