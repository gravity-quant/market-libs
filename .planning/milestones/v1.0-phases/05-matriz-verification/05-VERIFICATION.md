---
phase: 05-matriz-verification
verified: 2026-06-10T03:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run main_matriz.py against remarkets sandbox and confirm SUMMARY: PASS=17 FAIL=0 SKIPPED=9 FINDING=2 is still reproducible"
    expected: "Driver exits 0 with expected counts; live run confirms remarkets sandbox responds correctly"
    why_human: "Live run result is an operator-executed one-time observation captured in SUMMARY. Verifier cannot reproduce it without live credentials and sandbox availability."
  - test: "Confirm F-09 (get_instruments_by_cfi with malformed CFI not raising PrimaryAPIError) is still present in the current codebase"
    expected: "Calling get_instruments_by_cfi(cast(CFICode, 'INVALID-CFI')) should demonstrate the confirmed bug behavior (no PrimaryAPIError raised). This is intentionally deferred to a future cycle."
    why_human: "F-09 is classified CONFIRMED without a regression fix. Verifying the bug is real requires running against a live endpoint or at minimum a careful manual code trace."
---

# Phase 5: Matriz Verification Report

**Phase Goal:** The Matriz client is fully verified read-only against the remarkets sandbox with raw-payload diffing and deliberate error-path coverage, order mutation is verified by mock only behind hard gates, every finding is environment-labeled, and the per-package closing reports lock the full cycle.
**Verified:** 2026-06-10T03:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Auth flow (login + lazy-auth) verified live against remarkets; full read-only REST surface exercised; market-data assertions are shape/type/presence only with market-hours guard (MATZ-01, MATZ-02, MATZ-07) | VERIFIED | `probe_login_sync` + 18 sweep probes in main_matriz.py (1954 lines); `test_client.py` Verified-live section (12 invariant tests, line 502); live run SUMMARY `PASS=17 FAIL=0 SKIPPED=9` per 05-03-SUMMARY.md |
| 2 | Each model's raw payload diffed against `from_api` fields (both directions); envelope keys confirmed present; unmapped KeyError fixed to PrimaryAPIError (MATZ-03, MATZ-04) | VERIFIED | `_unwrap` helper present in client.py (1 def, 19 invocations); 0 raw `_get(...)[key]` patterns remain; `diff_safemodel_bidirectional` wired in `probe_field_type_map` in main_matriz.py; 18 envelope regression tests in test_client.py |
| 3 | `{"status":"ERROR"}` → PrimaryAPIError exercised across 3 distinct error conditions (bogus symbol, invalid account, malformed param) (MATZ-05) | VERIFIED | 3 always-on error probes in main_matriz.py (probe_error_bogus_symbol, probe_error_invalid_account, probe_error_malformed_cfi); 3 corresponding MATZ-05 mock tests in Verified-live section |
| 4 | new/replace/cancel_order verified by mock only behind hard gates; GET-as-write quirk preserved; prod-vs-sandbox gap recorded (MATZ-06) | VERIFIED | MATZ-06 section in test_client.py (10 tests: 5 new_order + 1 replace + 1 cancel + 3 GET-quirk sentinels asserting `request.method == "GET"`); no live calls to mutation endpoints in main_matriz.py (grep confirmed 0 reachable calls) |
| 5 | All discrepancies classified in matriz-client-findings.md; schema snapshots committed; every confirmed bug fixed (sync-only) with regression; per-package closing reports produced for all 4 verified packages (DRIFT-02) | VERIFIED | `.planning/verification/matriz-client-findings.md` exists (139 lines, F-01..F-10 classified); 8 schema snapshots in `.planning/verification/schemas/matriz-client/`; CYCLE-REPORT.md exists (103 lines); `## Cycle Closure` appended to all 4 findings files; F-09 CONFIRMED but explicitly deferred per operator decision (Option A caveat documented) |

**Score:** 5/5 truths verified

### Deferred Items

