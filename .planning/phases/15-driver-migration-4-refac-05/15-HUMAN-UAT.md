---
status: partial
phase: 15-driver-migration-4-refac-05
source: [15-VERIFICATION.md]
started: 2026-06-24T00:00:00Z
updated: 2026-06-24T00:00:00Z
---

## Current Test

[awaiting human testing — operator runs per-package LIVE smokes with credentials]

## Tests

### 1. Per-package LIVE smoke — ámbito (no auth required)
expected: `uv run --package ambito-financiero-client python main_ambito_financiero.py` exits 0 with findings written; one `Client()` per run.
result: [pending]

### 2. Per-package LIVE smoke — iol (needs IOL_USERNAME/IOL_PASSWORD in packages/iol-client/.env)
expected: `main_iol.py` exits 0; the forced-refresh probe (`probe_refresh_token`) shows a REAL token refresh on the threaded client (not a silenced no-op); one `Client()`/`AsyncClient()` per run.
result: [pending]

### 3. Per-package LIVE smoke — higyrus (needs credentials in packages/higyrus-client/.env)
expected: `main_higyrus.py` exits 0 with findings written; one `Client()`/`AsyncClient()` per run.
result: [pending]

### 4. Per-package LIVE smoke — matriz (needs credentials in packages/matriz-client/.env)
expected: `main_matriz.py` exits 0; TokenStore not corrupted; exactly ONE remarkets login per run (verifies the 15-05 sweep-probe fix — no second login from a singleton path).
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

None recorded — all items are deferred-by-design (locked decision D-11; milestone-final live re-verification is Phase 17 / LIVE-03). Credentials are not present in this environment.
