---
phase: 08-retries-backoff-structured-logging
plan: 05
subsystem: matriz-client
tags: [phase-08, matriz, atomic-commit, rely, log, sync-only, risk-api-no-reauth, auth-basic-redaction, primary-status-error-no-retry, duplicate-order-prevention]
requires: [phase-07 _core.py extraction, phase-08-01 cross-cutting scaffolding, phase-08-02 ámbito canary, phase-08-03 iol auth pattern, phase-08-04 higyrus account_id propagation]
provides:
  - matriz_client._transport.RetryTransport (sync ONLY — NO _atransport.py per D-25)
  - matriz_client._logging.RedactingFilter + attach() (Bearer + X-Auth-Token + X-Password + Authorization Basic + D-22 auth_basic tuple split)
  - 401 re-auth-once at Client._request (Token path; D-02 / RELY-04)
  - Risk API skip-re-auth on 401 (auth_basic path; D-23) — AuthenticationError raised immediately, NO infinite loop
  - PrimaryAPIError NEVER in transport retry_on= (D-24 — 200-OK status=ERROR is application-level)
  - Mutation gate on Primary order builders (HTTP GET semantically mutating per quirk — Pitfall 4 critical)
  - Login idempotent=True per D-03 (transient 5xx retry-eable; 401 raises immediately)
  - account_id propagation via RequestSpec.account_id → request.extensions['account_id'] (D-11 — Primary order GETs + Risk API)
  - Client/configure() extended with max_retries + http_client kwargs (D-15); AsyncClient UNCHANGED per D-25
  - Per-business-call request_id propagation via request.extensions (D-30)
  - Login routed through RetryTransport (D-29)
affects:
  - packages/matriz-client/src/matriz_client/_transport.py (NEW)
  - packages/matriz-client/src/matriz_client/_logging.py (NEW)
  - packages/matriz-client/src/matriz_client/__init__.py (attach _logging BEFORE other imports)
  - packages/matriz-client/src/matriz_client/_core.py (RequestSpec extended; GET + login flipped idempotent=True; mutating builders KEPT idempotent=False)
  - packages/matriz-client/src/matriz_client/client.py (Client + _request with Risk branch + Token path 401 re-auth + configure)
  - packages/matriz-client/tests/test_transport.py (NEW)
  - packages/matriz-client/tests/test_logging.py (NEW)
  - verification/snapshots/matriz-client-surface.txt
tech-stack:
  added:
    - "matriz-package mirror of higyrus Plan 4 sync transport stack: tenacity Retrying + wait_exponential_jitter + RedactingFilter"
    - "logging.getLogger('matriz_client') + NullHandler + RedactingFilter per LOG-01"
  patterns:
    - "Risk API auth_basic carve-out (D-23) — Client._request branches on spec.auth_basic; auth_basic 401 = AuthenticationError immediately (no re-auth attempt)"
    - "401 re-auth-once flow at shell tier (Token path only; D-02 + Pitfall 1)"
    - "Login routed through RetryTransport with idempotent=True per D-29"
    - "matriz D-22 redaction policy: Authorization Basic + auth_basic tuple splitting (split into auth_basic_user operational + auth_basic_password redacted)"
    - "matriz pattern isolation — NO _TOKEN_JSON_RE (higyrus), NO _CUIT_QUERY_RE (higyrus), NO _REFRESH_TOKEN_* (iol)"
    - "matriz account_id propagation (D-11) replicates higyrus Plan 4 pattern — Primary §6 order GETs (active/filled/all by accountId) + Risk §9 reads (by account_name)"
    - "matriz mutating builders quirk (Pitfall 4 / D-01 / D-24): build_new_order_request / build_replace_order_request / build_cancel_order_request use HTTP GET but explicit idempotent=False prevents retry-on-503 duplicate-order risk"
    - "matriz Phase 7 CR-03 preservation (parse_envelope_response body-consume-then-raise) + CR-05 preservation (_envelope_probe 18 sweeps) UNTOUCHED by Plan 5"
    - "matriz aio.py Phase 6 stub UNCHANGED at 103 LOC (D-25 — Phase 10 REFAC-04 territory)"
