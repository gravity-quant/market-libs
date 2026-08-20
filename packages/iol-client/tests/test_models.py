"""Tests del layer tolerante ``iol_client.models`` (Plan 30-01).

Fija el comportamiento que D-01..D-04 y D-08 especifican para `Cotizacion` y
`Punta`:

- Los **dos** schemas capturados que usan `Cotizacion` (`get-quote.json` y cada
  fila de `get-historical-quotes.json`) decodifican con **cero** registros de
  divergencia. Es el mismo modelo: ambos endpoints traen las mismas 20 claves y
  difieren sólo en cuáles llegan nulas (D-03).
- `puntas` en sus 3 formas observadas del corpus (`[]`, `None`, lista poblada).
- La asimetría D-04 de `cantidadOperaciones`: declarado `int` en `Cotizacion`,
  la rama entera del walker es **estricta** — un decimal del wire sustituye el
  typed zero y emite un registro de clase ``type``.
- El round-trip D-08: `schema_of(model.to_dict())` reproduce el `schema`
  committeado byte-idéntico, en los dos schemas.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import pathlib
from collections.abc import Iterator
from typing import Any

import pytest
from verification.schema import schema_of

from iol_client import _decode
from iol_client.models import Cotizacion, Punta, SafeModel

_MESSAGE = "decode divergence"

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SCHEMA_DIR = _REPO_ROOT / ".planning" / "verification" / "schemas" / "iol-client"


def _committed_schema(name: str) -> Any:
    """El valor de la clave ``schema`` del snapshot committeado ``name``."""
    return json.loads((_SCHEMA_DIR / f"{name}.json").read_text(encoding="utf-8"))["schema"]


# Payload sintético con las 20 claves y los tipos exactos de
# ``.planning/verification/schemas/iol-client/get-quote.json`` (captura
# 2026-06-06). Los valores son plausibles; lo que se fija son claves y tipos.
_QUOTE_PAYLOAD: dict[str, Any] = {
    "apertura": 1200.0,
    "cantidadOperaciones": 1543,
    "cierreAnterior": 1180.5,
    "descripcionTitulo": "GRUPO FINANCIERO GALICIA",
    "fechaHora": "2026-06-06T11:56:08.19",
    "interesesAbiertos": 0.0,
    "laminaMinima": 1,
    "lote": 1,
    "maximo": 1250.0,
    "minimo": 1190.0,
    "moneda": "peso_Argentino",
    "montoOperado": 987654321.0,
    "plazo": "t2",
    "precioAjuste": 0.0,
    "precioPromedio": 1220.25,
    "puntas": [],
    "tendencia": "sube",
    "ultimoPrecio": 1234.5,
    "variacion": 4.62,
    "volumenNominal": 812345.0,
}

# Misma forma, nulabilidad de la serie histórica (D-03): ``descripcionTitulo``,
# ``plazo`` y ``puntas`` llegan ``null``.
_HISTORICAL_ROW: dict[str, Any] = {
    **_QUOTE_PAYLOAD,
    "descripcionTitulo": None,
    "plazo": None,
    "puntas": None,
}


@pytest.fixture(autouse=True)
def _pristine_decode_context() -> Iterator[None]:
    """Arrancar cada test con el scope y el modo de decode desligados.

    Sin esto, cualquier test previo que haya corrido un ``_request`` real deja
    su ``DECODE_SCOPE`` ligado y la deduplicación colapsa los registros que
    estos tests afirman — volviéndolos verdes por ORDEN de ejecución. Mismo
    razonamiento que ``test_decode.py``.
    """
    mode = _decode.STRICT_DECODE.get()
    scope = _decode.DECODE_SCOPE.get()
    _decode.STRICT_DECODE.set(False)
    _decode.DECODE_SCOPE.set(None)
    try:
        yield
    finally:
        _decode.STRICT_DECODE.set(mode)
        _decode.DECODE_SCOPE.set(scope)


def _divergences(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Los registros de divergencia capturados, en orden de emisión."""
    return [r for r in caplog.records if r.getMessage() == _MESSAGE]


# ---------------------------------------------------------------------------
# Construcción desde los dos schemas capturados
# ---------------------------------------------------------------------------


def test_from_api_get_quote_payload_has_zero_divergences(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="iol_client"):
        quote = Cotizacion.from_api(_QUOTE_PAYLOAD)

    assert _divergences(caplog) == []
    assert quote.apertura == 1200.0
    assert quote.cantidadOperaciones == 1543
    assert quote.cierreAnterior == 1180.5
    assert quote.descripcionTitulo == "GRUPO FINANCIERO GALICIA"
    assert quote.fechaHora == "2026-06-06T11:56:08.19"
    assert quote.interesesAbiertos == 0.0
    assert quote.laminaMinima == 1
    assert quote.lote == 1
    assert quote.maximo == 1250.0
    assert quote.minimo == 1190.0
    assert quote.moneda == "peso_Argentino"
    assert quote.montoOperado == 987654321.0
    assert quote.plazo == "t2"
    assert quote.precioAjuste == 0.0
    assert quote.precioPromedio == 1220.25
    assert quote.puntas == []
    assert quote.tendencia == "sube"
    assert quote.ultimoPrecio == 1234.5
    assert quote.variacion == 4.62
    assert quote.volumenNominal == 812345.0


