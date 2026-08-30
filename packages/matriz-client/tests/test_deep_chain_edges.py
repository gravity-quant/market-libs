"""SC-2 / D-12 — los casos límite no rompen los SEIS alias de ``MarketDataSnapshot``.

matriz sigue bloqueado para verificación en vivo por política: el allowlist de
venue de ``main_matriz.py`` (D-MATZ-33 / ``LIVE-MATZ-33``) **no se rodea**, y la
superficie del paquete incluye entrada de órdenes. Esta suite es por lo tanto la
red mockeada que hace falsificable, sin depender del estado del mercado ni de
que el sandbox responda, que los seis eslabones que ``NOBJ-MTZ-02`` (Phase 37)
declaró se desreferencian sin levantar ``AttributeError`` ni ``TypeError``.

Se ejercitan los **seis** alias en cada caso, no una muestra: ``bids``,
``offers``, ``last``, ``settlement``, ``close`` y ``open_interest``. Cubrir tres
y extrapolar sería exactamente el agujero que un alias mal escrito atravesaría.

Las **dos superficies** de matriz para esta cadena son ``matriz_client.Client
.get_market_data`` y ``matriz_client.aio.AsyncClient.get_market_data``, ambas
devolviendo :class:`~matriz_client.models.MarketDataSnapshot`. ``ws_client.py``
**no** participa: la misma clase es el payload del frame WS ``type == "Md"``, así
que los alias sirven a esa superficie sin código propio y sin decode aparte (las
``@property`` son invisibles a :func:`typing.get_type_hints` y por lo tanto al
walker — Phase 35 criterio 5, D-16).

**Mercado cerrado (D-12).** Uno de los casos manda ``LA`` presente con un
``date`` de epoch-ms viejo. Lo que se verifica es que el modelo **no
discrimina**: devuelve el valor tal cual y las seis desreferencias siguen sin
levantar. El discriminador de antigüedad vive en el driver — la guarda sobre
``LA.date`` de ``main_matriz.py`` —, no en el modelo, y por eso esta suite no lo
replica. Ésta es la mitad mockeada de "mercado cerrado vs campo mal modelado":
la que dice que un book viejo no es una cadena rota.

**CR-02 — el payload ES el baseline committeado.** Las constantes se derivan de
``.planning/verification/schemas/matriz-client/get-market-data.json`` verbatim
(capturado contra remarkets el 2026-06-10): ``BI`` y ``OF`` en lista vacía,
``LA``/``SE``/``OI``/``CL``/``OP`` en ``null``, sin ``HI``/``LO``/``TV``. Poblar
un campo que el baseline manda vacío es el defecto que CR-02 midió; cuando una
constante SÍ puebla algo, lo declara y dice por qué. El envelope
``{"status": "OK", "marketData": {...}}`` es forma de transporte y no está en el
baseline (que captura el modelo, no el sobre); se agrega acá porque es lo que
``_core.parse_get_market_data_response`` desenvuelve. Todos los identificadores
son sintetizados (T-39-07).

**Control poblado obligatorio (T-39-08),** con aserción de identidad por ``is``
entre cada alias y su campo wire: un alias que copiara o cacheara pasaría un
``==`` y falla acá.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import Iterator
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

import matriz_client
from matriz_client import aio
from matriz_client.models import MarketDataSnapshot

# ---------------------------------------------------------------------------
# Payloads — derivados del baseline committeado (ver docstring, CR-02)
# ---------------------------------------------------------------------------

_SYMBOL = "AAA/ZZZ26"

# ``.planning/verification/schemas/matriz-client/get-market-data.json`` VERBATIM.
# Las siete claves que el capture registró, en el estado en que las registró.
_MD_BASELINE: dict[str, Any] = {
    "BI": [],
    "CL": None,
    "LA": None,
    "OF": [],
    "OI": None,
    "OP": None,
    "SE": None,
}

# Entradas sintéticas. ``BI``/``OF`` son niveles ``{price, size}``;
# ``LA``/``SE``/``OI``/``CL`` son entradas ``{price, size, date}`` (§8.1).
_BID: dict[str, Any] = {"price": 102.0, "size": 500}
_OFFER: dict[str, Any] = {"price": 102.5, "size": 300}
_FRESH_DATE = 4_102_444_800_000  # 2100-01-01, epoch-ms
_STALE_DATE = 946_684_800_000  # 2000-01-01, epoch-ms — el book de un mercado cerrado
_LA: dict[str, Any] = {"price": 102.25, "size": 3, "date": _FRESH_DATE}
_SE: dict[str, Any] = {"price": 101.0, "size": 0, "date": _FRESH_DATE}
_OI: dict[str, Any] = {"price": 1500.0, "size": 0, "date": _FRESH_DATE}
_CL: dict[str, Any] = {"price": 100.0, "size": 0, "date": _FRESH_DATE}

# Fila AISLADORA: el baseline con las cuatro hojas ESCALARES pobladas
# (``OP``/``HI``/``LO``/``TV``), de modo que los únicos candidatos a levantar
# sean los seis eslabones-objeto. Es la misma técnica que
# ``_LINKS_ONLY_NO_DATA_ROW`` del análogo de market-data, y se declara acá en vez
# de esconderse: poblar estas cuatro es deliberado, no un descuido de fidelidad.
_MD_ISOLATING: dict[str, Any] = {
    **_MD_BASELINE,
    "OP": 99.0,
    "HI": 103.0,
    "LO": 99.5,
    "TV": 4321.0,
}

# Las seis entradas pobladas — el CONTROL.
_MD_POPULATED: dict[str, Any] = {
    **_MD_ISOLATING,
    "BI": [_BID],
    "OF": [_OFFER],
    "LA": _LA,
    "SE": _SE,
    "OI": _OI,
    "CL": _CL,
}

# Listas vacías con los cuatro eslabones-objeto poblados: aísla "un link de lista
# vacío" de cualquier otra causa de fallo.
_MD_EMPTY_LISTS: dict[str, Any] = {**_MD_POPULATED, "BI": [], "OF": []}

# Claves ausentes: sin ``LA``/``SE``/``CL``/``OI``, con las listas pobladas.
_MD_MISSING_OBJECT_KEYS: dict[str, Any] = {
    k: v for k, v in _MD_POPULATED.items() if k not in {"LA", "SE", "CL", "OI"}
}

# ``null`` explícito sobre un eslabón de cada forma: ``LA`` (objeto) y ``BI``
# (lista). Debe dar el mismo resultado que la clave ausente.
_MD_EXPLICIT_NULL: dict[str, Any] = {**_MD_POPULATED, "LA": None, "BI": None}

# Mercado cerrado: todo poblado, pero ``LA.date`` es viejo.
_MD_STALE: dict[str, Any] = {**_MD_POPULATED, "LA": {**_LA, "date": _STALE_DATE}}


def _envelope(market_data: dict[str, Any]) -> dict[str, Any]:
    """El sobre ``{"status": "OK", "marketData": {...}}`` que el parser desenvuelve."""
    return {"status": "OK", "marketData": market_data}


# ---------------------------------------------------------------------------
# Helpers — la aserción con dientes
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _no_chain_break(what: str) -> Iterator[None]:
    """Falla el test si la cadena levanta ``AttributeError`` o ``TypeError``.

    Copia local a propósito: este monorepo no tiene paquete compartido por
    diseño, y un helper importado desde otro paquete introduciría exactamente el
    acoplamiento cruzado que la política del repo prohíbe.

    Deja pasar cualquier otra excepción — un error tipado del paquete es
    comportamiento correcto, no una rotura de cadena. Nunca se usa solo: cada
    sitio de uso assertea además el **valor** resultante.
    """
    try:
        yield
    except (AttributeError, TypeError) as exc:  # pragma: no cover - ruta de fallo
        pytest.fail(f"deep chain broke on {what}: {type(exc).__name__}: {exc}")


def _summarize(snap: MarketDataSnapshot) -> dict[str, Any]:
    """Desreferencia los SEIS alias y devuelve el resultado como valores.

    Es lo que convierte "no levanta" en una aserción con dientes: cada caso
    compara este resumen completo contra un esperado explícito, así que un alias
    que devolviera lo de otro campo, o que colapsara siempre a vacío, falla en
    vez de pasar. Los seis se tocan SIEMPRE, en todos los casos.
    """
    return {
        "bids": [level.price for level in snap.bids],
        "offers": [level.price for level in snap.offers],
        "last": snap.last.price,
        "settlement": snap.settlement.price,
        "close": snap.close.price,
        "open_interest": snap.open_interest.price,
        "truthy": tuple(
            name
            for name, value in (
                ("bids", snap.bids),
                ("offers", snap.offers),
                ("last", snap.last),
                ("settlement", snap.settlement),
                ("close", snap.close),
                ("open_interest", snap.open_interest),
            )
            if value
        ),
    }


_ALL_EMPTY: dict[str, Any] = {
    "bids": [],
    "offers": [],
    "last": None,
    "settlement": None,
    "close": None,
    "open_interest": None,
    "truthy": (),
}

_CASES = [
    pytest.param(_MD_BASELINE, _ALL_EMPTY, id="baseline-verbatim"),
    pytest.param(
        _MD_EMPTY_LISTS,
        {
            "bids": [],
            "offers": [],
            "last": 102.25,
            "settlement": 101.0,
            "close": 100.0,
            "open_interest": 1500.0,
            "truthy": ("last", "settlement", "close", "open_interest"),
        },
        id="empty-lists",
    ),
    pytest.param(
        _MD_MISSING_OBJECT_KEYS,
        {
            "bids": [102.0],
            "offers": [102.5],
            "last": None,
            "settlement": None,
            "close": None,
            "open_interest": None,
            "truthy": ("bids", "offers"),
        },
        id="missing-object-keys",
    ),
    pytest.param(
        _MD_EXPLICIT_NULL,
        {
            "bids": [],
            "offers": [102.5],
            "last": None,
            "settlement": 101.0,
            "close": 100.0,
            "open_interest": 1500.0,
            "truthy": ("offers", "settlement", "close", "open_interest"),
        },
        id="explicit-null",
    ),
    pytest.param(
        _MD_STALE,
        {
            "bids": [102.0],
            "offers": [102.5],
            "last": 102.25,
            "settlement": 101.0,
            "close": 100.0,
            "open_interest": 1500.0,
            "truthy": ("bids", "offers", "last", "settlement", "close", "open_interest"),
        },
        id="market-closed-stale-last",
    ),
]


# ---------------------------------------------------------------------------
# Los cinco casos, sobre las dos superficies
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("market_data", "expected"), _CASES)
def test_six_aliases_never_break_the_chain(
    httpx_mock: HTTPXMock, market_data: dict[str, Any], expected: dict[str, Any]
) -> None:
    """Superficie sync (``Client.get_market_data``): los seis alias, los cinco casos."""
    httpx_mock.add_response(method="GET", json=_envelope(market_data))

    snap = matriz_client.get_market_data(_SYMBOL)

    with _no_chain_break("snap.{bids,offers,last,settlement,close,open_interest}"):
        assert _summarize(snap) == expected
        assert len(snap.bids) == len(expected["bids"])
        assert len(snap.offers) == len(expected["offers"])


@pytest.mark.parametrize(("market_data", "expected"), _CASES)
async def test_six_aliases_never_break_the_chain_async(
    httpx_mock: HTTPXMock, market_data: dict[str, Any], expected: dict[str, Any]
) -> None:
    """Gemelo async — ``aio.AsyncClient.get_market_data``, la otra superficie."""
    httpx_mock.add_response(method="GET", json=_envelope(market_data))

    snap = await aio.get_market_data(_SYMBOL)

    with _no_chain_break("snap.{bids,offers,last,settlement,close,open_interest}"):
        assert _summarize(snap) == expected
        assert len(snap.bids) == len(expected["bids"])
        assert len(snap.offers) == len(expected["offers"])


# ---------------------------------------------------------------------------
# Mercado cerrado — el modelo no discrimina antigüedad
# ---------------------------------------------------------------------------


def test_stale_last_is_returned_as_is_by_the_model(httpx_mock: HTTPXMock) -> None:
    """El ``date`` viejo llega intacto: la guarda de antigüedad es del driver.

    Que ``LA`` esté viejo no es un campo mal modelado ni una cadena rota — es un
    mercado cerrado. El modelo devuelve el epoch-ms tal cual y no sustituye nada;
    quien decide si eso es aceptable es ``main_matriz.py``, no
    :class:`~matriz_client.models.MarketDataSnapshot`.
    """
    httpx_mock.add_response(method="GET", json=_envelope(_MD_STALE))

    snap = matriz_client.get_market_data(_SYMBOL)

    with _no_chain_break("snap.last.date"):
        assert snap.last.date == _STALE_DATE
        assert snap.last.price == 102.25
        assert bool(snap.last) is True


async def test_stale_last_is_returned_as_is_by_the_model_async(httpx_mock: HTTPXMock) -> None:
    """Gemelo async de :func:`test_stale_last_is_returned_as_is_by_the_model`."""
    httpx_mock.add_response(method="GET", json=_envelope(_MD_STALE))

    snap = await aio.get_market_data(_SYMBOL)

    with _no_chain_break("snap.last.date"):
        assert snap.last.date == _STALE_DATE
        assert snap.last.price == 102.25


# ---------------------------------------------------------------------------
# Control poblado + identidad de los alias
# ---------------------------------------------------------------------------


def test_populated_control_and_alias_identity(httpx_mock: HTTPXMock) -> None:
    """CONTROL (T-39-08) — valores reales y cada alias ES su campo wire.

    Sin este test, todas las aserciones de colapso seguirían verdes aunque los
    seis alias devolvieran siempre vacío. Las seis comparaciones por ``is`` son
    la otra mitad: un alias que copiara la lista o cacheara la entrada pasaría un
    ``==`` y se pone rojo acá — que es lo que declara que son **vistas de sólo
    lectura sin comportamiento** (NOBJ-MTZ-02).
    """
    httpx_mock.add_response(method="GET", json=_envelope(_MD_POPULATED))

    snap = matriz_client.get_market_data(_SYMBOL)

    assert snap.bids is snap.BI
    assert snap.offers is snap.OF
    assert snap.last is snap.LA
    assert snap.settlement is snap.SE
    assert snap.close is snap.CL
    assert snap.open_interest is snap.OI

    assert snap.bids[0].price == 102.0
    assert snap.bids[0].size == 500
    assert snap.offers[0].price == 102.5
    assert snap.last.price == 102.25
    assert snap.settlement.price == 101.0
    assert snap.close.price == 100.0
    assert snap.open_interest.price == 1500.0
    # Las hojas escalares de la misma respuesta siguen llegando.
    assert snap.OP == 99.0
    assert snap.HI == 103.0
    assert snap.LO == 99.5
    assert snap.TV == 4321.0


async def test_populated_control_and_alias_identity_async(httpx_mock: HTTPXMock) -> None:
    """Gemelo async de :func:`test_populated_control_and_alias_identity`."""
    httpx_mock.add_response(method="GET", json=_envelope(_MD_POPULATED))

    snap = await aio.get_market_data(_SYMBOL)

    assert snap.bids is snap.BI
    assert snap.offers is snap.OF
    assert snap.last is snap.LA
    assert snap.settlement is snap.SE
    assert snap.close is snap.CL
    assert snap.open_interest is snap.OI

    assert snap.bids[0].price == 102.0
    assert snap.offers[0].price == 102.5
    assert snap.last.price == 102.25
    assert snap.settlement.price == 101.0
    assert snap.close.price == 100.0
    assert snap.open_interest.price == 1500.0


# ---------------------------------------------------------------------------
# 204 / cuerpo vacío
# ---------------------------------------------------------------------------


def test_market_data_204_empty_body_does_not_break_the_chain(httpx_mock: HTTPXMock) -> None:
    """204 sin cuerpo: matriz levanta ``JSONDecodeError``, no ``AttributeError``/``TypeError``.

    Lo que D-12 exige es que la cadena profunda no se rompa; un error de decode
    no es una rotura de cadena porque no llega a haber snapshot que
    desreferenciar. El tipo se assertea explícitamente en vez de aceptar
    cualquier excepción.

    Comportamiento MEDIDO, dicho y no escondido: ``_core.parse_envelope_response``
    consume el body, pasa el status check (204 es éxito) y llama ``resp.json()``,
    así que la excepción escapa la jerarquía ``PrimaryAPIError``. Es la misma
    ausencia de tolerancia a 204 que tiene iol y la contraria a higyrus, que sí
    devuelve su zero-value. Queda anotado en el ``deferred-items.md`` de la fase
    (D39-02); cambiar ese comportamiento es un cambio de superficie del paquete,
    fuera del alcance de un plan que sólo crea tests. Si algún día matriz gana la
    tolerancia, este test es el primero en ponerse rojo.
    """
    httpx_mock.add_response(method="GET", status_code=204)

    with pytest.raises(json.JSONDecodeError) as exc:
        matriz_client.get_market_data(_SYMBOL)

    assert type(exc.value) is json.JSONDecodeError
    assert not isinstance(exc.value, AttributeError)
    assert not isinstance(exc.value, TypeError)


async def test_market_data_204_empty_body_does_not_break_the_chain_async(
    httpx_mock: HTTPXMock,
) -> None:
    """Gemelo async de :func:`test_market_data_204_empty_body_does_not_break_the_chain`."""
    httpx_mock.add_response(method="GET", status_code=204)

    with pytest.raises(json.JSONDecodeError) as exc:
        await aio.get_market_data(_SYMBOL)

    assert type(exc.value) is json.JSONDecodeError
    assert not isinstance(exc.value, AttributeError)
    assert not isinstance(exc.value, TypeError)


def test_null_market_data_envelope_raises_a_typed_error(httpx_mock: HTTPXMock) -> None:
    """``{"marketData": null}`` es violación de forma, no un snapshot vacío (WR-05).

    Contraparte del caso de arriba para el nivel del SOBRE: el eslabón que
    colapsa en silencio es el que está DENTRO de ``marketData``, no
    ``marketData`` mismo. Un envelope nulo sigue siendo un
    :class:`~matriz_client.exceptions.PrimaryAPIError` tipado — y no un
    ``AttributeError``, que es lo que D-12 prohíbe.
    """
    httpx_mock.add_response(method="GET", json={"status": "OK", "marketData": None})

    with pytest.raises(matriz_client.PrimaryAPIError) as exc:
        matriz_client.get_market_data(_SYMBOL)

    assert not isinstance(exc.value, AttributeError)
    assert "marketData" in (exc.value.description or "")


async def test_null_market_data_envelope_raises_a_typed_error_async(httpx_mock: HTTPXMock) -> None:
    """Gemelo async de :func:`test_null_market_data_envelope_raises_a_typed_error`."""
    httpx_mock.add_response(method="GET", json={"status": "OK", "marketData": None})

    with pytest.raises(matriz_client.PrimaryAPIError) as exc:
        await aio.get_market_data(_SYMBOL)

    assert not isinstance(exc.value, AttributeError)
    assert "marketData" in (exc.value.description or "")
