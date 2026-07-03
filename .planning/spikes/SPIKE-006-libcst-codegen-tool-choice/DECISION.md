---
spike: 006
decision: TBD
signoff_date: TBD
signoff_by: TBD
evidence_checklist:
  item_1_byte_identical_ambito: FAIL
  item_2_b8_identity: PASS
  item_3_ruff_format_check: FAIL
  item_4_ruff_check: PASS
  item_5_mypy_strict: PASS
  item_6_ambito_pytest_green: FAIL
  item_7_lint_imports: PASS
  item_8_marker_future_compat: PASS
  item_9_transformer_purity: PASS
  item_10_matriz_audit_denylist: PASS
matriz_audit_unresolved_rows: 0
timebox_status: WITHIN-CAP
next_phase: 19_DROPPED_on_NO-GO
refac_06_status: PERMANENTLY_SHELVED_on_NO-GO
recommended_verdict: NO-GO
---

# SPIKE-006 — libcst Codegen Tool Choice Decision (v1.3)

> **STATUS: DRAFT — awaiting operator signoff (Task 18-03-02).**
> The 10-item verdict map, the strict D-04 aggregate, and the D-07 timebox status below are
> mechanically computed from the four sub-experiment FINDINGs and are final as evidence. The
> frontmatter `decision:` + `signoff_by`/`signoff_date` are intentionally left `TBD` — the operator
> signs the binary GO/NO-GO here (D-06 / T-18-07 repudiation mitigation). The executor does NOT
> self-sign.

This decision artifact is the merge gate for Phase 18. It records the binary GO/NO-GO on
whether `libcst >=1.8.0,<2` is the right tool for REFAC-06 (single-source sync/async transport
shells), based on the 10-item D-RIGOR-02 evidence checklist + matriz audit + 1-day timebox,
evaluated under the STRICT un-migrated D-02 bar (no `aio.py` source migration).

## Evidence Checklist Summary

| # | Item | Status | Source |
|---|------|--------|--------|
| 1 (GO-det.) | Byte-identical round-trip vs CURRENT ámbito `client.py` | **FAIL** (13 hunks / 383 lines; content-absence root cause) | 001a/FINDING.md (Plan 02) |
| 2 | B8 identity preserved on generated | **PASS** (same object id across mod/aio/_core) | 001a/FINDING.md (Plan 02) |
| 3 | `uv run ruff format --check` clean | **FAIL** (length-changing swap left aio.py multi-line wrapping) | 001a (Plan 02) |
| 4 (GO-det.) | `uv run ruff check` clean (incl. I001 + ASYNC1xx) | **PASS** (`All checks passed!` — the item unasync FAILED) | 001a (Plan 02) |
| 5 | `uv run mypy --strict` clean | **PASS** (`Success: no issues found`) | 001a (Plan 02) |
| 6 (GO-det.) | Ámbito mocked suite green vs generated (no circular self-import) | **FAIL** (circular self-import `_validate_max_retries`) | 001a (Plan 02) |
| 7 | `uv run lint-imports` 4 contracts intact | **PASS** (`4 kept, 0 broken`) | 001a (Plan 02) |
| 8 | `@generated` marker × `from __future__ import annotations` | **PASS** (STRICT — all 4 commands exit 0; marker-neutral) | 001b/FINDING.md (Plan 01) |
| 9 (new) | CSTTransformer subclasses pure `CSTNode → CSTNode`, no side-effects | **PASS** (class-level; `vars(t)` unchanged across visit; 14/14) | 001a/FINDING.md (Plan 02) |
| 10a (new) | matriz construct audit: 0 unresolved rows | **PASS** (110 rows, 0 unresolved vs 959-LOC aio.py) | 001c/FINDING.md (Plan 01) |
| 10b (new) | matriz 4 deny-list files sha256-identical pre/post; `aio.py` transformed | **PASS** (4/4 byte-identical; aio.py transformed) | 001d/FINDING.md (Plan 01) |

**Aggregate (Plan 03):**

