---
phase: 40
slug: releases-breaking-coordinados
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-30
---

# Phase 40 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
>
> Every entry below was re-verified independently against live repo and GitHub state.
> SUMMARY prose was treated as a claim to be tested, never as evidence.

---

## Trust Boundaries

| Boundary | Description | Data Crossing | Verified state |
|----------|-------------|---------------|----------------|
| local working tree → public GitHub repo | `gravity-quant/market-libs` is PUBLIC (`gh repo view` → `visibility=PUBLIC`). Merging PR #15 published the whole Phase 35-40 diff, including `.planning/` artifacts. | Full source diff, planning docs | Crossed. Scanned clean. |
| operator scope decision → the bump set | The 40-01 Task 1 answer (`A-fold-higyrus, B-widen-now`) fixed which packages get a version, a tag and a public Release. | Package set N=4 | Implemented outcome matches the recorded answer exactly. |
| `pyproject.toml` version strings → `release.yml` build gate | The pipeline awk-reads each package's version from the tagged tree and refuses to build on mismatch. Four independent instances. | Version strings | 4/4 match at tag, pyproject, `__version__` and published wheel. |
| `uv lock` resolver → committed `uv.lock` | An unreviewed third-party re-resolution can enter through a lockfile refresh nobody reads. | Dependency graph | Churn was exactly 4 workspace-member version lines. Zero third-party delta. |
| local branch selection → `origin/main` | `main` has **NO branch protection** (`gh api .../branches/main/protection` → **404**, confirmed live). Nothing server-side gates a direct push. | Merge authorization | Only `pr_merge` activity on `main`; no direct push. |
| agent shell → GitHub credentials (`gh` OAuth token, SSH key) | Ambient credential; any echo lands in transcripts, a public PR body, a tag message or a Release note. | OAuth token, SSH key | Zero token patterns anywhere in phase artifacts, PR body, tag messages or Release bodies. |
| local branch history → published history | SUMMARY files across Phases 35-39 cite commit SHAs by value; a rewrite orphans every one. | Commit history | All 20 sampled SHAs reachable from `origin/main`. |
| local tag namespace → `origin` | 20 local package tags + milestone tags `v1.1`…`v1.6`. `git push --tags` would publish whatever is stale. | Published tags | `v1.3` remains local-only — decisive proof `--tags` was never used. |
| public wheel → the verifying interpreter | The post-publish check is only meaningful against the published artifact, not the checkout. | Package artifacts | Wheel source proven byte-identical to the tagged tree. |
| package name → PyPI | None of the six packages is on PyPI. A bare-name install would resolve a foreign project. | Install target | Confirmed live: all six return **404** on PyPI. Full-URL rule held. |

---

## Threat Register

Dispositions are taken from the `<threat_model>` blocks of `40-01-PLAN.md`, `40-02-PLAN.md` and
`40-03-PLAN.md`. `T-40-SC` appears in all three plans with a different disposition in 40-03, so it is
recorded as three plan-scoped entries.

### Plan 40-01 — reversible release prep