key-files:
  created:
    - packages/matriz-client/src/matriz_client/_transport.py
    - packages/matriz-client/src/matriz_client/_logging.py
    - packages/matriz-client/tests/test_transport.py
    - packages/matriz-client/tests/test_logging.py
    - .planning/phases/08-retries-backoff-structured-logging/08-05-SUMMARY.md
  modified:
    - packages/matriz-client/src/matriz_client/__init__.py
    - packages/matriz-client/src/matriz_client/_core.py
    - packages/matriz-client/src/matriz_client/client.py
    - verification/snapshots/matriz-client-surface.txt
decisions:
  - "D-23 LOCKED — matriz Risk API 401 ≠ token-stale: Client._request branches on spec.auth_basic; auth_basic 401 surfaces as AuthenticationError immediately (no _ensure_token call, no recursion). Static basic credentials cannot be re-issued by login — re-auth would just re-send the same wrong header and infinite-loop."
  - "D-24 LOCKED — matriz status='ERROR' NEVER in retry_on=: _core.parse_envelope_response raises PrimaryAPIError AFTER transport returns 200 OK. The transport's _RETRYABLE_STATUS = frozenset({408, 409, 429, *range(500, 600)}) — 200 NEVER matches. CR-03 body-consume-then-raise pattern preserved verbatim."
  - "D-25 LOCKED — matriz sync-only delivery in Phase 8: _atransport.py NOT created (Phase 10 REFAC-04 owns it alongside the async REST surface + TokenStore). aio.py LOC = 103 (Phase 6 stub) post-Plan-5 — pre-/post-Plan-5 line count unchanged. Forward reference in this SUMMARY: Phase 10 REFAC-04 will replicate the higyrus AsyncRetryTransport pattern when matriz async REST grows."
  - "D-22 LOCKED — matriz auth_basic logging redaction policy: RedactingFilter splits a (user, password) tuple in record.__dict__['auth_basic'] into auth_basic_user (operational, preserved) + auth_basic_password='***' (redacted) + removes the original auth_basic key. Plus Authorization: Basic <base64> header regex + X-Auth-Token + X-Password header regex. X-Username INTENTIONALLY preserved as operational metadata (D-22 split philosophy: username is identifier, only password is secret)."
  - "D-01 / Pitfall 4 / D-24 CRITICAL — matriz mutating builders (build_new_order_request, build_replace_order_request, build_cancel_order_request) use HTTP GET (Primary API quirk) but KEEP idempotent=False (explicit default). The RetryTransport mutation gate prevents transient-503 retry loops that would duplicate broker orders. test_retry_mutation_gate.py[matriz_new_order] GREEN (1 wire request)."
  - "D-02 401 re-auth-once — Token path: Client._request catches 401 → clears state.token → calls _ensure_token() → retries with refreshed X-Auth-Token header. 2nd 401 surfaces as AuthenticationError (Pitfall 1 prevention: re-auth happens EXACTLY once, no infinite loop)."
  - "D-11 account_id propagation — RequestSpec.account_id (str | None = None) set by Primary §6 builders (build_get_active_orders_request / build_get_filled_orders_request / build_get_all_orders_request from accountId) + Risk §9 builders (build_get_positions_request / build_get_detailed_positions_request / build_get_account_report_request from account_name). build_new_order_request also propagates account_id from the 'account' kwarg for trace correlation. Shell sets request.extensions['account_id'] ONLY when non-None."
  - "D-15 + D-16 — Client.__init__ + configure() gain max_retries=2 + http_client=None. configure() applies carry-forward semantics: max_retries change closes the cached httpx.Client to rebuild RetryTransport with the new max_attempts; http_client kwarg replaces the cached client AS-IS without auto-wrapping. AsyncClient signature UNCHANGED per D-25."
  - "D-29 — login() goes through the SAME RetryTransport as endpoint requests by using http.build_request() + http.send() instead of http.post(). Login is idempotent=True per D-03 (replay-safe) so transient 5xx retry. Preserves CR-03 body-consume in parse_login_response."
  - "D-30 — Per-call request_id (uuid4().hex) propagated via request.extensions['request_id'] for both login() and _request() in both Risk and Token branches."
  - "Phase 7 CR-03 preserved — parse_envelope_response body-consume-then-raise UNTOUCHED by Plan 5. Confirmed via packages/matriz-client/tests/test_core.py and the matriz baseline GREEN."
  - "Phase 7 CR-05 preserved — _envelope_probe 18 sweep cases unchanged. main_matriz.py NOT modified. verification/test_matriz_sweep_snapshot.py 20/20 GREEN post-Plan-5."
