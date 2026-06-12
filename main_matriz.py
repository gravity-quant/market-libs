"""Phase 5 live verification driver para ``matriz-client`` (Primary API / MATBA ROFEX).

Driver de verificación en vivo contra el sandbox de remarkets
(``https://api.remarkets.primary.com.ar``). Ejercita ~25 probes nombrados en
orden D-MATZ-29 cubriendo:

- ``MATZ-01`` — login sync vs. servicio real (no async — matriz no tiene aio.py).
- ``MATZ-02`` — happy-path sweep de los 18 endpoints REST públicos.
- ``MATZ-03`` — bidirectional SafeModel<->wire diff sobre los 11 modelos
  ``_SafeModel`` matriz vía ``diff_safemodel_bidirectional`` promovido en Phase 5.
- ``MATZ-05`` — 3 error probes always-on (bogus symbol, invalid account, malformed CFI)
  con distinción HTTP 4xx no-mapeado vs. ``status='ERROR'`` mapeado (D-MATZ-22/23).
- ``MATZ-07`` — market-hours guard sobre ``LA.date`` epoch ms (D-MATZ-5).
- ``DRIFT-01`` mirror — schema snapshots envelope D-21 + D-25 no-overwrite-on-drift.
- ``DRIFT-02`` — ``verify_cycle_closure`` x 4 paquetes verificados (Phase 2-5).

**Sync-only por diseño** (D-MATZ-30): matriz no tiene ``aio.py``, el driver no
ejecuta event loops ni rutinas async, y no tiene la función ``_async`` que
existe en los drivers de los otros paquetes.

**Security gates aplicados al inicio de ``main()``** (D-MATZ-33):

1. ``require_env(_PKG, ["PRIMARY_USER", "PRIMARY_PASSWORD"])`` — HARN-01 path.
2. Hostname assert remarkets: si ``"remarkets" not in primary.client._base_url``
   → ``ABORT`` con exit 1 (belt-and-suspenders contra prod por mis-configuración).

Output verbatim (D-02 mirror Phase 2-4): cada probe emite una línea
``PROBE <name>: <status> <detail>`` y al final ``SUMMARY: PASS=N FAIL=N
SKIPPED=N FINDING=N``, todo a través de ``safe_print(..., secrets=[...])``
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

import datetime as dt
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import httpx
from verification import (
    append_finding,
    diff_safemodel_bidirectional,
    require_env,
    safe_print,
    schema_of,
    write_findings,
)
from verification.cycle_report import verify_cycle_closure

import matriz_client as primary
from matriz_client import PrimaryAPIError
from matriz_client.client import _request as _matriz_request
from matriz_client.client import _risk_auth
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

# D-21 envelope: mapping cada probe func_name a su archivo de schema snapshot.
_SCHEMA_FILES: dict[str, Path] = {
    "get_segments": _SCHEMA_DIR / "get-segments.json",
    "get_all_instruments": _SCHEMA_DIR / "get-all-instruments.json",
    "get_instruments_details": _SCHEMA_DIR / "get-instruments-details.json",
    "get_instrument_detail": _SCHEMA_DIR / "get-instrument-detail.json",
    "get_instruments_by_cfi_ESXXXX": _SCHEMA_DIR / "get-instruments-by-cfi-esxxxx.json",
    "get_instruments_by_segment": _SCHEMA_DIR / "get-instruments-by-segment.json",
    "get_market_data": _SCHEMA_DIR / "get-market-data.json",
    "get_trades": _SCHEMA_DIR / "get-trades.json",
    "get_active_orders": _SCHEMA_DIR / "get-active-orders.json",
    "get_filled_orders": _SCHEMA_DIR / "get-filled-orders.json",
    "get_all_orders": _SCHEMA_DIR / "get-all-orders.json",
    "get_order_status": _SCHEMA_DIR / "get-order-status.json",
    "get_order_history": _SCHEMA_DIR / "get-order-history.json",
    "get_order_by_exec_id": _SCHEMA_DIR / "get-order-by-exec-id.json",
    "get_positions": _SCHEMA_DIR / "get-positions.json",
    "get_detailed_positions": _SCHEMA_DIR / "get-detailed-positions.json",
    "get_account_report": _SCHEMA_DIR / "get-account-report.json",
}

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
_fid_counter: int = 0


def _next_fid() -> str:
    """Devuelve el siguiente ``F-NN`` (NN zero-padded a 2 dígitos)."""
    global _fid_counter
    _fid_counter += 1
    return f"F-{_fid_counter:02d}"


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Resultado de un probe: nombre + status + detalle short-form."""

    name: str
    status: str  # "PASS" | "FAIL" | "SKIPPED" | "FINDING"
    detail: str


