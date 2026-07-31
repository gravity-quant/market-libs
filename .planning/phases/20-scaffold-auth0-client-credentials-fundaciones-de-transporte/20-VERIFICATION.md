---
phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
verified: 2026-07-29T18:20:00Z
status: passed
score: 9/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 9/9
  gaps_closed:
    - "WR-01: sync/async configure() base_url token-invalidation divergence — resolved by human decision (align async to sync); implemented + tested."
    - "WR-02: parse_token_response TypeError on null/non-numeric expires_in — fixed with fallback-TTL coercion; regression tests added."
    - "WR-03: build_token_request missing auth0_token_url validation — fixed, now validated alongside the other 3 credentials; regression test added."
    - "WR-05: Retry-After double-wait with tenacity backoff — fixed via shared _retry_after_or_jitter_wait strategy (sync + async); unit + integration tests added."
  gaps_remaining: []
  regressions: []
---

# Phase 20: Scaffold + Auth0 client-credentials + fundaciones de transporte Verification Report (Re-Verification)

**Phase Goal:** Levantar el paquete `market-data-client` espejando la estructura de `iol-client`, con autenticación Auth0 client-credentials (token cache TTL + refresh, dual sync/async) y las fundaciones de transporte (retries, logging redactado, exceptions, `configure()`, health).
**Verified:** 2026-07-29T18:20:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (human_needed gate resolved)

## Context

The initial verification (2026-07-29T15:10:00Z) scored **9/9 must-haves verified** with **zero BLOCKER-level gaps**. The only reason the phase was not `passed` was two human-decision items gating on judgment calls, not code correctness:

1. WR-01 — sync/async `configure()` divergence on `base_url` token invalidation (a real hand-mirroring bug requiring a design decision on which behavior is authoritative).
2. Whether WR-02/WR-03/WR-05 (REVIEW.md WARNING-severity findings) should be fixed now or tracked as debt.

Both decisions were made by the user (recorded in `20-UAT.md`, both items `passed`) and implemented across 3 commits (`efd7db8`, `43da829`, `dab8aea`), with the remaining lower-priority review items (WR-04, IN-01..04, the 401 re-auth test-coverage gap) explicitly tracked as debt in `.planning/todos/pending/market-data-client-review-debt.md` (commit `a1b814d`, scoped to `resolves_phase: 21`).

This re-verification independently re-confirms: (a) each of the four fixes is actually present and correct in the codebase — not just claimed in commit messages, (b) the package's 4 CI gates still pass with the expanded test count, and (c) no regression was introduced in any of the original 9 must-haves.

## Goal Achievement

