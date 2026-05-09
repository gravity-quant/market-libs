"""Smoke tests del cliente asincrónico de IOL (submódulo aio)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

from iol_client import IOLAuthError, aio


async def test_async_login_obtiene_access_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={"access_token": "tok-iol", "expires_in": 900},
    )
    assert await aio.login() == "tok-iol"


async def test_async_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=401, text="bad")
    with pytest.raises(IOLAuthError):
        await aio._request("GET", "/api/anything")


async def test_async_get_quote(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 1234.5},
    )
    quote = await aio.get_quote("GGAL")
    assert quote["ultimoPrecio"] == 1234.5


async def test_async_get_historical_quotes(httpx_mock: HTTPXMock) -> None:
    desde = dt.date(2026, 4, 1)
    hasta = dt.date(2026, 4, 5)
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion/seriehistorica/2026-04-01/2026-04-05/sinAjustar",
        json=[{"ultimoPrecio": 999.9}],
    )
    serie = await aio.get_historical_quotes("GGAL", desde, hasta)
    assert serie[-1]["ultimoPrecio"] == 999.9


async def test_async_get_instruments_by_type(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/Cotizaciones/cedears/argentina/Todos",
        json={"titulos": [{"simbolo": "AAPL"}]},
    )
    titulos = await aio.get_instruments_by_type("cedears")
    assert titulos[0]["simbolo"] == "AAPL"
