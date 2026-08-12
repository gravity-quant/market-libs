---
phase: 28-release-prep-publish-v0-3-0
plan: 03
subsystem: infra
tags: [release, git-tag, github-release, human-checkpoint, memory, publish]

# Dependency graph
requires:
  - phase: 28-02
    provides: "origin/main at the two-parent merge commit 5d0825d whose tree already reads version = \"0.4.0\" — the only valid tag anchor"
provides:
  - "git-tag:market-data-client-v0.4.0 — annotated tag 53dd170 on merge commit 5d0825d, pushed to origin"
  - "gh-release:market-data-client-v0.4.0 — public GitHub Release with market_data_client-0.4.0-py3-none-any.whl + market_data_client-0.4.0.tar.gz"
  - "release memory refreshed across all six regions; install lines now point at v0.4.0"
  - "operator go/no-go decision for D-18(b) recorded verbatim with timestamp"
affects: [PUB-MUT-01 satisfied, future consumers installing market-data-client]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Annotated tag created with an explicit commit-ish (`git tag -a <name> \"$MERGE_SHA\"`) rather than an implicit branch HEAD, so release.yml's version gate runs against the merged tree (RESEARCH P-3)"
    - "Tag pushed by name (`git push origin <tag>`) never `--tags`, so an unrelated stale local `v1.3` tag could not leak to origin"
    - "Pre-tag re-resolution of the anchor from `git rev-parse origin/main` instead of trusting the SHA literal recorded in the prior plan's SUMMARY"

key-files:
  created:
    - .planning/phases/28-release-prep-publish-v0-3-0/28-03-SUMMARY.md
  modified:
    - .claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md

key-decisions:
  - "[Phase 28-03] The tag was pushed ONLY after a SECOND explicit operator \"approved\" at 2026-08-12T00:13:56Z, recorded independently of the D-18(a) merge approval of 2026-08-01T22:13:53Z — the two D-18 gates were never collapsed"
  - "[Phase 28-03] The anchor was re-resolved live (`git rev-parse origin/main` → 5d0825d) and re-asserted structurally (3 fields from `git rev-list --parents`, merged tree version 0.4.0) before the tag was created, rather than trusting 28-02-SUMMARY's literal"
  - "[Phase 28-03] `release.yml` was NOT edited, re-created or re-run (D-06); the diff of `.github/workflows/` between market-data-client-v0.3.1 and market-data-client-v0.4.0 is 0 files"
  - "[Phase 28-03] All SIX regions of the release memory were refreshed, not the two named by CONTEXT D-04 — RESEARCH C-3 and the ce77ed4 precedent (+24/−14 across six regions) govern"
  - "[Phase 28-03] The two stale `**Scope note` paragraphs were collapsed into ONE accurate note; both had asserted that Phase 26 and Phase 27 were outstanding, which v0.4.0 falsifies"
  - "[Phase 28-03] The D-03 residual risk (D-13's CalendarDay non-breaking claim never independently audited) remains ACCEPTED and unchanged; the README changelog callout is the locked mitigation"

patterns-established:
  - "Post-release memory refresh sequenced AFTER the tag push because the memory cites three values that do not exist beforehand: the merge SHA, the PR number and the release.yml run ID (C-3)"
  - "Region-by-region grep assertions on a prose memory file (single Scope note; tag token count == 2 on the git install line; wheel filename on the wheel line) instead of eyeballing the diff"

requirements-completed: [PUB-MUT-01]

# Metrics
duration: 7min
completed: 2026-08-12
status: complete
---

# Phase 28 Plan 03: Tag, publish v0.4.0, refresh release memory Summary

**`market-data-client` v0.4.0 is publicly published — annotated tag `53dd170` placed on the re-resolved two-parent merge commit `5d0825d` and pushed by name after a second, independent operator approval, `release.yml` run `31549711805` green in 13s producing both the wheel and the sdist, and the in-repo release memory refreshed across all six regions so it now directs consumers to v0.4.0 and no longer claims the calendar surface or the live verification are outstanding.**

## Performance

