---
phase: 31-endpoints-de-ops-estructura-uniforme
plan: 02
subsystem: infra
tags: [ci, github-actions, ruff, mypy, stdlib, structural-gate, monorepo-layout]

# Dependency graph
requires:
  - phase: 29-decoder-observable
    provides: "`tools/check_decode_intactness.py` (the `tools/`-script-in-`lint`-job pattern this gate mirrors), `29-WALLETS-EXEMPTION.md`, and the signed `29-DLOCK-RESPONSE-LITERAL.md` that keeps the 5 new `types.py` empty"
  - phase: 30-iol-models
    provides: "`iol_client/models.py` — the reason ámbito and wallets were the only two packages still missing a `models.py`"
provides:
  - "`tools/check_uniform_structure.py` — stdlib-only cross-package existence gate, roster read from disk"
  - "a new `uniform-structure` step in the existing CI `lint` job"
  - "7 docstring-only modules giving all 6 packages the same `models.py` + `types.py` layout"
  - "a dated `## Amendment` on `29-WALLETS-EXEMPTION.md` recording that the exemption is unchanged"
affects: [32-surface-parity, 33-literal-promotion, any-phase-adding-a-package, any-phase-adding-response-models]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Structural CI gate as a stdlib-only `tools/*.py` script wired into the `lint` job, never a pytest file under `verification/`"
    - "On-disk roster enumeration (`packages/` `iterdir`) so a new package is gated automatically rather than silently exempted by omission"
    - "Docstring-only placeholder module carrying `from __future__ import annotations` + `__all__: list[str] = []`"

key-files:
  created:
    - tools/check_uniform_structure.py
    - packages/iol-client/src/iol_client/types.py
    - packages/higyrus-client/src/higyrus_client/types.py
    - packages/market-data-client/src/market_data_client/types.py
    - packages/ambito-financiero-client/src/ambito_financiero_client/types.py
    - packages/ambito-financiero-client/src/ambito_financiero_client/models.py
    - packages/wallets-client/src/wallets_client/types.py
    - packages/wallets-client/src/wallets_client/models.py
    - .planning/phases/31-endpoints-de-ops-estructura-uniforme/deferred-items.md
  modified:
    - .github/workflows/ci.yml
    - packages/ambito-financiero-client/tests/test_decode.py
    - .planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md

key-decisions:
  - "The uniform-structure roster is enumerated from disk, never hardcoded — a seventh package is gated automatically, an unresolvable `src/` root is a problem rather than a skip, and an empty scan is itself a problem, so the gate cannot report green vacuously (T-31-06)"
  - "`wallets-client`'s two new modules contain exactly one import statement each (`from __future__ import annotations`): that package has no `_decode.py`, so a cosmetic `SafeModel` would `ImportError` at package import and redden all 12 wallets CI matrix legs (T-31-07)"
  - "The 5 new `types.py` carry no `Literal` content, citing the signed `29-DLOCK-RESPONSE-LITERAL.md`; iol's `mercado`/`plazo` promotion stays deferred to Phase 33 pending a live census"
  - "The Phase 29 assertion `test_this_package_really_has_no_models_module` was restated rather than deleted or suppressed — the property it guards (ámbito declares no response models and its `models` module pulls in nothing) survives TYP-03; only the file-absence proxy for it did not"
  - "`29-WALLETS-EXEMPTION.md` gains a dated `## Amendment` note; formal supersession stays deferred to the phase that actually closes the exemption, and `tools/check_decode_intactness.py` was not touched"
  - "The 19 pre-existing matriz `verification/` failures and 2 pre-existing ámbito `mypy` test errors were logged to `deferred-items.md`, not fixed — neither is caused by this plan"

patterns-established:
  - "Observed-RED non-vacuity: the structural gate was run and captured failing, naming all 7 missing paths, BEFORE the files that turn it green existed"
  - "Placeholder modules justify their emptiness in their own docstring, citing the decision document by path, so the next reader cannot mistake a decision for an oversight"

requirements-completed: [TYP-03]

# Metrics
duration: 95min
completed: 2026-08-24
status: complete
---

# Phase 31 Plan 02: Estructura uniforme Summary

**A stdlib-only `tools/check_uniform_structure.py` wired into the CI `lint` job, enumerating `packages/` from disk, plus the 7 docstring-only modules that give all 6 packages the same `models.py` + `types.py` layout — observed RED with all 7 paths named, then GREEN.**

## Performance

- **Duration:** ~95 min (dominated by one 15m19s full-suite `pytest` run)
- **Started:** 2026-08-23T23:55:00Z (approx.)
- **Completed:** 2026-08-24T01:30:00Z
- **Tasks:** 2 of 2
- **Files created:** 9 · **Files modified:** 3

