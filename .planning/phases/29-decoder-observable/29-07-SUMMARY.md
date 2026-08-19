---
phase: 29-decoder-observable
plan: 07
subsystem: api
tags: [decoder, observability, logging, contextvars, redaction, security, dual-sync-async, fan-out]

# Dependency graph
requires:
  - phase: 29-decoder-observable
    plan: 02
    provides: "The canonical `_decode.py` walker this plan copies verbatim into the two packages that have no models module"
  - phase: 29-decoder-observable
    plan: 03
    provides: "The `_ClientState` flag + four-entry-point + two-bind-site shape, the marker-delimited generic-scan region for `_logging.py`, and the autouse pristine-decode-context fixture requirement"
  - phase: 29-decoder-observable
    plan: 05
    provides: "The proven per-package recipe, the five-line `_decode.py` delta (exception symbol at BOTH the import and the raise site), and the `higyrus`-naming comments kept verbatim"
  - phase: 29-decoder-observable
    plan: 06
    provides: "The confirmation that the walker has NO dict branch (carried forward to Phase 30), and the two-bind-site count per package"
  - phase: 29-decoder-observable
    plan: 01
    provides: "29-SEMANTICS-MATRIX.md rows 4 and 5 (iol and ambito carry the higyrus constant; iol's is re-ratified in Phase 30) and 29-AGGREGATION-CONTRACT.md (the 12 locks)"
provides:
  - "`packages/iol-client/src/iol_client/_decode.py` — the fourth copy of the canonical walker, landing BEFORE the models it will serve"
  - "`packages/ambito-financiero-client/src/ambito_financiero_client/_decode.py` — the fifth and final copy, dormant by design"
  - "`IOLDecodeError(IOLClientError)` and `AmbitoFinancieroDecodeError(AmbitoFinancieroClientError)`"
  - "`_ClientState.strict_decode: bool = False` in both packages + the kwarg on eight public entry points + four `_request` bind sites"
  - "Both `_logging.py` filter fixes inside the marker-delimited region Plan 09 will hash"
  - "The executable proof that the walker stands alone in a package with no `models.py` — the property that makes the verbatim-copy contract enforceable at all"
  - "The formatter-reflow finding: substituting the ContextVar name changes LINE COUNT in BOTH directions across the five copies"
affects: [29-08, 29-09, 30-iol-typed, 33-driver-runs]

actuals:
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "A locally declared frozen slotted dataclass with a `from_api` classmethod delegating to `walk_model` is a complete stand-in for a models module — it exercises every walker branch, including the duck-typed `_is_model` predicate, without one existing"
    - "Landing infrastructure one phase ahead of its consumer, and proving it functional there, so the consuming phase inherits a working component instead of bootstrapping one mid-phase"
    - "Asserting the ABSENCE of a module (`test_this_package_really_has_no_models_module`) as the precondition that makes a standalone-import claim meaningful"
    - "A per-package `_state` field-name-set assertion pinning a documented structural divergence (ambito's B7 no-token shape) against accidental cross-package drift"

key-files:
  created:
    - packages/iol-client/src/iol_client/_decode.py
    - packages/iol-client/tests/test_decode.py
    - packages/ambito-financiero-client/src/ambito_financiero_client/_decode.py
    - packages/ambito-financiero-client/tests/test_decode.py
  modified:
    - packages/iol-client/src/iol_client/exceptions.py
    - packages/iol-client/src/iol_client/__init__.py
    - packages/iol-client/src/iol_client/_state.py
    - packages/iol-client/src/iol_client/_logging.py
    - packages/iol-client/src/iol_client/client.py
    - packages/iol-client/src/iol_client/aio.py
    - packages/iol-client/tests/test_logging.py
    - packages/ambito-financiero-client/src/ambito_financiero_client/exceptions.py
    - packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py
    - packages/ambito-financiero-client/src/ambito_financiero_client/_state.py
    - packages/ambito-financiero-client/src/ambito_financiero_client/_logging.py
    - packages/ambito-financiero-client/src/ambito_financiero_client/client.py
    - packages/ambito-financiero-client/src/ambito_financiero_client/aio.py
    - packages/ambito-financiero-client/tests/test_logging.py
    - verification/snapshots/iol-client-surface.txt
    - verification/snapshots/ambito-financiero-client-surface.txt

