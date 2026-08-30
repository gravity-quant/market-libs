# Findings: matriz-client-client

## Run Context (ART)
- Timestamp: 2026-08-30T02:41:27.293177+00:00
- Resolved base URL / env: https://api.bbsa.matrizoms.com.ar
- Market hours note: **cerrado** — sábado 2026-08-29 23:34 ART, fuera de toda sesión de negociación ARG. El discriminador es el de D-MATZ-5 / D-12 y no se inventó otro: `/rest/marketdata/get` devolvió las siete entradas (`BI,OF,LA,OP,CL,SE,OI`) en `null`, así que `LA` no es dict y la **rama de antigüedad** de `LA.date` no se ejecutó; el camino que aplicó es el de `LA` ausente/nula, documentado en el docstring de `probe_get_market_data` como PASS-shape sin asserts de valor. Ver `.planning/verification/schemas/matriz-client/get-market-data.bbsa.json`.
- Run params (plan 39-07): `MATRIZ_SAMPLE_SYMBOL='MERV - XMEV - XLC - CI'` pasado explícito por CLI (precedente: el bloque análogo de `higyrus-client-findings.md`). El valor de `.env` (`AL30`) es de la era remarkets y **no existe** en bbsa — medido: 0 coincidencias sobre 9684 instrumentos —, lo que hacía fallar `get_instrument_detail` / `get_market_data` / sus espejos async y dejaba la cadena profunda de D-05 sin ejercitar. El símbolo usado es exactamente el que el driver auto-resuelve en bbsa sin override (`instruments[0].instrumentId.symbol`, D-MATZ-1). `MATRIZ_SAMPLE_CL_ORD_ID` / `MATRIZ_SAMPLE_PROPRIETARY` / `MATRIZ_SAMPLE_EXEC_ID` quedaron con sus valores de `.env`, también de la era remarkets: ver F-14, F-15, F-16 y sus espejos async.

<!-- Clases (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT -->
<!-- Estados (D-08): OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX). Sin campo de severidad. -->

<!-- BEGIN AUTO-GENERATED -->
## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|
| F-01 | NO-DATA | sync | NO-FIX |
| F-02 | SHAPE | sync | NO-FIX |
| F-03 | SHAPE | sync | NO-FIX |
| F-04 | SHAPE | sync | NO-FIX |
| F-05 | SHAPE | sync | NO-FIX |
| F-06 | SHAPE | sync | NO-FIX |
| F-07 | SHAPE | sync | NO-FIX |
| F-08 | SHAPE | sync | NO-FIX |
| F-09 | ERROR-MAP | sync | FIXED |
| F-10 | SHAPE | sync | NO-FIX |
| F-11 | SHAPE | sync | NO-FIX |
| F-12 | SHAPE | sync | NO-FIX |
| F-13 | NO-DATA | sync | NO-FIX |
| F-14 | ERROR-MAP | sync | EXPECTED |
| F-15 | ERROR-MAP | sync | EXPECTED |
| F-16 | ERROR-MAP | sync | EXPECTED |
| F-17 | SHAPE | sync | NO-FIX |
| F-18 | SHAPE | sync | NO-FIX |
| F-19 | SHAPE | sync | NO-FIX |
| F-20 | SHAPE | sync | NO-FIX |
| F-21 | SHAPE | sync | NO-FIX |
| F-22 | SHAPE | sync | NO-FIX |
| F-23 | SHAPE | sync | NO-FIX |
| F-24 | SHAPE | sync | NO-FIX |
| F-25 | SHAPE | sync | NO-FIX |
| F-26 | SHAPE | sync | NO-FIX |
| F-27 | SHAPE | sync | NO-FIX |
| F-28 | SHAPE | sync | EXPECTED |
| F-29 | SHAPE | async | NO-FIX |
| F-30 | SHAPE | async | NO-FIX |
| F-31 | SHAPE | async | NO-FIX |
| F-32 | SHAPE | async | NO-FIX |
| F-33 | SHAPE | async | NO-FIX |
| F-34 | SHAPE | async | NO-FIX |
| F-35 | SHAPE | async | NO-FIX |
| F-43 | SHAPE | async | FIXED |
| F-44 | SHAPE | async | FIXED |
| F-63 | ERROR-MAP | async | EXPECTED |
| F-64 | ERROR-MAP | async | EXPECTED |
| F-65 | ERROR-MAP | async | EXPECTED |

## Detalle por hallazgo

