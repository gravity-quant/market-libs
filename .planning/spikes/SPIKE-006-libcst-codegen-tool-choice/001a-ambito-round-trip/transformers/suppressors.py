"""``Suppressors`` — pure RemovalSentinel deletion of aio-only constructs (D-03).

The hand-written sync ``client.py`` is NOT merely ``aio.py`` with ``async`` stripped: it
OMITS several async-only constructs. To hit byte-identity at generation time (never by
editing ``aio.py``), this transformer removes:

- ``import warnings``                       — only async ``configure()`` warns (``aio.py:27``)
- the WR-07 ``ResourceWarning`` block        — the nested ``if prior_http_client is not None:
                                               warnings.warn(..., ResourceWarning, …)`` inside
                                               async ``configure()`` (``aio.py:~234-242``)
- the ``prior_http_client = …`` assignment   — feeds only the WR-07 block (aio-only)
- the ``"aclose"`` ``__all__`` entry         — no sync ``aclose`` delegator exists in client.py

The module-level ``aclose()`` delegator itself (``aio.py:266-268``) is removed by the DRIVER,
not here: distinguishing the module-level def from the (renamed) class method requires module
SCOPE, which is cross-cutting orchestration (item-9 / Pattern 2). Every ``leave_*`` below is a
pure per-node decision — no accumulation, no I/O.
"""

from __future__ import annotations

import libcst as cst


class Suppressors(cst.CSTTransformer):
    """Pure: each removal is a function of the single node visited."""

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine | cst.RemovalSentinel:
        if len(updated_node.body) == 1:
            stmt = updated_node.body[0]
            # `import warnings`
            if isinstance(stmt, cst.Import) and any(
                isinstance(a.name, cst.Name) and a.name.value == "warnings"
                for a in stmt.names
            ):
                return cst.RemovalSentinel.REMOVE
            # `prior_http_client = …` (feeds only the WR-07 block)
            if isinstance(stmt, cst.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0].target
                if isinstance(target, cst.Name) and target.value == "prior_http_client":
                    return cst.RemovalSentinel.REMOVE
        return updated_node

    def leave_If(
        self, original_node: cst.If, updated_node: cst.If
    ) -> cst.If | cst.RemovalSentinel:
        # The WR-07 guard: `if prior_http_client is not None:` (contains warnings.warn).
        test = updated_node.test
        if (
            isinstance(test, cst.Comparison)
            and isinstance(test.left, cst.Name)
            and test.left.value == "prior_http_client"
        ):
            return cst.RemovalSentinel.REMOVE
        return updated_node

    def leave_Element(
        self, original_node: cst.BaseElement, updated_node: cst.BaseElement
    ) -> cst.BaseElement | cst.RemovalSentinel:
        # Prune the `"aclose"` entry from `__all__` (no sync delegator twin).
        value = updated_node.value
        if isinstance(value, cst.SimpleString) and value.value.strip("\"'") == "aclose":
            return cst.RemovalSentinel.REMOVE
        return updated_node
