"""Tests for the tolerant ``market_data_client.models`` layer (Plan 21-01).

Pins the D-01/D-04/D-05 behaviors:

- ``MarketDataSnapshot.from_api`` tolerates ``{}`` / ``None`` / extra-key payloads
  without raising, substituting typed zero-defaults and ``entries == []``.
- ``received_at`` is a CLIENT-STAMPED field injected as a keyword; it must NOT be
  coerced from the payload — a decoy ``"received_at"`` payload key is ignored and
  the injected kwarg wins (D-01, the highest-risk fidelity point of the phase).
- ``entries`` deserializes as a tolerant ``list[str]`` of entry-type codes matching
  the real develop wire (LIVE-MD-01); the reconciled ``market_id``/``active``/
  ``market_data``/``staleness_seconds``/``note`` fields parse both the ``/marketdata``
  item shape and the ``/marketdata/latest`` no-data shape without raising.
- ``LatestRequest(...).to_dict()`` drops ``None``-valued optionals and keeps
  supplied values (D-05).
"""

from __future__ import annotations

import dataclasses

import pytest

from market_data_client.models import (
    HolidayIn,
    LatestRequest,
    MarketDataSnapshot,
    MarketHoursIn,
    NewSymbol,
    NewSymbols,
    SafeModel,
    SymbolPatch,
)


def test_from_api_empty_dict_typed_zero_defaults() -> None:
    snap = MarketDataSnapshot.from_api({})
    assert snap.symbol == ""
    assert snap.market_id == ""
    assert snap.entries == []
    assert snap.active is False
    assert snap.note is None


def test_from_api_none_does_not_raise() -> None:
    snap = MarketDataSnapshot.from_api(None)
    assert snap.entries == []
    assert snap.received_at == 0.0


def test_from_api_extra_keys_ignored() -> None:
    snap = MarketDataSnapshot.from_api(
        {"symbol": "GGAL", "unknown_key": 123, "another": {"nested": True}}
    )
    assert snap.symbol == "GGAL"
    assert snap.entries == []


def test_received_at_injected_wins_over_decoy_payload_key() -> None:
    # D-01: the client-supplied stamp is injected as a kwarg and MUST bypass
    # _coerce; a decoy "received_at" in the payload is ignored entirely.
    snap = MarketDataSnapshot.from_api({"symbol": "GGAL", "received_at": 999.0}, received_at=1234.5)
    assert snap.received_at == 1234.5
    assert snap.received_at != 999.0
    assert snap.received_at != 0.0


def test_received_at_defaults_to_zero_without_kwarg() -> None:
    # The parser (Plan 02) always supplies received_at; absent the kwarg the
    # field defaults to 0.0 rather than pulling a payload value.
    snap = MarketDataSnapshot.from_api({"symbol": "GGAL", "received_at": 999.0})
    assert snap.received_at == 0.0


def test_entries_wrong_type_tolerated_as_empty_list() -> None:
    # entries is now a plain list[str] of entry-type codes — a non-list wire value
    # collapses to [] (SafeModel tolerance), never a raise.
    snap = MarketDataSnapshot.from_api({"entries": "not-a-list"}, received_at=1.0)
    assert snap.entries == []


def test_from_api_marketdata_item_parses_new_fields() -> None:
    # Mirrors get-market-data.json items[0]: the reconciled wire shape parses in
    # full, market_data passes through untouched, and the decoy received_at loses.
    snap = MarketDataSnapshot.from_api(
        {
            "symbol": "GGAL",
            "market_id": "BCBA",
            "active": True,
            "entries": ["BI", "OF"],
            "market_data": {
                "BI": [{"price": 1, "size": 2}],
                "CL": {"date": 1, "price": 3},
                "HI": 4,
                "OI": None,
            },
            "staleness_seconds": 1.5,
            "received_at": "ignored",
        },
        received_at=42.0,
    )
    assert snap.symbol == "GGAL"
    assert snap.market_id == "BCBA"
    assert snap.active is True
    assert snap.entries == ["BI", "OF"]
    # market_data is a dict passthrough — nested rows are preserved verbatim.
    assert snap.market_data["BI"][0]["price"] == 1
    assert snap.market_data["OI"] is None
    assert snap.staleness_seconds == 1.5
    assert snap.received_at == 42.0
    assert snap.note is None


