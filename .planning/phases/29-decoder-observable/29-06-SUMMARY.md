---
phase: 29-decoder-observable
plan: 06
subsystem: api
tags: [decoder, observability, logging, contextvars, literal, redaction, security, dual-sync-async, tdd]

# Dependency graph
requires:
  - phase: 29-decoder-observable
    plan: 02
    provides: "The canonical `_decode.py` walker this plan copies verbatim, plus the carried-forward nested-model finding (`walk_field` calls `walk_model` directly, bypassing any per-model hook at the call site)"
  - phase: 29-decoder-observable
    plan: 03
    provides: "The `_ClientState` flag + four-entry-point + two-bind-site shape, the marker-delimited generic-scan region for `_logging.py`, and the autouse pristine-decode-context fixture requirement"
  - phase: 29-decoder-observable
    plan: 05
    provides: "The proven per-package recipe, the five-line `_decode.py` delta, the SILENT_SINK / call-site exemption pattern, and the precedent of asserting a structural precondition instead of adding a walker hook"
  - phase: 29-decoder-observable
    plan: 01
    provides: "29-SEMANTICS-MATRIX.md row 5 + Section 3(c), 29-AGGREGATION-CONTRACT.md (the 12 locks) and 29-DLOCK-RESPONSE-LITERAL.md (D-09)"
provides:
  - "`packages/matriz-client/src/matriz_client/_decode.py` — the third copy of the canonical walker, carrying the ONLY divergent `POLICY` constant of the five"
  - "`MatrizDecodeError(MatrizClientError)` — strict-mode decode divergence carrying field path and type names, never a wire value"
  - "matriz `models.py` delegating to the walker with all seven documented row-5 differences intact"
  - "`_is_mapping` / `_mapping_value` / `_apply_mapping_policy` — matriz's mapping axis, held at the call site so `_decode.py` stays byte-verbatim"
  - "`_ClientState.strict_decode: bool = False` + the kwarg on `Client.__init__`, `AsyncClient.__init__`, `client.configure`, `aio.configure` + both `_request` bind sites"
  - "The matriz `_logging.py` filter fix inside the marker-delimited region, placed AFTER the D-22 `auth_basic` pre-scan, with the ordering invariant tested two ways"
  - "The first executable proof that matriz's semantics survived the fan-out rather than being harmonized"
affects: [29-07, 29-08, 29-09, 30-iol-typed, 33-driver-runs]

actuals:
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "A per-package semantic axis the shared walker has no branch for lives in the call site's post-walk pass, never in the walker — the same lever Plan 05 used for market-data's model-level exemptions, applied here to a whole type shape"
    - "The post-walk pass takes the SAME sink the walker used, so strict mode, dedupe and lock 8's non-dict suppression all apply to it without re-deriving any of them"
    - "Asserting the absence of the higyrus constant (`dataclasses.astuple(POLICY) != higyrus_row`) as an executable form of the 'never harmonize' prohibition"
    - "Pinning a known, accepted behavioural delta as a test with the rationale in its docstring, rather than leaving it to be discovered as a regression"

key-files:
  created:
    - packages/matriz-client/src/matriz_client/_decode.py
    - packages/matriz-client/tests/test_decode.py
  modified:
    - packages/matriz-client/src/matriz_client/models.py
    - packages/matriz-client/src/matriz_client/exceptions.py
    - packages/matriz-client/src/matriz_client/__init__.py
    - packages/matriz-client/src/matriz_client/_state.py
    - packages/matriz-client/src/matriz_client/_logging.py
    - packages/matriz-client/src/matriz_client/client.py
    - packages/matriz-client/src/matriz_client/aio.py
    - packages/matriz-client/tests/test_logging.py
    - verification/snapshots/matriz-client-surface.txt

key-decisions:
  - "matriz declares four `dict[str, Any]` fields whose documented contract is 'missing dicts become `{}`'; the canonical walker has NO `dict` branch, because higyrus and market-data declare no mapping fields, so `walk_field` lands them on its bare pass-through and hands back `None`. Four pre-existing `test_models.py` assertions would have failed. The axis was implemented as a post-walk pass in `models.py` (`_apply_mapping_policy`) rather than a walker branch, because `_decode.py` is byte-verbatim across five copies (D-02) and Plan 09 hashes it."
  - "The mapping pass takes the SAME sink `walk_model` used — the emitting scope for a dict payload, `SILENT_SINK` for a non-dict one. That single argument is what makes lock 8 (non_dict is terminal), lock 5 (dedupe) and lock 4 (strict raises on missing/type) apply to the mapping axis without re-implementing any of them."
  - "matriz has an `aio.py` and therefore TWO bind sites, not one. Plan 03's carried-forward note said matriz has no async surface; that was true before Phase 10 Plan 10-02 grew the AsyncClient REST surface. The grep-count criterion is 1 per file, 2 total."
  - "matriz's `_decode.py` differs from higyrus in SIX lines below `from __future__`, not the five market-data has: the same five (exception import, its raise site, `_LOGGER_NAME`, two ContextVar names) plus `POLICY`, which is the whole point of this plan."
  - "An `int` arriving for a `float`-declared field now widens to `float` (`walk_field` coerces before consulting `scalar_passthrough`). This is the ONE observable delta outside the seven declared axes; it is numerically identity-preserving and agrees with the field's own annotation, and it is pinned by `test_int_into_a_float_field_widens_and_is_not_reported` rather than left unstated."
  - "The two `higyrus`-naming comments inside the copied body were kept VERBATIM, as Plan 05 did — even though `# higyrus has no ``empty()`` today` reads actively wrong sitting in the one package that does have `empty()`. Editing them would add differing lines and start eroding the invariant D-02 exists to protect. Plan 09 should normalize them once, for all five copies."

