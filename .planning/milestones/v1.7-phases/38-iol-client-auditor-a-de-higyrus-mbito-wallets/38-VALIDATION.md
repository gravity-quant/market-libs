---
phase: 38
slug: iol-client-auditor-a-de-higyrus-mbito-wallets
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-29
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` >= 8.3 with `pytest-asyncio` (`asyncio_mode = "auto"`), `pytest-httpx` >= 0.34 |
| **Config file** | root `pyproject.toml`, `[tool.pytest.ini_options]` (`--import-mode=importlib`, `--strict-markers`, `pythonpath = ["."]`) |
| **Quick run command** | `uv run --package iol-client pytest packages/iol-client -q` |
| **Full suite command** | `uv run --package iol-client pytest packages/iol-client -q && uv run --package higyrus-client pytest packages/higyrus-client -q && uv run --package ambito-financiero-client pytest packages/ambito-financiero-client -q && uv run --package wallets-client pytest packages/wallets-client -q && uv run python tools/check_decode_intactness.py && uv run python tools/check_uniform_structure.py && uv run python tools/check_surface_types.py && uv run mypy packages/iol-client && uv run ruff check packages/iol-client` |
| **Estimated runtime** | ~15s quick / ~90s full suite |

---

## Sampling Rate

- **After every task commit:** Run `uv run --package iol-client pytest packages/iol-client -q` (or the affected package's leg) + `uv run ruff check <touched paths>`
- **After every plan wave:** Run all four package suites + the three `tools/` gates + `uv run mypy packages/iol-client`
- **Before `/gsd-verify-work`:** Full suite must be green — 289 / 289 / 208+1 / 10 as the floor (any decrease is a regression, an increase is expected from the new RED test)
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 38-01-01 | 01 | 0 | NOBJ-AUD-01 | — | N/A | unit (RED fixture) | `pytest packages/iol-client/tests/test_surface_types_red.py -k optional_model_field -q` | ❌ W0 | ⬜ pending |
| 38-01-02 | 01 | 0 | NOBJ-AUD-01 | — | N/A | unit (RED fixture) | `pytest packages/iol-client/tests/test_surface_types_red.py -k optional_literal_alias -q` | ❌ W0 | ⬜ pending |
| 38-02-01 | 02 | 1 | NOBJ-IOL-01 | — | N/A | unit | `pytest packages/iol-client/tests/test_models.py -k puntas -q` | ✅ | ⬜ pending |
| 38-02-02 | 02 | 1 | NOBJ-IOL-01 | — | N/A | unit | `pytest packages/iol-client/tests/test_models.py -k round_trip -q` | ✅ | ⬜ pending |
| 38-03-01 | 03 | 2 | NOBJ-IOL-01 | — | N/A | static | `uv run mypy packages/iol-client` | ✅ | ⬜ pending |
| 38-03-02 | 03 | 2 | NOBJ-IOL-01 | — | N/A | snapshot | `uv run python verification/regen_snapshots.py && git diff --stat verification/snapshots/iol-client-surface.txt` | ✅ | ⬜ pending |
| 38-04-01 | 04 | 2 | NOBJ-AUD-01 | — | N/A | unit | `pytest packages/matriz-client/tests/test_surface_types_red.py -q` (read-only regression check) | ✅ | ⬜ pending |
| 38-05-01 | 05 | 3 | NOBJ-AUD-01 | — | N/A | doc review | `checkpoint:human-verify` on `38-CENSUS.md` | ❌ manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/iol-client/tests/test_surface_types_red.py` — add `test_an_optional_model_field_is_caught` (covers NOBJ-AUD-01 D-11 lower bound)
- [ ] `packages/iol-client/tests/test_surface_types_red.py` — add `test_an_optional_literal_alias_field_is_spared` (covers the D-01b narrowness corollary — must NOT reflag the 10 matriz `Literal | None` leaves)
- [ ] No framework install needed; no `conftest.py` changes needed

