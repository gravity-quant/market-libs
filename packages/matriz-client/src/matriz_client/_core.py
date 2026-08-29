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

import re
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, get_args

import httpx

from matriz_client import _decode
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

# Phase 9 BUG-01 (F-09) — hybrid CFI guard constants.
# Source of truth: ``matriz_client.types.CFICode`` (Literal, 9 valores).
# Pattern S5: compile-once regex + frozenset inmutable + hashable derivada del
# Literal via ``typing.get_args`` (Python 3.12+ garantiza orden de declaración).
# WR-01 fix (Phase 9 code review): ``\A...\Z`` anchors rechazan trailing ``\n``
# (Python ``$`` matchea antes de newline final por default sin re.MULTILINE).
_CFI_ISO_RE = re.compile(r"\A[A-Z]{6}\Z")
_CFI_LITERAL_VALUES: frozenset[str] = frozenset(get_args(CFICode))


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
    """Map HTTP error status codes to typed exceptions (WR-08).

    Phase 8 review WR-08: previously this helper called
    ``resp.raise_for_status()`` which raises stdlib
    ``httpx.HTTPStatusError`` — callers could NOT rely on
    ``except MatrizClientError:`` to catch all matriz failures, unlike
    iol/higyrus which map status codes to typed exceptions.

    Mapping (mirror iol/higyrus):
    - 401 / 403 → ``AuthenticationError`` (already a ``PrimaryAPIError``
      subclass; allows callers to differentiate auth failures from other
      API errors via the type hierarchy)
    - Any other 4xx / 5xx → ``PrimaryAPIError`` with the status code in
      the description string
    - 2xx / 3xx → no-op (consistent with iol/higyrus ``raise_for_response``)

    The 429 RateLimit case is mapped to ``PrimaryAPIError`` (matriz has
    no dedicated RateLimitError class today; this can be added in a
    future minor version without breaking the typed exception base).

    D-04 alias preservation: ``client._raise_for_response =
    _core.raise_for_response`` mantiene B8 (forward-looking Phase 10
    ``aio._raise_for_response is client._raise_for_response``).
    """
    if not resp.is_error:
        return
    if resp.status_code in (401, 403):
        raise AuthenticationError(
            "ERROR",
            f"HTTP {resp.status_code} (Unauthorized/Forbidden)",
        )
    raise PrimaryAPIError(
        status="ERROR",
        description=f"HTTP {resp.status_code}",
        message=None,
    )


