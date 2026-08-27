---
phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
reviewed: 2026-08-26T00:00:00Z
depth: standard
files_reviewed: 26
files_reviewed_list:
  - verification/divergences.py
  - verification/test_divergences.py
  - verification/__init__.py
  - main_higyrus.py
  - main_matriz.py
  - main_iol.py
  - main_ambito_financiero.py
  - main_market_data.py
  - verification/test_probe_context_coverage.py
  - verification/test_finding_count_consistency.py
  - scripts/preflight_33.py
  - scripts/literal_census_33.py
  - packages/iol-client/src/iol_client/types.py
  - packages/iol-client/src/iol_client/models.py
  - verification/test_cycle_closure_phase33.py
  - packages/market-data-client/src/market_data_client/models.py
  - packages/market-data-client/src/market_data_client/_core.py
  - packages/market-data-client/src/market_data_client/client.py
  - packages/market-data-client/src/market_data_client/aio.py
  - packages/market-data-client/src/market_data_client/__init__.py
  - packages/market-data-client/tests/test_decode.py
  - packages/market-data-client/tests/test_models.py
  - packages/market-data-client/tests/test_calendar_write.py
  - packages/market-data-client/tests/test_calendar_write_async.py
  - packages/market-data-client/tests/test_public_surface_market_data.py
  - packages/market-data-client/tests/test_reference_envelope_unwrap.py
  - packages/market-data-client/tests/test_preview_calendar_config_envelope.py
  - packages/market-data-client/tests/test_snapshot_no_data_row.py
  - packages/market-data-client/tests/test_symbol_write_ack_timestamps.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 33: Code Review Report

**Reviewed:** 2026-08-26T00:00:00Z
**Depth:** standard
**Files Reviewed:** 26 (+3 not independently re-verified line-by-line; see notes)
**Status:** issues_found

## Summary

This phase wires a new logging-based divergence handler (`verification/divergences.py`)
into five API-client drivers and fixes four confirmed model-shape defects in
`market-data-client` (S-1 envelope unwrap, SC-1/S-2 preview envelope split,
SC-2 `MarketDataSnapshot` Optional widening, SC-3 `Symbol` timestamp widening).

I read `verification/divergences.py` and its test suite line-by-line, traced
`probe_context` / `divergence_capture` / `DivergenceHandler` through their P-1/P-2/P-3
hardenings, and independently verified each documented behavior against its test.
I then read `market_data_client/models.py`, `_core.py`, `client.py`, `aio.py` and
`__init__.py` in full and cross-checked `CalendarConfigPreview` / `PreviewMarket` /
`Symbol.created_at` / `Symbol.updated_at` / `MarketDataSnapshot.{entries,market_data,
staleness_seconds}` for consistency across all five surfaces (declaration, builder/parser,
sync shell, async shell, package exports), including against the committed live-capture
JSON baselines and the corresponding regression tests. I traced the `divergence_capture`
wiring in all five `main_*.py` drivers (logger names, fid allocator sharing, ordering of
`write_findings` / `_seed_fid_counter` / first probe, `DIVERGENCES`/`HANDLER_ERRORS`
reporting) and the three distinct-but-equivalent patterns used to avoid double-writing a
`SHAPE` finding when a probe hits a decode error (higyrus/matriz via `probe_context`'s
`decode_error=`/`on_decode_error=` seam; iol via an in-probe `except` that calls the same
helper directly; market-data via an in-probe `except Exception` dispatching to
`_finding_for_exc`). All three converge on the same "the `DivergenceHandler` already wrote
the finding; do not write a second one" invariant and I did not find a case where a
divergence gets double-counted or silently dropped as a result of driver plumbing.

I did not find any BLOCKER-class issue (no security vulnerability, no data-loss risk, no
incorrect behavior that would ship broken) in the reviewed diff. The codebase carries an
unusually high density of self-documentation and regression tests that directly pin the
behaviors this review would otherwise have to infer, which made several initially-plausible
hypotheses (mapping-policy Optional handling, `_ENDPOINT_OPTIONAL` scope vs. the SC-2
widening, sync/async parity of the `Symbol`/`CalendarConfigPreview` shape-diff call sites)
resolve cleanly on closer reading against the committed baselines and tests. Two WARNING-
level findings and three INFO-level observations remain, detailed below.

