"""Smoke tests del cliente asincrónico de IOL (submódulo aio)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

from iol_client import IOLAuthError, aio
from iol_client.models import Cotizacion, Titulo


async def test_async_login_obtiene_access_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={"access_token": "tok-iol", "expires_in": 900},
    )
    assert await aio.login() == "tok-iol"


async def test_async_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    """Phase 8 D-02 async mirror: 401 → re-auth-once → 401 still raises IOLAuthError."""
    httpx_mock.add_response(status_code=401, text="bad")
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={"access_token": "FRESH", "expires_in": 900},
    )
    httpx_mock.add_response(status_code=401, text="bad again")
    with pytest.raises(IOLAuthError):
        await aio._request("GET", "/api/anything")


async def test_async_get_quote(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 1234.5},
    )
    quote = await aio.get_quote("GGAL")
    assert isinstance(quote, Cotizacion)
    assert quote.ultimoPrecio == 1234.5


async def test_async_get_historical_quotes(httpx_mock: HTTPXMock) -> None:
    desde = dt.date(2026, 4, 1)
    hasta = dt.date(2026, 4, 5)
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion/seriehistorica/2026-04-01/2026-04-05/sinAjustar",
        json=[{"ultimoPrecio": 999.9}],
    )
    serie = await aio.get_historical_quotes("GGAL", desde, hasta)
    assert len(serie) == 1
    assert all(isinstance(row, Cotizacion) for row in serie)
    assert serie[-1].ultimoPrecio == 999.9


async def test_async_get_instruments_by_type(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/Cotizaciones/cedears/argentina/Todos",
        json={"titulos": [{"simbolo": "AAPL"}]},
    )
    titulos = await aio.get_instruments_by_type("cedears")
    assert len(titulos) == 1
    assert isinstance(titulos[0], Titulo)
    assert titulos[0].simbolo == "AAPL"


# ------ Verified live (Phase 3) ------


async def test_async_get_quote_url_exacta_con_query_string(httpx_mock: HTTPXMock) -> None:
    """Phase 3: locking URL exacta de aio.get_quote + ultimoPrecio numeric (IOL-02 + IOL-04).

    Plan 30-01: the assertion on the ``simbolo`` key was **removed**, not
    migrated — same reason as the sync twin: ``simbolo`` is not one of the
    20 keys ``get-quote.json`` records, so it is not a field of
    :class:`Cotizacion`.
    """
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 1234.5, "simbolo": "GGAL"},
    )
    quote = await aio.get_quote("GGAL")
    assert isinstance(quote, Cotizacion)
    assert quote.ultimoPrecio == 1234.5
    assert isinstance(quote.ultimoPrecio, int | float)


async def test_async_get_instruments_by_type_unwraps_titulos(httpx_mock: HTTPXMock) -> None:
    """Phase 3: locking del unwrap data['titulos'] async (IOL-04 envelope).

    Espejo del sync — si el wire deja de emitir 'titulos', el cliente devuelve []
    silenciosamente; drift detectado por probe_field_type_map in-vivo (Pitfall 2).

    Plan 30-02: el unwrap sobrevive intacto como paso raw-dict y lo que sale de
    él son filas :class:`Titulo`; la aserción de forma pasó de nombrar el
    contenedor a nombrar la clase.
    """
    httpx_mock.add_response(
        url="https://api.test/api/v2/Cotizaciones/acciones/argentina/Todos",
        json={"titulos": [{"simbolo": "GGAL"}, {"simbolo": "PAMP"}]},
    )
    titulos = await aio.get_instruments_by_type("acciones")
    assert isinstance(titulos, list)
    assert len(titulos) == 2
    assert all(isinstance(t, Titulo) for t in titulos)
    assert [t.simbolo for t in titulos] == ["GGAL", "PAMP"]


async def test_async_get_historical_quotes_url_dia_gt_12(httpx_mock: HTTPXMock) -> None:
    """Phase 3: locking del formato YYYY-MM-DD del path histórico async (IOL-04).

    Espejo del sync con día > 12 que descarta ambigüedad DD/MM vs MM/DD.
    """
    desde = dt.date(2026, 4, 15)
    hasta = dt.date(2026, 4, 20)
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion/seriehistorica/2026-04-15/2026-04-20/sinAjustar",
        json=[{"fechaHora": "2026-04-18T17:00:00", "ultimoPrecio": 999.9}],
    )
    serie = await aio.get_historical_quotes("GGAL", desde, hasta)
    assert isinstance(serie, list)
    assert len(serie) >= 1
    assert all(isinstance(row, Cotizacion) for row in serie)
    assert serie[-1].ultimoPrecio == 999.9


# ------ Regressions ------


async def test_async_refresh_token_success_path(httpx_mock: HTTPXMock) -> None:
    """Regression: IOL-07 — refresh path async actualiza _token (finding F-NN, mirror del sync).

    El autouse fixture precarga _token; este test lo limpia y setea
    _refresh_token para forzar la rama refresh en _ensure_token dentro del _token_lock.
    Phase 6 migration: writes hit ``_default_async_client._state`` directamente
    porque el shim PEP 562 es read-only (Pitfall #1).
    """
    state = aio._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "refresh-cached"

    # Pitfall 5: match_content bind respuestas a bodies específicos (bytes literal).
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-cached&grant_type=refresh_token",
        json={
            "access_token": "tok-after-refresh",
            "refresh_token": "refresh-rotated",
            "expires_in": 900,
        },
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    await aio.get_instruments("argentina")

    assert aio._token == "tok-after-refresh"
    assert aio._refresh_token == "refresh-rotated"


async def test_async_refresh_fails_falls_back_to_password(httpx_mock: HTTPXMock) -> None:
    """Regression: IOL-07 — refresh inválido cae al password grant async (finding F-NN, mirror)."""
    state = aio._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "refresh-stale"

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-stale&grant_type=refresh_token",
        status_code=401,
        text="invalid_grant",
    )
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"username=u&password=p&grant_type=password",
        json={
            "access_token": "tok-from-password",
            "refresh_token": "refresh-fresh",
            "expires_in": 900,
        },
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    await aio.get_instruments("argentina")

    assert aio._token == "tok-from-password"
    assert aio._refresh_token == "refresh-fresh"


async def test_async_refresh_and_password_both_fail(httpx_mock: HTTPXMock) -> None:
    """Regression: IOL-07 — ambos fallan async → IOLAuthError (finding F-NN, mirror)."""
    state = aio._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "refresh-stale"

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-stale&grant_type=refresh_token",
        status_code=401,
        text="refresh_revoked",
    )
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"username=u&password=p&grant_type=password",
        status_code=401,
        text="bad_creds",
    )

    with pytest.raises(IOLAuthError) as excinfo:
        await aio.get_instruments("argentina")

    assert excinfo.value.status_code == 401


async def test_async_login_captures_refresh_token(httpx_mock: HTTPXMock) -> None:
    """Regression: IOL-07 — async login() captura refresh_token (finding F-NN, mirror)."""
    state = aio._get_default()._state
    state.token = None
    state.refresh_token = None

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={
            "access_token": "tok-x",
            "refresh_token": "refresh-captured",
            "expires_in": 900,
        },
    )

    await aio.login()

    assert aio._token == "tok-x"
    assert aio._refresh_token == "refresh-captured"


async def test_async_login_preserves_cached_refresh_token_when_server_omits(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression CR-01: async login() preserva _refresh_token si el server lo omite.

    Espejo del sync — la asimetría sync↔async ANTES del fix era idéntica: ambas
    superficies reseteaban a ``None``. El fix alinea ``_login_unlocked()`` con
    ``_refresh_unlocked()``: si el payload omite ``refresh_token``, MANTENER el
    cached. Cubre el flujo password-fallback tras refresh inválido.
    """
    state = aio._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "refresh-original"

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        # Server NO incluye refresh_token en el payload.
        json={"access_token": "tok-new", "expires_in": 900},
    )

    await aio.login()

    assert aio._token == "tok-new"
    # Cached refresh_token preservado tras el login (CR-01 fix).
    assert aio._refresh_token == "refresh-original"


