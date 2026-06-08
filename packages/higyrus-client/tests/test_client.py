"""Smoke tests del cliente sincrónico de Higyrus (API a nivel módulo)."""

from __future__ import annotations

import datetime as dt
import re

import pytest
from pytest_httpx import HTTPXMock

import higyrus_client
from higyrus_client import (
    HigyrusAPIError,
    HigyrusAuthError,
    HigyrusAuthorizationError,
    HigyrusRateLimitError,
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


def test_login_falla_si_falta_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(higyrus_client.client, "_base_url", "")
    with pytest.raises(HigyrusAuthError) as exc_info:
        higyrus_client.login()
    assert exc_info.value.status_code == 0


def test_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
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
