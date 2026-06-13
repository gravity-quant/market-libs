"""Cross-cutting WR-06 regression guard — ``max_retries`` kwarg validated everywhere.

Phase 8 code review WR-06 flagged that ``Client(max_retries=-5)`` and
``Client(max_retries=1.5)`` constructed successfully (or with a confusing
tenacity error later). The fix adds ``_validate_max_retries(value)`` to each
package's ``client.py`` (and re-imported by ``aio.py``) and calls it inside
every ``Client.__init__`` / ``AsyncClient.__init__`` / ``configure()`` /
``aio.configure()`` entry point.

The guard checks that **every** entry point on **every** package rejects:

- Negative ints (``max_retries=-1``)
- Floats (``max_retries=1.5``) — accidental Python decimal coercion
- Strings (``max_retries="2"``) — caller passed unparsed env var
- Bools (``max_retries=True``) — Python's bool-as-int idiom is intentionally
  rejected because it likely indicates a caller error (``max_retries=True``
  vs ``max_retries=1``); see the package-level helpers' docstrings.

And accepts the two canonical valid forms:
- ``max_retries=0`` (disables retries per D-19)
- ``max_retries=2`` (the documented default per D-20)
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

# Packages whose Client / AsyncClient / configure() accept max_retries.
# matriz AsyncClient is a stub (D-25) without max_retries; covered via the
# sync Client + configure() only.
_SYNC_PACKAGES = [
    ("ambito_financiero_client", "Client", {"base_url": "https://api.test"}),
    (
        "iol_client",
        "Client",
        {"base_url": "https://api.test", "username": "u", "password": "p"},
    ),
    (
        "higyrus_client",
        "Client",
        {
            "base_url": "https://api.test",
            "username": "u",
            "password": "p",
            "client_id": "tenant",
        },
    ),
    (
        "matriz_client",
        "Client",
        {"base_url": "https://api.test", "username": "u", "password": "p"},
    ),
]

_ASYNC_PACKAGES = [
    ("ambito_financiero_client", "AsyncClient", {"base_url": "https://api.test"}),
    (
        "iol_client",
        "AsyncClient",
        {"base_url": "https://api.test", "username": "u", "password": "p"},
    ),
    (
        "higyrus_client",
        "AsyncClient",
        {
            "base_url": "https://api.test",
            "username": "u",
            "password": "p",
            "client_id": "tenant",
        },
    ),
    # matriz AsyncClient stub does NOT accept max_retries per D-25.
]


@pytest.mark.parametrize(("pkg_name", "cls_name", "ctor_kwargs"), _SYNC_PACKAGES)
@pytest.mark.parametrize("bad", [-1, -100, 1.5, "2", True, False])
def test_sync_client_rejects_invalid_max_retries(
    pkg_name: str,
    cls_name: str,
    ctor_kwargs: dict[str, Any],
    bad: Any,
) -> None:
    """WR-06: ``Client(max_retries=BAD)`` raises ``ValueError`` per package."""
    pkg = importlib.import_module(pkg_name)
    cls = getattr(pkg, cls_name)
    with pytest.raises(ValueError, match="max_retries"):
        cls(max_retries=bad, **ctor_kwargs)


@pytest.mark.parametrize(("pkg_name", "cls_name", "ctor_kwargs"), _SYNC_PACKAGES)
@pytest.mark.parametrize("good", [0, 1, 2, 5])
def test_sync_client_accepts_valid_max_retries(
    pkg_name: str,
    cls_name: str,
    ctor_kwargs: dict[str, Any],
    good: int,
) -> None:
    """WR-06: ``Client(max_retries=N)`` for non-negative int succeeds per package."""
    pkg = importlib.import_module(pkg_name)
    cls = getattr(pkg, cls_name)
    instance = cls(max_retries=good, **ctor_kwargs)
    # Sanity: the value is stored on the instance.
    assert instance._max_retries == good


@pytest.mark.parametrize(("pkg_name", "cls_name", "ctor_kwargs"), _ASYNC_PACKAGES)
@pytest.mark.parametrize("bad", [-1, -100, 1.5, "2", True, False])
def test_async_client_rejects_invalid_max_retries(
    pkg_name: str,
    cls_name: str,
    ctor_kwargs: dict[str, Any],
    bad: Any,
) -> None:
    """WR-06: ``AsyncClient(max_retries=BAD)`` raises ``ValueError`` per package."""
    pkg = importlib.import_module(pkg_name)
    cls = getattr(pkg, cls_name)
    with pytest.raises(ValueError, match="max_retries"):
        cls(max_retries=bad, **ctor_kwargs)


@pytest.mark.parametrize(("pkg_name", "cls_name", "ctor_kwargs"), _ASYNC_PACKAGES)
@pytest.mark.parametrize("good", [0, 1, 2, 5])
def test_async_client_accepts_valid_max_retries(
    pkg_name: str,
    cls_name: str,
    ctor_kwargs: dict[str, Any],
    good: int,
) -> None:
    """WR-06: ``AsyncClient(max_retries=N)`` for non-negative int succeeds."""
    pkg = importlib.import_module(pkg_name)
    cls = getattr(pkg, cls_name)
    instance = cls(max_retries=good, **ctor_kwargs)
    assert instance._max_retries == good


@pytest.mark.parametrize(
    "pkg_name", ["ambito_financiero_client", "iol_client", "higyrus_client", "matriz_client"]
)
@pytest.mark.parametrize("bad", [-1, -100, 1.5, "2", True, False])
def test_sync_configure_rejects_invalid_max_retries(pkg_name: str, bad: Any) -> None:
    """WR-06: ``configure(max_retries=BAD)`` raises ``ValueError`` per package."""
    pkg = importlib.import_module(pkg_name)
    with pytest.raises(ValueError, match="max_retries"):
        pkg.configure(max_retries=bad)


@pytest.mark.parametrize(
    "pkg_name", ["ambito_financiero_client", "iol_client", "higyrus_client"]
)
@pytest.mark.parametrize("bad", [-1, -100, 1.5, "2", True, False])
def test_async_configure_rejects_invalid_max_retries(pkg_name: str, bad: Any) -> None:
    """WR-06: ``aio.configure(max_retries=BAD)`` raises ``ValueError`` per package."""
    pkg = importlib.import_module(pkg_name)
    with pytest.raises(ValueError, match="max_retries"):
        pkg.aio.configure(max_retries=bad)
