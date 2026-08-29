---
phase: 35-fundaci-n-null-object-bool-pol-tica-del-walker
plan: 05
subsystem: the walker disposition (NOBJ-02) + the phase gate
tags: [null-object, decode, walker, nobj-02, atomic-commit, canonical-digest, phase-gate]
requires:
  - higyrus_client.models.SafeModel.empty (35-01)
  - .planning/phases/35-.../35-RETIRED-TRIPLES.md (35-02)
  - the ten wrong-type tripwires written by 35-01 / 35-03 / 35-04
provides:
  - "EDIT 1 — list site, sink call gated on a non-null value, kind argument as the literal \"type\" — _decode.py x5"
  - "EDIT 2 — model site, null branch reduced to its return — _decode.py x5"
  - "the rewritten `# Phase 35, NOBJ-02:` disposition comment, byte-identical x5"
  - "CANONICAL_DIGEST = a1f00c824348164cb04c086993826c0050d6d344fcdaf778a37112751bc97e1f"
  - "the eleven inverted assertions across six test files"
affects:
  - 36 (market-data Null Object models decode against this disposition)
  - 37 (matriz typed report fields)
  - 38 (iol puntas)
  - 39 (live census — subtracts 35-RETIRED-TRIPLES.md rather than rediscovering)
tech-stack:
  added: []
  patterns:
    - "the list-site silence is an identity test against the null singleton, never a truthiness test"
    - "not calling the sink IS not raising — strict_decode needed no new code (D-02)"
    - "the comment rewrite is byte-identical x5 by construction because comments are hashed; module docstrings are not, and got manual review x5"
key-files:
  created:
    - .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-05-SUMMARY.md
  modified:
    - packages/ambito-financiero-client/src/ambito_financiero_client/_decode.py
    - packages/higyrus-client/src/higyrus_client/_decode.py
    - packages/iol-client/src/iol_client/_decode.py
    - packages/market-data-client/src/market_data_client/_decode.py
    - packages/matriz-client/src/matriz_client/_decode.py
    - packages/ambito-financiero-client/tests/test_decode.py
    - packages/higyrus-client/tests/test_decode.py
    - packages/iol-client/tests/test_decode.py
    - packages/market-data-client/tests/test_decode.py
    - packages/matriz-client/tests/test_decode.py
    - packages/market-data-client/tests/test_core.py
    - tools/check_decode_intactness.py
decisions:
  - "35-05: the module docstring's bullet claiming a sink call before EVERY substituted default rotted with this change and was amended byte-identically in all five copies. Docstrings are stripped by normalization rule 1, so the amendment does not move the digest — it is the manual x5 review D-10 demands actually finding something."
  - "35-05: the `# Phase 29 code review, WR-02 — an absent nested-model key is `missing`` SECTION HEADER above the inverted test was deliberately left unedited in all five test_decode.py files. Editing it would have produced a deletion not attributable to the eleven named assertions, breaking the phase's diff-accounting prohibition. Flagged here for the next reader rather than silently fixed."
  - "35-05: no comment was added at the list site. The plan prescribes the comment rewrite at the model site only; the identity-vs-truthiness constraint is enforced by the ten wrong-type tripwires and by the acceptance grep instead of by prose."
metrics:
  duration: ~10 min
  tasks: 2
  files: 13
  completed: 2026-08-29
status: complete
---

# Phase 35 Plan 05: the walker disposition + the phase gate Summary

A null or absent value on a non-optional model-typed or list-typed field now collapses to
the empty instance or `[]` **without emitting a divergence record**, while a wrong-typed
value on the same field still emits the six-key record and is still fatal under
`strict_decode`. The five `_decode.py` copies, the byte-identical comment rewrite, the
eleven inverted assertions and the recomputed `CANONICAL_DIGEST` landed as **one commit**,
`ece3a3c`, listing all twelve files.

---

## Criterion 1 — Truthiness across the six paquetes

Closed by plans 35-01, 35-03 and 35-04; this plan's job was not to redden it. The rosters
are obtained by introspection of the real shipped modules (D-15), never from a fixture list.

| Paquete | Roster | Base | Source |
|---|---:|---|---|
| `higyrus-client` | 15 | `SafeModel` (form A) | 35-01 |
| `iol-client` | 4 | `SafeModel` (form A) | 35-03 |
| `market-data-client` | 16 | `SafeModel` (form B, mapping pass) | 35-03 |
| `matriz-client` | 17 + `UnknownFrame` | `_SafeModel` (`empty()` shipped in Phase 29; only `__bool__` added) | 35-04 |
| **Total enumerated** | **52 + `UnknownFrame`** | | |

