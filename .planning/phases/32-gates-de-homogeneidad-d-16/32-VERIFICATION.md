---
phase: 32-gates-de-homogeneidad-d-16
verified: 2026-08-25T23:27:48Z
status: human_needed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Push the branch (or the commit range 32-01..6817b66) and observe the real GitHub Actions run for .github/workflows/ci.yml"
    expected: "All four jobs (lint, pre-commit, typecheck, test) are green, all twelve `test` matrix legs (6 packages × py3.12/py3.13) pass, the `lint` job shows the new `surface-types (Phase 32 GATE-TYP-01 …)` step passing, and no branch-protection required-status-check name changed as a result of adding a step (rather than a job) to `lint`."
    why_human: "No CI run exists for any commit in this phase (last real `ci.yml` run in `gh run list` is from 2026-08-18, nine days before this phase's commits). Every one of the six plan SUMMARYs' 'full CI green' claims is a local reproduction only (macOS/arm64, one checkout, sequential legs) — Plan 32-06 itself states this explicitly ('locally proven, pending real-runner confirmation') and carries an unresolved `<human-check>` for exactly this observation. Local reproduction cannot see Linux-vs-macOS behavioural differences, the `astral-sh/setup-uv@v3` cache path, the coverage-upload step, or true per-job runner isolation — the things ROADMAP.md's success criterion 5 literally asks to be green."
---

# Phase 32: Gates de homogeneidad + D-16 Verification Report

