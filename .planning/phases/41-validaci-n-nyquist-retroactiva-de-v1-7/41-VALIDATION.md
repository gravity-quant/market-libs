---
phase: 41
slug: validaci-n-nyquist-retroactiva-de-v1-7
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: false
not_verifiable_retroactively: 0
audited_commit_sha: 37a83fe693a303a551f4374f48fe6fc5521804f7
audit_baseline_head: 6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5
frozen_tree_verified: true
wave_0_complete: true
created: 2026-08-31
updated: 2026-08-31
last_audited: 2026-08-31
---

# Phase 41 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (per-package, monorepo workspace) |
| **Runner / toolchain medido** | uv 0.11.3 · pytest 9.0.3 · mypy 1.20.2 · ruff 0.15.12 · git 2.39.5 · node v24.15.0 |
| **Config file** | root `pyproject.toml` (`asyncio_mode = "auto"`, `--import-mode=importlib`) |
| **Quick run command** | `uv run pytest -k "<selector de la fila auditada>"` (por fila re-ejecutada) |
| **Full suite command** | `uv run pytest packages -q` (workspace-wide, 6 paquetes, ~93 s) |
| **Estimated runtime** | ~90 segundos para el barrido completo de re-ejecución |

Esta es una fase de auditoría/documentación retroactiva, no de implementación. Sus "tests" son
(a) la re-ejecución de los bloques `<automated>` ya declarados en las Phases 35–39 congeladas, y
(b) aserciones bash/grep que verifican que las tablas de disposición y el front-matter que esta
fase escribe son internamente consistentes.

Las versiones de arriba fueron **medidas** en la sesión de auditoría (2026-08-31) y quedan
registradas en `41-AUDIT-CONTRACT.md § 1.4`. Reemplazan la declaración previa de este archivo, que
nombraba la serie **8.x** del runner y era stale. La misma declaración stale (serie **8.3**)
sobrevive en `35-VALIDATION.md` y **no se corrige ahí en silencio**: se nombra como hallazgo de
bookkeeping en su propia sección de auditoría.

---

## Denominador del criterio 2 (Wave 0 gap #2 — cerrada)

El denominador de "cero filas sin disponer" para las cinco fases auditadas es **62**:

```
Phase 35 : 13   (12 filas reconstruidas desde 35-01..05-PLAN.md + 1 manual-only)
Phase 36 : 11
Phase 37 : 14
Phase 38 :  9
Phase 39 : 15
           ---
Total    : 62
```

Desglose canónico: **13 / 11 / 14 / 9 / 15**.

Se rechazan por escrito los dos denominadores equivocados: **51** (as-declared, que cuenta la fila
placeholder de la Phase 35 como una unidad — prohibido por D-05) y **25** (los criterios de éxito
del ROADMAP de v1.7 — excluidos por D-03). Detalle y aritmética en
`41-AUDIT-CONTRACT.md § 2`.

Denominador **de esta fase** (criterio de auto-disposición, D-10): **16** tareas reales
(3 + 2 + 2 + 2 + 2 + 2 + 3 sobre los siete planes), medido con `grep -c '<task '`. Nota: los
bloques `<verify><automated>` de `41-01` Task 3 y `41-07` Task 3 declaran `14`, que es una mis-suma
del planner sobre su propia lista enumerada de 16 IDs; el valor correcto es **16**
(`41-AUDIT-CONTRACT.md § 2.5`).

---

## Sampling Rate

- **Después de cada commit de tarea:** re-correr la aserción `<automated>` de esa tarea. Para las
  tareas de la Wave 2, eso incluye la re-ejecución de las filas de la fase que se está disponiendo.
- **Después de cada wave:** re-correr `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` —
  el criterio 1 es un **invariante continuo**, no un gate de una sola vez.
- **Antes de `/gsd-verify-work`:** los cinco `{N}-VALIDATION.md` deben parsear, declarar
  `audited_commit_sha`, y tener cero filas sin disponer (suma == 62).
- **Max feedback latency:** ~93 s (la corrida completa de `uv run pytest packages -q`, que es la
  fila más cara del conjunto).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 41-01-01 | 01 | 1 | NYQ-01 | T-41-02 / mitigate | El árbol de fuente de v1.7 está probado idéntico al tag y ambos SHA quedan declarados antes del primer artefacto | bash | `test -f …/41-AUDIT-CONTRACT.md && git diff --quiet v1.7 HEAD -- . ':(exclude).planning' && grep -q '37a83fe6…' …/41-AUDIT-CONTRACT.md && grep -qE 'audit_baseline_head[^0-9a-f]*[0-9a-f]{40}' …/41-AUDIT-CONTRACT.md` | ✅ | ✅ (VN 2026-08-31) |
