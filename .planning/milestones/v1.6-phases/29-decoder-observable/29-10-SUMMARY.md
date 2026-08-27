---
phase: 29-decoder-observable
plan: 10
subsystem: testing
tags: [decode, divergence, sizing, observability, schema-corpus, safemodel, httpx]

# Dependency graph
requires:
  - phase: 29-05
    provides: "the shipped `_decode.py` walker in observable mode — `walk_model`, `open_request_scope`, the `(model, field_path, kind)` dedupe triple"
  - phase: 29-06
    provides: "the six-key divergence record vocabulary and the per-package logger names the counting handler attaches to"
  - phase: 29-07
    provides: "the aggregation contract locks (1 record vocabulary, 3 `extra`→INFO, 4 strict-fatal split, 5 scope-level dedupe) that make the count well-defined"
provides:
  - "A ratified per-package divergence floor: higyrus ≥ 22, matriz ≥ 24, market-data ≥ 50, iol N/A, ambito N/A, total modelled ≥ 96"
  - "The declared budget Phase 33's live census must measure itself against, directly comparable without translation"
  - "A 43-row mapping table covering the entire type-only schema corpus, with every N/A row carrying a written reason"
  - "Five structural model-versus-wire findings (S-1…S-5) routed to named destination phases"
  - "A written blind-spot statement establishing that the floor's error margin points upward only"
  - "An operator-signed ratification line making the floor citable as a committed budget"
affects: [30-typed-iol, 31-model-surface, 32-strict-mode, 33-live-verification, 34-release]

actuals:
  tokens: 8200
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Witness synthesis by inverting `verification/schema.py::schema_of` — type names become typed zero values"
    - "Measurement routed through the owning package's own `_core.parse_*` rather than mapping a schema file straight to a model class"
    - "Envelope keys read out of the parser's own source via `inspect.getsource` regex, never re-derived from the payload"

key-files:
  created:
    - .planning/phases/29-decoder-observable/29-SIZING.md
  modified:
    - .planning/STATE.md

key-decisions:
  - "The floor is published as a lower bound with the `≥` form, never as a bare number or an estimate"
  - "Packages with no `models.py` (iol, ambito) are reported N/A with a written reason, never as zero — a zero reads as clean"
  - "The corpus was rebased off the roadmap's `verification/snapshots/` (payload-free text files) onto `.planning/verification/schemas/` per D-08"
  - "Matriz witnesses are re-enveloped before the real parser sees them, using the key read verbatim out of the parser's own source — the prohibition on re-deriving the unwrap key holds"
  - "Ratified by sebadlf on 2026-08-19; Phase 33 must contrast its live census against the floor, and exceeding it requires an explicit re-scope with deferred findings routed to named phases"

patterns-established:
  - "Floor-not-estimate reporting: a measurement that feeds a downstream budget states its blind spot and the direction of its error margin in writing"
  - "N/A-not-zero: an unmeasurable package is marked not-applicable with a reason, because a false clean is the failure mode the milestone exists to remove"
  - "Ratification gate: a number becomes a committed budget only behind an operator signature line naming the phase that must measure against it"

requirements-completed: [DEC-01]