### Fix Verification (the 4 items closed this cycle)

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | WR-01: `aio.configure(base_url=...)` now invalidates the cached token, mirroring `client.configure()` | ✓ VERIFIED | Read `aio.py:352-354` — `base_url is not None` branch now sets `rotated = True` (previously it did not), and the docstring (`aio.py:333-335`) explicitly states this now "ESPEJA exactamente la superficie sync." Read `client.py:333-335` — unchanged, still rotates on `base_url`. Both surfaces now agree. Confirmed via commit `efd7db8` diff (aio.py: 31 lines changed) and by direct file read post-merge. |
| 2 | WR-01 regression tests | ✓ VERIFIED | `test_client.py::test_configure_base_url_invalidates_cached_token` + `test_configure_base_url_keeps_token_when_seeded` (sync); `test_async_client.py::test_async_configure_base_url_invalidates_cached_token` + `test_async_configure_base_url_keeps_token_when_seeded` (async) — all 4 read directly; each asserts `client._state.token is None` after a bare `base_url` rotation and `token == "seeded"` when explicitly overridden. Substantive, not smoke-only. |
| 3 | WR-02: `parse_token_response` no longer raises `TypeError`/`ValueError` on `{"expires_in": null}` or a non-numeric value | ✓ VERIFIED | Read `_core.py:205-211` — `expires_in_raw = data.get("expires_in")` followed by a `try/except (TypeError, ValueError)` around `float(...)` that falls back to `_TOKEN_TTL_FALLBACK_SECONDS` on any coercion failure (covers both the `None` and non-numeric-string cases the review flagged). |
| 4 | WR-02 regression tests | ✓ VERIFIED | `test_core.py::test_parse_token_response_null_expires_in_uses_fallback` and `test_parse_token_response_non_numeric_expires_in_uses_fallback` — both read directly, assert the fallback TTL is applied instead of crashing. |
| 5 | WR-03: `build_token_request` validates `auth0_token_url` alongside the other 3 credentials | ✓ VERIFIED | Read `_core.py:152-162` — the guard now checks `not state.client_id or not state.client_secret or not state.audience or not state.auth0_token_url`, raising `MarketDataAuthError` before any HTTP dispatch. |
| 6 | WR-03 regression test | ✓ VERIFIED | `test_core.py::test_build_token_request_missing_auth0_token_url_raises` — read directly, asserts `MarketDataAuthError` is raised when only `auth0_token_url` is missing. |
| 7 | WR-05: Retry-After no longer stacks with tenacity's exponential-jitter backoff | ✓ VERIFIED | Read `_transport.py::_retry_after_or_jitter_wait` (new shared wait-strategy factory) — the manual in-attempt `time.sleep`/inline wait was removed; `Retry-After` is now carried on the `_RetryableStatus` sentinel (`retry_after` attr) and consumed by the tenacity `wait=` callable, which returns `min(exc.retry_after, cap)` when present, else the jitter backoff — the two paths are now mutually exclusive, never additive. `_atransport.py` imports and reuses the *same* `_retry_after_or_jitter_wait` function (intra-package import, not a re-implementation) — sync and async are provably mirrored (identical function object). |
| 8 | WR-05 regression tests | ✓ VERIFIED | `test_transport.py` (new file, 106 lines) — unit tests on `_retry_after_or_jitter_wait` directly (`test_wait_returns_retry_after_when_present`, `test_wait_caps_retry_after`, `test_wait_falls_back_to_jitter_when_no_retry_after`, `test_wait_falls_back_to_jitter_on_non_status_exception`) plus an integration test (`test_retry_after_honored_once_not_stacked_sync`) exercising the full transport with a mocked 503+Retry-After response, confirming exactly one honored delay. |

**All 4 fixes are present, correct, and independently regression-tested — not merely claimed in commit messages.**

### Original 9 Observable Truths — Regression Check

All 9 truths from the initial verification were re-checked for regression (not re-derived from scratch, since the initial verification's evidence and reasoning were independently confirmed as sound on first pass):

| # | Truth | Status | Regression Check |
|---|-------|--------|-------------------|
| 1 | SC1: package scaffold (imports, version, pyproject, py.typed) | ✓ VERIFIED (no change) | Not touched by any of the 4 fix commits — confirmed via `git show --stat` on all 4 commits (only `aio.py`, `_core.py`, `_transport.py`, `_atransport.py`, and test files touched). |
| 2 | SC2: token cache TTL + refresh, sync+async double-checked locking | ✓ VERIFIED (no regression) | `_ensure_token`/`_aensure_token` and `_authenticate`/`_authenticate_unlocked` unchanged; `test_token_lifecycle.py` + `test_token_lifecycle_async.py` still pass (part of the 56). |
| 3 | SC3: health endpoints via retry transport + exception mapping | ✓ VERIFIED (no regression) | `raise_for_response` unchanged; retry-transport control flow (mutation gate, `_is_retryable_status`, exhaustion handling) unchanged apart from the wait-strategy swap (WR-05) — re-confirmed still returns the last response unmolested on exhaustion (`except _RetryableStatus as exc: return exc.response`). |
| 4 | SC4: zero credential leakage (`RedactingFilter`) | ✓ VERIFIED (no change) | `_logging.py` not touched by any fix commit. |
| 5 | SC5: 4 CI gates green | ✓ VERIFIED (re-run, now 56 tests) | Ran all 4 myself this cycle — see "CI Gates" below. |
| 6 | Auth grant dispatches to absolute `auth0_token_url`, never `base_url + path` | ✓ VERIFIED (no regression) | `_send_auth_request` in both `client.py` and `aio.py` unchanged. |
| 7 | `_request` gates Bearer injection on `spec.authenticated`; anonymous 401 never re-auths | ✓ VERIFIED (no regression) | Both `_request` implementations re-read in full — the `if not spec.authenticated: raise` carve-out is unchanged; only the async header-merge line (`headers = {"Authorization": ..., **(spec.headers or {})}`) is unchanged from before (WR-04 was explicitly NOT fixed this cycle — correctly tracked as debt, not silently dropped). |
| 8 | Authenticated 401 → exactly-once re-auth → retry, persistent-401 re-raises, no recursion | ✓ VERIFIED (no regression) | Both `_request` re-auth carve-outs re-read in full — logic unchanged from the initially-verified version (sync: `client.py:254-271`; async: `aio.py:254-276`). The test-coverage gap noted in the initial verification (this invariant not covered by the phase's own committed suite) remains open and is correctly tracked in `market-data-client-review-debt.md` — not silently dropped, not claimed as fixed. |
| 9 | `configure()` is the sole controlled mutation entry, resets token on credential rotation | ✓ VERIFIED — **divergence closed** | `client_id`/`client_secret`/`audience`/`auth0_token_url` rotation behavior unchanged (still resets both surfaces). The one confirmed asymmetry (`base_url` rotation) is now closed — this is the WR-01 fix already detailed above. |

**Score:** 9/9 truths verified, 0 present-but-behavior-unverified, 0 regressions found.

### CI Gates (re-run independently)

| Gate | Command | Result | Status |
|------|---------|--------|--------|
| ruff check | `uv run ruff check packages/market-data-client` | All checks passed! | ✓ PASS |
| ruff format --check | `uv run ruff format --check packages/market-data-client` | 17 files already formatted | ✓ PASS |
| mypy strict | `uv run mypy packages/market-data-client/src` | Success: no issues in 9 source files | ✓ PASS |
| pytest | `uv run --package market-data-client pytest packages/market-data-client/tests -q` | **56 passed** (up from 44 — 12 new regression tests: 4 WR-01, 3 WR-02/WR-03, 5 WR-05) | ✓ PASS |

All 4 gates green, matching the count claimed in the task brief (56 tests).

### Anti-Pattern / Debt-Marker Scan (re-run on the 4 fix commits' touched files)

```
grep -rn -E "TBD|FIXME|XXX" packages/market-data-client/src/ packages/market-data-client/tests/
```
No matches. No debt markers introduced.

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| AUTH-MD-01 | ✓ SATISFIED | Truths #2, #6, #8, #9 (WR-01 fix). `REQUIREMENTS.md` checkbox remains `- [ ]` — unchanged bookkeeping caveat noted in the initial verification (typically updated at milestone close). |
| CORE-MD-01 | ✓ SATISFIED | Truths #3, #4, #7, #9, plus the WR-05 transport fix (retry foundation correctness). Same bookkeeping caveat. |

### Human Verification Required

**None.** Both items from the initial verification's human-verification gate are now resolved:

1. WR-01 sync/async `configure()` divergence — decision made (align async to sync), implemented, tested. Confirmed above.
2. WR-02/WR-03/WR-05 fix-now-vs-debt decision — decision made (fix all three now), implemented, tested. Confirmed above. Remaining lower-priority items (WR-04, IN-01..04, 401 re-auth test-coverage gap) correctly tracked as debt for Phase 21 rather than silently dropped.

### Gaps Summary

No gaps. No regressions. Phase goal fully achieved:

- Package scaffold mirrors `iol-client` structure (SC1).
- Auth0 `client_credentials` grant with TTL cache/refresh, sync AND async, double-checked locking (SC2), including the now-mirrored `configure()` invalidation contract (WR-01 closed).
- Retry transport, redacted logging, typed exceptions, `configure()`, health endpoints (SC3-SC5), including the corrected Retry-After honoring (WR-05 closed) and the hardened Auth0 grant builder/parser (WR-02, WR-03 closed).
- All 4 CI gates green with 56 passing tests (12 new regression tests directly covering the 4 fixes).
- The two remaining lower-severity review items (WR-04 latent header-precedence divergence, and the 401 re-auth test-coverage gap) are explicitly and traceably deferred to Phase 21 via `.planning/todos/pending/market-data-client-review-debt.md` — not silently abandoned.

Phase 20 is **passed**. Ready to proceed to Phase 21.

---

_Verified: 2026-07-29T18:20:00Z_
_Verifier: Claude (gsd-verifier, re-verification pass)_