| Threat ID | Category | Disposition | Independent verification | Status |
|-----------|----------|-------------|--------------------------|--------|
| T-40-01 | Information Disclosure | mitigate | Re-ran the scan over the published range `20ebb78..ee18131`: JWT `eyJ[A-Za-z0-9_-]{20,}` → **0**; secret-assignment pattern (`client_secret`/`api_key`/`password`/`access_token`/`private_key` + 20+ char value) → **0**; `gh[pousr]_`/`AKIA`/`BEGIN PRIVATE KEY` → **0**. Tracked `.env`-component files at `origin/main`: only the **6** `.env.example` templates, each carrying placeholders only (`tu_usuario`, `your-auth0-client-secret`). No value was printed during this audit. | **closed** |
| T-40-02 | Tampering | mitigate | For all four tags, read the tagged tree with `release.yml:47`'s own awk expression: `market-data-client-v0.6.0`→0.6.0, `iol-client-v0.4.0`→0.4.0, `matriz-client-v0.3.0`→0.3.0, `higyrus-client-v0.3.0`→0.3.0. `__version__` agrees at all four, **and** agrees inside each published wheel. Zero drift at any of the three sites × four packages. | **closed** |
| T-40-03 | Tampering | mitigate | Merged tree reads `ambito-financiero-client=0.2.0`, `wallets-client=0.2.0` at both pyproject and `__version__`. Neither has a `v0.3.0` tag; neither has a Release newer than 2026-07-28. `uv.lock` at `origin/main` registers both at 0.2.0. | **closed** |
| T-40-04 | Supply Chain / Tampering | mitigate | Exactly **1** commit in the PR range touches `uv.lock` (`f1e1a3e`). `git show --numstat` → **`4  4`**. Diff content is literally four `version` lines (`0.2.0→0.3.0`, `0.3.0→0.4.0`, `0.5.0→0.6.0`, `0.2.0→0.3.0`) — one per bumped workspace member. **Zero** third-party dependency lines changed. | **closed** |
| T-40-05 | Tampering / Repudiation | mitigate | All 20 sampled Phase 31-40 SHAs (`bf04b2f`, `d3cf04f`, `1c9a5bc`, `5c5c5db`, `b659084`, `cd2b4c0`, `33b11e9`, `a25fb30`, `b1654af`, `ef5296a`, `0f45508`, `ba4ce79`, `50d1c0e`, `a78eec3`, `78fd48f`, `c05a159`, `cd70d46`, `f1e1a3e`, `26ced53`, `1d62609`) test REACHABLE from `origin/main` via `git merge-base --is-ancestor`. Branch head `ee18131` is an ancestor of `origin/main`. No history was rewritten. | **closed** |
| T-40-06 | Elevation of Privilege | mitigate | **Server-side proof.** GitHub's own activity log (`repos/.../activity?ref=refs/heads/main`) shows the only `main` event for this phase is `pr_merge` at `2026-08-30T12:58:08Z` → `8e0013f`. The most recent `activity_type: push` to `main` is `2026-06-24`, two months before the phase. No `git push origin main` occurred. Branch protection is 404, so this held by discipline, not by enforcement. | **closed** |
| T-40-07 | Elevation of Privilege / Repudiation | mitigate | The recorded operator answer is `A-fold-higyrus, B-widen-now`. **Both are observable in shipped code**: `higyrus-client` is bumped to 0.3.0 at both sites and has a tag + public Release (= `A-fold-higyrus`); `models.py:492-493` at `origin/main` reads `market_id: str \| None` / `active: bool \| None` (= `B-widen-now`). A silently self-resolved answer would show a mismatch between the record and the tree. None exists. | **closed** |
| T-40-08 | Information Disclosure | mitigate | `grep -rniE 'gh[pousr]_…\|eyJ…\|AKIA…\|Bearer …'` across the entire Phase 40 planning directory → **0 hits**. SUMMARYs record `gh auth status` output as account + scopes only, never the token. | **closed** |
| T-40-09 | Tampering | mitigate | `release.yml` sha256 = `7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113`, identical across **10 refs** (HEAD, `origin/main`, the 4 new tags, the 4 prior release tags) — `sort -u` → 1. `git diff --name-only ba4ce79..ee18131 -- .github/` → **0 lines**: Phase 40 touched no workflow file in any commit. | **closed** |
| T-40-SC (40-01) | Supply Chain / Tampering | **accept** | Zero external installs in this plan; the only lockfile motion is the 4-line workspace-member churn proven under T-40-04. Recorded in the Accepted Risks Log below. | **closed (accepted)** |

### Plan 40-02 — PR + human gate + merge

