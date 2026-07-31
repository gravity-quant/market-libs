---
phase: 25-mutating-gate-symbols-write
verified: 2026-07-31T20:50:08Z
status: passed
score: 15/15 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: null
---

# Phase 25: Mutating-gate + Symbols write Verification Report

**Phase Goal:** El consumidor puede crear/actualizar symbols detrás de un gate de seguridad opt-in que hace IMPOSIBLE disparar una mutación por accidente — el gate es load-bearing y se construye primero; symbols es la primera superficie de mutación que lo ejercita. Dual sync/async, dispatch vía `_core.py` builders, 4 gates verdes (ruff/format/mypy-strict/pytest).
**Verified:** 2026-07-31T20:50:08Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria + PLAN must_haves merged)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC#1 — Default `Client()`/`AsyncClient()` refuses ALL mutations with `MarketDataMutationNotAllowedError ⊂ MarketDataError`, zero HTTP request | ✓ VERIFIED | `client.py:257-283` / `aio.py:215-239` `_ensure_mutation_allowed()` raises when `not self._state.mutating_allowed`; `exceptions.py:35` confirms `class MarketDataMutationNotAllowedError(MarketDataError)` (no status_code, not `MarketDataAPIError`). End-to-end proof: `test_symbols_write.py::test_create_symbol_refused_by_default_emits_no_request` forces `token_expires_at=0.0` and asserts `httpx_mock.get_requests() == []` — ran directly, PASSED (sync + async mirror in `test_symbols_write_async.py`, also ran directly, PASSED). |
| 2 | Gate is the LITERAL first statement of every mutation method (before build/token/transport) | ✓ VERIFIED | AST check performed directly against `client.py` and `aio.py`: for `create_symbol`/`create_symbols`/`update_symbol` on both `Client` and `AsyncClient`, the first statement past the docstring is `self._ensure_mutation_allowed()` (confirmed programmatically, not by grep alone). |
| 3 | SC#2 — With `mutating_allowed=True` (constructor OR `configure()`) AND matching host, consumer can `create_symbol`/`create_symbols`/`update_symbol` sync AND async | ✓ VERIFIED | `client.py:539-574`, `aio.py:552-586` implement all three methods; `__init__` (`client.py:124-155`, `aio.py:103-139`) and `configure()` (`client.py:605-669`, `aio.py:620-678`) both accept `mutating_allowed`/`expected_host` as `bool\|None`/`str\|None` sentinels. Happy-path dispatch tests (`test_create_symbol_sends_bearer_and_body`, `test_create_symbols_batch_sends_body`, `test_update_symbol_patches_body`, sync+async) all pass. |
| 4 | SC#3 — Request bodies serialize typed→JSON; 201/200 parse to tolerant SafeModel; 422 raises typed error | ✓ VERIFIED | `models.py:198-252` `NewSymbol`/`NewSymbols`/`SymbolPatch.to_dict()`; wire-body assertions in tests match exactly (`{"symbol":..,"market_id":..}`, `{"symbols":[...]}`, `{"active":...}`). `_core.py:684-697 parse_symbols_response` uses `Symbol.from_api` (tolerant). `test_create_symbol_422_raises_api_error` confirms `MarketDataAPIError` via unchanged `raise_for_response`. |
| 5 | SC#4 (task-prompt wording) — symbols builders set `request.extensions["idempotent"]` correctly, all `idempotent=True` per DM-03 | ✓ VERIFIED | `_core.py:394-447` all three builders set `idempotent=True`, `authenticated=True`; `client.py:303/371` and `aio.py:302/378` thread `req.extensions["idempotent"] = spec.idempotent` (pre-existing transport mechanism, unchanged). No non-idempotent symbols endpoint exists in this phase by design (DM-03) — the ROADMAP.md literal SC#4 text ("idempotent=False... never retried") describes the general no-retry mechanism the gate/transport provides, exercised for symbols only in the always-idempotent direction; the mechanism itself (`_transport.py:158-159`, `_atransport.py:57-59`) predates this phase and is unchanged. Not a phase defect — confirmed against the task-prompt's own restated SC#4 and CONTEXT.md D-07. |
| 6 | SC#5 — Sync/async parity via `_core.py` builders; 4 gates green | ✓ VERIFIED | See Gate Execution section below — all 4 gates run directly and green. Dispatch mirrors identically in both shells (confirmed line-by-line). |
| 7 | Exact-hostname host gate (`urlsplit(...).hostname ==`), not substring/endswith; adversarial superstring host rejected | ✓ VERIFIED | `client.py:278-283`/`aio.py:235-239` use `urlsplit(self._state.base_url).hostname` compared with `!=` only; grep confirms no `.endswith(` or substring host logic in either file (mentions are in docstrings describing what NOT to do). `test_substring_attacker_host_refused_sync`/`_async` (host `market-data-develop.bbsa.com.ar.attacker.example` vs expected `market-data-develop.bbsa.com.ar`) ran directly — PASSED. |
| 8 | `configure(mutating_allowed=...)` uses `bool\|None` sentinel so `configure(base_url=...)` cannot silently reset a prior opt-in | ✓ VERIFIED | `client.py:666-669`/`aio.py:675-678` apply `if mutating_allowed is not None:` / `if expected_host is not None:` guards. `test_configure_base_url_does_not_reset_flag_sync`/`_async` open the gate, then call `configure(base_url=...)` omitting the flag, and assert `mutating_allowed is True` still holds — ran directly, PASSED. |
| 9 | SC#5 export/parity enforced by an IN-PACKAGE test (`tests/test_public_surface_market_data.py`), not the cross-package nets | ✓ VERIFIED | `test_public_surface_market_data.py` exists with 5 tests: export presence, `__all__` membership, sync/async method-name parity, sync-shim flat-namespace presence, async-shim-under-`aio`-and-NOT-flat-namespace. Cross-package `verification/test_public_surface.py` confirmed to exclude `market_data_client` (per RESEARCH/PLAN documentation; in-package net is the sole enforcement). |
| 10 | New symbols exports in `__init__.py __all__` | ✓ VERIFIED | `__init__.py` imports and lists `create_symbol`, `create_symbols`, `update_symbol`, `MarketDataMutationNotAllowedError`, `NewSymbol`, `NewSymbols`, `SymbolPatch` — confirmed via grep and a direct `python -c` import+`__all__`-membership check, which printed `OK`. |
| 11 | `mutating_allowed`/`expected_host` live on shared `_ClientState`, not instance `__slots__` — views inherit gate state | ✓ VERIFIED | `_state.py:104-105` fields on `_ClientState` dataclass only. `test_view_inherits_gate_sync`/`_async` (`with_options(max_retries=0)` view) ran directly — PASSED. |
| 12 | `NewSymbols` enforces 1–500 batch bound with a plain `ValueError` (not `MarketData*`) before dispatch | ✓ VERIFIED | `models.py:230-233` `__post_init__` raises plain `ValueError`; test file confirms bounds cases (0, 501, exactly 1, exactly 500). |
| 13 | Request models (`NewSymbol`/`NewSymbols`/`SymbolPatch`) are NOT `SafeModel` subclasses | ✓ VERIFIED | Grep confirms no `class NewSymbol(SafeModel)` etc.; all three are plain `@dataclass(frozen=True, slots=True)`. |
| 14 | `_core.py` builders stay IO-free/state-independent; gate logic does NOT live in `_core.py` | ✓ VERIFIED | `_core.py:394-447` each builder does `del state` and contains no reference to `mutating_allowed`/`expected_host`; gate lives only in `client.py`/`aio.py`. |
| 15 | Async mutation methods NOT re-exported into flat `market_data_client` namespace (stay under `aio`) | ✓ VERIFIED | `test_async_shims_under_aio` explicitly asserts `getattr(market_data_client, name) is not getattr(aio, name)` — ran directly, PASSED (flat name is the sync shim). |