### F-01 -- no trades for SOJ.ROS/NOV26 308 P in last 7 days

**Class:** `NO-DATA` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** al menos 1 trade en ventana de 7 días (símbolo líquido)
- **Actual:** trades list vacía
- **Diff:** símbolo ilíquido o ventana sin actividad
- **Classification rationale (Phase 5):** NO-DATA es condición de mercado (símbolo poco operado en sandbox remarkets), no bug del cliente. `get_trades` retorna `[]` correctamente y el contrato wire→model se ejercita igual. Sin fix ni regression.

### F-02 -- prod-vs-remarkets divergence acknowledged

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** verification limited to remarkets sandbox by safety policy (REQUIREMENTS.md Out of Scope)
- **Actual:** prod (api.primary.com.ar) shape unverified; sandbox shape committed in .planning/verification/schemas/matriz-client/
- **Diff:** N/A (acknowledged limitation, not detected drift)
- **Disposición (Phase 39 / plan 39-07):** **SUPERSEDED (Pitfall 5 / plan 39-01).** El finding terminal de matriz se retituló a `prod-vs-sandbox divergence acknowledged` cuando la decisión D-02 amplió el allowlist D-MATZ-33 a bbsa, así que la deduplicación por título creó uno NUEVO en esta primera corrida en vivo: **F-28**. Este bloque queda como registro histórico del texto anterior (que hablaba de remarkets como único venue) y NO se borra. Su reemplazo es F-28.

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

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** verification limited to remarkets sandbox by safety policy (REQUIREMENTS.md Out of Scope)
- **Actual:** prod (api.primary.com.ar) shape unverified; sandbox shape committed in .planning/verification/schemas/matriz-client/
- **Diff:** N/A (acknowledged limitation, not detected drift)
- **Disposición (Phase 39 / plan 39-07):** **SUPERSEDED, ídem F-02** — F-10 era además un duplicado exacto de F-02 por título presente en el ledger desde antes de esta fase (los call sites de probe usan el default legacy `idempotent_by_title=False`, que sólo deduplica por fid). Reemplazado por **F-28**. No se borra.

### F-11 -- DetailedPosition.report roster declarado desde vendor doc, nunca observado en vivo

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** `DetailedPosition.report` tipado `dict[str, dict[str, InstrumentPositionReport]]` (dos niveles de keys abiertas: contractType -> symbol). Roster declarado de `InstrumentPositionReport`: `instrumentInitialSize`, `instrumentFilledSize`, `instrumentCurrentSize` -- los tres escalares hermanos de `packages/matriz-client/documentation/Primary-API.md:1745-1747`, dentro de la muestra `GET /rest/risk/detailedPosition/REM7374` en `:1701-1791`. Procedencia: vendor-documented, UNMEASURED (D-04a, tercera clase) -- nunca presentado como captura.
- **Actual:** No existe observacion en vivo de este payload en ningun lado del repo. `.planning/verification/schemas/matriz-client/` tiene ocho schemas committeados (instruments, market data, segments, trades) y ninguno cubre los endpoints Risk; `grep -rn 'detailedPosition' .planning/verification/schemas/` no matchea. El roster y los tipos runtime salen del vendor doc committeado, no de la wire. Los subarboles diferidos por D-07 (`detailedPositions`, `:1710-1744`, ~21 campos por elemento, con su `detailedDailyDiff` de 8 campos en `:1733-1742`) llegan como divergencias `extra` no-fatales y quedan descartados del surface tipado.
- **Diff:** Causa bloqueante: LIVE-MATZ-33 -- el hostname assert D-MATZ-33 en `main_matriz.py:2548-2556` aborta cualquier corrida cuyo `base_url` no sea remarkets, y no fue bypasseado (T-37-16). Sin corrida en vivo no hay captura, y sin captura el roster no puede confirmarse ni corregirse en este ciclo. Destino nombrado: Phase 39 / LIVE-NOBJ-01, donde se mide el payload real y se ensancha o corrige el roster.
- **Disposición (Phase 39 / plan 39-07):** **Destino LIVE-NOBJ-01 alcanzado a medias, y la mitad restante está medida.** La causa bloqueante que este finding nombraba (LIVE-MATZ-33) quedó levantada por D-02 y el payload SÍ se midió en esta corrida: `.planning/verification/schemas/matriz-client/get-detailed-positions.bbsa.json` registra `report` como mapa **vacío** (`{}`), porque la cuenta no tiene posiciones en bbsa (`get_positions` devolvió 0). El CONTENEDOR queda confirmado (es un mapa, y el tipo declarado lo admite); el roster de la hoja `InstrumentPositionReport` sigue **UNMEASURED** por ausencia de posiciones, no por ausencia de corrida — la causa cambió de política a datos. Destino de la mitad restante: una corrida con posiciones abiertas en la cuenta, elevada al operador en el checkpoint de la Task 3.