coverage:
  - id: D1
    description: "All 43 corpus files mapped to a parser and a model, or marked N/A with a specific written reason"
    requirement: "DEC-01"
    verification:
      - kind: automated_ui
        ref: "grep -cE '^\\| ' 29-SIZING.md → 74 (≥ 43 required); script asserts len(files) == 43 plus a two-way set difference between corpus keys and mapping keys"
        status: pass
    human_judgment: false
  - id: D2
    description: "Per-package floor published as a lower bound; the two packages with no models module marked N/A rather than zero"
    requirement: "DEC-01"
    verification:
      - kind: manual_procedural
        ref: "Operator read the floor table at the blocking checkpoint and ratified it verbatim"
        status: pass
    human_judgment: true
    rationale: "Whether a lower bound computed from ten-week-old evidence is acceptable as a downstream budget is a scope judgment only the operator can make; no test can assert it."
  - id: D3
    description: "Breakdown by kind sums to each package's floor and names the dominant silent-substitution class"
    requirement: "DEC-01"
    verification:
      - kind: other
        ref: "Arithmetic asserted in-report: 22+0+0+0=22; 0+0+18+6=24; 34+0+14+2=50; total 56+0+32+8=96"
        status: pass
    human_judgment: false
  - id: D4
    description: "Five structural model-versus-wire disagreements (S-1…S-5) named with package and field, each routed to a destination phase"
    requirement: "DEC-01"
    verification: []
    human_judgment: true
    rationale: "Whether each finding is a genuine defect or a legitimate market-closed / preview-endpoint shape needs live confirmation in Phase 33; the report deliberately does not fix any of them."
  - id: D5
    description: "Blind spot, freshness and consequence stated in writing; no package source modified by the measurement run"
    requirement: "DEC-01"
    verification:
      - kind: integration
        ref: "git diff --quiet HEAD -- packages/ → exit 0; uv run python tools/check_decode_intactness.py → exit 0; uv run pytest (3 packages) → 1082 passed"
        status: pass
    human_judgment: false
  - id: D6
    description: "Floor ratified by the operator and recorded in the project state file"
    requirement: "DEC-01"
    verification:
      - kind: automated_ui
        ref: "grep -qE '^Signed: .+' 29-SIZING.md → exit 0; STATE.md decisions list carries the [Phase 29 / 29-10] entry naming Phase 33"
        status: pass
    human_judgment: false

# Metrics
duration: ~15 min working (8h 53m wall clock including the ratification wait)
completed: 2026-08-19
status: complete
---

# Phase 29 Plan 10: Divergence sizing floor Summary

**A ratified per-package divergence floor — higyrus ≥ 22, matriz ≥ 24, market-data ≥ 50, total modelled ≥ 96 — measured by running the shipped walker in observable mode over witness payloads synthesized from the 43-file type-only schema corpus and routed through each package's own response parser, now the declared budget Phase 33's live census must measure itself against.**

## Performance

- **Duration:** ~15 min working; 8h 53m wall clock (2026-08-19T10:46 → 19:39 local), the gap being the blocking ratification checkpoint
- **Tasks:** 2 (1 auto, 1 blocking-human checkpoint)
- **Files modified:** 2 (`29-SIZING.md` created, `STATE.md` updated)

## Accomplishments

- **Published a floor, not an estimate.** Every modelled package's figure is written with the `≥` form. The total modelled floor is **≥ 96** unique divergence records (56 `missing`, 0 `type`, 32 `extra`, 8 `non_dict`), of which **64 are strict-fatal** under aggregation contract lock 4 — Phase 33's strict driver run should expect to be stopped by the first of those on each affected endpoint.
- **Named the dominant defect class with evidence.** `missing` is 56 of 96 (58%), and every one is the same shape: a field declared non-`Optional` arrives `null` and the decoder silently substitutes a typed zero. A consumer reading `posicion.precio` gets `0.0` and cannot distinguish "the price is zero" from "the API sent no price". That substitution is exactly what Phase 29 makes observable, and it is already the majority of the floor on a corpus of only 43 type-only captures.
- **Refused to report a false clean.** `iol-client` and `ambito-financiero-client` have no `models.py`; both are reported **N/A with a written reason**, never `≥ 0`. A zero would read as "clean", which is the precise failure mode this milestone exists to eliminate. iol becomes measurable only after Phase 30 (TYP-01).
- **Covered the corpus exhaustively.** All 43 files have a mapping row — 30 mapped to a parser and a model, 13 N/A with specific reasons. The row count is asserted by the script (`assert len(files) == 43` plus a two-way set difference between corpus keys and mapping keys), not eyeballed. Probe-named files were resolved by reading the driver that wrote each one, since `client_function` in the corpus is a probe name for well under half the corpus.
- **Found five structural model-versus-wire disagreements.** The highest-consequence is **S-3**: matriz's `Instrument.instrumentId` is absent on the byCFICode and bySegment endpoints where `marketId`/`symbol` arrive flattened, so the nested identity collapses to `InstrumentId.empty()` on every row while the two fields carrying the actual identity are reported `extra` and **discarded** — every consumer of `inst.instrumentId.symbol` reads empty, silently. **S-1** is the same envelope-unwrap failure already fixed twice in market-data (D-11, D-12) reappearing in `parse_instruments_response` and `parse_segments_response`.
- **Stated the blind spot and the direction of its error.** A type-only corpus cannot see non-finite numbers, out-of-set enumeration values (all nine matriz `types.py` aliases are untested by this floor), range/format violations, cross-field inconsistency, or heterogeneous collections — `schema_of` reduces a sequence to the *first* element, so the floor sees the best row, never the worst. **The margin points upward only.**
- **Gated the number behind a signature.** The floor became a citable budget only after the operator ratified it at a blocking checkpoint, and the ratification is recorded in STATE.md naming Phase 33 as the phase that must measure against it.

