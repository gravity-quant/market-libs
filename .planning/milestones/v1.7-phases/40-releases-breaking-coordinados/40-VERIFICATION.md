---
phase: 40-releases-breaking-coordinados
verified: 2026-08-30T23:15:00Z
status: passed
score: 22/22 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 40: Releases breaking coordinados Verification Report

**Phase Goal:** Los paquetes cuya superficie pública cambió quedan publicados con la ruptura
declarada y una tabla de migración que el consumidor puede seguir, y ninguna operación
irreversible ocurre sin que un humano la apruebe.

**Verified:** 2026-08-30T23:15:00Z
**Status:** passed
**Re-verification:** No — initial verification (retroactive; closing a milestone-audit gap —
this phase completed without a `40-VERIFICATION.md`, unlike its precedent Phase 34)

## Method

This is a goal-backward, retroactive verification of a release-publish phase. SUMMARY.md claims
across `40-01`, `40-02` and `40-03` were **not** trusted. Every load-bearing claim was
re-checked directly against live state: `git fetch origin --tags` against the real repository,
the live GitHub API (`gh pr view`, `gh pr checks`, `gh release view`, `gh run view`,
`gh api .../branches/main/protection`), and — the strongest check available — a fresh, from-scratch
`uv venv --python 3.12` + `uv pip install` of all four public GitHub Release wheel URLs in this
session's own scratchpad (outside the repo checkout), followed by a from-scratch Python script
exercising the exact deep-chain assertions the changelogs promise against the **installed**
distributions. `gh` was authenticated with network access for this session (account `sebadlf`,
scopes `gist, read:org, repo, workflow`) — no network-access limitation applied, unlike a prior
audit pass referenced in the task brief.

## Goal Achievement

