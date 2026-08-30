---
phase: 36
plan: 01
subsystem: market-data-client
tags: [tests, decode, mapping-axis, null-objects, cr-03]
requires:
  - "market_data_client.models._strip_optional (read-only, at plan start — dropped as a dependency by this plan)"
  - "market_data_client._decode.hints_for"
provides:
  - "packages/market-data-client/tests/ with zero call sites into the mapping machinery"
  - "module-local _strip_optional in test_core.py and test_decode.py"
  - "CR-03 disposition verdict (retire), recorded by name"
affects:
  - "36-02 — may now delete _mapping_value / _apply_mapping_policy / _is_mapping / _strip_optional from models.py without reddening a test"
tech-stack:
  added: []
  patterns:
    - "module-local helper copy (DT-03 no-shared-code), the pattern test_null_object.py documents as deliberate"
key-files:
  created: []
  modified:
    - packages/market-data-client/tests/test_core.py
    - packages/market-data-client/tests/test_decode.py
decisions:
  - "CR-03 disposition: retire — the contract's implementation leaves the paquete, not just its example"
  - "_strip_optional is copied module-locally into both test modules; _is_mapping is copied nowhere"
  - "The CR-03 section banner is replaced, not blank-deleted, because four rows in that block survive"
metrics:
  duration: ~15 min
  tasks: 3
  files: 2
  tests_before: 663
  tests_after: 660
  completed: 2026-08-29
status: complete
---

# Phase 36 Plan 01: Retirar el eje mapping del suite de tests — Summary

Retired the mapping axis from the `market-data-client` test suite by the 36-RESEARCH per-call-site
census (6 surgical sites + 1 clean deletion across 2 files), so Plan 36-02 can delete the machinery
from `models.py` without reddening anything — and did it without taking the CONTEXT D-05 line
ranges, which over-cover and would have carried off three live non-mapping invariants.

## CR-03 disposition verdict

**Verdict: `retire`**

The CR-03 required-mapping contract is retired from `market-data-client` together with the mapping
machinery it asserted against. The `_RequiredMapping` module-local carrier and its two tests
(`test_absent_required_mapping_field_reports_missing_and_substitutes_the_empty_dict` and
`test_strict_mode_raises_on_an_absent_required_mapping_field`) were deleted in Task 3.

**Rationale (one sentence):** After Phase 36 the contract's IMPLEMENTATION (`_mapping_value` /
`_apply_mapping_policy`) is being retired — not merely its example, as was the case at 33-07 — so
preserving the two tests would require keeping dead code alive in a shipped module purely to have
something to assert against, contradicting CONTEXT D-05 directly and making ROADMAP SC-5
unachievable as written.

**How the verdict was reached:** this session ran under GSD auto-mode
(`workflow.auto_advance = true`); the Task 1 `checkpoint:decision` gate (`gate="blocking"`, not
`blocking-human`) was auto-resolved by selecting the FIRST option offered, `retire`, which is also
the 36-RESEARCH Open Question 1 recommendation. No human operator verdict was collected — the plan
asked for one, and auto-mode substituted the documented auto-selection rule. If the operator wants
`preserve` instead, this plan's Task 3 commit (`de7614a`) is the single revert point.

**What survives the retirement:** the lock-8 half of the CR-03 block —
`test_mapping_pass_is_silent_under_a_non_dict_payload`, which asserts that a non-`dict` payload
emits exactly ONE terminal record — keeps its measured record set `[("", "non_dict")]` and is only
retitled in Plan 36-02. The four remaining tests of that block assert on
`MarketDataSnapshot.market_data` and were left untouched; Plan 36-02 migrates them.

**Residual risk accepted:** `market-data-client` stops asserting that a required `dict[...]` field
reports and substitutes `{}`. If a future phase re-declares a mapping field in this package,
nothing in this package catches the regression until someone re-mints the axis. The contract is
recorded here by name (CR-03) — and by name in a replacement comment banner at
`test_decode.py:1207-1223` — so it is discoverable rather than only inferable from a diff.

## What was built

### Task 1 — CR-03 verdict recorded (`29735d0`)

Verdict written to this SUMMARY under a CR-03 heading with its rationale. No file under
`packages/` changed, as the plan required.

### Task 2 — local Optional detector + mapping assertions dropped (`cba276a`)

Six census sites, two files, zero line-range deletions, no test deleted (663 → 663).

