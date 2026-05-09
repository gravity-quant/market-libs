"""Smoke tests del cliente asincrónico de Ámbito Financiero (submódulo aio)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

from ambito_financiero_client import (
    AmbitoFinancieroAuthError,
    AmbitoFinancieroNoDataError,
    aio,
)


async def test_async_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=401, text="unauthorized")
    with pytest.raises(AmbitoFinancieroAuthError):
        await aio._request("GET", "/anything")


async def test_async_get_dollar_banco_nacion_devuelve_venta(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-07/2026-04-07",
        json=[["Fecha", "Compra", "Venta"], ["07/04/2026", "1365,00", "1415,00"]],
    )
    assert await aio.get_dollar_banco_nacion(dt.date(2026, 4, 7)) == 1415.0


async def test_async_get_dollar_banco_nacion_sin_datos(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-04/2026-04-04",
        json=[["Fecha", "Compra", "Venta"]],
    )
    with pytest.raises(AmbitoFinancieroNoDataError):
        await aio.get_dollar_banco_nacion(dt.date(2026, 4, 4))