| 41-01-02 | 01 | 1 | NYQ-01 | T-41-03 / mitigate | El contrato fija denominador, claves, R-01..R-09, front-matter objetivo, esqueleto y mapa de CI | bash | `for s in '^## 2\.' … '^## 8\.'; do grep -qE "$s" $C \|\| exit 1; done; grep -q '13 / 11 / 14 / 9 / 15' $C && grep -q 'not_verifiable_retroactively' $C && grep -q 'Cero archivos de test nuevos; cero escalaciones.' $C && grep -q 'ci.yml:81-92' $C && test "$(grep -cE 'R-0[1-9]' $C)" -ge 9` | ✅ | ✅ (VN 2026-08-31) |
| 41-01-03 | 01 | 1 | NYQ-01 | — / — | Las dos Wave 0 gaps quedan cerradas y el mapa de esta fase refleja los 7 planes reales | bash | `grep -q 'wave_0_complete: true' $V && grep -q 'not_verifiable_retroactively' $V && grep -q '13 / 11 / 14 / 9 / 15' $V && test "$(grep -c '^\| 41-0[1-7]-0[0-9] ' $V)" -eq 16`, más dos aserciones negativas (cero placeholders de selector, cero declaraciones stale del runner) cuyos literales **no** pueden transcribirse en este archivo sin auto-falsificarlo — cadena literal en `41-01-PLAN.md` Task 3 | ✅ | ✅ (VN 2026-08-31) |
| 41-02-01 | 02 | 2 | NYQ-01 | — / — | Las 12 filas reales de la Phase 35 se reconstruyen desde sus 5 planes; la placeholder sobrevive marcada | bash | `test "$(grep -h -c '<automated>' $D/35-0*-PLAN.md \| paste -sd+ - \| bc)" -eq 12 && test "$(grep -c '^\| 35-0[1-5]-0[1-3] ' $D/35-VALIDATION.md)" -eq 12 && grep -q 'filled by planner' $D/35-VALIDATION.md && git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` | ✅ | ✅ (VN 2026-08-31) |
| 41-02-02 | 02 | 2 | NYQ-01 | T-41-03 / mitigate | Las 13 filas de la Phase 35 quedan dispuestas exactamente una vez; front-matter transformado sin flipear el flag | bash | `test "$N" -eq 13 && test $((S+H+R)) -eq 13 && grep -q '^status: validated' $F && grep -q '^nyquist_compliant: false' $F && grep -q '^not_verifiable_retroactively: 0' $F && grep -q '37a83fe6…' $F && grep -q 'Cero archivos de test nuevos; cero escalaciones.' $F` (cadena completa: `41-02-PLAN.md` Task 2) | ✅ | ✅ (VN 2026-08-31) |
| 41-03-01 | 03 | 2 | NYQ-01 | — / — | Las 11 filas de la Phase 36 re-corren verdes; la fila sin comando declarado (`36-r11`) se resuelve contra un lock enrolado en CI | pytest+bash | `uv run pytest packages/market-data-client/tests/test_market_data_chain.py -x -q && uv run pytest verification/test_main_market_data_deep_chain.py -q && uv run python tools/check_decode_intactness.py && grep -q 'verification/test_main_market_data_deep_chain.py' .github/workflows/ci.yml && git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` | ✅ | ✅ (VN 2026-08-31) |
| 41-03-02 | 03 | 2 | NYQ-01 | T-41-03 / mitigate | Las 11 filas de la Phase 36 quedan dispuestas exactamente una vez; front-matter transformado | bash | `test "$(X \| wc -l)" -eq 11 && test "$((VN+VH+NVR))" -eq 11 && grep -q '^status: validated' $F && grep -q '^nyquist_compliant: false' $F && grep -q '^not_verifiable_retroactively: 0' $F && grep -q '37a83fe6…' $F` (cadena completa: `41-03-PLAN.md` Task 2) | ✅ | ✅ (VN 2026-08-31) |
| 41-04-01 | 04 | 2 | NYQ-01 | — / — | Las 14 filas de la Phase 37 re-corren verdes; el selector `-k alias_surfaces` (0 seleccionados) se re-apunta leyendo el cuerpo del sustituto | pytest+static | `uv run pytest packages/matriz-client/tests/test_surface_types_red.py -q && uv run pytest packages/matriz-client/tests/test_null_object.py -k "rest_parsed_snapshot or ws_frame_parsed_snapshot" -q && uv run mypy packages/matriz-client/src && git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` | ✅ | ✅ (VN 2026-08-31) |
| 41-04-02 | 04 | 2 | NYQ-01 | T-41-03 / mitigate | Las 14 filas de la Phase 37 quedan dispuestas exactamente una vez; front-matter transformado | bash | `test "$(X \| wc -l)" -eq 14 && test "$((VN+VH+NVR))" -eq 14 && grep -q '^status: validated' $F && grep -q '^nyquist_compliant: false' $F && grep -q '^not_verifiable_retroactively: 0' $F && grep -q '37a83fe6…' $F` (cadena completa: `41-04-PLAN.md` Task 2) | ✅ | ✅ (VN 2026-08-31) |
| 41-05-01 | 05 | 2 | NYQ-01 | T-41-01 / mitigate | Las 7 filas automatizadas de la Phase 38 re-corren verdes y `regen_snapshots.py` deja el árbol limpio; las 2 de revisión reúnen su evidencia fechada | pytest+static+snapshot | `uv run pytest packages/iol-client/tests/test_models.py -k "puntas or round_trip" -q && uv run mypy packages/iol-client && uv run python verification/regen_snapshots.py && test -z "$(git status --porcelain)" && test -f …/38-CENSUS.md && grep -q 'human_verification' …/38-VERIFICATION.md && git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` | ✅ | ✅ (VN 2026-08-31) |
| 41-05-02 | 05 | 2 | NYQ-01 | T-41-03 / mitigate | Las 9 filas de la Phase 38 quedan dispuestas 7 VN / 2 VH / 0 NVR con 3 filas NOT ENFORCED nombradas | bash | `test "$(X \| wc -l)" -eq 9 && test "$(X \| grep -c 'VERIFIED-NOW')" -eq 7 && test "$(X \| grep -c 'VERIFIED-HISTORICALLY')" -eq 2 && test "$(X \| grep -c 'NOT ENFORCED')" -eq 3 && grep -q '^status: validated' $F && grep -q '^not_verifiable_retroactively: 0' $F` (cadena completa: `41-05-PLAN.md` Task 2) | ✅ | ✅ (VN 2026-08-31) |
| 41-06-01 | 06 | 2 | NYQ-01 | T-41-01 / mitigate | Las 10 filas automatizadas de la Phase 39 re-corren verdes; el selector `-k allowlist` se re-apunta; las 5 no automatizadas reúnen su evidencia parcial | pytest+manual | `uv run pytest verification/test_main_verify_classification.py verification/test_main_matriz_skip_line_shape.py verification/test_main_higyrus_skip_line_shape.py verification/test_cycle_closure_phase33.py verification/test_main_iol_deep_chain.py verification/test_main_higyrus_deep_chain.py verification/test_main_matriz_deep_chain.py -q && uv run pytest packages/matriz-client/tests/test_instruments_flat_identifier_shape.py -q && test -f …/39-CENSUS.md && test "$(ls .planning/verification/run-evidence/*.json \| wc -l)" -eq 4` | ✅ | ✅ (VN 2026-08-31) |
| 41-06-02 | 06 | 2 | NYQ-01 | T-41-03 / mitigate | Las 15 filas de la Phase 39 quedan 10 VN / 1 VH / 4 NVR, con `not_verifiable_retroactively: 4` como marcador del criterio 3b | bash | `test "$(X \| wc -l)" -eq 15 && test "$(X \| grep -c 'VERIFIED-NOW')" -eq 10 && test "$(X \| grep -c 'VERIFIED-HISTORICALLY')" -eq 1 && test "$(X \| grep -c 'NOT-VERIFIABLE-RETROACTIVELY')" -eq 4 && grep -q '^not_verifiable_retroactively: 4' $F` (cadena completa: `41-06-PLAN.md` Task 2) | ✅ | ✅ (VN 2026-08-31) |
| 41-07-01 | 07 | 3 | NYQ-01 | T-41-03 / mitigate | La aritmética del criterio 2 cierra (62 = 54 VN + 4 VH + 4 NVR), ningún flag quedó en `true`, ninguna celda es vacuamente verde | bash | bucle sobre `35..39`: `test $((a+b+d)) -eq $c` por fase · `grep 'deselected' \| grep -vc 'passed'` == 0 · `grep -q '^status: validated'` · `grep -q '^nyquist_compliant: true' && exit 1` · `test $T -eq 62 && test $VN -eq 54 && test $VH -eq 4 && test $NVR -eq 4` (cadena completa: `41-07-PLAN.md` Task 1) | ✅ | ✅ (VN 2026-08-31) |
| 41-07-02 | 07 | 3 | NYQ-01 | T-41-SC / accept | Criterio 4 (cero locks inertes: 52 archivos, `verification/` limpio) y criterio 5 (contención: `ci.yml` y `REQUIREMENTS.md` intactos, exactamente 5+1 VALIDATION.md tocados) | bash | `test -z "$(git status --porcelain verification/)" && test "$(ls verification/test_*.py \| wc -l)" -eq 52 && git diff --quiet $H HEAD -- .github/workflows/ci.yml && git diff --quiet $H HEAD -- .planning/REQUIREMENTS.md && grep -Fq 'NYQUIST-32-33' .planning/REQUIREMENTS.md && test "$(git diff --name-only $H HEAD \| grep -c 'v1\.7-phases/3[5-9]-.*-VALIDATION\.md')" -eq 5` (cadena completa: `41-07-PLAN.md` Task 2) | ✅ | ✅ (VN 2026-08-31) |
| 41-07-03 | 07 | 3 | NYQ-01 | T-41-03 / mitigate | La propia Phase 41 se auto-dispone con la misma vara (D-10): sección de auditoría, `status: validated`, filas dispuestas exactamente una vez | bash | `grep -q '^## Validation Audit 2026-08-31' $V && grep -q '^status: validated' $V && grep -qE '^not_verifiable_retroactively: [0-9]+' $V && grep -q '^audited_commit_sha: 37a83fe6…' $V && test "$(printf '%s\n' "$R" \| grep -c .)" -eq 16 && test -z "$(git status --porcelain)"` (cadena completa: `41-07-PLAN.md` Task 3; ver nota del denominador 16) | ✅ | ✅ (VN 2026-08-31) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · ⬜ histórico (VERIFIED-HISTORICALLY, auditoría 2026-08-31) · ⬜ no re-verificable (NOT-VERIFIABLE-RETROACTIVELY, auditoría 2026-08-31)*

