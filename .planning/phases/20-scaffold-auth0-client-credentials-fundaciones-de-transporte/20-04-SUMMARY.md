---
phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
plan: 04
subsystem: api
tags: [httpx, auth0, client-credentials, oauth2, sync-client, market-data-client]

# Dependency graph
requires:
  - phase: 20-01
    provides: _state (_ClientState, _REQUEST_TIMEOUT, auth0_token_url) + _transport (RetryTransport)
  - phase: 20-02
    provides: _core pure builders/parsers (build_token_request, parse_token_response, build_health_request/feed, parse_health_response, token_is_fresh, raise_for_response, RequestSpec.authenticated)
provides:
  - "Sync Client shell (client.py) for market-data-client"
  - "Auth0 client_credentials token lifecycle: _authenticate() + _ensure_token() (single-grant, no rotation token)"
  - "_send_auth_request dispatching the grant to the ABSOLUTE auth0_token_url (Pitfall 1)"
  - "_request with authenticated/anonymous branching + exactly-once 401 re-auth"
  - "configure() controlled-mutation entry with token reset on credential rotation"
  - "get_health()/get_health_feed() anonymous health getters (instance + module-level)"
affects: [20-05, 20-06, market-data-client, aio-mirror, live-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "B8 identity alias: _raise_for_response = _core.raise_for_response (shared object, no re-implemented mapping)"
    - "Collapsed auth pair _authenticate()/_ensure_token() (re-running the grant IS the refresh; D-05)"
    - "Absolute-token-URL dispatch: grant POSTs to state.auth0_token_url, endpoints reach base_url+path"
    - "spec.authenticated gates BOTH Bearer injection AND the 401 re-auth carve-out (Pitfall 4)"

key-files:
  created:
    - packages/market-data-client/src/market_data_client/client.py
  modified: []

key-decisions:
  - "No max_attempts request extension in this shell — per-call retry override deferred to Phase 21"
  - "configure() treats any credential/URL change as rotation → token=None + token_expires_at=0.0 unless token/token_expires_at explicitly seeded"
  - "uv.lock market-data-client member registration kept OUT of scope (logged to deferred-items.md)"

patterns-established:
  - "Anonymous-vs-authenticated request branching in a single _request() shell via RequestSpec.authenticated"
  - "Health 401 raises immediately (real error); authenticated 401 triggers exactly-one re-auth then re-raise"

requirements-completed: [AUTH-MD-01, CORE-MD-01]

# Metrics
duration: 6min
completed: 2026-07-29
status: complete
---

# Phase 20 Plan 04: Sync Client Shell Summary

**Sync `market-data-client` Client with Auth0 client_credentials single-grant token lifecycle, absolute-token-URL auth dispatch, anonymous-vs-authenticated `_request` branching with exactly-once 401 re-auth, `configure()`, and health getters — ruff + mypy strict clean, public sync surface imports.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-29T17:11:30Z
- **Completed:** 2026-07-29T17:17:45Z
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- `Client` class (371 LOC `client.py`) mirroring iol's shell, reduced to the market-data surface: `__init__` (client_credentials inputs only) + context-manager/`close()`, lazy `_ensure_http_client` wrapping `RetryTransport`.
- Auth0 `client_credentials` lifecycle collapsed into `_authenticate()` + `_ensure_token()` — no rotation token, no `_token_cache` (D-05); `_send_auth_request` dispatches the grant to the ABSOLUTE `state.auth0_token_url` (Pitfall 1 / T-20-02).
- `_request` net-new `authenticated` branch: Bearer injection + exactly-once 401 re-auth for authenticated specs; anonymous specs (health) raise a 401 immediately with no re-auth carve-out (Pitfall 4). Body-consume-then-raise preserved.
- `configure()` sole controlled-mutation entry, resetting the cached token on credential rotation; `_get_default()` lazy singleton + module-level `get_health()`/`get_health_feed()` shims; `get_health()`/`get_health_feed()` reach `{base_url}/health[/feed]` anonymously via the retry transport.
- `_raise_for_response = _core.raise_for_response` module-level alias (B8 identity).

## Task Commits

Each task was committed atomically:

1. **Task 1: Client class + auth dispatch (absolute token URL) + collapsed token lifecycle** - `9d39b13` (feat)
2. **Task 2: _request authenticated branch + configure() + health getters** - `a39b98d` (feat)

_TDD note: both tasks carry `tdd="true"`, but the plan's own `<verify>` blocks and objective define verification as ruff + mypy strict + namespace-import only — behavioral token-lifecycle / health / 401-re-auth tests are explicitly owned by Plan 06 (once `__init__` + `conftest` wire the full package). No test files were created here per that plan boundary._

## Files Created/Modified
- `packages/market-data-client/src/market_data_client/client.py` - Sync `Client` shell: class + lifecycle, `_ensure_http_client`, `_send_auth_request` (absolute token URL), `_authenticate`, `_ensure_token`, `_request` (authenticated branch + 401 re-auth-once), `get_health`, `get_health_feed`, `configure`, `_get_default`, module-level `get_health`/`get_health_feed`, `_raise_for_response` alias, `_DEFAULT_MAX_ATTEMPTS`.
- `.planning/phases/20-.../deferred-items.md` - Logged out-of-scope `uv.lock` member registration.

## Decisions Made
- Followed the plan as specified. Two minor wording adjustments in comments/docstrings to keep the file free of the literal tokens `refresh_token`, `with_options`, and `max_retries` (Task-1 verify greps `! grep -q refresh_token`; Task-2 acceptance requires those constructs absent). No behavioral impact.
- `configure()` reset guard: rotation resets token unless `token`/`token_expires_at` are explicitly passed (conftest seeding path) — matches Task 2 behavior spec.

## Deviations from Plan

None - plan executed exactly as written. (No Rule 1-4 deviations. The two comment/docstring rewordings above are cosmetic, made to satisfy the plan's own absence gates, not unplanned functional work.)

## Issues Encountered
- The freshly-created `.venv` lacked workspace dependencies; `uv sync --all-packages --all-extras --dev --frozen` was required before ruff/mypy/import verification could run. Side effect: `uv sync` regenerated `uv.lock` to register the `market-data-client` workspace member (a scaffold-level gap from Plan 01, NOT caused by `client.py`). Kept out of this plan's commits (scope = `client.py` only) and logged to `deferred-items.md` for the release-prep plan (`uv lock`).

## Threat surface
No new trust boundaries beyond the plan's `<threat_model>`. Mitigations implemented as designed:
- **T-20-02** (token to wrong host / anonymous leak): `_send_auth_request` targets absolute `auth0_token_url`; `_request` injects Bearer only when `spec.authenticated` (health passes `False`).
- **T-20-03** (stale token reuse): `_ensure_token` gates on `_core.token_is_fresh`; `configure()` resets `token=None` + `token_expires_at=0.0` on rotation.
- **T-20-08** (401 re-auth loop): exactly-one re-auth then re-raise; anonymous (health) 401 raises before any retry.
- **T-20-06** (Bearer/secret in logs): relies on `_logging.attach()` wired at import in Plan 06 (out of this plan's scope); `__repr__` here redacts secret + token.

## User Setup Required
None - no external service configuration required for this plan. (Live Auth0 credentials become relevant for the Plan 06 wiring / live-verification phase.)

## Next Phase Readiness
- Sync half of AUTH-MD-01 + CORE-MD-01 complete. The async mirror (Plan 05, parallel Wave 3) builds `aio.py` from the same `_core`/`_atransport` primitives.
- Plan 06 wires `__init__` + `conftest` and lands the behavioral token-lifecycle / health / 401-re-auth tests that this plan defers.
- Blocker/concern: `uv.lock` must register `market-data-client` (deferred-items.md) before CI lockfile checks pass — belongs to PUB-MD-01 release prep.

## Self-Check: PASSED

- `packages/market-data-client/src/market_data_client/client.py` — FOUND
- Commit `9d39b13` (Task 1) — FOUND
- Commit `a39b98d` (Task 2) — FOUND

---
*Phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte*
*Completed: 2026-07-29*