| # | File | Site | What changed |
|---|------|------|--------------|
| 1 | `test_core.py` | new `_strip_optional` | Six-line copy of `models.py:118-124`, with the DT-03 no-shared-code rationale in its docstring |
| 2 | `test_core.py` | `test_health_models_declare_no_mapping_field_and_no_received_at` | Mapping assertion dropped; renamed to `test_health_models_declare_no_received_at`; the `cast(Any, ...)` discipline comment repointed from `models._apply_mapping_policy` to `_decode.hints_for` so it does not outlive its referent |
| 3 | `test_core.py` | `test_health_models_declare_exactly_the_two_locked_optionals` (T-31-17) | Detector call repointed at the local copy. Nothing else touched; expected set still `{FeedIngestor.last_error, FeedPipeline.last_write_error}` |
| 4 | `test_core.py` | `test_mutation_result_models_..._no_optional` | Mapping assertion dropped, `received_at` + no-Optional assertions kept, detector repointed, renamed to `test_mutation_result_models_declare_no_received_at_and_no_optional` |
| 5 | `test_decode.py` | new `_strip_optional` | Same copy, same rationale |
| 6 | `test_decode.py` | `test_no_call_site_exempt_safemodel_appears_as_a_nested_field_type` | Mapping disjunct dropped from the `exempt` comprehension; exemption is now solely "declares its own `from_api`". Docstring gained a Phase 36 NARROWING paragraph and its "two companion tests below" promise was corrected to one |
| 7 | `test_decode.py` | `test_models_with_a_from_api_override_are_never_a_nested_field_type` (WR-03) | Detector repointed. Verdict set unchanged: `{MarketDataSnapshot, Symbol}` |

**Non-vacuity measured, not assumed** (the plan required verification): after dropping the mapping
disjunct, `exempt == ['MarketDataSnapshot', 'Symbol']` — non-empty, so the
`assert exempt` guard does not go vacuous.

### Task 3 — clean deletion + verdict executed (`de7614a`)

- `test_no_mapping_carrying_model_is_ever_a_nested_field_type` deleted in full — the census's one
  unconditional deletion. The deletion **stopped at its closing line**: CONTEXT's `~1328-1373`
  range also covers the WR-03 lock, and taking the range would have silently retired WR-03.
- `_RequiredMapping` and its two CR-03 rows deleted per the `retire` verdict.
- The CR-03 section banner was **replaced rather than blank-deleted** (see Deviations).

## Verification

| Check | Result |
|-------|--------|
| `uv run pytest packages/market-data-client -q` | **660 passed** — exactly the count the `retire` verdict predicts (663 − 1 clean deletion − 2 CR-03 rows) |
| `uv run ruff check packages/market-data-client` | All checks passed |
| `uv run ruff format --check packages/market-data-client` | 48 files already formatted |
| `uv run mypy packages/market-data-client/tests` | Success: no issues found in 35 source files |
| `-k 'locked_optionals'` (T-31-17) | 1 passed — survives the repointing |
| `-k 'from_api_override_are_never'` (WR-03) | 1 passed — still asserts `{MarketDataSnapshot, Symbol}` |
| `-k 'silent_under_a_non_dict'` (lock 8) | 1 passed |
| `grep -c 'def test_no_mapping_carrying_model_is_ever_a_nested_field_type'` | 0 |
| Code references to the mapping machinery in `tests/` | 0 (one prose mention of `_RequiredMapping` remains, in the retirement-record comment — that is the "discoverable by name" requirement, not a call site) |
| `git rev-parse HEAD:.../models.py` | `dea0dec488598c6e683c117eac9d475a221b7942` — unchanged from plan start |
| `uv run python tools/check_decode_intactness.py` | exit 0 (`_decode.py` digest untouched) |

## Note for Plan 36-02 — a non-event, not a regression

Plan 36-02 will make WR-03's computed `nested_types` set **GROW** by `MarketDataEntries`,
`EntryValue` and `BookLevel`, while its verdict (`overriding & nested_types == set()`) stays
identical. RESEARCH Open Question 3 resolved this as a non-event. An executor who sees the computed
set change must not treat it as a regression.

## Deviations from Plan

### Auto-fixed / auto-decided issues