**The two paquetes whose roster is empty, named with their reason** — neither is a blank
cell and neither is a bound:

- **`ambito-financiero-client`** — empty **by decision (D-05)**. Its entire public surface is
  one function returning a `float`, so `models.py` declares no base and no subclasses. Plan
  35-04 asserts that as a **positive structural property** parsed out of the real source with
  `ast`: no `ClassDef` node, an empty `__all__`, and `from __future__` as the only import.
  Its `_decode.py` copy is dormant by design and is exercised only by locally declared
  fixture dataclasses.
- **`wallets-client`** — empty **by decision (D-05)**, and additionally exempt from the
  decode roster (`29-WALLETS-EXEMPTION.md`, Check D below). Same three structural assertions
  plus a fourth: it carries **no walker module at all**, checked by both import failure and
  on-disk layout, so neither a stale `__pycache__` entry nor a file added without an import
  can hide the day the exemption ends.

Measured this plan, after the disposition change:

```
uv run pytest packages -q
1947 passed, 1 deselected in 90.56s (0:01:30)
```

The truthiness suites are inside that count and none of them was touched by this plan.

---

## Criterion 2 — The disposition, and both halves falsified

### The collapse half

**EDIT 1 — the list site, in all five copies.** The sink call is now nested under an identity
test against the null singleton, and its kind argument is the string literal `"type"`
(at that point the value is provably not null, so the discriminator could only ever have
returned that one answer):

```python
    if origin is list:
        if not isinstance(value, list):
            if value is not None:
                sink(model, path, "type", _name_of(hint), type(value).__name__)
            return []
```

**EDIT 2 — the model site, in all five copies.** The null guard's body is reduced to its
return. The returned VALUE is unchanged — it was already the all-defaults instance built
with the silent sink; only the reporting went away:

```python
        if value is None:
            return hint(**walk_model(hint, {}, path=path, policy=policy, sink=SILENT_SINK))
```

**`strict_decode` needed no new code (D-02).** The raise lives in the single
`DecodeScope.__call__` choke point, downstream of the sink call, so *not calling the sink is
not raising*. That choke point was read and left byte-untouched.

**The disposition comment** preceding the model site was rewritten rather than left to rot —
it previously explained why a null on a declared nested-model field was recorded, which is
exactly the half that stopped being true. It is byte-identical across the five copies by
construction (comments are hashed; the gate enforces it), it is prefixed
`# Phase 35, NOBJ-02:` following the file's `# Lock N:` / `# Phase NN code review, WR-0X:`
convention, and it keeps WR-02's history on record alongside the new disposition: WR-02's
*classification order* is still load-bearing and still there, and what NOBJ-02 retires is
only the record it used to emit. The comment describes the removed call in words rather than
quoting it, so the acceptance grep below stays honest.

### The falsification of the collapse half — the eleven inverted assertions

**The intermediate scope measurement.** With the walker edited and **before a single test was
touched**, `uv run pytest packages -q` produced exactly eleven failures, and they were exactly
the eleven the plan names — no twelfth, none missing:

```
FAILED packages/ambito-financiero-client/tests/test_decode.py::test_missing_list_field_returns_empty_list_and_reports
FAILED packages/ambito-financiero-client/tests/test_decode.py::test_absent_nested_model_key_is_missing_on_the_outer_model
FAILED packages/higyrus-client/tests/test_decode.py::test_missing_list_field_returns_empty_list_and_reports
FAILED packages/higyrus-client/tests/test_decode.py::test_absent_nested_model_key_is_missing_on_the_outer_model
FAILED packages/iol-client/tests/test_decode.py::test_missing_list_field_returns_empty_list_and_reports
FAILED packages/iol-client/tests/test_decode.py::test_absent_nested_model_key_is_missing_on_the_outer_model
FAILED packages/market-data-client/tests/test_core.py::test_health_from_api_missing_auth_yields_zero_valued_nested_model
FAILED packages/market-data-client/tests/test_decode.py::test_missing_list_field_returns_empty_list_and_reports
FAILED packages/market-data-client/tests/test_decode.py::test_absent_nested_model_key_is_missing_on_the_outer_model
FAILED packages/matriz-client/tests/test_decode.py::test_missing_list_field_returns_empty_list_and_reports
FAILED packages/matriz-client/tests/test_decode.py::test_absent_nested_model_key_is_missing_on_the_outer_model
11 failed, 1936 passed, 1 deselected in 91.50s (0:01:31)
```

