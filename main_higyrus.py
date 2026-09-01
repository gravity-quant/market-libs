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
import hashlib
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
    divergence_capture,
    endpoint_scope,
    probe_context,
    require_env,
    safe_print,
    schema_of,
    write_findings,
    write_run_evidence,
)
from verification.findings import max_existing_fid

import higyrus_client
from higyrus_client import (
    AsyncClient,
    Client,
    HigyrusAPIError,
    HigyrusAuthError,
    HigyrusClientError,
    HigyrusDecodeError,
)
from higyrus_client._core import RequestSpec, raise_for_response
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

# Phase 33 (LIVE-TYP-01): flag del segundo pase. El runner de dos pases corre el
# driver una vez en modo observable (censo completo) y otra con
# ``MARKET_LIBS_STRICT_DECODE=1``, que prueba que el raise de modo estricto
# efectivamente dispara. Viaja como kwarg del constructor para NO agregar un
# segundo sitio de construcción: ``test_main_higyrus_uses_single_client_instance``
# asserta ``1 <= ctor_calls <= 2`` por AST.
_STRICT: bool = os.getenv("MARKET_LIBS_STRICT_DECODE") == "1"

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
# NO arranca en 0 en el run real: ``_seed_fid_counter()`` lo sube al máximo fid
# ya registrado antes del primer probe (D-16/D-24). Sin ese seed, cada finding
# nuevo re-emitiría un fid ya ocupado — y contra el archivo committeado, que hoy
# lleva F-01 y F-02, eso significa reescribir el triage del operador en un caso
# y perder el finding en silencio en el otro, mientras el driver sigue
# reportando ``FINDING=N``.
_fid_counter: int = 0

# D-HIGY-10 cascade SKIPPED (Phase 3 D-IOL-3 mirror): flag único compartido
# entre surfaces sync y async. Si CUALQUIER login falla, todos los downstream
# emiten SKIPPED.
_auth_failed: bool = False
_auth_failure_reason: str = ""

# Phase 39 D-01: el vendor no está *rechazando* — no está *ahí*. Un
# ``httpx.ConnectError`` de ``login()`` (caso DNS ``gaierror``) no es un hallazgo
# sobre el cliente: es la ausencia de la contraparte contra la que se verifica.
# Hasta D-01 caía en ``_RESIDUAL_PROBE_EXCEPTIONS`` (que incluye
# ``httpx.HTTPError``, superclase de ``ConnectError``) y se escribía como finding
# ``AUTH OPEN`` en un ledger versionado, mientras el driver salía 0 sin decir
# nada: ``main_verify.py`` lo clasificaba ``RAN``. Falso limpio en los dos
# sentidos. Con estas globales, ``main()`` corta temprano y lo dice.
_vendor_unreachable: bool = False
_vendor_unreachable_reason: str = ""

# Línea verbatim que el driver emite a STDOUT cuando el vendor no es alcanzable.
# Literal a propósito: ``main_verify.py`` clasifica por la forma
# ``^SKIPPED \S.*:`` (los dos puntos son load-bearing) y no interpolar el
# hostname ni la base URL es lo que evita que el veredicto filtre el dato de
# entrada (T-39-04).
_VENDOR_UNREACHABLE_SKIP_LINE = (
    "SKIPPED higyrus-client: vendor host unreachable (DNS) — LIVE-HIGY-42"
)

# Causa medida que viaja en el ``ProbeResult`` del login (no en la línea SKIPPED).
_VENDOR_UNREACHABLE_DETAIL = "vendor host unreachable (DNS)"

# Causa medida + destino nombrado que viaja en el sobre de evidencia de corrida
# (Phase 39 D-09). Es la línea SKIPPED sin su prefijo de veredicto: ni hostname
# ni base URL, igual que ella (T-39-04/T-39-10).
_VENDOR_UNREACHABLE_EVIDENCE = "vendor host unreachable (DNS) — LIVE-HIGY-42"

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


def _seed_fid_counter() -> None:
    """Sube ``_fid_counter`` al máximo fid ya registrado en el findings file (D-16/D-24).

    Debe correr DESPUÉS de ``write_findings(_PKG)`` (el bootstrap del archivo) y
    ANTES del primer probe, para que todo fid emitido en este run caiga por
    encima de lo ya escrito y realmente aterrice en el archivo.

    La falla que previene tiene dos caras, y ambas son observables hoy contra
    ``.planning/verification/higyrus-client-findings.md``:

    - un fid re-emitido cuyo status registrado ES ``OPEN`` NO dispara el
      short-circuit de :func:`verification.findings.append_finding`: el bloque de
      detalle se **reescribe en el lugar** con contenido ajeno y el triage que el
      operador arrastró desde fases anteriores se pierde;
    - un fid re-emitido cuyo status registrado NO es ``OPEN`` sí dispara el
      short-circuit: el write se vuelve un no-op **silencioso** mientras
      ``main()`` igual lo cuenta en ``FINDING=N`` y el ``SUMMARY`` reporta éxito.
      El run pierde su entregable creyendo que funcionó. Los DOS fids
      committeados de higyrus están en este caso: ``F-01`` (``EXPECTED``) y
      ``F-02`` (``NO-FIX``), ambos terminales.

    Misma forma que ``main_iol.py::_seed_fid_counter`` y
    ``main_market_data.py::_seed_fid_counter``.
    """
    global _fid_counter
    _fid_counter = max_existing_fid(_PKG)


