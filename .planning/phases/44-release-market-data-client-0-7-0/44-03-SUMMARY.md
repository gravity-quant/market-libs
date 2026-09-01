---
phase: 44-release-market-data-client-0-7-0
plan: 03
subsystem: infra
tags: [github, release, gh-cli, market-data-client, uv, tag]

requires:
  - phase: 44-02
    provides: two-parent merge commit bca1add0 on origin/main carrying market-data-client 0.7.0
provides:
  - "Public GitHub Release market-data-client-v0.7.0 with wheel + sdist, tag anchored on the merge commit"
  - "Post-publish proof: the public wheel installs cleanly and the shipped Instrument/Segment/FeedSubscription behavior matches the changelog against the INSTALLED distribution"
affects: []

tech-stack:
  added: []
  patterns: ["annotated tag on a live-re-resolved merge SHA, never branch HEAD", "workflow immutability asserted by sha256 digest identity across refs, not by a stale tag-diff form", "post-publish consumability proof in a throwaway venv outside the repo, installed from the full Release asset URL"]

key-files:
  created: []
  modified: []

key-decisions:
  - "Operator gave a second, independent \"Approved\" reply at the D-08(b) checkpoint, distinct from the 44-02 merge approval — not auto-issued, orchestrator auto-approve path did not fire."
  - "MERGE_SHA was re-resolved live and cross-checked against 44-02-SUMMARY.md before tagging — matched exactly, no drift."

patterns-established:
  - "Pattern: close a phase's gate-authorship audit twice — once before the first irreversible op (44-02 Task 1) and once at phase end (this plan's Task 3) — so ROADMAP criterion 4 is asserted against the plan files themselves at both boundaries."

requirements-completed: [PUB-01]

duration: ~10min
completed: 2026-09-01
status: complete
---

# Phase 44 Plan 03: Tag pushed, Release published, post-publish consumability proven Summary

**`market-data-client-v0.7.0` annotated tag pushed on the live-re-resolved merge commit; public GitHub Release carries wheel + sdist; installed-distribution deep chain against the public wheel passes; other five packages' tag counts unchanged; phase-close gate-authorship audit closed at 0/2.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-09-01T13:26:35Z (operator approval)
- **Completed:** 2026-09-01 (shortly after)
- **Tasks:** 3 (Task 1 human checkpoint, Task 2 tag+push+watch+verify, Task 3 post-publish proof + final audit)
- **Files modified:** 0 repository files (git/gh operations + a throwaway venv outside the repo, removed after use)

## Accomplishments
- Presented the second, independent D-08(b) checkpoint with the live-re-resolved `MERGE_SHA` (cross-checked against `44-02-SUMMARY.md` — exact match), its two parents, the merged-tree version, and the exact tag string; operator replied **"Approved"**
- Re-derived the six-package tag baseline live before tagging: `iol-client` 4, `higyrus-client` 3, `matriz-client` 3, `ambito-financiero-client` 2, `wallets-client` 1, `market-data-client` 7 — all matched D-10's record exactly, no drift
- Created the ANNOTATED tag `market-data-client-v0.7.0` explicitly on `bca1add0de9336ef5ef738cb11a2bcb7623f9968` (never branch HEAD) and pushed it by name (never `--tags`, never `--force`)
- Watched `release.yml` run `33513425356` to `success`
- Verified the public Release lists both `market_data_client-0.7.0-py3-none-any.whl` and `market_data_client-0.7.0.tar.gz`
- Verified `release.yml`'s sha256 digest is identical across `HEAD`, `origin/main`, `market-data-client-v0.6.0` and `market-data-client-v0.7.0` (`7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113`) — seventh reuse without an edit, confirmed by digest identity
- Re-verified all six tag counts post-push, both locally and against `origin`: the five others unchanged, `market-data-client` moved 7→8
- Installed `market-data-client` 0.7.0 from its full public Release asset URL into a throwaway Python 3.12 venv outside the repo; exercised the `Instrument`/`Segment`/`FeedSubscription` deep chain against the INSTALLED distribution — all assertions passed, no unrelated package importable
- Closed the ROADMAP criterion 4 gate-authorship audit a second and final time: `0` bare-`blocking` attributes, `2` `human-action`/`blocking-human` checkpoint tags across the phase's plan files

## Task Commits
Git/gh operations only — no working-tree commits produced by this plan's own tasks (tag + push + release publish are git/GitHub state, not repo file changes). This SUMMARY and the STATE.md/ROADMAP.md updates are committed in a separate docs commit immediately following this file's creation.

