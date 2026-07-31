"""Tests for the tolerant ``market_data_client.models`` layer (Plan 21-01).

Pins the D-01/D-04/D-05 behaviors:

- ``MarketDataSnapshot.from_api`` tolerates ``{}`` / ``None`` / extra-key payloads
  without raising, substituting typed zero-defaults and ``entries == []``.
- ``received_at`` is a CLIENT-STAMPED field injected as a keyword; it must NOT be
  coerced from the payload — a decoy ``"received_at"`` payload key is ignored and
  the injected kwarg wins (D-01, the highest-risk fidelity point of the phase).
- Nested ``MarketDataEntry`` rows deserialize via the base ``SafeModel.from_api``
  and carry NO ``received_at`` attribute.
- ``LatestRequest(...).to_dict()`` drops ``None``-valued optionals and keeps
  supplied values (D-05).
"""

from __future__ import annotations

from market_data_client.models import (
    LatestRequest,
    MarketDataEntry,
    MarketDataSnapshot,
)


def test_from_api_empty_dict_typed_zero_defaults() -> None:
    snap = MarketDataSnapshot.from_api({})
    assert snap.symbol == ""
    assert snap.marketId == ""
    assert snap.entries == []


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


def test_entries_deserialize_as_entry_models_without_received_at() -> None:
    snap = MarketDataSnapshot.from_api(
        {
            "symbol": "GGAL",
            "entries": [
                {"entryType": "BID", "price": 100.5},
                {"entryType": "OFFER"},
            ],
        },
        received_at=42.0,
    )
    assert len(snap.entries) == 2
    assert all(isinstance(e, MarketDataEntry) for e in snap.entries)
    assert snap.entries[0].entryType == "BID"
    assert snap.entries[0].price == 100.5
    assert snap.entries[1].entryType == "OFFER"
    assert snap.entries[1].price == 0.0
    # Entries never carry received_at — only the top-level snapshot does.
    assert not hasattr(snap.entries[0], "received_at")


def test_entries_partial_or_wrong_type_tolerated() -> None:
    snap = MarketDataSnapshot.from_api({"entries": "not-a-list"}, received_at=1.0)
    assert snap.entries == []


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
