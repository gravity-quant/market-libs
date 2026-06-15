---
phase: 13-cross-package-ergonomics-with-options-max-retries-n
plan: 01
subsystem: testing
tags: [retrytransport, httpx, tenacity, pytest-httpx, with_options, mutation-gate, erg-01]

# Dependency graph
requires:
  - phase: 08-retries-backoff-structured-logging
    provides: "RetryTransport + AsyncRetryTransport per-package; request.extensions['idempotent'] mutation gate; _validate_max_retries helper; max_retries=N → max_attempts=N+1 mapping (D-19)"
  - phase: 10-matriz-aio-py-creation-tokenstore
    provides: "matriz aio.py 852 LOC + TokenStore 3-way concurrency primitive (consumed transitively by Plans 4-5; this plan only extends the transports)"
provides:
  - "RetryTransport.handle_request reads request.extensions['max_attempts'] (sync, 4 packages)"
  - "AsyncRetryTransport.handle_async_request reads request.extensions['max_attempts'] (async, 4 packages)"
  - "verification/test_with_options.py with 4 cross-cutting tests (13 collected items) — RED in HEAD per D-P1"
  - "Mutation gate eval order preserved: idempotent check FIRST, max_attempts only tightens/loosens idempotent calls"
affects:
  - "Plan 2 (with_options ambito): the transport extension wiring is ready; Plan 2 only adds Client.with_options + AsyncClient.with_options + _is_view flag"
  - "Plan 3 (with_options higyrus): same shape"
  - "Plan 4 (with_options matriz): same shape + state.client_max_retries field for TokenStore isolation (D-T1..T3)"
  - "Plan 5 (with_options iol): same shape + green gate consolidation"

# Tech tracking
tech-stack:
  added: []  # No new runtime deps; tenacity 9.1.4 already present from Phase 8
  patterns:
    - "Tests-first cross-cutting (RED in HEAD until later Plans implement the feature) — Phase 8 D-21 / Phase 13 D-P1 carry-forward"
    - "request.extensions['max_attempts'] threading pattern — mirror of Phase 8 request.extensions['idempotent'] mutation gate; mutation gate stays FIRST, max_attempts is computed AFTER"
    - "Acceptance criterion: literal grep for new_order kwarg 'qty=' (not 'quantity=') as guard against TypeError-shadowing-the-merge-gate regression"

key-files:
  created:
    - "verification/test_with_options.py — 4 cross-cutting tests: shares_http_client_and_token (x4 pkgs), does_not_bypass_mutation_gate_matriz (CRITICAL merge gate), max_attempts_extension_honored (x4 pkgs), chaining_inner_wins (x4 pkgs)"
  modified:
    - "packages/ambito-financiero-client/src/ambito_financiero_client/_transport.py — RetryTransport reads max_attempts extension"
    - "packages/ambito-financiero-client/src/ambito_financiero_client/_atransport.py — AsyncRetryTransport mirror"
    - "packages/higyrus-client/src/higyrus_client/_transport.py — same"
    - "packages/higyrus-client/src/higyrus_client/_atransport.py — same"
    - "packages/matriz-client/src/matriz_client/_transport.py — same (placed alongside the auth_basic extras block)"
    - "packages/matriz-client/src/matriz_client/_atransport.py — same"
    - "packages/iol-client/src/iol_client/_transport.py — same"
    - "packages/iol-client/src/iol_client/_atransport.py — same"

key-decisions:
  - "Extension key name is 'max_attempts' (not 'max_retries'): matches the existing tenacity stop_after_attempt(N) semantics and the RetryTransport's internal self._max_attempts field naming. Plans 2-5 shells will set req.extensions['max_attempts'] = self._max_retries + 1 uniformly (D-19 N→N+1 mapping carries forward)."
  - "Variable named effective_max_attempts (not just max_attempts) to avoid shadowing the constructor kwarg name and to make the read intent explicit (default fallback to self._max_attempts when the extension is absent)."
  - "Comment placement: a single inline comment line above the assignment, kept identical across all 8 files: '# Phase 13 ERG-01: per-request override via with_options(max_retries=N) view.' — supports grep-based archeology + eval-order acceptance criteria."
  - "Test file uses pytest.raises(AttributeError) implicitly: tests reference parent.with_options() as if it exists, accept the AttributeError fail mode in Plan 1 HEAD, and let Plans 2-5 flip rows GREEN incrementally. This matches the D-P1 spec exactly."
  - "Mutation-gate test uses # fmt: skip to keep new_order(symbol=\"GGAL\", side=\"BUY\", qty=1, ...) on a single line so the literal acceptance grep matches; ruff format would otherwise split the call across 6 lines."

