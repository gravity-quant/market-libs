"""Pure builders and parsers for the higyrus-client REST client.

Phase 7 REFAC-03 + D-01 (per-package ``RequestSpec`` con ``json_body`` +
``url_pre_encoded``) + D-02 (auth-flow factorizado) + D-04 (B8 identity via
alias re-export) + D-06 (body-consume-then-raise) + URL-encoding quirk
encapsulation.

This module is **private** — only ``higyrus_client.client`` and
``higyrus_client.aio`` may import it (enforced by ``import-linter`` contract
``higyrus_client._core does not depend on transport modules`` in
``pyproject.toml``).

**URL-encoding quirk (Higyrus IIS rechaza %2F):** los date params del backend
viajan en ``dd/mm/yyyy``; Higyrus IIS responde 400 "formato dd/mm/yyyy" si la
``/`` viaja como ``%2F``. La quirk vive ENCAPSULADA acá: cada
``build_<endpoint>_request`` que tiene query params usa::

    urlencode(params, doseq=True, quote_via=quote, safe="/")

y retorna ``RequestSpec(path=<path-con-?query-pre-encoded>,
url_pre_encoded=True)``. Los transport shells ``client.py``/``aio.py`` NO
conocen el detalle de encoding: cuando ``spec.url_pre_encoded is True``,
forwardean ``spec.path`` verbatim al ``httpx.Client.request(url=..., params=None)``.

**Auth flow (D-02):** ``build_login_request(state)`` retorna el
``RequestSpec`` con JSON body de credenciales; ``parse_login_response(resp)``
hace body-consume + ``raise_for_response`` + extract del ``token`` y computa
``token_expires_at = time.time() + _TOKEN_TTL_SECONDS``. Los shells orquestan
el HTTP call y escriben al state.

**D-04 alias re-export:** ``raise_for_response`` es el single source of truth
para mapear ``HigyrusClientError``. ``client.py`` y ``aio.py`` lo aliasean como
``_raise_for_response = _core.raise_for_response`` (módulo-level) — la
identidad ``aio._raise_for_response is client._raise_for_response`` se preserva
porque ambos referencian el MISMO objeto en ``_core``.

**D-06 body-consume-then-raise:** todos los ``parse_<endpoint>_response``
empiezan con ``resp.read()`` antes del status check — protege contra leaks de
HTTP/2 conn pool cuando el caller no consumió el body.

No I/O. No imports from ``higyrus_client.client`` or ``higyrus_client.aio``
(enforced by import-linter).
"""

from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from higyrus_client import _decode
from higyrus_client._params import drop_none, format_bool, format_date
from higyrus_client._state import _TOKEN_TTL_SECONDS, _ClientState
from higyrus_client.exceptions import (
    HigyrusAPIError,
    HigyrusAuthError,
    HigyrusAuthorizationError,
    HigyrusRateLimitError,
)
from higyrus_client.models import Cuenta, Health, Movimiento, Posicion, PosicionValuada

__all__ = [
    "RequestSpec",
    "build_get_health_request",
    "build_get_listado_cuentas_request",
    "build_get_movimientos_request",
    "build_get_posicion_valuada_request",
    "build_get_posiciones_request",
    "build_login_request",
    "parse_get_health_response",
    "parse_get_listado_cuentas_response",
    "parse_get_movimientos_response",
    "parse_get_posicion_valuada_response",
    "parse_get_posiciones_response",
    "parse_login_response",
    "raise_for_response",
    "token_is_fresh",
]


# ---------------------------------------------------------------------------
# RequestSpec
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RequestSpec:
    """Inmutable description of a higyrus HTTP request — no transport coupling.

    Per-package shape (D-01): higyrus tiene ``json_body`` para el ``POST
    /api/login`` y ``url_pre_encoded: bool`` para señalar que ``path`` ya
    incluye la query string pre-encoded con la quirk Higyrus
    (``urlencode(..., doseq=True, quote_via=quote, safe="/")``).

    Convención del shell consumer:

    - ``url_pre_encoded is True``  → ``path`` incluye ``?query=...`` con
      ``/`` literal preservado. El shell forwarda ``spec.path`` verbatim a
      ``httpx`` con ``params=None`` (no agrega ni recodifica).
    - ``url_pre_encoded is False`` → ``path`` es sólo la ruta; ``params``
      (si no es ``None``) se pasan como kwarg a ``httpx`` que aplica el
      encoding standard.

    Phase 8 D-01/D-09/D-11 extensions (additive, back-compat preserving):

    - ``idempotent: bool = False`` — mutation gate per RELY-03. POST/PATCH
      stay ``False`` (default); GET builders + ``build_login_request`` flip
      ``True`` per D-03. The shell ``_request()`` copies this to
      ``request.extensions["idempotent"]`` so the RetryTransport's gate sees
      it.
    - ``endpoint_name: str = ""`` — symbolic name for structured log records.
      Set by builders (e.g. ``endpoint_name="get_movimientos"``); propagated
      via ``request.extensions["endpoint_name"]``.
    - ``account_id: str | None = None`` — higyrus-specific D-11 propagation.
      Builders that accept ``id_cuenta`` populate this field; the shell
      ``_request()`` sets ``request.extensions["account_id"]`` only when
      non-None (no leak when caller doesn't pass id_cuenta).
    """

    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    json_body: dict[str, Any] | None = None
    url_pre_encoded: bool = False
    # Phase 8 additions (additive, defaulted for back-compat with Phase 7).
    idempotent: bool = False
    endpoint_name: str = ""
    account_id: str | None = None


