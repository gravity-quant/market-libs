---
phase: 29-decoder-observable
plan: 01
subsystem: api
tags: [decoder, observability, logging, dataclasses, typing, literal, policy]

# Dependency graph
requires:
  - phase: 28-verification-harness
    provides: "verification/schema.py `schema_of` type vocabulary and verification/findings.py `append_finding` SHAPE class, which the record schema is made compatible with"
provides:
  - "6-way `from_api` semantics matrix with every cell cited to a working-tree file:line"
  - "The seven `DecodePolicy` axes with concrete per-package constant tuples (higyrus/market-data, matriz, iol/ambito)"
  - "Three named exemptions the policy constant cannot express (received_at injection, Symbol key mirror + two-arg super, UnknownFrame catch-all)"
  - "12-lock aggregation contract: six-key record schema, four divergence kinds, level map, strict-mode disposition, dedupe triple, decode scope"
  - "Signed resolution of RESEARCH open decision 1 (strict never raises on `extra`)"
  - "Signed resolution of RESEARCH open decision 2 (dedupe key `(model, field_path, kind)`, request-scoped)"
  - "Signed D-09 policy: RESPONSE fields are never closed as `Literal` in this milestone"
affects: [29-02-walker, 29-03, 30-iol-typed, 31-ops-endpoints, 33-driver-runs, 34-publish]

actuals:
  tokens: 11774
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Policy-as-artifact: per-package semantic differences are recorded as declared policy axes with source citations, never harmonized"
    - "Reserved-LogRecord-safe structured `extra` schema (six flat str keys, no nested containers)"
    - "Signed one-way-door D-lock artifact with an operator signature block"

key-files:
  created:
    - .planning/phases/29-decoder-observable/29-SEMANTICS-MATRIX.md
    - .planning/phases/29-decoder-observable/29-AGGREGATION-CONTRACT.md
    - .planning/phases/29-decoder-observable/29-DLOCK-RESPONSE-LITERAL.md
  modified: []

key-decisions:
  - "Strict mode raises on `missing`, `type` and `non_dict` but NEVER on `extra` — reading criterion 2 literally would make Phase 33's strict driver run fail on every legitimate new vendor field"
  - "Dedupe key is the triple `(model, field_path, kind)` with the list index deliberately excluded, so N identically-diverging list elements collapse to one record"
  - "Dedupe scope is a per-decode-scope (request-bound) scope, never process-lifetime — a process-lifetime scope would make a second identical response decode silently clean"
  - "The divergence record carries six keys and NO `occurrences` counter — a true multiplicity would force a flush phase, two emission modes, and record loss on mid-decode process death"
  - "RESPONSE fields decode as `str`; out-of-set values are reported as divergences and returned unchanged, never enforced (D-09), reaching retroactively to matriz's 9 types.py aliases"
  - "The `Literal` walker branch validates the members' underlying runtime type while never enforcing set membership — silent on out-of-set values, loud on wrong runtime type"
  - "`literal_enforced` is `False` in all five copies and is documented as not a tunable"
  - "No row of the 6-way matrix is a bug to be fixed in Phase 29 — every difference is a declared policy axis"

patterns-established:
  - "Never-harmonize rule: a per-package semantic difference is resolved by parameterizing the policy, never by declaring one implementation correct"
  - "One-way-door decisions carry an in-artifact operator signature block (`Signed:` / `Date:` / `Decision recorded:`) so later phases can attribute their budget to a signed decision"
  - "Record contract is the primary redaction control; the RedactingFilter fix is defense in depth (types not values, never wire content)"

requirements-completed: [DEC-01]

