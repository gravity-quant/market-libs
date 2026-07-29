---
phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
reviewed: 2026-07-29T17:32:45Z
depth: deep
files_reviewed: 16
files_reviewed_list:
  - packages/market-data-client/src/market_data_client/__init__.py
  - packages/market-data-client/src/market_data_client/_atransport.py
  - packages/market-data-client/src/market_data_client/_core.py
  - packages/market-data-client/src/market_data_client/_logging.py
  - packages/market-data-client/src/market_data_client/_state.py
  - packages/market-data-client/src/market_data_client/_transport.py
  - packages/market-data-client/src/market_data_client/aio.py
  - packages/market-data-client/src/market_data_client/client.py
  - packages/market-data-client/src/market_data_client/exceptions.py
  - packages/market-data-client/tests/conftest.py
  - packages/market-data-client/tests/test_async_client.py
  - packages/market-data-client/tests/test_client.py
  - packages/market-data-client/tests/test_core.py
  - packages/market-data-client/tests/test_logging.py
  - packages/market-data-client/tests/test_token_lifecycle_async.py
  - packages/market-data-client/tests/test_token_lifecycle.py
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 20: Code Review Report

**Reviewed:** 2026-07-29T17:32:45Z
**Depth:** deep
**Files Reviewed:** 16
**Status:** issues_found

## Summary

Deep, cross-file review of the newly scaffolded `market-data-client` (Auth0 `client_credentials` M2M client) mirroring `iol-client`. The four security-critical concerns called out in the brief all hold up under inspection:

1. **Credential redaction (CORE-MD-01):** `RedactingFilter` covers `Bearer`, JSON `access_token`, and `client_secret` in BOTH url-encoded and JSON shapes. The filter is attached to the package logger before any client import, mutates records in place (so redaction survives propagation to root handlers), and the transport never logs request bodies. No unredacted `client_secret` path was found. **PASS.**
2. **Absolute token URL (Pitfall 1):** both `client._send_auth_request` and `aio._send_auth_request` dispatch the grant to `state.auth0_token_url` directly, never `base_url + path`. `build_token_request` correctly sets `path=""`. **PASS.**
3. **Independent sync/async state + double-checked locking:** separate `_ClientState` instances, lazy per-loop locks, correct double-checked re-auth in `_aensure_token` and the 401 carve-out. No deadlock in the token→client lock ordering. **PASS.**
4. **Anonymous health endpoints (D-08/D-09):** health specs set `authenticated=False`; `_request` skips token fetch and the `if not spec.authenticated: raise` carve-out fires before any re-auth, so a health 401 surfaces immediately with zero token POSTs. **PASS.**

No BLOCKER-severity defects were proven. The findings below are a genuine **sync/async logic divergence** in `configure()` (the single most consequential item, since the mandate explicitly asks for it), a token-parsing crash on a null `expires_in`, a missing required-field validation, and a header-precedence divergence — plus lower-severity notes.

No structural findings block was provided with this review.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: `configure()` sync/async divergence — `base_url` change invalidates the cached token in sync but NOT in async

**File:** `packages/market-data-client/src/market_data_client/client.py:333-352` vs `packages/market-data-client/src/market_data_client/aio.py:335-357`

**Issue:** The two `configure()` implementations do not agree on what triggers token invalidation, and their docstrings document *different contracts*.

- Sync `client.py` sets `rotated = True` for `base_url` (line 333-335), so changing only `base_url` wipes the cached token (`token=None`, `token_expires_at=0.0`). Its docstring explicitly states rotating `base_url` invalidates the token.
- Async `aio.py` does **not** set `credentials_rotated` for `base_url` (line 348-349 sets it without flagging rotation), so changing `base_url` leaves the token intact. Its docstring deliberately lists only `client_id/client_secret/audience/auth0_token_url` as invalidating.

This is a real behavioral fork: `import market_data_client; configure(base_url=...)` drops the token, but `aio.configure(base_url=...)` keeps it. The project constraint requires dual sync/async logic to be mirrored by hand — this is exactly the class of hand-mirroring drift that constraint guards against. Reconcile to one contract. (Recommendation: a `base_url` change should *not* invalidate an Auth0 token bound to an `audience`, i.e. the async behavior is the more defensible one — but pick one and mirror it.)

