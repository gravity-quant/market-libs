"""Cross-cutting logging.root snapshot guard — packages MUST NOT touch root logger.

Phase 8 D-14, D-26, D-27, LOG-01 / Pitfall 6. Wave 1 tests-first guard; passes
GREEN in HEAD trivially (no _logging.py yet) AND continues GREEN as Plans 2-5
add the per-package ``getLogger("<pkg>")`` + NullHandler attach pattern.

Invariant: importing any of the 4 paquetes MUST NOT add handlers to
``logging.root``, MUST NOT add filters to ``logging.root``, MUST NOT change
``logging.root.level``. Library code attaches NullHandler + RedactingFilter to
``logging.getLogger("<pkg>")`` ONLY — never the root logger. This prevents
library-induced hijacking of consumer applications' log configuration
(``logging.basicConfig`` / ``logging.root.addHandler`` is the canonical
anti-pattern called out in the Python logging HOWTO).

This guard is the regression-test layer of the 3-layer defense (D-27):
1. ruff LOG ruleset (catches ``logging.root.*`` direct calls statically)
2. CI grep step (catches ``logging.basicConfig`` which ruff LOG does NOT cover)
3. **This test** — runtime snapshot diff (catches anything the static checks miss)
"""

from __future__ import annotations

import importlib
import logging


def test_importing_packages_does_not_modify_logging_root() -> None:
    """LOG-01: importing all 4 paquetes MUST NOT modify logging.root state.

    Snapshots ``logging.root.handlers``, ``logging.root.filters``, and
    ``logging.root.level`` BEFORE re-importing each paquete. Re-imports via
    ``importlib.import_module`` (idempotent for already-imported modules — the
    cached module is returned). Re-asserts state unchanged.

    NOTE: pytest's caplog fixture installs handlers on root by design. This test
    deliberately does NOT request caplog. The snapshot is therefore taken under
    a "user code" view, not "test harness" view.
    """
    handlers_before = list(logging.root.handlers)
    filters_before = list(logging.root.filters)
    level_before = logging.root.level

    for pkg_name in [
        "ambito_financiero_client",
        "iol_client",
        "higyrus_client",
        "matriz_client",
    ]:
        importlib.import_module(pkg_name)

    assert list(logging.root.handlers) == handlers_before, (
        f"logging.root.handlers drifted after package import.\n"
        f"  before: {handlers_before!r}\n"
        f"  after:  {list(logging.root.handlers)!r}\n"
        f"Library code MUST attach NullHandler to its own logger only "
        f"(per D-13, D-14, LOG-01)."
    )
    assert list(logging.root.filters) == filters_before, (
        f"logging.root.filters drifted after package import.\n"
        f"  before: {filters_before!r}\n"
        f"  after:  {list(logging.root.filters)!r}"
    )
    assert logging.root.level == level_before, (
        f"logging.root.level drifted from {level_before} to {logging.root.level} "
        f"after package import. Library code MUST NOT call logging.basicConfig "
        f"or logging.root.setLevel."
    )
