"""D-18 / D-21 — market-data-client cycle closure is green and non-vacuously so.

Before Phase 27 ``verify_cycle_closure("market-data-client")`` returned
``(False, 34)``: F-03..F-36 were all ``FIXED`` with no ``Regression:`` bullet,
while the other four packages returned ``(True, [])``. The fixes for those 34
findings already existed (the v1.4 sweep plus quick tasks ``260731-j93``,
``260731-jim`` and ``260731-t9o``) — they were simply never linked, so the
structural validator could not see them.

The backfill links each finding to the test that actually proves its
reconciliation. ``verification.cycle_report`` validates that the path resolves
under the repo root and that the file literally contains ``def <test_name>(``,
but it cannot check that the test is *relevant* — hence the second test below,
which pins the vacuous-pass escape hatches:

- ``verify_cycle_closure`` returns ``(True, [])`` when the findings file does
  **not exist** (nothing to validate), so a deleted or renamed file would read
  as a pass.
- It also passes vacuously if no finding is in ``CONFIRMED``/``FIXED``, since
  only those two statuses participate in the check.
"""

from __future__ import annotations

from verification.cycle_report import _iter_findings, verify_cycle_closure
from verification.findings import findings_path

_PKG = "market-data-client"


def test_market_data_cycle_closure_is_green() -> None:
    """D-18/D-21 — todos los findings CONFIRMED/FIXED enlazan a un test real."""
    ok, missing = verify_cycle_closure(_PKG)
    assert ok, f"cycle closure not green; findings without a resolvable Regression link: {missing}"
    assert missing == []


def test_market_data_cycle_closure_is_not_vacuous() -> None:
    """El pass NO viene de un archivo ausente ni de cero findings aplicables."""
    path = findings_path(_PKG)
    assert path.exists(), (
        f"{path} is missing — verify_cycle_closure returns (True, []) for a "
        "nonexistent file, so its green result would be meaningless"
    )

    statuses = [status for _fid, status, _reg in _iter_findings(path.read_text(encoding="utf-8"))]
    applicable = [s for s in statuses if s in ("CONFIRMED", "FIXED")]
    assert applicable, (
        "no finding is CONFIRMED/FIXED, so the closure check had nothing to "
        f"validate; statuses seen: {sorted(set(statuses))}"
    )
    # El backfill de Phase 27 cubrió 34 findings FIXED (F-03..F-36).
    assert len(applicable) >= 34, f"expected >= 34 applicable findings, got {len(applicable)}"
