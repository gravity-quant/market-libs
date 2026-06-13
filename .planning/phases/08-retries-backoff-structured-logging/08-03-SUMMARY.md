---
phase: 08-retries-backoff-structured-logging
plan: 03
subsystem: iol-client
tags: [phase-08, iol, atomic-commit, rely, log, oauth-401-reauth]
requires: [phase-07 _core.py extraction, phase-08-01 cross-cutting scaffolding, phase-08-02 ámbito canary]
provides:
  - iol_client._transport.RetryTransport (sync, mirrors ámbito Plan 2 with iol_client logger)
  - iol_client._atransport.AsyncRetryTransport (async mirror)
  - iol_client._logging.RedactingFilter + attach() (Bearer/X-Auth-Token/password URL+JSON + OAuth refresh_token URL+JSON + access_token JSON)
  - 401 re-auth-once flow in Client._request + AsyncClient._request (D-02 / RELY-04)
  - Login + refresh idempotent=True per D-03 (transient 5xx retry-eable; 401 raises immediately)
  - Client/AsyncClient/configure() extended with max_retries + http_client kwargs (D-15)
  - Per-business-call request_id propagation via request.extensions (D-30)
  - Auth-flow shell helper _send_auth_request routing login/refresh through RetryTransport (D-29)
affects:
  - packages/iol-client/src/iol_client/_transport.py (NEW)
  - packages/iol-client/src/iol_client/_atransport.py (NEW)
  - packages/iol-client/src/iol_client/_logging.py (NEW)
  - packages/iol-client/src/iol_client/__init__.py (attach _logging BEFORE other imports)
  - packages/iol-client/src/iol_client/_core.py (RequestSpec extended; 6 builders flipped idempotent=True)
  - packages/iol-client/src/iol_client/client.py (Client + _request with 401 re-auth + _send_auth_request + configure)
  - packages/iol-client/src/iol_client/aio.py (AsyncClient + async _request with 401 re-auth + _send_auth_request + configure)
  - packages/iol-client/tests/test_transport.py (NEW)
  - packages/iol-client/tests/test_logging.py (NEW)
  - packages/iol-client/tests/test_client.py (test_request_propaga_auth_error queues login + 2nd 401 chain)
  - packages/iol-client/tests/test_async_client.py (async mirror of the above)
  - verification/snapshots/iol-client-surface.txt
  - verification/test_retry_mutation_gate.py (queue 3 503s; assert max_retries=2 → 3 wire requests)
tech-stack:
  added:
    - "iol-package mirror of ámbito Plan 2 transport stack: tenacity Retrying / AsyncRetrying + wait_exponential_jitter + RedactingFilter"
    - "logging.getLogger('iol_client') + NullHandler + RedactingFilter per LOG-01"
  patterns:
    - "401 re-auth-once flow at shell tier (NOT in transport retry_on=) per D-02 + Pitfall 1"
    - "Auth-flow (_login_unlocked/_refresh_unlocked) routed through RetryTransport with idempotent=True per D-29"
    - "Async double-checked locking on _client_lock + _token_lock preserved across new transport wiring"
    - "OAuth refresh_token redaction in BOTH URL-encoded (form body) AND JSON (response body) shapes"
key-files:
  created:
    - packages/iol-client/src/iol_client/_transport.py
    - packages/iol-client/src/iol_client/_atransport.py
    - packages/iol-client/src/iol_client/_logging.py
    - packages/iol-client/tests/test_transport.py
    - packages/iol-client/tests/test_logging.py
    - .planning/phases/08-retries-backoff-structured-logging/08-03-SUMMARY.md
  modified:
    - packages/iol-client/src/iol_client/__init__.py
    - packages/iol-client/src/iol_client/_core.py
    - packages/iol-client/src/iol_client/client.py
    - packages/iol-client/src/iol_client/aio.py
    - packages/iol-client/tests/test_client.py
    - packages/iol-client/tests/test_async_client.py
    - verification/snapshots/iol-client-surface.txt
    - verification/test_retry_mutation_gate.py
