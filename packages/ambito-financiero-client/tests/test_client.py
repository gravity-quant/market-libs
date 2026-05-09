"""Smoke tests del cliente sincrónico de Ámbito Financiero (API a nivel módulo)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

import ambito_financiero_client as ambito
from ambito_financiero_client import (
    AmbitoFinancieroAuthError,
    AmbitoFinancieroNoDataError,
    AmbitoFinancieroRateLimitError,
)


def test_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=401, text="unauthorized")
    with pytest.raises(AmbitoFinancieroAuthError):
        ambito.client._request("GET", "/anything")


def test_request_propaga_rate_limit(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=429, text="too many")
    with pytest.raises(AmbitoFinancieroRateLimitError):
        ambito.client._request("GET", "/anything")


def test_get_dollar_banco_nacion_devuelve_venta(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-07/2026-04-07",
        json=[["Fecha", "Compra", "Venta"], ["07/04/2026", "1365,00", "1415,00"]],
    )
    assert ambito.get_dollar_banco_nacion(dt.date(2026, 4, 7)) == 1415.0


def test_get_dollar_banco_nacion_parsea_separador_de_miles(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-07/2026-04-07",
        json=[["Fecha", "Compra", "Venta"], ["07/04/2026", "1.365,50", "1.415,75"]],
    )
    assert ambito.get_dollar_banco_nacion(dt.date(2026, 4, 7)) == 1415.75


def test_get_dollar_banco_nacion_sin_datos_levanta(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-04/2026-04-04",
        json=[["Fecha", "Compra", "Venta"]],
    )
    with pytest.raises(AmbitoFinancieroNoDataError):
        ambito.get_dollar_banco_nacion(dt.date(2026, 4, 4))
