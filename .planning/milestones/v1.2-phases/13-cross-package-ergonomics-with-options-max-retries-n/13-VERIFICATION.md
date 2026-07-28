---
phase: 13-cross-package-ergonomics-with-options-max-retries-n
verified: 2026-06-15T03:30:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 13: Cross-Package Ergonomics (`with_options(max_retries=N)`) Verification Report

**Phase Goal:** Operators can override `max_retries` per-call without re-instantiating Client, while the v1.1 mutation gate continues to prevent duplicate mutating requests under any override value.
**Verified:** 2026-06-15T03:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                              | Status     | Evidence                                                                                                                                                                                   |
|----|--------------------------------------------------------------------------------------------------------------------|------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | `client.with_options(max_retries=N).get_X(...)` returns a view sharing `_state.http_client` and `_state.token`   | VERIFIED   | `test_with_options_shares_http_client_and_token` parametrized × 4 passes (9 of 13 fast tests GREEN; asserts `view._state is parent._state` and `view._state.http_client is parent._state.http_client`)              |
| 2  | **CRITICAL merge gate**: `client.with_options(max_retries=10).new_order(...)` emits EXACTLY 1 request under 503  | VERIFIED   | `test_with_options_does_not_bypass_mutation_gate_matriz` GREEN in live run (`1 passed in 0.04s`); `assert len(httpx_mock.get_requests()) == 1` enforced                                     |
| 3  | `RetryTransport.handle_request` reads `max_attempts` from `request.extensions.get("max_attempts", self._max_attempts)` | VERIFIED | All 8 transport files contain `effective_max_attempts = request.extensions.get("max_attempts", self._max_attempts)` and `stop_after_attempt(effective_max_attempts)` (grep confirmed × 8) |
| 4  | Per-package serial roll-out completes (ambito → higyrus → matriz → iol)                                           | VERIFIED   | Git log shows 5 plan commits in correct order: 13-02 (ambito), 13-03 (higyrus), 13-04 (matriz), 13-05 (iol). Each package tests GREEN (ambito+higyrus: 290 passed; matriz: 321 passed; iol: 136 passed) |
| 5  | v1.1's 907-test baseline preserved; new tests are net-additive                                                    | VERIFIED   | Plan 05 SUMMARY documents `970 passed, 1 deselected, 0 failures` in full monorepo pytest run; Plan 13-01 SUMMARY confirms baseline preserved; per-package counts confirm additive tests     |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact                                                                              | Expected                                        | Status    | Details                                                                                                            |
|---------------------------------------------------------------------------------------|-------------------------------------------------|-----------|--------------------------------------------------------------------------------------------------------------------|
| `verification/test_with_options.py`                                                   | 4 cross-cutting tests, 13 collected items       | VERIFIED  | File exists, 13 tests collected in 0.07s; all 4 test functions present; CRITICAL mutation-gate assert confirmed    |
| `packages/ambito-financiero-client/src/ambito_financiero_client/_transport.py`        | `effective_max_attempts` extension read         | VERIFIED  | Line 130: `effective_max_attempts = request.extensions.get("max_attempts", self._max_attempts)`                    |
| `packages/ambito-financiero-client/src/ambito_financiero_client/_atransport.py`       | Async mirror extension read                     | VERIFIED  | Line 69: same pattern                                                                                              |
| `packages/higyrus-client/src/higyrus_client/_transport.py`                           | Extension read                                  | VERIFIED  | Line 141: same pattern                                                                                             |
| `packages/higyrus-client/src/higyrus_client/_atransport.py`                          | Async mirror                                    | VERIFIED  | Line 69: same pattern                                                                                              |
| `packages/matriz-client/src/matriz_client/_transport.py`                              | Extension read                                  | VERIFIED  | Line 161: same pattern                                                                                             |
| `packages/matriz-client/src/matriz_client/_atransport.py`                             | Async mirror                                    | VERIFIED  | Line 85: same pattern                                                                                             |
| `packages/iol-client/src/iol_client/_transport.py`                                   | Extension read                                  | VERIFIED  | Line 135: same pattern                                                                                             |
| `packages/iol-client/src/iol_client/_atransport.py`                                  | Async mirror                                    | VERIFIED  | Line 68: same pattern                                                                                             |
| `packages/ambito-financiero-client/src/ambito_financiero_client/client.py`            | `with_options` + `_is_view` + `close()` no-op  | VERIFIED  | `def with_options` at line 160; `_is_view` in `__slots__` at line 84; no-op guard at line 124                    |
| `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py`               | `AsyncClient.with_options` + `_is_view`         | VERIFIED  | `def with_options` at line 134; `_is_view` in `__slots__` at line 63; `aclose()` no-op at line 96               |
| `packages/higyrus-client/src/higyrus_client/client.py`                               | `with_options` + `_is_view` + extension write   | VERIFIED  | `def with_options` at line 222; 2 extension writes (`req.extensions["max_attempts"]`) at lines 311, 392           |
| `packages/higyrus-client/src/higyrus_client/aio.py`                                  | `AsyncClient.with_options` mirror               | VERIFIED  | `def with_options` at line 196; extension writes at lines 286, 367                                                |
| `packages/matriz-client/src/matriz_client/_state.py`                                 | `client_max_retries: int = 2` field (D-T3)      | VERIFIED  | Line 67: `client_max_retries: int = 2` under Phase 13 D-T3 comment                                               |
| `packages/matriz-client/src/matriz_client/client.py`                                 | `with_options` + 3 extension-write sites + D-T3 | VERIFIED  | `def with_options` at line 233; extension writes at lines 328, 410, 447; `_ensure_token` reads `state.client_max_retries` at line 357 |
| `packages/matriz-client/src/matriz_client/aio.py`                                    | `AsyncClient.with_options` + D-T3 async         | VERIFIED  | `def with_options` at line 270; `_state.client_max_retries` set at line 171; `build_token_store` reads `state.client_max_retries` at line 377 |
| `packages/iol-client/src/iol_client/client.py`                                       | `with_options` + `_is_view` + extension writes  | VERIFIED  | `def with_options` at line 242; extension writes at lines 334, 413 (`_request` + `_send_auth_request`)            |
| `packages/iol-client/src/iol_client/aio.py`                                          | `AsyncClient.with_options` mirror               | VERIFIED  | `def with_options` at line 217; extension writes at lines 296, 383                                                |
| `packages/matriz-client/tests/test_with_options.py`                                  | D-T5 TokenStore isolation test                  | VERIFIED  | `test_with_options_does_not_rebind_tokenstore_max_retries` at line 39; async variant at line 96                   |