- **Duration:** ~7 min agent-active (approval 00:13:56Z → memory commit ~00:20Z)
- **Started:** 2026-08-12T00:14Z (continuation agent, post-approval)
- **Completed:** 2026-08-12T00:20Z
- **Tasks:** 3 of 3 (Task 1 resolved by the prior executor's checkpoint; Tasks 2-3 executed here)
- **Files modified:** 1 working-tree file (the release memory); Task 2 is git/gh operations by design

## Accomplishments

- Re-resolved the tag anchor live rather than trusting the recorded literal, and re-asserted both invariants (two parents, merged tree at `0.4.0`) before creating anything.
- Created the annotated tag on that exact SHA and pushed it by name — the irreversible act — closing threat T-28-03.
- `release.yml` ran unedited and green, producing a public, non-draft, non-prerelease Release carrying both required assets, satisfying **PUB-MUT-01**.
- Collapsed the two factually-false `**Scope note` paragraphs into one accurate note and refreshed both install lines, closing threat T-28-10 (a stale install line silently propagates a superseded version — RESEARCH P-8).

## Task Commits

Task 2 is a pure git/gh operation whose `<files>` block is explicitly `(git/gh operations — no working-tree files modified)`, so it produced no code commit; its artifacts are the tag on `origin` and the public Release.

1. **Task 1: Second blocking go/no-go gate (D-18b)** — checkpoint, no commit; artifact is the operator reply recorded below
2. **Task 2: Tag the merge commit, push, verify the Release** — no commit by design; artifacts are tag `53dd170` and Release `market-data-client-v0.4.0`
3. **Task 3: Refresh all six memory regions** — `bb2adf4` `docs(memory): update market-data-client latest release to v0.4.0` (1 file, +44/−19)

## Files Created/Modified

- `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md` — modified, +44/−19 across six regions (commit `bb2adf4`)
- `.planning/phases/28-release-prep-publish-v0-3-0/28-03-SUMMARY.md` — created (this file)

## Measured Results

### The D-18(b) human gate — operator reply recorded verbatim

| Field | Value |
|-------|-------|
| **Operator reply (verbatim)** | `approved` |
| **Timestamp (UTC)** | **2026-08-12T00:13:56Z** |
| Gate | `checkpoint:human-verify`, `gate="blocking"`, in an `autonomous: false` plan |
| Independence | **SECOND** approval, recorded separately from the D-18(a) merge approval of **2026-08-01T22:13:53Z**. The two gates were **not** collapsed — approval of the merge was not treated as approval of the tag. |
| Shown to the operator | the freshly re-resolved merge SHA with its two parents, the merged tree's `version = "0.4.0"`, the exact tag string `market-data-client-v0.4.0`, and the statement that the Release is public and effectively permanent |
| Commands run before the reply | none that change remote state — no `git tag`, no `git push`, no `gh release` |

### The tag (D-01, SC#3, T-28-03)

| Field | Value |
|-------|-------|
| Tag name | `market-data-client-v0.4.0` |
| **Tag object SHA** | **`53dd170ea1eafa4b8b11ace5588f97763f7539f5`** |
| `git cat-file -t` | **`tag`** — annotated, not lightweight |
| **Commit it anchors** | **`5d0825d11e88c03e44631648d8da64d1de8fd751`** |
| `git rev-parse origin/main` | `5d0825d11e88c03e44631648d8da64d1de8fd751` — **equal** ✅ (SC#3) |
| Parents of the anchor | `7b0e0b2f831bd9435b5637632baa068833477831` + `0c1a3822a0049640964b8bfc48334bc34bb2c81b` |
| `git rev-list --parents -n1 \| wc -w` | **3** ✅ |
| Merged tree version (same awk as `release.yml:47`) | **`0.4.0`** ✅ |
| Creation form | `git tag -a market-data-client-v0.4.0 5d0825d… -m "…"` — explicit commit-ish, never a bare `git tag <name>` |
| Push form | `git push origin market-data-client-v0.4.0` — by name; **no** `--tags`, **no** force |
| Remote ref | `53dd170ea1eafa4b8b11ace5588f97763f7539f5  refs/tags/market-data-client-v0.4.0` |

Re-resolution was not a formality: the plan mandates recomputing the anchor rather than trusting `28-02-SUMMARY`'s literal. Both agreed, and the agreement is the cross-check.

### The pipeline run (D-06)

| Field | Value |
|-------|-------|
| **Run ID** | **`31549711805`** |
| **Conclusion** | **`success`** (status `completed`, 13s) |
| Workflow | `Release` (`release.yml`), triggered by `push` of the tag |
| URL | https://github.com/gravity-quant/market-libs/actions/runs/31549711805 |
| Steps green | Parsear tag → Verificar versión del pyproject == versión del tag → Instalar uv → Build wheel y sdist → Crear GitHub Release y subir artefactos |
| `.github/workflows/` diff `v0.3.1..v0.4.0` | **0 files** ✅ — the workflow was never edited, re-created or re-run (D-06) |

Three non-fatal annotations were emitted and are **not** failures: the Node.js 20 deprecation notice for `actions/checkout@v4` / `astral-sh/setup-uv@v3`, and two GitHub Actions **cache service** errors (`Failed to save`, `Failed to restore: Cache service responded with 400`). The cache is a build accelerator only; every functional step passed and the job concluded `success`. No workflow patch was applied — per D-06 a failure would have been surfaced, not fixed.

### The published Release (SC#3)

| Field | Value |
|-------|-------|
| Tag | `market-data-client-v0.4.0` |
| URL | https://github.com/gravity-quant/market-libs/releases/tag/market-data-client-v0.4.0 |
| Published | 2026-08-12T00:18:19Z |
| Draft / prerelease | `false` / `false` — genuinely public |
| **Asset 1** | **`market_data_client-0.4.0-py3-none-any.whl`** |
| **Asset 2** | **`market_data_client-0.4.0.tar.gz`** |

Both assets carry the `market_data_client-0.4.0` prefix; one ends `.whl`, one ends `.tar.gz`.

### Task 2 automated verify block — PASS

The plan's single-line compound form was refused by the worktree sandbox as too complex to prove it stays inside the worktree, so each leg was run as a separate plain command. Every leg is an independent read-back:

| Leg | Result |
|-----|--------|
| local tag exists | `market-data-client-v0.4.0` ✅ |
| remote tag ref exists | `53dd170… refs/tags/market-data-client-v0.4.0` ✅ |
| `rev-list -n1 <tag>` == `rev-parse origin/main` | `5d0825d…` == `5d0825d…` ✅ |
| anchor parent-field count == 3 | `3` ✅ |
| release assets contain `.whl` / `.tar.gz` / `market_data_client-0.4.0` | all three ✅ |
| `.github/workflows/` diff == 0 | `0` ✅ |

**Verdict: PASS.**

### Task 3 — the six memory regions

Diffstat `44 insertions(+), 19 deletions(-)`, comparable to the `ce77ed4` precedent (+24/−14).

| Region | Change |
|--------|--------|
| 1 — frontmatter `description:` (L3) | rewritten: v0.4.0 named latest, bump class `minor`, headline calendar-write + live-verified fixes, superseded list now `v0.2.0/v0.3.0/v0.3.1`; the "not on PyPI" closing sentence kept |
| 2 — `**Latest published:**` | now `market-data-client-v0.4.0`, 2026-08-12, merge commit `5d0825d`, **PR #10**, `release.yml` run **`31549711805`** |
| 3 — version-specific section | new `**v0.4.0 adds (v1.5 Phases 26-27 — MUT-MD-02 + LIVE-MUT-01):**` lead covering the eight new calendar names + async counterparts + `confirm` default `False`, the LIVE-MUT-01 fixes, and the `CalendarDay` replacement; v0.3.1 and v0.3.0 both retitled "carried forward into v0.4.0" |
| 4 — `**Scope note` | **two → one.** The pair asserting "symbols-write only" and that Phases 26/27 are outstanding was replaced by a single note recording symbols **+ calendar**, both exercised live against develop under LIVE-MUT-01 with dedicated test identifiers and create → verify → revert cleanup |
| 5 — `**Prior releases:**` | `v0.3.1` demoted into the head with its date, merge SHA `7b0e0b2` and PR #9; `v0.3.0` and `v0.2.0` retained; trailing sentence re-versioned to "v0.4.0 keeps all of this"; the v0.1.0 superseded/buggy statement kept |
| 6 — both install lines | git line carries `market-data-client-v0.4.0` **exactly twice**; wheel line carries the tag **and** `market_data_client-0.4.0-py3-none-any.whl` |

**Left byte-identical (no diff hunk touches them):** the intro paragraph, the `**Runtime config (env / .env)**` block, and the `Related: [[phase-23-wave2-pending-creds]]` line — matching `ce77ed4`. No credential value appears anywhere in the file; the runtime block names environment VARIABLES only.

### Task 3 automated verify block — PASS

| Assertion | Required | Actual |
|-----------|----------|--------|
| line 3 names v0.4.0 | ≥1 | 1 ✅ |
| ``Latest published: `market-data-client-v0.4.0` `` | ≥1 | 1 ✅ |
| `v0.4.0 adds` | ≥1 | 1 ✅ |
| `carried forward into v0.4.0` | ≥1 | 2 ✅ |
| `^\*\*Scope note` count | **exactly 1** | **1** ✅ |
| `NOT yet done` absent | 0 | **0** ✅ |
| `Prior releases` | ≥1 | 1 ✅ |
| tag tokens on `- git, pinned to tag` line | **exactly 2** | **2** ✅ |
| wheel filename on `- release wheel:` line | ≥1 | 1 ✅ |
| tag on `- release wheel:` line | ≥1 | 1 ✅ |
| `MARKET_DATA_AUTH0_TOKEN_URL` still present | ≥1 | 1 ✅ |
| memory file present in `HEAD` | ≥1 | 2 ✅ |

**Verdict: PASS.** Commit subject reads exactly `docs(memory): update market-data-client latest release to v0.4.0` and `git show --stat HEAD` lists only the memory file. Post-commit deletion check: no files deleted.

## Decisions Made

- **Two independent gates, honoured.** The tag push waited on its own "approved" (00:13:56Z), distinct from the merge approval (2026-08-01T22:13:53Z). D-18 mandates this and the Phase 24 single-gate precedent was deliberately not followed.
- **Anchor re-resolved, not trusted.** `git rev-parse origin/main` plus a structural two-parent assertion and a merged-tree version read ran *before* the tag existed. Had either failed the plan stops with nothing published.
- **Annotated tag with an explicit commit-ish.** A bare `git tag <name>` would have tagged the worktree's branch HEAD, producing a Release pointing at a commit outside `main`'s history (RESEARCH P-3).
- **Push by name only.** A stale local `v1.3` tag unrelated to this phase exists; `git push --tags` would have leaked it to `origin`.
- **All six memory regions, not the two named by D-04.** RESEARCH C-3 flags D-04 as under-specified; regions 4 and 6 are the ones with real downstream consequences and the ones most likely to be skipped.

## Deviations from Plan

None affecting the outcome — no deviation rule (1-4) was invoked and no auto-fix was needed.

One **procedural** note that is not a content deviation: the worktree sandbox refused both plans' single-line compound `<automated>` verify commands ("too complex to verify that it stays inside the worktree"). Each was decomposed into individual plain commands and every leg was executed and recorded. The assertions are unchanged — only their invocation form differs, and running them separately makes each result independently visible rather than collapsing to a single `PASS` token.

## Issues Encountered

The `release.yml` run emitted two GitHub Actions **cache service** errors (`Failed to save`, `Failed to restore: Cache service responded with 400`) alongside a Node.js 20 deprecation warning. All are annotations on an otherwise green job — the cache only accelerates `astral-sh/setup-uv`, every functional step passed, and the run concluded `success` with both artifacts uploaded. Per D-06 no workflow change was made in response.

## Branch Placement of the Memory Commit

Commit `bb2adf4` is authored on the parallel-execution worktree branch `worktree-agent-a6a21aeaeefc0d552`, **not** directly on `milestone/v1.5-mutations`. The plan's instruction to "commit the file to `milestone/v1.5-mutations`" is satisfied transitively: the orchestrator merges this agent branch back into `milestone/v1.5-mutations` after the wave completes.

From there the commit reaches `main` in a **future** PR — exactly the `ce77ed4` precedent, where the v0.3.1 memory refresh landed after its release on `milestone/v1.5-mutations` and shipped in the next PR. **The release is NOT blocked on this commit**; v0.4.0 is already public and installable. Recording it here so the pending main-ward hop is not lost. `milestone/v1.5-mutations` survived the PR #10 merge because `delete_branch_on_merge` is `false` (D-11).

## Residual Risk Carried Forward (D-03 / D-13) — ACCEPTED, unchanged

**v0.4.0 ships a source-breaking `CalendarDay` field replacement inside a minor bump on the strength of a D-13 claim that no independent audit ever confirmed.** `27-VERIFICATION.md` re-verified only D-22 (the symbols side, which *is* verifiably non-breaking); D-13 — the assertion that no published consumer could ever have held a populated `CalendarDay`, because `parse_calendar_response` iterated the envelope's keys instead of `days[]` — remains the one non-breaking claim never independently audited.

The **locked mitigation** is the explicit `packages/market-data-client/README.md` changelog callout naming all three removed fields (`date`, `marketId`, `isBusinessDay`) and all five replacements (`day`, `closed`, `description`, `open_time`, `close_time`); it is live on `main` and is now mirrored in the release memory's region 3. Rejected alternatives — a deprecated-alias compat shim (the `Symbol.marketId` pattern) and escalating to `1.0.0` — are not to be re-opened. The operator accepted this risk at both D-18 gates. **Status: accepted**, now carried past publication: if a real consumer surfaces an `AttributeError` on `CalendarDay.date`, the compat shim is the standing remedy.

## User Setup Required

None. No human involvement remains in this phase — both D-18 gates are closed and the Release is live.

## Next Phase Readiness

- **PUB-MUT-01 is satisfied** — v0.4.0 is installable from both the git tag and the Release wheel.
- The orchestrator still owns: merging this agent branch back into `milestone/v1.5-mutations`, and the `STATE.md` / `ROADMAP.md` updates (deliberately untouched here).
- The memory commit needs a future PR to reach `main` — not a blocker, just an outstanding hop.
- `CLAUDE.md:74` still reads `market-data-client v0.2.0`, now **three** releases stale. This is known, deliberate debt per D-07 (a `/gsd-map-codebase` artifact, not a hand-maintained release file; no prior release touched it) — not a defect introduced here.

**Blockers:** none.

## Self-Check: PASSED

- Tag `market-data-client-v0.4.0` — FOUND, type `tag` (annotated), object `53dd170ea1eafa4b8b11ace5588f97763f7539f5`
- Tag on `origin` — FOUND, `refs/tags/market-data-client-v0.4.0`
- Anchor `5d0825d11e88c03e44631648d8da64d1de8fd751` — FOUND, equals `git rev-parse origin/main`, 3 parent fields
- `release.yml` run `31549711805` — FOUND, conclusion `success`
- Release `market-data-client-v0.4.0` — FOUND, public, assets `market_data_client-0.4.0-py3-none-any.whl` + `market_data_client-0.4.0.tar.gz`
- `.github/workflows/` diff `v0.3.1..v0.4.0` — **0 files** ✅ (D-06)
- Commit `bb2adf4` — FOUND, subject `docs(memory): update market-data-client latest release to v0.4.0`, 1 file
- `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md` — FOUND, all six regions updated, exactly 1 `**Scope note`
- `.planning/phases/28-release-prep-publish-v0-3-0/28-03-SUMMARY.md` — FOUND
- `STATE.md` / `ROADMAP.md` — NOT modified ✅ (orchestrator-owned)

---
*Phase: 28-release-prep-publish-v0-3-0*
*Completed: 2026-08-12*