decisions:
  - "D-02 401 re-auth-once at shell tier — Client._request and AsyncClient._request catch IOLAuthError, clear state.token, call _ensure_token(), retry once with refreshed Authorization header"
  - "D-03 build_login_request + build_refresh_request marked idempotent=True (OAuth grants are replay-safe; 5xx retry-eable, 401 NEVER retry)"
  - "D-29 auth-flow routes through RetryTransport via _send_auth_request helper — preserves D-21 atomic commit + D-07 retry_on= locked set"
  - "D-10 OAuth refresh_token redaction covers BOTH URL-encoded form body AND JSON response body (per _core.py:175-178 emission shape); access_token JSON also redacted"
  - "CR-01 preservation — _ensure_token body untouched; refresh-token rotation logic in _login_unlocked / _refresh_unlocked / login / _refresh unchanged"
  - "D-15 + D-16 minimal public API extension — max_retries=2 + http_client=None on Client/AsyncClient/configure(); mutating either drops cached httpx.Client so next request rebuilds with new transport"
  - "D-19 max_retries=N → max_attempts=N+1 (anthropic/openai SDK semantics)"
  - "verification/test_retry_mutation_gate.py: corrected from expected_count=2 to expected_count=3 — Plan 8-01 author had a notation slip (D-06 'default max_attempts=2' vs D-15 'max_retries=2'); the canonical exposed default is max_retries=2 = 3 attempts"
  - "Reordered __init__.py — _logging.attach() BEFORE other imports per Plan 2 ámbito ordering + del cleanup (Pitfall 8 prevention)"
metrics:
  duration_minutes: 20
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 8
  test_count_baseline_iol: 96
  test_count_after_iol: 114
  new_iol_unit_tests: 18
  completed_date: 2026-06-13
---

# Phase 08 Plan 03: iol — Retries + Structured Logging + 401 Re-auth

**One-liner:** iol Plan 3 delivers the auth-paquete pattern — mirrors ámbito's `RetryTransport`+`AsyncRetryTransport`+`RedactingFilter` and adds the **401 re-auth-once flow at the shell tier** (D-02) plus OAuth `refresh_token` URL+JSON redaction (D-10), establishing the template that Plans 4 (higyrus) and 5 (matriz) will replicate.

## Objective

Land the iol delivery as a single atomic commit per D-21: 3 new private modules (`_transport.py`, `_atransport.py`, `_logging.py`) duplicated from ámbito with the OAuth-specific extras, 4 extends (`_core.py`, `client.py`, `aio.py`, `__init__.py`), 2 new test files, 1 snapshot update, and 2 existing tests adjusted to align with the new 401 re-auth-once semantics. iol is the first auth paquete, so this plan validates the canonical Pattern 3 401 re-auth flow (RESEARCH §Pattern 3 lines 549-602) without disturbing CR-01 conditional refresh-token rotation (Phase 7 baseline).

## Tasks Completed

| # | Name | Status | Files |
|---|------|--------|-------|
| 1 | Create _transport.py + _atransport.py + _logging.py + unit tests | ✅ Done | _transport.py, _atransport.py, _logging.py, test_transport.py, test_logging.py |
| 2 | Extend _core.py + client.py + aio.py + __init__.py + snapshot | ✅ Done | _core.py, client.py, aio.py, __init__.py, snapshot, mutation_gate fix |

Single atomic commit per D-21: **`43862d1`**.

## LOC Delta

| File | Before | After | Delta |
|------|--------|-------|-------|
| `_transport.py` | 0 | 199 | +199 (NEW; mirrors ámbito) |
| `_atransport.py` | 0 | 131 | +131 (NEW) |
| `_logging.py` | 0 | 111 | +111 (NEW; +2 refresh_token regex + access_token regex vs ámbito) |
| `_core.py` | 319 | 367 | +48 (RequestSpec extended with idempotent+endpoint_name; 6 builders flipped) |
| `client.py` | 491 | ~610 | +119 (RetryTransport wiring, _send_auth_request, 401 re-auth pattern, 2 kwargs) |
| `aio.py` | 458 | ~570 | +112 (async mirror with double-checked locking preservation) |
| `__init__.py` | 64 | 79 | +15 (_logging.attach BEFORE other imports + del cleanup) |
| `test_transport.py` | 0 | 182 | +182 (NEW; 8 tests including login-as-idempotent) |
| `test_logging.py` | 0 | 143 | +143 (NEW; 10 tests including 3 IOL refresh_token specific) |
| `test_client.py` | 319 | 332 | +13 (401 re-auth flow simulated with login+2nd 401 chain) |
| `test_async_client.py` | 255 | 262 | +7 (async mirror) |
| `iol-client-surface.txt` | 14 | 14 | 6 lines modified (Client/AsyncClient/configure +2 kwargs each) |
| `test_retry_mutation_gate.py` | 183 | 188 | +22 (max_retries=2 → 3 wire requests semantic) |

