"""Pure builders and parsers for the matriz REST client.

Phase 7 REFAC-03 + D-06 (CR-03 cierre body-consume-then-raise) + D-01 + D-02
+ D-04. NO imports from ``matriz_client.client`` or ``matriz_client.aio``
(enforced by ``import-linter`` contract in ``pyproject.toml``
``[tool.importlinter]``).

Todas las funciones públicas son puras: ``state`` in → ``RequestSpec`` o typed
result out. NO realizan I/O directo; el transport shell (``client.Client``)
ejecuta el HTTP call y delega el parsing en este módulo. La auth-flow primitiva
``build_login_request(state)``/``parse_login_response(resp)`` permite a
``client.Client.login()`` colapsar a un orchestrator 3-liner.

CR-03 (Plan 5 D-06) — orden CRÍTICO en cada parser que toca ``httpx.Response``:

  1. ``resp.read()``          ← consume body EXPLÍCITAMENTE (HTTP/2-safe)
  2. ``raise_for_response()`` ← mapea HTTP status → exception tipada
  3. ``resp.json()``          ← decode (may raise ValueError si malformed)
  4. Shape check + status==ERROR check
  5. ``return`` typed result

Si el body NO se consume antes de cualquier raise, futuro
``httpx.Client(http2=True)`` introduce stream leak en el connection pool (cada
raise sin read deja el stream abierto hasta GC). Ver tests/test_core.py
``test_parse_envelope_consumes_body_before_raise``.

Example::

    from matriz_client import _core
    from matriz_client._state import _ClientState

    state = _ClientState()
    spec = _core.build_get_segments_request(state)
    # ... transport shell ejecuta `http.request(spec.method, ..., spec.path, ...)` ...
    # resp = ...
    # data = _core.parse_envelope_response(resp, spec.path)
    # segments = [Segment.from_api(s) for s in _core.unwrap(data, "segments", spec.path)]
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from matriz_client._state import _TOKEN_TTL, _ClientState
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

__all__ = [
    "RequestSpec",
    "build_cancel_order_request",
    "build_get_account_report_request",
    "build_get_active_orders_request",
    "build_get_all_instruments_request",
    "build_get_all_orders_request",
    "build_get_detailed_positions_request",
    "build_get_filled_orders_request",
    "build_get_instrument_detail_request",
    "build_get_instruments_by_cfi_request",
    "build_get_instruments_by_segment_request",
    "build_get_instruments_details_request",
    "build_get_market_data_request",
    "build_get_order_by_exec_id_request",
    "build_get_order_history_request",
    "build_get_order_status_request",
    "build_get_positions_request",
    "build_get_segments_request",
    "build_get_trades_request",
    "build_login_request",
    "build_new_order_request",
    "build_replace_order_request",
    "parse_cancel_order_response",
    "parse_envelope_response",
    "parse_get_account_report_response",
    "parse_get_active_orders_response",
    "parse_get_all_instruments_response",
    "parse_get_all_orders_response",
    "parse_get_detailed_positions_response",
    "parse_get_filled_orders_response",
    "parse_get_instrument_detail_response",
    "parse_get_instruments_by_cfi_response",
    "parse_get_instruments_by_segment_response",
    "parse_get_instruments_details_response",
    "parse_get_market_data_response",
    "parse_get_order_by_exec_id_response",
    "parse_get_order_history_response",
    "parse_get_order_status_response",
    "parse_get_positions_response",
    "parse_get_segments_response",
    "parse_get_trades_response",
    "parse_login_response",
    "parse_new_order_response",
    "parse_replace_order_response",
    "raise_for_response",
    "token_is_fresh",
    "unwrap",
]


# --- RequestSpec --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RequestSpec:
    """Inmutable HTTP request specification — D-01 matriz shape.

    matriz tiene los fields más ricos del monorepo: ``auth_basic`` opcional
    para los 3 endpoints Risk (§9) que usan HTTP Basic en lugar del
    ``X-Auth-Token`` header. ``headers`` permite extras como el
    ``X-Username``/``X-Password`` del login.

    Phase 8 D-01/D-09/D-11 extensions (additive, back-compat preserving):

    - ``idempotent: bool = False`` — mutation gate per RELY-03. The shell
      ``_request()`` copies this to ``request.extensions["idempotent"]`` so
      the RetryTransport's gate sees it. **CRITICAL for matriz**:
      ``build_new_order_request`` / ``build_cancel_order_request`` /
      ``build_replace_order_request`` are HTTP GET (Primary API quirk) but
      MUST keep ``idempotent=False`` (default) to prevent duplicate-order
      risk on transient 503 (Pitfall 4 / D-24). GET builders that are truly
      idempotent (segments, instruments, orders read-only, market data, Risk
      reads) flip to ``True``. ``build_login_request`` is ``True`` per D-03
      (replay-safe — a fresh ``X-Auth-Token`` simply replaces the prior one).
    - ``endpoint_name: str = ""`` — symbolic name for structured log records.
      Set by builders (e.g. ``endpoint_name="get_segments"``); propagated via
      ``request.extensions["endpoint_name"]``.
    - ``account_id: str | None = None`` — D-11 propagation for log correlation.
      Builders that accept an ``account_id`` (Primary §6 active/filled/all
      orders) or ``account_name`` (Risk §9) populate this field; the shell
      ``_request()`` sets ``request.extensions["account_id"]`` only when
      non-None (no leak when caller didn't pass an account identifier).
    """

    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    auth_basic: tuple[str, str] | None = None
    # Phase 8 additions (additive, defaulted for back-compat with Phase 7).
    idempotent: bool = False
    endpoint_name: str = ""
    account_id: str | None = None


# --- Stateless helpers (D-04) -------------------------------------------


def raise_for_response(resp: httpx.Response) -> None:
    """Map HTTP error status codes to typed exceptions.

    D-04 alias preservation: ``client._raise_for_response =
    _core.raise_for_response`` mantiene B8 (forward-looking Phase 10
    ``aio._raise_for_response is client._raise_for_response``).
    """
    resp.raise_for_status()


def unwrap(data: dict[str, Any], key: str, endpoint: str) -> Any:
    """Return ``data[key]`` or raise ``PrimaryAPIError`` if missing.

    Surface a typed ``PrimaryAPIError`` (status ``"ERROR"``) cuando la
    Primary API response no trae el envelope key que el wrapper espera. Sin
    este guard, el caller vería un ``KeyError`` opaco fuera del contrato
    de excepciones del cliente (D-MATZ-9).
    """
    if key not in data:
        raise PrimaryAPIError(
            status="ERROR",
            description=f"missing envelope key '{key}' in response from {endpoint}",
            message=None,
        )
    return data[key]


def parse_envelope_response(resp: httpx.Response, endpoint: str) -> dict[str, Any]:
    """Body-consume-then-raise envelope parser — cierra CR-03 (Plan 5 D-06).

    Orden CRÍTICO:

      1. ``resp.read()``          ← consume body EXPLÍCITAMENTE (HTTP/2-safe)
      2. ``raise_for_response()`` ← mapea HTTP status
      3. ``resp.json()``          ← decode body
      4. Shape check (raw es dict)
      5. ``status == "ERROR"`` check
      6. ``return raw``

    Si el body NO se consume antes de cualquier raise, futuro
    ``httpx.Client(http2=True)`` introduce stream leak en el connection
    pool. Tests/test_core.py ``test_parse_envelope_consumes_body_before_raise``
    es el guard.
    """
    # CR-03 FIX (D-06): consume body EXPLICITLY antes de cualquier raise.
    resp.read()
    raise_for_response(resp)
    raw = resp.json()
    if not isinstance(raw, dict):
        raise PrimaryAPIError(
            status="ERROR",
            description=f"expected JSON object body at {endpoint}, got {type(raw).__name__}",
            message=None,
        )
    data: dict[str, Any] = raw
    if data.get("status") == "ERROR":
        raise PrimaryAPIError(
            status="ERROR",
            description=data.get("description"),
            message=data.get("message"),
        )
    return data


def _parse_risk_response(resp: httpx.Response, endpoint: str) -> dict[str, Any]:
    """Risk API parser — payload raíz ES el resultado (NO envelope key, D-07).

    Mismo orden CR-03 que ``parse_envelope_response`` pero sin envelope
    unwrap: ``DetailedPosition`` / ``AccountReport`` se construyen
    directamente con ``Model.from_api(raw)``.
    """
    resp.read()
    raise_for_response(resp)
    raw = resp.json()
    if not isinstance(raw, dict):
        raise PrimaryAPIError(
            status="ERROR",
            description=f"expected JSON object body at {endpoint}, got {type(raw).__name__}",
            message=None,
        )
    data: dict[str, Any] = raw
    if data.get("status") == "ERROR":
        raise PrimaryAPIError(
            status="ERROR",
            description=data.get("description"),
            message=data.get("message"),
        )
    return data


# --- Auth flow primitives (D-02) ----------------------------------------


def token_is_fresh(state: _ClientState) -> bool:
    """Pure freshness check — no I/O. Transport shell usa esto en _ensure_token."""
    return bool(state.token and time.time() < state.token_expires_at)


def build_login_request(state: _ClientState) -> RequestSpec:
    """Emite RequestSpec para ``POST /auth/getToken`` con headers de credenciales.

    Primary API mandate (D-22 Phase 6): credenciales viajan en headers
    ``X-Username`` / ``X-Password`` (NO en form body ni JSON). El token se
    extrae del response header ``X-Auth-Token`` por ``parse_login_response``.
    """
    if not state.username or not state.password:
        raise AuthenticationError("ERROR", "PRIMARY_USER and PRIMARY_PASSWORD must be set")
    return RequestSpec(
        method="POST",
        path="/auth/getToken",
        headers={
            "X-Username": state.username,
            "X-Password": state.password,
        },
        # D-03: login is replay-safe (a fresh X-Auth-Token replaces the prior);
        # marked idempotent=True so transient 5xx during auth retry via the
        # RetryTransport. 401 still NEVER retries — handled by shell re-auth.
        idempotent=True,
        endpoint_name="login",
    )


def parse_login_response(resp: httpx.Response) -> tuple[str, float]:
    """Parse login response — token en ``X-Auth-Token`` header (D-22 Phase 6).

    Returns:
        Tupla ``(token, expires_at_epoch)``. Caller (transport shell) escribe
        a ``state.token`` y ``state.token_expires_at``.

    Raises:
        AuthenticationError: si el header ``X-Auth-Token`` está ausente o vacío.
    """
    # CR-03 order: read body before raise.
    resp.read()
    raise_for_response(resp)
    token = resp.headers.get("X-Auth-Token")
    if not isinstance(token, str) or not token:
        raise AuthenticationError("ERROR", "No X-Auth-Token header in response")
    expires_at = time.time() + _TOKEN_TTL
    return token, expires_at


# --- §4 Segments --------------------------------------------------------


def build_get_segments_request(state: _ClientState) -> RequestSpec:
    """``GET /rest/segment/all`` — listar todos los market segments."""
    return RequestSpec(
        method="GET",
        path="/rest/segment/all",
        idempotent=True,
        endpoint_name="get_segments",
    )


def parse_get_segments_response(resp: httpx.Response) -> list[Segment]:
    """Parse envelope ``{segments: [...]}`` → ``list[Segment]``."""
    path = "/rest/segment/all"
    data = parse_envelope_response(resp, path)
    return [Segment.from_api(s) for s in unwrap(data, "segments", path)]


# --- §5 Instruments -----------------------------------------------------


def build_get_all_instruments_request(state: _ClientState) -> RequestSpec:
    """``GET /rest/instruments/all`` — listar todos los instrumentos."""
    return RequestSpec(
        method="GET",
        path="/rest/instruments/all",
        idempotent=True,
        endpoint_name="get_all_instruments",
    )


def parse_get_all_instruments_response(resp: httpx.Response) -> list[Instrument]:
    """Parse envelope ``{instruments: [...]}`` → ``list[Instrument]``."""
    path = "/rest/instruments/all"
    data = parse_envelope_response(resp, path)
    return [Instrument.from_api(i) for i in unwrap(data, "instruments", path)]


def build_get_instruments_details_request(state: _ClientState) -> RequestSpec:
    """``GET /rest/instruments/details`` — detalles de todos los instrumentos."""
    return RequestSpec(
        method="GET",
        path="/rest/instruments/details",
        idempotent=True,
        endpoint_name="get_instruments_details",
    )


def parse_get_instruments_details_response(resp: httpx.Response) -> list[InstrumentDetail]:
    """Parse envelope ``{instruments: [...]}`` → ``list[InstrumentDetail]``."""
    path = "/rest/instruments/details"
    data = parse_envelope_response(resp, path)
    return [InstrumentDetail.from_api(i) for i in unwrap(data, "instruments", path)]


def build_get_instrument_detail_request(
    state: _ClientState,
    symbol: str,
    market_id: MarketId = "ROFX",
) -> RequestSpec:
    """``GET /rest/instruments/detail?symbol=...&marketId=...``."""
    return RequestSpec(
        method="GET",
        path="/rest/instruments/detail",
        params={"symbol": symbol, "marketId": market_id},
        idempotent=True,
        endpoint_name="get_instrument_detail",
    )


def parse_get_instrument_detail_response(resp: httpx.Response) -> InstrumentDetail:
    """Parse envelope ``{instrument: {...}}`` → ``InstrumentDetail``."""
    path = "/rest/instruments/detail"
    data = parse_envelope_response(resp, path)
    return InstrumentDetail.from_api(unwrap(data, "instrument", path))


def build_get_instruments_by_cfi_request(
    state: _ClientState,
    cfi_code: CFICode,
) -> RequestSpec:
    """``GET /rest/instruments/byCFICode?CFICode=...``."""
    return RequestSpec(
        method="GET",
        path="/rest/instruments/byCFICode",
        params={"CFICode": cfi_code},
        idempotent=True,
        endpoint_name="get_instruments_by_cfi",
    )


def parse_get_instruments_by_cfi_response(resp: httpx.Response) -> list[Instrument]:
    """Parse envelope ``{instruments: [...]}`` → ``list[Instrument]``."""
    path = "/rest/instruments/byCFICode"
    data = parse_envelope_response(resp, path)
    return [Instrument.from_api(i) for i in unwrap(data, "instruments", path)]


def build_get_instruments_by_segment_request(
    state: _ClientState,
    segment_id: SegmentId,
    market_id: MarketId = "ROFX",
) -> RequestSpec:
    """``GET /rest/instruments/bySegment?MarketSegmentID=...&MarketID=...``."""
    return RequestSpec(
        method="GET",
        path="/rest/instruments/bySegment",
        params={"MarketSegmentID": segment_id, "MarketID": market_id},
        idempotent=True,
        endpoint_name="get_instruments_by_segment",
    )


def parse_get_instruments_by_segment_response(resp: httpx.Response) -> list[Instrument]:
    """Parse envelope ``{instruments: [...]}`` → ``list[Instrument]``."""
    path = "/rest/instruments/bySegment"
    data = parse_envelope_response(resp, path)
    return [Instrument.from_api(i) for i in unwrap(data, "instruments", path)]


# --- §6 Orders ----------------------------------------------------------


def build_new_order_request(
    state: _ClientState,
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
) -> RequestSpec:
    """``GET /rest/order/newSingleOrder`` con todos los params canonicales."""
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
    # Pitfall 4 / D-01 / D-24 CRITICAL: HTTP GET (Primary API quirk) but
    # idempotent=False (default — explicitly kept) to prevent duplicate-order
    # risk on transient 503. The RetryTransport mutation gate honors this.
    return RequestSpec(
        method="GET",
        path="/rest/order/newSingleOrder",
        params=params,
        idempotent=False,
        endpoint_name="new_order",
        account_id=account,
    )


def parse_new_order_response(resp: httpx.Response) -> NewOrderResponse:
    """Parse envelope ``{order: {clientId, proprietary}}`` → ``NewOrderResponse``."""
    path = "/rest/order/newSingleOrder"
    data = parse_envelope_response(resp, path)
    return NewOrderResponse.from_api(unwrap(data, "order", path))


def build_replace_order_request(
    state: _ClientState,
    cl_ord_id: str,
    proprietary: str,
    qty: int,
    price: float,
) -> RequestSpec:
    """``GET /rest/order/replaceById?clOrdId=...&proprietary=...&orderQty=...&price=...``.

    Pitfall 4 / D-01 / D-24: HTTP GET (Primary quirk) but ``idempotent=False``
    — replacing an order is a mutation; retry on 503 risks duplicate replaces.
    """
    return RequestSpec(
        method="GET",
        path="/rest/order/replaceById",
        params={
            "clOrdId": cl_ord_id,
            "proprietary": proprietary,
            "orderQty": qty,
            "price": price,
        },
        idempotent=False,
        endpoint_name="replace_order",
    )


def parse_replace_order_response(resp: httpx.Response) -> NewOrderResponse:
    """Parse envelope ``{order: {...}}`` → ``NewOrderResponse``."""
    path = "/rest/order/replaceById"
    data = parse_envelope_response(resp, path)
    return NewOrderResponse.from_api(unwrap(data, "order", path))


def build_cancel_order_request(
    state: _ClientState,
    cl_ord_id: str,
    proprietary: str,
) -> RequestSpec:
    """``GET /rest/order/cancelById?clOrdId=...&proprietary=...``.

    Pitfall 4 / D-01 / D-24: HTTP GET (Primary quirk) but ``idempotent=False``
    — cancel is a mutation; while a retried cancel on an already-cancelled
    order is harmless, we keep the gate explicit for uniformity with new/replace
    and resilience against future Primary API semantic changes.
    """
    return RequestSpec(
        method="GET",
        path="/rest/order/cancelById",
        params={"clOrdId": cl_ord_id, "proprietary": proprietary},
        idempotent=False,
        endpoint_name="cancel_order",
    )


def parse_cancel_order_response(resp: httpx.Response) -> NewOrderResponse:
    """Parse envelope ``{order: {...}}`` → ``NewOrderResponse``."""
    path = "/rest/order/cancelById"
    data = parse_envelope_response(resp, path)
    return NewOrderResponse.from_api(unwrap(data, "order", path))


def build_get_order_status_request(
    state: _ClientState,
    cl_ord_id: str,
    proprietary: str,
) -> RequestSpec:
    """``GET /rest/order/id?clOrdId=...&proprietary=...``."""
    return RequestSpec(
        method="GET",
        path="/rest/order/id",
        params={"clOrdId": cl_ord_id, "proprietary": proprietary},
        idempotent=True,
        endpoint_name="get_order_status",
    )


def parse_get_order_status_response(resp: httpx.Response) -> Order:
    """Parse envelope ``{order: {...}}`` → ``Order``."""
    path = "/rest/order/id"
    data = parse_envelope_response(resp, path)
    return Order.from_api(unwrap(data, "order", path))


def build_get_order_history_request(
    state: _ClientState,
    cl_ord_id: str,
    proprietary: str,
) -> RequestSpec:
    """``GET /rest/order/allById?clOrdId=...&proprietary=...``."""
    return RequestSpec(
        method="GET",
        path="/rest/order/allById",
        params={"clOrdId": cl_ord_id, "proprietary": proprietary},
        idempotent=True,
        endpoint_name="get_order_history",
    )


def parse_get_order_history_response(resp: httpx.Response) -> list[Order]:
    """Parse envelope ``{orders: [...]}`` → ``list[Order]``."""
    path = "/rest/order/allById"
    data = parse_envelope_response(resp, path)
    return [Order.from_api(o) for o in unwrap(data, "orders", path)]


def build_get_active_orders_request(
    state: _ClientState,
    account_id: str,
) -> RequestSpec:
    """``GET /rest/order/actives?accountId=...``."""
    return RequestSpec(
        method="GET",
        path="/rest/order/actives",
        params={"accountId": account_id},
        idempotent=True,
        endpoint_name="get_active_orders",
        account_id=account_id,
    )


def parse_get_active_orders_response(resp: httpx.Response) -> list[Order]:
    """Parse envelope ``{orders: [...]}`` → ``list[Order]``."""
    path = "/rest/order/actives"
    data = parse_envelope_response(resp, path)
    return [Order.from_api(o) for o in unwrap(data, "orders", path)]


def build_get_filled_orders_request(
    state: _ClientState,
    account_id: str,
) -> RequestSpec:
    """``GET /rest/order/filleds?accountId=...``."""
    return RequestSpec(
        method="GET",
        path="/rest/order/filleds",
        params={"accountId": account_id},
        idempotent=True,
        endpoint_name="get_filled_orders",
        account_id=account_id,
    )


def parse_get_filled_orders_response(resp: httpx.Response) -> list[Order]:
    """Parse envelope ``{orders: [...]}`` → ``list[Order]``."""
    path = "/rest/order/filleds"
    data = parse_envelope_response(resp, path)
    return [Order.from_api(o) for o in unwrap(data, "orders", path)]


def build_get_all_orders_request(
    state: _ClientState,
    account_id: str,
) -> RequestSpec:
    """``GET /rest/order/all?accountId=...``."""
    return RequestSpec(
        method="GET",
        path="/rest/order/all",
        params={"accountId": account_id},
        idempotent=True,
        endpoint_name="get_all_orders",
        account_id=account_id,
    )


def parse_get_all_orders_response(resp: httpx.Response) -> list[Order]:
    """Parse envelope ``{orders: [...]}`` → ``list[Order]``."""
    path = "/rest/order/all"
    data = parse_envelope_response(resp, path)
    return [Order.from_api(o) for o in unwrap(data, "orders", path)]


def build_get_order_by_exec_id_request(
    state: _ClientState,
    exec_id: str,
) -> RequestSpec:
    """``GET /rest/order/byExecId?execId=...``."""
    return RequestSpec(
        method="GET",
        path="/rest/order/byExecId",
        params={"execId": exec_id},
        idempotent=True,
        endpoint_name="get_order_by_exec_id",
    )


def parse_get_order_by_exec_id_response(resp: httpx.Response) -> Order:
    """Parse envelope ``{order: {...}}`` → ``Order``."""
    path = "/rest/order/byExecId"
    data = parse_envelope_response(resp, path)
    return Order.from_api(unwrap(data, "order", path))


# --- §7 Market Data -----------------------------------------------------


def build_get_market_data_request(
    state: _ClientState,
    symbol: str,
    entries: Sequence[MarketDataEntry] = DEFAULT_MARKET_DATA_ENTRIES,
    *,
    market_id: MarketId = "ROFX",
    depth: int | None = None,
) -> RequestSpec:
    """``GET /rest/marketdata/get?marketId=...&symbol=...&entries=...[&depth=...]``."""
    params: dict[str, Any] = {
        "marketId": market_id,
        "symbol": symbol,
        "entries": ",".join(entries),
    }
    if depth is not None:
        params["depth"] = depth
    return RequestSpec(
        method="GET",
        path="/rest/marketdata/get",
        params=params,
        idempotent=True,
        endpoint_name="get_market_data",
    )


def parse_get_market_data_response(resp: httpx.Response) -> MarketDataSnapshot:
    """Parse envelope ``{marketData: {...}}`` → ``MarketDataSnapshot``."""
    path = "/rest/marketdata/get"
    data = parse_envelope_response(resp, path)
    return MarketDataSnapshot.from_api(unwrap(data, "marketData", path))


def build_get_trades_request(
    state: _ClientState,
    symbol: str,
    *,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    market_id: MarketId = "ROFX",
    environment: str | None = None,
) -> RequestSpec:
    """``GET /rest/data/getTrades`` con params canonicales."""
    params: dict[str, Any] = {
        "marketId": market_id,
        "symbol": symbol,
    }
    if date is not None:
        params["date"] = date
    if date_from is not None:
        params["dateFrom"] = date_from
    if date_to is not None:
        params["dateTo"] = date_to
    if environment is not None:
        params["environment"] = environment
    return RequestSpec(
        method="GET",
        path="/rest/data/getTrades",
        params=params,
        idempotent=True,
        endpoint_name="get_trades",
    )


def parse_get_trades_response(resp: httpx.Response) -> list[Trade]:
    """Parse envelope ``{trades: [...]}`` → ``list[Trade]``."""
    path = "/rest/data/getTrades"
    data = parse_envelope_response(resp, path)
    return [Trade.from_api(t) for t in unwrap(data, "trades", path)]


# --- §9 Risk (HTTP Basic Auth — envelope_key applies via _unwrap for get_positions) ---


def build_get_positions_request(
    state: _ClientState,
    account_name: str,
) -> RequestSpec:
    """``GET /rest/risk/position/getPositions/{account_name}`` con HTTP Basic Auth (D-07).

    Risk API §9 NO usa ``X-Auth-Token`` — usa ``Authorization: Basic`` con
    las creds raw. ``auth_basic=(state.username, state.password)`` instruye
    al transport shell a usar ``httpx.BasicAuth(...)``.
    """
    return RequestSpec(
        method="GET",
        path=f"/rest/risk/position/getPositions/{account_name}",
        auth_basic=(state.username, state.password),
        # D-23: Risk reads are idempotent GETs → RetryTransport on 5xx YES;
        # 401 re-auth is handled differently in the shell (no re-auth for
        # auth_basic path because the basic creds are static — a re-auth would
        # just re-send the same wrong basic header).
        idempotent=True,
        endpoint_name="get_positions",
        account_id=account_name,
    )


def parse_get_positions_response(resp: httpx.Response, account_name: str) -> list[Position]:
    """Parse envelope ``{positions: [...]}`` → ``list[Position]``."""
    path = f"/rest/risk/position/getPositions/{account_name}"
    data = parse_envelope_response(resp, path)
    return [Position.from_api(p) for p in unwrap(data, "positions", path)]


def build_get_detailed_positions_request(
    state: _ClientState,
    account_name: str,
) -> RequestSpec:
    """``GET /rest/risk/detailedPosition/{account_name}`` con HTTP Basic Auth (D-07).

    Risk §9.2 sin envelope key — payload raíz ES el resultado.
    """
    return RequestSpec(
        method="GET",
        path=f"/rest/risk/detailedPosition/{account_name}",
        auth_basic=(state.username, state.password),
        # D-23: same Risk semantics as get_positions.
        idempotent=True,
        endpoint_name="get_detailed_positions",
        account_id=account_name,
    )


def parse_get_detailed_positions_response(
    resp: httpx.Response, account_name: str
) -> DetailedPosition:
    """Parse risk payload raíz (NO envelope key, D-07) → ``DetailedPosition``."""
    path = f"/rest/risk/detailedPosition/{account_name}"
    raw = _parse_risk_response(resp, path)
    return DetailedPosition.from_api(raw)


def build_get_account_report_request(
    state: _ClientState,
    account_name: str,
) -> RequestSpec:
    """``GET /rest/risk/accountReport/{account_name}`` con HTTP Basic Auth (D-07).

    Risk §9.3 sin envelope key — payload raíz ES el resultado.
    """
    return RequestSpec(
        method="GET",
        path=f"/rest/risk/accountReport/{account_name}",
        auth_basic=(state.username, state.password),
        # D-23: same Risk semantics as get_positions.
        idempotent=True,
        endpoint_name="get_account_report",
        account_id=account_name,
    )


def parse_get_account_report_response(resp: httpx.Response, account_name: str) -> AccountReport:
    """Parse risk payload raíz (NO envelope key, D-07) → ``AccountReport``."""
    path = f"/rest/risk/accountReport/{account_name}"
    raw = _parse_risk_response(resp, path)
    return AccountReport.from_api(raw)