def test_from_api_latest_nodata_item() -> None:
    # Mirrors get-latest.json: a /marketdata/latest no-data row collapses the null
    # fields tolerantly while note carries the message and received_at stays injected.
    snap = MarketDataSnapshot.from_api(
        {
            "symbol": "GGAL",
            "note": "no data",
            "active": None,
            "market_data": None,
            "market_id": None,
            "received_at": None,
            "staleness_seconds": None,
        },
        received_at=7.0,
    )
    assert snap.symbol == "GGAL"
    assert snap.note == "no data"
    assert snap.active is False
    assert snap.market_data is None
    assert snap.market_id == ""
    assert snap.entries == []
    assert snap.staleness_seconds == 0.0
    assert snap.received_at == 7.0


def test_latest_request_to_dict_drops_none_optionals() -> None:
    req = LatestRequest(symbols=["GGAL", "YPFD"])
    assert req.to_dict() == {"symbols": ["GGAL", "YPFD"]}


def test_latest_request_to_dict_keeps_supplied_optionals() -> None:
    req = LatestRequest(symbols=["GGAL"], marketId="BCBA", entries=["BID", "OFFER"])
    assert req.to_dict() == {
        "symbols": ["GGAL"],
        "marketId": "BCBA",
        "entries": ["BID", "OFFER"],
    }


# ----------------------------------------------------------------------
# Serialize-OUT request models (Plan 25-02, MUT-MD-01): NewSymbol, NewSymbols,
# SymbolPatch. NOT SafeModel subclasses — they serialize OUT via to_dict().
# ----------------------------------------------------------------------


def test_new_symbol_to_dict_defaults_market_id_rofx() -> None:
    """market_id defaults to "ROFX" and is ALWAYS sent explicitly (D-10)."""
    out = NewSymbol("DLR/DIC26").to_dict()
    assert out == {"symbol": "DLR/DIC26", "market_id": "ROFX"}


def test_new_symbol_to_dict_uses_snake_case_market_id_wire_key() -> None:
    """Wire key is snake_case ``market_id`` per source-plan schema (Pitfall 3 / A2),
    intentionally different from LatestRequest's camelCase ``marketId``."""
    out = NewSymbol("DLR/DIC26").to_dict()
    assert "market_id" in out
    assert "marketId" not in out


def test_new_symbol_to_dict_explicit_market_id() -> None:
    out = NewSymbol("GGAL", market_id="ROFX").to_dict()
    assert out == {"symbol": "GGAL", "market_id": "ROFX"}


def test_new_symbols_to_dict_wraps_each_symbol() -> None:
    out = NewSymbols([NewSymbol("A"), NewSymbol("B")]).to_dict()
    assert out == {
        "symbols": [
            {"symbol": "A", "market_id": "ROFX"},
            {"symbol": "B", "market_id": "ROFX"},
        ]
    }


def test_symbol_patch_to_dict_active_false() -> None:
    assert SymbolPatch(active=False).to_dict() == {"active": False}


def test_symbol_patch_to_dict_active_true() -> None:
    assert SymbolPatch(active=True).to_dict() == {"active": True}


def test_new_symbols_empty_raises_value_error() -> None:
    """Lower-bound guard: an empty batch raises a plain ValueError (NOT a
    MarketData* error) before any dispatch (D-11)."""
    with pytest.raises(ValueError, match="1-500"):
        NewSymbols([])