# ---- WR-01 Phase 8 review fix: atomic token-clear + ensure-token under lock ----


async def test_concurrent_401_triggers_exactly_one_reauth(httpx_mock: HTTPXMock) -> None:
    """WR-01 invariant lock: N concurrent 401s coalesce into a single re-auth.

    Phase 8 code review WR-01 flagged the token-clear + re-auth path as
    non-atomic: ``self._state.token = None`` happened OUTSIDE the token_lock,
    then ``self._ensure_token()`` was called separately (and re-acquired the
    lock internally). The reviewer warned that this opened a race window
    where two coroutines could race into duplicate logins.

    In practice, the OLD code WAS protected against thundering herd by virtue
    of ``_ensure_token``'s double-checked locking: the first coroutine to
    win the inner lock would do the login, and subsequent coroutines would
    see ``token_is_fresh = True`` and skip. So WR-01 was a SAFETY-CLARITY
    finding rather than an active duplicate-login bug.

    The WR-01 fix makes the contract atomic-and-explicit: token-clear is
    paired with re-auth under a single ``async with lock:`` block, and the
    re-check compares ``state.token == captured_local_token`` so a coroutine
    that arrived AFTER another coroutine already refreshed will skip the
    re-auth and just retry with the new token.

    This test guards the post-fix invariant: 3 concurrent ``get_quote``
    coroutines hit 401 on the initial request → exactly 1 login wire request
    fires + all 3 succeed on retry with the fresh token. Test design uses
    ``match_headers={\"Authorization\": \"Bearer STALE\"}`` to distinguish stale
    vs fresh on the GET endpoint and registers the login response ONCE
    (non-reusable) — if the fix regresses and a second concurrent login
    fires, pytest-httpx raises ``TimeoutException`` with no matching mock.
    """
    import asyncio

    # Reset state to force re-auth from scratch using password grant
    # (no refresh path) for deterministic flow.
    state = aio._get_default()._state
    state.refresh_token = None

    aio.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="STALE",
        token_expires_at=9_999_999_999.0,
    )

    # Stale-token GETs always return 401 (reusable: 3 concurrent tasks).
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        method="GET",
        match_headers={"Authorization": "Bearer STALE"},
        status_code=401,
        text="bad",
        is_reusable=True,
    )
    # EXACTLY ONE login response (NOT reusable). If the race triggers a second
    # login attempt, pytest-httpx will raise TimeoutException since there's no
    # second matching mock.
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={"access_token": "FRESH", "expires_in": 900},
    )
    # Fresh-token GETs always return 200 (reusable: 3 concurrent retries).
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        method="GET",
        match_headers={"Authorization": "Bearer FRESH"},
        json={"ultimoPrecio": 999.9},
        is_reusable=True,
    )

    results = await asyncio.gather(
        aio.get_quote("GGAL"),
        aio.get_quote("GGAL"),
        aio.get_quote("GGAL"),
    )
    assert all(isinstance(r, Cotizacion) for r in results)
    assert all(r.ultimoPrecio == 999.9 for r in results)

    # Assert exactly ONE login wire request (deduplication via token_lock).
    login_requests = [
        r for r in httpx_mock.get_requests() if r.url.path == "/token" and r.method == "POST"
    ]
    assert len(login_requests) == 1, (
        f"WR-01: expected exactly 1 login wire request from 3 concurrent 401s, "
        f"got {len(login_requests)}. The token-clear + re-auth was not atomic — "
        f"two coroutines raced into separate login attempts."
    )


