---
phase: 06-compat-safety-net-client-class-skeleton
plan: 01
subsystem: testing
tags: [pytest, snapshot, golden-file, public-surface, baseline, refac-01, safety-net, mvp-v1.1]

# Dependency graph
requires:
  - phase: 05-matriz-rest-verification
    provides: 277 mocked tests passing baseline; verification/ harness modules (schema, redaction, mutation_gate, etc.)
provides:
  - Public-surface snapshot test sweeping the 4 target packages against committed text baselines (W3 header-pinned)
  - Operator-run regen script (deterministic; lazy-imports enumeration helpers)
  - 4 PRE-refactor snapshot baselines under verification/snapshots/
  - Phase 6 entry-baseline (test_count + coverage% + git_sha + full test ID listing) anchoring REFAC-01 B5
  - testpaths extended to include verification/ so the new test is collected by `uv run pytest -q`
affects: [phase-06-02-guard-tests, phase-06-03-ambito-skeleton, phase-06-04-iol-skeleton, phase-06-05-higyrus-skeleton, phase-06-06-matriz-skeleton, phase-07-core-dedup, phase-11-harness-finalize]

# Tech tracking
tech-stack:
  added: []  # no new dependencies; uses stdlib inspect + pytest already in dev deps
  patterns:
    - "PEP-562-ready public-surface snapshot test (golden-file idiom, W3 header pinning, parametrized sweep)"
    - "Operator regen script with lazy import + auto-sys.path inject for `python <script>` entry"
    - "Phase entry-baseline file with embedded git_sha anchor (T-06-12 mitigation)"

key-files:
  created:
    - verification/test_public_surface.py
    - verification/regen_snapshots.py
    - verification/snapshots/ambito-financiero-client-surface.txt
    - verification/snapshots/iol-client-surface.txt
    - verification/snapshots/higyrus-client-surface.txt
    - verification/snapshots/matriz-client-surface.txt
    - verification/baselines/phase-06-baseline.txt
  modified:
    - pyproject.toml  # testpaths: added "verification"

key-decisions:
  - "Snapshot kind detection: iscoroutinefunction BEFORE isfunction (async fns also satisfy isfunction)."
  - "Header validation in _strip_header: assert 8 lines all start with '#' AND line 8 == '#' alone, then strip header before equality compare. Editing header docs does not mask body drift; structural drift (header length, separator) IS detected."
  - "regen script lazy-imports inside main() AND inserts repo_root into sys.path[0]. The bare `python verification/regen_snapshots.py` invocation does not put repo root on sys.path by default — fix required for D-11 operator usage."
  - "Pre-refactor baseline captures only the existing __all__ surface (top-level functions, exception classes, models, types). Plans 03-06 add Client / AsyncClient / close / aclose lines via regen_snapshots.py."

patterns-established:
  - "Golden-file text snapshot under verification/snapshots/<pkg-with-dashes>-surface.txt; one body line per __all__ symbol as `<name> : <kind> : <signature>`, sorted alphabetically, terminating newline."
  - "8-line `#` header with line 8 == `#` separator (W3); editor-resilient (literal in regen template)."
  - "Phase entry-baseline file format: 8-line `#` header + key:value pairs (captured_at, git_sha, test_count, coverage_total, commands) + `## test_ids` body block."

requirements-completed: [REFAC-01]

# Metrics
duration: 4min
completed: 2026-06-11
---

# Phase 06 Plan 01: Compat Safety Net Snapshot Test + Baselines Summary

**Public-surface snapshot test (`inspect.signature` over `__all__`) sweeping ambito/iol/higyrus/matriz with W3-pinned text golden files, deterministic regen script, and Phase 6 entry-baseline (281 tests / 95% coverage / git_sha-anchored) committed BEFORE any per-package Client class refactor lands.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-11T02:32:20Z
- **Completed:** 2026-06-11T02:36:24Z
- **Tasks:** 4 (all `type=auto`)
- **Files created:** 7
- **Files modified:** 1 (`pyproject.toml`)
- **Commits:** 4 (atomic per-task)
- **Tests baseline:** 277 → 281 (+4 new public-surface tests, all green)

