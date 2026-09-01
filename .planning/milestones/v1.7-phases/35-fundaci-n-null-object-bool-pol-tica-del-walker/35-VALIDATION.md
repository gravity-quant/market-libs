---
phase: 35
slug: fundaci-n-null-object-bool-pol-tica-del-walker
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: false
not_verifiable_retroactively: 0
audited_commit_sha: 37a83fe693a303a551f4374f48fe6fc5521804f7
audit_baseline_head: 6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5
frozen_tree_verified: true
wave_0_complete: false
created: 2026-08-28
updated: 2026-08-31
last_audited: 2026-08-31
---

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3 (+pytest-asyncio, pytest-httpx) |
| **Config file** | `pyproject.toml` (root) |
| **Quick run command** | `uv run pytest packages/<pkg>/tests/test_decode.py -q` (per touched package) |
| **Full suite command** | `uv run pytest packages/ -q` (NEVER bare `pytest` — `verification/` hangs >10 min and is red at baseline per HARN-VERIF-01) |
| **Estimated runtime** | ~95 seconds (full packages/ suite: 1749 tests measured) |

---

## Sampling Rate

- **After every task commit:** Run the touched package's `tests/test_decode.py` + `tests/test_models.py`
- **After every plan wave:** Run `uv run pytest packages/ -q` + the 4 gates (`check_decode_intactness.py`, `check_uniform_structure.py`, `check_surface_types.py`, per-package `test_surface_parity.py`)
- **Before `/gsd-verify-work`:** Full suite green + `uv run mypy` clean + `git diff` empty on `verification/snapshots/`
- **Max feedback latency:** ~100 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner) | — | — | NOBJ-01 / NOBJ-02 | — | N/A | unit | see plans | — | ⬜ superada por las 12 filas reconstruidas de abajo — ver `## Validation Audit 2026-08-31` |
| 35-01-01 | 01 | 1 | NOBJ-01 / NOBJ-02 | — | N/A | unit (RED fixture) | `uv run pytest packages/higyrus-client/tests/test_null_object.py -q -k "not_vacuous or invisible_to_get_type_hints or does_not_change_the_divergence_count" && ! uv run pytest packages/higyrus-client/tests/test_null_object.py -q -k "falsy_when_empty or truthy_when_populated or empty_emits_nothing"` | ✅ | ⬜ histórico |
| 35-01-02 | 01 | 1 | NOBJ-01 / NOBJ-02 | — | N/A | unit + static | `uv run pytest packages/higyrus-client -q && uv run mypy packages/higyrus-client/src && uv run ruff check packages/higyrus-client && uv run ruff format --check packages/higyrus-client` | ✅ | ✅ (VN 2026-08-31) |
| 35-01-03 | 01 | 1 | NOBJ-01 / NOBJ-02 | — | N/A | unit | `uv run pytest packages/higyrus-client/tests/test_decode.py -q -k "wrong_typed_list or still_raises_on_a_wrong_typed_list" && uv run pytest packages/higyrus-client -q` | ✅ | ✅ (VN 2026-08-31) |
| 35-02-01 | 02 | 1 | NOBJ-02 | — | N/A | static | `test -f .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md && test "$(grep -c '^\| ' .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md)" -ge 35` | ✅ | ✅ (VN 2026-08-31) |
| 35-02-02 | 02 | 1 | NOBJ-02 | — | N/A | static | `grep -q "iol-client" .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md && grep -q "wallets-client" .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md && grep -qi "phase 39" .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md` | ✅ | ✅ (VN 2026-08-31) |
| 35-03-01 | 03 | 2 | NOBJ-01 / NOBJ-02 | — | N/A | unit + static | `uv run pytest packages/iol-client -q && uv run mypy packages/iol-client/src && uv run ruff check packages/iol-client && uv run ruff format --check packages/iol-client` | ✅ | ✅ (VN 2026-08-31) |
| 35-03-02 | 03 | 2 | NOBJ-01 / NOBJ-02 | — | N/A | unit + static | `uv run pytest packages/market-data-client -q && uv run mypy packages/market-data-client/src && uv run ruff check packages/market-data-client && uv run ruff format --check packages/market-data-client` | ✅ | ✅ (VN 2026-08-31) |
| 35-04-01 | 04 | 2 | NOBJ-01 / NOBJ-02 | — | N/A | unit + static | `uv run pytest packages/matriz-client -q && uv run mypy packages/matriz-client/src && uv run ruff check packages/matriz-client && uv run ruff format --check packages/matriz-client` | ✅ | ✅ (VN 2026-08-31) |
| 35-04-02 | 04 | 2 | NOBJ-01 / NOBJ-02 | — | N/A | unit + static | `uv run pytest packages/ambito-financiero-client -q && uv run mypy packages/ambito-financiero-client/src && uv run ruff check packages/ambito-financiero-client && uv run ruff format --check packages/ambito-financiero-client` | ✅ | ✅ (VN 2026-08-31) |
| 35-04-03 | 04 | 2 | NOBJ-01 / NOBJ-02 | — | N/A | unit + static | `uv run pytest packages/wallets-client -q && uv run ruff check packages/wallets-client && uv run ruff format --check packages/wallets-client` | ✅ | ✅ (VN 2026-08-31) |
| 35-05-01 | 05 | 3 | NOBJ-02 | — | N/A | unit + static | `uv run python tools/check_decode_intactness.py && uv run pytest packages -q && uv run ruff check packages/ && uv run ruff format --check packages/ && uv run mypy && uv run mypy packages/market-data-client/src` | ✅ | ✅ (VN 2026-08-31) |
| 35-05-02 | 05 | 3 | NOBJ-02 | — | N/A | unit + static + snapshot | `uv run python tools/check_decode_intactness.py && uv run python tools/check_uniform_structure.py && uv run python tools/check_surface_types.py && uv run python tools/surface_parity.py && uv run pytest packages -q && uv run pytest tests -q && uv run python verification/regen_snapshots.py && git diff --exit-code verification/snapshots/ && git diff --exit-code pyproject.toml uv.lock` | ✅ | ✅ (VN 2026-08-31) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · ⬜ histórico (VERIFIED-HISTORICALLY, auditoría 2026-08-31) · ⬜ no re-verificable (NOT-VERIFIABLE-RETROACTIVELY, auditoría 2026-08-31)*