patterns-established:
  - "When the shared walker has no branch for a type shape one package declares, the branch goes in that package's call site and is handed the walker's own sink, so every lock keeps applying to it"
  - "A prohibition worth carrying in a plan's front matter is worth an assertion in the suite: `test_policy_is_not_the_higyrus_constant` fails the moment someone harmonizes a cell"
  - "A behavioural delta that is accepted rather than prevented gets a test whose docstring explains why it was accepted"

requirements-completed: [DEC-01]

coverage:
  - id: D1
    description: "matriz carries a verbatim copy of the walker; only the per-package deltas and the POLICY constant differ"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "diff <(sed '1,/^from __future__/d' higyrus/_decode.py) <(sed ... matriz/_decode.py) → 6 changed lines: the decode-error import, its raise site, `_LOGGER_NAME`, the two ContextVar name strings, and `POLICY`"
        status: pass
      - kind: test
        ref: "test_decode.py::test_all_exports_the_eleven_public_names, ::test_logger_name_is_this_package, ::test_context_var_names_are_package_prefixed, ::test_decode_module_never_imports_models"
        status: pass
    human_judgment: false
  - id: D2
    description: "matriz's POLICY differs from higyrus's on five of seven axes and is never harmonized"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_policy_constant_is_matriz_row_of_the_semantics_matrix (all seven fields asserted individually), test_policy_is_not_the_higyrus_constant (the prohibition, executable)"
        status: pass
      - kind: command
        ref: "`POLICY` prints `DecodePolicy(missing_str=None, missing_int=None, missing_float=None, missing_bool=None, non_dict_model='empty_classmethod', scalar_passthrough=True, literal_enforced=False)`; `POLICY.literal_enforced` prints `False`"
        status: pass
    human_judgment: false
  - id: D3
    description: "A missing scalar stays None, not a typed zero (difference 1)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_missing_scalar_is_none — asserts all four scalar axes return `None` AND explicitly asserts they are not `\"\"` / `0` / `0.0` / `False`"
        status: pass
    human_judgment: false
  - id: D4
    description: "A non-dict payload yields cls.empty() and emits exactly ONE record with no per-field missing records (difference 2 + lock 8)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_non_dict_returns_empty (equality with `cls.empty()` asserted, exactly one record, kind `non_dict`), test_none_payload_behaves_as_non_dict, test_empty_dict_is_a_dict_and_reports_per_field_missing, test_non_dict_path_reuses_the_empty_shape (four shipped classes)"
        status: pass
    human_judgment: false
  - id: D5
    description: "A missing nested model yields that model's empty(); scalars pass through unvalidated (differences 3 and 4)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_nested_missing_model_is_empty, test_wrong_typed_scalar_passes_through_and_reports, test_bool_payload_never_collapses_into_an_int_field"
        status: pass
    human_judgment: false
  - id: D6
    description: "The mapping axis: a dict-declared field with a non-mapping wire value returns {} and reports a type divergence"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_dict_hint_branch (declared_type `dict`, observed `str`), test_dict_hint_missing_key_returns_empty_mapping (kind `missing`), test_dict_hint_present_mapping_is_returned_verbatim (no record), test_shipped_mapping_fields_still_default_to_empty_dict (the four shipped fields test_models.py pins), test_strict_mode_raises_on_a_missing_mapping_field"
        status: pass
      - kind: test
        ref: "test_no_mapping_carrying_model_is_ever_a_nested_field_type — the precondition that makes a top-level-only pass complete"
        status: pass
    human_judgment: true
    rationale: "The precondition test proves no mapping-carrying model is TODAY another model's field type, which is what makes the call-site pass complete. It cannot prove a future plan will not nest one — but it fails loudly the moment that happens, which is the whole reason it exists. A human deciding to nest `InstrumentDetail` inside another model must move the pass into the walker or add a hook."
  - id: D7
    description: "empty() emits no divergence records, even with strict mode bound true (T-29-33)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_empty_emits_nothing (three module-local models, strict bound True, zero records), test_empty_is_silent_even_as_a_default_factory (two shipped models), test_strict_mode_does_not_make_empty_fatal"
        status: pass
    human_judgment: false
  - id: D8
    description: "The nine RESPONSE Literal aliases pass through unenforced; an out-of-set value is never fatal (D-09, T-29-31)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_literal_out_of_set_passes_through (5 aliases parametrized, asserts `returned is wire_value` — byte-identical by identity, not just equality), test_literal_out_of_set_does_not_raise_under_strict_mode (3 aliases), test_literal_wrong_runtime_type_reports (the asymmetry), test_literal_enforcement_is_off_for_all_nine_published_aliases (all nine, driven through `walk_field` directly)"
        status: pass
    human_judgment: false
  - id: D9
    description: "UnknownFrame is untouched, emits no extra records, and stays outside the SafeModel hierarchy (T-29-34)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_unknown_frame_untouched (whole payload retained, zero records), test_unknown_frame_is_not_a_safe_model, test_unknown_frame_still_does_not_report_under_strict_mode"
        status: pass
      - kind: command
        ref: "`git diff` on the `UnknownFrame` class shows a docstring paragraph added and nothing else — no field, default or method body changed"
        status: pass
    human_judgment: false
  - id: D10
    description: "The record is flat, all-str, top-level, type-not-value and never carries a wire value (T-29-29)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_record_is_flat_all_str_and_carries_no_wire_value (against a sentinel-built payload), test_contract_keys_avoid_every_reserved_logrecord_attribute, test_reserved_keys_emission_through_a_real_logger_call_does_not_raise, test_emitter_never_raises_into_the_decode_return_path"
        status: pass
    human_judgment: true
    rationale: "The test proves no emitted value equals a value in one sentinel payload and that the six keys are disjoint from the reserved set. It cannot prove that no future branch introduces a wire-carrying key — that guarantee is structural (every emitted string is a type name, a path, a package name, a model name or a kind) and needs a human reading `_emit` to confirm. Inherited unchanged from Plan 02, since the emitter is a byte-identical copy."
  - id: D11
    description: "The mode is reachable from all four public entry points, lands on the shared state, is inherited by views, and is bound at the top of both _request implementations with no reset"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_strict_mode_from_sync_constructor, ::_from_async_constructor, ::_from_sync_configure, ::_from_async_configure (the last two also assert Pitfall 5), test_strict_mode_view_inherits, test_strict_mode_is_not_env_backed, test_sync_request_binds_the_mode_and_a_fresh_scope, test_async_request_binds_the_mode_and_a_fresh_scope"
        status: pass
      - kind: command
        ref: "AST check: the first two statements of both `_request` bodies are `_decode.STRICT_DECODE.set(self._state.strict_decode)` and `_decode.open_request_scope()`; grep counts are 1 and 1 in each of `client.py` and `aio.py`"
        status: pass
    human_judgment: false
  - id: D12
    description: "The RedactingFilter fix sits AFTER the D-22 auth_basic pre-scan, and both shapes are handled in one pass (T-29-30)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_auth_basic_pre_scan_runs_before_the_generic_scan (one record carrying both shapes, one `filter()` call, tuple field replaced and nested leaf redacted), test_pre_scan_block_precedes_the_generic_scan_in_source (source line numbers + marker counts + the pre-scan being OUTSIDE the hashed region)"
        status: pass
      - kind: command
        ref: "`grep -n` — pre-scan at line 233, `_scan_record_dict(record)` at line 244; the marker-delimited region is BYTE-IDENTICAL to higyrus's (`diff` empty); `git diff` shows no hunk changing `_REDACTION_MARKERS` or any `_redact` pass"
        status: pass
    human_judgment: false
  - id: D13
    description: "A credential literal on the matriz decoder path reaches none of the three LogRecord surfaces"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_logging.py::test_decode_sentinel_never_leaks_credential (marker-FREE literal driven through a real `InstrumentDetail` decode, fresh scope so the dedupe set cannot make it vacuous, asserts >= 2 divergence records actually emitted, then all three surfaces plus `repr(record.__dict__)`)"
        status: pass
    human_judgment: true
    rationale: "The sentinel is a tripwire, not a proof: it shows one marker-free literal does not appear on the three surfaces for one divergent payload. The structural guarantee is lock 1's six all-str type-not-value keys, which a human must read `_emit` to confirm. Same posture as Plan 03's D9 and Plan 05's D8."
  - id: D14
    description: "The container recursion is bounded at depth 4 / 64 entries and preserves container type and object identity"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_nested_container_string_leaf_redacted, test_nested_list_and_tuple_leaves_redacted, test_untouched_containers_keep_object_identity, test_recursion_depth_bounded, test_wide_container_skipped (both sides of each bound)"
        status: pass
    human_judgment: false
  - id: D15
    description: "matriz's model suite stays green with no pre-existing test file modified"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "`git diff --numstat 32cc4a3 -- packages/{higyrus,matriz,market-data}-client/tests/` reports 7 paths, all `N  0` — ZERO deleted lines in every file; the only matriz paths are the new `test_decode.py` and the append to `test_logging.py`"
        status: pass
      - kind: test
        ref: "`uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q --no-cov` → 1074 passed (criterion asked for >= 872)"
        status: pass
    human_judgment: false

