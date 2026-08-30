---
phase: 37
plan: 05
subsystem: matriz-client models — human-facing alias ergonomics
tags: [alias-properties, null-object, nobj-mtz-02, websocket, market-data, tdd, roster-floor, d-16]
status: complete

requires:
  - "Phase 35 NOBJ-01 / D-16 — `_SafeModel.empty` / `__bool__` plus the `_AliasShaped` / `_AliasFree` fixtures that prove `@property` aliases are invisible to `get_type_hints`, `dataclasses.fields` and therefore to the walker"
  - "Phase 36 D-03 — `market_data_client.models.MarketDataEntries`'s six-property alias block, the verbatim form template"
  - "37-02 — `TickPriceRange`, the first of the three classes the raised roster floor accounts for"
  - "37-03 — `InstrumentPositionReport` / `DetailedAccountReport` and the measured `_safemodel_classes()` count of 20"
provides:
  - "`MarketDataSnapshot.bids` / `.offers` / `.last` / `.settlement` / `.close` / `.open_interest` — six read-only `@property` views over `BI` / `OF` / `LA` / `SE` / `CL` / `OI`"
  - "The falsifiable form of Success Criterion 3: identity assertions on a REST-parsed AND a WS-frame-parsed snapshot, so the shared-object claim reddens if `MarketDataFrame.marketData` is ever retyped"
  - "A named exclusion decision for `OP` and matriz's seven extra scalars, asserted rather than left as an omission"
  - "`test_null_object.py`'s roster floor raised 17 → 20 with a three-line provenance (35-RESEARCH F-1, 37-02, 37-03)"
  - "The phase's closing cross-package sweep, recorded verbatim below"
affects:
  - "Phase 38 — inherits both the alias template and the still-valid criterio-5 invariant; the floor is a lower bound, so adding classes there needs no change here"
  - "Phase 39 / LIVE-NOBJ-01 — the Verification Results table below records exactly what was and was NOT verifiable live under D-MATZ-33"

tech-stack:
  added: []
  patterns:
    - "Alias-as-view: a single `return self.<WIRE>`, no copy, no cache, no default, no transformation, no setter — asserted with `is`, never `==`"
    - "One class, two surfaces: a property added to a model that is simultaneously a REST return type and a WS frame payload serves both with zero transport-layer change (37-RESEARCH F-12)"
    - "Cite-don't-duplicate: a generic invariant proven once on module-local fixtures is APPLIED to the real class by a shape-match assertion, never re-proven"
    - "Name-shadowing rationale for disjointness on a `frozen=True` dataclass WITHOUT `slots` — the collision would be silent, not a class-creation error, which is why it has to be asserted"
    - "Roster floors stay `>=` forever and carry an arithmetic provenance so the number is never re-guessed"

key-files:
  created: []
  modified:
    - packages/matriz-client/src/matriz_client/models.py
    - packages/matriz-client/tests/test_null_object.py

key-decisions:
  - "Aliases cite `NOBJ-MTZ-02, D-16` rather than market-data's `D-03` — matriz's own D-03 is this phase's Risk envelope unwrap, so copying the template's decision id verbatim would have pointed a reader at an unrelated decision"
  - "The disjointness rationale was rewritten, not copied: matriz's dataclasses carry no `slots`, so a colliding alias would silently shadow decoded wire data instead of failing at class creation"
  - "The wire roster is asserted EXACTLY (`== _WIRE_FIELDS`, len 14), not as a subset, so a fifteenth field reddens rather than widening the surface silently"
  - "No `ws_client.py` edit and no WS-side task — `MarketDataFrame.marketData` IS a `MarketDataSnapshot`, measured and now asserted"
  - "The roster floor stays an inequality; it was raised as hygiene and nothing was sequenced behind it (F-13)"

requirements-completed: [NOBJ-MTZ-02]

metrics:
  duration: ~8 min
  completed: 2026-08-29
  tasks: 2
  commits: 3
  files_changed: 2
  tests: 547 → 556 (matriz); `-k alias` 2 → 11
---

# Phase 37 Plan 05: Six alias views on one class that is already both surfaces — Summary

