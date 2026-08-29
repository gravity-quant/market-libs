---
phase: 36
plan: 02
subsystem: market-data-client
tags: [models, null-objects, decode, revocation, tdd, nobj-md-01, nobj-md-02]
requires:
  - "market_data_client._decode.walk_field nested-model branch (NOBJ-02, Phase 35) — the null-collapses-silently policy this plan's non-optional links depend on"
  - "market_data_client._decode.hints_for"
  - "packages/market-data-client/tests/ with zero call sites into the mapping machinery (Plan 36-01)"
provides:
  - "BookLevel, EntryValue, MarketDataEntries + six read-only @property aliases, importable from the package barrel"
  - "MarketDataSnapshot.entries: list[str] and .market_data: MarketDataEntries — no None in either chain link"
  - "LatestRequest.entries: list[str] = field(default_factory=list) with absent-means-all preserved"
  - "models.py on form A of D-07 — the mapping machinery is gone from the paquete"
  - "packages/market-data-client/tests/test_market_data_chain.py — the SC-1 4x2 matrix + 8 edge probes"
affects:
  - "36-03 — the AST lock for the driver's deep chain now has a real shape to lock against"
  - "Phase 39 (LIVE-NOBJ-01) — the live run exercises this chain against develop; an eleventh market_data key arrives as a non-fatal `extra` to be corrected in-cycle there"
  - "Phase 40 (PUB-NOBJ-01) — three ADDITIVE public names + one SOURCE-BREAKING annotation change to absorb into the migration table"
tech-stack:
  added: []
  patterns:
    - "Null Object container with Null Object children (local copy of the matriz pattern, never an import — C-2 / D-NO-06)"
    - "read-only @property alias over a wire-named slot on a frozen+slots dataclass (invisible to get_type_hints, pinned by Phase 35 criterio 5)"
    - "non-vacuous absence lock: an absence assertion paired with positive structural assertions (33-07 criterio-4 precedent)"
key-files:
  created:
    - packages/market-data-client/tests/test_market_data_chain.py
  modified:
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/src/market_data_client/__init__.py
    - packages/market-data-client/tests/test_models.py
    - packages/market-data-client/tests/test_decode.py
    - packages/market-data-client/tests/test_snapshot_no_data_row.py
    - packages/market-data-client/tests/test_public_surface_market_data.py
decisions:
  - "The Phase 33 widening is revoked BY FIELD ROLE, additively: the two chain links go back to required, the two leaves keep | None, and the Phase 33 docstring block is kept rather than erased"
  - "A wrong-typed market_data changes divergence KIND (type -> non_dict) and ATTRIBUTION (MarketDataSnapshot -> MarketDataEntries) but NOT its disposition — still fatal under strict decode, now asserted rather than argued"
  - "The two no-data-row test names are load-bearing traceability anchors and were restored after the migration renamed them (deviation 2)"
  - "The three new names are re-exported from the package barrel and enrolled in _NEW_PUBLIC_NAMES, making the re-export enforced rather than recommended"
metrics:
  duration: ~55 min
  tasks: 3
  files: 7
  tests_before: 660
  tests_after: 707
  completed: 2026-08-29
status: complete
---

# Phase 36 Plan 02: `market_data` tipado + revocación parcial de la Fase 33 — Summary

`snapshot.market_data.last.price` is now real end to end: it type-checks under `mypy --strict` with
zero suppressions and returns a value or `None` — never raising — for all four payloads the vendor
can produce, on both the sync `Client` and the async `AsyncClient`.

## What was built

### Task 1 — the RED gate (`d5b31fa`, fixed up in `5334c5f`)

`packages/market-data-client/tests/test_market_data_chain.py`, 573 lines, 36 tests. Failed on
`ImportError: cannot import name 'BookLevel' from 'market_data_client'` — the right reason, and
the plan's own acceptance shape (it named `MarketDataEntries`; `BookLevel` simply sorts first in
the import block).

The 4×2 matrix is a real `pytest.mark.parametrize` over the four payloads, so a missing cell is
visible rather than inferable, and every row runs four times: sync, async, sync-strict,
async-strict. Every expected value is the one MEASURED in 36-RESEARCH F-1 / F-3 — asserted, not
recomputed. Eight edge probes cover roster boundary, alias adjacency, empty convergence, book and
`entries` ordering, `int`→`float` precision, `entries` emptiness, and the `LatestRequest`
empty-list boundary.

