---
phase: 32-gates-de-homogeneidad-d-16
plan: 01
subsystem: testing
tags: [mypy, strict-typing, ci, pytest, decode, logrecord, ruff]

# Dependency graph
requires:
  - phase: 29-decoder-observable
    provides: "The observable decoder (`_decode.py` × 5) and its per-package `test_decode.py` suites — the 33 mypy errors repaired here all live in those Phase 29 test files"
  - phase: 31-endpoints-de-ops-estructura-uniforme
    provides: "deferred-items.md D-2/D-3, which logged the higyrus + ambito errors as debt needing a five-copy repair plan before v1.6 ships"
provides:
  - "A CI-green baseline: all four `ci.yml` jobs (lint, pre-commit, typecheck, test) pass locally for the first time since 2026-08-18"
  - "The `typecheck` job's per-package mypy loop green for all six packages, reproduced with the exact one-package-per-invocation shape ci.yml:92-99 uses"
  - "Closure of Phase 31 deferred-items D-2 and D-3"
  - "A truthful CI signal for Waves 1-3 of Phase 32 to verify against"
affects: [32-02, 32-03, 32-04, 32-05, 32-06, phase-33-live-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Narrow per-line `# type: ignore[attr-defined]` for custom LogRecord attribute reads (the iol-client shape, now uniform across all four decode suites)"
    - "`object`-typed intermediate to express a deliberate declaration-vs-runtime divergence without a cast or an ignore"
    - "`typing.get_args(alias)` instead of `alias.__args__` for Literal alias introspection under strict mode"

key-files:
  created:
    - ".planning/phases/32-gates-de-homogeneidad-d-16/32-01-SUMMARY.md"
  modified:
    - "packages/matriz-client/tests/test_decode.py"
    - "packages/matriz-client/tests/test_ws_decode_mode.py"
    - "packages/higyrus-client/tests/test_decode.py"
    - "packages/ambito-financiero-client/tests/test_decode.py"

key-decisions:
  - "32-01: the 6 matriz `comparison-overlap` errors were fixed by widening the read to an `object`-typed intermediate, NOT by re-asserting against a substituted typed zero — matriz's `scalar_passthrough=True` means the returned value is deliberately the raw wire value, so asserting a typed zero would have inverted the property under test"
  - "32-01: RESEARCH.md assumption A1 CONFIRMED by execution — all 33 errors were fixable in test code alone; `pyproject.toml` is byte-unchanged and no strictness knob was relaxed"
  - "32-01: GATE-TYP-01 deliberately NOT marked complete — all six plans of Phase 32 carry that requirement ID and this plan delivers none of its stated scope; closing it at plan 1 of 6 would be a false completion"

patterns-established:
  - "Custom-LogRecord assertions: one narrow bracketed ignore per offending line; where the attribute name is a variable, `getattr(record, name)` instead of an ignore"
  - "Silent-sink invocation is a bare call statement, never `assert sink(...) is None` — the sink is annotated `-> None`, so the assertion is statically meaningless under strict mode"
  - "A dead `# type: ignore` is deleted, never neutralised by turning `warn_unused_ignores` off — the self-invalidation is the feature"

requirements-completed: []

# Metrics
duration: 9min
completed: 2026-08-25
status: complete
---

# Phase 32 Plan 01: Wave 0 — CI-green baseline Summary

**33 pre-existing strict-mypy errors repaired inside four Phase-29 decode test suites, turning the `typecheck` job green for the first time since 2026-08-18 with zero config changes and zero test removals — 1682 tests still passing.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-08-25T20:54:57Z
- **Completed:** 2026-08-25T21:04:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- **Task 1** — repaired all 29 mypy errors in `matriz-client`'s decode suites (28 in `test_decode.py`, 1 in `test_ws_decode_mode.py`). The live re-enumeration matched RESEARCH.md's measured breakdown exactly: 20 `attr-defined`, 6 `comparison-overlap`, 3 `arg-type`.
- **Task 2** — repaired the 4 errors in `higyrus-client` and `ambito-financiero-client`, closing Phase 31 `deferred-items.md` D-2 and D-3 (logged as "needs a five-copy repair plan before v1.6 ships").
- **Task 3** — reproduced every `ci.yml` job locally; all green, including the `pre-commit` job and a Python 3.13 smoke leg.
- The `typecheck` job's per-package loop now prints `Success: no issues found` six times. Success criterion 5 of Phase 32 ("la matriz completa de CI queda verde") is no longer blocked before it starts.

## Task Commits

Each task was committed atomically:

1. **Task 1: Repair the 29 mypy errors in matriz-client's Phase-29 decode tests** — `5ce4e87` (fix)
2. **Task 2: Repair the 4 mypy errors in higyrus-client and ambito-financiero-client decode tests** — `f08b7f2` (fix)
3. **Task 3: Reproduce every ci.yml job locally and record the green baseline** — no code commit by design; the task's own action reads *"Do not modify any file in this task"*, and `git status --porcelain -- packages/ pyproject.toml tools/ .github/` returned 0 lines after it ran. Its deliverable is the **CI-green baseline** section below, which ships in the plan-metadata commit.

## CI-green baseline (Wave 0 close)

> **Scope disclosure (required by Task 3):** this wave repaired **pre-existing Phase-29 debt discovered by Phase 32 research and not part of GATE-TYP-01's stated scope** — it is recorded here so the phase's scope history stays honest and does not read as silent scope expansion.

All commands run at `f08b7f2`, on CPython 3.12.13 via the workspace `.venv`.

### `lint` job

| # | Command | Exit | Headline output |
|---|---------|------|-----------------|
| 1 | `uv lock --check` | 0 | `Resolved 48 packages in 2ms` |
| 2 | `uv run ruff check .` | 0 | `All checks passed!` |
| 3 | `uv run ruff format --check .` | 0 | `231 files already formatted` |
| 4 | `uv run lint-imports` | 0 | `Analyzed 69 files, 141 dependencies.` / `Contracts: 5 kept, 0 broken.` |
| 5 | `lint-logging` grep (`ci.yml:47` verbatim) | 0 | no matches — `logging.basicConfig(` / `logging.root.\w` absent from `packages/*/src/` |
| 6 | `uv run python tools/check_decode_intactness.py` | 0 | Checks A-D green; 5 copies reduce to digest `ac14868282ad0a5c` (**unchanged** across this plan); filter region hash `684191c7cdc5ff9c` |
| 7 | `uv run python tools/check_uniform_structure.py` | 0 | `all 6 packages under packages/ carry models.py, types.py` |

### `pre-commit` job

| Command | Exit | Headline output |
|---------|------|-----------------|
| `uv run pre-commit run --all-files --show-diff-on-failure` | 0 | 9/9 hooks **Passed** (trailing-whitespace, end-of-file, check-yaml, check-toml, large-files, merge-conflicts, ruff, ruff-format, mypy). No hook rewrote a file. |

### `typecheck` job

| Command | Exit | Headline output |
|---------|------|-----------------|
| `uv run mypy` (src global) | 0 | `Success: no issues found in **62 source files**` — the expected count; the market-data `files` enrollment is Plan 32-05's job, not this one |

Per-package loop, **one package per invocation** under `set -e` semantics, in `ci.yml:95` order:

| # | Command | Exit | Headline output |
|---|---------|------|-----------------|
| 1 | `uv run mypy packages/higyrus-client/tests` | 0 | `Success: no issues found in 11 source files` |
| 2 | `uv run mypy packages/wallets-client/tests` | 0 | `Success: no issues found in 3 source files` |
| 3 | `uv run mypy packages/matriz-client/tests` | 0 | `Success: no issues found in 24 source files` |
| 4 | `uv run mypy packages/iol-client/tests` | 0 | `Success: no issues found in 13 source files` |
| 5 | `uv run mypy packages/ambito-financiero-client/tests` | 0 | `Success: no issues found in 19 source files` |
| 6 | `uv run mypy packages/market-data-client/tests` | 0 | `Success: no issues found in 27 source files` |

`Success: no issues found` printed **six times, once per package** — the acceptance criterion. Because CI iterates `higyrus-client` first under `set -e`, its green is what makes the remaining five legs observable at all; before this plan the loop aborted at package 1 and masked the identical ambito failure (T-32-08).

### `test` job

`uv run pytest packages/<pkg> -q`, one package per invocation, matching the matrix shape:

| # | Package | Exit | Result | Research expectation |
|---|---------|------|--------|----------------------|
| 1 | `higyrus-client` | 0 | 236 passed | 236 ✅ |
| 2 | `wallets-client` | 0 | 4 passed | 4 ✅ |
| 3 | `matriz-client` | 0 | 427 passed | 427 ✅ |
| 4 | `iol-client` | 0 | 242 passed | 242 ✅ |
| 5 | `ambito-financiero-client` | 0 | 200 passed, 1 deselected | 200 ✅ |
| 6 | `market-data-client` | 0 | 573 passed | 573 ✅ |

**Total: 1682 passed** — exactly the expected figure, never lower. Zero failed, zero skipped, zero xfailed. The single ambito `deselected` is pre-existing marker-config behaviour, untouched by this plan.

### Python 3.13 matrix leg

`uv` already had **CPython 3.13.12** provisioned (`cpython-3.13.12-macos-aarch64-none`), so the smoke check was run as the plan directs:

| Command | Exit | Result |
|---------|------|--------|
| `uv run --python 3.13 pytest packages/iol-client -q` | 0 | **242 passed** on `3.13.12 (main, Mar 25 2026)` |

The bare invocation the plan names initially returned `ModuleNotFoundError: No module named 'iol_client'` (rc=4) — the workspace was not synced *for that interpreter*, which is an environment-provisioning gap, not a test failure. It was resolved by provisioning an **isolated** 3.13 environment via `UV_PROJECT_ENVIRONMENT` pointed outside the repo, so the tracked tree and the default `.venv` were never traded away. The remaining 11 cells of the 6 × 2 matrix are left to the real CI run in Plan 32-06.

### Prohibition checks

| Check | Result |
|-------|--------|
| `git diff --stat -- pyproject.toml` | **empty** — no `[tool.mypy]` edit, no `per-file-ignores` entry, no relaxed `warn_unused_ignores`, no `--no-strict` |
| `git diff -- packages/*/tests \| grep -c '^-.*def test_'` | **0** in both task diffs — no test removed |
| Unbracketed added ignores | **0** — every one of the 16 added ignores carries a bracketed error code |
| Test count per package | **unchanged** in all six packages |
| `check_decode_intactness.py` digest | `ac14868282ad0a5c` **before and after** — the five `_decode.py` source copies were never touched |

## Files Created/Modified

- `packages/matriz-client/tests/test_decode.py` — 16 narrow `# type: ignore[attr-defined]`; 6 `comparison-overlap` fixes via `object`-typed intermediates; 2 `cast(Any, cls)` at the `hints_for` call sites; `alias.__args__` → `typing.get_args(alias)`; `cast`/`get_args` added to the `typing` import.
- `packages/matriz-client/tests/test_ws_decode_mode.py` — `_handle_message(object(), ...)` now receives the module's own `_FakeWebSocketApp` stand-in cast to the declared `websocket.WebSocketApp` parameter type, via a `TYPE_CHECKING`-only import (no new runtime import).
- `packages/higyrus-client/tests/test_decode.py` — `assert SILENT_SINK(...) is None` → bare call (iol shape, comment included); dead `# type: ignore[arg-type]` at `_full_payload` deleted.
- `packages/ambito-financiero-client/tests/test_decode.py` — identical pair of fixes.

## Decisions Made

1. **`comparison-overlap` resolved toward `object`-typed intermediates, not toward substituted typed zeros.** The plan left this open ("state which you chose in the SUMMARY"). matriz's `POLICY.scalar_passthrough is True` means a wrong-typed wire value is returned *verbatim* — so `obj.s == 7` for a `str`-declared field is asserting the wire `7` survived, not that a default was substituted. Asserting a typed zero would have inverted the property. Widening the read to `object` (`passed_through: dict[str, object]`, `side: object`, `segment_id: object`) keeps the assertion byte-equivalent while telling mypy the truth: the runtime value deliberately diverges from its own declaration. Cast-free, ignore-free, and the divergence stays legible in the source.
2. **`arg-type` at `hints_for` fixed with `cast(Any, cls)`, matching `market-data-client`.** These two are a mypy quirk, not a real type error: `hints_for` is annotated `(cls: Any)`, but `@lru_cache`'s `__call__` constrains arguments to `Hashable`, and mypy resolves `type[_SafeModel].__hash__` to the instance method rather than `type.__hash__`. `packages/market-data-client/tests/test_decode.py` already carries `cast(Any, cls)` at six such sites under the same strict config, so this is the repo's settled shape rather than a new one.
3. **`alias.__args__` → `typing.get_args(alias)`.** The 21st `attr-defined` was not a LogRecord read at all — mypy types a `Literal` alias as `<typing special form>`, which has no `__args__`. `get_args` is the public, typed accessor, so this error needed no ignore.
4. **The ws `arg-type` was fixed at the call site, not suppressed.** Feeding a wrong type is not the subject of `test_strict_mode_error_is_logged_when_no_error_callback_is_registered` — the subject is that a strict-mode decode error is logged rather than escaping the handler. Passing the file's declared `_FakeWebSocketApp` (the same object the monkeypatched constructor yields on the connected paths) makes the call *more* faithful to production shape than the bare `object()` it replaced.
5. **RESEARCH.md assumption A1 is now CONFIRMED, not assumed.** All 33 errors fell to test-code changes; no strictness policy decision was needed and none was made, so no operator sign-off was required.

## Deviations from Plan

**None — plan executed exactly as written.** No deviation rule fired: no bug was auto-fixed, no missing critical functionality was added, no blocker required a workaround, and no architectural change arose.

Two things worth flagging that are *not* deviations:

1. **`requirements-completed` is deliberately empty.** The plan's frontmatter lists `GATE-TYP-01`, but so does every one of the other five Phase 32 plans — the ID spans the whole phase. This plan's own objective states it "creates **none of them**" and is "pre-existing debt surfaced by research, not Phase 32 scope creep". Running `requirements mark-complete GATE-TYP-01` at plan 1 of 6 would flip the traceability table to Complete for work that has not started. Marking is left to Plan 32-06, which closes the phase. Recorded here so the omission is a documented choice, not an oversight.
2. **Task 3 produced no commit.** By its own instruction ("Do not modify any file in this task"), verified by `git status --porcelain` over `packages/`, `pyproject.toml`, `tools/` and `.github/` returning 0 lines afterwards.

---

**Total deviations:** 0
**Impact on plan:** None. Scope held exactly to the four named test files.

## Issues Encountered

- **The Python 3.13 leg needed environment provisioning.** `uv run --python 3.13 pytest packages/iol-client -q` failed with `ModuleNotFoundError: No module named 'iol_client'` because the workspace was not synced for that interpreter. Resolved without touching the tracked tree or trading away the default `.venv`: an isolated 3.13 environment was provisioned under `UV_PROJECT_ENVIRONMENT` pointing outside the repo. 242 tests then passed on 3.13.12. The default `.venv` was re-synced to 3.12.13 afterwards and the whole 3.12 baseline re-verified against the fresh environment (matriz 427 passed, `mypy packages/matriz-client/tests` green) so the recorded numbers are reproducible rather than an artefact of a stale env.
- **No other issue.** The live error re-enumeration matched RESEARCH.md's counts exactly, so no drift reconciliation was needed.

## User Setup Required

None — no external service configuration required. Every command in this plan is offline; no credential, no `.env`, and no network call was involved.

## Next Phase Readiness

**Ready.** Waves 1-3 of Phase 32 now have a truthful CI signal:

- All four `ci.yml` jobs are green locally at `f08b7f2`. Any red that Plans 32-02 … 32-06 produce is attributable to their own change, not inherited.
- The Wave 0 checklist in `32-VALIDATION.md` is closed.
- `check_decode_intactness.py` digest `ac14868282ad0a5c` is the reference value for later plans.
- The src-global `mypy` count is **62 source files**; Plan 32-05 is expected to move this when it enrolls `market-data-client` in `[tool.mypy] files`.

**Carry-forward notes:**

- `STATE.md` § Blockers/Concerns carries two bullets describing these errors as open debt. Both are now resolved and are updated as part of this plan's metadata commit.
- The Phase 31 `deferred-items.md` D-2/D-3 entries are closed by this plan.
- The same `deferred-items.md` bullet also reports `verification/` matriz probes calling `probe_login_sync()` with a pre-15-05 signature (19 failed + 19 errors in a *full* local suite run). That is **out of scope here and still open**: `verification/` has never executed in CI (`ci.yml:125` passes an explicit `packages/<pkg>` path that overrides `testpaths`), so it does not affect any of the six per-package legs recorded above. Phase 32's GATE-TYP-01 work is the first thing that will put repo-level test surface into CI, so that debt should be re-checked before Plan 32-06 claims a full-matrix green.

## Self-Check: PASSED

All four modified test files exist on disk. Both task commits (`5ce4e87`, `f08b7f2`) are present in git history. No claimed artifact is missing.

---
*Phase: 32-gates-de-homogeneidad-d-16*
*Completed: 2026-08-25*
