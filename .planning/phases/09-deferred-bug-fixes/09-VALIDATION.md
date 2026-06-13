---
phase: 9
slug: deferred-bug-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-13
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `09-RESEARCH.md` §"Validation Architecture" (lines 863–942).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.3+` + `pytest-asyncio 0.24+` (asyncio_mode=auto) + `pytest-httpx 0.34+` |
| **Config file** | Root `pyproject.toml` `[tool.pytest.ini_options]` (already present) |
| **Quick run command** | `uv run pytest packages/<pkg>/tests/<file>.py -x --no-header -q` |
| **Full suite command** | `uv run pytest --cov` (CI matrix: Python 3.12 + 3.13) |
| **Estimated runtime** | ~30 s per-package quick; ~90 s full suite (760 tests baseline post-Phase 8) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/<pkg>/tests/ -x --no-header -q` for the modified package only.
- **After every plan wave:** Run per-package full suite with coverage: `uv run pytest packages/<pkg>/tests/ --cov`.
- **Before `/gsd-verify-work` (Plan 09-04 green gate):** Full matrix + `ruff check` + `ruff format --check` + `mypy --strict` + `lint-imports` + cross-leak sentinel + public-surface zero-diff snapshot.
- **Max feedback latency:** ~30 s per-task; ~90 s full suite.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-* | 01 | 1 | BUG-03 | V2 / V3 (OAuth refresh + token lifecycle) | `state.refresh_token` preserved when server omits; rotated when server returns new; refresh→401 falls back to password without leaking IOLAuthError to caller | unit (sync mirror) | `uv run pytest packages/iol-client/tests/test_refresh_token_lifecycle.py -x` | ❌ W0 (Plan 09-01 creates) | ⬜ pending |
| 09-01-* | 01 | 1 | BUG-03 | V2 / V3 | Async mirror of 4 paths (token_lock double-checked locking respected) | unit (async mirror) | `uv run pytest packages/iol-client/tests/test_refresh_token_lifecycle_async.py -x` | ❌ W0 (Plan 09-01 creates) | ⬜ pending |
| 09-02-* | 02 | 1 | BUG-02 | V5 (input contract guard) | Happy-path mocked: server returns N cuentas → client returns N (contract guard prevents future client-side regression) | unit (mocked) | `uv run pytest packages/higyrus-client/tests/test_listado_cuentas_regression.py -x` *(only if bucket (c))* OR extend `test_client.py` | ⚠️ conditional W0 | ⬜ pending |
| 09-02-* | 02 | 1 | BUG-04 | V11 (cross-account isolation) | 2 mocked cuentas → 2 distinct wire requests with correct `id_cuenta` in path | unit (mocked, 2 cuentas) | `uv run pytest packages/higyrus-client/tests/test_multi_account.py -x` | ❌ W0 (Plan 09-02 creates) | ⬜ pending |
| 09-02-* | 02 | 1 | BUG-02 | — | Live triage: `main_higyrus.py` re-run with probe-scoped DEBUG logging; outcome bucket (a)/(b)/(c) recorded in finding `Resolution:` | manual (operator-driven live) | `uv run --package higyrus-client python main_higyrus.py` (driver) | N/A (manual) | ⬜ pending |
| 09-02-* | 02 | 1 | BUG-04 | V11 | Live: ≥2 cuentas iteradas via `probe_multi_account_iteration` con `HIGYRUS_SAMPLE_CUENTAS` env override | manual (operator-driven live, probe asserts) | `HIGYRUS_SAMPLE_CUENTAS=A,B uv run --package higyrus-client python main_higyrus.py` | N/A (manual, driver new probe) | ⬜ pending |
| 09-02-* | 02 | 1 | BUG-04 | — | Cross-package cleanup: `_state.account_id` removed in higyrus + iol; no references in code, tests, or docstrings | static (grep + tests pass) | `! rg -n "account_id" packages/{higyrus,iol}-client/src/*/_state.py` + per-package pytest | ✅ existing tests | ⬜ pending |
| 09-03-* | 03 | 2 | BUG-01 | V5 (input validation) / V7 (structured error) | Malformed CFI → `PrimaryAPIError(status="ERROR")` pre-HTTP; literal-known + regex forward-compat → pass | unit (10 parametric cases) | `uv run pytest packages/matriz-client/tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code -x` | ❌ W0 (Plan 09-03 extends `test_core.py`) | ⬜ pending |
| 09-03-* | 03 | 2 | BUG-01 | — | Live cycle_closure flip: `probe_error_malformed_cfi` (`main_matriz.py:1194`) flips FAIL → PASS post-fix | manual (operator-driven live) | `uv run --package matriz-client python main_matriz.py` + paste probe output | N/A (manual) | ⬜ pending |
| 09-04-* | 04 | 3 | BUG-01..04 | — | Green gate consolidation: full pytest matrix (3.12 + 3.13) + ruff + ruff format + mypy strict + lint-imports + cross-leak sentinel + public-surface snapshot zero-diff | suite + static | `uv run pytest --cov && uv run ruff check && uv run ruff format --check && uv run mypy --strict packages/ && uv run lint-imports` | ✅ existing infra | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

