"""Sync/async parity net para wallets (Phase 32, GATE-TYP-01).

Tres tests finos: los dos primeros delegan en el único walker compartido,
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
enrola en ``uv run mypy packages/wallets-client/tests``, que es la única forma en
que ``tools/*.py`` entra al chequeo estricto.

WALLETS ES EL ÚNICO PAQUETE PRE-PHASE-7
=======================================

Sus funciones de request son **a nivel módulo**, no métodos: ``client.py:33-36``
define los singletons ``_base_url`` / ``_token`` / ``_client`` directamente y
``_request`` es una función suelta. No hay ``Client``, no hay ``AsyncClient``, y
no hay ``_core.py`` (ni ``_state.py`` / ``_transport.py`` / ``_decode.py`` /
``_logging.py``).

Esa es la razón **estructural** — no preferencial — por la que wallets queda
fuera de ``root_packages`` de import-linter (**D-10**): sin ``_core.py`` no
existe un ``source_modules`` contra el cual escribir un contrato ``forbidden``
de la forma que usan los otros cinco. El mismo hecho sostiene su registro
``ExemptPackage`` en ``tools/check_decode_intactness.py`` (``EXEMPT_PACKAGES``),
cuyo campo ``resolved_by`` la Plan 32-05 actualizó para apuntar al desenlace
D-10 de esta fase. Quien aterrice en cualquiera de los dos artefactos debe
encontrar el otro.

EL PISO DE ESTE PAQUETE ES CASI-VACUO, Y ESO SE DECLARA
======================================================

Piso: **(1, 2)** en la métrica class-exclusive. Su única superficie pública de
módulo es ``configure`` del lado sync, y ``configure`` más ``aclose`` del lado
async. Ese piso **asegura casi nada** y es casi-vacuo **por construcción**, no
por descuido: no debe leerse como cobertura. Subirlo es trabajo de la fase que
le dé a wallets un ``Client``, no de esta.

Lo que este archivo NO hace es saltear el eje de clase. Un ``return`` temprano,
un marcador de omisión o un ``xfail`` harían que wallets pasara vacuamente, que
es literalmente el modo de falla WR-01/WR-02 de la Phase 15 que el criterio 3
cita por nombre. En su lugar, la ausencia del par de clases se **asevera**.
"""

from __future__ import annotations

from tools.surface_parity import (
    CLASS_AXIS_ABSENT,
    assert_module_lower_bound,
    assert_module_parity,
    class_parity_report,
)

from wallets_client import aio, client

_PACKAGE = "wallets_client"


def test_module_surface_names_and_hints_agree() -> None:
    """Eje de módulo: ``client`` y ``aio`` exponen los mismos nombres y las mismas hints.

    wallets es el único paquete con **cero** divergencias crudas: su ``configure``
    toma los mismos dos parámetros con los mismos tipos en ambas superficies, y la
    única diferencia de conjuntos de nombres es el ``aclose`` async-only que la
    regla 3 ya sanciona.
    """
    assert_module_parity(_PACKAGE)


def test_module_surface_is_not_vacuous() -> None:
    """Guardia de no-vacuidad contra un piso que asegura casi nada, y lo dice.

    El piso de wallets es (1, 2): un nombre público en ``client`` y dos en
    ``aio``. Es casi-vacuo **por construcción** — wallets no tiene par
    ``Client``/``AsyncClient`` y sus requests son funciones de módulo — y no debe
    leerse como cobertura. Subirlo le corresponde a la fase que le dé a wallets
    un ``Client``.
    """
    assert_module_lower_bound(_PACKAGE)


def test_wallets_has_no_client_class_pair() -> None:
    """El eje de clase se asevera por AUSENCIA, nunca se saltea.

    Misma forma que el Check D de ``tools/check_decode_intactness.py`` ("exempt
    package has acquired a ``_decode.py``"): el día que wallets gane un
    ``Client`` o un ``AsyncClient``, este test **falla**, y esa falla es la señal
    de que hay que enrolarlo en el eje de paridad de clases y reexaminar su
    exclusión de ``root_packages`` (D-10).
    """
    assert not hasattr(client, "Client"), (
        "wallets_client.client ganó un `Client`. El eje de paridad de clases ya no "
        "es inaplicable: agregá `assert_class_parity('wallets_client')` acá en lugar "
        "de esta aserción de ausencia, y reexaminá la exclusión de wallets de "
        "`root_packages` de import-linter (D-10), que se sostenía en que el paquete "
        "no tiene `_core.py` ni superficie basada en clases."
    )
    assert not hasattr(aio, "AsyncClient"), (
        "wallets_client.aio ganó un `AsyncClient`. Ver el mensaje de la aserción "
        "anterior: corresponde enrolar wallets en el eje de paridad de clases y "
        "reexaminar D-10."
    )
    # El helper compartido llega al mismo veredicto por su propio camino: marca el
    # reporte como ausente en vez de vaciarlo en silencio (32-04), y `assert_class_parity`
    # levanta ante ese estado justamente para que la ausencia se asevere acá.
    report = class_parity_report(_PACKAGE)
    assert report.axis == CLASS_AXIS_ABSENT, (
        f"tools/surface_parity.py reporta el eje {report.axis!r} para wallets, no "
        f"{CLASS_AXIS_ABSENT!r}: el par de clases apareció y esta aserción de ausencia "
        "quedó obsoleta."
    )
