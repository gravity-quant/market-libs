"""REST client for the MATBA ROFEX Primary API v1.21.

Phase 7 Plan 05 (REFAC-03 + CR-03 + CR-05) — transport shell delgado. Las
pure builders/parsers viven en ``matriz_client._core``; este módulo sólo
dispatcha HTTP y delega parsing.

Auth modes: ``X-Auth-Token`` (default) y HTTP Basic (Risk API §9).

D-04 alias preservation (B8 invariant, forward-compat con Phase 10 REFAC-04
matriz async REST): ``_raise_for_response = _core.raise_for_response`` y
``_unwrap = _core.unwrap`` referencian al mismo objeto que el (future)
``aio._raise_for_response`` → identidad preservada para tests B8.

Env vars: ``PRIMARY_USER``, ``PRIMARY_PASSWORD``, ``PRIMARY_BASE_URL``.

See :mod:`matriz_client.ws_client` for the WebSocket streaming counterpart.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Self

import httpx
from dotenv import load_dotenv

from matriz_client import _core, _transport
from matriz_client._core import RequestSpec
from matriz_client._state import _REQUEST_TIMEOUT, _ClientState
from matriz_client.exceptions import AuthenticationError
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

# D-04 aliases — preserve B8 identity (forward-compat con Phase 10 REFAC-04
# que destapará el async REST surface: ``aio._raise_for_response`` también
# referenciará ``_core.raise_for_response`` directamente).
_raise_for_response = _core.raise_for_response
_unwrap = _core.unwrap


class Client:
    """Synchronous REST client for the MATBA ROFEX Primary API.

    Lazy auth: ``login()`` is called automatically on the first authenticated
    request and refreshed before the 24h server-side expiry.

    Example::

        with Client() as c:
            segments = c.get_segments()
    """

    __slots__ = ("_max_retries", "_state")

    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        token_expires_at: float | None = None,
        max_retries: int = 2,
        http_client: httpx.Client | None = None,
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
        # Phase 8 D-15 / D-19: max_retries=N → max_attempts=N+1 (1 initial + N retries).
        # max_retries=0 disables retries entirely per D-19 (max_attempts <= 1 bypass).
        self._max_retries = max_retries
        # Phase 8 D-16: caller-supplied http_client used AS-IS (no auto-wrap).
        if http_client is not None:
            self._state.http_client = http_client

    # -- Lifecycle ---------------------------------------------------

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def close(self) -> None:
        http_client = self._state.http_client
        if http_client is not None and isinstance(http_client, httpx.Client):
            http_client.close()
        self._state.http_client = None

    def __repr__(self) -> str:
        return (
            f"Client(base_url={self._state.base_url!r}, "
            f"username={self._state.username!r}, "
            f"password='***', token='***')"
        )

    def __reduce__(self) -> Any:
        raise NotImplementedError(
            "matriz_client.Client is not picklable: it holds live HTTP/socket state"
        )

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        raise NotImplementedError(
            "matriz_client.Client cannot be deep-copied: it holds live HTTP/socket state"
        )

    # -- HTTP / auth -------------------------------------------------

    def _ensure_http_client(self) -> httpx.Client:
        """Crea ``httpx.Client`` lazy wrapping ``RetryTransport`` (Phase 8 D-15 / D-19).

        ``max_attempts = max_retries + 1`` per the anthropic/openai SDK semantics
        (D-19). The transport's mutation gate (D-01) honors
        ``request.extensions["idempotent"]`` so mutating builders pass through
        without retry (Pitfall 4 / D-24 — CRITICAL for matriz new_order).
        """
        existing = self._state.http_client
        if isinstance(existing, httpx.Client):
            return existing
        new = httpx.Client(
            timeout=_REQUEST_TIMEOUT,
            transport=_transport.RetryTransport(max_attempts=self._max_retries + 1),
        )
        self._state.http_client = new
        return new

    def login(self) -> str:
        """Authenticate via ``POST /auth/getToken`` (D-22: token en header).

        Phase 8 D-29: login goes through the RetryTransport with
        ``idempotent=True`` per D-03 (replay-safe — a fresh X-Auth-Token
        replaces the prior). Transient 5xx during auth retry via the transport;
        401 NEVER retries (handled by shell re-auth flow in ``_request()``).
        """
        spec = _core.build_login_request(self._state)
        http = self._ensure_http_client()
        request_id = uuid.uuid4().hex
        req = http.build_request(
            spec.method,
            f"{self._state.base_url}{spec.path}",
            headers=spec.headers,
        )
        req.extensions["idempotent"] = spec.idempotent
        req.extensions["request_id"] = request_id
        req.extensions["endpoint_name"] = spec.endpoint_name
        resp = http.send(req)
        token, expires_at = _core.parse_login_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        return token

    def _ensure_token(self) -> None:
        if _core.token_is_fresh(self._state):
            return
        self.login()

    def _risk_auth(self) -> tuple[str, str]:
        return (self._state.username, self._state.password)

    # -- Transport shell (D-03) --------------------------------------

    def _request(self, spec: RequestSpec) -> httpx.Response:
        """Dispatch HTTP, return raw ``httpx.Response``. Parsing en ``_core``.

        Phase 8 D-02 + D-11 + D-22 + D-23 + D-30 + RELY-04:

        - **Risk API path** (``spec.auth_basic is not None``): construct
          request with ``httpx.BasicAuth(*spec.auth_basic)``, propagate
          extensions for the transport (idempotent, request_id, endpoint_name,
          account_id, auth_basic for D-22 redaction) and SEND. **NO 401 re-auth
          per D-23** — auth_basic credentials are static; a re-auth would just
          re-send the same wrong basic header and infinite-loop.
        - **Token path** (X-Auth-Token): ensure token; build request; on 401
          (``AuthenticationError`` raised by ``_core.parse_envelope_response``
          via the per-method parsers), clear cached token, call
          ``_ensure_token()`` to re-login, retry request ONCE with refreshed
          ``X-Auth-Token`` header. ``AuthenticationError`` NEVER in
          ``retry_on=`` (D-07) — the transport sees only HTTP/transport
          signals.

        ``PrimaryAPIError`` (raised by ``parse_envelope_response`` on a 200-OK
        with ``status=="ERROR"``) is NOT caught here per D-24 — it propagates
        out and is NEVER retried by the transport (200-OK is not in the
        retryable status set; the application-level error is raised AFTER the
        transport returns).
        """
        http = self._ensure_http_client()
        url = f"{self._state.base_url}{spec.path}"
        request_id = uuid.uuid4().hex

        if spec.auth_basic is not None:
            # Risk API path — D-23: RetryTransport YES (idempotent=True for
            # Risk reads → 5xx retry-eable); 401 re-auth NO (static creds).
            req = http.build_request(spec.method, url, params=spec.params)
            req.extensions["idempotent"] = spec.idempotent
            req.extensions["request_id"] = request_id
            req.extensions["endpoint_name"] = spec.endpoint_name
            if spec.account_id is not None:
                req.extensions["account_id"] = spec.account_id
            # D-22 auth_basic propagation for log redaction (filter scans
            # extensions via the structured log record's __dict__).
            req.extensions["auth_basic"] = spec.auth_basic
            resp = http.send(req, auth=httpx.BasicAuth(*spec.auth_basic))
            if resp.status_code == 401:
                # WR-02 fix: consume the body BEFORE raising so the HTTP/2 stream
                # is closed (Phase 7 D-06 body-consume-then-raise hardening
                # applied to non-retryable carve-out paths). Without this read,
                # the unread stream leaks against the connection pool when
                # http2=True is enabled in the future.
                resp.read()
                # D-23: auth_basic 401 = invalid credentials. No re-auth (would
                # just re-send the same wrong basic header). Surface as typed
                # AuthError immediately.
                raise AuthenticationError(
                    "ERROR",
                    f"401 Unauthorized (Risk API, endpoint={spec.endpoint_name or spec.path})",
                )
            return resp

        # Token path — D-02 401 re-auth-once.
        self._ensure_token()
        if self._state.token is None:
            raise RuntimeError("matriz_client.client: _ensure_token() did not populate _token")
        headers = {"X-Auth-Token": self._state.token, **(spec.headers or {})}
        req = http.build_request(spec.method, url, params=spec.params, headers=headers)
        req.extensions["idempotent"] = spec.idempotent
        req.extensions["request_id"] = request_id
        req.extensions["endpoint_name"] = spec.endpoint_name
        if spec.account_id is not None:
            req.extensions["account_id"] = spec.account_id

        resp = http.send(req)
        if resp.status_code != 401:
            return resp

        # D-02 exactly-one re-auth: clear token, re-login, retry once.
        # D-23: this branch is gated on `spec.auth_basic is None` (Token path
        # only). Risk API auth_basic 401s are returned above without re-auth.
        self._state.token = None
        self._ensure_token()
        new_token = self._state.token
        if new_token is None:
            raise AuthenticationError(
                "ERROR", "_ensure_token() did not populate token after 401 re-auth"
            )
        req.headers["X-Auth-Token"] = new_token
        resp = http.send(req)
        if resp.status_code == 401:
            # WR-02 fix: body-consume-then-raise on the second 401 raise-site too.
            resp.read()
            # Second 401 — re-auth did not help; surface as typed AuthError.
            # No further retry (Pitfall 1 prevention — re-auth happens exactly once).
            raise AuthenticationError(
                "ERROR",
                f"401 Unauthorized after re-auth (endpoint={spec.endpoint_name or spec.path})",
            )
        return resp

    def _matriz_legacy_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        auth_basic: tuple[str, str] | None = None,
    ) -> dict[str, Any]:
        """DEPRECATED back-compat wrapper for ``main_matriz.py`` probes (Pitfall 7)."""
        spec = RequestSpec(method=method, path=path, params=params, auth_basic=auth_basic)
        resp = self._request(spec)
        return _core.parse_envelope_response(resp, path)

    # -- Segments (§4) ----------------------------------------------

    def get_segments(self) -> list[Segment]:
        return _core.parse_get_segments_response(
            self._request(_core.build_get_segments_request(self._state))
        )

    # -- Instruments (§5) -------------------------------------------

    def get_all_instruments(self) -> list[Instrument]:
        return _core.parse_get_all_instruments_response(
            self._request(_core.build_get_all_instruments_request(self._state))
        )

    def get_instruments_details(self) -> list[InstrumentDetail]:
        return _core.parse_get_instruments_details_response(
            self._request(_core.build_get_instruments_details_request(self._state))
        )

    def get_instrument_detail(self, symbol: str, market_id: MarketId = "ROFX") -> InstrumentDetail:
        return _core.parse_get_instrument_detail_response(
            self._request(_core.build_get_instrument_detail_request(self._state, symbol, market_id))
        )

    def get_instruments_by_cfi(self, cfi_code: CFICode) -> list[Instrument]:
        return _core.parse_get_instruments_by_cfi_response(
            self._request(_core.build_get_instruments_by_cfi_request(self._state, cfi_code))
        )

    def get_instruments_by_segment(
        self, segment_id: SegmentId, market_id: MarketId = "ROFX"
    ) -> list[Instrument]:
        return _core.parse_get_instruments_by_segment_response(
            self._request(
                _core.build_get_instruments_by_segment_request(self._state, segment_id, market_id)
            )
        )

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
        spec = _core.build_new_order_request(
            self._state,
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
        return _core.parse_new_order_response(self._request(spec))

    def replace_order(
        self, cl_ord_id: str, proprietary: str, qty: int, price: float
    ) -> NewOrderResponse:
        return _core.parse_replace_order_response(
            self._request(
                _core.build_replace_order_request(self._state, cl_ord_id, proprietary, qty, price)
            )
        )

    def cancel_order(self, cl_ord_id: str, proprietary: str) -> NewOrderResponse:
        return _core.parse_cancel_order_response(
            self._request(_core.build_cancel_order_request(self._state, cl_ord_id, proprietary))
        )

    def get_order_status(self, cl_ord_id: str, proprietary: str) -> Order:
        return _core.parse_get_order_status_response(
            self._request(_core.build_get_order_status_request(self._state, cl_ord_id, proprietary))
        )

    def get_order_history(self, cl_ord_id: str, proprietary: str) -> list[Order]:
        return _core.parse_get_order_history_response(
            self._request(
                _core.build_get_order_history_request(self._state, cl_ord_id, proprietary)
            )
        )

    def get_active_orders(self, account_id: str) -> list[Order]:
        return _core.parse_get_active_orders_response(
            self._request(_core.build_get_active_orders_request(self._state, account_id))
        )

    def get_filled_orders(self, account_id: str) -> list[Order]:
        return _core.parse_get_filled_orders_response(
            self._request(_core.build_get_filled_orders_request(self._state, account_id))
        )

    def get_all_orders(self, account_id: str) -> list[Order]:
        return _core.parse_get_all_orders_response(
            self._request(_core.build_get_all_orders_request(self._state, account_id))
        )

    def get_order_by_exec_id(self, exec_id: str) -> Order:
        return _core.parse_get_order_by_exec_id_response(
            self._request(_core.build_get_order_by_exec_id_request(self._state, exec_id))
        )

    # -- Market Data (§8) -------------------------------------------

    def get_market_data(
        self,
        symbol: str,
        entries: Sequence[MarketDataEntry] = DEFAULT_MARKET_DATA_ENTRIES,
        *,
        market_id: MarketId = "ROFX",
        depth: int | None = None,
    ) -> MarketDataSnapshot:
        return _core.parse_get_market_data_response(
            self._request(
                _core.build_get_market_data_request(
                    self._state, symbol, entries, market_id=market_id, depth=depth
                )
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
        return _core.parse_get_trades_response(
            self._request(
                _core.build_get_trades_request(
                    self._state,
                    symbol,
                    date=date,
                    date_from=date_from,
                    date_to=date_to,
                    market_id=market_id,
                    environment=environment,
                )
            )
        )

    # -- Risk API (§9) ----------------------------------------------

    def get_positions(self, account_name: str) -> list[Position]:
        return _core.parse_get_positions_response(
            self._request(_core.build_get_positions_request(self._state, account_name)),
            account_name,
        )

    def get_detailed_positions(self, account_name: str) -> DetailedPosition:
        return _core.parse_get_detailed_positions_response(
            self._request(_core.build_get_detailed_positions_request(self._state, account_name)),
            account_name,
        )

    def get_account_report(self, account_name: str) -> AccountReport:
        return _core.parse_get_account_report_response(
            self._request(_core.build_get_account_report_request(self._state, account_name)),
            account_name,
        )


# ------------------------------------------------------------------
# Default-singleton shims (D-04 / D-13 / D-20)
# ------------------------------------------------------------------

_default_client: Client | None = None


def _get_default() -> Client:
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
    max_retries: int | None = None,
    http_client: httpx.Client | None = None,
) -> None:
    """Sobrescribe credenciales/URL/token en runtime y resetea cache (D-04).

    Phase 8 D-15 / D-16 / D-19: ``max_retries`` (default 2; ``0`` disables
    retries entirely per D-19) and ``http_client`` (used AS-IS without
    auto-wrapping with ``RetryTransport`` per D-16) are runtime overrides on
    the default singleton. Changing ``max_retries`` triggers a transport
    rebuild on the next ``_ensure_http_client()`` call.
    """
    default = _get_default()
    if base_url is not None:
        default._state.base_url = base_url.rstrip("/")
    if username is not None:
        default._state.username = username
    if password is not None:
        default._state.password = password
    if token is not None or token_expires_at is not None:
        if token is not None:
            default._state.token = token
        if token_expires_at is not None:
            default._state.token_expires_at = token_expires_at
    elif base_url is not None or username is not None or password is not None:
        default._state.token = None
        default._state.token_expires_at = 0.0
    if max_retries is not None:
        # Close the cached httpx.Client so the next _ensure_http_client() call
        # rebuilds the RetryTransport with the new max_attempts (D-15).
        existing = default._state.http_client
        if isinstance(existing, httpx.Client):
            existing.close()
            default._state.http_client = None
        default._max_retries = max_retries
    if http_client is not None:
        # D-16: caller-supplied http_client used AS-IS — close the prior cached
        # client if any.
        existing = default._state.http_client
        if isinstance(existing, httpx.Client) and existing is not http_client:
            existing.close()
        default._state.http_client = http_client


def login() -> str:
    return _get_default().login()


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


# Module-level back-compat for ``main_matriz.py`` driver (Pitfall 7).


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    auth_basic: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """DEPRECATED: back-compat para `main_matriz.py`. Delega a ``_matriz_legacy_request``."""
    return _get_default()._matriz_legacy_request(method, path, params=params, auth_basic=auth_basic)


def _risk_auth() -> tuple[str, str]:
    return _get_default()._risk_auth()


# ------------------------------------------------------------------
# PEP 562 read-only shim (D-01, D-02, Open Q #4)
# ------------------------------------------------------------------

_FORWARDED_TO_STATE: dict[str, str] = {
    "_token": "token",
    "_token_ts": "token_expires_at",
    "_base_url": "base_url",
}
_FORWARDED_HTTP_CLIENT_NAMES: frozenset[str] = frozenset({"_session", "_client"})


def __getattr__(name: str) -> Any:
    """PEP 562 read-only forwarding. Writes via ``configure(...)`` only."""
    if name in _FORWARDED_TO_STATE:
        return getattr(_get_default()._state, _FORWARDED_TO_STATE[name])
    if name in _FORWARDED_HTTP_CLIENT_NAMES:
        return _get_default()._state.http_client
    raise AttributeError(f"module 'matriz_client.client' has no attribute {name!r}")