- Items PASS: **7 / 10** (items 2, 4, 5, 7, 8, 9, 10 — item 10 = 10a AND 10b)
- Items FAIL: **3 / 10** (items 1, 3, 6)
- Matriz audit unresolved rows: **0** (D-SCOPE-02 gate satisfied)
- Timebox: **WITHIN-CAP** (~28m since README spike start; cumulative Plans 01+02+03 far under the 24h D-07 cap)

**Strict D-RIGOR-02 verdict:** **NO-GO** (any item FAIL → NO-GO; items 1/3/6 FAIL).

## Decision

`decision: NO-GO` is the **recommended / mechanically-computed** aggregate (strict D-04 reading) —
**awaiting operator signature** in the frontmatter and the Operator Signoff section below. The
executor draft does NOT set the signed `decision:` field; the operator ratifies the binary verdict,
the item-9 class-level purity reading (Q2), and the residual docstring-divergence disposition (Q3).

Under D-04, GO would require all 10 items genuine PASS AND matriz audit 0-unresolved AND WITHIN-CAP.
Three items FAIL (1, 3, 6), so the strict aggregate is NO-GO regardless of the (satisfied) matriz-audit
and timebox gates. No operator discretion can convert the FAILs into a GO without softening the gate,
which D-04/D-08 forbid.

## Recommendation

**Recommended verdict:** **NO-GO** (strict D-RIGOR-02) — REFAC-06 permanently shelved (D-08).

**Rationale:**

1. **Same source-shape root cause as SPIKE-005.** The decisive GO-determining FAILs (items 1 and 6)
   trace to content that is *absent from `aio.py`* and cannot be synthesized by any pure single-file
   transform:
   - `_validate_max_retries` is *defined* only in `client.py:41-62` (a 22-line function) and merely
     *imported* at `aio.py:34` (`from ambito_financiero_client.client import _validate_max_retries`).
     A pure transform of `aio.py` cannot invent that body, so `ImportDirectionNormalizer` honestly
     RETAINED the self-import — which makes the generated `client.py` import the name FROM ITSELF,
     reproducing the EXACT SPIKE-005 `ImportError … partially initialized module … circular import`
     (item 6 FAIL).
   - The `from dotenv import load_dotenv` bootstrap + `load_dotenv()` (client.py:25/30) is absent from
     `aio.py` (D-19), contributing to the item-1 residual.

2. **Item 3** is the length-changing docstring / `__reduce__`/`__deepcopy__` TypeError-string
   divergence: the `AmbitoFinancieroAsyncClient` → `AmbitoFinancieroClient` swap shortened those
   strings while libcst preserved `aio.py`'s original multi-line wrapping. Plus independently
   hand-authored prose divergence (`with_options` 43-vs-19 lines, module docstring) that is NOT a
   mechanical label swap and would require embedding the `client.py` oracle in the tool (rejected as
   non-single-sourcing).

3. **libcst is NOT a regression — it is a partial capability gain.** Item 4 (`ruff check`, I001 +
   ASYNC1xx), which unasync/SPIKE-005 FAILED, now PASSES under libcst: `ImportNormalizer` closes the
   single-line import-order and `AsyncToSync` fully strips async, leaving zero ASYNC1xx. Items 5/7/9
   also PASS. The gap is purely the content-absence boundary, not tool defect.

4. **All inherited Wave-1 evidence PASS unconditionally:** item 8 marker (STRICT, all 4 commands exit
   0), item 10a matriz audit (110 rows, 0 unresolved vs the current 959-LOC `aio.py`), item 10b
   deny-list (4/4 sha256-byte-identical pre/post; `aio.py` transformed). The matriz deny-list (D-09)
   is CONFIRMED out of codegen scope, not renegotiated.

5. **Timebox WITHIN-CAP and matriz audit 0-unresolved** — neither D-07 (timebox) nor D-SCOPE-02
   (audit) AUTO-NO-GO trigger fired; the NO-GO is evidence-driven from items 1/3/6.

**Why NO-GO (not "GO with a source migration").** SPIKE-005 already advised a ~30-LOC `aio.py`
source migration would flip its 3 FAILs to PASS. The v1.3 libcst spike was the dedicated retest of
whether an AST-level tool could cross the content-absence boundary *without* that migration (D-02
STRICT). It cannot — libcst relocates/rewrites existing nodes but never synthesizes source-absent
content. Two spikes (token-level unasync + AST-level libcst) now independently reach the same
NO-GO for the same root cause under the un-migrated bar. Per D-08 the honest close-out is to
**permanently shelve REFAC-06**, DROP the Phase 19 GO-branch, and accept the duplicate
`client.py`/`aio.py` shells as a structural feature of the codebase.