**Plan 09-01 — iol BUG-03:**
- [ ] `packages/iol-client/tests/test_refresh_token_lifecycle.py` — covers BUG-03 paths 1+2+3+4 (sync)
- [ ] `packages/iol-client/tests/test_refresh_token_lifecycle_async.py` — covers BUG-03 paths 1+2+3+4 (async mirror)

**Plan 09-02 — higyrus BUG-02 + BUG-04 + cross-pkg cleanup:**
- [ ] `packages/higyrus-client/tests/test_multi_account.py` — covers BUG-04 (2-cuenta mocked)
- [ ] (Conditional, bucket (c) only) `packages/higyrus-client/tests/test_listado_cuentas_regression.py` — covers BUG-02 client-side fix
- [ ] Driver probe added: `main_higyrus.py::probe_multi_account_iteration` with `HIGYRUS_SAMPLE_CUENTAS` env override
- [ ] `_state.account_id` removed in higyrus + iol (cross-package D-09 cleanup)

**Plan 09-03 — matriz BUG-01:**
- [ ] Extend `packages/matriz-client/tests/test_core.py` con `test_get_instruments_by_cfi_validates_cfi_code` (parametric, 10 cases: 4 valid + 6 malformed)

**Plan 09-04 — Green gate (no new files):**
- [ ] `.planning/phases/09-deferred-bug-fixes/09-VALIDATION.md` updated with CI evidence
- [ ] No code or test changes — validation-only

**Framework install:** None — pytest/pytest-asyncio/pytest-httpx already in `uv.lock` post-Phase 8.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| BUG-02 live triage: classify outcome bucket (a)/(b)/(c) | BUG-02 | Live API access required; outcome depends on session state and rate-limit conditions; mocked test cannot reproduce the original `[]` return | 1) `cd <repo>` 2) Ensure `.env` has `HIGYRUS_USER` + `HIGYRUS_PASS` 3) `uv run --package higyrus-client python main_higyrus.py` 4) Inspect `probe_get_listado_cuentas` outcome 5) Decide bucket per D-05; record `Resolution: <a\|b\|c> — <rationale>` in `higyrus-client-findings.md` |
| BUG-04 live multi-account iteration | BUG-04 | Live API access required to confirm ≥2 real accounts isolated correctly; mocked test cannot prove no server-side cross-account state | 1) Identify ≥2 known cuentas (from `get_listado_cuentas` or hardcoded) 2) `HIGYRUS_SAMPLE_CUENTAS="A,B" uv run --package higyrus-client python main_higyrus.py` 3) Confirm `probe_multi_account_iteration` reports PASS for both cuentas 4) Paste output to Plan 09-02 |
| BUG-01 cycle_closure flip | BUG-01 | Probe is in live driver; mutating gate not in scope to automate; operator manual run avoids side-effects | 1) Run `uv run --package matriz-client python main_matriz.py` 2) Confirm `probe_error_malformed_cfi` (line 1194) reports PASS 3) Confirm `cycle_closure_matriz_client` flips FAIL → PASS 4) Paste evidence to Plan 09-03 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify, manual verify, or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (manual gates are isolated to BUG-02 triage + BUG-04 live + BUG-01 cycle_closure flip)
- [ ] Wave 0 covers all MISSING references (4 new test files + 1 driver probe + 2 `_state.py` cleanups)
- [ ] No watch-mode flags
- [ ] Feedback latency < 90 s (full suite)
- [ ] `nyquist_compliant: true` set in frontmatter after green gate (Plan 09-04)

**Approval:** pending
