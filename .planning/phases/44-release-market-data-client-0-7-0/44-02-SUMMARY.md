---
phase: 44-release-market-data-client-0-7-0
plan: 02
subsystem: infra
tags: [github, ci, release, gh-cli, market-data-client]

requires:
  - phase: 44-01
    provides: version bump to 0.7.0 at four sites, v0.7.0 changelog with two migration tables, single uv.lock refresh, pushed milestone/v1.8-cierre-deuda-post-v1.7 branch
provides:
  - "Merged PR #16 (release: market-data-client v0.7.0) into origin/main with a real two-parent merge commit"
  - "origin/main tree carrying market-data-client 0.7.0, ready to anchor the tag in plan 44-03"
affects: [44-03-release-market-data-client-0-7-0-tag]

tech-stack:
  added: []
  patterns: ["count-based CI gate assertion (never absence-of-failure)", "human-action/blocking-human checkpoint typed to survive both executor and orchestrator auto-approve layers"]

key-files:
  created: []
  modified: [".planning/STATE.md (synced to origin before merge)"]

key-decisions:
  - "Pushed the pending docs-only STATE.md commit (828210b) to origin before validating Task 1 preconditions, since HEAD must equal origin/<branch>. This retriggered a fresh CI run (GitHub did not apply paths-ignore to this PR-synchronize push as expected); re-watched all 15 checks to completion and re-verified the 15/15/2 count live rather than trusting the pre-push snapshot."
  - "Operator was presented the full checkpoint (PR state, live-verified check counts, diff stat, version transition, D-05/D-06/ROADMAP-5 scope facts, no-branch-protection warning) via an explicit blocking question, not auto-advanced. Operator replied \"Approved\" — recorded verbatim below."

patterns-established:
  - "Pattern: when a plan's precondition requires HEAD==origin/<branch> and a docs-only commit is pending locally, push it and re-verify the CI gate live before presenting a merge checkpoint — never present a snapshot captured before an intervening push."

requirements-completed: [PUB-01]

duration: ~20min
completed: 2026-09-01
status: complete
---

# Phase 44 Plan 02: Release PR opened, gate proven green, merged to main Summary

**PR #16 (market-data-client 0.6.0 → 0.7.0) merged into `origin/main` via a real two-parent merge commit after explicit operator approval at the D-08(a) checkpoint; no tag created.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-01 (resumed from a prior operator-abort at this same checkpoint)
- **Completed:** 2026-09-01T13:23:XXZ (merge completed shortly after 13:22:49Z approval)
- **Tasks:** 3 (Task 1 create+prove PR, Task 2 human checkpoint, Task 3 merge)
- **Files modified:** 0 working-tree files (git/gh operations only)

## Accomplishments
- Re-derived (not trusted) that PR #16 already existed, open, against `main`, from `milestone/v1.8-cierre-deuda-post-v1.7` — created in an earlier session per D-07, confirmed as the only open PR against `main`
- Proved the CI gate green **by count** on a live re-run: 15 total check rows, 15 `pass`, exactly 2 `Tests · market-data-client · py3.1x` rows
- Ran the in-file gate-authorship audit required by ROADMAP criterion 4: `0` bare-`blocking` gate attributes, exactly `2` line-anchored `<task type="checkpoint:human-action" gate="blocking-human">` tags across this phase's plan files
- Presented the full D-08(a) checkpoint to the operator and received an explicit literal **"Approved"** reply — not auto-issued, not inferred from silence
- Merged PR #16 with `gh pr merge 16 --merge` — a real merge commit with two parents
- Verified post-merge: merged tree reads `0.7.0` for `market-data-client`; the other five packages' versions are byte-identical to their pre-merge values; branch survived (not deleted); no tag exists locally or on origin

## Task Commits

Git/gh operations only — no working-tree file commits in this plan except the pre-existing docs commit synced to origin as a precondition-repair step (see Deviations).

1. **Task 1: Create PR (already existed from prior session), prove 15/15/2 gate, audit gate authorship** — no new commit; verification only
2. **Task 2: Human checkpoint** — no commit; operator reply recorded below
3. **Task 3: Merge** — produced merge commit `bca1add0de9336ef5ef738cb11a2bcb7623f9968` on `origin/main`