### F-12 -- AccountReport.detailedAccountReports roster declarado desde vendor doc, nunca observado en vivo

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** `AccountReport.detailedAccountReports` tipado `dict[str, DetailedAccountReport]` (UN nivel de keys abiertas, no dos -- la asimetria con `report` esta medida en 37-RESEARCH F-7/F-8). Roster declarado de `DetailedAccountReport`: `settlementDate` (epoch millis), el unico escalar con evidencia directa en `packages/matriz-client/documentation/Primary-API.md:1888`, dentro de la muestra `GET /rest/risk/accountReport/REM7374` en `:1817-1895`. Procedencia: vendor-documented, UNMEASURED (D-04a, tercera clase) -- nunca presentado como captura.
- **Actual:** No existe observacion en vivo de este payload en ningun lado del repo; `grep -rn 'accountData' .planning/verification/schemas/` no matchea. Los subarboles diferidos por D-07 (`currencyBalance` en `:1828-1859`, con su mapa open-keyed `detailedCurrencyBalance`; y `availableToOperate` en `:1860-1887`, con su objeto `cash` y su mapa open-keyed `detailedCash`) llegan como divergencias `extra` no-fatales y quedan descartados del surface tipado. Fila hermana: `AccountReport.portfolio` se retipo a `float | None` (D-02) sobre la misma clase de evidencia -- numero pelado en `:1894`, corroborado por el `totalMarketValue` identico de la misma cuenta en `:1706`.
- **Diff:** Causa bloqueante: LIVE-MATZ-33 -- el hostname assert D-MATZ-33 en `main_matriz.py:2548-2556` aborta cualquier corrida cuyo `base_url` no sea remarkets, y no fue bypasseado (T-37-16). Sin corrida en vivo no hay captura, y sin captura el roster no puede confirmarse ni corregirse en este ciclo. Destino nombrado: Phase 39 / LIVE-NOBJ-01, donde se mide el payload real y se ensancha o corrige el roster.
- **Disposición (Phase 39 / plan 39-07):** **Destino LIVE-NOBJ-01 alcanzado: roster CONFIRMADO.** La causa bloqueante (LIVE-MATZ-33) quedó levantada por D-02 y el payload se midió: `.planning/verification/schemas/matriz-client/get-account-report.bbsa.json` registra `detailedAccountReports` como mapa de **un** nivel de claves abiertas —la asimetría con `report` que 37-RESEARCH F-7/F-8 había medido se confirma— con `settlementDate: int` presente, exactamente el roster declarado. Los dos subárboles que D-07 difirió (`availableToOperate`, `currencyBalance`) llegaron como divergencias `extra` no-fatales, tal como este finding predijo: ver F-26 y F-27. No hace falta ensanchar ni corregir el roster declarado.

### F-13 -- no trades for MERV - XMEV - XLC - CI in last 7 days

**Class:** `NO-DATA` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** al menos 1 trade en ventana de 7 días (símbolo líquido)
- **Actual:** trades list vacía
- **Diff:** símbolo ilíquido o ventana sin actividad
- **Disposición (Phase 39 / plan 39-07):** Condición de mercado, no defecto del cliente: la corrida cayó el sábado 2026-08-29 23:34 ART, fuera de toda sesión de negociación ARG, y el símbolo resuelto en vivo no registró trades en la ventana de 7 días. `get_trades` devolvió `[]` correctamente y el contrato wire-modelo se ejercitó igual. Mismo fundamento que F-01 (Phase 5). Es además uno de los casos límite de D-12 que esta corrida buscó deliberadamente: colección vacía sobre datos reales.