| Threat ID | Category | Disposition | Independent verification | Status |
|-----------|----------|-------------|--------------------------|--------|
| T-40-10 | Tampering | mitigate | `gh pr view 15 --json statusCheckRollup`: **15 rows**, group-by conclusion → `[{SUCCESS, 15}]`. Exactly **2 rows per bumped package** (`higyrus`/`iol`/`market-data`/`matriz` × py3.12+py3.13), plus 2 for each unchanged package, plus lint/pre-commit/typecheck. Critically: `headRefOid` = `ee18131` = the merge commit's **second parent** — the merged code is exactly the code the 15 green checks covered. Counted positively; no pending, cancelled or zero-check state could pass. | **closed** |
| T-40-11 | Elevation of Privilege / Repudiation | mitigate | Verbatim `approved` recorded with timestamp and an explicit non-auto-issue statement. **Corroborated independently by git timeline**: commit `0168fa3` *"registrar el punto de detencion en el checkpoint pre-merge"* at 12:00Z is a physical artifact of the agent halting; the merge lands at 12:58Z — a **58-minute** gap. `auto_advance`/yolo self-approval would leave neither a halt commit nor a gap. | **closed** |
| T-40-12 | Tampering | mitigate | `git rev-list --parents -n1 origin/main` → **3 fields** (`8e0013f` + `20ebb78` + `ee18131`). Committer is `GitHub <noreply@github.com>` with subject `Merge pull request #15 from …` — a server-side `--merge`, not a local squash/rebase (either would yield a single-parent, locally-committed commit). All branch SHAs remain reachable. | **closed** |
| T-40-13 | Repudiation | mitigate | `40-02-SUMMARY.md:192-207` quotes the 40-01 answer verbatim (`A-fold-higyrus, B-widen-now`) with both option ids, presented as resolved fact under the heading *"re-presentadas como HECHOS RESUELTOS (no re-abiertas)"*. Neither question was re-asked. The shipped tree matches those dispositions (see T-40-07). | **closed** |
| T-40-14 | Tampering | mitigate | This plan created no tag. Confirmed by timestamp ordering: merge at `12:58:08Z`, all four tags tagged at `14:05:41Z` — 67 minutes later, in plan 40-03. The merged tree already read every target version, and the two unchanged packages stayed at 0.2.0 so neither could be tagged by mistake. | **closed** |
| T-40-15 | Information Disclosure | mitigate | `gh pr view 15 --json body` (5,345 bytes) → **0** credential-pattern hits. Release notes are `--generate-notes` output; all four bodies → **0** hits. | **closed** |
| T-40-16 | Tampering | mitigate | Same evidence as T-40-09: `git diff --name-only ba4ce79..ee18131 -- .github/` → 0 lines. The `ci.yml` delta present in the PR diff traces to 10 commits from Phases 36-39 (`d3cf04f`, `1c9a5bc`, `5c5c5db`, `b659084`, `cd2b4c0`, `33b11e9`, `a25fb30`, `b1654af`, `ef5296a`, `0f45508`), all predating `PHASE_BASE`. It was **surfaced in the PR body and at the checkpoint, not reverted or silenced** — the correct handling. See Residual Risk R-2. | **closed** |
| T-40-SC (40-02) | Supply Chain / Tampering | **accept** | No package installs occur in this plan. Recorded in the Accepted Risks Log below. | **closed (accepted)** |

### Plan 40-03 — tags + public Releases + post-publish verification

