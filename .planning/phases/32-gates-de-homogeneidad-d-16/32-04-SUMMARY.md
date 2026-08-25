---
phase: 32-gates-de-homogeneidad-d-16
plan: 04
subsystem: tooling
tags: [sync-async-parity, runtime-introspection, get-type-hints, normalization-table, non-vacuity, tdd, market-data-client, resource-warning]

# Dependency graph
requires:
  - phase: 32-gates-de-homogeneidad-d-16
    plan: 02
    provides: "The `tools/` cross-package gate precedent (D-05 step-en-lint, the docstring section shape) and the 1687-passing baseline any new red is measured against"
  - phase: 32-gates-de-homogeneidad-d-16
    plan: 03
    provides: "The recorded D-09 disposition — option-a, auto-resolved — which authorises editing the published `configure` signature of market-data-client"
  - phase: 31-endpoints-de-ops-estructura-uniforme
    provides: "D-12: the three-package roster of verification/test_async_configure_resource_warning.py stays untouched even though this plan makes market-data emit a ResourceWarning"
provides:
  - "tools/surface_parity.py — the shared runtime-introspection parity walker (D-07), with the metric stated exactly once, a four-rule normalization table, per-package integer lower bounds and two comparison axes"
  - "The affirmative substitute for the twice-abandoned codegen requirement (DT-04 / REFAC-06): divergence is no longer impossible, but it is impossible to keep"
  - "packages/market-data-client/tests/test_surface_parity.py — the pilot that RED-proved D-09 and is the template Plan 32-06 fans out to the other five packages"
  - "The D-09 fix: market_data_client.aio.configure accepts and threads http_client, closing the last sync/async hint divergence in the monorepo"
  - "Measured ground truth: 0 name-set divergences and 0 hint divergences across all six packages on both axes, after the four rules"
