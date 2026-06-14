---
phase: 09-deferred-bug-fixes
plan: 03
subsystem: matriz-client
tags: [phase-09, matriz, bug-fixes, cfi-validation, single-site, wave-2]
status: complete
requires: [09-01, 09-02]
provides:
  - F-09 CONFIRMED -> FIXED
  - cycle_closure_matriz_client FAIL -> PASS (live re-run confirmed by orchestrator from main)
  - 10 parametric regression cases covering CFI hybrid guard
affects:
  - matriz-client sync REST surface (Client.get_instruments_by_cfi)
tech-stack:
  added:
    - "stdlib re + typing.get_args (no new deps)"
  patterns:
    - "Pattern S5: compile-once regex + frozenset derived from Literal source-of-truth"
    - "Pattern S4: single-site fix in _core.py builder (Phase 7 REFAC-03)"
key-files:
  created: []
  modified:
    - packages/matriz-client/src/matriz_client/_core.py
    - packages/matriz-client/tests/test_core.py
    - packages/matriz-client/tests/test_client.py
    - .planning/verification/matriz-client-findings.md
decisions:
  - "D-01 hybrid Literal+regex guard locked: pre-HTTP validation in build_get_instruments_by_cfi_request"
  - "D-02 deviation vs ROADMAP: guard lives in builder, not in raise_for_response (which only sees httpx.Response)"
  - "D-03 live re-run operator-driven: Task 2 returns checkpoint to orchestrator"
metrics:
  tasks_completed: 3
  tasks_pending: 0
  test_delta: +10
  commits: 4
  completed: 2026-06-13
---

# Phase 9 Plan 03: matriz BUG-01 hybrid CFI guard (F-09 close) Summary

**One-liner:** Hybrid Literal + ISO 10962 regex guard pre-HTTP en
`build_get_instruments_by_cfi_request` cierra F-09 ERROR-MAP CFI inválido;
single-site fix propaga al transport shell sync; 10 parametric regression
cases cubren 3 buckets (literal-known, regex forward-compat, malformed); live
re-run operator-driven pendiente del orquestador.

## Status: PARTIAL — Checkpoint Pending

- **Task 1 (RED + GREEN):** DONE — commits `ab7c25c` (RED) + `208222a` (GREEN).
- **Task 2 (operator-driven live re-run):** CHECKPOINT PENDING — orchestrator
  owns the live `main_matriz.py` re-run from main checkout where Primary
  credentials live.
- **Task 3 (F-09 finding update):** DONE — commit `d7658e1`. Landed before Task 2
  so that `cycle_closure_matriz_client` detects F-09 as Open-with-Regression on
  the live re-run.

## Tasks Completed

### Task 1 — Hybrid CFI guard + parametric test (RED + GREEN)

**RED commit:** `ab7c25c` `test(09-03): add failing parametric test for CFI hybrid guard (BUG-01 RED)`

Added 10 parametric cases to `packages/matriz-client/tests/test_core.py`:

- Literal-known bucket: `ESXXXX`, `DBXXXX` → pass (no raise)
- Regex forward-compat bucket: `ABXXXX`, `ZQXXXX` → pass (no raise; not in
  Literal but matches `^[A-Z]{6}$`)
- Malformed bucket: `INVALID-CFI` (hyphen + len 11), `esxxxx` (lowercase),
  `E2XXXX` (digit), `ABCDE` (len 5), `ABCDEFG` (len 7), `""` (empty) →
  raise `PrimaryAPIError(status="ERROR")` with description containing
  "CFI inválido"

Pre-fix run: **6 failed (DID NOT RAISE PrimaryAPIError)** for malformed bucket,
4 passed for valid bucket. RED gate satisfied.

**GREEN commit:** `208222a` `fix(matriz): BUG-01 hybrid Literal+regex CFI validation + cycle_closure FAIL->PASS (BUG-01)`

