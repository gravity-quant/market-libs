---
phase: 01-safety-harness-verification-infrastructure
plan: 04
subsystem: verification-harness
tags: [pii-safety, anonymization, schema-snapshot, findings-template, tooling]
requires: []
provides:
  - "verification.schema.schema_of — snapshot de claves+tipos (PII-free por construcción, D-12)"
  - "verification.capture.capture — volcado de payload crudo al staging gitignored (HARN-06/D-11)"
  - "verification.anonymize.Denylist + anonymize — reemplazo de PII que preserva formato (HARN-06/D-10)"
  - "verification.findings.new_findings/write_findings — helper de plantilla de hallazgos (HARN-05)"
  - ".planning/verification/FINDINGS-TEMPLATE.md — plantilla documentada de hallazgos clasificados"
affects:
  - "Fases 2-5 copian FINDINGS-TEMPLATE.md por paquete y usan el pipeline capture→anonymize→fixture"
  - "Fase 2 (DRIFT-01) commitea el primer snapshot de schema_of"
tech-stack:
  added: []
  patterns:
    - "Módulo de raíz no publicable verification/ importado vía pythonpath=[\".\"] (Patrón 1)"
    - "Denylist como @dataclass(frozen=True, slots=True) siguiendo la convención de modelos"
    - "Recorrido recursivo dict/list/escalar (análogo a higyrus_client models._coerce)"
    - "Sólo stdlib (dataclasses, re, json, pathlib) — sin datos-falsos externos (A4)"
key-files:
  created:
    - verification/__init__.py
    - verification/schema.py
    - verification/capture.py
    - verification/anonymize.py
    - verification/findings.py
    - .planning/verification/FINDINGS-TEMPLATE.md
    - packages/ambito-financiero-client/tests/test_harness_schema.py
    - packages/ambito-financiero-client/tests/test_harness_anonymize.py
  modified:
    - .gitignore
    - pyproject.toml
decisions:
  - "pythonpath=[\".\"] en pyproject.toml para que los tests del harness importen el módulo verification/ de raíz (Rule 3 - blocking: --import-mode=importlib no agrega rootdir a sys.path sin un conftest de raíz)"
metrics:
  duration: ~12m
  completed: 2026-05-27
requirements: [HARN-05, HARN-06]
---

# Phase 01 Plan 04: Verification-Artifact Pipeline Summary

Pipeline de artefactos de verificación en un slice vertical — `schema_of` (snapshot claves+tipos PII-free), el pipeline de dos etapas `capture` (staging gitignored) → `anonymize` (reemplazo de PII que preserva formato), el helper/plantilla de hallazgos clasificados, y la entrada `.gitignore` que hace gitignored al staging crudo por construcción.

## What Was Built

**Task 1 — `schema_of` + `capture` + staging gitignored (D-12/D-11)** — commit `2d1443e`
- `verification/schema.py`: `schema_of(payload)` reduce cualquier payload a `{clave: nombre-de-tipo}` (dict ordenado), `[schema_of(primer)]`/`[]` (list), o el nombre del tipo (escalar). Nunca incluye valores → PII-free por construcción.
- `verification/capture.py`: `capture(pkg, endpoint, payload)` resuelve `.planning/verification/captures/` respecto de la ubicación del módulo (no del cwd), crea el dir con `mkdir(parents=True, exist_ok=True)`, escribe `<pkg>-<endpoint>.json` con `json.dumps(..., indent=2, ensure_ascii=False)` y devuelve la `Path`. No anonimiza (etapa separada).
- `.gitignore`: agrega `.planning/verification/captures/` — el payload crudo nunca es committeable por construcción.

**Task 2 — `anonymize` + `Denylist` + plantilla/writer de hallazgos (HARN-06/D-10, HARN-05/D-07/08/09)** — commit `6e4f95c`
- `verification/anonymize.py`: `Denylist` como `@dataclass(frozen=True, slots=True)` (`pkg`, `keys: frozenset[str]`, `replacements`); `anonymize(payload, deny)` recorre recursivamente y reemplaza sólo las CLAVES denylisted con `deny.replacements.get(k, _synthetic(k, v))`. `_synthetic` preserva forma (dígitos→0, letras→x para str; int→0; float→0.0; bool igual). Los valores no-PII relevantes para el formato (decimal AR `"1.415,00"`) se preservan verbatim. Sólo stdlib `re`.
- `verification/findings.py`: `new_findings(pkg)` y `write_findings(pkg)` rinden/escriben el esqueleto; exporta `FINDING_CLASSES` (7 clases) y `STATUS_LIFECYCLE`.
- `.planning/verification/FINDINGS-TEMPLATE.md`: plantilla documentada con encabezado ART (Timestamp ISO-8601, base URL/env resuelto, market-hours), tabla índice `ID | Class | Surface | Status`, las 7 clases fijas (SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT), el ciclo OPEN→CONFIRMED→FIXED + EXPECTED/NO-FIX (sin severidad), la convención `Regression: ... (issue #NNN)`, y el pipeline de dos etapas con revisión humana obligatoria.

