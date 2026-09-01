"""Phase 5 live verification driver para ``matriz-client`` (Primary API / MATBA ROFEX).

Driver de verificación en vivo contra un sandbox de Primary del allowlist
D-MATZ-33 (``_VENUE_ALLOWLIST``: remarkets o bbsa; nunca producción). Ejercita
~25 probes nombrados en orden D-MATZ-29 cubriendo:

- ``MATZ-01`` — login sync vs. servicio real.
- ``MATZ-02`` — happy-path sweep de los 18 endpoints REST públicos.
- ``MATZ-03`` — bidirectional SafeModel<->wire diff sobre los 11 modelos
  ``_SafeModel`` matriz vía ``diff_safemodel_bidirectional`` promovido en Phase 5.
- ``MATZ-05`` — 3 error probes always-on (bogus symbol, invalid account, malformed CFI)
  con distinción HTTP 4xx no-mapeado vs. ``status='ERROR'`` mapeado (D-MATZ-22/23).
- ``MATZ-07`` — market-hours guard sobre ``LA.date`` epoch ms (D-MATZ-5).
- ``DRIFT-01`` mirror — schema snapshots envelope D-21 + D-25 no-overwrite-on-drift.
- ``DRIFT-02`` — ``verify_cycle_closure`` x 4 paquetes verificados (Phase 2-5).

**Phase 10 LIVE-02 extension (REFAC-04):** ``matriz_client.aio`` async REST
surface landed in Plan 10-02 + 10-03. This driver now runs paired sync↔async
probes (D-06 interleaved pattern, mirror ``main_iol.py``) covering the
**REST-only subset** of the matriz surface. The async paridad scope per
CONTEXT D-09 excludes (a) WebSocket-mediated order entry (``ws_*``) and
(b) Risk API ``auth_basic`` endpoints (``get_positions``,
``get_detailed_positions``, ``get_account_report``) — those are Phase 11
CR-08 scope. A single ``asyncio.run(_async_main(...))`` orchestrates all
async probes (D-IOL-6 mirror) and the final paridad reporter compares the
PASS/FINDING/SKIPPED outcome sets between sync and async.

**Security gates aplicados al inicio de ``main()``** (D-MATZ-33):

1. ``require_env(_PKG, ["PRIMARY_USER", "PRIMARY_PASSWORD"])`` — HARN-01 path.
2. Allowlist de venue por igualdad exacta de hostname (Phase 39 D-02): si el
   hostname de la base URL resuelta no está en ``_VENUE_ALLOWLIST`` se emite la
   línea ``SKIPPED matriz-client: …`` a **stdout** y se sale con código 0
   (Phase 39 D-01: un bloqueo de política no es una falla del driver).

Output verbatim (D-02 mirror Phase 2-4): cada probe emite una línea
``PROBE <name>: <status> <detail>`` y al final ``SUMMARY: PASS=N FAIL=N
SKIPPED=N FINDING=N DIVERGENCES=N HANDLER_ERRORS=N`` (Phase 33: los dos últimos
campos son ``len(handler.seen)`` —la unidad del censo— y el tally de fallas del
sink; ver ``main()``), todo a través de ``safe_print(..., secrets=[...])``
(D-MATZ-32) con ``PRIMARY_USER``, ``PRIMARY_PASSWORD`` y ``_token`` (este último
agregado dinámicamente tras ``probe_login_sync``).

Uso::

    uv run --package matriz-client python main_matriz.py

Variables de entorno (ver ``packages/matriz-client/.env.example``):

- Requeridas: ``PRIMARY_USER``, ``PRIMARY_PASSWORD``
- Opcional default-remarkets: ``PRIMARY_BASE_URL``
- Opcional D-MATZ-33: ``PRIMARY_ACCOUNT`` (gate para 6 probes account-scoped),
  ``MATRIZ_SAMPLE_SYMBOL`` (override del símbolo auto-resuelto),
  ``MATRIZ_SAMPLE_CL_ORD_ID`` / ``MATRIZ_SAMPLE_PROPRIETARY`` (gate para 2
  probes ID-scoped), ``MATRIZ_SAMPLE_EXEC_ID`` (gate para get_order_by_exec_id).
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import hashlib
import json
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

import httpx
from verification import (
    append_finding,
    diff_safemodel_bidirectional,
    divergence_capture,
    probe_context,
    probes_executed,
    read_run_evidence,
    require_env,
    safe_print,
    schema_of,
    write_findings,
    write_run_evidence,
)
from verification.cycle_report import verify_cycle_closure
from verification.findings import max_existing_fid

import matriz_client as primary
from matriz_client import AsyncClient, Client, MatrizDecodeError, PrimaryAPIError
from matriz_client._core import RequestSpec, parse_envelope_response
from matriz_client.exceptions import AuthenticationError
from matriz_client.models import (
    AccountReport,
    DetailedPosition,
    Instrument,
    InstrumentDetail,
    MarketDataSnapshot,
    Order,
    Position,
    Segment,
    Trade,
)
from matriz_client.types import CFICode

# ---------------------------------------------------------------------------
# Module-level constants & state
# ---------------------------------------------------------------------------

_PKG = "matriz-client"
_REPO_ROOT = Path(__file__).resolve().parent
_SCHEMA_DIR = _REPO_ROOT / ".planning" / "verification" / "schemas" / _PKG

# ---------------------------------------------------------------------------
# D-MATZ-33 venue allowlist (Phase 39 D-02)
# ---------------------------------------------------------------------------
#
# Hostnames CONFIRMADOS como no-producción, mapeados a su token de venue. La
# autorización de la segunda entrada es una decisión explícita del operador del
# 2026-08-29 (Phase 39 D-02, registrada en `39-CONTEXT.md`): `api.bbsa.matrizoms.com.ar`
# es un sandbox real, distinto de remarkets, con `login()` y `get_segments()` ya
# verificados ahí.
#
# La comparación es por IGUALDAD EXACTA de hostname — nunca por pertenencia de
# substring ni por `endswith`. El chequeo anterior (`"remarkets" not in base`)
# habría dejado pasar `https://api.remarkets.primary.com.ar.attacker.example`, y
# un `endswith` deja pasar la misma clase de sufijo hostil; además
# `https://<host-confirmado>@attacker.example` mete el host confirmado en el
# userinfo y no en el authority (T-39-01, misma clase que documenta
# `verification/mutation_gate.py`).
#
# Ampliar este mapping NO es un cambio de rutina: cada host nuevo exige un
# checkpoint humano bloqueante (prohibición P-05 del milestone).
#
# `verification/mutation_gate.py` NO se toca: su `_SANDBOX_HOST` remarkets-only
# deja el order entry fail-closed automáticamente bajo bbsa, sin cambio de
# código (T-39-02).
_VENUE_ALLOWLIST: dict[str, str] = {
    "api.remarkets.primary.com.ar": "remarkets",
    "api.bbsa.matrizoms.com.ar": "bbsa",
}

# Línea verbatim que el driver emite a STDOUT cuando la base URL cae fuera del
# allowlist. Es un literal a propósito: `main_verify.py` clasifica por la forma
# `^SKIPPED \S.*:` (los dos puntos son load-bearing) y NO interpolar la base URL
# ni el hostname es lo que garantiza que el veredicto de política no filtre el
# dato de entrada (T-39-04). Antes de D-01 esta condición salía como `ABORT` a
# stderr con exit 1, que el clasificador reportaba `FAILED` — un bloqueo de
# política contado como falla.
_HOST_SKIP_LINE = "SKIPPED matriz-client: base URL fuera del allowlist D-MATZ-33 — LIVE-MATZ-33"

# Causa medida + destino nombrado que viaja en el sobre de evidencia de corrida
# (Phase 39 D-09). Es la línea SKIPPED sin su prefijo de veredicto: ni base URL
# ni hostname, por la misma razón que ella (T-39-04/T-39-10).
_HOST_SKIP_EVIDENCE = "base URL fuera del allowlist D-MATZ-33 — LIVE-MATZ-33"

# Destino nombrado por paquete para el veredicto SKIPPED del cierre de ciclo
# (Phase 39 D-09). Tres entradas explícitas; el resto cae al default. Un
# deferral sin destino es lo que P-03 prohíbe: "no corrió" tiene que decir
# hacia dónde se repara.
_CYCLE_CLOSURE_DESTINATION: dict[str, str] = {
    "higyrus-client": "LIVE-HIGY-42",
    "matriz-client": "LIVE-MATZ-33",
}
_CYCLE_CLOSURE_DEFAULT_DESTINATION = "LIVE-NOBJ-01"


def _cycle_closure_destination(pkg: str) -> str:
    """Destino nombrado al que se repara la falta de evidencia de corrida de ``pkg``."""
    return _CYCLE_CLOSURE_DESTINATION.get(pkg, _CYCLE_CLOSURE_DEFAULT_DESTINATION)


def _cycle_closure_verdict(
    pkg: str,
    *,
    probes: int,
    evidence: dict[str, Any] | None,
    ok: bool,
    missing: list[str],
) -> tuple[str, str]:
    """``(status, detail)`` del cierre de ciclo de ``pkg`` — el predicado D-09.

    Función de módulo, anotada y testeable por import: el predicado se verifica
    sin correr el driver, igual que :func:`_venue_token` (patrón de la Phase 39
    plan 01). El sitio de decisión —el loop de ``main()``— sólo hace la IO.

    Tabla:

    - ``probes <= 0`` (sobre ausente, o corrida saltada) ⇒ ``SKIPPED`` con la
      causa medida que el sobre trae —o ``"sin evidencia de corrida"`` si no
      trae ninguna— y el destino nombrado. **No** se escribe finding: no correr
      no es un defecto del paquete.
    - ``probes > 0`` y ``ok`` ⇒ ``PASS``, con el conteo de probes y el
      ``captured_at`` del sobre. Ese par ES la evidencia positiva que el censo
      transcribe.
    - ``probes > 0`` y no ``ok`` ⇒ ``FAIL`` con las regresiones faltantes
      (comportamiento previo, preservado).

    El criterio NO es "al menos un finding CONFIRMED/FIXED" —el que usa
    ``main_market_data.py``—: ámbito tiene cero por declarar cero clases de
    modelo y higyrus tiene cero por no haber sido medido nunca. Un predicado
    basado en promociones reprobaría a los dos, uno por estar limpio y el otro
    por no haber corrido, dándole el mismo veredicto a dos causas opuestas.
    """
    if probes <= 0:
        cause = ""
        if evidence is not None:
            raw = evidence.get("skipped")
            if isinstance(raw, str) and raw:
                cause = raw
        if not cause:
            cause = "sin evidencia de corrida"
        destination = _cycle_closure_destination(pkg)
        # La causa que escriben los caminos de skip de los drivers ya termina en
        # su destino; no se concatena dos veces.
        detail = cause if destination in cause else f"{cause} — {destination}"
        return ("SKIPPED", detail)

    if ok:
        captured_at = evidence.get("captured_at") if evidence is not None else None
        stamp = captured_at if isinstance(captured_at, str) and captured_at else "<sin timestamp>"
        return ("PASS", f"{probes} probes ejecutados, evidencia de {stamp}")

    return ("FAIL", f"missing regressions: {', '.join(missing)}")


def _venue_token(base_url: str) -> str | None:
    """Devuelve el token de venue del allowlist D-MATZ-33, o ``None`` (fail-closed).

    Extrae el hostname REAL con :func:`urllib.parse.urlsplit` y lo compara por
    igualdad contra :data:`_VENUE_ALLOWLIST`. Una base URL sin esquema (forma que
    admiten los ``.env`` históricos) se re-parsea como authority puro para que la
    variante userinfo tampoco pase por ahí. Cualquier entrada imparseable, sin
    host, o con un host que no esté en el allowlist devuelve ``None``.
    """
    try:
        parts = urlsplit(base_url)
        if not parts.netloc:
            parts = urlsplit(f"//{base_url}")
        host = parts.hostname
    except ValueError:
        # URL imparseable (p.ej. `https://[oops/api`): fail closed, nunca crash.
        return None
    if host is None:
        return None
    return _VENUE_ALLOWLIST.get(host)


# Phase 11 CR-06: tuple de excepciones residuales para los catch-all post-mapeo
# en los probe boundaries. Los probes capturan primero ``AuthenticationError``
# y/o ``httpx.HTTPStatusError`` específico cuando aplica; este catch-all
# atrapa el resto -- ``PrimaryAPIError`` no-AuthenticationError, network /
# transport residual, parsing o typing inesperado (e.g. payload shape
# inesperado que rompe un .get() o un .values()) -- y los reporta via
# ``append_finding(..., class_="ERROR-MAP", ...)``. EXCLUYE
# ``KeyboardInterrupt`` y ``SystemExit`` (no son ``Exception`` subclasses).
#
# NOTA: ``PrimaryAPIError`` ES incluido porque varios probes lo dejan caer al
# catch-all post-mapeo cuando NO es ``AuthenticationError`` (el primer except
# arriba captura el caso ``AuthenticationError`` esperado, y este residual
# atrapa el caso 500 / ERROR mapeado al base ``PrimaryAPIError``).
_RESIDUAL_PROBE_EXCEPTIONS = (
    httpx.HTTPError,
    OSError,
    PrimaryAPIError,
    AttributeError,
    TypeError,
    ValueError,
    KeyError,
)

# D-21 envelope: mapping cada probe func_name al SLUG de su archivo de schema snapshot
# (nombre base, sin directorio ni extensión). La ruta completa la arma
# :func:`_schema_path`, que le intercala el token de venue — ver ahí el porqué.
_SCHEMA_FILES: dict[str, str] = {
    "get_segments": "get-segments",
    "get_all_instruments": "get-all-instruments",
    "get_instruments_details": "get-instruments-details",
    "get_instrument_detail": "get-instrument-detail",
    "get_instruments_by_cfi_ESXXXX": "get-instruments-by-cfi-esxxxx",
    "get_instruments_by_segment": "get-instruments-by-segment",
    "get_market_data": "get-market-data",
    "get_trades": "get-trades",
    "get_active_orders": "get-active-orders",
    "get_filled_orders": "get-filled-orders",
    "get_all_orders": "get-all-orders",
    "get_order_status": "get-order-status",
    "get_order_history": "get-order-history",
    "get_order_by_exec_id": "get-order-by-exec-id",
    "get_positions": "get-positions",
    "get_detailed_positions": "get-detailed-positions",
    "get_account_report": "get-account-report",
}

# Token que reemplaza al de venue cuando el hostname NO está en `_VENUE_ALLOWLIST`.
# Camino INALCANZABLE en producción —el gate D-MATZ-33 de `main()` sale con SKIPPED
# antes de que corra ningún probe—, pero el helper no debe lanzar por eso: fail-safe,
# no fail-hard. Es un literal cerrado, nunca un fragmento de la URL de entrada
# (T-39-20).
_VENUE_SENTINEL = "unknown-venue"

# D-21 path templates por endpoint canonical (con {account_id} placeholder donde aplica).
_ENDPOINT_TEMPLATES: dict[str, str] = {
    "get_segments": "/rest/segment/all",
    "get_all_instruments": "/rest/instruments/all",
    "get_instruments_details": "/rest/instruments/details",
    "get_instrument_detail": "/rest/instruments/detail",
    "get_instruments_by_cfi_ESXXXX": "/rest/instruments/byCFICode",
    "get_instruments_by_segment": "/rest/instruments/bySegment",
    "get_market_data": "/rest/marketdata/get",
    "get_trades": "/rest/data/getTrades",
    "get_active_orders": "/rest/order/actives",
    "get_filled_orders": "/rest/order/filleds",
    "get_all_orders": "/rest/order/all",
    "get_order_status": "/rest/order/id",
    "get_order_history": "/rest/order/allById",
    "get_order_by_exec_id": "/rest/order/byExecId",
    "get_positions": "/rest/risk/position/getPositions/{account_id}",
    "get_detailed_positions": "/rest/risk/detailedPosition/{account_id}",
    "get_account_report": "/rest/risk/accountReport/{account_id}",
}

# Phase 33 (LIVE-TYP-01): flag del segundo pase. El runner de dos pases corre el
# driver una vez en modo observable (censo completo) y otra con
# ``MARKET_LIBS_STRICT_DECODE=1``, que prueba que el raise de modo estricto
# efectivamente dispara. Viaja como kwarg del constructor para NO agregar un
# segundo sitio de construcción: ``test_main_matriz_uses_single_client_instance``
# asserta ``1 <= ctor_calls <= 2`` por AST.
_STRICT: bool = os.getenv("MARKET_LIBS_STRICT_DECODE") == "1"

# D-MATZ-33 env vars opt-in precargadas al import.
_SAMPLE_SYMBOL: str | None = os.getenv("MATRIZ_SAMPLE_SYMBOL")
_SAMPLE_CL_ORD_ID: str | None = os.getenv("MATRIZ_SAMPLE_CL_ORD_ID")
_SAMPLE_PROPRIETARY: str | None = os.getenv("MATRIZ_SAMPLE_PROPRIETARY")
_SAMPLE_EXEC_ID: str | None = os.getenv("MATRIZ_SAMPLE_EXEC_ID")
_PRIMARY_ACCOUNT: str | None = os.getenv("PRIMARY_ACCOUNT")

# D-MATZ-31 cascade SKIPPED flag.
_auth_failed: bool = False
_auth_failure_reason: str = ""

# D-MATZ-1 / D-MATZ-2: resolved sample state for downstream probes.
_resolved_symbol: str | None = None
_resolved_segment: str | None = None

# Contador module-level para asignar fids deterministicamente F-01, F-02, ...
# NO arranca en 0 en el run real: ``_seed_fid_counter()`` lo sube al máximo fid
# ya registrado antes del primer probe (D-16/D-24). Sin ese seed, cada finding
# nuevo re-emitiría un fid ya ocupado — y contra el archivo committeado, que hoy
# lleva F-01..F-10, eso significa perder en silencio los primeros diez findings
# de cada corrida mientras el driver sigue reportando ``FINDING=N``.
_fid_counter: int = 0


def _seed_fid_counter() -> None:
    """Sube ``_fid_counter`` al máximo fid ya registrado en el findings file (D-16/D-24).

    Debe correr DESPUÉS de ``write_findings(_PKG)`` (el bootstrap del archivo) y
    ANTES del primer probe, para que todo fid emitido en este run caiga por
    encima de lo ya escrito y realmente aterrice en el archivo.

    La falla que previene tiene dos caras, y en matriz **la segunda aplica a los
    diez fids committeados**, sin excepción:

    - un fid re-emitido cuyo status registrado ES ``OPEN`` NO dispara el
      short-circuit de :func:`verification.findings.append_finding`: el bloque de
      detalle se **reescribe en el lugar** con contenido ajeno y el triage que el
      operador arrastró desde fases anteriores se pierde;
    - un fid re-emitido cuyo status registrado NO es ``OPEN`` sí dispara el
      short-circuit: el write se vuelve un no-op **silencioso** mientras
      ``main()`` igual lo cuenta en ``FINDING=N`` y el ``SUMMARY`` reporta éxito.
      El run pierde su entregable creyendo que funcionó.

    ``.planning/verification/matriz-client-findings.md`` lleva hoy ``F-01``..
    ``F-10`` y **ninguno** está ``OPEN``: 7 ``NO-FIX`` (``F-01``, ``F-03``..
    ``F-08``), 2 ``EXPECTED`` (``F-02``, ``F-10``) y 1 ``FIXED`` (``F-09``). Es
    decir que sin este seed los primeros diez findings de CADA corrida de matriz
    se descartan en silencio — el caso peor de los dos, diez veces seguidas.

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
# escribiendo un bloque nuevo en la corrida siguiente (verboso, nunca lossy).
# La clave es ``(identidad del baseline, digest del contenido de la divergencia)``
# y NO incluye la superficie: dentro de un proceso cada par función-superficie se
# visita una sola vez. En ESTE driver la identidad es el nombre del archivo de
# baseline, no ``func_name`` — ver el comentario del sitio de drift.
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


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Resultado de un probe: nombre + status + detalle short-form."""

    name: str
    status: str  # "PASS" | "FAIL" | "SKIPPED" | "FINDING"
    detail: str


def _shape_probe_result(probe_name: str, surface: str, exc: BaseException) -> ProbeResult:
    """Fallback de ``probe_context`` ante un ``MatrizDecodeError`` (D-07).

    El finding ``SHAPE`` YA lo escribió :class:`verification.divergences.DivergenceHandler`
    a partir del record de divergencia que ``_decode`` emitió justo antes de
    levantar. Este helper NO escribe un segundo finding: mintear uno acá
    duplicaría la divergencia bajo otro título y rompería el ``idempotent_by_title``
    del lock 10. Sólo traduce la excepción al ``ProbeResult`` que el driver espera.

    Lee ÚNICAMENTE ``model`` / ``field_path`` / ``declared_type`` /
    ``observed_type`` — los cuatro atributos certificados type-and-path-only por
    T-29-36 — y nada más de la excepción (T-33-07: nada de credenciales ni de
    valores del wire puede filtrarse a stdout ni a un artefacto committeado).
    Nunca ``repr(exc)``, nunca ``exc.args``.

    ``MatrizDecodeError`` es hermano de ``PrimaryAPIError``, no subclase: ambos
    cuelgan de ``MatrizClientError``. Por eso el ``_RESIDUAL_PROBE_EXCEPTIONS``
    de este driver —que sí contiene ``PrimaryAPIError``— no lo atrapa, y sin este
    seam el modo estricto mataría el proceso con traceback y cero findings.
    """
    name = probe_name.removeprefix("probe_")
    if isinstance(exc, MatrizDecodeError):
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
    """Variante 2-tuple de :func:`_shape_probe_result` para los probes del sweep sync.

    matriz tiene DOS formas canónicas de retorno de probe, no una: los 18 probes
    del happy-path sweep devuelven ``(ProbeResult, raw_payload | None)`` porque
    ``main()`` acumula sus payloads en ``payloads[...]``, mientras que login,
    field_type_map, los tres error probes, schema_snapshot y los 22 probes async
    devuelven un ``ProbeResult`` pelado. Un único fallback con forma de 2-tuple
    haría que ``results.append(probe_error_bogus_symbol(client))`` metiera una
    tupla en una ``list[ProbeResult]`` y el ``r.name`` del loop de impresión
    explotara con ``AttributeError`` — bajo modo estricto, exactamente el crash
    que este plan existe para eliminar. De ahí los dos helpers.
    """
    return (_shape_probe_result(probe_name, surface, exc), None)


def _first_dict(payload: Any, *, fname: str | None = None) -> dict[str, Any] | None:
    """Devuelve el primer dict de una lista, o None.

    Distingue 3 casos (Phase 11 CR-04 fix):

    - **ok**: ``payload`` es ``list[dict, ...]`` no vacía -> retorna el primer dict.
    - **no_data**: ``payload`` es ``[]`` -> retorna None silenciosamente
      (legitimate; vacío esperable durante off-market windows).
    - **wrong_type**: ``payload`` no es list, o lo es pero su primer elemento no
      es dict -> retorna None Y (si ``fname is not None``) emite un finding
      ``SHAPE OPEN`` con descripcion del shape divergente. Esto cierra CR-04:
      pre-Phase-11 los callers no podían distinguir wrong_type de no_data, y
      payloads mal-formados se ocultaban silenciosamente en el pipeline.

    El kwarg ``fname`` es opt-in para backwards-compat: los call-sites que no
    lo pasan obtienen el comportamiento legacy (silent None).
    """
    if isinstance(payload, list):
        if not payload:
            # no_data: vacío legítimo, NO finding.
            return None
        if not isinstance(payload[0], dict):
            # wrong_type: list cuyo primer elemento no es dict.
            if fname is not None:
                fid = _next_fid()
                append_finding(
                    _PKG,
                    fid=fid,
                    class_="SHAPE",
                    surface="sync",
                    status="OPEN",
                    title=f"{fname}: payload[0] no es dict",
                    expected="list[dict] (envelope-unwrapped)",
                    actual=f"type(payload[0])={type(payload[0]).__name__}",
                    diff="downstream SafeModel diff SKIPPED",
                    base_url=primary.client._base_url,
                )
            return None
        return cast(dict[str, Any], payload[0])
    # wrong_type: payload no es list.
    if fname is not None:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title=f"{fname}: payload no es list",
            expected="list[dict] (envelope-unwrapped)",
            actual=f"type(payload)={type(payload).__name__}",
            diff="downstream SafeModel diff SKIPPED",
            base_url=primary.client._base_url,
        )
    return None


def _schema_path(func_name: str, base_url: str) -> Path:
    """Ruta del baseline write-once de ``func_name`` SEGREGADA POR VENUE.

    El nombre es ``<slug>.<venue>.json``: el slug sale de :data:`_SCHEMA_FILES` y el
    token de venue de :func:`_venue_token` sobre la ``base_url`` que
    :func:`_write_or_check_schema` **ya recibe**. Esa función es la ÚNICA fuente de
    verdad de venues del driver (allowlist D-MATZ-33, plan 39-01): acá no hay una
    segunda tabla, y por eso el token nunca puede ser un fragmento arbitrario de la
    URL de entrada — sale de un dict cerrado de valores literales (T-39-20). El
    directorio se deriva de ``__file__`` vía :data:`_SCHEMA_DIR`.

    **Por qué el venue es parte de la clave (Phase 39, Open Question 1 / Pitfall 1).**
    Los baselines son write-once y D-25 prohíbe sobrescribir uno que difiere: si el
    archivo se eligiera sólo por nombre de función —como hasta la Phase 39— la primera
    corrida contra el sandbox **bbsa** diffearía sus formas contra las líneas base
    capturadas contra **remarkets** el 2026-06-10, y emitiría hasta 8 findings
    ``SHAPE OPEN`` que describen una diferencia **entre venues**, no un defecto del
    cliente. Ése es exactamente el ruido que SC-4 existe para evitar (precedente: la
    Phase 33 ya tuvo que separar findings de censo de findings de deriva). Con la
    segregación, esa primera corrida **captura baselines frescos** para bbsa y los de
    remarkets quedan intactos y siguen siendo válidos para una futura corrida contra
    remarkets. El censo del plan 39-08 debe transcribir este caveat.

    Un hostname fuera del allowlist cae en :data:`_VENUE_SENTINEL` en vez de lanzar:
    camino inalcanzable en producción porque el gate D-MATZ-33 sale antes de que corra
    ningún probe.
    """
    venue = _venue_token(base_url) or _VENUE_SENTINEL
    return _SCHEMA_DIR / f"{_SCHEMA_FILES[func_name]}.{venue}.json"


def _write_or_check_schema(
    func_name: str,
    endpoint_template: str,
    sample_params: dict[str, Any],
    raw_payload: Any,
    base_url: str,
) -> tuple[str, str]:
    """Escribe o compara el schema snapshot. D-25: no-overwrite-on-drift.

    Envelope D-21: ``{endpoint, client_function, captured_at, base_url,
    sample_params, schema}``. Si el archivo no existe → escribe + PASS. Si
    existe y el schema actual coincide con el committed → PASS sin drift.
    Si existe y difiere → emite finding ``SHAPE OPEN`` con expected/actual
    JSON, **NO sobreescribe** el baseline (D-25), retorna FINDING con fid.

    Phase 39: el archivo se elige por ``(func_name, venue)`` vía :func:`_schema_path`,
    no sólo por nombre de función. ``base_url`` sigue registrándose DENTRO del sobre
    —ahora además es parte de la clave del nombre, lo que hace el artefacto
    autoconsistente—. La política D-25 no cambia.

    Returns ``(status, detail)`` donde ``status`` es ``"PASS"`` o ``"FINDING"``.
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
    file_path = _schema_path(func_name, base_url)
    if not file_path.exists():
        file_path.write_text(
            json.dumps(envelope, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return ("PASS", f"escrito {file_path.name}")
    committed = json.loads(file_path.read_text(encoding="utf-8"))
    if committed.get("schema") == actual_schema:
        return ("PASS", f"{file_path.name} sin drift")
    # HARN-01 / D-01 ENMENDADA: dedupe intra-proceso. La identidad es
    # ``file_path.name`` y NO ``func_name`` porque desde la Phase 39 el baseline
    # se elige por ``(func_name, venue)`` vía ``_schema_path()``: con ``func_name``
    # a secas, dos drifts de venues distintos que casualmente compartieran
    # ``actual_schema`` colapsarían pese a tener ``expected`` distintos — pérdida
    # de censo. El digest cubre el PAR baseline-vs-actual por la misma razón.
    drift_key = (file_path.name, _drift_digest([committed.get("schema"), actual_schema]))
    if drift_key in _seen_drift_keys:
        # No-op con el contrato de ESTE helper: ``tuple[str, str]``. Un ``return``
        # desnudo devolvería ``None`` y el caller hace ``status, detail = ...``.
        # El detalle NO puede empezar con ``escrito``: el caller lo contaría como
        # baseline recién escrito.
        return ("PASS", f"{file_path.name} drift ya reportado en esta corrida")
    _seen_drift_keys.add(drift_key)
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title=f"Schema drift en {func_name}",
        expected=json.dumps(committed.get("schema"), ensure_ascii=False),
        actual=json.dumps(actual_schema, ensure_ascii=False),
        diff="comparar expected vs actual; NO se sobreescribe baseline (D-25)",
        base_url=base_url,
    )
    return ("FINDING", f"{fid}|{file_path.name}")


# ---------------------------------------------------------------------------
# CR-05 close (Phase 7 Plan 5 / D-07 / Pitfall 5):
# `_envelope_probe` dedupea los ~13 envelope probes "limpios" + 2 risk probes.
#
# Phase 37 code review CR-01: las 2 risk probes pasaban `envelope_key=None` bajo
# el claim D-07 "el payload raíz ES el resultado". El vendor doc lo falsifica
# (`documentation/Primary-API.md:1701-1703` y `:1817-1819` muestran los bodies
# envueltos en `detailedPosition` / `accountData`) y 37-01 ya había corregido
# `_core.parse_get_detailed_positions_response` / `parse_get_account_report_response`
# para desenvolver — pero el driver se quedó con la creencia vieja, así que
# alimentaba a `diff_safemodel_bidirectional` con el envelope crudo y habría
# fabricado una tanda de findings SHAPE "model declara, wire no emite". El
# parámetro `envelope_key` es ahora REQUERIDO (`str`, sin default) y la rama
# `None` fue eliminada: la ausencia de la rama es lo que impide que la creencia
# vuelva. Lock: `verification/test_main_matriz_risk_envelope_keys.py`.
#
# Las 3 probes con side-effect / lógica especial
# (`probe_get_segments` setea `_resolved_segment`; `probe_get_all_instruments`
# setea `_resolved_symbol`; `probe_get_market_data` tiene market-hours guard)
# permanecen custom — A4 honesty flag. `probe_get_instruments_by_cfi_sanity`
# (loop sobre 8 CFI codes) tampoco encaja en el helper plano.
# ---------------------------------------------------------------------------


def _sync_matriz_request(
    client: Client,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    auth_basic: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """Raw envelope request sobre el ``Client`` threadeado, semántica del shim legacy.

    Replica byte-por-byte el comportamiento del antiguo module shim
    ``matriz_client.client._request`` (que el driver usaba para capturar el raw
    envelope-parsed payload, y que delegaba en el cached default-client del
    paquete vía su ``_matriz_legacy_request`` — el camino singleton que esta
    migración 15-05 cierra): construye un ``RequestSpec``, llama al
    ``Client._request`` de instancia (que devuelve el ``httpx.Response`` crudo SIN
    levantar a nivel app), y delega el parseo + raise-on-error a
    ``parse_envelope_response`` (D-24: ``status='ERROR'`` → ``PrimaryAPIError``;
    401 Risk → ``AuthenticationError`` ya desde ``_request``). Misma firma y
    mismo return shape (``dict[str, Any]`` envelope) que el shim módulo-level.

    Mirror del idiom ``_raw_request_sync`` de ``main_higyrus.py`` adaptado al
    ``parse_envelope_response`` de matriz. Mantiene exactamente UN ``Client``: el
    threadeado desde ``main()`` (TokenStore-safe — sin segundo login remarkets).
    """
    spec = RequestSpec(method=method, path=path, params=params, auth_basic=auth_basic)
    resp = client._request(spec)
    return parse_envelope_response(resp, path)


def _envelope_probe(
    client: Client,
    name: str,
    path: str,
    *,
    envelope_key: str,
    request_params: dict[str, Any] | None = None,
    auth_basic_fn: Callable[[], tuple[str, str]] | None = None,
    pass_detail: Callable[[Any], str] | None = None,
) -> tuple[ProbeResult, Any | None]:
    """Sweep probe helper — CR-05 close.

    Args:
        client: The single threaded sync ``Client`` from ``main()`` (15-05
            single-Client migration; routes through ``_sync_matriz_request``
            instead of the module singleton shim).
        name: ProbeResult label.
        path: REST path (e.g. ``/rest/segment/all``).
        envelope_key: Envelope key to unwrap. **Requerido** — Phase 37 code
            review CR-01: no hay endpoint sin envelope. Las 2 risk probes
            (``detailedPosition`` / ``accountData``) pasaban ``None`` bajo un
            claim D-07 que el vendor doc falsifica
            (``documentation/Primary-API.md:1701-1703``, ``:1817-1819``); el
            parámetro ya no admite ``None`` para que la creencia no pueda volver.
        request_params: Forwarded to ``_sync_matriz_request(client, "GET", path,
            params=...)``.
        auth_basic_fn: Returns ``(user, pass)`` for Risk API HTTP Basic; ``None``
            usa el token X-Auth-Token cacheado.
        pass_detail: Optional callable que mapea ``payload -> str`` para
            personalizar el ``ProbeResult.detail`` en el camino PASS.

    Returns:
        ``(ProbeResult, raw_payload_or_None)`` — misma shape que las 18 probes pre-refactor.
    """
    # WR-04 fix Phase 7 review: el cascade SKIPPED por _auth_failed sólo aplica
    # a probes que dependen del token X-Auth-Token. Risk probes con auth_basic_fn
    # usan credenciales HTTP Basic independientes del token, así que NO se las
    # debería skipear si la auth del token falló — podrían ser ejecutables.
    if _auth_failed and auth_basic_fn is None:
        return (ProbeResult(name, "SKIPPED", f"auth failed: {_auth_failure_reason}"), None)
    base_url = primary.client._base_url
    auth = auth_basic_fn() if auth_basic_fn is not None else None
    try:
        raw = _sync_matriz_request(client, "GET", path, params=request_params, auth_basic=auth)
    except PrimaryAPIError as exc:
        fid = _next_fid()
        expected = f"200 OK con envelope {{{envelope_key}: ...}}"
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"{name} levantó PrimaryAPIError inesperado",
            expected=expected,
            actual=f"PrimaryAPIError: {exc}",
            diff="error upstream o envelope key ausente / status='ERROR'",
            base_url=base_url,
        )
        return (ProbeResult(name, "FINDING", f"{fid} (OPEN)"), None)
    # Envelope probe: unwrap key, validate shape (list o dict según el endpoint).
    payload = raw.get(envelope_key)
    # Para single-resource envelopes (instrument, order, marketData), `payload` es dict;
    # para list envelopes (instruments, segments, orders, trades, positions), es list.
    # Phase 37 code review CR-01: las 2 risk probes también son single-resource
    # — `detailedPosition` y `accountData` envuelven un dict, no una lista.
    expected_dict = name in {
        "get_instrument_detail",
        "get_order_status",
        "get_order_by_exec_id",
        "get_detailed_positions",
        "get_account_report",
    }
    if expected_dict:
        if not isinstance(payload, dict):
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="SHAPE",
                surface="sync",
                status="OPEN",
                title=f"{name} envelope shape incorrecto",
                expected=f"raw['{envelope_key}'] es dict",
                actual=f"raw['{envelope_key}']={type(payload).__name__}",
                diff=f"envelope key '{envelope_key}' ausente o no-dict",
                base_url=base_url,
            )
            return (ProbeResult(name, "FINDING", f"{fid} (OPEN)"), None)
        detail = pass_detail(payload) if pass_detail is not None else "received"
        return (ProbeResult(name, "PASS", detail), payload)
    # List envelope.
    if not isinstance(payload, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title=f"{name} envelope shape incorrecto",
            expected=f"raw['{envelope_key}'] es list",
            actual=f"raw['{envelope_key}']={type(payload).__name__}",
            diff=f"envelope key '{envelope_key}' ausente o no-list",
            base_url=base_url,
        )
        return (ProbeResult(name, "FINDING", f"{fid} (OPEN)"), None)
    detail = pass_detail(payload) if pass_detail is not None else f"{len(payload)} items"
    return (ProbeResult(name, "PASS", detail), payload)


