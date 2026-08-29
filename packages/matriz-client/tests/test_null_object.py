"""Null Object contract for ``matriz_client.models`` — NOBJ-01, Phase 35.

This paquete is the one hierarchy that already carried ``empty()`` before this
phase (Phase 29 shipped it), so Phase 35's source change here is ``__bool__``
alone. The suite pins five things:

1. Every shipped :class:`~matriz_client.models._SafeModel` subclass is **falsy**
   when it carries nothing, and ``Model.from_api(None) == Model.empty()``
   (ROADMAP Phase 35 criterio 1).
2. Every one of those classes becomes **truthy** the moment a single field
   differs from its empty value — truthiness is a field-level emptiness test,
   never a snapshot-level one.
3. ``empty()`` emits **zero** divergence records (T-29-33): it does not decode
   wire data, so it must not report substituted defaults.
4. :class:`~matriz_client.models.UnknownFrame` answers the same question the
   same way even though it sits OUTSIDE the base hierarchy — see the two
   dedicated cases at the bottom and the reasoning written there (D-08).
5. A read-only ``@property`` alias declared next to the wire fields of a
   ``frozen=True`` dataclass is **invisible** to :func:`typing.get_type_hints`
   and therefore to the walker — the invariant phases 36-38 depend on when they
   add ``last`` / ``bids`` aliases (ROADMAP Phase 35 criterio 5, D-16).
6. Phase 37 / ``NOBJ-MTZ-02`` **applies** point 5 to the real
   :class:`~matriz_client.models.MarketDataSnapshot`: the six human-facing
   aliases are asserted to be views (identity, not equality), to hold on a
   REST-parsed instance AND on one reached through
   :attr:`~matriz_client.models.MarketDataFrame.marketData`, and to leave the
   walker's view of the class untouched. The generic proof in point 5 is
   **cited, never duplicated** — see the docstrings of the cases at the bottom.

The class roster is obtained by **introspection of the real module**, never
from a hand-written fixture list (D-15): a fixture roster would keep passing on
the day a shipped model stops honouring the contract.

Both helpers below (``_safemodel_classes`` and ``_perturb``) and the two alias
fixture dataclasses are **module-local copies on purpose**. This monorepo has
no shared internal package by design, and the copies must not be replaced by an
import from another paquete nor from the repo-root harness: a helper shared
across paquetes would introduce exactly the cross-package coupling repo policy
forbids.

The alias fixtures are declared ``frozen=True`` **without** ``slots``, because
that is this paquete's convention (semantics matrix row 5, difference 5) and
criterio 5 has to be proven on the shape this paquete actually ships.
"""

from __future__ import annotations

import dataclasses
import inspect
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, get_type_hints

import pytest

from matriz_client import _decode, models
from matriz_client._decode import POLICY, DecodeScope, walk_model
from matriz_client.models import (
    MarketDataEntryValue,
    MarketDataFrame,
    MarketDataLevel,
    MarketDataSnapshot,
    UnknownFrame,
    _SafeModel,
)

_MESSAGE = "decode divergence"


@pytest.fixture(autouse=True)
def _pristine_decode_context() -> Iterator[None]:
    """Start every test in this module with an unbound decode mode and scope.

    Copied from ``test_decode.py`` for the same reason it exists there: once any
    test in the session drives a real ``_request``, the sync test context keeps
    that request's ``DECODE_SCOPE`` (and possibly ``STRICT_DECODE``) bound, and
    a later bare ``Model.from_api(None)`` would either join a stale dedupe set
    or raise under an inherited strict mode — turning assertions in this module
    green-or-red purely on test ORDER.
    """
    mode = _decode.STRICT_DECODE.get()
    scope = _decode.DECODE_SCOPE.get()
    _decode.STRICT_DECODE.set(False)
    _decode.DECODE_SCOPE.set(None)
    try:
        yield
    finally:
        _decode.STRICT_DECODE.set(mode)
        _decode.DECODE_SCOPE.set(scope)


# ---------------------------------------------------------------------------
# Roster + perturbation helpers (module-local copies — see module docstring)
# ---------------------------------------------------------------------------


