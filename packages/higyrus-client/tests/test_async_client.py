"""Smoke tests del cliente asincrónico de Higyrus (submódulo aio)."""

from __future__ import annotations

import datetime as dt
import logging
import re

import pytest
from pytest_httpx import HTTPXMock

from higyrus_client import (
    Cuenta,
    HigyrusAPIError,
    HigyrusAuthError,
    HigyrusAuthorizationError,
    HigyrusRateLimitError,
    Movimiento,
    Posicion,
    PosicionValuada,
    aio,
)
from higyrus_client._logging import attach as _attach_higyrus_logger


async def test_async_login_obtiene_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/login",
        method="POST",
        json={"username": "u", "token": "tok-async"},
    )
    assert await aio.login() == "tok-async"


async def test_async_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    """Phase 8 D-02 async mirror: 401 → re-auth-once (login) → 401 still raises HigyrusAuthError.

    Mirrors the sync test — the async shell catches HigyrusAuthError on the
    initial response, clears the cached token, re-authenticates, then retries
    once. If the retry also yields 401, HigyrusAuthError propagates (Pitfall 1:
    NO infinite loop).
    """
    httpx_mock.add_response(status_code=401, json={})
    httpx_mock.add_response(
        url="https://api.test/api/login",
        method="POST",
        json={"token": "FRESH"},
    )
    httpx_mock.add_response(status_code=401, json={})
    with pytest.raises(HigyrusAuthError):
        await aio._request("GET", "/api/health")


async def test_async_request_propaga_authorization_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=403, json={})
    with pytest.raises(HigyrusAuthorizationError):
        await aio._request("GET", "/api/health")


async def test_async_get_health(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/health",
        json={"status": "ok"},
    )
    assert await aio.get_health() == {"status": "ok"}


async def test_async_get_movimientos_serializa_fechas(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/123/movimientos?fechaDesde=01%2F01%2F2026&fechaHasta=31%2F01%2F2026",
        json=[],
    )
    movs = await aio.get_movimientos(
        id_cuenta="123",
        fecha_desde=dt.date(2026, 1, 1),
        fecha_hasta=dt.date(2026, 1, 31),
    )
    assert movs == []


# ------ Verified live (Phase 4) ------


async def test_async_get_listado_cuentas_url_con_estado_alta(httpx_mock: HTTPXMock) -> None:
    """Phase 4: locking URL exacta de aio.get_listado_cuentas con estado=alta (HIGY-02)."""
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
        method="GET",
        json=[{"id": "CTA-001", "titular": "<x>", "denominacion": "<y>"}],
    )
    cuentas = await aio.get_listado_cuentas(estado="alta")
    assert isinstance(cuentas, list)
    assert len(cuentas) == 1
    assert isinstance(cuentas[0], Cuenta)
    assert cuentas[0].id == "CTA-001"


async def test_async_safemodel_from_api_typed_defaults() -> None:
    """Phase 4: locking de SafeModel.from_api({}) → typed defaults para los 4 modelos top-level (HIGY-03)."""
    c = Cuenta.from_api({})
    m = Movimiento.from_api({})
    p = Posicion.from_api({})
    pv = PosicionValuada.from_api({})

    # Cuenta: str + nested SafeModel + list defaults.
    assert isinstance(c, Cuenta)
    assert c.id == ""
    assert c.titular == ""
    assert c.domicilios == []

    # Movimiento: str + float + list[int] defaults.
    assert isinstance(m, Movimiento)
    assert m.cuenta == ""
    assert m.cantidad == 0.0
    assert m.fechaConcertacion == ""
    assert m.idMovimientos == []

    # Posicion: incluye disponibleAjustado FCI-conditional → safe 0.0 (F-01 EXPECTED).
    assert isinstance(p, Posicion)
    assert p.cuenta == ""
    assert p.disponibleAjustado == 0.0
    assert p.cantidadLiquidada == 0
    assert p.parking == []

    # PosicionValuada: shape de la sweep — todos los floats arrancan en 0.0.
    assert isinstance(pv, PosicionValuada)
    assert pv.cuenta == ""
    assert pv.cantidad == 0.0
    assert pv.valuacion == 0.0