| Threat ID | Category | Disposition | Independent verification | Status |
|-----------|----------|-------------|--------------------------|--------|
| T-40-17 | Elevation of Privilege / Repudiation | mitigate | Verbatim `approved`, second and independent. **Corroborated by git timeline**: commit `61c4c9c` *"pre-gate evidence pack — detenido en el checkpoint D-07(b)"* at 13:07Z records the halt; tags land at 14:05Z — a **58-minute** gap. The two gates are **1h07m apart with a separate halt commit between them**, so they provably were not collapsed. One approval covered all four tags (D-09), as designed. | **closed** |
| T-40-18 | Tampering | mitigate | `git ls-remote --tags origin` peels all four new tags to **`8e0013f`** = `origin/main` = the merge commit. `git rev-list -n1 <tag>` agrees for all four. Notably the session HEAD at tag time was `61c4c9c`, **not** the merge — without the explicit SHA the tags would have landed outside `main`'s history. The explicit-SHA mitigation was load-bearing, not decorative. | **closed** |
| T-40-19 | Tampering | mitigate | **Decisive negative proof:** `comm -23 <(git tag -l) <(remote tags)` returns exactly one name — **`v1.3`**. A `git push --tags` would necessarily have published it. It is still local-only, so `--tags` was never run. Pre-existing package tags still peel to their original SHAs (e.g. `higyrus-client-v0.2.0`→`5d02b685`), so none was re-pointed. | **closed** |
| T-40-20 | Tampering | mitigate | `git cat-file -t` returns **`tag`** (annotated) for all four. Each tag string matches `release.yml:28`'s regex and its captured version equals the tagged tree's pyproject version — independently confirmed under T-40-02, and confirmed in production by four green `release.yml` runs whose version-match gate passed. | **closed** |
| T-40-21 | Tampering | mitigate | `release.yml` sha256 identical across **10 refs** including all four new tags (see T-40-09). All four runs concluded `success` on the **first attempt** — `gh run list` shows no failed, cancelled or re-run entry for any of them, so no retry-by-tag-deletion pressure ever arose. Zero tags deleted or re-pointed; zero Releases deleted. The spurious `wallets-client-v*==2` assertion FAIL was **overridden with justification rather than "fixed" by touching tags** — independently confirmed correct: wallets has exactly 1 tag, ambito exactly 2, matching the pre-phase baseline. | **closed** |
| T-40-22 | Supply Chain / Spoofing | mitigate | All four assets were fetched by **full public Release URL** (`https://github.com/gravity-quant/market-libs/releases/download/<tag>/<file>`); this audit re-downloaded all four unauthenticated. Asset `downloadCount` of 2/1/1/1 corroborates that a real install pulled from the public URL. **The slopsquat window is live**: all six package names return **404 on PyPI**, i.e. unregistered and claimable. When the malformed-URL 404 hit during execution (40-03 Deviation 2), the agent re-ran with quoted full URLs and did **not** fall back to a bare package name — the guard held under real pressure. | **closed** |
| T-40-23 | Tampering | mitigate | **Strongest available proof of consumability + provenance:** `market_data_client/models.py` extracted from the *published public wheel* hashes to `dfaa82fccf8e2fc5ec3a4aeb5e795c2905aa1202e51222ad705f905b31953949`, **byte-identical** to `git show market-data-client-v0.6.0:packages/market-data-client/src/market_data_client/models.py`. All four wheels' `METADATA` report the correct `Name`/`Version`, and each wheel's internal `__version__` matches. The D-12 widening (`market_id: str \| None`) is present *in the shipped artifact*, not just in the repo. | **closed** |
| T-40-24 | Tampering | mitigate | `gh run list --workflow=release.yml` shows **four distinct run IDs** — `33315928885`, `33315932932`, `33315937584`, `33315942414` — each `conclusion: success`, `status: completed`, on its own `headBranch` (one per tag), started at 14:05:50 / 14:05:55 / 14:06:01 / 14:06:07Z. Overlapping windows confirm genuine concurrency; each was verified on its own record, never inferred from a sibling. | **closed** |
| T-40-25 | Information Disclosure | mitigate | All four tag messages carry only package, version and headline (e.g. *"iol-client v0.4.0 — Cotizacion.puntas y Titulo.puntas pierden \| None (PUB-NOBJ-01)"*). All four Release bodies (`--generate-notes`, ~1.36 KB each) → **0** credential-pattern hits. Post-publish downloads used unauthenticated public URLs requiring no credential — verified by this audit re-downloading them with no token. | **closed** |
| T-40-SC (40-03) | Supply Chain / Tampering | **mitigate** | The only install-shaped operation is 40-03 Task 3, installing this repository's own wheels from public Release asset URLs. Provenance proven by hash identity against the tagged tree (T-40-23), not asserted. Zero bare-name installs. | **closed** |

---

## Accepted Risks Log

