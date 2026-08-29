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


def _model_package(root: Path, *, class_name: str, body: str, extra_imports: str = "") -> None:
    """A synthetic package exporting one dataclass whose body is ``body``.

    Every field case below is the same package with a different annotation, so
    the surrounding ``@dataclass`` / ``__all__`` / import plumbing is written
    once. ``body`` is inserted verbatim at four-space indentation depth already
    applied by the caller.

    ``extra_imports`` is appended to the import block for the cases that name a
    symbol the default block does not (``Union``, ``Mapping``, ``defaultdict``).
    The gate never imports or executes this source -- it parses it -- so an
    undefined name would not have failed anything; the parameter exists so a
    reader of the fixture is not left staring at source that could not run.
    """
    _write_fake_package(
        root,
        init_source=(
            f"from fake_client.client import {class_name}\n\n__all__ = ['{class_name}']\n"
        ),
        client_source=(
            "from dataclasses import dataclass, field\n"
            "from typing import Any, Optional\n"
            f"{extra_imports}"
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


def test_union_spelled_optional_untyped_mapping_field_is_caught(tmp_path: Path) -> None:
    """The THIRD spelling of optional, missed until the Phase 37 code review (CR-02).

    ``_strip_optional`` handled ``X | None`` and ``Optional[X]`` but not
    ``Union[X, None]``, so the very bypass its docstring claimed to have closed
    was open under one more import. The review executed the predicate and
    measured ``'Union[dict[str, Any], None]' -> False``.

    The runtime counterpart ``matriz_client.models._strip_optional`` accepts
    ``typing.Union`` and always did, so this was also a gate/runtime disagreement
    about what "optional" means -- the kind of drift that makes a green gate
    unreadable as evidence.
    """
    _model_package(
        tmp_path,
        class_name="Thing",
        body=f"    payload: Union[{_UNTYPED_MAPPING}, None] = None\n",
        extra_imports="from typing import Union\n",
    )

    with pytest.raises(CheckFailure, match=r"Thing\.payload"):
        check_surface_types(root=tmp_path)


def test_a_nested_untyped_mapping_value_is_caught(tmp_path: Path) -> None:
    """``dict[str, dict[str, Any]]`` reddens -- the shape THIS phase introduced (CR-02).

    ``DetailedPosition.report`` is ``dict[str, dict[str, InstrumentPositionReport]]``.
    Until the code review the predicate tested only ``_is_any(parameters[1])``,
    so an author who typed the OUTER level and left the inner one ``Any`` --
    the single most likely partial migration of exactly this field -- shipped
    green. The predicate now recurses through the mapping value parameter.
    """
    _model_package(
        tmp_path,
        class_name="Thing",
        body=f"    report: dict[str, {_UNTYPED_MAPPING}] = field(default_factory=dict)\n",
    )

    with pytest.raises(CheckFailure, match=r"Thing\.report"):
        check_surface_types(root=tmp_path)


def test_a_quoted_untyped_mapping_annotation_is_caught(tmp_path: Path) -> None:
    """A string annotation parses to ``ast.Constant`` and used to short-circuit (CR-02).

    ``payload: "dict[str, Any]"`` is legal Python and ordinary for forward refs.
    ``_base_name`` answered ``None`` for the ``Constant`` node, so the predicate
    returned ``False`` on an annotation stating exactly as little as the one it
    catches. Both the fully quoted form and the partially quoted
    ``dict[str, "Any"]`` are exercised; the recursion handles the second for free
    once the string arm exists.
    """
    _model_package(tmp_path, class_name="Thing", body='    payload: "dict[str, Any]" = None\n')
    with pytest.raises(CheckFailure, match=r"Thing\.payload"):
        check_surface_types(root=tmp_path)

    _model_package(tmp_path, class_name="Thing", body='    payload: dict[str, "Any"] = None\n')
    with pytest.raises(CheckFailure, match=r"Thing\.payload"):
        check_surface_types(root=tmp_path)


def test_a_bare_unparameterised_mapping_field_is_caught(tmp_path: Path) -> None:
    """Plain ``dict`` states LESS than ``dict[str, Any]`` yet used to be spared (CR-02).

    The predicate required an ``ast.Subscript``, so the unparameterised base fell
    straight through. WR-02 covers the other half of this shape's cost: at
    runtime ``models._is_mapping(dict)`` was ``False``, so the field also skipped
    the ``{}`` fallback, the element decode and the divergence report.
    """
    _model_package(tmp_path, class_name="Thing", body="    payload: dict = None\n")

    with pytest.raises(CheckFailure, match=r"Thing\.payload"):
        check_surface_types(root=tmp_path)


def test_an_aliased_mapping_base_is_caught(tmp_path: Path) -> None:
    """The alias vocabulary is exercised, not merely declared (CR-02).

    ``_MAPPING_BASES`` lists the aliases so "the ratchet cannot be bypassed by
    spelling the same untyped mapping as ``Mapping[str, Any]``", but nothing
    proved the claim. ``defaultdict`` was added to the set by the same review:
    it is a mapping that says exactly as little as ``dict`` about its values, and
    leaving it out left the bypass open under a different import.
    """
    _model_package(
        tmp_path,
        class_name="Thing",
        body="    payload: Mapping[str, Any] = None\n",
        extra_imports="from collections.abc import Mapping\n",
    )
    with pytest.raises(CheckFailure, match=r"Thing\.payload"):
        check_surface_types(root=tmp_path)

    _model_package(
        tmp_path,
        class_name="Thing",
        body="    payload: defaultdict[str, Any] = None\n",
        extra_imports="from collections import defaultdict\n",
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
    annotated ``list[Any]`` -- a package Phase 37 declared disjoint and out of
    scope. Those are the two declarations reproduced below, on classes of the
    same names, so the shape this test protects is the real one rather than a
    paraphrase of it. Measured, not assumed: the extended gate was run over the
    committed tree and reported 0 violations with both fields in place.

    Ratchet discipline says a red gate is never resolved by weakening the gate;
    the corollary D-01b adds is that an out-of-scope red is resolved by
    NARROWING the predicate, never by exempting the foreign field and never by
    editing the foreign package. This test is what stops a later contributor
    from "tightening" the predicate and silently pulling a disjoint package into
    this phase's blast radius -- the widening would look like a strictly better
    gate right up until CI reddened on a package nobody in this phase touched.
    """
    _write_fake_package(
        tmp_path,
        init_source=(
            "from fake_client.client import CalendarConfig, CalendarConfigPreview\n\n"
            "__all__ = ['CalendarConfig', 'CalendarConfigPreview']\n"
        ),
        client_source=(
            "from dataclasses import dataclass\n"
            "from typing import Any\n"
            "\n"
            "\n"
            "@dataclass(frozen=True)\n"
            "class CalendarConfig:\n"
            "    source: str\n"
            "    warnings: list[Any]\n"
            "\n"
            "\n"
            "@dataclass(frozen=True)\n"
            "class CalendarConfigPreview:\n"
            "    valid: bool\n"
            "    warnings: list[Any]\n"
        ),
    )

    result = scan_surface_types(tmp_path)

    assert result.violations == ()
    assert result.fields == 4
    assert result.exempted == 0


def test_any_nested_deeper_inside_a_typed_container_is_spared(tmp_path: Path) -> None:
    """A mention of ``Any`` is not enough; only the MAPPING spine is walked.

    ``list[dict[str, Any]]`` and ``dict[str, list[Any]]`` both mention ``Any``,
    and the wide return predicate would flag both. Neither reddens: the field
    predicate descends only through the value parameter of a mapping base, and a
    ``list`` is not one.

    Phase 37 code review, CR-02, sharpened this from "matches the annotation's
    own shape, not its subtree" to the statement above. The predicate now DOES
    recurse -- ``dict[str, dict[str, Any]]`` reddens, which is what closes the
    hole this phase's own container shape sat in -- and the reason ``list[Any]``
    survives that recursion is the mapping-only descent, not the absence of any
    descent at all. The distinction is load-bearing for D-01b: it is what keeps
    ``market-data-client``'s two exported ``list[Any]`` fields out of this
    phase's blast radius.
    """
    _model_package(
        tmp_path,
        class_name="Thing",
        body=(f"    rows: list[{_UNTYPED_MAPPING}] = ()\n    buckets: dict[str, list[Any]] = ()\n"),
    )

    result = scan_surface_types(tmp_path)

    assert result.violations == ()
    assert result.fields == 2


def test_a_fully_typed_nested_mapping_is_spared_by_the_recursion(tmp_path: Path) -> None:
    """The recursion's upper bound: ``dict[str, dict[str, Level]]`` stays green (CR-02).

    This is ``DetailedPosition.report``'s real shape. The recursion added by the
    code review must catch the partially-migrated form
    (``dict[str, dict[str, Any]]``) without reddening the finished one -- a
    predicate that flagged both would make the phase's own deliverable
    unsatisfiable and would be reverted rather than obeyed.
    """
    _model_package(
        tmp_path,
        class_name="Thing",
        body="    report: dict[str, dict[str, Level]] = field(default_factory=dict)\n",
    )

    result = scan_surface_types(tmp_path)

    assert result.violations == ()
    assert result.fields == 1


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

    The field floor is the measured 442 minus a deliberate margin, chosen the
    same way the 300-definition floor was: large enough that a resolution
    regression silently halving the scanned population fails here, loose enough
    that deleting a model or narrowing a package's ``__all__`` does not.

    The exemption floor stays at 20 rather than rising to 24. The one field
    exemption is asserted BY NAME in the reachability test above, which is a
    stronger statement than a bumped total: a total can be satisfied by any
    four exemptions, a named count only by the one this phase declared.
    """
    summary = check_surface_types()
    assert "0 violation" in summary
    assert "fields scanned" in summary

    result = scan_surface_types(_REPO_ROOT)
    assert result.violations == ()
    assert result.packages >= 6
    assert result.definitions >= 300
    assert result.exempted >= 20
    assert result.fields >= 350
    assert dict(result.exempted_by_reason)[_CATCH_ALL_REASON] == 1
