# Deferred items — Phase 31

Out-of-scope discoveries logged during execution. Per the executor scope boundary,
these are **not** fixed here: none is caused by this phase's changes, and each was
confirmed pre-existing at the commit the work started from.

## D-1 — `verification/` matriz probes drifted from `main_matriz.py` (19 failed + 19 errors)

**Found during:** plan 31-02, Task 2 full-suite run (`uv run pytest -q`).

**Symptom:**

```
TypeError: probe_login_sync() missing 1 required positional argument: 'client'
AssertionError: The following responses are mocked but not requested:
  - Match POST request on https://api.test/auth/getToken
```

**Files:** `verification/test_main_matriz_login_fail_uniformity.py`,
`verification/test_matriz_sweep_snapshot.py`.

**Cause:** `main_matriz.py`'s probe functions took a `client` parameter in
`1fbc83f refactor(15-05): route matriz sync sweep probes through threaded Client`;
the two verification suites still call them with the pre-15-05 signature. The mocked
`getToken` response then goes unrequested and `pytest_httpx` fails at teardown.

**Pre-existing:** yes. Plan 31-02 adds no file to `matriz-client` and touches nothing
on the matriz path. Confirmed by `git status --short`.

**Not caught by CI:** `verification/` has never executed in CI — the `test` job passes
an explicit `packages/${{ matrix.package }}` path that overrides `testpaths`. This is the
same fact that put `tools/check_uniform_structure.py` in the `lint` job (D-12) and is
recorded in `ci.yml`'s own inline comment.

**Owner:** the phase that reconciles the `verification/` harness with the v1.2 driver
signatures. Not TYP-02 and not TYP-03.

## D-2 — two `mypy --strict` errors in `packages/ambito-financiero-client/tests/test_decode.py`

**Found during:** plan 31-02, Task 2 (`uv run mypy packages/ambito-financiero-client/tests`).

**Symptom:**

```
test_decode.py:771: error: Function does not return a value (it only ever returns None)  [func-returns-value]
test_decode.py:840: error: Unused "type: ignore" comment  [unused-ignore]
```

(line numbers at HEAD; +28 after plan 31-02's edit to the same file)

**Pre-existing:** yes — verified directly by restoring the pristine `HEAD` copy of the
file, re-running `uv run mypy packages/ambito-financiero-client/tests`, and observing the
identical two errors at lines 771 and 840, then restoring the working copy.

**Note:** the `typecheck` CI job DOES run `mypy packages/<pkg>/tests` for this package,
so this is a live red step on `milestone/v1.5-mutations` independent of this phase.

**Owner:** whichever plan next touches that suite's `SILENT_SINK` assertion and its
`dataclasses.fields` comprehension. Fixing it inside 31-02 would have coupled a
layout-uniformity plan to an unrelated typing repair.
