# Findings: matriz-client-client

## Run Context (ART)
- Timestamp: 2026-06-10T01:01:55.430560+00:00
- Resolved base URL / env: https://api.remarkets.primary.com.ar
- Market hours note: <abierto|cerrado — afecta paths sesión-dependientes>

<!-- Clases (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT -->
<!-- Estados (D-08): OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX). Sin campo de severidad. -->

## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|
| F-01 | NO-DATA | sync | NO-FIX |
| F-02 | SHAPE | sync | EXPECTED |
| F-03 | SHAPE | sync | NO-FIX |
| F-04 | SHAPE | sync | NO-FIX |
| F-05 | SHAPE | sync | NO-FIX |
| F-06 | SHAPE | sync | NO-FIX |
| F-07 | SHAPE | sync | NO-FIX |
| F-08 | SHAPE | sync | NO-FIX |
| F-09 | ERROR-MAP | sync | CONFIRMED |
| F-10 | SHAPE | sync | EXPECTED |

## Detalle por hallazgo

### F-01 -- no trades for SOJ.ROS/NOV26 308 P in last 7 days

**Class:** `NO-DATA` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** al menos 1 trade en ventana de 7 días (símbolo líquido)
- **Actual:** trades list vacía
- **Diff:** símbolo ilíquido o ventana sin actividad
- **Classification rationale (Phase 5):** NO-DATA es condición de mercado (símbolo poco operado en sandbox remarkets), no bug del cliente. `get_trades` retorna `[]` correctamente y el contrato wire→model se ejercita igual. Sin fix ni regression.

### F-02 -- prod-vs-remarkets divergence acknowledged

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** verification limited to remarkets sandbox by safety policy (REQUIREMENTS.md Out of Scope)
- **Actual:** prod (api.primary.com.ar) shape unverified; sandbox shape committed in .planning/verification/schemas/matriz-client/
- **Diff:** N/A (acknowledged limitation, not detected drift)

### F-03 -- .instrument_detail.securityIdSource: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `securityIdSource` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Classification rationale (Phase 5):** `SafeModel.from_api` tolera wire-superset por diseño — campos extra del backend se ignoran sin romper deserialization. Sin fix ni regression. Si en el futuro la app necesita exponer alguno, se extiende el model en ese momento.

### F-04 -- .instrument_detail.securityType: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `securityType` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Classification rationale (Phase 5):** Mismo principio que F-03 — wire-superset tolerado por `SafeModel.from_api`.

### F-05 -- .instrument_detail.settlType: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `settlType` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Classification rationale (Phase 5):** Mismo principio que F-03 — wire-superset tolerado por `SafeModel.from_api`.

### F-06 -- .instrument_detail.strike: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `strike` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Classification rationale (Phase 5):** Mismo principio que F-03 — wire-superset tolerado por `SafeModel.from_api`.

### F-07 -- .instrument_detail.symbol: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `symbol` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Classification rationale (Phase 5):** Mismo principio que F-03 — wire-superset tolerado por `SafeModel.from_api`.

### F-08 -- .instrument_detail.underlying: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `underlying` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Classification rationale (Phase 5):** Mismo principio que F-03 — wire-superset tolerado por `SafeModel.from_api`.

### F-09 -- get_instruments_by_cfi con CFI inválido NO levantó excepción

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `CONFIRMED`

- **Expected:** PrimaryAPIError mapeado para CFI inválido
- **Actual:** ninguna excepción; el cliente retornó normalmente
- **Diff:** upstream aceptó CFI no válido; revisar validación
- **Classification rationale (Phase 5):** Gap real en el error mapping del cliente. El contrato espera `PrimaryAPIError` para CFI mal formado; el cliente lo deja pasar silenciosamente. Fix + regression test serán entregados en **Plan 05-04 cycle closure** (DRIFT-02). Hasta que se agregue, `cycle_closure_matriz_client` quedará FAIL en el próximo run — esa señal es justamente la que cierra el ciclo.

### F-10 -- prod-vs-remarkets divergence acknowledged

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** verification limited to remarkets sandbox by safety policy (REQUIREMENTS.md Out of Scope)
- **Actual:** prod (api.primary.com.ar) shape unverified; sandbox shape committed in .planning/verification/schemas/matriz-client/
- **Diff:** N/A (acknowledged limitation, not detected drift)
