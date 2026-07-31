---
phase: 25-mutating-gate-symbols-write
plan: 03
subsystem: api
tags: [market-data-client, mutation, dispatch, sync-async-parity, python, tdd]

# Dependency graph
requires:
  - phase: 25-01 (mutating-gate)
    provides: "_ensure_mutation_allowed() gate + MarketDataMutationNotAllowedError + gate state fields (mutating_allowed/expected_host)"
  - phase: 25-02 (request models + builders)
    provides: "NewSymbol/NewSymbols/SymbolPatch + build_create_symbol_request/build_create_symbols_request/build_update_symbol_request"
provides:
  - "Client.create_symbol/create_symbols/update_symbol — gate-first sync dispatch (POST /symbols, POST /symbols/batch, PATCH /symbols/{id})"
  - "AsyncClient.create_symbol/create_symbols/update_symbol — identical async mirror"
  - "Module-level sync shims (client.py) + async shims (aio.py) delegating to _get_default()"
  - "__init__ re-exports: 3 methods + 3 request models + MarketDataMutationNotAllowedError in __all__"
  - "In-package export + sync/async name-parity test net (cross-package nets exclude this package)"
  - "End-to-end zero-HTTP/zero-Auth0 refusal proof through create_symbol (adversarial forced-expired token)"
