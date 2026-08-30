---
phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets
fixed_at: 2026-08-29T21:20:42Z
review_path: .planning/phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-REVIEW.md
iteration: 1
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 38: Code Review Fix Report

**Fixed at:** 2026-08-29T21:20:42Z
**Source review:** .planning/phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 1
- Fixed: 1
- Skipped: 0

## Fixed Issues

### WR-01: D-11 optional-model-link predicate does not re-parse a quoted model name inside `list[...]`

**Files modified:** `tools/check_surface_types.py`, `packages/iol-client/tests/test_surface_types_red.py`
**Commit:** b2b06ff
**Applied fix:** Confirmed the source code matched the review's cited state exactly
(the `list` arm of `_field_annotation_is_optional_model` at
`tools/check_surface_types.py:870-874` read `inner.slice` directly through
`_base_name`, which returns `None` for a quoted `ast.Constant` element,
silently sparing shapes like `list["Punta"] | None`). Applied the review's
suggested fix verbatim: before testing membership, check whether the list's
element (`inner.slice`) is an `ast.Constant` string; if so, re-parse it via
`ast.parse(elem.value, mode="eval").body` (treating a `SyntaxError` during
re-parse as a violation, matching the sibling `_field_annotation_is_untyped_mapping`
predicate's existing "uninspectable annotation is not a spared one" convention),
then test `_base_name(elem) in class_names`.

Also added the red-fixture regression test the review requested
(`test_a_quoted_list_model_element_is_caught` in
`packages/iol-client/tests/test_surface_types_red.py`, placed alongside the
existing D-11 pair), asserting that `list['Leaf'] | None` reddens the D-11 gate
the same way the already-covered unquoted `list[Leaf] | None` form does. The
review's alternative option — correcting the docstring's "reproduces the
mapping predicate's two structural habits" claim instead of fixing the code —
was not needed since the code fix now makes that claim true.

**Verification performed:**
- Functionally reproduced the review's exact repro: `_field_annotation_is_optional_model(ast.parse('list["Punta"] | None', mode="eval").body, frozenset({"Punta"}))` now returns `True` (was `False`); the unquoted form `list[Punta] | None` continues to return `True`.
- `ruff check` on both modified files: clean.
- `mypy --strict` on both modified files: clean.
- Full `test_surface_types_red.py` suite: 16 passed (15 pre-existing + 1 new).
- `test_models.py` + `test_null_object.py`: 41 passed, unaffected by this change.

## Skipped Issues

None — the only in-scope finding was fixed.

---

_Fixed: 2026-08-29T21:20:42Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
