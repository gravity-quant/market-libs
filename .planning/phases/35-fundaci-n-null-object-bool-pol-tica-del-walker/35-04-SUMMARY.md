---
phase: 35-fundaci-n-null-object-bool-pol-tica-del-walker
plan: 04
subsystem: matriz-client models + ambito/wallets zero-roster contract tests
tags: [null-object, safemodel, decode, tdd, fan-out, unknown-frame, zero-roster]
requires:
  - higyrus_client.models.SafeModel.empty (35-01, the ported reference)
  - packages/iol-client/tests/test_null_object.py (35-03, the suite shape)
provides:
  - matriz_client.models._SafeModel.__bool__
  - matriz_client.models.UnknownFrame.__bool__
  - packages/matriz-client/tests/test_null_object.py
  - packages/ambito-financiero-client/tests/test_null_object.py
  - packages/wallets-client/tests/test_null_object.py
  - test_wrong_typed_list_field_still_reports_type (matriz, ambito)
  - test_strict_mode_still_raises_on_a_wrong_typed_list (matriz, ambito)
affects:
  - 35-05 (walker disposition edit — there are now EIGHT wrong-type tripwires)
  - 37 (UnknownFrame.raw exemption — this plan added truthiness only)
  - 39 (matriz live verification is blocked by LIVE-MATZ-33 and was not routed around)
tech-stack:
  added: []
  patterns:
    - "matriz needed __bool__ ONLY — its empty() shipped in Phase 29 and was not restated"
    - "__bool__ is 'self != type(self).empty()' verbatim (D-06) in all four bases plus UnknownFrame"
    - "a zero roster is asserted as a positive structural property (AST class count, empty __all__, import discipline, absent walker) — never as a >= 0 bound, never as an empty parametrize"
key-files:
  created:
    - packages/matriz-client/tests/test_null_object.py
    - packages/ambito-financiero-client/tests/test_null_object.py
    - packages/wallets-client/tests/test_null_object.py
  modified:
    - packages/matriz-client/src/matriz_client/models.py
    - packages/matriz-client/tests/test_decode.py
    - packages/ambito-financiero-client/tests/test_decode.py
decisions:
  - "35-04: matriz's base declares __dataclass_fields__ as a ClassVar for the type-checker, so get_type_hints reports one name dataclasses.fields does not. The criterio-5 hint assertion is pinned as an EQUALITY against that single known extra rather than relaxed to a subset check — a second non-field annotation on the base would redden it."
  - "35-04: the two UnknownFrame cases are named test_UnknownFrame_* in CamelCase so the class name appears in the pytest node id, which is what the plan's collect-only acceptance criterion measures. Ruff's naming rules are not enabled in this workspace, so no suppression comment is needed (and RUF100 rejects one)."
  - "35-04: wallets' third test checks the walker's absence by BOTH import failure and on-disk layout, so neither a stale __pycache__ entry nor a file added without an import can hide the day the exemption ends."
metrics:
  duration: ~15 min
  tasks: 3
  files: 6
  completed: 2026-08-29
status: complete
---

# Phase 35 Plan 04: Null Object fan-out to matriz + the two model-free paquetes Summary

`__bool__` landed on matriz's `_SafeModel` and — hand-written, outside the hierarchy — on
`UnknownFrame`, proven over the **17** shipped classes by introspection; ámbito and wallets
contribute an *asserted* emptiness rather than a skipped enumeration. matriz's Phase-29
`empty()` is provably byte-unchanged and no `_decode.py` byte moved.

## Measured Roster Count (matriz)

```
$ uv run python -c "...introspection over matriz_client.models..."
17 ['AccountId', 'AccountReport', 'DetailedPosition', 'ExecutionReportFrame', 'Instrument',
    'InstrumentDetail', 'InstrumentId', 'MarketDataEntryValue', 'MarketDataFrame',
    'MarketDataLevel', 'MarketDataSnapshot', 'NewOrderResponse', 'Order', 'OrderReport',
    'Position', 'Segment', 'Trade']
```

Matches `35-RESEARCH.md` F-1 exactly. `pytest --collect-only -q | grep -c
"test_every_shipped_model_is_falsy_when_empty"` returns **17**, and the same output carries
**2** ids naming `UnknownFrame` outside the parametrized roster.

`UnknownFrame` is absent from the roster **structurally** — it does not inherit `_SafeModel`,
so the `issubclass` filter cannot see it — with no hand-maintained deny-list. Its exclusion is
explained in a block comment above its two by-name cases so a future reader does not "fix" the
filter to swallow it.

All 17 classes are perturbable, and **only** because `_perturb`'s `cur is None` branch comes
first: this is the paquete RESEARCH F-3 predicted would need it. Six of the seventeen answer on
the nested-model branch instead (`Instrument.instrumentId` and friends), which is the seventh
branch carried forward from 35-01.

