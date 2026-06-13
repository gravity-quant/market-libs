---
phase: 08-retries-backoff-structured-logging
verified: 2026-06-13T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification: false
human_verification:
  - test: "Live smoke — verify retry behavior under real transient failures"
    expected: "Retries fire on real 5xx/429 responses from live APIs; Retry-After header observed and capped at 60s; no duplicate orders on matriz Primary API"
    why_human: "Cannot verify real-network backoff timing, rate limit responses, or actual duplicate-order prevention against the live remarkets environment programmatically without credentials and market availability"
  - test: "Log output legibility — consume DEBUG logs from each package during a live call"
    expected: "Structured fields (package, method, url, status_code, attempt, duration_ms) appear correctly; no credential substring (Bearer token, X-Auth-Token, password, refresh_token, auth_basic password) visible in any record at any level"
    why_human: "Subjective UX quality — consumer experience of log output cannot be asserted by automated tests alone; CI green confirms the filter fires but not that the field layout is usable"
  - test: "CI matrix Python 3.13 green — confirm all 755 tests pass on GitHub Actions for both 3.12 and 3.13"
    expected: "All CI jobs (lint, lint-imports, lint-logging, typecheck, tests 3.12, tests 3.13) show green checkmarks on the Phase 8 merge commit"
    why_human: "Local environment runs Python 3.12.11 only; VALIDATION.md records CI Python 3.13 deferred to operator checkpoint (Task 2 of Plan 6)"
  - test: "Deferred review items — confirm WR-03, WR-04, WR-05, IN-01..IN-06 have filed tracking for Phase 11"
    expected: "Each deferred item maps to either Phase 11 close-out plan or a Phase 9+ backlog entry; no deferred item silently disappears"
    why_human: "Phase 11 planning is TBD; traceability of minor deferred findings cannot be machine-verified yet"
---

# Phase 8: Retries, Backoff, Structured Logging — Verification Report

