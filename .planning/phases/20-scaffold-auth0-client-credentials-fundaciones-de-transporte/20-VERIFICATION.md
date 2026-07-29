---
phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
verified: 2026-07-29T15:10:00Z
status: human_needed
score: 9/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
behavior_unverified_items: []
human_verification:
  - test: "Confirm the sync/async `configure()` semantic divergence on `base_url` rotation (REVIEW.md WR-01) is acceptable, or decide which behavior is authoritative and file a follow-up to align both surfaces."
    expected: "A human product/engineering decision on whether `configure(base_url=...)` should invalidate the cached Auth0 token (sync currently does; async currently does not) — this is a judgment call, not a mechanical check."
    why_human: "Both behaviors are internally self-consistent and defensible (REVIEW.md recommends the async behavior as more correct); resolving it requires a design decision, not a grep/test."
  - test: "Confirm whether WR-02 (`parse_token_response` crashes with `TypeError` on `{\"expires_in\": null}`), WR-03 (missing `auth0_token_url` validation), WR-05 (double-wait Retry-After + tenacity backoff) should be fixed now or tracked as follow-up debt before Phase 21 builds on this foundation."
    expected: "A human decision on whether these three REVIEW.md WARNING-severity findings block phase completion or are accepted as known, tracked debt."
    why_human: "All three are narrow edge cases (non-standard Auth0 response, misconfiguration, retry-timing precision) that the code reviewer classified as WARNING not BLOCKER; whether to gate the phase on them is a project-priority judgment call, not a correctness question — the verifier's own behavioral spot-check (below) proves the core AUTH-MD-01/CORE-MD-01 paths work end-to-end."
---

# Phase 20: Scaffold + Auth0 client-credentials + fundaciones de transporte Verification Report

**Phase Goal:** Levantar el paquete `market-data-client` espejando la estructura de `iol-client`, con autenticación Auth0 client-credentials (token cache TTL + refresh, dual sync/async) y las fundaciones de transporte (retries, logging redactado, exceptions, `configure()`, health).
**Verified:** 2026-07-29T15:10:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

All 5 ROADMAP success criteria plus the plan-level must-haves were checked directly against the codebase (not inferred from SUMMARY.md claims). Where a truth asserted a runtime state-transition/retry invariant that the phase's own committed test suite did not exercise, I ran an independent, throwaway behavioral spot-check (via `pytest-httpx`) against the actual code, then deleted it — see "Behavioral Spot-Checks" below.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: `import market_data_client` + `from market_data_client import aio` work; `__version__ == "0.1.0"`; `pyproject.toml` has hatchling + httpx/python-dotenv/tenacity + `py.typed` | ✓ VERIFIED | Ran `uv run python -c "import market_data_client as m; from market_data_client import aio; ..."` directly — `m.__version__ == "0.1.0"`, `Client`/`AsyncClient`/`configure`/`get_health`/`MarketDataAuthError` all present. `pyproject.toml` confirmed (httpx, python-dotenv, tenacity; no platformdirs). `py.typed` exists (0 bytes). |
| 2 | SC2: client_credentials token fetched, cached, refreshed on TTL expiry, sync AND async (`asyncio.Lock` double-checked) | ✓ VERIFIED | Read `client.py::_authenticate/_ensure_token` and `aio.py::_authenticate_unlocked/_aensure_token` (double-checked re-check of `token_is_fresh` inside the lazy per-loop lock, confirmed present, not created in `__init__`). Ran `test_token_lifecycle.py` + `test_token_lifecycle_async.py` directly — both assert fetch→cache (1 POST) then forced-TTL-expiry→refetch (2nd POST), by COUNT not ordering. |
| 3 | SC3: `GET /health` + `GET /health/feed` respond via the retry transport; exception hierarchy maps 401/403→Auth, 429→RateLimit, other→APIError | ✓ VERIFIED | Read `_core.py::raise_for_response` (401/403/429/other branches) and `client.py`/`aio.py::get_health`/`get_health_feed`. Ran `test_client.py` + `test_async_client.py` directly — anonymous dispatch (no `Authorization` header, zero token-URL requests), 429→`MarketDataRateLimitError`, 500→`MarketDataAPIError` all pass. |
| 4 | SC4: zero credential leakage in logs (`RedactingFilter`) | ✓ VERIFIED | Independently ran `RedactingFilter().filter()` outside the test suite against a record embedding `client_secret`, `access_token`, and `Bearer` substrings — all three were scrubbed, confirmed via `assert` (not trusting the test suite alone). |
| 5 | SC5: all 4 CI gates green (ruff check, ruff format --check, mypy strict, pytest) for the package | ✓ VERIFIED | Ran all 4 myself: `ruff check packages/market-data-client` → all checks passed; `ruff format --check` → 16 files already formatted; `mypy packages/market-data-client/src` → no issues in 9 source files; `pytest packages/market-data-client/tests -q` → 44 passed. CI LOG-01 grep gate also re-run: clean. |
| 6 | `_send_auth_request` dispatches to the ABSOLUTE `state.auth0_token_url`, never `base_url + path` (Pitfall 1) — sync AND async | ✓ VERIFIED | Read both `client.py::_send_auth_request` and `aio.py::_send_auth_request` — both build the request against `self._state.auth0_token_url` directly, not `base_url`. `build_token_request` sets `path=""` confirming intent. |
| 7 | `_request` gates Bearer injection on `spec.authenticated`; health (authenticated=False) never fetches a token and a health 401 never triggers re-auth | ✓ VERIFIED | Read both `_request` implementations — `if not spec.authenticated: raise` fires before any re-auth carve-out. `test_health_401_raises_auth_without_reauth` (sync) and `test_async_health_401_raises_auth_without_reauth` (async) both assert `MarketDataAuthError` with zero token POSTs. |
| 8 | `_request` on an AUTHENTICATED endpoint performs exactly-once 401 re-auth then retries, and re-raises on a persistent second 401 (no recursion) — sync AND async | ✓ VERIFIED (via verifier spot-check, not phase's own tests — see note) | **Gap found:** the phase's own committed test suite (`test_client.py`, `test_async_client.py`) never constructs a 401→re-auth→200 sequence, nor a persistent-401 sequence, for an `authenticated=True` spec — only the anonymous-health-401 (no-reauth) path is tested. I wrote a throwaway pytest file exercising both sequences directly against `Client._request`/`AsyncClient._request`, ran it (4/4 passed: exactly-one token POST + successful retry, and exactly-one token POST + persistent-401 re-raise, both surfaces), then deleted it — `git status` confirms no residue. The code is correct; the regression-locking test coverage for it is missing. |
| 9 | `configure()` is the sole controlled mutation entry and resets the cached token on credential rotation | ✓ VERIFIED, with a noted cross-surface divergence | `client_id`/`client_secret`/`audience`/`auth0_token_url` rotation correctly resets the token on BOTH surfaces (confirmed by direct read of both `configure()` implementations). **However**, `base_url`-only rotation resets the token in sync `configure()` but NOT in async `configure()` — a real, confirmed hand-mirroring divergence (REVIEW.md WR-01, independently re-confirmed by reading `client.py:333-335` vs `aio.py:348-349`). This violates the project's explicit "dual sync/async logic must be mirrored" constraint. Routed to human verification below (judgment call on which behavior is correct). |

**Score:** 9/9 truths verified (0 present-but-behaviorally-unverified — truth #8's gap was closed by the verifier's own spot-check, not left open)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/market-data-client/pyproject.toml` | hatchling + httpx/python-dotenv/tenacity deps, no platformdirs | ✓ VERIFIED | Confirmed via direct read; `name = "market-data-client"`, `version = "0.1.0"`. |
| `packages/market-data-client/src/market_data_client/py.typed` | PEP 561 marker | ✓ VERIFIED | Exists, 0 bytes. |
| `packages/market-data-client/.env.example` | 5 `MARKET_DATA_*` vars, placeholders only | ✓ VERIFIED | `git show HEAD:.../.env.example` — all 5 vars present, no real credentials. |
| `packages/market-data-client/README.md` | usage note | ✓ VERIFIED (minor info finding) | Exists. Contains a forward-reference to `get_marketdata()` which does not exist yet (Phase 21 / MD-01 scope) — documentation is aspirational for the full package, not misleading about Phase 20's actual surface. Info-level only. |
| `exceptions.py` | 4-class hierarchy | ✓ VERIFIED | `MarketDataError → MarketDataAPIError → {MarketDataAuthError, MarketDataRateLimitError}`, `(status_code, message)` attrs confirmed by read. |
| `_state.py` | `_ClientState` + TTL constants | ✓ VERIFIED | `_TOKEN_TTL_BUFFER_SECONDS=60`, `_TOKEN_TTL_FALLBACK_SECONDS=3600`, `DEFAULT_BASE_URL` ends in `/api`; no `username`/`password`/`refresh_token`/`token_cache_path`. |
| `_transport.py` / `_atransport.py` | RetryTransport pair, `_LOGGER_NAME="market_data_client"` | ✓ VERIFIED | Confirmed via read + ruff/mypy pass. |
| `_core.py` | pure builders/parsers, `RequestSpec.authenticated` | ✓ VERIFIED | 236 lines, all functions IO-free, no `client`/`aio` imports. |
| `_logging.py` | `RedactingFilter` + `attach()` | ✓ VERIFIED | 101 lines; independently re-ran the redaction logic outside pytest. |
| `client.py` | sync `Client` shell | ✓ VERIFIED | 372 lines; full read confirms absolute-token-URL dispatch, `authenticated` branching, `configure()`. |
| `aio.py` | async `AsyncClient` shell | ✓ VERIFIED | 373 lines; full read confirms lazy per-loop locks, double-checked `_aensure_token`, mirrors sync shell. |
| `__init__.py` | attach-first + re-exports + `__version__` | ✓ VERIFIED | `attach()` called and `del`eted before the `# noqa: E402` imports of `.aio`/`.client`/`.exceptions`. |
| `tests/conftest.py` + 4 test modules | autouse fixtures + behavioral suite | ✓ VERIFIED | 44 tests, all substantive (state-transition and count-based assertions, not smoke-only). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `_atransport.py` | `_transport.py` | intra-package import of retry constants | ✓ WIRED | `from market_data_client._transport import ...` confirmed. |
| `client.py` | `_core.py` | `_raise_for_response = _core.raise_for_response` (B8 identity) | ✓ WIRED | Confirmed same-object alias, both `client.py` and `aio.py` reference `_core.raise_for_response`. |
| `client.py::_send_auth_request` | `state.auth0_token_url` | absolute-URL dispatch | ✓ WIRED | Confirmed (Pitfall 1 correctly implemented). |
| `aio.py::_send_auth_request` | `state.auth0_token_url` | absolute-URL dispatch | ✓ WIRED | Confirmed (mirrors sync). |
| `__init__.py` | `_logging.py` | `attach()` before any other import | ✓ WIRED | Confirmed ordering by direct read. |
| `client.py` / `aio.py` | `_transport.py` / `_atransport.py` | `_ensure_http_client` wraps `RetryTransport`/`AsyncRetryTransport` | ✓ WIRED | Confirmed. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Package imports + version | `uv run python -c "import market_data_client..."` | `version: 0.1.0`, all symbols present | ✓ PASS |
| Redaction (`RedactingFilter`, run outside pytest) | ad hoc `logging.LogRecord` + `.filter()` | `client_secret`/`access_token`/Bearer all scrubbed | ✓ PASS |
| ruff check | `uv run ruff check packages/market-data-client` | All checks passed | ✓ PASS |
| ruff format --check | `uv run ruff format --check packages/market-data-client` | 16 files already formatted | ✓ PASS |
| mypy strict | `uv run mypy packages/market-data-client/src` | Success: no issues in 9 source files | ✓ PASS |
| Package pytest suite | `uv run --package market-data-client pytest packages/market-data-client/tests -q` | 44 passed in 0.06s | ✓ PASS |
| LOG-01 grep gate | `grep -rnE 'logging\.basicConfig\s*\(\|logging\.root\.\w' packages/market-data-client/src/` | no matches (clean) | ✓ PASS |
| **Authenticated 401 → exactly-once re-auth → 200 (sync + async)** — NOT covered by phase's own tests | throwaway pytest file, deleted after run | 200 returned, exactly 1 token POST, both surfaces | ✓ PASS (verifier-authored spot-check) |
| **Authenticated persistent 401 → re-raise after 1 retry, no infinite loop (sync + async)** — NOT covered by phase's own tests | throwaway pytest file, deleted after run | `MarketDataAuthError` raised, exactly 1 token POST (no retry loop), both surfaces | ✓ PASS (verifier-authored spot-check) |
| Full monorepo `uv run pytest -q` (all 6 packages combined in one process) | direct execution | Failures/errors clustered at ~83-95% completion, then process stalls with no active CPU | ⚠️ Investigated — see note below |

**Note on the full-workspace combined pytest run:** Running `uv run pytest -q` from the repo root (all 6 packages in a single pytest session) showed clustered `F`/`E` marks and then stalled. I isolated the cause: **the same failure/stall pattern reproduces when `market-data-client` is excluded entirely** (`--ignore=packages/market-data-client`), and **every package passes cleanly when run individually** (iol-client 137, higyrus-client 160, ambito-financiero-client 131+1 deselected, wallets-client 4, matriz-client 322, market-data-client 44 — sum 798, matching the context notes' "798 tests" figure). This confirms the combined-run issue is a **pre-existing cross-package test-isolation problem, not caused by Phase 20**. It is also consistent with `ci.yml`, which runs `pytest` **per package** in a matrix (never a single combined invocation) — `market-data-client` is correctly NOT yet in that CI matrix (deferred to Phase 24 / PUB-MD-01 per `deferred-items.md` and ROADMAP). Not a Phase 20 gap.

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| AUTH-MD-01 | 20-01, 20-02, 20-04, 20-05, 20-06 | Auth0 `client_credentials` grant, token cache + TTL refresh, sync+async | ✓ SATISFIED | Truths #2, #6, #8 above; `REQUIREMENTS.md` checkbox is unchecked (`- [ ]`) — this is a tracking-doc bookkeeping item, not a code gap; typically updated at milestone close, not phase verification. |
| CORE-MD-01 | 20-01, 20-02, 20-03, 20-04, 20-05, 20-06 | Retry transport, redacted logging, typed exceptions, `configure()`, health endpoints | ✓ SATISFIED | Truths #3, #4, #7, #9 above. Same `REQUIREMENTS.md` checkbox caveat as above. |

No orphaned requirements found — `REQUIREMENTS.md` maps exactly AUTH-MD-01 and CORE-MD-01 to Phase 20, and both are claimed by all 6 plans' `requirements:` frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `client.py` vs `aio.py` | `client.py:333-335` / `aio.py:348-349` | `configure(base_url=...)` invalidates the cached token in sync but not async | ⚠️ Warning | Real hand-mirroring divergence (REVIEW.md WR-01); violates the project's dual-sync/async-mirroring constraint. Human decision requested below. |
| `_core.py` | 196-197 | `parse_token_response` raises unhandled `TypeError`/`ValueError` if Auth0 returns `"expires_in": null` or a non-numeric string (only the *absent*-key case falls back to `_TOKEN_TTL_FALLBACK_SECONDS`) | ⚠️ Warning | Confirmed present by direct read (REVIEW.md WR-02). Edge case, not exercised by the current test suite. |
| `_core.py` | 152-157 | `build_token_request` validates `client_id`/`client_secret`/`audience` but not `auth0_token_url` (defaults to `""`) | ⚠️ Warning | Confirmed present by direct read (REVIEW.md WR-03). A misconfigured deployment gets a confusing httpx error instead of a clean `MarketDataAuthError`. |
| `client.py:234-238` vs `aio.py:236` | — | `Authorization` header precedence differs: sync lets the injected Bearer win over `spec.headers`, async lets `spec.headers` win over the injected Bearer | ℹ️ Info | Confirmed present by direct read (REVIEW.md WR-04). Currently latent — no spec sets its own `Authorization`. |
| `_transport.py` / `_atransport.py` | — | `Retry-After` sleep stacks with tenacity's own exponential backoff (double wait) | ℹ️ Info | Not independently re-verified line-by-line by this verifier (trusting REVIEW.md WR-05 — inherited largely verbatim from `iol-client`'s existing, previously-reviewed transport per D-10). |
| `README.md` | — | References `market_data_client.get_marketdata()` which does not exist yet | ℹ️ Info | Phase 21 (MD-01) scope; forward-looking README, not misleading about what Phase 20 delivers. |

No `TBD`/`FIXME`/`XXX` debt markers found in any Phase-20-modified file. No blocker-level anti-patterns found.

### Human Verification Required

### 1. `configure()` sync/async divergence on `base_url` rotation (REVIEW.md WR-01)

**Test:** Decide whether `configure(base_url=...)` should invalidate the cached Auth0 token. Currently sync does; async does not (both are internally consistent and separately documented in their own docstrings, but they disagree with each other).
**Expected:** A single, mirrored contract on both surfaces, consistent with the project's "dual sync/async logic must be mirrored" constraint (CLAUDE.md).
**Why human:** This is a design/judgment call (is `base_url` a "credential" whose rotation should force re-auth, or an independent API-host setting?), not something a grep or test can resolve on its own — REVIEW.md recommends the async behavior as the more defensible one, but a human owner should confirm and then a follow-up fix should mirror it to the other surface.

### 2. Whether WR-02/WR-03/WR-05 (REVIEW.md warnings) block phase completion or are accepted as tracked debt

**Test:** Review REVIEW.md's WR-02 (`expires_in: null` crash), WR-03 (missing `auth0_token_url` required-field validation), WR-05 (Retry-After double-wait) and decide fix-now vs. track-for-later.
**Expected:** All three are narrow edge cases classified WARNING (not CRITICAL/BLOCKER) by the code reviewer; the verifier's own spot-check independently confirms the core AUTH-MD-01/CORE-MD-01 paths (token fetch/cache/refresh, health anonymous dispatch, exactly-once 401 re-auth, redaction) work correctly end-to-end.
**Why human:** Whether to gate phase completion on non-blocking code-quality warnings is a project-priority decision, not a correctness question this verifier can resolve unilaterally.

### Gaps Summary

No BLOCKER-level gaps found — the phase's core deliverable (package scaffold mirroring `iol-client`, Auth0 `client_credentials` auth with TTL cache/refresh in both sync and async, retry transport, redacted logging, typed exceptions, `configure()`, health endpoints) is present, correctly wired, and behaviorally proven, including the one invariant (exactly-once 401 re-auth then re-raise) whose regression-test coverage was missing from the phase's own test suite — I independently proved it correct via a throwaway spot-check and then removed the spot-check file, leaving the git tree unchanged.

Two items are routed to human verification (not phase-blocking, but requiring a project-owner decision before Phase 21 builds further on this foundation):
1. The sync/async `configure()` divergence on `base_url` token invalidation (a real, confirmed mirroring bug — REVIEW.md WR-01).
2. Whether the three REVIEW.md WARNING-severity findings (WR-02/WR-03/WR-05) should be fixed now or tracked as deferred debt.

Recommendation: given these are pre-existing, already-documented findings in `20-REVIEW.md` (0 critical / 5 warning / 4 info) that a human has not yet acted on, and Phase 21 depends on this package, it would be prudent to resolve at least WR-01 (the mirroring-constraint violation) before or during Phase 21's kickoff — but this does not block the Phase 20 gate itself, since Phase 20's explicit success criteria (SC1-SC5) are all met and independently re-verified.

---

_Verified: 2026-07-29T15:10:00Z_
_Verifier: Claude (gsd-verifier)_