## matriz `models.py` — The Evidence That `empty()` Was Not Touched

| Acceptance check | Required | Measured |
|---|---|---|
| `grep -c "def __bool__"` | 2 | **2** |
| `grep -c "return self != type(self).empty()"` | 2 | **2** |
| `grep -c "def empty"` vs the same at `HEAD` | equal | **2 == 2** |
| `git diff -U0 \| grep -c "^-"` | ≤ 2 | **2** |

The two `^-` lines are the diff's own `--- a/packages/...` header plus exactly **one** removed
source line:

```
-    modelling gap. Both methods below stay hand-written and untouched.
```

That is the `UnknownFrame` class-docstring sentence being re-counted from two to three, which
the plan required in the same edit (PATTERNS flag). Nothing in `from_api` or `empty()` was
rewritten, re-docstringed or "harmonized" — matriz's cells in the 6-way semantics matrix are
declared policy axes, not inconsistencies.

## The Shape of the Two Zero Assertions

Neither empty paquete asserts a bound. Both assert a **positive structural property** of the
shipped module, parsed out of its real source with `ast`:

| Paquete | Assertions | Tests |
|---|---|---|
| `ambito-financiero-client` | zero `ClassDef` nodes; `__all__ == []`; the only import is `from __future__` | 1 roster + 2 alias-pair = **3** |
| `wallets-client` | zero `ClassDef` nodes; `__all__ == []`; the only import is `from __future__`; **no `_decode.py`** in the paquete, checked by both import failure and on-disk layout | **3** |

`grep -c ">= 0"` returns `0` in both files; `grep -c "D-05"` returns `2` in each, so the reason
for the emptiness is cited rather than implied. `git diff --exit-code packages/*/src/` is clean
for both — no base was added to make either roster look non-empty, and wallets in particular
still cannot be given one without reddening all twelve of its CI matrix legs.

wallets carries **no** alias-invisibility test and **no** wrong-type test, because it has no
walker copy to drive. That absence is itself the third test rather than a comment.

## The Canonical Digest Was NOT Touched By This Plan

No byte of any `_decode.py` moved. `check_decode_intactness.py` still reduces the 5 copies to
`ac14868282ad0a5c`, matching the unchanged `CANONICAL_DIGEST` — the recomputation belongs to
plan 35-05 and this plan did not pre-empt it.

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
surface types: 6 packages, 180 `__all__` names, 324 definitions scanned, 13 constant/alias exports, 23 exempted (dunder 13, private-helper 1, serialize-out 9), 0 violations
exit=0
--- surface_parity ---
exit=0
```

`__all__` is unchanged at **180** names: `__bool__` is a method on an already-exported class in
both places it landed, so the public surface did not move (the Phase 35 "cero cambios de
superficie pública" condition). The matriz surface snapshot — 65 symbols, the largest of the
four — is byte-identical after regeneration, which is a real check here rather than a formality
(D-12, RESEARCH F-8).

## What Was Built

**Task 1 — matriz** (`4aef2f6` RED, `d3c10a4` GREEN, `6b62942` falsification).

- `packages/matriz-client/tests/test_null_object.py`, 303 lines. Module-local roster helper
  (filtering on the real private base, not a duck-typed predicate), `_perturb` with seven
  branches and `cur is None` first, `_walk` / `_divergences` / `_records`, the
  `_AliasShaped` / `_AliasFree` pair declared `frozen=True` **without** `slots` to match this
  paquete's convention, and the autouse `_pristine_decode_context` fixture. Eight tests, three
  of them parametrized over 17 classes → **56 cases**. RED at commit time: 18 failures (17
  falsy + `UnknownFrame` falsy), 38 green.
- Two `__bool__` methods on `models.py`. The base's carries a docstring in the base's own
  style; `UnknownFrame`'s is undocstringed, matching that class's LOCAL convention where the
  class docstring carries the contract. No `cast`, no `# type: ignore`.
- Two tests appended to `tests/test_decode.py` (+59 / −0), next to the existing model-site
  wrong-type test. Both drive `_Nested` with `rows: "garbage"` and assert full three-tuple
  **equality** against a one-element list, not the membership check this module usually uses.

**Task 2 — ámbito** (`07549bd`).

- `packages/ambito-financiero-client/tests/test_null_object.py`, 202 lines: the AST-based zero
  roster plus the criterio-5 alias pair built on this paquete's `_Model`-shaped
  frozen-slotted convention. 3 tests.
- Two tests appended to `tests/test_decode.py` (+57 / −0) inside the existing
  "Divergence class 2 — wrong type" section, navigated by symbol name because this module's
  line offsets are shifted relative to the other four.

**Task 3 — wallets** (`ca0c767`).