async def test_async_errors_envelope_parsed_on_4xx(httpx_mock: HTTPXMock) -> None:
    """Phase 4: locking del errors envelope parseado en respuesta 4xx — espejo async (HIGY-05)."""
    httpx_mock.add_response(
        method="GET",
        status_code=400,
        json={
            "timestamp": "2026-06-06T10:00:00Z",
            "errors": [{"title": "invalid cuenta", "detail": "CTA-INVALID not found"}],
        },
    )
    with pytest.raises(HigyrusAPIError) as exc_info:
        await aio.get_movimientos(
            "CTA-INVALID",
            dt.date(2026, 1, 1),
            dt.date(2026, 1, 1),
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.errors == [{"title": "invalid cuenta", "detail": "CTA-INVALID not found"}]
    assert exc_info.value.timestamp == "2026-06-06T10:00:00Z"


async def test_async_get_movimientos_drop_none_emits_only_required_params(
    httpx_mock: HTTPXMock,
) -> None:
    """Phase 4: locking de drop_none — los params None se omiten del query string async (HIGY-06 mocked)."""
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/CTA-001/movimientos?fechaDesde=07/05/2026&fechaHasta=06/06/2026",
        method="GET",
        json=[],
    )
    movs = await aio.get_movimientos(
        "CTA-001",
        dt.date(2026, 5, 7),
        dt.date(2026, 6, 6),
    )
    assert movs == []


async def test_async_get_movimientos_empty_path_returns_list(httpx_mock: HTTPXMock) -> None:
    """Phase 4: locking de empty path / 204 returns [] para aio.get_movimientos (HIGY-07)."""
    httpx_mock.add_response(method="GET", status_code=204)
    movs = await aio.get_movimientos(
        "CTA-001",
        dt.date(2026, 1, 1),
        dt.date(2026, 1, 1),
    )
    assert movs == []


async def test_async_get_listado_cuentas_empty_path_returns_list(httpx_mock: HTTPXMock) -> None:
    """Phase 4: locking de empty path / 204 returns [] para aio.get_listado_cuentas (HIGY-07)."""
    httpx_mock.add_response(method="GET", status_code=204)
    cuentas = await aio.get_listado_cuentas()
    assert cuentas == []


async def test_async_get_posiciones_empty_path_returns_list(httpx_mock: HTTPXMock) -> None:
    """Phase 4: locking de empty path / 204 returns [] para aio.get_posiciones (HIGY-07)."""
    httpx_mock.add_response(method="GET", status_code=204)
    posiciones = await aio.get_posiciones("CTA-001", dt.date(2026, 1, 1))
    assert posiciones == []


# ------ Regressions ------


async def test_async_get_health_raises_on_list_payload(httpx_mock: HTTPXMock) -> None:
    """Regression: assert isinstance(raw, dict) reemplazado por HigyrusAPIError tipado (finding F-NN)."""
    httpx_mock.add_response(
        url="https://api.test/api/health",
        method="GET",
        json=["unexpected", "list"],
    )
    with pytest.raises(HigyrusAPIError) as exc_info:
        await aio.get_health()
    assert exc_info.value.status_code == 0
    assert exc_info.value.errors[0]["title"] == "shape mismatch"
    assert "expected dict, got list" in exc_info.value.errors[0]["detail"]


async def test_async_get_movimientos_raises_on_dict_payload(httpx_mock: HTTPXMock) -> None:
    """Regression: assert isinstance(raw, list) reemplazado por HigyrusAPIError tipado (finding F-NN)."""
    httpx_mock.add_response(method="GET", json={"unexpected": "dict"})
    with pytest.raises(HigyrusAPIError) as exc_info:
        await aio.get_movimientos(
            id_cuenta="CTA-001",
            fecha_desde=dt.date(2026, 1, 1),
            fecha_hasta=dt.date(2026, 1, 31),
        )
    assert exc_info.value.status_code == 0
    assert exc_info.value.errors[0]["title"] == "shape mismatch"
    assert "expected list, got dict" in exc_info.value.errors[0]["detail"]


