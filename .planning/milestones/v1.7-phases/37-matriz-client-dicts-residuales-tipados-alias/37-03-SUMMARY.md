---
phase: 37
plan: 03
subsystem: matriz-client models — the Risk-endpoint mappings
tags: [risk-endpoints, vendor-documented-unmeasured, provenance, d-02, d-04, d-07, tdd, null-object, findings-ledger]
status: complete

requires:
  - "37-01 — the Risk envelope unwrap; without it these three fields decode from the wrong nesting level and the retype is inert"
  - "37-02 — the element-typed, self-recursing mapping axis; `report`'s depth-2 hint lands on it with zero axis changes"
  - "matriz_client._decode.walk_field / _safe_key (Phase 29) — byte-unchanged, verified"
  - "_SafeModel.empty / __bool__ (Phase 35 NOBJ-01) — both new models inherit them"
  - "verification.findings.append_finding (Phase 11 HARN-08/10) — the programmatic ledger writer"
provides:
  - "InstrumentPositionReport and DetailedAccountReport — the phase's two `vendor-documented, UNMEASURED` models"
  - "DetailedPosition.report: dict[str, dict[str, InstrumentPositionReport]] — TWO levels"
  - "AccountReport.detailedAccountReports: dict[str, DetailedAccountReport] — ONE level"
  - "AccountReport.portfolio: float | None — a scalar leaf that left the mapping axis"
  - "F-11 / F-12 in .planning/verification/matriz-client-findings.md — the two rosters declared unobserved"
  - "A models module with exactly ONE untyped mapping annotation left: UnknownFrame.raw"
affects:
  - "37-04 — the gate extension now has only UnknownFrame.raw to exempt; both new classes are on __all__ so its scan resolves them"
  - "37-05 — `_safemodel_classes()` is now 20; that plan raises test_null_object.py's roster floor from 17 to it"
  - "Phase 39 / LIVE-NOBJ-01 — inherits both unobserved rosters, now named in the ledger"

tech-stack:
  added: []
  patterns:
    - "Third provenance class `vendor-documented, UNMEASURED` (D-04a) — distinct from `baseline` and from `capture`, stated in those words"
    - "Closed roster + non-fatal `extra` divergence reporting with the COST disclosed and the detection artifact named (MarketDataEntries form, Phase 36)"
    - "Genuinely different container depths typed at their real depths, never harmonized (37-RESEARCH F-7/F-8)"
    - "Ledger provenance rows appended programmatically via append_finding, never by hand-editing the AUTO-GENERATED region (D-23)"
    - "TDD RED/GREEN as separate commits, one pair per task"

key-files:
  created: []
  modified:
    - packages/matriz-client/src/matriz_client/models.py
    - packages/matriz-client/src/matriz_client/__init__.py
    - packages/matriz-client/tests/test_models.py
    - packages/matriz-client/tests/test_decode.py
    - verification/snapshots/matriz-client-surface.txt
    - .planning/verification/matriz-client-findings.md

decisions:
  - "The two containers are typed at DIFFERENT depths (2 and 1) because the vendor samples show different depths — forcing a shared shape would fabricate a level of keys"
  - "lastCalculation / hasError / errorDetail were deliberately omitted from the test fixtures so the strict-mode extra counts are not blurred by unrelated pre-existing divergences"
  - "The F-09 bullet reordering the serializer performed was verified as a reorder, not a loss — every byte survives"
  - "The test_null_object.py roster floor was NOT raised here; the plan assigns that to 37-05"

metrics:
  duration: ~22 min
  completed: 2026-08-29
  tasks: 3
  commits: 5
  files_changed: 6
  tests: 510 → 535
---

# Phase 37 Plan 03: The three remaining Risk mappings, typed at honest depths — Summary

`DetailedPosition.report`, `AccountReport.detailedAccountReports` and `AccountReport.portfolio` are
typed at the depth the vendor sample actually shows — two levels, one level, and no levels at all —
with every roster labelled as derived from a document nobody has ever seen confirmed on the wire.

## The two derived rosters, verbatim, next to the line ranges they came from

Both were derived by **reading the vendor doc in this session**, not carried over from any prior
summary. `packages/matriz-client/documentation/Primary-API.md`:

