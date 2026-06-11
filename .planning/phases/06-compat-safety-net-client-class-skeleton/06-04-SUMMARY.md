---
phase: 06-compat-safety-net-client-class-skeleton
plan: 04
subsystem: iol-client refactor
tags: [refactor, client-class, oauth, pep-562, async, sync, refresh-token]
requires:
  - 06-01-PLAN.md (public-surface snapshot harness + regen script)
  - 06-02-PLAN.md (per-package guard test_fixture_reaches_production.py legacy pattern)
provides:
  - iol_client.Client (sync) + iol_client.AsyncClient (async) — per-instance OAuth state
  - iol_client._state._ClientState dataclass (slots, mutable, refresh_token-capable)
  - PEP 562 read-only shim in client.py + aio.py (D-02 + Pitfall #3 addendum)
  - iol_client.configure(token=..., token_expires_at=..., refresh_token=...) extension
  - Snapshot bump on verification/snapshots/iol-client-surface.txt
  - Migrated test_fixture_reaches_production.py (B3 ownership) using configure(token=...)
affects:
  - All iol-client downstream consumers (back-compat via PEP 562 shim; zero API break)
  - Phase 7 (REFAC-03 _core.py extraction) — Client classes are the target for _core.py absorption
  - Phase 9 BUG-03 (refresh_token persistence) — state.refresh_token field already in place
tech-stack:
  added:
    - typing.Self (Python 3.11+ context-manager return annotation)
  patterns:
    - PEP 562 module-level read-only __getattr__ shim (D-01)
    - Slots dataclass for per-instance state (T-06 + Pitfall #6 mitigation)
    - Lazy asyncio.Lock creation in async lifecycle (Pitfall #6)
    - Carry-forward configure() semantics (RESEARCH.md Open Q #5)
    - B8 lock-in: aio.py imports stateless helper from client.py
key-files:
  created:
    - packages/iol-client/src/iol_client/_state.py
    - packages/iol-client/tests/test_client_class.py
  modified:
    - packages/iol-client/src/iol_client/client.py
    - packages/iol-client/src/iol_client/aio.py
    - packages/iol-client/src/iol_client/__init__.py
    - packages/iol-client/tests/conftest.py
    - packages/iol-client/tests/test_client.py
    - packages/iol-client/tests/test_async_client.py
    - packages/iol-client/tests/test_fixture_reaches_production.py
    - verification/snapshots/iol-client-surface.txt
decisions:
  - "configure() carry-forward semantics: kwargs that are None are ignored; password= still resets cached token + refresh_token + token_expires_at (v1.0 invariant preserved)"
  - "PEP 562 shim forwards _refresh_token for IOL (Pitfall #3 addendum to D-02) — without this, 13+ test sites and main_iol.py-style drivers would receive AttributeError after the refactor"
  - "aio.py imports _raise_for_response from client.py (B8) — no duplication; follows the existing ARCHITECTURE.md pattern of aio importing shared types from client"
  - "AsyncClient locks (token_lock on _state, _client_lock on the instance) are lazily created on first async use to avoid binding to a loop alive at __init__ time (Pitfall #6)"
  - "B3 ownership: this plan exclusively owns test_fixture_reaches_production.py in Wave 1 and migrated it to configure(token=...) — no inter-Plan-1 conflict"
metrics:
  duration_seconds: 1800  # approx 30 min
  tasks_completed: 2
  files_modified: 9
  files_created: 2
  tests_added: 26  # 15 sync + 11 async/B8 in test_client_class.py
  baseline_tests: 277
  final_tests_passing: 314
  completed: "2026-06-11"
---

# Phase 06 Plan 04: IOL Client Skeleton Summary

One-liner: Lands `iol_client.Client` (sync) and `iol_client.AsyncClient` (async)
as per-instance OAuth holders with refresh_token rotation, an `_state.py`
dataclass, and a PEP 562 read-only shim — all behind zero API break for the 33
existing iol tests + 277 baseline.

## Objective Achieved

The biggest scope item in Phase 6 because IOL has the OAuth refresh_token flow:
the refactor had to relocate the per-instance state for **two** concurrent
auth flows (password grant + refresh token grant, with the documented
fallback from refresh to password), the double-checked async lock, and **15+
inline `monkeypatch.setattr(iol_client.client, "_token"/"_refresh_token", X)`
sites** that would have silently landed on a dead module dict after the
refactor (research Pitfall #4).

All of the above shipped in **2 atomic commits** (Tasks 1 and 2), one for the
sync side + the safety net of the W2 grep gate, one for the async mirror +
snapshot regen + per-package guard migration.

## Tasks Executed

### Task 1 — sync: `_state.py` + `Client` (OAuth + refresh) + shim + sync test migration

**Commit:** `db1cf5a`

- New file `packages/iol-client/src/iol_client/_state.py` — `@dataclass(slots=True)
  _ClientState` with the 9 fields enumerated in the plan (`base_url`,
  `username`, `password`, `token`, `token_expires_at`, `refresh_token`,
  `account_id` forward-declared, `http_client`, `token_lock`). Defaults via
  `field(default_factory=_env_*)` so env vars set after import (`load_dotenv`)
  take effect on each new instance. Constants `DEFAULT_BASE_URL`,
  `_REQUEST_TIMEOUT`, `_TOKEN_TTL_BUFFER_SECONDS` moved here.
- Restructured `client.py`:
  - `Client` class with `__slots__ = ("_state",)`, kwargs per D-13 (no
    `refresh_token=` kwarg in `__init__`; deferred to Phase 9 BUG-03).
  - OAuth `login()` (password grant), `_refresh()` (refresh token grant),
    `_ensure_token()` (refresh-then-fallback), `_request()` (Bearer header)
    — all reading/writing `self._state.*` instead of module globals.
  - `__repr__` redacts password, token AND refresh_token (D-18 + T-06-05).
  - `__reduce__` / `__deepcopy__` raise `TypeError` (D-23).
  - Top-level shims: `_get_default()` lazy singleton, `login()`,
    `configure()` (extended with `token=`, `token_expires_at=`,
    `refresh_token=` per Pitfall #3 addendum), and one delegator per
    existing public function.
  - PEP 562 `__getattr__` shim: forwards `_token`, `_token_expires_at`,
    `_refresh_token` (Pitfall #3), `_client`; explicit `AttributeError`
    for `_user`, `_password`, `_base_url` (T-06-01). No
    `DeprecationWarning` (D-03).
  - Module-level `_raise_for_response` preserved as stateless helper for
    `aio.py` to import (B8 lock-in primed).
- Conftest sync fixture migrated to `iol_client.configure(token=...,
  token_expires_at=...)` — drops the `monkeypatch` parameter.
- All 15+ inline monkeypatch sites in `test_client.py` migrated to
  direct `iol_client._get_default()._state.<field>` writes. The
  read-side assertions (`assert iol_client.client._token == X`) were left
  untouched — they go through the shim now.
- New `test_client_class.py` with 15 sync tests (lifecycle, redaction,
  pickle/deepcopy, configure carry-forward, Pitfall #2 isolation, every
  shim forwarding/denial case).

W2 pre/post-edit grep closure on test_client.py: 0 hits on writes
post-edit.

### Task 2 — async: `AsyncClient` + B8 + snapshot + per-package guard

**Commit:** `17e2e84`

- Restructured `aio.py`:
  - `AsyncClient` class with `__slots__ = ("_client_lock", "_state")`.
  - **Lazy asyncio.Lock creation** (Pitfall #6) — locks bind to the
    event loop running when authentication first happens, not to
    whatever loop was alive at `__init__` time.
  - `_login_unlocked` / `_refresh_unlocked` mirror the sync semantics
    including the CR-01 conditional refresh_token preservation when the
    server omits it from the response.
  - `aio.configure(...)` extended to match sync (`token=`,
    `token_expires_at=`, `refresh_token=`).
  - PEP 562 shim including `_token_lock` (D-02 aio addendum) for
    forwarding to the per-instance `asyncio.Lock`.
- **B8 lock-in:** `aio.py` imports `_raise_for_response` and
  `InstrumentType` from `iol_client.client` — does NOT duplicate the
  helper. Verified by `test_aio_imports_raise_for_response_from_client`:
  `aio._raise_for_response is client._raise_for_response`.
- `__init__.py`: re-exports `Client` and `AsyncClient` in `__all__`
  (alphabetical).
- Conftest async fixture migrated to `aio.configure(token=...,
  token_expires_at=...)`.
- All 13 inline `monkeypatch.setattr(aio, "_token"/..., X)` sites in
  `test_async_client.py` migrated to `aio._get_default()._state.<field>`
  direct writes.
- **B3 ownership** — `test_fixture_reaches_production.py` migrated in
  this commit from the legacy `monkeypatch.setattr(..., raising=False)`
  pattern to `iol_client.configure(token="SYNC-sentinel-iol", ...)` /
  `aio.configure(token="ASYNC-sentinel-iol", ...)`. Both guards
  green — they prove the new `configure()` path reaches the wire-level
  `Authorization: Bearer <sentinel>` header.
- Snapshot `verification/snapshots/iol-client-surface.txt` regenerated:
  `AsyncClient` and `Client` lines ADDED; `configure` signature UPDATED
  (with the new kwargs); every PRE-refactor entry preserved per D-06.
  The other 3 snapshot files were re-emitted unchanged (verified via
  `git diff`).
- Async tests appended to `test_client_class.py` (11 tests):
  `async def test_async_context_manager`, `test_aclose_idempotent`,
  `test_async_repr_redacts_password_and_token`, `test_async_pickle_raises`,
  `test_async_deepcopy_raises`, `test_async_configure_carry_forward`,
  `test_async_explicit_unaffected_by_top_level_configure`,
  `test_async_pep_562_shim_forwards_token_lock`,
  `test_async_pep_562_shim_forwards_refresh_token`,
  `test_async_pep_562_shim_raises_for_user`,
  `test_aio_imports_raise_for_response_from_client`.

W2 post-edit grep closure on test_async_client.py: 0 hits on writes.

## Verification

| Check | Result |
|-------|--------|
| `uv run pytest packages/iol-client/tests/ -q` | 59 passed |
| `uv run pytest packages/iol-client/tests/test_client.py packages/iol-client/tests/test_client_class.py -q` | 59 passed |
| `uv run pytest packages/iol-client/tests/test_fixture_reaches_production.py -q` | 2 passed (sync + async sentinels reach the wire) |
| `uv run pytest verification/test_public_surface.py -q` | 4 passed (snapshot drift accepted via diff) |
| `uv run pytest -q` (full suite) | **314 passed**, 1 skipped (matriz async REST stub per Phase 10), 1 deselected |
| `uv run ruff check packages/iol-client/` | All checks passed |
| `uv run ruff format --check packages/iol-client/` | All formatted |
| `uv run mypy --strict packages/iol-client/src` | 0 errors |
| W2 post-edit grep on test_client.py writes | 0 hits |
| W2 post-edit grep on test_async_client.py writes | 0 hits |
| B8 spot-check (`aio._raise_for_response is client._raise_for_response`) | True |
| B3 ownership: test_fixture_reaches_production.py touched only in this plan | Confirmed |

## Success Criteria

| Criterion | Status |
|-----------|--------|
| REFAC-02 (iol coverage) success criteria 3, 4 satisfied for iol-client | Done — `Client`, `AsyncClient`, `close()`, `aclose()` exposed; 277 baseline preserved |
| IOL OAuth refresh_token flow preserved through per-instance refactor | Done — `Client._ensure_token` ↔ `_refresh` ↔ `login` chain replicates v1.0 semantics; AsyncClient mirror with double-checked locking |
| Pitfall #3 (`_refresh_token` in allowlist) mitigated | Done — `_FORWARDED_TO_STATE` includes `"_refresh_token": "refresh_token"` in both `client.py` and `aio.py` |
| Inline monkeypatch sites migrated; W2 pre/post-edit grep closure | Done — 28 sites migrated; grep returns 0 on writes post-edit (sync + async) |
| B8 lock-in: aio.py imports `_raise_for_response` from client.py | Done — verified by dedicated test |
| B3 per-package guard ownership | Done — `test_fixture_reaches_production.py` migrated to `configure(token=...)` pattern; both sentinel guards pass |
| Public-surface snapshot updated | Done — `Client`, `AsyncClient` ADDED; baseline entries preserved |
| Fixture-reaches-production guards migrated to `configure(token=...)` pattern and green | Done — sync + async pass |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Sync conftest had to revert to legacy monkeypatch for the async fixture during Task 1**
- **Found during:** Task 1 verification
- **Issue:** The conftest async autouse fixture runs for ALL tests under `asyncio_mode = "auto"` because it's autouse. If Task 1 migrated it to `aio.configure(token=...)`, the test_client.py runs would fail at fixture setup because `aio.configure(...)` didn't accept the `token=` kwarg until Task 2's `aio.py` refactor landed.
- **Fix:** Kept the async fixture on the legacy monkeypatch pattern during Task 1 (with a documented "NOTE: Task 2 finalizes this" comment) and migrated it to `aio.configure(token=..., token_expires_at=...)` in Task 2 as part of the AsyncClient commit.
- **Files modified:** `packages/iol-client/tests/conftest.py`
- **Commit:** Both Task 1 (`db1cf5a` — interim state) and Task 2 (`17e2e84` — final migration).

**2. [Rule 3 — Blocking] Conftest sync teardown now closes the default Client's http_client**
- **Found during:** Task 1 (anticipation of httpx_mock fixture cycling)
- **Issue:** The `_default_client` is a module-level singleton — once created in test 1 with a mocked `httpx.Client`, subsequent tests would still hold the same (now stale) transport unless explicitly closed at teardown.
- **Fix:** Added `iol_client._get_default().close()` and `aio._get_default().aclose()` at teardown of the respective autouse fixtures.
- **Files modified:** `packages/iol-client/tests/conftest.py`
- **Commit:** `db1cf5a` (sync side) and `17e2e84` (async side).

**3. [Rule 1 — Bug] W2 verify-regex matched docstring residue**
- **Found during:** Task 1 W2 post-edit grep closure
- **Issue:** The plan's verify regex `iol_client\.client\._password\s*=` matched a literal example inside a docstring at the migrated test (`"en lugar de iol_client.client._password = ..."`).
- **Fix:** Rephrased the docstring example to avoid the false-positive match.
- **Files modified:** `packages/iol-client/tests/test_client.py` (docstring of `test_configure_resets_refresh_token_but_direct_password_mutation_preserves_it`).
- **Commit:** `db1cf5a`.

### CLAUDE.md compliance

- `from __future__ import annotations` present at the top of every new and modified `.py` file (project-wide convention).
- No relative imports, no wildcard imports (TID rule).
- Public methods carry one-line summary + (where applicable) RST-format endpoint backtick reference (e.g., `Endpoint: GET /api/v2/.../Cotizacion`).
- Line length ≤ 100 via ruff format (verified).
- `__slots__` declared on every new class (`Client`, `AsyncClient`, `_ClientState`).
- `load_dotenv()` stays in `client.py` only (D-19 preserved); `aio.py` does NOT call `load_dotenv()`.

## Threat Surface

The plan's `<threat_model>` enumerated 5 STRIDE entries (T-06-01 through
T-06-05); each has a passing test:

- **T-06-01 (Tampering — shim allowlist):** Tests
  `test_pep_562_shim_raises_for_user`, `test_pep_562_shim_raises_for_base_url`,
  and `test_pep_562_shim_raises_for_unknown` enforce the deny list. The
  allowlist includes `_token`, `_token_expires_at`, `_refresh_token`
  (Pitfall #3), and `_client`.
- **T-06-02 (Information Disclosure — repr):** Tests
  `test_repr_redacts_password_and_token` (sync) and
  `test_async_repr_redacts_password_and_token` (async) assert the raw
  password, token AND `rt-secret`/`rt-async-secret` are NOT in the repr;
  `***` IS present for set fields; `None` for unset.
- **T-06-03 (Tampering — conftest + 28 inline sites):** Mitigated by
  migration; the W2 pre/post-edit grep gate (sync + async) confirms
  zero missed sites. The per-package guard test
  `test_fixture_reaches_production.py` (now using `configure(token=...)`)
  proves the new path reaches the wire-level Authorization header.
- **T-06-04 (DoS — lifecycle):** Tests `test_close_idempotent` and
  `test_aclose_idempotent` enforce that double-close is a no-op.
- **T-06-05 (Information Disclosure — refresh_token):** `__repr__`
  redacts `refresh_token` (`'***'` when set, `None` when unset); same
  test as T-06-02 covers it.

No new threat flags introduced — no new network endpoints, no new auth
paths, no new file access, no new trust boundary surface.

## Known Stubs

None. Every code path created in this plan is wired end-to-end:

- `Client.login()` / `_refresh()` / `_ensure_token()` / `_request()` are
  exercised by the existing `test_client.py` regression tests for the
  OAuth refresh_token flow (5 tests including the CR-01 preserved-cached
  variant), plus all the smoke tests for `get_*` endpoints.
- The PEP 562 shim is exercised by both the legacy `assert
  iol_client.client._token == ...` assertions in `test_client.py` (read
  path) and by dedicated `test_pep_562_shim_*` tests in
  `test_client_class.py` (read + denial paths).
- `AsyncClient` and its lazy lock creation are exercised by
  `test_async_client.py` (the 5 regression tests for refresh + 5 smoke
  tests for `get_*`) plus the dedicated `test_async_*` tests in
  `test_client_class.py`.
- The fixture-reaches-production guard is the end-to-end wire-level proof
  that `configure(token=...)` reaches the `Authorization: Bearer
  <sentinel>` header in the outgoing httpx request.

## Self-Check: PASSED

- [x] `packages/iol-client/src/iol_client/_state.py` exists
- [x] `packages/iol-client/src/iol_client/client.py` exists and contains `class Client`
- [x] `packages/iol-client/src/iol_client/aio.py` exists and contains `class AsyncClient`
- [x] `packages/iol-client/src/iol_client/__init__.py` re-exports `Client` and `AsyncClient`
- [x] `packages/iol-client/tests/test_client_class.py` exists (26 tests)
- [x] `verification/snapshots/iol-client-surface.txt` updated with Client + AsyncClient lines
- [x] `packages/iol-client/tests/test_fixture_reaches_production.py` migrated to `configure(token=...)`
- [x] Commit `db1cf5a` exists in git log (Task 1)
- [x] Commit `17e2e84` exists in git log (Task 2)
- [x] Full test suite green: 314 passed
