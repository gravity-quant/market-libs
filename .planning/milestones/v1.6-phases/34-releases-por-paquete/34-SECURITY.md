---
phase: 34
slug: releases-por-paquete
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-27
---

# Phase 34 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| local working tree → public GitHub repo | `gravity-quant/market-libs` is a PUBLIC repository. Pushing `milestone/v1.5-mutations` and merging PR #12 publishes the whole Phase 29-34 diff, including `.planning/` artifacts. | Full source diff, .planning/ docs |
| `pyproject.toml` version strings → `release.yml` build gate | The pipeline reads each package's version from the tagged tree and refuses to build on mismatch. Two packages means two independent instances of this boundary. | Version strings |
| `uv lock` resolver → committed `uv.lock` | An unreviewed third-party dependency re-resolution could enter the repo through a lockfile refresh nobody reads. | Dependency graph |
| agent shell → GitHub credentials (`gh` OAuth token, SSH key) | Credentials are ambient in the environment; any echo lands in transcripts and logs, or in a public PR body / release memory file. | OAuth token, SSH key |
| local branch history → published history (`main`) | Dozens of SUMMARY files across Phases 29-33 cite commit SHAs by value; a history rewrite orphans every one of them. | Commit history |
| CI check results → merge decision | `main` has NO branch protection (`GET .../branches/main/protection` → 404, confirmed live). GitHub applies no gate of its own; only the agent's count-based check and the human checkpoint stand between unverified code and the public default branch. | Merge authorization |
| local git tags → `refs/tags` on `origin` → public GitHub Release | Pushing a tag matching `*-client-v*` fires `release.yml` immediately and builds/publishes a wheel + sdist as a permanent public Release. No ordering guard, no dry-run. | Published package artifacts |
| release memory file → future agents/consumers | `.claude/projects/.../memory/market-data-client-releases.md` is the instruction source future agents use to install the package; a stale line silently propagates a superseded version. | Install instructions |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-34-01 | Information Disclosure | `origin/main...HEAD` diff published to a PUBLIC branch | high | mitigate | Credential scan (JWT pattern, `client_secret` assignment, tracked `.env`) re-run immediately before push in 34-01 Task 3 — clean across the full 375-file diff. Findings would report file/line only, never value. | closed |
| T-34-02 | Tampering | version strings vs. release tags (×2 packages) | high | mitigate | 34-01 asserted `pyproject`==`__version__` per package; 34-02 Task 3 and 34-03 Task 2 independently re-asserted the merged-tree version via `release.yml`'s own awk expression before each tag was created. Confirmed `0.3.0`/`0.5.0`. | closed |
| T-34-03 / T-34-03a | Tampering | wrong package set published; tag anchored to wrong commit | high | mitigate | 34-01 asserted zero version-site diff for the 4 unchanged packages since `iol-client-v0.2.0`. 34-03 re-resolved `MERGE_SHA` live via `git rev-parse origin/main`, verified 2-parent shape, and both tags were created via `git tag -a <name> "$MERGE_SHA"` — never bare `git tag <name>` (which would anchor to branch HEAD). Both tags confirmed to resolve to `a89fa45` via `git ls-remote`. | closed |
| T-34-04 | Supply Chain / Tampering | `uv.lock` refresh | medium | mitigate | 34-01 Task 3 asserted the churn was exactly 2 insertions + 2 deletions (two workspace-member version lines only) before committing; a wider diff would have halted the task. | closed |
| T-34-05 | Tampering / Repudiation | merging red/pending/cancelled code into an unprotected public `main`; published git history rewrite | high | mitigate | 34-02 Task 1 enforced the CI gate by exact count (15 total, 15 pass, 2 iol rows, 2 market-data rows) rather than absence-of-fail — this caught BOTH a genuine `mypy` failure and a transient "no checks reported / exit 0" false-green live during execution. No `--force`, no rebase, no `git merge origin/main` used anywhere in the phase. | closed |
| T-34-06 | Elevation of Privilege / Repudiation | the two irreversible operations: PR merge, tag push | critical | mitigate | Both are `checkpoint:human-verify` gates (D-08a, D-08b), independent and never collapsed. Both were authored `gate="blocking"` (a plan-authoring inconsistency — should read `gate="blocking-human"`) but the orchestrator explicitly overrode the default auto-approve-under-yolo behavior per the plan's own prose. Genuine literal "approved" replies were relayed from the human operator and recorded verbatim with timestamps: merge gate `2026-08-27T20:24:40Z`, tag gate `2026-08-27T21:34:30Z`. Neither gate was self-approved by the agent or satisfied by `auto_advance`/yolo mode despite both being active in `config.json`. | closed |
| T-34-07 | Information Disclosure | `gh` OAuth token / SSH key / PR body / release memory | medium | mitigate | `gh auth status` used throughout instead of ever echoing the token; PR body and release memory contain no credential value (env VARIABLE names only). Credential scans clean. | closed |
| T-34-09 / T-34-10 | Tampering | merge strategy (squash/rebase risk); wrong PR vehicle (close+replace risk) | high | mitigate | `gh pr merge 12 --merge` used exclusively — verified via `git rev-list --parents -n1 origin/main` returning exactly 3 fields (2 parents). PR #12 was updated in place via `gh pr edit 12`, never closed; `gh pr list --state open --base main` confirmed exactly 1 open PR = #12 throughout. | closed |
| T-34-11 | Repudiation / Tampering | "fixing" a bad Release by deleting/re-pointing its tag | medium | mitigate | Preventive prohibition (`must_haves.prohibitions`) — never triggered. Both tags created once, on the correct SHA, and remain unmodified; no delete/re-point occurred. | closed |
| T-34-12 | Repudiation / Information Disclosure | stale release memory misdirecting installs | medium | mitigate | 34-03 Task 3 refreshed all 6 regions of `market-data-client-releases.md` with exact-occurrence-count assertions on both install lines; the 3 protected regions verified byte-identical by diff, not by eye. Live-verified in this UAT session: fresh `pip install` from the published wheel reports `market_data_client.__version__ == "0.5.0"`. | closed |
| T-34-SC | Tampering | uv/pip/cargo installs (supply chain) | low | accept | No external package installs occur in any of the 3 plans — `uv lock` re-resolves the existing dependency set with only the two workspace-member version strings changed (T-34-04 covers that diff). No package-legitimacy audit is applicable to this phase's own execution. | closed (accepted) |

*Status: open · closed · open — below {block_on} threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `workflow.security_block_on` (`high`) count toward `threats_open`*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-34-01 | T-34-SC | This phase performs no external package installs of its own; `uv lock` only re-resolves the two already-published workspace members' version strings. A full supply-chain audit of the existing third-party dependency set is out of scope for a release-prep phase and was already covered when those dependencies were first introduced. | sebadlf (operator, via the two D-08 checkpoint approvals covering this phase's full diff) | 2026-08-27 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-27 | 11 | 11 | 0 | Claude (orchestrator, retroactive audit against 34-01/34-02/34-03 SUMMARY.md evidence + live UAT install verification; register was authored at plan time by gsd-planner in all 3 PLAN.md `<threat_model>` blocks, ASVS L1 — short-circuit path, no separate auditor subagent spawned per secure-phase.md Step 3) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-27
