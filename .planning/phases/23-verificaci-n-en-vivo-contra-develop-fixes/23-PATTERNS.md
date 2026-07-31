# Phase 23: Verificación en vivo contra develop + fixes - Pattern Map

**Mapped:** 2026-07-30
**Files analyzed:** 8 (2 new drivers/guards, 1 modified runner, 2 modified source, 2 new test groups, 1 new findings/schema artifact)
**Analogs found:** 7 / 8 (1 additive-only, no analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `main_market_data.py` (NEW) | driver / entry-point | request-response (live probes) | `main_ambito_financiero.py` | role-match (auth + more endpoints) |
| `verification/test_main_market_data_uses_single_client_instance.py` (NEW) | test (AST guard) | transform (static analysis) | `verification/test_main_ambito_financiero_uses_single_client_instance.py` | exact (mechanical port) |
| `main_verify.py` (MODIFY) | config / aggregate runner | batch | `main_verify.py:28-34` (`_DRIVERS`) | self (one-line append) |
| `packages/market-data-client/src/market_data_client/models.py` (MODIFY) | model | transform (deserialize) | itself (in-place field reconcile) | self / additive |
| `packages/market-data-client/src/market_data_client/_core.py` (MODIFY) | service (pure parsers) | transform (parse + stamp) | itself (`parse_*_response` @516-609) | self / additive |
| `packages/market-data-client/tests/test_*.py` (NEW regressions) | test | request-response (mocked) | `tests/test_reference_client.py`, `tests/test_market_data.py` | exact |
| `.planning/verification/market-data-client-findings.md` (NEW, bootstrap) | artifact (generated) | file-I/O | `write_findings()` output (no hand-authoring) | n/a (tool-generated) |
| `.planning/verification/schemas/market-data-client/*.json` (NEW) | artifact (generated) | file-I/O | ambito schema snapshot envelope | role-match |

---

## Pattern Assignments

### `main_market_data.py` (driver, request-response)

**Analog:** `main_ambito_financiero.py` (smallest 4/4 driver template).

**KEY DIVERGENCE from analog:** ambito is auth-less and single-endpoint; market-data has
Auth0 client-credentials + 10 endpoints × 2 surfaces. The analog gives the *skeleton*
(ProbeResult, `_next_fid`, per-probe isolation, ONE `Client()`+`AsyncClient()`, findings
bootstrap, schema snapshot, summary). The endpoint/auth/env-gate specifics come from the
market-data source (`client.py` / `aio.py`) and the harness modules below.

**Module header + imports pattern** (`main_ambito_financiero.py:38-56`):
```python
from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path

import httpx
from verification import safe_print, schema_of, write_findings
from verification.findings import append_finding

import ambito_financiero_client as ambito
from ambito_financiero_client import AsyncClient, Client
```
For market-data, swap the package imports to:
```python
from verification.env_gate import require_env          # D-01 gate (ambito omits this — no auth)
import market_data_client as md
from market_data_client import AsyncClient, Client
from market_data_client import (
    CalendarConfig, CalendarDay, Instrument, LatestRequest,
    MarketDataSnapshot, Segment, Symbol,
)
```

**`_next_fid` counter + `ProbeResult`** (`main_ambito_financiero.py:74-97`) — copy verbatim:
```python
_fid_counter: int = 0

def _next_fid() -> str:
    global _fid_counter
    _fid_counter += 1
    return f"F-{_fid_counter:02d}"

@dataclass(frozen=True, slots=True)
class ProbeResult:
    name: str
    status: str  # "PASS" | "FAIL" | "SKIPPED" | "FINDING"
    detail: str
```

**Env-gate + early-exit (D-01)** — NOT in ambito (auth-less); pattern from `env_gate.require_env`
(`verification/env_gate.py:32-41`). Place at the TOP of `main()`:
```python
if not require_env(
    "market-data-client",
    ["MARKET_DATA_CLIENT_ID", "MARKET_DATA_CLIENT_SECRET",
     "MARKET_DATA_AUDIENCE", "MARKET_DATA_AUTH0_TOKEN_URL"],
):
    sys.exit(0)   # verbatim "SKIPPED market-data-client: missing ..." already printed by require_env
```
The exact env-var names come from `client.py:25-30` — `MARKET_DATA_CLIENT_ID` /
`MARKET_DATA_CLIENT_SECRET` / `MARKET_DATA_AUDIENCE` / `MARKET_DATA_AUTH0_TOKEN_URL`
(NOT the `..._AUTH0_CLIENT_ID` spellings the source plan implies — D-01/Specifics).
`MARKET_DATA_BASE_URL` is optional (defaults at `client.py:29-30`), so it is NOT gated.

**Per-probe exception isolation + finding emit** (`main_ambito_financiero.py:146-218`) — the
canonical structure to copy per probe: try the call, branch on package-specific exceptions,
emit `append_finding(...)` with the correct class, return a `ProbeResult`. Adapt the
exception ladder to market-data's hierarchy (`from market_data_client import
MarketDataAuthError, MarketDataAPIError, MarketDataRateLimitError, MarketDataError`):
```python
try:
    result = client.get_market_data(active=True)
    ...
except md.MarketDataAuthError as exc:
    fid = _next_fid()
    append_finding(_PKG, fid=fid, class_="AUTH", surface="sync", status="OPEN", ...)
    return ProbeResult("market_data_sync", "FINDING", f"{fid} (OPEN)")
except httpx.ConnectError as exc:          # D-09: network-unreachable develop → NO-DATA, never crash
    fid = _next_fid()
    append_finding(_PKG, fid=fid, class_="NO-DATA", surface="sync", status="OPEN", ...)
    return ProbeResult("market_data_sync", "SKIPPED", "develop unreachable")
except Exception as exc:
    fid = _next_fid()
    append_finding(_PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN", ...)
    return ProbeResult("market_data_sync", "FINDING", f"{fid} (OPEN)")
```
**D-09 is load-bearing:** an uncaught `httpx.ConnectError`/`ConnectTimeout` would flip the
aggregate runner to FAILED (`main_verify.py:78`). Every probe MUST catch broad `Exception`.

**SHAPE diffing per SafeModel (D-04)** — use the harness diff on the raw payload BEFORE it is
coerced by `from_api`. Signature from `verification/safemodel_diff.py:94-98`:
```python
from verification.safemodel_diff import diff_safemodel_bidirectional
# yields (path, direction, key); direction ∈ {"model-only", "wire-only"}
for path_, direction, key in diff_safemodel_bidirectional(raw_item, MarketDataSnapshot):
    fid = _next_fid()
    append_finding(_PKG, fid=fid, class_="SHAPE", surface="both", status="OPEN",
                   title=f"{direction} field {key} on MarketDataSnapshot{path_}", ...)
```
`model-only` = FALSE-PASS risk (model declares, wire omits → `from_api` silently defaults);
`wire-only` = info (server added a field). Apply to all 7 models: `MarketDataSnapshot`,
`MarketDataEntry`, `Instrument`, `Segment`, `Symbol`, `CalendarDay`, `CalendarConfig`.
NOTE: to inspect raw payloads, call `client._request(spec)` + `.json()` (as ambito does at
`main_ambito_financiero.py:152-154`) rather than the parsing wrapper, since `from_api`
already flattens divergence away.

**Async wrapper — ONE `asyncio.run` + isolated teardown** (`main_ambito_financiero.py:681-700`):
```python
async def _async_main(...) -> ...:
    aclient = AsyncClient()
    try:
        ... await probe_* (aclient) ...
    finally:
        with contextlib.suppress(Exception):   # IN-03: teardown never crashes the driver
            await aclient.aclose()
```

**main() orchestration + ONE sync `Client()`** (`main_ambito_financiero.py:708-759`):
```python
def main() -> None:
    write_findings(_PKG)               # D-08.3 idempotent bootstrap
    client = Client()                  # exactly ONE sync Client (success-criterion 1)
    results: list[ProbeResult] = []
    try:
        ... probe_* (client) ...
        result_async = asyncio.run(_async_main(...))   # exactly ONE AsyncClient inside
    finally:
        with contextlib.suppress(Exception):
            client.close()
    for r in results:
        safe_print(f"PROBE {r.name}: {r.status} {r.detail}".rstrip(), secrets=[])
    # SUMMARY line (verbatim format at :756-759)
```
**Single-Client invariant (success-criterion 1 / D-02):** exactly ONE `Client()` in `main()`
and ONE `AsyncClient()` in `_async_main()`, threaded as params into every probe. This is
enforced by the AST guard below.

**Schema snapshot (DRIFT-01, D-08.4)** (`main_ambito_financiero.py:501-558`) — write-once,
never-overwrite envelope using `schema_of` (`verification/schema.py:27`):
```python
_SCHEMA_DIR = _REPO_ROOT / ".planning" / "verification" / "schemas" / _PKG
actual_schema = schema_of(raw_payload)         # keys+types only, PII-free by construction
envelope = {"endpoint": ..., "client_function": ..., "captured_at": ...,
            "base_url": ..., "schema": actual_schema}
if not _SCHEMA_FILE.exists():
    _SCHEMA_FILE.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n")
elif committed.get("schema") != actual_schema:
    append_finding(_PKG, class_="SHAPE", ...)   # D-25: NEVER overwrite baseline
```

**Redacted output** — every stdout line goes through `safe_print(..., secrets=[...])`
(`verification/redaction.py:43`). It masks `Bearer <token>` reflections structurally
(regex, `redaction.py:31,60`) even if the token is not in the `secrets` list. Never print
a raw response dict or a token.

---

### `verification/test_main_market_data_uses_single_client_instance.py` (test, AST guard)

**Analog:** `verification/test_main_ambito_financiero_uses_single_client_instance.py` — mechanical port.

**The ONLY change is the driver constant** (`...:27-28`):
```python
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_market_data.py"          # was "main_ambito_financiero.py"
```
The walker body (`...:37-57`) copies verbatim — it counts `ast.Call` sites whose func is a
`Name`/`Attribute` in `_CTOR_NAMES = frozenset({"Client", "AsyncClient"})` and asserts
`1 <= count <= 2`. The `_CTOR_NAMES` set already matches market-data's class names, so no
constructor-name change is needed. Rename the test function to
`test_main_market_data_uses_single_client_instance`.

---

### `main_verify.py` (config, batch) — one-line append (D-08.2)

**Analog:** the existing `_DRIVERS` list (`main_verify.py:28-34`). Append the market-data tuple:
```python
_DRIVERS: list[tuple[str, str]] = [
    ("iol-client", "main_iol.py"),
    ("higyrus-client", "main_higyrus.py"),
    ("matriz-client", "main_matriz.py"),
    ("ambito-financiero-client", "main_ambito_financiero.py"),
    ("wallets-client", "main_wallets.py"),
    ("market-data-client", "main_market_data.py"),   # NEW
]
```
**Contract to preserve:** the driver's SKIPPED line MUST match `_ENV_SKIP =
re.compile(r"^SKIPPED \S.*:")` (`main_verify.py:41`). `require_env` prints
`SKIPPED market-data-client: missing ...` (colon present) → classified SKIPPED, not FAILED.
This is why D-01 forbids a `--live` flag (would break flag-less subprocess invocation at
`main_verify.py:61` and the SKIPPED classification).

---

### `packages/market-data-client/src/market_data_client/models.py` (model, transform) — in-cycle fixes

**Analog:** the file itself — fields are explicitly PROVISIONAL (`models.py:19-23`) and expected
to change once live develop payloads land. Fixes are field-name/type reconciliations on the 7
SafeModels (`models.py:118-275`).

**Constraints when editing:**
- Wire field names are **camelCase verbatim** (`marketId`, `marketSegmentId`, `instrumentType`,
  `isBusinessDay`, `businessDays`) — this module is `N815`-exempt (`models.py:22-23`).
- `received_at` is CLIENT-STAMPED and injected via the `MarketDataSnapshot.from_api` override
  (`models.py:146-164`), NOT coerced. If live payloads reveal a server event-time, add it as an
  **additive** `Optional` field (Phase-21 D-02 / deferred) — do not repurpose `received_at`.
- Reference models (`Instrument`, `Segment`, `Symbol`, `CalendarDay`, `CalendarConfig`) use the
  INHERITED `from_api` and carry NO `received_at` (D-05). Keep it that way unless live payloads
  prove otherwise (additive-only).
- New nullable fields default to `None` (`| None`), coerced fields fall back to typed zeros
  (`_coerce`, `models.py:74-115`).

**Mirroring:** models are single-source (no sync/async fork), so a model edit is inherently
mirrored. The sync/async duplication lives in the CALL SITES (see `_core.py` below).

---

### `packages/market-data-client/src/market_data_client/_core.py` (service, transform) — parser fixes

**Analog:** the two market-data parsers (`_core.py:516-555`) and the four reference parsers
(`_core.py:570-609`). All follow the SAME body-consume-then-raise contract.

**Market-data parser pattern with `received_at` stamp** (`_core.py:516-534`):
```python
def parse_market_data_response(resp: httpx.Response) -> list[MarketDataSnapshot]:
    resp.read()
    received_at = time.time()          # ONE stamp per response (D-01), line 527
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    return [MarketDataSnapshot.from_api(item, received_at=received_at) for item in raw]
```
`parse_latest_response` is identical (stamp at `_core.py:548`). Reference parsers
(`parse_instruments_response` etc.) are the same MINUS the `received_at` line and pass no
`received_at` kwarg. Preserve the `resp.read()` → `time.time()` → `raise_for_response` ordering
and the `[]` collection guard for `null`/empty bodies when applying any fix.

**Mirroring rule (D-06):** `_core.py` is shared by BOTH `client.py` and `aio.py` (the pure
parse/build layer is single-source — see `client.py:388-401` vs `aio.py:402-415` both calling
`_core.parse_market_data_response`). A parser fix therefore auto-mirrors. BUT any logic that
lives in the shell (`client.py` `_request` @289-346 vs `aio.py` `_request`) must be hand-mirrored;
an unmirrored shell change opens a `SYNC-ASYNC-DRIFT` finding by policy.

---

### `packages/market-data-client/tests/test_*.py` (test, mocked regressions) — D-07

**Two analog patterns depending on layer:**

1. **Shell-level (Bearer + param-encoding) via `httpx_mock`** — analog
   `tests/test_reference_client.py:20-53`:
   ```python
   from pytest_httpx import HTTPXMock
   import market_data_client

   def test_get_instruments_sends_bearer_and_encodes_params(httpx_mock: HTTPXMock) -> None:
       httpx_mock.add_response(method="GET", json=[{...}])
       result = market_data_client.client._get_default().get_instruments(
           include_expired=True, only_outright=False, offset=0, subscribed=None)
       req = httpx_mock.get_requests()[0]
       assert req.headers["Authorization"] == "Bearer test-token"
       assert req.url.params.get("include_expired") == "true"     # httpx-native bool (PARAM finding target)
       assert req.url.params.get("only_outright") == "false"
       assert req.url.params.get("offset") == "0"                 # falsy PRESERVED (D-03)
       assert "subscribed" not in req.url.params                  # None dropped
   ```
   The async mirror analog is `tests/test_reference_async_client.py` (same shape via
   `aio._get_default()`). Every fixed PARAM/AUTH finding links a test like this.

2. **Pure `_core` builder/parser** — analog `tests/test_market_data.py:39-190`:
   ```python
   _DUMMY_REQUEST = httpx.Request("GET", "http://t")
   def _resp(status_code, *, json_body=None) -> httpx.Response:
       return httpx.Response(status_code, json=json_body, request=_DUMMY_REQUEST)
   # assert received_at is stamped once, null body → [], 401 → MarketDataAuthError
   ```

**conftest seeding (`tests/conftest.py:29-72`):** autouse fixtures seed a non-expiring token
(`NEVER_EXPIRES = 9_999_999_999.0`) and a dummy base_url so no real auth grant fires and
`httpx_mock` can intercept. Sync AND async both seeded. New regression tests inherit this
automatically — do NOT re-seed.

**Cycle-closure link (D-07):** each CONFIRMED/FIXED finding must carry
`regression="packages/market-data-client/tests/test_x.py::test_name"` so
`verify_cycle_closure("market-data-client")` returns PASS. The link is validated STRUCTURALLY
(`cycle_report.py:123-176`): path must be repo-relative (no `..`, not absolute), file must
exist, and the file text must contain `def <test_name>(`.

---

### `.planning/verification/market-data-client-findings.md` + schema snapshots (artifacts, file-I/O)

**No analog to hand-author.** Bootstrap the findings file via `write_findings("market-data-client")`
(`findings.py:137-147`, idempotent — no-op if it exists) inside `main()`. All content is
tool-generated by `append_finding`; the file has an operator-owned zone above
`<!-- BEGIN AUTO-GENERATED -->` and below `<!-- END AUTO-GENERATED -->` that survives re-runs
(`findings.py:92-93,246-260`). Schema snapshots land under
`.planning/verification/schemas/market-data-client/` as the `schema_of`-envelope JSON
(see driver schema-snapshot pattern above).

---

## Shared Patterns

### Env-Gate (Auth0 credentials)
**Source:** `verification/env_gate.require_env` (`verification/env_gate.py:32-41`)
**Apply to:** `main_market_data.py` `main()` only.
```python
def require_env(pkg: str, names: list[str]) -> bool:
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        print(f"SKIPPED {pkg}: missing {', '.join(missing)}")   # colon → runner SKIPPED classification
        return False
    return True
```
Returns `False` without exiting; the DRIVER decides `sys.exit(0)` (clean skip for the batch).

### Findings Emit (7 closed classes, idempotent by fid)
**Source:** `verification/findings.append_finding` (`findings.py:517-640`; classes `findings.py:76-84`)
**Apply to:** every probe in `main_market_data.py`.
- Valid `class_` (closed tuple; unknown → `ValueError`): `SHAPE, AUTH, ERROR-MAP, PARAM,
  SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT`.
- Valid `status` lifecycle: `OPEN → CONFIRMED → FIXED` (+ terminal `EXPECTED`/`NO-FIX`).
- Idempotent by `fid`: human-promoted statuses (non-OPEN) are NEVER overwritten by re-runs
  (`findings.py:610-612`). `idempotent_by_title=True` dedupes terminal EXPECTED cross-run.
- `title` must be single-line (`\n`/`\r` → `ValueError`, `findings.py:573-574`).
- Class mapping (D-05): `received_at`/staleness + event-time gaps → **SHAPE**; mis-encoded
  bool/param filters → **PARAM**; token/401 anomalies → **AUTH**. No new class invented.
- Required kwargs: `fid, class_, surface, status, title, expected, actual, diff`
  (+ optional `regression, base_url, market_hours, idempotent_by_title`).

### SafeModel bidirectional diff (SHAPE detection)
**Source:** `verification/safemodel_diff.diff_safemodel_bidirectional` (`safemodel_diff.py:94-160`)
**Apply to:** every probe that receives a raw model payload (all 7 SafeModels).
Duck-typed (cross-package-safe), recurses nested SafeModels + `list[SafeModel]` (samples first
element). `model-only` = FALSE-PASS risk (surface as SHAPE); `wire-only` = info. Optional
fields are NOT flagged model-only (intended nullability, `safemodel_diff.py:135`).

### Schema snapshot (DRIFT-01, PII-free)
**Source:** `verification/schema.schema_of` (`schema.py:27-40`)
**Apply to:** schema-snapshot probe(s). Reduces payload to keys+type-names, never values →
directly committable. Write-once, never-overwrite; drift → SHAPE finding (D-25).

### Cycle-closure gate (regression linkage)
**Source:** `verification/cycle_report.verify_cycle_closure` (`cycle_report.py:123-176`)
**Apply to:** the phase exit gate. `verify_cycle_closure("market-data-client") → (ok, missing_fids)`.
Structural check only (no pytest import). PASS is criterion 4. Populate the `regression` field
as `packages/market-data-client/tests/<file>.py::<test_name>` on FIXED/CONFIRMED findings.

### Redacted stdout
**Source:** `verification/redaction.safe_print` / `redact` (`redaction.py:34-61`)
**Apply to:** every print in `main_market_data.py`. Masks known secrets (≥4 chars) AND any
`Bearer <token>` reflection via regex (`redaction.py:31`). Use `secrets=[]` for uniform lines
(the Bearer regex still fires). Never print a token as name+value.

### Single-Client invariant (AST-enforced)
**Source:** REFAC-05 guard pattern (`test_main_ambito_financiero_uses_single_client_instance.py`)
**Apply to:** `main_market_data.py` construction — exactly ONE `Client()` (in `main()`) + ONE
`AsyncClient()` (in `_async_main()`), threaded into probes. `1 <= ctor_count <= 2` or the new
AST guard fails RED.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.planning/verification/market-data-client-findings.md` | artifact | file-I/O | Not hand-authored; generated verbatim by `write_findings`/`append_finding`. Only the operator-zone (above BEGIN / below END markers) is human-editable, and even that is bootstrapped empty. |

(Note: `models.py` / `_core.py` fixes have "self" as analog — they reconcile PROVISIONAL shapes
in place against live payloads; the existing parser/model bodies ARE the pattern to preserve.)

---

## Metadata

**Analog search scope:** repo root drivers (`main_*.py`), `verification/` harness modules,
`packages/market-data-client/src/market_data_client/` (client, aio, models, _core, __init__),
`packages/market-data-client/tests/`.
**Files scanned:** 13 (2 root drivers, 6 verification modules, 5 market-data source/test files;
plus tests directory listing).
**Pattern extraction date:** 2026-07-30
</content>
</invoke>
