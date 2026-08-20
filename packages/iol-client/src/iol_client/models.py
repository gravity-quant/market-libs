"""Safe-access frozen dataclasses for IOL API responses.

All response models inherit from :class:`SafeModel` and are constructed via
:meth:`SafeModel.from_api`, which tolerates partial or missing fields and
substitutes safe defaults per type:

- ``str`` -> ``""``
- ``int`` / ``float`` -> ``0`` / ``0.0``
- ``bool`` -> ``False``
- ``list[X]`` -> ``[]``
- nested ``SafeModel`` -> ``X.from_api(None)`` (empty instance)
- ``X | None`` -> ``None`` when missing (explicit opt-in to nullable)

Extra keys in the payload are ignored; missing keys fall back to defaults.
Chained access like ``quote.puntas[0].precioCompra`` never raises on a
*declared* attribute — the worst case is a final ``None`` or a zero-valued
primitive. A **misspelled** attribute, by contrast, is a hard error in both
directions: mypy rejects it statically and ``slots=True`` raises
``AttributeError`` at runtime. That is the whole point of TYP-01.

Field names follow the wire format (camelCase) verbatim so JSON parsing can
stay declarative.

Per-field coercion lives in :mod:`iol_client._decode`, the canonical walker
shared in verbatim copies across the paquetes. Every substitution emits a
structured divergence record on the ``iol_client`` logger, and an undeclared
wire key is reported too. This module owns **no** emission channel of its own:
it imports nothing outside ``__future__``, ``dataclasses``, ``typing`` and
``iol_client._decode``, and it builds no records. All observability belongs to
the frozen decoder.

DecodePolicy re-ratification (Phase 30, discharging the obligation Phase 29
left open in ``29-SEMANTICS-MATRIX.md`` Section 2)
--------------------------------------------------------------------------
Phase 29 deferred to this phase the confirmation that iol's models actually
want **typed-zero substitution** rather than matriz-style ``missing -> None``.
They do. iol's constant stays as written —
``POLICY = DecodePolicy("", 0, 0.0, False, "from_api_none", False, False)``
(:data:`iol_client._decode.POLICY`) — for three reasons:

1. Every field the live corpus observed as nullable is already declared
   ``T | None`` here (D-03), and the walker returns those as ``None``
   **without** emitting a divergence record. The fields that would benefit
   from matriz-style ``None`` already get it, by declaration.
2. matriz's ``None`` policy travels with ``scalar_passthrough=True``, which
   returns a wrong-typed wire value unchanged — an ``int`` from the wire would
   land in a field annotated ``float``, breaking the very mypy guarantee
   TYP-01 exists to provide.
3. ``literal_enforced=False`` is fixed by D-09 (a RESPONSE field is never a
   closed set) and is not a tunable in any copy.

This is a ratification, not a change: ``_decode.py`` is byte-frozen and the
constant is already the value being ratified.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Self, cast

from iol_client import _decode


class SafeModel:
    """Base class for IOL API response models.

    Subclasses must be frozen dataclasses. Construct instances via
    :meth:`from_api` to tolerate partial or missing fields.
    """

    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Build an instance from an API payload, with safe defaults."""
        kwargs = _decode.walk_model(
            cls, payload, policy=_decode.POLICY, sink=_decode.current_sink()
        )
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Re-project the model as the plain wire dict (D-08).

        Escape hatch for the dict -> model break of Phase 30, and the adapter
        the verification harness feeds to ``verification.schema.schema_of``.
        Nested models are flattened to dicts; ``None`` keys are **kept** — a
        response model must reproduce the wire shape, holes included.

        ``cast(Any, self)`` follows ``_decode.py``'s existing mypy-strict
        discipline: :class:`SafeModel` itself is not a dataclass — every
        concrete subclass is — so ``asdict``'s ``DataclassInstance`` overload
        cannot be satisfied by the base's ``self``.
        """
        wire: dict[str, Any] = dataclasses.asdict(cast(Any, self))
        return wire


@dataclass(frozen=True, slots=True)
class Punta(SafeModel):
    """One order-book level inside :attr:`Cotizacion.puntas`.

    The element shape is **inobservado**: the 2026-06-06 live capture recorded
    ``puntas: []`` for ``get_quote`` and ``null`` for the historical series, so
    these four decimal fields are the only element form the corpus has ever
    shown (D-02, FA-03). Phase 33's strict live run is what confirms them.
    """

    cantidadCompra: float
    cantidadVenta: float
    precioCompra: float
    precioVenta: float


@dataclass(frozen=True, slots=True)
class Cotizacion(SafeModel):
    """Cotización — returned by ``get_quote`` and by every row of ``get_historical_quotes``.

    Verified against the committed schema snapshots captured 2026-06-06
    (``.planning/verification/schemas/iol-client/get-quote.json`` and
    ``get-historical-quotes.json``):

    - Both endpoints carry the **same 20 keys**; they differ only in which ones
      arrive ``null``. One model therefore covers both (D-01).
    - ``descripcionTitulo``, ``plazo`` and ``puntas`` are ``Optional`` because
      the historical series sends the three of them ``null``; in ``get_quote``
      all three arrive populated (D-03). The Optional branch of the walker
      returns ``None`` for those **without** emitting a divergence record.
    - ``puntas`` element shape is inobservado — see :class:`Punta` (D-02).
    - ``cantidadOperaciones`` is the one field where the two IOL models
      disagree, asymmetrically (D-04): ``int`` here, ``float`` in ``Titulo``,
      each following its own capture. The ``int`` branch of the walker is
      **strict** — a decimal from the wire substitutes the typed zero and
      reports; the ``float`` branch widens an integer silently. A Phase 33
      divergence on this field is that asymmetry firing, not a model defect.
    - ``plazo`` and ``moneda`` stay free text. Promotion to a closed set is
      Phase 33 work with a live census behind it (D-09/DT-07); no RESPONSE
      field gains a closed type in this phase.
    """

    apertura: float
    cantidadOperaciones: int
    cierreAnterior: float
    descripcionTitulo: str | None
    fechaHora: str
    interesesAbiertos: float
    laminaMinima: int
    lote: int
    maximo: float
    minimo: float
    moneda: str
    montoOperado: float
    plazo: str | None
    precioAjuste: float
    precioPromedio: float
    puntas: list[Punta] | None
    tendencia: str
    ultimoPrecio: float
    variacion: float
    volumenNominal: float
