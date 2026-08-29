"""RED fixture for GATE-TYP-01's FIELD dimension (Phase 37, NOBJ-MTZ-01).

The sibling module ``packages/iol-client/tests/test_surface_types_red.py`` proves
the gate's *return-annotation* dimension is not vacuous. This module proves the
same thing for the *field-annotation* dimension added in Phase 37 -- and that
proof was overdue: before Phase 37 the gate printed ``0 violations`` while five
``dict[str, Any]`` fields sat on matriz's exported model surface, because
``_candidates_for`` only ever produced ``FunctionDef``/``AsyncFunctionDef`` nodes
and dropped every ``AnnAssign`` in a class body. A gate that structurally cannot
see the thing it claims to check is green for the wrong reason.

It lives under ``packages/matriz-client/tests/`` for exactly the reason the iol
module lives under ``packages/iol-client/tests/``: that path is collected by the
6x2 CI test matrix and typechecked by the per-package mypy loop, while
``verification/`` has **never executed in CI** -- the ``test`` job passes an
explicit ``packages/<pkg>`` path on the pytest command line, which overrides
``[tool.pytest.ini_options] testpaths``. A non-vacuity proof parked in a
directory CI does not run is not a proof of anything.

It **mirrors** the iol module rather than importing from it. Factoring
``_write_fake_package`` into a shared helper would be this repo's first
cross-package test dependency, and the repo has none by design (the same reason
``_decode.py`` is replicated byte-verbatim instead of extracted).

No mypy or CLI subprocess is spawned, and no fixture tree is committed under
``packages/``. Both were deliberately rejected: a subprocess would buy nothing
the in-process call already gives, and a committed fake package would enter
``check_decode_intactness.py``'s Check D roster and would owe
``check_uniform_structure.py`` a ``models.py`` and a ``types.py``, turning two
unrelated gates red for a directory that is not a real package.

THE INJECTABLE-ROOT SEAM (D-04)
===============================

The gate is testable at all only because ``REPO_ROOT`` in
``tools/check_surface_types.py`` is a **default argument value** rather than a
constant referenced from inside the check body. That single departure from the
two pre-existing gates is what lets a synthetic tree under ``tmp_path`` be
injected as ``root``.

THE THREE PROPERTIES THIS MODULE PINS
=====================================

1. **Non-vacuity.** A reintroduced untyped mapping field on an exported class
   reddens, and the message names the qualified ``Class.field`` pair.
2. **Narrowness (D-01b).** ``list[Any]`` does NOT redden. The field predicate is
   deliberately narrower than ``_annotation_mentions_any``: a wide predicate
   would redden two exported fields in a package this phase declared disjoint
   and out of scope. Narrowness is a *contract*, not an accident, so it gets its
   own test rather than being left to chance.
3. **Exemption reachability (D-01c/D-01d).** The single declared field exemption
   absorbs a genuine hit -- it is counted by name in ``exempted_by_reason`` --
   and it is keyed on the qualified class-and-field pair, so the same field name
   on a different class still reddens.

``tools.check_surface_types`` imports from a package test because the repo root
is on ``sys.path`` (``pythonpath = ["."]`` at ``pyproject.toml``); ``tools/`` has
no ``__init__.py`` and resolves as an implicit namespace package. A side effect
worth naming: ``tools/*.py`` is outside mypy's global ``files``, so this import
is what enrols the gate in the per-package strict typecheck.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tools.check_surface_types import CheckFailure, check_surface_types, scan_surface_types

# Derived independently of the gate's own ``REPO_ROOT``: this module asserts
# *about* the gate, so it must not borrow the constant it is checking.
_REPO_ROOT = Path(__file__).resolve().parents[3]

_UNTYPED_MAPPING = "dict[str, Any]"

#: The reason string the one declared field exemption flows into. Spelled out
#: here rather than imported from the gate for the same reason ``_REPO_ROOT`` is
#: re-derived: a test that borrows the constant it checks cannot detect a
#: rename that silently empties the exemption.
_CATCH_ALL_REASON = "ws-catch-all"


def _write_fake_package(
    root: Path,
    *,
    init_source: str,
    client_source: str,
    extra_modules: dict[str, str] | None = None,
) -> None:
    """Materialise ``<root>/packages/fake-client/src/fake_client/`` on disk.

    Factored out so the synthetic cases below differ only in the source strings
    that matter, never in ``mkdir`` plumbing. ``extra_modules`` maps a submodule
    name to its source, for the cases that need a re-export intermediary.
    """
    pkg = root / "packages" / "fake-client" / "src" / "fake_client"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text(init_source, encoding="utf-8")
    (pkg / "client.py").write_text(client_source, encoding="utf-8")
    for name, source in (extra_modules or {}).items():
        (pkg / f"{name}.py").write_text(source, encoding="utf-8")


def _model_package(root: Path, *, class_name: str, body: str) -> None:
    """A synthetic package exporting one dataclass whose body is ``body``.

    Every field case below is the same package with a different annotation, so
    the surrounding ``@dataclass`` / ``__all__`` / import plumbing is written
    once. ``body`` is inserted verbatim at four-space indentation depth already
    applied by the caller.
    """
    _write_fake_package(
        root,
        init_source=(
            f"from fake_client.client import {class_name}\n\n__all__ = ['{class_name}']\n"
        ),
        client_source=(
            "from dataclasses import dataclass, field\n"
            "from typing import Any, Optional\n"
            "\n"
            "\n"
            "class Level:\n"
            "    pass\n"
            "\n"
            "\n"
            "@dataclass(frozen=True)\n"
            f"class {class_name}:\n"
            f"{body}"
        ),
    )


# ----------------------------------------------------------------------
# 1. Non-vacuity -- the property that did NOT hold before Phase 37
# ----------------------------------------------------------------------


def test_reintroduced_untyped_mapping_field_is_caught(tmp_path: Path) -> None:
    """Lower bound: an exported class field annotated ``dict[str, Any]`` reddens.

    This is the assertion the whole field dimension exists for. Before Phase 37
    this exact tree scanned green, because the candidate collector filtered a
    class body down to its member functions and discarded every ``AnnAssign``.
    """
    _model_package(tmp_path, class_name="Thing", body=f"    payload: {_UNTYPED_MAPPING}\n")

    with pytest.raises(CheckFailure, match=r"Thing\.payload"):
        check_surface_types(root=tmp_path)


def test_reverting_tick_price_ranges_to_its_pre_phase_form_reddens(tmp_path: Path) -> None:
    """The phase's own regression, re-enacted synthetically rather than in the tree.

    Plans 37-02/03 retyped matriz's untyped mapping fields; this asserts the
    gate would have caught them. The revert is performed on a synthetic copy
    under ``tmp_path`` -- never by editing the real tree, which would leave the
    repository red between the edit and the revert and would make the assertion
    order-dependent.
    """
    _model_package(
        tmp_path,
        class_name="InstrumentDetail",
        body=(
            "    symbol: str | None = None\n"
            f"    tickPriceRanges: {_UNTYPED_MAPPING} = field(default_factory=dict)\n"
        ),
    )

    with pytest.raises(CheckFailure, match=r"InstrumentDetail\.tickPriceRanges"):
        check_surface_types(root=tmp_path)


def test_bare_any_field_is_caught(tmp_path: Path) -> None:
    """A bare ``Any`` is the degenerate untyped surface, and is in scope too.

    ``payload: Any`` states strictly less than ``dict[str, Any]``. A predicate
    that caught only the mapping shape would leave the wider hole open.
    """
    _model_package(tmp_path, class_name="Thing", body="    payload: Any\n")

    with pytest.raises(CheckFailure, match=r"Thing\.payload"):
        check_surface_types(root=tmp_path)


def test_optional_untyped_mapping_field_is_caught(tmp_path: Path) -> None:
    """The predicate strips the optional wrapper before matching (RESEARCH A2).

    Nothing exported carries ``dict[str, Any] | None`` today, so this choice is
    unobservable on the real tree -- it only makes the ratchet stricter. Leaving
    the hole open would have made ``| None`` a one-token bypass of the gate.
    Both spellings are exercised: the PEP 604 union and ``Optional[...]``.
    """
    _model_package(
        tmp_path, class_name="Thing", body=f"    payload: {_UNTYPED_MAPPING} | None = None\n"
    )
    with pytest.raises(CheckFailure, match=r"Thing\.payload"):
        check_surface_types(root=tmp_path)

    _model_package(
        tmp_path, class_name="Thing", body=f"    payload: Optional[{_UNTYPED_MAPPING}] = None\n"
    )
    with pytest.raises(CheckFailure, match=r"Thing\.payload"):
        check_surface_types(root=tmp_path)


def test_conditionally_declared_field_is_scanned(tmp_path: Path) -> None:
    """A field declared under ``if`` in a class body is not in ``node.body``.

    The field collector reuses ``_module_level_statements`` for exactly the
    reason the function collector does (CR-01 shape 2): a version-guarded
    declaration is still part of the exported surface.
    """
    _write_fake_package(
        tmp_path,
        init_source="from fake_client.client import Thing\n\n__all__ = ['Thing']\n",
        client_source=(
            "import sys\n"
            "from dataclasses import dataclass\n"
            "from typing import Any\n"
            "\n"
            "\n"
            "@dataclass(frozen=True)\n"
            "class Thing:\n"
            "    name: str = ''\n"
            "\n"
            "    if sys.version_info >= (3, 12):\n"
            f"        payload: {_UNTYPED_MAPPING} | None = None\n"
        ),
    )

    with pytest.raises(CheckFailure, match=r"Thing\.payload"):
        check_surface_types(root=tmp_path)


def test_a_typed_mapping_field_does_not_trip_the_gate(tmp_path: Path) -> None:
    """The upper bound of the field predicate: a typed mapping is the fix, not the bug.

    ``dict[str, Level]`` is exactly the shape Plans 37-02/03 migrated the real
    fields to. A predicate that reddened it would make the ratchet unsatisfiable
    and would be reverted rather than obeyed.
    """
    _model_package(
        tmp_path,
        class_name="Thing",
        body="    payload: dict[str, Level] = field(default_factory=dict)\n",
    )

    result = scan_surface_types(tmp_path)

    assert result.violations == ()
    assert result.fields == 1


# ----------------------------------------------------------------------
# 2. Narrowness (D-01b) -- what keeps this phase inside its blast radius
# ----------------------------------------------------------------------


def test_a_list_of_any_field_is_spared_keeping_the_narrow_predicate_narrow(
    tmp_path: Path,
) -> None:
    """D-01b in executable form: ``list[Any]`` must NOT redden.

    The field predicate is deliberately NOT ``_annotation_mentions_any``, the
    wide predicate the return dimension uses. Widening it would immediately
    redden two *exported* fields in ``market-data-client`` --
    ``CalendarConfig.warnings`` and ``CalendarConfigPreview.warnings``, both
    ``list[Any]`` -- a package Phase 37 declared disjoint and out of scope.

    Ratchet discipline says a red gate is never resolved by weakening the gate;
    the corollary D-01b adds is that an out-of-scope red is resolved by
    NARROWING the predicate, never by exempting the foreign field and never by
    editing the foreign package. This test is what stops a later contributor
    from "tightening" the predicate and silently pulling a disjoint package into
    this phase's blast radius.
    """
    _model_package(tmp_path, class_name="CalendarConfig", body="    warnings: list[Any] = ()\n")

    result = scan_surface_types(tmp_path)

    assert result.violations == ()
    assert result.fields == 1


def test_any_nested_deeper_inside_a_typed_container_is_spared(tmp_path: Path) -> None:
    """Only the two declared shapes match; a mention of ``Any`` is not enough.

    ``list[dict[str, Any]]`` and ``dict[str, list[Any]]`` both mention ``Any``,
    and the wide return predicate would flag both. The field predicate matches
    the annotation's own shape, not its subtree, so neither reddens.
    """
    _model_package(
        tmp_path,
        class_name="Thing",
        body=(f"    rows: list[{_UNTYPED_MAPPING}] = ()\n    buckets: dict[str, list[Any]] = ()\n"),
    )

    result = scan_surface_types(tmp_path)

    assert result.violations == ()
    assert result.fields == 2


# ----------------------------------------------------------------------
# 3. Exemption reachability and qualification (D-01c / D-01d)
# ----------------------------------------------------------------------


def test_the_catch_all_frame_exemption_absorbs_a_real_hit_and_is_counted(
    tmp_path: Path,
) -> None:
    """The one declared field exemption is proven reachable, not dead code.

    The synthetic field is a genuine *hit* -- it matches the predicate -- so the
    exemption is what stops it, and it is counted under its own reason string.
    An exemption that never fires is unfalsifiable: it could be misspelled, or
    keyed on a class that no longer exists, and nothing would say so.
    """
    _model_package(
        tmp_path,
        class_name="UnknownFrame",
        body=(
            "    type: str | None = None\n"
            f"    raw: {_UNTYPED_MAPPING} = field(default_factory=dict)\n"
        ),
    )

    result = scan_surface_types(tmp_path)

    assert result.violations == ()
    assert result.fields == 2
    assert dict(result.exempted_by_reason)[_CATCH_ALL_REASON] == 1


def test_the_field_exemption_is_qualified_not_a_bare_member_name(tmp_path: Path) -> None:
    """The same field name on a different class still reddens (D-01c).

    Attribution by the simple member name is ``_is_exempt``'s documented design
    and is why the exemption could not be added there: ``raw`` is a plausible
    member name in six packages, and a bare-name entry would spare all of them.
    """
    _model_package(
        tmp_path,
        class_name="SomeOtherFrame",
        body=f"    raw: {_UNTYPED_MAPPING} = field(default_factory=dict)\n",
    )

    with pytest.raises(CheckFailure, match=r"SomeOtherFrame\.raw"):
        check_surface_types(root=tmp_path)


def test_a_private_field_is_absorbed_by_the_existing_taxonomy(tmp_path: Path) -> None:
    """``_is_exempt`` still applies to fields, after the qualified table misses.

    An underscore-prefixed field is not part of the exported surface for the
    same reason an underscore-prefixed method is not, so the field dimension
    reuses the existing reason rather than inventing a parallel one.
    """
    _model_package(tmp_path, class_name="Thing", body=f"    _cache: {_UNTYPED_MAPPING} = ()\n")

    result = scan_surface_types(tmp_path)

    assert result.violations == ()
    assert dict(result.exempted_by_reason)["private-helper"] == 1


# ----------------------------------------------------------------------
# 4. Upper bound -- the real tree, floors only
# ----------------------------------------------------------------------


def test_the_field_dimension_is_green_and_non_trivial_on_the_real_tree() -> None:
    """The extension did not redden the committed tree, and it saw real work.

    Every count is a **floor**, never an equality: a seventh package or a newly
    exported model must be able to raise the numbers without falsely reddening
    the suite. Floors still catch the failure that matters -- a dimension that
    collapses to zero scanned fields and reports green anyway, which is
    precisely the state the gate was in before Phase 37.
    """
    summary = check_surface_types()
    assert "0 violation" in summary
    assert "fields scanned" in summary

    result = scan_surface_types(_REPO_ROOT)
    assert result.violations == ()
    assert result.packages >= 6
    assert result.definitions >= 300
    assert result.exempted >= 20
    assert result.fields >= 1