`tdd_mode` is enabled: the 7 migrated assertions in `test_models.py` (D-04, plus the round-trip assertion found in research) are themselves the RED step for the source change — write them before flipping the `puntas` annotations and confirm they fail for the stated reason, not by collection error.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `38-CENSUS.md` has zero rows without a disposition | NOBJ-AUD-01 | Census completeness (SC-2) is a documentation contract, not an executable assertion | Read `38-CENSUS.md`, confirm every row (higyrus/ámbito/wallets) has a disposition value; confirm zero-violation packages are enumerated, not omitted |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---

## Validation Audit 2026-08-31

Auditoría Nyquist retroactiva de la Phase 38, corrida a mano contra el árbol congelado de v1.7 según
el contrato `41-AUDIT-CONTRACT.md` (Phase 41, NYQ-01). Estado de entrada: `status: draft`,
`nyquist_compliant: false`, 9 filas sin disponer —8 del mapa por tarea más 1 de
`## Manual-Only Verifications`, de las cuales **dos son revisión de un documento** y una **muta el
árbol de trabajo**—; **sin subagente** — la auditoría lee y dispone, no repara (D-06a).

**Auditor:** Phase 41 (`/gsd-execute-phase 41`, plan 41-05) — auditoría de lectura y disposición
**Árbol auditado:** commit de `v1.7` `37a83fe693a303a551f4374f48fe6fc5521804f7`; HEAD de la sesión
de auditoría `6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5`; identidad probada con
`git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0 (diff vacío)

| Metric | Count |
|--------|-------|
| Filas auditadas (denominador) | 9 |
| VERIFIED-NOW | 7 |
| VERIFIED-HISTORICALLY | 2 |
| NOT-VERIFIABLE-RETROACTIVELY | 0 |
| Correcciones de comando | 0 |
| Archivos de test nuevos escritos | 0 |
| Filas NOT ENFORCED en CI | 3 |
| Suite de re-ejecución de esta sesión | `311 passed in 13.91s` (`uv run pytest packages/iol-client -q`) |

**Nota de clave:** el denominador de esta fase es **9 = 8 filas de mapa + 1 fila manual-only**
(§2.1 del contrato). Las 8 filas del mapa reciben `38-r01`..`38-r08` en su orden de aparición y la
única fila de `## Manual-Only Verifications` recibe `38-m01` (§2.3). Los Task ID de este mapa **sí**
son únicos —a diferencia de los de la Phase 37—, pero la clave ordinal se aplica igual para que las
cinco tablas de disposición de la Phase 41 sean sumables con el mismo patrón.

### Disposición por fila

