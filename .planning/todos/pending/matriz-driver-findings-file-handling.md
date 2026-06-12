---
title: matriz driver — dedupe D-MATZ-27 + preserve classification rationale on re-runs
created: 2026-06-10
source: Phase 5 re-run validation (post-completion observation)
priority: low
scope: main_matriz.py + verification/findings.py
resolves_phase: 11
---

# Two-bug bundle observed in `main_matriz.py` re-runs

Surfaced during Phase 5 close validation (operator re-ran `main_matriz.py` to
confirm reproducibility; this re-run exposed two driver-level issues that do
not affect Phase 5 deliverables but should be cleaned up before the next
verification cycle).

## Bug 1 — D-MATZ-27 EXPECTED terminal not deduped across runs

**Symptom:** every live run appends another `prod-vs-remarkets divergence
acknowledged` entry to `matriz-client-findings.md`. Phase 5 cycle ended with
F-02 + F-10 (two duplicates already); the post-completion re-run added F-11.
After N re-runs the file accumulates N+1 duplicate EXPECTED entries.

**Root cause:** `main_matriz.py` calls `append_finding(D-MATZ-27 EXPECTED)`
unconditionally near the end of `main()` instead of checking whether the
terminal entry is already present.

**Fix sketch:**
```python
# Before append_finding for D-MATZ-27 terminal:
if "prod-vs-remarkets divergence acknowledged" not in path.read_text():
    append_finding(...)
```

Alternative: extend `verification/findings.py::append_finding` with an
optional `idempotent_by_title=True` flag that no-ops if a finding with the
same title already exists.

## Bug 2 — Findings file is regenerated, not append-only

**Symptom:** post-completion re-run **destroyed** the 8
`Classification rationale (Phase 5)` lines that the operator added during
Task 3.3 of Plan 05-03 to document why each finding was NO-FIX or CONFIRMED.
The driver rewrote the file from scratch using only the wire-derived data
(F-01..F-08 base entries + auto-classification table), losing all
operator-added narrative.

**Root cause:** `append_finding` likely opens the file in write mode (`'w'`)
or regenerates via `write_text` rather than appending to existing content.

**Fix sketch:** rework `verification/findings.py::append_finding` to:

1. Read the existing file (if any).
2. Parse the Index table and per-finding sections.
3. **Merge** new findings with existing ones, preserving every line the
   driver did not author (operator rationale, manual classifications,
   etc.).
4. Write the merged result back atomically.

Equivalent design: distinguish "auto-generated" vs "operator-added" content
via a comment marker (e.g., `<!-- auto-generated below this line -->`) and
preserve everything above it on each run.

## Why this is low priority

- Phase 5 baseline (`docs(05): baseline DRIFT-02 cycle closure
  (verification-cycle-2026-Q2)` at commit `4d48e07`) is preserved with the
  full classification rationale via `git checkout --`.
- The dedupe bug is cosmetic (the duplicates are all EXPECTED terminals,
  not actionable findings).
- The classification-rationale loss is recoverable via git (any future
  re-run that overwrites can be reverted to the canonical baseline before
  re-classification).

## When to address

Before the next verification cycle (cycle-2026-Q3 or whenever Phase 6+
begins). Capturing these as a single deferred milestone item is the
cleanest path: a small refactor of `verification/findings.py` that affects
all 4 drivers (ámbito, iol, higyrus, matriz) since they all use the same
`append_finding` helper.

## Related

- `.planning/verification/CYCLE-REPORT.md` Open question #6 (deferred
  items) — extend that list with this entry on next cycle.
- D-MATZ-27 anchor in `05-04-PLAN.md`.
