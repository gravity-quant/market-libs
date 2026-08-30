---
phase: 36-market-data-client-market-data-tipado-revocacion-de-la-fase-33
fixed_at: 2026-08-29T00:00:00Z
review_path: .planning/phases/36-market-data-client-market-data-tipado-revocaci-n-de-la-fase-/36-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 36: Code Review Fix Report

**Fixed at:** 2026-08-29
**Source review:** `.planning/phases/36-market-data-client-market-data-tipado-revocaci-n-de-la-fase-/36-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (2 critical, 6 warning; `fix_scope = critical_warning`)
- Fixed: 8
- Skipped: 0

Two of the eight (WR-02, WR-04) were fixed with a **different mechanism than the
review proposed**, because every remedy it listed collided with a signed decision
or a structural gate of this repo. Both are called out below with the collision
named. One finding (CR-02) is fixed as a *guard* correction and carries an
explicit deferred item for the shape change it uncovered — see the caveat at the
end.

**Verification run after the last fix (all green):**

| Gate | Result |
|---|---|
| `ruff check .` / `ruff format --check .` | pass (263 files) |
| `mypy` (src global, strict) | pass (75 files) |
| `mypy packages/*/tests` (6 paquetes) | pass |
| `pytest packages/market-data-client` | 711 passed |
| `pytest` other 5 paquetes | 289 / 10 / 488 / 289 / 208 passed |
| `lint-imports` | 5 contracts kept, 0 broken |
| `check_decode_intactness.py` | pass — digest `a1f00c824348164c` UNCHANGED |
| `check_uniform_structure.py` | pass |
| `check_surface_types.py` | pass |
| `pre-commit run` over the diff | all hooks pass |

The decode digest not moving is the load-bearing negative result: none of these
fixes touched `_decode.py` in any of the five paquetes.

## Fixed Issues

### CR-01: SHAPE-diff fabricated `model-only` findings for the six non-optional Null Object links

**Files modified:** `verification/safemodel_diff.py`, `verification/test_safemodel_diff_null_object_links.py` (new)
**Commit:** `da3bf2f`

`diff_safemodel_bidirectional` now skips direction A for a non-optional field
whose declared type is a nested SafeModel-like or `list[SafeModel-like]` — the
LINK/LEAF rule the walker already applies. The fix is in the differ, not in the
driver's suppression sets, exactly as the review argued: those sets are key-based
and path-agnostic and would have started suppressing a genuine `BI` omission on
any other model.

Reproduced before the fix and confirmed gone after: the row carrying only `LA`
under `market_data` yielded five `model-only` tuples (`BI`, `CL`, `OF`, `OI`,
`SE` at path `.market_data`) and now yields none.

The new module carries the falsification half of every claim — an absent scalar
LEAF is still reported, at the root and at depth — plus the driver-level
assertion the review asked for: `_emit_shape(partial_market_data_row,
MarketDataSnapshot, ...) == 0`, with `append_finding` monkeypatched so no test
can write the committed ledger, and a non-vacuity twin proving the driver did not
simply stop emitting.

### CR-02: the no-data-row fixtures did not match the baseline they cite

**Files modified:** `packages/market-data-client/tests/test_snapshot_no_data_row.py`, `packages/market-data-client/tests/test_market_data_chain.py`, `packages/market-data-client/src/market_data_client/models.py`, `36-DEFERRED-market-data-leaves.md` (new)
**Commit:** `b9884fb`

`_NO_DATA_ROW` is now `get-latest.json` verbatim — `market_id` and `active` back
to `null`, no `entries` key, `received_at: null` present. The consequences are
stated instead of hidden:

- `test_no_data_row_keeps_its_nulls` (+ async) keeps its load-bearing name (it
  anchors `F-72`/`73`/`75` and `F-92`/`93`/`95` in the append-only ledger) and now
  asserts `market_id == ""` / `active is False` as the manufactured typed zeros
  they are.
- The strict test is split into `..._links_are_never_fatal_under_strict_decode`
  (+ async), which isolates the LINKS on a row where only they are `null`, and
  `test_the_measured_no_data_row_still_raises_on_an_over_declared_leaf` (+ async),
  which pins `field_path == ".market_id"` so the raise is proven to come from a
  LEAF and never from `.market_data` / `.entries`.
- `test_a_wrong_typed_value_is_still_a_divergence` now builds on the links-only
  row and pins `.entries`. On the corrected baseline it would otherwise have gone
  green off the unrelated `.market_id` raise **without ever reaching `entries`** —
  a second instance of the same false-confidence pattern CR-02 names.
- `test_market_data_chain.py`: `_MD_NULL` is documented as the synthetic
  link-isolating row it actually is, and the MEASURED baseline row joins the
  module with `test_the_measured_no_data_row_is_the_committed_baseline_key_for_key`
  reading the JSON file and comparing key for key. A fixture can no longer drift
  from the baseline it claims to mirror without reddening — the root cause, not
  just this instance.
- A `non_strict_decode` fixture was needed for the two client-less tests:
  `Client.__init__` sets `_decode.STRICT_DECODE` without ever resetting the token,
  so the strict flag leaks across tests and a model-level decode would otherwise
  pass or fail on test ORDER.

### WR-01: the SC-5 structural lock never ran in CI

**Files modified:** `.github/workflows/ci.yml`
**Commit:** `d3cf04f`

Added as a `lint`-job step following the precedent of the three existing
cross-cutting gates, with the new CR-01 differ regression alongside the
deep-chain lock. Deliberately an explicit file list rather than
`pytest verification/`: that directory carries 23 pre-existing failures in
matriz / ámbito / higyrus (`deferred-items.md`, backlog `HARN-VERIF-01`) which
are out of this phase's scope and would redden the job for unrelated reasons.

### WR-02: the ten-key roster silently drops an eleventh key

**Files modified:** `packages/market-data-client/src/market_data_client/models.py`, `verification/test_safemodel_diff_null_object_links.py`
**Commit:** `40aec43`

**Fixed by a different mechanism than proposed** — all three suggested remedies
are blocked:

| Proposal | Blocker |
|---|---|
| Widen roster to matriz's 14 | Reverses D-02, a signed decision of the phase under review, and types four keys this paquete never measured (D-10 forbids retyping on another source's authority) |
| Captured-extras field + `unknown` property | Puts a `dict[str, Any]` back on a model that IS a nested field type — forbidden by `test_no_mapping_carrying_model_is_ever_a_nested_field_type` and by `check_surface_types.py` (Phase 32 GATE-TYP-01), and it is the mapping axis D-05 just retired |
| Promote `extra` INFO → WARNING | Means editing `_decode.py`, whose five copies are locked byte-identical by `check_decode_intactness.py`, reversing signed Phase 29 lock 3 across all six paquetes |

What *is* actionable: the review's premise that the drop is silent is incomplete
for this repo's pipeline. Verified empirically — the differ's direction B emits
`(".market_data", "wire-only", "IV")` for an undeclared key, and `_emit_shape`
writes it into the git-committed findings ledger the divergence census is
measured from. That detection path is now pinned by a test (so the CR-01
direction-A suppression cannot silently take direction B with it) and the
data-loss half plus its blocked mitigations are recorded at the declaration site.

### WR-03: stale cross-package contract in `matriz_client.models`

**Files modified:** `packages/matriz-client/src/matriz_client/models.py`, `.planning/milestones/v1.6-phases/29-decoder-observable/29-SEMANTICS-MATRIX.md`
**Commit:** `db4b9fa`

The `_mapping_value` docstring is amended to record the retirement, with an
explicit "do not re-create a copy over there to restore the symmetry" — the
failure mode a Phase 37 maintainer reading the old text would most plausibly
produce. The dangling `file:line` citation in `29-SEMANTICS-MATRIX.md` section
(d) is marked superseded **additively**, per that file's own convention, rather
than rewritten; the same note resolves its "Known consequence" paragraph, which
NOBJ-02 made obsolete.

### WR-04: `main` carries a second, source-incompatible `0.5.0`

**Files modified:** `packages/market-data-client/README.md`, `packages/market-data-client/src/market_data_client/__init__.py`
**Commit:** `c6563d0`

**Fixed by a different mechanism than proposed.** Neither suggested remedy is
available: a `0.6.0.dev0` marker requires regenerating `uv.lock`, and Phase 40's
SC-2 requires the global lock to be refreshed **exactly once** for all six
paquetes; a `CHANGELOG.md` would pre-empt the changelog format and migration
table Phase 40's SC-1 owns.

The marker is instead carried by the artifact itself — an
`## Unreleased — BREAKING` section at the top of the package README (which ships
as the wheel's long description) with the old→new migration table
(`market_data["LA"]["price"]` → `market_data.last.price`, `is None` → `not`, and
the two `entries` changes), plus a do-not-bump-here note at `__version__`
explaining why the deferral is deliberate and where the migration lives. The
README section also carries the CR-02 deferred divergence, so a consumer
installing from `main` sees it.

### WR-05: `chained={len(chained)}` could never differ from the row count

**Files modified:** `main_market_data.py`
**Commit:** `c3dda84`

Replaced with `with_last=` at all four sites via a shared `_with_last` helper
(the tuple index is named once as `_CHAINED_LAST_PRICE` rather than repeated raw
four times). That count is genuinely independent of the row count and answers the
question an operator reading a live-run artifact actually has: was the market
closed, or is the feed mute?

### WR-06: the batch decode path shipped unexercised while the guard reported it covered

**Files modified:** `main_market_data.py`, `verification/test_main_market_data_deep_chain.py`
**Commit:** `5cb3ee7`

Both `latest` probes now chain `batch` through the same six aliases, and the
detail carries `batch_with_last=`. The guard is strengthened past the review's
suggestion, which was to bump the aggregate floor: the aggregate is now *derived*
from a per-probe floor (12 for a two-collection probe, 6 otherwise), and a new
`test_every_fetched_snapshot_collection_is_chained` asserts the structural fact
rather than a count — every fetched collection must have some comprehension over
it carrying a `market_data.<alias>` dereference. A bare aggregate of 24 is
satisfiable by an 18/2/2/2 split, which is the same class of vacuity WR-06
reports.

Mutation-checked: deleting either `chained_batch` comprehension reddens all three
non-vacuity tests.

## Caveat — a real divergence uncovered by CR-02 and NOT fixed

`MarketDataSnapshot.market_id` (`str`) and `.active` (`bool`) are **over-declared**.
On the measured `get-latest.json` no-data row both arrive `null`, the walker
manufactures `""` / `False`, and `strict_decode` raises on `.market_id`. Both
halves of the union are measured (`str` / `bool` on the `/marketdata` baseline,
`NoneType` on the `/marketdata/latest` one), so under this repo's own option-b
nullability rule they QUALIFY for `| None`.

It is not fixed here on purpose: widening them is source-breaking on a published
read surface, and every prior shape change of that kind in this repo went through
a blocking operator checkpoint (33-07 Task 1 and 31-04 Task 1, both signed). A
code-review fixer taking that decision autonomously would bypass the governance
those checkpoints exist to enforce.

It is filed as
`.planning/phases/36-.../36-DEFERRED-market-data-leaves.md` with the measurement,
the recommended disposition, and the exact list of assertions that flip when the
operator widens — and it is asserted in the test suite today, so Phase 39 finds
it predicted instead of rediscovering it as a surprise. This is the "detectada,
documentada" half of the milestone's core value delivered in full, with
"corregida" queued behind the checkpoint that owns it.

---

_Fixed: 2026-08-29_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