def test_new_symbols_over_500_raises_value_error() -> None:
    """Upper-bound guard: 501 symbols raises a plain ValueError before dispatch."""
    with pytest.raises(ValueError, match="1-500"):
        NewSymbols([NewSymbol(f"S{i}") for i in range(501)])


def test_new_symbols_boundary_1_and_500_construct() -> None:
    """Exactly 1 and exactly 500 symbols construct successfully."""
    one = NewSymbols([NewSymbol("ONLY")])
    assert len(one.symbols) == 1
    full = NewSymbols([NewSymbol(f"S{i}") for i in range(500)])
    assert len(full.symbols) == 500


# ----------------------------------------------------------------------
# Calendar write request models (Plan 26-01, MUT-MD-02): MarketHoursIn,
# HolidayIn, HolidaysIn. NOT SafeModel subclasses — they serialize OUT via
# to_dict(), routed through ``_params.drop_none`` (D-08 / D-11).
# ----------------------------------------------------------------------

_TZ = "America/Argentina/Buenos_Aires"


def test_market_hours_in_to_dict_openapi_defaults_verbatim() -> None:
    """All 7 keys emitted with the live-OpenAPI defaults; confirm is False (D-10)."""
    out = MarketHoursIn("10:00", "17:00", _TZ).to_dict()
    assert out == {
        "open_time": "10:00",
        "close_time": "17:00",
        "timezone": _TZ,
        "pre_open_minutes": 10,
        "enabled": True,
        "updated_by": "",
        "confirm": False,
    }


def test_market_hours_in_confirm_opt_in_is_true() -> None:
    """``confirm`` is a model field the consumer must opt into on purpose (D-09)."""
    assert MarketHoursIn("10:00", "17:00", _TZ, confirm=True).to_dict()["confirm"] is True


def test_market_hours_in_to_dict_keeps_falsy_non_none_values() -> None:
    """drop_none preserves falsy-but-not-None: pre_open_minutes=0 / enabled=False."""
    out = MarketHoursIn(
        "10:00", "17:00", "TZ", pre_open_minutes=0, enabled=False, updated_by="ops"
    ).to_dict()
    assert out["pre_open_minutes"] == 0
    assert out["enabled"] is False
    assert out["updated_by"] == "ops"


def test_holiday_in_to_dict_drops_none_hours() -> None:
    """open_time/close_time DISAPPEAR when None; closed=True and description="" stay (D-11)."""
    out = HolidayIn("2026-12-25").to_dict()
    assert out == {"day": "2026-12-25", "closed": True, "description": ""}
    assert "open_time" not in out
    assert "close_time" not in out


def test_holiday_in_to_dict_custom_hours_all_five_keys() -> None:
    out = HolidayIn(
        "2026-12-24",
        closed=False,
        open_time="10:00",
        close_time="13:00",
        description="Nochebuena",
    ).to_dict()
    assert out == {
        "day": "2026-12-24",
        "closed": False,
        "open_time": "10:00",
        "close_time": "13:00",
        "description": "Nochebuena",
    }


def test_calendar_write_models_are_not_safe_models() -> None:
    """D-08: these serialize OUT — they must NOT inherit SafeModel nor expose from_api."""
    assert not issubclass(MarketHoursIn, SafeModel)
    assert not issubclass(HolidayIn, SafeModel)
    assert not hasattr(MarketHoursIn, "from_api")
    assert not hasattr(HolidayIn, "from_api")


def test_market_hours_in_is_frozen() -> None:
    hours = MarketHoursIn("10:00", "17:00", _TZ)
    with pytest.raises(dataclasses.FrozenInstanceError):
        hours.open_time = "11:00"  # type: ignore[misc]


def test_holiday_in_is_frozen() -> None:
    holiday = HolidayIn("2026-12-25")
    with pytest.raises(dataclasses.FrozenInstanceError):
        holiday.day = "2026-12-26"  # type: ignore[misc]