key-decisions:
  - "**The `ruff format` reflow is a real, bidirectional delta and it is now the headline hand-off to Plan 09.** Substituting the package name into the two ContextVar declarations changes the LINE COUNT of the file, in opposite directions at the two ends of the name-length spectrum. `iol_client` is short enough that `DECODE_SCOPE` collapses from three lines to one; `ambito_financiero_client` is long enough that `STRICT_DECODE` expands from one line to three. Both are forced by CI's `ruff format --check .`, neither is avoidable, and a normalizer that substitutes the name then compares byte-for-byte would report a false divergence on BOTH copies. Pinned by a test in each package."
  - "Both copies carry the higyrus POLICY constant verbatim, per matrix rows 4 and 5. iol's is re-ratified in Phase 30; ambito's is expected to stay inert indefinitely — which is exactly why it is pinned by a test rather than assumed, since nothing in production would fail if it drifted."
  - "The fixture dataclasses are declared in the TEST files, never in `src/`. iol will get real models in Phase 30 and a placeholder in `src/` would have to be deleted then; ambito is not scheduled to get any. Declaring them test-locally also means a future shipped model cannot turn a walker regression green."
  - "ambito's `configure` REPLACES the default client rather than mutating it in place (unlike iol, higyrus and matriz), so the `None`-sentinel carry-forward had to read the prior client's `_state.strict_decode` explicitly. Both halves — the opt-in and the non-reset — are asserted."
  - "The two `higyrus`-naming comments inside the copied body were kept VERBATIM in both packages, matching Plans 05 and 06. `# higyrus has no ``empty()`` today` now sits in four of the five copies reading as commentary about a different package. Plan 09 should normalize them once, for all five."
  - "`AmbitoFinancieroDecodeError` is deliberately distinct from `AmbitoFinancieroNoDataError`, and the test says why: that package already has an error meaning 'the request was fine, the answer is empty' (weekend / holiday / future date). Conflating a malformed payload with a market-calendar gap would make a shape bug look like normal operation."

patterns-established:
  - "Prove a copied component works in the package with the FEWEST surrounding dependencies — the absence of a models module is evidence no amount of testing in a package that has one could produce"
  - "When a mechanical transformation is subject to an auto-formatter, the transformation's output shape is not a function of the substitution alone; pin the resulting shape per package and hand the finding to whoever writes the checker"
  - "A dormant artifact gets a behaviour suite, not just an intactness hash: the gate proves it is unchanged, only the suite proves it still works"

requirements-completed: [DEC-01]

