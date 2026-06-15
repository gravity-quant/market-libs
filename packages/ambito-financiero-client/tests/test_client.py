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


# ------ Phase 13 ERG-01 — with_options(max_retries=N) view shape ------


def test_with_options_close_is_noop(httpx_mock: HTTPXMock) -> None:
    """Phase 13 D-V1: view.close() MUST NOT close parent's http_client.

    Anti-Pitfall 13: a view shares ``_state.http_client`` with the parent;
    closing the view would tear down the parent's TCP pool. The lifecycle
    no-op guard (``if getattr(self, "_is_view", False): return``) prevents this.
    """
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-07/2026-04-07",
        json=[["Fecha", "Compra", "Venta"], ["07/04/2026", "1365,00", "1415,00"]],
    )
    client = ambito.Client()
    # Force lazy init of http_client via an actual call.
    client.get_dollar_banco_nacion(dt.date(2026, 4, 7))
    parent_http = client._state.http_client
    assert parent_http is not None

    view = client.with_options(max_retries=5)
    view.close()  # MUST be no-op
    assert client._state.http_client is parent_http
    assert client._state.http_client is not None  # parent's pool still open


def test_with_options_exit_is_noop(httpx_mock: HTTPXMock) -> None:
    """``with view:`` block exits without tearing down parent's http_client."""
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-07/2026-04-07",
        json=[["Fecha", "Compra", "Venta"], ["07/04/2026", "1365,00", "1415,00"]],
    )
    client = ambito.Client()
    client.get_dollar_banco_nacion(dt.date(2026, 4, 7))
    parent_http = client._state.http_client
    assert parent_http is not None

    view = client.with_options(max_retries=5)
    with view:
        pass  # exit triggers __exit__ → close() → no-op guard

    assert client._state.http_client is parent_http
    assert client._state.http_client is not None


def test_with_options_chaining_inner_wins_local() -> None:
    """D-V2: ``c.with_options(5).with_options(10)._max_retries == 10``."""
    client = ambito.Client()
    view = client.with_options(max_retries=5).with_options(max_retries=10)
    assert view._max_retries == 10
    assert client._max_retries == 2
    assert view._state is client._state


def test_with_options_repr_shows_view_prefix() -> None:
    """View's ``__repr__`` is prefixed with ``"view of "`` (debug ergonomics)."""
    client = ambito.Client()
    view = client.with_options(max_retries=5)
    assert repr(view).startswith("view of AmbitoFinancieroClient(")
    assert not repr(client).startswith("view of ")


def test_with_options_invalid_max_retries_raises_value_error() -> None:
    """WR-06 carry-forward: invalid ``max_retries`` rejected BEFORE view construction."""
    client = ambito.Client()
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=-1)
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=True)
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=1.5)  # type: ignore[arg-type]
