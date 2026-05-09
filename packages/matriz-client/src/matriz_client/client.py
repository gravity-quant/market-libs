"""REST client for the MATBA ROFEX Primary API v1.21.

Thin wrapper over the HTTP endpoints of the Primary API. State is held at
module level (token, HTTP client, credentials) and the token is refreshed
automatically a little before the 24 h server-side expiry.

Auth modes:
- **Token** (default, most endpoints): obtained via ``POST /auth/getToken``
  and sent as ``X-Auth-Token`` on every subsequent request.
- **HTTP Basic** (Risk API only): uses ``PRIMARY_USER``/``PRIMARY_PASSWORD``
  directly on each request.

Environment variables (loaded from ``.env`` via ``python-dotenv``):
- ``PRIMARY_USER`` — API username (required)
- ``PRIMARY_PASSWORD`` — API password (required)
- ``PRIMARY_BASE_URL`` — defaults to ``https://api.remarkets.primary.com.ar``

See :mod:`matriz_client.ws_client` for the WebSocket streaming counterpart.
"""

from __future__ import annotations

import os
import time
from collections.abc import Sequence
from typing import Any

import httpx
from dotenv import load_dotenv

from matriz_client.exceptions import AuthenticationError, PrimaryAPIError
from matriz_client.models import (
    AccountReport,
    DetailedPosition,
    Instrument,
    InstrumentDetail,
    MarketDataSnapshot,
    NewOrderResponse,
    Order,
    Position,
    Segment,
    Trade,
)
from matriz_client.types import (
    DEFAULT_MARKET_DATA_ENTRIES,
    CFICode,
    MarketDataEntry,
    MarketId,
    OrderType,
    SegmentId,
    Side,
    TimeInForce,
)

load_dotenv()

# -- Module-level state --
_base_url: str = os.getenv("PRIMARY_BASE_URL", "https://api.remarkets.primary.com.ar").rstrip("/")
_user: str = os.getenv("PRIMARY_USER", "")
_password: str = os.getenv("PRIMARY_PASSWORD", "")
_token: str | None = None
_token_ts: float = 0.0
_TOKEN_TTL = 23 * 60 * 60  # refresh 1 h before the 24 h expiry
_REQUEST_TIMEOUT = 30.0
_session = httpx.Client(timeout=_REQUEST_TIMEOUT)


