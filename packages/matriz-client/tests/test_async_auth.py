"""Async auth tests for ``matriz_client.aio`` (Phase 10 Plan 10-02 Task 2).

Covers AsyncClient lifecycle, login, ``_aensure_token`` (TokenStore-backed),
401 re-auth-once flow, and the B8 ``_raise_for_response`` identity lock-in
(Phase 7 D-04 carry-forward).
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from matriz_client import aio
from matriz_client.exceptions import AuthenticationError

# ---------------------------------------------------------------------------
# AA1: login obtains token via X-Auth-Token header
# ---------------------------------------------------------------------------


async def test_async_login_obtiene_x_auth_token_header(httpx_mock: HTTPXMock) -> None:
    """AA1: aio.login() POSTs /auth/getToken; response X-Auth-Token populates _token."""
    state = aio._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "tok-async-aa1"},
    )
    token = await aio.login()
    assert token == "tok-async-aa1"
    # PEP 562 forwarded read.
    assert aio._token == "tok-async-aa1"


# ---------------------------------------------------------------------------
# AA2: AsyncClient is constructible with full kwargs surface
# ---------------------------------------------------------------------------


async def test_async_client_constructible_with_kwargs() -> None:
    """AA2: AsyncClient(base_url, username, password, token, token_expires_at, max_retries, http_client)."""
    c = aio.AsyncClient(
        base_url="https://override.test",
        username="alice",
        password="secret",
        token="seed-token",
        token_expires_at=10_000_000_000.0,
        max_retries=3,
    )
    assert c._state.base_url == "https://override.test"
    assert c._state.username == "alice"
    assert c._state.password == "secret"
    assert c._state.token == "seed-token"
    assert c._state.token_expires_at == 10_000_000_000.0
    assert c._max_retries == 3
    await c.aclose()


# ---------------------------------------------------------------------------
# AA3: async with enters / exits + aclose called automatically
# ---------------------------------------------------------------------------


async def test_async_with_calls_aclose_on_exit() -> None:
    """AA3: async with AsyncClient as c: ...; httpx.AsyncClient is closed."""
    async with aio.AsyncClient(base_url="https://api.test", username="u", password="p") as c:
        # Provision the underlying http_client lazily.
        http = await c._ensure_http_client()
        assert http.is_closed is False
    # After exit, _state.http_client is None (aclose dropped the reference).
    assert c._state.http_client is None


# ---------------------------------------------------------------------------
# AA4: __repr__ redacts password and token
# ---------------------------------------------------------------------------


async def test_repr_redacts_password_and_token() -> None:
    """AA4: __repr__ never contains password or token literals."""
    c = aio.AsyncClient(
        base_url="https://api.test",
        username="op",
        password="super-secret-AA4",
        token="bearer-AA4",
    )
    r = repr(c)
    assert "super-secret-AA4" not in r
    assert "bearer-AA4" not in r
    assert "***" in r
    await c.aclose()


# ---------------------------------------------------------------------------
# AA5: __reduce__ raises TypeError
# ---------------------------------------------------------------------------


async def test_reduce_raises_type_error() -> None:
    """AA5: AsyncClient is not picklable."""
    c = aio.AsyncClient()
    with pytest.raises(TypeError):
        c.__reduce__()
    await c.aclose()


# ---------------------------------------------------------------------------
# AA6: __deepcopy__ raises TypeError
# ---------------------------------------------------------------------------


async def test_deepcopy_raises_type_error() -> None:
    """AA6: AsyncClient is not deepcopy-safe."""
    import copy

    c = aio.AsyncClient()
    with pytest.raises(TypeError):
        copy.deepcopy(c)
    await c.aclose()


# ---------------------------------------------------------------------------
# AA7: 401 re-auth-once flow (D-02 async mirror)
# ---------------------------------------------------------------------------


async def test_401_triggers_exactly_one_reauth(httpx_mock: HTTPXMock) -> None:
    """AA7: 401 → invalidate TokenStore → re-auth via /auth/getToken → retry once.

    Async mirror of Phase 8 D-02 sync re-auth-once flow. Verifies a single
    re-auth attempt happens between the first 401 and the retry.
    """
    state = aio._get_default()._state
    # Force the path that needs to go through _aensure_token+TokenStore by
    # clearing the seeded token and credentials valid.
    state.token = None
    state.token_expires_at = 0.0
    # First /auth/getToken returns initial token.
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "initial-token"},
    )
    # First endpoint call returns 401 (token has been revoked server-side).
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        method="GET",
        status_code=401,
    )
    # Re-auth via /auth/getToken returns fresh token.
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "fresh-token"},
    )
    # Retry of endpoint returns 200 with envelope.
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        method="GET",
        json={"status": "OK", "segments": []},
    )

    segments = await aio.get_segments()
    assert segments == []

    # Verify: 2 auth calls (initial + re-auth) + 2 endpoint calls (401 + retry).
    auth_calls = [r for r in httpx_mock.get_requests() if r.url.path == "/auth/getToken"]
    endpoint_calls = [r for r in httpx_mock.get_requests() if r.url.path == "/rest/segment/all"]
    assert len(auth_calls) == 2, f"expected exactly 2 auth calls; got {len(auth_calls)}"
    assert len(endpoint_calls) == 2, f"expected exactly 2 endpoint calls; got {len(endpoint_calls)}"
    # After the re-auth, the X-Auth-Token header on the retry must be the fresh one.
    assert endpoint_calls[-1].headers.get("X-Auth-Token") == "fresh-token"


# ---------------------------------------------------------------------------
# AA8: 401 followed by 401 raises AuthenticationError
# ---------------------------------------------------------------------------


async def test_401_after_reauth_raises_authentication_error(httpx_mock: HTTPXMock) -> None:
    """AA8: Second 401 (after re-auth attempt) surfaces AuthenticationError."""
    state = aio._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "first-token"},
    )
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        method="GET",
        status_code=401,
    )
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "second-token"},
    )
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        method="GET",
        status_code=401,
    )

    with pytest.raises(AuthenticationError):
        await aio.get_segments()


# ---------------------------------------------------------------------------
# B8 lock-in cross-check (D-04 invariant)
# ---------------------------------------------------------------------------


def test_b8_aio_raise_for_response_lock_in() -> None:
    """B8: aio._raise_for_response is client._raise_for_response is _core.raise_for_response."""
    from matriz_client import _core
    from matriz_client import aio as _aio
    from matriz_client import client as _sync_client

    assert _aio._raise_for_response is _sync_client._raise_for_response
    assert _aio._raise_for_response is _core.raise_for_response


# ---------------------------------------------------------------------------
# PEP 562 shim (legacy read-only attribute forwarding)
# ---------------------------------------------------------------------------


async def test_pep562_forwards_legacy_attribute_reads() -> None:
    """PEP 562: aio._token / aio._base_url / aio._token_expires_at / aio._client read state."""
    state = aio._get_default()._state
    assert aio._token == state.token
    assert aio._base_url == state.base_url
    assert aio._token_expires_at == state.token_expires_at
    # _client forwards to state.http_client (None until first request).
    assert aio._client is state.http_client


async def test_pep562_unknown_attribute_raises_attribute_error() -> None:
    """PEP 562: unknown attribute access surfaces AttributeError per shim contract."""
    with pytest.raises(AttributeError):
        _ = aio._does_not_exist  # type: ignore[attr-defined]
