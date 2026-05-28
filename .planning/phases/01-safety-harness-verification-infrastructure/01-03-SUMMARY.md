---
phase: 01-safety-harness-verification-infrastructure
plan: 03
subsystem: testing
tags: [verification-harness, redaction, env-gate, mutation-gate, subprocess, drivers, uv]

# Dependency graph
requires:
  - phase: 01-01
    provides: verification/redaction.py (redact/safe_print) + verification/__init__.py barrel seed
  - phase: 01-02
    provides: verification/env_gate.py (require_env) + verification/mutation_gate.py (mutating_allowed)
  - phase: 01-04
    provides: verification/schema.py, capture.py, anonymize.py, findings.py re-exported by the barrel
provides:
  - Five extended main_*.py drivers gated (env) + redacted; Matriz additionally mutation-gated
  - main_verify.py aggregate runner (subprocess-per-driver, RAN/SKIPPED summary, never halts)
  - Lazy matriz_client import in mutation_gate.py so the barrel imports zero-config from any package env
affects: [phase-02, phase-03, phase-04, phase-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Zero-config driver import: `from verification import require_env, redact, safe_print` (repo root on sys.path[0])"
    - "Env gate at top of main(): `if not require_env(...): sys.exit(0)` (clean exit, batch-continues)"
    - "Subprocess-per-driver aggregate runner classifying RAN/SKIPPED from child stdout, never re-emitting raw payloads"
    - "Lazy intra-function import of a workspace package only available in its own uv env"

key-files:
  created:
    - main_verify.py
  modified:
    - main_iol.py
    - main_higyrus.py
    - main_matriz.py
    - main_wallets.py
    - verification/mutation_gate.py

key-decisions:
  - "verification/__init__.py barrel was already finalized by plans 01-01/01-04 with all four mandatory helpers — no change needed beyond making mutation_gate import lazy"
  - "main_ambito_financiero.py left untouched: no creds (no require_env), FX output non-sensitive (redaction would be a pure no-op) — per plan 'keep it minimal'"
  - "main_verify.py uses subprocess-per-driver (RESEARCH OQ1) for singleton isolation and to mirror the Phases 2-5 run command"

patterns-established:
  - "Driver env gate + sys.exit(0): missing creds print verbatim `SKIPPED <pkg>: missing X, Y` and exit clean so the batch continues"
  - "Aggregate runner prints per-package status only, never raw child stdout (credential re-emission guard)"
  - "Matriz mutation surface guarded by mutating_allowed() — unreachable by default"

requirements-completed: [HARN-01, HARN-02, HARN-03]

# Metrics
duration: ~21min
completed: 2026-05-28
---

# Phase 01 Plan 03: Wire safety helpers into the live-exploration drivers Summary

**All five main_*.py drivers now gate missing creds (verbatim SKIPPED + exit 0), redact token/credential output, Matriz double-gates its mutation surface, and a new main_verify.py subprocess runner aggregates RAN/SKIPPED across all five without ever halting.**

## Performance

- **Duration:** ~21 min
- **Started:** 2026-05-27T23:45Z (approx)
- **Completed:** 2026-05-28T00:07Z
- **Tasks:** 2
- **Files modified:** 5 (1 created, 4 modified) + 1 fixed (mutation_gate.py)

## Accomplishments

- HARN-01: every credential-bearing driver (iol/higyrus/matriz/wallets) gates env vars at the top of `main()` and prints the exact `SKIPPED <pkg>: missing X, Y` line, then `sys.exit(0)` so the batch continues. Ámbito (public) has no gate by design.
- HARN-03: `main_iol.py`'s raw `token[:12]` print is replaced by `redact(token)`; higyrus/matriz/wallets route credential-adjacent output through `safe_print(text, secrets)` with the resolved credential globals (filtered to non-empty, len >= 4) as the secrets list.
- HARN-02: `main_matriz.py` adds a `mutating_allowed()`-gated mutation branch — unreachable by default, printing `SKIPPED (mutating, guard off)`. Order placement is never run live regardless (REQUIREMENTS Out of Scope); this is the belt-and-suspenders wiring proving the gate is reachable from the driver.
- HARN-01/D-14: `main_verify.py` runs all five drivers via `uv run --package <pkg> python main_<name>.py` subprocesses, classifies each as RAN/SKIPPED from child stdout, prints a per-package aggregate summary, and never halts on a SKIPPED or child failure. Observed end-to-end: 4 SKIPPED (no `.env` in worktree) + 1 RAN (ambito), exit 0.

## Task Commits

Each task was committed atomically:

1. **Task 1: Finalize barrel + wire env gate & redaction into all five drivers** - `bf8be07` (feat)
2. **Task 2: main_verify.py aggregate runner with RAN/SKIPPED summary** - `d10c352` (feat)

## Files Created/Modified

- `main_verify.py` (created) - Aggregate runner: subprocess-per-driver, RAN/SKIPPED summary, never halts, prints per-package status only (no raw child stdout).
- `main_iol.py` (modified) - Env gate (IOL_USER, IOL_PASSWORD); `token[:12]` print replaced with `redact(token)`.
- `main_higyrus.py` (modified) - Env gate (HIGYRUS_USER, HIGYRUS_PASSWORD, HIGYRUS_BASE_URL); health + cuentas output through `safe_print`.
- `main_matriz.py` (modified) - Env gate (PRIMARY_USER, PRIMARY_PASSWORD); segments/instruments through `safe_print`; mutation branch gated by `mutating_allowed()`.
- `main_wallets.py` (modified) - Env gate (WALLETS_TOKEN, WALLETS_BASE_URL); response output through `safe_print`; kept try/except WalletsClientError.
- `verification/mutation_gate.py` (modified) - Moved `import matriz_client` from module level into `mutating_allowed()` (lazy) — see Deviations.
- `main_ambito_financiero.py` (unchanged) - Intentionally no `require_env` (public, no creds); FX output is non-sensitive so redaction would be a pure no-op (plan: "keep it minimal").

## Decisions Made

- The `verification/__init__.py` barrel already re-exported all four mandatory helpers (require_env, redact, safe_print, mutating_allowed) plus the optional schema_of/anonymize/Denylist/capture/findings from plans 01-01/01-04. No barrel edit was needed; the only barrel-related change was the lazy-import fix in mutation_gate.py (below).
- Left `main_ambito_financiero.py` untouched — the plan explicitly says add redaction only if output could be sensitive, and Ámbito returns a public FX float; adding `safe_print` with an empty secrets list would be a pure no-op and an unused import would fail ruff.
- `main_verify.py` chose subprocess-per-driver (RESEARCH Open Question 1 recommendation) for module-singleton isolation and to mirror the exact Phases 2-5 run command.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Made matriz_client import lazy in mutation_gate.py**
- **Found during:** Task 1 (finalizing the barrel + driver imports)
- **Issue:** `verification/mutation_gate.py` imported `matriz_client` at module level. The barrel `verification/__init__.py` eagerly imports `mutating_allowed`, so `from verification import require_env, redact, safe_print` triggered `import matriz_client`. But the drivers run via `uv run --package <pkg>`, and `matriz_client` is NOT installed in the iol/higyrus/wallets/ambito package environments — so the zero-config driver import (mandated by the plan) raised `ModuleNotFoundError: No module named 'matriz_client'` for every non-matriz driver.
- **Fix:** Moved `import matriz_client` from module scope into the body of `mutating_allowed()`, after the `VERIFY_MUTATING` flag check. The function still reads the live-resolved `matriz_client.client._base_url` at guard time (Pitfall 5 semantics preserved), and the import is only reached from `main_matriz.py` where the package is installed.
- **Files modified:** verification/mutation_gate.py
- **Verification:** `from verification import require_env, redact, safe_print, mutating_allowed` now succeeds from both the base env and the iol-client env; the 4 mutation_gate unit tests (test_harness_mutation_gate.py) still pass because `monkeypatch.setattr(matriz_client.client, "_base_url", ...)` mutates the cached module in `sys.modules`, which the lazy import re-reads.
- **Committed in:** bf8be07 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking import)
**Impact on plan:** The lazy-import fix was strictly necessary to satisfy the plan's mandated zero-config driver import — without it, four of five drivers could not import the harness at all. No behavior change to the mutation gate; no scope creep.