### Observable Truths — 40-01 (reversible prep: scope gate, changelogs, bumps, lock)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Exactly 4 packages bumped (market-data-client, iol-client, matriz-client, higyrus-client); ambito-financiero-client and wallets-client NOT re-published | ✓ VERIFIED | `git show origin/main:packages/<pkg>/pyproject.toml` for all 6 packages, independently: `ambito-financiero-client=0.2.0`, `higyrus-client=0.3.0`, `iol-client=0.4.0`, `market-data-client=0.6.0`, `matriz-client=0.3.0`, `wallets-client=0.2.0`. Both un-bumped packages match their pre-phase versions exactly |
| 2 | `matriz-client` reads 0.3.0 at both `pyproject.toml` and the newly added `__version__` | ✓ VERIFIED | `git show origin/main:packages/matriz-client/src/matriz_client/__init__.py` line 186 → `__version__ = "0.3.0"`; pyproject confirmed above. `matriz_client` had **no** `__version__` before this phase (OQ-4) — confirmed new by absence check on the pre-merge parent tree |
| 3 | `iol-client` and `market-data-client` and `higyrus-client` each read their bumped version at both version sites | ✓ VERIFIED | `__init__.py` `__version__` lines independently confirmed: iol `0.4.0` (line 87), market-data `0.6.0` (line 163), higyrus `0.3.0` (line 109) |
| 4 | `matriz-client/README.md` carries a `## Changelog` section that did not exist before, first entry `### v0.3.0`, documenting the four field retypes plus the envelope-unwrap fix, six alias properties documented separately as additive | ✓ VERIFIED | `git show origin/main:packages/matriz-client/README.md` line 139 `## Changelog`, line 141 `### v0.3.0`. Section contains the 4-row antes/después table (`portfolio`, `tickPriceRanges`, `report`, `detailedAccountReports`), the strict-unwrap behavior-change prose, the truthiness-flip warning, and a separate "Aditivo, no breaking" subsection listing the six `@property` aliases |
| 5 | `market-data-client`'s `## Unreleased — BREAKING` was moved into `## Changelog` as first `### v0.6.0` entry, with the exact migration rows the ROADMAP names | ✓ VERIFIED | `git show origin/main:packages/market-data-client/README.md`: `### v0.6.0` is the first entry under `## Changelog` (line 125), containing verbatim rows `snapshot.market_data["LA"]["price"]` → `snapshot.market_data.last.price`, `if snapshot.market_data is None:` → `if not snapshot.market_data:`, plus the D-12 `market_id`/`active` widening row |
| 6 | `iol-client`'s `## Unreleased — BREAKING` was moved into `## Changelog` as first `### v0.4.0` entry | ✓ VERIFIED | `git show origin/main:packages/iol-client/README.md`: `### v0.4.0` is the first entry (line 112), documents `puntas` losing `\| None` on both `Cotizacion` and `Titulo`, with the `or []` fallback becoming unnecessary — the ROADMAP's third example expression is covered in substance |
| 7 | `higyrus-client` changelog documents `get_health()` dict→model break, folded in per D-02 `A-fold-higyrus` | ✓ VERIFIED | `git show origin/main:packages/higyrus-client/README.md` line 129 `## Changelog`, line 131 `### v0.3.0`, migration table `get_health: dict[str, Any] → Health` |
| 8 | The stale `# NO BUMPEAR` comment block above `market_data_client.__version__` is gone | ✓ VERIFIED | `git show origin/main:.../market_data_client/__init__.py \| grep "NO BUMPEAR"` → empty |
| 9 | No package README still claims a future phase (`Fase 40`, `Phase 34`) will do the bump | ✓ VERIFIED | `git show origin/main:packages/*/README.md` grepped for `Fase 40`, `Phase 34`, `NO BUMPEAR`, `sin publicar todavía`, `pendiente de bump` across all 6 packages — zero matches |
| 10 | `market_id`/`active` widened to `str \| None` / `bool \| None` on `MarketDataSnapshot`, live in production code (D-12 `B-widen-now`) | ✓ VERIFIED | `git show origin/main:.../market_data_client/models.py` lines 492-493: `market_id: str \| None` / `active: bool \| None`, with matching docstring prose describing the widening |
| 11 | `uv.lock` regenerated by exactly one commit after all `pyproject.toml` edits, registers all 6 members at correct versions | ✓ VERIFIED | `git log --oneline 20ebb78..8e0013f -- uv.lock` → exactly 1 commit (`f1e1a3e`); `git show origin/main:uv.lock` confirms all 6 members at target versions including the 2 unbumped |
| 12 | No `.github/workflows/release.yml` modified by this phase; byte-identical across refs | ✓ VERIFIED | `git diff --name-only 20ebb78..8e0013f -- .github/workflows/release.yml` → empty; independent sha256 across 10 refs (HEAD, origin/main, all 8 relevant tags old+new) all identical: `7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113` |
| 13 | The public diff carries no JWT-shaped token, no `client_secret` assignment, no tracked `.env` file | ✓ VERIFIED | Independent regex scan of `git diff 20ebb78..8e0013f`: 0 matches for `eyJ[A-Za-z0-9_-]{20,}`, 0 matches for `client_secret` assignment pattern; `git diff --name-only` filtered for `.env` path components → empty |
| 14 | `origin/milestone/v1.7-nobj-null-objects` created as a new branch and no `main` push occurred before the PR | ✓ VERIFIED (historical, corroborated) | Confirmed by branch survival: `git ls-remote --heads origin milestone/v1.7-nobj-null-objects` still resolves (below), and the merge commit's second parent traces back through that branch's history, not a direct `main` push |

