# Phase 24: Release prep + publish v0.1.0 - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-07-31
**Phase:** 24-release-prep-publish-v0-1-0
**Mode:** assumptions
**Areas analyzed:** CI matrix, Docs (CLAUDE.md/MEMORY), Release vehicle (branch/PR), `.planning/` in PR, Merge & tag ownership, Version scope, README/version (pre-verified done)

## Assumptions Presented

### CI matrix
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Add `market-data-client` to `matrix.package` in ci.yml; only workflow change needed | Confident | ci.yml:97-102 lists 5 pkgs; no `market-data` in `.github/workflows/` |

### Release pipeline (release.yml)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| release.yml is generic; `market-data-client-v0.1.0` matches regex, zero edits | Confident | release.yml regex `^([a-z][a-z0-9-]*-client)-v<ver>$` + dir/version checks |

### Package artifacts (pre-verified DONE)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| README complete (uso, env vars, auth Auth0) | Confident | README.md 58 lines; MARKET_DATA_* env + client_credentials flow |
| version aligned 0.1.0 | Confident | pyproject `version="0.1.0"`; __init__.py:106 `__version__="0.1.0"` |
| uv.lock regenerated | Likely | lockfile contains market-data-client (3 refs); `M` in git status |

### Docs
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Update CLAUDE.md package listing + arch tables + MEMORY | Confident | CLAUDE.md:72,171 list 5 pkgs, no market-data row |

### Release vehicle (branch/PR)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Ship from existing `release/v0.2.0-bump` branch; one PR → main | Likely | current branch has 218 files/+23k vs main = full v1.4 milestone unmerged |

### `.planning/` in PR
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Keep `.planning/` in the PR (no filtering) | Likely | .planning tracked across prior milestones; CI ignores .md for triggering |

### Merge & tag ownership
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Agent prepares PR + stops; user merges/tags | Unclear | merge/tag/publish are irreversible outward-facing actions |

### Version scope
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Per-package only; no repo-wide v0.2.0 despite branch name | Unclear | monorepo uses per-package versioning; branch named `release/v0.2.0-bump` |

## Corrections Made

Three gray areas were resolved via user questions:

### Merge & tag ownership
- **Original assumption:** Agent prepares PR and stops at PR-ready; user merges + tags.
- **User correction:** **Drive merge + tag too** — agent merges the PR and pushes the tag
  `market-data-client-v0.1.0` on explicit go-ahead, still confirming at the merge point.
- **Reason:** User wants the agent to conduct the full flow, reserving only final go/no-go.

### Release vehicle (branch/PR)
- **Confirmed (not corrected):** Ship from existing `release/v0.2.0-bump` branch; one PR → main;
  `.planning/` included.

### Version scope
- **Confirmed (not corrected):** Per-package only; no workspace/repo-wide v0.2.0. Root pyproject
  change is just the workspace member addition.

## External Research

None — codebase provided sufficient evidence (ci.yml, release.yml, pyproject, README, CLAUDE.md,
git state all read directly).
