# Findings: market-data-client-client

## Run Context (ART)
- Timestamp: 2026-08-27T01:54:10.152155+00:00
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
| F-37 | SHAPE | sync | EXPECTED |
| F-38 | NO-DATA | sync | EXPECTED |
| F-39 | SHAPE | async | EXPECTED |
| F-40 | NO-DATA | async | EXPECTED |
| F-41 | ERROR-MAP | async | FIXED |
| F-42 | SHAPE | async | FIXED |
| F-43 | SHAPE | async | FIXED |
| F-44 | SHAPE | async | FIXED |
| F-45 | SHAPE | async | FIXED |
| F-46 | SHAPE | async | FIXED |
| F-47 | SHAPE | async | FIXED |
| F-48 | ERROR-MAP | async | EXPECTED |
| F-49 | ERROR-MAP | async | FIXED |
| F-50 | ERROR-MAP | async | EXPECTED |
| F-51 | ERROR-MAP | sync | FIXED |
| F-52 | SHAPE | sync | FIXED |
| F-53 | SHAPE | sync | FIXED |
| F-54 | SHAPE | sync | FIXED |
| F-55 | SHAPE | sync | FIXED |
| F-56 | SHAPE | sync | FIXED |
| F-57 | SHAPE | sync | FIXED |
| F-58 | ERROR-MAP | sync | EXPECTED |
| F-59 | ERROR-MAP | sync | FIXED |
| F-60 | ERROR-MAP | sync | EXPECTED |
| F-61 | SHAPE | both | EXPECTED |
| F-62 | SHAPE | both | EXPECTED |
| F-63 | SHAPE | sync | EXPECTED |
| F-64 | NO-DATA | sync | EXPECTED |
| F-65 | SHAPE | async | EXPECTED |
| F-66 | NO-DATA | async | EXPECTED |
| F-67 | SHAPE | sync | NO-FIX |
| F-68 | SHAPE | sync | NO-FIX |
| F-69 | SHAPE | sync | NO-FIX |
| F-70 | SHAPE | sync | NO-FIX |
| F-71 | SHAPE | sync | NO-FIX |
| F-72 | SHAPE | sync | FIXED |
| F-73 | SHAPE | sync | FIXED |
| F-74 | SHAPE | sync | NO-FIX |
| F-75 | SHAPE | sync | FIXED |
| F-81 | SHAPE | sync | NO-FIX |
| F-82 | SHAPE | sync | FIXED |
| F-83 | SHAPE | sync | FIXED |
| F-84 | SHAPE | sync | NO-FIX |
| F-85 | SHAPE | sync | NO-FIX |
| F-86 | NO-DATA | sync | EXPECTED |
| F-87 | SHAPE | async | NO-FIX |
| F-88 | SHAPE | async | NO-FIX |
| F-89 | SHAPE | async | NO-FIX |
| F-90 | SHAPE | async | NO-FIX |
| F-91 | SHAPE | async | NO-FIX |
| F-92 | SHAPE | async | FIXED |
| F-93 | SHAPE | async | FIXED |
| F-94 | SHAPE | async | NO-FIX |
| F-95 | SHAPE | async | FIXED |
| F-101 | SHAPE | async | NO-FIX |
| F-102 | SHAPE | async | FIXED |
| F-103 | SHAPE | async | FIXED |
| F-104 | SHAPE | async | NO-FIX |
| F-105 | SHAPE | async | NO-FIX |
| F-106 | NO-DATA | async | EXPECTED |
| F-107 | ERROR-MAP | async | EXPECTED |
| F-108 | SHAPE | async | NO-FIX |
| F-109 | SHAPE | async | NO-FIX |
| F-110 | SHAPE | async | FIXED |
| F-111 | SHAPE | async | FIXED |
| F-121 | SHAPE | async | FIXED |
| F-122 | SHAPE | async | FIXED |
| F-123 | SHAPE | async | FIXED |
| F-124 | SHAPE | async | FIXED |
| F-125 | SHAPE | async | FIXED |
| F-126 | SHAPE | async | FIXED |
| F-127 | SHAPE | async | FIXED |
| F-128 | SHAPE | async | FIXED |
| F-129 | SHAPE | async | FIXED |
| F-130 | SHAPE | async | FIXED |
| F-131 | SHAPE | async | FIXED |
| F-132 | SHAPE | async | FIXED |
| F-133 | SHAPE | async | NO-FIX |
| F-135 | SHAPE | async | NO-FIX |
| F-138 | ERROR-MAP | sync | EXPECTED |
| F-139 | SHAPE | sync | NO-FIX |
| F-140 | SHAPE | sync | NO-FIX |
| F-141 | SHAPE | sync | FIXED |
| F-142 | SHAPE | sync | FIXED |
| F-152 | SHAPE | sync | FIXED |
| F-153 | SHAPE | sync | FIXED |
| F-154 | SHAPE | sync | FIXED |
| F-155 | SHAPE | sync | FIXED |
| F-156 | SHAPE | sync | FIXED |
| F-157 | SHAPE | sync | FIXED |
| F-158 | SHAPE | sync | FIXED |
| F-159 | SHAPE | sync | FIXED |
| F-160 | SHAPE | sync | FIXED |
| F-161 | SHAPE | sync | FIXED |
| F-162 | SHAPE | sync | FIXED |
| F-163 | SHAPE | sync | FIXED |
| F-164 | SHAPE | sync | NO-FIX |
| F-166 | SHAPE | sync | NO-FIX |
| F-173 | ERROR-MAP | sync | EXPECTED |
| F-178 | SHAPE | sync | NO-FIX |
| F-183 | SHAPE | sync | NO-FIX |
| F-184 | SHAPE | sync | NO-FIX |
| F-185 | NO-DATA | sync | EXPECTED |
| F-190 | SHAPE | async | NO-FIX |
| F-195 | SHAPE | async | NO-FIX |
| F-196 | SHAPE | async | NO-FIX |
| F-197 | NO-DATA | async | EXPECTED |

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

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** {"count": "int", "items": [{"active": "bool", "entries": ["str"], "market_data": {"BI": [{"price": "int", "size": "int"}], "CL": {"date": "int", "price": "int"}, "HI": "int", "LA": {"date": "int", "price": "int", "size": "int"}, "LO": "int", "OF": [{"price": "int", "size": "int"}], "OI": "NoneType", "OP": "int", "SE": {"price": "int"}, "TV": "NoneType"}, "market_id": "str", "received_at": "str", "staleness_seconds": "float", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Actual:** {"count": "int", "items": [{"active": "bool", "entries": [], "market_data": "NoneType", "market_id": "str", "received_at": "NoneType", "staleness_seconds": "NoneType", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)
- **Classification:** EXPECTED
- **Resolution:** NO es un cambio de shape del cliente ni del contrato: el KEY SET del baseline y el del run son IDÉNTICOS. Lo único que difiere son los TIPOS que `schema_of` infiere de los valores, porque el run corrió con el mercado sin datos y el server mandó `market_data: null`, `received_at: null`, `staleness_seconds: null` y `entries: []` donde el baseline tenía valores. Re-baselinear sería peor que dejarlo: fijaría la forma de mercado-cerrado y el baseline derivaría en cada run con datos. Se deja el baseline intacto (D-25) y el finding se cierra como artefacto de horario de mercado. Reaparecerá con un fid nuevo en cada run fuera de horario; eso es el diseño del emisor de drift, no un defecto pendiente.

### F-38 -- market_data vacío para prefix '__no_such_symbol__'

**Class:** `NO-DATA` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** lista vacía para un prefix inexistente
- **Actual:** []
- **Diff:** empty/closed-market clasificado NO-DATA, nunca un crash
- **Classification:** EXPECTED
- **Resolution:** Es el resultado ESPERADO del probe: consulta un prefix inexistente a propósito para verificar que un resultado vacío se clasifica `NO-DATA` y nunca crashea (D-09). No hay divergencia entre cliente y server. El probe registra la observación en cada run por diseño.

### F-39 -- schema drift en get_market_data

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** {"count": "int", "items": [{"active": "bool", "entries": ["str"], "market_data": {"BI": [{"price": "int", "size": "int"}], "CL": {"date": "int", "price": "int"}, "HI": "int", "LA": {"date": "int", "price": "int", "size": "int"}, "LO": "int", "OF": [{"price": "int", "size": "int"}], "OI": "NoneType", "OP": "int", "SE": {"price": "int"}, "TV": "NoneType"}, "market_id": "str", "received_at": "str", "staleness_seconds": "float", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Actual:** {"count": "int", "items": [{"active": "bool", "entries": [], "market_data": "NoneType", "market_id": "str", "received_at": "NoneType", "staleness_seconds": "NoneType", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)
- **Classification:** EXPECTED
- **Resolution:** NO es un cambio de shape del cliente ni del contrato: el KEY SET del baseline y el del run son IDÉNTICOS. Lo único que difiere son los TIPOS que `schema_of` infiere de los valores, porque el run corrió con el mercado sin datos y el server mandó `market_data: null`, `received_at: null`, `staleness_seconds: null` y `entries: []` donde el baseline tenía valores. Re-baselinear sería peor que dejarlo: fijaría la forma de mercado-cerrado y el baseline derivaría en cada run con datos. Se deja el baseline intacto (D-25) y el finding se cierra como artefacto de horario de mercado. Reaparecerá con un fid nuevo en cada run fuera de horario; eso es el diseño del emisor de drift, no un defecto pendiente.

### F-40 -- market_data async vacío para prefix '__no_such_symbol__'

**Class:** `NO-DATA` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** lista vacía para un prefix inexistente
- **Actual:** []
- **Diff:** empty/closed-market clasificado NO-DATA, nunca un crash
- **Classification:** EXPECTED
- **Resolution:** Es el resultado ESPERADO del probe: consulta un prefix inexistente a propósito para verificar que un resultado vacío se clasifica `NO-DATA` y nunca crashea (D-09). No hay divergencia entre cliente y server. El probe registra la observación en cada run por diseño.

### F-41 -- create_symbol async parsea la respuesta de escritura con el parser de lectura

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** list[Symbol] con filas reales desde el body de POST /symbols
- **Actual:** body objeto JSON de 6 clave(s); parse_symbols_response devolvió 6 Symbol, 6 all-default
- **Diff:** parse_symbols_response itera el body: contra un objeto bare devuelve un Symbol all-default por clave (D-11; se captura, no se arregla acá)
- **Regression:** packages/market-data-client/tests/test_symbols_write_async.py::test_create_symbol_returns_real_rows_not_key_blanks
- **Classification:** FIXED
- **Resolution:** `parse_symbols_response` reescrito en `_core.py`: en vez de iterar el body crudo recorre una escalera de shapes — envelope `items[]`, objeto symbol plano, lista bare, y colapso a `[]` para todo lo demás — espejando `parse_latest_response`. El tipo de retorno publicado `list[Symbol]` NO cambia (D-22): se desenvuelve el envelope en vez de pasarlo crudo, así que no se fuerza un major. Las tres mutaciones de symbols devuelven ahora filas pobladas en ambas superficies.

### F-42 -- model-only field marketId en Symbol

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** Symbol y wire concuerdan en marketId
- **Actual:** model-only: marketId
- **Diff:** path=<root> direction=model-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_symbol_market_id_alias_mirrors_wire_snake_case
- **Classification:** FIXED
- **Resolution:** NO se renombró: `Symbol` es superficie publicada desde v0.2.0 y un rename rompería consumidores (D-22). Se agregó el campo wire-correcto `market_id` AL LADO y se sobreescribió `Symbol.from_api` para espejar el valor del wire dentro del alias camelCase, que hasta ahora quedaba en `""` para siempre contra un payload real. El alias queda marcado deprecated y se remueve en el próximo MAJOR. El SHAPE-diff del driver excluye `marketId` del direction model-only vía `_DEPRECATED_ALIAS`, porque su ausencia del wire es por diseño y permanente.

### F-43 -- wire-only field created_at en Symbol

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** Symbol y wire concuerdan en created_at
- **Actual:** wire-only: created_at
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_symbol_from_api_populated_wire_row
- **Classification:** FIXED
- **Resolution:** `Symbol` reconciliado en `models.py` contra la primera fila poblada jamás observada (armed run LIVE-MUT-01, 2026-08-01): se agregaron los cinco campos wire-only — `id`, `market_id`, `created_at`, `updated_at`, `received_at` — con defaults, así que `from_api` sobre un payload parcial sigue sin levantar.

### F-44 -- wire-only field id en Symbol

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** Symbol y wire concuerdan en id
- **Actual:** wire-only: id
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_symbol_row_id_is_an_int_not_a_string
- **Classification:** FIXED
- **Resolution:** `Symbol` reconciliado en `models.py` contra la primera fila poblada jamás observada (armed run LIVE-MUT-01, 2026-08-01): se agregaron los cinco campos wire-only — `id`, `market_id`, `created_at`, `updated_at`, `received_at` — con defaults, así que `from_api` sobre un payload parcial sigue sin levantar. `id` es además el valor que espera `PATCH /symbols/{symbol_id}`: el parámetro de path del cliente se ensanchó a `int | str` en el mismo ciclo (D-09/D-22).

### F-45 -- wire-only field market_id en Symbol

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** Symbol y wire concuerdan en market_id
- **Actual:** wire-only: market_id
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_symbol_field_set_matches_reconciled_wire
- **Classification:** FIXED
- **Resolution:** `Symbol` reconciliado en `models.py` contra la primera fila poblada jamás observada (armed run LIVE-MUT-01, 2026-08-01): se agregaron los cinco campos wire-only — `id`, `market_id`, `created_at`, `updated_at`, `received_at` — con defaults, así que `from_api` sobre un payload parcial sigue sin levantar. El link apunta a la aserción de SET DE CAMPOS EXACTO a propósito: un test que sólo leyera los campos nuevos seguiría verde si faltara alguno o si el alias publicado se hubiera borrado en silencio.

### F-46 -- wire-only field received_at en Symbol

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** Symbol y wire concuerdan en received_at
- **Actual:** wire-only: received_at
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_symbol_received_at_is_a_wire_field_not_a_client_stamp
- **Classification:** FIXED
- **Resolution:** `Symbol` reconciliado en `models.py` contra la primera fila poblada jamás observada (armed run LIVE-MUT-01, 2026-08-01): se agregaron los cinco campos wire-only — `id`, `market_id`, `created_at`, `updated_at`, `received_at` — con defaults, así que `from_api` sobre un payload parcial sigue sin levantar. `received_at` acá es un campo de WIRE (el timestamp de ingesta del server), NO el stamp de cliente de `MarketDataSnapshot`: mismo nombre, procedencia opuesta. El docstring del módulo lo dice explícito para que nadie lo confunda.

### F-47 -- wire-only field updated_at en Symbol

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** Symbol y wire concuerdan en updated_at
- **Actual:** wire-only: updated_at
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_symbol_from_api_populated_wire_row
- **Classification:** FIXED
- **Resolution:** `Symbol` reconciliado en `models.py` contra la primera fila poblada jamás observada (armed run LIVE-MUT-01, 2026-08-01): se agregaron los cinco campos wire-only — `id`, `market_id`, `created_at`, `updated_at`, `received_at` — con defaults, así que `from_api` sobre un payload parcial sigue sin levantar.

### F-48 -- D-19 async: doble-fire de POST /calendar/config/preview devolvió bodies DISTINTOS

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** medición en vivo del flag idempotent=True de build_preview_calendar_config_request (DM-03/D-19)
- **Actual:** los dos previews de la MISMA ventana devolvieron bodies DISTINTOS
- **Diff:** evidencia medida para el plan 27-07; el flag NO se cambia acá (D-20)
- **Classification:** EXPECTED
- **Resolution:** ADJUDICADO, flag MANTENIDO. 27-06 midió la diferencia y dejó la causa explícitamente sin medir. La causa es CONTENIDO DEPENDIENTE DEL RELOJ, no persistencia: el body capturado es `{market_after:{is_open, local_time, next_transition, reason, session_close, session_open, state}, requires_confirmation, valid, warnings}`, y `local_time` / `next_transition` son proyecciones de reloj que necesariamente difieren entre dos llamadas separadas por milisegundos. Nada en ese body es un identificador de recurso ni un acuse de escritura. La evidencia decisiva es independiente de la hipótesis: el probe leyó `GET /calendar/config` antes y después del doble-fire y la encontró IDÉNTICA campo a campo. Body distinto con config igual es exactamente la firma de un endpoint compute-only, así que es replay-safe y `idempotent=True` se sostiene. El driver ahora reporta los NOMBRES de las rutas que difieren (nunca valores) para que la adjudicación sea re-chequeable en cada run.

### F-49 -- D-19 async: POST /calendar/holidays dedupea por fecha (1 fila tras doble-fire)

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** medición en vivo del flag idempotent=False de build_add_holidays_request (DM-03/D-19), por CONTEO de días leídos del envelope, no por status code
- **Actual:** 1 fila para 2099-12-30 tras dos POST idénticos: el server hace UPSERT por fecha
- **Diff:** idempotent=False en build_add_holidays_request es CONSERVADOR DE MÁS; el spec en vivo dice 'Add or update … Idempotent by date' y la medición lo confirma — el flip lo decide el plan 27-07 (D-20)
- **Regression:** packages/market-data-client/tests/test_calendar_write_async.py::test_add_holidays_retries_three_times_on_repeated_503
- **Classification:** FIXED
- **Resolution:** Flag CORREGIDO: `build_add_holidays_request` pasa de `idempotent=False` a `idempotent=True` (D-20 — la medición manda sobre el razonamiento de Phase 26). El conteo de filas del doble-fire dio 1 fila por fecha en ambas superficies, o sea el server hace upsert por fecha, tal como dice la prosa del spec en vivo. La dirección importa: el valor viejo era CONSERVADOR DE MÁS, no permisivo de más — costaba un retry perdido, nunca estado duplicado. El flip dejó al paquete sin ningún builder `idempotent=False`, así que el short-circuit del retry se re-fijó a nivel transport con specs sintéticas (`test_transport.py`), sync y async, para no borrar en silencio la única prueba de que el flag hace algo.

### F-50 -- D-19 async: el segundo DELETE /calendar/holidays/{day} devolvió 404

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** medición en vivo del flag idempotent=True de build_delete_holiday_request (DM-03/D-19)
- **Actual:** status observado en el segundo DELETE de 2099-12-30: 404
- **Diff:** idempotente en ESTADO pero no en STATUS: build_delete_holiday_request lleva idempotent=True, así que un retry del RetryTransport convertiría ese 404 en MarketDataAPIError (_core.raise_for_response). Evidencia para 27-07
- **Regression:** packages/market-data-client/tests/test_calendar_write_async.py::test_delete_holiday_retry_after_lost_response_surfaces_404
- **Classification:** EXPECTED
- **Resolution:** Flag MANTENIDO en `idempotent=True`, con la adjudicación escrita. Lo que el flag gobierna es la SEGURIDAD DE REPLAY DEL ESTADO, y por esa medida el endpoint califica: un replay no puede borrar un segundo día ni resucitar una fila. El 404 del segundo fire cambia la IDENTIDAD del error, no el resultado — sin retry el caller habría levantado igual sobre el 5xx transitorio. Pasarlo a `False` cambiaría cero seguridad de datos a cambio de perder cobertura de retry sobre fallos transitorios reales, o sea estrictamente peor. Queda EXPECTED (no hubo cambio de código que arreglar) pero con test de regresión que fija la consecuencia en ambas superficies.

### F-51 -- create_symbol parsea la respuesta de escritura con el parser de lectura

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** list[Symbol] con filas reales desde el body de POST /symbols
- **Actual:** body objeto JSON de 6 clave(s); parse_symbols_response devolvió 6 Symbol, 6 all-default
- **Diff:** parse_symbols_response itera el body: contra un objeto bare devuelve un Symbol all-default por clave (D-11; se captura, no se arregla acá)
- **Regression:** packages/market-data-client/tests/test_symbols_write.py::test_create_symbol_returns_real_rows_not_key_blanks
- **Classification:** FIXED
- **Resolution:** `parse_symbols_response` reescrito en `_core.py`: en vez de iterar el body crudo recorre una escalera de shapes — envelope `items[]`, objeto symbol plano, lista bare, y colapso a `[]` para todo lo demás — espejando `parse_latest_response`. El tipo de retorno publicado `list[Symbol]` NO cambia (D-22): se desenvuelve el envelope en vez de pasarlo crudo, así que no se fuerza un major. Las tres mutaciones de symbols devuelven ahora filas pobladas en ambas superficies.

### F-52 -- model-only field marketId en Symbol

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** Symbol y wire concuerdan en marketId
- **Actual:** model-only: marketId
- **Diff:** path=<root> direction=model-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_symbol_market_id_alias_mirrors_wire_snake_case
- **Classification:** FIXED
- **Resolution:** NO se renombró: `Symbol` es superficie publicada desde v0.2.0 y un rename rompería consumidores (D-22). Se agregó el campo wire-correcto `market_id` AL LADO y se sobreescribió `Symbol.from_api` para espejar el valor del wire dentro del alias camelCase, que hasta ahora quedaba en `""` para siempre contra un payload real. El alias queda marcado deprecated y se remueve en el próximo MAJOR. El SHAPE-diff del driver excluye `marketId` del direction model-only vía `_DEPRECATED_ALIAS`, porque su ausencia del wire es por diseño y permanente.

### F-53 -- wire-only field created_at en Symbol

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** Symbol y wire concuerdan en created_at
- **Actual:** wire-only: created_at
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_symbol_from_api_populated_wire_row
- **Classification:** FIXED
- **Resolution:** `Symbol` reconciliado en `models.py` contra la primera fila poblada jamás observada (armed run LIVE-MUT-01, 2026-08-01): se agregaron los cinco campos wire-only — `id`, `market_id`, `created_at`, `updated_at`, `received_at` — con defaults, así que `from_api` sobre un payload parcial sigue sin levantar.

### F-54 -- wire-only field id en Symbol

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** Symbol y wire concuerdan en id
- **Actual:** wire-only: id
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_symbol_row_id_is_an_int_not_a_string
- **Classification:** FIXED
- **Resolution:** `Symbol` reconciliado en `models.py` contra la primera fila poblada jamás observada (armed run LIVE-MUT-01, 2026-08-01): se agregaron los cinco campos wire-only — `id`, `market_id`, `created_at`, `updated_at`, `received_at` — con defaults, así que `from_api` sobre un payload parcial sigue sin levantar. `id` es además el valor que espera `PATCH /symbols/{symbol_id}`: el parámetro de path del cliente se ensanchó a `int | str` en el mismo ciclo (D-09/D-22).

### F-55 -- wire-only field market_id en Symbol

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** Symbol y wire concuerdan en market_id
- **Actual:** wire-only: market_id
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_symbol_field_set_matches_reconciled_wire
- **Classification:** FIXED
- **Resolution:** `Symbol` reconciliado en `models.py` contra la primera fila poblada jamás observada (armed run LIVE-MUT-01, 2026-08-01): se agregaron los cinco campos wire-only — `id`, `market_id`, `created_at`, `updated_at`, `received_at` — con defaults, así que `from_api` sobre un payload parcial sigue sin levantar. El link apunta a la aserción de SET DE CAMPOS EXACTO a propósito: un test que sólo leyera los campos nuevos seguiría verde si faltara alguno o si el alias publicado se hubiera borrado en silencio.

### F-56 -- wire-only field received_at en Symbol

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** Symbol y wire concuerdan en received_at
- **Actual:** wire-only: received_at
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_symbol_received_at_is_a_wire_field_not_a_client_stamp
- **Classification:** FIXED
- **Resolution:** `Symbol` reconciliado en `models.py` contra la primera fila poblada jamás observada (armed run LIVE-MUT-01, 2026-08-01): se agregaron los cinco campos wire-only — `id`, `market_id`, `created_at`, `updated_at`, `received_at` — con defaults, así que `from_api` sobre un payload parcial sigue sin levantar. `received_at` acá es un campo de WIRE (el timestamp de ingesta del server), NO el stamp de cliente de `MarketDataSnapshot`: mismo nombre, procedencia opuesta. El docstring del módulo lo dice explícito para que nadie lo confunda.

### F-57 -- wire-only field updated_at en Symbol

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** Symbol y wire concuerdan en updated_at
- **Actual:** wire-only: updated_at
- **Diff:** path=<root> direction=wire-only
- **Regression:** packages/market-data-client/tests/test_reference_models.py::test_symbol_from_api_populated_wire_row
- **Classification:** FIXED
- **Resolution:** `Symbol` reconciliado en `models.py` contra la primera fila poblada jamás observada (armed run LIVE-MUT-01, 2026-08-01): se agregaron los cinco campos wire-only — `id`, `market_id`, `created_at`, `updated_at`, `received_at` — con defaults, así que `from_api` sobre un payload parcial sigue sin levantar.

### F-58 -- D-19 sync: doble-fire de POST /calendar/config/preview devolvió bodies DISTINTOS

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** medición en vivo del flag idempotent=True de build_preview_calendar_config_request (DM-03/D-19)
- **Actual:** los dos previews de la MISMA ventana devolvieron bodies DISTINTOS
- **Diff:** evidencia medida para el plan 27-07; el flag NO se cambia acá (D-20)
- **Classification:** EXPECTED
- **Resolution:** ADJUDICADO, flag MANTENIDO. 27-06 midió la diferencia y dejó la causa explícitamente sin medir. La causa es CONTENIDO DEPENDIENTE DEL RELOJ, no persistencia: el body capturado es `{market_after:{is_open, local_time, next_transition, reason, session_close, session_open, state}, requires_confirmation, valid, warnings}`, y `local_time` / `next_transition` son proyecciones de reloj que necesariamente difieren entre dos llamadas separadas por milisegundos. Nada en ese body es un identificador de recurso ni un acuse de escritura. La evidencia decisiva es independiente de la hipótesis: el probe leyó `GET /calendar/config` antes y después del doble-fire y la encontró IDÉNTICA campo a campo. Body distinto con config igual es exactamente la firma de un endpoint compute-only, así que es replay-safe y `idempotent=True` se sostiene. El driver ahora reporta los NOMBRES de las rutas que difieren (nunca valores) para que la adjudicación sea re-chequeable en cada run.

### F-59 -- D-19 sync: POST /calendar/holidays dedupea por fecha (1 fila tras doble-fire)

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** medición en vivo del flag idempotent=False de build_add_holidays_request (DM-03/D-19), por CONTEO de días leídos del envelope, no por status code
- **Actual:** 1 fila para 2099-12-29 tras dos POST idénticos: el server hace UPSERT por fecha
- **Diff:** idempotent=False en build_add_holidays_request es CONSERVADOR DE MÁS; el spec en vivo dice 'Add or update … Idempotent by date' y la medición lo confirma — el flip lo decide el plan 27-07 (D-20)
- **Regression:** packages/market-data-client/tests/test_calendar_write.py::test_add_holidays_retries_three_times_on_repeated_503
- **Classification:** FIXED
- **Resolution:** Flag CORREGIDO: `build_add_holidays_request` pasa de `idempotent=False` a `idempotent=True` (D-20 — la medición manda sobre el razonamiento de Phase 26). El conteo de filas del doble-fire dio 1 fila por fecha en ambas superficies, o sea el server hace upsert por fecha, tal como dice la prosa del spec en vivo. La dirección importa: el valor viejo era CONSERVADOR DE MÁS, no permisivo de más — costaba un retry perdido, nunca estado duplicado. El flip dejó al paquete sin ningún builder `idempotent=False`, así que el short-circuit del retry se re-fijó a nivel transport con specs sintéticas (`test_transport.py`), sync y async, para no borrar en silencio la única prueba de que el flag hace algo.

### F-60 -- D-19 sync: el segundo DELETE /calendar/holidays/{day} devolvió 404

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** medición en vivo del flag idempotent=True de build_delete_holiday_request (DM-03/D-19)
- **Actual:** status observado en el segundo DELETE de 2099-12-29: 404
- **Diff:** idempotente en ESTADO pero no en STATUS: build_delete_holiday_request lleva idempotent=True, así que un retry del RetryTransport convertiría ese 404 en MarketDataAPIError (_core.raise_for_response). Evidencia para 27-07
- **Regression:** packages/market-data-client/tests/test_calendar_write.py::test_delete_holiday_retry_after_lost_response_surfaces_404
- **Classification:** EXPECTED
- **Resolution:** Flag MANTENIDO en `idempotent=True`, con la adjudicación escrita. Lo que el flag gobierna es la SEGURIDAD DE REPLAY DEL ESTADO, y por esa medida el endpoint califica: un replay no puede borrar un segundo día ni resucitar una fila. El 404 del segundo fire cambia la IDENTIDAD del error, no el resultado — sin retry el caller habría levantado igual sobre el 5xx transitorio. Pasarlo a `False` cambiaría cero seguridad de datos a cambio de perder cobertura de retry sobre fallos transitorios reales, o sea estrictamente peor. Queda EXPECTED (no hubo cambio de código que arreglar) pero con test de regresión que fija la consecuencia en ambas superficies.

### F-61 -- política de snapshots de mutación y re-baseline deliberado de get-symbols.json (D-17/D-26)

**Class:** `SHAPE` . **Surface:** `both` . **Status:** `EXPECTED`

- **Expected:** los baselines write-once siguen detectando drift real en los endpoints de lectura de primera clase
- **Actual:** cada body de mutación y cada lectura de verificación FILTRADA usa un client_function dedicado, distinto por superficie, así que ninguno puede derivar el baseline de una lectura; get-calendar.json NO deriva porque schema_of muestrea sólo days[0] y el feriado de prueba tiene shape idéntica al item commiteado; get-symbols.json SÍ deriva de forma permanente, porque el símbolo revertido vive en active=False para siempre y probe_symbols_sync lee justamente con active=False
- **Diff:** get-symbols.json se RE-BASELINEA a propósito en el plan 27-07, no se excluye: excluirlo apagaría la detección de drift sobre un endpoint de lectura de primera clase, mientras que re-baselinearlo captura por primera vez la shape REAL de Symbol (hoy el baseline es 'schema': [])
- **Classification:** EXPECTED
- **Resolution:** Re-baseline EJECUTADO en el plan 27-07: `get-symbols.json` se borró antes del run confirmatorio para que el camino write-once del driver lo re-capturara, y el nuevo baseline registra por primera vez la shape REAL de una fila de `Symbol` (el committed anterior era `"schema": []`, capturado contra un catálogo vacío). Es un re-baseline y no una exclusión a propósito: excluir `get_symbols` apagaría la detección de drift sobre un endpoint de lectura de primera clase, mientras que re-baselinearlo la restaura. La predicción de que `get-calendar.json` NO deriva se verificó contra el run en vez de asumirse.

### F-62 -- PUT/DELETE /calendar/config operator-gated fuera del run en vivo (D-06)

**Class:** `SHAPE` . **Surface:** `both` . **Status:** `EXPECTED`

- **Expected:** shape en vivo de set_calendar_config / delete_calendar_config verificada contra develop
- **Actual:** sin cobertura en vivo: DELETE resetea a defaults del servidor y no restaura el valor previo, asi que no sirve de cleanup para un PUT; un PUT real dejaria la config compartida de develop alterada
- **Diff:** limitación operativa reconocida, no drift detectado; ambos endpoints siguen cubiertos por packages/market-data-client/tests (mocked)
- **Classification:** EXPECTED
- **Resolution:** Limitación operativa reconocida, sin cambios en 27-07 y fuera del alcance autorizado por el operator: `PUT`/`DELETE /calendar/config` siguen prohibidos en el run armado (D-06). El par sigue cubierto por tests mockeados in-package. La cobertura en vivo requiere una decisión de operator sobre alterar la config compartida de develop.

### F-63 -- schema drift en get_market_data

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** {"count": "int", "items": [{"active": "bool", "entries": ["str"], "market_data": {"BI": [{"price": "int", "size": "int"}], "CL": {"date": "int", "price": "int"}, "HI": "int", "LA": {"date": "int", "price": "int", "size": "int"}, "LO": "int", "OF": [{"price": "int", "size": "int"}], "OI": "NoneType", "OP": "int", "SE": {"price": "int"}, "TV": "NoneType"}, "market_id": "str", "received_at": "str", "staleness_seconds": "float", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Actual:** {"count": "int", "items": [{"active": "bool", "entries": [], "market_data": "NoneType", "market_id": "str", "received_at": "NoneType", "staleness_seconds": "NoneType", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)
- **Classification:** EXPECTED
- **Resolution:** Misma condición ya adjudicada en F-37/F-39: el KEY SET del baseline y el del run son IDÉNTICOS y sólo difieren los TIPOS que `schema_of` infiere de los valores, según haya o no datos de mercado al momento de leer. No es drift de contrato ni del cliente. El baseline NO se sobreescribe (D-25). El emisor de drift asigna un fid NUEVO en cada run a propósito y no dedupea por título: dos drifts con el mismo título pero distinto schema real son hallazgos distintos, y colapsarlos por título haría desaparecer en silencio al segundo.

### F-64 -- market_data vacío para prefix '__no_such_symbol__'

**Class:** `NO-DATA` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** lista vacía para un prefix inexistente
- **Actual:** []
- **Diff:** empty/closed-market clasificado NO-DATA, nunca un crash
- **Classification:** EXPECTED
- **Resolution:** Misma condición ya adjudicada en F-38/F-40: es el resultado ESPERADO del probe, que consulta un prefix inexistente a propósito para verificar que un resultado vacío se clasifica `NO-DATA` y nunca crashea (D-09). El probe registra la observación en cada run por diseño.

### F-65 -- schema drift en get_market_data

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** {"count": "int", "items": [{"active": "bool", "entries": ["str"], "market_data": {"BI": [{"price": "int", "size": "int"}], "CL": {"date": "int", "price": "int"}, "HI": "int", "LA": {"date": "int", "price": "int", "size": "int"}, "LO": "int", "OF": [{"price": "int", "size": "int"}], "OI": "NoneType", "OP": "int", "SE": {"price": "int"}, "TV": "NoneType"}, "market_id": "str", "received_at": "str", "staleness_seconds": "float", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Actual:** {"count": "int", "items": [{"active": "bool", "entries": [], "market_data": "NoneType", "market_id": "str", "received_at": "NoneType", "staleness_seconds": "NoneType", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)
- **Classification:** EXPECTED
- **Resolution:** Misma condición ya adjudicada en F-37/F-39: el KEY SET del baseline y el del run son IDÉNTICOS y sólo difieren los TIPOS que `schema_of` infiere de los valores, según haya o no datos de mercado al momento de leer. No es drift de contrato ni del cliente. El baseline NO se sobreescribe (D-25). El emisor de drift asigna un fid NUEVO en cada run a propósito y no dedupea por título: dos drifts con el mismo título pero distinto schema real son hallazgos distintos, y colapsarlos por título haría desaparecer en silencio al segundo.

### F-66 -- market_data async vacío para prefix '__no_such_symbol__'

**Class:** `NO-DATA` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** lista vacía para un prefix inexistente
- **Actual:** []
- **Diff:** empty/closed-market clasificado NO-DATA, nunca un crash
- **Classification:** EXPECTED
- **Resolution:** Misma condición ya adjudicada en F-38/F-40: es el resultado ESPERADO del probe, que consulta un prefix inexistente a propósito para verificar que un resultado vacío se clasifica `NO-DATA` y nunca crashea (D-09). El probe registra la observación en cada run por diseño.

### F-67 -- HealthFeed.symbols_never_delivered: extra (declared=-, observed=int) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent int
- **Diff:** - -> int at HealthFeed.symbols_never_delivered via /health/feed

### F-68 -- FeedIngestor.ingestor.last_error_age_seconds: extra (declared=-, observed=int) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent int
- **Diff:** - -> int at FeedIngestor.ingestor.last_error_age_seconds via /health/feed

### F-69 -- FeedIngestor.ingestor.last_error_at: extra (declared=-, observed=str) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent str
- **Diff:** - -> str at FeedIngestor.ingestor.last_error_at via /health/feed

### F-70 -- FeedIngestor.ingestor.subscription: extra (declared=-, observed=dict) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent dict
- **Diff:** - -> dict at FeedIngestor.ingestor.subscription via /health/feed

### F-71 -- schema drift en get_health_feed

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** {"active_symbols": "int", "ingestor": {"connected": "bool", "frames_total": "int", "heartbeat_age_seconds": "float", "last_error": "NoneType", "last_frame_age_seconds": "float", "last_frame_at": "str", "market": {"enabled": "bool", "is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}, "pipeline": {"batch_interval_ms": "int", "conserved": "bool", "flushes": "int", "frames_accepted": "int", "frames_coalesced": "int", "frames_unknown_symbol": "int", "last_flush_ms": "float", "last_write_at": "str", "last_write_error": "NoneType", "pending": "int", "pending_peak": "int", "rows_skipped_stale": "int"}, "present": "bool", "reason": "str", "reconnects": "int", "rows_written": "int", "started_at": "str", "state": "str", "symbols_subscribed": "int", "uptime_seconds": "int"}, "newest_received_at": "str", "oldest_received_at": "str", "staleness_seconds": "float", "status": "str", "symbols_with_data": "int"}
- **Actual:** {"active_symbols": "int", "ingestor": {"connected": "bool", "frames_total": "int", "heartbeat_age_seconds": "float", "last_error": "str", "last_error_age_seconds": "int", "last_error_at": "str", "last_frame_age_seconds": "float", "last_frame_at": "str", "market": {"enabled": "bool", "is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}, "pipeline": {"batch_interval_ms": "int", "conserved": "bool", "flushes": "int", "frames_accepted": "int", "frames_coalesced": "int", "frames_unknown_symbol": "int", "last_flush_ms": "float", "last_write_at": "str", "last_write_error": "NoneType", "pending": "int", "pending_peak": "int", "rows_skipped_stale": "int"}, "present": "bool", "reason": "str", "reconnects": "int", "rows_written": "int", "started_at": "str", "state": "str", "subscription": {"chunk_size": "int", "chunks": "int", "confirm_seconds": "int", "delivered_count": "int", "forced_reconnects": "int", "last_reconnect_reason": "str", "quarantined_count": "int", "quarantined_symbols": ["str"], "requested": "int", "sent": "int", "smd_rejections": "int", "smd_resends": "int", "smd_unattributed": "int", "unconfirmed_count": "int", "unconfirmed_symbols": []}, "symbols_subscribed": "int", "uptime_seconds": "int"}, "newest_received_at": "str", "oldest_received_at": "str", "staleness_seconds": "float", "status": "str", "symbols_never_delivered": "int", "symbols_with_data": "int"}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-72 -- MarketDataSnapshot.staleness_seconds: missing (declared=float, observed=NoneType) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares float
- **Actual:** wire sent NoneType
- **Diff:** float -> NoneType at MarketDataSnapshot.staleness_seconds via /marketdata
- **Regression:** packages/market-data-client/tests/test_snapshot_no_data_row.py::test_no_data_row_keeps_its_nulls

### F-73 -- MarketDataSnapshot.market_data: missing (declared=dict, observed=NoneType) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares dict
- **Actual:** wire sent NoneType
- **Diff:** dict -> NoneType at MarketDataSnapshot.market_data via /marketdata
- **Regression:** packages/market-data-client/tests/test_snapshot_no_data_row.py::test_no_data_row_keeps_its_nulls

### F-74 -- schema drift en get_market_data

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** {"count": "int", "items": [{"active": "bool", "entries": ["str"], "market_data": {"BI": [{"price": "int", "size": "int"}], "CL": {"date": "int", "price": "int"}, "HI": "int", "LA": {"date": "int", "price": "int", "size": "int"}, "LO": "int", "OF": [{"price": "int", "size": "int"}], "OI": "NoneType", "OP": "int", "SE": {"price": "int"}, "TV": "NoneType"}, "market_id": "str", "received_at": "str", "staleness_seconds": "float", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Actual:** {"count": "int", "items": [{"active": "bool", "entries": [], "market_data": "NoneType", "market_id": "str", "received_at": "NoneType", "staleness_seconds": "NoneType", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-75 -- MarketDataSnapshot.entries: missing (declared=list, observed=NoneType) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares list
- **Actual:** wire sent NoneType
- **Diff:** list -> NoneType at MarketDataSnapshot.entries via /marketdata/latest
- **Regression:** packages/market-data-client/tests/test_snapshot_no_data_row.py::test_no_data_row_keeps_its_nulls

### F-81 -- schema drift en get_latest

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** [{"active": "NoneType", "market_data": "NoneType", "market_id": "NoneType", "note": "str", "received_at": "NoneType", "staleness_seconds": "NoneType", "symbol": "str"}]
- **Actual:** [{"active": "bool", "market_data": "NoneType", "market_id": "str", "received_at": "NoneType", "staleness_seconds": "NoneType", "symbol": "str"}]
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-82 -- Instrument: non_dict (declared=Instrument, observed=str) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares Instrument
- **Actual:** wire sent str
- **Diff:** Instrument -> str at Instrument via /instruments
- **Regression:** packages/market-data-client/tests/test_reference_envelope_unwrap.py::test_get_instruments_unwraps_the_items_envelope

### F-83 -- Segment: non_dict (declared=Segment, observed=str) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares Segment
- **Actual:** wire sent str
- **Diff:** Segment -> str at Segment via /instruments/segments
- **Regression:** packages/market-data-client/tests/test_reference_envelope_unwrap.py::test_get_segments_unwraps_the_segments_envelope

### F-84 -- schema drift en get_calendar

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** {"config": {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": []}, "coverage": {"current_year_covered": "bool", "warning": "NoneType", "years": ["int"]}, "days": [{"close_time": "NoneType", "closed": "bool", "day": "str", "description": "str", "open_time": "NoneType"}], "market": {"is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}}
- **Actual:** {"config": {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": ["str"]}, "coverage": {"current_year_covered": "bool", "warning": "NoneType", "years": ["int"]}, "days": [{"close_time": "NoneType", "closed": "bool", "day": "str", "description": "str", "open_time": "NoneType"}], "market": {"is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-85 -- schema drift en get_calendar_config

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": []}
- **Actual:** {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": ["str"]}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-86 -- market_data vacío para prefix '__no_such_symbol__'

**Class:** `NO-DATA` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** lista vacía para un prefix inexistente
- **Actual:** []
- **Diff:** empty/closed-market clasificado NO-DATA, nunca un crash

### F-87 -- HealthFeed.symbols_never_delivered: extra (declared=-, observed=int) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent int
- **Diff:** - -> int at HealthFeed.symbols_never_delivered via /health/feed

### F-88 -- FeedIngestor.ingestor.last_error_age_seconds: extra (declared=-, observed=int) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent int
- **Diff:** - -> int at FeedIngestor.ingestor.last_error_age_seconds via /health/feed

### F-89 -- FeedIngestor.ingestor.last_error_at: extra (declared=-, observed=str) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent str
- **Diff:** - -> str at FeedIngestor.ingestor.last_error_at via /health/feed

### F-90 -- FeedIngestor.ingestor.subscription: extra (declared=-, observed=dict) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent dict
- **Diff:** - -> dict at FeedIngestor.ingestor.subscription via /health/feed

### F-91 -- schema drift en get_health_feed

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** {"active_symbols": "int", "ingestor": {"connected": "bool", "frames_total": "int", "heartbeat_age_seconds": "float", "last_error": "NoneType", "last_frame_age_seconds": "float", "last_frame_at": "str", "market": {"enabled": "bool", "is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}, "pipeline": {"batch_interval_ms": "int", "conserved": "bool", "flushes": "int", "frames_accepted": "int", "frames_coalesced": "int", "frames_unknown_symbol": "int", "last_flush_ms": "float", "last_write_at": "str", "last_write_error": "NoneType", "pending": "int", "pending_peak": "int", "rows_skipped_stale": "int"}, "present": "bool", "reason": "str", "reconnects": "int", "rows_written": "int", "started_at": "str", "state": "str", "symbols_subscribed": "int", "uptime_seconds": "int"}, "newest_received_at": "str", "oldest_received_at": "str", "staleness_seconds": "float", "status": "str", "symbols_with_data": "int"}
- **Actual:** {"active_symbols": "int", "ingestor": {"connected": "bool", "frames_total": "int", "heartbeat_age_seconds": "float", "last_error": "str", "last_error_age_seconds": "int", "last_error_at": "str", "last_frame_age_seconds": "float", "last_frame_at": "str", "market": {"enabled": "bool", "is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}, "pipeline": {"batch_interval_ms": "int", "conserved": "bool", "flushes": "int", "frames_accepted": "int", "frames_coalesced": "int", "frames_unknown_symbol": "int", "last_flush_ms": "float", "last_write_at": "str", "last_write_error": "NoneType", "pending": "int", "pending_peak": "int", "rows_skipped_stale": "int"}, "present": "bool", "reason": "str", "reconnects": "int", "rows_written": "int", "started_at": "str", "state": "str", "subscription": {"chunk_size": "int", "chunks": "int", "confirm_seconds": "int", "delivered_count": "int", "forced_reconnects": "int", "last_reconnect_reason": "str", "quarantined_count": "int", "quarantined_symbols": ["str"], "requested": "int", "sent": "int", "smd_rejections": "int", "smd_resends": "int", "smd_unattributed": "int", "unconfirmed_count": "int", "unconfirmed_symbols": []}, "symbols_subscribed": "int", "uptime_seconds": "int"}, "newest_received_at": "str", "oldest_received_at": "str", "staleness_seconds": "float", "status": "str", "symbols_never_delivered": "int", "symbols_with_data": "int"}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-92 -- MarketDataSnapshot.staleness_seconds: missing (declared=float, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares float
- **Actual:** wire sent NoneType
- **Diff:** float -> NoneType at MarketDataSnapshot.staleness_seconds via /marketdata
- **Regression:** packages/market-data-client/tests/test_snapshot_no_data_row.py::test_no_data_row_keeps_its_nulls_async

### F-93 -- MarketDataSnapshot.market_data: missing (declared=dict, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares dict
- **Actual:** wire sent NoneType
- **Diff:** dict -> NoneType at MarketDataSnapshot.market_data via /marketdata
- **Regression:** packages/market-data-client/tests/test_snapshot_no_data_row.py::test_no_data_row_keeps_its_nulls_async

### F-94 -- schema drift en get_market_data

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** {"count": "int", "items": [{"active": "bool", "entries": ["str"], "market_data": {"BI": [{"price": "int", "size": "int"}], "CL": {"date": "int", "price": "int"}, "HI": "int", "LA": {"date": "int", "price": "int", "size": "int"}, "LO": "int", "OF": [{"price": "int", "size": "int"}], "OI": "NoneType", "OP": "int", "SE": {"price": "int"}, "TV": "NoneType"}, "market_id": "str", "received_at": "str", "staleness_seconds": "float", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Actual:** {"count": "int", "items": [{"active": "bool", "entries": [], "market_data": "NoneType", "market_id": "str", "received_at": "NoneType", "staleness_seconds": "NoneType", "symbol": "str"}], "limit": "int", "offset": "int", "total": "int"}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-95 -- MarketDataSnapshot.entries: missing (declared=list, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares list
- **Actual:** wire sent NoneType
- **Diff:** list -> NoneType at MarketDataSnapshot.entries via /marketdata/latest
- **Regression:** packages/market-data-client/tests/test_snapshot_no_data_row.py::test_no_data_row_keeps_its_nulls_async

### F-101 -- schema drift en get_latest

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** [{"active": "NoneType", "market_data": "NoneType", "market_id": "NoneType", "note": "str", "received_at": "NoneType", "staleness_seconds": "NoneType", "symbol": "str"}]
- **Actual:** [{"active": "bool", "market_data": "NoneType", "market_id": "str", "received_at": "NoneType", "staleness_seconds": "NoneType", "symbol": "str"}]
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-102 -- Instrument: non_dict (declared=Instrument, observed=str) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares Instrument
- **Actual:** wire sent str
- **Diff:** Instrument -> str at Instrument via /instruments
- **Regression:** packages/market-data-client/tests/test_reference_envelope_unwrap.py::test_get_instruments_unwraps_the_items_envelope_async

### F-103 -- Segment: non_dict (declared=Segment, observed=str) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares Segment
- **Actual:** wire sent str
- **Diff:** Segment -> str at Segment via /instruments/segments
- **Regression:** packages/market-data-client/tests/test_reference_envelope_unwrap.py::test_get_segments_unwraps_the_segments_envelope_async

### F-104 -- schema drift en get_calendar

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** {"config": {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": []}, "coverage": {"current_year_covered": "bool", "warning": "NoneType", "years": ["int"]}, "days": [{"close_time": "NoneType", "closed": "bool", "day": "str", "description": "str", "open_time": "NoneType"}], "market": {"is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}}
- **Actual:** {"config": {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": ["str"]}, "coverage": {"current_year_covered": "bool", "warning": "NoneType", "years": ["int"]}, "days": [{"close_time": "NoneType", "closed": "bool", "day": "str", "description": "str", "open_time": "NoneType"}], "market": {"is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-105 -- schema drift en get_calendar_config

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": []}
- **Actual:** {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": ["str"]}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-106 -- market_data async vacío para prefix '__no_such_symbol__'

**Class:** `NO-DATA` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** lista vacía para un prefix inexistente
- **Actual:** []
- **Diff:** empty/closed-market clasificado NO-DATA, nunca un crash

### F-107 -- create_symbol_async: MarketDataAPIError inesperado

**Class:** `ERROR-MAP` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** 200 OK
- **Actual:** MarketDataAPIError('[422] {"detail":{"message":"el exchange no acepta estos símbolos; suscribirlos rechazaría el lote `smd` completo (docs/11-open-questions.md Q7). Usá ?force=true para guardarlos igual.","rejected":[{"symbol":"GSDPROBE/P27-ASYNC","market_id":"ROFX","reason":"el exchange no lista este símbolo (normalmente significa que el contrato venció); suscribirlo rechaza el lote entero y silencia hasta 50 símbolos válidos"}]}}')
- **Diff:** type=MarketDataAPIError

### F-108 -- schema drift en create_symbols_batch_async_response

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** {"created": "int", "items": [{"active": "bool", "created": "bool", "id": "int", "market_id": "str", "symbol": "str"}], "note": "str", "reactivated": "int", "requested": "int"}
- **Actual:** {"created": "int", "items": [], "note": "str", "reactivated": "int", "rejected": [{"market_id": "str", "reason": "str", "symbol": "str"}], "requested": "int", "validated": "bool", "warnings": []}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-109 -- Symbol.note: extra (declared=-, observed=str) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent str
- **Diff:** - -> str at Symbol.note via /symbols/{symbol_id}

### F-110 -- Symbol.created_at: missing (declared=str, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares str
- **Actual:** wire sent NoneType
- **Diff:** str -> NoneType at Symbol.created_at via /symbols/{symbol_id}
- **Regression:** packages/market-data-client/tests/test_symbol_write_ack_timestamps.py::test_create_ack_leaves_the_timestamps_absent_async

### F-111 -- Symbol.updated_at: missing (declared=str, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares str
- **Actual:** wire sent NoneType
- **Diff:** str -> NoneType at Symbol.updated_at via /symbols/{symbol_id}
- **Regression:** packages/market-data-client/tests/test_symbol_write_ack_timestamps.py::test_create_ack_leaves_the_timestamps_absent_async

### F-121 -- CalendarConfig.market_after: extra (declared=-, observed=dict) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares -
- **Actual:** wire sent dict
- **Diff:** - -> dict at CalendarConfig.market_after via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope_async

### F-122 -- CalendarConfig.requires_confirmation: extra (declared=-, observed=bool) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares -
- **Actual:** wire sent bool
- **Diff:** - -> bool at CalendarConfig.requires_confirmation via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope_async

### F-123 -- CalendarConfig.valid: extra (declared=-, observed=bool) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares -
- **Actual:** wire sent bool
- **Diff:** - -> bool at CalendarConfig.valid via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope_async

### F-124 -- CalendarConfig.open: missing (declared=str, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares str
- **Actual:** wire sent NoneType
- **Diff:** str -> NoneType at CalendarConfig.open via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope_async

### F-125 -- CalendarConfig.close: missing (declared=str, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares str
- **Actual:** wire sent NoneType
- **Diff:** str -> NoneType at CalendarConfig.close via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope_async

### F-126 -- CalendarConfig.enabled: missing (declared=bool, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares bool
- **Actual:** wire sent NoneType
- **Diff:** bool -> NoneType at CalendarConfig.enabled via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope_async

### F-127 -- CalendarConfig.editable: missing (declared=bool, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares bool
- **Actual:** wire sent NoneType
- **Diff:** bool -> NoneType at CalendarConfig.editable via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope_async

### F-128 -- CalendarConfig.env_bypass: missing (declared=bool, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares bool
- **Actual:** wire sent NoneType
- **Diff:** bool -> NoneType at CalendarConfig.env_bypass via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope_async

### F-129 -- CalendarConfig.pre_open_minutes: missing (declared=int, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares int
- **Actual:** wire sent NoneType
- **Diff:** int -> NoneType at CalendarConfig.pre_open_minutes via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope_async

### F-130 -- CalendarConfig.source: missing (declared=str, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares str
- **Actual:** wire sent NoneType
- **Diff:** str -> NoneType at CalendarConfig.source via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope_async

### F-131 -- CalendarConfig.timezone: missing (declared=str, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares str
- **Actual:** wire sent NoneType
- **Diff:** str -> NoneType at CalendarConfig.timezone via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope_async

### F-132 -- CalendarConfig.updated_by: missing (declared=str, observed=NoneType) [async]

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `FIXED`

- **Expected:** model declares str
- **Actual:** wire sent NoneType
- **Diff:** str -> NoneType at CalendarConfig.updated_by via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope_async

### F-133 -- schema drift en preview_calendar_config_async_response

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** {"market_after": {"is_open": "bool", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}, "requires_confirmation": "bool", "valid": "bool", "warnings": []}
- **Actual:** {"market_after": {"is_open": "bool", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}, "requires_confirmation": "bool", "valid": "bool", "warnings": ["str"]}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-135 -- schema drift en get_calendar_year_2099_async

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** {"config": {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": []}, "coverage": {"current_year_covered": "bool", "warning": "NoneType", "years": ["int"]}, "days": [{"close_time": "NoneType", "closed": "bool", "day": "str", "description": "str", "open_time": "NoneType"}], "market": {"is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}}
- **Actual:** {"config": {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": ["str"]}, "coverage": {"current_year_covered": "bool", "warning": "NoneType", "years": ["int"]}, "days": [{"close_time": "NoneType", "closed": "bool", "day": "str", "description": "str", "open_time": "NoneType"}], "market": {"is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-138 -- create_symbol_sync: MarketDataAPIError inesperado

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** 200 OK
- **Actual:** MarketDataAPIError('[422] {"detail":{"message":"el exchange no acepta estos símbolos; suscribirlos rechazaría el lote `smd` completo (docs/11-open-questions.md Q7). Usá ?force=true para guardarlos igual.","rejected":[{"symbol":"GSDPROBE/P27-SYNC","market_id":"ROFX","reason":"el exchange no lista este símbolo (normalmente significa que el contrato venció); suscribirlo rechaza el lote entero y silencia hasta 50 símbolos válidos"}]}}')
- **Diff:** type=MarketDataAPIError

### F-139 -- schema drift en create_symbols_batch_sync_response

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** {"created": "int", "items": [{"active": "bool", "created": "bool", "id": "int", "market_id": "str", "symbol": "str"}], "note": "str", "reactivated": "int", "requested": "int"}
- **Actual:** {"created": "int", "items": [], "note": "str", "reactivated": "int", "rejected": [{"market_id": "str", "reason": "str", "symbol": "str"}], "requested": "int", "validated": "bool", "warnings": []}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-140 -- Symbol.note: extra (declared=-, observed=str) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** model declares -
- **Actual:** wire sent str
- **Diff:** - -> str at Symbol.note via /symbols/{symbol_id}

### F-141 -- Symbol.created_at: missing (declared=str, observed=NoneType) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares str
- **Actual:** wire sent NoneType
- **Diff:** str -> NoneType at Symbol.created_at via /symbols/{symbol_id}
- **Regression:** packages/market-data-client/tests/test_symbol_write_ack_timestamps.py::test_create_ack_leaves_the_timestamps_absent

### F-142 -- Symbol.updated_at: missing (declared=str, observed=NoneType) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares str
- **Actual:** wire sent NoneType
- **Diff:** str -> NoneType at Symbol.updated_at via /symbols/{symbol_id}
- **Regression:** packages/market-data-client/tests/test_symbol_write_ack_timestamps.py::test_create_ack_leaves_the_timestamps_absent

### F-152 -- CalendarConfig.market_after: extra (declared=-, observed=dict) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares -
- **Actual:** wire sent dict
- **Diff:** - -> dict at CalendarConfig.market_after via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope

### F-153 -- CalendarConfig.requires_confirmation: extra (declared=-, observed=bool) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares -
- **Actual:** wire sent bool
- **Diff:** - -> bool at CalendarConfig.requires_confirmation via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope

### F-154 -- CalendarConfig.valid: extra (declared=-, observed=bool) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares -
- **Actual:** wire sent bool
- **Diff:** - -> bool at CalendarConfig.valid via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope

### F-155 -- CalendarConfig.open: missing (declared=str, observed=NoneType) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares str
- **Actual:** wire sent NoneType
- **Diff:** str -> NoneType at CalendarConfig.open via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope

### F-156 -- CalendarConfig.close: missing (declared=str, observed=NoneType) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares str
- **Actual:** wire sent NoneType
- **Diff:** str -> NoneType at CalendarConfig.close via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope

### F-157 -- CalendarConfig.enabled: missing (declared=bool, observed=NoneType) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares bool
- **Actual:** wire sent NoneType
- **Diff:** bool -> NoneType at CalendarConfig.enabled via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope

### F-158 -- CalendarConfig.editable: missing (declared=bool, observed=NoneType) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares bool
- **Actual:** wire sent NoneType
- **Diff:** bool -> NoneType at CalendarConfig.editable via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope

### F-159 -- CalendarConfig.env_bypass: missing (declared=bool, observed=NoneType) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares bool
- **Actual:** wire sent NoneType
- **Diff:** bool -> NoneType at CalendarConfig.env_bypass via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope

### F-160 -- CalendarConfig.pre_open_minutes: missing (declared=int, observed=NoneType) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares int
- **Actual:** wire sent NoneType
- **Diff:** int -> NoneType at CalendarConfig.pre_open_minutes via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope

### F-161 -- CalendarConfig.source: missing (declared=str, observed=NoneType) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares str
- **Actual:** wire sent NoneType
- **Diff:** str -> NoneType at CalendarConfig.source via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope

### F-162 -- CalendarConfig.timezone: missing (declared=str, observed=NoneType) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares str
- **Actual:** wire sent NoneType
- **Diff:** str -> NoneType at CalendarConfig.timezone via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope

### F-163 -- CalendarConfig.updated_by: missing (declared=str, observed=NoneType) [sync]

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** model declares str
- **Actual:** wire sent NoneType
- **Diff:** str -> NoneType at CalendarConfig.updated_by via /calendar/config/preview
- **Regression:** packages/market-data-client/tests/test_preview_calendar_config_envelope.py::test_preview_returns_the_preview_envelope

### F-164 -- schema drift en preview_calendar_config_sync_response

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** {"market_after": {"is_open": "bool", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}, "requires_confirmation": "bool", "valid": "bool", "warnings": []}
- **Actual:** {"market_after": {"is_open": "bool", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}, "requires_confirmation": "bool", "valid": "bool", "warnings": ["str"]}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-166 -- schema drift en get_calendar_year_2099_sync

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** {"config": {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": []}, "coverage": {"current_year_covered": "bool", "warning": "NoneType", "years": ["int"]}, "days": [{"close_time": "NoneType", "closed": "bool", "day": "str", "description": "str", "open_time": "NoneType"}], "market": {"is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}}
- **Actual:** {"config": {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": ["str"]}, "coverage": {"current_year_covered": "bool", "warning": "NoneType", "years": ["int"]}, "days": [{"close_time": "NoneType", "closed": "bool", "day": "str", "description": "str", "open_time": "NoneType"}], "market": {"is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-173 -- ingestor.last_error poblado por los símbolos de prueba de este harness (auto-infligido)

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** ingestor.last_error NoneType, como en el baseline get-health-feed.json
- **Actual:** tipo observado del campo: str (valor NO registrado)
- **Diff:** contaminación PROPIA del harness, no drift inexplicado: el spec en vivo documenta que un símbolo no validado contra el exchange aflora justo ahí. Clasificarlo SHAPE sería una misatribución y inflaría el conteo del criterio 4

### F-178 -- schema drift en get_health_feed

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** {"active_symbols": "int", "ingestor": {"connected": "bool", "frames_total": "int", "heartbeat_age_seconds": "float", "last_error": "NoneType", "last_frame_age_seconds": "float", "last_frame_at": "str", "market": {"enabled": "bool", "is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}, "pipeline": {"batch_interval_ms": "int", "conserved": "bool", "flushes": "int", "frames_accepted": "int", "frames_coalesced": "int", "frames_unknown_symbol": "int", "last_flush_ms": "float", "last_write_at": "str", "last_write_error": "NoneType", "pending": "int", "pending_peak": "int", "rows_skipped_stale": "int"}, "present": "bool", "reason": "str", "reconnects": "int", "rows_written": "int", "started_at": "str", "state": "str", "symbols_subscribed": "int", "uptime_seconds": "int"}, "newest_received_at": "str", "oldest_received_at": "str", "staleness_seconds": "float", "status": "str", "symbols_with_data": "int"}
- **Actual:** {"active_symbols": "int", "ingestor": {"connected": "bool", "frames_total": "int", "heartbeat_age_seconds": "float", "last_error": "str", "last_error_age_seconds": "int", "last_error_at": "str", "last_frame_age_seconds": "float", "last_frame_at": "str", "market": {"enabled": "bool", "is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}, "pipeline": {"batch_interval_ms": "int", "conserved": "bool", "flushes": "int", "frames_accepted": "int", "frames_coalesced": "int", "frames_unknown_symbol": "int", "last_flush_ms": "float", "last_write_at": "str", "last_write_error": "NoneType", "pending": "int", "pending_peak": "int", "rows_skipped_stale": "int"}, "present": "bool", "reason": "str", "reconnects": "int", "rows_written": "int", "started_at": "str", "state": "str", "subscription": {"chunk_size": "int", "chunks": "int", "confirm_seconds": "int", "delivered_count": "int", "forced_reconnects": "int", "last_reconnect_reason": "str", "quarantined_count": "int", "quarantined_symbols": ["str"], "requested": "int", "sent": "int", "smd_rejections": "int", "smd_resends": "int", "smd_unattributed": "int", "unconfirmed_count": "int", "unconfirmed_symbols": []}, "symbols_subscribed": "int", "uptime_seconds": "int"}, "newest_received_at": "str", "oldest_received_at": "str", "staleness_seconds": "float", "status": "str", "symbols_never_delivered": "int", "symbols_with_data": "int"}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-183 -- schema drift en get_calendar

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** {"config": {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": []}, "coverage": {"current_year_covered": "bool", "warning": "NoneType", "years": ["int"]}, "days": [{"close_time": "NoneType", "closed": "bool", "day": "str", "description": "str", "open_time": "NoneType"}], "market": {"is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}}
- **Actual:** {"config": {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": ["str"]}, "coverage": {"current_year_covered": "bool", "warning": "NoneType", "years": ["int"]}, "days": [{"close_time": "NoneType", "closed": "bool", "day": "str", "description": "str", "open_time": "NoneType"}], "market": {"is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-184 -- schema drift en get_calendar_config

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `NO-FIX`

- **Expected:** {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": []}
- **Actual:** {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": ["str"]}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-185 -- market_data vacío para prefix '__no_such_symbol__'

**Class:** `NO-DATA` . **Surface:** `sync` . **Status:** `EXPECTED`

- **Expected:** lista vacía para un prefix inexistente
- **Actual:** []
- **Diff:** empty/closed-market clasificado NO-DATA, nunca un crash

### F-190 -- schema drift en get_health_feed

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** {"active_symbols": "int", "ingestor": {"connected": "bool", "frames_total": "int", "heartbeat_age_seconds": "float", "last_error": "NoneType", "last_frame_age_seconds": "float", "last_frame_at": "str", "market": {"enabled": "bool", "is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}, "pipeline": {"batch_interval_ms": "int", "conserved": "bool", "flushes": "int", "frames_accepted": "int", "frames_coalesced": "int", "frames_unknown_symbol": "int", "last_flush_ms": "float", "last_write_at": "str", "last_write_error": "NoneType", "pending": "int", "pending_peak": "int", "rows_skipped_stale": "int"}, "present": "bool", "reason": "str", "reconnects": "int", "rows_written": "int", "started_at": "str", "state": "str", "symbols_subscribed": "int", "uptime_seconds": "int"}, "newest_received_at": "str", "oldest_received_at": "str", "staleness_seconds": "float", "status": "str", "symbols_with_data": "int"}
- **Actual:** {"active_symbols": "int", "ingestor": {"connected": "bool", "frames_total": "int", "heartbeat_age_seconds": "float", "last_error": "str", "last_error_age_seconds": "int", "last_error_at": "str", "last_frame_age_seconds": "float", "last_frame_at": "str", "market": {"enabled": "bool", "is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}, "pipeline": {"batch_interval_ms": "int", "conserved": "bool", "flushes": "int", "frames_accepted": "int", "frames_coalesced": "int", "frames_unknown_symbol": "int", "last_flush_ms": "float", "last_write_at": "str", "last_write_error": "NoneType", "pending": "int", "pending_peak": "int", "rows_skipped_stale": "int"}, "present": "bool", "reason": "str", "reconnects": "int", "rows_written": "int", "started_at": "str", "state": "str", "subscription": {"chunk_size": "int", "chunks": "int", "confirm_seconds": "int", "delivered_count": "int", "forced_reconnects": "int", "last_reconnect_reason": "str", "quarantined_count": "int", "quarantined_symbols": ["str"], "requested": "int", "sent": "int", "smd_rejections": "int", "smd_resends": "int", "smd_unattributed": "int", "unconfirmed_count": "int", "unconfirmed_symbols": []}, "symbols_subscribed": "int", "uptime_seconds": "int"}, "newest_received_at": "str", "oldest_received_at": "str", "staleness_seconds": "float", "status": "str", "symbols_never_delivered": "int", "symbols_with_data": "int"}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-195 -- schema drift en get_calendar

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** {"config": {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": []}, "coverage": {"current_year_covered": "bool", "warning": "NoneType", "years": ["int"]}, "days": [{"close_time": "NoneType", "closed": "bool", "day": "str", "description": "str", "open_time": "NoneType"}], "market": {"is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}}
- **Actual:** {"config": {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": ["str"]}, "coverage": {"current_year_covered": "bool", "warning": "NoneType", "years": ["int"]}, "days": [{"close_time": "NoneType", "closed": "bool", "day": "str", "description": "str", "open_time": "NoneType"}], "market": {"is_open": "bool", "last_business_day": "str", "local_time": "str", "next_transition": "str", "reason": "str", "session_close": "str", "session_open": "str", "state": "str"}}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-196 -- schema drift en get_calendar_config

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `NO-FIX`

- **Expected:** {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": []}
- **Actual:** {"close": "str", "editable": "bool", "enabled": "bool", "env_bypass": "bool", "open": "str", "pre_open_minutes": "int", "source": "str", "timezone": "str", "updated_at": "NoneType", "updated_by": "str", "warnings": ["str"]}
- **Diff:** baseline schema difiere; NO se sobreescribe (D-25)

### F-197 -- market_data async vacío para prefix '__no_such_symbol__'

**Class:** `NO-DATA` . **Surface:** `async` . **Status:** `EXPECTED`

- **Expected:** lista vacía para un prefix inexistente
- **Actual:** []
- **Diff:** empty/closed-market clasificado NO-DATA, nunca un crash
<!-- END AUTO-GENERATED -->
