# Phase 37: `matriz-client` — dicts residuales tipados + alias - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-29
**Phase:** 37-matriz-client-dicts-residuales-tipados-alias
**Mode:** assumptions
**Areas analyzed:** Gate extension mechanism, Provenance and observability of the four payloads,
Container shapes and fate of the mapping axis, Alias properties on MarketDataSnapshot

## Assumptions Presented

### Gate extension mechanism (SC-2)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Extend `tools/check_surface_types.py` with a field-scan dimension (not a matriz-local test) | Confident | `_candidates_for` (`tools/check_surface_types.py:495-514`) only yields function defs; running the gate now shows "0 violations" with all 5 sites in place |
| Field predicate must be narrower than the return predicate (`dict[str, Any]`/bare `Any` only) | Confident (measurement) / Likely (resolution) | AST scan found `CalendarConfig.warnings: list[Any]` and `CalendarConfigPreview.warnings: list[Any]` in exported market-data-client classes — a broad predicate would redden an out-of-scope package |
| Extension lands in the shared gate in the `lint` job | Confident | Gate's own docstring (D-05/D-12) rules out per-package `test` job and `verification/` (never runs in CI); `.planning/research/ARCHITECTURE.md:397` already names this blind spot |

### Provenance and observability of the four payloads (SC-1)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `packages/matriz-client/documentation/Primary-API.md` is admissible evidence, new provenance tier | Confident (file exists) / Unclear (qualifies under D-10) | Vendor doc committed in-package, never cited by any planning artifact; Phase 36's D-10 "forbids retyping on another source's authority alone" |
| `AccountReport.portfolio` is a scalar, not a mapping | Likely | `Primary-API.md:1894` shows `"portfolio": 60240`, matching `totalMarketValue: 60240` for the same account elsewhere in the doc |
| Risk parsers (`get_detailed_positions`/`get_account_report`) may be missing envelope unwrap | Likely | Asymmetry with sibling `get_positions` (`_core.py:885-889` unwraps, `:914-918`/`:941-945` don't); vendor doc shows wrapped bodies; no existing test would catch it |
| Provenance declared via existing two-artifact pattern (docstring + findings ledger) | Confident | Direct Phase-36 precedent (`MarketDataEntries` docstring) + existing `matriz-client-findings.md` ledger already supports `NO-FIX`/`EXPECTED` terminal states |

### Container shapes and fate of the mapping axis
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `_mapping_value`/`_apply_mapping_policy` gets upgraded, not deleted | Confident | Unlike Phase 36's deletion (field became a walker-native nested model), `dict[str, Model]` still has no matching branch in `walk_field` — falls to bare pass-through |
| `tickPriceRanges` stays `dict[str, TickPriceRange]`, not `list[...]` | Likely | All observed samples (baseline + 3 vendor-doc samples) show a single key `"0"` — no evidence of contiguity/ordering |
| `DetailedPosition.report` gets minimal disposition, not full 2-level tree | Confident (shape) / Unclear (how much to model) | Two-level open-keyed mapping with ~20-field nested records observed only in vendor doc, zero live captures |

### Alias properties on `MarketDataSnapshot` (SC-3)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Six read-only `@property` aliases on `MarketDataSnapshot` cover both REST and WS surfaces already | Confident | `MarketDataFrame.marketData` is the identical class REST returns; `ws_client.py` has no duplicate snapshot class |
| Properties already proven invisible to the walker by Phase 35 fixtures | Confident | `test_null_object.py:196-215,292-311,314-326` already prove this exact invariant |
| Roster floor `_safemodel_classes() >= 17` needs raising, not equality-breaking | Confident | Existing floor assertion (`test_null_object.py:229`) + Phase 36 precedent of raising it (D-03) |

## Corrections Made

No corrections — user selected "Yes, proceed" after reviewing the full assumption summary
(presented as a follow-up text message with all recommended alternatives spelled out per area,
since the initial AskUserQuestion call did not itself render the assumption content before the
user answered — corrected by displaying the full content immediately after and inviting objection
before writing files; none was raised).

## Auto-Resolved

Not applicable — not run with `--auto`.

## External Research

None — the subagent's "Needs External Research" section was empty; every open question was
settled by evidence already inside the repository (including a previously-uncited in-repo vendor
doc, `packages/matriz-client/documentation/Primary-API.md`). The one genuinely unmeasurable item
(live Risk-API payloads) is blocked by the internal `D-MATZ-33` policy assert, not by a research
gap.
