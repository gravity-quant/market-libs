"""Tests for the safe-access models in :mod:`matriz_client.models`.

The contract: ``Model.from_api(payload)`` parses any dict (full, partial,
or empty) without raising; missing keys collapse to safe defaults
(``[]``, empty model, ``None``, ``{}``) so attribute access on the
result never raises ``KeyError`` or ``AttributeError``.
"""

from __future__ import annotations

import dataclasses
from dataclasses import FrozenInstanceError
from typing import get_origin, get_type_hints

import pytest

import matriz_client
from matriz_client import models
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
    # Still ``{}`` after the Phase 37 retype: the empty-mapping default survives
    # ``dict[str, Any]`` -> ``dict[str, TickPriceRange]`` untouched.
    assert detail.tickPriceRanges == {}


# ----------------------------------------------------------------------
# tickPriceRanges — the one field in Phase 37 with live-capture provenance
# ----------------------------------------------------------------------
#
# PROVENANCE (D-04c, class `baseline`). The payload below is shaped from the
# committed live capture
# `.planning/verification/schemas/matriz-client/get-instrument-detail.json`,
# captured 2026-06-10T01:01:55Z against `https://api.remarkets.primary.com.ar`
# (symbol `SOJ.ROS/NOV26 308 P`). That file records TYPES, and for
# `tickPriceRanges` it records exactly one key `"0"` carrying
# `{"lowerLimit": "int", "tick": "float", "upperLimit": "NoneType"}`.
# The concrete VALUES are the vendor-documented samples at
# `packages/matriz-client/documentation/Primary-API.md:330,378,454`, which agree
# with the capture on all three field names, on the single `"0"` key, and on the
# three runtime types. The vendor doc is corroboration only — it is never
# presented as a capture (D-04a).


def test_instrument_detail_tickPriceRanges_decodes_the_committed_baseline() -> None:
    """D-05: the mapping values arrive as models, not raw dicts."""
    detail = InstrumentDetail.from_api(
        {
            "securityDescription": "TRI.ROS/DIC23 352 C",
            "tickPriceRanges": {"0": {"lowerLimit": 0, "upperLimit": None, "tick": 0.1}},
        }
    )

    assert list(detail.tickPriceRanges) == ["0"]
    entry = detail.tickPriceRanges["0"]
    assert not isinstance(entry, dict)
    # The capture records ``int`` on the wire; the walker's ``float`` arm widens
    # BEFORE consulting ``scalar_passthrough``, so this is silent and correct.
    assert entry.lowerLimit == 0.0
    assert isinstance(entry.lowerLimit, float)
    assert entry.tick == 0.1
    assert entry.upperLimit is None


def test_tickPriceRanges_values_are_TickPriceRange_null_objects() -> None:
    """NOBJ-01 / T-37-06: an attribute chain over the mapping never raises."""
    tick_price_range = matriz_client.TickPriceRange

    assert bool(tick_price_range.empty()) is False
    assert tick_price_range.empty().tick is None
    assert bool(tick_price_range.from_api({"tick": 0.05})) is True
    # The chain a caller actually writes, on a payload that carried nothing.
    assert (
        InstrumentDetail.from_api({}).tickPriceRanges.get("0", tick_price_range.empty()).tick
        is None
    )


def test_TickPriceRange_is_on_the_exported_surface() -> None:
    """Plan 37-04's field gate resolves candidates from ``__all__``."""
    assert "TickPriceRange" in matriz_client.__all__
    assert matriz_client.TickPriceRange is models.TickPriceRange


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
    # Still ``{}`` after Phase 37's retype to ``dict[str, dict[str, InstrumentPositionReport]]``:
    # the default factory is unchanged, so this assertion did NOT flip.
    assert parsed.report == {}


def test_InstrumentPositionReport_is_on_the_exported_surface() -> None:
    assert "InstrumentPositionReport" in matriz_client.__all__
    assert matriz_client.InstrumentPositionReport is models.InstrumentPositionReport


def test_InstrumentPositionReport_declares_only_the_vendor_documented_scalars() -> None:
    """D-07's MINIMAL disposition, stated executably.

    The roster is exactly the three sibling scalars of
    ``Primary-API.md:1745-1747``. The deferred ``detailedPositions`` array and
    its ``detailedDailyDiff`` object are NOT modelled — shipping them would
    present an unobserved model as observed (SC-1).
    """
    names = [f.name for f in dataclasses.fields(models.InstrumentPositionReport)]
    assert names == [
        "instrumentInitialSize",
        "instrumentFilledSize",
        "instrumentCurrentSize",
    ]
    hints = get_type_hints(models.InstrumentPositionReport)
    assert all(hints[n] == (float | None) for n in names)
    # F-11: this class sits at depth 2, and
    # ``test_no_mapping_carrying_model_is_ever_a_nested_field_type`` used to walk
    # exactly ONE level of ``__args__``, so a mapping field here was invisible to
    # it and this per-class assertion was the actual guard. The Phase 37 code
    # review (WR-08) made that walk depth-agnostic, so the general guard now
    # covers this class by construction rather than by name. Kept anyway: it is
    # cheap, it states the constraint where the class is defined, and deleting a
    # correct assertion to celebrate a better one elsewhere is how coverage
    # quietly shrinks.
    assert [n for n, t in hints.items() if get_origin(t) is dict] == []


def test_InstrumentPositionReport_empty_is_falsy_and_chain_safe() -> None:
    empty = models.InstrumentPositionReport.empty()
    assert not empty
    assert empty.instrumentCurrentSize is None
    assert models.InstrumentPositionReport.from_api({"instrumentFilledSize": 3})


def test_account_report_accepts_partial_payload() -> None:
    parsed = AccountReport.from_api(
        {"accountName": "REM6771", "collateral": 1000.0, "margin": 250.0}
    )
    assert parsed.accountName == "REM6771"
    # Phase 37 D-02: ``portfolio`` is a ``float | None`` scalar leaf now, not a
    # mapping. An absent scalar answers ``None``; this assertion FLIPPED.
    assert parsed.portfolio is None
    # Unchanged: still a mapping, so an absent one is still ``{}``.
    assert parsed.detailedAccountReports == {}


def test_DetailedAccountReport_is_on_the_exported_surface() -> None:
    assert "DetailedAccountReport" in matriz_client.__all__
    assert matriz_client.DetailedAccountReport is models.DetailedAccountReport


def test_DetailedAccountReport_declares_only_the_vendor_documented_scalar() -> None:
    """D-07's MINIMAL disposition for the one-level container.

    The roster is the single scalar of ``Primary-API.md:1888``. The two nested
    open-keyed objects the same sample shows (``currencyBalance`` at
    ``:1828-1859`` and ``availableToOperate`` at ``:1860-1887``) are DEFERRED —
    modelling them would present an unobserved tree as observed (SC-1).
    """
    names = [f.name for f in dataclasses.fields(models.DetailedAccountReport)]
    assert names == ["settlementDate"]
    hints = get_type_hints(models.DetailedAccountReport)
    assert hints["settlementDate"] == (int | None)
    # F-11, same constraint as InstrumentPositionReport: mapping-free. Also
    # subsumed by the now depth-agnostic general guard (WR-08), and kept for the
    # same reason.
    assert [n for n, t in hints.items() if get_origin(t) is dict] == []


def test_DetailedAccountReport_empty_is_falsy_and_chain_safe() -> None:
    empty = models.DetailedAccountReport.empty()
    assert not empty
    assert empty.settlementDate is None
    assert models.DetailedAccountReport.from_api({"settlementDate": 1})


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
