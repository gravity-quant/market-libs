---
phase: 09-deferred-bug-fixes
plan: 02
subsystem: testing
tags: [phase-09, higyrus, iol-cross-pkg, bug-fixes, multi-account, triage, wave-1, regression-tests, deferred-fixes]

# Dependency graph
requires:
  - phase: 06-compat-safety-net-client-class-skeleton
    provides: "_state.py per-instance state with `account_id` forward-decl (D-13) — Plan 09-02 removes it (D-09)"
  - phase: 07-core-py-extraction-sync-async-logic-dedup
    provides: "_core.py single-site fix pattern + per-call id_cuenta kwarg on account-dependent endpoints"
  - phase: 08-retries-backoff-structured-logging
    provides: "RetryTransport + RedactingFilter (active in main_higyrus.py live re-run); `RequestSpec.account_id` D-11 propagation (DIFFERENT from `_state.account_id`)"
provides:
  - "BUG-04 mocked regression test: per-call `id_cuenta` produces distinct wire requests"
  - "BUG-04 driver probe: `probe_multi_account_iteration` + `HIGYRUS_SAMPLE_CUENTAS` env var override"
  - "`_state.account_id` field removed from higyrus AND iol (D-09 cross-package cleanup)"
  - "(PENDING — operator checkpoint) BUG-02 quick-triage bucket classification + F-02 finding update"
affects: [phase-09-deferred-bug-fixes, phase-11-harness-final-uat, v1.2-backlog]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Multi-account iteration via per-call `id_cuenta` kwarg (D-08 per-call only; constructor pattern deferred to v1.2)"
    - "Driver probe with CSV env var override + live fallback + skip cascade (Pattern 4 in 09-RESEARCH.md)"

key-files:
  created:
    - "packages/higyrus-client/tests/test_multi_account.py — mocked 2-cuenta regression"
  modified:
    - "packages/higyrus-client/src/higyrus_client/_state.py — drop `account_id` field + docstring entry"
    - "packages/iol-client/src/iol_client/_state.py — drop `account_id` field + docstring entry (cross-package D-09)"
    - "main_higyrus.py — add `_SAMPLE_CUENTAS_CSV` + `probe_multi_account_iteration` + register in `_D_HIGY_10_ORDER`"

key-decisions:
  - "D-08 per-call only: constructor pattern `Client(account_id=X)` NOT introduced (deferred to v1.2 if UX feedback)"
  - "D-09 cross-package: `_state.account_id` removed from BOTH higyrus AND iol in one atomic plan (micro-deviation from per-package atomicity is acceptable per CONTEXT D-11)"
  - "Pitfall 1 enforced: `RequestSpec.account_id` (Phase 8 D-11) and `request.extensions['account_id']` (transport) are SEPARATE concerns — NOT touched"
  - "Probe lifecycle order: `multi_account_iteration` registered AFTER `errors_envelope_async` and BEFORE `auth_401` so it benefits from `_auth_failed` cascade and can consume `get_listado_cuentas` if CSV override is unset"

patterns-established:
  - "Multi-account regression: `for acct in (a, b): httpx_mock.add_response(url=f'.../{acct}/...')` then loop the same way through client.get_X(id_cuenta=acct) and assert distinct wire URLs"
  - "Driver probe source-order pattern: env var CSV > live API > SKIPPED with actionable message"

requirements-completed: [BUG-04]

# Metrics
duration: ~25min (Tasks 1+2 complete; Task 3 awaiting operator)
completed: 2026-06-13
---

# Phase 9 Plan 02: higyrus BUG-02 triage + BUG-04 multi-account Summary

**Per-call `id_cuenta` regression test (mocked 2-cuentas) + driver probe with CSV override + cross-package `_state.account_id` cleanup; BUG-02 quick-triage paused at operator checkpoint.**

## Status

**PARTIAL — paused at operator checkpoint (Task 3).** Tasks 1 + 2 landed; Task 3 (BUG-02 live triage + bucket classification + F-02 update) requires operator-driven live re-run of `main_higyrus.py` against the Higyrus API. The operator returns the bucket signal (`a`/`b`/`c`) which the orchestrator will use to either (i) close the plan and update F-02, or (ii) spawn a continuation agent for Task 4 (bucket-`c`-only client-side fix in `_core.py`).

## Performance

- **Duration so far:** ~25 min
- **Started:** 2026-06-13T16:04:00Z
- **Task 1 complete:** 2026-06-13T16:24:00Z
- **Task 2 complete:** 2026-06-13T16:28:30Z
- **Task 3 paused:** 2026-06-13T16:29:00Z (awaiting operator)
- **Tasks complete:** 2 / 4 (Task 3 awaiting human, Task 4 conditional on Task 3 outcome)
- **Files modified:** 3 source + 1 new test + 1 driver = 5
- **Tests:** higyrus 143 → 144 (+1: `test_multi_account_iteration_via_per_call_id_cuenta`)

## Accomplishments