### `InstrumentPositionReport` — from `Primary-API.md:1745-1747`

```json
          "instrumentInitialSize":-2,
          "instrumentFilledSize":0,
          "instrumentCurrentSize":-2
```

```
['instrumentInitialSize', 'instrumentFilledSize', 'instrumentCurrentSize']
```

Repeated identically at `:1785-1787` for the sample's second symbol, inside the
`GET /rest/risk/detailedPosition/REM7374` response at `:1701-1791`. All three declared
`float | None`: the wire carries `int`, and `walk_field`'s float arm widens **before** consulting
`scalar_passthrough`, so the widening is silent and fabricates no divergence — the same reasoning
`TickPriceRange.lowerLimit` carries.

**Deferred, and named in the docstring so the deferral stays discoverable:** the `detailedPositions`
array (`:1710-1744`, ~21 fields per element) and its `detailedDailyDiff` object (`:1733-1742`, 8
fields). D-07's minimal disposition. They arrive as non-fatal `extra` divergences.

### `DetailedAccountReport` — from `Primary-API.md:1888`

```json
        "settlementDate":1669950000000
```

```
['settlementDate']
```

Inside the `GET /rest/risk/accountReport/REM7374` response at `:1817-1895`. Declared `int | None`
(epoch millis), which also keeps `test_null_object.py`'s `_perturb` dispatcher on its `cur is None`
branch (RESEARCH Pitfall 5).

**Deferred:** `currencyBalance` (`:1828-1859`, carrying an open-keyed `detailedCurrencyBalance` map)
and `availableToOperate` (`:1860-1887`, carrying a `cash` object with its own open-keyed
`detailedCash` map plus four siblings).

### `AccountReport.portfolio` — from `Primary-API.md:1894`

```json
    "portfolio":60240,
```

A bare number, not an object. The corroboration that makes "account market value" the reading
rather than "an object we failed to model": the identical value appears as `"totalMarketValue":60240`
for the **same account** in the detailed-position sample at `:1706`. Both citations are recorded as
a comment at the field, not only in planning docs.

## The depths are genuinely different, and stayed different

This was the plan's central risk and it is the success criterion most worth stating plainly:

| Field | Depth | Shape | Evidence |
|-------|-------|-------|----------|
| `DetailedPosition.report` | **2** | `dict[str, dict[str, InstrumentPositionReport]]` | `report` → `FUTURE_OPTION_CALL` → `SOJ.ROS/MAY23 380 C` → the record (`:1707-1790`) |
| `AccountReport.detailedAccountReports` | **1** | `dict[str, DetailedAccountReport]` | `detailedAccountReports` → `"0"` → the record (`:1826-1890`) |
| `AccountReport.portfolio` | **0** | `float \| None` | a bare number (`:1894`) |

Neither container was pushed toward the other. The asymmetry is recorded as a comment at **both**
field declarations, in both directions, so a future reader tempted to "harmonize" them finds the
measurement (37-RESEARCH F-7/F-8) rather than an unexplained inconsistency.

`report`'s depth-2 hint required **zero** changes to the axis: 37-02's `_apply_mapping_policy`
derives `dict[str, InstrumentPositionReport]` as the element, `_mapping_value` sees
`_is_mapping(element)` and self-recurses. The signature recorded in 37-02-SUMMARY was used as
written and never re-derived.

## Provenance — the phase's test of SC-1

Both new models declare **D-04a's third class** in those exact words. Each docstring states:

1. `Provenance: vendor-documented, UNMEASURED (D-04a's third class)` — with the exact line range;
2. that this is **not** a capture and must never be cited as one;
3. that *no live observation exists anywhere in this repo* and **nobody has seen this shape on the
   wire**;
4. that none can be produced while `LIVE-MATZ-33` stands — `main_matriz.py:2548-2556` asserts the
   remarkets hostname (D-MATZ-33) and it was **not** bypassed (T-37-16);
5. Phase 39 / `LIVE-NOBJ-01` as the named destination.

`InstrumentPositionReport`'s docstring also points one screen up at `TickPriceRange` and says the
contrast is deliberate: that class cites a committed capture with a date and an environment, this
one cites a document. Making the two classes distinguishable *from inside the file* is the whole
point of the third provenance class.

