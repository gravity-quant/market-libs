# Phase 21: Market data (lectura) + modelos - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-07-29
**Phase:** 21-market-data-lectura-modelos
**Mode:** assumptions
**Areas analyzed:** received_at semantics, models.py & SafeModel base, endpoint builders & param serialization, with_options parity + Phase-20 debt fold-in, test strategy

## Assumptions Presented

### `received_at` semantics
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `received_at` is client-stamped at response-receipt time, injected via `from_api(payload, received_at=...)`, NOT a payload field | Unclear | `.future_plans/market_data.md:29-30`; D-05 `market_data.md:40`; `max_staleness_seconds` is a server-side filter (`market_data.md:74`, ROADMAP:129); Fase 4 flags received_at/staleness as a live divergence (`market_data.md:94`) |

### models.py & SafeModel base
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| New `models.py` carrying its own copy of higyrus's `SafeModel`+`_coerce`; frozen/slotted snapshot with nested `entries` + `received_at`; camelCase verbatim; N815 exemption | Likely | `higyrus_client/models.py:30-89`; no `models.py` in market-data-client; CLAUDE.md model mandate; D-06 `market_data.md:41` |

### Endpoint builders & param serialization
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Three `_core.py` builders returning `RequestSpec(authenticated=True, idempotent=True)`; GET filters as `params=` with `None` dropped (`drop_none`); `LatestRequest`→`json_body`; httpx-native bool encoding | Likely | `_core.py:78-102` RequestSpec fields; `build_health_request` template `_core.py:221-230` (authenticated=False); higyrus `drop_none` convention |

### with_options parity + WR-04 + 401 test gap
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Add `with_options(max_retries=N)` to both surfaces via iol shared-view-clone (thread `extensions["max_attempts"]`); fold in WR-04 header alignment (token wins) + authenticated-401 exactly-once re-auth tests | Confident | `client.py:70-71` defers retries to Phase 21; iol `client.py:128,140-177,202-208,264-320`; WR-04 in debt file `:19-26`; 401 test gap `:28-34`; `resolves_phase: 21` |

## Corrections Made

No corrections — the user confirmed all assumptions.

The one Unclear item (`received_at` semantics) was resolved by direct user selection:
- **Question:** client-stamped vs server-provided vs both (dual timestamps)?
- **User choice:** **Client-stamped** (the recommended option) → locked as D-01/D-02.

Assumptions 2, 3, and 4 (models.py + SafeModel copy, `_core.py` builders + param
serialization, `with_options` parity + WR-04 + 401 tests) confirmed as-is: **"Lock all three."**

## External Research

None performed — the analyzer flagged no research gaps. The endpoint surface, param list,
`LatestRequest` schema, and D-locks are all in-repo; the only genuine unknowns (exact response
payload shape, server-vs-client `received_at` confirmation) are deferred to Phase 23 live
verification against develop, not resolvable by external research.
