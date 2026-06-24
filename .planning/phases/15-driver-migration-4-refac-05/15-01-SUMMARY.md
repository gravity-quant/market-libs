---
phase: 15-driver-migration-4-refac-05
plan: 01
subsystem: testing
tags: [ast-guard, driver-migration, httpx, client-threading, tdd, ambito-financiero]

# Dependency graph
requires:
  - phase: 07-core-py-extraction-sync-async-logic-dedup
    provides: "Phase 6/7 LOC extraction baseline (iol client.py 522->490, aio.py 476->457) used as the pinned attestation anchor"
  - phase: 13-ergonomics
    provides: "Per-instance Client()/AsyncClient() surface with with_options() views that the driver now constructs directly"
provides:
  - "Migrated main_ambito_financiero.py: one sync Client() in main(), one async AsyncClient() in _async_main(), threaded into every probe_*"
  - "AST-walker test idiom (verification/test_main_<pkg>_uses_single_client_instance.py) that later drivers (iol/higyrus/matriz) copy"
  - "Constructor-style pinning convention (bare ast.Name) reused by Plans 02-04"
  - ".planning/phases/15-driver-migration-4-refac-05/15-LOC-ATTESTATION.md baseline-anchor + delta attestation reused by all later plans"
affects: [15-02 iol driver, 15-03 higyrus driver, 15-04 matriz driver, Phase 17 LIVE-03 re-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-Client threading: one Client()/AsyncClient() per driver, passed as a parameter to every probe (no _get_default())"
    - "AST-guard merge gate: ast.walk counting ctor Calls, matching both ast.Name and ast.Attribute, with a 1<=count<=2 non-vacuity bound"
    - "Class-level monkeypatch for __slots__ clients (per-instance setattr is read-only)"

key-files:
  created:
    - "verification/test_main_ambito_financiero_uses_single_client_instance.py"
    - ".planning/phases/15-driver-migration-4-refac-05/15-LOC-ATTESTATION.md"
  modified:
    - "main_ambito_financiero.py"
    - "packages/ambito-financiero-client/tests/test_driver_invariants.py"

key-decisions:
  - "Constructor style pinned BARE (from ambito_financiero_client import Client, AsyncClient -> ast.Name) per D-05"
  - "Raw _request swapped to client._request(RequestSpec(...)) + explicit _raise_for_response to preserve the module-delegator's error-raising behavior"
  - "antibot one-shot mutates client._state.user_agent + client.close() to rebuild the pool with the bad UA (UA is baked at httpx.Client construction)"
  - "_core.RequestSpec imported from ambito_financiero_client._core (its home module), not re-exported through client (which does not export _core in __all__)"

patterns-established:
  - "AST-guard non-vacuity: assert lower bound (>=1) so an un-migrated driver constructing zero classes FAILS RED instead of false-passing"
  - "Threaded-client regression tests patch the CLASS method (Client/AsyncClient use __slots__, blocking per-instance monkeypatch)"

requirements-completed: [REFAC-05]

# Metrics
duration: ~40min
completed: 2026-06-24
status: complete
---

# Phase 15 Plan 01: Driver Migration — ámbito (REFAC-05) Summary

**main_ambito_financiero.py migrated to a single threaded sync Client() + single async AsyncClient(), gated by a RED-first AST-walker test, with a measure-only LOC attestation pinning the Phase 6/7 baseline anchor.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-06-24 (execution start)
- **Completed:** 2026-06-24
- **Tasks:** 3 (plus 1 deviation fix)
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments
- AST-guard test authored RED-first (count==0 fails the >=1 lower bound on the un-migrated driver) and verified GREEN (count==2) post-migration.
- `main_ambito_financiero.py` now builds exactly one sync `Client()` in `main()` and one async `AsyncClient()` in `_async_main()`, threaded as a parameter into all 7 probes; zero CODE-line `_get_default()` calls remain (only operator-facing docstring prose at line 573).
- LIVE smoke passed cleanly: `PASS=6 FAIL=0 SKIPPED=1 FINDING=0` against the real ámbito API (antibot opt-in, not enabled), exit 0.
- LOC-attestation doc pins the Phase 6/7 baseline anchor (iol aggregate 947/998), records current LOC (iol=1511, matriz=922), documents the structurally-unreachable −30% disposition (measure-only, codegen DROPPED per Phase 12 NO-GO), and confirms shims STAY + the ≥907 test baseline holds (986 collected).

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): AST-guard failing test** - `4a21a09` (test)
2. **Task 2 (GREEN): migrate driver to single-Client threading** - `204baa6` (feat)
3. **Deviation fix: thread Client/AsyncClient into driver-invariant tests** - `6da94d6` (fix)
4. **Task 3: LOC-attestation doc** - `170cd20` (docs)

