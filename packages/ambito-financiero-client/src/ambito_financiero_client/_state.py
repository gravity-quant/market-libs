"""Per-instance state container for the Ámbito Financiero client (sync + async).

Plan 06-03 — REFAC-02. Absorbs the legacy module-level globals (`_base_url`,
`_user_agent`, `_client`) into a `@dataclass(slots=True) _ClientState` so the
sync `Client` and async `AsyncClient` skeleton classes can each hold their own
isolated state instead of mutating module-level globals (CONTEXT.md D-13/D-14
+ RESEARCH.md Pattern 2).

NOT frozen by design: the `http_client` field is mutated lazily on first call
and zeroed on `close()`/`aclose()`. For cross-package consistency we keep the
"mutable dataclass with lazy http_client" shape uniform with iol/higyrus/matriz
even though ambito has no token to refresh.

**Ambito-specific divergence (B7, locked in by Plan 06-03):** the dataclass
deliberately omits the `token_lock` field that iol/higyrus/matriz use to
serialize token refresh in their async path. Ambito has no auth and no token
refresh race condition; the asyncio.Lock pattern from PATTERNS.md Section 7
is unnecessary here. The `AsyncClient._ensure_http_client` method lazy-creates
the underlying `httpx.AsyncClient` without locking — see its docstring for the
acceptable-leak rationale (T-06-13).

Defaults are read via `field(default_factory=...)` so env vars set AFTER import
(typical in tests via `os.environ[...] = ...` before constructing `Client()`)
are still honored.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx

# La API responde 403 con UA tipo `python-httpx/...`; usamos uno de browser.
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _env_base_url() -> str:
    return os.getenv("AMBITO_BASE_URL", "https://mercados.ambito.com").rstrip("/")


def _env_user_agent() -> str:
    return _DEFAULT_USER_AGENT


@dataclass(slots=True)
class _ClientState:
    """Per-instance state for the ambito Client / AsyncClient.

    Mutable on purpose (`http_client` is lazy-created on first call and
    cleared on `close()`/`aclose()`). NOT frozen.

    Ambito has NO `token_lock` field — no auth means no refresh race; the
    AsyncClient creates its httpx.AsyncClient without serialization. This is
    the deliberate B7 divergence vs iol/higyrus/matriz; see module docstring
    and `aio.AsyncClient._ensure_http_client`.
    """

    base_url: str = field(default_factory=_env_base_url)
    user_agent: str = field(default_factory=_env_user_agent)
    http_client: httpx.Client | httpx.AsyncClient | None = None