| Task 1 criterion | Result |
|---|---|
| RED for exactly one reason | `ImportError` naming the three new classes — not a syntax error, not a mock-plumbing error |
| `ruff check` on the new module | All checks passed |
| `grep -c 'Async twin'` ≥ 4 | **4** |
| `grep -c 'strict_decode=True'` ≥ 2 | **3** |
| Rest of the suite unmoved | **660 passed** — exactly the Plan 36-01 count |
| No real identifier | every symbol is `"AAA1"` / `"ZZZ"`, synthesised |

### Task 2 — the GREEN source change (`ee49e6c`)

One commit, two files, no logic invented — the phase is declarative plus a retirement.

**The three classes.** `BookLevel`, then `EntryValue`, then `MarketDataEntries`, placed immediately
before `MarketDataSnapshot` under a `# ---` section divider. All three are
`@dataclass(frozen=True, slots=True)` subclasses of the LOCAL `SafeModel` — matriz's decorator
(no `slots`) and base class were deliberately NOT copied, only the pattern (C-2 / D-NO-06). None
declares its own `from_api` or `empty`; that inheritance is what keeps WR-03's intersection empty.
Roster scoped to the ten keys the Phase 33 capture measured, not matriz's fourteen (D-02). Each
carries a live-capture provenance block in the `HealthAuth` idiom; `Health`'s "absent nested model
reports `missing`" sentence was deliberately not copied — it predates Phase 35, whose NOBJ-02
policy made that collapse silent.

**The six aliases.** `bids`→`BI`, `offers`→`OF`, `last`→`LA`, `settlement`→`SE`, `close`→`CL`,
`open_interest`→`OI`. Plain read-only `@property`, one return each, no setter, no caching (D-03
forbids it and `functools.cached_property` is impossible over `slots=True` anyway). The shape
reproduces `_AliasShaped`, which Phase 35 pinned.

**The revocation (D-04, D-08).** `entries: list[str]`, `market_data: MarketDataEntries`, both in
their existing positional slot and both still without a default, so `note` does not move. The
`MarketDataSnapshot` docstring gained a symmetric `REVOKED IN PART` block beneath the Phase 33
`BREAKING since 0.5.0` block — the earlier verdict is kept, not erased. It names the checkpoint
being revoked (33-07 Task 1, `fix-shape-now`) and the source plan
`.future_plans/api-tipada-null-objects.md`, and states the reason the revocation is safe: Phase 35's
NOBJ-02 landed in between, so a `null` on a non-optional link now collapses silently and the
`F-72`/`F-73`/`F-75` divergences that motivated the widening cannot come back.

**`LatestRequest` (D-06).** `entries: list[str] = field(default_factory=list)`; `to_dict`'s guard
becomes `if self.entries:`. The wire is unchanged — an empty list still omits the key, so
absent-means-all survives and the literal `{"entries": []}` never ships. `_core.build_latest_request`
was NOT touched: that is a different `entries` in a different layer (Pitfall 8).

**The retirement (D-05).** All four helpers and all three call sites deleted. `SafeModel.from_api`
and `SafeModel.empty` are form A now — take the sink, walk, construct. **The `received_at`
injection survived** (Pitfall 5): it sits one line below the deleted call and is asserted by three
separate tests. Imports: out `types`, `Union`, `get_args`, `get_origin`, `fields`; in `field`.

| Task 2 criterion | Result |
|---|---|
| chain matrix green in full | **36 passed** |
| `mypy packages/market-data-client/src` | Success: no issues found in 13 source files |
| `type: ignore` in `models.py` | **1 → 0** (the one lived inside the retired machinery) |
| non-vacuous machinery one-liner | prints `ok` |
| three names importable from the barrel | `MarketDataEntries`, `BookLevel`, `EntryValue` |
| alias/field disjointness one-liner | prints `ok` |
| `check_decode_intactness.py` | 5 copies → `a1f00c824348164c` == `CANONICAL_DIGEST` |
| `check_surface_types.py` | **0 violations** |
| `_core.py` / `_decode.py` / `client.py` / `aio.py` blobs | `295ce13c` / `5446832d` / `7724342d` / `c4a75c1d` — all four unchanged |
| `ruff check packages/market-data-client` | All checks passed |