- BUG-04 regression test (`test_multi_account_iteration_via_per_call_id_cuenta`) guards against any future caching of `id_cuenta` at the client level — explicit assertion of 2 outgoing requests with distinct URL paths.
- BUG-04 driver probe (`probe_multi_account_iteration`) wired with three-source resolution: `HIGYRUS_SAMPLE_CUENTAS` CSV → live `get_listado_cuentas` → SKIPPED with actionable message.
- D-09 cross-package cleanup: `_state.account_id` field removed from higyrus AND iol with zero regression (research grep confirmed: 0 runtime reads of `state.account_id`). Pitfall 1 enforcement held — `RequestSpec.account_id` (Phase 8 D-11) untouched.
- Public surface snapshot zero-diff confirmed (private field; not exported).

## Task Commits

1. **Task 1: Cross-package `_state.account_id` removal** — `4f0d686` (refactor)
2. **Task 2: BUG-04 mocked regression + driver probe extension** — `4f86387` (test)
3. **Task 3: Operator-driven BUG-02 live triage** — PENDING (operator must return bucket signal)
4. **Task 4: Conditional bucket-(c) client-side fix** — PENDING (gated on Task 3 outcome)

**Plan metadata commit:** to be authored by the continuation agent after Task 3 closes, or by the orchestrator if Task 3 closes inline.

## Files Created/Modified

### Created
- `packages/higyrus-client/tests/test_multi_account.py` (56 lines) — mocked regression test using `pytest_httpx.HTTPXMock` with two explicit `add_response` calls (text-distinct wire URLs satisfy acceptance grep `fechaDesde=13%2F06%2F2026 ≥ 2`).

### Modified
- `packages/higyrus-client/src/higyrus_client/_state.py` (-4 lines: docstring entry + 2-line field block)
- `packages/iol-client/src/iol_client/_state.py` (-9 lines: docstring re-write that drops `account_id` mention + 4-line field block including its 3-line comment)
- `main_higyrus.py` (+85 lines: `_SAMPLE_CUENTAS_CSV` module-level + `probe_multi_account_iteration` function + 1 tuple entry in `_D_HIGY_10_ORDER` + 1 line in `main()`)

## Decisions Made

- **Two explicit `httpx_mock.add_response` calls instead of an f-string loop** in `test_multi_account.py`. The PLAN's acceptance criterion grepped for `fechaDesde=13%2F06%2F2026` returning `>= 2` ocurrencias. A `for acct in (a, b):` loop with f-string templating produces 1 textual occurrence; expanding to two literal `add_response` calls matches the criterion verbatim. The behavior tested is identical.
- **Probe registered between `errors_envelope_async` and `auth_401`** in `_D_HIGY_10_ORDER` (line ~163 of `main_higyrus.py`). This honors the plan's instruction to place it before `auth_401` (so `_auth_failed` cascade works) and after the listado_cuentas probes (so `get_listado_cuentas` is exercised first as a fallback source).
- **`Cuenta.id` (not `idCuenta`)** as the field name for live cuenta resolution. Confirmed via `packages/higyrus-client/src/higyrus_client/models.py:355` — `Cuenta.id: str`.

## Deviations from Plan

None - plan executed as written for Tasks 1 + 2. The two literal `add_response` calls vs. a loop are an interpretation of acceptance grep criteria, not a behavioral deviation.

## Issues Encountered

- `.env` file is not present in the worktree (only in the main checkout). Live triage of BUG-02 (Task 3) therefore cannot be automated from within this executor session; the operator must run `main_higyrus.py` in a context with credentials available.

## User Setup Required

**Task 3 requires operator action.** See `09-02-PLAN.md` `<task type="checkpoint:human-verify">` for the full step-by-step. Summary of what the operator does:
1. Confirm `.env` has valid `HIGYRUS_USER` + `HIGYRUS_PASSWORD`.
2. Re-run `uv run --package higyrus-client python main_higyrus.py` 3 times capturing `probe_get_listado_cuentas` + `probe_multi_account_iteration` output for each run.
3. Optionally enable DEBUG logging via `logging.getLogger("higyrus_client").setLevel(logging.DEBUG)` (probe-scoped, Pattern S8 try/finally).
4. Classify outcome into bucket `a` (transient → NO-FIX) / `b` (FIXED-by-environment) / `c` (reproducible client-side root cause → Task 4 needed).
5. Edit `.planning/verification/higyrus-client-findings.md` F-02 with `Status` flip + `Resolution: <bucket marker (a)/(b)/(c)> + rationale` + `Regression: <path>::<test>` (default: `tests/test_client.py::test_get_listado_cuentas_url_con_estado_alta` for buckets a/b).
6. Return resume signal: `approved (bucket a)` / `approved (bucket b)` / `bucket c → extend plan` / `multi-account FAILED: <reason>`.

## Next Phase Readiness

