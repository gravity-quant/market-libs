# Findings: market-data-client-client

## Run Context (ART)
- Timestamp: 2026-07-31T16:58:34.727471+00:00
- Resolved base URL / env: https://market-data-develop.bbsa.com.ar/api
- Market hours note: <abierto|cerrado — afecta paths sesión-dependientes>

<!-- Clases (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT -->
<!-- Estados (D-08): OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX). Sin campo de severidad. -->

<!-- BEGIN AUTO-GENERATED -->
## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|
| F-01 | SHAPE | sync | OPEN |
| F-02 | SHAPE | sync | OPEN |
| F-03 | SHAPE | sync | OPEN |
| F-04 | SHAPE | sync | OPEN |
| F-05 | SHAPE | sync | OPEN |
| F-06 | SHAPE | sync | OPEN |
| F-07 | SHAPE | sync | OPEN |
| F-08 | SHAPE | sync | OPEN |
| F-09 | SHAPE | sync | OPEN |
| F-10 | SHAPE | sync | OPEN |
| F-11 | SHAPE | sync | OPEN |
| F-12 | SHAPE | sync | OPEN |
| F-13 | SHAPE | sync | OPEN |
| F-14 | SHAPE | sync | OPEN |
| F-15 | SHAPE | sync | OPEN |
| F-16 | SHAPE | sync | OPEN |
| F-17 | SHAPE | sync | OPEN |
| F-18 | SHAPE | sync | OPEN |
| F-19 | SHAPE | async | OPEN |
| F-20 | SHAPE | async | OPEN |
| F-21 | SHAPE | async | OPEN |
| F-22 | SHAPE | async | OPEN |
| F-23 | SHAPE | async | OPEN |
| F-24 | SHAPE | async | OPEN |
| F-25 | SHAPE | async | OPEN |
| F-26 | SHAPE | async | OPEN |
| F-27 | SHAPE | async | OPEN |
| F-28 | SHAPE | async | OPEN |
| F-29 | SHAPE | async | OPEN |
| F-30 | SHAPE | async | OPEN |
| F-31 | SHAPE | async | OPEN |
| F-32 | SHAPE | async | OPEN |
| F-33 | SHAPE | async | OPEN |
| F-34 | SHAPE | async | OPEN |
| F-35 | SHAPE | async | OPEN |
| F-36 | SHAPE | async | OPEN |

## Detalle por hallazgo

### F-01 -- model-only field entries en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** MarketDataSnapshot y wire concuerdan en entries
- **Actual:** model-only: entries
- **Diff:** path=<root> direction=model-only

### F-02 -- model-only field marketId en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** MarketDataSnapshot y wire concuerdan en marketId
- **Actual:** model-only: marketId
- **Diff:** path=<root> direction=model-only

### F-03 -- wire-only field active en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** MarketDataSnapshot y wire concuerdan en active
- **Actual:** wire-only: active
- **Diff:** path=<root> direction=wire-only

### F-04 -- wire-only field market_data en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** MarketDataSnapshot y wire concuerdan en market_data
- **Actual:** wire-only: market_data
- **Diff:** path=<root> direction=wire-only

### F-05 -- wire-only field market_id en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** MarketDataSnapshot y wire concuerdan en market_id
- **Actual:** wire-only: market_id
- **Diff:** path=<root> direction=wire-only

### F-06 -- wire-only field note en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** MarketDataSnapshot y wire concuerdan en note
- **Actual:** wire-only: note
- **Diff:** path=<root> direction=wire-only

### F-07 -- wire-only field staleness_seconds en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** MarketDataSnapshot y wire concuerdan en staleness_seconds
- **Actual:** wire-only: staleness_seconds
- **Diff:** path=<root> direction=wire-only

### F-08 -- model-only field businessDays en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en businessDays
- **Actual:** model-only: businessDays
- **Diff:** path=<root> direction=model-only

### F-09 -- wire-only field close en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en close
- **Actual:** wire-only: close
- **Diff:** path=<root> direction=wire-only

### F-10 -- wire-only field editable en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en editable
- **Actual:** wire-only: editable
- **Diff:** path=<root> direction=wire-only

### F-11 -- wire-only field enabled en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en enabled
- **Actual:** wire-only: enabled
- **Diff:** path=<root> direction=wire-only