affects: [32-05, 32-06, 34-publish, phase-33-live-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Runtime-introspection gate as an importable helper, deliberately NOT a lint-job script: `typing.get_type_hints` must import both surfaces to resolve PEP-563 strings, which an AST gate structurally cannot do"
    - "Metric stated once, both columns derived (Pitfall 4): class-INCLUSIVE names drive the comparison, class-EXCLUSIVE counts drive the bounds, and only the latter is ever pinned as integers"
    - "Marked-absent report instead of a silent skip: `class_parity_report` returns `axis == CLASS_AXIS_ABSENT` for a package with no Client pair, and `assert_class_parity` RAISES on it rather than passing vacuously"
    - "Resolution failures propagate rather than skip — a swallowed `get_type_hints` error empties the comparison, which is the exact vacuity the phase exists to prevent"

key-files:
  created:
    - "tools/surface_parity.py"
    - "packages/market-data-client/tests/test_surface_parity.py"
    - ".planning/phases/32-gates-de-homogeneidad-d-16/32-04-SUMMARY.md"
  modified:
    - "packages/market-data-client/src/market_data_client/aio.py"

key-decisions:
  - "32-04: `assert_class_parity` RAISES for a package with no Client/AsyncClient pair rather than passing vacuously; the absence must be asserted explicitly via `class_parity_report` + `CLASS_AXIS_ABSENT`. RESEARCH requires wallets be skipped 'with a stated reason, not silently' — a helper that returns green for a package it never examined is the Phase 15 WR-01/WR-02 failure mode with a new name"
  - "32-04: `ParityReport.sync_count`/`async_count` carry the CLASS-EXCLUSIVE counts on the module axis, so they are directly comparable to MODULE_LOWER_BOUNDS without a second conversion step. This is the structural fix for Pitfall 4 — one metric, one table, both columns derived"
  - "32-04: the class axis compares the FULL non-underscore member set (callable or not) and narrows to callables only for the hint comparison. A public non-callable attribute present on one surface and absent on the other is drift regardless of whether it can be called (measured: zero such attributes today, so this costs nothing and closes a hole)"
  - "32-04: rule 1 is applied to the RENDERED hint string via a word-boundary regex, not to the resolved type object. Rendering first gives a stable, human-readable failure message ('sync declares httpx.Client | None, async declares <MISSING>') and makes the rewrite a one-line, auditable substitution"
  - "32-04: the D-09 block does NOT set `rotated`. A transport swap is not a credential rotation and must not invalidate the cached Auth0 token — verified against client.py:820-824, where the sync surface does the same"

patterns-established:
  - "A cross-surface gate records its sanctioned differences as a NUMBERED table in the module docstring, carrying check_decode_intactness.py's framing paragraph verbatim: the fix for a red gate is to revert the drift or add a rule with a stated reason, never to weaken the check"
  - "The count of things actually compared (`compared_hints`) is asserted against the same per-package floor as the surface size — a comparison that examined nothing agrees with everything"

requirements-completed: []

# Metrics
duration: 7min
completed: 2026-08-25
status: complete
---

# Phase 32 Plan 04: sync/async parity helper + market-data D-09 pilot Summary

**A shared runtime-introspection walker that derives public names from `dir()`/`__module__` rather than `__all__`, compares resolved `get_type_hints()` through a four-rule normalization table, and asserts per-package integer floors on both the surface size and the comparison size — it found exactly one real divergence in the monorepo on its first run, that divergence was demonstrated as a failing test, and it was closed in source without a single test or rule being edited.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-08-25T21:21:40Z
- **Completed:** 2026-08-25T21:28:49Z
- **Tasks:** 2 (both `tdd`)
- **Files created/modified:** 3 (2 new, 1 modified)

## Accomplishments

- **Criterion 3 of Phase 32 has apparatus, and the apparatus is non-vacuous.** Public names come from runtime introspection, hints from `typing.get_type_hints`, and both the name comparison and the size floors derive from a metric stated exactly once.
- **The design constraint the plan was built around was confirmed, not assumed.** A naive comparison is red in **all six** packages; rule 1 alone dissolves five of the six divergences, leaving market-data's genuine defect as the only red. Measured before writing a line of the helper.
- **The RED was precisely one failing assertion out of three**, with a message that reads as a bug report rather than as a diff.
- **The gate found a defect that the code was actively denying.** `aio.py`'s docstring asserted its semantics "ESPEJA exactamente la superficie sync `client.configure`" while missing a parameter that surface has. This is the first automated detection of that divergence.
- **`tools/surface_parity.py` is enrolled in strict mypy by construction.** `uv run mypy packages/market-data-client/tests` went from 27 to **28 source files** — the helper is pulled into the per-package strict loop by the pilot's import, exactly as Plan 32-02 measured for `check_surface_types.py`.

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): parity helper + market-data pilot** — `05717b9` (test)
2. **Task 2 (GREEN): thread `http_client` through `aio.configure` (D-09)** — `2eb8748` (fix)

## RED observation (Task 1, required verbatim by the plan)

`uv run pytest packages/market-data-client/tests/test_surface_parity.py -q` at commit `05717b9`, before the fix:

```
F..                                                                      [100%]
E       AssertionError: sync/async MODULE parity FAILED for market_data_client (market_data_client.client vs market_data_client.aio):
E         configure(): parameter 'http_client' differs -- sync declares httpx.Client | None, async declares <MISSING>
E         [compared 19 callable(s); sync=19, async=20]
E         Fix this by reverting the drift, or by adding a rule with a stated reason to the
E         numbered table in tools/surface_parity.py's `THE NORMALIZATION` docstring section.
E         Never by weakening the comparison, lowering a bound, or excluding a package.

1 failed, 2 passed in 0.02s
```

**Exactly one failing assertion out of three**, and it names the function, the parameter and both sides' declarations. The two passing tests — the class axis and the lower bounds — are what prove the failure is a real divergence rather than a broken helper: the same walker that reports this red also reports `Client`/`AsyncClient` in agreement and both surfaces above their floors, in the same run.

This is the first automated detection of a divergence that the async docstring at `aio.py:797-798` had been denying in prose since the surface was written.

