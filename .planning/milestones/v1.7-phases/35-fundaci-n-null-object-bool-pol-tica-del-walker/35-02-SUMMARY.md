---
phase: 35-fundaci-n-null-object-bool-pol-tica-del-walker
plan: 02
subsystem: planning artefact — D-17 accounting ledger
tags: [null-object, census, accounting, d-17, nobj-02, phase-39-input]
requires: []
provides:
  - .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md
  - "middle term of Phase 39's subtraction: higyrus 2, iol 0, market-data 0, matriz 5 (distinct triples) / matriz 6 (records)"
affects:
  - 35-05 (walker edit — its verification can cite this ledger for what stops being emitted)
  - Phase 39 (criterio 4 — subtracts instead of rediscovering)
  - Phases 36/37/38 (their own new non-Optional links are explicitly OUT of this ledger)
tech-stack:
  added: []
  patterns:
    - "census artefact as a named greppable file (29-SIZING.md / 33-CENSUS.md / 33-LITERALS.md precedent)"
    - "every numeric cell is citation-backed or explicitly UNKNOWN — no bare zeros"
key-files:
  created:
    - .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md
  modified: []
decisions:
  - "35-02: the retired kind is `missing` for all 35 rows, read from the shipped walker (_decode.py:443-445 list branch via _kind_of, :482-484 WR-02 model branch) — not from 29-SIZING, whose corpus run predates WR-02."
  - "35-02: 29-SIZING's corpus run is NOT a descendant of WR-02 (git merge-base --is-ancestor 2c31790 36b79e2 → false), so its `non_dict` labels for matriz's five model-link records are pre-WR-02 and differ from today's walker in BOTH the `model` and the `kind` component of the 4-tuple; Phase 39 must match on (slug, field_path) and read `kind` from this ledger."
  - "35-02: matriz's retired count differs by column — 6 against the records floor, 5 against distinct triples — because S-3's link is one triple recorded in two corpus files (29-SIZING.md:145-146). This is the concrete demonstration of the unit hazard, not a hypothetical."
  - "35-02: 'triples retired' is the INTERSECTION of the roster with a measured census, never the row count — 28 of the 35 rows intersect no ratified floor at all."
  - "35-02: iol's explicit zero row lives in the MAIN table (not only in the subtraction table) so the package is never an omitted row, satisfying the must_have that a zero carries its reason and named destination inline."
metrics:
  duration: ~18 min
  tasks: 2
  files: 1
  completed: 2026-08-29
status: complete
---

# Phase 35 Plan 02: D-17 retired-triples ledger Summary

A 241-line, greppable accounting artefact that states, per package and per field, exactly
which census 4-tuples the NOBJ-02 disposition stops emitting — so Phase 39 subtracts instead
of rediscovering, and the post-milestone drop in divergences cannot be read as a clean bill
of health it did not earn.

## What was built

`.planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md`,
containing:

1. **Header block** — counting unit (the distinct 4-tuple `(slug, model, field_path, kind)`,
   identical to `33-CENSUS.md:13-17`), the disposition applied, what it does NOT retire
   (wrong-type, `extra`, scalar `missing`, top-level `non_dict` per D-03a, the mapping axis
   per D-03c), and provenance (measured 2026-08-28 against `HEAD = 242b9f3`, still valid at
   `235506b` because 35-01 added methods, not fields).
2. **"Why every retired kind is `missing`"** — read from the shipped walker, with the
   pre-WR-02 kind caveat proven by `git merge-base --is-ancestor`.
3. **Main table** — 35 field rows plus one explicit reasoned zero row for `iol-client`,
   with two provenance columns and a note column.
4. **Unit warning** — the records-vs-distinct-triples conversion with the `33-CENSUS.md`
   citation.
5. **Expected subtraction per package** — all six packages, each row naming the column it
   counts against.
6. **How Phase 39 should use this** — mechanics, the failure mode, what a non-balancing
   subtraction means and which cause to check first.
7. **Method and limits** — the introspection blind spot, the direction of the error and why
   it is the safe one, plus two scope limits with named destinations.

## Per-package retired counts (the middle term Phase 39 subtracts)

| Package | Field rows in the roster | Triples retired (distinct) | Triples retired (records) | Expected post-35 baseline |
|---|---:|---:|---:|---|
| `higyrus-client` | 11 | **2** | **2** | 20 distinct / ≥ 20 records |
| `iol-client` | 0 | **0** | **0** | N/A — not zero (no floor exists) |
| `market-data-client` | 8 | **0** | **0** | 22 distinct / ≥ 50 records, both unchanged; live census 24 unchanged |
| `matriz-client` | 16 | **5** | **6** | 9 distinct / 18 records |
| `ambito-financiero-client` | 0 | 0 by enumeration | 0 by enumeration | N/A — declares no models |
| `wallets-client` | 0 | 0 by enumeration | 0 by enumeration | N/A — declares no models, no walker |

