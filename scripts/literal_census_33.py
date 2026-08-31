#!/usr/bin/env python
"""Censo de valores en vivo para LIVE-TYP-01 criterio 3 (D-08 / D-09 / D-10).

Recolecta, **desde el wire crudo**, el conjunto de valores distintos que la API
real emite en los nueve campos que este ciclo tiene que censar:

- ``matriz-client`` — los siete campos RESPONSE que llevan un alias ``Literal``:
  ``marketId`` (``Segment`` y ``InstrumentId``), ``cficode`` (``Instrument`` e
  ``InstrumentDetail``), ``currency`` y ``orderTypes`` (``InstrumentDetail``) y
  ``ordType`` (``Order``).
- ``iol-client`` — ``Titulo.mercado`` y ``Titulo.plazo``, la evidencia RESPONSE
  con la que se cierra DT-07.

**Por qué el censo lee el wire y no el stream de divergencias (D-08).**
``_decode.walk_field`` toma, en su rama ``Literal``, un ``return value`` temprano
cuando el valor tiene el tipo de runtime correcto y ``policy.literal_enforced``
es ``False`` — y es ``False`` en las cinco constantes ``POLICY``, de forma
permanente y por diseño. El sink nunca se llama, así que un valor fuera del
conjunto declarado **no produce ningún record de divergencia**.
``29-DLOCK-RESPONSE-LITERAL.md`` afirma lo contrario en sus líneas 140-142; el
código shipeado es el autoritativo. ``verification.schema.schema_of`` tampoco
sirve: reduce cada valor a su nombre de tipo. De ahí que la única fuente posible
sea el payload crudo.

**El censo es de sólo lectura.** No emite ninguna orden, ninguna mutación y
ningún barrido deliberado de 4xx contra la cuenta viva para enumerar el conjunto
de entrada aceptado: ese barrido está explícitamente diferido por D-10 y
prohibido por P-05 de ``33-06-PLAN.md``.

**Los payloads crudos van al staging gitignored.** Cada respuesta que el censo
toca se vuelca con ``verification.capture.capture(...)`` bajo
``.planning/verification/captures/`` (``.gitignore:51``), que es el único hogar
legal del wire crudo (C-4 / D-11 / T-33-32). Lo único derivado del wire que sale
por stdout —y por lo tanto lo único que puede llegar al artefacto committeado—
son los conjuntos de valores distintos de esos nueve campos, que son vocabulario
enum-like, no identificadores.

**matriz corre detrás del allowlist de venue D-MATZ-33.** El venue se resuelve
con ``_venue_token``, importado de ``main_matriz`` (D-01): igualdad EXACTA de
hostname contra el allowlist que ese módulo publica, nunca pertenencia de
substring ni ``endswith`` —``…primary.com.ar.attacker.example`` pasaría un
``in``— y fail-closed ante una base URL imparseable o sin host. Si el host no
está en el allowlist, el censo imprime ``SKIPPED — base URL fuera del
allowlist`` y **no autentica ni emite una sola request**: el gate corre antes
del login, así que un SKIP no cuesta ni un round trip. El gate no se rodea: la
superficie de matriz incluye entrada de órdenes y este es el mecanismo que
impide que una verificación toque una venue que no es un sandbox acordado.
Ampliar el allowlist **no es un cambio de rutina**: cada host nuevo exige una
decisión humana explícita (P-05), y se hace en ``main_matriz.py``, que es la
única fuente. El gate de MUTACIÓN es otro control, independiente
(``verification/mutation_gate.py``), y este script no lo toca.

Antes de la primera request el censo emite ``CENSUS-HEADER`` con el venue
medido y el timestamp UTC, y ``CENSUS-DLOCK`` recordando que el inventario es
una MEDICIÓN de una sola venue y no una autorización de promoción a ``Literal``.

**Por qué es un ``.py`` real y no un ``python -c``:** ``find_dotenv()`` cae a
``os.getcwd()`` cuando ``__main__`` no tiene ``__file__``, y no hay ``.env`` en
la raíz del repo — un ``-c`` reportaría credenciales ausentes fabricadas por el
modo de invocación (P-10).

Uso::

    uv run python scripts/literal_census_33.py
    uv run python scripts/literal_census_33.py --matriz-only  # sin census_iol()
    uv run python scripts/literal_census_33.py --selftest     # sin red
"""

