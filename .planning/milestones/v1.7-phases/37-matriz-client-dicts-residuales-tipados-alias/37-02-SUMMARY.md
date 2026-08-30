---
phase: 37
plan: 02
subsystem: matriz-client models / decode call-site axis
tags: [mapping-axis, element-typing, recursion, null-object, provenance, baseline, tdd, d-05, d-06]
status: complete

requires:
  - "matriz_client._decode.walk_field (Phase 29) — the byte-verbatim shared walker, untouched"
  - "matriz_client._decode.DecodeScope / SILENT_SINK (Phase 29) — the sink the axis must be HANDED"
  - "matriz_client._decode._safe_key (Phase 29 CR-04, lock 11) — key neutralization, reused not re-implemented"
  - "_SafeModel.empty / __bool__ (Phase 35 NOBJ-01) — inherited by TickPriceRange for free"
  - "37-01 — the Risk envelope unwrap (indirect precondition, RESEARCH Pitfall 1)"
provides:
  - "An element-typed, self-recursing mapping axis in matriz_client.models — the mechanism 37-03 calls with a two-level hint"
  - "_element_hint() — the shared derivation of a dict[...] annotation's VALUE type"
  - "TickPriceRange, the phase's only model with real live-capture provenance"
  - "InstrumentDetail.tickPriceRanges: dict[str, TickPriceRange] — 1 of the 4 target retypes closed"
  - "The provenance-docstring FORM (class `baseline`) that 37-03 mirrors with class `vendor-documented, unmeasured`"
  - "A regenerated public-surface snapshot recording both changes"
affects:
  - "37-03 — calls _mapping_value with a two-level hint; the verbatim signature is recorded below so it need not guess"
  - "37-04 — TickPriceRange is on __all__, so the new field gate can resolve it; one of the 5 dict[str, Any] sites is now gone"
  - "37-05 — no interaction (MarketDataSnapshot untouched)"

tech-stack:
  added: []
  patterns:
    - "Call-site decode axis: the per-package normalization lives in models.py, the shared walker stays byte-verbatim (29-SEMANTICS-MATRIX Section 3)"
    - "Route through walk_field with the sink in hand — never Model.from_api, which resolves its own sink and escapes the scope"
    - "Provenance docstring citing the committed capture file + capture date + environment (Phase 36 BookLevel form)"
    - "Closed roster + non-fatal `extra` divergence reporting for a partially observed payload"
    - "TDD RED/GREEN as separate commits, one pair per task"

key-files:
  created: []
  modified:
    - packages/matriz-client/src/matriz_client/models.py
    - packages/matriz-client/src/matriz_client/__init__.py
    - packages/matriz-client/tests/test_decode.py
    - packages/matriz-client/tests/test_models.py
    - verification/snapshots/matriz-client-surface.txt

decisions:
  - "The axis mirrors walk_field's own (value, hint, *, path, model, sink) shape — element is the 2nd POSITIONAL parameter, not keyword-only"
  - "Payload-supplied mapping keys are neutralized with _decode._safe_key before entering field_path (lock 11 extended to the axis)"
  - "F-11's blind spot answered with option (a): every Phase 37 inner model is kept mapping-free; the __args__ walk is NOT deepened"
  - "test_logging.py needed no edit — its assertion survived the retype unchanged"

metrics:
  duration: ~11 min
  completed: 2026-08-29
  tasks: 2
  commits: 4
  files_changed: 5
  tests: 493 → 510
---

# Phase 37 Plan 02: The tracer slice — element-typed mapping axis + `TickPriceRange` Summary

`InstrumentDetail.tickPriceRanges` now returns a mapping of `TickPriceRange` models decoded
through the shared walker, and the axis that decodes it recurses — so Plan 37-03's two-level
`report` field has a mechanism to land on that was proven against real captured data first.

## The axis signature, verbatim

Plan 37-03 calls this with a two-level hint and must not guess the parameter names.

