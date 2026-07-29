---
phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
plan: 06
subsystem: auth
tags: [auth0, client-credentials, httpx, pytest-httpx, market-data-client, integration, token-lifecycle, logging]

# Dependency graph
requires:
  - phase: 20-03
    provides: "_logging.py — RedactingFilter + attach() (Bearer / client_secret / access_token redaction, LOG-01)"
  - phase: 20-04
    provides: "client.py — sync Client, configure(), get_health/get_health_feed, _get_default, _ensure_token, _request 401 carve-out"
  - phase: 20-05
    provides: "aio.py — async AsyncClient, aio.configure(), _aensure_token (double-checked lock), async _request + health getters"
provides:
  - "__init__.py — attach-first ordering (_logging.attach() before any package import) + public re-exports (Client, AsyncClient, 4 exceptions, configure, get_health, get_health_feed) + __all__ + __version__='0.1.0'"
  - "tests/conftest.py — autouse sync+async configure() fixtures + NEVER_EXPIRES sentinel + teardown close/aclose (Pitfall 6 isolation)"
  - "Behavioral suite: token lifecycle (sync+async), health anonymous + 401 carve-out (sync+async), dispatch exception mapping"
  - "All 4 CI gates green for market-data-client (ruff check, ruff format --check, mypy strict, pytest)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "attach-first package init: _logging.attach() runs before importing client/aio/exceptions so redaction is installed package-wide before any credential could be logged (CORE-MD-01 / T-20-06)"
    - "autouse sync+async configure() fixtures seeding dummy creds + non-expiring token; teardown closes transport so httpx_mock intercepts a fresh transport per test (Pitfall 6)"
    - "count-based token-grant assertion (Pitfall 3): identical grant bodies asserted by POST count, not ordering"
    - "anonymous health dispatch assertion: no Authorization header + zero token-URL requests (Pitfall 4 / T-20-02)"

key-files:
  created:
    - packages/market-data-client/tests/conftest.py
    - packages/market-data-client/tests/test_token_lifecycle.py
    - packages/market-data-client/tests/test_token_lifecycle_async.py
    - packages/market-data-client/tests/test_client.py
    - packages/market-data-client/tests/test_async_client.py
  modified:
    - packages/market-data-client/src/market_data_client/__init__.py

key-decisions:
  - "Dispatch-level 429/500 mapping asserted by constructing an authenticated _core.RequestSpec (idempotent=False) and driving Client._request/AsyncClient._request directly — no public authenticated endpoint exists in this scaffold, so idempotent=False avoids the RetryTransport backoff loop while still exercising the dispatch mapping once (fine mapping already unit-tested in Plan 02)"
  - "conftest teardown resets creds via configure(client_id='', client_secret='', audience='', ...) mirroring iol's pattern; each test also seeds state explicitly so cross-test contamination is doubly guarded"

patterns-established:
  - "Token lifecycle driven via _ensure_token()/_aensure_token() directly (health is anonymous and must not drive the token path — Pitfall 4)"
  - "match_content on the client_credentials form body (grant_type=client_credentials&client_id=cid&client_secret=csec&audience=aud) matches dict-insertion order from _core.build_token_request"

requirements-completed: [AUTH-MD-01, CORE-MD-01]

# Metrics
duration: 15min
completed: 2026-07-29
status: complete
---

# Phase 20 Plan 06: Package Integration + Behavioral Verification Summary

**Wired `market_data_client` together — attach-first `__init__.py` (redaction installed before any package import) with public re-exports and `__version__="0.1.0"`, autouse sync+async isolation fixtures, and the behavioral suite (token lifecycle, anonymous health, 401 carve-out, dispatch mapping) proving SC1/SC2/SC3 with all 4 CI gates green (SC5).**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-07-29
- **Tasks:** 3
- **Files:** 6 (5 created, 1 modified)

## Accomplishments
- `__init__.py`: KEEPS the CRITICAL attach-first ordering verbatim — `from market_data_client import _logging as _logging_attach` → `_logging_attach.attach()` → `del _logging_attach` runs BEFORE the `# noqa: E402` re-exports of `.aio` / `.client` / `.exceptions`, so the `RedactingFilter` is attached before any importable module could emit a credential (CORE-MD-01 / T-20-06). Re-exports `AsyncClient`, `Client`, the 4 exceptions, `configure`, `get_health`, `get_health_feed`; keeps the private `_get_default` re-export (NOT in `__all__`); `__version__="0.1.0"`. Removed iol's `InstrumentType`/`login`/endpoint shims.
- `tests/conftest.py`: `NEVER_EXPIRES = 9_999_999_999.0` sentinel + two autouse fixtures (`_configure_sync`, `_configure_async`) seeding dummy creds (`cid`/`csec`/`aud`, test hosts) + a non-expiring token; teardown closes/acloses the default transport so each test gets a fresh transport `httpx_mock` can intercept (Pitfall 6).
- Token lifecycle (SC2 / AUTH-MD-01): sync `test_token_lifecycle.py` + async `test_token_lifecycle_async.py` prove fetch→cache→TTL-expiry re-fetch, driving `_ensure_token()`/`_aensure_token()` directly, matching the client_credentials grant body via `match_content`, and asserting a SECOND token POST fires after forcing `token_expires_at=0.0` (count-based, Pitfall 3). Includes fresh-token no-op tests.
- Health + dispatch (SC3): sync `test_client.py` + async `test_async_client.py` prove `get_health`/`get_health_feed` are anonymous (no `Authorization` header, zero token-URL requests — Pitfall 4 / T-20-02), a health 401 raises `MarketDataAuthError` with ZERO token POSTs (T-20-08), and authenticated 429/500 dispatch maps to `MarketDataRateLimitError`/`MarketDataAPIError` (D-14).