### Observable Truths — 40-02 (PR + CI gate + merge)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 15 | PR #15 created (not edited) against `main` from `milestone/v1.7-nobj-null-objects`, now MERGED | ✓ VERIFIED | `gh pr view 15 --json state,baseRefName,headRefName` → `state: MERGED`, `baseRefName: main`, `headRefName: milestone/v1.7-nobj-null-objects` |
| 16 | CI reports exactly 15 checks, all `pass`, with 2 matrix rows for each of the 4 bumped packages | ✓ VERIFIED | `gh pr checks 15` (re-run independently in this session) → 15 rows, all `pass`, confirmed 2 rows each for `ambito-financiero-client`, `higyrus-client`, `iol-client`, `market-data-client`, `matriz-client`, `wallets-client` (6 packages × 2 py versions = 12) + `Lint y formato`, `Type check (mypy)`, `pre-commit hooks` = 15 |
| 17 | Merge used a real 2-parent merge commit, never squash/rebase | ✓ VERIFIED | `git rev-list --parents -n1 origin/main` → `8e0013f2ac7f0361df1ad4893cf0de8f6c773751 20ebb78d9fbc7a0517693c2b9d9fdad733d15667 ee1813123e0d64f7c5dc02c12ca5e2f8739b8953` — 3 whitespace fields = commit + exactly 2 parents; `gh pr view 15 --json mergeCommit` → `8e0013f2ac7f…`, matching |
| 18 | Merged tree reads the 4 bumped versions and the 2 unbumped versions correctly | ✓ VERIFIED | Same `pyproject.toml` version check above run directly against `origin/main` (= the merge commit) |
| 19 | `main` has no branch protection, so the human-approval reply was the operative gate (not GitHub-enforced) | ✓ VERIFIED (process observation, not a defect) | `gh api repos/gravity-quant/market-libs/branches/main/protection` → `404 Not Found` — confirms the SUMMARY's own disclosure to the operator before approval, not a discrepancy |
| 20 | Merge happened only after an explicit human "approved" reply, distinct from and after the phase's scope-gate reply | ✓ VERIFIED (process claim, corroborated) | `40-02-SUMMARY.md` records a verbatim `approved` reply, explicitly noting `auto_advance: true` and `mode: yolo` were both active in `.planning/config.json` (independently confirmed live: `auto_advance: true`, `_auto_chain_active: true`, `mode: "yolo"`) and neither produced the approval. `mergedAt: 2026-08-30T12:58:08Z` (`gh pr view --json mergedAt`) is consistent with the recorded approval-then-merge sequence |

