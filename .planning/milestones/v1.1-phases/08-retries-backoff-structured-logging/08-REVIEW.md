---
phase: 08-retries-backoff-structured-logging
reviewed: 2026-06-13T00:00:00Z
depth: standard
files_reviewed: 49
files_reviewed_list:
  - packages/ambito-financiero-client/pyproject.toml
  - packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/_atransport.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/_core.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/_logging.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/_transport.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/aio.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/client.py
  - packages/ambito-financiero-client/tests/test_client_class.py
  - packages/ambito-financiero-client/tests/test_logging.py
  - packages/ambito-financiero-client/tests/test_transport.py
  - packages/higyrus-client/pyproject.toml
  - packages/higyrus-client/src/higyrus_client/__init__.py
  - packages/higyrus-client/src/higyrus_client/_atransport.py
  - packages/higyrus-client/src/higyrus_client/_core.py
  - packages/higyrus-client/src/higyrus_client/_logging.py
  - packages/higyrus-client/src/higyrus_client/_transport.py
  - packages/higyrus-client/src/higyrus_client/aio.py
  - packages/higyrus-client/src/higyrus_client/client.py
  - packages/higyrus-client/tests/test_async_client.py
  - packages/higyrus-client/tests/test_client.py
  - packages/higyrus-client/tests/test_logging.py
  - packages/higyrus-client/tests/test_transport.py
  - packages/iol-client/pyproject.toml
  - packages/iol-client/src/iol_client/__init__.py
  - packages/iol-client/src/iol_client/_atransport.py
  - packages/iol-client/src/iol_client/_core.py
  - packages/iol-client/src/iol_client/_logging.py
  - packages/iol-client/src/iol_client/_transport.py
  - packages/iol-client/src/iol_client/aio.py
  - packages/iol-client/src/iol_client/client.py
  - packages/iol-client/tests/test_async_client.py
  - packages/iol-client/tests/test_client.py
  - packages/iol-client/tests/test_logging.py
  - packages/iol-client/tests/test_transport.py
  - packages/matriz-client/pyproject.toml
  - packages/matriz-client/src/matriz_client/__init__.py
  - packages/matriz-client/src/matriz_client/_core.py
  - packages/matriz-client/src/matriz_client/_logging.py
  - packages/matriz-client/src/matriz_client/_transport.py
  - packages/matriz-client/src/matriz_client/client.py
  - packages/matriz-client/tests/test_logging.py
  - packages/matriz-client/tests/test_transport.py
  - verification/test_async_cancellation.py
  - verification/test_logging_no_token_leak.py
  - verification/test_logging_root_unchanged.py
  - verification/test_retry_401_reauth.py
  - verification/test_retry_after_cap.py
  - verification/test_retry_mutation_gate.py
  - .github/workflows/ci.yml
findings:
  critical: 2
  warning: 8
  info: 6
  total: 16
status: issues_found
---

# Phase 8: Code Review Report

**Reviewed:** 2026-06-13
**Depth:** standard
**Status:** issues_found

## Summary

Phase 8 lands a per-package RetryTransport/AsyncRetryTransport pair, a per-package RedactingFilter, structured logging extras, and re-auth-once flows for the auth-bearing packages (iol/higyrus/matriz). The major invariants — mutation gate (D-01), 401-not-in-`retry_on=` (D-07/D-23), Retry-After cap (D-04), `asyncio.sleep` cancellation propagation (D-32), root logger not touched (LOG-01), credential redaction (LOG-02), and matriz `_atransport.py` deferred to Phase 10 (D-25) — are all wired correctly in source and exercised by direct transport unit tests plus cross-cutting `verification/` guards.

**However**, the cross-cutting verification suite contains **two serious correctness gaps** (CR-01, CR-02) that will let the regressions they were designed to catch silently pass. Plus the iol/higyrus async re-auth flow has a deadlock-adjacent race (WR-01), the matriz Risk-path 401 carve-outs leak unread response bodies under HTTP/2 (WR-02), redaction regex bounds are unanchored (WR-03), `configure(max_retries=)` doesn't validate input (WR-06), `aio.configure()` leaks the prior connection pool (WR-07), and matriz `raise_for_response` is inconsistent with iol/higyrus typed exceptions (WR-08).

---

## Critical Issues

### CR-01 — `verification/test_retry_401_reauth.py` matriz Risk-API guard never reaches the carve-out branch and silently passes

**File:** `verification/test_retry_401_reauth.py:249-291` (function `test_matriz_risk_api_401_does_not_reauth`)

**Issue:** The test calls `client._matriz_legacy_request("GET", "/risk/account/something", auth_basic=("risk-user", "risk-pass"))`. Tracing through `Client._matriz_legacy_request` → it builds `RequestSpec(method=..., path=..., params=params, auth_basic=auth_basic)` with `idempotent` defaulting to `False`. The RetryTransport sees a non-idempotent request and passes through with 1 wire request **regardless of whether the D-23 carve-out exists**. The test's `len(requests) == 1` assertion is therefore meaningless — it would still pass even if the entire `if spec.auth_basic is not None` branch were deleted from `_request()`. The `pytest.raises(AuthenticationError)` catches the regression for the wrong reason (parser-level rather than shell-level branch).

