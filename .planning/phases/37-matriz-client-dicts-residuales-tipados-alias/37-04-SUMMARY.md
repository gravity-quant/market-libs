---
phase: 37-matriz-client-dicts-residuales-tipados-alias
plan: 04
subsystem: testing
tags: [ast, static-analysis, ci-gate, ratchet, mypy, ruff, dataclasses]

# Dependency graph
requires:
  - phase: 37-02
    provides: "InstrumentDetail.tickPriceRanges retyped to dict[str, TickPriceRange] — the gate extension would have reddened the lint job had it landed first"
  - phase: 37-03
    provides: "DetailedPosition.report / AccountReport.detailedAccountReports / AccountReport.portfolio retyped — same ordering constraint"
  - phase: 32
    provides: "tools/check_surface_types.py return-annotation dimension, the injectable-root seam (D-04), and packages/iol-client/tests/test_surface_types_red.py as the RED-fixture pattern"
provides:
  - "A second scanning dimension in the shared surface-type gate: annotated field declarations inside exported class bodies"
  - "_field_annotation_is_untyped_mapping — a narrow field predicate that spares list[Any] by contract"
  - "_FIELD_EXEMPTIONS — a qualified Class.field exemption table holding exactly one entry"
  - "ScanResult.fields plus a new term in the gate's summary line"
  - "packages/matriz-client/tests/test_surface_types_red.py — 12 cases pinning non-vacuity, narrowness, exemption reachability and qualification"
  - "RESEARCH F-9's cross-package blast-radius measurement recorded in the gate's own source"
affects: [37-05, 38-iol-client-audit, market-data-client-warnings-retype, any-phase-exporting-RequestSpec]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-dimension AST gate: parallel candidate/adjudicate pairs sharing one violation and one exemption accumulator"
    - "Qualified-name exemption table consulted before the simple-name taxonomy"
    - "Exemption reachability proven by a named count in exempted_by_reason, not by a total"

key-files:
  created:
    - packages/matriz-client/tests/test_surface_types_red.py
  modified:
    - tools/check_surface_types.py

key-decisions:
  - "The field predicate does not constrain the mapping's KEY type — stricter than the plan's letter, unobservable on the real tree, and it closes dict[int, Any] as a bypass"
  - "The anti-vacuity guard was widened from 'zero definitions' to 'zero definitions AND zero fields' — a package exporting only dataclasses was inspected and must not read as a broken checkout"
  - "Both tasks land the gate and its RED fixture together; a commit carrying only one half has a meaningless CI signal"
  - "The exemption floor stays at 20 rather than rising to 24; the one field exemption is asserted BY NAME instead, which a bumped total cannot express"
  - "Mapping aliases (Dict, Mapping, MutableMapping) join dict in the predicate so the ratchet cannot be bypassed by spelling"

patterns-established:
  - "Mirror-not-import for cross-package test fixtures: _write_fake_package is copied into the matriz module rather than extracted, preserving the repo's zero cross-package test dependencies"
  - "Record a measured blast radius in the gate source next to the exemption it de-risks, so the trap is documented where it would be triggered rather than rediscovered by a red CI run"

requirements-completed: [NOBJ-MTZ-01]

# Metrics
duration: 34min
completed: 2026-08-29
status: complete
---

# Phase 37 Plan 04: Gate field dimension Summary

**`tools/check_surface_types.py` gains a second AST dimension — annotated field declarations inside exported classes — with a narrow `dict[str, Any]`/bare-`Any` predicate, one qualified `UnknownFrame.raw` exemption counted by name, and a 12-case matriz RED fixture that proves the dimension is not vacuous.**

## Performance

- **Duration:** 34 min
- **Started:** 2026-08-29T00:00:00Z
- **Completed:** 2026-08-29T00:34:00Z
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## The delta — evidence for Success Criterion 2

Success Criterion 2 is not "matriz has no untyped mapping fields" (Plans 37-02/03 delivered that).
It is that the gate **reports** zero with a single documented exemption, *no obtenida por omisión o
por un hueco de resolución del gate*. Both lines are quoted verbatim.

**Before (37-RESEARCH F-2, measured with all five `dict[str, Any]` sites still in place):**

```
surface types: 6 packages, 183 `__all__` names, 330 definitions scanned, 13 constant/alias exports, 23 exempted (dunder 13, private-helper 1, serialize-out 9), 0 violations
```

**After (this plan, `uv run python tools/check_surface_types.py`):**

