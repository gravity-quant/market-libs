# Findings: iol-client-client

## Run Context (ART)
- Timestamp: 2026-06-25T00:06:30.440087+00:00
- Resolved base URL / env: https://api.invertironline.com
- Market hours note: <abierto|cerrado — afecta paths sesión-dependientes>

<!-- Clases (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT -->
<!-- Estados (D-08): OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX). Sin campo de severidad. -->

<!-- BEGIN AUTO-GENERATED -->
## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|
| F-01 | SHAPE | both | OPEN |
| F-02 | AUTH | sync | FIXED |

## Detalle por hallazgo

### F-01 -- missing assumed key `simbolo` in get_quote

**Class:** `SHAPE` . **Surface:** `both` . **Status:** `OPEN`

- **Expected:** clave `simbolo` (tipo str) presente en payload
- **Actual:** keys=['apertura', 'cantidadOperaciones', 'cierreAnterior', 'descripcionTitulo', 'fechaHora', 'interesesAbiertos', 'laminaMinima', 'lote', 'maximo', 'minimo', 'moneda', 'montoOperado', 'plazo', 'precioAjuste', 'precioPromedio', 'puntas', 'tendencia', 'ultimoPrecio', 'variacion', 'volumenNominal']
- **Diff:** clave `simbolo` ausente

### F-02 -- _token_expires_at no se renovó tras refresh path

**Class:** `AUTH` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** _token_expires_at > 1781413891.129759
- **Actual:** _token_expires_at=0.0
- **Diff:** el refresh path no actualizó el expiry
<!-- END AUTO-GENERATED -->

**Classification:** PROBE_STALE (not a client bug)
**Rationale:** El bug está en el probe, no en el cliente. `_refresh()` SÍ actualiza
`self._state.token_expires_at` correctamente (`packages/iol-client/src/iol_client/client.py:270`).
El probe en `main_iol.py:1289` hacía `iol_client.client._token_expires_at = 0.0` que CREABA
un atributo en el módulo sombreando el PEP 562 `__getattr__` forward a state. Lecturas
posteriores devolvían el 0.0 cacheado en el módulo, no el state value. Mismo patrón
estructural que INT-01 quick task `260613-nwb` (2026-06-13).
**Resolution:** Fix aplicado en `main_iol.py:1289` usando INT-01 idiom
(`iol_client.client._get_default()._state.token_expires_at = 0.0`) durante Phase 11
Plan 11-03 Task 3 operator disposition (2026-06-14).
**Regression:** `main_iol.py` re-run post-fix reporta
`PROBE refresh_token: PASS refresh path verified — token rotated`
(SUMMARY: PASS=13 FAIL=0 SKIPPED=1 FINDING=1; F-02 ya no surgió).
- **Regression:** packages/iol-client/tests/test_refresh_token_lifecycle.py::test_refresh_token_success_path_rotates
**Operator signoff:** sebadlf, 2026-06-14, via /gsd-execute-phase 11 Task 3 checkpoint
disposition "Fix inline ahora y cerrar Phase 11".
**Phase 17 link (operator):** la línea `Regression:` resoluble arriba enlaza el guarantee de
cliente subyacente a F-02 (que `_refresh()` actualiza `_state.token_expires_at` tras un refresh
exitoso) con la cobertura in-tree existente
`test_refresh_token_success_path_rotates`. Cierra el gap prose-only-Regression que dejaba
`verify_cycle_closure("iol-client")` en FAIL tras Phase 11. Provenance aditiva: F-02 sigue FIXED,
sin re-apertura ni cambio de status (D-05 / HARN-09).

