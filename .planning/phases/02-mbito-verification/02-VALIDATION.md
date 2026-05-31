---
phase: 2
slug: mbito-verification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-31
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

Filled by the planner from PLAN.md task IDs. Rows are placeholders — the planner replaces them with concrete tasks. Each AMB-01..06 and DRIFT-01 must appear in at least one row.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-XX-YY | XX | N | AMB-01 | — | `get_dollar_banco_nacion` retorna `list[list[str]]` con header `["Fecha","Compra","Venta"]` | unit (mocked) | `uv run --package ambito-financiero-client pytest packages/ambito-financiero-client/tests/test_client.py -k verified_live` | ✅ | ⬜ pending |
| 02-XX-YY | XX | N | AMB-02 | — | `parse_ar_decimal("1.415,00") == 1415.0`; rango plausible 100..100000 | unit (mocked) | `uv run --package ambito-financiero-client pytest packages/ambito-financiero-client/tests/test_client.py -k parse_decimal` | ✅ | ⬜ pending |
| 02-XX-YY | XX | N | AMB-03 | — | URL emitida `/dolarnacion/historico-general/YYYY-MM-DD/YYYY-MM-DD` con día > 12 | unit (mocked) | `uv run --package ambito-financiero-client pytest packages/ambito-financiero-client/tests/test_client.py -k url_emission` | ✅ | ⬜ pending |
| 02-XX-YY | XX | N | AMB-04 | — | `get_dollar_banco_nacion` levanta `AmbitoFinancieroNoDataError` cuando `len(rows) < 2` | unit (mocked) | `uv run --package ambito-financiero-client pytest packages/ambito-financiero-client/tests/test_client.py -k no_data` | ✅ | ⬜ pending |
| 02-XX-YY | XX | N | AMB-05 | — | Paridad estructural sync↔async para `get_dollar_banco_nacion` | manual (driver) + unit (mocked invariant) | `python main_ambito_financiero.py` + `uv run --package ambito-financiero-client pytest -k parity` | ✅ | ⬜ pending |
| 02-XX-YY | XX | N | AMB-06 | — | UA hardcodeado de browser pasa el anti-bot; UA default httpx reproduce 403 (opt-in `VERIFY_ANTIBOT=1`, one-shot) | manual (driver, live, gated) | `VERIFY_ANTIBOT=1 python main_ambito_financiero.py` | ❌ W0 (driver re-write) | ⬜ pending |
| 02-XX-YY | XX | N | DRIFT-01 | — | `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` committeado y diff-detection en re-runs | manual (driver writes/compares) + static (file exists) | `test -f .planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` | ❌ W0 (first run produces) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `verification/findings.py` — extender con `append_finding(...)` (D-10) + re-exportar vía `verification/__init__.py`
- [ ] `main_ambito_financiero.py` — re-escribir con los 7 probes (driver-only, D-05); no entra al pytest suite
- [ ] `packages/ambito-financiero-client/tests/test_client.py` — agregar sección `# ------ Verified live (Phase 2) ------` con invariantes D-08 mockeados
- [ ] `packages/ambito-financiero-client/tests/test_async_client.py` — espejo async de los invariantes nuevos
- [ ] `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` — primer snapshot, lo produce el primer run del driver (DRIFT-01)

*Existing infrastructure (Phase 1: `verification/` barrel, conftest.py root, `--live` marker, `pytest-httpx` fixture autouse) cubre todo lo demás.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Driver corre 7 probes contra `mercados.ambito.com` en vivo | AMB-01..06 (verificación en vivo) + DRIFT-01 (snapshot inicial) | Depende de servicio externo en vivo; salir del CI por riesgo de IP-ban y por D-05 (driver-only) | `python main_ambito_financiero.py` — esperar líneas `PROBE <name>: PASS/FAIL/SKIPPED/FINDING <fid> (<status>)` + summary + exit 0 |
| Anti-bot probe (UA inválido → 403) | AMB-06 | Opt-in D-12 + one-shot D-14 por riesgo de IP-ban; nunca corre por default | `VERIFY_ANTIBOT=1 python main_ambito_financiero.py` — esperar `PROBE antibot: PASS` (403 reproducido) o finding `EXPECTED ANTI-BOT` |
| Re-run del driver con drift detection | DRIFT-01 | Requiere baseline previo committeado; comparación schema vs JSON committeado; NO sobreescribe sin gesto humano (D-25) | Editar la respuesta esperada del cliente o el cliente mismo; re-correr el driver; esperar `FINDING F-NN: SHAPE OPEN` con expected/actual visibles |
| Triage humano de findings OPEN → CONFIRMED/EXPECTED/NO-FIX | DRIFT-01 (clasificación) | Decisión semántica que requiere contexto humano; lifecycle D-08 (Phase 1) | Editar `.planning/verification/ambito-financiero-client-findings.md` y promover status manualmente; idempotencia de `append_finding` preserva la promoción en runs sucesivos |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify (pytest mocked) or Wave 0 dependencies (driver creation, schema snapshot creation)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (driver, schema baseline)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (mocked suite + mypy + ruff)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
