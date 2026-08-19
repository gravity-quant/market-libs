---
phase: 29
slug: decoder-observable
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-18
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (pytest-asyncio auto mode, pytest-httpx) |
| **Config file** | pyproject.toml (root — testpaths, strict-markers, importlib mode) |
| **Quick run command** | `uv run pytest packages/<pkg>/tests -q` (package under edit) |
| **Full suite command** | `uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q` (872-test merge gate) then `uv run pytest -q` |
| **Estimated runtime** | ~64 seconds (merge gate); full workspace longer |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/<pkg>/tests -q`
- **After every plan wave:** Run the 872-test merge gate (3 SafeModel packages) — must stay green with zero test edits
- **Before `/gsd-verify-work`:** Full suite must be green + ruff + ruff-format + mypy --strict
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner) | — | — | DEC-01 | — | divergence records never contain wire values; caplog sentinel per package | unit | `uv run pytest packages/<pkg>/tests -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Existing infrastructure covers pytest/ruff/mypy; no new framework needed
- [ ] Per-package caplog sentinel tests are net-new files (created in-phase, in-package so they run in CI matrix — `verification/` never runs in CI)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| msgspec timing-spike D-lock sign-off | DEC-01 | Operator signs the D-lock artifact with three-arm benchmark numbers | Review spike output; sign DECISION artifact |
| Sizing-run floor sign-off (≥ N per package) | DEC-01 | Floor becomes Phase 33's declared budget — operator ratifies | Review sizing report artifact |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
