"""D-01 (Phase 42) — el censo decide el venue contra la MISMA fuente que el driver.

Este lock es el hermano de ``verification/test_main_matriz_skip_line_shape.py``,
re-apuntado de ``main_matriz.py`` a ``scripts/literal_census_33.py``. Aquel prueba
que el DRIVER resuelve el venue por igualdad exacta de hostname; éste prueba que
el CENSO lo hace **por la misma referencia importada**, no por una copia propia.

Cuatro capas:

1. **Identidad de fuente (D-01).** ``census._venue_token is main_matriz._venue_token``
   y ``census._VENUE_ALLOWLIST is main_matriz._VENUE_ALLOWLIST``. Es identidad de
   objeto (``is``), no igualdad de contenido (``==``): con el import, la divergencia
   entre los dos sitios de decisión pasa de "detectada" a estructuralmente imposible.
2. **Predicado de venue.** La tabla de 13 casos del analog (``:218-244``), ejercitada
   contra el uso importado del censo: sufijo hostil (``<host-conocido>.attacker.example``)
   y userinfo (``https://<host-conocido>@attacker.example``) rechazados (T-42-01).
3. **Anti-substring por AST.** Cero comparaciones por pertenencia sobre un literal
   string dentro de ``census_matriz``. El walk se restringe a ese ``FunctionDef``
   a propósito: el despacho de flags de ``main()`` (``"--selftest" in argv``) tiene
   la misma forma sintáctica y sobre el módulo entero daría un falso positivo, que
   invita a relajar la aserción — lo contrario de lo que el criterio 1 quiere.
4. **Header antes del tráfico.** ``_census_header`` se llama antes de la primera
   request, y sus líneas llevan venue + timestamp UTC (criterio 3).

``verification/mutation_gate.py`` **NO se toca en ninguna task de la Phase 42**: su
``_SANDBOX_HOST`` remarkets-only mantiene el order entry fail-closed bajo bbsa sin
cambio de código (T-39-02 / T-42-02). Las dos últimas pruebas de este archivo pinnean
ese comportamiento y son, además, el piso de no-vacuidad del lock: pasan desde el
primer día, así que un rojo acá nunca puede confundirse con "el archivo está roto".
"""

from __future__ import annotations

import ast
from pathlib import Path

import main_matriz
import pytest
import scripts.literal_census_33 as census

from verification import mutation_gate

_REPO_ROOT = Path(__file__).resolve().parent.parent
_TARGET = _REPO_ROOT / "scripts" / "literal_census_33.py"

# Sujeto del walk anti-substring: el único lugar donde el gate de venue puede vivir.
_GATED_FUNCTION = "census_matriz"

# Snippet sintético con la forma PROHIBIDA, usado como control positivo del walker.
# Si el detector dejara de detectar, la capa 3 quedaría verde por no inspeccionar nada.
_OFFENDING_SNIPPET = 'if "remarkets" not in base:\n    pass\n'


def _census_matriz_node() -> ast.FunctionDef:
    """El ``FunctionDef`` de ``census_matriz``, o ``AssertionError`` si desapareció.

    El ``raise`` del else es parte del patrón del analog (mismo espíritu que su
    ``_MIN_PRINT_SITES = 2``): un lock nunca puede pasar por no encontrar su sujeto.
    """
    tree = ast.parse(_TARGET.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == _GATED_FUNCTION:
            return node
    raise AssertionError(
        f"{_TARGET.name}: no se encontró la función {_GATED_FUNCTION!r}; el lock del "
        f"gate de venue quedaría VACUO (verde por no inspeccionar nada). Si la función "
        f"se renombró, actualizá _GATED_FUNCTION en vez de borrar esta aserción."
    )


def _membership_offenders(node: ast.AST) -> list[int]:
    """Líneas con una comparación por pertenencia cuyo lado izquierdo es un literal string.

    Aserción por AST, no por ``grep``: el docstring del censo cita en prosa el gate
    viejo ("remarkets-only") y un grep sobre el fuente no distingue la cita del código
    vivo.
    """
    offenders: list[int] = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Compare):
            continue
        if not any(isinstance(op, ast.In | ast.NotIn) for op in child.ops):
            continue
        left = child.left
        if isinstance(left, ast.Constant) and isinstance(left.value, str):
            offenders.append(child.lineno)
    return offenders


def _call_linenos(node: ast.AST, *, name: str | None = None, attr: str | None = None) -> list[int]:
    """Líneas de las llamadas dentro de ``node`` a un ``Name`` o a un ``Attribute``."""
    linenos: list[int] = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if (name is not None and isinstance(func, ast.Name) and func.id == name) or (
            attr is not None and isinstance(func, ast.Attribute) and func.attr == attr
        ):
            linenos.append(child.lineno)
    return sorted(linenos)


# ---------------------------------------------------------------------------
# Capa 1: identidad de la fuente única (D-01)
# ---------------------------------------------------------------------------


def test_census_shares_the_single_venue_source() -> None:
    """El censo no re-declara la política: la IMPORTA de ``main_matriz`` (D-01).

    Identidad de objeto, no igualdad de contenido: dos copias con el mismo contenido
    hoy pueden divergir mañana, y el modo de falla de esa divergencia es que el censo
    emita tráfico contra un host que el driver ya rechaza.
    """
    assert census._venue_token is main_matriz._venue_token, (
        "scripts/literal_census_33.py debe importar _venue_token de main_matriz "
        "(``from main_matriz import _VENUE_ALLOWLIST, _venue_token``), no re-declarar "
        "el predicado: la fuente de la política de venue es UNA sola (D-01)."
    )
    assert census._VENUE_ALLOWLIST is main_matriz._VENUE_ALLOWLIST, (
        "el allowlist tiene que ser el MISMO objeto que publica main_matriz.py; una "
        "copia local puede divergir y ampliar el alcance del tráfico sin checkpoint."
    )


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