def configure(
    *,
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> None:
    """Sobrescribe credenciales/URL en runtime y resetea el token cacheado."""
    global _base_url, _user, _password, _token, _token_ts
    if base_url is not None:
        _base_url = base_url.rstrip("/")
    if username is not None:
        _user = username
    if password is not None:
        _password = password
    _token = None
    _token_ts = 0.0


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------


def _ensure_token() -> None:
    """Log in if there is no cached token or it is older than ``_TOKEN_TTL``."""
    if _token and (time.time() - _token_ts) < _TOKEN_TTL:
        return
    login()


def login() -> str:
    """Authenticate against ``/auth/getToken`` and cache the resulting token.

    Returns:
        The newly issued token string, also stored in module state.

    Raises:
        AuthenticationError: If credentials are missing or the response has
            no ``X-Auth-Token`` header.
    """
    global _token, _token_ts
    if not _user or not _password:
        raise AuthenticationError("ERROR", "PRIMARY_USER and PRIMARY_PASSWORD must be set")

    resp = _session.post(
        f"{_base_url}/auth/getToken",
        headers={"X-Username": _user, "X-Password": _password},
    )
    resp.raise_for_status()
    token = resp.headers.get("X-Auth-Token")
    if not isinstance(token, str) or not token:
        raise AuthenticationError("ERROR", "No X-Auth-Token header in response")
    _token = token
    _token_ts = time.time()

    return token


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    auth_basic: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """Execute an HTTP request and decode the JSON payload.

    When ``auth_basic`` is provided, HTTP Basic Auth is used and the token
    flow is skipped (Risk API). Otherwise, the token is ensured/refreshed
    and sent via ``X-Auth-Token``.

    Raises:
        PrimaryAPIError: If the decoded payload has ``status == "ERROR"``.
    """
    url = f"{_base_url}{path}"
    if auth_basic:
        resp = _session.request(
            method,
            url,
            params=params,
            auth=httpx.BasicAuth(*auth_basic),
        )
    else:
        _ensure_token()
        assert _token is not None
        resp = _session.request(
            method,
            url,
            params=params,
            headers={"X-Auth-Token": _token},
        )

    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    if data.get("status") == "ERROR":
        raise PrimaryAPIError(
            status="ERROR",
            description=data.get("description"),
            message=data.get("message"),
        )
    return data


def _get(path: str, **params: Any) -> dict[str, Any]:
    """GET ``path`` with ``params`` after dropping keys whose value is ``None``."""
    clean = {k: v for k, v in params.items() if v is not None}
    return _request("GET", path, params=clean)


def _risk_auth() -> tuple[str, str]:
    """Return the (user, password) tuple used for Risk API HTTP Basic Auth."""
    return (_user, _password)


# ------------------------------------------------------------------
# Segments  (§4)
# ------------------------------------------------------------------


def get_segments() -> list[Segment]:
    """Return all available market segments."""
    return [Segment.from_api(s) for s in _get("/rest/segment/all")["segments"]]


# ------------------------------------------------------------------
# Instruments  (§5)
# ------------------------------------------------------------------


def get_all_instruments() -> list[Instrument]:
    """Return all tradable instruments with basic info (symbol + ``marketId``)."""
    return [Instrument.from_api(i) for i in _get("/rest/instruments/all")["instruments"]]


def get_instruments_details() -> list[InstrumentDetail]:
    """Return all instruments with full detail (tick size, contract size, etc.)."""
    return [InstrumentDetail.from_api(i) for i in _get("/rest/instruments/details")["instruments"]]


def get_instrument_detail(symbol: str, market_id: MarketId = "ROFX") -> InstrumentDetail:
    """Return the full detail record for a single instrument."""
    return InstrumentDetail.from_api(
        _get("/rest/instruments/detail", symbol=symbol, marketId=market_id)["instrument"]
    )


def get_instruments_by_cfi(cfi_code: CFICode) -> list[Instrument]:
    """Return instruments filtered by ISO 10962 CFI code."""
    return [
        Instrument.from_api(i)
        for i in _get("/rest/instruments/byCFICode", CFICode=cfi_code)["instruments"]
    ]


def get_instruments_by_segment(
    segment_id: SegmentId, market_id: MarketId = "ROFX"
) -> list[Instrument]:
    """Return instruments belonging to the given market segment."""
    return [
        Instrument.from_api(i)
        for i in _get(
            "/rest/instruments/bySegment", MarketSegmentID=segment_id, MarketID=market_id
        )["instruments"]
    ]


# ------------------------------------------------------------------
# Orders  (§6)
# ------------------------------------------------------------------


def new_order(
    symbol: str,
    side: Side,
    qty: int,
    account: str,
    price: float | None = None,
    *,
    order_type: OrderType = "LIMIT",
    time_in_force: TimeInForce = "DAY",
    market_id: MarketId = "ROFX",
    cancel_previous: bool = False,
    iceberg: bool = False,
    display_qty: int | None = None,
    expire_date: str | None = None,
) -> NewOrderResponse:
    """Submit a new single order (§6.3).

    Note: The Primary API accepts order submission over HTTP **GET**; this
    is a quirk of the upstream API, not a bug in this client.
    """
    params: dict[str, Any] = {
        "marketId": market_id,
        "symbol": symbol,
        "side": side,
        "orderQty": qty,
        "ordType": order_type,
        "timeInForce": time_in_force,
        "account": account,
        "cancelPrevious": str(cancel_previous),
        "iceberg": str(iceberg),
    }
    if price is not None:
        params["price"] = price
    if display_qty is not None:
        params["displayQty"] = display_qty
    if expire_date is not None:
        params["expireDate"] = expire_date

    return NewOrderResponse.from_api(_get("/rest/order/newSingleOrder", **params)["order"])


def replace_order(cl_ord_id: str, proprietary: str, qty: int, price: float) -> NewOrderResponse:
    """Modify an existing order, identified by ``(clOrdId, proprietary)`` (§6.5)."""
    return NewOrderResponse.from_api(
        _get(
            "/rest/order/replaceById",
            clOrdId=cl_ord_id,
            proprietary=proprietary,
            orderQty=qty,
            price=price,
        )["order"]
    )


def cancel_order(cl_ord_id: str, proprietary: str) -> NewOrderResponse:
    """Cancel the order identified by ``(clOrdId, proprietary)`` (§6.6)."""
    return NewOrderResponse.from_api(
        _get("/rest/order/cancelById", clOrdId=cl_ord_id, proprietary=proprietary)["order"]
    )


def get_order_status(cl_ord_id: str, proprietary: str) -> Order:
    """Return the latest status record for ``(clOrdId, proprietary)`` (§6.8)."""
    return Order.from_api(
        _get("/rest/order/id", clOrdId=cl_ord_id, proprietary=proprietary)["order"]
    )


def get_order_history(cl_ord_id: str, proprietary: str) -> list[Order]:
    """Return the full list of status transitions for ``(clOrdId, proprietary)`` (§6.9)."""
    return [
        Order.from_api(o)
        for o in _get("/rest/order/allById", clOrdId=cl_ord_id, proprietary=proprietary)["orders"]
    ]


def get_active_orders(account_id: str) -> list[Order]:
    """Return all orders currently active (``NEW`` or ``PARTIALLY_FILLED``) for an account (§6.10)."""
    return [Order.from_api(o) for o in _get("/rest/order/actives", accountId=account_id)["orders"]]


def get_filled_orders(account_id: str) -> list[Order]:
    """Return all fully filled orders for an account (§6.11)."""
    return [Order.from_api(o) for o in _get("/rest/order/filleds", accountId=account_id)["orders"]]


def get_all_orders(account_id: str) -> list[Order]:
    """Return the latest status record of every request sent by an account (§6.12)."""
    return [Order.from_api(o) for o in _get("/rest/order/all", accountId=account_id)["orders"]]


def get_order_by_exec_id(exec_id: str) -> Order:
    """Return the order matching the given execution ID (``execId``) (§6.13)."""
    return Order.from_api(_get("/rest/order/byExecId", execId=exec_id)["order"])


# ------------------------------------------------------------------
# Market Data  (§8)
# ------------------------------------------------------------------


def get_market_data(
    symbol: str,
    entries: Sequence[MarketDataEntry] = DEFAULT_MARKET_DATA_ENTRIES,
    *,
    market_id: MarketId = "ROFX",
    depth: int | None = None,
) -> MarketDataSnapshot:
    """Return real-time market data for an instrument (§8.1)."""
    return MarketDataSnapshot.from_api(
        _get(
            "/rest/marketdata/get",
            marketId=market_id,
            symbol=symbol,
            entries=",".join(entries),
            depth=depth,
        )["marketData"]
    )


def get_trades(
    symbol: str,
    *,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    market_id: MarketId = "ROFX",
    environment: str | None = None,
) -> list[Trade]:
    """Return historical trades for an instrument (§8.4)."""
    return [
        Trade.from_api(t)
        for t in _get(
            "/rest/data/getTrades",
            marketId=market_id,
            symbol=symbol,
            date=date,
            dateFrom=date_from,
            dateTo=date_to,
            environment=environment,
        )["trades"]
    ]


# ------------------------------------------------------------------
# Risk API  (§9) — uses HTTP Basic Auth
# ------------------------------------------------------------------


def get_positions(account_name: str) -> list[Position]:
    """Return aggregated positions for an account (§9.1, HTTP Basic Auth)."""
    return [
        Position.from_api(p)
        for p in _request(
            "GET",
            f"/rest/risk/position/getPositions/{account_name}",
            auth_basic=_risk_auth(),
        )["positions"]
    ]


def get_detailed_positions(account_name: str) -> DetailedPosition:
    """Return trade-level detailed positions for an account (§9.2)."""
    return DetailedPosition.from_api(
        _request("GET", f"/rest/risk/detailedPosition/{account_name}", auth_basic=_risk_auth())
    )


def get_account_report(account_name: str) -> AccountReport:
    """Return the full account report (cash, margins, P&L) for an account (§9.3)."""
    return AccountReport.from_api(
        _request("GET", f"/rest/risk/accountReport/{account_name}", auth_basic=_risk_auth())
    )