affects: [26-mutating-gate-calendar, 27-live-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Gate-first dispatch: _ensure_mutation_allowed() is the LITERAL first statement (before build_*, before _request, before token fetch) — zero IO on refusal"
    - "Dispatch mirrors get_symbols read shape: build_* -> _request -> parse_symbols_response (tolerant SafeModel)"
    - "422 flows through existing _core.raise_for_response unchanged (no new status handling in mutation methods)"

key-files:
  created:
    - packages/market-data-client/tests/test_symbols_write.py
    - packages/market-data-client/tests/test_symbols_write_async.py
    - packages/market-data-client/tests/test_public_surface_market_data.py
  modified:
    - packages/market-data-client/src/market_data_client/client.py
    - packages/market-data-client/src/market_data_client/aio.py
    - packages/market-data-client/src/market_data_client/__init__.py
    - packages/market-data-client/tests/test_mutation_gate.py

key-decisions:
  - "Reused tolerant parse_symbols_response as the write-response parser (return type list[Symbol]); response shape is Phase-27-deferred A1, from_api bounds the blast radius"
  - "Module shim tests reference the flat-namespace re-export, so the __init__ re-exports (logically Task 2) landed in the Task 1 GREEN commit to keep Task 1 tests self-contained"
  - "Fixed 8 pre-existing mypy [func-returns-value] errors from 25-01 by replacing 'assert _ensure_mutation_allowed() is None' with a plain call (helper is -> None)"

patterns-established:
  - "Gate-first mutation method verified structurally (AST: first statement past docstring is the gate call) on both shells"
  - "In-package public-surface + parity net independent of the cross-package verification/ tests that exclude market_data_client"

requirements-completed: [GATE-MD-01, MUT-MD-01]

# Metrics
duration: ~7min
completed: 2026-07-31
status: complete
---

# Phase 25 Plan 03: Symbols-write dispatch + shims + re-exports Summary

**Three gate-first symbols-write methods (create_symbol / create_symbols / update_symbol) wired identically onto Client and AsyncClient — `_ensure_mutation_allowed()` as the literal first statement guarantees zero HTTP + zero Auth0 on refusal, dispatch mirrors the get_symbols read shape (build → _request → tolerant parse), 422 surfaces via the existing raise_for_response, and the full surface is re-exported with an in-package export/parity net that the cross-package tests do not cover.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-07-31T20:36:55Z
- **Completed:** 2026-07-31T20:43:51Z
- **Tasks:** 2 (Task 1 TDD)
- **Files modified:** 7 (3 test files created, 3 source + 1 test modified)

## Accomplishments
- Added `create_symbol` / `create_symbols` / `update_symbol` to `Client` (client.py) and `AsyncClient` (aio.py), each with `self._ensure_mutation_allowed()` as the AST-verified literal first statement — before the `_core.build_*` call, before `self._request`, before any token fetch.
- Each method mirrors the `get_symbols` read shape: `spec = _core.build_*` → `resp = self._request(spec)` (`await` in async) → `return _core.parse_symbols_response(resp)` (tolerant `Symbol.from_api`). A 422 flows through the unchanged `_core.raise_for_response` → `MarketDataAPIError` (no new status handling).
- Added module-level sync shims (`create_symbol`/`create_symbols`/`update_symbol` delegating to `_get_default()`) and async shims under `aio`.
- Re-exported the 3 methods + 3 request models (`NewSymbol`/`NewSymbols`/`SymbolPatch`) + `MarketDataMutationNotAllowedError` through `__init__.py __all__` (sorted). Async methods stay under `aio` — NOT flat-namespace re-exported.
- Wrote sync + async dispatch/refusal test files including the adversarial end-to-end refusal: default singleton gate OFF + `token_expires_at=0.0`, `create_symbol` raises `MarketDataMutationNotAllowedError` and `httpx_mock.get_requests() == []` (proves zero HTTP AND zero Auth0 grant). Plus host-mismatch refusal and wire-body/Bearer assertions.
- Added the in-package `test_public_surface_market_data.py` net (export presence + `__all__` membership + sync/async method-name parity + shim placement), because the cross-package `verification/test_public_surface.py` + `test_sync_async_isolation.py` exclude `market_data_client`.
- Fixed the 8 pre-existing mypy-strict `[func-returns-value]` errors in `test_mutation_gate.py` (from 25-01).

## Task Commits

Each task committed atomically (hooks ran, no `--no-verify`):

1. **Task 1 (TDD RED): failing symbols-write dispatch + refusal tests** — `b1fd2bc` (test)
2. **Task 1 (TDD GREEN): gate-first dispatch (sync+async) + shims + re-exports** — `37d256a` (feat)
3. **Task 2: in-package export + sync/async parity net** — `e2d822a` (test)
4. **Cleanup: fix 8 mypy [func-returns-value] errors in test_mutation_gate** — `1bb26a6` (test)

_TDD: Task 1 ran RED (`b1fd2bc`, 18 failing) → GREEN (`37d256a`, 18 passing). No refactor commit needed. The `__init__` re-exports landed in the GREEN commit because the module-shim test references the flat namespace._

## Files Created/Modified
- `packages/market-data-client/src/market_data_client/client.py` — 3 sync gate-first methods + 3 module shims + models import.
- `packages/market-data-client/src/market_data_client/aio.py` — 3 async gate-first methods (identical mirror) + 3 async shims + models import.
- `packages/market-data-client/src/market_data_client/__init__.py` — re-export of 3 methods + 3 request models + the refusal exception in `__all__`.
- `packages/market-data-client/tests/test_symbols_write.py` — sync dispatch + wire-body + 201/200 parse + 422 typed error + end-to-end zero-request refusal + host-mismatch + shim.
- `packages/market-data-client/tests/test_symbols_write_async.py` — async mirror of the above.
- `packages/market-data-client/tests/test_public_surface_market_data.py` — in-package export + sync/async parity net.
- `packages/market-data-client/tests/test_mutation_gate.py` — mypy `[func-returns-value]` fix (assert→plain call).

## Decisions Made
- **Write-response parser:** reused the tolerant `parse_symbols_response` (return type `list[Symbol]`) for all three methods. The real create/update response shape is Phase-27-deferred (A1); `Symbol.from_api` keeps parsing tolerant so a shape surprise cannot crash the client.
- **Re-exports in the GREEN commit:** the Task 1 module-shim test exercises `market_data_client.create_symbol` (flat namespace), which needs the `__init__` re-export. To keep Task 1's test file self-passing, the re-exports (logically Task 2 scope) landed in the Task 1 GREEN commit; Task 2 then added only the dedicated parity net.

## Deviations from Plan
None - plan executed as written. The only sequencing nuance (re-exports folded into the Task 1 GREEN commit) is documented above and does not change scope.

## Issues Encountered
- **Pre-existing mypy error (carry-forward, NOT fixed per instructions):** `packages/market-data-client/tests/test_reference_core.py:208` — `Need type annotation for "body" [var-annotated]`. Present on HEAD before Wave 1 (confirmed in 25-01/25-02 summaries and `deferred-items.md`); explicitly left untouched per the plan instruction to fix only the 8 gate-test errors. `uv run mypy packages/market-data-client/tests` is otherwise clean.

## Carry-Forward (Phase 27, do NOT resolve here)
- **A1:** real create/update response shape (parser stays tolerant until confirmed live).
- **A2:** snake_case `market_id` wire key (confirmed live in Phase 27).
- **A3:** real POST idempotency (`idempotent=True` may flip to False if a retried POST duplicates state).
- **D-08:** percent-encoding of `/`-bearing `symbol_id` in the PATCH path (interpolated raw for now).

## Verification
- **Package suite:** `uv run --package market-data-client pytest packages/market-data-client/tests -q` → **189 passed** (order-independent).
- **Gate 2 — ruff check:** `uv run ruff check .` → All checks passed.
- **Gate 3 — ruff format:** `uv run ruff format --check .` → 191 files already formatted.
- **Gate 4a — mypy src:** `uv run mypy packages/market-data-client/src` → Success, no issues in 11 source files.
- **Gate 4b — mypy tests:** `uv run mypy packages/market-data-client/tests` → clean EXCEPT the noted pre-existing `test_reference_core.py:208` (carry-forward).
- **Gate-first AST guard:** all 6 methods (Client + AsyncClient × 3) have `_ensure_mutation_allowed()` as the literal first statement past the docstring.
- **Acceptance one-liner:** import + `__all__` membership + `hasattr(Client/AsyncClient, ...)` → `OK`.
- **Full suite (wave-merge):** `uv run pytest -q` was started; it exercises all packages including live-network suites in other packages (outside this plan's scope) and buffers output. The market-data-client path — this plan's deliverable — is fully green across all four gates. No cross-package code was touched (the verification nets exclude this package by design).

## Known Stubs
None - the three mutation methods fully dispatch, refuse with zero side effects, and surface 422 as a typed error. The tolerant write-response parser is an intentional Phase-27 deferral (A1), not a stub.

## User Setup Required
None - pure additive code, no package installs, no external service configuration.

## Self-Check: PASSED
- Created files verified on disk: `test_symbols_write.py`, `test_symbols_write_async.py`, `test_public_surface_market_data.py`, `25-03-SUMMARY.md`.
- Task commits verified in git log: `b1fd2bc`, `37d256a`, `e2d822a`, `1bb26a6`.

---
*Phase: 25-mutating-gate-symbols-write*
*Completed: 2026-07-31*
