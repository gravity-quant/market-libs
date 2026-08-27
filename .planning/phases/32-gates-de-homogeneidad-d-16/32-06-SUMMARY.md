---
phase: 32-gates-de-homogeneidad-d-16
plan: 06
subsystem: testing
tags: [sync-async-parity, fan-out, wallets, asserted-absence, non-vacuity, ci-matrix, criterion-5, gate-typ-01]

# Dependency graph
requires:
  - phase: 32-gates-de-homogeneidad-d-16
    plan: 04
    provides: "The frozen `tools/surface_parity.py` walker (single metric, four numbered rules, per-package integer floors) and the 52-line market-data pilot this plan copies five times"
  - phase: 32-gates-de-homogeneidad-d-16
    plan: 05
    provides: "Criterion 4 closed, mypy at 75 source files, and the `verification/` `probe_login_sync` carry-forward debt this plan was required to re-check before claiming a full-matrix green"
  - phase: 32-gates-de-homogeneidad-d-16
    plan: 01
    provides: "The Wave 0 CI-green baseline (1682 passing) this plan's 1707 is measured against, and the per-package mypy invocation shape"
provides:
  - "All six packages carry an in-package sync/async parity test that runs in the 6x2 CI matrix — criterion 3's coverage complete, no package and no axis skipped"
  - "packages/wallets-client/tests/test_surface_parity.py — the asserted-absence pattern: wallets participates on the module axis and asserts its missing Client/AsyncClient pair positively, never with a skip or an early return"
  - "Criterion 5 answered by a full local reproduction of all four ci.yml jobs and all twelve test matrix legs (6 packages x py3.12 + py3.13), each recorded with its exit status"
  - "GATE-TYP-01 closed — the requirement all six Phase 32 plans carried and all five prior plans deliberately left open"
  - "A measured, attributable re-statement of the `verification/` carry-forward debt: 2 failed + 2 errors localised to one file, invisible to every CI leg"
