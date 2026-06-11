---
phase: 06-compat-safety-net-client-class-skeleton
plan: 05
subsystem: higyrus-client
tags: [refactor, client-skeleton, async, pep562, safety-net]
requires:
  - 06-01-snapshot-baseline (verification/snapshots/higyrus-client-surface.txt baseline; verification/test_public_surface.py + regen_snapshots.py)
  - 06-02-fixture-reaches-production-guards (packages/higyrus-client/tests/test_fixture_reaches_production.py legacy sync+async guards)
provides:
  - higyrus_client.Client (sync class with __slots__=('_state',), lifecycle, redacted __repr__, raises pickle/deepcopy)
  - higyrus_client.AsyncClient (async class with __slots__=('_client_lock', '_state'), aclose, lifecycle, redacted __repr__)
  - higyrus_client._state._ClientState (slots dataclass with 9 fields including client_id and account_id forward-declared)
  - higyrus_client.configure(token=, token_expires_at=) carry-forward
  - higyrus_client.aio.configure(token=, token_expires_at=) carry-forward
  - PEP 562 shim in higyrus_client.client: _token, _token_ts (rename→token_expires_at), _client forwarders; AttributeError for credential names
  - PEP 562 shim in higyrus_client.aio: same + _token_lock forwarder
  - B8 single source of truth: aio._raise_for_response IS client._raise_for_response
  - URL-encoding safe="/" preserved in Client._request and AsyncClient._request
affects:
  - REFAC-02 success criteria 3, 4 satisfied for higyrus-client
  - 277-test v1.1 baseline preserved (315 total now: 288 baseline + 27 new)
tech-stack:
  added: []
  patterns: ["pep562_shim_with_rename", "carry_forward_configure", "lazy_default_client", "double_checked_locking_async", "slots_dataclass_mutable_state"]
key-files:
  created:
    - path: packages/higyrus-client/src/higyrus_client/_state.py
      role: "@dataclass(slots=True) _ClientState with higyrus fields incl. client_id and account_id forward-declared"
  modified:
    - path: packages/higyrus-client/src/higyrus_client/client.py
      role: "Add Client class + _raise_for_response shared helper + PEP 562 shim; preserve URL-encoding safe='/' quirk"
    - path: packages/higyrus-client/src/higyrus_client/aio.py
      role: "Add AsyncClient class with double-checked locking + PEP 562 shim; import _raise_for_response from client (B8)"
    - path: packages/higyrus-client/src/higyrus_client/__init__.py
      role: "Re-export Client and AsyncClient in __all__"
    - path: packages/higyrus-client/tests/conftest.py
      role: "Migrate _configure_sync and _configure_async to configure(token=, token_expires_at=); drop monkeypatch parameter"
    - path: packages/higyrus-client/tests/test_client.py
      role: "Migrate test_login_falla_si_falta_base_url to configure(base_url='') per Pitfall #4"
    - path: packages/higyrus-client/tests/test_async_client.py
      role: "No edits needed — fixture sites covered by conftest migration; no inline monkeypatch sites in test bodies"
    - path: packages/higyrus-client/tests/test_fixture_reaches_production.py
      role: "Migrate sync + async guards from monkeypatch.setattr to configure(token=); B3 — this plan exclusively owns this file in Wave 1"
    - path: verification/snapshots/higyrus-client-surface.txt
      role: "Regenerate: +Client, +AsyncClient lines; configure signature extended (no baseline entries removed — D-06)"
  added_tests:
    - path: packages/higyrus-client/tests/test_client_class.py
      role: "27 tests: 14 sync (Client lifecycle + repr + pickle + PEP 562 shim + URL-encoding) + 13 async (AsyncClient lifecycle + aclose + PEP 562 async shim incl. _token_lock + URL-encoding + B8 identity)"