## Files Created/Modified
- `verification/test_main_ambito_financiero_uses_single_client_instance.py` (created) - AST-walker asserting `1 <= (Client|AsyncClient) ctor Calls <= 2`; matches both ast.Name and ast.Attribute spellings.
- `main_ambito_financiero.py` (modified) - One sync `Client()` + one async `AsyncClient()`, threaded into every probe; mechanical `_state` read swaps; raw `_request` -> `client._request(RequestSpec(...))` + `_raise_for_response`; antibot mutates the threaded instance's UA.
- `packages/ambito-financiero-client/tests/test_driver_invariants.py` (modified) - WR-01/WR-03/IN-03 regression tests updated to construct a real client and patch the class-level surface.
- `.planning/phases/15-driver-migration-4-refac-05/15-LOC-ATTESTATION.md` (created) - Baseline-anchor resolution + delta attestation (D-08/D-09).

## Decisions Made
- **Constructor style pinned BARE** (`from ambito_financiero_client import Client, AsyncClient`) — bare `ast.Name` spelling per D-05; the AST walker also covers `ast.Attribute` so later drivers may choose either.
- **`_request` behavior preserved exactly:** the module-level `ambito.client._request("GET", path)` applied `_raise_for_response` and used a `(method, path)` signature, whereas the instance `Client._request(spec)` takes a `RequestSpec` and does NOT raise. To keep behavior byte-identical, the driver now builds a `RequestSpec`, calls `client._request(spec)`, then applies `_raise_for_response(resp)` — mirroring the delegator inline.
- **`_core` imported from its home module** (`ambito_financiero_client._core`) rather than re-imported through `client` — `client.py` does not list `_core` in `__all__`, so importing it through `client` tripped mypy strict `attr-defined`.
- **antibot pool rebuild:** because the User-Agent header is baked into the `httpx.Client` at construction, the one-shot bad-UA test mutates `client._state.user_agent` and calls `client.close()` to force a pool rebuild with the new header, restoring good UA + closing again in `finally`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug / Rule 3 - Blocking] Driver-invariant regression tests broken by the intended signature change**
- **Found during:** Task 2 (driver migration)
- **Issue:** `packages/ambito-financiero-client/tests/test_driver_invariants.py` called `driver.probe_happy_sync(date)`, `probe_happy_async(date)`, `probe_antibot(date)`, `probe_no_data(date)`, and `_async_main` with the OLD signatures (no client param) and mocked the module-level `ambito.client._request` / `aio._request` / `ambito.get_dollar_banco_nacion` / `aio.aclose`. The Phase 15 migration adds a required `client`/`aclient` parameter to every probe and routes through the threaded instance, so all 6 tests failed (`TypeError: missing 1 required positional argument`). This would break CI.
- **Fix:** Updated the 6 tests to construct a real `Client()` / `AsyncClient()` and patch the **class** method (`Client._request`, `Client.get_dollar_banco_nacion`, `Client.close`, `AsyncClient._request`, `AsyncClient.aclose`) — per-instance `setattr` is read-only because both clients use `__slots__`. WR-03 mocks set `status_code=200`/`is_error=False` so the newly-threaded `_raise_for_response` treats the mock as success. WR-01 now asserts the good UA is restored on `client._state` (instance, not the module default). IN-03 patches `AsyncClient.aclose` to raise and confirms `_async_main` swallows it.
- **Files modified:** packages/ambito-financiero-client/tests/test_driver_invariants.py
- **Verification:** `pytest packages/ambito-financiero-client/tests/test_driver_invariants.py` -> 6 passed; ruff + mypy clean.
- **Committed in:** `6da94d6`

