---
phase: 08-retries-backoff-structured-logging
plan: 04
subsystem: higyrus-client
tags: [phase-08, higyrus, atomic-commit, rely, log, account-id-propagation, json-password-redaction]
requires: [phase-07 _core.py extraction, phase-08-01 cross-cutting scaffolding, phase-08-02 ámbito canary, phase-08-03 iol auth pattern]
provides:
  - higyrus_client._transport.RetryTransport (sync; mirrors iol Plan 3 with higyrus_client logger)
  - higyrus_client._atransport.AsyncRetryTransport (async mirror)
  - higyrus_client._logging.RedactingFilter + attach() (Bearer/X-Auth-Token/password URL+JSON + token JSON + cuit URL query)
  - 401 re-auth-once flow in Client._request + AsyncClient._request (D-02 / RELY-04)
  - Login idempotent=True per D-03 (transient 5xx retry-eable; 401 raises immediately)
  - account_id propagation via RequestSpec.account_id -> request.extensions['account_id'] (D-11)
  - Client/AsyncClient/configure() extended with max_retries + http_client kwargs (D-15)
  - Per-business-call request_id propagation via request.extensions (D-30)
  - Auth-flow shell helper _send_auth_request routing login through RetryTransport (D-29)
affects:
  - packages/higyrus-client/src/higyrus_client/_transport.py (NEW)
  - packages/higyrus-client/src/higyrus_client/_atransport.py (NEW)
  - packages/higyrus-client/src/higyrus_client/_logging.py (NEW)
  - packages/higyrus-client/src/higyrus_client/__init__.py (attach _logging BEFORE other imports)
  - packages/higyrus-client/src/higyrus_client/_core.py (RequestSpec extended; 5 builders flipped idempotent=True)
  - packages/higyrus-client/src/higyrus_client/client.py (Client + _request with 401 re-auth + _send_auth_request + configure)
  - packages/higyrus-client/src/higyrus_client/aio.py (AsyncClient + async _request with 401 re-auth + _send_auth_request + configure)
  - packages/higyrus-client/tests/test_transport.py (NEW)
  - packages/higyrus-client/tests/test_logging.py (NEW)
  - packages/higyrus-client/tests/test_client.py (test_request_propaga_auth_error + test_login_429 + test_login_500 aligned to D-02/D-03)
  - packages/higyrus-client/tests/test_async_client.py (async mirror of the above)
  - verification/snapshots/higyrus-client-surface.txt
tech-stack:
  added:
    - "higyrus-package mirror of iol Plan 3 transport stack: tenacity Retrying / AsyncRetrying + wait_exponential_jitter + RedactingFilter"
    - "logging.getLogger('higyrus_client') + NullHandler + RedactingFilter per LOG-01"
  patterns:
    - "401 re-auth-once flow at shell tier (NOT in transport retry_on=) per D-02 + Pitfall 1"
    - "Auth-flow (login) routed through RetryTransport with idempotent=True per D-29"
    - "Async double-checked locking on _client_lock + state.token_lock preserved across new transport wiring"
    - "Higyrus JSON password redaction (login body) + JSON token redaction (login response) + cuit URL query redaction (PII)"
    - "account_id propagation pattern (D-11) — RequestSpec.account_id -> request.extensions['account_id'] -> log record extra (conditional; non-None only)"
    - "URL-encoding quirk (Phase 7) preserved — _core.py only adds fields to RequestSpec; url_pre_encoded untouched"
key-files:
  created:
    - packages/higyrus-client/src/higyrus_client/_transport.py
    - packages/higyrus-client/src/higyrus_client/_atransport.py
    - packages/higyrus-client/src/higyrus_client/_logging.py
    - packages/higyrus-client/tests/test_transport.py
    - packages/higyrus-client/tests/test_logging.py
    - .planning/phases/08-retries-backoff-structured-logging/08-04-SUMMARY.md
  modified:
    - packages/higyrus-client/src/higyrus_client/__init__.py
    - packages/higyrus-client/src/higyrus_client/_core.py
    - packages/higyrus-client/src/higyrus_client/client.py
    - packages/higyrus-client/src/higyrus_client/aio.py
    - packages/higyrus-client/tests/test_client.py
    - packages/higyrus-client/tests/test_async_client.py
    - verification/snapshots/higyrus-client-surface.txt
