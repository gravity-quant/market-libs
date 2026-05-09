"""Smoke tests del cliente asincrónico de Higyrus (submódulo aio)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

from higyrus_client import (
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
