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
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import BookLevel, MarketDataDecodeError, aio

# ``GET /marketdata/latest`` for a symbol the feed never delivered — the exact
# shape of the committed get-latest.json baseline. Identifiers synthesised.
_NO_DATA_ROW: dict[str, Any] = {
    "symbol": "AAA1",
    "market_id": "ZZZ",
    "active": False,
    "entries": None,
    "market_data": None,
    "staleness_seconds": None,
    "note": "sin datos para el simbolo",
}

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
    assert row.market_id == "ZZZ"
    assert row.note == "sin datos para el simbolo"


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
    assert row.market_id == "ZZZ"
    assert row.note == "sin datos para el simbolo"


def test_no_data_row_is_not_fatal_under_strict_decode(httpx_mock: HTTPXMock) -> None:
    """The strict raise stops firing — the row is a legitimate shape, not a defect.

    This is the assertion with teeth: before the widening, this exact body raised
    ``MarketDataDecodeError`` in strict mode, which is why the 33-05 strict pass
    reported ``FINDING SHAPE`` on ``market_data_*`` and ``latest_*``.
    """
    httpx_mock.add_response(method="GET", json=[_NO_DATA_ROW])

    with market_data_client.Client(
        base_url="https://market-data-develop.test/api",
        token="test-token",
        token_expires_at=9_999_999_999.0,
        strict_decode=True,
    ) as client:
        rows = client.get_latest(symbol="AAA1")

    assert rows[0].entries == []


async def test_no_data_row_is_not_fatal_under_strict_decode_async(httpx_mock: HTTPXMock) -> None:
    """Async twin of :func:`test_no_data_row_is_not_fatal_under_strict_decode` (C-3)."""
    httpx_mock.add_response(method="GET", json=[_NO_DATA_ROW])

    async with aio.AsyncClient(
        base_url="https://market-data-develop.test/api",
        token="test-token",
        token_expires_at=9_999_999_999.0,
        strict_decode=True,
    ) as client:
        rows = await client.get_latest(symbol="AAA1")

    assert rows[0].entries == []


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
    """
    httpx_mock.add_response(method="GET", json=[{**_NO_DATA_ROW, "entries": "not-a-list"}])

    with (
        market_data_client.Client(
            base_url="https://market-data-develop.test/api",
            token="test-token",
            token_expires_at=9_999_999_999.0,
            strict_decode=True,
        ) as client,
        pytest.raises(MarketDataDecodeError),
    ):
        client.get_latest(symbol="AAA1")