**Phase Goal:** CI falla si la homogeneidad se degrada — sin código compartido entre paquetes, los gates son lo único que impide que las seis superficies diverjan en tres releases.
**Verified:** 2026-08-25T23:27:48Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Derived from ROADMAP.md's five Success Criteria for Phase 32 (Option A/roadmap-contract path), cross-checked against plan `must_haves` and independently re-run against the working tree rather than trusted from SUMMARY/REVIEW-FIX prose.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A stdlib-AST-only script (`tools/check_surface_types.py`) walks `__all__` of all 6 packages and fails on any exported `Any`/`dict[str, Any]` return, with DT-06 exemptions, and runs in a real CI job | ✓ VERIFIED | Ran `uv run python tools/check_surface_types.py` directly: exit 0, `6 packages, 178 __all__ names, 319 definitions scanned, 13 constant/alias exports, 23 exempted (dunder 13, private-helper 1, serialize-out 9), 0 violations`. Wired at `.github/workflows/ci.yml:66` (`uv run python tools/check_surface_types.py`) inside the existing `lint` job, no `continue-on-error` present. Roadmap literal wording says "job de CI nuevo"; delivered as a **step** in the pre-existing `lint` job instead, per an explicitly recorded decision (D-05, Phase 31's locked D-12 supersedes the roadmap-summary prose) — documented in the gate's own docstring, the `ci.yml` step comment, and 32-02/32-06 SUMMARYs. Treated as a resolved, disclosed deviation, not a silent gap. |
| 2 | The surface gate is non-vacuous: a deliberately-introduced regression makes it fail, proven by a test | ✓ VERIFIED | `packages/iol-client/tests/test_surface_types_red.py` independently run: 15 tests, all pass (`uv run pytest ... -q`). Code review (32-REVIEW.md CR-01) found and reproduced 3 real false-negative shapes (alias re-export, conditionally-defined export, `__all__ +=`) that made the pre-fix gate report GREEN on genuine violations, including 2 live matriz-client re-exports. 32-REVIEW-FIX.md commit `db7ca0e` closes all three with a re-export-chain-following `_resolve_export` (confirmed present in `tools/check_surface_types.py:443`, `_MAX_RESOLUTION_HOPS = 8` at line 187) and 7 new RED cases, all independently confirmed passing on the current tree. |
| 3 | The sync/async parity test runs in-package on the existing 6×2 CI matrix, compares public names + `get_type_hints()` between `client.py`/`aio.py`, and is non-vacuous with per-package lower bounds — no `aio.py` without `__all__` can be silently skipped | ✓ VERIFIED | All six packages carry `packages/<pkg>/tests/test_surface_parity.py` (`ls packages/*/tests/test_surface_parity.py \| wc -l` = 6). `tools/surface_parity.py` derives names via `dir()`/`__module__`, never `__all__`. Code review (CR-02, WR-01 through WR-04) found and reproduced 4 more real gaps — no `__init__` comparison (a live sync/async constructor divergence existed in `market_data_client` at review time), annotation-only comparison missing parameter order/defaults, a `__module__` filter that hid real constant/alias divergences, and a hand-maintained bounds roster with no disk cross-check. All four fixed in commits `3617e51`/`1cf3741`/`927f757`/`a98ecba`, each closing a real, reproduced live divergence (not a hypothetical), each with new RED tests. Independently re-ran `packages/iol-client/tests/test_surface_parity_red.py` (27 tests combined with surface-types RED, all pass) and confirmed `assert_bounds_roster_matches_disk` (surface_parity.py:959) is invoked against the real tree at test line 519. wallets asserts its `Client`/`AsyncClient` absence positively (`ast.Assert` present, no `ast.Return`, no skip marker) rather than being excluded. |
| 4 | D-16 closed atomically: the four enrollment lists (mypy `files`, import-linter `root_packages`, `ci.yml` mypy-tests loop, `test_public_surface._PACKAGES`) agree; the `market_data_client._core` import-linter contract is RED-proven; wallets' inclusion/exclusion is an explicit, documented decision | ✓ VERIFIED | `pyproject.toml:97` mypy `files` lists all 6 package `src` trees — confirmed by direct read and by `uv run mypy` reporting 75 source files (0 issues). `root_packages` (`pyproject.toml:147-153`) lists 5 entries, **wallets deliberately absent**, with the structural reason ("no `_core.py`, no `source_modules` for a `forbidden` contract") recorded verbatim in `tools/check_decode_intactness.py`'s `resolved_by` field for the wallets `ExemptPackage` (confirmed by direct grep, naming Phase 32 and `root_packages` in the past tense — not a dangling forward reference). `ci.yml`'s mypy-tests loop already iterated all 6. `verification/test_public_surface.py` carries an explicit comment (lines 47-50, confirmed) stating market-data and wallets are excluded "by decision, not by oversight." The `market_data_client._core` boundary contract has an automated RED fixture (`packages/market-data-client/tests/test_core_boundary_red.py`) that mutates the tracked file, observes the contract go BROKEN, and restores it — independently re-run: 9 tests pass (combined with `test_transport_injection.py`), `git status --porcelain` on `_core.py` is empty afterward, and `uv run lint-imports` reports `5 kept, 0 broken` on the clean tree. |
| 5 | The full CI matrix (6 packages × py3.12 + py3.13) is green with the new gates active | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Every job/leg was reproduced **locally** and independently re-confirmed here: `uv run pytest packages -q` → 1736 passed, 1 deselected; `uv run mypy` → 75 files, 0 issues; per-package mypy loop → 6/6 green (12/4/25/16/20/30 source files, matching REVIEW-FIX's own count); `uv run ruff check .`/`ruff format --check .` → clean; `uv run lint-imports` → 5 kept, 0 broken; `uv run pre-commit run --all-files` → 9/9 hooks passed. All of this matches what 32-06-SUMMARY.md and 32-REVIEW-FIX.md claim, and is not merely trusted — it was re-executed independently for this verification. However, **no GitHub Actions run exists for this phase's commits** (`gh run list --workflow=ci.yml` shows the most recent real run is from 2026-08-18, before this phase started on 2026-08-25) — the twelve-leg real-runner matrix that the roadmap's literal wording asks for ("La matriz completa de CI ... queda verde") has never actually executed. This is not a silent gap: Plan 32-06 and its SUMMARY explicitly name this as an open `<human-check>` and state criterion 5 is "locally proven, pending real-runner confirmation" rather than claiming an unqualified green. |

**Score:** 5/5 truths present and locally verified (1 present-but-behavior-unverified on a real CI runner)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/check_surface_types.py` | stdlib-AST gate, injectable root, DT-06 exemptions | ✓ VERIFIED | Exists, runs green (0 violations), CR-01 false-negatives fixed and independently confirmed |
| `packages/iol-client/tests/test_surface_types_red.py` | Non-vacuity RED proof | ✓ VERIFIED | 15 tests, all pass |
| `.github/workflows/ci.yml` new step | `surface-types` step in `lint` job | ✓ VERIFIED | Confirmed at line 66, no `continue-on-error`, job count unchanged |
| `tools/surface_parity.py` | Shared introspection parity walker | ✓ VERIFIED | Exists; `__init__` comparison (rule 5), signature-shape diff, package-owned filter, and disk-cross-check roster all confirmed present in source, not just claimed |
| `packages/*/tests/test_surface_parity.py` (×6) | Thin per-package parity hooks | ✓ VERIFIED | All 6 present; wallets asserts absence, not skip |
| `packages/iol-client/tests/test_surface_parity_red.py` | Non-vacuity RED proof for parity gate (added during review-fix; the gate originally shipped with zero lower-bound tests) | ✓ VERIFIED | Confirmed present, 12 RED cases per REVIEW-FIX, re-run passes |
| `packages/market-data-client/tests/test_core_boundary_red.py` | Import-linter contract RED proof | ✓ VERIFIED | 2 tests present, hermeticity fixed (WR-05), re-run passes, tree clean after |
| `packages/market-data-client/tests/test_transport_injection.py` | Race-condition regression test (WR-07) | ✓ VERIFIED | Present, re-run passes |
| `market_data_client.aio.configure` / `client.configure` `http_client` parity | D-09 closed, `Client.__init__` also gained the parameter (CR-02 finding) | ✓ VERIFIED | Both `configure()` and `__init__()` on both surfaces confirmed to accept and validate `http_client`, mirrored per CLAUDE.md's dual sync/async constraint |
| `.planning/REQUIREMENTS.md` | GATE-TYP-01 traceability | ✓ VERIFIED | Row marked `Complete`; checkbox marked `[x]`; no orphaned requirement IDs for Phase 32 (only GATE-TYP-01 is declared, and all 6 plans carry it) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `packages/iol-client/tests/test_surface_types_red.py` | `tools/check_surface_types.py` | cross-package `tools.` import | WIRED | Confirmed importable, enrolled in `mypy packages/iol-client/tests` (16 files) |
| `.github/workflows/ci.yml` `lint` job | `tools/check_surface_types.py` | `uv run python tools/check_surface_types.py` | WIRED | Confirmed at line 66, blocking (no suppression key) |
| `packages/*/tests/test_surface_parity.py` | `tools/surface_parity.py` | `from tools.surface_parity import ...` | WIRED | Confirmed for all 6 files |
| `.github/workflows/ci.yml` `test` job | `packages/*/tests/*.py` (incl. all new RED/parity files) | per-package explicit path, 6×2 matrix | WIRED | Confirmed matrix definition (`package:` list of 6, `python-version: ["3.12","3.13"]`), explicit `packages/${{ matrix.package }}` path |
| `packages/market-data-client/tests/test_core_boundary_red.py` | `pyproject.toml` `[tool.importlinter]` | subprocess `lint-imports`, resolved beside `sys.executable` (post WR-05 fix) | WIRED | Confirmed present and independently re-run |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GATE-TYP-01 | 32-01 … 32-06 (all six) | CI fails if homogeneity degrades — surface-type gate, sync/async parity gate, D-16 closure | ✓ SATISFIED | REQUIREMENTS.md row = `Complete`, checkbox `[x]`. All three sub-clauses (a/b/c) independently confirmed against the working tree, not just SUMMARY prose. |

No orphaned requirements: REQUIREMENTS.md maps only GATE-TYP-01 to Phase 32, and it appears in every plan's `requirements:` frontmatter.

### Anti-Patterns Found

None blocking. No `TBD`/`FIXME`/`XXX` markers found in any file touched by this phase (checked across all `tools/*.py`, the new/modified test files, `aio.py`/`client.py`, `ci.yml`, `pyproject.toml`, `verification/test_public_surface.py`). No stub returns, no hardcoded empty collections feeding a real path, no silently-swallowed exceptions introduced by this phase's changes.

Two pre-existing (not-this-phase) info-level issues from `32-REVIEW.md` remain open by design (out of `fix_scope`) and are not blockers for this phase's goal:
- IN-02 (`check_surface_types.py`'s `_import_root` still not hardened against stray `__pycache__`/dot-directories — the equivalent hardening *was* applied to the freshly-written `surface_parity.py` roster check under WR-04, but not backported to the sibling)
- IN-05 (`verification/test_public_surface.py`'s comment could be read as contradicting `testpaths`, though the substantive claim — the CI `test` job never collects it — is correct and independently confirmed)

### Human Verification Required

#### 1. Real GitHub Actions confirmation of the full CI matrix (ROADMAP success criterion 5)

**Test:** Push this phase's commits (or the branch `milestone/v1.5-mutations` at `6817b66`) and observe the `ci.yml` workflow run on GitHub Actions.
**Expected:** All four jobs (`lint`, `pre-commit`, `typecheck`, `test`) pass; all twelve `test` matrix legs (6 packages × py3.12/3.13) pass; the `lint` job's new `surface-types` step is visible and green; no branch-protection required-status-check name changed.
**Why human:** This cannot be verified by static analysis or local reproduction. `gh run list --workflow=ci.yml` shows no run newer than 2026-08-18 — nine days before this phase's work began — so the real 12-leg matrix this phase's success criterion 5 literally requires has never executed. Every "green" claim in the six plan SUMMARYs and in this verification's own re-run is a local, single-machine, sequential reproduction (macOS/arm64), which the phase's own Plan 32-06 explicitly acknowledges is a proxy, not a certification, for the real runner matrix.

### Gaps Summary

No gaps found. All four "hard" success criteria (1-4) are genuinely implemented, wired, and — notably — were independently re-verified against the actual working tree rather than trusted from SUMMARY/REVIEW-FIX narrative; the code-review cycle caught and fixed real non-vacuity holes in both new gates (confirmed via git log, direct source reads, and re-running all RED suites), so "the gates were sold on non-vacuity" is now true rather than aspirational. The one open item is success criterion 5's requirement that the *real* CI matrix (not a local reproduction) be green — this is correctly and explicitly surfaced by the phase's own artifacts as an unresolved `<human-check>`, not silently claimed complete, and this verification confirms via `gh run list` that no such real run has yet occurred. That is a human-verification item, not a code defect — nothing indicates the real run would fail (the local reproduction passed on the same commit), but "would probably pass" is not "was observed to pass," which is what the roadmap's literal wording asks for.

---

*Verified: 2026-08-25T23:27:48Z*
*Verifier: Claude (gsd-verifier)*
