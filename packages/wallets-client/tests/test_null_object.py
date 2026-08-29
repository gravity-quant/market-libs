"""Null Object contract for ``wallets_client`` — NOBJ-01, Phase 35.

ROADMAP Phase 35 criterio 1 asks the six paquetes of this workspace to answer
the truthiness question. This paquete's answer is that it has **no response
model to ask**: it is still a stub with no verifiable endpoints and no declared
response shapes, so there is nothing here to be falsy (D-05).

That zero is asserted below as a POSITIVE structural property — no class
definitions, an empty ``__all__``, an import-free module, and no walker module
in the paquete at all — rather than left as an absence nobody checks. An empty
``parametrize`` list is skipped by pytest in silence, and a lower bound that any
roster whatsoever satisfies proves nothing; neither shortcut is used here.

The import-discipline assertion is the load-bearing one, and it is specific to
this paquete. There is no ``_decode.py`` here (the exemption is written up in
``.planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md``), so a base
class copied in to make the six paquetes look more uniform than they are would
raise ``ImportError`` the moment the paquete is imported and take every one of
its CI matrix legs with it. A cosmetically-uniform paquete that cannot be
imported trades a documented gap for a hidden outage.

The third test makes the *reason* the first two are the whole of this paquete's
contribution executable rather than a comment: no walker module means no
divergence records to compare, so the alias-invisibility pair and the wrong-type
falsification tests the other paquetes carry genuinely cannot exist here. The
day a ``_decode.py`` appears, that test reddens and this file must be revisited
— which is precisely the day this paquete stops being exempt.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import pathlib

import pytest

from wallets_client import models


def test_the_package_declares_no_response_models_by_decision() -> None:
    """D-05: the emptiness is a decision, and this is where it is executable.

    Two independent statements of the same property, because either one alone
    could be satisfied by an accident: the shipped module's AST carries zero
    class definitions, and its ``__all__`` is the empty list so nothing is
    published from it.
    """
    source = pathlib.Path(inspect.getfile(models)).read_text(encoding="utf-8")
    tree = ast.parse(source)

    classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    assert classes == []

    assert models.__all__ == []


def test_the_models_module_imports_nothing_beyond_the_future_flag() -> None:
    """The import discipline here is structural, not stylistic.

    This paquete carries no walker module, so a base copied in for cosmetic
    uniformity across the six paquetes would fail at package-import time and
    redden every leg of this paquete's CI matrix. Pinning the import list is how
    that stays a decision rather than a thing someone undoes in passing.
    """
    source = pathlib.Path(inspect.getfile(models)).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = [n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)]

    assert [n.module for n in imported if isinstance(n, ast.ImportFrom)] == ["__future__"]
    assert [n for n in imported if isinstance(n, ast.Import)] == []


def test_the_package_carries_no_walker_module() -> None:
    """The exemption itself, asserted rather than assumed.

    The other paquetes prove the ``@property`` alias invariant and the
    wrong-typed-list falsification against their own walker copy. Neither test
    can exist here, and this is why: there is no walker module to drive. Both
    the import and the on-disk layout are checked, so neither a stale
    ``__pycache__`` entry nor a file added without an import can hide the change.

    If this ever reddens, the exemption has ended and the two tests above stop
    being the whole of this paquete's contribution to criterio 1.
    """
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("wallets_client._decode")

    package_dir = pathlib.Path(inspect.getfile(models)).parent
    assert not (package_dir / "_decode.py").exists()
