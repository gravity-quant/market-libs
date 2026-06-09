# Phase 5: Matriz Verification — Pattern Map

**Mapped:** 2026-06-09
**Files analyzed:** 13 (1 rewrite + 1 refactor + 3 source edits + 2 new helpers + 1 barrel update + 1 test append + 4 generated artefacts)
**Analogs found:** 13 / 13 (todo target tiene un análogo concreto en Phase 2-4 + en el propio repo)

> Phase 5 reusa verbatim el lifecycle establecido en Phases 2-4 (Ámbito → IOL → Higyrus).
> Cada target abajo nombra un único análogo cercano y enumera deviaciones que el planner debe
> obligar. Excerpts de código son concretos — copiar la estructura, cambiar los nombres.
> Las decisiones D-MATZ-1..D-MATZ-34 de 05-CONTEXT.md son la fuente de truth de las desviaciones;
> este mapa de patrones es el cómo (copiar de dónde).

---

## File Classification

| Target File | Role | Data Flow | Closest Analog | Match Quality |
|-------------|------|-----------|----------------|---------------|
| `main_matriz.py` (REWRITE 57→~1800 líneas) | driver (verification entry point, sync-only) | request-response + IO write | `main_higyrus.py` (Phase 4 — 18 probes, recursive SafeModel diff inline, cascade SKIPPED, schema snapshot D-21/D-25, `_resolved_cuenta` flow) | exact role; **deviation: NO `asyncio.run`** (matriz es sync-only por diseño, sin `aio.py`) |
| `main_higyrus.py` (REFACTOR — replace inline helper con import) | driver | request-response | Self (lines 89-93, 200-293 inline `_diff_safemodel_bidirectional`) | exact (in-file refactor) |
| `verification/safemodel_diff.py` (NEW ~80 líneas) | utility helper (module-level genérico) | transform (introspection) | `main_higyrus.py` líneas 205-293 (`_is_optional`, `_nested_safemodel_class`, `_is_list_of_safemodel`, `_diff_safemodel_bidirectional`) — copia exacta con rename público | exact (promotion) |
| `verification/cycle_report.py` (NEW ~60 líneas) | utility helper (parse markdown + filesystem check) | transform (parse + assert) | `verification/findings.py` lines 212-345 (`_parse_findings` + `_Finding` dataclass) — reusa el parser interno | role-match (mismo shape: parsea findings.md, retorna tuple) |
| `verification/__init__.py` (UPDATE barrel) | export aggregator | n/a | Self (lines 29-49 — existing barrel pattern) | exact (in-file append) |
| `packages/matriz-client/src/matriz_client/client.py` (EDIT: `_unwrap` helper + 18 sites + `_token` raise + 3 docstrings) | library code (HTTP client, sync surface) | request-response | Self (lines 165-172 — el existing `data.get("status") == "ERROR"` typed-raise pattern); **HIGY-04 fix pattern**: `packages/higyrus-client/src/higyrus_client/client.py:222-231` (`raise HigyrusAPIError(...)` con "shape mismatch") | exact (in-file precedent + Phase 4 typed-exception parallel) |
| `packages/matriz-client/tests/test_client.py` (APPEND 2 secciones, ~30 tests) | test (mocked, sync surface) | n/a | `packages/higyrus-client/tests/test_client.py` lines 145-315 (`# ------ Verified live (Phase 4) ------` + `# ------ Regressions ------`); auth/orders mock pattern dentro del mismo `test_client.py` líneas 153-203 | exact role + data flow |
| `packages/matriz-client/.env.example` (APPEND 5 vars opcionales) | config (env template) | n/a | `packages/higyrus-client/.env.example` lines 8-21 (HIGYRUS_SAMPLE_* opt-in vars) | exact (in-file append + Phase 4 convention) |
| `.planning/verification/matriz-client-findings.md` (GENERATE + EXPECTED + cycle closure) | generated artefact (findings ledger) | event-driven append | `.planning/verification/higyrus-client-findings.md` (Phase 4 output) | exact format (generado por `write_findings` + `append_finding`) |
| `.planning/verification/{ambito-financiero,iol,higyrus,matriz}-client-findings.md` (APPEND `## Cycle Closure`) | modify existing artefact (4 archivos) | text append | Self (4 archivos pre-existentes) | **no analog para sección "## Cycle Closure"** — D-MATZ-25 introduce un nuevo formato; planner inventa el shape pero RESEARCH.md L1037-1040 + Assumption A3 indican que el append es la **última operación** del driver para no chocar con re-serialización de `append_finding` |
| `.planning/verification/schemas/matriz-client/<endpoint>.json` × ~11-19 (GENERATE) | generated artefact (schema snapshot) | n/a | `.planning/verification/schemas/higyrus-client/get-health.json` (envelope D-21 — endpoint, client_function, captured_at, base_url, sample_params, schema) | exact (literal envelope copy) |
| `.planning/verification/CYCLE-REPORT.md` (NEW) | generated artefact (consolidated report cross-package) | n/a | **No existing analog** — D-MATZ-26 introduce un nuevo formato consolidando 4 dimensiones; planner inventa el shape ancorado a CONTEXT.md L546-583 literal |

---

## Pattern Assignments

### 1. `main_matriz.py` (REWRITE) — driver, request-response sync-only

**Analog:** `/Users/sebadlf/development/becerra/market-libs/main_higyrus.py` (Phase 4, 2380 líneas, 18 probes)

**Why this analog:** Phase 4 estableció el shape final del driver: ~18-25 probes nombrados, `ProbeResult(name, status, detail)`, cascade SKIPPED vía `_auth_failed` flag, schema snapshot envelope D-21 con D-25 no-overwrite-on-drift, `_fid_counter` con `F-NN` zero-padded, `safe_print(...)` con secrets dinámicos, `write_findings(pkg)` upfront idempotente. Phase 5 reusa verbatim cada pieza y agrega: (1) hostname assert D-MATZ-33 antes de cualquier llamada, (2) sync-only lifecycle sin `asyncio.run` ni `_async_main`, (3) `_resolved_symbol` + `_resolved_segment` resolution flow, (4) consumo de helpers promovidos desde el barrel `verification.diff_safemodel_bidirectional` + `verification.cycle_report.verify_cycle_closure`, (5) bucle de cycle closure cross-package sobre 4 paquetes, (6) finding EXPECTED terminal hardcoded prod-vs-remarkets al final del run.

**Imports pattern** (copy structure from `main_higyrus.py:81-108`):

```python
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import httpx
from verification import (
    append_finding,
    diff_safemodel_bidirectional,  # NEW D-MATZ-19 export
    require_env,
    safe_print,
    schema_of,
    write_findings,
)
from verification.cycle_report import verify_cycle_closure  # NEW D-MATZ-28

import matriz_client as primary
from matriz_client import PrimaryAPIError
from matriz_client.client import _request as _matriz_request, _risk_auth  # for raw payload retention
from matriz_client.exceptions import AuthenticationError
from matriz_client.models import (
    AccountReport,
    DetailedPosition,
    Instrument,
    InstrumentDetail,
    MarketDataSnapshot,
    NewOrderResponse,
    Order,
    Position,
    Segment,
    Trade,
)
from matriz_client.types import CFICode
```

**Deviation from analog:** NO `asyncio`, `contextlib`, `from higyrus_client import aio` (matriz es sync-only). NO `format_bool` / `format_date` de `_params` (matriz no expone helpers de wire). Sí import directo de `cast` para `cast(CFICode, "INVALID-CFI")` D-MATZ-22. Imports de los 11 `_SafeModel` subclases que el probe `field_type_map` ejercitará.

