"""D-03 guard — ninguna línea que ``main_market_data.py`` imprima puede clasificar
al PAQUETE ENTERO como SKIPPED en ``main_verify.py``.

``main_verify.py`` decide RAN/SKIPPED/FAILED por la FORMA del stdout del hijo:
``_ENV_SKIP = ^SKIPPED \\S.*:``. El único emisor legítimo de esa forma es el gate
de credenciales ``require_env`` en ``verification/env_gate.py`` — que vive FUERA
de este driver y significa, correctamente, "el driver no corrió". Cualquier otra
línea del driver con esa forma haría que un read sweep completamente exitoso se
reportara como skip, que es exactamente la regresión que ``main_verify.py:75``
documenta.

Por eso el skip a nivel PROBE de los probes mutantes es
``SKIPPED (mutating, guard off)`` — SIN dos puntos — y el driver sigue corriendo
el read sweep en vez de terminar temprano (D-03 prohíbe un early exit a nivel
driver sobre el path del gate).

El patrón clasificador se IMPORTA de ``main_verify`` en vez de re-declararse, así
que si el clasificador cambia este guard lo sigue.
"""

from __future__ import annotations

import ast
from pathlib import Path

from main_verify import _ENV_SKIP

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_market_data.py"

# Nombres a través de los cuales el driver emite stdout.
_PRINTERS = frozenset({"safe_print", "print"})

# Valor hostil sustituido en cada hueco ``{...}`` de una f-string: lleva el prefijo
# del clasificador Y dos puntos, así que si la PARTE LITERAL de una línea permite
# que el clasificador matchee, este render lo destapa.
_HOSTILE = "SKIPPED evil: pwned"

# Piso de no-vacuidad: el driver imprime al menos la línea PROBE y la SUMMARY.
_MIN_PRINT_SITES = 2


def _driver_tree() -> ast.Module:
    return ast.parse((_REPO_ROOT / _DRIVER).read_text(encoding="utf-8"))


def _module_str_constants(tree: ast.Module) -> dict[str, str]:
    """Constantes string asignadas a nivel de módulo, por nombre."""
    out: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign | ast.AnnAssign):
            continue
        value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                out[target.id] = value.value
    return out


def _render(node: ast.expr, consts: dict[str, str]) -> str | None:
    """Renderiza un argumento de print a su peor caso, o ``None`` si no es analizable."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return consts.get(node.id)
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for piece in node.values:
            if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                parts.append(piece.value)
            else:
                parts.append(_HOSTILE)
        return "".join(parts)
    if isinstance(node, ast.Call):
        # p.ej. ``f"...".rstrip()`` — el receptor es lo que define la forma.
        func = node.func
        if isinstance(func, ast.Attribute):
            return _render(func.value, consts)
    return None


def _print_payloads() -> tuple[list[tuple[int, str]], list[int]]:
    """Devuelve ``([(lineno, rendered)], [lineno_no_analizable])`` de todo print del driver."""
    tree = _driver_tree()
    consts = _module_str_constants(tree)
    rendered: list[tuple[int, str]] = []
    unanalyzable: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        fname = func.id if isinstance(func, ast.Name) else None
        if fname not in _PRINTERS or not node.args:
            continue
        payload = _render(node.args[0], consts)
        if payload is None:
            unanalyzable.append(node.lineno)
        else:
            rendered.append((node.lineno, payload))
    return rendered, unanalyzable


def test_no_driver_output_line_can_classify_the_package_as_skipped() -> None:
    """Ningún ``safe_print``/``print`` del driver produce una línea ``^SKIPPED \\S.*:``."""
    rendered, unanalyzable = _print_payloads()

    assert not unanalyzable, (
        f"{_DRIVER}: argumento de print no analizable estáticamente en la(s) línea(s) "
        f"{unanalyzable}; mantené el payload como literal o f-string para que este "
        f"guard pueda probar la forma de salida."
    )
    assert len(rendered) >= _MIN_PRINT_SITES, (
        f"{_DRIVER}: sólo {len(rendered)} sitio(s) de print encontrados "
        f"(esperado >= {_MIN_PRINT_SITES}); el guard sería vacuo."
    )

    offenders: list[tuple[int, str]] = []
    for lineno, payload in rendered:
        for line in payload.splitlines() or [payload]:
            if _ENV_SKIP.match(line):
                offenders.append((lineno, line))
    assert not offenders, (
        f"{_DRIVER}: línea(s) de salida que main_verify.py clasificaría como SKIP de "
        f"PAQUETE ENTERO (D-03): {offenders}. El único emisor legítimo de esa forma es "
        f"require_env en verification/env_gate.py."
    )


def test_probe_level_mutating_skip_detail_is_colon_free() -> None:
    """El detalle de skip a nivel probe (el que usará 27-04) no lleva dos puntos."""
    consts = _module_str_constants(_driver_tree())

    assert "_MUTATING_SKIP_DETAIL" in consts, (
        f"{_DRIVER} debe declarar _MUTATING_SKIP_DETAIL: es la cadena que los probes "
        f"mutantes emiten con el gate apagado, y su forma es load-bearing (D-03)."
    )
    detail = consts["_MUTATING_SKIP_DETAIL"]
    assert ":" not in detail, f"el detalle de skip a nivel probe no puede llevar ':': {detail!r}"
    assert _ENV_SKIP.match(detail) is None
    assert detail == "SKIPPED (mutating, guard off)"


def test_probe_prefixed_lines_are_immune_by_construction() -> None:
    """Una línea ``PROBE ...`` es inmune aunque el detalle sea hostil."""
    hostile_line = f"PROBE {_HOSTILE}: {_HOSTILE} {_HOSTILE}"

    assert _ENV_SKIP.match(hostile_line) is None
    assert _ENV_SKIP.match(f"SUMMARY: {_HOSTILE}") is None
    # Control positivo: el guard NO es vacuo — la forma del env-gate SÍ matchea.
    assert _ENV_SKIP.match("SKIPPED market-data-client: missing MARKET_DATA_CLIENT_ID")


def test_main_has_no_early_exit_on_the_mutation_gate_path() -> None:
    """El único ``sys.exit`` de ``main()`` es el del gate de credenciales (D-03/D-04).

    Un gate de mutaciones apagado debe CONTINUAR hacia el read sweep; un early
    exit a nivel driver dejaría el paquete sin verificar y sin decirlo.
    """
    tree = _driver_tree()
    mains = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"]
    assert mains, f"{_DRIVER} no define main()"
    main_fn = mains[0]

    exits = [
        node
        for node in ast.walk(main_fn)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "exit"
    ]
    assert len(exits) == 1, (
        f"{_DRIVER}: main() tiene {len(exits)} llamada(s) a sys.exit "
        f"(esperado exactamente 1, la del gate de credenciales): "
        f"{[e.lineno for e in exits]}"
    )

    guarded: set[int] = set()
    for node in ast.walk(main_fn):
        if not isinstance(node, ast.If):
            continue
        uses_require_env = any(
            isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Name)
            and inner.func.id == "require_env"
            for inner in ast.walk(node.test)
        )
        if not uses_require_env:
            continue
        for stmt in node.body:
            for descendant in ast.walk(stmt):
                if isinstance(descendant, ast.Call):
                    guarded.add(id(descendant))

    assert all(id(e) in guarded for e in exits), (
        f"{_DRIVER}: sys.exit fuera del guard de require_env — un gate de mutaciones "
        f"apagado NO puede terminar el run (D-03)."
    )
