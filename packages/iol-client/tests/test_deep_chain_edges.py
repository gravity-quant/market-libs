"""SC-2 / D-12 — los casos límite de la API en vivo no rompen la cadena `.puntas`.

La mitad **en vivo** de la Phase 39 es time-boxed y depende del estado del
mercado: si el book llega vacío porque la rueda está cerrada, la corrida no
distingue "la cadena aguanta el book vacío" de "nunca hubo un book que
desreferenciar". Esta suite es la mitad **mockeada** que hace la propiedad
falsificable con independencia de eso: los cuatro casos límite que la API
produce —lista vacía, clave ausente, ``null`` explícito y 204 / cuerpo vacío—
se inyectan a mano sobre **ambas** superficies (``iol_client`` y
``iol_client.aio``) y se exige que ninguna desreferencia de la cadena profunda
levante ``AttributeError`` ni ``TypeError``.

Las dos cadenas de iol tienen forma distinta y ambas se cubren (D-02):

* :attr:`iol_client.models.Cotizacion.puntas` es ``list[Punta]`` — la cadena es
  ``quote.puntas[0].precioCompra`` y el subscript sólo se evalúa detrás de una
  guarda de veracidad;
* :attr:`iol_client.models.Titulo.puntas` es un :class:`~iol_client.models.Punta`
  **singular** — un Null Object, así que ``titulo.puntas.precioCompra`` se
  evalúa **siempre**, sin guarda, y devuelve el cero tipado cuando el wire no
  trajo book.

Vive bajo ``packages/iol-client/tests/`` y no bajo ``verification/`` porque ese
es el único árbol que el job ``test`` de CI corre de verdad; ``verification/``
sólo corre por allowlist explícita.

**CR-02 — el payload ES el baseline committeado.** Las constantes de este módulo
se derivan de ``.planning/verification/schemas/iol-client/get-quote.json`` y de
``get-instruments-by-type.json`` verbatim: mismas claves, mismos tipos y —lo que
CR-02 encontró que importa— **ningún campo que el baseline manda ``null`` se
puebla acá**. Los baselines son keys-and-types-only por construcción
(``verification/schema.py``), así que los valores concretos son sintetizados; el
símbolo, la descripción y el resto de los identificadores son inventados a
propósito (T-39-07: ningún valor observado de un venue real entra al repo).

**Control poblado obligatorio (T-39-08).** Sin él, las aserciones de "no lanza"
seguirían verdes aunque la cadena estuviera rota de otra manera —por ejemplo si
``puntas`` colapsara SIEMPRE a vacío, incluso con book en el wire—. Los dos
controles de este módulo son los que hacen que un verde signifique algo.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import Iterator
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

import iol_client
from iol_client import aio

# ---------------------------------------------------------------------------
# Payloads — derivados de los baselines committeados (ver docstring, CR-02)
# ---------------------------------------------------------------------------

# ``.planning/verification/schemas/iol-client/get-quote.json`` verbatim: las 20
# claves del baseline, con ``puntas: []`` tal cual el capture del 2026-06-06 lo
# registró. Ésta es a la vez la fila DEGENERADA (el book vacío) y la fila
# AISLADORA: todas las hojas escalares vienen pobladas, así que el único
# candidato a levantar en la cadena es el eslabón ``puntas``.
_QUOTE_EMPTY_PUNTAS: dict[str, Any] = {
    "apertura": 101.5,
    "cantidadOperaciones": 12,
    "cierreAnterior": 100.0,
    "descripcionTitulo": "TITULO SINTETICO SA",
    "fechaHora": "2099-01-01T00:00:00",
    "interesesAbiertos": 0.0,
    "laminaMinima": 1,
    "lote": 1,
    "maximo": 103.0,
    "minimo": 99.5,
    "moneda": "peso_Argentino",
    "montoOperado": 4321.0,
    "plazo": "t2",
    "precioAjuste": 0.0,
    "precioPromedio": 101.0,
    "puntas": [],
    "tendencia": "sube",
    "ultimoPrecio": 102.25,
    "variacion": 2.25,
    "volumenNominal": 43.0,
}

# Clave ausente: el wire simplemente no manda ``puntas``.
_QUOTE_MISSING_PUNTAS: dict[str, Any] = {
    k: v for k, v in _QUOTE_EMPTY_PUNTAS.items() if k != "puntas"
}

# ``null`` explícito: la serie histórica de iol manda exactamente esto.
_QUOTE_NULL_PUNTAS: dict[str, Any] = {**_QUOTE_EMPTY_PUNTAS, "puntas": None}

# Control poblado — la única fila del módulo donde el book existe. La forma del
# elemento es la que ``get-instruments-by-type.json`` registra para ``puntas``
# (los cuatro decimales); el elemento de ``Cotizacion.puntas`` es *inobservado*
# en el corpus (D-02 / :class:`~iol_client.models.Punta`) y esta fila lo declara.
_PUNTA_ROW: dict[str, Any] = {
    "cantidadCompra": 500.0,
    "cantidadVenta": 300.0,
    "precioCompra": 102.0,
    "precioVenta": 102.5,
}
_QUOTE_POPULATED_PUNTAS: dict[str, Any] = {**_QUOTE_EMPTY_PUNTAS, "puntas": [_PUNTA_ROW]}

# ``.planning/verification/schemas/iol-client/get-instruments-by-type.json``
# verbatim — una fila del envelope ``titulos``. Los tres campos que el baseline
# capturó como ``NoneType`` (``fechaVencimiento``, ``precioEjercicio``,
# ``tipoOpcion``) se dejan en ``None``: poblarlos sería el defecto exacto que
# CR-02 midió. Ésta es a la vez la fila aisladora y el CONTROL POBLADO de la
# cadena singular, porque el baseline trae ``puntas`` como objeto.
_TITULO_POPULATED_PUNTAS: dict[str, Any] = {
    "apertura": 101.5,
    "cantidadOperaciones": 12.0,
    "descripcion": "TITULO SINTETICO SA",
    "fecha": "2099-01-01T00:00:00",
    "fechaVencimiento": None,
    "laminaMinima": 1,
    "lote": 1,
    "maximo": 103.0,
    "mercado": "1",
    "minimo": 99.5,
    "moneda": "peso_Argentino",
    "plazo": "T0",
    "precioEjercicio": None,
    "puntas": _PUNTA_ROW,
    "simbolo": "AAA1",
    "tipoOpcion": None,
    "ultimoCierre": 100.0,
    "ultimoPrecio": 102.25,
    "variacionPorcentual": 2.25,
    "volumen": 43.0,
}

_TITULO_MISSING_PUNTAS: dict[str, Any] = {
    k: v for k, v in _TITULO_POPULATED_PUNTAS.items() if k != "puntas"
}

_TITULO_NULL_PUNTAS: dict[str, Any] = {**_TITULO_POPULATED_PUNTAS, "puntas": None}

# ``Cotizacion.puntas`` colapsa a ``[]`` en los tres casos degenerados. El id de
# cada caso viaja al nombre del test para que un rojo diga CUÁL de los tres.
_DEGENERATE_QUOTE_CASES = [
    pytest.param(_QUOTE_EMPTY_PUNTAS, id="empty-list"),
    pytest.param(_QUOTE_MISSING_PUNTAS, id="missing-key"),
    pytest.param(_QUOTE_NULL_PUNTAS, id="explicit-null"),
]

_DEGENERATE_TITULO_CASES = [
    pytest.param(_TITULO_MISSING_PUNTAS, id="missing-key"),
    pytest.param(_TITULO_NULL_PUNTAS, id="explicit-null"),
]


# ---------------------------------------------------------------------------
# Helper — la aserción con dientes
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _no_chain_break(what: str) -> Iterator[None]:
    """Falla el test si la cadena levanta ``AttributeError`` o ``TypeError``.

    Un ``pytest.raises`` invertido no existe, y un ``try/except: pass`` haría
    pasar el test justamente cuando la propiedad se rompe. Este bloque convierte
    las dos excepciones que D-12 declara prohibidas en un fallo con el nombre de
    la cadena que las produjo, y deja pasar cualquier otra —un error tipado del
    paquete es comportamiento correcto, no una rotura de cadena—.

    Nunca se usa solo: cada sitio de uso asserta además el **valor** resultante.
    """
    try:
        yield
    except (AttributeError, TypeError) as exc:  # pragma: no cover - ruta de fallo
        pytest.fail(f"deep chain broke on {what}: {type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Cotizacion.puntas — cadena por subscript (list[Punta])
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("payload", _DEGENERATE_QUOTE_CASES)
def test_quote_puntas_degenerate_never_breaks_the_chain(
    httpx_mock: HTTPXMock, payload: dict[str, Any]
) -> None:
    """Superficie sync: los tres casos degenerados dan ``[]``, ninguno levanta."""
    httpx_mock.add_response(method="GET", json=payload)

    quote = iol_client.get_quote("AAA1")

    with _no_chain_break("quote.puntas"):
        assert quote.puntas == []
        assert len(quote.puntas) == 0
        assert bool(quote.puntas) is False
        # La guarda de veracidad corta antes del subscript: éste es el idioma
        # que la lib documenta, y acá se ejercita en vez de describirse.
        precio = quote.puntas[0].precioCompra if quote.puntas else None
        assert precio is None
        # Iterar un book vacío tampoco levanta.
        assert [p.precioCompra for p in quote.puntas] == []
    # El eslabón colapsó, pero las hojas escalares de la MISMA fila siguen
    # llegando: sin esto, un modelo que devolviera todo vacío pasaría igual.
    assert quote.ultimoPrecio == 102.25


@pytest.mark.parametrize("payload", _DEGENERATE_QUOTE_CASES)
async def test_quote_puntas_degenerate_never_breaks_the_chain_async(
    httpx_mock: HTTPXMock, payload: dict[str, Any]
) -> None:
    """Gemelo async de :func:`test_quote_puntas_degenerate_never_breaks_the_chain`."""
    httpx_mock.add_response(method="GET", json=payload)

    quote = await aio.get_quote("AAA1")

    with _no_chain_break("quote.puntas"):
        assert quote.puntas == []
        assert len(quote.puntas) == 0
        assert bool(quote.puntas) is False
        precio = quote.puntas[0].precioCompra if quote.puntas else None
        assert precio is None
        assert [p.precioCompra for p in quote.puntas] == []
    assert quote.ultimoPrecio == 102.25


def test_quote_puntas_populated_control(httpx_mock: HTTPXMock) -> None:
    """CONTROL (T-39-08) — con book en el wire la cadena devuelve el valor real.

    Ésta es la aserción que impide que las tres anteriores sean verdes por la
    razón equivocada: si ``puntas`` colapsara siempre a ``[]``, todas ellas
    pasarían y sólo ésta se pondría roja.
    """
    httpx_mock.add_response(method="GET", json=_QUOTE_POPULATED_PUNTAS)

    quote = iol_client.get_quote("AAA1")

    assert bool(quote.puntas) is True
    assert len(quote.puntas) == 1
    assert quote.puntas[0].precioCompra == 102.0
    assert quote.puntas[0].precioVenta == 102.5
    assert quote.puntas[0].cantidadCompra == 500.0
    assert quote.puntas[0].cantidadVenta == 300.0


async def test_quote_puntas_populated_control_async(httpx_mock: HTTPXMock) -> None:
    """Gemelo async de :func:`test_quote_puntas_populated_control`."""
    httpx_mock.add_response(method="GET", json=_QUOTE_POPULATED_PUNTAS)

    quote = await aio.get_quote("AAA1")

    assert bool(quote.puntas) is True
    assert len(quote.puntas) == 1
    assert quote.puntas[0].precioCompra == 102.0
    assert quote.puntas[0].precioVenta == 102.5


# ---------------------------------------------------------------------------
# Titulo.puntas — cadena por atributo directo (Punta singular, Null Object)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("row", _DEGENERATE_TITULO_CASES)
def test_titulo_puntas_degenerate_dereferences_without_a_guard(
    httpx_mock: HTTPXMock, row: dict[str, Any]
) -> None:
    """Superficie sync: el Null Object singular se desreferencia SIN guarda.

    La diferencia con :class:`~iol_client.models.Cotizacion` es la que hace
    falta cubrir aparte: acá no hay subscript ni guarda de veracidad que corte,
    ``titulo.puntas.precioCompra`` se evalúa siempre. Que devuelva el cero
    tipado en vez de levantar es toda la propiedad NOBJ-IOL-01.
    """
    httpx_mock.add_response(method="GET", json={"titulos": [row]})

    [titulo] = iol_client.get_instruments_by_type("acciones")

    with _no_chain_break("titulo.puntas"):
        assert titulo.puntas.precioCompra == 0.0
        assert titulo.puntas.precioVenta == 0.0
        assert titulo.puntas.cantidadCompra == 0.0
        assert titulo.puntas.cantidadVenta == 0.0
        assert bool(titulo.puntas) is False
    assert titulo.simbolo == "AAA1"


@pytest.mark.parametrize("row", _DEGENERATE_TITULO_CASES)
async def test_titulo_puntas_degenerate_dereferences_without_a_guard_async(
    httpx_mock: HTTPXMock, row: dict[str, Any]
) -> None:
    """Gemelo async de :func:`test_titulo_puntas_degenerate_dereferences_without_a_guard`."""
    httpx_mock.add_response(method="GET", json={"titulos": [row]})

    [titulo] = await aio.get_instruments_by_type("acciones")

    with _no_chain_break("titulo.puntas"):
        assert titulo.puntas.precioCompra == 0.0
        assert titulo.puntas.precioVenta == 0.0
        assert bool(titulo.puntas) is False
    assert titulo.simbolo == "AAA1"


def test_titulo_puntas_populated_control(httpx_mock: HTTPXMock) -> None:
    """CONTROL (T-39-08) de la cadena singular — el baseline trae ``puntas`` poblado."""
    httpx_mock.add_response(method="GET", json={"titulos": [_TITULO_POPULATED_PUNTAS]})

    [titulo] = iol_client.get_instruments_by_type("acciones")

    assert bool(titulo.puntas) is True
    assert titulo.puntas.precioCompra == 102.0
    assert titulo.puntas.precioVenta == 102.5


async def test_titulo_puntas_populated_control_async(httpx_mock: HTTPXMock) -> None:
    """Gemelo async de :func:`test_titulo_puntas_populated_control`."""
    httpx_mock.add_response(method="GET", json={"titulos": [_TITULO_POPULATED_PUNTAS]})

    [titulo] = await aio.get_instruments_by_type("acciones")

    assert bool(titulo.puntas) is True
    assert titulo.puntas.precioCompra == 102.0


# ---------------------------------------------------------------------------
# 204 / cuerpo vacío
# ---------------------------------------------------------------------------


def test_quote_204_empty_body_does_not_break_the_chain(httpx_mock: HTTPXMock) -> None:
    """204 sin cuerpo: iol levanta ``JSONDecodeError``, **nunca** ``AttributeError``/``TypeError``.

    Lo que D-12 exige es que la cadena profunda no se rompa; un error de decode
    no es una rotura de cadena porque no llega a haber modelo que desreferenciar.
    El tipo se assertea explícitamente en vez de aceptar cualquier excepción.

    Comportamiento MEDIDO, dicho y no escondido: a diferencia de higyrus —cuyo
    ``_parse_list_or_raise`` trata ``204``/cuerpo vacío como su zero-value—, iol
    **no tiene tolerancia a 204** y la excepción que escapa queda fuera de la
    jerarquía ``IOLClientError``. Es una decisión de alcance ya registrada en el
    docstring de ``iol_client._core._parse_list_or_raise`` ("copiar el helper de
    higyrus metería una tolerancia a 204 que iol hoy no tiene"), no un
    descubrimiento de este plan; queda anotada en ``deferred-items.md`` de la
    fase. Si algún día iol gana esa tolerancia, este test es el primero en
    ponerse rojo y el cambio no puede pasar en silencio.
    """
    httpx_mock.add_response(method="GET", status_code=204)

    with pytest.raises(json.JSONDecodeError) as exc:
        iol_client.get_quote("AAA1")

    assert type(exc.value) is json.JSONDecodeError
    assert not isinstance(exc.value, AttributeError)
    assert not isinstance(exc.value, TypeError)


async def test_quote_204_empty_body_does_not_break_the_chain_async(httpx_mock: HTTPXMock) -> None:
    """Gemelo async de :func:`test_quote_204_empty_body_does_not_break_the_chain`."""
    httpx_mock.add_response(method="GET", status_code=204)

    with pytest.raises(json.JSONDecodeError) as exc:
        await aio.get_quote("AAA1")

    assert type(exc.value) is json.JSONDecodeError
    assert not isinstance(exc.value, AttributeError)
    assert not isinstance(exc.value, TypeError)


def test_instruments_by_type_missing_titulos_key_yields_no_rows(httpx_mock: HTTPXMock) -> None:
    """Envelope sin ``titulos``: cero filas, sin ``TypeError`` al iterar (D-06).

    Complemento del caso 204 para la cadena singular: el cuerpo ES el dict que
    el parser espera, sólo que sin filas. La comprehension del caller recorre
    una lista vacía en vez de iterar un ``None``.
    """
    httpx_mock.add_response(method="GET", json={})

    with _no_chain_break("get_instruments_by_type -> titulos"):
        titulos = iol_client.get_instruments_by_type("acciones")
        assert titulos == []
        assert [t.puntas.precioCompra for t in titulos] == []


async def test_instruments_by_type_missing_titulos_key_yields_no_rows_async(
    httpx_mock: HTTPXMock,
) -> None:
    """Gemelo async de :func:`test_instruments_by_type_missing_titulos_key_yields_no_rows`."""
    httpx_mock.add_response(method="GET", json={})

    with _no_chain_break("get_instruments_by_type -> titulos"):
        titulos = await aio.get_instruments_by_type("acciones")
        assert titulos == []
        assert [t.puntas.precioCompra for t in titulos] == []
