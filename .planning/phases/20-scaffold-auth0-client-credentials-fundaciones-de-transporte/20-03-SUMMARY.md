---
phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
plan: 03
subsystem: market-data-client credential redaction
tags: [logging, security, redaction, tdd, auth0]
requires: ["20-01"]
provides:
  - "market_data_client._logging.RedactingFilter"
  - "market_data_client._logging.attach"
affects:
  - "packages/market-data-client/src/market_data_client/_logging.py"
tech-stack:
  added: []
  patterns: ["RedactingFilter mirrors iol _logging with D-11 client_secret pattern swap", "package-logger-scoped attach() (NullHandler + filter)"]
key-files:
  created:
    - "packages/market-data-client/src/market_data_client/_logging.py"
    - "packages/market-data-client/tests/test_logging.py"
  modified: []
decisions:
  - "D-11 pattern set: KEEP Bearer + access_token JSON; DROP password/refresh_token/X-Auth-Token; ADD client_secret (urlenc + JSON)"
  - "Dict-args test records must wrap the mapping in a 1-tuple (logging unwraps it to record.args); a raw dict passed to LogRecord triggers KeyError(0)"
metrics:
  duration: "~10m"
  completed: "2026-07-29"
  tasks: 1
  files: 2
requirements: [CORE-MD-01]
status: complete
---

# Phase 20 Plan 03: _logging.py RedactingFilter + attach() (D-11) Summary

Built the market-data-client credential-redaction filter test-first: `RedactingFilter` scrubs Bearer tokens, JSON `access_token`, and Auth0 `client_secret` (URL-encoded + JSON) from log records; `attach()` is idempotent and binds a NullHandler + filter to the `market_data_client` package logger only.

## What Was Built

- **`_logging.py`** (101 lines): `RedactingFilter` (rewrites `record.msg`, `record.args` dict+tuple, and `record.__dict__` string values) + `attach()` (idempotent, package-logger-scoped). Pattern set per D-11: `_BEARER_RE`, `_ACCESS_TOKEN_JSON_RE`, `_CLIENT_SECRET_URLENC_RE`, `_CLIENT_SECRET_JSON_RE`. `_redact()` runs 4 passes in order (Bearer → client_secret urlenc → client_secret JSON → access_token JSON), idempotent on already-redacted text.
- **`test_logging.py`**: 6 tests — bearer, access_token JSON, client_secret urlenc (with surrounding-field survival), client_secret JSON, args+dict scan coverage, attach idempotency + root-logger-untouched assertion.

## TDD Gate Compliance

- **RED** (`91f5b2e`): `test_logging.py` authored and run before `_logging.py` existed — `ModuleNotFoundError: No module named 'market_data_client._logging'`. Captured as failing.
- **GREEN** (`2493c51`): `_logging.py` implemented — 6/6 pass.
- REFACTOR: none needed (code mirrors iol structure and is clean).

## Verification

- `uv run --package market-data-client pytest packages/market-data-client/tests/test_logging.py` → 6 passed.
- `uv run ruff check` on src + tests → All checks passed.
- `uv run mypy` (strict) on `_logging.py` → Success: no issues.
- CI LOG-01 gate: `grep -rnE 'logging\.basicConfig\s*\(|logging\.root\.\w' packages/market-data-client/src/` → no matches (clean).

Satisfies SC4 and the CORE-MD-01 zero-leak gate (T-20-02, T-20-06 mitigated; T-20-07 attach() root-logger tampering mitigated).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Dict-args test record construction**
- **Found during:** GREEN run of `test_redact_scans_args_and_dict`.
- **Issue:** Passing a raw `dict` as `args=` to `logging.LogRecord` triggers `KeyError: 0` — CPython's LogRecord single-mapping detection does `args[0]` on the dict. This is a test-authoring bug, not an implementation defect (the other 4 tests passed and confirmed the filter logic).
- **Fix:** Wrap the mapping in a 1-tuple (`args=({"h": ...},)`) exactly as `logging._log` does; LogRecord then unwraps it to `record.args`.
- **Files modified:** `packages/market-data-client/tests/test_logging.py`
- **Commit:** `2493c51`

## Self-Check: PASSED

- FOUND: packages/market-data-client/src/market_data_client/_logging.py
- FOUND: packages/market-data-client/tests/test_logging.py
- FOUND commit: 91f5b2e (RED)
- FOUND commit: 2493c51 (GREEN)
