"""WebSocket streaming client for the MATBA ROFEX Primary API.

Provides real-time market data and execution-report subscriptions, plus
order entry/cancel over the same connection. The WebSocket URL is derived
from the REST base URL by swapping the scheme (``https`` → ``wss``), and
the connection authenticates with the cached REST token. :func:`ws_connect`
dispara el login automáticamente si todavía no hay token cacheado.

The connection runs its event loop in a background daemon thread. All
inbound frames are dispatched to the user-provided callbacks registered
at :func:`ws_connect` time.

**Decode mode on the daemon thread (Phase 29 Plan 29-08, D-04).** This is the
one decode path in the package that never passes through ``Client._request``,
and a plain ``threading.Thread`` starts with an EMPTY execution context, so it
inherits no ``ContextVar`` value from the thread that spawned it. The mode is
therefore handed over explicitly: :func:`_bind_decode_mode_for_ws` snapshots
``_ClientState.strict_decode`` at connect time (on the caller's thread) and
:func:`_handle_open` binds that snapshot inside the daemon thread. See those
two functions for the mechanism and the measurement behind it.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from typing import Any

import websocket

from matriz_client import _decode
from matriz_client import client as _rest
from matriz_client.exceptions import MatrizDecodeError
from matriz_client.models import (
    ExecutionReportFrame,
    MarketDataFrame,
    PrimaryWsMessage,
    UnknownFrame,
)
from matriz_client.types import DEFAULT_MARKET_DATA_ENTRIES, MARKET_DATA_ENTRIES

# The package logger, exactly as ``_decode`` uses it. ``RedactingFilter`` is
# attached to ``logging.getLogger("matriz_client")`` and a filter only sees
# records logged directly to its own logger, so a child logger named after
# this module would bypass redaction on propagation.
_LOGGER = logging.getLogger("matriz_client")

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

# Phase 29 D-04: the decode mode snapshotted from the REST client's shared
# state at connect time, for the daemon thread to bind at ``on_open``. ``None``
# means "no connection has been established in this process yet"; it is reset
# to ``None`` by :func:`ws_disconnect` so a reconnection re-reads the flag.
_ws_strict_decode: bool | None = None


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _ws_url() -> str:
    """Derive the WebSocket URL from the REST base URL.

    Reads via the explicit ``_get_default()`` accessor (post Phase 6 Plan 06)
    instead of the legacy module-level ``_base_url`` global; the PEP 562 shim
    would also work, but the explicit form makes the cross-module ownership
    boundary obvious in code review.
    """
    url = _rest._get_default()._state.base_url
    if url.startswith("https://"):
        return url.replace("https://", "wss://", 1)
    return url.replace("http://", "ws://", 1)


def _handle_open(ws: websocket.WebSocketApp) -> None:
    """Bind the decode mode inside the daemon thread, then signal readiness.

    This callback is invoked by ``WebSocketApp.run_forever``, i.e. **on the
    daemon thread**, which is the whole reason the bind lives here rather than
    in :func:`ws_connect` (that runs on the caller's thread, whose context the
    daemon thread does not inherit). The daemon thread's execution context is
    stable for its lifetime, so binding once at open is sufficient for every
    frame the connection subsequently delivers, and it involves no context
    re-entry — see :func:`_bind_decode_mode_for_ws` for why that matters.

    ``_ws_strict_decode`` is ``None`` when this handler is reached without a
    preceding :func:`ws_connect` (a direct call in a test, or a reconnection
    race after :func:`ws_disconnect` cleared it); that collapses to the
    ``STRICT_DECODE`` default, which is observable mode.
    """
    _decode.STRICT_DECODE.set(bool(_ws_strict_decode))
    _decode.open_request_scope()
    _connected.set()


@_decode._response_parser
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
    """Decode one inbound frame and hand it to the message callback.

    A fresh decode scope is opened per frame. Aggregation-contract lock 6 binds
    one scope per decoded unit and explicitly rejects a process-lifetime scope,
    because a shared dedupe set makes the *second* identical divergence decode
    silently clean. A streamed frame is the WebSocket analogue of one HTTP
    response, so a scope that spanned the connection would let a long-lived
    subscription report a recurring divergence exactly once and then go quiet.

    A strict-mode decode raises, and an exception escaping this handler
    terminates ``run_forever`` — tearing the connection down for *every*
    subscriber over one malformed frame. :class:`MatrizDecodeError` is
    therefore caught here and routed to the registered error callback, falling
    back to the package logger when none is registered. Nothing broader is
    caught: an unrelated exception keeps its previous behaviour, and an error
    raised by ``_on_message`` itself is outside the guarded block.
    """
    if _on_message is None:
        return
    data: dict[str, Any] = json.loads(raw)
    _decode.open_request_scope()
    try:
        frame = _parse_frame(data)
    except MatrizDecodeError as exc:
        if _on_error is not None:
            _on_error(exc)
        else:
            _LOGGER.warning("websocket frame failed strict decode: %s", exc)
        return
    _on_message(frame)


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


def _acquire_token_for_ws(default: _rest.Client) -> None:
    """Acquire the REST token for the daemon-thread WebSocket connection.

    Phase 10 Plan 10-03 REFAC-04 — 3-way TokenStore wiring. The daemon
    thread participates in the cross-context lock by calling
    ``state.token_store.get_sync()`` directly. The preceding
    ``default._ensure_token()`` call is what lazy-inits ``state.token_store``
    if this is the first auth call in the process; the explicit
    ``get_sync()`` then anchors the daemon thread to the shared TokenStore
    (1 of 3 callers: sync REST main thread, async REST event loop, this
    daemon thread). The result is mirrored to ``state.token`` for the
    back-compat ``X-Auth-Token`` header read at the call site.
    """
    default._ensure_token()  # lazy-inits state.token_store if needed
    assert default._state.token_store is not None
    snap = default._state.token_store.get_sync()
    default._state.token = snap.value  # mirror for back-compat header read
    assert default._state.token is not None


def _bind_decode_mode_for_ws(default: _rest.Client) -> None:
    """Snapshot the REST client's decode mode for the daemon thread (D-04).

    Phase 29 Plan 29-08, D-04 — explicit decode-mode propagation. This helper
    exists for one fact: **a plain ``threading.Thread`` starts with an empty
    execution context and does not inherit the spawning thread's ``ContextVar``
    values.** Every ``STRICT_DECODE.get()`` on the daemon thread would return
    the ``False`` default. And the frame path never passes through
    ``Client._request``, which is the only place the REST surface binds the
    mode, so there is no other route by which the mode could arrive. Without
    this hand-off every streamed frame would decode in observable mode
    regardless of what the caller configured — a silent, mode-shaped hole in
    DEC-01. The non-inheritance fact is measured, not assumed: see
    ``market-data-client/tests/test_decode_concurrency.py`` (Plan 29-05) and
    ``test_ws_decode_mode.py::test_plain_thread_does_not_inherit_the_decode_mode``.

    This mirrors :func:`_acquire_token_for_ws` above, which hands the same
    daemon thread its main-thread token state at the same point in
    :func:`ws_connect`. D-03: the value is read from ``_ClientState``, never
    from an environment variable. The snapshot is taken here, on the caller's
    thread, and bound in :func:`_handle_open`, on the daemon thread.

    **The fallback mechanism, and why it is not the one used.** The alternative
    is a ``contextvars.copy_context()`` snapshot captured in :func:`ws_connect`
    and each frame parsed via ``ctx.run(_parse_frame, data)``. Research
    assumption A1 flagged its re-entrancy behaviour as reasoned but not
    executed; it was measured for this plan on CPython 3.12.13 and **A1 is
    confirmed**: repeated *sequential* ``ctx.run()`` calls on one stored
    ``Context`` succeed, but a nested or a concurrent (overlapping) call raises
    ``RuntimeError: cannot enter context ... is already entered``. Two further
    measured facts make it worse for this call site: writes performed inside a
    stored ``Context`` **persist across runs**, so a decode scope opened there
    would live for the whole connection and violate lock 6; and the ``Context``
    is process-global module state, so a second connection would contend with
    the first. Binding the plain value once at open has none of those
    properties, which is why it is the mechanism here.
    """
    global _ws_strict_decode
    _ws_strict_decode = default._state.strict_decode


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

    default = _rest._get_default()
    _acquire_token_for_ws(default)
    _bind_decode_mode_for_ws(default)
    assert default._state.token is not None  # narrowing for header dict below

    _on_message = on_message
    _on_error = on_error
    _on_close = on_close
    _connected.clear()

    url = _ws_url()
    _ws = websocket.WebSocketApp(
        url,
        header={"X-Auth-Token": default._state.token},
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
    """Close the WebSocket connection.

    Clears the D-04 decode-mode snapshot as well, so a client that flips
    ``strict_decode`` between connections gets the new mode on the next
    :func:`ws_connect` instead of the value the previous connection captured.
    """
    global _ws, _ws_thread, _ws_strict_decode
    if _ws is not None:
        _ws.close()
        _ws = None
    if _ws_thread is not None:
        _ws_thread.join(timeout=5.0)
        _ws_thread = None
    _ws_strict_decode = None
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