That measurement **is** the scope proof: it is the eleven-red set measured under the applied
change, not inferred, and it closes RESEARCH assumption A5.

Each of the ten in `test_decode.py` was inverted **by reading it**, not by scripted
substitution — matriz's copies are not verbatim siblings of the other four. Every assertion
about the returned VALUE is byte-unchanged; only the emitted-records assertion moved:

| Site | Old assertion | New assertion |
|---|---|---|
| list site, ambito / higyrus / iol / market-data | `_tuples(records) == [(".hojas", "missing")]` | `_tuples(records) == []` |
| list site, matriz | `(".rows", "missing") in _pairs(caplog)` | `(".rows", "missing") not in _pairs(caplog)` |
| model site, ambito / higyrus / iol / market-data | `triples == [("_CarriesNested", ".hoja", "missing")]` | `triples == []` |
| model site, matriz | `("_Nested", ".leaf", "missing") in triples` | `("_Nested", ".leaf", "missing") not in triples` |
| `test_core.py` (the eleventh) | `[(r.field_path, r.divergence) for r in records] == [(".auth", "missing")]` | `... == []` |

matriz's model-site copy carries a **second, negative** assertion after the inverted one
(`assert not [t for t in triples if t[2] == "non_dict"]`); it was kept intact, because it
pins the half NOBJ-02 does not touch. In `test_core.py` only the records line moved — the
`HealthAuth(configured=False, enabled=False, issuer="")` equality, which is the point of
NOBJ-02, stayed byte-identical.

All ten in `test_decode.py` were **renamed** (`..._and_reports` →
`..._without_reporting`; `..._is_missing_on_the_outer_model` →
`..._collapses_silently_on_the_outer_model`) and their docstrings rewritten, each gaining a
sentence recording that the inversion is deliberate and citing NOBJ-02 and D-13 — so a test
is never named for a report it no longer expects, and a later reader cannot mistake the
change for a weakened test.

### The falsification of the report half — the ten wrong-type tripwires

Written by waves 1-2 against the **unedited** walker, and green through this change. They are
what proves the silencing did not over-reach from "is null" to "is falsy" — an empty string,
a zero, an empty dict and an empty list are all falsy and are all legitimate wrong-types that
must keep diverging:

```
uv run pytest packages -q -k "wrong_typed_list or still_raises_on_a_wrong_typed_list"
10 passed, 1938 deselected in 0.23s
```

Not one of them was relaxed, renamed or skipped. The acceptance grep backs them up
structurally: `if value is not None:` appears **exactly once** in each of the five copies —
an identity check against null, never a truthiness test.

### The three adjacent dispositions D-14 protects — green and unedited

```
uv run pytest packages -q -k "test_non_dict_returns_empty or test_none_payload_behaves_as_non_dict
  or test_strict_mode_raises_on_a_missing_mapping_field or test_strict_mode_does_not_make_empty_fatal
  or test_non_dict_nested_payload_keeps_the_nested_attribution"
13 passed, 1935 deselected in 0.23s
```

The top-level `non_dict` record for a `None`/204 body, the `missing` record for scalar leaves
including scalars inside list elements, the mapping axis, and empty-is-not-fatal-under-strict
all survive untouched (D-03, D-14).

### The per-copy acceptance greps

Measured on all five `_decode.py` copies, identical in every one:

| Grep | At `HEAD~1` | Now | Meaning |
|---|---:|---:|---|
| `sink(model, path, "missing"` | 1 | none | the model-site sink call is gone; the check is non-vacuous |
| `if value is not None:` | none | 1 | the list-site gate exists, exactly once |
| `_kind_of(value), _name_of(hint)` | 2 | 1 | the list site lost its call; the `Literal` branch kept its own — the intended asymmetry |
| `Phase 35, NOBJ-02` | none | 1 | the disposition marker, same non-zero value in all five |
| `if value is None:` | 3 | 3 | unchanged — the `Optional` early return, the model-site guard and the other null checks all survive; only a sink call was removed |

---

## Criterion 3 — The four v1.6 gates, with the digest side by side