metrics:
  duration_minutes: 30
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 4
  test_count_baseline_matriz: 166
  test_count_after_matriz: 192
  new_matriz_unit_tests: 26
  matriz_aio_loc_before: 103
  matriz_aio_loc_after: 103
  completed_date: 2026-06-13
---

# Phase 08 Plan 05: matriz — Retries + Structured Logging + Risk API No-Reauth + Status=ERROR No-Retry

**One-liner:** matriz Plan 5 closes Wave 5 (last per-package wave) with the most complex specials of Phase 8 — sync-only `RetryTransport` (NO `_atransport.py` per D-25), `_logging.py` with D-22 `auth_basic` tuple-splitting + Authorization Basic + X-Auth-Token + X-Password redaction, shell `_request()` with Risk API branch (D-23: no 401 re-auth) + Token path D-02 re-auth-once, mutating-builder mutation gate (Pitfall 4 / D-24 duplicate-order prevention), `aio.py` UNCHANGED (Phase 6 stub deferred to Phase 10 REFAC-04). Atomic commit per D-21.

## Objective

Land the matriz delivery as a single atomic commit per D-21 (commit `273891b`): 2 new private modules (`_transport.py` sync ONLY, `_logging.py` with D-22 policy), 3 extends (`_core.py`, `client.py`, `__init__.py`), 2 new test files, 1 snapshot update (Client + configure() only — AsyncClient signature UNCHANGED per D-25), `aio.py` UNTOUCHED. Forward references to Phase 10 documented for the deferred `_atransport.py` + async REST surface.

## Tasks Completed

| # | Name | Status | Files |
|---|------|--------|-------|
| 1 | Create _transport.py (sync ONLY) + _logging.py (D-22 auth_basic) + unit tests | Done | _transport.py, _logging.py, test_transport.py, test_logging.py |
| 2 | Extend _core.py + client.py + __init__.py with Risk API branch + 401 re-auth-once + account_id; update snapshot | Done | _core.py, client.py, __init__.py, snapshot |

Single atomic commit per D-21: **`273891b`**.

## LOC Delta

| File | Before | After | Delta |
|------|--------|-------|-------|
| `_transport.py` | 0 → 225 | +225 (NEW; sync ONLY; mirrors higyrus Plan 4 with `_LOGGER_NAME='matriz_client'`) |
| `_atransport.py` | N/A | N/A | NOT CREATED — Phase 10 REFAC-04 territory per D-25 |
| `_logging.py` | 0 → 173 | +173 (NEW; D-22 auth_basic tuple split + X-Auth-Token + X-Password + Authorization Basic regex; X-Username preserved per D-22) |
| `_core.py` | 729 → 845 | +116 (RequestSpec gains `idempotent` + `endpoint_name` + `account_id`; login + 11 GET builders flipped idempotent=True; 3 mutating builders KEPT idempotent=False; 6 builders gain account_id propagation) |
| `client.py` | 604 → 737 | +133 (Client.__init__ + slots gain `max_retries`; _ensure_http_client wraps RetryTransport; login() routed through transport with extensions; _request() with Risk branch + Token D-02 re-auth-once; configure() gains 2 kwargs with carry-forward semantics) |
| `aio.py` | 103 → 103 | **0 (UNCHANGED per D-25 — Phase 6 stub preserved for Phase 10 REFAC-04)** |
| `__init__.py` | 164 → 176 | +12 (_logging.attach() BEFORE other imports + del cleanup; noqa: E402 on subsequent from-imports) |
| `test_transport.py` | 0 → 315 | +315 (NEW; 13 tests including Pitfall 4 critical `test_new_order_POST_does_NOT_retry_on_503` + Risk API auth_basic 401/503 branches + account_id propagation) |
| `test_logging.py` | 0 → 218 | +218 (NEW; 13 tests including D-22 `test_redact_auth_basic_tuple_in_extra` + Authorization Basic header + X-Auth-Token + X-Password redaction + X-Username preserved + pattern isolation guard) |
| `matriz-client-surface.txt` | 73 → 73 | 2 lines modified (Client + configure each gain 2 kwargs; **AsyncClient line UNCHANGED per D-25**) |

Total commit: **+1223 / -28 lines** across 8 files.

## Cross-cutting Guard Test Status

