"""RED fixture for GATE-TYP-01: the surface-type gate must be provably non-vacuous.

This file lives under ``packages/iol-client/tests/`` for exactly the reason
``test_typed_surface_red.py`` (the phase-30 precedent beside it) does: that path
is collected by the 6x2 CI test matrix and typechecked by the per-package mypy
loop, while ``verification/`` has **never executed in CI** -- the ``test`` job
passes an explicit ``packages/<pkg>`` path on the pytest command line, which
overrides ``[tool.pytest.ini_options] testpaths``. A non-vacuity proof parked in
a directory CI does not run is not a proof of anything.

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
injected as ``root`` -- and it is precisely why neither of those two gates has a
test today.

THE TWO BOUNDS ARE COMPLEMENTARY; NEITHER ALONE IS A PROOF
==========================================================

``test_gate_is_green_on_the_real_tree`` is the **upper bound**: the six packages
carry zero non-exempt hits today (research measured 319 definitions, 22 exempt,
0 violations), so a gate that reddens them is over-eager and would be reverted
rather than obeyed.

``test_gate_fails_on_an_injected_regression`` is the **lower bound**: a gate
that reports green on a deliberately broken tree is vacuous. A vacuous AST guard
is the failure mode postmortemed in this repo at
``.planning/milestones/v1.2-phases/15-driver-migration-4-refac-05/15-REVIEW.md``
WR-01/WR-02, and it is the one this file exists to make impossible. Because the
tree is already clean, the gate's entire value is the day it turns red; the
lower bound is the only evidence that day will ever arrive.

``tools.check_surface_types`` imports from a package test because the repo root
is on ``sys.path`` (``pythonpath = ["."]`` at ``pyproject.toml``, "Patron 1");
``tools/`` has no ``__init__.py`` and resolves as an implicit namespace package.
A side effect worth naming: ``tools/*.py`` is outside mypy's global ``files``,
so this import is what enrols the gate in the per-package strict typecheck.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tools.check_surface_types import CheckFailure, check_surface_types, scan_surface_types

# Derived independently of the gate's own ``REPO_ROOT``: this module asserts
# *about* the gate, so it must not borrow the constant it is checking.
_REPO_ROOT = Path(__file__).resolve().parents[3]

_UNTYPED_MAPPING_RETURN = "dict[str, Any]"


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


def test_gate_is_green_on_the_real_tree() -> None:
    """Upper bound: the committed tree scans clean, and the scan is not trivial.

    Every count is asserted as a **floor**, never an equality: a seventh package
    or a newly exported model must not falsely redden the suite. Floors still
    catch the failure that matters here -- a scan that collapses to nothing and
    reports green anyway.

    The ``fields`` floor is the second dimension's half of that proof and is what
    makes "green AND non-vacuous on the real tree" executable rather than a
    SUMMARY claim. The committed tree scans 442 fields (RESEARCH F-6, cross-checked
    against the gate's own ``442 fields scanned`` line), so 400 is a floor with
    headroom that still catches a field scan collapsing to nothing -- the exact
    state this file's gate was in before Phase 37, when it reported green with
    five untyped mapping fields on an exported surface.
    """
    summary = check_surface_types()
    assert "0 violation" in summary

    result = scan_surface_types(_REPO_ROOT)
    assert result.violations == ()
    assert result.packages >= 6
    assert result.definitions >= 300
    assert result.fields >= 400
    assert result.exempted >= 20


def test_gate_fails_on_an_injected_regression(tmp_path: Path) -> None:
    """Lower bound (non-vacuity): a module-level exported offender must redden.

    This is the assertion that makes the whole gate worth committing. Without
    it, a gate that returned green unconditionally would be indistinguishable
    from the real one on today's clean tree.
    """
    _write_fake_package(
        tmp_path,
        init_source="from fake_client.client import get_thing\n\n__all__ = ['get_thing']\n",
        client_source=(
            "from typing import Any\n"
            "\n"
            "\n"
            f"def get_thing() -> {_UNTYPED_MAPPING_RETURN}:\n"
            "    return {}\n"
        ),
    )

    with pytest.raises(CheckFailure, match="get_thing"):
        check_surface_types(root=tmp_path)


def test_regression_inside_an_exported_class_is_caught(tmp_path: Path) -> None:
    """D-03 in executable form: methods of exported classes are in scope.

    The likeliest real regression is not a new module-level function but a new
    ``Client.get_x()`` returning an untyped mapping. A gate that walked only
    module-level definitions would miss it -- and would also miss the single
    underscore-exempt hit research measured, which is reachable *only* as a
    method.
    """
    _write_fake_package(
        tmp_path,
        init_source="from fake_client.client import Client\n\n__all__ = ['Client']\n",
        client_source=(
            "from typing import Any\n"
            "\n"
            "\n"
            "class Client:\n"
            f"    def get_thing(self) -> {_UNTYPED_MAPPING_RETURN}:\n"
            "        return {}\n"
        ),
    )

    with pytest.raises(CheckFailure, match=r"Client\.get_thing"):
        check_surface_types(root=tmp_path)


def test_exempt_members_do_not_trip_the_gate(tmp_path: Path) -> None:
    """The DT-06 taxonomy is load-bearing and each reason is provably reachable.

    All three exempt shapes return an untyped mapping, so each one is a genuine
    *hit* that the exemption absorbs -- not a definition that never qualified.
    Counting them by reason is what stops the exemption predicate being widened
    silently to swallow a real violation.
    """
    _write_fake_package(
        tmp_path,
        init_source="from fake_client.client import Client\n\n__all__ = ['Client']\n",
        client_source=(
            "from typing import Any\n"
            "\n"
            "\n"
            "class Client:\n"
            f"    def to_dict(self) -> {_UNTYPED_MAPPING_RETURN}:\n"
            "        return {}\n"
            "\n"
            f"    def __reduce__(self) -> {_UNTYPED_MAPPING_RETURN}:\n"
            "        return {}\n"
            "\n"
            f"    def _helper(self) -> {_UNTYPED_MAPPING_RETURN}:\n"
            "        return {}\n"
            "\n"
            "    def get_name(self) -> str:\n"
            "        return ''\n"
        ),
    )

    result = scan_surface_types(tmp_path)

    assert result.violations == ()
    assert result.definitions == 4
    assert result.exempted == 3
    assert dict(result.exempted_by_reason) == {
        "dunder": 1,
        "private-helper": 1,
        "serialize-out": 1,
    }


def test_alias_reexport_is_scanned_not_silently_skipped(tmp_path: Path) -> None:
    """CR-01 shape 1: ``import Client as FakeClient`` must still scan ``Client``.

    The bound name is ``FakeClient`` and the ``ClassDef`` is named ``Client``, so
    a resolver that keys only on the bound name finds zero candidates and -- in
    the first cut of this gate -- recorded nothing and reported nothing. The
    whole class, every method, scanned green with ``dict[str, Any]`` in place.
    """
    _write_fake_package(
        tmp_path,
        init_source=(
            "from fake_client.client import Client as FakeClient\n\n__all__ = ['FakeClient']\n"
        ),
        client_source=(
            "from typing import Any\n"
            "\n"
            "\n"
            "class Client:\n"
            f"    def get_thing(self) -> {_UNTYPED_MAPPING_RETURN}:\n"
            "        return {}\n"
        ),
    )

    with pytest.raises(CheckFailure, match=r"Client\.get_thing"):
        check_surface_types(root=tmp_path)


def test_conditionally_defined_export_is_scanned(tmp_path: Path) -> None:
    """CR-01 shape 2: a definition under ``if``/``try`` is not in ``tree.body``.

    Both containers are exercised, because both are plausible in real source: a
    version-guarded ``class`` and a ``try: ... except ImportError:`` fallback
    ``def``. Iterating ``tree.body`` alone sees neither.
    """
    _write_fake_package(
        tmp_path,
        init_source=(
            "from fake_client.client import Client, get_thing\n\n"
            "__all__ = ['Client', 'get_thing']\n"
        ),
        client_source=(
            "import sys\n"
            "from typing import Any\n"
            "\n"
            "if sys.version_info >= (3, 12):\n"
            "\n"
            "    class Client:\n"
            f"        def get_conditional(self) -> {_UNTYPED_MAPPING_RETURN}:\n"
            "            return {}\n"
            "\n"
            "try:\n"
            "    import json\n"
            "except ImportError:  # pragma: no cover\n"
            "    json = None\n"
            "\n"
            "\n"
            f"def get_thing() -> {_UNTYPED_MAPPING_RETURN}:\n"
            "    return {}\n"
        ),
    )

    with pytest.raises(CheckFailure, match=r"Client\.get_conditional"):
        check_surface_types(root=tmp_path)


def test_all_augmented_assignment_names_are_scanned(tmp_path: Path) -> None:
    """CR-01 shape 3: ``__all__ += [...]`` is an ``ast.AugAssign``.

    The first cut handled ``Assign`` and ``AnnAssign`` and *returned at the first
    match*, so every name appended this way was exported, never scanned, and
    never reported -- the gate printed "1 definitions scanned, 0 violations".
    """
    _write_fake_package(
        tmp_path,
        init_source=(
            "from fake_client.client import get_a, get_b\n\n"
            "__all__ = ['get_a']\n"
            "__all__ += ['get_b']\n"
        ),
        client_source=(
            "from typing import Any\n"
            "\n"
            "\n"
            "def get_a() -> str:\n"
            "    return ''\n"
            "\n"
            "\n"
            f"def get_b() -> {_UNTYPED_MAPPING_RETURN}:\n"
            "    return {}\n"
        ),
    )

    with pytest.raises(CheckFailure, match="get_b"):
        check_surface_types(root=tmp_path)


def test_starred_all_element_is_a_failure_not_a_silent_drop(tmp_path: Path) -> None:
    """A non-``Constant`` ``__all__`` element makes the surface unreadable.

    ``__all__ = ['get_a', *models.__all__]`` passed the "is a list literal" check
    and then dropped the starred names in silence. The gate cannot know what is
    exported, and guessing "nothing" is the vacuity this file exists to prevent.
    """
    _write_fake_package(
        tmp_path,
        init_source=(
            "from fake_client import models\n"
            "from fake_client.client import get_a\n\n"
            "__all__ = ['get_a', *models.__all__]\n"
        ),
        client_source="def get_a() -> str:\n    return ''\n",
        extra_modules={"models": "__all__ = ['Thing']\n\n\nclass Thing:\n    pass\n"},
    )

    with pytest.raises(CheckFailure, match="non-literal element"):
        scan_surface_types(tmp_path)


def test_reexport_through_an_intermediate_is_followed_to_the_definition(tmp_path: Path) -> None:
    """A chain ``__init__`` -> ``shim`` -> ``client`` resolves, and still reddens.

    This is the shape live in the tree today (matriz publishes two constants
    through ``ws_client``, which only re-imports them from ``types``). Treating
    the first hop as authoritative would take the class's entire method surface
    out of the gate; treating a first-hop miss as a *problem* would falsely
    redden a correct tree. The chain is therefore followed.
    """
    _write_fake_package(
        tmp_path,
        init_source="from fake_client.shim import Client\n\n__all__ = ['Client']\n",
        client_source=(
            "from typing import Any\n"
            "\n"
            "\n"
            "class Client:\n"
            f"    def get_thing(self) -> {_UNTYPED_MAPPING_RETURN}:\n"
            "        return {}\n"
        ),
        extra_modules={"shim": "from fake_client.client import Client\n\n__all__ = ['Client']\n"},
    )

    with pytest.raises(CheckFailure, match=r"Client\.get_thing"):
        check_surface_types(root=tmp_path)


def test_a_dead_ended_export_chain_is_a_problem_not_a_skip(tmp_path: Path) -> None:
    """An export whose resolved module never binds the name must redden.

    This is CR-01's root cause stated positively: the collection step used to
    record nothing when zero candidates matched, and nothing was appended to
    ``problems``. Every *other* unresolvable condition in the gate is a problem;
    this one has to be too, or "an export the gate cannot inspect" stays silent.
    """
    _write_fake_package(
        tmp_path,
        init_source="from fake_client.shim import Client\n\n__all__ = ['Client']\n",
        client_source="class Client:\n    def get_thing(self) -> str:\n        return ''\n",
        extra_modules={"shim": "SOMETHING_ELSE = 1\n"},
    )

    with pytest.raises(CheckFailure, match="never a skip"):
        scan_surface_types(tmp_path)


def test_constant_exports_are_counted_rather_than_absorbed(tmp_path: Path) -> None:
    """A ``Literal`` alias or constant resolves to an assignment, and says so.

    It carries no return annotation, so it is neither a definition nor a
    violation -- but it must be *reported* as a resolved constant rather than
    vanish, otherwise "resolved to nothing" and "resolved to a constant" are the
    same green.
    """
    _write_fake_package(
        tmp_path,
        init_source=(
            "from fake_client.client import DEFAULT_MODE, get_thing\n\n"
            "__all__ = ['DEFAULT_MODE', 'get_thing']\n"
        ),
        client_source=(
            "DEFAULT_MODE: str = 'strict'\n\n\ndef get_thing() -> str:\n    return ''\n"
        ),
    )

    result = scan_surface_types(tmp_path)

    assert result.violations == ()
    assert result.definitions == 1
    assert result.assignments == 1


def test_empty_and_unresolvable_trees_are_failures_not_greens(tmp_path: Path) -> None:
    """An empty or unresolvable scan is a FAILURE, never a silent green.

    Three sub-cases, each of which a naively written gate would report as
    "nothing wrong found": no packages at all, a package with no import root,
    and a package that declares no module-level ``__all__``. Reporting green on
    any of them is the exact failure this phase exists to prevent.
    """
    empty = tmp_path / "empty-packages"
    (empty / "packages").mkdir(parents=True)
    with pytest.raises(CheckFailure, match="zero package directories"):
        scan_surface_types(empty)

    no_src = tmp_path / "no-src"
    (no_src / "packages" / "fake-client").mkdir(parents=True)
    with pytest.raises(CheckFailure, match="no resolvable import root"):
        scan_surface_types(no_src)

    no_all = tmp_path / "no-all"
    _write_fake_package(
        no_all,
        init_source="from fake_client.client import get_thing\n",
        client_source="def get_thing() -> str:\n    return ''\n",
    )
    with pytest.raises(CheckFailure, match="__all__"):
        scan_surface_types(no_all)


# ----------------------------------------------------------------------
# The OPTIONAL-MODEL-LINK field predicate (Phase 38, D-11)
#
# One redden-side bound and two spare-side bounds. The pair is the point: a
# predicate proven only to redden can be over-eager, and a predicate proven only
# to spare can be vacuous. Both halves were measured over all six packages before
# either was written (RESEARCH F-6).
# ----------------------------------------------------------------------


def test_an_optional_model_field_is_caught(tmp_path: Path) -> None:
    """Lower bound for D-11: an optional model link on an exported field reddens.

    Two shapes on one class, because the ratchet owes both. ``Thing.link``
    reproduces ``Titulo.puntas`` -- the bare ``Punta | None`` form -- and
    ``Thing.links`` reproduces ``Cotizacion.puntas`` -- the
    ``list[Punta] | None`` form. Those are the two fields plan 38-01 flipped to
    Null Objects, and they are the ONLY two sites the widened predicate reddens:
    the discriminator was implemented and executed over all six packages during
    research and reported exactly 2 hits, both in ``iol-client``, with zero
    collateral anywhere else (F-6).

    Both shapes are asserted, not just the bare one. Catching ``Punta | None``
    and missing ``list[Punta] | None`` would leave half the regression this gate
    exists to stop wide open -- and the list form is the one that shipped first.

    ``Leaf`` is deliberately NOT in ``__all__``. The classifier walks every
    ``.py`` under the package's import root rather than resolving through the
    exported surface, so an internal model is still a model; resolving through
    ``__all__`` would have spared this exact fixture.
    """
    _write_fake_package(
        tmp_path,
        init_source="from fake_client.client import Thing\n\n__all__ = ['Thing']\n",
        client_source=(
            "from dataclasses import dataclass\n"
            "\n"
            "\n"
            "@dataclass(frozen=True)\n"
            "class Leaf:\n"
            "    price: float = 0.0\n"
            "\n"
            "\n"
            "@dataclass(frozen=True)\n"
            "class Thing:\n"
            "    link: Leaf | None = None\n"
            "    links: list[Leaf] | None = None\n"
        ),
    )

    with pytest.raises(CheckFailure, match=r"Thing\.link"):
        check_surface_types(root=tmp_path)

    result = scan_surface_types(tmp_path)

    assert len(result.violations) == 2


def test_a_quoted_list_model_element_is_caught(tmp_path: Path) -> None:
    """WR-01 (Phase 38 code review): a quoted element inside ``list[...]`` must redden too.

    ``_field_annotation_is_optional_model``'s bare-model arm and its docstring
    both claim parity with ``_field_annotation_is_untyped_mapping``'s "re-parse a
    quoted annotation" habit, but the ``list[Model] | None`` arm read the list's
    element type directly without checking whether that element was itself a
    quoted string (``ast.Constant``). ``_base_name`` answers ``None`` for a
    ``Constant``, so ``list["Leaf"] | None`` silently spared where the unquoted
    ``list[Leaf] | None`` correctly reddened -- exactly the ``Titulo``/``Cotizacion``
    shape 38-01 removed, reintroduced behind a forward reference inside the
    ``list[...]`` subscript rather than around the whole annotation (the
    already-covered outer-quote case in ``test_an_optional_model_field_is_caught``).
    """
    _write_fake_package(
        tmp_path,
        init_source="from fake_client.client import Thing\n\n__all__ = ['Thing']\n",
        client_source=(
            "from dataclasses import dataclass\n"
            "\n"
            "\n"
            "@dataclass(frozen=True)\n"
            "class Leaf:\n"
            "    price: float = 0.0\n"
            "\n"
            "\n"
            "@dataclass(frozen=True)\n"
            "class Thing:\n"
            "    links: list['Leaf'] | None = None\n"
        ),
    )

    with pytest.raises(CheckFailure, match=r"Thing\.links"):
        check_surface_types(root=tmp_path)

    result = scan_surface_types(tmp_path)

    assert len(result.violations) == 1


def test_an_optional_literal_alias_field_is_spared(tmp_path: Path) -> None:
    """Narrowness pin: a ``Literal`` alias is not a model, so ``Mode | None`` stays green.

    This is what keeps ``matriz-client`` -- a package this phase declared
    disjoint -- outside the widened predicate's blast radius. Ten exported fields
    there carry an optional module-level ``Literal`` alias, at
    ``packages/matriz-client/src/matriz_client/models.py`` lines 532, 552, 553,
    561, 607, 619, 660, 661, 662 and 669. The count is **10**, not the 11 that
    ``38-CONTEXT.md``'s D-11 records: RESEARCH F-9/A1 re-ran both the grep and the
    AST scan and both contradict the CONTEXT figure.

    Those leaves are legal by policy, not by oversight. D-NO-03 permits a
    scalar-set leaf -- ``T | None`` where ``T`` is an enum-like alias -- to stay
    optional; the Null Object rule governs MODEL links. The discriminator
    separates the two structurally rather than by roster: ``Mode`` is bound by a
    module-level ``Assign`` and ``Leaf`` by a ``class`` statement, and only the
    latter is in the ``ClassDef``-name set.

    Ratchet discipline, restated because this is the test that enforces it: an
    out-of-scope red is resolved by NARROWING the predicate, never by exempting
    the foreign field and never by editing the foreign package.

    The field is asserted COUNTED as well as spared. A spare that disappeared
    from the census would be indistinguishable from a blind scan.
    """
    _write_fake_package(
        tmp_path,
        init_source="from fake_client.client import Thing\n\n__all__ = ['Thing']\n",
        client_source=(
            "from dataclasses import dataclass\n"
            "from typing import Literal\n"
            "\n"
            "Mode = Literal['a', 'b']\n"
            "\n"
            "\n"
            "@dataclass(frozen=True)\n"
            "class Thing:\n"
            "    mode: Mode | None = None\n"
        ),
    )

    result = scan_surface_types(tmp_path)

    assert result.violations == ()
    assert result.fields == 1


def test_an_optional_list_of_any_field_is_spared(tmp_path: Path) -> None:
    """RESEARCH F-6 note 4: ``list[Any] | None`` must still be green after the widening.

    ``Any`` is bound by no ``class`` statement, so the discriminator spares this
    shape structurally rather than by special case: ``_base_name`` answers
    ``None`` for a subscript, and the ``list[...]`` arm only matches when its own
    slice names a class. "Structurally" is a claim, though, and the fields it
    protects sit in a package this phase does not own -- ``CalendarConfig.warnings``
    and ``CalendarConfigPreview.warnings`` in ``market-data-client``, both
    annotated ``list[Any]`` and both put out of scope by Phase 37's D-01b. So the
    claim is pinned here rather than left to a red CI run on a foreign package.

    Counted as well as spared, for the reason the ``Literal`` pin states.
    """
    _write_fake_package(
        tmp_path,
        init_source="from fake_client.client import Thing\n\n__all__ = ['Thing']\n",
        client_source=(
            "from dataclasses import dataclass\n"
            "from typing import Any\n"
            "\n"
            "\n"
            "@dataclass(frozen=True)\n"
            "class Thing:\n"
            "    warnings: list[Any] | None = None\n"
        ),
    )

    result = scan_surface_types(tmp_path)

    assert result.violations == ()
    assert result.fields == 1