| ID | Risk | Rationale | Accepted by | Date |
|----|------|-----------|-------------|------|
| T-40-SC (40-01) | Supply-chain exposure via package installs during release prep | Plan 40-01 performs **zero external installs**. `uv lock` re-resolved the existing dependency set with only local workspace-member version strings changed; the `4 4` churn assertion (independently re-verified — the diff is literally four `version` lines) proves no third-party dependency entered. RESEARCH § Package Legitimacy Audit records zero `[ASSUMED]`, `[SUS]` or `[SLOP]` packages, so no legitimacy checkpoint applies. | Plan 40-01 `<threat_model>`, disposition `accept` | 2026-08-30 |
| T-40-SC (40-02) | Supply-chain exposure via package installs during PR + merge | Plan 40-02 performs **no package installs at all** — it is purely `gh`/`git` operations plus one planning artifact. Nothing resolvable from a registry is executed. RESEARCH § Package Legitimacy Audit records zero flagged packages. | Plan 40-02 `<threat_model>`, disposition `accept` | 2026-08-30 |

---

## Residual Risks

These are **mapped** to existing threat IDs (no unregistered attack surface), but their mitigations
are procedural or per-operation rather than structural, so they persist beyond this phase.

| ID | Residual risk | Mapped to | Standing exposure |
|----|---------------|-----------|-------------------|
| R-1 | `main` has **no branch protection** (`gh api .../branches/main/protection` → 404, re-confirmed live in this audit). The human checkpoint is the *sole* access control on merges and tag pushes to a PUBLIC default branch. Phase 40 honoured it twice, provably — but nothing server-side would stop the next actor. | T-40-06, T-40-10, T-40-11, T-40-17 | Persists. Enabling branch protection with required status checks would convert a discipline-based control into an enforced one. Recommended for a future phase; **not a Phase 40 gap**. |
| R-2 | The Phase 40 PR diff carried a `.github/workflows/ci.yml` delta inherited from Phases 36-39. Phase 40 itself touched zero workflow files (proven), and the delta was surfaced to the operator rather than reverted — the correct call. But it means "the PR diff contains no workflow paths" is not a usable invariant for release phases on this repo. | T-40-09, T-40-16 | Advisory. Future plans should assert *"this phase touched no workflow"* (`git diff PHASE_BASE..HEAD -- .github/`), never *"the cumulative diff contains none"*. |
| R-3 | None of the six package names is registered on PyPI (all **404**, verified live). Any of them can be claimed by a third party at any time; a future bare-name `pip install` would then resolve to a foreign project. | T-40-22, T-40-SC | Persists. The full-URL install rule is the only guard and must be re-applied every release. Already documented at `packages/market-data-client/README.md:38-40`. |

---

## Unregistered Flags

**None.**

All three SUMMARY `## Threat Flags` sections declare no new security surface, and this audit found no
new attack surface introduced by the phase. This is consistent with the phase's nature: it ships no
new endpoints, no auth paths, no file-access patterns and no schema changes at a trust boundary. The
only source mutations were version literals, one added `__version__`, one deleted stale comment
block, and the two D-12 type widenings — all operator-authorized and all verified present in the
published artifacts.

The three documented deviations were reviewed for hidden security impact and none was found:

- **40-02 Dev-1** (`ci.yml` in the PR diff) — traced to Phases 36-39; logged as R-2.
- **40-02 Dev-2** (two planning commits deliberately not pushed) — *strengthens* T-40-10: pushing an
  all-`.md` diff would have re-pointed the PR head to a SHA triggering **zero** checks under
  `paths-ignore`, converting a counted 15/15 gate into a false green. Correct security call.
- **40-03 Dev-1** (`wallets-client-v*==2` override) — re-verified independently: wallets has 1 tag,
  ambito has 2, neither has a `v0.3.0` tag or a new Release. The override concealed nothing, and
  no tag was created or deleted to force the assertion green.
- **40-03 Dev-2** (`zsh` word-splitting → malformed-URL 404) — the response was to re-run with quoted
  full URLs, **not** to fall back to a bare package name. T-40-22's guard held under pressure.

---

## Security Audit Trail