Each carries the closed-roster **cost disclosure** in the `MarketDataEntries` form — form copied,
content not: what closing the roster costs (an undeclared key is DISCARDED from the typed surface),
that detection is not silent (a non-fatal `extra` per key, reported even under `strict_decode`), and
the artifact where detection lands (`.planning/verification/matriz-client-findings.md`).

## The ledger rows (Task 3)

`max_existing_fid('matriz-client')` returned `10`; the next two sequential ids were allocated from
it rather than guessed. Both appended through `verification.findings.append_finding` with
`class_="SHAPE"`, `status="NO-FIX"` (terminal — declared-but-unobserved with no in-cycle fix
available), `surface="sync"` to match the existing rows, and `idempotent_by_title=True`.

| ID | Covers | Blocking cause | Destination |
|----|--------|----------------|-------------|
| F-11 | `DetailedPosition.report` / `InstrumentPositionReport` | `LIVE-MATZ-33` | Phase 39 `LIVE-NOBJ-01` |
| F-12 | `AccountReport.detailedAccountReports` / `DetailedAccountReport` | `LIVE-MATZ-33` | Phase 39 `LIVE-NOBJ-01` |

The AUTO-GENERATED region was never hand-edited. Idempotence was proven empirically, not assumed:
a third `append_finding` under an already-used title with a fresh `fid` was a verified no-op — no
`F-13` was added and no body changed (the probe left the file byte-identical modulo the ART
timestamp).

## Key Implementation Details

**`_decode.py` is byte-unchanged** across all five commits — `git diff --numstat` on it is empty and
`check_decode_intactness.py` is green. The axis, the models and the tests all live at the call site.

**`client.py` and `aio.py` untouched.** matriz has no `aio.py` at all for these endpoints; the
sync/async mirroring rule in CLAUDE.md is satisfied by construction here because both surfaces reach
these models through `_core.py`'s single parser pair.

**`_safemodel_classes()` is now 20** (was 18 after 37-02). Full roster:

```
AccountId, AccountReport, DetailedAccountReport, DetailedPosition, ExecutionReportFrame,
Instrument, InstrumentDetail, InstrumentId, InstrumentPositionReport, MarketDataEntryValue,
MarketDataFrame, MarketDataLevel, MarketDataSnapshot, NewOrderResponse, Order, OrderReport,
Position, Segment, TickPriceRange, Trade
```

`test_null_object.py`'s floor assertion is `>= 17`, so it is green as written; **Plan 37-05 raises
the floor to 20**, per this plan's output instruction. Not raised here.

**Both new models are mapping-free (F-11).** Stated executably rather than left as prose — two
tests assert `[n for n, t in get_type_hints(cls).items() if get_origin(t) is dict] == []`. This
matters most for `InstrumentPositionReport`, which now sits at depth 2 where
`test_no_mapping_carrying_model_is_ever_a_nested_field_type`'s single-level `__args__` walk cannot
see it. The constraint is load-bearing, and it is now checked rather than assumed.

**Only one untyped mapping annotation survives in matriz's models module:**

```
$ grep -nE '^\s+\w+: dict\[str, Any\]' packages/matriz-client/src/matriz_client/models.py
812:    raw: dict[str, Any] = field(default_factory=dict)
```

`UnknownFrame.raw` — the single documented exemption (D-01c), which Plan 37-04's gate will exempt by
class+field name.

**The REQUIREMENTS/ROADMAP naming slip is recorded in the code**, at the `report` declaration: both
documents say `AccountReport.report`, but `AccountReport` has no such field and never did. A later
verification pass reading only the requirement would otherwise hunt a field that does not exist.

**Path safety over two levels of vendor keys.** The divergence path for the deferred subtree is
`.report.FUTURE_OPTION_CALL.SOJ?ROS?MAY23?380?C.detailedPositions` — 37-02's `_safe_key` (lock 11)
neutralizes the `.`, `/` and spaces in the symbol so a vendor key cannot forge a path segment. The
test asserts the sanitized form verbatim, which is what makes the neutralization a checked contract
at depth 2 rather than an incidental property.

