"""Gate de cobertura del decorador: los 130 probes de los cinco drivers lo cargan.

El criterio 1 de la Phase 33 pide que **toda** divergencia de decode capturada en
vivo llegue al findings file cargando el endpoint y la superficie de la llamada
que la produjo. Ese contexto no viaja en el record congelado de seis claves: lo
bindea ``verification.divergences.probe_context`` alrededor de cada probe. Un
probe sin decorar sigue corriendo, sigue emitiendo su record y sigue produciendo
un finding — pero con ``endpoint="-"`` y ``surface="-"``, es decir un finding que
no se puede rutear al sitio de decode que lo originó. Y como el título ES la
clave de dedupe cross-run, dos divergencias distintas de dos superficies distintas
se colapsan en una.

Por qué existe este archivo y no basta con la inspección de cada plan: el cableado
se repartió entre cuatro planes (33-01 higyrus, 33-02 matriz+higyrus, 33-03
iol+ámbito, 33-04 market-data). Cada uno puede terminar creyendo que cubrió su
parte mientras otro dejó un driver a medias, y nadie mira el total. Este gate es
el único lugar del repo donde los cinco drivers se cuentan juntos.

**No es vacuo por construcción.** Tres capas:

1. Un piso numérico por driver (``_EXPECTED_PROBE_COUNT``) y un total de 130. Si
   alguien renombra probes hacia afuera del prefijo ``probe_``, el walker deja de
   verlos y el conteo cae por debajo del piso en vez de pasar con cero probes.
2. La superficie declarada tiene que coincidir con el sufijo ``_sync`` / ``_async``
   del nombre de la función — 89 de los 130 probes lo llevan, y ese subconjunto
   también tiene su propio piso, así que la aserción de superficie no puede
   volverse vacía borrando sufijos.
3. Los probes de paridad (``*_sync_async``) son la única exención, y está escrita
   como un allowlist explícito por nombre: un probe nuevo no puede entrar a la
   exención sin editar este archivo.

**Alcance:** ``verification/`` no corre en CI (ver ``33-BASELINE.md``); esto es un
gate local de fase. Su valor no es bloquear un merge sino impedir que los planes
33-02/33-03/33-04 se den por terminados mientras un driver quedó sin cablear, y
que un plan futuro agregue un probe sin decorar sin que nada se entere.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Los cinco drivers verificables de la fase. `main_wallets.py` no está: el
# paquete wallets no es uno de los cinco tipados que emiten records de decode.
_DRIVERS = [
    "main_ambito_financiero.py",
    "main_higyrus.py",
    "main_iol.py",
    "main_market_data.py",
    "main_matriz.py",
]

# Piso numérico por driver — medido en el momento en que los cinco quedaron
# cableados (33-04). Es un piso, no una igualdad hacia abajo: agregar probes es
# legítimo y no rompe el gate; perderlos, no.
_EXPECTED_PROBE_COUNT = {
    "main_ambito_financiero.py": 7,
    "main_higyrus.py": 19,
    "main_iol.py": 15,
    "main_market_data.py": 43,
    "main_matriz.py": 46,
}

# 7 + 19 + 15 + 43 + 46 = 130 probes en total.
_TOTAL_EXPECTED_PROBES = 130

# Piso del subconjunto que lleva sufijo de superficie en el nombre. Sin este
# número, borrar todos los sufijos volvería vacua la aserción de superficie.
_EXPECTED_SUFFIXED_COUNT = {
    "main_ambito_financiero.py": 2,
    "main_higyrus.py": 14,
    "main_iol.py": 10,
    "main_market_data.py": 40,
    "main_matriz.py": 23,
}

_DECORATOR_NAME = "probe_context"

# Las tres superficies que el harness reconoce. ``both`` la usan los dos probes
# de market-data que no hacen ninguna llamada en vivo y comparan las dos
# superficies desde adentro (33-04).
_VALID_SURFACES = frozenset({"sync", "async", "both"})

# Única exención de la regla sufijo -> superficie, escrita por nombre completo.
# Un probe de paridad termina en ``_sync_async`` porque compara las dos
# superficies dentro de una sola llamada; su superficie declarada es la de la
# llamada que efectivamente hace primero. Que la exención sea un allowlist y no
# un patrón es deliberado: un probe nuevo no puede entrar sin editar este archivo.
_PARITY_PROBES = frozenset(
    {
        "probe_parity_sync_async",  # ámbito, higyrus, iol
    }
)


def _probe_defs(driver: str) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Todas las defs ``probe_*`` del driver, sync y ``async def`` por igual."""
    tree = ast.parse((_REPO_ROOT / driver).read_text(encoding="utf-8"))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name.startswith("probe_")
    ]


def _probe_context_call(node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.Call | None:
    """El ``ast.Call`` de ``@probe_context(...)`` en el decorator_list, o ``None``.

    Sólo acepta la forma llamada con paréntesis: ``probe_context`` es una factory
    de decoradores, así que un ``@probe_context`` pelado sería un bug de todos
    modos y no debe contar como cobertura.
    """
    for decorator in node.decorator_list:
        if (
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Name)
            and decorator.func.id == _DECORATOR_NAME
        ):
            return decorator
    return None