**`MarketDataSnapshot` gained `bids` / `offers` / `last` / `settlement` / `close` / `open_interest` as
read-only `@property` views, and the claim that REST and WebSocket share the same object with the same
alias set stopped being an assumption and became eight assertions — with `ws_client.py` byte-unchanged.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-08-29T16:23:40Z
- **Completed:** 2026-08-29T16:31:30Z
- **Tasks:** 2
- **Files modified:** 2

## The one measurement that shaped the whole plan

`MarketDataFrame.marketData` is annotated `MarketDataSnapshot` (`models.py:779`), and
`ws_client._parse_frame` builds the frame with a bare `MarketDataFrame.from_api(data)` — no separate
WS snapshot type exists anywhere. So six properties on **one** class satisfy Success Criterion 3 on
both surfaces. 37-RESEARCH F-12 called this and the plan's prohibition forbade fabricating a WS-side
task; the work here honours that by **asserting** the fact instead of writing a no-op around it:

```python
def test_one_class_serves_both_surfaces_so_the_alias_set_is_shared() -> None:
    rest = MarketDataSnapshot.from_api(_REST_MARKET_DATA)
    ws = MarketDataFrame.from_api(_WS_FRAME).marketData
    assert type(rest) is type(ws) is MarketDataSnapshot
```

The value of asserting it: the only way the shared-object claim could ever stop holding is a retype of
`MarketDataFrame.marketData`, and that now reddens immediately rather than silently splitting the two
surfaces apart.

## The six aliases

| Alias | Wire field | Return type |
|-------|-----------|-------------|
| `bids` | `BI` | `list[MarketDataLevel]` |
| `offers` | `OF` | `list[MarketDataLevel]` |
| `last` | `LA` | `MarketDataEntryValue` |
| `settlement` | `SE` | `MarketDataEntryValue` |
| `close` | `CL` | `MarketDataEntryValue` |
| `open_interest` | `OI` | `MarketDataEntryValue` |

Each is exactly one `return` of the wire attribute — the Phase 36 form copied verbatim apart from the
return types and the decision id. No copy, no cache, no default, no transformation, no setter.
Identity is asserted with `is` rather than `==` (T-37-27): a copying or caching alias would still
compare equal and would still pass an equality assertion while having quietly ceased to be a view.

**The decision id was changed deliberately.** market-data's block cites `(D-03)`; matriz's `D-03` in
this very phase is the Risk envelope unwrap. Copying the template's id verbatim would have pointed a
future reader at an unrelated decision, so the aliases cite `NOBJ-MTZ-02, D-16` — the requirement plus
Phase 35's property-invisibility decision, which is the id `_AliasShaped` itself already carries.

## The exclusion, stated as a decision