| Guard | Status before Plan 5 | Status after Plan 5 |
|-------|----------------------|---------------------|
| `test_retry_mutation_gate.py::test_mutating_call_never_retries_against_503[matriz_client-new_order]` | RED | **GREEN** (1 wire request — duplicate-order risk MITIGATED — Pitfall 4 CRITICAL) |
| `test_retry_mutation_gate.py::test_idempotent_get_retries_on_503[matriz_client-get_segments]` | RED | **GREEN** (3 wire requests per D-15+D-19) |
| `test_retry_401_reauth.py::test_401_then_login_then_200_triggers_exactly_one_reauth[matriz_client]` | RED | **GREEN** (3 wire requests: STALE-TOKEN → login → FRESH-TOKEN) |
| `test_retry_401_reauth.py::test_401_then_login_then_401_raises_auth_error[matriz_client]` | RED | **GREEN** (3 wire requests + AuthenticationError raised — exactly 1 re-auth attempt per D-02) |
| `test_retry_401_reauth.py::test_matriz_risk_api_401_does_not_reauth` | RED | **GREEN** (1 wire request + AuthenticationError — D-23 NO re-auth for auth_basic path) |
| `test_logging_no_token_leak.py::test_token_literal_never_appears_in_log_records[matriz_client]` | trivially GREEN (no logs) | **GREEN** (token never leaked) |
| `test_logging_no_token_leak.py::test_matriz_auth_basic_password_not_logged` | RED | **GREEN** (D-22 auth_basic tuple splitting protects password) |
| `test_logging_root_unchanged.py::test_importing_packages_does_not_modify_logging_root` | GREEN | **GREEN** (continues with matriz `_logging.attach` landed) |
| `test_async_cancellation.py::test_cancellation_propagates_during_retry_backoff[matriz_client]` | SKIP (Phase 7 D-11) | **SKIP** (D-25 — `aio.py` REST stub until Phase 10 REFAC-04) |
| `test_sync_async_isolation.py[matriz_client sync]` | GREEN | **GREEN** (sync token isolation preserved) |
| `test_sync_async_isolation.py[matriz_client async]` | SKIP (Phase 7 D-11) | **SKIP** (D-25 — same reason text "matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore" verbatim) |
| `test_public_surface.py::test_public_surface_matches_snapshot[matriz_client]` | GREEN baseline | **GREEN** (snapshot updated with 2 new kwargs on Client + configure; AsyncClient UNCHANGED per D-25) |
| `test_phase06_nyquist_gaps.py::test_snapshot_regen_is_idempotent` | GREEN | **GREEN** (post-commit; regen produces identical snapshot) |
| `test_matriz_sweep_snapshot.py` (Phase 7 CR-05 — 18 cases + sentinel checks) | GREEN | **GREEN** (20/20 — Phase 7 CR-05 preserved verbatim) |
| `packages/matriz-client/tests/test_core.py::test_parse_envelope_consumes_body_before_raise` | GREEN | **GREEN** (Phase 7 CR-03 preserved verbatim) |

All cross-cutting Wave 1 guard tests for the 4 packages now GREEN — **Wave 5 closure**.

## Snapshot Diff

```diff
-Client : class : (*, base_url: 'str | None' = None, username: 'str | None' = None, password: 'str | None' = None, token: 'str | None' = None, token_expires_at: 'float | None' = None) -> 'None'
+Client : class : (*, base_url: 'str | None' = None, username: 'str | None' = None, password: 'str | None' = None, token: 'str | None' = None, token_expires_at: 'float | None' = None, max_retries: 'int' = 2, http_client: 'httpx.Client | None' = None) -> 'None'

-configure : function : (*, base_url: 'str | None' = None, username: 'str | None' = None, password: 'str | None' = None, token: 'str | None' = None, token_expires_at: 'float | None' = None) -> 'None'
+configure : function : (*, base_url: 'str | None' = None, username: 'str | None' = None, password: 'str | None' = None, token: 'str | None' = None, token_expires_at: 'float | None' = None, max_retries: 'int | None' = None, http_client: 'httpx.Client | None' = None) -> 'None'
```

**`AsyncClient` line UNCHANGED** per D-25 — Phase 10 REFAC-04 grows the async REST surface + signature.

## Risk API Carve-Out (D-23) — Implementation Evidence

