---
phase: 01
slug: safety-harness-verification-infrastructure
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-27
---

# Phase 01 — Validation Strategy

> Contrato de validación por fase, reconstruido retroactivamente desde los artefactos
> (PLAN/SUMMARY/VERIFICATION) tras completar la ejecución. Estado de entrada: B (no existía
> VALIDATION.md; 4 SUMMARY presentes).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (pytest-asyncio, pytest-httpx, pytest-cov) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`pythonpath=["."]`, `--import-mode=importlib`, `--strict-markers`, `--strict-config`, `testpaths=["packages"]`) |
| **Quick run command** | `uv run pytest packages/ambito-financiero-client/tests/test_harness_*.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~3–5 segundos (offline, sin red) |

El harness es tooling de raíz no publicable (`verification/`). Toda su batería de tests vive
junto al paquete neutral sin-auth `ambito-financiero-client` (bajo `testpaths=["packages"]`) y
corre 100% offline. El único test marcado `@pytest.mark.live` es el probe de ejemplo, deseleccionado
por defecto (mantiene el CI determinista — HARN-04).

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/ambito-financiero-client/tests/test_harness_*.py -q`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green (`157 passed, 1 deselected`)
- **Max feedback latency:** ~5 segundos

---

## Per-Task Verification Map

Mapa por requisito (HARN-01…06). Cada requisito de la fase tiene verificación automatizada.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| HARN-01 | 01-02, 01-03 | 1/2 | HARN-01 | T-01-07 | `require_env` devuelve bool, nunca `raise`/`sys.exit`; línea `SKIPPED <pkg>: missing X, Y` verbatim; runner agregado nunca se detiene | unit | `uv run pytest packages/ambito-financiero-client/tests/test_harness_env_gate.py packages/ambito-financiero-client/tests/test_harness_verify_runner.py -q` | ✅ | ✅ green |
| HARN-02 | 01-02, 01-03 | 1/2 | HARN-02 | T-01-05 / T-01-06 | Doble gate `VERIFY_MUTATING=1` AND hostname exacto `remarkets`; bypass con URL de prod falla safe | unit | `uv run pytest packages/ambito-financiero-client/tests/test_harness_mutation_gate.py -q` | ✅ | ✅ green |
| HARN-03 | 01-01, 01-03 | 1/2 | HARN-03 | T-01-01 / T-01-02 / T-01-03 | Valor completo nunca impreso; secretos ≥4 enmascarados; guarda de secreto vacío/corto; patrón Bearer enmascarado | unit | `uv run pytest packages/ambito-financiero-client/tests/test_harness_redaction.py -q` | ✅ | ✅ green |
| HARN-04 | 01-01 | 1 | HARN-04 | T-01-04 | `@pytest.mark.live` deseleccionado por defecto, seleccionado bajo `--live`; `--strict-markers` limpio (deselect ejercitado en cada corrida del suite) | unit (collection) | `uv run pytest packages/ambito-financiero-client/tests/test_harness_live_probe.py -q` (deselected) · `… --live -q` (passed) | ✅ | ✅ green |
| HARN-05 | 01-04 | 1 | HARN-05 | T-01-10 | Helper de hallazgos renderiza las 7 clases fijas + ciclo de 5 estados; `write_findings` respeta no-overwrite/overwrite | unit | `uv run pytest packages/ambito-financiero-client/tests/test_harness_findings.py -q` | ✅ (nuevo) | ✅ green |
| HARN-06 | 01-04 | 1 | HARN-06 | T-01-09 / T-01-11 / T-01-12 | `schema_of` PII-free (solo claves+tipos); `capture` escribe a staging gitignored; `anonymize` preserva formato y sanea subárboles PII | unit | `uv run pytest packages/ambito-financiero-client/tests/test_harness_schema.py packages/ambito-financiero-client/tests/test_harness_anonymize.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Inventario de tests del harness (offline):**

| Archivo | Tests | Requisito |
|---------|-------|-----------|
| `test_harness_env_gate.py` | 4 | HARN-01 |
| `test_harness_verify_runner.py` | 3 | HARN-01 |
| `test_harness_mutation_gate.py` | 5 | HARN-02 |
| `test_harness_redaction.py` | 8 | HARN-03 |
| `test_harness_live_probe.py` | 1 (live) | HARN-04 |
| `test_harness_findings.py` | 12 | HARN-05 ← **gap llenado en esta validación** |
| `test_harness_schema.py` | 4 | HARN-06 |
| `test_harness_anonymize.py` | 7 | HARN-06 |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. pytest ya estaba configurado (paquetes
preexistentes) y el split live/offline lo entregó el propio plan 01-01. El único faltante de
cobertura automatizada (HARN-05/`findings.py`) se cerró con `test_harness_findings.py`.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

> Nota: el contenido editorial de `.planning/verification/FINDINGS-TEMPLATE.md` (redacción de la
> plantilla) y la revisión humana obligatoria del pipeline `capture→anonymize→fixture` son por
> diseño juicios humanos; el *helper* programático (`findings.py`) y la mecánica del pipeline
> (`schema_of`/`capture`/`anonymize`) sí están cubiertos por tests automatizados.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (HARN-05 cerrado)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-27

---

## Validation Audit 2026-05-27

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

- **GAP-1 (HARN-05, MISSING → RESUELTO):** `verification/findings.py` estaba verificado solo por
  grep estático en VERIFICATION.md. Se añadió `packages/ambito-financiero-client/tests/test_harness_findings.py`
  (12 tests) cubriendo `FINDING_CLASSES` (7 clases en orden), `STATUS_LIFECYCLE` (5 estados),
  `new_findings()`, `findings_path()` y `write_findings()` (incl. no-overwrite/overwrite, con
  `_FINDINGS_DIR` monkeypatcheado a `tmp_path`). Suite: `145 → 157 passed`, 1 deselected, sin regresiones.
