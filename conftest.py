"""Hooks de pytest a nivel de repo para el harness de verificación en vivo.

Registra el marker ``live`` (satisface ``--strict-markers``), agrega la flag
``--live`` y deselecciona los tests marcados con ``@pytest.mark.live`` salvo que
se pase ``--live``. Así CI corre siempre offline y determinista (HARN-04, D-03/D-04):

- ``uv run pytest``         -> los tests ``live`` quedan deseleccionados.
- ``uv run pytest --live``  -> los tests ``live`` se seleccionan y corren.

Las fixtures autouse por paquete (``packages/*/tests/conftest.py``) se mantienen
intactas: estos hooks de colección viven sólo en la raíz.
"""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Agrega la flag ``--live`` (por defecto desactivada)."""
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Ejecuta tests @pytest.mark.live contra APIs reales.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Registra el marker ``live`` para que ``--strict-markers`` no falle."""
    config.addinivalue_line(
        "markers",
        "live: test que toca una API en vivo (deseleccionado salvo --live).",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Deselecciona los tests ``live`` salvo que se pase ``--live``."""
    if config.getoption("--live"):
        return
    selected: list[pytest.Item] = []
    deselected: list[pytest.Item] = []
    for item in items:
        (deselected if "live" in item.keywords else selected).append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected
