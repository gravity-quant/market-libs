---
status: testing
phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
source: [20-VERIFICATION.md]
started: 2026-07-29T17:40:00Z
updated: 2026-07-29T17:40:00Z
---

## Current Test

number: 1
name: Confirm the sync/async `configure()` semantic divergence on `base_url` rotation (REVIEW.md WR-01) is acceptable, or decide which behavior is authoritative
expected: |
  A human product/engineering decision on whether `configure(base_url=...)` should
  invalidate the cached Auth0 token (sync `client.py` currently does; async `aio.py`
  currently does not). REVIEW.md recommends the async behavior (do not invalidate) as
  more correct. This is a judgment call, not a mechanical check.
awaiting: user response

## Tests

### 1. `configure()` sync/async divergence (WR-01)
expected: A decision on whether `configure(base_url=...)` should invalidate the cached Auth0 token. Sync invalidates; async does not. The project constraint requires sync/async logic to be mirrored — so at minimum the two surfaces must be aligned. Decide which behavior is authoritative and file a follow-up to align both, or accept the divergence.
result: [pending]

### 2. Fix-now vs. track-as-debt for WR-02 / WR-03 / WR-05
expected: A decision on whether these three REVIEW.md WARNING-severity findings should be fixed before Phase 21 builds on this foundation, or accepted as known, tracked debt:
  - WR-02: `parse_token_response` raises `TypeError` on `{"expires_in": null}` (present-but-null key; untested).
  - WR-03: `auth0_token_url` documented required but not validated with the other three credentials — yields a deep httpx error instead of a clean `MarketDataAuthError`.
  - WR-05: `Retry-After` is honored in addition to tenacity's backoff (waits stack), both surfaces.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
