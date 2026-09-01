---
phase: 43-market-data-client-forma-de-instrument-segment-5-claves-extr
reviewed: 2026-09-01T01:31:04Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - packages/market-data-client/src/market_data_client/_core.py
  - packages/market-data-client/src/market_data_client/models.py
  - packages/market-data-client/tests/test_core.py
  - packages/market-data-client/tests/test_decode.py
  - packages/market-data-client/tests/test_models.py
  - packages/market-data-client/tests/test_reference_async_client.py
  - packages/market-data-client/tests/test_reference_client.py
  - packages/market-data-client/tests/test_reference_core.py
  - packages/market-data-client/tests/test_reference_envelope_unwrap.py
  - packages/market-data-client/tests/test_reference_models.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 43: Code Review Report

**Reviewed:** 2026-09-01T01:31:04Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

This phase reconciles `Instrument` / `Segment` field shape against a fresh
2026-08-31 wire read and types five previously-`extra` decode keys
(`FeedSubscription`, `FeedIngestor.last_error_age_seconds` /
`.last_error_at`, `Symbol.note`, `HealthFeed.symbols_never_delivered`). The
implementation is unusually well-evidenced: every added/removed field cites a
specific finding ID (`F-2xx`) or a committed schema baseline, and the test
suite backs each shape claim with both an empty-payload zero-default test and
a populated-wire-row test.

Verification performed beyond reading the diff:

- `uv run --package market-data-client pytest packages/market-data-client/tests/` — 727 passed.
- `uv run mypy packages/market-data-client/src/market_data_client/_core.py .../models.py` — clean, strict mode.
- `uv run ruff check` over all ten reviewed files — clean.
- `uv run python tools/check_surface_types.py` — 0 violations (confirms `FeedSubscription` carries no `dict[str, Any]` field and is never declared `| None`, satisfying `D-NO-01`).
- `uv run python tools/check_decode_intactness.py` and `tools/check_uniform_structure.py` — both green (confirms `_decode.py`, untouched by this diff, is still byte-identical across packages).
- Cross-package grep for stale attribute access against the removed `Instrument`/`Segment` fields.
- Manual comparison of every re-derived test fixture against
  `.planning/verification/market-data-client-findings.md` (F-140/F-109,
  F-205..F-218, F-67..F-71/F-87..F-89, F-202) to confirm no fixture invents a
  key or value the wire never sent, and that no fixture leaks a value from the
  gitignored raw capture — all fixtures use synthetic values over a
  measured key set, exactly as their comments claim.

The `Instrument.from_api` / `Symbol.from_api` alias mirrors are correct:
both use the required two-argument `super(Cls, cls).from_api(payload)` form
(mandatory once `@dataclass(slots=True)` rebuilds the class), both only FILL
an absent `marketId` rather than overwrite an explicit one, and both copy the
payload dict rather than mutate the caller's. `FeedIngestor.subscription` is
correctly a non-optional nested model (never `FeedSubscription | None`),
which is exactly what the surface-types gate (`D-NO-01`) requires and what
the tool run above confirms.

One real, provable regression was found, but it lives outside the file list
under review (`main_market_data.py`) and is already tracked as a disposed
backlog item (`DRV-MD-SEG-43` in `ROADMAP.md`) rather than an oversight — see
WR-01 below. Two documentation-accuracy nits round out the findings; neither
has a runtime effect.

## Warnings

### WR-01: `main_market_data.py` still dereferences the field `Segment` removal deleted

**File:** `main_market_data.py:1541-1542` (not in this phase's file list, but directly caused by `models.py`'s `Segment` shape replacement in this diff)
**Issue:** `probe_parity` computes sync/async segment-id parity via:
```python
ids_sync = sorted(s.marketSegmentId for s in seg_sync)
ids_async = sorted(s.marketSegmentId for s in seg_async)
```
`Segment.marketSegmentId` no longer exists — `models.py`'s `Segment` class was
replaced wholesale in this diff with `segment: str` / `live_instruments: int`
(D-06, deliberately *not* alias-mapped, since `marketSegmentId` and `segment`
are different names rather than a spelling variant). Every future run of
`probe_parity` will raise `AttributeError: 'Segment' object has no attribute
'marketSegmentId'` inside its own `try/except Exception` block, so it will
not crash the driver, but it silently defeats the probe's actual purpose
(comparing sync/async segment IDs) and instead reports a generic exception
finding every single run. This is a genuine, currently-reachable break
introduced by the model-shape change under review.

