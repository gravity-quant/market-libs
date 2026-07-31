"""Per-instance state for ``market-data-client`` Client/AsyncClient.

This module is **private** — only ``client.py`` and ``aio.py`` within
``market_data_client`` may import it. It holds the per-instance state that
each ``Client`` / ``AsyncClient`` owns and mutates: the Auth0
client-credentials inputs (``client_id``, ``client_secret``, ``audience``,
``auth0_token_url``), the cached bearer ``token`` + ``token_expires_at``, the
persistent ``http_client``, and the lazy asyncio locks.

Why NOT ``frozen=True``: the Auth0 client-credentials flow mutates ``token``
and ``token_expires_at`` on every refresh; a frozen dataclass would force
``replace()`` allocations on every refresh and break the in-place mutation
semantics that the downstream ``_ensure_token`` relies on.

Why ``slots=True``: prevents accidental attribute typos in the (numerous)
``self._state.<field>`` write sites scattered through ``client.py`` and
``aio.py`` (a misspelling on a non-slots dataclass would silently create a
new attribute and the production read would never see the update).

The ``token_lock`` field is consumed by ``AsyncClient`` only; the sync
``Client`` never touches it. It is created lazily on first async use (NOT
in ``__init__``) so that the lock is bound to whatever event loop is
running when authentication first happens (Auth0 refresh Pitfall).

Auth0 delta vs iol: there is no ``username``/``password``/``refresh_token``
disk cache — the ``client_credentials`` grant is machine-to-machine and
re-authenticates by re-posting the client credentials; ``expires_in`` drives
the TTL, falling back to ``_TOKEN_TTL_FALLBACK_SECONDS`` when the token
response omits it.
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
    "_TOKEN_TTL_FALLBACK_SECONDS",
    "_ClientState",
]

DEFAULT_BASE_URL = "https://market-data-develop.bbsa.com.ar/api"
_REQUEST_TIMEOUT = 30.0
# Refrescamos un poco antes del vencimiento reportado por Auth0 (``expires_in``).
_TOKEN_TTL_BUFFER_SECONDS = 60
# TTL usado sólo cuando la respuesta de Auth0 no incluye ``expires_in``.
_TOKEN_TTL_FALLBACK_SECONDS = 3600


def _env_base_url() -> str:
    """Default-factory for ``base_url``; re-reads env var on each instantiation."""
    return os.getenv("MARKET_DATA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _env_client_id() -> str:
    return os.getenv("MARKET_DATA_CLIENT_ID", "")


def _env_client_secret() -> str:
    return os.getenv("MARKET_DATA_CLIENT_SECRET", "")


def _env_audience() -> str:
    return os.getenv("MARKET_DATA_AUDIENCE", "")


def _env_auth0_token_url() -> str:
    return os.getenv("MARKET_DATA_AUTH0_TOKEN_URL", "")


@dataclass(slots=True)
class _ClientState:
    """Per-instance state for a market-data Client / AsyncClient.

    Defaults are computed via ``field(default_factory=...)`` so that env
    vars set AFTER module import (e.g. by ``load_dotenv()`` or test
    monkeypatching of ``os.environ``) take effect on each new instance.
    """

    base_url: str = field(default_factory=_env_base_url)
    client_id: str = field(default_factory=_env_client_id)
    client_secret: str = field(default_factory=_env_client_secret)
    audience: str = field(default_factory=_env_audience)
    auth0_token_url: str = field(default_factory=_env_auth0_token_url)
    token: str | None = None
    token_expires_at: float = 0.0
    http_client: httpx.Client | httpx.AsyncClient | None = None
    # Lazy-created in AsyncClient._ensure_token on first async use; sync
    # Client never touches this field.
    token_lock: asyncio.Lock | None = None
    # Lazy lock guarding ``http_client`` lazy-init. Lives on shared ``_state``
    # so a ``with_options`` view inherits the SAME lock instance as the parent.
    client_lock: asyncio.Lock | None = None
