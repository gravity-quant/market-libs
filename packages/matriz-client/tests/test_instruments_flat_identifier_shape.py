"""Regresión de la divergencia CONFIRMED de la Phase 39 (LIVE-NOBJ-01, plan 39-07).

Qué se midió en vivo
--------------------

``GET /rest/instruments/byCFICode`` y ``GET /rest/instruments/bySegment`` NO
devuelven la forma anidada de ``GET /rest/instruments/all``. Sus elementos son
**planos**::

    {"marketId": "ROFX", "symbol": "MERV - XMEV - RAGH - CI"}

mientras que ``/rest/instruments/all`` devuelve::

    {"cficode": "EMXXXX", "instrumentId": {"marketId": "ROFX", "symbol": "..."}}

Medido en los DOS venues del allowlist D-MATZ-33 y por lo tanto **no** es una
deriva entre venues:

- ``.planning/verification/schemas/matriz-client/get-instruments-by-cfi-esxxxx.remarkets.json``
  y ``get-instruments-by-segment.remarkets.json`` (capturados 2026-06-10 contra
  ``api.remarkets.primary.com.ar``) ya registraban ``[{marketId, symbol}]``.
- ``*.bbsa.json`` (capturados 2026-08-30 contra ``api.bbsa.matrizoms.com.ar``)
  registran exactamente lo mismo.

Por qué era invisible
---------------------

``Instrument`` declara ``instrumentId: InstrumentId`` y ``cficode``. Sobre un
elemento plano, ``instrumentId`` está **ausente**: la política Null Object de la
Phase 35 (NOBJ-02) colapsa el eslabón no-opcional ausente a
``InstrumentId.empty()`` **sin emitir divergencia**, y ``marketId``/``symbol``
—los únicos datos que el wire trajo— se descartan como divergencias ``extra``.
El resultado en vivo fue ``386`` y ``9160`` objetos ``Instrument`` con
``marketId=None, symbol=None, cficode=None``: el 100% del payload de dos
métodos públicos, descartado en silencio en las cuatro superficies
(``client.py`` y ``aio.py`` por dos endpoints).

La suite mockeada no lo detectaba porque
``tests/test_client.py::test_get_instruments_by_segment_url_invariant_phase5``
mockea la forma **anidada** para ``bySegment`` — una forma que el vendor no
emite en ese endpoint. Sólo la corrida en vivo la falsificó.

Qué pinea este archivo
----------------------

Que la forma plana del wire llegue al llamador por la MISMA ruta de acceso que
la forma anidada (``instrument.instrumentId.symbol``), en sync y en async, para
los dos endpoints afectados; y que el endpoint que sí manda la forma anidada
—el control poblado— siga funcionando igual. Falla sin el fix de
``_core._normalize_instrument_element`` y pasa con él.
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

import matriz_client
from matriz_client import aio
from matriz_client.models import Instrument

# El elemento plano tal cual lo devuelven los dos venues (copiado de las capturas
# en vivo del plan 39-07; el símbolo es el primer elemento real de bbsa).
_FLAT_ELEMENT = {"marketId": "ROFX", "symbol": "MERV - XMEV - RAGH - CI"}

# El elemento anidado de ``/rest/instruments/all`` — el CONTROL POBLADO: si el
# fix rompiera esta forma, el paquete perdería el único endpoint que hoy sí
# funciona.
_NESTED_ELEMENT = {
    "cficode": "EMXXXX",
    "instrumentId": {"marketId": "ROFX", "symbol": "MERV - XMEV - XLC - CI"},
}

_BY_CFI_URL = "https://api.test/rest/instruments/byCFICode?CFICode=ESXXXX"
_BY_SEGMENT_URL = "https://api.test/rest/instruments/bySegment?MarketSegmentID=MERV&MarketID=ROFX"
_ALL_URL = "https://api.test/rest/instruments/all"


def _envelope(*elements: dict[str, object]) -> dict[str, object]:
    return {"status": "OK", "instruments": list(elements)}


# ---------------------------------------------------------------------------
# byCFICode — forma plana
# ---------------------------------------------------------------------------


def test_by_cfi_flat_element_reaches_the_caller_sync(httpx_mock: HTTPXMock) -> None:
    """El símbolo del wire plano llega por ``instrumentId.symbol`` (superficie sync)."""
    httpx_mock.add_response(url=_BY_CFI_URL, method="GET", json=_envelope(_FLAT_ELEMENT))

    result = matriz_client.get_instruments_by_cfi("ESXXXX")

    assert len(result) == 1
    assert isinstance(result[0], Instrument)
    assert result[0].instrumentId.symbol == "MERV - XMEV - RAGH - CI"
    assert result[0].instrumentId.marketId == "ROFX"
    # El Null Object deja de ser falsy: el eslabón ahora transporta datos.
    assert bool(result[0].instrumentId) is True


async def test_by_cfi_flat_element_reaches_the_caller_async(httpx_mock: HTTPXMock) -> None:
    """Espejo async obligatorio (CLAUDE.md / D-08) del caso sync de arriba."""
    httpx_mock.add_response(url=_BY_CFI_URL, method="GET", json=_envelope(_FLAT_ELEMENT))

    result = await aio.get_instruments_by_cfi("ESXXXX")

    assert len(result) == 1
    assert result[0].instrumentId.symbol == "MERV - XMEV - RAGH - CI"
    assert result[0].instrumentId.marketId == "ROFX"
    assert bool(result[0].instrumentId) is True


def test_by_cfi_flat_element_does_not_fabricate_a_cficode(httpx_mock: HTTPXMock) -> None:
    """``cficode`` sigue ``None``: el wire de este endpoint no lo manda.

    El fix normaliza la ubicación de datos que SÍ llegaron; no inventa un valor
    para una clave que el vendor no emite. El llamador ya conoce el CFI porque
    es el parámetro que pasó.
    """
    httpx_mock.add_response(url=_BY_CFI_URL, method="GET", json=_envelope(_FLAT_ELEMENT))

    result = matriz_client.get_instruments_by_cfi("ESXXXX")

    assert result[0].cficode is None


def test_by_cfi_nested_element_still_works_sync(httpx_mock: HTTPXMock) -> None:
    """Forward-compat: si el vendor migrara este endpoint a la forma anidada, sigue andando.

    Pinea que el fix es ADITIVO (reconoce la forma plana) y no un renombre ciego
    que rompería la forma anidada.
    """
    httpx_mock.add_response(url=_BY_CFI_URL, method="GET", json=_envelope(_NESTED_ELEMENT))

    result = matriz_client.get_instruments_by_cfi("ESXXXX")

    assert result[0].instrumentId.symbol == "MERV - XMEV - XLC - CI"
    assert result[0].cficode == "EMXXXX"


# ---------------------------------------------------------------------------
# bySegment — forma plana
# ---------------------------------------------------------------------------


def test_by_segment_flat_element_reaches_the_caller_sync(httpx_mock: HTTPXMock) -> None:
    """Mismo defecto, segundo endpoint: 9160 elementos vacíos en la corrida en vivo."""
    httpx_mock.add_response(url=_BY_SEGMENT_URL, method="GET", json=_envelope(_FLAT_ELEMENT))

    result = matriz_client.get_instruments_by_segment("MERV")

    assert len(result) == 1
    assert result[0].instrumentId.symbol == "MERV - XMEV - RAGH - CI"
    assert result[0].instrumentId.marketId == "ROFX"
    assert bool(result[0].instrumentId) is True


async def test_by_segment_flat_element_reaches_the_caller_async(httpx_mock: HTTPXMock) -> None:
    """Espejo async obligatorio del caso sync de arriba."""
    httpx_mock.add_response(url=_BY_SEGMENT_URL, method="GET", json=_envelope(_FLAT_ELEMENT))

    result = await aio.get_instruments_by_segment("MERV")

    assert len(result) == 1
    assert result[0].instrumentId.symbol == "MERV - XMEV - RAGH - CI"
    assert result[0].instrumentId.marketId == "ROFX"
    assert bool(result[0].instrumentId) is True


# ---------------------------------------------------------------------------
# Control poblado: el endpoint que SÍ manda la forma anidada
# ---------------------------------------------------------------------------


def test_all_instruments_nested_control_is_unaffected_sync(httpx_mock: HTTPXMock) -> None:
    """``/rest/instruments/all`` manda la forma anidada y debe seguir intacto."""
    httpx_mock.add_response(url=_ALL_URL, method="GET", json=_envelope(_NESTED_ELEMENT))

    result = matriz_client.get_all_instruments()

    assert result[0].instrumentId.symbol == "MERV - XMEV - XLC - CI"
    assert result[0].instrumentId.marketId == "ROFX"
    assert result[0].cficode == "EMXXXX"


async def test_all_instruments_nested_control_is_unaffected_async(httpx_mock: HTTPXMock) -> None:
    """Espejo async del control poblado."""
    httpx_mock.add_response(url=_ALL_URL, method="GET", json=_envelope(_NESTED_ELEMENT))

    result = await aio.get_all_instruments()

    assert result[0].instrumentId.symbol == "MERV - XMEV - XLC - CI"
    assert result[0].cficode == "EMXXXX"


# ---------------------------------------------------------------------------
# Bordes: el normalizador no puede romper un payload degenerado
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "element",
    [
        pytest.param({}, id="dict-vacio"),
        pytest.param({"marketId": "ROFX"}, id="solo-marketId"),
        pytest.param({"symbol": "X"}, id="solo-symbol"),
        pytest.param({"instrumentId": None}, id="instrumentId-nulo"),
    ],
)
def test_degenerate_elements_do_not_raise(
    httpx_mock: HTTPXMock, element: dict[str, object]
) -> None:
    """Ningún elemento degenerado puede lanzar: la tolerancia del walker se preserva."""
    httpx_mock.add_response(url=_BY_CFI_URL, method="GET", json=_envelope(element))

    result = matriz_client.get_instruments_by_cfi("ESXXXX")

    assert len(result) == 1
    assert isinstance(result[0], Instrument)


def test_non_dict_element_does_not_raise(httpx_mock: HTTPXMock) -> None:
    """Un elemento que no es dict tampoco puede lanzar (el walker ya lo toleraba)."""
    httpx_mock.add_response(
        url=_BY_CFI_URL,
        method="GET",
        json={"status": "OK", "instruments": ["no-soy-un-dict"]},
    )

    result = matriz_client.get_instruments_by_cfi("ESXXXX")

    assert len(result) == 1
    assert isinstance(result[0], Instrument)
