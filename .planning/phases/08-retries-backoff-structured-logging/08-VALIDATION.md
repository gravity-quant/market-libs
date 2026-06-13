---
phase: 8
slug: retries-backoff-structured-logging
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-13
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3 + pytest-httpx 0.34 + pytest-asyncio 0.24 + pytest-cov 6.0 |
| **Config file** | `pyproject.toml` root (`[tool.pytest.ini_options]`) — `asyncio_mode = "auto"`, `--import-mode=importlib`, `--strict-markers` |
| **Quick run command** | `uv run pytest packages/<pkg>/ -x --no-header -q` (per-package, fail-fast) |
| **Full suite command** | `uv run pytest packages/ verification/ -q` (workspace-wide) |
| **Estimated runtime** | ~10-15 seconds quick / ~30-45 seconds full (current baseline 527 tests Phase 7) |

Phase 8 also runs static gates as part of green-gate verification (Plan 6):

| Static Gate | Command | Notes |
|-------------|---------|-------|
| ruff lint | `uv run ruff check packages/ verification/` | flake8-logging plugin (LOG001..LOG015) for D-27 partial enforcement |
| ruff format | `uv run ruff format --check packages/ verification/` | |
| mypy strict | `uv run mypy --strict packages/` | tenacity ships `py.typed` — no new stubs |
| import-linter | `uv run lint-imports` | Phase 7 D-09 baseline; Plan 1 may add new forbidden contract for `_logging.py → client.py`/`aio.py` |
| logging.basicConfig grep | `! grep -rn 'logging\.basicConfig' packages/*/src/` | D-27 complement to ruff LOG015 (which only covers `logging.root.*`) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/<pkg>/ -x --no-header -q` (the package being modified)
- **After every plan wave:** Run `uv run pytest packages/ verification/ -q` + `uv run ruff check . && uv run mypy --strict packages/`
- **Before `/gsd-verify-work`:** Full suite + all static gates green (the Plan 6 green-gate is exactly this)
- **Max feedback latency:** ~15 seconds for quick, ~45 seconds for full

---

## Per-Task Verification Map

*Placeholder — populated by gsd-planner during Plan 1..6 task generation. Each task MUST have either an `<automated>` verify command or a Wave 0 dependency. Sampling continuity rule (no 3 consecutive tasks without automated verify) applies per plan.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 8-01-01 | 01 | 1 | RELY-01..03, LOG-01..02 | T-8-01 (Pitfall 4) | mutation gate proof: POST 503 → exactly 1 outgoing request | regression | `uv run pytest verification/test_retry_mutation_gate.py -q` | ❌ W0 | ⬜ pending |
| 8-01-02 | 01 | 1 | RELY-04 | T-8-02 (Pitfall 5) | 401 → re-auth chain (200 chain → 2 reqs; 401 chain → AuthError) | regression | `uv run pytest verification/test_retry_401_reauth.py -q` | ❌ W0 | ⬜ pending |
| 8-01-03 | 01 | 1 | LOG-01 | T-8-03 (Pitfall 6) | `logging.root.handlers` unchanged after import of all 4 packages | regression | `uv run pytest verification/test_logging_root_unchanged.py -q` | ❌ W0 | ⬜ pending |
| 8-01-04 | 01 | 1 | LOG-02 | T-8-04 (Pitfall 7) | caplog: SECRET literal does NOT appear in `record.getMessage()`/`args` cross-paquete | regression | `uv run pytest verification/test_logging_no_token_leak.py -q` | ❌ W0 | ⬜ pending |
| 8-01-05 | 01 | 1 | RELY-02 | T-8-05 (Pitfall 13) | 429 + Retry-After:600 → cap at 60s + retry | regression | `uv run pytest verification/test_retry_after_cap.py -q` | ❌ W0 | ⬜ pending |
| 8-01-06 | 01 | 1 | RELY-01 | T-8-06 (Pitfall 16) | asyncio.wait_for(client.get_X(), timeout=0.5) durante 503+503 → TimeoutError sin esperar retry completo | regression | `uv run pytest verification/test_async_cancellation.py -q` | ❌ W0 | ⬜ pending |
| 8-XX-XX | 2-5 | 2-5 | RELY-01..04, LOG-01..03 | per-package | per-package green | unit + regression | `uv run pytest packages/<pkg>/ verification/ -q` | ✅ partial | ⬜ pending |
| 8-06-01 | 06 | 6 | All | — | full CI matrix green Python 3.12 + 3.13 | green-gate | `uv run pytest packages/ verification/ -q && uv run ruff check . && uv run mypy --strict packages/ && uv run lint-imports` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Sampling continuity note:** Plan 1 lands 6 cross-cutting guard tests in `verification/` that initially FAIL red (the infra they test doesn't exist yet); Plans 2-5 turn them green one paquete at a time. This is intentional — Wave 0 is "tests RED → infra → tests GREEN" within Plan 1's commit, then each subsequent package plan keeps them green incrementally.

---

## Wave 0 Requirements

- [ ] `verification/test_retry_mutation_gate.py` — parametrized × 4 paquetes mutation gate proof
- [ ] `verification/test_retry_401_reauth.py` — parametrized × paquetes con auth (iol, higyrus, matriz Primary; ámbito skip; matriz Risk skip per D-23)
- [ ] `verification/test_retry_after_cap.py` — cross-cutting Retry-After cap behavior
- [ ] `verification/test_logging_root_unchanged.py` — cross-cutting root logger non-pollution
- [ ] `verification/test_logging_no_token_leak.py` — parametrized × 4 paquetes caplog redaction
- [ ] `verification/test_async_cancellation.py` — parametrized × paquetes con async (ambito, iol, higyrus; matriz skip per D-25)
- [ ] tenacity ≥9.1.0,<10 agregada a `[project] dependencies` de los 4 paquetes (`pyproject.toml`)
- [ ] (potencial) Plan 1 puede agregar nueva import-linter contract: `<pkg>._logging` forbids `<pkg>.client`, `<pkg>.aio` (defensive — D-09 Phase 7 ya cubre `_core.py`; aplicar el mismo pattern a `_logging.py` y `_transport.py`/`_atransport.py`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live verification que retries no introducen regresiones en `verification-cycle-2026-Q2` baseline | LIVE-01 (Phase 11) | Live targets requieren credenciales `.env` + horario de mercado + remarkets disponibilidad | Phase 11 corre `main_iol.py --live` etc. con baseline check. Phase 8 NO ejercita live — solo mocked. |
| Real-world retry behavior bajo backend transient flap (no mockeable cleanly) | RELY-01..02 | Backoff timing real es función de network + server load | Phase 11 / smoke test post-deploy |
| Log output legibility por dev/ops humano | LOG-03 | Subjective UX assessment | Manual review post-merge; consumer-side `logging.getLogger("<pkg>").setLevel(DEBUG)` y leer output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (6 cross-cutting guard test files + tenacity dep)
- [ ] No watch-mode flags (pytest run is single-shot)
- [ ] Feedback latency < 45s full suite
- [ ] `nyquist_compliant: true` set in frontmatter (post-plan-checker approval)

**Approval:** pending
