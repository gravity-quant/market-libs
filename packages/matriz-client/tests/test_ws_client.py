from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from matriz_client import client as _rest
from matriz_client import ws_client as _ws
from matriz_client.models import (
    ExecutionReportFrame,
    MarketDataFrame,
    PrimaryWsMessage,
    UnknownFrame,
)


@pytest.fixture
def capture_send(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Replace _send with a capturing stub. Returns the list of sent messages."""
    sent: list[dict[str, Any]] = []
    monkeypatch.setattr(_ws, "_send", lambda msg: sent.append(msg))
    return sent


def test_ws_url_converts_https(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_rest, "_base_url", "https://api.remarkets.primary.com.ar")
    assert _ws._ws_url() == "wss://api.remarkets.primary.com.ar"


def test_ws_url_converts_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_rest, "_base_url", "http://localhost:8080")
    assert _ws._ws_url() == "ws://localhost:8080"


def test_send_without_connection_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_ws, "_ws", None)
    _ws._connected.clear()
    with pytest.raises(RuntimeError):
        _ws._send({"type": "x"})


def test_send_without_connected_event_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_ws, "_ws", MagicMock())
    _ws._connected.clear()
    with pytest.raises(RuntimeError):
        _ws._send({"type": "x"})


def test_send_forwards_json(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ws = MagicMock()
    monkeypatch.setattr(_ws, "_ws", fake_ws)
    _ws._connected.set()
    try:
        _ws._send({"type": "os"})
    finally:
        _ws._connected.clear()
    sent_raw = fake_ws.send.call_args.args[0]
    assert sent_raw == '{"type": "os"}'


def test_is_connected_reflects_event(monkeypatch: pytest.MonkeyPatch) -> None:
    _ws._connected.clear()
    assert _ws.ws_is_connected() is False
    _ws._connected.set()
    try:
        assert _ws.ws_is_connected() is True
    finally:
        _ws._connected.clear()


def test_subscribe_market_data_default_entries(capture_send: list[dict[str, Any]]) -> None:
    _ws.ws_subscribe_market_data(["DLR/DIC23"])
    assert capture_send == [
        {
            "type": "smd",
            "level": 1,
            "entries": ["BI", "OF", "LA", "OP", "CL", "SE", "OI"],
            "products": [{"symbol": "DLR/DIC23", "marketId": "ROFX"}],
            "depth": 1,
        }
    ]


def test_subscribe_market_data_custom(capture_send: list[dict[str, Any]]) -> None:
    _ws.ws_subscribe_market_data(["A", "B"], entries=["BI", "OF"], market_id="MERV", depth=5)
    msg = capture_send[0]
    assert msg["entries"] == ["BI", "OF"]
    assert msg["depth"] == 5
    assert msg["products"] == [
        {"symbol": "A", "marketId": "MERV"},
        {"symbol": "B", "marketId": "MERV"},
    ]


def test_subscribe_order_reports_all_accounts(capture_send: list[dict[str, Any]]) -> None:
    _ws.ws_subscribe_order_reports()
    assert capture_send == [{"type": "os"}]


def test_subscribe_order_reports_single_account(capture_send: list[dict[str, Any]]) -> None:
    _ws.ws_subscribe_order_reports(account="ACC1")
    assert capture_send[0] == {"type": "os", "account": {"id": "ACC1"}}


def test_subscribe_order_reports_multiple_accounts(
    capture_send: list[dict[str, Any]],
) -> None:
    _ws.ws_subscribe_order_reports(accounts=["A", "B"], snapshot_only_active=True)
    msg = capture_send[0]
    assert msg["accounts"] == [{"id": "A"}, {"id": "B"}]
    assert msg["snapshotOnlyActive"] is True


def test_ws_new_order_minimal(capture_send: list[dict[str, Any]]) -> None:
    _ws.ws_new_order("DLR/DIC23", "BUY", 1, "ACC1")
    msg = capture_send[0]
    assert msg["type"] == "no"
    assert msg["product"] == {"marketId": "ROFX", "symbol": "DLR/DIC23"}
    assert msg["quantity"] == 1
    assert msg["side"] == "BUY"
    assert msg["account"] == "ACC1"
    assert msg["iceberg"] is False
    assert "price" not in msg
    assert "displayQuantity" not in msg


def test_ws_new_order_full(capture_send: list[dict[str, Any]]) -> None:
    _ws.ws_new_order(
        "S",
        "SELL",
        10,
        "A",
        price=99.5,
        iceberg=True,
        display_quantity=2,
        time_in_force="GTD",
        expire_date="20260430",
        ws_cl_ord_id="req-1",
    )
    msg = capture_send[0]
    assert msg["price"] == 99.5
    assert msg["iceberg"] is True
    assert msg["displayQuantity"] == 2
    assert msg["timeInForce"] == "GTD"
    assert msg["expireDate"] == "20260430"
    assert msg["wsClOrdId"] == "req-1"


def test_ws_cancel_order(capture_send: list[dict[str, Any]]) -> None:
    _ws.ws_cancel_order("cl-1", "PBCP")
    assert capture_send == [{"type": "co", "clientId": "cl-1", "proprietary": "PBCP"}]


# ------------------------------------------------------------------
# Entry validation and level
# ------------------------------------------------------------------


def test_subscribe_market_data_rejects_unknown_entries(
    capture_send: list[dict[str, Any]],
) -> None:
    with pytest.raises(ValueError, match="Unknown market data entries"):
        _ws.ws_subscribe_market_data(["A"], entries=["BI", "BOGUS"])
    assert capture_send == []


def test_subscribe_market_data_accepts_full_entry_catalogue(
    capture_send: list[dict[str, Any]],
) -> None:
    _ws.ws_subscribe_market_data(["A"], entries=list(_ws.MARKET_DATA_ENTRIES))
    assert capture_send[0]["entries"] == list(_ws.MARKET_DATA_ENTRIES)


def test_subscribe_market_data_custom_level(capture_send: list[dict[str, Any]]) -> None:
    _ws.ws_subscribe_market_data(["A"], level=2)
    assert capture_send[0]["level"] == 2


# ------------------------------------------------------------------
# Inbound handlers
# ------------------------------------------------------------------


def test_handle_message_invokes_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    received: list[PrimaryWsMessage] = []
    monkeypatch.setattr(_ws, "_on_message", received.append)
    _ws._handle_message(
        MagicMock(),
        '{"type": "Md", "instrumentId": {"marketId": "ROFX", "symbol": "DLR/DIC23"},'
        ' "marketData": {"OP": 180.0}}',
    )
    assert len(received) == 1
    msg = received[0]
    assert isinstance(msg, MarketDataFrame)
    assert msg.instrumentId.symbol == "DLR/DIC23"
    assert msg.marketData.OP == 180.0


def test_handle_message_parses_execution_report(monkeypatch: pytest.MonkeyPatch) -> None:
    received: list[PrimaryWsMessage] = []
    monkeypatch.setattr(_ws, "_on_message", received.append)
    _ws._handle_message(
        MagicMock(),
        '{"type": "or", "timestamp": 1537212212623,'
        ' "orderReport": {"clOrdId": "abc", "wsClOrdId": "ws-1", "status": "PENDING_NEW"}}',
    )
    msg = received[0]
    assert isinstance(msg, ExecutionReportFrame)
    assert msg.timestamp == 1537212212623
    assert msg.orderReport.clOrdId == "abc"
    assert msg.orderReport.wsClOrdId == "ws-1"


def test_handle_message_unknown_type_falls_back_to_unknown_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[PrimaryWsMessage] = []
    monkeypatch.setattr(_ws, "_on_message", received.append)
    _ws._handle_message(MagicMock(), '{"type": "heartbeat", "ts": 123}')
    msg = received[0]
    assert isinstance(msg, UnknownFrame)
    assert msg.type == "heartbeat"
    assert msg.raw == {"type": "heartbeat", "ts": 123}


def test_handle_message_partial_market_data_payload_parses_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing keys collapse to safe defaults; chained access never raises."""
    received: list[PrimaryWsMessage] = []
    monkeypatch.setattr(_ws, "_on_message", received.append)
    _ws._handle_message(MagicMock(), '{"type": "Md"}')
    msg = received[0]
    assert isinstance(msg, MarketDataFrame)
    assert msg.instrumentId.symbol is None
    assert msg.marketData.BI == []
    assert msg.marketData.SE.price is None


def test_handle_message_noop_without_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_ws, "_on_message", None)
    _ws._handle_message(MagicMock(), '{"type": "Md"}')


def test_handle_error_invokes_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    received: list[Exception] = []
    monkeypatch.setattr(_ws, "_on_error", received.append)
    err = RuntimeError("boom")
    _ws._handle_error(MagicMock(), err)
    assert received == [err]


def test_handle_open_sets_event(monkeypatch: pytest.MonkeyPatch) -> None:
    _ws._connected.clear()
    _ws._handle_open(MagicMock())
    try:
        assert _ws._connected.is_set()
    finally:
        _ws._connected.clear()


def test_handle_close_clears_event_and_invokes_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"n": 0}

    def cb() -> None:
        called["n"] += 1

    _ws._connected.set()
    monkeypatch.setattr(_ws, "_on_close", cb)
    _ws._handle_close(MagicMock(), 1000, "normal")
    assert called["n"] == 1
    assert not _ws._connected.is_set()