```python
def _element_hint(tp: Any) -> Any: ...


def _mapping_value(
    value: Any,
    element: Any,
    *,
    path: str,
    model: str,
    sink: _decode.DecodeScope,
) -> Any: ...


def _apply_mapping_policy(
    cls: type[Any], kwargs: dict[str, Any], *, sink: _decode.DecodeScope
) -> None: ...   # unchanged signature — it derives `element` internally


def _convert(tp: Any, value: Any) -> Any: ...   # unchanged, reversed order preserved
```

`element` is the **second positional** parameter, deliberately mirroring
`_decode.walk_field(value, hint, *, path, model, policy, sink)` so the pairing of the two is
visible at every call site. `_apply_mapping_policy` and `_convert` both keep their existing
signatures; they derive the element hint via `_element_hint(...)` and pass it down.

**37-03 needs to do nothing to the axis.** Declaring
`report: dict[str, dict[str, InstrumentPositionReport]]` is sufficient — `_apply_mapping_policy`
derives `dict[str, InstrumentPositionReport]` as the element, `_mapping_value` sees
`_is_mapping(element)` and self-recurses. The recursion is already tested at depth 2 by
`test_typed_mapping_recurses_on_a_nested_mapping_hint`.

## What Was Built

### Task 1 — the axis (commits `44b6d66` RED → `8fe5f8c` GREEN)

**RED (`44b6d66`)** — 10 cases added, **6 correctly failing**, 4 passing on purpose:

| Case | Asserts | RED? |
|------|---------|------|
| `test_typed_mapping_values_decode_into_models` | `dict[str, Model]` yields model instances; `int`→`float` widened silently; zero divergences | ✗ fail |
| `test_typed_mapping_recurses_on_a_nested_mapping_hint` | `dict[str, dict[str, Model]]` decodes to models at depth 2 | ✗ fail |
| `test_nested_mapping_divergence_path_reads_through_both_keys` | path `.report.OUTER.0.tick` | ✗ fail |
| `test_the_axis_emits_through_the_sink_it_was_handed` | T-37-10 — handed `SILENT_SINK` under a bound EMITTING scope, emits nothing | ✗ fail |
| `test_typed_mapping_dedupes_within_one_scope` | lock 5 still collapses the second decode | ✗ fail |
| `test_convert_shim_inherits_the_element_routing` | F-17 — the shim gets the routing, not a bypass | ✗ fail |
| `test_the_axis_helpers_never_reference_current_sink` | AST: `current_sink` appears exactly once, inside `from_api` | ✓ pin |
| `test_non_dict_payload_on_a_mapping_carrier_emits_one_terminal_record` | lock 8 | ✓ pin |
| `test_typed_mapping_non_dict_value_still_substitutes_and_reports` | preserved container contract on a TYPED field | ✓ pin |
| `test_typed_mapping_non_dict_value_is_fatal_under_strict_mode` | strict mode still fatal on that record | ✓ pin |

The four passing cases are correct as RED: they pin contracts that must **survive** the rewrite,
not new behaviour. The sink-identity pair is the discriminating design — the AST test states
T-37-10 structurally, and the runtime test hands the axis `SILENT_SINK` *while a bound emitting
scope exists*, so an axis that reached for `current_sink()` would be caught by an actually
emitted record rather than by a source grep alone.

Fixtures are module-local synthetics (`_TickLike`, `_TypedMapping`, `_NestedMapping`) so a
shipped-model field change cannot turn an axis regression green.

**GREEN (`8fe5f8c`)** — three changes in `models.py`:

1. **`_element_hint(tp)`** — `get_args(_strip_optional(tp))[1]`, or `Any` when unparameterised.
   Reuses `_strip_optional` rather than re-deriving Optional handling, so it normalizes exactly
   as `_is_mapping` does.
2. **`_mapping_value`** — non-dict branch **behaviourally byte-equivalent** (same five-argument
   sink call, same `missing`/`type` discrimination, same `{}` return); dict branch rebuilt as a
   loop that either self-recurses (`_is_mapping(element)`) or delegates to `_decode.walk_field`
   with the element hint, the extended path, the same model name and the same sink.
3. **`_apply_mapping_policy` / `_convert`** — derive and forward the element hint.

The untyped case needs no special casing: `Any` reaches `walk_field`'s bare pass-through and the
value is returned verbatim, which is both correct for a legacy `dict[str, Any]` and what keeps
`test_convert_shim_still_coerces` green.

