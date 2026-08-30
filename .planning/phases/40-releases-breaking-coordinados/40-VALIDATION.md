---
phase: 40
slug: releases-breaking-coordinados
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-30
---

# Phase 40 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx, pytest-cov — but this phase ships no product code, so most verification is shell assertions over git/gh/registry state, not pytest cases |
| **Config file** | root `pyproject.toml` (`[tool.pytest.ini_options]`, `--import-mode=importlib`, `--strict-markers`, `pythonpath = ["."]`) |
| **Quick run command** | `uv run pytest packages/<pkg> -q` |
| **Full suite command** | `uv run pytest packages/<pkg>` × 6 **plus** `uv run pytest -q verification/<12-file allowlist>` — **never** a bare `uv run pytest` |
| **Estimated runtime** | ~30s per package suite; shell/git assertions are all well under 30s except the CI watch and the release-run watch |

---

## Sampling Rate

- **After every task commit:** Run the task's own `<verify><automated>` shell assertion (git/gh/registry state check).
- **After every plan wave:** Run the full local CI mirror (all four job bodies — lint's 8 gates, pre-commit, mypy, the 12-file `verification/` allowlist) before any push.
- **Before `/gsd-verify-work`:** 15/15 CI-green by explicit count on the PR, then post-publish wheel-install verification.
- **Max feedback latency:** 30 seconds per task; CI watch and release-run watch are the only exceptions (bounded by GitHub Actions runtime, not local).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 40-01-xx | 01 | 1 | PUB-NOBJ-01 | — | Scope gate resolves D-02/D-12 before any bump/lock (SC-4-adjacent, prevents D-10 violation) | shell | `checkpoint:decision` — operator reply recorded verbatim with timestamp | ✅ |
| 40-01-xx | 01 | 1 | PUB-NOBJ-01 | — | Only the confirmed-changed packages get a version bump | shell | `for p in packages/*/; do awk -F'"' '/^version/{print $2;exit}' $p/pyproject.toml; done` compared to the locked target table | ✅ |
| 40-01-xx | 01 | 1 | PUB-NOBJ-01 | — | Breaking callout is first in each package's `## Changelog` | shell | `grep -n -A2 '^## Changelog' packages/<pkg>/README.md` → first `###` is the new version; body's first non-blank line is the bold breaking callout | ✅ |
| 40-01-xx | 01 | 1 | PUB-NOBJ-01 | — | Migration table present and executable | shell | per-package `grep -q` on each locked before/after token (`market_data.last.price`, `not snapshot.market_data`, `titulo.puntas`, `tickPriceRanges["0"].tick`, etc.) | ✅ |
| 40-01-xx | 01 | 1 | PUB-NOBJ-01 | — | Unchanged packages NOT re-published | shell | `git tag -l 'ambito-financiero-client-v*'` and `'wallets-client-v*'` unchanged from the pre-phase set | ✅ |
| 40-01-xx | 01 | 1 | PUB-NOBJ-01 | — | `uv.lock` refreshed exactly once | shell | `git log --oneline <base>..HEAD -- uv.lock \| wc -l` == 1, and `git show --numstat --format= <that commit> -- uv.lock` == `N N` | ✅ |
| 40-02-xx | 02 | 2 | PUB-NOBJ-01 | — | CI green asserted by explicit count, never by absence of "fail" | shell | 15 total / 15 pass on the PR (12 test-matrix + lint + pre-commit + typecheck) | ✅ |
| 40-02-xx | 02 | 2 | PUB-NOBJ-01 | — | Pre-merge checkpoint never auto-approved despite yolo/auto_advance | manual | `checkpoint:human-verify gate="blocking"` — SUMMARY records operator's reply verbatim with timestamp | ✅ (34-02 template) |
| 40-02-xx | 02 | 2 | PUB-NOBJ-01 | — | Merge is a real merge commit, never squash/rebase | shell | `test "$(git rev-list --parents -n1 origin/main \| wc -w)" -eq 3` and `gh pr view <n> --json state` == `MERGED` | ✅ |
| 40-03-xx | 03 | 3 | PUB-NOBJ-01 | — | Tag-push checkpoint never auto-approved | manual | `checkpoint:human-verify gate="blocking"` — SUMMARY records operator's reply verbatim with timestamp | ✅ (34-03 template) |
| 40-03-xx | 03 | 3 | PUB-NOBJ-01 | — | Annotated tag per package on the re-resolved merge SHA | shell | `git cat-file -t <tag>` == `tag`; `git rev-list -n1 <tag>` == `git rev-parse origin/main`; per tag | ✅ |
| 40-03-xx | 03 | 3 | PUB-NOBJ-01 | — | `release.yml` unedited across the phase | shell | sha256 identity across refs (corrected form — do NOT reuse Phase 34's broken path-diff form, see Wave 0) | ✅ |
| 40-03-xx | 03 | 3 | PUB-NOBJ-01 | — | Wheel + sdist published per package | shell | `gh release view <tag> --json assets --jq '.assets[].name'` matches both exact filenames | ✅ |
| 40-03-xx | 03 | 3 | PUB-NOBJ-01 | — | Post-publish install + deep chain per package | shell + python | throwaway `uv venv --python 3.12` + `uv pip install <public wheel URL>` + deep-chain assertion from RESEARCH.md § Code Examples | ❌ **Wave 0 — no precedent task exists, must be authored** |

*Status: ⬜ pending — task IDs finalized when gsd-planner produces the actual PLAN.md files.*

---

## Wave 0 Requirements

- [x] **Post-publish wheel-install verification task** — authored as `40-03` Task 3 (throwaway venv pinned to Python 3.12, install from public GitHub Release wheel URLs, `__version__` assertions, deep-chain exercise per package). Confirmed present by gsd-plan-checker.
- [x] **Corrected `release.yml`-unedited assertion** — `40-01` Task 4(d) and `40-03` Task 2(f) both use the sha256-identity form across refs, not Phase 34's broken path-diff form. Confirmed present by gsd-plan-checker.
- [x] **`uv sync` step after `uv lock`** — `40-01` Task 4 runs `uv sync --all-packages --all-extras --dev` immediately after the single `uv lock`. Confirmed present by gsd-plan-checker.
- [x] No new pytest files or fixtures are needed. Framework install: none.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Scope gate (D-02 higyrus fold-in, D-12 market_id/active) | PUB-NOBJ-01 | Scope-adjacent decision — project precedent (D-08/D-18) forbids auto-resolution by any agent | Present both questions in a blocking `checkpoint:decision` at the start of plan 40-01; record operator's verbatim answer before any `pyproject.toml` edit |
| Pre-merge checkpoint (a) | PUB-NOBJ-01 | Irreversible operation (PR merge) — never auto-approved despite `auto_advance: true` + `mode: yolo` | `checkpoint:human-verify gate="blocking"` in plan 40-02, per the 34-02-PLAN.md template |
| Tag-push checkpoint (b) | PUB-NOBJ-01 | Irreversible operation (tag push triggers public release) — never auto-approved | `checkpoint:human-verify gate="blocking"` in plan 40-03, per the 34-03-PLAN.md template |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (post-publish install task, corrected workflow-immutability assertion, `uv sync` step)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (excluding CI/release-run watches, which are bounded by GitHub Actions runtime)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-30 (gsd-plan-checker: VERIFICATION PASSED, 0 blockers, 2 non-blocking warnings)