### F-14 -- get_order_status levantó PrimaryAPIError inesperado

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** 200 OK con envelope {order: ...}
- **Actual:** PrimaryAPIError: Order 520900296000570:ISV_PBCP doesn't exist
- **Diff:** error upstream o envelope key ausente / status='ERROR'
- **Disposición (Phase 39 / plan 39-07):** El identificador de orden de muestra (`MATRIZ_SAMPLE_CL_ORD_ID` / `MATRIZ_SAMPLE_PROPRIETARY`) es un valor de la era remarkets y esa orden no existe en el venue bbsa contra el que corrió esta fase (`get_all_orders` devolvió 0 órdenes para la cuenta). El cliente mapeó FIELMENTE el error del vendor a `PrimaryAPIError`: lo que no aplica a este venue es la expectativa del probe (200 OK), no el comportamiento del cliente. Deriva atribuible a la diferencia de venue, no a un defecto.

### F-15 -- get_order_history levantó PrimaryAPIError inesperado

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** 200 OK con envelope {orders: ...}
- **Actual:** PrimaryAPIError: Order 520900296000570:ISV_PBCP doesn't exist
- **Diff:** error upstream o envelope key ausente / status='ERROR'
- **Disposición (Phase 39 / plan 39-07):** El identificador de orden de muestra (`MATRIZ_SAMPLE_CL_ORD_ID` / `MATRIZ_SAMPLE_PROPRIETARY`) es un valor de la era remarkets y esa orden no existe en el venue bbsa contra el que corrió esta fase (`get_all_orders` devolvió 0 órdenes para la cuenta). El cliente mapeó FIELMENTE el error del vendor a `PrimaryAPIError`: lo que no aplica a este venue es la expectativa del probe (200 OK), no el comportamiento del cliente. Deriva atribuible a la diferencia de venue, no a un defecto.

### F-16 -- get_order_by_exec_id levantó PrimaryAPIError inesperado

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** 200 OK con envelope {order: ...}
- **Actual:** PrimaryAPIError: Parameter 'execId' not found
- **Diff:** error upstream o envelope key ausente / status='ERROR'
- **Disposición (Phase 39 / plan 39-07):** `MATRIZ_SAMPLE_EXEC_ID` es un valor de la era remarkets; bbsa responde `Parameter 'execId' not found`. Mismo fundamento que F-14/F-15: el cliente mapeó el error del vendor a `PrimaryAPIError` sin alterarlo. Deriva de venue, no defecto del cliente.

### F-17 -- .instrument_detail.securityId: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `securityId` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Disposición (Phase 39 / plan 39-07):** Wire-superset bajo `.instrument_detail`: el backend emite una clave que el modelo no declara. `_SafeModel.from_api` tolera el superset del wire por diseño y el walker lo reporta como divergencia `extra` no-fatal — el sistema funcionó, la divergencia NO fue silenciosa. Mismo principio que F-03..F-08, que son estas mismas claves medidas contra remarkets el 2026-06-10: esta corrida las confirma cross-venue. Sin fix ni regresión. `securityId` es la única de las siete que no estaba en el set de F-03..F-08.

### F-18 -- .instrument_detail.securityIdSource: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `securityIdSource` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Disposición (Phase 39 / plan 39-07):** Wire-superset bajo `.instrument_detail`: el backend emite una clave que el modelo no declara. `_SafeModel.from_api` tolera el superset del wire por diseño y el walker lo reporta como divergencia `extra` no-fatal — el sistema funcionó, la divergencia NO fue silenciosa. Mismo principio que F-03..F-08, que son estas mismas claves medidas contra remarkets el 2026-06-10: esta corrida las confirma cross-venue. Sin fix ni regresión.

### F-19 -- .instrument_detail.securityType: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `securityType` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Disposición (Phase 39 / plan 39-07):** Wire-superset bajo `.instrument_detail`: el backend emite una clave que el modelo no declara. `_SafeModel.from_api` tolera el superset del wire por diseño y el walker lo reporta como divergencia `extra` no-fatal — el sistema funcionó, la divergencia NO fue silenciosa. Mismo principio que F-03..F-08, que son estas mismas claves medidas contra remarkets el 2026-06-10: esta corrida las confirma cross-venue. Sin fix ni regresión.

### F-20 -- .instrument_detail.settlType: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `settlType` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Disposición (Phase 39 / plan 39-07):** Wire-superset bajo `.instrument_detail`: el backend emite una clave que el modelo no declara. `_SafeModel.from_api` tolera el superset del wire por diseño y el walker lo reporta como divergencia `extra` no-fatal — el sistema funcionó, la divergencia NO fue silenciosa. Mismo principio que F-03..F-08, que son estas mismas claves medidas contra remarkets el 2026-06-10: esta corrida las confirma cross-venue. Sin fix ni regresión.