decisions:
  - "D-02 401 re-auth-once at shell tier — Client._request and AsyncClient._request catch HigyrusAuthError, clear state.token, call _ensure_token(), retry once with refreshed Authorization header"
  - "D-03 build_login_request marked idempotent=True (login is replay-safe — fresh Bearer replaces prior; 5xx retry-eable, 401 NEVER retry)"
  - "D-11 account_id propagation pattern established — RequestSpec.account_id (str | None = None) set by GET builders that take id_cuenta; shell sets request.extensions['account_id'] ONLY when non-None (no leak when caller didn't pass id_cuenta)"
  - "D-29 auth-flow routes through RetryTransport via _send_auth_request helper — preserves D-21 atomic commit + D-07 retry_on= locked set"
  - "D-10 Higyrus JSON password redaction (login body) + JSON token redaction (login response) + cuit URL query redaction (PII) — pattern isolation from iol (NO _REFRESH_TOKEN regexes)"
  - "D-15 + D-16 minimal public API extension — max_retries=2 + http_client=None on Client/AsyncClient/configure(); higyrus configure() carry-forward pattern (new Client instance) preserves D-15 transport rebuild"
  - "D-19 max_retries=N → max_attempts=N+1 (anthropic/openai SDK semantics)"
  - "URL-encoding quirk preservation (Phase 7 D-XX) — _core.py adds endpoint_name + account_id + idempotent fields to RequestSpec; url_pre_encoded UNTOUCHED. Shell _request() preserves url_pre_encoded branch in httpx build_request."
  - "Test alignment per D-02 — test_request_propaga_auth_error (sync + async) updated to queue full 401 -> login -> 401 chain; test_login_500 + test_login_429 updated to queue 3 mocks for D-03 idempotent=True semantic"
metrics:
  duration_minutes: 25
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 7
  test_count_baseline_higyrus: 118
  test_count_after_higyrus: 141
  new_higyrus_unit_tests: 23
  completed_date: 2026-06-13
---

# Phase 08 Plan 04: higyrus — Retries + Structured Logging + 401 Re-auth + account_id Propagation

**One-liner:** higyrus Plan 4 delivers the auth-paquete pattern with the **account_id propagation extra** — mirrors iol's `RetryTransport`+`AsyncRetryTransport`+`RedactingFilter` (Plan 3), adds the 401 re-auth-once flow at the shell tier (D-02), introduces conditional `account_id` extension via `RequestSpec.account_id` (D-11), and covers Higyrus JSON password (login body) + JSON token (login response) + cuit URL query PII redaction. URL-encoding quirk (Phase 7) preserved verbatim — Plan 4 only ADDS fields to RequestSpec, never touches `url_pre_encoded`.

## Objective

Land the higyrus delivery as a single atomic commit per D-21: 3 new private modules (`_transport.py`, `_atransport.py`, `_logging.py`) mirroring iol with the Higyrus-specific extras, 4 extends (`_core.py`, `client.py`, `aio.py`, `__init__.py`), 2 new test files, 1 snapshot update, and 3 existing tests adjusted to align with the new D-02 (401 re-auth) + D-03 (login idempotent=True) semantics. higyrus is the first paquete with `account_id` propagation, so this plan establishes Pattern D-11 (RESEARCH §Assumptions Log A8) that Plan 5 (matriz) will replicate.

## Tasks Completed

| # | Name | Status | Files |
|---|------|--------|-------|
| 1 | Create _transport.py + _atransport.py + _logging.py + unit tests | Done | _transport.py, _atransport.py, _logging.py, test_transport.py, test_logging.py |
| 2 | Extend _core.py + client.py + aio.py + __init__.py + snapshot | Done | _core.py, client.py, aio.py, __init__.py, snapshot, test alignments |

Single atomic commit per D-21: **`214332f`**.

## LOC Delta

