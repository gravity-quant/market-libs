# Phase 41: Validación Nyquist retroactiva de v1.7 - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-31
**Phase:** 41-validaci-n-nyquist-retroactiva-de-v1-7
**Mode:** assumptions
**Areas analyzed:** Artifact shape & write target, Unit of disposition, Execution mechanism of `/gsd-validate-phase`, Front-matter semantics & mechanical-closure risk

## Assumptions Presented

### Artifact shape & write target

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Update the 5 existing `{N}-VALIDATION.md` files in place, not new `41-*` files | Confident | ROADMAP.md:75; stock validate-phase workflow write-back path |
| SHA declared = v1.7 tag commit, with tree-identity proof | Confident | `git diff v1.7 HEAD -- . ':(exclude).planning'` empty, verified this session |

### Unit of disposition

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Denominator = Per-Task Verification Map rows + Manual-Only rows (51 total), not the 25 v1.7 ROADMAP criteria | Likely | ROADMAP.md:74 wording "filas"; PITFALLS.md Pitfall 4 |
| `VERIFIED-NOW` will dominate over `VERIFIED-HISTORICALLY` | Likely | 15 cited test files across 4 populated maps verified to exist on disk |
| Phase 35 is a structural exception — reconstruct ~14 real rows from PLAN.md verify-blocks | Confident | 35-VALIDATION.md single placeholder row measured |

### Execution mechanism of `/gsd-validate-phase`

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Run skill 5×, never take the fix-gaps path (no gsd-nyquist-auditor spawn) | Confident | validate-phase.md §4; gsd-nyquist-auditor.md job = writing tests |
| Point requirements/roadmap resolution at v1.7 archived files, not root files | Confident | `init.phase-op 35` resolves root files, which now hold v1.8 IDs |
| Every VERIFIED row gets a 4th column naming CI enforcement surface | Confident | 52 files match `verification/test_*.py`, only 12 in ci.yml allowlist |

### Front-matter semantics & mechanical-closure risk

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| "Lock" = new executable test file; expected count zero | Likely | REQUIREMENTS.md cross-phase precondition table; SUMMARY.md |
| End state: `status: validated`, `nyquist_compliant` stays false on all 5 (PARTIAL) | Confident | Inline lifecycle comment in front-matter of 35/36/37/38; audit-milestone §5.5 |
| Main risk = "staleness laundering" (mechanical box-flip without re-execution) | Confident | PITFALLS.md Pitfall 4/5; v1.7-MILESTONE-AUDIT.md precedent of independent re-derivation |

## Corrections Made

No corrections — all assumptions confirmed ("Yes, proceed").

## External Research

No research performed — `/gsd-validate-phase` is a local skill/workflow/agent, fully readable on disk; the analyzer confirmed no external-library unknowns.
