"""Sync/async parity net para higyrus (Phase 32, GATE-TYP-01).

Tres tests finos: cada uno delega en el único walker compartido,
``tools/surface_parity.py`` (D-07). Seis copias del walker recrearían
exactamente la deriva que ``tools/check_decode_intactness.py`` existe para
prevenir en ``_decode.py``; la lógica vive en un solo lugar y estos archivos son
sólo el punto de enganche por paquete.

Viven bajo ``packages/<pkg>/tests/`` porque ``testpaths`` colecta ``packages``
dentro de la matriz 6x2 de CI, y ``verification/`` es la carpeta que este
codebase documenta repetidamente como CI-invisible (el job ``test`` pasa un path
explícito ``packages/<pkg>`` que pisa ``testpaths``). El módulo ``tools`` se
resuelve porque la raíz del repo está en ``sys.path`` — ``pythonpath = ["."]``,
``pyproject.toml:109``, namespace package implícito (Patrón 1 de la
investigación). Como efecto colateral deseado, importar el helper desde acá lo
enrola en ``uv run mypy packages/higyrus-client/tests``, que es la única forma en
que ``tools/*.py`` entra al chequeo estricto.

Piso de este paquete: **(7, 8)** en la métrica class-exclusive. Higyrus es el
paquete de mayor superficie de back-office fuera de matriz y el dueño del
``SafeModel`` original que las otras copias replican; el piso pinea que ninguna
de sus dos superficies puede colapsar por debajo de lo medido, que es la falla
que una comparación de paridad por sí sola no detecta — dos superficies que
coinciden porque ambas se vaciaron.
"""

from __future__ import annotations

from tools.surface_parity import (
    assert_class_parity,
    assert_module_lower_bound,
    assert_module_parity,
)

_PACKAGE = "higyrus_client"


def test_module_surface_names_and_hints_agree() -> None:
    """Eje de módulo: ``client`` y ``aio`` exponen los mismos nombres y las mismas hints."""
    assert_module_parity(_PACKAGE)


def test_client_and_async_client_methods_agree() -> None:
    """Eje de clase: ``Client`` y ``AsyncClient`` coinciden salvo ``close`` ↔ ``aclose``."""
    assert_class_parity(_PACKAGE)


def test_module_surface_is_not_vacuous() -> None:
    """Guardia de no-vacuidad: ambas superficies siguen por encima de su piso medido."""
    assert_module_lower_bound(_PACKAGE)
