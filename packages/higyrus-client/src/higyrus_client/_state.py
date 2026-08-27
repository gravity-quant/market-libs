"""Per-instance state for higyrus-client (sync + async).

Phase 06 Plan 05 — REFAC-02 higyrus. Absorbs the module-level globals
(``_base_url``, ``_client_id``, ``_user``, ``_password``, ``_token``,
``_token_ts``, ``_client``) currently held inside
``higyrus_client.client`` and ``higyrus_client.aio`` into a single mutable
dataclass so a ``Client`` / ``AsyncClient`` instance can carry its own
state.

The dataclass is ``slots=True`` (no ``__dict__`` per instance — typo-safe)
but **not** ``frozen=True`` because ``token``, ``token_expires_at`` and
``http_client`` mutate during normal operation (login refresh + lazy
http-client creation).

**Cross-pkg consistency rename — ``_token_ts`` → ``token_expires_at``:**
the legacy higyrus globals stored a "timestamp since last login"
(``time.time()`` at login completion) and computed expiry as
``(now - _token_ts) < _TOKEN_TTL_SECONDS``. The new field stores the
absolute epoch at which the token expires
(``time.time() + _TOKEN_TTL_SECONDS`` at login completion) and the
freshness check becomes ``time.time() < token_expires_at``. Test fixtures
that previously monkeypatched ``_token_ts = 9_999_999_999.0`` continue to
work after migration to ``configure(token_expires_at=9_999_999_999.0)``
because 9.99e9 is already a valid absolute epoch (year 2286). The PEP 562
shim in ``client.py`` and ``aio.py`` exposes ``_token_ts`` as a read-only
alias of ``state.token_expires_at`` for backwards-compatibility.

Fields:

- ``base_url``: from ``HIGYRUS_BASE_URL`` (rstripped of trailing ``/``)
- ``client_id``: from ``HIGYRUS_CLIENT_ID`` (tenant identifier, not secret)
- ``username``: from ``HIGYRUS_USER``
- ``password``: from ``HIGYRUS_PASSWORD``
- ``strict_decode``: Phase 29 D-03 decode mode. ``False`` (observable —
  a divergence is reported and the policy default substituted) or ``True``
  (strict — a ``missing`` / ``type`` / ``non_dict`` divergence raises
  ``HigyrusDecodeError``). Never env-backed.
- ``token``: cached Bearer token, ``None`` until first login
- ``token_expires_at``: absolute epoch when ``token`` becomes stale
- ``http_client``: lazy ``httpx.Client`` / ``httpx.AsyncClient``.
- ``token_lock``: lazy ``asyncio.Lock`` for async double-checked locking
  in ``aio.py``; ``None`` for sync ``Client``.

The module is private — leading underscore in filename AND class name.
NOT re-exported from ``__init__.py``.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field

import httpx

__all__ = [
    "_REQUEST_TIMEOUT",
    "_TOKEN_TTL_SECONDS",
    "_ClientState",
]

# Constants absorbed from higyrus_client.client / higyrus_client.aio.
# Higyrus tokens are valid for ~24h; refresh at 23h to leave a 1h buffer.
_TOKEN_TTL_SECONDS = 23 * 60 * 60
_REQUEST_TIMEOUT = 30.0


def _env_base_url() -> str:
    return os.getenv("HIGYRUS_BASE_URL", "").rstrip("/")


def _env_client_id() -> str:
    return os.getenv("HIGYRUS_CLIENT_ID", "")


def _env_user() -> str:
    return os.getenv("HIGYRUS_USER", "")


def _env_password() -> str:
    return os.getenv("HIGYRUS_PASSWORD", "")


@dataclass(slots=True)
class _ClientState:
    """Mutable per-instance state for ``Client`` / ``AsyncClient``.

    Defaults come from env vars via ``field(default_factory=...)`` so env
    changes after import (e.g., via ``configure()`` or a late-loaded
    ``.env``) are visible to instances constructed afterwards.
    """

    base_url: str = field(default_factory=_env_base_url)
    client_id: str = field(default_factory=_env_client_id)
    username: str = field(default_factory=_env_user)
    password: str = field(default_factory=_env_password)
    # Phase 29 D-03 — decode mode carrier. Deliberately a plain ``bool``
    # default and NOT a ``field(default_factory=_env_...)``: the strict-decode
    # flag must never be readable from an environment variable, and must never
    # live in a module-level global. The only carriers are this field plus the
    # ``_decode.STRICT_DECODE`` ContextVar that ``_request`` binds from it.
    # Like ``market_data_client``'s ``mutating_allowed`` (D-14), it lives ONLY
    # on the shared ``_ClientState`` — never in a ``Client.__slots__`` — so a
    # ``with_options`` view inherits the parent's mode and sees the parent's
    # later mutations.
    strict_decode: bool = False
    token: str | None = None
    token_expires_at: float = 0.0
    # Lazy: created on first ``_ensure_http_client()`` call. Holds either
    # ``httpx.Client`` (sync) or ``httpx.AsyncClient`` (async).
    http_client: httpx.Client | httpx.AsyncClient | None = None
    # Lazy: created on first async ``_ensure_token()`` call inside an
    # event loop, so we don't bind the lock to a particular loop at import
    # time. Always ``None`` for the sync ``Client``.
    token_lock: asyncio.Lock | None = None
    # Phase 13 WR-01 fix: lazy lock guarding ``http_client`` lazy-init.
    # Lives on shared ``_state`` (NOT per-instance ``__slots__``) so a
    # ``with_options`` view inherits the SAME lock instance as the parent.
    # Without this, parent and view each held an independent
    # ``asyncio.Lock``, leaving the shared ``http_client`` materialization
    # racy across concurrent first-callers (parent + view on the same loop).
    client_lock: asyncio.Lock | None = None
