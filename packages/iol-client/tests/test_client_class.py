"""Tests del esqueleto Client / AsyncClient (Phase 6, REFAC-02 iol-client).

Cubre:

- Lifecycle: context manager sync/async + idempotencia de ``close()`` /
  ``aclose()``.
- Repr: redaction de password, token y refresh_token (D-18 + T-06-05).
- Pickle / deepcopy: ambos raisean TypeError (D-23).
- Carry-forward semantics de ``configure()`` (RESEARCH.md Open Q #5).
- Aislamiento de instancia explícita vs el default Client (Pitfall #2).
- Shim PEP 562: forwarding de ``_token``, ``_token_expires_at``,
  ``_refresh_token`` (Pitfall #3 addendum), ``_client``; AttributeError
  explícito para ``_user``, ``_base_url`` (T-06-01).
- B8 lock-in: ``aio._raise_for_response`` es el mismo objeto que
  ``client._raise_for_response``.

Task 1 (sync) tests are at the top; Task 2 (async + B8 + per-package
guard migration) appends the AsyncClient / aio shim cases at the bottom.
"""

from __future__ import annotations

import asyncio
import copy
import pickle

import pytest

import iol_client
from iol_client import AsyncClient, Client, aio
from iol_client.client import _raise_for_response as _sync_raise

# ----------------------------------------------------------------------
# Sync — Client lifecycle / repr / pickle / deepcopy
# ----------------------------------------------------------------------


def test_client_context_manager() -> None:
    with Client() as c:
        assert isinstance(c, Client)
    # http_client never lazily created → still None after __exit__.
    assert c._state.http_client is None


def test_close_idempotent() -> None:
    c = Client()
    # Force the http_client into existence.
    c._ensure_http_client()
    assert c._state.http_client is not None
    c.close()
    assert c._state.http_client is None
    c.close()  # second call must be a no-op
    assert c._state.http_client is None


def test_repr_redacts_password_and_token() -> None:
    c = Client(
        base_url="https://api.test",
        username="alice",
        password="secret",
        token="tok123",
    )
    # T-06-05: also redact refresh_token.
    c._state.refresh_token = "rt-secret"
    rep = repr(c)
    assert "alice" in rep
    assert "secret" not in rep
    assert "tok123" not in rep
    assert "rt-secret" not in rep
    assert "***" in rep


def test_repr_shows_none_when_token_absent() -> None:
    c = Client(base_url="https://api.test", username="alice", password="")
    rep = repr(c)
    assert "token=None" in rep
    assert "refresh_token=None" in rep


def test_pickle_raises() -> None:
    c = Client()
    with pytest.raises(TypeError, match="not picklable"):
        pickle.dumps(c)


def test_deepcopy_raises() -> None:
    c = Client()
    with pytest.raises(TypeError, match="not deepcopy-safe"):
        copy.deepcopy(c)


# ----------------------------------------------------------------------
# configure() carry-forward + Pitfall #2 isolation
# ----------------------------------------------------------------------


def test_configure_carry_forward() -> None:
    # Carry-forward: each call only overrides the kwargs that are not None.
    iol_client.configure(base_url="https://a.test", username="u1")
    iol_client.configure(token="t1", token_expires_at=9.0e9)
    state = iol_client._get_default()._state
    assert state.base_url == "https://a.test"
    assert state.username == "u1"
    assert state.token == "t1"
    assert state.token_expires_at == 9.0e9


def test_explicit_client_unaffected_by_top_level_configure() -> None:
    """Pitfall #2: a Client(...) built explicitly is NOT touched by configure()."""
    explicit = Client(
        base_url="https://explicit.test",
        username="explicit-user",
        password="explicit-pw",
        token="explicit-tok",
    )
    iol_client.configure(
        base_url="https://default.test",
        username="default-user",
        password="default-pw",
        token="default-tok",
    )
    assert explicit._state.base_url == "https://explicit.test"
    assert explicit._state.token == "explicit-tok"
    assert explicit._state.username == "explicit-user"


# ----------------------------------------------------------------------
# PEP 562 shim — sync
# ----------------------------------------------------------------------


def test_pep_562_shim_forwards_token() -> None:
    iol_client._get_default()._state.token = "tok-shim"
    assert iol_client.client._token == "tok-shim"


def test_pep_562_shim_forwards_token_expires_at() -> None:
    iol_client._get_default()._state.token_expires_at = 1234.5
    assert iol_client.client._token_expires_at == 1234.5