Only **7 of the 35** rows intersect a ratified floor: higyrus `Movimiento.idMovimientos` and
`Posicion.parking`; matriz's S-3 `Instrument` identity link and the four S-5
`MarketDataSnapshot` entry-value fields. The other 28 are candidates that retire nothing
because they were never observed diverging.

## Cells that came out UNKNOWN

**None.** All 70 provenance cells resolved against a committed artefact. The two candidates
for `UNKNOWN` were `CalendarConfigPreview.market_after` and `.warnings`; both resolved
positively to "the class is newer than both source artefacts" — it was created by the 33-07
fix for S-2, after the census run — which is a stronger statement than not knowing.

## Gaps 35-05's verification and Phase 39's planner should see

- **Kind mismatch against `29-SIZING.md`.** Its corpus run predates WR-02 (`36b79e2` is not
  a descendant of `2c31790`), so it labels matriz's five model-link records `non_dict`
  attributed to the *nested* class, while today's shipped walker labels the same wire
  `missing` attributed to the *outer* model. Two of the four 4-tuple components differ for
  those rows. Match on `(slug, field_path)`; read `kind` from the ledger.
- **matriz's answer is column-dependent** (6 records vs. 5 distinct triples). Any subtraction
  that does not name its column will be wrong by one for matriz.
- **higyrus and matriz have no measured live census** to intersect with — `LIVE-HIGY-33`
  (DNS) and `LIVE-MATZ-33` (the remarkets-only assert, not to be worked around). Their
  retired counts are intersections with the `29-SIZING.md` floor only. Phase 39 must record
  them `SKIPPED` with measured cause and named destination.
- **Phases 36-38 are out of scope of this ledger.** Their new non-`Optional` links
  (market-data's `market_data`, matriz's typed report fields, iol's two order-book links)
  will retire further triples that belong to their own phases' accounting.
- **market-data's live census of 24 triples is untouched by NOBJ-02.** Any drop there in
  Phase 39 must be attributed to fixes, never to this policy.

## Deviations from Plan

None — plan executed exactly as written. Both tasks' acceptance criteria were checked with
the literal greps they specify:

| Check | Expected | Actual |
|---|---|---|
| `grep -c '^\| '` | ≥ 35 | 48 |
| `grep -c '^\| higyrus-client '` | 11 | 11 |
| `grep -c '^\| market-data-client '` | 8 | 8 |
| `grep -c '^\| matriz-client '` | 16 | 16 |
| `grep -c 'instrumentId'` | 5 | 5 |
| `grep -c 'idMovimientos'` / `'parking'` | ≥ 1 each | 1 / 1 |
| `grep -c '33-CENSUS'` / `'29-SIZING'` | ≥ 2 each | 48 / 49 |
| `grep -c '\| *\| *\|'` (blank cells) | 0 | 0 |
| `grep -ci 'estimat'` | 0 outside a denial | 1, and it is the denial sentence |
| `grep -A1 '^\| iol-client' \| grep -qi 'phase 38'` | match | match |

One structural choice worth naming (within the plan's stated discretion, not a deviation):
`iol-client`'s explicit zero row was placed in the **main table** as well as the subtraction
table, so the package is never an omitted row anywhere in the document. The main table
therefore holds 36 pipe rows — 35 field rows plus that one non-field row.

## Verification

| Step | Result |
|---|---|
| `test -f 35-RETIRED-TRIPLES.md` | PASS |
| `git diff --name-only HEAD~2 HEAD` | exactly one file, under `.planning/` — no package, tool or test file touched |
| `git diff --exit-code pyproject.toml uv.lock` | clean (T-35-SC: no installs) |
| `uv run pytest packages -q` | **1810 passed, 1 deselected** in 91.04s |
| `tools/check_decode_intactness.py` | OK |
| `tools/check_uniform_structure.py` | OK |
| `tools/check_surface_types.py` | OK |
| `tools/surface_parity.py` | OK |

## Threat model dispositions

- **T-35-04 (repudiation — the ledger authoring a claim it cannot support):** mitigated.
  Zero blank provenance cells, zero uncited counts, and a "Method and limits" section that
  states the introspection blind spot and the direction of the error explicitly.
- **T-35-05 (information disclosure):** accepted as scoped. The ledger records declared type
  names and field paths only — no payload values, no hostnames, no credentials.
- **T-35-SC (dependency tampering):** accepted as scoped. No installs; `pyproject.toml` and
  `uv.lock` verified clean.

## Commits

| Task | Commit | Description |
|---|---|---|
| 1 | `0036287` | derive the 35-row retired-triples table with per-cell provenance |
| 2 | `dda9d9b` | add the per-package subtraction, the iol zero-with-a-reason and the limits |

## Self-Check: PASSED

- `.planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md` — FOUND
- Commit `0036287` — FOUND
- Commit `dda9d9b` — FOUND
