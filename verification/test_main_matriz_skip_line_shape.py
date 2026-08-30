"""D-02 + D-01 (mitad matriz) — allowlist de venue por hostname exacto y forma
de la línea SKIPPED que ``main_verify.py`` clasifica.

Este lock es el ESPEJO INVERTIDO de
``verification/test_main_market_data_skip_line_shape.py``. Aquel exige que
NINGUNA línea del driver matchee ``_ENV_SKIP``; acá se exige que matchee
**exactamente una** —la línea D-01 de matriz— porque para matriz un host fuera
del allowlist SÍ significa "el driver no corrió", que es precisamente lo que el
clasificador debe reportar. Hasta D-01 esa condición salía ``FAILED`` (ABORT a
stderr + exit 1) y ``main_verify.py`` sólo escanea ``stdout``.

Dos capas:

1. **Forma de salida.** El patrón clasificador se IMPORTA de ``main_verify``
   (nunca se re-declara) y las líneas de print del driver se renderizan por AST
   a su peor caso, con un valor hostil en cada hueco de f-string.
2. **Predicado de venue.** La tabla de ``<behavior>`` del plan 39-01 se ejercita
   contra la función real: igualdad exacta de hostname, con el sufijo hostil
   (``<host-conocido>.attacker.example``) y la variante userinfo
   (``https://<host-conocido>@attacker.example``) rechazados (T-39-01).

``verification/mutation_gate.py`` NO se toca: su ``_SANDBOX_HOST`` remarkets-only
mantiene el order entry fail-closed bajo bbsa sin cambio de código (T-39-02).
"""

from __future__ import annotations

import ast
from pathlib import Path

import main_matriz
import pytest
from main_verify import _ENV_SKIP

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_matriz.py"

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


def _local_str_bindings(tree: ast.Module, consts: dict[str, str]) -> dict[str, str]:
    """Locales string-valuados, renderizados al peor caso (extensión sobre el analog).

    ``main_market_data.py`` pasa siempre el payload INLINE al print, así que el
    analog sólo necesita las constantes de módulo. ``main_matriz.py`` liga la
    línea PROBE a un local antes de imprimirla
    (``line = f"PROBE ...".rstrip()`` / ``safe_print(line, ...)``), y sin este
    paso ese sitio quedaría "no analizable" y el guard se apagaría justo donde
    más hace falta.
    """
    out: dict[str, str] = dict(consts)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id in out:
            continue
        rendered = _render(node.value, consts)
        if rendered is not None:
            out[target.id] = rendered
    return out


def _print_payloads() -> tuple[list[tuple[int, str]], list[int]]:
    """Devuelve ``([(lineno, rendered)], [lineno_no_analizable])`` de todo print del driver."""
    tree = _driver_tree()
    consts = _local_str_bindings(tree, _module_str_constants(tree))
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