def unwrap(data: dict[str, Any], key: str, endpoint: str) -> Any:
    """Return ``data[key]``, o levanta ``PrimaryAPIError`` si falta o es ``null``.

    Surface a typed ``PrimaryAPIError`` (status ``"ERROR"``) cuando la
    Primary API response no trae el envelope key que el wrapper espera. Sin
    este guard, el caller vería un ``KeyError`` opaco fuera del contrato
    de excepciones del cliente (D-MATZ-9).

    **El mensaje lista las keys que el body SÍ traía (Phase 37 code review,
    WR-05).** El cambio a ``strict-unwrap`` de 37-01 se apoya enteramente en el
    vendor doc: los dos endpoints Risk no tienen NINGUNA captura viva en
    ``.planning/verification/schemas/matriz-client/`` y no puede producirse
    ninguna mientras ``LIVE-MATZ-33`` esté en pie. Si el nombre de la key
    resultara ser otro, el operator necesita exactamente un dato para distinguir
    "el vendor usa otra key" de "el vendor cambió la forma" — y es el key set
    observado. Emitirlo acá es lo que hace que una corrida en vivo sea
    auto-diagnosticable en el primer intento en vez del segundo.

    **``null`` es una violación de forma igual que una key ausente (WR-05).** El
    review midió que ``{"status":"OK","detailedPosition": null}`` pasaba este
    guard y producía un modelo all-defaults en silencio — reintroduciendo
    exactamente el modo de falla que ``strict-unwrap`` se adoptó para eliminar
    ("la cuenta no tiene nada"). Para los envelopes de lista el ``None`` tampoco
    era benigno: reventaba con un ``TypeError`` crudo en la comprehension del
    caller, fuera del contrato de excepciones. Las dos disposiciones convergen en
    la misma respuesta, y la excepción tipada es la correcta para ambas.

    Los dos casos llevan mensajes distintos a propósito: en un log en vivo
    "ausente" y "presente pero null" apuntan a causas distintas del lado del
    vendor.
    """
    if key not in data:
        raise PrimaryAPIError(
            status="ERROR",
            description=(
                f"missing envelope key '{key}' in response from {endpoint} "
                f"(body carried: {sorted(data)})"
            ),
            message=None,
        )
    value = data[key]
    if value is None:
        raise PrimaryAPIError(
            status="ERROR",
            description=(
                f"envelope key '{key}' is null in response from {endpoint} "
                f"(body carried: {sorted(data)})"
            ),
            message=None,
        )
    return value


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

    Historia (Phase 37, D-03): matriz llevaba una SEGUNDA copia de este parser,
    ``_parse_risk_response``, byte-idéntica salvo por la llamada a ``unwrap``
    que le faltaba. Existía porque se creía que los endpoints Risk
    (``detailedPosition`` / ``accountReport``) respondían con el payload en la
    raíz — una creencia que el propio vendor doc committeado en el paquete
    falsifica: ``documentation/Primary-API.md:1701-1703`` y ``:1817-1819``
    muestran ambos bodies envueltos. Corregido el unwrap bajo la opción
    ratificada ``strict-unwrap``, la copia quedó sin diferencia y sin callers,
    y se eliminó. Los dos parsers Risk usan esta función. Si vuelve a aparecer
    la tentación de una variante sin unwrap, la evidencia contraria está en las
    dos líneas de vendor doc citadas arriba.
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


@_decode._response_parser
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


@_decode._response_parser
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


@_decode._response_parser
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


@_decode._response_parser
def parse_get_instrument_detail_response(resp: httpx.Response) -> InstrumentDetail:
    """Parse envelope ``{instrument: {...}}`` → ``InstrumentDetail``."""
    path = "/rest/instruments/detail"
    data = parse_envelope_response(resp, path)
    return InstrumentDetail.from_api(unwrap(data, "instrument", path))


def build_get_instruments_by_cfi_request(
    state: _ClientState,
    cfi_code: CFICode,
) -> RequestSpec:
    """``GET /rest/instruments/byCFICode?CFICode=...``.

    Phase 9 BUG-01 (F-09) — Hybrid Literal + ISO 10962 regex guard pre-HTTP.

    El typed signature declara ``CFICode`` (``Literal[...]`` con 9 valores
    válidos), pero callers pueden bypass con ``cast(CFICode, "INVALID-CFI")``
    y mypy strict no captura el cast en runtime. F-09 (CONFIRMED en cycle
    ``verification-cycle-2026-Q2``) documentó que pre-fix el cliente
    propagaba CFIs malformados al wire sin levantar excepción. El guard
    runtime hybrid bloquea esto:

    1. Si ``cfi_code`` está en ``_CFI_LITERAL_VALUES`` (frozenset derivado
       de ``types.CFICode`` via ``get_args``) → pass (literal-known).
    2. Si ``_CFI_ISO_RE.match(cfi_code)`` matchea ``^[A-Z]{6}$`` → pass
       (forward-compat ISO 10962:2021 sin lib bump).
    3. Otherwise → raise ``PrimaryAPIError(status="ERROR")`` pre-HTTP.

    **Deviation D-02 vs ROADMAP literal** (``_core.raise_for_response``):
    el guard vive en el builder, NO en ``raise_for_response``, porque
    ``raise_for_response(resp: httpx.Response)`` solo ve la response y
    no tiene acceso al ``cfi_code`` param. El contrato observable
    (``PrimaryAPIError(status="ERROR")``) se preserva — el probe driver
    ``probe_error_malformed_cfi`` (``main_matriz.py:1194``) captura el
    outcome esperado vía ``except PrimaryAPIError as exc: if exc.status
    == "ERROR": PASS``.
    """
    # WR-02 fix (Phase 9 code review): bypass de tipos (``cast(CFICode, None)``,
    # ints, lists) NO debe propagar ``TypeError`` — debe colapsar al contrato
    # observable ``PrimaryAPIError(status="ERROR")`` del guard.
    if not isinstance(cfi_code, str) or (
        cfi_code not in _CFI_LITERAL_VALUES and not _CFI_ISO_RE.match(cfi_code)
    ):
        raise PrimaryAPIError(
            status="ERROR",
            description=(
                f"CFI inválido: {cfi_code!r} "
                "(no es str, o no está en CFICode Literal, ni matchea ^[A-Z]{6}$)"
            ),
            message=None,
        )
    return RequestSpec(
        method="GET",
        path="/rest/instruments/byCFICode",
        params={"CFICode": cfi_code},
        idempotent=True,
        endpoint_name="get_instruments_by_cfi",
    )