*Los comandos de arriba están transcritos de los bloques `<verify><automated>` de los siete planes.
Los pipes van escapados (`\|`) por sintaxis de tabla y los SHA de 40 hex van elididos (`37a83fe6…`)
para que la fila sea legible; la forma ejecutable literal vive en el plan citado en cada celda.*

---

## Wave 0 Requirements

- [x] **Gap #1 — marcador de front-matter para el criterio 3b: RESUELTO.** El marcador es la clave
      entera **`not_verifiable_retroactively: {n}`**, presente en los **cinco** archivos con su
      valor real (35→0, 36→0, 37→0, 38→0, 39→4). Se descartó `nyquist_compliant: partial` porque
      D-09 fija el valor `false` y `41-PATTERNS.md` marca `partial` como un one-off del repo
      (`07-VALIDATION.md:5`) que no se adopta **como valor** — sí se copia su prosa como modelo para
      explicar un resultado PARTIAL. Ponerla también donde vale `0` es deliberado: un `0` explícito
      afirma "esta fase no retiene ninguno", su ausencia no afirma nada. Contrato:
      `41-AUDIT-CONTRACT.md § 4.3`.
- [x] **Gap #2 — denominador del criterio 2: FIJADO EN 62**, con el desglose
      **13 / 11 / 14 / 9 / 15**, declarado arriba en § *Denominador del criterio 2* y en
      `41-AUDIT-CONTRACT.md § 2`. Los denominadores 51 y 25 quedan rechazados por escrito.
