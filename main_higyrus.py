"""Driver de verificación en vivo del paquete ``higyrus-client`` (Phase 4 → 9).

Ejecuta 19 probes nombrados (18 originales Phase 4 + ``probe_multi_account_iteration``
agregado en Phase 9 Plan 09-02 para BUG-04) que ejercitan la superficie pública
sync+async del cliente Higyrus contra ``https://cliente.aunesa.com/Irmo`` (o el
override ``HIGYRUS_BASE_URL``) y producen seis artefactos committeables: el
findings markdown clasificado y 5 schema snapshots JSON (DRIFT-01 mirror, uno
por endpoint).

Probes en orden de PRESENTATION D-HIGY-10 (las líneas ``PROBE ...: ...`` se
imprimen al final en este orden — la EXECUTION order es distinta y respeta
``_resolved_cuenta`` resolution-before-async, ver ``main()``):

1.  ``probe_login_sync``                       — ``higyrus_client.login()`` (HIGY-01).
2.  ``probe_login_async``                      — ``await aio.login()`` (HIGY-01).
3.  ``probe_get_health_sync``                  — ``GET /api/health`` (HIGY-02).
4.  ``probe_get_health_async``                 — espejo async (HIGY-02).
5.  ``probe_get_listado_cuentas_sync``         — ``estado="alta"``; RESOLVES ``_resolved_cuenta`` (HIGY-02, D-HIGY-11).
6.  ``probe_get_listado_cuentas_async``        — espejo async (HIGY-02).
7.  ``probe_get_movimientos_sync``             — ``_resolved_cuenta`` + últimos 30 días (HIGY-02 + HIGY-07).
8.  ``probe_get_movimientos_async``            — espejo async (HIGY-02).
9.  ``probe_get_posicion_valuada_sync``        — ``_resolved_cuenta`` + propia/detalle/today (HIGY-02).
10. ``probe_get_posicion_valuada_async``       — espejo async (HIGY-02).
11. ``probe_get_posiciones_sync``              — ``_resolved_cuenta`` + today (HIGY-02 + HIGY-07).
12. ``probe_get_posiciones_async``             — espejo async (HIGY-02).
13. ``probe_parity_sync_async``                — captura ``httpx.Request.url.query`` sync vs async (HIGY-06).
14. ``probe_field_type_map``                   — diff bidireccional SafeModel vs wire sobre 4 endpoints (HIGY-03).
15. ``probe_schema_snapshot``                  — 5 snapshots con envelope D-21 + D-25 no-overwrite (D-HIGY-16).
16. ``probe_errors_envelope_sync``             — id_cuenta inválido → envelope ``[{title, detail}]`` (HIGY-05).
17. ``probe_errors_envelope_async``            — espejo async (HIGY-05).
18. ``probe_multi_account_iteration``          — loop sobre 2 cuentas con per-call ``id_cuenta`` kwarg; source order ``HIGYRUS_SAMPLE_CUENTAS`` CSV > live ``get_listado_cuentas`` (BUG-04, Phase 9 Plan 09-02).
19. ``probe_auth_401``                         — opt-in vía ``VERIFY_HIGYRUS_BAD_CREDS=1`` (HIGY-AUTH, D-HIGY-10 #18).

Uso::

    uv run --package higyrus-client python main_higyrus.py

Variables de entorno (cargadas por ``higyrus_client`` vía ``python-dotenv``):

- ``HIGYRUS_USER`` (requerido)
- ``HIGYRUS_PASSWORD`` (requerido)
- ``HIGYRUS_BASE_URL`` (requerido)
- ``HIGYRUS_CLIENT_ID`` (opcional, default ``""``)
- ``HIGYRUS_SAMPLE_CUENTA`` (opcional; override de ``cuentas[0].id`` resuelto por probe 5, D-HIGY-11)
- ``HIGYRUS_SAMPLE_CUENTAS`` (opcional; CSV ``A,B`` con ≥2 ids para forzar el multi-account probe sin depender de live ``get_listado_cuentas``, BUG-04 Phase 9)
- ``HIGYRUS_SAMPLE_TIPO_CUENTA`` (opcional, default ``"propia"``, D-HIGY-14)
- ``HIGYRUS_SAMPLE_NIVEL`` (opcional, default ``"detalle"``, D-HIGY-14)
- ``VERIFY_HIGYRUS_BAD_CREDS=1`` (opcional; activa ``probe_auth_401``, D-HIGY-10 #18)

Reglas de seguridad (Phase 4 es la PRIMERA fase con PII real en payloads):

- **D-HIGY-2 stdout discipline:** las líneas PROBE y el SUMMARY emiten sólo
  CONTEOS y SHAPE descriptors, NUNCA contenido de payloads (no nombres de
  titulares, no CBU, no CUIT). Los raw payloads se inspeccionan in-memory.
- **Auth-once discipline:** el primer ``login()`` cachea el token; los probes
  downstream reusan vía ``_ensure_token`` sin re-disparar password grant.
- **Cascade SKIPPED (D-HIGY-10 + Phase 3 D-IOL-3 mirror):** si
  ``probe_login_sync`` o ``probe_login_async`` fallan, los probes downstream
  emiten ``SKIPPED`` con razón ``auth failed``. Implementado vía flag
  module-level ``_auth_failed``.
- **Single-shot 401 (D-HIGY-10 #18 + T-4-02):** ``probe_auth_401`` es opt-in,
  sin retry, sin sleep, sin loop. Cada corrida consume **1** intento contra
  credenciales reales.
- **Try/finally con restore (T-4-07):** ``probe_auth_401`` SIEMPRE restaura
  ``HIGYRUS_PASSWORD`` original (vía ``configure``) aunque el call levante.
- **Redacción (D-HIGY-15):** todos los prints pasan por ``safe_print(text,
  secrets=[HIGYRUS_USER, HIGYRUS_PASSWORD, _sync_token_snapshot,
  _async_token_snapshot])``; los tokens se capturan POR VALOR tras cada login
  exitoso para que ``probe_auth_401`` (que puede resetear ``_token = None``
  vía ``configure``) no nulifique la lista de redacción. Defense-in-depth
  Phase 3 CR-03 mirror.

Artefactos generados (NO commiteados en este plan; se commitean en 04-03 tras
checkpoint humano):

- ``.planning/verification/higyrus-client-findings.md`` (esqueleto + appends).
- ``.planning/verification/schemas/higyrus-client/get-health.json``
- ``.planning/verification/schemas/higyrus-client/get-listado-cuentas.json``
- ``.planning/verification/schemas/higyrus-client/get-movimientos.json``
- ``.planning/verification/schemas/higyrus-client/get-posicion-valuada.json``
- ``.planning/verification/schemas/higyrus-client/get-posiciones.json``
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import json
import os
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from verification import (
    append_finding,
    diff_safemodel_bidirectional,
    require_env,
    safe_print,
    schema_of,
    write_findings,
)

import higyrus_client
from higyrus_client import HigyrusAPIError, HigyrusAuthError, HigyrusClientError, aio
from higyrus_client._params import format_bool, format_date
from higyrus_client.models import (
    Cuenta,
    Movimiento,
    Posicion,
    PosicionValuada,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_PKG = "higyrus-client"
_REPO_ROOT = Path(__file__).resolve().parent
_SCHEMA_DIR = _REPO_ROOT / ".planning" / "verification" / "schemas" / _PKG

# Phase 11 CR-06: tuple de excepciones residuales para los catch-all post-mapeo
# en los probe boundaries. Los probes capturan primero ``HigyrusAPIError`` /
# ``HigyrusAuthError`` / ``HigyrusAuthorizationError`` para los casos
# esperados; este catch-all atrapa cualquier residual de red, parsing o
# typing inesperado (e.g. SafeModel construction errors, dict.get sobre None),
# y los reporta via ``append_finding(..., class_="ERROR-MAP", ...)``. EXCLUYE
# ``KeyboardInterrupt`` y ``SystemExit`` (no son ``Exception`` subclasses).
_RESIDUAL_PROBE_EXCEPTIONS = (
    httpx.HTTPError,
    OSError,
    AttributeError,
    TypeError,
    ValueError,
    KeyError,
)
_SCHEMA_FILES: dict[str, Path] = {
    "get_health": _SCHEMA_DIR / "get-health.json",
    "get_listado_cuentas": _SCHEMA_DIR / "get-listado-cuentas.json",
    "get_movimientos": _SCHEMA_DIR / "get-movimientos.json",
    "get_posicion_valuada": _SCHEMA_DIR / "get-posicion-valuada.json",
    "get_posiciones": _SCHEMA_DIR / "get-posiciones.json",
}

# D-HIGY-16 envelope D-21: path templates por endpoint.
_ENDPOINT_TEMPLATES: dict[str, str] = {
    "get_health": "/api/health",
    "get_listado_cuentas": "/api/cuentas/listadoCuentas",
    "get_movimientos": "/api/cuentas/{id_cuenta}/movimientos",
    "get_posicion_valuada": "/api/cuentas/{id_cuenta}/posicionValuada",
    "get_posiciones": "/api/cuentas/{id_cuenta}/posiciones",
}

# D-HIGY-14: env vars opcionales para sample params.
_SAMPLE_CUENTA: str | None = os.getenv("HIGYRUS_SAMPLE_CUENTA")
_SAMPLE_TIPO_CUENTA: str = os.getenv("HIGYRUS_SAMPLE_TIPO_CUENTA", "propia")
_SAMPLE_NIVEL: str = os.getenv("HIGYRUS_SAMPLE_NIVEL", "detalle")

# Phase 9 D-10 (BUG-04): CSV de cuentas para el multi-account iteration probe.
# Override de la fuente "live ``get_listado_cuentas``" cuando devuelve <2
# cuentas o cuando el operator quiere forzar IDs conocidas. Formato CSV
# ``"A,B"`` (python-dotenv no soporta arrays nativos).
_SAMPLE_CUENTAS_CSV: str = os.getenv("HIGYRUS_SAMPLE_CUENTAS", "")

# D-HIGY-10 presentation order: lista declarada de los 18 probes en el orden en
# que se imprimen al final de main() (NO el orden de ejecución).
_D_HIGY_10_ORDER: tuple[str, ...] = (
    "login_sync",
    "login_async",
    "get_health_sync",
    "get_health_async",
    "get_listado_cuentas_sync",
    "get_listado_cuentas_async",
    "get_movimientos_sync",
    "get_movimientos_async",
    "get_posicion_valuada_sync",
    "get_posicion_valuada_async",
    "get_posiciones_sync",
    "get_posiciones_async",
    "parity_sync_async",
    "field_type_map",
    "schema_snapshot",
    "errors_envelope_sync",
    "errors_envelope_async",
    "multi_account_iteration",
    "auth_401",
)

# Contador module-level para asignar fids deterministicamente F-01, F-02, ...
_fid_counter: int = 0

# D-HIGY-10 cascade SKIPPED (Phase 3 D-IOL-3 mirror): flag único compartido
# entre surfaces sync y async. Si CUALQUIER login falla, todos los downstream
# emiten SKIPPED.
_auth_failed: bool = False
_auth_failure_reason: str = ""

# D-HIGY-11: id de cuenta resuelto por probe 5 (probe_get_listado_cuentas_sync)
# para que los downstream que requieren id_cuenta tengan un sample real. El
# orden de ejecución de main() garantiza que este global queda seteado ANTES
# del único ``asyncio.run(_async_main(...))`` (los probes async cuenta-
# dependientes reciben el valor por parámetro explícito).
_resolved_cuenta: str | None = None

# Phase 11 CR-07: el ``_capture_*_query_string`` helper muta in-place el
# ``event_hooks`` compartido del ``httpx.Client`` / ``httpx.AsyncClient`` del
# default-client de ``higyrus_client``. Si dos threads o dos coroutines invocan
# el helper concurrentemente, la restauración del hook del thread A puede
# sobreescribir el setup del thread B (race de read-modify-write). Estos locks
# serializan los críticos. La alternativa "per-request hook injection" (fresh
# ``httpx.Client(event_hooks=...)`` cada call) se descartó por radio de impacto
# excesivo (requiere reconstruir transport+auth del default-client) — el lock
# es mínimo y suficiente para preservar el invariante de no-corrupción.
_event_hooks_lock_sync = threading.Lock()
_event_hooks_lock_async: asyncio.Lock | None = None


def _get_event_hooks_lock_async() -> asyncio.Lock:
    """Lazy init del lock async (necesita un event loop corriendo al crear)."""
    global _event_hooks_lock_async
    if _event_hooks_lock_async is None:
        _event_hooks_lock_async = asyncio.Lock()
    return _event_hooks_lock_async


def _next_fid() -> str:
    """Devuelve el siguiente ``F-NN`` (NN zero-padded a 2 dígitos)."""
    global _fid_counter
    _fid_counter += 1
    return f"F-{_fid_counter:02d}"


# ---------------------------------------------------------------------------
# ProbeResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Resultado de un probe; agregado al summary final."""

    name: str
    status: str  # "PASS" | "FAIL" | "SKIPPED" | "FINDING"
    detail: str


