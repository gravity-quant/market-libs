"""Shared type vocabulary for the Invertir Online client -- deliberately empty.

This module is a **placeholder by decision, not by oversight**. It exists so the
six packages of this workspace present the same file layout (Phase 31, TYP-03)
and the next endpoint is born with somewhere to put its enum-like vocabulary,
instead of inventing a new home per package.

It carries no :class:`~typing.Literal` aliases yet, and that is the point.
``.planning/phases/29-decoder-observable/29-DLOCK-RESPONSE-LITERAL.md`` is the
signed lock under which **response fields are never closed as ``Literal`` in this
milestone**: such a field decodes as ``str``, and a wire value outside the
documented set is reported as a divergence and returned unchanged -- never
rejected, never coerced, never defaulted.

**DT-07 is CLOSED: ``mercado`` and ``plazo`` stay ``str``, permanently.** The
live census ran in Phase 33 (plan 33-06) over 2 191 ``Titulo`` rows across the
six instrument types, and it is the census -- not its absence -- that decides
the outcome. The RESPONSE side emits ``mercado`` as ``{"1"}`` and ``plazo`` as
``{"T0", "T1"}``, while the INPUT parameters these very functions default to are
``mercado="bcba"`` and ``plazo="t2"``: the two vocabularies are numeric-vs-name
for one field and disjoint-by-case for the other. A ``Literal`` closed on the
observed response set would reject the library's own defaults, and the set a
vendor *emits* is in no case provably the set it *accepts* -- the only way to
observe the input domain is a deliberate 4xx sweep against a live brokerage
account, which D-10 rejects. An incomplete ``Literal`` breaks legitimate caller
input, which is strictly worse than ``str``. Evidence, row counts and full
reasoning:
``.planning/phases/33-verificaci-n-en-vivo-en-modo-estricto-fixes/33-LITERALS.md``.

This closure is scoped to those two RESPONSE fields. :data:`iol_client.InstrumentType`
is a ``Literal`` over an **input** parameter and is a different question that the
D-lock explicitly leaves open; it is unaffected.

:mod:`matriz_client.types` is still the shape this module grows into if a future
endpoint brings enum-like vocabulary that a census can close: a small catalogue
of aliases, with payload shapes staying in ``models.py``.
"""

from __future__ import annotations

__all__: list[str] = []
