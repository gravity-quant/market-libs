"""Sync/async parity net for market-data (Phase 32, GATE-TYP-01).

Tres tests finos: cada uno delega en el único walker compartido,
``tools/surface_parity.py`` (D-07). Seis copias del walker recrearían
exactamente la deriva que ``tools/check_decode_intactness.py`` existe para
prevenir en ``_decode.py``; la lógica vive en un solo lugar y estos archivos son
sólo el punto de enganche por paquete.

Viven bajo ``packages/<pkg>/tests/`` porque ``testpaths`` colecta ``packages``
dentro de la matriz 6x2 de CI, y ``verification/`` es la carpeta que este
codebase documenta repetidamente como CI-invisible. El módulo ``tools`` se
resuelve porque la raíz del repo está en ``sys.path`` — ``pythonpath = ["."]``,
``pyproject.toml:109``, namespace package implícito (Patrón 1 de la
investigación). Como efecto colateral deseado, importar el helper desde acá lo
enrola en ``uv run mypy packages/market-data-client/tests``, que es la única
forma en que ``tools/*.py`` entra al chequeo estricto.

Este archivo NO repite lo que
``test_public_surface_market_data.py::test_sync_async_method_name_parity`` ya
cubre: esa es la red pre-existente de **nombres solamente**, y sobre una tupla
curada de métodos de mutación. Acá se agregan los tres ejes que le faltan — el
eje de módulo, la comparación de ``get_type_hints()`` resuelta, y los lower
bounds por paquete — todos derivados por introspección en runtime, nunca de
``__all__`` (cuatro de seis ``client.py`` y tres de seis ``aio.py`` no tienen
``__all__``, así que un test basado en ``__all__`` pasaría vacuamente en la mitad
del monorepo).
"""

from __future__ import annotations

from tools.surface_parity import (
    assert_class_parity,
    assert_module_lower_bound,
    assert_module_parity,
)

_PACKAGE = "market_data_client"


def test_module_surface_names_and_hints_agree() -> None:
    """Eje de módulo: ``client`` y ``aio`` exponen los mismos nombres y las mismas hints."""
    assert_module_parity(_PACKAGE)


def test_client_and_async_client_methods_agree() -> None:
    """Eje de clase: ``Client`` y ``AsyncClient`` coinciden salvo ``close`` ↔ ``aclose``."""
    assert_class_parity(_PACKAGE)


def test_module_surface_is_not_vacuous() -> None:
    """Guardia de no-vacuidad: ambas superficies siguen por encima de su piso medido."""
    assert_module_lower_bound(_PACKAGE)