## Deviations from Plan

### Corrected plan references (not deviations in behaviour)

The plan's `read_first` line numbers for the test files were stale — they predated Plan 37-02's
additions. The committed assertions the plan describes were located by content instead:
`test_decode.py:524-527` (not `:465-475`) and `test_models.py:312/320-321` (not `:245-262`). The
same assertions, at their real locations; nothing about the plan's intent changed.

### Judgement calls, recorded

**1. Three vendor keys deliberately omitted from the `accountData` fixture**

`hasError`, `errorDetail` and `lastCalculation` (`Primary-API.md:1891-1893`) are present in the
vendor sample but are **not** declared fields of `AccountReport`. Including them verbatim would add
three `extra` records at the OUTER model, blurring the inner-extra count
`test_detailedAccountReports_deferred_objects_are_non_fatal_extras` asserts. They are omitted with a
comment stating explicitly that their absence is *not* a claim that the vendor omits them.

**2. `lastCalculation` omitted from the `detailedPosition` fixture, for a different reason**

The wire carries an epoch `int` while `DetailedPosition.lastCalculation` is annotated `str | None` —
the pre-existing mismatch 37-01 recorded as a follow-up and which this plan was told **not** to fix.
Including it would have made the strict-mode assertions fail for an unrelated reason. It is omitted
with a comment naming the mismatch and its out-of-scope status. **The field was not touched.**

**3. The serializer reordered one bullet of a pre-existing finding**

`append_finding` re-serialises the whole AUTO-GENERATED region, and F-09's `**Regression:**` bullet
moved from last position to above `Classification rationale` — the writer's canonical field order
asserting itself on a file whose stored order predated it. This is a **reorder, not a loss**, and it
was verified as such rather than eyeballed:

- every pre-existing `fid` survives (`lost fids: []`);
- every pre-existing finding's `(title, sorted bullet set)` is identical, F-09 included;
- the operator prose after `<!-- END AUTO-GENERATED -->` (Cycle Closure, the status table, the
  regression-link table, the CYCLE-REPORT caveat) is **byte-identical** by `diff`.

The D-23 regression this guard exists to prevent — destruction of neighbouring operator prose — did
not occur. No revert was warranted. Recording it because the plan's acceptance criterion said
"additions plus the ART timestamp line only", and a moved line is neither.

### Auto-fixed Issues

None. No bug, no missing critical functionality and no blocker was encountered; every task ran as
written. The three items above are judgement calls recorded for the record, not Rule 1-3 fixes.

## Known Stubs

None. No placeholder, no hardcoded empty flowing to a caller, no TODO or FIXME introduced. The `{}`
defaults on both mapping fields are the documented Null Object contract; the `| None` scalars are
declared absence, not stubs. The deferred subtrees are **not** stubs either — they are absent from
the model by decision and reported as divergences, which is the opposite of a silent placeholder.

## Threat Flags

None. This plan introduced no new network endpoint, auth path, file access pattern, or schema at a
trust boundary. All seven register dispositions were honoured:

- **T-37-11 (mitigate)** — the third provenance class is stated in both docstrings with the line
  range, the D-MATZ-33 blocking reason, and the explicit "nobody has seen this on the wire"
  sentence. Neither model is presented as observed (SC-1).
- **T-37-12 (mitigate)** — undeclared keys are discarded but reported as non-fatal `extra`
  divergences; the cost is disclosed in both docstrings and the detection artifact is named. Locked
  by `test_report_deferred_detailedPositions_is_one_non_fatal_extra` and
  `test_detailedAccountReports_deferred_objects_are_non_fatal_extras`, both under `STRICT_DECODE`.
- **T-37-13 (mitigate)** — every leaf is a `_SafeModel` of `| None` scalars; a non-dict container
  substitutes `{}` at either level. Locked by two chain-safety tests that sweep six and five payload
  shapes respectively, including a non-dict at the *inner* level.
- **T-37-14 (mitigate)** — a malformed `portfolio` now goes through the walker's float arm, reports
  a `type` divergence with `declared_type == "float"`, and is fatal under strict mode. Previously
  any non-dict value silently became `{}`. Locked by
  `test_portfolio_non_numeric_reports_a_type_divergence_and_is_fatal_under_strict`.
