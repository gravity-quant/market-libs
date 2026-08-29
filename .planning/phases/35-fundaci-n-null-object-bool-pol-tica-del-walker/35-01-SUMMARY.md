---
phase: 35-fundaci-n-null-object-bool-pol-tica-del-walker
plan: 01
subsystem: higyrus-client models + decode contract tests
tags: [null-object, safemodel, decode, tdd, tracer-slice]
requires: []
provides:
  - higyrus_client.models.SafeModel.empty
  - higyrus_client.models.SafeModel.__bool__
  - packages/higyrus-client/tests/test_null_object.py
  - test_wrong_typed_list_field_still_reports_type (higyrus)
  - test_strict_mode_still_raises_on_a_wrong_typed_list (higyrus)
affects:
  - 35-03 (iol + market-data fan-out of empty()/__bool__)
  - 35-04 (matriz + ambito + wallets fan-out)
  - 35-05 (walker disposition edit — the two new falsification tests are its tripwire)
tech-stack:
  added: []
  patterns:
    - "empty() routes through walk_model(cls, {}, policy=POLICY, sink=SILENT_SINK) — never through from_api"
    - "__bool__ is 'self != type(self).empty()' verbatim (D-06)"
    - "class roster obtained by introspection of the real module, never a fixture list (D-15)"
key-files:
  created:
    - packages/higyrus-client/tests/test_null_object.py
  modified:
    - packages/higyrus-client/src/higyrus_client/models.py
    - packages/higyrus-client/tests/test_decode.py
decisions:
  - "35-01: _perturb needs a SEVENTH branch (nested SafeModel, recursive) that RESEARCH Pitfall 3 does not list — in higyrus a nested-model field's empty value is a nested empty INSTANCE, not None, so Administrador (3 nested fields, zero scalars) falls through every branch the research helper declares."
  - "35-01: the criterio-5 equality is asserted on (field_path, divergence, declared_type, observed_type) and deliberately EXCLUDES the model key — the alias-carrying class and its alias-free twin necessarily disagree on their own class name and on nothing else."
  - "35-01: test_null_object.py carries its own copy of the autouse _pristine_decode_context fixture — without it a leaked STRICT_DECODE=True from another module would make every from_api(None) raise, and a leaked DECODE_SCOPE would dedupe records away by test ORDER."
metrics:
  duration: ~7 min
  tasks: 3
  files: 3
  completed: 2026-08-29
status: complete
---

# Phase 35 Plan 01: Fundación Null Object (tracer slice, higyrus) Summary

`higyrus_client.models.SafeModel` gained `empty()` (form A) and `__bool__`, proven over all
**15** real shipped subclasses by introspection — not a fixture roster — with the `@property`
alias-invisibility invariant that phases 36-38 depend on retired here, and the wrong-type
falsification half of NOBJ-02 pinned as a tripwire for plan 35-05.

## What Was Built

**Task 1 — RED suite** (`325b7bc`, `packages/higyrus-client/tests/test_null_object.py`, 259 lines).
Module-local roster helper (`inspect.getmembers` filtered by `SafeModel` subclass + `is_dataclass`
+ defining-module identity), module-local `_perturb`, module-local `_walk`/`_divergences`, and the
`_AliasShaped` / `_AliasFree` fixture pair. Six tests: three `empty()`-dependent (RED at commit
time, 45 failures across 15 parametrized classes × 3) and three day-0 green.

**Task 2 — GREEN** (`ec26ae9`, `packages/higyrus-client/src/higyrus_client/models.py`).
Two methods added to the base, between the existing `from_api` and `to_dict`:

- `empty()` — `@classmethod ... -> Self`; body is `walk_model(cls, {}, policy=POLICY, sink=SILENT_SINK)`
  then `cls(**kwargs)`. Same mechanism as the walker's own nested-model default site, so an
  `empty()` instance and a nested default are the same object by construction.
- `__bool__` — `return self != type(self).empty()` verbatim (D-06).

No `cast`, no `# type: ignore`, no memoization. `from_api`, `to_dict`, `__all__` and all 15
shipped dataclasses untouched.

**Task 3 — falsification** (`763b960`, `packages/higyrus-client/tests/test_decode.py`, +55 / −0).
Two new tests appended next to the existing model-site wrong-type test: a `str` where
`list[_Leaf]` is declared returns `[]` and emits exactly `[("_Nested", ".hojas", "type")]`, and the
same payload stays fatal under strict mode with the exception's `field_path` / `declared_type` /
`observed_type` / `model` all asserted.

