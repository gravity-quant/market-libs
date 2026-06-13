"""Smoke tests del cliente sincrónico de Higyrus (API a nivel módulo)."""

from __future__ import annotations

import datetime as dt
import re

import pytest
from pytest_httpx import HTTPXMock

import higyrus_client
from higyrus_client import (
    Cuenta,
    HigyrusAPIError,
    HigyrusAuthError,
    HigyrusAuthorizationError,
    HigyrusRateLimitError,
    Movimiento,
    Posicion,
    PosicionValuada,
)


def test_login_obtiene_y_cachea_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/login",
        method="POST",
        json={"username": "u", "token": "tok-123"},
    )
    assert higyrus_client.login() == "tok-123"
    assert higyrus_client.client._token == "tok-123"


def test_login_sin_token_levanta_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/login",
        method="POST",
        json={"username": "u"},
    )
    with pytest.raises(HigyrusAuthError):
        higyrus_client.login()


def test_login_credenciales_rechazadas(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/login",
        method="POST",
        status_code=401,
        json={
            "timestamp": "2026-04-24T12:00:00Z",
            "errors": [{"title": "auth", "detail": "bad"}],
        },
    )
    with pytest.raises(HigyrusAuthError) as exc_info:
        higyrus_client.login()
    assert exc_info.value.status_code == 401
    assert exc_info.value.errors == [{"title": "auth", "detail": "bad"}]
    assert exc_info.value.timestamp == "2026-04-24T12:00:00Z"


def test_login_falla_si_falta_base_url() -> None:
    # Phase 6 Plan 05 (Pitfall #4): el legacy monkeypatch a
    # higyrus_client.client._base_url=`""` ya no llega al state desde el
    # refactor. Usamos configure(base_url="") que es la vía soportada.
    higyrus_client.configure(base_url="")
    with pytest.raises(HigyrusAuthError) as exc_info:
        higyrus_client.login()
    assert exc_info.value.status_code == 0


def test_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    """Phase 8 D-02: 401 → re-auth-once (login) → 401 still raises HigyrusAuthError.

    The shell ``_request()`` catches HigyrusAuthError on the initial response,
    clears the cached token, re-authenticates via ``_ensure_token()`` (which
    calls ``login()``), then retries the request once. If the retry also yields
    401, HigyrusAuthError propagates (Pitfall 1: NO infinite loop).
    """
    httpx_mock.add_response(status_code=401, json={})
    httpx_mock.add_response(
        url="https://api.test/api/login",
        method="POST",
        json={"token": "FRESH"},
    )
    httpx_mock.add_response(status_code=401, json={})
    with pytest.raises(HigyrusAuthError):
        higyrus_client.client._request("GET", "/api/health")


def test_request_propaga_authorization_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=403, json={})
    with pytest.raises(HigyrusAuthorizationError):
        higyrus_client.client._request("GET", "/api/health")


def test_request_propaga_rate_limit(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=429, json={})
    with pytest.raises(HigyrusRateLimitError):
        higyrus_client.client._request("GET", "/api/health")


def test_get_health(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/health",
        json={"status": "ok"},
    )
    assert higyrus_client.get_health() == {"status": "ok"}


def test_get_listado_cuentas_devuelve_modelos(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        json=[
            {
                "id": "c1",
                "tipo": "comitente",
                "denominacion": "Cliente 1",
                "estado": "alta",
            }
        ],
    )
    cuentas = higyrus_client.get_listado_cuentas(estado="alta")
    assert len(cuentas) == 1
    assert cuentas[0].id == "c1"
    assert cuentas[0].denominacion == "Cliente 1"
    # Campos no presentes caen al default seguro de SafeModel.
    assert cuentas[0].alias == ""
    assert cuentas[0].domicilios == []


def test_get_listado_cuentas_204_devuelve_lista_vacia(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=204)
    assert higyrus_client.get_listado_cuentas() == []


def test_get_movimientos_serializa_fechas_dd_mm_yyyy(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/123/movimientos?fechaDesde=01%2F01%2F2026&fechaHasta=31%2F01%2F2026",
        json=[],
    )
    movs = higyrus_client.get_movimientos(
        id_cuenta="123",
        fecha_desde=dt.date(2026, 1, 1),
        fecha_hasta=dt.date(2026, 1, 31),
    )
    assert movs == []


