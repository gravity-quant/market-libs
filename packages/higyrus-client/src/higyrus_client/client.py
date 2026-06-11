"""Cliente HTTP sincrónico para la API de Higyrus.

Hay dos formas equivalentes de usar el cliente:

1. **API a nivel módulo (legacy):** las funciones se llaman directamente
   sobre el paquete. Internamente delegan en una instancia perezosa de
   :class:`Client` creada en el primer uso::

        import higyrus_client

        cuentas = higyrus_client.get_listado_cuentas(estado="alta")

2. **Instancia explícita** (Phase 6 REFAC-02, recomendado para tests y
   aplicaciones que necesitan aislamiento de state)::

        from higyrus_client import Client

        with Client(base_url="...", client_id="...", username="...",
                    password="...") as c:
            cuentas = c.get_listado_cuentas(estado="alta")

El token se obtiene con ``POST /api/login`` (Bearer válido por 24 h) en la
primera llamada que lo necesite y se refresca automáticamente antes del
vencimiento. ``login()`` está expuesto por si querés validar credenciales
temprano, pero no es obligatorio invocarlo.

Configuración por variables de entorno (cargadas con ``python-dotenv``):

- ``HIGYRUS_BASE_URL`` (requerido) — URL hasta el prefijo ``/api``.
- ``HIGYRUS_USER`` (requerido)
- ``HIGYRUS_PASSWORD`` (requerido)
- ``HIGYRUS_CLIENT_ID`` (opcional, default ``""``).

Para reconfigurar el default-client en runtime sin reiniciar el proceso,
asignar a :func:`configure` (acepta los mismos kwargs).

**PEP 562 compat shim** (D-01, D-02): este módulo expone reads de los
nombres legacy ``_token``, ``_token_ts`` (renamed internamente a
``token_expires_at``) y ``_client`` como aliases read-only del state del
default-client. Reads de ``_user``, ``_password``, ``_client_id``,
``_base_url`` levantan ``AttributeError`` para forzar el uso de
``configure()``. Escrituras a través del módulo NO están soportadas —
hacelas via ``configure()`` o ``Client(...)`` explícito.

**B8 — Helper compartido con ``aio.py``:** ``_raise_for_response(resp)`` es
stateless y se importa desde ``higyrus_client.aio`` directamente; no se
duplica.
"""

from __future__ import annotations

import datetime as dt
import time
from typing import Any, Self
from urllib.parse import quote, urlencode

import httpx
from dotenv import load_dotenv

from higyrus_client._params import drop_none, format_bool, format_date
from higyrus_client._state import _REQUEST_TIMEOUT, _TOKEN_TTL_SECONDS, _ClientState
from higyrus_client.exceptions import (
    HigyrusAPIError,
    HigyrusAuthError,
    HigyrusAuthorizationError,
    HigyrusRateLimitError,
)
from higyrus_client.models import Cuenta, Movimiento, Posicion, PosicionValuada

load_dotenv()


# ---------------------------------------------------------------------------
# Module-level helper (shared with aio.py per B8 — DO NOT duplicate)
# ---------------------------------------------------------------------------


def _raise_for_response(resp: httpx.Response) -> None:
    """Mapea respuestas non-2xx a la jerarquía ``HigyrusClientError``.

    Stateless; ``higyrus_client.aio`` la importa directamente y la usa en
    su ``_request`` y ``_login_unlocked`` (B8: single source of truth para
    la lógica de mapeo de errores).
    """
    try:
        payload: dict[str, Any] = resp.json()
    except ValueError:
        payload = {}

    errors = payload.get("errors") if isinstance(payload, dict) else None
    timestamp = payload.get("timestamp") if isinstance(payload, dict) else None

    exc_cls: type[HigyrusAPIError]
    if resp.status_code == 401:
        exc_cls = HigyrusAuthError
    elif resp.status_code == 403:
        exc_cls = HigyrusAuthorizationError
    elif resp.status_code == 429:
        exc_cls = HigyrusRateLimitError
    else:
        exc_cls = HigyrusAPIError

    raise exc_cls(resp.status_code, errors, timestamp)


