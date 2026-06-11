"""Singleton-state dataclass for matriz-client (Phase 6 Plan 06).

Holds credentials, cached token, optional persistent HTTP client and account
context for the MATBA ROFEX Primary API. Used by ``client.Client`` (sync) and
``aio.AsyncClient`` (stub — Phase 10 REFAC-04 grows the REST surface).

Notes:
- ``token_expires_at`` is a unix timestamp; ``_ensure_token`` compares against
  ``time.time()``. Renamed from legacy ``_token_ts`` (D-04).
- ``http_client`` may hold either an ``httpx.Client`` (sync) or an
  ``httpx.AsyncClient`` (stub async). The field is typed as the union of
  both because state is shared across sync/async classes.
- No ``refresh_token`` field: matriz does not implement OAuth refresh; the
  token simply expires after 24h and ``_ensure_token`` calls ``login()`` again.
- No ``token_lock``: matriz has no async REST surface yet (Phase 10).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx
from dotenv import load_dotenv

load_dotenv()

# Constants shared across sync + stub async paths.
_TOKEN_TTL: int = 23 * 60 * 60  # refresh ~1h before the 24h server-side expiry.
_REQUEST_TIMEOUT: float = 30.0


def _default_base_url() -> str:
    return os.getenv("PRIMARY_BASE_URL", "https://api.remarkets.primary.com.ar").rstrip("/")


def _default_username() -> str:
    return os.getenv("PRIMARY_USER", "")


def _default_password() -> str:
    return os.getenv("PRIMARY_PASSWORD", "")


@dataclass(slots=True)
class _ClientState:
    """Mutable singleton-state container for a single ``Client`` instance."""

    base_url: str = field(default_factory=_default_base_url)
    username: str = field(default_factory=_default_username)
    password: str = field(default_factory=_default_password)
    token: str | None = None
    token_expires_at: float = 0.0
    http_client: httpx.Client | httpx.AsyncClient | None = None
    account_id: str | None = None
