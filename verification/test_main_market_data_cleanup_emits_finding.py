"""D-08 / T-27-23 guard — un cleanup fallido EMITE un finding, nunca se traga.

Los probes destructivos de ``main_market_data.py`` crean estado en una
infraestructura compartida (develop) y lo revierten en un ``finally``. Si ese
revert falla y el fallo se suprime, develop queda con estado huérfano y **no
queda registro de ello en ninguna parte**: el driver reporta PASS, el sweep
terminal no sabe qué perseguir y el próximo operador se encuentra el residuo sin
explicación. Repudiation, textual.

El driver YA tiene dos ``finally`` con ``contextlib.suppress(Exception)``
(``client.close()`` y ``await aclient.aclose()``). Esos son legítimos: cierran un
transporte local, no dejan estado remoto huérfano. Aplicar el mismo idiom al
cleanup de estado CREADO es lo que este guard prohíbe.

Para cada probe cuyo nombre lo marca como probe de mutación, cada ``finally``
que posea debe:

* contener una llamada al emisor de findings de cleanup (o a ``append_finding``);
* NO contener ningún context manager que se trague errores; y
* capturar la excepción del cleanup en su propio ``try/except``, para que un
  cleanup fallido tampoco escape del probe.

El guard afirma además su propia no-vacuidad: si el patrón de nombres dejara de
matchear (un rename, un typo), el test falla RED en vez de pasar sin mirar nada.

Nota de interacción con ``test_main_market_data_postprocess_guarded.py``: ese
guard sólo considera protegidas las llamadas dentro del **body** de un ``try``,
así que en un ``finally`` NO puede haber ``_emit_shape`` ni
``_write_schema_snapshot``. ``_emit_cleanup_finding`` no es un post-proceso de
shape y no está en su lista.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_market_data.py"

# Marcadores en el nombre de un ``probe_*`` que lo identifican como probe que
# ESCRIBE en develop (y por lo tanto tiene estado que revertir). Los de calendar
# se listan desde ya para cubrir el plan 27-05.
_MUTATION_PROBE_MARKERS = (
    "create_symbol",
    "create_symbols",
    "update_symbol",
    "add_holiday",
    "delete_holiday",
    "set_calendar_config",
    "preview_calendar_config",
)

# Emisores aceptables dentro de un ``finally`` de cleanup.
_CLEANUP_EMITTERS = frozenset({"_emit_cleanup_finding", "append_finding"})

# Context managers que se tragan excepciones — prohibidos en un ``finally`` de
# cleanup de estado remoto.
_SWALLOWING_CMS = frozenset({"suppress"})


def _driver_tree() -> ast.Module:
    return ast.parse((_REPO_ROOT / _DRIVER).read_text(encoding="utf-8"))


def _called_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _mutation_probes() -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = _driver_tree()
    out: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not node.name.startswith("probe_"):
            continue
        if any(marker in node.name for marker in _MUTATION_PROBE_MARKERS):
            out.append(node)
    return out


def _finally_blocks(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[tuple[int, list[ast.stmt]]]:
    """``[(lineno del try, sentencias del finalbody)]`` de cada ``try`` con ``finally``."""
    return [
        (node.lineno, node.finalbody)
        for node in ast.walk(func)
        if isinstance(node, ast.Try) and node.finalbody
    ]


def test_mutation_probe_finally_blocks_emit_a_finding() -> None:
    """Todo ``finally`` de un probe de mutación emite un finding de cleanup (D-08)."""
    probes = _mutation_probes()
    checked = 0
    silent: list[tuple[str, int]] = []

    for func in probes:
        for lineno, finalbody in _finally_blocks(func):
            checked += 1
            emits = any(
                isinstance(inner, ast.Call) and _called_name(inner) in _CLEANUP_EMITTERS
                for stmt in finalbody
                for inner in ast.walk(stmt)
            )
            if not emits:
                silent.append((func.name, lineno))

    assert not silent, (
        f"{_DRIVER}: ``finally`` de probe de mutación que NO emite ningún finding "
        f"(D-08 / T-27-23): {silent}. Un cleanup fallido debe dejar registro; "
        f"usá _emit_cleanup_finding."
    )
    assert checked >= 1, (
        f"{_DRIVER}: no se inspeccionó ningún ``finally`` de probe de mutación "
        f"(probes matcheados: {[f.name for f in probes]}). El guard sería vacuo."
    )


def test_mutation_probe_finally_blocks_swallow_nothing() -> None:
    """Ningún ``finally`` de un probe de mutación usa un context manager supresor."""
    swallowers: list[tuple[str, int, str]] = []

    for func in _mutation_probes():
        for lineno, finalbody in _finally_blocks(func):
            for stmt in finalbody:
                for inner in ast.walk(stmt):
                    if isinstance(inner, ast.With | ast.AsyncWith):
                        for item in inner.items:
                            ctx = item.context_expr
                            if isinstance(ctx, ast.Call) and _called_name(ctx) in _SWALLOWING_CMS:
                                swallowers.append((func.name, lineno, ast.unparse(ctx)))

    assert not swallowers, (
        f"{_DRIVER}: cleanup de estado remoto envuelto en un supresor de errores "
        f"(D-08): {swallowers}. El idiom ``contextlib.suppress`` sólo es legítimo para "
        f"cerrar transportes locales (client.close / aclient.aclose)."
    )


def test_mutation_probe_cleanup_catches_its_own_failure() -> None:
    """El cleanup vive en su propio ``try/except`` dentro del ``finally``.

    Sin ese ``except``, un cleanup fallido se propagaría FUERA del probe, saltando
    su escalera D-09 y degradando el run entero al guard de nivel driver.
    """
    uncaught: list[tuple[str, int]] = []

    for func in _mutation_probes():
        for lineno, finalbody in _finally_blocks(func):
            catches = any(
                isinstance(inner, ast.Try) and inner.handlers
                for stmt in finalbody
                for inner in ast.walk(stmt)
            )
            if not catches:
                uncaught.append((func.name, lineno))

    assert not uncaught, (
        f"{_DRIVER}: ``finally`` de cleanup sin ``try/except`` propio: {uncaught}. "
        f"Un fallo ahí escaparía del probe (D-09)."
    )


def test_cleanup_guard_is_not_vacuous() -> None:
    """El patrón de nombres matchea probes reales y el emisor de cleanup existe."""
    tree = _driver_tree()
    probes = _mutation_probes()

    assert probes, (
        f"{_DRIVER}: el patrón {_MUTATION_PROBE_MARKERS} no matcheó ningún ``probe_*``. "
        f"O se renombraron los probes destructivos o el patrón tiene un typo — en "
        f"cualquiera de los dos casos este guard dejó de vigilar algo."
    )

    with_finally = [f.name for f in probes if _finally_blocks(f)]
    assert with_finally, (
        f"{_DRIVER}: ningún probe de mutación tiene ``finally``; el ciclo "
        f"create -> verify -> revert no estaría cerrando nada (D-05). "
        f"Probes matcheados: {[f.name for f in probes]}"
    )

    defined = {
        n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    assert "_emit_cleanup_finding" in defined, (
        f"{_DRIVER} debe definir _emit_cleanup_finding: es el emisor que reemplaza el "
        f"idiom de supresión en el cleanup de estado creado (D-08)."
    )