**Phase Goal:** Reliability via retries transparentes con jitter y mutation gate + observability vía logging estructurado redactado por paquete.
**Verified:** 2026-06-13T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Per-package RetryTransport/AsyncRetryTransport con full-jitter backoff (initial=1s/max=30s/exp_base=2) + Retry-After cap 60s; registro en 408/409/429/≥500 + ConnectError/ConnectTimeout/ReadTimeout | ✓ VERIFIED | `_transport.py` (179-239 LOC each) + `_atransport.py` (131-132 LOC each for ambito/iol/higyrus; absent for matriz per D-25) all contain real `tenacity.Retrying`/`AsyncRetrying` with `wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0)` + `_RETRYABLE_STATUS = frozenset({408, 409, 429, *range(500, 600)})` + `_RETRY_AFTER_CAP_S = 60.0`. `test_retry_after_cap.py` PASSED (76.67s total run). |
| 2 | Mutation-aware gate funciona end-to-end: `RequestSpec.idempotent: bool = False` default; GET endpoints marcan `True`; matriz mutating builders (new_order/cancel_order/replace_order) KEEP `False`; POST 503 → 1 outgoing request | ✓ VERIFIED | `RequestSpec.idempotent: bool = False` confirmed in all 4 `_core.py` files. Matriz `_core.py:504-572` has explicit `idempotent=False` for new_order/cancel_order/replace_order with comment "Pitfall 4 / D-01 / D-24". `test_retry_mutation_gate.py[matriz_client-new_order-kwargs0]` PASSED. `_transport.py:119-120`: `if not request.extensions.get("idempotent", False):` pass-through confirmed. `AuthError`/`PrimaryAPIError`/`HigyrusAPIError` NOT in `retry_on=` (verified by source read — only `httpx.ConnectError/ConnectTimeout/ReadTimeout` in transport exception handler). |
| 3 | 401 re-auth-once in shell `_request()`: 401→200 = 2 requests total (1 stale + re-auth + 1 fresh); 401→401 raises AuthError. matriz Risk API (auth_basic) NO re-auth per D-23. | ✓ VERIFIED | `iol_client/client.py:327-347` has explicit re-auth-once + `resp.read()` body-consume (WR-02 fix). `matriz_client/client.py:271-335` has D-23 carve-out (`if spec.auth_basic is not None:` → no re-auth). `test_retry_401_reauth.py` — 7 cases PASSED: iol/higyrus/matriz Primary (401→200 = 3 wire requests; 401→401 = AuthError); `test_matriz_risk_api_401_does_not_reauth` PASSED (CR-01 fixed: now exercises real `get_positions()` surface). WR-01 fixed: iol/higyrus async `aio.py` wraps token-clear + ensure_token in `async with lock:` to prevent concurrent duplicate logins. |
| 4 | `logging.getLogger("<pkg>")` + `NullHandler` per package; CI grep rule blocks `logging.basicConfig`/`logging.root` in `packages/*/src/`; `logging.root.handlers` unchanged after import × 4 packages | ✓ VERIFIED | All 4 `__init__.py` files confirmed: `from <pkg> import _logging as _logging_attach; _logging_attach.attach(); del _logging_attach`. CI `lint-logging` step in `.github/workflows/ci.yml` (refined in Plan 6 to match `logging\.basicConfig\s*\(` + `logging\.root\.\w` to avoid docstring false-positives). ruff `"LOG"` ruleset in root `pyproject.toml`. `grep -rnE --include='*.py' 'logging\.basicConfig\s*\(|logging\.root\.\w' packages/*/src/` returns no matches (CLEAN). `test_logging_root_unchanged.py` PASSED. |
| 5 | `RedactingFilter` per package covers Bearer/X-Auth-Token/password=/IOL refresh_token/Higyrus JSON password/matriz auth_basic; caplog with SECRET-LITERAL-12345 verifies no token in any `record.getMessage()` or `record.args` | ✓ VERIFIED | 4 distinct `_logging.py` files (89-173 LOC each) with package-specific regex patterns. Matriz: `_X_AUTH_TOKEN_RE`, `_X_PASSWORD_RE`, `_AUTH_BASIC_RE` + D-22 tuple-split. IOL: `_REFRESH_TOKEN_URL_RE`, `_REFRESH_TOKEN_JSON_RE`, `_ACCESS_TOKEN_JSON_RE`. Higyrus: `_CUIT_QUERY_RE`, `_TOKEN_JSON_RE`, `_PASSWORD_JSON_RE`. CR-02 fixed: `test_logging_no_token_leak.py[matriz]` now exercises real Risk surface with 503→200 retry (emits WARNING with `auth_basic` in extras). 5 caplog test cases PASSED including `test_matriz_auth_basic_password_not_logged`. |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Status | LOC | Details |
|----------|--------|-----|---------|
| `packages/ambito-financiero-client/src/ambito_financiero_client/_transport.py` | ✓ VERIFIED | 194 | Full `RetryTransport` with tenacity, mutation gate, Retry-After cap |
| `packages/ambito-financiero-client/src/ambito_financiero_client/_atransport.py` | ✓ VERIFIED | 132 | `AsyncRetryTransport` with `AsyncRetrying` + `asyncio.sleep` |
| `packages/ambito-financiero-client/src/ambito_financiero_client/_logging.py` | ✓ VERIFIED | 89 | `RedactingFilter` + `attach()` with Bearer/password patterns |
| `packages/iol-client/src/iol_client/_transport.py` | ✓ VERIFIED | 199 | Full `RetryTransport` + OAuth patterns |
| `packages/iol-client/src/iol_client/_atransport.py` | ✓ VERIFIED | 131 | `AsyncRetryTransport` |
| `packages/iol-client/src/iol_client/_logging.py` | ✓ VERIFIED | 111 | `RedactingFilter` + refresh_token URL/JSON patterns |
| `packages/higyrus-client/src/higyrus_client/_transport.py` | ✓ VERIFIED | 205 | Full `RetryTransport` + account_id propagation |
| `packages/higyrus-client/src/higyrus_client/_atransport.py` | ✓ VERIFIED | 132 | `AsyncRetryTransport` |
| `packages/higyrus-client/src/higyrus_client/_logging.py` | ✓ VERIFIED | 116 | `RedactingFilter` + JSON pwd/token/cuit patterns |
| `packages/matriz-client/src/matriz_client/_transport.py` | ✓ VERIFIED | 239 | Full `RetryTransport` + D-23 Risk carve-out comments, auth_basic propagation |
| `packages/matriz-client/src/matriz_client/_logging.py` | ✓ VERIFIED | 173 | `RedactingFilter` + X-Auth-Token/X-Password/auth_basic D-22 tuple-split |
| `packages/matriz-client/src/matriz_client/_atransport.py` | ✓ VERIFIED ABSENT | N/A | Correctly absent per D-25; deferred to Phase 10 REFAC-04 |
| `packages/matriz-client/src/matriz_client/aio.py` | ✓ VERIFIED | 103 | Phase 6 stub UNCHANGED per D-25 — `wc -l` returns 103 |
| `verification/test_retry_mutation_gate.py` | ✓ VERIFIED | 196 | Parametrized × 4 packages; PASSED |
| `verification/test_retry_401_reauth.py` | ✓ VERIFIED | 298 | Parametrized × iol/higyrus/matriz; 7 PASSED |
| `verification/test_retry_after_cap.py` | ✓ VERIFIED | 78 | 60s cap; PASSED |
| `verification/test_logging_root_unchanged.py` | ✓ VERIFIED | 67 | Cross-cutting; PASSED |
| `verification/test_logging_no_token_leak.py` | ✓ VERIFIED | 230 | 5 cases PASSED |
| `verification/test_async_cancellation.py` | ✓ VERIFIED | 111 | 3 PASSED + 1 SKIPPED (matriz D-25) |
| `verification/test_max_retries_validation.py` | ✓ VERIFIED | 157 | WR-06 regression; 112 parametrized cases |
| `verification/test_async_configure_resource_warning.py` | ✓ VERIFIED | 121 | WR-07 regression; 6 cases |
| `.github/workflows/ci.yml` (lint-logging step) | ✓ VERIFIED | N/A | `lint-logging` step present; refined regex avoids docstring false-positives |
| Root `pyproject.toml` (ruff LOG ruleset) | ✓ VERIFIED | N/A | `"LOG"` in `[tool.ruff.lint] select` at line 57 |
| All 4 packages `pyproject.toml` (tenacity dep) | ✓ VERIFIED | N/A | `"tenacity>=9.1.0,<10"` confirmed in all 4 packages at lines 24-25 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_transport.py` mutation gate | `_core.RequestSpec.idempotent` | `request.extensions["idempotent"]` set by shell `_request()` from `RequestSpec.idempotent` | ✓ WIRED | `_transport.py:119`: `request.extensions.get("idempotent", False)` + `client.py` sets `req.extensions["idempotent"] = spec.idempotent` |
| Shell `_request()` 401 handler | `_ensure_token()` re-auth | `except AuthError: state.token = None; _ensure_token(); retry once` | ✓ WIRED | Confirmed in iol `client.py:327-347` + higyrus + matriz Token path `client.py:300-335` |
| Matriz Risk API D-23 carve-out | No re-auth on 401 | `if spec.auth_basic is not None: ... no _ensure_token()` | ✓ WIRED | `matriz client.py:271-297` has explicit D-23 carve-out; test CR-01 fixed to exercise real surface |
| `_logging.attach()` → `__init__.py` | Package logger `NullHandler` + `RedactingFilter` | Module-level call `_logging_attach.attach(); del _logging_attach` | ✓ WIRED | Confirmed in all 4 `__init__.py` files |
| `RedactingFilter.filter()` D-22 auth_basic tuple | `request.extensions["auth_basic"]` → log record | `auth_basic` tuple set in `req.extensions["auth_basic"] = spec.auth_basic` + transport propagates to log extras | ✓ WIRED | `_transport.py` (CR-02 fix) propagates `auth_basic` from extensions to WARNING/ERROR extras; `_logging.py` `_redact_auth_basic_tuple()` splits tuple in filter |
| CI `lint-logging` grep step | `packages/*/src/` Python files | `grep -rnE 'logging\.basicConfig\s*\(|logging\.root\.\w'` | ✓ WIRED | `.github/workflows/ci.yml:42-49`; local verification returns no matches (CLEAN) |
| `RetryTransport` → `tenacity.Retrying` | backoff + retry logic | `from tenacity import Retrying, wait_exponential_jitter, stop_after_attempt, retry_if_exception_type` | ✓ WIRED | Imports confirmed in all `_transport.py` files; tenacity 9.1.4 importable |
| WR-06 `_validate_max_retries()` | `Client.__init__` / `AsyncClient.__init__` / `configure()` / `aio.configure()` | Called at every entry point | ✓ WIRED | 20 call sites confirmed across 4 packages |
| WR-07 `ResourceWarning` | `aio.configure()` when overwriting live `_state.http_client` | `warnings.warn(ResourceWarning, ...)` | ✓ WIRED | Confirmed in ambito/iol/higyrus `aio.py` |

---

### Data-Flow Trace (Level 4)

Not applicable — Phase 8 delivers transport/logging infrastructure (no UI/rendering components). The test suite verifies data flows via wire-request count assertions and `caplog` record inspection.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 755 tests GREEN (full suite including review-fix regressions) | `uv run pytest packages/ verification/ -q --no-header` | `755 passed, 3 skipped, 1 deselected in 150.83s` | ✓ PASS |
| CRITICAL Pitfall 4 — duplicate-order prevention | `uv run pytest verification/test_retry_mutation_gate.py -k new_order -v` | `1 passed, 3 deselected in 0.05s` | ✓ PASS |
| 6 cross-cutting guard tests GREEN | `uv run pytest verification/test_retry_*.py verification/test_logging_*.py verification/test_async_cancellation.py -v` | `21 passed, 1 skipped in 76.67s` | ✓ PASS |
| ruff lint (scoped) | `uv run ruff check packages/ verification/` | `All checks passed!` | ✓ PASS |
| ruff format | `uv run ruff format --check packages/ verification/` | `116 files already formatted` | ✓ PASS |
| mypy strict | `uv run mypy` | `Success: no issues found in 45 source files` | ✓ PASS |
| import-linter | `uv run lint-imports` | `Contracts: 4 kept, 0 broken` | ✓ PASS |
| CI lint-logging grep (local replication) | `grep -rnE 'logging\.basicConfig\s*\(|logging\.root\.\w' packages/*/src/` | No matches (exit 1 = clean) | ✓ PASS |
| matriz aio.py preserved at 103 LOC | `wc -l packages/matriz-client/src/matriz_client/aio.py` | `103` | ✓ PASS |
| matriz `_atransport.py` absent | `test -f packages/matriz-client/src/matriz_client/_atransport.py` | exit 1 = `ABSENT_OK` | ✓ PASS |
| tenacity 9.1.4 importable | `uv run python -c "import tenacity; ..."` | `9.1.4` | ✓ PASS (per VALIDATION.md) |

---

### Probe Execution

Not applicable for this phase — no `scripts/*/tests/probe-*.sh` convention used. Phase 8 uses pytest-based verification suite.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| RELY-01 | 08-01..06 | Retries transparentes via tenacity: 408/409/429/≥500 + ConnectError/ConnectTimeout/ReadTimeout; default max_attempts=2 | ✓ SATISFIED | `RetryTransport` + `AsyncRetryTransport` in all 4 packages; `_RETRYABLE_STATUS = frozenset({408,409,429,*range(500,600)})` + `_RETRYABLE_EXC` confirmed; per-package `test_transport.py` covers retry path |
| RELY-02 | 08-01..06 | Backoff exponencial full-jitter; Retry-After header honored with 60s cap | ✓ SATISFIED | `wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0)` in all transports; `_RETRY_AFTER_CAP_S = 60.0` + RFC 9110 parsing; `test_retry_after_cap.py` PASSED |
| RELY-03 | 08-01..06 | Mutation-aware retry gate: `idempotent: bool = False` default; GET → True; POST/PATCH never retried without True | ✓ SATISFIED | `RequestSpec.idempotent` in all 4 `_core.py`; mutation gate in all transports; `test_retry_mutation_gate.py[matriz_new_order]` PASSED (Pitfall 4 CRITICAL) |
| RELY-04 | 08-01..06 | Exactly-one 401 re-auth; AuthError/APIError/PrimaryAPIError/HigyrusAPIError NEVER in retry_on= | ✓ SATISFIED | Re-auth-once in shell `_request()` for iol/higyrus/matriz; D-23 Risk no-reauth; `test_retry_401_reauth.py` PASSED; WR-01 async race condition fixed (atomic lock) |
| LOG-01 | 08-01..06 | `logging.getLogger("<pkg>")` + NullHandler in `__init__.py`; no basicConfig; CI grep rule | ✓ SATISFIED | All 4 `__init__.py` have `_logging_attach.attach()`; CI step confirmed; local grep CLEAN; `test_logging_root_unchanged.py` PASSED |
| LOG-02 | 08-01..06 | RedactingFilter per package covering package-specific patterns | ✓ SATISFIED | 4 distinct `_logging.py` files with package-specific regex; `test_logging_no_token_leak.py` PASSED × 4 packages + `test_matriz_auth_basic_password_not_logged` PASSED |
| LOG-03 | 08-01..06 | Level conventions (DEBUG/INFO/WARNING/ERROR) + structured extra fields (package, method, url, status_code, attempt, duration_ms, account_id) | ✓ SATISFIED | Confirmed in `_transport.py` logging calls (WARNING per retry, ERROR on terminal failures); per-package `test_logging.py` (81 tests PASSED) covers structured fields |

All 7 Phase 8 requirements (RELY-01..04, LOG-01..03) are SATISFIED. No orphaned requirements for Phase 8 found in REQUIREMENTS.md (traceability table lists all 7 as "Complete").

---

### Hard Invariants

| Invariant | Check | Result | Status |
|-----------|-------|--------|--------|
| D-25: matriz `aio.py` == 103 LOC | `wc -l packages/matriz-client/src/matriz_client/aio.py` | `103` | ✓ PASS |
| D-25: matriz `_atransport.py` does NOT exist | `test -f packages/matriz-client/src/matriz_client/_atransport.py` | ABSENT | ✓ PASS |
| Phase 7 baseline 527 tests NOT regressed | Full suite passes | `755 passed, 3 skipped` (527 baseline + 228 new) | ✓ PASS |
| No `AuthError`/`PrimaryAPIError`/`HigyrusAPIError` in tenacity `retry_on=` | Verified via source read of all `_transport.py` retry_on= clauses | Only `_RETRYABLE_EXC` (ConnectError/ConnectTimeout/ReadTimeout) in transport retry_on | ✓ PASS |
| Pitfall 18: No tests weakened | VALIDATION.md explicit statement + test count grew 527→755 | 228 new tests, none removed; updated tests STRENGTHENED their contracts | ✓ PASS |

---

### Code Review Fix Closure Summary

| Finding | Severity | Status | Evidence |
|---------|----------|--------|----------|
| CR-01: `test_matriz_risk_api_401_does_not_reauth` exercised wrong surface (legacy shim, vacuously true) | Critical | ✓ CLOSED | Commit `745503c` — rewrote to call `get_positions("acc")` (real Risk surface, `idempotent=True`); falsifiability confirmed by commenting out D-23 carve-out |
| CR-02: `test_matriz_auth_basic_password_not_logged` emitted zero log records (no WARNING from non-idempotent legacy shim) | Critical | ✓ CLOSED | Commit `625cb55` — rewrote to call `get_positions()` with 503→200; `_transport.py` now propagates `auth_basic` to log extras; test asserts `auth_basic_user` preserved + `auth_basic_password == "***"` |
| WR-01: iol/higyrus async 401 re-auth token-clear outside lock (race window) | Warning | ✓ CLOSED | Commits `56c851f` (iol) + `b98e2b2` (higyrus) — atomic `async with lock:` wrapping token-clear + unlocked login |
| WR-02: 401 carve-out raise-sites skip `resp.read()` — HTTP/2 stream leak potential | Warning | ✓ CLOSED | Commits `1a20fd6` (matriz) + `6cad440` (iol) + `4770efa` (higyrus) — explicit `resp.read()` / `await resp.aread()` before all 401 raise-sites |
| WR-06: `configure(max_retries=)` accepts negatives/floats silently | Warning | ✓ CLOSED | Commit `0ab7a7d` — `_validate_max_retries()` in all 4 packages × all entry points; 112-case parametrized regression |
| WR-07: `aio.configure()` drops prior `httpx.AsyncClient` without warning (connection pool leak) | Warning | ✓ CLOSED | Commit `a8342e7` — `ResourceWarning` emitted in ambito/iol/higyrus `aio.configure()`; 6-case regression |
| WR-08: matriz `raise_for_response` raised stdlib `httpx.HTTPStatusError` instead of typed `MatrizClientError` | Warning | ✓ CLOSED | Commit `952a0de` — `_core.raise_for_response` now maps 401/403→`AuthenticationError`, other 4xx/5xx→`PrimaryAPIError`; 4 regression tests |

**Deferred (out-of-scope for Phase 8):**

| Finding | Severity | Rationale for Deferral |
|---------|----------|------------------------|
| WR-03: Redaction regex bounds unanchored (over-redact is acceptable) | Warning | Over-redaction is the safer direction; regex framework revision deferred |
| WR-04: matriz `_X_USERNAME_RE` dead code (cosmetic) | Warning | Documented inline as "for symmetry-completeness"; harmless |
| WR-05: CI `lint-logging` grep extension — detect `logging.getLogger()` with no args | Warning | `test_logging_root_unchanged.py` is the real backstop and is GREEN; grep extension is defense-in-depth |
| IN-01..IN-06: cosmetic/performance/test-cleanup findings | Info | Out of v1.1 scope per review notes |

---

### Test Count Delta

| Phase | Total | Skipped | Note |
|-------|-------|---------|------|
| Phase 7 baseline | 527 | 2 | post-Phase-7 final |
| Phase 8 green gate (Plan 6) | 627 | 3 | +100 tests (6 guard files × parametrize + 81 per-package transport+logging) |
| Phase 8 post-review-fix | **755** | **3** | **+128 regression tests**: WR-01 +2, WR-02 +4, WR-06 +112, WR-07 +6, WR-08 +4 |

3 SKIPs are all D-25 forward-references (matriz async REST deferred to Phase 10):
1. `packages/matriz-client/tests/test_fixture_reaches_production.py:64` — matriz async REST stub
2. `verification/test_async_cancellation.py:82` — "matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore"
3. `verification/test_sync_async_isolation.py:176` — "matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore"

---

### Anti-Patterns Found

| File | Pattern | Severity | Assessment |
|------|---------|----------|------------|
| `.planning/spikes/`, `.claude/skills/spike-findings-market-libs/sources/` | 108 pre-existing ruff errors (F401, F541, etc.) | ℹ️ Info | NOT Phase 8 caused; pre-existing in research artifacts. `uv run ruff check packages/ verification/` is CLEAN. Tracked in `deferred-items.md`. |
| `verification/test_async_cancellation.py` | Parametrizes matriz then skips (IN-04) | ℹ️ Info | Cosmetic; deferred as IN-04. Matrix cleanup can drop matriz from `_ASYNC_PACKAGES` in Phase 10 or 11. |
| `verification/test_retry_after_capped_at_60s` | Slow test (~76s) unmarked (IN-05) | ℹ️ Info | Deferred as IN-05; `@pytest.mark.slow_retry` can be added in Phase 11. |
| All `_logging.py` `_PASSWORD_URLENC_RE` | Regex bounds unanchored (WR-03) | ⚠️ Warning | Deferred per review; over-redaction is safer than under-redaction. Not a production correctness issue. |

No `TBD`, `FIXME`, or `XXX` markers found in Phase 8 source files (`packages/*/src/` and `verification/`).

---

### Human Verification Required

#### 1. Live Smoke — Retry Behavior Under Real Transient Failures

**Test:** Run `uv run python main_iol.py` (or equivalent) in an environment where the live API is accessible, then simulate a transient failure (or observe natural 5xx) to verify retries fire, Retry-After is respected, and no duplicate orders are issued against matriz.
**Expected:** Retry WARNING log records appear (with structured fields: package, method, url, status_code, attempt, duration_ms); no credentials appear in any log output; no duplicate order confirmation from matriz broker.
**Why human:** Requires live credentials, network access, and market availability. Cannot mock real backoff timing or real duplicate-order scenarios programmatically.

#### 2. Log Output Legibility

**Test:** Set `logging.getLogger("<pkg>").setLevel(logging.DEBUG)` for any of the 4 packages, then exercise a real or mocked request path and read the log output.
**Expected:** Structured fields present and readable; Bearer/X-Auth-Token/password/refresh_token/auth_basic password all appear as `***`; no raw credential substring visible at any log level.
**Why human:** Subjective UX quality cannot be captured by automated token-absence assertions alone; developer experience of log output matters for operational use.

#### 3. CI Matrix Python 3.13 Confirmation

**Test:** Visit the Phase 8 merge commit on GitHub and confirm all CI jobs pass on Python 3.13 (not just 3.12 which was tested locally).
**Expected:** All CI jobs (lint, lint-logging grep, lint-imports, typecheck, tests 3.12, tests 3.13) show green checkmarks.
**Why human:** Local environment is Python 3.12.11 only; VALIDATION.md records CI Python 3.13 deferred to operator checkpoint (Plan 6 Task 2). The operator checkpoint has been logged as closed (`0d6ffe9`), but this verifier cannot independently access GitHub CI status.

#### 4. Deferred Review Items Tracking

**Test:** Confirm WR-03, WR-04, WR-05, IN-01..IN-06 are tracked in Phase 9/11 planning or a backlog file.
**Expected:** Each deferred finding appears in either Phase 11 REQUIREMENTS (CR-06, CR-07, CR-08 cover some of this territory), the ROADMAP backlog section, or a `deferred-items.md` file referenced from REVIEW-FIX.md.
**Why human:** Phase 11 is TBD; the traceability from deferred minor findings to future phases cannot be machine-verified until Phase 11 plans are written.

---

### Gaps Summary

No gaps found. All 5 ROADMAP success criteria are verified with evidence from the actual codebase. All 7 requirements (RELY-01..04, LOG-01..03) are satisfied. All 7 in-scope code review findings (CR-01, CR-02, WR-01, WR-02, WR-06, WR-07, WR-08) are closed with regression tests. Hard invariants (matriz aio.py=103 LOC, `_atransport.py` absent, no root logger pollution, Pitfall 4 duplicate-order prevention) are all confirmed.

Status is `human_needed` because: (a) CI Python 3.13 matrix confirmation requires GitHub access; (b) live smoke under real network conditions cannot be automated; (c) log legibility is subjective. These are standard deferred-to-Phase-11 items per the VALIDATION.md Manual-Only Verifications table.

---

_Verified: 2026-06-13T00:00:00Z_
_Verifier: Claude (gsd-verifier, initial verification)_
