---
phase: 29-decoder-observable
plan: 02
subsystem: api
tags: [decoder, observability, logging, dataclasses, typing, literal, contextvars, tdd]

# Dependency graph
requires:
  - phase: 29-decoder-observable
    plan: 01
    provides: "The signed DecodePolicy axes + per-package constants (29-SEMANTICS-MATRIX.md §2), the 12-lock record/dedupe contract (29-AGGREGATION-CONTRACT.md) and the D-09 RESPONSE-Literal lock — this plan is their literal transcription"
provides:
  - "packages/higyrus-client/src/higyrus_client/_decode.py — the canonical walker the four other copies in Wave 4 transcribe"
  - "DecodePolicy / POLICY: the seven declared semantic axes as a frozen dataclass plus higyrus's constant tuple"
  - "walk_field: _coerce's branch order verbatim, plus a sink call before every substituted default and a Literal branch that never enforces membership"
  - "walk_model: extra-wire-key detection, the capability _coerce structurally cannot have"
  - "DecodeScope / SILENT_SINK / STRICT_DECODE / DECODE_SCOPE / open_request_scope / current_sink — the dedupe + mode plumbing Plan 03 wires into _request"
  - "hints_for: lru_cache-backed get_type_hints, the phase's single highest-leverage performance change"
  - "HigyrusDecodeError — strict-mode decode divergence carrying field path and type names, never a wire value"
  - "39-test behaviour contract covering five divergence classes x two modes"
affects: [29-03, 29-04, 29-05, 29-06, 29-07, 29-09, 30-iol-typed, 33-driver-runs]

actuals:
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Callable sink object as the reporting seam: the walker never touches logging directly, so a caller can substitute SILENT_SINK or a strict-raising scope without a branch in the walker"
    - "ContextVar-carried decode mode + decode scope with .set()-without-reset discipline (D-03)"
    - "Duck-typed nested-model predicate (is a class + is a dataclass + has a callable from_api) so the walker never imports models"
    - "Index-free list path segment ([]) as the mechanism that collapses N identically-diverging rows into one record"
    - "Back-compat shim preserving a private helper's signature and return values while its body moves to a new module"

key-files:
  created:
    - packages/higyrus-client/src/higyrus_client/_decode.py
    - packages/higyrus-client/tests/test_decode.py
  modified:
    - packages/higyrus-client/src/higyrus_client/models.py
    - packages/higyrus-client/src/higyrus_client/exceptions.py
    - packages/higyrus-client/src/higyrus_client/__init__.py
    - verification/snapshots/higyrus-client-surface.txt

key-decisions:
  - "walk_field calls walk_model directly for a nested model rather than hint.from_api(value), because from_api restarts the path at the root and would break the dotted .parking[].diasParking contract — the returned instance is identical since from_api only does cls(**kwargs)"
  - "A missing/wrong-typed list field reports a divergence and returns [] — the substitution is reported wherever a default replaces wire data"
  - "int-where-float-is-declared is NOT reported: float(value) is a widening coercion, not a substituted default, and JSON routinely sends 0 for a float field"
  - "_coerce's throwaway sink is a fresh DecodeScope, not SILENT_SINK — a legacy caller reaching for the shim gets the same observability as a caller going through from_api"
  - "policy.non_dict_model is descriptive, not a branch: walking every field with a None value under SILENT_SINK converges on {} substitution for higyrus and on cls.empty() for matriz's policy tuple, so both matrix rows fall out of one code path"
  - "hints_for takes Any rather than type[Any] because mypy rejects type[Any] against lru_cache's Hashable parameter; walk_model routes cls through the file's existing cast(Any, cls) discipline instead of a type-ignore"

patterns-established:
  - "Report-then-substitute: every branch that returns a policy default calls the sink immediately before returning, so reporting can never drift out of sync with substitution"
  - "Emission wrapped in contextlib.suppress(Exception) so a consumer handler can never invert observable mode into fatal mode"
  - "Golden-file regeneration is committed in the same commit family as the source change that justifies it, and is explicitly not a test edit"