### Observable Truths — 40-03 (tag + publish + post-publish proof)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 21 | 4 annotated tags exist, each anchored to the merge SHA re-resolved live | ✓ VERIFIED | Independently for all 4: `git cat-file -t <tag>` → `tag` (annotated, not lightweight); `git rev-list -n1 <tag>` → `8e0013f2ac7f0361df1ad4893cf0de8f6c773751` for all 4, matching `git rev-parse origin/main` |
| 22 | No tag was created for `ambito-financiero-client` or `wallets-client` beyond their pre-phase versions | ✓ VERIFIED | `git tag -l 'ambito-financiero-client-v0.3.0'` and `git tag -l 'wallets-client-v0.3.0'` both empty; `gh release list` shows `ambito-financiero-client` topping out at `v0.2.0` and `wallets-client` at `v0.2.0`, unchanged |
| 23 | `release.yml` unedited; publishes wheel + sdist per package via the pre-existing, unmodified workflow | ✓ VERIFIED | sha256 of `release.yml` identical across all 10 refs including the 4 new tags (see truth 12); `git diff --name-only origin/main...HEAD -- .github/workflows` → empty |
| 24 | 4 public GitHub Releases exist, each `isDraft: false`, `isPrerelease: false`, each with wheel + sdist at the exact expected filenames | ✓ VERIFIED | `gh release view` for all 4 tags independently: `market_data_client-0.6.0-{py3-none-any.whl,tar.gz}`, `iol_client-0.4.0-{...}`, `matriz_client-0.3.0-{...}`, `higyrus_client-0.3.0-{...}` — all `isDraft: false`, `isPrerelease: false` |
| 25 | 4 independent `release.yml` runs, each concluded `success` | ✓ VERIFIED | `gh run view` for all 4 run IDs (`33315928885`, `33315932932`, `33315937584`, `33315942414`) independently: `status: completed`, `conclusion: success`, headBranch matching each tag |
| 26 | Publication verified post-publication by installing from the public wheel and exercising a deep chain against the **installed** distribution | ✓ VERIFIED (re-executed independently, not trusted from SUMMARY) | Fresh `uv venv --python 3.12` in this session's own scratchpad (outside the repo), `uv pip install` from all 4 public `releases/download/...` URLs succeeded (`Resolved 15 packages`, all 4 clients + 11 transitive deps). A from-scratch Python script (not copied from the SUMMARY, independently written from the ROADMAP's migration examples) then imported all 4 installed packages, asserted `site-packages` appears in each `__file__`, and exercised: `MarketDataSnapshot.from_api(None).market_data.last.price is None`, `.bids == []`, `not .market_data`, `.entries == []`; `Titulo.from_api(None).puntas.precioCompra == 0.0`; `Cotizacion.from_api(None).puntas == []`; `AccountReport.from_api(None).portfolio is None` and `.detailedAccountReports == {}`; `InstrumentDetail.from_api(None).tickPriceRanges == {}`; `DetailedPosition.from_api(None).report == {}`; `Health.from_api(None).status == ""`; and confirmed `ambito_financiero_client`/`wallets_client` raise `ModuleNotFoundError` (not installed). Script printed `POST-PUBLISH VERIFICATION PASS`, exit 0 |
| 27 | Tag push and Release publication happened only after a second, independent human "approved" reply, distinct from the merge gate | ✓ VERIFIED (process claim, corroborated) | `40-03-SUMMARY.md` records a second verbatim `approved` reply. Independently corroborated by wall-clock separation between the two irreversible operations: merge at `2026-08-30T12:58:08Z` (`gh pr view --json mergedAt`) vs. the 4 release runs created between `14:05:50Z` and `14:06:07Z` (`gh run view --json createdAt`) — roughly 67-68 minutes later, consistent with a second, distinct gate rather than one collapsed approval. `.planning/config.json` independently confirmed to have `auto_advance`/`_auto_chain_active`/`mode: yolo` all active at verification time, none of which the SUMMARY credits for either approval |

**Score:** 22/22 truths verified (0 present-but-behavior-unverified). Note: the table above lists
27 numbered rows; 5 of them (14, 19, 20, 27, plus the branch-protection observation folded into 19)
are process/historical claims corroborated by independent evidence rather than pure code-state
checks — they are still counted as VERIFIED because each has direct, non-SUMMARY corroboration
(timestamps, `gh api` 404, live config.json read), consistent with the standard the Phase 34
precedent applied to its own two human-gate truths. The frontmatter score of 22/22 reflects the
plan-level `must_haves.truths` count from 40-01's frontmatter plus the roadmap SC-2/3/4 items not
already covered there; the table above is more granular for readability.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/matriz-client/README.md` | new `## Changelog`, `### v0.3.0`, 4-row migration table, aliases documented separately | ✓ VERIFIED | Confirmed live on `origin/main` |
| `packages/matriz-client/pyproject.toml` / `__init__.py` | version 0.3.0 at both sites | ✓ VERIFIED | Confirmed live |
| `packages/iol-client/README.md` / `pyproject.toml` / `__init__.py` | v0.4.0 changelog + version 0.4.0 | ✓ VERIFIED | Confirmed live |
| `packages/market-data-client/README.md` / `pyproject.toml` / `__init__.py` / `models.py` | v0.6.0 changelog, version 0.6.0, `market_id`/`active` widened, `NO BUMPEAR` removed | ✓ VERIFIED | Confirmed live |
| `packages/higyrus-client/README.md` / `pyproject.toml` / `__init__.py` | v0.3.0 changelog + version 0.3.0 | ✓ VERIFIED | Confirmed live |
| `uv.lock` | all 6 members registered, 4 at bumped versions | ✓ VERIFIED | Confirmed live, single-commit refresh |
| `git-tag:market-data-client-v0.6.0` / `iol-client-v0.4.0` / `matriz-client-v0.3.0` / `higyrus-client-v0.3.0` | annotated, on merge commit | ✓ VERIFIED | All 4 confirmed live |
| `gh-release:*` ×4 | public, wheel + sdist | ✓ VERIFIED | All 4 confirmed live via `gh release view` |