**Score:** 15/15 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `exceptions.py` | `MarketDataMutationNotAllowedError(MarketDataError)` | ✓ VERIFIED | Present, correct base class, in `__all__`. |
| `_state.py` | `mutating_allowed`/`expected_host` fields + `_DEFAULT_EXPECTED_HOST` | ✓ VERIFIED | Present with correct defaults (`False` / develop host). |
| `client.py` | sync `_ensure_mutation_allowed` + gate params + 3 mutation methods + 3 module shims | ✓ VERIFIED | All present, wired, gate-first confirmed via AST. |
| `aio.py` | async mirror (identical) | ✓ VERIFIED | All present, identical structure confirmed. |
| `models.py` | `NewSymbol`/`NewSymbols`/`SymbolPatch` | ✓ VERIFIED | Present, correct `to_dict()`, correct wire keys. |
| `_core.py` | 3 pure builders | ✓ VERIFIED | Present, `idempotent=True`, `authenticated=True`, correct paths/methods. |
| `__init__.py` | re-exports of 7 new public names | ✓ VERIFIED | Confirmed via import + `__all__` membership check. |
| `tests/test_mutation_gate.py` | helper-level adversarial gate tests (sync+async) | ✓ VERIFIED | 14 tests present including substring-attacker case; all pass. |
| `tests/test_symbols_write.py` / `test_symbols_write_async.py` | dispatch + refusal + parity tests | ✓ VERIFIED | Present, cover happy-path, 422, end-to-end refusal, host mismatch, module shim. |
| `tests/test_public_surface_market_data.py` | in-package export/parity net | ✓ VERIFIED | Present, 5 assertions covering export/`__all__`/parity/shim placement. |
| `tests/conftest.py` | gate-field teardown reset | ✓ VERIFIED | Both sync and async teardowns reset `mutating_allowed=False`, `expected_host="market-data-develop.bbsa.com.ar"`. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `client.py` mutation methods | `_state.py` | `self._state.mutating_allowed` / `.expected_host` / `.base_url` reads | ✓ WIRED | Confirmed at `client.py:274-283`. |
| `client.py` gate | `exceptions.py` | `raise MarketDataMutationNotAllowedError(...)` | ✓ WIRED | Two raise sites (flag leg, host leg), confirmed. |
| `client.py`/`aio.py` methods | `_core.py` builders | `spec = _core.build_create_symbol_request(...)` etc. | ✓ WIRED | Confirmed for all three methods, both shells. |
| `__init__.py` | `models.py` | re-export `NewSymbol`/`NewSymbols`/`SymbolPatch` | ✓ WIRED | Confirmed via import test. |
| module shims | `_get_default()` instance methods | delegation | ✓ WIRED | AST shows shims call `_get_default().create_symbol(...)` etc.; module shim test passes. |

