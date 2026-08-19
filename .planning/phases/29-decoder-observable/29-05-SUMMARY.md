---
phase: 29-decoder-observable
plan: 05
subsystem: api
tags: [decoder, observability, logging, contextvars, asyncio, threading, redaction, security, dual-sync-async, tdd]

# Dependency graph
requires:
  - phase: 29-decoder-observable
    plan: 02
    provides: "The canonical `_decode.py` walker this plan copies verbatim, plus the carried-forward nested-model finding (`walk_field` calls `walk_model` directly, bypassing a nested `from_api` override)"
  - phase: 29-decoder-observable
    plan: 03
    provides: "The `_ClientState` flag + four-entry-point + two-bind-site shape, the marker-delimited generic-scan region for `_logging.py`, and the autouse pristine-decode-context fixture requirement"
  - phase: 29-decoder-observable
    plan: 01
    provides: "29-SEMANTICS-MATRIX.md (market-data's POLICY row + the two model-level exemptions) and 29-AGGREGATION-CONTRACT.md (the 12 locks)"
provides:
  - "`packages/market-data-client/src/market_data_client/_decode.py` — the second copy of the canonical walker; 5 lines differ from higyrus below `from __future__`"
  - "`MarketDataDecodeError(MarketDataError)` — strict-mode decode divergence carrying field path and type names, never a wire value"
  - "market-data `models.py` delegating to the walker with both Section-3 exemptions intact"
  - "`_ClientState.strict_decode: bool = False` + the kwarg on `Client.__init__`, `AsyncClient.__init__`, `client.configure`, `aio.configure` + both `_request` bind sites"
  - "The market-data `_logging.py` filter fix inside the same marker-delimited region Plan 09 will hash"
  - "`test_decode_concurrency.py` — the interleaved-async non-clobbering proof and the plain-thread non-inheritance proof the whole phase's carrier choice rests on"
affects: [29-06, 29-07, 29-08, 29-09, 30-iol-typed, 33-driver-runs]

actuals:
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Pre-processing hook as the ONLY exemption mechanism available to a call site whose walker must stay byte-identical: normalize the payload BEFORE the walk, then discard the walker's output for that key"
    - "Class-keyed (never field-name-keyed) model exemptions — `MarketDataSnapshot.received_at` is a client stamp, `Symbol.received_at` is a wire field, same name, opposite provenance"
    - "Two-checkpoint concurrency assertion: each task asserts the mode it sees BOTH before and after its suspension point, so a leak in either direction fails"
    - "Structural precondition test in place of a walker hook: assert no shipped model is ever another model's field type, so the nested-override bypass is provably moot"

key-files:
  created:
    - packages/market-data-client/src/market_data_client/_decode.py
    - packages/market-data-client/tests/test_decode.py
    - packages/market-data-client/tests/test_decode_concurrency.py
  modified:
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/src/market_data_client/exceptions.py
    - packages/market-data-client/src/market_data_client/__init__.py
    - packages/market-data-client/src/market_data_client/_state.py
    - packages/market-data-client/src/market_data_client/_logging.py
    - packages/market-data-client/src/market_data_client/client.py
    - packages/market-data-client/src/market_data_client/aio.py
    - packages/market-data-client/tests/test_logging.py

key-decisions:
  - "`MarketDataSnapshot.from_api` writes the client stamp OVER the payload's `received_at` before the walk AND discards the walker's output for that key. Step 1 is what makes the walker emit no divergence for the field in any case (absent / conflicting / wrong-typed) and keeps strict mode from making a client-stamped field fatal; step 2 is what makes 'a wire value can never win over the client stamp' true by construction rather than by argument. A walker-level exclusion hook was rejected: it would break the byte-identity D-02 requires across all five copies."
  - "The market-data `_decode.py` differs from higyrus in FIVE lines below `from __future__`, not the four the plan's acceptance criterion enumerates. The exception SYMBOL appears at two sites — the import and the `raise` — so Plan 09's normalizer must normalize the name, not just the import statement."
  - "Two comments inside the copied body still read `higyrus` (`# higyrus-client row of 29-SEMANTICS-MATRIX.md` and `# higyrus has no ``empty()`` today`). They were kept VERBATIM on purpose: the plan's `at most N lines` criterion and Plan 09's byte-identity gate both forbid touching them, and a per-package edit there would be the first crack in the verbatim-copy invariant."
  - "`test_decode.py`'s generic-walker rows drive module-local model fixtures, but the exemption rows drive the REAL shipped `MarketDataSnapshot` and `Symbol` — because for those two the exemption IS the shipped class's contract, and a local stand-in would prove nothing."
  - "The plain-thread non-inheritance test asserts a fact Plan 08 must ACT on, not one it can rely on: matriz's websocket daemon thread will see the ContextVar default no matter what the REST client was configured with."