coverage:
  - id: D1
    description: "Both copies differ from the canonical body only in the normalized per-package lines"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "`diff <(sed '1,/^from __future__/d' higyrus/_decode.py) <(sed ... iol/_decode.py)` → 5 changed lines in 4 hunks: the decode-error import, its raise site, `_LOGGER_NAME`, and the two ContextVar names (the second collapsed 3→1 by the formatter). Same for ambito, with `STRICT_DECODE` expanded 1→3 instead. `POLICY` byte-identical in both."
        status: pass
      - kind: test
        ref: "test_decode.py::test_all_exports_the_eleven_public_names, ::test_policy_constant_matches_the_semantics_matrix, ::test_logger_name_is_this_package, ::test_context_var_names_are_package_prefixed (both packages)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The walker imports nothing from a models module and stands alone in a package that has none"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_decode_module_never_imports_models (AST scan; package imports == {`<pkg>.exceptions`}), test_this_package_really_has_no_models_module (asserts `models.py` absent on disk AND `import <pkg>.models` raises ModuleNotFoundError) — both packages"
        status: pass
      - kind: command
        ref: "`python -c 'import iol_client._decode'` and the ambito equivalent both succeed"
        status: pass
    human_judgment: false
  - id: D3
    description: "The five divergence classes decode correctly in both modes in each package, on locally declared fixtures"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_missing_scalars_return_typed_zeros_and_report, test_missing_list_field_returns_empty_list_and_reports, test_wrong_typed_scalar_returns_default_and_reports_type, test_bool_payload_never_collapses_into_an_int_field, test_extra_wire_key_reports_at_info_and_leaves_the_model_untouched, test_non_dict_payload_emits_one_record_and_suppresses_per_field_missing, test_none_payload_behaves_as_non_dict, test_empty_dict_is_a_dict_and_reports_per_field_missing (both packages)"
        status: pass
      - kind: test
        ref: "test_strict_mode_raises_with_the_exact_field_path_and_no_wire_value, ::_raises_on_missing, ::_raises_on_non_dict, ::_never_raises_on_an_extra_wire_key (lock 4, both packages)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The `from_api` shape a typed surface will take is proven functional, not merely present"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_from_api_shape_decodes_a_clean_payload_without_a_single_record, ::_reports_a_missing_float_and_still_substitutes, ::_nested_path_is_dotted_from_the_decode_root, ::_is_fatal_under_strict_mode — four tests per package driving a `from_api` classmethod that delegates to `walk_model`"
        status: pass
    human_judgment: false
  - id: D5
    description: "The record is flat, all-str, top-level, type-not-value and never carries a wire value (T-29-36)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_record_is_flat_all_str_and_carries_no_wire_value (sentinel-built payload), test_contract_keys_avoid_every_reserved_logrecord_attribute, test_reserved_keys_emission_through_a_real_logger_call_does_not_raise, test_emitter_never_raises_into_the_decode_return_path (both packages)"
        status: pass
    human_judgment: true
    rationale: "The test proves no emitted value equals a value in one sentinel payload and that the six keys are disjoint from the reserved set. It cannot prove no future branch introduces a wire-carrying key — that guarantee is structural (every emitted string is a type name, a path, a package name, a model name or a kind) and needs a human reading `_emit`. Inherited unchanged from Plan 02, since the emitter is a byte-identical copy."
  - id: D6
    description: "Strict mode is reachable from eight public entry points across the two packages and bound at four `_request` methods with no reset"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_strict_mode_from_constructor, ::_from_configure (also asserts Pitfall 5), ::_view_inherits, ::_is_not_env_backed, ::_bound_by_request, ::_bound_by_module_shim, test_async_request_binds_mode, test_no_reset_after_request, test_request_binds_a_fresh_scope_per_response — both packages"
        status: pass
      - kind: command
        ref: "`inspect.signature` reports `strict_decode` in `Client`, `AsyncClient`, `<pkg>.configure` and `<pkg>.aio.configure` — eight `True`. `grep -c '_decode\\.STRICT_DECODE\\.set'` is 1 in each of the four files; same for `open_request_scope`."
        status: pass
    human_judgment: false
  - id: D7
    description: "D-09: `Literal` membership is never enforced on a RESPONSE field, in either copy"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_literal_membership_is_never_enforced, test_literal_out_of_set_value_is_returned_by_identity (asserts `returned is wire_value`), test_literal_reports_a_wrong_runtime_type (the asymmetry), test_literal_membership_is_not_enforced_under_strict_mode — both packages; `POLICY.literal_enforced is False` asserted in both"
        status: pass
    human_judgment: false
  - id: D8
    description: "The RedactingFilter fix ships to both copies with the same bounded recursion, and the marker sets are untouched"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "`diff` of the text between `decode-intactness: generic-scan begin` / `end` against higyrus's — EMPTY (byte-identical) in both packages. `git diff` on each `_logging.py` shows no hunk touching `_REDACTION_MARKERS` or any `_redact` pass."
        status: pass
      - kind: test
        ref: "test_nested_container_string_leaf_redacted, test_nested_list_and_tuple_leaves_redacted, test_untouched_containers_keep_object_identity, test_recursion_depth_bounded, test_wide_container_skipped, test_marker_tuple_and_redaction_chain_are_untouched_by_phase_29 — six per package"
        status: pass
    human_judgment: false
  - id: D9
    description: "A credential literal on either decoder path reaches none of the three LogRecord surfaces"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_logging.py::test_decode_sentinel_never_leaks_credential in both packages (marker-FREE literal driven through a real `_decode.walk_model` call, fresh scope so the dedupe set cannot make it vacuous, asserts >= 2 divergence records actually emitted, then all three surfaces plus `repr(record.__dict__)`)"
        status: pass
    human_judgment: true
    rationale: "The sentinel is a tripwire, not a proof: it shows one marker-free literal does not appear on the three surfaces for one divergent payload. The structural guarantee is lock 1's six all-str type-not-value keys, which a human must read `_emit` to confirm. Same posture as Plans 03, 05 and 06."
  - id: D10
    description: "Exactly two snapshot files changed and no pre-existing test file was edited"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "`git diff --name-only d0b0089 -- verification/snapshots/` reports exactly `iol-client-surface.txt` and `ambito-financiero-client-surface.txt`. `git diff --numstat d0b0089 -- packages/{iol,ambito-financiero}-client/tests/` reports 3 paths, all `N  0` — zero deleted lines. `git diff --diff-filter=D` across both commits is empty."
        status: pass
      - kind: test
        ref: "`uv run pytest packages -q --no-cov` → 1465 passed across all five packages"
        status: pass
    human_judgment: false
  - id: D11
    description: "ambito's B7 structural divergence (no token fields, no token lock) survives the fan-out"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_state_still_has_no_token_fields — asserts the field-name set is exactly {base_url, user_agent, strict_decode, http_client}, so a future change that dragged the iol/higyrus token shape across fails loudly"
        status: pass
      - kind: command
        ref: "`git diff` on `aio.py` shows the bind added and no locking construct introduced or moved"
        status: pass
    human_judgment: false

