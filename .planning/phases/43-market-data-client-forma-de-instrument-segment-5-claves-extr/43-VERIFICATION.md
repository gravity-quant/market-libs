---
phase: 43-market-data-client-forma-de-instrument-segment-5-claves-extr
verified: 2026-09-01T01:34:07Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 43: `market-data-client` — forma de `Instrument`/`Segment` + 5 claves `extra` tipadas Verification Report

**Phase Goal:** `market-data-client` deja de declarar campos que el wire no manda y de ignorar campos que sí manda — `get_segments()` deja de devolver filas enteramente vacías, `Instrument` refleja el payload real, y las cinco claves `extra` medidas quedan tipadas — todo en un único cambio de `models.py`, verificado y listo para publicar pero **sin** publicar.
**Verified:** 2026-09-01T01:34:07Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Tabla de disposición campo por campo para `Instrument`/`Segment`, cero filas sin disponer, `marketId` como alias aditivo (no rename) | ✓ VERIFIED | `43-DISPOSITION.md` §1.1/1.2 tables match `models.py:788-895` field-for-field: `Instrument` declares `symbol, marketId, segment, expired, market_id, currency, days_to_maturity, maturity, outright, subscribed, active` (11 fields, `instrumentType` absent); `Segment` declares exactly `segment, live_instruments` (2 fields, the 3 old fields absent). `Instrument.from_api` override at `models.py:842-866` mirrors `market_id`→`marketId` only when `marketId` is absent from payload (`if ... "marketId" not in payload and "market_id" in payload`), uses explicit two-arg `super(Instrument, cls).from_api(payload)` — never overwrites an explicit value, never a rename |
| 2 | `get_segments()` devuelve filas pobladas contra el payload real medido (antes/después medido, no afirmado) | ✓ VERIFIED | `Segment` model now has real wire keys; `test_get_segments_unwraps_the_segments_envelope` (+ async twin) assert `result[0].segment == "SEG1"` and `result[0].live_instruments == 7` — ran directly, both pass. `_core.py` docstring for `parse_segments_response` (lines 1042-1051) reconciled: no longer claims the shape fix is deliberately deferred |
| 3 | 5 claves `extra` (`HealthFeed.symbols_never_delivered`, `FeedIngestor.last_error_age_seconds`/`.last_error_at`/`.subscription`, `Symbol.note`) declaradas y tipadas, censo deja de reportarlas `extra` sin flip a `missing` | ✓ VERIFIED | All 5 fields present in `models.py`: `FeedIngestor.subscription: FeedSubscription` (non-optional nested model, `models.py:1494`), `.last_error_age_seconds: int \| None` / `.last_error_at: str \| None` (`models.py:1496-1497`), `HealthFeed.symbols_never_delivered: int` (plain, `models.py:1549`), `Symbol.note: str \| None` (`models.py:971`). Ran `test_health_feed_from_api_drops_an_undeclared_key_and_reports_it_once`, `test_healthy_feed_payload_emits_no_missing_for_the_conditional_error_fields`, `test_measured_health_feed_payload_produces_zero_divergence_records` directly — all pass. Traced the no-flip mechanism in `_decode.py:438-444` (`Union` branch returns `None` on absent key without calling `sink`, so no `missing` record for the two conditional fields) |
| 4 | Fixtures re-derivadas de baselines medidos, aserción de subconjunto, ninguna renombrada | ✓ VERIFIED | Ran `test_every_fixture_key_is_a_measured_wire_key` and `test_instrument_field_set_matches_reconciled_wire` directly — both pass. `test_reference_client.py`/`test_reference_async_client.py` fixtures now use `{"segment": "DDF", ...}` / `{"segment": "DDF", "live_instruments": 7}` — old `marketSegmentId`/`description` values grepped for and absent. `test_decode.py`'s `overriding == {"Instrument", "MarketDataSnapshot", "Symbol"}` (3-element set including new `Instrument` override) confirmed present at line 1383 |
| 5 | 4 gates CI v1.6 verdes, dual sync/async espejado o demostrado innecesario por medición, sin bump de versión | ✓ VERIFIED | Ran locally: `pytest packages/market-data-client` → 727 passed; `mypy _core.py models.py` → clean; `check_surface_types.py` → 0 violations, 452 fields scanned; `check_decode_intactness.py`/`check_uniform_structure.py` → both green. `git diff --name-only 396c717 HEAD` confirms `client.py`/`aio.py`/`main_market_data.py`/`pyproject.toml`/`uv.lock` are absent from the diff — only `models.py`, `_core.py` (docstring-only, confirmed via diff), and 7 test files changed. Version confirmed unchanged: `pyproject.toml` and `__init__.py.__version__` both still `0.6.0` |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/market-data-client/src/market_data_client/models.py` | `Instrument` (11 fields + `from_api` override), `Segment` (2 fields), `FeedSubscription`, 3 new `FeedIngestor` fields, `HealthFeed.symbols_never_delivered`, `Symbol.note` | ✓ VERIFIED | All present and match disposition exactly, read directly from source |
| `packages/market-data-client/src/market_data_client/_core.py` | `parse_segments_response` docstring reconciled (D-14) | ✓ VERIFIED | Diff shows docstring-only change; no logic touched; "DELIBERATELY" / "SHAPE-MD-REF-33" language removed |
| `packages/market-data-client/tests/test_reference_models.py` | field-set exact assertions, alias-mirror tests, `_WIRE_INSTRUMENT_ROW`/`_WIRE_SEGMENT_ROW` fixtures | ✓ VERIFIED | `test_instrument_field_set_matches_reconciled_wire` present and passing |
| `packages/market-data-client/tests/test_reference_envelope_unwrap.py` | value assertions on unwrapped rows | ✓ VERIFIED | `live_instruments` value-assertion present and passing |
| `packages/market-data-client/tests/test_core.py` | `_MEASURED_HEALTH_FEED_43` fixture, key-subset helper, zero-divergence test | ✓ VERIFIED | `test_every_fixture_key_is_a_measured_wire_key`, `test_measured_health_feed_payload_produces_zero_divergence_records` present and passing |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `test_reference_models.py` | `models.py` | `dataclasses.fields(Instrument)`/`(Segment)` exact-set assertion | ✓ WIRED | `test_instrument_field_set_matches_reconciled_wire` passes |
| `models.py` | `_decode.py` | `Instrument.from_api` mirrors `market_id`→`marketId` before `walk_model` sees payload | ✓ WIRED | `super(Instrument, cls).from_api` confirmed present at `models.py:866` |
| `test_decode.py` | `models.py` | `overriding == {...}` set now includes `Instrument` (3 elements) | ✓ WIRED | Confirmed at `test_decode.py:1383` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| SHAPE-01 | 43-01-PLAN.md, 43-03-PLAN.md | Corregir campos `Instrument`/`Segment` contra wire fresco, disposición por campo, fixtures re-derivadas | ✓ SATISFIED | Truths 1, 2, 4, 5 |
| HARN-02 | 43-02-PLAN.md, 43-03-PLAN.md | Tipar las 5 claves `extra` restantes, mismo `models.py`, mismo release | ✓ SATISFIED | Truth 3 |

No orphaned requirements — `REQUIREMENTS.md` lines 62-63 map only SHAPE-01 and HARN-02 to Phase 43, and both are claimed across the three plans' frontmatter.

### Anti-Patterns Found

`grep -n -E "TBD|FIXME|XXX"` over all 10 phase-touched source/test files → 0 matches (exit 1). No debt markers found. No placeholder/stub patterns found in `models.py` (all new fields carry live-measured provenance in docstrings, not guesses).

### Human Verification Required

None. This phase is a pure type/shape correction verifiable entirely through static inspection and the existing test suite — no runtime/UI/state-machine behavior requiring human judgment.

### Deferred / Tracked Follow-ups (non-blocking)

Two items were found during Phase 43's own review and are explicitly and deliberately out of D-16's locked scope (`models.py` + tests + one docstring only). Both are documented, named, and routed to backlog — not silently dropped:

1. **`DRV-MD-SEG-43`** (`main_market_data.py:1541-1542`) — the verification driver's `probe_parity_sync_async` still dereferences `Segment.marketSegmentId`, which this phase's `Segment` replacement removed. Caught by a `try/except Exception`, so it degrades to a silent handler-finding rather than crashing, but it defeats the probe's actual purpose. Confirmed present in the file today (`main_market_data.py:1541-1542` still reads `s.marketSegmentId`). Tracked in `ROADMAP.md` § Backlog, candidate for Phase 44/45. Flagged as a code-review WARNING (WR-01) — correctly triaged as a tracked, scoped-out item rather than an oversight.
2. **`SURF-MD-FEEDSUB-43`** — `FeedSubscription` is in `models.__all__` but not re-exported from the package's `__init__.py` (confirmed: `FeedMarket`/`FeedPipeline` are in both, `FeedSubscription` only in `models.__all__`). This means `check_surface_types.py`'s scan does not cover `FeedSubscription`'s 15 fields today (confirmed: the tool's own field-count delta of +10 excludes the 15 `FeedSubscription` fields). Tracked in `ROADMAP.md` § Backlog, candidate for Phase 44.

Neither item blocks this phase's goal — both are explicitly out of D-16's locked scope, both are named in `ROADMAP.md`'s backlog section (confirmed present), and neither regresses any of the 5 success criteria.

### Gaps Summary

None. All 5 ROADMAP success criteria and all must-haves declared across the three PLAN.md frontmatter blocks were independently verified against the live codebase (not SUMMARY claims): field declarations read directly from `models.py`, the no-regression/no-flip mechanics traced through `_decode.py`, the CI gates re-run locally (727 tests passed, mypy clean, surface-types 0 violations, decode-intactness/uniform-structure green), the diff scoped to exactly `models.py` + `_core.py` (docstring-only) + 7 test files with no version bump. The two backlog items found (`DRV-MD-SEG-43`, `SURF-MD-FEEDSUB-43`) are explicitly scoped out by D-16, tracked in `ROADMAP.md`, and do not represent gaps in this phase's own goal.

---

_Verified: 2026-09-01T01:34:07Z_
_Verifier: Claude (gsd-verifier)_
