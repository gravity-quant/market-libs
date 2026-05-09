"""WebSocket streaming client for the MATBA ROFEX Primary API.

Provides real-time market data and execution-report subscriptions, plus
order entry/cancel over the same connection. The WebSocket URL is derived
from the REST base URL by swapping the scheme (``https`` → ``wss``), and
the connection authenticates with the cached REST token. :func:`ws_connect`
dispara el login automáticamente si todavía no hay token cacheado.

The connection runs its event loop in a background daemon thread. All
inbound frames are dispatched to the user-provided callbacks registered
at :func:`ws_connect` time.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from typing import Any

import websocket

from matriz_client import client as _rest
from matriz_client.models import (
    ExecutionReportFrame,
    MarketDataFrame,
    PrimaryWsMessage,
    UnknownFrame,
)
from matriz_client.types import DEFAULT_MARKET_DATA_ENTRIES, MARKET_DATA_ENTRIES

# -- Types --
MessageCallback = Callable[[PrimaryWsMessage], None]
ErrorCallback = Callable[[Exception], None]
CloseCallback = Callable[[], None]

__all__ = [
    "DEFAULT_MARKET_DATA_ENTRIES",
    "MARKET_DATA_ENTRIES",
    "ws_cancel_order",
    "ws_connect",
    "ws_disconnect",
    "ws_is_connected",
    "ws_new_order",
    "ws_subscribe_market_data",
    "ws_subscribe_order_reports",
]

# -- Module-level state --
_ws: websocket.WebSocketApp | None = None
_ws_thread: threading.Thread | None = None
_on_message: MessageCallback | None = None
_on_error: ErrorCallback | None = None
_on_close: CloseCallback | None = None
_connected = threading.Event()


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _ws_url() -> str:
    """Derive the WebSocket URL from the REST base URL."""
    url = _rest._base_url
    if url.startswith("https://"):
        return url.replace("https://", "wss://", 1)
    return url.replace("http://", "ws://", 1)


def _handle_open(ws: websocket.WebSocketApp) -> None:
    _connected.set()


def _parse_frame(data: dict[str, Any]) -> PrimaryWsMessage:
    """Wrap ``data`` in the safe-access frame model matching its ``type``.

    Frames with an unknown or missing ``type`` collapse to
    :class:`~matriz_client.models.UnknownFrame`, which keeps the raw
    payload available via :attr:`UnknownFrame.raw`.
    """
    type_name = data.get("type", "")
    if type_name == "Md":
        return MarketDataFrame.from_api(data)
    if type_name == "or":
        return ExecutionReportFrame.from_api(data)
    return UnknownFrame.from_api(data)


def _handle_message(ws: websocket.WebSocketApp, raw: str) -> None:
    if _on_message is not None:
        data: dict[str, Any] = json.loads(raw)
        _on_message(_parse_frame(data))


def _handle_error(ws: websocket.WebSocketApp, error: Exception) -> None:
    if _on_error is not None:
        _on_error(error)


def _handle_close(
    ws: websocket.WebSocketApp,
    close_status_code: int | None,
    close_msg: str | None,
) -> None:
    _connected.clear()
    if _on_close is not None:
        _on_close()


def _send(msg: dict[str, Any]) -> None:
    if _ws is None or not _connected.is_set():
        raise RuntimeError("WebSocket is not connected. Call ws_connect() first.")
    _ws.send(json.dumps(msg))


# ------------------------------------------------------------------
# Connection
# ------------------------------------------------------------------


def ws_connect(
    *,
    on_message: MessageCallback | None = None,
    on_error: ErrorCallback | None = None,
    on_close: CloseCallback | None = None,
    timeout: float = 10.0,
) -> None:
    """Connect to the Primary WebSocket, authenticating with the REST token.

    Runs the WebSocket event loop in a background daemon thread.
    Blocks until the connection is established or *timeout* seconds elapse.
    """
    global _ws, _ws_thread, _on_message, _on_error, _on_close

    if _ws is not None and _connected.is_set():
        return

    _rest._ensure_token()
    assert _rest._token is not None

    _on_message = on_message
    _on_error = on_error
    _on_close = on_close
    _connected.clear()

    url = _ws_url()
    _ws = websocket.WebSocketApp(
        url,
        header={"X-Auth-Token": _rest._token},
        on_open=_handle_open,
        on_message=_handle_message,
        on_error=_handle_error,
        on_close=_handle_close,
    )

    _ws_thread = threading.Thread(target=_ws.run_forever, daemon=True)
    _ws_thread.start()
    if not _connected.wait(timeout=timeout):
        raise TimeoutError(f"WebSocket connection to {url} timed out after {timeout}s")


def ws_disconnect() -> None:
    """Close the WebSocket connection."""
    global _ws, _ws_thread
    if _ws is not None:
        _ws.close()
        _ws = None
    if _ws_thread is not None:
        _ws_thread.join(timeout=5.0)
        _ws_thread = None
    _connected.clear()


def ws_is_connected() -> bool:
    """Return True if the WebSocket is currently connected."""
    return _connected.is_set()


# ------------------------------------------------------------------
# Market Data subscriptions  (§8.2)
# ------------------------------------------------------------------


def ws_subscribe_market_data(
    symbols: list[str],
    entries: list[str] | None = None,
    *,
    market_id: str = "ROFX",
    depth: int = 1,
    level: int = 1,
) -> None:
    """Subscribe to real-time market data for one or more instruments.

    Incoming messages arrive via the ``on_message`` callback registered with
    :func:`ws_connect` and have ``type == "Md"`` (see §8.2 of the spec).

    Args:
        symbols: List of instrument symbols (e.g. ``["DLR/DIC23", "SOJ.ROS/MAY23"]``).
        entries: Entry codes to receive (see :data:`MARKET_DATA_ENTRIES`).
            Defaults to :data:`DEFAULT_MARKET_DATA_ENTRIES`.
        market_id: Market identifier, defaults to ``"ROFX"``.
        depth: Book depth (1-5), defaults to 1.
        level: Market-data level as defined by the Primary API, defaults to 1.

    Raises:
        ValueError: If ``entries`` contains codes that are not recognized.
        RuntimeError: If the WebSocket is not connected.
    """
    if entries is None:
        entries = list(DEFAULT_MARKET_DATA_ENTRIES)
    else:
        unknown = set(entries) - set(MARKET_DATA_ENTRIES)
        if unknown:
            raise ValueError(f"Unknown market data entries: {sorted(unknown)}")

    msg: dict[str, Any] = {
        "type": "smd",
        "level": level,
        "entries": entries,
        "products": [{"symbol": s, "marketId": market_id} for s in symbols],
        "depth": depth,
    }
    _send(msg)


# ------------------------------------------------------------------
# Execution Report subscriptions  (§7)
# ------------------------------------------------------------------


def ws_subscribe_order_reports(
    account: str | None = None,
    accounts: list[str] | None = None,
    *,
    snapshot_only_active: bool = False,
) -> None:
    """Subscribe to execution reports.

    Args:
        account: Single account ID to subscribe to.
        accounts: List of account IDs to subscribe to.
        snapshot_only_active: If True, only receive reports for active orders
                              (NEW / PARTIALLY_FILLED).

    If both *account* and *accounts* are None, subscribes to all accounts.
    """
    msg: dict[str, Any] = {"type": "os"}

    if accounts is not None:
        msg["accounts"] = [{"id": a} for a in accounts]
    elif account is not None:
        msg["account"] = {"id": account}

    if snapshot_only_active:
        msg["snapshotOnlyActive"] = True

    _send(msg)


# ------------------------------------------------------------------
# Orders  (§6.4 / §6.7)
# ------------------------------------------------------------------


def ws_new_order(
    symbol: str,
    side: str,
    quantity: int,
    account: str,
    price: float | None = None,
    *,
    market_id: str = "ROFX",
    iceberg: bool = False,
    display_quantity: int | None = None,
    time_in_force: str | None = None,
    expire_date: str | None = None,
    ws_cl_ord_id: str | None = None,
) -> None:
    """Send a new order via WebSocket.

    Args:
        symbol: Instrument symbol (e.g. "DLR/DIC23").
        side: "BUY" or "SELL".
        quantity: Order quantity.
        account: Account ID.
        price: Order price (required for LIMIT orders).
        market_id: Market identifier, defaults to "ROFX".
        iceberg: Whether this is an iceberg order.
        display_quantity: Visible quantity for iceberg orders.
        time_in_force: "DAY", "IOC", "FOK", or "GTD". Omit for default (DAY).
        expire_date: Expiry date for GTD orders (format: "YYYYMMDD").
        ws_cl_ord_id: Optional client-assigned ID to identify this order
                      in the first execution report.
    """
    msg: dict[str, Any] = {
        "type": "no",
        "product": {"marketId": market_id, "symbol": symbol},
        "quantity": quantity,
        "side": side,
        "account": account,
        "iceberg": iceberg,
    }

    if price is not None:
        msg["price"] = price
    if display_quantity is not None:
        msg["displayQuantity"] = display_quantity
    if time_in_force is not None:
        msg["timeInForce"] = time_in_force
    if expire_date is not None:
        msg["expireDate"] = expire_date
    if ws_cl_ord_id is not None:
        msg["wsClOrdId"] = ws_cl_ord_id

    _send(msg)


def ws_cancel_order(client_id: str, proprietary: str) -> None:
    """Cancel an order via WebSocket.

    Args:
        client_id: The clOrdId of the order to cancel.
        proprietary: The proprietary identifier (e.g. "PBCP").
    """
    _send(
        {
            "type": "co",
            "clientId": client_id,
            "proprietary": proprietary,
        }
    )