| Check | Method | Result |
|-------|--------|--------|
| Repo visibility | `gh repo view --json visibility` | PUBLIC |
| Branch protection on `main` | `gh api repos/:owner/:repo/branches/main/protection` | 404 (none) |
| Merge shape | `git rev-list --parents -n1 origin/main` | 3 fields — 2 parents |
| Merge provenance | `git log -1 --format='%cn <%ce>'` | `GitHub <noreply@github.com>` (server-side merge) |
| Direct pushes to `main` | `gh api repos/.../activity?ref=refs/heads/main` | Only `pr_merge`; last direct push 2026-06-24 |
| CI gate | `gh pr view 15 --json statusCheckRollup` | 15 rows / 15 SUCCESS / 2 per bumped package |
| CI↔merge binding | `headRefOid` vs merge parent 2 | `ee18131` == `ee18131` |
| History preservation | `git merge-base --is-ancestor` × 20 SHAs | 20/20 reachable |
| Tag anchors | `git ls-remote --tags origin` (peeled) | 4/4 → `8e0013f` |
| Tag annotation | `git cat-file -t` × 4 | 4/4 `tag` |
| No `--tags` push | `comm -23` local vs remote tags | `v1.3` local-only → proof |
| Version alignment | `release.yml:47` awk × 4 tagged trees | 4/4 tag == pyproject == `__version__` |
| Lockfile integrity | `git show --numstat f1e1a3e -- uv.lock` | `4  4`; diff = 4 version lines only |
| Workflow immutability | sha256 `release.yml` × 10 refs | 1 distinct hash (`7109ff0b…`) |
| Phase-40 workflow touches | `git diff --name-only ba4ce79..ee18131 -- .github/` | 0 lines |
| Credential scan (diff) | JWT / secret-assignment / `gh*_` / `AKIA` / PEM over `20ebb78..ee18131` | 0 hits |
| Credential scan (artifacts) | `grep -rniE` over Phase 40 planning dir | 0 hits |
| Credential scan (public surfaces) | PR body + 4 Release bodies + 4 tag messages | 0 hits |
| Tracked secrets | `git ls-tree -r origin/main` for `.env` | 6 `.env.example`, placeholders only |
| Release assets | `gh release view --json assets` × 4 | 4/4 wheel + sdist, exact filenames |
| Release runs | `gh run list --workflow=release.yml` | 4 distinct IDs, all `success`, first attempt |
| Artifact provenance | sha256 of `models.py` in published wheel vs tagged tree | Byte-identical (`dfaa82fc…`) |
| Wheel metadata | `METADATA` Name/Version × 4 public wheels | 4/4 correct |
| PyPI slopsquat surface | `pypi.org/pypi/<name>/json` × 6 | 6/6 404 (unregistered) |
| Negative publication | tags + releases for ambito / wallets | No `v0.3.0` tag, no new Release |
| Human gate 1 (D-07a) | halt commit `0168fa3` 12:00Z → merge 12:58Z | 58 min gap |
| Human gate 2 (D-07b) | halt commit `61c4c9c` 13:07Z → tags 14:05Z | 58 min gap; 1h07 after gate 1 |

**Implementation files modified by this audit: none.** This audit created exactly one file,
`40-SECURITY.md`.

---

## Sign-Off

**Phase 40 — releases breaking coordinados: SECURED.**

- **28/28** threat entries resolved: **26 mitigate → CLOSED**, **2 accept → documented and CLOSED**.
- **0 open threats.** No BLOCKER findings.
- **0 unregistered flags.**
- **3 residual risks** logged (R-1 branch protection, R-2 workflow-diff invariant, R-3 PyPI
  slopsquat window) — all mapped to existing threat IDs, none a Phase 40 gap.
- ASVS Level 1 coverage across V2 (authentication/secrets), V4 (access control), V5 (validation) and
  V14 (configuration) — verified rather than asserted.

The two irreversible operations of this phase — the merge to a public unprotected `main`, and the
push of four tags creating four permanent public Releases — each ran only after a distinct, literal
operator approval, each preceded by a committed halt and a ~58-minute gap, and separated from each
other by 1h07m. With branch protection absent, those checkpoints were the only access control that
existed, and the git record shows they were genuinely exercised.

The published artifacts are proven consumable and proven to originate from the tagged commit by hash
identity, not by a green pipeline alone.
