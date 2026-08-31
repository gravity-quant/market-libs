# Phase 43: `market-data-client` — forma de `Instrument`/`Segment` + 5 claves `extra` tipadas - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-31
**Phase:** 43-market-data-client-forma-de-instrument-segment-5-claves-extr
**Mode:** assumptions
**Areas analyzed:** Instrument/Segment field-by-field disposition, HARN-02 extra-key typing approach, Fixture re-derivation approach, CI-green / dual-surface mirroring scope

## Assumptions Presented

### Instrument/Segment field-by-field disposition

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `Instrument` mantiene symbol/segment/expired, agrega market_id/currency/days_to_maturity/maturity/outright/subscribed, agrega active:bool\|None | Confident | `42-WIRE-READ.md` §2; F-205 (`market-data-client-findings.md:1591`) |
| `Instrument.marketId` queda como alias aditivo D-22; `instrumentType` se remueve | Confident | `models.py:817-901` (precedente Symbol); F-212/F-213 |
| `Segment` reemplazado por completo: marketSegmentId/marketId/description removidos, segment/live_instruments agregados | Likely | `models.py:802-813` vs `42-WIRE-READ.md` §2; F-214…F-218; `_core.py:1042-1051` |
| Criterio 2 se demuestra offline contra captura gitignored + censo, sin segunda corrida en vivo | Likely | captures presentes en disco 2026-08-31; `42-WIRE-READ.md` §4.1 (`_emit_shape` inerte) |

### HARN-02 extra-key typing approach

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `FeedIngestor.subscription` → nueva dataclass anidada `FeedSubscription(SafeModel)`, no `dict[str, Any]` | Confident | `tools/check_surface_types.py` surface-types gate; `_decode.py` sin rama dict; `research/ARCHITECTURE.md:299-303` |
| 15 campos de `FeedSubscription` verbatim del blob medido, `unconfirmed_symbols` con elemento asumido `str` | Likely | F-71 (`market-data-client-findings.md:950`); `research/SUMMARY.md:141` (LOW confidence flagged) |
| `last_error_age_seconds`/`last_error_at` nullable; `Symbol.note` nullable; `symbols_never_delivered` plano | Likely | baseline 07-31 sin las claves + capturas posteriores con ellas condicionadas a error/escritura |

### Fixture re-derivation approach

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 9 sitios de test a tocar, incluidas 2 exact-set assertions que rompen mecánicamente | Confident | lectura directa de cada archivo citado en D-12 |
| Helper nuevo "subset del baseline medido", baselines write-once sin refrescar | Likely | D-25; `42-WIRE-READ.md` §3; `test_core.py:1055-1062` |

### CI-green / dual-surface mirroring scope

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `client.py`/`aio.py` sin cambios de fuente — parsers genéricos compartidos vía `_core.py` | Confident | `_core.py:981-1141`; `research/ARCHITECTURE.md:504` |
| "4 gates de CI" = 4 jobs de `ci.yml` (lint/pre-commit/typecheck/test) | Likely | `REQUIREMENTS.md:83`; `ci.yml`; lectura alternativa de `research/ARCHITECTURE.md:505` descartada por conteo de archivos en `tools/` |
| Sin bump de versión en ningún sitio — sólo `models.py` + tests | Confident | `ROADMAP.md` criterio 5; `test_version_metadata.py:39-54` |

## Corrections Made

No corrections — all 10 assumptions confirmed across the 4 grouped questions ("Yes, proceed" selected on every one).

## External Research

No research performed — `needs_research` returned empty from the analyzer; every disposition is grounded in committed measurement (Phase 42 wire read + Phase 33 findings ledger), in-repo precedent (D-22, D-25), or an executable CI gate.