### Task 3 — the migration census (`aef7585`, corrected in `3f6d5ca`)

Every test here reddened because its SUBJECT changed, not because the code was wrong, so every one
was migrated to the property it still protects. **None was deleted.**

| File | What moved |
|------|-----------|
| `test_models.py` | three `entries is None` → `== []`, comments repointed from the widening to its revocation; the reconciled-wire row now reads `.market_data.bids[0].price == 1.0` and asks `open_interest` by truthiness; the no-data row asserts `== MarketDataEntries.empty()` with `staleness_seconds is None` LEFT ALONE; the field-set lock keeps its eight names and gains four hint assertions so a future re-widening reddens there; a third `LatestRequest` case pins the D-06 empty-list boundary; new `mapping_machinery` lock |
| `test_decode.py` | four surviving rows migrated; the wrong-typed row records the divergence-kind change AND asserts the strict raise; the lock-8 row keeps its measured record set and is retitled to name the terminal record |
| `test_snapshot_no_data_row.py` | migrated, not deleted (SC-4) — same **6** tests; module docstring records the by-field-role revocation; the populated row moved off its dict literal to `.bids[0].price == 10.0`; `wrong_typed` untouched and green |
| `test_public_surface_market_data.py` | a fifth batch appended to `_NEW_PUBLIC_NAMES` with the three names |

The `mapping_machinery` lock is deliberately non-vacuous. A bare `not hasattr(...)` would pass
against an empty module, so following the 33-07 criterio-4 precedent (a zero floor is declared by
structural property, never by `>= 0`) the absence sits beside **three** positive assertions: the
`received_at` injection still beats a decoy payload key, `MarketDataEntries` declares exactly its
ten-key roster, and the introspected `SafeModel` roster is exactly nineteen.

## Test count reconciliation

**660 → 707.** Every one of the 47 is accounted for:

| Source | Δ |
|--------|---|
| `test_market_data_chain.py` (new module) | +36 |
| `test_models.py`: `LatestRequest` empty-list boundary + `mapping_machinery` lock | +2 |
| `test_null_object.py`: roster **16 → 19** × 3 parametrized tests, **with no edit to that file** | +9 |

The roster growth is the non-event Plan 36-01's handoff note and RESEARCH Open Question 3 both
predicted. `test_the_model_roster_is_not_vacuous`'s `>= 16` bound held without editing, and WR-03's
computed `nested_types` grew by the three new names while its verdict
(`overriding & nested_types == set()`) stayed identical.

## Recorded for downstream phases

- **The divergence-kind change.** A wrong-typed `market_data` used to report `("MarketDataSnapshot",
  ".market_data", "type")` via the retired `_mapping_value`; it now reports `("MarketDataEntries",
  ".market_data", "non_dict")` via the walker's nested-model branch. **The disposition is
  unchanged** — `non_dict` is not in `_INFO_KINDS`, so it is still fatal under `strict_decode`, and
  `test_decode.py::test_wrong_typed_market_data_reports_non_dict_against_the_container` now asserts
  that raise instead of arguing it in prose. Phase 39's census must expect the new
  `(model, field_path, kind)` triple for this case.
- **The `SafeModel` roster moved 16 → 19** (`BookLevel`, `EntryValue`, `MarketDataEntries`).
- **This paquete moved from form B to form A of D-07.** `29-SEMANTICS-MATRIX.md`'s market-data row
  is now the same shape as the form-A paquetes. This is a per-paquete policy axis, not a
  convergence to replicate: the form-B paquetes keep their pass, and a form-A paquete must not grow
  a no-op one to look identical. `models.py`'s module docstring and `SafeModel.empty`'s docstring
  both say so explicitly, replacing prose that described a pass which no longer exists (Pitfall 4).
- **Semver consequence for Phase 40 (`PUB-NOBJ-01`)**, two-part and NOT purely additive:
  - **ADDITIVE:** three new public names — `BookLevel`, `EntryValue`, `MarketDataEntries` — in both
    `models.__all__` and the package `__all__`.
  - **SOURCE-BREAKING:** `MarketDataSnapshot.market_data` changes from `dict[str, Any] | None` to
    `MarketDataEntries`, so every consumer subscript (`md["BI"][0]["price"]`) must become an
    attribute chain (`md.bids[0].price`) — and the value widens `int` → `float` in the process.
    `MarketDataSnapshot.entries` and `LatestRequest.entries` stop admitting `None`. The migration
    table wants a vieja→nueva row per accessor. **No bump was made here** (D-09): `pyproject.toml`
    is still `cfb60655` and `uv.lock` still `5c8ea46c`, both unchanged.
