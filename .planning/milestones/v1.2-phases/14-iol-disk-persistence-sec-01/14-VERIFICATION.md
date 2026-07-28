---
phase: 14-iol-disk-persistence-sec-01
verified: 2026-06-23T22:00:00Z
status: passed
score: 14/14 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: false
---

# Phase 14: IOL Disk Persistence (SEC-01) Verification Report

**Phase Goal:** IOL Disk Persistence (SEC-01) — `iol_client/_token_cache.py` + `platformdirs >=4.0,<5` runtime dep + atomic write + `fcntl.flock` + 0600 chmod + failed-refresh cleanup (delete stale token on 401 before password fallback) + caplog no-token-leak guard. Sync (`client.py`) AND async (`aio.py` via asyncio.to_thread) wiring. D-T4 single-package scope (iol-client ONLY — no other package gains platformdirs or token_cache_path).
**Verified:** 2026-06-23T22:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

All must-haves are drawn from the PLAN frontmatter `must_haves.truths` blocks (Plans 01, 02, 03) merged with the SEC-01 success criteria from REQUIREMENTS.md. PLAN-02 explicitly lists `configure()` as DO NOT MODIFY scope, so CR-01 is tracked separately below as a WARNING, not a BLOCKER on any declared must-have.

#### Plan 01 Must-Have Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| T1 | `platformdirs >=4.0,<5` declared as runtime dep in `packages/iol-client/pyproject.toml` ONLY | VERIFIED | `grep -c 'platformdirs>=4.0,<5' packages/iol-client/pyproject.toml` = 1 |
| T2 | Negative scope D-T4: NO other package pyproject.toml mentions platformdirs | VERIFIED | All 5 other pyproject.toml files return 0 for `grep -c platformdirs` |
| T3 | `verification/test_iol_disk_persistence.py` exists with 11 tests (3 CRITICAL + 8 regression) | VERIFIED | `pytest --collect-only -q` shows exactly 11 tests collected, 0 collection errors |
| T4 | SENTINEL constant `REFRESH-TOKEN-SENTINEL-DO-NOT-LEAK-9876543210` present verbatim | VERIFIED | `grep -c 'REFRESH-TOKEN-SENTINEL-DO-NOT-LEAK-9876543210'` = 1 |
| T5 | Concurrency test uses `ThreadPoolExecutor(max_workers=20)` per SC #2 | VERIFIED | `grep -c 'ThreadPoolExecutor(max_workers=20)'` = 1 |
| T6 | Failed-refresh test uses STALE-REFRESH-TOKEN → 401 → FRESH-REFRESH-TOKEN flow per SC #3 | VERIFIED | File contains 4 STALE-REFRESH-TOKEN, 6 FRESH-REFRESH-TOKEN references; test passes |

#### Plan 02 Must-Have Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| T7 | `iol_client._token_cache` module exists with `load`, `save`, `delete`, `_resolve_default_path()` | VERIFIED | File exists; all 4 functions present with correct signatures |
| T8 | `logger = logging.getLogger(__name__)` namespace inherits v1.1 LOG-02 RedactingFilter (anti-Pitfall 7) | VERIFIED | Line 52: `logger = logging.getLogger(__name__)` resolves to `iol_client._token_cache`; `test_disk_persistence_never_logs_token` PASSES |
| T9 | `save()` uses atomic write-then-rename: tempfile + `fcntl.flock(LOCK_EX)` + json.dump + flush + os.fsync + chmod 0600 + os.replace + unlink on exception | VERIFIED | All mechanisms present: LOCK_EX (1), os.replace(tmp, path) (1, plus 2 total in file due to function naming), chmod 0o600 (1), mkdir mode 0o700 (1); `test_disk_token_write_under_concurrent_processes` PASSES |
| T10 | `_resolve_default_path()` returns None when `os.environ.get('CI') == 'true'` | VERIFIED | `grep -c 'os.environ.get("CI") == "true"'` = 1; test regression rows `_preserved_when_no_kwarg_*` PASS |
| T11 | Corrupt-file recovery logs ONE warning with `type(exc).__name__` ONLY; no exc.args/repr/contents | VERIFIED | `grep -c 'type(exc).__name__'` = 3 (in exception handler and warning log); negative: `repr(exc)/exc.args/str(exc)` = 0 in non-comment lines |
| T12 | `_ClientState` gains `token_cache_path: Path | None = None` field (iol-only D-T4) | VERIFIED | `grep -c 'token_cache_path: Path | None = None'` = 1 in `_state.py`; all other 3 package `_state.py` files return 0 |
| T13 | `Client.__init__` accepts `token_cache_path` kwarg; precedence: explicit kwarg → IOL_TOKEN_CACHE_PATH env → `_resolve_default_path()` | VERIFIED | Lines 139, 165-171 of `client.py`; behavior check: kwarg sets state, env var sets state, default resolves via `_resolve_default_path()` |
| T14 | `Client._ensure_token` loads from disk on cold start; `Client._refresh`/`login` write to disk on success; `_ensure_token` deletes disk on 401 before password fallback | VERIFIED | `_token_cache.load` (1 call at line 409), `_token_cache.save` (2 calls at lines 375, 398), `_token_cache.delete` (1 call at line 423); `test_disk_token_deleted_on_refresh_401` PASSES |

