# Phase 22: Instruments + symbols(read) + calendar(read) + modelos - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-07-30
**Phase:** 22-instruments-symbols-read-calendar-read-modelos
**Mode:** assumptions
**Areas analyzed:** Endpoint builders + param serialization, Response models, Return shapes, Public surface, Test strategy

## Assumptions Presented

### Endpoint builders + param serialization (`_core.py`)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Five pure GET builders (`build_instruments_request`, `build_segments_request`, `build_symbols_request`, `build_calendar_request`, `build_calendar_config_request`), `authenticated=True, idempotent=True`, `_params.drop_none`, `params or None` | Confident | `_core.py:build_market_data_request` template; success criterion 1; `.future_plans/market_data.md` Fase 3 |
| Booleans ride httpx-native `true/false` encoding; explicit encoding deferred to Phase 23 (== Phase-21 D-07) | Confident | `_params.py` docstring; Phase 21 D-07 |

### Response models (`models.py`)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Net-new PROVISIONAL `SafeModel` dataclasses (`Instrument`, `Segment`, `Symbol`, `CalendarDay`, `CalendarConfig`) appended to existing `models.py`; camelCase verbatim; `from_api` tolerant | Likely (approach Confident, field names provisional) | `models.py` holds all response models; A1/A2 OpenAPI-not-vendored |
| Reference-data models do NOT carry client-stamped `received_at` (plain SafeModel, like nested `MarketDataEntry`) | Likely | `MarketDataEntry` omits `received_at`; `received_at` is the `max_staleness_seconds` companion (Phase 21 D-01/D-02); reference endpoints have no staleness filter |

### Return shapes (parsers)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| instruments/segments/symbols/calendar → `list[Model]` with 204/None → `[]` guard | Confident | success criterion 2; `parse_market_data_response` template |
| `GET /calendar/config` → single typed `CalendarConfig` (not a list); empty body → `CalendarConfig.from_api(None)` | Likely | criterion 2 "modelos tipados"; deferred `PUT/POST/DELETE /calendar/config` confirm one resource |

### Public surface
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Five methods on `Client` + `AsyncClient` + five shims + `__init__.py` re-exports; concise `get_*` names; dual sync/async parity | Confident | `client.py`/`aio.py`/`__init__.py` `get_market_data` pattern |

### Test strategy
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| pytest-httpx: param serialization, `from_api` tolerance, 204/None→[] guards, single-object config parse, sync/async parity; all 4 CI gates green | Confident | Phase 21 D-11 test strategy |

## Corrections Made

No corrections — all assumptions confirmed ("Yes, proceed").

## External Research

None performed — response shapes are OpenAPI-undefined by design (A1/A2) and reconciled live in
Phase 23; no library/ecosystem questions surfaced.