affects: [phase-33-live-verification, phase-34-republish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fan-out of a shared gate as thin per-package hook files: the walker exists once in tools/, the six in-package files are three delegating calls each"
    - "Asserted absence with an actionable failure message: the assertion names what the failure MEANS (enrol on the class axis, re-examine D-10) rather than merely reporting a boolean"
    - "Absence cross-checked on two independent paths — `hasattr` on both surfaces AND the helper's own `CLASS_AXIS_ABSENT` marking — so the test cannot go stale on one side alone"
    - "Non-vacuity of an absence assertion proven in-process by injecting the attribute (`c.Client = type(...)`) rather than by mutating a tracked file"

key-files:
  created:
    - "packages/ambito-financiero-client/tests/test_surface_parity.py"
    - "packages/iol-client/tests/test_surface_parity.py"
    - "packages/higyrus-client/tests/test_surface_parity.py"
    - "packages/matriz-client/tests/test_surface_parity.py"
    - "packages/wallets-client/tests/test_surface_parity.py"
    - ".planning/phases/32-gates-de-homogeneidad-d-16/32-06-SUMMARY.md"
  modified: []

key-decisions:
  - "32-06: the wallets absence test asserts on BOTH paths — `hasattr` on `client`/`aio` (the shape the plan prescribed, and the shape of check_decode_intactness.py's Check D) AND `class_parity_report(...).axis == CLASS_AXIS_ABSENT` (the marked-absent report 32-04 built precisely for this caller). Either alone would be a single point of staleness; together the test fails the day the pair appears no matter which side notices first"
  - "32-06: the plan's expected iol count of 248 is a two-off arithmetic slip and 250 is correct (242 baseline + 3 parity + 5 surface-gate RED from 32-02). Reconciled, not forced: the plan's OWN total derivation (1682 + 18 + 5 + 2 = 1707) agrees with 250, and the measured workspace total is exactly 1707"
  - "32-06: `tools/surface_parity.py` is byte-unchanged. No normalization rule was added, no bound lowered, no comparison narrowed. All eighteen assertions across six packages passed on their first run"
  - "32-06: the `verification/` debt was re-checked STATICALLY plus one targeted file run rather than by a full `pytest verification` run — the full run does not terminate in ten minutes locally because those probes reach live services, which is itself further evidence that `verification/` is not a CI-runnable surface"
  - "32-06: GATE-TYP-01 is marked complete HERE, at plan 6 of 6, exactly as Plans 32-01, 32-02, 32-04 and 32-05 each recorded they were deferring it to"

patterns-established:
  - "A gate's per-package hook file states its own package's floor and what that floor does and does not assert — the integer never travels without its interpretation"
  - "When a per-package expectation in a plan disagrees with a measurement, reconcile against the plan's own independent derivation before treating either as authoritative"

requirements-completed: [GATE-TYP-01]

# Metrics
duration: 21min
completed: 2026-08-25
status: complete
---

# Phase 32 Plan 06: parity fan-out to five packages + full CI reproduction Summary

**All six workspace packages now carry an in-package sync/async parity test that runs in every one of the twelve CI matrix legs — wallets included, on the module axis and with its missing `Client`/`AsyncClient` pair asserted positively rather than skipped — and every `ci.yml` job plus all twelve legs were reproduced locally green, at 1707 passing on both Python 3.12 and 3.13, with the shared walker byte-unchanged.**

## Performance

- **Duration:** 21 min
- **Started:** 2026-08-25T21:42:30Z
- **Completed:** 2026-08-25T22:03:38Z
- **Tasks:** 3 (2 `tdd`, 1 `auto`)
- **Files created/modified:** 5 created, 0 modified

## Task Commits

1. **Task 1 — parity tests for the four class-bearing packages** — `fa215e0` (test), 4 files, +200 lines
2. **Task 2 — wallets enrolled with an asserted class absence** — `10fd60d` (test), 1 file, +118 lines
3. **Task 3 — full CI reproduction** — **no code commit by design.** The task's own action says "Modify no source in this task"; `git status --porcelain -- packages/ tools/ .github/ pyproject.toml verification/ uv.lock` returned 0 lines after it ran. Its deliverable is the *Criterion 5* section below, which ships in this plan's metadata commit.

## Accomplishments

- **Criterion 3's coverage is complete and no package passes vacuously.** Six parity files, eighteen assertions, zero skips, zero xfails, zero early returns. `ls packages/*/tests/test_surface_parity.py | wc -l` = **6**.
- **The helper survived the fan-out untouched.** `git diff HEAD~1 -- tools/surface_parity.py` after Task 1 returned **0 lines**. All twelve of Task 1's assertions passed on their first run, which is what 32-04's measurement predicted and is the evidence that nothing was accommodated.
- **wallets' absence assertion is provably non-vacuous.** Injecting `client.Client = type("Client", (), {})` in-process makes the test **fail** at line 98 with the actionable message. A test that would still pass once the thing it denies exists is not an assertion; this one is.
- **Twelve-for-twelve locally.** All six packages passed on **both** interpreters with identical counts. The py3.13 leg was reproduced, not assumed.
- **The carry-forward debt was re-checked, not waved through.** It is still open, it is smaller and more precisely located than the last measurement suggested, and it is invisible to all twelve CI legs.

## Criterion 5 — full CI reproduction

All commands run at `10fd60d` on CPython 3.12.13 via the workspace `.venv`, in `ci.yml` job order.

### `lint` job — 9 steps

| # | Command | Exit | Headline output |
|---|---------|------|-----------------|
| 1 | `uv lock --check` | 0 | `Resolved 48 packages in 2ms` |
| 2 | `uv sync --all-packages --all-extras --dev --frozen` | 0 | `Checked 46 packages in 3ms` |
| 3 | `uv run ruff check .` | 0 | `All checks passed!` |
| 4 | `uv run ruff format --check .` | 0 | `241 files already formatted` (was 235 at 32-05) |
| 5 | `uv run lint-imports` | 0 | `Analyzed 69 files, 141 dependencies.` / **`Contracts: 5 kept, 0 broken.`** |
| 6 | `lint-logging` grep (`ci.yml:47` verbatim) | 0 | no matches |
| 7 | `uv run python tools/check_decode_intactness.py` | 0 | Checks A-D green; digest **`ac14868282ad0a5c`** unchanged; filter region `684191c7cdc5ff9c`; Check C now scans **75** package source files |
| 8 | `uv run python tools/check_uniform_structure.py` | 0 | `all 6 packages under packages/ carry models.py, types.py` |
| 9 | `uv run python tools/check_surface_types.py` | 0 | `6 packages, 178 __all__ names, 319 definitions scanned, 23 exempted (dunder 13, private-helper 1, serialize-out 9), 0 violations` — identical to 32-04/32-05 |

### `pre-commit` job

| Command | Exit | Headline output |
|---------|------|-----------------|
| `uv run pre-commit run --all-files --show-diff-on-failure` | **0** | **9/9 hooks Passed** (trailing-whitespace, end-of-file, check-yaml, check-toml, large-files, merge-conflicts, ruff, ruff-format, mypy). No hook rewrote a file. |

This job was not in the Wave 0 baseline table's critical path and its `mypy` hook covers a different file set than the `typecheck` job's; it is green on the six new files.

### `typecheck` job

| Command | Exit | Headline output |
|---------|------|-----------------|
| `uv run mypy` (src global) | 0 | **`Success: no issues found in 75 source files`** — the count Plan 32-05 moved from 62, expected and confirmed |

Per-package loop, one package per invocation, in `ci.yml:101` order:

| # | Command | Exit | Source files | Delta vs Wave 0 |
|---|---------|------|-------------:|-----------------|
| 1 | `uv run mypy packages/higyrus-client/tests` | 0 | 12 | 11 → 12 (+1 parity) |
| 2 | `uv run mypy packages/wallets-client/tests` | 0 | 4 | 3 → 4 (+1 parity) |
| 3 | `uv run mypy packages/matriz-client/tests` | 0 | 25 | 24 → 25 (+1 parity) |
| 4 | `uv run mypy packages/iol-client/tests` | 0 | 15 | 13 → 15 (+1 parity, +1 surface-types RED from 32-02) |
| 5 | `uv run mypy packages/ambito-financiero-client/tests` | 0 | 20 | 19 → 20 (+1 parity) |
| 6 | `uv run mypy packages/market-data-client/tests` | 0 | 29 | 27 → 29 (+1 parity 32-04, +1 boundary RED 32-05) |

`Success: no issues found` printed **six times**.

**The helper really is enrolled in strict mypy, verified rather than assumed.** `uv run mypy packages/wallets-client/tests -v` prints `Metadata fresh for tools.surface_parity: file /Users/admin/development/market-libs/tools/surface_parity.py` — the module is in the build graph even though it is not counted in the `N source files` headline (that headline counts explicit sources, not followed imports). This is the mechanism by which `tools/*.py`, which sits outside mypy's global `files`, gets strict-checked at all.

### `test` job — py3.12 leg

`uv run pytest packages/<pkg> -q`, one package per invocation, matching the matrix shape:

| # | Package | Exit | Result | Plan expectation | Reconciliation |
|---|---------|------|--------|------------------|----------------|
| 1 | `higyrus-client` | 0 | **239 passed** | 239 | matches (236 + 3) |
| 2 | `wallets-client` | 0 | **7 passed** | 7 | matches (4 + 3) — a **75 % increase** in wallets' coverage, which is itself the measure of how thin its floor is |
| 3 | `matriz-client` | 0 | **430 passed** | 430 | matches (427 + 3) |
| 4 | `iol-client` | 0 | **250 passed** | 248 | **+2 — explained below** |
| 5 | `ambito-financiero-client` | 0 | **203 passed**, 1 deselected | 203 | matches (200 + 3) |
| 6 | `market-data-client` | 0 | **578 passed** | 578 | matches (573 + 3 + 2) |

**Aggregate:** `uv run pytest packages -q` → **1707 passed, 1 deselected**, 0 failed, 0 skipped, 0 xfailed.

**The iol reconciliation.** The plan's per-package expectation of 248 disagrees with the plan's own total derivation in the same paragraph: "the Wave 0 baseline of 1682 plus 3 parity tests per package, plus 5 surface-gate RED tests in iol and 2 boundary RED tests in market-data" = 1682 + 18 + 5 + 2 = **1707**. iol's share of that is 242 + 3 + 5 = **250**, not 248, and the measured workspace total is exactly 1707. The plan's per-package figure is a two-off arithmetic slip; the measurement, the plan's own total and the arithmetic all agree at 250. Treated as a reconciliation, as the plan instructed, not as a failure to force.

### `test` job — py3.13 leg

`uv` had **CPython 3.13.12** provisioned (`cpython-3.13.12-macos-aarch64-none`). Following the Plan 32-01 pattern, an **isolated** environment was provisioned via `UV_PROJECT_ENVIRONMENT` pointing **outside** the repository, so the tracked tree and the default `.venv` were never traded away. Verified before running: `sys.prefix` is the scratch path, `sys.version_info[:2] == (3, 13)`, and `iol_client.__file__` resolves to the workspace source.

| # | Package | Exit | Result |
|---|---------|------|--------|
| 1 | `higyrus-client` | 0 | 239 passed |
| 2 | `wallets-client` | 0 | 7 passed |
| 3 | `matriz-client` | 0 | 430 passed |
| 4 | `iol-client` | 0 | 250 passed |
| 5 | `ambito-financiero-client` | 0 | 203 passed, 1 deselected |
| 6 | `market-data-client` | 0 | 578 passed |

**All twelve `test` matrix legs reproduced locally: 6 packages x 2 interpreters, identical counts on both, 1707 each.** Afterwards `.venv/bin/python -VV` still reports 3.12.13 and `git status --porcelain -- uv.lock pyproject.toml` is empty — the isolated env cost the tracked tree nothing.

### Legs that could NOT be reproduced locally — named, not assumed

**One, and it is the same one every local reproduction has:** the twelve `test` legs on **real GitHub Actions runners** on `ubuntu-latest`. Locally they ran as twelve sequential invocations on macOS/arm64 against one checkout; on CI they are twelve independent jobs on separate Linux runners with `fail-fast: false`. What a local run cannot observe: Linux-vs-macOS behavioural differences, the `astral-sh/setup-uv@v3` cache path, the coverage upload step, and job-level isolation.

That gap is exactly what this plan's `<human-check>` covers, and it is **not** claimed as satisfied here. Criterion 5 is answered as: *every job and every leg reproduced green locally with all three gates active; the real-runner observation remains an open human-check to be performed after the branch is pushed.*

### `git status --porcelain` at the end of Task 3

Scoped to everything Task 3 could have touched — `packages/`, `tools/`, `.github/`, `pyproject.toml`, `verification/`, `uv.lock` — it is **empty**. The unscoped command is not literally empty: it lists five untracked paths (`.gsd/` and four `.planning/research/.cache/*.json`) that were **already present in the working tree before this plan's first command** and belong to GSD tooling, not to this plan. Recorded rather than quietly re-scoped.

## The `verification/` `probe_login_sync` carry-forward debt — re-checked before the green claim

Plans 32-01, 32-02, 32-04 and 32-05 each carried this forward with the instruction that **32-06 must re-check it before claiming a full-matrix green**. Done, and the finding is sharper than the carry-forward text:

- **Still open.** `main_matriz.py:486` declares `def probe_login_sync(client: Client) -> ProbeResult`. `verification/test_main_matriz_login_fail_uniformity.py` calls `main_matriz.probe_login_sync()` at lines 53 and 78. Measured: `uv run pytest verification/test_main_matriz_login_fail_uniformity.py -q` → **2 failed, 2 errors**, `TypeError`.
- **Localised.** A static census (`grep -rn "probe_login_sync()" verification/`) finds **exactly two call sites, both in that one file**. The "19 failed + 19 errors" figure carried since 32-01 came from a *full* local `pytest` run and bundled other causes; the portion attributable to this signature drift is 2 + 2.
- **Invisible to CI, confirmed by measurement not by argument.** `uv run pytest packages/matriz-client --collect-only -q | grep -c "verification/"` returns **0**. The `test` job passes an explicit `packages/${{ matrix.package }}` path that overrides `testpaths = ["packages", "tests", "verification"]`, so none of the twelve legs collects this file. The full-matrix green claim above is therefore unaffected by this debt, and the claim does not depend on the debt being fixed.
- **Why it was not measured with a full `pytest verification` run.** That run was started and did **not terminate within ten minutes**; it was stopped. Those probes reach live services. This is itself further evidence for the standing conclusion that `verification/` is not a CI-runnable surface — it is not merely *not collected*, it is not *runnable* unattended. Recorded as an observation, not as a new decision.
- **Still deferred.** Fixing it is out of this plan's scope (`files_modified` names five test files and one tools file); it belongs with the six-roster `verification/` debt D-12 defers, listed by path in `32-05-SUMMARY.md`.

## The five ROADMAP success criteria, answered individually

### Criterion 1 — the stdlib-AST-only surface gate, running in real CI

**Satisfied.** `tools/check_surface_types.py` (Plan 32-02) walks the `__all__` of all six packages with `ast` only, imports nothing, and fails on any exported function whose return annotation is `Any`/`dict[str, Any]` **or absent**. Measured this run: `6 packages, 178 __all__ names, 319 definitions scanned, 23 exempted (dunder 13, private-helper 1, serialize-out 9), 0 violations`, exit 0. The DT-06 exemptions are explicit and counted as absorbed *hits*, so the number stays comparable with RESEARCH's 22.

**D-05 resolution, recorded explicitly so no future reader mistakes it for an unresolved contradiction.** `ROADMAP.md:25` and `REQUIREMENTS.md`'s GATE-TYP-01 text both say **"job de CI nuevo"**. The delivered form is a **step in the existing `lint` job** (`.github/workflows/ci.yml:61-66`). This is not a shortfall: Phase 31's **locked D-12** fixes the pattern for cross-package gates as "step en `lint`", and a **D-lock outranks roadmap-summary prose**. The two sibling gates (`check_decode_intactness.py`, `check_uniform_structure.py`) already live there. The load-bearing half of the roadmap's wording — *"`verification/` nunca corrió en CI"* — is fully honoured: the gate does not live under `verification/`, and it does run on every push. Adding a step also does **not rename the `lint` job**, which is what closes RESEARCH assumption A2 without touching branch protection. The resolution is recorded in three places besides this one: the gate's own docstring, the `ci.yml` step comment (`D-05: step en lint, NO job nuevo`), and `32-02-SUMMARY.md`.

### Criterion 2 — the surface gate is non-vacuous, proven by a RED fixture

**Satisfied.** `packages/iol-client/tests/test_surface_types_red.py` (Plan 32-02) builds a tree carrying a deliberate `dict[str, Any]` return and asserts the gate **fails** on it, plus asserts the exemption taxonomy of a tree deliberately full of exempt hits. It runs in the 6x2 matrix (it is one of the 5 tests that take iol from 242 to 250 with the parity file), not as a manual demonstration recorded in prose. Verified this run inside iol's 250 passing.

### Criterion 3 — non-vacuous sync/async parity by introspection, in-package, with lower bounds

**Satisfied, and this plan is what completes it.** The helper (Plan 32-04) derives public names from `dir()` + `__module__` at **runtime**, never from `__all__` — decisive, because four of six `client.py` and three of six `aio.py` have no `__all__`, so an `__all__`-based test would pass vacuously across half the monorepo. It compares **resolved** `get_type_hints()` (not `__annotations__`, which every module in this repo renders as strings via `from __future__ import annotations`) through four numbered rules, and asserts per-package integer floors on **both** the surface size and the number of callables actually compared.

This plan fans it to the remaining five:

| Package | Module axis | Class axis | Floor (class-exclusive) |
|---------|-------------|-----------|-------------------------|
| `ambito_financiero_client` | pass | pass (3/3 methods) | (2, 3) |
| `iol_client` | pass | pass (7/7) | (6, 7) |
| `higyrus_client` | pass | pass (8/8) | (7, 8) |
| `matriz_client` | pass | pass (23/23) | (22, 23) |
| `market_data_client` | pass (32-04) | pass | (19, 20) |
| `wallets_client` | pass | **absence asserted** | (1, 2), near-vacuous by construction |

**No package skipped, no axis skipped.** `grep -c 'pytest.skip\|mark.skip\|mark.xfail'` returns **0** for every one of the six files, and the wallets absence test contains an `ast.Assert` and **no** `ast.Return` (asserted by the plan's own AST criterion). The floors are six per-package literals; `_bounds_for` raises for an unknown package rather than defaulting, so a seventh package cannot be silently asserted against another's floor. The Phase 15 WR-01/WR-02 failure mode — a guard that returns early and therefore asserts nothing — is closed by construction and by measurement.

### Criterion 4 — D-16 closed atomically across the four enrollment lists

**Satisfied by Plan 32-05, and its atomicity holds.** The four lists: mypy `files` (`pyproject.toml:97` — the one real gap, `packages/market-data-client/src` added, 62 → **75** source files, zero fixes required); import-linter `root_packages` (already correct, deliberately **not** edited per D-01); the `ci.yml` mypy-tests loop (already complete at six); and `verification/test_public_surface._PACKAGES` (held at four with an inline comment, per D-11). The `market_data_client._core` contract is **RED-proven** by `packages/market-data-client/tests/test_core_boundary_red.py`, which observed it `BROKEN` under a deliberate violation and restored the file with an asserted byte-equality plus a green re-run.

**Atomicity note, as required.** The reconciliation landed **atomically in Plan 32-05 Task 1**, commit `461b8d1`, containing exactly three files: `pyproject.toml`, `verification/test_public_surface.py`, `tools/check_decode_intactness.py`. Task 2's RED fixture landed separately in `f72b766` and **cannot** break criterion 4's atomicity, because atomicity is the property that the four enrollment lists are never observably inconsistent with one another between commits — and the RED fixture touches none of them.

**The deferred rosters, listed by path** (D-12; recorded so the deferral is documented, not an omission):

- `verification/test_async_cancellation.py`
- `verification/test_logging_no_token_leak.py`
- `verification/test_max_retries_validation.py`
- `verification/test_findings_dedupe_by_title.py`
- `verification/test_async_configure_resource_warning.py` — notable because Plan 32-04 made market-data emit exactly the `ResourceWarning` its three-package roster tests for, and the roster was still deliberately not touched
- `verification/test_sync_async_isolation.py`
- `tools/check_decode_intactness.py` — the `IN_SCOPE_PACKAGES` / `EXEMPT_PACKAGES` **membership** tuples (only the wallets `resolved_by` string changed in 32-05; no membership moved)

### Criterion 5 — the full CI matrix green with the new gates active

**Answered by the full local reproduction above, with its one gap named rather than elided.** Four jobs reproduced: `lint` (9/9 steps exit 0, including all three `tools/` gates), `pre-commit` (9/9 hooks passed), `typecheck` (global mypy at 75 files plus six per-package greens), `test` (six packages x two interpreters, 1707 passing each, 0 failed). The three gates the phase added — `check_surface_types.py`, the parity suite, the import-linter RED fixture — were all **active** during that reproduction, not disabled for it.

The one thing a local run cannot prove is the twelve legs executing on real GitHub Actions runners; that is the `<human-check>`, and it stays open. Criterion 5 is therefore **locally proven, pending real-runner confirmation** — stated that way deliberately rather than as an unqualified green.

## VALIDATION.md plan-numbering reconciliation

`32-VALIDATION.md` numbers its plans **00-04** while this plan set numbers **32-01 … 32-06**. The offset is not uniform, because Plan 32-03 (the `checkpoint:decision` on D-09) produced no artifact and so has no VALIDATION row:

| VALIDATION plan | Task IDs | This plan set | Subject |
|---|---|---|---|
| 00 | `32-00-01` | **32-01** | Wave 0 — 33 pre-existing mypy errors, CI-green baseline |
| 01 | `32-01-01/02/03` | **32-02** | Surface AST gate + `lint` step + RED fixture |
| — | *(none)* | **32-03** | D-09 decision checkpoint — no artifact, no row |
| 02 | `32-02-01/02/03` | **32-04** | Parity helper + market-data pilot + the D-09 fix |
| 03 | `32-03-01/02/03` | **32-05** | D-16 atomic reconciliation + import-linter RED proof |
| 04 | `32-04-01` | **32-06** | Full CI matrix green (this plan) |

Note that VALIDATION's `32-02-02` — *"wallets' missing `Client` on async side is asserted explicitly, not silently skipped"* — is scoped there to VALIDATION plan 02 (this set's 32-04), but the artifact it names, `packages/wallets-client/tests/test_surface_parity.py`, is delivered **here** in 32-06 Task 2. Plan 32-04 delivered the *mechanism* (`CLASS_AXIS_ABSENT` plus an `assert_class_parity` that refuses to pass vacuously); 32-06 delivers the *file*. Recorded so the two artifacts reconcile without a reader concluding a row went unmet.

The plan's own framing — "the wave indices are the same but the plan numbering differs by one" — holds for VALIDATION 00→32-01 and 01→32-02 and then widens to two from VALIDATION 02 onward, for the reason above.

## Verification evidence

| Check | Result |
|-------|--------|
| `uv run pytest packages/*/tests/test_surface_parity.py -q` (Task 1's four) | **12 passed**, 0 failed, 0 skipped — first run |
| `uv run pytest packages/wallets-client/tests/test_surface_parity.py -q` | **3 passed**, 0 failed, 0 skipped |
| Every parity file has exactly 3 tests, all `-> None` (AST) | **OK** for all four Task-1 files |
| `grep -c 'pytest.skip\|mark.skip\|mark.xfail'` per file | **0** on all six |
| wallets absence test: has `ast.Assert`, has no `ast.Return` (AST) | **OK** |
| **Absence test is non-vacuous** — inject `client.Client`, re-run | **FAILS** at line 98 with the actionable message |
| `ls packages/*/tests/test_surface_parity.py \| wc -l` | **6** |
| `git diff HEAD~1 -- tools/surface_parity.py` after Task 1 | **0 lines** — helper byte-unchanged |
| `uv run pytest packages/wallets-client -q` | **7 passed** (4 pre-existing + 3 new) |
| `uv run ruff check . && uv run ruff format --check .` | exit 0 — 241 files formatted |
| `uv run mypy` | exit 0 — **75 source files** |
| Per-package `uv run mypy packages/<pkg>/tests` x 6 | exit 0 x 6 |
| Helper enrolled in strict mypy (verified via `-v`) | **OK** — `Metadata fresh for tools.surface_parity` |
| `uv run pytest packages -q` | **1707 passed**, 1 deselected, 0 failed |
| py3.13 leg, all six packages | **1707 passed** total, 0 failed |
| `uv run pre-commit run --all-files` | exit 0 — 9/9 hooks |
| `uv run lint-imports` | exit 0 — **5 kept, 0 broken** |
| `check_surface_types.py` / `check_uniform_structure.py` / `check_decode_intactness.py` | exit 0 x 3; decode digest `ac14868282ad0a5c` unchanged |
| `uv lock --check` | exit 0 — `Resolved 48 packages` |
| `git status --porcelain -- packages/ tools/ .github/ pyproject.toml verification/ uv.lock` after Task 3 | **empty** |
| No file deletions in either commit | **OK** (`git diff --diff-filter=D` empty on both) |
| Default `.venv` still 3.12.13 after the 3.13 leg | **OK** |

## Normalization rule added

**None.** `tools/surface_parity.py` is byte-unchanged by this plan. No rule was added to the numbered table, no `MODULE_LOWER_BOUNDS` entry was adjusted, no comparison was narrowed, and no package was excluded. All eighteen assertions across six packages passed on their first run against the floors 32-04 measured. This section exists because the plan's acceptance criteria require it to exist *if* the helper changed; it is here recording that it did not.

## Decisions Made

1. **The wallets absence is asserted on two independent paths.** The plan prescribed a `hasattr` assertion (the Check D shape); 32-04's SUMMARY anticipated a `class_parity_report(...).axis == CLASS_AXIS_ABSENT` assertion (the marked-absent report it built for exactly this caller). Both are in the one test. `hasattr` is the direct structural fact and produces the clearest failure; the report check ties the file to the helper's own notion of absence, so if a future refactor changed what `CLASS_AXIS_ABSENT` means, the file notices. Either alone is a single point of staleness.
2. **The absence test's failure messages say what a failure *means*, not what it *is*.** "wallets_client.client ganó un `Client`" is followed by the two actions the failure demands: swap the absence assertion for `assert_class_parity('wallets_client')`, and re-examine wallets' exclusion from import-linter `root_packages` (D-10), whose stated reason was precisely that wallets has no `_core.py` and no class-based surface. A future reader hitting this red does not have to reconstruct the argument.
3. **Non-vacuity of the absence test was proven in-process, not by mutating a tracked file.** `c.Client = type("Client", (), {})` before invoking pytest programmatically reproduces exactly the future the test guards against, with zero risk of leaving the tree dirty. 32-05's import-linter RED fixture had to write to disk because `lint-imports` reads source statically; this one does not, so it should not.
4. **The iol count discrepancy was reconciled, not forced.** The plan said 248, the measurement said 250, and the plan's own total derivation said 1707 — which requires 250. The plan explicitly framed the counts as "reconciliation targets, not assertions; a mismatch is a signal to explain". Explained above.
5. **The `verification/` debt was measured statically plus one targeted file, after the full run was stopped at ten minutes.** A full `pytest verification` would be the more complete measurement, but it does not terminate unattended because those probes reach live services — and running live probes was neither in this plan's scope nor safe to leave running. The static census gives an exact, attributable site count (2), which is what the green claim actually needs.
6. **GATE-TYP-01 is marked complete here.** Plans 32-01, 32-02, 32-04 and 32-05 each recorded, in the same words, that marking the requirement complete before the phase's scope was delivered would flip the traceability table for work that had not happened, and each named 32-06 as the owner of the close. All five criteria are now answered — four fully, criterion 5 locally with its real-runner gap named — so the close happens here as designed.

## Deviations from Plan

**None — plan executed exactly as written.** No deviation rule fired: no bug was auto-fixed, no missing critical functionality was added, no blocker required a workaround, and no architectural change arose. **Zero packages were installed** (T-32-SC honoured; `uv lock --check` green and `uv.lock` byte-unchanged).

Four things worth flagging that are **not** deviations:

1. **One mechanical `ruff` repair during Task 2, pre-commit.** `I001` — the import block needed a blank line between the `tools.surface_parity` import and the `wallets_client` import (ruff classifies them into different sections; the other five files import only from `tools`). Fixed with `ruff check --fix`. No behaviour change, landed inside Task 2's own commit.
2. **The plan's iol expectation of 248 vs the measured 250.** A reconciliation, handled as the plan's own text instructs, not a deviation. Detailed above.
3. **Task 3 produced no commit,** by its own instruction ("Modify no source in this task"), verified by an empty scoped `git status --porcelain`.
4. **Two files listed in Task 3's `<files>`** (`wallets`/`matriz` parity tests) were **re-verified, not edited** — that is what the plan says they are listed for.

---

**Total deviations:** 0
**Impact on plan:** None. Scope held exactly to the five named test files; `tools/surface_parity.py` appeared in `files_modified` as a contingency and the contingency was not needed.

## Deferred debt (recorded, not silenced)

- **`verification/test_main_matriz_login_fail_uniformity.py:53,78`** — 2 call sites of `probe_login_sync()` with the pre-15-05 arity; `main_matriz.py:486` requires `client: Client`. Measured 2 failed + 2 errors. Invisible to all twelve CI legs (measured: 0 `verification/` items collected under a per-package path). **Re-checked as this plan was required to, and still deferred.**
- **The six `verification/` package rosters + the `check_decode_intactness.py` membership tuples** — D-12's deferral, listed by path under criterion 4 above. Unchanged by this plan.
- **`verification/` is not merely CI-invisible, it is not unattended-runnable.** A full `pytest verification` did not terminate in ten minutes because those probes reach live services. Worth a future decision about whether that directory should be split into an offline half (which could then be gated) and a live half.
- **`CLAUDE.md`'s architecture section is stale** — it states "**No async support in matriz:** `matriz_client` has no `aio.py`". `packages/matriz-client/src/matriz_client/aio.py` exists (Phase 10 REFAC-04) with a full `AsyncClient`, and matriz is green on both parity axes with 22 callables compared. Carried forward from `32-04-SUMMARY.md`, now also recorded in `packages/matriz-client/tests/test_surface_parity.py`'s own docstring so it is contradicted at the point of the claim. A `/gsd-docs-update` pass should fix the doc.
- **`REQUIREMENTS.md` § Traceability has never been maintained.** Marking GATE-TYP-01 complete surfaced that the table's other rows are all still `Pending`, including `DEC-01` (Phase 29, complete), `TYP-01` (Phase 30, complete) and `TYP-02`/`TYP-03` (Phase 31, complete) — the checkbox list above the table is accurate, the table below it is not. **Only the GATE-TYP-01 row was updated**, because the other four are prior phases' bookkeeping and fixing them here would be exactly the "arreglado de paso" D-12 forbids. Recorded by name so a future `/gsd-health` or milestone audit can close them together.
- **Phase 34 changelog:** `market-data-client` (published v0.4.0) gains a public keyword-only parameter with a default from Plan 32-04. Purely additive, not source-breaking → **minor-worthy**, never a major. Carried forward from `32-03-SUMMARY.md` / `32-04-SUMMARY.md`.

## Known Stubs

**None.** No hardcoded empty return, no placeholder text, no TODO/FIXME, no early return, no conditional no-op, and no component awaiting a data source. Every symbol this plan's artifact list names is implemented and exercised. The construct most at risk of being a stub — wallets' class-axis test, which the plan explicitly warns could be written as a vacuous pass — is proven real by an AST assertion (`Assert` present, `Return` absent), by a grep for skip markers returning 0, and by an in-process injection that makes it fail.

## Threat mitigations applied

| Threat | Disposition | Mitigation as built |
|--------|-------------|--------------------|
| T-32-25 (a package passing the parity axis vacuously) | mitigate | wallets asserts its class-pair absence positively on two independent paths; 0 skip/xfail markers across all six files; no `ast.Return` in the absence test; all six packages carry a parity file; non-vacuity demonstrated by injection |
| T-32-26 (a green claim covering less than the full matrix) | mitigate | Every command recorded with its exit status; the one unreproduced leg (real GitHub Actions runners) is named explicitly and criterion 5 is stated as "locally proven, pending real-runner confirmation" rather than as an unqualified green |
| T-32-27 (weakening the helper to turn a package green) | mitigate | `git diff HEAD~1 -- tools/surface_parity.py` = 0 lines; a `Normalization rule added` section exists and records that no rule was added |
| T-32-28 (info disclosure via parity failure messages) | mitigate | The helper renders symbol names and resolved *type* strings only — type-not-value by construction. wallets' new messages name modules, attribute names and a decision ID; no value, no environment, no credential. The per-package SEC-01 caplog sentinels were re-run inside the 1707 |
| T-32-29 (`load_dotenv()` executed by six packages' imports) | accept | Already true of every existing package test; the helper reads only `__module__`, `dir()` and resolved hints and never touches `os.environ`. Accepted as the plan declares |
| T-32-SC (package-manager installs) | accept | **Zero installs.** `uv lock --check` exit 0 as the first `lint` step; `uv.lock` byte-unchanged; the 3.13 environment was provisioned `--frozen` from the existing lock |

## Threat Flags

**None.** No new security-relevant surface appeared: no network endpoint, no auth path, no file access pattern, no schema change at a trust boundary. The five new files are test-only, import-only, and assert on type metadata.

## Issues Encountered

- **None blocking.** The single friction point was the Task 2 `I001` import-sort finding, fixed before that task's commit.
- **The full `pytest verification` run had to be stopped.** It exceeded ten minutes because those probes reach live services. Handled by measuring the debt statically plus one targeted file run; the background process was terminated and left the tree clean (`git status` on source paths empty afterwards).
- **`timeout(1)` is not available on this macOS shell**, so the targeted verification run was executed without a wall-clock guard. It completed in 0.04 s, so no guard was needed.

## User Setup Required

None. Every command in this plan is offline — no credential, no `.env` value and no network call was made by any command whose result is recorded here. The parity helper *does* import package modules, which executes each package's module-level `load_dotenv()`, but it reads only `__module__`, `dir()` and resolved type hints; no environment value is read, rendered or asserted on. (The one command that *would* have reached live services — the full `pytest verification` run — was stopped and its result is not relied on.)

## Next Phase Readiness

**Ready. Phase 32 is complete and GATE-TYP-01 is closed.**

Phase 33 (live verification in strict mode) inherits:

- **A suite at 1707 passing** on both Python 3.12 and 3.13, 0 failed, 1 deselected (pre-existing ambito marker config).
- **Six parity nets that will redden on the first sync/async divergence** any Phase 33 fix introduces. This matters concretely: CLAUDE.md's "Dual sync/async" constraint says a logic fix must be mirrored in both surfaces, and Phase 33 exists to make in-cycle fixes. Until now that constraint was prose; it is now a gate. A fix applied to `client.py` and forgotten in `aio.py` is a red test, not a consumer's discovery.
- **All five gates green:** `check_surface_types.py` (0 violations), `check_decode_intactness.py` (digest `ac14868282ad0a5c`), `check_uniform_structure.py`, `lint-imports` (5 kept, 0 broken), and the six-package parity suite.
- **mypy at 75 src source files** across all six packages — new package source is type-checked by default rather than by enrollment.
- **The Phase 29 sizing floors** (`higyrus ≥ 22`, `matriz ≥ 24`, `market-data ≥ 50`) as Phase 33's declared divergence budget, unchanged by this phase.

**Two things Phase 33 should carry:**

1. **The `<human-check>` is still open.** Before Phase 32 is considered closed on a real runner: `gh run list --workflow=ci.yml --limit 1` then `gh run view <id>` — confirm four jobs and twelve `test` legs green, confirm the `lint` job shows the new `surface-types` step and it passed, and confirm no branch-protection required status check name changed (RESEARCH A2 — adding a step should not rename the `lint` job).
2. **If a seventh package is ever added,** it must gain an entry in `MODULE_LOWER_BOUNDS` before any parity assertion runs for it — `_bounds_for` raises with an explicit message rather than defaulting, so it cannot be silently asserted against another package's floor.

## Self-Check: PASSED

- `packages/ambito-financiero-client/tests/test_surface_parity.py` — FOUND
- `packages/iol-client/tests/test_surface_parity.py` — FOUND
- `packages/higyrus-client/tests/test_surface_parity.py` — FOUND
- `packages/matriz-client/tests/test_surface_parity.py` — FOUND
- `packages/wallets-client/tests/test_surface_parity.py` — FOUND
- Commit `fa215e0` — present in git history
- Commit `10fd60d` — present in git history
- `key_links` verified: all six files match `from tools\.surface_parity import`; the wallets file matches `hasattr` against both `wallets_client.client` and `wallets_client.aio`; `.github/workflows/ci.yml`'s `test` job collects `packages/<pkg>` and therefore these files in all twelve legs

---
*Phase: 32-gates-de-homogeneidad-d-16*
*Completed: 2026-08-25*
