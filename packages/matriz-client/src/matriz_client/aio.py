"""matriz_client.aio — async REST mirror of matriz_client.client (Phase 10 REFAC-04).

API a nivel módulo (back-compat con el stub Phase 6 Plan 06)::

    from matriz_client import aio

    await aio.login()
    segments = await aio.get_segments()
    await aio.aclose()

API basada en clase (Phase 10 Plan 10-02)::

    from matriz_client import AsyncClient

    async with AsyncClient(username="op", password="secret") as c:
        positions = await c.get_positions("ACC-1")

El módulo expone un shim PEP 562 (read-only) que forwarda lecturas legacy de
``_token``, ``_token_expires_at``, ``_base_url`` y ``_client`` al
``_default_async_client._state.*``. Esto cierra el contrato de back-compat
para callers que migraban del stub Plan 06 al surface completo Plan 10-02.

Cleanup contract (D-16): caller-responsible. ``AsyncClient`` implementa
``aclose()`` + ``__aenter__/__aexit__``. NO hay ``atexit`` ni ``__del__``-driven
cleanup (Pitfall 12). NO se llama ``load_dotenv()`` acá — eso vive en
``client.py`` y se ejecuta como side effect del import del workspace.

B8 lock-in (D-04): ``_raise_for_response`` se importa desde
``matriz_client._core`` — NO se duplica. Mismo objeto que en ``client.py``,
así el invariante ``aio._raise_for_response is client._raise_for_response is
_core.raise_for_response`` se preserva.

Phase 10 Plan 10-03 REFAC-04 — 3-way TokenStore wiring:

- TokenStore vive en ``self._state.token_store`` (NEW field, Plan 10-03 adds
  to ``_ClientState``). Sync ``Client``, async ``AsyncClient`` y ``ws_client``
  daemon thread comparten esta única instancia (lazy init via
  ``build_token_store(state, max_retries=...)``).
- Plan 10-02 per-instance stashes ELIMINADAS: no quedan slots auxiliares en
  la clase. La async path reusa el sync default ``Client``'s
  ``_state.http_client`` para satisfacer el requisito de ``MatrizRefresh``
  de un sync ``httpx.Client`` (corre dentro de ``asyncio.to_thread``).
"""

from __future__ import annotations

import time
import uuid
import warnings
from collections.abc import Sequence
from typing import Any, Self

import httpx

from matriz_client import _atransport, _core
from matriz_client._core import RequestSpec

# B8 (D-04): import the shared, stateless helper from _core (NOT from
# client.py). Explicit ``as _raise_for_response`` satisfies mypy strict
# ``implicit_reexport=False``.
from matriz_client._core import raise_for_response as _raise_for_response
from matriz_client._state import _REQUEST_TIMEOUT, _ClientState
from matriz_client._token_store import build_token_store
from matriz_client.client import _validate_max_retries
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

# Suppress ruff F401 for the deliberate re-export alias (consumed by tests
# via ``from matriz_client.aio import _raise_for_response``).
_ = _raise_for_response


