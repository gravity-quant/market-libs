---
phase: 41
slug: validaci-n-nyquist-retroactiva-de-v1-7
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-31
---

# Phase 41 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (per-package, monorepo workspace) |
| **Config file** | root `pyproject.toml` (`asyncio_mode = "auto"`, `--import-mode=importlib`) |
| **Quick run command** | `uv run --package <pkg> pytest -k "<selector>"` (per audited row) |
| **Full suite command** | `uv run pytest` (workspace-wide, all 6 packages) |
| **Estimated runtime** | ~90 seconds (45 declared automated rows across Phases 35–39) |

This is a retroactive audit/documentation phase, not a feature-implementation phase. Its own
"tests" are the re-execution of the 45 `<automated>` rows already declared in the frozen
Phases 35–39 plan files (measured by the researcher this session — all green, 2 with stale
`-k` selectors returning vacuous pytest exit 5), plus bash/grep assertions verifying the
disposition tables and front-matter this phase writes are internally consistent.

---

## Sampling Rate

- **After every task commit:** Re-run the `<automated>` command(s) for the phase's declared rows being disposed in that task; for documentation-only tasks, run the front-matter/table consistency check (grep row counts against declared totals).
- **After every plan wave:** Run the full re-execution sweep across all rows touched so far.
- **Before `/gsd-verify-work`:** All five `*-VALIDATION.md` front-matters must parse, declare a tree SHA, and have zero undisposed rows.
- **Max feedback latency:** ~90 seconds (full 45-row re-run).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 41-01-01 | 01 | 0 | NYQ-01 | — / — | Frozen-tree invariant holds before any artifact write | bash | `git diff --quiet v1.7^{commit} HEAD -- . ':(exclude).planning'` | ✅ | ⬜ pending |
| 41-01-02 | 01 | 1 | NYQ-01 | — / — | Phase 35 rows re-run/reconstructed; disposition assigned | pytest+bash | `uv run pytest -k "<row selector>"` per row | ✅ | ⬜ pending |
| 41-02-01 | 02 | 1 | NYQ-01 | — / — | Phase 36 rows re-run; disposition assigned | pytest | `uv run pytest -k "<row selector>"` per row | ✅ | ⬜ pending |
| 41-03-01 | 03 | 1 | NYQ-01 | — / — | Phase 37 rows re-run incl. stale `-k alias_surfaces` fix | pytest | `uv run pytest -k "<row selector>"` per row | ✅ | ⬜ pending |
| 41-04-01 | 04 | 1 | NYQ-01 | — / — | Phase 38 rows re-run; disposition assigned | pytest | `uv run pytest -k "<row selector>"` per row | ✅ | ⬜ pending |
| 41-05-01 | 05 | 1 | NYQ-01 | — / — | Phase 39 rows re-run incl. stale `-k allowlist` fix; manual-only rows disposed | pytest+manual | `uv run pytest -k "<row selector>"` per row | ✅ | ⬜ pending |
| 41-06-01 | 06 | 2 | NYQ-01 | — / — | Every row disposed exactly once; counts close to 62 | bash | `grep -c "VERIFIED-\|NOT-VERIFIABLE" *-VALIDATION.md` | ✅ | ⬜ pending |
| 41-07-01 | 07 | 2 | NYQ-01 | — / — | CI allowlist enrollment or inert declaration for every on-disk test/lock | bash | `grep <test-id> .github/workflows/ci.yml` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] No new test files — Wave 0 is the frozen-tree invariant check (`git diff --quiet v1.7^{commit} HEAD`) run before any of the five VALIDATION.md artifacts are written.

*Existing infrastructure (pytest suites already in each package) covers all re-execution needs; this phase does not add new test files.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Phase 39's 4 manual-only rows (execution-report timing, order lifecycle under live market conditions) | NYQ-01 | Requires live MATBA ROFEX market session; not re-runnable retroactively | Inspect `.planning/verification/run-evidence/` envelopes + `39-07-SUMMARY.md` transcripts + recorded operator sign-off; assign `VERIFIED-HISTORICALLY` or `NOT-VERIFIABLE-RETROACTIVELY` per row per D-04 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter (only where earned per D-09 — this phase's own audit tasks, not a mechanical flip of Phases 35–39's flags)

**Approval:** pending