def test_get_posiciones_envia_booleano_capitalizado(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/123/posiciones?fecha=15%2F04%2F2026&incluirParking=True",
        json=[],
    )
    posiciones = higyrus_client.get_posiciones(
        id_cuenta="123",
        fecha=dt.date(2026, 4, 15),
        incluir_parking=True,
    )
    assert posiciones == []


# ------ Verified live (Phase 4) ------


def test_get_listado_cuentas_url_con_estado_alta(httpx_mock: HTTPXMock) -> None:
    """Phase 4: locking URL exacta de get_listado_cuentas con estado=alta (HIGY-02)."""
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
        method="GET",
        json=[{"id": "CTA-001", "titular": "<x>", "denominacion": "<y>"}],
    )
    cuentas = higyrus_client.get_listado_cuentas(estado="alta")
    assert isinstance(cuentas, list)
    assert len(cuentas) == 1
    assert isinstance(cuentas[0], Cuenta)
    assert cuentas[0].id == "CTA-001"


def test_safemodel_from_api_typed_defaults() -> None:
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


def test_errors_envelope_parsed_on_4xx(httpx_mock: HTTPXMock) -> None:
    """Phase 4: locking del errors envelope parseado en respuesta 4xx (HIGY-05)."""
    httpx_mock.add_response(
        method="GET",
        status_code=400,
        json={
            "timestamp": "2026-06-06T10:00:00Z",
            "errors": [{"title": "invalid cuenta", "detail": "CTA-INVALID not found"}],
        },
    )
    with pytest.raises(HigyrusAPIError) as exc_info:
        higyrus_client.get_movimientos(
            "CTA-INVALID",
            dt.date(2026, 1, 1),
            dt.date(2026, 1, 1),
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.errors == [{"title": "invalid cuenta", "detail": "CTA-INVALID not found"}]
    assert exc_info.value.timestamp == "2026-06-06T10:00:00Z"


def test_get_movimientos_drop_none_emits_only_required_params(httpx_mock: HTTPXMock) -> None:
    """Phase 4: locking de drop_none — los params None se omiten del query string (HIGY-06 mocked)."""
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/CTA-001/movimientos?fechaDesde=07/05/2026&fechaHasta=06/06/2026",
        method="GET",
        json=[],
    )
    movs = higyrus_client.get_movimientos(
        "CTA-001",
        dt.date(2026, 5, 7),
        dt.date(2026, 6, 6),
    )
    assert movs == []


def test_get_movimientos_empty_path_returns_list(httpx_mock: HTTPXMock) -> None:
    """Phase 4: locking de empty path / 204 returns [] para get_movimientos (HIGY-07)."""
    httpx_mock.add_response(method="GET", status_code=204)
    movs = higyrus_client.get_movimientos(
        "CTA-001",
        dt.date(2026, 1, 1),
        dt.date(2026, 1, 1),
    )
    assert movs == []


def test_get_posiciones_empty_path_returns_list(httpx_mock: HTTPXMock) -> None:
    """Phase 4: locking de empty path / 204 returns [] para get_posiciones (HIGY-07)."""
    httpx_mock.add_response(method="GET", status_code=204)
    posiciones = higyrus_client.get_posiciones("CTA-001", dt.date(2026, 1, 1))
    assert posiciones == []


# ------ Regressions ------


def test_get_health_raises_on_list_payload(httpx_mock: HTTPXMock) -> None:
    """Regression: assert isinstance(raw, dict) reemplazado por HigyrusAPIError tipado (finding F-NN)."""
    httpx_mock.add_response(
        url="https://api.test/api/health",
        method="GET",
        json=["unexpected", "list"],
    )
    with pytest.raises(HigyrusAPIError) as exc_info:
        higyrus_client.get_health()
    assert exc_info.value.status_code == 0
    assert exc_info.value.errors[0]["title"] == "shape mismatch"
    assert "expected dict, got list" in exc_info.value.errors[0]["detail"]


def test_get_movimientos_raises_on_dict_payload(httpx_mock: HTTPXMock) -> None:
    """Regression: assert isinstance(raw, list) reemplazado por HigyrusAPIError tipado (finding F-NN)."""
    httpx_mock.add_response(method="GET", json={"unexpected": "dict"})
    with pytest.raises(HigyrusAPIError) as exc_info:
        higyrus_client.get_movimientos(
            id_cuenta="CTA-001",
            fecha_desde=dt.date(2026, 1, 1),
            fecha_hasta=dt.date(2026, 1, 31),
        )
    assert exc_info.value.status_code == 0
    assert exc_info.value.errors[0]["title"] == "shape mismatch"
    assert "expected list, got dict" in exc_info.value.errors[0]["detail"]