# Metrics
duration: 16min
completed: 2026-08-19
status: complete
---

# Phase 29 Plan 06: matriz keeps its own semantics Summary

**matriz now decodes through the same byte-verbatim walker as higyrus and market-data while returning exactly the values it returned before — `None` where the others substitute `""`, `cls.empty()` where the others substitute `{}`, wire scalars unvalidated, `UnknownFrame` untouched and the nine published `Literal` aliases still open — with the difference carried by a named policy constant that a test now asserts is *not* the higyrus one.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-08-19T12:36:40Z
- **Completed:** 2026-08-19T12:52:21Z
- **Tasks:** 3
- **Files modified:** 2 created, 9 modified

## Accomplishments

- **The one divergent copy is still a copy.** Below `from __future__`, matriz's `_decode.py` differs from the higyrus original in exactly six lines: the decode-error import, its `raise` site, `_LOGGER_NAME`, the two ContextVar name strings, and `POLICY`. Five of those are the same normalized deltas market-data carries; the sixth is the point of this plan. `__all__` matches higyrus's eleven names exactly.
- **The "never harmonize" prohibition is now executable.** `test_policy_constant_is_matriz_row_of_the_semantics_matrix` asserts each of the seven axes individually, and `test_policy_is_not_the_higyrus_constant` asserts the tuple as a whole differs from `("", 0, 0.0, False, "from_api_none", False, False)`. `test_missing_scalar_is_none` goes further and asserts the *absence* of the higyrus values (`obj.s != ""`, `obj.i != 0`, …) — the single most tempting cell to "fix" is now the one that fails loudest.
- **A whole type shape the walker has no branch for was found and handled without touching the walker.** matriz declares four `dict[str, Any]` fields (`InstrumentDetail.tickPriceRanges`, `DetailedPosition.report`, `AccountReport.detailedAccountReports` / `.portfolio`) whose documented contract is "missing dicts become `{}`". The canonical walker has no `dict` branch — higyrus and market-data declare no mapping fields — so `walk_field` lands such a value on its bare pass-through and returns `None`. Four pre-existing `test_models.py` assertions would have failed. The axis now lives in `models.py` as `_apply_mapping_policy`, a post-walk pass handed *the walker's own sink*, so strict mode, dedupe and lock 8's non-dict suppression all apply to it without a line of re-derivation.
- **`empty()` is silent, and that is load-bearing rather than cosmetic.** It is the nested-model default, the `default_factory` of six shipped fields, and the shape a non-dict payload converges on. Routing it through an emitting sink would produce one spurious record per field on every one of those calls. `test_empty_emits_nothing` binds strict mode `True` first, so it proves silence in the mode where a leak would be fatal rather than merely noisy.
- **The non-dict early return is gone as a code path and preserved as behaviour, and the equality is asserted rather than argued.** `POLICY.non_dict_model = "empty_classmethod"` makes the walker emit the single terminal `non_dict` record and produce the all-defaults kwargs; `cls(**kwargs)` is the same instance `empty()` builds. `test_non_dict_returns_empty` asserts `obj == _Nested.empty()` *and* that exactly one record fired, and `test_non_dict_path_reuses_the_empty_shape` repeats it on four shipped classes.
- **D-09 is proven by identity, not by equality.** `test_literal_out_of_set_passes_through` asserts `returned is wire_value` for five of the nine aliases — a coercion that happened to produce an equal string would still fail. A companion test binds strict mode and asserts three aliases still do not raise, and `test_literal_enforcement_is_off_for_all_nine_published_aliases` drives all nine through `walk_field` directly. The wrong-*runtime-type* case stays loud, which is the asymmetry the D-lock exists for.
- **`UnknownFrame` is exempt and the diff proves it.** The only change to the class is a docstring paragraph citing matrix Section 3(c); no field, default or method body moved. `test_unknown_frame_untouched` asserts the whole payload is retained and zero records fire, including under strict mode.
- **The D-22 ordering invariant survived and is now tested two ways.** The generic scan sits at line 244, the `auth_basic` pre-scan at line 233, and the marker-delimited region is byte-identical to higyrus's (`diff` empty). Beyond the line-order assertion, `test_auth_basic_pre_scan_runs_before_the_generic_scan` drives ONE record carrying both a credential tuple and a nested marker-bearing string leaf through ONE `filter()` call and asserts both are handled — which is the property the line order is a proxy for.
- **The zero-edit merge gate held across all three packages.** 1074 passed; `git diff --numstat` over the three test directories reports seven paths, every one of them `N  0`.