## Files Created/Modified
None in the working tree from this plan's own tasks. `.planning/STATE.md`'s pending commit (`828210b`, authored in the prior aborted session) was pushed to origin as a precondition-repair step — see Deviations.

## Decisions Made
- Pushed the pending `828210b` docs commit to `origin/<branch>` before evaluating Task 1's preconditions, since one precondition is `HEAD == origin/<branch>` and it was false at resume time (local was 1 commit ahead). This is a `.planning/`-only, `.md`-only change.
- This push unexpectedly retriggered a full CI run rather than being skipped by `paths-ignore: ["**.md"]` — re-watched to completion (all 15 pass) and re-derived the count live before presenting the checkpoint, so no stale data was shown to the operator.

## Deviations from Plan

### Auto-fixed Issues

**1. [Precondition repair] Synced HEAD to origin before Task 1 validation**
- **Found during:** Resuming Task 1 preconditions after a prior operator-abort at this same checkpoint
- **Issue:** Local `HEAD` (`828210b`, a docs-only STATE.md commit recording the prior abort) was one commit ahead of `origin/milestone/v1.8-cierre-deuda-post-v1.7` (`855cd0c`). Task 1 precondition (a) requires these to be equal.
- **Fix:** `git push origin milestone/v1.8-cierre-deuda-post-v1.7` (fast-forward, no force). Then re-verified `HEAD == origin/<branch>`.
- **Files modified:** none (push only, no new commit created)
- **Verification:** `git rev-parse HEAD` == `git rev-parse origin/<branch>` after push
- **Committed in:** n/a — commit already existed locally; only pushed

**2. [Gate re-verification] Re-watched CI to completion after the sync push**
- **Found during:** Post-push re-verification of the 15/15/2 count
- **Issue:** The sync push unexpectedly triggered a fresh CI run (new run id `33512391562`) rather than being skipped by `ci.yml`'s `paths-ignore: ["**.md"]` for the pull_request-synchronize event; the pre-push 15/15/2 snapshot was from a now-superseded run and could not be presented as current.
- **Fix:** `gh pr checks 16 --watch` to completion on the new run; re-derived 15/15/2 live before constructing the operator checkpoint.
- **Files modified:** none
- **Verification:** `gh pr checks 16` shows all 15 rows `pass`, 2 matching `Tests · market-data-client · py3.1[23]`, immediately before presenting the checkpoint
- **Committed in:** n/a

**3. [Documented, not fixed] Merge diff includes a one-line `.github/workflows/ci.yml` change**
- **Found during:** Task 3 post-merge verification — `git diff --name-only <premerge>..<merge_sha> -- .github/workflows | wc -l` returned `1`, not the expected `0`
- **Issue:** Plan's acceptance criteria for Task 3 asserts zero workflow diff in the merge, assuming a workflow-untouched phase 44 scope.
- **Investigation:** The change (`ci.yml` driver-locks step allowlist, 12 → 13 paths) was introduced by commit `7cc103a` (`test(42-01): lock de falsificación del gate de venue del censo + enrolamiento en CI`, 2026-08-31), authored during **Phase 42**, not Phase 44. It is already part of this milestone branch's history (branch carries all of v1.8's phases, not just 44), landed and presumably reviewed under its own phase's process, and *tightens* CI (enrolls a new test file into an existing allowlist so its driver-lock actually runs — "without this line the lock would be INERT" per its own commit message) rather than weakening any gate. No phase-44 plan touched `.github/workflows/`.
- **Fix:** None applied — not a phase-44 defect. Recorded here rather than silently passing a criterion written under a narrower assumption than the branch's actual contents.
- **Files modified:** none by this plan
- **Verification:** `git log --oneline 37a83fe..828210b -- .github/workflows/ci.yml` → single hit, `7cc103a`, dated before Phase 44 began; `git show --stat 7cc103a` confirms it also added `verification/test_literal_census_venue_gate.py` (272 lines) in the same commit — a test-enrollment commit, not a gate-weakening one.
- **Committed in:** n/a (pre-existing commit, not created by this plan)

---

**Total deviations:** 3 (2 auto-fixed precondition/re-verification repairs, 1 documented-not-fixed false-positive on an overly narrow acceptance criterion)
**Impact on plan:** No scope creep. The two repairs were necessary to keep the gate honest (re-verify after an intervening push rather than trust a stale snapshot). The workflow-diff finding required investigation before the merge could be trusted as clean, but resolved to a benign pre-existing commit from an earlier phase, not a plan violation.

