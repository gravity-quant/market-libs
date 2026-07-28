---
phase: 14-iol-disk-persistence-sec-01
plan: 03
subsystem: auth
tags: [iol-client, asyncio, refresh-token, disk-persistence, fcntl, platformdirs, oauth, mypy, pre-commit]

# Dependency graph
requires:
  - phase: 14-iol-disk-persistence-sec-01 (Plan 1)
    provides: iol_client._token_cache module (sync fcntl-locked atomic load/save/delete helpers) + _state.token_cache_path field
  - phase: 14-iol-disk-persistence-sec-01 (Plan 2)
    provides: sync Client(token_cache_path=...) wiring — the surface mirrored here via asyncio.to_thread
provides:
  - AsyncClient.__init__ refresh_token + token_cache_path kwargs (zero divergence with sync Client)
  - async _aensure_token cold-init disk load + cleanup-on-401 delete via asyncio.to_thread (D-A1)
  - async _login_unlocked / _refresh_unlocked disk save via asyncio.to_thread (anti-Pitfall 8)
  - regenerated verification/snapshots/iol-client-surface.txt (AsyncClient signature change)
  - Phase 14 SEC-01 consolidated green gate PASS (984 tests + ruff + mypy + lint-imports + pre-commit)
affects: [phase-15-driver-migration, iol-client-async-consumers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Blocking-syscall offload from async: await asyncio.to_thread(_token_cache.<fn>, ...) dispatches the sync fcntl+JSON helper to an executor thread without deadlocking the token_lock holder (D-A1)"
    - "Zero-divergence sync/async surface mirror (D-V3): async __init__ signature is byte-for-byte the sync Client signature minus the httpx client type"

key-files:
  created: []
  modified:
    - packages/iol-client/src/iol_client/aio.py
    - verification/snapshots/iol-client-surface.txt
    - .pre-commit-config.yaml

key-decisions:
  - "Renamed async _ensure_token -> _aensure_token to match the RED verification contract (verification/test_iol_disk_persistence.py calls client._aensure_token()); the only internal caller (_request) was updated. No test in the iol-client async suite invoked the old name as a callable, so the rename is non-breaking."
  - "Mirrored the FULL sync __init__ signature into AsyncClient — added BOTH refresh_token AND token_cache_path (not just token_cache_path) — because the async regression tests pass refresh_token= and D-V3 mandates zero divergence."
  - "Added platformdirs>=4.0,<5 to the mypy pre-commit hook additional_dependencies (Rule 3 blocking fix): Plan 1's _token_cache.py introduced the platformdirs import, but the isolated mypy hook env lacked the stub, breaking the consolidated green gate even though uv run mypy passed."

patterns-established:
  - "asyncio.to_thread for blocking persistence: the 4 disk call sites (load/save/save/delete) each wrap the shared sync helper, preserving a single fcntl.flock implementation across sync + async callers"
  - "Disk read placed OUTSIDE the token_lock (one-time per-cold-instance work); disk writes + delete placed INSIDE the existing critical sections (mirror of sync placement)"

requirements-completed: [SEC-01]

# Metrics
duration: ~35min
completed: 2026-06-24
status: complete
---

# Phase 14 Plan 03: AsyncClient disk persistence + consolidated green gate Summary

**AsyncClient now mirrors the sync Client's refresh_token disk persistence — load/save/delete dispatched via `asyncio.to_thread` — closing Phase 14 SEC-01 with all 11 verification tests GREEN and the full 984-test monorepo gate passing.**

## Performance

- **Duration:** ~35 min (dominated by the 15m21s full-monorepo pytest run)
- **Started:** 2026-06-24T01:05:00Z (approx)
- **Completed:** 2026-06-24T01:41:50Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- `AsyncClient.__init__` gained `refresh_token` + `token_cache_path` kwargs with the same precedence ladder as sync (explicit kwarg > `IOL_TOKEN_CACHE_PATH` env > `_resolve_default_path()`, `None` on CI per anti-Pitfall 10).
- Async OAuth flow now persists to disk: `_aensure_token` cold-init load + cleanup-on-401 delete; `_login_unlocked` / `_refresh_unlocked` save — every call wrapped in `await asyncio.to_thread(...)` (D-A1), reusing the single sync `_token_cache` implementation (one fcntl.flock body for sync + async).
- All 11 `verification/test_iol_disk_persistence.py` tests GREEN (3 CRITICAL + 8 regression, the 4 async rows flipped RED→GREEN).
- Surface snapshot regenerated (enumerator walks `__init__` signatures — outcome (b)); only `iol-client-surface.txt` changed.
- Consolidated Phase 14 green gate PASS: pytest 984 passed (threshold ≥981), ruff check + ruff format --check, mypy strict, lint-imports (4 contracts kept), pre-commit --all-files (idempotent).

## Task Commits

Each task was committed atomically:

1. **Task 1: Mirror Plan 2 sync wiring into AsyncClient via asyncio.to_thread** - `1e940dd` (feat)
2. **Task 2: Regenerate iol-client surface snapshot** - `8beb77a` (test)
3. **Task 3: Consolidated green gate + pre-commit mypy hook fix** - `535a58e` (fix)

_Note: Task 1 was authored test-first against the pre-committed RED verification suite (no new test file — the contract already existed in HEAD)._

## Files Created/Modified
- `packages/iol-client/src/iol_client/aio.py` - Async disk-persistence wiring: `__init__` precedence resolution, `_aensure_token` load+delete, `_login_unlocked`/`_refresh_unlocked` save; method rename `_ensure_token`→`_aensure_token`.
- `verification/snapshots/iol-client-surface.txt` - `AsyncClient` signature line now carries `refresh_token` + `token_cache_path` (the only diff).
- `.pre-commit-config.yaml` - `platformdirs>=4.0,<5` added to mypy hook `additional_dependencies` (Rule 3 gate fix).

## Decisions Made
- **Method rename `_ensure_token` → `_aensure_token`:** the committed-RED verification suite calls `client._aensure_token()`. The plan body referred to `_ensure_token`, but the test contract is authoritative. The sole internal caller (`_request`) was updated; no async test invoked the old name as a callable.
- **Full signature mirror (refresh_token + token_cache_path):** the async regression tests construct `AsyncClient(refresh_token=..., token_cache_path=...)`, and D-V3 demands zero sync/async divergence. The sync `Client` already exposed `refresh_token`; the async side was missing it — added here.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `platformdirs` to the mypy pre-commit hook's `additional_dependencies`**
- **Found during:** Task 3 (consolidated green gate, pre-commit step)
- **Issue:** `uv run mypy` passed, but the `pre-commit run --all-files` mypy hook (isolated venv) failed with `Cannot find implementation or library stub for module named "platformdirs"` on `iol_client/_token_cache.py:50`. Plan 1 introduced this runtime import; the hook env's `additional_dependencies` list was never updated to include it, so the gate could not go green.
- **Fix:** Added `platformdirs>=4.0,<5` (matching the iol-client pyproject constraint) to the mypy hook in `.pre-commit-config.yaml`.
- **Files modified:** `.pre-commit-config.yaml`
- **Verification:** `pre-commit run --all-files` now passes all hooks; second run idempotent (no file mutations).
- **Committed in:** `535a58e` (Task 3 commit)

**2. [Plan-spec correction] Renamed async `_ensure_token` → `_aensure_token`**
- **Found during:** Task 1
- **Issue:** Plan `<behavior>`/`<action>` instructed modifying `AsyncClient._ensure_token`, but the pre-committed RED verification suite calls `client._aensure_token()`. Honoring the plan's literal method name would leave 4 async verification tests RED (AttributeError).
- **Fix:** Renamed the method and updated the single internal caller in `_request`; updated two docstring references for accuracy.
- **Files modified:** `packages/iol-client/src/iol_client/aio.py`
- **Verification:** All 11 verification tests GREEN; iol-client suite (137 tests) preserved.
- **Committed in:** `1e940dd` (Task 1 commit)

---

**Total deviations:** 2 (1 Rule 3 blocking, 1 plan-spec correction)
**Impact on plan:** Both were necessary to reach the consolidated green gate. The rename is the test contract winning over the plan prose; the pre-commit fix closes an infrastructure gap left by Plan 1. No scope creep — single-package iol-client boundary preserved (D-T4), `main_iol.py` untouched (D-D1).

## Issues Encountered
- The plan's `regen_snapshots iol-client` invocation does not match the actual script (it takes no args and regenerates all 4 snapshots). Ran `uv run python verification/regen_snapshots.py`; only `iol-client-surface.txt` changed (the other 3 regenerated byte-identical). Idempotent on re-run.

## Verification Results

| Gate step | Result |
|-----------|--------|
| `verification/test_iol_disk_persistence.py` | 11 passed (3 CRITICAL + 8 regression) |
| iol-client package suite | 137 passed |
| Full monorepo `uv run pytest` | **984 passed**, 1 deselected (≥981 threshold met) |
| `uv run ruff check` | exit 0 |
| `uv run ruff format --check` | 153 files already formatted, exit 0 |
| `uv run mypy` | Success, 51 source files, exit 0 |
| `uv run lint-imports` | 4 contracts kept, 0 broken, exit 0 |
| `pre-commit run --all-files` (x2) | all Passed, idempotent, exit 0 |
| D-T4 (platformdirs in other pyproject) | all 0 |
| D-T4 (token_cache_path in other _state.py) | all 0 |
| D-D1 (main_iol.py diff across Plans 1+2+3) | 0 lines |

## Snapshot Outcome
**Outcome (b)** per Task 2 step 3: the enumerator walks `__init__` signatures (`str(inspect.signature(class))`), so the `AsyncClient` line gained `refresh_token: 'str | None' = None, token_cache_path: 'Path | None' = None`. `grep -c token_cache_path` on the snapshot returns 2 (Client + AsyncClient). No other snapshot file touched; idempotent.

## Next Phase Readiness
- **Phase 14 SEC-01 is shippable.** Sync + async refresh-token disk persistence both land, both gated.
- **Phase 15 driver-migration handoff:** `main_iol.py` adoption is OPTIONAL. The `token_cache_path` kwarg defaults preserve v1.1 behavior when unset (default-path resolution returns `None` on CI; on dev machines it resolves to the platformdirs path, enabling persistence transparently). Operators who do not want disk persistence at all can pass `token_cache_path=None`-equivalent by running under `CI=true` or by not relying on the default path — but note: on a non-CI dev box the default path IS resolved, so persistence is on by default outside CI. Phase 15 should document this default-on-dev behavior if it surfaces the kwarg in the driver.
- No blockers.

## Self-Check: PASSED

- FOUND: packages/iol-client/src/iol_client/aio.py
- FOUND: verification/snapshots/iol-client-surface.txt
- FOUND: .pre-commit-config.yaml
- FOUND commit: 1e940dd
- FOUND commit: 8beb77a
- FOUND commit: 535a58e

---
*Phase: 14-iol-disk-persistence-sec-01*
*Completed: 2026-06-24*