from __future__ import annotations

import contextlib
import datetime as dt
import sys
from pathlib import Path
from typing import Any

# La raíz del repo entra a ``sys.path`` para poder importar ``verification/``,
# que vive en la raíz y no es un paquete publicable. Se resuelve respecto de la
# ubicación de este archivo, nunca del cwd (mismo criterio que
# ``verification/capture.py``).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# La política de venue NO se re-declara acá: se IMPORTA del sitio que ya la
# publica (D-01). La forma ``from main_matriz import ...`` —y no ``import
# main_matriz`` con uso calificado— es la que hace que el lock pueda pinnear
# IDENTIDAD de objeto (``is``), con lo cual la divergencia entre el gate del
# driver y el del censo pasa de "detectada" a estructuralmente imposible.
from main_matriz import _VENUE_ALLOWLIST, _venue_token  # noqa: E402
from verification.capture import capture  # noqa: E402

__all__ = ["collect_paths", "main"]

# Los nueve campos objetivo, por nombre de clave de wire. El walker recolecta
# por *path*, no por nombre suelto, para que ``Segment.marketId`` y
# ``InstrumentId.marketId`` —dos modelos distintos, mismo nombre de clave— no se
# mezclen en una sola fila del censo.
_MATRIZ_KEYS = frozenset({"marketId", "cficode", "currency", "orderTypes", "ordType"})
_IOL_KEYS = frozenset({"mercado", "plazo"})

# Los seis tipos de instrumento que ``main_iol.py`` ya ejercita (``_ALL_INSTRUMENT_TYPES``).
_IOL_INSTRUMENT_TYPES: tuple[str, ...] = (
    "obligacionesNegociables",
    "titulosPublicos",
    "cedears",
    "acciones",
    "letras",
    "cauciones",
)


# ----------------------------------------------------------------------
# Walker de wire crudo
# ----------------------------------------------------------------------


def collect_paths(
    node: Any,
    keys: frozenset[str],
    *,
    path: str = "",
    acc: dict[str, list[tuple[str, str]]] | None = None,
) -> dict[str, list[tuple[str, str]]]:
    """Recorre un payload crudo y acumula los valores escalares de ``keys`` por path.

    El path colapsa los índices de lista a ``[]``, de modo que
    ``{"segments": [{"marketId": "ROFX"}]}`` acumula bajo ``segments[].marketId``.
    Un campo declarado ``list[Literal[...]]`` (``orderTypes``) acumula sus
    miembros bajo ``...orderTypes[]``, que es exactamente la unidad que el alias
    describe.

    Devuelve ``{path: [(tipo_json, valor), ...]}`` **con repeticiones**: la
    longitud de la lista es el conteo de filas inspeccionadas para ese campo y el
    ``set`` de sus valores es el conjunto distinto. El tipo de runtime va al lado
    del valor porque un alias ``Literal`` valida **sólo** el tipo de sus miembros
    (``_decode.walk_field``), así que "qué tipo llegó" es tan parte del censo como
    "qué valor llegó".
    """
    if acc is None:
        acc = {}
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else key
            if key in keys:
                _record(acc, child, value)
            collect_paths(value, keys, path=child, acc=acc)
    elif isinstance(node, list):
        for item in node:
            collect_paths(item, keys, path=f"{path}[]", acc=acc)
    return acc


def _record(acc: dict[str, list[tuple[str, str]]], path: str, value: Any) -> None:
    """Acumula ``value`` bajo ``path``; una lista acumula sus miembros bajo ``path[]``."""
    if isinstance(value, list):
        for item in value:
            _record(acc, f"{path}[]", item)
        return
    if isinstance(value, dict):
        # Un dict no es un valor de vocabulario; sus hojas ya las visita el
        # recorrido general. No se acumula nada acá.
        return
    rendered = "null" if value is None else str(value)
    acc.setdefault(path, []).append((type(value).__name__, rendered))


