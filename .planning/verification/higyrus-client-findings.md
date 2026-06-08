# Findings: higyrus-client-client

## Run Context (ART)
- Timestamp: 2026-06-08T02:03:51.811734+00:00
- Resolved base URL / env: https://becerra.aunesa.com/Irmo
- Run params: `HIGYRUS_SAMPLE_CUENTA=5208`, `HIGYRUS_SAMPLE_TIPO_CUENTA="Comitentes y propias"`, `HIGYRUS_SAMPLE_NIVEL="Global"` (pasados explícito por CLI — ver setup gotcha en 04-02 SUMMARY)
- Market hours note: <abierto|cerrado — no aplica a este run; ningún endpoint sesión-dependiente verificado>

<!-- Clases (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT -->
<!-- Estados (D-08): OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX). Sin campo de severidad. -->

## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|
| F-01 | SHAPE | both | EXPECTED |
| F-02 | NO-DATA | both | OPEN |

## Detalle por hallazgo

### F-01 -- .posicion.disponibleAjustado: model declara, wire no emite (documentado FCI-conditional)

**Class:** `SHAPE` . **Surface:** `both` . **Status:** `EXPECTED`

- **Expected:** model y wire coinciden en el set de claves
- **Actual:** `disponibleAjustado` ausente en wire bajo `.posicion` (cuenta 5208 sin posiciones FCI con `irmo.fci.rescate_estadoSolicitudesAdescontar` activo); `SafeModel.from_api()` sustituye default tipado `0.0` per design
- **Diff:** key `disponibleAjustado` ausente en wire (model: `Posicion.disponibleAjustado: float`)
- **Resolution:** Documented behavior per `Posicion` docstring (`packages/higyrus-client/src/higyrus_client/models.py:197-199`): "The `disponibleAjustado` field is only populated for FCI instruments when the Higyrus parameter `irmo.fci.rescate_estadoSolicitudesAdescontar` is active; if absent, the safe-access default (`0.0`) is used." Closure: SafeModel safe-access es by-design. Polish futuro candidato: upgrade a `disponibleAjustado: float | None = None` para distinguir explícitamente "no FCI active" de "valor cero real" (no en scope de Phase 4).

### F-02 -- get_listado_cuentas(estado="alta") devuelve 0 cuentas (era 8771 en smoke pre-fase)

**Class:** `NO-DATA` . **Surface:** `both` . **Status:** `OPEN`

- **Expected:** ~8771 cuentas (count observado en el smoke test previo a Phase 4 con misma .env)
- **Actual:** lista vacía `[]` (HTTP 200), consistente en 3 runs consecutivos del driver post-fase-4 sobre ambas surfaces (sync + async)
- **Diff:** mismo endpoint `/api/cuentas/listadoCuentas?estado=alta`, mismo Bearer token, misma credencial, mismo `HIGYRUS_BASE_URL` — sin embargo el primer smoke test (pre-fase-4) devolvió 8771 cuentas. Causa raíz no determinada en scope de Phase 4: hipótesis abiertas (a) session-mutating side effect del flujo login_sync+login_async consecutivo del driver, (b) rate-limit silencioso post-smoke (Higyrus throttle), (c) cambio real de permisos del user / scope del token entre runs, (d) bug server-side que devuelve `[]` en vez de la lista esperable. No es bloqueante: el driver acepta `HIGYRUS_SAMPLE_CUENTA` override per D-HIGY-11 y los 6 endpoints cuenta-dependientes se ejercitan correctamente con la cuenta `5208`.
- **Resolution:** OPEN — investigación deferida fuera de scope de Phase 4. Candidato para polish post-milestone: reproducir el discrepancy con un script aislado que loguee headers + body sobre múltiples corridas, contactar a Higyrus support si reproducible, o aceptar como `NO-FIX (account-state-conditional)` si no se puede repro.
