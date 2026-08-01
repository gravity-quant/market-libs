---
phase: 28
slug: release-prep-publish-v0-3-0
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-08-01
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `28-RESEARCH.md` § Validation Architecture (lines 1235-1277).
>
> **Note:** this phase ships **no production code**. "Tests" here means the existing
> package suite plus assertions over *release state* (version sites, lockfile churn,
> push state, PR checks, tag placement, Release assets). Every command below is an
> exact string, not a description.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx, pytest-cov |
| **Config file** | root `pyproject.toml` `[tool.pytest.ini_options]` (`:104-121`) |
| **Quick run command** | `uv run pytest packages/market-data-client -q` |
| **Full suite command** | `uv run pytest packages/market-data-client` — **scoped; never bare `uv run pytest`** (root `testpaths` includes `verification/`, which carries 19 known pre-existing matriz failures that CI never runs — see D-14 / RESEARCH P-5) |
| **Estimated runtime** | ~1 second (387 tests, 0.51s measured 2026-08-01) |
| **Local CI mirror** | `uv lock --check && uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run mypy && uv run pre-commit run --all-files` (~2 min) |

---

## Sampling Rate

- **After every task commit:** `uv run pytest packages/market-data-client -q` + the three-site version-sync assertion
- **After every plan wave:** full local CI mirror (6 commands above)
- **Before `/gsd-verify-work`:** 15/15 green on the PR, then `gh release view` shows both assets
- **Max feedback latency:** 120 seconds (local mirror); the PR gate is bounded by `gh pr checks --watch`

---

## Per-Task Verification Map

Task IDs are assigned at planning time; the rows below are the **mandatory** checks each
plan must carry. Every row is an automated assertion — there are no un-instrumented steps.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 28-01-* | 01 | 1 | PUB-MUT-01 | T-28-02 | Tag/version mismatch cannot mislabel a public artifact | assertion | `V=$(awk -F'"' '/^version[[:space:]]*=/{print $2;exit}' packages/market-data-client/pyproject.toml); test "$V" = 0.4.0 && grep -qx '__version__ = "0.4.0"' packages/market-data-client/src/market_data_client/__init__.py` | ✅ inline | ⬜ pending |
| 28-01-* | 01 | 1 | PUB-MUT-01 | T-28-04 | Unreviewed dependency change cannot ride in via the lockfile | assertion | `uv lock --check && git diff --stat uv.lock \| grep -qE 'uv\.lock \| 2 \+-'` | ✅ inline | ⬜ pending |
| 28-01-* | 01 | 1 | PUB-MUT-01 | — | Breaking field swap is discoverable, not silent (D-03) | assertion | `grep -qx '### v0.4.0' packages/market-data-client/README.md && grep -q 'CalendarDay' packages/market-data-client/README.md` | ✅ inline | ⬜ pending |
| 28-01-* | 01 | 1 | PUB-MUT-01 | — | No accidental source edit slipped into a release-prep commit | unit | `uv run pytest packages/market-data-client -q` → `387 passed` | ✅ existing | ⬜ pending |
| 28-01-* | 01 | 1 | PUB-MUT-01 | — | Local mirror of all four CI jobs is green before the PR opens | lint/type | `uv lock --check && uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run mypy && uv run pre-commit run --all-files` | ✅ existing | ⬜ pending |
| 28-01-* | 01 | 1 | PUB-MUT-01 | T-28-01 | No credential reaches the public diff | assertion | `git diff origin/main...HEAD \| grep -nE 'eyJ[A-Za-z0-9_-]{20,}'` → no match, **and** `git ls-files \| grep -E '(^\|/)\.env$'` → empty | ✅ inline | ⬜ pending |
| 28-01-* | 01 | 1 | PUB-MUT-01 | — | Workflow files untouched (D-06) | assertion | `test "$(git diff --name-only market-data-client-v0.3.1..HEAD -- .github/workflows \| wc -l \| tr -d ' ')" = 0` | ✅ inline | ⬜ pending |
| 28-01-* | 01 | 1 | PUB-MUT-01 | — | v0.2.0 read surface intact (SC #4) | assertion | `uv run python -c "import market_data_client as m; assert all(n in m.__all__ for n in ('get_market_data','get_latest','get_calendar','CalendarDay','Symbol','MarketDataSnapshot'))"` | ✅ inline | ⬜ pending |
| 28-01-* | 01 | 1 | PUB-MUT-01 | — | Branch is pushed — **C-1**, the step CONTEXT.md omits; fast-forward only, never `--force` | assertion | `test "$(git rev-parse HEAD)" = "$(git rev-parse origin/milestone/v1.5-mutations)"` | ✅ inline | ⬜ pending |
| 28-02-* | 02 | 2 | PUB-MUT-01 | T-28-05 | 15/15 green asserted by **count**, not by absence of the word "fail" — `main` is unprotected (**C-2**), so this is self-enforced | integration | count-based assertion over `gh pr checks <n>` requiring exactly 15 rows with status `pass` (see RESEARCH § Release Mechanics Phase B) | ✅ inline | ⬜ pending |
| 28-02-* | 02 | 2 | PUB-MUT-01 | — | Merge is a real merge commit, two parents (D-11) | assertion | `test "$(git rev-list --parents -n1 origin/main \| wc -w \| tr -d ' ')" -eq 3` | ✅ inline | ⬜ pending |
| 28-02-* | 02 | 2 | PUB-MUT-01 | T-28-03 | Tag resolves to the merge commit, not to a branch commit (SC #3) | assertion | `test "$(git rev-list -n1 market-data-client-v0.4.0)" = "$(git rev-parse origin/main)"` | ✅ inline | ⬜ pending |
| 28-02-* | 02 | 2 | PUB-MUT-01 | — | GitHub Release carries wheel + sdist (SC #3) | integration | `gh release view market-data-client-v0.4.0 --json assets --jq '.assets[].name'` contains `.whl` and `.tar.gz` | ✅ inline | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

**None.** Existing infrastructure covers all phase requirements — no new test files, no
framework install. Every check above is either an assertion over release state or the
already-green 387-test package suite.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Go/no-go before **merging the PR** (D-18a) | PUB-MUT-01 | Irreversible in practice; `main` has no branch protection (**C-2**), so this human gate is the *only* thing standing between a red PR and `main` | Present the 15-check table + the diff stat; wait for an explicit "approved" from the operator before running `gh pr merge --merge` |
| Go/no-go before **pushing the tag** (D-18b) | PUB-MUT-01 | Pushing the tag fires `release.yml` and creates a **public** GitHub Release; a re-point is not cleanly reversible once the Release exists | Present the resolved merge-commit SHA + the exact tag string `market-data-client-v0.4.0`; wait for a second explicit "approved" before `git push origin <tag>` |
| Residual D-03 risk acknowledgement | PUB-MUT-01 | D-13's `CalendarDay` non-breaking claim was never independently audited (`27-VERIFICATION.md` covered only D-22); no reliable probe exists for a git-installed, non-PyPI package | Record the accepted risk in the phase SUMMARY; the changelog callout is the locked mitigation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references *(N/A — no Wave 0 gaps)*
- [ ] No watch-mode flags *(exception: `gh pr checks --watch` is a bounded blocking wait on a remote gate, not a local file watcher)*
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
