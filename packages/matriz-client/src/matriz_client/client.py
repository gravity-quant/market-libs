"""REST client for the MATBA ROFEX Primary API v1.21.

Phase 6 Plan 06 ships a ``Client`` class with the full sync REST surface plus
backwards-compatible top-level shims (``configure``, ``login``, ``get_*``,
``new_order``, ``replace_order``, ``cancel_order``, ``get_market_data``, …)
delegating to a lazy default singleton.

Auth modes:
- **Token** (default, most endpoints): obtained via ``POST /auth/getToken``
  and sent as ``X-Auth-Token`` on every subsequent request. The token is
  parsed from the *response header* ``X-Auth-Token`` (D-22), not the body.
- **HTTP Basic** (Risk API only): uses ``PRIMARY_USER``/``PRIMARY_PASSWORD``
  directly on each request.

Environment variables (loaded from ``.env`` via ``python-dotenv``):
- ``PRIMARY_USER`` — API username (required)
- ``PRIMARY_PASSWORD`` — API password (required)
- ``PRIMARY_BASE_URL`` — defaults to ``https://api.remarkets.primary.com.ar``

See :mod:`matriz_client.ws_client` for the WebSocket streaming counterpart.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any, Self

import httpx
from dotenv import load_dotenv

from matriz_client._state import _REQUEST_TIMEOUT, _TOKEN_TTL, _ClientState
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

__all__ = [
    "Client",
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
]


# ------------------------------------------------------------------
# Module-level helpers (stateless)
# ------------------------------------------------------------------


def _raise_for_response(resp: httpx.Response) -> None:
    """Map HTTP error status codes to typed exceptions.

    Centralized so both sync ``Client`` and (in Phase 10) ``AsyncClient`` can
    share the same error semantics (B8: do NOT duplicate in ``aio.py``).
    """
    resp.raise_for_status()


def _unwrap(data: dict[str, Any], key: str, endpoint: str) -> Any:
    """Return ``data[key]`` or raise ``PrimaryAPIError`` if missing.

    Surfaces a typed ``PrimaryAPIError`` (status ``"ERROR"``) when the Primary
    API response is missing the envelope key the wrapper expects. Without this
    guard, the caller would see an opaque ``KeyError`` that is not part of the
    client's documented exception contract (D-MATZ-9).
    """
    if key not in data:
        raise PrimaryAPIError(
            status="ERROR",
            description=f"missing envelope key '{key}' in response from {endpoint}",
            message=None,
        )
    return data[key]


# ------------------------------------------------------------------
# Client class
# ------------------------------------------------------------------


class Client:
    """Synchronous REST client for the MATBA ROFEX Primary API.

    Lazy auth: ``login()`` is called automatically on the first authenticated
    request and refreshed before the 24h server-side expiry.

    Args:
        base_url: Primary API base URL. Defaults to ``PRIMARY_BASE_URL`` env.
        username: ``PRIMARY_USER`` env override.
        password: ``PRIMARY_PASSWORD`` env override.
        token: Pre-existing token (useful for tests). If provided alongside
            ``token_expires_at`` in the future, ``_ensure_token()`` skips the
            login round-trip.
        token_expires_at: Unix timestamp at which the cached token expires.

    Example::

        with Client() as c:
            segments = c.get_segments()
    """

    __slots__ = ("_state",)

    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        token_expires_at: float | None = None,
    ) -> None:
        self._state = _ClientState()
        if base_url is not None:
            self._state.base_url = base_url.rstrip("/")
        if username is not None:
            self._state.username = username
        if password is not None:
            self._state.password = password
        if token is not None:
            self._state.token = token
        if token_expires_at is not None:
            self._state.token_expires_at = token_expires_at

    # -- Lifecycle ---------------------------------------------------

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Idempotently close the underlying HTTP client."""
        http_client = self._state.http_client
        if http_client is not None and isinstance(http_client, httpx.Client):
            http_client.close()
        self._state.http_client = None

    def __repr__(self) -> str:
        return (
            f"Client(base_url={self._state.base_url!r}, "
            f"username={self._state.username!r}, "
            f"password='***', "
            f"token='***')"
        )

    def __reduce__(self) -> Any:
        raise NotImplementedError(
            "matriz_client.Client is not picklable: it holds live HTTP/socket state"
        )

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        raise NotImplementedError(
            "matriz_client.Client cannot be deep-copied: it holds live HTTP/socket state"
        )

    # -- HTTP client lazy accessor ----------------------------------

    def _ensure_http_client(self) -> httpx.Client:
        """Return the persistent ``httpx.Client``; create lazily if needed."""
        existing = self._state.http_client
        if isinstance(existing, httpx.Client):
            return existing
        new = httpx.Client(timeout=_REQUEST_TIMEOUT)
        self._state.http_client = new
        return new

    # -- Auth -------------------------------------------------------

    def login(self) -> str:
        """Authenticate against ``/auth/getToken`` and cache the token.

        D-22: The Primary API returns the token in the ``X-Auth-Token``
        *response header*, NOT the JSON body. Raises ``AuthenticationError``
        if the header is missing or credentials are unset.
        """
        if not self._state.username or not self._state.password:
            raise AuthenticationError("ERROR", "PRIMARY_USER and PRIMARY_PASSWORD must be set")
        http = self._ensure_http_client()
        resp = http.post(
            f"{self._state.base_url}/auth/getToken",
            headers={
                "X-Username": self._state.username,
                "X-Password": self._state.password,
            },
        )
        _raise_for_response(resp)
        token = resp.headers.get("X-Auth-Token")
        if not isinstance(token, str) or not token:
            raise AuthenticationError("ERROR", "No X-Auth-Token header in response")
        self._state.token = token
        self._state.token_expires_at = time.time() + _TOKEN_TTL
        return token

    def _ensure_token(self) -> None:
        """Log in if there is no cached token or it is past expiry."""
        if self._state.token and time.time() < self._state.token_expires_at:
            return
        self.login()

    def _risk_auth(self) -> tuple[str, str]:
        """Return the (user, password) tuple for Risk API HTTP Basic Auth."""
        return (self._state.username, self._state.password)

    # -- Request plumbing -------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        auth_basic: tuple[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request and decode the JSON payload."""
        http = self._ensure_http_client()
        url = f"{self._state.base_url}{path}"
        if auth_basic:
            resp = http.request(
                method,
                url,
                params=params,
                auth=httpx.BasicAuth(*auth_basic),
            )
        else:
            self._ensure_token()
            if self._state.token is None:
                raise RuntimeError("matriz_client.client: _ensure_token() did not populate _token")
            resp = http.request(
                method,
                url,
                params=params,
                headers={"X-Auth-Token": self._state.token},
            )

        _raise_for_response(resp)
        raw = resp.json()
        if not isinstance(raw, dict):
            # Defense for CR-01: see prior comment in legacy module.
            raise PrimaryAPIError(
                status="ERROR",
                description=f"expected JSON object body at {path}, got {type(raw).__name__}",
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

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        clean = {k: v for k, v in params.items() if v is not None}
        return self._request("GET", path, params=clean)

    # -- Segments (§4) ----------------------------------------------

    def get_segments(self) -> list[Segment]:
        path = "/rest/segment/all"
        return [Segment.from_api(s) for s in _unwrap(self._get(path), "segments", path)]

    # -- Instruments (§5) -------------------------------------------

    def get_all_instruments(self) -> list[Instrument]:
        path = "/rest/instruments/all"
        return [Instrument.from_api(i) for i in _unwrap(self._get(path), "instruments", path)]

    def get_instruments_details(self) -> list[InstrumentDetail]:
        path = "/rest/instruments/details"
        return [InstrumentDetail.from_api(i) for i in _unwrap(self._get(path), "instruments", path)]

    def get_instrument_detail(self, symbol: str, market_id: MarketId = "ROFX") -> InstrumentDetail:
        path = "/rest/instruments/detail"
        return InstrumentDetail.from_api(
            _unwrap(self._get(path, symbol=symbol, marketId=market_id), "instrument", path)
        )

    def get_instruments_by_cfi(self, cfi_code: CFICode) -> list[Instrument]:
        path = "/rest/instruments/byCFICode"
        return [
            Instrument.from_api(i)
            for i in _unwrap(self._get(path, CFICode=cfi_code), "instruments", path)
        ]

    def get_instruments_by_segment(
        self, segment_id: SegmentId, market_id: MarketId = "ROFX"
    ) -> list[Instrument]:
        path = "/rest/instruments/bySegment"
        return [
            Instrument.from_api(i)
            for i in _unwrap(
                self._get(path, MarketSegmentID=segment_id, MarketID=market_id),
                "instruments",
                path,
            )
        ]

    # -- Orders (§6) ------------------------------------------------

    def new_order(
        self,
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
        path = "/rest/order/newSingleOrder"
        return NewOrderResponse.from_api(_unwrap(self._get(path, **params), "order", path))

    def replace_order(
        self, cl_ord_id: str, proprietary: str, qty: int, price: float
    ) -> NewOrderResponse:
        path = "/rest/order/replaceById"
        return NewOrderResponse.from_api(
            _unwrap(
                self._get(
                    path,
                    clOrdId=cl_ord_id,
                    proprietary=proprietary,
                    orderQty=qty,
                    price=price,
                ),
                "order",
                path,
            )
        )

    def cancel_order(self, cl_ord_id: str, proprietary: str) -> NewOrderResponse:
        path = "/rest/order/cancelById"
        return NewOrderResponse.from_api(
            _unwrap(
                self._get(path, clOrdId=cl_ord_id, proprietary=proprietary),
                "order",
                path,
            )
        )

    def get_order_status(self, cl_ord_id: str, proprietary: str) -> Order:
        path = "/rest/order/id"
        return Order.from_api(
            _unwrap(
                self._get(path, clOrdId=cl_ord_id, proprietary=proprietary),
                "order",
                path,
            )
        )

    def get_order_history(self, cl_ord_id: str, proprietary: str) -> list[Order]:
        path = "/rest/order/allById"
        return [
            Order.from_api(o)
            for o in _unwrap(
                self._get(path, clOrdId=cl_ord_id, proprietary=proprietary),
                "orders",
                path,
            )
        ]

    def get_active_orders(self, account_id: str) -> list[Order]:
        path = "/rest/order/actives"
        return [
            Order.from_api(o)
            for o in _unwrap(self._get(path, accountId=account_id), "orders", path)
        ]

    def get_filled_orders(self, account_id: str) -> list[Order]:
        path = "/rest/order/filleds"
        return [
            Order.from_api(o)
            for o in _unwrap(self._get(path, accountId=account_id), "orders", path)
        ]

    def get_all_orders(self, account_id: str) -> list[Order]:
        path = "/rest/order/all"
        return [
            Order.from_api(o)
            for o in _unwrap(self._get(path, accountId=account_id), "orders", path)
        ]

    def get_order_by_exec_id(self, exec_id: str) -> Order:
        path = "/rest/order/byExecId"
        return Order.from_api(_unwrap(self._get(path, execId=exec_id), "order", path))

    # -- Market Data (§8) -------------------------------------------

    def get_market_data(
        self,
        symbol: str,
        entries: Sequence[MarketDataEntry] = DEFAULT_MARKET_DATA_ENTRIES,
        *,
        market_id: MarketId = "ROFX",
        depth: int | None = None,
    ) -> MarketDataSnapshot:
        path = "/rest/marketdata/get"
        return MarketDataSnapshot.from_api(
            _unwrap(
                self._get(
                    path,
                    marketId=market_id,
                    symbol=symbol,
                    entries=",".join(entries),
                    depth=depth,
                ),
                "marketData",
                path,
            )
        )

    def get_trades(
        self,
        symbol: str,
        *,
        date: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        market_id: MarketId = "ROFX",
        environment: str | None = None,
    ) -> list[Trade]:
        path = "/rest/data/getTrades"
        return [
            Trade.from_api(t)
            for t in _unwrap(
                self._get(
                    path,
                    marketId=market_id,
                    symbol=symbol,
                    date=date,
                    dateFrom=date_from,
                    dateTo=date_to,
                    environment=environment,
                ),
                "trades",
                path,
            )
        ]

    # -- Risk API (§9) ----------------------------------------------

    def get_positions(self, account_name: str) -> list[Position]:
        path = f"/rest/risk/position/getPositions/{account_name}"
        return [
            Position.from_api(p)
            for p in _unwrap(
                self._request("GET", path, auth_basic=self._risk_auth()),
                "positions",
                path,
            )
        ]

    def get_detailed_positions(self, account_name: str) -> DetailedPosition:
        return DetailedPosition.from_api(
            self._request(
                "GET",
                f"/rest/risk/detailedPosition/{account_name}",
                auth_basic=self._risk_auth(),
            )
        )

    def get_account_report(self, account_name: str) -> AccountReport:
        return AccountReport.from_api(
            self._request(
                "GET",
                f"/rest/risk/accountReport/{account_name}",
                auth_basic=self._risk_auth(),
            )
        )


# ------------------------------------------------------------------
# Default-singleton shims (D-04 / D-13 / D-20)
# ------------------------------------------------------------------

_default_client: Client | None = None


def _get_default() -> Client:
    """Return the lazily-constructed default ``Client`` singleton."""
    global _default_client
    if _default_client is None:
        _default_client = Client()
    return _default_client


def configure(
    *,
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
    token_expires_at: float | None = None,
) -> None:
    """Sobrescribe credenciales/URL/token en runtime y resetea cache.

    D-04 extension: ``token`` and ``token_expires_at`` kwargs are accepted so
    test fixtures can pre-seed the cache without monkeypatching module state.
    Any base_url/username/password update without an explicit ``token`` resets
    the token cache to force re-auth.
    """
    default = _get_default()
    if base_url is not None:
        default._state.base_url = base_url.rstrip("/")
    if username is not None:
        default._state.username = username
    if password is not None:
        default._state.password = password
    # Token semantics: explicit override wins; otherwise base/cred changes
    # invalidate the cache.
    if token is not None or token_expires_at is not None:
        if token is not None:
            default._state.token = token
        if token_expires_at is not None:
            default._state.token_expires_at = token_expires_at
    elif base_url is not None or username is not None or password is not None:
        default._state.token = None
        default._state.token_expires_at = 0.0


def login() -> str:
    return _get_default().login()


# -- Top-level domain delegators -----------------------------------


def get_segments() -> list[Segment]:
    return _get_default().get_segments()


def get_all_instruments() -> list[Instrument]:
    return _get_default().get_all_instruments()


def get_instruments_details() -> list[InstrumentDetail]:
    return _get_default().get_instruments_details()


def get_instrument_detail(symbol: str, market_id: MarketId = "ROFX") -> InstrumentDetail:
    return _get_default().get_instrument_detail(symbol, market_id)


def get_instruments_by_cfi(cfi_code: CFICode) -> list[Instrument]:
    return _get_default().get_instruments_by_cfi(cfi_code)


def get_instruments_by_segment(
    segment_id: SegmentId, market_id: MarketId = "ROFX"
) -> list[Instrument]:
    return _get_default().get_instruments_by_segment(segment_id, market_id)


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
    return _get_default().new_order(
        symbol,
        side,
        qty,
        account,
        price,
        order_type=order_type,
        time_in_force=time_in_force,
        market_id=market_id,
        cancel_previous=cancel_previous,
        iceberg=iceberg,
        display_qty=display_qty,
        expire_date=expire_date,
    )


def replace_order(cl_ord_id: str, proprietary: str, qty: int, price: float) -> NewOrderResponse:
    return _get_default().replace_order(cl_ord_id, proprietary, qty, price)


def cancel_order(cl_ord_id: str, proprietary: str) -> NewOrderResponse:
    return _get_default().cancel_order(cl_ord_id, proprietary)


def get_order_status(cl_ord_id: str, proprietary: str) -> Order:
    return _get_default().get_order_status(cl_ord_id, proprietary)


def get_order_history(cl_ord_id: str, proprietary: str) -> list[Order]:
    return _get_default().get_order_history(cl_ord_id, proprietary)


def get_active_orders(account_id: str) -> list[Order]:
    return _get_default().get_active_orders(account_id)


def get_filled_orders(account_id: str) -> list[Order]:
    return _get_default().get_filled_orders(account_id)


def get_all_orders(account_id: str) -> list[Order]:
    return _get_default().get_all_orders(account_id)


def get_order_by_exec_id(exec_id: str) -> Order:
    return _get_default().get_order_by_exec_id(exec_id)


def get_market_data(
    symbol: str,
    entries: Sequence[MarketDataEntry] = DEFAULT_MARKET_DATA_ENTRIES,
    *,
    market_id: MarketId = "ROFX",
    depth: int | None = None,
) -> MarketDataSnapshot:
    return _get_default().get_market_data(symbol, entries, market_id=market_id, depth=depth)


def get_trades(
    symbol: str,
    *,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    market_id: MarketId = "ROFX",
    environment: str | None = None,
) -> list[Trade]:
    return _get_default().get_trades(
        symbol,
        date=date,
        date_from=date_from,
        date_to=date_to,
        market_id=market_id,
        environment=environment,
    )


def get_positions(account_name: str) -> list[Position]:
    return _get_default().get_positions(account_name)


def get_detailed_positions(account_name: str) -> DetailedPosition:
    return _get_default().get_detailed_positions(account_name)


def get_account_report(account_name: str) -> AccountReport:
    return _get_default().get_account_report(account_name)


# ------------------------------------------------------------------
# PEP 562 read-only shim (D-01, D-02, Open Q #4)
# ------------------------------------------------------------------

# Names whose reads forward to ``_get_default()._state.<attr>``.
_FORWARDED_TO_STATE: dict[str, str] = {
    "_token": "token",
    "_token_ts": "token_expires_at",
    "_base_url": "base_url",  # Open Q #4 — verification/mutation_gate.py reads this.
}

# Legacy HTTP client names that forward to ``_get_default()._state.http_client``.
# Matriz historically named the global ``_session`` (Pitfall #5); for parity
# with the other packages we also forward ``_client``.
_FORWARDED_HTTP_CLIENT_NAMES: frozenset[str] = frozenset({"_session", "_client"})


def __getattr__(name: str) -> Any:
    """PEP 562 read-only forwarding to the default Client's state.

    Writes are not supported through module attribute access; mutate via
    ``configure(...)`` instead. Reads of ``_user``/``_password`` raise
    ``AttributeError`` deliberately — credentials must never be observed
    through the legacy module global path (security hardening).
    """
    if name in _FORWARDED_TO_STATE:
        return getattr(_get_default()._state, _FORWARDED_TO_STATE[name])
    if name in _FORWARDED_HTTP_CLIENT_NAMES:
        return _get_default()._state.http_client
    raise AttributeError(f"module 'matriz_client.client' has no attribute {name!r}")