## Files Created/Modified
None in the repository working tree. A throwaway venv was created outside the repo (`mktemp -d`) for Task 3 and removed after use.

## Decisions Made
- None beyond what the plan specified — followed as written, including the mandatory `bash -c` wrapping for verification blocks (zsh in this shell does not word-split unquoted variable expansions the way the plan's automated verify blocks assume; ad hoc post-hoc verification outside the plan's own `bash -c` blocks needed the same wrapping to behave correctly).

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - `gh` was already authenticated and able to push tags; no dashboard configuration needed beyond answering the checkpoint.

## Human Checkpoint — D-08(b), verbatim

- **Presented to operator:** the freshly re-resolved `MERGE_SHA` (`bca1add0de9336ef5ef738cb11a2bcb7623f9968`) with its two parents (`37a83fe` pre-merge main, `828210b` branch head), the merged-tree version (`0.7.0`, read with `release.yml`'s own awk expression), the exact tag string `market-data-client-v0.7.0`, what Task 2/3 would do automatically after approval, and the explicit permanence warning that a Release cannot be cleanly un-published nor its tag cleanly re-pointed.
- **Operator's reply:** **"Approved"**
- **Timestamp:** 2026-09-01T13:26:35Z
- **Second and independent:** distinct from the 44-02 merge approval (2026-09-01T13:22:49Z); the two gates were not collapsed. Not auto-issued — collected via an explicit interactive checkpoint presented directly to the operator in this session; the orchestrator's `execute-phase.md:1057-1061` auto-approve path (which never reads the gate attribute) did not fire because this checkpoint is authored `checkpoint:human-action`, which that path does not intercept.
- **Verified before the reply:** `origin/main` was still the two-parent merge commit and `market-data-client-v0.7.0` existed neither locally nor on `origin` at the moment of the reply.

## Tag, Release and Verification Results

- **Tag string / type / anchor:** `market-data-client-v0.7.0`, ANNOTATED (`git cat-file -t` → `tag`), anchored on `bca1add0de9336ef5ef738cb11a2bcb7623f9968` (`git rev-list -n1` matches exactly)
- **Tag message:** `market-data-client v0.7.0 — forma de Instrument/Segment reconciliada contra el wire (PUB-01)`
- **Pushed by name only:** `git push origin market-data-client-v0.7.0` — no `--tags`, no `--force`, anywhere in this phase
- **release.yml run:** ID `33513425356`, conclusion `success`, watched individually with `gh run watch`
- **Release assets (exact filenames):** `market_data_client-0.7.0-py3-none-any.whl`, `market_data_client-0.7.0.tar.gz`
- **release.yml sha256 (identical across all four refs):** `7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113` at `HEAD`, `origin/main`, `market-data-client-v0.6.0`, `market-data-client-v0.7.0`
- **Tag counts, pre-push baseline → post-push (local / remote), all matching:**
  - `iol-client`: 4 → 4 / 4
  - `higyrus-client`: 3 → 3 / 3
  - `matriz-client`: 3 → 3 / 3
  - `ambito-financiero-client`: 2 → 2 / 2
  - `wallets-client`: 1 → 1 / 1
  - `market-data-client`: 7 → 8 / 8
- **Post-publish install:** URL `https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.7.0/market_data_client-0.7.0-py3-none-any.whl`; venv Python `3.12.13`; `market_data_client.__version__` == `importlib.metadata.version("market-data-client")` == `"0.7.0"`; deep-chain script printed `POST-PUBLISH VERIFICATION PASS — installed-distribution deep chain OK`; no unrelated package (`iol_client`, `higyrus_client`, `matriz_client`, `ambito_financiero_client`, `wallets_client`) importable in the venv
- **Gate-authorship audit (phase close, matches the 44-02 Task 1 pre-merge value):** bare-`blocking` count `0`, `human-action`/`blocking-human` tag count `2`
- **No credential, token or SSH key was echoed at any point**

## Next Phase Readiness
Phase 44 is complete. `market-data-client` 0.7.0 is publicly released, tagged, and proven installable/consumable from its public wheel. The known deferral `DRV-MD-SEG-43` (`main_market_data.py`, blind to the new `Segment` shape) remains explicitly scoped to Phase 45, not this phase. No blockers.

---
*Phase: 44-release-market-data-client-0-7-0*
*Completed: 2026-09-01*