**Docstring history carried forward, not dropped.** The Phase 29 CR-03 paragraph, the Phase 36
WR-03 paragraph (including its "do not re-create the copy in market-data" instruction — `grep
'Phase 36'` still matches at two sites), and the "why the axis lives in `models.py`" explanation
all survive verbatim. One Phase 37 paragraph appended, recording that the axis now also OWNS
element decoding and that the recursion exists for 37-03's `report`.

### Task 2 — `TickPriceRange` (commits `2e77611` RED → `8572523` GREEN)

**RED (`2e77611`)** — 4 cases, all failing behaviourally rather than at collection time (the new
symbol is reached through `matriz_client.TickPriceRange` **inside** test bodies, so the suite
still collects and the failures are real assertions, not an `ImportError`):

| Case | Asserts |
|------|---------|
| `test_instrument_detail_tickPriceRanges_decodes_the_committed_baseline` | one key `"0"`; value is not a dict; `lowerLimit == 0.0` and is a `float`; `tick == 0.1`; `upperLimit is None` |
| `test_tickPriceRanges_values_are_TickPriceRange_null_objects` | T-37-06 — `empty()` falsy, populated truthy, the caller's chain over an absent mapping never raises |
| `test_TickPriceRange_is_on_the_exported_surface` | in `matriz_client.__all__` and identical to `models.TickPriceRange` |
| `test_tickPriceRanges_undeclared_inner_key_is_one_non_fatal_extra` | T-37-08 — exactly one `extra` at `.tickPriceRanges.0.vendorNew`, model `TickPriceRange`, non-fatal under strict mode |

**GREEN (`8572523`)** — `TickPriceRange` added immediately before `InstrumentDetail`, matching
matriz's local house style: `@dataclass(frozen=True)` with **no** `slots=True`, base `_SafeModel`
(the private one, not market-data's public `SafeModel`), three `float | None = None` leaves.
`from_api` / `empty` / `__bool__` are all inherited; none is hand-written.

The field was retyped to `dict[str, TickPriceRange]` keeping `field(default_factory=dict)`, and
the class was added to both `models.__all__` and the package `__init__.py` (import block and
`__all__`, both alphabetical) — required because Plan 37-04's gate resolves candidates from
`__all__`, so an inner model absent from the surface would be invisible to its scan.

## Provenance — the tracer property

`TickPriceRange`'s docstring declares class **`baseline`** (D-04a, the first of the three
provenance classes) and cites:

- the file: `.planning/verification/schemas/matriz-client/get-instrument-detail.json`
- the capture date: `2026-06-10T01:01:55Z`
- the environment: `https://api.remarkets.primary.com.ar` (reMarkets), symbol `SOJ.ROS/NOV26 308 P`

The capture records exactly one key `"0"` carrying
`{"lowerLimit": "int", "tick": "float", "upperLimit": "NoneType"}`. The vendor doc samples at
`Primary-API.md:330,378,454` agree on all three names, on the single key and on the three runtime
types — and are **labelled vendor-documented corroboration, never presented as a capture**
(D-04a). The same distinction is repeated in the test file's provenance block, because that is
where the concrete VALUES (`0`, `null`, `0.1`) come from: the capture stores types, the vendor doc
stores values, and the summary of which is which travels with the payload.

The second docstring paragraph pre-empts the one "fix" a future reader would be tempted to make:
`lowerLimit` is `float | None` although the wire carries `int`, because `walk_field`'s float arm
widens **before** consulting `scalar_passthrough`, so the widening is silent and fabricates no
divergence. Retyping it to `int` would start reporting a divergence on every well-formed payload.
Identical reasoning to Phase 36's `BookLevel.price`; the form was copied, the content was not.

## Key Implementation Details

