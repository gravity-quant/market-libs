---
phase: 01-safety-harness-verification-infrastructure
plan: 02
subsystem: testing
tags: [safety-gate, env-gate, mutation-guard, harness, verification, pytest]

# Dependency graph
requires: []
provides:
  - "verification/env_gate.py — require_env() credential gate emitting verbatim 'SKIPPED <pkg>: missing X, Y' (HARN-01/D-15)"
  - "verification/mutation_gate.py — mutating_allowed() double-gate (VERIFY_MUTATING=1 AND live remarkets base URL) (HARN-02/D-16)"
  - "root conftest.py making the verification/ tooling package importable under pytest --import-mode=importlib"
affects: [02-ambito, 03-iol, 04-higyrus, 05-matriz, live-verification-drivers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Top-level verification/ package for cross-package harness tooling (stdlib-only, no inter-package deps)"
    - "Read-only live module-state gating: guard reads matriz_client.client._base_url at call time, never a hardcoded constant"

key-files:
  created:
    - verification/env_gate.py
    - verification/mutation_gate.py
    - verification/__init__.py
    - conftest.py
    - packages/ambito-financiero-client/tests/test_harness_env_gate.py
    - packages/ambito-financiero-client/tests/test_harness_mutation_gate.py
  modified: []

key-decisions:
  - "Added root conftest.py inserting rootdir into sys.path so the top-level verification/ package is importable under pytest's importlib mode (it is not on the package path)"
  - "Reworded module docstrings to avoid the literal tokens 'raise'/'sys.exit' and a second 'matriz_client.client._base_url' occurrence so the plan's verbatim source-grep acceptance criteria hold exactly"

patterns-established:
  - "Harness safety gate: verbatim SKIPPED line + bool return, never raises/exits — caller owns clean exit"
  - "Mutation double-gate reads resolved module state live to catch configure(base_url=prod) overrides"

requirements-completed: [HARN-01, HARN-02]

# Metrics
duration: ~21min
completed: 2026-05-27
---

# Phase 01 Plan 02: Safety Gates (require_env + mutating_allowed) Summary

**Two stdlib-only hard safety gates — a credential `require_env` emitting the verbatim `SKIPPED <pkg>: missing X, Y` line, and a `mutating_allowed` double-gate (`VERIFY_MUTATING=1` AND a live-resolved `remarkets` base URL) that fails safe even against a prod-URL bypass — each TDD-proven.**

## Performance

- **Duration:** ~21 min
- **Started:** 2026-05-27T23:31Z
- **Completed:** 2026-05-27T23:52Z
- **Tasks:** 2 (both TDD: RED → GREEN)
- **Files created:** 6

## Accomplishments
- `require_env(pkg, names)` (HARN-01/D-15): returns `True` silently when all vars present, else prints the verbatim `SKIPPED <pkg>: missing X, Y` line (comma-space join, in order) and returns `False` — never raises, never exits, so the aggregate runner continues.
- `mutating_allowed()` (HARN-02/D-16): enforces both `VERIFY_MUTATING == "1"` AND `"remarkets" in matriz_client.client._base_url`, reading the resolved module state live at guard time. The adversarial "flag on + prod URL" path is unit-proven to fail safe with the verbatim `SKIPPED (mutating, guard off)` line.
- 8 harness unit tests (4 per gate) covering missing/partial/present, flag-off/on, non-"1" values, and the prod-bypass attempt — all green.
- ruff (E/W/F/I/B/UP/SIM/RUF/ASYNC/PIE/PT/RET/TID) and mypy strict both clean on `verification/`.

## Task Commits

Each task was executed TDD-style and committed atomically:

1. **Task 1 (RED): require_env failing test + test infra** - `6b04e7d` (test)
2. **Task 1 (GREEN): require_env implementation** - `6f0aa77` (feat)
3. **Task 2 (RED): mutating_allowed failing test** - `40bc8d2` (test)
4. **Task 2 (GREEN): mutating_allowed implementation** - `9d4107b` (feat)
5. **Lint fix: sort harness test imports (ruff I001)** - `18e3c96` (style)

_TDD gate sequence satisfied for both tasks: a `test(...)` commit precedes each `feat(...)` commit._

## Files Created/Modified
- `verification/env_gate.py` - `require_env()` credential gate (HARN-01/D-15), stdlib-only, Spanish docstring, `__all__ = ["require_env"]`.
- `verification/mutation_gate.py` - `mutating_allowed()` double-gate (HARN-02/D-16); reads `matriz_client.client._base_url` live; `__all__ = ["mutating_allowed"]`.
- `verification/__init__.py` - package marker for the top-level harness tooling package.
- `conftest.py` (repo root) - inserts rootdir into `sys.path` so `verification/` is importable under pytest's `--import-mode=importlib` (rootdir is not otherwise on the path).
- `packages/ambito-financiero-client/tests/test_harness_env_gate.py` - 4 tests: all-missing, partial-missing, all-present, no-raise contract.
- `packages/ambito-financiero-client/tests/test_harness_mutation_gate.py` - 4 tests: flag-off, flag-on+remarkets, adversarial flag-on+prod, non-"1" value.

## Decisions Made
- **Root `conftest.py` for import resolution.** Verified empirically that `from verification.env_gate import require_env` fails under pytest's importlib mode because the repo root is not on `sys.path`. A root `conftest.py` that inserts the rootdir is the standard, least-invasive pytest idiom; it keeps the plan's intended import style (`from verification.* import ...`) without polluting individual test files. (Rule 3 — blocking issue.)
- **Docstring wording to satisfy verbatim source-greps.** The plan's acceptance criteria use literal greps — `grep -cE 'raise|sys\.exit' env_gate.py` must be 0, and `grep -c 'matriz_client.client._base_url' mutation_gate.py` must be 1. Illustrative usage in the docstrings originally tripped both counts. Reworded the docstrings (describing clean-exit behaviour and the resolved-state read without the literal tokens) so the executable code is the only match — behaviour unchanged.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added root `conftest.py` + workspace sync for test import resolution**
- **Found during:** Task 1 (RED, before writing implementation)
- **Issue:** (a) The worktree `.venv` had no workspace packages installed, so `import matriz_client` failed; (b) the top-level `verification/` package was not importable under pytest's `--import-mode=importlib` because rootdir is not on `sys.path` — every harness test would `ModuleNotFoundError` at collection.
- **Fix:** (a) Ran `uv sync --all-packages --all-extras --dev --frozen` to install the already-declared workspace members (no new/unknown packages — exempt from the package-install checkpoint). (b) Added a root `conftest.py` that inserts the rootdir into `sys.path`, plus `verification/__init__.py` as the package marker.
- **Files modified:** conftest.py, verification/__init__.py (committed with the Task 1 RED commit)
- **Verification:** A throwaway probe test confirmed the import resolved; both harness suites collect and pass.
- **Committed in:** `6b04e7d` (Task 1 RED commit)

**2. [Rule 1 - Bug/Lint] Sorted harness test imports per ruff isort (I001)**
- **Found during:** Final plan verification
- **Issue:** ruff `I001` flagged the import blocks in both new test files (ruff classifies `verification.*` as first-party and regroups the import blocks).
- **Fix:** Applied `ruff check --fix`; tests re-run green afterward.
- **Files modified:** packages/ambito-financiero-client/tests/test_harness_env_gate.py, packages/ambito-financiero-client/tests/test_harness_mutation_gate.py
- **Verification:** `ruff check verification <tests>` → All checks passed; 8 tests pass.
- **Committed in:** `18e3c96`

---

**Total deviations:** 2 auto-fixed (1 blocking infra, 1 lint). The two docstring rewordings are documented under "Decisions Made" (they keep behaviour identical while satisfying the plan's verbatim source-grep criteria).
**Impact on plan:** Both auto-fixes were necessary to make the plan's own tests runnable and CI-clean. No scope creep — the gate implementations match the VERIFIED RESEARCH bodies exactly.

## Issues Encountered
- Initial `uv run python -c "import matriz_client"` failed with `ModuleNotFoundError` in the fresh worktree venv; resolved by `uv sync --all-packages`. After sync, `matriz_client.client._base_url` resolved to the `https://api.remarkets.primary.com.ar` default as expected.

## Verification Evidence
- `uv run pytest packages/ambito-financiero-client/tests/test_harness_env_gate.py packages/ambito-financiero-client/tests/test_harness_mutation_gate.py -q` → 8 passed.
- `uv run ruff check verification` → All checks passed.
- `uv run mypy verification` → Success: no issues found in 3 source files.
- Full ambito package suite (`uv run pytest packages/ambito-financiero-client/tests/ -q`) → 16 passed (no regressions).
- Source asserts: `env_gate.py` contains the verbatim f-string and 0 `raise|sys.exit` matches; `mutation_gate.py` reads `matriz_client.client._base_url` exactly once with no hardcoded base-URL constant.

## Threat Model Compliance
- T-01-05 / T-01-06 (Tampering/Elevation, prod misconfig): mitigated — double gate + live base-URL read, adversarial prod-URL test proves fail-safe.
- T-01-07 (Reliability/fail-safe): mitigated — `require_env` returns a bool, never raises/exits.
- T-01-08 (Info disclosure): accepted — `_base_url` read for gating only, never echoed.
- T-01-SC (supply chain): respected — no package installs (only an already-declared workspace sync).
No new security surface introduced beyond the plan's threat model.

## Next Phase Readiness
- Both hard safety gates exist and are proven; the later client-verification phases (Ámbito → IOL → Higyrus → Matriz) can wire `require_env` into each `main_*.py` driver and gate Matriz's mutating surface behind `mutating_allowed()` before any live API call.
- Note for downstream drivers: the gate functions live in the top-level `verification/` package, importable thanks to the new root `conftest.py` under pytest and via rootdir on `sys.path` for the `main_*.py` scripts run from repo root.

## Self-Check: PASSED

All created files verified on disk (env_gate.py, mutation_gate.py, __init__.py, conftest.py, both harness test files, this SUMMARY) and all task commits verified in git log (6b04e7d, 6f0aa77, 40bc8d2, 9d4107b, 18e3c96, 936d6ff).

---
*Phase: 01-safety-harness-verification-infrastructure*
*Completed: 2026-05-27*