def _classifying_lines() -> list[tuple[int, str]]:
    rendered, unanalyzable = _print_payloads()
    assert not unanalyzable, (
        f"{_DRIVER}: argumento de print no analizable estáticamente en la(s) línea(s) "
        f"{unanalyzable}; mantené el payload como literal, f-string o local ligado a "
        f"uno de esos, para que este guard pueda probar la forma de salida."
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
    return hits


# ---------------------------------------------------------------------------
# Capa 1: forma de la salida
# ---------------------------------------------------------------------------


def test_exactly_one_driver_line_classifies_the_package_as_skipped() -> None:
    """Una sola línea del driver clasifica SKIPPED: la de venue fuera del allowlist."""
    hits = _classifying_lines()

    assert len(hits) == 1, (
        f"{_DRIVER}: se esperaba EXACTAMENTE una línea que main_verify.py "
        f"clasifique como SKIP de PAQUETE ENTERO (la de D-MATZ-33); encontradas: {hits}"
    )
    _lineno, line = hits[0]
    assert line == main_matriz._HOST_SKIP_LINE, (
        f"la única línea clasificadora debe ser _HOST_SKIP_LINE, no {line!r}"
    )


def test_host_skip_line_is_a_plain_module_constant() -> None:
    """La línea es una constante literal: sin interpolación no hay leak (T-39-04)."""
    consts = _module_str_constants(_driver_tree())
    assert "_HOST_SKIP_LINE" in consts, (
        f"{_DRIVER} debe declarar _HOST_SKIP_LINE como literal de módulo: su forma "
        f"es load-bearing para el clasificador y su AUSENCIA de interpolación es lo "
        f"que garantiza que no filtre la base URL (T-39-04)."
    )
    assert consts["_HOST_SKIP_LINE"] == main_matriz._HOST_SKIP_LINE
    assert _ENV_SKIP.match(main_matriz._HOST_SKIP_LINE) is not None
    assert main_matriz._HOST_SKIP_LINE.endswith("LIVE-MATZ-33")


def test_mutation_gate_line_still_does_not_classify() -> None:
    """Control negativo: la línea colon-free del mutation gate sigue inmune (WR-01)."""
    assert _ENV_SKIP.match(_MUTATION_GATE_LINE) is None


def test_env_gate_form_still_matches() -> None:
    """Control positivo: el guard no es vacuo — la forma del env-gate SÍ matchea."""
    assert _ENV_SKIP.match("SKIPPED matriz-client: missing PRIMARY_USER") is not None


# ---------------------------------------------------------------------------
# Capa 2: predicado de venue (T-39-01 / T-39-03)
# ---------------------------------------------------------------------------


def test_venue_allowlist_has_exactly_the_two_known_hosts() -> None:
    """Dos entradas y ninguna más: ampliar el allowlist es una decisión humana (D-02)."""
    allowlist = main_matriz._VENUE_ALLOWLIST
    assert set(allowlist) == {
        "api.remarkets.primary.com.ar",
        "api.bbsa.matrizoms.com.ar",
    }, (
        "el allowlist D-MATZ-33 tiene exactamente dos hosts confirmados por el "
        "operador; cualquier agregado requiere un checkpoint humano nuevo (P-05)."
    )
    assert len(allowlist) == 2


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("api.remarkets.primary.com.ar", "remarkets"),
        ("https://api.remarkets.primary.com.ar", "remarkets"),
        ("api.bbsa.matrizoms.com.ar", "bbsa"),
        ("https://api.bbsa.matrizoms.com.ar", "bbsa"),
        # Barra final: el estado del cliente ya viene rstrip("/")-normalizado,
        # pero el predicado no debe DEPENDER de eso.
        ("https://api.bbsa.matrizoms.com.ar/", "bbsa"),
        # Sufijo hostil: un ``in`` o un ``endswith`` lo dejarían pasar.
        ("api.bbsa.matrizoms.com.ar.attacker.example", None),
        ("https://api.bbsa.matrizoms.com.ar.attacker.example", None),
        # Userinfo: el host REAL es attacker.example.
        ("https://api.bbsa.matrizoms.com.ar@attacker.example", None),
        ("https://api.remarkets.primary.com.ar@attacker.example", None),
        # Producción: el host que esta política existe para mantener afuera.
        ("api.primary.com.ar", None),
        ("https://api.primary.com.ar", None),
        # Fail-closed ante basura.
        ("", None),
        ("https://[oops/api", None),
    ],
)
def test_venue_token_resolves_by_exact_hostname(base_url: str, expected: str | None) -> None:
    """Igualdad exacta de hostname; nunca substring ni sufijo (T-39-01)."""
    assert main_matriz._venue_token(base_url) == expected


def test_no_substring_membership_check_over_a_host_literal() -> None:
    """El chequeo por pertenencia de substring no puede volver al driver.

    Aserción por AST, no por ``grep``: el comentario que documenta POR QUÉ el
    chequeo viejo era inseguro cita su código, y un grep sobre el fuente no
    distingue la cita del código vivo.
    """
    offenders: list[int] = []
    for node in ast.walk(_driver_tree()):
        if not isinstance(node, ast.Compare):
            continue
        if not any(isinstance(op, ast.In | ast.NotIn) for op in node.ops):
            continue
        left = node.left
        if isinstance(left, ast.Constant) and isinstance(left.value, str):
            offenders.append(node.lineno)
    assert not offenders, (
        f"{_DRIVER}: comparación por pertenencia de substring sobre un literal en "
        f"la(s) línea(s) {offenders}; el gate D-MATZ-33 debe usar igualdad exacta "
        f"de hostname — ``https://api.remarkets.primary.com.ar.attacker.example`` "
        f"pasaría un ``in``."
    )
