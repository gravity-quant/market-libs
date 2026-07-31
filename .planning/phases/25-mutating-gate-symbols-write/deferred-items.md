# Deferred Items — Phase 25

Out-of-scope discoveries logged during execution (not fixed — pre-existing, unrelated to the mutation gate).

## Pre-existing mypy error in a test file

- **File:** `packages/market-data-client/tests/test_reference_core.py:208`
- **Error:** `Need type annotation for "body"  [var-annotated]`
- **Status:** Present on HEAD (57cb64e) BEFORE any Phase 25 work — confirmed via `git stash`.
- **Scope:** Test file, not `src/`. The pre-commit mypy hook only scans `^packages/.*/src/`, so it does NOT block commits. Full-suite `uv run mypy packages/market-data-client` reports it because tests are included.
- **Action:** Not fixed (out of scope per executor scope-boundary rule — not caused by the gate work).

## Pre-existing mypy errors in `test_mutation_gate.py` (noted during Plan 25-02)

- **File:** `packages/market-data-client/tests/test_mutation_gate.py` (8 errors, e.g. lines
  61, 70, 136, 150, 167, 175, 190, 200).
- **Error:** `"_ensure_mutation_allowed" of "Client"/"AsyncClient" does not return a value
  (it only ever returns None) [func-returns-value]` — assertions of the form
  `assert view._ensure_mutation_allowed() is None`.
- **Status:** Present from Plan 25-01 (test file committed in `43c4866`), untouched by
  Plan 25-02.
- **Scope:** Test file, not `src/`. Pre-commit mypy hook only scans `^packages/.*/src/`,
  so it does NOT block commits. Plan 25-02's own source (`models.py`, `_core.py`) is
  mypy-clean.
- **Action:** Not fixed (out of scope — belongs to Plan 25-01 test cleanup).
