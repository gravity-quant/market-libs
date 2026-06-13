---
phase: 08-retries-backoff-structured-logging
fixed_at: 2026-06-13T00:00:00Z
review_path: .planning/phases/08-retries-backoff-structured-logging/08-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 08: Code Review Fix Report

**Fixed at:** 2026-06-13
**Source review:** .planning/phases/08-retries-backoff-structured-logging/08-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope (Critical + production-source Warnings): 7 (CR-01, CR-02, WR-01, WR-02, WR-06, WR-07, WR-08)
- Fixed: 7
- Skipped: 0
- Deferred this cycle:
  - WR-03 (regex bounds — over-redact is safer)
  - WR-04 (matriz `_X_USERNAME_RE` dead code — cosmetic)
  - WR-05 (CI grep extension — defense-in-depth)
  - 6 Info findings (cosmetic/perf/test-cleanup)

**Test count delta:** Phase 8 baseline 627 passed + 3 skipped → 755 passed + 3 skipped (**+128 regression tests**).

**Gates status (all GREEN post-fix):**
- `uv run pytest packages/ verification/ -q` → 755 passed, 3 skipped, 1 deselected in ~151s
- `uv run ruff check packages/ verification/` → "All checks passed!"
- `uv run ruff format --check packages/ verification/` → "116 files already formatted"
- `uv run mypy` → "Success: no issues found in 45 source files"
- `uv run lint-imports` → "Contracts: 4 kept, 0 broken"

---

## Fixed Issues

### CR-01: matriz Risk-API 401 reauth guard never reached the carve-out branch

**Files modified:** `verification/test_retry_401_reauth.py`
**Commit:** `745503c` — `test(08): fix CR-01 — exercise real Risk surface in 401 reauth guard`
**Applied fix:**

Rewrote `test_matriz_risk_api_401_does_not_reauth` to exercise `matriz_client.get_positions("acc")` (the real Risk surface, `idempotent=True`) instead of the `_matriz_legacy_request` shim (which builds `RequestSpec` with `idempotent=False`). With `idempotent=False`, the RetryTransport short-circuits with 1 wire request REGARDLESS of whether the D-23 carve-out exists — the previous `len(requests) == 1` assertion was vacuously true. Now if the shell drops the `if spec.auth_basic is not None:` carve-out, the code falls through to the Token path, attempts re-auth via `/auth/getToken`, producing multiple wire requests and a different exception type. The assertion (1 wire request + AuthenticationError raised) is now the actual D-23 contract.

**Verification:** Temporarily commenting out the carve-out in `client.py:248-269` produces `httpx.TimeoutException` (no mock for `/auth/getToken`) — confirming the test reaches the D-23 branch. Restored carve-out makes test PASS.

### CR-02: matriz auth_basic redaction guard never triggered any matriz log records

**Files modified:** `verification/test_logging_no_token_leak.py`, `packages/matriz-client/src/matriz_client/_transport.py`
**Commit:** `625cb55` — `test(08): fix CR-02 — exercise real Risk surface for auth_basic redaction guard`
**Applied fix:**

Three coupled changes:

1. **`_transport.py`**: propagate `auth_basic` from `request.extensions` into the WARNING / ERROR log records' extras dict. Previously the transport read `account_id` from extensions but ignored `auth_basic`. Without `auth_basic` in the extras, the `RedactingFilter` had nothing to split (the D-22 wire-up was missing).

2. **Test rewrite**: changed from `_matriz_legacy_request` (`idempotent=False`, no WARNING ever emitted) to `matriz_client.get_positions("acc")` (`idempotent=True`) with a 503→200 retry chain. The retry transport now emits a WARNING per attempt.

3. **Test assertions**: assert directly that the WARNING record has `record.__dict__["auth_basic_user"] == "risk-user"` AND `auth_basic_password == "***"` AND the original `"auth_basic"` key was deleted from `__dict__`. This genuinely exercises the `_redact_auth_basic_tuple` code path end-to-end.

**Verification:** Temporarily commenting out the tuple split branch in `RedactingFilter.filter` makes the test FAIL with the tuple `('risk-user', 'SECRET-LITERAL-12345')` visible in `record.__dict__['auth_basic']`. Restored filter makes test PASS.

### WR-01: iol/higyrus async re-auth race window (token-clear outside lock)

