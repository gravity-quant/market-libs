"""Suite de la unidad puente de la Phase 33: record de decode -> finding ``SHAPE``.

Cubre el mecanismo del criterio 1 de la fase (LIVE-TYP-01, D-01/D-02): que una
divergencia emitida por ``_decode._emit`` en cualquiera de los cinco paquetes
tipados llegue a ``append_finding`` cargando su endpoint, su modelo, su ruta de
campo y su superficie.

Cada test cierra un canal de pérdida silenciosa verificado en ``33-RESEARCH.md``:

- ``test_handler_maps_record_to_shape_finding`` — el mapeo mismo existe.
- ``test_probe_context_binding`` — D-02: endpoint/surface viajan por ContextVar
  y se resetean (sync y ``async def``).
- ``test_install_sets_level_and_restores`` — P-1: un logger de paquete en NOTSET
  hereda el ``WARNING`` del logger raíz, así que los 32 records de especie
  ``extra`` del piso ratificado de 96 se descartan ANTES de que corra ningún
  handler. Subir el nivel es lo que los admite; restaurarlo es lo que impide
  secuestrar la configuración de logging del consumidor (T-33-05).
- ``test_extra_kind_is_captured`` — P-1 desde el otro lado: el record INFO llega
  con el nivel subido y NO llega sin él, así que la subida es load-bearing y no
  incidental.
- ``test_emit_never_raises`` — P-2: ``_decode._emit`` corre la emisión entera
  dentro de un ``contextlib.suppress(Exception)`` (lock 9), así que una excepción
  del handler se pierde sin rastro y el run reporta limpio. El handler la
  convierte en un número contable.

Aislamiento: todos los tests que escriben findings monkeypatchean
``verification.findings._FINDINGS_DIR`` a ``tmp_path``. Ningún test toca los
archivos committeados de ``.planning/verification/``.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

import pytest

import verification.findings
from verification.divergences import (
    PACKAGE_LOGGERS,
    DivergenceHandler,
    divergence_capture,
    probe_context,
)

# Lock 1 de ``29-AGGREGATION-CONTRACT.md``: el mensaje es una constante sin
# interpolación; toda parte variable del record viaja en ``extra``.
_MESSAGE = "decode divergence"

_DETAIL_HEADER_RE = re.compile(r"^### (?P<fid>F-\d+) -- (?P<title>.+)$", re.MULTILINE)


def _record_extra(
    *,
    package: str = "higyrus_client",
    divergence: str = "missing",
    model: str = "Movimiento",
    field_path: str = ".fecha",
    declared_type: str = "str",
    observed_type: str = "NoneType",
) -> dict[str, str]:
    """Construye el dict ``extra`` de seis claves planas que emite ``_decode._emit``."""
    return {
        "package": package,
        "divergence": divergence,
        "field_path": field_path,
        "declared_type": declared_type,
        "observed_type": observed_type,
        "model": model,
    }


def _fid_allocator() -> Any:
    """Devuelve un ``next_fid(slug) -> 'F-NN'`` determinístico, uno por test."""
    counter = {"n": 0}

    def _next_fid(slug: str) -> str:
        counter["n"] += 1
        return f"F-{counter['n']:02d}"

    return _next_fid


@pytest.fixture
def isolated_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirige el directorio de findings a ``tmp_path`` durante el test.

    ``monkeypatch`` deshace el setattr en su propio teardown, así que el fixture
    no necesita uno propio (de ahí el ``return`` y no un ``yield``).
    """
    monkeypatch.setattr(verification.findings, "_FINDINGS_DIR", tmp_path)
    return tmp_path


def test_handler_maps_record_to_shape_finding(isolated_findings: Path) -> None:
    """Un record de seis claves produce EXACTAMENTE un finding SHAPE completo.

    Es el criterio 1 de la fase en su forma mínima: endpoint + modelo + ruta de
    campo + superficie tienen que sobrevivir el viaje desde el ``extra`` del
    ``LogRecord`` hasta el archivo de findings.
    """
    endpoint = "/api/cuentas/{id_cuenta}/movimientos"

    with divergence_capture(["higyrus_client"], next_fid=_fid_allocator()) as handler:

        @probe_context(endpoint=endpoint, surface="sync")
        def _probe() -> None:
            logging.getLogger("higyrus_client").warning(_MESSAGE, extra=_record_extra())

        _probe()

    path = isolated_findings / "higyrus-client-findings.md"
    assert path.exists(), (
        "el handler no escribió ningún archivo de findings; el puente "
        "record -> append_finding no existe y el criterio 1 no tiene mecanismo"
    )
    text = path.read_text(encoding="utf-8")

    blocks = _DETAIL_HEADER_RE.findall(text)
    assert len(blocks) == 1, f"se esperaba 1 bloque '### F-', hay {len(blocks)}: {blocks}"

    title = blocks[0][1]
    for token in ("Movimiento", ".fecha", "missing"):
        assert token in title, (
            f"el título {title!r} no carga {token!r}; el título ES la clave de dedupe "
            "cross-run (idempotent_by_title), así que perder un componente colapsa "
            "divergencias distintas en un solo finding"
        )

    assert "**Class:** `SHAPE`" in text, "la clase del finding debe ser SHAPE"
    assert "**Surface:** `sync`" in text, (
        "la superficie debe quedar registrada en el finding — el criterio 1 la exige"
    )
    diff_line = next(ln for ln in text.splitlines() if ln.startswith("- **Diff:**"))
    assert endpoint in diff_line, (
        f"el diff {diff_line!r} no nombra el endpoint {endpoint!r}; sin él un finding "
        "no se puede rutear al sitio de decode que lo produjo (D-02)"
    )

    assert handler.seen == {("higyrus-client", "Movimiento", ".fecha", "missing")}, (
        "``seen`` es la unidad del censo y tiene que ser el triple con slug, la única "
        f"directamente comparable con 29-SIZING.md; se obtuvo {handler.seen!r}"
    )


