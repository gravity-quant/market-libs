---
phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
plan: 01
status: in-progress
---

# Phase 33 Plan 01: TRACER — divergence handler wired through higyrus get_health Summary

## Title convention (locked)

**Selection (verbatim): `surface-in-title-write-new`**

Resolved under auto-mode (`workflow.auto_advance: true`, `mode: yolo`) as the first-listed
option of the Task 1 `checkpoint:decision`, which the plan itself annotates as
"the RESEARCH-recommended default (Open Question 1)". Recorded here per the task's
`<resume-signal>`: Task 2's title format and 33-05's census table both read from this section.

### (a) The surface IS embedded in the title

The exact f-string `DivergenceHandler.emit` uses, byte-for-byte:

```python
title=f"{model}{path}: {kind} (declared={declared}, observed={observed}) [{surface}]"
```

where every interpolated name comes ONLY from the frozen six-key record
(`model`, `field_path`, `divergence`, `declared_type`, `observed_type`) plus the
`surface` this module itself bound via `_SURFACE` — never from a wire value
(prohibition P-01 / T-33-01 / Lock 11).

Consequences that downstream plans must honour:

- The cross-run `idempotent_by_title` dedupe identity is
  `(model, field_path, kind, declared, observed, surface)` — six components, surface included.
- A sync-only or async-only divergence is therefore visible as its own finding, which is
  what criterion 1 asks for.
- **The finding count is roughly 2× the distinct-triple count.** `33-CENSUS.md` (plan 33-04)
  and `33-LITERALS.md` (plan 33-05) MUST report and label BOTH numbers so the ≥96 floor
  contrast is not misread.
- **The census unit is never the finding count.** It is `DivergenceHandler.seen`, a set of
  distinct `(slug, model, field_path, kind)` 4-tuples — the only unit directly comparable
  to `29-SIZING.md` without translation (D-06, aggregation-contract locks 1 and 5).

### (b) matriz `F-03`..`F-08` disposition: write six NEW findings

The six hand-written `NO-FIX` records `F-03`..`F-08` in
`.planning/verification/matriz-client-findings.md` (the S-4 `extra` keys on
`InstrumentDetail`: `securityIdSource`, `securityType`, `settlType`, `strike`, `symbol`,
`underlying`) are **NOT** absorbed by title matching.

- The handler writes six new `OPEN` `SHAPE` findings alongside them, under the deterministic
  title format above.
- Those six are then triaged to `NO-FIX` **referencing the original fid** in their triage prose.
- No bespoke per-finding title table is introduced inside the handler — that would be the exact
  hand-rolled pattern D-07 deletes elsewhere in this phase, and any drift between the table and
  the real titles would silently revert to writing duplicates anyway.
- The six original records keep their operator prose and their `NO-FIX` disposition untouched:
  `append_finding`'s non-`OPEN` short-circuit preserves them byte-identically.

### Task 1 acceptance

No source file was modified by this task — `git status --porcelain verification/ main_higyrus.py`
was empty at the end of it. The only artifact is this section.

<!-- gsd:write-continue -->