This is not an unnoticed oversight — the phase's own planning artifacts
(`43-01-SUMMARY.md`, `43-03-SUMMARY.md`, `43-PATTERNS.md`) document the site,
confirm it is caught by the `try/except`, and record it as backlog item
`DRV-MD-SEG-43` for a later phase (D-16 scoped this phase to `models.py` +
tests only). Flagging it here because it is a real, reproducible break that a
reviewer should be able to find independently of the backlog note, and
because `grep -rn "marketSegmentId" packages/ main_*.py` still finds the
live call site today.
**Fix:** When `DRV-MD-SEG-43` is picked up, change the two lines to:
```python
ids_sync = sorted(s.segment for s in seg_sync)
ids_async = sorted(s.segment for s in seg_async)
```
(no other logic in `probe_parity` needs to change).

## Info

### IN-01: Nullability-verdict comment miscounts the Phase 43 additions

**File:** `packages/market-data-client/src/market_data_client/models.py:1255-1257`
**Issue:** The comment reads:
> Nothing else qualifies, and that is a decision, not an omission: the other
> three Phase 43 fields (`HealthFeed.symbols_never_delivered` and the two
> nested-model references) came back populated wherever they were observed.

Phase 43 adds exactly **four** new fields across `FeedIngestor` /
`HealthFeed`: `subscription`, `last_error_age_seconds`, `last_error_at` (all
three on `FeedIngestor`) and `symbols_never_delivered` (on `HealthFeed`). Two
of those four (`last_error_age_seconds`, `last_error_at`) are the pair
already accounted for a few lines above as the newly-nullable D-09 pair. That
leaves exactly **two** fields — `symbols_never_delivered` and
`subscription` — as "the other" fields that stayed non-nullable, and only
**one** of those two is a nested-model reference (`subscription`; there is
no second one). The comment's "three... fields... the two nested-model
references" over-counts by one field and by one nested-model reference. This
is corroborated mechanically by `test_every_fixture_key_is_a_measured_wire_key`
in `tests/test_core.py`, whose delta set names exactly four new top-level
keys, not five.
**Fix:** Reword to something like: "the other two Phase 43 fields
(`HealthFeed.symbols_never_delivered` and the one nested-model reference,
`FeedIngestor.subscription`) came back populated wherever they were
observed."

### IN-02: `Symbol.note` docstring cites F-140/F-109 for a claim those findings don't cover

**File:** `packages/market-data-client/src/market_data_client/models.py:950-960`
**Issue:** The docstring says `note` "is PRESENT in the write acknowledgements —
`create-symbol-sync-response.json` and `update-symbol-sync-response.json`,
measured live as `F-140` (sync) and `F-109` (async)". Checking
`.planning/verification/market-data-client-findings.md`, both F-140 and
F-109 are recorded with `Diff: - -> str at Symbol.note via
/symbols/{symbol_id}` — i.e. they were only measured against the `PATCH`
(update) endpoint, not `POST /symbols` (create). The underlying factual claim
about `create-symbol-sync-response.json` is independently true (its committed
schema baseline at
`.planning/verification/schemas/market-data-client/create-symbol-sync-response.json`
does show `"note": "str"`), so nothing is wrong about the field typing
decision itself — but citing F-140/F-109 as the evidence for the create-path
half of the claim is imprecise, since those two findings only speak to the
update path. A future reader chasing the citation to confirm the create-path
claim would find it unsupported by the named findings.
**Fix:** Either cite the `create-symbol-sync-response.json` baseline directly
for the create-path half of the claim (as the module already does elsewhere
for baseline-sourced facts), or drop the "measured live as F-140/F-109"
qualifier from the `create-symbol-sync-response.json` clause since those two
findings are update-path-only.

---

_Reviewed: 2026-09-01T01:31:04Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
