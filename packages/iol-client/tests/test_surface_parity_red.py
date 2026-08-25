"""RED fixture for ``tools/surface_parity.py``: the parity gate must bound below.

``tools/check_surface_types.py`` ships with ``test_surface_types_red.py`` beside
it; ``tools/surface_parity.py`` shipped with **nothing**. Its six in-package hook
files (``packages/<pkg>/tests/test_surface_parity.py``) are the *upper* bound --
they assert the real tree agrees today. Nothing asserted the gate would notice if
it stopped agreeing, which is the failure mode the module's own docstring calls
"a gate quietly relaxed until it passes".

Every case below fails against the gate as first shipped and passes against the
fixed one. They are added alongside the fixes they bound, so each one names the
Phase 32 review finding it is the executable form of.

WHY THIS FILE LIVES IN ``packages/iol-client/tests/``
=====================================================

Same reason as ``test_surface_types_red.py`` next to it: this path is collected
by the 6x2 CI test matrix and typechecked by the per-package mypy loop, while
``verification/`` has never executed in the CI ``test`` job. A non-vacuity proof
parked in a directory CI does not run proves nothing.

It asserts about ``tools/surface_parity.py`` and about **no** iol-client
behaviour, and the trees it examines are synthesised under ``tmp_path``, so it
adds no cross-package coupling to this package's suite.

WHY THE FIXTURES ARE REAL IMPORTABLE MODULES
============================================

``tools/surface_parity.py`` resolves hints at runtime with
``typing.get_type_hints``, deliberately (see its ``WHY THIS HELPER IMPORTS
PACKAGE MODULES`` section). A synthetic tree therefore has to be *importable*,
not merely parseable, so each case writes a two-module package under ``tmp_path``
and puts it on ``sys.path`` for the duration of the test.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

import pytest
from tools.surface_parity import class_parity_report

# A module-level `from __future__ import annotations` is what forces the gate to
# resolve hints rather than string-match them, so every fixture carries it: the
# fixtures must have the same shape as the real modules under test.
_FUTURE = "from __future__ import annotations\n"


class _SurfacePairFactory(Protocol):
    """Materialise an importable ``<package>.client`` / ``<package>.aio`` pair."""

    def __call__(self, package: str, *, client_source: str, aio_source: str) -> str: ...


@pytest.fixture
def surface_pair(tmp_path: Path) -> Iterator[_SurfacePairFactory]:
    """Yield the factory, then unwind ``sys.path`` and ``sys.modules``.

    Teardown is not optional bookkeeping: these fixtures are *imported*, so a
    leaked entry would let one case resolve another case's modules and quietly
    change what the next assertion is about.
    """
    created: list[str] = []

    def _make(package: str, *, client_source: str, aio_source: str) -> str:
        pkg = tmp_path / package
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "client.py").write_text(_FUTURE + client_source, encoding="utf-8")
        (pkg / "aio.py").write_text(_FUTURE + aio_source, encoding="utf-8")
        created.append(package)
        return package

    sys.path.insert(0, str(tmp_path))
    try:
        yield _make
    finally:
        sys.path.remove(str(tmp_path))
        for package in created:
            for name in [n for n in sys.modules if n == package or n.startswith(f"{package}.")]:
                del sys.modules[name]


def _class_mismatches(package: str) -> str:
    return "\n".join(class_parity_report(package).hint_mismatches)


def test_constructor_drift_is_reported(surface_pair: _SurfacePairFactory) -> None:
    """CR-02: ``__init__`` is hidden by the underscore filter and must be re-added.

    The shape is the live one the review measured: an ``AsyncClient`` that
    accepts an injected transport and a ``Client`` that cannot. A consumer
    writing symmetric sync/async code gets ``TypeError: __init__() got an
    unexpected keyword argument 'http_client'`` on the sync side, and the gate
    added specifically to make that impossible to keep reported green.
    """
    package = surface_pair(
        "fake_ctor_drift",
        client_source=(
            "class Client:\n"
            "    def __init__(self, *, base_url: str | None = None) -> None:\n"
            "        self.base_url = base_url\n"
            "\n"
            "    def close(self) -> None:\n"
            "        return None\n"
        ),
        aio_source=(
            "class AsyncClient:\n"
            "    def __init__(\n"
            "        self, *, base_url: str | None = None, http_client: object | None = None\n"
            "    ) -> None:\n"
            "        self.base_url = base_url\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        return None\n"
        ),
    )

    mismatches = _class_mismatches(package)

    assert "Client.__init__" in mismatches
    assert "http_client" in mismatches


def test_agreeing_constructors_are_not_reported(surface_pair: _SurfacePairFactory) -> None:
    """The complement of the case above: rule 5 must not be over-eager.

    Without this leg a gate that flagged ``__init__`` unconditionally would be
    indistinguishable from one that compares it correctly, and the five
    class-bearing packages would be red for no reason.

    ``compared_hints`` is asserted alongside the agreement, because agreement
    over an empty comparison is the vacuity the whole module exists to prevent.
    """
    package = surface_pair(
        "fake_ctor_agree",
        client_source=(
            "class Client:\n"
            "    def __init__(self, *, base_url: str | None = None) -> None:\n"
            "        self.base_url = base_url\n"
            "\n"
            "    def close(self) -> None:\n"
            "        return None\n"
        ),
        aio_source=(
            "class AsyncClient:\n"
            "    def __init__(self, *, base_url: str | None = None) -> None:\n"
            "        self.base_url = base_url\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        return None\n"
        ),
    )

    report = class_parity_report(package)

    assert report.hint_mismatches == ()
    assert report.compared_hints >= 2, "`__init__` was not counted among the compared members"


def test_reordered_and_rekinded_parameters_are_reported(
    surface_pair: _SurfacePairFactory,
) -> None:
    """WR-01: ``get_type_hints`` is an unordered ``name -> type`` map, nothing more.

    It carries no parameter *kind*, no *default*, no ``*args``/``**kwargs`` and
    no ordering. The review reproduced the consequence against the shipped
    helper: a function reordered, defaulted, and made keyword-only compared
    EQUAL to its counterpart. That is precisely the drift the gate claims to
    freeze.
    """
    package = surface_pair(
        "fake_signature_drift",
        client_source=(
            "class Client:\n"
            "    def __init__(self) -> None:\n"
            "        return None\n"
            "\n"
            "    def get_quote(self, symbol: str, mercado: str = 'bcba') -> str:\n"
            "        return symbol\n"
            "\n"
            "    def close(self) -> None:\n"
            "        return None\n"
        ),
        aio_source=(
            "class AsyncClient:\n"
            "    def __init__(self) -> None:\n"
            "        return None\n"
            "\n"
            "    async def get_quote(self, mercado: str, *, symbol: str = 'x') -> str:\n"
            "        return symbol\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        return None\n"
        ),
    )

    mismatches = _class_mismatches(package)

    assert "Client.get_quote" in mismatches
    assert "parameter list differs" in mismatches
    assert "kind differs" in mismatches


def test_default_value_drift_is_reported(surface_pair: _SurfacePairFactory) -> None:
    """WR-01, the consequential half: same names, same order, different default.

    ``mercado: str = 'bcba'`` on one surface and ``'nyse'`` on the other is
    invisible to an annotation-only comparison and changes what the two surfaces
    *do* -- the same blind spot as the reordering above, with real consequences.
    """
    package = surface_pair(
        "fake_default_drift",
        client_source=(
            "class Client:\n"
            "    def __init__(self) -> None:\n"
            "        return None\n"
            "\n"
            "    def get_quote(self, *, mercado: str = 'bcba') -> str:\n"
            "        return mercado\n"
            "\n"
            "    def close(self) -> None:\n"
            "        return None\n"
        ),
        aio_source=(
            "class AsyncClient:\n"
            "    def __init__(self) -> None:\n"
            "        return None\n"
            "\n"
            "    async def get_quote(self, *, mercado: str = 'nyse') -> str:\n"
            "        return mercado\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        return None\n"
        ),
    )

    mismatches = _class_mismatches(package)

    assert "Client.get_quote" in mismatches
    assert "default differs" in mismatches
    assert "bcba" in mismatches
    assert "nyse" in mismatches


def test_no_default_never_compares_equal_to_a_none_default(
    surface_pair: _SurfacePairFactory,
) -> None:
    """A required parameter and one defaulting to ``None`` are not the same surface.

    Both annotate ``str | None``, so the hint halves agree exactly. Only the
    signature half can tell them apart, and rendering "no default" as a distinct
    sentinel rather than as ``None`` is what makes that possible.
    """
    package = surface_pair(
        "fake_required_drift",
        client_source=(
            "class Client:\n"
            "    def __init__(self) -> None:\n"
            "        return None\n"
            "\n"
            "    def get_quote(self, *, mercado: str | None) -> str:\n"
            "        return mercado or ''\n"
            "\n"
            "    def close(self) -> None:\n"
            "        return None\n"
        ),
        aio_source=(
            "class AsyncClient:\n"
            "    def __init__(self) -> None:\n"
            "        return None\n"
            "\n"
            "    async def get_quote(self, *, mercado: str | None = None) -> str:\n"
            "        return mercado or ''\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        return None\n"
        ),
    )

    report = class_parity_report(package)
    mismatches = "\n".join(report.hint_mismatches)

    assert "default differs" in mismatches, (
        "a required parameter compared equal to one defaulting to None -- "
        "the two surfaces do not accept the same calls"
    )
