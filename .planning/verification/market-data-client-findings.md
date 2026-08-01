# Findings: market-data-client-client

## Run Context (ART)
- Timestamp: 2026-08-01T15:54:42.284490+00:00
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
| F-37 | SHAPE | sync | OPEN |
| F-38 | NO-DATA | sync | OPEN |
| F-39 | SHAPE | async | OPEN |
| F-40 | NO-DATA | async | OPEN |
| F-41 | ERROR-MAP | async | OPEN |
| F-42 | SHAPE | async | OPEN |
| F-43 | SHAPE | async | OPEN |
| F-44 | SHAPE | async | OPEN |
| F-45 | SHAPE | async | OPEN |
| F-46 | SHAPE | async | OPEN |
| F-47 | SHAPE | async | OPEN |
| F-48 | ERROR-MAP | async | EXPECTED |
| F-49 | ERROR-MAP | async | EXPECTED |
| F-50 | ERROR-MAP | async | EXPECTED |
| F-51 | ERROR-MAP | sync | OPEN |
| F-52 | SHAPE | sync | OPEN |
| F-53 | SHAPE | sync | OPEN |
| F-54 | SHAPE | sync | OPEN |
| F-55 | SHAPE | sync | OPEN |
| F-56 | SHAPE | sync | OPEN |
| F-57 | SHAPE | sync | OPEN |
| F-58 | ERROR-MAP | sync | EXPECTED |
| F-59 | ERROR-MAP | sync | EXPECTED |
| F-60 | ERROR-MAP | sync | EXPECTED |
| F-61 | SHAPE | both | EXPECTED |
| F-62 | SHAPE | both | EXPECTED |

## Detalle por hallazgo

### F-01 -- market_data vacío para prefix '__no_such_symbol__'

**Class:** `NO-DATA` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** lista vacía para un prefix inexistente
- **Actual:** []
- **Diff:** empty/closed-market clasificado NO-DATA, nunca un crash
- **Classification:** EXPECTED
- **Rationale:** El probe `no_data` consulta a propósito el prefix inexistente `__no_such_symbol__`; `[]` es la respuesta correcta del servicio (vacío benigno, no una divergencia cliente-vs-servicio).

### F-02 -- market_data async vacío para prefix '__no_such_symbol__'

**Class:** `NO-DATA` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** lista vacía para un prefix inexistente
- **Actual:** []
- **Diff:** empty/closed-market clasificado NO-DATA, nunca un crash
- **Classification:** EXPECTED
- **Rationale:** El probe `no_data` consulta a propósito el prefix inexistente `__no_such_symbol__`; `[]` es la respuesta correcta del servicio (vacío benigno, no una divergencia cliente-vs-servicio).

