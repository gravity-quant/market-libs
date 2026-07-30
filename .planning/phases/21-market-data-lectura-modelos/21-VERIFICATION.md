---
phase: 21-market-data-lectura-modelos
verified: 2026-07-29T00:00:00Z
status: passed
score: 9/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 21: Market data (lectura) + modelos Verification Report

**Phase Goal:** Implementar la superficie de lectura de market data (`GET /marketdata`,
`GET|POST /marketdata/latest`) con modelos `SafeModel` y paridad `with_options`.
**Verified:** 2026-07-29
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `get_market_data`/`get_latest`/`get_latest_batch` exist in BOTH sync (`client.py`) and async (`aio.py`), with query params serialized correctly | ✓ VERIFIED | `client.py:360-421` (3 methods + module shims :508-546), `aio.py:373-435` (3 async methods + module shims :520-558). Params funneled through `_core.build_market_data_request`/`build_latest_request`/`build_latest_batch_request` → `_params.drop_none` (None dropped, falsy kept). |
| 2 | Responses deserialize into `SafeModel` dataclasses with `received_at` as a first-class field; `from_api` tolerates partial/None payloads without raising | ✓ VERIFIED | `models.py:108-154` — `MarketDataSnapshot(SafeModel)` has `received_at: float` field; `from_api({})`/`from_api(None)`/extra-key payloads all tolerated (test_models.py, 9/9 pass). |
| 3 | `with_options(max_retries=N)` propagates as a shared-view clone in BOTH sync and async | ✓ VERIFIED | `client.py:199-227`, `aio.py:155-185` — `view._state = self._state` (shared), `view._max_retries` overridden, `view._is_view = True`; `close()`/`aclose()` no-op guard present in both. Retry-count tests confirm behaviorally (6 requests for `max_retries=5`, 1 for `max_retries=0`), both surfaces. |
| 4 | Mocked pytest-httpx tests cover param serialization + model tolerance, green | ✓ VERIFIED | `uv run --package market-data-client pytest packages/market-data-client -q` → **95 passed**, 0 failed. |
| 5 | `received_at` is injected DIRECTLY in `MarketDataSnapshot.from_api` (NOT routed through `_coerce`) | ✓ VERIFIED | `models.py:136-154`: `from_api` overridden on `MarketDataSnapshot` only; loop sets `kwargs["received_at"] = received_at` directly for that field, calls `_coerce` for every other field. `test_received_at_injected_wins_over_decoy_payload_key` asserts a decoy payload `"received_at": 999.0` is ignored and the kwarg (`1234.5`) wins. |
| 6 | `with_options` threads `request.extensions["max_attempts"] = self._max_retries + 1` into BOTH `_request` AND `_send_auth_request` in `client.py` AND `aio.py` (4 locations) | ✓ VERIFIED | Confirmed all 4 sites: `client.py:252` (`_send_auth_request`), `client.py:319` (`_request`), `aio.py:252` (`_send_auth_request`), `aio.py:327` (`_request`). Behaviorally proven by `test_with_options_retry_count_equals_max_retries_plus_one` (sync) and `test_async_with_options_retry_count_equals_max_retries_plus_one` (async) — both pass. |
| 7 | D-09: async `aio.py` authenticated header merge makes the Authorization token WIN over `spec.headers` | ✓ VERIFIED | `aio.py:309`: `headers = {**(spec.headers or {}), "Authorization": f"Bearer {token}"}` — spec spread first, Authorization last. Regression test `test_async_authenticated_token_wins_over_decoy_spec_header` (test_async_client.py:177-200) dispatches a decoy `Authorization` header and asserts the sent header equals the fresh token — passes. |
| 8 | D-10: permanent regression tests exist for authenticated 401 → re-auth once → retry → succeed AND persistent-401 re-raise, for BOTH sync and async | ✓ VERIFIED | Sync: `test_authenticated_401_reauths_once_then_succeeds` + `test_authenticated_persistent_401_reraises_with_single_reauth` (test_client.py:139-183). Async: `test_async_authenticated_401_reauths_once_then_succeeds` + `test_async_authenticated_persistent_401_reraises_with_single_reauth` (test_async_client.py:122-168). All 4 assert re-auth token-POST count (exactly one), not ordering. All pass. |
| 9 | No cross-package imports (`models.py`/`_params.py` are verbatim copies of higyrus templates, not imports) | ✓ VERIFIED | `grep -rn "higyrus\|iol_client\|matriz_client\|ambito_financiero\|wallets_client" packages/market-data-client/src/` → only docstring mentions in `models.py`/`_params.py` explaining the copy-not-import decision (D-03/D-07); no `import` statements. `SafeModel`/`_coerce` body is byte-identical to `higyrus_client/models.py:29-105` (diffed manually). |