# Metrics
duration: 22min
completed: 2026-08-19
status: complete
---

# Phase 29 Plan 07: The walker stands alone Summary

**iol and ámbito now carry the same byte-verbatim decode walker as the three packages that have models — and neither of them has a models module, which is the point: a walker that imports cleanly, decodes correctly and reports divergences in a package with no `models.py` beside it is the strongest available evidence that the module has no hidden coupling to one, and that is what makes the verbatim-copy contract enforceable everywhere else.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-08-19T13:05:00Z
- **Completed:** 2026-08-19T13:27:00Z
- **Tasks:** 2
- **Files modified:** 4 created, 16 modified

## Accomplishments

- **The copy topology is five packages, and the fifth one is dormant on purpose.** ámbito's public surface is one function returning a `float`. Nothing in `src/` will ever call `walk_model` there. The copy exists so the Plan 09 intactness gate has five copies with one canonical shape to normalize to — and because a dormant artifact with only a hash behind it rots quietly. It has a 53-test behaviour suite for exactly that reason: the gate proves it is unchanged, only the suite proves it still works.
- **iol receives its decoder one phase before it receives its models, and the decoder is already proven.** Phase 30 will write `iol_client/models.py` against a walker that has 52 passing tests against it, rather than bootstrapping one mid-phase. The test fixtures are `from_api`-carrying frozen slotted dataclasses — the exact shape Phase 30 will generate — so the delegation contract is pinned before the first real model exists.
- **The standalone-import property is asserted twice, positively and negatively.** `test_decode_module_never_imports_models` walks the AST and asserts the only in-package import is `<pkg>.exceptions`. `test_this_package_really_has_no_models_module` asserts `models.py` is absent from disk *and* that `import <pkg>.models` raises `ModuleNotFoundError`. The second is what makes the first meaningful — without it, "no models import" would be a claim about a file, not about the package.
- **A formatter reflow was found that no prior plan could have seen, and it cuts both ways.** Substituting the package name into the two `ContextVar` declarations changes the file's **line count**, in *opposite directions* at the two ends of the name-length spectrum. `iol_client` is short enough that the three-line `DECODE_SCOPE` call collapses to one; `ambito_financiero_client` is long enough that the one-line `STRICT_DECODE` assignment expands to three. Neither is optional — CI runs `ruff format --check .` — and neither has anything to do with the walker. Plans 05 and 06 could not have hit this: `market_data_client` and `matriz_client` both sit in the middle of the range. Pinned by a test in each package and carried forward below.
- **Strict mode is reachable from eight public entry points and bound at four `_request` methods.** Both constructors, both `configure` functions, in both packages, all using the `None`-sentinel carry-forward. ámbito needed the non-obvious half: its `configure` *replaces* the default client rather than mutating it, so the carry-forward reads the prior client's `_state.strict_decode` explicitly — and the Pitfall-5 test (`configure(base_url=...)` must not reset a previous opt-in) is what proves it does.
- **ámbito's deliberate B7 divergence survived the fan-out and is now mechanically pinned.** That package has no token fields and no token lock — no auth means no refresh race. `test_state_still_has_no_token_fields` asserts the field-name set is exactly the four it should be, so a future change that dragged the iol/higyrus token shape across during a decode-carrier edit fails loudly. The async bind adds no locking of its own.
- **Both filter fixes are byte-identical to higyrus's inside the marker region**, with both marker tuples and both `_redact` pass chains untouched — asserted by `diff` on the region *and* by a per-package pattern-isolation test (iol must not grow `_CUIT_QUERY_RE`; ámbito must not grow `_REFRESH_TOKEN_*`).
- **1465 tests pass across all five packages**, with zero deleted lines in every pre-existing test file and exactly two snapshot files changed.

## Task Commits

1. **Task 1: iol — walker copy, decode error, mode carrier, filter fix, tests** — `6a6e105` (feat)
2. **Task 2: ámbito — walker copy, decode error, mode carrier, filter fix, tests** — `610c9e9` (feat)

## Files Created/Modified

**iol-client**