# ---------------------------------------------------------------------------
# Pattern 1: Bidirectional SafeModel diff (D-HIGY-3/4/5)
# ---------------------------------------------------------------------------
# Helper promovido a ``verification/safemodel_diff.py`` (Phase 5 / D-MATZ-18).
# Se consume vía el barrel: ``from verification import diff_safemodel_bidirectional``.
# La signature es idéntica al inline original Phase 4; la única diferencia
# conductual es duck-typing cross-package (admite higyrus SafeModel y matriz
# _SafeModel sin importar paquetes-cliente).


# ---------------------------------------------------------------------------
# Pattern 2: Live query-string capture sync vs async (D-HIGY-10 #13, HIGY-06)
# ---------------------------------------------------------------------------


def _capture_sync_query_string(
    cuenta: str, fecha_desde: dt.date, fecha_hasta: dt.date
) -> str | None:
    """Captura el query string emitido por el sync client.

    WR-05 (review-04): usa ``httpx.Client.event_hooks`` (API estable y
    pública) en vez de monkey-patch del bound method ``_client.request``.
    Esto elimina los ``# type: ignore[method-assign]`` y desacopla el spy
    del code path de dispatch — cualquier camino de request en httpx
    (``request``, ``send``, batch APIs futuras) dispara el hook.

    Los 4 params opcionales de ``get_movimientos`` se omiten (= None) para
    activar el ``drop_none`` codepath y exponer la deviation conocida en
    ``aio._request``.
    """
    captured: dict[str, str] = {}
    # Phase 11 CR-07: forzar instanciación del http_client lazy ANTES de
    # capturar ``original_hooks`` para no leer ``None.event_hooks`` cuando el
    # helper se llama antes que cualquier endpoint.
    higyrus_client.client._get_default()._ensure_http_client()
    client = higyrus_client.client._client
    assert client is not None  # invariante post-_ensure_http_client

    def _spy(request: httpx.Request) -> None:
        # WR-NEW-01 (review-04 iter-2): el event_hook se dispara para TODO
        # request emitido por el cliente, incluido ``POST /api/login`` cuando
        # ``_ensure_token`` necesita refrescar el token. Filtrar por path
        # del endpoint objetivo evita que el query de ``/api/login`` (vacío)
        # sobrescriba el del GET ``/movimientos`` cuando ese GET falla con
        # error de transporte antes de salir. Sin este filtro,
        # ``probe_parity_sync_async`` puede emitir un FINDING SYNC-ASYNC-DRIFT
        # espurio (``sync_q == ""`` vs ``async_q == "fechaDesde=…"``).
        if not request.url.path.endswith("/movimientos"):
            return
        raw_query = request.url.query
        if isinstance(raw_query, bytes):
            captured["query"] = raw_query.decode("utf-8")
        else:
            captured["query"] = str(raw_query)

    # Phase 11 CR-07: el read-modify-write de ``client.event_hooks`` es la
    # zona de corrupción cross-thread; el lock serializa el ciclo completo
    # (capture-original / install-spy / call / restore-original).
    with _event_hooks_lock_sync:
        original_hooks = client.event_hooks
        # Preserva los hooks pre-existentes en caso de que otro componente los
        # haya registrado (defensivo aunque hoy el client no usa hooks).
        hooks_with_spy: dict[str, list[Any]] = {
            "request": [*original_hooks.get("request", []), _spy],
            "response": list(original_hooks.get("response", [])),
        }
        try:
            client.event_hooks = hooks_with_spy
            higyrus_client.get_movimientos(cuenta, fecha_desde, fecha_hasta)
        except (httpx.HTTPError, HigyrusAPIError, HigyrusAuthError, HigyrusClientError):
            # Phase 11 CR-07 + CR-06: narrowed from bare ``Exception`` to the
            # specific subclasses raised by ``get_movimientos`` (httpx transport
            # + higyrus domain exception hierarchy). Si el server rechaza la
            # cuenta/rango, el hook ya capturó el query string antes de
            # ``_raise_for_response``; si la falla es de transporte antes de la
            # emisión, el dict queda vacío y ``probe_parity_sync_async`` reporta
            # SKIPPED en vez de propagar.
            pass
        finally:
            client.event_hooks = original_hooks
    return captured.get("query")


async def _capture_async_query_string(
    cuenta: str, fecha_desde: dt.date, fecha_hasta: dt.date
) -> str | None:
    """Mirror async del sync — captura del aio surface vía ``event_hooks``.

    WR-05 mirror (review-04): usa ``httpx.AsyncClient.event_hooks`` (request
    hook async-aware) en vez de monkey-patch del bound method. El async
    client es lazy; ``_ensure_http_client`` se invoca para garantizar que
    ``_client is not None`` antes de modificar los hooks.
    """
    await aio._get_default()._ensure_http_client()
    assert aio._client is not None
    client = aio._client
    captured: dict[str, str] = {}

    async def _spy(request: httpx.Request) -> None:
        # WR-NEW-01 mirror (review-04 iter-2): mismo filtrado que el helper
        # sync — evita que el request del login (``POST /api/login``)
        # contamine el query capturado cuando el token está sin cachear
        # antes de la entrada al hook.
        if not request.url.path.endswith("/movimientos"):
            return
        raw_query = request.url.query
        if isinstance(raw_query, bytes):
            captured["query"] = raw_query.decode("utf-8")
        else:
            captured["query"] = str(raw_query)

    # Phase 11 CR-07: asyncio.Lock serializa el read-modify-write de
    # ``client.event_hooks`` cross-coroutine (asyncio.gather x N invocaciones).
    async with _get_event_hooks_lock_async():
        original_hooks = client.event_hooks
        hooks_with_spy: dict[str, list[Any]] = {
            "request": [*original_hooks.get("request", []), _spy],
            "response": list(original_hooks.get("response", [])),
        }
        try:
            client.event_hooks = hooks_with_spy
            await aio.get_movimientos(cuenta, fecha_desde, fecha_hasta)
        except (httpx.HTTPError, HigyrusAPIError, HigyrusAuthError, HigyrusClientError):
            # Phase 11 CR-07 + CR-06: narrowed from bare ``Exception`` to the
            # specific subclasses raised by ``aio.get_movimientos``. Paridad
            # sync↔async preservada en el clause.
            pass
        finally:
            client.event_hooks = original_hooks
    return captured.get("query")


# ---------------------------------------------------------------------------
# Schema snapshot helper (D-HIGY-16 + D-25 no-overwrite-on-drift)
# ---------------------------------------------------------------------------


