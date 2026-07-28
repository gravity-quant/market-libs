---
phase: 14-iol-disk-persistence-sec-01
plan: 01
subsystem: testing
tags: [iol-client, platformdirs, disk-persistence, refresh-token, tests-first, fcntl, sec-01]

# Dependency graph
requires:
  - phase: 13-cross-package-ergonomics-with-options-max-retries-n
    provides: "_ClientState dataclass shape + Client.__init__ kwarg pattern that Plan 2 extends with token_cache_path"
  - phase: v1.1 LOG-02
    provides: "RedactingFilter on logging.getLogger('iol_client') that iol_client._token_cache will inherit (anti-Pitfall 7)"
provides:
  - "platformdirs>=4.0,<5 runtime dependency on iol-client ONLY (D-T4 single-package scope)"
  - "verification/test_iol_disk_persistence.py — 11 RED tests (3 CRITICAL merge gates + 8 BUG-03 regression tests)"
  - "RED-in-HEAD verification surface (D-P1) that Plans 2-3 must turn GREEN"
affects: [14-02-PLAN (_token_cache.py + sync Client), 14-03-PLAN (async AsyncClient + green gate)]

# Tech tracking
tech-stack:
  added: ["platformdirs>=4.0,<5 (iol-client only)"]
  patterns:
    - "Tests-first cross-cutting RED-in-HEAD (Phase 8 D-21 / Phase 13 D-P1 carry-forward)"
    - "Import-safe collection: top-level `import iol_client` only; `iol_client._token_cache` referenced inside test bodies so failures surface at TEST run, not collection"
    - "Single-package field carve-out (Phase 13 D-T3 matriz-only `client_max_retries` → Phase 14 iol-only `platformdirs` + future `token_cache_path`)"

key-files:
  created:
    - "verification/test_iol_disk_persistence.py — 11 disk-persistence tests, RED in HEAD"
  modified:
    - "packages/iol-client/pyproject.toml — platformdirs>=4.0,<5 dep"
    - "uv.lock — platformdirs resolution refreshed"

key-decisions:
  - "D-P1: tests committed RED in HEAD (not GREEN as impl side-effect) for bisect/forensics clarity"
  - "D-P2: cross-cutting tests live in verification/test_iol_disk_persistence.py, separate from v1.1 verification/test_logging_no_token_leak.py"
  - "D-T4: platformdirs declared on iol-client ONLY; negative grep clean on root + 4 other packages"
  - "Per-task atomic commits (executor protocol) instead of the single 3-file commit the plan text assumed — worktree merge flow makes this safe (deviation R-3, see below)"

patterns-established:
  - "RUF002 hygiene: ASCII-only docstrings in test files (multiplication-sign × → x) to keep `ruff check` exit 0 under the RUF rule set"
  - "B007 hygiene: iterate record.__dict__.values() (not .items() with unused key) for the sentinel-leak loop"

requirements-completed: [SEC-01]  # NOTE: SEC-01 is only PARTIALLY addressed by Plan 1 (RED gate). Plans 2-3 complete the GREEN implementation. Do not mark SEC-01 fully done until Plan 3.

# Metrics
duration: 19min
completed: 2026-06-24
status: complete
---

# Phase 14 Plan 01: Cross-cutting IOL disk-persistence tests + platformdirs dep Summary

**Landed the Phase 14 SEC-01 tests-first RED surface — 11 disk-persistence tests (3 CRITICAL anti-Pitfall 7/8/9 merge gates + 8 BUG-03 × {sync, async} regression tests) committed RED-in-HEAD, plus `platformdirs>=4.0,<5` declared on iol-client only — anchoring the verification contract that Plans 2-3 must satisfy.**

## Performance