def _safemodel_classes() -> list[type]:
    """Every shipped ``_SafeModel`` subclass of THIS paquete, by introspection.

    The base is private here and the filter references it directly rather than
    duck-typing around the leading underscore: this module lives inside the
    paquete, so reaching for the real base is the honest test, and a duck-typed
    predicate would also sweep in :class:`UnknownFrame`, which is covered
    separately and deliberately.

    The defining-module filter in the last condition is load-bearing: without
    it any subclass merely re-exported into ``models``' namespace would enter
    the roster and be asserted against as if this paquete shipped it.
    """
    return sorted(
        (
            obj
            for _, obj in inspect.getmembers(models, inspect.isclass)
            if issubclass(obj, _SafeModel)
            and obj is not _SafeModel
            and dataclasses.is_dataclass(obj)
            and obj.__module__ == models.__name__
        ),
        key=lambda c: c.__name__,
    )


def _perturb(empty: Any) -> Any:
    """Return a copy of ``empty`` differing from it in exactly one field.

    Branch order is load-bearing, and this is the paquete where it earns its
    keep: nearly every field declared here is Optional with a ``None`` default,
    so a helper that dispatched on ``str`` first would fall through on almost
    the whole roster and cover it vacuously. ``cur is None`` is therefore
    tested FIRST.

    The trailing nested-model branch handles the other half of the same
    problem: a nested-model field's empty value is a nested empty INSTANCE, not
    ``None`` (``Instrument.instrumentId`` is this paquete's example), so those
    are perturbed recursively.

    Falling off the end raises rather than returning ``empty`` unchanged: a
    class this helper cannot perturb must fail loudly instead of silently
    turning ``test_every_shipped_model_is_truthy_when_populated`` vacuous.
    """
    for f in dataclasses.fields(empty):
        cur = getattr(empty, f.name)
        if cur is None:
            return dataclasses.replace(empty, **{f.name: "SENTINEL"})
        if isinstance(cur, str):
            return dataclasses.replace(empty, **{f.name: "SENTINEL"})
        if isinstance(cur, bool):
            return dataclasses.replace(empty, **{f.name: not cur})
        if isinstance(cur, int | float):
            return dataclasses.replace(empty, **{f.name: cur + 1})
        if isinstance(cur, list):
            return dataclasses.replace(empty, **{f.name: ["SENTINEL"]})
        if isinstance(cur, dict):
            return dataclasses.replace(empty, **{f.name: {"k": "v"}})
        if isinstance(cur, _SafeModel):
            return dataclasses.replace(empty, **{f.name: _perturb(cur)})
    raise AssertionError(f"no perturbable field on {type(empty).__name__}")