**Module-level constants + `ProbeResult` + `_next_fid` pattern** (copy from `main_higyrus.py:110-198`):

```python
_PKG = "matriz-client"
_REPO_ROOT = Path(__file__).resolve().parent
_SCHEMA_DIR = _REPO_ROOT / ".planning" / "verification" / "schemas" / _PKG
_SCHEMA_FILES: dict[str, Path] = {
    "get_segments": _SCHEMA_DIR / "get-segments.json",
    "get_all_instruments": _SCHEMA_DIR / "get-all-instruments.json",
    "get_instruments_details": _SCHEMA_DIR / "get-instruments-details.json",
    "get_instrument_detail": _SCHEMA_DIR / "get-instrument-detail.json",
    "get_instruments_by_cfi_ESXXXX": _SCHEMA_DIR / "get-instruments-by-cfi-ESXXXX.json",
    "get_instruments_by_segment": _SCHEMA_DIR / "get-instruments-by-segment.json",
    "get_market_data": _SCHEMA_DIR / "get-market-data.json",
    "get_trades": _SCHEMA_DIR / "get-trades.json",
    # opt-in condicionales (PRIMARY_ACCOUNT-gated):
    "get_active_orders": _SCHEMA_DIR / "get-active-orders.json",
    "get_filled_orders": _SCHEMA_DIR / "get-filled-orders.json",
    "get_all_orders": _SCHEMA_DIR / "get-all-orders.json",
    "get_positions": _SCHEMA_DIR / "get-positions.json",
    "get_detailed_positions": _SCHEMA_DIR / "get-detailed-positions.json",
    "get_account_report": _SCHEMA_DIR / "get-account-report.json",
    # opt-in condicionales (MATRIZ_SAMPLE_*-gated):
    "get_order_status": _SCHEMA_DIR / "get-order-status.json",
    "get_order_history": _SCHEMA_DIR / "get-order-history.json",
    "get_order_by_exec_id": _SCHEMA_DIR / "get-order-by-exec-id.json",
}

_ENDPOINT_TEMPLATES: dict[str, str] = {
    "get_segments": "/rest/segment/all",
    "get_all_instruments": "/rest/instruments/all",
    # ... 16-17 entradas total
}

# D-MATZ-33 env vars opcionales
_SAMPLE_SYMBOL: str | None = os.getenv("MATRIZ_SAMPLE_SYMBOL")
_SAMPLE_CL_ORD_ID: str | None = os.getenv("MATRIZ_SAMPLE_CL_ORD_ID")
_SAMPLE_PROPRIETARY: str | None = os.getenv("MATRIZ_SAMPLE_PROPRIETARY")
_SAMPLE_EXEC_ID: str | None = os.getenv("MATRIZ_SAMPLE_EXEC_ID")
_PRIMARY_ACCOUNT: str | None = os.getenv("PRIMARY_ACCOUNT")

# Cascade SKIPPED flag (D-MATZ-31)
_auth_failed: bool = False
_auth_failure_reason: str = ""

# Resolved samples (D-MATZ-1, D-MATZ-2)
_resolved_symbol: str | None = None
_resolved_segment: str | None = None

_fid_counter: int = 0


def _next_fid() -> str:
    """Devuelve el siguiente ``F-NN`` (NN zero-padded a 2 dígitos)."""
    global _fid_counter
    _fid_counter += 1
    return f"F-{_fid_counter:02d}"


@dataclass(frozen=True, slots=True)
class ProbeResult:
    name: str
    status: str  # "PASS" | "FAIL" | "SKIPPED" | "FINDING"
    detail: str
```

**Deviation from analog:** NO `_D_HIGY_10_ORDER` presentation-order tuple obligatorio (matriz puede usar el orden de ejecución para presentación — Phase 4 distinguía exec vs presentation porque sync+async se entrelazaban; matriz es secuencial puro). NO `HIGYRUS_*` env vars: usar `PRIMARY_USER`/`PRIMARY_PASSWORD`/`PRIMARY_BASE_URL`/`PRIMARY_ACCOUNT`/`MATRIZ_SAMPLE_*`.

**Probe function pattern with cascade SKIPPED + finding emission** (copy from `main_higyrus.py:583-659` — `probe_get_health_sync`):

```python
def probe_get_segments() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe: read + envelope ["segments"]; resuelve _resolved_segment."""
    if _auth_failed:
        return (
            ProbeResult("get_segments", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    global _resolved_segment
    base_url = primary.client._base_url
    try:
        raw = _matriz_request("GET", "/rest/segment/all")
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
            title="get_segments PrimaryAPIError inesperado",
            expected="200 OK + dict con envelope 'segments'",
            actual=repr(exc), diff=f"description={exc.description!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_segments", "FINDING", f"{fid} (OPEN)"), None)
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
            title=f"get_segments unexpected {type(exc).__name__}",
            expected="200 OK + dict con envelope 'segments'",
            actual=repr(exc), diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_segments", "FINDING", f"{fid} (OPEN)"), None)
    segments_raw = raw.get("segments")
    if not isinstance(segments_raw, list):
        fid = _next_fid()
        append_finding(
            _PKG, fid=fid, class_="SHAPE", surface="sync", status="OPEN",
            title="get_segments envelope shape inesperada",
            expected="dict con `segments` lista",
            actual=f"segments type={type(segments_raw).__name__}",
            diff=f"raw keys={sorted(raw.keys()) if isinstance(raw, dict) else 'n/a'}",
            base_url=base_url,
        )
        return (ProbeResult("get_segments", "FINDING", f"{fid} (OPEN)"), None)
    if segments_raw:
        first = segments_raw[0]
        if isinstance(first, dict):
            _resolved_segment = first.get("marketSegmentId")
    return (ProbeResult("get_segments", "PASS", f"{len(segments_raw)} segments"), segments_raw)
```

**Deviation from analog:** Surface es siempre `"sync"` (sin async). Cada probe que resuelve sample sets el global module-level (`_resolved_symbol`/`_resolved_segment`) consistente con `_resolved_cuenta` en main_higyrus.py L176, L296. Las 3 condiciones de error (sin envelope key) reciben `class_="SHAPE"` en lugar de `"ERROR-MAP"` (la última es para errores explícitos de protocolo: `PrimaryAPIError`).

**Risk API probe pattern (HTTP Basic Auth)** (Pitfall 2 de RESEARCH L640):

```python
def probe_get_positions() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    if _auth_failed:
        return (ProbeResult("get_positions", "SKIPPED", f"auth failed: {_auth_failure_reason}"), None)
    if not _PRIMARY_ACCOUNT:
        return (ProbeResult("get_positions", "SKIPPED", "missing PRIMARY_ACCOUNT env var"), None)
    base_url = primary.client._base_url
    try:
        raw = _matriz_request(
            "GET",
            f"/rest/risk/position/getPositions/{_PRIMARY_ACCOUNT}",
            auth_basic=_risk_auth(),
        )
    except PrimaryAPIError as exc:
        # ... finding ERROR-MAP OPEN
        ...
    # ... envelope check + return
```

**Critical:** llamar `_matriz_request("GET", path, auth_basic=_risk_auth())` directo (NO `_get`), porque `_get` siempre fluye por X-Auth-Token.

**Error probe with HTTP 4xx vs `{"status":"ERROR"}` distinction** (verbatim CONTEXT.md L498-519 / RESEARCH L883-938):

