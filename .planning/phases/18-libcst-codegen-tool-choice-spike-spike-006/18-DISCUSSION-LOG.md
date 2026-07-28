# Phase 18: libcst Codegen Tool-Choice Spike (SPIKE-006) - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-07-02
**Phase:** 18-libcst-codegen-tool-choice-spike-spike-006
**Mode:** assumptions
**Areas analyzed:** Sub-Experiment Decomposition, Transformer Scope & GO Bar, libcst Dependency
Handling, Decision Artifact & Timebox, Phase 19 Handoff Artifact

## Assumptions Presented

### Sub-Experiment Decomposition
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 4 sub-experiments mirroring SPIKE-005 001a–001d; item 9 folds into 001a; reuse 001c/audit.py verbatim; 001d sha256 under MetadataWrapper | Confident | `SPIKE-005/README.md:73-78`; `001c/audit.py` stdlib-`ast` tool-agnostic; `todo:113-116` |

### Transformer Scope & the GO Bar (item 1)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Byte-identity needs MORE than the 3 named transformers — must suppress aio-only close()/ResourceWarning/_REQUEST_TIMEOUT; GO bar is genuine PASS not soft path-to-PASS | Likely | `_validate_max_retries` def `client.py:41-62` / import `aio.py:34`; import-order `aio.py:32`; `aclose()` `aio.py:266-268`; ResourceWarning `aio.py:224-242`; `_REQUEST_TIMEOUT` `client.py:32` vs `aio.py:49`; SPIKE-005 `001a/FINDING.md` hunks H6/H7/H10 |

### libcst Dependency Handling
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Ephemeral `uv run --with 'libcst>=1.8.0,<2'`; pinned dev-dep deferred to Phase 19 | Likely | libcst absent from all pyproject/uv.lock; `SPIKE-005/README.md:40,50`; `REQUIREMENTS.md:56` puts pinned dep under REFAC-06 |

### Decision Artifact & Timebox
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| DECISION.md + evidence-checklist.txt at SPIKE-006 root; any-FAIL→NO-GO + Recipe-2 overlay; 24h D-SCOPE-03 cap inherited | Unclear (timebox) | `SPIKE-005/DECISION.md:1-20,52-53`; `evidence-checklist.txt:301-316`; **timebox NOT restated in REQUIREMENTS/ROADMAP for v1.3** |

### Phase 19 Handoff Artifact
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| GO handoff = 3 working canary-proven CSTTransformer drafts, asserted pure; not 4-package-generalized in spike | Likely | `ROADMAP.md:77`; `REQUIREMENTS.md:40`; `todo:120-121`; SPIKE-005 `DECISION.md:161,183` (iol/higyrus inferred) |

## Corrections Made

Two areas were surfaced to the operator as genuine decisions (not corrections of a wrong
assumption, but resolution of the two highest-impact / Unclear gray areas):

### Transformer Scope & GO Bar (item 1)
- **Question posed:** How should item 1 treat the legitimate divergence where generated sync
  `client.py` would differ from the hand-written one (hand-written omits `close()`/ResourceWarning)?
- **Operator decision:** **STRICT — match hand-written verbatim.** Build suppression transformers
  so generated output is byte-identical to the existing v1.1 `client.py`; ANY divergence =
  item-1 FAIL = NO-GO. No edits to `aio.py` source.
- **Reason:** Honors the CODEGEN-01 requirement literal + consistent with the operator's strict
  SPIKE-005 NO-GO reading; keeps the gate unambiguous.

### Timebox
- **Question posed:** The 24h D-SCOPE-03 cap is the one parameter not restated for v1.3 — what
  timebox governs SPIKE-006?
- **Operator decision:** **Inherit the 24h D-SCOPE-03 hard cap; over-cap → AUTO-NO-GO.**
- **Reason:** Strict inherited precedent, elected knowing libcst is slower to author.

## External Research

Not performed. Three libcst-API topics were flagged (round-trip trivia fidelity, cross-module
purity tension, docstring rewrite mechanics) but recorded in CONTEXT.md `<decisions>` §"Needs
Research" for the gsd-phase-researcher — resolving them **empirically is the spike's core work**,
so a pre-spike research agent would duplicate it.