decisions:
  - "Cross-pkg rename _token_ts → token_expires_at: internal field is absolute expiry epoch (matches iol's convention). PEP 562 shim maps _token_ts → state.token_expires_at for backward compat. Conftest legacy value 9_999_999_999.0 is already a valid future epoch (year 2286), so the migration is mechanical."
  - "B8 lock-in: aio.py imports _raise_for_response from client.py rather than duplicating the body. Module-level __all__ in aio.py re-exports the imported name so the test test_aio_imports_raise_for_response_from_client (identity check) passes."
  - "configure() carry-forward semantic: replaces the default-client/default-async-client with a NEW instance that copies values for kwargs left None. This guarantees atomic reset and matches the legacy 'set _token=None on configure' behavior at the Client level (new instance has token=None unless explicitly passed)."
  - "AsyncClient lock lifecycle: _client_lock is a __slots__ attribute on the instance, created lazy on first access; state.token_lock lives in _ClientState (also lazy) so it can be exposed via the PEP 562 _token_lock shim. Both bind to the current event loop on first use, avoiding the 'lock bound to import-time loop' bug (research Pitfall #6)."
  - "configure() in aio.py is synchronous (it cannot await aclose()), so when a test fixture calls configure() the previous default's http_client is NOT closed automatically. The conftest teardown still calls `await aio.aclose()` to close it — documented in the module docstring."
metrics:
  duration_minutes: ~35
  completed: "2026-06-11"
  tasks_completed: 2
  files_created: 2  # _state.py + test_client_class.py
  files_modified: 7  # client.py, aio.py, __init__.py, conftest.py, test_client.py, test_fixture_reaches_production.py, snapshot
  commits: 4  # 2 RED + 2 GREEN (TDD)
  tests_added: 27  # 14 sync + 13 async
  tests_passing: "315 passed, 1 skipped (matriz aio Phase 10), 1 deselected"
---

# Phase 06 Plan 05: Compat Safety Net + Client Class Skeleton (higyrus-client) Summary

Higyrus Client / AsyncClient skeletons landed: 398 LOC of module-level globals + functions in `client.py` and 402 LOC in `aio.py` absorbed into `_state.py` + `Client` + `AsyncClient`, with PEP 562 read-only shim for legacy `_token`/`_token_ts`/`_client` names, internal field rename `_token_ts → token_expires_at`, URL-encoding `safe='/'` quirk preserved, B8 enforcement of shared `_raise_for_response`, and full conftest + per-package guard migration to `configure(token=..., token_expires_at=...)`.

## Tasks

| # | Name | Commit | Status |
|---|------|--------|--------|
| 1 | _state.py + Client (sync) + sync conftest + sync test migration + URL-encoding regression test | `4bf1ec2` (RED) → `e5e69e0` (GREEN) | done |
| 2 | AsyncClient + async conftest + async test migration + __init__.py + snapshot + per-package guard migration | `93e2f27` (RED) → `c804957` (GREEN) | done |

## TDD Gate Compliance

- Task 1: RED commit `4bf1ec2` (13 of 14 tests fail) → GREEN commit `e5e69e0` (all 43 sync tests pass).
- Task 2: RED commit `93e2f27` (12 of 12 new async tests fail) → GREEN commit `c804957` (all 80 higyrus tests pass).

## Verification

- `uv run pytest packages/higyrus-client/tests -q` → 80 passed in 0.36s.
- `uv run pytest verification/ -q -k "higyrus or public_surface"` → 4 passed (1 per package).
- `uv run pytest packages/higyrus-client/tests/test_fixture_reaches_production.py -q` → 2 passed (sync + async).
- `uv run pytest -q` → 315 passed, 1 skipped (matriz aio Phase 10), 1 deselected. **Baseline preserved.**
- `uv run ruff check packages/higyrus-client/` → All checks passed!
- `uv run ruff format --check packages/higyrus-client/` → 12 files already formatted.
- `uv run mypy --strict packages/higyrus-client/src` → Success: no issues found in 7 source files.
- B8 spot-check: `from higyrus_client.client import _raise_for_response as s; from higyrus_client.aio import _raise_for_response as a; print(s is a)` → `True`.
- Manual: `grep -n "monkeypatch.setattr(higyrus_client.client" packages/higyrus-client/tests/` → 0 hits (all migrated).
- Manual: `grep -n "monkeypatch.setattr(aio" packages/higyrus-client/tests/` → 0 hits (all migrated).

## Architectural Notes

### `_token_ts → token_expires_at` rename mapping

