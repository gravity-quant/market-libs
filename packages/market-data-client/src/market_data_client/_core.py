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

import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from market_data_client import _decode, _params
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
from market_data_client.models import (
    CalendarConfig,
    CalendarDay,
    Health,
    HealthFeed,
    Instrument,
    LatestRequest,
    MarketDataSnapshot,
    Segment,
    Symbol,
)

__all__ = [
    "RequestSpec",
    "build_add_holidays_request",
    "build_calendar_config_request",
    "build_calendar_request",
    "build_create_symbol_request",
    "build_create_symbols_request",
    "build_delete_calendar_config_request",
    "build_delete_holiday_request",
    "build_health_feed_request",
    "build_health_request",
    "build_instruments_request",
    "build_latest_batch_request",
    "build_latest_request",
    "build_market_data_request",
    "build_preview_calendar_config_request",
    "build_segments_request",
    "build_set_calendar_config_request",
    "build_symbols_request",
    "build_token_request",
    "build_update_symbol_request",
    "parse_calendar_config_response",
    "parse_calendar_response",
    "parse_calendar_write_response",
    "parse_health_feed_response",
    "parse_health_response",
    "parse_instruments_response",
    "parse_latest_response",
    "parse_market_data_response",
    "parse_segments_response",
    "parse_symbols_response",
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


@_decode._response_parser
def parse_health_response(resp: httpx.Response) -> Health:
    """Pure: parse ``GET /health`` → a single :class:`Health` (Phase 31 TYP-02, D-01/D-05).

    Until Phase 31 ONE function served both health endpoints and returned the raw
    mapping. Their live shapes are unrelated — ``/health`` is ``{status, auth{}}``
    and ``/health/feed`` is a three-level ingestor tree — so the sharing ended:
    this parser is named by ``get_health`` only, and ``parse_health_feed_response``
    below by ``get_health_feed`` only.

    Shape follows ``parse_calendar_config_response``, the in-package template for
    a non-collection typed parser. Body-consume-then-raise order is a Phase 7
    D-06 HTTP/2-safety invariant and is NEVER reordered. An empty body / 204
    collapses to ``Health.from_api(None)`` — the zero-valued instance, explicitly
    NOT a raise and explicitly not an empty mapping.

    D-04: this parser GAINS a non-dict shape guard it never had (the shared
    version annotated ``resp.json()`` as a dict and returned it unchecked, so a
    list body produced an instance-shaped lie). The message carries
    ``type(raw).__name__`` — the type NAME only, never the value and never a
    repr (T-31-19 / T-29-36 / ASVS V7): market-data payloads carry symbol and
    account identifiers.
    """
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return Health.from_api(None)
    raw = resp.json()
    if not isinstance(raw, dict):
        raise MarketDataAPIError(0, f"expected dict, got {type(raw).__name__}")
    return Health.from_api(raw)


@_decode._response_parser
def parse_health_feed_response(resp: httpx.Response) -> HealthFeed:
    """Pure: parse ``GET /health/feed`` → a single :class:`HealthFeed` (Phase 31, D-01/D-05).

    The half of the Phase 31 split that ``get_health_feed`` now names for itself.
    Same contract as :func:`parse_health_response` — decorated, body-consume-then-raise,
    empty/204 → the zero-valued instance, non-dict → ``MarketDataAPIError`` naming
    the observed TYPE only — over a different model whose tree is three levels
    deep (``HealthFeed`` → ``FeedIngestor`` → ``FeedMarket`` / ``FeedPipeline``).
    """
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return HealthFeed.from_api(None)
    raw = resp.json()
    if not isinstance(raw, dict):
        raise MarketDataAPIError(0, f"expected dict, got {type(raw).__name__}")
    return HealthFeed.from_api(raw)


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
    symbol: str,
    market_id: str | None = None,
    entries: str | None = None,
) -> RequestSpec:
    """Pure: build spec for ``GET /marketdata/latest`` (D-06).

    Same authenticated/idempotent contract as ``build_market_data_request``.
    ``symbol`` is required (the live OpenAPI marks the query param
    ``required=True``; F-01/F-13); ``market_id`` and ``entries`` remain
    droppable ``None`` optionals, empty dict → ``params=None``.
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
# Symbols write builders (MUT-MD-01) — POST/PATCH, idempotent + authenticated
# ----------------------------------------------------------------------
#
# Pure builders mirroring ``build_latest_batch_request`` (``del state``, no I/O):
# each takes the already-serialized model dict as its ``json_body`` and stays
# state-agnostic. All three are ``idempotent=True`` per DM-03 (retry-safe;
# revalidated live in Phase 27). The mutation gate does NOT live here — the shell
# checks it before calling these (D-05).


def build_create_symbol_request(state: _ClientState, json_body: dict[str, Any]) -> RequestSpec:
    """Pure: build spec for ``POST /symbols`` (single symbol create, MUT-MD-01).

    ``idempotent=True`` (DM-03 — retry-safe per spec; revalidated live in
    Phase 27); ``authenticated=True``. ``json_body`` is the already-serialized
    ``NewSymbol.to_dict()`` (the payload, not state).
    """
    del state  # state-independent (payload comes via json_body)
    return RequestSpec(
        method="POST",
        path="/symbols",
        json_body=json_body,
        idempotent=True,
        endpoint_name="create_symbol",
        authenticated=True,
    )


def build_create_symbols_request(state: _ClientState, json_body: dict[str, Any]) -> RequestSpec:
    """Pure: build spec for ``POST /symbols/batch`` (batch create, MUT-MD-01).

    Same idempotent/authenticated contract as ``build_create_symbol_request``;
    ``json_body`` is the already-serialized ``NewSymbols.to_dict()``.
    """
    del state  # state-independent (payload comes via json_body)
    return RequestSpec(
        method="POST",
        path="/symbols/batch",
        json_body=json_body,
        idempotent=True,
        endpoint_name="create_symbols",
        authenticated=True,
    )


def build_update_symbol_request(
    state: _ClientState, symbol_id: int | str, json_body: dict[str, Any]
) -> RequestSpec:
    """Pure: build spec for ``PATCH /symbols/{symbol_id}`` (MUT-MD-01).

    ``symbol_id`` is the DATABASE ROW ID, not the symbol name. The live develop
    OpenAPI types the path parameter ``{"type": "integer"}`` and the real wire
    confirms it: every row of ``GET /symbols`` carries ``"id": <int>``, and so does
    the body of ``POST /symbols`` (LIVE-MUT-01 armed run 2026-08-01; baselines
    ``get-symbols-probe-prefix-{sync,async}.json`` and
    ``create-symbol-{sync,async}-response.json``).

    **The percent-encoding item is DISSOLVED, not deferred (D-09).** Phase 25
    recorded ``symbol_id`` as a possibly ``/``-bearing identifier such as
    ``"DLR/DIC26"`` and deferred quoting to Phase 27. That premise was FALSE: the
    parameter is an integer row id and an integer cannot contain a slash, so there
    is nothing to encode. The value is interpolated RAW and stays raw — adding a
    quoting layer here would only be able to corrupt a legitimate id. Do not
    re-open this: the dissolution rests on the re-fetched contract plus the
    measured wire, not on an assumption.

    The annotation WIDENS to ``int | str`` rather than narrowing to ``int``
    (D-22): ``str`` is the type published in v0.3.0/v0.3.1, so narrowing would
    break every consumer at type-check time. ``int`` is the correct form and the
    one callers should migrate to; ``str`` keeps working and is interpolated
    identically.

    ``idempotent=True`` (DM-03, CONFIRMED live: two identical PATCHes left exactly
    one row), ``authenticated=True``; ``json_body`` is the already-serialized
    ``SymbolPatch.to_dict()``.
    """
    del state  # state-independent (payload comes via json_body)
    return RequestSpec(
        method="PATCH",
        path=f"/symbols/{symbol_id}",
        json_body=json_body,
        idempotent=True,
        endpoint_name="update_symbol",
        authenticated=True,
    )


# ----------------------------------------------------------------------
# Reference-data read builders (D-01 / D-02 / D-03) — authenticated + idempotent
# ----------------------------------------------------------------------


def build_instruments_request(
    state: _ClientState,
    *,
    q: str | None = None,
    segment: str | None = None,
    market_id: str | None = None,
    include_expired: bool | None = None,
    only_outright: bool | None = None,
    subscribed: bool | None = None,
    limit: int | None = None,
    offset: int | None = None,
    refresh: str | None = None,
) -> RequestSpec:
    """Pure: build spec for ``GET /instruments`` (D-01 / D-02 / D-03).

    ``authenticated=True`` gates Bearer injection in the Wave 3 shells;
    ``idempotent=True`` marks the GET read as retry-eligible. ``None`` optionals
    are dropped via ``_params.drop_none`` (D-02) preserving legitimate falsy
    filters (``include_expired=False`` / ``offset=0`` / ``""``); an empty dict
    collapses to ``params=None``. Booleans ride httpx-native ``True → "true"``
    encoding — explicit wire-encoding deferred to Phase 23 (D-03; no bool
    serializer copied from higyrus).
    """
    del state  # state-independent (filters come via kwargs)
    params = _params.drop_none(
        {
            "q": q,
            "segment": segment,
            "market_id": market_id,
            "include_expired": include_expired,
            "only_outright": only_outright,
            "subscribed": subscribed,
            "limit": limit,
            "offset": offset,
            "refresh": refresh,
        }
    )
    return RequestSpec(
        method="GET",
        path="/instruments",
        params=params or None,
        idempotent=True,
        endpoint_name="instruments",
        authenticated=True,
    )


def build_segments_request(state: _ClientState) -> RequestSpec:
    """Pure: build spec for ``GET /instruments/segments`` (D-01, no params).

    Same authenticated/idempotent contract as ``build_instruments_request`` but
    takes no filter kwargs — ``params`` stays ``None``.
    """
    del state  # state-independent
    return RequestSpec(
        method="GET",
        path="/instruments/segments",
        idempotent=True,
        endpoint_name="segments",
        authenticated=True,
    )


def build_symbols_request(
    state: _ClientState,
    *,
    active: bool | None = None,
    market_id: str | None = None,
    prefix: str | None = None,
) -> RequestSpec:
    """Pure: build spec for ``GET /symbols`` (D-01 / D-02 / D-03).

    ``None`` optionals dropped via ``_params.drop_none`` (D-02); a legit
    ``active=False`` is preserved, empty dict → ``params=None``. Booleans ride
    httpx-native encoding (D-03; no bool serializer copied from higyrus).
    """
    del state  # state-independent (filters come via kwargs)
    params = _params.drop_none(
        {
            "active": active,
            "market_id": market_id,
            "prefix": prefix,
        }
    )
    return RequestSpec(
        method="GET",
        path="/symbols",
        params=params or None,
        idempotent=True,
        endpoint_name="symbols",
        authenticated=True,
    )


def build_calendar_request(state: _ClientState, *, year: int | None = None) -> RequestSpec:
    """Pure: build spec for ``GET /calendar`` (D-01 / D-02).

    Single ``year`` filter dropped via ``_params.drop_none`` when ``None``; an
    empty dict collapses to ``params=None``.
    """
    del state  # state-independent (filter comes via kwarg)
    params = _params.drop_none({"year": year})
    return RequestSpec(
        method="GET",
        path="/calendar",
        params=params or None,
        idempotent=True,
        endpoint_name="calendar",
        authenticated=True,
    )


def build_calendar_config_request(state: _ClientState) -> RequestSpec:
    """Pure: build spec for ``GET /calendar/config`` (D-01, no params).

    Same authenticated/idempotent contract as the other reference reads but takes
    no filter kwargs — ``params`` stays ``None``.
    """
    del state  # state-independent
    return RequestSpec(
        method="GET",
        path="/calendar/config",
        idempotent=True,
        endpoint_name="calendar_config",
        authenticated=True,
    )


# ----------------------------------------------------------------------
# Calendar write builders (MUT-MD-02) — PUT/POST/DELETE, authenticated
# ----------------------------------------------------------------------
#
# Pure builders mirroring the Phase 25 symbols-write shape (``del state``, no
# I/O): the ones carrying a body take the ALREADY-serialized model dict as
# ``json_body`` (the shell serializes — NOT ``build_latest_batch_request``, which
# calls ``to_dict()`` inside the builder; Phase 25 is the precedent to follow).
# Idempotency is assigned per DM-03 / D-04: ``True`` for the config trio and for
# the holiday delete, ``False`` ONLY for ``POST /calendar/holidays`` (an append).
# The DELETE builders OMIT ``json_body`` entirely so it stays ``None`` — with
# httpx 0.28.1 that emits ``content == b""`` and NO ``Content-Type`` header,
# whereas ``json={}`` would emit ``b"{}"`` plus ``Content-Type: application/json``
# (D-02 / T-26-08). The mutation gate does NOT live here — the shell checks it
# before calling these.


def build_set_calendar_config_request(
    state: _ClientState, json_body: dict[str, Any]
) -> RequestSpec:
    """Pure: build spec for ``PUT /calendar/config`` (market hours replace, MUT-MD-02).

    ``idempotent=True`` (DM-03 / D-04 — a full replace is retry-safe; revalidated
    live in Phase 27); ``authenticated=True``. ``json_body`` is the
    already-serialized ``MarketHoursIn.to_dict()`` (the payload, not state).
    """
    del state  # state-independent (payload comes via json_body)
    return RequestSpec(
        method="PUT",
        path="/calendar/config",
        json_body=json_body,
        idempotent=True,
        endpoint_name="set_calendar_config",
        authenticated=True,
    )


def build_preview_calendar_config_request(
    state: _ClientState, json_body: dict[str, Any]
) -> RequestSpec:
    """Pure: build spec for ``POST /calendar/config/preview`` (dry-run, MUT-MD-02).

    A write expressed as POST that mutates nothing server-side, so it keeps the
    same ``idempotent=True`` / ``authenticated=True`` contract as
    ``build_set_calendar_config_request``; ``json_body`` is the already-serialized
    payload dict.

    ``idempotent=True`` **KEPT after measurement** (D-20). The armed run recorded
    that two previews of the SAME window returned DIFFERENT bodies on both
    surfaces (F-48 / F-58) and, correctly, left the cause unmeasured. It is
    adjudicated here rather than left dangling: the difference is CLOCK-DEPENDENT
    CONTENT, not persistence. The captured body shape
    (``preview-calendar-config-{sync,async}-response.json``) is
    ``{market_after:{is_open, local_time, next_transition, reason, session_close,
    session_open, state}, requires_confirmation, valid, warnings}`` — ``local_time``
    and ``next_transition`` are wall-clock projections that necessarily differ
    between two calls milliseconds apart. Nothing in that body is a resource
    identifier or a write receipt.

    The decisive evidence is independent of the hypothesis: the probe read
    ``GET /calendar/config`` before and after the double fire and compared it
    field by field, finding it IDENTICAL both times. Body inequality with config
    equality is exactly what a compute-only endpoint looks like, so the endpoint
    is replay-safe and the flag stands. The re-run reports the differing key
    NAMES (never values) so the adjudication is re-checkable rather than argued.
    """
    del state  # state-independent (payload comes via json_body)
    return RequestSpec(
        method="POST",
        path="/calendar/config/preview",
        json_body=json_body,
        idempotent=True,
        endpoint_name="preview_calendar_config",
        authenticated=True,
    )


def build_add_holidays_request(state: _ClientState, json_body: dict[str, Any]) -> RequestSpec:
    """Pure: build spec for ``POST /calendar/holidays`` (holiday UPSERT, MUT-MD-02).

    ``idempotent=True``, **corrected from ``False`` on measurement** (D-20). Phase
    26 reasoned that appending holidays would duplicate days under a replay and
    wrote the package's only ``idempotent=False``. The LIVE-MUT-01 armed run
    (2026-08-01) measured the opposite by ROW COUNT rather than by status code:
    two identical POSTs left **exactly 1 row** for ``2099-12-29`` and **1 row**
    for ``2099-12-30``, on both surfaces (F-49 / F-59). The endpoint UPSERTS by
    date. The live OpenAPI says the same in prose — *"Add or update calendar
    entries. Idempotent by date, so re-seeding is safe."* — and the measurement,
    not the prose, is what authorizes this flag (D-20: the spec's wording alone
    was never sufficient).

    Direction matters for severity. This flag was too CONSERVATIVE, not too
    permissive: the cost of the old value was a lost retry on a transient ``5xx``,
    never duplicated state. The safe direction was the prior state, and correcting
    it buys back retry coverage that the transport was already able to provide.

    The flag reaches the transport as ``request.extensions["idempotent"]``; with
    ``True`` the retry loop now runs instead of short-circuiting on its first line
    (T-26-07). ``authenticated=True``; ``json_body`` is the already-serialized
    ``HolidaysIn.to_dict()``.

    Note that no builder in this package carries ``idempotent=False`` any more.
    The short-circuit itself is therefore pinned directly at the transport, in
    ``tests/test_transport.py``, with a synthetic non-idempotent spec — otherwise
    this correction would have silently deleted the only proof that the flag does
    anything at all.
    """
    del state  # state-independent (payload comes via json_body)
    return RequestSpec(
        method="POST",
        path="/calendar/holidays",
        json_body=json_body,
        idempotent=True,
        endpoint_name="add_holidays",
        authenticated=True,
    )


def build_delete_calendar_config_request(state: _ClientState) -> RequestSpec:
    """Pure: build spec for ``DELETE /calendar/config`` (reset to defaults, MUT-MD-02).

    Zero-kwarg counterpart of ``build_calendar_config_request`` — no filters, no
    body. ``json_body`` is OMITTED on purpose so it stays ``None``: httpx then
    sends an empty body with no ``Content-Type``, whereas ``json_body={}`` would
    put ``b"{}"`` on the wire for the server to interpret (D-02 / T-26-08).
    ``idempotent=True`` (DM-03 — a reset replayed is still a reset).
    """
    del state  # state-independent
    return RequestSpec(
        method="DELETE",
        path="/calendar/config",
        idempotent=True,
        endpoint_name="delete_calendar_config",
        authenticated=True,
    )


# D-18: a ``day`` is ONE path segment. This is an allow-list of the characters a
# segment may contain, not an enumeration of hostile tokens — an enumeration is
# only ever as good as the reviewer's imagination and the first one shipped here
# missed both a lone ``.`` (RFC 3986 dot-segment removal DELETES the segment) and
# every percent-encoded form of the tokens it did list (``%2e%2e%2f`` → ``../``).
# The charset is RFC 3986 ``unreserved`` (ALPHA / DIGIT / ``-`` / ``.`` / ``_`` /
# ``~``): it needs no encoding to travel a path, so D-03's byte-for-byte
# interpolation stays intact for every legitimate ISO date. Everything else —
# ``/``, ``?``, ``#``, ``\``, whitespace, control and unicode characters, and
# critically ``%``, the percent-encoding introducer — is rejected by construction.
_DAY_SEGMENT_RE = re.compile(r"\A[A-Za-z0-9._~-]+\Z")


def build_delete_holiday_request(state: _ClientState, day: str) -> RequestSpec:
    """Pure: build spec for ``DELETE /calendar/holidays/{day}`` (MUT-MD-02).

    ``idempotent=True`` — declared by DM-03, and **KEPT after measurement**
    (D-20). The armed run found the second DELETE of the same day returns
    ``404`` on both surfaces (F-50 / F-60): the endpoint is idempotent in STATE
    (the day does not come back) but not in STATUS. That asymmetry was examined
    rather than waved through, because it is the one case where "idempotent"
    means two different things:

    * What the flag governs is REPLAY SAFETY OF STATE, and by that measure the
      endpoint qualifies — a replay cannot delete a second day, duplicate
      anything, or resurrect a row.
    * The observable wrinkle is that a retry issued after the first attempt
      already succeeded server-side but its response was lost meets a ``404``,
      which ``raise_for_response`` turns into :class:`MarketDataAPIError`. That
      is a change of ERROR IDENTITY, not a change of outcome: without the retry
      the caller would have received the transient ``5xx``/transport error and
      raised anyway. No caller ends up believing a delete happened when it did
      not, and none ends up deleting twice.
    * Flipping to ``False`` would therefore trade zero data-safety gain for the
      loss of retry coverage on genuine transient failures — strictly worse.

    ``tests/test_calendar_write.py::test_delete_holiday_retry_after_lost_response_surfaces_404``
    pins the wrinkle so it stays a documented, tested consequence instead of a
    surprise in production.

    ``authenticated=True``; ``json_body`` is OMITTED so it stays ``None`` and the
    DELETE goes out with an empty body and no ``Content-Type`` (D-02). The
    response is parsed by the tolerant passthrough
    :func:`parse_calendar_write_response`, not by any calendar-read parser (D-16).

    Path-safety guard (D-18 / T-26-01): ``day`` is interpolated RAW into the path
    — no percent-encoding, so a legitimate ISO date rides the wire byte for byte
    (D-03) — which makes an unvalidated ``day`` able to change WHICH endpoint runs.
    The guard is the ``_DAY_SEGMENT_RE`` charset allow-list plus an all-dots
    rejection, and it blocks exactly three failure modes, all verified against the
    pinned httpx 0.28.1:

    * **Segment retargeting.** ``day="../config"`` normalizes to
      ``DELETE /api/calendar/config`` — a market-config reset. Worse, a lone
      ``day="."`` is removed entirely by RFC 3986 dot-segment removal at
      ``build_request``, collapsing the request to ``DELETE /api/calendar/holidays``
      — the COLLECTION endpoint, i.e. a mutation the caller never asked for. Hence
      the ``day.strip(".")`` check: ``.`` and ``..`` are inside the charset (they
      are RFC 3986 ``unreserved``) but an all-dots segment is never a day.
    * **Percent-encoded escapes.** httpx preserves already-encoded sequences
      without double-encoding, so ``"%2e%2e%2fconfig"``, ``"%2Fconfig"`` and
      ``"config%3Fx=1"`` reach the wire and decode server-side to ``../config``,
      ``//config`` and a query string — the classic decode-then-route traversal
      (ASGI servers ``unquote()`` before routing). ``%`` is therefore not in the
      charset. ``\\`` is excluded for the same reason: WHATWG-normalizing proxies
      read it as ``/``.
    * **Non-``str`` input.** Untyped callers (notebooks, ``main_*.py``, config
      read from JSON) can arrive with an ``int`` or a ``list``; the ``isinstance``
      check turns both into the same path-safety refusal instead of a
      ``TypeError`` (or, for a ``list``, a silently interpolated ``repr``).

    The server's ``422`` is NOT a mitigation for any of these: the request never
    reaches the endpoint that would validate it. So the guard REJECTS rather than
    sanitizes — a plain :class:`ValueError` (the ``MarketData*`` hierarchy stays
    reserved for server contract errors, D-12) raised BEFORE the ``RequestSpec`` is
    built, naming only ``day`` and its value so no credential or client state
    leaks. Nothing is percent-encoded here, so the guard stays strictly narrower
    than a quoting escape, and it is NOT date-format validation: ``"2026-13-45"``
    passes and goes on to earn the server's ``422`` (D-13). ``%`` is excluded as
    the encoding introducer, not because of date shape.
    """
    if not isinstance(day, str) or not _DAY_SEGMENT_RE.fullmatch(day) or day.strip(".") == "":
        raise ValueError(f"day must be a single path segment, got {day!r}")
    del state  # state-independent
    return RequestSpec(
        method="DELETE",
        path=f"/calendar/holidays/{day}",
        idempotent=True,
        endpoint_name="delete_holiday",
        authenticated=True,
    )


# ----------------------------------------------------------------------
# Market-data read parsers (D-01) — client-stamped received_at
# ----------------------------------------------------------------------


@_decode._response_parser
def parse_market_data_response(resp: httpx.Response) -> list[MarketDataSnapshot]:
    """Pure: parse a ``GET /marketdata`` response → list of snapshots (D-01).

    Order mirrors ``parse_health_response`` (body-consume-then-raise) with the
    ``received_at`` stamp captured ONCE, between ``resp.read()`` and
    ``raise_for_response`` — the single wall-clock is threaded into EVERY
    snapshot so all rows from one response share the same stamp (D-01/D-02: the
    client owns the stamp). The develop wire wraps the rows in an envelope
    ``{count, items:[...], limit, offset, total}`` (LIVE-MD-01), so a dict body is
    unwrapped via ``items``; a bare-list body is still accepted as-is; a
    ``null``/empty/other body collapses to ``[]`` (collection guard).
    """
    resp.read()
    received_at = time.time()
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    if isinstance(raw, dict):
        rows = raw.get("items", [])
    elif isinstance(raw, list):
        rows = raw
    else:
        rows = []
    if not isinstance(rows, list):
        rows = []
    return [MarketDataSnapshot.from_api(item, received_at=received_at) for item in rows]


@_decode._response_parser
def parse_latest_response(resp: httpx.Response) -> list[MarketDataSnapshot]:
    """Pure: parse a ``GET/POST /marketdata/latest`` response → list of snapshots.

    Same one-stamp-per-response contract as ``parse_market_data_response``.
    Two confirmed live shapes (develop) are handled by one parser:

    * single-symbol ``GET /marketdata/latest`` returns a bare list ``[{...}]``,
      iterated as-is;
    * batch ``POST /marketdata/latest`` returns an envelope
      ``{requested, count, not_found, server_time, items:[...]}`` whose rows are
      unwrapped via ``items``.

    A dict body without ``items`` (or a non-list ``items``), a ``null``/empty, or
    any other body collapses to ``[]`` (collection guard — no KeyError). The
    ``not_found`` list is intentionally not surfaced here (batch omits not-found
    symbols); surfacing it would be a future enhancement requiring a return-type
    change.
    """
    resp.read()
    received_at = time.time()
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    if isinstance(raw, dict):
        rows = raw.get("items", [])
    elif isinstance(raw, list):
        rows = raw
    else:
        rows = []
    if not isinstance(rows, list):
        rows = []
    return [MarketDataSnapshot.from_api(item, received_at=received_at) for item in rows]


# ----------------------------------------------------------------------
# Reference-data read parsers (D-05 / D-06 / D-07) — NO received_at stamp
# ----------------------------------------------------------------------
#
# The four collection parsers replicate ``parse_market_data_response`` EXACTLY
# except they OMIT the ``received_at = time.time()`` stamp and call
# ``Model.from_api(item)`` with no ``received_at`` kwarg (D-05/D-06): reference
# data is unstamped. Body-consume-then-raise order is preserved; a ``null``/empty
# body collapses to ``[]`` (collection guard). ``parse_calendar_config_response``
# is the single-object exception (D-07).


@_decode._response_parser
def parse_instruments_response(resp: httpx.Response) -> list[Instrument]:
    """Pure: parse ``GET /instruments`` → ``list[Instrument]`` (D-05 / D-06).

    Body-consume-then-raise order; a 204 / ``null`` body collapses to ``[]``. No
    ``received_at`` stamp — reference data is unstamped (D-05).
    """
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    return [Instrument.from_api(item) for item in raw]


@_decode._response_parser
def parse_segments_response(resp: httpx.Response) -> list[Segment]:
    """Pure: parse ``GET /instruments/segments`` → ``list[Segment]`` (D-05 / D-06).

    Body-consume-then-raise order; a 204 / ``null`` body collapses to ``[]``. No
    ``received_at`` stamp — reference data is unstamped (D-05).
    """
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    return [Segment.from_api(item) for item in raw]


@_decode._response_parser
def parse_symbols_response(resp: httpx.Response) -> list[Symbol]:
    """Pure: parse any ``/symbols`` response → ``list[Symbol]`` (D-05 / D-06 / D-11).

    Serves FOUR endpoints with three different body shapes, all confirmed against
    the real develop wire in the LIVE-MUT-01 armed run (2026-08-01; baselines
    ``get-symbols-probe-prefix-*.json``, ``create-symbol-*-response.json``,
    ``create-symbols-batch-*-response.json``, ``update-symbol-*-response.json``):

    * ``GET /symbols`` returns a BARE LIST of rows — iterated as-is. This is the
      path the parser was originally written for and it was never the defect;
      it must not regress.
    * ``POST /symbols`` and ``PATCH /symbols/{symbol_id}`` return a FLAT SYMBOL
      OBJECT (``{active, created, id, market_id, note, symbol}`` /
      ``{active, id, market_id, note, symbol}``) — wrapped into a one-row list.
    * ``POST /symbols/batch`` returns an ENVELOPE
      ``{created, items:[{...}], note, reactivated, requested}`` — rows unwrapped
      via ``items``, exactly like ``parse_latest_response``.

    **The D-11 bug this fixes.** The previous body was
    ``[Symbol.from_api(item) for item in raw]``. Against a bare JSON OBJECT that
    iterates the object's KEYS, so every mutation produced one ALL-DEFAULT
    ``Symbol`` per key — measured live as *"body objeto JSON de 6 clave(s);
    parse_symbols_response devolvió 6 Symbol, 6 all-default"* on BOTH surfaces
    (F-41 / F-51). Same failure mode ``parse_calendar_response`` had before D-12.

    **The return type is UNCHANGED (D-22).** ``list[Symbol]`` is what v0.3.0
    published for ``create_symbol`` / ``create_symbols`` / ``update_symbol``, so
    the envelope is unwrapped rather than passed through — the non-breaking
    realization ``parse_latest_response`` already established. The envelope's
    scalar counters (``created``, ``reactivated``, ``requested``, ``note``) are
    intentionally NOT surfaced; doing so would require a return-type change and
    therefore a major bump.

    Discrimination is by KEY, not by guesswork: ``items`` marks the batch
    envelope, a top-level ``symbol`` marks a flat row. ``items`` wins if both are
    somehow present. Anything else — a dict with neither key, a non-list
    ``items``, an empty body, a ``null``, a scalar — collapses to ``[]`` rather
    than raising (collection guard: no ``KeyError``, no ``TypeError`` from
    iterating an ``int``). Body-consume-then-raise order is preserved so error
    statuses still raise before any decoding. No ``received_at`` client stamp —
    reference data is unstamped (D-05); ``Symbol.received_at`` is a wire field.
    """
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    rows: Any
    if isinstance(raw, dict):
        if isinstance(raw.get("items"), list):
            rows = raw["items"]
        elif "symbol" in raw:
            rows = [raw]
        else:
            rows = []
    elif isinstance(raw, list):
        rows = raw
    else:
        rows = []
    if not isinstance(rows, list):
        rows = []
    return [Symbol.from_api(item) for item in rows]


@_decode._response_parser
def parse_calendar_response(resp: httpx.Response) -> list[CalendarDay]:
    """Pure: parse ``GET /calendar`` → ``list[CalendarDay]`` (D-05 / D-06 / D-12).

    The develop wire wraps the rows in the object envelope
    ``{config, coverage, days[], market}`` (LIVE-MUT-01; the live OpenAPI declares
    the ``200`` as a bare ``object``, and the shape is committed under
    ``.planning/verification/schemas/market-data-client/get-calendar.json``), so a
    dict body is unwrapped via ``days``. This mirrors ``parse_latest_response``
    exactly — the only difference is the unwrap key (``days``, not ``items``).

    A bare-list body is still accepted as-is for compatibility; a dict without
    ``days`` (or a non-list ``days``), a ``null``/empty, or any other body
    collapses to ``[]`` (double collection guard — no ``KeyError``, no iteration
    over the envelope's KEYS, which is what produced all-default rows before the
    D-12 fix). Body-consume-then-raise order is preserved, so error statuses still
    raise before any decoding. No ``received_at`` stamp — reference data is
    unstamped (D-05).
    """
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    if isinstance(raw, dict):
        rows = raw.get("days", [])
    elif isinstance(raw, list):
        rows = raw
    else:
        rows = []
    if not isinstance(rows, list):
        rows = []
    return [CalendarDay.from_api(item) for item in rows]


@_decode._response_parser
def parse_calendar_config_response(resp: httpx.Response) -> CalendarConfig:
    """Pure: parse ``GET /calendar/config`` → a single ``CalendarConfig`` (D-07).

    The ONE non-collection reference parser: returns a single typed object, NOT a
    list. Uses the ``parse_health_response`` body-consume order but returns a
    tolerant model — an empty/None body collapses to ``CalendarConfig.from_api(None)``
    (the D-07 fallback), never a raise. No ``received_at`` stamp (D-05).
    """
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return CalendarConfig.from_api(None)
    raw = resp.json()
    return CalendarConfig.from_api(raw)


def parse_calendar_write_response(resp: httpx.Response) -> dict[str, Any]:
    """Pure: parse a calendar-write ``200`` → tolerant dict passthrough (D-06 / D-07).

    Serves BOTH holiday endpoints (``POST /calendar/holidays`` and
    ``DELETE /calendar/holidays/{day}``) — same contract, same tolerance, one
    function. The live OpenAPI declares every calendar-write ``200`` as a bare
    ``object`` with no schema, so there is nothing to type against until Phase 27
    (LIVE-MUT-01) captures the real shape; until then the body is handed back
    verbatim.

    Tolerance is deliberate (T-26-13): an absent body, a ``null``, a list or a
    scalar all degrade to an empty dict instead of raising a raw
    :class:`json.JSONDecodeError` or silently returning a value that contradicts
    the annotation. This is why it is a NEW function rather than a reuse of
    ``parse_health_response`` — that one copies only the body-consume-then-raise
    ORDER, not its (missing) guards. Transport errors keep flowing through
    ``raise_for_response`` (401/403 → Auth, 429 → RateLimit, 422 and the rest →
    API error) before any decoding happens.

    The config trio (``set`` / ``delete`` / ``preview``) does NOT use this parser:
    it reuses ``parse_calendar_config_response`` unmodified (D-05). Neither
    holiday endpoint is typed against the calendar-read model — that read pair is
    broken against the real wire (D-16).
    """
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return {}
    raw = resp.json()
    if not isinstance(raw, dict):
        return {}
    return raw
