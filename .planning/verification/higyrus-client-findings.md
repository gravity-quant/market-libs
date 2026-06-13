# Findings: higyrus-client-client

## Run Context (ART)
- Timestamp: 2026-06-13T17:40:30.842321+00:00
- Resolved base URL / env: https://becerra.aunesa.com/Irmo
- Run params: `HIGYRUS_SAMPLE_CUENTA=5208`, `HIGYRUS_SAMPLE_TIPO_CUENTA="Comitentes y propias"`, `HIGYRUS_SAMPLE_NIVEL="Global"` (pasados explícito por CLI — ver setup gotcha en 04-02 SUMMARY)
- Market hours note: <abierto|cerrado — no aplica a este run; ningún endpoint sesión-dependiente verificado>

<!-- Clases (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT -->
<!-- Estados (D-08): OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX). Sin campo de severidad. -->

## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|
| F-01 | SHAPE | both | EXPECTED |
| F-02 | NO-DATA | both | NO-FIX |

## Detalle por hallazgo

### F-01 -- .posicion.disponibleAjustado: model declara, wire no emite (documentado FCI-conditional)

**Class:** `SHAPE` . **Surface:** `both` . **Status:** `EXPECTED`

- **Expected:** model y wire coinciden en el set de claves
- **Actual:** `disponibleAjustado` ausente en wire bajo `.posicion` (cuenta 5208 sin posiciones FCI con `irmo.fci.rescate_estadoSolicitudesAdescontar` activo); `SafeModel.from_api()` sustituye default tipado `0.0` per design
- **Diff:** key `disponibleAjustado` ausente en wire (model: `Posicion.disponibleAjustado: float`)
- **Resolution:** Documented behavior per `Posicion` docstring (`packages/higyrus-client/src/higyrus_client/models.py:197-199`): "The `disponibleAjustado` field is only populated for FCI instruments when the Higyrus parameter `irmo.fci.rescate_estadoSolicitudesAdescontar` is active; if absent, the safe-access default (`0.0`) is used." Closure: SafeModel safe-access es by-design. Polish futuro candidato: upgrade a `disponibleAjustado: float | None = None` para distinguir explícitamente "no FCI active" de "valor cero real" (no en scope de Phase 4).

### F-02 -- get_listado_cuentas(estado="alta") devuelve 0 cuentas (era 8771 en smoke pre-fase)

**Class:** `NO-DATA` . **Surface:** `both` . **Status:** `NO-FIX`

- **Expected:** ~8771 cuentas (count observado en el smoke test previo a Phase 4 con misma .env)
- **Actual:** lista vacía `[]` (HTTP 200), consistente en 3 runs consecutivos del driver post-fase-4 sobre ambas surfaces (sync + async)
- **Diff:** mismo endpoint `/api/cuentas/listadoCuentas?estado=alta`, mismo Bearer token, misma credencial, mismo `HIGYRUS_BASE_URL` — sin embargo el primer smoke test (pre-fase-4) devolvió 8771 cuentas. Causa raíz no determinada en scope de Phase 4: hipótesis abiertas (a) session-mutating side effect del flujo login_sync+login_async consecutivo del driver, (b) rate-limit silencioso post-smoke (Higyrus throttle), (c) cambio real de permisos del user / scope del token entre runs, (d) bug server-side que devuelve `[]` en vez de la lista esperable. No es bloqueante: el driver acepta `HIGYRUS_SAMPLE_CUENTA` override per D-HIGY-11 y los 6 endpoints cuenta-dependientes se ejercitan correctamente con la cuenta `5208`.
- **Resolution:** Phase 9 Plan 09-02 BUG-02 quick triage (bucket a — NO-FIX, account-state-conditional): re-corrido `main_higyrus.py` N=3 post-Phase-8 D-01 RetryTransport consistente — `get_listado_cuentas(estado="alta")` devuelve `[]` 3/3 sobre ambas surfaces, mientras `get_movimientos` (139 items), `get_posicion_valuada` (390 items) y `get_posiciones` (76 items) devuelven data sobre la misma sesión y cuenta operacional. El envelope server-side es `HTTP 200` válido con body vacío legítimo — la cuenta del operador no tiene cuentas con `estado="alta"` accesibles vía el token actual. Phase 8 D-01 RetryTransport amortigua transients hipotéticos. Hipótesis pre-existentes (a) session-mutating side effect y (b) rate-limit silencioso descartadas por consistencia 3/3 y por la actividad de los demás endpoints; hipótesis (c) cambio real de permisos / scope del token es la más alineada con la evidencia. El happy-path contract guard `test_get_listado_cuentas_url_con_estado_alta` (existing) preserva regresiones client-side futuras del parsing path.
- **Regression:** `packages/higyrus-client/tests/test_client.py::test_get_listado_cuentas_url_con_estado_alta`

<!-- evidence
Phase 9 Plan 09-02 BUG-02 triage — N=3 runs, run logs at /tmp/main_higyrus_phase9_run{1,2,3}.log

Run 1: PROBE get_listado_cuentas_sync:  PASS 0 cuentas
       PROBE get_listado_cuentas_async: PASS 0 cuentas
       PROBE get_movimientos_sync:      PASS 139 items
       PROBE get_posicion_valuada_sync: PASS 390 items
       PROBE get_posiciones_sync:       PASS 76 items
Run 2: idem (3/3 consistent)
Run 3: idem (3/3 consistent)

SUMMARY 3/3: PASS=16 FAIL=0 SKIPPED=2 FINDING=1 (F-01 pre-existing)

Triage executed by orchestrator on behalf of operator (sebadlf authorized
bucket (a) NO-FIX). Driver shim drift surfaced during triage and repaired
in same wave: fix(higyrus): legacy shim — forward _base_url + add
aio._ensure_http_client wrapper (Phase 6 migration drift).
-->


## Cycle Closure

**Cycle ID:** `verification-cycle-2026-Q2`
**Closure date:** 2026-06-10T01:10:32+00:00
**Packages verified in this cycle:** 4 (ambito-financiero-client, iol-client, higyrus-client, matriz-client)

### Findings by status (this package)

| OPEN | CONFIRMED | FIXED | EXPECTED | NO-FIX | Total |
|------|-----------|-------|----------|--------|-------|
| 0 | 0 | 0 | 1 | 1 | 2 |

*(Phase 9 Plan 09-02 BUG-02 triage flipped F-02: OPEN → NO-FIX.)*

### Regression tests linked to FIXED/CONFIRMED findings

*(historical findings predate the regression-link convention introduced in Phase 5; see [CYCLE-REPORT.md](./CYCLE-REPORT.md) "Open questions" for downstream milestone caveat)*

### Cycle validation

`verify_cycle_closure("higyrus-client")` returned: **PASS**

---

See [CYCLE-REPORT.md](./CYCLE-REPORT.md) for the consolidated cross-package report.
