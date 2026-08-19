"""Safe-access frozen dataclasses for market-data API responses.

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
Chained access like ``snapshot.entries[0].price`` never raises — the worst
case is a final ``None`` or a zero-valued primitive.

Field names follow the wire format (camelCase) verbatim so JSON parsing can
stay declarative. They are PROVISIONAL: the OpenAPI is not vendored (A1/A2),
so shapes are reconciled against real payloads in Phase 23; ``from_api``
tolerance bounds the blast radius of a wrong guess. This module is exempt from
the ``N815`` naming rule (see ``[tool.ruff.lint.per-file-ignores]`` in the root
``pyproject.toml``).

``received_at`` is a first-class, CLIENT-STAMPED field on
:class:`MarketDataSnapshot` (D-01): it records when the client received the
response, NOT a payload value. :meth:`MarketDataSnapshot.from_api` injects it
directly as a keyword and never routes it through ``_coerce`` (which would
collapse it to ``0.0``). :class:`MarketDataSnapshot` is the ONLY client-stamped
model. :class:`Symbol` also declares a ``received_at``, but that one is a plain
WIRE field read off the payload like any other (the server's ingest timestamp for
the row) — same name, opposite provenance. No other :class:`SafeModel` subclass
carries a ``received_at`` at all.

This module is a package-local copy of the higyrus ``SafeModel`` / ``_coerce``
implementation (D-03): the no-shared-internals constraint forbids importing any
symbol from ``higyrus_client``.

Phase 29 (DEC-01): the per-field coercion now lives in
:mod:`market_data_client._decode`, the canonical walker shared in verbatim
copies across the paquetes. **The substitution behaviour above is unchanged** —
every default listed is still the default, and :meth:`SafeModel.from_api` still
takes exactly one positional argument and returns the same instance it always
did. What is new is *reporting*: each substitution now emits a structured
divergence record on the ``market_data_client`` logger, and an undeclared wire
key — which ``_coerce`` structurally could not see, since it never received the
payload's own key set — is reported too. The record names the field and the
types, **never** the value: market-data payloads carry symbol and account
identifiers (T-29-22).

Both model-level exemptions of ``29-SEMANTICS-MATRIX.md`` Section 3 survive the
delegation verbatim: :meth:`MarketDataSnapshot.from_api` keeps its extended
signature and its ``received_at`` injection bypass, and :meth:`Symbol.from_api`
keeps its wire-key mirror and its explicit two-argument ``super()``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

from market_data_client import _decode, _params

__all__ = [
    "CalendarConfig",
    "CalendarDay",
    "HolidayIn",
    "HolidaysIn",
    "Instrument",
    "LatestRequest",
    "MarketDataSnapshot",
    "MarketHoursIn",
    "NewSymbol",
    "NewSymbols",
    "SafeModel",
    "Segment",
    "Symbol",
    "SymbolPatch",
]


class SafeModel:
    """Base class for market-data API response models.

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


def _coerce(value: Any, hint: Any) -> Any:
    """Coerce ``value`` to match ``hint``, substituting safe defaults for ``None``.

    Back-compat shim over :func:`market_data_client._decode.walk_field`. Kept
    with its original two-positional-argument signature and identical return
    values so any existing caller keeps working; new code should reach for the
    walker.
    """
    return _decode.walk_field(
        value,
        hint,
        path="",
        model="",
        policy=_decode.POLICY,
        sink=_decode.DecodeScope(),
    )