def _divergences(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Every divergence record captured so far, in emission order."""
    return [r for r in caplog.records if r.getMessage() == _MESSAGE]


def _walk(
    cls: type,
    payload: Any,
    caplog: pytest.LogCaptureFixture,
) -> tuple[Any, list[logging.LogRecord]]:
    """Walk ``payload`` into ``cls`` with a fresh scope, returning instance + records.

    Driving the walker directly rather than through ``from_api`` keeps the
    record list the WALKER's, so a ``from_api`` override could not quietly
    change what this module measures.
    """
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        kwargs = walk_model(cls, payload, policy=POLICY, sink=DecodeScope())
    return cls(**kwargs), _divergences(caplog)


def _records(records: list[logging.LogRecord]) -> list[tuple[str, str, str, str]]:
    """Project records onto the four class-independent contract keys.

    The ``model`` key is deliberately excluded: the criterio-5 pair below
    compares an alias-carrying class against its alias-free twin, and those two
    necessarily disagree on their own class name and on nothing else.
    """
    return [
        (r.field_path, r.divergence, r.declared_type, r.observed_type)  # type: ignore[attr-defined]
        for r in records
    ]


# ---------------------------------------------------------------------------
# Module-local fixtures for the criterio-5 pair (D-16)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Leaf(_SafeModel):
    """Nested leaf shared by both halves of the alias pair."""

    price: float | None = None
    size: int | None = None


@dataclass(frozen=True)
class _AliasShaped(_SafeModel):
    """The exact shape phases 36-38 introduce: wire fields + a read-only alias."""

    LA: _Leaf = field(default_factory=_Leaf.empty)
    BI: list[_Leaf] = field(default_factory=list)

    @property
    def last(self) -> _Leaf:
        """Human-facing alias over the wire-named field (D-16)."""
        return self.LA


@dataclass(frozen=True)
class _AliasFree(_SafeModel):
    """The identical wire fields, with no property alias — the control."""

    LA: _Leaf = field(default_factory=_Leaf.empty)
    BI: list[_Leaf] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Criterio 1 — the roster is real
# ---------------------------------------------------------------------------


def test_the_model_roster_is_not_vacuous() -> None:
    """An empty roster would make every parametrized test below pass vacuously.

    ``>= 17`` rather than ``== 17``: 17 is the count measured for this paquete
    in ``35-RESEARCH.md`` F-1, and phases 36-38 may legitimately add classes.
    Every class is also asserted individually, so the guard only has to catch
    the catastrophic case where introspection returns nothing at all.
    """
    assert len(_safemodel_classes()) >= 17


@pytest.mark.parametrize("cls", _safemodel_classes(), ids=lambda c: c.__name__)
def test_every_shipped_model_is_falsy_when_empty(cls: type) -> None:
    """NOBJ-01: a model carrying nothing answers ``False`` to ``bool()``."""
    assert bool(cls.from_api(None)) is False  # type: ignore[attr-defined]
    assert cls.from_api(None) == cls.empty()  # type: ignore[attr-defined]


@pytest.mark.parametrize("cls", _safemodel_classes(), ids=lambda c: c.__name__)
def test_every_shipped_model_is_truthy_when_populated(cls: type) -> None:
    """NOBJ-01, the falsification half: one differing field is enough."""
    assert bool(_perturb(cls.empty())) is True  # type: ignore[attr-defined]


@pytest.mark.parametrize("cls", _safemodel_classes(), ids=lambda c: c.__name__)
def test_empty_emits_nothing(cls: type, caplog: pytest.LogCaptureFixture) -> None:
    """T-29-33 / D-07: ``empty()`` does not decode wire data, so it reports nothing."""
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        instance = cls.empty()  # type: ignore[attr-defined]

    assert instance is not None
    assert _divergences(caplog) == []


# ---------------------------------------------------------------------------
# Criterio 1, the outlier — `UnknownFrame` is outside the roster ON PURPOSE
# ---------------------------------------------------------------------------
#
# `UnknownFrame` does not inherit the base, so the introspection filter above
# cannot see it — and that exclusion is correct, not a bug in the filter. The
# class is exempt from the walker entirely (semantics matrix Section 3(c)):
# under a naive extra-key rule every key of an unmodelled frame would be
# "extra", but those keys are a deliberate catch-all. What it is NOT exempt
# from is the truthiness contract: it is a member of the public
# `PrimaryWsMessage` union, so `if frame:` has to read the same for every
# variant a caller can receive (D-08). Hence a hand-written `__bool__` on the
# class and the two by-name cases below. A future reader tempted to "fix" the
# roster filter so it swallows this class should read this comment first.


def test_UnknownFrame_is_falsy_when_empty() -> None:
    """D-08: the union's catch-all variant answers ``False`` when it carries nothing."""
    assert bool(UnknownFrame.empty()) is False
    assert bool(UnknownFrame.from_api(None)) is False
    assert UnknownFrame.from_api(None) == UnknownFrame.empty()


def test_UnknownFrame_is_truthy_when_it_carries_a_frame_type() -> None:
    """D-08: a frame that preserved a real payload is truthy, like every sibling."""
    frame = UnknownFrame.from_api({"type": "brandNew", "someField": 1})

    assert frame.type == "brandNew"
    assert bool(frame) is True


# ---------------------------------------------------------------------------
# Criterio 5 — @property aliases are invisible to the walker (D-16)
# ---------------------------------------------------------------------------


def test_property_aliases_are_invisible_to_get_type_hints() -> None:
    """``get_type_hints`` reports every DECLARED annotation, and the alias is not one.

    One adaptation this paquete forces and the tracer did not: its base declares
    ``__dataclass_fields__`` as a ``ClassVar`` so the type-checker will accept
    ``cls`` as a dataclass. That annotation is real, so ``get_type_hints``
    reports it, while ``dataclasses.fields`` correctly omits it — and the walker
    enumerates the latter. The subtraction below is therefore pinned as an
    equality against that one known name rather than waved away: if a second
    non-field annotation ever appears on the base, this test says so.

    The property is in neither collection, which is the invariant phases 36-38
    depend on.
    """
    hints = get_type_hints(_AliasShaped)
    declared = {f.name for f in dataclasses.fields(_AliasShaped)}

    assert declared <= set(hints)
    assert set(hints) - declared == {"__dataclass_fields__"}
    assert "last" not in hints


def test_adding_a_property_alias_does_not_change_the_divergence_count(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The alias cannot fabricate a divergence nor suppress one (criterio 5).

    The invariant asserted is EQUALITY between the alias-carrying class and its
    alias-free twin, never an absolute record count: plan 35-05 changes what the
    walker emits for a non-optional link carrying nothing, and this test must
    survive that change untouched. If it ever reddens, the alias itself became
    visible to the walker — which is the only thing it is here to detect.
    """
    shaped, shaped_records = _walk(_AliasShaped, {}, caplog)
    free, free_records = _walk(_AliasFree, {}, caplog)

    assert _records(shaped_records) == _records(free_records)
    assert shaped.LA == free.LA
    assert shaped.BI == free.BI
    assert shaped.last is shaped.LA


# ---------------------------------------------------------------------------
# NOBJ-MTZ-02 (Phase 37) — criterio 5 APPLIED to the real MarketDataSnapshot
# ---------------------------------------------------------------------------
#
# Everything below asserts the six aliases on the class this paquete actually
# ships. It deliberately does NOT re-prove the invariant: the generic proof
# lives in `test_property_aliases_are_invisible_to_get_type_hints` and
# `test_adding_a_property_alias_does_not_change_the_divergence_count` above,
# with their `_AliasShaped` / `_AliasFree` fixtures, whose docstring already
# says they exist "for phases 36-38". Those two tests and their fixtures are
# not to be modified by this phase — they are cited by name from here instead.
#
# The single fact that makes this section short: `MarketDataFrame.marketData`
# IS a `MarketDataSnapshot` (37-RESEARCH F-12). One class serves the REST
# return type and the WebSocket frame payload, so six properties on that one
# class satisfy Success Criterion 3 on both surfaces and `ws_client.py` needs
# no change at all. The pair of identity cases below is the direct evidence
# for that claim, which is why it is asserted rather than assumed.

_ALIAS_NAMES = {"bids", "offers", "last", "settlement", "close", "open_interest"}

#: The fourteen declared wire fields of ``MarketDataSnapshot``, asserted exactly
#: so an accidental fifteenth field or a rename reddens here.
_WIRE_FIELDS = {
    "BI",
    "OF",
    "LA",
    "SE",
    "OI",
    "CL",
    "OP",
    "HI",
    "LO",
    "TV",
    "IV",
    "EV",
    "NV",
    "ACP",
}

#: Wire entries carrying no alias, on purpose. ``OP`` is the headline case: it
#: arrives as a BARE FLOAT rather than an ``{price, size, date}`` object (the
#: comment at the field in ``models.py`` records this, issue #102), so there is
#: no entry object for an ``open`` alias to view. The other seven are matriz's
#: extra scalars, absent from the Phase 36 template and outside NOBJ-MTZ-02.
_UNALIASED_SCALARS = {"OP", "HI", "LO", "TV", "IV", "EV", "NV", "ACP"}

#: A market-data body in the REST shape (§8.1), values taken from the payload
#: ``test_models.py`` already pins for this class.
_REST_MARKET_DATA: dict[str, Any] = {
    "BI": [{"price": 179.75, "size": 275}, {"price": 178.95, "size": 514}],
    "OF": [{"price": 179.8, "size": 1000}],
    "LA": {"price": 179.75, "size": 5, "date": 1669852800000},
    "SE": {"price": 180.3, "size": None, "date": 1669852800000},
    "CL": {"price": 180.35, "size": None, "date": 1669852800000},
    "OI": {"price": None, "size": 217596, "date": 1664150400000},
    "OP": 180.35,
}

#: The identical market data, wrapped in the ``type == "Md"`` envelope
#: ``ws_client._parse_frame`` hands to ``MarketDataFrame.from_api`` (§8.2).
_WS_FRAME: dict[str, Any] = {
    "type": "Md",
    "timestamp": 1669852800000,
    "instrumentId": {"marketId": "ROFX", "symbol": "DLR/DIC23"},
    "marketData": _REST_MARKET_DATA,
}


def test_the_six_alias_names_and_the_fourteen_wire_fields_are_disjoint() -> None:
    """No alias may collide with a declared field name (NOBJ-MTZ-02).

    The rationale differs from ``market-data-client``'s and must not be copied
    from it verbatim. There the class is ``frozen=True, slots=True``, so a
    colliding name is a SLOT collision that fails loudly at class creation.
    This paquete's dataclasses carry no ``slots`` (semantics matrix row 5,
    difference 5), so a collision here would be silent NAME SHADOWING: the
    property would sit on the class and win attribute lookup over the instance
    ``__dict__`` entry the dataclass ``__init__`` wrote, quietly hiding decoded
    wire data behind a view of a different field. Nothing would raise. That is
    exactly why the disjointness has to be asserted rather than trusted to the
    runtime.

    The wire roster is asserted EXACTLY, not as a subset, so an accidental
    fifteenth field or a rename reddens here instead of widening the surface.
    """
    field_names = {f.name for f in dataclasses.fields(MarketDataSnapshot)}

    assert field_names == _WIRE_FIELDS
    assert len(field_names) == 14
    assert field_names & _ALIAS_NAMES == set()
    # And the frozen dataclass still constructs with the properties present.
    assert MarketDataSnapshot.empty() is not None


def test_each_alias_returns_the_identical_object_on_a_rest_parsed_snapshot() -> None:
    """The six aliases are plain read-only views — no copy, no cache, no transformation.

    ``is`` rather than ``==`` is the whole point: an alias that built a copy, a
    cached value or a derived object would still compare equal and would still
    pass an equality assertion, while silently ceasing to be a view of the wire
    field (T-37-27).
    """
    snapshot = MarketDataSnapshot.from_api(_REST_MARKET_DATA)

    assert snapshot.bids is snapshot.BI
    assert snapshot.offers is snapshot.OF
    assert snapshot.last is snapshot.LA
    assert snapshot.settlement is snapshot.SE
    assert snapshot.close is snapshot.CL
    assert snapshot.open_interest is snapshot.OI


def test_each_alias_returns_the_identical_object_on_a_ws_frame_parsed_snapshot() -> None:
    """The same six identities hold on a snapshot reached through a WebSocket frame.

    This is the falsifiable form of Success Criterion 3's "es el mismo objeto y
    el mismo juego de alias". ``MarketDataFrame.marketData`` is annotated
    ``MarketDataSnapshot``, so the WS surface inherits the properties with no
    ``ws_client.py`` change; asserting it here means a future retype of that
    field — the only way the claim could stop holding — reddens immediately
    instead of silently splitting the two surfaces apart.
    """
    frame = MarketDataFrame.from_api(_WS_FRAME)
    snapshot = frame.marketData

    assert isinstance(snapshot, MarketDataSnapshot)
    assert snapshot.bids is snapshot.BI
    assert snapshot.offers is snapshot.OF
    assert snapshot.last is snapshot.LA
    assert snapshot.settlement is snapshot.SE
    assert snapshot.close is snapshot.CL
    assert snapshot.open_interest is snapshot.OI


def test_the_alias_chain_reads_the_frame_payload_values_without_raising() -> None:
    """A WS frame carrying book levels and a last price is readable through the aliases."""
    snapshot = MarketDataFrame.from_api(_WS_FRAME).marketData

    assert snapshot.last.price == 179.75
    assert snapshot.last.size == 5
    assert isinstance(snapshot.bids[0], MarketDataLevel)
    assert snapshot.bids[0].price == 179.75
    assert snapshot.bids[1].size == 514
    assert snapshot.offers[0].price == 179.8
    assert snapshot.settlement.price == 180.3
    assert snapshot.close.price == 180.35
    assert snapshot.open_interest.size == 217596


def test_one_class_serves_both_surfaces_so_the_alias_set_is_shared() -> None:
    """REST and WS answer the SAME six alias names because they are the same class.

    37-RESEARCH F-12, asserted rather than assumed: this is the measurement that
    makes a separate WebSocket-side alias task a no-op.
    """
    rest = MarketDataSnapshot.from_api(_REST_MARKET_DATA)
    ws = MarketDataFrame.from_api(_WS_FRAME).marketData

    assert type(rest) is type(ws) is MarketDataSnapshot
    for name in _ALIAS_NAMES:
        assert isinstance(getattr(type(rest), name), property)
        assert getattr(rest, name) == getattr(ws, name)


def test_the_empty_snapshot_answers_all_six_aliases_without_raising() -> None:
    """T-37-23: every alias views a field whose default is a Null Object.

    The two list aliases answer ``[]``; the four entry aliases answer the empty
    :class:`MarketDataEntryValue`, so ``.price`` on any of them is ``None``
    rather than an ``AttributeError``.
    """
    snapshot = MarketDataSnapshot.empty()

    assert snapshot.bids == []
    assert snapshot.offers == []
    for name in ("last", "settlement", "close", "open_interest"):
        entry = getattr(snapshot, name)
        assert isinstance(entry, MarketDataEntryValue)
        assert entry == MarketDataEntryValue.empty()
        assert entry.price is None


def test_the_empty_frame_chain_reaches_the_last_alias_and_answers_none() -> None:
    """T-37-23 through the full WebSocket chain: ``frame.marketData.last.price``.

    The deepest reachable chain a caller writes on the WS surface, over a frame
    that carries nothing at all.
    """
    assert MarketDataFrame.empty().marketData.last.price is None
    assert MarketDataFrame.from_api(None).marketData.bids == []
    assert MarketDataFrame.from_api({"type": "Md"}).marketData.open_interest.size is None


def test_the_bare_scalar_entries_are_deliberately_left_unaliased() -> None:
    """``OP`` and matriz's seven extra scalars get NO alias — a decision, not an omission.

    ``OP`` is the one a reader would expect to find as ``open``: it is excluded
    because it arrives as a bare float, not as an ``{price, size, date}`` entry
    object, so an ``open`` alias would return a scalar where its five siblings
    return a model — an asymmetry the Phase 36 template also refused. ``HI``,
    ``LO`` and ``TV`` are excluded for the same reason; ``IV``, ``EV``, ``NV``
    and ``ACP`` are matriz-only scalars absent from the template and outside
    NOBJ-MTZ-02's named set.
    """
    assert _UNALIASED_SCALARS <= _WIRE_FIELDS
    assert _UNALIASED_SCALARS | {"BI", "OF", "LA", "SE", "OI", "CL"} == _WIRE_FIELDS

    for name in ("open", "high", "low", "trade_volume", "traded_volume"):
        assert not hasattr(MarketDataSnapshot, name)

    # The alias set is exactly the six NOBJ-MTZ-02 names, no more.
    properties = {n for n, v in vars(MarketDataSnapshot).items() if isinstance(v, property)}
    assert properties == _ALIAS_NAMES


def test_the_six_aliases_are_invisible_on_the_real_snapshot_class() -> None:
    """Criterio 5 APPLIED once to the shipped class — the proof is not re-run here.

    ``test_property_aliases_are_invisible_to_get_type_hints`` and
    ``test_adding_a_property_alias_does_not_change_the_divergence_count`` above
    already establish the invariant generically, on fixtures declared in this
    paquete's own shape. This case only checks that the REAL class matches those
    fixtures' shape, so the generic conclusion actually transfers to it — it
    deliberately does not rebuild the ``_AliasShaped`` / ``_AliasFree`` machinery
    (T-37-25).
    """
    hints = get_type_hints(MarketDataSnapshot)
    declared = {f.name for f in dataclasses.fields(MarketDataSnapshot)}

    assert declared <= set(hints)
    assert set(hints) - declared == {"__dataclass_fields__"}
    assert set(hints) & _ALIAS_NAMES == set()
    assert declared & _ALIAS_NAMES == set()