Additionally the reset *condition* is structured differently: sync uses `if rotated and token is None and token_expires_at is None:` (skip reset when caller seeds a token), while async uses `if credentials_rotated:` then re-applies the explicit token override afterward. Both converge to the same result for the conftest seeding pattern, but the two code shapes make future edits error-prone.

**Fix:** Align both. For example, in `client.py` stop flagging `base_url` as rotation:
```python
if base_url is not None:
    state.base_url = base_url.rstrip("/")
    # base_url is the API host, not an Auth0 grant input — do NOT rotate the token.
```
and normalize the reset gate to match `aio.py` (or vice-versa), then add a test asserting `configure(base_url=...)` has identical token-retention behavior on both surfaces.

### WR-02: `parse_token_response` crashes with `TypeError` when `expires_in` is present but `null`

**File:** `packages/market-data-client/src/market_data_client/_core.py:196-197`

**Issue:** `expires_in = data.get("expires_in", _TOKEN_TTL_FALLBACK_SECONDS)` only falls back when the key is *absent*. If the token response contains `"expires_in": null` (key present, value `None`), `data.get` returns `None`, and `float(expires_in)` raises `TypeError: float() argument must be a string or a real number, not 'NoneType'`. This propagates raw out of `_authenticate()` / `_authenticate_unlocked()` instead of the intended `_TOKEN_TTL_FALLBACK_SECONDS` fallback (D-07) or a clean `MarketDataAuthError`. A non-numeric string value (`"expires_in": "soon"`) raises `ValueError` for the same reason. The D-07 test (`test_parse_token_response_fallback_when_expires_in_absent`) only covers the absent-key case, so this gap is untested.

**Fix:**
```python
expires_in = data.get("expires_in")
if not isinstance(expires_in, (int, float)) or isinstance(expires_in, bool):
    expires_in = _TOKEN_TTL_FALLBACK_SECONDS
expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
```
Add a test with `{"access_token": "TOK", "expires_in": None}` asserting the fallback TTL is used.

### WR-03: `build_token_request` does not validate the required `auth0_token_url`

**File:** `packages/market-data-client/src/market_data_client/_core.py:152-157`

**Issue:** The guard raises `MarketDataAuthError` when `client_id`, `client_secret`, or `audience` is empty, but `auth0_token_url` — documented as **required** in both `client.py` and the `__init__.py` docstrings — is not checked. `_env_auth0_token_url()` defaults to `""` (`_state.py:73-74`). If a consumer sets the three credentials but forgets `MARKET_DATA_AUTH0_TOKEN_URL`, the grant reaches `http.build_request(spec.method, "", ...)` with an empty URL and fails deep inside httpx (`httpx.UnsupportedProtocol` / relative-URL error), producing a confusing traceback instead of the same clean, actionable `MarketDataAuthError` the other missing inputs get.

**Fix:**
```python
if (
    not state.client_id
    or not state.client_secret
    or not state.audience
    or not state.auth0_token_url
):
    raise MarketDataAuthError(
        0,
        "MARKET_DATA_CLIENT_ID, MARKET_DATA_CLIENT_SECRET, MARKET_DATA_AUDIENCE "
        "y MARKET_DATA_AUTH0_TOKEN_URL son requeridos",
    )
```

### WR-04: Authorization header precedence diverges between sync and async `_request`

**File:** `packages/market-data-client/src/market_data_client/aio.py:236` vs `packages/market-data-client/src/market_data_client/client.py:234-238`

**Issue:** For authenticated requests the two shells merge `spec.headers` and the injected `Authorization` in opposite precedence:

- Async: `headers = {"Authorization": f"Bearer {token}", **(spec.headers or {})}` — `spec.headers` *wins* (a spec-provided `Authorization` would silently override the injected Bearer).
- Sync: `headers = dict(spec.headers or {})` then `headers["Authorization"] = ...` — the injected Bearer *wins*.