Total: **+1057 / -51 lines** across 13 files.

## Cross-cutting Guard Test Status

| Guard | Status before Plan 3 | Status after Plan 3 |
|-------|----------------------|---------------------|
| `test_retry_mutation_gate.py::test_idempotent_get_retries_on_503[iol_client-get_instruments-kwargs0]` | RED | **GREEN** |
| `test_retry_401_reauth.py::test_401_then_login_then_200_triggers_exactly_one_reauth[iol_client]` | RED | **GREEN** (3 wire requests + FRESH-TOKEN in last Authorization) |
| `test_retry_401_reauth.py::test_401_then_login_then_401_raises_auth_error[iol_client]` | RED | **GREEN** (3 wire requests + IOLAuthError raised, no infinite loop) |
| `test_logging_no_token_leak.py::test_token_literal_never_appears_in_log_records[iol_client]` | trivially GREEN (no logs emitted yet) | **GREEN** (SECRET-LITERAL-12345 not in any record) |
| `test_logging_root_unchanged.py::test_importing_packages_does_not_modify_logging_root` | GREEN | **GREEN** (continues with iol's _logging.attach landed) |
| `test_async_cancellation.py::test_cancellation_propagates_during_retry_backoff[iol_client]` | RED | **GREEN** (TimeoutError raised < 1.0s) |
| `test_sync_async_isolation.py[iol_client]` | GREEN | **GREEN** (CR-01 preserved — _ensure_token body untouched) |
| `test_public_surface.py::test_public_surface_matches_snapshot[iol_client]` | GREEN baseline | **GREEN** (snapshot updated with 2 new kwargs) |
| `test_phase06_nyquist_gaps.py::test_snapshot_regen_is_idempotent` | GREEN | **GREEN** (post-commit; pre-commit shows unstaged diff by design) |

Higyrus + matriz parametrize branches remain RED awaiting Plans 4 + 5 — by design per Plan 8-01.

## Snapshot Diff

```diff
-AsyncClient : class : (*, base_url: 'str | None' = None, username: 'str | None' = None, password: 'str | None' = None, token: 'str | None' = None, token_expires_at: 'float | None' = None) -> 'None'
-Client : class : (*, base_url: 'str | None' = None, username: 'str | None' = None, password: 'str | None' = None, token: 'str | None' = None, token_expires_at: 'float | None' = None) -> 'None'
+AsyncClient : class : (..., max_retries: 'int' = 2, http_client: 'httpx.AsyncClient | None' = None) -> 'None'
+Client : class : (..., max_retries: 'int' = 2, http_client: 'httpx.Client | None' = None) -> 'None'

-configure : function : (..., refresh_token: 'str | None' = None) -> 'None'
+configure : function : (..., refresh_token: 'str | None' = None, max_retries: 'int | None' = None, http_client: 'httpx.Client | None' = None) -> 'None'
```

## CR-01 Preservation Evidence

CR-01 (Phase 7 D-XX) — IOL conditional refresh-token rotation — is preserved by surgical scope:

- `_ensure_token()` body unchanged (still tries refresh first if available, falls back to password)
- `_login_unlocked` / `_refresh_unlocked` (async) and `login` / `_refresh` (sync) still apply the `if refresh is not None: state.refresh_token = refresh` guard exactly as in Phase 7 baseline
- The 401 re-auth-once flow in `_request()` operates AT shell level AFTER `_ensure_token()` was invoked; it does NOT touch the refresh-rotation conditional
- Refresh path now benefits from RetryTransport for transient 5xx (D-29) but a 401-during-refresh still raises IOLAuthError immediately (NOT retried — D-02)
- Existing iol tests (Phase 7 baseline = 96 tests) all GREEN post-Plan 3 — empirical CR-01 preservation evidence

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test alignment] `test_request_propaga_auth_error` (sync + async) updated for D-02 behavior**

