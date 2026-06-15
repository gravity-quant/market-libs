"""Cliente HTTP asincrónico para la API de Higyrus.

Dos formas equivalentes de usar el cliente:

1. **API a nivel módulo (legacy):** ``from higyrus_client import aio`` +
   ``await aio.get_listado_cuentas(estado="alta")``. Delega en una
   instancia perezosa de :class:`AsyncClient`.

2. **Instancia explícita** (Phase 6 REFAC-02)::

        from higyrus_client import AsyncClient

        async with AsyncClient(base_url="...", client_id="...",
                               username="...", password="...") as c:
            cuentas = await c.get_listado_cuentas(estado="alta")

State independiente del módulo sync (``higyrus_client.client``): hacer
login en uno no afecta el otro.

**Phase 7 REFAC-03** — transport shell async mirror del sync. La lógica
pura vive en :mod:`higyrus_client._core`. Endpoint methods = 3-liners.

**B8 — D-04:** ``_raise_for_response`` se importa de
``higyrus_client._core`` directamente. El re-export con
``as _raise_for_response`` satisface mypy strict y preserva la identidad
``aio._raise_for_response is client._raise_for_response`` (ambos aliases
referencian el MISMO objeto en ``_core``).

**PEP 562 compat shim** (D-01, D-02): reads de ``_token``, ``_token_ts``
(renamed a ``token_expires_at``), ``_token_lock`` y ``_client`` forwardean
al state. Reads de ``_user``/``_password``/``_client_id``/``_base_url``
levantan ``AttributeError``.

NO se llama ``load_dotenv()`` acá (D-19) — la carga del ``.env`` la hace
``higyrus_client.client`` cuando se importa.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import uuid
import warnings
from typing import Any, Self

import httpx

from higyrus_client import _atransport, _core
from higyrus_client._core import RequestSpec
from higyrus_client._core import raise_for_response as _raise_for_response  # D-04 B8 alias
from higyrus_client._state import _REQUEST_TIMEOUT, _ClientState
from higyrus_client.client import _validate_max_retries
from higyrus_client.exceptions import HigyrusAuthError
from higyrus_client.models import Cuenta, Movimiento, Posicion, PosicionValuada

# Re-export for tests / external introspection. B8 enforcement test
# asserts aio._raise_for_response is client._raise_for_response.
__all__ = [
    "AsyncClient",
    "_get_default",
    "_raise_for_response",
    "aclose",
    "configure",
    "get_health",
    "get_listado_cuentas",
    "get_movimientos",
    "get_posicion_valuada",
    "get_posiciones",
    "login",
]


# ---------------------------------------------------------------------------
# AsyncClient class — Phase 7 transport shell async
# ---------------------------------------------------------------------------


class AsyncClient:
    """Async HTTP client for Higyrus. Phase 7 transport shell.

    Async-specific bits (``state.client_lock`` para http-client;
    ``state.token_lock`` para token refresh) se crean lazy dentro del loop.
    Pickle/deepcopy NO soportados (D-23).

    Phase 13 WR-01 fix: ``client_lock`` lives on ``_state`` (mirror of
    ``token_lock``) so ``with_options`` views inherit the SAME lock
    instance as the parent — no second lock per view, no race on first
    ``_ensure_http_client`` materialization.
    """

    __slots__ = ("_is_view", "_max_retries", "_state")

    def __init__(
        self,
        *,
        base_url: str | None = None,
        client_id: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        token_expires_at: float | None = None,
        max_retries: int = 2,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        # WR-06: validate max_retries early.
        _validate_max_retries(max_retries)
        self._state = _ClientState()
        if base_url is not None:
            self._state.base_url = base_url.rstrip("/")
        if client_id is not None:
            self._state.client_id = client_id
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
        # Phase 13 D-V1 mirror sync — False for normally-constructed clients;
        # True for views returned by with_options(). Used by aclose()/__aexit__
        # short-circuit guard.
        self._is_view = False
        # Phase 8 D-16: caller-supplied http_client used AS-IS.
        if http_client is not None:
            self._state.http_client = http_client
        # Phase 13 WR-01 fix: ``client_lock`` lives on ``self._state`` (lazy,
        # bound to the current event loop on first use). Hoisted off the
        # instance __slots__ so ``with_options`` views share the SAME lock
        # instance as the parent (mirror of ``token_lock``).

    # ---- Lifecycle ----

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Cierra ``httpx.AsyncClient`` si fue inicializado. Idempotente.

        Phase 13 D-V1 mirror sync: views (constructed via ``with_options``)
        short-circuit here so ``view.aclose()`` / ``view.__aexit__`` never
        tear down the parent's shared TCP pool (anti-Pitfall 13).
        """
        if getattr(self, "_is_view", False): return  # noqa: E701  # fmt: skip
        client_lock = self._ensure_client_lock()
        async with client_lock:
            client = self._state.http_client
            if client is not None:
                assert isinstance(client, httpx.AsyncClient)
                await client.aclose()
                self._state.http_client = None

    def __repr__(self) -> str:
        # D-18: redact password and token; show client_id (not a secret).
        # Phase 13 mirror sync: views surface "view of " prefix for debug ergonomics.
        prefix = "view of " if getattr(self, "_is_view", False) else ""
        return (
            f"{prefix}<higyrus_client.AsyncClient("
            f"base_url={self._state.base_url!r}, "
            f"client_id={self._state.client_id!r}, "
            f"username={self._state.username!r}, "
            f"password={'***' if self._state.password else None!r}, "
            f"token={'***' if self._state.token else None!r})>"
        )

    def __reduce__(self) -> Any:  # D-23
        raise TypeError(
            "higyrus_client.AsyncClient is not picklable; use multiprocessing's "
            "fork start method or recreate in the worker via "
            "higyrus_client.AsyncClient(...)"
        )

    def __deepcopy__(self, memo: Any) -> Any:  # D-23
        raise TypeError(
            "higyrus_client.AsyncClient is not deepcopy-safe (httpx.AsyncClient "
            "owns TCP pool + SSL context)"
        )

    # ---- Locks + HTTP client + auth ----

    def _ensure_client_lock(self) -> asyncio.Lock:
        """Crea el lock de http-client lazy (bind to current loop).

        Phase 13 WR-01 fix: backed by ``self._state.client_lock`` (shared
        across parent and ``with_options`` views) instead of a per-instance
        ``__slots__`` attribute. Mirrors the existing ``token_lock`` pattern.
        """
        if self._state.client_lock is None:
            self._state.client_lock = asyncio.Lock()
        return self._state.client_lock

    def _ensure_token_lock(self) -> asyncio.Lock:
        """Crea el lock de token lazy. Expuesto via PEP 562 como ``aio._token_lock``."""
        if self._state.token_lock is None:
            self._state.token_lock = asyncio.Lock()
        return self._state.token_lock

    def with_options(self, *, max_retries: int) -> Self:
        """Return a new AsyncClient view with overridden ``max_retries``.

        Async mirror of ``Client.with_options`` (D-V3 — same idiomatic shape;
        zero divergence sync↔async). The view shares ``_state`` (token,
        refresh state via ``token_expires_at``, account_id propagation) and
        the shared ``httpx.AsyncClient`` with the parent (anti-Pitfall 13;
        no second TCP pool). Only ``_max_retries`` differs.

        Lifecycle ``aclose()`` / ``__aexit__`` are no-op on views.

        NOTE: ``with_options`` itself is SYNC even on ``AsyncClient`` — it
        constructs the view in-memory only. The subsequent endpoint call is
        the async one::

            view = client.with_options(max_retries=5)
            movs = await view.get_movimientos("CTA-001", d1, d2)

        Phase 13 WR-01 fix: the view shares ``_state.client_lock`` with the
        parent (mirror of the existing ``token_lock`` pattern). Whichever
        of {parent, view} triggers the first ``_ensure_http_client`` lazy-init
        creates the single ``asyncio.Lock`` on ``_state``, and both surfaces
        thereafter acquire the SAME lock — guaranteeing exactly one
        ``httpx.AsyncClient`` is allocated for the shared ``_state.http_client``.
        Cross-loop usage is unsupported (Phase 6 + 7 invariant).

        See ``higyrus_client.Client.with_options`` for full semantics
        (chaining, D-V4 configure-invariance, mutation gate authority,
        auth-flow override per D-T6).
        """
        # WR-06 carry-forward: validate before view construction (D-V3 parity).
        _validate_max_retries(max_retries)
        view = type(self).__new__(type(self))
        view._state = self._state  # SHARE — anti-Pitfall 13 (incl. client_lock)
        view._max_retries = max_retries  # OVERRIDE
        view._is_view = True  # FLAG for aclose()/__aexit__ no-op (D-V1)
        return view

    async def _ensure_http_client(self) -> httpx.AsyncClient:
        """Crea ``httpx.AsyncClient`` lazy (necesita loop) con AsyncRetryTransport.

        Phase 8 D-15 / D-19 / D-32: wraps ``AsyncRetryTransport`` so async
        requests benefit from bounded retries + native ``asyncio.sleep``
        backoff (CancelledError-aware). Preserves the Phase 6/7 double-checked
        locking pattern (``self._state.client_lock`` — Phase 13 WR-01 fix
        hoists from per-instance __slots__ onto shared _state so views and
        parent acquire the SAME lock) — instantiation runs INSIDE the
        lock-protected block so concurrent first-callers race a single
        ``AsyncClient`` allocation.
        """
        client = self._state.http_client
        if isinstance(client, httpx.AsyncClient):
            return client
        client_lock = self._ensure_client_lock()
        async with client_lock:
            client = self._state.http_client
            if isinstance(client, httpx.AsyncClient):
                return client
            new_client = httpx.AsyncClient(
                timeout=_REQUEST_TIMEOUT,
                transport=_atransport.AsyncRetryTransport(max_attempts=self._max_retries + 1),
            )
            self._state.http_client = new_client
            return new_client

    async def _send_auth_request(self, spec: RequestSpec) -> httpx.Response:
        """Send an auth-flow request (login) through the AsyncRetryTransport with extensions.

        Phase 8 D-29 mirror: login goes through the SAME AsyncRetryTransport as
        endpoint requests; ``request.extensions`` carries ``idempotent`` (True
        per D-03) + ``request_id`` + ``endpoint_name`` so the transport's
        structured WARNING/ERROR records carry the canonical D-09 fields. NO
        ``Authorization`` header — auth-flow itself establishes the token.
        """
        http = await self._ensure_http_client()
        request_id = uuid.uuid4().hex
        req = http.build_request(
            spec.method,
            f"{self._state.base_url}{spec.path}",
            json=spec.json_body,
            headers=spec.headers,
        )
        req.extensions["idempotent"] = spec.idempotent
        req.extensions["request_id"] = request_id
        req.extensions["endpoint_name"] = spec.endpoint_name
        # Phase 13 ERG-01 mirror sync (D-T6): auth-flow requests are
        # ``idempotent=True`` (D-03), so the view's per-call cap MUST also
        # apply to login/refresh. Uniform path — parent or view both set this.
        req.extensions["max_attempts"] = self._max_retries + 1
        return await http.send(req)

    async def _login_unlocked(self) -> str:
        """Login sin tomar el lock (asume que el caller lo tiene)."""
        spec = _core.build_login_request(self._state)
        resp = await self._send_auth_request(spec)
        token, expires_at = _core.parse_login_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        return token

    async def login(self) -> str:
        """Autentica contra ``POST /api/login`` y cachea el token."""
        token_lock = self._ensure_token_lock()
        async with token_lock:
            return await self._login_unlocked()

    async def _ensure_token(self) -> None:
        """Refresca el token; double-checked locking para evitar thundering-herd."""
        if _core.token_is_fresh(self._state):
            return
        token_lock = self._ensure_token_lock()
        async with token_lock:
            if _core.token_is_fresh(self._state):
                return
            await self._login_unlocked()

    async def _request(self, spec: RequestSpec) -> httpx.Response:
        """Dispatch an authenticated async request (Bearer) con 401 re-auth-once.

        Phase 8 D-02 + D-30 + D-11 + RELY-04 async mirror: per-business-call UUID4
        ``request_id`` + extensions propagation (incl. account_id when set per
        D-11); on 401 (``HigyrusAuthError`` from ``raise_for_response``), the
        shell clears ``state.token``, calls ``_ensure_token()`` (which re-runs
        the login flow via the ``token_lock`` double-checked locking), then
        retries the request ONCE with the refreshed Authorization header. Second
        401 raises directly (Pitfall 1 — no infinite loop). All non-401 error
        statuses raise their typed exceptions directly without re-auth.

        URL-encoding quirk preservation (Phase 7): when ``spec.url_pre_encoded``
        is True, the ``path`` already includes the pre-encoded query string with
        the Higyrus quirk (``/`` literal preserved). We forward it verbatim to
        ``httpx.AsyncClient.build_request(url=..., params=None)`` so httpx does
        not re-encode.

        WR-03 fix Phase 7 review: si ``_ensure_token()`` retorna sin excepción
        pero ``self._state.token`` queda ``None`` (estado inconsistente —
        servidor responde 200 sin token), reemplazamos el ``assert`` por
        ``HigyrusAuthError`` tipado.
        """
        await self._ensure_token()
        token_lock = self._ensure_token_lock()
        async with token_lock:
            token = self._state.token
        if token is None:
            raise HigyrusAuthError(
                0,
                [{"title": "auth", "detail": "_ensure_token() returned without populating token"}],
            )

        request_id = uuid.uuid4().hex
        http = await self._ensure_http_client()
        url = f"{self._state.base_url}{spec.path}"
        headers = {"Authorization": f"Bearer {token}", **(spec.headers or {})}

        # WR-02 mirror + URL-encoding quirk preservation:
        build_params: dict[str, Any] | None = None if spec.url_pre_encoded else spec.params
        req = (
            http.build_request(
                spec.method, url, params=build_params, json=spec.json_body, headers=headers
            )
            if spec.json_body is not None
            else http.build_request(spec.method, url, params=build_params, headers=headers)
        )

        req.extensions["idempotent"] = spec.idempotent
        req.extensions["request_id"] = request_id
        req.extensions["endpoint_name"] = spec.endpoint_name
        # Phase 13 ERG-01 mirror sync — per-call override; parent or view's
        # _max_retries (Phase 8 D-19 N→N+1). Uniform path.
        req.extensions["max_attempts"] = self._max_retries + 1
        # D-11: only set account_id when non-None (no leak when caller didn't pass id_cuenta).
        if spec.account_id is not None:
            req.extensions["account_id"] = spec.account_id

        resp = await http.send(req)
        try:
            _raise_for_response(resp)
        except HigyrusAuthError:
            # WR-02 hardening (async mirror): explicit body-consume before re-auth.
            await resp.aread()
            # D-02 exactly-one re-auth (async mirror).
            # WR-01 fix: token-clear + re-auth under a SINGLE token_lock
            # acquisition. The OLD code cleared self._state.token OUTSIDE the
            # lock then called self._ensure_token() (which re-acquired the
            # lock). The double-check inside _ensure_token already prevented
            # duplicate logins in practice, but the contract was non-atomic and
            # opened a theoretical race window. The fix wraps clear+ensure
            # under one `async with token_lock:` block with an inner re-check
            # against the captured local `token` so a coroutine that arrived
            # AFTER another coroutine refreshed will skip its own re-auth.
            async with token_lock:
                if self._state.token is None or self._state.token == token:
                    self._state.token = None
                    await self._login_unlocked()
                new_token = self._state.token
            if new_token is None:
                raise HigyrusAuthError(
                    0,
                    [
                        {
                            "title": "auth",
                            "detail": "_ensure_token() returned without populating token",
                        }
                    ],
                ) from None
            req.headers["Authorization"] = f"Bearer {new_token}"
            resp = await http.send(req)
            # WR-02 hardening: body-consume on second response BEFORE second raise.
            await resp.aread()
            _raise_for_response(resp)
        return resp

    # ---- Endpoints (Phase 7 3-liner shells) ----

    async def get_health(self) -> dict[str, Any]:
        """``GET /api/health``."""
        spec = _core.build_get_health_request(self._state)
        return _core.parse_get_health_response(await self._request(spec))

    async def get_movimientos(
        self,
        id_cuenta: str,
        fecha_desde: dt.date,
        fecha_hasta: dt.date,
        *,
        especie: str | None = None,
        tipo_titulo: str | None = None,
        tipo_titulo_agente: str | None = None,
        movimiento: str | None = None,
    ) -> list[Movimiento]:
        """``GET /api/cuentas/{id_cuenta}/movimientos`` (async)."""
        spec = _core.build_get_movimientos_request(
            self._state, id_cuenta, fecha_desde, fecha_hasta,
            especie=especie, tipo_titulo=tipo_titulo,
            tipo_titulo_agente=tipo_titulo_agente, movimiento=movimiento,
        )  # fmt: skip
        return _core.parse_get_movimientos_response(await self._request(spec))

    async def get_posicion_valuada(
        self,
        id_cuenta: str,
        tipo_cuenta: str,
        nivel: str,
        desde: dt.date,
        hasta: dt.date,
        *,
        lugar: str | None = None,
        estado: str | None = None,
        tipo_titulo: str | None = None,
        extracto: str | None = None,
        ocultar_cerradas: bool | None = None,
        especie: str | None = None,
        concertacion: bool | None = None,
        actualizar: bool | None = None,
    ) -> list[PosicionValuada]:
        """``GET /api/cuentas/{id_cuenta}/posicionValuada`` (async)."""
        spec = _core.build_get_posicion_valuada_request(
            self._state, id_cuenta, tipo_cuenta=tipo_cuenta, nivel=nivel,
            desde=desde, hasta=hasta, lugar=lugar, estado=estado,
            tipo_titulo=tipo_titulo, extracto=extracto,
            ocultar_cerradas=ocultar_cerradas, especie=especie,
            concertacion=concertacion, actualizar=actualizar,
        )  # fmt: skip
        return _core.parse_get_posicion_valuada_response(await self._request(spec))

    async def get_listado_cuentas(
        self,
        *,
        id_cuenta: list[str] | None = None,
        tipo_cuenta: str | None = None,
        estado: str | None = None,
        fecha_desde: dt.date | None = None,
        fecha_hasta: dt.date | None = None,
    ) -> list[Cuenta]:
        """``GET /api/cuentas/listadoCuentas`` (async)."""
        spec = _core.build_get_listado_cuentas_request(
            self._state, id_cuenta=id_cuenta, tipo_cuenta=tipo_cuenta,
            estado=estado, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        )  # fmt: skip
        return _core.parse_get_listado_cuentas_response(await self._request(spec))

    async def get_posiciones(
        self,
        id_cuenta: str,
        fecha: dt.date,
        *,
        especie: str | None = None,
        incluir_parking: bool = False,
    ) -> list[Posicion]:
        """``GET /api/cuentas/{id_cuenta}/posiciones`` (async)."""
        spec = _core.build_get_posiciones_request(
            self._state, id_cuenta, fecha=fecha, especie=especie,
            incluir_parking=incluir_parking,
        )  # fmt: skip
        return _core.parse_get_posiciones_response(await self._request(spec))