## Measured Roster Count

```
$ uv run python -c "...introspection over higyrus_client.models..."
roster: 15
```

Matches `35-RESEARCH.md` F-1's measured count for higyrus exactly. `pytest --collect-only` reports
15 parametrized cases for each of the three model-level tests (45 cases total).

## The Canonical Digest Was NOT Touched By This Plan

No byte of any `_decode.py` moved. `check_decode_intactness.py` still reduces the 5 copies to
`ac14868282ad0a5c`, matching the unchanged `CANONICAL_DIGEST` — the digest recomputation is plan
35-05's, and this plan did not pre-empt it.

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
surface types: 6 packages, 180 `__all__` names, 321 definitions scanned, 13 constant/alias exports, 23 exempted (dunder 13, private-helper 1, serialize-out 9), 0 violations
exit=0
--- surface_parity ---
exit=0
```

## Verification Results

| Check | Command | Result |
|---|---|---|
| higyrus suite | `uv run pytest packages/higyrus-client -q` | 289 passed (287 before Task 3's two) |
| workspace suite | `uv run pytest packages -q` | **1810 passed, 1 deselected** in 93s |
| lint | `uv run ruff check packages/ && uv run ruff format --check packages/` | clean, 187 files formatted |
| typecheck (root) | `uv run mypy` | Success — 75 source files |
| typecheck (market-data) | `uv run mypy packages/market-data-client/src` | Success — 13 source files |
| 4 v1.6 gates | see block above | all exit 0 |
| surface snapshots | `regen_snapshots.py && git diff --exit-code verification/snapshots/` | byte-identical (D-12) |
| dependencies | `git diff --exit-code pyproject.toml uv.lock packages/*/pyproject.toml` | clean (T-35-SC) |
| non-memoization | `Cuenta.empty() is not Cuenta.empty()` | asserts True |
| additive-only | `git diff --numstat .../test_decode.py` | `55  0` — zero deletions |

Bare `uv run pytest` was never invoked (HARN-VERIF-01: `testpaths` includes `verification/`, which
hangs past 10 minutes and is red at baseline).

## TDD Gate Compliance

RED → GREEN → (no REFACTOR needed) in commit order:

1. `325b7bc` `test(35-01)` — RED gate. Verified failing before the implementation existed: the
   three day-0 tests passed and the three `empty()`-dependent tests failed with `AttributeError`
   on `empty`, exactly as the plan's `cmd1 && ! cmd2` verification demands.
2. `ec26ae9` `feat(35-01)` — GREEN gate. All 48 cases pass.
3. `763b960` `test(35-01)` — Task 3's tests are green day-0 **by design**; they are not a TDD
   cycle but a tripwire for plan 35-05 (see below).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] `_perturb` as specified cannot perturb `Administrador`**

- **Found during:** Task 1
- **Issue:** The plan (and `35-RESEARCH.md` Pitfall 3) states that `higyrus_client.models.Administrador`
  is the local class proving the `cur is None` branch must come first. Probed against the real
  module, that is not what happens: higyrus's walker builds a nested-model default as a nested
  **empty instance**, not `None` — `Administrador.from_api(None)` returns
  `Administrador(agente=Agente('', ''), operador=Operador('', '', ''), sucursal=Sucursal('', ''))`.
  All three fields are `SafeModel` instances, matching none of the six branches the research helper
  declares, so `_perturb` would hit its `raise AssertionError` fall-through and
  `test_every_shipped_model_is_truthy_when_populated[Administrador]` would fail permanently.
  (The `None`-first branch is still needed — it is matriz, in plan 35-04, where it earns its keep,
  since matriz declares almost everything Optional-with-`None`-default.)
- **Fix:** Added a seventh branch, **after** `dict` and **before** the `raise`:
  `if isinstance(cur, SafeModel): return dataclasses.replace(empty, **{f.name: _perturb(cur)})`.
  Branch order required by the plan (`cur is None` strictly before `isinstance(cur, str)`) is
  preserved, as is the loud `AssertionError` fall-through.
- **Files modified:** `packages/higyrus-client/tests/test_null_object.py`
- **Commit:** `325b7bc`
- **Fan-out note for 35-03 / 35-04:** the copied helper in iol, market-data, matriz, ámbito and
  wallets needs this same seventh branch wherever a nested-model field's default is an instance
  rather than `None`.

**2. [Rule 2 — Missing critical coverage] criterio-5 equality must exclude the `model` key**

- **Found during:** Task 1
- **Issue:** The plan says to "assert the two record lists are equal". Compared as raw records or
  as `(model, field_path, divergence)` triples, `_AliasShaped` and `_AliasFree` can never be equal —
  the walker stamps each record with its own class name. A literal reading of the instruction would
  produce a permanently-red test.
- **Fix:** Projection helper `_records()` compares
  `(field_path, divergence, declared_type, observed_type)` and documents in its docstring exactly
  why `model` is excluded. The invariant remains equality between the pair, never an absolute
  count, so it survives 35-05's disposition change untouched.
- **Files modified:** `packages/higyrus-client/tests/test_null_object.py`
- **Commit:** `325b7bc`

**3. [Rule 3 — Blocking] added the autouse `_pristine_decode_context` fixture to the new module**

- **Found during:** Task 1
- **Issue:** The plan did not name this fixture as part of `test_null_object.py`. Without it, a
  `STRICT_DECODE=True` leaked from another test module makes every `cls.from_api(None)` in this
  suite raise `HigyrusDecodeError` (a non-dict payload emits a terminal `non_dict` record, which is
  fatal under strict), and a leaked `DECODE_SCOPE` makes divergence assertions order-dependent.
- **Fix:** Copied verbatim from `test_decode.py` with an adapted docstring.
- **Files modified:** `packages/higyrus-client/tests/test_null_object.py`
- **Commit:** `325b7bc`

**4. [Rule 3 — Blocking] two acceptance greps counted docstring prose**

- **Found during:** Tasks 1 and 3
- **Issue:** `grep -c "obj.__module__ == models.__name__"` returned `2` (criterion: `1`) and
  `grep -c "pytest.raises"` rose by `2` (criterion: `+1`) because both literals also appeared inside
  explanatory docstrings.
- **Fix:** Reworded both docstrings to describe the construct rather than quote it. No behavioural
  change; both criteria now return their exact expected values.
- **Files modified:** `packages/higyrus-client/tests/test_null_object.py`, `packages/higyrus-client/tests/test_decode.py`
- **Commits:** `325b7bc`, `763b960`

### Prohibitions — Verified

| Prohibition | Status | Evidence |
|---|---|---|
| `empty()` is never `cls.from_api(None)` | **verified** | Body reads `_decode.walk_model(cls, {}, policy=_decode.POLICY, sink=_decode.SILENT_SINK)` then `cls(**kwargs)`; `from_api` appears nowhere in it. |
| `empty()` is never memoized | **verified** | No decorator, no module-level cache, no class attribute. Proven behaviourally: `Cuenta.empty() is not Cuenta.empty()` asserts True. |
| No existing test edited | **verified** | `git diff --numstat packages/higyrus-client/tests/test_decode.py` → `55  0`. Zero deletions. |

### Authentication Gates

None — this plan makes no network calls.

## Known Stubs

None.

## Threat Flags

None. `empty()` and `__bool__` are pure and payload-independent (T-35-01 accepted), memoization is
prohibited and behaviourally enforced (T-35-02 mitigated), nothing changed about what the divergence
channel emits (T-35-03 accepted), and no dependency manifest moved (T-35-SC verified clean).

## For the Next Plan

- **35-03 / 35-04 (fan-out):** copy the `empty()` + `__bool__` pair and the test module shape, but
  give `_perturb` the seventh nested-model branch (deviation 1) wherever nested defaults are
  instances. For ámbito and wallets the roster is 0 by decision (D-05) — assert that explicitly, not
  with an empty `parametrize` that pytest would skip silently.
- **35-05 (walker edit):** `test_wrong_typed_list_field_still_reports_type` and
  `test_strict_mode_still_raises_on_a_wrong_typed_list` are green today against the **unedited**
  walker. They are the falsification boundary: if the silencing edit reaches past `value is None` to
  every non-list value, these redden. Do not "fix" them by relaxing them.
  `test_adding_a_property_alias_does_not_change_the_divergence_count` asserts equality between the
  alias pair, not an absolute count, so it must stay green through the disposition change unmodified.

## Self-Check: PASSED

- `packages/higyrus-client/tests/test_null_object.py` — FOUND
- `packages/higyrus-client/src/higyrus_client/models.py` — FOUND (contains `def __bool__`, `def empty`)
- `packages/higyrus-client/tests/test_decode.py` — FOUND (contains both new test names)
- Commit `325b7bc` — FOUND
- Commit `ec26ae9` — FOUND
- Commit `763b960` — FOUND
