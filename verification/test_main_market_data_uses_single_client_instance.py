"""REFAC-05 -- ``main_market_data.py`` MUST construct at most one sync
``Client`` and one async ``AsyncClient`` (the single-Client invariant, D-01/D-02).

Every probe threads exactly one ``Client()`` built in ``main()`` and one
``AsyncClient()`` built in ``_async_main()`` as parameters -- no probe reaches a
module singleton on its own. This AST gate is the merge-blocking invariant: it
counts constructor ``Call`` sites for the two client classes across the whole
driver and asserts ``1 <= count <= 2`` -- the lower bound makes the gate
non-vacuous (a driver that constructs ZERO classes, i.e. the un-migrated state,
FAILS RED rather than passing trivially).

The walker matches BOTH constructor spellings per D-05: bare ``Client()`` /
``AsyncClient()`` (``ast.Name``) and module-qualified ``md.Client()`` /
``mod.AsyncClient()`` (``ast.Attribute``). View-builder method calls are not
constructors -- the one named by its ``.``-suffixed builder (an ``ast.Attribute``
whose ``attr`` is the view builder, not a class name) is therefore excluded by
construction because its attribute is not in the constructor-name set.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_market_data.py"

# The two client constructor names. Matched whether spelled bare (``ast.Name``)
# or module-qualified (``ast.Attribute``). Nothing else counts -- in particular
# any view-builder method call (an attribute access whose name is NOT one of
# these) is not a constructor and is excluded.
_CTOR_NAMES = frozenset({"Client", "AsyncClient"})


def test_main_market_data_uses_single_client_instance() -> None:
    """AST walk: ``1 <= (Client|AsyncClient) ctor Calls <= 2`` in the driver.

    Lower bound (>=1) is the non-vacuity guard: an un-migrated driver constructs
    zero classes (all via ``_get_default()``) and so FAILS RED. The migrated driver
    constructs exactly two (one sync ``Client`` + one async ``AsyncClient``) and
    PASSES GREEN.
    """
    tree = ast.parse((_REPO_ROOT / _DRIVER).read_text(encoding="utf-8"))
    ctor_sites: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in _CTOR_NAMES:
            ctor_sites.append((node.lineno, func.id))
        elif isinstance(func, ast.Attribute) and func.attr in _CTOR_NAMES:
            ctor_sites.append((node.lineno, func.attr))
    assert 1 <= len(ctor_sites) <= 2, (
        f"{_DRIVER} constructs {len(ctor_sites)} client instance(s) (expected 1..2): {ctor_sites}"
    )
