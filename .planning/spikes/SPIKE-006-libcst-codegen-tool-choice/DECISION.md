---
spike: 006
decision: TBD
signoff_date: TBD
signoff_by: TBD
evidence_checklist:
  item_1_byte_identical_ambito: TBD
  item_2_b8_identity: TBD
  item_3_ruff_format_check: TBD
  item_4_ruff_check: TBD
  item_5_mypy_strict: TBD
  item_6_ambito_pytest_green: TBD
  item_7_lint_imports: TBD
  item_8_marker_future_compat: TBD
  item_9_transformer_purity: TBD
  item_10_matriz_audit_denylist: TBD
matriz_audit_unresolved_rows: TBD
timebox_status: TBD
next_phase: TBD
refac_06_status: TBD
recommended_verdict: TBD
---

# SPIKE-006 — libcst Codegen Tool Choice Decision (v1.3)

> **STATUS: SKELETON** — `decision: TBD` awaiting Plan 03 aggregation + operator signoff.
> Plan 01 populates the inherited items (8, 10a, 10b); Plan 02 populates the GO-determining
> items (1, 4, 6) + 2, 3, 5, 9; Plan 03 re-runs the full 10-item checklist and the operator
> signs the binary GO/NO-GO here.

This decision artifact is the merge gate for Phase 18. It records the binary GO/NO-GO on
whether `libcst >=1.8.0,<2` is the right tool for REFAC-06 (single-source sync/async transport
shells), based on the 10-item D-RIGOR-02 evidence checklist + matriz audit + 1-day timebox,
evaluated under the STRICT un-migrated D-02 bar (no `aio.py` source migration).

## Evidence Checklist Summary

| # | Item | Status | Source |
|---|------|--------|--------|
| 1 (GO-det.) | Byte-identical round-trip vs CURRENT ámbito `client.py` | TBD | 001a/FINDING.md (Plan 02) |
| 2 | B8 identity preserved on generated | TBD | 001a/FINDING.md (Plan 02) |
| 3 | `uv run ruff format --check` clean | TBD | 001a (Plan 02) |
| 4 (GO-det.) | `uv run ruff check` clean (incl. I001 + ASYNC1xx) | TBD | 001a (Plan 02) |
| 5 | `uv run mypy --strict` clean | TBD | 001a (Plan 02) |
| 6 (GO-det.) | Ámbito mocked suite green vs generated (no circular self-import) | TBD | 001a (Plan 02) |
| 7 | `uv run lint-imports` 4 contracts intact | TBD | 001a (Plan 02) |
| 8 | `@generated` marker × `from __future__ import annotations` | TBD | 001b/FINDING.md (Plan 01) |
| 9 (new) | CSTTransformer subclasses pure `CSTNode → CSTNode`, no side-effects | TBD | 001a/FINDING.md (Plan 02) |
| 10a (new) | matriz construct audit: 0 unresolved rows | TBD | 001c/FINDING.md (Plan 01) |
| 10b (new) | matriz 4 deny-list files sha256-identical pre/post; `aio.py` transformed | TBD | 001d/FINDING.md (Plan 01) |

**Aggregate (filled by Plan 03):**

- Items PASS: TBD / 10
- Items FAIL: TBD / 10
- Matriz audit unresolved rows: TBD (D-SCOPE-02 gate: must be 0)
- Timebox: TBD

**Strict D-RIGOR-02 verdict:** TBD (any FAIL → NO-GO).

## Decision

`decision: TBD` — awaiting operator signoff (Plan 03).

## Recommendation

TBD — Plan 03 records the advisory recommendation and both GO / NO-GO routing branches.

Per 18-RESEARCH.md §Primary Recommendation, the honest likely outcome under the STRICT
un-migrated D-02 bar is a **second NO-GO for the same source-shape root cause** as SPIKE-005
(items 1, 4, 6 trace to source-absent content the transformer cannot synthesize without a
one-time aio.py migration). That negative result is an explicitly valid, guaranteed milestone
deliverable (D-08) — the spike does NOT soften the gate to manufacture a GO.

## Operator Signoff

**Verdict:** TBD
**Date:** TBD
**Operator:** TBD

**Rationale:** TBD (Plan 03).

## Linkage

- Evidence: `.planning/spikes/SPIKE-006-libcst-codegen-tool-choice/evidence-checklist.txt`
- Sub-experiment findings:
  - `001a-ambito-round-trip/FINDING.md` (Plan 02)
  - `001b-ambito-marker-future-compat/FINDING.md` (Plan 01)
  - `001c-matriz-construct-audit/FINDING.md` (Plan 01)
  - `001d-matriz-deny-list-config/FINDING.md` (Plan 01)
- Spike entry: `.planning/spikes/SPIKE-006-libcst-codegen-tool-choice/README.md`
- Phase plans: `.planning/phases/18-libcst-codegen-tool-choice-spike-spike-006/18-0{1,2,3}-PLAN.md`
- Prior art: `.planning/spikes/SPIKE-005-codegen-tool-choice/` (unasync NO-GO, 2026-06-14)
