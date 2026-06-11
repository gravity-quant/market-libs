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

The ``refresh_token`` and ``account_id`` fields are forward-declared for
schema consistency across packages (RESEARCH.md Per-Package Divergence
Matrix). Phase 6 ``Client.__init__`` does NOT accept them as kwargs
(D-13). ``refresh_token`` is mutated by ``Client.login()`` / ``_refresh()``
internally; ``account_id`` is populated by Phase 9 BUG-04.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field

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
    # Forward-declared for Phase 9 BUG-04 (multi-account iteration). Not
    # populated in Phase 6 but kept in the schema for cross-package shape
    # consistency with higyrus.
    account_id: str | None = None
    http_client: httpx.Client | httpx.AsyncClient | None = None
    # Lazy-created in AsyncClient._ensure_token on first async use; sync
    # Client never touches this field.
    token_lock: asyncio.Lock | None = None
