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
import sys  # noqa: F401  # used by main() in Part B (Task 2.4)
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import httpx  # noqa: F401  # used by error probes in Part B (Task 2.4)
from verification import (
    append_finding,
    diff_safemodel_bidirectional,  # noqa: F401  # used by probe_field_type_map in Part B
    require_env,  # noqa: F401  # used by main() in Part B
    safe_print,  # noqa: F401  # used by main() in Part B
    schema_of,
    write_findings,  # noqa: F401  # used by main() in Part B
)
from verification.cycle_report import (  # noqa: F401  # used by main() in Part B
    verify_cycle_closure,
)

import matriz_client as primary
from matriz_client import PrimaryAPIError
from matriz_client.client import _request as _matriz_request
from matriz_client.client import _risk_auth
from matriz_client.exceptions import AuthenticationError
from matriz_client.models import (
    AccountReport,  # noqa: F401  # used by probe_field_type_map in Part B
    DetailedPosition,  # noqa: F401  # used by probe_field_type_map in Part B
    Instrument,  # noqa: F401  # used by probe_field_type_map in Part B
    InstrumentDetail,  # noqa: F401  # used by probe_field_type_map in Part B
    MarketDataSnapshot,  # noqa: F401  # used by probe_field_type_map in Part B
    Order,  # noqa: F401  # used by probe_field_type_map in Part B
    Position,  # noqa: F401  # used by probe_field_type_map in Part B
    Segment,  # noqa: F401  # used by probe_field_type_map in Part B
    Trade,  # noqa: F401  # used by probe_field_type_map in Part B
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
    return (
        ProbeResult("get_detailed_positions", "PASS", f"account={raw.get('account', '<unknown>')}"),
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
    return (
        ProbeResult(
            "get_account_report",
            "PASS",
            f"accountName={raw.get('accountName', '<unknown>')}",
        ),
        raw,
    )
