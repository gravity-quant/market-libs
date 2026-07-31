# Findings: market-data-client-client

## Run Context (ART)
- Timestamp: 2026-07-31T17:32:10.626555+00:00
- Resolved base URL / env: https://market-data-develop.bbsa.com.ar/api
- Market hours note: <abierto|cerrado — afecta paths sesión-dependientes>

<!-- Clases (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT -->
<!-- Estados (D-08): OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX). Sin campo de severidad. -->

<!-- BEGIN AUTO-GENERATED -->
## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|
| F-01 | NO-DATA | sync | EXPECTED |
| F-02 | NO-DATA | async | EXPECTED |
| F-03 | SHAPE | sync | FIXED |
| F-04 | SHAPE | sync | FIXED |
| F-05 | SHAPE | sync | FIXED |
| F-06 | SHAPE | sync | FIXED |
| F-07 | SHAPE | sync | FIXED |
| F-08 | SHAPE | sync | FIXED |
| F-09 | SHAPE | sync | FIXED |
| F-10 | SHAPE | sync | FIXED |
| F-11 | SHAPE | sync | FIXED |
| F-12 | SHAPE | sync | FIXED |
| F-13 | SHAPE | sync | FIXED |
| F-14 | SHAPE | sync | FIXED |
| F-15 | SHAPE | sync | FIXED |
| F-16 | SHAPE | sync | FIXED |
| F-17 | SHAPE | sync | FIXED |
| F-18 | SHAPE | sync | FIXED |
| F-19 | SHAPE | async | FIXED |
| F-20 | SHAPE | async | FIXED |
| F-21 | SHAPE | async | FIXED |
| F-22 | SHAPE | async | FIXED |
| F-23 | SHAPE | async | FIXED |
| F-24 | SHAPE | async | FIXED |
| F-25 | SHAPE | async | FIXED |
| F-26 | SHAPE | async | FIXED |
| F-27 | SHAPE | async | FIXED |
| F-28 | SHAPE | async | FIXED |
| F-29 | SHAPE | async | FIXED |
| F-30 | SHAPE | async | FIXED |
| F-31 | SHAPE | async | FIXED |
| F-32 | SHAPE | async | FIXED |
| F-33 | SHAPE | async | FIXED |
| F-34 | SHAPE | async | FIXED |
| F-35 | SHAPE | async | FIXED |
| F-36 | SHAPE | async | FIXED |

## Detalle por hallazgo

### F-01 -- market_data vacío para prefix '__no_such_symbol__'

**Class:** `NO-DATA` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Classification:** EXPECTED
- **Rationale:** El probe `no_data` consulta a propósito el prefix inexistente `__no_such_symbol__`; `[]` es la respuesta correcta del servicio (vacío benigno, no una divergencia cliente-vs-servicio).

- **Expected:** lista vacía para un prefix inexistente
- **Actual:** []
- **Diff:** empty/closed-market clasificado NO-DATA, nunca un crash

### F-02 -- market_data async vacío para prefix '__no_such_symbol__'

**Class:** `NO-DATA` . **Surface:** `async` . **Status:** `EXPECTED`

- **Classification:** EXPECTED
- **Rationale:** El probe `no_data` consulta a propósito el prefix inexistente `__no_such_symbol__`; `[]` es la respuesta correcta del servicio (vacío benigno, no una divergencia cliente-vs-servicio).

- **Expected:** lista vacía para un prefix inexistente
- **Actual:** []
- **Diff:** empty/closed-market clasificado NO-DATA, nunca un crash

### F-03 -- wire-only field active en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** MarketDataSnapshot y wire concuerdan en active
- **Actual:** wire-only: active
- **Diff:** path=<root> direction=wire-only

### F-04 -- wire-only field market_data en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** MarketDataSnapshot y wire concuerdan en market_data
- **Actual:** wire-only: market_data
- **Diff:** path=<root> direction=wire-only

### F-05 -- wire-only field market_id en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** MarketDataSnapshot y wire concuerdan en market_id
- **Actual:** wire-only: market_id
- **Diff:** path=<root> direction=wire-only

### F-06 -- wire-only field note en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** MarketDataSnapshot y wire concuerdan en note
- **Actual:** wire-only: note
- **Diff:** path=<root> direction=wire-only

### F-07 -- wire-only field staleness_seconds en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** MarketDataSnapshot y wire concuerdan en staleness_seconds
- **Actual:** wire-only: staleness_seconds
- **Diff:** path=<root> direction=wire-only

### F-08 -- model-only field businessDays en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en businessDays
- **Actual:** model-only: businessDays
- **Diff:** path=<root> direction=model-only

