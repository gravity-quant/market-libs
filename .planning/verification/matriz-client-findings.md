# Findings: matriz-client-client

## Run Context (ART)
- Timestamp: 2026-08-30T02:41:27.293177+00:00
- Resolved base URL / env: https://api.bbsa.matrizoms.com.ar
- Market hours note: <abierto|cerrado — afecta paths sesión-dependientes>

<!-- Clases (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT -->
<!-- Estados (D-08): OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX). Sin campo de severidad. -->

<!-- BEGIN AUTO-GENERATED -->
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
| F-09 | ERROR-MAP | sync | FIXED |
| F-10 | SHAPE | sync | EXPECTED |
| F-11 | SHAPE | sync | NO-FIX |
| F-12 | SHAPE | sync | NO-FIX |
| F-13 | NO-DATA | sync | OPEN |
| F-14 | ERROR-MAP | sync | OPEN |
| F-15 | ERROR-MAP | sync | OPEN |
| F-16 | ERROR-MAP | sync | OPEN |
| F-17 | SHAPE | sync | OPEN |
| F-18 | SHAPE | sync | OPEN |
| F-19 | SHAPE | sync | OPEN |
| F-20 | SHAPE | sync | OPEN |
| F-21 | SHAPE | sync | OPEN |
| F-22 | SHAPE | sync | OPEN |
| F-23 | SHAPE | sync | OPEN |
| F-24 | SHAPE | sync | OPEN |
| F-25 | SHAPE | sync | OPEN |
| F-26 | SHAPE | sync | OPEN |
| F-27 | SHAPE | sync | OPEN |
| F-28 | SHAPE | sync | EXPECTED |
| F-29 | SHAPE | async | OPEN |
| F-30 | SHAPE | async | OPEN |
| F-31 | SHAPE | async | OPEN |
| F-32 | SHAPE | async | OPEN |
| F-33 | SHAPE | async | OPEN |
| F-34 | SHAPE | async | OPEN |
| F-35 | SHAPE | async | OPEN |
| F-43 | SHAPE | async | OPEN |
| F-44 | SHAPE | async | OPEN |
| F-63 | ERROR-MAP | async | OPEN |
| F-64 | ERROR-MAP | async | OPEN |
| F-65 | ERROR-MAP | async | OPEN |

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

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** PrimaryAPIError mapeado para CFI inválido
- **Actual:** ninguna excepción; el cliente retornó normalmente (pre-Phase 9)
- **Diff:** upstream aceptó CFI no válido; revisar validación
- **Regression:** `packages/matriz-client/tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code` (10 casos paramétricos cubriendo 3 buckets: literal-known x2, regex forward-compat x2, malformed x6 — hyphen/lowercase/digit/len5/len7/empty)
- **Classification rationale (Phase 5):** Gap real en el error mapping del cliente. El contrato espera `PrimaryAPIError` para CFI mal formado; el cliente lo deja pasar silenciosamente. Fix + regression test serán entregados en **Plan 05-04 cycle closure** (DRIFT-02). Hasta que se agregue, `cycle_closure_matriz_client` quedará FAIL en el próximo run — esa señal es justamente la que cierra el ciclo.
- **Resolution:** Phase 9 Plan 09-03 BUG-01 — hybrid Literal + ISO 10962 regex guard agregado pre-HTTP en `build_get_instruments_by_cfi_request` (`packages/matriz-client/src/matriz_client/_core.py:423-441`). Si `cfi_code in _CFI_LITERAL_VALUES` (frozenset derivado de `types.CFICode` via `get_args`) → pass (literal-known, 9 valores ISO 10962:2015). Si `_CFI_ISO_RE.match(cfi_code)` (regex `^[A-Z]{6}$`) → pass (forward-compat ISO 10962:2021 sin lib bump). Otherwise → `raise PrimaryAPIError(status="ERROR", description="CFI inválido: ...")`. Deviation D-02 vs ROADMAP literal `_core.raise_for_response()`: el guard vive en el builder porque `raise_for_response` solo ve `httpx.Response` y no ve el `cfi_code` param; el contrato observable (`PrimaryAPIError(status="ERROR")`) se preserva. Single-site fix (Phase 7 REFAC-03) — el cambio en `_core.py` propaga al transport shell `Client.get_instruments_by_cfi` automáticamente. matriz NO tiene `aio.py` REST aún (Phase 10 territory). Live re-run de `main_matriz.py` confirma `probe_error_malformed_cfi` reporta PASS post-fix; `cycle_closure_matriz_client` flipea FAIL → PASS (operator-driven evidence — ver 09-03 SUMMARY paste).