def test_get_listado_cuentas_raises_on_dict_payload(httpx_mock: HTTPXMock) -> None:
    """Regression: assert isinstance(raw, list) reemplazado por HigyrusAPIError tipado (finding F-NN)."""
    httpx_mock.add_response(method="GET", json={"unexpected": "dict"})
    with pytest.raises(HigyrusAPIError) as exc_info:
        higyrus_client.get_listado_cuentas()
    assert exc_info.value.status_code == 0
    assert exc_info.value.errors[0]["title"] == "shape mismatch"
    assert "expected list, got dict" in exc_info.value.errors[0]["detail"]


def test_get_posicion_valuada_raises_on_dict_payload(httpx_mock: HTTPXMock) -> None:
    """Regression: assert isinstance(raw, list) reemplazado por HigyrusAPIError tipado (finding F-NN)."""
    httpx_mock.add_response(method="GET", json={"unexpected": "dict"})
    with pytest.raises(HigyrusAPIError) as exc_info:
        higyrus_client.get_posicion_valuada(
            "CTA-001",
            "propia",
            "detalle",
            dt.date(2026, 1, 1),
            dt.date(2026, 1, 1),
        )
    assert exc_info.value.status_code == 0
    assert exc_info.value.errors[0]["title"] == "shape mismatch"
    assert "expected list, got dict" in exc_info.value.errors[0]["detail"]


def test_get_posiciones_raises_on_dict_payload(httpx_mock: HTTPXMock) -> None:
    """Regression: assert isinstance(raw, list) reemplazado por HigyrusAPIError tipado (finding F-NN)."""
    httpx_mock.add_response(method="GET", json={"unexpected": "dict"})
    with pytest.raises(HigyrusAPIError) as exc_info:
        higyrus_client.get_posiciones("CTA-001", dt.date(2026, 1, 1))
    assert exc_info.value.status_code == 0
    assert exc_info.value.errors[0]["title"] == "shape mismatch"
    assert "expected list, got dict" in exc_info.value.errors[0]["detail"]


# ------ Wire encoding ------