**Impact:** If the D-23 carve-out is regressed, real Risk endpoints (which set `idempotent=True`) would silently fall through to the token re-auth path — exactly the failure mode the test purports to prevent.

**Fix:** Exercise the actual Risk surface (e.g. `matriz_client.get_positions("acc")`), not the legacy shim. See full patch sketch in the reviewer's notes.

---

### CR-02 — `verification/test_logging_no_token_leak.py` matriz Risk-path subtest never triggers any matriz log records → tuple-splitting filter not exercised end-to-end

**File:** `verification/test_logging_no_token_leak.py:133-178` (function `test_matriz_auth_basic_password_not_logged`)

**Issue:** The test calls `_matriz_legacy_request(..., auth_basic=("risk-user", _SECRET_LITERAL))` which builds a `RequestSpec` with `idempotent=False`. The transport bypasses the retry loop on non-idempotent requests, so **no WARNING log record is ever emitted**. With zero matriz-emitted records to scan, `for r in caplog.records: assert _SECRET_LITERAL not in r.getMessage()` is **vacuously true**. The `RedactingFilter`'s `auth_basic` tuple-splitting code path (D-22) is never exercised.

**Impact:** A regression that removed `_redact_auth_basic_tuple` would not be caught by this test. The redaction guard for matriz auth_basic credentials is effectively absent.

**Fix:** Exercise a real Risk endpoint with a 503→200 retry chain so the WARNING record fires; assert `record.__dict__["auth_basic_user"] == "risk-user"` AND `auth_basic_password == "***"`. Patch sketch in reviewer notes.

---

## Warnings

### WR-01 — iol/higyrus async `_request` re-auth has a race window between token-clear and `_ensure_token()` re-acquire

**Files:** `packages/iol-client/src/iol_client/aio.py:308-313`, `packages/higyrus-client/src/higyrus_client/aio.py:309-316`

**Issue:** `self._state.token = None` happens outside any lock; if another coroutine reads `_state.token` between this assignment and the start of `_ensure_token()`, both coroutines will race into re-login. The thundering-herd protection of double-checked locking is defeated.

**Fix:** Atomic clear+re-auth inside the token_lock:
```python
async with lock:
    self._state.token = None
await self._ensure_token()
```

---

### WR-02 — matriz Risk-path 401 carve-out raises without `resp.read()` — potential HTTP/2 stream leak

**File:** `packages/matriz-client/src/matriz_client/client.py:261-269`

**Issue:** `if resp.status_code == 401: raise AuthenticationError(...)` runs before the body is consumed. The retry transport's idempotent path consumes via `response.read()` only on retryable statuses; 401 is not retryable, so the response goes back unread. Under HTTP/2, the unread stream leaks against the connection pool.

This is the Phase 7 D-06 invariant — "body-consume-then-raise" — partially regressed for non-retryable error statuses on the pass-through path. Same hardening recommended in iol-client (`client.py:301-313`, `aio.py:304-316`) and higyrus-client (`client.py:285-307`, `aio.py:307-329`).

**Fix:** `resp.read(); raise AuthenticationError(...)` at every 401 raise-site in the shell.

---

### WR-03 — Redaction regexes have unanchored bounds → false-positive matches against unrelated query strings

**Files:** All packages' `_logging.py` (e.g. `iol-client/src/iol_client/_logging.py:51-59`)

**Issue:** `_PASSWORD_URLENC_RE = re.compile(r"(password=)[^&\s]+")` matches `mypassword=value`. Same for `_REFRESH_TOKEN_URLENC_RE` and `_CUIT_QUERY_RE`. The redaction itself is harmless (it never under-redacts; it only over-redacts), but the patterns may scrub user-controlled query values that happen to contain these substrings.

**Fix:** Anchor with `(?:^|[&?])` prefix:
```python
_PASSWORD_URLENC_RE = re.compile(r"(?:^|[&?])(password=)[^&\s]+")
```

---

### WR-04 — matriz `_X_USERNAME_RE` is dead code

**File:** `packages/matriz-client/src/matriz_client/_logging.py:71-72`

**Issue:** Declared with a "for symmetry-completeness" comment but never used in `_redact()` and never referenced by any test.

**Fix:** Remove, or document the omission inline in `_redact()` instead.

---

### WR-05 — CI `lint-logging` grep is incomplete

**File:** `.github/workflows/ci.yml:42-50`

**Issue:** The grep `'logging\.basicConfig\s*\(|logging\.root\.\w'` misses `logging.getLogger()` (no args = root), `getattr(logging, 'root')`, `logger.root.addHandler(...)`, and `logging.Logger.manager.root`. The runtime regression test `test_logging_root_unchanged.py` is the real backstop, but the static guard's coverage claim overstates.

