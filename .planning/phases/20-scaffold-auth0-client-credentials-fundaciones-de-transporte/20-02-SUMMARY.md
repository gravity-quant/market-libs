---
phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
plan: 02
subsystem: auth
tags: [auth0, client-credentials, httpx, pytest, market-data-client, request-spec]

# Dependency graph
requires:
  - phase: 20-01
    provides: "_state.py (_ClientState, _TOKEN_TTL_BUFFER_SECONDS, _TOKEN_TTL_FALLBACK_SECONDS) + exceptions.py (MarketDataAPIError/AuthError/RateLimitError)"
provides:
  - "_core.py pure Auth0 client_credentials request builder + response parser (2-tuple)"
  - "raise_for_response exception mapping (401/403->Auth, 429->RateLimit, other->APIError)"
  - "token_is_fresh freshness predicate"
  - "RequestSpec dataclass with net-new authenticated:bool=True flag (gates Bearer injection in Wave 3)"
  - "anonymous health builders (/health, /health/feed) + parse_health_response"
affects: [20-04, 20-05, 20-06, "market-data-client client.py/aio.py Wave 3 shells"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure builder/parser core (state in -> RequestSpec; httpx.Response in -> typed result); IO-free, no client/aio imports"
    - "Body-consume-then-raise ordering in parsers (resp.read -> raise_for_response -> resp.json) (D-06)"
    - "authenticated flag on RequestSpec to distinguish anonymous specs (token grant, health) from Bearer-carrying ones (D-09)"

key-files:
  created:
    - packages/market-data-client/src/market_data_client/_core.py
    - packages/market-data-client/tests/test_core.py
  modified: []

key-decisions:
  - "Single client_credentials grant -> parse_token_response returns a 2-tuple (token, expires_at), no refresh slot (D-05)"
  - "expires_at = now + expires_in - 60s buffer; falls back to 3600s only when expires_in absent (D-07)"
  - "build_token_request sets path='' (Wave 3 dispatches to absolute auth0_token_url) and authenticated=False (T-20-02)"
  - "No models.py/types.py this plan; parse_health_response returns plain dict[str, Any] (D-03)"

patterns-established:
  - "Pattern: RequestSpec.authenticated flag defaults True; anonymous specs opt out"
  - "Pattern: Auth0 token builder/parser co-located with raise_for_response in _core.py (D-04), not a separate auth module"

requirements-completed: [AUTH-MD-01, CORE-MD-01]

# Metrics
duration: 6min
completed: 2026-07-29
status: complete
---

# Phase 20 Plan 02: _core.py pure Auth0 builders/parsers Summary

**Pure, IO-free `_core.py` for market-data-client: Auth0 client_credentials request builder + 2-tuple token parser (60s buffer / 3600s fallback), status->exception mapping, `token_is_fresh`, and anonymous `/health` builders — all TDD-driven (RED first, 24 tests GREEN).**

## Performance

- **Duration:** ~6 min
- **Completed:** 2026-07-29
- **Tasks:** 1 feature (TDD: RED + GREEN, no refactor needed)
- **Files modified:** 2 created

## Accomplishments
- `build_token_request` / `parse_token_response`: Auth0 `client_credentials` grant, form-encoded, anonymous (`authenticated=False`, `path=""`), 2-tuple `(token, expires_at)` with conservative 60s buffer and 3600s fallback when `expires_in` absent.
- `raise_for_response`: 401/403 -> `MarketDataAuthError`, 429 -> `MarketDataRateLimitError`, other error -> `MarketDataAPIError` (D-14).
- `token_is_fresh`: `bool(state.token and time.time() < state.token_expires_at)` (bakes in buffer via parser).
- `RequestSpec` extended with net-new `authenticated: bool = True` last field (D-09), plus anonymous health builders (`/health`, `/health/feed`) and `parse_health_response` -> `dict[str, Any]`.
- Threat register mitigations landed: T-20-02 (grant carries no stale Bearer, absolute URL), T-20-03 (conservative expiry via buffer), T-20-05 (non-str/empty access_token raises rather than caching a bogus token).

## Task Commits

TDD feature — RED then GREEN:

1. **RED: failing test_core.py** - `1c4949e` (test)
2. **GREEN: implement _core.py** - `569bd85` (feat)

_No REFACTOR commit — implementation was clean on first GREEN (ruff + mypy strict pass)._

## Files Created/Modified
- `packages/market-data-client/src/market_data_client/_core.py` - Pure Auth0 builders/parsers, exception mapping, `token_is_fresh`, `RequestSpec` (with `authenticated` flag), health builders.
- `packages/market-data-client/tests/test_core.py` - 24 unit tests covering RequestSpec shape/frozen, token build/parse (expiry derivation, fallback, missing/non-str/empty access_token), raise_for_response mapping (401/403/429/500/200), token_is_fresh, anonymous health builders + parser.

## Decisions Made
- Followed plan as specified. Grant is a single `client_credentials` post; parser is a 2-tuple (no refresh rotation, unlike iol's 3-tuple). Fallback TTL only applies when `expires_in` is absent; a present `expires_in` (even small, e.g. 120s) is honored verbatim (explicit test asserts this).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `pytest` was not yet installed in the fresh worktree `.venv`; resolved by running the documented workspace sync (`uv sync --all-packages --all-extras --dev --frozen`) before the RED run. No source impact.

## TDD Gate Compliance
- RED gate: `test(20-02)` commit `1c4949e` present; suite failed on import of missing `market_data_client._core` before implementation.
- GREEN gate: `feat(20-02)` commit `569bd85` present; 24/24 tests pass.

## Verification
- `uv run --package market-data-client pytest packages/market-data-client/tests/test_core.py -q` -> 24 passed.
- `uv run ruff check .../_core.py .../test_core.py` -> All checks passed.
- `uv run mypy .../_core.py` -> Success (strict).

## Known Stubs
None — all functions are fully wired and tested. `parse_health_response` intentionally returns a plain `dict[str, Any]` (SafeModel is Phases 21/22 scope per D-03), not a stub.

## Next Phase Readiness
- Wave 3 shells (`client.py` / `aio.py`) can now dispatch these pure specs: token grant to the absolute `auth0_token_url`, endpoint/health requests to `base_url`, gating the `Authorization: Bearer` header on `RequestSpec.authenticated`.
- No blockers.

## Self-Check: PASSED
- FOUND: packages/market-data-client/src/market_data_client/_core.py
- FOUND: packages/market-data-client/tests/test_core.py
- FOUND: commit 1c4949e (RED test)
- FOUND: commit 569bd85 (GREEN feat)

---
*Phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte*
*Completed: 2026-07-29*
