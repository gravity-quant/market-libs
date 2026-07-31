"""Cliente HTTP asincrónico para la API de market data (primary-extractor).

Espejo async de ``client.py`` (Wave 3) con estado singleton por instancia
INDEPENDIENTE de la superficie sync — no hay estado mutable compartido entre
``Client`` y ``AsyncClient`` por construcción.

Flujo de auth (Auth0 client-credentials, D-05): un único grant
``client_credentials`` (machine-to-machine), sin credenciales de usuario ni
rotación de refresh. El grant se despacha a la URL ABSOLUTA
``state.auth0_token_url`` (Pitfall 1 / T-20-02) — NUNCA a ``base_url`` — para
que el Bearer nunca viaje al host equivocado. El token se cachea y se refresca
por TTL (``expires_in``, con fallback), y el re-auth concurrente se serializa
con el ``asyncio.Lock`` per-loop double-checked (D-12 — NO el primitivo de
concurrencia de 3-vías de matriz)::

    from market_data_client import aio

    async with aio.AsyncClient() as c:
        health = await c.get_health()

Locks (Pitfall 2): ``self._state.token_lock`` y ``self._state.client_lock`` se
crean LAZY en el primer uso async (NO en ``__init__``) para bindear al event
loop que esté corriendo cuando la autenticación ocurre por primera vez.

B8 (D-04): ``_raise_for_response`` es el MISMO objeto que en la superficie sync
(``_core.raise_for_response``) — no se duplica.

Cleanup contract: caller-responsible. Usar ``async with`` o ``await c.aclose()``.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Self
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv

from market_data_client import _atransport, _core
from market_data_client._core import RequestSpec
from market_data_client._state import _REQUEST_TIMEOUT, _ClientState
from market_data_client.exceptions import (
    MarketDataAuthError,
    MarketDataMutationNotAllowedError,
)
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

# B8 (D-04): mismo objeto que la superficie sync — el invariante
# ``aio._raise_for_response is client._raise_for_response is
# _core.raise_for_response`` se preserva. Consumido por ``_request`` (Task 2).
_raise_for_response = _core.raise_for_response


# WR-06 carry-forward: valida el kwarg ``max_retries`` temprano. Duplicado por
# paquete por el constraint "no shared internals" (NO se importa de client.py ni
# de iol). Espeja verbatim ``client._validate_max_retries``.
def _validate_max_retries(value: int) -> None:
    """Valida el kwarg ``max_retries``.

    ``max_retries`` debe ser un ``int`` no-negativo. Valores negativos y tipos
    no-int (incl. ``float``, ``bool``) se rechazan temprano con ``ValueError`` en
    vez de crashear más tarde dentro de tenacity (mitigación T-21-03-01).
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


