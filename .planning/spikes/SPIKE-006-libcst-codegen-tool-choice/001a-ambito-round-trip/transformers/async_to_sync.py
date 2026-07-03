"""``AsyncToSync`` — pure libcst ``CSTNode → CSTNode`` async→sync lowering (SPIKE-006 001a).

Strips ``async``/``await`` and applies the fixed async→sync node-rename map. Holds NO
cross-node mutable state and performs NO I/O (item-9 purity): every ``leave_*`` is a
function of the node it visits alone. The immutable ``_RENAME`` map is a module constant,
not instance state.

Deliberately DOES NOT touch the ``_raise_for_response = _core.raise_for_response`` ``Assign``
node — B8 identity must be preserved verbatim (Pitfall 4). That assignment contains no
async construct and none of the renamed names, so it passes through untouched.
"""

from __future__ import annotations

import libcst as cst

# Fixed async→sync identifier map. `AmbitoFinancieroAsyncClient` (a repr/docstring string
# literal, not a Name) is handled by DocstringLocalizer via the "AsyncClient"→"Client"
# substring swap; here we rename only `Name` nodes.
_RENAME: dict[str, str] = {
    "AsyncClient": "Client",
    "_atransport": "_transport",
    "AsyncRetryTransport": "RetryTransport",
    "aclose": "close",
    "__aenter__": "__enter__",
    "__aexit__": "__exit__",
}


class AsyncToSync(cst.CSTTransformer):
    """Pure: depends only on the node it visits; no global/instance accumulation, no I/O."""

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if updated_node.asynchronous is not None:
            return updated_node.with_changes(asynchronous=None)
        return updated_node

    def leave_Await(
        self, original_node: cst.Await, updated_node: cst.Await
    ) -> cst.BaseExpression:
        # Unwrap `await X` → `X`. All ámbito awaits wrap a simple call expression.
        return updated_node.expression

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        new = _RENAME.get(updated_node.value)
        if new is not None:
            return updated_node.with_changes(value=new)
        return updated_node