coverage:
  - id: D1
    description: "6-way `from_api` semantics matrix with derived DecodePolicy constants per package and three cited exemptions"
    requirement: "DEC-01"
    verification:
      - kind: other
        ref: "grep -cE '^\\| [1-6] \\|' 29-SEMANTICS-MATRIX.md == 6 && grep -q 'literal_enforced|received_at|UnknownFrame'"
        status: pass
    human_judgment: true
    rationale: "The automated check proves row count and keyword presence, not cell accuracy. Each cell asserts a behavior read off a source file:line; only a human comparing the table against models.py can confirm no cell misstates a package's real from_api semantics — and Plan 02's walker is a literal transcription of these constants."
  - id: D2
    description: "12-lock aggregation contract resolving both RESEARCH open decisions (strict-on-extra, dedupe key + scope)"
    requirement: "DEC-01"
    verification:
      - kind: other
        ref: "grep for field_path|declared_type|observed_type|divergence >= 4 && grep -q 'non_dict' && grep -q 'append_finding'"
        status: pass
    human_judgment: true
    rationale: "The greps prove key vocabulary is present, not that all twelve locks are internally consistent or that the resolved decisions are the right ones. Phases 30-34 are built on locks 4 and 5; an ambiguous lock becomes five divergent implementations, which is the exact failure DEC-01 exists to eliminate."
  - id: D3
    description: "Both one-way-door decisions signed by the operator in-artifact"
    requirement: "DEC-01"
    verification:
      - kind: other
        ref: "grep -qE '^Signed: .+' in both 29-DLOCK-RESPONSE-LITERAL.md and 29-AGGREGATION-CONTRACT.md"
        status: pass
    human_judgment: false

# Metrics
duration: 24min
completed: 2026-08-18
status: complete
---

# Phase 29 Plan 01: Decoder policy artifacts Summary

**Three signed policy artifacts — the 6-way `from_api` semantics matrix with per-package `DecodePolicy` constants, a 12-lock aggregation contract resolving strict-on-extra and the dedupe key, and the D-09 lock keeping RESPONSE fields open as `str` — written before any decoder code exists.**

## Performance

- **Duration:** 24 min (includes a blocking-human checkpoint pause between task 2 and task 3)
- **Started:** 2026-08-19T01:33:00Z
- **Completed:** 2026-08-19T01:56:56Z
- **Tasks:** 3
- **Files modified:** 3 created, 0 source files touched

## Accomplishments

- **The semantics matrix exists before the decoder does (D-07).** Six `from_api` implementations across higyrus, market-data and matriz are tabulated with real working-tree line ranges, so Plan 02's walker is a transcription rather than a reinvention.
- **Per-package divergence is now a parameter, not an accident.** The seven `DecodePolicy` fields carry concrete constant tuples: `("", 0, 0.0, False, "from_api_none", False, False)` for higyrus/market-data/iol/ambito and `(None, None, None, None, "empty_classmethod", True, False)` for matriz — so five verbatim copies of `_decode.py` can share one file while preserving each package's real semantics.
- **Both RESEARCH open decisions are closed in writing and signed.** Strict mode never raises on `extra` (lock 4); the dedupe key is `(model, field_path, kind)` scoped to one decode scope (locks 5-6). Phase 33 can now budget its strict driver runs against a signed decision rather than an assumption.
- **The record schema is reserved-`LogRecord`-safe by construction.** Six flat `str` keys, no nested containers, types-not-values — which simultaneously satisfies the T-29-01 redaction posture and prevents `Logger.makeRecord` from raising and turning observable mode fatal (T-29-02).
- **D-09 is locked and reaches backwards.** matriz's nine `types.py` `Literal` aliases are explicitly named as covered; the evidence that this is behaviorally free (matriz `_convert` already ends in a bare pass-through) is recorded, so the change is reporting-only.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write the 6-way `from_api` semantics matrix (D-07)** - `8b3b69b` (docs)
2. **Task 2: Write the aggregation contract and the RESPONSE-Literal D-lock** - `daba077` (docs)
3. **Task 3: Checkpoint — sign the strict-on-extra and RESPONSE-Literal decisions** - `289902d` (docs)

**Plan metadata:** see the `docs(29-01): complete plan` commit.

## Files Created/Modified

- `.planning/phases/29-decoder-observable/29-SEMANTICS-MATRIX.md` (261 lines) - The 6-way `from_api` table with cited line ranges, the companion `empty()` table, the seven derived `DecodePolicy` axes with per-package constants, the three exemptions, and the "never harmonize" statement.
- `.planning/phases/29-decoder-observable/29-AGGREGATION-CONTRACT.md` (391 lines) - Twelve numbered locks: record schema, divergence kinds, level map, strict disposition, dedupe key, decode scope, emission timing/ordering, non-dict terminality, emitter safety, findings compatibility, redaction posture, filter recursion bounds. Signed.
- `.planning/phases/29-decoder-observable/29-DLOCK-RESPONSE-LITERAL.md` (164 lines) - The D-09 sign-off: RESPONSE fields decode as `str`, out-of-set reported not enforced, the nine matriz aliases named, the behavioral-freedom evidence, and the Phase 33 deferral. Signed.

