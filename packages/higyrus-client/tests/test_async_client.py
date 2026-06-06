"""Smoke tests del cliente asincrónico de Higyrus (submódulo aio)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

from higyrus_client import (
    HigyrusAPIError,
    HigyrusAuthError,
    HigyrusAuthorizationError,
    aio,
)


async def test_async_login_obtiene_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/login",
        method="POST",
        json={"username": "u", "token": "tok-async"},
    )
    assert await aio.login() == "tok-async"


async def test_async_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
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