def _first_dict(payload: Any) -> dict[str, Any] | None:
    """Devuelve el primer dict de una lista, o None si payload no es lista no vacía
    o el primer elemento no es dict. Utility para extraer un sample dict de un
    envelope-unwrapped list payload (segments, instruments, trades, orders, ...).
    """
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return cast(dict[str, Any], payload[0])
    return None


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
# Probe 1: login_sync (D-MATZ-29 #1, MATZ-01)
# ---------------------------------------------------------------------------


def probe_login_sync() -> ProbeResult:
    """Probe 1: ``primary.login()`` sync (MATZ-01).

    Setea ``_auth_failed`` global si la auth falla — activa cascade SKIPPED
    en todos los downstream (D-MATZ-31). Distingue ``AuthenticationError``
    (esperable si credenciales inválidas) de ``Exception`` inesperada (transport
    / network — emite finding ERROR-MAP OPEN).
    """
    global _auth_failed, _auth_failure_reason
    base_url = primary.client._base_url
    t0 = time.monotonic()
    try:
        primary.login()
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
        return ProbeResult("login_sync", "FAIL", f"{fid} (OPEN): AuthenticationError")
    except Exception as exc:
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
        return ProbeResult("login_sync", "FAIL", f"{fid} (OPEN): {type(exc).__name__}")
    duration = time.monotonic() - t0
    return ProbeResult("login_sync", "PASS", f"token obtenido en {duration:.2f}s")


# ---------------------------------------------------------------------------
# Probes 2-19: read-sweep (D-MATZ-29 #2-#19, MATZ-02)
#
# Cada probe retorna ``(ProbeResult, raw_payload | None)``. El raw_payload es
# el dict/lista crudo retornado por ``_matriz_request`` (envelope ya extraído)
# para uso downstream por ``probe_field_type_map`` y ``probe_schema_snapshot``.
# ---------------------------------------------------------------------------


def probe_get_segments() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
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
        raw = _matriz_request("GET", path)
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


def probe_get_all_instruments() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
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
        raw = _matriz_request("GET", path)
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


