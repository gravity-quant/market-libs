---
phase: 28-release-prep-publish-v0-3-0
verified: 2026-08-12T02:00:00Z
status: passed
score: 15/15 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: null
---

# Phase 28: Release prep + publish v0.3.0 (effective v0.4.0) Verification Report

**Phase Goal:** `market-data-client` se publica como `v0.4.0` (minor bump, no breaking sobre la superficie de lectura) por el pipeline de tags.
**Verified:** 2026-08-12T02:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

All truths verified against **live git/gh state** and the **current codebase**, not against SUMMARY.md prose. Roadmap Success Criteria (the contract) plus PLAN-frontmatter must-haves are merged below.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Version bumped to `0.4.0` in `pyproject.toml` + `__version__`; `uv.lock` refreshed and `uv lock --check` exits 0 (SC#1) | ✓ VERIFIED | Live: `pyproject.toml:3` = `0.4.0`; `__init__.py` = `__version__ = "0.4.0"`; `uv.lock` `market-data-client` block = `0.4.0`; `uv lock --check` → `Resolved 48 packages`, exit 0 |
| 2 | README changelog documents calendar-write surface (MUT-MD-02) + gate opt-in + the `CalendarDay` field replacement (`date`/`marketId`/`isBusinessDay` → `day`/`closed`/`description`/`open_time`/`close_time`), D-03 (SC#1) | ✓ VERIFIED | `packages/market-data-client/README.md:62-90` — `### v0.4.0` section, read in full: names all 8 new `__all__` entries, cites `(MUT-MD-02)` and `(LIVE-MUT-01)`, and a dedicated "Breaking changes" block names all 3 removed and all 5 replacement `CalendarDay` fields, each backticked |
| 3 | `.planning/` re-pointed off the already-published v0.3.0: PUB-MUT-01 and Phase 28 ROADMAP block target v0.4.0; D-16 mypy/import-linter follow-up archived in v1.6 Backlog | ✓ VERIFIED | `REQUIREMENTS.md:28` targets `market-data-client-v0.4.0` with the mid-milestone constancia; `ROADMAP.md:190,195-198` re-pointed SC#1/#3/#4 to v0.4.0/v0.3.1; `ROADMAP.md:252` `### Deferred to v1.6+ (from v1.5)` backlog subsection exists |
| 4 | PR open carrying the whole Phase 25-27 diff including `.planning/` artifacts (D-08/D-09) | ✓ VERIFIED | PR #10, `baseRefName=main`, `headRefName=milestone/v1.5-mutations`, state `MERGED` (live `gh pr view`) — single PR, `.planning/` retained per 28-02-SUMMARY (67/100 changed files) |
| 5 | 15 CI checks reported, all 15 `pass`, 2 of them `Tests · market-data-client · py3.12/py3.13` — counted, never inferred from absence of "fail" (SC#2) | ✓ VERIFIED | Live `gh pr checks 10`: exactly 15 rows, all `pass`, including both `market-data-client` matrix jobs |
| 6 | PR merged only after explicit human "approved" reply (D-18a), separate from the D-18b tag approval | ✓ VERIFIED | 28-02-SUMMARY records verbatim reply `approved` at `2026-08-01T22:13:53Z`; 28-03-SUMMARY records a SECOND independent verbatim `approved` at `2026-08-12T00:13:56Z` for the tag gate — two distinct timestamps, two distinct gates, matching the D-18 requirement |
| 7 | `origin/main` advanced to a real merge commit with TWO parents via `gh pr merge --merge` (D-11) | ✓ VERIFIED | Live `git rev-list --parents -n1 5d0825d…` → 3 fields (commit + 2 parents: `7b0e0b2`, `0c1a382`); subject `Merge pull request #10 …` |
| 8 | Tag `market-data-client-v0.4.0` pushed only after a SECOND explicit approval (D-18b), annotated, on the merge commit SHA (not branch HEAD) (SC#3) | ✓ VERIFIED | Live `git cat-file -t market-data-client-v0.4.0` = `tag` (annotated); `git rev-list -n1 market-data-client-v0.4.0` == `git rev-parse origin/main` == `5d0825d11e88c03e44631648d8da64d1de8fd751` |
| 9 | Public GitHub Release `market-data-client-v0.4.0` exists carrying both a `.whl` and a `.tar.gz`, built by the unedited `release.yml` (SC#3, D-06) | ✓ VERIFIED | Live `gh release view` → `isDraft=false`, `isPrerelease=false`; assets `market_data_client-0.4.0-py3-none-any.whl`, `market_data_client-0.4.0.tar.gz`; `gh run view 31549711805` → `conclusion=success`, `headSha=5d0825d…`; `git diff --name-only market-data-client-v0.3.1..market-data-client-v0.4.0 -- .github/workflows` → 0 lines |
| 10 | Minor bump measured against v0.3.1 is non-breaking on the read surface; symbols changes additive/widening; sole documented exception is the D-03 `CalendarDay` carve-out, explicit in the changelog (SC#4) | ✓ VERIFIED | README `### v0.4.0` explicitly separates "features nuevas… superficie de lectura v0.2.0 sigue intacta" from a distinct "Breaking changes" block naming the `CalendarDay` carve-out and its D-13 pre-authorization rationale; `ROADMAP.md:198` states the same baseline explicitly against v0.3.1 |
| 11 | In-repo release memory refreshed: no longer claims calendar-write/live-verification outstanding; directs consumers to v0.4.0 | ✓ VERIFIED | Live: `market-data-client-releases.md` frontmatter + "Latest published" block name v0.4.0; exactly 1 `**Scope note` paragraph (was 2 stale ones); 0 occurrences of `NOT yet done`; both install lines carry `market-data-client-v0.4.0` / `market_data_client-0.4.0-py3-none-any.whl` |
| 12 | No file under `.github/workflows/` and no line of `CLAUDE.md` touched by this phase (D-06/D-07) | ✓ VERIFIED | Live diff `market-data-client-v0.3.1..market-data-client-v0.4.0 -- .github/workflows` = 0 lines; 28-01-SUMMARY records the same for `CLAUDE.md` |
| 13 | No tracked `.env`; no credential leaked in the published diff (T-28-01) | ✓ VERIFIED | Live `git ls-files \| grep -E '(^|/)\.env$'` → empty |
| 14 | `packages/market-data-client -q` test suite passes (387 tests) — never a bare `uv run pytest` | ✓ VERIFIED | Re-run live: `387 passed in 0.51s` |
| 15 | No debt markers (`TBD`/`FIXME`/`XXX`) introduced in phase-modified files | ✓ VERIFIED | grep across all 6 phase-modified files (pyproject.toml, `__init__.py`, README.md, REQUIREMENTS.md, ROADMAP.md, release memory) — zero matches |

**Score:** 15/15 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/market-data-client/pyproject.toml` | `version = "0.4.0"` | ✓ VERIFIED | Live grep confirms |
| `packages/market-data-client/src/market_data_client/__init__.py` | `__version__ = "0.4.0"` | ✓ VERIFIED | Live grep confirms |
| `packages/market-data-client/README.md` | `### v0.4.0` changelog w/ CalendarDay callout | ✓ VERIFIED | Full section read; all 8 required tokens present |
| `uv.lock` | workspace member at `0.4.0` | ✓ VERIFIED | Live grep + `uv lock --check` exit 0 |
| `.planning/ROADMAP.md` | v0.4.0 re-point + `### Deferred to v1.6` | ✓ VERIFIED | Live grep confirms both |
| `git-tag:market-data-client-v0.4.0` | annotated tag on merge commit | ✓ VERIFIED | Live `git cat-file -t` = `tag`; anchor matches `origin/main` |
| `gh-release:market-data-client-v0.4.0` | public Release, wheel+sdist | ✓ VERIFIED | Live `gh release view` |
| release memory file | 6 regions refreshed | ✓ VERIFIED | Live checks on all assertion patterns |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `pyproject.toml` | `.github/workflows/release.yml` | version-match gate (`awk` read of first `^version` line) | ✓ WIRED | Pipeline run `31549711805` concluded `success`, confirming the gate matched `0.4.0` == tag `0.4.0` |
| `pyproject.toml` | `uv.lock` | `uv lock` re-registers workspace member version | ✓ WIRED | `uv lock --check` exits 0 live |
| `git-tag:market-data-client-v0.4.0` | `.github/workflows/release.yml` | `*-client-v*` push trigger | ✓ WIRED | `release.yml` triggered and ran to `success` on this tag push |
| `gh-release` | release memory | `**Latest published:**` block cites SHA/PR/run ID | ✓ WIRED | All three values in the memory file match live values exactly (SHA `5d0825d`, PR #10, run `31549711805`) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PUB-MUT-01 | 28-01, 28-02, 28-03 | `market-data-client` published as `v0.4.0` via tag pipeline | ✓ SATISFIED | Live git/gh state: tag → merge commit → PR #10 (15/15 checks) → Release with both assets, `release.yml` unedited, run success. REQUIREMENTS.md checkbox remains `[ ]` and traceability row `Pending` — by design (28-01-PLAN.md explicitly defers flipping this to the phase-close step, not a prep-plan responsibility); the underlying publication is fully live and verified. |

No orphaned requirements — PUB-MUT-01 is the only requirement mapped to Phase 28 in `REQUIREMENTS.md`, and it is claimed by all three plans' frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.claude/projects/.../memory/market-data-client-releases.md:26-27`, `README.md:76-77` | — | Inaccurate `confirm` guardrail claim (covers 1 of 3 request models, misstates semantics as a persistence gate) | ℹ️ Info (per 28-REVIEW.md CR-01) | Documentation-only; the mutating-gate itself (the actual security control) is unaffected. Pre-existing known finding, explicitly out of scope for this verification per task instructions. |
| `README.md:22,30` | — | `get_marketdata()` does not exist (real name `get_market_data`) | ℹ️ Info (per 28-REVIEW.md CR-02) | Pre-existing (not introduced by phase 28's diff, which only appended the changelog); shipped inside the published wheel's long_description. Explicitly flagged as known/accepted context, not a phase-28 gap. |
| `.claude/projects/.../memory/MEMORY.md:2` | — | Index still advertises v0.2.0 as latest (untouched by phase 28) | ℹ️ Info (per 28-REVIEW.md CR-03) | The refreshed release-detail file (`market-data-client-releases.md`) is correct; only the routing index is stale. Explicitly flagged as known/accepted context, not a phase-28 gap. |

No `TBD`/`FIXME`/`XXX` debt markers found in any phase-modified file. These three items are carried forward from `28-REVIEW.md` (status `issues_found`) per explicit instruction not to re-litigate them as new gaps here — the published release artifacts (version sites, tag, Release assets, CI gate, merge shape) all verified clean and correct.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Package test suite passes | `uv run pytest packages/market-data-client -q` | `387 passed in 0.51s` | ✓ PASS |
| Lockfile consistency | `uv lock --check` | `Resolved 48 packages`, exit 0 | ✓ PASS |
| Tag anchors merge commit | `git rev-list -n1 market-data-client-v0.4.0` vs `git rev-parse origin/main` | Both `5d0825d11e88c…` | ✓ PASS |
| Merge commit has 2 parents | `git rev-list --parents -n1 origin/main \| wc -w` | `3` | ✓ PASS |
| CI gate count | `gh pr checks 10 \| wc -l` / pass count | 15 / 15 | ✓ PASS |
| Release assets | `gh release view --json assets` | `.whl` + `.tar.gz`, both `market_data_client-0.4.0*` | ✓ PASS |
| Workflow files untouched | `git diff --name-only v0.3.1..v0.4.0 -- .github/workflows` | 0 lines | ✓ PASS |
| No tracked `.env` | `git ls-files \| grep -E '(^|/)\.env$'` | empty | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` conventional probes and no probe references in PLAN/SUMMARY for this phase — this phase's verification surface is git/gh state and package tests, both covered above. Skipped (no declared or conventional probes).

### Human Verification Required

None. This phase already went through two blocking human checkpoints (D-18a merge approval, D-18b tag approval) whose recorded verbatim replies and timestamps are independently corroborated by the resulting live git/gh state (PR merged with a 2-parent commit; tag created only after; Release published only after). No further human verification is needed — the phase's remaining unknowns (documentation-accuracy defects) are pre-scoped as known/accepted context, not open questions.

### Gaps Summary

No gaps found. Every ROADMAP Success Criterion (4) and every PLAN-frontmatter must-have across all three plans (28-01, 28-02, 28-03) was independently re-verified against live git/gh state and the current codebase — not inferred from SUMMARY.md prose:

- Version bump: confirmed live at all 3 sites + `uv lock --check`.
- PR: confirmed live — 15/15 checks pass, 2 market-data-client matrix jobs, merged with a 2-parent commit.
- Tag + Release: confirmed live — annotated tag on the merge commit SHA, public Release with both wheel and sdist, `release.yml` run `31549711805` concluded `success`, workflow files unedited since v0.3.1.
- Non-breaking bump claim: the README documents the sole exception (D-03 `CalendarDay` carve-out) explicitly and separately from the "read surface intact" claim.
- `.planning/` re-pointing and D-16 backlog archival: confirmed live.
- Release memory: confirmed live — all 6 regions refreshed, single accurate scope note, no stale "outstanding" claims.

The three documentation-accuracy findings from `28-REVIEW.md` (inaccurate `confirm` guardrail scope/semantics claim; pre-existing `get_marketdata()` README typo; stale `MEMORY.md` index) remain present in the codebase as of this verification — confirmed by direct grep — but are explicitly scoped out of this goal-backward verification per the task's stated context (known/accepted, documentation defects, published artifacts themselves verified clean). They do not block phase goal achievement: PUB-MUT-01's actual deliverable — a correctly versioned, correctly tagged, publicly installable `v0.4.0` release — is fully live and verified.

The only unclosed procedural item is that `REQUIREMENTS.md`'s PUB-MUT-01 checkbox and traceability row remain `[ ]`/`Pending` — this is by design per `28-01-PLAN.md` (flipping to Complete is the phase-close step, performed after this verification passes, not a prep-plan responsibility).

---

*Verified: 2026-08-12T02:00:00Z*
*Verifier: Claude (gsd-verifier)*