The shell `Client._request` branches on `spec.auth_basic`:

- **Risk path** (`spec.auth_basic is not None` — Risk §9 GET positions / detailedPosition / accountReport):
  1. Build request without `X-Auth-Token` headers
  2. Set extensions (idempotent, request_id, endpoint_name, account_id, auth_basic for D-22 redaction)
  3. `http.send(req, auth=httpx.BasicAuth(*spec.auth_basic))`
  4. On 401 → raise `AuthenticationError` **immediately** (NO `_ensure_token()` call, NO recursion)
  5. RetryTransport still applies for transient 5xx (idempotent=True for Risk reads)

- **Token path** (X-Auth-Token):
  1. `_ensure_token()` — login if missing/expired
  2. Build request with `X-Auth-Token: <token>` header
  3. Send; on 401 → clear `state.token` → re-`_ensure_token()` → retry **once** with refreshed token
  4. 2nd 401 → raise `AuthenticationError` (Pitfall 1: re-auth happens **exactly once**)

## Mutating Order Builders — Pitfall 4 / D-24 Evidence

`build_new_order_request`, `build_replace_order_request`, `build_cancel_order_request` use HTTP **GET** (Primary API quirk) but explicit `idempotent=False`. The `RetryTransport.handle_request` check is method-agnostic — it reads `request.extensions["idempotent"]` set by the shell from `RequestSpec.idempotent`. Non-idempotent requests pass through with NO retry loop, preventing duplicate-broker-orders on transient 503.

```python
# packages/matriz-client/src/matriz_client/_core.py — build_new_order_request
return RequestSpec(
    method="GET",
    path="/rest/order/newSingleOrder",
    params=params,
    idempotent=False,  # CRITICAL — Pitfall 4 / D-01 / D-24
    endpoint_name="new_order",
    account_id=account,
)
```

`test_retry_mutation_gate.py::test_mutating_call_never_retries_against_503[matriz_client-new_order-kwargs0]` GREEN — 1 wire request emitted against 503,503 mocks.

## D-22 auth_basic Redaction Evidence

The matriz `RedactingFilter.filter()` has special handling BEFORE the generic `record.__dict__` scan:

```python
if "auth_basic" in record.__dict__:
    split = _redact_auth_basic_tuple(record.__dict__["auth_basic"])
    if split is not None:
        del record.__dict__["auth_basic"]
        record.__dict__.update(split)
# → record now has `auth_basic_user` (operational, preserved) +
#   `auth_basic_password='***'` (redacted) + original `auth_basic` removed
```

The split philosophy (D-22): the **username** is operational metadata for correlation (preserved); only the **password** is the secret. Same philosophy applies to the `X-Username` / `X-Password` header pair — X-Username regex defined for symmetry but NOT applied in `_redact()`; X-Password regex applied.

Defensive: malformed `auth_basic` values (non-tuple, wrong arity, non-string members) are left untouched without crash. `test_redact_auth_basic_tuple_malformed_does_not_crash` verifies.

## Phase 7 CR-03 + CR-05 Preservation Evidence

**CR-03** (`_core.parse_envelope_response` body-consume-then-raise):
- Plan 5 surgical scope: ADDED fields to `RequestSpec` (idempotent, endpoint_name, account_id) + flipped builders' RequestSpec construction kwargs. The `parse_envelope_response` body is verbatim Phase 7.
- `packages/matriz-client/tests/test_core.py::test_parse_envelope_consumes_body_before_raise` GREEN post-Plan-5.

**CR-05** (`_envelope_probe` 18-case sweep in `main_matriz.py`):
- Plan 5 does NOT touch `main_matriz.py`.
- `verification/test_matriz_sweep_snapshot.py` 20/20 GREEN post-Plan-5 (18 envelope-shape probes + 2 sanity checks).

## D-25 Forward Reference — Phase 10 REFAC-04

This Plan 5 delivers **sync-only**. The deferred items for Phase 10 REFAC-04 (after the TokenStore research spike):

