"""Guard ESTRUCTURAL del mutating-gate (criterio 3, T-31-01 / T-31-02 / T-31-04).

Complementa —no reemplaza— a ``tests/test_mutation_gate.py``, que es BEHAVIORAL
(refusal a nivel helper). Este módulo camina el AST de los dos shells y afirma
que ``_ensure_mutation_allowed()`` es la primera sentencia EJECUTABLE de los 8
métodos mutadores, en ``client.py`` y en ``aio.py``.

Ubicación in-package, NO bajo ``verification/``: el job ``test`` de ``ci.yml``
corre ``pytest packages/${{ matrix.package }}``, un path explícito que pisa
``[tool.pytest.ini_options] testpaths``, así que ``verification/`` **nunca**
corrió en CI (G-5; el propio ``ci.yml`` lo dice textualmente en el comentario
inline del paso ``decode-intactness``). Este guard tiene que viajar en la matriz
6x2, así que vive acá.

No-vacuidad (T-31-04): el set de métodos DESCUBIERTOS se compara por IGUALDAD
contra el roster de 8 nombres. Nunca un "no vacío", nunca un lower bound — un
guard que encuentra cero sujetos y reporta verde ya se shippeó dos veces en este
repo (Phase 15 WR-01/WR-02).

Segunda cláusula del criterio 3: los dos builders de feriados afirman
``RequestSpec.idempotent is True`` de forma DIRECTA, por identidad.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

import market_data_client
from market_data_client import _core

_GATE_CALL = "_ensure_mutation_allowed"

# Roster EXACTO de métodos gated (RESEARCH § Mutating-Gate Invariant: 16 call
# sites confirmados = 8 nombres x 2 shells).
_MUTATION_METHODS = frozenset(
    {
        "create_symbol",
        "create_symbols",
        "update_symbol",
        "set_calendar_config",
        "delete_calendar_config",
        "preview_calendar_config",
        "add_holidays",
        "delete_holiday",
    }
)

_SHELLS = ("client.py", "aio.py")


def _shell_tree(name: str) -> ast.Module:
    """AST del shell ``name``, resuelto A TRAVÉS del paquete importado.

    Resolver vía ``market_data_client.__file__`` (en vez de armar un path desde
    la raíz del repo) mantiene el guard funcionando bajo
    ``--import-mode=importlib`` y también sobre un wheel instalado.
    """
    source = pathlib.Path(market_data_client.__file__).parent / name
    return ast.parse(source.read_text(encoding="utf-8"))


def _called_name(node: ast.Call) -> str | None:
    """Nombre invocado de un ``Call``: ``f(...)`` -> ``f``; ``m.f(...)`` -> ``f``."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _shell_methods(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Funciones definidas DIRECTAMENTE en el cuerpo de una clase del shell.

    Deliberadamente NO es un ``ast.walk`` del módulo entero. Los dos shells
    definen, además de los métodos de ``Client`` / ``AsyncClient``, shims a nivel
    módulo con LOS MISMOS 8 NOMBRES (``client.py:950``/``:955``,
    ``aio.py:956``/``:961``) que delegan en el singleton default
    (``_get_default().add_holidays(...)``) y por lo tanto —correctamente— NO
    llaman al gate: el gate corre adentro del método al que delegan. Barrerlos
    con ``ast.walk`` haría fallar al guard sobre código sano y, peor, invitaría a
    aflojar el predicado. El invariante vive en la clase, que es donde están los
    16 call sites confirmados.
    """
    return [
        fn
        for cls in tree.body
        if isinstance(cls, ast.ClassDef)
        for fn in cls.body
        if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef)
    ]


def _first_stmt_is_gate(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """¿``_ensure_mutation_allowed()`` es la primera sentencia EJECUTABLE de ``fn``?"""
    body = fn.body
    # Saltear el docstring es exactamente lo que hace que "primera sentencia
    # LITERAL" signifique "primera sentencia EJECUTABLE": los 8 métodos abren con
    # un docstring, que es un `Expr(Constant)` y no ejecuta nada.
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    return (
        bool(body)
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Call)
        and _called_name(body[0].value) == _GATE_CALL
    )


def _discovered(shell: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Métodos del shell cuyo nombre está en el roster, indexados por nombre."""
    return {
        fn.name: fn for fn in _shell_methods(_shell_tree(shell)) if fn.name in _MUTATION_METHODS
    }


# ----------------------------------------------------------------------
# Test A — no-vacuidad por IGUALDAD de sets (T-31-04)
# ----------------------------------------------------------------------


@pytest.mark.parametrize("shell", _SHELLS)
def test_every_mutation_method_is_discovered_in_shell(shell: str) -> None:
    """El set descubierto es IGUAL al roster de 8 — ni un nombre de más ni de menos."""
    discovered = set(_discovered(shell))
    assert discovered == _MUTATION_METHODS, (
        f"{shell}: el set de métodos mutadores descubiertos no coincide con el roster. "
        f"faltan={sorted(_MUTATION_METHODS - discovered)} "
        f"sobran={sorted(discovered - _MUTATION_METHODS)}"
    )


# ----------------------------------------------------------------------
# Test B — el gate es la primera sentencia ejecutable (T-31-01, ASVS V4)
# ----------------------------------------------------------------------


@pytest.mark.parametrize("shell", _SHELLS)
def test_gate_is_first_executable_statement_in_every_mutation_method(shell: str) -> None:
    """Los 8 métodos del shell abren con ``self._ensure_mutation_allowed()``."""
    offenders: list[str] = []
    for name, fn in sorted(_discovered(shell).items()):
        if _first_stmt_is_gate(fn):
            continue
        body = fn.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            body = body[1:]
        actual = ast.dump(body[0])[:160] if body else "<cuerpo vacío>"
        offenders.append(f"{shell}::{name} (línea {fn.lineno}) — primera sentencia: {actual}")
    assert not offenders, (
        f"{_GATE_CALL}() dejó de ser la primera sentencia ejecutable en:\n" + "\n".join(offenders)
    )


# ----------------------------------------------------------------------
# Test C — segunda cláusula del criterio 3: flags de idempotencia (T-31-02)
# ----------------------------------------------------------------------


def test_both_holiday_builders_are_idempotent() -> None:
    """Los dos builders de feriados emiten ``idempotent is True`` (D-20).

    D-20: ambos flags fueron corregidos a ``True`` en la Phase 27 sobre MEDICIÓN
    de row-count en vivo (dos POST idénticos dejaron exactamente 1 fila — el
    endpoint hace upsert por fecha; el segundo DELETE del mismo día devuelve 404
    pero el ESTADO es replay-safe). El criterio 3 significa que deben SEGUIR en
    ``True``.

    G-6: el docstring de ``add_holidays`` en ``client.py`` todavía afirma lo
    contrario (``idempotent=False``) y está STALE — se corrige en el plan 31-05.
    Este test es la autoridad; la prosa no lo es.
    """
    state = market_data_client.Client(base_url="https://market-data-develop.test/api")._state

    add = _core.build_add_holidays_request(
        state,
        {"days": [{"day": "2099-12-29", "closed": True, "description": "probe"}]},
    )
    delete = _core.build_delete_holiday_request(state, "2099-12-29")

    # Identidad, no truthiness: un `1` o un objeto verdadero no califican.
    assert add.idempotent is True
    assert delete.idempotent is True