The legacy higyrus globals stored `_token_ts = time.time()` at login completion and computed staleness via `(time.time() - _token_ts) < 23h`. The new `_ClientState.token_expires_at` stores absolute epoch (`time.time() + 23h`) and the freshness check becomes `time.time() < token_expires_at`. This matches iol's convention (already absolute epoch) and is the convention for Phase 9+ cross-pkg work.

External backward-compat: the PEP 562 shim in `client.py` and `aio.py` maps `_token_ts` (legacy read name) → `state.token_expires_at` (new field). Conftest fixtures and external tests that read `pkg.client._token_ts` continue to work; writes via `monkeypatch.setattr(pkg.client, "_token_ts", X)` no longer reach state (Pitfall #1 — module dict writes bypass `__getattr__`) and must migrate to `configure(token_expires_at=X)`. Conftest already migrated.

The conftest fixture's legacy value `9_999_999_999.0` (chosen as "a big number") happens to be a valid future epoch (year 2286), so the migration is mechanical: `monkeypatch.setattr(higyrus_client.client, "_token_ts", 9_999_999_999.0)` → `higyrus_client.configure(token_expires_at=9_999_999_999.0)`. Both expressions cache a non-stale token for the test's duration.

### URL-encoding `safe="/"` preserved (Higyrus IIS quirk, F-01..F-06)

Higyrus IIS rejects `%2F` in query strings with `400 "formato dd/mm/yyyy"`. The legacy `_request` used `urlencode(merged, doseq=True, quote_via=quote, safe="/")` to keep `/` literal in date params like `08/05/2026`. Both `Client._request` and `AsyncClient._request` preserve this verbatim, and a new regression test (`test_url_encoding_preserves_slash_in_query` + async mirror) guards it. The existing `test_request_preserves_literal_slash_in_query` regression test from Phase 4 also continues to pass.

### B8: aio.py imports `_raise_for_response` from client.py

`packages/higyrus-client/src/higyrus_client/aio.py` line 47:
```python
from higyrus_client.client import _raise_for_response  # B8: shared helper
```

This avoids duplicating the error-mapping logic. A new test `test_aio_imports_raise_for_response_from_client` asserts identity (`is`), not equality, to lock the invariant.

### configure() carry-forward atomically replaces the default

Calling `configure(token=...)` replaces the module-level `_default_client` (or `_default_async_client`) with a NEW `Client`/`AsyncClient` instance. The new instance copies values from the old default for any kwarg passed as `None`. Side effect:

- For the sync case, the old default's `http_client.close()` is called before the swap.
- For the async case, the swap is synchronous and the old default's `http_client.aclose()` is NOT awaited automatically (you can't await in a sync function). Tests' teardown still calls `await aio.aclose()` to clean up.

### AsyncClient lock lifecycle

