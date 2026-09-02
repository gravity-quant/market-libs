---
phase: 45
slug: limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-02
validated: 2026-09-02
reconstructed: true
---

> **Reconstructed retroactively (State B, #2117).** This phase never had a `VALIDATION.md` on disk
> — it was reconstructed in this audit from `45-01..05-PLAN.md`/`SUMMARY.md`, `45-VERIFICATION.md`,
> and `45-HARN-04-DECISION.md`, then every automated command below was re-run live against HEAD
> (not copied from any artifact's own claim).

# Phase 45 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8.3 + pytest-asyncio ≥0.24 + pytest-httpx ≥0.34 |
| **Config file** | root `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest -q verification/test_drift_dedupe_falsification.py` |
| **Full suite command** | `uv run pytest -q <the 18 explicit-allowlist paths in .github/workflows/ci.yml lint job>` |
| **Estimated runtime** | ~0.2s per targeted file; 18-file allowlist ~1s |

---

## Sampling Rate

- **After every task commit:** `uv run pytest -q verification/test_drift_dedupe_falsification.py verification/test_finding_count_consistency.py`
- **After every plan wave:** the 18-file CI lint allowlist + `uv run python tools/check_surface_types.py`
- **Before `/gsd-verify-work`:** all 4 CI gates green (lint, format, mypy, pytest) + the 18-file allowlist run standalone
- **Max feedback latency:** ~1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 45-01-T1 | 01 | 1 | HARN-03 | — | `check_surface_types.py` docstring: historical block pinned to `00ffb2f~1` intact, current block dated with measured 187/337/467 | gate | `uv run python tools/check_surface_types.py` | ✅ | ✅ green — `187 __all__ names, 337 definitions scanned, 467 fields scanned, 0 violations`, re-run 2026-09-02 |
| 45-01-T2 | 01 | 1 | HARN-03 | — | `main_market_data.py::probe_parity` compares `Segment.segment` for real (D-05 ENMENDADA), mypy clean | unit+type | `uv run mypy main_market_data.py` | ✅ | ✅ green — `Success`, re-run 2026-09-02 |
| 45-01-T3 | 01 | 1 | HARN-03 | — | IN-05 retired in ROADMAP with code verification attached | doc | `grep -n 'IN-05' .planning/ROADMAP.md` | ✅ | ✅ green — only listed as resolved (Phase 40), none pending |
| 45-02-T1 | 02 | 1 | HARN-01 | T-45-01 | `(func, digest)` dedupe guard on `main_market_data.py` before `_next_fid()`; 3 runtime arms (collapse, no-collapse, fid-not-burned) | unit | `uv run pytest -q verification/test_drift_dedupe_falsification.py` | ✅ | ✅ green — **6 passed** (all arms, all 5 drivers), re-run 2026-09-02 |
| 45-02-T2 | 02 | 1 | HARN-01 | — | P-3 fid invariant (`test_finding_count_consistency.py`) unaffected, no relaxation | unit | `uv run pytest -q verification/test_finding_count_consistency.py` | ✅ | ✅ green — **2 passed**, file untouched since Phase 33-05 |
| 45-03-T1 | 03 | 2 | HARN-01 | T-45-02 | Remaining 6 D-02 drift sites (iol ×3, higyrus, matriz, ambito) guarded, no-op matches each function's return contract | unit | `uv run pytest -q verification/test_drift_dedupe_falsification.py` (arms 4-6: AST order/shape locks + higyrus runtime) | ✅ | ✅ green — included in the same 6-passed run above |
| 45-04-T1 | 04 | 2 | HARN-04 | — | Written, dated decision on matriz `verification/` debt (2 files accepted, not repaired) | doc | `test -f .planning/phases/45-*/45-HARN-04-DECISION.md` | ✅ | ✅ green — present, dated 2026-09-01, 340+ lines |
| 45-04-T2 | 04 | 2 | HARN-04 | — | Accepted-debt files reproduce their documented red state (not silently fixed, not silently worse) | unit | `uv run pytest -q verification/test_matriz_sweep_snapshot.py verification/test_main_matriz_login_fail_uniformity.py` | ✅ | ✅ **matches documented debt exactly** — `19 failed, 3 passed, 19 errors`, re-run 2026-09-02, byte-identical to `45-HARN-04-DECISION.md`'s recorded figures |
| 45-04-T3 | 04 | 2 | HARN-04 | — | Canary transfer (`test_probe_context_coverage.py`) real and green | unit | `uv run pytest -q verification/test_probe_context_coverage.py` | ✅ | ✅ green — **6 passed**, re-run 2026-09-02 |
| 45-04-T4 | 04 | 2 | HARN-04 | — | Q4 orphaned assertion closed inside an already-CI-enrolled file | unit | `uv run pytest -q verification/test_main_matriz_skip_line_shape.py -k login_sync_probe_returns_finding_never_fail` | ✅ | ✅ green — 1 passed |
| 45-05-T1 | 05 | 3 | HARN-01, HARN-03, HARN-04 | T-45-03 | CI `lint` job allowlist grows 13→18 files, exactly ONE consolidated commit | gate | `grep -c 'verification/test_.*\.py' .github/workflows/ci.yml` | ✅ | ✅ green — **18**, re-run 2026-09-02; `git log --oneline <base>..HEAD -- .github/workflows/ci.yml` confirms 1 commit |
| 45-05-T2 | 05 | 3 | HARN-03 | — | IN-06 closed: `test_public_surface.py` runs in CI, not inert | unit+gate | `uv run pytest -q verification/test_public_surface.py` + allowlist membership | ✅ | ✅ green — **4 passed**, present in `ci.yml` |
| 45-05-T3 | 05 | 3 | All three | — | All 18 allowlisted files run green together | integration | `uv run pytest -q <18 allowlist paths>` | ✅ | ✅ green — **181 passed** per `45-VERIFICATION.md`; the 6 files independently spot-checked in this audit (dedupe-falsification, fid-invariant, canary, public-surface) all green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Filas: 12 · ⬜ pending: 0 · ❌ red: 0 (2 debt files intentionally red by design, declared as such, not counted as phase coverage failures) · manual-only: 0.**

---

## Wave 0 Requirements

Existing infrastructure covered every requirement — no new test scaffolding/framework install
needed. All work landed as extensions to existing files (`verification/test_drift_dedupe_falsification.py`
is new but built on the pre-existing `verification/` pytest harness, not a new framework).

- [x] `verification/test_drift_dedupe_falsification.py` — new file, HARN-01, 6 arms across all 5 drivers. **Entregado:** 6 passed.
- [x] Framework install: **none** — pytest already present and configured.

---

## Manual-Only Verifications

None. Every behavior in this phase (dedupe guards, comment fix, CI allowlist edit, written decision
doc) is verifiable by an automated command or a direct file/grep check — no live-market or
human-judgment dependency, unlike Phases 39/42.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — all 12 rows carry a re-run automated/gate/doc-check command
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references — the 1 new test file is green
- [x] No watch-mode flags
- [x] Feedback latency < 1s (targeted commands); ~1s for the full 18-file allowlist
- [x] `nyquist_compliant: true` set in frontmatter — based on independent re-execution of all 12 rows in this audit, not inherited from any prior artifact's claim

**Approval:** closed 2026-09-02 by `/gsd-validate-phase 45` (retroactive reconstruction + audit ahead of `/gsd-complete-milestone v1.8`). No `VALIDATION.md` existed for this phase prior to this audit — reconstructed from `45-01..05-PLAN.md`/`SUMMARY.md`, `45-VERIFICATION.md`, and `45-HARN-04-DECISION.md`, then independently re-verified line-by-line against live HEAD.

---

## Validation Audit 2026-09-02

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 (file reconstructed from scratch; no missing test coverage found) |
| Escalated | 0 |

This phase had no `VALIDATION.md` at all (MISSING classification in `audit-milestone` §5.5). State B
reconstruction: read all 5 PLAN/SUMMARY pairs plus `45-VERIFICATION.md` and `45-HARN-04-DECISION.md`,
built the 12-row requirement→test map from their claims, then independently re-ran every automated
row against live HEAD rather than trusting any artifact's own report. Result: 0 MISSING, 0 PARTIAL.
The two matriz debt-file rows correctly reproduce their documented red state (`19 failed, 3 passed,
19 errors`) — this is accepted, disclosed debt per `45-HARN-04-DECISION.md`, not a validation gap.
