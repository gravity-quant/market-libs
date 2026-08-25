"""Sync/async parity net para iol (Phase 32, GATE-TYP-01).

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
enrola en ``uv run mypy packages/iol-client/tests``, que es la única forma en que
``tools/*.py`` entra al chequeo estricto.

Piso de este paquete: **(6, 7)** en la métrica class-exclusive. Iol es el
paquete cuya superficie tipada entregó la Phase 30 (16 firmas migradas a
modelos), así que el piso protege tanto los nombres de módulo como el hecho de
que la comparación de hints examinó al menos 6 callables — la vía por la que un
`get_type_hints` que dejara de resolver se leería como acuerdo.
"""

from __future__ import annotations

from tools.surface_parity import (
    assert_class_parity,
    assert_module_lower_bound,
    assert_module_parity,
)

_PACKAGE = "iol_client"


def test_module_surface_names_and_hints_agree() -> None:
    """Eje de módulo: ``client`` y ``aio`` exponen los mismos nombres y las mismas hints."""
    assert_module_parity(_PACKAGE)


def test_client_and_async_client_methods_agree() -> None:
    """Eje de clase: ``Client`` y ``AsyncClient`` coinciden salvo ``close`` ↔ ``aclose``."""
    assert_class_parity(_PACKAGE)


def test_module_surface_is_not_vacuous() -> None:
    """Guardia de no-vacuidad: ambas superficies siguen por encima de su piso medido."""
    assert_module_lower_bound(_PACKAGE)