## Accomplishments

- All 6 packages now carry both `models.py` and `types.py` under `src/<import_name>/`. The 7 new files are exactly D-09's list: `types.py` in iol, higyrus, market-data, ámbito and wallets; `models.py` in ámbito and wallets.
- The layout is now a **CI-enforced invariant**, not a convention. `tools/check_uniform_structure.py` runs as a new step of the existing `lint` job, mirroring `decode-intactness` including its two-line Spanish rationale comment (D-12).
- The gate's roster comes from disk, so a seventh package entering the workspace is checked automatically — the criterion-4 property that a hardcoded 6-name list could not have delivered.
- Non-vacuity was **observed, not asserted**: the gate was run before the 7 files existed and failed with all 7 paths listed (verbatim output below).
- `tools/check_decode_intactness.py` is green and **byte-unedited**; `verification/snapshots/ambito-financiero-client-surface.txt` is **byte-unchanged**.

## Task Commits

1. **Task 1: RED — stdlib-only uniform-structure gate** — `f1d1cd6` (test)
2. **Task 2: GREEN — the 7 docstring-only modules** — `2bc5dfc` (feat)

_TDD plan: the RED gate and the GREEN files are deliberately distinct commits._

## The RED observation (verbatim, captured at `f1d1cd6`)

```
::error::Phase 31 TYP-03 uniform structure -- uniform structure is incomplete:
    package `ambito-financiero-client` is missing packages/ambito-financiero-client/src/ambito_financiero_client/models.py
    package `ambito-financiero-client` is missing packages/ambito-financiero-client/src/ambito_financiero_client/types.py
    package `higyrus-client` is missing packages/higyrus-client/src/higyrus_client/types.py
    package `iol-client` is missing packages/iol-client/src/iol_client/types.py
    package `market-data-client` is missing packages/market-data-client/src/market_data_client/types.py
    package `wallets-client` is missing packages/wallets-client/src/wallets_client/models.py
    package `wallets-client` is missing packages/wallets-client/src/wallets_client/types.py
::error::uniform-structure gate FAILED (1 of 1 checks)
exit=1
```

All 7 paths, one line each, copy-pasteable. `grep -c 'types.py'` → 5, `grep -c 'models.py'` → 2.

## The GREEN success sentence (at `2bc5dfc`)

```
uniform structure: all 6 packages under `packages/` carry `models.py`, `types.py` in their import root
exit=0
```

## Files Created/Modified

- `tools/check_uniform_structure.py` — the gate. `pathlib` + `sys` only. `_import_root()` resolves `src/<import_name>/` from disk (so `ambito-financiero-client` → `ambito_financiero_client` needs no mapping table); `check_uniform_structure()` accumulates four-space-indented problem lines and raises once; `main()` prints `::error::` to stderr and `raise SystemExit(main())`.
- `.github/workflows/ci.yml` — one new `uniform-structure` step at the end of the existing `lint` job. No new job; `test`, `typecheck` and `pre-commit` untouched.
- `packages/{iol,higyrus,market-data,ambito-financiero,wallets}-client/.../types.py` — docstring-only, `__all__: list[str] = []`.
- `packages/{ambito-financiero,wallets}-client/.../models.py` — docstring-only, `__all__: list[str] = []`.
- `packages/ambito-financiero-client/tests/test_decode.py` — Phase 29 precondition restated (see Deviation 1).
- `.planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md` — dated `## Amendment`.
- `.planning/phases/31-endpoints-de-ops-estructura-uniforme/deferred-items.md` — two out-of-scope pre-existing failures.

## Decisions Made

**The exemption-doc amendment (the decision the plan asked to record).** A 6-line dated
`## Amendment` was appended stating three things: (1) Phase 31 gave `wallets-client` and
`ambito-financiero-client` docstring-only `models.py` and `types.py`, so the module table's
`models.py` row now reads "yes" for both; (2) **the exemption itself is UNCHANGED** — it is
scoped to `_decode.py`, which neither package received, and `check_decode_intactness.py` was
not edited; (3) the table is stale in one further respect independent of this phase — iol
gained a `models.py` in Phase 30. Formal supersession stays deferred to the phase that
actually closes the exemption, exactly as RESEARCH Open Question 4 framed it. `EXEMPTION_DOC`
and both roster constants in the checker were not touched.

**`.egg-info` filtering in `_import_root`.** The plan's action mandates skipping `src/` children
ending in `.egg-info`; Task 1's acceptance criterion says the module's only string literals
should be `"src"`, the two module names and message text. These reconcile: `.egg-info` is a
build-artifact suffix, not a package directory name, so it cannot make the roster go stale —
which is the property the criterion protects. It is declared as `_BUILD_ARTIFACT_SUFFIX` with a
comment stating it is not a roster entry, so the distinction is auditable rather than implied.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] A Phase 29 test asserted ámbito has no `models.py`**

- **Found during:** Task 2 (full-suite `pytest -q`)
- **Issue:** `packages/ambito-financiero-client/tests/test_decode.py::test_this_package_really_has_no_models_module` asserted `not (package_dir / "models.py").exists()` and that importing `ambito_financiero_client.models` raises `ModuleNotFoundError`. TYP-03 deliberately creates that file (D-11), so the test failed. Its module docstring and the neighbouring `test_decode_module_never_imports_models` docstring also asserted in prose that ámbito "is expected never to grow one".
- **Fix:** The test was **restated, not deleted and not suppressed.** The property it guards — that `_decode` standing alone in this package is real evidence of no hidden models coupling — never depended on the file's absence; it depended on ámbito declaring no models. The test is now `test_this_package_really_declares_no_response_models`, and asserts the stronger, still-true set: `models.py` exists (TYP-03), its AST declares **zero** `ClassDef`s, its only import is `__future__`, and `ambito_financiero_client.models.__all__ == []`. The two stale docstrings were corrected to match.
- **Files modified:** `packages/ambito-financiero-client/tests/test_decode.py`
- **Verification:** `uv run pytest -q packages/ambito-financiero-client` → 200 passed, 1 deselected. `ruff check`, `ruff format --check` clean.
- **Committed in:** `2bc5dfc` (Task 2 commit)

**2. [Rule 1 - Bug] Two wallets docstring lines began with `import `, breaking an acceptance grep**

- **Found during:** Task 2 (acceptance verification)
- **Issue:** Both wallets modules wrapped the phrase "…would raise `ImportError` at package / import and redden all twelve…" so that a **docstring** line started with `import `. The plan's acceptance grep `grep -cE '^(import |from )'` therefore returned 2 instead of the required 1, falsely reporting that the import-free constraint (threat T-31-07) was violated. A future reader running the same grep would have drawn the same wrong conclusion.
- **Fix:** Rewrapped both sentences to "…would raise `ImportError` the moment the package is imported, reddening all twelve wallets CI matrix legs." No import statement existed in either file at any point; only the prose changed.
- **Files modified:** `packages/wallets-client/src/wallets_client/models.py`, `packages/wallets-client/src/wallets_client/types.py`
- **Verification:** `grep -cE '^(import |from )'` → 1 for each; a repo-wide grep over all 7 new modules returns only the 7 `from __future__ import annotations` lines.
- **Committed in:** `2bc5dfc` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both were necessary to complete the plan as written. Deviation 1 was
unavoidable — TYP-03 and that Phase 29 assertion are directly contradictory, and the plan's
`read_first` list did not include the ámbito test suite. No scope creep: no production behaviour
changed, and the restated test is strictly more specific than the one it replaces.

## Issues Encountered

**Pre-existing failures in the full local suite — logged, not fixed.** `uv run pytest -q`
finishes `20 failed, 1944 passed, 1 deselected, 19 errors in 919.09s`. One of those 20 was
Deviation 1 and is now fixed. The remaining 19 failures + 19 errors are all matriz
`verification/` probes calling `probe_login_sync()` with the pre-`15-05` signature
(`TypeError: probe_login_sync() missing 1 required positional argument: 'client'`). This plan
adds no file to `matriz-client`. Separately, `mypy packages/ambito-financiero-client/tests`
reports 2 errors — **verified pre-existing** by restoring the pristine `HEAD` copy of the file,
re-running mypy, observing the identical two errors at lines 771/840, and restoring the working
copy. Both families are written up in
`.planning/phases/31-endpoints-de-ops-estructura-uniforme/deferred-items.md`. Per the executor
scope boundary they were not fixed here; fixing them would have coupled a layout plan to an
unrelated harness repair.

**Consequence for one acceptance criterion:** Task 2's `uv run pytest -q` exits 0 criterion is
**not** met, and cannot be met by this plan — the residue is entirely pre-existing and
matriz-scoped. Everything this plan can be responsible for is green: all 6 package suites,
`verification/test_public_surface.py` (4 passed), both gates, ruff, and mypy on all `src`.

## Verification Evidence

