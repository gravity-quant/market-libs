# Deferred Items — Phase 25

Out-of-scope discoveries logged during execution (not fixed — pre-existing, unrelated to the mutation gate).

## Pre-existing mypy error in a test file

- **File:** `packages/market-data-client/tests/test_reference_core.py:208`
- **Error:** `Need type annotation for "body"  [var-annotated]`
- **Status:** Present on HEAD (57cb64e) BEFORE any Phase 25 work — confirmed via `git stash`.
- **Scope:** Test file, not `src/`. The pre-commit mypy hook only scans `^packages/.*/src/`, so it does NOT block commits. Full-suite `uv run mypy packages/market-data-client` reports it because tests are included.
- **Action:** Not fixed (out of scope per executor scope-boundary rule — not caused by the gate work).