def _next_fid() -> str:
    """Devuelve el siguiente ``F-NN`` (NN zero-padded a 2 dígitos)."""
    global _fid_counter
    _fid_counter += 1
    return f"F-{_fid_counter:02d}"


# Guarda de dedupe de schema drift (HARN-01 / D-01 ENMENDADA). Estado POR
# PROCESO: el colapso es intra-run, así que una divergencia sin arreglar sigue
# escribiendo un bloque nuevo en la corrida siguiente (verboso, nunca lossy). La
# clave es ``(identidad del baseline, digest del contenido de la divergencia)`` y
# NO incluye la superficie: dentro de un proceso cada par función-superficie se
# visita una sola vez, así que una clave con ``surface`` no podría colapsar nada.
# Copia local deliberada del artefacto de ``main_market_data.py``: ``CLAUDE.md``
# prohíbe código compartido entre unidades y ``verification/findings.py`` está
# vedado como sitio de estado por ser append-only por contrato.
_seen_drift_keys: set[tuple[str, str]] = set()


def _drift_digest(payload: object) -> str:
    """Digest determinístico del contenido de una divergencia (clave de dedupe).

    ``sort_keys`` lo hace estable frente al orden de iteración de los dicts.
    ``default=str`` garantiza que este camino NUNCA levante una excepción nueva:
    el contrato de la ladder D-09 es que una divergencia de forma degrada a
    finding y jamás a crash.
    """
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _shape_probe_result(probe_name: str, surface: str, exc: BaseException) -> ProbeResult:
    """Fallback de ``probe_context`` ante un ``HigyrusDecodeError`` (D-07).

    El finding ``SHAPE`` YA lo escribió :class:`verification.divergences.DivergenceHandler`
    a partir del record de divergencia que ``_decode`` emitió justo antes de
    levantar. Este helper NO escribe un segundo finding: mintear uno acá
    duplicaría la divergencia bajo otro título y rompería el ``idempotent_by_title``
    del lock 10. Sólo traduce la excepción al 2-tuple que el driver espera.

    Lee ÚNICAMENTE ``model`` / ``field_path`` / ``declared_type`` /
    ``observed_type`` — los cuatro atributos certificados type-and-path-only por
    T-29-36 — y nada más de la excepción (T-33-07: nada de credenciales ni de
    valores del wire puede filtrarse a stdout ni a un artefacto committeado).
    """
    name = probe_name.removeprefix("probe_")
    if isinstance(exc, HigyrusDecodeError):
        detail = (
            f"SHAPE [{surface}] {exc.model}{exc.field_path} "
            f"declared={exc.declared_type} observed={exc.observed_type}"
        )
    else:
        detail = f"SHAPE [{surface}] {type(exc).__name__}"
    return ProbeResult(name, "FINDING", detail)


def _shape_probe_result_pair(
    probe_name: str, surface: str, exc: BaseException
) -> tuple[ProbeResult, None]:
    """Variante 2-tuple de :func:`_shape_probe_result` para los probes con payload.

    higyrus tiene DOS formas canónicas de retorno de probe, no una: los 8 probes
    que alimentan ``payloads[...]`` en ``main()`` (health, listado_cuentas,
    movimientos, posicion_valuada, posiciones — sync y async) devuelven
    ``(ProbeResult, raw_payload | None)``, mientras que login, parity,
    field_type_map, schema_snapshot, errors_envelope, auth_401 y
    multi_account_iteration devuelven un ``ProbeResult`` pelado. Un único
    fallback con forma de 2-tuple haría que
    ``results["auth_401"] = probe_auth_401(client)`` metiera una tupla en un
    ``dict[str, ProbeResult]`` y el ``r.status`` del loop de impresión explotara
    con ``AttributeError`` — bajo modo estricto, exactamente el crash que este
    plan existe para eliminar. Mismo par de helpers que ``main_matriz.py``.
    """
    return (_shape_probe_result(probe_name, surface, exc), None)