- `src/iol_client/_decode.py` (448 lines, **created**) — the fourth copy. Docstring adapted to state that nothing imports it yet and why the copy arrives before its consumer.
- `src/iol_client/exceptions.py` — adds `IOLDecodeError(IOLClientError)` with `field_path` / `declared_type` / `observed_type` / `model`. Not a subclass of `IOLAPIError`: the HTTP response succeeded, so it carries no `status_code`. This file has no `__all__`.
- `src/iol_client/__init__.py` — re-exports it; `__all__` stays ASCII-sorted.
- `src/iol_client/_state.py` — `strict_decode: bool = False` after `password`, a plain default with the T-29-16 rationale in a source comment and a matching paragraph in the module docstring. The three fields above it all use `default_factory`, which is what makes the deviation worth commenting.
- `src/iol_client/client.py` / `aio.py` — the kwarg on both constructors and both `configure` functions (both mutate the default client's state in place, so the `None` sentinel is the whole implementation); the two-statement bind at the top of both `_request` methods with the no-reset rationale; `_decode` added to the package import. Neither module-level `_request` shim binds — they delegate through the method.
- `src/iol_client/_logging.py` — the marker-delimited generic-scan region, byte-identical to higyrus's; docstring gains the D-05(a) and D-05(b) paragraphs. `_REDACTION_MARKERS` and the `_redact` chain byte-unchanged.
- `tests/test_decode.py` (1045 lines, **created**) — 52 tests.
- `tests/test_logging.py` (+189 lines, **0 deleted**) — 7 new tests.
- `verification/snapshots/iol-client-surface.txt` — four lines changed (`Client`, `AsyncClient`, `configure`, plus the new `IOLDecodeError`).

**ambito-financiero-client**

- `src/ambito_financiero_client/_decode.py` (453 lines, **created**) — the fifth copy. Five more lines than iol's because the formatter splits `STRICT_DECODE` here.
- `src/ambito_financiero_client/exceptions.py` — adds `AmbitoFinancieroDecodeError(AmbitoFinancieroClientError)`, with a docstring paragraph on why it is deliberately *not* related to `AmbitoFinancieroNoDataError`.
- `src/ambito_financiero_client/__init__.py` — re-exports it; `__all__` stays ASCII-sorted.
- `src/ambito_financiero_client/_state.py` — `strict_decode: bool = False` between `user_agent` and `http_client`.
- `src/ambito_financiero_client/client.py` / `aio.py` — the kwarg on all four entry points; both `configure` functions build a NEW client, so each reads `prior_strict_decode` from the outgoing one. The bind at the top of both `_request` methods, with a comment recording that no locking was added on the async side.
- `src/ambito_financiero_client/_logging.py` — the same byte-identical region and docstring paragraphs.
- `tests/test_decode.py` (1096 lines, **created**) — 53 tests.
- `tests/test_logging.py` (+186 lines, **0 deleted**) — 7 new tests.
- `verification/snapshots/ambito-financiero-client-surface.txt` — five lines changed.

## Decisions Made

- **The reflow finding is the plan's most consequential output and it is documented in three places** — a test in each package, this summary, and the hand-off list below. It is the first delta in the fan-out that is *not* a function of the substitution alone: it is a function of the substituted string's **length**. Any Plan 09 normalizer must either compare semantically or re-format both sides before comparing. A `sed`-then-`diff` implementation passes on three copies and fails on two, in opposite directions.
- **Fixture dataclasses live in the test files, never in `src/`.** A placeholder model in iol's `src/` would have to be deleted in Phase 30; one in ámbito's would be permanently dead code on a published wheel. Test-local declaration also preserves the property the whole suite family relies on: a shipped model gaining or losing a field can never turn a walker regression green.
- **ámbito's `AmbitoFinancieroDecodeError` is deliberately unrelated to `AmbitoFinancieroNoDataError`.** That package already has an error meaning "the request was fine, the answer is empty" — weekend, holiday, future date. A decode divergence is a malformed payload, a different fact entirely. Conflating them would make a shape bug read as normal market-calendar behaviour, which is precisely the false pass this milestone exists to eliminate. Asserted by `test_decode_error_is_not_an_api_error_nor_a_no_data_error`.
- **Both POLICY constants are pinned by test even though neither is reachable in production.** iol's is re-ratified in Phase 30 per the matrix; ámbito's is expected to stay inert indefinitely. The inert one is the *more* important to pin, because nothing in production would fail if it silently drifted — which is what "dormant" means and why a dormant copy needs a suite.
- **The two `higyrus`-naming comments inside the copied body were kept verbatim in both packages**, matching Plans 05 and 06. `# higyrus has no ``empty()`` today` now appears in four of the five copies as commentary about a different package. Editing it would add differing lines and erode the invariant D-02 exists to protect. Plan 09 should normalize once, for all five.
- **The sentinel literal carries no redaction marker** in both packages, matching Plans 03, 05 and 06: a marker-bearing sentinel would be rescued by `_redact` and the test would silently become a filter test.
- **ámbito's async bind adds no locking.** That package's `AsyncClient` creates its transport without the token-lock serialization the other three use (the documented B7 divergence, T-06-13). The plan called this out explicitly; the bind is a plain pair of statements at the top of the method and the acceptable-leak rationale in `_ensure_http_client` is untouched.

## Deviations from Plan

### Auto-fixed Issues

None. No bug, missing critical functionality or blocking issue was encountered. The walker, the carrier shape and the filter fix all transcribed cleanly, no pre-existing test in either package needed an edit, and no package-manager install was attempted.

### Clarifications to acceptance criteria

**1. The `_decode.py` diff is five changed lines in four hunks, not "at most five lines" line-for-line.** The criterion enumerates the logger name, the two ContextVar name lines, the decode-error import and `POLICY`. As Plan 05 already flagged, the exception *symbol* also appears at its `raise` site, so that is five. `POLICY` is byte-identical in both packages (the matrix gives both the higyrus row), so the count works out to five either way. What is genuinely new is that in **both** packages one of the ContextVar hunks is a **line-count change** rather than a substitution — 3→1 for iol's `DECODE_SCOPE`, 1→3 for ámbito's `STRICT_DECODE` — because `ruff format` reflows the statement at the 100-column boundary. Documented above and carried forward.

**2. Six container-recursion tests were appended to each `test_logging.py`, not the four the plan names.** The higyrus copy has five in that section; Plan 05 already recorded that discrepancy and appended five. A sixth was added per package — `test_marker_tuple_and_redaction_chain_are_untouched_by_phase_29` — asserting the exact marker tuple and the absence of the *other* packages' regexes, because pattern isolation is a hard project invariant and the plan's acceptance criterion for it (`git diff` shows no hunk touching the marker tuple) is a one-time check rather than a standing one.

**3. The plan's `<read_first>` cites `verification/regen_snapshots.py` for Task 1 and specifies running it once at the end of Task 2.** It was run at the end of *each* task, because Task 1's acceptance criterion requires `git status --porcelain verification/snapshots/` to show a change only to the iol file "at this point in the task", which is only observable if the regen has already run. The script rewrites all four files from current source and is idempotent, so the Task 2 run produced exactly the ámbito change on top. Net effect over both commits is the two files the plan requires.

**4. `iol_client/exceptions.py` has no `__all__`.** The plan's action says "re-export it from `iol_client/__init__.py`, keeping `__all__` ASCII-sorted" — that is the package `__all__`, which was updated. No module-level `__all__` exists in the exceptions module to maintain (matching matriz; unlike market-data and ámbito's package `__init__`).

