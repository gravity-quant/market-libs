---
phase: 35-fundaci-n-null-object-bool-pol-tica-del-walker
plan: 03
subsystem: iol-client + market-data-client models + decode contract tests
tags: [null-object, safemodel, decode, tdd, fan-out, form-a, form-b]
requires:
  - higyrus_client.models.SafeModel.empty (35-01, the ported reference)
provides:
  - iol_client.models.SafeModel.empty
  - iol_client.models.SafeModel.__bool__
  - market_data_client.models.SafeModel.empty
  - market_data_client.models.SafeModel.__bool__
  - packages/iol-client/tests/test_null_object.py
  - packages/market-data-client/tests/test_null_object.py
  - test_wrong_typed_list_field_still_reports_type (iol, market-data)
  - test_strict_mode_still_raises_on_a_wrong_typed_list (iol, market-data)
affects:
  - 35-04 (matriz + ambito + wallets fan-out — same suite shape)
  - 35-05 (walker disposition edit — the four new falsification tests are its tripwire)
  - 36 (market-data Null Object models — empty()/__bool__ are its foundation)
  - 38 (iol puntas Null Object — the alias-invisibility invariant is retired here)
tech-stack:
  added: []
  patterns:
    - "form A (iol): empty() = walk_model(cls, {}, POLICY, SILENT_SINK) then cls(**kwargs)"
    - "form B (market-data): the same walk PLUS _apply_mapping_policy(cls, kwargs, sink=SILENT_SINK), unconditional"
    - "__bool__ is 'self != type(self).empty()' verbatim (D-06) in both packages"
    - "class roster obtained by introspection of the real module, never a fixture list (D-15)"
key-files:
  created:
    - packages/iol-client/tests/test_null_object.py
    - packages/market-data-client/tests/test_null_object.py
  modified:
    - packages/iol-client/src/iol_client/models.py
    - packages/iol-client/tests/test_decode.py
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/tests/test_decode.py
decisions:
  - "35-03: iol takes form A verbatim from the 35-01 tracer — no mapping pass exists in this package and none was invented (grep _apply_mapping_policy in iol models.py returns 0)."
  - "35-03: market-data takes form B — empty() runs _apply_mapping_policy with an UNCONDITIONAL silent sink; from_api's isinstance(payload, dict) ternary collapses because inside empty() there is no payload that could be non-dict."
  - "35-03: no shared helper unifies the two forms. The delta is a declared per-package policy axis (29-SEMANTICS-MATRIX 'never harmonize') and Phase 36 retires market-data's mapping machinery outright, so a unifying shim would be born dead."
  - "35-03: market-data gained one test the other packages do not need — test_empty_and_from_api_agree_on_every_mapping_declared_field — which is the direct behavioural assertion of T-35-06, not just the exact-string grep the plan's acceptance criteria specify."
metrics:
  duration: ~14 min
  tasks: 2
  files: 6
  completed: 2026-08-29
status: complete
---

# Phase 35 Plan 03: Null Object fan-out to iol + market-data Summary

`empty()` + `__bool__` landed on the two remaining `SafeModel` bases — iol in **form A**
(bare walk) and market-data in **form B** (walk + mapping pass) — each proven over its real
shipped roster by introspection, with the alias-invisibility invariant and the wrong-type
falsification tripwires copied into both packages. No `_decode.py` byte moved.

## Measured Roster Counts

```
$ uv run python -c "...introspection over each models module..."
iol 4  ['Cotizacion', 'Instrumento', 'Punta', 'Titulo']
md  16 ['AddHolidaysResult', 'CalendarConfig', 'CalendarConfigPreview', 'CalendarDay',
        'DeleteHolidayResult', 'FeedIngestor', 'FeedMarket', 'FeedPipeline', 'Health',
        'HealthAuth', 'HealthFeed', 'Instrument', 'MarketDataSnapshot', 'PreviewMarket',
        'Segment', 'Symbol']
```

Both match `35-RESEARCH.md` F-1 exactly. `pytest --collect-only` reports **4** parametrized
cases per model-level test in iol (12 total) and **16** in market-data (48 total).

The seven serialize-OUT request dataclasses (`LatestRequest`, `NewSymbol`, `NewSymbols`,
`SymbolPatch`, `MarketHoursIn`, `HolidayIn`, `HolidaysIn`) are absent from the market-data
collect-only output — the `issubclass(obj, SafeModel)` condition excludes them structurally,
with **no hand-maintained deny-list** (D-08). Verified by grep against the collect output: 0 hits.

## The `empty()` Form Used Per Package, With Its Justification

