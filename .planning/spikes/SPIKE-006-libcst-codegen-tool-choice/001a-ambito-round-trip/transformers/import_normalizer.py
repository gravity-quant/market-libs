"""``ImportNormalizer`` — pure alphabetical alias-order for the bare-package import (item 4).

After ``AsyncToSync`` renames ``_atransport → _transport``, the ámbito source line
``from ambito_financiero_client import _transport, _core`` is non-alphabetical and trips
ruff I001. This transformer sorts the alias list of the ``from ambito_financiero_client
import …`` statement (bare package only) into alphabetical order, matching hand-written
``client.py``. Pure per-node; no I/O, no accumulation.
"""

from __future__ import annotations

import libcst as cst

_TARGET_MODULE = "ambito_financiero_client"


class ImportNormalizer(cst.CSTTransformer):
    """Pure: sorts one ImportFrom's alias list; visits each node independently."""

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        module = updated_node.module
        # Only the bare `from ambito_financiero_client import …` (a Name module, not an
        # Attribute like `ambito_financiero_client.client`, and not `__future__`).
        if not isinstance(module, cst.Name) or module.value != _TARGET_MODULE:
            return updated_node
        names = updated_node.names
        if isinstance(names, cst.ImportStar) or len(names) < 2:
            return updated_node
        ordered = sorted(names, key=lambda a: a.name.value)
        if [a.name.value for a in ordered] == [a.name.value for a in names]:
            return updated_node
        # Re-attach a trailing-comma policy: drop each alias's comma, then let the last
        # alias carry no comma (libcst default) so the emitted list is `_core, _transport`.
        rebuilt = [a.with_changes(comma=cst.MaybeSentinel.DEFAULT) for a in ordered]
        return updated_node.with_changes(names=rebuilt)