#### Imports added to `_core.py`

```python
import re
from typing import Any, get_args  # get_args added to existing line
```

#### Module-level constants added to `_core.py`

```python
# Phase 9 BUG-01 (F-09) — hybrid CFI guard constants.
# Source of truth: ``matriz_client.types.CFICode`` (Literal, 9 valores).
# Pattern S5: compile-once regex + frozenset inmutable + hashable derivada del
# Literal via ``typing.get_args`` (Python 3.12+ garantiza orden de declaración).
_CFI_ISO_RE = re.compile(r"^[A-Z]{6}$")
_CFI_LITERAL_VALUES: frozenset[str] = frozenset(get_args(CFICode))
```

#### Builder body change

```python
if cfi_code not in _CFI_LITERAL_VALUES and not _CFI_ISO_RE.match(cfi_code):
    raise PrimaryAPIError(
        status="ERROR",
        description=(
            f"CFI inválido: {cfi_code!r} "
            "(no está en CFICode Literal ni matchea ^[A-Z]{6}$)"
        ),
        message=None,
    )
```

#### Test delta

- `tests/test_core.py`: **+10 parametric cases** in
  `test_get_instruments_by_cfi_validates_cfi_code`. Full file count goes from
  198 to **208 passed** (+10 net).
- `tests/test_client.py`: existing `test_get_instruments_by_cfi_raises_primary_api_error_on_malformed_cfi` updated to reflect new contract (rejection
  pre-HTTP). Pre-Phase-9 test mocked a server-side `{'status':'ERROR'}` response
  that F-09 documented never actually came back from the real server — with the
  Phase 9 fix the guard rejects before any wire call, so `httpx_mock` is no
  longer needed and the description check now matches "CFI inválido" from the
  local guard. This is **Rule 1 (auto-fix bug)**: the pre-Phase-9 test
  encoded the desired-but-never-observed server contract; post-fix it must
  encode the actually-implemented client-side contract.

#### Verification (Task 1 acceptance criteria)

| Check                                                                                  | Result |
| -------------------------------------------------------------------------------------- | ------ |
| `import re` present in `_core.py`                                                      | PASS   |
| `from typing import ... get_args` present                                              | PASS   |
| `_CFI_ISO_RE = re.compile(r"^[A-Z]{6}$")` present                                      | PASS   |
| `_CFI_LITERAL_VALUES = frozenset(get_args(CFICode))` present                           | PASS   |
| Guard raise with `CFI inválido` description present                                    | PASS   |
| Parser `parse_get_instruments_by_cfi_response` preserved (no change)                   | PASS   |
| Parametric test `test_get_instruments_by_cfi_validates_cfi_code` defined               | PASS   |
| 10/10 parametric cases pass                                                            | PASS   |
| Full matriz `tests/test_core.py` GREEN                                                 | PASS   |
| Full matriz suite GREEN (208 passed + 1 skipped)                                       | PASS   |
| `uv run ruff check ...` clean                                                          | PASS   |
| `uv run ruff format --check ...` clean                                                 | PASS   |
| `uv run mypy --strict packages/matriz-client/` clean                                   | PASS   |
| `uv run lint-imports` 4 contracts kept, 0 broken                                       | PASS   |
| Cross-leak sentinel `verification/test_sync_async_isolation.py` GREEN                  | PASS   |
| Public surface snapshot `test_public_surface_matches_snapshot[matriz_client]` zero-diff| PASS   |
| `aio.py` LOC unchanged (103)                                                           | PASS   |
| `_atransport.py` absent                                                                | PASS   |
| Full pytest workspace GREEN (776 passed + 3 skipped + 1 deselected in 147.11s)         | PASS   |

### Task 2 — Operator-driven live re-run (CHECKPOINT PENDING)

This task is `type="checkpoint:human-verify" gate="blocking"`. It requires:

1. `uv run --package matriz-client python main_matriz.py` to run against Primary
   sandbox with `MATRIZ_USER` / `MATRIZ_PASSWORD` (`PRIMARY_USER` / `PRIMARY_PASSWORD`) loaded
   from `packages/matriz-client/.env`.
2. Inspect the run log for:
   - `probe_error_malformed_cfi` → expected **PASS** post-fix with detail
     referencing `PrimaryAPIError(status="ERROR")` raised pre-HTTP.
   - `cycle_closure_matriz_client` → expected **PASS** post-Task-3 finding
     update (F-09 now has `Regression:` line linking to the parametric test).
3. Paste evidence (timestamp + 2 probe sections) into this SUMMARY.

The worktree does **not** carry `.env` files by design (#3097 isolation pattern;
credentials live only in main checkout). The orchestrator owns the live re-run
from main and will append the evidence here when complete. Until then, this
SUMMARY is **PARTIAL**.

#### Live re-run evidence (orchestrator-completed from main)

```text
Timestamp: 2026-06-13T~17:50:00Z
Log: /tmp/main_matriz_phase9_run.log
Exit: 0

$ grep -B1 -A4 "error_malformed_cfi" /tmp/main_matriz_phase9_run.log
PROBE error_invalid_account: PASS PrimaryAPIError as expected: You don't have access to account INVALID-ACCT-XXXXX
PROBE error_malformed_cfi:   PASS PrimaryAPIError as expected: CFI inválido: 'INVALID-CFI' (no está en CFICode Literal ni matchea ^[A-Z]{6}$)
PROBE schema_snapshot:       PASS 8 snapshots OK

$ grep -B1 -A4 "cycle_closure" /tmp/main_matriz_phase9_run.log
PROBE cycle_closure_ambito_financiero_client: PASS
PROBE cycle_closure_iol_client:              PASS
PROBE cycle_closure_higyrus_client:           PASS
PROBE cycle_closure_matriz_client:            PASS   ← FAIL → PASS post-Task 3 finding update

SUMMARY: PASS=18 FAIL=0 SKIPPED=9 FINDING=1
```

Both expected probes PASS:
- `probe_error_malformed_cfi` confirms the hybrid guard raises `PrimaryAPIError(status="ERROR")` pre-HTTP with the documented message `"CFI inválido: 'INVALID-CFI' (no está en CFICode Literal ni matchea ^[A-Z]{6}$)"`.
- `cycle_closure_matriz_client` flips FAIL → PASS because F-09 is now `FIXED` with `Regression:` line linking to `tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code`.

### Task 3 — F-09 finding update

**Commit:** `d7658e1` `docs(matriz): F-09 CONFIRMED -> FIXED + Resolution + Regression (BUG-01)`

Updated `.planning/verification/matriz-client-findings.md`:

#### F-09 detail section

- **Status:** `CONFIRMED` → `FIXED`
- **Actual** updated to `(pre-Phase 9)` marker
- **Resolution** added: full description of hybrid Literal+regex guard,
  source-of-truth derivation, D-02 deviation rationale, single-site fix
  propagation per Phase 7 REFAC-03, live re-run evidence reference
- **Regression** added: links to
  `packages/matriz-client/tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code`
  (10 parametric cases, 3 buckets)

#### Index table

- F-09 row: `CONFIRMED` → `FIXED`

#### Cycle Closure section

- Findings by status: CONFIRMED count 1 → 0, FIXED count 0 → 1
- Regression tests table: new row for F-09 added
- `verify_cycle_closure("matriz-client")` returned: **FAIL** → **PASS**
- Missing regressions: F-09 removed (now empty)

#### Run Context

- Timestamp annotation appended (2026-06-13 — Phase 9 Plan 09-03 update)

#### Task 3 acceptance criteria

