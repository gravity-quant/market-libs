# Findings: ambito-financiero-client-client

## Run Context (ART)
- Timestamp: 2026-06-05T22:37:10.993981+00:00
- Resolved base URL / env: https://mercados.ambito.com
- Market hours note: <abierto|cerrado — afecta paths sesión-dependientes>

<!-- Clases (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT -->
<!-- Estados (D-08): OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX). Sin campo de severidad. -->

<!-- BEGIN AUTO-GENERATED -->
## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|
| F-01 | ANTI-BOT | sync | EXPECTED |

## Detalle por hallazgo

### F-01 -- UA inválido recibe 403

**Class:** `ANTI-BOT` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** 403 con UA=python-httpx/...
- **Actual:** 403 con UA=python-httpx/...
- **Diff:** ninguno; comportamiento esperado de la defensa anti-bot
<!-- END AUTO-GENERATED -->

## Cycle Closure

**Cycle ID:** `verification-cycle-2026-Q2`
**Closure date:** 2026-06-10T01:10:32+00:00
**Packages verified in this cycle:** 4 (ambito-financiero-client, iol-client, higyrus-client, matriz-client)

### Findings by status (this package)

| OPEN | CONFIRMED | FIXED | EXPECTED | NO-FIX | Total |
|------|-----------|-------|----------|--------|-------|
| 0 | 0 | 0 | 1 | 0 | 1 |

### Regression tests linked to FIXED/CONFIRMED findings

*(historical findings predate the regression-link convention introduced in Phase 5; see [CYCLE-REPORT.md](./CYCLE-REPORT.md) "Open questions" for downstream milestone caveat)*

### Cycle validation

`verify_cycle_closure("ambito-financiero-client")` returned: **PASS**

---

See [CYCLE-REPORT.md](./CYCLE-REPORT.md) for the consolidated cross-package report.