## Task Commits

Each task was committed atomically; Task 2's TDD gate sequence is explicit in the log:

1. **Task 1: walker copy + decode error + mode carrier + filter fix** — `f32bbae` (feat)
2. **Task 2 (RED): failing decode contract for matriz's divergent policy** — `69a034a` (test)
3. **Task 2 (GREEN): `models.py` delegates to the walker** — `919729a` (feat)
4. **Task 3: caplog sentinel + container recursion + pre-scan ordering** — `59ec8f4` (test)

## Files Created/Modified

- `packages/matriz-client/src/matriz_client/_decode.py` (446 lines, **created**) — the third copy of the canonical walker, carrying `POLICY = DecodePolicy(None, None, None, None, "empty_classmethod", True, False)`.
- `packages/matriz-client/src/matriz_client/exceptions.py` — adds `MatrizDecodeError(MatrizClientError)` with `field_path` / `declared_type` / `observed_type` / `model`. Deliberately **not** a subclass of `PrimaryAPIError`: the HTTP response succeeded *and* its envelope said `status == "OK"`; it is the payload shape that failed, so it carries no `status`/`description`. This file has no `__all__` (checked, per the plan's warning), so nothing else needed touching there.
- `packages/matriz-client/src/matriz_client/__init__.py` — re-exports it; the package `__all__` keeps its existing shape (two catalogue constants first, then one ASCII-sorted block) with `MatrizDecodeError` inserted between `MatrizClientError` and `NewOrderResponse`. `test_types.py`'s "every types-module name is in `__all__`" assertion is unaffected.
- `packages/matriz-client/src/matriz_client/_state.py` — `strict_decode: bool = False` after `client_max_retries`, a **plain** default with no `default_factory` despite every credential field above it using one, with the T-29-16 rationale in a source comment and a matching bullet in the module docstring's Notes list.
- `packages/matriz-client/src/matriz_client/client.py` — `strict_decode` kwarg on `Client.__init__` and `configure`; the two-statement bind at the top of `_request` with its no-reset rationale; `_decode` added to the package import. The module-level `_request` shim is untouched — it delegates through the method.
- `packages/matriz-client/src/matriz_client/aio.py` — the async mirror of all three changes, plus the note that each asyncio task carries its own ContextVar copy.
- `packages/matriz-client/src/matriz_client/models.py` (511 lines, was 396) — `_SafeModel.from_api` and `empty()` delegate to `walk_model`; `_convert` is a back-compat shim over `walk_field` with its **reversed** argument order intact; `_is_mapping` / `_mapping_value` / `_apply_mapping_policy` carry the mapping axis; `_strip_optional` and `_is_model` unchanged; `UnknownFrame` unchanged beyond a docstring paragraph. No model class body, field or default touched, and no `slots` added.
- `packages/matriz-client/src/matriz_client/_logging.py` — the marker-delimited generic-scan region, byte-identical to higyrus's, placed AFTER the D-22 pre-scan; the `filter()` call site carries the ordering rationale; the docstring gains the ordering-invariant paragraph and the "marker anchoring is deliberately unchanged" paragraph. `_REDACTION_MARKERS` and the `_redact` pass chain are byte-unchanged.
- `packages/matriz-client/tests/test_decode.py` (1041 lines, **created**) — 71 tests.
- `packages/matriz-client/tests/test_logging.py` (+209 lines, **0 deleted** — append-only, verified with `git diff --numstat`) — 8 new tests.
- `verification/snapshots/matriz-client-surface.txt` — regenerated by `verification/regen_snapshots.py`; four lines changed (`Client`, `AsyncClient`, `configure`, plus the new `MatrizDecodeError` entry). The other three package snapshots regenerated byte-identically.

## Decisions Made

- **The mapping axis lives at the call site, and takes the walker's sink.** Two mechanisms were available: a `dict` branch in `walk_field`, or a pass in `models.py`. The first breaks the byte-identity D-02 requires across five copies and that Plan 09 hashes; matrix Section 3 already blesses the second shape for market-data's two model-level exemptions. The non-obvious part is the sink argument: passing `SILENT_SINK` when the payload is not a dict is what keeps lock 8 true (a 204 body emits ONE record, not one per mapping field on top of it), and passing the live scope otherwise is what makes strict mode fatal on a missing mapping field exactly as it is on every other axis. Both halves are tested.
- **The mapping pass is top-level only, and the precondition is a test rather than a comment.** `walk_field` recurses into a nested model through `walk_model` directly, so the pass is bypassed for a mapping field on a model reached as another model's field type. `test_no_mapping_carrying_model_is_ever_a_nested_field_type` computes the two sets from the live class objects and asserts they are disjoint — the same discharge Plan 05 used for the nested-`from_api`-override finding. If a future plan nests `InstrumentDetail`, that test fails and the pass has to move.
- **`int` into a `float`-declared field now widens, and that is documented rather than hidden.** `walk_field`'s `float` branch returns `float(value)` for any `int | float` *before* it consults `scalar_passthrough`, so a wire `10` for `Order.orderQty` used to come back as `int` `10` and now comes back as `10.0`. It is numerically identical, it agrees with the field's own annotation, and Plan 02 signed the branch off deliberately (widening is a coercion, not a substituted default, which is why nothing is reported). But it *is* a type change on published surface and it is not one of the seven declared axes, so `test_int_into_a_float_field_widens_and_is_not_reported` pins it with the reasoning in its docstring. Flagged below for Phase 33.
- **The two `higyrus`-naming comments inside the copied body were kept verbatim**, matching Plan 05. One of them (`# higyrus has no ``empty()`` today`) reads actively wrong in the one package that *does* have `empty()`. Editing it would add differing lines and start the erosion of the verbatim-copy invariant. Plan 09 should decide once, for all five copies.
- **matriz has two bind sites, not one.** Plan 03's hand-off note said matriz has no `aio.py`; that stopped being true when Phase 10 Plan 10-02 grew the AsyncClient REST surface. Both `Client._request` and `AsyncClient._request` carry the bind, and the grep-count criterion is 1 per file.
- **The `configure` carry-forward is trivially satisfied here.** Unlike higyrus, matriz's `configure` mutates the default client's state in place rather than replacing the client, so the `None` sentinel is the whole implementation. Both `configure` tests still assert the Pitfall-5 sequence explicitly.
- **The sentinel literal carries no redaction marker**, matching Plans 03 and 05: a marker-bearing sentinel would be rescued by `_redact` and the test would silently become a filter test.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] The canonical walker has no `dict` branch; matriz declares four mapping fields**