**Fix:** Extend pattern to include `logging\.getLogger\(\s*\)` and `\.root\.addHandler`.

---

### WR-06 — `configure(max_retries=)` accepts negatives and floats silently

**Files:** All `Client.__init__` / `configure()` sites

**Issue:** `Client(max_retries=-5)` constructs successfully; `Client(max_retries=1.5)` constructs but trips inside tenacity later with a confusing error.

**Fix:**
```python
if max_retries is not None:
    if not isinstance(max_retries, int) or max_retries < 0:
        raise ValueError(f"max_retries must be a non-negative int, got {max_retries!r}")
```

---

### WR-07 — `aio.configure()` silently drops the prior `httpx.AsyncClient` without `aclose()` → connection pool leak

**Files:** `ambito_financiero_client/aio.py:178-191`, `iol-client/aio.py:431-434`, `higyrus-client/aio.py:444-465`

**Issue:** The docstring openly admits the leak. Every call to `aio.configure()` after the first leaks a TCP pool + SSL context. Not blocking for short-lived tests but unbounded for long-running processes with rotating credentials.

**Fix:** Emit `ResourceWarning` when overwriting a live `_state.http_client`, document the recommended `await aio.aclose()` pre-step.

---

### WR-08 — matriz `_core.raise_for_response` uses stdlib `resp.raise_for_status()` → callers see `httpx.HTTPStatusError`, not `matriz_client.MatrizClientError`

**File:** `packages/matriz-client/src/matriz_client/_core.py:173-180`

**Issue:** Unlike iol/higyrus which map 401/403/429/4xx/5xx to typed exceptions, matriz raises stdlib `httpx.HTTPStatusError`. `verification/test_retry_mutation_gate.py:97-105` already tolerates both, but callers can no longer rely on `except MatrizClientError:` to catch all matriz failures.

**Fix:** Map status codes to typed `AuthenticationError`/`PrimaryAPIError`. Knock-on effects on `parse_envelope_response` and `_parse_risk_response` callers are limited because the subsequent `data.get("status") == "ERROR"` check masks most cases — only true HTTP errors change exception type.

---

## Info

### IN-01 — `RedactingFilter` rebuilds `record.args` tuple unconditionally
Performance-only; out of v1 scope. Future tuning: early-exit if no marker substring present.

### IN-02 — matriz `_matriz_legacy_request` documented as DEPRECATED but emits no `DeprecationWarning`
Phase 9 BUG cleanup may want to add the warning.

### IN-03 — `_AUTH_PACKAGES` / `_PACKAGES` literals duplicated across cross-cutting test modules
Risk of drift. Extract to `verification/_packages.py`.

### IN-04 — `test_async_cancellation.py` parametrizes matriz then immediately skips
Drop matriz from `_ASYNC_PACKAGES` until Phase 10 grows the surface.

### IN-05 — `test_retry_after_capped_at_60s` is documented as slow but unmarked
Add `@pytest.mark.slow_retry` + register the marker in root `pyproject.toml`.

### IN-06 — `RetryTransport.__init__` `**kwargs` swallows typos until super().__init__
Minor API design observation; not a bug.

---

## Cross-cutting Notes — Verified Invariants (PASS)

- **Pitfall 4 (mutation gate):** `RequestSpec.idempotent=False` for matriz mutating builders. Transport short-circuits on `idempotent=False`. Direct unit test asserts 1 wire request. ✓
- **Pitfall 5 (401 retry storm):** `_RETRYABLE_STATUS = frozenset({408, 409, 429, *range(500, 600)})` — 401 absent. AuthError types not in `retry_on=`; shells handle re-auth-once. ✓
- **Pitfall 6 (root logger hijack):** No `logging.basicConfig` / `logging.root.*` in source. NullHandler + filter attached to `getLogger("<pkg>")` only. ✓
- **Pitfall 16 (asyncio.CancelledError):** `await asyncio.sleep(...)` in AsyncRetryTransport; tenacity AsyncRetrying respects cancellation. ✓
- **Pitfall 17 (LogRecord stdlib attr collision):** Extras don't collide with stdlib `LogRecord.__dict__` keys. ✓
- **D-23 matriz Risk API auth_basic carve-out:** Shell branches on `spec.auth_basic is not None`. ✓ in source (but **see CR-01** — guard test is flawed)
- **D-24 PrimaryAPIError never retried:** Raised post-transport-return; not in `retry_on=`. ✓
- **D-25 matriz `_atransport.py` absent + `aio.py` unchanged:** Confirmed. ✓
- **Per-package serial:** Each package has its own copies; no cross-package imports. ✓
- **Tenacity API:** Iterator-style `for attempt in Retrying(...)` with `reraise=True` is documented 9.x API. ✓

---

*Reviewed: 2026-06-13*
*Reviewer: Claude (gsd-code-reviewer)*
*Depth: standard*