**Phase 17 — F-01 re-confirmado OPEN (operator, baseline carry-forward, D-05):** La
re-verificación en vivo LIVE-03 posterior a las migraciones v1.2 (REFAC-05 driver migration /
SEC-01 IOL disk persistence / ERG-01 `with_options`) NO resolvió F-01
(`missing assumed key 'simbolo' in get_quote`, SHAPE/both). Se re-confirma **OPEN** como
divergencia documentada de baseline `verification-cycle-2026-Q2`; la investigación de root-cause
de la forma del payload de `get_quote` queda fuera de alcance (17-CONTEXT Deferred Ideas). OPEN es
no-gating para `verify_cycle_closure`. NO es un cambio de status ni una nueva entrada
AUTO-GENERATED; no se re-abrió ningún finding terminal (D-05 / HARN-09). Nota: en la corrida en
vivo LIVE-03 (2026-06-25, credenciales provisionadas por el operador) el driver iol **RAN** y
re-emitió F-01 (`field_type_map: FINDING F-01 (OPEN)`, SUMMARY `PASS=13 FAIL=0 SKIPPED=1 FINDING=1`);
la zona AUTO-GENERATED quedó byte-idéntica (dedupe content-addressed) y F-01 se mantiene OPEN. No
surgió ningún fid nuevo.
**Operator signoff:** sebadlf, 2026-06-25, via /gsd-execute-phase 17 (LIVE-03 gate, iol RAN en vivo).

**Phase 39 — F-01 arrastrado OPEN con destino nombrado, y el hecho nuevo que lo acompaña
(plan 39-07, LIVE-NOBJ-01):** la corrida en vivo del 2026-08-30 (`SUMMARY: PASS=14 FAIL=0
SKIPPED=1 FINDING=0 DIVERGENCES=0 HANDLER_ERRORS=0`, 15 probes, ledger byte-idéntico en su zona
AUTO-GENERATED) **no re-emitió F-01**, al revés de lo que ocurrió en LIVE-03. La causa está
medida y no es una pérdida de cobertura silenciosa: `_ASSUMED_QUOTE_FIELDS` de `main_iol.py:158`
ya no contiene `simbolo` —hoy declara sólo `ultimoPrecio`— y el modelo `Cotizacion` de la Phase
30, construido **desde los snapshots en vivo committeados** (ver su docstring), tampoco lo
declara; `simbolo: str` vive en `Titulo`, cuyo endpoint sí lo emite. Es decir: la suposición que
F-01 documentaba —que `get_quote` traía `simbolo`— fue retirada del cliente y del probe cuando la
Phase 30 tipó el paquete contra la forma real del wire.

Dos lecturas quedan abiertas y la decisión de cuál firmar es del operador, no del ejecutor:
(a) la divergencia está **materialmente resuelta** y F-01 merece un status terminal, o (b) el
probe simplemente dejó de mirar. La evidencia favorece (a) —el `Actual:` del propio F-01 ya
listaba las 20 claves de `get_quote` **sin** `simbolo`, así que la API nunca la emitió—, pero
promover un finding a terminal es exactamente lo que D-08 reserva para la firma del operador.
Hasta esa firma se **mantiene OPEN**, con destino nombrado `LIVE-NOBJ-01`, y el censo debe
contabilizarlo explícitamente: su permanencia **no** es una regresión nueva, y su no-re-emisión
**no** es un fix declarado. NO es un cambio de status ni una entrada AUTO-GENERATED nueva
(D-05 / HARN-09).

## Cycle Closure

**Cycle ID:** `verification-cycle-2026-Q2`
**Closure date:** 2026-06-10T01:10:32+00:00
**Packages verified in this cycle:** 4 (ambito-financiero-client, iol-client, higyrus-client, matriz-client)

### Findings by status (this package)

| OPEN | CONFIRMED | FIXED | EXPECTED | NO-FIX | Total |
|------|-----------|-------|----------|--------|-------|
| 1 | 0 | 0 | 0 | 0 | 1 |

### Regression tests linked to FIXED/CONFIRMED findings

*(historical findings predate the regression-link convention introduced in Phase 5; see [CYCLE-REPORT.md](./CYCLE-REPORT.md) "Open questions" for downstream milestone caveat)*

### Cycle validation

`verify_cycle_closure("iol-client")` returned: **PASS**

---

See [CYCLE-REPORT.md](./CYCLE-REPORT.md) for the consolidated cross-package report.
