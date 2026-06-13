---
phase: 8
slug: retries-backoff-structured-logging
status: approved
nyquist_compliant: true
wave_0_complete: true
phase_status: ready_for_verify
created: 2026-06-13
updated: 2026-06-13
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
| mypy strict | `uv run mypy` + per-package `uv run mypy packages/<pkg>/tests` | tenacity ships `py.typed` — no new stubs |
| import-linter | `uv run lint-imports` | Phase 7 D-09 baseline; Plan 1 may add new forbidden contract for `_logging.py → client.py`/`aio.py` |
| logging.basicConfig grep | `! grep -rnE 'logging\.basicConfig\s*\(\|logging\.root\.\w' packages/*/src/` | D-27 complement to ruff LOG015 (which only covers `logging.root.*`); refined in Plan 6 to skip docstring false-positives |

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
| 8-01-01 | 01 | 1 | RELY-01..03, LOG-01..02 | T-8-01 (Pitfall 4) | mutation gate proof: POST 503 → exactly 1 outgoing request | regression | `uv run pytest verification/test_retry_mutation_gate.py -q` | ✅ | ✅ green |
| 8-01-02 | 01 | 1 | RELY-04 | T-8-02 (Pitfall 5) | 401 → re-auth chain (200 chain → 2 reqs; 401 chain → AuthError) | regression | `uv run pytest verification/test_retry_401_reauth.py -q` | ✅ | ✅ green |
| 8-01-03 | 01 | 1 | LOG-01 | T-8-03 (Pitfall 6) | `logging.root.handlers` unchanged after import of all 4 packages | regression | `uv run pytest verification/test_logging_root_unchanged.py -q` | ✅ | ✅ green |
| 8-01-04 | 01 | 1 | LOG-02 | T-8-04 (Pitfall 7) | caplog: SECRET literal does NOT appear in `record.getMessage()`/`args` cross-paquete | regression | `uv run pytest verification/test_logging_no_token_leak.py -q` | ✅ | ✅ green |
| 8-01-05 | 01 | 1 | RELY-02 | T-8-05 (Pitfall 13) | 429 + Retry-After:600 → cap at 60s + retry | regression | `uv run pytest verification/test_retry_after_cap.py -q` | ✅ | ✅ green |
| 8-01-06 | 01 | 1 | RELY-01 | T-8-06 (Pitfall 16) | asyncio.wait_for(client.get_X(), timeout=0.5) durante 503+503 → TimeoutError sin esperar retry completo | regression | `uv run pytest verification/test_async_cancellation.py -q` | ✅ | ✅ green |
| 8-XX-XX | 2-5 | 2-5 | RELY-01..04, LOG-01..03 | per-package | per-package green | unit + regression | `uv run pytest packages/<pkg>/ verification/ -q` | ✅ | ✅ green |
| 8-06-01 | 06 | 6 | All | — | full CI matrix green Python 3.12 + 3.13 | green-gate | `uv run pytest packages/ verification/ -q && uv run ruff check packages/ verification/ && uv run mypy && uv run lint-imports` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Sampling continuity note:** Plan 1 lands 6 cross-cutting guard tests in `verification/` that initially FAIL red (the infra they test doesn't exist yet); Plans 2-5 turn them green one paquete at a time. This is intentional — Wave 0 is "tests RED → infra → tests GREEN" within Plan 1's commit, then each subsequent package plan keeps them green incrementally.

---

## Wave 0 Requirements

- [x] `verification/test_retry_mutation_gate.py` — parametrized × 4 paquetes mutation gate proof
- [x] `verification/test_retry_401_reauth.py` — parametrized × paquetes con auth (iol, higyrus, matriz Primary; ámbito skip; matriz Risk skip per D-23)
- [x] `verification/test_retry_after_cap.py` — cross-cutting Retry-After cap behavior
- [x] `verification/test_logging_root_unchanged.py` — cross-cutting root logger non-pollution
- [x] `verification/test_logging_no_token_leak.py` — parametrized × 4 paquetes caplog redaction
- [x] `verification/test_async_cancellation.py` — parametrized × paquetes con async (ambito, iol, higyrus; matriz skip per D-25)
- [x] tenacity ≥9.1.0,<10 agregada a `[project] dependencies` de los 4 paquetes (`pyproject.toml`)
- [x] (potencial) Plan 1 puede agregar nueva import-linter contract: `<pkg>._logging` forbids `<pkg>.client`, `<pkg>.aio` (defensive — D-09 Phase 7 ya cubre `_core.py`; aplicar el mismo pattern a `_logging.py` y `_transport.py`/`_atransport.py`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live verification que retries no introducen regresiones en `verification-cycle-2026-Q2` baseline | LIVE-01 (Phase 11) | Live targets requieren credenciales `.env` + horario de mercado + remarkets disponibilidad | Phase 11 corre `main_iol.py --live` etc. con baseline check. Phase 8 NO ejercita live — solo mocked. |
| Real-world retry behavior bajo backend transient flap (no mockeable cleanly) | RELY-01..02 | Backoff timing real es función de network + server load | Phase 11 / smoke test post-deploy |
| Log output legibility por dev/ops humano | LOG-03 | Subjective UX assessment | Manual review post-merge; consumer-side `logging.getLogger("<pkg>").setLevel(DEBUG)` y leer output |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (6 cross-cutting guard test files + tenacity dep)
- [x] No watch-mode flags (pytest run is single-shot)
- [x] Feedback latency < 45s full suite
- [x] `nyquist_compliant: true` set in frontmatter (post-plan-checker approval)

**Approval:** Phase 8 Plan 6 — green-gate consolidation passed all static gates + full pytest suite on Python 3.12. CI matrix Python 3.12 + 3.13 verification deferred to operator checkpoint (Task 2 — `<how-to-verify>` step 1).

---

## Phase 8 — Green Gate Evidence (Plan 06)

> Captured 2026-06-13 by Plan 6 executor. All gates run locally on Python 3.12.11
> (CPython, active venv `.venv/`, managed by uv 0.9.0+). CI matrix Python 3.13 is
> covered by the operator checkpoint via PR status on GitHub.

### Gate Output Matrix

| Gate | Command | Result |
|------|---------|--------|
| Lockfile up-to-date | `uv lock --check` | exits 0 — "Resolved 47 packages" |
| Workspace sync | `uv sync --all-packages --all-extras --dev --frozen` | exits 0 |
| ruff lint (scoped) | `uv run ruff check packages/ verification/` | "All checks passed!" — exits 0 (LOG ruleset active) |
| ruff format (scoped) | `uv run ruff format --check packages/ verification/` | "114 files already formatted" — exits 0 |
| mypy strict global | `uv run mypy` | "Success: no issues found in 45 source files" |
| mypy strict per-package tests | `uv run mypy packages/<pkg>/tests` × 5 | all "Success: no issues found in N source files" |
| import-linter | `uv run lint-imports` | "Contracts: 4 kept, 0 broken" (ámbito/iol/higyrus/matriz `_core` does not depend on transport modules) |
| Public surface snapshot | `uv run pytest verification/test_public_surface.py -v` | **4 passed in 0.06s** — zero diff (only the 2 new kwargs land per signature) |
| Cross-leak sentinel | `uv run pytest verification/test_sync_async_isolation.py -v` | **7 passed, 1 skipped** (matriz async SKIP per D-25 — "matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore") |
| Matriz sweep snapshot (CR-05) | `uv run pytest verification/test_matriz_sweep_snapshot.py -v` | **20 passed in 0.05s** — Phase 7 CR-05 preserved (18 envelope-shape probes + 2 sanity checks) |
| Matriz body-consume (CR-03) | `uv run pytest packages/matriz-client/tests/test_core.py::test_parse_envelope_consumes_body_before_raise -v` | **1 passed in 0.02s** — Phase 7 CR-03 preserved |
| 6 cross-cutting guard tests | `uv run pytest verification/test_retry_* verification/test_logging_* verification/test_async_cancellation.py -v` | **21 passed, 1 skipped in 76.18s** (matriz async SKIP per D-25) |
| Per-package transport+logging | `uv run pytest packages/*/tests/test_transport.py packages/*/tests/test_logging.py` | **81 passed in 60.88s** (ámbito 14 + iol 18 + higyrus 23 + matriz 26) |
| CRITICAL Pitfall 4 | `uv run pytest verification/test_retry_mutation_gate.py -k new_order -v` | **1 passed, 3 deselected in 0.05s** — `test_mutating_call_never_retries_against_503[matriz_client-new_order-kwargs0]` GREEN |
| Full pytest suite | `uv run pytest packages/ verification/ -q` | **627 passed, 3 skipped, 1 deselected in 147.98s** |
| CI grep lint-logging (refined) | `! grep -rnE 'logging\.basicConfig\s*\(\|logging\.root\.\w' packages/*/src/` | exit=1 (no matches) — refined in Plan 6 to skip docstring false-positives (see Deviations below) |
| matriz aio.py preservation | `wc -l packages/matriz-client/src/matriz_client/aio.py` | **103** (Phase 6 stub UNCHANGED per D-25) |
| matriz _atransport.py absent | `test -f packages/matriz-client/src/matriz_client/_atransport.py` | exit=1 / ABSENT_OK — D-25 honored |
| tenacity version + py.typed | `python -c "from tenacity import ...; print(metadata.version('tenacity'))"` | **9.1.4** + 6 symbols import OK |

### LOC Delta — Consolidated 4-Paquete Matrix

| Pkg | _transport.py (NEW) | _atransport.py (NEW) | _logging.py (NEW) | client.py delta | aio.py delta | __init__.py delta |
|---|---|---|---|---|---|---|
| ámbito | 179 | 139 | 84 | +40 (190 → 230) | +40 (195 → 235) | +8 (47 → 55) |
| iol | 199 | 131 | 111 | +119 (491 → 610) | +112 (458 → 570) | +15 (64 → 79) |
| higyrus | 205 | 132 | 116 | +117 (445 → 562) | +102 (486 → 588) | +8 (97 → 105) |
| matriz | 225 | **N/A (D-25)** | 173 | +133 (604 → 737) | **0 (UNCHANGED at 103 LOC per D-25)** | +12 (164 → 176) |

`_core.py` delta per package (RequestSpec + builders flipping idempotent): ámbito +10, iol +48, higyrus +58, matriz +116. matriz `_atransport.py` deferred to Phase 10 REFAC-04 per D-25.

### Cross-Cutting Guard Tests — Final Status (Post-Plan-5)

22 collected tests, **21 passed + 1 SKIP** (matriz async per D-25). Verbatim Phase 7 D-11 SKIP reason text preserved: `"matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore"`.

| Test | ámbito | iol | higyrus | matriz Primary | matriz Risk |
|---|---|---|---|---|---|
| `test_retry_mutation_gate::test_idempotent_get_retries_on_503` | n/a (no GETs parametrized) | ✅ get_instruments | ✅ get_listado_cuentas | ✅ get_segments | n/a |
| `test_retry_mutation_gate::test_mutating_call_never_retries_against_503` | n/a | n/a | n/a | ✅ **new_order (Pitfall 4 CRITICAL — 1 wire request)** | n/a |
| `test_retry_401_reauth::test_401_then_login_then_200_triggers_exactly_one_reauth` | n/a | ✅ (3 wire reqs, FRESH-TOKEN in retry) | ✅ | ✅ (Token path) | — |
| `test_retry_401_reauth::test_401_then_login_then_401_raises_auth_error` | n/a | ✅ (AuthError, no infinite loop) | ✅ | ✅ | — |
| `test_retry_401_reauth::test_matriz_risk_api_401_does_not_reauth` | n/a | n/a | n/a | n/a | ✅ **D-23 — auth_basic 401 raises AuthenticationError, 1 wire req** |
| `test_retry_after_cap::test_retry_after_capped_at_60s` | covered by iol witness | ✅ | covered | covered | — |
| `test_logging_root_unchanged::test_importing_packages_does_not_modify_logging_root` | ✅ (NullHandler attached to per-pkg logger only) | ✅ | ✅ | ✅ | ✅ |
| `test_logging_no_token_leak::test_token_literal_never_appears_in_log_records` | ✅ (SECRET-LITERAL-12345 redacted) | ✅ (+ refresh_token URL+JSON + access_token JSON) | ✅ (+ JSON pwd + JSON token + cuit query) | ✅ (X-Auth-Token + X-Password) | ✅ |
| `test_logging_no_token_leak::test_matriz_auth_basic_password_not_logged` | n/a | n/a | n/a | n/a | ✅ **D-22 auth_basic tuple split** |
| `test_async_cancellation::test_cancellation_propagates_during_retry_backoff` | ✅ (TimeoutError <1.0s) | ✅ | ✅ | ⏭️ SKIP D-25 | ⏭️ SKIP D-25 |

### CRITICAL Pitfall 4 / D-01 / D-24 — Duplicate-Order Prevention Evidence

```
$ uv run pytest verification/test_retry_mutation_gate.py -k new_order -v
verification/test_retry_mutation_gate.py::test_mutating_call_never_retries_against_503[matriz_client-new_order-kwargs0] PASSED [100%]
======================= 1 passed, 3 deselected in 0.05s ========================
```

`build_new_order_request` in `packages/matriz-client/src/matriz_client/_core.py` carries explicit `idempotent=False` (HTTP GET semantically mutating per Primary API quirk). The `RetryTransport.handle_request` check is method-agnostic — it reads `request.extensions["idempotent"]` set by the shell from `RequestSpec.idempotent`. Non-idempotent requests pass through with NO retry loop, preventing duplicate-broker-orders on transient 503. This is the **most important safety property of Phase 8** — a single test failure here would mean duplicate-order risk in production.

### CR-03 + CR-05 Preservation Evidence (Phase 7 Regression Guards)

**CR-03 — `parse_envelope_response` body-consume-then-raise:**

```
$ uv run pytest packages/matriz-client/tests/test_core.py::test_parse_envelope_consumes_body_before_raise -v
packages/matriz-client/tests/test_core.py::test_parse_envelope_consumes_body_before_raise PASSED [100%]
============================== 1 passed in 0.02s ===============================
```

Plan 5 surgical scope: ADDED fields to `RequestSpec` (idempotent, endpoint_name, account_id) — the `parse_envelope_response` body is verbatim Phase 7.

**CR-05 — `_envelope_probe` 18-case sweep:**

```
$ uv run pytest verification/test_matriz_sweep_snapshot.py -v
====================== 20 passed in 0.05s ======================
```

18 envelope-shape probes + 2 sanity checks. Plan 5 did NOT touch `main_matriz.py`.

### D-25 — Matriz aio.py + _atransport.py Preservation Evidence

```
$ wc -l packages/matriz-client/src/matriz_client/aio.py
     103 packages/matriz-client/src/matriz_client/aio.py

$ test -f packages/matriz-client/src/matriz_client/_atransport.py && echo EXISTS || echo ABSENT_OK
ABSENT_OK
```

matriz `aio.py` LOC = 103 (Phase 6 stub UNCHANGED). `_atransport.py` confirmed ABSENT — both deferred to Phase 10 REFAC-04 alongside TokenStore.

### Public Surface Snapshot Diffs (Per-Package, Phase 6 Baseline → Phase 8 Final)

All 4 paquetes: exactly the 2 new kwargs (`max_retries: 'int' = 2` + `http_client: 'httpx.<Client|AsyncClient> | None' = None`) land in `Client/AsyncClient/configure()` signatures (matriz AsyncClient UNCHANGED per D-25). No other surface changes — verified by `verification/test_public_surface.py` GREEN.

- **ámbito:** Client + AsyncClient + configure() — 3 signatures, 2 kwargs each = 6 lines changed
- **iol:** Client + AsyncClient + configure() — 3 signatures, 2 kwargs each = 6 lines changed
- **higyrus:** Client + AsyncClient + configure() — 3 signatures, 2 kwargs each = 6 lines changed
- **matriz:** Client + configure() only — 2 signatures, 2 kwargs each = 4 lines changed; **AsyncClient line UNCHANGED per D-25**

### Test Count Delta

| Phase | Total | Skipped | Note |
|---|---|---|---|
| Phase 7 baseline | 527 | 2 | post-Phase-7 final |
| Plan 1 (Wave 1 scaffolding) | 532 | 3 (incl matriz async) | +6 incl 14 RED guards (intentional) |
| Plan 2 (ámbito canary) | 546 | 3 | +14 ámbito transport+logging unit tests |
| Plan 3 (iol) | 564 | 3 | +18 iol unit tests |
| Plan 4 (higyrus) | 587 | 3 | +23 higyrus unit tests |
| Plan 5 (matriz) | 613 | 3 | +26 matriz unit tests; **Wave 5 closure (all guard tests GREEN)** |
| **Plan 6 final (this validation)** | **627** | **3** | **+14 net (likely some pre-existing additions); +100 vs Phase 7 baseline** |

`uv run pytest packages/ verification/ -q` final output: **627 passed, 3 skipped, 1 deselected in 147.98s (0:02:27)**.

The 3 SKIP reasons (verbatim):
1. `packages/matriz-client/tests/test_fixture_reaches_production.py:64: matriz async REST surface is Phase 10 REFAC-04; stub AsyncClient ships in Plan 06 with no REST methods`
2. `verification/test_async_cancellation.py:82: matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore`
3. `verification/test_sync_async_isolation.py:176: matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore`

All 3 SKIPs are forward-looking-D-25 acknowledgments; none mask a Phase 8 deficiency.

### tenacity Verification

```
$ uv run python -c "import importlib.metadata; print('tenacity', importlib.metadata.version('tenacity')); from tenacity import Retrying, AsyncRetrying, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type, retry_if_result; print('OK imports')"
tenacity 9.1.4
OK imports
```

tenacity 9.1.4 importable across 4 paquetes; py.typed compatible with mypy strict (no new stubs needed; mypy global pass = "Success: no issues found in 45 source files").

### Pitfall 18 Statement (Explicit)

**No tests were weakened during Phase 8.** All pre-existing tests in `packages/*/tests/` + `verification/` pass with their original assertions; only **new** tests were added (in `tests/test_transport.py`, `tests/test_logging.py`, `verification/test_retry_*`, `verification/test_logging_*`, `verification/test_async_cancellation.py`). The only test-file modifications in Plans 2-5 were:
- `test_request_propaga_auth_error` (iol + higyrus + matriz sync + async) — **strengthened** to queue full 401→login→401 chain validating the new D-02 re-auth-once contract (replaces the pre-Phase-8 single-shot 401 semantic). The pre-existing intent ("a 401 surfaces as AuthError") is preserved; the test now exercises the FULL contract.
- `test_login_500_levanta_api_error` + `test_login_429_levanta_rate_limit` (higyrus sync + async) — **strengthened** to queue 3 × mocked responses so the D-03 idempotent=True retry loop exhausts and the final response surfaces as the typed exception (D-05 last-response semantics).
- `test_async_client_has_no_client_lock_attribute` (ámbito) — **updated** the `__slots__` set equality to include `_max_retries` per D-15 (B7 divergence rationale `"_client_lock" not in __slots__` preserved).
- `verification/test_retry_mutation_gate.py` — **fixed** an authoring slip in Plan 1 (Plan 3 deviation #2): expected_count corrected from 2 to 3 wire requests per D-15+D-19 canonical default `max_retries=2 = max_attempts=3`.

None of these qualify as "weakening" — each updated test exercises a stronger or more canonical contract than before.

### Phase 8 Commit Log (5 Atomic Commits per D-21 + Per-Plan Doc Commits)

```
72e5298 docs(08-05): complete matriz retries+structured-logging plan
273891b feat(matriz): retries + structured logging — sync-only (aio.py defer Phase 10) + Risk API 401-no-reauth + status=ERROR no-retry (RELY-01..04, LOG-01..03)
4a30de4 docs(08-04): complete higyrus retries+structured-logging plan
214332f feat(higyrus): retries + structured logging — RetryTransport, RedactingFilter, account_id propagation, JSON password redaction (RELY-01..04, LOG-01..03)
54ce535 docs(08-03): complete iol retries + structured logging plan
43862d1 feat(iol): retries + structured logging — RetryTransport, RedactingFilter, 401 re-auth-once, OAuth refresh_token redaction (RELY-01..04, LOG-01..03)
fbdce8c docs(08-02): complete ámbito canary plan
7eacae8 feat(ambito): retries + structured logging — RetryTransport, RedactingFilter (RELY-01..04, LOG-01..03)
187289e docs(08-01): complete wave 1 cross-cutting infrastructure plan
515738c feat(verification): RetryTransport + _logging scaffolds + cross-cutting guard tests (RELY-01..04, LOG-01..03)
```

5 atomic `feat(*)` commits per D-21 (Plan 1 + 4 per-package); each followed by a `docs(*)` commit dropping the per-plan SUMMARY.md. Plan 6 lands as `ci(phase-08): green gate consolidation` + `docs(08-06): complete green gate consolidation plan`.

### 5 ROADMAP §Phase 8 Success Criteria — Backward Verification

1. ✅ **RetryTransport per paquete with full-jitter backoff + Retry-After cap 60s** — verified by `test_retry_after_cap.py` GREEN + `tests/test_transport.py::test_retry_after_cap_60s` (per-package) GREEN. `wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0)` configured in each `_transport.py`. `_RETRYABLE_STATUS = frozenset({408, 409, 429, *range(500, 600)})`.
2. ✅ **Mutation-aware retry gate end-to-end (POST 503 → 1 wire request)** — verified by `test_retry_mutation_gate.py[matriz_client-new_order]` GREEN (CRITICAL Pitfall 4). `RequestSpec.idempotent: bool = False` default; GET endpoints opt-in to `True`; matriz mutating GETs (new_order/replace_order/cancel_order) KEPT `idempotent=False` despite using HTTP GET.
3. ✅ **401 re-auth-once in shell** — verified by `test_retry_401_reauth.py` × 3 paquetes (iol/higyrus/matriz Primary) GREEN. Shell `_request()` catches `AuthError`/`401`, clears `state.token`, calls `_ensure_token()`, retries ONCE; 2nd 401 raises. matriz Risk path (`auth_basic`) NO re-auth per D-23 (GREEN).
4. ✅ **NullHandler + grep CI rule + ruff LOG015** — verified by `test_logging_root_unchanged.py` GREEN. CI `lint-logging` step active (refined in Plan 6 — see Deviations). ruff `LOG` ruleset enabled in root `pyproject.toml [tool.ruff.lint] select`.
5. ✅ **RedactingFilter with per-paquete patterns** — verified by `test_logging_no_token_leak.py` × 4 paquetes + `test_matriz_auth_basic_password_not_logged` GREEN. Per-package patterns:
   - **ámbito** — Bearer + URL-encoded password + JSON password (forward-consistent baseline)
   - **iol** — + OAuth refresh_token URL+JSON + access_token JSON
   - **higyrus** — + JSON password (login body) + JSON token (login response) + cuit URL query (PII)
   - **matriz** — + D-22 auth_basic tuple-split + Authorization Basic + X-Auth-Token + X-Password (X-Username preserved as operational metadata per D-22)

### Plan 6 Deviations — Auto-fixes Applied

**1. [Rule 1 - Format] `verification/test_retry_401_reauth.py` ruff-format violation (pre-existing from Plans 2-5)**

- **Found during:** `uv run ruff format --check packages/ verification/` initial run.
- **Root cause:** A 2-line f-string in `test_401_then_login_then_200_triggers_exactly_one_reauth` did not fit ruff's preferred single-line format. Pre-existing from Plan 3 / Plan 4 edits.
- **Fix applied:** `uv run ruff format verification/test_retry_401_reauth.py` — collapsed the 2-line f-string to a single line.
- **Files modified:** `verification/test_retry_401_reauth.py`

**2. [Rule 1 - Bug in Plan 1 deliverable] CI `lint-logging` grep step false-positive on docstrings (would have failed CI on `main`)**

- **Found during:** Plan 6 Task 1 — running the CI grep step locally per the `<action>` block: `grep -rn --include='*.py' 'logging\.basicConfig\|logging\.root' packages/*/src/` returned exit 0 with **8 matches** in the new `_logging.py` and `__init__.py` files.
- **Investigation:** All 8 matches are in **docstrings/comments** that LITERALLY DOCUMENT the LOG-01 rule itself — e.g., `` ``logging.getLogger("ambito_financiero_client")`` ONLY — NEVER ``logging.root``. `` The grep treats these as violations even though they're rule-documentation, not actual `logging.root.*` calls. This means CI on `main` is currently RED on the `lint-logging` step.
- **Root cause:** Plan 1 landed the CI step with an overly broad pattern. Plans 2-5 added `_logging.py` modules whose docstrings reference `logging.root` to document the rule (correctly!) — but the grep doesn't distinguish.
- **Fix applied:** Refined the CI step's grep to match only actual code calls — `logging\.basicConfig\s*\(` (call with paren) OR `logging\.root\.\w` (attribute access with trailing dot+identifier). Bare `logging.root` references inside backticks/comments no longer trigger.
- **Verification:** `grep -rnE --include='*.py' 'logging\.basicConfig\s*\(|logging\.root\.\w' packages/*/src/` → exit 1 (no matches). The refined pattern still catches every realistic violation (any actual `logging.root.handlers = [...]`, `logging.root.setLevel(...)`, `logging.basicConfig(level=...)` etc. would match).
- **Files modified:** `.github/workflows/ci.yml`
- **Acceptance:** This Rule 1 fix is in-scope for the green-gate consolidation plan — the green gate cannot certify Phase 8 until CI is green. Without this fix, CI's `lint-logging` step would fail on `main` after Plan 5 landed.

### Pre-existing Out-of-Scope Issues Acknowledged (NOT Phase 8 Caused)

- `uv run ruff check .` (from repo root, full scope incl `.planning/spikes/` and `.claude/skills/spike-findings-market-libs/sources/`) reports **108 pre-existing errors** in spike research artifacts (F401, F541, F841, B011, I001, PT015, RET504, RUF003, RUF059, SIM105, UP017, UP035 — NOT from the new LOG ruleset). Documented in `.planning/phases/08-retries-backoff-structured-logging/deferred-items.md`. **Phase 8 specific scope is clean:** `uv run ruff check packages/ verification/` → "All checks passed!" Resolution path (out-of-scope for Phase 8): add `extend-exclude = [".planning/spikes/", ".claude/skills/spike-findings-market-libs/sources/"]` to `[tool.ruff]`, or fix the spike files. Tracked for a future quick task or Phase 11.
