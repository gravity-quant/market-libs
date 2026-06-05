# Findings: ambito-financiero-client-client

## Run Context (ART)
- Timestamp: 2026-06-05T22:37:10.993981+00:00
- Resolved base URL / env: https://mercados.ambito.com
- Market hours note: <abierto|cerrado — afecta paths sesión-dependientes>

<!-- Clases (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT -->
<!-- Estados (D-08): OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX). Sin campo de severidad. -->

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