## Q2 — item-9 purity scope ratification (operator)

Item 9 is interpreted at the **CLASS level** (RESEARCH A3): each of the five `CSTTransformer`
subclasses is a pure `CSTNode → CSTNode` function (`vars(instance)` byte-identical before/after
`module.visit()`; no cross-node mutable accumulation, no I/O, no global reads). `ImportDirectionNormalizer`
takes an **immutable** `frozenset` config at `__init__` (read-only closed-over constant — not
accumulation). All cross-module / scope-aware orchestration (module-level-def scan, `close`-delegator
drop, `@generated` marker insertion) lives ONLY in the **impure driver** `experiment.py`. Operator
ratifies this class-level reading. (Moot for the verdict — items 1/3/6 already force NO-GO — but
recorded for completeness.)

## Q3 — residual docstring divergence disposition (operator)

`DocstringLocalizer` performs only mechanical swaps (`asincrónico→sincrónico`, `AsyncClient→Client`,
strip `await `). Independently hand-authored prose (module docstring, `with_options` 43-vs-19,
per-method docstrings, the length-changed TypeError strings) remains in the item-1 residual. Closing
it would require emitting the entire target literal per module (embedding the `client.py` oracle in
the tool — not single-sourcing, rejected). Operator disposition: treat residual docstring divergence
as **item-1 FAIL** under the strict D-02 reading (→ NO-GO), consistent with the recommendation.

## Operator Signoff

**Verdict:** TBD (operator sets GO or NO-GO)
**Date:** TBD
**Operator:** TBD

**Rationale:** TBD — operator ratifies the strict D-04 aggregate (recommended NO-GO), the item-9
class-level purity reading (Q2), and the residual docstring-divergence disposition (Q3). To sign:
set frontmatter `decision:` + `signoff_by` + `signoff_date`, fill this section, and (on NO-GO) the
drafted `NO-GO.md` close-out becomes effective.

## Routing After Signoff

- **On NO-GO (recommended):** `NO-GO.md` close-out becomes effective — REFAC-06 PERMANENTLY shelved,
  Phase 19 (GO-branch) DROPPED, duplicate `client.py`/`aio.py` shells accepted as a structural
  feature. Project-state governance (REQUIREMENTS.md REFAC-06 status, ROADMAP.md Phase 19 drop,
  CLAUDE.md / `spike-findings-codegen-market-libs` Skill update, 18-SUMMARY.md) lands in the
  post-signoff continuation.
- **On GO (not recommended on this evidence):** `GO-handoff.md` would promote the `001a/transformers/`
  classes as canary-proven Phase 19 drafts. Not applicable given 3 FAILs.

## Linkage

- Evidence: `.planning/spikes/SPIKE-006-libcst-codegen-tool-choice/evidence-checklist.txt`
- Sub-experiment findings:
  - `001a-ambito-round-trip/FINDING.md` (items 1/2/3/4/5/6/7/9; Q1 content-absence, Q2 purity, Q3 docstring)
  - `001b-ambito-marker-future-compat/FINDING.md` (item 8)
  - `001c-matriz-construct-audit/FINDING.md` (item 10a)
  - `001d-matriz-deny-list-config/FINDING.md` (item 10b)
- Item-1 diff transcript: `001a-ambito-round-trip/diff_vs_current_client.txt`
- Close-out: `.planning/spikes/SPIKE-006-libcst-codegen-tool-choice/NO-GO.md`
- Spike entry: `.planning/spikes/SPIKE-006-libcst-codegen-tool-choice/README.md`
- Phase plans: `.planning/phases/18-libcst-codegen-tool-choice-spike-spike-006/18-0{1,2,3}-PLAN.md`
- Prior art: `.planning/spikes/SPIKE-005-codegen-tool-choice/` (unasync NO-GO, 2026-06-14)