```
surface types: 6 packages, 186 `__all__` names, 330 definitions scanned, 442 fields scanned, 13 constant/alias exports, 24 exempted (dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1), 0 violations
```

The same `0 violations`, now earned. **442 fields inspected** where the previous line inspected
none, and **one named exemption** (`ws-catch-all 1`) absorbing a genuine hit rather than sitting
unreachable. The `__all__` count moved 183 → 186 from the model classes Plans 37-02/03 exported;
`330 definitions` is unchanged, which is the point — the function dimension never saw any of this.

## Accomplishments

- **Closed the measured blind spot (F-2).** `_field_candidates_for` + `_adjudicate_field` mirror
  the existing `_candidates_for` + `_adjudicate` pair, reusing `_module_level_statements` so a
  field declared under an `if` inside a class body is scanned for the same reason a conditionally
  defined method is.
- **Kept the blast radius inside the phase (D-01b).** `_field_annotation_is_untyped_mapping` is a
  new predicate, not a reuse of the wide `_annotation_mentions_any`. It matches the annotation's
  own shape, never its subtree: bare `Any`, and a two-parameter mapping whose value is `Any`, with
  `X | None` / `Optional[X]` stripped first. `list[Any]`, `list[dict[str, Any]]` and
  `dict[str, list[Any]]` are all spared, so `market-data-client`'s two exported `warnings` fields
  stay out of scope. Confirmed by execution: its 711-test suite passes and the gate is green with
  that package in the roster.
- **Made the one exemption falsifiable (D-01c/D-01d).** `_FIELD_EXEMPTIONS` is keyed on
  `"UnknownFrame.raw"`, consulted before `_is_exempt`, and its reason flows into the shared
  `exempted_by_reason` accumulator. The fixture asserts `exempted_by_reason["ws-catch-all"] == 1`
  on both a synthetic tree and the real one, and asserts that the same field name on a differently
  named class still reddens.
- **Recorded RESEARCH F-9 where it will be needed.** The gate's source now states that the
  internal request-spec dataclass declares an optional untyped mapping field in all six packages,
  that this is unreachable only because it is in no package's `__all__`, and that exporting it
  would redden all six at once.

## Task Commits

1. **Task 1: Give the gate a field dimension with the one qualified exemption, proven non-vacuous** — `f580c23` (feat)
2. **Task 2: Prove the extension across all six packages and record the ratchet's new floor** — `00a9821` (test)

**Plan metadata:** see the `docs(37-04)` commit.

### TDD gate compliance