**Lock 11 extended to the axis (Rule 2 — security).** Mapping keys are payload content and they
now enter `field_path`. The walker already neutralizes an `extra` key with `_decode._safe_key`
for exactly this reason (a key carrying `\n` would forge a line in any text handler; a key
carrying `.` would forge a path segment and collide with a real decode site under lock 10). The
plan's action said only "append the key to the incoming path". Appending it raw would have opened
a log-injection hole the walker closes two functions away, so `_decode._safe_key` is reused —
importing the walker's own helper rather than re-implementing the regex, so the two cannot drift.
This is the one place the plan's letter was exceeded, and it is recorded as a deviation below.

**`_decode.py` byte-unchanged.** `git diff --numstat` on it is empty across all four commits, and
`check_decode_intactness.py` still reduces all five copies to `a1f00c824348164c`. The plan's first
prohibition holds exactly.

**`market_data_client/models.py` untouched.** The second prohibition — do not re-create the axis
over there to restore symmetry — holds; the file is not in the diff.

**`Model.from_api` never called from the axis.** Every element goes through
`_decode.walk_field(..., sink=sink)` with the caller's sink in hand. `current_sink` appears
exactly once in the whole of `models.py`, inside `_SafeModel.from_api`, and that is now asserted
structurally by an AST test rather than only by a grep in an acceptance criterion.

**`tickPriceRanges` stayed a mapping.** All three observed samples carry exactly one key `"0"`;
nothing observed proves contiguity or ordering, so flattening to `list[TickPriceRange]` would
assert a sequence property no evidence supports (D-05). The reason is recorded as a comment at
the field, not just in planning docs.

**The empty-mapping assertions did not flip.** `test_decode.py:467`, `:554` and `test_models.py:65`
all assert `tickPriceRanges == {}` on an absent payload, and all three are still TRUE after the
retype — the default factory is unchanged. Per the plan, only assertions whose truth changed were
touched; these were left alone, with one clarifying comment added at `test_models.py`.

**`test_logging.py` needed no edit at all.** Its sentinel payload sends a bare `str` where the
mapping is declared, which still takes the non-dict branch, still substitutes `{}` and still emits
a `type` record. It was listed in `files_modified` and in the Pitfall-4 hit list as a site to
CHECK; checking it showed nothing to change, and inventing an edit would have been noise.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing critical functionality] Payload-supplied mapping keys were not neutralized**

- **Found during:** Task 1, GREEN phase
- **Issue:** The plan's action specified "Compose the extended path by appending the key to the
  incoming path". Mapping keys are vendor-controlled wire content, and `field_path` is emitted
  into log records. The walker neutralizes `extra` keys with `_safe_key` for precisely this
  threat (lock 11 / Phase 29 CR-04) — a key carrying a newline forges a line in a text handler, a
  key carrying `.` forges a path segment. Raw interpolation would have opened a log-injection
  hole in the one new place where wire keys reach a record.
- **Fix:** `item_path = f"{path}.{_decode._safe_key(key)}"`, reusing the walker's own helper
  rather than re-implementing the regex, with the reasoning recorded in the docstring.
- **Files modified:** `packages/matriz-client/src/matriz_client/models.py`
- **Commit:** `8fe5f8c`
- **Note:** this reaches for an underscore-private of `_decode`. That is deliberate — a private
  copy in `models.py` could drift from the walker's, which is the failure mode lock 11 exists to
  prevent. `_decode.py` is not modified by this; it is read.

**2. [Rule 3 — Blocking] `-k tickPriceRange` collected zero tests**

- **Found during:** Task 2, acceptance-criteria check
- **Issue:** Task 2's criterion requires
  `pytest .../test_models.py -k tickPriceRange -q` to collect at least 1 test. My initial names
  were snake_case (`test_..._tick_price_ranges_...`), which `-k tickPriceRange` cannot match, so
  the criterion was unsatisfiable as written.
- **Fix:** renamed the four new tests to embed the wire/class name verbatim
  (`test_instrument_detail_tickPriceRanges_decodes_the_committed_baseline`,
  `test_tickPriceRanges_values_are_TickPriceRange_null_objects`,
  `test_TickPriceRange_is_on_the_exported_surface`,
  `test_tickPriceRanges_undeclared_inner_key_is_one_non_fatal_extra`). This is established house
  style, not an exception invented for the criterion:
  `test_null_object.py::test_UnknownFrame_is_falsy_when_empty` already embeds a class name
  verbatim, and pep8-naming (`N`) is not in the repo's ruff rule set. Now collects 3.