# ----------------------------------------------------------------------
# Phase 13 ERG-01 — async with_options view shape tests + iol-specific
# 401-re-auth-with-view (async). Plan 13-05.
# ----------------------------------------------------------------------


async def test_with_options_aclose_is_noop(httpx_mock: HTTPXMock) -> None:
    """Phase 13 D-V1 async mirror: view.aclose() MUST NOT close parent's http_client."""
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 100.0},
    )
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    await client.get_quote("GGAL")
    parent_http = client._state.http_client
    assert parent_http is not None
    assert client._state.token == "test-token"

    view = client.with_options(max_retries=5)
    await view.aclose()  # MUST be no-op
    assert client._state.http_client is parent_http
    assert client._state.http_client is not None
    assert client._state.token == "test-token"
    # Cleanup parent for next test (autouse fixture handles default too).
    await client.aclose()


async def test_with_options_aexit_is_noop(httpx_mock: HTTPXMock) -> None:
    """``async with view:`` block exits without tearing down parent's http_client."""
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 100.0},
    )
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    await client.get_quote("GGAL")
    parent_http = client._state.http_client
    assert parent_http is not None

    view = client.with_options(max_retries=5)
    async with view:
        pass  # __aexit__ → aclose() → no-op guard

    assert client._state.http_client is parent_http
    assert client._state.http_client is not None
    assert client._state.token == "test-token"
    await client.aclose()