- **Found during:** Task 2, while reading `models.py` against `_decode.py`.
- **Issue:** `walk_field` branches on `Union`, `list`, nested model, `str`, `bool`, `int`, `float` and `Literal`, then falls through to `return value`. `get_origin(dict[str, Any]) is dict` matches none of them, so a mapping-declared field returned the raw wire value — `None` when the key was absent. matriz's `_convert` had an explicit `if origin is dict: return value if isinstance(value, dict) else {}` branch, and four pre-existing `test_models.py` assertions depend on it (`test_instrument_detail_accepts_partial_payload`, `test_detailed_position_accepts_partial_payload`, `test_account_report_accepts_partial_payload`). The plan anticipated the behaviour — its `<behavior>` list names a `dict_hint_branch` test — but not that the walker would have no branch to produce it.
- **Fix:** `_is_mapping` / `_mapping_value` / `_apply_mapping_policy` in `models.py`, called after `walk_model` in both `from_api` and `empty()`, taking the same sink the walker used. `_convert` keeps the branch inline for its single-hint case. `_decode.py` is untouched.
- **Why not a walker branch:** D-02 requires the five copies to stay byte-verbatim and Plan 09 hashes the file; a matriz-only branch there would be the first crack in that invariant, and matrix Section 3 already establishes the call site as the sanctioned lever for a per-package semantic the policy constant cannot carry.
- **Files modified:** `packages/matriz-client/src/matriz_client/models.py`, `packages/matriz-client/tests/test_decode.py`
- **Commit:** `919729a`