# ---------------------------------------------------------------------------
# Probe 1: login_sync (D-MATZ-29 #1, MATZ-01)
# ---------------------------------------------------------------------------


@probe_context(
    endpoint="/auth/getToken",
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
def probe_login_sync(client: Client) -> ProbeResult:
    """Probe 1: ``client.login()`` sync (MATZ-01).

    Setea ``_auth_failed`` global si la auth falla — activa cascade SKIPPED
    en todos los downstream (D-MATZ-31). Distingue ``AuthenticationError``
    (esperable si credenciales inválidas) de ``Exception`` inesperada (transport
    / network — emite finding ERROR-MAP OPEN).
    """
    global _auth_failed, _auth_failure_reason
    base_url = client._state.base_url
    t0 = time.monotonic()
    try:
        client.login()
    except AuthenticationError as exc:
        _auth_failed = True
        _auth_failure_reason = f"AuthenticationError: {exc}"
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="login() sync falló (AuthenticationError)",
            expected="login() retorna token válido y obtiene X-Auth-Token header",
            actual=f"AuthenticationError: {exc}",
            diff="verificar PRIMARY_USER/PRIMARY_PASSWORD; revisar headers de respuesta",
            base_url=base_url,
        )
        # Phase 11 CR-02: 'FINDING' (was 'FAIL') for uniformity with the rest
        # of the driver taxonomy (e.g. ERROR-MAP probes use 'FINDING' on the
        # equivalent diagnostic path).
        return ProbeResult("login_sync", "FINDING", f"{fid} (OPEN): AuthenticationError")
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        _auth_failed = True
        _auth_failure_reason = f"{type(exc).__name__}: {exc}"
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"login() sync levantó {type(exc).__name__} no mapeado",
            expected="AuthenticationError o éxito; transporte mapeado a tipo conocido",
            actual=f"{type(exc).__name__}: {exc}",
            diff="excepción no es subclase de AuthenticationError; revisar mapping",
            base_url=base_url,
        )
        # Phase 11 CR-02: 'FINDING' (was 'FAIL') for uniformity with the rest
        # of the driver taxonomy.
        return ProbeResult("login_sync", "FINDING", f"{fid} (OPEN): {type(exc).__name__}")
    duration = time.monotonic() - t0
    return ProbeResult("login_sync", "PASS", f"token obtenido en {duration:.2f}s")


