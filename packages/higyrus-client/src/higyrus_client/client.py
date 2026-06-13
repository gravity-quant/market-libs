"""Cliente HTTP sincrónico para la API de Higyrus.

Dos formas equivalentes de usar el cliente:

1. **API a nivel módulo (legacy):** ``import higyrus_client`` + llamar
   ``higyrus_client.get_listado_cuentas(...)``. Delega en una instancia
   perezosa de :class:`Client` creada al primer uso.

2. **Instancia explícita** (Phase 6 REFAC-02)::

        from higyrus_client import Client

        with Client(base_url="...", client_id="...", username="...",
                    password="...") as c:
            cuentas = c.get_listado_cuentas(estado="alta")

El token se obtiene con ``POST /api/login`` (Bearer 24 h TTL) en la primera
llamada que lo requiera; refresh automático antes del vencimiento.
``login()`` está expuesto si querés validar creds temprano, pero no es
obligatorio. Configuración por env vars (``HIGYRUS_BASE_URL``,
``HIGYRUS_USER``, ``HIGYRUS_PASSWORD``, ``HIGYRUS_CLIENT_ID``) cargadas
con ``python-dotenv``; reconfigurable en runtime via :func:`configure`.

**Phase 7 REFAC-03** — transport shell: la lógica pura (builders/parsers
+ URL-encoding quirk + ``raise_for_response``) vive en
:mod:`higyrus_client._core`. Endpoint methods = 3-liners. La quirk
Higyrus (IIS rechaza ``%2F``) está encapsulada en ``_core``; este módulo
NO conoce el detalle de URL-encoding.

**D-04 B8 alias:** ``_raise_for_response`` aliasea
``_core.raise_for_response`` — la identidad
``aio._raise_for_response is client._raise_for_response`` se preserva.

**PEP 562 compat shim** (D-01, D-02): reads de ``_token``, ``_token_ts``
(renamed a ``token_expires_at``) y ``_client`` forwardean al state del
default-client; reads de ``_user``/``_password``/``_client_id``/
``_base_url`` levantan ``AttributeError`` (forzar el uso de
``configure()``). Escrituras NO soportadas — usar ``configure()`` o
``Client(...)`` explícito.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Self

import httpx
from dotenv import load_dotenv

from higyrus_client import _core, _transport
from higyrus_client._core import RequestSpec
from higyrus_client._state import _REQUEST_TIMEOUT, _ClientState
from higyrus_client.exceptions import HigyrusAuthError
from higyrus_client.models import Cuenta, Movimiento, Posicion, PosicionValuada

load_dotenv()


# ---------------------------------------------------------------------------
# Module-level helper alias (D-04 — B8 identity preserved via _core)
# ---------------------------------------------------------------------------

# Aliasea ``_core.raise_for_response`` a nivel módulo. ``higyrus_client.aio``
# importa el MISMO objeto desde ``_core``, así que la identidad
# ``aio._raise_for_response is client._raise_for_response`` queda en pie.
_raise_for_response = _core.raise_for_response


# ---------------------------------------------------------------------------
# Client class — Phase 7 transport shell
# ---------------------------------------------------------------------------


class Client:
    """Sync HTTP client for Higyrus. State en ``self._state`` (``_ClientState``).

    Phase 7 transport shell. Pickle / deepcopy NO soportados (D-23).
    """

    __slots__ = ("_max_retries", "_state")

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
        http_client: httpx.Client | None = None,
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
        # Phase 8 D-15 / D-19: max_retries=N → max_attempts=N+1 (1 initial + N retries).
        # max_retries=0 disables retries entirely per D-19 (max_attempts <= 1 bypass).
        self._max_retries = max_retries
        # Phase 8 D-16: caller-supplied http_client used AS-IS (no auto-wrap).
        if http_client is not None:
            self._state.http_client = http_client

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
        """Cierra ``httpx.Client`` si fue inicializado. Idempotente."""
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

    # ---- HTTP client + auth ----

    def _ensure_http_client(self) -> httpx.Client:
        """Crea ``httpx.Client`` lazy en el primer uso.

        Phase 8 D-15 / D-19: wraps ``RetryTransport`` so all requests (auth and
        endpoint) benefit from bounded retries + full-jitter backoff. The
        transport's mutation gate (D-01) honors ``request.extensions["idempotent"]``
        so non-idempotent specs pass through with no retry loop. ``max_attempts =
        max_retries + 1`` per the anthropic/openai SDK semantics (D-19).
        """
        client = self._state.http_client
        if isinstance(client, httpx.Client):
            return client
        new_client = httpx.Client(
            timeout=_REQUEST_TIMEOUT,
            transport=_transport.RetryTransport(max_attempts=self._max_retries + 1),
        )
        self._state.http_client = new_client
        return new_client

    def _send_auth_request(self, spec: RequestSpec) -> httpx.Response:
        """Send an auth-flow request (login) through the RetryTransport with extensions.

        Phase 8 D-29: login goes through the SAME RetryTransport as endpoint
        requests so transient 5xx are retry-eable (D-03 marks ``build_login_request``
        ``idempotent=True``). The shell propagates ``request_id`` + ``endpoint_name``
        via ``request.extensions`` so the transport's structured WARNING/ERROR
        records carry the canonical D-09 fields. NO ``Authorization`` header —
        auth-flow itself establishes the token.

        URL-encoding quirk preservation (Phase 7): login uses ``json_body``, not
        ``params``, so ``url_pre_encoded`` does not apply here.
        """
        http = self._ensure_http_client()
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
        return http.send(req)

    def login(self) -> str:
        """Autentica contra ``POST /api/login`` y cachea el token (TTL 23h)."""
        spec = _core.build_login_request(self._state)
        resp = self._send_auth_request(spec)
        token, expires_at = _core.parse_login_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        return token

    def _ensure_token(self) -> None:
        """Refresca el token si no existe o venció."""
        if not _core.token_is_fresh(self._state):
            self.login()

    def _request(self, spec: RequestSpec) -> httpx.Response:
        """Transport shell — orquesta auth + dispatch HTTP con 401 re-auth-once.

        Phase 8 D-02 + D-30 + D-11 + RELY-04: per-business-call ``request_id``
        (UUID4) propagated via ``request.extensions``; on 401 (``HigyrusAuthError``
        raised by ``_core.raise_for_response``), the shell clears the cached token,
        calls ``_ensure_token()`` to obtain a fresh Bearer, then retries the
        request ONCE with the refreshed Authorization header. The transport NEVER
        sees ``HigyrusAuthError`` (D-07 invariant — only HTTP/transport signals
        trigger retry); the shell handles the auth-stale case explicitly.

        D-11: ``spec.account_id`` (when non-None) is propagated to
        ``request.extensions["account_id"]`` so structured log records (WARNING/
        ERROR emitted by the RetryTransport) include it as an extra field. No
        leak when caller didn't pass id_cuenta.

        Second-401 case: if the retry also yields 401, ``raise_for_response`` on
        the second response re-raises HigyrusAuthError — NO recursion, NO
        infinite loop (Pitfall 1 prevention). All non-401 error statuses (429,
        5xx, etc.) raise their typed exceptions directly without re-auth.

        URL-encoding quirk preservation (Phase 7): when ``spec.url_pre_encoded``
        is True, the ``path`` already includes the pre-encoded query string with
        the Higyrus quirk (``/`` literal preserved). We forward it verbatim to
        ``httpx.Client.build_request(url=..., params=None)`` so httpx does not
        re-encode.

        WR-03 fix Phase 7 review: si ``_ensure_token()`` retorna sin excepción
        pero ``self._state.token`` queda ``None`` (estado inconsistente —
        servidor responde 200 sin token), reemplazamos el ``assert`` por
        ``HigyrusAuthError`` tipado.
        """
        self._ensure_token()
        token = self._state.token
        if token is None:
            raise HigyrusAuthError(
                0,
                [{"title": "auth", "detail": "_ensure_token() returned without populating token"}],
            )

        request_id = uuid.uuid4().hex
        http = self._ensure_http_client()
        url = f"{self._state.base_url}{spec.path}"
        headers = {"Authorization": f"Bearer {token}", **(spec.headers or {})}

        # WR-02 preservation + URL-encoding quirk preservation:
        # - When url_pre_encoded is True: build with params=None, path is verbatim.
        # - When url_pre_encoded is False: pass params= kwarg so httpx encodes them.
        build_params: dict[str, Any] | None = None if spec.url_pre_encoded else spec.params
        # json_body is omitted when None to avoid injecting ``null`` on GETs.
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
        # D-11: only set account_id when non-None (no leak when caller didn't pass id_cuenta).
        if spec.account_id is not None:
            req.extensions["account_id"] = spec.account_id

        resp = http.send(req)
        try:
            _raise_for_response(resp)
        except HigyrusAuthError:
            # D-02 exactly-one re-auth: clear cached token, re-authenticate, retry once.
            # higyrus has no Risk API → no auth_basic branch to skip (cf. matriz D-23).
            self._state.token = None
            self._ensure_token()
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
            resp = http.send(req)
            _raise_for_response(resp)
        return resp

    # ---- Endpoints (Phase 7 3-liner shells) ----

    def get_health(self) -> dict[str, Any]:
        """``GET /api/health`` (requiere Bearer)."""
        spec = _core.build_get_health_request(self._state)
        return _core.parse_get_health_response(self._request(spec))

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
        """``GET /api/cuentas/{id_cuenta}/movimientos``."""
        spec = _core.build_get_movimientos_request(
            self._state, id_cuenta, fecha_desde, fecha_hasta,
            especie=especie, tipo_titulo=tipo_titulo,
            tipo_titulo_agente=tipo_titulo_agente, movimiento=movimiento,
        )  # fmt: skip
        return _core.parse_get_movimientos_response(self._request(spec))

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
        """``GET /api/cuentas/{id_cuenta}/posicionValuada``."""
        spec = _core.build_get_posicion_valuada_request(
            self._state, id_cuenta, tipo_cuenta=tipo_cuenta, nivel=nivel,
            desde=desde, hasta=hasta, lugar=lugar, estado=estado,
            tipo_titulo=tipo_titulo, extracto=extracto,
            ocultar_cerradas=ocultar_cerradas, especie=especie,
            concertacion=concertacion, actualizar=actualizar,
        )  # fmt: skip
        return _core.parse_get_posicion_valuada_response(self._request(spec))

    def get_listado_cuentas(
        self,
        *,
        id_cuenta: list[str] | None = None,
        tipo_cuenta: str | None = None,
        estado: str | None = None,
        fecha_desde: dt.date | None = None,
        fecha_hasta: dt.date | None = None,
    ) -> list[Cuenta]:
        """``GET /api/cuentas/listadoCuentas``."""
        spec = _core.build_get_listado_cuentas_request(
            self._state, id_cuenta=id_cuenta, tipo_cuenta=tipo_cuenta,
            estado=estado, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        )  # fmt: skip
        return _core.parse_get_listado_cuentas_response(self._request(spec))

    def get_posiciones(
        self,
        id_cuenta: str,
        fecha: dt.date,
        *,
        especie: str | None = None,
        incluir_parking: bool = False,
    ) -> list[Posicion]:
        """``GET /api/cuentas/{id_cuenta}/posiciones``."""
        spec = _core.build_get_posiciones_request(
            self._state, id_cuenta, fecha=fecha, especie=especie,
            incluir_parking=incluir_parking,
        )  # fmt: skip
        return _core.parse_get_posiciones_response(self._request(spec))


# ---------------------------------------------------------------------------
# Default-client + module-level API (legacy) — preserve public surface
# ---------------------------------------------------------------------------

_default_client: Client | None = None


def _get_default() -> Client:
    """Devuelve el ``Client`` perezoso a nivel módulo."""
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
    max_retries: int | None = None,
    http_client: httpx.Client | None = None,
) -> None:
    """Sobrescribe credenciales/URL del default-client en runtime.

    Semántica carry-forward: el default-client se reemplaza por una NUEVA
    instancia copiando los valores actuales para kwargs no pasados.

    Phase 8 D-15 / D-16 / D-19: ``max_retries`` (default 2; ``0`` disables
    retries entirely per D-19) and ``http_client`` (used AS-IS without
    auto-wrapping with ``RetryTransport`` per D-16) are carry-forward kwargs.
    Replacing the default-client closes the prior cached ``httpx.Client``.
    """
    global _default_client
    current = _get_default()
    # Phase 8: carry forward max_retries from the current client unless explicitly overridden.
    next_max_retries = max_retries if max_retries is not None else current._max_retries
    new = Client(
        base_url=base_url if base_url is not None else current._state.base_url,
        client_id=client_id if client_id is not None else current._state.client_id,
        username=username if username is not None else current._state.username,
        password=password if password is not None else current._state.password,
        token=token,
        token_expires_at=token_expires_at,
        max_retries=next_max_retries,
        http_client=http_client,
    )
    current.close()
    _default_client = new


def login() -> str:
    return _get_default().login()


def get_health() -> dict[str, Any]:
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
    return _get_default().get_movimientos(
        id_cuenta, fecha_desde, fecha_hasta,
        especie=especie, tipo_titulo=tipo_titulo,
        tipo_titulo_agente=tipo_titulo_agente, movimiento=movimiento,
    )  # fmt: skip


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
    return _get_default().get_posicion_valuada(
        id_cuenta, tipo_cuenta, nivel, desde, hasta,
        lugar=lugar, estado=estado, tipo_titulo=tipo_titulo,
        extracto=extracto, ocultar_cerradas=ocultar_cerradas,
        especie=especie, concertacion=concertacion, actualizar=actualizar,
    )  # fmt: skip


def get_listado_cuentas(
    *,
    id_cuenta: list[str] | None = None,
    tipo_cuenta: str | None = None,
    estado: str | None = None,
    fecha_desde: dt.date | None = None,
    fecha_hasta: dt.date | None = None,
) -> list[Cuenta]:
    return _get_default().get_listado_cuentas(
        id_cuenta=id_cuenta, tipo_cuenta=tipo_cuenta, estado=estado,
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
    )  # fmt: skip


def get_posiciones(
    id_cuenta: str,
    fecha: dt.date,
    *,
    especie: str | None = None,
    incluir_parking: bool = False,
) -> list[Posicion]:
    return _get_default().get_posiciones(
        id_cuenta, fecha, especie=especie, incluir_parking=incluir_parking,
    )  # fmt: skip


# ---------------------------------------------------------------------------
# Legacy module-level `_request` shim + PEP 562 read-only shim
# ---------------------------------------------------------------------------


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """Module-level shim legacy — preserva signature pre-Phase-7 para tests."""
    spec = RequestSpec(method=method, path=path, params=params, json_body=json_body)
    resp = _get_default()._request(spec)
    if not resp.is_success:
        _core.raise_for_response(resp)
    if resp.status_code == 204 or not resp.content:
        return None
    body: dict[str, Any] | list[Any] = resp.json()
    return body


# Maps legacy module-level name -> _ClientState attribute name. The
# ``_token_ts`` entry encodes the cross-pkg rename to ``token_expires_at``.
_FORWARDED_TO_STATE: dict[str, str] = {
    "_token": "token",
    "_token_ts": "token_expires_at",
}

_FORWARDED_HTTP_CLIENT = "_client"


def __getattr__(name: str) -> Any:
    """PEP 562 read-only shim (D-01)."""
    if name in _FORWARDED_TO_STATE:
        return getattr(_get_default()._state, _FORWARDED_TO_STATE[name])
    if name == _FORWARDED_HTTP_CLIENT:
        return _get_default()._state.http_client
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