def _write_or_check_schema(
    func_name: str,
    endpoint_template: str,
    sample_params: dict[str, Any],
    raw_payload: Any,
    base_url: str,
) -> tuple[str, str]:
    """Escribe o compara el schema snapshot. D-25: no-overwrite-on-drift.

    Returns ``(status, detail)`` donde ``status`` es ``"PASS"`` o ``"FINDING"``.
    En PASS, ``detail`` describe la acción ("escrito"/"sin drift"). En FINDING,
    ``detail`` es ``"<fid>|<filename>"``.
    """
    actual_schema = schema_of(raw_payload)
    envelope = {
        "endpoint": endpoint_template,
        "client_function": func_name,
        "captured_at": dt.datetime.now(dt.UTC).isoformat(),
        "base_url": base_url,
        "sample_params": sample_params,
        "schema": actual_schema,
    }
    _SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    file_path = _SCHEMA_FILES[func_name]
    if not file_path.exists():
        file_path.write_text(
            json.dumps(envelope, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return ("PASS", f"escrito {file_path.name}")
    committed = json.loads(file_path.read_text(encoding="utf-8"))
    if committed.get("schema") == actual_schema:
        return ("PASS", f"{file_path.name} sin drift")
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="SHAPE",
        surface="both",
        status="OPEN",
        title=f"Schema drift en {func_name}",
        expected=json.dumps(committed.get("schema"), ensure_ascii=False),
        actual=json.dumps(actual_schema, ensure_ascii=False),
        diff="comparar expected vs actual; NO se sobreescribe baseline (D-25)",
        base_url=base_url,
    )
    return ("FINDING", f"{fid}|{file_path.name}")


# ---------------------------------------------------------------------------
# Probes 1-2: login (HIGY-01)
# ---------------------------------------------------------------------------


def probe_login_sync() -> ProbeResult:
    """Probe 1: ``higyrus_client.login()`` (HIGY-01).

    Setea ``_auth_failed`` global ante CUALQUIER falla de login para activar
    la cascade SKIPPED (D-HIGY-10, Phase 3 D-IOL-3 mirror). Se diferencian
    dos brackets de exception:

    1. ``HigyrusClientError`` — base class del paquete (cubre
       ``HigyrusAuthError`` 401, ``HigyrusAuthorizationError`` 403,
       ``HigyrusRateLimitError`` 429, ``HigyrusAPIError`` cualquier otro
       non-2xx mapeado). Status code disponible en ``exc.status_code``.
    2. ``Exception`` — transporte / network (e.g. ``httpx.ConnectError``,
       ``httpx.TimeoutException``, ``httpx.HTTPStatusError`` para 5xx que
       bypassan ``_raise_for_response``). Sin status_code típico.

    Ambos brackets emiten finding ``AUTH OPEN`` y setean ``_auth_failed``
    para garantizar el contrato cascade SKIPPED del driver. Esto previene
    que un 403/429/500/network failure propague fuera de ``main()`` y
    aborte la driver antes de las 18 líneas + SUMMARY (review-04 CR-02).
    """
    global _auth_failed, _auth_failure_reason
    base_url = higyrus_client.client._get_default()._state.base_url
    try:
        higyrus_client.login()
    except HigyrusClientError as exc:
        _auth_failed = True
        _auth_failure_reason = f"sync login: {type(exc).__name__}: {exc}"
        fid = _next_fid()
        status_code = getattr(exc, "status_code", None)
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title=f"login() sync falló ({type(exc).__name__})",
            expected="login succeeds + cached token",
            actual=repr(exc),
            diff=f"status_code={status_code!r}",
            base_url=base_url,
        )
        return ProbeResult("login_sync", "FINDING", f"{fid} (OPEN)")
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        _auth_failed = True
        _auth_failure_reason = f"sync login: unexpected {type(exc).__name__}: {exc}"
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title=f"login() sync unexpected {type(exc).__name__}",
            expected="login succeeds + cached token",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return ProbeResult("login_sync", "FINDING", f"{fid} (OPEN)")
    return ProbeResult("login_sync", "PASS", "_token cached")


async def probe_login_async() -> ProbeResult:
    """Probe 2: ``await aio.login()`` (HIGY-01).

    Setea el mismo ``_auth_failed`` global compartido con probe 1 (Discretion:
    flag único, no surface-segregated — D-IOL-3 Discretion mirror).

    Catch widening espejo de ``probe_login_sync`` (review-04 CR-02): captura
    ``HigyrusClientError`` (cubre Auth/Authorization/RateLimit/APIError) y
    cualquier otro ``Exception`` (network / transport) para que no propaguen
    fuera de ``asyncio.run()`` y aborten la driver antes del SUMMARY.
    """
    global _auth_failed, _auth_failure_reason
    base_url = aio._get_default()._state.base_url
    try:
        await aio.login()
    except HigyrusClientError as exc:
        _auth_failed = True
        _auth_failure_reason = f"async login: {type(exc).__name__}: {exc}"
        fid = _next_fid()
        status_code = getattr(exc, "status_code", None)
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title=f"login() async falló ({type(exc).__name__})",
            expected="login succeeds + cached token",
            actual=repr(exc),
            diff=f"status_code={status_code!r}",
            base_url=base_url,
        )
        return ProbeResult("login_async", "FINDING", f"{fid} (OPEN)")
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        _auth_failed = True
        _auth_failure_reason = f"async login: unexpected {type(exc).__name__}: {exc}"
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title=f"login() async unexpected {type(exc).__name__}",
            expected="login succeeds + cached token",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return ProbeResult("login_async", "FINDING", f"{fid} (OPEN)")
    return ProbeResult("login_async", "PASS", "ok")


# ---------------------------------------------------------------------------
# Probes 3-4: get_health (HIGY-02)
# ---------------------------------------------------------------------------


def probe_get_health_sync() -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 3: ``higyrus_client.get_health()`` (HIGY-02). WR-03 single call.

    Captura el raw payload vía ``_request`` directo (en vez del wrapper, que
    valida ``isinstance(raw, dict)`` y devuelve el mismo dict pero sin
    diferencia observable) para reuso por probe 15 (schema_snapshot). D-HIGY-2:
    el detail emite ``keys=N`` (conteo), nunca contenido.
    """
    if _auth_failed:
        return (
            ProbeResult("get_health_sync", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = higyrus_client.client._get_default()._state.base_url
    try:
        raw = higyrus_client.client._request("GET", "/api/health")
    except HigyrusAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="get_health_sync recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_health_sync", "FINDING", f"{fid} (OPEN)"), None)
    except HigyrusAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_health_sync recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_health_sync", "FINDING", f"{fid} (OPEN)"), None)
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"get_health_sync unexpected {type(exc).__name__}",
            expected="200 OK + dict",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_health_sync", "FINDING", f"{fid} (OPEN)"), None)
    if not isinstance(raw, dict) or len(raw) < 1:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_health_sync shape inesperada",
            expected="dict con al menos una key",
            actual=f"type={type(raw).__name__} keys={len(raw) if isinstance(raw, dict) else 'n/a'}",
            diff="shape !=dict o dict vacío",
            base_url=base_url,
        )
        return (ProbeResult("get_health_sync", "FINDING", f"{fid} (OPEN)"), None)
    return (ProbeResult("get_health_sync", "PASS", f"keys={len(raw)}"), raw)


async def probe_get_health_async() -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 4: espejo async de probe 3 (HIGY-02)."""
    if _auth_failed:
        return (
            ProbeResult("get_health_async", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = aio._get_default()._state.base_url
    try:
        raw = await aio._request("GET", "/api/health")
    except HigyrusAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title="get_health_async recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_health_async", "FINDING", f"{fid} (OPEN)"), None)
    except HigyrusAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="get_health_async recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_health_async", "FINDING", f"{fid} (OPEN)"), None)
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"get_health_async unexpected {type(exc).__name__}",
            expected="200 OK + dict",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_health_async", "FINDING", f"{fid} (OPEN)"), None)
    if not isinstance(raw, dict) or len(raw) < 1:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="async",
            status="OPEN",
            title="get_health_async shape inesperada",
            expected="dict con al menos una key",
            actual=f"type={type(raw).__name__} keys={len(raw) if isinstance(raw, dict) else 'n/a'}",
            diff="shape !=dict o dict vacío",
            base_url=base_url,
        )
        return (ProbeResult("get_health_async", "FINDING", f"{fid} (OPEN)"), None)
    return (ProbeResult("get_health_async", "PASS", f"keys={len(raw)}"), raw)


# ---------------------------------------------------------------------------
# Probes 5-6: get_listado_cuentas (HIGY-02 + D-HIGY-11)
# ---------------------------------------------------------------------------


