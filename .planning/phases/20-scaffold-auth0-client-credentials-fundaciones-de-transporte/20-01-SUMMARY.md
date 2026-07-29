---
phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
plan: 01
subsystem: infra
tags: [market-data, auth0, httpx, tenacity, hatchling, uv-workspace, retry-transport]

# Dependency graph
requires:
  - phase: (existing iol-client package)
    provides: reference layout for pyproject, exceptions, _state, _transport/_atransport (D-01 file set)
provides:
  - "market-data-client package skeleton (pyproject.toml, py.typed, .env.example, README.md) registered as uv workspace member"
  - "Typed exception hierarchy: MarketDataError / MarketDataAPIError / MarketDataAuthError / MarketDataRateLimitError (status_code, message)"
  - "Per-instance _ClientState dataclass with Auth0 client-credentials fields + token cache fields + lazy locks"
  - "RetryTransport + AsyncRetryTransport (full-jitter backoff, mutation gate, Retry-After cap) with _LOGGER_NAME=market_data_client"
  - "TTL constants _TOKEN_TTL_BUFFER_SECONDS=60, _TOKEN_TTL_FALLBACK_SECONDS=3600; DEFAULT_BASE_URL=https://market-data-develop.bbsa.com.ar/api"
affects: [20-02 (_core/_logging), 20-03 (client/aio), 20-04 (__init__/tests), Phase 24 PUB-MD-01 (lockfile + ci.yml matrix)]

# Tech tracking
tech-stack:
  added: [tenacity>=9.1.0<10 (market-data-client runtime dep), httpx, python-dotenv]
  patterns:
    - "iol-client private-module mirroring (exceptions/_state/_transport/_atransport verbatim with package rename)"
    - "Auth0 client_credentials state shape (no username/password/refresh_token/disk-cache — machine-to-machine re-auth)"
    - "intra-package _atransport → _transport import of shared retry constants"

key-files:
  created:
    - packages/market-data-client/pyproject.toml
    - packages/market-data-client/src/market_data_client/py.typed
    - packages/market-data-client/.env.example
    - packages/market-data-client/README.md
    - packages/market-data-client/src/market_data_client/exceptions.py
    - packages/market-data-client/src/market_data_client/_state.py
    - packages/market-data-client/src/market_data_client/_transport.py
    - packages/market-data-client/src/market_data_client/_atransport.py
    - packages/market-data-client/src/market_data_client/__init__.py
  modified:
    - pyproject.toml (root — added market-data-client to [tool.uv.sources])

key-decisions:
  - "Pulled a minimal __init__.py forward from Wave 4 (Rule 3 blocking fix) so mypy strict + the pre-commit mypy hook can anchor the package base; Wave 4 overwrites it with full re-exports"
  - "uv.lock left modified but uncommitted per plan (lockfile finalization deferred to Phase 24 / PUB-MD-01)"
  - "platformdirs deliberately omitted from dependencies (D-02 — disk token cache deferred to v1.5+)"

patterns-established:
  - "Auth0 client-credentials _ClientState: client_id/client_secret/audience/auth0_token_url via env default factories + token/token_expires_at + http_client + lazy token_lock/client_lock"
  - "MARKET_DATA_* env var namespace (CLIENT_ID/CLIENT_SECRET/AUDIENCE/AUTH0_TOKEN_URL/BASE_URL)"

requirements-completed: [AUTH-MD-01, CORE-MD-01]

# Metrics
duration: ~35min
completed: 2026-07-29
status: complete
---

# Phase 20 Plan 01: Package Scaffold + Dependency-Free Foundations Summary

**Stood up the `market-data-client` package skeleton mirroring `iol-client` — hatchling/uv workspace metadata, the 4-class typed exception hierarchy, an Auth0-client-credentials `_ClientState`, and the sync/async retry transport pair — all passing ruff + mypy strict.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-07-29T17:01:18Z
- **Tasks:** 3
- **Files created:** 9 (package) + 1 root pyproject modified

## Accomplishments
- New `market-data-client` package registered as a uv workspace member (`[tool.uv.sources]`), importable as `market_data_client` after `uv sync`; editable `.pth` path hook installed
- Typed exception hierarchy `MarketDataError` → `MarketDataAPIError(status_code, message)` → `MarketDataAuthError`/`MarketDataRateLimitError`
- `_ClientState` (slots dataclass) holding Auth0 credentials, cached token + expiry, http client, and lazy asyncio locks — with iol's `username`/`password`/`refresh_token`/`token_cache_path` removed
- `RetryTransport` + `AsyncRetryTransport` copied verbatim from iol with only `_LOGGER_NAME="market_data_client"` and the intra-package import path changed; full-jitter backoff, mutation gate, Retry-After 60s cap preserved
- Foundation deps: httpx, python-dotenv, tenacity — **no** `platformdirs` (D-02)

## Task Commits

Each task was committed atomically:

1. **Task 1: Package scaffold + workspace registration** - `0319bd2` (feat)
2. **Task 2: exceptions.py + _state.py** - `2c65533` (feat)
3. **Task 3: _transport.py + _atransport.py + minimal __init__** - `e913c30` (feat)

_Note: STATE.md / ROADMAP.md updates and the docs metadata commit are owned by the execute-phase orchestrator after the wave merges (worktree mode)._