## Task Commits

Each task was committed atomically:

1. **Task 1: Run the sizing pass and write the floor report** — `36b79e2` (docs)
2. **Task 2: Checkpoint — ratify the floor as the declared downstream budget** — `86a7b5b` (docs)

**Plan metadata:** see final `docs(29-10): complete the divergence sizing floor plan` commit

## Files Created/Modified

- `.planning/phases/29-decoder-observable/29-SIZING.md` — the floor report: method (including the corpus rebase and the one deviation), the 43-row mapping table, the floor table, the breakdown by kind, five structural findings, the blind spot, per-package freshness, the consequence paragraph, and the signed ratification line
- `.planning/STATE.md` — decisions list entry recording the ratified floor and Phase 33's obligation to contrast against it

## Operator Ratification (Task 2)

**Verbatim response:** `ratified`

**Operator:** sebadlf — **Date:** 2026-08-19

Full response as given at the checkpoint:

> **ratified** — operator **sebadlf**, date **2026-08-19**.
> The per-package floors are accepted as the declared budget for the live-verification phase (Phase 33): higyrus-client ≥ 22, matriz-client ≥ 24, market-data-client ≥ 50, iol-client N/A (models arrive Phase 30), ambito-financiero-client N/A. Total modelled ≥ 96. The 5 structural findings (S-1..S-5) remain documented for in-cycle correction in Phase 33.

The signature block in `29-SIZING.md` now reads `Signed: "ratified" — sebadlf`, `Date: 2026-08-19`, with a `Decision recorded:` paragraph restating the floors, Phase 33's obligation, and the re-scope requirement. The task gate `grep -qE '^Signed: .+'` exits 0.

## Reproducing the measurement

The sizing script is throwaway and deliberately **not committed** — the deliverable is the report, and `git status --porcelain` confirms no script entered the repository.

**Exact invocation used for this run:**

```
uv run python /private/tmp/claude-501/-Users-admin-development-market-libs/13278da6-8b39-432e-bf19-efcd8a4cdccd/scratchpad/sizing.py
```

The script's full method is specified by the five steps in the report's Method section plus the mapping table, which is the only part that required reading the drivers. The witness synthesizer and the counting handler are about ten lines each.

## Decisions Made

- **The corpus named in the roadmap is the wrong one (D-08).** ROADMAP criterion 5 points at `verification/snapshots/`, which holds four public-surface `.txt` files with no payloads in them; `.planning/verification/captures/` is empty. The run was rebased onto `.planning/verification/schemas/` — the 43 type-only JSON files the live drivers write (ambito 1 / higyrus 5 / iol 4 / matriz 8 / market-data 25).
- **Route every witness through the owning package's own parser (D-06).** Mapping a schema file straight to a model class would walk the raw wrapper against an item model and produce a flood of artificial `missing`/`extra` reports. Going through the parser also makes the number directly comparable with Phase 33's live census without translation, since both runs emit the same six-key record through the same walker with the same dedupe triple.
- **`type` divergences are zero, and that is a property of the method.** The witness carries typed zero values synthesized from the corpus's type names, so a `type` divergence can only appear if the corpus recorded a type name differing from the declared type. It never did. The floor says nothing about live `type` divergences.
- **The floor is ratified as a budget with a re-scope clause.** If Phase 33's live census exceeds these numbers — which it will, since the blind spot only points upward — the overrun requires an explicit re-scope: every deferred finding routed to a named destination phase with its package and field recorded. Deferring without a destination, or silencing by narrowing the walker, is not an available option.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Matriz witnesses had to be re-enveloped before the real parser would accept them**