## Issues Encountered

- **mypy at repo root cannot resolve workspace package imports.** Running `uv run mypy main_iol.py ...` from the base env reports `import-not-found` for `iol_client`/`ambito_financiero_client`/etc., because the workspace packages are only installed in their own per-package uv envs (the drivers live at repo root, outside `[tool.mypy] files`). This is the exact situation the plan's verification note anticipates. Resolution: `mypy verification` passes clean (in-glob); `mypy main_verify.py conftest.py` passes clean (stdlib-only at root); and `uv run --package iol-client mypy main_iol.py` passes clean (proving the driver code itself is type-correct when its package is present). The drivers are therefore ruff-checked at root and mypy-checked within their package env — documented here per the plan's instruction.

## Verification Evidence

- `env -u IOL_USER -u IOL_PASSWORD uv run --package iol-client python main_iol.py` → prints `SKIPPED iol-client: missing IOL_USER, IOL_PASSWORD`, exit 0. ✓
- `env -u WALLETS_TOKEN -u WALLETS_BASE_URL uv run --package wallets-client python main_wallets.py` → `SKIPPED wallets-client: missing WALLETS_TOKEN, WALLETS_BASE_URL`, exit 0. ✓
- `main_iol.py` no longer contains `token[:12]`; contains `redact(`. ✓
- `main_matriz.py` contains `mutating_allowed(` guarding a mutation branch. ✓
- `main_ambito_financiero.py` contains no `require_env(`. ✓
- `verification.__all__` contains require_env, redact, safe_print, mutating_allowed; `from verification import require_env, redact, safe_print, mutating_allowed` succeeds from repo root. ✓
- `uv run python main_verify.py` → per-package RAN/SKIPPED summary for all five, exit 0, never halted (4 SKIPPED + 1 RAN in the cred-less worktree). ✓
- `main_verify.py` uses `subprocess` and prints per-package status only (no raw child stdout). ✓
- `uv run ruff check verification main_*.py conftest.py` → All checks passed. ✓
- `uv run mypy verification` → Success; `uv run mypy main_verify.py conftest.py` → Success. ✓
- `uv run --all-packages pytest -q` → 137 passed, 1 deselected (live example). ✓

## Next Phase Readiness

- The safety harness is now wired end-to-end into the live-exploration vehicle. Phases 2-5 can run `uv run --package <pkg> python main_<name>.py` (or `main_verify.py`) with the HARN-01/02/03 guarantees observable in driver output: creds gated, tokens redacted, Matriz mutations unreachable by default.
- No blockers introduced. Drivers are minimal smoke tests today — Phases 2-5 extend each to cover the full public surface, reusing the same gate/redaction wiring.

---
*Phase: 01-safety-harness-verification-infrastructure*
*Completed: 2026-05-28*
