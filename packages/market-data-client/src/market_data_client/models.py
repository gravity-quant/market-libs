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

Phase 29 code review (CR-03): the **mapping axis** lives here too, as
:func:`_mapping_value` / :func:`_apply_mapping_policy` — a verbatim copy of
matriz's pair. The canonical walker has no ``dict`` branch by design (it must stay
byte-identical across five paquetes), so a ``dict``-declared field needs a
call-site pass to be decoded at all. :attr:`MarketDataSnapshot.market_data` is
such a field and had no pass, so an absent or wrong-typed ``market_data``
substituted ``None`` silently: no divergence record, no strict raise, and a value
contradicting its own ``dict[str, Any]`` annotation. It now falls back to ``{}``
and reports, exactly as every other declared field falls back to its typed zero.

Phase 31 (TYP-02, D-02): :meth:`SafeModel.to_dict` is added to the base — a
per-package VERBATIM COPY of ``iol_client.models.SafeModel.to_dict``, never an
import (C-2 forbids cross-package imports and there is no shared internal
package by design). **CR-01 caveat, load-bearing:** its docstring calls it "the
adapter the verification harness feeds to ``verification.schema.schema_of``",
which is the iol wording and is now known to be WRONG for a snapshot site. Phase
30's own CR-01 finding is that ``schema_of`` over a model projection is a
function of the DECLARATION, not of the wire — the walker has already coerced
every non-optional field to its declared type and dropped every undeclared key,
so a ``float -> str``, an added key and a removed key are all three invisible.
``to_dict()`` is therefore the escape hatch for ``len()`` / ``isinstance``
call sites ONLY; every driver schema-snapshot site must keep feeding RAW WIRE
(see ``main_market_data.py``'s ``_raw_via_request_sync`` / ``_raw_via_request_async``).
"""

from __future__ import annotations

import dataclasses
import types
from dataclasses import dataclass, fields
from typing import Any, Self, Union, cast, get_args, get_origin

from market_data_client import _decode, _params

__all__ = [
    "AddHolidaysResult",
    "CalendarConfig",
    "CalendarConfigPreview",
    "CalendarDay",
    "DeleteHolidayResult",
    "FeedIngestor",
    "FeedMarket",
    "FeedPipeline",
    "Health",
    "HealthAuth",
    "HealthFeed",
    "HolidayIn",
    "HolidaysIn",
    "Instrument",
    "LatestRequest",
    "MarketDataSnapshot",
    "MarketHoursIn",
    "NewSymbol",
    "NewSymbols",
    "PreviewMarket",
    "SafeModel",
    "Segment",
    "Symbol",
    "SymbolPatch",
]


def _strip_optional(tp: Any) -> Any:
    """Return ``T`` from ``T | None`` / ``Optional[T]``; pass through otherwise."""
    if get_origin(tp) in (Union, types.UnionType):
        args = [a for a in get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp


def _is_mapping(tp: Any) -> bool:
    """True for a ``dict[...]``-declared field, ``Optional`` unwrapped first."""
    return get_origin(_strip_optional(tp)) is dict


def _mapping_value(value: Any, *, path: str, model: str, sink: _decode.DecodeScope) -> Any:
    """market-data's mapping axis: a non-mapping wire value falls back to ``{}``.

    Phase 29 code review, CR-03. The canonical walker has **no** ``dict`` branch —
    that is sanctioned (``29-SEMANTICS-MATRIX.md`` Section 2 records the mapping
    axis as a call-site concern, so ``_decode.py`` can stay byte-verbatim across
    the five paquetes) — but the compensating call-site pass was only ever built
    for matriz. market-data declares a mapping field too
    (:attr:`MarketDataSnapshot.market_data`), so without this pass ``walk_field``
    fell through every arm to its bare ``return value`` and handed back whatever
    the payload had: ``None`` when the key is absent. That produced **no**
    divergence record in observable mode, **no** raise in strict mode, and an
    instance holding ``None`` where ``dict[str, Any]`` is annotated — the exact
    class of silent substitution DEC-01 exists to surface.

    Reporting matches what the walker emits for any other substituted default —
    ``missing`` when the payload carried nothing, ``type`` otherwise — so lock 2's
    kind, lock 3's WARNING level and lock 4's strict disposition all apply here
    exactly as they do on every other axis. This is a verbatim port of matriz's
    ``_mapping_value``; keeping the two identical is deliberate.
    """
    if isinstance(value, dict):
        return value
    sink(model, path, "missing" if value is None else "type", "dict", type(value).__name__)
    return {}


def _apply_mapping_policy(
    cls: type[Any], kwargs: dict[str, Any], *, sink: _decode.DecodeScope
) -> None:
    """Apply :func:`_mapping_value` to every mapping-declared field of ``cls``.

    Runs after :func:`market_data_client._decode.walk_model` and mutates its
    kwargs in place. It reaches TOP-LEVEL fields only: ``walk_field`` recurses
    into a nested model through ``walk_model`` directly, so a mapping field on a
    model reached as another model's field type would be missed. No shipped
    market-data model that declares a mapping field is ever another model's field
    type — ``test_no_mapping_carrying_model_is_ever_a_nested_field_type`` pins
    that precondition, and fails loudly if a future plan nests one.

    **``None`` under an OPTIONAL mapping hint is left alone (Phase 33, SC-2).**
    :func:`_is_mapping` unwraps ``Optional`` before testing the origin — it has
    to, or a ``dict[...] | None`` field would skip the pass entirely and go back
    to holding whatever the payload had. But that unwrap made the pass blind to
    the very distinction the annotation encodes, so once
    :attr:`MarketDataSnapshot.market_data` widened to ``dict[str, Any] | None``
    the pass kept substituting ``{}`` and kept emitting a ``missing`` record for
    a ``null`` the vendor sends legitimately — silently undoing the widening one
    line after the walker honoured it. The guard restores the walker's own
    contract at this call site: under ``T | None`` a ``None`` "stays ``None``
    instead of collapsing to a typed zero, and is NOT a divergence"
    (``_decode.walk_field``). A NON-optional mapping field is untouched by the
    guard, so an absent ``market_data`` on a model that declares it required is
    still reported exactly as before (CR-03), and a WRONG-TYPED value under
    either annotation still routes through :func:`_mapping_value` and is still
    reported. The guard admits ``None`` under an explicit ``| None`` and nothing
    else.
    """
    # ``cast(Any, cls)`` is the walker's own mypy-strict discipline for
    # ``get_type_hints``-driven code. No ``type: ignore`` is introduced.
    target = cast(Any, cls)
    hints = _decode.hints_for(target)
    model = cls.__name__
    for f in fields(target):
        hint = hints[f.name]
        if not _is_mapping(hint):
            continue
        if kwargs[f.name] is None and _strip_optional(hint) is not hint:
            continue
        kwargs[f.name] = _mapping_value(kwargs[f.name], path=f".{f.name}", model=model, sink=sink)


class SafeModel:
    """Base class for market-data API response models.

    Subclasses must be frozen dataclasses. Construct instances via
    :meth:`from_api` to tolerate partial or missing fields.
    """

    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Build an instance from an API payload, with safe defaults."""
        sink = _decode.current_sink()
        kwargs = _decode.walk_model(cls, payload, policy=_decode.POLICY, sink=sink)
        # Lock 8: under a non-dict payload the walker already swapped its field
        # sink to ``SILENT_SINK``, so the mapping pass must be silent too —
        # otherwise a 204 body would emit one extra record per mapping field on
        # top of the terminal ``non_dict`` one.
        _apply_mapping_policy(
            cls, kwargs, sink=sink if isinstance(payload, dict) else _decode.SILENT_SINK
        )
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Re-project the model as the plain wire dict (D-08).

        Escape hatch for the dict -> model break of Phase 30: use it for
        ``len()`` / ``isinstance`` call sites ONLY. It is **NOT** a valid input
        to ``verification.schema.schema_of`` (WR-04). The walker has already
        coerced every non-optional field to its declared type and dropped every
        undeclared key, so a type change, an added key and a removed key are all
        three invisible in this projection (Phase 30 CR-01) — every driver
        schema-snapshot site must keep feeding RAW WIRE, as the module docstring
        above spells out. Nested models are flattened to dicts; ``None`` keys are
        **kept** — a response model must reproduce the declared shape, holes
        included.

        ``cast(Any, self)`` follows ``_decode.py``'s existing mypy-strict
        discipline: :class:`SafeModel` itself is not a dataclass — every
        concrete subclass is — so ``asdict``'s ``DataclassInstance`` overload
        cannot be satisfied by the base's ``self``.
        """
        wire: dict[str, Any] = dataclasses.asdict(cast(Any, self))
        return wire


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

    **BREAKING since 0.5.0 (Phase 33, SC-2).** :attr:`entries`,
    :attr:`market_data` and :attr:`staleness_seconds` were declared
    non-``Optional`` and are now ``| None``. ``GET /marketdata/latest`` answers
    for a symbol the feed has never delivered with a row carrying ``symbol`` +
    ``note`` and ``null`` everywhere else (committed baseline
    ``.planning/verification/schemas/market-data-client/get-latest.json``), so the
    three fields were simply over-declared. The 33-05 live run measured all three
    as ``missing`` divergences on both surfaces (``F-72``/``F-73``/``F-75`` and
    ``F-92``/``F-93``/``F-95``), and the strict pass raised on two of them.

    The widening — not a parser-side substitution — is the honest fix, and the
    operator selected it at the 33-07 Task 1 checkpoint (``fix-shape-now``).
    Manufacturing ``0.0`` / ``[]`` / ``{}`` for a value the vendor legitimately
    sends as ``null`` would have re-introduced the silent typed zero this
    milestone exists to remove. The widening admits ``None`` and nothing else: a
    wrong-TYPED value is still a divergence and still fatal under
    ``strict_decode``, pinned by
    ``tests/test_snapshot_no_data_row.py::test_a_wrong_typed_value_is_still_a_divergence``.

    All three keep their positional slot and stay REQUIRED constructor
    arguments — only the annotation widens, so no field order moves and no
    default masks an absent key.
    """

    symbol: str
    market_id: str
    active: bool
    entries: list[str] | None
    market_data: dict[str, Any] | None
    staleness_seconds: float | None
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
        sink = _decode.current_sink()
        kwargs = _decode.walk_model(cls, stamped, policy=_decode.POLICY, sink=sink)
        # CR-03: ``market_data`` is declared ``dict[str, Any]`` and the walker has
        # no ``dict`` branch, so without this pass an absent or wrong-typed
        # ``market_data`` was substituted silently — no record, no strict raise,
        # and a ``None`` held under a non-Optional annotation. Lock 8 again: the
        # pass is silent under a non-dict payload.
        _apply_mapping_policy(
            cls, kwargs, sink=sink if isinstance(stamped, dict) else _decode.SILENT_SINK
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


# ----------------------------------------------------------------------
# Calendar-config PREVIEW envelope (Phase 33, LIVE-TYP-01 / S-2) — plan 33-07
# ----------------------------------------------------------------------
#
# ``POST /calendar/config/preview`` does NOT return a configuration. It returns
# a compute-only verdict about a PROPOSED window, and the two shapes share not a
# single key. Until Phase 33 the endpoint was declared ``-> CalendarConfig`` and
# decoded through ``parse_calendar_config_response``, which manufactured an
# all-typed-zero config and DISCARDED all three real answers.
#
# ``29-SIZING.md`` predicted the exact divergence set as S-2 and the 33-05 live
# run returned it field for field: nine ``missing`` (``.close``, ``.editable``,
# ``.enabled``, ``.env_bypass``, ``.open``, ``.pre_open_minutes``, ``.source``,
# ``.timezone``, ``.updated_by``) and three ``extra`` (``.market_after``,
# ``.requires_confirmation``, ``.valid``) on EACH surface — findings ``F-121``..
# ``F-132`` and ``F-152``..``F-163``.
#
# Correcting it changes a PUBLISHED return type, so it went through the 33-07
# Task 1 blocking checkpoint and the operator selected ``fix-shape-now``. The
# consequence is recorded rather than absorbed: ``market-data-client`` becomes a
# SOURCE-BREAKING entry of Phase 34's bump set at 0.4.0 -> 0.5.0.
#
# Neither class declares a ``dict[...]`` field and neither overrides
# ``from_api``, so the walker's ``hint(**walk_model(...))`` nested-construction
# path is correct for ``PreviewMarket`` (the preconditions pinned by
# ``test_no_mapping_carrying_model_is_ever_a_nested_field_type`` and
# ``test_models_with_a_from_api_override_are_never_a_nested_field_type`` hold).
# Neither carries ``received_at``: a dry-run verdict is not a snapshot (D-05).


@dataclass(frozen=True, slots=True)
class PreviewMarket(SafeModel):
    """The ``market_after`` block of the preview verdict — the session the window would produce.

    Live-capture provenance: field set taken verbatim from
    ``.planning/verification/schemas/market-data-client/preview-calendar-config-sync-response.json``,
    captured 2026-08-01 against ``market-data-develop``; the ``-async-`` capture
    is byte-identical, and that identity is itself the sync/async parity
    evidence. NOT from the OpenAPI, which declares this ``200`` as a bare,
    schema-less ``object``.

    Deliberately NOT :class:`FeedMarket`, which it superficially resembles:
    ``FeedMarket`` additionally declares ``enabled`` and ``last_business_day``,
    and neither key exists on this envelope. Reusing it would have manufactured
    two permanent ``missing`` divergences per preview call — re-introducing, one
    level down, exactly the defect this model exists to remove.

    No field is declared ``| None``: both committed captures show every field
    populated, and an over-declared Optional would permanently hide that field
    from the divergence census (T-31-17, the 31-04 option-b logic applied here).
    """

    is_open: bool
    local_time: str
    next_transition: str
    reason: str
    session_close: str
    session_open: str
    state: str


@dataclass(frozen=True, slots=True)
class CalendarConfigPreview(SafeModel):
    """The ``POST /calendar/config/preview`` ``200`` envelope (Phase 33, S-2).

    The dry run's three answers, none of which :class:`CalendarConfig` could
    carry:

    * :attr:`valid` — would the proposed window be accepted at all;
    * :attr:`requires_confirmation` — does it produce warnings, so the real
      ``PUT`` needs ``confirm=True`` as its second opinion;
    * :attr:`market_after` — the session state the window would produce.

    :attr:`warnings` is the list to read before deciding. It is the one key whose
    NAME the old ``CalendarConfig`` also declared, which is precisely why the
    defect was survivable in practice and invisible in review: the single
    attribute a caller actually reached for happened to line up.

    The intended flow is unchanged — ``preview_calendar_config(...)`` → inspect
    ``warnings`` → re-issue ``set_calendar_config(...)`` with ``confirm=True`` —
    but the verdict now arrives typed instead of being reconstructed from a
    field that survived by coincidence.
    """

    market_after: PreviewMarket
    requires_confirmation: bool
    valid: bool
    warnings: list[Any]


# ----------------------------------------------------------------------
# Calendar-WRITE mutation results (Phase 31, TYP-02 / D-01) — plan 31-05
# ----------------------------------------------------------------------
#
# ``POST /calendar/holidays`` and ``DELETE /calendar/holidays/{day}`` are the
# only two endpoints typed in this milestone that were ALREADY PUBLISHED as
# mutations (v0.4.0). The change is therefore RESPONSE-ONLY and that claim is
# mechanical, not asserted: ``tests/test_v040_request_pin.py`` pins the emitted
# request of both, raw-bytes, on both surfaces, and
# ``tests/test_mutation_gate_ast.py`` pins ``_ensure_mutation_allowed()`` as the
# first executable statement of every gated method plus ``idempotent is True``
# on both holiday builders.
#
# Declared AFTER :class:`CalendarDay` so :attr:`AddHolidaysResult.days` resolves.
# Neither carries ``received_at``: a mutation ACKNOWLEDGEMENT is not a snapshot
# and has no staleness dimension. Neither declares a ``dict[...]`` field and
# neither overrides ``from_api`` — a shape carve-out belongs in the parser, and
# on a nested model an override is silently skipped anyway because the walker
# builds nested models with ``hint(**walk_model(...))``. No field of either is
# declared ``| None``: all four committed captures show every field populated,
# and an over-declared Optional would permanently hide that field from the
# divergence census (T-31-17, the 31-04 option-b logic applied here).


@dataclass(frozen=True, slots=True)
class AddHolidaysResult(SafeModel):
    """The ``POST /calendar/holidays`` ``200`` envelope (Phase 31 TYP-02, D-01).

    Live-capture provenance: field set taken verbatim from
    ``.planning/verification/schemas/market-data-client/add-holidays-sync-response.json``,
    captured 2026-08-01 against ``market-data-develop``. The ``-async-`` capture
    of the same endpoint is BYTE-IDENTICAL to it, and that identity is itself the
    sync/async surface-parity evidence. Not from the OpenAPI — which declares this
    ``200`` as a bare, schema-less ``object`` — and not from a mock. The
    pre-Phase-31 unit mock asserted ``{"created": 1}``; no such key exists on the
    wire.

    :attr:`days` REUSES the shipped :class:`CalendarDay` rather than declaring a
    parallel element model (D-01). The capture's ``days[]`` items match
    ``CalendarDay`` field for field — ``day``, ``closed``, ``description`` and
    both ``str | None`` hour fields, which the capture shows as ``null`` for a
    fully closed day. A parallel class would drift from ``CalendarDay`` on the
    next wire change and would add a second nested field type to police under the
    two committed structural decode tests, for no gain.

    :attr:`saved` is the server's upserted-row count and :attr:`note` its
    human-readable acknowledgement. This is a MUTATION response typed
    response-only: no request byte moves and the mutating gate is untouched.
    """

    days: list[CalendarDay]
    note: str
    saved: int


@dataclass(frozen=True, slots=True)
class DeleteHolidayResult(SafeModel):
    """The ``DELETE /calendar/holidays/{day}`` ``200`` envelope (Phase 31 TYP-02, D-01).

    Live-capture provenance: field set taken verbatim from
    ``.planning/verification/schemas/market-data-client/delete-holiday-sync-response.json``,
    captured 2026-08-01 against ``market-data-develop``. The ``-async-`` capture is
    BYTE-IDENTICAL. Not from the OpenAPI and not from a mock.

    :attr:`deleted` is declared ``bool`` because the capture says ``bool``. The
    pre-Phase-31 unit mock sent the INTEGER ``1`` and asserted a mapping equality
    against it; that mock contradicts the wire and was corrected on the test side
    rather than accommodated here by widening the declaration. The measured
    consequence, pinned by
    ``test_delete_holiday_result_integer_deleted_is_not_widened_and_is_reported``:
    an ``int`` arriving for this field is NOT widened — ``walk_field`` emits a
    ``type`` divergence (``declared=bool`` / ``observed=int``) and substitutes
    ``False``, because market-data's ``POLICY.scalar_passthrough`` is ``False``.

    :attr:`day` echoes the ISO ``YYYY-MM-DD`` path segment that was deleted. Like
    :class:`AddHolidaysResult` this is a MUTATION response typed response-only.
    """

    day: str
    deleted: bool


# ----------------------------------------------------------------------
# Health models (Phase 31, TYP-02 / D-01) — ``GET /health`` + ``GET /health/feed``
# ----------------------------------------------------------------------
#
# Declared in DEPENDENCY ORDER so every nested type exists before its parent.
# NONE of the six overrides ``from_api`` (the walker builds a nested model with
# ``hint(**walk_model(...))`` and never calls it, so an override on a nested
# model is silently skipped — it looks like a fix and is not one); NONE declares
# a ``dict[...]`` field (four of them ARE nested field types, and
# ``test_no_mapping_carrying_model_is_ever_a_nested_field_type`` forbids a
# mapping-carrying model from being one); and NONE carries a ``received_at`` —
# health is not a snapshot and has no staleness dimension.
#
# NULLABILITY VERDICT (plan 31-04 Task 1 checkpoint, **option-b / Restraint**):
# nothing is declared nullable unless it was CONTEXT-locked (D-01) or actually
# observed as ``null`` in the one live capture. Exactly TWO fields qualify —
# :attr:`FeedIngestor.last_error` and :attr:`FeedPipeline.last_write_error`.
# Rationale, recorded here because Phase 33 adjudicates against it: a wrong
# non-null guess surfaces LOUDLY in Phase 33's strict driver run (self-correcting,
# the designed outcome, directly comparable against the ratified
# ``market-data-client >= 50`` divergence floor), whereas an over-declared
# ``Optional`` would SILENTLY and permanently hide that field from the divergence
# census — ``_decode.walk_field``'s union-with-``None`` branch returns ``None``
# without emitting a divergence record (T-31-17).


@dataclass(frozen=True, slots=True)
class HealthAuth(SafeModel):
    """The ``auth`` sub-object of ``GET /health`` (Phase 31 TYP-02, D-01).

    Live-capture provenance: field set taken verbatim from
    ``.planning/verification/schemas/market-data-client/get-health.json``,
    captured 2026-07-31 against ``market-data-develop``. Not from the OpenAPI and
    not from a mock.

    No ``| None`` field: every one of the three came back populated and
    non-nullable in the capture (checkpoint verdict option-b).
    """

    configured: bool
    enabled: bool
    issuer: str


@dataclass(frozen=True, slots=True)
class Health(SafeModel):
    """The ``GET /health`` envelope (Phase 31 TYP-02, D-01).

    Live-capture provenance: field set taken verbatim from
    ``.planning/verification/schemas/market-data-client/get-health.json``,
    captured 2026-07-31 against ``market-data-develop``.

    No ``| None`` field. :attr:`auth` is declared as the non-optional nested
    :class:`HealthAuth`, so an absent ``auth`` key yields the ZERO-VALUED
    ``HealthAuth`` plus a ``missing`` divergence record — never ``None``, which
    would have been reported by nothing (checkpoint verdict option-b).
    """

    status: str
    auth: HealthAuth


@dataclass(frozen=True, slots=True)
class FeedMarket(SafeModel):
    """``ingestor.market`` inside ``GET /health/feed`` (Phase 31 TYP-02, D-01).

    Live-capture provenance: field set taken verbatim from
    ``.planning/verification/schemas/market-data-client/get-health-feed.json``,
    captured 2026-07-31 against ``market-data-develop``.

    No ``| None`` field — and this is the model the Task 1 checkpoint argued
    hardest about. :attr:`last_business_day`, :attr:`next_transition`,
    :attr:`session_open`, :attr:`session_close` and :attr:`reason` are the
    "market-session group": a CLOSED or DISABLED market plausibly has no session
    times, so option-a would have declared all five ``str | None``. The verdict
    was **option-b**: the single capture observed all five as populated strings
    with ``enabled: true``, so declaring them nullable would be inference rather
    than evidence, and would make each field's future ``null`` permanently
    invisible to the divergence census. If one of them IS nullable, Phase 33's
    strict run raises on it — loud, in-cycle, and corrected there.

    :attr:`reason` also exists on :class:`FeedIngestor`. They are independent
    fields on independent models; only this one is in the market-session group.
    """

    enabled: bool
    is_open: bool
    state: str
    local_time: str
    last_business_day: str
    next_transition: str
    session_open: str
    session_close: str
    reason: str


@dataclass(frozen=True, slots=True)
class FeedPipeline(SafeModel):
    """``ingestor.pipeline`` inside ``GET /health/feed`` (Phase 31 TYP-02, D-01).

    Live-capture provenance: field set taken verbatim from
    ``.planning/verification/schemas/market-data-client/get-health-feed.json``,
    captured 2026-07-31 against ``market-data-develop``.

    ``| None`` justification — :attr:`last_write_error` is declared
    ``str | None`` because the live capture OBSERVED it as ``null`` and because
    CONTEXT D-01 locks it as nullable. Its non-``None`` member is typed ``str``
    on the OpenAPI's word alone: the capture shows a healthy pipeline, so a
    populated error value was never seen (RESEARCH assumption A1). That half is
    still an assumption and Phase 33's live evidence adjudicates it.

    :attr:`last_write_at` is deliberately NOT nullable (checkpoint verdict
    option-b): it came back a populated string, and an over-declared ``Optional``
    here would silently absorb a future ``null`` with no divergence record.
    """

    batch_interval_ms: int
    conserved: bool
    flushes: int
    frames_accepted: int
    frames_coalesced: int
    frames_unknown_symbol: int
    last_flush_ms: float
    pending: int
    pending_peak: int
    rows_skipped_stale: int
    last_write_at: str
    last_write_error: str | None = None


@dataclass(frozen=True, slots=True)
class FeedIngestor(SafeModel):
    """``ingestor`` inside ``GET /health/feed`` (Phase 31 TYP-02, D-01).

    Live-capture provenance: field set taken verbatim from
    ``.planning/verification/schemas/market-data-client/get-health-feed.json``,
    captured 2026-07-31 against ``market-data-develop``.

    ``| None`` justification — :attr:`last_error` is declared ``str | None``
    because the live capture OBSERVED it as ``null`` and because CONTEXT D-01
    locks it as nullable. As with :attr:`FeedPipeline.last_write_error`, the
    ``str`` half of the union is unobserved (RESEARCH assumption A1) and awaits
    Phase 33.

    :attr:`last_frame_at` and :attr:`started_at` are deliberately NOT nullable
    (checkpoint verdict option-b): both came back populated strings from a
    connected ingestor. A disconnected one plausibly has neither, which is
    precisely the guess Phase 33's strict run is expected to adjudicate — loudly,
    which is the designed outcome, rather than silently, which an ``Optional``
    would have made it.

    :attr:`market` and :attr:`pipeline` are non-optional nested models, so an
    absent key yields the zero-valued instance plus a ``missing`` record.
    """

    connected: bool
    present: bool
    state: str
    reason: str
    frames_total: int
    reconnects: int
    rows_written: int
    symbols_subscribed: int
    uptime_seconds: int
    heartbeat_age_seconds: float
    last_frame_age_seconds: float
    last_frame_at: str
    started_at: str
    market: FeedMarket
    pipeline: FeedPipeline
    last_error: str | None = None


@dataclass(frozen=True, slots=True)
class HealthFeed(SafeModel):
    """The ``GET /health/feed`` envelope, three nesting levels (Phase 31 TYP-02, D-01).

    Live-capture provenance: field set taken verbatim from
    ``.planning/verification/schemas/market-data-client/get-health-feed.json``,
    captured 2026-07-31 against ``market-data-develop``. Its shape is unrelated to
    :class:`Health`'s, which is why the two endpoints stopped sharing one parser
    (D-05).

    No ``| None`` field on this level. :attr:`newest_received_at` and
    :attr:`oldest_received_at` came back populated strings and are declared
    ``str`` per the checkpoint verdict — note they are WIRE timestamps of the
    newest/oldest stored row, NOT the client-stamped ``received_at`` of
    :class:`MarketDataSnapshot`; this model carries no client stamp at all.

    **SINGLE-STATE CAVEAT (RESEARCH A1/A2/A3 — read before trusting any
    declaration in this tree).** The one committed capture is a single
    observation of a CONNECTED ingestor with an OPEN market and a healthy
    pipeline. It therefore cannot distinguish "never ``null``" from "not ``null``
    right now". Under the Task 1 checkpoint verdict (**option-b / Restraint**)
    nine under-determined fields — :attr:`FeedIngestor.last_frame_at`,
    :attr:`FeedIngestor.started_at`, :attr:`FeedPipeline.last_write_at`,
    :attr:`FeedMarket.next_transition`, :attr:`FeedMarket.session_open`,
    :attr:`FeedMarket.session_close`, :attr:`FeedMarket.last_business_day`,
    :attr:`newest_received_at` and :attr:`oldest_received_at` — are declared
    non-nullable on evidence from that single state. Each is a DECLARED
    ASSUMPTION awaiting Phase 33's live strict run, which is the confirming
    evidence and the intended adjudicator.
    """

    status: str
    active_symbols: int
    symbols_with_data: int
    staleness_seconds: float
    newest_received_at: str
    oldest_received_at: str
    ingestor: FeedIngestor
