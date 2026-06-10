---
phase: 05-matriz-verification
plan: 03
subsystem: testing
tags: [verification, matriz-client, live-run, verified-live, mock-only-mutation, MATZ-06, GET-as-write, sentinel, schema-snapshot, remarkets, findings]

requires:
  - phase: 05-matriz-verification
    provides: "Plan 05-01 helpers (diff_safemodel_bidirectional, verify_cycle_closure), envelope _unwrap, _token raise, §6.3 docstrings; Plan 05-02 driver main_matriz.py con ~25 probes D-MATZ-29 y cycle_closure × 4 pkgs"
provides:
  - "# ------ Verified live (Phase 5) ------ section en test_client.py: 12 invariantes mockeados (URLs verbatim + envelope unwrap + market-hours guard sentinel + 3 MATZ-05 error mapping tests)"
  - "# ------ MATZ-06 mock-only contract ------ section: 11 tests (5 new_order + 1 replace_order + 1 cancel_order + 3 sentinels GET-as-write quirk §6.3) — mock-only por diseño (REQUIREMENTS.md Out of Scope para live)"
  - "Live run real contra https://api.remarkets.primary.com.ar (sandbox): PASS=17, FAIL=0, SKIPPED=9 (account/ID-scoped opcionales sin credenciales), FINDING=2 emisores producieron 9 entradas F-01..F-09 + 2 EXPECTED terminales D-MATZ-27 (F-02/F-10)"
  - "matriz-client-findings.md poblado con 10 entradas clasificadas (1 NO-FIX NO-DATA + 6 NO-FIX SHAPE wire-superset + 2 EXPECTED prod-vs-remarkets + 1 CONFIRMED ERROR-MAP)"
  - "8 schemas committeables (PII-free, envelope D-21) en .planning/verification/schemas/matriz-client/"
  - "cycle_closure × 4 pkgs PASS (ambito, iol, higyrus, matriz) — verifica que todos los CONFIRMED/FIXED históricos linkean a regression tests existentes"
  - "matriz-client tests totales: 112 (101 pre + 23 nuevos Phase 5: Verified-live + MATZ-06); repo total: 273 passed"
affects: [05-04, cycle-closure, drift-02-validation, future-matriz-changes]

tech-stack:
  added: []
  patterns:
    - "Mock-only contract: MATZ-06 (mutations) nunca tocan live por diseño — ejercitado vía httpx_mock con URL verbatim + envelope key + method assertion"
    - "Verified-live invariants: tests mockeados que reflejan exactamente lo que el live run ejercita (URL completa con query string verbatim + envelope unwrap + error shape) — sirve de safety net para refactors futuros"
    - "GET-as-write sentinel: 3 tests con docstring §6.3 + request.method == 'GET' asserts que bloquean cualquier refactor accidental GET→POST"
    - "Findings classification (operator-driven, Phase 5): cada OPEN se transiciona manualmente a CONFIRMED (fix+regression en Plan 05-04) / NO-FIX (server-side o tolerated by SafeModel) / EXPECTED (gap conocido terminal)"

key-files:
  created:
    - ".planning/verification/matriz-client-findings.md"
    - ".planning/verification/schemas/matriz-client/get-all-instruments.json"
    - ".planning/verification/schemas/matriz-client/get-instrument-detail.json"
    - ".planning/verification/schemas/matriz-client/get-instruments-by-cfi-esxxxx.json"
    - ".planning/verification/schemas/matriz-client/get-instruments-by-segment.json"
    - ".planning/verification/schemas/matriz-client/get-instruments-details.json"
    - ".planning/verification/schemas/matriz-client/get-market-data.json"
    - ".planning/verification/schemas/matriz-client/get-segments.json"
    - ".planning/verification/schemas/matriz-client/get-trades.json"
  modified:
    - "packages/matriz-client/tests/test_client.py (+442 líneas, +23 tests: Verified-live × 12 + MATZ-06 mock-only × 11)"
    - ".gitignore (entry para live-run-matriz-*.log — operator-only artifacts)"