def test_probe_context_binding(isolated_findings: Path) -> None:
    """D-02: el decorador bindea endpoint+surface y los resetea al salir (sync y async).

    El handler lee los ContextVar en tiempo de ``emit``: ``logging`` despacha los
    handlers sincrónicamente en el frame que emite, así que ve el binding del
    caller. Después del ``reset`` tiene que ver los defaults — un token no
    reseteado haría que el endpoint del último probe contamine todo lo que emita
    después.
    """
    observed: list[tuple[str, str]] = []

    def _record_sink(*args: Any, **kwargs: Any) -> Path:
        diff = str(kwargs["diff"])
        observed.append((str(kwargs["surface"]), diff.rsplit(" via ", 1)[-1]))
        return isolated_findings / "unused.md"

    with divergence_capture(["higyrus_client"], next_fid=_fid_allocator()):

        @probe_context(endpoint="/api/health", surface="sync")
        def _sync_probe() -> None:
            logging.getLogger("higyrus_client").warning(_MESSAGE, extra=_record_extra())

        @probe_context(endpoint="/api/health", surface="async")
        async def _async_probe() -> None:
            logging.getLogger("higyrus_client").warning(
                _MESSAGE, extra=_record_extra(model="Health", field_path=".status")
            )

        original = verification.findings.append_finding
        try:
            verification.findings.append_finding = _record_sink
            _sync_probe()
            asyncio.run(_async_probe())
            # Fuera de todo decorador: los ContextVar deben leer sus defaults.
            logging.getLogger("higyrus_client").warning(
                _MESSAGE, extra=_record_extra(model="Cuenta", field_path=".id")
            )
        finally:
            verification.findings.append_finding = original

    assert observed[0] == ("sync", "/api/health"), f"el probe sync no vio su binding: {observed!r}"
    assert observed[1] == ("async", "/api/health"), (
        "el wrapper ``async def`` tiene que bindear igual que el sync — si el decorador "
        f"no ramifica sobre iscoroutinefunction devuelve una corrutina sin await: {observed!r}"
    )
    assert observed[2] == ("-", "-"), (
        "tras salir del decorador los ContextVar tienen que leer sus defaults; "
        f"se obtuvo {observed[2]!r}, prueba de que el ``reset`` no corrió"
    )


def test_install_sets_level_and_restores() -> None:
    """P-1: el CM sube los cinco loggers de paquete a INFO y restaura todo al salir.

    Un logger de paquete en NOTSET hereda el ``WARNING`` del logger raíz, así que
    los 32 records de especie ``extra`` del piso ratificado de 96 se descartan
    ANTES de que corra ningún handler: el censo devolvería un número más chico y
    se leería como limpio. Subir el nivel es lo que los admite.

    Restaurar nivel Y set de handlers es la otra mitad: no hacerlo secuestra la
    configuración de logging del consumidor, que es justo el anti-patrón que el
    harness no puede permitirse (T-33-05).

    NOTA: este test NO pide el fixture ``caplog`` a propósito. ``caplog`` instala
    handlers en el logger raíz por diseño y volvería vacua la aserción de que ese
    logger quedó intacto — el mismo motivo documentado en
    ``verification/test_logging_root_unchanged.py``.
    """
    root = logging.getLogger()
    root_handlers_before = list(root.handlers)
    root_filters_before = list(root.filters)
    root_level_before = root.level

    levels_before = {name: logging.getLogger(name).level for name in PACKAGE_LOGGERS}
    for name, level in levels_before.items():
        assert level == logging.NOTSET, (
            f"el logger {name!r} ya tenía nivel {level}; este test asume el estado de "
            "librería (NOTSET), que es lo que hace load-bearing a la subida de nivel"
        )
        assert not logging.getLogger(name).isEnabledFor(logging.INFO), (
            f"{name!r} ya admite INFO sin el CM: entonces la subida de nivel no probaría "
            "nada sobre P-1 y este test sería vacuo"
        )

    with divergence_capture(PACKAGE_LOGGERS, next_fid=_fid_allocator()) as handler:
        for name in PACKAGE_LOGGERS:
            lg = logging.getLogger(name)
            assert lg.level == logging.INFO, f"{name!r} no quedó en INFO dentro del CM"
            assert lg.isEnabledFor(logging.INFO), (
                f"{name!r} no admite INFO dentro del CM — los records ``extra`` se pierden"
            )
            assert handler in lg.handlers, f"el handler no quedó adjunto a {name!r}"

    for name, level in levels_before.items():
        lg = logging.getLogger(name)
        assert lg.level == level, (
            f"{name!r} quedó en nivel {lg.level} tras salir del CM (esperado {level}); "
            "no restaurar secuestra la configuración de logging del consumidor"
        )
        assert handler not in lg.handlers, f"el handler sobrevivió al CM en {name!r}"

    assert list(root.handlers) == root_handlers_before, (
        "los handlers del logger raíz cambiaron; el harness sólo puede tocar los cinco "
        "``getLogger('<pkg>')`` nombrados"
    )
    assert list(root.filters) == root_filters_before, "los filtros del logger raíz cambiaron"
    assert root.level == root_level_before, "el nivel del logger raíz cambió"