- **T-37-15 (mitigate)** — two `SHAPE` rows appended through `append_finding`, naming cause and
  destination; the append-only guard suite was re-run (22 passed) and the neighbour-integrity check
  was performed programmatically.
- **T-37-16 (mitigate)** — the hostname assert was never bypassed and no live run was attempted.
  Its absence is recorded in both docstrings and both ledger rows rather than worked around.
- **T-37-SC (accept)** — zero packages installed; `uv.lock` untouched.

## Deferred / Follow-ups

- **Both rosters are unverified against the live API** and cannot be verified before `LIVE-MATZ-33`
  lifts. Now recorded in two places: the docstrings and ledger rows F-11 / F-12. Destination: Phase
  39 / `LIVE-NOBJ-01`.
- **The deferred subtrees** — `detailedPositions` + `detailedDailyDiff`, and `currencyBalance` +
  `availableToOperate` — are named in the docstrings with their line ranges and their destination.
  They should be modelled from a **capture**, not from the document.
- **`DetailedPosition.lastCalculation` is annotated `str | None` but the wire carries an epoch
  `int`** — still open, inherited from 37-01. `models.py` was in scope here but that field is not
  one of this plan's three targets and the executor was instructed not to incidentally "fix" it. It
  is now also visible as a comment in the test fixture that omits it. Worth a disposition in the
  Phase 38 audit.
- **`test_null_object.py`'s roster floor is still `>= 17`** against an actual 20. Raising it is
  Plan 37-05's job per this plan's output instruction.
- **F-11's depth-2 blind spot is still answered by convention**, and this plan is where the
  convention started mattering: `InstrumentPositionReport` genuinely sits at depth 2. Both new
  models are asserted mapping-free, so option (a) holds. The day a Phase 37 inner model gains a
  mapping field, option (b) — deepening the guard's `__args__` walk — becomes mandatory.

## Verification Results

| Check | Result | Criterion |
|-------|--------|-----------|
| `pytest packages/matriz-client/tests -q` | **535 passed** | 510 baseline → strictly greater ✓ |
| `pytest packages -q` (whole repo) | **2042 passed**, 1 deselected | no cross-package regression ✓ |
| `mypy packages/matriz-client/src` | Success — 17 source files | ✓ |
| `ruff check packages/matriz-client` | All checks passed | ✓ |
| `ruff format --check packages/matriz-client` | 43 files already formatted | ✓ |
| `tools/check_decode_intactness.py` | Checks A–D green | ✓ |
| `tools/check_uniform_structure.py` | all 6 packages OK | ✓ |
| `tools/surface_parity.py` | OK | ✓ |
| `tools/check_surface_types.py` | 0 violations | still green pre-37-04 ✓ |
| `pytest verification/test_findings_append_only.py test_finding_count_consistency.py test_findings_dedupe_by_title.py` | **22 passed** | ✓ |
| `pytest verification/test_main_market_data_deep_chain.py test_safemodel_diff_null_object_links.py` | **14 passed** | the two guards the `lint` job runs ✓ |
| `dataclasses.fields(InstrumentPositionReport)` | `['instrumentInitialSize', 'instrumentFilledSize', 'instrumentCurrentSize']` | exactly the `:1745-1747` scalars ✓ |
| mapping fields on `InstrumentPositionReport` | `[]` | F-11 constraint holds ✓ |
| mapping fields on `DetailedAccountReport` | `[]` | F-11 constraint holds ✓ |
| `AccountReport.from_api({'accountName':'x'})` | `portfolio=None`, `detailedAccountReports={}` | prints `None {}` ✓ |
| `get_type_hints(DetailedPosition)['report']` | `dict[str, dict[str, InstrumentPositionReport]]` | two levels ✓ |
| `get_type_hints(AccountReport)['portfolio']` | `float \| None` | scalar ✓ |
| `grep -nE '^\s+\w+: dict\[str, Any\]' models.py` | **1 line**, `812: raw:` inside `UnknownFrame` | exactly one, and it is the exemption ✓ |
| `grep -c 'InstrumentPositionReport' models.py` | **4** | ≥ 3 ✓ |
| `grep -c 'DetailedAccountReport' snapshots/matriz-client-surface.txt` | **2** | ≥ 2 ✓ |
| `grep -c 'InstrumentPositionReport' snapshots/matriz-client-surface.txt` | **2** | ≥ 2 ✓ |
| `grep -c 'LIVE-MATZ-33' matriz-client-findings.md` | **2** | ≥ 2 ✓ |
| `grep -c 'LIVE-NOBJ-01' matriz-client-findings.md` | **2** | ≥ 2 ✓ |
| Index table row count | 10 → **12** | exactly two more, both SHAPE/NO-FIX ✓ |
| prose after `END AUTO-GENERATED` | byte-identical by `diff` | no D-23 regression ✓ |
| `git diff --numstat .../_decode.py` | empty | byte-unchanged ✓ |
| `_safemodel_classes()` | **20** | recorded for 37-05's floor raise ✓ |