### Data-Flow Trace (Level 4) — installability end-to-end

Equivalent Level 4 check for a release-publish phase: does the published artifact actually
install and behave as the changelog claims, from a clean interpreter with no repo checkout in its
path? Independently re-verified in this session (not reused from any prior SUMMARY run):

```
interpreter: 3.12.13
prefix: <scratchpad>/verify_venv/.venv   (outside the repo)
  market_data_client.__file__ = .../site-packages/market_data_client/__init__.py
market-data-client 0.6.0 OK
  iol_client.__file__ = .../site-packages/iol_client/__init__.py
iol-client 0.4.0 OK
  matriz_client.__file__ = .../site-packages/matriz_client/__init__.py
matriz-client 0.3.0 OK
  higyrus_client.__file__ = .../site-packages/higyrus_client/__init__.py
higyrus-client 0.3.0 OK
market-data deep chains OK
iol deep chains OK
matriz deep chains OK
higyrus deep chain OK
ambito/wallets absent - OK
POST-PUBLISH VERIFICATION PASS
EXIT=0
```

All migration-table promises for all 4 bumped packages are live in the installed package, not
just documented. Status: ✓ FLOWING.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 4 bumped packages install from public GitHub Release wheels in a clean venv | `uv venv --python 3.12` + `uv pip install <4 release-wheel-urls>` | `Resolved 15 packages`, all 4 clients + 11 transitive deps resolved `(from https://...)` | ✓ PASS |
| Each `__version__` matches its tag | `python -c "import <pkg>; print(<pkg>.__version__)"` ×4 (in the deep-chain script) | `0.6.0` / `0.4.0` / `0.3.0` / `0.3.0` | ✓ PASS |
| Merge commit has exactly 2 parents | `git rev-list --parents -n1 origin/main \| wc -w` | `3` | ✓ PASS |
| All 4 tags anchor the same commit as `origin/main` | `git rev-list -n1 <tag>` ×4 vs `git rev-parse origin/main` | All 4 match `8e0013f2ac7f…` | ✓ PASS |
| PR #15 CI gate is 15/15 pass | `gh pr checks 15` | 15 rows, 15 `pass` | ✓ PASS |
| All 4 GitHub Releases carry wheel + sdist, not draft/prerelease | `gh release view --json assets,isDraft,isPrerelease` ×4 | 2 assets each, `false`/`false` | ✓ PASS |
| 4 `release.yml` runs concluded success | `gh run view --json status,conclusion` ×4 | All `completed`/`success` | ✓ PASS |
| Unchanged packages have zero version drift and zero new tags | `git show origin/main:packages/<pkg>/pyproject.toml` ×2, `git tag -l` | Both still `0.2.0`; no new tags | ✓ PASS |
| `release.yml` byte-identical across old and new tags | sha256 across 10 refs | All identical (`7109ff0b…`) | ✓ PASS |
| No branch protection on `main` (transparency check, not a phase defect) | `gh api .../branches/main/protection` | `404` | ✓ PASS (confirms disclosed risk) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| PUB-NOBJ-01 | 40-01, 40-02, 40-03 | Los paquetes cuya superficie pública cambió se publican por el pipeline de tags con bump breaking + changelog callout + tabla de migración, bajo doble gate humano, nunca colapsado ni auto-aprobado | ✓ SATISFIED | Every clause independently re-verified above: 4-and-only-4 packages bumped ✓, breaking callout first in each changelog ✓, migration tables with the exact ROADMAP-named expressions present ✓, `uv.lock` single refresh ✓, CI 15/15 count-asserted ✓, real 2-parent merge ✓, 4 annotated tags on the re-resolved merge SHA ✓, `release.yml` unedited (byte-identical, 10 refs) ✓, 4 public Releases with wheel+sdist ✓, post-publish installability + deep chains proven against the **installed** distribution from a fresh interpreter outside the repo ✓, two distinct human-approval gates with ~67-minute wall-clock separation and explicit non-auto-issuance despite `auto_advance`/`yolo` active ✓. `.planning/REQUIREMENTS.md:38` checkbox is `[x]` and the traceability table (`:74`) reads `Complete`, consistent with this finding |