def test_request_preserves_literal_slash_in_query(httpx_mock: HTTPXMock) -> None:
    """Regression F-01..F-06 (plan 04-04): httpx no debe encodar `/` en query — Higyrus IIS rechaza %2F con 400 "formato dd/mm/yyyy"."""
    httpx_mock.add_response(
        url=re.compile(r"^https://api\.test/api/cuentas/5208/movimientos\?.*"),
        method="GET",
        json=[],
    )

    result = higyrus_client.get_movimientos(
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


def test_request_doseq_splits_list_params_into_repeated_keys(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression CR-01 (review 04): `list[str]` params deben re-emitirse como
    claves repetidas (``idCuenta=A&idCuenta=B``), no como literal
    ``['A', 'B']``. Sin ``doseq=True``, ``urlencode`` emite el repr de la lista
    URL-encodeado, que el backend Higyrus rechaza o filtra incorrectamente.
    """
    httpx_mock.add_response(
        url=re.compile(r"^https://api\.test/api/cuentas/listadoCuentas\?.*"),
        method="GET",
        json=[],
    )

    result = higyrus_client.get_listado_cuentas(id_cuenta=["A", "B"])
    assert result == []

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    query_str = requests[0].url.query.decode()
    assert "idCuenta=A" in query_str
    assert "idCuenta=B" in query_str
    # Negative assertion: el repr de la lista NO debe aparecer (ni `[`/`]`
    # URL-encoded ni `'` URL-encoded).
    assert "%5B" not in query_str  # `[`
    assert "%5D" not in query_str  # `]`
    assert "%27" not in query_str  # `'`


def test_login_403_levanta_authorization_error(httpx_mock: HTTPXMock) -> None:
    """Regression WR-01 (review-04): login() con 403 debe levantar
    ``HigyrusAuthorizationError`` (no ``httpx.HTTPStatusError``).
    """
    httpx_mock.add_response(
        url="https://api.test/api/login",
        method="POST",
        status_code=403,
        json={
            "timestamp": "2026-06-08T10:00:00Z",
            "errors": [{"title": "auth", "detail": "forbidden"}],
        },
    )
    with pytest.raises(HigyrusAuthorizationError) as exc_info:
        higyrus_client.login()
    assert exc_info.value.status_code == 403


def test_login_429_levanta_rate_limit(httpx_mock: HTTPXMock) -> None:
    """Regression WR-01 (review-04): login() con 429 debe levantar
    ``HigyrusRateLimitError`` (no ``httpx.HTTPStatusError``).

    Phase 8 D-03: ``build_login_request`` is marked ``idempotent=True`` so 429
    is retry-eable by the RetryTransport. Queue 3 x429 (default
    ``max_retries=2`` → max_attempts=3) so the final exhaust surfaces as
    ``HigyrusRateLimitError`` (D-05 last-response semantics).
    """
    for _ in range(3):
        httpx_mock.add_response(
            url="https://api.test/api/login",
            method="POST",
            status_code=429,
            json={"errors": [{"title": "rate", "detail": "too many"}]},
        )
    with pytest.raises(HigyrusRateLimitError) as exc_info:
        higyrus_client.login()
    assert exc_info.value.status_code == 429


def test_login_500_levanta_api_error(httpx_mock: HTTPXMock) -> None:
    """Regression WR-01 (review-04): login() con 500 debe levantar
    ``HigyrusAPIError`` (no ``httpx.HTTPStatusError``); todos los non-2xx
    se canalizan vía ``_raise_for_response``.

    Phase 8 D-03: ``build_login_request`` is marked ``idempotent=True`` so 5xx
    is retry-eable by the RetryTransport. Queue 3 x500 (default
    ``max_retries=2`` → max_attempts=3) so the final exhaust surfaces as
    ``HigyrusAPIError`` (D-05 last-response semantics).
    """
    for _ in range(3):
        httpx_mock.add_response(
            url="https://api.test/api/login",
            method="POST",
            status_code=500,
            json={"errors": [{"title": "server", "detail": "boom"}]},
        )
    with pytest.raises(HigyrusAPIError) as exc_info:
        higyrus_client.login()
    assert exc_info.value.status_code == 500


def test_get_request_omits_body_and_content_type(httpx_mock: HTTPXMock) -> None:
    """Regression WR-02 (review-04): ``_request`` no debe inyectar body `null`
    en GETs. Sin condicionar el kwarg `json`, httpx envía ``Content-Type:
    application/json`` con body literal ``null`` — wire-format incorrecto
    para endpoints sin body.
    """
    httpx_mock.add_response(method="GET", json={"status": "ok"})
    higyrus_client.get_health()
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    req = requests[0]
    # El body del request debe estar vacío (bytes b"" o None).
    assert not req.content
    # El Content-Type no debe ser application/json (no hay body).
    assert "content-type" not in {k.lower() for k in req.headers}


# ---- WR-02 Phase 8 review fix: body-consume-then-raise on 401 carve-outs ----


def test_401_carve_out_body_consumed_before_raise(httpx_mock: HTTPXMock) -> None:
    """WR-02 regression: 401 re-auth flow consumes body before raising HigyrusAuthError.

    The shell ``_request()`` catches HigyrusAuthError on the initial response,
    runs the re-auth-once flow, retries, and on the second 401 raises
    HigyrusAuthError. WR-02 hardens both raise paths with explicit
    ``resp.read()`` so the body-consume-then-raise contract (Phase 7 D-06) is
    preserved on the carve-out path.

    Mock: 401 (with non-empty body) → login 200 → 401 (with non-empty body).
    Assert HigyrusAuthError raised + exactly 3 wire requests.
    """
    higyrus_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        client_id="tenant",
        token="STALE",
        token_expires_at=9_999_999_999.0,
    )
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
        status_code=401,
        content=b'{"errors":[{"title":"auth"}]}',
    )
    httpx_mock.add_response(
        url="https://api.test/api/login",
        method="POST",
        json={"token": "FRESH"},
    )
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
        status_code=401,
        content=b'{"errors":[{"title":"auth-again"}]}',
    )
    with pytest.raises(HigyrusAuthError):
        higyrus_client.get_listado_cuentas(estado="alta")
    # 3 wire requests = initial 401 + login 200 + retry 401 (D-02 exactly once).
    assert len(httpx_mock.get_requests()) == 3
