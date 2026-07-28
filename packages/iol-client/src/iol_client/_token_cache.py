"""IOL refresh_token disk persistence helpers (Phase 14 SEC-01).

Sync API consumed directly by :mod:`iol_client.client`; the async mirror in
:mod:`iol_client.aio` invokes these same helpers via ``asyncio.to_thread``
(Plan 3). All file I/O is ``fcntl.flock``-locked and atomic via the POSIX
write-then-rename pattern (``os.replace``), so concurrent readers NEVER observe
a truncated or partially-written file.

This module is **package-private** (leading underscore): operators do NOT import
it directly. Its only consumers are the ``client.py`` / ``aio.py`` siblings.

Logger: ``logging.getLogger(__name__)`` resolves to ``"iol_client._token_cache"``
which inherits the ``iol_client``-namespace ``RedactingFilter`` installed by the
v1.1 LOG-02 ``attach()`` (anti-Pitfall 7 mitigation). The corrupt-file recovery
path (D-C1) logs EXACTLY ONE warning carrying only ``type(exc).__name__`` — never
the exception object, its args, its repr, or any file contents — so a leaked
refresh_token can never reach a downstream log handler.

Environment variables:

- ``CI``: when ``"true"``, :func:`_resolve_default_path` refuses to resolve a
  default disk path (anti-Pitfall 10 — no secret persistence on shared CI
  runners). The explicit ``IOL_TOKEN_CACHE_PATH`` override is resolved in
  ``client.py``, not here.

POSIX scope-lock: Phase 14 targets Linux/macOS (CONTEXT.md ``<domain>``). The
top-of-module ``import fcntl`` fails fast on Windows by design.

Usage (consumed from ``client.py``)::

    from iol_client import _token_cache

    path = _token_cache._resolve_default_path()
    if path is not None:
        _token_cache.save(path, refresh_token, acquired_at=time.time())
        cached = _token_cache.load(path)
        _token_cache.delete(path)
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import secrets
from pathlib import Path
from typing import Any

import platformdirs

logger = logging.getLogger(__name__)  # iol_client._token_cache

_SCHEMA_VERSION = 1


def _resolve_default_path() -> Path | None:
    """Return the platformdirs default cache path, or ``None`` on CI.

    Anti-Pitfall 10: when ``CI=true`` we refuse default-path persistence so a
    refresh_token is never written to a shared CI runner's filesystem. This
    function NEVER raises and NEVER touches the filesystem.
    """
    if os.environ.get("CI") == "true":
        return None
    base = Path(platformdirs.user_data_dir("iol-client", "market-libs"))
    return base / "refresh_token.json"


def load(path: Path) -> dict[str, Any] | None:
    """Load and validate the cached refresh_token JSON at ``path``.

    Returns the validated dict ``{"version": 1, "refresh_token": str,
    "acquired_at": float}`` on success, or ``None`` when the file is absent,
    corrupt, or fails shape validation.

    A missing file returns ``None`` silently (cold start is normal). Any other
    failure logs EXACTLY ONE warning carrying only ``type(exc).__name__`` (D-C1
    — never the exception, its args/repr, or file contents) and returns
    ``None``. The corrupt file is NOT deleted (D-C1: leave operator artifacts
    intact for inspection).
    """
    try:
        with open(path, "rb") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            data = json.load(f)
        if not isinstance(data, dict):
            raise TypeError("token cache root is not a JSON object")
        if data.get("version") != _SCHEMA_VERSION:
            raise ValueError("unsupported token cache schema version")
        refresh_token = data["refresh_token"]
        if not isinstance(refresh_token, str) or not refresh_token:
            raise ValueError("refresh_token missing or empty")
        acquired_at = float(data["acquired_at"])
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, KeyError, TypeError, ValueError, OSError) as exc:
        # D-C1: sanitized — type name ONLY, never exc / exc.args / file bytes.
        logger.warning(
            "ignoring unreadable token cache at %s (%s); falling back to password grant",
            path,
            type(exc).__name__,
        )
        return None
    return {"version": _SCHEMA_VERSION, "refresh_token": refresh_token, "acquired_at": acquired_at}


def save(path: Path, refresh_token: str, *, acquired_at: float) -> None:
    """Atomically persist ``refresh_token`` to ``path`` (write-then-rename).

    D-P3 atomic write-then-rename: writes to a unique tempfile in the same
    directory under ``fcntl.flock(LOCK_EX)``, fsyncs, chmods 0600 on the
    tempfile (so the final file has correct perms from the first moment — no
    0644 window), then ``os.replace(tmp, path)`` which is atomic on POSIX. On
    any failure the tempfile is unlinked and the exception re-raised.

    Parent dir is created 0700. Anti-Pitfalls 9 (flock) + 10 (0600/0700 perms).
    No log line on success: zero log sites equals zero leak risk.
    """
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.parent / f"{path.name}.tmp.{os.getpid()}.{secrets.token_hex(4)}"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(
                {
                    "version": _SCHEMA_VERSION,
                    "refresh_token": refresh_token,
                    "acquired_at": acquired_at,
                },
                f,
            )
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def delete(path: Path) -> None:
    """Remove the cached refresh_token file at ``path`` (idempotent).

    No-op if the file is already absent. No log line. Used by the anti-Pitfall 8
    cleanup-on-401 path before the password fallback.
    """
    path.unlink(missing_ok=True)