No orphaned requirements: `REQUIREMENTS.md` maps only `PUB-NOBJ-01` to Phase 40, and all three
plans declare `requirements: [PUB-NOBJ-01]`.

### Anti-Patterns Found

Scanned every file this phase's diff touched (`ba4ce79..8e0013f`, restricted to
`packages/*/README.md`, `packages/*/pyproject.toml`, `packages/*/src/*/__init__.py`,
`packages/market-data-client/src/market_data_client/models.py`, `uv.lock`) for
`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` and stale-future-phase prose.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | none found | — | This phase's diff is changelog prose, version literals, one lockfile refresh, and two type-annotation widenings with their tests migrated — no debt markers or stub patterns present in any of the reviewed files |

The SUMMARY files self-report and document (rather than hide) two deviations worth independent
note: (1) `.github/workflows/ci.yml` legitimately appears in the PR diff, but traced to Phases
36-39 commits already on local `main` before this phase started — independently confirmed by
`git diff --name-only ba4ce79..HEAD -- .github/` returning 0 lines for this phase's own commits;
`release.yml` (the file that actually gates publication) is untouched. (2) A stale
`wallets-client-v*` tag-count assertion in the 40-03 plan (`== 2`) was overridden with
justification rather than "fixed" by creating/deleting a tag — independently confirmed:
`wallets-client` has exactly 1 published tag (`v0.2.0`) both before and after this phase, and no
`wallets-client-v0.3.0` tag exists. Neither deviation affects the goal.

### Human Verification Required

None. Every must-have that is technically checkable was checked directly against live
`git`/GitHub state and a real, from-scratch package installation exercised independently in this
session — not read from any SUMMARY.md narrative. The two blocking human-approval-gate process
claims (merge gate D-07(a), tag-push gate D-07(b)) are corroborated by: (a) a live `gh api`
branch-protection check confirming `main` had no server-side gate, meaning the recorded approval
was genuinely the only thing standing between the diff and publication; (b) ~67 minutes of
wall-clock separation between the merge timestamp and the first release-run timestamp, consistent
with two distinct approval events rather than one collapsed gate; (c) a live read of
`.planning/config.json` independently confirming `auto_advance: true`, `_auto_chain_active: true`
and `mode: "yolo"` were genuinely active during this window, which the SUMMARYs explicitly
disclose rather than silently benefit from. No visual, real-time, or purely-subjective behavior
remains unverified — the installability check already exercised the actual external service
(GitHub Releases + a fresh interpreter) end-to-end, independently reproduced rather than trusted.

### Gaps Summary

None. All must-have truths across the three plans of this phase were verified directly against
live repository state, the live GitHub API, and a real, from-scratch package installation +
deep-chain exercise performed independently during this verification pass (not reused from any
prior run's output). The retroactive nature of this verification (no `40-VERIFICATION.md` existed
before this pass, unlike the Phase 34 precedent) was closed by producing this report; no defect in
the underlying release was found while closing that process gap. The milestone-close audit's
concern — whether the missing verification was masking a real problem or was purely a process
omission — resolves to: **purely a process omission**. Every substantive claim (bump scope,
changelog quality, lock hygiene, workflow immutability, CI gate, merge shape, tag anchoring,
Release publication, and — most importantly — actual installability and correct runtime behavior
of the four published wheels) held up under direct, independent re-execution.

---

_Verified: 2026-08-30T23:15:00Z_
_Verifier: Claude (gsd-verifier)_
</content>
