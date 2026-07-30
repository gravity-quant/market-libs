---
title: market-data-client — remaining Phase 20 code-review debt (WR-04 + IN-01..04 + 401 re-auth test gap)
created: 2026-07-29
source: Phase 20 code review (20-REVIEW.md) + verification (20-VERIFICATION.md)
priority: low
scope: packages/market-data-client/
resolves_phase: 21
---

# Deferred Phase 20 review items

Phase 20 fixed the four items the user prioritized (WR-01 sync/async `configure()`
alignment, WR-02 null `expires_in`, WR-03 `auth0_token_url` validation, WR-05
Retry-After double-wait). These remaining items from `20-REVIEW.md` /
`20-VERIFICATION.md` were accepted as tracked debt — none is a BLOCKER and all
security-critical paths (redaction, absolute token URL, independent state +
double-checked locking, anonymous health carve-out) verified clean.

## WR-04 — Authorization-header merge precedence diverges sync vs async (WARNING, latent)

`client._request` sets `headers["Authorization"]` AFTER spreading `spec.headers`
(Authorization wins); `aio._request` builds `{"Authorization": ..., **(spec.headers or {})}`
(spec.headers wins). Harmless today — no `RequestSpec` carries its own
`Authorization` header — but it is a real dual-surface divergence that will bite
if an authenticated spec ever sets one. Align both to the same precedence when
Phase 21 adds authenticated endpoints.

## Test-coverage gap — authenticated 401 → exactly-once re-auth (from 20-VERIFICATION.md)

The committed suite exercises the anonymous-health-401 (no re-auth) path but NOT
the authenticated `401 → clear token → re-auth once → retry → succeed` and
persistent-401 re-raise sequences, for either surface. The verifier confirmed the
code is correct via a throwaway test; add permanent regression coverage
(sync + async) before Phase 21 builds authenticated endpoints on this foundation.

## IN-01..IN-04 (INFO)

- IN-01: `configure(http_client=...)` asymmetry — sync accepts an explicit
  `http_client`; async `configure()` does not expose it.
- IN-02: `RedactingFilter` scope boundary — document/verify which handlers it
  reaches once non-package loggers are involved.
- IN-03: `assert`-based narrowing (`assert token is not None`) is stripped under
  `python -O`; consider explicit guards on the hot auth path.
- IN-04: unguarded `resp.json()` dict assumptions in `parse_health_response` /
  token parse if the server returns a non-object JSON body.