@dataclass(frozen=True, slots=True)
class MarketDataSnapshot(SafeModel):
    """A market-data snapshot returned by the ``/marketdata`` read endpoints.

    Reconciled against the real develop wire (LIVE-MD-01): ``/marketdata`` items
    carry ``symbol``, ``market_id``, ``active``, ``entries`` (a list of entry-type
    code strings, e.g. ``["BI", "OF"]``), ``market_data`` (a dict passthrough of
    per-entry-type rows), ``staleness_seconds``, and — on ``/marketdata/latest``
    no-data rows — a ``note`` string. ``received_at`` is a first-class,
    CLIENT-STAMPED field (D-01): it is injected by :meth:`from_api` as a keyword
    and never coerced from the payload (a wire/decoy ``received_at`` never wins).
    """

    symbol: str
    market_id: str
    active: bool
    entries: list[str]
    market_data: dict[str, Any]
    staleness_seconds: float
    received_at: float
    note: str | None = None

    @classmethod
    def from_api(cls, payload: Any, *, received_at: float = 0.0) -> Self:
        """Build a snapshot, injecting the client-supplied ``received_at`` stamp.

        Every field except ``received_at`` is deserialized tolerantly through
        the walker (:mod:`market_data_client._decode`). ``received_at`` is set
        DIRECTLY from the keyword argument, bypassing the walker (which would
        otherwise collapse it to ``0.0`` when the payload omits the key) — this
        is the D-01 fidelity contract, restated as ``29-SEMANTICS-MATRIX.md``
        Section 3(a): a payload ``"received_at"`` key is IGNORED and the
        injected stamp always wins.

        Phase 29 mechanics, two steps and both load-bearing:

        1. The stamp is written over the payload's own ``received_at`` BEFORE
           the walk, the same pre-processing-hook shape :meth:`Symbol.from_api`
           uses for its mirror. The walker therefore never sees a wire value at
           that key, so it emits NO divergence for it in any case — absent,
           conflicting or wrong-typed — and strict mode can never make a
           client-stamped field fatal. Because ``received_at`` is a DECLARED
           field, writing it also cannot produce an ``extra`` record.
        2. The walker's output for that key is then DISCARDED and replaced with
           the keyword verbatim, so the final value is the caller's ``float``
           exactly as passed — never a coerced or policy-substituted one. This
           is the step that makes "a wire-supplied ``received_at`` can never win
           over the client stamp" true by construction rather than by argument.

        The exemption is CLASS-keyed, not field-name-keyed: :class:`Symbol` also
        declares a ``received_at``, but that one is a genuine wire field (the
        server's ingest timestamp) and is read straight off the payload.
        """
        stamped: Any = {**payload, "received_at": received_at} if isinstance(payload, dict) else payload  # fmt: skip
        kwargs = _decode.walk_model(
            cls, stamped, policy=_decode.POLICY, sink=_decode.current_sink()
        )
        kwargs["received_at"] = received_at  # INJECT — skip the walker (D-01)
        return cls(**kwargs)


@dataclass(frozen=True, slots=True)
class LatestRequest:
    """Typed request body for the batch ``POST /marketdata/latest`` endpoint (D-05).

    NOT a :class:`SafeModel` — this dataclass serializes OUT via :meth:`to_dict`.
    PROVISIONAL field names (A1/A2 — Phase 23 reconciles). :meth:`to_dict` drops
    ``None``-valued optionals so the wire body stays minimal and Phase 23 can
    adjust field names in one place.
    """

    symbols: list[str]
    marketId: str | None = None
    entries: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a wire dict, dropping ``None``-valued optional fields."""
        out: dict[str, Any] = {"symbols": self.symbols}
        if self.marketId is not None:
            out["marketId"] = self.marketId
        if self.entries is not None:
            out["entries"] = self.entries
        return out


# ----------------------------------------------------------------------
# Symbols write request models (D-09 / D-10 / D-11) — serialize-OUT
# ----------------------------------------------------------------------
#
# These three request models feed the ``POST /symbols``, ``POST /symbols/batch``
# and ``PATCH /symbols/{id}`` write endpoints (MUT-MD-01). Like
# :class:`LatestRequest`, they are NOT :class:`SafeModel` subclasses — they
# serialize OUT via a hand-written :meth:`to_dict`, they do not deserialize IN.


@dataclass(frozen=True, slots=True)
class NewSymbol:
    """Typed request body element for a symbol create (D-09 / D-10).

    NOT a :class:`SafeModel` — this dataclass serializes OUT via :meth:`to_dict`.
    ``market_id`` is defaulted, non-nullable, and ALWAYS emitted (D-10). The wire
    key is snake_case ``market_id`` per the source-plan schema — INTENTIONALLY
    different from :class:`LatestRequest`'s camelCase ``marketId`` (Pitfall 3 /
    A2; the real key is confirmed live in Phase 27).
    """

    symbol: str
    market_id: str = "ROFX"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a wire dict — both keys always present (D-10)."""
        return {"symbol": self.symbol, "market_id": self.market_id}


