"""Skeleton tests for the ambito_financiero_client Client and AsyncClient classes.

Plan 06-03 — REFAC-02 (ambito). Exercises the per-instance state model
(`_ClientState`), the lifecycle protocol (`__enter__`/`__exit__`/`close()`
and `__aenter__`/`__aexit__`/`aclose()`), the PEP 562 read-only `__getattr__`
shim (D-02 ambito row: only `_client` forwarded), the redacted `__repr__`,
the pickle/deepcopy bans (D-23) and the `configure()` carry-forward semantics
(RESEARCH.md Open Q #5).

The AsyncClient mirror tests additionally enforce the B7/B8 divergences:

- B7: `AsyncClient.__slots__ == ("_state",)` — no `_client_lock`. Ambito has
  no auth, no token refresh race; the asyncio.Lock pattern used by
  iol/higyrus/matriz is unnecessary.
- B8: `aio._raise_for_response is client._raise_for_response` — the helper
  is IMPORTED from `client.py`, not duplicated in `aio.py`.
"""

from __future__ import annotations

import copy
import pickle

import pytest

import ambito_financiero_client
from ambito_financiero_client import AsyncClient, Client, aio
from ambito_financiero_client import client as ambito_client_mod

# --- Sync Client lifecycle ---------------------------------------------------


def test_client_context_manager_calls_close() -> None:
    """`with Client() as c: pass` closes the underlying httpx.Client on exit."""
    c = Client()
    with c:
        # Force the http client to materialize so close() has something to do.
        c._ensure_http_client()
        assert c._state.http_client is not None
    assert c._state.http_client is None


def test_close_is_idempotent() -> None:
    """Calling `close()` twice in a row must not raise (T-06-04 mitigation)."""
    c = Client()
    c.close()
    c.close()


def test_repr_contains_no_secrets_redacted() -> None:
    """`__repr__` shows `base_url` literally + the boolean `client_open` flag.

    Ambito has no credentials/tokens; the redaction reduces to the base_url
    plus the client_open boolean (matches the threat model T-06-02 entry).
    """
    c = Client(base_url="https://x")
    rep = repr(c)
    assert "https://x" in rep
    assert "client_open=False" in rep


def test_pickle_raises() -> None:
    """`pickle.dumps(Client())` raises `TypeError` (D-23)."""
    with pytest.raises(TypeError, match="not picklable"):
        pickle.dumps(Client())


def test_deepcopy_raises() -> None:
    """`copy.deepcopy(Client())` raises `TypeError` (D-23)."""
    with pytest.raises(TypeError, match="not deepcopy-safe"):
        copy.deepcopy(Client())


def test_configure_carry_forward() -> None:
    """RESEARCH.md Open Q #5 — `configure()` preserves prior fields when kwarg=None."""
    ambito_financiero_client.configure(base_url="https://a")
    assert ambito_client_mod._get_default()._state.base_url == "https://a"
    ambito_financiero_client.configure(user_agent="UA1")
    # base_url carried forward, user_agent updated.
    assert ambito_client_mod._get_default()._state.base_url == "https://a"
    assert ambito_client_mod._get_default()._state.user_agent == "UA1"


def test_explicit_client_unaffected_by_top_level_configure() -> None:
    """RESEARCH.md Pitfall #2 + CONTEXT.md D-14 — explicit Client() is isolated."""
    c = Client(base_url="https://explicit")
    ambito_financiero_client.configure(base_url="https://other")
    assert c._state.base_url == "https://explicit"


def test_pep_562_shim_forwards_http_client() -> None:
    """`client._client` (PEP 562 shim) resolves to the default Client's http_client."""
    # Force the default Client's http_client to materialize.
    default = ambito_client_mod._get_default()
    default._ensure_http_client()
    assert ambito_client_mod._client is default._state.http_client


def test_pep_562_shim_raises_for_unknown() -> None:
    """T-06-01 mitigation — only `_client` is forwarded; other reads raise."""
    with pytest.raises(AttributeError):
        ambito_client_mod._user  # noqa: B018


# --- AsyncClient lifecycle (mirror) ------------------------------------------


async def test_async_client_context_manager_calls_aclose() -> None:
    """`async with AsyncClient() as c: pass` aclose()s the underlying httpx.AsyncClient."""
    c = AsyncClient()
    async with c:
        # Force the async http client to materialize so aclose() has work.
        c._ensure_http_client()
        assert c._state.http_client is not None
    assert c._state.http_client is None


async def test_aclose_is_idempotent() -> None:
    """Calling `aclose()` twice in a row must not raise (T-06-04 mirror)."""
    c = AsyncClient()
    await c.aclose()
    await c.aclose()


def test_async_pickle_raises() -> None:
    """`pickle.dumps(AsyncClient())` raises `TypeError` (D-23 mirror)."""
    with pytest.raises(TypeError, match="not picklable"):
        pickle.dumps(AsyncClient())


def test_async_deepcopy_raises() -> None:
    """`copy.deepcopy(AsyncClient())` raises `TypeError` (D-23 mirror)."""
    with pytest.raises(TypeError, match="not deepcopy-safe"):
        copy.deepcopy(AsyncClient())


async def test_async_configure_carry_forward() -> None:
    """Mirror of sync carry-forward, exercised on `aio.configure`."""
    aio.configure(base_url="https://a-async")
    assert aio._get_default()._state.base_url == "https://a-async"
    aio.configure(user_agent="UA-async")
    assert aio._get_default()._state.base_url == "https://a-async"
    assert aio._get_default()._state.user_agent == "UA-async"


async def test_async_pep_562_shim_forwards_http_client() -> None:
    """`aio._client` (PEP 562 shim) resolves to the default AsyncClient's http_client."""
    default = aio._get_default()
    default._ensure_http_client()
    assert aio._client is default._state.http_client


def test_async_pep_562_shim_raises_for_unknown() -> None:
    """T-06-01 mirror — only `_client` forwarded in aio; other reads raise."""
    with pytest.raises(AttributeError):
        aio._user  # noqa: B018


def test_async_client_has_no_client_lock_attribute() -> None:
    """B7 enforcement — ambito's AsyncClient diverges from iol/higyrus/matriz.

    No auth, no token refresh race, no lock. The asyncio.Lock pattern from
    PATTERNS.md Section 7 is unnecessary here; the AsyncClient slots tuple
    has no ``_client_lock``. Phase 8 adds ``_max_retries`` to slots (D-15).
    See aio.AsyncClient._ensure_http_client docstring.
    """
    assert "_client_lock" not in AsyncClient.__slots__
    # Phase 8: slots is (_max_retries, _state) — no _client_lock (B7 divergence preserved).
    assert set(AsyncClient.__slots__) == {"_state", "_max_retries"}


def test_aio_imports_raise_for_response_from_client() -> None:
    """B8 enforcement — `_raise_for_response` is SHARED, not duplicated.

    `aio.py` imports the helper from `ambito_financiero_client.client`; the
    identity check below proves it is a real re-export, not a parallel
    definition.
    """
    from ambito_financiero_client.aio import _raise_for_response as async_helper
    from ambito_financiero_client.client import _raise_for_response as sync_helper

    assert sync_helper is async_helper
