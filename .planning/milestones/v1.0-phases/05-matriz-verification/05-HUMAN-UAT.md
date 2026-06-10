---
status: partial
phase: 05-matriz-verification
source: [05-VERIFICATION.md]
started: 2026-06-10T01:30:00Z
updated: 2026-06-10T01:30:00Z
---

## Current Test

[awaiting human testing — ambos ítems probablemente ya satisfechos por el live run de Task 3.3 y el operator decision A en Task 4.4]

## Tests

### 1. Live run reproducibility against remarkets sandbox
expected: `uv run --package matriz-client python main_matriz.py` produces `SUMMARY: PASS=17 FAIL=0 SKIPPED=9 FINDING=2` (or equivalent counts) against `https://api.remarkets.primary.com.ar` with valid `PRIMARY_USER` + `PRIMARY_PASSWORD` in `packages/matriz-client/.env`.
result: pending — operator ran this during Task 3.3 checkpoint on 2026-06-09T22:01Z with SUMMARY exactly matching expected counts; reproducibility is a soft check (market data changes daily, so trade counts and segment counts may vary slightly across runs).

### 2. F-09 deferred bug confirmation
expected: `get_instruments_by_cfi` with a deliberately malformed CFI (e.g., `"INVALID_CFI_XYZ"`) returns normally instead of raising `PrimaryAPIError`. This is the intentional DRIFT-02 signal — `verify_cycle_closure("matriz-client")` should return `FAIL` with `missing=["F-09"]` until a future cycle adds the fix + regression test.
result: pending — operator decided Op A + F-09 defer during Task 4.4 checkpoint on 2026-06-10T01:10Z; the CONFIRMED status with deferred regression is by design.

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps

[No gaps — both human items are already substantially satisfied by Task 3.3 live run and Task 4.4 operator decisions; awaiting explicit operator "approved" signal to mark phase complete.]
