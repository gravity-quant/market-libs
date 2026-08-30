"""SC-2 / D-12 — los casos límite no rompen la cadena ``Posicion.parking``.

**higyrus no tiene mitad en vivo en esta fase.** El host del vendor no resuelve
por DNS desde esta red, así que el driver ``main_higyrus.py`` se reporta
``SKIPPED`` con causa medida y destino nombrado — ``LIVE-HIGY-33`` (plan 39-01,
``_VENDOR_UNREACHABLE_SKIP_LINE``). Esta suite es por lo tanto la **única
evidencia falsificable** de que la cadena tipada de higyrus aguanta los cuatro
casos límite de D-12; no es un complemento opcional de una corrida en vivo que
no va a existir.

Hay una segunda razón, independiente del DNS, por la que la rama **poblada** de
``parking`` sólo puede vivir acá: el driver pide ``incluirParking`` en **falso**
en sus dos sitios de llamada (``main_higyrus.py:1796`` y ``:1909``), así que ni
siquiera una corrida en vivo exitosa produciría una fila con book de parking.
El control poblado de este módulo es la única cobertura de esa rama en todo el
repo.

La cadena bajo prueba es ``posicion.parking[...].diasParking``:
:attr:`~higyrus_client.models.Posicion.parking` es ``list[Parking]`` —
no-Opcional y sin default de dataclass—, así que un ``null`` del wire o la clave
ausente colapsan a ``[]`` por la rama NOBJ-02 del walker y la cadena se recorre
sin guarda de nulidad.

**CR-02 — el payload ES el baseline committeado.** Las constantes se derivan de
``.planning/verification/schemas/higyrus-client/get-posiciones.json`` verbatim:
las mismas 19 claves, en el mismo estado. En particular el baseline capturó
``parking`` como ``NoneType`` y **no** trae ``disponibleAjustado``; las dos cosas
se respetan tal cual. Poblar un campo que el baseline manda vacío es el defecto
exacto que CR-02 midió y que volvió verde una aserción por la razón equivocada.
Los baselines son keys-and-types-only por construcción, así que los valores
concretos son sintetizados — cuenta, especie e ISIN incluidos (T-39-07).

**Control poblado obligatorio (T-39-08):** sin él, todas las aserciones de
colapso seguirían verdes aunque ``parking`` colapsara SIEMPRE, con book en el
wire o sin él.
"""

from __future__ import annotations

import contextlib
import datetime as dt
from collections.abc import Iterator
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

import higyrus_client
from higyrus_client import aio
from higyrus_client.models import Posicion

# ---------------------------------------------------------------------------
# Payloads — derivados del baseline committeado (ver docstring, CR-02)
# ---------------------------------------------------------------------------

# ``.planning/verification/schemas/higyrus-client/get-posiciones.json`` verbatim:
# 19 claves, ``parking`` en ``null`` (así lo capturó el 2026-06-08) y SIN
# ``disponibleAjustado`` (el baseline tampoco lo trae — el campo sólo llega para
# FCI). Ésta es a la vez la fila del caso NULL EXPLÍCITO y la fila AISLADORA:
# todas las hojas escalares vienen pobladas, así que el único candidato a
# levantar en la cadena es el eslabón ``parking``.
_POSICION_NULL_PARKING: dict[str, Any] = {
    "cantidadLiquidada": 150,
    "cantidadPendienteLiquidar": 0,
    "codigoISIN": "XX0000000001",
    "cuenta": "CTA-0001",
    "especie": "AAA1",
    "estado": "LIQUIDADA",
    "fecha": "2099-01-01",
    "fechaPrecio": "2099-01-01",
    "informacion": "",
    "lugar": "LOCAL",
    "monedaCotizacion": "ARS",
    "nombreEspecie": "ESPECIE SINTETICA",
    "parking": None,
    "precio": 102,
    "precioUnitario": 1,
    "simboloLocal": "AAA1",
    "subCuenta": "0",
    "tipoTitulo": "ACCIONES",
    "tipoTituloAgente": "ACCIONES",
}

