---
phase: 15-driver-migration-4-refac-05
plan: 02
subsystem: testing
tags: [iol-client, ast-guard, tdd, driver-migration, single-client, oauth, httpx]

# Dependency graph
requires:
  - phase: 15-01
    provides: "AST-guard test idiom (test_main_ambito_financiero_uses_single_client_instance.py) and the dual ast.Name/ast.Attribute ctor-counting walker with 1<=count<=2 assertion"
provides:
  - "main_iol.py migrated to single sync Client() + single async AsyncClient() threaded into all 15 probes"
  - "verification/test_main_iol_uses_single_client_instance.py — AST guard capping client ctors at 2 (D-01/D-02)"
  - "D-03 forced-refresh write-site now operates on the same threaded instance the next read uses"
affects: [15-03, 15-04, phase-17]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Driver single-Client invariant enforced by an AST gate (mirrors wave-1 ámbito)"
    - "Raw _request from a driver: build RequestSpec + call instance Client._request + replicate raise-on-error (module-level shim semantic preserved)"

key-files:
  created:
    - verification/test_main_iol_uses_single_client_instance.py
  modified:
    - main_iol.py

key-decisions:
  - "Adapted the raw _request call to the instance Client._request(RequestSpec) signature + explicit raise-on-error, since Client._request (D-03) returns the raw response un-raised whereas the old module-level shim raised on 4xx/5xx"
  - "Removed the now-unused `aio` import; kept `iol_client` import (still used for iol_client.InstrumentType type aliases)"
  - "probe_auth_401's pre-existing `_token_expires_at = 0.0` reset was migrated to the threaded client (client._state.token_expires_at = 0.0) alongside the D-03 write-site"

patterns-established:
  - "Pattern 1: every sync probe_* takes a `client: Client` param; every async probe_* takes an `aclient: AsyncClient` param; no probe reaches _get_default()"
  - "Pattern 2: forced-refresh write and the verifying read share one threaded instance — the regression cannot silently no-op"

requirements-completed: [REFAC-05]

# Metrics
duration: 22min
completed: 2026-06-24
status: complete
---

# Phase 15 Plan 02: iol Driver Migration Summary

**main_iol.py now builds exactly one sync `Client()` and one async `AsyncClient()`, threaded into all 15 probes, with the D-03 forced-refresh write-site and its verifying read operating on the same instance — guarded by a new RED-first AST test.**

## Performance

- **Duration:** ~22 min
- **Started:** 2026-06-24
- **Completed:** 2026-06-24
- **Tasks:** 2 (TDD: RED test + GREEN migration)
- **Files modified:** 2 (1 created, 1 migrated)

## Accomplishments
- Authored `verification/test_main_iol_uses_single_client_instance.py` as a RED-first AST guard (count 0 on un-migrated driver → fails; count 2 post-migration → passes). Matches both `ast.Name` (bare) and `ast.Attribute` (qualified) ctor spellings.
- Migrated `main_iol.py`: `main()` builds one `Client()`, `_async_main()` builds one `AsyncClient()`, both threaded as params into every `probe_*`. Eliminated all `_get_default()` code sites (17 `_state` read sites + module-attr reads).
- D-03 critical write-site: `probe_refresh_token(client)` now writes `client._state.token_expires_at = 0.0` and reads `client.get_instruments("argentina")` on the SAME threaded `client` — the forced-refresh regression can no longer pass unseen.
- ruff check + mypy strict green on `main_iol.py`; full verification suite (230 tests) and iol-client package suite (137 tests) pass.

## Task Commits

1. **Task 1: RED — AST guard for single Client in main_iol.py** - `9d3601c` (test) — fails RED (count 0 < lower bound)
2. **Task 2: GREEN — thread single Client/AsyncClient through main_iol.py** - `2d367b2` (feat) — AST guard passes (count 2)

_TDD: RED `test(...)` commit precedes GREEN `feat(...)` commit; no REFACTOR commit needed._

## Files Created/Modified
- `verification/test_main_iol_uses_single_client_instance.py` - AST-walker asserting `1 <= (Client|AsyncClient) ctor Calls <= 2` in main_iol.py; lower bound makes RED non-vacuous.
- `main_iol.py` - Single sync + single async client threaded into all 15 probes; D-03 forced-refresh write/read share one instance; raw `_request` adapted to `RequestSpec`; finding literals untouched.

