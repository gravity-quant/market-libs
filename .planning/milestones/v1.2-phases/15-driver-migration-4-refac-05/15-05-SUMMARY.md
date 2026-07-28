---
phase: 15-driver-migration-4-refac-05
plan: 05
subsystem: testing
tags: [matriz, single-client, tokenstore, refac-05, verification-driver, ast-guard]

# Dependency graph
requires:
  - phase: 15-driver-migration-4-refac-05 (plan 15-04, wave 4)
    provides: "matriz single-Client migration of the sync hostname read + 6 async _state reads + login/error probes; left an 18-probe sweep carve-out routing through the module singleton"
provides:
  - "main_matriz.py 18 sync sweep probes now route through the single threaded sync Client built in main() (no second runtime Client / TokenStore / remarkets login)"
  - "Driver-local _sync_matriz_request(client, ...) helper mirroring main_higyrus _raw_request_sync, adapted to matriz _core.parse_envelope_response semantics"
  - "Strengthened (non-vacuous) AST guard: zero singleton-path source references in addition to the <=2-ctor cap"
affects: [milestone-final matriz live smoke, REFAC-05 criterion #1, future matriz driver edits]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Threaded single-Client request helper: build RequestSpec -> instance Client._request -> _core.parse_envelope_response (matriz analogue of higyrus _raw_request_sync)"
    - "Two-part AST/source merge gate: ctor-count cap + forbidden singleton-path regex scan (non-vacuity hardening)"

key-files:
  created: []
  modified:
    - main_matriz.py
    - verification/test_main_matriz_uses_single_client_instance.py

key-decisions:
  - "Reused matriz's existing instance semantics (Client._request + _core.parse_envelope_response) inside a driver-local helper rather than calling the package's Client._matriz_legacy_request, to keep the driver self-documenting and mirror the higyrus _raw_request_sync idiom exactly (build RequestSpec -> _request -> parse)."
  - "Risk API auth swapped from the module-level _risk_auth singleton accessor to the instance method client._risk_auth, so the 3 Risk probes draw credentials from the SAME threaded Client._state (no _get_default() touch)."
  - "Made the WR-02 singleton-path scan regex-based with a non-identifier left boundary so the NEW helper name _sync_matriz_request( does not false-positive on the forbidden _matriz_request( substring."

patterns-established:
  - "Singleton-leak prevention is enforced by TWO complementary static checks (ctor count + source-fragment scan), because a ctor cap alone cannot observe a second Client constructed inside the package by the module shim."

requirements-completed: []

# Metrics
duration: 8min
completed: 2026-06-24
---

# Phase 15 Plan 05: Matriz Single-Client Sweep Migration Summary

**Closed the wave-4 carve-out: all 18 matriz sync sweep probes now route through the single threaded sync `Client` (via a higyrus-mirrored `_sync_matriz_request` helper) instead of the module singleton, eliminating the second runtime `Client` / second remarkets login that REFAC-05 Criterion #1 targets — and the AST guard is no longer vacuous.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-24T16:40:39Z
- **Completed:** 2026-06-24T16:48:50Z
- **Tasks:** 1 (atomic gap-closure)
- **Files modified:** 2

## Accomplishments

1. **Driver-local threaded request helper.** Added `_sync_matriz_request(client, method, path, *, params=None, auth_basic=None) -> dict[str, Any]`, mirroring `main_higyrus.py`'s `_raw_request_sync` idiom: builds a `RequestSpec`, calls the instance `Client._request` (raw `httpx.Response`, app-level raise deferred), and delegates parse + raise-on-error to `matriz_client._core.parse_envelope_response` (D-24: `status='ERROR'` → `PrimaryAPIError`; 401 Risk → `AuthenticationError` from `_request`). Same signature and same `dict` envelope return shape as the eliminated module shim.

2. **Threaded `client: Client` into every sweep probe.** `_envelope_probe` and all 18 sweep probes (`probe_get_segments` … `probe_get_account_report`, including the 4 custom ones — segments, all_instruments, cfi_sanity, market_data) now take `client` and route through `_sync_matriz_request`. `main()`'s sweep loop passes the single threaded `client` (`probe_fn(client)`).

3. **Risk API auth de-singletonised.** The 3 Risk probes swapped `auth_basic_fn=_risk_auth` (module accessor → `_get_default()`) for `auth_basic_fn=client._risk_auth` (instance method on the threaded `Client`).

4. **Removed singleton imports.** Dropped `from matriz_client.client import _request as _matriz_request` and `from matriz_client.client import _risk_auth`; added `from matriz_client._core import RequestSpec, parse_envelope_response`.

5. **Strengthened the AST guard (WR-02).** Added `test_main_matriz_has_no_singleton_path_references`: a pure static source scan asserting the driver contains zero `_get_default(`, `_request as _matriz_request`, or `_matriz_request(` references. Patterns use a non-identifier left boundary so the new `_sync_matriz_request(` helper does not trip the `_matriz_request(` rule. The original `<=2`-ctor cap is retained; the new test closes its vacuity gap (a regression that threads one `Client` but still dispatches via the package singleton now FAILS even with the ctor count unchanged).

6. **Fixed the stale `_async_main` comment (WR-03).** The block claiming "one AsyncClient default singleton" now states the single `AsyncClient` is explicitly constructed and threaded as a parameter into every async probe, NOT the module default singleton.

## Verification

- `ruff check` + `ruff format --check` clean on both modified files.
- `uv run mypy main_matriz.py` (strict): **Success: no issues found** (after `uv sync` makes `matriz_client` resolvable — the un-synced run's `import-not-found` / consequent `no-any-return` were the known environment artifact, not code defects).
- `uv run pytest verification/test_main_matriz_uses_single_client_instance.py verification/test_main_drivers_bare_except.py`: **4 passed** (strengthened matriz guard GREEN — exactly 1 sync `Client` + 1 `AsyncClient`, zero singleton refs).
- `uv run pytest packages/matriz-client`: **322 passed**.
- D-06 finding-literal byte-stability: `git diff bc4a697 -- main_matriz.py | grep -E '(title=|fid=|class_=)'` shows **no net change**; `ProbeResult(` name literals also unchanged.
- Exactly one `Client()` (main_matriz.py:2162) and one `AsyncClient()` (main_matriz.py:2101); async surface (77 `aclient` refs) untouched.

## Deviations from Plan

**None for Rules 1-4.** Plan executed as written. One mechanical hardening worth noting (within scope of "strengthen the guard so it is non-vacuous"): the WR-02 source scan was implemented as boundary-anchored regexes rather than plain substring `in` checks, specifically because the new helper name `_sync_matriz_request(` ends in the forbidden `_matriz_request(` substring and a naive `in` check would have false-positived the migrated (correct) driver. A docstring in `_sync_matriz_request` was also reworded to avoid a literal `_get_default(` token so the source scan stays GREEN while still describing (in prose) the singleton path the migration closed.

## Operator-Deferred Items

- **matriz LIVE smoke.** `packages/matriz-client/.env` is absent, so the live remarkets run is operator-deferred (not a plan failure). The runtime behaviour (single Client → single TokenStore → single remarkets login) is enforced statically by the strengthened AST guard; the milestone-final live smoke confirms it end-to-end. Never log/commit credentials.

## Self-Check: PASSED

- File exists: `main_matriz.py` (modified) — FOUND
- File exists: `verification/test_main_matriz_uses_single_client_instance.py` (modified) — FOUND
- File exists: `.planning/phases/15-driver-migration-4-refac-05/15-05-SUMMARY.md` — FOUND
- Commit `1fbc83f` — FOUND
