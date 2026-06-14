# Phase 11: Harness Hardening + Code Review Close-out + Live Re-verification — Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 16 (1 extended, 6 modified drivers/configs, 6 new regression tests, 2 verification doc updates, 1 LIVE-01 evidence section)
**Analogs found:** 16 / 16 (100% — Phase 11 reuses internal patterns by design; no greenfield)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `verification/findings.py` (EXTEND `_parse_findings` + `_serialize_findings` + add `idempotent_by_title` kwarg to `append_finding`) | utility (markdown serializer + idempotent merge) | file-I/O (read → parse → merge → atomic write) | self (lines 156-342 `_parse_findings`/`_serialize_findings` + 403-494 `append_finding`) | exact (in-place extension per D-HARN-01) |
| `main_matriz.py` (CR-01 lines 1297-1321 + CR-02 line 411/428 + CR-04 lines 182-189 + CR-06 ≥10 `except Exception` sites + HARN-10 dedupe lines 2093-2114) | driver smoke (verification probe orchestrator) | request-response (live HTTP) + file-I/O (findings.md append) | self (Phase 7 CR-05 refactor `_envelope_probe` at lines 263-380; Phase 8 retries hookup) | exact (in-driver surgical fixes) |
| `main_higyrus.py` (CR-06 ≥10 `except Exception` sites + CR-07 lines 228-328 event_hooks lock + CR-08 line-length sites) | driver smoke (verification probe orchestrator) | request-response (live HTTP) + thread-shared `httpx.Client.event_hooks` | self (lines 228-328 `_capture_sync_query_string`/`_capture_async_query_string`) | exact |
| `main_iol.py` (HARN-08 dedupe in append_finding call-sites if needed) | driver smoke (verification probe orchestrator) | request-response (live HTTP) + file-I/O | self (`main_iol.py:75` import + ~20 append_finding sites) | exact (same harness contract) |
| `main_ambito_financiero.py` (HARN-08 dedupe in append_finding call-sites if needed) | driver smoke (verification probe orchestrator) | request-response (live HTTP) + file-I/O | self (`main_ambito_financiero.py:50` import + ~6 append_finding sites) | exact (same harness contract) |
| `verification/test_findings_append_only.py` (NEW — HARN-07/09 regression) | regression test (cross-cutting harness) | file-I/O (temp findings files + N re-runs) | `verification/test_logging_root_unchanged.py:1-40` + `verification/test_max_retries_validation.py:1-50` | role-match (cross-cutting verification test idiom) |
| `verification/test_findings_dedupe_by_title.py` (NEW — HARN-08/10 regression) | regression test (idempotency contract) | file-I/O (N append_finding calls with same title) | `verification/test_retry_mutation_gate.py:1-40` (parametric × packages) | role-match (parametric cross-pkg invariant test) |
| `packages/higyrus-client/tests/test_event_hooks_thread_safety.py` (NEW — CR-07 RED→GREEN) | regression test (concurrency, RED first) | event-driven (concurrent `event_hooks` mutation under threading) | `verification/test_async_cancellation.py:1-100` (async concurrency idiom) + Phase 9 `test_multi_account.py` (mocked-HTTP idiom) | role-match (thread-safety RED→GREEN per D-21 / Phase 8 D-21) |
| `verification/test_main_drivers_bare_except.py` (NEW — CR-06 RED→GREEN cross-pkg lint check) | regression test (static-analysis style guard) | transform (AST walk over `main_*.py`) | `verification/test_logging_root_unchanged.py:1-40` (cross-pkg invariant check via import) | role-match (style-guard via AST/grep) |
| `main_matriz.py` regression `verification/test_main_matriz_first_dict.py` (NEW — CR-04 mocked) | regression test (driver unit) | pure-function (`_first_dict` distinguishability) | `verification/test_matriz_sweep_snapshot.py:1-60` (mocked-driver-probe idiom via `pytest-httpx`) | exact (same idiom, same import shape) |
| `verification/test_main_matriz_login_fail_uniformity.py` (NEW — CR-02 mocked) | regression test (driver unit) | pure-function (`ProbeResult.status` string normalization) | `verification/test_matriz_sweep_snapshot.py:1-60` | exact (same idiom) |
| `verification/test_main_matriz_schema_snapshot_alignment.py` (NEW — CR-01 mocked) | regression test (driver unit) | pure-function (path/sample_params symmetry) | `verification/test_matriz_sweep_snapshot.py:1-60` | exact (same idiom) |
| `pyproject.toml` (housekeeping — `[tool.ruff] extend-exclude` for spike sources per D-WAVE-01 §integration) | config | n/a (static config) | self (existing `[tool.ruff]` block; Phase 8 D-21 housekeeping deferred-items.md call-out) | exact (1-line `extend-exclude` add per specifics §spike) |
| `.planning/verification/CYCLE-REPORT.md` (UPDATE Q#6 with HARN deferred resolutions) | doc (cycle log) | n/a (manual edit) | `.planning/verification/CYCLE-REPORT.md` self + Phase 9 09-VERIFICATION.md Q#6 update idiom | exact (self-update) |
| `.planning/verification/{ambito,iol,higyrus,matriz}-findings.md` (MIGRATION — inject BEGIN/END markers preserving current content per D-HARN-01) | doc (findings file migration) | file-I/O (in-place marker injection) | `.planning/verification/matriz-client-findings.md` (baseline at commit `4d48e07`) | exact (one-time migration; non-destructive) |
| `.planning/phases/11-.../11-VALIDATION.md` LIVE-01 evidence section (NEW) | doc (live-run evidence + acceptance bar gates) | n/a (markdown) | `.planning/phases/10-.../10-VALIDATION.md` (live probe evidence layout per Phase 10 LIVE-02) | role-match (VALIDATION.md live-evidence idiom) |

---

## Pattern Assignments

### `verification/findings.py` (EXTEND — utility, file-I/O)

**Analog:** self (in-place extension per D-HARN-01 — full rewrite NO necesario).

**Imports pattern** (lines 37-42, unchanged — Phase 11 adds NO new imports):

```python
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path
```

**BEGIN/END marker contract** (NEW — extends `new_findings()` template at lines 100-119):

The existing `new_findings()` already emits the HTML-comment idiom for D-09/D-08 metadata:

```python
# Existing pattern (lines 113-114):
f"<!-- Clases (D-09): {classes} -->\n"
f"<!-- Estados (D-08): {lifecycle}. Sin campo de severidad. -->\n"
```

Phase 11 ADDS two new HTML-comment markers around the `## Index` + `## Detalle por hallazgo` blocks:

```markdown
<!-- BEGIN AUTO-GENERATED -->
## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|
| F-01 | ... |
## Detalle por hallazgo
### F-01 -- ...
<!-- END AUTO-GENERATED -->
```

**Migration path** (one-time, per `<canonical_refs>`): a separate task injects markers into the 4 existing `<pkg>-findings.md` files committed at `4d48e07`, preserving operator narrative ABOVE the `## Index` block and BELOW the last finding section.

**`_parse_findings` extension pattern** (extends lines 212-342):

The existing parser already does a line-scan state machine tracking `in_art` / `in_index` / `current_fid`. Phase 11 adds:

```python
# After existing state vars (around line 240):
in_auto_zone = False
operator_prefix: list[str] = []   # lines BEFORE <!-- BEGIN AUTO-GENERATED -->
operator_suffix: list[str] = []   # lines AFTER <!-- END AUTO-GENERATED -->

for raw_line in lines:
    line = raw_line.rstrip("\r")
    if line == "<!-- BEGIN AUTO-GENERATED -->":
        in_auto_zone = True
        continue
    if line == "<!-- END AUTO-GENERATED -->":
        in_auto_zone = False
        continue
    if not in_auto_zone and not_yet_seen_begin:
        operator_prefix.append(raw_line)
        continue
    if not in_auto_zone and seen_end:
        operator_suffix.append(raw_line)
        continue
    # (existing scan logic — Index/Detalle parsing — only runs when in_auto_zone is True)
```

Return shape extends `_ParsedFile` (line 156) with two new fields:

```python
@dataclass(slots=True)
class _ParsedFile:
    findings: list[_Finding] = field(default_factory=list)
    art: dict[str, str] = field(default_factory=dict)
    operator_prefix: list[str] = field(default_factory=list)   # NEW
    operator_suffix: list[str] = field(default_factory=list)   # NEW
```

**`_serialize_findings` extension pattern** (extends lines 345-400):

Today the serializer emits the whole file from scratch. Phase 11 wraps the Index + Detalle blocks with the markers and prepends `operator_prefix` / appends `operator_suffix`:

```python
def _serialize_findings(pkg, findings, art, *, prefix=None, suffix=None) -> str:
    # ... existing header + ART block emission (lines 366-373 unchanged) ...
    out.append("<!-- BEGIN AUTO-GENERATED -->")
    out.append("## Index")
    out.append("| ID | Class | Surface | Status |")
    # ... existing Index + Detalle loop (lines 378-398 unchanged) ...
    out.append("<!-- END AUTO-GENERATED -->")
    if suffix:
        out.extend(line.rstrip("\n") for line in suffix)
    # operator_prefix prepended BEFORE header (above ART block per HARN-07 contract)
    if prefix:
        return "\n".join(prefix) + "\n".join(out) + "\n"
    return "\n".join(out) + "\n"
```

**`append_finding` extension pattern — `idempotent_by_title` flag** (HARN-08/10, extends lines 403-494):

Add `idempotent_by_title: bool = False` keyword after `regression=None` (around line 414). When True, before the existing `existing[fid].status != "OPEN"` preservation guard (line 473), check title presence:

```python
if idempotent_by_title:
    for existing_finding in findings_list:
        if existing_finding.title == title:
            # Title already present — refresh ART only and return.
            path.write_text(_replace_art_block(text, art), encoding="utf-8")
            return path
```

Closes HARN-10 (D-MATZ-27 EXPECTED terminal dedupe) AND HARN-08 (cross-driver content-addressed dedupe) with the SAME 5-LOC change in the harness. Driver-side adoption is one kwarg flip per call-site.

**Error-handling pattern** (lines 438-447, unchanged):

```python
if class_ not in FINDING_CLASSES:
    raise ValueError(...)
if status not in STATUS_LIFECYCLE:
    raise ValueError(...)
if "\n" in title or "\r" in title:
    raise ValueError(f"title debe ser una sola línea; recibido {title!r} (CR-02 invariant)")
```

NEW validation when `idempotent_by_title=True`: title MUST be unique by intent — duplicate-title-with-different-content is treated as no-op (rationale: operator-aligned semantics).

---

### `main_matriz.py` (driver smoke — surgical CR fixes + HARN-10)

**Analog:** self. Phase 7 D-05 + Phase 8 D-21 patterns apply (atomic commit per CR + RED-before-GREEN for the multi-site/thread-safety subset).

**CR-04 `_first_dict` distinguishability** (lines 182-189 — `mocked` regression test):

Current code (lines 182-189):

```python
def _first_dict(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return cast(dict[str, Any], payload[0])
    return None
```

Phase 11 fix sketch — distinguish 3 cases (`no_data` / `wrong_type` / `ok`) using a typed return OR a side-channel finding emission per case (planner picks minimal blast radius):

```python
def _first_dict(payload: Any, *, fname: str | None = None) -> dict[str, Any] | None:
    if not isinstance(payload, list):
        # wrong_type — was silently None
        if fname is not None:
            fid = _next_fid()
            append_finding(_PKG, fid=fid, class_="SHAPE", surface="sync",
                status="OPEN", title=f"{fname}: payload no es list",
                expected="list[dict] (envelope-unwrapped)",
                actual=f"type={type(payload).__name__}",
                diff="downstream SafeModel diff SKIPPED",
                base_url=primary.client._base_url)
        return None
    if not payload:
        return None  # empty-list — legitimate no_data, no finding
    if not isinstance(payload[0], dict):
        # wrong_type — was silently None
        ...
        return None
    return cast(dict[str, Any], payload[0])
```

**CR-02 `probe_login_sync` `FAIL`→`FINDING` uniformity** (lines 411, 428):

Current code emits `"FAIL"` (lines 411 + 428). Driver elsewhere uses `"FINDING"` for auth failures (e.g., lines 1707/1722/1737 use `"FINDING"` for ERROR-MAP probes). Fix: change both `return ProbeResult("login_sync", "FAIL", ...)` to `"FINDING"`. Cascade SKIPPED behavior unchanged (`_auth_failed = True` still set).

Mocked test idiom (analog `verification/test_matriz_sweep_snapshot.py`):

```python
def test_probe_login_sync_returns_FINDING_on_auth_failure(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://api.remarkets.primary.com.ar/auth/getToken",
                            status_code=401)
    main_matriz._auth_failed = False  # reset module-level state
    result = main_matriz.probe_login_sync()
    assert result.status == "FINDING"   # NOT "FAIL"
    assert result.name == "login_sync"
```

**CR-01 `probe_schema_snapshot` `sample_params` vs snapshot path alignment** (lines 1297-1321):

Current code uses placeholders like `"accountId": "<PRIMARY_ACCOUNT>"` (line 1306-1320) inside the `sample_params` dict — these are written to the **schema envelope file** (`_write_or_check_schema` line 222). Meanwhile, the actual HTTP request path templates (`_ENDPOINT_TEMPLATES` lines 127-145) interpolate the live `PRIMARY_ACCOUNT` value via `_envelope_probe`. Result: snapshot envelope claims `accountId=<PRIMARY_ACCOUNT>` placeholder but path metadata reflects the live account. Fix: align both — either resolve `_PRIMARY_ACCOUNT` in both places (and redact via the existing PII-discipline pattern from `main_higyrus.py:769-789`) OR replace both with literal placeholder strings consistently.

Mocked regression test asserts `envelope["sample_params"]` and the path used in the captured request reflect the SAME redaction state.

**CR-06 bare `except Exception` narrowing** (10 sites in main_matriz.py per grep, plus 19 in main_higyrus.py):

Per `<decisions>` §D-CR-02, this is **RED first**: write `verification/test_main_drivers_bare_except.py` using `ast.parse(Path("main_matriz.py").read_text())` and walk for `ast.ExceptHandler` with `type is None` or `type=ast.Name("Exception")` and `body` shapes that swallow without re-raise. Test FAILS RED on `main`. Then narrow each site to specific subclasses: `httpx.HTTPError`, `PrimaryAPIError`, `HigyrusAPIError`, `AttributeError` (per call-site). NEVER mask `KeyboardInterrupt` / `SystemExit` (bare `except Exception` ALREADY excludes these, but `except:` would not — verify the AST guard rejects bare-bareword too).

The Phase 8 D-21 split-by-file commit pattern applies: 2 commits (one for `main_matriz.py`, one for `main_higyrus.py`) per `<specifics>` §CR-06.

**HARN-10 D-MATZ-27 dedupe** (lines 2093-2114):

Current code unconditionally appends the EXPECTED terminal. Fix per `<specifics>` — flip to `idempotent_by_title=True`:

```python
# Lines 2093-2114 — replace unconditional append with idempotent flavor:
append_finding(
    _PKG,
    fid=fid,
    class_="SHAPE",
    surface="sync",
    status="EXPECTED",
    title="prod-vs-remarkets divergence acknowledged",
    expected=(...),
    actual=(...),
    diff="N/A (acknowledged limitation, not detected drift)",
    base_url=base,
    idempotent_by_title=True,   # NEW — HARN-10 fix
)
```

**Error-handling pattern preserved** (existing — lines 412 / 1092 / 1172 / 1251 etc.):

Existing `except Exception as exc` blocks at probe boundaries (`probe_login_sync`, `probe_field_type_map`, error probes) are the CR-06 narrowing scope. The narrowing must preserve the EXISTING `append_finding(..., class_="ERROR-MAP", status="OPEN", title=f"... unexpected {type(exc).__name__}", ...)` idiom — only the `except` clause shape changes.

---

### `main_higyrus.py` (driver smoke — CR-07 + CR-06 + CR-08)

**Analog:** self (`_capture_sync_query_string` / `_capture_async_query_string` lines 228-328).

**CR-07 `event_hooks` thread-safety** (lines 233-318):

Current code mutates `httpx.Client.event_hooks` IN-PLACE (lines 271 + 320):

```python
# Current (sync):
hooks_with_spy: dict[str, list[Any]] = {
    "request": [*original_hooks.get("request", []), _spy],
    "response": list(original_hooks.get("response", [])),
}
try:
    client.event_hooks = hooks_with_spy
    higyrus_client.get_movimientos(cuenta, fecha_desde, fecha_hasta)
except Exception:
    pass
finally:
    client.event_hooks = original_hooks
```

Multiple concurrent callers (multi-event-loop, or async + sync from same process) corrupt the shared module-level `_client.event_hooks`. ROADMAP cites "lock OR per-request hook injection" — `<specifics>` calls per-request hook injection **preferred** (no shared state mutation cross-event-loop) but more invasive.

**Phase 11 fix sketch (per-request hook injection, preferred)**:

```python
# Pass spy as a per-request keyword arg to a one-shot httpx.Client.send() OR
# build a fresh httpx.Client(event_hooks={"request": [_spy]}) for this single
# capture — discard after. NO mutation of shared client.event_hooks.
```

**Alternative (lock, minimal blast radius)**:

```python
_event_hooks_lock = threading.Lock()   # module-level

with _event_hooks_lock:
    original_hooks = client.event_hooks
    try:
        client.event_hooks = hooks_with_spy
        higyrus_client.get_movimientos(cuenta, fecha_desde, fecha_hasta)
    finally:
        client.event_hooks = original_hooks
```

Async mirror uses `asyncio.Lock()` for the `aio._client` path. Per D-CR-02, RED first: `packages/higyrus-client/tests/test_event_hooks_thread_safety.py` spawns 2 threads invoking `_capture_sync_query_string` concurrently and asserts both captured queries are non-empty AND `client.event_hooks` post-test equals `original_hooks` (no corruption). Test fails RED on current code path.

**CR-06 bare except narrowing** (19 sites per grep):

Same pattern as `main_matriz.py` — narrow `except Exception:` at lines 274/325 and elsewhere. The 2 sites at lines 273-280 and 322-326 already have the contract documented in their docstrings ("CR-03 review-04: broadened to Exception for parity") — those specific sites must preserve their current behavior (capture, swallow, return None) but narrow to `(httpx.HTTPError, HigyrusAPIError, HigyrusAuthError)`.

**CR-08 line-length >100 cols cosmetic** (main_higyrus.py:767 per REQUIREMENTS):

CURRENT line 767 (`if _resolved_cuenta is None:`) is 41 cols — the violation referenced in REQUIREMENTS has likely drifted. `<specifics>` says "split or silence with `# noqa`" — Phase 11 enforces this via `uv run ruff check --no-fix && uv run ruff format --check` as the SOLE gate per D-CR-02. NO new regression test required. The actual cosmetic sites at lines 18, 20, 22, 26-32 are docstring rst literal blocks where ruff already excepts long lines; planner verifies via `awk 'length>100'` after the other CR fixes settle.

---

### `main_iol.py` + `main_ambito_financiero.py` (driver smoke — HARN-08 adoption only)

**Analog:** self. Surgical: flip selected `append_finding(...)` call-sites to `idempotent_by_title=True` for the small set of probes that emit identical-title findings on every run (e.g., terminal EXPECTED/NO-FIX style entries). The planner identifies these by grep — most call-sites are status="OPEN" with unique titles per-probe and DON'T need the flag. No CR fixes scope here; HARN-08 only.

**Imports pattern** (already aligned — both drivers use `from verification.findings import append_finding` per `main_iol.py:75` and `main_ambito_financiero.py:50`).

---

### `verification/test_findings_append_only.py` (NEW — HARN-07/09 regression)

**Analog:** `verification/test_logging_root_unchanged.py` lines 1-40 (cross-cutting verification test idiom).

**Imports pattern** (analog):

```python
"""HARN-07 / HARN-09 — append_finding preserves operator content cross-runs.

Invariant: after N re-runs of append_finding against a temp findings file
that has operator-added narrative (BEFORE <!-- BEGIN AUTO-GENERATED --> and
AFTER <!-- END AUTO-GENERATED --> plus Classification:/Rationale:/Regression:
bullets INSIDE finding sections), SHA256 of operator content == initial SHA256.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from verification.findings import append_finding, write_findings, findings_path
```

**Core regression pattern** (per `<specifics>` HARN-09 contract — "N veces re-run vs estado inicial"):

```python
def test_operator_fields_survive_N_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Initialize a clean findings file with the marker scaffold.
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    path = write_findings("test-pkg")
    # 2. Inject operator-added narrative ABOVE the auto-zone + Resolution: bullets
    #    INSIDE one finding section.
    canonical = path.read_text(encoding="utf-8")
    operator_blob = "## Operator Narrative\nClassification: NO-FIX (out of scope v1.1)\n\n"
    path.write_text(operator_blob + canonical, encoding="utf-8")
    initial_sha = hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()
    # 3. Run append_finding 3× with identical args (idempotent intent).
    for _ in range(3):
        append_finding("test-pkg", fid="F-01", class_="SHAPE", surface="sync",
                       status="OPEN", title="t", expected="e", actual="a", diff="d")
    # 4. After 3 runs, operator narrative MUST be byte-identical.
    final = path.read_text(encoding="utf-8")
    assert operator_blob in final
    # ART block timestamp WILL change between runs — but operator narrative below
    # markers must be byte-identical.
```

**Test execution pattern**: `uv run pytest verification/test_findings_append_only.py -q` — < 1s per Phase 8 D-21 sampling latency budget.

---

### `verification/test_findings_dedupe_by_title.py` (NEW — HARN-08/10 regression)

**Analog:** `verification/test_retry_mutation_gate.py:1-40` (parametric × packages cross-cutting invariant).

**Core pattern**:

```python
def test_idempotent_by_title_does_not_duplicate(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    for _ in range(5):
        append_finding("test-pkg", fid=f"F-{_:02d}", class_="SHAPE", surface="sync",
                       status="EXPECTED", title="prod-vs-remarkets divergence acknowledged",
                       expected="...", actual="...", diff="N/A",
                       idempotent_by_title=True)
    # Read final file; count occurrences of the title.
    text = findings_path("test-pkg").read_text(encoding="utf-8")
    assert text.count("prod-vs-remarkets divergence acknowledged") == 1   # NOT 5
```

---

### `packages/higyrus-client/tests/test_event_hooks_thread_safety.py` (NEW — CR-07 RED→GREEN)

**Analog:** `verification/test_async_cancellation.py:1-100` + Phase 9 mocked-HTTP idiom from `packages/higyrus-client/tests/test_multi_account.py`.

**Imports pattern** (analog):

```python
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from pytest_httpx import HTTPXMock

import main_higyrus
import higyrus_client
```

**RED→GREEN regression pattern** (per Phase 8 D-21 / Phase 9 D-04):

```python
def test_concurrent_capture_does_not_corrupt_event_hooks(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Configure 2 concurrent captures of _capture_sync_query_string.
    # ASSERT: both captures return non-None queries AND client.event_hooks
    # post-test == client.event_hooks pre-test (no corruption).
    higyrus_client.configure(base_url="https://test", username="u", password="p", client_id="t")
    httpx_mock.add_response(url__regex=r".*/login.*", json={"token": "x"})
    httpx_mock.add_response(url__regex=r".*/movimientos.*", json=[])
    pre_hooks = higyrus_client.client._client.event_hooks
    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [pool.submit(main_higyrus._capture_sync_query_string,
                            "1", dt.date.today(), dt.date.today()) for _ in range(2)]
        results = [f.result() for f in futs]
    assert all(r is not None for r in results)
    assert higyrus_client.client._client.event_hooks == pre_hooks   # no corruption
```

---

### `verification/test_main_drivers_bare_except.py` (NEW — CR-06 RED→GREEN cross-pkg lint)

**Analog:** `verification/test_logging_root_unchanged.py:1-40` (cross-pkg invariant via import + walk).

**Core pattern** (per `<specifics>` CR-06 split):

```python
import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVERS = ["main_matriz.py", "main_higyrus.py"]

@pytest.mark.parametrize("driver", _DRIVERS)
def test_no_bare_except_Exception_in_driver(driver: str) -> None:
    tree = ast.parse((_REPO_ROOT / driver).read_text(encoding="utf-8"))
    bare_sites: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            # Bare `except:` → type is None. Bare `except Exception:` → type=ast.Name("Exception").
            if node.type is None or (isinstance(node.type, ast.Name) and node.type.id == "Exception"):
                bare_sites.append((node.lineno, ast.unparse(node.type) if node.type else "<bare>"))
    assert not bare_sites, f"{driver} has bare except sites: {bare_sites}"
```

The test fails RED on `main` (10 + 19 = 29 sites). Plan task splits the fix into 2 commits per `<specifics>` CR-06: one per driver. After each commit the test is parametrized GREEN for that driver.

---

### `verification/test_main_matriz_first_dict.py` (NEW — CR-04 mocked)

**Analog:** `verification/test_matriz_sweep_snapshot.py:1-60` (mocked-driver-probe idiom).

**Core pattern**:

```python
import main_matriz

def test_first_dict_distinguishes_no_data_from_wrong_type(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    # ok case — list[dict, ...]
    assert main_matriz._first_dict([{"a": 1}], fname="get_segments") == {"a": 1}
    # no_data — empty list — NO finding emitted
    assert main_matriz._first_dict([], fname="get_segments") is None
    # wrong_type — emits a SHAPE finding via append_finding
    result = main_matriz._first_dict("not-a-list", fname="get_segments")
    assert result is None
    findings_text = (tmp_path / "matriz-client-findings.md").read_text(encoding="utf-8")
    assert "get_segments: payload no es list" in findings_text
```

(Two siblings — `test_main_matriz_login_fail_uniformity.py` and `test_main_matriz_schema_snapshot_alignment.py` — follow the identical analog with assertions targeted at CR-02 / CR-01 respectively.)

---

### `pyproject.toml` housekeeping — `[tool.ruff] extend-exclude`

**Analog:** existing `[tool.ruff]` block in repo-root `pyproject.toml` + Phase 8 deferred-items.md call-out at `.planning/phases/08-.../08-VALIDATION.md` lines 305-307.

**Pattern** (per `<specifics>` Option A — 1-line `extend-exclude`):

```toml
[tool.ruff]
line-length = 100
target-version = "py312"
extend-exclude = [
    ".claude/skills/spike-findings-market-libs/sources/**",
    ".planning/spikes/**",
]
```

Verifies via `uv run ruff check .` (full repo scope) → exit 0 (currently 108 errors from spike artifacts per Phase 8 VALIDATION.md §Pre-existing Out-of-Scope Issues). Required for `CI green final` success criterion (`<code_context>` §Integration Points).

---

## Shared Patterns

### Atomic per-CR commit (Phase 8 D-21 template — `<canonical_refs>` §Phase 8 commits 745503c + 625cb55)

**Source:** Phase 8 commits `745503c test(08): fix CR-01 — exercise real Risk surface in 401 reauth guard` + `625cb55 test(08): fix CR-02 — exercise real Risk surface for auth_basic redaction guard`.

**Apply to:** All 6 CR fix tasks in Plan B (CR mega-plan), per D-CR-01.

**Commit message template** (one per CR):

```
fix(11): CR-NN — <one-liner> (close-out v1.1)

- Test: <regression test file path> RED → GREEN
- Fix: <source file path + line range> — <what changed>
- Closes: CR-NN (WR-NN in code review report)
- Phase 8 CR-01/02 atomic pattern (745503c, 625cb55).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

CR-06 splits into 2 commits (one per driver) per `<specifics>`. CR-07 + CR-06 use RED-before-GREEN ordering per D-CR-02 (test commit FIRST asserting current code FAILS, then fix commit). CR-01/02/04 do single RED+GREEN commits (driver-level mocked tests). CR-08 is `ruff format --check`-only, no test, single commit.

---

### Append-only verification-cycle invariant (Phase 5 D-08 — `<code_context>` §Established Patterns)

**Source:** `.planning/verification/<pkg>-findings.md` files committed at `4d48e07` (baseline `verification-cycle-2026-Q2`).

**Apply to:** All 4 findings.md files. Phase 11 enforces this via the new HARN-07/09 regression test (`verification/test_findings_append_only.py`). The contract: post-N-runs SHA256 of operator content == post-1-run SHA256.

**Verification command**:

```bash
git diff 4d48e07 -- .planning/verification/<pkg>-findings.md
# Expected output: NO operator content removed; only ART block timestamps + new
# auto-generated findings between markers.
```

---

### Cross-package parametric regression test idiom (Phase 8 D-21 + Phase 9 D-04)

**Source:** `verification/test_retry_mutation_gate.py` + `verification/test_logging_no_token_leak.py` + `verification/test_max_retries_validation.py`.

**Apply to:** `verification/test_findings_dedupe_by_title.py` + `verification/test_main_drivers_bare_except.py` (both parametric × packages or × drivers).

**Pattern**:

```python
import pytest
_PACKAGES = ["ambito-financiero-client", "iol-client", "higyrus-client", "matriz-client"]

@pytest.mark.parametrize("pkg", _PACKAGES)
def test_invariant(pkg: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    ...
```

---

### Driver-level mocked regression via pytest-httpx (Phase 7 CR-05 idiom)

**Source:** `verification/test_matriz_sweep_snapshot.py:1-60`.

**Apply to:** CR-01/02/04 driver-level unit tests.

**Imports pattern**:

```python
from __future__ import annotations
from collections.abc import Iterator
from typing import Any
import main_matriz
import pytest
from pytest_httpx import HTTPXMock
import matriz_client
```

**Test idiom**: `httpx_mock.add_response(url=..., json=...)` + invoke probe via `main_matriz.probe_X()` directly + assert on returned `ProbeResult.status` / `ProbeResult.detail` / side-effects on findings.md (via `tmp_path` monkeypatch).

---

### LIVE-01 acceptance-bar pattern (`<decisions>` §D-LIVE-01 + Phase 9 BUG-02 NO-FIX override)

**Source:** `.planning/phases/09-deferred-bug-fixes/09-VERIFICATION.md` frontmatter NO-FIX override pattern.

**Apply to:** `.planning/phases/11-.../11-VALIDATION.md` LIVE-01 evidence section.

**Pattern**:

```markdown
## LIVE-01 Evidence

**Baseline:** commit `4d48e07` ("docs(05): baseline DRIFT-02 cycle closure (verification-cycle-2026-Q2)")

**Run command (per package):**
- `uv run --package <pkg> python main_<name>.py --live`

**Acceptance bar (operator-gated per D-LIVE-01):**

| Package | Pre-existing PRE-baseline status | Post-run status | Operator disposition |
|---|---|---|---|
| ámbito | PASS (0 findings) | <PASS/FAIL/NEW> | <PASS / NEW-BUG-XX / NO-FIX> |
| iol | PASS | <PASS/FAIL/NEW> | ... |
| higyrus | PASS | <PASS/FAIL/NEW> | ... |
| matriz | F-02 + F-09 fixed in Phase 9 | <PASS/FAIL/NEW> | ... |

**Blocking regressions (NO operator gate — block close):**
- Wire URL changes sync vs async (`test_sync_async_isolation.py` divergence)
- Probe outcome flips PASS→FAIL for PRE-baseline findings
- Credential leak in logs (`test_logging_no_token_leak.py` FAILURE)
```

---

## No Analog Found

None — every Phase 11 deliverable maps to an existing in-tree pattern (Phase 11 is by design a close-out phase per ROADMAP, reusing infrastructure landed in Phases 5-10).

---

## Per-Plan File Index (for downstream `gsd-planner` consumption)

### Plan A — Harness hardening (HARN-07/08/09/10)

| File | Action | Pattern source |
|---|---|---|
| `verification/findings.py` | EXTEND `_ParsedFile`, `_parse_findings`, `_serialize_findings`, `append_finding(idempotent_by_title=...)` | self (in-place) |
| `verification/test_findings_append_only.py` | NEW | `verification/test_logging_root_unchanged.py` |
| `verification/test_findings_dedupe_by_title.py` | NEW | `verification/test_retry_mutation_gate.py` |
| `.planning/verification/{ambito,iol,higyrus,matriz}-findings.md` | MIGRATE (inject markers — one-time) | baseline `4d48e07` |
| `main_matriz.py` line 2097 | MODIFY (`idempotent_by_title=True`) | self |
| `main_iol.py`, `main_higyrus.py`, `main_ambito_financiero.py` | MODIFY (flip selected `append_finding` calls to `idempotent_by_title=True` where titles repeat) | self |

### Plan B — CR mega-plan (CR-01/02/04/06/07/08)

| File | Action | Pattern source | TDD bucket |
|---|---|---|---|
| `packages/higyrus-client/tests/test_event_hooks_thread_safety.py` | NEW (CR-07 RED) | `verification/test_async_cancellation.py` | RED-first (D-CR-02) |
| `main_higyrus.py` lines 228-328 | MODIFY (CR-07 GREEN — per-request hook injection OR lock) | self | RED-then-GREEN |
| `verification/test_main_drivers_bare_except.py` | NEW (CR-06 RED, parametric × 2 drivers) | `verification/test_logging_root_unchanged.py` | RED-first |
| `main_matriz.py` 10 sites | MODIFY (CR-06 GREEN — commit 1) | self | RED-then-GREEN |
| `main_higyrus.py` 19 sites | MODIFY (CR-06 GREEN — commit 2) | self | RED-then-GREEN |
| `verification/test_main_matriz_first_dict.py` | NEW (CR-04 mocked) | `verification/test_matriz_sweep_snapshot.py` | RED+GREEN single commit |
| `main_matriz.py` lines 182-189 | MODIFY (CR-04 GREEN) | self | same commit as test |
| `verification/test_main_matriz_login_fail_uniformity.py` | NEW (CR-02 mocked) | `verification/test_matriz_sweep_snapshot.py` | RED+GREEN single commit |
| `main_matriz.py` lines 411, 428 | MODIFY (CR-02 GREEN) | self | same commit as test |
| `verification/test_main_matriz_schema_snapshot_alignment.py` | NEW (CR-01 mocked) | `verification/test_matriz_sweep_snapshot.py` | RED+GREEN single commit |
| `main_matriz.py` lines 1297-1321 | MODIFY (CR-01 GREEN) | self | same commit as test |
| `pyproject.toml` | MODIFY (CR-08 housekeeping + spike-artifacts `extend-exclude`) | self | ruff-only gate (no test) |
| `main_higyrus.py:767` (or current location of >100 col cosmetic) | MODIFY (CR-08 GREEN) | self | ruff-only gate |

### Plan C — LIVE-01 final gate

| File | Action | Pattern source |
|---|---|---|
| `main_iol.py`, `main_higyrus.py`, `main_matriz.py`, `main_ambito_financiero.py` | RUN (live, NO edits) | per-driver CLI |
| `.planning/verification/{ambito,iol,higyrus,matriz}-findings.md` | RE-RUN APPEND (driver-side only — operator narrative preserved by Plan A) | HARN-07 contract |
| `.planning/verification/CYCLE-REPORT.md` Q#6 | UPDATE | self |
| `.planning/phases/11-.../11-VALIDATION.md` LIVE-01 section | NEW | `.planning/phases/10-.../10-VALIDATION.md` LIVE-02 evidence |

---

## Metadata

**Analog search scope:**
- `verification/` (findings.py + 12 test files)
- `main_*.py` (4 drivers at repo root)
- `.planning/verification/` (4 baseline findings.md files)
- `.planning/phases/{05,07,08,09,10}-*/` (PATTERNS.md + VALIDATION.md for analog)
- Phase 8 commits `745503c` + `625cb55` (per-CR atomic commit template)

**Files scanned:** ~30 (4 drivers, 12 verification tests, 4 findings.md, 5 phase PATTERNS.md/VALIDATION.md, `verification/findings.py`)

**Key patterns identified:**
1. **In-place extension of `findings.py`** — `_parse_findings` + `_serialize_findings` already preserve operator status; Phase 11 adds BEGIN/END markers as additive contract (~50 LOC delta vs full rewrite).
2. **Per-CR atomic commit (Phase 8 template)** — 6 CR fixes = 6 commits (CR-06 splits to 2, CR-07+CR-06 use RED-before-GREEN); Phase 8 `745503c`/`625cb55` are the canonical references.
3. **RED-before-GREEN for thread-safety + multi-site (Phase 8 D-21 + Phase 9 D-04)** — CR-07 (event_hooks concurrency) and CR-06 (≥20 sites) both follow this; CR-01/02/04 driver-mocked tests are RED+GREEN single-commit.
4. **Cross-pkg parametric regression test idiom** — `verification/test_retry_mutation_gate.py` and `verification/test_logging_no_token_leak.py` are the templates; Phase 11 adds 2 more parametric tests in the same style.
5. **Driver-level mocked test via `pytest-httpx`** — `verification/test_matriz_sweep_snapshot.py` is the template for CR-01/02/04 driver-unit tests (`httpx_mock.add_response(...)` + invoke probe + assert ProbeResult).
6. **Append-only baseline invariant (Phase 5 D-08)** — operator narrative in findings.md SHA256-preserved cross-runs; HARN-07/09 regression enforces this contract.

**Pattern extraction date:** 2026-06-14
