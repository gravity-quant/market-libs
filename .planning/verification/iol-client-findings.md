# Findings: iol-client-client

## Run Context (ART)
- Timestamp: 2026-06-14T05:11:31.130065+00:00
- Resolved base URL / env: https://api.invertironline.com
- Market hours note: <abierto|cerrado — afecta paths sesión-dependientes>

<!-- Clases (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT -->
<!-- Estados (D-08): OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX). Sin campo de severidad. -->

<!-- BEGIN AUTO-GENERATED -->
## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|
| F-01 | SHAPE | both | OPEN |
| F-02 | AUTH | sync | OPEN |

## Detalle por hallazgo

### F-01 -- missing assumed key `simbolo` in get_quote

**Class:** `SHAPE` . **Surface:** `both` . **Status:** `OPEN`

- **Expected:** clave `simbolo` (tipo str) presente en payload
- **Actual:** keys=['apertura', 'cantidadOperaciones', 'cierreAnterior', 'descripcionTitulo', 'fechaHora', 'interesesAbiertos', 'laminaMinima', 'lote', 'maximo', 'minimo', 'moneda', 'montoOperado', 'plazo', 'precioAjuste', 'precioPromedio', 'puntas', 'tendencia', 'ultimoPrecio', 'variacion', 'volumenNominal']
- **Diff:** clave `simbolo` ausente

### F-02 -- _token_expires_at no se renovó tras refresh path

**Class:** `AUTH` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** _token_expires_at > 1781413891.129759
- **Actual:** _token_expires_at=0.0
- **Diff:** el refresh path no actualizó el expiry
<!-- END AUTO-GENERATED -->

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
