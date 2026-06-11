"""Cliente HTTP asincrónico para la API de Higyrus.

Hay dos formas equivalentes de usar el cliente:

1. **API a nivel módulo (legacy):** las funciones se llaman directamente
   sobre el submódulo. Internamente delegan en una instancia perezosa
   de :class:`AsyncClient` creada en el primer uso::

        from higyrus_client import aio

        cuentas = await aio.get_listado_cuentas(estado="alta")
        await aio.aclose()

2. **Instancia explícita** (Phase 6 REFAC-02, recomendado para tests y
   aplicaciones que necesitan aislamiento de state)::

        from higyrus_client import AsyncClient

        async with AsyncClient(base_url="...", client_id="...",
                               username="...", password="...") as c:
            cuentas = await c.get_listado_cuentas(estado="alta")

El login se dispara automáticamente en la primera llamada que lo necesite;
``aio.login()`` está expuesto por si querés validar credenciales temprano,
pero no es obligatorio. State independiente del módulo sync
(``higyrus_client.client``): hacer login en uno no afecta el otro.

**B8 — Helper compartido:** ``_raise_for_response`` se importa de
``higyrus_client.client`` (no se duplica). Single source of truth para el
mapping de errores Higyrus.

**PEP 562 compat shim** (D-01, D-02): este módulo expone reads de los
nombres legacy ``_token``, ``_token_ts`` (renamed internamente a
``token_expires_at``), ``_token_lock``, y ``_client`` como aliases
read-only del state del default async client. Reads de ``_user``,
``_password``, ``_client_id``, ``_base_url`` levantan ``AttributeError``.

Notar: NO se llama ``load_dotenv()`` en este módulo (D-19) — la carga del
``.env`` la hace ``higyrus_client.client`` cuando se importa. Importar
``aio`` directamente sin importar ``higyrus_client`` antes funciona
porque los defaults del state leen env vars que ``higyrus_client.client``
ya cargó (todo el paquete pasa por el import side-effect).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import time
from typing import Any, Self
from urllib.parse import quote, urlencode

import httpx

from higyrus_client._params import drop_none, format_bool, format_date
from higyrus_client._state import _REQUEST_TIMEOUT, _TOKEN_TTL_SECONDS, _ClientState
from higyrus_client.client import _raise_for_response  # B8: shared helper
from higyrus_client.exceptions import HigyrusAPIError, HigyrusAuthError
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
# AsyncClient class
# ---------------------------------------------------------------------------


class AsyncClient:
    """Async HTTP client for Higyrus.

    State lives in ``self._state`` (``_ClientState``). The async-specific
    bits (``_client_lock`` for http-client creation; ``state.token_lock``
    for token refresh) are created lazy inside the loop so the class is
    safe to instantiate at import time / outside an event loop.

    Pickle / deepcopy contract (D-23): NOT supported.
    """

    __slots__ = ("_client_lock", "_state")

    def __init__(
        self,
        *,
        base_url: str | None = None,
        client_id: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        token_expires_at: float | None = None,
    ) -> None:
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
        # Lazy: bound to the current event loop on first use.
        self._client_lock: asyncio.Lock | None = None

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
        """Cierra el ``httpx.AsyncClient`` si fue inicializado. Idempotente."""
        client_lock = self._ensure_client_lock()
        async with client_lock:
            client = self._state.http_client
            if client is not None:
                assert isinstance(client, httpx.AsyncClient)
                await client.aclose()
                self._state.http_client = None

    def __repr__(self) -> str:
        # D-18: redact password and token; show client_id (not a secret).
        return (
            "<higyrus_client.AsyncClient("
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

    # ---- Lock lifecycle ----

    def _ensure_client_lock(self) -> asyncio.Lock:
        """Crea el lock de http-client lazy (bind to current loop)."""
        if self._client_lock is None:
            self._client_lock = asyncio.Lock()
        return self._client_lock

    def _ensure_token_lock(self) -> asyncio.Lock:
        """Crea el lock de token lazy (bind to current loop). Expuesto vía
        shim PEP 562 como ``aio._token_lock`` para callers legacy."""
        if self._state.token_lock is None:
            self._state.token_lock = asyncio.Lock()
        return self._state.token_lock

    # ---- HTTP client lifecycle ----

    async def _ensure_http_client(self) -> httpx.AsyncClient:
        """Crea ``httpx.AsyncClient`` lazy en el primer uso (necesita loop)."""
        client = self._state.http_client
        if isinstance(client, httpx.AsyncClient):
            return client
        client_lock = self._ensure_client_lock()
        async with client_lock:
            client = self._state.http_client
            if isinstance(client, httpx.AsyncClient):
                return client
            new_client = httpx.AsyncClient(timeout=_REQUEST_TIMEOUT)
            self._state.http_client = new_client
            return new_client

    # ---- Auth ----

    async def _login_unlocked(self) -> str:
        """Login sin tomar el lock (asume que el caller ya lo tiene)."""
        if not self._state.base_url:
            raise HigyrusAuthError(
                0, [{"title": "config", "detail": "HIGYRUS_BASE_URL must be set"}]
            )
        if not self._state.username or not self._state.password:
            raise HigyrusAuthError(
                0,
                [{"title": "config", "detail": "HIGYRUS_USER and HIGYRUS_PASSWORD must be set"}],
            )

        http_client = await self._ensure_http_client()
        resp = await http_client.post(
            f"{self._state.base_url}/api/login",
            json={
                "clientId": self._state.client_id,
                "username": self._state.username,
                "password": self._state.password,
            },
        )
        # WR-01 mirror (review-04): canalizar todos los non-2xx por
        # _raise_for_response para preservar la jerarquía HigyrusClientError.
        if not resp.is_success:
            _raise_for_response(resp)

        data: dict[str, Any] = resp.json()
        token = data.get("token")
        if not isinstance(token, str) or not token:
            raise HigyrusAuthError(
                resp.status_code,
                [{"title": "auth", "detail": "No token in login response"}],
            )

        self._state.token = token
        # Phase 6 REFAC-02 rename: epoch absoluto de expiración.
        self._state.token_expires_at = time.time() + _TOKEN_TTL_SECONDS
        return token

    async def login(self) -> str:
        """Autentica contra ``POST /api/login`` y cachea el token."""
        token_lock = self._ensure_token_lock()
        async with token_lock:
            return await self._login_unlocked()

    async def _ensure_token(self) -> None:
        """Refresca el token si no existe o si superó ``_TOKEN_TTL_SECONDS``.

        Usa double-checked locking para evitar el thundering-herd cuando
        múltiples coroutines llegan a un endpoint con token vencido al mismo
        tiempo.
        """
        if self._state.token and time.time() < self._state.token_expires_at:
            return
        token_lock = self._ensure_token_lock()
        async with token_lock:
            # Double-check tras esperar el lock — otro coroutine pudo refrescar.
            if self._state.token and time.time() < self._state.token_expires_at:
                return
            await self._login_unlocked()

    # ---- Internals ----

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        """Ejecuta una request autenticada y decodifica el JSON.

        Devuelve ``None`` si la API responde 204 o cuerpo vacío. Preserva
        la quirk higyrus de NO encodear ``/`` en query strings.
        """
        await self._ensure_token()
        token_lock = self._ensure_token_lock()
        async with token_lock:
            token = self._state.token
        assert token is not None

        http_client = await self._ensure_http_client()
        clean_params = drop_none(params) if params else None
        url = f"{self._state.base_url}{path}"
        if clean_params:
            # B6 - same logic as sync: preservar `/` literal en query y
            # re-emitir `list[str]` como claves repetidas.
            query = urlencode(clean_params, doseq=True, quote_via=quote, safe="/")
            url = f"{url}?{query}"
        # WR-02 mirror (review-04): omitir `json` cuando no hay body.
        kwargs: dict[str, Any] = {"headers": {"Authorization": f"Bearer {token}"}}
        if json_body is not None:
            kwargs["json"] = json_body
        resp = await http_client.request(method, url, **kwargs)

        if not resp.is_success:
            _raise_for_response(resp)

        if resp.status_code == 204 or not resp.content:
            return None

        body: dict[str, Any] | list[Any] = resp.json()
        return body

    async def _get(self, path: str, **params: Any) -> dict[str, Any] | list[Any] | None:
        return await self._request("GET", path, params=params)

    # ---- Health ----

    async def get_health(self) -> dict[str, Any]:
        """Estado del servidor vía ``GET /api/health``."""
        raw = await self._request("GET", "/api/health")
        if not isinstance(raw, dict):
            raise HigyrusAPIError(
                status_code=0,
                errors=[
                    {
                        "title": "shape mismatch",
                        "detail": f"expected dict, got {type(raw).__name__}",
                    }
                ],
            )
        return raw

    # ---- Cuentas ----

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
        """Movimientos de una cuenta en un rango de fechas (async)."""
        raw = await self._get(
            f"/api/cuentas/{id_cuenta}/movimientos",
            fechaDesde=format_date(fecha_desde),
            fechaHasta=format_date(fecha_hasta),
            especie=especie,
            tipoTitulo=tipo_titulo,
            tipoTituloAgente=tipo_titulo_agente,
            movimiento=movimiento,
        )
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise HigyrusAPIError(
                status_code=0,
                errors=[
                    {
                        "title": "shape mismatch",
                        "detail": f"expected list, got {type(raw).__name__}",
                    }
                ],
            )
        return [Movimiento.from_api(item) for item in raw]

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
        """Posición valuada de una cuenta en un rango de fechas (async)."""
        raw = await self._get(
            f"/api/cuentas/{id_cuenta}/posicionValuada",
            tipoCuenta=tipo_cuenta,
            nivel=nivel,
            desde=format_date(desde),
            hasta=format_date(hasta),
            lugar=lugar,
            estado=estado,
            tipoTitulo=tipo_titulo,
            extracto=extracto,
            ocultarCerradas=format_bool(ocultar_cerradas),
            especie=especie,
            concertacion=format_bool(concertacion),
            actualizar=format_bool(actualizar),
        )
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise HigyrusAPIError(
                status_code=0,
                errors=[
                    {
                        "title": "shape mismatch",
                        "detail": f"expected list, got {type(raw).__name__}",
                    }
                ],
            )
        return [PosicionValuada.from_api(item) for item in raw]

    async def get_listado_cuentas(
        self,
        *,
        id_cuenta: list[str] | None = None,
        tipo_cuenta: str | None = None,
        estado: str | None = None,
        fecha_desde: dt.date | None = None,
        fecha_hasta: dt.date | None = None,
    ) -> list[Cuenta]:
        """Listado completo de cuentas, filtrable (async)."""
        raw = await self._get(
            "/api/cuentas/listadoCuentas",
            idCuenta=id_cuenta,
            tipoCuenta=tipo_cuenta,
            estado=estado,
            fechaDesde=format_date(fecha_desde),
            fechaHasta=format_date(fecha_hasta),
        )
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise HigyrusAPIError(
                status_code=0,
                errors=[
                    {
                        "title": "shape mismatch",
                        "detail": f"expected list, got {type(raw).__name__}",
                    }
                ],
            )
        return [Cuenta.from_api(item) for item in raw]

    async def get_posiciones(
        self,
        id_cuenta: str,
        fecha: dt.date,
        *,
        especie: str | None = None,
        incluir_parking: bool = False,
    ) -> list[Posicion]:
        """Resumen de posiciones de una cuenta a una fecha (async)."""
        raw = await self._get(
            f"/api/cuentas/{id_cuenta}/posiciones",
            fecha=format_date(fecha),
            especie=especie,
            incluirParking=format_bool(incluir_parking),
        )
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise HigyrusAPIError(
                status_code=0,
                errors=[
                    {
                        "title": "shape mismatch",
                        "detail": f"expected list, got {type(raw).__name__}",
                    }
                ],
            )
        return [Posicion.from_api(item) for item in raw]


# ---------------------------------------------------------------------------
# Default async client + module-level API (legacy)
# ---------------------------------------------------------------------------

_default_async_client: AsyncClient | None = None


def _get_default() -> AsyncClient:
    """Devuelve el ``AsyncClient`` perezoso a nivel módulo.

    Se crea en el primer uso leyendo env vars vía los defaults de
    ``_ClientState``. ``configure()`` lo reemplaza por una nueva instancia.
    """
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
) -> None:
    """Sobrescribe credenciales/URL del default async client en runtime.

    Mismo carry-forward semantic que el sync ``configure()``: el default
    se reemplaza por una nueva instancia copiando los valores actuales
    para los kwargs no pasados. ``token=`` y ``token_expires_at=`` se
    aceptan como kwargs para que los conftest migren de
    ``monkeypatch.setattr(aio, "_token", ...)`` a
    ``aio.configure(token=...)``.
    """
    global _default_async_client
    current = _get_default()
    new = AsyncClient(
        base_url=base_url if base_url is not None else current._state.base_url,
        client_id=client_id if client_id is not None else current._state.client_id,
        username=username if username is not None else current._state.username,
        password=password if password is not None else current._state.password,
        token=token,
        token_expires_at=token_expires_at,
    )
    # NOTE: no podemos await current.aclose() acá (configure es sync). El
    # default antiguo queda sin un http_client cerrado hasta el próximo
    # `await aio.aclose()`. Llamar a aclose explícitamente desde el
    # teardown del fixture sigue siendo necesario.
    _default_async_client = new


async def aclose() -> None:
    """Cierra ``httpx.AsyncClient`` del default si fue inicializado."""
    await _get_default().aclose()


async def login() -> str:
    """Login a nivel módulo (D-20): delega en el ``AsyncClient`` perezoso."""
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
        id_cuenta,
        fecha_desde,
        fecha_hasta,
        especie=especie,
        tipo_titulo=tipo_titulo,
        tipo_titulo_agente=tipo_titulo_agente,
        movimiento=movimiento,
    )


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
        id_cuenta,
        tipo_cuenta,
        nivel,
        desde,
        hasta,
        lugar=lugar,
        estado=estado,
        tipo_titulo=tipo_titulo,
        extracto=extracto,
        ocultar_cerradas=ocultar_cerradas,
        especie=especie,
        concertacion=concertacion,
        actualizar=actualizar,
    )


async def get_listado_cuentas(
    *,
    id_cuenta: list[str] | None = None,
    tipo_cuenta: str | None = None,
    estado: str | None = None,
    fecha_desde: dt.date | None = None,
    fecha_hasta: dt.date | None = None,
) -> list[Cuenta]:
    return await _get_default().get_listado_cuentas(
        id_cuenta=id_cuenta,
        tipo_cuenta=tipo_cuenta,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


async def get_posiciones(
    id_cuenta: str,
    fecha: dt.date,
    *,
    especie: str | None = None,
    incluir_parking: bool = False,
) -> list[Posicion]:
    return await _get_default().get_posiciones(
        id_cuenta,
        fecha,
        especie=especie,
        incluir_parking=incluir_parking,
    )


# ---------------------------------------------------------------------------
# Internal accessors for the module-level _request shim
# ---------------------------------------------------------------------------


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """Module-level shim — delega en el default async client.

    Mantenido para preservar compatibilidad con tests legacy que invocan
    ``aio._request(...)`` directamente.
    """
    return await _get_default()._request(method, path, params=params, json_body=json_body)


# ---------------------------------------------------------------------------
# PEP 562 read-only shim — D-01, D-02
# ---------------------------------------------------------------------------

# Maps legacy module-level name -> _ClientState attribute name. The
# ``_token_ts`` entry encodes the cross-pkg rename to ``token_expires_at``;
# ``_token_lock`` exposes the lazy state.token_lock created on first use.
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