- [x] **Gate de entrada (criterio 1): PASADO.** `git rev-parse v1.7^{commit}` →
      `37a83fe693a303a551f4374f48fe6fc5521804f7`;
      `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0. Es un invariante continuo,
      re-verificado por cada tarea de las Waves 2 y 3, no un gate de una sola vez.

*No se instala framework de test, no se toca `conftest.py`, y no se espera ningún archivo pytest
nuevo (D-08, conteo esperado: 0). La infraestructura existente cubre todas las necesidades de
re-ejecución.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Las 4 filas manual-only de la Phase 39 (`39-m01`..`39-m04`): corrida de driver en vivo, discriminación D-12 mercado-cerrado vs. mal modelado, contraste de censo, checkpoint del operador sobre D-02 | NYQ-01 | Exigían una sesión de mercado MATBA ROFEX en vivo o un checkpoint humano que no se puede re-derivar. Ningún comando de esta fase abre un socket (R-08) | **Disposición ya resuelta: `NOT-VERIFIABLE-RETROACTIVELY` para las cuatro (R-07).** Honra el ejemplo explícito de D-04 por sobre la recomendación alternativa del researcher: ante un conflicto entre una decisión lockeada y una inferencia posterior gana la decisión, y en una auditoría la dirección segura es sub-declarar (D-10). La evidencia parcial superviviente **no se descarta**: cada celda `Evidence` nombra `.planning/verification/run-evidence/{iol,higyrus,ambito-financiero,matriz}-client.json` (2026-08-29), `39-07-SUMMARY.md`, `39-CENSUS.md` § "Casos límite de D-12" y el sign-off del operador citado en `39-VALIDATION.md`, calificada como insuficiente para re-derivar la conducta. Rationale completo: `41-AUDIT-CONTRACT.md § 3.1` |

La Phase 41 en sí misma no tiene filas manual-only: sus 16 tareas llevan aserción `<automated>`.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter (only where earned per D-09 — this phase's own audit tasks, not a mechanical flip of Phases 35–39's flags)
- [x] Audit 2026-08-31: 16 filas dispuestas (16 VERIFIED-NOW / 0 históricas / 0 no re-verificables); 0 archivos de lock nuevos; nyquist_compliant sigue en false

**Approval:** pending

> **Nota de auto-disposición (D-10) — RESUELTA.** El `status` y el `nyquist_compliant` de **este**
> archivo estuvieron deliberadamente en `draft` / `false` hasta que la fase pudo sostenerse con la
> misma vara que las cinco que audita. `41-07` Task 3 corrió esa disposición con evidencia
> re-ejecutada: `status` pasó a `validated`, y `nyquist_compliant` **sigue en `false`** porque R-09
> no se satisface (tres filas cerraron con comando corregido). Cerrar las Wave 0 gaps no es lo mismo
> que estar validada, y estar validada no es lo mismo que ser Nyquist-compliant.

---

## Validation Audit 2026-08-31

Auto-auditoría Nyquist de la Phase 41, corrida a mano contra el árbol congelado de v1.7 según el
contrato `41-AUDIT-CONTRACT.md` (D-10: la fase se sostiene con la misma vara que las cinco que
audita). Estado de entrada: `status: draft`, `nyquist_compliant: false`, mapa con 16 filas de las
cuales 13 estaban sin disponer; **sin subagente** — la auditoría lee y dispone, no repara (D-06a).

**Auditor:** Phase 41 (`/gsd-execute-phase 41`, plan 41-07) — auditoría de lectura y disposición
**Árbol auditado:** commit de `v1.7` `37a83fe693a303a551f4374f48fe6fc5521804f7`; HEAD de la sesión
de auditoría `6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5`; identidad probada con
`git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0 (diff vacío)