### F-21 -- .instrument_detail.strike: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `strike` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Disposición (Phase 39 / plan 39-07):** Wire-superset bajo `.instrument_detail`: el backend emite una clave que el modelo no declara. `_SafeModel.from_api` tolera el superset del wire por diseño y el walker lo reporta como divergencia `extra` no-fatal — el sistema funcionó, la divergencia NO fue silenciosa. Mismo principio que F-03..F-08, que son estas mismas claves medidas contra remarkets el 2026-06-10: esta corrida las confirma cross-venue. Sin fix ni regresión.

### F-22 -- .instrument_detail.symbol: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `symbol` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Disposición (Phase 39 / plan 39-07):** Wire-superset bajo `.instrument_detail`: el backend emite una clave que el modelo no declara. `_SafeModel.from_api` tolera el superset del wire por diseño y el walker lo reporta como divergencia `extra` no-fatal — el sistema funcionó, la divergencia NO fue silenciosa. Mismo principio que F-03..F-08, que son estas mismas claves medidas contra remarkets el 2026-06-10: esta corrida las confirma cross-venue. Sin fix ni regresión.

### F-23 -- .instrument_detail.underlying: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `underlying` presente en wire bajo `.instrument_detail`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Disposición (Phase 39 / plan 39-07):** Wire-superset bajo `.instrument_detail`: el backend emite una clave que el modelo no declara. `_SafeModel.from_api` tolera el superset del wire por diseño y el walker lo reporta como divergencia `extra` no-fatal — el sistema funcionó, la divergencia NO fue silenciosa. Mismo principio que F-03..F-08, que son estas mismas claves medidas contra remarkets el 2026-06-10: esta corrida las confirma cross-venue. Sin fix ni regresión.

### F-24 -- .account_report.hasError: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `hasError` presente en wire bajo `.account_report`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Disposición (Phase 39 / plan 39-07):** Clave del wire que `AccountReport` no declara, observada por primera vez en esta corrida (la captura viva de los endpoints Risk era imposible hasta que D-02 amplió el allowlist D-MATZ-33). Wire-superset tolerado por diseño y reportado, no silenciado. Ensanchar el roster es un cambio de superficie pública de un paquete publicado y pertenece al ciclo de release, no a un plan de verificación: elevado al operador en el checkpoint de la Task 3.

### F-25 -- .account_report.lastCalculation: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `lastCalculation` presente en wire bajo `.account_report`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Disposición (Phase 39 / plan 39-07):** Clave del wire que `AccountReport` no declara, observada por primera vez en esta corrida (la captura viva de los endpoints Risk era imposible hasta que D-02 amplió el allowlist D-MATZ-33). Wire-superset tolerado por diseño y reportado, no silenciado. Ensanchar el roster es un cambio de superficie pública de un paquete publicado y pertenece al ciclo de release, no a un plan de verificación: elevado al operador en el checkpoint de la Task 3.

### F-26 -- .account_report.detailedAccountReports{}.availableToOperate: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `availableToOperate` presente en wire bajo `.account_report.detailedAccountReports{}`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Disposición (Phase 39 / plan 39-07):** Es EXACTAMENTE uno de los dos subárboles que D-07 difirió del surface tipado y que F-12 predijo que llegarían como divergencias `extra` no-fatales. Predicción validada en vivo: el comportamiento observado es el diseñado. Sin fix ni regresión.

### F-27 -- .account_report.detailedAccountReports{}.currencyBalance: wire emite, model ignora (info)

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declara el superset del wire
- **Actual:** key `currencyBalance` presente en wire bajo `.account_report.detailedAccountReports{}`
- **Diff:** backend posiblemente agregó campo nuevo; candidato a extender model
- **Disposición (Phase 39 / plan 39-07):** Es EXACTAMENTE uno de los dos subárboles que D-07 difirió del surface tipado y que F-12 predijo que llegarían como divergencias `extra` no-fatales. Predicción validada en vivo: el comportamiento observado es el diseñado. Sin fix ni regresión.

### F-28 -- prod-vs-sandbox divergence acknowledged

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** verification limited to a venue in the D-MATZ-33 hostname allowlist (this run: bbsa) by safety policy; the allowlist is widened only by explicit operator decision (Phase 39 D-02)
- **Actual:** prod (api.primary.com.ar) shape unverified; sandbox shape (bbsa) committed in .planning/verification/schemas/matriz-client/
- **Diff:** N/A (acknowledged limitation, not detected drift)