`OP` is the one a reader would look for as `open`. It has no alias because it arrives as a **bare
float**, not an `{price, size, date}` entry object — the pre-existing comment at the `CL` declaration
(issue #102) already records exactly that asymmetry, and the class docstring now points at it. An
`open` alias would return a scalar where its five siblings return a model.

`HI`, `LO`, `TV` are excluded for the same reason; `IV`, `EV`, `NV`, `ACP` are matriz-only scalars
absent from the Phase 36 template and outside `NOBJ-MTZ-02`'s named set.
`test_the_bare_scalar_entries_are_deliberately_left_unaliased` asserts that none of `open`, `high`,
`low`, `trade_volume`, `traded_volume` exists on the class, and pins the property set to exactly the
six names — so an eventual seventh alias is a conscious edit, not a drift.

## Disjointness — the rationale that could NOT be copied

market-data's disjointness test says a colliding alias "would either shadow the field or fail at class
creation", which is true there because `MarketDataEntries` is `frozen=True, slots=True`. matriz's
dataclasses carry **no** `slots` (semantics matrix row 5, difference 5). Here a collision would be
silent **name shadowing**: the property would sit on the class and win attribute lookup over the
`__dict__` entry the dataclass `__init__` wrote, quietly hiding decoded wire data behind a view of a
different field, with nothing raising. The test docstring states this in full — it is precisely why
the disjointness has to be asserted rather than trusted to the runtime.

## Applied, not re-proven (T-37-25)

`test_property_aliases_are_invisible_to_get_type_hints`,
`test_adding_a_property_alias_does_not_change_the_divergence_count` and their `_AliasShaped` /
`_AliasFree` fixtures are **unmodified**. `git diff` over this plan's commits shows no `-` line
touching any of them; the only new references are `+` lines citing them by name from the new tests'
docstrings and from a section comment. The new
`test_the_six_aliases_are_invisible_on_the_real_snapshot_class` checks only that the REAL class
matches those fixtures' shape, so the generic conclusion transfers to it — it deliberately does not
rebuild the `_walk` / `_records` machinery.

Two independent corroborations that the aliases really are invisible, beyond the test:

- `tools/check_surface_types.py` reports the same `442 fields scanned, 0 violations` after the change.
- Re-running `verification/regen_snapshots.py` produced **no diff** — the recorded public surface
  (`verification/snapshots/matriz-client-surface.txt`) is byte-identical, because it records the
  `__init__` signature and properties are not in it.

## Roster floor: 17 → 20, with arithmetic

Measured in-process before raising, per the plan's instruction not to guess:

```
$ uv run --package matriz-client python -c "... print(len(_safemodel_classes()))"
20
```

Matching the count `37-03-SUMMARY.md` recorded. The docstring now carries the provenance so the number
is never re-derived: `17` (35-RESEARCH F-1) `+1` `TickPriceRange` (37-02) `+2`
`InstrumentPositionReport` / `DetailedAccountReport` (37-03) `= 20`. It also records that this plan's
six aliases add **no** class — invisible to the roster for the same reason they are invisible to the
walker — and that `UnknownFrame` is excluded on purpose and must not be swept in by a "fixed" filter.

It stays `>=`, never `==`: F-13's point, and the Phase 36 precedent. **Nothing was sequenced behind
it.**

### The three new classes pass the parametrized Null Object contract

`pytest -k "InstrumentPositionReport or DetailedAccountReport or TickPriceRange"` → **9 passed**, i.e.
3 classes × 3 cases (falsy-when-empty, truthy-when-perturbed, silent `empty()`). `_perturb` did **not**
raise on any of them — RESEARCH Pitfall 5's failure mode did not occur, because all three carry
all-optional scalar fields defaulting to `None` and land on the dispatcher's first (`cur is None`)
branch, exactly as 37-03 predicted when it chose `int | None` for `settlementDate`.

## Task Commits

1. **Task 1: the six aliases + both-surface proof** — `4193dd2` (test, RED) → `65bd7c0` (feat, GREEN)
2. **Task 2: roster floor + closing sweep** — `0b4505b` (test)

No REFACTOR commit was needed; the GREEN implementation landed in final shape.

## Files Created/Modified

- `packages/matriz-client/src/matriz_client/models.py` — six `@property` aliases on
  `MarketDataSnapshot` plus a class-docstring paragraph recording the three facts a future reader
  needs (views only; `OP` excluded as a bare scalar; one class = both surfaces, hence no
  `ws_client.py` change).
- `packages/matriz-client/tests/test_null_object.py` — eight new cases, two module-level payload
  fixtures (`_REST_MARKET_DATA`, `_WS_FRAME`), three name-set constants, a new module-docstring point
  6, and the raised roster floor with its provenance.

## Decisions Made

See `key-decisions` in the frontmatter. The two worth restating: the decision id was **changed** from
the template's rather than copied (matriz's `D-03` means something else in this phase), and the
disjointness rationale was **rewritten** rather than copied (no `slots` here, so a collision is silent
rather than loud).

## Deviations from Plan

None in behaviour — both tasks ran as written, and no Rule 1-3 auto-fix was required. Two recording
notes:

**1. The plan's `read_first` line numbers were stale.** Same drift 37-03-SUMMARY recorded. The plan
cited `models.py:400-441` for the market-data models and `:508-516` for `MarketDataFrame`; they are
actually at `:537-578` and `:772-779`. The referenced content was located by symbol instead. Nothing
about the plan's intent changed.

**2. Two of the eight new tests passed at RED, on purpose.** `test_the_six_alias_names_..._disjoint`
and `test_the_six_aliases_are_invisible_on_the_real_snapshot_class` pin invariants that must
**survive** the change, not new behaviour: with zero properties on the class both hold trivially, and
their job is to still hold with six. The RED measurement was **7 failed, 67 passed** on the module,
plus 26 `attr-defined` mypy errors, all behavioural — the aliases are reached through attribute access
inside test bodies, never at import time, so the suite still collected.

