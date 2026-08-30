# Phase 40: Releases breaking coordinados - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-30
**Phase:** 40-releases-breaking-coordinados
**Mode:** assumptions
**Areas analyzed:** Bump set, matriz-client changelog authorship, branch/PR vehicle,
two-checkpoint mechanic, market-data-client unresolved divergence

## Assumptions Presented

### Bump set — which packages get bumped

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| market-data-client 0.5.0→0.6.0, iol-client 0.3.0→0.4.0, matriz-client 0.2.0→0.3.0 bumped; ambito/wallets untouched | Confident | `34-CONTEXT.md` D-01 precedent; Phase 38 NOBJ-AUD-01 census (0 violations in higyrus/ambito/wallets) |
| higyrus-client's orphaned `get_health()` break (unpublished since Phase 31) — fold in or defer? | Unclear | `higyrus_client/client.py:450` already returns `Health`; `pyproject.toml` still `0.2.0`; README cites "Phase 34" as executor, but `34-CONTEXT.md` D-01 explicitly excluded higyrus |

### matriz-client changelog authorship

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Author `## Unreleased — BREAKING` section from scratch covering portfolio retype, 2 typed-mapping fields, envelope-unwrap fix, 6 additive aliases | Confident | `matriz-client/README.md` has no Changelog heading; `37-01..05-SUMMARY.md` document exact changes |
| matriz-client's missing `__version__` is not a release blocker | Confident | `release.yml:47` reads only `pyproject.toml`; matriz shipped v0.1.1/v0.2.0 without `__version__` |

### Branch/PR vehicle

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| New branch + new PR required (no reuse) | Confident | local `main` 180 commits ahead of `origin/main`; no open PR; no v1.7 remote branch |
| CI-green count = 15 checks | Likely | `ci.yml` unedited since Phase 34; matches Phase 34's own computed count |

### Two-checkpoint mechanic

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Two independent blocking checkpoints (pre-merge, pre-tag-push), merge commit real, tags on re-resolved merge SHA | Confident | `34-CONTEXT.md` D-08/D-09/D-10; `.planning/config.json` confirms yolo/auto_advance still active; Phase 39 D-02 reused same never-auto-resolve pattern |

### market-data-client unresolved market_id/active divergence

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Not automatically in-scope; must be surfaced as an explicit checkpoint item, not silently resolved either way | Unclear | `36-DEFERRED-market-data-leaves.md` names "Phase 40" as the natural venue, but `PUB-NOBJ-01`/Phase 39 never touched this decision |

## Corrections Made

No corrections — user selected "Yes, proceed" without singling out specific corrections.

For the two Unclear items (higyrus bump scope, market_id/active divergence), rather than silently
defaulting to either presented alternative, the decision was recorded as: **surface explicitly as
an operator checkpoint question during execution**, consistent with the project's own repeated
precedent (D-08/D-18) of never auto-resolving scope-adjacent decisions. This is a judgment call
made in CONTEXT.md (D-02, D-12) rather than a user-selected alternative — flagged here for
transparency.

## Auto-Resolved

Not applicable — `--auto` was not used.

## External Research

None — the analyzer agent returned an empty "Needs External Research" section; this phase is
entirely mechanical/repo-internal.
