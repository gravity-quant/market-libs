---
phase: 14-iol-disk-persistence-sec-01
plan: 02
subsystem: iol-client
tags: [SEC-01, disk-persistence, refresh-token, fcntl, atomic-write, sync]
requires:
  - "14-01: verification/test_iol_disk_persistence.py (RED contract) + platformdirs dep"
provides:
  - "iol_client._token_cache module (load/save/delete/_resolve_default_path)"
  - "_ClientState.token_cache_path field (iol-only D-T4)"
  - "Client(token_cache_path=...) + Client(refresh_token=...) kwargs (sync)"
  - "Sync disk-cache wiring: cold load + write-on-refresh/login + delete-on-401"
affects:
  - "Plan 3 (Wave 3) mirrors this into aio.py to turn the 4 async rows GREEN"
tech-stack:
  added:
    - "platformdirs>=4.0,<5 (consumed; declared in Plan 1)"
  patterns:
    - "POSIX atomic write-then-rename (tempfile + fcntl.flock LOCK_EX + fsync + chmod 0600 + os.replace)"
    - "fcntl.flock LOCK_SH for reads, LOCK_EX for writes"
    - "Sanitized corrupt-recovery logging (type(exc).__name__ only — D-C1)"
    - "logging.getLogger(__name__) namespace inheritance for RedactingFilter (anti-Pitfall 7)"
key-files:
  created:
    - "packages/iol-client/src/iol_client/_token_cache.py"
  modified:
    - "packages/iol-client/src/iol_client/_state.py"
    - "packages/iol-client/src/iol_client/client.py"
    - "verification/test_iol_disk_persistence.py (fixed broken match_content matchers)"
    - "verification/snapshots/iol-client-surface.txt (regen for new Client kwargs)"
decisions:
  - "Added Client(refresh_token=...) kwarg (not in plan signature) because the written/loaded sync regression tests construct Client(refresh_token=...) — required to satisfy the verification contract"
  - "Fixed truncated match_content matchers in the verification file (Plan 1 RED) to the full urlencoded body shape — the original matchers were unsatisfiable by any correct client under pytest-httpx exact-match semantics"
  - "acquired_at=time.time() read at the call site (in _refresh + login), not inside save(), keeping the helper pure/deterministic"
metrics:
  duration: "~30 min"
  completed: "2026-06-23"
  tasks: 3
  files: 5
status: complete
---

# Phase 14 Plan 02: IOL refresh_token disk persistence — sync side Summary

Sync-side SEC-01: a POSIX-locked, atomic-write `iol_client._token_cache` module plus `Client(token_cache_path=...)` wiring that loads the refresh_token from disk on cold start, persists it after every successful refresh/login, and deletes the stale token before the password fallback on a refresh-401 — turning the 3 CRITICAL merge gates and 4 sync regression rows GREEN while the 4 async rows stay RED for Plan 3.

## What Was Built

### Task 1 — `_token_cache.py` (commit 47eefb7)
New package-private module with `load(path)`, `save(path, refresh_token, *, acquired_at)`, `delete(path)`, and `_resolve_default_path()`:
- **save**: `path.parent.mkdir(mode=0o700)` → unique tempfile (`<name>.tmp.<pid>.<randhex>`) → `fcntl.flock(LOCK_EX)` → `json.dump` → `flush` + `os.fsync` → `chmod 0600` on the tempfile → `os.replace(tmp, path)` (atomic). On any exception the tempfile is unlinked and the error re-raised. No success log site.
- **load**: opens under `fcntl.flock(LOCK_SH)`, validates `version == 1` + non-empty `refresh_token` str + float-compatible `acquired_at`. Missing file → `None` silently. Any other failure → ONE warning carrying only `type(exc).__name__` (D-C1, never the exception/args/repr/contents) → `None`; the corrupt file is left intact.
- **_resolve_default_path**: returns `None` when `CI=true` (anti-Pitfall 10), else `platformdirs.user_data_dir("iol-client", "market-libs") / refresh_token.json`. Never raises, never touches the filesystem.
- **logger** = `logging.getLogger(__name__)` → `iol_client._token_cache`, inheriting the v1.1 LOG-02 `RedactingFilter` (anti-Pitfall 7).

### Task 2 — `_state.py` field (commit 3886c13)
`_ClientState` gains `token_cache_path: Path | None = None` as the last field (preserves `dataclasses.fields()` ordering) + `from pathlib import Path`. iol-only per D-T4 — the other 4 packages' `_state.py` are untouched (verified: 0 occurrences each).

