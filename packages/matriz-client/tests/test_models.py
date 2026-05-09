"""Tests for the safe-access models in :mod:`matriz_client.models`.

The contract: ``Model.from_api(payload)`` parses any dict (full, partial,
or empty) without raising; missing keys collapse to safe defaults
(``[]``, empty model, ``None``, ``{}``) so attribute access on the
result never raises ``KeyError`` or ``AttributeError``.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from matriz_client.models import (
    AccountReport,
    DetailedPosition,
    Instrument,
    InstrumentDetail,
    InstrumentId,
    MarketDataEntryValue,
    MarketDataLevel,
    MarketDataSnapshot,
    NewOrderResponse,
    Order,
    OrderReport,
    Position,
    Segment,
    Trade,
)

# ----------------------------------------------------------------------
# Basic identifiers
# ----------------------------------------------------------------------


def test_instrument_id_round_trip() -> None:
    parsed = InstrumentId.from_api({"marketId": "ROFX", "symbol": "DLR/DIC23"})
    assert parsed.marketId == "ROFX"
    assert parsed.symbol == "DLR/DIC23"


def test_segment_round_trip() -> None:
    parsed = Segment.from_api({"marketSegmentId": "DDF", "marketId": "ROFX"})
    assert parsed.marketSegmentId == "DDF"
    assert parsed.marketId == "ROFX"


def test_instrument_round_trip() -> None:
    parsed = Instrument.from_api(
        {
            "instrumentId": {"marketId": "ROFX", "symbol": "DLR/DIC23"},
            "cficode": "FXXXSX",
        }
    )
    assert parsed.instrumentId.symbol == "DLR/DIC23"
    assert parsed.cficode == "FXXXSX"


def test_instrument_detail_accepts_partial_payload() -> None:
    detail = InstrumentDetail.from_api({})
    assert detail.instrumentId == InstrumentId.empty()
    assert detail.currency is None
    assert detail.orderTypes == []
    assert detail.tickPriceRanges == {}


# ----------------------------------------------------------------------
# Orders
# ----------------------------------------------------------------------


def test_new_order_response_round_trip() -> None:
    parsed = NewOrderResponse.from_api({"clientId": "1-1234", "proprietary": "PBCP"})
    assert parsed.clientId == "1-1234"
    assert parsed.proprietary == "PBCP"


ORDER_PAYLOAD = {
    "orderId": "218681",
    "clOrdId": "1-1234",
    "proprietary": "PBCP",
    "execId": "1669995044232",
    "accountId": "REM6771",
    "instrumentId": {"marketId": "ROFX", "symbol": "DLR/DIC23"},
    "price": 210.5,
    "orderQty": 10,
    "ordType": "LIMIT",
    "side": "BUY",
    "timeInForce": "DAY",
    "transactTime": "20230101-18:19:15.123-0300",
    "avgPx": 0.0,
    "lastPx": 0.0,
    "lastQty": 0,
    "cumQty": 0,
    "leavesQty": 10,
    "status": "NEW",
    "text": "",
}


def test_order_round_trip() -> None:
    parsed = Order.from_api(ORDER_PAYLOAD)
    assert parsed.orderId == "218681"
    assert parsed.side == "BUY"
    assert parsed.instrumentId.symbol == "DLR/DIC23"


def test_order_accepts_null_order_id() -> None:
    payload = {**ORDER_PAYLOAD, "orderId": None, "status": "PENDING_NEW"}
    parsed = Order.from_api(payload)
    assert parsed.orderId is None


def test_order_partial_payload_uses_safe_defaults() -> None:
    parsed = Order.from_api({"clOrdId": "only"})
    assert parsed.clOrdId == "only"
    assert parsed.orderId is None
    assert parsed.price is None
    assert parsed.instrumentId == InstrumentId.empty()
    assert parsed.instrumentId.symbol is None


def test_order_report_superset_of_order() -> None:
    report = OrderReport.from_api({**ORDER_PAYLOAD, "wsClOrdId": "ws-abc"})
    assert report.wsClOrdId == "ws-abc"
    assert report.orderId == "218681"


# ----------------------------------------------------------------------
# Market data
# ----------------------------------------------------------------------


def test_market_data_level_round_trip() -> None:
    parsed = MarketDataLevel.from_api({"price": 179.8, "size": 1000})
    assert parsed.price == 179.8
    assert parsed.size == 1000


def test_market_data_entry_value_allows_nulls() -> None:
    parsed = MarketDataEntryValue.from_api({"price": None, "size": 217596, "date": 1664150400000})
    assert parsed.price is None
    assert parsed.size == 217596


def test_market_data_snapshot_from_spec_example() -> None:
    payload = {
        "SE": {"price": 180.3, "size": None, "date": 1669852800000},
        "LA": {"price": 179.85, "size": 4, "date": 1669995044232},
        "OI": {"price": None, "size": 217596, "date": 1664150400000},
        "OF": [
            {"price": 179.8, "size": 1000},
            {"price": 180.35, "size": 1000},
        ],
        "OP": 180.35,
        "CL": {"price": 180.35, "size": None, "date": 1669852800000},
        "BI": [
            {"price": 179.75, "size": 275},
            {"price": 178.95, "size": 514},
        ],
    }
    parsed = MarketDataSnapshot.from_api(payload)
    assert parsed.OP == 180.35
    assert parsed.BI[0].price == 179.75
    assert parsed.SE.size is None
    assert parsed.SE.price == 180.3
    assert parsed.CL.price == 180.35
    assert parsed.CL.date == 1669852800000


def test_market_data_snapshot_close_is_entry_value_not_scalar() -> None:
    """Regression: CL viene como objeto {price, size, date}, no como float (issue #102)."""
    parsed = MarketDataSnapshot.from_api(
        {"CL": {"price": 20090.0, "size": None, "date": 1777420800000}}
    )
    assert isinstance(parsed.CL, MarketDataEntryValue)
    assert parsed.CL.price == 20090.0
    assert parsed.CL.size is None
    assert parsed.CL.date == 1777420800000


def test_market_data_snapshot_close_missing_returns_empty_entry() -> None:
    """Safe-access: si CL no viene, devuelve un MarketDataEntryValue vacío, no None."""
    parsed = MarketDataSnapshot.from_api({"OP": 180.0})
    assert isinstance(parsed.CL, MarketDataEntryValue)
    assert parsed.CL.price is None
    assert parsed.CL.size is None
    assert parsed.CL.date is None


def test_market_data_snapshot_accepts_empty_payload() -> None:
    parsed = MarketDataSnapshot.from_api({})
    assert parsed.BI == []
    assert parsed.OF == []
    assert parsed.OP is None
    # Nested-model fields default to an empty instance, never None.
    assert MarketDataEntryValue.empty() == parsed.SE
    assert parsed.SE.price is None


def test_market_data_snapshot_safe_chained_access_on_missing_keys() -> None:
    """The headline guarantee: chained access never raises on missing keys."""
    parsed = MarketDataSnapshot.from_api({"OP": 180.0})
    assert parsed.OP == 180.0
    # Missing BI iterates as an empty list, not None.
    assert list(parsed.BI) == []
    # Missing SE returns an empty MarketDataEntryValue; .price is None.
    assert parsed.SE.price is None
    assert parsed.LA.size is None


# ----------------------------------------------------------------------
# Trades, Risk
# ----------------------------------------------------------------------


def test_trade_round_trip() -> None:
    parsed = Trade.from_api(
        {
            "symbol": "DLR/DIC23",
            "servertime": 1669995044232,
            "size": 4,
            "price": 179.85,
            "datetime": "2022-12-02T18:20:44.232-03:00",
        }
    )
    assert parsed.price == 179.85


def test_position_round_trip() -> None:
    parsed = Position.from_api(
        {
            "symbol": "DLR/DIC23",
            "buySize": 10.0,
            "buyPrice": 210.5,
            "sellSize": 0.0,
            "sellPrice": 0.0,
            "totalDailyDiff": 0.0,
            "totalDiff": 0.0,
            "tradingSymbol": "DLR/DIC23",
        }
    )
    assert parsed.symbol == "DLR/DIC23"


def test_detailed_position_accepts_partial_payload() -> None:
    parsed = DetailedPosition.from_api({"account": "REM6771"})
    assert parsed.account == "REM6771"
    assert parsed.report == {}


def test_account_report_accepts_partial_payload() -> None:
    parsed = AccountReport.from_api(
        {"accountName": "REM6771", "collateral": 1000.0, "margin": 250.0}
    )
    assert parsed.accountName == "REM6771"
    assert parsed.portfolio == {}
    assert parsed.detailedAccountReports == {}


# ----------------------------------------------------------------------
# Constructor edge cases
# ----------------------------------------------------------------------


def test_from_api_with_none_returns_empty() -> None:
    assert MarketDataSnapshot.from_api(None) == MarketDataSnapshot.empty()
    assert Order.from_api(None) == Order.empty()


def test_from_api_with_non_dict_returns_empty() -> None:
    # Defensive: if the API ever returns something unexpected, the model
    # still constructs cleanly instead of raising.
    assert NewOrderResponse.from_api("garbage") == NewOrderResponse.empty()
    assert NewOrderResponse.from_api(123) == NewOrderResponse.empty()


def test_empty_classmethod_produces_default_instance() -> None:
    snapshot = MarketDataSnapshot.empty()
    assert snapshot.BI == []
    assert snapshot.OP is None
    assert snapshot.SE.price is None


# ----------------------------------------------------------------------
# Config behavior
# ----------------------------------------------------------------------


def test_extra_fields_are_ignored() -> None:
    parsed = NewOrderResponse.from_api(
        {"clientId": "1-1234", "proprietary": "PBCP", "newField": "future"}
    )
    assert parsed.clientId == "1-1234"
    assert not hasattr(parsed, "newField")


def test_models_are_frozen() -> None:
    parsed = NewOrderResponse.from_api({"clientId": "1-1234", "proprietary": "PBCP"})
    with pytest.raises(FrozenInstanceError):
        parsed.clientId = "mutated"  # type: ignore[misc]