- `packages/matriz-client/src/matriz_client/_atransport.py` — async mirror of `_transport.RetryTransport` (will replicate the higyrus Plan 4 `AsyncRetryTransport` template).
- `packages/matriz-client/src/matriz_client/aio.py` — full async REST surface (Phase 10 grows the 103-LOC Phase 6 stub).
- `verification/test_async_cancellation.py[matriz_client]` — currently SKIP with reason "matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore"; will turn GREEN when async surface lands.
- `verification/test_sync_async_isolation.py[matriz_client async]` — currently SKIP same reason; will activate when async surface lands.
- `AsyncClient.__init__` snapshot signature — currently Phase 6 stub `(*, base_url, username, password, token, token_expires_at)`; will gain `max_retries=2 + http_client=httpx.AsyncClient | None=None` in Phase 10.

The matriz `_request()` Token-path 401 re-auth pattern in this plan is sync-only; the async mirror (with `asyncio.Lock` for `state.token` mutation + double-checked locking) lands in Phase 10 as part of the shared `TokenStore` primitive.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — login() routed through transport]**

- **Found during:** Task 2 verification — the original `Client.login()` used `http.post(...)` directly, bypassing the transport's mutation gate and extensions.
- **Issue:** Per D-29, login must go through the same RetryTransport as endpoint requests with `idempotent=True` from `build_login_request`. The direct `http.post()` call would not propagate `request.extensions["idempotent"]` and would skip the structured WARNING log on retry.
- **Fix:** Replaced the direct `http.post()` with `http.build_request() + http.send()` after populating `request.extensions["idempotent"]/["request_id"]/["endpoint_name"]`. Mirrors the higyrus `_send_auth_request` pattern from Plan 4.
- **Files modified:** `packages/matriz-client/src/matriz_client/client.py` (`login()` method)
- **Commit:** `273891b`

**2. [Rule 1 — AuthenticationError surfaced on 2nd 401 in Token path]**

- **Found during:** Task 2 — running `verification/test_retry_401_reauth.py::test_401_then_login_then_401_raises_auth_error[matriz_client]` first time.
- **Issue:** matriz `_core.raise_for_response` uses `resp.raise_for_status()` which raises `httpx.HTTPStatusError` (not typed `AuthenticationError`). After re-auth, if the 2nd response is also 401, the parser layer would surface `httpx.HTTPStatusError`, but the cross-cutting guard test expects `pkg.AuthenticationError`.
- **Fix:** Added explicit `if resp.status_code == 401: raise AuthenticationError(...)` after the re-auth retry in `_request()`. Mirrors the higyrus Plan 4 pattern (where `HigyrusAuthError` is raised typedly by `raise_for_response` itself).
- **Files modified:** `packages/matriz-client/src/matriz_client/client.py` (`_request()` Token path 2nd-401 handling)
- **Commit:** `273891b`

**3. [Rule 1 — AuthenticationError surfaced on auth_basic 401 in Risk path]**

- **Found during:** Task 2 — running `verification/test_retry_401_reauth.py::test_matriz_risk_api_401_does_not_reauth` first time.
- **Issue:** Same root cause as #2 — `resp.raise_for_status()` raises `httpx.HTTPStatusError` for 401, but D-23 requires `AuthenticationError` surfaced immediately for the auth_basic path (no re-auth).
- **Fix:** Added explicit `if resp.status_code == 401: raise AuthenticationError(...)` after `http.send()` in the Risk branch BEFORE returning the response.
- **Files modified:** `packages/matriz-client/src/matriz_client/client.py` (`_request()` Risk branch 401 handling)
- **Commit:** `273891b`

No Rule 4 (architectural) decisions required. No Rule 2 (security gaps) — D-22 `auth_basic` redaction + X-Auth-Token + X-Password + Authorization Basic were all planned in Task 1.

## Authentication Gates

None — all verification was offline via `pytest-httpx` mocks.

## Known Stubs / Threat Flags

None added by this plan. The `_request()` 401 re-auth-once flow is in-process with no caching, no disk persistence, and no out-of-band signal — clean per the threat register (T-8-02-MATZ-PRIMARY mitigation in place: bounded re-auth at exactly 1 retry; T-8-02-MATZ-RISK in place: D-23 skip-re-auth verified by `test_matriz_risk_api_401_does_not_reauth`). T-8-04-MATZ-TOKEN (X-Auth-Token leak), T-8-04-MATZ-BASIC (auth_basic password leak via tuple or Authorization Basic header), T-8-04-MATZ-LOGIN (X-Password header leak) all mitigated by the RedactingFilter patterns; verified by `test_redact_x_auth_token_header`, `test_redact_authorization_basic_header`, `test_redact_x_password_header_preserves_x_username`, `test_redact_auth_basic_tuple_in_extra` in `test_logging.py`. T-8-MATZ-D24-PRESERVE (status=ERROR retry regression) mitigated by surgical scope — `_core.parse_envelope_response` body untouched, `_RETRYABLE_STATUS = frozenset({408, 409, 429, *range(500, 600)})` excludes 200, all matriz sweep tests GREEN. T-8-CR03-PRESERVE + T-8-CR05-PRESERVE + T-8-D25-AIO-DRIFT all verified GREEN (CR-03 preserved, CR-05 preserved, aio.py LOC = 103 = Phase 6 baseline).