| Metric | Count |
|--------|-------|
| Filas auditadas (denominador) | 16 |
| VERIFIED-NOW | 16 |
| VERIFIED-HISTORICALLY | 0 |
| NOT-VERIFIABLE-RETROACTIVELY | 0 |
| Correcciones de comando | 3 |
| Archivos de test nuevos escritos | 0 |
| Filas NOT ENFORCED en CI | 12 |
| Suite de re-ejecución de esta sesión | `38 passed` + `6 passed` + `19 passed` + `2 passed, 72 deselected` + `9 passed, 17 deselected` + `78 passed` + `13 passed` (más 3 corridas de mypy limpias y 9 cadenas de aserción bash en exit 0) |

### Disposición por fila

| Row | Disposition | Evidence (this session) | CI enforcement surface |
|-----|-------------|-------------------------|------------------------|
| 41-r01 · 41-01-01 | VERIFIED-NOW | cadena de `41-01-PLAN.md` Task 1 re-ejecutada: existencia del contrato + `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` + los dos SHA presentes → `exit 0` | NOT ENFORCED — aserción de estado de archivo y de identidad de árbol; ningún job de `ci.yml` la corre |
| 41-r02 · 41-01-02 | VERIFIED-NOW | cadena de `41-01-PLAN.md` Task 2 re-ejecutada: las 7 secciones `## 2.`..`## 8.` presentes, desglose canónico, clave de front-matter, frase de cierre, rango del allowlist y ≥ 9 reglas → `exit 0` | NOT ENFORCED — grep sobre un artefacto de `.planning/` |
| 41-r03 · 41-01-03 | VERIFIED-NOW (comando corregido) | cadena de `41-01-PLAN.md` Task 3 re-ejecutada con el denominador corregido a **16**: gaps cerradas, desglose canónico, 16 filas de tarea, y las dos aserciones negativas (cero placeholders de selector, cero declaraciones stale del runner) → `exit 0`. Los literales de esas dos negaciones **no** se transcriben acá porque este archivo es su propio objeto de aserción | NOT ENFORCED — grep auto-referencial sobre este mismo archivo |
| 41-r04 · 41-02-01 | VERIFIED-NOW | cadena de `41-02-PLAN.md` Task 1 re-ejecutada: 12 bloques `<automated>` sumados sobre los 5 planes de la Phase 35, 12 filas reconstruidas, placeholder sobreviviente marcada, árbol congelado → `exit 0` | NOT ENFORCED — grep sobre artefactos archivados de `.planning/milestones/` |
| 41-r05 · 41-02-02 | VERIFIED-NOW | cadena de `41-02-PLAN.md` Task 2 re-ejecutada: 13 filas, suma de tokens `= 13`, `status: validated`, flag en `false`, marcador en `0`, SHA de v1.7 y frase de cierre → `exit 0` | NOT ENFORCED — aserción aritmética sobre la tabla de `35-VALIDATION.md` |
| 41-r06 · 41-03-01 | VERIFIED-NOW | `uv run pytest packages/market-data-client/tests/test_market_data_chain.py -x -q` → `38 passed in 0.09s`; `uv run pytest verification/test_main_market_data_deep_chain.py -q` → `6 passed in 0.09s`; `uv run python tools/check_decode_intactness.py` verde; lock presente en el allowlist; árbol congelado → `exit 0` | parcial — el `pytest` de paquete corre en job `test`, `ci.yml:133-166`; el lock de `verification/` está allowlisted en `ci.yml:81`; `check_decode_intactness.py` corre en job `lint`, `ci.yml:55`. Las aserciones de grep del mismo bloque no corren en CI |
| 41-r07 · 41-03-02 | VERIFIED-NOW | cadena de `41-03-PLAN.md` Task 2 re-ejecutada: 11 filas, suma de tokens `= 11`, front-matter transformado con marcador en `0` y SHA de v1.7 → `exit 0` | NOT ENFORCED — aserción aritmética sobre la tabla de `36-VALIDATION.md` |
| 41-r08 · 41-04-01 | VERIFIED-NOW | `uv run pytest packages/matriz-client/tests/test_surface_types_red.py -q` → `19 passed in 0.20s`; `uv run pytest packages/matriz-client/tests/test_null_object.py -k "rest_parsed_snapshot or ws_frame_parsed_snapshot" -q` → `2 passed, 72 deselected in 0.01s` (descarte **parcial**, con conteo de pasados distinto de cero); `uv run mypy packages/matriz-client/src` → `Success: no issues found in 17 source files` | parcial — `pytest` de paquete en job `test`, `ci.yml:133-166`; `mypy` sobre `src` en job `typecheck`, `ci.yml:122-123`. La cláusula de árbol congelado del mismo bloque no corre en CI |
| 41-r09 · 41-04-02 | VERIFIED-NOW | cadena de `41-04-PLAN.md` Task 2 re-ejecutada: 14 filas, suma de tokens `= 14`, front-matter transformado con marcador en `0` y SHA de v1.7 → `exit 0` | NOT ENFORCED — aserción aritmética sobre la tabla de `37-VALIDATION.md` |
| 41-r10 · 41-05-01 | VERIFIED-NOW | `uv run pytest packages/iol-client/tests/test_models.py -k "puntas or round_trip" -q` → `9 passed, 17 deselected in 0.01s`; `uv run mypy packages/iol-client` → `Success: no issues found in 31 source files`; `uv run python verification/regen_snapshots.py` deja `git status --porcelain verification/` **vacío**; artefactos de censo y de confirmación fechada presentes → `exit 0` | parcial — `pytest` de paquete en job `test`, `ci.yml:133-166`; `mypy` en job `typecheck`, `ci.yml:122-123`. `regen_snapshots.py` y su `git diff` no corren en CI |
| 41-r11 · 41-05-02 | VERIFIED-NOW | cadena de `41-05-PLAN.md` Task 2 re-ejecutada: 9 filas, 7 verificadas ahora, 2 por artefacto fechado, 3 filas sin cobertura de CI nombradas, front-matter transformado → `exit 0` | NOT ENFORCED — aserción aritmética sobre la tabla de `38-VALIDATION.md` |
| 41-r12 · 41-06-01 | VERIFIED-NOW | `uv run pytest` sobre los 7 locks de `verification/` citados por el mapa de la Phase 39 → `78 passed in 0.41s`; `uv run pytest packages/matriz-client/tests/test_instruments_flat_identifier_shape.py -q` → `13 passed in 0.03s`; censo presente y los 4 sobres de evidencia de corrida en disco → `exit 0` | parcial — los 7 locks están allowlisted en job `lint`, `ci.yml:81-92`; el `pytest` de paquete corre en job `test`, `ci.yml:133-166`. Las aserciones de existencia de artefacto no corren en CI |
| 41-r13 · 41-06-02 | VERIFIED-NOW | cadena de `41-06-PLAN.md` Task 2 re-ejecutada: 15 filas, 10 verificadas ahora, 1 por artefacto fechado, 4 no re-derivables, y el marcador de front-matter en `4` → `exit 0` | NOT ENFORCED — aserción aritmética sobre la tabla de `39-VALIDATION.md` |
| 41-r14 · 41-07-01 | VERIFIED-NOW | bucle sobre las 5 fases: `total=62 VN=54 VH=4 NVR=4`, suma por fase igual al conteo de filas en las 5, cero celdas de descarte total, `status: validated` en las 5, cero flags en verdadero, SHA de v1.7 uniforme → `exit 0` | NOT ENFORCED — gate aritmético de shell sobre artefactos de `.planning/` |
| 41-r15 · 41-07-02 | VERIFIED-NOW (comando corregido) | cadena de `41-07-PLAN.md` Task 2 con la cláusula de `REQUIREMENTS.md` corregida (ver `### Correcciones de comando`): `verification/` limpio, 52 locks, `ci.yml` sin cambios desde el baseline, fila de alcance excluido byte-intacta, 5 artefactos de v1.7 tocados y 6 en total, cero fases fuera de alcance, rollup presente, árbol congelado → `exit 0` | NOT ENFORCED — gate de contención de alcance basado en `git diff` contra un SHA de sesión |
| 41-r16 · 41-07-03 | VERIFIED-NOW (comando corregido) | cadena de `41-07-PLAN.md` Task 3 con el denominador corregido a **16**: sección de auditoría presente, `status: validated`, marcador numérico presente, SHA de v1.7, 16 filas dispuestas con suma de tokens `= 16`, árbol de trabajo limpio y árbol congelado → `exit 0` (corrida post-commit) | NOT ENFORCED — grep auto-referencial sobre este mismo archivo |