requirements-completed: [DEC-01]

coverage:
  - id: D1
    description: "The canonical _decode.py walker exporting the eleven public names, with DecodePolicy transcribed from the semantics matrix"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "packages/higyrus-client/tests/test_decode.py::test_all_exports_the_ten_public_names, ::test_policy_constant_matches_the_semantics_matrix"
        status: pass
    human_judgment: false
  - id: D2
    description: "Five divergence classes (missing / type / extra / non_dict / None-204) decode without raising in observable mode and emit the values today's decoder discards"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_missing_scalars_return_typed_zeros_and_report, test_wrong_typed_scalar_returns_default_and_reports_type, test_extra_wire_key_reports_at_info_and_leaves_the_model_untouched, test_non_dict_payload_emits_one_record_and_suppresses_per_field_missing, test_none_payload_behaves_as_non_dict, test_empty_dict_is_a_dict_and_reports_per_field_missing"
        status: pass
    human_judgment: false
  - id: D3
    description: "The record is flat, all-str, top-level, type-not-value, and never carries a wire value"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_record_is_flat_all_str_and_carries_no_wire_value (asserts against a sentinel-built payload), test_contract_keys_avoid_every_reserved_logrecord_attribute"
        status: pass
    human_judgment: true
    rationale: "The test proves no emitted value equals a value in one sentinel payload and that the six keys are disjoint from the reserved set. It cannot prove that no future branch introduces a wire-carrying key — that guarantee is structural (every emitted string is a type name, a path, a package name, a model name or a kind) and needs a human reading the emitter to confirm."
  - id: D4
    description: "Constructing a real LogRecord through Logger.warning with the six-key schema succeeds — the emitter never raises KeyError on a reserved attribute"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_reserved_keys_emission_through_a_real_logger_call_does_not_raise (drives logger.warning(..., extra=...), NOT a setattr-built LogRecord)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Strict mode raises HigyrusDecodeError with the exact field path on missing / type / non_dict, and never on extra"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_strict_mode_raises_with_the_exact_field_path_and_no_wire_value, test_strict_mode_raises_on_missing, test_strict_mode_raises_on_non_dict, test_strict_mode_never_raises_on_an_extra_wire_key"
        status: pass
    human_judgment: false
  - id: D6
    description: "A Literal-typed hint returns its wire value unchanged even outside the declared member set, and still reports a type divergence on a wrong runtime type"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_literal_membership_is_never_enforced, test_literal_reports_a_wrong_runtime_type, test_literal_membership_is_not_enforced_under_strict_mode"
        status: pass
    human_judgment: false
  - id: D7
    description: "Within one decode scope each (model, field_path, kind) triple emits exactly once; distinct kinds at the same path stay distinct"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_list_elements_collapse_under_an_index_free_path, test_distinct_kinds_at_the_same_path_stay_distinct, test_one_scope_shared_across_two_walks_emits_once"
        status: pass
    human_judgment: false
  - id: D8
    description: "SafeModel.from_api keeps its single-positional-argument signature and return contract; the pre-existing 872-test suite stays green with zero test-file edits"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client --ignore=.../test_decode.py -> 872 passed; git diff --name-only <base>..HEAD -- '*/tests/' -> only test_decode.py"
        status: pass
    human_judgment: false
  - id: D9
    description: "get_type_hints resolved through a per-class lru_cache so repeat decodes do not re-evaluate stringified annotations"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_hints_for_is_cache_backed (asserts cache_info().hits increases across repeated decodes)"
        status: pass
    human_judgment: false
  - id: D10
    description: "Emission order for multiple divergent fields in one decode is deterministic and stable across runs"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_emission_order_is_extras_sorted_then_declaration_order, test_emission_order_is_stable_across_repeated_decodes"
        status: pass
    human_judgment: true
    rationale: "Backstop per the plan's must_haves. Two runs in one process over one payload is a weaker claim than run-to-run stability across processes; the ordering is structurally deterministic (sorted extras, then dataclasses.fields() declaration order, depth-first) with no set iteration in the emission path, but only a reader of walk_model can confirm no unordered collection leaks in."

