---
phase: 28-release-prep-publish-v0-3-0
plan: 01
subsystem: infra
tags: [release, semver, uv-lock, changelog, ci-mirror, credential-scan, git-push]

# Dependency graph
requires:
  - phase: 26-calendar-write
    provides: "the 13 new public calendar-write names (8 flat `__all__` + 5 `aio` shims) the v0.4.0 changelog documents"
  - phase: 27-safe-live-verification
    provides: "the live-verified fixes (update_symbol widening, Symbol defaulted fields, marketId alias, envelope unwrap, CalendarDay field reconciliation) the v0.4.0 changelog documents"
provides:
  - "market-data-client release-ready at 0.4.0 with three aligned version sites (pyproject, __version__, uv.lock)"
  - "README `### v0.4.0` changelog entry carrying the mandatory D-03 CalendarDay field-replacement callout"
  - ".planning/ artifacts (REQUIREMENTS.md PUB-MUT-01 + ROADMAP Phase 28 block) re-pointed from the already-published v0.3.0 to v0.4.0"
  - "D-16 typecheck-coverage follow-up archived in ROADMAP § Backlog under `### Deferred to v1.6+ (from v1.5)`"
  - "origin/milestone/v1.5-mutations pushed to local HEAD via plain fast-forward — unblocks `gh pr create` in plan 28-02"