@_decode._response_parser
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


@_decode._response_parser
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


@_decode._response_parser
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


@_decode._response_parser
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


@_decode._response_parser
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


@_decode._response_parser
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


@_decode._response_parser
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


@_decode._response_parser
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


@_decode._response_parser
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


@_decode._response_parser
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


@_decode._response_parser
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


@_decode._response_parser
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


@_decode._response_parser
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


@_decode._response_parser
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

    Risk §9.2 responde ENVUELTO en la key ``detailedPosition``
    (``documentation/Primary-API.md:1701-1703``). El claim previo de esta
    docstring — "sin envelope key, payload raíz ES el resultado" — lo falsifica
    el propio vendor doc; corregido en Phase 37 (D-03, ``strict-unwrap``).
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


@_decode._response_parser
def parse_get_detailed_positions_response(
    resp: httpx.Response, account_name: str
) -> DetailedPosition:
    """Parse envelope ``{detailedPosition: {...}}`` → ``DetailedPosition``.

    Phase 37 D-03, opción ratificada ``strict-unwrap``. Hasta esta fase el
    parser pasaba el body RAÍZ a ``from_api`` bajo un claim de ausencia de
    envelope que el vendor doc falsifica, así que ``detailedPosition`` entraba
    como key ``extra`` y ningún campo declarado se encontraba jamás. El vendor doc
    (``documentation/Primary-API.md:1701-1703``) muestra el body envuelto, y el
    endpoint hermano ``parse_get_positions_response`` ya desenvolvía.

    Un body SIN la envelope key levanta ``PrimaryAPIError`` vía ``unwrap`` —
    disposición ratificada por el operator en el checkpoint de 37-01: una
    respuesta de forma equivocada se vuelve ruidosa en vez de producir un
    modelo all-defaults que se lee como "la cuenta no tiene nada".
    """
    path = f"/rest/risk/detailedPosition/{account_name}"
    data = parse_envelope_response(resp, path)
    return DetailedPosition.from_api(unwrap(data, "detailedPosition", path))


def build_get_account_report_request(
    state: _ClientState,
    account_name: str,
) -> RequestSpec:
    """``GET /rest/risk/accountReport/{account_name}`` con HTTP Basic Auth (D-07).

    Risk §9.3 responde ENVUELTO en la key ``accountData``
    (``documentation/Primary-API.md:1817-1819``). El claim previo de esta
    docstring — "sin envelope key, payload raíz ES el resultado" — lo falsifica
    el propio vendor doc; corregido en Phase 37 (D-03, ``strict-unwrap``).
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


@_decode._response_parser
def parse_get_account_report_response(resp: httpx.Response, account_name: str) -> AccountReport:
    """Parse envelope ``{accountData: {...}}`` → ``AccountReport``.

    Phase 37 D-03, opción ratificada ``strict-unwrap`` — gemelo exacto de
    ``parse_get_detailed_positions_response``. El claim previo de ausencia de
    envelope lo falsifica ``documentation/Primary-API.md:1817-1819``, que muestra
    el body envuelto en ``accountData``. Un body SIN la key levanta
    ``PrimaryAPIError`` vía ``unwrap``.
    """
    path = f"/rest/risk/accountReport/{account_name}"
    data = parse_envelope_response(resp, path)
    return AccountReport.from_api(unwrap(data, "accountData", path))