Items not yet met but explicitly addressed in the operator-ratified caveat documented in CYCLE-REPORT.md:

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | F-09: get_instruments_by_cfi with malformed CFI does not raise PrimaryAPIError (CONFIRMED, no regression) | Future cycle | CYCLE-REPORT.md Open question #3: "F-09 fix deferred to a future cycle/milestone — until then verify_cycle_closure('matriz-client') returns FAIL with missing=[F-09]". Operator decision B explicitly accepted. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `verification/safemodel_diff.py` | Duck-typed cross-package diff helper | VERIFIED | Exists; `def diff_safemodel_bidirectional` + `def _is_safemodel_like` both present; `__all__ = ["diff_safemodel_bidirectional"]`; no cross-package coupling |
| `verification/cycle_report.py` | Structural CONFIRMED/FIXED regression linkage validator | VERIFIED | Exists; `def verify_cycle_closure` present; imports `findings_path`; references `CONFIRMED`/`FIXED`; `OSError` guard (CR-02) confirmed at line 162-169 |
| `verification/__init__.py` | Barrel exports `diff_safemodel_bidirectional` | VERIFIED | Contains 2 occurrences of `diff_safemodel_bidirectional` (import + `__all__` entry); `verify_cycle_closure` NOT in barrel (correct per modularity preference) |
| `packages/matriz-client/src/matriz_client/client.py` | `_unwrap` helper + 18 envelope refactors + `_token` raise + §6.3 docstrings + CR-01 non-dict guard | VERIFIED | `def _unwrap`: 1; `_unwrap(`: 19; `assert _token is not None`: 0; `raise RuntimeError`: 1; `Never refactor to POST`: 3; `not isinstance(raw, dict)` guard: 1 (line 168) |
| `packages/matriz-client/tests/test_client.py` | Regressions section (18+1) + Verified-live (12) + MATZ-06 (10) | VERIFIED | Line 940; 114 tests total pass; `# ------ Regressions ------`: 1; `raises_primary_api_error_on_missing_envelope_key`: 18; sentinel: 1; Verified-live: 12; MATZ-06: 10 |
| `main_matriz.py` | Full ~25-probe driver, sync-only, secrets-redacted, cycle closure wired | VERIFIED | 1954 lines; 24 `def probe_*` functions; `asyncio`: 0 occurrences; `verify_cycle_closure`: 4; `diff_safemodel_bidirectional`: 4; `remarkets`: 11; `PRIMARY_ACCOUNT` in secrets (line 1833-1835) |
| `main_higyrus.py` | Inline helper removed; imports from barrel | VERIFIED | `_diff_safemodel_bidirectional`: 0; `def _is_optional`: 0; `diff_safemodel_bidirectional`: 3 (import + invocation + comment); mypy passes |
| `packages/matriz-client/.env.example` | 5 opt-in env vars with comments | VERIFIED | `PRIMARY_ACCOUNT=`: 1; `MATRIZ_SAMPLE_*` vars: 4 |
| `.planning/verification/matriz-client-findings.md` | F-01..F-10 classified | VERIFIED | Exists (139 lines); F-09 CONFIRMED; `## Cycle Closure` appended |
| `.planning/verification/CYCLE-REPORT.md` | Consolidated cross-package cycle report | VERIFIED | Exists (103 lines); 4-package stats table; 6 open questions; cycle validation table |
| `.planning/verification/schemas/matriz-client/*.json` | 8 PII-free schema snapshots (D-21 envelope) | VERIFIED | 8 files: get-all-instruments.json, get-instrument-detail.json, get-instruments-by-cfi-esxxxx.json, get-instruments-by-segment.json, get-instruments-details.json, get-market-data.json, get-segments.json, get-trades.json |
| `tests/test_cycle_report.py` | 2 CR-02 regression tests | VERIFIED | Exists (122 lines); 2 tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main_matriz.py::probe_field_type_map` | `verification/safemodel_diff.py::diff_safemodel_bidirectional` | `from verification import diff_safemodel_bidirectional` | WIRED | 4 occurrences in main_matriz.py including import + calls |
| `main_matriz.py::main` | `verification/cycle_report.py::verify_cycle_closure` | `from verification.cycle_report import verify_cycle_closure` (4 pkgs loop) | WIRED | 4 occurrences confirmed |
| `client.py::get_segments (and 17 others)` | `client.py::_unwrap` | `_unwrap(_get(path), "segments", path)` | WIRED | 18 call sites; 0 raw `_get(...)[key]` remaining |
| `client.py::_unwrap` | `exceptions.py::PrimaryAPIError` | `raise PrimaryAPIError(status="ERROR", description=f"missing envelope key...")` | WIRED | Confirmed at `missing envelope key` grep: 1 |
| `test_client.py::Regressions` | `matriz_client.PrimaryAPIError` | `pytest.raises(PrimaryAPIError); assert "missing envelope key" in exc_info.value.description` | WIRED | 18 occurrences of `missing envelope key` in test_client.py |
| `client.py::_request (else branch)` | `RuntimeError` | `if _token is None: raise RuntimeError("did not populate _token")` | WIRED | `assert _token is not None`: 0; `raise RuntimeError`: 1; `did not populate _token`: 1 |
| `verification/__init__.py` | `verification/safemodel_diff.py::diff_safemodel_bidirectional` | `from verification.safemodel_diff import diff_safemodel_bidirectional` | WIRED | 2 occurrences in __init__.py |
| `main_higyrus.py` | `verification/safemodel_diff.py::diff_safemodel_bidirectional` | `from verification import diff_safemodel_bidirectional` | WIRED | `_diff_safemodel_bidirectional`: 0; `diff_safemodel_bidirectional`: 3 |
| `main_matriz.py::main` | `sys.exit(1)` | `if "remarkets" not in base: ABORT + sys.exit(1)` | WIRED | 11 occurrences of `remarkets` in main_matriz.py |
| `main_matriz.py::main` | `PRIMARY_ACCOUNT secret redaction` | `account_env = os.getenv("PRIMARY_ACCOUNT", ""); secrets.append(account_env)` | WIRED | Lines 1833-1835 confirmed |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `client.py::get_segments` | `list[Segment]` | `_get("/rest/segment/all")` via `_unwrap` | Yes — live HTTP request + deserialization | FLOWING |
| `test_client.py::Verified-live` | Mock responses for URL invariants | `httpx_mock.add_response(url=<full URL>)` | Yes — mock returns non-empty JSON matching live schema | FLOWING |
| `main_matriz.py::probe_field_type_map` | `payloads dict` | Accumulated from 18 sweep probes | Yes — populated from live API responses | FLOWING |
| `verification/cycle_report.py::verify_cycle_closure` | `tuple[bool, list[str]]` | `path.read_text` of `<pkg>-findings.md` | Yes — reads real markdown files | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `_unwrap` count in client.py | `grep -c "_unwrap(" client.py` | 19 | PASS |
| No raw `_get(...)[key]` indexing | `grep -cE '_get\([^)]+\)\["' client.py` | 0 | PASS |
| No `assert _token` | `grep -c "assert _token" client.py` | 0 | PASS |
| CR-01 non-dict guard present | `grep -n "not isinstance.*raw.*dict" client.py` | line 168 | PASS |
| CR-02 OSError guard present | `grep -c "OSError" cycle_report.py` | 2 | PASS |
| WR-01 PRIMARY_ACCOUNT in secrets | `grep -c "account_env" main_matriz.py` | 5 | PASS |
| WR-08 key names redacted in higyrus | `grep "cuentas\[0\]" main_higyrus.py` | `cuentas[0]=<dict, {len(first)} keys hidden>` | PASS |
| Full test suite | `uv run pytest -q` | 277 passed, 1 deselected | PASS |
| mypy packages/matriz-client | `uv run mypy packages/matriz-client` | Success: no issues found in 12 source files | PASS |
| mypy verification | `uv run mypy verification` | Success: no issues found in 10 source files | PASS |
| ruff check | `uv run ruff check .` | All checks passed | PASS |
| ruff format | `uv run ruff format --check .` | 71 files already formatted | PASS |

### Probe Execution

Probes are operator-executed live runs — not scripted files. See Behavioral Spot-Checks above for automated verifiable checks.

| Probe | Type | Result | Status |
|-------|------|--------|--------|
| `uv run python main_matriz.py` (live vs remarkets) | Operator live run | PASS=17 FAIL=0 SKIPPED=9 FINDING=2 per 05-03-SUMMARY.md | PASS (operator-reported, human verify needed) |
| `uv run pytest packages/matriz-client -q` | Automated | 114 passed | PASS |
| `uv run pytest tests/test_cycle_report.py -q` | Automated | 2 passed | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MATZ-01 | 05-02, 05-03 | Auth flow (login + lazy-auth) verified live against remarkets | SATISFIED | `probe_login_sync` in main_matriz.py; live run PASS confirmed |
| MATZ-02 | 05-02, 05-03 | Read-only REST surface sweep with raw payloads retained | SATISFIED | 18 sweep probes; 8 schema snapshots captured |
| MATZ-03 | 05-01, 05-02 | Bidirectional diff of raw payload vs model fields | SATISFIED | `diff_safemodel_bidirectional` wired in `probe_field_type_map` |
| MATZ-04 | 05-01 | Envelope keys confirmed present; unmapped KeyError → PrimaryAPIError | SATISFIED | `_unwrap` helper; 18 sites refactored; 18 regression tests |
| MATZ-05 | 05-02, 05-03 | ERROR path exercised: bogus symbol, invalid account, malformed param | SATISFIED | 3 always-on error probes + 3 mock tests in Verified-live |
| MATZ-06 | 05-03 | new/replace/cancel mock-only; GET-as-write quirk locked | SATISFIED | 10 MATZ-06 tests; 3 GET-method sentinels; no live mutation calls |
| MATZ-07 | 05-02, 05-03 | Market-data assertions shape/type/presence only; market-hours guard | SATISFIED | `probe_get_market_data` with LA.date stale check; market-hours sentinel in Verified-live |
| DRIFT-02 | 05-01, 05-04 | Per-package closing reports; confirmed bugs fixed with regression; cycle closed | SATISFIED | CYCLE-REPORT.md; `## Cycle Closure` on all 4 findings files; `verify_cycle_closure` × 4; F-09 deferred per operator Option A |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `packages/matriz-client/tests/test_client.py` | MATZ-06 count discrepancy: SUMMARY claims 11 tests, codebase contains 10 | INFO | SUMMARY.md arithmetic error (`5+1+1+3=10`, not 11). Does not affect functionality or test coverage. 10 tests are present and passing. |
| `packages/matriz-client/tests/test_client.py` | `F-NN` placeholder in regression test docstrings | INFO | Intentional per SUMMARY.md known stubs — Plan 05-03 assigned real fids. Non-blocking. |
| `.planning/ROADMAP.md` | Success Criteria #5 references `matriz-findings.md` but actual file is `matriz-client-findings.md` | INFO | Typo in ROADMAP, not a code defect. Convention is `<pkg>-findings.md` (consistent with all other packages). |
| `verification/cycle_report.py` | Pre-existing WR findings (WR-02..WR-07) from REVIEW.md are quality concerns not yet addressed | WARNING | WR-02 (FAIL vs FINDING inconsistency in probe_login_sync), WR-03 (HTTP/2 resource leak), WR-04 (_first_dict silent swallow), WR-05 (18-probe boilerplate duplication), WR-06 (bare except Exception), WR-07 (hooks mutation locking). None are blockers per REVIEW classification. |