- **Duration:** 19 min active (excludes ~15 min full-suite baseline run wall-clock)
- **Started:** 2026-06-24T00:25:16Z
- **Completed:** 2026-06-24T00:45:09Z
- **Tasks:** 3 completed
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- `verification/test_iol_disk_persistence.py` created with exactly 11 tests, all RED in HEAD, collection succeeds with no ImportError.
- `platformdirs>=4.0,<5` declared on iol-client's `[project].dependencies` ONLY; D-T4 negative grep clean on the root + 4 other packages.
- `uv.lock` refreshed; pre-existing **973-test baseline preserved** (973 passed, 1 deselected) — the new dep did not break any import chain.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add platformdirs runtime dep to iol-client (D-T4)** — `66a9f4b` (chore)
2. **Task 2: Create verification/test_iol_disk_persistence.py with 11 RED tests** — `8f9a6ef` (test)
3. **Task 3: Refresh uv.lock + confirm RED-in-HEAD** — `4aa3193` (chore)

_Note: the plan text described Task 3 as a single combined commit touching 3 files; the executor's atomic per-task protocol produced 3 commits instead. See Deviations._

## Files Created/Modified
- `verification/test_iol_disk_persistence.py` (NEW, 475 lines) — 3 CRITICAL merge gates (`test_disk_persistence_never_logs_token`, `test_disk_token_write_under_concurrent_processes`, `test_disk_token_deleted_on_refresh_401`) + 8 regression tests (4 BUG-03 paths × sync/async).
- `packages/iol-client/pyproject.toml` — added `"platformdirs>=4.0,<5"` to `[project].dependencies`.
- `uv.lock` — platformdirs and transitive resolution refreshed (`uv lock`).

## RED-in-HEAD Verification (D-P1 contract)

All 11 tests are RED by design. Running `uv run --frozen pytest verification/test_iol_disk_persistence.py`:

```
11 failed, 2 errors in 0.02s
```

Observed failure classes (exactly the expected RED-in-HEAD signatures — Plans 2-3 turn these GREEN):

- `AttributeError: module 'iol_client' has no attribute '_token_cache'` — the `_token_cache` module is created in Plan 2.
- `TypeError: Client.__init__() got an unexpected keyword argument 'refresh_token'`
- `TypeError: AsyncClient.__init__() got an unexpected keyword argument 'refresh_token'` — the `token_cache_path` / `refresh_token` constructor kwargs are added in Plans 2-3.

The `2 errors` are fixture-stage variants of the same 11 failures (construction fails before the test body executes); 0 tests passed. Collection itself succeeds (11 collected, no ImportError) because `import iol_client` is safe at module level and `iol_client._token_cache` is referenced only inside test bodies.

**This RED state is the explicit deliverable.** No attempt was made to make the tests pass.

## D-T4 Single-Package Scope (verified)

`grep -c platformdirs` results:
- `packages/iol-client/pyproject.toml`: 1 ✓
- `pyproject.toml` (root): 0 ✓
- `packages/ambito-financiero-client/pyproject.toml`: 0 ✓
- `packages/higyrus-client/pyproject.toml`: 0 ✓
- `packages/matriz-client/pyproject.toml`: 0 ✓
- `packages/wallets-client/pyproject.toml`: 0 ✓

## Baseline Preservation

`uv run --frozen pytest --ignore=verification/test_iol_disk_persistence.py`:

```
973 passed, 1 deselected in 922.08s (0:15:22)
```

Matches the Phase 13 post-fix baseline exactly. The new RED tests are net-additive failures only; the platformdirs dep did not regress any existing import or test.

## Quality Gates

