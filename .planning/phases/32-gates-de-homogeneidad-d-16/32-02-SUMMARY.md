---
phase: 32-gates-de-homogeneidad-d-16
plan: 02
subsystem: tooling
tags: [ci-gate, ast, static-analysis, non-vacuity, tdd, stdlib-only, github-actions]

# Dependency graph
requires:
  - phase: 32-gates-de-homogeneidad-d-16
    plan: 01
    provides: "The CI-green baseline (all four ci.yml jobs green at f08b7f2) — any red this plan produces is attributable to its own change, not inherited"
  - phase: 31-endpoints-de-ops-estructura-uniforme
    provides: "tools/check_uniform_structure.py, the roster-from-disk / anti-vacuity gate template this plan copies, plus locked decision D-12 (cross-package gates are steps of the existing `lint` job)"
  - phase: 30-iol-tipado
    provides: "packages/iol-client/tests/test_typed_surface_red.py, the RED-fixture precedent that fixes where a non-vacuity proof lives"
provides:
  - "tools/check_surface_types.py — a stdlib-AST-only ratchet that fails the day an exported name returns Any / dict[str, Any] / an unannotated value"
  - "The D-04 injectable-root seam: the first gate in this repo that can be tested, because REPO_ROOT is a default argument value rather than a body-referenced constant"
  - "packages/iol-client/tests/test_surface_types_red.py — five automated bounds proving the gate non-vacuous inside the 6x2 CI matrix"
  - "A blocking `surface-types` step in the existing `lint` job of .github/workflows/ci.yml"
  - "The measured surface baseline: 6 packages, 178 __all__ names, 319 definitions, 23 exempted, 0 violations"