### F-29 -- InstrumentDetail.securityId: extra (declared=-, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent NoneType
- **Diff:** - -> NoneType at InstrumentDetail.securityId via /rest/instruments/details
- **Disposición (Phase 39 / plan 39-07):** Mismo wire-superset de `InstrumentDetail` que F-17..F-23, reportado por el otro observador: el walker sobre la superficie async tipada. Su presencia con el mismo roster de claves ES la evidencia de paridad de observación sync-async, no un defecto adicional. Sin fix ni regresión.

### F-30 -- InstrumentDetail.securityIdSource: extra (declared=-, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent NoneType
- **Diff:** - -> NoneType at InstrumentDetail.securityIdSource via /rest/instruments/details
- **Disposición (Phase 39 / plan 39-07):** Mismo wire-superset de `InstrumentDetail` que F-17..F-23, reportado por el otro observador: el walker sobre la superficie async tipada. Su presencia con el mismo roster de claves ES la evidencia de paridad de observación sync-async, no un defecto adicional. Sin fix ni regresión.

### F-31 -- InstrumentDetail.securityType: extra (declared=-, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent NoneType
- **Diff:** - -> NoneType at InstrumentDetail.securityType via /rest/instruments/details
- **Disposición (Phase 39 / plan 39-07):** Mismo wire-superset de `InstrumentDetail` que F-17..F-23, reportado por el otro observador: el walker sobre la superficie async tipada. Su presencia con el mismo roster de claves ES la evidencia de paridad de observación sync-async, no un defecto adicional. Sin fix ni regresión.

### F-32 -- InstrumentDetail.settlType: extra (declared=-, observed=str) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent str
- **Diff:** - -> str at InstrumentDetail.settlType via /rest/instruments/details
- **Disposición (Phase 39 / plan 39-07):** Mismo wire-superset de `InstrumentDetail` que F-17..F-23, reportado por el otro observador: el walker sobre la superficie async tipada. Su presencia con el mismo roster de claves ES la evidencia de paridad de observación sync-async, no un defecto adicional. Sin fix ni regresión.

### F-33 -- InstrumentDetail.strike: extra (declared=-, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent NoneType
- **Diff:** - -> NoneType at InstrumentDetail.strike via /rest/instruments/details
- **Disposición (Phase 39 / plan 39-07):** Mismo wire-superset de `InstrumentDetail` que F-17..F-23, reportado por el otro observador: el walker sobre la superficie async tipada. Su presencia con el mismo roster de claves ES la evidencia de paridad de observación sync-async, no un defecto adicional. Sin fix ni regresión.

### F-34 -- InstrumentDetail.symbol: extra (declared=-, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent NoneType
- **Diff:** - -> NoneType at InstrumentDetail.symbol via /rest/instruments/details
- **Disposición (Phase 39 / plan 39-07):** Mismo wire-superset de `InstrumentDetail` que F-17..F-23, reportado por el otro observador: el walker sobre la superficie async tipada. Su presencia con el mismo roster de claves ES la evidencia de paridad de observación sync-async, no un defecto adicional. Sin fix ni regresión.

### F-35 -- InstrumentDetail.underlying: extra (declared=-, observed=str) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent str
- **Diff:** - -> str at InstrumentDetail.underlying via /rest/instruments/details
- **Disposición (Phase 39 / plan 39-07):** Mismo wire-superset de `InstrumentDetail` que F-17..F-23, reportado por el otro observador: el walker sobre la superficie async tipada. Su presencia con el mismo roster de claves ES la evidencia de paridad de observación sync-async, no un defecto adicional. Sin fix ni regresión.