- `self._client_lock` is in `__slots__` (instance-bound, created lazy on first `_ensure_client_lock`).
- `self._state.token_lock` is in `_ClientState` (shared shape with sync; created lazy on first `_ensure_token_lock`).
- Both bind to the current event loop on first use, avoiding the import-time-loop binding bug (Research Pitfall #6).
- `_token_lock` is also exposed via the PEP 562 shim (`aio._token_lock` → `state.token_lock`), so legacy callers can introspect it.

### Per-package guard ownership (B3)

`packages/higyrus-client/tests/test_fixture_reaches_production.py` is exclusively owned by this plan in Wave 1. No other Wave 1 plan touches it. The file's sync + async tests now use `configure(token=..., token_expires_at=...)` instead of the legacy `monkeypatch.setattr` which no longer reaches state.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] aio.configure() needs token=/token_expires_at= kwargs in Task 1**

- **Found during:** Task 1 GREEN (sync tests).
- **Issue:** The conftest's `_configure_async` autouse fixture calls `aio.configure(token=..., token_expires_at=...)` — autouse means it runs for EVERY test, including sync tests. After migrating the conftest in Task 1, every sync test errored with `TypeError: configure() got an unexpected keyword argument 'token'` because `aio.configure` hadn't been extended yet.
- **Fix:** Extended `aio.configure()` signature in Task 1 (before Task 2's full async refactor) to accept `token=` and `token_expires_at=` as a Phase 6 prerequisite, with carry-forward semantic preserved. This is consistent with RESEARCH.md's "Conftest Migration Pattern" which prescribes extending `configure()` as a per-package prerequisite. The full AsyncClient refactor still lands in Task 2 — only the signature extension moved earlier.
- **Files modified:** `packages/higyrus-client/src/higyrus_client/aio.py` (configure signature).
- **Commit:** `e5e69e0` (folded into Task 1 GREEN).

**2. [Rule 1 — Code style] Inline `from urllib.parse import` in AsyncClient._request**

- **Found during:** Task 2 GREEN (initial draft).
- **Issue:** Initial draft of `AsyncClient._request` had the `urlencode` / `quote` import inline inside the function for visual proximity to the comment block. This violates the project's "imports at module top" convention.
- **Fix:** Moved the import to module-level alongside `httpx` and other stdlib.
- **Files modified:** `packages/higyrus-client/src/higyrus_client/aio.py`.
- **Commit:** `c804957` (folded into Task 2 GREEN).

**3. [Rule 1 — Lint] `__slots__` natural-sort violation**

- **Found during:** Task 2 GREEN (ruff check after AsyncClient implementation).
- **Issue:** Ruff `RUF023` flagged `AsyncClient.__slots__ = ("_state", "_client_lock")` as not naturally sorted.
- **Fix:** Reordered to `("_client_lock", "_state")`.
- **Files modified:** `packages/higyrus-client/src/higyrus_client/aio.py`.
- **Commit:** `c804957` (folded into Task 2 GREEN).

**4. [Rule 1 — Lint] Multiple ruff `I001` (import ordering) + `SIM108` (ternary) fixes during Task 1**

- **Found during:** Task 1 GREEN (post-implementation ruff check).
- **Issue:** Ruff flagged `I001` import sorting in `__init__.py` and `test_client_class.py`; `SIM108` for two if/else blocks in `aio.configure()` that should be ternary expressions; `F401` for an unused `aio` import in the sync-only Task 1 stage.
- **Fix:** Ran `ruff check --fix` and `ruff format`, manually re-added `aio` import in Task 2 when async tests joined the file.
- **Files modified:** `packages/higyrus-client/src/higyrus_client/__init__.py`, `packages/higyrus-client/src/higyrus_client/aio.py`, `packages/higyrus-client/tests/test_client_class.py`.
- **Commit:** `e5e69e0` (folded into Task 1 GREEN).

No architectural deviations (Rule 4): the plan executed as written. The rename, URL-encoding preservation, B8 enforcement, B3 ownership, and Pitfall #4 mitigation all landed exactly per the plan's `truths` list.

### Auth Gates Encountered

None. All tests use `pytest_httpx` mocks; no live-API calls executed.

## Known Stubs

None. All migrations complete; no stubs introduced.

## Threat Flags

No new security-relevant surface introduced beyond the plan's `<threat_model>`. The PEP 562 shim allowlist + rename mapping (T-06-01), repr redaction (T-06-02), conftest migration (T-06-03), aclose idempotence (T-06-04), and URL-encoding safe='/' (T-06-06) are all mitigated as designed.

## Self-Check

Run automatically before commit:

- FOUND: `packages/higyrus-client/src/higyrus_client/_state.py`
- FOUND: `packages/higyrus-client/src/higyrus_client/client.py`
- FOUND: `packages/higyrus-client/src/higyrus_client/aio.py`
- FOUND: `packages/higyrus-client/src/higyrus_client/__init__.py`
- FOUND: `packages/higyrus-client/tests/conftest.py`
- FOUND: `packages/higyrus-client/tests/test_client.py`
- FOUND: `packages/higyrus-client/tests/test_client_class.py`
- FOUND: `packages/higyrus-client/tests/test_fixture_reaches_production.py`
- FOUND: `verification/snapshots/higyrus-client-surface.txt`
- FOUND commit `4bf1ec2`: test(06-05) RED sync
- FOUND commit `e5e69e0`: feat(06-05) GREEN sync
- FOUND commit `93e2f27`: test(06-05) RED async
- FOUND commit `c804957`: feat(06-05) GREEN async

## Self-Check: PASSED