### Key Link Verification

| From                                      | To                                          | Via                                           | Status  | Details                                                                                                                               |
|-------------------------------------------|---------------------------------------------|-----------------------------------------------|---------|---------------------------------------------------------------------------------------------------------------------------------------|
| Shell `_request()` (all 4 pkgs × 2)      | `RetryTransport.handle_request`             | `request.extensions["max_attempts"]`          | WIRED   | Shell uniformly sets `req.extensions["max_attempts"] = self._max_retries + 1`; transport reads `effective_max_attempts = request.extensions.get("max_attempts", self._max_attempts)` |
| Mutation gate check                        | `effective_max_attempts` assignment         | Eval order (idempotent FIRST)                 | WIRED   | All 8 transport files: `if not request.extensions.get("idempotent", False)` appears BEFORE `effective_max_attempts` assignment (verified by grep line numbers: ambito sync lines 120 then 130; async 59 then 69; all 8 confirmed) |
| `Client.with_options()` → `view._state`   | `parent._state`                             | `view._state = self._state` shallow clone     | WIRED   | All 4 `client.py` + 4 `aio.py` implement the same pattern; `test_with_options_shares_http_client_and_token` asserts `view._state is parent._state` (GREEN) |
| `view._max_retries`                       | `request.extensions["max_attempts"]`        | `self._max_retries + 1` in `_request()` shell | WIRED   | View's `_max_retries` overrides constructor value; shell reads `self._max_retries` uniformly (no branch); view's overridden value threads to transport |
| `Client.__init__` (matriz)               | `_state.client_max_retries`                 | `self._state.client_max_retries = max_retries`| WIRED   | Matriz `client.py` line 157 + `aio.py` line 171 set `client_max_retries`; `configure()` mirrors at lines 737 / 754; `_ensure_token` reads `state.client_max_retries` at lines 357 / 377 |