# Metrics
duration: 11min
completed: 2026-08-19
status: complete
---

# Phase 29 Plan 02: The canonical `_decode` walker Summary

**The tracer slice: a new `_decode.py` in higyrus turns every silent type substitution into a six-key structured record on the package logger, adds the extra-wire-key detection `_coerce` structurally could not have, and higyrus's `models.py` now delegates to it without moving a single return value — 872 pre-existing tests green with zero test-file edits.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-08-19T02:04:41Z
- **Completed:** 2026-08-19T02:15:30Z
- **Tasks:** 3
- **Files modified:** 2 created, 4 modified

## Accomplishments

- **The silent substitution is now loud, and the value never moved.** `_coerce` detected a type mismatch and threw the fact away (`return value if isinstance(value, str) else ""`). `walk_field` preserves that branch order verbatim — Union, list, nested model, `str`, `bool`, `int`-with-`bool`-guard, `float`, pass-through — and adds one sink call immediately before each substituted default. Every return value is byte-identical to before; the 872-test merge gate is the proof.
- **Extra wire keys are detectable for the first time.** Both legacy `from_api` implementations iterate `dataclasses.fields(cls)` and call `data.get(name)`, so the payload's own key set was never enumerated. `walk_model` computes `sorted(set(payload) - declared)` and reports each at INFO — vendor growth is information, not a defect (lock 3).
- **N identically-diverging catalogue rows collapse to one record.** A `list[X]` element contributes the path segment `[]` with no index, so `.parking[].diasParking` is the same key for row 1 and row 5,000. The dedupe triple `(model, field_path, kind)` lives in a per-decode-scope `DecodeScope`, never a module global — a process-lifetime set would make the second identical response decode silently clean, the exact false pass this milestone exists to kill.
- **A `null`/204 body emits one record instead of 21.** Lock 8 is implemented by swapping the field sink to `SILENT_SINK` for the non-dict branch, so `non_dict` is terminal for reporting while the walker still builds the all-defaults instance. An empty dict is still a dict and still reports per-field `missing`.
- **The emitter cannot invert observable mode into fatal mode.** The six keys are disjoint from every reserved `LogRecord` attribute — the two most natural names, `module` and `name`, both raise `KeyError` in `makeRecord` — and the whole emission is wrapped in `contextlib.suppress(Exception)` so a third-party handler blowing up cannot reach the decode return path. Both are tested against the real failure mode, not a `setattr`-built record.
- **`Literal` stays open (D-09).** An out-of-set value is returned byte-for-byte unchanged with no `type` divergence; a wrong *runtime* type still reports and is still fatal under strict mode. Vendor enum growth must not storm a Phase 33 driver run.
- **The 89%-of-decode-cost win is in.** `hints_for` is an `lru_cache`-backed `get_type_hints`, so the stringified annotations that `from __future__ import annotations` forces everywhere are resolved once per class instead of once per decode.

## Task Commits

Each task was committed atomically, with the TDD gate sequence explicit in the log:

1. **Task 1 (RED): failing behaviour contract for the walker** - `b6b8aa0` (test)
2. **Task 1 (GREEN): the canonical `_decode.py` walker + `HigyrusDecodeError`** - `262f9a9` (feat)
3. **Task 2 (RED): failing `models.py` delegation contract** - `9dc6659` (test)
4. **Task 2 (GREEN): `models.py` delegates to the walker** - `38f0d47` (feat)
5. **Task 3: public-surface snapshot regen** - `cf45764` (chore)

## Files Created/Modified