### F-43 -- Instrument.marketId: extra (declared=-, observed=str) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares -
- **Actual:** wire sent str
- **Diff:** - -> str at Instrument.marketId via /rest/instruments/byCFICode
- **Disposición (Phase 39 / plan 39-07):** **CONFIRMED en vivo y corregido in-cycle.** `/rest/instruments/byCFICode` y `/rest/instruments/bySegment` devuelven el identificador PLANO (`{marketId, symbol}`), no anidado bajo `instrumentId` como `/rest/instruments/all`. Sobre esa forma la política Null Object (Phase 35 / NOBJ-02) colapsaba el eslabón ausente a `InstrumentId.empty()` SIN emitir divergencia, y los únicos datos que el wire traía se descartaban como `extra`: la corrida midió 386 y 9160 objetos `Instrument` con `marketId=None, symbol=None, cficode=None` — el 100% del payload de dos métodos públicos, perdido en silencio en las cuatro superficies. Medido en los DOS venues del allowlist (baseline remarkets 2026-06-10 y captura bbsa 2026-08-30): no es deriva entre venues. Fix: `_core._normalize_instrument_element`, sitio único que ambos shells (`client.py` y `aio.py`) atraviesan por REFAC-03 — mismo mecanismo de espejo sync/async que cerró F-09. Post-fix la corrida en vivo baja de DIVERGENCES=9 a DIVERGENCES=7 y los 9160 instrumentos llegan con su símbolo real. La baja es por CORRECCIÓN REAL, no por colapso de política.
- **Regression:** packages/matriz-client/tests/test_instruments_flat_identifier_shape.py::test_by_cfi_flat_element_reaches_the_caller_sync (el archivo pinea las CUATRO superficies: los espejos async son `test_by_cfi_flat_element_reaches_the_caller_async` y `test_by_segment_flat_element_reaches_the_caller_async`, más el control poblado de la forma anidada de `/rest/instruments/all`, la tolerancia forward-compat y seis bordes degenerados)

### F-44 -- Instrument.symbol: extra (declared=-, observed=str) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares -
- **Actual:** wire sent str
- **Diff:** - -> str at Instrument.symbol via /rest/instruments/byCFICode
- **Disposición (Phase 39 / plan 39-07):** **CONFIRMED en vivo y corregido in-cycle.** `/rest/instruments/byCFICode` y `/rest/instruments/bySegment` devuelven el identificador PLANO (`{marketId, symbol}`), no anidado bajo `instrumentId` como `/rest/instruments/all`. Sobre esa forma la política Null Object (Phase 35 / NOBJ-02) colapsaba el eslabón ausente a `InstrumentId.empty()` SIN emitir divergencia, y los únicos datos que el wire traía se descartaban como `extra`: la corrida midió 386 y 9160 objetos `Instrument` con `marketId=None, symbol=None, cficode=None` — el 100% del payload de dos métodos públicos, perdido en silencio en las cuatro superficies. Medido en los DOS venues del allowlist (baseline remarkets 2026-06-10 y captura bbsa 2026-08-30): no es deriva entre venues. Fix: `_core._normalize_instrument_element`, sitio único que ambos shells (`client.py` y `aio.py`) atraviesan por REFAC-03 — mismo mecanismo de espejo sync/async que cerró F-09. Post-fix la corrida en vivo baja de DIVERGENCES=9 a DIVERGENCES=7 y los 9160 instrumentos llegan con su símbolo real. La baja es por CORRECCIÓN REAL, no por colapso de política.
- **Regression:** packages/matriz-client/tests/test_instruments_flat_identifier_shape.py::test_by_segment_flat_element_reaches_the_caller_sync (el archivo pinea las CUATRO superficies: los espejos async son `test_by_cfi_flat_element_reaches_the_caller_async` y `test_by_segment_flat_element_reaches_the_caller_async`, más el control poblado de la forma anidada de `/rest/instruments/all`, la tolerancia forward-compat y seis bordes degenerados)

### F-63 -- aio.get_order_status_async levantó PrimaryAPIError inesperado

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** 200 OK + surface-typed payload
- **Actual:** PrimaryAPIError: Order 520900296000570:ISV_PBCP doesn't exist
- **Diff:** error upstream o status='ERROR' inesperado
- **Disposición (Phase 39 / plan 39-07):** El identificador de orden de muestra (`MATRIZ_SAMPLE_CL_ORD_ID` / `MATRIZ_SAMPLE_PROPRIETARY`) es un valor de la era remarkets y esa orden no existe en el venue bbsa contra el que corrió esta fase (`get_all_orders` devolvió 0 órdenes para la cuenta). El cliente mapeó FIELMENTE el error del vendor a `PrimaryAPIError`: lo que no aplica a este venue es la expectativa del probe (200 OK), no el comportamiento del cliente. Deriva atribuible a la diferencia de venue, no a un defecto. Espejo async de F-14.

