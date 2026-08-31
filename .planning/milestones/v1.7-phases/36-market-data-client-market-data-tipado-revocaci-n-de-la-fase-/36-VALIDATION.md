---
phase: 36
slug: market-data-client-market-data-tipado-revocaci-n-de-la-fase
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-29
---

# Phase 36 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ con pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx, pytest-cov |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (raíz del monorepo) |
| **Quick run command** | `uv run pytest packages/market-data-client -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~1 segundo para `market-data-client` (663 tests medidos); workspace completo ~1810 tests |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/market-data-client -q` + `uv run ruff check packages/market-data-client main_market_data.py`
- **After every plan wave:** Run `uv run mypy` (src global) + `uv run mypy packages/market-data-client/tests` + `uv run python tools/check_decode_intactness.py`
- **Before `/gsd-verify-work`:** Full suite must be green — `uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run python tools/check_decode_intactness.py && uv run python tools/check_uniform_structure.py && uv run python tools/check_surface_types.py`, then `uv run pre-commit run --all-files`, then `uv run mypy` + per-package test loop, then `uv run pytest -q`
- **Max feedback latency:** ~1 segundo (quick command)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 36-01-01 | 01 | 0 | NOBJ-MD-01 | — | Cadena `snapshot.market_data.last.price` etc. no lanza con 4 payloads × 2 superficies (SC-1) | unit + integration | `uv run pytest packages/market-data-client/tests/test_market_data_chain.py -x` | ❌ W0 | ⬜ pending |
| 36-01-02 | 01 | — | NOBJ-MD-01 | — | Cadena compila bajo mypy strict (SC-1) | static | `uv run mypy packages/market-data-client/src packages/market-data-client/tests` | ✅ | ⬜ pending |
| 36-01-03 | 01 | — | NOBJ-MD-01 | — | `MarketDataEntries`/`BookLevel`/`EntryValue` con forma + 6 alias (SC-2) | unit | `uv run pytest packages/market-data-client/tests/test_models.py -k entries -x` | ✅ (extender) | ⬜ pending |
| 36-01-04 | 01 | — | NOBJ-MD-01 | — | Alias invisibles al walker; roster Null Object `>= 16` → 19 | unit (parametrizado) | `uv run pytest packages/market-data-client/tests/test_null_object.py -x` | ✅ | ⬜ pending |
| 36-02-01 | 02 | — | NOBJ-MD-02 | — | `entries`/`market_data` sin `None` en anotación (SC-2/SC-3) | unit (introspección de hints) | `uv run pytest packages/market-data-client/tests/test_models.py -k field_set -x` | ✅ (extender) | ⬜ pending |
| 36-02-02 | 02 | — | NOBJ-MD-02 | — | `LatestRequest.entries` default `[]`, `to_dict` omite clave vacía | unit | `uv run pytest packages/market-data-client/tests/test_models.py -k latest_request -x` | ✅ | ⬜ pending |
| 36-02-03 | 02 | — | NOBJ-MD-02 | — | Fila no-data: `bool(market_data) is False` + `note` poblado, sync/async, strict/no-strict (SC-4) | integration | `uv run pytest packages/market-data-client/tests/test_snapshot_no_data_row.py -x` | ✅ (migrar) | ⬜ pending |
| 36-02-04 | 02 | — | NOBJ-MD-02 | — | Wrong-type sigue divergiendo y fatal en strict | integration | `uv run pytest packages/market-data-client/tests/test_snapshot_no_data_row.py -k wrong_typed -x` | ✅ | ⬜ pending |
| 36-03-01 | 03 | 0 | NOBJ-MD-02 | — | Maquinaria de mapping ausente del paquete, aserción no vacua (SC-5) | unit (introspección negativa + positiva) | `uv run pytest packages/market-data-client/tests/test_models.py -k mapping_machinery -x` | ❌ W0 | ⬜ pending |
| 36-03-02 | 03 | — | NOBJ-MD-02 | — | Hash de `_decode.py` no se movió (SC-5) | gate de CI | `uv run python tools/check_decode_intactness.py` | ✅ | ⬜ pending |
| 36-03-03 | 03 | 0 | NOBJ-MD-02 | — | Driver consume por encadenamiento profundo en sitios reales (SC-5) | AST / grep | planner decide: AST reutilizando precedente 30-09, o assertion en el plan | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/market-data-client/tests/test_market_data_chain.py` — matriz de 4 payloads × 2 superficies de SC-1 (wire real de `get-market-data.json`, `market_data` ausente, `market_data: null`, `market_data: {}`); por caso: cadena no lanza, set de divergencias, `bool(market_data)`. Valores esperados medidos — ver RESEARCH.md F-1.
- [ ] `test_models.py -k mapping_machinery` — aserción de ausencia de maquinaria de mapping, emparejada con una aserción positiva (p. ej. `from_api` sigue inyectando `received_at`, roster `SafeModel` sigue en 19) para evitar un verde vacuo.
- [ ] Lock AST del driver para SC-5 (encadenamiento profundo en `main_market_data.py`) — reutilizar precedente 30-09 si el planner opta por AST.
- [ ] Helper `_strip_optional` módulo-local en `test_core.py` y `test_decode.py` (3 sitios) — prerequisito de las ediciones del censo de tests, no test propio.

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---

## Validation Audit 2026-08-31

Auditoría Nyquist retroactiva de la Phase 36, corrida a mano contra el árbol congelado de v1.7 según
el contrato `41-AUDIT-CONTRACT.md` (Phase 41, NYQ-01). Estado de entrada: `status: draft`,
`nyquist_compliant: false`, mapa con 11 filas sin disponer —de las cuales una shipeó **sin comando
declarado**— y tres celdas `File Exists` que afirman que el archivo de test no existe; **sin
subagente** — la auditoría lee y dispone, no repara (D-06a).

**Auditor:** Phase 41 (`/gsd-execute-phase 41`, plan 41-03) — auditoría de lectura y disposición
**Árbol auditado:** commit de `v1.7` `37a83fe693a303a551f4374f48fe6fc5521804f7`; HEAD de la sesión
de auditoría `6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5`; identidad probada con
`git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0 (diff vacío)