**2. [Rule 3 - Blocking] mypy strict rejects `type[Any]` against `lru_cache`'s `Hashable` parameter**

- **Found during:** Task 2 (GREEN), on `uv run mypy packages/matriz-client/src`.
- **Issue:** `_apply_mapping_policy` calls `_decode.hints_for(cls)`; mypy reported `Argument 1 to "__call__" of "_lru_cache_wrapper" has incompatible type "type[Any]"; expected "Hashable"`. Identical to the error Plan 02 hit inside `walk_model`.
- **Fix:** the same discipline the walker already uses — `target = cast(Any, cls)`, bound once and reused for `hints_for` and `fields`. **No `type: ignore` comment was introduced.**
- **Files modified:** `packages/matriz-client/src/matriz_client/models.py`
- **Commit:** `919729a`

**3. [Rule 1 - Bug] Ruff RUF002 on a multiplication sign in a new docstring**

- **Found during:** Task 1, on `uv run ruff check .`.
- **Issue:** the `_logging.py` docstring heading read `**Ordering invariant (D-22 × Phase 29).**`; RUF002 flags the ambiguous `×`.
- **Fix:** replaced with `+`. No semantic change.
- **Files modified:** `packages/matriz-client/src/matriz_client/_logging.py`
- **Commit:** `f32bbae`

### Clarifications to acceptance criteria

**1. The `_decode.py` diff is six lines, not the "at most five" the criterion enumerates.** The criterion lists the logger name, the two ContextVar names, the decode-error import and `POLICY`; the exception *symbol* also appears at its `raise` site, which Plan 05 already flagged. Six is the correct count for matriz and five for market-data, and the difference is `POLICY` — the whole subject of this plan.

**2. The module docstring delta is three lines, not two.** market-data changed two docstring lines (the title and the `Who imports it:` line). matriz changed a third, because the sentence names `SafeModel.from_api` and the `_coerce` shim, and matriz's are `_SafeModel.from_api` and `_convert`. The docstring sits above `from __future__` and is therefore outside the compared region; accuracy was preferred to symmetry there. The two `higyrus`-naming comments *inside* the compared body were left verbatim.

**3. The plan says "matriz has ONE bind site, not two: no aio.py".** That note came from Plan 03 and predates Phase 10 Plan 10-02. matriz has an `aio.py` with a full `AsyncClient` REST surface, so there are two bind sites and the grep count is 1 per file.

---

