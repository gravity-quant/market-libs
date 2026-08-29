"""Safe-access models for the Primary API v1.21 client.

Each model is a frozen dataclass that exposes the wire payload through
attribute access with always-defined defaults: missing list keys become
``[]``, missing nested-model keys become an empty model instance, missing
scalars become ``None``, missing dicts become ``{}``. Chained access like
``snapshot.SE.price`` never raises ``KeyError`` or ``AttributeError`` —
the worst case is a final ``None`` for an absent scalar.

Construct an instance from a raw dict via ``Model.from_api(payload)``;
``Model.empty()`` builds a default instance with all attributes at their
safe defaults. Instances are frozen to discourage mutation of API
responses.

Phase 29 (DEC-01): the per-field coercion now runs inside
:mod:`matriz_client._decode`, which returns **exactly the same values** and
additionally reports every substituted default as a structured record on the
``matriz_client`` logger. Nothing a caller observes changes; what changes is
that the divergences this module used to swallow are now visible.

matriz's decode semantics are **not** the other paquetes' semantics, and that
is deliberate — every difference is a declared axis of
``29-SEMANTICS-MATRIX.md`` row 5, carried by :data:`matriz_client._decode.POLICY`
(``missing_* = None``, ``non_dict_model = "empty_classmethod"``,
``scalar_passthrough = True``), never a bug to be harmonized away. Two things
the policy constant cannot express live here instead:

- the **mapping axis** — a mapping-declared field falls back to ``{}``, and
  (Phase 37) its VALUES are decoded against the declared element type, with
  recursion for a nested mapping hint. The canonical walker has no ``dict``
  branch because higyrus and market-data declare no mapping fields, so both
  halves live here; see :func:`_apply_mapping_policy`.
- **UnknownFrame**, which is not a :class:`_SafeModel` at all and is exempt
  from extra-key reporting (matrix Section 3(c)).
"""

from __future__ import annotations

import collections.abc
import types
from dataclasses import dataclass, field, fields
from typing import Any, ClassVar, Self, Union, cast, get_args, get_origin

from matriz_client import _decode
from matriz_client.types import (
    CFICode,
    Currency,
    MarketId,
    OrderStatus,
    OrderType,
    SegmentId,
    Side,
    TimeInForce,
)

__all__ = [
    "AccountId",
    "AccountReport",
    "DetailedAccountReport",
    "DetailedPosition",
    "ExecutionReportFrame",
    "Instrument",
    "InstrumentDetail",
    "InstrumentId",
    "InstrumentPositionReport",
    "MarketDataEntryValue",
    "MarketDataFrame",
    "MarketDataLevel",
    "MarketDataSnapshot",
    "NewOrderResponse",
    "Order",
    "OrderReport",
    "Position",
    "PrimaryWsMessage",
    "Segment",
    "TickPriceRange",
    "Trade",
    "UnknownFrame",
]


# ----------------------------------------------------------------------
# Type-hint introspection helpers
# ----------------------------------------------------------------------