## Files Created/Modified
- `packages/market-data-client/pyproject.toml` - Package metadata, hatchling build, deps (httpx/python-dotenv/tenacity), test extras
- `packages/market-data-client/src/market_data_client/py.typed` - PEP 561 typed marker (empty)
- `packages/market-data-client/.env.example` - 5 `MARKET_DATA_*` placeholder vars (no real secrets)
- `packages/market-data-client/README.md` - Sync/async usage + Auth0 client-credentials + env vars
- `packages/market-data-client/src/market_data_client/exceptions.py` - 4-class exception hierarchy
- `packages/market-data-client/src/market_data_client/_state.py` - `_ClientState` + TTL constants + env factories
- `packages/market-data-client/src/market_data_client/_transport.py` - `RetryTransport` (sync)
- `packages/market-data-client/src/market_data_client/_atransport.py` - `AsyncRetryTransport` (async mirror)
- `packages/market-data-client/src/market_data_client/__init__.py` - Minimal package marker (deviation — see below)
- `pyproject.toml` (root) - Added `market-data-client = { workspace = true }`

## Decisions Made
- **Minimal `__init__.py` pulled forward from Wave 4** to unblock the mypy gate (see Deviations).
- **`uv.lock` intentionally uncommitted** — the plan assigns lockfile finalization to Phase 24. The venv is synced locally so all `uv run` verification passed; the root `pyproject.toml` now references the workspace source, so a `--frozen` sync on `main` will require the Phase 24 lock update. This is per plan scope and flagged for Phase 24 / PUB-MD-01.
- **No `platformdirs`** — disk token cache (`_token_cache.py`) is out of scope (D-02, deferred to v1.5+).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Minimal `__init__.py` pulled forward from Wave 4**
- **Found during:** Task 3 (_transport.py + _atransport.py)
- **Issue:** With no `__init__.py` in `src/market_data_client/`, mypy strict cannot anchor the package base. `_atransport.py` imports `market_data_client._transport` while mypy also names the file directly `_transport`, yielding `error: Source file found twice under different module names`. This fails both the plan's own `uv run mypy packages/market-data-client/src` verification AND the pre-commit `mypy` hook (`files: ^packages/.*/src/`, which passes changed files directly) — and `--no-verify` hook bypass was not authorized by the orchestrator.
- **Fix:** Added a minimal `__init__.py` (docstring + `__version__ = "0.1.0"`). Every existing package resolves this the same way (mypy walks up to the package with `__init__.py`). Wave sequencing means the Wave 4 worktree branches after Wave 1 merges, so it sees and overwrites this file with the full re-export version — no add/add merge conflict.
- **Files modified:** packages/market-data-client/src/market_data_client/__init__.py
- **Verification:** `uv run mypy packages/market-data-client/src` → "Success: no issues found in 5 source files"; pre-commit hooks passed on the Task 3 commit.
- **Committed in:** e913c30 (Task 3 commit)

**2. [Rule 3 - Blocking] Re-synced editable install to register the `.pth` path hook**
- **Found during:** Task 2 (exceptions.py + _state.py import verification)
- **Issue:** The Task-1 `uv sync` ran when the package dir held only `py.typed` (no importable module), so uv/hatchling installed a dist-info but did NOT create the editable `_editable_impl_market_data_client.pth` path hook. `import market_data_client` then failed with `ModuleNotFoundError`.
- **Fix:** Ran `uv sync --all-packages --all-extras --dev --reinstall-package market-data-client` after the first real modules existed; this created `_editable_impl_market_data_client.pth`.
- **Files modified:** none (venv-only; no tracked-file change)
- **Verification:** `import market_data_client._state, ...exceptions` succeeds; all namespace imports pass.
- **Committed in:** n/a (environment-only fix; no source change)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking)
**Impact on plan:** Both fixes were necessary to satisfy the plan's stated verification gates (mypy strict + namespace import) and to allow committing with hooks enabled. The `__init__.py` is the only new tracked file beyond the 8 planned; it is a placeholder that Wave 4 owns and overwrites. No scope creep.

## Issues Encountered
- `.env.example` and the iol `.env.example` are read-blocked by the environment's permission settings; the plan specified the exact 5 `MARKET_DATA_*` vars, so the template was authored directly from the plan spec without needing to read the iol analog.

## Threat Flags
None — T-20-01 (`.env.example` placeholders only), T-20-SC (deps pinned/approved), and T-20-03 (`token_expires_at` + 60s buffer field present) mitigations are all implemented as planned. No new trust boundaries introduced.

## Known Stubs
- `__init__.py` is an intentional minimal placeholder (no public re-exports yet) — Wave 4 (20-04) wires the full public surface once `client.py`/`aio.py` exist. Documented above as a deviation, not a defect.

## Next Phase Readiness
- Wave 2 (`_core.py`, `_logging.py`) can now import `market_data_client.exceptions`, `market_data_client._state`, and `market_data_client._transport`/`_atransport`.
- **Flag for Phase 24 / PUB-MD-01:** commit the finalized `uv.lock` (workspace now references `market-data-client`) and add the `ci.yml` test-matrix entry. Until then, `uv sync --frozen` at workspace scope on `main` will need the lock update.

## Self-Check: PASSED

All 9 package files + SUMMARY.md verified present on disk; all 4 commit hashes (`0319bd2`, `2c65533`, `e913c30`, `2df9d8b`) verified in git log.

---
*Phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte*
*Completed: 2026-07-29*