`git diff HEAD~1 -- packages/market-data-client/tests/test_surface_parity.py tools/surface_parity.py` returned **0 lines** after the GREEN commit: the drift was closed in source. No assertion was relaxed, no bound lowered, no rule added to accommodate the defect, and no package excluded.

## Measured ground truth (the helper's own output, re-verified before implementation)

Module axis, class-inclusive name sets after rules 2 and 3, and resolved-hint comparison:

| Package | client incl / excl | aio incl / excl | sync-only | async-only | compared | hint mismatches |
|---------|---:|---:|---|---|---:|---|
| `ambito_financiero_client` | 3 / 2 | 4 / 3 | — | — | 2 | 0 |
| `iol_client` | 7 / 6 | 8 / 7 | — | — | 6 | 0 |
| `higyrus_client` | 8 / 7 | 9 / 8 | — | — | 7 | 0 |
| `matriz_client` | 23 / 22 | 24 / 23 | — | — | 22 | 0 |
| `market_data_client` | 20 / 19 | 21 / 20 | — | — | 19 | **1 (D-09)** → 0 after Task 2 |
| `wallets_client` | 1 / 1 | 2 / 2 | — | — | 1 | 0 |

The class-exclusive columns reproduce D-08's integers exactly, and `compared` equals the class-exclusive sync count in every package — so `compared_hints >= MODULE_LOWER_BOUNDS[pkg][0]` is a tight assertion, not a slack one.

Class axis: all five class-bearing packages have **equal-sized** member sets differing only by `close` ↔ `aclose`, with **zero** hint mismatches. `wallets_client` has no pair at all and is marked, not skipped.

## Verification evidence

| Check | Result |
|-------|--------|
| `uv run pytest packages/market-data-client/tests/test_surface_parity.py -q` (Task 1) | **1 failed, 2 passed** — the RED |
| `uv run pytest packages/market-data-client/tests/test_surface_parity.py -q` (Task 2) | **3 passed, 0 failed** |
| Failure message names `http_client` | grep count **2** (≥1 required) |
| `uv run pytest packages/market-data-client -q` | **576 passed** (573 baseline + the 3 new), 0 failed |
| `uv run pytest packages -q` | **1690 passed**, 1 deselected (1687 baseline + 3) |
| `uv run mypy packages/market-data-client/src` | exit 0 — 13 source files |
| `uv run mypy packages/market-data-client/tests` | exit 0 — **28** source files (was 27; the helper is enrolled) |
| `uv run ruff check .` / `ruff format --check .` | exit 0 — 235 files already formatted |
| Bounds are per-package, 6 entries, wallets `(1, 2)` | **OK** |
| Metric stated once (`class-exclusive` + `class-inclusive` in docstring) | **OK** |
| Four numbered normalization rules in the docstring | **4** |
| Other four packages green on all three assertions | **OK** — `4 packages green` |
| wallets: module axis + bounds green, class axis raises loudly | **OK** |
| Resolved hint is `httpx.AsyncClient \| None` | **OK** |
| AST: `http_client` is a kwonly arg AND `client._state.http_client = http_client` present | **OK** |
| `git diff HEAD~1 -- <test> <helper>` after GREEN | **0 lines** |
| Blast radius: `git diff --stat -- packages/market-data-client/src` | exactly **1 file**, `aio.py`, +28 lines |
| `git status --porcelain -- verification/` | **empty** |
| `uv run python tools/check_surface_types.py` | exit 0 — 6 / 178 / 319 / 23 / **0 violations**, unchanged |
| `tools/check_decode_intactness.py` | green — Checks B/C/D unchanged |
| `tools/check_uniform_structure.py` | green — all 6 packages |
| No file deletions in either commit | **OK** |

## Runtime behaviour of the new parameter (verified, five sub-cases)

The prohibition the plan carried forward from 32-03 is that a public parameter accepted and discarded is a lie in the published surface. Verified in a live process, not just by AST:

1. `configure(base_url=...)` with no `http_client` → `_state.http_client` stays `None` (the sentinel carry-forward contract every other parameter honours).
2. `configure(http_client=c1)` on a fresh state → `_state.http_client is c1`, **no warning**.
3. `configure(http_client=c1)` again with the *same* object → **silent** (the `is not` identity guard).
4. `configure(http_client=c2)` with a *different* live client → exactly **one** `ResourceWarning` naming `await market_data_client.aio.aclose()` as the remedy, then the swap lands.
5. A transport swap does **not** rotate the token: a seeded `token` survives a subsequent `configure(http_client=...)`.

## Files Created/Modified

- **`tools/surface_parity.py`** (new, 512 lines) — stdlib-only (`importlib`, `inspect`, `re`, `typing`, `dataclasses`, `types`). Exports `MODULE_LOWER_BOUNDS`, `ParityReport`, `public_names`, `normalized_hints`, `module_parity_report`, `class_parity_report`, `assert_module_parity`, `assert_class_parity`, `assert_module_lower_bound`, plus the axis labels `MODULE_AXIS` / `CLASS_AXIS` / `CLASS_AXIS_ABSENT`. Four docstring sections in the plan's order: `THE METRIC, STATED ONCE`, `THE NORMALIZATION`, `WHY THIS HELPER IMPORTS PACKAGE MODULES`, `THE LOWER BOUNDS ARE PER-PACKAGE INTEGERS`.
- **`packages/market-data-client/tests/test_surface_parity.py`** (new, 52 lines) — three delegating tests. Docstring states the Patrón 1 import (`pythonpath = ["."]`, `pyproject.toml:109`), why the file lives in-package rather than under CI-invisible `verification/`, and explicitly defers to `test_public_surface_market_data.py::test_sync_async_method_name_parity` as the pre-existing name-only net this file extends with hints, the module axis and bounds.
- **`packages/market-data-client/src/market_data_client/aio.py`** (+28 lines) — one `import warnings`, one keyword-only parameter, one carry-forward block, one docstring paragraph.

## The four normalization rules, as recorded in the helper

1. `httpx.Client` in a sync hint ≡ `httpx.AsyncClient` in the corresponding async hint. **The only hint divergence in five of six packages** — without this rule the suite is red across the board and market-data's real defect is buried.
2. `Client` (sync) ≡ `AsyncClient` (async), at both axes. Structural, uniform across all five class-bearing packages.
3. `aclose` is async-only, `close` is sync-only. At the **module** axis it is a **drop** (no sync module-level `close` shim exists on any surface); at the **class** axis it is a **rename**.
4. Return types need no rule — async functions annotate the awaited type, and no `Coroutine`/`Awaitable` annotation appears anywhere.

The framing paragraph is copied from `tools/check_decode_intactness.py:44-50` with only its subject noun changed, and the file says so.

## Decisions Made

1. **`assert_class_parity` raises for a package with no `Client` pair** rather than passing vacuously. `class_parity_report` returns a report marked `CLASS_AXIS_ABSENT` as the plan requires, so Plan 32-06's wallets test can assert the absence loudly — but the *assert* helper refuses to produce a green for a comparison it never made. RESEARCH's requirement is that wallets be "explicitly skipped with a stated reason, not silently"; a helper that returns green for an unexamined package is that silence with better branding.
2. **`ParityReport.sync_count`/`async_count` are class-EXCLUSIVE on the module axis.** This is the structural fix for Pitfall 4: the bounds table and the report speak the same metric, so `assert_module_lower_bound` is a direct comparison with no conversion step where an off-by-one could re-enter.
3. **The class axis compares the full non-underscore member set, not just callables.** A public non-callable attribute on one surface and not the other is drift. Measured: zero such attributes exist today in any of the five pairs, so the stricter rule costs nothing and closes a hole.
4. **Rule 1 rewrites the rendered string, not the type object.** Rendering first (`module.QualName` for plain classes, `repr` otherwise) makes the failure message read as a declaration rather than as a `<class '...'>` repr, and reduces the rule to a single auditable word-boundary substitution.
5. **The D-09 block does not set `rotated`.** Verified against `client.py:820-824` before writing, as the plan instructed: the sync surface does not set it there either. Swapping a transport is not a credential rotation, and invalidating the cached Auth0 token on a transport swap would be a behaviour change smuggled in under a parity fix.
6. **`http_client` was placed after `token_expires_at` and before `mutating_allowed`**, matching the sync signature's *relative* position. The two signatures still order their other keyword-only parameters differently, and that remains semantically irrelevant — all parameters are keyword-only and `get_type_hints` returns an order-insensitive dict, which is one of the reasons the helper uses it rather than `inspect.signature`. Aligning the position is a readability choice, not a correctness one, and the helper would be green either way.