def _strip_optional(tp: Any) -> Any:
    """Return ``T`` from ``T | None`` / ``Optional[T]``; pass through otherwise."""
    if get_origin(tp) in (Union, types.UnionType):
        args = [a for a in get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp


def _is_model(tp: Any) -> bool:
    return isinstance(tp, type) and issubclass(tp, _SafeModel)


def _is_mapping_base(obj: Any) -> bool:
    """Whether ``obj`` is a class that IS a mapping — the axis's vocabulary.

    Expressed as a subclass test against :class:`collections.abc.Mapping` rather
    than as a hardcoded tuple, so it answers the same thing
    ``tools/check_surface_types.py``'s ``_MAPPING_BASES`` does *by construction*
    instead of by two lists happening to be kept in step. ``dict``,
    ``collections.abc.Mapping``/``MutableMapping``, ``defaultdict`` and
    ``OrderedDict`` all qualify;
    ``test_the_runtime_mapping_vocabulary_covers_the_gates`` pins the agreement.
    """
    return isinstance(obj, type) and issubclass(obj, collections.abc.Mapping)


def _is_mapping(tp: Any) -> bool:
    """True for a mapping-declared field, ``Optional`` unwrapped first.

    Three shapes answer True and are then handled IDENTICALLY by
    :func:`_apply_mapping_policy` and :func:`_mapping_value`: the parameterised
    ``dict[str, X]``, its blessed aliases (``Mapping[str, X]``,
    ``MutableMapping[str, X]``, ``defaultdict[str, X]``, ...), and the
    unparameterised base (bare ``dict``, bare ``Mapping``).

    Both widenings past bare ``dict[...]`` came from the Phase 37 code review:

    - **WR-01.** The axis tested ``get_origin(...) is dict`` and nothing else,
      while the surface gate blesses ``Mapping``/``MutableMapping`` *specifically*
      so "the ratchet cannot be bypassed by spelling the same untyped mapping as
      ``Mapping[str, Any]``". The disagreement was a TRAP, not a passive gap: an
      author whose ``Mapping[str, Any]`` field is reddened by the gate naturally
      "fixes" it to ``Mapping[str, Model]``, which turns the gate green and the
      runtime broken — ``get_origin`` answers ``collections.abc.Mapping``, the
      axis skipped the field, and the values reached the caller as RAW payload
      dicts under a model annotation. That is the exact type lie
      :func:`_mapping_value` exists to remove. Widening here rather than
      narrowing the gate: the gate's wider vocabulary is the correct one, and
      narrowing it would reopen the bypass it was written to close.
    - **WR-02.** ``get_origin(dict)`` is ``None``, so a field annotated with a
      bare ``dict`` was invisible to the axis — skipping the ``{}`` fallback, the
      element decode and the divergence report, passing garbage through verbatim
      and answering ``None`` for an absent key — in the spelling that states the
      LEAST.

    Neither widening changes the behaviour of any SHIPPED model: matriz declares
    four mapping fields and all four are parameterised ``dict[...]``, which is
    why the review filed them as warnings rather than blockers. What they change
    is the answer for the NEXT field, and ``Mapping[str, X]`` is one the surface
    gate actively steers an author toward.

    ``get_origin`` is consulted FIRST: on Python 3.12 ``isinstance(dict[str, X],
    type)`` is ``False``, but it was ``True`` on 3.9/3.10, and ordering the two
    checks this way makes the function's answer independent of that history.
    """
    stripped = _strip_optional(tp)
    origin = get_origin(stripped)
    if origin is not None:
        return _is_mapping_base(origin)
    return _is_mapping_base(stripped)


def _element_hint(tp: Any) -> Any:
    """The declared VALUE type of a mapping annotation; ``Any`` when unparameterised.

    ``Optional`` is stripped first via :func:`_strip_optional`, so
    ``dict[str, X] | None`` answers ``X`` exactly as the bare form does — the
    same normalization :func:`_is_mapping` already performs, reused rather than
    re-derived.

    A legacy ``dict[str, Any]`` and an unparameterised ``dict`` both answer
    ``Any``, which :func:`_decode.walk_field` lands on its bare pass-through:
    the value is returned verbatim. That is the correct behaviour for an untyped
    mapping and it is what keeps ``test_convert_shim_still_coerces`` green (F-17)
    without a special case that skips the walker.

    Phase 37 code review, WR-02: the unparameterised half of that sentence used
    to be a lie. ``_is_mapping(dict)`` answered ``False``, so
    ``_apply_mapping_policy`` never visited such a field and this function was
    never called for it — the docstring documented a code path that could not be
    reached. WR-02's widening of :func:`_is_mapping` is what makes the claim true
    rather than aspirational, which is why the two fixes had to land together.
    """
    args = get_args(_strip_optional(tp))
    return args[1] if len(args) == 2 else Any


def _mapping_value(
    value: Any,
    element: Any,
    *,
    path: str,
    model: str,
    sink: _decode.DecodeScope,
) -> Any:
    """matriz's mapping axis: decode a ``dict``-declared field, element type included.

    A non-mapping wire value falls back to ``{}``; a mapping is rebuilt with each
    value routed through :func:`_decode.walk_field` against ``element``.

    The canonical walker has **no** ``dict`` branch, so ``walk_field`` lands such
    a value on its bare pass-through and hands the raw dict back unchanged
    (``_decode.py:555`` is ``return value`` — 37-RESEARCH F-6 corrects the
    long-standing claim in this docstring that it returned ``None``). matriz
    declares four mapping fields (``InstrumentDetail.tickPriceRanges``,
    ``DetailedPosition.report``, ``AccountReport.detailedAccountReports`` /
    ``.portfolio``) whose documented contract is "missing dicts become ``{}``".

    The axis lives here rather than in ``_decode.py`` because that file is a
    byte-verbatim copy across five paquetes (D-02) and Plan 09 hashes it; a
    per-paquete branch there would be the first crack in that invariant. This
    mirrors the mechanism ``29-SEMANTICS-MATRIX.md`` Section 3 already blesses
    for market-data's two model-level exemptions: the call site normalizes, the
    walker stays untouched.

    Phase 29 code review, CR-03: the axis was **not** matriz-only. market-data
    declared a mapping field too (``MarketDataSnapshot.market_data``) and never
    received the compensating pass, so its flagship model carried a completely
    invisible divergence. ``market_data_client.models`` was given a verbatim copy
    of this function and of :func:`_apply_mapping_policy`, and the two had to
    stay identical.

    **That obligation ENDED with Phase 36 (NOBJ-MD-01, D-05).** market-data's
    ``market_data`` is no longer a mapping: it is the typed Null Object
    ``MarketDataEntries``, so the walker's own nested-model branch owns it and the
    compensating pass had nothing left to compensate for. Both helpers were
    DELETED from ``market_data_client.models`` in that phase — there is no second
    copy to keep in sync any more, and this axis is matriz-only again. Do not
    re-create a copy over there to restore the symmetry: per-paquete ``from_api``
    differences are declared policy axes (``29-SEMANTICS-MATRIX.md``, "never
    harmonize"), and market-data is form A of D-07 (a bare walk) on purpose.
    Recorded by the Phase 36 code review (WR-03), which found this paragraph
    still instructing a maintainer to synchronize a function that no longer
    exists.

    Reporting matches what the walker would emit for any other substituted
    default — ``missing`` when the payload carried nothing, ``type`` otherwise
    — so strict mode is fatal here exactly as it is on every other axis.

    **Phase 37 (NOBJ-MTZ-01, D-05 / D-06): the axis now also OWNS element
    decoding.** Until this phase it only coerced the outer CONTAINER and returned
    a present mapping verbatim, which was adequate while every mapping field was
    declared ``dict[str, Any]``. It is not adequate for ``dict[str, Model]``: the
    walker's missing ``dict`` branch means an element type is never consulted by
    anything else, so without the loop below the inner values would reach the
    caller as raw payload dicts under a model annotation — a type lie. Each value
    is therefore routed through :func:`_decode.walk_field` with the element hint,
    the extended path and, critically, **the sink this function was handed**.

    Never ``Model.from_api`` here: an override resolves its own sink through
    ``current_sink()`` rather than accepting the one threaded through this
    recursion, so the nested decode would leave the surrounding
    :class:`~matriz_client._decode.DecodeScope` and lock 5's dedupe collapse
    would stop firing inside it (``_decode.py:459-506`` documents the same trap
    for the walker's own nested-model branch). ``walk_field`` takes the sink as a
    parameter, which is why it is the correct entry point.

    The function **self-recurses** when the element hint is itself a mapping.
    That exists for ``DetailedPosition.report``, which Plan 37-03 types as
    ``dict[str, dict[str, InstrumentPositionReport]]`` — two levels of
    vendor-open keys (``contractType`` then ``symbol``), the only honest shape
    for a payload whose key sets are not enumerable.

    Payload-supplied keys are neutralized with :func:`_decode._safe_key` before
    they enter a ``field_path``, for the same reason the walker neutralizes an
    ``extra`` key (lock 11): a mapping key is wire content, and one carrying a
    newline would otherwise forge a line in any text handler. The walker's own
    helper is reused rather than re-implemented so the two cannot drift.
    """
    if not isinstance(value, dict):
        sink(model, path, "missing" if value is None else "type", "dict", type(value).__name__)
        return {}
    decoded: dict[Any, Any] = {}
    for key, item in value.items():
        item_path = f"{path}.{_decode._safe_key(key)}"
        if _is_mapping(element):
            decoded[key] = _mapping_value(
                item,
                _element_hint(element),
                path=item_path,
                model=model,
                sink=sink,
            )
        else:
            decoded[key] = _decode.walk_field(
                item,
                element,
                path=item_path,
                model=model,
                policy=_decode.POLICY,
                sink=sink,
            )
    return decoded


def _apply_mapping_policy(
    cls: type[Any], kwargs: dict[str, Any], *, sink: _decode.DecodeScope
) -> None:
    """Apply :func:`_mapping_value` to every mapping-declared field of ``cls``.

    Runs after :func:`matriz_client._decode.walk_model` and mutates its kwargs
    in place. It reaches TOP-LEVEL fields only: ``walk_field`` recurses into a
    nested model through ``walk_model`` directly, so a mapping field on a model
    reached as another model's field type would be missed. No shipped matriz
    model that declares a mapping field is ever another model's field type —
    ``test_no_mapping_carrying_model_is_ever_a_nested_field_type`` pins that
    precondition, and fails loudly if a future plan nests one.

    Phase 37: the declared ELEMENT hint is derived here (:func:`_element_hint`)
    and handed to :func:`_mapping_value`, which owns the decoding of the values.
    """
    # ``cast(Any, cls)`` is the walker's own mypy-strict discipline for
    # ``get_type_hints``-driven code: mypy rejects ``type[Any]`` against
    # ``lru_cache``'s ``Hashable`` parameter. No ``type: ignore`` is introduced.
    target = cast(Any, cls)
    hints = _decode.hints_for(target)
    model = cls.__name__
    for f in fields(target):
        hint = hints[f.name]
        if _is_mapping(hint):
            kwargs[f.name] = _mapping_value(
                kwargs[f.name],
                _element_hint(hint),
                path=f".{f.name}",
                model=model,
                sink=sink,
            )


def _convert(tp: Any, value: Any) -> Any:
    """Coerce ``value`` to the shape declared by ``tp``, applying safe defaults.

    Back-compat shim over :func:`matriz_client._decode.walk_field`. The
    argument order — type hint FIRST, value second — is **reversed** relative
    to higyrus's and market-data's ``_coerce`` and is kept exactly as it was:
    swapping it would be a silent break for anything that already imports this
    helper. The mapping branch stays here because it is matriz's own axis (see
    :func:`_mapping_value`).

    The throwaway sink is a fresh :class:`~matriz_client._decode.DecodeScope`,
    not the silent one, so a legacy caller reaching for the shim gets the same
    observability as a caller going through ``from_api`` — and never shares
    dedupe state with a surrounding request scope.

    Phase 37: the element hint is derived from ``get_args(tp)`` via
    :func:`_element_hint` and handed on, so the shim INHERITS the new element
    routing instead of bypassing it. A bare ``dict[str, Any]`` still yields
    ``Any``, which walks to a verbatim pass-through — ``_convert(dict[str, Any],
    None) == {}`` and the reversed ``(tp, value)`` order are both pinned by
    committed tests (F-17) and neither moves.
    """
    sink = _decode.DecodeScope()
    if _is_mapping(tp):
        return _mapping_value(value, _element_hint(tp), path="", model="", sink=sink)
    return _decode.walk_field(
        value,
        tp,
        path="",
        model="",
        policy=_decode.POLICY,
        sink=sink,
    )


# ----------------------------------------------------------------------
# Base
# ----------------------------------------------------------------------


class _SafeModel:
    """Mixin providing safe ``from_api``/``empty`` constructors for dataclasses."""

    # Declared so pyright accepts ``cls`` as a dataclass; populated by ``@dataclass``.
    __dataclass_fields__: ClassVar[dict[str, Any]]

    @classmethod
    def from_api(cls, data: Any) -> Self:
        """Build an instance from an API payload, with matriz's safe defaults.

        Phase 29 code review, WR-01. The previous docstring claimed that
        ``POLICY``'s ``non_dict_model = "empty_classmethod"`` "makes the walker"
        take matriz's non-dict fallback. It does not, and never did: the walker
        runs the identical ``data = {}`` substitution for all five paquetes and
        reads that field nowhere. A docstring attributing behaviour to an unread
        constant is worse than no docstring, and it also falsified
        ``29-SEMANTICS-MATRIX.md``'s central safety argument ("there is no
        unparameterized path in the walker").

        The axis is made load-bearing here instead, which is where matrix row 5
        always said it lived: the walker implements ``"from_api_none"``
        unconditionally, and a paquete whose policy declares
        ``"empty_classmethod"`` applies it at its own call site. The walker still
        emits the single terminal ``non_dict`` record first (lock 8), so the
        branch below changes the construction path, not the reporting.

        ``test_non_dict_returns_empty`` asserts the resulting equality, which is
        now true by construction rather than by coincidence.
        """
        sink = _decode.current_sink()
        kwargs = _decode.walk_model(cls, data, policy=_decode.POLICY, sink=sink)
        if _decode.POLICY.non_dict_model == "empty_classmethod" and not isinstance(data, dict):
            # Matrix row 5, now actually READ: matriz's non-dict fallback is the
            # ``empty()`` classmethod. Flipping the constant to ``"from_api_none"``
            # changes this line's behaviour, which is the property the matrix
            # claims for every cell in it.
            return cls.empty()
        # Lock 8 again: under a non-dict payload the walker already swapped its
        # field sink to ``SILENT_SINK``, so the mapping pass must be silent too
        # — otherwise a 204 body would emit one extra record per mapping field
        # on top of the terminal ``non_dict`` one.
        _apply_mapping_policy(
            cls, kwargs, sink=sink if isinstance(data, dict) else _decode.SILENT_SINK
        )
        return cls(**kwargs)

    @classmethod
    def empty(cls) -> Self:
        """Build an all-defaults instance. Emits nothing (T-29-33).

        ``empty()`` does not decode wire data: it is the nested-model default,
        the ``default_factory`` of several shipped fields, and the shape a
        non-dict payload converges on. Routing it through an emitting sink
        would produce one spurious ``missing`` record per field on every one of
        those calls and would break the terminal-``non_dict`` rule.
        """
        kwargs = _decode.walk_model(cls, {}, policy=_decode.POLICY, sink=_decode.SILENT_SINK)
        _apply_mapping_policy(cls, kwargs, sink=_decode.SILENT_SINK)
        return cls(**kwargs)

    def __bool__(self) -> bool:
        """A model carrying nothing is falsy (Phase 35, NOBJ-01).

        Emptiness is decided field by field against ``empty()``, so ``if
        snapshot:`` answers "did the wire carry anything for this shape" and
        never "did the request succeed". A field that is meaningful on its own
        should still be asked directly.
        """
        return self != type(self).empty()


# ----------------------------------------------------------------------
# Identifiers
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class InstrumentId(_SafeModel):
    """Canonical identifier for an instrument (§5.1)."""

    marketId: MarketId | None = None
    symbol: str | None = None


@dataclass(frozen=True)
class AccountId(_SafeModel):
    """Account wrapper used by WebSocket subscriptions (§7.1)."""

    id: str | None = None


# ----------------------------------------------------------------------
# Segments and instruments
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Segment(_SafeModel):
    """Market segment descriptor (§4.1)."""

    marketSegmentId: SegmentId | None = None
    marketId: MarketId | None = None


@dataclass(frozen=True)
class Instrument(_SafeModel):
    """Instrument header returned by list endpoints (§5.1)."""

    instrumentId: InstrumentId = field(default_factory=InstrumentId.empty)
    cficode: CFICode | None = None


@dataclass(frozen=True)
class TickPriceRange(_SafeModel):
    """One tick-size band inside :attr:`InstrumentDetail.tickPriceRanges` (§5.2).

    Live-capture provenance (D-04a class ``baseline``): field set taken verbatim
    from ``.planning/verification/schemas/matriz-client/get-instrument-detail.json``,
    captured 2026-06-10T01:01:55Z against ``https://api.remarkets.primary.com.ar``
    (reMarkets, symbol ``SOJ.ROS/NOV26 308 P``). The capture records exactly one
    key ``"0"`` carrying exactly these three names. Not from the vendor doc and
    not from a mock — the samples at ``documentation/Primary-API.md:330,378,454``
    agree on all three names, on the single key and on the runtime types, and are
    cited here as **vendor-documented corroboration only**, never as a capture.

    ``lowerLimit`` is declared ``float | None`` although the capture records
    ``int`` on the wire: ``_decode.walk_field``'s ``float`` arm widens ``int`` to
    ``float`` BEFORE consulting ``scalar_passthrough``, so the widening is silent
    and fabricates no divergence (37-RESEARCH F-5; identical reasoning to Phase
    36's ``BookLevel.price``). A future reader must not "fix" it to ``int`` —
    that would start reporting a divergence on every well-formed payload.
    ``upperLimit`` was ``null`` in every observed sample, so an absent one
    answers ``None`` rather than a typed zero.

    The roster is CLOSED at these three keys because that is what the capture
    shows (T-37-08). A fourth key the vendor adds later is discarded from the
    model but reported as a non-fatal ``extra`` divergence by the walker, which
    is the "closed roster + divergence reporting" form Phase 36's
    ``MarketDataEntries`` established for a partially observed payload.
    """

    lowerLimit: float | None = None
    upperLimit: float | None = None
    tick: float | None = None


@dataclass(frozen=True)
class InstrumentDetail(_SafeModel):
    """Full instrument detail (§5.2).

    The Primary API omits many fields depending on segment/CFI; safe defaults
    keep attribute access non-throwing.
    """

    instrumentId: InstrumentId = field(default_factory=InstrumentId.empty)
    cficode: CFICode | None = None
    segment: Segment = field(default_factory=Segment.empty)
    lowLimitPrice: float | None = None
    highLimitPrice: float | None = None
    minPriceIncrement: float | None = None
    minTradeVol: float | None = None
    maxTradeVol: float | None = None
    tickSize: float | None = None
    contractMultiplier: float | None = None
    roundLot: float | None = None
    priceConvertionFactor: float | None = None
    maturityDate: str | None = None
    currency: Currency | None = None
    orderTypes: list[OrderType] = field(default_factory=list)
    timesInForce: list[TimeInForce] = field(default_factory=list)
    instrumentPricePrecision: int | None = None
    instrumentSizePrecision: int | None = None
    securityDescription: str | None = None
    # D-05: a string-keyed MAPPING, never ``list[TickPriceRange]``. All three
    # observed samples carry exactly one key ``"0"``; nothing observed proves the
    # keys are contiguous or ordered, and flattening to a list would assert a
    # sequence property no evidence supports.
    tickPriceRanges: dict[str, TickPriceRange] = field(default_factory=dict)


# ----------------------------------------------------------------------
# Orders
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class NewOrderResponse(_SafeModel):
    """Identifiers returned by ``newSingleOrder`` / ``replaceById`` / ``cancelById`` (§6.3)."""

    clientId: str | None = None
    proprietary: str | None = None


@dataclass(frozen=True)
class Order(_SafeModel):
    """Single order status record (§6.8).

    ``orderId`` is ``None`` until the exchange accepts the order (§13).
    """

    orderId: str | None = None
    clOrdId: str | None = None
    proprietary: str | None = None
    execId: str | None = None
    accountId: str | None = None
    instrumentId: InstrumentId = field(default_factory=InstrumentId.empty)
    price: float | None = None
    orderQty: float | None = None
    ordType: OrderType | None = None
    side: Side | None = None
    timeInForce: TimeInForce | None = None
    transactTime: str | None = None
    avgPx: float | None = None
    lastPx: float | None = None
    lastQty: float | None = None
    cumQty: float | None = None
    leavesQty: float | None = None
    status: OrderStatus | None = None
    text: str | None = None


@dataclass(frozen=True)
class OrderReport(Order):
    """Execution report (§7.5) — superset of :class:`Order`."""

    wsClOrdId: str | None = None


# ----------------------------------------------------------------------
# Market data
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class MarketDataLevel(_SafeModel):
    """Price level inside an order-book entry (``BI`` / ``OF``)."""

    price: float | None = None
    size: int | None = None


@dataclass(frozen=True)
class MarketDataEntryValue(_SafeModel):
    """Scalar market-data entry (``LA``, ``SE``, ``OI`` …) per §8.1."""

    price: float | None = None
    size: int | None = None
    date: int | None = None


@dataclass(frozen=True)
class MarketDataSnapshot(_SafeModel):
    """Market-data response (§8.1).

    Each entry is optional in the wire payload; missing entries fall back
    to safe defaults so chained access (``snapshot.SE.price``) never
    raises.

    Phase 37 / ``NOBJ-MTZ-02`` adds six human-facing alias properties over the
    wire-named entry fields, in the form ``market-data-client`` established in
    Phase 36 (``MarketDataEntries``). Three things a future reader needs:

    1. **They are views and carry no behaviour.** Each is a single ``return``
       of the wire attribute — no copy, no cache, no default and no
       transformation, and none has a setter. ``test_null_object.py``'s
       ``test_each_alias_returns_the_identical_object_on_a_rest_parsed_snapshot``
       asserts this with ``is`` rather than ``==``, which is what makes a
       copying or caching alias fail rather than pass unnoticed.
    2. **``OP`` is excluded on purpose**, and so are ``HI``, ``LO``, ``TV`` and
       matriz's extra ``IV`` / ``EV`` / ``NV`` / ``ACP``. ``OP`` arrives as a
       BARE SCALAR rather than an ``{price, size, date}`` entry object — the
       comment at the ``CL`` declaration below already records that asymmetry
       (issue #102) — so an ``open`` alias would return a float where its five
       siblings return a model. The Phase 36 template excluded the scalar
       entries for the same reason.
    3. **This ONE class is both surfaces.** It is the REST return type of the
       ``/marketdata`` endpoints AND the payload type of
       :attr:`MarketDataFrame.marketData`, the WebSocket ``type == "Md"`` frame
       model. The six properties therefore serve the WebSocket surface with no
       ``ws_client.py`` change whatsoever (37-RESEARCH F-12) — a separate
       WS-side alias change would be a no-op. Because properties are invisible
       to :func:`typing.get_type_hints` and to :func:`dataclasses.fields`
       (Phase 35 criterio 5, D-16), they are equally invisible to
       ``_decode.walk_model`` and add no decode path on either surface.
    """

    BI: list[MarketDataLevel] = field(default_factory=list)
    OF: list[MarketDataLevel] = field(default_factory=list)
    LA: MarketDataEntryValue = field(default_factory=MarketDataEntryValue.empty)
    SE: MarketDataEntryValue = field(default_factory=MarketDataEntryValue.empty)
    OI: MarketDataEntryValue = field(default_factory=MarketDataEntryValue.empty)
    # CL viene como objeto {price, size, date} en la wire format (§8.1),
    # igual que LA/SE/OI. OP en cambio es escalar. Ver issue #102.
    CL: MarketDataEntryValue = field(default_factory=MarketDataEntryValue.empty)
    OP: float | None = None
    HI: float | None = None
    LO: float | None = None
    TV: float | None = None
    IV: float | None = None
    EV: float | None = None
    NV: float | None = None
    ACP: float | None = None

    @property
    def bids(self) -> list[MarketDataLevel]:
        """Human-facing alias over the wire-named field ``BI`` (NOBJ-MTZ-02, D-16)."""
        return self.BI

    @property
    def offers(self) -> list[MarketDataLevel]:
        """Human-facing alias over the wire-named field ``OF`` (NOBJ-MTZ-02, D-16)."""
        return self.OF

    @property
    def last(self) -> MarketDataEntryValue:
        """Human-facing alias over the wire-named field ``LA`` (NOBJ-MTZ-02, D-16)."""
        return self.LA

    @property
    def settlement(self) -> MarketDataEntryValue:
        """Human-facing alias over the wire-named field ``SE`` (NOBJ-MTZ-02, D-16)."""
        return self.SE

    @property
    def close(self) -> MarketDataEntryValue:
        """Human-facing alias over the wire-named field ``CL`` (NOBJ-MTZ-02, D-16)."""
        return self.CL

    @property
    def open_interest(self) -> MarketDataEntryValue:
        """Human-facing alias over the wire-named field ``OI`` (NOBJ-MTZ-02, D-16)."""
        return self.OI


@dataclass(frozen=True)
class Trade(_SafeModel):
    """Historical trade record (§8.4)."""

    symbol: str | None = None
    servertime: int | None = None
    size: int | None = None
    price: float | None = None
    datetime: str | None = None


# ----------------------------------------------------------------------
# Risk API
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Position(_SafeModel):
    """Aggregated position per symbol for an account (§9.1)."""

    symbol: str | None = None
    buySize: float | None = None
    buyPrice: float | None = None
    sellSize: float | None = None
    sellPrice: float | None = None
    totalDailyDiff: float | None = None
    totalDiff: float | None = None
    tradingSymbol: str | None = None


@dataclass(frozen=True)
class InstrumentPositionReport(_SafeModel):
    """One ``report[contractType][symbol]`` entry of :class:`DetailedPosition` (§9.2).

    **Provenance: vendor-documented, UNMEASURED (D-04a's third class).** The
    field set is transcribed from ``documentation/Primary-API.md:1745-1747``
    (repeated identically at ``:1785-1787``) inside the
    ``GET /rest/risk/detailedPosition/REM7374`` sample at ``:1701-1791``. This
    is **not** a capture and must never be cited as one: *no live observation of
    this payload exists anywhere in this repo*, and none can be produced while
    ``LIVE-MATZ-33`` stands — ``main_matriz.py`` asserts the remarkets hostname
    (D-MATZ-33) and that assert is not bypassed. Nobody has seen this shape on
    the wire. Real verification is deferred to Phase 39 / ``LIVE-NOBJ-01``,
    which is where this roster gets confirmed or corrected.

    Contrast with :class:`TickPriceRange` one screen up, whose provenance class
    is ``baseline``: that one cites a committed live capture with a date and an
    environment. The distinction is deliberate and load-bearing (SC-1).

    **The deferred subtree, named so it stays discoverable.** The sample's entry
    also carries a ``detailedPositions`` array (``:1710-1744``, ~21 fields per
    element) whose elements each carry a ``detailedDailyDiff`` object
    (``:1733-1742``, 8 fields). D-07 defers **both** rather than modelling a
    two-deep tree nobody has measured; shipping them would present an invented
    model as observed. Destination: Phase 39 / ``LIVE-NOBJ-01``.

    **The cost of the closed roster, disclosed (T-37-12).** ``report`` used to be
    a ``dict[str, Any]`` passthrough where every key the vendor sent was
    readable. It is a closed dataclass now, so ``detailedPositions`` — and any
    key the vendor adds later — is DISCARDED: its value never reaches the
    caller. Detection is not silent: the walker emits a non-fatal ``extra``
    divergence for each one (reported, never raised, not even under
    ``strict_decode``), and the artifact where a real run's divergences land is
    the append-only ``.planning/verification/matriz-client-findings.md``, where
    Phase 37 also filed this roster as declared-but-unobserved. Widening the
    roster is the right answer once a live run MEASURES one of those keys.

    Every field is a nullable scalar and **no field is a mapping** — F-11
    measured that ``test_no_mapping_carrying_model_is_ever_a_nested_field_type``
    walks a single level of ``__args__``, so a mapping declared on a model
    nested at depth 2 (which this class is) would be invisible to that guard.
    Keeping the model mapping-free is the phase's answer; deepening the guard is
    option (b) and is not in scope.

    The wire carries ``int`` for all three sizes; they are declared
    ``float | None`` because ``_decode.walk_field``'s ``float`` arm widens
    ``int`` BEFORE consulting ``scalar_passthrough``, so the widening is silent
    and fabricates no divergence — same reasoning as ``TickPriceRange``'s
    ``lowerLimit``. Do not "fix" them to ``int``.
    """

    instrumentInitialSize: float | None = None
    instrumentFilledSize: float | None = None
    instrumentCurrentSize: float | None = None


@dataclass(frozen=True)
class DetailedPosition(_SafeModel):
    """Detailed position aggregated per account (§9.2)."""

    account: str | None = None
    totalDailyDiffPlain: float | None = None
    totalMarketValue: float | None = None
    # TWO levels of vendor-open keys — ``contractType`` then ``symbol``
    # (``Primary-API.md:1707-1790``) — decoded by the self-recursing mapping
    # axis (D-06/D-07). Neither level is enumerable, so this is the only honest
    # shape: flattening it would fabricate an enum of contract types, and
    # forcing it to share a container shape with
    # ``AccountReport.detailedAccountReports`` would be wrong in the other
    # direction — that field is genuinely ONE level (37-RESEARCH F-7/F-8).
    #
    # NAMING SLIP, recorded so a later verification pass does not chase a ghost:
    # ``REQUIREMENTS.md`` and ``ROADMAP.md`` both say "AccountReport.report".
    # ``AccountReport`` has no ``report`` field and never did — the field is
    # ``DetailedPosition.report``, right here.
    report: dict[str, dict[str, InstrumentPositionReport]] = field(default_factory=dict)
    lastCalculation: str | None = None


@dataclass(frozen=True)
class DetailedAccountReport(_SafeModel):
    """One ``detailedAccountReports[key]`` entry of :class:`AccountReport` (§9.3).

    **Provenance: vendor-documented, UNMEASURED (D-04a's third class).** The
    field set is transcribed from ``documentation/Primary-API.md:1888`` inside
    the ``GET /rest/risk/accountReport/REM7374`` sample at ``:1817-1895``. This
    is **not** a capture: *no live observation of this payload exists anywhere in
    this repo*, and none can be produced while ``LIVE-MATZ-33`` stands —
    ``main_matriz.py`` asserts the remarkets hostname (D-MATZ-33) and that assert
    is not bypassed. Nobody has seen this shape on the wire. Real verification is
    deferred to Phase 39 / ``LIVE-NOBJ-01``.

    **The deferred subtrees, named so they stay discoverable.** The sample's
    entry also carries ``currencyBalance`` (``:1828-1859``, an open-keyed
    ``detailedCurrencyBalance`` map of ``{consumed, available}`` pairs) and
    ``availableToOperate`` (``:1860-1887``, a ``cash`` object with its own
    open-keyed ``detailedCash`` map plus four siblings). D-07 defers **both**
    rather than modelling open-keyed trees nobody has measured. Destination:
    Phase 39 / ``LIVE-NOBJ-01``.

    **The cost of the closed roster, disclosed (T-37-12).**
    ``detailedAccountReports`` used to be a ``dict[str, Any]`` passthrough where
    every key the vendor sent was readable. It is a closed dataclass now, so the
    two deferred objects — and any key the vendor adds later — are DISCARDED:
    their values never reach the caller. Detection is not silent: the walker
    emits a non-fatal ``extra`` divergence per key (reported, never raised, not
    even under ``strict_decode``), and the artifact where a real run's
    divergences land is the append-only
    ``.planning/verification/matriz-client-findings.md``, where Phase 37 also
    filed this roster as declared-but-unobserved.

    This entry sits under **ONE** level of vendor-open keys, unlike
    :class:`InstrumentPositionReport` which sits under two. The asymmetry is
    measured (37-RESEARCH F-7/F-8), not an oversight: forcing the two containers
    to share a depth would fabricate a level of keys one of the samples does not
    show.

    No field is a mapping, for the same F-11 reason as
    :class:`InstrumentPositionReport`. ``settlementDate`` is an epoch-millis
    ``int`` on the wire and is declared ``int | None`` accordingly.
    """

    settlementDate: int | None = None


@dataclass(frozen=True)
class AccountReport(_SafeModel):
    """Full account report with cash, margins and portfolio (§9.3)."""

    accountName: str | None = None
    marketMember: str | None = None
    marketMemberIdentity: str | None = None
    collateral: float | None = None
    margin: float | None = None
    availableToCollateral: float | None = None
    # ONE level of vendor-open keys (``Primary-API.md:1826-1890``). Deliberately
    # NOT mirrored on ``DetailedPosition.report``'s two-level shape — F-7
    # measured the asymmetry and forcing a shared depth here would fabricate a
    # level of keys the vendor sample does not show.
    detailedAccountReports: dict[str, DetailedAccountReport] = field(default_factory=dict)
    # D-02: a SCALAR leaf, not a mapping and not a model. Evidence: the vendor
    # sample carries a bare number at ``Primary-API.md:1894``
    # (``"portfolio":60240``), and the identical value appears as
    # ``"totalMarketValue":60240`` for the SAME account in the detailed-position
    # sample (``:1706``) — which is what makes "account market value" the
    # reading rather than "an object we failed to model". Consequence: it leaves
    # the mapping axis entirely (``_apply_mapping_policy`` no longer visits it)
    # and a malformed value is now a reported ``type`` divergence, fatal under
    # strict mode, instead of silently collapsing to ``{}`` (T-37-14).
    portfolio: float | None = None
    ordersMargin: float | None = None
    currentCash: float | None = None
    dailyDiff: float | None = None
    uncoveredMargin: float | None = None


# ----------------------------------------------------------------------
# WebSocket frames
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class MarketDataFrame(_SafeModel):
    """Market-data WebSocket frame (``type == "Md"``, §8.2)."""

    type: str | None = None
    timestamp: int | None = None
    instrumentId: InstrumentId = field(default_factory=InstrumentId.empty)
    marketData: MarketDataSnapshot = field(default_factory=MarketDataSnapshot.empty)


@dataclass(frozen=True)
class ExecutionReportFrame(_SafeModel):
    """Execution-report WebSocket frame (``type == "or"``, §7.5)."""

    type: str | None = None
    timestamp: int | None = None
    orderReport: OrderReport = field(default_factory=OrderReport.empty)


@dataclass(frozen=True)
class UnknownFrame:
    """Catch-all for WebSocket frames whose ``type`` is not modeled.

    Preserves the raw payload in :attr:`raw` so callers can still inspect
    forward-compatible fields without losing information. Implements the
    ``from_api``/``empty`` duck-typed contract so the WS dispatcher can
    treat it like any other frame model.

    Phase 29: exempt from the walker entirely per ``29-SEMANTICS-MATRIX.md``
    Section 3(c) — under a naive extra-key rule every key of every unknown
    frame would be "extra", but those keys are a deliberate catch-all, not a
    modelling gap. All three methods below stay hand-written and untouched.

    Phase 35 (D-08): the third of them is ``__bool__``. This class does not
    inherit :class:`_SafeModel`, but it IS a member of the public
    ``PrimaryWsMessage`` union, so ``if frame:`` has to read the same for every
    variant a caller can receive.
    """

    type: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: Any) -> Self:
        if not isinstance(data, dict):
            return cls()
        return cls(type=data.get("type"), raw=dict(data))

    @classmethod
    def empty(cls) -> Self:
        return cls()

    def __bool__(self) -> bool:
        return self != type(self).empty()


PrimaryWsMessage = MarketDataFrame | ExecutionReportFrame | UnknownFrame
"""Union of inbound WebSocket frame variants surfaced to user callbacks."""