### F-03 -- wire-only field active en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** MarketDataSnapshot y wire concuerdan en active
- **Actual:** wire-only: active
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_models.py::test_from_api_marketdata_item_parses_new_fields
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-04 -- wire-only field market_data en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** MarketDataSnapshot y wire concuerdan en market_data
- **Actual:** wire-only: market_data
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_models.py::test_from_api_marketdata_item_parses_new_fields
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-05 -- wire-only field market_id en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** MarketDataSnapshot y wire concuerdan en market_id
- **Actual:** wire-only: market_id
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_models.py::test_from_api_marketdata_item_parses_new_fields
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-06 -- wire-only field note en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** MarketDataSnapshot y wire concuerdan en note
- **Actual:** wire-only: note
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_models.py::test_from_api_marketdata_item_parses_new_fields
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-07 -- wire-only field staleness_seconds en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** MarketDataSnapshot y wire concuerdan en staleness_seconds
- **Actual:** wire-only: staleness_seconds
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_models.py::test_from_api_marketdata_item_parses_new_fields
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-08 -- model-only field businessDays en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en businessDays
- **Actual:** model-only: businessDays
- **Diff:** path=<root> direction=model-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_field_set_matches_reconciled_wire
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-09 -- wire-only field close en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en close
- **Actual:** wire-only: close
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-10 -- wire-only field editable en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en editable
- **Actual:** wire-only: editable
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-11 -- wire-only field enabled en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en enabled
- **Actual:** wire-only: enabled
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-12 -- wire-only field env_bypass en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en env_bypass
- **Actual:** wire-only: env_bypass
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-13 -- wire-only field open en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en open
- **Actual:** wire-only: open
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-14 -- wire-only field pre_open_minutes en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en pre_open_minutes
- **Actual:** wire-only: pre_open_minutes
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-15 -- wire-only field source en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en source
- **Actual:** wire-only: source
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-16 -- wire-only field updated_at en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en updated_at
- **Actual:** wire-only: updated_at
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-17 -- wire-only field updated_by en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en updated_by
- **Actual:** wire-only: updated_by
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-18 -- wire-only field warnings en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en warnings
- **Actual:** wire-only: warnings
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-19 -- model-only field entries en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** MarketDataSnapshot y wire concuerdan en entries
- **Actual:** model-only: entries
- **Diff:** path=<root> direction=model-only
- **Regression:** packages/market-data-client/tests/test_models.py::test_from_api_latest_nodata_item
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-20 -- model-only field marketId en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** MarketDataSnapshot y wire concuerdan en marketId
- **Actual:** model-only: marketId
- **Diff:** path=<root> direction=model-only
- **Regression:** packages/market-data-client/tests/test_models.py::test_marketdata_snapshot_field_set_matches_reconciled_wire
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-21 -- wire-only field active en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** MarketDataSnapshot y wire concuerdan en active
- **Actual:** wire-only: active
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_models.py::test_from_api_marketdata_item_parses_new_fields
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-22 -- wire-only field market_data en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** MarketDataSnapshot y wire concuerdan en market_data
- **Actual:** wire-only: market_data
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_models.py::test_from_api_marketdata_item_parses_new_fields
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-23 -- wire-only field market_id en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** MarketDataSnapshot y wire concuerdan en market_id
- **Actual:** wire-only: market_id
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_models.py::test_from_api_marketdata_item_parses_new_fields
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-24 -- wire-only field note en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** MarketDataSnapshot y wire concuerdan en note
- **Actual:** wire-only: note
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_models.py::test_from_api_marketdata_item_parses_new_fields
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-25 -- wire-only field staleness_seconds en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** MarketDataSnapshot y wire concuerdan en staleness_seconds
- **Actual:** wire-only: staleness_seconds
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_models.py::test_from_api_marketdata_item_parses_new_fields
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-26 -- model-only field businessDays en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en businessDays
- **Actual:** model-only: businessDays
- **Diff:** path=<root> direction=model-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_field_set_matches_reconciled_wire
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-27 -- wire-only field close en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en close
- **Actual:** wire-only: close
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-28 -- wire-only field editable en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en editable
- **Actual:** wire-only: editable
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-29 -- wire-only field enabled en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en enabled
- **Actual:** wire-only: enabled
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-30 -- wire-only field env_bypass en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en env_bypass
- **Actual:** wire-only: env_bypass
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-31 -- wire-only field open en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en open
- **Actual:** wire-only: open
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-32 -- wire-only field pre_open_minutes en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en pre_open_minutes
- **Actual:** wire-only: pre_open_minutes
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-33 -- wire-only field source en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en source
- **Actual:** wire-only: source
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-34 -- wire-only field updated_at en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en updated_at
- **Actual:** wire-only: updated_at
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-35 -- wire-only field updated_by en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en updated_by
- **Actual:** wire-only: updated_by
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-36 -- wire-only field warnings en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** CalendarConfig y wire concuerdan en warnings
- **Actual:** wire-only: warnings
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated
- **Classification:** FIXED
- **Resolution:** Reconciliado contra el wire real de develop en quick task 260731-jim (commits `0852d43` MarketDataSnapshot + envelope-unwrap, `45c1885` CalendarConfig, `8c8e494` tests). Re-run en vivo 2026-07-31 confirma 0 divergencias SHAPE; 139 tests del paquete verdes.