**1. [Rule 3 — Blocking] `models` import became unused in `test_core.py`**
- **Found during:** Task 2
- **Issue:** After dropping the last two `models.*` call sites, `from market_data_client import _core, _decode, models` left `models` unused — ruff F401, which would have failed the task's own gate.
- **Fix:** Dropped `models` from the import. `test_decode.py` still imports it (used elsewhere) and was left alone.
- **Commit:** `cba276a`

**2. [Rule 3 — Blocking] Task 2's grep-for-zero criteria are not jointly satisfiable with its test-count criterion**
- **Found during:** Task 2
- **Issue:** Task 2 requires `models._is_mapping(` and `models._strip_optional(` to grep to `0` in both files AND requires `663 passed` / "this task deletes no test". The two remaining references live inside `test_no_mapping_carrying_model_is_ever_a_nested_field_type`, whose assertion (`carriers == {"MarketDataSnapshot"}`) cannot be expressed without the mapping predicate — which the plan explicitly says is "NOT copied anywhere".
- **Fix:** Deferred both greps to Task 3, which deletes that test wholesale. The end-state criterion (zero references after the plan) is met; the intermediate one was unachievable as written. The alternative — inlining the mapping predicate in Task 2 only for Task 3 to delete it minutes later — would have added churn and contradicted the plan's own "copied nowhere" instruction.
- **Verified at:** `de7614a` — both greps now 0.

**3. [Rule 2 — Correctness of the artifact] CR-03 section banner replaced instead of deleted**
- **Found during:** Task 3
- **Issue:** The plan says to delete "the section banner that introduces them". But that banner introduces the whole CR-03 block, and **four** of its rows survive (the plan itself says "Do NOT touch the four remaining tests in that block"). Deleting the banner outright would have filed those four surviving tests under the preceding, unrelated CR-04 heading.
- **Fix:** Replaced the banner with one that states the CR-03 retirement by name, explains why the 33-07 reasoning does not carry over, and names the four surviving rows as `MarketDataSnapshot` rows that 36-02 migrates. This satisfies both the plan's "delete the CR-03 banner" instruction and its "record the retirement by name so it is discoverable" instruction.
- **Commit:** `de7614a`

**4. [Rule 1 — False-clean signal] `NOBJ-MD-02` was NOT marked complete**
- **Found during:** state updates
- **Issue:** This plan's frontmatter declares `requirements: [NOBJ-MD-02]`, so the standard state step marked it complete in `REQUIREMENTS.md`. But `NOBJ-MD-02` is declared by **all three** plans of this phase, and its text covers the `entries` revert, the no-data row, and "se elimina la maquinaria `_mapping_value`/`_apply_mapping_policy` **y sus tests de precondición**". This plan delivered only the tests half — the machinery itself leaves `models.py` in 36-02.
- **Fix:** Reverted the mark; `NOBJ-MD-02` stays `Pending`. Marking it here would have produced exactly the false-clean reading this project exists to eliminate. 36-02 / 36-03 will complete it.

**5. [Checkpoint] Task 1's operator gate was auto-resolved, not answered by a human**
- The plan's Task 1 asks for an operator verdict. This session ran under auto-mode, so the first option (`retire`) was auto-selected per the documented rule for `checkpoint:decision` gates whose `gate` is `"blocking"` rather than `"blocking-human"`. Recorded here so the substitution is auditable rather than reading as a human decision.

### Scope discipline

`models.py`, `_decode.py`, `_core.py`, `client.py`, `aio.py`, `pyproject.toml`, `__version__` and
`uv.lock` were **not** touched — the plan's prohibition held. `git status --short
packages/market-data-client/src/` reported 0 lines at plan end.

## Known Stubs

None. This plan is test-side only and removes code rather than adding placeholders.

## Threat Flags

None. No new network endpoint, auth path, file access pattern or trust-boundary schema change —
this plan removed test-side references to a call-site pass and introduced no runtime surface.
T-36-01-01 (a range deletion silently retiring T-31-17 or WR-03) was mitigated as planned: edits
followed the per-call-site census, both locks were run by name, and the exact post-task test counts
(663 then 660) were pinned so an overshoot would have reddened.

## Self-Check: PASSED

- `packages/market-data-client/tests/test_core.py` — FOUND, contains `def _strip_optional`
- `packages/market-data-client/tests/test_decode.py` — FOUND, contains `def _strip_optional`
- `.planning/phases/36-.../36-01-SUMMARY.md` — FOUND
- Commits `29735d0`, `cba276a`, `de7614a` — all FOUND in `git log`
