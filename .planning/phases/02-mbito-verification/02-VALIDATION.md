---
phase: 2
slug: mbito-verification
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-31
updated: 2026-06-01
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (asyncio_mode=auto) + pytest-httpx + mypy --strict + ruff |
| **Config file** | `pyproject.toml` (root) — pytest config / mypy config / ruff config |
| **Quick run command** | `uv run --package ambito-financiero-client pytest packages/ambito-financiero-client/tests` |
| **Full suite command** | `uv run --all-packages pytest && uv run mypy && uv run ruff check && uv run ruff format --check` |
| **Estimated runtime** | ~20 seconds (mocked suite + static checks) |

---

## Sampling Rate

- **After every task commit:** Run `uv run --package ambito-financiero-client pytest packages/ambito-financiero-client/tests` (~5s)
- **After every plan wave:** Run full suite (`pytest --all-packages` + `mypy` + `ruff check` + `ruff format --check`)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~20 seconds (mocked tests only; the live driver `main_ambito_financiero.py` is invoked manually and is intentionally OUT of the pytest suite per D-05)

---

## Per-Task Verification Map

Each AMB-01..06 and DRIFT-01 maps to at least one row. Task IDs use the `02-NN-T#.#` convention (PHASE-PLAN-TASK).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-T1.1 | 02-01 | 1 | DRIFT-01 | T-2-FIND-IDEMP | `append_finding(...)` is idempotent by `fid`; preserves human-promoted status (CONFIRMED/FIXED/EXPECTED/NO-FIX) across re-runs | unit (mocked) | `uv run --package ambito-financiero-client pytest packages/ambito-financiero-client/tests/test_findings_helper.py -v` | ✅ (file authored in this task) | ⬜ pending |
| 02-01-T1.2 | 02-01 | 1 | DRIFT-01 | T-2-BARREL | `verification.append_finding` importable via barrel re-export | unit (import smoke) | `uv run python -c "from verification import append_finding; print(append_finding.__doc__)"` | ✅ | ⬜ pending |
| 02-02-T2.1 | 02-02 | 2 | AMB-01, AMB-02, AMB-03, AMB-04, AMB-05, AMB-06, DRIFT-01 | T-2-DRIVER, T-2-ANTIBOT-IPBAN, T-2-DRIFT-OVERWRITE | Driver con 7 probes en orden D-13 (antibot último); exit 0 siempre (D-04); BAD_UA opt-in (D-12); one-shot anti-bot sin retry (D-14); schema snapshot no sobreescribe en drift (D-25); `safe_print(secrets=[])` uniforme (D-26) | static + import smoke | `uv run python -c "import main_ambito_financiero as m; assert all(hasattr(m, p) for p in ['probe_happy_sync','probe_happy_async','probe_parity_sync_async','probe_parse_decimal_adversarial','probe_no_data','probe_schema_snapshot','probe_antibot'])"` + `uv run mypy main_ambito_financiero.py` + `uv run ruff check main_ambito_financiero.py` + `uv run ruff format --check main_ambito_financiero.py` | ✅ (file rewritten in this task) | ⬜ pending |
| 02-03-T3.1 | 02-03 | 3 | AMB-01, AMB-02, AMB-03, AMB-04, AMB-05 | T-2-TESTS-DUAL | Tests mockeados invariantes D-08 en `test_client.py` y espejo en `test_async_client.py`; URL emitida con día > 12 (AMB-03); shape `list[list[str]]` + header `["Fecha","Compra","Venta"]` (AMB-01/AMB-05); `parse_ar_decimal("1.415,00") == 1415.0` (AMB-02); `AmbitoFinancieroNoDataError` cuando `len(rows) < 2` (AMB-04); paridad sync↔async para mismo payload (AMB-05) | unit (mocked) | `uv run --package ambito-financiero-client pytest packages/ambito-financiero-client/tests/test_client.py packages/ambito-financiero-client/tests/test_async_client.py -v` + `grep -c "# ------ Verified live (Phase 2) ------" packages/ambito-financiero-client/tests/test_client.py` (= 1) + idem `test_async_client.py` | ✅ (existing files appended) | ⬜ pending |
| 02-03-T3.2 | 02-03 | 3 | AMB-01, AMB-02, AMB-03, AMB-04, AMB-06 (opcional opt-in), DRIFT-01 | T-2-LIVE-RUN, T-2-IPBAN | Live run del driver: `PROBE ...: PASS/FAIL/SKIPPED/FINDING ... (...)` por probe + SUMMARY final; exit 0; schema snapshot creado en path D-19; findings markdown creado vía `write_findings`; humano inspecciona artefactos y promueve findings OPEN si corresponde | manual (driver run live) + automated (file existence) | `python main_ambito_financiero.py` + `test -f .planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` + `test -f .planning/verification/ambito-financiero-client-findings.md` | ❌ W0 (driver run produces these files for the first time) | ⬜ pending |
| 02-03-T3.3 | 02-03 | 3 | DRIFT-01 | T-2-DRIFT-COMMIT | Snapshot estructural JSON + findings markdown commiteados al repo; ART block refrescado con timestamp del run; archivo NO en gitignore de `.planning/verification/captures/` | static (git + file checks) | `git ls-files --error-unmatch .planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` + `git ls-files --error-unmatch .planning/verification/ambito-financiero-client-findings.md` + `git log -1 --pretty=format:%s .planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json \| grep -q -E '(02|baseline\|schema)'` | ✅ (committed in this task) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `verification/findings.py` — extender con `append_finding(...)` (D-10) — Task 02-01-T1.1
- [x] `verification/__init__.py` — re-exportar `append_finding` — Task 02-01-T1.2
- [x] `main_ambito_financiero.py` — re-escribir con los 7 probes (driver-only, D-05) — Task 02-02-T2.1
- [x] `packages/ambito-financiero-client/tests/test_client.py` — agregar sección `# ------ Verified live (Phase 2) ------` con invariantes D-08 — Task 02-03-T3.1
- [x] `packages/ambito-financiero-client/tests/test_async_client.py` — espejo async — Task 02-03-T3.1
- [x] `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` — primer snapshot (lo produce el primer run del driver, DRIFT-01) — Tasks 02-03-T3.2 + 02-03-T3.3
- [x] `.planning/verification/ambito-financiero-client-findings.md` — esqueleto + findings populated por el driver — Tasks 02-03-T3.2 + 02-03-T3.3