*Disposiciones: `VERIFIED-NOW` = comando re-ejecutado en esta sesión, verde, con conteo distinto de
cero · `VERIFIED-HISTORICALLY` = artefacto fechado citado, no re-derivable ·
`NOT-VERIFIABLE-RETROACTIVELY` = requería red en vivo, ventana de mercado o checkpoint humano no
reproducible. Calificadores: `(comando corregido)` R-02 · `(ruta corregida)` R-03 ·
`(comando redactado retroactivamente)` R-04.*

### Correcciones de comando

| Fila | Comando viejo | Comando nuevo | Por qué |
|------|---------------|---------------|---------|
| `41-r03` | conteo de filas de tarea con `-eq 14` | mismo conteo con `-eq 16` | Mis-suma del planner sobre su propia lista enumerada de 16 IDs (`3 + 2 + 2 + 2 + 2 + 2 + 3 = 16`, medido con `grep -c '<task '`). Corrección ya registrada por `41-01` en `41-AUDIT-CONTRACT.md § 2.5`; se re-ejecuta acá contra el valor correcto |
| `41-r15` | `git diff --quiet <baseline> HEAD -- .planning/REQUIREMENTS.md` | hash byte-a-byte de la fila de alcance excluido contra el mismo commit de baseline, más `test <líneas cambiadas> -eq 2` sobre el diff acotado | La cláusula as-written es **insatisfacible por construcción**: el propio seam de estado de GSD (`requirements mark-complete NYQ-01`), que el workflow de ejecución obliga a correr al cerrar cada plan, edita `REQUIREMENTS.md` durante la fase. Las dos únicas líneas cambiadas son la casilla y la celda de estado de `NYQ-01`; la fila que el criterio 5 protege queda con hash idéntico al del baseline |
| `41-r16` | conteo de filas dispuestas con `-eq 14` | mismo conteo con `-eq 16` | Mismo arrastre de la mis-suma del planner que `41-r03` |