affects: [32-03, 32-04, 32-05, 32-06, phase-33-live-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Injectable root (D-04): `REPO_ROOT` is a default argument value only; the scan body threads a `root: Path` parameter, which is the seam that makes a `tools/` gate testable at all"
    - "Scan/assert split: `scan_surface_types(root) -> ScanResult` raises only on structural problems and *returns* violations; `check_surface_types(root)` turns violations into the failure"
    - "Exemption accounting by reason (`exempted_by_reason`) so the DT-06 taxonomy cannot be widened silently to swallow a real violation"
    - "A package test importing a repo-root `tools/` module enrols that module in the per-package strict mypy loop (verified via `mypy -v`)"

key-files:
  created:
    - "tools/check_surface_types.py"
    - "packages/iol-client/tests/test_surface_types_red.py"
    - ".planning/phases/32-gates-de-homogeneidad-d-16/32-02-SUMMARY.md"
  modified:
    - ".github/workflows/ci.yml"

key-decisions:
  - "32-02: a MISSING return annotation is a violation, not just an annotation mentioning `Any` — this is stricter than research's simulation and is what makes the 23rd exemption appear (an exception class's unannotated `__init__`, absorbed as `dunder`). The delta is a consequence of the stricter rule, never of a broader exemption predicate"
  - "32-02: `exempted` counts HITS the exemptions absorbed (definitions that would otherwise have been violations), not every dunder/underscore member encountered — the only semantics under which the count is comparable to research's measured 22"
  - "32-02: `scan_surface_types` raises on structural problems but returns violations; only `check_surface_types` raises on violations. This split is what lets the RED fixture assert on the exemption taxonomy of a tree that is deliberately full of exempt hits"
  - "32-02: no package name appears anywhere in the gate's source, docstring included — a prose mention reads as a hardcoded roster to anyone grepping for one, and the plan's own acceptance criterion greps"
  - "32-02: D-05 recorded in situ (gate docstring + ci.yml comment) — ROADMAP.md:25's 'job de CI nuevo' is superseded by Phase 31's locked D-12 'step en lint'; a step also leaves the job name unchanged, closing research assumption A2"

patterns-established:
  - "A gate's non-vacuity proof is a test in the 6x2 matrix, never a manual demonstration recorded in a SUMMARY"
  - "Real-tree assertions use FLOORS (>=), never equalities, so a seventh package or a new export cannot falsely redden the suite while a collapse to a trivial scan still does"
  - "Synthetic broken trees live under pytest's `tmp_path`, never as committed fixtures under `packages/` (which would enter check_decode_intactness.py's Check D roster and owe check_uniform_structure.py a models.py + types.py)"

requirements-completed: []

# Metrics
duration: 7min
completed: 2026-08-25
status: complete
---

# Phase 32 Plan 02: TRACER slice — surface-type AST gate + RED fixture + CI wiring Summary

**A stdlib-AST-only ratchet that walks every `__all__` name (including methods of exported classes) and fails on an untyped return, proven non-vacuous by five automated bounds in the 6×2 CI matrix and wired as a blocking step of the existing `lint` job — 6 packages, 178 `__all__` names, 319 definitions, 23 exempted, 0 violations on today's tree.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-08-25T21:07:23Z
- **Completed:** 2026-08-25T21:14:40Z
- **Tasks:** 3
- **Files created/modified:** 3

## Accomplishments

- **Criterion 1 and criterion 2 of Phase 32 are satisfied by one shippable vertical slice.** The gate exists, is green on the real tree, is RED on four distinct broken trees, typechecks under strict mypy, and runs in a real CI job that it can fail.
- **The gate is a ratchet with a proof.** Today's tree is already clean, so a gate with no lower bound would be indistinguishable from `return "ok"`. Four of the five tests are that lower bound.
- **The D-04 seam landed.** `tools/check_surface_types.py` is the first gate in this repo with an injectable root, and therefore the first with a test at all. The two pre-existing gates (`check_decode_intactness.py`, `check_uniform_structure.py`) still reference `REPO_ROOT` from inside their bodies and still have none.
- **A side effect worth naming, now measured rather than predicted.** `tools/*.py` sits outside mypy's global `files`. Because the RED fixture imports the gate from inside `packages/iol-client/tests/`, `uv run mypy packages/iol-client/tests` now parses and typechecks `tools/check_surface_types.py` as a followed import — confirmed with `mypy -v` (`Parsing …/tools/check_surface_types.py (tools.check_surface_types)`). The gate is enrolled in the per-package strict loop by construction.

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): automated non-vacuity proof before the gate exists** — `d3ff075` (test)
2. **Task 2 (GREEN): stdlib-AST surface-types gate with an injectable root** — `e871541` (feat)
3. **Task 3: blocking `surface-types` step in the existing `lint` job** — `c1a7f90` (chore)

## RED observation (Task 1, required verbatim by the plan)

`uv run pytest packages/iol-client/tests/test_surface_types_red.py -q` immediately after Task 1's commit:

```
==================================== ERRORS ====================================
_____ ERROR collecting packages/iol-client/tests/test_surface_types_red.py _____
ImportError while importing test module '/Users/admin/development/market-libs/packages/iol-client/tests/test_surface_types_red.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
packages/iol-client/tests/test_surface_types_red.py:57: in <module>
    from tools.check_surface_types import CheckFailure, check_surface_types, scan_surface_types
E   ModuleNotFoundError: No module named 'tools.check_surface_types'
=========================== short test summary info ============================
ERROR packages/iol-client/tests/test_surface_types_red.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.04s
```

Exactly one reason for the failure — the module the tests describe did not exist yet. Not a syntax error, not a fixture error. `ruff check` and `ruff format --check` were both exit 0 on the same file at the same commit, and the AST walk confirmed **five** `test_*` functions, all carrying a `-> None` return annotation.

`git diff HEAD -- packages/iol-client/tests/test_surface_types_red.py` returned **0 lines** after Task 2 landed: all five tests passed without a single assertion being edited to fit the implementation.

## Measured baseline (the gate's own output)

```
surface types: 6 packages, 178 `__all__` names, 319 definitions scanned, 23 exempted
(dunder 13, private-helper 1, serialize-out 9), 0 violations
```