def test_extra_kind_is_captured(isolated_findings: Path) -> None:
    """P-1: un record ``extra`` (INFO) llega con el nivel subido y NO llega sin él.

    Las dos mitades importan. La primera prueba que los 32 records ``extra`` del
    piso de 96 son alcanzables; la segunda prueba que la subida de nivel es
    load-bearing y no incidental — sin ella el mismo record se descarta en
    ``Logger.isEnabledFor`` antes de tocar handler alguno y el censo devuelve un
    falso limpio.
    """
    extra_kind = _record_extra(divergence="extra", declared_type="-", observed_type="str")

    # Mitad 1: SIN el CM (nivel por defecto) el record INFO no llega al handler.
    handler_without_cm = DivergenceHandler(_fid_allocator())
    lg = logging.getLogger("higyrus_client")
    assert lg.level == logging.NOTSET, "precondición: el logger de paquete está en NOTSET"
    lg.addHandler(handler_without_cm)
    try:
        lg.info(_MESSAGE, extra=extra_kind)
    finally:
        lg.removeHandler(handler_without_cm)
    assert handler_without_cm.seen == set(), (
        "el record INFO llegó al handler SIN subir el nivel: entonces la subida no es "
        "load-bearing y la mitad 2 de este test no probaría nada sobre P-1"
    )

    # Mitad 2: DENTRO del CM el mismo record llega y aterriza como finding.
    with divergence_capture(["higyrus_client"], next_fid=_fid_allocator()) as handler:

        @probe_context(endpoint="/api/health", surface="sync")
        def _probe() -> None:
            logging.getLogger("higyrus_client").info(_MESSAGE, extra=extra_kind)

        _probe()

    assert handler.seen == {("higyrus-client", "Movimiento", ".fecha", "extra")}, (
        f"el record ``extra`` no llegó al handler dentro del CM: {handler.seen!r}"
    )
    text = (isolated_findings / "higyrus-client-findings.md").read_text(encoding="utf-8")
    assert len(_DETAIL_HEADER_RE.findall(text)) == 1, (
        "el record ``extra`` llegó al handler pero no aterrizó como finding"
    )


@pytest.mark.parametrize("exc_type", [ValueError, OSError])
def test_emit_never_raises(
    isolated_findings: Path,
    monkeypatch: pytest.MonkeyPatch,
    exc_type: type[Exception],
) -> None:
    """P-2: una falla del sink es un número contable, jamás una excepción perdida.

    ``_decode._emit`` corre la emisión entera dentro de un
    ``contextlib.suppress(Exception)`` (lock 9): una excepción que salga del
    handler se pierde sin rastro y el run reporta limpio. El handler la absorbe y
    la tallya en ``errors``, que el driver imprime como número — un pipeline de
    logging que puede fallar de forma invisible no sirve como registro de
    auditoría (T-33-04).

    ``ValueError`` cubre el rechazo de validación de ``append_finding``
    (``class_`` / ``status`` / ``title`` multilínea); ``OSError`` cubre el camino
    de escritura del archivo de findings.
    """

    def _boom(*args: Any, **kwargs: Any) -> Path:
        raise exc_type("boom")

    monkeypatch.setattr(verification.findings, "append_finding", _boom)

    with divergence_capture(["higyrus_client"], next_fid=_fid_allocator()) as handler:

        @probe_context(endpoint="/api/health", surface="sync")
        def _probe() -> None:
            logging.getLogger("higyrus_client").warning(_MESSAGE, extra=_record_extra())

        _probe()  # no debe levantar nada

    assert len(handler.errors) == 1, (
        f"se esperaba exactamente 1 falla tallada en ``errors``, hay {handler.errors!r}"
    )
    assert exc_type.__name__ in handler.errors[0], (
        f"la entrada de ``errors`` no nombra el tipo de excepción: {handler.errors[0]!r}"
    )
    assert handler.seen == {("higyrus-client", "Movimiento", ".fecha", "missing")}, (
        "el triple del censo tiene que sobrevivir una falla del sink — se agrega ANTES "
        f"de llamarlo justamente por esto; se obtuvo {handler.seen!r}"
    )
