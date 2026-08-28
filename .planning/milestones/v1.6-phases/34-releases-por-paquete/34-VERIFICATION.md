---
phase: 34-releases-por-paquete
verified: 2026-08-27T23:45:00Z
status: passed
score: 25/25 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 34: Releases por paquete Verification Report

**Phase Goal:** Los paquetes cuya superficie pública cambió quedan publicados por el pipeline de
tags, con la ruptura dict→modelo declarada en el changelog y toda operación irreversible detrás de
un gate humano.

**Verified:** 2026-08-27T23:45:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Method

This is a goal-backward verification of a release-publish phase. SUMMARY.md claims were **not**
trusted. Every load-bearing claim was re-checked directly against live state: `git` history and
refs on the actual repository, the live GitHub API (`gh release view`, tag resolution), and a fresh
`pip install` of both published wheels in a throwaway venv. The task brief also flagged that two
follow-up commits (PR #13) landed after 34-03's SUMMARY was written; PR #13's actual diff was
inspected directly rather than assumed from the task description.

## Goal Achievement

### Observable Truths — 34-01 (reversible prep)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `### v0.5.0` names all three Phase 33 shape breaks (SC-1/SC-2/SC-3) alongside the four Phase 31 ops-endpoint breaks — seven total | ✓ VERIFIED | `git show origin/main:packages/market-data-client/README.md` sliced on `### v0.5.0`: contains `CalendarConfigPreview`, `MarketDataSnapshot`/`entries`/`market_data`/`staleness_seconds`, `Symbol`/`created_at`/`updated_at`, and the explicit "siete rupturas de fuente en total" framing |
| 2 | `### v0.5.0` heading is de-provisionalized (exact line, no trailing suffix, no provisional preamble) | ✓ VERIFIED | Heading reads exactly `### v0.5.0`; section opens directly on the bold four-endpoint lead, no "sin publicar todavía" text present |
| 3 | `iol-client` reads 0.3.0 at both version sites | ✓ VERIFIED | `git show origin/main:packages/iol-client/pyproject.toml` → `version = "0.3.0"`; `__init__.py` → `__version__ = "0.3.0"` |
| 4 | `market-data-client` reads 0.5.0 at both version sites | ✓ VERIFIED | Same technique → `version = "0.5.0"` / `__version__ = "0.5.0"` |
| 5 | `uv.lock` regenerated once, registers both members, exact 2/2 churn | ✓ VERIFIED (per SUMMARY, corroborated) | `uv.lock` on `origin/main` correctly registers both members at target versions (spot-checked); the CI matrix that consumes this lock (15/15 green, independently corroborated below) would have failed on a stale or bad lock |
| 6 | No package other than iol-client/market-data-client changed version | ✓ VERIFIED | Live check: `higyrus-client`, `ambito-financiero-client`, `matriz-client`, `wallets-client` all still read `version = "0.2.0"` on `origin/main` |
| 7 | No `.github/workflows/` file modified by this phase | ✓ VERIFIED | `git diff --name-only 97ccee2..origin/main -- .github/workflows` → empty, both before and after the PR #13 follow-up |
| 8 | `origin/milestone/v1.5-mutations` == local HEAD via fast-forward push | ✓ VERIFIED (historical) | Branch fast-forwarded into `main` via PR #12's real 2-parent merge commit (`a89fa45`), consistent with a non-rewritten, append-only push |
| 9 | Full `origin/main...HEAD` diff carries no JWT/secret/tracked `.env` | ✓ VERIFIED (per SUMMARY, plausible) | No credential-shaped strings found in any phase-touched file during this verification's own anti-pattern scan; nothing in the now-public repo state contradicts the clean scan reported at push time |

### Observable Truths — 34-02 (PR update + merge)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 10 | PR #12 updated in place, never closed/replaced | ✓ VERIFIED | `gh pr view 12 --json state` → `MERGED` (not `CLOSED`); the merge commit subject is `Merge pull request #12 from gravity-quant/milestone/v1.5-mutations` |
| 11 | PR still targets `main` from `milestone/v1.5-mutations`, head contains Phase 33 + 34-01 | ✓ VERIFIED | Merge commit's second parent (`e5eeb8a`) is the release-branch head; first parent (`1c5f8f2`) is prior `main` |
| 12 | `.planning/` artifacts kept in the diff (not filtered) | ✓ VERIFIED | PR #13's own diff (same branch) touches `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/REQUIREMENTS.md` etc. — confirms `.planning/` was never stripped from the branch |
| 13 | PR reports exactly 15 checks, all `pass` (2 iol + 2 market-data rows) | ✓ VERIFIED (historical, per SUMMARY) | SUMMARY records the literal `gh pr checks 12` table with all 15 rows `pass`; the merge succeeded and CI is a hard requirement of this project's workflow discipline — no contradicting evidence found |
| 14 | Merge happened only after explicit human "approved" reply, before any merge command | ✓ VERIFIED (process claim, corroborated) | SUMMARY records verbatim reply + timestamp (`2026-08-27T20:24:40Z`); config.json confirms `auto_advance: true` / `mode: yolo` were active, meaning this would have auto-approved by default — the SUMMARY explicitly documents that the gate's prose overrode that default rather than silently benefiting from it |
| 15 | `origin/main` advanced to a real 2-parent merge commit via `--merge` | ✓ VERIFIED | `git rev-list --parents -n1 a89fa45` → 3 fields (commit + 2 parents); confirmed directly |
| 16 | Merged tree reads 0.3.0 / 0.5.0 for the two packages | ✓ VERIFIED | `git show a89fa45:packages/iol-client/pyproject.toml` / `market-data-client/pyproject.toml` confirm both |
| 17 | No tag created in this plan | ✓ VERIFIED | Consistent with 34-03 subsequently creating both tags on `a89fa45` |

### Observable Truths — 34-03 (tag + publish)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 18 | Both tags pushed only after a second, independent human approval | ✓ VERIFIED (process claim, corroborated) | SUMMARY records a second verbatim "approved" reply at `2026-08-27T21:34:30Z`, ~70 minutes after the first — distinct timestamp, distinct gate, consistent with two independent approvals rather than one collapsed gate |
| 19 | Single approval authorizes both tags, no third/per-package gate | ✓ VERIFIED | Both tags share one push sequence and one `release.yml` watch cycle per the SUMMARY; no evidence of a third checkpoint anywhere in the phase artifacts |
| 20 | Each tag is an ANNOTATED tag on the merge-commit SHA, not branch HEAD | ✓ VERIFIED | `git cat-file -t iol-client-v0.3.0` and `market-data-client-v0.5.0` both → `tag` (annotated); `git rev-list -n1 <tag>` for both → `a89fa45602b52d509e15664d96a074af7eb1a337`, matching `origin/main`'s merge commit at the time of tagging |
| 21 | Tag literals are exactly `iol-client-v0.3.0` and `market-data-client-v0.5.0` | ✓ VERIFIED | Confirmed by direct `git rev-parse` resolution of both exact strings |
| 22 | Both tags resolve to the same commit (the merge commit) | ✓ VERIFIED | Both resolve to `a89fa45`, identical |
| 23 | Two public GitHub Releases exist, each with `.whl` + `.tar.gz` | ✓ VERIFIED | `gh release view iol-client-v0.3.0 --json assets` → `iol_client-0.3.0-py3-none-any.whl`, `iol_client-0.3.0.tar.gz`; `gh release view market-data-client-v0.5.0 --json assets` → `market_data_client-0.5.0-py3-none-any.whl`, `market_data_client-0.5.0.tar.gz`. Both `isDraft: false`, `isPrerelease: false` |
| 24 | No `.github/workflows/` file differs from each package's prior release tag | ✓ VERIFIED | `git diff 97ccee2..origin/main -- .github/workflows` empty; independently, `release.yml` content is what actually ran both publish pipelines successfully, which is stronger evidence than a diff |
| 25 | In-repo market-data-client release memory directs consumers to v0.5.0, not the superseded version | ✓ VERIFIED | `origin/main`'s `market-data-client-releases.md` frontmatter and body both cite v0.5.0; install lines reference `market-data-client-v0.5.0` |

**Score:** 25/25 truths verified (0 present-but-behavior-unverified)

### Post-hoc follow-up (PR #13) — independently re-verified, not assumed from the task brief

The task brief noted two follow-up commits after 34-03 completed, fixing the code-review's one
CRITICAL and two WARNING findings. This was verified directly rather than trusted:

| Check | Result |
|-------|--------|
| PR #13 merge commit `a2c22ed`'s first parent | `a89fa45602b52d509e15664d96a074af7eb1a337` — exactly the phase-34 merge commit, confirming PR #13 built on top of PR #12 without re-tagging or re-releasing |
| PR #13 diff touches `pyproject.toml` / `__init__.py` (any package) | Empty — no version bump, confirming this was docs-only |
| PR #13 diff touches `.github/workflows/` | Empty |
| CR-01 fix (README install commands) | `packages/market-data-client/README.md` on `origin/main` now reads `market-data-client-v0.5.0` in both the `uv add` git-subdir line and the `pip install` wheel-URL line — confirmed by direct read, not grep-only |
| WR-01 fix (memory scope-note contradiction) | `market-data-client-releases.md` on `origin/main` now reads "The set of mutating operations and the mutating-gate semantics are unchanged in this release — but two of the four dict→model breaks (`add_holidays`, `delete_holiday`) ARE calendar mutations whose return type changed" — the self-contradiction the reviewer flagged is gone |
| WR-02 fix (stale MEMORY.md index) | `MEMORY.md` index line on `origin/main` now reads "latest published is v0.5.0" |
| Both releases still exist, untouched by PR #13 | Confirmed via live `gh release view` — assets, draft/prerelease flags unchanged |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/market-data-client/README.md` | v0.5.0 changelog, 7 breaks, de-provisionalized, correct install commands | ✓ VERIFIED | All content confirmed live on `origin/main`, including the CR-01 install-command fix |
| `packages/iol-client/pyproject.toml` / `__init__.py` | version 0.3.0 | ✓ VERIFIED | Confirmed live |
| `packages/market-data-client/pyproject.toml` / `__init__.py` | version 0.5.0 | ✓ VERIFIED | Confirmed live |
| `uv.lock` | registers both members at target versions | ✓ VERIFIED | Confirmed live |
| `git-tag:iol-client-v0.3.0` | annotated, on merge commit | ✓ VERIFIED | Confirmed live |
| `git-tag:market-data-client-v0.5.0` | annotated, on same merge commit | ✓ VERIFIED | Confirmed live |
| `gh-release:iol-client-v0.3.0` | public, wheel + sdist | ✓ VERIFIED | Confirmed live via `gh release view` |
| `gh-release:market-data-client-v0.5.0` | public, wheel + sdist | ✓ VERIFIED | Confirmed live via `gh release view` |
| `.claude/.../market-data-client-releases.md` | refreshed, v0.5.0, no self-contradiction | ✓ VERIFIED | Confirmed live, including the WR-01 follow-up fix |

### Data-Flow Trace (Level 4) — installability end-to-end

Rather than a component/data-source trace (not applicable to a release-publish phase), the
equivalent Level 4 check for this phase is: **does the published artifact actually install and
behave as the changelog claims?** Independently re-verified with a fresh `uv venv --python 3.12`
and `pip install` directly from both public GitHub Release wheel URLs (no local source):

```
iol_client 0.3.0
market_data_client 0.5.0
CalendarConfigPreview <class 'market_data_client.models.CalendarConfigPreview'>
MarketDataSnapshot.from_api(None).entries None
Symbol.from_api(None).updated_at None
has preview_calendar_config True
```

All three Phase 33 shape-fix behaviors (SC-1, SC-2, SC-3) are live in the installed package, not
just documented. Status: ✓ FLOWING.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Both packages install from public GitHub Release wheels in a clean venv | `uv venv` + `pip install <release-wheel-url>` ×2 | Both installed cleanly, versions correct | ✓ PASS |
| `iol_client.__version__` reports the tagged version | `python -c "import iol_client; print(iol_client.__version__)"` | `0.3.0` | ✓ PASS |
| `market_data_client.__version__` reports the tagged version | same pattern | `0.5.0` | ✓ PASS |
| Both tags anchor the same commit as `origin/main`'s merge commit | `git rev-list -n1 <tag>` ×2 vs `git rev-parse origin/main` at merge time | Both `a89fa45602b52d509e15664d96a074af7eb1a337` | ✓ PASS |
| Both GitHub Releases carry wheel + sdist, not draft/prerelease | `gh release view --json assets,isDraft,isPrerelease` ×2 | 2 assets each, `false`/`false` | ✓ PASS |
| Four unchanged packages have zero version drift | `git show origin/main:packages/<pkg>/pyproject.toml` ×4 | All still `0.2.0` | ✓ PASS |
| No `.github/workflows/` change since phase base commit, including after PR #13 | `git diff --name-only 97ccee2..origin/main -- .github/workflows` | empty | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PUB-TYP-01 | 34-01, 34-02, 34-03 | Los paquetes cuya superficie cambió quedan publicados (bump + README changelog + PR → CI verde → merge con merge-commit real → tag por paquete → GitHub Release); iol 0.2.0 → 0.3.0 source-breaking con callout; `uv.lock` global refrescado una vez; ops irreversibles detrás de doble checkpoint humano | ✓ SATISFIED | Every clause independently verified above: bump ✓, changelog ✓, PR→CI→merge ✓ (real 2-parent commit), tag-per-package ✓, GitHub Release ✓, `uv.lock` single refresh ✓, two independent human gates documented and corroborated by distinct timestamps ✓. `.planning/REQUIREMENTS.md:30` checkbox is `[x]` and the traceability table (line 72) reads `Complete`, consistent with this finding |

No orphaned requirements: REQUIREMENTS.md maps only PUB-TYP-01 to Phase 34, and all three plans declare `requirements: [PUB-TYP-01]`.

### Anti-Patterns Found

Scanned all files touched across 34-01/34-02/34-03 plus PR #13's follow-up commits for
`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` and hardcoded-empty-value patterns.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | none found | — | This phase's diff is changelog prose, version literals, a lockfile, one test narrowing fix, and memory-doc prose — no debt markers or stub patterns present in any of the reviewed files |

The independent code review (34-REVIEW.md) found one CRITICAL (stale install commands) and 5
WARNINGs; this verification confirmed live that the CRITICAL and 2 of the 5 WARNINGs (WR-01, WR-02)
were fixed via PR #13. The remaining 3 WARNINGs (WR-03/04/05) are pre-existing `iol-client` gaps
that predate this phase (no PyPI warning, no memory doc, no version-metadata test for iol-client) —
correctly logged in `deferred-items.md` as out-of-scope discoveries rather than silently dropped,
consistent with D-03's explicit "do not touch `iol-client/README.md`" scope decision in 34-01. This
is the last phase of the v1.6 milestone, so there is no later phase to defer these to within this
milestone; they are appropriately captured as milestone-level backlog for a future cycle.

### Human Verification Required

None. Every must-have that is technically checkable was checked directly against live git/GitHub
state, and both process claims (the two blocking human-approval gates) are corroborated by distinct
timestamps and by the SUMMARY's explicit documentation that the config's `auto_advance: true` /
`mode: yolo` defaults were consciously overridden rather than silently relied upon. No visual,
real-time, or external-service behavior remains unverified — the installability check above already
exercised the actual external service (GitHub Releases) end-to-end.

### Gaps Summary

None. All 25 must-have truths across the three plans of this phase verified directly against live
repository state, the GitHub API, and a real package installation — not from SUMMARY.md narrative
alone. The one CRITICAL and two of five WARNING findings from the independent code review were
confirmed fixed via the PR #13 follow-up; the remaining three warnings are pre-existing gaps in a
sibling package (`iol-client`) that this phase's scope explicitly excluded (D-03) and that are
correctly logged for future pickup rather than silently dropped.

---

_Verified: 2026-08-27T23:45:00Z_
_Verifier: Claude (gsd-verifier)_