patterns-established:
  - "Per-test isolation in verification/: autouse fixture _reset_default_clients clears each package's module-level _default_client between tests (precedent: verification/test_retry_mutation_gate.py uses configure() to reset, but this file additionally clears the singleton itself for resilience against future tests that bypass configure())."
  - "Endpoint factory pattern: _idempotent_get_call(pkg_name) returns a callable lambda client: client.<get>(...) per package; the test parametrize iterates pkg_names and applies the factory uniformly. Cleaner than per-pkg branches inside the test body."
  - "AttributeError tolerance for RED-in-HEAD tests: mypy 'attr-defined' error on .with_options(...) is locally suppressed with # type: ignore[attr-defined] ONLY at the matriz mutation-gate call (which uses the typed _get_default() return). The other 3 call sites have parent typed as Any (from _make_client) so no ignore is needed."

requirements-completed: [ERG-01]

# Metrics
duration: ~25min
completed: 2026-06-15
---

# Phase 13 Plan 01: Cross-Cutting Tests + RetryTransport extension wiring Summary

**RetryTransport (sync + async) now reads `request.extensions['max_attempts']` across 4 packages; cross-cutting `verification/test_with_options.py` committed RED in HEAD with 13 collected tests covering SC#1/SC#2/SC#3 + CRITICAL matriz mutation-gate merge gate.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-06-15T02:24:00Z (approximate, plan execution start)
- **Completed:** 2026-06-15T02:49:38Z
- **Tasks:** 3 (atomic per-task commits)
- **Files modified:** 8 (transport) + 1 (test, new) = 9 total

## Accomplishments

- **8 transport files extended with the SAME 1-line read pattern** (sync × 4 + async × 4): `effective_max_attempts = request.extensions.get("max_attempts", self._max_attempts)` placed AFTER the idempotent mutation gate, and `stop_after_attempt(effective_max_attempts)` consumes the value inside the (Async)Retrying loop. Each file diff is exactly 2 new lines (1 comment + 1 assignment) + 1 line replacement.
- **Mutation-gate eval order preserved** in every file: `idempotent` check sits BEFORE `effective_max_attempts` assignment by line number. Acceptance criteria grep'd this across all 8 files. The non-idempotent path is still `if not request.extensions.get("idempotent", False): return super().handle_request(request)` — unchanged.
- **Constructor-default bypass preserved**: `if self._max_attempts <= 1: return super().handle_request(request)` remains the second gate. The extension does NOT override `max_retries=0` (constructor still wins). This matches D-19 semantics.
- **`verification/test_with_options.py` created with 4 cross-cutting tests** (3 parametrized × 4 pkgs + 1 matriz-only mutation-gate = 13 collected items). All 13 fail RED with `AttributeError: 'Client' object has no attribute 'with_options'` — exactly the D-P1 expected state. Ruff + mypy strict GREEN; existing Phase 8 tests (`test_retry_mutation_gate.py`, `test_max_retries_validation.py`) untouched.
- **CRITICAL merge gate test in place**: `test_with_options_does_not_bypass_mutation_gate_matriz` carries the literal `new_order(symbol="GGAL", side="BUY", qty=1, ...)` (the `qty` 3-letter spelling, NOT the longer-form which would TypeError before the mutation gate is exercised) and the `assert len(httpx_mock.get_requests()) == 1` invariant. Anti-Pitfall 14 / SC#2 ROADMAP / money-on-the-line.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend RetryTransport sync × 4 packages** — `49c9bb4` (feat)
2. **Task 2: Extend AsyncRetryTransport × 4 packages (mirror sync)** — `ba32197` (feat)
3. **Task 3: Create verification/test_with_options.py with 4 cross-cutting tests** — `5d9bebc` (test)

## Files Created/Modified

### Created

- `verification/test_with_options.py` (299 LOC) — 4 cross-cutting `with_options` tests; RED in HEAD per D-P1; CRITICAL `test_with_options_does_not_bypass_mutation_gate_matriz` carries the SC#2 merge-gate assertion.

### Modified

- `packages/ambito-financiero-client/src/ambito_financiero_client/_transport.py` (+3 / -1) — sync RetryTransport reads `max_attempts` extension
- `packages/ambito-financiero-client/src/ambito_financiero_client/_atransport.py` (+3 / -1) — async mirror
- `packages/higyrus-client/src/higyrus_client/_transport.py` (+3 / -1) — same
- `packages/higyrus-client/src/higyrus_client/_atransport.py` (+3 / -1) — same
- `packages/matriz-client/src/matriz_client/_transport.py` (+3 / -1) — same (placed alongside the `auth_basic` extras block, before the `Retrying(...)` loop)
- `packages/matriz-client/src/matriz_client/_atransport.py` (+3 / -1) — same
- `packages/iol-client/src/iol_client/_transport.py` (+3 / -1) — same
- `packages/iol-client/src/iol_client/_atransport.py` (+3 / -1) — same