patterns-established:
  - "When a walker must stay byte-identical across copies, per-model exemptions live entirely in the call site's payload normalization — never in a walker branch, never in a policy field"
  - "A concurrency claim about a context carrier is asserted with forced interleaving (paired `asyncio.Event` handoffs), not with `gather` plus a hopeful `sleep(0)`"
  - "The in-package decoder caplog sentinel is marker-FREE in every package, so it can only ever be evidence about the record contract and never about that package's redaction regexes"

requirements-completed: [DEC-01]

coverage:
  - id: D1
    description: "market-data carries a verbatim copy of the walker; only the per-package deltas differ"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "diff <(sed '1,/^from __future__/d' higyrus/_decode.py) <(sed ... market-data/_decode.py) → 5 changed lines: the decode-error import, its raise site, `_LOGGER_NAME`, and the two ContextVar name strings. `POLICY` is byte-identical (the matrix gives market-data higyrus's row)."
        status: pass
      - kind: test
        ref: "test_decode.py::test_all_exports_the_eleven_public_names, ::test_policy_constant_matches_the_semantics_matrix, ::test_logger_name_is_this_package, ::test_decode_module_never_imports_models"
        status: pass
    human_judgment: false
  - id: D2
    description: "The five divergence classes decode without raising in observable mode and yield market-data's typed zero-defaults, emitting records per the aggregation contract"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_missing_scalars_return_typed_zeros_and_report, test_missing_list_field_returns_empty_list_and_reports, test_wrong_typed_scalar_returns_default_and_reports_type, test_bool_payload_never_collapses_into_an_int_field, test_extra_wire_key_reports_at_info_and_leaves_the_model_untouched, test_non_dict_payload_emits_one_record_and_suppresses_per_field_missing, test_none_payload_behaves_as_non_dict, test_empty_dict_is_a_dict_and_reports_per_field_missing"
        status: pass
    human_judgment: false
  - id: D3
    description: "The record is flat, all-str, top-level, type-not-value, and never carries a wire value (T-29-22)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_record_is_flat_all_str_and_carries_no_wire_value (against a sentinel-built payload), test_contract_keys_avoid_every_reserved_logrecord_attribute, test_reserved_keys_emission_through_a_real_logger_call_does_not_raise"
        status: pass
    human_judgment: true
    rationale: "The test proves no emitted value equals a value in one sentinel payload and that the six keys are disjoint from the reserved set. It cannot prove that no future branch introduces a wire-carrying key — that guarantee is structural (every emitted string is a type name, a path, a package name, a model name or a kind) and needs a human reading `_emit` to confirm. Inherited unchanged from Plan 02, since the emitter is a byte-identical copy."
  - id: D4
    description: "`MarketDataSnapshot.from_api` keeps its extended signature and its `received_at` injection bypass; a wire-supplied `received_at` can never win (T-29-24)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_snapshot_signature_preserved (['payload','received_at'], KEYWORD_ONLY, default 0.0), test_snapshot_received_at_not_walked (payload carries 999.0, keyword 123.5 wins, ZERO divergence records), test_snapshot_received_at_absent_from_payload_still_takes_the_stamp, test_snapshot_wrong_typed_wire_received_at_emits_no_divergence, test_snapshot_received_at_is_never_fatal_under_strict_mode, test_snapshot_other_fields_still_report"
        status: pass
      - kind: test
        ref: "test_symbol_received_at_is_a_wire_field_not_a_stamp — the class-keyed near-miss the matrix warns about"
        status: pass
    human_judgment: false
  - id: D5
    description: "`Symbol.from_api` still mirrors `market_id` into `marketId` before delegating, and still uses the explicit two-argument super (T-29-26)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_symbol_market_id_mirror_preserved (asserts NO `extra` record for the mirrored source key), test_symbol_explicit_market_id_still_wins, test_symbol_uses_two_arg_super (source grep AND a runtime exercise that a zero-arg super would break), test_symbol_non_dict_payload_survives_the_mirror_guard"
        status: pass
      - kind: command
        ref: "grep -c 'super(Symbol, cls)' models.py → 1"
        status: pass
    human_judgment: false
  - id: D6
    description: "Interleaved async tasks each see their own decode mode; the parent context is unchanged after both finish (T-29-25)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_decode_concurrency.py::test_interleaved_async_tasks_do_not_clobber_each_others_mode (two asyncio.Event handoffs force a real interleave; both tasks assert their mode before AND after suspension; the strict task raises at the exact path, the observable task returns a model and emits records; the parent's mode and scope are asserted unchanged), ::test_each_task_gets_its_own_decode_scope"
        status: pass
    human_judgment: false
  - id: D7
    description: "A plain thread does not inherit the mode — it sees the ContextVar default"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_plain_thread_sees_the_contextvar_default_not_the_main_thread_value (also asserts the decode really runs observable in there), test_thread_bind_does_not_leak_back_into_the_spawning_thread"
        status: pass
    human_judgment: false
  - id: D8
    description: "A credential literal never reaches getMessage(), str(record.args) or record.__dict__ on the market-data decoder path"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_logging.py::test_decode_sentinel_never_leaks_credential (marker-FREE literal, fresh scope so the dedupe set cannot make it vacuous, asserts >= 2 divergence records actually emitted, then all three surfaces plus repr(record.__dict__))"
        status: pass
    human_judgment: true
    rationale: "The sentinel is a tripwire, not a proof: it shows one marker-free literal does not appear on the three surfaces for one divergent payload. The structural guarantee is lock 1's six all-str type-not-value keys, which a human must read `_emit` to confirm. Same posture as Plan 03's D9."
  - id: D9
    description: "The strict-decode flag sits beside `mutating_allowed` / `expected_host` on the shared `_ClientState` and is inherited by `with_options` views"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_strict_mode_view_inherits (asserts `view._state is parent._state`, that a parent mutation is visible through the view, and that the name is in NEITHER class's `__slots__`), test_strict_mode_is_not_env_backed (asserts `default is False` and `default_factory is MISSING`)"
        status: pass
    human_judgment: false
  - id: D10
    description: "The mode is reachable from all four public entry points and bound at the top of both `_request` methods, with no reset"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_strict_mode_from_sync_constructor, ::_from_async_constructor, ::_from_sync_configure, ::_from_async_configure (the last two also assert Pitfall 5 — a later configure(base_url=...) does NOT reset the opt-in), test_strict_mode_bound_by_sync_request, test_strict_mode_bound_by_async_request, test_no_reset_after_request, test_request_binds_a_fresh_scope_per_response"
        status: pass
      - kind: command
        ref: "AST check: the first two statements of both `_request` bodies are `_decode.STRICT_DECODE.set(self._state.strict_decode)` and `_decode.open_request_scope()`; grep counts are 1 and 1 in each file"
        status: pass
    human_judgment: false
  - id: D11
    description: "The `RedactingFilter` scan reaches string leaves nested in containers, bounded at depth 4 / 64 entries, without touching the market-data marker set"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_nested_container_string_leaf_redacted, test_nested_list_and_tuple_leaves_redacted, test_untouched_containers_keep_object_identity, test_recursion_depth_bounded, test_wide_container_skipped"
        status: pass
      - kind: command
        ref: "git diff on `_logging.py` shows no hunk changing `_REDACTION_MARKERS` or any `_redact` pass; marker lines `decode-intactness: generic-scan begin/end` appear exactly once each"
        status: pass
    human_judgment: false

# Metrics
duration: 11min
completed: 2026-08-19
status: complete
---

# Phase 29 Plan 05: Fanning the walker out to market-data Summary

**The tracer slice reproduces in a second package: market-data carries a byte-verbatim walker, `Client(strict_decode=True)` reaches it through a ContextVar bound at the top of both `_request` implementations, and the two model-level exemptions the semantics matrix records — `MarketDataSnapshot`'s client stamp and `Symbol`'s wire-key mirror — survive the delegation with a proof that interleaved async tasks never clobber each other's mode.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-08-19T12:19:49Z
- **Completed:** 2026-08-19T12:30:58Z
- **Tasks:** 3
- **Files modified:** 3 created, 8 modified

## Accomplishments

- **The copy really is a copy.** Below `from __future__`, market-data's `_decode.py` differs from the higyrus original in exactly five lines: the decode-error import, its `raise` site, `_LOGGER_NAME`, and the two ContextVar name strings. `POLICY` is byte-identical because the semantics matrix gives market-data higyrus's row verbatim. Two comments inside the body still say `higyrus`; keeping them was a deliberate choice, not an oversight (see Decisions).
- **The exemption the matrix could not express is now enforced by construction, not by argument.** `MarketDataSnapshot.from_api` writes the client stamp over the payload's own `received_at` *before* the walk and then discards the walker's output for that key. The first step means the walker never sees a wire value at that key, so it emits no divergence for it whether the payload omits it, contradicts it, or sends garbage — and strict mode can never make a client-stamped field fatal. The second step means the final value is the caller's `float` verbatim, never a coerced or substituted one. Four tests cover the four cases and a fifth asserts the field is silent while every *other* field still reports.
- **The near-miss the matrix warned about is now a test.** `Symbol` also declares `received_at`, but there it is the server's ingest timestamp — same name, opposite provenance. `test_symbol_received_at_is_a_wire_field_not_a_stamp` pins that the exemption is class-keyed; a field-name-keyed one would have broken `Symbol` silently.
- **`Symbol`'s mirror and its two-argument super both survive, and both are tested twice.** The mirror runs before the walker sees the payload, so after it `marketId` is a declared-and-present key and no `extra` record fires for it — the test asserts that absence explicitly, because it is the part a mechanical rewrite would get wrong. The `super(Symbol, cls)` form is checked by a source grep *and* by a runtime exercise: the grep survives a refactor that happens to work, the exercise catches the `TypeError` a zero-argument super raises under the slots rebuild.
- **Plan 02's carried-forward nested-model finding is discharged structurally.** `walk_field` walks a nested model through `walk_model` directly, which would bypass a `from_api` override on a nested model type. Rather than add a hook to a file that must stay byte-identical, `test_no_shipped_safemodel_appears_as_a_nested_field_type` asserts the precondition that makes the bypass moot: no shipped market-data `SafeModel` is ever declared as another model's field type. If a future plan nests one, that test fails and the walker needs the hook.
- **The carrier's isolation properties are now asserted, not assumed.** Two coroutines on one loop, forced to genuinely interleave with paired `asyncio.Event` handoffs: the strict task binds and suspends, the observable task runs *while that bind is live in the sibling context*, and the strict task resumes only after the sibling's decode is done. Both assert the mode they see before and after suspension, so a leak in either direction fails. The parent context's mode and scope are asserted unchanged afterwards.
- **A plain thread provably does not inherit — and that is a finding for Plan 08, not a reassurance.** `threading.Thread` starts with an empty context, so every `ContextVar` read there returns the default. matriz's websocket daemon thread would therefore run every streamed frame in observable mode regardless of how the REST client was configured. Plan 08 has to bind explicitly.
- **The filter fix landed inside the exact marker-delimited region Plan 09 will hash**, byte-identical to higyrus's, with `_REDACTION_MARKERS` and the `_redact` pass chain untouched — the marker sets differ per package by design, and the `git diff` confirms no hunk touches either.

## Task Commits

Each task was committed atomically; Task 2's TDD gate sequence is explicit in the log:

1. **Task 1: walker copy + decode error + mode carrier + filter fix** — `411a443` (feat)
2. **Task 2 (RED): failing decode contract for market-data** — `ef0049b` (test)
3. **Task 2 (GREEN): `models.py` delegates to the walker** — `7c99dbf` (feat)
4. **Task 3: interleaved-async proof + decoder caplog sentinel** — `77eeaab` (test)

## Files Created/Modified

- `packages/market-data-client/src/market_data_client/_decode.py` (447 lines, **created**) — the second copy of the canonical walker.
- `packages/market-data-client/src/market_data_client/exceptions.py` — adds `MarketDataDecodeError(MarketDataError)` with `field_path` / `declared_type` / `observed_type` / `model`. Deliberately **not** a subclass of `MarketDataAPIError`: the HTTP response succeeded, it is the payload shape that failed, so it carries no `status_code`. `__all__` stays ASCII-sorted.
- `packages/market-data-client/src/market_data_client/__init__.py` — re-exports it; the package `__all__` stays ASCII-sorted.
- `packages/market-data-client/src/market_data_client/_state.py` — `strict_decode: bool = False` immediately after `expected_host`, a **plain** default with no `default_factory` despite every credential field around it using one, with the T-29-16 rationale in a source comment.
- `packages/market-data-client/src/market_data_client/client.py` — `strict_decode` kwarg on `Client.__init__` and `configure`; the two-statement bind at the top of `_request`, with a comment naming the re-auth carve-out as the reason the collector is scoped to the decode entry rather than to the response object.
- `packages/market-data-client/src/market_data_client/aio.py` — the verbatim async mirror of all three changes, plus the note that each asyncio task carries its own context copy.
- `packages/market-data-client/src/market_data_client/models.py` (556 lines, was 559) — `SafeModel.from_api` delegates to `walk_model`; `_coerce` is a back-compat shim over `walk_field`; both overrides preserved with their reasoning extended to name the walker. No other model class, field or default touched.
- `packages/market-data-client/src/market_data_client/_logging.py` — the marker-delimited generic-scan region, byte-identical to higyrus's, plus the docstring paragraph stating that marker anchoring is deliberately unchanged and that the record contract, not this filter, is what keeps wire values out.
- `packages/market-data-client/tests/test_decode.py` (1043 lines, **created**) — 60 tests.
- `packages/market-data-client/tests/test_decode_concurrency.py` (**created**) — 4 tests.
- `packages/market-data-client/tests/test_logging.py` (+155 lines, **0 deleted** — append-only, verified with `git diff --numstat`) — 6 new tests.

## Decisions Made

- **The `received_at` bypass is a pre-processing hook plus a post-walk overwrite, not a walker branch.** The walker has no field-exclusion mechanism, and adding one would break the byte-identity D-02 requires across five copies. The available lever is the call site, and the matrix already blesses that shape for `Symbol`'s mirror ("runs before the walker sees the payload"). Writing the stamp into the payload first is what suppresses the divergence record; overwriting the walker's output afterwards is what makes the keyword win verbatim. Doing only the second would leave a spurious `missing` record — and, worse, a strict-mode raise on a client-stamped field. Doing only the first would route the value through `walk_field`, which the plan's prohibition forbids.
- **Five differing lines, not four.** The plan's acceptance criterion enumerates the logger name, the two ContextVar names, the decode-error import and `POLICY`. The exception *symbol* appears at two sites, so the `raise` line differs too. Flagged here rather than papered over: Plan 09's normalizer must normalize the exception name, not just the import statement.
- **Two `higyrus`-naming comments were kept verbatim inside the copied body.** `# higyrus-client row of 29-SEMANTICS-MATRIX.md Section 2` and `# higyrus has no ``empty()`` today` both read oddly in market-data. Editing them would add two more differing lines and start the erosion of the verbatim-copy invariant that D-02 exists to protect. Plan 09 should decide whether to normalize them once, for all five copies, rather than each executor deciding locally.
- **The exemption tests drive the real shipped classes.** Everywhere else in the suite the model fixtures are module-local, so a shipped model gaining a field cannot turn a walker regression green. For `MarketDataSnapshot` and `Symbol` the opposite is true: the exemption *is* the shipped class's contract, and a local stand-in would prove nothing.
- **The concurrency test forces the interleave rather than hoping for it.** `asyncio.gather` plus `await asyncio.sleep(0)` would likely serialize into a passing test that proves nothing. Two `asyncio.Event` handoffs guarantee that the observable task runs while the strict task's `set()` is live, and both tasks assert at two checkpoints so a leak in either direction fails.
- **The sentinel literal carries no redaction marker**, matching Plan 03's reasoning: a `Bearer …`-shaped sentinel would be rescued by `_redact` and the test would silently become a filter test.

## Deviations from Plan

### Auto-fixed Issues

None. No bug, missing critical functionality or blocking issue was encountered — the walker, the carrier shape and the filter fix all transcribed cleanly, and no pre-existing market-data test needed an edit.

### Clarifications to acceptance criteria

**1. The `_decode.py` diff is five lines, not the four the criterion enumerates.** Documented above under Decisions and carried forward to Plan 09. Not a defect: the criterion says "at most", and the fifth line is the `raise` site of the very symbol the fourth line imports.

**2. Five container-recursion tests were appended to `test_logging.py`, not the four the plan names.** The plan says "the four container-recursion tests mirroring the higyrus copy" and then names four; the higyrus copy actually has five in that section. The fifth, `test_untouched_containers_keep_object_identity`, pins the identity-preserving rebuild, so a future simplification that always allocates would be caught. Mirroring the higyrus copy faithfully was read as the governing instruction.

---

**Total deviations:** 0 auto-fixed. Two acceptance-criterion clarifications, both documented above.
**Impact on plan:** None. No scope creep; every file touched is in the plan's `files_modified` list.

## Issues Encountered

- None. `ruff format` reflowed nothing; `ruff format --check .` reports 207 files already formatted.
- One line needed an explicit `# fmt: skip` (the `stamped` ternary in `MarketDataSnapshot.from_api`), matching the existing repo convention for a long expression the formatter would otherwise split unhelpfully.

## Verification

- `uv run pytest packages/market-data-client -q --no-cov` — **460 passed** (390 pre-existing + 60 `test_decode` + 4 `test_decode_concurrency` + 6 appended to `test_logging`).
- `uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q --no-cov` — **995 passed** (criterion asked for >= 872).
- `uv run pytest .../test_decode_concurrency.py .../test_logging.py .../test_decode.py -q --no-cov` — 76 passed.
- `uv run mypy packages/market-data-client/src` — Success: no issues found in 12 source files.
- `uv run ruff check .` — All checks passed. `uv run ruff format --check .` — 207 files already formatted.
- `uv run lint-imports` — Contracts: 4 kept, 0 broken.
- Zero-edit gate on pre-existing tests, asserted mechanically:
  ```
  $ git diff --numstat 2c908c0..HEAD -- 'packages/market-data-client/tests/'
  1043	0	packages/market-data-client/tests/test_decode.py
  ```
  One path at the Task-2 boundary, and it is the new file; `test_decode_concurrency.py` and the `test_logging.py` append land in Task 3 at `155  0` — **0 deleted lines** in every case.
- `diff <(sed '1,/^from __future__/d' higyrus/_decode.py) <(sed '1,/^from __future__/d' market-data/_decode.py)` — 5 changed lines, enumerated above. `POLICY` byte-identical.
- `sorted(market_data_client._decode.__all__) == sorted(higyrus_client._decode.__all__)` — True, the eleven public names.
- `inspect.signature(...)` — `strict_decode` present in `Client`, `AsyncClient`, `market_data_client.configure` and `market_data_client.aio.configure`: four `True`.
- `grep -c 'strict_decode' _state.py` — 1; the declaration is `strict_decode: bool = False`, and `dataclasses.fields` reports `default is False` / `default_factory is MISSING`.
- `grep -c '_decode\.STRICT_DECODE\.set'` — 1 in `client.py`, 1 in `aio.py`; same counts for `_decode.open_request_scope`. An AST check confirms both are the first two statements of each `_request` body (docstring excluded), neither in a `finally`.
- `inspect.signature(MarketDataSnapshot.from_api).parameters` — `['payload', 'received_at']`, the second `KEYWORD_ONLY` with default `0.0`. `SafeModel.from_api` — `['payload']`.
- `grep -c 'super(Symbol, cls)' models.py` — 1.
- Marker lines in `_logging.py`: `decode-intactness: generic-scan begin` ×1 and `... end` ×1. `git diff` shows no hunk touching `_REDACTION_MARKERS` or any `_redact` pass.
- `MarketDataDecodeError` importable from `market_data_client`, present in `__all__`, and both `__all__` lists verified still ASCII-sorted.
- `git diff --diff-filter=D --name-only` across all four commits — empty; no files deleted.
- No `verification/snapshots/market-data-client-surface.txt` exists, so no regeneration was needed (the in-package `test_public_surface_market_data.py` passes unchanged).

## Prohibitions status

Both plan prohibitions were carried as `flagged-unverified` and are now satisfied:

- *"Divergence records must NEVER contain a wire value — market-data payloads carry account and symbol identifiers, and the record names the field, never the value."* — Satisfied structurally and tested twice. `_emit` builds its six values from `_LOGGER_NAME`, the kind, the path, the declared type name, `type(value).__name__` and `cls.__name__`. `test_record_is_flat_all_str_and_carries_no_wire_value` decodes a payload of unique sentinel strings and asserts no emitted value appears among them; `test_decode_sentinel_never_leaks_credential` drives a marker-free credential literal through a real shipped model and checks all three `LogRecord` surfaces plus `repr(record.__dict__)`.
- *"The `received_at` client stamp must NEVER be routed through the walker — a wire-supplied value would then win over the client's own timestamp."* — Satisfied in outcome, with the mechanism stated plainly rather than glossed. The value assigned to the field is the keyword verbatim; the walker's output for that key is discarded. The reason the stamp is *also* written into the payload before the walk is to suppress the divergence record and the strict-mode raise that a `missing`/`type` observation on a client-stamped field would otherwise produce — the walker offers no exclusion hook, and adding one would break byte-identity. `test_snapshot_received_at_not_walked` asserts the keyword beats a conflicting wire `999.0` and that zero divergence records are emitted; three sibling tests cover the absent, wrong-typed and strict-mode cases. A reader who wants the literal "not routed" property should read the two-step comment in `models.py`, which states exactly what happens and why.

## TDD Gate Compliance

Task 2 was the plan's `tdd="true"` task and its gate sequence is present and correctly ordered in git history: RED `ef0049b` `test(...)` → GREEN `7c99dbf` `feat(...)`. The RED run reported **4 failed / 56 passed** — the four delegation assertions failed for the right reason (`models.py` still carried its own `_coerce` copy) while the walker suite was already green, so nothing passed by accident. No REFACTOR gate was needed. Tasks 1 and 3 are not TDD tasks (a verbatim file copy and a test-only addition respectively).

## Known Stubs

None. Every symbol this plan touched is on a live path: both bind sites run on every request, `_scan_record_dict` runs on every log record, `strict_decode` is read by the bind, and both overrides run on every snapshot and symbol decode. `SILENT_SINK` remains the deliberately-unreferenced-in-production constant it is in higyrus — required so the copies stay byte-identical, exercised by tests, and used internally by `walk_model`'s non-dict branch.

## Threat Flags

None. This plan adds no network endpoint, no auth path, no file access and no schema at a trust boundary. The three boundaries it does touch (upstream JSON → walker, walker → package logger, async task context → sibling task context) are the plan's own T-29-22 through T-29-28, each with a named mitigation and a test above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Wave 4 continues unblocked.** The per-package recipe is now proven twice: copy `_decode.py` with the five-line delta, add the decode error to `exceptions.py` and the package `__all__`, add `strict_decode: bool = False` to `_ClientState`, add the kwarg to the entry points, bind two statements at the top of each `_request`, and transcribe the marker-delimited region into `_logging.py`.
- **Carried forward for Plan 08 (matriz websocket), now with evidence:** a plain `threading.Thread` sees the ContextVar DEFAULT, never the spawning thread's value — `test_plain_thread_sees_the_contextvar_default_not_the_main_thread_value` asserts it directly. matriz's websocket daemon thread therefore cannot inherit the REST client's mode and must bind it explicitly, or every streamed frame silently decodes observable.
- **Carried forward for Plan 09 (intactness gate), three items:** (1) the exception SYMBOL appears at two sites, so the normalizer must normalize the name, not just the import line; (2) two comments in the copied body name `higyrus` and were kept verbatim on purpose — Plan 09 should decide once, for all five copies, whether to normalize them rather than let each executor choose; (3) the `_logging.py` region to hash is the text strictly between the two marker lines, which appear exactly once each in market-data as they do in higyrus.
- **Carried forward for Plan 06 / 07:** the `walk_field` → `walk_model` nested-model bypass is only harmless while no shipped model is another model's field type. market-data now asserts that precondition as a test; any package with nested models must either do the same or add the hook.
- **Carried forward for every remaining package:** the autouse pristine-decode-context fixture is mandatory, not hygiene, once the bind is live. Both new test modules here carry it.
- **No blockers.**

## Self-Check: PASSED

Created files verified present on disk: `packages/market-data-client/src/market_data_client/_decode.py`, `packages/market-data-client/tests/test_decode.py`, `packages/market-data-client/tests/test_decode_concurrency.py`. Modified files verified present: `models.py`, `exceptions.py`, `__init__.py`, `_state.py`, `_logging.py`, `client.py`, `aio.py`, `tests/test_logging.py`. All four task commits (`411a443`, `ef0049b`, `7c99dbf`, `77eeaab`) verified present in git history.

---
*Phase: 29-decoder-observable*
*Completed: 2026-08-19*