# ----------------------------------------------------------------------
# Reporte
# ----------------------------------------------------------------------


def _report(pkg: str, endpoint: str, acc: dict[str, list[tuple[str, str]]]) -> None:
    """Imprime una línea por path observado: endpoint, filas, tipos y valores distintos."""
    if not acc:
        print(f"{pkg} {endpoint}: NO TARGET FIELD PRESENT IN PAYLOAD")
        return
    for path in sorted(acc):
        entries = acc[path]
        distinct = sorted({value for _, value in entries})
        types = sorted({type_name for type_name, _ in entries})
        print(f"{pkg} {endpoint} {path}: rows={len(entries)} types={types} distinct={distinct}")


def _skip(pkg: str, reason: str) -> None:
    print(f"{pkg}: SKIPPED — {reason}")


def _census_header_lines(venue: str) -> list[str]:
    """Venue + timestamp del censo: sin esto la salida no dice contra qué se midió.

    El ``venue`` es el TOKEN que devuelve :func:`_venue_token` (``remarkets`` /
    ``bbsa``), nunca un hostname resuelto ni la base URL, y ``allowlist_size`` es un
    CONTEO — el encabezado nombra la política sin filtrar el dato de entrada
    (T-39-04 / C-4), igual que las líneas de veredicto.
    """
    stamp = dt.datetime.now(dt.UTC).isoformat()
    return [
        f"CENSUS-HEADER venue={venue} captured_at={stamp} allowlist_size={len(_VENUE_ALLOWLIST)}",
        "CENSUS-DLOCK: el D-lock (b) de la Phase 29 SIGUE EN VIGOR — los campos "
        "RESPONSE NO se cierran como Literal. Este inventario es una MEDICIÓN de "
        "una sola venue, no una autorización de promoción.",
    ]


def _census_header(venue: str) -> None:
    """Imprime el encabezado del censo; se llama antes de la primera request."""
    for line in _census_header_lines(venue):
        print(line)


# ----------------------------------------------------------------------
# matriz — detrás del gate remarkets-only (D-MATZ-33)
# ----------------------------------------------------------------------


def census_matriz() -> bool:
    """Censa los siete campos de matriz. Devuelve ``False`` si quedó SKIPPED.

    El gate de hostname corre **antes** de cualquier request y antes del login:
    un SKIP no debe costar ni un round trip contra un host fuera de política.
    """
    import os

    from matriz_client import _core
    from matriz_client.client import Client

    if not all(os.getenv(name) for name in ("PRIMARY_USER", "PRIMARY_PASSWORD")):
        _skip("matriz-client", "credenciales ausentes")
        return False

    client = Client()
    base = client._state.base_url
    venue = _venue_token(base)  # igualdad exacta de hostname, fail-closed
    if venue is None:
        # No se imprime la URL: el criterio de no-fuga del pre-flight (nunca una
        # URL resuelta) manda acá también. La causa queda igualmente nombrada.
        _skip(
            "matriz-client",
            "base URL fuera del allowlist D-MATZ-33 (la verificación es sandbox-only)",
        )
        with contextlib.suppress(Exception):
            client.close()
        return False

    # El venue MEDIDO viaja al encabezado; nunca se hardcodea, así que el header no
    # puede mentir sobre contra qué se censó.
    _census_header(venue)

    try:
        for endpoint, spec in (
            ("get_segments", _core.build_get_segments_request(client._state)),
            ("get_all_instruments", _core.build_get_all_instruments_request(client._state)),
            (
                "get_instruments_details",
                _core.build_get_instruments_details_request(client._state),
            ),
        ):
            raw = client._request(spec).json()
            capture("matriz", f"census-{endpoint}", raw)
            _report("matriz-client", endpoint, collect_paths(raw, _MATRIZ_KEYS))

        account = os.getenv("PRIMARY_ACCOUNT")
        if not account:
            _skip("matriz-client ordType", "PRIMARY_ACCOUNT ausente (endpoints de órdenes)")
        else:
            for endpoint, spec in (
                (
                    "get_active_orders",
                    _core.build_get_active_orders_request(client._state, account),
                ),
                ("get_all_orders", _core.build_get_all_orders_request(client._state, account)),
            ):
                raw = client._request(spec).json()
                capture("matriz", f"census-{endpoint}", raw)
                _report("matriz-client", endpoint, collect_paths(raw, _MATRIZ_KEYS))
    finally:
        with contextlib.suppress(Exception):
            client.close()
    return True