def _surface_literal(call: ast.Call) -> str | None:
    """El literal del kwarg ``surface=`` del decorador, o ``None`` si no es literal."""
    for keyword in call.keywords:
        if keyword.arg == "surface" and isinstance(keyword.value, ast.Constant):
            value = keyword.value.value
            return value if isinstance(value, str) else None
    return None


def _expected_surface(name: str) -> str | None:
    """Superficie que el sufijo del nombre obliga, o ``None`` si no obliga ninguna."""
    if name in _PARITY_PROBES:
        return None
    if name.endswith("_async"):
        return "async"
    if name.endswith("_sync"):
        return "sync"
    return None


@pytest.mark.parametrize("driver", _DRIVERS)
def test_every_probe_carries_probe_context(driver: str) -> None:
    """Todo ``probe_*`` del driver lleva ``@probe_context(...)`` con superficie válida.

    Las cuatro aserciones son independientes y cada una cierra un modo de falla
    distinto: sin decorador el finding pierde su ruteo; sin piso el gate pasa con
    cero probes; sin superficie válida el título de dedupe queda incompleto; sin
    match de sufijo un probe async puede declararse ``sync`` y colapsar dos
    divergencias distintas bajo un mismo título.
    """
    probes = _probe_defs(driver)

    expected_count = _EXPECTED_PROBE_COUNT[driver]
    assert len(probes) >= expected_count, (
        f"{driver} expone {len(probes)} probes, por debajo del piso {expected_count} "
        f"medido cuando los cinco drivers quedaron cableados (33-04). Un conteo que "
        f"cae no es 'menos trabajo': significa que el walker dejó de ver probes que "
        f"sí corren, y este gate pasaría verde sobre un driver sin inspeccionar."
    )

    undecorated = [node.name for node in probes if _probe_context_call(node) is None]
    assert not undecorated, (
        f"{driver} tiene {len(undecorated)} probe(s) sin @{_DECORATOR_NAME}: "
        f"{undecorated}. Un probe sin decorar sigue emitiendo su record de decode, "
        f"pero el finding sale con endpoint='-' y surface='-': no se puede rutear al "
        f"sitio que lo produjo, y como el título es la clave de dedupe cross-run, dos "
        f"divergencias de dos superficies distintas se colapsan en una."
    )

    bad_surfaces = [
        (node.name, _surface_literal(call))
        for node in probes
        if (call := _probe_context_call(node)) is not None
        and _surface_literal(call) not in _VALID_SURFACES
    ]
    assert not bad_surfaces, (
        f"{driver} declara superficies fuera de {sorted(_VALID_SURFACES)}: "
        f"{bad_surfaces}. La superficie va DENTRO del título del finding "
        f"(convención lockeada `surface-in-title-write-new`, 33-01), así que un "
        f"valor no literal o desconocido corrompe la identidad de dedupe."
    )

    suffixed = [node for node in probes if _expected_surface(node.name) is not None]
    suffix_floor = _EXPECTED_SUFFIXED_COUNT[driver]
    assert len(suffixed) >= suffix_floor, (
        f"{driver} tiene {len(suffixed)} probes con sufijo de superficie, por debajo "
        f"del piso {suffix_floor}. Sin ese piso, borrar los sufijos volvería vacua la "
        f"aserción de coincidencia que sigue."
    )

    mismatched = [
        (node.name, _surface_literal(call), _expected_surface(node.name))
        for node in probes
        if (call := _probe_context_call(node)) is not None
        and (expected := _expected_surface(node.name)) is not None
        and _surface_literal(call) != expected
    ]
    assert not mismatched, (
        f"{driver} declara una superficie que contradice el sufijo del nombre "
        f"(nombre, declarada, esperada): {mismatched}. La superficie declarada es la "
        f"que viaja al título; si miente, el finding atribuye la divergencia a la "
        f"superficie equivocada y el par sync/async deja de ser distinguible."
    )


def test_total_probe_coverage_is_one_hundred_and_thirty() -> None:
    """El total de los cinco drivers alcanza los 130 probes decorados.

    Los pisos por driver ya cubren el caso 'un driver se vació'. Este total cubre
    el caso que ningún test por-driver puede ver: que un driver desaparezca de
    ``_DRIVERS``. La lista se afirma explícitamente para que quitarle una entrada
    enrojezca acá y no reduzca silenciosamente el alcance del gate.
    """
    assert len(_DRIVERS) == 5, (
        f"_DRIVERS tiene {len(_DRIVERS)} entradas; el gate cubre los cinco drivers "
        f"verificables de la fase y quitar uno reduce el alcance sin que nada falle."
    )

    total = 0
    for driver in _DRIVERS:
        probes = _probe_defs(driver)
        decorated = [node for node in probes if _probe_context_call(node) is not None]
        assert len(decorated) == len(probes), (
            f"{driver}: {len(probes) - len(decorated)} probe(s) sin decorar"
        )
        total += len(decorated)

    assert total >= _TOTAL_EXPECTED_PROBES, (
        f"los cinco drivers suman {total} probes decorados, por debajo de los "
        f"{_TOTAL_EXPECTED_PROBES} que quedaron cableados al cierre de 33-04. "
        f"El censo en vivo de 33-05 se cuenta sobre esta población: si encoge, "
        f"el censo encoge con ella y el resultado se lee como 'menos divergencias' "
        f"en vez de como 'menos inspección'."
    )