| Check | Result |
|---|---|
| `uv run python tools/check_uniform_structure.py` | exit 0, success sentence naming 6 packages |
| `uv run python tools/check_decode_intactness.py` | exit 0, Checks A–D all green |
| `git diff HEAD~2 HEAD -- tools/check_decode_intactness.py` | **empty** — byte-unedited |
| `git diff HEAD~2 HEAD -- verification/snapshots/` | **empty** — ámbito golden byte-unchanged |
| `uv run ruff check .` / `ruff format --check .` | clean, 231 files |
| `uv run mypy` (5 enrolled packages, strict) | 62 source files, no issues |
| `uv run mypy packages/market-data-client/src` (D-13, local-only) | 13 source files, no issues |
| `uv run lint-imports` | 4 contracts kept, 0 broken |
| Both modules present in every package | `for d in packages/*/src/*/` loop prints nothing |
| 7 new modules carry the future import | 7 |
| 7 new modules annotate `__all__: list[str] = []` | 1 each |
| wallets modules' import-statement count | 1 each |
| ámbito `__init__.py` mentions of `types`/`models` | 0 |
| `check_uniform_structure.py` imports | only `__future__`, `sys`, `pathlib` |
| `except` clauses in the gate | 1, naming `CheckFailure` explicitly |
| `check_uniform_structure.py` refs in `ci.yml` | exactly 1, inside the `lint` job |
| `## Amendment` in `29-WALLETS-EXEMPTION.md` | 1 |
| Import smoke, all 6 packages + 7 new modules | all import; none re-exported into any `__all__` |
| Deletions in the two commits | none |

## Threat Model Dispositions

| Threat | Status |
|---|---|
| T-31-06 (vacuous green) | **mitigated** — roster from disk; unresolvable `src/` and empty scan are both problems; RED observed and captured; no bare/`Exception` handler |
| T-31-07 (wallets import outage) | **mitigated** — exactly 1 import statement per wallets module; import smoke confirms all 6 packages import |
| T-31-08 (ámbito golden tampering) | **mitigated** — nothing re-exported; `git diff --stat verification/snapshots/` empty; `test_public_surface.py` passes |
| T-31-09 (Phase 29 gate tampering) | **mitigated** — `check_decode_intactness.py` byte-unedited and green |
| T-31-10 (docstring info disclosure) | **accepted** — docstrings name planning-doc paths and package names only |
| T-31-SC (package-manager installs) | **mitigated** — zero installs; `uv.lock` untouched; gate is stdlib-only |

## Known Stubs

The 7 new modules are stubs **by design and by decision**, each documented in its own docstring:

| File | Why it is empty | Resolved by |
|---|---|---|
| 5 × `types.py` | `29-DLOCK-RESPONSE-LITERAL.md` forbids closing response fields as `Literal` this milestone | Phase 33 (iol `mercado`/`plazo`), pending a live census |
| `ambito_financiero_client/models.py` | ámbito parses via `_parsing.parse_ar_decimal`; it declares no response models | not scheduled — intentional |
| `wallets_client/{models,types}.py` | `wallets-client` is a stub with no verifiable endpoints | Phase 32 (D-16 reconciliation) |

None blocks this plan's goal: TYP-03 is a **layout** requirement, and the layout is complete and
gated. No stub is re-exported, so none is reachable from any package's public surface.

## Flagged Assumptions (still open)

- **TYP-03 / unclassified / unresolved** — the deterministic edge probe emitted the generic
  "review manually" probe. Its one genuine failure mode (a gate green while a file is missing)
  was addressed as T-31-06 with an observed RED. **The probe row itself remains open.**

## User Setup Required

None — no external service configuration required. Zero dependency changes; `uv.lock` untouched.

## Next Phase Readiness

- Every package now has a home for response models and enum-like vocabulary, so Phase 32's AST
  surface gate and Phase 33's `Literal` promotion both have a fixed target file per package.
- The `lint` job now carries two structural gates (`decode-intactness`, `uniform-structure`) and
  is the established home for cross-package checks — Phase 32's surface gate belongs there too,
  not under `verification/`.
- **Blocker for Phase 32's D-16 reconciliation:** `wallets-client` now presents the uniform
  layout but is still exempt from the decode roster. The exemption doc's amendment records this
  explicitly; the formal supersession is still owed.
- **Carried debt (see `deferred-items.md`):** matriz's `verification/` probes are broken against
  the current `main_matriz.py` signature, and ámbito's test suite has 2 live `mypy --strict`
  errors that the `typecheck` CI job does run.

## Self-Check: PASSED

All 10 claimed files verified present on disk; all 3 claimed commits verified in
`git log`. Both CI gates re-run green at `2bc5dfc`; no file deletions in either task commit.

---
*Phase: 31-endpoints-de-ops-estructura-uniforme*
*Completed: 2026-08-24*