# ---------------------------------------------------------------------------
# Default async client + module-level API (legacy)
# ---------------------------------------------------------------------------

_default_async_client: AsyncClient | None = None


def _get_default() -> AsyncClient:
    """Devuelve el ``AsyncClient`` perezoso a nivel módulo."""
    global _default_async_client
    if _default_async_client is None:
        _default_async_client = AsyncClient()
    return _default_async_client


def configure(
    *,
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    client_id: str | None = None,
    token: str | None = None,
    token_expires_at: float | None = None,
    max_retries: int | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> None:
    """Sobrescribe credenciales/URL del default async client (carry-forward semantic).

    Phase 8 D-15 / D-16 / D-19: ``max_retries`` (default 2; ``0`` disables
    retries) and ``http_client`` (AsyncClient used AS-IS per D-16) are
    carry-forward kwargs. NOTE: configure() is synchronous, so the prior client
    is dropped without ``aclose()`` — callers should call ``await aclose()``
    BEFORE reconfiguring the http client to avoid leaking the prior connection
    pool.
    """
    # WR-06: validate max_retries (only when explicitly passed).
    if max_retries is not None:
        _validate_max_retries(max_retries)
    global _default_async_client
    current = _get_default()
    next_max_retries = max_retries if max_retries is not None else current._max_retries
    # WR-07: warn before dropping a live httpx.AsyncClient — its connection
    # pool + SSL context leak until garbage collection. The recommended
    # consumer pattern is `await aio.aclose()` BEFORE configure(...).
    if current._state.http_client is not None:
        warnings.warn(
            "higyrus_client.aio.configure(): replacing a live httpx.AsyncClient "
            "without awaiting aclose() leaks the connection pool. Call "
            "`await higyrus_client.aio.aclose()` before configure(...) to avoid "
            "the leak.",
            ResourceWarning,
            stacklevel=2,
        )
    new = AsyncClient(
        base_url=base_url if base_url is not None else current._state.base_url,
        client_id=client_id if client_id is not None else current._state.client_id,
        username=username if username is not None else current._state.username,
        password=password if password is not None else current._state.password,
        token=token,
        token_expires_at=token_expires_at,
        max_retries=next_max_retries,
        http_client=http_client,
    )
    # NOTE: no podemos await current.aclose() acá (configure es sync).
    _default_async_client = new


async def aclose() -> None:
    await _get_default().aclose()


async def login() -> str:
    return await _get_default().login()


async def get_health() -> dict[str, Any]:
    return await _get_default().get_health()


async def get_movimientos(
    id_cuenta: str,
    fecha_desde: dt.date,
    fecha_hasta: dt.date,
    *,
    especie: str | None = None,
    tipo_titulo: str | None = None,
    tipo_titulo_agente: str | None = None,
    movimiento: str | None = None,
) -> list[Movimiento]:
    return await _get_default().get_movimientos(
        id_cuenta, fecha_desde, fecha_hasta,
        especie=especie, tipo_titulo=tipo_titulo,
        tipo_titulo_agente=tipo_titulo_agente, movimiento=movimiento,
    )  # fmt: skip


async def get_posicion_valuada(
    id_cuenta: str,
    tipo_cuenta: str,
    nivel: str,
    desde: dt.date,
    hasta: dt.date,
    *,
    lugar: str | None = None,
    estado: str | None = None,
    tipo_titulo: str | None = None,
    extracto: str | None = None,
    ocultar_cerradas: bool | None = None,
    especie: str | None = None,
    concertacion: bool | None = None,
    actualizar: bool | None = None,
) -> list[PosicionValuada]:
    return await _get_default().get_posicion_valuada(
        id_cuenta, tipo_cuenta, nivel, desde, hasta,
        lugar=lugar, estado=estado, tipo_titulo=tipo_titulo,
        extracto=extracto, ocultar_cerradas=ocultar_cerradas,
        especie=especie, concertacion=concertacion, actualizar=actualizar,
    )  # fmt: skip


async def get_listado_cuentas(
    *,
    id_cuenta: list[str] | None = None,
    tipo_cuenta: str | None = None,
    estado: str | None = None,
    fecha_desde: dt.date | None = None,
    fecha_hasta: dt.date | None = None,
) -> list[Cuenta]:
    return await _get_default().get_listado_cuentas(
        id_cuenta=id_cuenta, tipo_cuenta=tipo_cuenta, estado=estado,
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
    )  # fmt: skip


async def get_posiciones(
    id_cuenta: str,
    fecha: dt.date,
    *,
    especie: str | None = None,
    incluir_parking: bool = False,
) -> list[Posicion]:
    return await _get_default().get_posiciones(
        id_cuenta, fecha, especie=especie, incluir_parking=incluir_parking,
    )  # fmt: skip


# ---------------------------------------------------------------------------
# Legacy module-level `_request` shim + PEP 562 read-only shim
# ---------------------------------------------------------------------------


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """Module-level shim async — preserva signature pre-Phase-7."""
    spec = RequestSpec(method=method, path=path, params=params, json_body=json_body)
    resp = await _get_default()._request(spec)
    if not resp.is_success:
        _raise_for_response(resp)
    if resp.status_code == 204 or not resp.content:
        return None
    body: dict[str, Any] | list[Any] = resp.json()
    return body


# Maps legacy module-level name -> _ClientState attribute name. ``_token_ts``
# encodes the cross-pkg rename to ``token_expires_at``; ``_token_lock``
# exposes the lazy state.token_lock.
_FORWARDED_TO_STATE: dict[str, str] = {
    "_token": "token",
    "_token_ts": "token_expires_at",
    "_token_lock": "token_lock",
}

_FORWARDED_HTTP_CLIENT = "_client"


def __getattr__(name: str) -> Any:
    """PEP 562 read-only shim (D-01)."""
    if name in _FORWARDED_TO_STATE:
        return getattr(_get_default()._state, _FORWARDED_TO_STATE[name])
    if name == _FORWARDED_HTTP_CLIENT:
        return _get_default()._state.http_client
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