- `packages/higyrus-client/src/higyrus_client/_decode.py` (446 lines) - The canonical walker. `DecodePolicy` + `POLICY`, `DecodeScope` + `SILENT_SINK`, `STRICT_DECODE` / `DECODE_SCOPE` ContextVars, `open_request_scope` / `current_sink`, `hints_for`, `walk_field`, `walk_model`, `_emit`, `_LOGGER_NAME`, `_DIVERGENCE_MESSAGE`, `_RECORD_KEYS`. Imports stdlib plus `higyrus_client.exceptions` only.
- `packages/higyrus-client/tests/test_decode.py` (751 lines) - 39 tests: module surface + policy constant, five divergence classes, record shape against a sentinel payload, reserved-key emission through a real `logger.warning`, emitter safety with a raising handler, dedupe collapse, deterministic ordering, four strict-mode cases, three D-09 cases, the `hints_for` cache, `SILENT_SINK` inertness, scope plumbing, and the six delegation tests.
- `packages/higyrus-client/src/higyrus_client/models.py` (354 lines, was 373) - `SafeModel.from_api` builds kwargs via `_decode.walk_model`; `_coerce` is now a 9-line back-compat shim over `_decode.walk_field`. No model class body, field or default touched. Module docstring states the substitution behaviour is unchanged and only the reporting is new.
- `packages/higyrus-client/src/higyrus_client/exceptions.py` - Adds `HigyrusDecodeError(HigyrusClientError)` with `field_path` / `declared_type` / `observed_type` / `model` attributes. Deliberately **not** a subclass of `HigyrusAPIError`: the HTTP response succeeded, it is the payload shape that failed.
- `packages/higyrus-client/src/higyrus_client/__init__.py` - Re-exports `HigyrusDecodeError`; `__all__` stays ASCII-sorted.
- `verification/snapshots/higyrus-client-surface.txt` - One line added for `HigyrusDecodeError`. Regenerated by the operator script, not hand-edited.

## Decisions Made

- **A nested model is walked through `walk_model`, not `hint.from_api(value)`.** `from_api` restarts `path` at the root, which would flatten `.parking[].diasParking` into `.diasParking` and destroy the aggregation contract's worked example. The returned instance is identical because `from_api` only does `cls(**kwargs)` over the same walk. **Consequence carried forward to Plan 06:** a `from_api` *override* on a nested model — market-data's `Symbol` with its `market_id` -> `marketId` mirror — would be bypassed when that model appears nested inside another. Higyrus has no overrides, so nothing is affected here, but Plan 06 must confirm `Symbol` is never a nested field type or add an explicit hook.
- **`int` where `float` is declared is not reported.** `float(value)` is a widening coercion, not a substituted default, and JSON routinely sends `0` for a float field. Reporting it would be a permanent false-positive floor. The rule the walker follows is: report exactly where a policy default replaces wire data.
- **`_coerce`'s throwaway sink is a fresh `DecodeScope`, not `SILENT_SINK`.** The plan said "throwaway sink"; making it silent would give a legacy caller strictly less observability than the same coercion reached through `from_api`. A fresh scope also means the shim never shares dedupe state with a surrounding request scope, which matches "throwaway".
- **`policy.non_dict_model` is descriptive rather than a branch.** Walking every declared field with a `None` value under `SILENT_SINK` produces `{}`-substitution semantics under higyrus's policy tuple and exactly `cls.empty()`'s values under matriz's (`missing_*=None`, `scalar_passthrough=True`, `list[X] -> []`, nested -> recurse). Both matrix rows fall out of one code path, which is what keeps the five copies byte-identical without a per-package branch.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test asserted against a `LogRecord.__dict__` baseline that omits formatter-injected keys**

- **Found during:** Task 1 (GREEN)
- **Issue:** `test_record_is_flat_all_str_and_carries_no_wire_value` computed the "standard attribute" baseline from a freshly constructed `LogRecord` and asserted the remainder equalled the six contract keys. It failed with `message` in the remainder — `caplog`'s formatter calls `record.getMessage()` and caches the result onto `record.__dict__` before the assertion runs. A test artifact, not a walker defect: the emitted `extra` really is six keys.
- **Fix:** Added `{"message", "asctime"}` to the baseline with a comment naming the cause. These are exactly the two names `Logger.makeRecord` adds by hand, already enumerated in aggregation-contract lock 1, so the assertion still fails if the walker ever emits a seventh key.
- **Files modified:** `packages/higyrus-client/tests/test_decode.py`
- **Commit:** `262f9a9`