### F-64 -- aio.get_order_history_async levantó PrimaryAPIError inesperado

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** 200 OK + surface-typed payload
- **Actual:** PrimaryAPIError: Order 520900296000570:ISV_PBCP doesn't exist
- **Diff:** error upstream o status='ERROR' inesperado
- **Disposición (Phase 39 / plan 39-07):** El identificador de orden de muestra (`MATRIZ_SAMPLE_CL_ORD_ID` / `MATRIZ_SAMPLE_PROPRIETARY`) es un valor de la era remarkets y esa orden no existe en el venue bbsa contra el que corrió esta fase (`get_all_orders` devolvió 0 órdenes para la cuenta). El cliente mapeó FIELMENTE el error del vendor a `PrimaryAPIError`: lo que no aplica a este venue es la expectativa del probe (200 OK), no el comportamiento del cliente. Deriva atribuible a la diferencia de venue, no a un defecto. Espejo async de F-15.

### F-65 -- aio.get_order_by_exec_id_async levantó PrimaryAPIError inesperado

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** 200 OK + surface-typed payload
- **Actual:** PrimaryAPIError: Parameter 'execId' not found
- **Diff:** error upstream o status='ERROR' inesperado
- **Disposición (Phase 39 / plan 39-07):** `MATRIZ_SAMPLE_EXEC_ID` es un valor de la era remarkets; bbsa responde `Parameter 'execId' not found`. Mismo fundamento que F-14/F-15: el cliente mapeó el error del vendor a `PrimaryAPIError` sin alterarlo. Deriva de venue, no defecto del cliente. Espejo async de F-16.

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

## Cycle Closure — Phase 39 (LIVE-NOBJ-01, plan 39-07)

**Cycle ID:** `verification-cycle-2026-Q3-nobj`
**Run date:** 2026-08-30T02:41 UTC (sábado 2026-08-29 23:34 ART, mercado cerrado)
**Venue:** `api.bbsa.matrizoms.com.ar` — el segundo venue del allowlist D-MATZ-33, habilitado por la decisión D-02 de esta fase. `LIVE-MATZ-33` deja de bloquear a matriz: el paquete quedó clasificado **RAN**, no `SKIPPED`.
**SUMMARY verbatim:** `SUMMARY: PASS=39 FAIL=0 SKIPPED=4 FINDING=7 DIVERGENCES=9 HANDLER_ERRORS=0` (post-fix in-cycle: `DIVERGENCES=7`).

La sección `verification-cycle-2026-Q2` de arriba se conserva intacta como registro histórico; esta la sucede.

### Findings by status (this package, ledger completo)

| OPEN | CONFIRMED | FIXED | EXPECTED | NO-FIX | Total |
|------|-----------|-------|----------|--------|-------|
| 0 | 0 | 3 | 7 | 30 | 40 |

Los 28 findings nuevos de esta corrida (F-13..F-35, F-43, F-44, F-63..F-65) tienen todos una disposición argumentada en su propio bloque; ninguno quedó `OPEN`.

### Regression tests linked to FIXED/CONFIRMED findings

| Finding | Regression test |
|---------|-----------------|
| F-09    | `packages/matriz-client/tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code` (Phase 9 Plan 09-03 BUG-01 — 10 parametric cases, 3 buckets) |
| F-43    | `packages/matriz-client/tests/test_instruments_flat_identifier_shape.py::test_by_cfi_flat_element_reaches_the_caller_sync` (Phase 39 plan 39-07 — 13 casos: 4 superficies afectadas, control poblado anidado, forward-compat y 6 bordes degenerados) |
| F-44    | `packages/matriz-client/tests/test_instruments_flat_identifier_shape.py::test_by_segment_flat_element_reaches_the_caller_sync` (mismo archivo) |

### Lo que esta corrida midió y las fases anteriores no podían

- **La cadena profunda de `MarketDataSnapshot` corrió contra datos reales en las DOS superficies.** `/rest/marketdata/get` devolvió las siete entradas en `null` (mercado cerrado) y los seis alias de la Phase 37 se desreferenciaron sin una sola excepción: `last=None bids=0 offers=0 settlement=None close=None oi=None`, idéntico en `client.py` y en `aio.py`. La política Null Object absorbió siete eslabones nulos sobre un payload real **sin fabricar una sola divergencia** — SC-2 demostrado en vivo, no contra fixtures.
- **Los dos endpoints Risk quedaron capturados.** `LIVE-MATZ-33` era la causa bloqueante que F-11 y F-12 nombraban; ambos reciben su medición en esta corrida (ver sus bloques).
- **Una divergencia CONFIRMED apareció y se corrigió in-cycle** (F-43 / F-44): ver `_core._normalize_instrument_element`.

---

See [CYCLE-REPORT.md](./CYCLE-REPORT.md) for the consolidated cross-package report.