| Row | Disposition | Evidence (this session) | CI enforcement surface |
|-----|-------------|-------------------------|------------------------|
| 38-r01 · 38-01-01 | VERIFIED-NOW | `uv run pytest packages/iol-client/tests/test_surface_types_red.py -k optional_model_field -q` → `1 passed, 15 deselected in 0.01s`, exit 0 — deselect parcial, no total (§6.2) (R-01) | job `test`, `ci.yml:133-166` (paso de tests en `ci.yml:154-160`; leg `iol-client` de la matriz 6 paquetes × py3.12/3.13) |
| 38-r02 · 38-01-02 | VERIFIED-NOW | `uv run pytest packages/iol-client/tests/test_surface_types_red.py -k optional_literal_alias -q` → `1 passed, 15 deselected in 0.01s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 38-r03 · 38-02-01 | VERIFIED-NOW | `uv run pytest packages/iol-client/tests/test_models.py -k puntas -q` → `5 passed, 21 deselected in 0.01s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 38-r04 · 38-02-02 | VERIFIED-NOW | `uv run pytest packages/iol-client/tests/test_models.py -k round_trip -q` → `4 passed, 22 deselected in 0.01s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 38-r05 · 38-03-01 | VERIFIED-NOW | `uv run mypy packages/iol-client` → `Success: no issues found in 31 source files`, exit 0 (R-01) | job `typecheck`, `ci.yml:122-123` (step `mypy (src global)`) más `ci.yml:124-131` (step `mypy (tests por paquete)`, bucle que incluye `iol-client`): entre los dos cubren el mismo árbol que el comando del mapa recorre de una sola pasada |
| 38-r06 · 38-03-02 | VERIFIED-NOW | `uv run python verification/regen_snapshots.py && git diff --stat verification/snapshots/iol-client-surface.txt` → exit 0; el generador reescribió los **4** snapshots (`ambito-financiero-client` 10 símbolos, `iol-client` 19, `higyrus-client` 31, `matriz-client` 68) y la salida fue **byte-idéntica**: `git diff --stat verification/snapshots/iol-client-surface.txt` sin ninguna línea, `git diff --stat verification/snapshots/` sin ninguna línea y `git status --porcelain verification/` vacío tras la corrida (R-01) | **NOT ENFORCED** — `verification/regen_snapshots.py` no aparece en `.github/workflows/ci.yml`: ni en el job `lint` (que allowlistea 12 archivos `verification/test_*.py` en `ci.yml:81-92`, ninguno de ellos éste) ni en ningún otro job. La deriva de snapshot sólo se detecta corriendo el script a mano |
| 38-r07 · 38-04-01 | VERIFIED-NOW | `uv run pytest packages/matriz-client/tests/test_surface_types_red.py -q` → `19 passed in 0.22s`, exit 0 — chequeo de regresión de sólo-lectura sobre el paquete vecino, sin deselect (R-01) | job `test`, `ci.yml:133-166` (leg `matriz-client`; es la única fila del mapa de la Phase 38 que corre fuera de `iol-client`) |
| 38-r08 · 38-05-01 | VERIFIED-HISTORICALLY | Revisión de documento (`checkpoint:human-verify` sobre `38-CENSUS.md`), no re-derivable. Artefacto citado: la **confirmación humana fechada** registrada en el front-matter de `38-VERIFICATION.md`, clave `human_verification[0].confirmed: 2026-08-29T22:04:57Z`, cuyo `<expected>` enumera literalmente lo que el lector confirmó (toda fila de ambas tablas con celda de disposición y de evidencia no vacías; los tres paquetes representados; los ceros de ámbito y wallets por enumeración explícita y no por tabla vacía; la condición de stub de wallets; la discrepancia 10-vs-11 contra D-11 nombrada y no absorbida). El censo sigue en disco: `.planning/milestones/v1.7-phases/38-…/38-CENSUS.md`, 426 líneas. Cruzado con `38-VERIFICATION.md` truth #4 y truth #14 (R-06) | **NOT ENFORCED (por naturaleza)** — una revisión de completitud documental no es una aserción ejecutable; ningún job de `ci.yml` la cubre ni podría cubrirla |
| 38-m01 · (manual-only fila 1) | VERIFIED-HISTORICALLY | Misma conducta declarada desde la otra tabla: *"`38-CENSUS.md` tiene cero filas sin disposición"* (SC-2). Artefacto citado: la misma confirmación humana fechada `2026-08-29T22:04:57Z` del front-matter de `38-VERIFICATION.md` (`human_verification[0].confirmed`), más `38-CENSUS.md` en disco (426 líneas) y el sign-off del lector en `38-UAT.md`. La auditoría **no** re-hizo la lectura del censo con criterio propio: eso sustituiría la evidencia registrada por un juicio de 2026-08-31 (R-06, §3 del contrato) | **NOT ENFORCED (por naturaleza)** — la propia celda `Why Manual` del mapa lo dice: *"Census completeness (SC-2) is a documentation contract, not an executable assertion"* |

*Disposiciones: `VERIFIED-NOW` = comando re-ejecutado en esta sesión, verde, con conteo distinto de
cero · `VERIFIED-HISTORICALLY` = artefacto fechado citado, no re-derivable ·
`NOT-VERIFIABLE-RETROACTIVELY` = requería red en vivo, ventana de mercado o checkpoint humano no
reproducible. Calificadores: `(comando corregido)` R-02 · `(ruta corregida)` R-03 ·
`(comando redactado retroactivamente)` R-04.*