- **Found during:** Task 1 (sizing pass)
- **Issue:** The plan assumed the corpus uniformly stores the **raw wire envelope**. That holds for market-data (`main_market_data.py::_write_schema_snapshot` is fed the raw response body) but **not** for matriz: `main_matriz.py` stores the **already-unwrapped** collection, because each probe returns `raw["segments"]` / `raw["instruments"]` / `raw["marketData"]` rather than `raw` (verified at `main_matriz.py:602`, `:2229`, `:1479`). Handing a matriz witness straight to `parse_get_*_response` raised `PrimaryAPIError: missing envelope key` on all eight files and produced a matriz floor of **zero** — a silent undercount of exactly the kind this report exists to prevent.
- **Fix:** Each matriz witness is put back inside its envelope before the real parser sees it, under the key read **verbatim out of the owning parser's own source** via a regex over `inspect.getsource(parser)` matching `unwrap(data, "<key>", path)`. The key is never guessed and never inferred from the payload — the package still owns the answer to "which key holds the rows", and the script only reads that answer out of the package instead of receiving it pre-applied. Every matriz witness still routes through the real parser, so both the prohibition (T-29-54) and the comparability guarantee (D-06) hold. The re-envelope key used for each matriz file is recorded in the mapping table.
- **Files modified:** none in the repository — the change was to the throwaway script; the report documents the deviation in its own "One deviation from the plan's stated method, and why" section
- **Verification:** matriz's floor moved from a spurious 0 to ≥ 24; `git diff --quiet HEAD -- packages/` exits 0
- **Committed in:** `36b79e2` (Task 1 commit, as report text)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The deviation was necessary for correctness — the plan's stated method would have published a matriz floor of zero, which is both an undercount and a false clean. The fix preserves every guarantee the plan's prohibition was protecting. No scope creep; no package source touched.

## Issues Encountered

- **Probe-named corpus files.** `client_function` in the corpus is a probe name rather than an API function name for well under half the corpus, so automatic resolution was not viable. Resolved by reading each of the five drivers and following the client method through to `_core.parse_*`; every probe-named row in the mapping table cites the driver line that resolved it (e.g. `main_market_data.py:1469` → `client.get_symbols(prefix=_PROBE_PREFIX)`).
- **Two empty captures.** `higyrus/get-listado-cuentas` and `matriz/get-trades` recorded `schema: []` — the live wire returned no rows. Both are counted as walked-but-zero with a note that this is **not** evidence of a clean model, and both are named in the blind-spot section as endpoints whose divergences cannot be in this number.
- **`INFO`-level records were initially dropped.** The counting handler had to be attached at `DEBUG` level, otherwise the 32 `extra` records (emitted at `INFO` per aggregation contract lock 3) would not have been counted.
- **`git status` noise.** Three untracked `.planning/research/.cache/*.json` files and an untracked `.gsd/` directory predate this plan and are unrelated to it; left untouched per the scope boundary.

## User Setup Required

None — no external service configuration required. The run reads no environment file and no live endpoint; the corpus is type-only and stores no values (T-29-57).

## Next Phase Readiness

- **Phase 33 is unblocked and now has a declared budget.** It must contrast its live census against higyrus ≥ 22 / matriz ≥ 24 / market-data ≥ 50 / total ≥ 96, and the two runs are directly comparable without translation.
- **Five structural findings are queued with named destinations:** S-1 → Phase 33 live re-verification of `GET /instruments` and `GET /instruments/segments`; S-2 → Phase 33 / TYP-02 (the preview response wants its own model); S-3 → Phase 33 live confirmation then Phase 30/31 model work; S-4 → Phase 31 / TYP-03 coverage gap; S-5 → Phase 33 recapture during market hours to decide `Optional` versus defect.
- **Caveat carried forward:** three of the five corpora are roughly ten weeks old, and matriz's capture is a market-closed snapshot (`BI`/`OF` empty), which shapes which divergences it could contain at all. Staleness weakens the floor's currency but not its validity as a lower bound.
- **Phase 29 verification is green:** `uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q --no-cov` → **1082 passed** (plan floor: ≥ 872); `uv run python tools/check_decode_intactness.py` → exit 0 (all five `_decode.py` copies still reduce to one normalized hash `a5889d5778f11dde`); `git diff --quiet HEAD -- packages/` → exit 0.

---
*Phase: 29-decoder-observable*
*Completed: 2026-08-19*

## Self-Check: PASSED

All claimed artifacts verified on disk (`29-SIZING.md`, `29-10-SUMMARY.md`); both task commits (`36b79e2`, `86a7b5b`) verified in git history; the task-2 gate `grep -qE '^Signed: .+'` exits 0.
