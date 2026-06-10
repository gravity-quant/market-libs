---
phase: 01-safety-harness-verification-infrastructure
plan: 01
subsystem: testing
tags: [pytest, redaction, conftest, live-marker, harness, mypy-strict, ruff]

# Dependency graph
requires: []
provides:
  - "Root conftest.py: --live flag + live marker registration + deselect-by-default collection hook (HARN-04)"
  - "verification/ importable non-published repo-root package (no pyproject, not a workspace member)"
  - "verification/redaction.py: redact() + safe_print() defense-in-depth credential masking (HARN-03)"
  - "Trivial @pytest.mark.live example test, copyable template for Phases 2-5 live tests"
  - "Repo-root sys.path bootstrap in conftest so verification/ imports under --import-mode=importlib"
affects: [02-iol, 03-driver-wiring, 04-higyrus, 05-matriz, ambito, live-verification, capture, anonymize, schema]

# Tech tracking
tech-stack:
  added: []  # stdlib + already-present pytest only; uv.lock unchanged
  patterns:
    - "Repo-root conftest.py owns the live/offline collection split (package conftests keep only autouse fixtures)"
    - "verification/ as a plain repo-root dir imported via sys.path (never installed/built)"
    - "Defense-in-depth redaction: redact() at the print site (layer 1) + safe_print() structural masking (layer 2)"
    - "noqa: RUF001 on the intentional non-ASCII '‹REDACTED›' marker literal"

key-files:
  created:
    - conftest.py
    - verification/__init__.py
    - verification/redaction.py
    - packages/ambito-financiero-client/tests/test_harness_live_probe.py
    - packages/ambito-financiero-client/tests/test_harness_redaction.py
  modified: []

key-decisions:
  - "Added repo root to sys.path inside conftest.py — --import-mode=importlib does not auto-add rootdir, so verification/ was not importable from tests (Rule 3 blocking fix)"
  - "Kept the exact '‹REDACTED›' marker literal required by the plan and suppressed RUF001 inline rather than swapping to ASCII"
  - "Committed each TDD task as a single feat slice (conftest+test interdependent; redaction module+test interdependent)"

patterns-established:
  - "Live/offline test split: @pytest.mark.live + --live deselect hook at the repo root, --strict-markers-clean"
  - "Credential masking: redact(value, keep=4) returns prefix+ellipsis; safe_print(text, secrets) masks known secrets >= 4 chars with a len(secret) >= 4 guard"

requirements-completed: [HARN-03, HARN-04]

# Metrics
duration: 4min
completed: 2026-05-27
---

# Phase 01 Plan 01: Offline-Clean Test Foundation Summary

**Root conftest live/offline split (`--live` deselect-by-default), the importable non-published `verification/` package, and defense-in-depth `redact`/`safe_print` credential masking — all unit-proven including the empty-secret corruption guard.**

## Performance

- **Duration:** 4 min (231 s)
- **Started:** 2026-05-27T23:47:52Z
- **Completed:** 2026-05-27T23:51:43Z
- **Tasks:** 2
- **Files modified:** 5 (all created)