### F-12 -- wire-only field env_bypass en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en env_bypass
- **Actual:** wire-only: env_bypass
- **Diff:** path=<root> direction=wire-only

### F-13 -- wire-only field open en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en open
- **Actual:** wire-only: open
- **Diff:** path=<root> direction=wire-only

### F-14 -- wire-only field pre_open_minutes en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en pre_open_minutes
- **Actual:** wire-only: pre_open_minutes
- **Diff:** path=<root> direction=wire-only

### F-15 -- wire-only field source en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en source
- **Actual:** wire-only: source
- **Diff:** path=<root> direction=wire-only

### F-16 -- wire-only field updated_at en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en updated_at
- **Actual:** wire-only: updated_at
- **Diff:** path=<root> direction=wire-only

### F-17 -- wire-only field updated_by en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en updated_by
- **Actual:** wire-only: updated_by
- **Diff:** path=<root> direction=wire-only

### F-18 -- wire-only field warnings en CalendarConfig

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en warnings
- **Actual:** wire-only: warnings
- **Diff:** path=<root> direction=wire-only

### F-19 -- model-only field entries en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** MarketDataSnapshot y wire concuerdan en entries
- **Actual:** model-only: entries
- **Diff:** path=<root> direction=model-only

### F-20 -- model-only field marketId en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** MarketDataSnapshot y wire concuerdan en marketId
- **Actual:** model-only: marketId
- **Diff:** path=<root> direction=model-only

### F-21 -- wire-only field active en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** MarketDataSnapshot y wire concuerdan en active
- **Actual:** wire-only: active
- **Diff:** path=<root> direction=wire-only

### F-22 -- wire-only field market_data en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** MarketDataSnapshot y wire concuerdan en market_data
- **Actual:** wire-only: market_data
- **Diff:** path=<root> direction=wire-only

### F-23 -- wire-only field market_id en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** MarketDataSnapshot y wire concuerdan en market_id
- **Actual:** wire-only: market_id
- **Diff:** path=<root> direction=wire-only

### F-24 -- wire-only field note en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** MarketDataSnapshot y wire concuerdan en note
- **Actual:** wire-only: note
- **Diff:** path=<root> direction=wire-only

### F-25 -- wire-only field staleness_seconds en MarketDataSnapshot

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** MarketDataSnapshot y wire concuerdan en staleness_seconds
- **Actual:** wire-only: staleness_seconds
- **Diff:** path=<root> direction=wire-only

### F-26 -- model-only field businessDays en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en businessDays
- **Actual:** model-only: businessDays
- **Diff:** path=<root> direction=model-only

### F-27 -- wire-only field close en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en close
- **Actual:** wire-only: close
- **Diff:** path=<root> direction=wire-only

### F-28 -- wire-only field editable en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en editable
- **Actual:** wire-only: editable
- **Diff:** path=<root> direction=wire-only

### F-29 -- wire-only field enabled en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en enabled
- **Actual:** wire-only: enabled
- **Diff:** path=<root> direction=wire-only

### F-30 -- wire-only field env_bypass en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en env_bypass
- **Actual:** wire-only: env_bypass
- **Diff:** path=<root> direction=wire-only

### F-31 -- wire-only field open en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en open
- **Actual:** wire-only: open
- **Diff:** path=<root> direction=wire-only

### F-32 -- wire-only field pre_open_minutes en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en pre_open_minutes
- **Actual:** wire-only: pre_open_minutes
- **Diff:** path=<root> direction=wire-only

### F-33 -- wire-only field source en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en source
- **Actual:** wire-only: source
- **Diff:** path=<root> direction=wire-only

### F-34 -- wire-only field updated_at en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en updated_at
- **Actual:** wire-only: updated_at
- **Diff:** path=<root> direction=wire-only

### F-35 -- wire-only field updated_by en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en updated_by
- **Actual:** wire-only: updated_by
- **Diff:** path=<root> direction=wire-only

### F-36 -- wire-only field warnings en CalendarConfig

**Class:** `SHAPE` . **Surface:** `async` . **Status:** `OPEN`

- **Expected:** CalendarConfig y wire concuerdan en warnings
- **Actual:** wire-only: warnings
- **Diff:** path=<root> direction=wire-only
<!-- END AUTO-GENERATED -->