- **`_ENDPOINT_OPTIONAL` was not touched**, per RESEARCH Pitfall 7's measured answer — `entries` must
  stay in the frozenset or the Phase 39 driver emits a false `model-only entries` finding on every
  `/marketdata/latest` run.

## Verification

| Check | Result |
|-------|--------|
| `uv run pytest packages/market-data-client -q` | **707 passed** in 1.03 s |
| `uv run mypy packages/market-data-client/src` | Success: no issues found in 13 source files |
| `uv run mypy packages/market-data-client/tests` | Success: no issues found in 36 source files |
| `uv run ruff check packages/market-data-client` | All checks passed |
| `uv run ruff format --check packages/market-data-client` | 49 files already formatted |
| `uv run python tools/check_decode_intactness.py` | Checks A–D pass; digest `a1f00c824348164c` == `CANONICAL_DIGEST` (SC-5's "sin mover el hash") |
| `uv run python tools/check_surface_types.py` | 0 violations |
| `uv run python tools/check_uniform_structure.py` | clean, all 6 packages |
| `-k mapping_machinery` | 1 passed, and its body carries three positive structural assertions |
| `-k wrong_typed` (no-data row) | 1 passed, unedited |
| `test_null_object.py` | **61 passed**, file unedited in this plan |
| `test_public_surface_market_data.py` | 6 passed |
| `git diff --stat -- .planning/verification/schemas/market-data-client/` | **empty** (Pitfall 9 / T-36-02-04) |
| `pyproject.toml` / `uv.lock` blobs | `cfb60655…` / `5c8ea46c…` — unchanged (D-09 / T-36-02-SC) |
| `verification/test_cycle_closure_market_data.py` + the `market-data-client` arm of `test_cycle_closure_phase33.py` | green after `3f6d5ca` (see deviation 2) |
| repo-root `verification/` market-data modules | 11 passed |
| whole-workspace `uv run pytest -q` | 2376 passed; the 23 failures + 19 errors are ALL in `verification/` and none is market-data — see `deferred-items.md` |

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 — Bug] The `entries` edge probe used partial payloads, so its record-set assertion could not hold**

- **Found during:** Task 2, when the module first turned green everywhere else
- **Issue:** The four `entries` cases in the Task 1 module were written as minimal payloads
  (`{}`, `{"entries": None}`, …). Every omitted declared field emits its own `missing` record, so
  the probe's `_records(caplog) == expected_records` assertion saw four extra records and failed —
  a defect in the test I authored in Task 1, not in the source.
- **Fix:** Varied ONLY `entries` over a complete row (`_ENTRIES_BASE`). The record-set assertion
  stays GLOBAL rather than being weakened to a path filter, which is the stronger of the two ways
  out.
- **Files modified:** `packages/market-data-client/tests/test_market_data_chain.py`
- **Commit:** `5334c5f`

**2. [Rule 1 — Bug / false-clean signal] Renaming the two no-data-row tests orphaned six live findings**

- **Found during:** post-Task-3 wider-gate run (`uv run pytest verification -q`)
- **Issue:** Task 3's migration renamed `test_no_data_row_keeps_its_nulls` / `_async` to
  `..._keeps_its_full_expressive_power`, on the reading that "keeps its nulls" no longer described
  what the test asserts. Those two names are the `Regression:` anchors of findings `F-72`/`F-73`/
  `F-75` and `F-92`/`F-93`/`F-95` in the **append-only** ledger
  `.planning/verification/market-data-client-findings.md`, and
  `verification/test_cycle_closure_market_data.py` resolves each bullet to a real `def <test>(`.
  The rename turned six CONFIRMED findings into dangling links and reddened both the market-data
  cycle-closure gate and the `market-data-client` arm of `test_cycle_closure_phase33.py` — a
  false-clean of precisely the kind this project exists to eliminate.
