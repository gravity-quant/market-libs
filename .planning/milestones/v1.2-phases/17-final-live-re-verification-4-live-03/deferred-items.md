# Phase 17 — Deferred Items (out-of-scope discoveries during 17-03 execution)

These items were discovered while running the CI gate set in Plan 17-03. They are
**pre-existing**, **out-of-CI-scope**, and **NOT v1.2 BLOCKERs**. Per the executor
SCOPE BOUNDARY they were logged, not fixed (this plan only modified
`.planning/REQUIREMENTS.md`).

## DEF-17-01 — `verification/test_matriz_sweep_snapshot.py` fails under pytest-httpx 0.36.2

- **Discovered during:** Plan 17-03, Task 2 (full-tree `uv run pytest -q`).
- **Symptom:** 19 failed + 19 errors, all confined to
  `verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved`.
  The teardown error is pytest-httpx's strict
  `_assert_options()`: *"The following responses are mocked but not requested:
  Match any request on https://api.test/..."*.
- **Root cause:** The locked dev dependency `pytest-httpx==0.36.2` (uv.lock) enforces
  *assert-all-responses-were-requested* by default at fixture teardown. The test
  registers `httpx_mock.add_response(...)` mocks that the probe under test does not
  consume, so teardown now fails. The test file is **unchanged since Phase 07
  (commit `9314e6e`)** — it predates this plan and predates v1.2 entirely; the file
  even carries an author comment about needing `assert_all_responses_were_requested=False`.
- **Why NOT a v1.2 BLOCKER / why out of scope:**
  - **CI never runs this file.** `.github/workflows/ci.yml` scopes the test job to
    `pytest packages/${matrix.package}` (per-package suites only). The top-level
    `verification/` directory is not in any CI test path. The operator-confirmed
    remote gate (CI matrix green 3.12/3.13) is therefore unaffected.
  - The CI-scoped suite is fully green here: `pytest packages/` → **754 passed, 1 deselected**.
  - It is a dev-tooling (test-fixture strictness) issue, not v1.2 product code.
  - The plan's machine-checkable Task 2 gate (`--collect-only ≥ 989` + `ruff check` +
    `mypy --strict`) all PASS; collection is 989/990.
- **Suggested fix (deferred, NOT applied here):** either add
  `assert_all_responses_were_requested=False` to the `httpx_mock` registration / marker
  in `test_matriz_sweep_snapshot.py`, or only register the single response the probe
  actually requests. This is a test-only change, isolated to one verification helper file.
- **Disposition:** Deferred — out-of-scope pre-existing test-fixture drift; tracked here
  for a future test-hardening quick-task. Does not gate v1.2 milestone close.