__all__ = [
    "_raise_for_response",
    "AsyncClient",
    "aclose",
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


class AsyncClient:
    """Async REST client for the MATBA ROFEX Primary API.

    Per-instance state lives in ``self._state`` (same ``_ClientState`` shape
    as the sync ``Client``, but a different INSTANCE — NO shared mutable state
    between sync and async surfaces by construction). Phase 10 Plan 10-03 adds
    ``self._state.token_store`` (NEW field on ``_ClientState``) so the sync
    ``Client``, this async ``AsyncClient``, and the ``ws_client`` daemon thread
    can converge on a single TokenStore instance per their own ``_state``.

    Pickle / deepcopy contract: NOT supported (``httpx.AsyncClient`` owns a TCP
    pool + SSL context tied to a specific event loop).

    Cleanup contract (D-16): caller-responsible. Use ``async with`` or
    ``await client.aclose()``.
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
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        # WR-06 (Phase 8 mirror): validate max_retries early.
        _validate_max_retries(max_retries)
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
        # Phase 8 D-15 / D-19: max_retries=N → max_attempts=N+1.
        self._max_retries = max_retries
        # Phase 8 D-16: caller-supplied http_client used AS-IS.
        if http_client is not None:
            self._state.http_client = http_client
        # Phase 10 Plan 10-03: TokenStore lazy-init via build_token_store on
        # first _aensure_token() call; lives on self._state.token_store (NEW
        # field). No per-instance stash slots — sync, async and ws_client
        # daemon thread all share state.token_store per state instance.

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Release the underlying ``httpx.AsyncClient`` (idempotent).

        Phase 10 Plan 10-03: also clears ``self._state.token_store`` so the
        next ``AsyncClient`` instance does NOT inherit a stale TokenStore
        tied to old credentials/transport. The TokenStore itself holds no
        socket resources, so there is no async cleanup required for the
        store — just drop the reference.
        """
        http_client = self._state.http_client
        if http_client is not None and isinstance(http_client, httpx.AsyncClient):
            await http_client.aclose()
            self._state.http_client = None
        self._state.token_store = None

    def __repr__(self) -> str:
        password_repr = "'***'" if self._state.password else "''"
        token_repr = "'***'" if self._state.token else "None"
        return (
            f"AsyncClient(base_url={self._state.base_url!r}, "
            f"username={self._state.username!r}, "
            f"password={password_repr}, "
            f"token={token_repr})"
        )

    def __reduce__(self) -> Any:
        raise TypeError(
            "matriz_client.aio.AsyncClient is not picklable: httpx.AsyncClient "
            "owns a TCP pool + SSL context bound to an event loop."
        )

    def __deepcopy__(self, memo: dict[int, Any]) -> AsyncClient:
        raise TypeError(
            "matriz_client.aio.AsyncClient is not deepcopy-safe (httpx.AsyncClient "
            "owns TCP pool + SSL context). Recreate from configure() in the "
            "target context instead."
        )

    # ------------------------------------------------------------------
    # HTTP transport + token auth (async)
    # ------------------------------------------------------------------

    async def _ensure_http_client(self) -> httpx.AsyncClient:
        """Lazily create the per-instance ``httpx.AsyncClient`` with AsyncRetryTransport.

        Phase 10 Plan 10-02: NO per-loop ``asyncio.Lock`` needed because
        TokenStore (Plan 10-01) owns refresh locking for the token path, and
        the http_client itself is created once and reused (httpx.AsyncClient
        is thread-/coroutine-safe for concurrent sends per httpx docs).
        """
        existing = self._state.http_client
        if isinstance(existing, httpx.AsyncClient):
            return existing
        new_client = httpx.AsyncClient(
            timeout=_REQUEST_TIMEOUT,
            transport=_atransport.AsyncRetryTransport(max_attempts=self._max_retries + 1),
        )
        self._state.http_client = new_client
        return new_client

    async def _aensure_token(self) -> None:
        """Ensure ``self._state.token`` is fresh via ``state.token_store.get_async()``.

        Phase 10 Plan 10-03 REFAC-04 — migrated from Plan 10-02 per-instance
        stash to the shared ``self._state.token_store`` (NEW field on
        ``_ClientState``). This converges sync REST + async REST + ws_client
        daemon on a single TokenStore per state instance.

        Flow:

        1. Fast path: if the cached token in ``self._state`` is still fresh
           (per ``_core.token_is_fresh``), short-circuit. Honors the legacy
           ``configure(token=..., token_expires_at=...)`` pre-seed contract.
        2. Ensure the async ``httpx.AsyncClient`` exists (transport for the
           main request path is unaffected by the store).
        3. Lazy-init ``self._state.token_store`` via ``build_token_store``.
           The factory wires ``MatrizRefresh`` which requires a SYNC
           ``httpx.Client`` (refresh runs inside ``asyncio.to_thread``). We
           reuse the SYNC default ``Client``'s ``_state.http_client`` for
           that purpose via a temporary swap of ``self._state.http_client``.
        4. ``await self._state.token_store.get_async()`` (3-way safe per
           Spike 001c) and mirror the result back to ``state.token``.
        """
        await self._ensure_http_client()
        # Fast path — preserves the configure(token=...) pre-seed contract
        # used by both the sync ``Client._ensure_token`` mirror and the test
        # conftest fixtures.
        if _core.token_is_fresh(self._state):
            return
        if self._state.token_store is None:
            # ``MatrizRefresh`` needs a sync ``httpx.Client``; reuse the sync
            # default ``Client``'s ``_state.http_client`` via the cross-surface
            # state. The refresh runs inside ``asyncio.to_thread`` (TokenStore
            # ``get_async`` path), so a sync ``httpx.Client`` is safe there.
            from matriz_client.client import _get_default as _get_sync_default

            sync_default = _get_sync_default()
            sync_default._ensure_http_client()
            saved_http_client = self._state.http_client
            # CONCURRENCY INVARIANT (per-loop asyncio.Lock):
            # The swap of ``self._state.http_client`` below is safe because
            # this entire ``if self._state.token_store is None`` lazy-init
            # block executes inside the per-loop asyncio.Lock acquired by
            # ``TokenStore.get_async()`` before ``_aensure_token`` returns.
            # The Lock guarantees no concurrent coroutine on the SAME event
            # loop can observe the swapped ``self._state.http_client``
            # mid-build. Across loops, each loop has its own
            # ``TokenStore.get_async()`` Lock, but the lazy-init only fires
            # once per state instance (guarded by the ``is None`` check) —
            # subsequent calls skip the swap entirely. Do NOT relax or
            # remove this invariant without re-analyzing the cross-context
            # lock semantics.
            self._state.http_client = sync_default._state.http_client
            try:
                self._state.token_store = build_token_store(
                    self._state, max_retries=self._max_retries
                )
            finally:
                self._state.http_client = saved_http_client
        snap = await self._state.token_store.get_async()
        # Mirror for legacy reads via PEP 562 shim. The TokenStore owns the
        # canonical refreshed_at timestamp; mirror to state.token + bump
        # token_expires_at so subsequent ``_aensure_token`` calls in the same
        # session take the fast path until the matriz 23h TTL elapses.
        self._state.token = snap.value
        # NB: snap.refreshed_at is from time.monotonic(); state.token_expires_at
        # is compared against time.time() in _core.token_is_fresh. Use time.time()
        # here for the legacy comparator + the matriz 23h TTL.
        self._state.token_expires_at = time.time() + (23 * 3600)

    async def login(self) -> str:
        """Explicit eager async login. Mirrors sync ``Client.login()`` semantics."""
        spec = _core.build_login_request(self._state)
        http = await self._ensure_http_client()
        request_id = uuid.uuid4().hex
        url = f"{self._state.base_url}{spec.path}"
        req = http.build_request(spec.method, url, headers=spec.headers)
        req.extensions["idempotent"] = spec.idempotent
        req.extensions["request_id"] = request_id
        req.extensions["endpoint_name"] = spec.endpoint_name
        resp = await http.send(req)
        token, expires_at = _core.parse_login_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        return token

    # ------------------------------------------------------------------
    # Transport shell (async mirror of client._request)
    # ------------------------------------------------------------------

    async def _request(self, spec: RequestSpec) -> httpx.Response:
        """Dispatch async HTTP, return raw ``httpx.Response``. Mirror of sync ``client._request``.

        Phase 10 Plan 10-02 async mirror of Phase 8 D-02 + D-22 + D-23 + D-30:

        - **Risk API path** (``spec.auth_basic is not None``): build request with
          ``httpx.BasicAuth(*spec.auth_basic)`` + extensions (incl. auth_basic for
          D-22 redaction); send; on 401 raise ``AuthenticationError`` (NO re-auth
          per D-23 — static creds, re-auth would just re-send the same wrong
          basic header).
        - **Token path** (X-Auth-Token): ``await self._aensure_token()``; build
          request with ``X-Auth-Token`` header; on 401 invalidate the TokenStore,
          re-ensure token, retry ONCE with refreshed header; on second 401 raise
          ``AuthenticationError``.
        """
        http = await self._ensure_http_client()
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
            # D-22 auth_basic propagation for log redaction (transport scans
            # extensions and splits the tuple before emitting WARNING/ERROR).
            req.extensions["auth_basic"] = spec.auth_basic
            resp = await http.send(req, auth=httpx.BasicAuth(*spec.auth_basic))
            if resp.status_code == 401:
                # WR-02 mirror: consume body BEFORE raise (HTTP/2-safe; same
                # invariant as sync _request).
                await resp.aread()
                raise AuthenticationError(
                    "ERROR",
                    f"401 Unauthorized (Risk API, endpoint={spec.endpoint_name or spec.path})",
                )
            return resp

        # Token path — D-02 401 re-auth-once.
        await self._aensure_token()
        assert self._state.token is not None  # mypy strict narrowing
        headers = {"X-Auth-Token": self._state.token, **(spec.headers or {})}
        req = http.build_request(spec.method, url, params=spec.params, headers=headers)
        req.extensions["idempotent"] = spec.idempotent
        req.extensions["request_id"] = request_id
        req.extensions["endpoint_name"] = spec.endpoint_name
        if spec.account_id is not None:
            req.extensions["account_id"] = spec.account_id

        resp = await http.send(req)
        if resp.status_code != 401:
            return resp

        # D-02 exactly-one re-auth: invalidate TokenStore, re-ensure, retry once.
        await resp.aread()  # body-consume before re-auth path (WR-02 mirror)
        self._state.token = None
        # Reset token_expires_at so the fast path in _aensure_token does NOT
        # short-circuit the re-auth with the stale token timestamp.
        self._state.token_expires_at = 0.0
        if self._state.token_store is not None:
            self._state.token_store.invalidate()
        await self._aensure_token()
        assert self._state.token is not None
        req.headers["X-Auth-Token"] = self._state.token
        resp = await http.send(req)
        if resp.status_code == 401:
            await resp.aread()
            raise AuthenticationError(
                "ERROR",
                f"401 Unauthorized after re-auth (endpoint={spec.endpoint_name or spec.path})",
            )
        return resp

    # ------------------------------------------------------------------
    # §4 Segments
    # ------------------------------------------------------------------

    async def get_segments(self) -> list[Segment]:
        spec = _core.build_get_segments_request(self._state)
        resp = await self._request(spec)
        return _core.parse_get_segments_response(resp)

    # ------------------------------------------------------------------
    # §5 Instruments
    # ------------------------------------------------------------------

    async def get_all_instruments(self) -> list[Instrument]:
        spec = _core.build_get_all_instruments_request(self._state)
        resp = await self._request(spec)
        return _core.parse_get_all_instruments_response(resp)

    async def get_instruments_details(self) -> list[InstrumentDetail]:
        spec = _core.build_get_instruments_details_request(self._state)
        resp = await self._request(spec)
        return _core.parse_get_instruments_details_response(resp)

    async def get_instrument_detail(
        self, symbol: str, market_id: MarketId = "ROFX"
    ) -> InstrumentDetail:
        spec = _core.build_get_instrument_detail_request(self._state, symbol, market_id)
        resp = await self._request(spec)
        return _core.parse_get_instrument_detail_response(resp)

    async def get_instruments_by_cfi(self, cfi_code: CFICode) -> list[Instrument]:
        spec = _core.build_get_instruments_by_cfi_request(self._state, cfi_code)
        resp = await self._request(spec)
        return _core.parse_get_instruments_by_cfi_response(resp)

    async def get_instruments_by_segment(
        self, segment_id: SegmentId, market_id: MarketId = "ROFX"
    ) -> list[Instrument]:
        spec = _core.build_get_instruments_by_segment_request(self._state, segment_id, market_id)
        resp = await self._request(spec)
        return _core.parse_get_instruments_by_segment_response(resp)

    # ------------------------------------------------------------------
    # §6 Orders
    # ------------------------------------------------------------------

    async def new_order(
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
        resp = await self._request(spec)
        return _core.parse_new_order_response(resp)

    async def replace_order(
        self, cl_ord_id: str, proprietary: str, qty: int, price: float
    ) -> NewOrderResponse:
        spec = _core.build_replace_order_request(self._state, cl_ord_id, proprietary, qty, price)
        resp = await self._request(spec)
        return _core.parse_replace_order_response(resp)

    async def cancel_order(self, cl_ord_id: str, proprietary: str) -> NewOrderResponse:
        spec = _core.build_cancel_order_request(self._state, cl_ord_id, proprietary)
        resp = await self._request(spec)
        return _core.parse_cancel_order_response(resp)

    async def get_order_status(self, cl_ord_id: str, proprietary: str) -> Order:
        spec = _core.build_get_order_status_request(self._state, cl_ord_id, proprietary)
        resp = await self._request(spec)
        return _core.parse_get_order_status_response(resp)

    async def get_order_history(self, cl_ord_id: str, proprietary: str) -> list[Order]:
        spec = _core.build_get_order_history_request(self._state, cl_ord_id, proprietary)
        resp = await self._request(spec)
        return _core.parse_get_order_history_response(resp)

    async def get_active_orders(self, account_id: str) -> list[Order]:
        spec = _core.build_get_active_orders_request(self._state, account_id)
        resp = await self._request(spec)
        return _core.parse_get_active_orders_response(resp)

    async def get_filled_orders(self, account_id: str) -> list[Order]:
        spec = _core.build_get_filled_orders_request(self._state, account_id)
        resp = await self._request(spec)
        return _core.parse_get_filled_orders_response(resp)

    async def get_all_orders(self, account_id: str) -> list[Order]:
        spec = _core.build_get_all_orders_request(self._state, account_id)
        resp = await self._request(spec)
        return _core.parse_get_all_orders_response(resp)

    async def get_order_by_exec_id(self, exec_id: str) -> Order:
        spec = _core.build_get_order_by_exec_id_request(self._state, exec_id)
        resp = await self._request(spec)
        return _core.parse_get_order_by_exec_id_response(resp)

    # ------------------------------------------------------------------
    # §7 Market Data
    # ------------------------------------------------------------------

    async def get_market_data(
        self,
        symbol: str,
        entries: Sequence[MarketDataEntry] = DEFAULT_MARKET_DATA_ENTRIES,
        *,
        market_id: MarketId = "ROFX",
        depth: int | None = None,
    ) -> MarketDataSnapshot:
        spec = _core.build_get_market_data_request(
            self._state, symbol, entries, market_id=market_id, depth=depth
        )
        resp = await self._request(spec)
        return _core.parse_get_market_data_response(resp)

    async def get_trades(
        self,
        symbol: str,
        *,
        date: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        market_id: MarketId = "ROFX",
        environment: str | None = None,
    ) -> list[Trade]:
        spec = _core.build_get_trades_request(
            self._state,
            symbol,
            date=date,
            date_from=date_from,
            date_to=date_to,
            market_id=market_id,
            environment=environment,
        )
        resp = await self._request(spec)
        return _core.parse_get_trades_response(resp)

    # ------------------------------------------------------------------
    # §9 Risk API (HTTP Basic Auth)
    # ------------------------------------------------------------------

    async def get_positions(self, account_name: str) -> list[Position]:
        spec = _core.build_get_positions_request(self._state, account_name)
        resp = await self._request(spec)
        return _core.parse_get_positions_response(resp, account_name)

    async def get_detailed_positions(self, account_name: str) -> DetailedPosition:
        spec = _core.build_get_detailed_positions_request(self._state, account_name)
        resp = await self._request(spec)
        return _core.parse_get_detailed_positions_response(resp, account_name)

    async def get_account_report(self, account_name: str) -> AccountReport:
        spec = _core.build_get_account_report_request(self._state, account_name)
        resp = await self._request(spec)
        return _core.parse_get_account_report_response(resp, account_name)


# ----------------------------------------------------------------------
# Default-async-client lazy singleton + top-level shims
# ----------------------------------------------------------------------


_default_async_client: AsyncClient | None = None


def _get_default() -> AsyncClient:
    """Lazy access to the module-level default AsyncClient."""
    global _default_async_client
    if _default_async_client is None:
        _default_async_client = AsyncClient()
    return _default_async_client


def configure(
    *,
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
    token_expires_at: float | None = None,
    max_retries: int | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> None:
    """Sobrescribe credenciales/URL/token en runtime y resetea cache (D-04 mirror).

    Phase 10 Plan 10-02:

    - Setting ``password=`` resets the cached token + ``token_expires_at`` +
      the shared ``state.token_store`` (forces a fresh refresh on next
      ``_aensure_token``; T-10-03-04 credential-rotation mitigation).
    - Setting ``max_retries=`` drops the cached ``httpx.AsyncClient`` (so the
      next ``_ensure_http_client`` rebuilds with the new transport) AND the
      shared ``state.token_store`` (so the ``RefreshPolicy`` is rebuilt with
      the new retry budget).
    - Setting ``http_client=`` swaps the cached client AS-IS (D-16 — no
      auto-wrap). The caller MUST ``await aclose()`` BEFORE configure() to
      avoid leaking the prior connection pool (WR-07 mirror).
    """
    if max_retries is not None:
        _validate_max_retries(max_retries)
    client = _get_default()
    if base_url is not None:
        client._state.base_url = base_url.rstrip("/")
    if username is not None:
        client._state.username = username
    if password is not None:
        client._state.password = password
        client._state.token = None
        client._state.token_expires_at = 0.0
        # Phase 10 Plan 10-03 — credential rotation requires TokenStore reset
        # (T-10-03-04 mitigation). Otherwise the existing TokenStore would
        # keep returning the cached OLD token until its TTL elapsed.
        client._state.token_store = None
    if token is not None:
        client._state.token = token
    if token_expires_at is not None:
        client._state.token_expires_at = token_expires_at
    if max_retries is not None:
        if client._state.http_client is not None:
            warnings.warn(
                "matriz_client.aio.configure(): replacing a live httpx.AsyncClient "
                "(via max_retries=) without awaiting aclose() leaks the connection "
                "pool. Call `await matriz_client.aio.aclose()` before configure(...).",
                ResourceWarning,
                stacklevel=2,
            )
        client._max_retries = max_retries
        client._state.http_client = None
        # Phase 10 Plan 10-03 — RefreshPolicy is wired with the old max_retries
        # value at TokenStore construction time; force a rebuild to apply the
        # new retry budget.
        client._state.token_store = None
    if http_client is not None:
        if client._state.http_client is not None and client._state.http_client is not http_client:
            warnings.warn(
                "matriz_client.aio.configure(): replacing a live httpx.AsyncClient "
                "(via http_client=) without awaiting aclose() leaks the connection "
                "pool. Call `await matriz_client.aio.aclose()` before configure(...).",
                ResourceWarning,
                stacklevel=2,
            )
        client._state.http_client = http_client


async def login() -> str:
    """Top-level async shim: delega al default AsyncClient."""
    return await _get_default().login()


async def aclose() -> None:
    """Top-level async shim: cierra el default AsyncClient (idempotente)."""
    await _get_default().aclose()


# ----------------------------------------------------------------------
# Endpoint delegators (mirror sync ``client`` module-level shims)
# ----------------------------------------------------------------------


async def get_segments() -> list[Segment]:
    return await _get_default().get_segments()


async def get_all_instruments() -> list[Instrument]:
    return await _get_default().get_all_instruments()


async def get_instruments_details() -> list[InstrumentDetail]:
    return await _get_default().get_instruments_details()


async def get_instrument_detail(symbol: str, market_id: MarketId = "ROFX") -> InstrumentDetail:
    return await _get_default().get_instrument_detail(symbol, market_id)


async def get_instruments_by_cfi(cfi_code: CFICode) -> list[Instrument]:
    return await _get_default().get_instruments_by_cfi(cfi_code)


async def get_instruments_by_segment(
    segment_id: SegmentId, market_id: MarketId = "ROFX"
) -> list[Instrument]:
    return await _get_default().get_instruments_by_segment(segment_id, market_id)


async def new_order(
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
    return await _get_default().new_order(
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


async def replace_order(
    cl_ord_id: str, proprietary: str, qty: int, price: float
) -> NewOrderResponse:
    return await _get_default().replace_order(cl_ord_id, proprietary, qty, price)


async def cancel_order(cl_ord_id: str, proprietary: str) -> NewOrderResponse:
    return await _get_default().cancel_order(cl_ord_id, proprietary)


async def get_order_status(cl_ord_id: str, proprietary: str) -> Order:
    return await _get_default().get_order_status(cl_ord_id, proprietary)


async def get_order_history(cl_ord_id: str, proprietary: str) -> list[Order]:
    return await _get_default().get_order_history(cl_ord_id, proprietary)


async def get_active_orders(account_id: str) -> list[Order]:
    return await _get_default().get_active_orders(account_id)


async def get_filled_orders(account_id: str) -> list[Order]:
    return await _get_default().get_filled_orders(account_id)


async def get_all_orders(account_id: str) -> list[Order]:
    return await _get_default().get_all_orders(account_id)


async def get_order_by_exec_id(exec_id: str) -> Order:
    return await _get_default().get_order_by_exec_id(exec_id)


async def get_market_data(
    symbol: str,
    entries: Sequence[MarketDataEntry] = DEFAULT_MARKET_DATA_ENTRIES,
    *,
    market_id: MarketId = "ROFX",
    depth: int | None = None,
) -> MarketDataSnapshot:
    return await _get_default().get_market_data(symbol, entries, market_id=market_id, depth=depth)


async def get_trades(
    symbol: str,
    *,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    market_id: MarketId = "ROFX",
    environment: str | None = None,
) -> list[Trade]:
    return await _get_default().get_trades(
        symbol,
        date=date,
        date_from=date_from,
        date_to=date_to,
        market_id=market_id,
        environment=environment,
    )


async def get_positions(account_name: str) -> list[Position]:
    return await _get_default().get_positions(account_name)


async def get_detailed_positions(account_name: str) -> DetailedPosition:
    return await _get_default().get_detailed_positions(account_name)


async def get_account_report(account_name: str) -> AccountReport:
    return await _get_default().get_account_report(account_name)


# ----------------------------------------------------------------------
# PEP 562 read-only shim (Plan 10-02 back-compat for legacy globals)
# ----------------------------------------------------------------------

_FORWARDED_TO_STATE: dict[str, str] = {
    "_token": "token",
    "_token_expires_at": "token_expires_at",
    "_base_url": "base_url",
}

_FORWARDED_HTTP_CLIENT = "_client"


def __getattr__(name: str) -> Any:
    """PEP 562 read-only shim. Writes via ``configure(...)`` only."""
    if name in _FORWARDED_TO_STATE:
        return getattr(_get_default()._state, _FORWARDED_TO_STATE[name])
    if name == _FORWARDED_HTTP_CLIENT:
        return _get_default()._state.http_client
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
