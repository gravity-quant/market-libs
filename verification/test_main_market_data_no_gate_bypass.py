"""T-27-20 guard — ningún spec de MUTACIÓN puede llegar al dispatch SIN gate.

``main_market_data.py`` tiene dos familias de helpers de dispatch crudo:

* ``_raw_via_request_sync`` / ``_raw_via_request_async`` llaman
  ``client._request(spec)`` **directamente**, y ``_request``
  (``packages/market-data-client/src/market_data_client/client.py``) NO invoca
  ``_ensure_mutation_allowed()``. Son correctos para LECTURAS y sólo para
  lecturas.
* ``_mutate_raw_sync`` / ``_mutate_raw_async`` chequean el gate PRIMERO y recién
  después despachan.

Pasarle un spec construido por un builder de escritura a la primera familia
dispararía una escritura real **bypasseando el gate** — con el gate posiblemente
cerrado, contra el host que sea. Es una elevación de privilegio, y es la trampa
más fácil de reintroducir de toda la fase porque las dos familias tienen la misma
firma.

Este guard camina el AST del driver y afirma, en positivo y en negativo:

1. ningún argumento de un helper SIN gate proviene de un builder de mutación
   (ni por anidamiento directo ni vía una variable local asignada desde uno);
2. los dos helpers CON gate existen y llaman ``_ensure_mutation_allowed`` antes
   de su dispatch;
3. el guard no es vacuo (los builders de mutación y los helpers sin gate siguen
   existiendo y siendo usados);
4. los identificadores de prueba comparten el prefijo auditable y son estables.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_market_data.py"

# Builders de ESCRITURA de ``market_data_client._core``. Los tres de symbols los
# usa el plan 27-04; los de calendar los usa el 27-05 — se listan desde ya para
# que el guard cubra esa ola sin tener que acordarse de ampliarlo.
_MUTATION_BUILDERS = frozenset(
    {
        "build_create_symbol_request",
        "build_create_symbols_request",
        "build_update_symbol_request",
        "build_set_calendar_config_request",
        "build_preview_calendar_config_request",
        "build_add_holidays_request",
        "build_delete_calendar_config_request",
        "build_delete_holiday_request",
    }
)

# Helpers que despachan SIN chequear el gate (correctos sólo para lecturas).
_UNGATED_DISPATCH = frozenset({"_raw_via_request_sync", "_raw_via_request_async"})

# Helpers que chequean el gate antes de despachar.
_GATED_DISPATCH = ("_mutate_raw_sync", "_mutate_raw_async")

_GATE_CALL = "_ensure_mutation_allowed"
_DISPATCH_CALL = "_request"

# Constantes de identificadores de prueba (D-05). El prefijo es lo que hace
# barrible el residuo permanente.
_PREFIX_CONST = "_PROBE_PREFIX"
_EXPECTED_PREFIX = "GSDPROBE/"
_SYNC_SYMBOL_CONSTS = ("_SYM_SYNC", "_SYM_SYNC_B1", "_SYM_SYNC_B2")
_ASYNC_SYMBOL_CONSTS = ("_SYM_ASYNC", "_SYM_ASYNC_B1", "_SYM_ASYNC_B2")


def _driver_tree() -> ast.Module:
    return ast.parse((_REPO_ROOT / _DRIVER).read_text(encoding="utf-8"))


def _called_name(node: ast.Call) -> str | None:
    """Nombre invocado de un ``Call``: ``f(...)`` -> ``f``; ``m.f(...)`` -> ``f``."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _functions(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]