## Success Criteria

- [x] `DetailedPosition.report` is a two-level typed mapping;
      `AccountReport.detailedAccountReports` is a one-level typed mapping;
      `AccountReport.portfolio` is `float | None`.
- [x] Both new inner models declare only scalars evidenced in the cited vendor line ranges and label
      their provenance as vendor-documented and unmeasured.
- [x] Deferred subtrees arrive as non-fatal `extra` divergences, not as invented models.
- [x] Two ledger rows record the unobserved rosters with the blocking cause and named destination.
- [x] Exactly one untyped mapping field annotation remains in `models.py`: `UnknownFrame.raw`.
- [x] `tools/check_surface_types.py` was NOT touched (Plan 37-04 owns it; RESEARCH Pitfall 3).
- [x] `ROADMAP.md` was not modified.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| `ac995d0` | test | RED — two-level `DetailedPosition.report` from the vendor sample (7 failed, 125 passed) |
| `b164d37` | feat | GREEN — `InstrumentPositionReport` + the two-level retype + exports |
| `a0cb9a5` | test | RED — one-level `detailedAccountReports` + `portfolio` as a scalar (12 failed, 130 passed) |
| `c519978` | feat | GREEN — `DetailedAccountReport`, the one-level retype, the `portfolio` demotion, the snapshot |
| `1696d52` | docs | F-11 / F-12 — both unobserved rosters declared in the findings ledger |

## Self-Check: PASSED

All six claimed files exist on disk. All five claimed commit hashes resolve in `git log`. All four
`must_haves.artifacts` `contains` probes hold (`models.py` ⊃ `class InstrumentPositionReport`;
`__init__.py` ⊃ `DetailedAccountReport`; `matriz-client-findings.md` ⊃ `SHAPE`; the snapshot ⊃
`InstrumentPositionReport`). Both `must_haves.key_links` patterns match in `models.py`
(`dict\[str, dict\[str, InstrumentPositionReport\]\]` and
`detailedAccountReports: dict\[str, DetailedAccountReport\]`). The working tree is clean.

## TDD Gate Compliance

Two full RED → GREEN pairs, in order, one per behaviour-adding task; Task 3 is a documentation
append with no behaviour and correctly carries no `tdd="true"`.

Each RED was verified to fail for the right reason before any implementation was written. Task 1
measured `7 failed, 125 passed`; Task 2 measured `12 failed, 130 passed`. Both counts are
**behavioural** failures rather than collection errors — the new symbols are reached through
`models.` / `matriz_client.` attribute access inside test bodies, never at import time, so the suite
still collected. Two Task-1 cases (`test_report_non_dict_still_substitutes_and_reports`,
`test_report_non_dict_is_fatal_under_strict_mode`) passed at RED on purpose: they pin container
contracts that must **survive** the retype, not new behaviour.

No REFACTOR commit was needed — both GREEN implementations landed in final shape. No test was
deleted or weakened to make a red go away. The two assertions that were inverted
(`portfolio == {}` → `is None`) were inverted because D-02 made the old claim **false**, and both
were kept in place with a comment rather than deleted, so the change is legible in the diff. The
`detailedAccountReports == {}` assertions stayed true and stayed as written. The matriz suite is
green at every commit of this plan.
