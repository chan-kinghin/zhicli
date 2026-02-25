"""Auto-update support for zhi.

Provides version checking (via PyPI), caching, and self-update
for both pip installs and PyInstaller-frozen exe builds.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from zhi.config import get_config_dir
from zhi.i18n import t

logger = logging.getLogger(__name__)

_PYPI_URL = "https://pypi.org/pypi/zhicli/json"
_GITHUB_RELEASE_URL = "https://api.github.com/repos/chan-kinghin/zhicli/releases/latest"
_CACHE_FILE = "update_cache.json"
_CACHE_TTL = 86400  # 24 hours in seconds
_REQUEST_TIMEOUT = 5  # seconds
_MIN_EXE_SIZE = 1_000_000  # 1MB minimum for a valid PyInstaller bundle


# ---------------------------------------------------------------------------
# Version parsing & comparison
# ---------------------------------------------------------------------------


def _parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a version string like '1.2.3' into a comparable tuple.

    Strips leading 'v' and ignores non-numeric suffixes (e.g. '1.2.3.dev0').
    Returns (0,) for unparseable strings.
    """
    v = version_str.strip().lstrip("v")
    parts: list[int] = []
    for segment in v.split("."):
        # Take only leading digits from each segment
        digits = ""
        for ch in segment:
            if ch.isdigit():
                digits += ch
            else:
                break
        if digits:
            parts.append(int(digits))
        else:
            break
    return tuple(parts) if parts else (0,)


def is_newer(latest: str, current: str) -> bool:
    """Return True if *latest* is strictly newer than *current*."""
    return _parse_version(latest) > _parse_version(current)


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def _cache_path(config_dir: Path | None = None) -> Path:
    """Return the path to the update cache file."""
    if config_dir is None:
        config_dir = get_config_dir()
    return config_dir / _CACHE_FILE


def _read_cache(config_dir: Path | None = None) -> dict[str, Any] | None:
    """Read the update cache. Returns None if missing/expired/corrupt."""
    path = _cache_path(config_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        checked_at = data.get("checked_at", 0)
        if time.time() - checked_at > _CACHE_TTL:
            return None
        if "version" not in data:
            return None
        return data
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def _write_cache(version: str, config_dir: Path | None = None) -> None:
    """Write the latest version to the cache."""
    path = _cache_path(config_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"version": version, "checked_at": time.time()}
        path.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        logger.debug("Could not write update cache to %s", path)


# ---------------------------------------------------------------------------
# Network: fetch latest version
# ---------------------------------------------------------------------------


def _fetch_latest_version_pypi() -> str | None:
    """Fetch the latest version string from PyPI. Returns None on failure."""
    try:
        resp = httpx.get(_PYPI_URL, timeout=_REQUEST_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
        version = data.get("info", {}).get("version")
        return version if isinstance(version, str) else None
    except (httpx.HTTPError, KeyError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Public: check for update (cache-aware, never raises)
# ---------------------------------------------------------------------------


def check_for_update(
    current_version: str,
    config_dir: Path | None = None,
    *,
    force: bool = False,
) -> dict[str, str] | None:
    """Check if a newer version is available.

    Returns ``{"current": ..., "latest": ...}`` when an update is found,
    or ``None`` when up-to-date or on error.

    Uses a 24-hour cache to avoid hitting the network every invocation.
    Pass ``force=True`` to bypass the cache (used by ``zhi update``).

    This function never raises — all errors are caught and logged.
    """
    try:
        # Try cache first
        if not force:
            cached = _read_cache(config_dir)
            if cached is not None:
                latest = cached["version"]
                if is_newer(latest, current_version):
                    return {"current": current_version, "latest": latest}
                return None

        # Fetch from PyPI
        latest = _fetch_latest_version_pypi()
        if latest is None:
            return None

        # Update cache
        _write_cache(latest, config_dir)

        if is_newer(latest, current_version):
            return {"current": current_version, "latest": latest}
        return None

    except Exception:
        logger.debug("Update check failed", exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Frozen (PyInstaller) detection
# ---------------------------------------------------------------------------


def is_frozen() -> bool:
    """Return True if running as a PyInstaller-frozen exe."""
    return getattr(sys, "frozen", False) is True


# ---------------------------------------------------------------------------
# Self-update: pip
# ---------------------------------------------------------------------------


def update_pip() -> bool:
    """Update zhicli via pip. Returns True on success."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "zhicli"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, OSError) as exc:
        logger.debug("pip update failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Self-update: exe (PyInstaller)
# ---------------------------------------------------------------------------


def _get_exe_download_url() -> str | None:
    """Get the Windows exe download URL from the latest GitHub release."""
    try:
        resp = httpx.get(
            _GITHUB_RELEASE_URL,
            timeout=_REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if name.endswith(".exe"):
                url: str | None = asset.get("browser_download_url")
                return url
        return None
    except (httpx.HTTPError, KeyError, ValueError):
        return None


def update_exe(
    progress_callback: Any | None = None,
) -> bool:
    """Download and swap the running exe. Returns True on success.

    The strategy:
    1. Download new exe to a temp file next to the current exe.
    2. Rename current exe → current.old
    3. Rename temp → current name
    4. The .old file is cleaned up on next startup via cleanup_old_exe().

    ``progress_callback``, if provided, is called with (percent: int).
    """
    current_exe = Path(sys.executable)
    if not current_exe.exists():
        return False

    url = _get_exe_download_url()
    if url is None:
        return False

    temp_path = current_exe.with_suffix(".new")
    old_path = current_exe.with_suffix(".old")

    try:
        # Download with streaming
        with httpx.stream("GET", url, timeout=30, follow_redirects=True) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(temp_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total > 0:
                        percent = int(downloaded * 100 / total)
                        progress_callback(percent)

        # Validate size
        if temp_path.stat().st_size < _MIN_EXE_SIZE:
            logger.warning("Downloaded file too small, aborting update")
            temp_path.unlink(missing_ok=True)
            return False

        # Swap: current -> .old, .new -> current
        if old_path.exists():
            old_path.unlink()
        current_exe.rename(old_path)
        temp_path.rename(current_exe)
        return True

    except (httpx.HTTPError, OSError) as exc:
        logger.debug("exe update failed: %s", exc)
        # Try to restore if the rename was partial
        temp_path.unlink(missing_ok=True)
        return False


def cleanup_old_exe() -> None:
    """Remove leftover .old exe from a previous update."""
    if not is_frozen():
        return
    old_path = Path(sys.executable).with_suffix(".old")
    if old_path.exists():
        try:
            old_path.unlink()
            logger.debug("Cleaned up old exe: %s", old_path)
        except OSError:
            logger.debug("Could not remove old exe: %s", old_path)


# ---------------------------------------------------------------------------
# High-level: perform update
# ---------------------------------------------------------------------------


def perform_update(
    progress_callback: Any | None = None,
) -> tuple[bool, str]:
    """Perform a self-update. Returns (success, message).

    Dispatches to pip or exe update based on how zhi is running.
    """
    from zhi import __version__

    # Check if there's actually an update available
    print(t("update.checking"))
    result = check_for_update(__version__, force=True)

    if result is None:
        return True, t("update.up_to_date", current=__version__)

    latest = result["latest"]

    if is_frozen():
        print(t("update.updating_exe"))
        success = update_exe(progress_callback=progress_callback)
    else:
        print(t("update.updating_pip"))
        success = update_pip()

    if success:
        return True, t("update.success", version=latest)
    else:
        return False, t("update.failed", error="see log for details")