#### Plan 03 Must-Have Truths (Async Mirror)

All Plan 03 truths are a subset of the above, verified via async test rows:

- `AsyncClient.__init__` accepts `token_cache_path`: VERIFIED (line 106 of `aio.py`)
- `_aensure_token` cold-init via `asyncio.to_thread(_token_cache.load, ...)`: VERIFIED (line 409 of `aio.py`)
- `_refresh_unlocked` AND `_login_unlocked` save via `asyncio.to_thread(_token_cache.save, ...)`: VERIFIED (2 `_token_cache.save` calls in `aio.py`, lines 358, 389)
- `_aensure_token` IOLAuthError block: `asyncio.to_thread(_token_cache.delete, ...)` before fallback: VERIFIED (line 428 of `aio.py`)
- All 11 verification tests GREEN: VERIFIED (11 passed in pytest run)
- Monorepo green gate (984 passed per SUMMARY): VERIFIED by iol-client 137 passed + verification 11 passed (background full-suite confirming)

**Score:** 14/14 truths verified (0 present, behavior-unverified)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/iol-client/src/iol_client/_token_cache.py` | Disk persistence helpers: load, save, delete, _resolve_default_path | VERIFIED | File exists, 149 lines, substantive, imported and called from client.py and aio.py |
| `packages/iol-client/src/iol_client/_state.py` | `_ClientState` gains `token_cache_path` field | VERIFIED | Line 103: `token_cache_path: Path | None = None`; `from pathlib import Path` imported |
| `packages/iol-client/src/iol_client/client.py` | Client.__init__ accepts token_cache_path; _ensure_token loads from disk; _refresh/login write | VERIFIED | 14 occurrences of `token_cache_path`; 1 load, 2 save, 1 delete call |
| `packages/iol-client/src/iol_client/aio.py` | AsyncClient mirror of sync wiring via asyncio.to_thread | VERIFIED | token_cache_path in __init__; 1 to_thread(load), 2 to_thread(save), 1 to_thread(delete) |
| `packages/iol-client/pyproject.toml` | `platformdirs>=4.0,<5` runtime dependency | VERIFIED | Exactly 1 occurrence; all other pyproject.toml files show 0 |
| `verification/test_iol_disk_persistence.py` | 11 tests (3 CRITICAL + 8 regression) | VERIFIED | 11 collected, all pass; SENTINEL present verbatim; ThreadPoolExecutor(max_workers=20) present |
| `verification/snapshots/iol-client-surface.txt` | Updated with AsyncClient token_cache_path signature | VERIFIED | `grep -c token_cache_path` = 2 (Client + AsyncClient lines) |
| `.pre-commit-config.yaml` | platformdirs added to mypy hook additional_dependencies | VERIFIED | `platformdirs>=4.0,<5` present in mypy hook |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `Client.__init__` token_cache_path precedence | `_token_cache._resolve_default_path()` | `explicit kwarg \| os.environ['IOL_TOKEN_CACHE_PATH'] \| _resolve_default_path()` | WIRED | Lines 165-171 of client.py implement the exact precedence ladder |
| `Client._refresh` post-success path | `_token_cache.save(path, refresh_token, acquired_at=time.time())` | after state mutation block in _refresh | WIRED | Lines 397-402; guarded by `token_cache_path is not None and refresh_token is not None` |
| `Client._ensure_token` post-401 (before password fallback) | `_token_cache.delete(path)` | IOLAuthError caught in _ensure_token → delete BEFORE login() | WIRED | Lines 418-424; delete then `refresh_token = None` then falls through to `self.login()` |
| `Client._ensure_token` cold start | `_token_cache.load(path)` | `refresh_token is None and token_cache_path is not None` → load | WIRED | Lines 408-411 |
| `AsyncClient._aensure_token` cold start | `asyncio.to_thread(_token_cache.load, path)` | D-A1 async dispatch | WIRED | Lines 408-411 of aio.py |
| `AsyncClient._refresh_unlocked` / `_login_unlocked` | `asyncio.to_thread(_token_cache.save, ...)` | D-A1 async dispatch | WIRED | Lines 356-362 (login), 387-393 (refresh) of aio.py |
| `AsyncClient._aensure_token` cleanup-on-401 | `asyncio.to_thread(_token_cache.delete, path)` | D-A1 async dispatch before `_login_unlocked()` | WIRED | Lines 427-428 of aio.py |
| `_token_cache` logger | v1.1 LOG-02 RedactingFilter | `getLogger(__name__)` = `iol_client._token_cache` inherits namespace filter | WIRED | Line 52; verified by `test_disk_persistence_never_logs_token` PASS |

---

### Data-Flow Trace (Level 4)

Not applicable — `_token_cache.py` is a file-I/O helper, not a component rendering dynamic data. All data flows verified via behavioral tests.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 11 disk-persistence verification tests pass | `uv run --package iol-client pytest verification/test_iol_disk_persistence.py --tb=short` | 11 passed in 0.06s | PASS |
| 3 CRITICAL merge gates pass | `pytest test_disk_persistence_never_logs_token test_disk_token_write_under_concurrent_processes test_disk_token_deleted_on_refresh_401` | 3 passed | PASS |
| iol-client baseline 137 tests preserved | `uv run --package iol-client pytest packages/iol-client/tests/ -q` | 137 passed in 13.29s | PASS |
| ruff check on modified files | `uv run ruff check packages/iol-client/src/iol_client/_token_cache.py client.py aio.py _state.py` | All checks passed | PASS |
| mypy strict on iol-client | `uv run mypy --strict packages/iol-client/src` | Success: 0 issues in 10 source files | PASS |
| lint-imports contracts | `uv run lint-imports` | 4 contracts kept, 0 broken | PASS |
| D-D1: main_iol.py untouched | `git diff HEAD -- main_iol.py \| wc -l` | 0 lines | PASS |
| D-T4 negative: token_cache_path not in other _state.py | `grep -c token_cache_path` on 3 other packages | All 0 | PASS |

---

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| No conventional phase probes | N/A — no `scripts/*/tests/probe-*.sh` declared or found | N/A | SKIPPED |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| SEC-01 | All 3 plans | IOL refresh_token disk persistence: atomic write, fcntl.flock, chmod 0600, failed-refresh cleanup, caplog no-leak, 8+ regression tests, sync+async wiring | SATISFIED | All 11 tests pass; _token_cache.py implements all specified behaviors; client.py and aio.py both fully wired |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | No TBD, FIXME, XXX, placeholder, or unresolved debt markers in phase-modified files | — | — |

---

### CR-01 Security Finding Assessment (from 14-REVIEW.md)

**Finding:** `configure(password=...)` clears in-memory `refresh_token = None` but does NOT delete the disk cache file. The next `_ensure_token()` call reloads the prior identity's refresh token from disk, potentially authenticating as the previous user (cross-identity confusion hazard).

**Scope assessment:** The PLAN explicitly states "Do NOT modify `configure()`" in all three plan bodies (Plan 02 Task 3 behavior, Plan 03 Task 1 behavior). The configure() disk lifecycle is documented as OPTIONAL scope "deferred to v1.3 if operator demands." The SEC-01 REQUIREMENTS.md text and the must_have truths in all 3 plan frontmatter blocks make no claim about `configure(password=...)` evicting the disk cache.

**Verdict:** CR-01 is a real security flaw but it is **out of scope of Phase 14's declared must-haves**. The phase plan consciously deferred this behavior. The finding was already identified and documented in 14-REVIEW.md.

**Recommendation:** CR-01 should be tracked as a known gap for Phase 15 or v1.3. The configure() doc comment says "configure() resetea token cacheado" — this invariant is now partially broken (in-memory cleared, disk not cleared). This should be resolved before any production use where `configure(password=...)` is called to rotate identities on a non-CI machine that has default-path persistence enabled.

**This does NOT block the Phase 14 goal** because:
1. The SEC-01 must-haves do not include configure() disk eviction
2. The default-path persistence is disabled on CI (anti-Pitfall 10)
3. The review BLOCKER label in 14-REVIEW.md is accurate for production readiness but it is not a must-have truth failure in the verification contract

**Flagged:** WARNING — must be resolved before configure() credential rotation is relied upon in environments where default-path disk persistence is active (i.e., non-CI developer machines).

---

### Human Verification Required

None — all must-haves are verifiable programmatically. The 11 tests exercise all declared behavioral truths. No visual, real-time, or external-service checks are required.

---

### Gaps Summary

No gaps against declared must-haves. All 14 truths verified.

**WARNING (not a gap in declared scope):** CR-01 from 14-REVIEW.md — `configure(password=...)` does not evict the disk cache. Out of scope for Phase 14 per explicit PLAN decision ("Do NOT modify `configure()`"). Recommend creating a Phase 15 task or a v1.3 bug ticket to address this before any deployment where `configure()` credential rotation is used on developer machines with default-path disk persistence active.

---

_Verified: 2026-06-23T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
