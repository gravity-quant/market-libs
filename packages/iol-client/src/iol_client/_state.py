"""Per-instance state for ``iol-client`` Client/AsyncClient.

This module is **private** — only ``client.py`` and ``aio.py`` within
``iol_client`` may import it. It holds the absorption of the v1.0
module-level globals (``_base_url``, ``_user``, ``_password``, ``_token``,
``_token_expires_at``, ``_refresh_token``, ``_client``) into a single
``@dataclass(slots=True)`` instance that each ``Client`` / ``AsyncClient``
owns and mutates per-instance.

Why NOT ``frozen=True``: the OAuth flow mutates ``token``, ``refresh_token``
and ``token_expires_at`` on every refresh/login; a frozen dataclass would
force ``replace()`` allocations on every refresh and break the in-place
mutation semantics that ``Client._refresh()`` / ``_ensure_token`` rely on.

Why ``slots=True``: prevents accidental attribute typos in the (numerous)
``self._state.<field>`` write sites scattered through ``client.py`` and
``aio.py`` (a misspelling on a non-slots dataclass would silently create a
new attribute and the production read would never see the update).

The ``token_lock`` field is consumed by ``AsyncClient`` only; the sync
``Client`` never touches it. It is created lazily on first async use (NOT
in ``__init__``) so that the lock is bound to whatever event loop is
running when authentication first happens (research Pitfall #6).

The ``refresh_token`` field stores the OAuth refresh token captured at
login. Phase 6 ``Client.__init__`` does NOT accept it as a kwarg (D-13
preserved). However, the module-level ``configure()`` helper DOES accept
``refresh_token=...`` since Phase 6 D-IOL-10 (Pitfall #3 extension to
the original D-13 contract — see ``client.py::configure`` and
``aio.py::configure``), enabling tests and legacy callers to inject a
seed token symmetrically with ``configure(token=X)``.

``refresh_token`` is also mutated by ``Client.login()`` / ``_refresh()``
internally — server-rotated values overwrite the seeded one only when
the parser returns a non-None value (CR-01 conditional rotation,
covered by Phase 9 Plan 09-01 regression tests for the 4 paths
success-rotates / 401-fallback / preserve-on-omit / rotate-on-provide).
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path

import httpx

__all__ = [
    "DEFAULT_BASE_URL",
    "_REQUEST_TIMEOUT",
    "_TOKEN_TTL_BUFFER_SECONDS",
    "_ClientState",
]

DEFAULT_BASE_URL = "https://api.invertironline.com"
_REQUEST_TIMEOUT = 30.0
# Refrescamos un poco antes del vencimiento documentado (15 min).
_TOKEN_TTL_BUFFER_SECONDS = 60


def _env_base_url() -> str:
    """Default-factory for ``base_url``; re-reads env var on each instantiation."""
    return os.getenv("IOL_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _env_user() -> str:
    return os.getenv("IOL_USER", "")


def _env_password() -> str:
    return os.getenv("IOL_PASSWORD", "")


@dataclass(slots=True)
class _ClientState:
    """Per-instance state for an IOL Client / AsyncClient.

    Defaults are computed via ``field(default_factory=...)`` so that env
    vars set AFTER module import (e.g. by ``load_dotenv()`` or test
    monkeypatching of ``os.environ``) take effect on each new instance.
    """

    base_url: str = field(default_factory=_env_base_url)
    username: str = field(default_factory=_env_user)
    password: str = field(default_factory=_env_password)
    token: str | None = None
    token_expires_at: float = 0.0
    refresh_token: str | None = None
    http_client: httpx.Client | httpx.AsyncClient | None = None
    # Lazy-created in AsyncClient._ensure_token on first async use; sync
    # Client never touches this field.
    token_lock: asyncio.Lock | None = None
    # Phase 13 WR-01 fix: lazy lock guarding ``http_client`` lazy-init.
    # Lives on shared ``_state`` (NOT per-instance ``__slots__``) so a
    # ``with_options`` view inherits the SAME lock instance as the parent.
    # Without this, parent and view each held an independent
    # ``asyncio.Lock``, leaving the shared ``http_client`` materialization
    # racy across concurrent first-callers (parent + view on the same loop).
    client_lock: asyncio.Lock | None = None
    # Phase 14 SEC-01 (D-T4 iol-only carve-out): disk-cache path for refresh_token.
    # None disables disk persistence (covers CI=true + operator opt-out path).
    token_cache_path: Path | None = None