**Score:** 9/9 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/market-data-client/src/market_data_client/models.py` | `SafeModel`/`_coerce` copy, `MarketDataEntry`, `MarketDataSnapshot` (received_at first-class), `LatestRequest` | ✓ VERIFIED | 178 lines. All symbols present, `__all__` exported, module docstring complete. |
| `packages/market-data-client/src/market_data_client/_params.py` | `drop_none` helper | ✓ VERIFIED | 28 lines, `drop_none` present, no `format_date`/`format_bool` (per D-07 scope). |
| `packages/market-data-client/src/market_data_client/_core.py` | 3 builders + 2 parsers, `authenticated=True`/`idempotent=True`, `received_at` stamping | ✓ VERIFIED | 404 lines. `build_market_data_request`/`build_latest_request`/`build_latest_batch_request` all set both flags; `parse_market_data_response`/`parse_latest_response` stamp `received_at = time.time()` once, before `raise_for_response`, with null/empty-body `[]` guards. |
| `packages/market-data-client/src/market_data_client/client.py` | `with_options` + slots + 3 read methods + max_attempts threading + module shims | ✓ VERIFIED | 546 lines (was smaller pre-phase). `__slots__ = ("_is_view", "_max_retries", "_state")`; all present. |
| `packages/market-data-client/src/market_data_client/aio.py` | Async mirror + D-09 fix + slots + 3 async read methods + max_attempts threading + async shims | ✓ VERIFIED | 563 lines. `__slots__` matches sync; D-09 fix confirmed; all async methods present. |
| `packages/market-data-client/src/market_data_client/__init__.py` | Re-exports models + `LatestRequest` + new sync read methods | ✓ VERIFIED | `LatestRequest`, `MarketDataSnapshot`, `MarketDataEntry` imported and in `__all__`; `get_market_data`/`get_latest`/`get_latest_batch` also re-exported. |
| `packages/market-data-client/tests/test_models.py` | from_api tolerance + received_at injection + LatestRequest tests | ✓ VERIFIED | 99 lines, 9 `def test_` functions, all pass. |
| `packages/market-data-client/tests/test_market_data.py` | builder + parser unit tests | ✓ VERIFIED | 190 lines, pure `_core` unit tests, all pass. |
| `packages/market-data-client/tests/test_with_options.py` | sync retry-propagation-by-count regression | ✓ VERIFIED | 103 lines, 4 tests, all pass. |
| `packages/market-data-client/tests/test_with_options_async.py` | async retry-propagation-by-count regression | ✓ VERIFIED | 121 lines, 4 tests, all pass. |
| `packages/market-data-client/tests/test_client.py` (extended) | D-10 sync 401 sequences + end-to-end serialization | ✓ VERIFIED | 249 lines total; new D-10 + read-method tests present and pass. |
| `packages/market-data-client/tests/test_async_client.py` (extended) | D-10 async 401 sequences + D-09 regression + end-to-end async serialization | ✓ VERIFIED | 273 lines total; new D-10 + D-09 + read-method tests present and pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `models.py` (`MarketDataSnapshot.from_api`) | `models.py` (`received_at` kwarg) | Injects `received_at` directly, skipping `_coerce` | ✓ WIRED | `models.py:150-151`: `if field.name == "received_at": kwargs[field.name] = received_at`. |
| `_core.py` (builders) | `_params.py` (`drop_none`) | Builders call `drop_none` to strip None optionals | ✓ WIRED | `_core.py:288,324` call `_params.drop_none({...})`. |
| `_core.py` (parsers) | `models.py` (`MarketDataSnapshot.from_api`) | Parsers construct `MarketDataSnapshot.from_api(item, received_at=...)` | ✓ WIRED | `_core.py:383,404`. |
| `client.py` (`_request`/`_send_auth_request`) | `_transport.py` (`RetryTransport`) | `req.extensions['max_attempts'] = self._max_retries + 1` consumed by transport | ✓ WIRED | `client.py:252,319`; behaviorally proven by retry-count tests. |
| `aio.py` (`_request`/`_send_auth_request`) | `_atransport.py` (`AsyncRetryTransport`) | Same extension threading, async surface | ✓ WIRED | `aio.py:252,327`; behaviorally proven by async retry-count tests. |
| `client.py`/`aio.py` (read methods) | `_core.py` (builders/parsers) | Read methods call `_core.build_*_request` + `_core.parse_*_response` | ✓ WIRED | All 6 read methods (3 sync + 3 async) follow the 3-liner shape. |
| `__init__.py` | `models.py` | Barrel re-export of `MarketDataSnapshot`/`MarketDataEntry`/`LatestRequest` | ✓ WIRED | `__init__.py:56-60`, confirmed importable (`import market_data_client; market_data_client.LatestRequest` resolves). |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full package test suite | `uv run --package market-data-client pytest packages/market-data-client -q` | 95 passed | ✓ PASS |
| Strict type checking | `uv run mypy packages/market-data-client/src` | Success: no issues found in 11 source files | ✓ PASS |
| Lint | `uv run ruff check packages/market-data-client` | All checks passed | ✓ PASS |
| Format | `uv run ruff format --check packages/market-data-client` | 23 files already formatted | ✓ PASS |
| Retry-count regression (sync) | `test_with_options_retry_count_equals_max_retries_plus_one` | 6/6 outgoing requests for `max_retries=5` | ✓ PASS |
| Retry-count regression (async) | `test_async_with_options_retry_count_equals_max_retries_plus_one` | 6/6 outgoing requests for `max_retries=5` | ✓ PASS |
| D-10 401 re-auth-once (sync + async) | `test_authenticated_401_reauths_once_then_succeeds` / async equiv | Exactly 1 token POST, 200 returned | ✓ PASS |
| D-10 persistent-401 (sync + async) | `test_authenticated_persistent_401_reraises_with_single_reauth` / async equiv | `MarketDataAuthError` raised, exactly 1 token POST | ✓ PASS |
| D-09 header precedence (async) | `test_async_authenticated_token_wins_over_decoy_spec_header` | Sent `Authorization` == fresh token, decoy ignored | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MD-01 | 21-01, 21-02, 21-03, 21-04 | Lectura de market data (`GET /marketdata`, `GET/POST /marketdata/latest`) devuelta como `SafeModel` dataclasses con `received_at` de primera clase, paridad `with_options(max_retries=N)` sync y async | ✓ SATISFIED | All 4 plans deliver toward MD-01; REQUIREMENTS.md marks MD-01 → Phase 21 → Complete; all observable truths above verified against code. |

No orphaned requirements — REQUIREMENTS.md maps only MD-01 to Phase 21, and all 4 plans declare `requirements: [MD-01]`.

### Anti-Patterns Found

None. Scanned all 6 phase-21-modified source files (`models.py`, `_params.py`, `_core.py`, `client.py`, `aio.py`, `__init__.py`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/"not yet implemented" — zero matches.

**Known, documented, non-blocking provisional scope (not an anti-pattern):** Field names in `MarketDataSnapshot`/`MarketDataEntry`/`LatestRequest` are explicitly PROVISIONAL (A1/A2 — the market-data OpenAPI spec is not yet vendored). This is documented in the module docstring, the plan `<action>` blocks, and STATE.md as a known Phase-21→22 risk explicitly deferred to Phase 23 ("Verificación en vivo contra develop + fixes") for reconciliation against real payloads. `from_api` tolerance bounds the blast radius of a wrong guess. This does not block Phase 21's goal, which is scoped to the read surface + model shape + `with_options` parity, not wire-shape reconciliation against a live server.

### Human Verification Required

None. This phase's surface is a pure backend HTTP client library exercised entirely through mocked pytest-httpx tests — no UI, no visual, no external live-service behavior that requires human judgment. Live verification against the real `market-data-develop` service is explicitly Phase 23's scope (LIVE-MD-01), not Phase 21's.

### Gaps Summary

No gaps found. All 4 ROADMAP success criteria and all 9 derived/focus-area observable truths verified directly against the codebase (not SUMMARY.md claims): the read methods exist and dispatch correctly on both surfaces, `received_at` injection bypasses `_coerce` exactly as designed, `with_options` threads `max_attempts` into all 4 required dispatch sites, the D-09 async header-precedence fix is applied and regression-tested, D-10 permanent 401 regression tests exist and pass on both surfaces, and there are zero cross-package imports. All four package gates (pytest, mypy, ruff check, ruff format) are green when run explicitly against `packages/market-data-client` (confirmed NOT relying on a bare root invocation, since this package is absent from root mypy `files` and the CI matrix per Phase-24 scope).

---

_Verified: 2026-07-29_
_Verifier: Claude (gsd-verifier)_