**Note on scope:** `test_calendar_write.py` / `test_calendar_write_async.py` were read in
full but concern the Phase 26/27/31 calendar-write surface, not a Phase-33-introduced
behavior; they are listed because they were in `files_to_read` and were read for cross-
consistency with `CalendarConfigPreview`.

## Warnings

### WR-01: `iol_client/models.py::SafeModel.to_dict()` carries a docstring claim that Phase 30's own review established as false, and that `market_data_client`'s sibling copy was corrected to contradict

**File:** `packages/iol-client/src/iol_client/models.py:80-94`
**Issue:**
`SafeModel.to_dict()`'s docstring states:

> "Escape hatch for the dict -> model break of Phase 30, **and the adapter the
> verification harness feeds to `verification.schema.schema_of`**."

This is the same sentence `market_data_client/models.py::SafeModel.to_dict()` used to
carry, and this milestone's own code (and Phase 30/31's own CR-01 finding, restated at
length in `market_data_client/models.py:66-78`) establishes it is **wrong**: `schema_of`
over a model projection is a function of the model's *declaration*, not of the wire — the
walker has already coerced every non-optional field to its declared type and dropped every
undeclared key, so a `float→str`, an added key and a removed key are all three invisible
to `schema_of(model.to_dict())`. `market_data_client/models.py:69-78` was rewritten to say
the opposite explicitly ("It is NOT a valid input to `verification.schema.schema_of`") and
every `main_market_data.py` schema-snapshot call site feeds raw wire, never `to_dict()`
output (confirmed: `_raw_via_request_sync`/`_raw_via_request_async`). `main_iol.py` also
already does the right thing at runtime (`_capture_raw_wire`, itself documented as the
"CR-01 ratified" fix). So there is no live bug today — but `iol_client/models.py`'s
docstring is the one copy in this review's file set that still asserts the disproven claim
as fact, in a module whose own module docstring explicitly claims "this module owns no
emission channel of its own" and is held to the same DecodePolicy ratification rigor as
every other paragraph in the file.

**Fix:**
Mirror the correction already applied to `market_data_client/models.py:66-78` into
`packages/iol-client/src/iol_client/models.py:80-94`, e.g.:

```python
def to_dict(self) -> dict[str, Any]:
    """Re-project the model as the plain wire dict (D-08).

    Escape hatch for the dict -> model break of Phase 30: use it for
    ``len()`` / ``isinstance`` call sites ONLY. It is **NOT** a valid input to
    ``verification.schema.schema_of`` — the walker has already coerced every
    non-optional field to its declared type and dropped every undeclared key,
    so a type change, an added key and a removed key are all three invisible
    in this projection (Phase 30 CR-01). Every driver schema-snapshot site
    must keep feeding RAW WIRE (see ``main_iol.py``'s ``_capture_raw_wire``).
    ...
    """
```

### WR-02: Three independent, differently-shaped implementations of the same "don't double-write the SHAPE finding on decode error" invariant across the five drivers

