"""Smoke tests for :mod:`matriz_client.types` re-exports."""

from __future__ import annotations

import matriz_client
from matriz_client import types


def test_every_public_symbol_is_defined() -> None:
    for name in types.__all__:
        assert hasattr(types, name), f"Missing attribute in types module: {name}"


def test_every_public_symbol_is_re_exported_from_package() -> None:
    for name in types.__all__:
        assert hasattr(matriz_client, name), f"Missing re-export from matriz_client: {name}"
        assert name in matriz_client.__all__, f"Missing from matriz_client.__all__: {name}"