*Las casillas [x] indican que la dependencia está planeada en un task concreto. El estado real de creación/modificación se actualiza a `wave_0_complete: true` cuando ejecuta `/gsd-execute-phase 2`. Existing infrastructure (Phase 1: barrel `verification/`, root `conftest.py`, marker `live`, fixture `pytest-httpx` autouse) cubre todo lo demás sin necesidad de Wave 0.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Driver corre 7 probes contra `mercados.ambito.com` en vivo | AMB-01..06 (verificación en vivo) + DRIFT-01 (snapshot inicial) | Depende de servicio externo en vivo; salir del CI por riesgo de IP-ban y por D-05 (driver-only) | `python main_ambito_financiero.py` — esperar líneas `PROBE <name>: PASS/FAIL/SKIPPED/FINDING <fid> (<status>)` + summary + exit 0 |
| Anti-bot probe (UA inválido → 403) | AMB-06 | Opt-in D-12 + one-shot D-14 por riesgo de IP-ban; nunca corre por default | `VERIFY_ANTIBOT=1 python main_ambito_financiero.py` — esperar `PROBE antibot: PASS` (403 reproducido) o `FINDING F-NN (OPEN)` con `class=ANTI-BOT` |
| Re-run del driver con drift detection | DRIFT-01 | Requiere baseline previo committeado; comparación `schema_of` actual vs JSON committeado; NO sobreescribe sin gesto humano (D-25) | Cambiar deliberadamente la respuesta esperada del cliente (e.g., mock) o esperar drift natural; re-correr `python main_ambito_financiero.py`; esperar `FINDING F-NN: SHAPE OPEN` con `expected`/`actual` visibles + archivo committeado intacto |
| Triage humano de findings OPEN → CONFIRMED/EXPECTED/NO-FIX | DRIFT-01 (clasificación) + AMB-* (cierre de hallazgos) | Decisión semántica que requiere contexto humano; lifecycle D-08 (Phase 1) | Editar `.planning/verification/ambito-financiero-client-findings.md` y promover status manualmente; idempotencia de `append_finding` (Task 02-01-T1.1) preserva la promoción humana en runs sucesivos |
| Fix dual sync+async + 2 regression tests opportunistic | SC5 del ROADMAP — solo si aparece un CONFIRMED en el live run de Task 02-03-T3.2 | Bug discovery es estocástico; el plan MVP no asume que aparezca un bug. Si aparece, el flujo es: humano promueve a CONFIRMED → fix en `client.py` + `aio.py` → 2 regression tests en `test_client.py` + `test_async_client.py` con docstring `Regression: ... (finding F-NN)` (D-07) | Insertar un Plan 02-04 opportunistic (signal `holds-finding-X` del checkpoint 02-03-T3.2) o aplicar el fix manualmente y re-correr la suite completa antes del commit de T3.3 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify (T1.1, T1.2, T2.1, T3.1, T3.3) or Wave 0 dependencies (T3.2 es `checkpoint:human-verify` con `<human-check>` + 2 `<automated>` secundarios para file-existence)
- [x] Sampling continuity: ninguna secuencia de 3 tasks consecutivas sin `<automated>` (Wave 1: T1.1+T1.2 ambas auto; Wave 2: T2.1 auto; Wave 3: T3.1 auto, T3.2 checkpoint con automated secondaries, T3.3 auto)
- [x] Wave 0 cubre todas las referencias MISSING (driver creation, schema baseline, findings file esqueleto)
- [x] No watch-mode flags en ningún `<automated>` command
- [x] Feedback latency < 30s (mocked suite + mypy + ruff ~20s)
- [x] `nyquist_compliant: true` set in frontmatter (this revision, 2026-06-01)

**Approval:** approved 2026-06-01 (orchestrator post plan-checker iteration 1; BLOCKER de Dim 8 resuelto via Task ID concretos + sign-off completo + parity row para AMB-05 + threat refs por task)
