"""Async query endpoint tests for ``matriz_client.aio`` (Phase 10 Plan 10-02 Task 2).

Mirror of sync ``test_client.py`` happy-paths for the 20 query endpoints across
§4 Segments, §5 Instruments, §6 Orders (read-only), §8 Market Data, §9 Risk API.

Each test issues one happy-path mock and verifies (a) the endpoint URL hits the
correct path and (b) the parsed model is non-empty / well-typed.
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from matriz_client import aio
from matriz_client.exceptions import PrimaryAPIError
from matriz_client.models import (
    AccountReport,
    DetailedPosition,
    Instrument,
    InstrumentDetail,
    MarketDataSnapshot,
    Order,
    Position,
    Segment,
    Trade,
)

# ---------------------------------------------------------------------------
# §4 Segments
# ---------------------------------------------------------------------------


async def test_async_get_segments(httpx_mock: HTTPXMock) -> None:
    """AQ1: get_segments parses {segments: [...]} envelope into list[Segment]."""
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        method="GET",
        json={"status": "OK", "segments": [{"marketSegmentId": "DDA", "marketId": "ROFX"}]},
    )
    segments = await aio.get_segments()
    assert isinstance(segments, list)
    assert len(segments) == 1
    assert isinstance(segments[0], Segment)
    assert segments[0].marketSegmentId == "DDA"


# ---------------------------------------------------------------------------
# §5 Instruments
# ---------------------------------------------------------------------------


async def test_async_get_all_instruments(httpx_mock: HTTPXMock) -> None:
    """AQ2: get_all_instruments parses {instruments: [...]}."""
    httpx_mock.add_response(
        url="https://api.test/rest/instruments/all",
        method="GET",
        json={
            "status": "OK",
            "instruments": [
                {"instrumentId": {"symbol": "DLR/MAR26", "marketId": "ROFX"}, "cficode": "FXXXSX"}
            ],
        },
    )
    instruments = await aio.get_all_instruments()
    assert isinstance(instruments, list)
    assert len(instruments) == 1
    assert isinstance(instruments[0], Instrument)


async def test_async_get_instruments_details(httpx_mock: HTTPXMock) -> None:
    """AQ3: get_instruments_details parses {instruments: [...]} → list[InstrumentDetail]."""
    httpx_mock.add_response(
        url="https://api.test/rest/instruments/details",
        method="GET",
        json={
            "status": "OK",
            "instruments": [
                {
                    "instrumentId": {"symbol": "DLR/MAR26", "marketId": "ROFX"},
                    "cficode": "FXXXSX",
                    "currency": "ARS",
                }
            ],
        },
    )
    details = await aio.get_instruments_details()
    assert isinstance(details, list)
    assert len(details) == 1
    assert isinstance(details[0], InstrumentDetail)


async def test_async_get_instrument_detail(httpx_mock: HTTPXMock) -> None:
    """AQ4: get_instrument_detail parses {instrument: {...}} → InstrumentDetail."""
    httpx_mock.add_response(
        url="https://api.test/rest/instruments/detail?symbol=DLR/MAR26&marketId=ROFX",
        method="GET",
        json={
            "status": "OK",
            "instrument": {
                "instrumentId": {"symbol": "DLR/MAR26", "marketId": "ROFX"},
                "currency": "ARS",
            },
        },
    )
    detail = await aio.get_instrument_detail("DLR/MAR26", "ROFX")
    assert isinstance(detail, InstrumentDetail)


async def test_async_get_instruments_by_cfi(httpx_mock: HTTPXMock) -> None:
    """AQ5: get_instruments_by_cfi parses {instruments: [...]}."""
    httpx_mock.add_response(
        url="https://api.test/rest/instruments/byCFICode?CFICode=FXXXSX",
        method="GET",
        json={
            "status": "OK",
            "instruments": [
                {"instrumentId": {"symbol": "DLR/MAR26", "marketId": "ROFX"}, "cficode": "FXXXSX"}
            ],
        },
    )
    instruments = await aio.get_instruments_by_cfi("FXXXSX")
    assert isinstance(instruments, list)
    assert len(instruments) == 1


async def test_async_get_instruments_by_cfi_rejects_invalid_cfi() -> None:
    """AQ5b: get_instruments_by_cfi guard rejects bad CFI pre-HTTP (Phase 9 BUG-01 mirror)."""
    with pytest.raises(PrimaryAPIError) as exc:
        await aio.get_instruments_by_cfi("NOT-A-CFI")  # type: ignore[arg-type]
    assert exc.value.status == "ERROR"


async def test_async_get_instruments_by_segment(httpx_mock: HTTPXMock) -> None:
    """AQ6: get_instruments_by_segment parses {instruments: [...]}."""
    httpx_mock.add_response(
        url="https://api.test/rest/instruments/bySegment?MarketSegmentID=DDA&MarketID=ROFX",
        method="GET",
        json={
            "status": "OK",
            "instruments": [
                {"instrumentId": {"symbol": "GGAL/CI", "marketId": "ROFX"}, "cficode": "ESXXXX"}
            ],
        },
    )
    instruments = await aio.get_instruments_by_segment("DDA", "ROFX")
    assert isinstance(instruments, list)
    assert len(instruments) == 1


# ---------------------------------------------------------------------------
# §6 Orders (read-only)
# ---------------------------------------------------------------------------


async def test_async_get_order_status(httpx_mock: HTTPXMock) -> None:
    """AQ7: get_order_status parses {order: {...}} → Order."""
    httpx_mock.add_response(
        url="https://api.test/rest/order/id?clOrdId=cl-1&proprietary=PBCP",
        method="GET",
        json={"status": "OK", "order": {"clOrdId": "cl-1", "proprietary": "PBCP", "status": "NEW"}},
    )
    order = await aio.get_order_status("cl-1", "PBCP")
    assert isinstance(order, Order)
    assert order.clOrdId == "cl-1"


async def test_async_get_order_history(httpx_mock: HTTPXMock) -> None:
    """AQ8: get_order_history parses {orders: [...]}."""
    httpx_mock.add_response(
        url="https://api.test/rest/order/allById?clOrdId=cl-1&proprietary=PBCP",
        method="GET",
        json={
            "status": "OK",
            "orders": [
                {"clOrdId": "cl-1", "proprietary": "PBCP", "status": "NEW"},
                {"clOrdId": "cl-1", "proprietary": "PBCP", "status": "FILLED"},
            ],
        },
    )
    history = await aio.get_order_history("cl-1", "PBCP")
    assert isinstance(history, list)
    assert len(history) == 2


async def test_async_get_active_orders(httpx_mock: HTTPXMock) -> None:
    """AQ9: get_active_orders parses {orders: [...]} for account."""
    httpx_mock.add_response(
        url="https://api.test/rest/order/actives?accountId=ACC-9",
        method="GET",
        json={"status": "OK", "orders": [{"clOrdId": "cl-a", "accountId": "ACC-9"}]},
    )
    actives = await aio.get_active_orders("ACC-9")
    assert isinstance(actives, list)
    assert len(actives) == 1


async def test_async_get_filled_orders(httpx_mock: HTTPXMock) -> None:
    """AQ10: get_filled_orders parses {orders: [...]} for account."""
    httpx_mock.add_response(
        url="https://api.test/rest/order/filleds?accountId=ACC-10",
        method="GET",
        json={"status": "OK", "orders": [{"clOrdId": "cl-f", "status": "FILLED"}]},
    )
    filleds = await aio.get_filled_orders("ACC-10")
    assert isinstance(filleds, list)
    assert len(filleds) == 1


async def test_async_get_all_orders(httpx_mock: HTTPXMock) -> None:
    """AQ11: get_all_orders parses {orders: [...]} for account."""
    httpx_mock.add_response(
        url="https://api.test/rest/order/all?accountId=ACC-11",
        method="GET",
        json={"status": "OK", "orders": []},
    )
    allord = await aio.get_all_orders("ACC-11")
    assert allord == []


async def test_async_get_order_by_exec_id(httpx_mock: HTTPXMock) -> None:
    """AQ12: get_order_by_exec_id parses {order: {...}} → Order."""
    httpx_mock.add_response(
        url="https://api.test/rest/order/byExecId?execId=exec-12",
        method="GET",
        json={"status": "OK", "order": {"execId": "exec-12", "status": "FILLED"}},
    )
    order = await aio.get_order_by_exec_id("exec-12")
    assert isinstance(order, Order)
    assert order.execId == "exec-12"


# ---------------------------------------------------------------------------
# §7 Market Data
# ---------------------------------------------------------------------------


async def test_async_get_market_data(httpx_mock: HTTPXMock) -> None:
    """AQ13: get_market_data parses {marketData: {...}} → MarketDataSnapshot."""
    httpx_mock.add_response(
        url="https://api.test/rest/marketdata/get?marketId=ROFX&symbol=DLR/MAR26&entries=BI,OF,LA,OP,CL,SE,OI",
        method="GET",
        json={
            "status": "OK",
            "marketData": {
                "BI": [{"price": 1000.0, "size": 100}],
                "OF": [{"price": 1001.0, "size": 50}],
                "LA": {"price": 1000.5, "size": 10, "date": 1718294400000},
            },
        },
    )
    snap = await aio.get_market_data("DLR/MAR26")
    assert isinstance(snap, MarketDataSnapshot)
    assert snap.BI[0].price == 1000.0
    assert snap.LA.price == 1000.5


async def test_async_get_trades(httpx_mock: HTTPXMock) -> None:
    """AQ14: get_trades parses {trades: [...]}."""
    httpx_mock.add_response(
        url="https://api.test/rest/data/getTrades?marketId=ROFX&symbol=DLR/MAR26&date=2026-06-13",
        method="GET",
        json={
            "status": "OK",
            "trades": [{"symbol": "DLR/MAR26", "size": 5, "price": 1000.0}],
        },
    )
    trades = await aio.get_trades("DLR/MAR26", date="2026-06-13")
    assert isinstance(trades, list)
    assert len(trades) == 1
    assert isinstance(trades[0], Trade)


# ---------------------------------------------------------------------------
# §9 Risk API (HTTP Basic Auth path)
# ---------------------------------------------------------------------------


async def test_async_get_positions(httpx_mock: HTTPXMock) -> None:
    """AQ15: get_positions (BasicAuth path) parses {positions: [...]}."""
    httpx_mock.add_response(
        url="https://api.test/rest/risk/position/getPositions/ACC-1",
        method="GET",
        json={
            "status": "OK",
            "positions": [{"symbol": "DLR/MAR26", "buySize": 1.0, "buyPrice": 1000.0}],
        },
    )
    positions = await aio.get_positions("ACC-1")
    assert isinstance(positions, list)
    assert len(positions) == 1
    assert isinstance(positions[0], Position)


async def test_async_get_detailed_positions(httpx_mock: HTTPXMock) -> None:
    """AQ16: get_detailed_positions (BasicAuth) parses raw payload → DetailedPosition."""
    httpx_mock.add_response(
        url="https://api.test/rest/risk/detailedPosition/ACC-2",
        method="GET",
        json={"status": "OK", "account": "ACC-2", "totalMarketValue": 1234.5, "report": {}},
    )
    dp = await aio.get_detailed_positions("ACC-2")
    assert isinstance(dp, DetailedPosition)
    assert dp.account == "ACC-2"


async def test_async_get_account_report(httpx_mock: HTTPXMock) -> None:
    """AQ17: get_account_report (BasicAuth) parses raw payload → AccountReport."""
    httpx_mock.add_response(
        url="https://api.test/rest/risk/accountReport/ACC-3",
        method="GET",
        json={
            "status": "OK",
            "accountName": "ACC-3",
            "marketMember": "MM",
            "collateral": 100.0,
            "currentCash": 50.0,
        },
    )
    rep = await aio.get_account_report("ACC-3")
    assert isinstance(rep, AccountReport)
    assert rep.accountName == "ACC-3"


# ---------------------------------------------------------------------------
# Error propagation (Phase 7 D-24 mirror — 200-OK status=ERROR raises)
# ---------------------------------------------------------------------------


async def test_async_status_error_envelope_raises_primary_api_error(httpx_mock: HTTPXMock) -> None:
    """Phase 7 D-24 mirror: 200-OK with status=ERROR raises PrimaryAPIError, not retried."""
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        method="GET",
        json={"status": "ERROR", "description": "bad segments", "message": "fail"},
    )
    with pytest.raises(PrimaryAPIError) as exc:
        await aio.get_segments()
    assert exc.value.status == "ERROR"