```python
def probe_error_bogus_symbol() -> ProbeResult:
    """Probe error #1 (D-MATZ-22): bogus symbol → expect PrimaryAPIError."""
    if _auth_failed:
        return ProbeResult("error_bogus_symbol", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = primary.client._base_url
    try:
        primary.get_market_data("ZZZZZZ-NOT-A-SYMBOL")
    except PrimaryAPIError as e:
        if e.status == "ERROR":
            return ProbeResult(
                "error_bogus_symbol", "PASS",
                f"PrimaryAPIError as expected: {e.description}",
            )
        fid = _next_fid()
        append_finding(
            _PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
            title="PrimaryAPIError with non-ERROR status",
            expected="PrimaryAPIError(status='ERROR') for bogus symbol",
            actual=f"PrimaryAPIError(status={e.status!r}, description={e.description!r})",
            diff="status != 'ERROR'", base_url=base_url,
        )
        return ProbeResult("error_bogus_symbol", "FINDING", f"{fid} (OPEN)")
    except httpx.HTTPStatusError as e:
        fid = _next_fid()
        append_finding(
            _PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
            title="HTTP 4xx not mapped to PrimaryAPIError",
            expected="PrimaryAPIError wrap for any error response",
            actual=f"httpx.HTTPStatusError {e.response.status_code} raw",
            diff="error mapping bypass — _raise_for_response missing or order incorrect",
            base_url=base_url,
        )
        return ProbeResult("error_bogus_symbol", "FINDING", f"{fid} (OPEN)")
    # ... (más excepts + sin-excepción fallback igual que Phase 4)
```

**Schema snapshot `_write_or_check_schema` helper** (copy verbatim from `main_higyrus.py:409-455`):

```python
def _write_or_check_schema(
    func_name: str,
    endpoint_template: str,
    sample_params: dict[str, Any],
    raw_payload: Any,
    base_url: str,
) -> tuple[str, str]:
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
        _PKG, fid=fid, class_="SHAPE", surface="sync", status="OPEN",
        title=f"Schema drift en {func_name}",
        expected=json.dumps(committed.get("schema"), ensure_ascii=False),
        actual=json.dumps(actual_schema, ensure_ascii=False),
        diff="comparar expected vs actual; NO se sobreescribe baseline (D-25)",
        base_url=base_url,
    )
    return ("FINDING", f"{fid}|{file_path.name}")
```

**Deviation:** `surface="sync"` (no `"both"`), conjunto de archivos diferente (matriz tiene ~16-19 vs higyrus 5). El helper es portable; planner solo cambia `_SCHEMA_FILES` y `_ENDPOINT_TEMPLATES`.

**`field_type_map` probe usando el helper promovido** (refactor from `main_higyrus.py:1710-1786` — usar `diff_safemodel_bidirectional` del barrel en lugar de `_diff_safemodel_bidirectional` privado):

```python
def probe_field_type_map(payloads: dict[str, Any]) -> ProbeResult:
    """Probe field_type_map: diff bidireccional sobre los 11 modelos matriz (MATZ-03)."""
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
        # NewOrderResponse cubierto por mock-only (MATZ-06); opcional acá
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
                expected = "model y wire coinciden en el set de claves"
                diff_detail = (
                    f"key `{key}` ausente en wire bajo `{path}` (model: {model_cls.__name__})"
                )
            else:
                title = f"{path}.{key}: wire emite, model ignora (info)"
                actual = f"key `{key}` presente en wire bajo `{path}`"
                expected = "model declara el superset del wire"
                diff_detail = (
                    "backend posiblemente agregó campo nuevo; candidato a extender model"
                )
            append_finding(
                _PKG, fid=fid, class_="SHAPE", surface="sync", status="OPEN",
                title=title, expected=expected, actual=actual, diff=diff_detail,
                base_url=base_url,
            )
            fids.append(fid)
    if fids:
        return ProbeResult("field_type_map", "FINDING", f"{', '.join(fids)} (OPEN)")
    return ProbeResult("field_type_map", "PASS", "11 models, no field drift")
```

**Deviation:** import del helper desde `verification`, no inline. `surface="sync"`. 11 modelos en `targets` (matriz) vs 4 (higyrus).

**`main()` lifecycle (sin asyncio)** (copy structure from `main_higyrus.py:2224-2377`, drop async):

```python
def main() -> None:
    if not require_env(_PKG, ["PRIMARY_USER", "PRIMARY_PASSWORD"]):
        sys.exit(0)

    # D-MATZ-33 belt-and-suspenders hostname assert
    base = primary.client._base_url
    if "remarkets" not in base:
        print(
            f"ABORT: PRIMARY_BASE_URL={base!r} is not a remarkets sandbox URL — "
            "Phase 5 verification is remarkets-only by safety policy",
            file=sys.stderr,
        )
        sys.exit(1)

    write_findings(_PKG)

    # D-MATZ-32: secrets dinámicos (token se agrega tras login)
    secrets: list[str] = []
    _password_env = os.getenv("PRIMARY_PASSWORD", "")
    if _password_env:
        secrets.append(_password_env)
    _user_env = os.getenv("PRIMARY_USER", "")
    if _user_env and len(_user_env) >= 4:
        secrets.append(_user_env)

    results: list[ProbeResult] = []
    payloads: dict[str, Any] = {}

    # Probe 1: login (D-MATZ-29 #1) — setea _auth_failed si falla
    r = probe_login_sync()
    results.append(r)
    token = getattr(primary.client, "_token", None)
    if token:
        secrets.append(token)

    # Probes 2-19: happy-path sweep (cada uno respeta cascade SKIPPED interno)
    for fn in (
        probe_get_segments,
        probe_get_all_instruments,
        probe_get_instruments_details,
        probe_get_instrument_detail,
        probe_get_instruments_by_cfi_ESXXXX,
        probe_get_instruments_by_cfi_sanity,
        probe_get_instruments_by_segment,
        probe_get_market_data,
        probe_get_trades,
        probe_get_active_orders,
        probe_get_filled_orders,
        probe_get_all_orders,
        probe_get_order_status,
        probe_get_order_history,
        probe_get_order_by_exec_id,
        probe_get_positions,
        probe_get_detailed_positions,
        probe_get_account_report,
    ):
        r, raw = fn()
        results.append(r)
        if raw is not None:
            payloads[fn.__name__.replace("probe_", "")] = raw

    # Probe 20: field_type_map
    results.append(probe_field_type_map(payloads))

    # Probes 21-23: error probes (D-MATZ-22)
    results.append(probe_error_bogus_symbol())
    results.append(probe_error_invalid_account())
    results.append(probe_error_malformed_cfi())

    # Probe 24: schema snapshots
    results.append(probe_schema_snapshot(payloads, base))

    # Probe 25: cycle closure × 4 (D-MATZ-28)
    for pkg in ("ambito-financiero-client", "iol-client", "higyrus-client", "matriz-client"):
        ok, missing = verify_cycle_closure(pkg)
        status_str = "PASS" if ok else "FAIL"
        detail = "" if ok else f" — missing regressions: {', '.join(missing)}"
        results.append(
            ProbeResult(f"cycle_closure_{pkg.replace('-', '_')}", status_str, detail)
        )
        if not ok:
            fid = _next_fid()
            append_finding(
                pkg, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
                title=f"cycle closure: {len(missing)} CONFIRMED/FIXED without regression test",
                expected="every CONFIRMED/FIXED finding linked to existing test path",
                actual=f"missing regressions: {', '.join(missing)}",
                diff="see verify_cycle_closure output",
            )

    # D-MATZ-27: EXPECTED terminal prod-vs-remarkets
    fid = _next_fid()
    append_finding(
        _PKG, fid=fid, class_="SHAPE", surface="sync", status="EXPECTED",
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
    )

    # Stdout verbatim D-02 + SUMMARY
    counts = {"PASS": 0, "FAIL": 0, "SKIPPED": 0, "FINDING": 0}
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
```

