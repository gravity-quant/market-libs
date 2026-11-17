---
phase: quick-261117-ny5
plan: 01
status: complete
subsystem: matriz-client
tags: [matriz, auth, token-store, 401, sync, bugfix]
requirements: [QUICK-261117-ny5]
key-files:
  modified:
    - packages/matriz-client/src/matriz_client/client.py
    - packages/matriz-client/tests/test_client.py
commits:
  - 0d52da2
completed: 2026-11-17
---

# Quick 261117-ny5: Sync matriz 401 re-auth invalidates TokenStore — Summary

Sync `Client._request` now runs the same Token-path 401 sequence as `aio.AsyncClient._request`
(consume body, `token = None`, `token_expires_at = 0.0`, `token_store.invalidate()`, re-ensure,
retry once), so a server-rejected token cached in the TokenStore is replaced instead of re-sent.

## What changed

- `client.py` `_request` 401 branch: added `resp.read()`, `token_expires_at` reset and
  `token_store.invalidate()` before `_ensure_token()`; comment and docstring updated.
  Risk API (auth_basic) path, second-401 raise, `_ensure_token`, `_token_store.py` and the TTL
  clock are untouched. `aio.py` needed no change.
- `test_client.py`: `test_token_path_401_invalidates_token_store_and_reauths`.

## RED / GREEN

- Pre-fix: test failed with `AssertionError: assert 1 == 2` (only one `POST /auth/getToken`),
  plus pytest-httpx teardown error for the unrequested second `getToken` mock.
- Post-fix: passes. Full matriz-client suite 323 passed; ruff check, ruff format --check and
  mypy strict clean.

## Deviations from Plan

1. **[Rule 1 - Test bug] Header capture at send time.** The plan's assertion on
   `get_requests()[0].headers` cannot work: the client retries by mutating the same
   `httpx.Request` object, and pytest-httpx records it by reference, so both entries showed
   `fresh-token`. The endpoint is mocked with a callback that records `X-Auth-Token` per send
   and returns 401 then 200; assertion is `sent_tokens == ["initial-token", "fresh-token"]`.
   Re-verified RED against reverted `client.py` (fails as above) and GREEN with the fix.
2. **[Rule 3 - Blocking] Tools run from `.venv` instead of `uv run`.** `uv run` aborts because
   `packages/market-data-client/` (untracked, contains only an `.env`) matches the `packages/*`
   workspace glob without a `pyproject.toml`. Left untouched; ran `.venv/bin/python -m pytest`,
   `.venv/bin/ruff`, `.venv/bin/mypy` instead.
3. Single commit for both tasks (as specified in Task 2), rather than separate RED/GREEN commits.

## Self-Check: PASSED

- client.py and test_client.py modified; commit 0d52da2 exists and contains only those two files.