def probe_get_listado_cuentas_sync() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 5: ``higyrus_client.get_listado_cuentas(estado="alta")`` (HIGY-02).

    Resuelve ``_resolved_cuenta`` global (D-HIGY-11):

    1. Si ``HIGYRUS_SAMPLE_CUENTA`` está seteado, lo usa como override.
    2. Si no, usa ``cuentas[0].id`` del listado.
    3. Si la lista está vacía, emite finding NO-DATA OPEN y deja
       ``_resolved_cuenta = None`` (downstream cuenta-dependent → SKIPPED).

    Captura el raw payload vía ``_request`` directo para reuso por probe 14
    (diff bidireccional sobre el primer dict del listado) y probe 15.
    """
    global _resolved_cuenta
    if _auth_failed:
        return (
            ProbeResult(
                "get_listado_cuentas_sync",
                "SKIPPED",
                f"auth failed: {_auth_failure_reason}",
            ),
            None,
        )
    base_url = higyrus_client.client._get_default()._state.base_url
    try:
        raw = higyrus_client.client._request(
            "GET",
            "/api/cuentas/listadoCuentas",
            params={"estado": "alta"},
        )
    except HigyrusAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="get_listado_cuentas_sync recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_listado_cuentas_sync", "FINDING", f"{fid} (OPEN)"), None)
    except HigyrusAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_listado_cuentas_sync recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_listado_cuentas_sync", "FINDING", f"{fid} (OPEN)"), None)
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"get_listado_cuentas_sync unexpected {type(exc).__name__}",
            expected="200 OK + list",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_listado_cuentas_sync", "FINDING", f"{fid} (OPEN)"), None)
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_listado_cuentas_sync shape inesperada",
            expected="list[dict] o []",
            actual=f"type={type(raw).__name__}",
            diff="shape !=list",
            base_url=base_url,
        )
        return (ProbeResult("get_listado_cuentas_sync", "FINDING", f"{fid} (OPEN)"), None)
    # Resolución del _resolved_cuenta (D-HIGY-11).
    if _SAMPLE_CUENTA:
        _resolved_cuenta = _SAMPLE_CUENTA
    elif raw:
        first = raw[0]
        if isinstance(first, dict):
            candidate = first.get("id")
            _resolved_cuenta = candidate if isinstance(candidate, str) and candidate else None
        if _resolved_cuenta is None:
            fid = _next_fid()
            # WR-08 (PII discipline D-HIGY-2): NO emitir los key names de la
            # primera cuenta — incluyen potencialmente identificadores como
            # ``titular`` / ``cbu`` / ``cuit`` que ``append_finding`` escribiría
            # verbatim al findings markdown committeado. Reportamos sólo el
            # conteo + tipo para satisfacer la disciplina "COUNTS and SHAPE
            # descriptors, NEVER payload content".
            actual_shape = (
                f"cuentas[0]=<dict, {len(first)} keys hidden>"
                if isinstance(first, dict)
                else f"cuentas[0]=<{type(first).__name__}>"
            )
            append_finding(
                _PKG,
                fid=fid,
                class_="NO-DATA",
                surface="sync",
                status="OPEN",
                title="cuentas[0].id no resoluble",
                expected="cuentas[0]['id'] presente como str no vacío",
                actual=actual_shape,
                diff="no se pudo resolver _resolved_cuenta — downstream SKIPPED",
                base_url=base_url,
            )
            return (
                ProbeResult(
                    "get_listado_cuentas_sync",
                    "FINDING",
                    f"{fid} (OPEN); {len(raw)} cuentas pero sin id",
                ),
                raw,
            )
    else:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="NO-DATA",
            surface="sync",
            status="OPEN",
            title="no cuentas en estado=alta — downstream SKIPPED",
            expected="al menos 1 cuenta en estado=alta",
            actual="lista vacía",
            diff="cuentas[] sin elementos; setear HIGYRUS_SAMPLE_CUENTA o cambiar el filtro",
            base_url=base_url,
        )
        return (
            ProbeResult("get_listado_cuentas_sync", "SKIPPED", "no cuentas"),
            raw,
        )
    return (
        ProbeResult("get_listado_cuentas_sync", "PASS", f"{len(raw)} cuentas"),
        raw,
    )


async def probe_get_listado_cuentas_async() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 6: espejo async (HIGY-02). NO toca ``_resolved_cuenta`` (ya seteado
    por probe 5 sync; si sync skippeó por cascade, el async también)."""
    if _auth_failed:
        return (
            ProbeResult(
                "get_listado_cuentas_async",
                "SKIPPED",
                f"auth failed: {_auth_failure_reason}",
            ),
            None,
        )
    base_url = aio._get_default()._state.base_url
    try:
        raw = await aio._request(
            "GET",
            "/api/cuentas/listadoCuentas",
            params={"estado": "alta"},
        )
    except HigyrusAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title="get_listado_cuentas_async recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_listado_cuentas_async", "FINDING", f"{fid} (OPEN)"), None)
    except HigyrusAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="get_listado_cuentas_async recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_listado_cuentas_async", "FINDING", f"{fid} (OPEN)"), None)
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"get_listado_cuentas_async unexpected {type(exc).__name__}",
            expected="200 OK + list",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_listado_cuentas_async", "FINDING", f"{fid} (OPEN)"), None)
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="async",
            status="OPEN",
            title="get_listado_cuentas_async shape inesperada",
            expected="list[dict] o []",
            actual=f"type={type(raw).__name__}",
            diff="shape !=list",
            base_url=base_url,
        )
        return (ProbeResult("get_listado_cuentas_async", "FINDING", f"{fid} (OPEN)"), None)
    return (
        ProbeResult("get_listado_cuentas_async", "PASS", f"{len(raw)} cuentas"),
        raw,
    )


# ---------------------------------------------------------------------------
# Probes 7-8: get_movimientos (HIGY-02 + HIGY-07)
# ---------------------------------------------------------------------------


def probe_get_movimientos_sync(
    today: dt.date,
    resolved_cuenta: str | None,
) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 7: ``higyrus_client.get_movimientos(cuenta, today-30d, today)`` (HIGY-02 + HIGY-07)."""
    if _auth_failed:
        return (
            ProbeResult(
                "get_movimientos_sync",
                "SKIPPED",
                f"auth failed: {_auth_failure_reason}",
            ),
            None,
        )
    if resolved_cuenta is None:
        return (
            ProbeResult("get_movimientos_sync", "SKIPPED", "no _resolved_cuenta resuelto"),
            None,
        )
    base_url = higyrus_client.client._get_default()._state.base_url
    fecha_desde = today - dt.timedelta(days=30)
    fecha_hasta = today
    try:
        raw = higyrus_client.client._request(
            "GET",
            f"/api/cuentas/{resolved_cuenta}/movimientos",
            params={
                "fechaDesde": format_date(fecha_desde),
                "fechaHasta": format_date(fecha_hasta),
            },
        )
    except HigyrusAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="get_movimientos_sync recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_movimientos_sync", "FINDING", f"{fid} (OPEN)"), None)
    except HigyrusAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_movimientos_sync recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_movimientos_sync", "FINDING", f"{fid} (OPEN)"), None)
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"get_movimientos_sync unexpected {type(exc).__name__}",
            expected="200 OK + list",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_movimientos_sync", "FINDING", f"{fid} (OPEN)"), None)
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_movimientos_sync shape inesperada",
            expected="list[dict] o []",
            actual=f"type={type(raw).__name__}",
            diff="shape !=list",
            base_url=base_url,
        )
        return (ProbeResult("get_movimientos_sync", "FINDING", f"{fid} (OPEN)"), None)
    if not raw:
        return (
            ProbeResult("get_movimientos_sync", "PASS", "0 items — empty path verified"),
            raw,
        )
    return (
        ProbeResult("get_movimientos_sync", "PASS", f"{len(raw)} items"),
        raw,
    )


async def probe_get_movimientos_async(
    today: dt.date,
    resolved_cuenta: str | None,
) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 8: espejo async (HIGY-02 + HIGY-07)."""
    if _auth_failed:
        return (
            ProbeResult(
                "get_movimientos_async",
                "SKIPPED",
                f"auth failed: {_auth_failure_reason}",
            ),
            None,
        )
    if resolved_cuenta is None:
        return (
            ProbeResult("get_movimientos_async", "SKIPPED", "no _resolved_cuenta resuelto"),
            None,
        )
    base_url = aio._get_default()._state.base_url
    fecha_desde = today - dt.timedelta(days=30)
    fecha_hasta = today
    try:
        raw = await aio._request(
            "GET",
            f"/api/cuentas/{resolved_cuenta}/movimientos",
            params={
                "fechaDesde": format_date(fecha_desde),
                "fechaHasta": format_date(fecha_hasta),
            },
        )
    except HigyrusAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title="get_movimientos_async recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_movimientos_async", "FINDING", f"{fid} (OPEN)"), None)
    except HigyrusAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="get_movimientos_async recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_movimientos_async", "FINDING", f"{fid} (OPEN)"), None)
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"get_movimientos_async unexpected {type(exc).__name__}",
            expected="200 OK + list",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_movimientos_async", "FINDING", f"{fid} (OPEN)"), None)
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="async",
            status="OPEN",
            title="get_movimientos_async shape inesperada",
            expected="list[dict] o []",
            actual=f"type={type(raw).__name__}",
            diff="shape !=list",
            base_url=base_url,
        )
        return (ProbeResult("get_movimientos_async", "FINDING", f"{fid} (OPEN)"), None)
    if not raw:
        return (
            ProbeResult("get_movimientos_async", "PASS", "0 items — empty path verified"),
            raw,
        )
    return (
        ProbeResult("get_movimientos_async", "PASS", f"{len(raw)} items"),
        raw,
    )


# ---------------------------------------------------------------------------
# Probes 9-10: get_posicion_valuada (HIGY-02 + posible PARAM)
# ---------------------------------------------------------------------------