**Deviation:** NO `asyncio.run(_async_main(...))`, NO `async_results`, NO presentation-order tuple `_D_HIGY_10_ORDER` (matriz puede usar execution order para presentación; opcionalmente declarar tupla si el implementador prefiere consistencia con Phase 4 — pero D-MATZ-30 explícitamente acepta lifecycle simplificado).

---

### 2. `main_higyrus.py` (REFACTOR) — replace inline diff helper con import desde barrel (D-MATZ-20)

**Analog:** self (in-file refactor — líneas 89-93 imports + 200-293 inline helpers a remover)

**Refactor pattern**:

```python
# ANTES (líneas 89-93):
from collections.abc import Iterator
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

# DESPUÉS:
from typing import Any

# (eliminados: Iterator, NoneType, UnionType, Union, get_args, get_origin, get_type_hints)
```

```python
# ANTES (líneas 96-97):
from verification import require_env, safe_print, schema_of, write_findings
from verification.findings import append_finding

# DESPUÉS:
from verification import (
    append_finding,
    diff_safemodel_bidirectional,  # NEW D-MATZ-19
    require_env,
    safe_print,
    schema_of,
    write_findings,
)
```

```python
# ELIMINAR líneas 205-293 enteras:
# def _is_optional(hint): ...
# def _nested_safemodel_class(hint): ...
# def _is_list_of_safemodel(hint): ...
# def _diff_safemodel_bidirectional(payload, model_cls, path=""): ...
```

```python
# REEMPLAZAR llamada en línea 1755:
# ANTES:
for path, direction, key in _diff_safemodel_bidirectional(
    payload, model_cls, path=f".{root_name}"
):
# DESPUÉS:
for path, direction, key in diff_safemodel_bidirectional(
    payload, model_cls, path=f".{root_name}"
):
```

**Deviation from analog:** ninguna — es un refactor pura promoción. Los tests Phase 4 (`packages/higyrus-client/tests/test_client.py` líneas 250-315 — Regressions) NO dependen del helper inline directamente; ejercitan el cliente. Sin embargo, **el plan debe ejecutar `uv run pytest packages/higyrus-client/ -q` post-refactor para confirmar que Phase 4 sigue verde** (Assumption A1 de RESEARCH L978).