- `packages/wallets-client/tests/test_null_object.py`, 91 lines. Exactly 3 tests: zero roster,
  import-free module, absent walker. Nothing under `src/`.

## Verification Results

| Check | Command | Result |
|---|---|---|
| matriz suite | `uv run pytest packages/matriz-client -q` | **488 passed** (486 after Task 1's source edit, 484 at plan start) |
| ámbito suite | `uv run pytest packages/ambito-financiero-client -q` | **208 passed, 1 deselected** |
| wallets suite | `uv run pytest packages/wallets-client -q` | **10 passed** |
| workspace suite | `uv run pytest packages -q` | **1947 passed, 1 deselected** in 89s (1881 at 35-03 close) |
| matriz null-object | `pytest .../test_null_object.py -q` | 56 passed |
| ámbito null-object | `pytest .../test_null_object.py -q` | 3 passed |
| wallets null-object | `pytest .../test_null_object.py -q` | 3 passed |
| wrong-type pair ×2 | `pytest .../test_decode.py -q -k wrong_typed_list` | 2 passed in each paquete |
| lint | `uv run ruff check packages/ && ruff format --check packages/` | clean, 192 files formatted |
| typecheck (root) | `uv run mypy` | Success — 75 source files |
| typecheck (market-data, scoped) | `uv run mypy packages/market-data-client/src` | Success — 13 source files |
| 4 v1.6 gates | see block above | all exit 0 |
| surface snapshots | `regen_snapshots.py && git diff --exit-code verification/snapshots/` | byte-identical (D-12) |
| dependencies | `git diff --exit-code pyproject.toml uv.lock packages/*/pyproject.toml` | clean (T-35-SC) |
| additive-only ×2 | `git diff --numstat .../test_decode.py` | `59 0` (matriz), `57 0` (ámbito) — zero deletions |
| `src/` untouched ×2 | `git diff --exit-code packages/{ambito,wallets}/src/` | both exit 0 |
| pre-commit | `uv run pre-commit run --files <the six>` | all hooks Passed |

Bare `uv run pytest` was never invoked (HARN-VERIF-01 / RESEARCH Pitfall 5: `testpaths`
includes `verification/`, which hangs past 10 minutes and is red at baseline).

## TDD Gate Compliance

One full RED → GREEN cycle, for the only task in this plan that touches source:

1. `4aef2f6` `test(35-04)` — RED gate. Verified failing before `__bool__` existed: 18 failures
   (an object with no `__bool__` and no `__len__` is unconditionally truthy), 38 green.
2. `d3c10a4` `feat(35-04)` — GREEN gate. All 56 cases pass.
3. `6b62942`, `07549bd`, `ca0c767` — green day-0 **by design**. These are not TDD cycles:
   the wrong-type pair is a tripwire for 35-05, and the ámbito/wallets suites assert properties
   the shipped modules already hold. Asserting them is the deliverable.

No REFACTOR commit was needed.

## Deviations from Plan

### Carried Forward From 35-01 / 35-03 (all five prior-wave carry-forwards applied)

1. **`_perturb`'s seventh nested-`_SafeModel` branch** is present in the matriz copy, and here
   it is genuinely load-bearing: six of the seventeen classes lead with a nested-model field
   whose empty value is an INSTANCE, not `None`.
2. **The criterio-5 equality excludes the `model` key** — `_records()` projects onto
   `(field_path, divergence, declared_type, observed_type)` in both new alias-carrying modules.
3. **The autouse `_pristine_decode_context` fixture** was copied into all three new modules
   (wallets' copy is unnecessary and was therefore NOT added — that module drives no decode).
4. **No docstring in any new file names a sibling paquete.** Written that way from the start;
   the source of the port is referred to as "the tracer paquete" / "this paquete".
5. **matriz's `empty()` was verified, not rewritten.** The Phase-29 form-B body was read,
   confirmed against the plan's expectations, and left alone; only `__bool__` was added.

### Auto-fixed Issues

**1. [Rule 1 — Bug] the ported hint assertion is false on this paquete's base**

- **Found during:** Task 1
- **Issue:** The tracer's `test_property_aliases_are_invisible_to_get_type_hints` asserts
  `set(get_type_hints(cls)) == {f.name for f in dataclasses.fields(cls)}`. That is false for
  matriz: its `_SafeModel` declares `__dataclass_fields__: ClassVar[dict[str, Any]]` so pyright
  will accept `cls` as a dataclass. `get_type_hints` reports that annotation (it is real);
  `dataclasses.fields` correctly omits it (it is a `ClassVar`). The ported test failed on a
  difference that has nothing to do with the property alias.
- **Fix:** The assertion is now three statements — the declared fields are a subset of the
  hints, the difference is **exactly** `{"__dataclass_fields__"}`, and `"last"` is in neither.
  Pinned as an equality rather than relaxed to a subset check, so a second non-field annotation
  appearing on the base reddens it. The docstring explains that the walker enumerates
  `dataclasses.fields`, which is why the extra hint is harmless.
- **Files modified:** `packages/matriz-client/tests/test_null_object.py`
- **Commit:** `4aef2f6`

**2. [Rule 3 — Blocking] `# noqa: N802` on the two `UnknownFrame` cases is itself a lint error**

- **Found during:** Task 1
- **Issue:** The plan requires at least two test **ids** naming `UnknownFrame`, and a pytest
  node id for a non-parametrized test is `<file>::<function name>` — so the class name has to
  appear in the function name in its real CamelCase. Anticipating a pep8-naming complaint I
  added `# noqa: N802`; ruff rejected both with `RUF100 Unused noqa directive (non-enabled:
  N802)`, because `N` is not in this workspace's rule selection.
- **Fix:** Removed both suppressions. `test_UnknownFrame_is_falsy_when_empty` and
  `test_UnknownFrame_is_truthy_when_it_carries_a_frame_type` pass ruff unadorned, and
  `--collect-only -q | grep -c UnknownFrame` returns `2`.
- **Files modified:** `packages/matriz-client/tests/test_null_object.py`
- **Commit:** `4aef2f6`

### Prohibitions — Verified

| Prohibition | Status | Evidence |
|---|---|---|
| matriz's `empty()` is not rewritten, re-docstringed or harmonized | **verified** | `def empty` count equals the count at the parent commit (2 == 2); `git diff -U0` shows one removed source line, and it is the `UnknownFrame` docstring's method-count sentence. |
| No `SafeModel` base added to ámbito or wallets | **verified** | `git diff --exit-code packages/ambito-financiero-client/src/` and `.../wallets-client/src/` both exit 0. The new tests assert the emptiness rather than removing it. |
| A zero is never asserted as `>= 0` | **verified** | `grep -c ">= 0"` returns `0` in both new files; each carries an AST-derived equality against zero plus `D-05` cited twice. |
| No pre-existing test edited | **verified** | `git diff --numstat` → `59 0` (matriz) and `57 0` (ámbito). Zero deletions in both. The inversions at matriz `:335` / `:1234` and ámbito `:354` / `:1272` are untouched and remain 35-05's. |
| No dependency installs | **verified** | `git diff --exit-code pyproject.toml uv.lock packages/*/pyproject.toml` clean (T-35-SC). |

### Authentication Gates

None — this plan makes no network calls. matriz's live-verification block
(`LIVE-MATZ-33`, the remarkets-only policy assert) was **not** routed around; nothing in this
plan needs live traffic, and the block is named here so the Phase 39 planner does not discover
it fresh.

## Known Stubs

None.

## Threat Flags

None. The register's five rows are discharged or accepted as planned: **T-35-09** mitigated by
the two `def empty` / removed-line checks recorded above; **T-35-10** mitigated — no base was
copied into wallets and `src/` is provably unchanged; **T-35-11** mitigated — both zeros are
positive structural assertions with the reason cited and a `>= 0` bound grep-absent;
**T-35-12** accepted — `UnknownFrame.raw` gained truthiness only, nothing about what it holds or
who reads it changed (Phase 37's subject); **T-35-SC** verified — no installs, manifests clean.

## For the Next Plan

- **35-05 (walker edit):** there are now **eight** wrong-type tripwires (higyrus ×2, iol ×2,
  market-data ×2, matriz ×2, ámbito ×2 — ten in total across the phase), all green against the
  unedited walker. If the silencing edit reaches past `value is None` to every non-list value,
  they redden. Do not "fix" them by relaxing them. The five
  `test_adding_a_property_alias_does_not_change_the_divergence_count` copies assert equality
  between an alias pair, never an absolute count, so they must stay green through the
  disposition change unmodified. `CANONICAL_DIGEST` is still `ac14868282ad0a5c` and is 35-05's
  to recompute. NOBJ-01 is closed across all six paquetes as of this plan.
- **Phase 37:** `UnknownFrame` now has three hand-written methods and its class docstring says
  so. An edit that adds a fourth must update that sentence in the same commit.

## Self-Check: PASSED

- `packages/matriz-client/tests/test_null_object.py` — FOUND (303 lines)
- `packages/ambito-financiero-client/tests/test_null_object.py` — FOUND (202 lines)
- `packages/wallets-client/tests/test_null_object.py` — FOUND (91 lines)
- `packages/matriz-client/src/matriz_client/models.py` — FOUND (contains `def __bool__` ×2)
- `packages/matriz-client/tests/test_decode.py` — FOUND (contains both new test names)
- `packages/ambito-financiero-client/tests/test_decode.py` — FOUND (contains both new test names)
- Commits `4aef2f6`, `d3c10a4`, `6b62942`, `07549bd`, `ca0c767` — all FOUND