## Decisions Made

The two one-way doors under checkpoint, plus the deviation bundled with them, were all resolved by the operator selecting **`approve-as-drafted`**:

- **(a) Strict mode never raises on extra wire keys.** Rationale recorded in lock 4: reading verification criterion 2 literally would make Phase 33's strict driver run fail on every legitimate upstream field addition — a divergence storm by construction, worsening the mass-divergence-discovery risk already flagged in STATE.md. Extra keys emit at INFO instead (lock 3).
- **(b) RESPONSE fields are never closed as `Literal` in this milestone.** Closing an alias requires a live census, which only Phase 33 has the credentials and pipeline to gather; closing early would be a silent behavior break on published surface. The D-lock explicitly scopes itself to RESPONSE fields — `Literal` on *input* parameters is left undecided.
- **(c) Six-key record, no `occurrences` counter.** This deviates from the `29-RESEARCH.md` seven-key draft and was therefore placed under the same signature. A true multiplicity forces a flush phase at scope close, two emission modes (request-scoped vs self-owned), and loses records if the process dies mid-decode — while the phase criterion asks for exactly one record per divergent field, not a count. Aggregate counting is Phase 33's job via the findings pipeline.

Because `approve-as-drafted` was selected, neither lock 4 nor lock 7 required a rewrite; the checkpoint resolved by filling signature blocks only.

## Operator's verbatim answer

> **approve-as-drafted** — signed by operator **sebadlf** (2026-08-18).
> Both decisions approved exactly as drafted: (a) strict mode never raises on extra wire keys (lock 4), (b) RESPONSE fields never closed as Literal. The six-key record schema without `occurrences` is also approved.

## Deviations from Plan

None - plan executed exactly as written.

The one deviation *from the research draft* (dropping the `occurrences` key) was planned deliberately in task 2 and placed under the task 3 signature, so it is a plan-specified decision rather than an executor deviation.

## Issues Encountered

- **Execution spanned two executor sessions.** Task 3 is a `gate="blocking-human"` checkpoint, so the first executor correctly halted after task 2 and returned checkpoint state rather than auto-approving. The continuation executor verified both prior commits and the three on-disk artifacts before resuming, and redid no completed work.

## Verification

- `grep -qE '^Signed: .+'` passes on both `29-DLOCK-RESPONSE-LITERAL.md` and `29-AGGREGATION-CONTRACT.md`.
- `uv run ruff format --check .` — 202 files already formatted.
- `uv run ruff check .` — All checks passed.
- `git status --porcelain packages/` — empty. No source file was touched by this plan, as required.

## Prohibitions status

Both plan prohibitions were carried as `flagged-unverified` and are now satisfied by the artifacts as written:

- *"The matrix must NEVER resolve a per-package semantic difference by declaring one implementation correct"* — satisfied. Every difference is a `DecodePolicy` axis; the matrix closes with an explicit "never harmonize" statement.
- *"The aggregation contract must NEVER specify a process-lifetime dedupe scope"* — satisfied. Lock 6 rejects it by name and gives the reason (a second identical response would decode silently clean).

## Known Stubs

None. This plan produces documentation artifacts only; no code, no placeholder data paths.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Plan 02 (the walker) is unblocked** and has a complete specification: the `DecodePolicy` field list and constants come from matrix section 2, the six-key record and dedupe triple from locks 1 and 5, the emission ordering from lock 7, and the `Literal` branch behavior from the D-lock.
- **Phases 30-34 have their signed foundation.** Phase 30 (`iol-client` typed) and Phase 31 (ops endpoints) may now write model surface against D-09; Phase 33 may budget its strict driver runs against lock 4.
- **Carried forward for Plan 02:** iol and ambito carry the higyrus/market-data constant tuple so the five copies stay verbatim, but iol's value must be **re-ratified when Phase 30 adds `models.py`** — this is recorded in matrix section 2 and is not a blocker for Phase 29.
- **No blockers.**

## Self-Check: PASSED

All 3 created artifacts + this SUMMARY verified present on disk; all 3 task commits (`8b3b69b`, `daba077`, `289902d`) verified present in git history.

---
*Phase: 29-decoder-observable*
*Completed: 2026-08-18*