# ---------------------------------------------------------------------------
# Client class
# ---------------------------------------------------------------------------


class Client:
    """Sync HTTP client for Higyrus.

    State lives in ``self._state`` (``_ClientState`` dataclass). Construct
    explicitly with kwargs or rely on the lazy default-client + module-level
    shims for the historical API.

    Pickle / deepcopy contract (D-23): NOT supported. ``httpx.Client``
    owns a TCP pool and SSL context that can't safely round-trip. Use
    ``multiprocessing``'s ``fork`` start method, or reconstruct in the
    worker via ``higyrus_client.Client(...)`` / ``configure()``.
    """

    __slots__ = ("_state",)

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

    # ---- Lifecycle ----

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Cierra el ``httpx.Client`` subyacente si fue inicializado. Idempotente."""
        client = self._state.http_client
        if client is not None:
            assert isinstance(client, httpx.Client)
            client.close()
            self._state.http_client = None

    def __repr__(self) -> str:
        # D-18: redact password and token; show client_id (not a secret).
        return (
            "<higyrus_client.Client("
            f"base_url={self._state.base_url!r}, "
            f"client_id={self._state.client_id!r}, "
            f"username={self._state.username!r}, "
            f"password={'***' if self._state.password else None!r}, "
            f"token={'***' if self._state.token else None!r})>"
        )

    def __reduce__(self) -> Any:  # D-23
        raise TypeError(
            "higyrus_client.Client is not picklable; use multiprocessing's "
            "fork start method or recreate in the worker via "
            "higyrus_client.Client(...)"
        )

    def __deepcopy__(self, memo: Any) -> Any:  # D-23
        raise TypeError(
            "higyrus_client.Client is not deepcopy-safe (httpx.Client owns TCP pool + SSL context)"
        )

    # ---- HTTP client lifecycle ----

    def _ensure_http_client(self) -> httpx.Client:
        """Crea ``httpx.Client`` lazy en el primer uso."""
        client = self._state.http_client
        if isinstance(client, httpx.Client):
            return client
        new_client = httpx.Client(timeout=_REQUEST_TIMEOUT)
        self._state.http_client = new_client
        return new_client

    # ---- Auth ----

    def login(self) -> str:
        """Autentica contra ``POST /api/login`` y cachea el token.

        Devuelve el token recién emitido. La mayoría de los callers no
        necesitan invocarla: el primer request a cualquier endpoint
        dispara el login automáticamente y los subsiguientes lo refrescan
        antes del vencimiento (TTL = 23h).
        """
        if not self._state.base_url:
            raise HigyrusAuthError(
                0, [{"title": "config", "detail": "HIGYRUS_BASE_URL must be set"}]
            )
        if not self._state.username or not self._state.password:
            raise HigyrusAuthError(
                0,
                [{"title": "config", "detail": "HIGYRUS_USER and HIGYRUS_PASSWORD must be set"}],
            )

        http_client = self._ensure_http_client()
        resp = http_client.post(
            f"{self._state.base_url}/api/login",
            json={
                "clientId": self._state.client_id,
                "username": self._state.username,
                "password": self._state.password,
            },
        )
        # WR-01 (review-04): cualquier non-2xx debe pasar por
        # _raise_for_response para mapear a HigyrusClientError.
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
        # Phase 6 REFAC-02 rename: el campo guarda epoch absoluto de
        # expiración (no timestamp-since-login como el legacy ``_token_ts``).
        self._state.token_expires_at = time.time() + _TOKEN_TTL_SECONDS
        return token

    def _ensure_token(self) -> None:
        """Refresca el token si no existe o si superó ``_TOKEN_TTL_SECONDS``."""
        if self._state.token and time.time() < self._state.token_expires_at:
            return
        self.login()

    # ---- Internals ----

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        """Ejecuta una request autenticada y decodifica el JSON.

        Devuelve ``None`` si la API responde 204 o cuerpo vacío. Preserva
        la quirk higyrus de NO encodear ``/`` en query strings (Higyrus IIS
        rechaza ``%2F`` con 400 "formato dd/mm/yyyy", F-01..F-06 plan
        04-04).
        """
        self._ensure_token()
        token = self._state.token
        assert token is not None

        http_client = self._ensure_http_client()
        clean_params = drop_none(params) if params else None
        url = f"{self._state.base_url}{path}"
        if clean_params:
            # Preservar `/` literal en query (Higyrus IIS rechaza `%2F`).
            # `doseq=True` re-emite `list[str]` como claves repetidas:
            # idCuenta=A&idCuenta=B (CR-01 review-04).
            query = urlencode(clean_params, doseq=True, quote_via=quote, safe="/")
            url = f"{url}?{query}"
        # WR-02 (review-04): omitir `json` cuando no hay body para no
        # inyectar `null` con Content-Type application/json en GETs.
        kwargs: dict[str, Any] = {"headers": {"Authorization": f"Bearer {token}"}}
        if json_body is not None:
            kwargs["json"] = json_body
        resp = http_client.request(method, url, **kwargs)

        if not resp.is_success:
            _raise_for_response(resp)

        if resp.status_code == 204 or not resp.content:
            return None

        body: dict[str, Any] | list[Any] = resp.json()
        return body

    def _get(self, path: str, **params: Any) -> dict[str, Any] | list[Any] | None:
        return self._request("GET", path, params=params)

    # ---- Health ----

    def get_health(self) -> dict[str, Any]:
        """Estado del servidor vía ``GET /api/health`` (requiere Bearer)."""
        raw = self._request("GET", "/api/health")
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

    def get_movimientos(
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
        """Movimientos de una cuenta en un rango de fechas.

        Endpoint: ``GET /api/cuentas/{id_cuenta}/movimientos``.
        """
        raw = self._get(
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

    def get_posicion_valuada(
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
        """Posición valuada de una cuenta en un rango de fechas.

        Endpoint: ``GET /api/cuentas/{id_cuenta}/posicionValuada``.
        """
        raw = self._get(
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

    def get_listado_cuentas(
        self,
        *,
        id_cuenta: list[str] | None = None,
        tipo_cuenta: str | None = None,
        estado: str | None = None,
        fecha_desde: dt.date | None = None,
        fecha_hasta: dt.date | None = None,
    ) -> list[Cuenta]:
        """Listado completo de cuentas, filtrable.

        Endpoint: ``GET /api/cuentas/listadoCuentas``.
        """
        raw = self._get(
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

    def get_posiciones(
        self,
        id_cuenta: str,
        fecha: dt.date,
        *,
        especie: str | None = None,
        incluir_parking: bool = False,
    ) -> list[Posicion]:
        """Resumen de posiciones de una cuenta a una fecha.

        Endpoint: ``GET /api/cuentas/{id_cuenta}/posiciones``.
        """
        raw = self._get(
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
# Default-client + module-level API (legacy)
# ---------------------------------------------------------------------------

_default_client: Client | None = None


def _get_default() -> Client:
    """Devuelve el ``Client`` perezoso a nivel módulo.

    Se crea en el primer uso leyendo env vars vía los defaults de
    ``_ClientState``. ``configure()`` lo reemplaza por una nueva instancia
    para que el reseteo del state sea atómico.
    """
    global _default_client
    if _default_client is None:
        _default_client = Client()
    return _default_client


def configure(
    *,
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    client_id: str | None = None,
    token: str | None = None,
    token_expires_at: float | None = None,
) -> None:
    """Sobrescribe credenciales/URL del default-client en runtime.

    Útil en tests, notebooks, o cuando hay rotación dinámica.

    Semántica de carry-forward (Phase 6 REFAC-02 prerequisite):
    el default-client se reemplaza por una NUEVA instancia, copiando los
    valores actuales para los kwargs no pasados (``None``). Los kwargs
    ``token=`` y ``token_expires_at=`` permiten precargar el token sin
    monkeypatch — los conftests de tests los usan en lugar de
    ``monkeypatch.setattr(pkg.client, "_token", ...)``.
    """
    global _default_client
    current = _get_default()
    new = Client(
        base_url=base_url if base_url is not None else current._state.base_url,
        client_id=client_id if client_id is not None else current._state.client_id,
        username=username if username is not None else current._state.username,
        password=password if password is not None else current._state.password,
        token=token,
        token_expires_at=token_expires_at,
    )
    # Cerrar el http_client antiguo si quedó abierto, para no leakearlo.
    current.close()
    _default_client = new


def login() -> str:
    """Login a nivel módulo (D-20): delega en el ``Client`` perezoso."""
    return _get_default().login()


def get_health() -> dict[str, Any]:
    """``GET /api/health`` via default-client."""
    return _get_default().get_health()


def get_movimientos(
    id_cuenta: str,
    fecha_desde: dt.date,
    fecha_hasta: dt.date,
    *,
    especie: str | None = None,
    tipo_titulo: str | None = None,
    tipo_titulo_agente: str | None = None,
    movimiento: str | None = None,
) -> list[Movimiento]:
    """``GET /api/cuentas/{id_cuenta}/movimientos`` via default-client."""
    return _get_default().get_movimientos(
        id_cuenta,
        fecha_desde,
        fecha_hasta,
        especie=especie,
        tipo_titulo=tipo_titulo,
        tipo_titulo_agente=tipo_titulo_agente,
        movimiento=movimiento,
    )


def get_posicion_valuada(
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
    """``GET /api/cuentas/{id_cuenta}/posicionValuada`` via default-client."""
    return _get_default().get_posicion_valuada(
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


def get_listado_cuentas(
    *,
    id_cuenta: list[str] | None = None,
    tipo_cuenta: str | None = None,
    estado: str | None = None,
    fecha_desde: dt.date | None = None,
    fecha_hasta: dt.date | None = None,
) -> list[Cuenta]:
    """``GET /api/cuentas/listadoCuentas`` via default-client."""
    return _get_default().get_listado_cuentas(
        id_cuenta=id_cuenta,
        tipo_cuenta=tipo_cuenta,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


def get_posiciones(
    id_cuenta: str,
    fecha: dt.date,
    *,
    especie: str | None = None,
    incluir_parking: bool = False,
) -> list[Posicion]:
    """``GET /api/cuentas/{id_cuenta}/posiciones`` via default-client."""
    return _get_default().get_posiciones(
        id_cuenta,
        fecha,
        especie=especie,
        incluir_parking=incluir_parking,
    )


# ---------------------------------------------------------------------------
# Internal accessors for the module-level _request shim
# ---------------------------------------------------------------------------


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """Module-level shim — delega en el default-client.

    Mantenido para preservar compatibilidad con tests legacy que invocan
    ``higyrus_client.client._request(...)`` directamente.
    """
    return _get_default()._request(method, path, params=params, json_body=json_body)


# ---------------------------------------------------------------------------
# PEP 562 read-only shim — D-01, D-02
# ---------------------------------------------------------------------------

# Maps legacy module-level name -> _ClientState attribute name. The
# ``_token_ts`` entry encodes the cross-pkg rename to ``token_expires_at``
# (the field stores absolute epoch; conftest's 9_999_999_999.0 value is a
# valid future epoch — year 2286 — so legacy fixtures migrate cleanly).
_FORWARDED_TO_STATE: dict[str, str] = {
    "_token": "token",
    "_token_ts": "token_expires_at",
}

_FORWARDED_HTTP_CLIENT = "_client"


def __getattr__(name: str) -> Any:
    """PEP 562 read-only shim (D-01).

    Forwards reads of legacy names to the default-client's state. Reads
    of credential names raise ``AttributeError`` to force callers onto
    ``configure()``.
    """
    if name in _FORWARDED_TO_STATE:
        return getattr(_get_default()._state, _FORWARDED_TO_STATE[name])
    if name == _FORWARDED_HTTP_CLIENT:
        return _get_default()._state.http_client
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
