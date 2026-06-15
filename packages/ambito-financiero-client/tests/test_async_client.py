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

# parse_ar_decimal sigue siendo internal (no está en el __all__ del paquete);
# se importa desde _parsing para el test de invariante AMB-02 (Phase 2 / D-08).
# Espejo literal del sync por D-09 (una sola convención cross-surface).
from ambito_financiero_client._parsing import parse_ar_decimal


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


# ------ Verified live (Phase 2) ------


async def test_async_get_dollar_banco_nacion_emite_url_dia_gt_12(
    httpx_mock: HTTPXMock,
) -> None:
    """Phase 2: locking de URL emitida con día > 12 (AMB-03, async espejo).

    Espejo async del sync — D-06 dual surface invariant: lo que verifica el sync
    también se verifica en async.
    """
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-21/2026-04-21",
        json=[["Fecha", "Compra", "Venta"], ["21/04/2026", "1.365,00", "1.415,00"]],
    )
    assert await aio.get_dollar_banco_nacion(dt.date(2026, 4, 21)) == 1415.0


def test_async_parse_ar_decimal_formato_real() -> None:
    """Phase 2: locking de ``parse_ar_decimal('1.415,00') == 1415.0`` (AMB-02).

    Duplicación literal del sync por D-09 (mantiene la simetría exacta de la
    sección Verified live aunque ``parse_ar_decimal`` no sea async).
    """
    assert parse_ar_decimal("1.415,00") == 1415.0


async def test_async_get_dollar_banco_nacion_shape_list_of_list_str(
    httpx_mock: HTTPXMock,
) -> None:
    """Phase 2: locking de shape ``list[list[str]]`` y header row 0 (AMB-01/AMB-03, async).

    Espejo async del sync. Verificado en vivo: ``row 0 == ["Fecha","Compra","Venta"]``.
    """
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-21/2026-04-21",
        json=[["Fecha", "Compra", "Venta"], ["21/04/2026", "1.365,00", "1.415,00"]],
    )
    assert await aio.get_dollar_banco_nacion(dt.date(2026, 4, 21)) == 1415.0


# ------ Regressions ------

# (vacío hasta que un finding promovido a CONFIRMED se cierre como FIXED;
# convención: docstring ``Regression: ... (finding F-NN)`` per D-07).


# ------ Phase 13 ERG-01 — with_options(max_retries=N) view shape (async mirror) ------


async def test_with_options_aclose_is_noop(httpx_mock: HTTPXMock) -> None:
    """Phase 13 D-V1 async mirror: view.aclose() MUST NOT close parent's http_client."""
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-07/2026-04-07",
        json=[["Fecha", "Compra", "Venta"], ["07/04/2026", "1365,00", "1415,00"]],
    )
    client = aio.AsyncClient()
    await client.get_dollar_banco_nacion(dt.date(2026, 4, 7))
    parent_http = client._state.http_client
    assert parent_http is not None

    view = client.with_options(max_retries=5)
    await view.aclose()  # MUST be no-op
    assert client._state.http_client is parent_http
    assert client._state.http_client is not None
    await client.aclose()  # cleanup parent's pool


async def test_with_options_aexit_is_noop(httpx_mock: HTTPXMock) -> None:
    """``async with view:`` block exits without tearing down parent's http_client."""
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-07/2026-04-07",
        json=[["Fecha", "Compra", "Venta"], ["07/04/2026", "1365,00", "1415,00"]],
    )
    client = aio.AsyncClient()
    await client.get_dollar_banco_nacion(dt.date(2026, 4, 7))
    parent_http = client._state.http_client
    assert parent_http is not None

    view = client.with_options(max_retries=5)
    async with view:
        pass  # exit triggers __aexit__ → aclose() → no-op guard

    assert client._state.http_client is parent_http
    assert client._state.http_client is not None
    await client.aclose()


async def test_with_options_chaining_inner_wins_local_async() -> None:
    """D-V2 async mirror: chaining inner wins."""
    client = aio.AsyncClient()
    view = client.with_options(max_retries=5).with_options(max_retries=10)
    assert view._max_retries == 10
    assert client._max_retries == 2
    assert view._state is client._state


async def test_with_options_async_repr_shows_view_prefix() -> None:
    """Async view's ``__repr__`` is prefixed with ``"view of "``."""
    client = aio.AsyncClient()
    view = client.with_options(max_retries=5)
    assert repr(view).startswith("view of AmbitoFinancieroAsyncClient(")
    assert not repr(client).startswith("view of ")


async def test_with_options_async_invalid_max_retries_raises_value_error() -> None:
    """WR-06 carry-forward async mirror: invalid ``max_retries`` raises ValueError."""
    client = aio.AsyncClient()
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=-1)
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=True)
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=1.5)  # type: ignore[arg-type]