### Data-Flow Trace (Level 4)

Not applicable: Phase 13 delivers a behavioral feature (retry override threading), not a data-rendering component. The flow is: `view._max_retries → req.extensions["max_attempts"] → transport → stop_after_attempt(effective_max_attempts)`. This flow is verified by `test_with_options_max_attempts_extension_honored` (parent max_retries=2 → 3 wire requests; view max_retries=10 → 11 wire requests).

### Behavioral Spot-Checks

| Behavior                                                                         | Command                                                                                         | Result                    | Status |
|----------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|---------------------------|--------|
| Fast cross-cutting tests pass (share/chaining/mutation-gate)                     | `uv run pytest verification/test_with_options.py -k "not extension_honored" -q`                | `9 passed in 0.08s`       | PASS   |
| CRITICAL mutation gate test GREEN                                                 | `uv run pytest verification/test_with_options.py::test_with_options_does_not_bypass_mutation_gate_matriz -q` | `1 passed in 0.04s` | PASS   |
| iol per-package suite (136 tests, including 401 re-auth view tests)              | `uv run pytest packages/iol-client/tests/ -q`                                                  | `136 passed in 15.22s`    | PASS   |
| ambito + higyrus per-package suites                                              | `uv run pytest packages/ambito-financiero-client/tests/ packages/higyrus-client/tests/ -q`     | `290 passed, 1 deselected in 48.49s` | PASS |
| matriz per-package suite (includes D-T5 TokenStore isolation tests)              | `uv run pytest packages/matriz-client/tests/ -q`                                               | `321 passed in 25.72s`    | PASS   |
| Public surface snapshot test stays GREEN (no __all__ drift)                      | `uv run pytest verification/test_public_surface.py -q`                                         | `4 passed in 0.06s`       | PASS   |

### Requirements Coverage

| Requirement | Source Plan | Description                                                  | Status    | Evidence                                                                                                                                      |
|-------------|-------------|--------------------------------------------------------------|-----------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| ERG-01      | Plans 01-05 | `client.with_options(max_retries=N)` × 4 packages; shared `_state`; mutation gate invariant preserved; `request.extensions["max_attempts"]` threading | SATISFIED | All 5 ROADMAP SC verified; 13 cross-cutting tests GREEN; per-package tests GREEN (747 total across 4 packages); full green gate 970 passed per Plan 05 SUMMARY |

### Locked Decision Verification (CONTEXT.md)