---

**Total deviations:** 1 auto-fixed (1 bug/blocking — regression tests coupled to the old signatures).
**Impact on plan:** The fix is mandatory for CI green and is an unavoidable consequence of the planned probe-signature change. No scope creep — the same WR-01/WR-03/IN-03 invariants are still asserted, only the wiring updated.

## Issues Encountered
- **mypy `attr-defined` on `_core`:** importing `_core` through `client.py` failed strict mypy because it is not in `client.__all__`. Resolved by importing `RequestSpec` directly from `ambito_financiero_client._core`.
- **Standalone `mypy main_ambito_financiero.py` cannot resolve the package** (the root driver is outside `[tool.mypy].files`, which only covers `packages/*/src`). Ran the CI-equivalent `uv run --package ambito-financiero-client mypy main_ambito_financiero.py` instead — the driver is type-clean (the only remaining error is a pre-existing `verification/mutation_gate.py` matriz_client stub, out of scope).

## LIVE Smoke (Criterion #4, operator-driven)
Run during execution (ámbito requires no auth):
```
PROBE happy_sync: PASS precio=1490.0
PROBE happy_async: PASS precio=1490.0
PROBE parity_sync_async: PASS sync==async=1490.0
PROBE parse_decimal: PASS venta=1490.0
PROBE no_data: PASS NoDataError para 2026-08-23
PROBE schema_snapshot: PASS schema sin drift
PROBE antibot: SKIPPED (opt-in via VERIFY_ANTIBOT=1)
SUMMARY: PASS=6 FAIL=0 SKIPPED=1 FINDING=0
```
Exit 0 — single threaded sync `Client` + single async `AsyncClient` confirmed working against the live service.

## Verification Status
- AST-guard test: RED proven (count==0 fails >=1) -> GREEN (count==2). PASS.
- `grep -n '_get_default' main_ambito_financiero.py`: only line 573 (docstring prose). Zero CODE occurrences. PASS.
- ruff check + mypy strict (package context) on the driver: clean. PASS.
- Finding title/fid/class_ literals unchanged (`git diff` shows no edits to those lines). PASS.
- ámbito package suite (excluding cross-package matriz-coupled harness test when matriz absent): 127 passed; full-workspace targeted run (driver invariants + harness mutation gate + AST guard): 12 passed.
- Full repo-wide `pytest -q` (includes slow LIVE-API probes) was launched and still running at SUMMARY time; the static collected baseline (986 >= 907) is satisfied and all relevant static/unit gates are green.

## Threat Surface
No new security-relevant surface introduced. Per the plan threat register: T-15-01 (no credential logging — ámbito has no auth) preserved; T-15-02 (the <=2-ctor AST gate) is the mitigation, now established for later TokenStore-sensitive drivers; no package installs (T-15-SC N/A).

## Known Stubs
None. No hardcoded empty values, placeholder text, or unwired data sources introduced.

## Next Phase Readiness
- Plan 02 (iol driver) can copy the AST-walker idiom verbatim and reuse the BARE constructor-style pinning + the LOC-attestation anchor.
- Note for later drivers with auth (iol OAuth, matriz TokenStore): the single-Client invariant is now machine-enforced; the forced-refresh write-site `main_iol.py:1289` must target the threaded instance.
- Full live-suite confirmation deferred to Phase 17 (LIVE-03); the static baseline obligation is met.

## Self-Check: PASSED

All created files exist on disk; all task commits (`4a21a09`, `204baa6`, `6da94d6`, `170cd20`, `36654e7`) present in git history.

---
*Phase: 15-driver-migration-4-refac-05*
*Completed: 2026-06-24*
