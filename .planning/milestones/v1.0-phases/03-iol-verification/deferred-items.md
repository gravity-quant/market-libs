# Phase 3 IOL Verification — Deferred Items

Out-of-scope discoveries logged during execution. Not fixed by the plan owner.

## During Plan 03-01 execution

### 1. `uv run mypy .` (whole-repo) fails on `packages/higyrus-client/tests/conftest.py`

- **Discovered:** Plan 03-01 final verification (`uv run mypy .`)
- **Pre-existing:** YES — reproducible from `main` HEAD (`6978b27`); not caused by IOL-07 fix
- **Symptom:** mypy emits "duplicate module named ..." / "package conflict" for
  `packages/higyrus-client/tests/conftest.py`, blocking the whole-repo strict pass
- **Scope guard:** Out of scope for plan 03-01 (target: `packages/iol-client/*`).
  `uv run mypy packages/iol-client` is clean.
- **Action:** None taken in plan 03-01. Should be addressed in a separate config
  fix (likely needs `--explicit-package-bases` or `__init__.py` adjustment in
  higyrus-client tests) or in a higyrus-targeted plan in Phase 4.
- **Whole-repo gate impact:** The per-package mypy gate
  `uv run mypy packages/iol-client` (which IOL-07 actually requires) passes.
  The root-level `uv run mypy .` was a per-Wave-1-merge bonus suggested by the
  plan, not a per-plan acceptance criterion.