> **Nota de reconstrucción (auditoría 2026-08-31, Phase 41 / NYQ-01).** El mapa shipeó con una única
> fila placeholder. Las 12 filas de arriba se reconstruyeron desde los bloques `<verify><automated>`
> de `35-01..05-PLAN.md` (3 + 2 + 2 + 3 + 2 = 12, medido con `grep -c '<automated>'`), en el orden de
> los planes. La fila placeholder se **conserva** como evidencia de que la fase shipeó con el mapa sin
> llenar. Los comandos están transcritos **literales** de su plan de origen, sin corregir: las
> correcciones de ruta se documentan en `### Correcciones de comando` de la sección de auditoría, no
> reescribiendo el comando histórico. (El `\|` de la fila `35-02-01` es sólo el escape de markdown
> para el pipe literal del `grep -c '^| '` original.)

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — pytest + the 4 v1.6 gates already run in CI; new tests slot into existing `tests/test_decode.py` / `tests/test_models.py` per package.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Snapshot byte-identity | NOBJ-02 (criterio 4) | `verification/` never runs in CI | `git diff --exit-code verification/snapshots/` after regen |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter
- [x] Audit 2026-08-31: 13 filas dispuestas (12 VERIFIED-NOW / 1 VERIFIED-HISTORICALLY / 0 NOT-VERIFIABLE-RETROACTIVELY); 0 archivos de lock nuevos; nyquist_compliant sigue en false

**Approval:** pending

---

## Validation Audit 2026-08-31

