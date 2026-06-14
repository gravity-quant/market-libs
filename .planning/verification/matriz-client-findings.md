# Findings: matriz-client-client

## Run Context (ART)
- Timestamp: 2026-06-10T01:01:55.430560+00:00 (original Phase 5 baseline); updated 2026-06-13 for Phase 9 Plan 09-03 F-09 close (operator-driven live re-run timestamp captured in 09-03 SUMMARY paste).
- Resolved base URL / env: https://api.remarkets.primary.com.ar
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
- **Classification rationale (Phase 5):** Gap real en el error mapping del cliente. El contrato espera `PrimaryAPIError` para CFI mal formado; el cliente lo deja pasar silenciosamente. Fix + regression test serán entregados en **Plan 05-04 cycle closure** (DRIFT-02). Hasta que se agregue, `cycle_closure_matriz_client` quedará FAIL en el próximo run — esa señal es justamente la que cierra el ciclo.
- **Resolution:** Phase 9 Plan 09-03 BUG-01 — hybrid Literal + ISO 10962 regex guard agregado pre-HTTP en `build_get_instruments_by_cfi_request` (`packages/matriz-client/src/matriz_client/_core.py:423-441`). Si `cfi_code in _CFI_LITERAL_VALUES` (frozenset derivado de `types.CFICode` via `get_args`) → pass (literal-known, 9 valores ISO 10962:2015). Si `_CFI_ISO_RE.match(cfi_code)` (regex `^[A-Z]{6}$`) → pass (forward-compat ISO 10962:2021 sin lib bump). Otherwise → `raise PrimaryAPIError(status="ERROR", description="CFI inválido: ...")`. Deviation D-02 vs ROADMAP literal `_core.raise_for_response()`: el guard vive en el builder porque `raise_for_response` solo ve `httpx.Response` y no ve el `cfi_code` param; el contrato observable (`PrimaryAPIError(status="ERROR")`) se preserva. Single-site fix (Phase 7 REFAC-03) — el cambio en `_core.py` propaga al transport shell `Client.get_instruments_by_cfi` automáticamente. matriz NO tiene `aio.py` REST aún (Phase 10 territory). Live re-run de `main_matriz.py` confirma `probe_error_malformed_cfi` reporta PASS post-fix; `cycle_closure_matriz_client` flipea FAIL → PASS (operator-driven evidence — ver 09-03 SUMMARY paste).
- **Regression:** `packages/matriz-client/tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code` (10 casos paramétricos cubriendo 3 buckets: literal-known x2, regex forward-compat x2, malformed x6 — hyphen/lowercase/digit/len5/len7/empty)

### F-10 -- prod-vs-remarkets divergence acknowledged

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** verification limited to remarkets sandbox by safety policy (REQUIREMENTS.md Out of Scope)
- **Actual:** prod (api.primary.com.ar) shape unverified; sandbox shape committed in .planning/verification/schemas/matriz-client/
- **Diff:** N/A (acknowledged limitation, not detected drift)
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
