# Findings: iol-client-client

## Run Context (ART)
- Timestamp: 2026-06-06T14:56:08.192584+00:00
- Resolved base URL / env: https://api.invertironline.com
- Market hours note: <abierto|cerrado — afecta paths sesión-dependientes>

<!-- Clases (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT -->
<!-- Estados (D-08): OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX). Sin campo de severidad. -->

## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|
| F-01 | SHAPE | both | OPEN |

## Detalle por hallazgo

### F-01 -- missing assumed key `simbolo` in get_quote

**Class:** `SHAPE` . **Surface:** `both` . **Status:** `OPEN`

- **Expected:** clave `simbolo` (tipo str) presente en payload
- **Actual:** keys=['apertura', 'cantidadOperaciones', 'cierreAnterior', 'descripcionTitulo', 'fechaHora', 'interesesAbiertos', 'laminaMinima', 'lote', 'maximo', 'minimo', 'moneda', 'montoOperado', 'plazo', 'precioAjuste', 'precioPromedio', 'puntas', 'tendencia', 'ultimoPrecio', 'variacion', 'volumenNominal']
- **Diff:** clave `simbolo` ausente