Task 1 carried `tdd="true"`. The RED/GREEN cycle was executed in the working tree — the 12-case
fixture was written first and observed failing 12/12 against the unextended gate, then the gate was
implemented and observed passing 12/12 — but the two halves were **landed in one commit**, on the
plan's explicit instruction (`<action>`: "Land the gate change and this test module in the SAME
commit"). The reasoning is CI-shaped and correct: the RED half alone leaves `uv run python
tools/check_surface_types.py` green while the new test module fails, and the GREEN half alone
carries no evidence that the extension did not redden the tree. A separate `test(...)` gate commit
would have been a knowingly-red commit on `main` for this repo's lint job. Recorded here rather
than silently, since it means git log shows `feat` → `test` instead of the usual `test` → `feat`.

## Files Created/Modified

- `tools/check_surface_types.py` — module docstring now names both dimensions with the measured
  before/after; new `_OPTIONAL`, `_MAPPING_BASES`, `_FIELD_EXEMPTIONS` constants; new `_base_name`,
  `_is_any`, `_is_none`, `_strip_optional`, `_field_annotation_is_untyped_mapping`,
  `_field_candidates_for`, `_adjudicate_field`; `ScanResult.fields`; field loop wired into
  `scan_surface_types`; new summary term; widened anti-vacuity guard.
- `packages/matriz-client/tests/test_surface_types_red.py` — NEW. 12 tests in four groups:
  non-vacuity (6), narrowness (2), exemption reachability and qualification (3), real-tree floors (1).

### Named assertions the plan asked to be recorded

- `test_reverting_tick_price_ranges_to_its_pre_phase_form_reddens` — the plan's "revert
  `InstrumentDetail.tickPriceRanges` to its pre-phase form" check, performed on a synthetic package
  under `tmp_path` rather than by editing the real tree.
- `test_a_list_of_any_field_is_spared_keeping_the_narrow_predicate_narrow` — the D-01b out-of-scope
  spare, reproducing both real market-data declarations on classes of the same names.
- `test_the_catch_all_frame_exemption_absorbs_a_real_hit_and_is_counted` — exemption reachability.
- `test_the_field_exemption_is_qualified_not_a_bare_member_name` — exemption qualification.

## Decisions Made

- **The mapping's key type is not constrained.** The plan's letter said "a string-keyed mapping
  subscript whose value parameter is `Any`". The implementation matches any two-parameter mapping
  whose **value** is `Any`, which subsumes the string-keyed case. Rationale: a mapping keyed by
  something other than `str` says exactly as little about its values, and constraining the key
  would leave `dict[int, Any]` as a one-token bypass. Strictly stricter than the plan, and
  unobservable on the real tree — F-9's cross-package AST scan found no exported `dict[<non-str>,
  Any]` anywhere. Documented in the predicate's own docstring.
- **`Dict` / `Mapping` / `MutableMapping` join `dict`.** Only `dict` appears in the tree today;
  the aliases are recognised so the ratchet cannot be defeated by spelling. Matched structurally
  through `_base_name`, so `typing.Dict` and `collections.abc.Mapping` are the same entry.
- **The anti-vacuity guard was widened, not weakened.** It was `definitions_total == 0`; it is now
  `definitions_total == 0 and fields_total == 0`. A package exporting only dataclasses with no
  methods *was* inspected, and calling that a broken checkout would be false — every synthetic
  dataclass fixture in the new module hits exactly that shape. A hard "zero fields is a problem"
  clause was deliberately **not** added: it would have reddened the pre-existing iol fixtures,
  whose fake packages legitimately declare no fields. The zero-fields signal lives instead as the
  `result.fields >= 350` floor in the real-tree test, where it can be a lower bound.
- **The exemption total floor stayed at 20.** Raising it to 24 would be satisfiable by any four
  exemptions. `exempted_by_reason["ws-catch-all"] == 1` is the stronger statement and is what the
  real-tree test asserts.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Widened the anti-vacuity guard to admit field-only scans**

- **Found during:** Task 1 (GREEN step)
- **Issue:** Every synthetic fixture in the new module exports a dataclass with fields and no
  methods. Under the existing `definitions_total == 0` guard, `scan_surface_types` raised
  "zero definitions were scanned" before ever adjudicating a field, so the narrowness and
  exemption-reachability cases could not observe a clean scan at all.
- **Fix:** Guard is now `definitions_total == 0 and fields_total == 0`, with an inline comment
  stating why this is a widening and not a weakening, and why a hard zero-fields clause was
  rejected (it would redden the iol fixtures).
- **Files modified:** `tools/check_surface_types.py`
- **Verification:** All 12 matriz cases and all 12 pre-existing iol cases pass; the real-tree scan
  is unaffected (it has both dimensions non-zero).
- **Committed in:** `f580c23` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The guard change is required for the plan's own behavior spec to be
expressible. No scope creep — the diff for this plan is exactly the two files the plan names.

## Issues Encountered

**`mypy packages/matriz-client/tests` is red on four PRE-EXISTING errors — deferred, not fixed.**

Task 1's acceptance list includes `uv run mypy packages/matriz-client/tests` reporting success. It
does not, but not because of anything this plan wrote. The four errors live in
`packages/matriz-client/tests/test_core.py:372` and `test_decode.py:666,839,840` and are fallout
from the retypes in Plans 37-01/37-02/37-03 (`comparison-overlap` on assertions that were not
updated alongside a field retype, plus a `type: ignore` sitting one line above the access it was
meant to cover).

Confirmed pre-existing by measurement rather than inference: removing the new test module from the
tree and re-running mypy still reports `Found 4 errors in 2 files (checked 26 source files)`. Both
files this plan owns typecheck clean, and `uv run mypy packages/matriz-client/src` reports
`Success: no issues found in 17 source files`.

Not fixed here because the plan's `<verification>` block requires `git diff --name-only` for this
plan to list only `tools/check_surface_types.py` and
`packages/matriz-client/tests/test_surface_types_red.py` — editing two further test files would
have violated the plan's own stated scope check. Recorded with per-error diagnosis and suggested
fixes in
`.planning/phases/37-matriz-client-dicts-residuales-tipados-alias/deferred-items.md` (DEF-37-01).
**This fails the CI `typecheck` job today and should be resolved before phase verification.**

## Verification Results

| Check | Result |
|-------|--------|
| `uv run python tools/check_surface_types.py` | exit 0, summary quoted above, `442 fields scanned` |
| `uv run python tools/check_decode_intactness.py` | exit 0 (Checks A–D) |
| `uv run python tools/check_uniform_structure.py` | exit 0 |
| `uv run python tools/surface_parity.py` | exit 0 |
| `packages/matriz-client/tests/test_surface_types_red.py` | 12 passed |
| `packages/iol-client/tests/test_surface_types_red.py` | 12 passed (pre-existing floors hold) |
| `pytest -k "list or narrow"` on the new module | 1 passed, 11 deselected |
| ambito-financiero-client | 208 passed, 1 deselected |
| higyrus-client | 289 passed |
| iol-client | 289 passed |
| market-data-client | 711 passed |
| matriz-client | 547 passed |
| wallets-client | 10 passed |
| `pytest verification/test_main_market_data_deep_chain.py verification/test_safemodel_diff_null_object_links.py` | 14 passed |
| `uv run mypy packages/matriz-client/src` | Success, 17 files |
| `uv run mypy packages/matriz-client/tests` | **4 pre-existing errors** — see Issues Encountered / DEF-37-01 |
| `uv run ruff check tools packages/matriz-client` | All checks passed |
| `uv run ruff format --check tools packages/matriz-client` | 48 files unchanged |
| `git diff --name-only f580c23~1..HEAD` | exactly the two planned files |

`scan_surface_types(Path('.'))` reports `442 {'dunder': 13, 'private-helper': 1, 'serialize-out': 9,
'ws-catch-all': 1}`.

## Prohibition Compliance

| Prohibition | Status |
|-------------|--------|
| Do not land before the 37-02/37-03 retypes | Held — 37-02 and 37-03 summaries exist; matriz's only remaining `dict[str, Any]` field is `UnknownFrame.raw:812` |
| Do not add the exemption to `_is_exempt` | Held — `_FIELD_EXEMPTIONS` is a separate qualified table; `test_the_field_exemption_is_qualified_not_a_bare_member_name` pins it |
| Do not widen the predicate to any mention of `Any` | Held — `list[Any]`, `list[dict[str, Any]]`, `dict[str, list[Any]]` all spared; market-data's 711 tests pass |
| Do not commit a fake package under `packages/` | Held — every synthetic tree is written under `tmp_path` |
| Do not prove the gate by subprocess | Held — all assertions call `scan_surface_types` / `check_surface_types` in-process |
| Do not touch `models.py`, `_core.py` or any package source | Held — the plan diff is two files, neither of them package source |
| Ratchet discipline: never resolve a red by weakening the gate | Held — no exemption was added beyond the one declared entry, no foreign package was edited |

## User Setup Required

None — no external service configuration required. Zero packages installed; `uv.lock` untouched
(threat T-37-SC accepted disposition holds).

## Next Phase Readiness

- **Ready for 37-05** (`MarketDataSnapshot` property aliases). Plan 37-05 adds read-only
  `@property` aliases, which are `FunctionDef` nodes with return annotations — they land in the
  *existing* function dimension and are unaffected by anything here. The field floor of 350 has
  ~90 counts of headroom above the measured 442 and will not be disturbed.
- **One blocker for phase verification:** DEF-37-01 (the four pre-existing mypy errors in
  `test_core.py` / `test_decode.py`). It fails the CI `typecheck` job and belongs to the retype
  plans, not this one.
- **A trap is now documented rather than latent:** exporting the internal request-spec dataclass
  from any package's `__all__` would redden all six packages at once. The condition and the remedy
  are stated in `tools/check_surface_types.py` next to `_FIELD_EXEMPTIONS`.

## Self-Check: PASSED

- Files exist: `tools/check_surface_types.py`, `packages/matriz-client/tests/test_surface_types_red.py`, `37-04-SUMMARY.md`, `deferred-items.md`
- Commits exist: `f580c23`, `00a9821`
- `must_haves` artifact contents present: `_FIELD_EXEMPTIONS` in the gate (4 references), `_write_fake_package` in the fixture (5 references)
- `must_haves` key_links present: `_adjudicate_field(` (definition + call site in `scan_surface_types`), `check_surface_types(root=tmp_path)` (multiple call sites)

---
*Phase: 37-matriz-client-dicts-residuales-tipados-alias*
*Completed: 2026-08-29*