def _raw_request_sync(
    client: Client,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """Raw request sobre el ``Client`` threadeado, semántica del shim legacy.

    Replica byte-por-byte el comportamiento del antiguo
    ``higyrus_client.client._request(method, path, params=...)`` (que el driver
    usaba para capturar el raw payload): construye un ``RequestSpec``, llama al
    ``Client._request`` de instancia, levanta vía ``raise_for_response`` ante
    non-2xx, y devuelve ``None`` en 204/empty o ``resp.json()`` en caso éxito.
    Necesario porque ``Client._request`` (D-03) devuelve el ``httpx.Response``
    crudo SIN levantar — el shim module-level sí levantaba.
    """
    spec = RequestSpec(method=method, path=path, params=params)
    resp = client._request(spec)
    if not resp.is_success:
        raise_for_response(resp)
    if resp.status_code == 204 or not resp.content:
        return None
    body: dict[str, Any] | list[Any] = resp.json()
    return body


async def _raw_request_async(
    aclient: AsyncClient,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """Mirror async de ``_raw_request_sync`` sobre el ``AsyncClient`` threadeado."""
    spec = RequestSpec(method=method, path=path, params=params)
    resp = await aclient._request(spec)
    if not resp.is_success:
        raise_for_response(resp)
    if resp.status_code == 204 or not resp.content:
        return None
    body: dict[str, Any] | list[Any] = resp.json()
    return body


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
    client: Client, cuenta: str, fecha_desde: dt.date, fecha_hasta: dt.date
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
    http_client = client._ensure_http_client()

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
        original_hooks = http_client.event_hooks
        # Preserva los hooks pre-existentes en caso de que otro componente los
        # haya registrado (defensivo aunque hoy el client no usa hooks).
        hooks_with_spy: dict[str, list[Any]] = {
            "request": [*original_hooks.get("request", []), _spy],
            "response": list(original_hooks.get("response", [])),
        }
        try:
            http_client.event_hooks = hooks_with_spy
            client.get_movimientos(cuenta, fecha_desde, fecha_hasta)
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
            http_client.event_hooks = original_hooks
    return captured.get("query")


async def _capture_async_query_string(
    aclient: AsyncClient, cuenta: str, fecha_desde: dt.date, fecha_hasta: dt.date
) -> str | None:
    """Mirror async del sync — captura del aio surface vía ``event_hooks``.

    WR-05 mirror (review-04): usa ``httpx.AsyncClient.event_hooks`` (request
    hook async-aware) en vez de monkey-patch del bound method. El async
    client es lazy; ``_ensure_http_client`` se invoca para garantizar que
    el ``httpx.AsyncClient`` está materializado antes de modificar los hooks.
    """
    http_client = await aclient._ensure_http_client()
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
        original_hooks = http_client.event_hooks
        hooks_with_spy: dict[str, list[Any]] = {
            "request": [*original_hooks.get("request", []), _spy],
            "response": list(original_hooks.get("response", [])),
        }
        try:
            http_client.event_hooks = hooks_with_spy
            await aclient.get_movimientos(cuenta, fecha_desde, fecha_hasta)
        except (httpx.HTTPError, HigyrusAPIError, HigyrusAuthError, HigyrusClientError):
            # Phase 11 CR-07 + CR-06: narrowed from bare ``Exception`` to the
            # specific subclasses raised by ``aclient.get_movimientos``. Paridad
            # sync↔async preservada en el clause.
            pass
        finally:
            http_client.event_hooks = original_hooks
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
    # HARN-01 / D-01 ENMENDADA: dedupe intra-proceso. El digest cubre el PAR
    # baseline-vs-actual, no sólo el actual — dos drifts con el mismo ``actual``
    # pero distinto ``expected`` son findings distintos y no pueden colapsarse.
    drift_key = (func_name, _drift_digest([committed.get("schema"), actual_schema]))
    if drift_key in _seen_drift_keys:
        # No-op con el contrato de ESTE helper: ``tuple[str, str]``. Un ``return``
        # desnudo devolvería ``None`` y el caller hace ``status, detail = ...``.
        # El detalle NO puede empezar con ``escrito``: el caller lo contaría como
        # baseline recién escrito (``elif detail.startswith("escrito")``).
        return ("PASS", f"{file_path.name} drift ya reportado en esta corrida")
    _seen_drift_keys.add(drift_key)
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


@probe_context(
    endpoint="/api/login",
    surface="sync",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result,
)
def probe_login_sync(client: Client) -> ProbeResult:
    """Probe 1: ``client.login()`` (HIGY-01).

    Setea ``_auth_failed`` global ante CUALQUIER falla de login para activar
    la cascade SKIPPED (D-HIGY-10, Phase 3 D-IOL-3 mirror). Se diferencian
    dos brackets de exception:

    1. ``HigyrusAPIError`` — la familia de errores de transporte-mapeado del
       paquete (cubre ``HigyrusAuthError`` 401, ``HigyrusAuthorizationError``
       403, ``HigyrusRateLimitError`` 429, y el propio ``HigyrusAPIError`` para
       cualquier otro non-2xx mapeado). Status code disponible en
       ``exc.status_code``.
    2. ``Exception`` — transporte / network (e.g. ``httpx.ConnectError``,
       ``httpx.TimeoutException``, ``httpx.HTTPStatusError`` para 5xx que
       bypassan ``_raise_for_response``). Sin status_code típico.

    Ambos brackets emiten finding ``AUTH OPEN`` y setean ``_auth_failed``
    para garantizar el contrato cascade SKIPPED del driver. Esto previene
    que un 403/429/500/network failure propague fuera de ``main()`` y
    aborte la driver antes de las 18 líneas + SUMMARY (review-04 CR-02).

    Phase 33 (D-07): el bracket 1 se angosta de ``HigyrusClientError`` (la base
    del paquete) a ``HigyrusAPIError``. ``HigyrusDecodeError`` es HERMANO de
    ``HigyrusAPIError``, no subclase, y la base los cubría a los dos — así que
    una divergencia de forma en la respuesta de login habría salido reclasificada
    como ``AUTH`` **y** habría seteado ``_auth_failed``, cascadeando SKIPPED a
    los 17 probes restantes y colapsando el censo entero de la corrida. La lista
    que este docstring ya enumeraba es exactamente la familia ``HigyrusAPIError``;
    el ``Decode`` nunca fue intencional acá. Ahora lo intercepta ``probe_context``.
    """
    global _auth_failed, _auth_failure_reason
    global _vendor_unreachable, _vendor_unreachable_reason
    base_url = client._state.base_url
    try:
        client.login()
    except HigyrusAPIError as exc:
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
    except httpx.ConnectError as exc:
        # Phase 39 D-01: host inalcanzable != cliente defectuoso. Va DESPUÉS de
        # ``HigyrusAPIError`` (un rechazo real del vendor sigue produciendo su
        # finding AUTH) y ANTES de ``_RESIDUAL_PROBE_EXCEPTIONS`` (que incluye
        # ``httpx.HTTPError``, superclase de ``ConnectError``: invertir el orden
        # deja esta rama inalcanzable). NO llama ``append_finding``: un AUTH OPEN
        # fabricado enrojece la rama de exención de higyrus en
        # ``verification/test_cycle_closure_phase33.py`` y ensucia un ledger
        # versionado con un hallazgo que no es sobre el cliente.
        # ``httpx.ConnectTimeout`` NO entra acá (no es subclase): un timeout
        # sigue cayendo en el bracket residual.
        _vendor_unreachable = True
        _vendor_unreachable_reason = f"sync login: {type(exc).__name__}: {exc}"
        _auth_failed = True
        _auth_failure_reason = f"sync login: {_VENDOR_UNREACHABLE_DETAIL}"
        return ProbeResult("login_sync", "SKIPPED", _VENDOR_UNREACHABLE_DETAIL)
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


@probe_context(
    endpoint="/api/login",
    surface="async",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_login_async(aclient: AsyncClient) -> ProbeResult:
    """Probe 2: ``await aclient.login()`` (HIGY-01).

    Setea el mismo ``_auth_failed`` global compartido con probe 1 (Discretion:
    flag único, no surface-segregated — D-IOL-3 Discretion mirror).

    Catch widening espejo de ``probe_login_sync`` (review-04 CR-02): captura
    ``HigyrusAPIError`` (cubre Auth/Authorization/RateLimit/APIError) y
    cualquier otro ``Exception`` (network / transport) para que no propaguen
    fuera de ``asyncio.run()`` y aborten la driver antes del SUMMARY.

    Phase 33 (D-07): mismo angostamiento que el sync — de ``HigyrusClientError``
    a ``HigyrusAPIError``, para que un ``HigyrusDecodeError`` (hermano, no
    subclase) no salga reclasificado como ``AUTH`` cascadeando SKIPPED al resto
    del sweep. Lo intercepta ``probe_context``.
    """
    global _auth_failed, _auth_failure_reason
    global _vendor_unreachable, _vendor_unreachable_reason
    base_url = aclient._state.base_url
    try:
        await aclient.login()
    except HigyrusAPIError as exc:
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
    except httpx.ConnectError as exc:
        # Espejo byte-paralelo del handler sync (CLAUDE.md dual sync/async, D-08).
        # Mismo orden de los tres brackets y misma ausencia de ``append_finding``.
        _vendor_unreachable = True
        _vendor_unreachable_reason = f"async login: {type(exc).__name__}: {exc}"
        _auth_failed = True
        _auth_failure_reason = f"async login: {_VENDOR_UNREACHABLE_DETAIL}"
        return ProbeResult("login_async", "SKIPPED", _VENDOR_UNREACHABLE_DETAIL)
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


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_health"],
    surface="sync",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_health_sync(client: Client) -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 3: ``higyrus_client.get_health()`` (HIGY-02).

    Hace las DOS cosas (Phase 31 code review CR-01), igual que
    ``probe_health_sync`` de ``main_market_data.py``:

    1. **Llama al wrapper tipado** ``Client.get_health() -> Health``. Ésta es la
       única forma de que la superficie pública de TYP-02 quede efectivamente
       ejercitada contra la API viva: el wrapper construye el ``Health`` vía
       ``_decode.walk_model``, emite records de divergencia en el logger
       ``higyrus_client`` y levanta ``HigyrusDecodeError`` bajo
       ``strict_decode=True``. Sin esta llamada la corrida estricta de la
       Phase 33 produciría CERO evidencia de divergencia para ``Health`` y para
       ``parse_get_health_response``.
    2. **Re-dispara el raw** vía ``_request`` directo para quedarse con el wire
       crudo que alimenta el snapshot de probe 15. El snapshot NO puede salir
       del wrapper: el ``schema_of`` sería función de la DECLARACIÓN del modelo
       y no del wire — el walker ya coercionó cada campo no-opcional a su tipo
       declarado y descartó toda clave no declarada, así que un
       float-vuelto-string, una clave agregada y una clave eliminada quedarían
       los tres invisibles. Éste es el análogo higyrus del ``_capture_raw_wire``
       de ``main_iol.py`` (Phase 30 CR-01). Por eso ``raw`` llega acá como dict
       crudo y los reads ``isinstance(raw, dict)`` / ``len(raw)`` de abajo
       siguen siendo drift-visible sin necesitar ``to_dict()``.

    Ambas llamadas van DENTRO del mismo ``try`` (aislamiento per-probe).

    Phase 33 (D-07): el ``HigyrusDecodeError`` del modo estricto ya NO se atrapa
    acá. Lo intercepta el decorador ``probe_context``, y el finding ``SHAPE`` lo
    escribe el ``DivergenceHandler`` desde el record de divergencia que
    ``_decode`` emitió justo antes de levantar. Un catch a mano acá mintearía un
    segundo finding para la misma divergencia, bajo un título distinto, rompiendo
    el ``idempotent_by_title`` del lock 10.

    D-HIGY-2: el detail emite ``keys=N`` (conteo) y el NOMBRE del tipo devuelto
    por el wrapper, nunca contenido del wire.
    """
    if _auth_failed:
        return (
            ProbeResult("get_health_sync", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = client._state.base_url
    try:
        health = client.get_health()
        raw = _raw_request_sync(client, "GET", "/api/health")
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
    return (
        ProbeResult("get_health_sync", "PASS", f"keys={len(raw)} typed={type(health).__name__}"),
        raw,
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_health"],
    surface="async",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
async def probe_get_health_async(
    aclient: AsyncClient,
) -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 4: espejo async de probe 3 (HIGY-02).

    Mismo par wrapper-tipado + re-disparo crudo que el sync (code review CR-01):
    ``await aclient.get_health()`` ejercita la superficie pública de TYP-02 y
    ``_raw_request_async`` conserva el wire para el snapshot de probe 15.

    Phase 33 (D-07): igual que el sync, el ``HigyrusDecodeError`` lo intercepta
    ``probe_context`` y el finding ``SHAPE`` lo escribe el ``DivergenceHandler``.
    """
    if _auth_failed:
        return (
            ProbeResult("get_health_async", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = aclient._state.base_url
    try:
        health = await aclient.get_health()
        raw = await _raw_request_async(aclient, "GET", "/api/health")
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
    return (
        ProbeResult("get_health_async", "PASS", f"keys={len(raw)} typed={type(health).__name__}"),
        raw,
    )


# ---------------------------------------------------------------------------
# Probes 5-6: get_listado_cuentas (HIGY-02 + D-HIGY-11)
# ---------------------------------------------------------------------------


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_listado_cuentas"],
    surface="sync",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_listado_cuentas_sync(
    client: Client,
) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
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
    base_url = client._state.base_url
    try:
        raw = _raw_request_sync(
            client,
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


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_listado_cuentas"],
    surface="async",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
async def probe_get_listado_cuentas_async(
    aclient: AsyncClient,
) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
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
    base_url = aclient._state.base_url
    try:
        raw = await _raw_request_async(
            aclient,
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


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_movimientos"],
    surface="sync",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_movimientos_sync(
    client: Client,
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
    base_url = client._state.base_url
    fecha_desde = today - dt.timedelta(days=30)
    fecha_hasta = today
    try:
        raw = _raw_request_sync(
            client,
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


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_movimientos"],
    surface="async",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
async def probe_get_movimientos_async(
    aclient: AsyncClient,
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
    base_url = aclient._state.base_url
    fecha_desde = today - dt.timedelta(days=30)
    fecha_hasta = today
    try:
        raw = await _raw_request_async(
            aclient,
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


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_posicion_valuada"],
    surface="sync",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_posicion_valuada_sync(
    client: Client,
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
    base_url = client._state.base_url
    try:
        raw = _raw_request_sync(
            client,
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


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_posicion_valuada"],
    surface="async",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
async def probe_get_posicion_valuada_async(
    aclient: AsyncClient,
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
    base_url = aclient._state.base_url
    try:
        raw = await _raw_request_async(
            aclient,
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


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_posiciones"],
    surface="sync",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_posiciones_sync(
    client: Client,
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
    base_url = client._state.base_url
    try:
        raw = _raw_request_sync(
            client,
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
    # D-04: cadena tipada ``Posicion.parking[...].diasParking`` sobre el payload
    # QUE YA ESTÁ EN LA MANO — cero llamadas HTTP adicionales.
    # ``SafeModel.from_api`` enruta por el mismo walker, el mismo sink y el mismo
    # camino de emisión que el parser del propio cliente, y hereda la ContextVar de
    # modo estricto que ``Client._request`` bindea y deliberadamente NO resetea, así
    # que construir el wrapper acá emite exactamente los mismos registros de
    # divergencia que habría emitido la función tipada, gratis. Eso es lo que hace
    # que la cadena respete la convención "una llamada HTTP por concepto de probe";
    # ``test_the_typed_chain_adds_no_http_call`` lo pinea estructuralmente.
    #
    # ``raw`` ya está normalizado a lista (``None`` de 204/cuerpo vacío → ``[]``), así
    # que la comprensión tolera el payload nulo sin rama defensiva. ``.parking`` es
    # ``list[Parking]`` no-Optional: con la clave ausente o ``null`` el Null Object
    # entrega ``[]``, nunca ``None`` — por eso la guarda es por veracidad, no ``is None``.
    #
    # LIMITACIÓN DE COBERTURA MEDIDA (transcribir al censo del plan 39-08, NO es un
    # detalle de implementación): el probe sigue enviando ``incluirParking=False`` y
    # este plan deliberadamente NO lo cambia — flipearlo alteraría la forma de la
    # respuesta y quemaría el baseline write-once de ``get_posiciones`` por deriva de
    # schema, sin ganancia (la mitad en vivo está bloqueada por DNS, LIVE-HIGY-42).
    # Consecuencia explícita: **en una corrida en vivo la rama poblada de ``parking``
    # no se ejercita**. La evidencia de esa rama es la suite mockeada del plan 39-02,
    # ``packages/higyrus-client/tests/test_deep_chain_edges.py``.
    try:
        posiciones = [Posicion.from_api(row) for row in raw]
        parking_entries = sum(len(posicion.parking) for posicion in posiciones)
        primer_dias_parking = next(
            (posicion.parking[0].diasParking for posicion in posiciones if posicion.parking),
            None,
        )
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"get_posiciones_sync cadena .parking unexpected {type(exc).__name__}",
            expected="Posicion.parking: list[Parking] (Null Object, nunca None)",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_posiciones_sync", "FINDING", f"{fid} (OPEN)"), None)
    if not raw:
        return (
            ProbeResult(
                "get_posiciones_sync",
                "PASS",
                f"0 items — empty path verified (parking={parking_entries})",
            ),
            raw,
        )
    return (
        ProbeResult(
            "get_posiciones_sync",
            "PASS",
            f"{len(raw)} items parking={parking_entries} diasParking={primer_dias_parking}",
        ),
        raw,
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_posiciones"],
    surface="async",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
async def probe_get_posiciones_async(
    aclient: AsyncClient,
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
    base_url = aclient._state.base_url
    try:
        raw = await _raw_request_async(
            aclient,
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
    # D-04 mirror: cadena tipada ``Posicion.parking[...].diasParking`` sobre el payload
    # QUE YA ESTÁ EN LA MANO — cero llamadas HTTP adicionales.
    # ``SafeModel.from_api`` enruta por el mismo walker, el mismo sink y el mismo
    # camino de emisión que el parser del propio cliente, y hereda la ContextVar de
    # modo estricto que ``AsyncClient._request`` bindea y deliberadamente NO resetea,
    # así que construir el wrapper acá emite exactamente los mismos registros de
    # divergencia que habría emitido la función tipada, gratis. Eso es lo que hace
    # que la cadena respete la convención "una llamada HTTP por concepto de probe";
    # ``test_the_typed_chain_adds_no_http_call`` lo pinea estructuralmente.
    #
    # ``raw`` ya está normalizado a lista (``None`` de 204/cuerpo vacío → ``[]``), así
    # que la comprensión tolera el payload nulo sin rama defensiva. ``.parking`` es
    # ``list[Parking]`` no-Optional: con la clave ausente o ``null`` el Null Object
    # entrega ``[]``, nunca ``None`` — por eso la guarda es por veracidad, no ``is None``.
    #
    # LIMITACIÓN DE COBERTURA MEDIDA (transcribir al censo del plan 39-08, NO es un
    # detalle de implementación): el probe sigue enviando ``incluirParking=False`` y
    # este plan deliberadamente NO lo cambia — flipearlo alteraría la forma de la
    # respuesta y quemaría el baseline write-once de ``get_posiciones`` por deriva de
    # schema, sin ganancia (la mitad en vivo está bloqueada por DNS, LIVE-HIGY-42).
    # Consecuencia explícita: **en una corrida en vivo la rama poblada de ``parking``
    # no se ejercita**. La evidencia de esa rama es la suite mockeada del plan 39-02,
    # ``packages/higyrus-client/tests/test_deep_chain_edges.py``.
    try:
        posiciones = [Posicion.from_api(row) for row in raw]
        parking_entries = sum(len(posicion.parking) for posicion in posiciones)
        primer_dias_parking = next(
            (posicion.parking[0].diasParking for posicion in posiciones if posicion.parking),
            None,
        )
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"get_posiciones_async cadena .parking unexpected {type(exc).__name__}",
            expected="Posicion.parking: list[Parking] (Null Object, nunca None)",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_posiciones_async", "FINDING", f"{fid} (OPEN)"), None)
    if not raw:
        return (
            ProbeResult(
                "get_posiciones_async",
                "PASS",
                f"0 items — empty path verified (parking={parking_entries})",
            ),
            raw,
        )
    return (
        ProbeResult(
            "get_posiciones_async",
            "PASS",
            f"{len(raw)} items parking={parking_entries} diasParking={primer_dias_parking}",
        ),
        raw,
    )


# ---------------------------------------------------------------------------
# Probe 13: parity sync↔async via query string capture (HIGY-06)
# ---------------------------------------------------------------------------


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_movimientos"],
    surface="sync",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result,
)
def probe_parity_sync_async(
    client: Client,
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
    base_url = client._state.base_url
    fecha_desde = today - dt.timedelta(days=30)
    fecha_hasta = today
    sync_q = _capture_sync_query_string(client, resolved_cuenta, fecha_desde, fecha_hasta)
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


@probe_context(
    endpoint="-",
    surface="sync",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result,
)
def probe_field_type_map(
    client: Client,
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
    base_url = client._state.base_url
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


@probe_context(
    endpoint="-",
    surface="sync",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result,
)
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


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_movimientos"],
    surface="sync",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result,
)
def probe_errors_envelope_sync(client: Client, today: dt.date) -> ProbeResult:
    """Probe 16: id_cuenta inválido → envelope ``[{title, detail}]`` (HIGY-05)."""
    if _auth_failed:
        return ProbeResult(
            "errors_envelope_sync",
            "SKIPPED",
            f"auth failed: {_auth_failure_reason}",
        )
    base_url = client._state.base_url
    try:
        client.get_movimientos(_INVALID_CUENTA_LITERAL, today, today)
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


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_movimientos"],
    surface="async",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_errors_envelope_async(aclient: AsyncClient, today: dt.date) -> ProbeResult:
    """Probe 17: espejo async de probe 16 (HIGY-05)."""
    if _auth_failed:
        return ProbeResult(
            "errors_envelope_async",
            "SKIPPED",
            f"auth failed: {_auth_failure_reason}",
        )
    base_url = aclient._state.base_url
    try:
        await aclient.get_movimientos(_INVALID_CUENTA_LITERAL, today, today)
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


@probe_context(
    endpoint="/api/login",
    surface="sync",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result,
)
def probe_auth_401(client: Client) -> ProbeResult:
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

    base_url = client._state.base_url
    original_password = os.getenv("HIGYRUS_PASSWORD", "")
    bad_password = original_password + "_INVALID"
    try:
        # D-03/T-15-05: ``configure()`` queda FUERA de scope de la migración —
        # este probe deliberadamente muta las credenciales del default-client
        # module-level y ejercita su ``login()`` para forzar el 401. Por eso el
        # ``configure``/``login`` siguen siendo module-level (NO se threadea el
        # ``client`` de buenas credenciales acá): el threaded ``client`` se usa
        # sólo para leer ``base_url`` arriba.
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


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_listado_cuentas"],
    surface="sync",
    decode_error=HigyrusDecodeError,
    on_decode_error=_shape_probe_result,
)
def probe_multi_account_iteration(client: Client) -> ProbeResult:
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
    base_url = client._state.base_url
    # Source 1: env var override (CSV).
    if _SAMPLE_CUENTAS_CSV.strip():
        cuentas = [c.strip() for c in _SAMPLE_CUENTAS_CSV.split(",") if c.strip()]
    else:
        # Source 2: live get_listado_cuentas() — si non-empty, primeras 2.
        try:
            live = client.get_listado_cuentas(estado="alta")
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
    # P-5: este probe golpea DOS endpoints bajo una sola superficie. El decorador
    # bindea el primero (``get_listado_cuentas``, la fuente 2 de arriba); sin este
    # re-binding toda divergencia de ``Movimiento`` se atribuiría al listado de
    # cuentas y la ruta del finding señalaría el endpoint equivocado.
    with endpoint_scope(_ENDPOINT_TEMPLATES["get_movimientos"]):
        for acct in cuentas[:2]:
            try:
                client.get_movimientos(
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

    # D-02: un único ``AsyncClient`` threadeado en todos los probes async; estado
    # propio (independiente del sync ``Client``). El ``aclose()`` del finally
    # cierra ESTA instancia (no el default-client module-level).
    aclient = AsyncClient(strict_decode=_STRICT)

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
        result_login = await probe_login_async(aclient)
        async_token_snapshot = aclient._state.token if result_login.status == "PASS" else None

        result_health, health_raw = await probe_get_health_async(aclient)
        result_listado, listado_raw = await probe_get_listado_cuentas_async(aclient)
        result_movs, _movs_raw = await probe_get_movimientos_async(aclient, today, resolved_cuenta)
        result_pv, _pv_raw = await probe_get_posicion_valuada_async(aclient, today, resolved_cuenta)
        result_pos, _pos_raw = await probe_get_posiciones_async(aclient, today, resolved_cuenta)

        # Async parity capture for probe 13 (params optional = None → drop_none).
        # Phase 33 (P-5): éste es el ÚNICO call site de decode en vivo del driver
        # que vive fuera de un ``probe_*``, así que el decorador no lo cubre —
        # ``get_movimientos`` acá decodifica ``Movimiento`` igual que el probe
        # dedicado. Sin este ``endpoint_scope`` el ``diff`` del finding diría
        # ``via -``. La superficie sigue siendo ``-`` (bindearla necesitaría un
        # ``surface_scope`` que ``verification/divergences.py`` no expone); no es
        # un hueco del censo —``handler.seen`` se indexa por
        # ``(slug, model, field_path, kind)``, sin endpoint ni superficie— y las
        # mismas triples ya llegan bien atribuidas vía
        # ``probe_get_movimientos_async``.
        if not _auth_failed and resolved_cuenta is not None:
            fecha_desde = today - dt.timedelta(days=30)
            fecha_hasta = today
            try:
                with endpoint_scope(_ENDPOINT_TEMPLATES["get_movimientos"]):
                    async_query = await _capture_async_query_string(
                        aclient, resolved_cuenta, fecha_desde, fecha_hasta
                    )
            except _RESIDUAL_PROBE_EXCEPTIONS:
                async_query = None

        result_errors = await probe_errors_envelope_async(aclient, today)
    finally:
        with contextlib.suppress(*_RESIDUAL_PROBE_EXCEPTIONS):
            await aclient.aclose()
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

    # D-16/D-24 (P-3): sube el allocator por encima de todo fid ya committeado.
    # Orden obligatorio — ``write_findings`` < ``_seed_fid_counter`` < primer
    # probe. Mismo orden canónico que ``main_market_data.py`` y ``main_iol.py``.
    _seed_fid_counter()

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

    # Phase 33 (LIVE-TYP-01 / D-01): el handler de divergencias se instala
    # alrededor del sweep entero — sube ``higyrus_client`` de NOTSET a INFO (sin
    # eso los records de especie ``extra`` se descartan antes de llegar a ningún
    # handler) y traduce cada record de seis claves a un finding ``SHAPE``.
    # ``next_fid`` recibe el slug y lo descarta: el driver ya tiene UN allocator
    # por proceso y compartirlo es lo que impide que el handler y el driver se
    # pisen los fids.
    with divergence_capture(("higyrus_client",), next_fid=lambda _slug: _next_fid()) as handler:
        results: dict[str, ProbeResult] = {}
        payloads: dict[str, Any] = {}

        # D-01/D-02: un único ``Client`` sync threadeado en TODOS los probes sync.
        # Estado propio (independiente del ``AsyncClient`` que ``_async_main``
        # construye por separado). Reemplaza los ~14 ``_get_default()`` reads.
        client = Client(strict_decode=_STRICT)

        # (a) Probe 1 sync (login_sync) — puede setear _auth_failed.
        results["login_sync"] = probe_login_sync(client)

        # Phase 39 D-01: si el vendor no es alcanzable, el driver NO corrió.
        # Se emite la línea SKIPPED a STDOUT (el único stream que
        # ``main_verify.py`` escanea) y se sale con código 0, antes de que
        # ningún probe downstream cascadee 17 SKIPPED y antes de cualquier
        # ``append_finding``: la rama no escribe nada en el ledger. El
        # ``sys.exit`` adentro del ``with`` es seguro — ``divergence_capture``
        # es un ``@contextmanager`` con ``try/finally``, así que el
        # ``SystemExit`` propaga por el ``yield`` y los loggers se restauran.
        if _vendor_unreachable:
            print(_VENDOR_UNREACHABLE_SKIP_LINE)
            # Phase 39 (D-09 / T-39-12): el sobre se REESCRIBE con cero probes y
            # la causa medida. Sin esto, el sobre de una corrida anterior
            # quedaría en pie y el cierre de ciclo lo leería como evidencia de
            # ESTA corrida — que es precisamente el repudio que la costura de
            # no-vacuidad existe para cerrar. Una corrida saltada invalida el
            # sobre; no lo deja intacto.
            write_run_evidence(
                _PKG,
                driver="main_higyrus.py",
                triples=[],
                counts={},
                skipped=_VENDOR_UNREACHABLE_EVIDENCE,
            )
            sys.exit(0)

        _sync_token_snapshot = (
            client._state.token if results["login_sync"].status == "PASS" else None
        )
        if _sync_token_snapshot:
            secrets.append(_sync_token_snapshot)

        # (b) Probe 3 sync (get_health_sync).
        result_health_sync, health_raw = probe_get_health_sync(client)
        results["get_health_sync"] = result_health_sync
        if health_raw is not None:
            payloads["get_health"] = health_raw

        # (c) Probe 5 sync (get_listado_cuentas_sync) — RESOLVE _resolved_cuenta.
        result_listado_sync, listado_raw = probe_get_listado_cuentas_sync(client)
        results["get_listado_cuentas_sync"] = result_listado_sync
        if listado_raw is not None:
            payloads["get_listado_cuentas"] = listado_raw

        # (d) Probe 7 sync (get_movimientos_sync).
        result_movs_sync, movs_raw = probe_get_movimientos_sync(client, today, _resolved_cuenta)
        results["get_movimientos_sync"] = result_movs_sync
        if movs_raw is not None:
            payloads["get_movimientos"] = movs_raw

        # (e) Probe 9 sync (get_posicion_valuada_sync).
        result_pv_sync, pv_raw = probe_get_posicion_valuada_sync(client, today, _resolved_cuenta)
        results["get_posicion_valuada_sync"] = result_pv_sync
        if pv_raw is not None:
            payloads["get_posicion_valuada"] = pv_raw

        # (f) Probe 11 sync (get_posiciones_sync).
        result_pos_sync, pos_raw = probe_get_posiciones_sync(client, today, _resolved_cuenta)
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
            client, today, _resolved_cuenta, async_results.async_query
        )

        # (i) Probe 14 (field_type_map) — diff sobre raw sync payloads.
        results["field_type_map"] = probe_field_type_map(
            client,
            payloads.get("get_listado_cuentas"),
            payloads.get("get_movimientos"),
            payloads.get("get_posiciones"),
            payloads.get("get_posicion_valuada"),
        )

        # (j) Probe 15 (schema_snapshot) — 5 snapshots.
        base_url = client._state.base_url
        results["schema_snapshot"] = probe_schema_snapshot(
            today, _resolved_cuenta, payloads, base_url
        )

        # (k) Probe 16 (errors_envelope_sync) — always-on.
        results["errors_envelope_sync"] = probe_errors_envelope_sync(client, today)

        # (k.5) Phase 9 BUG-04 (D-08, D-10): multi-account iteration probe.
        # Corre después de get_listado_cuentas + get_movimientos (sync + async) para
        # que _resolved_cuenta esté disponible si el operator quiere comparar; el
        # propio probe puede consumir get_listado_cuentas o el override CSV.
        results["multi_account_iteration"] = probe_multi_account_iteration(client)

        # (l) Probe 18 (auth_401) — opt-in, single-shot, ÚLTIMO.
        results["auth_401"] = probe_auth_401(client)

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
    # Phase 33 (P-3 / T-33-11): ``DIVERGENCES`` es ``len(handler.seen)`` — el
    # conteo de triples distintos ``(slug, model, field_path, kind)``, LA unidad
    # del censo y la única directamente comparable contra el piso de
    # ``29-SIZING.md``. NO es el conteo de findings: con la superficie embebida
    # en el título hay ~2 findings por triple, así que ni ``FINDING=N`` ni el
    # conteo de bloques del archivo sirven para ese contraste. ``HANDLER_ERRORS``
    # es el tally de fallas del sink: un pipeline de logging que puede fallar en
    # silencio no sirve como registro de auditoría, así que el número se imprime
    # siempre — un valor distinto de cero invalida el censo de esta corrida.
    # Formato idéntico al de ``main_matriz.py`` para que 33-04 parsee una sola
    # forma de línea.
    safe_print(
        f"SUMMARY: PASS={n_pass} FAIL={n_fail} SKIPPED={n_skip} FINDING={n_find} "
        f"DIVERGENCES={len(handler.seen)} HANDLER_ERRORS={len(handler.errors)}",
        secrets=secrets,
    )

    # Phase 39 (D-09 + D-10): la línea SUMMARY imprime el CONTEO de triples y se
    # va con el proceso; el sobre persiste los MIEMBROS —la unidad del censo— y
    # el conteo de probes, la evidencia positiva de que este driver corrió.
    write_run_evidence(
        _PKG,
        driver="main_higyrus.py",
        triples=sorted(handler.seen),
        counts={"PASS": n_pass, "FAIL": n_fail, "SKIPPED": n_skip, "FINDING": n_find},
    )


if __name__ == "__main__":
    main()
