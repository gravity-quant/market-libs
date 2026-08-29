---
phase: 36
plan: 01
subsystem: market-data-client
tags: [tests, decode, mapping-axis, null-objects]
status: in-progress
---

# Phase 36 Plan 01: Retirar el eje mapping del suite de tests — Summary

## CR-03 disposition verdict

**Verdict: `retire`**

The CR-03 required-mapping contract is retired from `market-data-client` together with the mapping
machinery it asserted against. The `_RequiredMapping` module-local carrier and its two tests
(`test_absent_required_mapping_field_reports_missing_and_substitutes_the_empty_dict` and
`test_strict_mode_raises_on_an_absent_required_mapping_field`) are deleted in Task 3.

**Rationale (one sentence):** After Phase 36 the contract's IMPLEMENTATION (`_mapping_value` /
`_apply_mapping_policy`) is being retired — not merely its example, as was the case at 33-07 — so
preserving the two tests would require keeping dead code alive in a shipped module purely to have
something to assert against, contradicting CONTEXT D-05 directly and making ROADMAP SC-5
unachievable as written.

**How the verdict was reached:** this session ran under GSD auto-mode
(`workflow.auto_advance = true`); the Task 1 `checkpoint:decision` gate (`gate="blocking"`, not
`blocking-human`) was auto-resolved by selecting the FIRST option offered, `retire`, which is also
the 36-RESEARCH Open Question 1 recommendation.

**What survives the retirement:** the lock-8 half of the CR-03 block —
`test_mapping_pass_is_silent_under_a_non_dict_payload`, which asserts that a non-`dict` payload
emits exactly ONE terminal record — keeps its measured record set `[("", "non_dict")]` and is only
retitled in Plan 36-02. The four remaining tests of the CR-03 block that assert on
`MarketDataSnapshot.market_data` are untouched here; Plan 36-02 migrates them.

**Residual risk accepted:** `market-data-client` stops asserting that a required `dict[...]` field
reports and substitutes `{}`. If a future phase re-declares a mapping field in this package,
nothing in this package catches the regression until someone re-mints the axis. The contract is
recorded here by name (CR-03) so it is discoverable rather than only inferable from a diff.

<!-- gsd:write-continue -->