affects: [28-02 PR + merge, 28-03 tag + GitHub Release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reversible-prep / irreversible-publish split: every edit in this plan is revertible with a commit; nothing outward-facing happened beyond a fast-forward branch push"
    - "Three-way local version assertion (pyproject == __version__ == uv.lock) as the sole defense for the two sites release.yml does not validate"
    - "Pre-push credential re-scan over the full origin/main...HEAD diff, re-run after the plan's own commits rather than trusting the planning-time scan"

key-files:
  created:
    - .planning/phases/28-release-prep-publish-v0-3-0/28-01-SUMMARY.md
  modified:
    - packages/market-data-client/pyproject.toml
    - packages/market-data-client/src/market_data_client/__init__.py
    - packages/market-data-client/README.md
    - uv.lock
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "[Phase 28-01] Released as 0.4.0 (minor), not 0.3.2 and not 1.0.0 — the unpublished diff adds 13 new public names, so a patch bump would violate semver for every `~=0.3.1` pin (D-01)"
  - "[Phase 28-01] The CalendarDay field replacement ships inside a minor bump with an explicit changelog callout instead of a deprecated-alias compat shim — D-03 rejected the shim; the callout IS the locked mitigation"
  - "[Phase 28-01] The ROADMAP/phase title strings `Phase 28: Release prep + publish v0.3.0` were left verbatim while only the release target inside them was re-pointed to v0.4.0 — GSD tooling resolves the phase directory from that string"
  - "[Phase 28-01] D-16 (market-data-client absent from root mypy `files`, import-linter `root_packages` and the ci.yml:85 mypy-tests loop) stays deferred but is now archived in ROADMAP § Backlog for v1.6 so it stops rolling silently release after release"
  - "[Phase 28-01] The branch was published with a plain fast-forward push (behind=0, ahead=104); no force flag and no rebase/merge of origin/main, preserving the ~99 commit SHAs the Phase 25-27 SUMMARYs cross-reference (D-10, T-28-08)"

patterns-established:
  - "Changelog convention held: Spanish prose, `### vX.Y.Z` H3, bold lead line naming the bump class + parenthetical semver justification, bullets shaped `- **<Área> (<REQ-ID>):**`, every identifier backticked, ~95-100 col wrap, 2-space continuation indent"
  - "Scoped test invocation `uv run pytest packages/market-data-client -q` is mandatory; a bare `uv run pytest` picks up root `testpaths` including `verification/` and its 19 pre-existing matriz failures that no CI job executes (D-14)"

requirements-completed: []  # PUB-MUT-01 remains Pending — satisfied by the 28-03 publication, not by this prep plan

# Metrics
duration: 12min
completed: 2026-08-01
status: complete
---

# Phase 28 Plan 01: Release prep for market-data-client v0.4.0 Summary

**market-data-client bumped to 0.4.0 across all three version sites with a `### v0.4.0` changelog entry that names the CalendarDay field swap outright, `.planning/` re-pointed off the already-published v0.3.0, and the release branch published to origin via a plain fast-forward after a green 7-gate local CI mirror and a clean credential scan.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-08-01T21:02Z
- **Completed:** 2026-08-01T21:14Z
- **Tasks:** 3 of 3
- **Files modified:** 6 (4 in the release commit, 2 in the planning commit)

## Accomplishments

- Three version sites aligned at `0.4.0` — `pyproject.toml:3`, `__version__` and the `uv.lock` workspace-member block — with `uv lock --check` green. The `__version__` site is the one `release.yml` never validates, so the local three-way assertion is its only defense (T-28-02).
- Authored the `### v0.4.0` README changelog entry in the established Spanish voice, documenting the calendar-write surface `(MUT-MD-02)`, the live-verified fixes `(LIVE-MUT-01)`, and — non-negotiably per D-03 — an explicit `CalendarDay` field-replacement callout.
- Re-pointed `PUB-MUT-01` and the ROADMAP Phase 28 block from the already-published v0.3.0 to v0.4.0, recording the mid-milestone constancia, and archived the D-16 typecheck-coverage follow-up in a new `### Deferred to v1.6+ (from v1.5)` backlog subsection.
- Mirrored all four CI jobs locally (7 commands) — every result matched the D-15 baseline exactly — re-ran the credential scan over the full `origin/main...HEAD` diff, and published the branch with a plain fast-forward push.

## Task Commits

Each task was committed atomically:

1. **Task 1: Bump the three version sites + author the `### v0.4.0` changelog entry + refresh uv.lock** — `bd920c6` (chore) — exactly 4 files, 37 insertions / 3 deletions
2. **Task 2: Re-point PUB-MUT-01 + the ROADMAP Phase 28 block to v0.4.0 + archive D-16 in the v1.6 backlog** — `679d07f` (docs) — exactly 2 files, 11 insertions / 7 deletions
3. **Task 3: Mirror the CI gate locally + credential scan + fast-forward push** — no commit by design (no working-tree files modified); the observable output is `origin/milestone/v1.5-mutations` advancing `ce77ed4..679d07f`

**Plan metadata:** see the final `docs(28-01)` commit below.

## Files Created/Modified

- `packages/market-data-client/pyproject.toml` — `version = "0.4.0"`; the single string `release.yml:42-51` awk-reads and validates against the tag
- `packages/market-data-client/src/market_data_client/__init__.py` — `__version__ = "0.4.0"`; runtime-visible mirror, NOT validated by the pipeline
- `packages/market-data-client/README.md` — new `### v0.4.0` changelog entry (34 lines) above `### v0.3.1`
- `uv.lock` — workspace-member version re-registered by `uv lock`; churn exactly 1 insertion + 1 deletion
- `.planning/REQUIREMENTS.md` — PUB-MUT-01 targets `market-data-client-v0.4.0` + mid-milestone constancia; traceability row left `Pending`
- `.planning/ROADMAP.md` — milestone bullet, Phase 28 bullet, Goal and SC#1/#3/#4 re-pointed; new `### Deferred to v1.6+ (from v1.5)` backlog subsection

## Measured Results

### `uv.lock` churn (T-28-04 supply-chain gate)

```
$ git diff --stat uv.lock
 uv.lock | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

Exactly the 2-line churn of the `7f051ae` precedent — `uv lock` re-resolved 48 packages and reported only `Updated market-data-client v0.3.1 -> v0.4.0`. No third-party dependency was re-resolved, so no unreviewed dependency change was smuggled into the release.

### Test count

`uv run pytest packages/market-data-client -q` → **387 passed** in 0.53s. Matches the D-15 baseline. A bare `uv run pytest` was never executed at any point (D-14).

### The seven local CI-mirror gates

| # | Command | Result | Baseline match |
|---|---------|--------|----------------|
| 1 | `uv lock --check` | Resolved 48 packages, exit 0 | ✅ |
| 2 | `uv run ruff check .` | `All checks passed!` | ✅ |
| 3 | `uv run ruff format --check .` | `201 files already formatted` | ✅ (exactly 201) |
| 4 | `uv run lint-imports` | `Contracts: 4 kept, 0 broken.` | ✅ |
| 5 | `uv run mypy` | `Success: no issues found in 51 source files` | ✅ |
| 6 | `uv run pytest packages/market-data-client -q` | `387 passed` | ✅ |
| 7 | `uv run pre-commit run --all-files` | all 9 hooks `Passed` | ✅ zero file rewrites |

Gate 7 rewrote nothing, so Task 1's commit did not need amending — the README entry was authored trailing-whitespace-free and EOF-clean on the first pass.

### Do-not-touch guarantees (D-06 / D-07)

```
$ git diff --name-only market-data-client-v0.3.1..HEAD -- .github/workflows | wc -l
0
$ git diff --name-only market-data-client-v0.3.1..HEAD -- CLAUDE.md | wc -l
0
```

No workflow file and no line of `CLAUDE.md` was touched by this phase.

### Credential scan (T-28-01), re-run immediately before the push

| Check | Result |
|-------|--------|
| JWT pattern `eyJ[A-Za-z0-9_-]{20,}` in `git diff origin/main...HEAD` | no match |
| `client_secret`-style assignment of a 20+ char value in the same diff | no match |
| Tracked `.env` (`git ls-files` path component `== .env`) | none — empty output |
| `.env.example` templates | 6, all legitimate |

Clean. The scan was re-run **after** Tasks 1 and 2 landed, not inherited from the planning-time run, because the diff grows with every commit. No token, secret value or credential was echoed at any point.

### Ahead/behind at push time (computed at run time, not read from planning artifacts)

| Comparison | Behind | Ahead |
|------------|--------|-------|
| `origin/milestone/v1.5-mutations...HEAD` (pre-push) | 0 | 104 |
| `origin/main...HEAD` | 2 | 105 |

`git merge-base --is-ancestor origin/milestone/v1.5-mutations HEAD` succeeded → plain fast-forward confirmed before pushing. The push output was `ce77ed4..679d07f` (two-dot range = non-forced update). The "2 behind main" is cosmetic exactly as D-10 predicted: `git diff --stat HEAD...origin/main` produced **empty** output, so `origin/main` holds no content the branch lacks. No rebase and no merge of `origin/main` was performed.

## Decisions Made

- **Version 0.4.0, not 0.3.2 or 1.0.0** (D-01). The unpublished diff adds 13 new public names to `__all__`, so a patch bump would violate semver for every `~=0.3.1` pin; 1.0.0 would contradict locked D-13/D-22 and burn the major that `Symbol`'s docstring reserves for removing the `marketId` alias.
- **`CalendarDay` documented, not shimmed** (D-03). The changelog callout is the locked mitigation; the deprecated-alias compat shim was explicitly rejected and was not re-opened.
- **Changelog structured as two blocks.** The new-surface bullets follow the `### v0.3.0` Model-A voice; the `CalendarDay` callout is a separate `**Breaking changes** (semver minor bump en línea 0.x)` block reusing the `### v0.2.0` Model-B voice, so the source-breaking change reads as a first-class heading rather than a buried bullet.
- **Phase title strings preserved verbatim.** Only the release target inside the ROADMAP bullet and detail block was re-pointed; `### Phase 28: Release prep + publish v0.3.0` still exists character-for-character because GSD tooling resolves the `28-release-prep-publish-v0-3-0` directory from it.
- **PUB-MUT-01 left unchecked and its traceability row left `Pending`.** Flipping to `Complete` is the phase-close step after the actual publication in plan 28-03, not a prep step.

## Deviations from Plan

None — plan executed exactly as written. No deviation rule was invoked; no auto-fix was needed.

Two procedural notes that are **not** deviations:

1. **`.planning/STATE.md` was dirty during Task 3's push.** The plan's Task 3 acceptance list includes "`git status --porcelain` is empty". At push time the only modified file was `.planning/STATE.md`, carrying the orchestrator's own phase-pointer advance (27 → 28) written by `init.execute-phase` before this agent started — not a plan edit. It is folded into the final `docs(28-01)` metadata commit, after which the tree is clean. No plan-owned file was left uncommitted at any point.
2. **A second fast-forward push follows the metadata commit.** Task 3 pushed at `679d07f` as instructed. The SUMMARY / STATE / ROADMAP metadata commit lands after it, so a second plain fast-forward push is required for `origin/milestone/v1.5-mutations` to actually equal local `HEAD` — which is the plan's stated success criterion and plan 28-02's precondition (`gh pr create` must see the complete branch). Same command, still no force flag.

## Issues Encountered

None. Every gate matched its D-15 baseline on the first run.

## Residual Risk Accepted (D-03 — recorded per the plan's `<output>` requirement)

**The v0.4.0 release ships a source-breaking `CalendarDay` change inside a minor bump on the strength of a claim that was never independently audited.**

- D-13 pre-authorises the `CalendarDay` field replacement as non-breaking, arguing that `parse_calendar_response` iterated the response envelope's keys instead of `days[]`, so no released consumer could ever have held a populated `CalendarDay` instance and therefore no consumer could have been reading `d.date`, `d.marketId` or `d.isBusinessDay`.
- **The gap:** `27-VERIFICATION.md` re-verified only **D-22**. D-13 is the one non-breaking claim in this release that no independent audit has ever confirmed. `CalendarDay` has been in `__all__` since v0.2.0, so if the D-13 argument is wrong, `d.date` on a v0.3.1 consumer becomes an `AttributeError` after a minor upgrade.
- **Mitigation locked and applied:** the operator's 2026-08-01 decision was to honour D-13 and ship the minor, but require the `v0.4.0` changelog to name the field replacement explicitly so the change is discoverable rather than silent. That callout is live in `packages/market-data-client/README.md` and names all three removed fields (`date`, `marketId`, `isBusinessDay`) and all five replacements (`day`, `closed`, `description`, `open_time`, `close_time`), each backticked, plus the rationale.
- **Rejected alternatives, not to be re-opened:** a deprecated-alias compat shim following the `Symbol.marketId` pattern; escalating the release to `1.0.0`.
- **Status: accepted.** Carried into plans 28-02 and 28-03 as an accepted risk, not a blocker.

## User Setup Required

None — no external service configuration required. The remaining human involvement is the two blocking D-18 checkpoints in plans 28-02 (before merging the PR) and 28-03 (before pushing the tag).

## Next Phase Readiness

Ready for plan **28-02** (PR + merge):

- `origin/milestone/v1.5-mutations` is published and, after the metadata push, equals local `HEAD` — `gh pr create` will not fail or prompt interactively (C-1 resolved).
- All 15 CI checks are pre-validated locally; no known CI risk in the diff.
- The branch is 2 commits "behind" `origin/main` cosmetically only — do **not** rebase or merge to "fix" it (D-10).
- The PR must use `gh pr merge --merge` (true merge commit, D-11) and must keep `.planning/` artifacts (D-09, no `/gsd-pr-branch`).
- Plan 28-03 owns the release-memory file at `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md` — deliberately untouched here because it cites a `release.yml` run ID that does not exist yet (C-3).

**Blockers:** none.

## Self-Check: PASSED

- `packages/market-data-client/pyproject.toml` — FOUND, `version = "0.4.0"`
- `packages/market-data-client/src/market_data_client/__init__.py` — FOUND, `__version__ = "0.4.0"`
- `packages/market-data-client/README.md` — FOUND, contains `### v0.4.0`
- `uv.lock` — FOUND, market-data-client block at `version = "0.4.0"`
- `.planning/REQUIREMENTS.md` — FOUND, PUB-MUT-01 targets `market-data-client-v0.4.0`
- `.planning/ROADMAP.md` — FOUND, contains `### Deferred to v1.6+ (from v1.5)`
- `.planning/phases/28-release-prep-publish-v0-3-0/28-01-SUMMARY.md` — FOUND
- Commit `bd920c6` — FOUND in `git log`
- Commit `679d07f` — FOUND in `git log`, and equals `origin/milestone/v1.5-mutations` at Task 3 push time

---
*Phase: 28-release-prep-publish-v0-3-0*
*Completed: 2026-08-01*