| Package | Form | Body | Why |
|---|---|---|---|
| `iol-client` | **A** | `walk_model(cls, {}, POLICY, SILENT_SINK)` → `cls(**kwargs)` | iol's `from_api` is a bare walk. There is no mapping pass in this package, and inventing a no-op one to look like market-data would be dead code. `grep -c "_apply_mapping_policy" iol/models.py` → **0**. |
| `market-data-client` | **B** | the same walk, then `_apply_mapping_policy(cls, kwargs, sink=_decode.SILENT_SINK)` → `cls(**kwargs)` | This package's `from_api` runs the mapping pass because the walker has no `dict` branch. `empty()` must run it too or the two constructors disagree on every `dict`-typed field (T-35-06). The `isinstance(payload, dict)` ternary `from_api` uses does **not** carry over: inside `empty()` there is no payload, so both sinks are unconditionally silent. |

The delta is declared in market-data's `empty()` docstring as a per-package policy axis, per D-07
and `29-SEMANTICS-MATRIX.md`'s "never harmonize" rule. **No shared helper, module or shim was
created** to unify the two bodies.

## The Canonical Digest Was NOT Touched By This Plan

No byte of any `_decode.py` moved. `check_decode_intactness.py` still reduces the 5 copies to
`ac14868282ad0a5c`, matching the unchanged `CANONICAL_DIGEST` — the recomputation belongs to plan
35-05 and this plan did not pre-empt it.

## The 4 v1.6 Gates — Exact Output