**File:** `main_higyrus.py` / `main_matriz.py` (via `probe_context(decode_error=..., on_decode_error=...)`) vs. `main_iol.py` (in-probe `except IOLDecodeError` calling `_shape_probe_result` directly, `probe_context` never receives `decode_error=`) vs. `main_market_data.py` (in-probe broad `except Exception` dispatching through `_finding_for_exc`, which special-cases `MarketDataDecodeError`; `probe_context` also never receives `decode_error=`)
**Issue:** All three converge on the same net effect (the `DivergenceHandler` writes the one `SHAPE` finding; the probe-local handler only translates the already-raised exception into a `ProbeResult` without calling `append_finding` a second time), and each divergence from the `probe_context`-seam pattern is explained in-line with a specific, defensible rationale (`main_iol.py:365-406`, `main_market_data.py:374-416`). This is not a functional bug — I traced all three paths and none produces a duplicate finding or a silently-dropped one. It is, however, three different code shapes solving an identical problem, discoverable only by reading each driver's private rationale in full; a future contributor extending a fourth driver (or extending `market-data-client`'s probe set) has no single canonical pattern to copy and risks re-deriving a fourth shape, or worse, copying the `probe_context(decode_error=...)` seam onto a driver whose `except Exception` already intercepts the decode error upstream (which — per `main_iol.py`'s own docstring at line 372 — would make the decorator kwarg silently dead code, exactly the trap `main_iol.py`'s comment says it wrote itself to prevent a "future reader" from stumbling into).
**Fix:** No code change required for this phase; consider consolidating to one canonical pattern (or documenting the decision matrix in `verification/divergences.py`'s module docstring, next to the existing `probe_context` contract) before a sixth verifiable package is added, so the choice of pattern is made once instead of re-litigated per driver.

## Info

### IN-01: `divergence_capture`'s per-triple census (`handler.seen`) intentionally undercounts relative to distinct finding titles when `observed_type` varies across calls for the same `(model, field_path, kind)`

**File:** `verification/divergences.py:112-187`
**Issue:** `DivergenceHandler.seen` is keyed on `(slug, model, field_path, kind)` — it does not include `declared_type`/`observed_type`. If the *same* field diverges with different observed wire types across two calls within one run (e.g. `int` once, `str` once — plausible for a loosely-typed vendor field), two distinct-titled findings are written (title includes `declared`/`observed`), but `len(handler.seen)` still reports one triple. This is consistent with the documented intent ("`seen` is the unit of the census … NOT the finding count — with the surface embedded in the title there are ~2 findings per triple") and is not a bug against that stated contract, but the "~2 findings per triple" approximation in every driver's `SUMMARY` comment is only strictly true when `observed_type` is stable per field within a run; it is not enforced or asserted anywhere. Not actionable without knowing whether any of the five vendors actually exhibit multi-typed fields within a single run — flagging for awareness, not for a code change.

### IN-02: `CLAUDE.md`'s architectural-constraints section is stale relative to `matriz_client` async support

**File:** `main_matriz.py:1,17-26,84-99` (imports and uses `matriz_client.AsyncClient` / `matriz_client.aio` extensively) vs. project `CLAUDE.md` ("Architectural Constraints" → "No async support in matriz: `matriz_client` has no `aio.py`.")
**Issue:** `main_matriz.py`'s own module docstring states Phase 10 landed `matriz_client.aio` as a REST-only async surface, and the file imports and exercises `AsyncClient` throughout (`_async_main`, ~23 async probes). `CLAUDE.md` — read as part of this review's mandated project-context step — still asserts the opposite. Not a defect in the reviewed source files, but a documentation-drift observation surfaced by this review; `CLAUDE.md` is itself checked into the repo and is read as authoritative context by every future agent session.
**Fix:** Update `CLAUDE.md`'s Architectural Constraints / Anti-Patterns sections to reflect the Phase 10 `matriz_client.aio` REST-only async surface (out of scope for this review to edit directly).

### IN-03: `_DAY_SEGMENT_RE.fullmatch(...)` is redundant given the pattern's own `\A...\Z` anchors

**File:** `packages/market-data-client/src/market_data_client/_core.py:811,882`
**Issue:** `_DAY_SEGMENT_RE = re.compile(r"\A[A-Za-z0-9._~-]+\Z")` is already fully anchored; calling `.fullmatch(day)` instead of `.match(day)` (or `.search(day)`) adds no additional guarantee here — both anchoring mechanisms are already present and redundant with each other. Purely stylistic; no behavioral difference and no security implication (the char-class + all-dots check the surrounding code performs is sound either way).
**Fix:** Optional simplification — drop either the `\A...\Z` anchors from the pattern or switch to `.match()`, not both. Not worth a dedicated change on its own.

---

_Reviewed: 2026-08-26T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