def probe_get_instruments_details() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 4 (D-MATZ-29 #4): ``GET /rest/instruments/details``."""
    if _auth_failed:
        return (
            ProbeResult(
                "get_instruments_details", "SKIPPED", f"auth failed: {_auth_failure_reason}"
            ),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/instruments/details"
    try:
        raw = _matriz_request("GET", path)
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_instruments_details levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {instruments: [...]}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_details", "FINDING", f"{fid} (OPEN)"), None)
    instruments = raw.get("instruments")
    if not isinstance(instruments, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_instruments_details envelope shape incorrecto",
            expected="raw['instruments'] es list",
            actual=f"raw['instruments']={type(instruments).__name__}",
            diff="envelope key 'instruments' ausente o no-list",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_details", "FINDING", f"{fid} (OPEN)"), None)
    return (
        ProbeResult("get_instruments_details", "PASS", f"{len(instruments)} instrument details"),
        instruments,
    )


def probe_get_instrument_detail() -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 5 (D-MATZ-29 #5): ``GET /rest/instruments/detail`` con ``_resolved_symbol``.

    SKIPPED si ``_resolved_symbol`` no se resolvió (probe #3 falló o instruments vacío).
    """
    if _auth_failed:
        return (
            ProbeResult("get_instrument_detail", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    if _resolved_symbol is None:
        return (
            ProbeResult("get_instrument_detail", "SKIPPED", "no _resolved_symbol from probe #3"),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/instruments/detail"
    try:
        raw = _matriz_request("GET", path, params={"symbol": _resolved_symbol, "marketId": "ROFX"})
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_instrument_detail levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {instrument: {...}}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_instrument_detail", "FINDING", f"{fid} (OPEN)"), None)
    instrument = raw.get("instrument")
    if not isinstance(instrument, dict):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_instrument_detail envelope shape incorrecto",
            expected="raw['instrument'] es dict",
            actual=f"raw['instrument']={type(instrument).__name__}",
            diff="envelope key 'instrument' ausente o no-dict",
            base_url=base_url,
        )
        return (ProbeResult("get_instrument_detail", "FINDING", f"{fid} (OPEN)"), None)
    return (
        ProbeResult("get_instrument_detail", "PASS", f"symbol={_resolved_symbol}"),
        instrument,
    )


def probe_get_instruments_by_cfi_ESXXXX() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 6 (D-MATZ-29 #6): ``GET /rest/instruments/byCFICode`` con ``CFICode='ESXXXX'``.

    Baseline para schema snapshot D-MATZ-6 (los otros 8 CFI van por probe #7).
    """
    if _auth_failed:
        return (
            ProbeResult(
                "get_instruments_by_cfi_ESXXXX",
                "SKIPPED",
                f"auth failed: {_auth_failure_reason}",
            ),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/instruments/byCFICode"
    try:
        raw = _matriz_request("GET", path, params={"CFICode": "ESXXXX"})
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_instruments_by_cfi(ESXXXX) levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {instruments: [...]}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_by_cfi_ESXXXX", "FINDING", f"{fid} (OPEN)"), None)
    instruments = raw.get("instruments")
    if not isinstance(instruments, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_instruments_by_cfi(ESXXXX) envelope shape incorrecto",
            expected="raw['instruments'] es list",
            actual=f"raw['instruments']={type(instruments).__name__}",
            diff="envelope key 'instruments' ausente o no-list",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_by_cfi_ESXXXX", "FINDING", f"{fid} (OPEN)"), None)
    return (
        ProbeResult(
            "get_instruments_by_cfi_ESXXXX", "PASS", f"{len(instruments)} ESXXXX instruments"
        ),
        instruments,
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


def probe_get_instruments_by_cfi_sanity() -> tuple[ProbeResult, None]:
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
            raw = _matriz_request("GET", path, params={"CFICode": cfi})
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


def probe_get_instruments_by_segment() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 8 (D-MATZ-29 #8): ``GET /rest/instruments/bySegment`` con ``_resolved_segment``.

    SKIPPED si ``_resolved_segment`` no se resolvió (probe #2 falló o segments vacío).
    """
    if _auth_failed:
        return (
            ProbeResult(
                "get_instruments_by_segment", "SKIPPED", f"auth failed: {_auth_failure_reason}"
            ),
            None,
        )
    if _resolved_segment is None:
        return (
            ProbeResult(
                "get_instruments_by_segment", "SKIPPED", "no _resolved_segment from probe #2"
            ),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/instruments/bySegment"
    try:
        raw = _matriz_request(
            "GET", path, params={"MarketSegmentID": _resolved_segment, "MarketID": "ROFX"}
        )
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_instruments_by_segment levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {instruments: [...]}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_by_segment", "FINDING", f"{fid} (OPEN)"), None)
    instruments = raw.get("instruments")
    if not isinstance(instruments, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_instruments_by_segment envelope shape incorrecto",
            expected="raw['instruments'] es list",
            actual=f"raw['instruments']={type(instruments).__name__}",
            diff="envelope key 'instruments' ausente o no-list",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_by_segment", "FINDING", f"{fid} (OPEN)"), None)
    return (
        ProbeResult(
            "get_instruments_by_segment",
            "PASS",
            f"segment={_resolved_segment}: {len(instruments)} instruments",
        ),
        instruments,
    )


def probe_get_market_data() -> tuple[ProbeResult, dict[str, Any] | None]:
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
        raw = _matriz_request(
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
    # D-MATZ-5 market-hours guard: inspecciona LA.date.
    la = md.get("LA")
    detail = f"symbol={_resolved_symbol}, entries={len(md)}"
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


def probe_get_trades() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 10 (D-MATZ-29 #10): ``GET /rest/data/getTrades`` con ``date_from=today-7d``.

    D-MATZ-8: si lista vacía → finding NO-DATA OPEN + PASS-shape.
    """
    if _auth_failed:
        return (
            ProbeResult("get_trades", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    if _resolved_symbol is None:
        return (
            ProbeResult("get_trades", "SKIPPED", "no _resolved_symbol from probe #3"),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/data/getTrades"
    today = dt.date.today()
    seven_days_ago = today - dt.timedelta(days=7)
    try:
        raw = _matriz_request(
            "GET",
            path,
            params={
                "marketId": "ROFX",
                "symbol": _resolved_symbol,
                "dateFrom": seven_days_ago.isoformat(),
                "dateTo": today.isoformat(),
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
            title="get_trades levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {trades: [...]}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_trades", "FINDING", f"{fid} (OPEN)"), None)
    trades = raw.get("trades")
    if not isinstance(trades, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_trades envelope shape incorrecto",
            expected="raw['trades'] es list",
            actual=f"raw['trades']={type(trades).__name__}",
            diff="envelope key 'trades' ausente o no-list",
            base_url=base_url,
        )
        return (ProbeResult("get_trades", "FINDING", f"{fid} (OPEN)"), None)
    if not trades:
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
            base_url=base_url,
        )
        return (ProbeResult("get_trades", "PASS", f"empty trades ({fid} NO-DATA)"), trades)
    return (ProbeResult("get_trades", "PASS", f"{len(trades)} trades"), trades)


def probe_get_active_orders() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 11 (D-MATZ-29 #11): ``GET /rest/order/actives`` con ``PRIMARY_ACCOUNT``.

    SKIPPED si ``PRIMARY_ACCOUNT`` no está seteado (D-MATZ-3).
    """
    if _auth_failed:
        return (
            ProbeResult("get_active_orders", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    if _PRIMARY_ACCOUNT is None:
        return (
            ProbeResult("get_active_orders", "SKIPPED", "no PRIMARY_ACCOUNT env var"),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/order/actives"
    try:
        raw = _matriz_request("GET", path, params={"accountId": _PRIMARY_ACCOUNT})
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_active_orders levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {orders: [...]}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_active_orders", "FINDING", f"{fid} (OPEN)"), None)
    orders = raw.get("orders")
    if not isinstance(orders, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_active_orders envelope shape incorrecto",
            expected="raw['orders'] es list",
            actual=f"raw['orders']={type(orders).__name__}",
            diff="envelope key 'orders' ausente o no-list",
            base_url=base_url,
        )
        return (ProbeResult("get_active_orders", "FINDING", f"{fid} (OPEN)"), None)
    return (ProbeResult("get_active_orders", "PASS", f"{len(orders)} active orders"), orders)


def probe_get_filled_orders() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 12 (D-MATZ-29 #12): ``GET /rest/order/filleds`` con ``PRIMARY_ACCOUNT``.

    SKIPPED si ``PRIMARY_ACCOUNT`` no está seteado (D-MATZ-3).
    """
    if _auth_failed:
        return (
            ProbeResult("get_filled_orders", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    if _PRIMARY_ACCOUNT is None:
        return (
            ProbeResult("get_filled_orders", "SKIPPED", "no PRIMARY_ACCOUNT env var"),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/order/filleds"
    try:
        raw = _matriz_request("GET", path, params={"accountId": _PRIMARY_ACCOUNT})
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_filled_orders levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {orders: [...]}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_filled_orders", "FINDING", f"{fid} (OPEN)"), None)
    orders = raw.get("orders")
    if not isinstance(orders, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_filled_orders envelope shape incorrecto",
            expected="raw['orders'] es list",
            actual=f"raw['orders']={type(orders).__name__}",
            diff="envelope key 'orders' ausente o no-list",
            base_url=base_url,
        )
        return (ProbeResult("get_filled_orders", "FINDING", f"{fid} (OPEN)"), None)
    return (ProbeResult("get_filled_orders", "PASS", f"{len(orders)} filled orders"), orders)


def probe_get_all_orders() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 13 (D-MATZ-29 #13): ``GET /rest/order/all`` con ``PRIMARY_ACCOUNT``.

    SKIPPED si ``PRIMARY_ACCOUNT`` no está seteado (D-MATZ-3).
    """
    if _auth_failed:
        return (
            ProbeResult("get_all_orders", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    if _PRIMARY_ACCOUNT is None:
        return (
            ProbeResult("get_all_orders", "SKIPPED", "no PRIMARY_ACCOUNT env var"),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/order/all"
    try:
        raw = _matriz_request("GET", path, params={"accountId": _PRIMARY_ACCOUNT})
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_all_orders levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {orders: [...]}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_all_orders", "FINDING", f"{fid} (OPEN)"), None)
    orders = raw.get("orders")
    if not isinstance(orders, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_all_orders envelope shape incorrecto",
            expected="raw['orders'] es list",
            actual=f"raw['orders']={type(orders).__name__}",
            diff="envelope key 'orders' ausente o no-list",
            base_url=base_url,
        )
        return (ProbeResult("get_all_orders", "FINDING", f"{fid} (OPEN)"), None)
    return (ProbeResult("get_all_orders", "PASS", f"{len(orders)} total orders"), orders)


def probe_get_order_status() -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 14 (D-MATZ-29 #14): ``GET /rest/order/id`` con ``cl_ord_id``+``proprietary``.

    SKIPPED si ``MATRIZ_SAMPLE_CL_ORD_ID`` o ``MATRIZ_SAMPLE_PROPRIETARY`` ausentes (D-MATZ-4).
    """
    if _auth_failed:
        return (
            ProbeResult("get_order_status", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    if _SAMPLE_CL_ORD_ID is None or _SAMPLE_PROPRIETARY is None:
        return (
            ProbeResult(
                "get_order_status",
                "SKIPPED",
                "no MATRIZ_SAMPLE_CL_ORD_ID / MATRIZ_SAMPLE_PROPRIETARY env vars",
            ),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/order/id"
    try:
        raw = _matriz_request(
            "GET",
            path,
            params={"clOrdId": _SAMPLE_CL_ORD_ID, "proprietary": _SAMPLE_PROPRIETARY},
        )
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_order_status levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {order: {...}}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_order_status", "FINDING", f"{fid} (OPEN)"), None)
    order = raw.get("order")
    if not isinstance(order, dict):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_order_status envelope shape incorrecto",
            expected="raw['order'] es dict",
            actual=f"raw['order']={type(order).__name__}",
            diff="envelope key 'order' ausente o no-dict",
            base_url=base_url,
        )
        return (ProbeResult("get_order_status", "FINDING", f"{fid} (OPEN)"), None)
    return (
        ProbeResult("get_order_status", "PASS", f"clOrdId={_SAMPLE_CL_ORD_ID}"),
        order,
    )


def probe_get_order_history() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 15 (D-MATZ-29 #15): ``GET /rest/order/allById`` con ``cl_ord_id``+``proprietary``.

    SKIPPED si ``MATRIZ_SAMPLE_CL_ORD_ID`` o ``MATRIZ_SAMPLE_PROPRIETARY`` ausentes (D-MATZ-4).
    """
    if _auth_failed:
        return (
            ProbeResult("get_order_history", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    if _SAMPLE_CL_ORD_ID is None or _SAMPLE_PROPRIETARY is None:
        return (
            ProbeResult(
                "get_order_history",
                "SKIPPED",
                "no MATRIZ_SAMPLE_CL_ORD_ID / MATRIZ_SAMPLE_PROPRIETARY env vars",
            ),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/order/allById"
    try:
        raw = _matriz_request(
            "GET",
            path,
            params={"clOrdId": _SAMPLE_CL_ORD_ID, "proprietary": _SAMPLE_PROPRIETARY},
        )
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_order_history levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {orders: [...]}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_order_history", "FINDING", f"{fid} (OPEN)"), None)
    orders = raw.get("orders")
    if not isinstance(orders, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_order_history envelope shape incorrecto",
            expected="raw['orders'] es list",
            actual=f"raw['orders']={type(orders).__name__}",
            diff="envelope key 'orders' ausente o no-list",
            base_url=base_url,
        )
        return (ProbeResult("get_order_history", "FINDING", f"{fid} (OPEN)"), None)
    return (
        ProbeResult("get_order_history", "PASS", f"{len(orders)} history rows"),
        orders,
    )


def probe_get_order_by_exec_id() -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 16 (D-MATZ-29 #16): ``GET /rest/order/byExecId`` con ``MATRIZ_SAMPLE_EXEC_ID``.

    SKIPPED si ``MATRIZ_SAMPLE_EXEC_ID`` no está seteado (D-MATZ-4).
    """
    if _auth_failed:
        return (
            ProbeResult("get_order_by_exec_id", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    if _SAMPLE_EXEC_ID is None:
        return (
            ProbeResult("get_order_by_exec_id", "SKIPPED", "no MATRIZ_SAMPLE_EXEC_ID env var"),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/order/byExecId"
    try:
        raw = _matriz_request("GET", path, params={"execId": _SAMPLE_EXEC_ID})
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_order_by_exec_id levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {order: {...}}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_order_by_exec_id", "FINDING", f"{fid} (OPEN)"), None)
    order = raw.get("order")
    if not isinstance(order, dict):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_order_by_exec_id envelope shape incorrecto",
            expected="raw['order'] es dict",
            actual=f"raw['order']={type(order).__name__}",
            diff="envelope key 'order' ausente o no-dict",
            base_url=base_url,
        )
        return (ProbeResult("get_order_by_exec_id", "FINDING", f"{fid} (OPEN)"), None)
    return (
        ProbeResult("get_order_by_exec_id", "PASS", f"execId={_SAMPLE_EXEC_ID}"),
        order,
    )


def probe_get_positions() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 17 (D-MATZ-29 #17): ``GET /rest/risk/position/getPositions/{account}``.

    **Risk API HTTP Basic Auth** (Pitfall 2 RESEARCH L640): bypassa ``_get`` y
    llama ``_matriz_request`` directo con ``auth_basic=_risk_auth()``.
    SKIPPED si ``PRIMARY_ACCOUNT`` ausente (D-MATZ-3).
    """
    if _auth_failed:
        return (
            ProbeResult("get_positions", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    if _PRIMARY_ACCOUNT is None:
        return (
            ProbeResult("get_positions", "SKIPPED", "no PRIMARY_ACCOUNT env var"),
            None,
        )
    base_url = primary.client._base_url
    path = f"/rest/risk/position/getPositions/{_PRIMARY_ACCOUNT}"
    try:
        raw = _matriz_request("GET", path, auth_basic=_risk_auth())
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_positions levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {positions: [...]}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente (ejercita _unwrap fix Plan 05-01)",
            base_url=base_url,
        )
        return (ProbeResult("get_positions", "FINDING", f"{fid} (OPEN)"), None)
    positions = raw.get("positions")
    if not isinstance(positions, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_positions envelope shape incorrecto",
            expected="raw['positions'] es list",
            actual=f"raw['positions']={type(positions).__name__}",
            diff="envelope key 'positions' ausente o no-list",
            base_url=base_url,
        )
        return (ProbeResult("get_positions", "FINDING", f"{fid} (OPEN)"), None)
    return (ProbeResult("get_positions", "PASS", f"{len(positions)} positions"), positions)


def probe_get_detailed_positions() -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 18 (D-MATZ-29 #18): ``GET /rest/risk/detailedPosition/{account}``.

    Risk API HTTP Basic Auth. **SIN envelope key** — el payload raíz es el dict
    completo de ``DetailedPosition.from_api(raw)``. SKIPPED si ``PRIMARY_ACCOUNT``
    ausente (D-MATZ-3).
    """
    if _auth_failed:
        return (
            ProbeResult(
                "get_detailed_positions", "SKIPPED", f"auth failed: {_auth_failure_reason}"
            ),
            None,
        )
    if _PRIMARY_ACCOUNT is None:
        return (
            ProbeResult("get_detailed_positions", "SKIPPED", "no PRIMARY_ACCOUNT env var"),
            None,
        )
    base_url = primary.client._base_url
    path = f"/rest/risk/detailedPosition/{_PRIMARY_ACCOUNT}"
    try:
        raw = _matriz_request("GET", path, auth_basic=_risk_auth())
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_detailed_positions levantó PrimaryAPIError inesperado",
            expected="200 OK con dict {account, totalDailyDiffPlain, ...}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o status='ERROR' en payload",
            base_url=base_url,
        )
        return (ProbeResult("get_detailed_positions", "FINDING", f"{fid} (OPEN)"), None)
    if not isinstance(raw, dict):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_detailed_positions payload shape incorrecto",
            expected="payload raíz es dict (sin envelope key)",
            actual=f"raw={type(raw).__name__}",
            diff="payload raíz no es dict",
            base_url=base_url,
        )
        return (ProbeResult("get_detailed_positions", "FINDING", f"{fid} (OPEN)"), None)
    # WR-01 belt-and-suspenders: aunque PRIMARY_ACCOUNT está en `secrets` y
    # safe_print lo redacta, no insertamos el accountId completo en el detail
    # string. Reportamos sólo "received" como evidencia estructural — el
    # accountId real ya está en el endpoint template del schema snapshot
    # como placeholder <PRIMARY_ACCOUNT>.
    _ = raw.get("account", "<unknown>")
    return (
        ProbeResult("get_detailed_positions", "PASS", "account received"),
        raw,
    )


def probe_get_account_report() -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 19 (D-MATZ-29 #19): ``GET /rest/risk/accountReport/{account}``.

    Risk API HTTP Basic Auth. **SIN envelope key** — el payload raíz es el dict
    completo de ``AccountReport.from_api(raw)``. SKIPPED si ``PRIMARY_ACCOUNT``
    ausente (D-MATZ-3).
    """
    if _auth_failed:
        return (
            ProbeResult("get_account_report", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    if _PRIMARY_ACCOUNT is None:
        return (
            ProbeResult("get_account_report", "SKIPPED", "no PRIMARY_ACCOUNT env var"),
            None,
        )
    base_url = primary.client._base_url
    path = f"/rest/risk/accountReport/{_PRIMARY_ACCOUNT}"
    try:
        raw = _matriz_request("GET", path, auth_basic=_risk_auth())
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_account_report levantó PrimaryAPIError inesperado",
            expected="200 OK con dict {accountName, marketMember, ...}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o status='ERROR' en payload",
            base_url=base_url,
        )
        return (ProbeResult("get_account_report", "FINDING", f"{fid} (OPEN)"), None)
    if not isinstance(raw, dict):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_account_report payload shape incorrecto",
            expected="payload raíz es dict (sin envelope key)",
            actual=f"raw={type(raw).__name__}",
            diff="payload raíz no es dict",
            base_url=base_url,
        )
        return (ProbeResult("get_account_report", "FINDING", f"{fid} (OPEN)"), None)
    # WR-01: idem get_detailed_positions — no inserto el accountName real en
    # el detail string. La evidencia estructural ("received") basta para PASS;
    # el accountId real queda redactado por `safe_print` a través de la lista
    # secrets ahora que PRIMARY_ACCOUNT figura allí.
    _ = raw.get("accountName", "<unknown>")
    return (
        ProbeResult("get_account_report", "PASS", "accountName received"),
        raw,
    )


# ---------------------------------------------------------------------------
# Probe 20: field_type_map (D-MATZ-29 #20, MATZ-03)
# ---------------------------------------------------------------------------


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
    targets: list[tuple[str, Any, type]] = [
        ("segment", _first_dict(payloads.get("get_segments")), Segment),
        ("instrument", _first_dict(payloads.get("get_all_instruments")), Instrument),
        ("instrument_detail", payloads.get("get_instrument_detail"), InstrumentDetail),
        ("market_data", payloads.get("get_market_data"), MarketDataSnapshot),
        ("trade", _first_dict(payloads.get("get_trades")), Trade),
        ("order", _first_dict(payloads.get("get_all_orders")), Order),
        ("position", _first_dict(payloads.get("get_positions")), Position),
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


def probe_error_bogus_symbol() -> ProbeResult:
    """Probe 21 (D-MATZ-29 #21): símbolo inválido en ``get_market_data``.

    Distingue ``PrimaryAPIError(status='ERROR')`` mapeado (PASS) de
    ``httpx.HTTPStatusError`` HTTP 4xx no-mapeado (finding ERROR-MAP OPEN).
    """
    if _auth_failed:
        return ProbeResult("error_bogus_symbol", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = primary.client._base_url
    try:
        primary.get_market_data("ZZZZZZ-NOT-A-SYMBOL")
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
    except Exception as exc:
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


def probe_error_invalid_account() -> ProbeResult:
    """Probe 22 (D-MATZ-29 #22): account inválido en ``get_active_orders``.

    Distingue ``PrimaryAPIError(status='ERROR')`` mapeado (PASS) de HTTP 4xx
    no-mapeado (finding ERROR-MAP OPEN).
    """
    if _auth_failed:
        return ProbeResult(
            "error_invalid_account", "SKIPPED", f"auth failed: {_auth_failure_reason}"
        )
    base_url = primary.client._base_url
    try:
        primary.get_active_orders("INVALID-ACCT-XXXXX")
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
    except Exception as exc:
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


def probe_error_malformed_cfi() -> ProbeResult:
    """Probe 23 (D-MATZ-29 #23): CFI malformado en ``get_instruments_by_cfi``.

    Requiere ``cast(CFICode, 'INVALID-CFI')`` por mypy strict — el cliente
    acepta el string a runtime pero el upstream lo rechaza. Distingue
    PrimaryAPIError(status='ERROR') mapeado (PASS) de HTTP 4xx no-mapeado.
    """
    if _auth_failed:
        return ProbeResult("error_malformed_cfi", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = primary.client._base_url
    try:
        primary.get_instruments_by_cfi(cast(CFICode, "INVALID-CFI"))
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
    except Exception as exc:
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


def probe_schema_snapshot(payloads: dict[str, Any], base_url: str) -> ProbeResult:
    """Probe 24 (D-MATZ-29 #24): schema snapshot sweep.

    Itera _SCHEMA_FILES y para cada func_name presente en payloads invoca
    ``_write_or_check_schema`` con envelope D-21 + D-25 no-overwrite-on-drift.
    Acumula resultados PASS / FINDING. Si todos PASS → PASS. Si hay drifts
    → FINDING con fids correspondientes.
    """
    if _auth_failed:
        return ProbeResult("schema_snapshot", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    sample_params: dict[str, dict[str, Any]] = {
        "get_segments": {},
        "get_all_instruments": {},
        "get_instruments_details": {},
        "get_instrument_detail": {"symbol": _resolved_symbol or "<unresolved>"},
        "get_instruments_by_cfi_ESXXXX": {"CFICode": "ESXXXX"},
        "get_instruments_by_segment": {"segmentId": _resolved_segment or "<unresolved>"},
        "get_market_data": {"symbol": _resolved_symbol or "<unresolved>"},
        "get_trades": {"symbol": _resolved_symbol or "<unresolved>", "windowDays": 7},
        "get_active_orders": {"accountId": "<PRIMARY_ACCOUNT>"},
        "get_filled_orders": {"accountId": "<PRIMARY_ACCOUNT>"},
        "get_all_orders": {"accountId": "<PRIMARY_ACCOUNT>"},
        "get_order_status": {
            "clOrdId": "<MATRIZ_SAMPLE_CL_ORD_ID>",
            "proprietary": "<MATRIZ_SAMPLE_PROPRIETARY>",
        },
        "get_order_history": {
            "clOrdId": "<MATRIZ_SAMPLE_CL_ORD_ID>",
            "proprietary": "<MATRIZ_SAMPLE_PROPRIETARY>",
        },
        "get_order_by_exec_id": {"execId": "<MATRIZ_SAMPLE_EXEC_ID>"},
        "get_positions": {"account": "<PRIMARY_ACCOUNT>"},
        "get_detailed_positions": {"account": "<PRIMARY_ACCOUNT>"},
        "get_account_report": {"account": "<PRIMARY_ACCOUNT>"},
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
# main() lifecycle (D-MATZ-29 #25 cycle_closure + D-MATZ-27 EXPECTED terminal)
# ---------------------------------------------------------------------------


def main() -> None:
    """Driver lifecycle sync-only (D-MATZ-30).

    Secuencia:
    1. HARN-01 ``require_env`` gate — exit 0 si faltan credenciales.
    2. D-MATZ-33 hostname assert remarkets — exit 1 si base_url no es remarkets.
    3. ``write_findings(_PKG)`` para inicializar el findings file.
    4. Secrets discovery dinámico (D-MATZ-32): PRIMARY_USER, PRIMARY_PASSWORD del
       env + ``_token`` agregado dinámicamente tras probe_login_sync.
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

    # D-MATZ-33 belt-and-suspenders hostname assert: prevention contra prod.
    base = primary.client._base_url
    if "remarkets" not in base:
        print(
            f"ABORT: PRIMARY_BASE_URL={base!r} is not a remarkets sandbox URL — "
            "Phase 5 verification is remarkets-only by safety policy",
            file=sys.stderr,
        )
        sys.exit(1)

    write_findings(_PKG)

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

    results: list[ProbeResult] = []
    payloads: dict[str, Any] = {}

    # Probe 1: login.
    r1 = probe_login_sync()
    results.append(r1)
    token = getattr(primary.client, "_token", None)
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
        result, raw = probe_fn()
        results.append(result)
        if raw is not None:
            payloads[key] = raw

    # Probe 20: field_type_map (MATZ-03).
    results.append(probe_field_type_map(payloads))

    # Probes 21-23: error probes (MATZ-05). D-MATZ-24: DESPUÉS de happy-path
    # sweep y field_type_map para minimizar interferencia con state.
    results.append(probe_error_bogus_symbol())
    results.append(probe_error_invalid_account())
    results.append(probe_error_malformed_cfi())

    # Probe 24: schema snapshots (DRIFT-01 mirror, D-MATZ-24 después de errors).
    results.append(probe_schema_snapshot(payloads, base))

    # Probe 25: cycle_closure x 4 paquetes (D-MATZ-28, DRIFT-02).
    for pkg in (
        "ambito-financiero-client",
        "iol-client",
        "higyrus-client",
        "matriz-client",
    ):
        ok, missing = verify_cycle_closure(pkg)
        status_str = "PASS" if ok else "FAIL"
        detail = "" if ok else f"missing regressions: {', '.join(missing)}"
        results.append(
            ProbeResult(
                f"cycle_closure_{pkg.replace('-', '_')}",
                status_str,
                detail,
            )
        )
        if not ok:
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

    # D-MATZ-27 EXPECTED terminal: prod-vs-remarkets divergence acknowledged.
    # Esta ES la última invocación de append_finding sobre _PKG en main()
    # (Assumption A3 del plan).
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="SHAPE",
        surface="sync",
        status="EXPECTED",
        title="prod-vs-remarkets divergence acknowledged",
        expected=(
            "verification limited to remarkets sandbox by safety policy "
            "(REQUIREMENTS.md Out of Scope)"
        ),
        actual=(
            "prod (api.primary.com.ar) shape unverified; sandbox shape "
            "committed in .planning/verification/schemas/matriz-client/"
        ),
        diff="N/A (acknowledged limitation, not detected drift)",
        base_url=base,
    )

    # Stdout verbatim D-02 + SUMMARY. Cada línea via safe_print con secrets.
    counts: dict[str, int] = {"PASS": 0, "FAIL": 0, "SKIPPED": 0, "FINDING": 0}
    for r in results:
        line = f"PROBE {r.name}: {r.status} {r.detail}".rstrip()
        safe_print(line, secrets=secrets)
        counts[r.status] = counts.get(r.status, 0) + 1
    safe_print(
        f"SUMMARY: PASS={counts['PASS']} FAIL={counts['FAIL']} "
        f"SKIPPED={counts['SKIPPED']} FINDING={counts['FINDING']}",
        secrets=secrets,
    )


if __name__ == "__main__":
    main()