### Behavioral Spot-Checks (ran directly, not trusted from SUMMARY)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full package suite | `uv run --package market-data-client pytest packages/market-data-client/tests -q` | 189 passed | ✓ PASS |
| ruff check | `uv run ruff check packages/market-data-client` | All checks passed | ✓ PASS |
| ruff format | `uv run ruff format --check packages/market-data-client` | 31 files already formatted | ✓ PASS |
| mypy src | `uv run mypy packages/market-data-client/src` | Success, no issues in 11 source files | ✓ PASS |
| mypy tests | `uv run mypy packages/market-data-client/tests` | 1 pre-existing error at `test_reference_core.py:208` (confirmed pre-dates Phase 25 per `deferred-items.md`; not a phase gap) | ✓ PASS (documented carry-forward) |
| Zero-HTTP refusal (sync) | `pytest .../test_symbols_write.py::test_create_symbol_refused_by_default_emits_no_request` | PASSED | ✓ PASS |
| Zero-HTTP refusal (async) | `pytest .../test_symbols_write_async.py::test_create_symbol_refused_by_default_emits_no_request` | PASSED | ✓ PASS |
| Substring-attacker host rejection (sync+async) | `pytest .../test_mutation_gate.py::test_substring_attacker_host_refused_{sync,async}` | PASSED | ✓ PASS |
| Import + export/parity one-liner | `python -c "import market_data_client as m; ..."` | printed `OK` | ✓ PASS |
| Gate-first AST check | custom `ast.parse` script against `client.py`/`aio.py` | `_ensure_mutation_allowed()` confirmed literal first statement in all 6 methods (3 × 2 shells) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GATE-MD-01 | 25-01, 25-03 | Opt-in mutating-gate, refuse-by-default, exact-host second gate, no-retry of non-idempotent ops, typed error, dual sync/async | ✓ SATISFIED | Gate mechanics + end-to-end refusal proof verified above. |
| MUT-MD-01 | 25-02, 25-03 | Symbols write (`create_symbol`/`create_symbols`/`update_symbol`) typed request models, tolerant SafeModel responses, 422 typed error, sync+async | ✓ SATISFIED | Dispatch/serialization/parsing verified above. |