```
##### 1 decode-intactness
Check A  decode-helper intactness: 5 copies of `_decode.py` reduce to one normalized hash a1f00c824348164c, matching CANONICAL_DIGEST
Check B  filter scan-region intactness: 5 marker-delimited regions (54 lines each) reduce to one hash 684191c7cdc5ff9c
Check C  ban list: `strict=False` (in `_decode.py`), `msgspec.field(` absent from 75 package source files
Check D  package roster: 5 in-scope packages carry a `_decode.py`; `wallets-client` exempt (see .planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md)
exit=0
##### 2 uniform-structure
uniform structure: all 6 packages under `packages/` carry `models.py`, `types.py` in their import root
exit=0
##### 3 surface-types
surface types: 6 packages, 180 `__all__` names, 324 definitions scanned, 13 constant/alias exports, 23 exempted (dunder 13, private-helper 1, serialize-out 9), 0 violations
exit=0
##### 4 surface-parity
exit=0
```

### The digest, old and new

| | Value |
|---|---|
| **OLD** `CANONICAL_DIGEST` | `ac14868282ad0a5c6fb85ab7b7920068303a781835b9c76ca50f26283c1c3dc5` |
| **NEW** `CANONICAL_DIGEST` | `a1f00c824348164cb04c086993826c0050d6d344fcdaf778a37112751bc97e1f` |

**The new value was read verbatim from the gate's own failure message** — it was not authored,
not predicted, and not copied from any planning document. This is the message it was read
from, produced after the five copies were edited and before the pin was touched:

```
::error::Phase 29 DEC-01 decode intactness -- the canonical decode body CHANGED -- all five copies agree with each other but not with the reviewed body.
  expected (CANONICAL_DIGEST): ac14868282ad0a5c6fb85ab7b7920068303a781835b9c76ca50f26283c1c3dc5
  computed:                    a1f00c824348164cb04c086993826c0050d6d344fcdaf778a37112751bc97e1f
  A uniform edit across all five copies passes the mutual check by construction; this pin is what makes it visible.
  If the change is intended and reviewed, bump CANONICAL_DIGEST in this script to the computed value and say why in the commit message.
::error::decode-intactness gate FAILED (1 of 4 checks)
```

Two things that message settles beyond the value itself. First, it reports **ONE** distinct
hash across the five copies (`all five copies agree with each other`) — no copy was left
behind and none diverged, so the printed digest is meaningful rather than an artefact of a
disagreement being silenced. Second, Checks B, C and D stayed green throughout, so the only
thing that moved was the reviewed body.

The new pin **differs from the digest `35-RESEARCH.md` §Findings F-6 printed as `computed:`**
(`cd937d179f454b50f4a3cf6abbf2b2ee3fcb193e14e57d1b50b1b790fb8dbd16`), which corresponds to a
variant of this edit that had no comment rewrite. Verified mechanically —
`grep -c "cd937d17..." tools/check_decode_intactness.py` returns nothing.

### No gate was weakened

No normalization rule was added or relaxed, no lower bound was lowered, no package was
excluded from any roster, and no strictness knob was touched. The evidence:

```
git diff --stat tools/check_decode_intactness.py
 tools/check_decode_intactness.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)

git diff --exit-code pyproject.toml .github/workflows/ci.yml \
  tools/check_uniform_structure.py tools/check_surface_types.py tools/surface_parity.py
exit=0
```

One insertion and one deletion, on the pin line and nothing else. The other three gate
scripts, `pyproject.toml` and `ci.yml` are byte-unchanged.

---

## Criterion 4 — No public surface changed

### The surface snapshots regenerate byte-identical

`verification/regen_snapshots.py` has no `--check` flag, so the check is a regeneration
followed by a diff. This is asserted here rather than inferred from a CI leg, because
`verification/` never runs in CI:

```
uv run python verification/regen_snapshots.py
Wrote .../ambito-financiero-client-surface.txt (10 symbols)
Wrote .../iol-client-surface.txt (19 symbols)
Wrote .../higyrus-client-surface.txt (31 symbols)
Wrote .../matriz-client-surface.txt (65 symbols)

git diff --exit-code verification/snapshots/
exit=0
```

All four snapshot files are byte-identical. The snapshot format records name, kind and the
constructor signature, which is why adding methods to a base does not move it (D-12) — and
`__all__` held steady at **180** names across the whole phase.

### The phase-wide test-edit accounting

Across the entire phase (`242b9f3..HEAD`), by `git diff --numstat`:

| File | Added | Deleted | Nature |
|---|---:|---|---|
| `ambito-financiero-client/tests/test_null_object.py` | 209 | none | new file |
| `higyrus-client/tests/test_null_object.py` | 275 | none | new file |
| `iol-client/tests/test_null_object.py` | 283 | none | new file |
| `market-data-client/tests/test_null_object.py` | 314 | none | new file |
| `matriz-client/tests/test_null_object.py` | 331 | none | new file |
| `wallets-client/tests/test_null_object.py` | 91 | none | new file |
| `ambito-financiero-client/tests/test_decode.py` | 78 | 12 | additive tripwires + 2 inversions |
| `higyrus-client/tests/test_decode.py` | 76 | 12 | additive tripwires + 2 inversions |
| `iol-client/tests/test_decode.py` | 76 | 12 | additive tripwires + 2 inversions |
| `market-data-client/tests/test_decode.py` | 76 | 12 | additive tripwires + 2 inversions |
| `matriz-client/tests/test_decode.py` | 83 | 9 | additive tripwires + 2 inversions |
| `market-data-client/tests/test_core.py` | 1 | 1 | the eleventh inversion |

**Deletions appear in exactly six test files** — the five `test_decode.py` and market-data's
`test_core.py` — and every one is attributable to the eleven named assertions and their
names and docstrings. There is no seventh test file with deletions. The six
`test_null_object.py` files are purely additive. **The eleven were the whole of it.**

Source-side, the five `_decode.py` copies each show an identical `29 / 10` numstat, which is
the verbatim-x5 discipline visible in the diff itself.

### Everything else

```
uv run pytest packages -q            1947 passed, 1 deselected in 90.56s
uv run pytest tests -q               2 passed in 0.01s
uv run ruff check packages/          All checks passed!
uv run ruff format --check packages/ 192 files already formatted
uv run mypy                          Success: no issues found in 75 source files
uv run mypy packages/market-data-client/src
                                     Success: no issues found in 13 source files
git diff --exit-code pyproject.toml uv.lock packages/*/pyproject.toml
                                     exit=0
```

Bare `uv run pytest` was **never** invoked. `testpaths` includes `verification/`, which does
not finish inside ten minutes (real-sleep retry tests) and is red at baseline under the known
`HARN-VERIF-01` debt; a green there is neither achievable nor expected and is not part of
this phase's contract (RESEARCH Pitfall 5 / F-9). CI does not run it either — the `test` job
passes an explicit per-package path that overrides `testpaths`. This phase installs nothing
and its dependency closure is unchanged.

---

## Criterion 5 — Alias invisibility

The invariant phases 36-38 depend on — that a `@property` alias on a dataclass is invisible
to `get_type_hints()`, so adding one cannot fabricate a `missing` record nor change the
divergence count — is pinned in **each of the five paquetes that have a walker**:

| Paquete | `test_property_aliases_are_invisible_to_get_type_hints` | `test_adding_a_property_alias_does_not_change_the_divergence_count` |
|---|---|---|
| `ambito-financiero-client` | `tests/test_null_object.py:184` | `tests/test_null_object.py:192` |
| `higyrus-client` | `tests/test_null_object.py:250` | `tests/test_null_object.py:258` |
| `iol-client` | `tests/test_null_object.py:258` | `tests/test_null_object.py:266` |
| `market-data-client` | `tests/test_null_object.py:289` | `tests/test_null_object.py:297` |
| `matriz-client` | `tests/test_null_object.py:292` | `tests/test_null_object.py:314` |

**`wallets-client` has none, and asserts that absence instead** — it carries no walker to
drive, so its `tests/test_null_object.py` states the fact as its third test,
`test_the_package_carries_no_walker_module` (`:75`), checked by both import failure and
on-disk layout. That absence is the test, not a comment.

The count test compares an alias-carrying class against its alias-free twin — an **equality
between the pair**, never an absolute count — which is precisely why all five survived this
plan's disposition change unmodified. matriz's copy carries the extra `__dataclass_fields__`
`ClassVar` handling that 35-04 pinned as an equality against that single known extra.

---

## Handoff to Phase 39

The accounting artefact is
**`.planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md`**
(plan 35-02). It is the middle term of Phase 39's subtraction: it states, per package and per
field, exactly which census tuples the NOBJ-02 disposition just stopped emitting, so the
post-milestone drop in divergences is *accounted for* rather than read as a clean bill of
health it did not earn.

| Paquete | Field rows | Retired (distinct triples) | Retired (records) |
|---|---:|---:|---:|
| `higyrus-client` | 11 | 2 | 2 |
| `iol-client` | none — no floor exists; see the ledger's explicit reasoned row | none | none |
| `market-data-client` | 8 | none retired — the 8 rows intersect no ratified floor | none retired |
| `matriz-client` | 16 | 5 | 6 |
| `ambito-financiero-client` | none — declares no models (D-05) | none | none |
| `wallets-client` | none — declares no models and no walker (D-05) | none | none |

**The unit warning, repeated because it is where this subtraction goes wrong.** The ledger
counts **distinct 4-tuples** `(slug, model, field_path, kind)`. The ratified floors in
`29-SIZING.md` are **sums of records over corpus files**. Subtracting across the two columns
invents a shortfall that is not there. matriz is the concrete demonstration rather than a
hypothetical: its answer is **6 against the records floor and 5 against distinct triples**,
because one link is a single triple recorded in two corpus files. Any subtraction that does
not name its column will be wrong by one for matriz.

Two further hazards the ledger records and Phase 39 must carry:

- **Kind mismatch against `29-SIZING.md`.** Its corpus run predates WR-02, so it labels
  matriz's five model-link records `non_dict` attributed to the *nested* class, while the
  shipped walker labelled the same wire `missing` attributed to the *outer* model. Two of the
  four tuple components differ for those rows: match on `(slug, field_path)` and read `kind`
  from the ledger.
- **Two inherited live blocks.** `LIVE-HIGY-33` (the higyrus host does not resolve by DNS from
  this network) and `LIVE-MATZ-33` (the remarkets-only policy assert in `main_matriz.py`,
  which is **not** to be routed around — matriz's surface includes order entry). Both must be
  recorded `SKIPPED` with measured cause and named destination, never as a count that reads
  as clean (precedent D-13 / 33-05).
- **Phases 36-38 are out of this ledger's scope.** Their new non-`Optional` links retire
  further tuples that belong to their own phases' accounting, and market-data's live census of
  24 tuples is untouched by NOBJ-02 — any drop there must be attributed to fixes, never to
  this policy.

---

## Prohibitions — Verified

| Prohibition | Status | Evidence |
|---|---|---|
| No gate is weakened to make this land | **verified** | `git diff --stat tools/check_decode_intactness.py` → 1 insertion, 1 deletion, on the pin line. `git diff --exit-code pyproject.toml .github/workflows/ci.yml tools/check_uniform_structure.py tools/check_surface_types.py tools/surface_parity.py` → exit 0. |
| No test is edited beyond the 11 named assertions | **verified** | Phase-wide `git diff --numstat` over test files shows deletions in exactly six files; every deletion is one of the eleven assertions or its name/docstring. No seventh file. |
| The silencing never extends beyond a null value | **verified** | The gate reads `if value is not None:` — an identity check against the null singleton, present exactly once per copy. The 10 wrong-type tests, which use non-list and `""`-class wrong values, are green. |
| The new `CANONICAL_DIGEST` is never predicted, authored, or copied from RESEARCH | **verified** | Read verbatim from the gate's failure message, quoted above. `grep -c "cd937d17..."` (the RESEARCH F-6 value) in the gate script returns nothing; the pinned value differs from it. |
| The whole of Task 1 is one commit | **verified** | `git log --oneline -1 --name-only` on `ece3a3c` lists all twelve files; `git log -1 --name-only --format="" \| grep -c .` returns **12**. |
| No file under `packages/`, `tools/` or `verification/` modified by Task 2 | **verified** | `git status --porcelain` after the gate shows an empty worktree; the only new file is this SUMMARY under `.planning/`. |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] the module docstring's reporting bullet rotted with the change**

- **Found during:** Task 1, Step 3's mandated manual review of the five module docstrings
  (D-10: comments are hashed, module docstrings are not and get reviewed by hand ×5).
- **Issue:** All five copies' module docstrings claim, under "The two behaviours the walker
  adds over `_coerce`", that reporting is *"a sink call immediately before every substituted
  default"*. After EDIT 1 and EDIT 2 that is false in exactly the two cases NOBJ-02 carves
  out. Leaving it would have shipped a false document at the top of the very file the phase
  exists to change — and the whole point of the manual ×5 review is to catch this.
- **Fix:** The bullet was amended, byte-identically in all five copies, to name the carve-out
  and to restate that a wrong-typed value on either site still reports and is still fatal
  under strict mode. Because normalization rule 1 strips the module docstring, the amendment
  **does not move the digest** — verified: the digest the gate computed was the same before
  and after the docstring edit.
- **Files modified:** the five `_decode.py` copies.
- **Commit:** `ece3a3c` (inside the atomic commit, as it must be).

### Scope Decisions Recorded Rather Than Acted On

**The `WR-02` section header above the inverted test was left unedited in all five
`test_decode.py` files.** It reads
`# Phase 29 code review, WR-02 — an absent nested-model key is `missing``, and its second
clause is no longer true of what the walker emits. It was **not** edited because doing so
would have produced a deletion not attributable to the eleven named assertions or their
names and docstrings, which is exactly what the plan's diff-accounting prohibition forbids.
The section still correctly introduces WR-02's *classification order*, which remains
load-bearing, and it also introduces `test_non_dict_nested_payload_keeps_the_nested_attribution`,
which is unchanged. Flagged here so a later reader corrects it deliberately rather than
discovering it as a surprise.

**No comment was added at the list site.** The plan prescribes the comment rewrite at the
model site only. The identity-versus-truthiness constraint is enforced by the ten wrong-type
tripwires and by the per-copy acceptance grep, not by prose.

### Authentication Gates

None — this plan makes no network calls.

---

## Known Stubs

None.

## Threat Flags

None. The register's rows are discharged or accepted as planned:

- **T-35-13** (reduced observability) — **accepted**, bounded by construction and by test. The
  silence applies only to an identity match against the null singleton on a field the
  annotation declares non-optional. A wrong string, an empty dict, a zero and an empty list
  all still emit and all stay fatal under `strict_decode`, because the raise is downstream of
  the sink and the sink is still called for them.
- **T-35-14** (silencing over-reaching from "is null" to "is falsy") — **mitigated**: the gate
  is an identity check, the acceptance grep requires exactly one per copy, and the ten
  wrong-type tests are green.
- **T-35-15** (silently weakening a CI gate) — **mitigated**: one insertion and one deletion on
  the pin line; the other three gate scripts, `pyproject.toml` and `ci.yml` byte-unchanged;
  the pin differs from the RESEARCH digest, which is what proves it was recomputed.
- **T-35-16** (a partial landing leaving the gate red on a pushed commit) — **mitigated**: all
  twelve files in the single commit `ece3a3c`.
- **T-35-17** (wire-derived strings reaching the log sink) — **accepted, unchanged**.
  `_safe_key` neutralisation, the 64-character key cap, the per-triple dedupe and the
  never-raise guarantee of the emitter are all outside the two edited branches and are
  byte-untouched.
- **T-35-SC** (dependency tampering) — **verified**: no installs anywhere;
  `git diff --exit-code pyproject.toml uv.lock packages/*/pyproject.toml` exits 0.

**ASVS L1:** no `high`-severity finding. The change narrows one observability path
deliberately, measurably and falsifiably, and touches none of the four input-handling
controls in the walker.

---

## Commits

| Task | Commit | Description |
|---|---|---|
| 1 | `ece3a3c` | `feat(35-05)`: EDIT 1 + EDIT 2 ×5, the byte-identical disposition comment, the 11 inversions and the recomputed `CANONICAL_DIGEST` — twelve files, one commit |
| 2 | *(this SUMMARY)* | `docs(35-05)`: the phase gate and its captured evidence |

**Reversibility:** two-way door. No public signature, no return value and no wire behaviour
changed — only what the divergence channel records. Reverting is a `git revert` of `ece3a3c`;
the digest bump follows the code back automatically.

## Self-Check: PASSED

- `.planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-05-SUMMARY.md` — FOUND
- The five `_decode.py` copies — FOUND, each containing `Phase 35, NOBJ-02` and
  `if value is not None:` exactly once
- `tools/check_decode_intactness.py` — FOUND, containing
  `CANONICAL_DIGEST = "a1f00c824348164cb04c086993826c0050d6d344fcdaf778a37112751bc97e1f"`
- `packages/market-data-client/tests/test_core.py` — FOUND, containing
  `test_health_from_api_missing_auth_yields_zero_valued_nested_model`
- Commit `ece3a3c` — FOUND, listing twelve files