@dataclass(frozen=True, slots=True)
class NewSymbols:
    """Typed request body for the batch ``POST /symbols/batch`` endpoint (D-09).

    NOT a :class:`SafeModel` — serializes OUT via :meth:`to_dict`. Enforces the
    client-side 1-500 batch-size guard in :meth:`__post_init__`, raising a plain
    :class:`ValueError` (NOT a ``MarketData*`` error — that hierarchy is reserved
    for server contract errors, D-11) before any spec build or HTTP dispatch. The
    ``ValueError``-only ``__post_init__`` reads but never mutates fields, so it is
    valid on a frozen dataclass without ``object.__setattr__``.
    """

    symbols: list[NewSymbol]

    def __post_init__(self) -> None:
        """Enforce the 1-500 batch-size bound (D-11) — plain ValueError."""
        if not 1 <= len(self.symbols) <= 500:
            raise ValueError(f"NewSymbols requires 1-500 symbols, got {len(self.symbols)}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to ``{"symbols": [each element's to_dict()]}``."""
        return {"symbols": [s.to_dict() for s in self.symbols]}


@dataclass(frozen=True, slots=True)
class SymbolPatch:
    """Typed request body for the ``PATCH /symbols/{id}`` endpoint (D-09).

    NOT a :class:`SafeModel` — serializes OUT via :meth:`to_dict`. Carries the
    single ``active`` toggle the update endpoint accepts.
    """

    active: bool

    def to_dict(self) -> dict[str, Any]:
        """Serialize to ``{"active": self.active}``."""
        return {"active": self.active}


# ----------------------------------------------------------------------
# Calendar write request models (D-08 .. D-13) — serialize-OUT
# ----------------------------------------------------------------------
#
# These three request models feed the ``PUT /calendar/config``,
# ``POST /calendar/config/preview`` and ``POST /calendar/holidays`` write
# endpoints (MUT-MD-02). Like the symbols write models above they are NOT
# :class:`SafeModel` subclasses (D-08) — they serialize OUT via a hand-written
# :meth:`to_dict`, they never deserialize IN. Field names, defaults and bounds
# are verbatim from the live OpenAPI (re-fetched 2026-07-31); the scalar bounds
# it declares are deliberately NOT enforced client-side (D-13) — they surface as
# the server's ``422``.


@dataclass(frozen=True, slots=True)
class MarketHoursIn:
    """Typed request body for the calendar-config write endpoints (D-08 / D-09).

    NOT a :class:`SafeModel` — this dataclass serializes OUT via :meth:`to_dict`.
    Field order, wire keys and defaults are verbatim from the live OpenAPI
    (D-10): ``open_time`` / ``close_time`` / ``timezone`` are required, the rest
    default to ``pre_open_minutes=10``, ``enabled=True``, ``updated_by=""`` and
    ``confirm=False``.

    ``confirm`` is a FIELD of this model, not a loose method kwarg (D-09): it is
    the exact analogue of :attr:`NewSymbol.market_id` — defaulted, non-nullable
    and ALWAYS emitted. It is the "second opinion" guardrail the server demands
    when a legal-but-suspicious window produces warnings (see
    ``POST /calendar/config/preview``), so the consumer has to write
    ``confirm=True`` on purpose to overwrite a warned-about config.

    The scalar bounds the OpenAPI declares (``pre_open_minutes`` 0-120,
    ``timezone`` 1-64 chars, ``updated_by`` <= 200 chars, and the ``format: time``
    shape of the hour strings) are NOT validated client-side (D-13): a client-side
    regex would produce false negatives because ``format: time`` also admits
    ``"10:00:00"``. Out-of-range values ride to the server's ``422``.
    """

    open_time: str
    close_time: str
    timezone: str
    pre_open_minutes: int = 10
    enabled: bool = True
    updated_by: str = ""
    confirm: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a wire dict — all 7 keys always present (D-10).

        Routed through ``_params.drop_none`` for consistency with
        :meth:`HolidayIn.to_dict` (D-11); here it is a no-op because no field is
        nullable, so every key — including ``confirm: False`` — always travels.
        """
        return _params.drop_none(
            {
                "open_time": self.open_time,
                "close_time": self.close_time,
                "timezone": self.timezone,
                "pre_open_minutes": self.pre_open_minutes,
                "enabled": self.enabled,
                "updated_by": self.updated_by,
                "confirm": self.confirm,
            }
        )


@dataclass(frozen=True, slots=True)
class HolidayIn:
    """Typed request body element for a holiday create (D-08 / D-10 / D-11).

    NOT a :class:`SafeModel` — this dataclass serializes OUT via :meth:`to_dict`.
    ``day`` is the required ISO ``YYYY-MM-DD`` date; ``closed`` defaults to
    ``True`` (``False`` = open with custom hours) and ``description`` to ``""``,
    both verbatim from the live OpenAPI (D-10).

    This is the FIRST request model of the package with nullable fields, so
    ``_params.drop_none`` is load-bearing here (D-11): ``open_time`` /
    ``close_time`` DISAPPEAR from the wire when they are ``None`` (the OpenAPI
    documents ``null`` as "configured default", and the field default is ``None``
    too, so dropping the key is semantically equivalent — assumption A3,
    revalidated live in Phase 27), while the falsy-but-not-``None`` ``closed`` and
    ``description=""`` are still emitted.

    As with :class:`MarketHoursIn`, the declared scalar bounds (``description``
    <= 500 chars, the ``format: date`` / ``format: time`` shapes) are NOT checked
    client-side (D-13) — they surface as the server's ``422``.
    """

    day: str
    closed: bool = True
    open_time: str | None = None
    close_time: str | None = None
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a wire dict, dropping the ``None``-valued hour pair (D-11)."""
        return _params.drop_none(
            {
                "day": self.day,
                "closed": self.closed,
                "open_time": self.open_time,
                "close_time": self.close_time,
                "description": self.description,
            }
        )


@dataclass(frozen=True, slots=True)
class HolidaysIn:
    """Typed request body for the batch ``POST /calendar/holidays`` endpoint (D-08).

    NOT a :class:`SafeModel` — serializes OUT via :meth:`to_dict`. Enforces the
    client-side 1-500 batch-size bound the live OpenAPI declares
    (``days: {minItems: 1, maxItems: 500}``) in :meth:`__post_init__`, raising a
    plain :class:`ValueError` (NOT a ``MarketData*`` error — that hierarchy is
    reserved for server contract errors, D-12) before any spec build or HTTP
    dispatch. The ``ValueError``-only ``__post_init__`` reads but never mutates
    fields, so it is valid on a frozen dataclass without ``object.__setattr__``.
    """

    days: list[HolidayIn]

    def __post_init__(self) -> None:
        """Enforce the 1-500 batch-size bound (D-12) — plain ValueError."""
        if not 1 <= len(self.days) <= 500:
            raise ValueError(f"HolidaysIn requires 1-500 days, got {len(self.days)}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to ``{"days": [each element's to_dict()]}`` — pure wrapper (D-11)."""
        return {"days": [d.to_dict() for d in self.days]}


# ----------------------------------------------------------------------
# Reference-data models (D-04 / D-05) — plain SafeModel, no received_at
# ----------------------------------------------------------------------
#
# These five catalog models follow the ``SafeModel`` base precedent: they are
# built via the INHERITED ``SafeModel.from_api`` (no override) and carry NO
# client-stamped ``received_at`` (D-05) — reference data is slow-moving with no
# ``max_staleness_seconds`` companion to justify a receipt-time stamp. Shapes
# are PROVISIONAL (A1/A2 — OpenAPI not vendored); Phase 23 reconciles field
# names/types against real develop payloads, and ``from_api`` tolerance bounds
# the blast radius of a wrong guess.


@dataclass(frozen=True, slots=True)
class Instrument(SafeModel):
    """An instrument row from ``GET /instruments``.

    PROVISIONAL shape (A1/A2 — OpenAPI not vendored; Phase 23 reconciles). A
    plain :class:`SafeModel` subclass built via the inherited ``from_api``: it
    carries NO ``received_at`` (D-05 — reference data is unstamped).
    """

    symbol: str
    marketId: str
    segment: str
    instrumentType: str
    expired: bool


@dataclass(frozen=True, slots=True)
class Segment(SafeModel):
    """A market segment row from ``GET /instruments/segments``.

    PROVISIONAL shape (A1/A2 — OpenAPI not vendored; Phase 23 reconciles). A
    plain :class:`SafeModel` subclass built via the inherited ``from_api``: it
    carries NO ``received_at`` (D-05 — reference data is unstamped).
    """

    marketSegmentId: str
    marketId: str
    description: str


@dataclass(frozen=True, slots=True)
class Symbol(SafeModel):
    """A symbol row from ``GET /symbols`` — and from the three symbols mutations.

    Reconciled against the FIRST POPULATED symbol row ever observed (LIVE-MUT-01,
    armed destructive run 2026-08-01, baselines
    ``.planning/verification/schemas/market-data-client/get-symbols-probe-prefix-{sync,async}.json``).
    Until that run the develop catalogue was empty and the committed baseline was a
    bare ``[]``, so every field below the first three was unknowable — the live
    OpenAPI declares the row as a bare ``object`` with ``additionalProperties: true``
    and types nothing. The shape is therefore MEASURED, not inferred from the spec
    (D-10 forbids retyping on the spec's authority alone).

    Wire fields, verbatim: ``symbol``, ``market_id``, ``active``, ``id``,
    ``created_at``, ``updated_at``, ``received_at``.

    ``id`` is the DATABASE ROW ID and the value
    ``PATCH /symbols/{symbol_id}`` expects — the live spec types that path
    parameter as an integer and the wire agrees. It also rides the ``POST /symbols``
    response body, so a create/patch cycle never has to re-read the catalogue.

    ``received_at`` here is a WIRE field (``null`` on every row observed so far):
    the SERVER's ingest timestamp for the symbol. It is NOT the client stamp of
    :class:`MarketDataSnapshot` — this model is unstamped like every other
    reference model (D-05), and the inherited ``from_api`` reads this key straight
    off the payload.

    ``marketId`` is a DEPRECATED CAMEL-CASE ALIAS of :attr:`market_id`. The wire
    uses snake_case throughout this API; the 27-06 SHAPE-diff surfaced ``marketId``
    as model-only and ``market_id`` as wire-only in the same diff, so the camelCase
    spelling was simply wrong. It is NOT renamed, because ``Symbol`` is published
    read surface since v0.2.0 and a rename would break consumers (D-22). Instead
    the wire-correct field is added alongside and :meth:`from_api` mirrors
    ``market_id`` into ``marketId``, so the alias — which used to be permanently
    ``""`` against a real payload — now carries the real value. New code should
    read :attr:`market_id`; the alias is scheduled for removal at the next MAJOR.
    """

    symbol: str
    marketId: str
    active: bool
    id: int = 0
    market_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    received_at: str | None = None

    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Build a ``Symbol``, mirroring the wire ``market_id`` into ``marketId``.

        The only :class:`SafeModel` subclass that pre-processes its payload. The
        wire never sends ``marketId``; without this the deprecated alias would stay
        ``""`` forever and silently contradict :attr:`market_id`. An explicit
        ``marketId`` in the payload (a hand-built dict, an older fixture) still
        wins — the mirror only FILLS an absent key, it never overwrites.

        Phase 29 (``29-SEMANTICS-MATRIX.md`` Section 3(b)): the mirror runs
        BEFORE the walker sees the payload, which is what keeps extra-key
        reporting correct. After the mirror ``marketId`` is a declared field
        with a present key, so no ``extra`` record fires for it — right, because
        the client synthesized that key, the vendor did not send it.
        """
        if isinstance(payload, dict) and "marketId" not in payload and "market_id" in payload:
            payload = {**payload, "marketId": payload["market_id"]}
        # Explicit two-arg ``super()``: ``@dataclass(slots=True)`` REBUILDS the
        # class, so the implicit ``__class__`` cell captured by a zero-arg
        # ``super()`` still points at the pre-slots class and raises
        # ``TypeError: obj must be an instance or subtype of type``. The module
        # global ``Symbol`` is rebound to the slots class, so naming it works.
        return super(Symbol, cls).from_api(payload)


@dataclass(frozen=True, slots=True)
class CalendarDay(SafeModel):
    """One entry of the ``days[]`` list inside the ``GET /calendar`` envelope (D-12).

    Reconciled against the real develop wire (LIVE-MUT-01): the committed baseline
    ``.planning/verification/schemas/market-data-client/get-calendar.json`` shows the
    response is the object envelope ``{config, coverage, days[], market}`` whose
    ``days[]`` items are ``{day, closed, open_time, close_time, description}`` — i.e.
    the :class:`HolidayIn` request shape echoed back. ``day`` is the ISO
    ``YYYY-MM-DD`` date; ``closed`` flags a non-trading day; ``open_time`` /
    ``close_time`` are ``str | None`` because the wire sends ``null`` for a fully
    closed day and custom ``HH:MM`` session hours otherwise.

    The previously declared ``date`` / ``marketId`` / ``isBusinessDay`` fields exist
    NOWHERE on the wire — they were the PROVISIONAL A1/A2 guess. Retyping them is
    treated as a minor, NON-breaking change (D-13): ``parse_calendar_response``
    iterated the envelope's keys instead of ``days[]``, so no released consumer could
    ever have read a populated instance.

    A plain :class:`SafeModel` subclass built via the inherited ``from_api``: it
    carries NO ``received_at`` (D-05 — reference data is unstamped).
    """

    day: str
    closed: bool
    description: str
    open_time: str | None = None
    close_time: str | None = None


@dataclass(frozen=True, slots=True)
class CalendarConfig(SafeModel):
    """The single calendar configuration object from ``GET /calendar/config`` (D-07).

    Reconciled against the real develop wire (LIVE-MD-01): ``open``/``close`` trading
    times (str); ``enabled``/``editable``/``env_bypass`` flags (bool);
    ``pre_open_minutes`` (int); ``source``/``timezone``/``updated_by`` (str);
    ``warnings`` (list, wire sends ``[]``); ``updated_at`` (str | None, wire sends
    ``null``). The ONE non-collection reference model (D-07): an empty/None body
    collapses to ``CalendarConfig.from_api(None)`` (tolerant default), never a raise.
    A plain :class:`SafeModel` subclass built via the inherited ``from_api``: it
    carries NO ``received_at`` (D-05 — reference data is unstamped).
    """

    open: str
    close: str
    enabled: bool
    editable: bool
    env_bypass: bool
    pre_open_minutes: int
    source: str
    timezone: str
    updated_by: str
    warnings: list[Any]
    updated_at: str | None = None