# ---------------------------------------------------------------------------
# Stateless helpers (D-04 — moved from client.py; alias preserved there)
# ---------------------------------------------------------------------------


def raise_for_response(resp: httpx.Response) -> None:
    """Mapea respuestas non-2xx a la jerarquía ``HigyrusClientError``.

    No-op para respuestas 2xx/3xx — contrato compartido con ambito/iol/matriz
    (CR-01 fix Phase 7 review). Sin este guard cualquier caller directo
    obtendría ``HigyrusAPIError(status_code=200, ...)`` en un happy-path.

    Precondición (D-06): ``resp.read()`` (o ``_consume_and_check``) ya fue
    llamado antes de este helper — el body está en buffer. ``resp.json()``
    acá es idempotente sobre el buffer en memoria; el caller es responsable
    del orden body-consume-then-raise. Tolerante a body no-JSON: si falla
    el decode, ``errors`` y ``timestamp`` quedan vacíos pero la excepción
    se levanta igual.

    D-04: single source of truth para el mapping de errores. ``client.py`` y
    ``aio.py`` lo aliasean como ``_raise_for_response = _core.raise_for_response``;
    la identidad ``aio._raise_for_response is client._raise_for_response`` se
    preserva.
    """
    if not resp.is_error:
        return  # no-op para 2xx/3xx — consistente con el resto del monorepo

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


def token_is_fresh(state: _ClientState) -> bool:
    """Token exists and hasn't expired according to the absolute epoch in state."""
    return bool(state.token) and time.time() < state.token_expires_at


# ---------------------------------------------------------------------------
# Auth flow primitives (D-02)
# ---------------------------------------------------------------------------


def build_login_request(state: _ClientState) -> RequestSpec:
    """Construye el ``RequestSpec`` para ``POST /api/login``.

    Levanta ``HigyrusAuthError`` (status 0) si las creds o el ``base_url`` no
    fueron configuradas — equivalente al guard que el legacy ``Client.login()``
    aplicaba antes del HTTP call. Mantener el raise acá deja al shell con un
    único concern: ejecutar el request.
    """
    if not state.base_url:
        raise HigyrusAuthError(0, [{"title": "config", "detail": "HIGYRUS_BASE_URL must be set"}])
    if not state.username or not state.password:
        raise HigyrusAuthError(
            0,
            [{"title": "config", "detail": "HIGYRUS_USER and HIGYRUS_PASSWORD must be set"}],
        )
    return RequestSpec(
        method="POST",
        path="/api/login",
        json_body={
            "clientId": state.client_id,
            "username": state.username,
            "password": state.password,
        },
        # D-03: login is replay-safe (a fresh Bearer simply replaces the prior);
        # marked idempotent=True so transient 5xx during auth retries via the
        # RetryTransport. 401 still NEVER retries — handled by shell re-auth flow.
        idempotent=True,
        endpoint_name="login",
    )


def parse_login_response(resp: httpx.Response) -> tuple[str, float]:
    """D-06 body-consume-then-raise + extract ``(token, expires_at)``.

    Orden CRÍTICO:
      1. ``resp.read()``  ← consume body explícito (HTTP/2-safe)
      2. ``raise_for_response(resp)``  ← status check después de consumir
      3. ``resp.json()``  ← decode (raises ValueError si malformed)
      4. extract ``token`` + compute ``expires_at = now + _TOKEN_TTL_SECONDS``

    El TTL absoluto se compone acá para que el shell no tenga que importar
    ``_TOKEN_TTL_SECONDS`` ni reproducir la matemática.
    """
    resp.read()
    if not resp.is_success:
        raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    token = data.get("token")
    if not isinstance(token, str) or not token:
        raise HigyrusAuthError(
            resp.status_code,
            [{"title": "auth", "detail": "No token in login response"}],
        )
    expires_at = time.time() + _TOKEN_TTL_SECONDS
    return token, expires_at