### NOT touched (per plan scope)

- `client.py` / `aio.py` of any of the 4 packages (Plans 2-5 scope)
- `_state.py` of any package (Plan 4 will add `client_max_retries` to matriz only)
- `verification/test_retry_mutation_gate.py` (Phase 8 D-26 scope separation)
- `verification/snapshots/*-surface.txt` (Plans 2-5 D-V5 / D-P4 scope)
- `pyproject.toml` (no new runtime deps per `<code_context>` "No nuevas runtime deps")

## Decisions Made

### Comment placement: single inline line, identical across all 8 files

The plan said "Add an inline comment next to the new `effective_max_attempts = ...` line". I placed it on its OWN line directly above the assignment so the assignment can stay within line=100 and the diff is exactly 2 new lines + 1 replacement per file. The comment text is identical across all 8 files:

```
# Phase 13 ERG-01: per-request override via with_options(max_retries=N) view.
```

This supports grep-based archeology (`grep -rn "Phase 13 ERG-01"` immediately surfaces all 8 sites) and the line-number eval-order acceptance criteria.

### Test file uses `# fmt: skip` once to satisfy literal acceptance grep

The plan's acceptance criterion `grep -c 'new_order(symbol="GGAL", side="BUY", qty=1,' verification/test_with_options.py` requires the call to appear on a single line. Ruff format (line=100) would otherwise split the call across 6 lines because the chain `client.with_options(max_retries=10).new_order(...)` is 154 chars. Solution: append `# type: ignore[attr-defined]  # fmt: skip` to the line, preserving both the literal grep match AND the mypy attr-defined suppression. The trailing `# fmt: skip` is a documented escape hatch (already used in `packages/higyrus-client/src/higyrus_client/client.py`).

### `_reset_default_clients` autouse fixture clears module singletons

The matriz mutation-gate test uses `matriz_client.configure(...)` followed by `matriz_client._get_default()`. To prevent the configured singleton from leaking into subsequent tests (which would, in turn, leak the modified `_state.token` across the parametrize matrix), the autouse fixture explicitly sets `mod._default_client = None` before AND after every test in this file. This is a defensive belt-and-suspenders over the `configure()` reset logic.

### `assert_all_responses_were_requested=False` on tests that fail RED before any request

`test_with_options_does_not_bypass_mutation_gate_matriz` mocks a 503 response but in RED state never consumes it (the `with_options` call raises `AttributeError` first). Without the marker the test would report ERROR at teardown ("responses mocked but not requested") instead of FAILED. The marker keeps the RED signal clean.

### `_idempotent_get_call(pkg_name)` factory returns lambdas

Cleaner than per-pkg branches inside the test body. The test parametrize iterates `pkg_names`, the factory builds a callable, and the test body just calls `call(parent)` and `call(view)`. Endpoint signatures per package:

- ambito: `get_dollar_banco_nacion(dt.date(2024, 1, 2))` (1 arg)
- iol: `get_quote("GGAL")` (1 arg, defaults for `mercado`/`plazo`)
- higyrus: `get_movimientos("1", dt.date(2024, 1, 1), dt.date(2024, 1, 31))` (3 args; `id_cuenta` is `str`)
- matriz: `get_segments()` (no args)

## Deviations from Plan

None — plan executed exactly as written. The plan's `<action>` blocks were precise enough that no auto-fix rules triggered. The two micro-adjustments documented under "Decisions Made" above (single-line comment placement; `# fmt: skip` for the literal acceptance grep) were explicitly within the planner's discretion per the plan's `<action>` constraint "EXACTLY 2 new lines (the assignment + the comment) and 1 line replacement", which both decisions honor.

## Issues Encountered

### Initial `quantity=1` mention in test docstring tripped the negative acceptance grep

While drafting the test 2 docstring I included the cautionary text "Using ``quantity=1`` would raise ``TypeError``..." as a NEGATIVE example explaining why we use `qty`. The acceptance criterion `grep -c 'quantity=1' verification/test_with_options.py` requires ZERO matches. Reworded the docstring to "The longer-form spelling would raise ``TypeError``..." so the literal `quantity=1` substring no longer appears. The semantic guard is unchanged.

### `# type: ignore[attr-defined]` placement: only on the typed call site

mypy strict flags `client.with_options(...)` because `client` (returned from `matriz_client._get_default()`) is typed as `Client` which has no `with_options` method yet. The same call on `parent` (returned from `_make_client(...)` which returns `Any`) does NOT trigger mypy. Solution: add the `# type: ignore[attr-defined]` ONLY at the matriz mutation-gate call site; the other 3 `with_options` call sites use `Any`-typed parent and need no ignore.

### Default `assert_all_responses_were_requested=True` caused teardown ERROR + FAILED on the mutation-gate test

The mutation-gate test mocks a 503 with `is_reusable=True` but in RED state never consumes it. Default pytest-httpx behavior fails the test at teardown with "responses mocked but not requested" — producing both ERROR and FAILED rows. Added `@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)` so the test reports a single FAILED row.

## Forward References for Plans 2-5

Plans 2-5 land `with_options` per-package and turn the test rows GREEN incrementally:

- **Plan 2 (ámbito):** turns `[ambito_financiero_client]` rows GREEN in tests 1, 3, 4. Test 2 (matriz-only) remains RED. Snapshot update: `verification/snapshots/ambito-surface.txt` gains `Client.with_options(*, max_retries: int) -> Client` + `AsyncClient.with_options(*, max_retries: int) -> AsyncClient`.
- **Plan 3 (higyrus):** turns `[higyrus_client]` rows GREEN. Snapshot mirror.
- **Plan 4 (matriz):** turns `[matriz_client]` rows GREEN in tests 1, 3, 4 AND turns test 2 (mutation-gate) GREEN. Also lands D-T3 (`_state.client_max_retries` field + `_ensure_token` consumes it instead of `self._max_retries`) and the matriz-specific D-T5 test in `packages/matriz-client/tests/`.
- **Plan 5 (iol):** turns `[iol_client]` rows GREEN; consolidates the green gate (`uv run pytest` full monorepo + ruff + mypy + lint-imports + pre-commit). LAST in serial because Phase 14 SEC-01 disk persistence interacts with the iol shell.

## Next Phase Readiness

- **Plan 1 deliverables verified**: 8 transport modifications + 1 new test file committed RED. Acceptance criteria all GREEN (grep counts, eval order line-number invariant, ruff + mypy strict, existing Phase 8/10 transport tests still passing).
- **Plan 2 ready to start (ámbito canary)**: with the transport extension already honoring `request.extensions["max_attempts"]`, Plan 2 only needs to add `Client.with_options` + `AsyncClient.with_options` + `_is_view` flag + `close()`/`__exit__`/`aclose()`/`__aexit__` no-op-if-view + update shell `_request()` to set `req.extensions["max_attempts"] = self._max_retries + 1` uniformly + snapshot update + per-package mocked tests. The 3 ámbito rows in `verification/test_with_options.py` flip to GREEN as part of Plan 2.

## Self-Check: PASSED

- All 8 transport files exist with `effective_max_attempts = request.extensions.get` + `stop_after_attempt(effective_max_attempts)` patterns (`grep -c` returns 1 per file, both queries).
- `verification/test_with_options.py` exists, collects 13 tests, all 13 fail RED with `AttributeError`.
- Commit hashes verified in `git log --oneline -5`:
  - `49c9bb4 feat(13-01): RetryTransport reads max_attempts extension across 4 packages (ERG-01)` (Task 1)
  - `ba32197 feat(13-01): AsyncRetryTransport reads max_attempts extension across 4 packages (ERG-01)` (Task 2)
  - `5d9bebc test(13-01): cross-cutting with_options tests + matriz mutation-gate (ERG-01, D-P2)` (Task 3)
- No `client.py` / `aio.py` / `_state.py` / snapshot file / `pyproject.toml` modified — confirmed by `git diff --name-only HEAD~3..HEAD`.
- `verification/test_retry_mutation_gate.py` untouched (`git diff` returns empty).
- `uv run ruff check packages/ verification/test_with_options.py` exits 0.
- `uv run ruff format --check packages/ verification/test_with_options.py` exits 0.
- `uv run mypy --strict packages/ambito-financiero-client/src packages/higyrus-client/src packages/matriz-client/src packages/iol-client/src verification/test_with_options.py` exits 0.
- Per-package test suites (ambito, higyrus, matriz, iol) all GREEN after Task 2 (no regressions in Phase 8/10 transport behavior).

---
*Phase: 13-cross-package-ergonomics-with-options-max-retries-n*
*Completed: 2026-06-15*