Auditoría Nyquist retroactiva de la Phase 35, corrida a mano contra el árbol congelado de v1.7 según
el contrato `41-AUDIT-CONTRACT.md` (Phase 41, NYQ-01). Estado de entrada: `status: draft`,
`nyquist_compliant: false`, mapa con 1 fila placeholder sin disponer que ocultaba 12 bloques de
verificación reales; **sin subagente** — la auditoría lee y dispone, no repara (D-06a).

**Auditor:** Phase 41 (`/gsd-execute-phase 41`, plan 41-02) — auditoría de lectura y disposición
**Árbol auditado:** commit de `v1.7` `37a83fe693a303a551f4374f48fe6fc5521804f7`; HEAD de la sesión
de auditoría `6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5`; identidad probada con
`git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0 (diff vacío)

| Metric | Count |
|--------|-------|
| Filas auditadas (denominador) | 13 |
| VERIFIED-NOW | 12 |
| VERIFIED-HISTORICALLY | 1 |
| NOT-VERIFIABLE-RETROACTIVELY | 0 |
| Correcciones de comando | 2 (ambas `ruta corregida`, R-03) |
| Archivos de test nuevos escritos | 0 |
| Filas NOT ENFORCED en CI | 5 |
| Suite de re-ejecución de esta sesión | `2152 passed, 1 deselected in 86.96s` |

### Disposición por fila

| Row | Disposition | Evidence (this session) | CI enforcement surface |
|-----|-------------|-------------------------|------------------------|
| 35-r01 · 35-01-01 | VERIFIED-HISTORICALLY | Paso RED de TDD: la cadena corre un selector positivo y después asserta con `&& !` que `falsy_when_empty or truthy_when_populated or empty_emits_nothing` fallan. Esos 3 tests hoy pasan (medido: `45 passed, 3 deselected`), así que la cadena sale 1 **por diseño** (R-05). NO se re-ejecutó y NO se "arregló". Evidencia histórica: `35-01-SUMMARY.md` (commit `ece3a3c`, set rojo de 11 fallas medido en plan-time), corroborado independientemente por la verdad #2 de `35-VERIFICATION.md` | **NOT ENFORCED** — la forma negada de la aserción no existe en `ci.yml`. El archivo `packages/higyrus-client/tests/test_null_object.py` sí corre, en su forma positiva, en el job `test` (`ci.yml:133-166`); esa corrida no es esta fila |
| 35-r02 · 35-01-02 | VERIFIED-NOW | `uv run pytest packages/higyrus-client -q && uv run mypy packages/higyrus-client/src && uv run ruff check packages/higyrus-client && uv run ruff format --check packages/higyrus-client` → `303 passed in 38.88s` · `Success: no issues found in 13 source files` · `All checks passed!` · `27 files already formatted` | job `test`, `ci.yml:133-166`; tramo mypy → job `typecheck`, `ci.yml:122-123`; tramos ruff → job `lint`, `ci.yml:36-39` |
| 35-r03 · 35-01-03 | VERIFIED-NOW | `uv run pytest packages/higyrus-client/tests/test_decode.py -q -k "wrong_typed_list or still_raises_on_a_wrong_typed_list" && uv run pytest packages/higyrus-client -q` → `2 passed, 57 deselected in 0.01s` · `303 passed in 39.22s` | job `test`, `ci.yml:133-166` |
| 35-r04 · 35-02-01 | VERIFIED-NOW (ruta corregida) | Comando original del mapa (ruta muerta tras la mudanza al archivo del milestone): `test -f .planning/phases/35-…/35-RETIRED-TRIPLES.md && test "$(grep -c '^\| ' .planning/phases/35-…/35-RETIRED-TRIPLES.md)" -ge 35`. Ejecutado con la ruta corregida: `test -f .planning/milestones/v1.7-phases/35-…/35-RETIRED-TRIPLES.md && test "$(grep -c '^\| ' .planning/milestones/v1.7-phases/35-…/35-RETIRED-TRIPLES.md)" -ge 35` → exit 0; `grep -c '^\| '` = **58**, por encima del piso `-ge 35` (R-03) | **NOT ENFORCED** — aserción sobre markdown de `.planning/`; no aparece en `ci.yml` |
| 35-r05 · 35-02-02 | VERIFIED-NOW (ruta corregida) | Comando original del mapa: `grep -q "iol-client" .planning/phases/35-…/35-RETIRED-TRIPLES.md && grep -q "wallets-client" … && grep -qi "phase 39" …`. Ejecutado con la ruta corregida bajo `.planning/milestones/v1.7-phases/35-…/` → exit 0; hits medidos: `iol-client` **9**, `wallets-client` **4**, `phase 39` **23** (R-03) | **NOT ENFORCED** — aserción sobre markdown de `.planning/`; no aparece en `ci.yml` |
| 35-r06 · 35-03-01 | VERIFIED-NOW | `uv run pytest packages/iol-client -q && uv run mypy packages/iol-client/src && uv run ruff check packages/iol-client && uv run ruff format --check packages/iol-client` → `311 passed in 13.50s` · `Success: no issues found in 13 source files` · `All checks passed!` · `31 files already formatted` | job `test`, `ci.yml:133-166`; mypy → job `typecheck`, `ci.yml:122-123`; ruff → job `lint`, `ci.yml:36-39` |
| 35-r07 · 35-03-02 | VERIFIED-NOW | `uv run pytest packages/market-data-client -q && uv run mypy packages/market-data-client/src && uv run ruff check packages/market-data-client && uv run ruff format --check packages/market-data-client` → `711 passed in 1.07s` · `Success: no issues found in 13 source files` · `All checks passed!` · `49 files already formatted` | job `test`, `ci.yml:133-166`; mypy → job `typecheck`, `ci.yml:122-123`; ruff → job `lint`, `ci.yml:36-39` |
| 35-r08 · 35-04-01 | VERIFIED-NOW | `uv run pytest packages/matriz-client -q && uv run mypy packages/matriz-client/src && uv run ruff check packages/matriz-client && uv run ruff format --check packages/matriz-client` → `609 passed in 27.14s` · `Success: no issues found in 17 source files` · `All checks passed!` · `46 files already formatted` | job `test`, `ci.yml:133-166`; mypy → job `typecheck`, `ci.yml:122-123`; ruff → job `lint`, `ci.yml:36-39` |
| 35-r09 · 35-04-02 | VERIFIED-NOW | `uv run pytest packages/ambito-financiero-client -q && uv run mypy packages/ambito-financiero-client/src && uv run ruff check packages/ambito-financiero-client && uv run ruff format --check packages/ambito-financiero-client` → `208 passed, 1 deselected in 14.04s` · `Success: no issues found in 13 source files` · `All checks passed!` · `34 files already formatted` | job `test`, `ci.yml:133-166`; mypy → job `typecheck`, `ci.yml:122-123`; ruff → job `lint`, `ci.yml:36-39` |
| 35-r10 · 35-04-03 | VERIFIED-NOW | `uv run pytest packages/wallets-client -q && uv run ruff check packages/wallets-client && uv run ruff format --check packages/wallets-client` → `10 passed in 0.02s` · `All checks passed!` · `11 files already formatted` | job `test`, `ci.yml:133-166`; ruff → job `lint`, `ci.yml:36-39` (la cadena no lleva tramo mypy: wallets está exento del roster de `_decode.py`) |
| 35-r11 · 35-05-01 | VERIFIED-NOW | `uv run python tools/check_decode_intactness.py && uv run pytest packages -q && uv run ruff check packages/ && uv run ruff format --check packages/ && uv run mypy && uv run mypy packages/market-data-client/src` → gate exit 0 (`5 in-scope packages carry a _decode.py; wallets-client exempt`) · `2152 passed, 1 deselected in 86.96s` · `All checks passed!` · `198 files already formatted` · `Success: no issues found in 75 source files` · `Success: no issues found in 13 source files` | `check_decode_intactness.py` → job `lint`, `ci.yml:55`; `pytest packages` → job `test`, `ci.yml:133-166`; ruff → job `lint`, `ci.yml:36-39`; mypy → job `typecheck`, `ci.yml:122-123` |
| 35-r12 · 35-05-02 | VERIFIED-NOW | Gate de fase, 9 tramos, todos exit 0: `check_decode_intactness.py` · `check_uniform_structure.py` · `check_surface_types.py` · `tools/surface_parity.py` · `uv run pytest packages -q` → `2152 passed, 1 deselected in 93.56s` · `uv run pytest tests -q` → `2 passed in 0.01s` · `uv run python verification/regen_snapshots.py` (4 archivos escritos, byte-idénticos) · `git diff --exit-code verification/snapshots/` → exit 0 · `git diff --exit-code pyproject.toml uv.lock` → exit 0. Post-corrida: `git status --porcelain verification/` vacío | **Parcial — la fila NO colapsa a un solo veredicto.** Sí corren en CI: `check_decode_intactness.py` (job `lint`, `ci.yml:55`), `check_uniform_structure.py` (`ci.yml:60`), `check_surface_types.py` (`ci.yml:66`), `pytest packages` (job `test`, `ci.yml:133-166`). **NOT ENFORCED:** `tools/surface_parity.py` **como script** — no aparece en `ci.yml` (los seis `packages/*/tests/test_surface_parity.py` sí corren en el job `test`; no es la misma cosa) y `verification/regen_snapshots.py` + su `git diff` |
| 35-m01 · (manual-only fila 1) | VERIFIED-NOW | La celda `Test Instructions` de la fila manual-only es un comando ejecutable, no un checkpoint humano. Re-corrido esta sesión: `uv run python verification/regen_snapshots.py && git diff --exit-code verification/snapshots/` → 4 archivos escritos, **byte-idénticos**, `git diff --exit-code` exit 0, `git status --porcelain verification/` vacío después (R-01) | **NOT ENFORCED** — `verification/regen_snapshots.py` no aparece en `ci.yml`; es la razón declarada en la propia columna `Why Manual` de la fila |

*Disposiciones: `VERIFIED-NOW` = comando re-ejecutado en esta sesión, verde, con conteo distinto de
cero · `VERIFIED-HISTORICALLY` = artefacto fechado citado, no re-derivable ·
`NOT-VERIFIABLE-RETROACTIVELY` = requería red en vivo, ventana de mercado o checkpoint humano no
reproducible. Calificadores: `(comando corregido)` R-02 · `(ruta corregida)` R-03 ·
`(comando redactado retroactivamente)` R-04.*

### Correcciones de comando

Dos, ambas de **ruta** (R-03), ambas causadas por la mudanza de `.planning/phases/35-…/` a
`.planning/milestones/v1.7-phases/35-…/` del archivo del milestone v1.7. Ninguna toca el selector ni
la aserción: el piso y los literales buscados quedaron idénticos.

| Fila | Comando viejo (literal del mapa) | Comando ejecutado | Por qué |
|------|----------------------------------|-------------------|---------|
| 35-r04 | `test -f .planning/phases/35-…/35-RETIRED-TRIPLES.md && test "$(grep -c '^\| ' …)" -ge 35` | idéntico con el prefijo `.planning/milestones/v1.7-phases/` | La ruta `.planning/phases/35-…/` ya no existe (verificado: `test -f` → falso). El archivo vive en el archivo del milestone y tiene **58** filas `^\| `, por encima del piso `-ge 35` |
| 35-r05 | `grep -q "iol-client" .planning/phases/35-…/35-RETIRED-TRIPLES.md && grep -q "wallets-client" … && grep -qi "phase 39" …` | idéntico con el prefijo `.planning/milestones/v1.7-phases/` | Misma ruta muerta. Los tres literales están presentes en el archivo archivado (9 / 4 / 23 hits) |

**`35-02-PLAN.md` NO fue editado.** Los archivos de plan son registro histórico; la ruta stale se
nombra abajo, no se reescribe.

Cero correcciones de **selector** (R-02) y cero comandos redactados retroactivamente (R-04) en esta
fase: los 12 bloques `<verify><automated>` de los cinco planes declaran comando concreto, y ningún
selector `-k` seleccionó cero tests.

### Hallazgos de bookkeeping

Cuatro. Ninguno cambia una disposición; los cuatro se **nombran** en vez de corregirse en silencio.

1. **Versiones stale en `## Test Infrastructure`.** La tabla de este archivo declara **pytest 8.3**.
   Lo medido en esta sesión es **pytest 9.0.3**, con **mypy 1.20.2** (compiled: yes) y
   **ruff 0.15.12**, sobre **uv 0.11.3**. La fila es stale desde antes de esta fase. No se reescribe
   la tabla histórica.
2. **Conteo de tests stale en `## Test Infrastructure`.** El campo `Estimated runtime` declara
   *"~95 seconds (full packages/ suite: 1749 tests measured)"*. Lo medido hoy sobre el mismo árbol
   congelado es **2152 passed, 1 deselected in 86.96s**. El tiempo estimado sigue siendo correcto; el
   conteo de tests no — quedó fijado en una medición de plan-time anterior a las suites que las
   propias waves 1-2 de la fase agregaron.
3. **Dos rutas stale embebidas en `35-02-PLAN.md`.** Los dos bloques `<verify><automated>` de ese
   plan siguen apuntando a `.planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md`,
   ruta que ya no existe. Se dejan **a propósito**: son registro histórico de lo que la fase declaró
   verificar. La corrección vive en la columna `Evidence` de las filas `35-r04` / `35-r05`, no en el
   archivo de plan.
4. **El mapa shipeó vacío.** `## Per-Task Verification Map` se entregó con una única fila
   `(filled by planner)` y ninguna fila real, pese a que los cinco planes de la fase declaraban 12
   bloques `<verify><automated>` concretos. Ese es el hallazgo que motiva D-05: disponer esa fila
   como unidad habría certificado "1/1, 100%" sin auditar nada. La fila se **conserva** en el mapa,
   marcada como superada, precisamente para que la evidencia del hueco no desaparezca al taparlo.

### Escalaciones

Ninguna. Ninguna fila quedó sin regla aplicable: R-05 cubre el único paso RED (`35-r01`), R-03 cubre
las dos rutas muertas (`35-r04`, `35-r05`) y R-01 cubre las diez restantes. Ningún selector `-k`
seleccionó cero tests, de modo que no apareció una tercera fila de selección vacía (la señal que el
contrato manda escalar). Las cuentas medidas coinciden exactamente con la distribución esperada de la
§2.4 del contrato — 12 / 1 / 0 — y con el conteo esperado de 5 filas `NOT ENFORCED`; no hubo
divergencia que reportar. El árbol quedó limpio: `git status --porcelain verification/` vacío y
`ls verification/test_*.py | wc -l` sigue en **52** después de correr el regenerador de snapshots dos
veces.
Cero archivos de test nuevos; cero escalaciones.

Veredicto de auditoría: **Phase 35 queda PARTIAL** — status draft → validated,
nyquist_compliant sigue en false.

`nyquist_compliant` sigue en `false` porque R-09 no se satisface por dos de sus tres condiciones. (b)
falla: la fase retiene **una** fila `VERIFIED-HISTORICALLY` (`35-r01`, el paso RED de TDD, cuya
conducta sólo es demostrable contra el árbol pre-GREEN que ya no existe). (c) falla: **dos** filas
llevan calificador de corrección (`35-r04` y `35-r05`, ruta corregida). Una fase cuyo contrato de
verificación tuvo que ser reparado por su auditor para poder correr no es Nyquist-compliant; es una
fase cuyo bookkeeping estaba roto y hoy está descrito. El estado real de la conducta es bueno — 12 de
13 filas verdes hoy sobre el árbol congelado, cero rojos, cero gaps de cobertura — y esa es
exactamente la distinción que `status: validated` + `nyquist_compliant: false` codifica.
