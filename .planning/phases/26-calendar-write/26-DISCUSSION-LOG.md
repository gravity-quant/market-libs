# Phase 26: Calendar write - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-07-31
**Phase:** 26-calendar-write
**Mode:** assumptions
**Areas analyzed:** Builders + routing, Return types + parsers, Request models, Validation + no-retry proof, Scope boundary (pre-existing read bug)

## Assumptions Presented

### A. Builders + routing (`_core.py`)

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Five pure builders mirroring the Phase-25 symbols builders; no `RequestSpec` change; the two DELETEs leave `json_body=None` | Confident | `_core.py:106-131`, `client.py:364-370`, `build_segments_request` (`_core.py:502-515`), `build_update_symbol_request` (`_core.py:429-447`); empirically verified with pinned httpx 0.28.1 that a `json=None` DELETE emits no body and no `Content-Type` |
| `day` interpolated RAW into `/calendar/holidays/{day}` — no `quote()` | Confident (raised from Likely by OpenAPI) | Live OpenAPI declares the path param as `{"type":"string","format":"date"}` → ISO `YYYY-MM-DD`; the D-08 `"DLR/DIC26"` risk does not apply |
| Idempotency per DM-03: `idempotent=False` only for `POST /calendar/holidays` | Confident | DM-03 in `market_data_mutations.md`; ROADMAP criterion 4 |

### B. Return types + parsers

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `set_calendar_config` / `delete_calendar_config` / `preview_calendar_config` → `CalendarConfig` via the existing `parse_calendar_config_response` | Confident (raised from Likely by OpenAPI + captured wire) | `_core.py:733-746`, `models.py:326-350`; `.planning/verification/schemas/market-data-client/get-calendar-config.json` matches the model field-for-field; the model already carries `warnings`, which the OpenAPI ties `confirm` to |
| `add_holidays` / `delete_holiday` → `dict[str, Any]` passthrough; NOT `list[CalendarDay]` | Confident | OpenAPI declares all five 200s as bare `object` (`additionalProperties: true`); `parse_health_response` (`_core.py:273-278`) is the passthrough precedent; `CalendarDay` fields do not exist on the real wire |
| Parsers keep body-consume-then-raise order and stay tolerant of empty/`null` bodies | Confident | `parse_calendar_config_response`, `parse_symbols_response` in `_core.py` |

### C. Request models

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `confirm` is a field of `MarketHoursIn` (`= False`, always emitted), not a separate method kwarg | Confident (raised from Likely by OpenAPI) | OpenAPI lists `confirm` inside `MarketHoursIn` with `default: false`; `NewSymbol.market_id` precedent (`models.py:197-213`, 25-CONTEXT D-10); Phase-25 methods take model + path params only (`client.py:539-574`) |
| Frozen `@dataclass(frozen=True, slots=True)` + hand-written `to_dict()`, not `SafeModel` | Confident | Phase-25 D-09; `LatestRequest.to_dict()` (`models.py:177-184`) |
| `to_dict()` via `_params.drop_none`: `open_time`/`close_time` dropped when `None`; `closed=True` / `description=""` always emitted | Confident | `_params.py:22-28` (preserves falsy-but-not-`None`); OpenAPI documents `open_time: null = "configured default"`; ROADMAP criterion 3 names `drop_none` |
| Defaults verbatim from the live OpenAPI (`pre_open_minutes=10`, `enabled=True`, `updated_by=""`, `confirm=False`; `closed=True`, `description=""`) | Confident | Live OpenAPI component schemas |