### F-10 -- prod-vs-remarkets divergence acknowledged

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** verification limited to remarkets sandbox by safety policy (REQUIREMENTS.md Out of Scope)
- **Actual:** prod (api.primary.com.ar) shape unverified; sandbox shape committed in .planning/verification/schemas/matriz-client/
- **Diff:** N/A (acknowledged limitation, not detected drift)

### F-11 -- DetailedPosition.report roster declarado desde vendor doc, nunca observado en vivo

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** `DetailedPosition.report` tipado `dict[str, dict[str, InstrumentPositionReport]]` (dos niveles de keys abiertas: contractType -> symbol). Roster declarado de `InstrumentPositionReport`: `instrumentInitialSize`, `instrumentFilledSize`, `instrumentCurrentSize` -- los tres escalares hermanos de `packages/matriz-client/documentation/Primary-API.md:1745-1747`, dentro de la muestra `GET /rest/risk/detailedPosition/REM7374` en `:1701-1791`. Procedencia: vendor-documented, UNMEASURED (D-04a, tercera clase) -- nunca presentado como captura.
- **Actual:** No existe observacion en vivo de este payload en ningun lado del repo. `.planning/verification/schemas/matriz-client/` tiene ocho schemas committeados (instruments, market data, segments, trades) y ninguno cubre los endpoints Risk; `grep -rn 'detailedPosition' .planning/verification/schemas/` no matchea. El roster y los tipos runtime salen del vendor doc committeado, no de la wire. Los subarboles diferidos por D-07 (`detailedPositions`, `:1710-1744`, ~21 campos por elemento, con su `detailedDailyDiff` de 8 campos en `:1733-1742`) llegan como divergencias `extra` no-fatales y quedan descartados del surface tipado.
- **Diff:** Causa bloqueante: LIVE-MATZ-33 -- el hostname assert D-MATZ-33 en `main_matriz.py:2548-2556` aborta cualquier corrida cuyo `base_url` no sea remarkets, y no fue bypasseado (T-37-16). Sin corrida en vivo no hay captura, y sin captura el roster no puede confirmarse ni corregirse en este ciclo. Destino nombrado: Phase 39 / LIVE-NOBJ-01, donde se mide el payload real y se ensancha o corrige el roster.

### F-12 -- AccountReport.detailedAccountReports roster declarado desde vendor doc, nunca observado en vivo

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** `AccountReport.detailedAccountReports` tipado `dict[str, DetailedAccountReport]` (UN nivel de keys abiertas, no dos -- la asimetria con `report` esta medida en 37-RESEARCH F-7/F-8). Roster declarado de `DetailedAccountReport`: `settlementDate` (epoch millis), el unico escalar con evidencia directa en `packages/matriz-client/documentation/Primary-API.md:1888`, dentro de la muestra `GET /rest/risk/accountReport/REM7374` en `:1817-1895`. Procedencia: vendor-documented, UNMEASURED (D-04a, tercera clase) -- nunca presentado como captura.
- **Actual:** No existe observacion en vivo de este payload en ningun lado del repo; `grep -rn 'accountData' .planning/verification/schemas/` no matchea. Los subarboles diferidos por D-07 (`currencyBalance` en `:1828-1859`, con su mapa open-keyed `detailedCurrencyBalance`; y `availableToOperate` en `:1860-1887`, con su objeto `cash` y su mapa open-keyed `detailedCash`) llegan como divergencias `extra` no-fatales y quedan descartados del surface tipado. Fila hermana: `AccountReport.portfolio` se retipo a `float | None` (D-02) sobre la misma clase de evidencia -- numero pelado en `:1894`, corroborado por el `totalMarketValue` identico de la misma cuenta en `:1706`.
- **Diff:** Causa bloqueante: LIVE-MATZ-33 -- el hostname assert D-MATZ-33 en `main_matriz.py:2548-2556` aborta cualquier corrida cuyo `base_url` no sea remarkets, y no fue bypasseado (T-37-16). Sin corrida en vivo no hay captura, y sin captura el roster no puede confirmarse ni corregirse en este ciclo. Destino nombrado: Phase 39 / LIVE-NOBJ-01, donde se mide el payload real y se ensancha o corrige el roster.