**319 definitions matches research's simulation exactly.** The exemption count is **23**, one more than research's measured 22, and the extra hit is fully accounted for:

| Reason | Count | Research | Delta |
|--------|------:|---------:|-------|
| `dunder` | 13 | 12 | +1 — an exception class's `__init__`, which carries **no return annotation** |
| `private-helper` | 1 | 1 | — (`Client._matriz_legacy_request`, reachable only as a method — direct empirical confirmation that D-03's class-walk is load-bearing) |
| `serialize-out` | 9 | 9 | — (exactly the nine `__all__`-reachable `to_dict` methods; the tenth definition is not `__all__`-reachable, so `__all__`-scoped resolution is what keeps criterion 1's number correct) |

Research's simulation flagged only annotations *containing* `Any`. This gate additionally treats a **missing** return annotation as untyped, because an unannotated exported return is exactly the untyped surface the ratchet exists to prevent. That stricter rule surfaces one extra hit, which the pre-existing `dunder` exemption absorbs. Recorded in the gate docstring so a future reader does not read 23-vs-22 as drift.

## Verification evidence

| Check | Result |
|-------|--------|
| `uv run pytest packages/iol-client/tests/test_surface_types_red.py -q` | **5 passed** |
| `uv run python tools/check_surface_types.py` | exit **0**, 6 packages / 319 definitions / 0 violations |
| `uv run mypy tools/check_surface_types.py` | exit 0 — `Success: no issues found in 1 source file` |
| `uv run mypy packages/iol-client/tests` | exit 0 — `Success: no issues found in 14 source files` (was 13) |
| `uv run ruff check tools/... && uv run ruff format --check tools/...` | exit 0 |
| Import set ⊆ `{ast, sys, pathlib, dataclasses}` | **OK** — `['__future__', 'ast', 'dataclasses', 'pathlib', 'sys']` |
| No hardcoded package roster in the gate | **OK** — no package import name occurs anywhere in the file |
| Both existing gates still green | `check_decode_intactness.py` digest `ac14868282ad0a5c` **unchanged**; `check_uniform_structure.py` green |
| `grep -c 'uv run python tools/check_surface_types.py' .github/workflows/ci.yml` | **1** |
| Step is inside the `lint` job | **OK** — `lint:` at line 22 < step at line 65 < `pre-commit:` at line 67 |
| Job roster unchanged at four | **4** |
| `continue-on-error` outside comments | **0** |
| Whole `lint` job reproduced locally (all **seven** steps) | exit **0** |
| `uv run pre-commit run --files .github/workflows/ci.yml` | all applicable hooks Passed (incl. `check yaml`) |
| Wave 0 baseline unbroken | `uv run pytest packages -q` → **1687 passed**, 1 deselected (1682 + the 5 new) |

## What each of the five tests pins

1. **`test_gate_is_green_on_the_real_tree`** — upper bound. `check_surface_types()` reports `0 violation`; the scan has empty `violations`, `packages >= 6`, `definitions >= 300`, `exempted >= 20`. All floors, never equalities.
2. **`test_gate_fails_on_an_injected_regression`** — lower bound. A synthetic `fake-client` whose exported module-level `get_thing` returns `dict[str, Any]` raises `CheckFailure` matching `get_thing`.
3. **`test_regression_inside_an_exported_class_is_caught`** — D-03 in executable form. The offender is a *method* of an exported class; the failure names `Client.get_thing`. This is the most likely real regression vector.
4. **`test_exempt_members_do_not_trip_the_gate`** — the DT-06 taxonomy is reachable and load-bearing. All three exempt shapes (`to_dict`, `__reduce__`, `_helper`) genuinely return untyped mappings, so each is a real hit the exemption absorbs; `exempted_by_reason` is asserted as `{dunder: 1, private-helper: 1, serialize-out: 1}`.
5. **`test_empty_and_unresolvable_trees_are_failures_not_greens`** — three sub-cases, all `CheckFailure`: an empty `packages/`, a package with no `src/`, and a package whose `__init__.py` declares no module-level `__all__`. A naive gate would report all three as "nothing wrong found".

## Files Created/Modified

- **`tools/check_surface_types.py`** (new, 488 lines) — stdlib-only (`ast`, `sys`, `pathlib`, `dataclasses`). Exports `CheckFailure`, `ScanResult`, `scan_surface_types`, `check_surface_types`, `main`, plus `REPO_ROOT`, `_BUILD_ARTIFACT_SUFFIX`, `_fail`, `_import_root`, `_parse`, `_all_names`, `_definition_sites`, `_is_exempt`, `_annotation_mentions_any`, `_module_path`, `_adjudicate`. The docstring carries the four named sections copied in structure from the analog plus `THE ROOT IS INJECTABLE (D-04)` and `WHAT IS EXEMPT, AND WHAT DT-06 CLAUSE IS SUBSUMED`, and records D-05 and the OQ-2 resolution in situ.
- **`packages/iol-client/tests/test_surface_types_red.py`** (new, 211 lines) — five tests plus one module-level `_write_fake_package` helper. Docstring states why the file lives in a package test directory (`verification/` has never executed in CI), names the D-04 seam, and states that the two bounds are complementary.
- **`.github/workflows/ci.yml`** (+6 lines) — one `surface-types` step appended to the `lint` job after `uniform-structure`, carrying the sibling gates' three-line rationale comment verbatim plus a fourth line recording D-05.

## Decisions Made

1. **A missing return annotation is a violation.** The plan's behaviour spec required it and the gate implements it. The consequence — one extra `dunder` exemption relative to research's 22 — is documented in the gate docstring rather than papered over. The alternative (only flagging annotations that *mention* `Any`) would let `def get_thing(self):` onto the exported surface unchallenged, which is the same untyped surface by a different spelling.
2. **`exempted` counts absorbed hits, not every exempt member.** Counting every dunder and underscore member encountered would produce a number in the hundreds that no longer means anything and could not be compared to research's baseline. Hit semantics is also what makes test 4's `exempted == 3` a meaningful assertion about the predicate rather than about the fixture's shape.
3. **Structural failures raise from `scan_surface_types`; violations do not.** Test 4 needs to inspect the exemption taxonomy of a tree deliberately full of exempt hits — which is only possible if the scan returns rather than raises. Conversely, test 5's three cases must raise *from the scan*, because a structural failure is not a "violation" of anyone's surface; it means the gate could not see the surface at all.
4. **No package name in the gate's source, docstring included.** The first draft named the package owning the unannotated `__init__` when explaining the 23-vs-22 delta. The plan's own acceptance criterion greps for `higyrus_client` / `matriz_client` in every non-comment line, and it failed. Rather than argue that prose is not a roster, the sentence was rewritten to describe the shape (`an exception class's __init__`) instead of the owner, and the docstring now states explicitly why: *a prose mention reads as a hardcoded roster to anyone grepping for one.*
5. **The test derives `_REPO_ROOT` independently** (`Path(__file__).resolve().parents[3]`) rather than importing the gate's own `REPO_ROOT`. A test asserting *about* a gate must not borrow the constant it is checking.
6. **A2 closed as the plan required.** Adding a *step* does not rename the *job*: `grep -cE '^  (lint|pre-commit|typecheck|test):'` is still `4` and the job is still named `lint` / "Lint y formato (ruff)". No GitHub branch-protection required-check name moves, so no repo-admin action is implied by this plan. (`main` also has `protected: false` per Phase 28's measurement, so no required check exists to move.)

## Deviations from Plan

**None — plan executed exactly as written.** No deviation rule fired: no bug was auto-fixed, no missing critical functionality was added, no blocker required a workaround, and no architectural change arose. No package was installed; the gate is stdlib-only by design and `uv.lock` is byte-unchanged (`uv lock --check` → `Resolved 48 packages`).

Four things worth flagging that are *not* deviations:

1. **Two mechanical repairs during Task 2, both pre-commit.** (a) `ruff check --fix` reordered the Task 1 import block (isort I001) before that commit; (b) mypy flagged a variable-name collision (`node` / `member` rebound between an outer `ast.stmt` loop and an inner unpack), fixed by renaming the inner unpack to `qualified_name` / `member_name` / `func_node`. Neither changed behaviour and both landed inside their own task's commit.
2. **`requirements-completed` is deliberately empty.** All six Phase 32 plans carry `GATE-TYP-01`; this plan delivers criterion 1 and criterion 2 but not criteria 3-5. Marking the requirement complete at plan 2 of 6 would flip the traceability table for work that has not started. Plan 32-06 closes it — the same reasoning Plan 32-01 recorded.
3. **The plan's `<!-- planner-discipline-allow: continue-on-error -->` marker was not copied into `ci.yml`.** It exists in the PLAN to let the planner *name* the forbidden key; the acceptance criterion greps for `continue-on-error` in non-comment lines of `ci.yml` and expects `0`. The prohibition is honoured in the artefact: the step declares exactly `name` and `run`.
4. **The 23-vs-22 exemption delta is a plan-specified consequence**, not an unplanned finding — the plan's Task 2 action states "A definition with no return annotation at all is a violation too". It is highlighted here only because a reader comparing against `32-RESEARCH.md` would otherwise see an unexplained +1.

---

**Total deviations:** 0
**Impact on plan:** None. Scope held exactly to the three named files.

## Issues Encountered

- **None blocking.** The only two friction points were the isort reorder and the mypy name collision described above, both resolved inside their own task.
- **Carry-forward, unchanged:** `verification/` matriz probes still call `probe_login_sync()` with the pre-15-05 signature. This plan does **not** move that needle — the gate is a `tools/` script invoked directly by the `lint` job, and the RED fixture lives under `packages/iol-client/tests/`, so `verification/` still never executes in CI. Plan 32-06 must still re-check that debt before claiming a full-matrix green.

## Known Stubs

**None.** No hardcoded empty return, no placeholder text, no TODO/FIXME, and no component awaiting a data source. Every symbol the plan's artifact list names is implemented and exercised by a test.

## User Setup Required

None — every command in this plan is offline. No credential, no `.env`, and no network call was involved, and the gate never reads a `.env` or imports a package module (so no `load_dotenv()` runs inside it).

## Next Phase Readiness

**Ready.** Plans 32-03 … 32-06 inherit:

- A **blocking** CI step. A regression on the exported surface now fails the `lint` job rather than being reported into the void.
- The measured baseline `6 / 178 / 319 / 23 / 0`, and `check_decode_intactness.py`'s digest `ac14868282ad0a5c` still unchanged.
- The suite at **1687 passing** (Wave 0's 1682 + this plan's 5).
- A working precedent for the D-04 injectable-root seam, which Plan 32-04's `tools/surface_parity.py` should copy rather than reinvent.

**Carry-forward notes:**

- Plan 32-05 is expected to move mypy's src-global count (currently **62 source files**) when it enrols `market-data-client` in `[tool.mypy] files`. That edit does not interact with this gate.
- Plan 32-06 owns `requirements mark-complete GATE-TYP-01` and the full-matrix green claim — and must re-check the `verification/` `probe_login_sync` debt first.
- If a future plan ever needs the gate to enforce a *second* rule (banning raw transport types such as `httpx.Response` on the exported surface), the gate docstring records that as a deliberate scope addition, not a bug fix — the `_request` clause of DT-06 is currently subsumed by the `private-helper` rule.

## Self-Check: PASSED

- `tools/check_surface_types.py` — FOUND
- `packages/iol-client/tests/test_surface_types_red.py` — FOUND
- `.github/workflows/ci.yml` — FOUND (contains `tools/check_surface_types.py`, exactly once)
- Commits `d3ff075`, `e871541`, `c1a7f90` — all present in git history

---
*Phase: 32-gates-de-homogeneidad-d-16*
*Completed: 2026-08-25*
