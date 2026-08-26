"""Suite de la unidad puente de la Phase 33: record de decode -> finding ``SHAPE``.

Cubre el mecanismo del criterio 1 de la fase (LIVE-TYP-01, D-01/D-02): que una
divergencia emitida por ``_decode._emit`` en cualquiera de los cinco paquetes
tipados llegue a ``append_finding`` cargando su endpoint, su modelo, su ruta de
campo y su superficie.

- ``test_handler_maps_record_to_shape_finding`` — el mapeo mismo existe.
- ``test_probe_context_binding`` — D-02: endpoint/surface viajan por ContextVar
  y se resetean (sync y ``async def``).

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
from verification.divergences import divergence_capture, probe_context

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