## Known Stubs

None. No placeholder, hardcoded empty, TODO or FIXME was introduced. The `[]` and empty-model returns
are the documented Null Object contract, not stubs — they are what T-37-23 requires.

## Threat Flags

None. This plan introduced no network endpoint, auth path, file access pattern or schema at a trust
boundary. All six register dispositions were honoured:

- **T-37-23 (mitigate)** — `MarketDataSnapshot.empty()` answers all six aliases; the full WS chain
  `MarketDataFrame.empty().marketData.last.price` answers `None`. Locked by two tests, including the
  `from_api(None)` and `from_api({"type": "Md"})` variants.
- **T-37-24 (mitigate)** — disjointness asserted against the exact fourteen-name wire roster, with the
  name-shadowing rationale written out because matriz has no `slots` to fail loudly.
- **T-37-25 (mitigate)** — the aliases are absent from `get_type_hints` and `dataclasses.fields`
  (`14 set() set()`); the Phase 35 proof was cited and left byte-unmodified.
- **T-37-26 (mitigate)** — `ws_client.py` not edited; the connect-time decode-mode snapshot and the
  per-frame bound context are untouched, and `test_ws_client.py` + `test_ws_decode_mode.py` were run
  as acceptance (**35 passed**) rather than assumed green.
- **T-37-27 (mitigate)** — every alias is a single return; identity is asserted with `is` on both a
  REST-parsed and a WS-frame-parsed instance.
- **T-37-SC (accept)** — zero packages installed; `uv.lock` untouched.

## Verification Results — the phase's closing sweep

| Check | Result | Criterion |
|-------|--------|-----------|
| `pytest packages/matriz-client/tests -q` | **556 passed** | 547 baseline → strictly greater ✓ |
| `pytest test_null_object.py -q` | **74 passed** | ✓ |
| `pytest test_null_object.py -k alias -q` | **11 passed**, 63 deselected | 2 before → strictly more ✓ |
| the two invisibility tests, by nodeid | **2 passed** | and unmodified in `git diff` ✓ |
| `pytest test_ws_client.py test_ws_decode_mode.py -q` | **35 passed** | daemon-thread + per-connection/per-frame decode-mode propagation, SC-4 ✓ |
| `pytest -k "InstrumentPositionReport or DetailedAccountReport or TickPriceRange"` | **9 passed** | 3 classes × 3 contract cases; `_perturb` did not raise ✓ |
| `mypy packages/matriz-client/src` | Success — 17 source files | typed half of SC-3 ✓ |
| `mypy packages/matriz-client/tests/test_null_object.py` | Success — 1 source file | pre-commit runs mypy over tests too ✓ |
| `ruff check .` / `ruff format --check .` | All checks passed / already formatted | ✓ |
| `_safemodel_classes()` in-process | **20** | equals the raised floor and 37-03-SUMMARY ✓ |
| `tools/check_surface_types.py` | 442 fields scanned, **0 violations** | 37-04's extended gate still green ✓ |
| `tools/check_decode_intactness.py` | Checks A–D green | ✓ |
| `tools/check_uniform_structure.py` | all 6 packages OK | ✓ |
| `tools/surface_parity.py` | OK | ✓ |
| `pytest verification/test_main_market_data_deep_chain.py test_safemodel_diff_null_object_links.py` | **14 passed** | the two guards the `lint` job runs explicitly ✓ |
| `pytest verification/test_public_surface.py` | **4 passed** | ✓ |
| `regen_snapshots.py` re-run | **no diff** | aliases invisible to the recorded public surface ✓ |
| `ambito-financiero-client` suite | **208 passed**, 1 deselected | ✓ |
| `higyrus-client` suite | **289 passed** | ✓ |
| `iol-client` suite | **289 passed** | ✓ |
| `market-data-client` suite | **711 passed** | ✓ |
| `matriz-client` suite | **556 passed** | ✓ |
| `wallets-client` suite | **10 passed** | ✓ |
| **all six package suites** | **2063 passed** | no cross-package regression ✓ |
| `S.empty()` alias chain | prints `[] [] None None None None` | T-37-23 ✓ |
| `F.empty().marketData.last.price` | prints `None` | T-37-23 through the WS chain ✓ |
| `len(fields), fields & aliases, hints & aliases` | prints `14 set() set()` | T-37-24 / T-37-25 ✓ |
| `git diff --numstat` on `ws_client.py`, `_decode.py`, `client.py`, `aio.py` **across the whole phase** (`00ffb2f~1..HEAD`) | **empty** | byte-unchanged, F-12 + D-NO-06 ✓ |
| `git diff --name-only` for this plan | `models.py`, `test_null_object.py` only | ✓ |
| `ROADMAP.md` | not modified | orchestrator owns that write ✓ |