**Files modified:**
- `packages/iol-client/src/iol_client/aio.py` + `tests/test_async_client.py` — commit `56c851f`
- `packages/higyrus-client/src/higyrus_client/aio.py` + `tests/test_async_client.py` — commit `b98e2b2`

**Applied fix:**

Wrapped token-clear + re-auth under a single `async with token_lock:` block in `AsyncClient._request()` (both iol and higyrus). The OLD code cleared `self._state.token = None` OUTSIDE the lock then called `self._ensure_token()` (which re-acquires the lock). In practice the double-checked locking inside `_ensure_token` already prevented duplicate logins (so WR-01 was a safety-clarity finding rather than an active duplicate-login bug), but the contract was non-atomic.

The fix inlines the unlocked variants (calling `_ensure_token` from within the lock would deadlock) and adds an inner re-check against the captured local stale token so a coroutine that arrives AFTER another coroutine refreshed will skip its own re-auth.

iol additionally preserves the refresh-then-password-fallback path within the lock:
```python
async with lock:
    if self._state.token is None or self._state.token == token:
        self._state.token = None
        if self._state.refresh_token:
            try:
                await self._refresh_unlocked()
            except IOLAuthError:
                await self._login_unlocked()
        else:
            await self._login_unlocked()
```

higyrus is simpler (no refresh_token flow): just `_login_unlocked()` under the lock.

**Regression tests added** (per package): `test_concurrent_401_triggers_exactly_one_reauth` — 3 concurrent coroutines hit 401 on initial request; assert exactly 1 POST `/token` (iol) or `/api/login` (higyrus) wire request fires + all 3 succeed on retry with FRESH token. Test design uses `match_headers={"Authorization": "Bearer STALE|FRESH"}` to distinguish stale vs fresh on the GET endpoint; login mock registered ONCE (non-reusable) so the test FAILS with `TimeoutException` if a duplicate login is attempted.

### WR-02: 401 carve-out raises without `resp.read()` — potential HTTP/2 stream leak

**Files modified:**
- `packages/matriz-client/src/matriz_client/client.py` + `tests/test_client.py` — commit `1a20fd6`
- `packages/iol-client/src/iol_client/client.py` + `aio.py` + `tests/test_client.py` — commit `6cad440`
- `packages/higyrus-client/src/higyrus_client/client.py` + `aio.py` + `tests/test_client.py` — commit `4770efa`

**Applied fix:**

Added explicit `resp.read()` (sync) / `await resp.aread()` (async) BEFORE every 401 raise-site on the carve-out paths. Investigation showed that `httpx.Client.send()` already auto-consumes the response body by default (`stream=False` → `response.read()` called inside `Client.send`), and `_raise_for_response` in iol/higyrus reads `resp.text` / `resp.json()` which buffers the body. So the body IS effectively consumed today — but the explicit `resp.read()` documents the Phase 7 D-06 body-consume-then-raise contract on the carve-out paths where `_raise_for_response` is bypassed (matriz Risk path) AND guards against future http2=True streaming responses or changes to httpx's auto-consume default.

Three raise-sites hardened per package:
- matriz Risk-path 401 (D-23 carve-out) — first occurrence not via `_raise_for_response`
- matriz Token-path second-401 (after re-auth-once exhausted)
- iol/higyrus Token-path 401 paths (sync + async)

**Regression tests added** (per package):
- matriz: `test_risk_api_401_carve_out_consumes_body_before_raise` + `test_token_path_second_401_carve_out_consumes_body_before_raise` (in `test_client.py`)
- iol: `test_401_carve_out_body_consumed_before_raise` (in `test_client.py`)
- higyrus: `test_401_carve_out_body_consumed_before_raise` (in `test_client.py`)

Each mocks a 401 with non-empty body and asserts the typed AuthError is raised + the exact wire request count (1 for matriz Risk; 3 for token-path re-auth-once contract).

### WR-06: `configure(max_retries=)` accepts negatives and floats silently

**Files modified:**
- `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` + `aio.py`
- `packages/iol-client/src/iol_client/client.py` + `aio.py`
- `packages/higyrus-client/src/higyrus_client/client.py` + `aio.py`
- `packages/matriz-client/src/matriz_client/client.py` (sync only per D-25)
- `verification/test_max_retries_validation.py` (NEW)

**Commit:** `0ab7a7d` — `fix(all): WR-06 — validate max_retries kwarg is non-negative int`

**Applied fix:**