async def test_async_get_listado_cuentas_raises_on_dict_payload(httpx_mock: HTTPXMock) -> None:
    """Regression: assert isinstance(raw, list) reemplazado por HigyrusAPIError tipado (finding F-NN)."""
    httpx_mock.add_response(method="GET", json={"unexpected": "dict"})
    with pytest.raises(HigyrusAPIError) as exc_info:
        await aio.get_listado_cuentas()
    assert exc_info.value.status_code == 0
    assert exc_info.value.errors[0]["title"] == "shape mismatch"
    assert "expected list, got dict" in exc_info.value.errors[0]["detail"]


async def test_async_get_posicion_valuada_raises_on_dict_payload(httpx_mock: HTTPXMock) -> None:
    """Regression: assert isinstance(raw, list) reemplazado por HigyrusAPIError tipado (finding F-NN)."""
    httpx_mock.add_response(method="GET", json={"unexpected": "dict"})
    with pytest.raises(HigyrusAPIError) as exc_info:
        await aio.get_posicion_valuada(
            "CTA-001",
            "propia",
            "detalle",
            dt.date(2026, 1, 1),
            dt.date(2026, 1, 1),
        )
    assert exc_info.value.status_code == 0
    assert exc_info.value.errors[0]["title"] == "shape mismatch"
    assert "expected list, got dict" in exc_info.value.errors[0]["detail"]


async def test_async_get_posiciones_raises_on_dict_payload(httpx_mock: HTTPXMock) -> None:
    """Regression: assert isinstance(raw, list) reemplazado por HigyrusAPIError tipado (finding F-NN)."""
    httpx_mock.add_response(method="GET", json={"unexpected": "dict"})
    with pytest.raises(HigyrusAPIError) as exc_info:
        await aio.get_posiciones("CTA-001", dt.date(2026, 1, 1))
    assert exc_info.value.status_code == 0
    assert exc_info.value.errors[0]["title"] == "shape mismatch"
    assert "expected list, got dict" in exc_info.value.errors[0]["detail"]


# ------ Wire encoding ------


async def test_request_preserves_literal_slash_in_query_async(httpx_mock: HTTPXMock) -> None:
    """Regression F-01..F-06 (plan 04-04): aio._request no debe encodar `/` en query — espejo async."""
    httpx_mock.add_response(
        url=re.compile(r"^https://api\.test/api/cuentas/5208/movimientos\?.*"),
        method="GET",
        json=[],
    )

    result = await aio.get_movimientos(
        "5208",
        fecha_desde=dt.date(2026, 5, 8),
        fecha_hasta=dt.date(2026, 6, 7),
    )
    assert result == []

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    query_str = requests[0].url.query.decode()
    assert "fechaDesde=08/05/2026" in query_str
    assert "fechaHasta=07/06/2026" in query_str
    assert "%2F" not in query_str