def probe_get_posicion_valuada_sync(
    today: dt.date,
    resolved_cuenta: str | None,
) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 9: ``higyrus_client.get_posicion_valuada(...)`` (HIGY-02).

    Si el server rechaza ``tipo_cuenta`` o ``nivel`` con 400, emite finding
    PARAM OPEN con instrucciones para overridear vía
    ``HIGYRUS_SAMPLE_TIPO_CUENTA`` / ``HIGYRUS_SAMPLE_NIVEL`` (D-HIGY-14).
    """
    if _auth_failed:
        return (
            ProbeResult(
                "get_posicion_valuada_sync",
                "SKIPPED",
                f"auth failed: {_auth_failure_reason}",
            ),
            None,
        )
    if resolved_cuenta is None:
        return (
            ProbeResult("get_posicion_valuada_sync", "SKIPPED", "no _resolved_cuenta resuelto"),
            None,
        )
    base_url = higyrus_client.client._get_default()._state.base_url
    try:
        raw = higyrus_client.client._request(
            "GET",
            f"/api/cuentas/{resolved_cuenta}/posicionValuada",
            params={
                "tipoCuenta": _SAMPLE_TIPO_CUENTA,
                "nivel": _SAMPLE_NIVEL,
                "desde": format_date(today),
                "hasta": format_date(today),
            },
        )
    except HigyrusAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="get_posicion_valuada_sync recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_posicion_valuada_sync", "FINDING", f"{fid} (OPEN)"), None)
    except HigyrusAPIError as exc:
        fid = _next_fid()
        # 400 con error que menciona tipo_cuenta/nivel → PARAM, no ERROR-MAP.
        if exc.status_code == 400 and _errors_mention(exc.errors, ("tipo", "nivel")):
            append_finding(
                _PKG,
                fid=fid,
                class_="PARAM",
                surface="sync",
                status="OPEN",
                title="tipo_cuenta o nivel rechazado por server",
                expected="200 OK con tipoCuenta+nivel default (propia/detalle)",
                actual=repr(exc.errors),
                diff="overridear HIGYRUS_SAMPLE_TIPO_CUENTA / HIGYRUS_SAMPLE_NIVEL en .env",
                base_url=base_url,
            )
        else:
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="sync",
                status="OPEN",
                title="get_posicion_valuada_sync recibió APIError inesperado",
                expected="200 OK",
                actual=repr(exc),
                diff=f"status_code={exc.status_code!r}",
                base_url=base_url,
            )
        return (ProbeResult("get_posicion_valuada_sync", "FINDING", f"{fid} (OPEN)"), None)
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"get_posicion_valuada_sync unexpected {type(exc).__name__}",
            expected="200 OK + list",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_posicion_valuada_sync", "FINDING", f"{fid} (OPEN)"), None)
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_posicion_valuada_sync shape inesperada",
            expected="list[dict] o []",
            actual=f"type={type(raw).__name__}",
            diff="shape !=list",
            base_url=base_url,
        )
        return (ProbeResult("get_posicion_valuada_sync", "FINDING", f"{fid} (OPEN)"), None)
    return (
        ProbeResult("get_posicion_valuada_sync", "PASS", f"{len(raw)} items"),
        raw,
    )


async def probe_get_posicion_valuada_async(
    today: dt.date,
    resolved_cuenta: str | None,
) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 10: espejo async (HIGY-02)."""
    if _auth_failed:
        return (
            ProbeResult(
                "get_posicion_valuada_async",
                "SKIPPED",
                f"auth failed: {_auth_failure_reason}",
            ),
            None,
        )
    if resolved_cuenta is None:
        return (
            ProbeResult("get_posicion_valuada_async", "SKIPPED", "no _resolved_cuenta resuelto"),
            None,
        )
    base_url = aio._get_default()._state.base_url
    try:
        raw = await aio._request(
            "GET",
            f"/api/cuentas/{resolved_cuenta}/posicionValuada",
            params={
                "tipoCuenta": _SAMPLE_TIPO_CUENTA,
                "nivel": _SAMPLE_NIVEL,
                "desde": format_date(today),
                "hasta": format_date(today),
            },
        )
    except HigyrusAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title="get_posicion_valuada_async recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_posicion_valuada_async", "FINDING", f"{fid} (OPEN)"), None)
    except HigyrusAPIError as exc:
        fid = _next_fid()
        if exc.status_code == 400 and _errors_mention(exc.errors, ("tipo", "nivel")):
            append_finding(
                _PKG,
                fid=fid,
                class_="PARAM",
                surface="async",
                status="OPEN",
                title="tipo_cuenta o nivel rechazado por server (async)",
                expected="200 OK con tipoCuenta+nivel default (propia/detalle)",
                actual=repr(exc.errors),
                diff="overridear HIGYRUS_SAMPLE_TIPO_CUENTA / HIGYRUS_SAMPLE_NIVEL en .env",
                base_url=base_url,
            )
        else:
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="async",
                status="OPEN",
                title="get_posicion_valuada_async recibió APIError inesperado",
                expected="200 OK",
                actual=repr(exc),
                diff=f"status_code={exc.status_code!r}",
                base_url=base_url,
            )
        return (ProbeResult("get_posicion_valuada_async", "FINDING", f"{fid} (OPEN)"), None)
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"get_posicion_valuada_async unexpected {type(exc).__name__}",
            expected="200 OK + list",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_posicion_valuada_async", "FINDING", f"{fid} (OPEN)"), None)
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="async",
            status="OPEN",
            title="get_posicion_valuada_async shape inesperada",
            expected="list[dict] o []",
            actual=f"type={type(raw).__name__}",
            diff="shape !=list",
            base_url=base_url,
        )
        return (ProbeResult("get_posicion_valuada_async", "FINDING", f"{fid} (OPEN)"), None)
    return (
        ProbeResult("get_posicion_valuada_async", "PASS", f"{len(raw)} items"),
        raw,
    )


def _errors_mention(errors: list[dict[str, Any]] | None, keywords: tuple[str, ...]) -> bool:
    """True si algún ``errors[i].title`` o ``errors[i].detail`` menciona keywords (case-insensitive)."""
    if not errors:
        return False
    for entry in errors:
        if not isinstance(entry, dict):
            continue
        blob = " ".join(
            str(entry.get(k, "")).lower() for k in ("title", "detail", "source", "code")
        )
        if any(kw.lower() in blob for kw in keywords):
            return True
    return False


# ---------------------------------------------------------------------------
# Probes 11-12: get_posiciones (HIGY-02 + HIGY-07)
# ---------------------------------------------------------------------------


def probe_get_posiciones_sync(
    today: dt.date,
    resolved_cuenta: str | None,
) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 11: ``higyrus_client.get_posiciones(cuenta, today)`` (HIGY-02 + HIGY-07)."""
    if _auth_failed:
        return (
            ProbeResult(
                "get_posiciones_sync",
                "SKIPPED",
                f"auth failed: {_auth_failure_reason}",
            ),
            None,
        )
    if resolved_cuenta is None:
        return (
            ProbeResult("get_posiciones_sync", "SKIPPED", "no _resolved_cuenta resuelto"),
            None,
        )
    base_url = higyrus_client.client._get_default()._state.base_url
    try:
        raw = higyrus_client.client._request(
            "GET",
            f"/api/cuentas/{resolved_cuenta}/posiciones",
            params={
                "fecha": format_date(today),
                # CR-04 (review-04): wire format Higyrus es capitalizado
                # (`"True"`/`"False"`, vía ``format_bool``). El driver enviaba
                # ``"false"`` lowercase, contradiciendo la convención que el
                # API pública usa y que ``test_get_posiciones_envia_booleano_capitalizado``
                # locking.
                "incluirParking": format_bool(False),
            },
        )
    except HigyrusAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="get_posiciones_sync recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_posiciones_sync", "FINDING", f"{fid} (OPEN)"), None)
    except HigyrusAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_posiciones_sync recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_posiciones_sync", "FINDING", f"{fid} (OPEN)"), None)
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"get_posiciones_sync unexpected {type(exc).__name__}",
            expected="200 OK + list",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_posiciones_sync", "FINDING", f"{fid} (OPEN)"), None)
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_posiciones_sync shape inesperada",
            expected="list[dict] o []",
            actual=f"type={type(raw).__name__}",
            diff="shape !=list",
            base_url=base_url,
        )
        return (ProbeResult("get_posiciones_sync", "FINDING", f"{fid} (OPEN)"), None)
    if not raw:
        return (
            ProbeResult("get_posiciones_sync", "PASS", "0 items — empty path verified"),
            raw,
        )
    return (
        ProbeResult("get_posiciones_sync", "PASS", f"{len(raw)} items"),
        raw,
    )


async def probe_get_posiciones_async(
    today: dt.date,
    resolved_cuenta: str | None,
) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 12: espejo async (HIGY-02 + HIGY-07)."""
    if _auth_failed:
        return (
            ProbeResult(
                "get_posiciones_async",
                "SKIPPED",
                f"auth failed: {_auth_failure_reason}",
            ),
            None,
        )
    if resolved_cuenta is None:
        return (
            ProbeResult("get_posiciones_async", "SKIPPED", "no _resolved_cuenta resuelto"),
            None,
        )
    base_url = aio._get_default()._state.base_url
    try:
        raw = await aio._request(
            "GET",
            f"/api/cuentas/{resolved_cuenta}/posiciones",
            params={
                "fecha": format_date(today),
                # CR-04 mirror (review-04): wire format Higyrus es capitalizado
                # (`"True"`/`"False"`, vía ``format_bool``). El driver enviaba
                # ``"false"`` lowercase, contradiciendo la convención.
                "incluirParking": format_bool(False),
            },
        )
    except HigyrusAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title="get_posiciones_async recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_posiciones_async", "FINDING", f"{fid} (OPEN)"), None)
    except HigyrusAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="get_posiciones_async recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_posiciones_async", "FINDING", f"{fid} (OPEN)"), None)
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"get_posiciones_async unexpected {type(exc).__name__}",
            expected="200 OK + list",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_posiciones_async", "FINDING", f"{fid} (OPEN)"), None)
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="async",
            status="OPEN",
            title="get_posiciones_async shape inesperada",
            expected="list[dict] o []",
            actual=f"type={type(raw).__name__}",
            diff="shape !=list",
            base_url=base_url,
        )
        return (ProbeResult("get_posiciones_async", "FINDING", f"{fid} (OPEN)"), None)
    if not raw:
        return (
            ProbeResult("get_posiciones_async", "PASS", "0 items — empty path verified"),
            raw,
        )
    return (
        ProbeResult("get_posiciones_async", "PASS", f"{len(raw)} items"),
        raw,
    )


# ---------------------------------------------------------------------------
# Probe 13: parity sync↔async via query string capture (HIGY-06)
# ---------------------------------------------------------------------------