Added `_validate_max_retries(value)` helper to each package's `client.py` (and re-imported by `aio.py`). The helper is duplicated 4x per the "no shared internals between packages" project constraint. Called from every `Client.__init__` / `AsyncClient.__init__` / `configure()` / `aio.configure()` entry point.

Validation rejects:
- Negative ints (`max_retries=-1`)
- Floats (`max_retries=1.5`) — accidental Python decimal coercion
- Strings (`max_retries="2"`) — unparsed env-var passthrough
- Bools (`max_retries=True/False`) — bool is technically int in Python so `isinstance(True, int)` returns True, but accepting it masks a likely caller error. The validator rejects bool explicitly.

**Regression test added** at `verification/test_max_retries_validation.py` — 112 parametrized cases covering every entry point on every package against 6 bad values + 4 good values.

### WR-07: `aio.configure()` silently drops the prior `httpx.AsyncClient` — connection pool leak

**Files modified:**
- `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py`
- `packages/iol-client/src/iol_client/aio.py`
- `packages/higyrus-client/src/higyrus_client/aio.py`
- `verification/test_async_configure_resource_warning.py` (NEW)

**Commit:** `a8342e7` — `fix(all): WR-07 — emit ResourceWarning on aio.configure() http_client replacement`

**Applied fix:**

Emit `ResourceWarning` when overwriting a live `_state.http_client` in `aio.configure()`. The warning text includes the recommended `await aio.aclose()` pre-step. Production code MUST NOT call `aclose()` automatically from `configure()` because `configure()` is synchronous and there's no event loop guaranteed at that point — the warning is the only sensible signal.

Three packages × per-call-site coverage (ambito has 1 site, iol has 2 sites for max_retries= vs http_client=, higyrus has 1 site since it rebuilds the AsyncClient via the constructor carry-forward pattern). matriz has no async configure() per D-25.

**Regression test added** at `verification/test_async_configure_resource_warning.py` — 6 parametrized cases (3 packages × 2 scenarios: warns-when-live and no-warn-when-empty).

### WR-08: matriz `raise_for_response` raised stdlib `httpx.HTTPStatusError` instead of typed `MatrizClientError`

**Files modified:**
- `packages/matriz-client/src/matriz_client/_core.py`
- `packages/matriz-client/tests/test_core.py`
- `verification/test_retry_mutation_gate.py`

**Commit:** `952a0de` — `fix(matriz): WR-08 — map raise_for_response status codes to typed exceptions`

**Applied fix:**

Mirrored the iol/higyrus mapping pattern in matriz `_core.raise_for_response`:
- 2xx / 3xx → no-op (new — consistent with iol/higyrus)
- 401 / 403 → `AuthenticationError` (already a `PrimaryAPIError` subclass)
- Any other 4xx / 5xx → `PrimaryAPIError` with `HTTP {code}` description

Callers can now reliably `except MatrizClientError:` to catch all matriz failures.

**Knock-on test updates:**

- `test_core.py::test_parse_envelope_response_raises_on_http_error_status` updated: now expects `PrimaryAPIError` + `HTTP 500` in description instead of `HTTPStatusError`.
- 4 new regression tests added in `test_core.py`:
  - `test_raise_for_response_maps_401_to_authentication_error`
  - `test_raise_for_response_maps_403_to_authentication_error`
  - `test_raise_for_response_maps_500_to_primary_api_error`
  - `test_raise_for_response_noop_on_2xx`