- **Commit:** `8572523`

**3. [Rule 2 — Missing critical functionality] Two stale module docstrings**

- **Found during:** Task 1, GREEN phase
- **Issue:** `models.py`'s and `test_decode.py`'s module docstrings both described the mapping
  axis as "a `dict`-declared field falls back to `{}`" — a complete description before this plan
  and an incomplete one after it, since the axis now also decodes elements. A docstring that
  under-describes a security-relevant decode path invites a maintainer to assume values are
  untouched.
- **Fix:** both updated to name the element decoding and the recursion, in the same commit as the
  code that falsified them (the 37-01 discipline).
- **Commit:** `8fe5f8c`

### Process Note — a `git stash` that should not have happened

While measuring the pre-change baseline count for one acceptance criterion I ran `git stash -u`,
which reverted the uncommitted Task 1 GREEN work. It was recovered in full by `git stash pop` in
the next command; the working tree was then re-verified (`503 passed`, mypy clean, ruff clean)
**before** the GREEN commit, so nothing was committed in a disturbed state and the commit contents
are unaffected. Recording it because it was avoidable — `git show <ref>:<path>` answers the same
question without touching the working tree, and it is the sanctioned alternative. No data was lost.

## Known Stubs

None. No placeholder, no hardcoded empty flowing to a caller, no TODO or FIXME introduced. The
`{}` returns in `_mapping_value` are the documented Null Object contract, not stubs.

## Threat Flags

None. This plan introduced no new network endpoint, auth path, file access pattern, or schema at a
trust boundary. The register's dispositions were honoured:

- **T-37-06 (mitigate)** — `TickPriceRange` inherits `empty()` / `__bool__`, all three fields are
  `float | None`, and a non-dict container still substitutes `{}`. Locked by
  `test_tickPriceRanges_values_are_TickPriceRange_null_objects`.
- **T-37-07 (mitigate)** — element values are now validated by `_decode.walk_field` against the
  declared hint instead of passing through unexamined; mismatches are reported through the sink.
- **T-37-08 (accept)** — the roster is closed at the three keys the capture shows; an undeclared
  inner key is discarded but reported as a non-fatal `extra`. Locked by
  `test_tickPriceRanges_undeclared_inner_key_is_one_non_fatal_extra`, which runs under
  `STRICT_DECODE = True` to prove non-fatality.
- **T-37-09 (mitigate)** — the `baseline` docstring cites file, date and environment, so the
  roster is re-derivable from committed evidence.
- **T-37-10 (mitigate)** — the axis emits only through the sink it was handed. Asserted twice:
  structurally (AST, `current_sink` occurs once and only inside `from_api`) and behaviourally
  (handed `SILENT_SINK` under a bound emitting scope, emits nothing).
- **T-37-SC (accept)** — zero packages installed; `uv.lock` untouched.

## Deferred / Follow-ups

- **F-11's depth-2 blind spot is answered by convention, not by the guard.**
  `test_no_mapping_carrying_model_is_ever_a_nested_field_type` walks one level of `__args__`, so a
  model nested at depth 2 — 37-03's `dict[str, dict[str, InstrumentPositionReport]]` — never
  enters `nested_types`. The phase's answer is F-11 option (a): every Phase 37 inner model is kept
  mapping-free, so no carrier can reach depth 2. This is now a **comment inside that test** rather
  than an unstated assumption, and it becomes load-bearing for 37-03: if `InstrumentPositionReport`
  or `DetailedAccountReport` ever gains a mapping field, the guard stays green while the axis
  silently skips it, and option (b) — deepening the walk — becomes mandatory.
