"""Phase 33 criterion 4 — cycle closure is green for all five packages, NON-vacuously.

``verify_cycle_closure`` answers exactly one question: does every finding in
status ``CONFIRMED``/``FIXED`` carry a ``Regression:`` bullet that resolves to a
real test? It has two documented escape hatches, and before Phase 33 both were
wide open on this repo:

* it returns ``(True, [])`` for a findings file that does **not exist** — so a
  deleted or renamed file reads as a pass;
* it returns ``(True, [])`` when **no** finding is ``CONFIRMED``/``FIXED`` — the
  filter simply has nothing to walk.

Measured pre-phase (``33-RESEARCH.md`` Pitfall P-7), the inspected counts were
ámbito **0**, higyrus **0**, iol **1**, matriz **1**, market-data **50**. Two of
the five therefore PASSed while inspecting nothing at all, and reporting
criterion 4 from that state is the false clean this milestone exists to remove
(D-11, T-33-40).

This file replaces ``verification/test_cycle_closure_market_data.py``'s single
shared ``>= 34`` literal with a PER-PACKAGE floor, and — the part that matters —
refuses to write a ``>= 0`` floor for the two packages whose Phase 33
contribution is zero. A ``>= 0`` assertion is precisely the vacuous green this
file exists to prevent; it would read like a bound and mean nothing. Those two
rows carry an argued, positive exemption instead, so a later reader can tell an
exemption from an oversight.

Structural only: regex over markdown, ``ast.parse`` sobre ``main_matriz.py``, y
—desde la Phase 39— import del predicado de cierre de ciclo de ese mismo driver,
que es una función de módulo pura (mismo patrón que ``_venue_token``: el
predicado se verifica sin correr el driver). No se toca la red, no se construye
ningún cliente y no se ejecuta ``main()``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from verification.cycle_report import _iter_findings, verify_cycle_closure
from verification.findings import findings_path

_REPO_ROOT = Path(__file__).resolve().parent.parent

_PACKAGES = (
    "ambito-financiero-client",
    "higyrus-client",
    "iol-client",
    "matriz-client",
    "market-data-client",
)

# MEASURED, not estimated. Each number is the count of CONFIRMED/FIXED findings
# ``verify_cycle_closure`` actually inspected for that package BEFORE Phase 33
# ran, recorded in ``33-RESEARCH.md`` Pitfall P-7 and re-measured by plan 33-07
# before promoting anything.
_PRE_PHASE_BASELINE = {
    "ambito-financiero-client": 0,
    "higyrus-client": 0,
    "iol-client": 1,
    "matriz-client": 1,
    "market-data-client": 50,
}

# Findings plan 33-07 promoted OUT of ``OPEN`` into ``FIXED``. Only
# market-data-client received any: it is the one package of the five whose live
# run produced divergences (ámbito measured a true zero, iol measured a true
# zero, and higyrus and matriz could not run at all).
#
# The 38 are the four fix families, each with its regression test:
#   S-1  envelope unwrap ............ F-82  F-83  F-102 F-103   (4)
#   SC-1 preview envelope ........... F-121..F-132, F-152..F-163 (24)
#   SC-2 snapshot Optional .......... F-72  F-73  F-75  F-92  F-93  F-95 (6)
#   SC-3 Symbol timestamps .......... F-110 F-111 F-141 F-142   (4)
_PHASE_33_PROMOTIONS = {
    "ambito-financiero-client": 0,
    "higyrus-client": 0,
    "iol-client": 0,
    "matriz-client": 0,
    "market-data-client": 38,
}

_LOWER_BOUND = {pkg: _PRE_PHASE_BASELINE[pkg] + _PHASE_33_PROMOTIONS[pkg] for pkg in _PACKAGES}

# El censo de la Phase 33 fue archivado con su milestone: la ruta original bajo
# ``.planning/phases/`` ya no existe y las dos exenciones argumentadas —las
# únicas que lo leen— fallaban con ``FileNotFoundError``. Un guard que muere por
# una ruta obsoleta no es un guard: es un rojo permanente que se aprende a
# ignorar. Repuntado, no relajado (Phase 39).
_CENSUS = (
    _REPO_ROOT
    / ".planning"
    / "milestones"
    / "v1.6-phases"
    / "33-verificaci-n-en-vivo-en-modo-estricto-fixes"
    / "33-CENSUS.md"
)

# The verbatim strict-pass SUMMARY line ámbito's driver printed on 2026-08-27,
# transcribed into the census. It is the positive evidence that the driver RAN:
# a non-zero probe count alongside the two zeros.
_AMBITO_STRICT_SUMMARY = (
    "ambito      P2 strict SUMMARY: PASS=6  FAIL=0 SKIPPED=1  "
    "FINDING=0  DIVERGENCES=0  HANDLER_ERRORS=0"
)


def _applicable(pkg: str) -> list[tuple[str, str, str | None]]:
    """The findings ``verify_cycle_closure`` actually filters on, for ``pkg``."""
    text = findings_path(pkg).read_text(encoding="utf-8")
    return [row for row in _iter_findings(text) if row[1] in ("CONFIRMED", "FIXED")]


def _statuses(pkg: str) -> list[str]:
    text = findings_path(pkg).read_text(encoding="utf-8")
    return [status for _fid, status, _reg in _iter_findings(text)]


def _ambito_declares_zero_models() -> tuple[int, list[str]]:
    """Parse ámbito's ``models.py`` and return ``(class_count, __all__ names)``.

    Read as TEXT and parsed with ``ast`` — importing the package would run
    ``load_dotenv()`` at import time, which every other gate in this repo
    forbids by name.
    """
    source = (
        _REPO_ROOT
        / "packages"
        / "ambito-financiero-client"
        / "src"
        / "ambito_financiero_client"
        / "models.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    exported: list[str] = []
    for node in ast.walk(tree):
        targets = [node.target] if isinstance(node, ast.AnnAssign) else getattr(node, "targets", [])
        if not isinstance(node, ast.Assign | ast.AnnAssign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
            continue
        value = node.value
        if isinstance(value, ast.List):
            exported = [
                e.value
                for e in value.elts
                if isinstance(e, ast.Constant) and isinstance(e.value, str)
            ]
    return len(classes), exported


@pytest.mark.parametrize("pkg", _PACKAGES)
def test_cycle_closure_is_green(pkg: str) -> None:
    """Every CONFIRMED/FIXED finding resolves to a real regression test."""
    ok, missing = verify_cycle_closure(pkg)
    assert ok, (
        f"{pkg}: cycle closure is NOT green. Findings whose Regression: bullet "
        f"is absent or does not resolve to an existing `def <test>(`: {missing}"
    )
    assert missing == []


@pytest.mark.parametrize("pkg", _PACKAGES)
def test_cycle_closure_is_not_vacuous(pkg: str) -> None:
    """The green above came from inspecting findings, not from an empty filter.

    Three packages carry a NUMERIC floor derived from the measured pre-phase
    baseline plus this phase's promotions. Two carry an argued exemption
    instead, because their floor would be ``0`` and a ``>= 0`` assertion is the
    vacuous green this test exists to prevent.
    """
    path = findings_path(pkg)
    assert path.exists(), (
        f"{pkg}: {path} does not exist. verify_cycle_closure returns (True, []) "
        "for a nonexistent file, so its green result above would be meaningless."
    )

    bound = _LOWER_BOUND[pkg]
    applicable = _applicable(pkg)

    if bound == 0:
        _assert_zero_contribution_is_argued(pkg)
        return

    assert applicable, (
        f"{pkg}: no finding is CONFIRMED/FIXED, so the closure check had nothing "
        f"to validate. Statuses seen: {sorted(set(_statuses(pkg)))}"
    )
    assert len(applicable) >= bound, (
        f"{pkg}: the closure gate inspected {len(applicable)} findings but the "
        f"floor is {bound} = pre-phase baseline {_PRE_PHASE_BASELINE[pkg]} "
        f"+ Phase 33 promotions {_PHASE_33_PROMOTIONS[pkg]}. A count BELOW the "
        "floor means findings were demoted, deleted or never promoted — not that "
        "the bound is stale. Re-measure before touching this number."
    )


def _assert_zero_contribution_is_argued(pkg: str) -> None:
    """Positive exemption for the two packages whose Phase 33 contribution is 0.

    Neither gets a ``>= 0`` bound. Each gets the specific property that makes
    its zero a RESULT rather than an absence of measurement.
    """
    census = _CENSUS.read_text(encoding="utf-8")
    statuses = _statuses(pkg)

    if pkg == "ambito-financiero-client":
        # D-12: zero model classes → zero walker calls → zero divergences. The
        # zero is structural, and the driver DID run: 6 probes passed while
        # handler.seen and handler.errors were both empty. A driver that never
        # ran would show the same two zeros AND a zero probe count.
        class_count, exported = _ambito_declares_zero_models()
        assert class_count == 0, (
            "ambito-financiero-client now declares "
            f"{class_count} model class(es). D-12 no longer holds, so its "
            "cycle-closure exemption no longer holds either: it can produce "
            "divergences now and needs a real numeric floor."
        )
        assert exported == [], (
            f"ambito-financiero-client models.__all__ is no longer empty ({exported}); "
            "see the assertion above — the exemption is void."
        )
        assert _AMBITO_STRICT_SUMMARY in census, (
            "33-CENSUS.md no longer carries ámbito's verbatim strict-pass SUMMARY "
            "line. That line is the POSITIVE evidence that the driver ran (6 "
            "probes PASSed) rather than silently doing nothing, and it is the "
            "only thing separating this exemption from an unmeasured zero."
        )
        assert "OPEN" not in statuses, (
            f"ambito-financiero-client has findings still awaiting triage: {statuses}"
        )
        return

    if pkg == "higyrus-client":
        # NOT a structural zero and deliberately NOT reported as one. The vendor
        # host does not resolve by DNS from this network, so the package was
        # never measured. Its closure green is HONESTLY vacuous, the census says
        # so in those words, and the repair has a named destination. Asserting
        # that here makes the vacuity legible instead of hiding it behind a
        # bound that would pass for the wrong reason.
        assert "SKIPPED — vendor inalcanzable" in census, (
            "33-CENSUS.md no longer records higyrus-client as "
            "'SKIPPED — vendor inalcanzable'. Its cycle-closure green is vacuous "
            "BY MEASUREMENT ABSENCE, and that has to stay written down: without "
            "it, a reader would take the green for a clean bill of health on a "
            "package whose >=22 floor has never been contrasted."
        )
        assert "LIVE-HIGY-33" in census, (
            "higyrus-client's unmeasured floor lost its named destination "
            "(LIVE-HIGY-33). A deferral without a destination is exactly what "
            "P-03 forbids."
        )
        assert "OPEN" not in statuses, (
            f"higyrus-client has findings still awaiting triage: {statuses}"
        )
        return

    raise AssertionError(  # pragma: no cover - guards the exemption list itself
        f"{pkg} has a zero lower bound but no argued exemption. Add one, or give "
        "it a real numeric floor — a silent `>= 0` is not available."
    )


# ---------------------------------------------------------------------------
# Phase 39 D-09 — el cierre de ciclo decide por EVIDENCIA POSITIVA DE CORRIDA
# ---------------------------------------------------------------------------
#
# Los tests de arriba pinean que el green no es vacuo *para el estado
# committeado del repo*. Los de abajo pinean la costura que lo impide a futuro:
# el loop de cuatro paquetes de ``main_matriz.py`` sólo puede emitir PASS con un
# conteo de probes > 0 en el sobre de evidencia, y sin sobre emite SKIPPED con
# destino nombrado en vez de un PASS que no significa nada.
#
# El predicado NO es "al menos un finding CONFIRMED/FIXED" — el que usa
# ``main_market_data.py``. Ese criterio reprobaría a ámbito (cero por declarar
# cero clases de modelo) y a higyrus (cero por no haber sido medido): dos causas
# opuestas con el mismo veredicto. Esa distinción es lo que estos tests fijan.


def _matriz_source() -> str:
    return (_REPO_ROOT / "main_matriz.py").read_text(encoding="utf-8")


def _cycle_closure_loop() -> ast.For:
    """El ``for pkg in (...)`` de cuatro slugs dentro de ``main()``.

    Localizado por su iterable —una tupla de constantes string que contiene los
    cuatro slugs—, no por número de línea: el número se mueve con cada edición y
    un guard que apunta a una línea vieja se apaga solo.
    """
    tree = ast.parse(_matriz_source())
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.iter, ast.Tuple):
            continue
        slugs = [
            e.value
            for e in node.iter.elts
            if isinstance(e, ast.Constant) and isinstance(e.value, str)
        ]
        if set(_PACKAGES) - {"market-data-client"} <= set(slugs):
            return node
    raise AssertionError(
        "no se encontró el loop de cierre de ciclo de 4 paquetes en main_matriz.py. "
        "Si se movió o se renombró, este guard quedó apuntando a nada."
    )


def _called_names(node: ast.AST) -> set[str]:
    return {
        n.func.id
        for n in ast.walk(node)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }


def test_el_loop_consulta_la_evidencia_de_corrida() -> None:
    """El loop lee ``probes_executed`` — la evidencia positiva — antes de decidir."""
    called = _called_names(_cycle_closure_loop())

    assert "probes_executed" in called, (
        "el loop de cierre de ciclo dejó de consultar el conteo de probes. Sin "
        "ese predicado, verify_cycle_closure devuelve (True, []) también cuando "
        "el archivo de findings no existe, y el PASS resultante no distingue "
        "'todo enlazado' de 'nada que validar' — el PASS vacuo que SC-3 prohíbe."
    )
    assert "verify_cycle_closure" in called, (
        "el loop dejó de llamar a verify_cycle_closure: el endurecimiento debe "
        "ENVOLVER esa función, no rodearla. Su guard de path traversal sobre la "
        "ruta del bullet Regression (T-39-11) tiene que seguir en el camino."
    )


def test_el_loop_no_decide_por_conteo_de_findings_promovidos() -> None:
    """Pitfall 6: el predicado de market-data NO se copia acá.

    ``main_market_data.py`` reprueba un cierre de ciclo con cero findings
    CONFIRMED/FIXED. Ese criterio es correcto para market-data (50 findings
    promovidos) y ERRÓNEO para ámbito y higyrus, cuyos ceros no son defectos.
    """
    loop = _cycle_closure_loop()
    called = _called_names(loop)

    assert "findings_path" not in called, (
        "el loop de cierre de ciclo empezó a leer el archivo de findings para "
        "contar promociones. Ese es el predicado de main_market_data.py y "
        "reprobaría a ámbito y a higyrus por estar limpio uno y sin medir el "
        "otro (Pitfall 6). El predicado correcto es el conteo de probes."
    )
    names = {n.id for n in ast.walk(loop) if isinstance(n, ast.Name)}
    assert not any("CLOSED_STATUS" in name for name in names), (
        f"el loop referencia un regex de estados cerrados ({sorted(names)}): el "
        "conteo de findings promovidos volvió a ser el criterio de decisión."
    )


def test_sin_evidencia_el_veredicto_es_skipped_con_destino_nombrado() -> None:
    """Cero probes ⇒ SKIPPED, nunca PASS, y siempre con destino."""
    import main_matriz

    status, detail = main_matriz._cycle_closure_verdict(
        "iol-client", probes=0, evidence=None, ok=True, missing=[]
    )

    assert status == "SKIPPED", (
        "un paquete sin evidencia de corrida obtuvo un veredicto distinto de "
        "SKIPPED. verify_cycle_closure devolvió ok=True porque no había nada "
        "que validar; promoverlo a PASS es el cero silencioso que D-09 prohíbe."
    )
    assert "sin evidencia de corrida" in detail
    assert "LIVE-NOBJ-01" in detail, (
        f"el SKIPPED perdió su destino nombrado: {detail!r}. Un deferral sin "
        "destino es exactamente lo que P-03 prohíbe."
    )


def test_la_causa_medida_del_sobre_viaja_al_detalle() -> None:
    """Un sobre de corrida saltada aporta SU causa, no una genérica."""
    import main_matriz

    status, detail = main_matriz._cycle_closure_verdict(
        "higyrus-client",
        probes=0,
        evidence={"skipped": "vendor host unreachable (DNS) — LIVE-HIGY-33"},
        ok=True,
        missing=[],
    )

    assert status == "SKIPPED"
    assert "vendor host unreachable (DNS)" in detail
    assert detail.count("LIVE-HIGY-33") == 1, (
        f"el destino se duplicó o desapareció en {detail!r}: la causa del sobre "
        "ya lo trae, así que el veredicto no debe volver a concatenarlo."
    )


def test_un_paquete_limpio_que_corrio_da_pass() -> None:
    """Cero findings promovidos + probes > 0 ⇒ PASS. Éste es el pin de Pitfall 6."""
    import main_matriz

    status, detail = main_matriz._cycle_closure_verdict(
        "ambito-financiero-client",
        probes=7,
        evidence={"captured_at": "2026-08-29T12:00:00+00:00", "probes_executed": 7},
        ok=True,
        missing=[],
    )

    assert status == "PASS", (
        "un paquete que CORRIÓ y no tiene findings promovidos fue reprobado. "
        "Ámbito declara cero clases de modelo: su cero es un resultado medido, "
        "no una ausencia de medición, y reprobarlo por estar limpio invierte el "
        "significado del gate."
    )
    assert "7" in detail, f"el PASS no transcribe el conteo de probes: {detail!r}"
    assert "2026-08-29T12:00:00+00:00" in detail, (
        f"el PASS no transcribe el captured_at del sobre: {detail!r}. Ese par "
        "(conteo, timestamp) ES la evidencia positiva que el censo copia."
    )


def test_regresiones_faltantes_siguen_dando_fail() -> None:
    """Comportamiento previo preservado: probes > 0 y ok=False ⇒ FAIL."""
    import main_matriz

    status, detail = main_matriz._cycle_closure_verdict(
        "matriz-client",
        probes=24,
        evidence={"captured_at": "2026-08-29T12:00:00+00:00"},
        ok=False,
        missing=["F-07", "F-11"],
    )

    assert status == "FAIL"
    assert "F-07" in detail
    assert "F-11" in detail


def test_no_correr_no_escribe_finding() -> None:
    """El camino SKIPPED no es un defecto, así que no toca el ledger."""
    loop = _cycle_closure_loop()
    append_calls = [
        n
        for n in ast.walk(loop)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "append_finding"
    ]

    assert len(append_calls) == 1, (
        f"el loop tiene {len(append_calls)} llamadas a append_finding; debe "
        "tener exactamente una, la del camino FAIL."
    )
    guards = [
        n
        for n in ast.walk(loop)
        if isinstance(n, ast.If)
        and any(
            isinstance(c, ast.Call)
            and isinstance(c.func, ast.Name)
            and c.func.id == "append_finding"
            for c in ast.walk(n)
        )
    ]
    assert guards, (
        "la llamada a append_finding del loop quedó sin guarda: se escribiría un "
        "finding ERROR-MAP también en el camino SKIPPED, convirtiendo 'no corrió' "
        "en un defecto del paquete."
    )
    guard_src = ast.unparse(guards[0].test)
    assert "FAIL" in guard_src, (
        f"la guarda del append_finding es {guard_src!r}: ya no discrimina el "
        "camino FAIL del camino SKIPPED."
    )


def test_los_destinos_nombrados_son_tres_mas_default() -> None:
    """Higyrus y matriz tienen destino propio; el resto cae al default."""
    import main_matriz

    assert main_matriz._cycle_closure_destination("higyrus-client") == "LIVE-HIGY-33"
    assert main_matriz._cycle_closure_destination("matriz-client") == "LIVE-MATZ-33"
    assert main_matriz._cycle_closure_destination("iol-client") == "LIVE-NOBJ-01"
    assert main_matriz._cycle_closure_destination("ambito-financiero-client") == "LIVE-NOBJ-01"


def test_el_acoplamiento_del_loop_esta_documentado() -> None:
    """El loop vive en el driver de matriz: si matriz no corre, nadie recibe veredicto.

    El acoplamiento es una consecuencia deliberada de dónde se implantó la
    costura (Open Question 2 de RESEARCH). Declararlo en el fuente es lo que
    separa una limitación conocida de una sorpresa: sin la nota, un lector del
    censo tomaría el silencio de los cuatro paquetes por un resultado limpio.
    """
    source = _matriz_source()

    assert "NO CORRIÓ — LIVE-MATZ-33" in source, (
        "main_matriz.py perdió la nota que declara qué debe registrar el censo "
        "cuando el gate D-MATZ-33 impide que el loop corra: 'cycle_closure: NO "
        "CORRIÓ — LIVE-MATZ-33' para los cuatro paquetes, nunca un silencio."
    )


def test_el_sobre_de_evidencia_es_la_entrada_del_predicado() -> None:
    """El predicado se apoya en ``verification.run_evidence``, no en un contador local."""
    source = _matriz_source()

    assert "probes_executed" in source
    assert "read_run_evidence" in source, (
        "main_matriz.py dejó de leer el sobre de evidencia: sin él no puede "
        "transcribir ni la causa medida del skip ni el captured_at del PASS."
    )


def test_the_two_exemptions_are_the_only_ones() -> None:
    """No third package may drift into the argued-exemption path unnoticed.

    The exemption branch is the weakest assertion in this file, so the set of
    packages allowed to reach it is pinned. A package whose floor drops to zero
    — because a baseline was edited down, or a promotion count zeroed — lands
    here loudly instead of quietly acquiring an exemption it was never argued.
    """
    zero_floor = {pkg for pkg in _PACKAGES if _LOWER_BOUND[pkg] == 0}
    assert zero_floor == {"ambito-financiero-client", "higyrus-client"}, (
        f"packages reaching the argued-exemption path changed: {sorted(zero_floor)}"
    )
