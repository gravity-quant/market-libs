"""Ejemplo trivial del mecanismo --live (HARN-04).

Sirve como plantilla copiable para los tests en vivo reales de las fases 2-5.
"""

from __future__ import annotations

import pytest


@pytest.mark.live
def test_live_marker_is_wired() -> None:
    """Demuestra el mecanismo --live. No toca la red.

    Sin --live: deseleccionado. Con --live: corre y pasa.
    Copiar como plantilla para tests en vivo reales en fases 2-5.
    """
    assert True