## Success Criteria

- [x] `snapshot.last`, `.bids`, `.offers`, `.settlement`, `.close`, `.open_interest` work identically
      on a REST-parsed and on a WS-frame-parsed `MarketDataSnapshot` — same class, same six names,
      identity-equal targets on both.
- [x] `mypy --strict` clean over `packages/matriz-client/src` (and over the touched test module).
- [x] The matriz suite is green on the REST paths and on the WebSocket daemon-thread paths, including
      per-connection and per-frame decode-mode propagation.
- [x] The roster floor equals the measured class count (20) and carries a stated provenance.
- [x] `ws_client.py` untouched; the aliases remain invisible to the walker with no divergence-count
      delta and no rewrite of the invisibility proof.

## Next Phase Readiness

**`NOBJ-MTZ-02` is complete**, and with 37-01…37-04 already landed, Phase 37's requirement set
(`NOBJ-MTZ-01`, `NOBJ-MTZ-02`) is closed on the typed-surface side.

**What Phase 39 / `LIVE-NOBJ-01` needs from this plan:** everything above was verified against
**fixtures and the vendor doc, never against the live API**. `D-MATZ-33`'s remarkets-hostname assert
in `main_matriz.py` was not bypassed and no live run was attempted. Specifically **not** verifiable
here:

- that the live `/marketdata` REST body and the live `type == "Md"` WS frame carry the entry shapes
  the fixtures use (in particular that `CL` really is an object and `OP` really is a bare scalar on
  the wire today — the exclusion decision rests on that);
- the two unobserved Risk rosters inherited from 37-03 (ledger `F-11` / `F-12`).

**Carried forward, unchanged:** `DetailedPosition.lastCalculation` is still annotated `str | None`
while the wire carries an epoch `int` (open since 37-01; `models.py` was in scope here but that field
is not this plan's target and was deliberately not touched). Worth a disposition in the Phase 38
audit.

## Self-Check: PASSED

Both claimed files exist on disk, plus this summary. All three claimed commit hashes resolve in
`git log`. Both `must_haves.artifacts` `contains` probes hold (`models.py` ⊃ `def open_interest`;
`test_null_object.py` ⊃ `open_interest`). Both `must_haves.key_links` patterns match at the expected
multiplicity: `return self\.(BI|OF|LA|SE|CL|OI)` → **6** in `models.py`, and `MarketDataFrame\.from_api`
→ **6** in `test_null_object.py`. `ROADMAP.md` is unmodified.

## TDD Gate Compliance

One full RED → GREEN pair for the single behaviour-adding task, in order:

- **RED** `4193dd2` (`test(...)`) — measured **7 failed, 67 passed** plus 26 `attr-defined` mypy
  errors, all behavioural rather than collection errors. Two of the eight new cases passed at RED on
  purpose (disjointness and real-class invisibility pin invariants that must *survive*, not new
  behaviour); this is recorded under Deviations rather than hidden.
- **GREEN** `65bd7c0` (`feat(...)`) — **74 passed** in the module, **556** in the matriz suite, mypy
  clean over both `src` and the touched test module.
- **No REFACTOR** commit — the implementation landed in final shape; a REFACTOR commit with no
  changes would have been noise.

Task 2 (`0b4505b`) is a test-only floor raise with no behaviour, correctly carrying no `tdd="true"` in
the plan and therefore no RED gate. No test was deleted or weakened, and the two Phase 35 invisibility
tests plus their fixtures are byte-unmodified.

---
*Phase: 37-matriz-client-dicts-residuales-tipados-alias*
*Completed: 2026-08-29*