### Hallazgos de bookkeeping

- **El denominador de esta fase estaba mal declarado en dos bloques de verificación.** `41-01` Task 3
  y `41-07` Task 3 dicen `14`; la lista enumerada de IDs dentro de esos mismos bloques tiene 16
  entradas y el conteo medido sobre los siete planes da **16**. Se **nombra** y se corrige en el
  comando ejecutado; los archivos de plan **no** se reescriben — son registro histórico.
- **La cláusula de inmutabilidad de `REQUIREMENTS.md` del criterio 5 choca con el seam de estado del
  propio workflow.** No es una violación de alcance: es un gate escrito sin contemplar que
  `requirements mark-complete` corre dentro de la misma fase. Queda nombrado acá para que la Phase 45
  no herede la misma aserción imposible.
- **Una entrada de caché de research de esta fase quedó sin trackear.** Sus 16 hermanas de
  `.planning/research/.cache/` sí están en git; ésta se generó durante la fase y quedó fuera del
  índice, ensuciando `git status --porcelain` y haciendo fallar la cláusula de árbol limpio de
  `41-05` Task 1 y de `41-07` Task 3 por una razón ajena a lo que esas cláusulas miden. Se trackeó
  tras revisarla: cero esquemas de URL, arrobas de host, tokens, contraseñas o portadores.