| Metric | Count |
|--------|-------|
| Filas auditadas (denominador) | 11 |
| VERIFIED-NOW | 11 |
| VERIFIED-HISTORICALLY | 0 |
| NOT-VERIFIABLE-RETROACTIVELY | 0 |
| Correcciones de comando | 1 (`comando redactado retroactivamente`, R-04) |
| Archivos de test nuevos escritos | 0 |
| Filas NOT ENFORCED en CI | 0 |
| Suite de re-ejecución de esta sesión | `711 passed in 1.09s` (`uv run pytest packages/market-data-client -q`) |

### Disposición por fila

| Row | Disposition | Evidence (this session) | CI enforcement surface |
|-----|-------------|-------------------------|------------------------|
| 36-r01 · 36-01-01 | VERIFIED-NOW | `uv run pytest packages/market-data-client/tests/test_market_data_chain.py -x` → `38 passed in 0.10s` (R-01) | job `test`, `ci.yml:133-166` (paso de tests en `ci.yml:154-160`; el archivo cae bajo el leg `market-data-client` de la matriz 6 paquetes × py3.12/3.13) |
| 36-r02 · 36-01-02 | VERIFIED-NOW | `uv run mypy packages/market-data-client/src packages/market-data-client/tests` → `Success: no issues found in 49 source files`, exit 0 (R-01) | job `typecheck`: el tramo `src` vía `uv run mypy` (src global), `ci.yml:122-123`; el tramo `tests` vía el bucle por paquete, `ci.yml:124-131` |
| 36-r03 · 36-01-03 | VERIFIED-NOW | `uv run pytest packages/market-data-client/tests/test_models.py -k entries -x` → `2 passed, 35 deselected in 0.01s` (deselect parcial, no total: §6.2 del contrato) (R-01) | job `test`, `ci.yml:133-166` |
| 36-r04 · 36-01-04 | VERIFIED-NOW | `uv run pytest packages/market-data-client/tests/test_null_object.py -x` → `61 passed in 0.04s` (R-01) | job `test`, `ci.yml:133-166` |
| 36-r05 · 36-02-01 | VERIFIED-NOW | `uv run pytest packages/market-data-client/tests/test_models.py -k field_set -x` → `1 passed, 36 deselected in 0.01s` (R-01) | job `test`, `ci.yml:133-166` |
| 36-r06 · 36-02-02 | VERIFIED-NOW | `uv run pytest packages/market-data-client/tests/test_models.py -k latest_request -x` → `3 passed, 34 deselected in 0.01s` (R-01) | job `test`, `ci.yml:133-166` |
| 36-r07 · 36-02-03 | VERIFIED-NOW | `uv run pytest packages/market-data-client/tests/test_snapshot_no_data_row.py -x` → `8 passed in 0.04s` (R-01) | job `test`, `ci.yml:133-166` |
| 36-r08 · 36-02-04 | VERIFIED-NOW | `uv run pytest packages/market-data-client/tests/test_snapshot_no_data_row.py -k wrong_typed -x` → `1 passed, 7 deselected in 0.01s` (R-01) | job `test`, `ci.yml:133-166` |
| 36-r09 · 36-03-01 | VERIFIED-NOW | `uv run pytest packages/market-data-client/tests/test_models.py -k mapping_machinery -x` → `1 passed, 36 deselected in 0.01s` (R-01) | job `test`, `ci.yml:133-166` |
| 36-r10 · 36-03-02 | VERIFIED-NOW | `uv run python tools/check_decode_intactness.py` → exit 0; Check A: `5 copies of _decode.py reduce to one normalized hash a1f00c824348164c, matching CANONICAL_DIGEST` (R-01) | job `lint`, `ci.yml:55` (step `decode-intactness`, Phase 29 DEC-01) |
| 36-r11 · 36-03-03 | VERIFIED-NOW (comando redactado retroactivamente) | **El mapa NO declaraba comando para esta fila.** Su celda `Automated Command` dice literalmente *"planner decide: AST reutilizando precedente 30-09, o assertion en el plan"* — una decisión de diseño pendiente, no un contrato de verificación. El comando de abajo **fue redactado por esta auditoría** (R-04); no estaba en el mapa y no debe leerse como si lo hubiera estado. Sustituto elegido: `verification/test_main_market_data_deep_chain.py`, cuyo **cuerpo fue leído** antes de disponer (no sólo su nombre, Assumptions Log A1): sus 6 tests parsean `main_market_data.py` por AST y assertan que las cuatro read probes existen por nombre, que cada una dereferencia `market_data.<alias>` sobre lo que fetcheó, que cada dereferencia vive dentro del `try` de la probe, un piso agregado de 36 accesos, un piso por probe (6/12/6/12) y que toda colección fetcheada está encadenada — es decir, exactamente la conducta SC-5 *"Driver consume por encadenamiento profundo en sitios reales"* que la fila declara, y no otra. Ejecutado: `uv run pytest verification/test_main_market_data_deep_chain.py -q` → `6 passed in 0.10s` | job `lint`, `ci.yml:81-92` (allowlist explícito de `verification/`; este archivo es el primero de los 12, `ci.yml:81`). Verificado: `grep -c 'verification/test_main_market_data_deep_chain.py' .github/workflows/ci.yml` → `1` |

*Disposiciones: `VERIFIED-NOW` = comando re-ejecutado en esta sesión, verde, con conteo distinto de
cero · `VERIFIED-HISTORICALLY` = artefacto fechado citado, no re-derivable ·
`NOT-VERIFIABLE-RETROACTIVELY` = requería red en vivo, ventana de mercado o checkpoint humano no
reproducible. Calificadores: `(comando corregido)` R-02 · `(ruta corregida)` R-03 ·
`(comando redactado retroactivamente)` R-04.*
