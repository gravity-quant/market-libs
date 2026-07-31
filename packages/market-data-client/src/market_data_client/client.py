"""Cliente HTTP sincrónico para la API de market data (primary-extractor).

API basada en clase (Phase 20+)::

    from market_data_client import Client

    with Client() as client:
        health = client.get_health()

API a nivel módulo (delegación al default Client)::

    import market_data_client

    health = market_data_client.get_health()

Este paquete usa Auth0 con el grant ``client_credentials`` (machine-to-machine):
un ``POST`` al ``auth0_token_url`` ABSOLUTO con
``grant_type=client_credentials&client_id=...&client_secret=...&audience=...``
devuelve ``{"access_token", "expires_in"}``. El cliente cachea el
``access_token`` y lo refresca re-corriendo el mismo grant antes del
vencimiento — re-autenticar ES el refresh, sin token de rotación (D-05).

Variables de entorno (cargadas con ``python-dotenv``):

- ``MARKET_DATA_CLIENT_ID`` (requerido)
- ``MARKET_DATA_CLIENT_SECRET`` (requerido)
- ``MARKET_DATA_AUDIENCE`` (requerido)
- ``MARKET_DATA_AUTH0_TOKEN_URL`` (requerido — URL absoluta del token endpoint)
- ``MARKET_DATA_BASE_URL`` (opcional, default
  ``https://market-data-develop.bbsa.com.ar/api``).

El helper ``_raise_for_response`` es un alias module-level
(``= _core.raise_for_response`` — D-04) que preserva la identidad B8
(``aio._raise_for_response is client._raise_for_response is
_core.raise_for_response``) sin duplicar la lógica de mapeo de errores. La
auth-flow + dispatch de endpoints puros viven en ``market_data_client._core``.

Pitfall 1 (T-20-02): el grant de token despacha a la URL ABSOLUTA
``state.auth0_token_url``, NO a ``base_url + path`` — el token endpoint vive en
un host distinto (Auth0) que la API de market data.
"""

from __future__ import annotations

import uuid
from typing import Any, Self

import httpx
from dotenv import load_dotenv

from market_data_client import _core, _transport
from market_data_client._state import _REQUEST_TIMEOUT, _ClientState
from market_data_client.exceptions import MarketDataAuthError
from market_data_client.models import (
    CalendarConfig,
    CalendarDay,
    Instrument,
    LatestRequest,
    MarketDataSnapshot,
    Segment,
    Symbol,
)

load_dotenv()


# ----------------------------------------------------------------------
# Stateless helpers (D-04 alias — sourced from _core.py to preserve B8)
# ----------------------------------------------------------------------

# D-04: preserva la identidad B8. Los tests `aio._raise_for_response is
# client._raise_for_response` quedan verdes porque AMBOS aliases referencian
# el MISMO objeto (_core.raise_for_response).
_raise_for_response = _core.raise_for_response


# WR-06 carry-forward: validate max_retries kwarg early. Duplicated per package
# per the "no shared internals" project constraint (NOT imported from iol).
def _validate_max_retries(value: int) -> None:
    """Validate the ``max_retries`` kwarg.

    ``max_retries`` must be a non-negative ``int``. Negative values and non-int
    types (incl. ``float``, ``bool``) are rejected early with ``ValueError``
    instead of crashing later inside tenacity (T-21-03-01 mitigation).
    """
    if isinstance(value, bool):
        raise ValueError(
            f"max_retries must be a non-negative int, got {value!r} (bool not accepted)"
        )
    if not isinstance(value, int):
        raise ValueError(
            f"max_retries must be a non-negative int, got {value!r} (type={type(value).__name__})"
        )
    if value < 0:
        raise ValueError(f"max_retries must be a non-negative int, got {value!r}")


# ----------------------------------------------------------------------
# Client class
# ----------------------------------------------------------------------


