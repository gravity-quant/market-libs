"""Phase 37 code review CR-01 -- las 2 risk probes del driver desenvuelven su envelope.

Plan 37-01 cambió ``_core.parse_get_detailed_positions_response`` y
``parse_get_account_report_response`` para desenvolver ``detailedPosition`` /
``accountData`` (D-03, ``strict-unwrap``), pero ``main_matriz.py`` se quedó con
la creencia anterior — "Risk no tiene envelope (D-07)" — y seguía pasando
``envelope_key=None``. Consecuencia medida por el code review: el payload que el
driver acumula para probe 20 (``field_type_map``) era el envelope CRUDO
(``{"status", "detailedPosition"}``), así que
``diff_safemodel_bidirectional`` lo habría diffeado contra el roster de
``DetailedPosition`` y habría emitido una tanda de findings SHAPE
"model declara, wire no emite (FALSE PASS riesgo)" fabricados — justo la clase de
finding falso que este milestone existe para eliminar.

Este lock es *grep-assertable* a propósito: no puede vivir en
``packages/matriz-client/tests/`` porque lo que verifica es el DRIVER, no el
paquete. Corre desde la lista explícita del job ``lint`` en
``.github/workflows/ci.yml``, por la misma razón que los otros guards de
``verification/``: el job ``test`` pasa un path explícito que pisa ``testpaths``,
así que ``verification/`` nunca corre ahí.

Tres capas, de la más estructural a la más literal:

1. ``_envelope_probe`` ya no ACEPTA ``envelope_key=None`` (el parámetro es
   ``str`` requerido). La ausencia de la rama es lo que impide que la creencia
   vuelva.
2. Ninguna call site del driver pasa ``envelope_key=None``.
3. Las dos risk probes citan exactamente las keys que ``_core`` desenvuelve, y
   ambas están declaradas como single-resource (dict), no como list envelope.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import main_matriz
import pytest

_DRIVER = Path(main_matriz.__file__)

# La fuente de verdad: lo que `_core` desenvuelve hoy. Si un día 37-01 se
# revirtiera, este mapping y el driver tienen que moverse juntos.
_RISK_ENVELOPE_KEYS = {
    "get_detailed_positions": "detailedPosition",
    "get_account_report": "accountData",
}


def test_envelope_probe_does_not_accept_a_none_envelope_key() -> None:
    """Capa 1: el parámetro es ``str`` requerido, sin default ``None``."""
    parameter = inspect.signature(main_matriz._envelope_probe).parameters["envelope_key"]
    assert parameter.default is inspect.Parameter.empty, (
        "`envelope_key` recuperó un default; la rama sin-envelope (D-07) es "
        "exactamente la creencia que 37-01 falsificó y CR-01 encontró viva acá."
    )
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


def test_no_envelope_probe_call_site_passes_a_none_envelope_key() -> None:
    """Capa 2: grep estructural (AST, no regex) sobre todas las llamadas del driver."""
    tree = ast.parse(_DRIVER.read_text(encoding="utf-8"))
    offenders: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        if not (isinstance(callee, ast.Name) and callee.id == "_envelope_probe"):
            continue
        for keyword in node.keywords:
            if keyword.arg != "envelope_key":
                continue
            if isinstance(keyword.value, ast.Constant) and keyword.value.value is None:
                offenders.append(node.lineno)
    assert offenders == [], (
        f"`envelope_key=None` sobrevive en {_DRIVER.name} línea(s) {offenders}. "
        "Los endpoints Risk SÍ traen envelope "
        "(documentation/Primary-API.md:1701-1703 y :1817-1819)."
    )


@pytest.mark.parametrize(("probe_name", "envelope_key"), sorted(_RISK_ENVELOPE_KEYS.items()))
def test_risk_probe_declares_the_envelope_key_core_unwraps(
    probe_name: str, envelope_key: str
) -> None:
    """Capa 3: la key literal del driver coincide con la que ``_core`` desenvuelve."""
    source = inspect.getsource(getattr(main_matriz, f"probe_{probe_name}"))
    assert f'envelope_key="{envelope_key}"' in source
    assert "envelope_key=None" not in source


@pytest.mark.parametrize("probe_name", sorted(_RISK_ENVELOPE_KEYS))
def test_risk_probe_is_treated_as_a_single_resource_envelope(probe_name: str) -> None:
    """Un envelope Risk envuelve un dict; tratarlo como list envelope daría FINDING.

    ``_envelope_probe`` decide dict-vs-list por NOMBRE de probe. Si un rename
    dejara el nombre fuera del set, la probe reportaría un SHAPE finding falso
    en cada corrida en vivo en vez de pasar.
    """
    source = inspect.getsource(main_matriz._envelope_probe)
    assert f'"{probe_name}"' in source, (
        f"{probe_name} no figura en el set `expected_dict` de `_envelope_probe`; "
        "su envelope se validaría como list y fabricaría un SHAPE finding."
    )
