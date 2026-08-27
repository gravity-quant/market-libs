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
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import MarketDataDecodeError, aio

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
    """``None`` survives as ``None`` — no ``0.0``, no ``[]``, no ``{}``."""
    httpx_mock.add_response(method="GET", json=[_NO_DATA_ROW])

    rows = market_data_client.client._get_default().get_latest(symbol="AAA1")

    assert len(rows) == 1
    row = rows[0]
    assert row.entries is None
    assert row.market_data is None
    assert row.staleness_seconds is None
    # The fields that DO arrive are untouched.
    assert row.symbol == "AAA1"
    assert row.market_id == "ZZZ"
    assert row.note == "sin datos para el simbolo"


async def test_no_data_row_keeps_its_nulls_async(httpx_mock: HTTPXMock) -> None:
    """Async twin of :func:`test_no_data_row_keeps_its_nulls` (C-3)."""
    httpx_mock.add_response(method="GET", json=[_NO_DATA_ROW])

    rows = await aio._get_default().get_latest(symbol="AAA1")

    assert len(rows) == 1
    row = rows[0]
    assert row.entries is None
    assert row.market_data is None
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

    assert rows[0].entries is None


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

    assert rows[0].entries is None


def test_populated_row_still_decodes(httpx_mock: HTTPXMock) -> None:
    """Non-regression: widening must not weaken the populated path."""
    httpx_mock.add_response(method="GET", json={"count": 1, "items": [_POPULATED_ROW]})

    rows = market_data_client.client._get_default().get_market_data()

    assert len(rows) == 1
    assert rows[0].entries == ["BI", "OF"]
    assert rows[0].market_data == {"BI": [{"price": 10, "size": 1}]}
    assert rows[0].staleness_seconds == 1.5


def test_a_wrong_typed_value_is_still_a_divergence(httpx_mock: HTTPXMock) -> None:
    """The widening admits ``None`` ONLY — a wrong type stays fatal in strict mode.

    Widening to ``| None`` must not become a blanket amnesty. ``entries`` arriving
    as a ``str`` is still a real divergence and must still raise, otherwise the
    fix would have traded one silent substitution for another.
    """
    httpx_mock.add_response(
        method="GET", json=[{**_NO_DATA_ROW, "entries": "not-a-list"}]
    )

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