# ---------------------------------------------------------------------------
# Probes 2-19: read-sweep (D-MATZ-29 #2-#19, MATZ-02)
#
# Cada probe retorna ``(ProbeResult, raw_payload | None)``. El raw_payload es
# el dict/lista crudo retornado por ``_sync_matriz_request`` sobre el ``Client``
# threadeado (envelope ya extraído) para uso downstream por
# ``probe_field_type_map`` y ``probe_schema_snapshot``.
# ---------------------------------------------------------------------------


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_segments"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_segments(client: Client) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 2 (D-MATZ-29 #2): ``GET /rest/segment/all``.

    Setea ``_resolved_segment`` = ``segments[0].marketSegmentId`` (D-MATZ-2).
    """
    global _resolved_segment
    if _auth_failed:
        return (
            ProbeResult("get_segments", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/segment/all"
    try:
        raw = _sync_matriz_request(client, "GET", path)
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_segments levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {segments: [...]}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_segments", "FINDING", f"{fid} (OPEN)"), None)
    segments = raw.get("segments")
    if not isinstance(segments, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_segments envelope shape incorrecto",
            expected="raw['segments'] es list",
            actual=f"raw['segments']={type(segments).__name__}",
            diff="envelope key 'segments' ausente o no-list",
            base_url=base_url,
        )
        return (ProbeResult("get_segments", "FINDING", f"{fid} (OPEN)"), None)
    if segments and isinstance(segments[0], dict):
        seg_id = segments[0].get("marketSegmentId")
        if isinstance(seg_id, str):
            _resolved_segment = seg_id
    return (ProbeResult("get_segments", "PASS", f"{len(segments)} segments"), segments)


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_all_instruments"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_all_instruments(client: Client) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 3 (D-MATZ-29 #3): ``GET /rest/instruments/all``.

    Setea ``_resolved_symbol`` = ``instruments[0].instrumentId.symbol`` (D-MATZ-1).
    Si ``MATRIZ_SAMPLE_SYMBOL`` está presente, lo usa como override.
    """
    global _resolved_symbol
    if _auth_failed:
        return (
            ProbeResult("get_all_instruments", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/instruments/all"
    try:
        raw = _sync_matriz_request(client, "GET", path)
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_all_instruments levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {instruments: [...]}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_all_instruments", "FINDING", f"{fid} (OPEN)"), None)
    instruments = raw.get("instruments")
    if not isinstance(instruments, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_all_instruments envelope shape incorrecto",
            expected="raw['instruments'] es list",
            actual=f"raw['instruments']={type(instruments).__name__}",
            diff="envelope key 'instruments' ausente o no-list",
            base_url=base_url,
        )
        return (ProbeResult("get_all_instruments", "FINDING", f"{fid} (OPEN)"), None)
    if _SAMPLE_SYMBOL:
        _resolved_symbol = _SAMPLE_SYMBOL
    elif instruments and isinstance(instruments[0], dict):
        iid = instruments[0].get("instrumentId")
        if isinstance(iid, dict):
            sym = iid.get("symbol")
            if isinstance(sym, str):
                _resolved_symbol = sym
    return (
        ProbeResult("get_all_instruments", "PASS", f"{len(instruments)} instruments"),
        instruments,
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_instruments_details"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_instruments_details(
    client: Client,
) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 4 (D-MATZ-29 #4): ``GET /rest/instruments/details`` — vía ``_envelope_probe``."""
    return _envelope_probe(
        client,
        "get_instruments_details",
        "/rest/instruments/details",
        envelope_key="instruments",
        pass_detail=lambda p: f"{len(p)} instrument details",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_instrument_detail"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_instrument_detail(client: Client) -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 5 (D-MATZ-29 #5): ``GET /rest/instruments/detail`` con ``_resolved_symbol``.

    SKIPPED si ``_resolved_symbol`` no se resolvió (probe #3 falló o instruments vacío).
    """
    if _resolved_symbol is None and not _auth_failed:
        return (
            ProbeResult("get_instrument_detail", "SKIPPED", "no _resolved_symbol from probe #3"),
            None,
        )
    return _envelope_probe(
        client,
        "get_instrument_detail",
        "/rest/instruments/detail",
        envelope_key="instrument",
        request_params={"symbol": _resolved_symbol, "marketId": "ROFX"},
        pass_detail=lambda _: f"symbol={_resolved_symbol}",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_instruments_by_cfi_ESXXXX"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_instruments_by_cfi_ESXXXX(
    client: Client,
) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 6 (D-MATZ-29 #6): ``GET /rest/instruments/byCFICode`` con ``CFICode='ESXXXX'``.

    Baseline para schema snapshot D-MATZ-6 (los otros 8 CFI van por probe #7).
    """
    return _envelope_probe(
        client,
        "get_instruments_by_cfi_ESXXXX",
        "/rest/instruments/byCFICode",
        envelope_key="instruments",
        request_params={"CFICode": "ESXXXX"},
        pass_detail=lambda p: f"{len(p)} ESXXXX instruments",
    )


# D-MATZ-6: 8 CFI restantes para sanity sweep (type-only, sin snapshot por cada uno).
_CFI_SANITY_CODES: tuple[CFICode, ...] = (
    "DBXXXX",
    "OCASPS",
    "OPASPS",
    "FXXXSX",
    "OPAFXS",
    "OCAFXS",
    "EMXXXX",
    "DBXXFR",
)


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_instruments_by_cfi_ESXXXX"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_instruments_by_cfi_sanity(client: Client) -> tuple[ProbeResult, None]:
    """Probe 7 (D-MATZ-29 #7): sanity sweep de los 8 CFI codes restantes.

    Type-only assertions (sin snapshot por cada uno per D-MATZ-6). Si CUALQUIER
    CFI falla shape → finding SHAPE OPEN.
    """
    if _auth_failed:
        return (
            ProbeResult(
                "get_instruments_by_cfi_sanity",
                "SKIPPED",
                f"auth failed: {_auth_failure_reason}",
            ),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/instruments/byCFICode"
    failures: list[str] = []
    counts: dict[str, int] = {}
    for cfi in _CFI_SANITY_CODES:
        try:
            raw = _sync_matriz_request(client, "GET", path, params={"CFICode": cfi})
        except PrimaryAPIError as exc:
            failures.append(f"{cfi}:PrimaryAPIError({exc})")
            continue
        instruments = raw.get("instruments")
        if not isinstance(instruments, list):
            failures.append(f"{cfi}:envelope-not-list")
            continue
        if instruments and not isinstance(instruments[0], dict):
            failures.append(f"{cfi}:first-not-dict")
            continue
        counts[cfi] = len(instruments)
    if failures:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="CFI sanity sweep: shape failures en sub-set de codes",
            expected="cada CFI retorna envelope {instruments: [dict, ...]}",
            actual=f"failures: {', '.join(failures)}",
            diff="ver lista de codes que fallaron shape",
            base_url=base_url,
        )
        return (
            ProbeResult("get_instruments_by_cfi_sanity", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    detail = ", ".join(f"{c}={n}" for c, n in counts.items())
    return (ProbeResult("get_instruments_by_cfi_sanity", "PASS", detail), None)


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_instruments_by_segment"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_instruments_by_segment(
    client: Client,
) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 8 (D-MATZ-29 #8): ``GET /rest/instruments/bySegment`` con ``_resolved_segment``.

    SKIPPED si ``_resolved_segment`` no se resolvió (probe #2 falló o segments vacío).
    """
    if _resolved_segment is None and not _auth_failed:
        return (
            ProbeResult(
                "get_instruments_by_segment", "SKIPPED", "no _resolved_segment from probe #2"
            ),
            None,
        )
    return _envelope_probe(
        client,
        "get_instruments_by_segment",
        "/rest/instruments/bySegment",
        envelope_key="instruments",
        request_params={"MarketSegmentID": _resolved_segment, "MarketID": "ROFX"},
        pass_detail=lambda p: f"segment={_resolved_segment}: {len(p)} instruments",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_market_data"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_market_data(client: Client) -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 9 (D-MATZ-29 #9): ``GET /rest/marketdata/get`` con ``_resolved_symbol``.

    D-MATZ-5 market-hours guard: inspecciona ``LA.date`` (epoch ms). Si stale > 2h
    respecto a ``time.time() * 1000`` → finding NO-DATA OPEN + PASS-shape (no
    asserts de valor, solo shape/type/presence). Si ``LA`` o ``date`` ausente,
    se trata como PASS-shape (no fail) — segments cerrados pueden no emitir LA.
    """
    if _auth_failed:
        return (
            ProbeResult("get_market_data", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    if _resolved_symbol is None:
        return (
            ProbeResult("get_market_data", "SKIPPED", "no _resolved_symbol from probe #3"),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/marketdata/get"
    entries = "BI,OF,LA,OP,CL,SE,OI"
    try:
        raw = _sync_matriz_request(
            client,
            "GET",
            path,
            params={
                "marketId": "ROFX",
                "symbol": _resolved_symbol,
                "entries": entries,
            },
        )
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_market_data levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {marketData: {...}}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_market_data", "FINDING", f"{fid} (OPEN)"), None)
    md = raw.get("marketData")
    if not isinstance(md, dict):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_market_data envelope shape incorrecto",
            expected="raw['marketData'] es dict",
            actual=f"raw['marketData']={type(md).__name__}",
            diff="envelope key 'marketData' ausente o no-dict",
            base_url=base_url,
        )
        return (ProbeResult("get_market_data", "FINDING", f"{fid} (OPEN)"), None)
    # ------------------------------------------------------------------
    # D-05: gastar los SEIS alias de `MarketDataSnapshot` (Phase 37 / NOBJ-MTZ-02).
    # ------------------------------------------------------------------
    #
    # El snapshot se construye sobre el sub-dict `marketData` YA obtenido: CERO
    # llamadas HTTP adicionales. `MarketDataSnapshot.from_api` es exactamente el
    # constructor que `_core.parse_get_market_data_response` invoca sobre este mismo
    # sub-dict, así que enruta por el mismo walker, el mismo sink y el mismo contexto
    # de decode estricto que el parser del cliente: la construcción emite exactamente
    # los registros que la función tipada habría emitido, gratis. Un segundo round
    # trip al endpoint tipado duplicaría el request del concepto market-data y la
    # emisión de divergencias; `verification/test_main_matriz_deep_chain.py` lo
    # prohíbe por AST.
    #
    # Los seis alias son propiedades de SÓLO LECTURA, invisibles a
    # `typing.get_type_hints` y a `dataclasses.fields` (Phase 35 criterio 5, D-16) y
    # por lo tanto invisibles a `_decode.walk_model`: desreferenciarlas NO agrega
    # camino de decode y NO puede fabricar un `missing` ni mover el conteo de
    # divergencias. El censo NO debe atribuirle a esta cadena un cambio de números que
    # estructuralmente no puede causar.
    #
    # Con entradas ausentes o `null` cada Null Object es falsy y ninguna
    # desreferencia lanza — la semántica de borde está pinneada por la suite mockeada
    # `packages/matriz-client/tests/test_deep_chain_edges.py` (plan 39-02).
    #
    # `MatrizDecodeError` NO se captura acá a propósito: no es subclase de nada en
    # `_RESIDUAL_PROBE_EXCEPTIONS`, así que un raise de modo estricto desde `from_api`
    # sigue viajando al decorador `probe_context(..., on_decode_error=...)` y produce
    # el finding SHAPE de siempre, sin doble emisión bajo otro título.
    try:
        snapshot = MarketDataSnapshot.from_api(md)
        last_price = snapshot.last.price
        bid_levels = len(snapshot.bids)
        offer_levels = len(snapshot.offers)
        settlement_price = snapshot.settlement.price
        close_price = snapshot.close.price
        open_interest_size = snapshot.open_interest.size
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"get_market_data: la cadena tipada levantó {type(exc).__name__}",
            expected="los 6 alias de MarketDataSnapshot desreferenciables sin excepción",
            actual=f"{type(exc).__name__}: {exc}",
            diff="eslabón roto en MarketDataSnapshot -> MarketDataEntryValue/MarketDataLevel",
            base_url=base_url,
        )
        return (ProbeResult("get_market_data", "FINDING", f"{fid} (OPEN)"), md)
    chain = (
        f"last={last_price} bids={bid_levels} offers={offer_levels} "
        f"settlement={settlement_price} close={close_price} oi={open_interest_size}"
    )
    # D-MATZ-5 market-hours guard: inspecciona LA.date.
    #
    # D-12: la guarda de antigüedad de `LA.date` sigue siendo el ÚNICO discriminador
    # entre "mercado cerrado" y "campo mal modelado". Los valores de la cadena de
    # arriba se REPORTAN, nunca se usan para clasificar.
    la = md.get("LA")
    detail = f"symbol={_resolved_symbol}, entries={len(md)}, {chain}"
    if isinstance(la, dict):
        la_date = la.get("date")
        if isinstance(la_date, int):
            now_ms = int(time.time() * 1000)
            stale_ms = now_ms - la_date
            if stale_ms > 7200000:  # 2h
                fid = _next_fid()
                stale_h = stale_ms / 3600000
                append_finding(
                    _PKG,
                    fid=fid,
                    class_="NO-DATA",
                    surface="sync",
                    status="OPEN",
                    title="market-hours: LA.date stale > 2h (segment cerrado o sin trades)",
                    expected="LA.date dentro de las últimas 2h durante market-hours",
                    actual=f"LA.date stale by {stale_h:.1f}h",
                    diff="run-time vs LA.date; shape OK, value asserts skipped",
                    base_url=base_url,
                )
                detail = f"{detail} (stale LA.date by {stale_h:.1f}h — shape OK)"
    return (ProbeResult("get_market_data", "PASS", detail), md)


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_trades"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_trades(client: Client) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 10 (D-MATZ-29 #10): ``GET /rest/data/getTrades`` con ``date_from=today-7d``.

    D-MATZ-8: si lista vacía → finding NO-DATA OPEN + PASS-shape (reportado por
    el caller pre-_envelope_probe; el helper sólo cubre el envelope happy path).
    """
    if _resolved_symbol is None and not _auth_failed:
        return (ProbeResult("get_trades", "SKIPPED", "no _resolved_symbol from probe #3"), None)
    today = dt.date.today()
    seven_days_ago = today - dt.timedelta(days=7)
    result, payload = _envelope_probe(
        client,
        "get_trades",
        "/rest/data/getTrades",
        envelope_key="trades",
        request_params={
            "marketId": "ROFX",
            "symbol": _resolved_symbol,
            "dateFrom": seven_days_ago.isoformat(),
            "dateTo": today.isoformat(),
        },
        pass_detail=lambda p: f"{len(p)} trades" if p else "empty trades",
    )
    # D-MATZ-8 NO-DATA finding solo aplica si el helper devolvió PASS con lista vacía.
    if result.status == "PASS" and isinstance(payload, list) and not payload:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="NO-DATA",
            surface="sync",
            status="OPEN",
            title=f"no trades for {_resolved_symbol} in last 7 days",
            expected="al menos 1 trade en ventana de 7 días (símbolo líquido)",
            actual="trades list vacía",
            diff="símbolo ilíquido o ventana sin actividad",
            base_url=primary.client._base_url,
        )
        result = ProbeResult("get_trades", "PASS", f"empty trades ({fid} NO-DATA)")
    return (result, payload)


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_active_orders"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_active_orders(client: Client) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 11 (D-MATZ-29 #11): ``GET /rest/order/actives`` con ``PRIMARY_ACCOUNT``."""
    if _PRIMARY_ACCOUNT is None and not _auth_failed:
        return (ProbeResult("get_active_orders", "SKIPPED", "no PRIMARY_ACCOUNT env var"), None)
    return _envelope_probe(
        client,
        "get_active_orders",
        "/rest/order/actives",
        envelope_key="orders",
        request_params={"accountId": _PRIMARY_ACCOUNT},
        pass_detail=lambda p: f"{len(p)} active orders",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_filled_orders"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_filled_orders(client: Client) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 12 (D-MATZ-29 #12): ``GET /rest/order/filleds`` con ``PRIMARY_ACCOUNT``."""
    if _PRIMARY_ACCOUNT is None and not _auth_failed:
        return (ProbeResult("get_filled_orders", "SKIPPED", "no PRIMARY_ACCOUNT env var"), None)
    return _envelope_probe(
        client,
        "get_filled_orders",
        "/rest/order/filleds",
        envelope_key="orders",
        request_params={"accountId": _PRIMARY_ACCOUNT},
        pass_detail=lambda p: f"{len(p)} filled orders",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_all_orders"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_all_orders(client: Client) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 13 (D-MATZ-29 #13): ``GET /rest/order/all`` con ``PRIMARY_ACCOUNT``."""
    if _PRIMARY_ACCOUNT is None and not _auth_failed:
        return (ProbeResult("get_all_orders", "SKIPPED", "no PRIMARY_ACCOUNT env var"), None)
    return _envelope_probe(
        client,
        "get_all_orders",
        "/rest/order/all",
        envelope_key="orders",
        request_params={"accountId": _PRIMARY_ACCOUNT},
        pass_detail=lambda p: f"{len(p)} total orders",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_order_status"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_order_status(client: Client) -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 14 (D-MATZ-29 #14): ``GET /rest/order/id`` con ``cl_ord_id``+``proprietary``."""
    if (_SAMPLE_CL_ORD_ID is None or _SAMPLE_PROPRIETARY is None) and not _auth_failed:
        return (
            ProbeResult(
                "get_order_status",
                "SKIPPED",
                "no MATRIZ_SAMPLE_CL_ORD_ID / MATRIZ_SAMPLE_PROPRIETARY env vars",
            ),
            None,
        )
    return _envelope_probe(
        client,
        "get_order_status",
        "/rest/order/id",
        envelope_key="order",
        request_params={"clOrdId": _SAMPLE_CL_ORD_ID, "proprietary": _SAMPLE_PROPRIETARY},
        pass_detail=lambda _: f"clOrdId={_SAMPLE_CL_ORD_ID}",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_order_history"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_order_history(client: Client) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 15 (D-MATZ-29 #15): ``GET /rest/order/allById`` con ``cl_ord_id``+``proprietary``."""
    if (_SAMPLE_CL_ORD_ID is None or _SAMPLE_PROPRIETARY is None) and not _auth_failed:
        return (
            ProbeResult(
                "get_order_history",
                "SKIPPED",
                "no MATRIZ_SAMPLE_CL_ORD_ID / MATRIZ_SAMPLE_PROPRIETARY env vars",
            ),
            None,
        )
    return _envelope_probe(
        client,
        "get_order_history",
        "/rest/order/allById",
        envelope_key="orders",
        request_params={"clOrdId": _SAMPLE_CL_ORD_ID, "proprietary": _SAMPLE_PROPRIETARY},
        pass_detail=lambda p: f"{len(p)} history rows",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_order_by_exec_id"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_order_by_exec_id(client: Client) -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 16 (D-MATZ-29 #16): ``GET /rest/order/byExecId`` con ``MATRIZ_SAMPLE_EXEC_ID``."""
    if _SAMPLE_EXEC_ID is None and not _auth_failed:
        return (
            ProbeResult("get_order_by_exec_id", "SKIPPED", "no MATRIZ_SAMPLE_EXEC_ID env var"),
            None,
        )
    return _envelope_probe(
        client,
        "get_order_by_exec_id",
        "/rest/order/byExecId",
        envelope_key="order",
        request_params={"execId": _SAMPLE_EXEC_ID},
        pass_detail=lambda _: f"execId={_SAMPLE_EXEC_ID}",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_positions"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_positions(client: Client) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 17 (D-MATZ-29 #17): ``GET /rest/risk/position/getPositions/{account}``.

    **Risk API HTTP Basic Auth** (Pitfall 2 RESEARCH L640): el helper acepta
    ``auth_basic_fn``. SKIPPED si ``PRIMARY_ACCOUNT`` ausente (D-MATZ-3).
    """
    if _PRIMARY_ACCOUNT is None and not _auth_failed:
        return (ProbeResult("get_positions", "SKIPPED", "no PRIMARY_ACCOUNT env var"), None)
    return _envelope_probe(
        client,
        "get_positions",
        f"/rest/risk/position/getPositions/{_PRIMARY_ACCOUNT}",
        envelope_key="positions",
        auth_basic_fn=client._risk_auth,
        pass_detail=lambda p: f"{len(p)} positions",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_detailed_positions"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_detailed_positions(client: Client) -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 18 (D-MATZ-29 #18): ``GET /rest/risk/detailedPosition/{account}``.

    Risk API HTTP Basic Auth. **Envelope key ``detailedPosition``**
    (``documentation/Primary-API.md:1701-1703``), igual que ya desenvuelve
    ``_core.parse_get_detailed_positions_response`` desde 37-01 (D-03,
    ``strict-unwrap``). El claim previo de esta docstring — "SIN envelope key
    (D-07), el payload raíz es el dict completo" — lo falsifica el vendor doc; el
    code review de la Phase 37 (CR-01) lo encontró sobreviviendo acá después de
    que 37-01 lo corrigiera en el cliente. Sin este fix el driver alimentaba a
    ``diff_safemodel_bidirectional`` (probe 20) con el envelope crudo.
    SKIPPED si ``PRIMARY_ACCOUNT`` ausente (D-MATZ-3).
    """
    if _PRIMARY_ACCOUNT is None and not _auth_failed:
        return (
            ProbeResult("get_detailed_positions", "SKIPPED", "no PRIMARY_ACCOUNT env var"),
            None,
        )
    return _envelope_probe(
        client,
        "get_detailed_positions",
        f"/rest/risk/detailedPosition/{_PRIMARY_ACCOUNT}",
        envelope_key="detailedPosition",
        auth_basic_fn=client._risk_auth,
        # WR-01: no insertamos accountId completo en detail string.
        pass_detail=lambda _: "account received",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_account_report"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result_pair,
)
def probe_get_account_report(client: Client) -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 19 (D-MATZ-29 #19): ``GET /rest/risk/accountReport/{account}``.

    Risk API HTTP Basic Auth. **Envelope key ``accountData``**
    (``documentation/Primary-API.md:1817-1819``), igual que ya desenvuelve
    ``_core.parse_get_account_report_response`` desde 37-01 (D-03,
    ``strict-unwrap``). Gemelo exacto de ``probe_get_detailed_positions``: mismo
    claim D-07 previo, misma falsificación por el vendor doc, mismo hallazgo del
    code review de la Phase 37 (CR-01).
    SKIPPED si ``PRIMARY_ACCOUNT`` ausente (D-MATZ-3).
    """
    if _PRIMARY_ACCOUNT is None and not _auth_failed:
        return (
            ProbeResult("get_account_report", "SKIPPED", "no PRIMARY_ACCOUNT env var"),
            None,
        )
    return _envelope_probe(
        client,
        "get_account_report",
        f"/rest/risk/accountReport/{_PRIMARY_ACCOUNT}",
        envelope_key="accountData",
        auth_basic_fn=client._risk_auth,
        # WR-01: no insertamos accountName real en detail string.
        pass_detail=lambda _: "accountName received",
    )


# ---------------------------------------------------------------------------
# Probe 20: field_type_map (D-MATZ-29 #20, MATZ-03)
# ---------------------------------------------------------------------------


@probe_context(
    endpoint="-",
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
def probe_field_type_map(payloads: dict[str, Any]) -> ProbeResult:
    """Probe 20 (D-MATZ-29 #20, MATZ-03): bidirectional SafeModel<->wire diff.

    Itera los 9 modelos ``_SafeModel`` sampleables desde payloads acumulados
    usando ``diff_safemodel_bidirectional`` (helper promovido en Plan 05-01).
    Por cada divergencia ``model-only`` (FALSE PASS riesgo) o ``wire-only``
    (info) emite finding ``SHAPE OPEN``. NewOrderResponse queda cubierto por
    mock-only en Plan 05-03; los nested se cubren recursivamente.
    """
    if _auth_failed:
        return ProbeResult("field_type_map", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = primary.client._base_url
    # Phase 11 CR-04: pasar fname= a _first_dict para que el wrong_type case
    # emita un finding SHAPE OPEN en vez de colapsar silenciosamente con no_data.
    targets: list[tuple[str, Any, type]] = [
        ("segment", _first_dict(payloads.get("get_segments"), fname="get_segments"), Segment),
        (
            "instrument",
            _first_dict(payloads.get("get_all_instruments"), fname="get_all_instruments"),
            Instrument,
        ),
        ("instrument_detail", payloads.get("get_instrument_detail"), InstrumentDetail),
        ("market_data", payloads.get("get_market_data"), MarketDataSnapshot),
        ("trade", _first_dict(payloads.get("get_trades"), fname="get_trades"), Trade),
        ("order", _first_dict(payloads.get("get_all_orders"), fname="get_all_orders"), Order),
        ("position", _first_dict(payloads.get("get_positions"), fname="get_positions"), Position),
        ("detailed_position", payloads.get("get_detailed_positions"), DetailedPosition),
        ("account_report", payloads.get("get_account_report"), AccountReport),
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
                surface="sync",
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
    return ProbeResult("field_type_map", "PASS", "9 models, 0 divergences")


# ---------------------------------------------------------------------------
# Probes 21-23: error probes always-on (D-MATZ-29 #21-#23, MATZ-05)
#
# D-MATZ-22 strings literales: 'ZZZZZZ-NOT-A-SYMBOL', 'INVALID-ACCT-XXXXX',
# 'INVALID-CFI'. D-MATZ-23: distinción HTTP 4xx no-mapeado (finding ERROR-MAP
# OPEN) vs status='ERROR' mapeado (PASS).
# ---------------------------------------------------------------------------


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_market_data"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
def probe_error_bogus_symbol(client: Client) -> ProbeResult:
    """Probe 21 (D-MATZ-29 #21): símbolo inválido en ``get_market_data``.

    Distingue ``PrimaryAPIError(status='ERROR')`` mapeado (PASS) de
    ``httpx.HTTPStatusError`` HTTP 4xx no-mapeado (finding ERROR-MAP OPEN).
    """
    if _auth_failed:
        return ProbeResult("error_bogus_symbol", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = client._state.base_url
    try:
        client.get_market_data("ZZZZZZ-NOT-A-SYMBOL")
    except PrimaryAPIError as exc:
        if exc.status == "ERROR":
            return ProbeResult(
                "error_bogus_symbol", "PASS", f"PrimaryAPIError as expected: {exc.description}"
            )
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="bogus symbol: PrimaryAPIError con status != 'ERROR'",
            expected="PrimaryAPIError(status='ERROR') al pasar símbolo inválido",
            actual=f"PrimaryAPIError(status={exc.status!r}): {exc}",
            diff="status no es 'ERROR'; revisar mapping de error",
            base_url=base_url,
        )
        return ProbeResult("error_bogus_symbol", "FINDING", f"{fid} (OPEN)")
    except httpx.HTTPStatusError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="bogus symbol: HTTP 4xx no mapeado a PrimaryAPIError",
            expected="PrimaryAPIError mapeado para símbolo inválido",
            actual=f"HTTPStatusError {exc.response.status_code}: {exc}",
            diff="upstream devolvió 4xx en lugar de status='ERROR' en payload",
            base_url=base_url,
        )
        return ProbeResult("error_bogus_symbol", "FINDING", f"{fid} (OPEN)")
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"bogus symbol: unexpected {type(exc).__name__}",
            expected="PrimaryAPIError mapeado para símbolo inválido",
            actual=f"{type(exc).__name__}: {exc}",
            diff="excepción inesperada; revisar mapping",
            base_url=base_url,
        )
        return ProbeResult("error_bogus_symbol", "FINDING", f"{fid} (OPEN)")
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="ERROR-MAP",
        surface="sync",
        status="OPEN",
        title="get_market_data con símbolo inválido NO levantó excepción",
        expected="PrimaryAPIError mapeado para símbolo inválido",
        actual="ninguna excepción; el cliente retornó normalmente",
        diff="upstream devolvió 200 OK con shape válida pero data inexistente",
        base_url=base_url,
    )
    return ProbeResult("error_bogus_symbol", "FINDING", f"{fid} (OPEN)")


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_active_orders"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
def probe_error_invalid_account(client: Client) -> ProbeResult:
    """Probe 22 (D-MATZ-29 #22): account inválido en ``get_active_orders``.

    Distingue ``PrimaryAPIError(status='ERROR')`` mapeado (PASS) de HTTP 4xx
    no-mapeado (finding ERROR-MAP OPEN).
    """
    if _auth_failed:
        return ProbeResult(
            "error_invalid_account", "SKIPPED", f"auth failed: {_auth_failure_reason}"
        )
    base_url = client._state.base_url
    try:
        client.get_active_orders("INVALID-ACCT-XXXXX")
    except PrimaryAPIError as exc:
        if exc.status == "ERROR":
            return ProbeResult(
                "error_invalid_account",
                "PASS",
                f"PrimaryAPIError as expected: {exc.description}",
            )
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="invalid account: PrimaryAPIError con status != 'ERROR'",
            expected="PrimaryAPIError(status='ERROR') al pasar account inválido",
            actual=f"PrimaryAPIError(status={exc.status!r}): {exc}",
            diff="status no es 'ERROR'; revisar mapping de error",
            base_url=base_url,
        )
        return ProbeResult("error_invalid_account", "FINDING", f"{fid} (OPEN)")
    except httpx.HTTPStatusError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="invalid account: HTTP 4xx no mapeado a PrimaryAPIError",
            expected="PrimaryAPIError mapeado para account inválido",
            actual=f"HTTPStatusError {exc.response.status_code}: {exc}",
            diff="upstream devolvió 4xx en lugar de status='ERROR' en payload",
            base_url=base_url,
        )
        return ProbeResult("error_invalid_account", "FINDING", f"{fid} (OPEN)")
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"invalid account: unexpected {type(exc).__name__}",
            expected="PrimaryAPIError mapeado para account inválido",
            actual=f"{type(exc).__name__}: {exc}",
            diff="excepción inesperada; revisar mapping",
            base_url=base_url,
        )
        return ProbeResult("error_invalid_account", "FINDING", f"{fid} (OPEN)")
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="ERROR-MAP",
        surface="sync",
        status="OPEN",
        title="get_active_orders con account inválido NO levantó excepción",
        expected="PrimaryAPIError mapeado para account inválido",
        actual="ninguna excepción; el cliente retornó normalmente",
        diff="upstream devolvió 200 OK con shape válida",
        base_url=base_url,
    )
    return ProbeResult("error_invalid_account", "FINDING", f"{fid} (OPEN)")


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_instruments_by_cfi_ESXXXX"],
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
def probe_error_malformed_cfi(client: Client) -> ProbeResult:
    """Probe 23 (D-MATZ-29 #23): CFI malformado en ``get_instruments_by_cfi``.

    Requiere ``cast(CFICode, 'INVALID-CFI')`` por mypy strict — el cliente
    acepta el string a runtime pero el upstream lo rechaza. Distingue
    PrimaryAPIError(status='ERROR') mapeado (PASS) de HTTP 4xx no-mapeado.
    """
    if _auth_failed:
        return ProbeResult("error_malformed_cfi", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = client._state.base_url
    try:
        client.get_instruments_by_cfi(cast(CFICode, "INVALID-CFI"))
    except PrimaryAPIError as exc:
        if exc.status == "ERROR":
            return ProbeResult(
                "error_malformed_cfi",
                "PASS",
                f"PrimaryAPIError as expected: {exc.description}",
            )
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="malformed CFI: PrimaryAPIError con status != 'ERROR'",
            expected="PrimaryAPIError(status='ERROR') al pasar CFI inválido",
            actual=f"PrimaryAPIError(status={exc.status!r}): {exc}",
            diff="status no es 'ERROR'; revisar mapping de error",
            base_url=base_url,
        )
        return ProbeResult("error_malformed_cfi", "FINDING", f"{fid} (OPEN)")
    except httpx.HTTPStatusError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="malformed CFI: HTTP 4xx no mapeado a PrimaryAPIError",
            expected="PrimaryAPIError mapeado para CFI inválido",
            actual=f"HTTPStatusError {exc.response.status_code}: {exc}",
            diff="upstream devolvió 4xx en lugar de status='ERROR' en payload",
            base_url=base_url,
        )
        return ProbeResult("error_malformed_cfi", "FINDING", f"{fid} (OPEN)")
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"malformed CFI: unexpected {type(exc).__name__}",
            expected="PrimaryAPIError mapeado para CFI inválido",
            actual=f"{type(exc).__name__}: {exc}",
            diff="excepción inesperada; revisar mapping",
            base_url=base_url,
        )
        return ProbeResult("error_malformed_cfi", "FINDING", f"{fid} (OPEN)")
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="ERROR-MAP",
        surface="sync",
        status="OPEN",
        title="get_instruments_by_cfi con CFI inválido NO levantó excepción",
        expected="PrimaryAPIError mapeado para CFI inválido",
        actual="ninguna excepción; el cliente retornó normalmente",
        diff="upstream aceptó CFI no válido; revisar validación",
        base_url=base_url,
    )
    return ProbeResult("error_malformed_cfi", "FINDING", f"{fid} (OPEN)")


# ---------------------------------------------------------------------------
# Probe 24: schema snapshot sweep (D-MATZ-29 #24, DRIFT-01 mirror)
# ---------------------------------------------------------------------------


@probe_context(
    endpoint="-",
    surface="sync",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
def probe_schema_snapshot(payloads: dict[str, Any], base_url: str) -> ProbeResult:
    """Probe 24 (D-MATZ-29 #24): schema snapshot sweep.

    Itera _SCHEMA_FILES y para cada func_name presente en payloads invoca
    ``_write_or_check_schema`` con envelope D-21 + D-25 no-overwrite-on-drift.
    Acumula resultados PASS / FINDING. Si todos PASS → PASS. Si hay drifts
    → FINDING con fids correspondientes.
    """
    if _auth_failed:
        return ProbeResult("schema_snapshot", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    # Phase 11 CR-01: sample_params placeholders alineados al estilo del path
    # template (``{name}``) para que el envelope sea visualmente consistente
    # entre la columna ``endpoint`` (que ya usa ``{account_id}``) y la columna
    # ``sample_params``. Pre-fix usaba un mix: el path template tenia
    # ``{account_id}`` mientras sample_params tenia ``<PRIMARY_ACCOUNT>``,
    # divergencia documentada como CR-01 (WR-01).
    #
    # CR-01 Option B (placeholder-everywhere): el envelope NO leak PII; todos
    # los valores account/symbol/segment/cl_ord_id/proprietary/exec_id se
    # representan como ``{name}`` placeholders. La column ``endpoint`` ya usa
    # ese estilo para las 3 risk probes; las probes con account-en-query ahora
    # tambien emiten placeholder en ``sample_params`` aunque el wire-level
    # query string SI envia el valor live -- el envelope documenta la SHAPE,
    # no el valor.
    sample_params: dict[str, dict[str, Any]] = {
        "get_segments": {},
        "get_all_instruments": {},
        "get_instruments_details": {},
        "get_instrument_detail": {"symbol": "{symbol}"},
        "get_instruments_by_cfi_ESXXXX": {"CFICode": "ESXXXX"},
        "get_instruments_by_segment": {"segmentId": "{segment_id}"},
        "get_market_data": {"symbol": "{symbol}"},
        "get_trades": {"symbol": "{symbol}", "windowDays": 7},
        "get_active_orders": {"accountId": "{account_id}"},
        "get_filled_orders": {"accountId": "{account_id}"},
        "get_all_orders": {"accountId": "{account_id}"},
        "get_order_status": {
            "clOrdId": "{cl_ord_id}",
            "proprietary": "{proprietary}",
        },
        "get_order_history": {
            "clOrdId": "{cl_ord_id}",
            "proprietary": "{proprietary}",
        },
        "get_order_by_exec_id": {"execId": "{exec_id}"},
        "get_positions": {"account_id": "{account_id}"},
        "get_detailed_positions": {"account_id": "{account_id}"},
        "get_account_report": {"account_id": "{account_id}"},
    }
    fids: list[str] = []
    snapshots_taken = 0
    for func_name, _ in _SCHEMA_FILES.items():
        if func_name not in payloads or payloads[func_name] is None:
            continue
        snapshots_taken += 1
        status, detail = _write_or_check_schema(
            func_name,
            _ENDPOINT_TEMPLATES[func_name],
            sample_params.get(func_name, {}),
            payloads[func_name],
            base_url,
        )
        if status == "FINDING":
            fid_part = detail.split("|", 1)[0]
            fids.append(fid_part)
    if fids:
        return ProbeResult(
            "schema_snapshot",
            "FINDING",
            f"{snapshots_taken} snapshots, {len(fids)} drifts: {', '.join(fids)} (OPEN)",
        )
    return ProbeResult("schema_snapshot", "PASS", f"{snapshots_taken} snapshots OK")


# ---------------------------------------------------------------------------
# Async probes (Phase 10 LIVE-02 — D-06 interleaved sync+async pattern).
#
# Each ``probe_X_async`` mirrors its ``probe_X_sync`` counterpart at the
# behaviour level: same surface, same SKIPPED triggers, same shape of
# PASS / FINDING / SKIPPED detail string. The async-failure surface is
# ``surface="async"`` in append_finding (vs ``"sync"`` above).
#
# Scope per CONTEXT D-09: REST-only subset. Risk API ``auth_basic`` probes
# (positions / detailed_positions / account_report) emit a single SKIPPED
# async stub each — they are Phase 11 CR-08 territory. CFI sanity sweep
# (8-loop variant) is mirrored as a single async probe. The 3 error probes
# (bogus symbol / invalid account / malformed CFI) have async mirrors that
# exercise the same error-mapping invariants through ``aio``.
#
# Auth state: ``probe_login_async`` reuses the shared ``_auth_failed`` /
# ``_auth_failure_reason`` cascade (D-IOL-3 idiom). If sync login already
# failed, async login still runs (independent state instance per Phase 7
# cross-leak isolation), so the cascade is set DURING the sync run, then
# async probes inherit it iff async login also fails.
# ---------------------------------------------------------------------------


@probe_context(
    endpoint="/auth/getToken",
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_login_async(aclient: AsyncClient) -> ProbeResult:
    """Async login probe (D-06 pair of ``probe_login_sync``)."""
    global _auth_failed, _auth_failure_reason
    base_url = aclient._state.base_url
    t0 = time.monotonic()
    try:
        await aclient.login()
    except AuthenticationError as exc:
        _auth_failed = True
        _auth_failure_reason = f"async AuthenticationError: {exc}"
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title="aio.login() async falló (AuthenticationError)",
            expected="login() retorna token válido y obtiene X-Auth-Token header",
            actual=f"AuthenticationError: {exc}",
            diff="verificar PRIMARY_USER/PRIMARY_PASSWORD; revisar headers de respuesta",
            base_url=base_url,
        )
        return ProbeResult("login_async", "FAIL", f"{fid} (OPEN): AuthenticationError")
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        _auth_failed = True
        _auth_failure_reason = f"async {type(exc).__name__}: {exc}"
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"aio.login() async levantó {type(exc).__name__} no mapeado",
            expected="AuthenticationError o éxito; transporte mapeado a tipo conocido",
            actual=f"{type(exc).__name__}: {exc}",
            diff="excepción no es subclase de AuthenticationError; revisar mapping",
            base_url=base_url,
        )
        return ProbeResult("login_async", "FAIL", f"{fid} (OPEN): {type(exc).__name__}")
    duration = time.monotonic() - t0
    return ProbeResult("login_async", "PASS", f"token obtenido en {duration:.2f}s")


async def _ainvoke(
    aclient: AsyncClient,
    name: str,
    coro_factory: Callable[[], Any],
    *,
    expected: str = "200 OK + surface-typed payload",
) -> ProbeResult:
    """Run a single async probe call and map exceptions to ProbeResult.

    Common skeleton for the 16 REST-only async paridad probes — keeps each
    individual ``probe_X_async`` short and mirrors the error-mapping flow
    used by ``_envelope_probe`` on the sync side. ``aclient`` is the single
    ``AsyncClient`` threaded from ``_async_main`` (TokenStore-safe: exactly one
    instance shares the 3-way concurrency primitive).
    """
    if _auth_failed:
        return ProbeResult(name, "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = aclient._state.base_url
    try:
        result = await coro_factory()
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"aio.{name} levantó PrimaryAPIError inesperado",
            expected=expected,
            actual=f"PrimaryAPIError: {exc}",
            diff="error upstream o status='ERROR' inesperado",
            base_url=base_url,
        )
        return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"aio.{name} levantó {type(exc).__name__} no mapeado",
            expected=expected,
            actual=f"{type(exc).__name__}: {exc}",
            diff="transporte async devolvió excepción no mapeada a PrimaryAPIError",
            base_url=base_url,
        )
        return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
    # PASS detail mirror sync helpers — short summary only (WR-01: no PII).
    if isinstance(result, list):
        return ProbeResult(name, "PASS", f"{len(result)} items")
    return ProbeResult(name, "PASS", "received")


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_segments"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_segments_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_segments``."""
    return await _ainvoke(aclient, "get_segments_async", aclient.get_segments)


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_all_instruments"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_all_instruments_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_all_instruments``."""
    return await _ainvoke(aclient, "get_all_instruments_async", aclient.get_all_instruments)


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_instruments_details"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_instruments_details_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_instruments_details``."""
    return await _ainvoke(aclient, "get_instruments_details_async", aclient.get_instruments_details)


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_instrument_detail"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_instrument_detail_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_instrument_detail`` (depende de ``_resolved_symbol``)."""
    if _resolved_symbol is None and not _auth_failed:
        return ProbeResult(
            "get_instrument_detail_async", "SKIPPED", "no _resolved_symbol from probe #3"
        )
    sym = _resolved_symbol or ""
    return await _ainvoke(
        aclient, "get_instrument_detail_async", lambda: aclient.get_instrument_detail(sym, "ROFX")
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_instruments_by_cfi_ESXXXX"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_instruments_by_cfi_ESXXXX_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_instruments_by_cfi_ESXXXX``."""
    return await _ainvoke(
        aclient,
        "get_instruments_by_cfi_ESXXXX_async",
        lambda: aclient.get_instruments_by_cfi("ESXXXX"),
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_instruments_by_cfi_ESXXXX"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_instruments_by_cfi_sanity_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_instruments_by_cfi_sanity`` — 8 CFI codes."""
    if _auth_failed:
        return ProbeResult(
            "get_instruments_by_cfi_sanity_async",
            "SKIPPED",
            f"auth failed: {_auth_failure_reason}",
        )
    base_url = aclient._state.base_url
    failures: list[str] = []
    counts: dict[str, int] = {}
    for cfi in _CFI_SANITY_CODES:
        try:
            items = await aclient.get_instruments_by_cfi(cfi)
        except PrimaryAPIError as exc:
            failures.append(f"{cfi}:PrimaryAPIError({exc})")
            continue
        except _RESIDUAL_PROBE_EXCEPTIONS as exc:
            failures.append(f"{cfi}:{type(exc).__name__}({exc})")
            continue
        counts[cfi] = len(items)
    if failures:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="async",
            status="OPEN",
            title="CFI sanity sweep async: shape failures",
            expected="cada CFI retorna list[Instrument] vía aio",
            actual=f"failures: {', '.join(failures)}",
            diff="ver lista de codes que fallaron shape",
            base_url=base_url,
        )
        return ProbeResult("get_instruments_by_cfi_sanity_async", "FINDING", f"{fid} (OPEN)")
    detail = ", ".join(f"{c}={n}" for c, n in counts.items())
    return ProbeResult("get_instruments_by_cfi_sanity_async", "PASS", detail)


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_instruments_by_segment"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_instruments_by_segment_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_instruments_by_segment``."""
    if _resolved_segment is None and not _auth_failed:
        return ProbeResult(
            "get_instruments_by_segment_async", "SKIPPED", "no _resolved_segment from probe #2"
        )
    seg = cast(Any, _resolved_segment or "")
    return await _ainvoke(
        aclient,
        "get_instruments_by_segment_async",
        lambda: aclient.get_instruments_by_segment(seg, "ROFX"),
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_market_data"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_market_data_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_market_data`` (no market-hours guard async — sync owns it).

    **Cuerpo propio en vez de ``_ainvoke`` (D-05).** El helper genérico sólo mapea
    excepciones y DESCARTA el resultado, así que la mitad async no podía gastar los seis
    alias: ése era el gap. El mapeo de excepciones se replica byte-paralelo al del
    helper —la misma familia (``PrimaryAPIError`` primero, ``_RESIDUAL_PROBE_EXCEPTIONS``
    después), el mismo ``append_finding`` con ``surface="async"``, los mismos títulos y el
    mismo nombre de probe (clave de findings)— para no perder cobertura de error-mapping.

    ``AsyncClient.get_market_data`` ya devuelve un ``MarketDataSnapshot`` TIPADO, así que
    esta superficie no construye nada: la única llamada emisora de request es la que ya
    tenía. Ver el comentario extenso en ``probe_get_market_data`` para por qué los seis
    alias son observación pura y no pueden mover el conteo de divergencias.
    """
    if _auth_failed:
        return ProbeResult(
            "get_market_data_async", "SKIPPED", f"auth failed: {_auth_failure_reason}"
        )
    if _resolved_symbol is None:
        return ProbeResult("get_market_data_async", "SKIPPED", "no _resolved_symbol from probe #3")
    sym = _resolved_symbol
    base_url = aclient._state.base_url
    expected = "200 OK + surface-typed payload"
    try:
        snapshot = await aclient.get_market_data(sym, ("BI", "OF", "LA", "OP", "CL", "SE", "OI"))
        last_price = snapshot.last.price
        bid_levels = len(snapshot.bids)
        offer_levels = len(snapshot.offers)
        settlement_price = snapshot.settlement.price
        close_price = snapshot.close.price
        open_interest_size = snapshot.open_interest.size
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="aio.get_market_data_async levantó PrimaryAPIError inesperado",
            expected=expected,
            actual=f"PrimaryAPIError: {exc}",
            diff="error upstream o status='ERROR' inesperado",
            base_url=base_url,
        )
        return ProbeResult("get_market_data_async", "FINDING", f"{fid} (OPEN)")
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"aio.get_market_data_async levantó {type(exc).__name__} no mapeado",
            expected=expected,
            actual=f"{type(exc).__name__}: {exc}",
            diff="transporte async devolvió excepción no mapeada a PrimaryAPIError",
            base_url=base_url,
        )
        return ProbeResult("get_market_data_async", "FINDING", f"{fid} (OPEN)")
    return ProbeResult(
        "get_market_data_async",
        "PASS",
        f"symbol={sym}, last={last_price} bids={bid_levels} offers={offer_levels} "
        f"settlement={settlement_price} close={close_price} oi={open_interest_size}",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_trades"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_trades_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_trades``."""
    if _resolved_symbol is None and not _auth_failed:
        return ProbeResult("get_trades_async", "SKIPPED", "no _resolved_symbol from probe #3")
    today = dt.date.today()
    seven_days_ago = today - dt.timedelta(days=7)
    sym = _resolved_symbol or ""
    return await _ainvoke(
        aclient,
        "get_trades_async",
        lambda: aclient.get_trades(
            sym, date_from=seven_days_ago.isoformat(), date_to=today.isoformat()
        ),
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_active_orders"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_active_orders_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_active_orders``."""
    if _PRIMARY_ACCOUNT is None and not _auth_failed:
        return ProbeResult("get_active_orders_async", "SKIPPED", "no PRIMARY_ACCOUNT env var")
    acct = _PRIMARY_ACCOUNT or ""
    return await _ainvoke(
        aclient, "get_active_orders_async", lambda: aclient.get_active_orders(acct)
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_filled_orders"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_filled_orders_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_filled_orders``."""
    if _PRIMARY_ACCOUNT is None and not _auth_failed:
        return ProbeResult("get_filled_orders_async", "SKIPPED", "no PRIMARY_ACCOUNT env var")
    acct = _PRIMARY_ACCOUNT or ""
    return await _ainvoke(
        aclient, "get_filled_orders_async", lambda: aclient.get_filled_orders(acct)
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_all_orders"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_all_orders_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_all_orders``."""
    if _PRIMARY_ACCOUNT is None and not _auth_failed:
        return ProbeResult("get_all_orders_async", "SKIPPED", "no PRIMARY_ACCOUNT env var")
    acct = _PRIMARY_ACCOUNT or ""
    return await _ainvoke(aclient, "get_all_orders_async", lambda: aclient.get_all_orders(acct))


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_order_status"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_order_status_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_order_status``."""
    if (_SAMPLE_CL_ORD_ID is None or _SAMPLE_PROPRIETARY is None) and not _auth_failed:
        return ProbeResult(
            "get_order_status_async",
            "SKIPPED",
            "no MATRIZ_SAMPLE_CL_ORD_ID / MATRIZ_SAMPLE_PROPRIETARY env vars",
        )
    cl_id = _SAMPLE_CL_ORD_ID or ""
    prop = _SAMPLE_PROPRIETARY or ""
    return await _ainvoke(
        aclient, "get_order_status_async", lambda: aclient.get_order_status(cl_id, prop)
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_order_history"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_order_history_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_order_history``."""
    if (_SAMPLE_CL_ORD_ID is None or _SAMPLE_PROPRIETARY is None) and not _auth_failed:
        return ProbeResult(
            "get_order_history_async",
            "SKIPPED",
            "no MATRIZ_SAMPLE_CL_ORD_ID / MATRIZ_SAMPLE_PROPRIETARY env vars",
        )
    cl_id = _SAMPLE_CL_ORD_ID or ""
    prop = _SAMPLE_PROPRIETARY or ""
    return await _ainvoke(
        aclient, "get_order_history_async", lambda: aclient.get_order_history(cl_id, prop)
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_order_by_exec_id"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_order_by_exec_id_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_get_order_by_exec_id``."""
    if _SAMPLE_EXEC_ID is None and not _auth_failed:
        return ProbeResult(
            "get_order_by_exec_id_async", "SKIPPED", "no MATRIZ_SAMPLE_EXEC_ID env var"
        )
    exec_id = _SAMPLE_EXEC_ID or ""
    return await _ainvoke(
        aclient, "get_order_by_exec_id_async", lambda: aclient.get_order_by_exec_id(exec_id)
    )


# Risk API auth_basic probes (positions / detailed_positions / account_report)
# — out-of-scope for Phase 10 async paridad per CONTEXT D-09. Each emits a
# single SKIPPED async stub so the paridad comparator sees a matching
# SKIPPED entry on the async side (mirror sync SKIPPED-on-no-account, and
# document that the async surface DOES expose these endpoints but Phase 10
# scope deliberately defers their live exercise to Phase 11 CR-08).


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_positions"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_positions_async(aclient: AsyncClient) -> ProbeResult:
    return ProbeResult(
        "get_positions_async",
        "SKIPPED",
        "Risk API auth_basic out-of-scope for Phase 10 async paridad (D-09; Phase 11 CR-08)",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_detailed_positions"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_detailed_positions_async(aclient: AsyncClient) -> ProbeResult:
    return ProbeResult(
        "get_detailed_positions_async",
        "SKIPPED",
        "Risk API auth_basic out-of-scope for Phase 10 async paridad (D-09; Phase 11 CR-08)",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_account_report"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_get_account_report_async(aclient: AsyncClient) -> ProbeResult:
    return ProbeResult(
        "get_account_report_async",
        "SKIPPED",
        "Risk API auth_basic out-of-scope for Phase 10 async paridad (D-09; Phase 11 CR-08)",
    )


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_market_data"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_error_bogus_symbol_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_error_bogus_symbol`` (MATZ-05)."""
    if _auth_failed:
        return ProbeResult(
            "error_bogus_symbol_async", "SKIPPED", f"auth failed: {_auth_failure_reason}"
        )
    base_url = aclient._state.base_url
    try:
        await aclient.get_market_data("ZZZZZZ-NOT-A-SYMBOL")
    except PrimaryAPIError as exc:
        if exc.status == "ERROR":
            return ProbeResult(
                "error_bogus_symbol_async",
                "PASS",
                f"PrimaryAPIError as expected: {exc.description}",
            )
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="bogus symbol async: PrimaryAPIError con status != 'ERROR'",
            expected="PrimaryAPIError(status='ERROR') al pasar símbolo inválido",
            actual=f"PrimaryAPIError(status={exc.status!r}): {exc}",
            diff="status no es 'ERROR'; revisar mapping de error",
            base_url=base_url,
        )
        return ProbeResult("error_bogus_symbol_async", "FINDING", f"{fid} (OPEN)")
    except httpx.HTTPStatusError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="bogus symbol async: HTTP 4xx no mapeado a PrimaryAPIError",
            expected="PrimaryAPIError mapeado para símbolo inválido",
            actual=f"HTTPStatusError {exc.response.status_code}: {exc}",
            diff="upstream devolvió 4xx en lugar de status='ERROR' en payload",
            base_url=base_url,
        )
        return ProbeResult("error_bogus_symbol_async", "FINDING", f"{fid} (OPEN)")
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"bogus symbol async: unexpected {type(exc).__name__}",
            expected="PrimaryAPIError mapeado para símbolo inválido",
            actual=f"{type(exc).__name__}: {exc}",
            diff="excepción inesperada; revisar mapping",
            base_url=base_url,
        )
        return ProbeResult("error_bogus_symbol_async", "FINDING", f"{fid} (OPEN)")
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="ERROR-MAP",
        surface="async",
        status="OPEN",
        title="aio.get_market_data con símbolo inválido NO levantó excepción",
        expected="PrimaryAPIError mapeado para símbolo inválido",
        actual="ninguna excepción; el cliente retornó normalmente",
        diff="upstream devolvió 200 OK con shape válida pero data inexistente",
        base_url=base_url,
    )
    return ProbeResult("error_bogus_symbol_async", "FINDING", f"{fid} (OPEN)")


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_active_orders"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_error_invalid_account_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_error_invalid_account`` (MATZ-05)."""
    if _auth_failed:
        return ProbeResult(
            "error_invalid_account_async", "SKIPPED", f"auth failed: {_auth_failure_reason}"
        )
    base_url = aclient._state.base_url
    try:
        await aclient.get_active_orders("INVALID-ACCT-XXXXX")
    except PrimaryAPIError as exc:
        if exc.status == "ERROR":
            return ProbeResult(
                "error_invalid_account_async",
                "PASS",
                f"PrimaryAPIError as expected: {exc.description}",
            )
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="invalid account async: PrimaryAPIError con status != 'ERROR'",
            expected="PrimaryAPIError(status='ERROR') al pasar account inválido",
            actual=f"PrimaryAPIError(status={exc.status!r}): {exc}",
            diff="status no es 'ERROR'; revisar mapping de error",
            base_url=base_url,
        )
        return ProbeResult("error_invalid_account_async", "FINDING", f"{fid} (OPEN)")
    except httpx.HTTPStatusError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="invalid account async: HTTP 4xx no mapeado a PrimaryAPIError",
            expected="PrimaryAPIError mapeado para account inválido",
            actual=f"HTTPStatusError {exc.response.status_code}: {exc}",
            diff="upstream devolvió 4xx en lugar de status='ERROR' en payload",
            base_url=base_url,
        )
        return ProbeResult("error_invalid_account_async", "FINDING", f"{fid} (OPEN)")
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"invalid account async: unexpected {type(exc).__name__}",
            expected="PrimaryAPIError mapeado para account inválido",
            actual=f"{type(exc).__name__}: {exc}",
            diff="excepción inesperada; revisar mapping",
            base_url=base_url,
        )
        return ProbeResult("error_invalid_account_async", "FINDING", f"{fid} (OPEN)")
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="ERROR-MAP",
        surface="async",
        status="OPEN",
        title="aio.get_active_orders con account inválido NO levantó excepción",
        expected="PrimaryAPIError mapeado para account inválido",
        actual="ninguna excepción; el cliente retornó normalmente",
        diff="upstream devolvió 200 OK con shape válida",
        base_url=base_url,
    )
    return ProbeResult("error_invalid_account_async", "FINDING", f"{fid} (OPEN)")


@probe_context(
    endpoint=_ENDPOINT_TEMPLATES["get_instruments_by_cfi_ESXXXX"],
    surface="async",
    decode_error=MatrizDecodeError,
    on_decode_error=_shape_probe_result,
)
async def probe_error_malformed_cfi_async(aclient: AsyncClient) -> ProbeResult:
    """D-06 async pair of ``probe_error_malformed_cfi`` (MATZ-05)."""
    if _auth_failed:
        return ProbeResult(
            "error_malformed_cfi_async", "SKIPPED", f"auth failed: {_auth_failure_reason}"
        )
    base_url = aclient._state.base_url
    try:
        await aclient.get_instruments_by_cfi(cast(CFICode, "INVALID-CFI"))
    except PrimaryAPIError as exc:
        if exc.status == "ERROR":
            return ProbeResult(
                "error_malformed_cfi_async",
                "PASS",
                f"PrimaryAPIError as expected: {exc.description}",
            )
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="malformed CFI async: PrimaryAPIError con status != 'ERROR'",
            expected="PrimaryAPIError(status='ERROR') al pasar CFI inválido",
            actual=f"PrimaryAPIError(status={exc.status!r}): {exc}",
            diff="status no es 'ERROR'; revisar mapping de error",
            base_url=base_url,
        )
        return ProbeResult("error_malformed_cfi_async", "FINDING", f"{fid} (OPEN)")
    except httpx.HTTPStatusError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="malformed CFI async: HTTP 4xx no mapeado a PrimaryAPIError",
            expected="PrimaryAPIError mapeado para CFI inválido",
            actual=f"HTTPStatusError {exc.response.status_code}: {exc}",
            diff="upstream devolvió 4xx en lugar de status='ERROR' en payload",
            base_url=base_url,
        )
        return ProbeResult("error_malformed_cfi_async", "FINDING", f"{fid} (OPEN)")
    except _RESIDUAL_PROBE_EXCEPTIONS as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"malformed CFI async: unexpected {type(exc).__name__}",
            expected="PrimaryAPIError mapeado para CFI inválido",
            actual=f"{type(exc).__name__}: {exc}",
            diff="excepción inesperada; revisar mapping",
            base_url=base_url,
        )
        return ProbeResult("error_malformed_cfi_async", "FINDING", f"{fid} (OPEN)")
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="ERROR-MAP",
        surface="async",
        status="OPEN",
        title="aio.get_instruments_by_cfi con CFI inválido NO levantó excepción",
        expected="PrimaryAPIError mapeado para CFI inválido",
        actual="ninguna excepción; el cliente retornó normalmente",
        diff="upstream aceptó CFI no válido; revisar validación",
        base_url=base_url,
    )
    return ProbeResult("error_malformed_cfi_async", "FINDING", f"{fid} (OPEN)")


# ---------------------------------------------------------------------------
# Async wrapper — un único asyncio.run (D-IOL-6 mirror).
#
# Phase 10 LIVE-02: all async probes share one event loop + exactly one
# explicitly-constructed ``AsyncClient`` instance (threaded as a parameter into
# every async probe — NOT the module default singleton), then aclose() at the
# end. The wrapper returns the full list of async ProbeResults in execution
# order so main() can interleave them with sync results (D-06 pairing per
# CONTEXT.md).
# ---------------------------------------------------------------------------


async def _async_main() -> list[ProbeResult]:
    """Run all paridad-scope async probes inside a single asyncio.run.

    Order matches the sync sweep (probes 1-19) plus the 3 error probes.
    Returns 22 ProbeResults: 1 login + 16 REST-only read-sweep probes +
    3 Risk-API-skipped probes + 3 error probes — 19 are real async invocations
    against the live surface; the 3 Risk probes are documented SKIPPED stubs
    (out-of-scope per D-09).
    """
    # CRITICAL (anti-Pitfall 1): construct EXACTLY ONE AsyncClient. matriz's
    # TokenStore is a 3-way concurrency primitive — a second AsyncClient would
    # split the shared token/refresh state and risk corruption / OAuth churn.
    # The <=2-ctor AST gate (test_main_matriz_uses_single_client_instance)
    # enforces this invariant. The single instance is threaded into every async
    # probe below.
    aclient = AsyncClient(strict_decode=_STRICT)
    async_results: list[ProbeResult] = []
    try:
        async_results.append(await probe_login_async(aclient))
        async_results.append(await probe_get_segments_async(aclient))
        async_results.append(await probe_get_all_instruments_async(aclient))
        async_results.append(await probe_get_instruments_details_async(aclient))
        async_results.append(await probe_get_instrument_detail_async(aclient))
        async_results.append(await probe_get_instruments_by_cfi_ESXXXX_async(aclient))
        async_results.append(await probe_get_instruments_by_cfi_sanity_async(aclient))
        async_results.append(await probe_get_instruments_by_segment_async(aclient))
        async_results.append(await probe_get_market_data_async(aclient))
        async_results.append(await probe_get_trades_async(aclient))
        async_results.append(await probe_get_active_orders_async(aclient))
        async_results.append(await probe_get_filled_orders_async(aclient))
        async_results.append(await probe_get_all_orders_async(aclient))
        async_results.append(await probe_get_order_status_async(aclient))
        async_results.append(await probe_get_order_history_async(aclient))
        async_results.append(await probe_get_order_by_exec_id_async(aclient))
        async_results.append(await probe_get_positions_async(aclient))
        async_results.append(await probe_get_detailed_positions_async(aclient))
        async_results.append(await probe_get_account_report_async(aclient))
        async_results.append(await probe_error_bogus_symbol_async(aclient))
        async_results.append(await probe_error_invalid_account_async(aclient))
        async_results.append(await probe_error_malformed_cfi_async(aclient))
    finally:
        with contextlib.suppress(Exception):
            await aclient.aclose()
    return async_results


# ---------------------------------------------------------------------------
# main() lifecycle (D-MATZ-29 #25 cycle_closure + D-MATZ-27 EXPECTED terminal)
# ---------------------------------------------------------------------------


def main() -> None:
    """Driver lifecycle sync-only (D-MATZ-30).

    Secuencia:
    1. HARN-01 ``require_env`` gate — exit 0 si faltan credenciales.
    2. D-MATZ-33 venue allowlist (Phase 39 D-02/D-01) — línea SKIPPED a stdout y
       exit 0 si el hostname de base_url no está en ``_VENUE_ALLOWLIST``.
    3. ``write_findings(_PKG)`` para inicializar el findings file.
    3b. ``_seed_fid_counter()`` (Phase 33, P-3): sube el allocator por encima de
       los diez fids ya committeados. Orden obligatorio: DESPUÉS de
       ``write_findings`` y ANTES del primer probe.
    4. Secrets discovery dinámico (D-MATZ-32): PRIMARY_USER, PRIMARY_PASSWORD del
       env + ``_token`` agregado dinámicamente tras probe_login_sync.
    4b. ``divergence_capture(("matriz_client",), ...)`` (Phase 33, D-01) envuelve
       el sweep entero: sube el logger de paquete a INFO y traduce cada record de
       divergencia a un finding ``SHAPE``. El ``handler`` sobrevive al ``with``,
       así que el SUMMARY reporta ``DIVERGENCES`` y ``HANDLER_ERRORS``.
    5. Probes 1-19: login + 18 read-sweep (D-MATZ-29 happy-path sweep).
    6. Probe 20: field_type_map (MATZ-03).
    7. Probes 21-23: 3 error probes (MATZ-05).
    8. Probe 24: schema snapshot sweep (DRIFT-01 mirror).
       D-MATZ-24: error probes ANTES de snapshots — si rompen state, snapshots ya
       fueron generados. Pero implementación: schema_snapshot ejercita lo que ya
       fue colectado en payloads, ergo orden no es load-bearing para el snapshot.
    9. Probe 25: cycle_closure x 4 paquetes (D-MATZ-28, DRIFT-02).
    10. D-MATZ-27 EXPECTED terminal — última operación sobre matriz-client.
    11. Emit verbatim PROBE / SUMMARY via safe_print con secrets redacted.
    """
    if not require_env(_PKG, ["PRIMARY_USER", "PRIMARY_PASSWORD"]):
        sys.exit(0)

    # Single sync Client for the whole sync sweep (D-01/D-02). One instance —
    # the AST gate caps construction at one sync + one async client.
    # Phase 33 (LIVE-TYP-01): ``strict_decode`` viaja como kwarg del constructor
    # justamente para no abrir un segundo sitio de construcción.
    client = Client(strict_decode=_STRICT)

    # D-MATZ-33 belt-and-suspenders hostname gate: prevención contra prod.
    # Phase 39 D-02: allowlist por igualdad exacta de hostname (dos venues
    # confirmados por el operador), en vez del substring `"remarkets" in base`.
    # Phase 39 D-01: un host fuera del allowlist NO es una falla del driver — es
    # un bloqueo de política. Se emite la línea SKIPPED a STDOUT (el único stream
    # que `main_verify.py` escanea) y se sale con código 0, ANTES de
    # `write_findings(_PKG)` y del primer probe: la rama de skip no escribe ni un
    # finding (T-39-03).
    base = client._state.base_url
    venue = _venue_token(base)
    if venue is None:
        print(_HOST_SKIP_LINE)
        # Phase 39 (D-09 / T-39-12): el sobre se REESCRIBE con cero probes y la
        # causa medida. Sin esto, el sobre de una corrida anterior quedaría en
        # pie y el loop de cierre de ciclo de abajo lo leería como evidencia de
        # ESTA corrida. Una corrida saltada invalida el sobre.
        write_run_evidence(
            _PKG,
            driver="main_matriz.py",
            triples=[],
            counts={},
            skipped=_HOST_SKIP_EVIDENCE,
        )
        sys.exit(0)

    write_findings(_PKG)

    # D-16/D-24 (P-3): sube el allocator por encima de todo fid ya committeado.
    # Orden obligatorio — ``write_findings`` < ``_seed_fid_counter`` < primer
    # probe. Mismo orden canónico que ``main_iol.py``, ``main_higyrus.py`` y
    # ``main_market_data.py``. Sin esto los diez fids committeados de matriz
    # (ninguno ``OPEN``) se re-emiten y los diez primeros findings de la corrida
    # se descartan en silencio mientras ``FINDING=N`` los sigue contando.
    _seed_fid_counter()

    # D-MATZ-32 secrets dinámicos: filtrar credenciales de longitud >= 4 al inicio,
    # _token se agrega tras login.
    secrets: list[str] = []
    password_env = os.getenv("PRIMARY_PASSWORD", "")
    if password_env and len(password_env) >= 4:
        secrets.append(password_env)
    user_env = os.getenv("PRIMARY_USER", "")
    if user_env and len(user_env) >= 4:
        secrets.append(user_env)
    # WR-01: PRIMARY_ACCOUNT es PII operacional (account ID real). Sin esto, las
    # líneas PROBE de get_detailed_positions y get_account_report (y cualquier
    # probe que devuelva el accountId en su detail string) lo imprimirían
    # verbatim en stdout / CI logs. safe_print lo redacta como cualquier otro
    # secret una vez incluido en la lista.
    account_env = os.getenv("PRIMARY_ACCOUNT", "")
    if account_env and len(account_env) >= 4:
        secrets.append(account_env)

    # Phase 33 (LIVE-TYP-01 / D-01): el handler de divergencias se instala
    # alrededor del sweep entero — sube ``matriz_client`` de NOTSET a INFO (sin
    # eso los records de especie ``extra`` se descartan antes de llegar a
    # ningún handler) y traduce cada record de seis claves a un finding
    # ``SHAPE``. ``next_fid`` recibe el slug y lo descarta: el driver ya tiene
    # UN allocator por proceso y compartirlo es lo que impide que el handler y
    # el driver se pisen los fids.
    with divergence_capture(("matriz_client",), next_fid=lambda _slug: _next_fid()) as handler:
        results: list[ProbeResult] = []
        payloads: dict[str, Any] = {}

        # Probe 1: login.
        r1 = probe_login_sync(client)
        results.append(r1)
        token = getattr(client._state, "token", None)
        if isinstance(token, str) and len(token) >= 4:
            secrets.append(token)

        # Probes 2-19: happy-path sweep (D-MATZ-29 #2-#19).
        sweep_probes: list[tuple[str, Any]] = [
            ("get_segments", probe_get_segments),
            ("get_all_instruments", probe_get_all_instruments),
            ("get_instruments_details", probe_get_instruments_details),
            ("get_instrument_detail", probe_get_instrument_detail),
            ("get_instruments_by_cfi_ESXXXX", probe_get_instruments_by_cfi_ESXXXX),
            ("get_instruments_by_cfi_sanity", probe_get_instruments_by_cfi_sanity),
            ("get_instruments_by_segment", probe_get_instruments_by_segment),
            ("get_market_data", probe_get_market_data),
            ("get_trades", probe_get_trades),
            ("get_active_orders", probe_get_active_orders),
            ("get_filled_orders", probe_get_filled_orders),
            ("get_all_orders", probe_get_all_orders),
            ("get_order_status", probe_get_order_status),
            ("get_order_history", probe_get_order_history),
            ("get_order_by_exec_id", probe_get_order_by_exec_id),
            ("get_positions", probe_get_positions),
            ("get_detailed_positions", probe_get_detailed_positions),
            ("get_account_report", probe_get_account_report),
        ]
        for key, probe_fn in sweep_probes:
            result, raw = probe_fn(client)
            results.append(result)
            if raw is not None:
                payloads[key] = raw

        # Probe 20: field_type_map (MATZ-03).
        results.append(probe_field_type_map(payloads))

        # Probes 21-23: error probes (MATZ-05). D-MATZ-24: DESPUÉS de happy-path
        # sweep y field_type_map para minimizar interferencia con state.
        results.append(probe_error_bogus_symbol(client))
        results.append(probe_error_invalid_account(client))
        results.append(probe_error_malformed_cfi(client))

        # Probe 24: schema snapshots (DRIFT-01 mirror, D-MATZ-24 después de errors).
        results.append(probe_schema_snapshot(payloads, base))

        # Phase 39 (D-09): sobre interino de matriz, ANTES del loop de cierre de
        # ciclo. El loop lee la evidencia de los CUATRO paquetes —matriz
        # incluido— y a esta altura del run el sobre en disco todavía es el de
        # la corrida ANTERIOR. Sin esta escritura, matriz se juzgaría a sí mismo
        # por una corrida vieja (o, en el primer run, se reportaría SKIPPED "sin
        # evidencia" en el mismo output donde acaba de imprimir 24 probes). El
        # bloque del SUMMARY lo reescribe al final con los conteos completos.
        interim_counts: dict[str, int] = {"PASS": 0, "FAIL": 0, "SKIPPED": 0, "FINDING": 0}
        for r in results:
            interim_counts[r.status] = interim_counts.get(r.status, 0) + 1
        write_run_evidence(
            _PKG,
            driver="main_matriz.py",
            triples=sorted(handler.seen),
            counts=interim_counts,
        )

        # Probe 25: cycle_closure x 4 paquetes (D-MATZ-28, DRIFT-02), endurecido
        # contra el PASS vacuo (Phase 39 D-09). Cada veredicto se decide sobre
        # EVIDENCIA POSITIVA DE CORRIDA —el conteo de probes del sobre— y no
        # sobre la ausencia de findings: `verify_cycle_closure` devuelve
        # `(True, [])` también cuando el archivo de findings no existe, así que
        # su `ok` solo, sin el sobre al lado, no distingue "todo enlazado" de
        # "nada que validar".
        #
        # ACOPLAMIENTO DECLARADO: el cierre de ciclo de los CUATRO paquetes vive
        # dentro del driver de matriz, así que si matriz sale temprano por el
        # gate D-MATZ-33 este loop no corre y NINGUNO de los cuatro recibe
        # veredicto de cierre. En ese caso el censo de la fase debe registrar
        # `cycle_closure: NO CORRIÓ — LIVE-MATZ-33` para los cuatro paquetes,
        # nunca un silencio que un lector tome por limpio.
        for pkg in (
            "ambito-financiero-client",
            "iol-client",
            "higyrus-client",
            "matriz-client",
        ):
            evidence = read_run_evidence(pkg)
            probes = probes_executed(pkg)
            ok, missing = verify_cycle_closure(pkg)
            status_str, detail = _cycle_closure_verdict(
                pkg,
                probes=probes,
                evidence=evidence,
                ok=ok,
                missing=missing,
            )
            results.append(
                ProbeResult(
                    f"cycle_closure_{pkg.replace('-', '_')}",
                    status_str,
                    detail,
                )
            )
            # Sólo el camino FAIL escribe finding: un paquete que no corrió sale
            # SKIPPED y no toca el ledger — no medir no es un defecto.
            if status_str == "FAIL":
                fid = _next_fid()
                append_finding(
                    pkg,
                    fid=fid,
                    class_="ERROR-MAP",
                    surface="sync",
                    status="OPEN",
                    title=f"cycle closure: {len(missing)} CONFIRMED/FIXED without regression test",
                    expected="every CONFIRMED/FIXED finding linked to existing test path",
                    actual=f"missing regressions: {', '.join(missing)}",
                    diff="see verify_cycle_closure output",
                )

        # D-MATZ-27 EXPECTED terminal: prod-vs-sandbox divergence acknowledged.
        # Esta ES la última invocación de append_finding sobre _PKG en main()
        # (Assumption A3 del plan).
        # HARN-10 (Phase 11): idempotent_by_title=True evita que el terminal se
        # duplique cross-run con cada _next_fid() distinto — content-addressed
        # dedupe by title; el title funciona como identidad estable del finding.
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="EXPECTED",
            # Phase 39 (Pitfall 5): el título anterior
            # ("prod-vs-remarkets divergence acknowledged") y su `expected`
            # citaban una fila de REQUIREMENTS.md que ya no existe y afirmaban
            # que la verificación era remarkets-only — falso bajo D-02. Como el
            # dedupe es `idempotent_by_title=True`, el título nuevo crea un
            # finding NUEVO: el anterior queda superseded en el ledger y recibe
            # disposición explícita en el plan 39-07 (no se borra).
            title="prod-vs-sandbox divergence acknowledged",
            expected=(
                "verification limited to a venue in the D-MATZ-33 hostname "
                f"allowlist (this run: {venue}) by safety policy; the allowlist "
                "is widened only by explicit operator decision (Phase 39 D-02)"
            ),
            actual=(
                "prod (api.primary.com.ar) shape unverified; sandbox shape "
                f"({venue}) committed in .planning/verification/schemas/matriz-client/"
            ),
            diff="N/A (acknowledged limitation, not detected drift)",
            base_url=base,
            idempotent_by_title=True,
        )

        # Phase 10 LIVE-02 — D-06 interleaved sync+async paridad.
        # Run all async probes in a single asyncio.run (D-IOL-6 mirror), then
        # APPEND each async result to the report alongside its sync counterpart.
        async_results = asyncio.run(_async_main())
        results.extend(async_results)

    # Stdout verbatim D-02 + SUMMARY. Cada línea via safe_print con secrets.
    counts: dict[str, int] = {"PASS": 0, "FAIL": 0, "SKIPPED": 0, "FINDING": 0}
    for r in results:
        line = f"PROBE {r.name}: {r.status} {r.detail}".rstrip()
        safe_print(line, secrets=secrets)
        counts[r.status] = counts.get(r.status, 0) + 1
    # Phase 33 (P-3 / T-33-11): ``DIVERGENCES`` es ``len(handler.seen)`` — el
    # conteo de triples distintos ``(slug, model, field_path, kind)``, LA unidad
    # del censo y la única directamente comparable contra el piso de
    # ``29-SIZING.md``. NO es el conteo de findings: con la superficie embebida
    # en el título hay ~2 findings por triple. ``HANDLER_ERRORS`` es el tally de
    # fallas del sink: un pipeline de logging que puede fallar en silencio no
    # sirve como registro de auditoría, así que el número se imprime siempre —
    # un valor distinto de cero invalida el censo de esta corrida.
    safe_print(
        f"SUMMARY: PASS={counts['PASS']} FAIL={counts['FAIL']} "
        f"SKIPPED={counts['SKIPPED']} FINDING={counts['FINDING']} "
        f"DIVERGENCES={len(handler.seen)} HANDLER_ERRORS={len(handler.errors)}",
        secrets=secrets,
    )

    # Phase 39 (D-09 + D-10): la línea SUMMARY imprime el CONTEO de triples y se
    # va con el proceso; el sobre persiste los MIEMBROS —la unidad del censo— y
    # el conteo de probes. Esta escritura REEMPLAZA la interina que el sweep
    # hizo antes del loop de cierre de ciclo: acá los conteos ya incluyen los
    # probes async y el propio veredicto de cierre.
    write_run_evidence(
        _PKG,
        driver="main_matriz.py",
        triples=sorted(handler.seen),
        counts=counts,
    )

    # Phase 10 LIVE-02 paridad reporter (D-06): compare PASS/FINDING/SKIPPED
    # outcome sets between sync and async probes. Naming convention: the
    # async probe is the sync name with ``_async`` suffix (or the sync name
    # with ``_sync`` stripped from the sync name where present — matriz sync
    # uses bare names like ``get_segments``, async uses ``get_segments_async``).
    sync_outcomes: dict[str, str] = {}
    async_outcomes: dict[str, str] = {}
    # D-09 exclusions: Risk API auth_basic + sync-only auxiliaries are
    # out-of-scope for Phase 10 paridad (Phase 11 CR-08 will lift these).
    _PARIDAD_EXCLUDED: set[str] = {
        "get_positions",
        "get_detailed_positions",
        "get_account_report",
        "field_type_map",
        "schema_snapshot",
    }
    for r in results:
        if r.name.endswith("_async"):
            key = r.name[: -len("_async")]
            if key in _PARIDAD_EXCLUDED:
                continue
            async_outcomes[key] = r.status
        elif r.name in {"login_sync"}:
            sync_outcomes["login"] = r.status
        elif r.name.startswith("cycle_closure_"):
            # cycle_closure probes are sync-only (DRIFT-02), not paired async.
            continue
        elif r.name in _PARIDAD_EXCLUDED:
            continue
        else:
            sync_outcomes[r.name] = r.status
    common_keys = set(sync_outcomes) & set(async_outcomes)
    divergences = [
        (k, sync_outcomes[k], async_outcomes[k])
        for k in sorted(common_keys)
        if sync_outcomes[k] != async_outcomes[k]
    ]
    paridad = not divergences and bool(common_keys)
    paridad_status = "PASS" if paridad else "FAIL"
    safe_print(
        f"=== Phase 10 LIVE-02 Paridad sync↔async: {paridad_status} "
        f"(probes_paired={len(common_keys)}, divergences={len(divergences)}) ===",
        secrets=secrets,
    )
    if divergences:
        for key, sync_st, async_st in divergences:
            safe_print(f"  DIVERGENCE {key}: sync={sync_st} async={async_st}", secrets=secrets)


if __name__ == "__main__":
    main()