def test_from_api_historical_row_has_zero_divergences(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """D-03: la rama Optional del walker devuelve ``None`` sin emitir registro."""
    with caplog.at_level(logging.DEBUG, logger="iol_client"):
        row = Cotizacion.from_api(_HISTORICAL_ROW)

    assert _divergences(caplog) == []
    assert row.descripcionTitulo is None
    assert row.plazo is None
    assert row.puntas is None
    assert row.ultimoPrecio == 1234.5


def test_cotizacion_declara_exactamente_veinte_campos() -> None:
    assert len(dataclasses.fields(Cotizacion)) == 20


# ---------------------------------------------------------------------------
# Tolerancia: payload vacío y payload ausente
# ---------------------------------------------------------------------------


def test_from_api_empty_dict_yields_typed_zeros() -> None:
    quote = Cotizacion.from_api({})
    assert quote.apertura == 0.0
    assert quote.cantidadOperaciones == 0
    assert quote.moneda == ""
    assert quote.descripcionTitulo is None
    assert quote.plazo is None
    assert quote.puntas is None


def test_from_api_none_does_not_raise() -> None:
    quote = Cotizacion.from_api(None)
    assert quote.ultimoPrecio == 0.0
    assert quote.puntas is None


# ---------------------------------------------------------------------------
# Polimorfismo de ``puntas`` — las 3 formas observadas
# ---------------------------------------------------------------------------


def test_puntas_lista_vacia_queda_vacia() -> None:
    assert Cotizacion.from_api({**_QUOTE_PAYLOAD, "puntas": []}).puntas == []


def test_puntas_nula_queda_nula() -> None:
    assert Cotizacion.from_api({**_QUOTE_PAYLOAD, "puntas": None}).puntas is None


def test_puntas_poblada_construye_modelos_punta() -> None:
    payload = {
        **_QUOTE_PAYLOAD,
        "puntas": [
            {
                "cantidadCompra": 100.0,
                "precioCompra": 1233.0,
                "precioVenta": 1235.0,
                "cantidadVenta": 250.0,
            }
        ],
    }
    quote = Cotizacion.from_api(payload)
    assert quote.puntas is not None
    assert len(quote.puntas) == 1
    punta = quote.puntas[0]
    assert isinstance(punta, Punta)
    assert punta.cantidadCompra == 100.0
    assert punta.cantidadVenta == 250.0
    assert punta.precioCompra == 1233.0
    assert punta.precioVenta == 1235.0


def test_punta_from_api_construye_los_cuatro_campos() -> None:
    punta = Punta.from_api(
        {
            "cantidadCompra": 1.0,
            "cantidadVenta": 2.0,
            "precioCompra": 3.0,
            "precioVenta": 4.0,
        }
    )
    assert isinstance(punta, SafeModel)
    assert (punta.cantidadCompra, punta.cantidadVenta) == (1.0, 2.0)
    assert (punta.precioCompra, punta.precioVenta) == (3.0, 4.0)


# ---------------------------------------------------------------------------
# Asimetría D-04 — ``cantidadOperaciones`` es la rama entera, estricta
# ---------------------------------------------------------------------------


def test_cantidad_operaciones_entera_pasa_sin_registro(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="iol_client"):
        quote = Cotizacion.from_api({**_QUOTE_PAYLOAD, "cantidadOperaciones": 7})

    assert quote.cantidadOperaciones == 7
    assert _divergences(caplog) == []


def test_cantidad_operaciones_decimal_sustituye_typed_zero_y_reporta(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """D-04 a propósito: la rama ``int`` NO ensancha, la rama ``float`` sí."""
    with caplog.at_level(logging.DEBUG, logger="iol_client"):
        quote = Cotizacion.from_api({**_QUOTE_PAYLOAD, "cantidadOperaciones": 7.0})

    assert quote.cantidadOperaciones == 0
    # El walker prefija cada segmento con ``.``; en el tope el path es
    # ``.<campo>`` (``_decode.walk_model``).
    registros = [
        r for r in _divergences(caplog) if getattr(r, "field_path", None) == ".cantidadOperaciones"
    ]
    assert len(registros) == 1
    assert registros[0].divergence == "type"  # type: ignore[attr-defined]
    assert registros[0].declared_type == "int"  # type: ignore[attr-defined]
    assert registros[0].observed_type == "float"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# D-08 — ``to_dict()`` y el round-trip contra los schemas committeados
# ---------------------------------------------------------------------------


def test_to_dict_devuelve_un_dict_plano() -> None:
    quote = Cotizacion.from_api(
        {
            **_QUOTE_PAYLOAD,
            "puntas": [
                {
                    "cantidadCompra": 1.0,
                    "cantidadVenta": 2.0,
                    "precioCompra": 3.0,
                    "precioVenta": 4.0,
                }
            ],
        }
    )
    wire = quote.to_dict()
    assert isinstance(wire, dict)
    assert not isinstance(wire, Cotizacion)
    assert isinstance(wire["puntas"][0], dict)
    assert wire["puntas"][0]["precioVenta"] == 4.0


def test_round_trip_reproduce_el_schema_committeado_de_get_quote() -> None:
    quote = Cotizacion.from_api(_QUOTE_PAYLOAD)
    assert schema_of(quote.to_dict()) == _committed_schema("get-quote")


def test_round_trip_reproduce_el_schema_committeado_de_serie_historica() -> None:
    row = Cotizacion.from_api(_HISTORICAL_ROW)
    assert schema_of(row.to_dict()) == _committed_schema("get-historical-quotes")[0]