- `verification/test_retry_mutation_gate.py::_expected_error_types` tuple for matriz tightened from `(MatrizClientError, HTTPStatusError)` to `(MatrizClientError,)` — matriz is now self-consistent on the typed exception hierarchy. ambito/iol/higyrus keep `HTTPStatusError` tolerance as defensive belt-and-suspenders (those paths weren't touched in this review cycle).

### Style: ruff format auto-fix

**Commit:** `43cdda9` — `style(08): apply ruff format to WR-06/WR-07 review-fix changes`

Format-only pass after the per-finding fixes landed. No logic changes.

---

## Verification Post-fix

### Test suite delta

| Phase | Total | Skipped | Note |
|---|---|---|---|
| Phase 8 baseline (post-review) | 627 | 3 | Phase 8 final pre-review-fix |
| **Post-review-fix (this report)** | **755** | **3** | **+128 regression tests across 7 closures** |

Test breakdown of the +128 delta:
- CR-01: 0 (rewritten in place — net change 0)
- CR-02: 0 (rewritten in place — net change 0)
- WR-01: +2 (one regression test per package: iol + higyrus)
- WR-02: +4 (3 regression tests in packages + matriz contributes 2)
- WR-06: +112 (parametrized 4 packages × 5 entry points × 6 bad + 4 good values)
- WR-07: +6 (3 packages × 2 scenarios)
- WR-08: +4 (3 regression tests + 1 noop test)

### Gates

```
$ uv run pytest packages/ verification/ -q
... 755 passed, 3 skipped, 1 deselected in 150.57s (0:02:30)

$ uv run ruff check packages/ verification/
All checks passed!

$ uv run ruff format --check packages/ verification/
116 files already formatted

$ uv run mypy
Success: no issues found in 45 source files

$ uv run lint-imports
Analyzed 41 files, 74 dependencies.
ambito_financiero_client._core does not depend on transport modules KEPT
higyrus_client._core does not depend on transport modules KEPT
iol_client._core does not depend on transport modules KEPT
matriz_client._core does not depend on transport modules KEPT
Contracts: 4 kept, 0 broken.
```

The 3 skipped tests are all the D-25 forward-references (matriz async REST surface deferred to Phase 10 REFAC-04 + TokenStore). None mask a Phase 8 deficiency.

---

## Out of Scope (deferred this cycle)

### Warnings deferred

- **WR-03** (Redaction regex bounds unanchored) — the over-redaction is safer than under-redaction in the current shape; the proposed `(?:^|[&?])` prefix is a defensive nicety. Deferred to a future cycle when the regex framework is revisited.
- **WR-04** (matriz `_X_USERNAME_RE` dead code) — cosmetic; the dead pattern is harmless and documented inline as "for symmetry-completeness". Removal can ride with a future cleanup pass.
- **WR-05** (CI `lint-logging` grep extension) — the proposed `logging.getLogger()` (no args) detection is defense-in-depth; the runtime regression test `test_logging_root_unchanged.py` is the actual backstop and is GREEN. Defer to Phase 11 if the grep is found to under-cover in production.

### Info findings (cosmetic / perf / test cleanup)

- **IN-01** `RedactingFilter` rebuilds `record.args` unconditionally — performance-only; out of v1 scope per the review note.
- **IN-02** matriz `_matriz_legacy_request` lacks `DeprecationWarning` — Phase 9 BUG cleanup can add.
- **IN-03** `_AUTH_PACKAGES` / `_PACKAGES` literals duplicated across cross-cutting tests — risk of drift; defer extraction to a future cycle.
- **IN-04** `test_async_cancellation.py` parametrizes matriz then skips — drop matriz from `_ASYNC_PACKAGES` until Phase 10 grows the surface.
- **IN-05** `test_retry_after_capped_at_60s` is slow but unmarked — add `@pytest.mark.slow_retry`.
- **IN-06** `RetryTransport.__init__` `**kwargs` swallows typos — minor API design observation, not a bug.

---

## Final Return — Fix Commit Hashes

```
745503c test(08): fix CR-01 — exercise real Risk surface in 401 reauth guard
625cb55 test(08): fix CR-02 — exercise real Risk surface for auth_basic redaction guard
1a20fd6 fix(matriz): WR-02 — consume body before raising on 401 carve-out (Phase 7 D-06 hardening)
6cad440 fix(iol):    WR-02 — consume body before raising on 401 carve-out (Phase 7 D-06 hardening)
4770efa fix(higyrus): WR-02 — consume body before raising on 401 carve-out (Phase 7 D-06 hardening)
56c851f fix(iol):    WR-01 — atomic token-clear+ensure-token in async 401 reauth
b98e2b2 fix(higyrus): WR-01 — atomic token-clear+ensure-token in async 401 reauth
0ab7a7d fix(all):    WR-06 — validate max_retries kwarg is non-negative int
a8342e7 fix(all):    WR-07 — emit ResourceWarning on aio.configure() http_client replacement
952a0de fix(matriz): WR-08 — map raise_for_response status codes to typed exceptions
43cdda9 style(08):   apply ruff format to WR-06/WR-07 review-fix changes
```

11 atomic commits, +128 regression tests, all gates GREEN. Phase 8 review-fix CYCLE CLOSED.

---

_Fixed: 2026-06-13_
_Fixer: Claude (gsd-code-fixer, Phase 8 review-fix iteration 1)_
_Iteration: 1_