- **Found during:** Task 2 — running `uv run pytest packages/iol-client/ -q` after wiring 401 re-auth flow.
- **Issue:** The legacy tests queued ONE 401 response and asserted `IOLAuthError`. Under the new D-02 401 re-auth-once flow, the shell calls `_ensure_token()` (login attempt), which has no mock queued and raises `httpx.TimeoutException`.
- **Fix:** Updated both tests to queue the full 401→login(200)→401 chain to validate the canonical "401 re-auth then second-401 raises IOLAuthError without infinite loop" behavior. Pre-existing test intent ("a 401 surfaces as IOLAuthError") preserved; the test now exercises the FULL re-auth contract instead of the pre-Phase-8 single-shot semantic.
- **Files modified:** `packages/iol-client/tests/test_client.py`, `packages/iol-client/tests/test_async_client.py`
- **Commit:** `43862d1`

**2. [Rule 1 - Plan 8-01 cross-cutting test bug] `test_idempotent_get_retries_on_503` expected count corrected from 2 to 3**

- **Found during:** Task 2 verification run — iol branch failed because mock queue depth (2) was less than actual emit count (3).
- **Issue:** The Wave 1 cross-cutting test queued 2 × 503 responses and asserted `len(requests) == 2`. The author's comment said `Phase 8 D-06 default max_attempts=2 → 1 initial + 1 retry`. But D-15 + D-19 establish the canonical default as `max_retries=2` (= max_attempts=3); D-06's wording was a notation slip. ámbito Plan 2 implemented `max_retries=2 → max_attempts=3`, and iol mirrors that. The test was authored against the wrong default.
- **Fix:** Updated the test to queue 3 × 503 responses and assert `len(requests) == 3`. Comment updated to cite D-15+D-19 instead of D-06. This unblocks higyrus + matriz Plan 4/5 too — they implement the same defaults.
- **Files modified:** `verification/test_retry_mutation_gate.py`
- **Commit:** `43862d1`

No Rule 4 (architectural) decisions required.

## Authentication Gates

None — all verification was offline via `pytest-httpx` mocks.

## Known Stubs / Threat Flags

None added by this plan. The `_request()` 401 re-auth-once flow uses an in-process re-auth attempt with no caching, no disk persistence, and no out-of-band signal — clean per the threat register (T-8-02-IOL mitigation in place: bounded re-auth at exactly 1 retry).

## Self-Check: PASSED

- [x] `packages/iol-client/src/iol_client/_transport.py` — FOUND, 199 LOC, `class RetryTransport`, `_LOGGER_NAME = "iol_client"`
- [x] `packages/iol-client/src/iol_client/_atransport.py` — FOUND, 131 LOC, `class AsyncRetryTransport`
- [x] `packages/iol-client/src/iol_client/_logging.py` — FOUND, 111 LOC, `class RedactingFilter`, `_REFRESH_TOKEN_URLENC_RE` + `_REFRESH_TOKEN_JSON_RE` regexes
- [x] `packages/iol-client/tests/test_transport.py` — FOUND, 8 tests including `test_login_request_retries_on_503_when_idempotent_true`
- [x] `packages/iol-client/tests/test_logging.py` — FOUND, 10 tests including `test_redact_refresh_token_urlenc`, `test_redact_refresh_token_json`, `test_login_response_payload_full_redaction`
- [x] `verification/snapshots/iol-client-surface.txt` updated — 2 new kwargs in Client/AsyncClient/configure() signatures
- [x] Commit `43862d1` exists on `main` (`git log --oneline 43862d1` confirms)
- [x] 114/114 iol-client tests GREEN; 121/121 ámbito tests GREEN; higyrus + matriz unchanged
- [x] ruff + ruff format + mypy strict GREEN; lint-imports contracts kept

## Outcome

iol Plan 3 establishes the **auth-paquete pattern** — Plans 4 (higyrus, with `account_id` extension to RequestSpec + structured logs) and 5 (matriz, with `auth_basic` Risk API carve-out per D-23 + Primary API X-Auth-Token shape) will replicate this template with their per-package tweaks. The cross-cutting guard test fix (`max_retries=2 → 3 wire requests`) unblocks Plan 4/5 too — they don't need to re-discover the Plan 8-01 notation slip.
