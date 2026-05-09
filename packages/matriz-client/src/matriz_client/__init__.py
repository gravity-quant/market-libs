"""Python client for the MATBA ROFEX Primary API v1.21.

Re-exports the REST (:mod:`.client`) and WebSocket (:mod:`.ws_client`)
surface as a flat namespace, so callers can simply do::

    import matriz_client as primary

    segments = primary.get_segments()  # login automático en la 1ra llamada
    primary.ws_connect(on_message=my_handler)

El token se cachea y se refresca antes de la expiración (24 h server-side).
``login()`` está expuesto por si querés validar credenciales temprano, pero
no es obligatorio invocarlo.

See the README and the in-module docstrings for usage details.
"""

from matriz_client.client import (
    cancel_order,
    configure,
    get_account_report,
    get_active_orders,
    get_all_instruments,
    get_all_orders,
    get_detailed_positions,
    get_filled_orders,
    get_instrument_detail,
    get_instruments_by_cfi,
    get_instruments_by_segment,
    get_instruments_details,
    get_market_data,
    get_order_by_exec_id,
    get_order_history,
    get_order_status,
    get_positions,
    get_segments,
    get_trades,
    login,
    new_order,
    replace_order,
)
from matriz_client.exceptions import AuthenticationError, MatrizClientError, PrimaryAPIError
from matriz_client.models import (
    AccountId,
    AccountReport,
    DetailedPosition,
    ExecutionReportFrame,
    Instrument,
    InstrumentDetail,
    InstrumentId,
    MarketDataEntryValue,
    MarketDataFrame,
    MarketDataLevel,
    MarketDataSnapshot,
    NewOrderResponse,
    Order,
    OrderReport,
    Position,
    PrimaryWsMessage,
    Segment,
    Trade,
    UnknownFrame,
)
from matriz_client.types import (
    CFICode,
    Currency,
    MarketDataEntry,
    MarketId,
    OrderStatus,
    OrderType,
    SegmentId,
    Side,
    TimeInForce,
)
from matriz_client.ws_client import (
    DEFAULT_MARKET_DATA_ENTRIES,
    MARKET_DATA_ENTRIES,
    ws_cancel_order,
    ws_connect,
    ws_disconnect,
    ws_is_connected,
    ws_new_order,
    ws_subscribe_market_data,
    ws_subscribe_order_reports,
)

__all__ = [
    "DEFAULT_MARKET_DATA_ENTRIES",
    "MARKET_DATA_ENTRIES",
    # Models — safe-access dataclasses
    "AccountId",
    "AccountReport",
    "AuthenticationError",
    # Types — Literals
    "CFICode",
    "Currency",
    "DetailedPosition",
    "ExecutionReportFrame",
    "Instrument",
    "InstrumentDetail",
    "InstrumentId",
    "MarketDataEntry",
    "MarketDataEntryValue",
    "MarketDataFrame",
    "MarketDataLevel",
    "MarketDataSnapshot",
    "MarketId",
    "MatrizClientError",
    "NewOrderResponse",
    "Order",
    "OrderReport",
    "OrderStatus",
    "OrderType",
    "Position",
    "PrimaryAPIError",
    "PrimaryWsMessage",
    "Segment",
    "SegmentId",
    "Side",
    "TimeInForce",
    "Trade",
    "UnknownFrame",
    # REST
    "cancel_order",
    "configure",
    "get_account_report",
    "get_active_orders",
    "get_all_instruments",
    "get_all_orders",
    "get_detailed_positions",
    "get_filled_orders",
    "get_instrument_detail",
    "get_instruments_by_cfi",
    "get_instruments_by_segment",
    "get_instruments_details",
    "get_market_data",
    "get_order_by_exec_id",
    "get_order_history",
    "get_order_status",
    "get_positions",
    "get_segments",
    "get_trades",
    "login",
    "new_order",
    "replace_order",
    # WebSocket
    "ws_cancel_order",
    "ws_connect",
    "ws_disconnect",
    "ws_is_connected",
    "ws_new_order",
    "ws_subscribe_market_data",
    "ws_subscribe_order_reports",
]