key-decisions:
  - "F-01 (NO-DATA, símbolo ilíquido) → NO-FIX: condición de mercado en sandbox remarkets, no bug del cliente. Sin regression."
  - "F-02 + F-10 (SHAPE, prod-vs-remarkets) → EXPECTED terminal D-MATZ-27: ámbito del milestone limitado a remarkets por safety policy (REQUIREMENTS.md Out of Scope). F-10 es duplicado emitido por el driver — observación menor, candidato a dedupe opcional."
  - "F-03..F-08 (SHAPE, 6 findings: instrument_detail wire emite securityIdSource/securityType/settlType/strike/symbol/underlying que el model ignora) → NO-FIX bloque: SafeModel.from_api tolera wire-superset por diseño; extender el model es opcional y se aplaza."
  - "F-09 (ERROR-MAP, get_instruments_by_cfi con CFI inválido NO levantó PrimaryAPIError) → CONFIRMED: gap real. Fix + regression test serán entregados en Plan 05-04. Hasta entonces cycle_closure_matriz_client quedará FAIL en el próximo run — esa señal es justamente la que cierra DRIFT-02."
  - "Schemas committeados sólo 8 (no 11-19) porque los probes account/ID-scoped requieren PRIMARY_ACCOUNT y MATRIZ_SAMPLE_* env vars opt-in que el operator no tenía configurados — rango inferior aceptable per Assumption A4."

patterns-established:
  - "Verified-live URL-verbatim: cada test mockeado de la sección Phase 5 declara la URL completa con query string exacto (e.g., '?marketId=ROFX&securityId=…') para detectar cambios accidentales en el path o en los query params del cliente"
  - "Operator-driven classification workflow: live run → findings OPEN auto-generados → checkpoint human-verify → operator clasifica via AskUserQuestion → orchestrator persiste con rationale → commit"
  - "Schema envelope D-21: {endpoint, client_function, captured_at, base_url, sample_params, schema} con `schema_of` recursivo emitiendo solo nombres de tipo ('str', 'int', 'float', 'bool', list[X], dict[str,X]) — nunca valores reales, PII-free por construcción"

requirements-completed: [MATZ-01, MATZ-02, MATZ-05, MATZ-06, MATZ-07, DRIFT-02]

duration: "~40 min (Tasks 3.1+3.2 autómatos ~7 min en agent + live run ~3s + clasificación operator ~30 min)"
completed: 2026-06-09
---

# Phase 5 Plan 03: Live run + Verified-live + mock-only Summary

**Live run contra remarkets PASS=17/FAIL=0/SKIPPED=9/FINDING=2; suite mockeada Phase 5 lockea 12 invariantes Verified-live + 11 MATZ-06 mock-only contract con 3 sentinels GET-quirk §6.3; cycle_closure × 4 pkgs PASS confirma DRIFT-02 helper promotion funcionando end-to-end**

## Performance

- **Duration:** ~40 min (executor agent ~7 min, live run ~3s, operator classification + audit ~30 min)
- **Started:** 2026-06-09T22:55Z
- **Completed:** 2026-06-09T23:35Z
- **Tasks:** 3
- **Files modified:** 1 test file (+442 líneas, +23 tests); 1 findings file new; 8 schema snapshots new; 1 .gitignore update

## Accomplishments

- **Verified-live section locked** (12 tests, +260 líneas): URL invariants exactos para 8 endpoints + market-hours sentinel + 3 tests MATZ-05 error mapping verificando `PrimaryAPIError(status='ERROR')`
- **MATZ-06 mock-only contract locked** (11 tests, +182 líneas): 5 new_order (baseline, MARKET, iceberg, GTD, cancelPrevious) + 1 replace_order + 1 cancel_order + 3 sentinels `request.method == "GET"` con docstring `§6.3 ... Never refactor to POST without explicit API confirmation`
- **Live run real contra sandbox remarkets** ejecutado por el operator: 17 probes PASS, 0 FAIL, 9 SKIPPED (account/ID-scoped opcionales), 2 FINDING-producing probes → 10 entradas F-01..F-10
- **cycle_closure × 4 pkgs PASS** — el helper `verify_cycle_closure` promovido en Plan 05-01 confirma que todos los CONFIRMED/FIXED históricos de ámbito/iol/higyrus/matriz linkean a regression tests existentes (DRIFT-02 funcionando)
- **8 schema snapshots committeables capturados** con envelope D-21 (PII-free): get-all-instruments, get-instrument-detail, get-instruments-by-cfi-esxxxx, get-instruments-by-segment, get-instruments-details, get-market-data, get-segments, get-trades
- **Findings classification completada** (operator-driven): 1 NO-FIX (NO-DATA), 6 NO-FIX (SHAPE wire-superset), 2 EXPECTED (prod-vs-remarkets terminal D-MATZ-27), 1 CONFIRMED (F-09 ERROR-MAP — handoff a Plan 05-04)

