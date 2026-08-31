---
phase: 41
slug: validaci-n-nyquist-retroactiva-de-v1-7
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-08-31
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
| 41-02-01 | 02 | 2 | NYQ-01 | — / — | Las 12 filas reales de la Phase 35 se reconstruyen desde sus 5 planes; la placeholder sobrevive marcada | bash | `test "$(grep -h -c '<automated>' $D/35-0*-PLAN.md \| paste -sd+ - \| bc)" -eq 12 && test "$(grep -c '^\| 35-0[1-5]-0[1-3] ' $D/35-VALIDATION.md)" -eq 12 && grep -q 'filled by planner' $D/35-VALIDATION.md && git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` | ✅ | ⬜ pending |
| 41-02-02 | 02 | 2 | NYQ-01 | T-41-03 / mitigate | Las 13 filas de la Phase 35 quedan dispuestas exactamente una vez; front-matter transformado sin flipear el flag | bash | `test "$N" -eq 13 && test $((S+H+R)) -eq 13 && grep -q '^status: validated' $F && grep -q '^nyquist_compliant: false' $F && grep -q '^not_verifiable_retroactively: 0' $F && grep -q '37a83fe6…' $F && grep -q 'Cero archivos de test nuevos; cero escalaciones.' $F` (cadena completa: `41-02-PLAN.md` Task 2) | ✅ | ⬜ pending |
| 41-03-01 | 03 | 2 | NYQ-01 | — / — | Las 11 filas de la Phase 36 re-corren verdes; la fila sin comando declarado (`36-r11`) se resuelve contra un lock enrolado en CI | pytest+bash | `uv run pytest packages/market-data-client/tests/test_market_data_chain.py -x -q && uv run pytest verification/test_main_market_data_deep_chain.py -q && uv run python tools/check_decode_intactness.py && grep -q 'verification/test_main_market_data_deep_chain.py' .github/workflows/ci.yml && git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` | ✅ | ⬜ pending |
| 41-03-02 | 03 | 2 | NYQ-01 | T-41-03 / mitigate | Las 11 filas de la Phase 36 quedan dispuestas exactamente una vez; front-matter transformado | bash | `test "$(X \| wc -l)" -eq 11 && test "$((VN+VH+NVR))" -eq 11 && grep -q '^status: validated' $F && grep -q '^nyquist_compliant: false' $F && grep -q '^not_verifiable_retroactively: 0' $F && grep -q '37a83fe6…' $F` (cadena completa: `41-03-PLAN.md` Task 2) | ✅ | ⬜ pending |
| 41-04-01 | 04 | 2 | NYQ-01 | — / — | Las 14 filas de la Phase 37 re-corren verdes; el selector `-k alias_surfaces` (0 seleccionados) se re-apunta leyendo el cuerpo del sustituto | pytest+static | `uv run pytest packages/matriz-client/tests/test_surface_types_red.py -q && uv run pytest packages/matriz-client/tests/test_null_object.py -k "rest_parsed_snapshot or ws_frame_parsed_snapshot" -q && uv run mypy packages/matriz-client/src && git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` | ✅ | ⬜ pending |
| 41-04-02 | 04 | 2 | NYQ-01 | T-41-03 / mitigate | Las 14 filas de la Phase 37 quedan dispuestas exactamente una vez; front-matter transformado | bash | `test "$(X \| wc -l)" -eq 14 && test "$((VN+VH+NVR))" -eq 14 && grep -q '^status: validated' $F && grep -q '^nyquist_compliant: false' $F && grep -q '^not_verifiable_retroactively: 0' $F && grep -q '37a83fe6…' $F` (cadena completa: `41-04-PLAN.md` Task 2) | ✅ | ⬜ pending |
| 41-05-01 | 05 | 2 | NYQ-01 | T-41-01 / mitigate | Las 7 filas automatizadas de la Phase 38 re-corren verdes y `regen_snapshots.py` deja el árbol limpio; las 2 de revisión reúnen su evidencia fechada | pytest+static+snapshot | `uv run pytest packages/iol-client/tests/test_models.py -k "puntas or round_trip" -q && uv run mypy packages/iol-client && uv run python verification/regen_snapshots.py && test -z "$(git status --porcelain)" && test -f …/38-CENSUS.md && grep -q 'human_verification' …/38-VERIFICATION.md && git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` | ✅ | ⬜ pending |
| 41-05-02 | 05 | 2 | NYQ-01 | T-41-03 / mitigate | Las 9 filas de la Phase 38 quedan dispuestas 7 VN / 2 VH / 0 NVR con 3 filas NOT ENFORCED nombradas | bash | `test "$(X \| wc -l)" -eq 9 && test "$(X \| grep -c 'VERIFIED-NOW')" -eq 7 && test "$(X \| grep -c 'VERIFIED-HISTORICALLY')" -eq 2 && test "$(X \| grep -c 'NOT ENFORCED')" -eq 3 && grep -q '^status: validated' $F && grep -q '^not_verifiable_retroactively: 0' $F` (cadena completa: `41-05-PLAN.md` Task 2) | ✅ | ⬜ pending |
| 41-06-01 | 06 | 2 | NYQ-01 | T-41-01 / mitigate | Las 10 filas automatizadas de la Phase 39 re-corren verdes; el selector `-k allowlist` se re-apunta; las 5 no automatizadas reúnen su evidencia parcial | pytest+manual | `uv run pytest verification/test_main_verify_classification.py verification/test_main_matriz_skip_line_shape.py verification/test_main_higyrus_skip_line_shape.py verification/test_cycle_closure_phase33.py verification/test_main_iol_deep_chain.py verification/test_main_higyrus_deep_chain.py verification/test_main_matriz_deep_chain.py -q && uv run pytest packages/matriz-client/tests/test_instruments_flat_identifier_shape.py -q && test -f …/39-CENSUS.md && test "$(ls .planning/verification/run-evidence/*.json \| wc -l)" -eq 4` | ✅ | ⬜ pending |
| 41-06-02 | 06 | 2 | NYQ-01 | T-41-03 / mitigate | Las 15 filas de la Phase 39 quedan 10 VN / 1 VH / 4 NVR, con `not_verifiable_retroactively: 4` como marcador del criterio 3b | bash | `test "$(X \| wc -l)" -eq 15 && test "$(X \| grep -c 'VERIFIED-NOW')" -eq 10 && test "$(X \| grep -c 'VERIFIED-HISTORICALLY')" -eq 1 && test "$(X \| grep -c 'NOT-VERIFIABLE-RETROACTIVELY')" -eq 4 && grep -q '^not_verifiable_retroactively: 4' $F` (cadena completa: `41-06-PLAN.md` Task 2) | ✅ | ⬜ pending |
| 41-07-01 | 07 | 3 | NYQ-01 | T-41-03 / mitigate | La aritmética del criterio 2 cierra (62 = 54 VN + 4 VH + 4 NVR), ningún flag quedó en `true`, ninguna celda es vacuamente verde | bash | bucle sobre `35..39`: `test $((a+b+d)) -eq $c` por fase · `grep 'deselected' \| grep -vc 'passed'` == 0 · `grep -q '^status: validated'` · `grep -q '^nyquist_compliant: true' && exit 1` · `test $T -eq 62 && test $VN -eq 54 && test $VH -eq 4 && test $NVR -eq 4` (cadena completa: `41-07-PLAN.md` Task 1) | ✅ | ⬜ pending |
| 41-07-02 | 07 | 3 | NYQ-01 | T-41-SC / accept | Criterio 4 (cero locks inertes: 52 archivos, `verification/` limpio) y criterio 5 (contención: `ci.yml` y `REQUIREMENTS.md` intactos, exactamente 5+1 VALIDATION.md tocados) | bash | `test -z "$(git status --porcelain verification/)" && test "$(ls verification/test_*.py \| wc -l)" -eq 52 && git diff --quiet $H HEAD -- .github/workflows/ci.yml && git diff --quiet $H HEAD -- .planning/REQUIREMENTS.md && grep -Fq 'NYQUIST-32-33' .planning/REQUIREMENTS.md && test "$(git diff --name-only $H HEAD \| grep -c 'v1\.7-phases/3[5-9]-.*-VALIDATION\.md')" -eq 5` (cadena completa: `41-07-PLAN.md` Task 2) | ✅ | ⬜ pending |
| 41-07-03 | 07 | 3 | NYQ-01 | T-41-03 / mitigate | La propia Phase 41 se auto-dispone con la misma vara (D-10): sección de auditoría, `status: validated`, filas dispuestas exactamente una vez | bash | `grep -q '^## Validation Audit 2026-08-31' $V && grep -q '^status: validated' $V && grep -qE '^not_verifiable_retroactively: [0-9]+' $V && grep -q '^audited_commit_sha: 37a83fe6…' $V && test "$(printf '%s\n' "$R" \| grep -c .)" -eq 16 && test -z "$(git status --porcelain)"` (cadena completa: `41-07-PLAN.md` Task 3; ver nota del denominador 16) | ✅ | ⬜ pending |

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

**Approval:** pending

> **Nota de auto-disposición (D-10):** el `status` y el `nyquist_compliant` de **este** archivo se
> dejan deliberadamente en `draft` / `false`. La Phase 41 se sostiene con la misma vara que las cinco
> que audita: su propia disposición se escribe en `41-07` Task 3, con evidencia re-ejecutada, no
> aquí. Cerrar las Wave 0 gaps no es lo mismo que estar validada.