```
--- check_decode_intactness ---
Check A  decode-helper intactness: 5 copies of `_decode.py` reduce to one normalized hash ac14868282ad0a5c, matching CANONICAL_DIGEST
Check B  filter scan-region intactness: 5 marker-delimited regions (54 lines each) reduce to one hash 684191c7cdc5ff9c
Check C  ban list: `strict=False` (in `_decode.py`), `msgspec.field(` absent from 75 package source files
Check D  package roster: 5 in-scope packages carry a `_decode.py`; `wallets-client` exempt (see .planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md)
exit=0
--- check_uniform_structure ---
uniform structure: all 6 packages under `packages/` carry `models.py`, `types.py` in their import root
exit=0
--- check_surface_types ---
surface types: 6 packages, 180 `__all__` names, 323 definitions scanned, 13 constant/alias exports, 23 exempted (dunder 13, private-helper 1, serialize-out 9), 0 violations
exit=0
--- surface_parity ---
exit=0
```

`check_surface_types` scanned 323 definitions, up from 321 at the 35-01 close — the two new
`empty()` classmethods. `__all__` is unchanged at 180 names: `empty` and `__bool__` are methods on
an already-exported base, so **the public surface did not move** (the Phase 35 "cero cambios de
superficie pública" condition).

## What Was Built

**Task 1 — iol** (`157f559` RED, `29bec9b` GREEN, `9692009` falsification).

- `packages/iol-client/tests/test_null_object.py`, 283 lines. Module-local roster helper,
  `_perturb` (seven branches, `cur is None` first), `_walk` / `_divergences` / `_records`,
  the `_AliasShaped` / `_AliasFree` pair, and the autouse `_pristine_decode_context` fixture.
  Six tests; the three `empty()`-dependent ones were RED at commit time (12 failures across
  4 classes × 3), the three day-0 ones green.
- Two methods on `iol_client.models.SafeModel`, placed between `from_api` and `to_dict`
  exactly as in the tracer. No `cast`, no `# type: ignore`, no memoization.
- Two tests appended to `tests/test_decode.py` (+55 / −0), adjacent to the existing model-site
  wrong-type test.

**Task 2 — market-data** (`11d0903` RED, `6339ed0` GREEN, `b5c9674` falsification).

- `packages/market-data-client/tests/test_null_object.py`, 314 lines. Same shape plus **one extra
  test the other packages do not carry** — `test_empty_and_from_api_agree_on_every_mapping_declared_field`
  — and the `MarketDataSnapshot` caveat written into the falsy test's docstring. RED at commit
  time: 49 failures (16 × 3 + the agreement test), 3 day-0 green.
- Form-B `empty()` + `__bool__` on the base. Both scoped and global mypy clean.
- Two tests appended to `tests/test_decode.py` (+55 / −0). `tests/test_core.py` **untouched** —
  the eleventh inversion at `test_core.py:1052` belongs to 35-05.

## The `MarketDataSnapshot` Caveat (D-09 / T-35-08)

`bool(MarketDataSnapshot.from_api(None)) is False` passes only because `received_at` defaults to
`0.0` on that code path; the shipped client always passes a wall-clock stamp, so a snapshot
decoded in production differs from its `empty()` and is **truthy even when the wire carried
nothing**. The assertion was **not** weakened or skipped to hide this. The nuance is stated in
two places, as the plan requires:

1. The `test_every_shipped_model_is_falsy_when_empty` docstring, which names the green as
   *structural, not semantic* and directs callers to ask the FIELD.
2. The `__bool__` docstring on the base, whose second recorded fact cites `MarketDataSnapshot`
   by name as this workspace's live example of an envelope that stamps after the walk.

## Verification Results

| Check | Command | Result |
|---|---|---|
| iol suite | `uv run pytest packages/iol-client -q` | **289 passed** (272 at plan start) |
| market-data suite | `uv run pytest packages/market-data-client -q` | **663 passed** (609 at plan start) |
| workspace suite | `uv run pytest packages -q` | **1881 passed, 1 deselected** in 90s (1810 at 35-01 close) |
| iol null-object | `pytest .../test_null_object.py -q` | 15 passed |
| market-data null-object | `pytest .../test_null_object.py -q` | 52 passed |
| wrong-type pair ×2 | `pytest .../test_decode.py -q -k wrong_typed_list` | 2 passed in each package |
| lint | `uv run ruff check packages/ && ruff format --check packages/` | clean, 189 files formatted |
| typecheck (root) | `uv run mypy` | Success — 75 source files |
| typecheck (market-data, scoped) | `uv run mypy packages/market-data-client/src` | Success — 13 source files (RESEARCH Pitfall 6: not covered by the root `files` list) |
| 4 v1.6 gates | see block above | all exit 0 |
| surface snapshots | `regen_snapshots.py && git diff --exit-code verification/snapshots/` | byte-identical (D-12) |
| dependencies | `git diff --exit-code pyproject.toml uv.lock packages/*/pyproject.toml` | clean (T-35-SC) |
| non-memoization (iol) | `Punta.empty() is not Punta.empty()` | asserts True |
| non-memoization (market-data) | `Health.empty() is not Health.empty()` | asserts True |
| additive-only ×2 | `git diff --numstat .../test_decode.py` | `55  0` in **both** — zero deletions |
| `test_core.py` untouched | `git diff --numstat .../test_core.py` | empty output |

Bare `uv run pytest` was never invoked (HARN-VERIF-01: `testpaths` includes `verification/`,
which hangs past 10 minutes and is red at baseline).

## TDD Gate Compliance

Two full RED → GREEN cycles, one per package, in commit order:

1. `157f559` `test(35-03)` — iol RED gate. Verified failing before the implementation existed:
   12 `AttributeError: type object 'X' has no attribute 'empty'`, 3 day-0 tests green.
2. `29bec9b` `feat(35-03)` — iol GREEN gate. All 15 cases pass.
3. `9692009` `test(35-03)` — green day-0 **by design**; a tripwire for 35-05, not a TDD cycle.
4. `11d0903` `test(35-03)` — market-data RED gate. 49 failing, 3 day-0 green.
5. `6339ed0` `feat(35-03)` — market-data GREEN gate. All 52 cases pass.
6. `b5c9674` `test(35-03)` — tripwire, green day-0 by design.

No REFACTOR commit was needed in either cycle.

## Deviations from Plan

### Carried Forward From 35-01 (all three prior-wave deviations applied)

1. **`_perturb`'s seventh nested-`SafeModel` branch** was copied into both new modules. Neither
   package has a shipped class that *needs* it today — iol's `Titulo.puntas` is `Punta | None`
   and answers on the first branch, and every market-data class leads with a scalar — but the
   branch is kept so the helper stays the same helper across the six paquetes and survives
   Phase 36/38 turning nested links non-Optional. Documented in each copy's docstring.
2. **The criterio-5 equality excludes the `model` key** — `_records()` projects onto
   `(field_path, divergence, declared_type, observed_type)` in both copies, with the exclusion
   explained in its docstring.
3. **The autouse `_pristine_decode_context` fixture** was copied into both new modules.

### Auto-fixed Issues

**1. [Rule 3 — Blocking] the iol no-cross-package-coupling grep counted docstring prose**

- **Found during:** Task 1
- **Issue:** The acceptance criterion
  `grep -c "higyrus\|matriz_client\|market_data_client\|..." tests/test_null_object.py` must
  return `0`. It returned `2`: both hits were the word "higyrus" inside explanatory docstrings
  ("the contract higyrus pinned first", "carried over from the higyrus tracer"), naming the
  source of the port — prose, not coupling. The module imports nothing outside `iol_client`.
- **Fix:** Reworded both to "the tracer paquete" and "the 35-01 tracer". Same 35-01 deviation-4
  pattern: describe the construct rather than quote the name. No behavioural change; the grep
  now returns `0`. The market-data copy was written with the same discipline from the start and
  returned `0` on first measurement.
- **Files modified:** `packages/iol-client/tests/test_null_object.py`
- **Commit:** `9692009`

**2. [Rule 2 — Missing critical coverage] T-35-06 was only grep-enforced**

- **Found during:** Task 2
- **Issue:** The plan's acceptance criteria enforce form B with an exact-string grep for
  `_apply_mapping_policy(cls, kwargs, sink=_decode.SILENT_SINK)`. A textual check cannot detect a
  future edit that keeps the line but changes what it does, and the threat register lists
  `empty()` diverging from `from_api` on dict-typed fields as a **mitigate** disposition.
- **Fix:** Added `test_empty_and_from_api_agree_on_every_mapping_declared_field`, asserting the
  two constructors produce the same `market_data` value on `MarketDataSnapshot` — the one shipped
  class declaring a mapping field. Behavioural, so it survives a refactor of the pass.
- **Files modified:** `packages/market-data-client/tests/test_null_object.py`
- **Commit:** `11d0903`

### Prohibitions — Verified

| Prohibition | Status | Evidence |
|---|---|---|
| `empty()` is never `cls.from_api(None)` in either package | **verified** | Both bodies read `_decode.walk_model(cls, {}, policy=_decode.POLICY, sink=_decode.SILENT_SINK)` then construct; `from_api` appears in neither. |
| No shared helper unifies the two forms | **verified** | No new module, no new function. Each base carries its own body; market-data's docstring declares the delta and cites `29-SEMANTICS-MATRIX.md`. `grep -c "_apply_mapping_policy" iol/models.py` → `0`. |
| `empty()` is never memoized | **verified** | No decorator, no module-level cache, no class attribute in either package. Proven behaviourally: `Punta.empty() is not Punta.empty()` and `Health.empty() is not Health.empty()` both assert True. |
| No pre-existing test edited | **verified** | `git diff --numstat` → `55  0` on **both** `test_decode.py` files. `test_core.py` produced empty output (unchanged). |

### Authentication Gates

None — this plan makes no network calls.

## Known Stubs

None.

## Threat Flags

None. The threat register's four rows are discharged or accepted as planned: **T-35-06** mitigated
by form B plus the new behavioural agreement test; **T-35-07** mitigated — memoization prohibited
and behaviourally disproven in both packages; **T-35-08** mitigated — the `MarketDataSnapshot`
caveat is written into both the test docstring and the `__bool__` docstring and the assertion was
not weakened; **T-35-SC** verified — no installs, and
`git diff --exit-code pyproject.toml uv.lock packages/*/pyproject.toml` is clean.

## For the Next Plan

- **35-04 (matriz + ámbito + wallets):** copy the suite shape from either module here.
  matriz's `_SafeModel` **already has `empty()`** (form B, `models.py:238`) — only `__bool__` and
  `UnknownFrame.__bool__` are missing there, so that package is not a full port. matriz is also
  where `_perturb`'s `cur is None` first branch finally earns its keep (almost everything is
  Optional-with-`None`-default). For ámbito and wallets the roster is 0 by decision (D-05) —
  assert that explicitly, never with an empty `parametrize` pytest would skip silently.
- **35-05 (walker edit):** there are now **six** wrong-type tripwires (higyrus ×2, iol ×2,
  market-data ×2), all green against the unedited walker. If the silencing edit reaches past
  `value is None` to every non-list value, they redden. Do not "fix" them by relaxing them.
  The three `test_adding_a_property_alias_does_not_change_the_divergence_count` copies assert
  equality between an alias pair, never an absolute count, so they must stay green through the
  disposition change unmodified. `CANONICAL_DIGEST` is still `ac14868282ad0a5c` and is 35-05's to
  recompute.

## Self-Check: PASSED

- `packages/iol-client/tests/test_null_object.py` — FOUND (283 lines)
- `packages/market-data-client/tests/test_null_object.py` — FOUND (314 lines)
- `packages/iol-client/src/iol_client/models.py` — FOUND (contains `def empty`, `def __bool__`)
- `packages/market-data-client/src/market_data_client/models.py` — FOUND (contains `def empty`, `def __bool__`, the form-B pass)
- `packages/iol-client/tests/test_decode.py` — FOUND (contains both new test names)
- `packages/market-data-client/tests/test_decode.py` — FOUND (contains both new test names)
- Commits `157f559`, `29bec9b`, `9692009`, `11d0903`, `6339ed0`, `b5c9674` — all FOUND