# ---------------------------------------------------------------------------
# Endpoint builders — URL-encoding quirk encapsulator
# ---------------------------------------------------------------------------


def _encode_query(base_path: str, params: dict[str, Any]) -> str:
    """Wrapper around ``urlencode`` con la quirk Higyrus.

    ``doseq=True``: si un valor es ``list[str]`` (e.g. ``idCuenta=["A","B"]``),
    se re-emite como claves repetidas (``idCuenta=A&idCuenta=B``) — necesario
    para el filtro multi-cuenta en ``GET /api/cuentas/listadoCuentas``.

    ``quote_via=quote`` + ``safe="/"``: preserva ``/`` literal en los valores
    (date params ``dd/mm/yyyy``) porque Higyrus IIS rechaza ``%2F`` con 400
    "formato dd/mm/yyyy" (F-01..F-06 plan 04-04 Phase 6).
    """
    clean = drop_none(params)
    if not clean:
        return base_path
    query = urlencode(clean, doseq=True, quote_via=quote, safe="/")
    return f"{base_path}?{query}"


def build_get_health_request(_state: _ClientState) -> RequestSpec:
    """``GET /api/health`` — sin params, sin quirk."""
    return RequestSpec(
        method="GET",
        path="/api/health",
        idempotent=True,
        endpoint_name="get_health",
    )


def build_get_movimientos_request(
    _state: _ClientState,
    id_cuenta: str,
    fecha_desde: dt.date,
    fecha_hasta: dt.date,
    *,
    especie: str | None = None,
    tipo_titulo: str | None = None,
    tipo_titulo_agente: str | None = None,
    movimiento: str | None = None,
) -> RequestSpec:
    """``GET /api/cuentas/{id_cuenta}/movimientos`` con quirk encapsulada."""
    params: dict[str, Any] = {
        "fechaDesde": format_date(fecha_desde),
        "fechaHasta": format_date(fecha_hasta),
        "especie": especie,
        "tipoTitulo": tipo_titulo,
        "tipoTituloAgente": tipo_titulo_agente,
        "movimiento": movimiento,
    }
    path = _encode_query(f"/api/cuentas/{id_cuenta}/movimientos", params)
    return RequestSpec(
        method="GET",
        path=path,
        url_pre_encoded=True,
        idempotent=True,
        endpoint_name="get_movimientos",
        account_id=id_cuenta,
    )


def build_get_posicion_valuada_request(
    _state: _ClientState,
    id_cuenta: str,
    *,
    tipo_cuenta: str,
    nivel: str,
    desde: dt.date,
    hasta: dt.date,
    lugar: str | None = None,
    estado: str | None = None,
    tipo_titulo: str | None = None,
    extracto: str | None = None,
    ocultar_cerradas: bool | None = None,
    especie: str | None = None,
    concertacion: bool | None = None,
    actualizar: bool | None = None,
) -> RequestSpec:
    """``GET /api/cuentas/{id_cuenta}/posicionValuada`` con quirk encapsulada."""
    params: dict[str, Any] = {
        "tipoCuenta": tipo_cuenta,
        "nivel": nivel,
        "desde": format_date(desde),
        "hasta": format_date(hasta),
        "lugar": lugar,
        "estado": estado,
        "tipoTitulo": tipo_titulo,
        "extracto": extracto,
        "ocultarCerradas": format_bool(ocultar_cerradas),
        "especie": especie,
        "concertacion": format_bool(concertacion),
        "actualizar": format_bool(actualizar),
    }
    path = _encode_query(f"/api/cuentas/{id_cuenta}/posicionValuada", params)
    return RequestSpec(
        method="GET",
        path=path,
        url_pre_encoded=True,
        idempotent=True,
        endpoint_name="get_posicion_valuada",
        account_id=id_cuenta,
    )


def build_get_listado_cuentas_request(
    _state: _ClientState,
    *,
    id_cuenta: list[str] | None = None,
    tipo_cuenta: str | None = None,
    estado: str | None = None,
    fecha_desde: dt.date | None = None,
    fecha_hasta: dt.date | None = None,
) -> RequestSpec:
    """``GET /api/cuentas/listadoCuentas`` con quirk encapsulada (doseq para id_cuenta list)."""
    params: dict[str, Any] = {
        "idCuenta": id_cuenta,
        "tipoCuenta": tipo_cuenta,
        "estado": estado,
        "fechaDesde": format_date(fecha_desde),
        "fechaHasta": format_date(fecha_hasta),
    }
    path = _encode_query("/api/cuentas/listadoCuentas", params)
    # listadoCuentas does NOT take a single id_cuenta — it can filter by a LIST
    # of accounts via the ``id_cuenta`` kwarg. We do NOT set account_id (D-11
    # is single-account-scoped; multi-account log correlation is out of scope).
    return RequestSpec(
        method="GET",
        path=path,
        url_pre_encoded=True,
        idempotent=True,
        endpoint_name="get_listado_cuentas",
    )


