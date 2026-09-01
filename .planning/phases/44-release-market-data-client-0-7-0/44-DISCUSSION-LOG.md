# Phase 44: Release `market-data-client` 0.7.0 - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-31
**Phase:** 44-release-market-data-client-0-7-0
**Mode:** assumptions
**Areas analyzed:** Version bump mechanics, README changelog + migration table, Scope (fold
DRV-MD-SEG-43 / SURF-MD-FEEDSUB-43), Two-gate mechanics

## Assumptions Presented

### Version bump mechanics
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 4 version sites = pyproject.toml:3, __init__.py:163, README.md:15, README.md:24 (not uv.lock, not the version test) | Confident | `PITFALLS.md:258`, live grep of README |
| release.yml zero edits (7th reuse); uv lock runs exactly once, after all 4 sites bumped | Confident | `git log -1 -- release.yml` = 2026-05-09, unchanged across 6+ releases |

### README changelog + migration table
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| New `### v0.7.0` section directly above `### v0.6.0`, no "Unreleased" staging section | Confident | No README in the repo (market-data-client or iol-client) uses an "Unreleased" heading |
| Two separate tables (Instrument, Segment), transcribed from `43-DISPOSITION.md` §1.1/§1.2 | Likely | `43-DISPOSITION.md:41-53` (6-col engineering format); `models.py:894-895` confirms shipped shape |

### Scope — fold DRV-MD-SEG-43 / SURF-MD-FEEDSUB-43
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Fold SURF-MD-FEEDSUB-43 (one-line `__all__` fix); defer DRV-MD-SEG-43 to Phase 45 | Unclear (recommendation) | `__init__.py:104-156` missing `FeedSubscription`; `ROADMAP.md:240-241`; `ROADMAP.md:62,175` names Phase 45 as harness cleanup |

### Two-gate mechanics
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| New branch required (`milestone/vX.Y-...` pattern); no branch/PR exists today | Confident | `git rev-list --count origin/main..HEAD` = 84; `gh pr list` no open PR, highest #15 merged |
| Two `autonomous: false` plans, each with one `gate="blocking-human"` checkpoint (merge, tag push) | Confident | `gate="blocking"` (missing `-human`) confirmed in Phase 34 (34-02/34-03) **and** Phase 40 (40-01/40-02/40-03) — 3 phases, not 1 |
| `<verify>` blocks via `bash -c`; all counts re-derived live | Confident | Phase 40 measured zsh word-splitting failure + a stale hardcoded tag count |
| Merge gate counts 15/15 CI checks explicitly, not absence-of-failure | Confident | `ci.yml`: 4 jobs, test matrix 6×2=12, total 15; Phase 34 precedent caught a real fail + a transient race this way |

## Corrections Made

No corrections — all assumptions confirmed as presented, including the Unclear scope-fold
recommendation (fold SURF only, defer DRV to Phase 45).

## Auto-Resolved

Not applicable — not run in `--auto` mode.

## External Research

None performed — the analyzer's `Needs External Research` output was empty. Every mechanic has
an in-repo, measured precedent across Phases 28, 34, and 40.

## Notes on Analysis

The `gsd-assumptions-analyzer` subagent corrected two premises the orchestrator's initial scouting
had gotten wrong before presenting assumptions to the user:

1. The 4 version sites are pyproject.toml + `__init__.py` + **two README install lines** — not
   pyproject/`__init__`/uv.lock/version-test as initially scoped. `uv.lock` and the version test
   are separate concerns (an artifact refreshed once, and a verifier, respectively).
2. The `gate="blocking"` (missing `-human`) authoring defect has occurred in **both** Phase 34 and
   Phase 40 — three prior phases carrying the pattern (34-02, 34-03, 40-01, 40-02, 40-03), not the
   single occurrence the orchestrator's initial framing implied. This raises Phase 44's version of
   this checkpoint from "second strike" to explicitly the fourth-and-fifth instance, reinforcing
   why criterion 4 requires plan-file-level verification rather than relying on another orchestrator
   override.
