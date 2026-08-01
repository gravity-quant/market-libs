---
phase: 27-verificaci-n-en-vivo-segura-fixes
plan: 01
subsystem: verification-harness
tags: [verification, findings, cycle-closure, fid-allocator, tdd, pytest]

# Dependency graph
requires:
  - phase: 23-market-data-client-live-verification
    provides: "main_market_data.py, the write-once schema snapshots and the F-01..F-36 findings corpus this plan repairs"
  - phase: 11-harness-hardening
    provides: "verification/findings.py append-only BEGIN/END zone contract and verification/cycle_report.py"
provides:
  - "append_finding with a NEW fid no longer destroys the human-triage prose of pre-existing findings (D-23)"
  - "max_existing_fid(pkg) so a driver allocator can seed above the highest recorded fid (D-16/D-24)"
  - "34 legacy Regression bullets backfilled on F-03..F-36, taking market-data-client cycle closure from (False, 34) to (True, [])"
affects: [27-03-driver-gate, 27-04-symbols-cycle, 27-05-calendar-cycle, 27-06-armed-run, 27-07-close-cycle]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Unknown-bullet round-trip: _parse_findings captures every bullet and _serialize_findings re-emits them, so an additive serializer change preserves fields it does not model"
    - "Allocator seeding over title-dedupe: max_existing_fid replaces the reset-to-zero counter that collided with recorded findings"

key-files:
  created:
    - verification/test_findings_fid_seed.py
    - verification/test_cycle_closure_market_data.py
    - .planning/phases/27-verificaci-n-en-vivo-segura-fixes/deferred-items.md
  modified:
    - verification/findings.py
    - verification/test_findings_append_only.py
    - .planning/verification/market-data-client-findings.md
    - packages/market-data-client/tests/test_models.py
    - packages/market-data-client/tests/test_reference_models.py
---

# Plan 27-01 — Harness plumbing

> **Close-out note (orchestrator-written).** The executor committed all three tasks but
> terminated before writing this SUMMARY, leaving its worktree locked. Per the
> `safe_resume_gate` recovery options this was closed out **manually** rather than
> re-executed, because the committed work was independently verified correct first (see
> Verification below). Re-executing would have duplicated commits on already-correct work.
> Content below is reconstructed from the five task commits and direct inspection of the
> merged tree — not from executor narration.

## Objective

Close the three harness blockers that RESEARCH reproduced **by execution**, so the later
destructive live run can actually record its own deliverable. Without this plan a live run
would silently discard its findings and corrupt 36 existing records.

## Tasks completed

| # | Task | Commits |
|---|------|---------|
| 1 | Preserve unknown finding bullets across re-serialization (D-23) | `a06b966` (RED) → `62c6888` (GREEN) |
| 2 | Add `max_existing_fid(pkg)` allocator-seed helper (D-16/D-24) | `043f656` (RED) → `07ffbce` (GREEN) |
| 3 | Backfill the 34 legacy `Regression:` bullets, lock cycle closure (D-21/D-18) | `16e9141` |

Both TDD tasks committed a genuine failing RED before GREEN.

## What shipped

**D-23 — the data-loss fix.** `_parse_findings` already captured every bullet but forwarded
only four to `_Finding`; `_serialize_findings` therefore re-emitted only those four. The fix
carries the remaining bullets through as `extra_bullets` and re-emits them. This is an
additive serializer change — `append_finding`'s public signature is unchanged, which matters
because the module is shared by five drivers.

**D-16/D-24 — the allocator seed.** `max_existing_fid(pkg)` returns the highest fid already
recorded, so a driver can start above it instead of resetting to zero and colliding with
`F-01`…`F-36`. RESEARCH proved `idempotent_by_title=True` cannot substitute here: the title
check runs *before* the fid short-circuit but only no-ops on an already-present title, and
every new finding carries a new title. The plan did not offer the title approach as an
alternative and none was taken.

**D-21/D-18 — the backfill.** 34 `Regression:` bullets added to F-03…F-36, each pointing at
the test that already covered that fix (from the v1.4 sweep and quick tasks `260731-j93`,
`260731-jim`, `260731-t9o`). No new tests were needed — the coverage existed and was simply
never linked.

## Verification

Independently checked against the merged tree, not taken on trust:

- **Cycle closure:** `verify_cycle_closure("market-data-client")` → `(True, [])`. It returned
  `(False, 34)` at base SHA `dd56f21`. The other three packages were already `(True, [])`.
- **Prose preservation:** `Classification:` **36** and `Resolution:` **34** bullets survive
  intact, and the findings file **grew** 22,212 → 26,226 bytes. The bug's signature was a
  collapse to ~11,580 bytes with both counts going to 0.
- **Link relevance audited.** `cycle_report.py` only validates that a `Regression:` path
  resolves and contains `def <test_name>(` — it cannot tell whether the test is *relevant*, so
  a well-formed fabrication would pass. Sampled the backfill: F-03…F-07 ("wire-only field
  {active, market_data, market_id, note, staleness_seconds} en MarketDataSnapshot") all point
  at `test_models.py::test_from_api_marketdata_item_parses_new_fields`, whose body asserts
  exactly those five fields. Findings sharing one test is legitimate here — they are one
  defect class (the `260731-jim` model reconciliation). No fabricated links found.
- **New tests:** 17 pass across `test_findings_fid_seed.py`, `test_cycle_closure_market_data.py`
  and the extended `test_findings_append_only.py`.

## Deviations

None from the plan's scope. The plan's blast-radius bound ("additive fix to a module shared by
five drivers; blast radius must stay at the serializer") was respected — see deferred item 3.

## Deferred

Recorded in full in `deferred-items.md`. Three items, none blocking:

1. **`test_main_matriz_login_fail_uniformity.py`** — 2 failures + 2 errors from Phase-15
   signature drift (`probe_login_sync()` called without its now-required `client` arg).
2. **`test_matriz_sweep_snapshot.py`** — 17 failures + 17 errors, same root cause.
   Together: **19 failed / 19 errors / 220 passed** in `verification/`. **Proven pre-existing**
   by reverting `verification/findings.py` and reproducing the identical counts, so this plan
   is not implicated. Plan 27-02 independently reached the same conclusion at the same base
   SHA. Practical effect: the matriz sweep-snapshot guard currently guards nothing.
3. **`append_finding` same-fid update on an OPEN finding still drops `extra_bullets`** — the
   replacement path builds a fresh `_Finding` with empty `extra_bullets`. The non-OPEN
   short-circuit already protects every promoted finding (CONFIRMED/FIXED/EXPECTED/NO-FIX),
   which is the case this phase depends on. One-line follow-up if a later phase wants it.

## Requirement

`LIVE-MUT-01` — partially advanced. This plan makes criteria 4 and 5 *reachable*; it does not
satisfy them. All seven plans in the phase claim the requirement; it is marked complete only
after 27-07.
