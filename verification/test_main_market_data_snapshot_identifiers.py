"""D-17 / T-27-29 guard — ningún payload de mutación puede derivar un baseline de lectura.

``_write_schema_snapshot`` es write-once y content-addressed por su
``client_function``: el nombre determina el archivo
(``.planning/verification/schemas/market-data-client/<nombre>.json``). Si un probe
de MUTACIÓN —o una lectura de verificación FILTRADA, que devuelve un
sub-conjunto— reusara el ``client_function`` de un probe de lectura, ocurriría
una de dos cosas, ambas malas:

* con baseline ya commiteado, el payload distinto emite un finding ``SHAPE`` que
  parece drift del servidor y no lo es; o
* sin baseline, lo ESCRIBE con la shape equivocada, y a partir de ahí toda
  corrida futura compara la lectura real contra el molde de una escritura.

En cualquiera de los dos casos el baseline deja de detectar drift real: un
false-positive permanente o un false-negative permanente.

Los **nueve identificadores de lectura** de :data:`_READ_IDENTIFIERS` sí aparecen
DOS veces cada uno, y es deliberado desde Phase 23: sync y async leen el MISMO
endpoint y comparten una única baseline —esa baseline es la fuente de verdad del
endpoint, no de la superficie—. Todo lo demás debe ser único y disjunto de ese
conjunto.
"""

from __future__ import annotations

import ast
import collections
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_market_data.py"

# Identificadores de los probes de LECTURA (Phase 23). Comparten baseline entre
# superficies a propósito, así que pueden aparecer exactamente dos veces: una en
# el probe sync y otra en su espejo async.
_READ_IDENTIFIERS = frozenset(
    {
        "get_health",
        "get_health_feed",
        "get_market_data",
        "get_latest",
        "get_instruments",
        "get_segments",
        "get_symbols",
        "get_calendar",
        "get_calendar_config",
    }
)

# Piso de no-vacuidad: el driver captura como mínimo los 9 identificadores de
# lectura (x2 superficies) más los de mutación de los planes 27-04 y 27-05.
_MIN_IDENTIFIERS = 25


def _snapshot_identifiers() -> list[str]:
    """Todo literal pasado como ``client_function=`` en el driver, con repeticiones."""
    tree = ast.parse((_REPO_ROOT / _DRIVER).read_text(encoding="utf-8"))
    return [
        kw.value.value
        for call in ast.walk(tree)
        if isinstance(call, ast.Call)
        for kw in call.keywords
        if kw.arg == "client_function"
        and isinstance(kw.value, ast.Constant)
        and isinstance(kw.value.value, str)
    ]


def test_non_read_snapshot_identifiers_are_unique() -> None:
    """Cada identificador que NO es de lectura aparece exactamente una vez (D-17)."""
    counts = collections.Counter(_snapshot_identifiers())
    dupes = sorted(
        f"{name} (x{n})" for name, n in counts.items() if name not in _READ_IDENTIFIERS and n > 1
    )

    assert not dupes, (
        f"{_DRIVER}: identificador de snapshot duplicado fuera del conjunto de lecturas "
        f"compartidas: {dupes}. Dos probes escribiendo el MISMO archivo se pisan el "
        f"baseline mutuamente, o peor: una superficie emite un finding SHAPE contra el "
        f"payload de la otra (D-17 / T-27-29)."
    )


def test_read_snapshot_identifiers_are_shared_only_across_surfaces() -> None:
    """Los identificadores de lectura aparecen a lo sumo dos veces: sync + async."""
    counts = collections.Counter(_snapshot_identifiers())
    over_shared = sorted(
        f"{name} (x{n})" for name, n in counts.items() if name in _READ_IDENTIFIERS and n > 2
    )

    assert not over_shared, (
        f"{_DRIVER}: identificador de lectura usado más de dos veces: {over_shared}. "
        f"Compartir baseline entre sync y async es deliberado (la baseline pertenece al "
        f"ENDPOINT); una tercera aparición significa que un probe distinto —típicamente "
        f"una lectura FILTRADA de verificación— se colgó de la baseline sin filtrar."
    )


def test_mutation_probes_never_reuse_a_read_identifier() -> None:
    """Ningún probe de mutación reusa un ``client_function`` de lectura (D-17).

    Se afirma estructuralmente, no por conteo: la lista de identificadores que
    cada ``probe_*`` de mutación pasa a ``_write_schema_snapshot`` debe ser
    disjunta de :data:`_READ_IDENTIFIERS`.
    """
    tree = ast.parse((_REPO_ROOT / _DRIVER).read_text(encoding="utf-8"))
    offenders: list[tuple[str, str]] = []
    markers = ("create_symbol", "update_symbol", "preview_calendar", "holiday")

    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not func.name.startswith("probe_") or not any(m in func.name for m in markers):
            continue
        for call in ast.walk(func):
            if not isinstance(call, ast.Call):
                continue
            for kw in call.keywords:
                if (
                    kw.arg == "client_function"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value in _READ_IDENTIFIERS
                ):
                    offenders.append((func.name, str(kw.value.value)))

    assert not offenders, (
        f"{_DRIVER}: probe de mutación snapshoteando bajo un identificador de LECTURA: "
        f"{offenders}. El body de una escritura derivaría —o directamente escribiría— la "
        f"baseline de un endpoint de lectura (D-17 / T-27-29)."
    )


def test_snapshot_identifier_guard_is_not_vacuous() -> None:
    """Hay identificadores que vigilar y los de lectura declarados existen de verdad."""
    identifiers = _snapshot_identifiers()

    assert len(identifiers) >= _MIN_IDENTIFIERS, (
        f"{_DRIVER}: sólo {len(identifiers)} usos de client_function (piso "
        f"{_MIN_IDENTIFIERS}); el driver pudo haber sido vaciado y este guard pasaría "
        f"sin mirar nada."
    )
    missing = sorted(_READ_IDENTIFIERS - set(identifiers))
    assert not missing, (
        f"{_DRIVER}: identificadores de lectura declarados en el guard pero ausentes del "
        f"driver: {missing}. Si se renombraron, actualizá _READ_IDENTIFIERS — si no, el "
        f"guard estaría exceptuando nombres que ya nadie usa."
    )