# Lista vacía: el vendor manda la clave, sin entradas.
_POSICION_EMPTY_PARKING: dict[str, Any] = {**_POSICION_NULL_PARKING, "parking": []}

# Clave ausente: el vendor no manda ``parking`` en absoluto.
_POSICION_MISSING_PARKING: dict[str, Any] = {
    k: v for k, v in _POSICION_NULL_PARKING.items() if k != "parking"
}

# Control poblado — los cuatro campos de :class:`~higyrus_client.models.Parking`.
# Ninguna corrida en vivo de esta fase puede producir esta fila: el driver pide
# ``incluirParking`` en falso (ver docstring del módulo).
_PARKING_ROW: dict[str, Any] = {
    "monedaPosicion": "ARS",
    "diasParking": 3,
    "cantidadLiquidada": 150,
    "observacion": "parking sintetico",
}
_POSICION_POPULATED_PARKING: dict[str, Any] = {
    **_POSICION_NULL_PARKING,
    "parking": [_PARKING_ROW],
}

_DEGENERATE_ROWS = [
    pytest.param(_POSICION_EMPTY_PARKING, id="empty-list"),
    pytest.param(_POSICION_MISSING_PARKING, id="missing-key"),
    pytest.param(_POSICION_NULL_PARKING, id="explicit-null"),
]

_ID_CUENTA = "CTA-0001"
_FECHA = dt.date(2099, 1, 1)


# ---------------------------------------------------------------------------
# Helper — la aserción con dientes
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


# ---------------------------------------------------------------------------
# Construcción directa desde payload — Posicion.from_api
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("row", _DEGENERATE_ROWS)
def test_posicion_from_api_collapses_parking_to_empty_list(row: dict[str, Any]) -> None:
    """Los tres casos degenerados dan ``[]``, nunca ``None``, y no levantan.

    Se construye por ``Posicion.from_api(row)`` y jamás por
    ``Posicion(field=value)`` (CLAUDE.md): el constructor directo saltearía el
    walker, que es justamente el sujeto de esta prueba.
    """
    posicion = Posicion.from_api(row)

    with _no_chain_break("posicion.parking"):
        assert posicion.parking == []
        assert posicion.parking is not None
        assert len(posicion.parking) == 0
        assert bool(posicion.parking) is False
        assert [p.diasParking for p in posicion.parking] == []
        dias = posicion.parking[0].diasParking if posicion.parking else None
        assert dias is None
    # Las hojas escalares de la MISMA fila siguen llegando: sin esto, un modelo
    # que devolviera todo vacío pasaría igual.
    assert posicion.especie == "AAA1"
    assert posicion.cantidadLiquidada == 150


def test_posicion_from_api_populated_control() -> None:
    """CONTROL (T-39-08) — con book de parking la cadena devuelve el entero real."""
    posicion = Posicion.from_api(_POSICION_POPULATED_PARKING)

    assert bool(posicion.parking) is True
    assert len(posicion.parking) == 1
    assert posicion.parking[0].diasParking == 3
    assert posicion.parking[0].monedaPosicion == "ARS"
    assert posicion.parking[0].cantidadLiquidada == 150
    assert posicion.parking[0].observacion == "parking sintetico"


# ---------------------------------------------------------------------------
# Ruta tipada del cliente — sync y async
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("row", _DEGENERATE_ROWS)
def test_get_posiciones_degenerate_parking_never_breaks_the_chain(
    httpx_mock: HTTPXMock, row: dict[str, Any]
) -> None:
    """Superficie sync: la ruta completa del cliente, no sólo el modelo."""
    httpx_mock.add_response(method="GET", json=[row])

    posiciones = higyrus_client.get_posiciones(_ID_CUENTA, _FECHA)

    with _no_chain_break("posiciones[...].parking"):
        assert len(posiciones) == 1
        assert posiciones[0].parking == []
        assert bool(posiciones[0].parking) is False
        assert sum(len(p.parking) for p in posiciones) == 0
        assert [d.diasParking for p in posiciones for d in p.parking] == []
    assert posiciones[0].especie == "AAA1"


