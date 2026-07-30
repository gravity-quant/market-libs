"""Pure builders and parsers for the market-data-client REST client.

Phase 20 D-01 (per-package ``RequestSpec``) + D-04 (Auth0 token
builder/parser vive AQUÍ, junto a ``raise_for_response``, no en un módulo
auth separado) + D-05 (grant único ``client_credentials``, sin refresh
rotation → parser 2-tuple) + D-06 (body-consume-then-raise en parsers) +
D-07 (fallback TTL cuando ``expires_in`` ausente) + D-08/D-09 (health
builders anónimos + flag ``authenticated``) + D-14 (mapping de status).

All functions are PURE: state in → ``RequestSpec`` (builders) or
``httpx.Response`` in → typed result (parsers). NO I/O dispatch
(``httpx.Client.request`` / ``await httpx.AsyncClient.request`` vive en
``client.py`` / ``aio.py``, Wave 3). NO imports desde
``market_data_client.client`` ni ``market_data_client.aio`` — ``_core``
permanece IO-free y desacoplado de los shells (import boundary).

Usage from a transport shell (Wave 3)::

    from market_data_client import _core

    def _ensure_token(self) -> str:
        spec = _core.build_token_request(self._state)
        resp = self._http.post(
            self._state.auth0_token_url,  # absolute URL (Pitfall 1)
            data=spec.data,
            headers=spec.headers,
        )
        token, expires_at = _core.parse_token_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        return token

Auth0 delta vs iol: un único grant ``client_credentials`` (machine-to-machine),
sin ``username``/``password`` ni ``refresh_token`` — de ahí que
``parse_token_response`` retorne un 2-tuple ``(token, expires_at)`` en lugar del
3-tuple con slot de refresh de iol (D-05). El ``build_token_request`` marca
``authenticated=False`` y ``path=""`` para que el grant nunca cargue un Bearer
stale y despache (Wave 3) a la URL absoluta de Auth0, no a ``base_url``
(T-20-02, Pitfall 1).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from market_data_client import _params
from market_data_client._state import (
    _TOKEN_TTL_BUFFER_SECONDS,
    _TOKEN_TTL_FALLBACK_SECONDS,
    _ClientState,
)
from market_data_client.exceptions import (
    MarketDataAPIError,
    MarketDataAuthError,
    MarketDataRateLimitError,
)
from market_data_client.models import LatestRequest, MarketDataSnapshot

__all__ = [
    "RequestSpec",
    "build_health_feed_request",
    "build_health_request",
    "build_latest_batch_request",
    "build_latest_request",
    "build_market_data_request",
    "build_token_request",
    "parse_health_response",
    "parse_latest_response",
    "parse_market_data_response",
    "parse_token_response",
    "raise_for_response",
    "token_is_fresh",
]


# ----------------------------------------------------------------------
# RequestSpec
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RequestSpec:
    """Pure description of an HTTP request — no transport coupling.

    Per-package shape (D-01 / no shared internals): ``data`` field para el
    body form-encoded del grant Auth0 ``POST /token``
    (``application/x-www-form-urlencoded``, NOT JSON).

    ``idempotent`` gatea el mutation-gate del ``RetryTransport``
    (``request.extensions["idempotent"]``); ``endpoint_name`` fluye a los log
    records estructurados. Net-new vs iol: ``authenticated: bool = True`` (D-09)
    gatea, en los shells de Wave 3, la inyección del header ``Authorization:
    Bearer``: los specs anónimos (grant de token, health) lo setean en ``False``
    para no cargar un Bearer stale (T-20-02).
    """

    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    json_body: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    idempotent: bool = False
    endpoint_name: str = ""
    authenticated: bool = True


# ----------------------------------------------------------------------
# Stateless helpers (D-14)
# ----------------------------------------------------------------------


def raise_for_response(resp: httpx.Response) -> None:
    """Map an HTTP error response to the package's exception hierarchy.

    401/403 → ``MarketDataAuthError``; 429 → ``MarketDataRateLimitError``;
    cualquier otro status de error → ``MarketDataAPIError`` (D-14). Compartido
    por sync ``client.py`` y async ``aio.py`` (Wave 3).
    """
    if resp.status_code in (401, 403):
        raise MarketDataAuthError(resp.status_code, resp.text)
    if resp.status_code == 429:
        raise MarketDataRateLimitError(resp.status_code, resp.text)
    if resp.is_error:
        raise MarketDataAPIError(resp.status_code, resp.text)


def token_is_fresh(state: _ClientState) -> bool:
    """Pure helper: True iff ``state.token`` is set AND not yet expired.

    Usado por los ``_ensure_token()`` de los transport shells (sync + async)
    para decidir si saltar el flujo de auth en un request dado. El buffer de
    60s ya está horneado en ``token_expires_at`` por ``parse_token_response``
    (T-20-03).
    """
    return bool(state.token and time.time() < state.token_expires_at)


# ----------------------------------------------------------------------
# Auth0 client-credentials grant (D-04 / D-05)
# ----------------------------------------------------------------------


def build_token_request(state: _ClientState) -> RequestSpec:
    """Pure: build the Auth0 ``client_credentials`` grant request spec.

    Endpoint: ``POST`` al ``state.auth0_token_url`` absoluto (de ahí
    ``path=""`` — el dispatch de Wave 3 usa la URL absoluta, NO ``base_url``;
    Pitfall 1 / T-20-02).

    ``idempotent=True`` — el grant es replay-safe (un 5xx transitorio se puede
    reintentar; un re-issue exitoso sólo sobreescribe el access_token en state).
    ``authenticated=False`` — el grant nunca carga un Bearer previo.
    """
    if (
        not state.client_id
        or not state.client_secret
        or not state.audience
        or not state.auth0_token_url
    ):
        raise MarketDataAuthError(
            0,
            "MARKET_DATA_CLIENT_ID, MARKET_DATA_CLIENT_SECRET, "
            "MARKET_DATA_AUDIENCE y MARKET_DATA_AUTH0_TOKEN_URL son requeridos",
        )
    return RequestSpec(
        method="POST",
        path="",
        data={
            "grant_type": "client_credentials",
            "client_id": state.client_id,
            "client_secret": state.client_secret,
            "audience": state.audience,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        idempotent=True,
        endpoint_name="token",
        authenticated=False,
    )


def parse_token_response(resp: httpx.Response) -> tuple[str, float]:
    """Pure: parse the Auth0 token response → ``(token, expires_at)``.

    Order (D-06 body-consume-then-raise):

    1. ``resp.read()`` — explicit body consume (HTTP/2-safe).
    2. ``raise_for_response(resp)`` — status check after body consumed.
    3. ``resp.json()`` — decode (raises ``ValueError`` if malformed).
    4. Type-guard ``access_token`` (non-empty str) y deriva ``expires_at``.

    ``expires_at = now + expires_in - buffer``. Cuando el response omite
    ``expires_in`` se usa ``_TOKEN_TTL_FALLBACK_SECONDS`` (D-07). NO hay slot de
    refresh (D-05): el grant ``client_credentials`` re-autentica re-posteando las
    credenciales. Un ``access_token`` ausente / non-str / vacío levanta
    ``MarketDataAuthError`` en lugar de cachear un token bogus (T-20-05).
    """
    resp.read()
    raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise MarketDataAuthError(resp.status_code, "No access_token in response")
    # D-07 fallback extended (WR-02): ``dict.get(k, default)`` only falls back on
    # an ABSENT key — a present-but-null ``"expires_in": null`` returns None and
    # ``float(None)`` would raise TypeError. Coerce None / non-numeric to the
    # fallback TTL so a non-standard Auth0 response cannot crash the token cache.
    expires_in_raw = data.get("expires_in")
    try:
        expires_in = (
            float(_TOKEN_TTL_FALLBACK_SECONDS) if expires_in_raw is None else float(expires_in_raw)
        )
    except (TypeError, ValueError):
        expires_in = float(_TOKEN_TTL_FALLBACK_SECONDS)
    expires_at = time.time() + expires_in - _TOKEN_TTL_BUFFER_SECONDS
    return access_token, expires_at


# ----------------------------------------------------------------------
# Health builders + parser (D-08 / D-09) — anonymous specs
# ----------------------------------------------------------------------


def build_health_request(state: _ClientState) -> RequestSpec:
    """Pure: build spec for ``GET /health`` (anonymous, D-08/D-09)."""
    del state  # state-independent
    return RequestSpec(
        method="GET",
        path="/health",
        idempotent=True,
        endpoint_name="health",
        authenticated=False,
    )


def build_health_feed_request(state: _ClientState) -> RequestSpec:
    """Pure: build spec for ``GET /health/feed`` (anonymous, D-08/D-09)."""
    del state  # state-independent
    return RequestSpec(
        method="GET",
        path="/health/feed",
        idempotent=True,
        endpoint_name="health_feed",
        authenticated=False,
    )


def parse_health_response(resp: httpx.Response) -> dict[str, Any]:
    """Pure: parse a health response → JSON dict (D-03: no SafeModel here)."""
    resp.read()
    raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    return data


# ----------------------------------------------------------------------
# Market-data read builders (D-06) — authenticated + idempotent
# ----------------------------------------------------------------------


def build_market_data_request(
    state: _ClientState,
    *,
    market_id: str | None = None,
    prefix: str | None = None,
    active: bool | None = None,
    entries: str | None = None,
    max_staleness_seconds: int | None = None,
    with_data: bool | None = None,
    order: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> RequestSpec:
    """Pure: build spec for ``GET /marketdata`` (D-06).

    ``authenticated=True`` gatea la inyección del Bearer en los shells de Wave 3;
    ``idempotent=True`` marca el GET como replay-safe (retry-eligible). Los
    optionals ``None`` se dropean vía ``_params.drop_none`` (D-07) preservando los
    falsy legítimos (``active=False`` / ``offset=0`` / ``""``); un dict vacío
    colapsa a ``params=None``. Los booleans viajan con el encoding httpx-nativo
    (``True → "true"``) — encoding explícito diferido a Phase 23 (D-07).
    """
    del state  # state-independent (filtros vienen por kwargs)
    params = _params.drop_none(
        {
            "market_id": market_id,
            "prefix": prefix,
            "active": active,
            "entries": entries,
            "max_staleness_seconds": max_staleness_seconds,
            "with_data": with_data,
            "order": order,
            "limit": limit,
            "offset": offset,
        }
    )
    return RequestSpec(
        method="GET",
        path="/marketdata",
        params=params or None,
        idempotent=True,
        endpoint_name="market_data",
        authenticated=True,
    )


def build_latest_request(
    state: _ClientState,
    *,
    symbol: str | None = None,
    market_id: str | None = None,
    entries: str | None = None,
) -> RequestSpec:
    """Pure: build spec for ``GET /marketdata/latest`` (D-06).

    Same authenticated/idempotent contract as ``build_market_data_request``;
    ``None`` optionals dropped, empty dict → ``params=None``.
    """
    del state  # state-independent (filtros vienen por kwargs)
    params = _params.drop_none(
        {
            "symbol": symbol,
            "market_id": market_id,
            "entries": entries,
        }
    )
    return RequestSpec(
        method="GET",
        path="/marketdata/latest",
        params=params or None,
        idempotent=True,
        endpoint_name="latest",
        authenticated=True,
    )


def build_latest_batch_request(state: _ClientState, latest_request: LatestRequest) -> RequestSpec:
    """Pure: build spec for the batch ``POST /marketdata/latest`` (D-05 / D-06).

    A read expressed as POST (the batch body doesn't fit a query string). It is
    replay-safe like ``build_token_request`` → ``idempotent=True``, so the
    mutation-gate lets the transport retry it. The typed ``LatestRequest`` is
    serialized to the wire body via ``to_dict`` (drops ``None`` optionals).
    """
    del state  # state-independent (payload viene en latest_request)
    return RequestSpec(
        method="POST",
        path="/marketdata/latest",
        json_body=latest_request.to_dict(),
        idempotent=True,
        endpoint_name="latest_batch",
        authenticated=True,
    )


# ----------------------------------------------------------------------
# Market-data read parsers (D-01) — client-stamped received_at
# ----------------------------------------------------------------------


def parse_market_data_response(resp: httpx.Response) -> list[MarketDataSnapshot]:
    """Pure: parse a ``GET /marketdata`` response → list of snapshots (D-01).

    Order mirrors ``parse_health_response`` (body-consume-then-raise) with the
    ``received_at`` stamp captured ONCE, between ``resp.read()`` and
    ``raise_for_response`` — the single wall-clock is threaded into EVERY
    snapshot so all rows from one response share the same stamp (D-01/D-02: the
    client owns the stamp; live-payload reconciliation is deferred to Phase 23).
    A ``null``/empty body collapses to ``[]`` (collection guard).
    """
    resp.read()
    received_at = time.time()
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    return [MarketDataSnapshot.from_api(item, received_at=received_at) for item in raw]


def parse_latest_response(resp: httpx.Response) -> list[MarketDataSnapshot]:
    """Pure: parse a ``GET/POST /marketdata/latest`` response → list of snapshots.

    Same one-stamp-per-response contract as ``parse_market_data_response``.
    Return type is PROVISIONAL (A1/A2 — OpenAPI response shapes not vendored):
    the batch ``POST`` naturally returns multiple symbols, so a ``list`` is the
    common shape for both the single-symbol GET and the batch POST; Phase 23
    reconciles against real develop payloads (a single-snapshot GET shape, if
    confirmed, is a one-line adjustment absorbed by ``from_api`` tolerance).
    """
    resp.read()
    received_at = time.time()
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    return [MarketDataSnapshot.from_api(item, received_at=received_at) for item in raw]