## Issues Encountered
None beyond the deviations above — all resolved before the irreversible merge ran.

## User Setup Required
None - no external service configuration required. `gh auth status` was already valid.

## Human Checkpoint — D-08(a), verbatim

- **Presented to operator:** PR #16 URL/number/title/state, live-re-verified `gh pr checks 16` counts (15 total / 15 pass / 2 market-data matrix rows), diff stat (+26838/-2066, 111 files, 86 under `.planning/`), gate-authorship audit (0 bare-`blocking`, 2 `human-action`/`blocking-human` tags), the exact `0.6.0` → `0.7.0` transition with the Instrument/Segment migration summary and truthiness flip, D-05 (`SURF-MD-FEEDSUB-43` folded in) and D-06 (`DRV-MD-SEG-43` deferred to Phase 45) quoted back as resolved facts, ROADMAP criterion 5 (no other package published), and the explicit statement that `main` has no branch protection.
- **Operator's reply:** **"Approved"**
- **Timestamp:** 2026-09-01T13:22:49Z
- **Not auto-issued:** The reply was collected via an explicit interactive checkpoint (`AskUserQuestion`) presented to the operator in this session; it was not satisfied by `auto_advance`, by yolo mode, by silence, or self-issued by the agent. The orchestrator's `execute-phase.md:1057-1061` auto-approve path (which presets `{user_response}` to `approved` for `human-verify`/`decision` types without reading the gate attribute) did not fire — this checkpoint is authored as `checkpoint:human-action`, which that path does not intercept; the checkpoint was presented and answered directly.
- **Prior session's checkpoint reply at the same gate:** "abort" (2026-09-01, recorded in `.planning/STATE.md` before this session) — no irreversible action was taken then; the PR stayed open and `origin/main` stayed unchanged, exactly as designed.

## Merge Result

- **Merge command:** `gh pr merge 16 --merge` (real merge, never `--squash`, never `--rebase`; no branch-delete flag)
- **MERGE_SHA:** `bca1add0de9336ef5ef738cb11a2bcb7623f9968`
- **Parents:** `37a83fe693a303a551f4374f48fe6fc5521804f7` (pre-merge `origin/main`), `828210b95203a598ed94002311a6f6dcfd276826` (branch head)
- **Subject:** `Merge pull request #16 from gravity-quant/milestone/v1.8-cierre-deuda-post-v1.7`
- **`git rev-list --parents -n1 origin/main | wc -w`:** `3` (commit + 2 parents) — confirmed real merge, not squash/rebase
- **`gh pr view 16 --json state`:** `MERGED`
- **Merged-tree version (`release.yml`'s own awk expression) for `market-data-client`:** `0.7.0`
- **Other five packages, pre-merge → merged-tree (unchanged, all byte-identical):**
  - `iol-client`: `0.4.0` → `0.4.0`
  - `higyrus-client`: `0.3.0` → `0.3.0`
  - `matriz-client`: `0.3.0` → `0.3.0`
  - `ambito-financiero-client`: `0.2.0` → `0.2.0`
  - `wallets-client`: `0.2.0` → `0.2.0`
- **Branch survived:** `git ls-remote --heads origin milestone/v1.8-cierre-deuda-post-v1.7` still returns a ref — no branch-delete flag was passed
- **No tag created in this plan:** `git tag -l 'market-data-client-v0.7.0'` and `git ls-remote --tags origin 'market-data-client-v0.7.0'` both empty at end of plan
- **No credential, token or SSH key was echoed at any point**

## Next Phase Readiness
Plan 44-03 remains — it creates the annotated tag `market-data-client-v0.7.0` on `MERGE_SHA` (re-resolved live, not trusted from this document) and the public GitHub Release, gated by a SECOND, independent `human-action`/`blocking-human` checkpoint (the tag/release push approval). That checkpoint has not yet been presented or answered. No blockers for 44-03: `origin/main` carries the `0.7.0` tree, the other five packages are untouched, and no tag exists yet.

---
*Phase: 44-release-market-data-client-0-7-0*
*Completed: 2026-09-01*
