"""SC-2 regression — the no-data row of ``/marketdata`` is a legitimate shape.

The Phase 33 live run (33-05) measured three ``missing`` divergences on
:class:`~market_data_client.models.MarketDataSnapshot`, on both surfaces:
``F-72``/``F-92`` (``.staleness_seconds``), ``F-73``/``F-93`` (``.market_data``)
and ``F-75``/``F-95`` (``.entries``). The strict pass turned two of them into
raises::

    PROBE market_data_sync: FINDING SHAPE [sync] MarketDataDecodeError model=MarketDataSnapshot path=.staleness_seconds declared=float observed=NoneType
    PROBE latest_sync:      FINDING SHAPE [sync] MarketDataDecodeError model=MarketDataSnapshot path=.entries          declared=list  observed=NoneType

This is NOT vendor breakage: ``GET /marketdata/latest`` answers for a symbol the
feed has never delivered with a row that carries ``symbol`` + ``note`` and
``null`` everywhere else — the committed baseline
``.planning/verification/schemas/market-data-client/get-latest.json`` shows
exactly that. The three fields were simply over-declared as non-``Optional``.

Operator disposition (33-07 Task 1, ``SC-2 = fix-shape-now``): widen all three.
A parser-side substitution was explicitly rejected — manufacturing ``0.0`` /
``[]`` / ``{}`` for a field the vendor legitimately sends as ``null`` is the
silent typed zero this milestone exists to remove. SOURCE-BREAKING for
``market-data-client``; Phase 34 carries the 0.4.0 → 0.5.0 bump.

The three fields keep their positional slot and stay REQUIRED constructor
arguments — only the annotation widens — so no field order changes and no
default masks an absent key.

**Phase 36 (NOBJ-MD-01 / NOBJ-MD-02, D-04 / D-07) revokes that disposition IN
PART — by field role, not as a rollback.** ``market_data`` and ``entries`` are
CHAIN LINKS and go back to required, the first as the typed Null Object
``MarketDataEntries``; ``staleness_seconds`` is a LEAF and keeps its ``| None``
(D-NO-03). The revocation does not resurrect the ``F-72``/``F-73``/``F-75`` and
``F-92``/``F-93``/``F-95`` divergences the header records, because Phase 35's
NOBJ-02 policy landed in between: a ``null`` or absent value on a NON-OPTIONAL
list or nested-model link now collapses to ``[]`` / the empty instance and emits
NOTHING. That is what makes required honest again for a link and still dishonest
for a leaf, which has nothing to point at. Source plan for the revocation:
``.future_plans/api-tipada-null-objects.md``.

The assertions below are therefore MIGRATED, never deleted (SC-4): each moves to
the property it still protects — ``is None`` becomes ``== []`` for the list link
and a falsy-truthiness question for the container, while the leaf's ``is None``
is left exactly as it was. The final test of the file is the one that survives
both phases untouched: a WRONG-TYPED value is still a divergence and is still
fatal under ``strict_decode``. Neither the widening nor its revocation was ever
allowed to amnesty that.

**Phase 36 code review, CR-02 — the fixture now IS the baseline.** Until the
review, ``_NO_DATA_ROW`` claimed to be "the exact shape of the committed
get-latest.json baseline" and was not: it populated ``market_id`` with ``"ZZZ"``
and ``active`` with ``False``, the two fields the baseline sends as ``null``, and
it carried an ``entries`` key the baseline does not carry at all. The
strict-mode test — the one this module calls "the assertion with teeth" — was
therefore green only because its fixture had been populated; against the payload
it claimed to represent it would have been red. ``_NO_DATA_ROW`` is now the
committed baseline verbatim, and the consequence is STATED rather than hidden:

* the two LINKS (``entries``, ``market_data``) collapse silently and the chain
  stays walkable — the property Phase 36 exists to establish, now demonstrated
  against the one payload the repo has actually measured;
* the two LEAVES ``market_id`` (``str``) and ``active`` (``bool``) are still
  OVER-DECLARED. The walker manufactures ``""`` / ``False`` for them and strict
  mode raises on ``.market_id``. This is a real, measured divergence, it is NOT
  fixed here — a source-breaking shape change needs the operator checkpoint the
  33-07 Task 1 precedent established — and it is filed as a deferred item
  (``36-DEFERRED-market-data-leaves.md``) so Phase 39 finds it predicted instead
  of rediscovering it as a surprise.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import BookLevel, MarketDataDecodeError, aio

# ``GET /marketdata/latest`` for a symbol the feed never delivered — the committed
# baseline ``.planning/verification/schemas/market-data-client/get-latest.json``
# VERBATIM: ``symbol`` + ``note`` carry a string and every other key is ``null``.
# There is deliberately NO ``entries`` key: the baseline does not send one, and
# adding it would be the same kind of quiet populating CR-02 found. Only the
# identifiers are synthesised (C-4).
_NO_DATA_ROW: dict[str, Any] = {
    "active": None,
    "market_data": None,
    "market_id": None,
    "note": "sin datos para el simbolo",
    "received_at": None,
    "staleness_seconds": None,
    "symbol": "AAA1",
}

# The same row with ONLY the two over-declared LEAVES populated, so the two LINKS
# are the only thing left that could raise. This is what isolates "a link is
# never fatal" from "a leaf still is" — without it, the strict raise on
# ``.market_id`` would mask whether the links were fatal too.
_LINKS_ONLY_NO_DATA_ROW: dict[str, Any] = {**_NO_DATA_ROW, "market_id": "ZZZ", "active": False}

# A populated ``/marketdata`` row — the non-regression control.
_POPULATED_ROW: dict[str, Any] = {
    "symbol": "AAA1",
    "market_id": "ZZZ",
    "active": True,
    "entries": ["BI", "OF"],
    "market_data": {"BI": [{"price": 10, "size": 1}]},
    "staleness_seconds": 1.5,
    "received_at": "2099-01-01T00:00:00Z",
}


def test_no_data_row_keeps_its_nulls(httpx_mock: HTTPXMock) -> None:
    """The row still says "nothing here" — now without a ``None`` on either link.

    **This test's NAME is load-bearing and must not be renamed.** It is the
    ``Regression:`` anchor of findings ``F-72`` / ``F-73`` / ``F-75`` in the
    append-only ledger ``.planning/verification/market-data-client-findings.md``,
    and ``verification/test_cycle_closure_market_data.py`` resolves that bullet
    to a real ``def <test>(``. Renaming it turns six CONFIRMED findings into
    dangling links and reddens the cycle-closure gate.

    What the name still means after the Phase 36 revocation: the LEAF keeps its
    ``None`` — ``staleness_seconds`` has nothing to point at, and manufacturing
    ``0.0`` for it would be the silent typed zero this milestone exists to
    remove. The two LINKS answer the same "nothing here" through emptiness
    instead — ``entries == []`` and a falsy ``market_data`` — and the chain
    through the falsy container stays walkable, which is the whole point of the
    Null Object. No substitution was ever manufactured for any of the three.

    Since CR-02 the payload is the committed baseline verbatim, so this test also
    records the two substitutions that ARE manufactured on it — ``market_id`` and
    ``active`` — as the deferred over-declaration they are, not as data.
    """
    httpx_mock.add_response(method="GET", json=[_NO_DATA_ROW])

    rows = market_data_client.client._get_default().get_latest(symbol="AAA1")

    assert len(rows) == 1
    row = rows[0]
    assert row.entries == []
    assert bool(row.market_data) is False
    assert row.market_data.last.price is None
    assert row.market_data.bids == []
    assert row.staleness_seconds is None
    # The fields that DO arrive are untouched.
    assert row.symbol == "AAA1"
    assert row.note == "sin datos para el simbolo"
    # CR-02, stated not hidden: these two are still declared non-Optional, so the
    # walker substitutes the silent typed zero this milestone exists to remove.
    # Deferred (36-DEFERRED-market-data-leaves.md), NOT amnestied — when the
    # operator widens them, these two lines turn into ``is None`` and this test
    # is the one that reddens first.
    assert row.market_id == ""
    assert row.active is False


async def test_no_data_row_keeps_its_nulls_async(httpx_mock: HTTPXMock) -> None:
    """Async twin of :func:`test_no_data_row_keeps_its_nulls` (C-3).

    Its NAME is load-bearing for the same reason as its sync twin's: it is the
    ``Regression:`` anchor of ``F-92`` / ``F-93`` / ``F-95``.
    """
    httpx_mock.add_response(method="GET", json=[_NO_DATA_ROW])

    rows = await aio._get_default().get_latest(symbol="AAA1")

    assert len(rows) == 1
    row = rows[0]
    assert row.entries == []
    assert bool(row.market_data) is False
    assert row.market_data.last.price is None
    assert row.market_data.bids == []
    assert row.staleness_seconds is None
    assert row.symbol == "AAA1"
    assert row.note == "sin datos para el simbolo"
    # CR-02 — see the sync twin.
    assert row.market_id == ""
    assert row.active is False


def test_no_data_row_links_are_never_fatal_under_strict_decode(httpx_mock: HTTPXMock) -> None:
    """The two LINKS collapse silently — the strict raise stops firing for them.

    This is the assertion with teeth: before the widening, this exact body raised
    ``MarketDataDecodeError`` in strict mode, which is why the 33-05 strict pass
    reported ``FINDING SHAPE`` on ``market_data_*`` and ``latest_*``.

    The payload isolates the question (CR-02). It is the committed baseline with
    the two over-declared LEAVES populated, so ``entries`` and ``market_data``
    are the only ``null``\\ s left: if either link were still fatal, this raises,
    and the raise could not be blamed on anything else.
    """
    httpx_mock.add_response(method="GET", json=[_LINKS_ONLY_NO_DATA_ROW])

    with market_data_client.Client(
        base_url="https://market-data-develop.test/api",
        token="test-token",
        token_expires_at=9_999_999_999.0,
        strict_decode=True,
    ) as client:
        rows = client.get_latest(symbol="AAA1")

    assert rows[0].entries == []
    assert bool(rows[0].market_data) is False
    assert rows[0].market_data.last.price is None


async def test_no_data_row_links_are_never_fatal_under_strict_decode_async(
    httpx_mock: HTTPXMock,
) -> None:
    """Async twin of :func:`test_no_data_row_links_are_never_fatal_under_strict_decode` (C-3)."""
    httpx_mock.add_response(method="GET", json=[_LINKS_ONLY_NO_DATA_ROW])

    async with aio.AsyncClient(
        base_url="https://market-data-develop.test/api",
        token="test-token",
        token_expires_at=9_999_999_999.0,
        strict_decode=True,
    ) as client:
        rows = await client.get_latest(symbol="AAA1")

    assert rows[0].entries == []
    assert bool(rows[0].market_data) is False
    assert rows[0].market_data.last.price is None


def test_the_measured_no_data_row_still_raises_on_an_over_declared_leaf(
    httpx_mock: HTTPXMock,
) -> None:
    """CR-02 — the divergence the phase did NOT fix, asserted instead of hidden.

    Against the committed baseline VERBATIM, strict decode raises on
    ``.market_id`` (``str`` declared, ``NoneType`` observed) and would raise on
    ``.active`` next. Both are scalar LEAVES with nothing to point at on a
    no-data row — the same D-NO-03 argument that kept ``staleness_seconds``
    nullable — but widening them is source-breaking and belongs to an operator
    checkpoint, so it is deferred, not silently absorbed
    (``36-DEFERRED-market-data-leaves.md``).

    The ``field_path`` assertion is the load-bearing half: it pins that the raise
    comes from a LEAF and NEVER from ``.market_data`` / ``.entries``. Should a
    link regress into being fatal again, this test reddens on the path rather
    than passing on the mere fact that *something* raised.
    """
    httpx_mock.add_response(method="GET", json=[_NO_DATA_ROW])

    with (
        market_data_client.Client(
            base_url="https://market-data-develop.test/api",
            token="test-token",
            token_expires_at=9_999_999_999.0,
            strict_decode=True,
        ) as client,
        pytest.raises(MarketDataDecodeError) as exc,
    ):
        client.get_latest(symbol="AAA1")

    assert exc.value.model == "MarketDataSnapshot"
    assert exc.value.field_path == ".market_id"
    assert exc.value.declared_type == "str"
    assert exc.value.observed_type == "NoneType"


async def test_the_measured_no_data_row_still_raises_on_an_over_declared_leaf_async(
    httpx_mock: HTTPXMock,
) -> None:
    """Async twin of :func:`test_the_measured_no_data_row_still_raises_on_an_over_declared_leaf`."""
    httpx_mock.add_response(method="GET", json=[_NO_DATA_ROW])

    async with aio.AsyncClient(
        base_url="https://market-data-develop.test/api",
        token="test-token",
        token_expires_at=9_999_999_999.0,
        strict_decode=True,
    ) as client:
        with pytest.raises(MarketDataDecodeError) as exc:
            await client.get_latest(symbol="AAA1")

    assert exc.value.model == "MarketDataSnapshot"
    assert exc.value.field_path == ".market_id"
    assert exc.value.declared_type == "str"
    assert exc.value.observed_type == "NoneType"


def test_populated_row_still_decodes(httpx_mock: HTTPXMock) -> None:
    """Non-regression: neither the widening nor its revocation weakens this path.

    The ``market_data`` assertion moved from a whole-dict literal to the chain,
    and the wire ``10`` is asserted as ``10.0``: ``walk_field``'s float arm
    widens ``int`` before consulting ``scalar_passthrough``, silently
    (36-RESEARCH F-3).
    """
    httpx_mock.add_response(method="GET", json={"count": 1, "items": [_POPULATED_ROW]})

    rows = market_data_client.client._get_default().get_market_data()

    assert len(rows) == 1
    assert rows[0].entries == ["BI", "OF"]
    assert bool(rows[0].market_data) is True
    assert rows[0].market_data.bids == [BookLevel(price=10.0, size=1)]
    assert rows[0].market_data.bids[0].price == 10.0
    assert rows[0].staleness_seconds == 1.5


def test_a_wrong_typed_value_is_still_a_divergence(httpx_mock: HTTPXMock) -> None:
    """The widening admits ``None`` ONLY — a wrong type stays fatal in strict mode.

    Widening to ``| None`` must not become a blanket amnesty. ``entries`` arriving
    as a ``str`` is still a real divergence and must still raise, otherwise the
    fix would have traded one silent substitution for another.

    CR-02: the payload is built on ``_LINKS_ONLY_NO_DATA_ROW``, not on the raw
    baseline, and the ``field_path`` is pinned. Built on the baseline this test
    would go green off the unrelated ``.market_id`` raise while ``entries``
    was never even reached — a bare ``pytest.raises`` cannot tell those apart.
    """
    httpx_mock.add_response(
        method="GET", json=[{**_LINKS_ONLY_NO_DATA_ROW, "entries": "not-a-list"}]
    )

    with (
        market_data_client.Client(
            base_url="https://market-data-develop.test/api",
            token="test-token",
            token_expires_at=9_999_999_999.0,
            strict_decode=True,
        ) as client,
        pytest.raises(MarketDataDecodeError) as exc,
    ):
        client.get_latest(symbol="AAA1")

    assert exc.value.field_path == ".entries"
    assert exc.value.observed_type == "str"
