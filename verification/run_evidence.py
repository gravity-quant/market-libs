"""Sobre de evidencia de corrida por paquete (Phase 39 — D-09 + D-10).

Por qué existe
--------------

Los cuatro drivers en alcance de esta fase cierran su corrida con una línea
``SUMMARY: ... DIVERGENCES=N ...`` donde ``N`` es ``len(handler.seen)``. Eso es
un **conteo**. Los miembros —las 4-tuplas ``(slug, model, field_path, kind)`` que
``DivergenceHandler.seen`` acumula y que su docstring declara *la unidad del
censo*— no se persisten en ningún lado: viven en memoria y mueren con el
proceso. La diferencia de conjuntos que el censo exige contra el censo de la
fase anterior es, por eso, hoy literalmente incomputable: se puede comparar
``N`` con ``M``, pero no se puede decir *qué* triple apareció ni *cuál*
desapareció. Este módulo persiste los miembros.

Por qué es seguro versionarlo
-----------------------------

Una triple es ``(slug, model, field_path, kind)``: el nombre del paquete, el
nombre de una clase de modelo, la ruta de un campo dentro de ese modelo, y la
especie de divergencia. Cuatro piezas de **metadata de tipo**. Las cuatro ya
aparecen verbatim dentro de los títulos de los findings committeados que
``DivergenceHandler.emit`` escribe (``f"{model}{path}: {kind} ..."``). El sobre
no lleva ningún valor de wire, ninguna base URL, ningún hostname y ninguna
credencial — y el set de claves está pineado por un test para que agregar un
campo que transporte payload no pase inadvertido (T-39-10).

Por qué el predicado de no-vacuidad es el conteo de PROBES
----------------------------------------------------------

``verify_cycle_closure(pkg)`` devuelve ``(True, [])`` tanto cuando todo está
enlazado como cuando el archivo de findings ni siquiera existe: el PASS vacuo.
La tentación es endurecerlo exigiendo *"al menos un finding CONFIRMED/FIXED"* —
que es lo que hace ``main_market_data.py``. Ese predicado es **incorrecto** para
los otros cuatro paquetes: ámbito declara cero clases de modelo (su cero de
divergencias es estructural y está medido) y higyrus nunca pudo medirse. Un
criterio basado en findings promovidos reprobaría a los dos, uno por estar
limpio y el otro por no haber corrido — dos causas opuestas con el mismo
veredicto. El criterio correcto es **evidencia positiva de corrida**: cuántos
probes ejecutó el driver. Cero probes es "no corrió"; N probes con cero findings
es "corrió y está limpio".

Uso::

    from verification.run_evidence import write_run_evidence, probes_executed

    write_run_evidence(
        "iol-client",
        driver="main_iol.py",
        triples=sorted(handler.seen),
        counts={"PASS": n_pass, "FAIL": n_fail, ...},
    )
    probes_executed("iol-client")   # -> 15

El artefacto vive en ``.planning/verification/run-evidence/<slug>.json`` y se
**reescribe** en cada corrida: describe LA ÚLTIMA, así que una corrida saltada
invalida el sobre anterior en vez de dejarlo en pie (T-39-12).
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

# La guarda de forma de slug se REUTILIZA, no se re-escribe: un segundo regex es
# una segunda superficie que puede divergir del original y aflojarse sin que
# nadie lo note (T-39-09).
from verification.findings import _validate_pkg_slug

__all__ = [
    "probes_executed",
    "read_run_evidence",
    "run_evidence_path",
    "write_run_evidence",
]

# Raíz del repo = el directorio que contiene el paquete ``verification/``. El
# directorio destino se deriva de ``__file__``, NUNCA de un input.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_RUN_EVIDENCE_DIR = _REPO_ROOT / ".planning" / "verification" / "run-evidence"


def run_evidence_path(slug: str) -> Path:
    """Ruta del sobre de ``slug``: ``.planning/verification/run-evidence/<slug>.json``.

    Valida ``slug`` con el mismo validador que :mod:`verification.findings`
    (``ValueError`` si no matchea), así que no puede resolver fuera del
    directorio de artefactos.
    """
    _validate_pkg_slug(slug)
    return _RUN_EVIDENCE_DIR / f"{slug}.json"


def write_run_evidence(
    slug: str,
    *,
    driver: str,
    triples: Iterable[tuple[str, str, str, str]],
    counts: Mapping[str, int],
    skipped: str | None = None,
) -> Path:
    """Escribe (reemplazando) el sobre de evidencia de ``slug`` y devuelve su ruta.

    Args:
        slug: slug del paquete (``iol-client``, ``matriz-client``, ...).
        driver: nombre del driver que produjo la corrida (``main_iol.py``).
        triples: las 4-tuplas de ``DivergenceHandler.seen``. Se deduplican y se
            ordenan: la salida es determinística aunque la entrada sea un
            ``set``, cuyo orden de iteración varía entre procesos.
        counts: conteos por estado de probe. Su suma es ``probes_executed``.
        skipped: causa medida + destino nombrado si la corrida NO ocurrió; en
            ese caso ``triples`` y ``counts`` van vacíos. ``None`` si corrió.

    El sobre **reemplaza** cualquier contenido anterior. Esa es la propiedad que
    impide que un sobre viejo se lea como evidencia de esta corrida (T-39-12).
    """
    path = run_evidence_path(slug)

    ordered = sorted({tuple(str(part) for part in triple) for triple in triples})
    counted = {str(k): int(v) for k, v in counts.items()}

    envelope: dict[str, Any] = {
        "slug": slug,
        "driver": driver,
        "captured_at": dt.datetime.now(dt.UTC).isoformat(),
        "counts": counted,
        "probes_executed": sum(counted.values()),
        "n_triples": len(ordered),
        "triples": [list(triple) for triple in ordered],
        "skipped": skipped,
    }

    _RUN_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def read_run_evidence(slug: str) -> dict[str, Any] | None:
    """Devuelve el sobre de ``slug``, o ``None`` si no existe o no parsea.

    Nunca lanza por un archivo ausente, ilegible o con JSON corrupto: un sobre
    que no se puede leer es *ausencia de evidencia*, y el consumidor ya trata la
    ausencia como "no corrió". Un ``ValueError`` acá abortaría el loop de cierre
    de ciclo a mitad de camino y dejaría a los paquetes restantes sin veredicto.

    (``slug`` sí se valida: un slug fuera de forma es un bug del llamador, no un
    estado del disco.)
    """
    path = run_evidence_path(slug)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    return raw


def probes_executed(slug: str) -> int:
    """Cuántos probes ejecutó la última corrida de ``slug``. ``0`` si no hay sobre.

    Este entero ES el predicado de no-vacuidad del cierre de ciclo: ``0``
    significa "el driver no corrió" y nunca puede promover un ``PASS``. Un valor
    no entero en el sobre (edición manual, archivo truncado) también devuelve
    ``0`` — el fail-closed es hacia SKIPPED, nunca hacia PASS.
    """
    envelope = read_run_evidence(slug)
    if envelope is None:
        return 0
    value = envelope.get("probes_executed")
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value