### F-37 -- schema drift en get_market_data

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** {"count": "int", "items": [{"active": "bool", "entries": ["str"], "market_data": {"BI": [{"price": "int", "size": "int"}], "CL": {"date": "int", "price": "int"}, "HI": "int", "LA": {"date": "int", "price": "int", "size": "int"}, "LO": "int", "OF": [{"price": "int", "size": "int"}], "OI": "NoneType", "OP": "int", "SE": {"price": "int"}, "TV": "NoneType"}, "market_id": "str", "received_at": "str", "staleness_seconds": "float", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Actual:** {"count": "int", "items": [{"active": "bool", "entries": [], "market_data": "NoneType", "market_id": "str", "received_at": "NoneType", "staleness_seconds": "NoneType", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-38 -- market_data vacío para prefix '__no_such_symbol__'

**Class:** `NO-DATA` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** lista vacía para un prefix inexistente
- **Actual:** []
- **Diff:** empty/closed-market clasificado NO-DATA, nunca un crash

### F-39 -- schema drift en get_market_data

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** {"count": "int", "items": [{"active": "bool", "entries": ["str"], "market_data": {"BI": [{"price": "int", "size": "int"}], "CL": {"date": "int", "price": "int"}, "HI": "int", "LA": {"date": "int", "price": "int", "size": "int"}, "LO": "int", "OF": [{"price": "int", "size": "int"}], "OI": "NoneType", "OP": "int", "SE": {"price": "int"}, "TV": "NoneType"}, "market_id": "str", "received_at": "str", "staleness_seconds": "float", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Actual:** {"count": "int", "items": [{"active": "bool", "entries": [], "market_data": "NoneType", "market_id": "str", "received_at": "NoneType", "staleness_seconds": "NoneType", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-40 -- market_data async vacío para prefix '__no_such_symbol__'

**Class:** `NO-DATA` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** lista vacía para un prefix inexistente
- **Actual:** []
- **Diff:** empty/closed-market clasificado NO-DATA, nunca un crash

### F-41 -- create_symbol async parsea la respuesta de escritura con el parser de lectura

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** list[Symbol] con filas reales desde el body de POST /symbols
- **Actual:** body objeto JSON de 6 clave(s); parse_symbols_response devolvió 6 Symbol, 6 all-default
- **Diff:** parse_symbols_response itera el body: contra un objeto bare devuelve un Symbol all-default por clave (D-11; se captura, no se arregla acá)

### F-42 -- model-only field marketId en Symbol

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** Symbol y wire concuerdan en marketId
- **Actual:** model-only: marketId
- **Diff:** path=<root> direction=model-only

### F-43 -- wire-only field created_at en Symbol

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** Symbol y wire concuerdan en created_at
- **Actual:** wire-only: created_at
- **Diff:** path=<root> direction=wire-only

### F-44 -- wire-only field id en Symbol

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** Symbol y wire concuerdan en id
- **Actual:** wire-only: id
- **Diff:** path=<root> direction=wire-only

### F-45 -- wire-only field market_id en Symbol

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** Symbol y wire concuerdan en market_id
- **Actual:** wire-only: market_id
- **Diff:** path=<root> direction=wire-only

### F-46 -- wire-only field received_at en Symbol

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** Symbol y wire concuerdan en received_at
- **Actual:** wire-only: received_at
- **Diff:** path=<root> direction=wire-only

### F-47 -- wire-only field updated_at en Symbol

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** Symbol y wire concuerdan en updated_at
- **Actual:** wire-only: updated_at
- **Diff:** path=<root> direction=wire-only

### F-48 -- D-19 async: doble-fire de POST /calendar/config/preview devolvió bodies DISTINTOS

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** medición en vivo del flag idempotent=True de build_preview_calendar_config_request (DM-03/D-19)
- **Actual:** los dos previews de la MISMA ventana devolvieron bodies DISTINTOS
- **Diff:** evidencia medida para el plan 27-07; el flag NO se cambia acá (D-20)

### F-49 -- D-19 async: POST /calendar/holidays dedupea por fecha (1 fila tras doble-fire)

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** medición en vivo del flag idempotent=False de build_add_holidays_request (DM-03/D-19), por CONTEO de días leídos del envelope, no por status code
- **Actual:** 1 fila para 2099-12-30 tras dos POST idénticos: el server hace UPSERT por fecha
- **Diff:** idempotent=False en build_add_holidays_request es CONSERVADOR DE MÁS; el spec en vivo dice 'Add or update … Idempotent by date' y la medición lo confirma — el flip lo decide el plan 27-07 (D-20)

### F-50 -- D-19 async: el segundo DELETE /calendar/holidays/{day} devolvió 404

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** medición en vivo del flag idempotent=True de build_delete_holiday_request (DM-03/D-19)
- **Actual:** status observado en el segundo DELETE de 2099-12-30: 404
- **Diff:** idempotente en ESTADO pero no en STATUS: build_delete_holiday_request lleva idempotent=True, así que un retry del RetryTransport convertiría ese 404 en MarketDataAPIError (_core.raise_for_response). Evidencia para 27-07

### F-51 -- create_symbol parsea la respuesta de escritura con el parser de lectura

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** list[Symbol] con filas reales desde el body de POST /symbols
- **Actual:** body objeto JSON de 6 clave(s); parse_symbols_response devolvió 6 Symbol, 6 all-default
- **Diff:** parse_symbols_response itera el body: contra un objeto bare devuelve un Symbol all-default por clave (D-11; se captura, no se arregla acá)

### F-52 -- model-only field marketId en Symbol

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** Symbol y wire concuerdan en marketId
- **Actual:** model-only: marketId
- **Diff:** path=<root> direction=model-only

### F-53 -- wire-only field created_at en Symbol

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** Symbol y wire concuerdan en created_at
- **Actual:** wire-only: created_at
- **Diff:** path=<root> direction=wire-only

### F-54 -- wire-only field id en Symbol

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** Symbol y wire concuerdan en id
- **Actual:** wire-only: id
- **Diff:** path=<root> direction=wire-only

### F-55 -- wire-only field market_id en Symbol

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** Symbol y wire concuerdan en market_id
- **Actual:** wire-only: market_id
- **Diff:** path=<root> direction=wire-only

### F-56 -- wire-only field received_at en Symbol

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** Symbol y wire concuerdan en received_at
- **Actual:** wire-only: received_at
- **Diff:** path=<root> direction=wire-only

### F-57 -- wire-only field updated_at en Symbol

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** Symbol y wire concuerdan en updated_at
- **Actual:** wire-only: updated_at
- **Diff:** path=<root> direction=wire-only

### F-58 -- D-19 sync: doble-fire de POST /calendar/config/preview devolvió bodies DISTINTOS

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** medición en vivo del flag idempotent=True de build_preview_calendar_config_request (DM-03/D-19)
- **Actual:** los dos previews de la MISMA ventana devolvieron bodies DISTINTOS
- **Diff:** evidencia medida para el plan 27-07; el flag NO se cambia acá (D-20)

### F-59 -- D-19 sync: POST /calendar/holidays dedupea por fecha (1 fila tras doble-fire)

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** medición en vivo del flag idempotent=False de build_add_holidays_request (DM-03/D-19), por CONTEO de días leídos del envelope, no por status code
- **Actual:** 1 fila para 2099-12-29 tras dos POST idénticos: el server hace UPSERT por fecha
- **Diff:** idempotent=False en build_add_holidays_request es CONSERVADOR DE MÁS; el spec en vivo dice 'Add or update … Idempotent by date' y la medición lo confirma — el flip lo decide el plan 27-07 (D-20)

### F-60 -- D-19 sync: el segundo DELETE /calendar/holidays/{day} devolvió 404

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** medición en vivo del flag idempotent=True de build_delete_holiday_request (DM-03/D-19)
- **Actual:** status observado en el segundo DELETE de 2099-12-29: 404
- **Diff:** idempotente en ESTADO pero no en STATUS: build_delete_holiday_request lleva idempotent=True, así que un retry del RetryTransport convertiría ese 404 en MarketDataAPIError (_core.raise_for_response). Evidencia para 27-07

### F-61 -- política de snapshots de mutación y re-baseline deliberado de get-symbols.json (D-17/D-26)

**Class:** `SHAPE` . **Surface:** `both` . **Status:** `EXPECTED`

- **Expected:** los baselines write-once siguen detectando drift real en los endpoints de lectura de primera clase
- **Actual:** cada body de mutación y cada lectura de verificación FILTRADA usa un client_function dedicado, distinto por superficie, así que ninguno puede derivar el baseline de una lectura; get-calendar.json NO deriva porque schema_of muestrea sólo days[0] y el feriado de prueba tiene shape idéntica al item commiteado; get-symbols.json SÍ deriva de forma permanente, porque el símbolo revertido vive en active=False para siempre y probe_symbols_sync lee justamente con active=False
- **Diff:** get-symbols.json se RE-BASELINEA a propósito en el plan 27-07, no se excluye: excluirlo apagaría la detección de drift sobre un endpoint de lectura de primera clase, mientras que re-baselinearlo captura por primera vez la shape REAL de Symbol (hoy el baseline es 'schema': [])

### F-62 -- PUT/DELETE /calendar/config operator-gated fuera del run en vivo (D-06)

**Class:** `SHAPE` . **Surface:** `both` . **Status:** `EXPECTED`

- **Expected:** shape en vivo de set_calendar_config / delete_calendar_config verificada contra develop
- **Actual:** sin cobertura en vivo: DELETE resetea a defaults del servidor y no restaura el valor previo, asi que no sirve de cleanup para un PUT; un PUT real dejaria la config compartida de develop alterada
- **Diff:** limitación operativa reconocida, no drift detectado; ambos endpoints siguen cubiertos por packages/market-data-client/tests (mocked)
<!-- END AUTO-GENERATED -->
