---
phase: 30
slug: iol-client-tipado
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-19
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (pytest-asyncio auto, pytest-httpx) |
| **Config file** | `pyproject.toml` (root — `[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest packages/iol-client/tests/ -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~30 seconds (package) / ~120 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/iol-client/tests/ -q`
- **After every plan wave:** Run `uv run pytest -q` + `uv run mypy packages/iol-client/src packages/iol-client/tests` + `uv run ruff check .`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner) | — | — | TYP-01 | — | no credentials in model reprs/logs | unit + typecheck | `uv run pytest packages/iol-client/tests/ -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — `packages/iol-client/tests/` already runs in the CI matrix (py3.12 + py3.13) and is mypy-strict-checked by the `ci.yml:85` loop.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live wire confirmation of `puntas` element shape in `get_quote` | TYP-01 (carry-forward) | Captured sample was `[]`; only the live API can confirm — deferred to Phase 33 strict run | Run `main_iol.py` with credentials in Phase 33 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
