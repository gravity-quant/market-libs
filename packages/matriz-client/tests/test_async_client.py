"""Async-mirror tests for ``matriz_client.aio.AsyncClient.with_options``.

Phase 13 ERG-01 per-package mocked tests (6 tests) — mirror of the sync
``test_client.py::test_with_options_*`` set, plus the matriz-specific
TokenStore-sharing test (D-T2 async mirror).

Other async behaviors live in ``test_async_auth.py`` /
``test_async_queries.py`` / ``test_async_mutations.py`` (Phase 10).
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

import matriz_client
from matriz_client import aio


async def test_with_options_aclose_is_noop(httpx_mock: HTTPXMock) -> None:
    """Phase 13 D-V1 async mirror: view.aclose() MUST NOT close parent's http_client.

    Anti-Pitfall 13 + D-T2: view shares ``_state.http_client`` and
    ``_state.token_store`` with the parent. ``view.aclose()`` is a no-op so
    the parent's pool + cached token + 3-way TokenStore primitive stay intact.
    """
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": []},
    )
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    await client.get_segments()
    parent_http = client._state.http_client
    assert parent_http is not None
    assert client._state.token == "test-token"

    view = client.with_options(max_retries=5)
    await view.aclose()  # MUST be no-op
    assert client._state.http_client is parent_http
    assert client._state.http_client is not None  # parent's pool still open
    assert client._state.token == "test-token"

    await client.aclose()  # cleanup parent's pool


async def test_with_options_aexit_is_noop(httpx_mock: HTTPXMock) -> None:
    """``async with view:`` exits without tearing down parent's http_client."""
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": []},
    )
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    await client.get_segments()
    parent_http = client._state.http_client
    assert parent_http is not None

    view = client.with_options(max_retries=5)
    async with view:
        pass  # exit triggers __aexit__ → aclose() → no-op guard

    assert client._state.http_client is parent_http
    assert client._state.http_client is not None
    assert client._state.token == "test-token"

    await client.aclose()


async def test_with_options_chaining_inner_wins_local_async() -> None:
    """D-V2 async mirror: chaining inner wins."""
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    view = client.with_options(max_retries=5).with_options(max_retries=10)
    assert view._max_retries == 10
    assert client._max_retries == 2
    assert view._state is client._state


async def test_with_options_async_repr_shows_view_prefix() -> None:
    """Async view ``__repr__`` is prefixed with ``"view of "``. D-18 redaction preserved."""
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="SECRET-PASSWORD-DO-NOT-LEAK",
        token="SECRET-TOKEN-DO-NOT-LEAK",
        token_expires_at=9_999_999_999.0,
    )
    view = client.with_options(max_retries=5)
    assert repr(view).startswith("view of AsyncClient(")
    assert not repr(client).startswith("view of ")
    assert "SECRET-PASSWORD-DO-NOT-LEAK" not in repr(view)
    assert "SECRET-TOKEN-DO-NOT-LEAK" not in repr(view)


async def test_with_options_async_invalid_max_retries_raises_value_error() -> None:
    """WR-06 carry-forward async mirror: invalid ``max_retries`` raises ValueError."""
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=-1)
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=True)
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=1.5)  # type: ignore[arg-type]


async def test_with_options_async_view_shares_token_store_3way_primitive(
    httpx_mock: HTTPXMock,
) -> None:
    """D-T2 async mirror: view shares ``_state.token_store`` (Phase 10 3-way primitive).

    The async path lazily builds the TokenStore inside the per-loop
    asyncio.Lock acquired by ``TokenStore.get_async()``. The view
    inherits the SAME ``_state.token_store`` instance — the 3-way
    concurrency primitive is preserved unchanged.

    NOTE: ``matriz_client._aensure_token`` needs the sync ``Client``'s
    ``_state.http_client`` for ``MatrizRefresh`` (which runs inside
    ``asyncio.to_thread``). The conftest fixture seeds the sync default
    Client via ``matriz_client.configure``; we ensure that sync HTTP
    client is built before triggering the async refresh.
    """
    # Use the module-level default singletons so the sync HTTP client used by
    # MatrizRefresh inside asyncio.to_thread is pre-built by the autouse
    # _configure_sync fixture; conftest already seeded credentials.
    sync_default = matriz_client._get_default()
    sync_default._ensure_http_client()

    client = aio._get_default()
    # Force first _aensure_token in parent so token_store gets built.
    client._state.token = None
    client._state.token_expires_at = 0.0
    client._state.token_store = None
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "first-token-async"},
    )
    await client._aensure_token()
    parent_store = client._state.token_store
    assert parent_store is not None, "parent's _aensure_token did not build token_store"

    view = client.with_options(max_retries=5)
    assert view._state.token_store is parent_store, (
        "async view must SHARE _state.token_store (Phase 10 3-way primitive) — "
        "D-T2 violation if the view holds a separate instance."
    )
    assert view._state is client._state
