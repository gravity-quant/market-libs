---
phase: 35
slug: fundaci-n-null-object-bool-pol-tica-del-walker
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-28
---

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3 (+pytest-asyncio, pytest-httpx) |
| **Config file** | `pyproject.toml` (root) |
| **Quick run command** | `uv run pytest packages/<pkg>/tests/test_decode.py -q` (per touched package) |
| **Full suite command** | `uv run pytest packages/ -q` (NEVER bare `pytest` — `verification/` hangs >10 min and is red at baseline per HARN-VERIF-01) |
| **Estimated runtime** | ~95 seconds (full packages/ suite: 1749 tests measured) |

---

## Sampling Rate

- **After every task commit:** Run the touched package's `tests/test_decode.py` + `tests/test_models.py`
- **After every plan wave:** Run `uv run pytest packages/ -q` + the 4 gates (`check_decode_intactness.py`, `check_uniform_structure.py`, `check_surface_types.py`, per-package `test_surface_parity.py`)
- **Before `/gsd-verify-work`:** Full suite green + `uv run mypy` clean + `git diff` empty on `verification/snapshots/`
- **Max feedback latency:** ~100 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner) | — | — | NOBJ-01 / NOBJ-02 | — | N/A | unit | see plans | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — pytest + the 4 v1.6 gates already run in CI; new tests slot into existing `tests/test_decode.py` / `tests/test_models.py` per package.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Snapshot byte-identity | NOBJ-02 (criterio 4) | `verification/` never runs in CI | `git diff --exit-code verification/snapshots/` after regen |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
