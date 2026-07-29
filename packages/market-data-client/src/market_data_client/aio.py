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
from typing import Self

import httpx
from dotenv import load_dotenv

from market_data_client import _atransport, _core
from market_data_client._core import RequestSpec
from market_data_client._state import _REQUEST_TIMEOUT, _ClientState

load_dotenv()

# B8 (D-04): mismo objeto que la superficie sync — el invariante
# ``aio._raise_for_response is client._raise_for_response is
# _core.raise_for_response`` se preserva. Consumido por ``_request`` (Task 2).
_raise_for_response = _core.raise_for_response

# max_attempts fijo del AsyncRetryTransport (no hay ``with_options`` per-call en
# esta superficie — D scope de Plan 05). ``max_attempts=3`` = 1 intento + 2 retries.
_DEFAULT_MAX_ATTEMPTS = 3


class AsyncClient:
    """Cliente async para la API de market data.

    El estado por instancia vive en ``self._state`` (misma forma
    :class:`_ClientState` que el sync ``Client`` pero una INSTANCIA distinta).

    Pickle / deepcopy NO soportado (``httpx.AsyncClient`` posee un pool TCP +
    contexto SSL atados a un event loop específico).
    """

    __slots__ = ("_state",)

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
    ) -> None:
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
        if token is not None:
            self._state.token = token
        if token_expires_at is not None:
            self._state.token_expires_at = token_expires_at
        if http_client is not None:
            self._state.http_client = http_client

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
        """Libera el ``httpx.AsyncClient`` subyacente (idempotente)."""
        http_client = self._state.http_client
        if http_client is not None:
            assert isinstance(http_client, httpx.AsyncClient)
            await http_client.aclose()
            self._state.http_client = None

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
                transport=_atransport.AsyncRetryTransport(max_attempts=_DEFAULT_MAX_ATTEMPTS),
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