async def test_async_request_doseq_splits_list_params_into_repeated_keys(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression CR-01 (review 04): espejo async — `list[str]` params deben
    re-emitirse como claves repetidas (``idCuenta=A&idCuenta=B``).
    """
    httpx_mock.add_response(
        url=re.compile(r"^https://api\.test/api/cuentas/listadoCuentas\?.*"),
        method="GET",
        json=[],
    )

    result = await aio.get_listado_cuentas(id_cuenta=["A", "B"])
    assert result == []

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    query_str = requests[0].url.query.decode()
    assert "idCuenta=A" in query_str
    assert "idCuenta=B" in query_str
    assert "%5B" not in query_str
    assert "%5D" not in query_str
    assert "%27" not in query_str


async def test_async_login_403_levanta_authorization_error(httpx_mock: HTTPXMock) -> None:
    """Regression WR-01 mirror (review-04): aio.login() con 403 debe levantar
    ``HigyrusAuthorizationError`` (no ``httpx.HTTPStatusError``).
    """
    httpx_mock.add_response(
        url="https://api.test/api/login",
        method="POST",
        status_code=403,
        json={"errors": [{"title": "auth", "detail": "forbidden"}]},
    )
    with pytest.raises(HigyrusAuthorizationError) as exc_info:
        await aio.login()
    assert exc_info.value.status_code == 403


async def test_async_login_500_levanta_api_error(httpx_mock: HTTPXMock) -> None:
    """Regression WR-01 mirror (review-04): aio.login() con 500 debe levantar
    ``HigyrusAPIError`` (no ``httpx.HTTPStatusError``).

    Phase 8 D-03: ``build_login_request`` is marked ``idempotent=True`` so 5xx
    is retry-eable by the AsyncRetryTransport. Queue 3 x 500 so the final
    exhaust surfaces as ``HigyrusAPIError`` (D-05 last-response semantics).
    """
    for _ in range(3):
        httpx_mock.add_response(
            url="https://api.test/api/login",
            method="POST",
            status_code=500,
            json={"errors": [{"title": "server", "detail": "boom"}]},
        )
    with pytest.raises(HigyrusAPIError) as exc_info:
        await aio.login()
    assert exc_info.value.status_code == 500


async def test_async_get_request_omits_body_and_content_type(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression WR-02 mirror (review-04): ``aio._request`` no debe inyectar
    body `null` en GETs.
    """
    httpx_mock.add_response(method="GET", json={"status": "ok"})
    await aio.get_health()
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    req = requests[0]
    assert not req.content
    assert "content-type" not in {k.lower() for k in req.headers}


# ---- WR-01 Phase 8 review fix: atomic token-clear + ensure-token under lock ----


async def test_concurrent_401_triggers_exactly_one_reauth(httpx_mock: HTTPXMock) -> None:
    """WR-01 invariant lock: N concurrent 401s coalesce into a single re-auth.

    Mirror of the iol WR-01 regression test. The Phase 8 code review flagged
    higyrus aio._request as having a token-clear + re-auth race window
    structurally identical to iol. In practice the OLD code's double-checked
    locking inside _ensure_token already prevented duplicate logins, but the
    contract was non-atomic. The fix wraps clear + re-auth under a single
    token_lock acquisition with an inner re-check against the captured local
    token, so a coroutine that arrives AFTER another coroutine refreshed
    skips its own re-auth.

    Test: 3 concurrent get_listado_cuentas coroutines hit 401 on the initial
    request → exactly 1 POST /api/login wire request fires + all 3 succeed
    on retry with the fresh token. Distinguishes stale vs fresh via
    match_headers on the GET endpoint; login mock is registered ONCE so the
    test FAILS with TimeoutException if a duplicate login is attempted.
    """
    import asyncio

    aio.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        client_id="tenant",
        token="STALE",
        token_expires_at=9_999_999_999.0,
    )

    # Stale-token GETs always return 401 (reusable: 3 concurrent tasks).
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
        method="GET",
        match_headers={"Authorization": "Bearer STALE"},
        status_code=401,
        text="bad",
        is_reusable=True,
    )
    # EXACTLY ONE login response (NOT reusable) — race triggers TimeoutException.
    httpx_mock.add_response(
        url="https://api.test/api/login",
        method="POST",
        json={"token": "FRESH"},
    )
    # Fresh-token GETs always return 200 (reusable: 3 concurrent retries).
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
        method="GET",
        match_headers={"Authorization": "Bearer FRESH"},
        json=[],
        is_reusable=True,
    )

    results = await asyncio.gather(
        aio.get_listado_cuentas(estado="alta"),
        aio.get_listado_cuentas(estado="alta"),
        aio.get_listado_cuentas(estado="alta"),
    )
    assert all(r == [] for r in results)

    # Assert exactly ONE login wire request (deduplication via token_lock).
    login_requests = [
        r for r in httpx_mock.get_requests() if r.url.path == "/api/login" and r.method == "POST"
    ]
    assert len(login_requests) == 1, (
        f"WR-01: expected exactly 1 login wire request from 3 concurrent 401s, "
        f"got {len(login_requests)}. The token-clear + re-auth was not atomic."
    )


# ------ Phase 13 ERG-01 — with_options(max_retries=N) view shape (async mirror) ------