**Critical** (Assumption A1 / Open Question #3): el helper promovido **debe ser duck-typed** (`hasattr(cls, "from_api")` + `dataclasses.is_dataclass(cls)`) o aceptar `base_cls` opcional, porque matriz usa `_SafeModel` (con underscore) y higyrus usa `SafeModel` (sin underscore) — son clases distintas con misma signature. Si el helper hace `issubclass(cls, SafeModel)` con import directo de higyrus, falla con matriz. Recommendation RESEARCH L1001: **duck typing**.

---

### 3. `verification/safemodel_diff.py` (NEW) — promotion del helper Phase 4 D-MATZ-18

**Analog:** `main_higyrus.py:205-293` (4 funciones inline a promover)

**Why this analog:** es la fuente literal. Phase 4 D-HIGY-4 lockeó la signature y la semantics; D-MATZ-18 mandata la promoción sin cambios funcionales.

**Excerpt verbatim a copiar (con rename público + duck-typing per Open Question #3):**

```python
"""Helper de diff bidireccional entre wire payload y SafeModel declarado.

Promovido en Phase 5 desde la copia inline de ``main_higyrus.py`` (Phase 4
D-HIGY-4). Centraliza el mecanismo de detección de field-drop silencioso
(``model-only`` direction → FALSE PASS riesgo) y de campos nuevos del backend
(``wire-only`` direction → info).

Reusable cross-package vía duck typing: cualquier ``dataclass`` con classmethod
``from_api(payload)`` (la convención de SafeModel base en los paquetes higyrus
y matriz) es admitida.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

__all__ = ["diff_safemodel_bidirectional"]


def _is_optional(hint: Any) -> bool:
    """True si hint es Optional[T] / T | None."""
    origin = get_origin(hint)
    if origin is Union or origin is UnionType:
        return any(a is NoneType for a in get_args(hint))
    return False


def _is_safemodel_like(cls: Any) -> bool:
    """Duck-typing: clase con ``from_api`` classmethod y es dataclass.

    Aplica a higyrus ``SafeModel`` y a matriz ``_SafeModel`` por igual,
    sin cruzar imports entre paquetes.
    """
    return (
        isinstance(cls, type)
        and dataclasses.is_dataclass(cls)
        and callable(getattr(cls, "from_api", None))
    )


def _nested_safemodel_class(hint: Any) -> type | None:
    """Si hint es SafeModel subclass o list[SafeModel subclass], devolver la clase."""
    if _is_safemodel_like(hint):
        return hint  # type: ignore[return-value]
    if get_origin(hint) is list:
        args = get_args(hint)
        if args and _is_safemodel_like(args[0]):
            return args[0]  # type: ignore[return-value]
    return None


def _is_list_of_safemodel(hint: Any) -> bool:
    return get_origin(hint) is list and _nested_safemodel_class(hint) is not None


def diff_safemodel_bidirectional(
    payload: Any,
    model_cls: type,
    path: str = "",
) -> Iterator[tuple[str, str, str]]:
    """Yield ``(path, direction, key)`` tuples para cada divergencia model<->wire.

    ``direction in {'model-only', 'wire-only'}``:

    - ``'model-only'``: la key está declarada por el modelo pero AUSENTE en wire
      → FALSE PASS riesgo (``SafeModel.from_api`` sustituye default tipado).
    - ``'wire-only'``: la key está presente en wire pero AUSENTE en el modelo
      → info (backend agregó campo nuevo).

    Optional[T] / T | None ausente NO emite ``'model-only'`` (es la
    representación intencional del campo nullable).

    Recursivo en nested SafeModels y en ``list[SafeModel]`` (samplea el
    primer elemento, consistente con ``schema_of``).
    """
    if not isinstance(payload, dict):
        return
    hints = get_type_hints(model_cls)
    model_keys = set(hints.keys())
    wire_keys = set(payload.keys())
    for key in sorted(model_keys - wire_keys):
        hint = hints[key]
        if _is_optional(hint):
            continue
        yield (path, "model-only", key)
    for key in sorted(wire_keys - model_keys):
        yield (path, "wire-only", key)
    for key in model_keys & wire_keys:
        hint = hints[key]
        nested_payload = payload[key]
        nested_cls = _nested_safemodel_class(hint)
        if nested_cls is None:
            continue
        if _is_list_of_safemodel(hint):
            if isinstance(nested_payload, list) and nested_payload:
                yield from diff_safemodel_bidirectional(
                    nested_payload[0], nested_cls, f"{path}.{key}[0]"
                )
        else:
            yield from diff_safemodel_bidirectional(
                nested_payload, nested_cls, f"{path}.{key}"
            )
```

**Deviation from analog:** (1) reemplaza `issubclass(cls, SafeModel)` por duck typing `_is_safemodel_like` (cross-package compat); (2) rename `_diff_safemodel_bidirectional` → `diff_safemodel_bidirectional` (sin underscore, público); (3) docstring al tope del módulo nuevo (sin equivalente inline).

---

### 4. `verification/cycle_report.py` (NEW) — D-MATZ-28

**Analog:** `verification/findings.py:212-345` (`_parse_findings` + `_Finding` + `_ParsedFile`)

**Why this analog:** ya existe un parser interno de findings.md en `verification.findings`. El helper nuevo reusa este parser para extraer findings CONFIRMED/FIXED y validar que cada uno tenga `regression:` populado y path estructural válido.

**Excerpt pattern (a inventar — sin código verbatim previo, pero anclado al shape de `findings.py:212-345`):**

```python
"""Helper de validación de cierre de ciclo (D-MATZ-28, DRIFT-02).

Para cada paquete verificado, parsea ``<pkg>-findings.md`` y verifica que
cada finding en status ``CONFIRMED`` o ``FIXED`` linkea a un regression
test path existente (``<test_file>::<test_name>``).

Validación estructural — NO ejecuta pytest. Suficiente para detectar gaps
del ciclo donde un bug fue clasificado como fix pero faltó el test.
"""

from __future__ import annotations

import re
from pathlib import Path

from verification.findings import findings_path

__all__ = ["verify_cycle_closure"]

_REPO_ROOT = Path(__file__).resolve().parent.parent
_REGRESSION_RE = re.compile(r"^([^:]+\.py)::([A-Za-z_][A-Za-z0-9_]*)$")


def verify_cycle_closure(pkg: str) -> tuple[bool, list[str]]:
    """Asserta que todos los findings CONFIRMED/FIXED del paquete tienen regression.

    Args:
        pkg: Slug del paquete (e.g. ``"matriz-client"``).

    Returns:
        (ok, missing_regressions)
        - ``ok=True`` si todos los CONFIRMED/FIXED tienen ``regression`` válida
          (path ``<file>.py::<test_name>``) y el archivo existe en filesystem.
        - ``missing_regressions``: lista de fids sin regression válida.
    """
    path = findings_path(pkg)
    if not path.exists():
        return (True, [])  # nothing to validate
    text = path.read_text(encoding="utf-8")
    # Parse findings con detection de status + regression field.
    # (Implementación interna: regex sobre las secciones "### F-NN -- <title>"
    # extrayendo "**Status:** \`<status>\`" y un campo opcional "- **Regression:**
    # <test_file>::<test_name>". Si el formato del finding no incluye el campo
    # regression, el field stays None y el finding cuenta como missing.)
    missing: list[str] = []
    for fid, status, regression in _iter_findings(text):
        if status not in ("CONFIRMED", "FIXED"):
            continue
        if not regression:
            missing.append(fid)
            continue
        m = _REGRESSION_RE.match(regression)
        if not m:
            missing.append(fid)
            continue
        test_file_rel = m.group(1)
        test_file_abs = (_REPO_ROOT / test_file_rel).resolve()
        if not test_file_abs.exists():
            missing.append(fid)
            continue
        # Verificar que el test_name aparece como `def test_<name>` en el file
        # (estructural, sin pytest collection).
        contents = test_file_abs.read_text(encoding="utf-8")
        if f"def {m.group(2)}(" not in contents:
            missing.append(fid)
    return (not missing, missing)


def _iter_findings(text: str) -> "list[tuple[str, str, str | None]]":
    """Itera (fid, status, regression_path_or_None) por finding parseado.

    Helper interno; el formato exacto del campo `regression:` queda discrecional
    al planner (puede inferirse del Index/Detalle o de un campo agregado al
    formato actual de FINDINGS-TEMPLATE.md).
    """
    # Implementación delegada al planner: regex sobre secciones detalle.
    # ... (similar a verification.findings._parse_findings)
    ...
```

**Deviation from analog:** archivo nuevo desde cero; el parser de `verification.findings._parse_findings` no expone `regression`, por lo que el helper nuevo parsea localmente (o el planner puede expandir `_Finding` para incluir el campo). Decisión discrecional D-MATZ-28: usar `ERROR-MAP` como class si el probe falla (CONTEXT.md L644 verbatim).

**Critical** (Pitfall RESEARCH L1100-1102 + Assumption A5): NO se requiere import de pytest; el parse es estructural. El finding ``regression`` field es parte del shape del ``<pkg>-findings.md`` que ya está documentado en FINDINGS-TEMPLATE.md.

---

### 5. `verification/__init__.py` (UPDATE barrel) — D-MATZ-19

**Analog:** self (líneas 29-49)

**Update pattern**:

```python
# AGREGAR imports (después de los existentes):
from verification.safemodel_diff import diff_safemodel_bidirectional

# AGREGAR a __all__ (orden alfabético — preservar el orden existente):
__all__ = [
    "Denylist",
    "anonymize",
    "append_finding",
    "capture",
    "diff_safemodel_bidirectional",  # NEW D-MATZ-19
    "mutating_allowed",
    "new_findings",
    "redact",
    "require_env",
    "safe_print",
    "schema_of",
    "write_findings",
]
```

**Deviation:** ninguna; in-file append exacto al pattern existente. **NO se exporta `verify_cycle_closure` del barrel** — RESEARCH L728/L781 lo muestra como `from verification.cycle_report import verify_cycle_closure`, fuera del barrel por preferencia de modularidad. El planner puede decidir agregarlo al barrel si prefiere uniformidad.

---

### 6. `packages/matriz-client/src/matriz_client/client.py` (EDIT 4 things)

**Analog:** self (líneas 165-172 — patrón existente de typed raise) + Phase 4 sibling `packages/higyrus-client/src/higyrus_client/client.py:222-231` (mismo patrón aplicado para HIGY-04)

**Why this analog:** D-MATZ-9 verbatim cita el patrón Phase 4 D-HIGY-8 (rechazar nueva subclase, usar exception existente con marker en `description`). El precedente in-file `if data.get("status") == "ERROR": raise PrimaryAPIError(...)` muestra el shape exacto del raise typed.

#### 6a. Agregar helper `_unwrap` privado (D-MATZ-9 verbatim)

```python
# Insertar después de _get (línea 179) o donde el planner prefiera:

def _unwrap(data: dict[str, Any], key: str, endpoint: str) -> Any:
    """Return ``data[key]`` or raise ``PrimaryAPIError`` if missing.

    Args:
        data: Decoded JSON response from ``_request``/``_get``.
        key: Envelope key expected to wrap the payload (e.g., ``"order"``).
        endpoint: Path that produced the response, used for error context.

    Raises:
        PrimaryAPIError: If ``key`` is absent from ``data``.
    """
    if key not in data:
        raise PrimaryAPIError(
            status="ERROR",
            description=f"missing envelope key '{key}' in response from {endpoint}",
            message=None,
        )
    return data[key]
```

**Analog excerpt to mirror (el shape del raise typed, líneas 167-172 actuales):**

```python
if data.get("status") == "ERROR":
    raise PrimaryAPIError(
        status="ERROR",
        description=data.get("description"),
        message=data.get("message"),
    )
```

#### 6b. Refactor de 18 sites `_get(...)[key]` → `_unwrap(_get(...), key, path)` (D-MATZ-10)

**Refactor pattern (sample del site `get_segments`, línea 194):**

```python
# ANTES:
def get_segments() -> list[Segment]:
    """Return all available market segments."""
    return [Segment.from_api(s) for s in _get("/rest/segment/all")["segments"]]

# DESPUÉS:
def get_segments() -> list[Segment]:
    """Return all available market segments."""
    path = "/rest/segment/all"
    return [Segment.from_api(s) for s in _unwrap(_get(path), "segments", path)]
```

**Sample sites a refactorear (18 totales, verificados via grep):**

| # | Función | Endpoint | Envelope key | Línea actual |
|---|---------|----------|--------------|--------------|
| 1 | `get_segments` | `/rest/segment/all` | `segments` | 194 |
| 2 | `get_all_instruments` | `/rest/instruments/all` | `instruments` | 204 |
| 3 | `get_instruments_details` | `/rest/instruments/details` | `instruments` | 209 |
| 4 | `get_instrument_detail` | `/rest/instruments/detail` | `instrument` | 215 |
| 5 | `get_instruments_by_cfi` | `/rest/instruments/byCFICode` | `instruments` | 223 |
| 6 | `get_instruments_by_segment` | `/rest/instruments/bySegment` | `instruments` | 235 |
| 7 | `new_order` | `/rest/order/newSingleOrder` | `order` | 282 |
| 8 | `replace_order` | `/rest/order/replaceById` | `order` | 294 |
| 9 | `cancel_order` | `/rest/order/cancelById` | `order` | 301 |
| 10 | `get_order_status` | `/rest/order/id` | `order` | 308 |
| 11 | `get_order_history` | `/rest/order/allById` | `orders` | 316 |
| 12 | `get_active_orders` | `/rest/order/actives` | `orders` | 322 |
| 13 | `get_filled_orders` | `/rest/order/filleds` | `orders` | 327 |
| 14 | `get_all_orders` | `/rest/order/all` | `orders` | 332 |
| 15 | `get_order_by_exec_id` | `/rest/order/byExecId` | `order` | 337 |
| 16 | `get_market_data` | `/rest/marketdata/get` | `marketData` | 360 |
| 17 | `get_trades` | `/rest/data/getTrades` | `trades` | 384 |
| 18 | `get_positions` | `/rest/risk/position/getPositions/{account}` | `positions` | 401 |

**NOT refactor:** `get_detailed_positions` (línea 408) y `get_account_report` (línea 415) — retornan el dict raíz directamente al model (CONTEXT.md L344 nota).

#### 6c. Reemplazar `assert _token is not None` (D-MATZ-12)

**Refactor pattern (línea 157):**

```python
# ANTES:
else:
    _ensure_token()
    assert _token is not None
    resp = _session.request(
        method,
        url,
        params=params,
        headers={"X-Auth-Token": _token},
    )

# DESPUÉS:
else:
    _ensure_token()
    if _token is None:
        raise RuntimeError(
            "matriz_client.client: _ensure_token() did not populate _token"
        )
    resp = _session.request(
        method,
        url,
        params=params,
        headers={"X-Auth-Token": _token},
    )
```

**Critical** (Pitfall RESEARCH L673-678): solo aplica dentro de la rama `else` (no-`auth_basic`). La rama `if auth_basic:` no ejecuta `_ensure_token()` y `_token` puede ser `None` legítimamente.

#### 6d. Docstring expand new_order/replace_order/cancel_order (D-MATZ-17)

```python
# ANTES (líneas 259-263 — new_order):
"""Submit a new single order (§6.3).

Note: The Primary API accepts order submission over HTTP **GET**; this
is a quirk of the upstream API, not a bug in this client.
"""

# DESPUÉS (texto del warning a discreción; debe citar §6.3 y "never refactor"):
"""Submit a new single order (§6.3).

WARNING: Submission uses HTTP GET per Primary API §6.3 spec — this is
intentional, not a bug. Never refactor to POST without explicit API
confirmation; the upstream service silently mismatches POSTs.
"""
```

Idem para `replace_order` (líneas 286) y `cancel_order` (línea 299).

---

### 7. `packages/matriz-client/tests/test_client.py` (APPEND 2 secciones — D-MATZ-34)

**Analog:** `/Users/sebadlf/development/becerra/market-libs/packages/higyrus-client/tests/test_client.py` líneas 145-315 (Phase 4 Verified-live + Regressions)

**Why this analog:** define el shape de las dos secciones que Phase 5 va a appendear: comentario divisor `# ------ <name> ------`, tests pequeños con `httpx_mock.add_response(url=..., method=..., json=...)`, docstring `"""Regression: ... (finding F-NN)."""`.

**Section divider pattern** (copy verbatim from `packages/higyrus-client/tests/test_client.py:145, 250, 317`):

```python
# ------ Verified live (Phase 5) ------


def test_get_segments_url_invariant(httpx_mock: HTTPXMock) -> None:
    """Verified Phase 5: URL exacta + envelope unwrap (finding F-NN si rompe)."""
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        method="GET",
        json={"status": "OK", "segments": [{"marketSegmentId": "DDF", "marketId": "ROFX"}]},
    )
    result = matriz_client.get_segments()
    assert len(result) == 1
    assert result[0].marketSegmentId == "DDF"
```

**Regression pattern for envelope unwrap (D-MATZ-11, copy from `test_client.py:253-264` higyrus):**

```python
# ------ Regressions ------


def test_get_segments_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        method="GET",
        json={"some_other_key": []},  # missing "segments"
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_segments()
    assert "missing envelope key 'segments'" in (exc_info.value.description or "")
```

**18 tests** mirrorean uno por endpoint refactoreado (D-MATZ-10 tabla arriba). Cada test: 1 mock response con `json={"some_other_key": ...}`, 1 `pytest.raises(PrimaryAPIError)`, 1 assert sobre `.description`.

**Sentinel `_token` RuntimeError test (D-MATZ-13)**:

```python
def test_request_raises_runtime_error_if_ensure_token_leaves_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: defensive guard against _ensure_token returning without populating _token (CONCERNS.md L52-55, finding F-NN)."""
    monkeypatch.setattr(_client, "_token", None, raising=False)
    monkeypatch.setattr(_client, "_ensure_token", lambda: None)
    with pytest.raises(RuntimeError, match="did not populate _token"):
        _client._request("GET", "/rest/anything")
```

**Analog from autouse fixture in `conftest.py:14-30`:** los tests heredan `_configure_sync` que precarga `_token="test-token"`. Para este sentinel test, el monkeypatch sobreescribe a `None`. El `_ensure_token` también es monkeypatched para que NO repare (simula el escenario del bug original).

**11 mock-only mutation tests (D-MATZ-14/15/16)**:

**Analog (in-file precedent for mock pattern):** `packages/matriz-client/tests/test_client.py:153-184` (`test_new_order_builds_params` + `test_new_order_omits_optional_fields`).

```python
def test_new_order_baseline_limit_day_with_price(httpx_mock: HTTPXMock) -> None:
    """Mock-only contract: LIMIT/DAY/price set/defaults (MATZ-06)."""
    httpx_mock.add_response(
        url=(
            "https://api.test/rest/order/newSingleOrder"
            "?marketId=ROFX&symbol=X&side=BUY&orderQty=1&ordType=LIMIT"
            "&timeInForce=DAY&account=ACC&cancelPrevious=False&iceberg=False&price=100.0"
        ),
        method="GET",
        json={"status": "OK", "order": {"clientId": "C", "proprietary": "P"}},
    )
    result = matriz_client.new_order("X", "BUY", 1, "ACC", price=100.0)
    assert result.clientId == "C"
    assert result.proprietary == "P"


def test_new_order_uses_GET_method_per_primary_api_quirk(httpx_mock: HTTPXMock) -> None:
    """GET-as-write quirk: Primary API mandates GET for order mutations (§6.3).

    Never refactor to POST without explicit API confirmation — this test
    breaks if anyone changes the method.
    """
    httpx_mock.add_response(
        url=(
            "https://api.test/rest/order/newSingleOrder"
            "?marketId=ROFX&symbol=X&side=BUY&orderQty=1&ordType=LIMIT"
            "&timeInForce=DAY&account=ACC&cancelPrevious=False&iceberg=False&price=100.0"
        ),
        method="GET",
        json={"status": "OK", "order": {"clientId": "C", "proprietary": "P"}},
    )
    matriz_client.new_order("X", "BUY", 1, "ACC", price=100.0)
    [request] = httpx_mock.get_requests()
    assert request.method == "GET", "Primary API §6.3 mandates GET for order submission"
```

**Deviation from analog:** `test_new_order_builds_params` (pre-existing líneas 153-174) usa `request.url.params` para verificar; los Phase 5 tests pueden usar `url=` con string completo (más estricto) **O** `request.url.params` (más permisivo). D-MATZ-14 sugiere "URL exacta verbatim" → el primer enfoque.

---

### 8. `packages/matriz-client/.env.example` (APPEND 5 vars) — D-MATZ-33

**Analog:** `packages/higyrus-client/.env.example` líneas 8-21 (HIGYRUS_SAMPLE_* opt-in pattern)

**Append pattern (texto a agregar al final del archivo actual):**

```
# Optional — used by main_matriz.py driver (Phase 5)
# PRIMARY_ACCOUNT: requerido SOLO para los 6 probes account-scoped (Risk API + order reads).
# Sin esta var, los 6 probes emiten SKIPPED; el resto del driver corre normal (D-MATZ-3).
PRIMARY_ACCOUNT=

# MATRIZ_SAMPLE_SYMBOL: override opcional del símbolo auto-resuelto desde get_all_instruments()[0]
MATRIZ_SAMPLE_SYMBOL=

# MATRIZ_SAMPLE_CL_ORD_ID / MATRIZ_SAMPLE_PROPRIETARY: opt-in para los 2 probes ID-scoped
# (get_order_status, get_order_history). Sin ellos → SKIPPED (D-MATZ-4).
MATRIZ_SAMPLE_CL_ORD_ID=
MATRIZ_SAMPLE_PROPRIETARY=

# MATRIZ_SAMPLE_EXEC_ID: opt-in para get_order_by_exec_id. Sin él → SKIPPED.
MATRIZ_SAMPLE_EXEC_ID=
```

**Deviation:** matriz NO tiene `VERIFY_MATRIZ_BAD_CREDS` (a diferencia de Higyrus `VERIFY_HIGYRUS_BAD_CREDS`); D-MATZ-22 corre los 3 error probes always-on sin opt-in. NO se incluye un override de `MATRIZ_SAMPLE_SEGMENT` (D-MATZ-2 YAGNI).

---

### 9. `.planning/verification/matriz-client-findings.md` (GENERATE)

**Analog:** `.planning/verification/higyrus-client-findings.md` (Phase 4 output)

**Esqueleto** (creado automáticamente por `write_findings("matriz-client")` desde el driver, mirror del higyrus file):

```markdown
# Findings: matriz-client-client

## Run Context (ART)
- Timestamp: <ISO-8601>
- Resolved base URL / env: <url> (remarkets)
- Market hours note: <abierto|cerrado — afecta market data probes>

<!-- Clases (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT -->
<!-- Estados (D-08): OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX). Sin campo de severidad. -->

## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|

## Detalle por hallazgo
```

**Findings agregados durante el run:**
- F-01..F-NN: emitidos por probes (cada uno SHAPE/ERROR-MAP/NO-DATA según D-MATZ-29)
- Último: EXPECTED terminal `prod-vs-remarkets divergence acknowledged` (D-MATZ-27 verbatim CONTEXT.md L590-603)

**Deviation:** doble `-client` en header line 1 (`# Findings: matriz-client-client`) — Pitfall 9 RESEARCH L688-692: aceptar la convención por consistencia con Phase 2-4.

---

### 10. `.planning/verification/{ambito-financiero,iol,higyrus,matriz}-client-findings.md` (APPEND `## Cycle Closure`)

**Analog:** ninguno — D-MATZ-25 introduce sección nueva. El shape lo decide el planner basado en CONTEXT.md L533-542 verbatim.

**Append pattern (escribir AL FINAL de cada uno de los 4 archivos, DESPUÉS de cualquier `append_finding` del run de Phase 5):**

```markdown

## Cycle Closure

**Closed:** <ISO-8601 timestamp del run Phase 5>

### Findings by status

| Status | Count |
|--------|-------|
| OPEN | N |
| CONFIRMED | N |
| FIXED | N |
| EXPECTED | N |
| NO-FIX | N |

### Regression tests linked to FIXED findings

| Finding | Regression path |
|---------|-----------------|
| F-NN | packages/matriz-client/tests/test_client.py::test_X |
| ... | ... |

### Validation

`verify_cycle_closure("<pkg>")` → PASS|FAIL — <detail>
```

**Critical** (Assumption A3 RESEARCH L980): **El append `## Cycle Closure` se hace como ÚLTIMA operación** del Phase 5 driver, después de cualquier `append_finding`. Si en el futuro alguien llama `append_finding` sobre el mismo paquete, la sección `## Cycle Closure` puede ser dropeada por la re-serialización (el parser de `verification.findings._parse_findings` no la conoce).

**Implementation:** `Path(".planning/verification/<pkg>-findings.md").write_text(existing + closure_section)` o similar — escritura directa, NO usar `append_finding`.

---

### 11. `.planning/verification/schemas/matriz-client/*.json` (GENERATE ~11-19 archivos)

**Analog:** `.planning/verification/schemas/higyrus-client/get-health.json` (envelope D-21 baseline)

**Envelope shape verbatim:**

```json
{
  "endpoint": "/rest/segment/all",
  "client_function": "get_segments",
  "captured_at": "2026-06-10T15:32:01.234567+00:00",
  "base_url": "https://api.remarkets.primary.com.ar",
  "sample_params": {},
  "schema": {
    "segments": [
      {"marketSegmentId": "str", "marketId": "str"}
    ],
    "status": "str"
  }
}
```

**Deviation:** ninguna — el helper `_write_or_check_schema` (Pattern Assignment #1) produce este shape exacto via `schema_of(raw_payload)`. D-25 no-overwrite-on-drift se hereda del helper Phase 4.

**Conteo:** entre 11 (sin PRIMARY_ACCOUNT ni MATRIZ_SAMPLE_*) y 19 (todas las opt-ins activas) — Open Question #1 RESEARCH L988-991.

---

### 12. `.planning/verification/CYCLE-REPORT.md` (NEW — D-MATZ-26)

**Analog:** ninguno. D-MATZ-26 introduce el archivo. Shape anclado a CONTEXT.md L546-583 literal.

**Template a producir (escribir al final del driver):**

```markdown
# Cycle Report: market-libs verification cycle (Phases 2-5)

**Closed:** <ISO-8601 timestamp>
**Cycle:** Phases 2-5 (ambito-financiero, iol, higyrus, matriz)
**Cycle mode:** verification-only (no breaking refactors)

## 1. Stats per-package

| Package | Findings Total | OPEN | CONFIRMED | FIXED | EXPECTED | NO-FIX | Regression Tests | Schemas Committed |
|---------|----------------|------|-----------|-------|----------|--------|------------------|-------------------|
| ambito-financiero-client | N | N | N | N | N | N | N | 1 |
| iol-client | N | N | N | N | N | N | N | 4 |
| higyrus-client | N | N | N | N | N | N | N | 5 |
| matriz-client | N | N | N | N | N | N | N | 11-19 |
| **TOTAL** | N | N | N | N | N | N | N | ~21-29 |

## 2. Cross-cycle

- Total findings emitidos: N
- Total regression tests agregados: N
- Total bugs encontrados + fixados (CONFIRMED→FIXED): N

### Patrones recurrentes

- (narrativa, ej: "envelope-key indexing detected as KeyError unmapped en X de 4 paquetes; HIGY/MATZ se fixaron in-cycle")
- (False-pass SafeModel: HIGY `Posicion.disponibleAjustado`, MATZ <if any>)
- (...)

## 3. Open questions for downstream milestone

- **prod-vs-remarkets gap** (matriz-client F-NN EXPECTED): verification limitada a remarkets sandbox por safety policy; recordado para milestone futuro "verify matriz against prod with appropriate safety harness"
- (deferred items, ej: iteración multi-cuenta HIGY, refresh_token persistente IOL, etc.)

## 4. Schemas summary

```
ambito-financiero-client (1):
  .planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json
iol-client (4):
  .planning/verification/schemas/iol-client/get-quote.json
  ...
higyrus-client (5):
  .planning/verification/schemas/higyrus-client/get-health.json
  ...
matriz-client (N):
  .planning/verification/schemas/matriz-client/get-segments.json
  ...
```
```

**Deviation:** archivo nuevo de generación discrecional (formato literal de CONTEXT.md L546-583); el planner puede agregar/eliminar columnas mientras respete las 4 dimensiones.

---

## Shared Patterns

### Cascade SKIPPED tras login failure (D-MATZ-31)

**Source:** `main_higyrus.py:165-169` + `main_higyrus.py:591-595` (probe checking `_auth_failed`)

**Apply to:** Todos los probes en `main_matriz.py` después de `probe_login_sync`.

```python
# Module-level (líneas iniciales):
_auth_failed: bool = False
_auth_failure_reason: str = ""

# Dentro de cada probe (primer check):
if _auth_failed:
    return ProbeResult("<name>", "SKIPPED", f"auth failed: {_auth_failure_reason}")

# Dentro de probe_login_sync (set en falla):
global _auth_failed, _auth_failure_reason
_auth_failed = True
_auth_failure_reason = f"sync login: {type(exc).__name__}: {exc}"
```

### Stdout discipline + `safe_print` con secrets dinámicos (D-MATZ-32)

**Source:** `main_higyrus.py:2266-2278, 2285-2289, 2365` + `verification/redaction.py:43`

**Apply to:** Toda salida de `main_matriz.py` que pueda incluir credenciales o token.

```python
secrets: list[str] = []
_password_env = os.getenv("PRIMARY_PASSWORD", "")
if _password_env:
    secrets.append(_password_env)
_user_env = os.getenv("PRIMARY_USER", "")
if _user_env and len(_user_env) >= 4:
    secrets.append(_user_env)
# Después del login:
token = getattr(primary.client, "_token", None)
if token:
    secrets.append(token)
# En cada print:
safe_print(f"PROBE {r.name}: {r.status} {r.detail}".rstrip(), secrets=secrets)
```

### Hostname assert remarkets (D-MATZ-33)

**Source:** sin analog directo (Phase 5 introduce); shape inspirado en `verification.mutation_gate` interno

**Apply to:** start of `main()` en `main_matriz.py`, antes de `write_findings`.

```python
base = primary.client._base_url
if "remarkets" not in base:
    print(
        f"ABORT: PRIMARY_BASE_URL={base!r} is not a remarkets sandbox URL — "
        "Phase 5 verification is remarkets-only by safety policy",
        file=sys.stderr,
    )
    sys.exit(1)
```

**Critical** (D-MATZ-33): usar `if/raise` o `if/sys.exit(1)`, NUNCA `assert "remarkets" in base` — consistente con D-MATZ-12 (assert se strippea con `python -O`).

### `_next_fid()` deterministic F-NN counter

**Source:** `main_higyrus.py:179-183`

**Apply to:** `main_matriz.py` para cada `append_finding(fid=_next_fid(), ...)`.

```python
_fid_counter: int = 0


def _next_fid() -> str:
    """Devuelve el siguiente ``F-NN`` (NN zero-padded a 2 dígitos)."""
    global _fid_counter
    _fid_counter += 1
    return f"F-{_fid_counter:02d}"
```

### Idempotent `write_findings(pkg)` upfront

**Source:** `main_higyrus.py:2256` + `verification/findings.py:122` (`write_findings`)

**Apply to:** `main_matriz.py` luego del hostname assert, antes del primer probe.

```python
write_findings(_PKG)  # no-op si el archivo ya existe (D-03 mirror)
```

### `append_finding` con signature completa

**Source:** `verification/findings.py:403-417`

**Apply to:** Cada emisión de finding en `main_matriz.py`.

```python
append_finding(
    pkg=_PKG,             # str slug validado por _PKG_SLUG_RE
    fid=fid,              # F-NN
    class_=class_,        # uno de FINDING_CLASSES (SHAPE/AUTH/ERROR-MAP/PARAM/SYNC-ASYNC-DRIFT/NO-DATA/ANTI-BOT)
    surface=surface,      # "sync" / "async" / "both" — matriz siempre "sync"
    status=status,        # uno de STATUS_LIFECYCLE (OPEN/CONFIRMED/FIXED/EXPECTED/NO-FIX)
    title=title,          # single-line (CR-02 invariant)
    expected=expected,    # string
    actual=actual,        # string
    diff=diff,            # string
    base_url=base_url,    # opcional, refresca ART block
)
```

---

## No Analog Found

Files with no close match in the codebase (planner uses CONTEXT.md/RESEARCH.md verbatim como fuente):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `verification/cycle_report.py` | utility (parse + filesystem assert) | transform | No existing helper hace markdown parsing + filesystem assert; el planner inventa el shape anclado a `findings.py:212-345` parser pattern y a CONTEXT.md L610-642 literal |
| `.planning/verification/{pkg}-findings.md` (`## Cycle Closure` sección) | text append a 4 archivos | append-only | Sección nueva D-MATZ-25; shape inventado por el planner conforme CONTEXT.md L533-542 |
| `.planning/verification/CYCLE-REPORT.md` | consolidated report | n/a | Nuevo archivo D-MATZ-26; shape inventado por el planner conforme CONTEXT.md L546-583 literal |

---

## Metadata

**Analog search scope:**
- `/Users/sebadlf/development/becerra/market-libs/main_higyrus.py` (Phase 4 driver, 2380 líneas — análogo primario)
- `/Users/sebadlf/development/becerra/market-libs/main_matriz.py` (current smoke driver — análogo de partida)
- `/Users/sebadlf/development/becerra/market-libs/packages/matriz-client/src/matriz_client/{client,exceptions,models}.py` (target del fix MATZ-04 + assert)
- `/Users/sebadlf/development/becerra/market-libs/packages/higyrus-client/src/higyrus_client/client.py` (HIGY-04 fix pattern paralelo MATZ-04)
- `/Users/sebadlf/development/becerra/market-libs/packages/{higyrus,matriz}-client/tests/test_client.py` (test patterns: 2 secciones + regression docstring)
- `/Users/sebadlf/development/becerra/market-libs/verification/{__init__,findings,schema,redaction,env_gate}.py` (existing helpers)
- `/Users/sebadlf/development/becerra/market-libs/.planning/verification/higyrus-client-findings.md` (findings file format)
- `/Users/sebadlf/development/becerra/market-libs/.planning/verification/schemas/higyrus-client/get-health.json` (envelope D-21 baseline)
- `/Users/sebadlf/development/becerra/market-libs/.planning/phases/04-higyrus-verification/04-PATTERNS.md` (Phase 4 patterns format mirror)
- `/Users/sebadlf/development/becerra/market-libs/packages/{higyrus,matriz}-client/.env.example` (env template format)
- `/Users/sebadlf/development/becerra/market-libs/packages/matriz-client/tests/conftest.py` (autouse fixture pattern para los Phase 5 tests)

**Files scanned:** ~25 (drivers, clients, tests, helpers, findings/schemas committeados)

**Pattern extraction date:** 2026-06-09

---

*Phase: 05-matriz-verification*
*Pattern mapping completed: 2026-06-09*