async def test_with_options_chaining_inner_wins_local_async() -> None:
    """D-V2 async mirror: ``c.with_options(5).with_options(10)._max_retries == 10``."""
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
    await client.aclose()


async def test_with_options_async_view_shares_client_lock_with_parent() -> None:
    """Phase 13 WR-01 regression: view shares ``_state.client_lock`` with parent.

    Construct the view BEFORE the parent has materialized its async
    ``client_lock`` (lazy on first ``_ensure_client_lock``). The view's
    first lock acquisition MUST observe the SAME ``asyncio.Lock`` instance
    as the parent's subsequent acquisition — otherwise the two would race
    on the shared ``_state.http_client`` lazy-init (anti-Pitfall 13).
    """
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    # View constructed BEFORE the parent's lock is materialized.
    assert client._state.client_lock is None
    view = client.with_options(max_retries=5)
    # First-call materialization on the view populates the SHARED state slot.
    view._ensure_client_lock()
    assert client._state.client_lock is not None
    # Parent's view of the same shared state surfaces the SAME Lock instance.
    assert view._ensure_client_lock() is client._ensure_client_lock()
    assert view._state.client_lock is client._state.client_lock
    await client.aclose()


async def test_with_options_async_repr_shows_view_prefix() -> None:
    """Async view's ``__repr__`` is prefixed with ``"view of "``. D-18 redaction preserved."""
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="ASYNC-SECRET-PASSWORD-DO-NOT-LEAK",
        token="ASYNC-SECRET-TOKEN-DO-NOT-LEAK",
        token_expires_at=9_999_999_999.0,
    )
    client._state.refresh_token = "ASYNC-SECRET-REFRESH-DO-NOT-LEAK"
    view = client.with_options(max_retries=5)
    assert repr(view).startswith("view of IOLAsyncClient(")
    assert not repr(client).startswith("view of ")
    assert "ASYNC-SECRET-PASSWORD-DO-NOT-LEAK" not in repr(view)
    assert "ASYNC-SECRET-TOKEN-DO-NOT-LEAK" not in repr(view)
    assert "ASYNC-SECRET-REFRESH-DO-NOT-LEAK" not in repr(view)
    await client.aclose()


async def test_with_options_async_invalid_max_retries_raises_value_error() -> None:
    """WR-06 carry-forward (async): invalid ``max_retries`` rejected BEFORE view construction."""
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
    await client.aclose()


async def test_with_options_async_view_401_triggers_reauth_via_shared_refresh_token(
    httpx_mock: HTTPXMock,
) -> None:
    """Phase 13 iol-specific async: view's 401 path uses parent's shared refresh_token.

    Async mirror of the sync test. iol AsyncClient kwargs are
    ``username``/``password`` (NOT ``client_id``/``client_secret``);
    ``refresh_token`` is a ``_state`` field set post-construction (NOT a
    constructor kwarg) — verified at ``packages/iol-client/src/iol_client/aio.py:89-99``.
    """
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="p",
        token="stale-token",
        token_expires_at=9_999_999_999.0,
    )
    client._state.refresh_token = "fresh-refresh"

    view = client.with_options(max_retries=5)

    # 1. GET → 401 (stale token).
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        status_code=401,
        text="unauthorized",
    )
    # 2. POST /token refresh → 200 with new tokens.
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=fresh-refresh&grant_type=refresh_token",
        json={
            "access_token": "new-token",
            "refresh_token": "new-refresh",
            "expires_in": 900,
        },
    )
    # 3. GET → 200 with quote.
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 123.45},
    )

    quote = await view.get_quote("GGAL")

    assert isinstance(quote, Cotizacion)
    assert quote.ultimoPrecio == 123.45
    # Parent's state updated by view's re-auth path — SHARED _state semantics.
    assert client._state.token == "new-token"
    assert client._state.refresh_token == "new-refresh"
    assert view._state is client._state
    # 3 wire requests: initial 401 + /token refresh + retry GET.
    assert len(httpx_mock.get_requests()) == 3
    await client.aclose()