async def test_with_options_aclose_is_noop(httpx_mock: HTTPXMock) -> None:
    """Phase 13 D-V1 async mirror: view.aclose() MUST NOT close parent's http_client."""
    httpx_mock.add_response(
        url="https://api.test/api/health",
        json={"status": "ok"},
    )
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="p",
        client_id="tenant",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    await client.get_health()
    parent_http = client._state.http_client
    assert parent_http is not None
    assert client._state.token == "test-token"

    view = client.with_options(max_retries=5)
    await view.aclose()  # MUST be no-op
    assert client._state.http_client is parent_http
    assert client._state.http_client is not None
    assert client._state.token == "test-token"
    await client.aclose()  # cleanup parent's pool


async def test_with_options_aexit_is_noop(httpx_mock: HTTPXMock) -> None:
    """``async with view:`` exits without tearing down parent's http_client."""
    httpx_mock.add_response(
        url="https://api.test/api/health",
        json={"status": "ok"},
    )
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="p",
        client_id="tenant",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    await client.get_health()
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
        client_id="tenant",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    view = client.with_options(max_retries=5).with_options(max_retries=10)
    assert view._max_retries == 10
    assert client._max_retries == 2
    assert view._state is client._state


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
        client_id="tenant",
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


async def test_with_options_async_repr_shows_view_prefix() -> None:
    """Async view's ``__repr__`` is prefixed with ``"view of "``. D-18 redaction preserved."""
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="SECRET-PASSWORD-DO-NOT-LEAK",
        client_id="tenant",
        token="SECRET-TOKEN-DO-NOT-LEAK",
        token_expires_at=9_999_999_999.0,
    )
    view = client.with_options(max_retries=5)
    assert repr(view).startswith("view of <higyrus_client.AsyncClient(")
    assert not repr(client).startswith("view of ")
    assert "SECRET-PASSWORD-DO-NOT-LEAK" not in repr(view)
    assert "SECRET-TOKEN-DO-NOT-LEAK" not in repr(view)


async def test_with_options_async_invalid_max_retries_raises_value_error() -> None:
    """WR-06 carry-forward async mirror: invalid ``max_retries`` raises ValueError."""
    client = aio.AsyncClient(
        base_url="https://api.test",
        username="u",
        password="p",
        client_id="tenant",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=-1)
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=True)
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=1.5)  # type: ignore[arg-type]


async def test_with_options_view_async_retry_log_still_redacts_token(
    caplog: pytest.LogCaptureFixture,
    httpx_mock: HTTPXMock,
) -> None:
    """Phase 13 T-13-03-01 async mirror: view's async retry log MUST NOT leak token sentinel.

    Mirror of the sync redaction test. Exercises the AsyncRetryTransport
    retry path through the view's per-call cap; asserts the WARNING records
    do NOT contain the token sentinel anywhere.
    """
    sentinel = "HIGYRUS-TOKEN-SENTINEL-DO-NOT-LEAK"
    _attach_higyrus_logger()
    aio.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        client_id="tenant",
        token=sentinel,
        token_expires_at=9_999_999_999.0,
    )
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/123/movimientos?fechaDesde=01%2F01%2F2024&fechaHasta=31%2F01%2F2024",
        status_code=503,
        is_reusable=True,
    )

    caplog.set_level(logging.DEBUG, logger="higyrus_client")
    client = aio._get_default()
    view = client.with_options(max_retries=2)
    fecha_desde = dt.date(2024, 1, 1)
    fecha_hasta = dt.date(2024, 1, 31)
    with pytest.raises((HigyrusAPIError, HigyrusAuthorizationError, HigyrusRateLimitError)):
        await view.get_movimientos("123", fecha_desde, fecha_hasta)

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_records, (
        "expected >=1 WARNING async retry-attempt record; got zero. View's "
        "async max_attempts did not reach the AsyncRetryTransport."
    )

    for record in caplog.records:
        message = record.getMessage()
        assert sentinel not in message, (
            f"async view retry log leaked token in record.getMessage(): {message!r}"
        )
        if record.args:
            args_str = str(record.args)
            assert sentinel not in args_str, (
                f"async view retry log leaked token in record.args: {args_str!r}"
            )
        for key, value in record.__dict__.items():
            if isinstance(value, str):
                assert sentinel not in value, (
                    f"async view retry log leaked token in record.{key}: {value!r}"
                )