---

**Total deviations:** 0 auto-fixed. Four acceptance-criterion clarifications, all documented above.
**Impact on plan:** None on scope. Every file touched is in the plan's `files_modified` list; no file outside it was created or modified.

## Issues Encountered

- The first `ruff format` pass on iol's `_decode.py` collapsed the `DECODE_SCOPE` declaration, which initially read as a transcription error. It is not — it is the formatter acting correctly on a shorter identifier, and the same run on ámbito produced the mirror-image expansion of `STRICT_DECODE`. Confirming the mechanism (measure both statements against the 100-column limit; `market_data_client` and `matriz_client` both land between the two thresholds, which is why Plans 05 and 06 saw neither) took one round trip and turned a suspected defect into the plan's main hand-off.
- No other issues. `ruff check` passed on the first run for both packages; `mypy --strict` passed on the first run for both.

## Verification

- `uv run pytest packages/iol-client packages/ambito-financiero-client -q --no-cov` — **387 passed, 1 deselected**.
- `uv run pytest packages -q --no-cov` — **1465 passed, 1 deselected** across all five packages.
- `uv run pytest .../test_decode.py .../test_logging.py` (both packages) — 136 passed.
- `uv run pytest verification/test_public_surface.py -q --no-cov` — 4 passed against both regenerated snapshots.
- `uv run mypy packages/iol-client/src packages/ambito-financiero-client/src` — Success: no issues found in 22 source files.
- `uv run ruff check .` — All checks passed. `uv run ruff format --check .` — 213 files already formatted.
- `uv run lint-imports` — Contracts: 4 kept, 0 broken.
- `diff <(sed '1,/^from __future__/d' higyrus/_decode.py) <(sed ... iol/_decode.py)` — 4 hunks / 5 changed lines: the decode-error import, `_LOGGER_NAME`, the raise site, and the ContextVar block (`STRICT_DECODE` substituted, `DECODE_SCOPE` collapsed 3→1). Same shape for ámbito with `STRICT_DECODE` expanded 1→3.
- `sorted(<pkg>._decode.__all__) == sorted(higyrus_client._decode.__all__)` — `True` for both, the eleven public names.
- `POLICY` in both — `DecodePolicy(missing_str='', missing_int=0, missing_float=0.0, missing_bool=False, non_dict_model='from_api_none', scalar_passthrough=False, literal_enforced=False)`, byte-identical to higyrus's.
- `python -c "import iol_client._decode"` and the ámbito equivalent — both succeed; neither package has a `models` module.
- `inspect.signature(...)` — `strict_decode` present in `Client`, `AsyncClient`, `<pkg>.configure` and `<pkg>.aio.configure` for both packages: **eight `True`**.
- `dataclasses.fields(_ClientState)` — `strict_decode` has `default is False` and `default_factory is MISSING` in both.
- `grep -c '_decode\.STRICT_DECODE\.set'` — 1 in each of the four files (`client.py` and `aio.py` × 2 packages); same counts for `_decode.open_request_scope`.
- `diff` of the `decode-intactness: generic-scan` region against higyrus's — **empty** (byte-identical) in both packages.
- `git diff` on both `_logging.py` files — no hunk touching `_REDACTION_MARKERS` or any `_redact` pass; the only lines mentioning the marker tuple are the new helper and the removed old loop condition.
- `IOLDecodeError` / `AmbitoFinancieroDecodeError` importable from their packages, present in `__all__`, and both `__all__` lists verified still ASCII-sorted.
- Zero-edit gate: `git diff --numstat d0b0089 -- packages/{iol,ambito-financiero}-client/tests/` reports 3 paths — `1045  0`, `189  0`, `186  0`. **Zero deleted lines in every case.**
- `git diff --name-only d0b0089 -- verification/snapshots/` — exactly `iol-client-surface.txt` and `ambito-financiero-client-surface.txt`.
- `git diff --diff-filter=D --name-only d0b0089..HEAD` — empty; no files deleted.