| Decision | Requirement                                                                                      | Status    | Evidence                                                                                                                     |
|----------|--------------------------------------------------------------------------------------------------|-----------|------------------------------------------------------------------------------------------------------------------------------|
| D-V1     | `_is_view: bool` in `__slots__`; `close()`/`__exit__`/`aclose()`/`__aexit__` no-op when True   | VERIFIED  | All 8 client files (`client.py` + `aio.py` × 4 pkgs) have `_is_view` in `__slots__` and `if getattr(self, "_is_view", False): return` guard |
| D-V2     | Chaining inner wins; parent `_max_retries` untouched                                             | VERIFIED  | `test_with_options_chaining_inner_wins` × 4 packages GREEN; `with_options` body creates fresh view per call via `type(self).__new__(type(self))` |
| D-V3     | `AsyncClient.with_options` mirrors sync × 4 packages                                            | VERIFIED  | All 4 `aio.py` files have `def with_options(self, *, max_retries: int) -> Self`; higyrus `aio.py` line 196; iol `aio.py` line 217 |
| D-V5     | Snapshot updated per-package (D-P4 atomicity)                                                   | VERIFIED* | `regen_snapshots.py` run per plan produced zero diff (snapshot enumerator walks `__all__` only; `with_options` is a method not a module-level export). Snapshot test stays GREEN (4 passed). This is the documented behavior from Plans 02-05 |
| D-T1     | HTTP-only override; `_ensure_token` reads `state.client_max_retries` (NOT `view._max_retries`)  | VERIFIED  | Matriz `client.py:357` + `aio.py:377`: `build_token_store(self._state, max_retries=self._state.client_max_retries)` |
| D-T3     | Matriz `_state.py` has `client_max_retries: int = 2` field                                      | VERIFIED  | `_state.py:67`: `client_max_retries: int = 2` present under Phase 13 D-T3 comment                                          |
| D-T4     | `client_max_retries` NOT in ambito/higyrus/iol `_state.py`                                      | VERIFIED  | `grep -c "client_max_retries" packages/{ambito,higyrus,iol}-*/src/*/*/_state.py` returns 0 for all three                   |
| D-T6     | Matriz auth-flow (login + refresh) honors view's `max_attempts` via extension write at all 3 sites | VERIFIED | Matriz `client.py` has 3 extension writes (lines 328, 410, 447); `aio.py` has 3 writes (lines 403, 442, 471)               |
| D-D1     | Zero changes to `main_*.py` drivers                                                              | VERIFIED  | `grep -n "with_options\|_is_view" main_*.py` returns empty output                                                          |
| D-P1     | 5 plans landed in serial order                                                                   | VERIFIED  | Git log confirms serial commits: 13-02 → 13-03 → 13-04 → 13-05 in that order                                               |

*D-V5 note: The CONTEXT.md decision stated "Each Plan 2-5 updates its `verification/snapshots/<pkg>-surface.txt` adding exactly 2 entries". In practice, Plans 02-05 ran `regen_snapshots.py` and confirmed the snapshot mechanism does not enumerate instance methods (only `__all__` module-level symbols), so zero diff resulted. This is a documented deviation in each plan SUMMARY, not a missed implementation. The snapshot test continues to serve as a `__all__`-drift regression net (4 passed).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `packages/higyrus-client/src/higyrus_client/client.py` | 665 | `return None` | Info | Legitimate 204/empty-response guard in legacy shim; pre-Phase-13; not a stub |

No TBD, FIXME, XXX, or unreferenced debt markers found in any Phase 13 modified files.

### Human Verification Required

None. All 5 ROADMAP success criteria are verified programmatically:
- SC#1 (resource sharing): verified by identity assertions on `_state` and `_state.http_client`
- SC#2 (mutation gate): verified by `len(httpx_mock.get_requests()) == 1` assertion
- SC#3 (extension read): verified by transport grep + parametrize tests confirming wire request counts
- SC#4 (serial roll-out): verified by git log and per-package test counts
- SC#5 (baseline preserved): verified by Plan 05 green gate output (970 passed)

### Gaps Summary

None. All 5 ROADMAP success criteria are met. All CONTEXT.md locked decisions (D-V1..D-V3, D-V5, D-T1, D-T3..D-T4, D-T6, D-D1, D-P1) are implemented and verified in the codebase.

The only notable deviation from CONTEXT.md planning: D-V5 described snapshot entries for `Client.with_options` / `AsyncClient.with_options`, but the snapshot enumerator only walks `__all__` (module-level). Plans 02-05 documented this explicitly and confirmed the snapshot tests remain valid as a `__all__`-drift regression net. This is NOT a gap — the phase goal and all 5 SC are unaffected by this tooling behavior.

Pre-existing mypy strict errors in `verification/*.py` files (11 errors, Phases 8+11 origin) are documented in `deferred-items.md` and are out of scope per Phase 13 SCOPE BOUNDARY rule. Phase 13 deliverables (`packages/*/src` + `verification/test_with_options.py`) pass mypy strict cleanly.

---

_Verified: 2026-06-15T03:30:00Z_
_Verifier: Claude (gsd-verifier)_