def probe_parity_sync_async(
    today: dt.date,
    resolved_cuenta: str | None,
    async_query: str | None,
) -> ProbeResult:
    """Probe 13: paridad sync↔async vía ``httpx.Request.url.query`` (HIGY-06).

    Captura el query string del sync surface invocando ``get_movimientos`` con
    los 4 params opcionales = None (activa ``drop_none``); compara con el
    ``async_query`` capturado dentro de ``_async_main``. Si difieren, emite
    finding ``SYNC-ASYNC-DRIFT OPEN`` documentando la deviation conocida en
    ``aio._request``.
    """
    if _auth_failed:
        return ProbeResult("parity_sync_async", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    if resolved_cuenta is None:
        return ProbeResult("parity_sync_async", "SKIPPED", "no _resolved_cuenta resuelto")
    base_url = higyrus_client.client._get_default()._state.base_url
    fecha_desde = today - dt.timedelta(days=30)
    fecha_hasta = today
    sync_q = _capture_sync_query_string(resolved_cuenta, fecha_desde, fecha_hasta)
    if sync_q is None and async_query is None:
        return ProbeResult(
            "parity_sync_async",
            "SKIPPED",
            "ningún query capturado (ambos surfaces fallaron)",
        )
    if sync_q != async_query:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SYNC-ASYNC-DRIFT",
            surface="both",
            status="OPEN",
            title="sync y async emiten query strings distintos en get_movimientos",
            expected="sync.query == async.query (drop_none paridad)",
            actual=f"sync={sync_q!r}; async={async_query!r}",
            diff="diferencia en cómo drop_none se aplica en aio._request",
            base_url=base_url,
        )
        return ProbeResult("parity_sync_async", "FINDING", f"{fid} (OPEN)")
    return ProbeResult("parity_sync_async", "PASS", f"query={sync_q!r}")


# ---------------------------------------------------------------------------
# Probe 14: bidirectional SafeModel diff (HIGY-03)
# ---------------------------------------------------------------------------


def probe_field_type_map(
    cuentas_raw: list[dict[str, Any]] | None,
    movimientos_raw: list[dict[str, Any]] | None,
    posiciones_raw: list[dict[str, Any]] | None,
    posicion_valuada_raw: list[dict[str, Any]] | None,
) -> ProbeResult:
    """Probe 14: diff bidireccional Cuenta/Movimiento/Posicion/PosicionValuada (HIGY-03).

    Itera los 4 endpoints con modelos; por cada divergencia
    (``model-only`` o ``wire-only``) emite finding ``SHAPE OPEN``. Recurre en
    nested SafeModels y en ``list[SafeModel]`` (samplea el primer elemento).
    """
    if _auth_failed:
        return ProbeResult("field_type_map", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = higyrus_client.client._get_default()._state.base_url
    targets: list[tuple[str, dict[str, Any] | None, type]] = [
        (
            "cuenta",
            cuentas_raw[0] if cuentas_raw and isinstance(cuentas_raw[0], dict) else None,
            Cuenta,
        ),
        (
            "movimiento",
            movimientos_raw[0]
            if movimientos_raw and isinstance(movimientos_raw[0], dict)
            else None,
            Movimiento,
        ),
        (
            "posicion",
            posiciones_raw[0] if posiciones_raw and isinstance(posiciones_raw[0], dict) else None,
            Posicion,
        ),
        (
            "posicion_valuada",
            posicion_valuada_raw[0]
            if posicion_valuada_raw and isinstance(posicion_valuada_raw[0], dict)
            else None,
            PosicionValuada,
        ),
    ]
    fids: list[str] = []
    for root_name, payload, model_cls in targets:
        if payload is None:
            continue
        for path, direction, key in diff_safemodel_bidirectional(
            payload, model_cls, path=f".{root_name}"
        ):
            fid = _next_fid()
            if direction == "model-only":
                title = f"{path}.{key}: model declara, wire no emite (FALSE PASS riesgo)"
                actual = "<wire ausente; SafeModel sustituye default tipado>"
                diff_detail = (
                    f"key `{key}` ausente en wire bajo `{path}` (model: {model_cls.__name__})"
                )
                expected = "model y wire coinciden en el set de claves"
            else:
                title = f"{path}.{key}: wire emite, model ignora (info)"
                actual = f"key `{key}` presente en wire bajo `{path}`"
                diff_detail = "backend posiblemente agregó campo nuevo; candidato a extender model"
                expected = "model declara el superset del wire"
            append_finding(
                _PKG,
                fid=fid,
                class_="SHAPE",
                surface="both",
                status="OPEN",
                title=title,
                expected=expected,
                actual=actual,
                diff=diff_detail,
                base_url=base_url,
            )
            fids.append(fid)
    if fids:
        return ProbeResult("field_type_map", "FINDING", f"{', '.join(fids)} (OPEN)")
    return ProbeResult("field_type_map", "PASS", "4 endpoints, no field drift")


# ---------------------------------------------------------------------------
# Probe 15: 5 schema snapshots (D-HIGY-16 + D-21 + D-25)
# ---------------------------------------------------------------------------


def probe_schema_snapshot(
    today: dt.date,
    resolved_cuenta: str | None,
    payloads: dict[str, Any],
    base_url: str,
) -> ProbeResult:
    """Probe 15: 5 schema snapshots con envelope D-21 + D-25 no-overwrite (D-HIGY-16)."""
    if _auth_failed:
        return ProbeResult("schema_snapshot", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    fecha_desde = today - dt.timedelta(days=30)
    fecha_hasta = today
    cuenta_param = resolved_cuenta if resolved_cuenta else "<unresolved>"
    targets: list[tuple[str, Any, dict[str, Any]]] = [
        ("get_health", payloads.get("get_health"), {}),
        (
            "get_listado_cuentas",
            payloads.get("get_listado_cuentas"),
            {"estado": "alta"},
        ),
        (
            "get_movimientos",
            payloads.get("get_movimientos"),
            {
                "id_cuenta": cuenta_param,
                "fecha_desde": fecha_desde.isoformat(),
                "fecha_hasta": fecha_hasta.isoformat(),
            },
        ),
        (
            "get_posicion_valuada",
            payloads.get("get_posicion_valuada"),
            {
                "id_cuenta": cuenta_param,
                "tipo_cuenta": _SAMPLE_TIPO_CUENTA,
                "nivel": _SAMPLE_NIVEL,
                "desde": today.isoformat(),
                "hasta": today.isoformat(),
            },
        ),
        (
            "get_posiciones",
            payloads.get("get_posiciones"),
            {"id_cuenta": cuenta_param, "fecha": today.isoformat()},
        ),
    ]
    finding_fids: list[str] = []
    written: list[str] = []
    matched: list[str] = []
    skipped: list[str] = []
    for func_name, payload, sample_params in targets:
        if payload is None:
            skipped.append(func_name)
            continue
        status, detail = _write_or_check_schema(
            func_name,
            _ENDPOINT_TEMPLATES[func_name],
            sample_params,
            payload,
            base_url,
        )
        if status == "FINDING":
            fid, fname = detail.split("|", 1)
            finding_fids.append(f"{fid}/{fname}")
        elif detail.startswith("escrito"):
            written.append(func_name)
        else:
            matched.append(func_name)
    if finding_fids:
        return ProbeResult(
            "schema_snapshot",
            "FINDING",
            f"{', '.join(finding_fids)} (OPEN) — NO sobreescribe",
        )
    return ProbeResult(
        "schema_snapshot",
        "PASS",
        f"written={written!r} matched={matched!r} skipped={skipped!r}",
    )


# ---------------------------------------------------------------------------
# Probes 16-17: errors envelope (HIGY-05 always-on)
# ---------------------------------------------------------------------------


_INVALID_CUENTA_LITERAL = "INVALID-CUENTA-XXXXX"


def probe_errors_envelope_sync(today: dt.date) -> ProbeResult:
    """Probe 16: id_cuenta inválido → envelope ``[{title, detail}]`` (HIGY-05)."""
    if _auth_failed:
        return ProbeResult(
            "errors_envelope_sync",
            "SKIPPED",
            f"auth failed: {_auth_failure_reason}",
        )
    base_url = higyrus_client.client._get_default()._state.base_url
    try:
        higyrus_client.get_movimientos(_INVALID_CUENTA_LITERAL, today, today)
    except HigyrusAPIError as exc:
        envelope_ok = (
            isinstance(exc.errors, list)
            and len(exc.errors) >= 1
            and isinstance(exc.errors[0], dict)
            and "title" in exc.errors[0]
            and "detail" in exc.errors[0]
        )
        if envelope_ok:
            return ProbeResult(
                "errors_envelope_sync",
                "PASS",
                "errors envelope parseado: title+detail presentes",
            )
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="errors envelope mal formado para id_cuenta inválido",
            expected="exc.errors = [{title, detail}, ...]",
            actual=f"exc.errors={exc.errors!r}",
            diff="title o detail ausentes en exc.errors[0]",
            base_url=base_url,
        )
        return ProbeResult("errors_envelope_sync", "FINDING", f"{fid} (OPEN)")
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"errors_envelope_sync unexpected {type(exc).__name__}",
            expected="HigyrusAPIError con envelope errors",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return ProbeResult("errors_envelope_sync", "FINDING", f"{fid} (OPEN)")
    # else: 200 OK con id_cuenta inválido — wire raro.
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="ERROR-MAP",
        surface="sync",
        status="OPEN",
        title="200 OK con id_cuenta inválido",
        expected="HigyrusAPIError (4xx) con envelope errors",
        actual="200 OK",
        diff="el server aceptó un id_cuenta sintéticamente inválido",
        base_url=base_url,
    )
    return ProbeResult("errors_envelope_sync", "FINDING", f"{fid} (OPEN)")


