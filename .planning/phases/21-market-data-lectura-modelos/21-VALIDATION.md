---
phase: 21
slug: market-data-lectura-modelos
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-29
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-httpx + pytest-asyncio (asyncio_mode = "auto") |
| **Config file** | root `pyproject.toml` (pytest config); per-package `conftest.py` |
| **Quick run command** | `uv run --package market-data-client pytest packages/market-data-client -q` |
| **Full suite command** | `uv run pytest packages/market-data-client` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run --package market-data-client pytest packages/market-data-client -q`
- **After every plan wave:** Run the full suite plus the explicit gates (`ruff check`, `ruff format --check`, `mypy` against the package path — see note)
- **Before `/gsd-verify-work`:** Full suite + all four CI gates green against the package path
- **Max feedback latency:** 15 seconds

> **Gate note (from RESEARCH.md):** `market-data-client/src` is currently absent from the root mypy `files` list and the CI matrix (deferred to Phase 24). Run gates explicitly against the package path — do NOT assume the global invocation covers this package.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | MD-01 | — | Query params for GET /marketdata + GET /marketdata/latest serialize correctly; None optionals dropped | unit | `uv run --package market-data-client pytest packages/market-data-client -q` | ❌ W0 | ⬜ pending |
| 21-01-02 | 01 | 1 | MD-01 | — | SafeModel.from_api tolerates partial/None payloads; received_at client-stamped at receipt | unit | `uv run --package market-data-client pytest packages/market-data-client -q` | ❌ W0 | ⬜ pending |
| 21-01-03 | 01 | 1 | MD-01 | — | with_options(max_retries=N) propagates via request.extensions["max_attempts"] (sync+async) | unit | `uv run --package market-data-client pytest packages/market-data-client -q` | ❌ W0 | ⬜ pending |
| 21-01-04 | 01 | 1 | MD-01 | — | Authenticated 401 → clear token → re-auth once → retry → succeed, and persistent-401 re-raise (sync+async) | unit | `uv run --package market-data-client pytest packages/market-data-client -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Task IDs are provisional — reconcile against the actual plan task numbering the planner emits.*

---

## Wave 0 Requirements

- [ ] `packages/market-data-client/tests/` — pytest-httpx test modules for market-data read surface (param serialization, model tolerance, with_options, 401 re-auth) — mirror existing package test layout
- [ ] `packages/market-data-client/tests/conftest.py` — shared fixtures (configure()/monkeypatch state isolation), if not already present from Phase 20

*Framework already installed (pytest + pytest-httpx + pytest-asyncio present in workspace).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Boolean/`entries` param wire-encoding actually accepted by the live server | MD-01 | Mocked tests cannot catch a server silently ignoring a mis-encoded filter | Deferred to Phase 23 live verification (per CONTEXT.md Claude's Discretion + Deferred Ideas) |
| `received_at`/`max_staleness_seconds` semantic reconciliation | MD-01 | Requires real develop payloads | Deferred to Phase 23 (CONTEXT.md D-02) |

*All Phase-21-scoped behaviors have automated verification; the manual items above are explicit Phase-23 reconciliation targets, not Phase-21 gaps.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-29 (plan-checker VERIFICATION PASSED; wave_0_complete flips true at execution time)
