"""Smoke tests del cliente sincrónico de IOL (API a nivel módulo)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

import iol_client
from iol_client import IOLAuthError, IOLRateLimitError


def test_login_obtiene_access_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={"access_token": "tok-iol", "expires_in": 900},
    )
    assert iol_client.login() == "tok-iol"
    assert iol_client.client._token == "tok-iol"


def test_login_falla_sin_credenciales() -> None:
    iol_client.configure(username="", password="")
    with pytest.raises(IOLAuthError):
        iol_client.login()


def test_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=401, text="bad")
    with pytest.raises(IOLAuthError):
        iol_client.client._request("GET", "/api/anything")


def test_request_propaga_rate_limit(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=429, text="too many")
    with pytest.raises(IOLRateLimitError):
        iol_client.client._request("GET", "/api/anything")


def test_get_quote_arma_url_y_params(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 1234.5, "simbolo": "GGAL"},
    )
    quote = iol_client.get_quote("GGAL")
    assert quote["ultimoPrecio"] == 1234.5


def test_get_quote_acepta_mercado_custom(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/nyse/Titulos/KO/Cotizacion?model.mercado=nyse&model.simbolo=KO&model.plazo=t1",
        json={"ultimoPrecio": 60.1},
    )
    quote = iol_client.get_quote("KO", mercado="nyse", plazo="t1")
    assert quote["ultimoPrecio"] == 60.1


def test_get_historical_quotes_arma_path(httpx_mock: HTTPXMock) -> None:
    desde = dt.date(2026, 4, 1)
    hasta = dt.date(2026, 4, 5)
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion/seriehistorica/2026-04-01/2026-04-05/sinAjustar",
        json=[{"fechaHora": "2026-04-04T17:00:00", "ultimoPrecio": 999.9}],
    )
    serie = iol_client.get_historical_quotes("GGAL", desde, hasta)
    assert serie[-1]["ultimoPrecio"] == 999.9


def test_get_instruments_devuelve_payload(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": ["acciones", "cedears"]},
    )
    payload = iol_client.get_instruments()
    assert payload == {"instrumentos": ["acciones", "cedears"]}


def test_get_instruments_by_type_extrae_titulos(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/Cotizaciones/acciones/argentina/Todos",
        json={"titulos": [{"simbolo": "GGAL"}, {"simbolo": "PAMP"}]},
    )
    titulos = iol_client.get_instruments_by_type("acciones")
    assert [t["simbolo"] for t in titulos] == ["GGAL", "PAMP"]