No current spec carries its own `Authorization`, so this is latent, but it is a genuine hand-mirroring divergence: the same `RequestSpec` could produce a different outgoing `Authorization` header on the two surfaces. The async re-auth path (`aio.py:271`) then force-sets `req.headers["Authorization"]`, making async internally inconsistent with its own initial merge as well.

**Fix:** Make async match sync (injected Bearer authoritative):
```python
headers = {**(spec.headers or {}), "Authorization": f"Bearer {token}"}
```

### WR-05: `Retry-After` honored *in addition to* tenacity's exponential backoff (double wait)

**File:** `packages/market-data-client/src/market_data_client/_transport.py:154-173` and `packages/market-data-client/src/market_data_client/_atransport.py:85-105`

**Issue:** On a retryable status carrying `Retry-After`, the transport sleeps `min(delay, cap)` inside the `with attempt` block (line 159 / 91) and then raises `_RetryableStatus`, which tenacity catches and applies its **own** `wait_exponential_jitter` before the next attempt. The two waits stack, so the effective delay is `Retry-After + jittered_backoff` rather than honoring the server's `Retry-After` as the authoritative interval. On the terminal attempt the `Retry-After` sleep also fires pointlessly right before the response is returned (the loop will not retry again). Behavior is consistently wrong on both sync and async surfaces.

**Fix:** Either skip the manual sleep and feed `Retry-After` into tenacity's `wait` (via a callable that reads the exception), or guard the manual sleep so it does not run on the final attempt and disable tenacity's wait when `Retry-After` is present. At minimum, skip the sleep when `attempt_number >= effective_max_attempts`.

## Info

### IN-01: `configure` surface asymmetry — sync accepts `http_client`, async does not

**File:** `packages/market-data-client/src/market_data_client/client.py:306-361` vs `packages/market-data-client/src/market_data_client/aio.py:315-357`

**Issue:** Sync `configure()` accepts an `http_client` kwarg (closing the previous client before swapping), but `aio.configure()` has no equivalent, so async consumers cannot inject a pre-built `AsyncClient` via `configure`. This is a deliberate-looking scope choice, but combined with WR-01 it means the two `configure()` contracts differ in three ways. Document the asymmetry explicitly or add the parameter for parity.

### IN-02: `RedactingFilter` only guards the `market_data_client` logger — httpx/httpcore DEBUG logs bypass it

**File:** `packages/market-data-client/src/market_data_client/_logging.py:88-101`

**Issue:** Redaction is attached to `logging.getLogger("market_data_client")` only (correct per LOG-01 — must not touch root). If a consumer enables `logging.getLogger("httpx")` / `"httpcore"` at DEBUG, those records do not pass through `RedactingFilter`. In practice httpx does not log request bodies or `Authorization` headers, so `client_secret` (in the form body) and the Bearer are not exposed — hence INFO, not a leak. Worth a one-line note in the module docstring so a future endpoint that logs a URL with a query-string credential is not assumed to be auto-redacted.

### IN-03: `assert token is not None` used for runtime narrowing — stripped under `python -O`

**File:** `packages/market-data-client/src/market_data_client/aio.py:235,270`; `packages/market-data-client/src/market_data_client/client.py:237,266`

**Issue:** The Bearer-injection paths rely on `assert self._state.token is not None` for both mypy narrowing and a runtime guard. Under `python -O` asserts are elided; if the invariant were ever violated the code would emit `Authorization: Bearer None`. The invariant does hold today (`_ensure_token`/`_aensure_token` raise on failure), so this is defensive hygiene rather than a live bug. Consider an explicit `if token is None: raise MarketDataAuthError(...)` in the token-injection path.

### IN-04: `parse_token_response` / `parse_health_response` assume `resp.json()` returns a dict

**File:** `packages/market-data-client/src/market_data_client/_core.py:192-193,234`

**Issue:** `data: dict[str, Any] = resp.json()` is annotated as a dict but `resp.json()` may return a list or scalar for a malformed/unexpected body; the subsequent `data.get(...)` then raises `AttributeError`. Auth0 and the health endpoints return objects, so this is low-likelihood, but a defensive `isinstance(data, dict)` guard would convert a surprising `AttributeError` into a clean `MarketDataAuthError`/`MarketDataAPIError`.

---

_Reviewed: 2026-07-29T17:32:45Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