- **Falla de test pre-existente y fuera de alcance.**
  `verification/test_main_matriz_login_fail_uniformity.py::test_probe_login_sync_returns_FINDING_on_authentication_error`
  falla con `TypeError: probe_login_sync() missing 1 required positional argument: 'client'`. El
  archivo no cambió en esta fase (el diff acumulado no toca ni un byte fuera de `.planning/`) y su
  último cambio traza a trabajo de la Phase 11. **No se arregla acá**: hacerlo violaría el invariante
  del criterio 1. Es además uno de los 40 locks que hoy no corren en CI, lo que explica que la falla
  haya sobrevivido sin romper el pipeline — exactamente el hallazgo que la declaración inerte de
  `41-ROLLUP.md` nombra.

### Escalaciones

Ninguna condición requirió juicio fuera del contrato: las tres correcciones de comando caen bajo
R-02 y quedan registradas arriba, y ninguna fila quedó sin regla que la calzara. Cero comandos de
red (R-08), cero instalaciones de paquete, cero cambios de fuente de producto.
Cero archivos de test nuevos; cero escalaciones.

**Evaluación de R-09 para esta fase.** (a) 100 % de filas verificadas ahora en forma **plana**:
**NO** — 13 de 16 son planas, 3 llevan calificador. (b) cero filas históricas y cero no
re-verificables: **SÍ** — 0 y 0. (c) cero calificadores de corrección: **NO** — 3 (`41-r03`,
`41-r15`, `41-r16`). Como (a) y (c) fallan, **R-09 no se satisface** y `nyquist_compliant` se queda
en `false`. El resultado es honesto y no se maquilla: dos de esas tres correcciones existen porque
el propio planner de esta fase declaró un denominador mal sumado, y la tercera porque escribió un
gate que su propio workflow de ejecución invalida. Una fase cuyo contrato de verificación tuvo que
ser reparado por su auditor no es Nyquist-compliant, aunque el auditor sea ella misma —
especialmente si el auditor es ella misma.

Veredicto de auditoría: **Phase 41 queda PARTIAL** — status draft → validated,
nyquist_compliant sigue en false.