def test_pep_562_shim_forwards_refresh_token() -> None:
    """Pitfall #3 enforcement: ``_refresh_token`` MUST be in the allowlist."""
    iol_client._get_default()._state.refresh_token = "rt-1"
    assert iol_client.client._refresh_token == "rt-1"


def test_pep_562_shim_forwards_http_client() -> None:
    state = iol_client._get_default()._state
    state.http_client = None
    # Lazily create via _ensure_http_client; the shim should forward.
    iol_client._get_default()._ensure_http_client()
    assert iol_client.client._client is iol_client._get_default()._state.http_client
    assert iol_client.client._client is not None


def test_pep_562_shim_raises_for_user() -> None:
    with pytest.raises(AttributeError):
        iol_client.client._user  # noqa: B018 — intentional attribute access


def test_pep_562_shim_raises_for_base_url() -> None:
    with pytest.raises(AttributeError):
        iol_client.client._base_url  # noqa: B018


def test_pep_562_shim_raises_for_unknown() -> None:
    with pytest.raises(AttributeError):
        iol_client.client._totally_unknown  # noqa: B018


# ----------------------------------------------------------------------
# Async — AsyncClient lifecycle / repr / pickle / deepcopy
# ----------------------------------------------------------------------


async def test_async_context_manager() -> None:
    async with AsyncClient() as c:
        assert isinstance(c, AsyncClient)
    assert c._state.http_client is None


async def test_aclose_idempotent() -> None:
    c = AsyncClient()
    await c._ensure_http_client()
    assert c._state.http_client is not None
    await c.aclose()
    assert c._state.http_client is None
    await c.aclose()  # no-op
    assert c._state.http_client is None


def test_async_repr_redacts_password_and_token() -> None:
    c = AsyncClient(
        base_url="https://api.test",
        username="bob",
        password="async-secret",
        token="async-tok",
    )
    c._state.refresh_token = "rt-async-secret"
    rep = repr(c)
    assert "bob" in rep
    assert "async-secret" not in rep
    assert "async-tok" not in rep
    assert "rt-async-secret" not in rep
    assert "***" in rep


def test_async_pickle_raises() -> None:
    c = AsyncClient()
    with pytest.raises(TypeError, match="not picklable"):
        pickle.dumps(c)


def test_async_deepcopy_raises() -> None:
    c = AsyncClient()
    with pytest.raises(TypeError, match="not deepcopy-safe"):
        copy.deepcopy(c)


async def test_async_configure_carry_forward() -> None:
    aio.configure(base_url="https://b.test", username="u2")
    aio.configure(token="t2", token_expires_at=8.0e9)
    state = aio._get_default()._state
    assert state.base_url == "https://b.test"
    assert state.username == "u2"
    assert state.token == "t2"
    assert state.token_expires_at == 8.0e9


async def test_async_explicit_unaffected_by_top_level_configure() -> None:
    explicit = AsyncClient(
        base_url="https://explicit-async.test",
        username="explicit-async-user",
        password="explicit-async-pw",
        token="explicit-async-tok",
    )
    aio.configure(
        base_url="https://default-async.test",
        username="default-async-user",
        password="default-async-pw",
        token="default-async-tok",
    )
    assert explicit._state.base_url == "https://explicit-async.test"
    assert explicit._state.token == "explicit-async-tok"
    assert explicit._state.username == "explicit-async-user"


async def test_async_pep_562_shim_forwards_token_lock() -> None:
    """The aio shim must forward ``_token_lock`` to ``_state.token_lock`` (D-02 aio)."""
    state = aio._get_default()._state
    # Manually create the lock (the production path creates it lazily inside
    # _ensure_token; for the shim test we only need the forwarding assertion).
    state.token_lock = asyncio.Lock()
    assert aio._token_lock is state.token_lock
    assert isinstance(aio._token_lock, asyncio.Lock)


async def test_async_pep_562_shim_forwards_refresh_token() -> None:
    """Pitfall #3 enforcement for aio shim."""
    aio._get_default()._state.refresh_token = "rt-async-1"
    assert aio._refresh_token == "rt-async-1"


def test_async_pep_562_shim_raises_for_user() -> None:
    with pytest.raises(AttributeError):
        aio._user  # noqa: B018


# ----------------------------------------------------------------------
# B8 lock-in: aio imports _raise_for_response from client
# ----------------------------------------------------------------------


def test_aio_imports_raise_for_response_from_client() -> None:
    """B8: ``aio._raise_for_response`` IS ``client._raise_for_response``."""
    from iol_client.aio import _raise_for_response as _async_raise

    assert _async_raise is _sync_raise
