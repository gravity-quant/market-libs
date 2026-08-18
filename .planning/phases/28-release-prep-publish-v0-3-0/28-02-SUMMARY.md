---
phase: 28-release-prep-publish-v0-3-0
plan: 02
subsystem: infra
tags: [release, pull-request, ci-gate, merge-commit, human-checkpoint, github]

# Dependency graph
requires:
  - phase: 28-01
    provides: "origin/milestone/v1.5-mutations published at HEAD (fast-forward) — the precondition `gh pr create` needs; plus the v0.4.0 bump across the three version sites"
provides:
  - "PR #10 (milestone/v1.5-mutations -> main), merged — the single release PR carrying Phases 25-27 plus the v0.4.0 prep commits"
  - "origin/main advanced to merge commit 5d0825d with TWO parents (7b0e0b2, 0c1a382) — the tag anchor plan 28-03 will use"
  - "merged tree carries version = \"0.4.0\" in packages/market-data-client/pyproject.toml, satisfying release.yml:42-51 in advance"
  - "operator go/no-go decision for D-18(a) recorded verbatim with timestamp"
affects: [28-03 tag + GitHub Release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Count-based CI gate assertion (15 total rows / 15 status==pass / 2 market-data-client rows) replacing the inadequate `! grep -qiE '\\bfail'` form — pending, skipping and cancelled all read as green under the negative-pattern check"
    - "Blocking human checkpoint as the sole access control on an irreversible operation when the platform enforces nothing (main has protected:false, rulesets [])"
    - "Real merge commit (`gh pr merge --merge`) asserted structurally by parent count, not by trusting the flag"

key-files:
  created:
    - .planning/phases/28-release-prep-publish-v0-3-0/28-02-SUMMARY.md
  modified: []

key-decisions:
  - "[Phase 28-02] Exactly one PR opened (#10) per D-08; `/gsd-pr-branch` was NOT run and `.planning/` was NOT filtered out (D-09) — 67 of the 100 changed files are `.planning/` artifacts carrying the Phases 25-27 live-verification evidence"
  - "[Phase 28-02] The 15-green gate was asserted BY COUNT (15 rows / 15 `pass` / 0 non-pass / 2 market-data-client rows), never by absence of the word `fail` — `cancel-in-progress: true` at ci.yml:20 makes `cancelled` genuinely reachable and a Markdown-only diff would produce zero checks, so `total == 15` is load-bearing"
  - "[Phase 28-02] The merge ran ONLY after the operator's explicit verbatim \"approved\" at 2026-08-01T22:13:53Z; `main` has no branch protection (protected:false, rulesets []), so that reply was the only gate standing between an unverified build and a public default branch"
  - "[Phase 28-02] Merged with `gh pr merge 10 --merge` — never `--squash` (would collapse ~106 commits and orphan every SHA the Phase 25-27 SUMMARYs cross-reference) and never `--rebase` (would rewrite history reachable from the v0.3.0/v0.3.1 tags); the resulting two-parent shape was verified structurally"
  - "[Phase 28-02] No tag and no GitHub Release were created in this plan — D-18 requires two independent gates and the tag is gated behind a SECOND checkpoint in plan 28-03; the gates were deliberately not collapsed"

patterns-established:
  - "Merge-shape verification by `git rev-list --parents -n1 origin/main | wc -w` == 3 rather than trusting that `--merge` was honoured; a single-parent result halts the phase because plan 28-03 tags exactly this commit"
  - "Merged-tree version pre-check with the SAME awk expression release.yml:47 uses (`awk -F'\"' '/^version[[:space:]]*=/{print $2; exit}'`), run against `git show origin/main:...` — proves the tag will satisfy the pipeline's version-match gate before the tag exists"

requirements-completed: []  # PUB-MUT-01 remains Pending — satisfied by the 28-03 publication

# Metrics
duration: 69min
completed: 2026-08-01
status: complete
---

# Phase 28 Plan 02: Release PR + merge to public `main` Summary

**PR #10 opened as the single release PR carrying the whole Phase 25-27 diff including the `.planning/` artifacts, its CI gate proven green by explicit counting (15 rows / 15 `pass` / 0 non-pass / 2 market-data-client rows) rather than by pattern-matching for failure, and merged into unprotected public `main` only after the operator's verbatim "approved" — producing the two-parent merge commit `5d0825d` whose tree already reads `version = "0.4.0"`, with no tag and no Release created.**

## Performance

- **Duration:** ~69 min wall-clock (PR created 21:05:27Z → merged 22:14:22Z); the bulk is the human checkpoint wait, agent-active time is ~6 min
- **Started:** 2026-08-01T21:05Z
- **Completed:** 2026-08-01T22:15Z
- **Tasks:** 3 of 3
- **Files modified:** 0 working-tree files (all three tasks are git/gh operations by design)

## Accomplishments

- Opened **exactly one** PR — #10, `milestone/v1.5-mutations` → `main` — with the D-12 title convention, carrying 100 changed files (+27,025 / −323) of which 67 are `.planning/` artifacts deliberately kept per D-09.
- Proved the CI gate genuinely green by **counting**, closing threat T-28-05: 15 total rows, 15 with status `pass`, **0** rows in any other status, 2 of them the market-data-client matrix jobs. No commit was pushed while checks were in flight, so no `cancel-in-progress` cancellation could masquerade as green.
- Presented the D-18(a) blocking checkpoint and executed the irreversible merge **only** on the operator's explicit approval, closing threat T-28-06 — the sole access control on this operation, since GitHub enforces none.
- Merged with a real merge commit (`--merge`) and verified the two-parent shape structurally, closing T-28-09; then confirmed the merged tree already carries `version = "0.4.0"` so plan 28-03's tag will satisfy `release.yml:42-51`.

## Task Commits

Each task was executed atomically; Tasks 1 and 3 are pure git/gh operations whose `<files>` block is explicitly `(git/gh operations — no working-tree files modified)`, so neither produced a code commit. Their observable artifacts are on GitHub and on `origin/main`.

1. **Task 1: Open the release PR and assert 15/15 checks pass BY COUNT** — no commit by design; artifact is PR #10 and CI run `30718388691`
2. **Task 2: Blocking go/no-go gate (D-18a)** — checkpoint, no commit; artifact is the recorded operator reply below
3. **Task 3: Merge with a real merge commit** — no commit authored by this agent; the artifact is GitHub's merge commit `5d0825d11e88c03e44631648d8da64d1de8fd751` on `origin/main`

**Plan metadata:** see the final `docs(28-02)` commit below.

## Files Created/Modified

No working-tree file was created or modified by this plan. The only file it writes is this SUMMARY plus the STATE/ROADMAP metadata updates in the closing commit.

## Measured Results

### The release PR

| Field | Value |
|-------|-------|
| Number | **#10** |
| URL | https://github.com/gravity-quant/market-libs/pull/10 |
| Title | `release: market-data-client v0.4.0 (calendar write + live-verified mutation fixes)` |
| Base ← head | `main` ← `milestone/v1.5-mutations` |
| Created | 2026-08-01T21:05:27Z |
| Merged | 2026-08-01T22:14:22Z |
| Diff | `100 files changed, 27025 insertions(+), 323 deletions(-)` |
| Commits ahead of `origin/main` | 106 |
| Open PRs to `main` at creation time | 1 (D-08 satisfied — no second PR opened) |

### The CI gate — asserted by count (T-28-05, SC#2)

CI run id: **`30718388691`** (https://github.com/gravity-quant/market-libs/actions/runs/30718388691)

Literal `gh pr checks 10` output, all 15 rows:

```
Lint y formato (ruff)                        pass   11s
Tests · ambito-financiero-client · py3.12    pass   28s
Tests · ambito-financiero-client · py3.13    pass   24s
Tests · higyrus-client · py3.12              pass   53s
Tests · higyrus-client · py3.13              pass   1m7s
Tests · iol-client · py3.12                  pass   25s
Tests · iol-client · py3.13                  pass   27s
Tests · market-data-client · py3.12          pass   14s
Tests · market-data-client · py3.13          pass   16s
Tests · matriz-client · py3.12               pass   42s
Tests · matriz-client · py3.13               pass   42s
Tests · wallets-client · py3.12              pass   13s
Tests · wallets-client · py3.13              pass   12s
Type check (mypy)                            pass   16s
pre-commit hooks                             pass   18s
```

The counted totals — the assertion that actually gated the merge:

| Metric | Command | Value | Required |
|--------|---------|-------|----------|
| Total rows | `gh pr checks 10 \| wc -l` | **15** | 15 |
| Rows with status `pass` | `gh pr checks 10 \| awk -F'\t' '$2=="pass"' \| wc -l` | **15** | 15 |
| market-data-client rows | `grep -c 'Tests · market-data-client · py3\.1[23]'` | **2** | 2 |
| Rows in any other status (`fail` / `pending` / `skipping` / `cancelled`) | `awk -F'\t' '$2!="pass"' \| wc -l` | **0** | 0 |

The check names match the 15 read verbatim off the completed run of PR #9 — 3 singleton jobs plus 6 packages × 2 Python versions. The `total == 15` leg is not redundant with `passed == 15`: a Markdown-only diff would trigger **zero** checks under `paths-ignore: ["**.md", ".gitignore"]`, and "no checks" is emphatically not green.

### Scope guarantees on the PR diff (D-06 / D-09)

| Check | Command | Result |
|-------|---------|--------|
| `.planning/` artifacts retained | `gh pr view 10 --json files --jq '[.files[].path \| select(startswith(".planning/"))] \| length'` | **67** — not filtered; `/gsd-pr-branch` was never run |
| `.github/workflows/` untouched | same, `startswith(".github/workflows/")` | **0** |
| Branch tip unchanged during the run | `git rev-parse HEAD` vs `git rev-parse origin/milestone/v1.5-mutations` | both `0c1a382` — no mid-run push, so no cancelled run |
| No tag created during Task 1 | `git tag -l 'market-data-client-v0.4.0'` | empty |

### `main` has no branch protection (C-2) — re-verified live this session

```
$ gh api repos/gravity-quant/market-libs/branches/main --jq '{name,protected}'
{"name":"main","protected":false}
$ gh api repos/gravity-quant/market-libs/rulesets
[]
```

GitHub would have merged this PR with red, pending or cancelled checks. The count assertion above and the operator's approval below were the only enforcement in existence.

### The D-18(a) human gate — operator reply recorded verbatim

| Field | Value |
|-------|-------|
| **Operator reply (verbatim)** | `approved` |
| **Timestamp (UTC)** | **2026-08-01T22:13:53Z** |
| Mechanism | Blocking `checkpoint:human-verify` (`gate="blocking"`) in an `autonomous: false` plan, presented via the orchestrator |
| Shown to the operator | PR URL and number; the literal `gh pr checks` output; the three counted totals (15 rows / 15 `pass` / 0 non-pass / 2 market-data-client rows); the diff stat; the accepted D-03/D-13 residual risk; and the explicit statement that `main` has NO branch protection so the approval is the only gate |
| Independently re-verified by the orchestrator before presenting | exactly one open PR (#10, head `milestone/v1.5-mutations`); 15/15/0/2; `protected:false`; `rulesets []`; `git tag -l` empty; `git status --porcelain` clean |
| Commands executed before the reply | none that change remote state — no `gh pr merge`, no `git tag`, no `git push` |

Merge executed **29 seconds** after the approval timestamp (approved 22:13:53Z → merged 22:14:22Z).

### The merge commit (D-11, T-28-09)

```
$ git rev-list --parents -n1 origin/main
5d0825d11e88c03e44631648d8da64d1de8fd751 7b0e0b2f831bd9435b5637632baa068833477831 0c1a3822a0049640964b8bfc48334bc34bb2c81b

$ git log -1 --format='%H | parents: %p | %s' origin/main
5d0825d11e88c03e44631648d8da64d1de8fd751 | parents: 7b0e0b2 0c1a382 | Merge pull request #10 from gravity-quant/milestone/v1.5-mutations
```

| Field | Value |
|-------|-------|
| **`MERGE_SHA`** | **`5d0825d11e88c03e44631648d8da64d1de8fd751`** |
| **Parent 1** (prior `origin/main`) | `7b0e0b2f831bd9435b5637632baa068833477831` |
| **Parent 2** (branch tip merged) | `0c1a3822a0049640964b8bfc48334bc34bb2c81b` |
| Field count from `git rev-list --parents -n1` | **3** — commit + exactly two parents |
| Subject | begins `Merge pull request` ✅ |
| **Merge method** | **`gh pr merge 10 --merge`** — no `--squash`, no `--rebase` anywhere in the command history |
| PR state after merge | `MERGED` (not `OPEN`, not `CLOSED`) |
| `mergeCommit.oid` reported by GitHub | `5d0825d11e88c03e44631648d8da64d1de8fd751` — matches `git rev-parse origin/main` |

Plan 28-03 should recompute `MERGE_SHA` from `git rev-parse origin/main` rather than trusting this literal; the value above is the cross-check.

### The merged tree already satisfies `release.yml` (T-28-03a)

```
$ git show origin/main:packages/market-data-client/pyproject.toml \
    | awk -F'"' '/^version[[:space:]]*=/{print $2; exit}'
0.4.0
```

Read with the **same** awk expression `release.yml:47` uses. The tag plan 28-03 places on `5d0825d` will therefore pass the pipeline's version-match gate.

### Nothing irreversible beyond the merge (D-18 two-gate separation)

| Check | Command | Result |
|-------|---------|--------|
| No local tag | `git tag -l 'market-data-client-v0.4.0'` | empty |
| No remote tag | `git ls-remote --tags origin 'market-data-client-v0.4.0'` | empty |
| No GitHub Release | `gh release view market-data-client-v0.4.0` | `release not found` |
| Release branch survived the merge | `git ls-remote --heads origin milestone/v1.5-mutations` | `0c1a382 refs/heads/milestone/v1.5-mutations` — available for the 28-03 memory commit |

`delete_branch_on_merge` is `false` on this repo and no branch-delete flag was passed, exactly as D-11 requires.

## Decisions Made

- **Exactly one PR** (D-08). `gh pr list --state open --base main` returned `[]` before creation and exactly one entry after — no second PR was opened at any point, including after the checkpoint.
- **`.planning/` kept in the diff** (D-09). 67 of 100 changed files are planning artifacts; filtering them would have stripped ~60 KB of Phases 25-27 live-verification evidence from `main` and broken the SHA cross-references the phase SUMMARYs rely on. `/gsd-pr-branch` was never invoked.
- **The gate asserted by count, not by absence of "fail"** (S-2, T-28-05). Phase 24's `! … | grep -qiE '\bfail'` form passes on `pending`, `cancelled` and on empty output. The replacement counts three quantities and additionally records that zero rows sit in any non-`pass` status.
- **Merged only on explicit "approved"** (D-18a, T-28-06). With `protected:false` and `rulesets []`, nothing on GitHub would have stopped a merge of a red PR. The checkpoint was the only access control, and no remote-state-changing command ran before the reply.
- **`--merge`, verified structurally** (D-11, T-28-09). The flag was mandated, but the plan does not trust it — the two-parent shape is asserted from `git rev-list --parents`, because a single-parent result would mean the merge was squashed or rebased and plan 28-03 tags exactly this commit.
- **The two D-18 gates were not collapsed.** No tag, no push, no Release in this plan; gate (b) in plan 28-03 remains a fully independent decision for the operator.

## Deviations from Plan

None — plan executed exactly as written. No deviation rule was invoked; no auto-fix was needed; no architectural question arose.

One procedural note that is **not** a deviation: `gh pr merge 10 --merge` completed silently (no `✓ Merged pull request` line on stdout). The merge was confirmed out-of-band instead — `gh pr view 10 --json state,mergeCommit` returned `MERGED` with `mergeCommit.oid` equal to `git rev-parse origin/main`, and the structural two-parent assertion passed. Silent success is not treated as evidence anywhere in this plan; every claim above rests on an independent read-back.

## Issues Encountered

None. All 15 checks passed on the first run, matching the D-15 local baseline exactly, and the merge produced the expected commit shape on the first attempt.

## Residual Risk Carried Forward (D-03 / D-13)

Unchanged from plan 28-01 and explicitly re-presented to the operator at the checkpoint before approval:

**The v0.4.0 release ships a source-breaking `CalendarDay` field replacement inside a minor bump on the strength of a D-13 claim that no independent audit ever confirmed** (`27-VERIFICATION.md` re-verified only D-22). The locked mitigation — an explicit changelog callout naming all three removed fields and all five replacements — is live in `packages/market-data-client/README.md` and is now merged to `main`. The operator accepted this risk in the same reply that approved the merge. Rejected alternatives (a deprecated-alias compat shim; escalating to `1.0.0`) are not to be re-opened. **Status: accepted**, carried into plan 28-03.

## User Setup Required

None. The remaining human involvement is the second blocking D-18(b) checkpoint in plan 28-03, before the tag push that triggers `release.yml` and creates the public GitHub Release.

## Next Phase Readiness

Ready for plan **28-03** (tag + GitHub Release):

- `origin/main` is at `5d0825d`, a real two-parent merge commit — the correct and only tag anchor.
- The merged tree already reads `version = "0.4.0"` under the exact awk expression `release.yml:47` uses, so gate 3 of the release pipeline is pre-satisfied.
- The tag name `market-data-client-v0.4.0` matches the `release.yml:28` regex (group 1 `market-data-client`, group 2 `0.4.0`) with no workflow edit needed (D-06).
- `milestone/v1.5-mutations` still exists on `origin` at `0c1a382`, available for the release-memory commit that plan 28-03 owns (the memory file cites a `release.yml` run id that does not exist yet — C-3).
- Plan 28-03 must recompute `MERGE_SHA` from `git rev-parse origin/main` rather than hardcoding `5d0825d`.
- The D-18(b) gate is independent: approval of the merge is **not** approval of the tag.

**Blockers:** none.

## Self-Check: PASSED

- PR #10 — FOUND, state `MERGED`, `mergeCommit.oid` = `5d0825d11e88c03e44631648d8da64d1de8fd751`
- Commit `5d0825d11e88c03e44631648d8da64d1de8fd751` — FOUND at `origin/main`, subject `Merge pull request #10 …`
- Parent `7b0e0b2f831bd9435b5637632baa068833477831` — FOUND (prior `origin/main`)
- Parent `0c1a3822a0049640964b8bfc48334bc34bb2c81b` — FOUND (branch tip, still `refs/heads/milestone/v1.5-mutations` on origin)
- `git rev-list --parents -n1 origin/main | wc -w` — **3** ✅
- `git show origin/main:packages/market-data-client/pyproject.toml` version — **`0.4.0`** ✅
- CI run `30718388691` — FOUND, 15 rows / 15 `pass` / 0 non-pass / 2 market-data-client
- `git tag -l 'market-data-client-v0.4.0'` — empty ✅ (no tag created in this plan)
- `git ls-remote --tags origin 'market-data-client-v0.4.0'` — empty ✅
- `gh release view market-data-client-v0.4.0` — `release not found` ✅
- `.planning/phases/28-release-prep-publish-v0-3-0/28-02-SUMMARY.md` — FOUND

---
*Phase: 28-release-prep-publish-v0-3-0*
*Completed: 2026-08-01*