### F-09 -- wire-only field close en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en close
- **Actual:** wire-only: close
- **Diff:** path=<root> direction=wire-only

### F-10 -- wire-only field editable en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en editable
- **Actual:** wire-only: editable
- **Diff:** path=<root> direction=wire-only

### F-11 -- wire-only field enabled en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en enabled
- **Actual:** wire-only: enabled
- **Diff:** path=<root> direction=wire-only

### F-12 -- wire-only field env_bypass en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en env_bypass
- **Actual:** wire-only: env_bypass
- **Diff:** path=<root> direction=wire-only

### F-13 -- wire-only field open en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en open
- **Actual:** wire-only: open
- **Diff:** path=<root> direction=wire-only

### F-14 -- wire-only field pre_open_minutes en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en pre_open_minutes
- **Actual:** wire-only: pre_open_minutes
- **Diff:** path=<root> direction=wire-only

### F-15 -- wire-only field source en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en source
- **Actual:** wire-only: source
- **Diff:** path=<root> direction=wire-only

### F-16 -- wire-only field updated_at en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en updated_at
- **Actual:** wire-only: updated_at
- **Diff:** path=<root> direction=wire-only

### F-17 -- wire-only field updated_by en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en updated_by
- **Actual:** wire-only: updated_by
- **Diff:** path=<root> direction=wire-only

### F-18 -- wire-only field warnings en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en warnings
- **Actual:** wire-only: warnings
- **Diff:** path=<root> direction=wire-only

### F-19 -- model-only field entries en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** MarketDataSnapshot y wire concuerdan en entries
- **Actual:** model-only: entries
- **Diff:** path=<root> direction=model-only

### F-20 -- model-only field marketId en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** MarketDataSnapshot y wire concuerdan en marketId
- **Actual:** model-only: marketId
- **Diff:** path=<root> direction=model-only

### F-21 -- wire-only field active en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** MarketDataSnapshot y wire concuerdan en active
- **Actual:** wire-only: active
- **Diff:** path=<root> direction=wire-only

### F-22 -- wire-only field market_data en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** MarketDataSnapshot y wire concuerdan en market_data
- **Actual:** wire-only: market_data
- **Diff:** path=<root> direction=wire-only

### F-23 -- wire-only field market_id en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** MarketDataSnapshot y wire concuerdan en market_id
- **Actual:** wire-only: market_id
- **Diff:** path=<root> direction=wire-only

### F-24 -- wire-only field note en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** MarketDataSnapshot y wire concuerdan en note
- **Actual:** wire-only: note
- **Diff:** path=<root> direction=wire-only

### F-25 -- wire-only field staleness_seconds en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** MarketDataSnapshot y wire concuerdan en staleness_seconds
- **Actual:** wire-only: staleness_seconds
- **Diff:** path=<root> direction=wire-only

### F-26 -- model-only field businessDays en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en businessDays
- **Actual:** model-only: businessDays
- **Diff:** path=<root> direction=model-only

### F-27 -- wire-only field close en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en close
- **Actual:** wire-only: close
- **Diff:** path=<root> direction=wire-only

### F-28 -- wire-only field editable en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en editable
- **Actual:** wire-only: editable
- **Diff:** path=<root> direction=wire-only

### F-29 -- wire-only field enabled en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en enabled
- **Actual:** wire-only: enabled
- **Diff:** path=<root> direction=wire-only

### F-30 -- wire-only field env_bypass en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en env_bypass
- **Actual:** wire-only: env_bypass
- **Diff:** path=<root> direction=wire-only

### F-31 -- wire-only field open en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en open
- **Actual:** wire-only: open
- **Diff:** path=<root> direction=wire-only

### F-32 -- wire-only field pre_open_minutes en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en pre_open_minutes
- **Actual:** wire-only: pre_open_minutes
- **Diff:** path=<root> direction=wire-only

### F-33 -- wire-only field source en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en source
- **Actual:** wire-only: source
- **Diff:** path=<root> direction=wire-only

### F-34 -- wire-only field updated_at en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en updated_at
- **Actual:** wire-only: updated_at
- **Diff:** path=<root> direction=wire-only

### F-35 -- wire-only field updated_by en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en updated_by
- **Actual:** wire-only: updated_by
- **Diff:** path=<root> direction=wire-only

### F-36 -- wire-only field warnings en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

- **Expected:** CalendarConfig y wire concuerdan en warnings
- **Actual:** wire-only: warnings
- **Diff:** path=<root> direction=wire-only
<!-- END AUTO-GENERATED -->