def _mutation_tainted_locals(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Nombres locales asignados (directa o indirectamente) desde un builder de mutación."""
    tainted: set[str] = set()
    # Dos pasadas: cubre ``spec = build_x(...)`` y luego ``other = spec``.
    for _ in range(2):
        for node in ast.walk(func):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            value = node.value
            derives = any(
                isinstance(inner, ast.Call) and _called_name(inner) in _MUTATION_BUILDERS
                for inner in ast.walk(value)
            ) or any(
                isinstance(inner, ast.Name) and inner.id in tainted for inner in ast.walk(value)
            )
            if derives:
                tainted.add(target.id)
    return tainted


def test_no_mutation_spec_reaches_an_ungated_dispatch_helper() -> None:
    """Ningún ``_raw_via_request_*`` recibe un spec derivado de un builder de escritura."""
    tree = _driver_tree()
    offenders: list[tuple[str, str, int]] = []

    for func in _functions(tree):
        tainted = _mutation_tainted_locals(func)
        for node in ast.walk(func):
            if not isinstance(node, ast.Call):
                continue
            if _called_name(node) not in _UNGATED_DISPATCH:
                continue
            args: list[ast.expr] = [*node.args, *(kw.value for kw in node.keywords)]
            for arg in args:
                from_builder = any(
                    isinstance(inner, ast.Call) and _called_name(inner) in _MUTATION_BUILDERS
                    for inner in ast.walk(arg)
                )
                from_tainted = any(
                    isinstance(inner, ast.Name) and inner.id in tainted for inner in ast.walk(arg)
                )
                if from_builder or from_tainted:
                    offenders.append((func.name, ast.unparse(arg), node.lineno))

    assert not offenders, (
        f"{_DRIVER}: spec de MUTACIÓN despachado por un helper SIN gate "
        f"(bypass de _ensure_mutation_allowed, T-27-20): {offenders}. "
        f"Usá _mutate_raw_sync / _mutate_raw_async."
    )


def test_gated_dispatch_helpers_check_the_gate_before_dispatching() -> None:
    """``_mutate_raw_*`` existen y llaman ``_ensure_mutation_allowed`` antes de ``_request``."""
    tree = _driver_tree()
    by_name = {f.name: f for f in _functions(tree)}

    for helper in _GATED_DISPATCH:
        assert helper in by_name, (
            f"{_DRIVER} debe definir {helper}: es la ÚNICA ruta de mutación permitida "
            f"desde el driver."
        )
        func = by_name[helper]
        gate_lines = [
            n.lineno
            for n in ast.walk(func)
            if isinstance(n, ast.Call) and _called_name(n) == _GATE_CALL
        ]
        dispatch_lines = [
            n.lineno
            for n in ast.walk(func)
            if isinstance(n, ast.Call) and _called_name(n) == _DISPATCH_CALL
        ]
        assert gate_lines, f"{helper} no llama {_GATE_CALL}: sería un bypass del gate."
        assert dispatch_lines, f"{helper} no despacha por {_DISPATCH_CALL}."
        assert min(gate_lines) < min(dispatch_lines), (
            f"{helper}: {_GATE_CALL} debe evaluarse ANTES del dispatch "
            f"(gate en {gate_lines}, dispatch en {dispatch_lines})."
        )


def test_gate_bypass_guard_is_not_vacuous() -> None:
    """El driver realmente usa builders de mutación y helpers sin gate: hay qué guardar."""
    tree = _driver_tree()

    builder_calls = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and _called_name(n) in _MUTATION_BUILDERS
    ]
    ungated_calls = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and _called_name(n) in _UNGATED_DISPATCH
    ]
    defined = {f.name for f in _functions(tree)}

    assert builder_calls, (
        f"{_DRIVER}: ningún builder de mutación es invocado; el guard de bypass no "
        f"tendría material que vigilar."
    )
    assert ungated_calls, (
        f"{_DRIVER}: ningún helper SIN gate es invocado; el guard de bypass sería vacuo."
    )
    assert defined >= _UNGATED_DISPATCH, (
        f"{_DRIVER}: faltan helpers sin gate {sorted(_UNGATED_DISPATCH - defined)}; "
        f"si se renombraron, actualizá _UNGATED_DISPATCH o el guard deja de mirar nada."
    )


def test_probe_symbol_identifiers_are_prefixed_stable_and_surface_disjoint() -> None:
    """Los seis identificadores comparten el prefijo auditable, son fijos y disjuntos (D-05)."""
    tree = _driver_tree()
    consts: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        value = node.value
        if (
            isinstance(target, ast.Name)
            and isinstance(value, ast.Constant)
            and isinstance(value.value, str)
        ):
            consts[target.id] = value.value

    assert consts.get(_PREFIX_CONST) == _EXPECTED_PREFIX, (
        f"{_DRIVER} debe declarar {_PREFIX_CONST} = {_EXPECTED_PREFIX!r}: es el prefijo "
        f"por el que se barre el residuo permanente vía GET /symbols?prefix=."
    )

    names = (*_SYNC_SYMBOL_CONSTS, *_ASYNC_SYMBOL_CONSTS)
    missing = [n for n in names if n not in consts]
    assert not missing, (
        f"{_DRIVER}: identificadores de prueba ausentes o no literales: {missing}. "
        f"Deben ser literales string a nivel de módulo (greppables, no derivados)."
    )

    values = [consts[n] for n in names]
    assert all(v.startswith(_EXPECTED_PREFIX) for v in values), (
        f"{_DRIVER}: todo identificador de prueba debe empezar con {_EXPECTED_PREFIX!r} "
        f"para que el residuo sea barrible: {values}"
    )
    assert len(set(values)) == len(values), (
        f"{_DRIVER}: identificadores de prueba duplicados: {values}"
    )
    sync_values = {consts[n] for n in _SYNC_SYMBOL_CONSTS}
    async_values = {consts[n] for n in _ASYNC_SYMBOL_CONSTS}
    assert not (sync_values & async_values), (
        f"{_DRIVER}: sync y async deben usar identificadores DISJUNTOS para que el "
        f"conteo de filas de idempotencia sea inequívoco por superficie."
    )