async def probe_errors_envelope_async(today: dt.date) -> ProbeResult:
    """Probe 17: espejo async de probe 16 (HIGY-05)."""
    if _auth_failed:
        return ProbeResult(
            "errors_envelope_async",
            "SKIPPED",
            f"auth failed: {_auth_failure_reason}",
        )
    base_url = aio._get_default()._state.base_url
    try:
        await aio.get_movimientos(_INVALID_CUENTA_LITERAL, today, today)
    except HigyrusAPIError as exc:
        envelope_ok = (
            isinstance(exc.errors, list)
            and len(exc.errors) >= 1
            and isinstance(exc.errors[0], dict)
            and "title" in exc.errors[0]
            and "detail" in exc.errors[0]
        )
        if envelope_ok:
            return ProbeResult(
                "errors_envelope_async",
                "PASS",
                "errors envelope parseado: title+detail presentes",
            )
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="errors envelope mal formado para id_cuenta inválido (async)",
            expected="exc.errors = [{title, detail}, ...]",
            actual=f"exc.errors={exc.errors!r}",
            diff="title o detail ausentes en exc.errors[0]",
            base_url=base_url,
        )
        return ProbeResult("errors_envelope_async", "FINDING", f"{fid} (OPEN)")
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"errors_envelope_async unexpected {type(exc).__name__}",
            expected="HigyrusAPIError con envelope errors",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return ProbeResult("errors_envelope_async", "FINDING", f"{fid} (OPEN)")
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="ERROR-MAP",
        surface="async",
        status="OPEN",
        title="200 OK con id_cuenta inválido (async)",
        expected="HigyrusAPIError (4xx) con envelope errors",
        actual="200 OK",
        diff="el server aceptó un id_cuenta sintéticamente inválido",
        base_url=base_url,
    )
    return ProbeResult("errors_envelope_async", "FINDING", f"{fid} (OPEN)")


# ---------------------------------------------------------------------------
# Probe 18: opt-in 401 (HIGY-AUTH, D-HIGY-10 #18 + T-4-07)
# ---------------------------------------------------------------------------


def probe_auth_401() -> ProbeResult:
    """Probe 18: 401 con credenciales inválidas (HIGY-AUTH).

    Opt-in vía ``VERIFY_HIGYRUS_BAD_CREDS=1``. Single-shot, sin retry, sin
    sleep. ``try/finally`` SIEMPRE restaura ``HIGYRUS_PASSWORD`` original vía
    ``configure(password=...)``.

    Deviation explícita vs Phase 3 IOL CR-03: Higyrus NO tiene
    ``_refresh_token`` a preservar; ``configure()`` (que resetea ``_token`` y
    ``_token_ts``) es simétrico y seguro. Los secrets snapshots de main()
    capturan los tokens POR VALOR antes de invocar este probe, por lo que el
    ``configure(password=...)`` que nulifica ``_token`` no impacta la lista
    de redacción.
    """
    if os.getenv("VERIFY_HIGYRUS_BAD_CREDS") != "1":
        return ProbeResult("auth_401", "SKIPPED", "(opt-in via VERIFY_HIGYRUS_BAD_CREDS=1)")
    if _auth_failed:
        return ProbeResult("auth_401", "SKIPPED", f"auth failed: {_auth_failure_reason}")

    base_url = higyrus_client.client._get_default()._state.base_url
    original_password = os.getenv("HIGYRUS_PASSWORD", "")
    bad_password = original_password + "_INVALID"
    try:
        higyrus_client.configure(password=bad_password)
        try:
            higyrus_client.login()
        except HigyrusAuthError as exc:
            status_code = exc.status_code
            if status_code == 401:
                # HARN-08 (Phase 11): idempotent_by_title=True para evitar que
                # el terminal EXPECTED se duplique cross-run con cada
                # _next_fid() distinto — content-addressed dedupe by title.
                fid = _next_fid()
                append_finding(
                    _PKG,
                    fid=fid,
                    class_="AUTH",
                    surface="sync",
                    status="EXPECTED",
                    title="credenciales inválidas reciben 401",
                    expected="401 con password=HIGYRUS_PASSWORD+_INVALID",
                    actual="401",
                    diff="ninguno; comportamiento esperado",
                    base_url=base_url,
                    idempotent_by_title=True,
                )
                return ProbeResult("auth_401", "FINDING", f"{fid} (EXPECTED)")
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="AUTH",
                surface="sync",
                status="OPEN",
                title="credenciales inválidas recibieron status inesperado",
                expected="401",
                actual=f"status_code={status_code!r}",
                diff=f"AuthError con status_code={status_code!r}",
                base_url=base_url,
            )
            return ProbeResult("auth_401", "FINDING", f"{fid} (OPEN)")
        except _RESIDUAL_PROBE_EXCEPTIONS as exc:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="AUTH",
                surface="sync",
                status="OPEN",
                title="credenciales inválidas produjeron error inesperado",
                expected="401 (HigyrusAuthError)",
                actual=repr(exc),
                diff=f"type={type(exc).__name__}",
                base_url=base_url,
            )
            return ProbeResult("auth_401", "FINDING", f"{fid} (OPEN)")
        # Sin excepción → defensa relajada (200 OK con bad creds).
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="credenciales inválidas NO recibieron 401",
            expected="401 con password=HIGYRUS_PASSWORD+_INVALID",
            actual="200 OK (defensa relajada)",
            diff="el server aceptó un password inválido",
            base_url=base_url,
        )
        return ProbeResult("auth_401", "FINDING", f"{fid} (OPEN)")
    finally:
        # T-4-07 mitigation: SIEMPRE restaurar el password original.
        higyrus_client.configure(password=original_password)


# ---------------------------------------------------------------------------
# Phase 9 BUG-04 (D-08, D-10): multi-account iteration probe
# ---------------------------------------------------------------------------


def probe_multi_account_iteration() -> ProbeResult:
    """Probe BUG-04 (D-08 per-call only): itera ≥2 cuentas via per-call kwarg.

    Source order:
    1. ``HIGYRUS_SAMPLE_CUENTAS`` env var (CSV ``"A,B"``) — operator override.
    2. ``get_listado_cuentas(estado="alta")`` live — primeras 2 ids.
    3. SKIPPED si <2 cuentas disponibles.

    Por cada cuenta corre ``get_movimientos(id_cuenta=acct, fecha_desde=today,
    fecha_hasta=today)``. PASS si ambas calls succeed; FINDING + ``append_finding``
    on first ``HigyrusAPIError``; SKIPPED si la cascade upstream (auth, fuente
    cuentas <2) impide ejercerlo.
    """
    if _auth_failed:
        return ProbeResult(
            "multi_account_iteration",
            "SKIPPED",
            f"auth failed: {_auth_failure_reason}",
        )
    base_url = higyrus_client.client._get_default()._state.base_url
    # Source 1: env var override (CSV).
    if _SAMPLE_CUENTAS_CSV.strip():
        cuentas = [c.strip() for c in _SAMPLE_CUENTAS_CSV.split(",") if c.strip()]
    else:
        # Source 2: live get_listado_cuentas() — si non-empty, primeras 2.
        try:
            live = higyrus_client.get_listado_cuentas(estado="alta")
        except _RESIDUAL_PROBE_EXCEPTIONS as exc:
            return ProbeResult(
                "multi_account_iteration",
                "SKIPPED",
                f"listado_cuentas failed: {exc!r}",
            )
        cuentas = [c.id for c in live[:2]] if len(live) >= 2 else []
    if len(cuentas) < 2:
        return ProbeResult(
            "multi_account_iteration",
            "SKIPPED",
            "need >=2 cuentas; set HIGYRUS_SAMPLE_CUENTAS=A,B",
        )
    today = dt.date.today()
    for acct in cuentas[:2]:
        try:
            higyrus_client.get_movimientos(
                id_cuenta=acct,
                fecha_desde=today,
                fecha_hasta=today,
            )
        except HigyrusAPIError as exc:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="sync",
                status="OPEN",
                title=f"multi_account: get_movimientos({acct})",
                expected="200 OK",
                actual=repr(exc),
                diff=f"status={exc.status_code!r}",
                base_url=base_url,
            )
            return ProbeResult(
                "multi_account_iteration",
                "FINDING",
                f"{fid} (OPEN)",
            )
    return ProbeResult(
        "multi_account_iteration",
        "PASS",
        f"iterated {len(cuentas[:2])} cuentas successfully",
    )


# ---------------------------------------------------------------------------
# Async wrapper — un único asyncio.run (D-HIGY-13, IN-03 Phase 2 mirror)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _AsyncResults:
    """Empaqueta los resultados del único ``asyncio.run(_async_main(...))``."""

    login: ProbeResult
    health: ProbeResult
    health_raw: dict[str, Any] | None
    listado_cuentas: ProbeResult
    listado_cuentas_raw: list[dict[str, Any]] | None
    movimientos: ProbeResult
    posicion_valuada: ProbeResult
    posiciones: ProbeResult
    errors_envelope: ProbeResult
    async_query: str | None
    async_token_snapshot: str | None