## Task Commits

Each task was committed atomically (Tasks 3.1 + 3.2 por agente en worktree merged a main; Task 3.3 completado desde main per workflow pattern de checkpoint human-verify):

1. **Task 3.1: Verified-live (Phase 5) section** — `b9db0a5` (test): URL invariants + market-hours sentinel + MATZ-05 error mapping (+260 líneas, +12 tests)
2. **Task 3.2: MATZ-06 mock-only contract** — `94b7950` (test): 5 new_order + 1 replace + 1 cancel + 3 sentinels GET-quirk §6.3 (+182 líneas, +11 tests)
3. **Task 3.3: Live run + classification** — `747a77d` (feat): findings classified + 8 schemas captured + `.gitignore` para `live-run-matriz-*.log`

**Plan metadata:** (este commit)

## Files Created/Modified

- `packages/matriz-client/tests/test_client.py` — appended 2 new sections; 23 nuevos tests; matriz-client total 112 (was 89 pre Plan 05; +19 Plan 05-01 + 23 Plan 05-03 = 112)
- `.planning/verification/matriz-client-findings.md` — new (10 entradas F-01..F-10 con clasificación + rationale)
- `.planning/verification/schemas/matriz-client/*.json` — 8 new (PII-free, envelope D-21)
- `.gitignore` — entry `live-run-matriz-*.log` (operator-only artifacts)

## Decisions Made

- **F-09 → CONFIRMED with deferred regression**: el fix + regression test van en Plan 05-04 cycle closure. Hasta que se agreguen, `cycle_closure_matriz_client` queda FAIL en el próximo run — esa señal es justamente la que cierra DRIFT-02 (validamos que el ciclo detecta el gap automáticamente).
- **F-03..F-08 NO-FIX bloque**: SafeModel.from_api tolera wire-superset por diseño. Si futura app necesita exponer alguno de estos campos, se extiende el model en ese momento — la verificación no lo bloquea.
- **F-10 duplicado de F-02 (D-MATZ-27 emitido dos veces)** no se corrige en este plan: es observación menor, candidato a dedupe opcional del `append_finding` en futuras iteraciones del driver.
- **8 schemas vs 11-19 rango esperado**: el operator no tenía `PRIMARY_ACCOUNT` ni `MATRIZ_SAMPLE_*` configurados, por lo que 9 probes opcionales quedaron SKIPPED. Per Assumption A4 (RESEARCH L981), el rango inferior es aceptable.

## Deviations from Plan

None — plan ejecutado según spec. Las únicas decisiones operator-driven fueron las clasificaciones de findings (esperadas por el checkpoint human-verify) y el agregado de `.gitignore` para los `live-run-matriz-*.log` (operator-only, never commit).

## Issues Encountered

- **Driver emite D-MATZ-27 EXPECTED terminal dos veces** (F-02 al inicio del run + F-10 al cierre del cycle_closure block) — no afecta funcionalidad pero es ruido en el findings file. Candidato a fix en próxima iteración del `main_matriz.py` (no es Phase 5 scope).

## User Setup Required

None — no external service configuration required. Las credenciales `PRIMARY_USER/PRIMARY_PASSWORD/PRIMARY_BASE_URL` ya estaban configuradas en `packages/matriz-client/.env` (gitignored, operator-managed).

## Next Phase Readiness

**Plan 05-04 (cycle closure) está completamente desbloqueado:**

- `matriz-client-findings.md` tiene F-09 CONFIRMED esperando regression en Plan 05-04
- `cycle_closure × 4 pkgs` funcionando — Plan 05-04 solo necesita agregar la sección `## Cycle Closure` por paquete + `CYCLE-REPORT.md` consolidado
- 8 schemas committeados sirven de baseline para próximos drift runs
- Todos los CONFIRMED/FIXED históricos (ámbito/iol/higyrus) ya linkean a regression tests existentes — verificado por `verify_cycle_closure` en este live run

**Blocker conocido (acordado):** el próximo run de `main_matriz.py` reportará `cycle_closure_matriz_client: FAIL` hasta que Plan 05-04 agregue la regression test para F-09 — ese es el comportamiento esperado y la señal que cierra DRIFT-02.

---
*Phase: 05-matriz-verification*
*Plan: 03*
*Completed: 2026-06-09*