| File | Before | After | Delta |
|------|--------|-------|-------|
| `_transport.py` | 0 | 205 | +205 (NEW; mirrors iol with higyrus logger) |
| `_atransport.py` | 0 | 132 | +132 (NEW) |
| `_logging.py` | 0 | 116 | +116 (NEW; JSON password + JSON token + cuit query regex vs Plan 3) |
| `_core.py` | 438 | 496 | +58 (RequestSpec extended with idempotent+endpoint_name+account_id; 5 builders flipped) |
| `client.py` | 445 | 562 | +117 (RetryTransport wiring, _send_auth_request, 401 re-auth pattern, account_id propagation, 2 kwargs) |
| `aio.py` | 486 | 588 | +102 (async mirror with double-checked locking preservation) |
| `__init__.py` | 97 | 105 | +8 (_logging.attach BEFORE other imports + del cleanup) |
| `test_transport.py` | 0 | 260 | +260 (NEW; 11 tests including 3 account_id-specific) |
| `test_logging.py` | 0 | 191 | +191 (NEW; 12 tests including 4 higyrus-specific + pattern isolation guard) |
| `test_client.py` | 432 | 463 | +31 (401 re-auth flow simulated; login 5xx/429 retry mocks) |
| `test_async_client.py` | 339 | 357 | +18 (async mirror) |
| `higyrus-client-surface.txt` | 38 | 38 | 3 lines modified (Client/AsyncClient/configure +2 kwargs each) |

Total commit: **+1299 / -63 lines** across 12 files.

## Cross-cutting Guard Test Status

| Guard | Status before Plan 4 | Status after Plan 4 |
|-------|----------------------|---------------------|
| `test_retry_mutation_gate.py::test_idempotent_get_retries_on_503[higyrus_client-get_listado_cuentas-kwargs1]` | RED | **GREEN** |
| `test_retry_401_reauth.py::test_401_then_login_then_200_triggers_exactly_one_reauth[higyrus_client]` | RED | **GREEN** (3 wire requests + FRESH-TOKEN in last Authorization) |
| `test_retry_401_reauth.py::test_401_then_login_then_401_raises_auth_error[higyrus_client]` | RED | **GREEN** (3 wire requests + HigyrusAuthError raised, no infinite loop) |
| `test_logging_no_token_leak.py::test_token_literal_never_appears_in_log_records[higyrus_client]` | trivially GREEN (no logs emitted) | **GREEN** (SECRET-LITERAL-12345 not in any record; JSON password + token redacted) |
| `test_logging_root_unchanged.py::test_importing_packages_does_not_modify_logging_root` | GREEN | **GREEN** (continues with higyrus's _logging.attach landed) |
| `test_async_cancellation.py::test_cancellation_propagates_during_retry_backoff[higyrus_client]` | RED | **GREEN** (TimeoutError raised < 1.0s) |
| `test_sync_async_isolation.py[higyrus_client]` | GREEN | **GREEN** (URL-encoding quirk preserved — Phase 7 baseline untouched) |
| `test_public_surface.py::test_public_surface_matches_snapshot[higyrus_client]` | GREEN baseline | **GREEN** (snapshot updated with 2 new kwargs) |
| `test_phase06_nyquist_gaps.py::test_snapshot_regen_is_idempotent` | GREEN | **GREEN** (post-commit; regen produces identical snapshot) |

Matriz parametrize branches remain RED awaiting Plan 5 — by design per Plan 8-01.

## Snapshot Diff

```diff
-AsyncClient : class : (*, base_url: 'str | None' = None, client_id: 'str | None' = None, username: 'str | None' = None, password: 'str | None' = None, token: 'str | None' = None, token_expires_at: 'float | None' = None) -> 'None'
-Client : class : (*, base_url: 'str | None' = None, client_id: 'str | None' = None, username: 'str | None' = None, password: 'str | None' = None, token: 'str | None' = None, token_expires_at: 'float | None' = None) -> 'None'
+AsyncClient : class : (..., max_retries: 'int' = 2, http_client: 'httpx.AsyncClient | None' = None) -> 'None'
+Client : class : (..., max_retries: 'int' = 2, http_client: 'httpx.Client | None' = None) -> 'None'

-configure : function : (..., token_expires_at: 'float | None' = None) -> 'None'
+configure : function : (..., token_expires_at: 'float | None' = None, max_retries: 'int | None' = None, http_client: 'httpx.Client | None' = None) -> 'None'
```

## URL-encoding Quirk Preservation Evidence

The Phase 7 D-XX `url_pre_encoded: bool = False` field in `RequestSpec` (encodes the Higyrus IIS "rechaza %2F" quirk) is preserved by surgical scope:

- `_core.py` RequestSpec dataclass: Plan 4 ONLY ADDS fields (`idempotent`, `endpoint_name`, `account_id`) — `url_pre_encoded` and `_encode_query()` helper UNTOUCHED.
- Sync `client.py._request()`: preserves the `spec.url_pre_encoded` branch — when True, `httpx.build_request(params=None)` is called so the path's pre-encoded query is forwarded verbatim.
- Async `aio.py._request()`: same — `spec.url_pre_encoded` branch preserved in the async mirror.
- Existing higyrus tests covering URL-encoding (`test_get_movimientos_serializa_fechas_dd_mm_yyyy`, `test_build_get_movimientos_request_preserves_slash_in_query`, `test_build_get_listado_cuentas_estado_with_slash_preserves_literal`, etc.) all GREEN post-Plan 4 — empirical quirk-preservation evidence (118 baseline tests + 23 new = 141 tests, 0 failures, 0 regressions).
- `test_sync_async_isolation.py[higyrus_client]` (Phase 7 cross-leak sentinel) GREEN — sync/async surface state separation preserved.

## account_id Propagation Pattern (D-11)

This plan establishes the pattern that Plan 5 (matriz) will replicate:

1. `RequestSpec` field: `account_id: str | None = None` (additive; default None means no propagation).
2. Builders that accept `id_cuenta` (movimientos, posicion_valuada, posiciones) set `account_id=id_cuenta` in the returned RequestSpec.
3. Builders that take a LIST of accounts (`listadoCuentas`) do NOT set account_id — multi-account log correlation is out of scope (single-account-scoped per D-11).
4. Shell `_request()` (sync + async): sets `request.extensions["account_id"]` ONLY when `spec.account_id is not None` — no leak when caller didn't pass id_cuenta.
5. `RetryTransport` / `AsyncRetryTransport`: reads `request.extensions.get("account_id")` and adds it to the structured log record's `extra={"account_id": ...}` ONLY when truthy. The WARNING/ERROR records emitted during retry attempts include account_id when set.
6. `RedactingFilter`: account_id is operational metadata (NOT PII) and is **NOT** redacted. Guard test `test_account_id_not_redacted` in `test_logging.py` verifies this.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test alignment] `test_request_propaga_auth_error` (sync + async) updated for D-02 behavior**