No orphaned requirements — `REQUIREMENTS.md` maps only GATE-MD-01 and MUT-MD-01 to Phase 25, and both are declared in the plans' `requirements` frontmatter.

### Anti-Patterns Found

None. Scanned all 7 modified source files and 7 test files for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/skip/xfail markers — the only regex hits were false positives from the Spanish word "método" containing the substring "todo" (not an actual TODO marker). No stub returns, no hardcoded-empty response bodies feeding rendering paths (this is a client library, not UI).

### Deferred Items (explicitly surfaced, not phase failures)

Per CONTEXT.md `<deferred>` and `deferred-items.md`, the following are confirmed present as documented assumptions in code/docstrings (not silently dropped), and are correctly out of Phase 25 scope per the task instructions:

- **A1** — exact 201/200/422 response shapes: `_core.py:684-697` and method docstrings explicitly note the parser stays tolerant (`Symbol.from_api`) pending Phase 27 live confirmation.
- **A2** — snake_case `market_id` wire key: `models.py:202-205` docstring flags this as confirmed-live-in-Phase-27.
- **A3** — real server-side POST idempotency: `_core.py:389-397` docstrings flag `idempotent=True` as "revalidated live in Phase 27."
- **D-08** — PATCH path `/`-encoding for `symbol_id`: `_core.py:434-436` docstring explicitly flags raw interpolation, deferred to Phase 27.
- Pre-existing mypy error in `test_reference_core.py:208`: logged in `deferred-items.md`, confirmed pre-dating Phase 25 via the SUMMARY's `git stash` verification claim (independently re-confirmed by direct `mypy` run showing this as the sole test-suite error).
- market-data-client's absence from the cross-package mypy CI loop: documented as a follow-up in `deferred-items.md`/SUMMARY context, not a Phase-25 defect (the in-package `test_public_surface_market_data.py` net compensates for the equivalent public-surface/parity gap this phase introduces).

None of these affect the pass/fail determination for Phase 25 — they are correctly scoped forward to Phase 27 (LIVE-MUT-01) per the locked CONTEXT.md decisions.

### Human Verification Required

None. All must-haves are either directly observable in code (structural/wiring checks) or covered by mocked behavioral tests that were re-run directly during this verification (not trusted from SUMMARY claims alone).

### Gaps Summary

No gaps found. All 15 derived truths (merging ROADMAP.md's 5 Success Criteria with the `must_haves` frontmatter across all 3 plans, plus the CONTEXT.md-locked security decisions D-01/D-13/D-14 the task explicitly asked to verify) are genuinely met in the codebase, not just claimed in SUMMARY.md. All 4 gates (ruff check, ruff format, mypy-strict, pytest) were re-run directly and are green, with the sole exception of one documented, verified-pre-existing mypy error in a test file unrelated to this phase's scope.

---

_Verified: 2026-07-31T20:50:08Z_
_Verifier: Claude (gsd-verifier)_