async def _async_main(
    today: dt.date,
    resolved_cuenta: str | None,
) -> _AsyncResults:
    """Compone los probes async + el async parity capture en un único event loop.

    D-HIGY-13 + IN-03 Phase 2 mirror: un único ``asyncio.run`` + ``aclose``
    envuelto en ``contextlib.suppress(Exception)``.

    El ``async_token_snapshot`` se captura POR VALOR inmediatamente tras
    ``probe_login_async`` exitoso para que ``probe_auth_401`` (que sucede
    DESPUÉS del ``asyncio.run`` y resetea ``_token`` vía ``configure``) no
    nulifique el snapshot en la lista de redacción de main().

    WR-04 (review-04): TODOS los locals referenciados por ``_AsyncResults``
    se inicializan a sentinels SKIPPED ANTES del ``try:`` para que un
    refactor futuro que mueva el ``return`` después del ``finally`` (o que
    falle parcialmente y necesite devolver resultados parciales) no rompa
    con ``UnboundLocalError``. Mirror defensivo del patrón del sync side
    en ``main()``.
    """

    def _skipped(name: str) -> ProbeResult:
        return ProbeResult(name, "SKIPPED", "(not executed)")

    result_login: ProbeResult = _skipped("login_async")
    async_token_snapshot: str | None = None
    result_health: ProbeResult = _skipped("get_health_async")
    health_raw: dict[str, Any] | None = None
    result_listado: ProbeResult = _skipped("get_listado_cuentas_async")
    listado_raw: list[dict[str, Any]] | None = None
    result_movs: ProbeResult = _skipped("get_movimientos_async")
    result_pv: ProbeResult = _skipped("get_posicion_valuada_async")
    result_pos: ProbeResult = _skipped("get_posiciones_async")
    result_errors: ProbeResult = _skipped("errors_envelope_async")
    async_query: str | None = None

    try:
        result_login = await probe_login_async()
        async_token_snapshot = aio._token if result_login.status == "PASS" else None

        result_health, health_raw = await probe_get_health_async()
        result_listado, listado_raw = await probe_get_listado_cuentas_async()
        result_movs, _movs_raw = await probe_get_movimientos_async(today, resolved_cuenta)
        result_pv, _pv_raw = await probe_get_posicion_valuada_async(today, resolved_cuenta)
        result_pos, _pos_raw = await probe_get_posiciones_async(today, resolved_cuenta)

        # Async parity capture for probe 13 (params optional = None → drop_none).
        if not _auth_failed and resolved_cuenta is not None:
            fecha_desde = today - dt.timedelta(days=30)
            fecha_hasta = today
            try:
                async_query = await _capture_async_query_string(
                    resolved_cuenta, fecha_desde, fecha_hasta
                )
            except _RESIDUAL_PROBE_EXCEPTIONS:
                async_query = None

        result_errors = await probe_errors_envelope_async(today)
    finally:
        with contextlib.suppress(*_RESIDUAL_PROBE_EXCEPTIONS):
            await aio.aclose()
    return _AsyncResults(
        login=result_login,
        health=result_health,
        health_raw=health_raw,
        listado_cuentas=result_listado,
        listado_cuentas_raw=listado_raw,
        movimientos=result_movs,
        posicion_valuada=result_pv,
        posiciones=result_pos,
        errors_envelope=result_errors,
        async_query=async_query,
        async_token_snapshot=async_token_snapshot,
    )


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def main() -> None:
    """Orquesta los 18 probes y emite las 18 líneas + SUMMARY al final.

    Execution order (D-HIGY-13 + D-HIGY-11 enforce):

    (a) probe_login_sync                       — captura _sync_token_snapshot POR VALOR si éxito
    (b) probe_get_health_sync                  — payload raw para probe 14/15
    (c) probe_get_listado_cuentas_sync         — RESUELVE _resolved_cuenta global
    (d) probe_get_movimientos_sync             — usa _resolved_cuenta
    (e) probe_get_posicion_valuada_sync        — usa _resolved_cuenta
    (f) probe_get_posiciones_sync              — usa _resolved_cuenta
    (g) asyncio.run(_async_main(today, resolved_cuenta=_resolved_cuenta))
        consolida: login_async (+_async_token_snapshot POR VALOR), health_async,
        listado_cuentas_async, movimientos_async, posicion_valuada_async,
        posiciones_async, async parity capture, errors_envelope_async.
    (h) probe_parity_sync_async                — usa async_query del tuple-return de _async_main
    (i) probe_field_type_map                   — diff sobre raw sync payloads
    (j) probe_schema_snapshot                  — 5 snapshots
    (k) probe_errors_envelope_sync             — always-on
    (l) probe_auth_401                         — opt-in single-shot, ÚLTIMO

    Presentation order (D-HIGY-10): tras colectar todos los ProbeResult, se
    imprimen las 18 líneas ``PROBE <name>: <status> <detail>`` en el orden
    declarado por ``_D_HIGY_10_ORDER`` (NO en el orden de ejecución).
    """
    if not require_env(_PKG, ["HIGYRUS_USER", "HIGYRUS_PASSWORD", "HIGYRUS_BASE_URL"]):
        # HARN-01: exit limpio sin interrumpir (require_env ya imprimió SKIPPED).
        return

    today = dt.date.today()

    # D-03 mirror: idempotente — no-op si el archivo ya existe.
    write_findings(_PKG)

    # D-HIGY-15 initial secrets: HIGYRUS_USER + HIGYRUS_PASSWORD del env.
    # WR-03 (review-04): el password se redacta SIEMPRE — sin threshold —
    # porque un short-but-real password es el peor caso para dejar sin
    # mascarar (puede aparecer en repr(exc) de HigyrusAuthError con echo
    # base64 de las credenciales). El username conserva ``len(v) >= 4``
    # para evitar redactar substrings demasiado cortos que matcheen
    # ruido en el output (e.g. "ok"). Si HIGYRUS_USER queda excluido,
    # emite warning a stderr para que el operador detecte el gap.
    _user_env = os.getenv("HIGYRUS_USER", "")
    _password_env = os.getenv("HIGYRUS_PASSWORD", "")
    secrets: list[str] = []
    if _password_env:
        secrets.append(_password_env)
    if _user_env and len(_user_env) >= 4:
        secrets.append(_user_env)
    elif _user_env:
        print(
            f"WARNING: HIGYRUS_USER='{_user_env[:1]}…' too short to redact; "
            "check stdout discipline",
            file=sys.stderr,
        )

    results: dict[str, ProbeResult] = {}
    payloads: dict[str, Any] = {}

    # (a) Probe 1 sync (login_sync) — puede setear _auth_failed.
    results["login_sync"] = probe_login_sync()
    _sync_token_snapshot = (
        higyrus_client.client._token if results["login_sync"].status == "PASS" else None
    )
    if _sync_token_snapshot:
        secrets.append(_sync_token_snapshot)

    # (b) Probe 3 sync (get_health_sync).
    result_health_sync, health_raw = probe_get_health_sync()
    results["get_health_sync"] = result_health_sync
    if health_raw is not None:
        payloads["get_health"] = health_raw

    # (c) Probe 5 sync (get_listado_cuentas_sync) — RESOLVE _resolved_cuenta.
    result_listado_sync, listado_raw = probe_get_listado_cuentas_sync()
    results["get_listado_cuentas_sync"] = result_listado_sync
    if listado_raw is not None:
        payloads["get_listado_cuentas"] = listado_raw

    # (d) Probe 7 sync (get_movimientos_sync).
    result_movs_sync, movs_raw = probe_get_movimientos_sync(today, _resolved_cuenta)
    results["get_movimientos_sync"] = result_movs_sync
    if movs_raw is not None:
        payloads["get_movimientos"] = movs_raw

    # (e) Probe 9 sync (get_posicion_valuada_sync).
    result_pv_sync, pv_raw = probe_get_posicion_valuada_sync(today, _resolved_cuenta)
    results["get_posicion_valuada_sync"] = result_pv_sync
    if pv_raw is not None:
        payloads["get_posicion_valuada"] = pv_raw

    # (f) Probe 11 sync (get_posiciones_sync).
    result_pos_sync, pos_raw = probe_get_posiciones_sync(today, _resolved_cuenta)
    results["get_posiciones_sync"] = result_pos_sync
    if pos_raw is not None:
        payloads["get_posiciones"] = pos_raw

    # (g) Single asyncio.run(_async_main(...)) — D-HIGY-13.
    async_results = asyncio.run(_async_main(today, resolved_cuenta=_resolved_cuenta))
    results["login_async"] = async_results.login
    results["get_health_async"] = async_results.health
    results["get_listado_cuentas_async"] = async_results.listado_cuentas
    results["get_movimientos_async"] = async_results.movimientos
    results["get_posicion_valuada_async"] = async_results.posicion_valuada
    results["get_posiciones_async"] = async_results.posiciones
    results["errors_envelope_async"] = async_results.errors_envelope

    # Async token snapshot — captured POR VALOR dentro de _async_main.
    if async_results.async_token_snapshot:
        secrets.append(async_results.async_token_snapshot)

    # (h) Probe 13 (parity_sync_async).
    results["parity_sync_async"] = probe_parity_sync_async(
        today, _resolved_cuenta, async_results.async_query
    )

    # (i) Probe 14 (field_type_map) — diff sobre raw sync payloads.
    results["field_type_map"] = probe_field_type_map(
        payloads.get("get_listado_cuentas"),
        payloads.get("get_movimientos"),
        payloads.get("get_posiciones"),
        payloads.get("get_posicion_valuada"),
    )

    # (j) Probe 15 (schema_snapshot) — 5 snapshots.
    base_url = higyrus_client.client._get_default()._state.base_url
    results["schema_snapshot"] = probe_schema_snapshot(today, _resolved_cuenta, payloads, base_url)

    # (k) Probe 16 (errors_envelope_sync) — always-on.
    results["errors_envelope_sync"] = probe_errors_envelope_sync(today)

    # (k.5) Phase 9 BUG-04 (D-08, D-10): multi-account iteration probe.
    # Corre después de get_listado_cuentas + get_movimientos (sync + async) para
    # que _resolved_cuenta esté disponible si el operator quiere comparar; el
    # propio probe puede consumir get_listado_cuentas o el override CSV.
    results["multi_account_iteration"] = probe_multi_account_iteration()

    # (l) Probe 18 (auth_401) — opt-in, single-shot, ÚLTIMO.
    results["auth_401"] = probe_auth_401()

    # Presentation order: imprimir las 18 líneas en orden D-HIGY-10 declarado.
    for name in _D_HIGY_10_ORDER:
        r = results.get(name)
        if r is None:
            # Defensa: si por algún bug un probe no quedó registrado, marcar SKIPPED
            # para no romper el conteo del summary.
            r = ProbeResult(name, "SKIPPED", "(no recolectado)")
        safe_print(f"PROBE {r.name}: {r.status} {r.detail}".rstrip(), secrets=secrets)

    # Summary final verbatim D-02.
    collected = [results.get(name) for name in _D_HIGY_10_ORDER]
    n_pass = sum(1 for r in collected if r is not None and r.status == "PASS")
    n_fail = sum(1 for r in collected if r is not None and r.status == "FAIL")
    n_skip = sum(1 for r in collected if r is not None and r.status == "SKIPPED")
    n_find = sum(1 for r in collected if r is not None and r.status == "FINDING")
    safe_print(
        f"SUMMARY: PASS={n_pass} FAIL={n_fail} SKIPPED={n_skip} FINDING={n_find}",
        secrets=secrets,
    )


if __name__ == "__main__":
    main()