# ----------------------------------------------------------------------
# iol — Titulo.mercado / Titulo.plazo
# ----------------------------------------------------------------------


def census_iol() -> bool:
    """Censa ``Titulo.mercado`` y ``Titulo.plazo`` sobre los seis tipos de instrumento.

    ``GET /api/v2/Cotizaciones/{tipo}/{pais}/Todos`` devuelve **todos** los
    instrumentos del tipo pedido en la plaza, así que el conjunto observado es
    genuinamente emitido por el vendor y no un eco de lo que el driver mandó.
    """
    import os

    from iol_client import _core
    from iol_client.client import Client

    if not all(os.getenv(name) for name in ("IOL_USER", "IOL_PASSWORD")):
        _skip("iol-client", "credenciales ausentes")
        return False

    client = Client()
    agg: dict[str, list[tuple[str, str]]] = {}
    try:
        for itype in _IOL_INSTRUMENT_TYPES:
            spec = _core.build_get_instruments_by_type_request(client._state, itype)
            raw = client._request(spec).json()
            capture("iol", f"census-instruments-by-type-{itype}", raw)
            per_type = collect_paths(raw, _IOL_KEYS)
            _report("iol-client", f"get_instruments_by_type[{itype}]", per_type)
            for path, values in per_type.items():
                agg.setdefault(path, []).extend(values)

        print("--- iol agregado sobre los 6 tipos ---")
        _report("iol-client", "get_instruments_by_type[TOTAL]", agg)

        # NO-EVIDENCIA, registrado a propósito: ``Cotizacion.plazo`` de
        # ``get_quote`` devuelve el eco de los defaults ``bcba`` / ``t2`` que el
        # llamador mandó. Se imprime etiquetado para que nadie lo confunda con
        # un censo (D-10).
        quote_spec = _core.build_get_quote_request(client._state, "GGAL")
        quote_raw = client._request(quote_spec).json()
        capture("iol", "census-quote-echo", quote_raw)
        echo = collect_paths(quote_raw, _IOL_KEYS)
        for path in sorted(echo):
            echoed = sorted({value for _, value in echo[path]})
            print(
                f"iol-client get_quote {path}: NO-EVIDENCIA (eco de los defaults "
                f"enviados) distinct={echoed}"
            )
    finally:
        with contextlib.suppress(Exception):
            client.close()
    return True


# ----------------------------------------------------------------------
# Self-test offline: prueba que el walker no es un canal muerto
# ----------------------------------------------------------------------

_SELFTEST_MATRIZ: dict[str, Any] = {
    "status": "OK",
    "segments": [{"marketSegmentId": "DDF", "marketId": "ROFX"}],
    "instruments": [
        {"instrumentId": {"marketId": "ROFX", "symbol": "X"}, "cficode": "FXXXSX"},
        {"instrumentId": {"marketId": "ROFX", "symbol": "Y"}, "cficode": "ZZZZZZ"},
    ],
    "orders": [{"ordType": "LIMIT"}, {"ordType": "MARKET"}],
    "details": [{"currency": "ARS", "orderTypes": ["LIMIT", "MARKET"]}],
}

_SELFTEST_IOL: dict[str, Any] = {
    "titulos": [
        {"simbolo": "A", "mercado": "bCBA", "plazo": "t2"},
        {"simbolo": "B", "mercado": "bcba", "plazo": "t1"},
    ]
}