class AsyncClient:
    """Cliente async para la API de market data.

    El estado por instancia vive en ``self._state`` (misma forma
    :class:`_ClientState` que el sync ``Client`` pero una INSTANCIA distinta).

    Pickle / deepcopy NO soportado (``httpx.AsyncClient`` posee un pool TCP +
    contexto SSL atados a un event loop específico).
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
        token: str | None = None,
        token_expires_at: float | None = None,
        http_client: httpx.AsyncClient | None = None,
        mutating_allowed: bool | None = None,
        expected_host: str | None = None,
        max_retries: int = 2,
    ) -> None:
        # WR-06: valida max_retries temprano (antes de mutar estado).
        _validate_max_retries(max_retries)
        # NO se crea ningún asyncio.Lock acá (Pitfall 2 — se bindearía al loop
        # vivo en construcción). Los locks se crean lazy en el primer uso async.
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
        # Gate de mutaciones (D-13/D-15): sentinel None = "no cambiar". Espeja
        # verbatim la superficie sync — un _ClientState fresco ya default-ea
        # mutating_allowed=False y expected_host al host develop.
        if mutating_allowed is not None:
            self._state.mutating_allowed = mutating_allowed
        if expected_host is not None:
            self._state.expected_host = expected_host
        if token is not None:
            self._state.token = token
        if token_expires_at is not None:
            self._state.token_expires_at = token_expires_at
        if http_client is not None:
            self._state.http_client = http_client
        # D-08: max_retries=N → max_attempts=N+1 (1 intento inicial + N reintentos).
        self._max_retries = max_retries
        # D-08: los AsyncClient construidos normalmente NO son views; with_options
        # setea esto en True sobre el shared-view clone que retorna.
        self._is_view = False

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
        """Libera el ``httpx.AsyncClient`` subyacente (idempotente).

        D-08: los views (construidos vía ``with_options``) short-circuitan acá,
        así ``view.aclose()`` / ``view.__aexit__`` NUNCA cierran el transport
        compartido del parent ni invalidan su token cacheado (anti-Pitfall 13).
        ``getattr`` defensivo para instancias parcialmente inicializadas.
        """
        if getattr(self, "_is_view", False):
            return
        http_client = self._state.http_client
        if http_client is not None:
            assert isinstance(http_client, httpx.AsyncClient)
            await http_client.aclose()
            self._state.http_client = None

    def with_options(self, *, max_retries: int) -> Self:
        """Retorna un shared-view clone con un ``max_retries`` sobrescrito.

        D-08 (patrón iol Phase-13, espejado — NO importado): el view comparte el
        ``_state`` de este AsyncClient (incl. token cacheado, ``token_expires_at``,
        el ``httpx.AsyncClient`` subyacente Y los ``asyncio.Lock`` per-loop que ya
        viven en ``_state`` — el view hereda LOS MISMOS locks, sin lock-hoisting).
        Sin re-auth, sin segundo pool TCP (anti-Pitfall 13). Sólo difiere el
        ``max_retries`` per-call; el ``_max_retries`` del parent queda en su valor
        de constructor.

        El ``_max_retries`` del view se thread-ea al shell (``_request`` y
        ``_send_auth_request``) vía ``request.extensions["max_attempts"]`` para que
        el ``AsyncRetryTransport`` lo honre per-call (LOAD-BEARING — sin el
        threading ``with_options`` es un no-op silencioso). El mapeo es
        ``max_retries=N → max_attempts=N+1``.

        ``view.aclose()`` / ``view.__aexit__`` son no-ops así el view nunca cierra
        el transport compartido del parent; el parent es dueño del pool.

            data = await client.with_options(max_retries=5).get_market_data(...)
            data = await client.with_options(max_retries=0).get_latest(...)  # sin reintentos
        """
        # WR-06 carry-forward: valida temprano así el error es un ValueError limpio
        # antes de construir el view.
        _validate_max_retries(max_retries)
        view = type(self).__new__(type(self))
        view._state = self._state  # SHARE — anti-Pitfall 13
        view._max_retries = max_retries  # OVERRIDE
        view._is_view = True  # FLAG para el no-op de aclose()/__aexit__ (D-08)
        return view

    # ------------------------------------------------------------------
    # Mutation gate (GATE-MD-01 — D-04/D-05/D-15)
    # ------------------------------------------------------------------

    def _ensure_mutation_allowed(self) -> None:
        """Rechaza mutaciones sin opt-in o hacia un host inesperado (D-04/D-05).

        Espejo VERBATIM del helper sync (D-15). Es una lectura PURA de estado
        (SIN ``await``, SIN IO): NO emite request HTTP NI round-trip a Auth0 en
        refusal ni en éxito. Debe ser la PRIMERA sentencia (no-awaited) de cada
        método mutador (cableado en el Plan 03), antes de ``_core.build_*`` y de
        cualquier ``_ensure_token``.

        Dos patas:
          1. ``mutating_allowed`` debe ser True (refuse-by-default, D-13).
          2. El host de ``base_url`` debe coincidir EXACTAMENTE con
             ``expected_host`` (D-01, security-load-bearing) vía
             ``urlsplit(...).hostname`` — NUNCA substring ni ``endswith``. Un
             ``expected_host`` en ``None`` deshabilita SÓLO esta segunda pata.
        """
        if not self._state.mutating_allowed:
            raise MarketDataMutationNotAllowedError(
                "Mutación rechazada: seteá mutating_allowed=True (constructor o configure())."
            )
        expected = self._state.expected_host
        actual = urlsplit(self._state.base_url).hostname
        if expected is not None and actual != expected:
            raise MarketDataMutationNotAllowedError(
                f"Mutación rechazada: host de base_url {actual!r} != expected_host {expected!r}."
            )

    # ------------------------------------------------------------------
    # HTTP transport + lazy per-loop locks
    # ------------------------------------------------------------------

    def _ensure_client_lock(self) -> asyncio.Lock:
        """Crea el lock del http-client lazy (bind al loop corriente)."""
        if self._state.client_lock is None:
            self._state.client_lock = asyncio.Lock()
        return self._state.client_lock

    def _ensure_token_lock(self) -> asyncio.Lock:
        """Crea el lock del token lazy (bind al loop corriente, Pitfall 2)."""
        if self._state.token_lock is None:
            self._state.token_lock = asyncio.Lock()
        return self._state.token_lock

    async def _ensure_http_client(self) -> httpx.AsyncClient:
        """Crea lazy el ``httpx.AsyncClient`` con ``AsyncRetryTransport``.

        Double-checked locking (``self._state.client_lock``): la instanciación
        corre DENTRO del bloque protegido por el lock para que callers
        concurrentes en el primer uso corran una única asignación.
        """
        http_client = self._state.http_client
        if http_client is not None:
            assert isinstance(http_client, httpx.AsyncClient)
            return http_client
        client_lock = self._ensure_client_lock()
        async with client_lock:
            http_client = self._state.http_client
            if http_client is not None:
                assert isinstance(http_client, httpx.AsyncClient)
                return http_client
            new_client = httpx.AsyncClient(
                timeout=_REQUEST_TIMEOUT,
                transport=_atransport.AsyncRetryTransport(max_attempts=self._max_retries + 1),
            )
            self._state.http_client = new_client
            return new_client

    # ------------------------------------------------------------------
    # Auth0 client-credentials grant (async, double-checked locking)
    # ------------------------------------------------------------------

    async def _send_auth_request(self, spec: RequestSpec) -> httpx.Response:
        """Despacha el grant a la URL ABSOLUTA ``state.auth0_token_url``.

        Pitfall 1 / T-20-02: el grant va al host absoluto de Auth0, NO a
        ``base_url``. Propaga ``idempotent``/``endpoint_name``/``request_id``
        pero NO setea ``max_attempts`` (no hay override per-call). Sin header
        ``Authorization`` — el grant establece el token.
        """
        http = await self._ensure_http_client()
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
        # D-08 LOAD-BEARING: cap de reintentos per-call; parent o view lo setean.
        # Los specs de auth-flow son idempotent=True, así el cap del view aplica acá.
        req.extensions["max_attempts"] = self._max_retries + 1
        return await http.send(req)

    async def _authenticate_unlocked(self) -> str:
        """El caller DEBE tener tomado ``self._state.token_lock``.

        Un único grant ``client_credentials`` (D-05): construye el spec vía
        ``_core.build_token_request``, despacha a la URL absoluta, parsea el
        2-tuple y escribe ``state.token``/``token_expires_at``. Sin refresh
        rotation ni disk cache.
        """
        spec = _core.build_token_request(self._state)
        resp = await self._send_auth_request(spec)
        token, expires_at = _core.parse_token_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        return token

    async def _aensure_token(self) -> None:
        """Asegura un token fresco con double-checked locking (D-12).

        Fast-path: retorna si ``token_is_fresh``. Si no, toma el token lock y
        RE-CHECKEA ``token_is_fresh`` DENTRO del lock antes de autenticar —
        previene el thundering-herd de re-auth concurrente (T-20-08).
        """
        if _core.token_is_fresh(self._state):
            return
        lock = self._ensure_token_lock()
        async with lock:
            if _core.token_is_fresh(self._state):
                return
            await self._authenticate_unlocked()

    # ------------------------------------------------------------------
    # Request dispatch (authenticated branch + exactly-once 401 re-auth)
    # ------------------------------------------------------------------

    async def _request(self, spec: RequestSpec) -> httpx.Response:
        """Despacha un request async ramificando sobre ``spec.authenticated``.

        Autenticado (D-08/D-09): ``await self._aensure_token()`` + inyecta el
        header ``Authorization: Bearer``. En el primer ``MarketDataAuthError``
        limpia el token bajo el token lock, re-autentica EXACTAMENTE una vez,
        reenvía una vez y re-levanta si el segundo response vuelve a dar 401
        (sin recursión — Pitfall 4). Anónimo (health): sin ``_aensure_token`` ni
        header ``Authorization``; un 401 levanta inmediatamente.
        """
        http = await self._ensure_http_client()
        token_lock = self._ensure_token_lock()
        if spec.authenticated:
            await self._aensure_token()
            async with token_lock:
                token = self._state.token
            assert token is not None
            # D-09 (Pitfall 3): el token se spread-ea AL FINAL así SIEMPRE gana —
            # un ``Authorization`` en ``spec.headers`` nunca puede shadow-ear el
            # token fresco (T-21-04-01, alto). Alineado a la superficie sync.
            headers = {**(spec.headers or {}), "Authorization": f"Bearer {token}"}
        else:
            token = None
            headers = dict(spec.headers or {})

        request_id = uuid.uuid4().hex
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
        # D-08 LOAD-BEARING: cap de reintentos per-call; parent o view lo setean.
        req.extensions["max_attempts"] = self._max_retries + 1
        resp = await http.send(req)
        try:
            _raise_for_response(resp)
        except MarketDataAuthError:
            # Health (anónimo) NO re-autentica — un 401 es definitivo.
            if not spec.authenticated:
                raise
            # body-consume antes del carve-out (D-06).
            await resp.aread()
            # Exactamente-un re-auth bajo el token lock (double-checked serializa
            # el re-auth concurrente, T-20-08). Re-checkeo: otra corrutina pudo
            # ya haber rotado el token — en ese caso sólo reintentamos.
            async with token_lock:
                if self._state.token is None or self._state.token == token:
                    self._state.token = None
                    await self._authenticate_unlocked()
                new_token = self._state.token
            assert new_token is not None
            req.headers["Authorization"] = f"Bearer {new_token}"
            resp = await http.send(req)
            # body-consume del segundo response antes del segundo raise.
            await resp.aread()
            _raise_for_response(resp)
        return resp

    # ------------------------------------------------------------------
    # Public health endpoints (anonymous)
    # ------------------------------------------------------------------

    async def get_health(self) -> dict[str, Any]:
        """Estado de salud del servicio (anónimo, D-08/D-09)."""
        spec = _core.build_health_request(self._state)
        resp = await self._request(spec)
        return _core.parse_health_response(resp)

    async def get_health_feed(self) -> dict[str, Any]:
        """Estado de salud del feed de datos (anónimo, D-08/D-09)."""
        spec = _core.build_health_feed_request(self._state)
        resp = await self._request(spec)
        return _core.parse_health_response(resp)

    # ------------------------------------------------------------------
    # Public endpoint methods — market-data reads (authenticated, D-06)
    # ------------------------------------------------------------------

    async def get_market_data(
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
        """Autenticado ``GET {base_url}/marketdata`` → lista de snapshots (D-06).

        Espejo async de ``client.get_market_data``. Los filtros opcionales se
        dropean cuando son ``None`` (``_params.drop_none`` en el builder); los
        bools usan el encoding nativo de httpx (``True → "true"``). El Bearer lo
        inyecta ``_request`` (spec autenticado) y el cap de reintentos per-call se
        thread-ea vía ``with_options`` cuando se usa.
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
        resp = await self._request(spec)
        return _core.parse_market_data_response(resp)

    async def get_latest(
        self,
        *,
        symbol: str,
        market_id: str | None = None,
        entries: str | None = None,
    ) -> list[MarketDataSnapshot]:
        """Autenticado ``GET {base_url}/marketdata/latest`` → lista de snapshots (D-06)."""
        spec = _core.build_latest_request(
            self._state,
            symbol=symbol,
            market_id=market_id,
            entries=entries,
        )
        resp = await self._request(spec)
        return _core.parse_latest_response(resp)

    async def get_latest_batch(self, latest_request: LatestRequest) -> list[MarketDataSnapshot]:
        """Autenticado batch ``POST {base_url}/marketdata/latest`` → lista de snapshots.

        Un read expresado como POST (el body del batch no entra en el query
        string); el builder lo marca ``idempotent=True`` así es replay-safe. El
        :class:`LatestRequest` tipado serializa al body via ``to_dict``.
        """
        spec = _core.build_latest_batch_request(self._state, latest_request)
        resp = await self._request(spec)
        return _core.parse_latest_response(resp)

    # ------------------------------------------------------------------
    # Public endpoint methods — reference-data reads (authenticated, D-06/D-07)
    # ------------------------------------------------------------------

    async def get_instruments(
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
        """Autenticado ``GET {base_url}/instruments`` → lista de instrumentos (D-06)."""
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
        resp = await self._request(spec)
        return _core.parse_instruments_response(resp)

    async def get_segments(self) -> list[Segment]:
        """Autenticado ``GET {base_url}/instruments/segments`` → lista de segmentos (D-06)."""
        spec = _core.build_segments_request(self._state)
        resp = await self._request(spec)
        return _core.parse_segments_response(resp)

    async def get_symbols(
        self,
        *,
        active: bool | None = None,
        market_id: str | None = None,
        prefix: str | None = None,
    ) -> list[Symbol]:
        """Autenticado ``GET {base_url}/symbols`` → lista de símbolos (D-06)."""
        spec = _core.build_symbols_request(
            self._state,
            active=active,
            market_id=market_id,
            prefix=prefix,
        )
        resp = await self._request(spec)
        return _core.parse_symbols_response(resp)

    async def get_calendar(self, *, year: int | None = None) -> list[CalendarDay]:
        """Autenticado ``GET {base_url}/calendar`` → lista de días de calendario (D-06)."""
        spec = _core.build_calendar_request(self._state, year=year)
        resp = await self._request(spec)
        return _core.parse_calendar_response(resp)

    async def get_calendar_config(self) -> CalendarConfig:
        """Autenticado ``GET {base_url}/calendar/config`` → objeto config único (D-07)."""
        spec = _core.build_calendar_config_request(self._state)
        resp = await self._request(spec)
        return _core.parse_calendar_config_response(resp)


# ----------------------------------------------------------------------
# Default-async-client lazy singleton + top-level module surface
# ----------------------------------------------------------------------


_default_async_client: AsyncClient | None = None


def _get_default() -> AsyncClient:
    """Acceso lazy al ``AsyncClient`` default a nivel módulo.

    Singleton INDEPENDIENTE del default de la superficie sync (``client.py``):
    no comparten estado por construcción.
    """
    global _default_async_client
    if _default_async_client is None:
        _default_async_client = AsyncClient()
    return _default_async_client


def configure(
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
    audience: str | None = None,
    auth0_token_url: str | None = None,
    base_url: str | None = None,
    token: str | None = None,
    token_expires_at: float | None = None,
    mutating_allowed: bool | None = None,
    expected_host: str | None = None,
) -> None:
    """Sobrescribe credenciales/URLs del default async en runtime.

    Superficie async (estado singleton independiente). Rotar CUALQUIER
    credencial/URL (``base_url``/``client_id``/``client_secret``/``audience``/
    ``auth0_token_url``) resetea el token cacheado (``token=None`` +
    ``token_expires_at=0.0``) para forzar un re-auth, salvo que
    ``token``/``token_expires_at`` se pasen explícitamente (el conftest los
    siembra para tests sin re-auth). Los kwargs ``None`` se ignoran
    (carry-forward). Esta semántica ESPEJA exactamente la superficie sync
    ``client.configure`` (WR-01 — el constraint dual sync/async exige que ambas
    superficies invaliden en ``base_url``). No expone credenciales de usuario,
    rotación de refresh ni override de reintentos (grant machine-to-machine, D-05).
    """
    client = _get_default()
    rotated = False
    if client_id is not None:
        client._state.client_id = client_id
        rotated = True
    if client_secret is not None:
        client._state.client_secret = client_secret
        rotated = True
    if audience is not None:
        client._state.audience = audience
        rotated = True
    if auth0_token_url is not None:
        client._state.auth0_token_url = auth0_token_url
        rotated = True
    if base_url is not None:
        client._state.base_url = base_url.rstrip("/")
        rotated = True
    # Rotar credenciales/URL invalida el token cacheado, salvo que el caller
    # siembre explícitamente token/token_expires_at (test seeding) — espeja sync.
    if rotated and token is None and token_expires_at is None:
        client._state.token = None
        client._state.token_expires_at = 0.0
    # Overrides explícitos de token DESPUÉS del reset para que ganen.
    if token is not None:
        client._state.token = token
    if token_expires_at is not None:
        client._state.token_expires_at = token_expires_at
    # Gate de mutaciones: config puro (D-13/D-15), NO credenciales — NO setea
    # ``rotated`` (no invalida el token). Sentinel None = "no cambiar", así que
    # un ``configure(base_url=...)`` NO resetea un opt-in previo (Pitfall 5).
    if mutating_allowed is not None:
        client._state.mutating_allowed = mutating_allowed
    if expected_host is not None:
        client._state.expected_host = expected_host


async def get_health() -> dict[str, Any]:
    """Shim async top-level: delega al default AsyncClient."""
    return await _get_default().get_health()


async def get_health_feed() -> dict[str, Any]:
    """Shim async top-level: delega al default AsyncClient."""
    return await _get_default().get_health_feed()


async def get_market_data(
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
    """Shim async top-level: delega al default AsyncClient."""
    return await _get_default().get_market_data(
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


async def get_latest(
    *,
    symbol: str,
    market_id: str | None = None,
    entries: str | None = None,
) -> list[MarketDataSnapshot]:
    """Shim async top-level: delega al default AsyncClient."""
    return await _get_default().get_latest(symbol=symbol, market_id=market_id, entries=entries)


async def get_latest_batch(latest_request: LatestRequest) -> list[MarketDataSnapshot]:
    """Shim async top-level: delega al default AsyncClient."""
    return await _get_default().get_latest_batch(latest_request)


async def get_instruments(
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
    """Shim async top-level: delega al default AsyncClient."""
    return await _get_default().get_instruments(
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


async def get_segments() -> list[Segment]:
    """Shim async top-level: delega al default AsyncClient."""
    return await _get_default().get_segments()


async def get_symbols(
    *,
    active: bool | None = None,
    market_id: str | None = None,
    prefix: str | None = None,
) -> list[Symbol]:
    """Shim async top-level: delega al default AsyncClient."""
    return await _get_default().get_symbols(active=active, market_id=market_id, prefix=prefix)


async def get_calendar(*, year: int | None = None) -> list[CalendarDay]:
    """Shim async top-level: delega al default AsyncClient."""
    return await _get_default().get_calendar(year=year)


async def get_calendar_config() -> CalendarConfig:
    """Shim async top-level: delega al default AsyncClient."""
    return await _get_default().get_calendar_config()


async def aclose() -> None:
    """Shim async top-level: cierra el default AsyncClient (idempotente)."""
    await _get_default().aclose()
