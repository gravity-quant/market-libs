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

# parse_ar_decimal sigue siendo internal (no está en el __all__ del paquete);
# se importa desde _parsing para el test de invariante AMB-02 (Phase 2 / D-08).
from ambito_financiero_client._parsing import parse_ar_decimal


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


# ------ Verified live (Phase 2) ------


def test_get_dollar_banco_nacion_emite_url_dia_gt_12(httpx_mock: HTTPXMock) -> None:
    """Phase 2: locking de URL emitida con día > 12 (AMB-03).

    Verificado en vivo contra ``mercados.ambito.com``: el formato es ``DD/MM``
    (``21/04/2026``), no ``MM/DD``. Usar día > 12 elimina la ambigüedad
    estructuralmente (el server no podría reinterpretar ``21`` como mes).
    """
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-21/2026-04-21",
        json=[["Fecha", "Compra", "Venta"], ["21/04/2026", "1.365,00", "1.415,00"]],
    )
    assert ambito.get_dollar_banco_nacion(dt.date(2026, 4, 21)) == 1415.0


def test_parse_ar_decimal_formato_real() -> None:
    """Phase 2: locking de ``parse_ar_decimal('1.415,00') == 1415.0`` (AMB-02).

    El payload real emite el decimal con separador de miles ``.`` y separador
    decimal ``,`` (``"1.415,00"``). El parser debe tolerarlo verbatim.
    """
    assert parse_ar_decimal("1.415,00") == 1415.0


def test_get_dollar_banco_nacion_shape_list_of_list_str(httpx_mock: HTTPXMock) -> None:
    """Phase 2: locking de shape ``list[list[str]]`` y header row 0 (AMB-01/AMB-03).

    Verificado en vivo: ``row 0 == ["Fecha", "Compra", "Venta"]`` (header
    literal), ``row 1+`` son los datos. El cliente debe poder consumir ese
    shape sin transformaciones intermedias.
    """
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-21/2026-04-21",
        json=[["Fecha", "Compra", "Venta"], ["21/04/2026", "1.365,00", "1.415,00"]],
    )
    # Si el shape fuera distinto (dict o list[str]), el cliente fallaría; el
    # hecho de que devuelva 1415.0 es proxy de que el shape esperado se respeta.
    assert ambito.get_dollar_banco_nacion(dt.date(2026, 4, 21)) == 1415.0


# ------ Regressions ------

# (vacío hasta que un finding promovido a CONFIRMED se cierre como FIXED;
# convención: docstring ``Regression: ... (finding F-NN)`` per D-07).