**Total deviations:** 3 auto-fixed (one Rule 2, one Rule 3, one Rule 1). Three acceptance-criterion clarifications, all documented above.
**Impact on plan:** None on scope — every file touched is in the plan's `files_modified` list. The Rule 2 fix added three private helpers to `models.py` that the plan did not enumerate; they are the minimum needed to keep four documented behaviours and four pre-existing test assertions true.

## Issues Encountered

- The RED run's first draft used a nested `X-Auth-Token` dict **key** with a marker-free value, which the marker-anchored filter correctly leaves alone — the test was wrong, not the filter. Corrected to put the marker in the string leaf itself, which is what the redaction contract actually covers.
- `ruff` flagged `SIM300` (Yoda condition) and `PT019` (fixture injected as a parameter) on the first draft of the new suite; both were mechanical fixes before the RED commit.

## Verification

- `uv run pytest packages/matriz-client -q --no-cov` — **393 passed** (322 pre-existing + 71 new in `test_decode.py`; `test_logging.py`'s 8 land in Task 3).
- `uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q --no-cov` — **1074 passed** (criterion asked for >= 872).
- `uv run pytest packages/matriz-client/tests/test_decode.py packages/matriz-client/tests/test_logging.py -q --no-cov` — 92 passed.
- `uv run pytest verification/test_public_surface.py -q --no-cov` — 4 passed against the regenerated snapshot; `git status --porcelain verification/snapshots/` showed only `matriz-client-surface.txt`.
- `uv run mypy packages/matriz-client/src` — Success: no issues found in 17 source files.
- `uv run ruff check .` — All checks passed. `uv run ruff format --check .` — 209 files already formatted.
- `uv run lint-imports` — Contracts: 4 kept, 0 broken.
- `diff <(sed '1,/^from __future__/d' higyrus/_decode.py) <(sed '1,/^from __future__/d' matriz/_decode.py)` — 6 changed lines, enumerated above.
- `sorted(matriz_client._decode.__all__) == sorted(higyrus_client._decode.__all__)` — True, the eleven public names.
- `POLICY` — `DecodePolicy(missing_str=None, missing_int=None, missing_float=None, missing_bool=None, non_dict_model='empty_classmethod', scalar_passthrough=True, literal_enforced=False)`. `POLICY.literal_enforced` — `False`.
- `grep -c '_decode\.STRICT_DECODE\.set'` — 1 in `client.py`, 1 in `aio.py`; same counts for `_decode.open_request_scope`. An AST check confirms both are the first two statements of each `_request` body (docstring excluded), neither in a `finally`.
- `inspect.signature(...)` — `strict_decode` present in `Client`, `AsyncClient`, `matriz_client.configure` and `matriz_client.aio.configure`: four `True`.
- `dataclasses.fields(_ClientState)` — `strict_decode` has `default is False` and `default_factory is MISSING`.
- `len(inspect.signature(models._SafeModel.from_api).parameters)` — **1**, and the parameter is still named `data`.
- `list(inspect.signature(models._convert).parameters)` — `['tp', 'value']` — the reversed order is unchanged.
- **Pre-scan ordering (recorded per the plan's acceptance criterion):** in `packages/matriz-client/src/matriz_client/_logging.py`, `if "auth_basic" in record.__dict__:` is at **line 233** and `_scan_record_dict(record)` is at **line 244**. 233 < 244. The marker lines `decode-intactness: generic-scan begin` / `... end` appear exactly once each, and the pre-scan is outside that region — asserted by `test_pre_scan_block_precedes_the_generic_scan_in_source` as well as by the greps.
- `diff` of the marker-delimited region against higyrus's — **empty** (byte-identical).
- `git diff` on `_logging.py` shows no hunk touching `_REDACTION_MARKERS` or any `_redact` pass; the only lines mentioning `_REDACTION_MARKERS` are the new helper and the removed old loop condition.
- `git diff` on the `UnknownFrame` class — a docstring paragraph added, nothing else.
- Zero-edit gate, asserted mechanically: `git diff --numstat 32cc4a3 -- packages/{higyrus,matriz,market-data}-client/tests/` reports 7 paths, all with **0 deleted lines**; the matriz entries are `1041  0` (new `test_decode.py`) and `209  0` (append to `test_logging.py`).
- `git diff --diff-filter=D --name-only 32cc4a3..HEAD` — empty; no files deleted.
- `MatrizDecodeError` importable from `matriz_client`, present in `__all__`, and the sorted block of `__all__` verified still ASCII-sorted.

## Prohibitions status

Both plan prohibitions were carried as `flagged-unverified` and are now satisfied:

- *"The walker must NEVER enforce `Literal` membership on matriz's response fields."* — Satisfied structurally and tested four ways. `POLICY.literal_enforced is False`, the walker's `Literal` branch computes `member_ok = value in args if policy.literal_enforced else True`, and the suite asserts (a) five aliases return the wire object **by identity** for an out-of-set value, (b) three of them do not raise under a bound strict mode, (c) all nine are `str`-valued and pass an out-of-set string through `walk_field` unchanged, and (d) a wrong *runtime* type still reports. Confirmed on the source, as the plan asked: matriz's old `_convert` ended in a bare `return value` for these fields (`models.py:92` pre-change), so the change here is **reporting-only** and returns no different value.
- *"matriz's decode semantics must NEVER be harmonized toward the higyrus defaults."* — Satisfied by construction and asserted. Five of the seven policy fields differ; `test_policy_is_not_the_higyrus_constant` fails the moment any cell is harmonized; `test_missing_scalar_is_none` asserts the negative form (`!= ""`, `!= 0`, …) rather than only the positive one; and the four axis-specific tests (null missing-scalar, empty-constructor non-dict, empty nested model, mapping branch) each pin one row. The 1074-test zero-edit merge gate is the mechanical counterpart. The one behavioural delta that *did* appear — `int` widening into a `float`-declared field — is outside the seven axes, is not a harmonization of any matrix cell, and is pinned by its own test with the rationale in the docstring.

## TDD Gate Compliance

Task 2 was the plan's `tdd="true"` task and its gate sequence is present and correctly ordered in git history: RED `69a034a` `test(...)` → GREEN `919729a` `feat(...)`. The RED run reported **24 failed / 46 passed** — the failures were exactly the delegation assertions (no divergence record is emitted while `models.py` still carries its own `_convert` copy), while the walker-surface, `empty()`-silence and `UnknownFrame` rows were already green, so nothing passed by accident. No REFACTOR gate was needed. Tasks 1 and 3 are not TDD tasks (a file copy plus wiring, and a test-only append).

## Known Stubs

None. Every symbol this plan touched is on a live path: both bind sites run on every request, `_scan_record_dict` runs on every log record, `strict_decode` is read by the bind, and `_apply_mapping_policy` runs on every `from_api` and every `empty()`. `SILENT_SINK` is *not* a stub in matriz — unlike higyrus and market-data it is referenced by production code here, in `empty()` and in the non-dict branch of `from_api`.

## Threat Flags

None. This plan adds no network endpoint, no auth path, no file access and no schema at a trust boundary. The three boundaries it does touch (upstream JSON → walker, walker → `logging.getLogger("matriz_client")`, published `Literal` surface → consumers) are the plan's own T-29-29 through T-29-35, each with a named mitigation and a test above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Wave 4 continues unblocked.** The per-package recipe is now proven three times. matriz was the one package where it needed a genuine addition, and the addition is confined to the call site.
- **Carried forward for Plan 07 (iol / ámbito), and it matters more there than it looks:** the canonical walker has **no `dict` branch**. Neither iol nor ámbito has a `models.py` today, so the copy is inert in both — but **Phase 30 must not write a `dict[...]`-typed model field without deciding what that field should do when the wire disagrees.** Under the walker as it stands the answer is "return the raw value, report nothing".
- **Carried forward for Plan 09 (intactness gate), four items:** (1) matriz's copy differs in **six** lines, market-data's in five and the extra one is `POLICY` — the normalizer must handle a `POLICY` line that genuinely differs, not just a package-name substitution; (2) the exception symbol appears at two sites, so normalize the name and not just the import statement; (3) the two `higyrus`-naming comments inside the copied body were kept verbatim in both fan-out packages — decide once, for all five; (4) matriz's `_logging.py` marker region is byte-identical to higyrus's with the D-22 pre-scan sitting outside it, which is the case the marker design was introduced for and is now confirmed working.
- **Carried forward for Plan 08 (matriz websocket), with Plan 05's evidence now directly applicable:** a plain `threading.Thread` sees the ContextVar DEFAULT. matriz's WS daemon thread therefore cannot inherit the REST client's mode and must bind it explicitly. Note also that `ws_client.py` dispatches to `UnknownFrame` for unmodeled frames, which is exempt from reporting entirely — so a WS decode-mode bind only affects `MarketDataFrame` / `ExecutionReportFrame`.
- **Carried forward for Phase 33 (driver runs):** `int` → `float` widening on `float`-declared matriz fields is live as of this plan. Any live-response comparison that checks `type(value)` rather than `value ==` will see it. It is pinned by `test_int_into_a_float_field_widens_and_is_not_reported`, not by a policy axis, so a future decision to preserve the old `int` would need its own artifact.
- **Carried forward for anyone nesting matriz models:** `test_no_mapping_carrying_model_is_ever_a_nested_field_type` fails if `InstrumentDetail`, `DetailedPosition` or `AccountReport` is ever declared as another model's field type. That failure is the signal to move `_apply_mapping_policy` into the walker rather than to weaken the test.
- **No blockers.**

## Self-Check: PASSED

Created files verified present on disk: `packages/matriz-client/src/matriz_client/_decode.py`, `packages/matriz-client/tests/test_decode.py`. Modified files verified present: `models.py`, `exceptions.py`, `__init__.py`, `_state.py`, `_logging.py`, `client.py`, `aio.py`, `tests/test_logging.py`, `verification/snapshots/matriz-client-surface.txt`. All four task commits (`f32bbae`, `69a034a`, `919729a`, `59ec8f4`) verified present in git history.

---
*Phase: 29-decoder-observable*
*Completed: 2026-08-19*