### F-13 -- no trades for MERV - XMEV - XLC - CI in last 7 days

**Class:** `NO-DATA` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** al menos 1 trade en ventana de 7 días (símbolo líquido)
- **Actual:** trades list vacía
- **Diff:** símbolo ilíquido o ventana sin actividad

### F-14 -- get_order_status levantó PrimaryAPIError inesperado

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** 200 OK con envelope {order: ...}
- **Actual:** PrimaryAPIError: Order 520900296000570:ISV_PBCP doesn't exist
- **Diff:** error upstream o envelope key ausente / status='ERROR'

### F-15 -- get_order_history levantó PrimaryAPIError inesperado

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** 200 OK con envelope {orders: ...}
- **Actual:** PrimaryAPIError: Order 520900296000570:ISV_PBCP doesn't exist
- **Diff:** error upstream o envelope key ausente / status='ERROR'

### F-16 -- get_order_by_exec_id levantó PrimaryAPIError inesperado

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** 200 OK con envelope {order: ...}
- **Actual:** PrimaryAPIError: Parameter 'execId' not found
- **Diff:** error upstream o envelope key ausente / status='ERROR'

### F-17 -- .instrument_detail.securityId: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** model declara el superset del wire
- **Actual:** key `securityId` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model

### F-18 -- .instrument_detail.securityIdSource: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** model declara el superset del wire
- **Actual:** key `securityIdSource` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model

### F-19 -- .instrument_detail.securityType: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** model declara el superset del wire
- **Actual:** key `securityType` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model

### F-20 -- .instrument_detail.settlType: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** model declara el superset del wire
- **Actual:** key `settlType` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model

### F-21 -- .instrument_detail.strike: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** model declara el superset del wire
- **Actual:** key `strike` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model

### F-22 -- .instrument_detail.symbol: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** model declara el superset del wire
- **Actual:** key `symbol` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model

### F-23 -- .instrument_detail.underlying: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** model declara el superset del wire
- **Actual:** key `underlying` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model

### F-24 -- .account_report.hasError: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** model declara el superset del wire
- **Actual:** key `hasError` presente en wire bajo `.account_report`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model

### F-25 -- .account_report.lastCalculation: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** model declara el superset del wire
- **Actual:** key `lastCalculation` presente en wire bajo `.account_report`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model

### F-26 -- .account_report.detailedAccountReports{}.availableToOperate: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** model declara el superset del wire
- **Actual:** key `availableToOperate` presente en wire bajo `.account_report.detailedAccountReports{}`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model

### F-27 -- .account_report.detailedAccountReports{}.currencyBalance: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** model declara el superset del wire
- **Actual:** key `currencyBalance` presente en wire bajo `.account_report.detailedAccountReports{}`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model

### F-28 -- prod-vs-sandbox divergence acknowledged

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** verification limited to a venue in the D-MATZ-33 hostname allowlist (this run: bbsa) by safety policy; the allowlist is widened only by explicit operator decision (Phase 39 D-02)
- **Actual:** prod (api.primary.com.ar) shape unverified; sandbox shape (bbsa) committed in .planning/verification/schemas/matriz-client/
- **Diff:** N/A (acknowledged limitation, not detected drift)

### F-29 -- InstrumentDetail.securityId: extra (declared=-, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** model declares -
- **Actual:** wire sent NoneType
- **Diff:** - -> NoneType at InstrumentDetail.securityId via /rest/instruments/details

