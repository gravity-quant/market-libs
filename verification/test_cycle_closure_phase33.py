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

Structural only: regex over markdown plus ``ast.parse`` over one source file. No
package is imported, no network is touched, no client is constructed.
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

_CENSUS = (
    _REPO_ROOT
    / ".planning"
    / "phases"
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
