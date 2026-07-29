---
phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
plan: 05
subsystem: auth
tags: [auth0, client-credentials, httpx, asyncio, async, market-data-client, token-lifecycle]

# Dependency graph
requires:
  - phase: 20-01
    provides: "AsyncRetryTransport (_atransport.py) — async httpx transport with full-jitter retries + mutation gate"
  - phase: 20-02
    provides: "_core.py pure builders/parsers (build_token_request, parse_token_response, token_is_fresh, raise_for_response, health builders) + _state.py (_ClientState, _REQUEST_TIMEOUT)"
provides:
  - "aio.py — async AsyncClient shell mirroring the sync client.py in async form with independent module-level singleton state"
  - "Lazy per-loop asyncio.Lock lifecycle (_ensure_token_lock/_ensure_client_lock) + double-checked _ensure_http_client/_aensure_token"
  - "Absolute-token-URL grant dispatch (_send_auth_request → state.auth0_token_url) + single client_credentials grant (_authenticate_unlocked)"
  - "async _request with authenticated branch (Bearer injection + exactly-once 401 re-auth) and anonymous health carve-out"
  - "configure() (independent async singleton) + async module getters get_health/get_health_feed/aclose"
affects: [20-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy per-loop asyncio.Lock (created on first async use, never in __init__ — Pitfall 2)"
    - "Double-checked locking for token refresh (D-12 asyncio.Lock, NOT matriz's 3-way concurrency primitive)"
    - "Absolute-URL grant dispatch (auth0_token_url) with authenticated-flag Bearer gating (Pitfall 1 / D-08/D-09)"
    - "B8 identity: module alias _raise_for_response = _core.raise_for_response (same object as sync surface)"

key-files:
  created:
    - packages/market-data-client/src/market_data_client/aio.py
  modified: []

key-decisions:
  - "auth0_token_url rotation via configure() also invalidates the cached token (treated as a credential-class change alongside client_id/client_secret/audience)"
  - "401 re-auth uses the atomic clear-then-authenticate-under-token-lock pattern (iol WR-01 hardening) rather than the plan's clear+_aensure_token sketch — same exactly-once semantics, closes the thundering-herd race per T-20-08"
  - "__init__ accepts base_url/client_id/client_secret/audience/auth0_token_url/token/token_expires_at/http_client overrides mirroring configure()'s surface"

patterns-established:
  - "Async transport shell: no with_options/_is_view, no endpoint methods, no PEP 562 shim — reduced from iol's ~760-line aio.py"
  - "load_dotenv() called at module import in aio.py (no client.py to bootstrap it in this package's async surface)"

requirements-completed: [AUTH-MD-01, CORE-MD-01]

# Metrics
duration: 18min
completed: 2026-07-29
status: complete
---

# Phase 20 Plan 05: Async Client Shell (aio.py) Summary

**Async `AsyncClient` for market-data-client with per-loop double-checked asyncio.Lock token lifecycle, absolute Auth0 client-credentials grant dispatch, authenticated/anonymous `_request` branching, `configure()`, and async health getters — passes ruff + ruff format + mypy strict + namespace import.**

## Performance

- **Duration:** ~18 min
- **Completed:** 2026-07-29
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- `AsyncClient` shell with independent per-instance `_ClientState`, `__slots__`, async context manager, and idempotent `aclose()`.
- Lazy per-loop locks (`_ensure_token_lock`/`_ensure_client_lock`) created only on first async use — never in `__init__` (Pitfall 2, binds to the running loop); double-checked `_ensure_http_client` wrapping `AsyncRetryTransport(max_attempts=_DEFAULT_MAX_ATTEMPTS)`.
- `_send_auth_request` dispatches the grant to the ABSOLUTE `state.auth0_token_url` (Pitfall 1 / T-20-02); `_authenticate_unlocked` performs a single `client_credentials` grant; `_aensure_token` re-checks `token_is_fresh` inside the token lock before authenticating (double-checked, D-12 / T-20-08).
- async `_request` mirrors the sync authenticated branch: token injection + exactly-once 401 re-auth gated on `spec.authenticated`; anonymous health (`get_health`/`get_health_feed`) reaches base_url health paths without a Bearer and raises immediately on 401 (D-08/D-09, Pitfall 4).
- `configure()` on the independent async singleton rotates Auth0 creds/urls and resets the token on rotation; async module getters `get_health`/`get_health_feed`/`aclose` delegate to `_get_default()`.

## Task Commits

Each task was committed atomically:

1. **Task 1: AsyncClient + lazy per-loop locks + double-checked token lifecycle** - `3fd6a5f` (feat)
2. **Task 2: async _request authenticated branch + configure() + async health getters** - `a52b6a5` (feat)

_Note: this plan is tdd-flagged but its behavioral async lifecycle/health tests land in Plan 06; verification here is via ruff + ruff format --check + mypy strict + namespace import, per the plan's automated verify blocks._

## Files Created/Modified
- `packages/market-data-client/src/market_data_client/aio.py` - Async `AsyncClient` shell: lazy per-loop locks, double-checked token lifecycle, absolute-URL grant dispatch, `_request` authenticated/anonymous branching, `configure()`, async health getters + module singleton.

## Decisions Made
- **auth0_token_url rotation invalidates the cached token** in `configure()` — grouped with `client_id`/`client_secret`/`audience` as a credential-class change (changing the issuer URL would produce a token from a different authority). `base_url` changes do NOT reset the token (base_url is not part of the grant).
- **401 re-auth uses the atomic clear-then-authenticate-under-token-lock pattern** (mirroring iol's WR-01 hardening) instead of the plan action's literal "clear `state.token=None`, `await self._aensure_token()`" sketch. Both yield exactly-once re-auth; the atomic form additionally closes the thundering-herd race that T-20-08 mandates the double-checked lock serialize. Semantics (exactly-one re-auth, second 401 re-raises, no recursion) are identical to what the plan specifies.
- **`__init__` mirrors `configure()`'s override surface** (`base_url`/`client_id`/`client_secret`/`audience`/`auth0_token_url`/`token`/`token_expires_at`/`http_client`); no `max_retries`/user-credential kwargs (single machine-to-machine grant, D-05).

## Deviations from Plan

None - plan executed exactly as written. (The 401 re-auth atomic-lock refinement noted under Decisions is a hardening within the plan's stated behavior/threat-model, not a scope change; no code was added beyond the plan's artifact spec.)

## Issues Encountered
- The Task 1 automated verify includes hard `! grep -q 'refresh_token'` and `! grep -q 'TokenStore'` gates that are content-sensitive across the ENTIRE file, including prose. The initial module docstring mentioned both terms while asserting their absence; reworded the docstring (and, proactively, the `with_options`/`username`/`password`/`max_retries` prose) to keep every deferred/wrong-pattern literal at zero occurrences. Resolved; all absence checks return 0.

## User Setup Required
None - no external service configuration required by this plan. (Live Auth0 credentials for `market-data-develop` are exercised in later verification plans, not here.)

## Next Phase Readiness
- `aio.py` public surface (`AsyncClient`, `configure`, `get_health`, `get_health_feed`, `_get_default`, `aclose`) imports cleanly and type-checks under mypy strict.
- Behavioral async lifecycle/health tests (double-checked lock, absolute-URL dispatch, anonymous health carve-out, exactly-once 401 re-auth) are ready to be authored in Plan 06.
- Wave 4 will wire `aio` into the package `__init__.py` public re-exports alongside `client.py`.

## Self-Check: PASSED

- FOUND: `packages/market-data-client/src/market_data_client/aio.py`
- FOUND commit: `3fd6a5f` (Task 1)
- FOUND commit: `a52b6a5` (Task 2)

---
*Phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte*
*Completed: 2026-07-29*