class Client:
    """Sync client for the market-data REST API.

    Per-instance state lives in ``self._state`` (a :class:`_ClientState`
    dataclass). The class owns an ``httpx.Client`` lazily and the Auth0
    ``client_credentials`` token cache.

    Lifecycle: instances are context managers (``with Client() as c: ...``)
    and must be ``close()``d to release the underlying HTTP transport.
    ``close()`` is idempotent.
    """

    __slots__ = ("_is_view", "_max_retries", "_state")

    def __init__(
        self,
        *,
        base_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        audience: str | None = None,
        auth0_token_url: str | None = None,
        max_retries: int = 2,
    ) -> None:
        # WR-06: validate max_retries early (before any state mutation).
        _validate_max_retries(max_retries)
        self._state = _ClientState()
        if base_url is not None:
            self._state.base_url = base_url.rstrip("/")
        if client_id is not None:
            self._state.client_id = client_id
        if client_secret is not None:
            self._state.client_secret = client_secret
        if audience is not None:
            self._state.audience = audience
        if auth0_token_url is not None:
            self._state.auth0_token_url = auth0_token_url
        # D-08: max_retries=N → max_attempts=N+1 (1 initial + N retries).
        self._max_retries = max_retries
        # D-08: normally-constructed Clients are NOT views; with_options sets
        # this to True on the returned shared-view clone.
        self._is_view = False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Release the underlying ``httpx.Client`` (idempotent).

        D-08: views (constructed via ``with_options``) short-circuit here so
        ``view.close()`` / ``view.__exit__`` never tear down the parent's shared
        transport nor invalidate the parent's cached token (anti-Pitfall 13).
        ``getattr`` defensive for partially-initialized instances.
        """
        if getattr(self, "_is_view", False):
            return
        http_client = self._state.http_client
        if http_client is not None:
            assert isinstance(http_client, httpx.Client)
            http_client.close()
            self._state.http_client = None

    def __repr__(self) -> str:
        # Redact secret + token — never surface credentials in logs/reprs.
        secret_repr = "'***'" if self._state.client_secret else "''"
        token_repr = "'***'" if self._state.token else "None"
        return (
            f"MarketDataClient(base_url={self._state.base_url!r}, "
            f"client_id={self._state.client_id!r}, "
            f"client_secret={secret_repr}, "
            f"token={token_repr})"
        )

    # ------------------------------------------------------------------
    # HTTP transport + Auth0 client-credentials
    # ------------------------------------------------------------------

    def _ensure_http_client(self) -> httpx.Client:
        """Lazily create the per-instance ``httpx.Client``.

        Wraps ``RetryTransport`` so all requests (auth and endpoint) benefit
        from bounded retries + full-jitter backoff. The transport's mutation
        gate (D-01) honors ``request.extensions["idempotent"]`` so
        non-idempotent specs pass through with no retry loop.
        """
        http_client = self._state.http_client
        if http_client is not None:
            assert isinstance(http_client, httpx.Client)
            return http_client
        new_client = httpx.Client(
            timeout=_REQUEST_TIMEOUT,
            transport=_transport.RetryTransport(max_attempts=self._max_retries + 1),
        )
        self._state.http_client = new_client
        return new_client

    def with_options(self, *, max_retries: int) -> Self:
        """Return a shared-view clone with an overridden ``max_retries``.

        D-08 (iol Phase-13 pattern, mirrored — NOT imported): the view shares
        this Client's ``_state`` (incl. cached ``token``, ``token_expires_at``,
        and the underlying ``httpx.Client``). No re-auth, no second TCP
        connection pool (anti-Pitfall 13). Only the per-call ``max_retries``
        differs; the parent's ``_max_retries`` stays at its constructor value.

        The view's ``_max_retries`` is threaded into the shell's ``_request()``
        and ``_send_auth_request()`` via ``request.extensions["max_attempts"]``
        so the ``RetryTransport`` honors it per-call (LOAD-BEARING — without the
        extension threading ``with_options`` is a silent no-op). The mapping is
        ``max_retries=N → max_attempts=N+1`` (1 initial + N retries).

        ``view.close()`` / ``view.__exit__`` are no-ops so the view never tears
        down the parent's shared transport; the parent owns the pool.

            data = client.with_options(max_retries=5).get_market_data(...)
            data = client.with_options(max_retries=0).get_latest(...)  # no retries
        """
        # WR-06 carry-forward: validate early so the error is a clean ValueError
        # before view construction.
        _validate_max_retries(max_retries)
        view = type(self).__new__(type(self))
        view._state = self._state  # SHARE — anti-Pitfall 13
        view._max_retries = max_retries  # OVERRIDE
        view._is_view = True  # FLAG for close()/__exit__ no-op (D-08)
        return view

    def _send_auth_request(self, spec: _core.RequestSpec) -> httpx.Response:
        """Dispatch the Auth0 grant to the ABSOLUTE ``auth0_token_url``.

        Pitfall 1 (T-20-02, CRITICAL): the token grant POSTs to
        ``self._state.auth0_token_url`` (an absolute Auth0 URL on a different
        host than ``base_url``), NOT ``f"{base_url}{spec.path}"``. The grant
        request carries NO ``Authorization`` header — auth-flow establishes the
        token. ``idempotent=True`` (from the spec) makes a transient 5xx on the
        grant retry-eable through the ``RetryTransport``.
        """
        http = self._ensure_http_client()
        request_id = uuid.uuid4().hex
        req = http.build_request(
            spec.method,
            self._state.auth0_token_url,
            data=spec.data,
            headers=spec.headers,
        )
        req.extensions["idempotent"] = spec.idempotent
        req.extensions["request_id"] = request_id
        req.extensions["endpoint_name"] = spec.endpoint_name
        # D-08 LOAD-BEARING: per-call retry cap; parent or view path both set it.
        # Auth-flow specs are idempotent=True so the view's cap applies here too.
        req.extensions["max_attempts"] = self._max_retries + 1
        return http.send(req)

    def _authenticate(self) -> str:
        """Run the Auth0 ``client_credentials`` grant and cache the token.

        Builds the grant via ``_core.build_token_request``, dispatches it to the
        absolute ``auth0_token_url`` via ``_send_auth_request``, parses the
        2-tuple ``(token, expires_at)``, writes it to state, and returns the
        token. Re-running this grant IS the refresh (D-05 — no rotation token).
        """
        spec = _core.build_token_request(self._state)
        resp = self._send_auth_request(spec)
        token, expires_at = _core.parse_token_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        return token

    def _ensure_token(self) -> None:
        """No-op when the cached token is fresh; else re-run the grant.

        Gates on ``_core.token_is_fresh`` (which bakes in the 60 s TTL buffer);
        a stale/absent token triggers a full ``_authenticate()`` re-grant
        (T-20-03).
        """
        if _core.token_is_fresh(self._state):
            return
        self._authenticate()

    def _request(self, spec: _core.RequestSpec) -> httpx.Response:
        """Dispatch a request against ``base_url`` with per-spec auth branching.

        Two branches gated on ``spec.authenticated`` (D-08/D-09, Pitfall 4):

        - ``authenticated is True``: ensure a fresh token, inject
          ``Authorization: Bearer <token>``; on a first ``MarketDataAuthError``
          (401/403) clear the cached token, re-auth ONCE, retry the SAME request
          once, and re-raise on a second 401 (no recursion/infinite loop).
        - ``authenticated is False`` (health): NO ``_ensure_token()``, NO
          ``Authorization`` header; a 401 raises immediately (the ``if not
          spec.authenticated: raise`` carve-out fires FIRST — a health 401 is a
          real error, never a stale-token signal).

        Body-consume-then-raise (Phase 7 D-06): ``resp.read()`` precedes every
        ``_raise_for_response`` in the re-auth carve-out so the surfacing error
        already has a fully-consumed body (HTTP/2-safe).
        """
        headers = dict(spec.headers or {})
        if spec.authenticated:
            self._ensure_token()
            assert self._state.token is not None
            headers["Authorization"] = f"Bearer {self._state.token}"

        request_id = uuid.uuid4().hex
        http = self._ensure_http_client()
        url = f"{self._state.base_url}{spec.path}"
        req = http.build_request(
            spec.method,
            url,
            params=spec.params,
            json=spec.json_body,
            headers=headers,
        )
        req.extensions["idempotent"] = spec.idempotent
        req.extensions["request_id"] = request_id
        req.extensions["endpoint_name"] = spec.endpoint_name
        # D-08 LOAD-BEARING: per-call retry cap; parent or view path both set it.
        req.extensions["max_attempts"] = self._max_retries + 1
        resp = http.send(req)
        try:
            _raise_for_response(resp)
        except MarketDataAuthError:
            # Pitfall 4: an anonymous (health) 401 is a REAL error — raise before
            # any re-auth carve-out. There is no token to refresh.
            if not spec.authenticated:
                raise
            # Exactly-one re-auth: consume body, clear token, re-authenticate,
            # retry the SAME request once. A persistent 401 re-raises below.
            resp.read()
            self._state.token = None
            self._ensure_token()
            assert self._state.token is not None
            req.headers["Authorization"] = f"Bearer {self._state.token}"
            resp = http.send(req)
            resp.read()
            _raise_for_response(resp)
        return resp

    # ------------------------------------------------------------------
    # Public endpoint methods — health (anonymous, CORE-MD-01)
    # ------------------------------------------------------------------

    def get_health(self) -> dict[str, Any]:
        """Reach ``GET {base_url}/health`` anonymously via the retry transport."""
        spec = _core.build_health_request(self._state)
        resp = self._request(spec)
        return _core.parse_health_response(resp)

    def get_health_feed(self) -> dict[str, Any]:
        """Reach ``GET {base_url}/health/feed`` anonymously via the retry transport."""
        spec = _core.build_health_feed_request(self._state)
        resp = self._request(spec)
        return _core.parse_health_response(resp)

    # ------------------------------------------------------------------
    # Public endpoint methods — market-data reads (authenticated, D-06)
    # ------------------------------------------------------------------

    def get_market_data(
        self,
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
    ) -> list[MarketDataSnapshot]:
        """Authenticated ``GET {base_url}/marketdata`` → list of snapshots (D-06).

        Optional filters are dropped when ``None`` (``_params.drop_none`` in the
        builder); bools ride httpx's native ``True → "true"`` encoding. The
        Bearer is injected by ``_request`` (authenticated spec) and the per-call
        retry cap is threaded via ``with_options`` when used.
        """
        spec = _core.build_market_data_request(
            self._state,
            market_id=market_id,
            prefix=prefix,
            active=active,
            entries=entries,
            max_staleness_seconds=max_staleness_seconds,
            with_data=with_data,
            order=order,
            limit=limit,
            offset=offset,
        )
        resp = self._request(spec)
        return _core.parse_market_data_response(resp)

    def get_latest(
        self,
        *,
        symbol: str,
        market_id: str | None = None,
        entries: str | None = None,
    ) -> list[MarketDataSnapshot]:
        """Authenticated ``GET {base_url}/marketdata/latest`` → list of snapshots (D-06)."""
        spec = _core.build_latest_request(
            self._state,
            symbol=symbol,
            market_id=market_id,
            entries=entries,
        )
        resp = self._request(spec)
        return _core.parse_latest_response(resp)

    def get_latest_batch(self, latest_request: LatestRequest) -> list[MarketDataSnapshot]:
        """Authenticated batch ``POST {base_url}/marketdata/latest`` → list of snapshots.

        A read expressed as POST (the batch body doesn't fit a query string); the
        builder marks it ``idempotent=True`` so it is replay-safe. The typed
        :class:`LatestRequest` serializes to the wire body via ``to_dict``.
        """
        spec = _core.build_latest_batch_request(self._state, latest_request)
        resp = self._request(spec)
        return _core.parse_latest_response(resp)

    # ------------------------------------------------------------------
    # Public endpoint methods — reference-data reads (authenticated, D-06/D-07)
    # ------------------------------------------------------------------

    def get_instruments(
        self,
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
    ) -> list[Instrument]:
        """Authenticated ``GET {base_url}/instruments`` → list of instruments (D-06)."""
        spec = _core.build_instruments_request(
            self._state,
            q=q,
            segment=segment,
            market_id=market_id,
            include_expired=include_expired,
            only_outright=only_outright,
            subscribed=subscribed,
            limit=limit,
            offset=offset,
            refresh=refresh,
        )
        resp = self._request(spec)
        return _core.parse_instruments_response(resp)

    def get_segments(self) -> list[Segment]:
        """Authenticated ``GET {base_url}/instruments/segments`` → list of segments (D-06)."""
        spec = _core.build_segments_request(self._state)
        resp = self._request(spec)
        return _core.parse_segments_response(resp)

    def get_symbols(
        self,
        *,
        active: bool | None = None,
        market_id: str | None = None,
        prefix: str | None = None,
    ) -> list[Symbol]:
        """Authenticated ``GET {base_url}/symbols`` → list of symbols (D-06)."""
        spec = _core.build_symbols_request(
            self._state,
            active=active,
            market_id=market_id,
            prefix=prefix,
        )
        resp = self._request(spec)
        return _core.parse_symbols_response(resp)

    def get_calendar(self, *, year: int | None = None) -> list[CalendarDay]:
        """Authenticated ``GET {base_url}/calendar`` → list of calendar days (D-06)."""
        spec = _core.build_calendar_request(self._state, year=year)
        resp = self._request(spec)
        return _core.parse_calendar_response(resp)

    def get_calendar_config(self) -> CalendarConfig:
        """Authenticated ``GET {base_url}/calendar/config`` → single config object (D-07)."""
        spec = _core.build_calendar_config_request(self._state)
        resp = self._request(spec)
        return _core.parse_calendar_config_response(resp)


# ----------------------------------------------------------------------
# Default-client lazy singleton + top-level shims
# ----------------------------------------------------------------------


_default_client: Client | None = None


def _get_default() -> Client:
    """Lazy access to the module-level default Client (env-var constructed)."""
    global _default_client
    if _default_client is None:
        _default_client = Client()
    return _default_client


def configure(
    *,
    base_url: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    audience: str | None = None,
    auth0_token_url: str | None = None,
    token: str | None = None,
    token_expires_at: float | None = None,
    http_client: httpx.Client | None = None,
) -> None:
    """Sobrescribe credenciales/URLs en runtime con semántica carry-forward.

    Carry-forward: los campos ``None`` se ignoran; los demás sobrescriben en el
    ``_default_client._state``. ``configure()`` es el ÚNICO punto de mutación
    controlada (CORE-MD-01). Rotar cualquier credencial/URL (``base_url``,
    ``client_id``, ``client_secret``, ``audience``, ``auth0_token_url``)
    invalida el token cacheado (``token=None`` + ``token_expires_at=0.0``), a
    menos que ``token``/``token_expires_at`` se pasen explícitamente (el conftest
    los siembra para tests sin re-auth) — T-20-03.

    ``http_client`` se usa AS-IS (sin auto-wrap con ``RetryTransport``); el
    cliente cacheado previo se cierra antes de reemplazarlo.
    """
    client = _get_default()
    state = client._state
    rotated = False
    if base_url is not None:
        state.base_url = base_url.rstrip("/")
        rotated = True
    if client_id is not None:
        state.client_id = client_id
        rotated = True
    if client_secret is not None:
        state.client_secret = client_secret
        rotated = True
    if audience is not None:
        state.audience = audience
        rotated = True
    if auth0_token_url is not None:
        state.auth0_token_url = auth0_token_url
        rotated = True
    # Rotar credenciales invalida el token cacheado, salvo que el caller siembre
    # explícitamente token/token_expires_at (test seeding).
    if rotated and token is None and token_expires_at is None:
        state.token = None
        state.token_expires_at = 0.0
    if token is not None:
        state.token = token
    if token_expires_at is not None:
        state.token_expires_at = token_expires_at
    if http_client is not None:
        if state.http_client is not None:
            assert isinstance(state.http_client, httpx.Client)
            state.http_client.close()
        state.http_client = http_client


def get_health() -> dict[str, Any]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_health()


def get_health_feed() -> dict[str, Any]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_health_feed()


def get_market_data(
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
) -> list[MarketDataSnapshot]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_market_data(
        market_id=market_id,
        prefix=prefix,
        active=active,
        entries=entries,
        max_staleness_seconds=max_staleness_seconds,
        with_data=with_data,
        order=order,
        limit=limit,
        offset=offset,
    )


def get_latest(
    *,
    symbol: str,
    market_id: str | None = None,
    entries: str | None = None,
) -> list[MarketDataSnapshot]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_latest(symbol=symbol, market_id=market_id, entries=entries)


def get_latest_batch(latest_request: LatestRequest) -> list[MarketDataSnapshot]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_latest_batch(latest_request)


def get_instruments(
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
) -> list[Instrument]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_instruments(
        q=q,
        segment=segment,
        market_id=market_id,
        include_expired=include_expired,
        only_outright=only_outright,
        subscribed=subscribed,
        limit=limit,
        offset=offset,
        refresh=refresh,
    )


def get_segments() -> list[Segment]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_segments()


def get_symbols(
    *,
    active: bool | None = None,
    market_id: str | None = None,
    prefix: str | None = None,
) -> list[Symbol]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_symbols(active=active, market_id=market_id, prefix=prefix)


def get_calendar(*, year: int | None = None) -> list[CalendarDay]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_calendar(year=year)


def get_calendar_config() -> CalendarConfig:
    """Top-level shim: delega al default Client."""
    return _get_default().get_calendar_config()