# ---------------------------------------------------------------------------
# Capa 2: predicado de venue, visto desde el censo (T-42-01 / T-42-05)
# ---------------------------------------------------------------------------


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
    """Igualdad exacta de hostname desde el sitio del censo; nunca substring (T-42-01)."""
    assert census._venue_token(base_url) == expected


# ---------------------------------------------------------------------------
# Capa 3: el gate viejo no puede volver (criterio 1)
# ---------------------------------------------------------------------------


def test_no_substring_membership_check_inside_census_matriz() -> None:
    """``if "remarkets" not in base:`` no puede volver a ``census_matriz``.

    El walk se restringe al cuerpo de ``census_matriz`` a propósito (decisión Q4):
    ``main()`` despacha flags con ``"--selftest" in argv``, que es la misma forma
    sintáctica y sobre el módulo entero sería un falso positivo.
    """
    offenders = _membership_offenders(_census_matriz_node())
    assert not offenders, (
        f"{_TARGET.name}: comparación por pertenencia de substring sobre un literal en "
        f"la(s) línea(s) {offenders} dentro de {_GATED_FUNCTION}; el gate D-MATZ-33 debe "
        f"usar igualdad exacta de hostname vía _venue_token — "
        f"``https://api.remarkets.primary.com.ar.attacker.example`` pasaría un ``in``."
    )


def test_membership_walker_detects_an_injected_offender() -> None:
    """Control positivo: el detector de la capa 3 no está apagado."""
    injected = ast.parse(_OFFENDING_SNIPPET)
    assert _membership_offenders(injected), (
        "_membership_offenders dejó de detectar la forma prohibida; sin este control "
        "el guard anti-substring podría estar verde por no inspeccionar nada (P-02)."
    )


# ---------------------------------------------------------------------------
# Capa 4: header venue + timestamp antes del tráfico (criterio 3)
# ---------------------------------------------------------------------------


def test_census_header_precedes_the_first_request() -> None:
    """El header se emite ANTES de la primera request: no puede describir lo ya ocurrido."""
    node = _census_matriz_node()
    header_calls = _call_linenos(node, name="_census_header")
    request_calls = _call_linenos(node, attr="_request")
    assert header_calls, (
        f"{_TARGET.name}: {_GATED_FUNCTION} debe llamar a _census_header — el criterio 3 "
        f"exige venue y timestamp en el encabezado del censo."
    )
    assert request_calls, (
        f"{_TARGET.name}: no se encontró ninguna llamada a ``_request`` dentro de "
        f"{_GATED_FUNCTION}; esta aserción de orden quedaría vacua."
    )
    assert header_calls[0] < request_calls[0], (
        f"{_TARGET.name}: _census_header (línea {header_calls[0]}) debe preceder a la "
        f"primera request (línea {request_calls[0]}); un header emitido después del "
        f"tráfico no gatea nada."
    )


def test_census_header_lines_carry_venue_and_timestamp() -> None:
    """``CENSUS-HEADER`` lleva venue + ``captured_at`` UTC, y ``CENSUS-DLOCK`` el D-lock (b)."""
    lines = census._census_header_lines("bbsa")
    assert lines, "_census_header_lines no devolvió ninguna línea"
    assert lines[0].startswith("CENSUS-HEADER venue=bbsa captured_at="), (
        f"la primera línea del header debe abrir con el venue MEDIDO y el timestamp; "
        f"se obtuvo {lines[0]!r}"
    )
    # Conteo, jamás un hostname: el header no filtra el dato de entrada (T-42-04).
    assert "allowlist_size=2" in lines[0]
    assert any(line.startswith("CENSUS-DLOCK") for line in lines), (
        "falta la línea CENSUS-DLOCK: el censo es una MEDICIÓN de una sola venue, no "
        "una autorización para promover los campos RESPONSE a ``Literal`` (Pitfall 3)."
    )


# ---------------------------------------------------------------------------
# Capa 5: el gate de MUTACIÓN no se amplía (criterio 4 / T-42-02)
# ---------------------------------------------------------------------------


def test_mutation_gate_stays_fail_closed_under_bbsa(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ampliar el gate de LECTURA no amplía el de MUTACIÓN: bbsa sigue fail-closed."""
    monkeypatch.setenv("VERIFY_MUTATING", "1")
    allowed = mutation_gate.mutating_allowed_for(
        env_var="VERIFY_MUTATING",
        base_url="https://api.bbsa.matrizoms.com.ar",
        expected_host=mutation_gate._SANDBOX_HOST,
    )
    assert allowed is False, (
        "el order entry debe seguir INALCANZABLE bajo bbsa sin cambio de código "
        "(T-39-02 / T-42-02): _SANDBOX_HOST es remarkets-only y no se amplía."
    )


def test_mutation_gate_allows_remarkets_control(monkeypatch: pytest.MonkeyPatch) -> None:
    """Control positivo: el ``False`` de arriba sale del hostname, no de un env mal seteado."""
    monkeypatch.setenv("VERIFY_MUTATING", "1")
    allowed = mutation_gate.mutating_allowed_for(
        env_var="VERIFY_MUTATING",
        base_url="https://api.remarkets.primary.com.ar",
        expected_host=mutation_gate._SANDBOX_HOST,
    )
    assert allowed is True
