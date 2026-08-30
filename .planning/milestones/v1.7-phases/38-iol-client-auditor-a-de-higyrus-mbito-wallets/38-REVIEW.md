---
phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets
reviewed: 2026-08-29T21:16:55Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - packages/iol-client/src/iol_client/models.py
  - packages/iol-client/tests/test_models.py
  - packages/iol-client/tests/test_null_object.py
  - verification/snapshots/iol-client-surface.txt
  - tools/check_surface_types.py
  - packages/iol-client/tests/test_surface_types_red.py
  - packages/iol-client/README.md
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: issues_found
---

# Phase 38: Code Review Report

**Reviewed:** 2026-08-29T21:16:55Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

This phase flips `Cotizacion.puntas` (`list[Punta] | None` -> `list[Punta]`) and
`Titulo.puntas` (`Punta | None` -> `Punta`) to the Null Object pattern, updates
the docs/tests/surface snapshot accordingly, and adds a new D-11 gate dimension
to `tools/check_surface_types.py` that reddens any exported field re-declaring
an optional model link.

I re-derived every factual claim in the extensive `models.py` docstrings
against the live `_decode.py` walker (the NOBJ-02 collapse arms at the cited
line ranges, the `Union` early-return, the `list`-branch `sink()` guard) and
found no discrepancy — the prose is accurate. I ran the full test suite for
the three test files (`56 passed`), `ruff check`, and `mypy --strict` on all
five source/tool files reviewed — all clean. Field-position claims
("position 16 of 20 / four no-default fields after it", "position 14 of 20 /
six after it") were counted by hand against the actual dataclass field order
and are correct. The `to_dict()` round-trip lossiness the tests assert
(`puntas: null` on the wire -> `puntas: []` in `to_dict()`) is consistent with
`dataclasses.asdict` semantics and is exercised by
`test_round_trip_reproduce_el_schema_committeado_de_serie_historica`.

The one issue found is in the new D-11 gate predicate
(`_field_annotation_is_optional_model` in `tools/check_surface_types.py`): its
`list[Model] | None` arm does not re-parse a quoted (forward-referenced) model
name inside the list subscript, unlike its own bare-model arm and unlike the
sibling `_field_annotation_is_untyped_mapping` predicate it explicitly claims
to mirror ("reproduces the mapping predicate's two structural habits"). This
creates a narrow but real silent gap in a gate whose entire stated purpose is
to make silent gaps impossible (see the module's own CR-01 history). I
verified the gap directly by calling the predicate with a synthetic
`list["Punta"] | None` annotation (see below) — it currently returns `False`
(spared) where the equivalent unquoted form `list[Punta] | None` correctly
returns `True`. No such quoted shape exists anywhere in the six packages
today, so nothing in production is currently mis-scanned, and this is
classified as a Warning rather than a Blocker.

## Warnings

### WR-01: D-11 optional-model-link predicate does not re-parse a quoted model name inside `list[...]`

**File:** `tools/check_surface_types.py:799-875` (`_field_annotation_is_optional_model`, the `list` arm around line 870-874)
**Issue:**

`_field_annotation_is_optional_model` handles three "quoted annotation" cases —
the whole annotation quoted, the inner arm of the union quoted, and (via
delegation to `_strip_optional`) the `Union[X, None]` spelling — but its final
`list[Model] | None` branch reads the list's element type directly without
checking whether that element is itself a quoted string:

```python
if isinstance(inner, ast.Subscript) and _base_name(inner.value) == "list":
    # Spelled as the builtin only, matching the two real fields and RESEARCH
    # F-6's measurement. No `typing.List[Model] | None` exists in the tree,
    # and there is no `_MAPPING_BASES`-style alias set to bypass here.
    return _base_name(inner.slice) in class_names
return False
```

`_base_name` only understands `ast.Name` / `ast.Attribute`; for a quoted
element (`ast.Constant` holding a string) it returns `None`, so
`None in class_names` is always `False` regardless of what the quoted string
names. Reproduced directly:

```python
>>> import ast
>>> from tools.check_surface_types import _field_annotation_is_optional_model
>>> src = ast.parse('list["Punta"] | None', mode="eval").body
>>> _field_annotation_is_optional_model(src, frozenset({"Punta"}))
False   # should be True -- this is exactly the Titulo/Cotizacion shape 38-01 removed
>>> src2 = ast.parse('list[Punta] | None', mode="eval").body
>>> _field_annotation_is_optional_model(src2, frozenset({"Punta"}))
True    # unquoted form is caught correctly
```

By contrast, `_field_annotation_is_untyped_mapping` (the sibling predicate this
one's docstring explicitly claims to reproduce — "It reproduces the mapping
predicate's two structural habits -- a quoted annotation is re-parsed and
judged...") *does* handle this recursively: each recursive call re-enters the
function, which re-checks for a quoted `Constant` at its own top before
testing `_is_any`/mapping-base membership. `_field_annotation_is_optional_model`
has no equivalent recursive re-entry for its `list` arm, so the claimed parity
with the mapping predicate is not actually true for this one shape.

The gate is a ratchet whose sole stated job (per its own module docstring,
Section "RESOLUTION IS TRANSITIVE, AND UNRESOLVED IS A PROBLEM") is to make
exactly this class of silent miss impossible — CR-01 in Phase 32 was a
previous instance of the same failure mode (a resolvable case that quietly
produced zero findings instead of a violation). Nothing in the current six
packages triggers this gap (no field is annotated with a quoted list element
today, and it's an unusual thing to write given the mandatory
`from __future__ import annotations`), so this is not an active production
defect — but a future contributor who reintroduces an optional model link
using a quoted forward reference inside a `list[...]` (plausible when working
around definition order, e.g. two models referencing each other) would
silently defeat the D-11 ratchet with no test or CI signal.

**Fix:** Re-parse the list element the same way the bare-model arm already
does, before testing membership:

```python
if isinstance(inner, ast.Subscript) and _base_name(inner.value) == "list":
    elem = inner.slice
    if isinstance(elem, ast.Constant) and isinstance(elem.value, str):
        try:
            elem = ast.parse(elem.value, mode="eval").body
        except SyntaxError:
            return True  # an uninspectable annotation is not a spared one
    return _base_name(elem) in class_names
return False
```

Add a red-fixture test alongside the existing D-11 pair in
`packages/iol-client/tests/test_surface_types_red.py` asserting that
`list["Leaf"] | None` reddens the same way `list[Leaf] | None` does, and
correct (or remove) the docstring's "reproduces the mapping predicate's two
structural habits" claim if the fix is not applied, so the documented
guarantee matches the actual behavior.

---

_Reviewed: 2026-08-29T21:16:55Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