## Self-Check: PASSED

- [x] `packages/matriz-client/src/matriz_client/_transport.py` — FOUND, 225 LOC, `class RetryTransport`, `_LOGGER_NAME = "matriz_client"`
- [x] `packages/matriz-client/src/matriz_client/_atransport.py` — ABSENT (D-25 — Phase 10 REFAC-04 territory)
- [x] `packages/matriz-client/src/matriz_client/_logging.py` — FOUND, 173 LOC, `class RedactingFilter`, `_AUTH_BASIC_RE` + `_X_AUTH_TOKEN_RE` + `_X_PASSWORD_RE` + `_redact_auth_basic_tuple` helper (no `_TOKEN_JSON_RE` / `_CUIT_QUERY_RE` / `_REFRESH_TOKEN_*` — pattern isolation guard verifies)
- [x] `packages/matriz-client/tests/test_transport.py` — FOUND, 13 tests including `test_new_order_POST_does_NOT_retry_on_503` (Pitfall 4 CRITICAL) + Risk API auth_basic 401/503 branches
- [x] `packages/matriz-client/tests/test_logging.py` — FOUND, 13 tests including D-22 `test_redact_auth_basic_tuple_in_extra` + `test_redact_authorization_basic_header` + `test_redact_x_password_header_preserves_x_username` + pattern isolation guard
- [x] `verification/snapshots/matriz-client-surface.txt` updated — 2 new kwargs in Client + configure(); `AsyncClient.__init__` line UNCHANGED per D-25
- [x] Commit `273891b` exists on `main` (`git log --oneline 273891b` confirms)
- [x] 192/192 matriz-client tests GREEN (166 baseline + 26 new); 141/141 higyrus-client + 114/114 iol-client + 121/121 ámbito-client tests unchanged
- [x] ruff + ruff format + mypy strict GREEN; lint-imports contracts kept (4/4)
- [x] `wc -l packages/matriz-client/src/matriz_client/aio.py` = `103` (Phase 6 stub UNCHANGED per D-25)
- [x] `packages/matriz-client/src/matriz_client/_atransport.py` does NOT exist
- [x] `test_phase06_nyquist_gaps.py::test_snapshot_regen_is_idempotent` GREEN post-commit (regen produces identical snapshot)
- [x] `test_matriz_sweep_snapshot.py` 20/20 GREEN (Phase 7 CR-05 preserved)
- [x] `test_parse_envelope_consumes_body_before_raise` GREEN (Phase 7 CR-03 preserved)
- [x] All cross-cutting Wave 1 guard tests GREEN for the 4 packages (Wave 5 closure)

## Outcome

**Phase 8 Plan 5 closes Wave 5 (last per-package wave).** Wave 6 (Plan 6) runs the full CI green-gate consolidation. With the matriz delivery landed:

- All 4 packages (ámbito, iol, higyrus, matriz) now ship `RetryTransport` + `RedactingFilter` with package-specific tweaks
- All cross-cutting Wave 1 guard tests GREEN (mutation gate, 401 re-auth, async cancellation where applicable, sync/async isolation, public surface snapshot, root logger unchanged, token literal not in logs)
- D-25 honored: matriz `aio.py` stays at Phase 6 stub (103 LOC); `_atransport.py` deferred to Phase 10 REFAC-04
- D-23 + D-24 carve-outs implemented and guarded (Risk API no-reauth; status=ERROR no-retry)
- Phase 7 CR-03 (`parse_envelope_response` body-consume) + CR-05 (`_envelope_probe` sweep) preserved verbatim
- Pitfall 4 (matriz `new_order` POST against 503) mitigated by explicit `idempotent=False` on mutating builders + transport mutation gate