def _selftest() -> int:
    """Ejercita el walker sobre payloads sintéticos, sin red y sin credenciales.

    Existe para que un ``SKIPPED`` de matriz sea distinguible de un extractor
    roto: si el walker estuviera muerto, este self-test daría conjuntos vacíos y
    el censo entero sería un verde que no inspeccionó nada (P-02).
    """
    matriz = collect_paths(_SELFTEST_MATRIZ, _MATRIZ_KEYS)
    _report("selftest-matriz", "synthetic", matriz)
    iol = collect_paths(_SELFTEST_IOL, _IOL_KEYS)
    _report("selftest-iol", "synthetic", iol)

    expected_matriz = {
        "segments[].marketId": {"ROFX"},
        "instruments[].instrumentId.marketId": {"ROFX"},
        "instruments[].cficode": {"FXXXSX", "ZZZZZZ"},
        "orders[].ordType": {"LIMIT", "MARKET"},
        "details[].currency": {"ARS"},
        "details[].orderTypes[]": {"LIMIT", "MARKET"},
    }
    expected_iol = {
        "titulos[].mercado": {"bCBA", "bcba"},
        "titulos[].plazo": {"t1", "t2"},
    }
    ok = True
    for expected, got in ((expected_matriz, matriz), (expected_iol, iol)):
        for path, values in expected.items():
            observed = {value for _, value in got.get(path, [])}
            if observed != values:
                print(f"SELFTEST FAIL {path}: {sorted(observed)} != {sorted(values)}")
                ok = False

    # Criterio 3, offline: el encabezado lleva el venue MEDIDO y un timestamp, y
    # reafirma el D-lock (b). Se ejercita con un token sintético para que la
    # cobertura no dependa de red ni de credenciales.
    header = _census_header_lines("venue-sintetico")
    if not header[0].startswith("CENSUS-HEADER venue=venue-sintetico captured_at="):
        print(f"SELFTEST FAIL header: {header[0]!r} no abre con venue y captured_at")
        ok = False
    if not any(line.startswith("CENSUS-DLOCK") for line in header):
        print("SELFTEST FAIL header: falta la línea CENSUS-DLOCK")
        ok = False

    # Criterio 1, offline: el gate resuelve por igualdad exacta de hostname y el
    # sufijo hostil cae fail-closed. Sólo se imprime el TOKEN observado, nunca la
    # entrada (T-39-04).
    for probe, expected_token in (
        ("api.bbsa.matrizoms.com.ar", "bbsa"),
        ("api.bbsa.matrizoms.com.ar.attacker.example", None),
    ):
        observed_token = _venue_token(probe)
        if observed_token != expected_token:
            print(f"SELFTEST FAIL venue: token {observed_token!r} != {expected_token!r}")
            ok = False

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ----------------------------------------------------------------------


def main(argv: list[str]) -> int:
    """Corre el censo (o el self-test offline con ``--selftest``)."""
    if "--selftest" in argv:
        return _selftest()
    if "--matriz-only" in argv:
        # Retorno TEMPRANO a propósito: caer al ``return 0 if (ran_matriz and
        # ran_iol)`` de abajo daría exit 1 en una corrida exitosa, porque iol no fue
        # pedido y su flag quedaría en ``False``. El veredicto de iol se reporta como
        # NOT-REQUESTED, que no es lo mismo que SKIPPED.
        ran_matriz = census_matriz()
        print(
            f"CENSUS: matriz={'RAN' if ran_matriz else 'SKIPPED'} iol=NOT-REQUESTED (--matriz-only)"
        )
        return 0 if ran_matriz else 1
    ran_matriz = census_matriz()
    ran_iol = census_iol()
    print(
        f"CENSUS: matriz={'RAN' if ran_matriz else 'SKIPPED'} iol={'RAN' if ran_iol else 'SKIPPED'}"
    )
    return 0 if (ran_matriz and ran_iol) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