- **Found during:** Task 2 — running `uv run pytest packages/higyrus-client/ -v` after wiring 401 re-auth flow.
- **Issue:** The legacy tests queued ONE 401 response and asserted `HigyrusAuthError`. Under the new D-02 401 re-auth-once flow, the shell calls `_ensure_token()` (login attempt), which has no mock queued and raises `httpx.TimeoutException`.
- **Fix:** Updated both tests to queue the full 401 -> login(200) -> 401 chain to validate the canonical "401 re-auth then second-401 raises HigyrusAuthError without infinite loop" behavior. Pre-existing test intent ("a 401 surfaces as HigyrusAuthError") preserved; the test now exercises the FULL re-auth contract instead of the pre-Phase-8 single-shot semantic. Mirrors the iol Plan 3 fix verbatim (different exception class).
- **Files modified:** `packages/higyrus-client/tests/test_client.py`, `packages/higyrus-client/tests/test_async_client.py`
- **Commit:** `214332f`

**2. [Rule 1 - Test alignment] `test_login_500_levanta_api_error` + `test_login_429_levanta_rate_limit` (sync + async) updated for D-03 idempotent=True semantics**

- **Found during:** Task 2 — running `uv run pytest packages/higyrus-client/ -v`.
- **Issue:** The Phase 7 tests queued ONE 5xx/429 response on the login URL and asserted the typed exception. Under D-03 (`build_login_request` marked `idempotent=True`), the RetryTransport now retries 5xx/429 up to `max_attempts=3` (default `max_retries=2`), so a single mock is consumed by the first attempt and subsequent retries hit `httpx.TimeoutException`.
- **Fix:** Updated both 500 tests (sync + async) and the 429 test to queue 3 × mocked responses so the retry loop exhausts and the final response surfaces as the typed exception (D-05 last-response semantics). Documentation in docstrings cites D-03 + D-05 + D-15+D-19 explicitly.
- **Files modified:** `packages/higyrus-client/tests/test_client.py`, `packages/higyrus-client/tests/test_async_client.py`
- **Commit:** `214332f`