## Task Commits

Each task was committed atomically:

1. **Task 1: `__init__.py` (attach-first + re-exports) + `conftest.py` fixtures** - `906f5db` (feat)
2. **Task 2: token lifecycle tests (sync + async)** - `b87596b` (test)
3. **Task 3: health + 401 tests (sync + async) + full 4-gate run** - `143ac57` (test)

## Files Created/Modified
- `packages/market-data-client/src/market_data_client/__init__.py` (modified) - Replaced the Wave-1 placeholder with the attach-first init + public re-exports + `__all__` + `__version__="0.1.0"`.
- `packages/market-data-client/tests/conftest.py` (created) - Autouse sync+async `configure()` fixtures + `NEVER_EXPIRES` + teardown close/aclose.
- `packages/market-data-client/tests/test_token_lifecycle.py` (created) - Sync fetch→cache→TTL-refetch + fresh no-op.
- `packages/market-data-client/tests/test_token_lifecycle_async.py` (created) - Async mirror via `_aensure_token()`.
- `packages/market-data-client/tests/test_client.py` (created) - Sync health anonymous + 401 carve-out + 429/500 dispatch mapping.
- `packages/market-data-client/tests/test_async_client.py` (created) - Async mirror.

## Verification Evidence
- **SC1:** `import market_data_client; from market_data_client import aio; assert __version__=='0.1.0'` → OK.
- **SC2:** `pytest -k token` → 18 passed (lifecycle + core token unit tests).
- **SC3:** `pytest -k "health or client"` → 44 passed.
- **SC4:** `pytest -k "redact or logging"` → 6 passed (Plan 03 redaction re-run in-suite).
- **SC5:** `ruff check` + `ruff format --check` + `mypy --strict src` + `pytest tests` all exit 0; full suite **44 passed**. LOG-01 grep gate clean over package src.

## Decisions Made
- **Dispatch 429/500 asserted via a synthetic authenticated `_core.RequestSpec` driven through `_request`** — this scaffold exposes only anonymous health endpoints, so there is no public authenticated call to hang the mapping test on. Using `idempotent=False` on the spec bypasses the `RetryTransport` backoff loop (a 429 on an idempotent request would otherwise trigger real jittered sleeps), keeping the test fast while still exercising the dispatch mapping once at the shell level. The fine-grained status→exception mapping is already locked in Plan 02's `test_core.py`.
- **conftest teardown mirrors iol's reset-via-configure pattern** with empty credential strings; combined with each test seeding `state.token`/`token_expires_at` explicitly at the top, cross-test singleton contamination (Pitfall 6) is doubly guarded.

## Deviations from Plan
None - plan executed exactly as written. Ruff's isort/formatter auto-normalized the two new test modules' import blocks and collapsed multi-line `add_response(...)` calls on first `ruff check --fix`/`ruff format`; this is formatting only, no behavior change, and the committed files are gate-clean.

## Threat Surface
No new security-relevant surface beyond the plan's `<threat_model>`. The behavioral tests actively assert the register's mitigations: T-20-06 (attach-first), T-20-02 (anonymous health, no Bearer), T-20-08 (health 401 → zero token POSTs), T-20-01 (dummy creds + test hosts, no `.env` committed).

## Known Stubs
None. No hardcoded empty UI values, placeholders, or unwired data sources — this is a client library with a fully wired public surface.

## Issues Encountered
- First `ruff check` failed on I001 (import block un-sorted) for both new test modules, then `ruff format --check` wanted the multi-line `add_response` calls collapsed. Both resolved via `ruff check --fix` + `ruff format`; final gate run is fully green.
- `uv.lock` went dirty after `uv sync` registered the `market-data-client` workspace member; per plan scope note (lockfile finalization deferred to PUB-MD-01) it was restored via `git checkout -- uv.lock` and NOT committed.

## User Setup Required
None - no external service configuration required by this plan. Live Auth0 credentials for `market-data-develop` are exercised in later live-verification plans, not here.

## Next Phase Readiness
- The package public surface (`import market_data_client` + `from market_data_client import aio`) imports cleanly, type-checks under mypy strict, and is version `0.1.0`.
- SC1/SC2/SC3/SC5 closed; SC4 re-confirmed in-suite. The phase's behavioral contract (token lifecycle sync+async, anonymous health, 401 carve-out, exception mapping, credential redaction) is proven end-to-end.
- Lockfile finalization (`uv.lock` registration of the workspace member) remains deferred to PUB-MD-01 as planned.

## Self-Check: PASSED

- FOUND: `packages/market-data-client/src/market_data_client/__init__.py`
- FOUND: `packages/market-data-client/tests/conftest.py`
- FOUND: `packages/market-data-client/tests/test_token_lifecycle.py`
- FOUND: `packages/market-data-client/tests/test_token_lifecycle_async.py`
- FOUND: `packages/market-data-client/tests/test_client.py`
- FOUND: `packages/market-data-client/tests/test_async_client.py`
- FOUND commit: `906f5db` (Task 1)
- FOUND commit: `b87596b` (Task 2)
- FOUND commit: `143ac57` (Task 3)

---
*Phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte*
*Completed: 2026-07-29*