## Deviations from Plan

**None — plan executed exactly as written.** No deviation rule fired: no bug was auto-fixed outside the task's own scope, no missing critical functionality was added beyond what the plan specified, no blocker required a workaround, and no architectural change arose. No package was installed; the helper is stdlib-only apart from importing the workspace packages themselves.

Three things worth flagging that are **not** deviations:

1. **Two mechanical repairs during Task 1, both pre-commit.** (a) `ruff` flagged RUF002 on a `×` (multiplication sign) in the test docstring, replaced with `x`; (b) `ruff format` reflowed the helper. Neither changed behaviour and both landed inside their own task's commit.
2. **`requirements-completed` is deliberately empty.** All six Phase 32 plans carry `GATE-TYP-01`; this plan delivers criterion 3's apparatus and the pilot, but the fan-out to the other five packages is Plan 32-06's, and criteria 4-5 are unstarted. Marking the requirement complete at plan 4 of 6 would flip the traceability table for work that has not happened. Plan 32-06 owns the close — the same reasoning Plans 32-01 and 32-02 recorded.
3. **The plan's optional branch on D-09 was not taken.** `32-03-SUMMARY.md` records option-a, so Task 1 expected the RED (it did not implement a normalization exception for `configure`) and Task 2 ran. Under option-b, Task 2 would have been dropped.

---

**Total deviations:** 0
**Impact on plan:** None. Scope held exactly to the three named files.

## Deferred debt (recorded, not silenced)

- **`verification/test_async_configure_resource_warning.py:27`** still declares `_ASYNC_PACKAGES = ["ambito_financiero_client", "iol_client", "higyrus_client"]` — three packages, **market-data excluded**. This plan makes `market_data_client.aio.configure` emit exactly the `ResourceWarning` that roster tests for, and the roster was still **not** touched. That is deliberate: enrolling market-data there is one of the ~6 out-of-scope rosters **D-12** defers, and folding it in here would be exactly the "arreglado de paso" the decision forbids. Recorded with its file path so it is documented debt rather than an oversight. Asserted empty: `git status --porcelain -- verification/`.
- **Carry-forward, unchanged from 32-02:** `verification/` matriz probes still call `probe_login_sync()` with the pre-15-05 signature. This plan does not move that needle — the pilot lives under `packages/market-data-client/tests/`, so `verification/` still never executes in CI. Plan 32-06 must re-check that debt before claiming a full-matrix green.
- **Phase 34 changelog:** `market-data-client` (published v0.4.0) gains a public keyword-only parameter with a default. Purely additive, not source-breaking → a **minor-worthy** changelog entry, never a major. Carried forward from `32-03-SUMMARY.md`.

## Known Stubs

**None.** No hardcoded empty return, no placeholder text, no TODO/FIXME, and no symbol accepted-and-discarded. Every symbol the plan's artifact list names is implemented and exercised. The one symbol most at risk of being a stub — the new `http_client` parameter — is proven real by an AST assertion, a resolved-hint assertion and five live-process behavioural sub-cases.

## Threat Flags

None. The plan's `<threat_model>` dispositions were all honoured in implementation:

- **T-32-13** (info disclosure via failure messages): the mismatch renderer emits symbol names and rendered *type* strings only. No parameter value, no environment value, no state contents — type-not-value by construction. The RED message quoted above is the evidence.
- **T-32-15** (a parity test that compares nothing): `assert_module_parity` asserts `compared_hints >= MODULE_LOWER_BOUNDS[package][0]`; `get_type_hints` failures propagate rather than being swallowed; the bounds are per-package integers with an explicit guard that raises for an unknown package rather than defaulting.
- **T-32-16** (a parameter accepted and discarded): closed by both required assertions plus live verification.
- **T-32-17** (connection-pool leak): the `ResourceWarning` fires on replacing a *different* live client and names the remedy.
- **T-32-18** (scope creep into deferred rosters): `verification/` untouched, deferral recorded above with its file path.
- **T-32-14** / **T-32-SC** were `accept` dispositions and remain accepted: the helper's imports do run `load_dotenv()` (unavoidable for runtime introspection, and already true of every package test), and zero packages were installed.

No new security-relevant surface appeared: no network endpoint, no auth path, no file access pattern, no schema change at a trust boundary.

## Issues Encountered

**None blocking.** The two friction points were the RUF002 ambiguous-character lint and the post-write `ruff format` reflow, both resolved inside Task 1 before its commit.

One observation worth recording for a future reader: `CLAUDE.md`'s architecture section states "**No async support in matriz:** `matriz_client` has no `aio.py`". That is **stale** — `packages/matriz-client/src/matriz_client/aio.py` exists (Phase 10+), the parity helper imports it successfully, and matriz is green on both axes with 22 callables compared. The helper's correctness does not depend on that doc being fixed, but the doc is wrong and a `/gsd-docs-update` pass should catch it.

## User Setup Required

None — every command in this plan is offline. No credential, no `.env` value and no network call was involved. The helper *does* import package modules, which executes each package's module-level `load_dotenv()`, but it reads only `__module__`, `dir()` and resolved type hints; no environment value is read, rendered or asserted on.

## Next Phase Readiness

**Ready.** Plan 32-06 inherits a **frozen** helper and a working template:

- The helper is already verified correct for all six packages. `assert_module_parity` / `assert_class_parity` / `assert_module_lower_bound` are green for the four other class-bearing packages *today*, and wallets is green on the module axis and bounds while raising loudly on the class axis.
- The fan-out is a copy of the 52-line pilot with `_PACKAGE` changed, **except for wallets**, whose test must call `class_parity_report("wallets_client")` and assert `axis == CLASS_AXIS_ABSENT` explicitly rather than calling `assert_class_parity` — the helper enforces this by raising.
- Expected suite delta for 32-06: **+15** tests (3 × 5 packages), taking the workspace from 1690 to 1705, assuming wallets keeps three tests with the class one reshaped as an absence assertion.
- The baseline is now **1690 passing**, 1 deselected. `check_surface_types.py` still reports `6 / 178 / 319 / 23 / 0`; `check_decode_intactness.py`'s Check B hash `684191c7cdc5ff9c` and Checks C/D are unchanged.
- Plan 32-06 owns `requirements mark-complete GATE-TYP-01` and the full-matrix green claim, and must still re-check the `verification/` `probe_login_sync` debt first.

**If a future package is added:** it must gain an entry in `MODULE_LOWER_BOUNDS` before any parity assertion will run for it — `_bounds_for` raises with an explicit message rather than defaulting, so a seventh package cannot be silently asserted against another package's floor.

## Self-Check: PASSED

- `tools/surface_parity.py` — FOUND (512 lines, ≥150 required)
- `packages/market-data-client/tests/test_surface_parity.py` — FOUND (52 lines, ≥30 required)
- `packages/market-data-client/src/market_data_client/aio.py` — FOUND (contains `http_client`)
- Commit `05717b9` — FOUND in git history
- Commit `2eb8748` — FOUND in git history
- `key_links` verified: the test imports `from tools.surface_parity import ...`; the helper calls `get_type_hints` on both surfaces via `importlib.import_module`; `aio.configure` assigns `client._state.http_client = http_client`

---
*Phase: 32-gates-de-homogeneidad-d-16*
*Completed: 2026-08-25*