No Rule 4 (architectural) decisions required. No Rule 2 (security gaps) — the Higyrus JSON password redaction + JSON token redaction + cuit query redaction were all planned in Task 1.

## Authentication Gates

None — all verification was offline via `pytest-httpx` mocks.

## Known Stubs / Threat Flags

None added by this plan. The `_request()` 401 re-auth-once flow uses an in-process re-auth attempt with no caching, no disk persistence, and no out-of-band signal — clean per the threat register (T-8-02-HIGY mitigation in place: bounded re-auth at exactly 1 retry). T-8-04-HIGY (JSON password leak), T-8-04b-HIGY (JSON token leak), T-8-04c-HIGY (cuit query leak) all mitigated by the RedactingFilter patterns; verified by `test_redact_password_json_login_body`, `test_redact_token_json_login_response`, `test_redact_cuit_query` in `test_logging.py`. T-8-URL-ENC-PRESERVE (regression risk) mitigated by surgical scope — all existing higyrus tests GREEN.

## Self-Check: PASSED

- [x] `packages/higyrus-client/src/higyrus_client/_transport.py` — FOUND, 205 LOC, `class RetryTransport`, `_LOGGER_NAME = "higyrus_client"`
- [x] `packages/higyrus-client/src/higyrus_client/_atransport.py` — FOUND, 132 LOC, `class AsyncRetryTransport`
- [x] `packages/higyrus-client/src/higyrus_client/_logging.py` — FOUND, 116 LOC, `class RedactingFilter`, `_PASSWORD_JSON_RE` + `_TOKEN_JSON_RE` + `_CUIT_QUERY_RE` regexes (NO `_REFRESH_TOKEN_*` — pattern isolation guard verifies)
- [x] `packages/higyrus-client/tests/test_transport.py` — FOUND, 11 tests including 3 account_id-specific + login-as-idempotent
- [x] `packages/higyrus-client/tests/test_logging.py` — FOUND, 12 tests including 4 higyrus-specific (JSON password, JSON token, cuit query, account_id NOT redacted) + pattern isolation guard
- [x] `verification/snapshots/higyrus-client-surface.txt` updated — 2 new kwargs in Client/AsyncClient/configure() signatures
- [x] Commit `214332f` exists on `main` (`git log --oneline 214332f` confirms)
- [x] 141/141 higyrus-client tests GREEN (118 baseline + 23 new); 114/114 iol-client + 121/121 ámbito-client tests unchanged; matriz tests unchanged
- [x] ruff + ruff format + mypy strict GREEN; lint-imports contracts kept (`higyrus_client._core does not depend on transport modules` — verified)
- [x] URL-encoding quirk preserved: existing higyrus tests covering `dd/mm/yyyy` + `safe="/"` + `doseq=True` all GREEN
- [x] test_phase06_nyquist_gaps.py::test_snapshot_regen_is_idempotent GREEN post-commit (regen produces identical snapshot)

## Outcome

higyrus Plan 4 establishes the **account_id propagation pattern (D-11)** — Plan 5 (matriz) will replicate this template with its per-package tweaks (auth_basic Risk API + status=ERROR no-retry per D-23/D-24). The Higyrus-specific RedactingFilter pattern set (JSON password + JSON token + cuit query) provides 3 of the 4 reference shapes used across the monorepo (the 4th is matriz's auth_basic redaction per D-22). higyrus Plan 4 establishes account_id propagation pattern — Plan 5 (matriz) replicates with auth_basic Risk API + status=ERROR no-retry tweaks.
