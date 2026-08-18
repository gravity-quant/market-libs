"""Binds ``market_data_client.__version__`` to the packaging metadata (WR-04).

The version lives in TWO hand-edited places — ``pyproject.toml:[project].version``
and ``__init__.__version__`` — and the publish gate (``release.yml``) validates
only the former against the git tag. Nothing structurally prevents a release that
edits ``pyproject.toml`` alone from shipping a wheel whose
``importlib.metadata.version("market-data-client")`` and
``market_data_client.__version__`` disagree — a lie in exactly the field consumers
quote in bug reports.

This net closes that hole from both sides:

(a) ``__version__`` equals the version declared in this package's ``pyproject.toml``
    (read via ``tomllib`` from the package directory, so it works from a source
    checkout regardless of how the package was installed);
(b) ``__version__`` equals the INSTALLED distribution metadata, which is what a
    consumer holding only the wheel actually observes.
"""

from __future__ import annotations

import pathlib
import tomllib
from importlib.metadata import version as _dist_version

import market_data_client

_PYPROJECT = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"


def _declared_version() -> str:
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    declared: str = data["project"]["version"]
    return declared


def test_pyproject_is_readable_from_the_package_dir() -> None:
    """Guard the fixture itself: a moved/renamed pyproject must fail loudly."""
    assert _PYPROJECT.is_file(), f"expected a pyproject.toml at {_PYPROJECT}"
    assert _declared_version()


def test_dunder_version_matches_pyproject() -> None:
    """``__init__.__version__`` must not drift from the packaged version."""
    assert market_data_client.__version__ == _declared_version(), (
        "market_data_client.__version__ "
        f"({market_data_client.__version__!r}) != pyproject [project].version "
        f"({_declared_version()!r}) — update BOTH when bumping a release."
    )


def test_dunder_version_matches_installed_distribution_metadata() -> None:
    """What a consumer sees via ``importlib.metadata`` must agree too."""
    assert market_data_client.__version__ == _dist_version("market-data-client")