- **`DetailedPosition.lastCalculation` type mismatch** (inherited from 37-01's follow-ups) is
  still open; `models.py` was in scope here but that field is not one of this plan's four targets.
- **No live verification.** `tickPriceRanges` has a committed capture, which is the strongest
  evidence available in this phase, but the D-MATZ-33 hostname assert was not bypassed and no new
  live run was attempted. Destination for real re-verification remains Phase 39 / `LIVE-NOBJ-01`.

## Verification Results

| Check | Result | Criterion |
|-------|--------|-----------|
| `pytest packages/matriz-client/tests -q` | **510 passed** | > 488 baseline ✓ (493 after 37-01) |
| `pytest packages -q` (whole repo) | **2017 passed**, 1 deselected | no cross-package regression |
| `pytest test_decode.py -k "mapping or convert" -q` | **15 passed** | strictly more than 7 before ✓ |
| `pytest test_models.py -k tickPriceRange -q` | **3 passed** | ≥ 1 ✓ |
| `mypy packages/matriz-client/src` | Success — 17 source files | ✓ |
| `grep -c 'type: ignore' models.py` | **1** | unchanged from before the task ✓ |
| `ruff check packages/matriz-client` | All checks passed | ✓ |
| `ruff format --check packages/matriz-client` | 43 files already formatted | ✓ |
| `tools/check_decode_intactness.py` | Checks A–D green; hash `a1f00c824348164c` | ✓ |
| `tools/check_surface_types.py` | 184 `__all__` names, **0 violations** | still green pre-37-04 ✓ |
| `tools/check_uniform_structure.py` | all 6 packages OK | ✓ |
| `tools/surface_parity.py` | OK | ✓ |
| `verification/test_main_market_data_deep_chain.py` + `test_safemodel_diff_null_object_links.py` | **14 passed** | the two guards the `lint` job runs ✓ |
| `git diff --numstat .../_decode.py` | empty | byte-unchanged ✓ |
| `grep -n 'current_sink' models.py` | one call, inside `from_api` (+1 docstring mention) | ✓ |
| `grep -n 'Phase 36' models.py` | 2 matches | WR-03 instruction survived ✓ |
| `grep -c 'TickPriceRange' verification/snapshots/matriz-client-surface.txt` | **2** | ≥ 2 ✓ |
| `python -c "import matriz_client; print(matriz_client.TickPriceRange.empty())"` | `TickPriceRange(lowerLimit=None, upperLimit=None, tick=None)` | no raise ✓ |

## Success Criteria

- [x] `InstrumentDetail.tickPriceRanges` is `dict[str, TickPriceRange]` and decodes the committed
      baseline shape into model instances, not raw dicts.
- [x] The axis routes element values through `_decode.walk_field` with the caller's sink and
      recurses on a nested mapping hint (proven at depth 2).
- [x] `_convert` still answers `{}` for a bare untyped-mapping hint against `None` and keeps its
      reversed `(tp, value)` argument order.
- [x] `TickPriceRange` is on the exported surface and in the regenerated snapshot.
- [x] `_decode.py` is byte-unchanged and all four gates are green.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| `44b6d66` | test | RED — element-typed, self-recursing mapping axis (6 failed, 88 passed) |
| `8fe5f8c` | feat | GREEN — the axis: `_element_hint`, element routing, recursion, `_safe_key` |
| `2e77611` | test | RED — `tickPriceRanges` against the committed live baseline (4 failed, 119 passed) |
| `8572523` | feat | GREEN — `TickPriceRange`, the retype, the exports, the snapshot |

## Self-Check: PASSED

All five claimed files exist on disk. All four claimed commit hashes resolve in `git log`. Both
`must_haves.artifacts` `contains` probes hold (`models.py` ⊃ `class TickPriceRange`;
`__init__.py`, `test_decode.py` and the snapshot all ⊃ `TickPriceRange`). Both
`must_haves.key_links` patterns match in `models.py` (`_decode\.walk_field\(` and `get_args\(`).

## TDD Gate Compliance

Two full RED → GREEN pairs, in order, one per task. Each RED was verified to fail for the right
reason before any implementation was written — Task 1 measured `6 failed, 88 passed` (the six new
behavioural cases, with four deliberate pins already green), Task 2 measured `4 failed, 119 passed`
with behavioural assertion failures rather than a collection error, because the new symbol is
reached inside test bodies. No REFACTOR commit was needed: the GREEN implementations landed in
their final shape and no cleanup pass changed behaviour. No test was deleted or weakened to make a
red go away, and the matriz suite is green at every commit of this plan.
