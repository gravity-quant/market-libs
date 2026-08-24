"""Shared type vocabulary for the Ambito Financiero client -- deliberately empty.

This module is a **placeholder by decision, not by oversight**. It exists so the
six packages of this workspace present the same file layout (Phase 31, TYP-03)
and the next endpoint is born with somewhere to put its enum-like vocabulary,
instead of inventing a new home per package.

It carries no :class:`~typing.Literal` aliases yet, and that is the point.
``.planning/phases/29-decoder-observable/29-DLOCK-RESPONSE-LITERAL.md`` is the
signed lock under which **response fields are never closed as ``Literal`` in this
milestone**: such a field decodes as ``str``, and a wire value outside the
documented set is reported as a divergence and returned unchanged -- never
rejected, never coerced, never defaulted. The one promotion already identified
across the workspace -- ``iol_client``'s ``mercado`` and ``plazo`` -- is
**deferred to Phase 33**, pending a live census of the values the APIs emit.

:mod:`matriz_client.types` is the shape this module grows into once that census
lands: a small catalogue of enum-like aliases, with payload shapes staying in
``models.py``.

This module is **not** re-exported into :mod:`ambito_financiero_client`'s
``__all__``: doing so would add rows to
``verification/snapshots/ambito-financiero-client-surface.txt``, and this phase
changes the layout, not the public surface.
"""

from __future__ import annotations

__all__: list[str] = []