### D. Validation + the `idempotent=False` proof

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `HolidaysIn.days` 1–500 bound enforced client-side via `ValueError` in `__post_init__` | Confident (raised from Likely by OpenAPI) | Live OpenAPI declares `days: {minItems: 1, maxItems: 500}` — the source plan omitted this; exact `NewSymbols` mirror (`models.py:230-233`, 25-CONTEXT D-11) |
| Scalar bounds (`pre_open_minutes` 0–120, string maxLengths, `HH:MM` format) left to the server's 422 | Confident | Phase 25 deliberately did not enforce `NewSymbol.symbol`'s declared 1–255 bound → the real precedent is collection-length bounds only; `raise_for_response` (`_core.py:138-150`) already maps 422; a client-side regex would risk false negatives against `format: time` |
| Phase 26 must add the package's FIRST dispatch-level `idempotent=False` no-retry test | Confident | `_transport.py:157-160`, `_atransport.py:56-59` short-circuit on falsy `idempotent`, but the market-data suite has only builder-level asserts (`tests/test_core.py:330,342,354`); the only dispatch-level test in the monorepo is in another package (`iol-client/tests/test_transport.py:42-53`); all three Phase-25 builders are `idempotent=True` |

### E. Scope boundary

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Phase 26 does NOT fix the pre-existing `get_calendar` / `CalendarDay` / `parse_calendar_response` envelope bug — only avoids inheriting it, records it for Phase 27 | Confident | Bug is Phase-22 code (`_core.py:716-730`, `models.py:312-323`) outside MUT-MD-02's boundary (`REQUIREMENTS.md:20`); proven by `.planning/verification/schemas/market-data-client/get-calendar.json`; mirrors the Phase-25 disposition of the analogous WR-01 read-path bug |

## Corrections Made

No corrections — all assumptions confirmed by the user.

## External Research

The live develop OpenAPI turned out to be reachable from this machine, so the flagged
research gap was closed directly rather than left open.

- **`https://market-data-develop.bbsa.com.ar/api/openapi.json`** (fetched 2026-07-31,
  HTTP 200; NOT vendored in the repo). Findings:
  - `HolidaysIn.days` carries `minItems: 1, maxItems: 500` — **absent from the source
    plan**, which only said `days: [HolidayIn] (req)`. Raised the validation assumption
    from "non-empty guard only, Likely" to "exact 1–500 `NewSymbols` mirror, Confident".
  - `day` path param is `format: date` → confirmed raw interpolation is safe (D-03).
  - `confirm` is a `MarketHoursIn` field with `default: false`, described as *"Required
    when the change produces warnings. See POST /calendar/config/preview"* — i.e. a second
    opinion, not a force flag. Resolved the field-vs-kwarg question (D-09).
  - `MarketHoursIn` bounds: `pre_open_minutes` 0–120, `timezone` 1–64, `updated_by` ≤200;
    `HolidayIn.description` ≤500; `open_time`/`close_time` are `format: time`. Combined
    with Phase 25 having skipped `NewSymbol.symbol`'s declared 1–255 bound, this fixed the
    validation line at collection-bounds-only (D-13).
  - All five calendar-write 200 responses are declared as bare `object`
    (`additionalProperties: true`) — the server promises **no** response shape. This did
    NOT resolve the return types; it confirmed that tolerant parsing is the right hedge and
    left the concrete shapes to Phase 27.
- **Captured live wire snapshots** (`.planning/verification/schemas/market-data-client/`):
  `get-calendar-config.json` matches `CalendarConfig` field-for-field (backing D-05);
  `get-calendar.json` proves the `{config, coverage, days[], market}` envelope and that
  `days[]` items carry the `HolidayIn` shape, not `CalendarDay`'s (backing D-06 and D-16).

## Unresolved by design (carried to Phase 27 / LIVE-MUT-01)

- Concrete 200 body of each of the five calendar-write endpoints.
- Real server-side idempotency of `PUT /calendar/config`, `DELETE /calendar/holidays/{day}`,
  and whether `POST /calendar/holidays` is genuinely non-idempotent.
- Whether `"HH:MM:SS"` is accepted alongside `"HH:MM"`, and the real semantics of dropping
  vs. sending `null` for a holiday's time overrides.