- Task 1 + Task 2 commits ready to merge from this worktree.
- Task 3 awaits operator action. After resolution:
  - Buckets a/b → close Plan 09-02 by updating F-02 + final metadata commit, no further code changes.
  - Bucket c → continuation agent or operator extends Plan 09-02 with `_core.py` fix + `tests/test_listado_cuentas_regression.py`.
- Plan 09-04 (Wave 3 green gate) WILL re-validate cross-leak sentinel + public-surface zero-diff over the cumulative phase 9 work.

## Verification Evidence (Tasks 1 + 2)

### Task 1 acceptance grep
```
$ grep -c "account_id" packages/higyrus-client/src/higyrus_client/_state.py
0
$ grep -c "account_id" packages/iol-client/src/iol_client/_state.py
0
$ grep -c "refresh_token" packages/iol-client/src/iol_client/_state.py
5
$ grep -c "token_expires_at" packages/higyrus-client/src/higyrus_client/_state.py
7
```

### Task 1 test suites
- `uv run pytest packages/higyrus-client/tests/ packages/iol-client/tests/ -x` → 259 passed
- `uv run pytest verification/test_sync_async_isolation.py verification/test_public_surface.py packages/higyrus-client/tests/test_logging.py packages/higyrus-client/tests/test_transport.py -x` → 34 passed, 1 skipped (matriz aio.py stub per D-25)
- `uv run ruff check packages/{higyrus,iol}-client/src/*/_state.py` → All checks passed
- `uv run mypy --strict packages/{higyrus,iol}-client/src/*/_state.py` → no issues

### Task 2 acceptance grep
```
$ grep -c "^def test_" packages/higyrus-client/tests/test_multi_account.py
1
$ grep -c "fechaDesde=13%2F06%2F2026" packages/higyrus-client/tests/test_multi_account.py
2
$ grep -c '"/5208/"' packages/higyrus-client/tests/test_multi_account.py
1
$ grep -c '"/9999/"' packages/higyrus-client/tests/test_multi_account.py
1
$ grep -c "_SAMPLE_CUENTAS_CSV" main_higyrus.py
3
$ grep -c "def probe_multi_account_iteration" main_higyrus.py
1
$ grep -c "multi_account_iteration" main_higyrus.py
8
```

### Task 2 test/build
- `uv run pytest packages/higyrus-client/tests/test_multi_account.py -x` → 1 passed
- `uv run pytest packages/higyrus-client/tests/ -x` → 144 passed (143 baseline +1)
- `uv run ruff check packages/higyrus-client/tests/test_multi_account.py main_higyrus.py` → All checks passed
- `uv run mypy --strict packages/higyrus-client/tests/test_multi_account.py` → no issues
- `uv run python -c "import main_higyrus"` → OK (smoke import)

## Self-Check

| Item | Status | Notes |
|------|--------|-------|
| Task 1 commit `4f0d686` exists | FOUND | `git log --oneline --all \| grep 4f0d686` |
| Task 2 commit `4f86387` exists | FOUND | `git log --oneline --all \| grep 4f86387` |
| `packages/higyrus-client/tests/test_multi_account.py` exists | FOUND | created in Task 2 |
| `packages/higyrus-client/src/higyrus_client/_state.py::account_id` removed | VERIFIED | grep returns 0 |
| `packages/iol-client/src/iol_client/_state.py::account_id` removed | VERIFIED | grep returns 0 |
| `main_higyrus.py::probe_multi_account_iteration` present | VERIFIED | grep returns 1 |
| `main_higyrus.py::_SAMPLE_CUENTAS_CSV` present | VERIFIED | grep returns 3 |
| `_D_HIGY_10_ORDER` includes `multi_account_iteration` | VERIFIED | grep returns 8 occurrences total |
| RequestSpec.account_id (Phase 8 D-11) intact | VERIFIED | `_core.py:117/132/310/353/408` unchanged |
| Higyrus test suite 144 pass | VERIFIED | +1 vs baseline |
| Iol test suite still GREEN | VERIFIED | included in 259-pass run |
| Cross-leak sentinel GREEN | VERIFIED | `verification/test_sync_async_isolation.py` 1 skipped (matriz D-25) but no failures |
| Public-surface zero-diff | VERIFIED | `verification/test_public_surface.py` passes (private field) |
| Ruff + mypy strict on all modified | VERIFIED | both tasks |
| Task 3 operator checkpoint reached | PARTIAL — paused | awaiting human bucket signal |
| Task 4 bucket-(c) fix landed | NOT APPLICABLE | gated on Task 3 outcome |
| F-02 finding `Resolution:` + `Regression:` lines | NOT APPLICABLE | operator owns this edit |

## Self-Check: PARTIAL — PAUSED

Tasks 1 + 2 verified PASS. Plan paused at Task 3 operator-driven checkpoint per `<parallel_execution>` and plan-level `autonomous: false` instruction.

---
*Phase: 09-deferred-bug-fixes*
*Plan: 02*
*Status: PARTIAL — paused at Task 3 operator checkpoint*
*Last update: 2026-06-13*