| Check                                                                                                      | Result |
| ---------------------------------------------------------------------------------------------------------- | ------ |
| F-09 status line shows `FIXED`                                                                             | PASS   |
| `Resolution.*Phase 9 Plan 09-03 BUG-01` present (1 occurrence)                                             | PASS   |
| `Regression.*test_get_instruments_by_cfi_validates_cfi_code` present (1 occurrence)                        | PASS   |
| CONFIRMED count decrement reflected in Cycle Closure section                                               | PASS   |
| File parses as markdown OK (no encoding errors)                                                            | PASS   |

## Files modified

| File                                                            | Type            | Net delta                                                                                                                              |
| --------------------------------------------------------------- | --------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/matriz-client/src/matriz_client/_core.py`             | source          | +2 imports (re, get_args); +2 module-level constants; +9 lines in builder body (guard); +27 lines in builder docstring                  |
| `packages/matriz-client/tests/test_core.py`                     | test            | +55 lines (parametric test + section header)                                                                                            |
| `packages/matriz-client/tests/test_client.py`                   | test            | -3 lines / +12 lines (httpx_mock-dependent test rewritten as pre-HTTP-guard smoke test)                                                |
| `.planning/verification/matriz-client-findings.md`              | doc             | F-09 Status flip + Resolution + Regression + Cycle Closure section diff + Run Context note                                              |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-Phase-9 test in `test_client.py` encoded the wrong contract**

- **Found during:** Task 1 GREEN verification (full matriz suite run)
- **Issue:** `test_get_instruments_by_cfi_raises_primary_api_error_on_malformed_cfi`
  in `tests/test_client.py:772` mocked an HTTP response `{'status':'ERROR',
  'description':'malformed CFI code ...'}` and asserted `'malformed' in
  description`. F-09 documented that the real server NEVER returned that
  response — the cycle confirmed the client propagated malformed CFIs to the
  wire and returned cleanly. With the Phase 9 fix, the guard rejects pre-HTTP,
  the `httpx_mock` registered mock is never consumed, and pytest-httpx fails the
  teardown ("responses are mocked but not requested"); additionally the
  description no longer contains `'malformed'` because it now contains the
  local guard's "CFI inválido" message.
- **Fix:** Rewrote the test to drop `httpx_mock`, document the pre-Phase-9 vs
  post-Phase-9 contract delta in the docstring, and assert
  `'CFI inválido' in description`. The test now serves as the smoke
  contract-level check at the top-level `matriz_client.get_instruments_by_cfi`
  entry point (full bucket coverage stays in
  `tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code`).
- **Files modified:** `packages/matriz-client/tests/test_client.py`
- **Commit:** `208222a` (rolled into the GREEN commit since it is part of the
  same fix surface — the assertion message and removal of the unused mock are
  inseparable from the guard implementation)

**2. [Rule 1 - Style] Ruff RUF002 (ambiguous `×`) + PT006 (parametrize tuple)**

- **Found during:** Task 1 GREEN ruff sweep
- **Issue:** Initial docstring/comment text used `×` (Unicode multiplication
  sign) instead of ASCII `x`, triggering RUF002; the `@pytest.mark.parametrize`
  call passed a string `"cfi,expect_raise"` rather than the project-preferred
  tuple `("cfi", "expect_raise")` per PT006.
- **Fix:** Replaced `×` with `x` in 4 docstring/comment locations across
  `test_core.py` + `test_client.py`; converted parametrize first argument to a
  tuple.
- **Files modified:** `packages/matriz-client/tests/test_core.py`,
  `packages/matriz-client/tests/test_client.py`
- **Commit:** `208222a` (rolled into GREEN)

### Architectural Changes

None — Rule 4 not triggered.

## Authentication Gates

None encountered. Task 2 is an operator-driven live re-run that the
orchestrator handles from main where credentials are present. From the
worktree, no live network calls were attempted.

## Phase-level invariants preserved

| Invariant                                                                       | Pre  | Post | Notes                                          |
| ------------------------------------------------------------------------------- | ---- | ---- | ---------------------------------------------- |
| matriz `aio.py` LOC (Phase 8 D-25)                                              | 103  | 103  | preserved; this plan does not touch async surface |
| matriz `_atransport.py` (Phase 8 D-25)                                          | absent | absent | preserved                                    |
| Import-linter contracts                                                         | 4 kept | 4 kept | `_core.py` still does not depend on transport |
| Cross-leak sentinel `test_sync_async_isolation`                                 | GREEN | GREEN | unchanged                                      |
| Public surface snapshot `test_public_surface_matches_snapshot[matriz_client]`   | GREEN | GREEN | zero-diff                                      |
| Mypy strict on matriz-client                                                    | GREEN | GREEN | clean                                          |
| Full pytest workspace                                                           | 765 passed (pre-09-03) | 776 passed (+10 parametric + 1 wallets unrelated tick) | +10 net regression cases from Task 1; full sweep 776 passed + 3 skipped + 1 deselected in 147.11s |

## Self-Check: PASSED

Verified existence of all artifacts and commits:

- File `packages/matriz-client/src/matriz_client/_core.py`: FOUND (modified)
- File `packages/matriz-client/tests/test_core.py`: FOUND (extended)
- File `packages/matriz-client/tests/test_client.py`: FOUND (modified per Rule 1)
- File `.planning/verification/matriz-client-findings.md`: FOUND (F-09 updated)
- Commit `ab7c25c` (RED): FOUND (`git log --oneline | grep ab7c25c`)
- Commit `208222a` (GREEN): FOUND
- Commit `d7658e1` (Task 3 finding update): FOUND
- Module-level constants `_CFI_ISO_RE` and `_CFI_LITERAL_VALUES`: FOUND in
  `_core.py` (greps return 1 / 3)
- Test `test_get_instruments_by_cfi_validates_cfi_code`: FOUND in
  `tests/test_core.py` (10 parametric cases collected by pytest)
- F-09 Status `FIXED`, Resolution line, Regression line: all FOUND in
  `matriz-client-findings.md`

## TDD Gate Compliance

| Gate     | Commit  | Status |
| -------- | ------- | ------ |
| RED      | `ab7c25c` | `test(...)` — RED commit verified failing 6/10 (DID NOT RAISE) before GREEN |
| GREEN    | `208222a` | `fix(...)` — GREEN commit makes all 10/10 pass |
| REFACTOR | (n/a)     | No separate refactor needed — guard is minimal |

## Orchestrator Action Required (Task 2 closure)

1. From main checkout (where `packages/matriz-client/.env` carries
   `PRIMARY_USER`/`PRIMARY_PASSWORD`):
   ```bash
   uv run --package matriz-client python main_matriz.py 2>&1 | tee /tmp/main_matriz_phase9_run.log
   grep -A 3 "error_malformed_cfi" /tmp/main_matriz_phase9_run.log
   grep -A 5 "cycle_closure" /tmp/main_matriz_phase9_run.log
   ```
2. Confirm `probe_error_malformed_cfi` reports PASS and
   `cycle_closure_matriz_client` reports PASS.
3. Append the 2 grep outputs (timestamp included) to the "Live re-run evidence
   (orchestrator to fill)" block above.
4. Flip this SUMMARY's frontmatter `status` from `partial-checkpoint` to
   `complete` and remove the `checkpoint_pending` block.
5. Commit the SUMMARY edit (the orchestrator's normal post-wave metadata
   commit on main).

If the live re-run surfaces:
- `probe_error_malformed_cfi UNEXPECTED outcome` → investigate; the guard
  may not be reaching the wire path correctly (revisit Task 1).
- `cycle_closure still FAIL` after Task 3 → check that the finding `Regression:`
  line is exactly parseable by the cycle closure probe (string match on test
  path).
- `rate-limit hit (HTTP 429)` → respect the cooldown documented in Primary
  support docs and retry.
