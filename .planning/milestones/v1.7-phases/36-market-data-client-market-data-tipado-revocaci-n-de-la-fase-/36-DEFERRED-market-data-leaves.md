# Deferred — `MarketDataSnapshot.market_id` / `.active` are over-declared

**Raised by:** Phase 36 code review, CR-02 (`36-REVIEW.md`).
**Status:** DETECTED + DOCUMENTED, **not** corrected. Needs an operator checkpoint.
**Predicted to surface in:** Phase 39 (live strict run against develop).

## The measurement

The committed baseline
`.planning/verification/schemas/market-data-client/get-latest.json` — the
`GET /marketdata/latest` answer for a symbol the feed has never delivered — is,
verbatim:

```json
{"active":"NoneType","market_data":"NoneType","market_id":"NoneType",
 "note":"str","received_at":"NoneType","staleness_seconds":"NoneType","symbol":"str"}
```

`MarketDataSnapshot` declares `market_id: str` and `active: bool`, both
non-optional scalar **leaves**. Against that row the walker reports two `missing`
divergences and substitutes the silent typed zeros `""` and `False`; under
`strict_decode` it raises:

```
MarketDataDecodeError: decode divergence in MarketDataSnapshot.market_id:
                       declared str, observed NoneType
```

Both halves of the union are MEASURED, not inferred: the same two fields arrive
as a populated `str` / `bool` on the `/marketdata` baseline
(`get-market-data.json`). Under the repo's own option-b nullability rule (Phase
31, plan 31-04 Task 1 — "nothing is declared nullable unless CONTEXT-locked or
actually observed as `null` in a live capture") both fields QUALIFY for `| None`.

## Why it is not fixed in this pass

The correct fix is the same one Phase 36 applied by field role to
`staleness_seconds` (D-NO-03): a scalar LEAF with nothing to point at on a
no-data row keeps its `| None`, because manufacturing a typed zero for it is the
silent substitution this milestone exists to remove. Widening `market_id` and
`active` is therefore the honest disposition — and it is **source-breaking on a
published read surface**.

Every prior shape change of that kind in this repo went through a blocking
operator checkpoint (33-07 Task 1, `SC-2 = fix-shape-now`, signed; 31-04 Task 1,
option-b, signed). A code-review fixer taking that decision autonomously would
bypass the governance those checkpoints exist to enforce, so it is deferred
instead of applied.

## What Phase 36 DID do about it

CR-02's actual defect was that the regression guard hid this: the fixtures
claimed to mirror `get-latest.json` and quietly populated the two fields the
baseline sends as `null`, so "the assertion with teeth" was green only because
its payload had been doctored. That is fixed — the fixtures are now the baseline
verbatim, and the surviving divergence is ASSERTED rather than absent:

- `packages/market-data-client/tests/test_snapshot_no_data_row.py`
  - `_NO_DATA_ROW` is the baseline verbatim (no `entries` key; `market_id` /
    `active` / `market_data` / `received_at` / `staleness_seconds` all `null`).
  - `test_no_data_row_keeps_its_nulls` (+ `_async`) asserts `market_id == ""` and
    `active is False` — the manufactured zeros, named as such.
  - `test_no_data_row_links_are_never_fatal_under_strict_decode` (+ `_async`)
    isolates the LINKS on a row where only they are `null`.
  - `test_the_measured_no_data_row_still_raises_on_an_over_declared_leaf`
    (+ `_async`) pins `field_path == ".market_id"`, so the raise is proven to
    come from a LEAF and never from `.market_data` / `.entries`.
- `packages/market-data-client/tests/test_market_data_chain.py`
  - `_MEASURED_NO_DATA_ROW` joins the module, and
    `test_the_measured_no_data_row_is_the_committed_baseline_key_for_key` pins
    the fixture against the JSON file itself, so a fixture can never again drift
    from the baseline it claims to mirror without reddening.

## Recommended disposition

Widen both by field role at the next shape checkpoint, together with the Phase 40
coordinated version bump that already owns this package's breaking set:

```python
market_id: str | None
active: bool | None
```

Then the two `assert row.market_id == ""` / `assert row.active is False` lines
become `is None`, and
`test_the_measured_no_data_row_still_raises_on_an_over_declared_leaf` (both
surfaces) is retired — the measured row would stop raising entirely.

If the operator instead selects "keep declared", record the two fields as
permanent NO-FIX entries in
`.planning/verification/market-data-client-findings.md` so the divergence census
stops counting them as unexplained.