@pytest.mark.parametrize("row", _DEGENERATE_ROWS)
async def test_get_posiciones_degenerate_parking_never_breaks_the_chain_async(
    httpx_mock: HTTPXMock, row: dict[str, Any]
) -> None:
    """Gemelo async de :func:`test_get_posiciones_degenerate_parking_never_breaks_the_chain`."""
    httpx_mock.add_response(method="GET", json=[row])

    posiciones = await aio.get_posiciones(_ID_CUENTA, _FECHA)

    with _no_chain_break("posiciones[...].parking"):
        assert len(posiciones) == 1
        assert posiciones[0].parking == []
        assert bool(posiciones[0].parking) is False
        assert sum(len(p.parking) for p in posiciones) == 0
        assert [d.diasParking for p in posiciones for d in p.parking] == []
    assert posiciones[0].especie == "AAA1"


def test_get_posiciones_populated_control(httpx_mock: HTTPXMock) -> None:
    """CONTROL (T-39-08) por la ruta del cliente, superficie sync.

    ``incluir_parking=True`` es la única forma de pedir esta rama, y el driver
    en vivo pide lo contrario — de ahí que esta aserción no tenga equivalente
    posible fuera de esta suite.
    """
    httpx_mock.add_response(method="GET", json=[_POSICION_POPULATED_PARKING])

    posiciones = higyrus_client.get_posiciones(_ID_CUENTA, _FECHA, incluir_parking=True)

    assert bool(posiciones[0].parking) is True
    assert sum(len(p.parking) for p in posiciones) == 1
    assert posiciones[0].parking[0].diasParking == 3
    assert posiciones[0].parking[0].monedaPosicion == "ARS"


async def test_get_posiciones_populated_control_async(httpx_mock: HTTPXMock) -> None:
    """Gemelo async de :func:`test_get_posiciones_populated_control`."""
    httpx_mock.add_response(method="GET", json=[_POSICION_POPULATED_PARKING])

    posiciones = await aio.get_posiciones(_ID_CUENTA, _FECHA, incluir_parking=True)

    assert bool(posiciones[0].parking) is True
    assert posiciones[0].parking[0].diasParking == 3


# ---------------------------------------------------------------------------
# 204 / cuerpo vacío
# ---------------------------------------------------------------------------


def test_get_posiciones_204_yields_the_empty_shape(httpx_mock: HTTPXMock) -> None:
    """204 sin cuerpo: la ruta devuelve ``[]`` y la comprehension no levanta.

    Se corresponde con la rama ``status_code == 204 or not resp.content`` →
    ``None`` que ``main_higyrus._raw_request_sync`` replica del shim legacy: el
    paquete trata el 204 como su zero-value (``higyrus_client._core
    ._parse_list_or_raise``) en vez de dejar escapar un error de decode. Es la
    diferencia con iol y matriz, y está medida, no asumida.
    """
    httpx_mock.add_response(method="GET", status_code=204)

    with _no_chain_break("get_posiciones -> 204"):
        posiciones = higyrus_client.get_posiciones(_ID_CUENTA, _FECHA)
        assert posiciones == []
        assert sum(len(p.parking) for p in posiciones) == 0

    # El idioma del driver sobre el ``None`` que ``_raw_request_sync`` devuelve
    # en 204: la comprehension recorre ``[]`` en vez de iterar ``None``, que es
    # lo que produciría el ``TypeError`` que D-12 prohíbe.
    raw: list[dict[str, Any]] | None = None
    with _no_chain_break("comprehension sobre el raw de un 204"):
        assert [Posicion.from_api(r) for r in (raw or [])] == []


async def test_get_posiciones_204_yields_the_empty_shape_async(httpx_mock: HTTPXMock) -> None:
    """Gemelo async de :func:`test_get_posiciones_204_yields_the_empty_shape`."""
    httpx_mock.add_response(method="GET", status_code=204)

    with _no_chain_break("get_posiciones -> 204"):
        posiciones = await aio.get_posiciones(_ID_CUENTA, _FECHA)
        assert posiciones == []
        assert sum(len(p.parking) for p in posiciones) == 0
