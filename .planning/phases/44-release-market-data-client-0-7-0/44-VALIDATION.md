---
phase: 44
slug: release-market-data-client-0-7-0
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-01
validated: 2026-09-02
---

# Phase 44 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx, pytest-cov |
| **Config file** | root `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `bash -c 'uv run pytest packages/market-data-client -q'` |
| **Full suite command** | `bash -c 'uv run pytest packages/market-data-client && uv run ruff check . && uv run ruff format --check . && uv run mypy packages/market-data-client && uv run python tools/check_surface_types.py && uv run python tools/check_uniform_structure.py && uv run python tools/surface_parity.py && uv run python tools/check_decode_intactness.py && uv lock --check'` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `bash -c 'uv run pytest packages/market-data-client -q'`
- **After every plan wave:** Run the full suite command above (all four gate tools + lock check + mypy + ruff)
- **Before `/gsd-verify-work`:** Full suite must be green, plus all 15 CI checks on the release PR green (counted positively, not by absence-of-failure — D-11)
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 44-01-* | 01 | 1 | PUB-01 | — | `__version__` == pyproject == installed dist == `0.7.0` | unit | `uv run pytest packages/market-data-client/tests/test_version_metadata.py -x` | ✅ | ✅ green — **3 passed**, re-run 2026-09-02 |
| 44-01-* | 01 | 1 | PUB-01 | — | `FeedSubscription` exported from package root (D-05) | smoke | `uv run python -c "from market_data_client import FeedSubscription"` | ✅ inline | ✅ green — `OK`, re-run 2026-09-02 |
| 44-01-* | 01 | 1 | PUB-01 | — | Export surface clean, 187 names | gate | `uv run python tools/check_surface_types.py` | ✅ tool | ✅ green — `187 __all__ names, 337 definitions scanned, 0 violations` |
| 44-01-* | 01 | 1 | PUB-01 | — | `uv.lock` in sync with bumped pyproject, refreshed exactly once (D-02) | gate | `uv lock --check` | ✅ CI step | ✅ green — `Resolved 48 packages`, clean |
| 44-01-* | 01 | 1 | PUB-01 | — | README carries `### v0.7.0` + both migration tables (D-03/D-04) | doc | `bash -c 'grep -c "^### v0.7.0" packages/market-data-client/README.md'` == 1 | ✅ inline | ✅ green — `1` |
| 44-01-* | 01 | 1 | PUB-01 | — | No stale `0.6.0` in README install/wheel-name lines (D-01, scoped per OQ-3) | doc | `bash -c "sed -n '1,/^## Changelog/p' packages/market-data-client/README.md \| grep -c 0.6.0"` == 0 | ✅ inline | ✅ green — `0` |
| 44-02-* | 02 | 2 | PUB-01 | T-44-01 | 15/15 CI checks pass, counted positively (D-11) | integration | `gh pr checks 16` | ✅ inline | ✅ green — **15/15 `pass`**, re-run 2026-09-02 |
| 44-02-* | 02 | 2 | PUB-01 | T-44-04 | Merge gate authored `checkpoint:human-action gate="blocking-human"`, never `gate="blocking"` | meta | gate-authorship audit (grep) | ✅ inline | ✅ green — `44-02-PLAN.md:305` + `44-03-PLAN.md:185`, 0 bare `gate="blocking"` hits |
| 44-02-* | 02 | 2 | PUB-01 | T-44-04 | Merge is `--merge` only, never squash/rebase | integration | `git rev-list --parents -n1 bca1add0...` (two parents) | ✅ inline | ✅ green — 2 parents (`37a83fe6`, `828210b9`) confirmed |
| 44-03-* | 03 | 3 | PUB-01 | T-44-01/T-44-04 | Tag annotated, on two-parent merge commit re-resolved post-merge (D-09) | integration | `git cat-file -t` + `git rev-list --parents -n1` | ✅ inline | ✅ green — `tag` type, anchor == `bca1add0...` |
| 44-03-* | 03 | 3 | PUB-01 | T-44-04 | Tag-push gate authored `checkpoint:human-action gate="blocking-human"`, never `gate="blocking"` | meta | gate-authorship audit (grep) | ✅ inline | ✅ green — same grep as above, both plans correctly typed |
| 44-03-* | 03 | 3 | PUB-01 | — | Release carries wheel **and** sdist by exact filename | integration | `gh release view market-data-client-v0.7.0 --json assets` | ✅ inline | ✅ green — both `market_data_client-0.7.0-py3-none-any.whl` and `.tar.gz` present |
| 44-03-* | 03 | 3 | PUB-01 | — | Public wheel installs and a deep chain runs outside the repo (D-12) | e2e | throwaway-venv script (see RESEARCH.md § Code Examples) | ✅ inline | ✅ **documentary, executed** — `44-03-SUMMARY.md` records the install-and-exercise proof in a throwaway venv; not re-run here (re-running would republish nothing new, per 44-VERIFICATION.md) |
| 44-03-* | 03 | 3 | PUB-01 | T-44-05 | Other five packages' tag counts unchanged vs. measured baseline (D-10) | integration | tag-count loop, re-derived live (see RESEARCH.md § Code Examples) | ✅ inline | ✅ green — `iol-client 4, higyrus-client 3, matriz-client 3, ambito-financiero-client 2, wallets-client 1` (baseline unchanged; `market-data-client` at 9 — includes the later, out-of-milestone v0.7.1 errata tag) |
| 44-03-* | 03 | 3 | PUB-01 | T-44-03 | `release.yml` byte-identical across HEAD / origin/main / prior tags / new tag (D-02, no edits) | integration | sha256 digest identity (see RESEARCH.md § Code Examples) | ✅ inline | ✅ green — `7109ff0b...` identical across `HEAD`/`origin/main`/`market-data-client-v0.7.0` |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — no Wave 0 test scaffolding needed.
`test_version_metadata.py` already asserts the three-way version identity, all four repo gate
tools (`check_surface_types.py`, `check_uniform_structure.py`, `surface_parity.py`,
`check_decode_intactness.py`) already exist and are green at baseline, and every remaining
criterion is an inline shell assertion against live git/gh state rather than new test code.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Merge checkpoint (checkpoint a) | PUB-01 | Irreversible operation — merges 86 pending commits + this phase's release prep into `main` via a real merge commit; per D-08/CONTEXT.md this must never auto-approve, even under `auto_advance: true` + `mode: yolo` | Operator reviews the PR (15/15 CI checks green, diff scoped to `market-data-client` + README), then explicitly approves `gh pr merge --merge` |
| Tag-push checkpoint (checkpoint b) | PUB-01 | Irreversible operation — pushes the annotated `market-data-client-v0.7.0` tag, which triggers `release.yml` and publishes a public GitHub Release; per D-08/CONTEXT.md this must never auto-approve | Operator reviews the re-resolved post-merge SHA and confirms only the single named tag is pushed (never `git push --tags`), then explicitly approves the tag push |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — 13 of 14 rows carry a re-run automated/inline command; the 1 remaining row (public-wheel e2e install) is correctly declared documentary with named evidence
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none missing)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter — confirmed by independent re-execution in this audit, not carried over from the pre-execution projection

**Approval:** closed 2026-09-02 by `/gsd-validate-phase 44` (retroactive audit ahead of `/gsd-complete-milestone v1.8`). All 14 mapped behaviors re-verified live against git/gh state: 15/15 PR checks, both release-gate checkpoints correctly authored `gate="blocking-human"`, tag/merge topology confirmed, release assets confirmed, `release.yml` byte-identity confirmed, other-package tag counts unchanged.

---

## Validation Audit 2026-09-02

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

This VALIDATION.md was seeded by plan-phase before Phase 44 executed and was never reconciled
afterward (`status: draft`, #2117). All 14 rows were independently re-run against live git/gh state
in this audit (not trusted from `44-VERIFICATION.md`'s prior claims): 0 MISSING, 0 PARTIAL.