No `TBD`, `FIXME`, or `XXX` comment-style debt markers found in any phase-modified source files. The `XXX` occurrences in code strings (e.g., `"INVALID-ACCT-XXXXX"`, `"ESXXXX"`) are intentional test data literals, not debt markers.

### Human Verification Required

### 1. Live Run Reproducibility

**Test:** Run `uv run --package matriz-client python main_matriz.py` with valid `PRIMARY_USER`/`PRIMARY_PASSWORD`/`PRIMARY_BASE_URL=https://api.remarkets.primary.com.ar` in `.env`.
**Expected:** `SUMMARY: PASS=17 FAIL=0 SKIPPED=9 FINDING=2` (or similar — account-scoped probes will vary based on `PRIMARY_ACCOUNT` configuration). No `FAIL=` lines. Driver exits 0.
**Why human:** Live API availability, sandbox state, and operator credentials are required. The one-time run result (PASS=17) is documented in 05-03-SUMMARY.md but cannot be replicated by automated codebase inspection.

### 2. F-09 Confirmed Bug Behavior

**Test:** Trace or manually test that calling `get_instruments_by_cfi(cast(CFICode, "INVALID-CFI"))` against a live endpoint does NOT raise `PrimaryAPIError` (confirming the bug is real, not a false classification).
**Expected:** The call returns without raising (or raises a different exception type), confirming the ERROR-MAP gap that makes `verify_cycle_closure("matriz-client")` return FAIL.
**Why human:** F-09 is CONFIRMED without a regression test by operator decision. The deferred status is intentional. A human should confirm the bug remains present before the next cycle fixes it.

### Gaps Summary

No automated blocking gaps found. All 5 observable truths verified against codebase evidence. The phase goal is achieved in the codebase.

The two human verification items are informational/confirmatory:
1. Live run reproducibility is inherently a human concern (external API dependency).
2. F-09 deferred status is an intentional operator decision — the DRIFT-02 signal is functioning as designed (cycle_closure_matriz_client = FAIL until fix is applied in a future cycle).

The MATZ-06 count discrepancy (10 tests in code vs 11 claimed in SUMMARY) is a minor SUMMARY arithmetic error: `5 new_order + 1 replace + 1 cancel + 3 GET-sentinels = 10`. The 10 tests that exist match the plan specification exactly and all pass.

---

_Verified: 2026-06-10T03:00:00Z_
_Verifier: Claude (gsd-verifier)_