**2. [Rule 3 - Blocking] mypy strict rejects `type[Any]` against `lru_cache`'s `Hashable` parameter**

- **Found during:** Task 1 (GREEN)
- **Issue:** `uv run mypy packages/higyrus-client/src` reported `Argument 1 to "__call__" of "_lru_cache_wrapper" has incompatible type "type[Any]"; expected "Hashable"` at the `hints_for(cls)` call inside `walk_model`.
- **Fix:** `hints_for` takes `Any`, and `walk_model` routes `cls` through the file's existing `cast(Any, cls)` discipline (bound once as `target` and reused for both `hints_for` and `fields`). **No `type: ignore` comment was introduced**, per the plan's explicit instruction.
- **Files modified:** `packages/higyrus-client/src/higyrus_client/_decode.py`
- **Commit:** `262f9a9`

### Deliberate reading of an acceptance criterion

One Task 1 acceptance criterion reads: *"`python -c "import higyrus_client._decode"` succeeds in a process that has NOT imported `higyrus_client.models`."* As written this is unsatisfiable by any module in the package — importing any submodule executes `higyrus_client/__init__.py`, which imports `models`. The criterion's intent is that `_decode` carries no dependency on `models`, so it is verified by `test_decode_module_never_imports_models`, which AST-parses `_decode.py` and asserts its only package import is `higyrus_client.exceptions`. This is a strictly stronger check than the import probe: it would catch a lazy in-function `import models` that the probe would miss.

## Issues Encountered

- **`ruff`'s isort classified `higyrus_client._decode` as third-party while the RED test was failing.** With the module absent from disk, the import block sorted into an odd two-group shape. It resolved itself the moment `_decode.py` existed; `ruff check` and `ruff format --check` are clean across all 204 repo files.

## Verification

- `uv run pytest packages/higyrus-client/tests/test_decode.py -q --no-cov` — **39 passed** (criterion asked for >= 14).
- `uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q --no-cov` — **911 passed**.
- Same run with `--ignore=packages/higyrus-client/tests/test_decode.py` — **872 passed**. This is the merge gate: the pre-existing suite, untouched.
- Zero-edit gate, asserted mechanically rather than observed:
  ```
  $ git diff --name-only f540533..HEAD -- 'packages/higyrus-client/tests/' \
        'packages/matriz-client/tests/' 'packages/market-data-client/tests/'
  packages/higyrus-client/tests/test_decode.py
  ```
  One path, and it is the new file. **Regenerating `verification/snapshots/higyrus-client-surface.txt` is not a test edit** — it is a golden file whose own 8-line header sanctions regeneration alongside the source change that justifies it, and it lives outside every `tests/` directory.
- `uv run mypy packages/higyrus-client/src` — Success: no issues found in 12 source files.
- `uv run ruff check .` — All checks passed. `uv run ruff format --check .` — 204 files already formatted.
- `uv run lint-imports` — Contracts: 4 kept, 0 broken.
- `uv run pytest verification/test_public_surface.py -q --no-cov` — 4 passed.
- `git status --porcelain verification/snapshots/` after regen showed only `higyrus-client-surface.txt`; the other three packages regenerated byte-identically.
- Regenerated snapshot header: 8 lines, all `#`-prefixed, line 8 is exactly `'#'`.
- `grep -n '^from\|^import' _decode.py` — stdlib only (`contextlib`, `logging`, `contextvars`, `dataclasses`, `functools`, `types`, `typing`) plus `higyrus_client.exceptions`.
- `python -c "import higyrus_client._decode as d; print(sorted(d.__all__))"` — `['DECODE_SCOPE', 'DecodePolicy', 'DecodeScope', 'POLICY', 'SILENT_SINK', 'STRICT_DECODE', 'current_sink', 'hints_for', 'open_request_scope', 'walk_field', 'walk_model']`.
- `grep -c 'higyrus_client' _decode.py` — 5 (>= 2 required).
- `HigyrusDecodeError` importable from `higyrus_client`, present in `__all__`, and `__all__` verified still ASCII-sorted.
- `inspect.signature(SafeModel.from_api).parameters` — `['payload']`.

