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

from market_data_client.models import (
    LatestRequest,
    MarketDataSnapshot,
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
