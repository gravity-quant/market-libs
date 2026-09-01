"""D-01 (mitad higyrus) — un vendor inalcanzable se reporta SKIPPED, no como finding.

Hasta D-01, un ``httpx.ConnectError`` de ``client.login()`` (el caso DNS
``gaierror`` medido en la sesión de research de la Phase 39) caía en el bracket
residual ``_RESIDUAL_PROBE_EXCEPTIONS`` —que incluye ``httpx.HTTPError``, del que
``ConnectError`` es subclase— y se absorbía como un finding ``AUTH OPEN``. El
driver salía con código 0 sin ninguna línea SKIPPED, así que ``main_verify.py``
lo clasificaba ``RAN``: un **falso limpio**, con un finding fabricado escrito en
un ledger versionado y una rama de exención de
``verification/test_cycle_closure_phase33.py`` enrojecida de yapa.

Este lock es el ESPEJO INVERTIDO de
``verification/test_main_market_data_skip_line_shape.py``: aquel exige que
NINGUNA línea del driver matchee ``_ENV_SKIP``, acá se exige **exactamente una**.

Tres capas:

1. **Forma de salida.** El patrón clasificador se IMPORTA de ``main_verify``
   (nunca se re-declara) y los prints del driver se renderizan por AST a su peor
   caso, con un valor hostil en cada hueco de f-string.
2. **Estructura del handler.** Por ``ast``: en ``probe_login_sync`` y en
   ``probe_login_async`` existe un ``except`` que nombra ``ConnectError``, está
   DESPUÉS del de ``HigyrusAPIError`` y ANTES del bracket residual, y su cuerpo
   no llama ``append_finding``. El ORDEN es lo que impide que la rama nueva se
   trague un rechazo real del vendor (T-39-05), y la ausencia de
   ``append_finding`` es lo que impide que escriba en el ledger.
3. **Alcance de la excepción.** ``httpx.ConnectTimeout`` NO es subclase de
   ``httpx.ConnectError``: un timeout sigue cayendo en el bracket residual.
"""

from __future__ import annotations

import ast
from pathlib import Path

import httpx
import main_higyrus
from main_verify import _ENV_SKIP

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_higyrus.py"

# Nombres a través de los cuales el driver emite stdout.
_PRINTERS = frozenset({"safe_print", "print"})

# Valor hostil sustituido en cada hueco ``{...}`` de una f-string: lleva el prefijo
# del clasificador Y dos puntos, así que si la PARTE LITERAL de una línea permite
# que el clasificador matchee, este render lo destapa.
_HOSTILE = "SKIPPED evil: pwned"

# Piso de no-vacuidad: el driver imprime al menos la línea PROBE y la SUMMARY.
_MIN_PRINT_SITES = 2

# Forma verbatim del mutation gate, sin dos puntos a propósito (WR-01).
_MUTATION_GATE_LINE = "SKIPPED (mutating, guard off)"

# Los dos probes de login, sync y async: el espejo es obligatorio (CLAUDE.md / D-08).
_LOGIN_PROBES = ("probe_login_sync", "probe_login_async")


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


# ---------------------------------------------------------------------------
# Capa 1: forma de la salida
# ---------------------------------------------------------------------------


def test_exactly_one_driver_line_classifies_the_package_as_skipped() -> None:
    """Una sola línea del driver clasifica SKIPPED: la de vendor inalcanzable."""
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

    hits: list[tuple[int, str]] = []
    for lineno, payload in rendered:
        for line in payload.splitlines() or [payload]:
            if _ENV_SKIP.match(line):
                hits.append((lineno, line))

    assert len(hits) == 1, (
        f"{_DRIVER}: se esperaba EXACTAMENTE una línea que main_verify.py clasifique "
        f"como SKIP de PAQUETE ENTERO (la de vendor inalcanzable, D-01); "
        f"encontradas: {hits}"
    )
    _lineno, line = hits[0]
    assert line == main_higyrus._VENDOR_UNREACHABLE_SKIP_LINE


def test_unreachable_skip_line_is_a_plain_module_constant() -> None:
    """La línea es un literal de módulo: sin interpolación no hay leak (T-39-04)."""
    consts = _module_str_constants(_driver_tree())
    assert "_VENDOR_UNREACHABLE_SKIP_LINE" in consts, (
        f"{_DRIVER} debe declarar _VENDOR_UNREACHABLE_SKIP_LINE como literal de "
        f"módulo: su forma es load-bearing para el clasificador y su AUSENCIA de "
        f"interpolación es lo que garantiza que no filtre el hostname (T-39-04)."
    )
    line = main_higyrus._VENDOR_UNREACHABLE_SKIP_LINE
    assert consts["_VENDOR_UNREACHABLE_SKIP_LINE"] == line
    assert _ENV_SKIP.match(line) is not None
    assert line.startswith(f"SKIPPED {main_higyrus._PKG}: ")
    assert line.endswith("LIVE-HIGY-42")
    assert "http" not in line
    assert ".com" not in line