## Accomplishments

- **Public-surface safety net** wired against the 4 target packages with deterministic snapshot comparison. Wave 1 per-package skeleton drift (Plans 03-06) will now show up as a failing assertion + forensic-localizable git diff (Pitfall #1 mitigation per CONTEXT.md).
- **Deterministic regen path** (`uv run python verification/regen_snapshots.py`) for operator-driven refresh of the 4 baselines when an intentional `__all__` change lands. `git diff --exit-code verification/snapshots/` returns 0 on a clean tree.
- **Phase 6 entry-baseline** captured (REFAC-01 checker B5): 281 tests collected, 95% aggregate coverage, anchored to git SHA `d6aa845…` and the full test ID listing — enabling diff-against-baseline regression detection in Phases 07-11.
- **pyproject.toml testpaths extension** picks up the new test under `uv run pytest -q` without requiring explicit path args (PATTERNS.md Critical Risk #4).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add `verification` to pytest testpaths** — `35fe66d` (chore)
2. **Task 2: Create snapshot enumerator + parametrized snapshot test + 4 baseline snapshot files** — `461f53b` (test)
3. **Task 3: Create `regen_snapshots.py` operator script** — `d6aa845` (feat)
4. **Task 4: Capture Phase 6 entry-baseline (test count + coverage%) for REFAC-01** — `73eb87a` (docs)

## Files Created/Modified

- `verification/test_public_surface.py` — Parametrized golden-file test (`@pytest.mark.parametrize("pkg_name", _PACKAGES)`). Enumerates `__all__` symbols via `inspect.signature`; signature wrapped in try/except `(TypeError, ValueError)` per RESEARCH.md Pitfall 9. `_kind` checks `iscoroutinefunction` before `isfunction` (async fns also satisfy `isfunction`). `_strip_header` validates W3 invariant: 8 lines all start with `#`, line 8 is exactly `#` (header/body separator).
- `verification/regen_snapshots.py` — Operator entry point. Lazy-imports `_PACKAGES`, `_enumerate_surface`, `_snapshot_path` inside `main()`. Auto-inserts repo root into `sys.path[0]` so `python verification/regen_snapshots.py` resolves the `verification` package directly. Header template literal in this file (8-line `#` block with line 8 == `#` alone) ensures editor auto-strip-trailing-whitespace cannot silently corrupt the separator.
- `verification/snapshots/ambito-financiero-client-surface.txt` — 7 body lines (5 exception classes + `configure` + `get_dollar_banco_nacion`).
- `verification/snapshots/iol-client-surface.txt` — 11 body lines (4 exception classes + `InstrumentType` Literal + 5 endpoint functions + `login`).
- `verification/snapshots/higyrus-client-surface.txt` — 27 body lines (5 exception classes + 14 model dataclasses + `SafeModel` + 6 endpoint functions + `login`).
- `verification/snapshots/matriz-client-surface.txt` — 62 body lines (3 exception classes + 17 models + 9 type literals + 2 WS data constants + 21 REST functions + 6 WS functions + `login`).
- `verification/baselines/phase-06-baseline.txt` — Phase 6 entry-baseline. Header block + key-value fields (`captured_at`, `git_sha`, `test_count: 281`, `coverage_total: 95%`, `coverage_command`, `pytest_command`) + `## test_ids` body with the full 281-line test ID listing.
- `pyproject.toml` — `[tool.pytest.ini_options]` `testpaths` changed from `["packages", "tests"]` to `["packages", "tests", "verification"]`. Single-line additive edit.

## Decisions Made

- **Kind detection order: `iscoroutinefunction` BEFORE `isfunction`.** Async functions (`coroutine`) also satisfy `inspect.isfunction`; checking `isfunction` first would mis-label every async public function in `iol_client.aio` / `higyrus_client.aio` / `ambito_financiero_client.aio` as `function` instead of `coroutine`. RESEARCH.md Pattern 5 calls this out explicitly.
- **Header invariant in test, not regex.** `_strip_header` validates 8 lines starting with `#` AND `lines[7].rstrip("\n") == "#"` via explicit asserts with clear remediation messages — preferred over regex for forensic clarity at failure time.
- **`load_dotenv` is not in `__all__`** so it does not appear in any snapshot. The pre-refactor baselines reflect ONLY the documented public surface (per D-06). Plans 03-06 will add `Client`, `AsyncClient`, `close`, `aclose` to each `__all__` and regenerate via `regen_snapshots.py`.
- **Header template stored as literal string in `regen_snapshots.py`** (not pulled from a shared constant). Reason: editors with auto-strip-trailing-whitespace could silently corrupt line 8 (`"#\n"`) if it were stored as a raw multi-line string in a less-obvious location. Two literals (one in the snapshot files themselves, one in the regen template) are intentional redundancy for W3 pinning.
- **Coverage measured at 95%** via `uv run pytest --cov=packages -q --cov-report=term` aggregated TOTAL line. Coverage tool config already lives in `pyproject.toml` `[tool.coverage.run]` (`branch = true`, `source = ["packages"]`). No fallback / per-package aggregation needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff RUF002: en-dash in docstring**
- **Found during:** Task 2 (after writing `verification/test_public_surface.py`)
- **Issue:** Docstring at line 4 used `–` (EN DASH) in `Plans 03–06`; ruff RUF002 flagged the ambiguous character (project enforces RUF rules per `pyproject.toml`).
- **Fix:** Replaced `–` with ASCII `-` (`Plans 03-06`). The same edit was preemptively applied to the commit messages of all 4 task commits for consistency.
- **Files modified:** `verification/test_public_surface.py`
- **Verification:** `uv run ruff check verification/test_public_surface.py` → `All checks passed!`
- **Committed in:** `461f53b` (rolled into Task 2 commit before the commit landed)

**2. [Rule 1 - Bug] regen_snapshots.py failed under `python verification/regen_snapshots.py`**
- **Found during:** Task 3 (verify step)
- **Issue:** When invoked as `uv run python verification/regen_snapshots.py`, Python puts the script's parent directory (`verification/`) on `sys.path`, NOT the repo root. The lazy `from verification.test_public_surface import ...` raised `ModuleNotFoundError: No module named 'verification'`. The script would have worked only under pytest (which uses `pyproject.toml`'s `pythonpath = ["."]` setting).
- **Fix:** Inside `main()`, before the lazy import, inserted `repo_root = Path(__file__).resolve().parent.parent` into `sys.path[0]` if not already present. Preserves the lazy-import contract (no import-time side effects) and makes the script work via the documented D-11 operator command without requiring `uv run` magic or `PYTHONPATH=` prefix.
- **Files modified:** `verification/regen_snapshots.py`
- **Verification:** `uv run python verification/regen_snapshots.py` prints 4 `Wrote ...` lines; `git diff --exit-code verification/snapshots/` returns 0 (deterministic).
- **Committed in:** `d6aa845` (rolled into Task 3 commit before the commit landed)

---

**Total deviations:** 2 auto-fixed (2 × Rule 1 - Bug)
**Impact on plan:** Both fixes are essential for correctness (lint compliance + operator-usable entry point). No scope creep; both fixes stay inside the plan's `files_modified` set. The plan's D-11 contract (operator runs `python verification/regen_snapshots.py`) is now actually achievable as written.

## Issues Encountered

- **uv workspace not pre-synced in worktree.** First `uv run pytest --collect-only -q` after Task 1 failed with `ModuleNotFoundError: No module named 'wallets_client'` (and the other 4 packages). Recovered by running `uv sync --all-packages --all-extras --dev` once; subsequent commands worked normally. Not a deviation (no plan change); just an environment setup step expected for a fresh worktree.

## User Setup Required

None — no external service configuration required. All tasks were purely additive to the in-repo verification harness.

## Verification Evidence

All `<verification>` block items from the plan exit clean:

| Check | Command | Result |
|---|---|---|
| Snapshot test | `uv run pytest verification/test_public_surface.py -q` | `4 passed in 0.07s` |
| Deterministic regen | `uv run python verification/regen_snapshots.py && git diff --exit-code verification/snapshots/` | exit 0 |
| Full suite | `uv run pytest -q` | `281 passed, 1 deselected in 0.54s` (277 baseline + 4 new = 281) |
| Ruff lint | `uv run ruff check verification/` | `All checks passed!` |
| Mypy strict | `uv run mypy --strict verification/test_public_surface.py verification/regen_snapshots.py` | `Success: no issues found in 2 source files` |
| Baseline keys | `grep -v '^#' verification/baselines/phase-06-baseline.txt \| grep -E '^(test_count\|coverage_total):'` | both present (`test_count: 281`, `coverage_total: 95%`) |
| W3 header (per pkg) | `head -8 \| grep -c '^#'` + `sed -n '8p'` | All 4 snapshots: `first8_hash=8 line8=[#]` |

## Next Phase Readiness

- The snapshot test is committed and green: Plan 06-02 (per-package fixture-reaches-production guard tests) can land directly without further setup.
- Plans 06-03 through 06-06 (per-package Client class skeletons) MUST run `uv run python verification/regen_snapshots.py` immediately after their `__all__` mutation and commit the snapshot diff alongside the source change (D-11). The test will fail noisily if they don't.
- Phase 6 entry-baseline (281 tests / 95% coverage / git_sha `d6aa845…`) is available as a diff target for future phase summary checks.
- No blockers; no architectural deferrals.

## Threat Surface Scan

No new threat surface introduced beyond the plan's `<threat_model>` block. T-06-01 (snapshot tampering), T-06-08 (info disclosure via snapshot contents), T-06-12 (baseline retroactive edit) mitigations are in place as specified:
- T-06-01: snapshot files carry the "DO NOT EDIT BY HAND" header documenting the regen command; header is stripped before body equality compare; the 8-line invariant is validated structurally.
- T-06-08: snapshot bodies contain only public symbol names + signatures from `__all__`; `_state` and credentials are not in `__all__` for any package.
- T-06-12: `phase-06-baseline.txt` embeds `git_sha: d6aa845d900893e26c2b14c9769a738691af7766` so a retroactive edit is detectable via `git log -p verification/baselines/phase-06-baseline.txt`.

## Self-Check: PASSED

**Files created (all 7 present):**
- `verification/test_public_surface.py` — FOUND
- `verification/regen_snapshots.py` — FOUND
- `verification/snapshots/ambito-financiero-client-surface.txt` — FOUND
- `verification/snapshots/iol-client-surface.txt` — FOUND
- `verification/snapshots/higyrus-client-surface.txt` — FOUND
- `verification/snapshots/matriz-client-surface.txt` — FOUND
- `verification/baselines/phase-06-baseline.txt` — FOUND

**Commits (all 4 in `git log`):**
- `35fe66d` — FOUND (chore(06-01): add verification to pytest testpaths)
- `461f53b` — FOUND (test(06-01): add public-surface snapshot test + 4 baselines)
- `d6aa845` — FOUND (feat(06-01): add regen_snapshots.py operator script)
- `73eb87a` — FOUND (docs(06-01): capture Phase 6 entry-baseline (REFAC-01 / B5))

---
*Phase: 06-compat-safety-net-client-class-skeleton*
*Plan: 01*
*Completed: 2026-06-11*