- **Fix:** Restored both names. SC-4 asked for the ASSERTIONS to be migrated and never for a
  rename, and the alternative — editing the append-only ledger — would have reached outside the
  plan's seven declared files to repair damage the plan never asked for. Both docstrings now record
  that the name is a load-bearing traceability anchor, and spell out what "keeps its nulls" means
  after the revocation: the leaf keeps its `None`, the two links say the same thing through
  emptiness, and no substitution was ever manufactured for any of the three.
- **Files modified:** `packages/market-data-client/tests/test_snapshot_no_data_row.py`
- **Commit:** `3f6d5ca`
- **Verified:** both cycle-closure checks green; `F-72`…`F-95` resolve again.

### Notes, not deviations

**3. The RED failure named `BookLevel`, not `MarketDataEntries`.** Task 1's acceptance criterion
asked for an `ImportError` / `AttributeError` "naming `MarketDataEntries`". The actual failure was
`ImportError: cannot import name 'BookLevel'` — the same import statement, the same three missing
classes; Python simply reports the first name in the block and the block is alphabetical. The
criterion's intent (a comprehensible import failure, not a syntax or mock-plumbing error) was met.

**4. `test_null_object.py::test_empty_and_from_api_agree_on_every_mapping_declared_field` is now
green but no longer means what it says.** Its subject — the one shipped class declaring a
mapping-typed field — no longer exists, so it compares `MarketDataEntries.empty()` against itself.
RESEARCH flagged it for retitling or retirement, but this plan's acceptance criteria require
`test_null_object.py` to pass **with no edit to that file**, and its `<files>` list excludes it.
Left untouched deliberately; **flagged for Plan 36-03 or a follow-up**. The module docstring of that
same file also still declares this paquete's membership in form B (lines 21-24), which is now false.

### Scope discipline

`git diff --stat d2bdd28..HEAD` reports exactly the seven files this plan declares. `_decode.py`,
`_core.py`, `client.py`, `aio.py`, `pyproject.toml`, `__version__`, `uv.lock`, `README.md` and
everything under `.planning/verification/schemas/` were not touched — all verified by blob hash or
by an empty `git diff --stat`, not by inspection.

## Known Stubs

None. No hardcoded empty value flows to a consumer, no placeholder text, no unwired data source.
The empty values this plan introduces (`MarketDataEntries.empty()`, `[]`) are the Null Object
semantics the requirement asks for, not stubs: each is reachable, typed, asserted, and produced by
the shipped walker rather than hardcoded at a call site.

## Threat Flags

None. No new network endpoint, no auth path, no file access pattern, no schema change at a trust
boundary. The register's dispositions held:

- **T-36-02-01** (info disclosure via new nested divergence paths) — mitigated. `models.py` adds
  **zero** calls to the sink; the new paths are DECLARED field names, never payload content.
- **T-36-02-02** (hostile wire key forging a log line) — mitigated. `_decode.py` is unmodified, so
  `_safe_key` (lock 11) is intact by the digest gate, and the eleventh-key path is exercised
  explicitly, including under `strict_decode=True`.
- **T-36-02-04** (a lossy `to_dict()` overwriting a wire baseline) — mitigated.
  `git diff --stat -- .planning/verification/schemas/market-data-client/` is empty.
- **T-36-02-SC** (supply chain) — accepted; this plan installs nothing and both pinned blobs are
  unchanged.

The boundary was **strengthened**, which is the security half of the phase: `market_data` moved from
an unvalidated `dict[str, Any]` passthrough to ten declared, type-checked fields — without one line
of new validation code.

## Self-Check: PASSED

- `packages/market-data-client/tests/test_market_data_chain.py` — FOUND (573 lines, contains
  `MarketDataEntries`)
- `packages/market-data-client/src/market_data_client/models.py` — FOUND, contains
  `class MarketDataEntries(SafeModel)`
- `packages/market-data-client/src/market_data_client/__init__.py` — FOUND, contains
  `MarketDataEntries`
- `packages/market-data-client/tests/test_models.py` — FOUND, contains `mapping_machinery`
- `packages/market-data-client/tests/test_snapshot_no_data_row.py` — FOUND, contains
  `bool(row.market_data)`
- Commits `d5b31fa`, `5334c5f`, `ee49e6c`, `aef7585`, `3f6d5ca` — all FOUND in `git log`
