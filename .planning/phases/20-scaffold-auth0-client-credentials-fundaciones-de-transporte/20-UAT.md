---
status: passed
phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
source: [20-VERIFICATION.md]
started: 2026-07-29T17:40:00Z
updated: 2026-07-29T18:05:00Z
---

## Current Test

number: 2
name: Fix-now vs. track-as-debt for WR-02 / WR-03 / WR-05
expected: Resolved — user chose to fix all three now; implemented + tested.
awaiting: none

## Tests

### 1. `configure()` sync/async divergence (WR-01)
expected: A decision on whether `configure(base_url=...)` should invalidate the cached Auth0 token. Sync invalidates; async does not. The project constraint requires sync/async logic to be mirrored.
result: passed — Decision: align async to sync (both invalidate on `base_url` rotation). Implemented in `aio.configure` (commit efd7db8) with mirrored regression tests in `test_client.py` + `test_async_client.py`.

### 2. Fix-now vs. track-as-debt for WR-02 / WR-03 / WR-05
expected: A decision on whether these three REVIEW.md WARNING-severity findings should be fixed before Phase 21 builds on this foundation, or accepted as known, tracked debt.
result: passed — Decision: fix all three now.
  - WR-02 (`parse_token_response` null `expires_in`) + WR-03 (`auth0_token_url` validation) fixed in `_core.py` (commit 43da829) with regression tests.
  - WR-05 (Retry-After double-wait) fixed in `_transport.py`/`_atransport.py` via a shared tenacity wait strategy (commit dab8aea) with unit + integration tests.
  Remaining review items (WR-04, IN-01..04, 401 re-auth test gap) tracked as debt for Phase 21 (commit a1b814d).

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