### F-30 -- InstrumentDetail.securityIdSource: extra (declared=-, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** model declares -
- **Actual:** wire sent NoneType
- **Diff:** - -> NoneType at InstrumentDetail.securityIdSource via /rest/instruments/details

### F-31 -- InstrumentDetail.securityType: extra (declared=-, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** model declares -
- **Actual:** wire sent NoneType
- **Diff:** - -> NoneType at InstrumentDetail.securityType via /rest/instruments/details

### F-32 -- InstrumentDetail.settlType: extra (declared=-, observed=str) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** model declares -
- **Actual:** wire sent str
- **Diff:** - -> str at InstrumentDetail.settlType via /rest/instruments/details

### F-33 -- InstrumentDetail.strike: extra (declared=-, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** model declares -
- **Actual:** wire sent NoneType
- **Diff:** - -> NoneType at InstrumentDetail.strike via /rest/instruments/details

### F-34 -- InstrumentDetail.symbol: extra (declared=-, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** model declares -
- **Actual:** wire sent NoneType
- **Diff:** - -> NoneType at InstrumentDetail.symbol via /rest/instruments/details

### F-35 -- InstrumentDetail.underlying: extra (declared=-, observed=str) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** model declares -
- **Actual:** wire sent str
- **Diff:** - -> str at InstrumentDetail.underlying via /rest/instruments/details

### F-43 -- Instrument.marketId: extra (declared=-, observed=str) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** model declares -
- **Actual:** wire sent str
- **Diff:** - -> str at Instrument.marketId via /rest/instruments/byCFICode

### F-44 -- Instrument.symbol: extra (declared=-, observed=str) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** model declares -
- **Actual:** wire sent str
- **Diff:** - -> str at Instrument.symbol via /rest/instruments/byCFICode

### F-63 -- aio.get_order_status_async levantó PrimaryAPIError inesperado

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** 200 OK + surface-typed payload
- **Actual:** PrimaryAPIError: Order 520900296000570:ISV_PBCP doesn't exist
- **Diff:** error upstream o status='ERROR' inesperado

### F-64 -- aio.get_order_history_async levantó PrimaryAPIError inesperado

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** 200 OK + surface-typed payload
- **Actual:** PrimaryAPIError: Order 520900296000570:ISV_PBCP doesn't exist
- **Diff:** error upstream o status='ERROR' inesperado

### F-65 -- aio.get_order_by_exec_id_async levantó PrimaryAPIError inesperado

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** 200 OK + surface-typed payload
- **Actual:** PrimaryAPIError: Parameter 'execId' not found
- **Diff:** error upstream o status='ERROR' inesperado
<!-- END AUTO-GENERATED -->

## Cycle Closure

**Cycle ID:** `verification-cycle-2026-Q2`
**Closure date:** 2026-06-10T01:10:32+00:00
**Packages verified in this cycle:** 4 (ambito-financiero-client, iol-client, higyrus-client, matriz-client)

### Findings by status (this package)

| OPEN | CONFIRMED | FIXED | EXPECTED | NO-FIX | Total |
|------|-----------|-------|----------|--------|-------|
| 0 | 0 | 1 | 2 | 7 | 10 |

### Regression tests linked to FIXED/CONFIRMED findings

| Finding | Regression test |
|---------|-----------------|
| F-09    | `packages/matriz-client/tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code` (Phase 9 Plan 09-03 BUG-01 — 10 parametric cases, 3 buckets) |

*(historical findings F-01..F-08, F-10 predate the regression-link convention introduced in Phase 5; see [CYCLE-REPORT.md](./CYCLE-REPORT.md) "Open questions" for downstream milestone caveat)*

### Cycle validation

`verify_cycle_closure("matriz-client")` returned: **PASS** (post-Phase-9 Plan 09-03 — F-09 transitioned to FIXED with `Regression:` line linking to mocked parametric test; live re-run evidence captured in 09-03 SUMMARY paste).

Missing regressions: *(none)*

---

See [CYCLE-REPORT.md](./CYCLE-REPORT.md) for the consolidated cross-package report.