def build_get_posiciones_request(
    _state: _ClientState,
    id_cuenta: str,
    *,
    fecha: dt.date,
    especie: str | None = None,
    incluir_parking: bool = False,
) -> RequestSpec:
    """``GET /api/cuentas/{id_cuenta}/posiciones`` con quirk encapsulada."""
    params: dict[str, Any] = {
        "fecha": format_date(fecha),
        "especie": especie,
        "incluirParking": format_bool(incluir_parking),
    }
    path = _encode_query(f"/api/cuentas/{id_cuenta}/posiciones", params)
    return RequestSpec(
        method="GET",
        path=path,
        url_pre_encoded=True,
        idempotent=True,
        endpoint_name="get_posiciones",
        account_id=id_cuenta,
    )


# ---------------------------------------------------------------------------
# Endpoint parsers — body-consume-then-raise (D-06) + SafeModel.from_api
# ---------------------------------------------------------------------------


def _consume_and_check(resp: httpx.Response) -> bytes:
    """D-06: ``resp.read()`` (idempotente) + status check. Devuelve el body raw."""
    body = resp.read()
    if not resp.is_success:
        raise_for_response(resp)
    return body


@_decode._response_parser
def parse_get_health_response(resp: httpx.Response) -> Health:
    """Parser ``GET /api/health`` → :class:`Health`. 204 / body vacío → zero-valued.

    CR-02 fix Phase 7 review: el comportamiento previo levantaba
    ``HigyrusAPIError(status_code=0, errors=[{shape mismatch, expected dict, got
    empty body}])`` en 204 o body vacío, lo cual rompe el contrato HTTP (204
    No Content es una respuesta válida para health check sin body) y produce un
    error confuso con ``status_code=0`` que el caller no puede distinguir de
    un error real. Si el servidor alguna vez cambia 200→204, el cliente rompía
    silenciosamente.

    Consistente con los otros parsers de lista del módulo, que tratan
    204/empty body como su zero-value (``[]`` para list parsers, el zero-valued
    ``Health`` acá).

    Phase 31 TYP-02 (D-01 / D-04): el retorno pasa de mapping a :class:`Health`,
    y el carve-out de 204 / body vacío devuelve ``Health.from_api(None)`` — la
    instancia zero-valued, explícitamente NO un mapping vacío. Efecto observable
    medido: un payload ``None`` es una divergencia ``non_dict``, así que un 204
    legítimo emite UN record en el logger ``higyrus_client`` y, bajo
    ``strict_decode=True``, levanta :class:`HigyrusDecodeError` en vez de
    devolver la instancia. Es un delta real sobre la rama defensiva que CR-02
    introdujo justamente para que un 204 NO levantara; queda pinneado por test.
    """
    body = _consume_and_check(resp)
    if resp.status_code == 204 or not body:
        return Health.from_api(None)
    raw = resp.json()
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
    return Health.from_api(raw)


@_decode._response_parser
def _parse_list_or_raise(resp: httpx.Response, model_cls: type[Any]) -> list[Any]:
    """Helper común para parsers que retornan ``list[Model]`` con 204→``[]``."""
    body = _consume_and_check(resp)
    if resp.status_code == 204 or not body:
        return []
    raw = resp.json()
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
    return [model_cls.from_api(item) for item in raw]


def parse_get_movimientos_response(resp: httpx.Response) -> list[Movimiento]:
    """Parser ``GET /api/cuentas/{id_cuenta}/movimientos`` → ``list[Movimiento]``."""
    result: list[Movimiento] = _parse_list_or_raise(resp, Movimiento)
    return result


def parse_get_posicion_valuada_response(resp: httpx.Response) -> list[PosicionValuada]:
    """Parser ``GET /api/cuentas/{id_cuenta}/posicionValuada`` → ``list[PosicionValuada]``."""
    result: list[PosicionValuada] = _parse_list_or_raise(resp, PosicionValuada)
    return result


def parse_get_listado_cuentas_response(resp: httpx.Response) -> list[Cuenta]:
    """Parser ``GET /api/cuentas/listadoCuentas`` → ``list[Cuenta]``."""
    result: list[Cuenta] = _parse_list_or_raise(resp, Cuenta)
    return result


def parse_get_posiciones_response(resp: httpx.Response) -> list[Posicion]:
    """Parser ``GET /api/cuentas/{id_cuenta}/posiciones`` → ``list[Posicion]``."""
    result: list[Posicion] = _parse_list_or_raise(resp, Posicion)
    return result