## How It Was Verified

- `uv run pytest .../test_harness_schema.py .../test_harness_anonymize.py -q` → 9 passed.
- `uv run pytest -q` (repo completo) → 123 passed (sin regresiones del cambio de `pythonpath`).
- `git check-ignore .planning/verification/captures/probe.json` → imprime la ruta, exit 0.
- `grep -F SYNC-ASYNC-DRIFT FINDINGS-TEMPLATE.md` matchea; las 7 clases + tokens del ciclo (OPEN/CONFIRMED/FIXED/EXPECTED/NO-FIX) presentes.
- `grep -c -i faker verification/anonymize.py` → 0 (stdlib `re`, no Faker).
- `uv run ruff check verification` → All checks passed; `uv run ruff format --check verification` → limpio.
- `uv run mypy verification` → Success: no issues found in 5 source files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `verification/` no era importable desde los tests sin rootdir en sys.path**
- **Found during:** Task 1 (fase GREEN)
- **Issue:** Los tests del harness viven bajo `packages/<pkg>/tests/` e importan `from verification.schema import schema_of`. Con `--import-mode=importlib` y sin un `conftest.py` de raíz (que pertenece a otro plan de la misma wave, 01-02/03), pytest no agrega el rootdir del repo a `sys.path`, así que el import fallaba con `ModuleNotFoundError: No module named 'verification'`. La investigación (Patrón 1) había verificado el import sólo para los scripts `main_*.py` (script-dir en `sys.path[0]`), no para pytest.
- **Fix:** Agregué `pythonpath = ["."]` a `[tool.pytest.ini_options]` en `pyproject.toml` — el mecanismo idiomático de pytest para hacer importable un módulo de raíz. No depende de que exista el conftest de raíz (que llega en otro plan) y no rompe ningún otro test.
- **Files modified:** `pyproject.toml`
- **Commit:** `2d1443e`
- **Verification:** Todo el suite del repo pasa (123 tests), incluyendo los paquetes existentes — sin regresiones.

**2. [Rule 1 - Bug] Docstring mencionaba "Faker" y fallaba el criterio `grep -c -i faker == 0`**
- **Found during:** Task 2 (verificación)
- **Issue:** El docstring de `anonymize.py` decía "Faker queda explícitamente descartado (A4)", lo que hacía que `grep -c -i faker verification/anonymize.py` devolviera 1 en vez de 0 (criterio de aceptación de la fuente).
- **Fix:** Reescribí la frase a "sin dependencias de datos-falsos (A4)" — preserva la intención (Faker rechazado) sin el token literal.
- **Files modified:** `verification/anonymize.py`
- **Commit:** `6e4f95c`

## Threat Model Compliance

| Threat ID | Disposition | Status |
|-----------|-------------|--------|
| T-01-09 (raw payload → git) | mitigate | ✓ `captures/` en `.gitignore`, probado con `git check-ignore` |
| T-01-10 (anonymize + review gate) | mitigate | ✓ `Denylist` + plantilla documenta la revisión humana obligatoria |
| T-01-11 (schema snapshot PII-free) | mitigate | ✓ `schema_of` emite sólo claves+tipos, probado por unidad (ningún valor en el output) |
| T-01-12 (format preservation false-pass) | mitigate | ✓ decimal AR `"1.415,00"` preservado, probado por el test de no-PII |
| T-01-SC (package installs) | accept | ✓ sólo stdlib, sin instalaciones |

Sin threat flags nuevos: no se introdujo superficie de seguridad fuera del threat_model del plan.

## Known Stubs

Ninguno. El plan es infraestructura genérica: NO se commitea ningún snapshot de esquema real ni fixture en esta fase (D-12 — el primer snapshot se commitea en la Fase 2 / DRIFT-01). Esto es comportamiento intencional documentado en el plan, no un stub.

## TDD Gate Compliance

Ambas tareas son `tdd="true"`. Se siguió RED (test falla por `ModuleNotFoundError` con el módulo ausente) → GREEN (implementación mínima per RESEARCH verbatim, tests pasan). Por ser infra cohesiva de un slice vertical, cada tarea se commiteó como un único `feat` que incluye test + implementación juntos (el test demuestra la conducta). Los commits son `feat(...)`; no hubo fase REFACTOR separada necesaria.

## Self-Check: PASSED

Archivos creados verificados en disco:
- verification/schema.py, verification/capture.py, verification/anonymize.py, verification/findings.py, verification/__init__.py — FOUND
- .planning/verification/FINDINGS-TEMPLATE.md — FOUND
- packages/ambito-financiero-client/tests/test_harness_schema.py, test_harness_anonymize.py — FOUND

Commits verificados:
- 2d1443e (Task 1) — FOUND
- 6e4f95c (Task 2) — FOUND