- `ruff check verification/test_iol_disk_persistence.py` — exit 0 (after RUF002 `×`→`x` and B007 loop-var fixes; see Deviations).
- `ruff format --check verification/test_iol_disk_persistence.py` — exit 0.
- `uv lock` — exit 0; platformdirs resolved (5 lock entries).
- TOML validity — `tomllib.loads(...)` exits 0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Lint Bug] RUF002 ambiguous multiplication sign in docstrings**
- **Found during:** Task 2 (`ruff check` returned exit 1)
- **Issue:** The plan/CONTEXT prose uses `×` (U+00D7 MULTIPLICATION SIGN) in "BUG-03 × disk" phrasing; carried verbatim into test docstrings, it tripped `RUF002` (the repo's ruff config selects the full `RUF` rule set and does not ignore RUF002), failing the acceptance criterion `ruff check ... exit 0`.
- **Fix:** Replaced all 11 `×` occurrences with ASCII `x` in docstrings.
- **Files modified:** `verification/test_iol_disk_persistence.py`
- **Commit:** `8f9a6ef`

**2. [Rule 1 - Lint Bug] B007 unused loop control variable**
- **Found during:** Task 2 (`ruff check`)
- **Issue:** The verbatim CONTEXT sentinel-loop shape `for k, v in record.__dict__.items()` never uses `k`, tripping `B007`.
- **Fix:** Changed to `for v in record.__dict__.values()` — semantics identical (still scans every string-valued field).
- **Files modified:** `verification/test_iol_disk_persistence.py`
- **Commit:** `8f9a6ef`

### Process Deviation (documented, not auto-fixed)

**3. [Rule 3 - Protocol reconciliation] Atomic per-task commits vs. single combined commit**
- **Plan text:** Task 3 acceptance said "HEAD commit touches exactly 3 files (`pyproject.toml`, test file, `uv.lock`)" — i.e. a single combined commit.
- **Executor protocol:** mandates one atomic commit per task. This produced 3 commits (`66a9f4b`, `8f9a6ef`, `4aa3193`) collectively touching the same 3 files.
- **Why kept:** The worktree-merge flow (orchestrator merges the per-agent branch) makes atomic granularity strictly better for bisect/forensics and is the hard executor requirement. The net file set committed is identical to the plan's intent (3 files, no extras, no deletions).
- **Impact:** none functional; the combined-commit acceptance grep (`git show --stat HEAD` showing exactly 3 files) does not hold per-commit, but the union of the 3 task commits is exactly those 3 files.

## Threat Surface

No new threat surface beyond what the plan's `<threat_model>` already enumerates. The 4 STRIDE threats (T-14-01..04) remain in the `mitigate` disposition with their mitigations NOT YET IMPLEMENTED — those land in Plans 2-3. T-14-SC (supply chain) is addressed: `platformdirs>=4.0,<5` is a top-1k PyPI package (consumed by pip, virtualenv, black, ipython), pinned, and resolved cleanly via `uv lock` — not ASSUMED/SUS/SLOP.

## Known Stubs

None. The "missing" `iol_client._token_cache` module and `token_cache_path` kwarg are NOT stubs in this plan's scope — they are the explicit RED-in-HEAD contract that Plans 2-3 implement (D-P1). Documented as intentional and resolved by Plans 2-3.

## Notes for Plan 2 / Plan 3

- Plan 2 must create `packages/iol-client/src/iol_client/_token_cache.py` with `logger = logging.getLogger(__name__)` (= `iol_client._token_cache`) so it inherits the v1.1 LOG-02 `RedactingFilter` (anti-Pitfall 7 precondition for `test_disk_persistence_never_logs_token` to go GREEN).
- The tests construct `iol_client.Client(..., refresh_token="SEED-REFRESH-TOKEN", token_cache_path=path)` and `aio.AsyncClient(..., refresh_token=..., token_cache_path=path)`. Plan 2/3 must add BOTH the `token_cache_path` kwarg AND a `refresh_token` constructor kwarg (the current constructors expose neither — `refresh_token` is presently only settable via `configure()`). The RED `TypeError` on `refresh_token` confirms this gap.
- `test_disk_token_preserved_when_no_kwarg_*` requires `_resolve_default_path()` to return `None` under `CI=true` (anti-Pitfall 10) so the seeded-elsewhere file stays byte-untouched.

## Self-Check: PASSED

- Files verified on disk: `verification/test_iol_disk_persistence.py`, `packages/iol-client/pyproject.toml`, `uv.lock`, `.planning/phases/14-iol-disk-persistence-sec-01/14-01-SUMMARY.md` — all FOUND.
- Commits verified in git log: `66a9f4b`, `8f9a6ef`, `4aa3193`, `702e4ca` — all FOUND.
