"""``DocstringLocalizer`` — pure ``SimpleString.value`` label localization (item 1 docstrings).

Rewrites the raw literal of every ``SimpleString`` (docstrings AND ordinary string literals
such as the ``__all__`` entries and repr templates), applying the mechanical async→sync label
swaps and stripping ``await `` occurrences inside docstring example blocks. Triple-quote style
and internal indentation are preserved because only ``.value`` substrings are swapped — the
node structure is untouched.

CAVEAT (RESEARCH Q3, decisive): the hand-written ``client.py`` docstrings DIVERGE STRUCTURALLY
from ``aio.py`` (different examples; ``with_options`` docstring is 43 lines vs 19). These are
independently hand-authored prose, NOT ``sincrónico↔asincrónico`` swaps. This transformer only
performs the mechanical swaps; the structural prose divergence is honest item-1 residual and is
NOT closed by hardcoding the target literal (which would embed the oracle in the tool).
"""

from __future__ import annotations

import libcst as cst

# Order matters: longer substrings first so `AmbitoFinancieroAsyncClient` collapses to
# `AmbitoFinancieroClient` via the `AsyncClient`→`Client` rule.
_SWAPS: tuple[tuple[str, str], ...] = (
    ("asincrónico", "sincrónico"),
    ("AsyncClient", "Client"),
    ("await ", ""),
)


class DocstringLocalizer(cst.CSTTransformer):
    """Pure: rewrites one string literal's value; no accumulation, no I/O."""

    def leave_SimpleString(
        self, original_node: cst.SimpleString, updated_node: cst.SimpleString
    ) -> cst.SimpleString:
        value = updated_node.value
        new = value
        for src, dst in _SWAPS:
            new = new.replace(src, dst)
        if new == value:
            return updated_node
        return updated_node.with_changes(value=new)