## Decisions Made
- **RequestSpec adaptation:** The plan's recipe mapped `iol_client.client._request("GET", path)` → `client._request("GET", path)`, but the instance `Client._request` takes a single `RequestSpec` (not positional method/path) and — unlike the legacy module-level shim — returns the raw response without raising on 4xx/5xx. To preserve the original behaviour (errors propagate into the `except Exception` block), the call was rewritten as `client._request(RequestSpec(method=..., path=...))` followed by `if resp.is_error: _raise_for_response(resp)`. `RequestSpec` is imported from `iol_client._core` and `_raise_for_response` from `iol_client.client`. (Rule 3 — blocking type error surfaced by mypy strict.)
- **Unused `aio` import removed:** After threading `AsyncClient`, the `aio` submodule is no longer referenced in code (only in module docstring prose). Removed to keep ruff `F401`/CI green. `iol_client` import retained — still used by `iol_client.InstrumentType` aliases. (Rule 3 — blocking lint/type error.)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Raw `_request` signature mismatch under mypy strict**
- **Found during:** Task 2 (migration)
- **Issue:** Plan recipe `client._request("GET", path)` fails mypy strict — `Client._request` expects one `RequestSpec` arg, not positional `(method, path)`. Additionally, the instance method does not raise on error status (the old module-level shim did), so a naive swap would change error-handling semantics.
- **Fix:** Built `RequestSpec(method="GET", path=...)`, called `client._request(spec)`, and replicated the shim's raise-on-error via `if resp.is_error: _raise_for_response(resp)`. Added imports `from iol_client._core import RequestSpec` and `from iol_client.client import _raise_for_response`.
- **Files modified:** main_iol.py
- **Verification:** `mypy --package iol-client main_iol.py` clean on main_iol.py; full verification suite (230 passed) green.
- **Committed in:** `2d367b2` (Task 2 commit)

**2. [Rule 3 - Blocking] Unused `aio` import after AsyncClient threading**
- **Found during:** Task 2 (migration)
- **Issue:** Threading `AsyncClient` removed all `aio.*` code references; the `aio` import became unused (ruff F401, CI-blocking).
- **Fix:** Removed `aio` from the `from iol_client import ...` line. Kept `iol_client` (used by `iol_client.InstrumentType`).
- **Files modified:** main_iol.py
- **Verification:** `ruff check main_iol.py` — all checks passed.
- **Committed in:** `2d367b2` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking issues surfaced by mypy strict / ruff).
**Impact on plan:** Both fixes were necessary to satisfy the plan's own CI-green acceptance criteria (ruff + mypy strict). No scope creep — finding literals, probe names, and asserted invariants are byte-stable.

## Note on the single write-site grep criterion

The plan's acceptance criterion `grep -c 'client\._state\.token_expires_at = 0\.0' main_iol.py == 1` returns **2**, not 1:
- `:1304` — the D-03 forced-refresh write-site in `probe_refresh_token` (the criterion's intended target).
- `:1438` — a **pre-existing** forced re-login reset in `probe_auth_401` (originally `iol_client.client._token_expires_at = 0.0`), faithfully migrated to the threaded instance.

The substantive invariant the criterion guards — the D-03 write and its verifying read share one threaded `client` instance — holds exactly (verified: `probe_refresh_token(client)` writes `client._state.token_expires_at = 0.0` then reads `client.get_instruments("argentina")` on the same `client`). The count is 2 only because `probe_auth_401` independently and legitimately resets expiry on the same (now threaded) instance; this is correct behaviour, not a defect.

## Issues Encountered
- mypy can only resolve `iol_client` under the package environment (`uv run --package iol-client mypy main_iol.py`); the bare `uv run mypy main_iol.py` reports a spurious `import-not-found`. A pre-existing, unrelated `matriz_client` stub error in `verification/mutation_gate.py` is out of scope (logged, not fixed per scope boundary).

## User Setup Required

**The per-package LIVE smoke (D-11, Criterion #4) is operator-deferred.** It requires IOL OAuth credentials (`IOL_USER`, `IOL_PASSWORD`) in `packages/iol-client/.env`, which is ABSENT in this environment. The live smoke (`uv run --package iol-client python main_iol.py`, confirming exit 0 + a real token refresh in the forced-refresh probe) CANNOT run here and is NOT a plan failure — it is operator-driven, not the Phase 17 gate. All static work is complete: AST test (RED→GREEN), full driver migration, ruff + mypy strict, and the static/unit suites (230 verification + 137 iol-client tests). No credentials were logged or committed.

## Next Phase Readiness
- iol driver migration complete and CI-green; wave-2 serial order (D-11) satisfied.
- Ready for 15-03 / 15-04 (remaining driver migrations). The single-Client AST-guard idiom is now established for both ámbito (wave 1) and iol (wave 2).
- Blocker for full phase sign-off: operator must run the iol LIVE smoke with real credentials (deferred, see User Setup Required).

---
*Phase: 15-driver-migration-4-refac-05*
*Completed: 2026-06-24*

## Self-Check: PASSED

- FOUND: verification/test_main_iol_uses_single_client_instance.py
- FOUND: .planning/phases/15-driver-migration-4-refac-05/15-02-SUMMARY.md
- FOUND commit 9d3601c (test — RED AST guard)
- FOUND commit 2d367b2 (feat — GREEN migration)
- FOUND commit fa8f15b (docs — SUMMARY)
- STATE.md / ROADMAP.md untouched (worktree mode — orchestrator owns those writes)