## Prohibitions status

All three plan prohibitions were carried as `flagged-unverified` and are now satisfied:

- *"Divergence records must NEVER contain a wire value."* — Satisfied structurally and tested. `_emit` builds its six values from `_LOGGER_NAME`, the kind, the path, `_name_of(hint)`, `type(value).__name__` and `cls.__name__`. `test_record_is_flat_all_str_and_carries_no_wire_value` decodes a payload of unique sentinel strings and asserts no emitted value appears among them.
- *"Observable mode must NEVER raise from its own emitter."* — Satisfied. The emission is inside `contextlib.suppress(Exception)`; `test_emitter_never_raises_into_the_decode_return_path` installs a handler whose `emit` raises `RuntimeError` and asserts the decode returns the correct all-defaults instance.
- *"The walker must NEVER enforce `Literal` membership on RESPONSE fields."* — Satisfied. `test_literal_membership_is_never_enforced` asserts `"zzz"` comes back unchanged with no `type` record, and `test_literal_membership_is_not_enforced_under_strict_mode` asserts the same under a bound strict mode. `POLICY.literal_enforced is False` is asserted independently.

## TDD Gate Compliance

Gate sequence is present and correctly ordered in git history for both TDD cycles:

- Cycle 1 (walker): RED `b6b8aa0` `test(...)` -> GREEN `262f9a9` `feat(...)`. RED failed at collection (`ImportError: cannot import name '_decode'`), so no test could have passed by accident.
- Cycle 2 (delegation): RED `9dc6659` `test(...)` -> GREEN `38f0d47` `feat(...)`. RED reported 4 failed / 35 passed — the four new delegation assertions failed for the right reason (`models.py` still carried its own coercion copy) while the walker suite stayed green.
- No REFACTOR gate was needed; no cleanup pass changed behaviour.

## Known Stubs

None. `SILENT_SINK` is unreferenced by higyrus production code today and is documented as such in the module — it is a required constant so the five copies stay byte-identical, and it is exercised by tests and used internally by `walk_model`'s non-dict branch. `open_request_scope` is likewise defined but not yet called: wiring it into `Client._request` / `AsyncClient._request` alongside the `strict_decode` mode bind is Plan 03's scope, per the phase's artifact list.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Plan 03 (client wiring) is unblocked.** It needs `_ClientState.strict_decode: bool = False`, the `strict_decode: bool | None = None` keyword on `Client.__init__` / `AsyncClient.__init__` / `configure`, and a `STRICT_DECODE.set()` + `open_request_scope()` pair at the top of `_request`. Both ContextVars and `open_request_scope` exist and are tested.
- **Wave 4 (Plans 04-07) transcribes this body.** The four per-package deltas are named in the module docstring: the package name in the docstring, the `POLICY` assignment, the `_LOGGER_NAME` literal, and the decode exception imported from `exceptions`. Plan 09's intactness check normalizes exactly those.
- **Carried forward for Plan 06 (market-data):** the nested-model branch calls `walk_model` directly, so a `from_api` override on a *nested* model type is bypassed. `Symbol.from_api`'s `market_id` -> `marketId` mirror and `MarketDataSnapshot.received_at`'s injection bypass both need Plan 06 to confirm those classes never appear as a nested field type, or to add an explicit hook. The two-arg `super(Symbol, cls)` form must be preserved verbatim per matrix §3(b).
- **No blockers.**

## Self-Check: PASSED

Created files verified present on disk: `packages/higyrus-client/src/higyrus_client/_decode.py`, `packages/higyrus-client/tests/test_decode.py`. Modified files verified present: `models.py`, `exceptions.py`, `__init__.py`, `verification/snapshots/higyrus-client-surface.txt`. All five task commits (`b6b8aa0`, `262f9a9`, `9dc6659`, `38f0d47`, `cf45764`) verified present in git history.

---
*Phase: 29-decoder-observable*
*Completed: 2026-08-19*