def test_mutation_gate_line_still_does_not_classify() -> None:
    """Control negativo: la línea colon-free del mutation gate sigue inmune (WR-01)."""
    assert _ENV_SKIP.match(_MUTATION_GATE_LINE) is None


def test_env_gate_form_still_matches() -> None:
    """Control positivo: el guard no es vacuo — la forma del env-gate SÍ matchea."""
    assert _ENV_SKIP.match("SKIPPED higyrus-client: missing HIGYRUS_USER") is not None


# ---------------------------------------------------------------------------
# Capa 2: estructura de los handlers de login (T-39-05)
# ---------------------------------------------------------------------------


def _login_probe(name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    tree = _driver_tree()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{_DRIVER} no define {name}()")


def _handler_names(handler: ast.ExceptHandler) -> set[str]:
    """Todos los identificadores que aparecen en el tipo capturado del handler."""
    if handler.type is None:
        return set()
    return {n.id for n in ast.walk(handler.type) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(handler.type) if isinstance(n, ast.Attribute)
    }


def _handler_index(probe: ast.FunctionDef | ast.AsyncFunctionDef, wanted: str) -> int:
    for node in ast.walk(probe):
        if not isinstance(node, ast.Try):
            continue
        for index, handler in enumerate(node.handlers):
            if wanted in _handler_names(handler):
                return index
    return -1


def _handler_body(probe: ast.FunctionDef | ast.AsyncFunctionDef, wanted: str) -> list[ast.stmt]:
    for node in ast.walk(probe):
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            if wanted in _handler_names(handler):
                return handler.body
    raise AssertionError(f"{probe.name}: no hay handler que capture {wanted}")


def test_both_login_probes_catch_connect_error_before_the_residual_bracket() -> None:
    """El orden de los tres brackets es load-bearing (T-39-05).

    ``HigyrusAPIError`` (rechazo real del vendor, sigue produciendo su finding)
    < ``ConnectError`` (host inalcanzable, SKIPPED sin finding)
    < ``_RESIDUAL_PROBE_EXCEPTIONS`` (que INCLUYE ``httpx.HTTPError``, superclase
    de ``ConnectError``, y por eso se lo tragaría si fuera primero).
    """
    for name in _LOGIN_PROBES:
        probe = _login_probe(name)
        api_index = _handler_index(probe, "HigyrusAPIError")
        connect_index = _handler_index(probe, "ConnectError")
        residual_index = _handler_index(probe, "_RESIDUAL_PROBE_EXCEPTIONS")

        assert connect_index >= 0, (
            f"{name}: falta el handler de httpx.ConnectError; un vendor caído "
            f"volvería a salir como finding AUTH OPEN (falso limpio, D-01)."
        )
        assert api_index >= 0, f"{name}: falta el handler de HigyrusAPIError"
        assert residual_index >= 0, f"{name}: falta el bracket residual"
        assert api_index < connect_index, (
            f"{name}: el handler de ConnectError quedó ANTES del de "
            f"HigyrusAPIError; un rechazo real del vendor no puede salir como skip."
        )
        assert connect_index < residual_index, (
            f"{name}: el handler de ConnectError quedó DESPUÉS del bracket "
            f"residual, que incluye httpx.HTTPError (superclase): la rama nueva "
            f"sería inalcanzable."
        )


def test_the_connect_error_branch_writes_no_finding() -> None:
    """La rama nueva no puede llamar ``append_finding`` (enrojece cycle_closure)."""
    for name in _LOGIN_PROBES:
        probe = _login_probe(name)
        calls = [
            node.lineno
            for stmt in _handler_body(probe, "ConnectError")
            for node in ast.walk(stmt)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "append_finding"
        ]
        assert not calls, (
            f"{name}: la rama de vendor inalcanzable llama append_finding en la(s) "
            f"línea(s) {calls}; un finding AUTH OPEN nuevo enrojece la rama de "
            f"exención de higyrus en verification/test_cycle_closure_phase33.py."
        )


def test_the_connect_error_branch_returns_a_skipped_probe_result() -> None:
    """El probe devuelve ``SKIPPED`` con causa medida, no ``FINDING``."""
    for name in _LOGIN_PROBES:
        probe = _login_probe(name)
        statuses = [
            arg.value
            for stmt in _handler_body(probe, "ConnectError")
            for node in ast.walk(stmt)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "ProbeResult"
            for arg in node.args
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
        ]
        assert "SKIPPED" in statuses, (
            f"{name}: la rama de vendor inalcanzable debe devolver "
            f"ProbeResult(..., 'SKIPPED', ...); encontrado: {statuses}"
        )


# ---------------------------------------------------------------------------
# Capa 3: alcance de la excepción
# ---------------------------------------------------------------------------


def test_connect_timeout_is_not_swallowed_by_the_new_branch() -> None:
    """Un timeout NO es un host inalcanzable: sigue en el bracket residual."""
    assert not issubclass(httpx.ConnectTimeout, httpx.ConnectError)
    assert issubclass(httpx.ConnectError, httpx.HTTPError)