## Accomplishments
- HARN-04: `@pytest.mark.live` registered in the root `conftest.py` with a `--live` flag; live tests deselected by default (`uv run pytest` → `1 deselected`), selected under `--live` (`uv run pytest --live` → live example passes). CI stays fully offline and deterministic.
- HARN-03: `redact()` returns only a 4-char prefix + ellipsis (full value structurally unreachable); `safe_print()` masks any known credential ≥4 chars anywhere in the output, with the mandatory `len(secret) >= 4` guard against the `str.replace("", marker)` corruption bug (concourse #4656).
- `verification/` established as an importable, non-published repo-root package — no `pyproject.toml`, not a uv workspace member, `uv.lock` unchanged (no new deps).
- Trivial `@pytest.mark.live` example test delivered as the copyable template for the real live tests in Phases 2-5.
- Full suite green: `120 passed, 1 deselected` offline; `121 passed` with `--live`. ruff + mypy strict clean on the out-of-glob tooling (`verification main_*.py conftest.py`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Root conftest.py — live marker + --live flag + verification package** - `5e9d786` (feat)
2. **Task 2: verification/redaction.py — redact() + safe_print() with empty-secret guard** - `b4a1af4` (feat)

_Note: Both tasks are TDD. Each was committed as a single feat slice because the test and its implementation are interdependent (the live probe is meaningless without the registering conftest; the redaction tests cannot import a non-existent module). RED was demonstrated before GREEN for both (see Issues Encountered)._

## Files Created/Modified
- `conftest.py` - Repo-root pytest hooks: `pytest_addoption` (--live), `pytest_configure` (live marker), `pytest_collection_modifyitems` (deselect-by-default); also bootstraps repo root onto `sys.path` for `verification/` imports under importlib mode.
- `verification/__init__.py` - Minimal package marker for the non-published repo-root verification tooling (Spanish docstring, no re-exports, no pyproject).
- `verification/redaction.py` - `redact()` and `safe_print()` (HARN-03/D-13), stdlib-only, `__all__` declared.
- `packages/ambito-financiero-client/tests/test_harness_live_probe.py` - The trivial network-free `@pytest.mark.live` example test (Phases 2-5 template).
- `packages/ambito-financiero-client/tests/test_harness_redaction.py` - 6 unit tests for redact/safe_print incl. the empty/short-secret guard via `capsys`.

## Decisions Made
- **sys.path bootstrap in conftest:** `--import-mode=importlib` (set in `pyproject.toml`) does not add the rootdir to `sys.path`, so `from verification.redaction import ...` failed at collection. The root `conftest.py` (which lives at the repo root) now inserts its own directory onto `sys.path`. This keeps `verification/` a plain directory — no pyproject, no workspace membership (Pitfall 1 avoided), `uv.lock` untouched.
- **Kept the exact `‹REDACTED›` marker:** the plan's acceptance criteria assert the literal output `x ‹REDACTED› y\n`. Rather than swap to ASCII, suppressed RUF001 inline with `# noqa: RUF001` plus an explanatory comment (the non-ASCII guillemets are deliberate — they will not collide with `<`/`>` appearing in real payloads).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] verification/ not importable under --import-mode=importlib**
- **Found during:** Task 2 (redaction tests)
- **Issue:** RESEARCH claimed `verification` is on `sys.path` during pytest, but with `--import-mode=importlib` pytest does NOT add the rootdir to `sys.path`. Both single-file and full-suite runs failed at collection with `ModuleNotFoundError: No module named 'verification'`.
- **Fix:** Added a `sys.path.insert(0, repo_root)` bootstrap at the top of the root `conftest.py` (the conftest's own directory is the repo root). No pyproject/workspace change — `verification/` stays a plain dir.
- **Files modified:** conftest.py
- **Verification:** `uv run pytest` → `120 passed, 1 deselected`; redaction tests `6 passed`; `verification` import resolves in-suite.
- **Committed in:** `b4a1af4` (Task 2 commit)

**2. [Rule 3 - Blocking] RUF001 ambiguous-Unicode error on the intentional '‹REDACTED›' marker**
- **Found during:** Task 2 (ruff strict gate)
- **Issue:** ruff RUF001 flagged the guillemets in `‹REDACTED›` as ambiguous Unicode (6 occurrences across redaction.py + test). The project's CI runs ruff strict, so this blocks. The plan requires the exact literal in its acceptance criteria.
- **Fix:** Added `# noqa: RUF001` on the three lines carrying the literal, with a comment documenting the deliberate non-ASCII choice. Also let ruff `--fix` sort the test's import block (I001).
- **Files modified:** verification/redaction.py, packages/ambito-financiero-client/tests/test_harness_redaction.py
- **Verification:** `uv run ruff check verification main_*.py conftest.py` → All checks passed.
- **Committed in:** `b4a1af4` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking).
**Impact on plan:** Both fixes were strictly necessary to make the planned code importable under the existing pytest config and to pass the existing CI gates. No scope creep — no behavior added beyond the plan; the `verification/` package remains a plain, non-published directory and `uv.lock` is unchanged.

## Issues Encountered
- **RED demonstrated for both TDD tasks before GREEN:** Task 1 RED — the live probe ran with a `PytestUnknownMarkWarning` and was NOT deselected (opposite of desired) before the conftest existed. Task 2 RED — the redaction tests failed collection with `ModuleNotFoundError` before `redaction.py` existed. GREEN reached after implementing each.
- **Workspace not synced initially:** the worktree's fresh `.venv` had no packages; `uv sync --all-packages --all-extras --dev --frozen` installed them (no lockfile change).

## User Setup Required
None - no external service configuration required. This plan is stdlib + already-present pytest only; no credentials, no live network.

## Next Phase Readiness
- The `--live`/offline split and the `@pytest.mark.live` template are ready for Phases 2-5 to author real live tests.
- `verification/` is ready to receive its further harness submodules (env_gate, mutation_gate, findings, capture, anonymize, schema); the barrel/re-exports are deferred to plan 03 (driver wiring) per the plan.
- `redact`/`safe_print` are ready to be wired into the `main_*.py` driver print sites.

## Self-Check: PASSED

All created files verified present on disk; both task commits verified in git log (see below).

---
*Phase: 01-safety-harness-verification-infrastructure*
*Completed: 2026-05-27*
