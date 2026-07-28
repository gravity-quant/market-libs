"""``ImportDirectionNormalizer`` — pure removal of a self-import that is redundant because
the name is locally defined (Q1 content-absence boundary).

The import-DIRECTION asymmetry is: ``client.py`` DEFINES ``_validate_max_retries`` (a 22-line
``def``, ``client.py:41-62``) while ``aio.py`` only IMPORTS it
(``from ambito_financiero_client.client import _validate_max_retries``, ``aio.py:34``).

Relocating a def across emitted modules is inherently cross-module orchestration and would
require STATE — so it does NOT live here (item-9 / Pitfall 5). Instead this transformer takes
an **immutable frozenset of names known to be locally defined in the emitted module**
(computed by the impure driver by scanning ``module.body``) and strips a
``from <pkg>.client import <name>`` self-import IFF ``<name>`` is in that set. Passing an
immutable config at ``__init__`` is read-only closed-over data — NOT cross-node accumulation —
so purity (item 9) holds (asserted as ``vars(t)`` unchanged before/after visit).

Q1 CONSEQUENCE (the decisive item-1/item-6 evidence): for the un-migrated ámbito ``aio.py``,
``_validate_max_retries`` has NO local ``def`` — it is content that exists only in the ORACLE
``client.py``, which D-02/D-03 forbid reading as a donor. So the driver passes an EMPTY set,
the self-import is RETAINED, and the generated module reproduces the exact SPIKE-005 item-6
``ImportError: cannot import name '_validate_max_retries' from partially initialized module``.
That is an honest FAIL — a valid, guaranteed deliverable (D-04/D-08), never bypassed.
"""

from __future__ import annotations

import libcst as cst

_SELF_IMPORT_MODULE = "ambito_financiero_client.client"


def _module_dotted(node: cst.BaseExpression | None) -> str:
    """Render an ImportFrom module expression (Name / Attribute) as a dotted string."""
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        return f"{_module_dotted(node.value)}.{node.attr.value}"
    return ""


class ImportDirectionNormalizer(cst.CSTTransformer):
    """Pure: config-at-init (immutable frozenset), no cross-node state, no I/O."""

    def __init__(self, locally_defined: frozenset[str]) -> None:
        super().__init__()
        # Immutable read-only config — NOT accumulated across visits.
        self._locally_defined = locally_defined

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom | cst.RemovalSentinel:
        if _module_dotted(updated_node.module) != _SELF_IMPORT_MODULE:
            return updated_node
        names = updated_node.names
        if isinstance(names, cst.ImportStar):
            return updated_node
        imported = {a.name.value for a in names}
        # Strip the self-import only if EVERY imported name is locally defined in the
        # emitted module (redundant). If any name is content-absent, retain verbatim (Q1).
        if imported and imported <= self._locally_defined:
            return cst.RemovalSentinel.REMOVE
        return updated_node