### Task 3 — `client.py` wiring (commit 82c2633)
- **`__init__`**: new keyword-only `refresh_token` + `token_cache_path` kwargs. Precedence ladder: explicit kwarg → `IOL_TOKEN_CACHE_PATH` env → `_token_cache._resolve_default_path()` (None on CI). Always sets `self._state.token_cache_path` (possibly None).
- **`_ensure_token`**: cold-start disk load (first call only — `refresh_token is None and token_cache_path is not None`); on `IOLAuthError` from `_refresh()`, deletes the disk file + clears in-memory refresh_token BEFORE falling through to `self.login()` (anti-Pitfall 8).
- **`_refresh` + `login`**: after the state mutation block, persist the current refresh_token via `_token_cache.save(..., acquired_at=time.time())` when disk caching is enabled. `login` writing the fresh token is what makes the 401-recovery gate end with the FRESH token on disk.

## Verification Results

- 3 CRITICAL merge gates GREEN: `test_disk_persistence_never_logs_token` (Pitfall 7), `test_disk_token_write_under_concurrent_processes` (Pitfall 9), `test_disk_token_deleted_on_refresh_401` (Pitfall 8).
- 4 sync regression rows GREEN (`*_sync`).
- 4 async rows RED as intended — `AsyncClient.__init__() got an unexpected keyword argument 'token_cache_path'` (Plan 3 owns aio.py).
- `verification/test_iol_disk_persistence.py`: **7 passed, 4 failed** (expected).
- iol-client baseline suite: **137 passed**.
- Full monorepo suite: **979 passed, 5 failed** — the 5 are the 4 expected async rows + the snapshot-idempotency test which was RED only until the regenerated snapshot was committed (now GREEN at HEAD).
- Quality: `ruff check`, `ruff format --check`, `mypy --strict packages/iol-client/src` all exit 0.
- Negative scope verified: `main_iol.py` untouched (D-D1, 0 diff lines); `platformdirs` absent from the other 4 packages' src (D-T4, 0); no `repr(exc)`/`exc.args`/`str(exc)` leak outside comments in `_token_cache.py` (0).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `Client(refresh_token=...)` kwarg**
- **Found during:** Task 3.
- **Issue:** `test_disk_token_written_after_successful_refresh_sync` (and its async mirror) construct `Client(refresh_token="SEED-REFRESH-TOKEN", ...)`, but the plan's Task 3 `__init__` signature ordering (`...token_expires_at, token_cache_path, max_retries...`) omitted `refresh_token`. The verification contract is unsatisfiable without it. Historically `Client.__init__` did NOT accept `refresh_token` (D-13), but the Phase 14 disk tests require it.
- **Fix:** Added keyword-only `refresh_token: str | None = None` before `token_cache_path`; body sets `self._state.refresh_token` when provided (mirrors the existing `configure(refresh_token=...)` surface).
- **Files modified:** `packages/iol-client/src/iol_client/client.py`
- **Commit:** 82c2633

**2. [Rule 1 - Bug] Fixed broken `match_content` matchers in the verification file**
- **Found during:** Task 3.
- **Issue:** The Plan 1 RED tests registered mocks with truncated `match_content=b"grant_type=refresh_token"` / `b"grant_type=password"`. pytest-httpx 0.36 `match_content` is an EXACT full-body match, so these never matched the real client body (`refresh_token=<seed>&grant_type=refresh_token`), surfacing as `httpx.TimeoutException` (no response found) plus an unused-mock teardown ERROR. The intended GREEN state was unreachable regardless of implementation correctness.
- **Fix:** Replaced each truncated matcher with the full urlencoded body the real client emits (per-test seed token), matching the existing iol-client test-suite convention (e.g. `packages/iol-client/tests/test_refresh_token_lifecycle_async.py`).
- **Files modified:** `verification/test_iol_disk_persistence.py`
- **Commit:** 82c2633

**3. [Rule 2 - Missing critical] Regenerated the iol-client public-surface snapshot**
- **Found during:** Task 3 full-suite run.
- **Issue:** `test_snapshot_regen_is_idempotent` failed because the new `Client` kwargs changed the public signature, leaving the committed `verification/snapshots/iol-client-surface.txt` stale.
- **Fix:** Ran `verification/regen_snapshots.py` and committed the regenerated iol snapshot in the SAME commit as the source change (only the sync `Client` line changed; the other 3 packages' snapshots were byte-identical; the `AsyncClient` line is intentionally unchanged for Plan 3).
- **Files modified:** `verification/snapshots/iol-client-surface.txt`
- **Commit:** 82c2633

## Known Stubs

None. The async surface intentionally remains unwired — that is Plan 3's scope, tracked by the 4 RED `*_async` rows, not a stub in this plan's deliverables.

## Self-Check: PASSED

- FOUND: `packages/iol-client/src/iol_client/_token_cache.py`
- FOUND: `_ClientState.token_cache_path` field + `Client` kwargs wiring
- FOUND: commit 47eefb7 (Task 1), 3886c13 (Task 2), 82c2633 (Task 3)
- 3 CRITICAL gates + 4 sync rows GREEN; 4 async rows RED (intended); iol baseline 137 passed; full suite 979 passed (5 expected/transient failures resolved or owned by Plan 3).
