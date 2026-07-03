"""RED-phase test suite (SPIKE-006 001a): pins the behavior + item-9 PURITY of the five
libcst ``CSTTransformer`` subclasses BEFORE they exist (TDD).

Run under the ephemeral libcst env (D-05 — libcst never added to dev deps). This file
lives under ``.planning/spikes/**`` which is excluded from ruff / mypy / pytest testpaths
(root ``pyproject.toml``), so it is invoked EXPLICITLY, never auto-collected by CI:

    uv run --with 'libcst>=1.8.0,<2' python -m pytest \
      .planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/transformers/test_transformers.py -q

Two contracts are asserted:
  1. Mechanical transform behavior (async→sync strip, node renames, import-order,
     docstring label localization, aio-only suppression).
  2. Item 9 (D-RIGOR-02): each ``CSTTransformer`` subclass is a PURE ``CSTNode → CSTNode``
     function — visiting a module MUST NOT mutate the transformer instance's ``vars()``
     (no cross-node accumulation) and MUST perform no I/O. Immutable config passed at
     ``__init__`` is allowed (read-only closed-over constant), so purity is asserted as
     "``vars(t)`` is byte-identical before and after ``module.visit(t)``".
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import libcst as cst

sys.path.insert(0, str(Path(__file__).resolve().parent))

from async_to_sync import AsyncToSync  # noqa: E402
from docstring_localizer import DocstringLocalizer  # noqa: E402
from import_direction_normalizer import ImportDirectionNormalizer  # noqa: E402
from import_normalizer import ImportNormalizer  # noqa: E402
from suppressors import Suppressors  # noqa: E402


def _apply(transformer: cst.CSTTransformer, src: str) -> str:
    return cst.parse_module(src).visit(transformer).code


# --- item-9 purity harness ------------------------------------------------


def _assert_pure(transformer: cst.CSTTransformer, src: str) -> None:
    """Visiting MUST NOT mutate the transformer instance (no cross-node state)."""
    before = copy.deepcopy(vars(transformer))
    cst.parse_module(src).visit(transformer)
    after = vars(transformer)
    # No attribute added/removed/mutated across the visit.
    assert set(before) == set(after), f"{type(transformer).__name__} added/removed attrs"
    for k in before:
        assert before[k] == after[k], f"{type(transformer).__name__} mutated {k!r} across visit"


# --- AsyncToSync ----------------------------------------------------------

_ASYNC_SRC = """
import httpx


class AsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, a, b, c) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._state.http_client.aclose()

    def _ensure(self):
        return httpx.AsyncClient(
            transport=_atransport.AsyncRetryTransport(max_attempts=1)
        )


async def get_x():
    return await _get_default().get_x()
"""


def test_async_to_sync_strips_async_await_and_renames() -> None:
    out = _apply(AsyncToSync(), _ASYNC_SRC)
    assert "async def" not in out
    assert "await " not in out
    assert "class Client:" in out
    assert "def __enter__" in out and "def __exit__" in out
    assert "def close(self)" in out and "aclose" not in out
    assert "httpx.Client(" in out and "httpx.AsyncClient" not in out
    assert "_transport.RetryTransport" in out and "_atransport" not in out
    assert "AsyncRetryTransport" not in out


def test_async_to_sync_is_pure() -> None:
    _assert_pure(AsyncToSync(), _ASYNC_SRC)


# --- ImportNormalizer -----------------------------------------------------


def test_import_normalizer_sorts_ambito_alias_list() -> None:
    src = "from ambito_financiero_client import _transport, _core\n"
    out = _apply(ImportNormalizer(), src)
    assert out == "from ambito_financiero_client import _core, _transport\n"


def test_import_normalizer_leaves_future_import() -> None:
    src = "from __future__ import annotations\n"
    assert _apply(ImportNormalizer(), src) == src


def test_import_normalizer_is_pure() -> None:
    _assert_pure(ImportNormalizer(), "from ambito_financiero_client import _transport, _core\n")


# --- DocstringLocalizer ---------------------------------------------------


def test_docstring_localizer_swaps_labels() -> None:
    src = '"""Cliente asincrónico. AmbitoFinancieroAsyncClient con AsyncClient."""\n'
    out = _apply(DocstringLocalizer(), src)
    assert "sincrónico" in out and "asincrónico" not in out
    assert "AmbitoFinancieroClient" in out
    assert "AsyncClient" not in out


def test_docstring_localizer_is_pure() -> None:
    _assert_pure(DocstringLocalizer(), '"""asincrónico AsyncClient"""\n')


# --- Suppressors ----------------------------------------------------------

_SUPPRESS_SRC = """
import warnings

__all__ = ["AsyncClient", "aclose", "configure"]


def configure() -> None:
    if _default_async_client is not None:
        prior_base_url = _default_async_client._state.base_url
        prior_http_client = _default_async_client._state.http_client
        if prior_http_client is not None:
            warnings.warn("leak", ResourceWarning, stacklevel=2)
    new_base_url = prior_base_url
"""


def test_suppressors_removes_import_warnings() -> None:
    out = _apply(Suppressors(), _SUPPRESS_SRC)
    assert "import warnings" not in out


def test_suppressors_removes_wr07_block_and_prior_http_client() -> None:
    out = _apply(Suppressors(), _SUPPRESS_SRC)
    assert "ResourceWarning" not in out
    assert "warnings.warn" not in out
    assert "prior_http_client" not in out


def test_suppressors_prunes_aclose_from_all() -> None:
    out = _apply(Suppressors(), _SUPPRESS_SRC)
    assert '"aclose"' not in out
    # non-aclose entries survive
    assert '"configure"' in out


def test_suppressors_is_pure() -> None:
    _assert_pure(Suppressors(), _SUPPRESS_SRC)


# --- ImportDirectionNormalizer (Q1 content-absence) -----------------------


def test_import_direction_strips_import_when_name_is_locally_defined() -> None:
    # When the def IS local, the self-import is redundant → stripped.
    src = (
        "from ambito_financiero_client.client import _validate_max_retries\n"
        "\n\ndef _validate_max_retries(v):\n    return None\n"
    )
    out = _apply(ImportDirectionNormalizer(frozenset({"_validate_max_retries"})), src)
    assert "from ambito_financiero_client.client import _validate_max_retries" not in out
    assert "def _validate_max_retries" in out


def test_import_direction_retains_import_when_name_absent() -> None:
    # Q1: the def is ABSENT from source → cannot be synthesized → self-import retained
    # (honest item-1/item-6 residual; NOT bypassed by reading client.py).
    src = "from ambito_financiero_client.client import _validate_max_retries\n"
    out = _apply(ImportDirectionNormalizer(frozenset()), src)
    assert "from ambito_financiero_client.client import _validate_max_retries" in out


def test_import_direction_is_pure() -> None:
    _assert_pure(
        ImportDirectionNormalizer(frozenset({"_validate_max_retries"})),
        "from ambito_financiero_client.client import _validate_max_retries\n",
    )
