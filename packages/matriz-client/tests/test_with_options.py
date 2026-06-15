"""Matriz-specific tests for ``with_options(max_retries=N)`` view shape.

Phase 13 ERG-01 / D-T5 + D-T6 matriz-specific assertions that do NOT live in
the cross-cutting ``verification/test_with_options.py`` (which parametrizes
across the 4 packages):

- **D-T5 — TokenStore isolation:** view's ``max_retries`` is HTTP-only; the
  TokenStore retry cap stays gobernado por the ``Client`` constructor via
  ``state.client_max_retries``. The view's ``_ensure_token`` (sync) and
  ``_aensure_token`` (async) build the TokenStore with the PARENT's value,
  NOT view's override. Verified by spying ``build_token_store``.

- **D-T6 — view's max_attempts honors login():** matriz uses ``login()``
  directly (NOT a ``_send_auth_request`` helper, unlike higyrus). Login is
  ``idempotent=True`` per Phase 8 D-03, so the view's per-call
  ``extensions["max_attempts"]`` cap MUST apply to login wire requests.
  Verified by capturing the outgoing login request and asserting
  ``request.extensions["max_attempts"] == view._max_retries + 1``.

Both sync + async variants per D-V3 surface parity.
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

import matriz_client
from matriz_client import _token_store as ts
from matriz_client import aio
from matriz_client._state import _ClientState
from matriz_client._token_store import TokenStore

# ---------------------------------------------------------------------------
# D-T5 — TokenStore retry cap stays at parent's constructor value
# ---------------------------------------------------------------------------


def test_with_options_does_not_rebind_tokenstore_max_retries(
    monkeypatch: pytest.MonkeyPatch,
    httpx_mock: HTTPXMock,
) -> None:
    """D-T1 / D-T3 sync: view's ``max_retries`` is HTTP-only; the TokenStore
    retry cap stays gobernado por the ``Client`` constructor
    (``state.client_max_retries``).

    Spies ``build_token_store`` and asserts the call from view's
    ``_ensure_token`` carries the PARENT's ``max_retries=2``, NOT view's
    override of 10.
    """
    build_calls: list[int] = []
    orig_build = ts.build_token_store

    def spy(state: _ClientState, *, max_retries: int) -> TokenStore:
        build_calls.append(max_retries)
        return orig_build(state, max_retries=max_retries)

    # Patch the symbol that ``client.py`` imported at module load time.
    monkeypatch.setattr(matriz_client.client, "build_token_store", spy)

    client = matriz_client.Client(
        base_url="https://api.test",
        username="u",
        password="p",
        max_retries=2,
    )
    view = client.with_options(max_retries=10)

    # Force first _ensure_token from view: clear cached token + force
    # state.token_store None so the lazy-init branch fires.
    client._state.token = None
    client._state.token_expires_at = 0.0
    client._state.token_store = None

    # Mock the refresh endpoint. ``MatrizRefresh`` POSTs to /auth/getToken
    # with X-Username/X-Password headers and reads X-Auth-Token from response
    # headers.
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "fresh-from-view"},
    )

    view._ensure_token()

    # Acceptance: the parent's constructor value (2) was used, NOT view's
    # override (10). View's max_retries does NOT leak into the TokenStore.
    assert build_calls == [2], (
        f"expected build_token_store called with max_retries=[2] (parent's "
        f"constructor value), got {build_calls}. View's HTTP-only override "
        f"leaked into the TokenStore retry cap — D-T1 isolation violated."
    )
    assert client._state.token == "fresh-from-view"  # sanity


async def test_with_options_does_not_rebind_tokenstore_max_retries_async(
    monkeypatch: pytest.MonkeyPatch,
    httpx_mock: HTTPXMock,
) -> None:
    """D-T1 / D-T3 async mirror of the sync isolation test.

    The async path in ``aio._aensure_token`` builds the TokenStore inside the
    per-loop asyncio.Lock; spying ``build_token_store`` (imported into aio.py
    at module load) and asserting the call carries parent's value.
    """
    build_calls: list[int] = []
    orig_build = ts.build_token_store

    def spy(state: _ClientState, *, max_retries: int) -> TokenStore:
        build_calls.append(max_retries)
        return orig_build(state, max_retries=max_retries)

    # Patch the symbol that ``aio.py`` imported at module load time.
    monkeypatch.setattr(aio, "build_token_store", spy)

    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="p",
        max_retries=2,
    )
    view = client.with_options(max_retries=10)

    # Force first _aensure_token from view.
    client._state.token = None
    client._state.token_expires_at = 0.0
    client._state.token_store = None

    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "fresh-from-view-async"},
    )

    await view._aensure_token()

    assert build_calls == [2], (
        f"expected build_token_store called with max_retries=[2] (parent's "
        f"constructor value), got {build_calls}. Async view's HTTP-only "
        f"override leaked into the TokenStore retry cap — D-T1 isolation "
        f"violated."
    )
    assert client._state.token == "fresh-from-view-async"  # sanity

    await client.aclose()


# ---------------------------------------------------------------------------
# D-T6 — view's max_attempts extension is propagated to login() wire requests
# ---------------------------------------------------------------------------


def test_with_options_view_login_request_carries_max_attempts_extension(
    httpx_mock: HTTPXMock,
) -> None:
    """D-T6 sync: the matriz ``login()`` shell is one of THREE sites that
    set ``req.extensions["max_attempts"] = self._max_retries + 1``.

    Matriz uses ``login()`` directly (no ``_send_auth_request`` helper —
    differs from higyrus). Login carries ``idempotent=True`` per Phase 8 D-03,
    so a view's per-call cap MUST flow through to login wire requests.

    Asserts the outgoing login request has
    ``extensions["max_attempts"] == 11`` (view._max_retries=10 + 1), NOT 3
    (which is what the parent constructor would have produced: 2 + 1).
    """
    client = matriz_client.Client(
        base_url="https://api.test",
        username="u",
        password="p",
        max_retries=2,
    )
    view = client.with_options(max_retries=10)

    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "tok-from-login"},
    )

    token = view.login()
    assert token == "tok-from-login"

    # Capture the outgoing login request and assert max_attempts extension
    # came from VIEW's override (10+1=11), not parent's (2+1=3).
    requests = httpx_mock.get_requests()
    assert len(requests) == 1, f"expected 1 login request, got {len(requests)}"
    request = requests[0]
    assert request.extensions["max_attempts"] == 11, (
        f"view.login() expected extensions['max_attempts']=11 "
        f"(view._max_retries=10 + 1), got {request.extensions.get('max_attempts')!r}. "
        f"Site 1 of THREE (login()) did not honor view's per-call cap — "
        f"D-T6 violation; CRITICAL merge-gate coverage gap."
    )


async def test_with_options_async_view_login_request_carries_max_attempts_extension(
    httpx_mock: HTTPXMock,
) -> None:
    """D-T6 async: the matriz async ``login()`` shell mirrors sync — Site 1
    of THREE async sites that set ``req.extensions["max_attempts"]``.

    Asserts the outgoing async login request has
    ``extensions["max_attempts"] == 11`` (view._max_retries=10 + 1).
    """
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="p",
        max_retries=2,
    )
    view = client.with_options(max_retries=10)

    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "tok-from-async-login"},
    )

    token = await view.login()
    assert token == "tok-from-async-login"

    requests = httpx_mock.get_requests()
    assert len(requests) == 1, f"expected 1 async login request, got {len(requests)}"
    request = requests[0]
    assert request.extensions["max_attempts"] == 11, (
        f"async view.login() expected extensions['max_attempts']=11 "
        f"(view._max_retries=10 + 1), got {request.extensions.get('max_attempts')!r}. "
        f"Async Site 1 of THREE (async login()) did not honor view's "
        f"per-call cap — D-T6 violation."
    )

    await client.aclose()