## Prohibitions status

Both plan prohibitions were carried as `flagged-unverified` and are now satisfied:

- *"The walker module must NEVER import from a models module — two of the five packages have none, and the reverse import would be a cycle in the three that do."* — Satisfied structurally and now proven in the only way it can be proven: **by landing the module in two packages where `models` does not exist.** `test_decode_module_never_imports_models` walks the AST and asserts the only in-package import is `<pkg>.exceptions`; `test_this_package_really_has_no_models_module` asserts `models.py` is absent from disk and that `import <pkg>.models` raises `ModuleNotFoundError`. A successful `import <pkg>._decode` in that state is direct evidence the module has no coupling to one. Nested models continue to be detected duck-typed via `_is_model`, which is what makes the standalone property possible.
- *"Divergence records must NEVER contain a wire value — iol payloads carry account and instrument identifiers and higyrus-style tax-identifier query markers exist in this codebase for a reason."* — Satisfied structurally and tested twice per package. `_emit` builds its six values from `_LOGGER_NAME`, the kind, the path, the declared type name, `type(value).__name__` and `cls.__name__` — no branch has access to a wire value. `test_record_is_flat_all_str_and_carries_no_wire_value` decodes a payload of unique sentinel strings and asserts no emitted value appears among them; `test_decode_sentinel_never_leaks_credential` drives a marker-free credential literal through a real `walk_model` call and checks `getMessage()`, `str(record.args)`, every string in `record.__dict__` and `repr(record.__dict__)`. The strict-mode exception carries the same six type-and-path values and no wire value — `test_strict_mode_raises_with_the_exact_field_path_and_no_wire_value` asserts the sentinel is absent from `str(excinfo.value)`. iol's `cuit`-style marker set is a higyrus concern and is correctly *absent* from iol's filter; `test_marker_tuple_and_redaction_chain_are_untouched_by_phase_29` asserts that isolation in both directions.

## TDD Gate Compliance

Neither task in this plan carries `tdd="true"`, and the plan declares no `<behavior>` block. Both tasks are a verbatim file copy plus wiring plus a test suite — there is no behaviour to drive RED-first, because the behaviour under test is a byte-identical copy of an already-implemented and already-tested module. The MVP+TDD runtime gate does not fire: neither task is behaviour-adding under the `task.is-behavior-adding` predicate (no `tdd="true"` frontmatter, no `<behavior>` block). Both commits are `feat(...)` and no `test(...)`/`feat(...)` gate sequence is required or claimed.

## Known Stubs

None, with one deliberate and documented exception that is **not** a stub:

- **ámbito's `_decode.py` is dormant** — nothing in `src/` calls `walk_model` there, and nothing is scheduled to. This is the plan's intended state (D-02, matrix row 5), not unfinished work: the copy exists so the intactness gate covers five copies and so a future typed surface inherits a proven decoder. It is fully exercised by a 53-test suite, so it cannot rot silently. Its `strict_decode` flag, both bind sites and `AmbitoFinancieroDecodeError` are reachable and tested, but only through the test suite's own fixtures.
- **iol's `_decode.py` is dormant until Phase 30**, on the same terms, and Phase 30 is the named consumer.
- `SILENT_SINK` is the deliberately-unreferenced-in-production constant it is in higyrus and market-data — required so the five copies stay byte-identical, used internally by `walk_model`'s non-dict branch, and exercised by tests.

No hardcoded empty value flows to any rendered surface; no placeholder text was introduced; no component was left without a data source.

## Threat Flags

None. This plan adds no network endpoint, no auth path, no file access and no schema at a trust boundary. The three boundaries it does touch (upstream JSON → walker, walker → the two package loggers, dormant module → future phases) are the plan's own T-29-36 through T-29-41, each with a named mitigation and a test above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Wave 4 is complete on the fan-out axis: all five copies exist.** The per-package recipe is now proven five times, including in the two hardest cases (a package with no models module, and one that will never have one).
- **Carried forward for Plan 09 (intactness gate) — this is the plan's most important hand-off, five items:**
  1. **The ContextVar substitution changes LINE COUNT, in both directions.** `iol_client` collapses `DECODE_SCOPE` from three lines to one; `ambito_financiero_client` expands `STRICT_DECODE` from one line to three. `market_data_client` and `matriz_client` sit between the thresholds and show neither. A normalizer that substitutes the package name and byte-compares will report a false divergence on **two of five copies**, in opposite directions. It must compare semantically or re-format both sides. Each affected package now carries a test pinning its own shape.
  2. The exception **symbol** appears at two sites (the import and the `raise`), so normalize the name, not just the import statement (inherited from Plan 05, confirmed here twice more).
  3. `POLICY` genuinely differs in exactly one copy (matriz); the other four are byte-identical to higyrus's (inherited from Plan 06, confirmed here).
  4. The two `higyrus`-naming comments inside the copied body were kept verbatim in all four fan-out packages. Decide once, for all five.
  5. Both `_logging.py` marker regions here are byte-identical to higyrus's with no pre-scan block above them (unlike matriz's D-22 case), so the region to hash is the text strictly between the two marker lines, which appear exactly once each.
- **Carried forward for Phase 30 (iol typed surface), three items:**
  1. **The walker has NO `dict` branch.** Carried from Plan 06 and it matters here: if Phase 30 declares a `dict[...]`-typed field on an iol model, `walk_field` falls through to its bare pass-through and returns the raw value — `None` when the key is absent — reporting nothing. matriz solved this with a post-walk pass in its call site (`_apply_mapping_policy`), which is the sanctioned lever; do not add a walker branch.
  2. **iol's `POLICY` must be re-ratified**, per matrix Section 2. The planner must confirm the models being written actually want typed-zero substitution (`""` / `0` / `0.0` / `False`) rather than matriz-style `None`, and record that confirmation. `test_policy_constant_matches_the_semantics_matrix` pins the current value and will fail loudly if it is changed without also changing the test.
  3. The `from_api` shape is already pinned by four tests in `test_decode.py` (`test_from_api_shape_*`). Phase 30's real models should adopt that exact shape — a frozen slotted dataclass whose `from_api` calls `cls(**walk_model(cls, payload, policy=POLICY))` — and should either add a nested-model precondition test (as market-data and matriz did) or route nested `from_api` overrides through the call site.
- **Carried forward for Plan 08 (matriz websocket):** unchanged and still applicable — a plain `threading.Thread` sees the ContextVar **default**, so matriz's WS daemon thread must bind explicitly. Nothing in this plan affects that.
- **No blockers.**

## Self-Check: PASSED

Created files verified present on disk: `packages/iol-client/src/iol_client/_decode.py`, `packages/iol-client/tests/test_decode.py`, `packages/ambito-financiero-client/src/ambito_financiero_client/_decode.py`, `packages/ambito-financiero-client/tests/test_decode.py`. Modified files verified present: both `exceptions.py`, both `__init__.py`, both `_state.py`, both `_logging.py`, both `client.py`, both `aio.py`, both `tests/test_logging.py`, and both `verification/snapshots/*-surface.txt`. Both task commits (`6a6e105`, `610c9e9`) verified present in git history.

---
*Phase: 29-decoder-observable*
*Completed: 2026-08-19*
