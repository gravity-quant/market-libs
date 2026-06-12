"""Tests del harness de verificación: findings helper (HARN-05/D-07/08/09).

Estos tests prueban el comportamiento observable del módulo ``verification.findings``:

- ``FINDING_CLASSES`` contiene exactamente las 7 clases fijas en el orden documentado.
- ``STATUS_LIFECYCLE`` contiene exactamente los 5 estados en el orden documentado.
- ``new_findings(pkg)`` renderiza el título del paquete, el encabezado ART, todas las
  7 clases en los comentarios HTML, la cadena del ciclo de estados y el encabezado del
  índice.
- ``findings_path(pkg)`` devuelve ``.planning/verification/<pkg>-findings.md`` bajo el
  directorio de hallazgos resuelto.
- ``write_findings(pkg)`` crea el archivo, devuelve la ruta y el contenido coincide con
  ``new_findings(pkg)``.
- ``write_findings`` NO sobreescribe un archivo existente cuando ``overwrite=False`` y
  SÍ sobreescribe cuando ``overwrite=True``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import verification.findings as findings_module
from verification.findings import (
    FINDING_CLASSES,
    STATUS_LIFECYCLE,
    findings_path,
    new_findings,
    write_findings,
)


def test_finding_classes_has_exactly_seven_documented_classes_in_order() -> None:
    """HARN-05/D-09: las 7 clases fijas en el orden documentado."""
    expected = ("SHAPE", "AUTH", "ERROR-MAP", "PARAM", "SYNC-ASYNC-DRIFT", "NO-DATA", "ANTI-BOT")
    assert expected == FINDING_CLASSES


def test_status_lifecycle_has_exactly_five_states_in_order() -> None:
    """HARN-05/D-08: los 5 estados del ciclo en el orden documentado."""
    expected = ("OPEN", "CONFIRMED", "FIXED", "EXPECTED", "NO-FIX")
    assert expected == STATUS_LIFECYCLE


def test_new_findings_renders_package_title() -> None:
    """new_findings renderiza el título ``# Findings: higyrus-client``."""
    rendered = new_findings("higyrus")
    assert "# Findings: higyrus-client" in rendered


def test_new_findings_renders_art_run_context_header() -> None:
    """new_findings renderiza el encabezado ART de contexto de ejecución."""
    rendered = new_findings("higyrus")
    assert "## Run Context (ART)" in rendered


def test_new_findings_renders_all_seven_finding_classes() -> None:
    """new_findings incluye todas las 7 clases en el cuerpo del archivo."""
    rendered = new_findings("higyrus")
    for cls in FINDING_CLASSES:
        assert cls in rendered, f"clase ausente en el renderizado: {cls!r}"


def test_new_findings_renders_lifecycle_string() -> None:
    """new_findings incluye la cadena del ciclo de estados."""
    rendered = new_findings("higyrus")
    # El ciclo documentado: OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX)
    assert "OPEN" in rendered
    assert "CONFIRMED" in rendered
    assert "FIXED" in rendered
    assert "EXPECTED" in rendered
    assert "NO-FIX" in rendered


def test_new_findings_renders_index_table_header() -> None:
    """new_findings incluye el encabezado de la tabla de índice."""
    rendered = new_findings("higyrus")
    assert "## Index" in rendered
    assert "| ID | Class | Surface | Status |" in rendered


def test_findings_path_returns_correct_path_under_findings_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """findings_path devuelve ``<dir>/<pkg>-findings.md`` bajo el directorio de hallazgos."""
    fake_dir = tmp_path / "verification"
    monkeypatch.setattr(findings_module, "_FINDINGS_DIR", fake_dir)
    result = findings_path("higyrus")
    assert result == fake_dir / "higyrus-findings.md"


def test_write_findings_creates_file_and_returns_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """write_findings crea el archivo y devuelve la ruta."""
    fake_dir = tmp_path / "verification"
    monkeypatch.setattr(findings_module, "_FINDINGS_DIR", fake_dir)
    result = write_findings("higyrus")
    assert result.exists()
    assert result.name == "higyrus-findings.md"


def test_write_findings_content_matches_new_findings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """write_findings escribe exactamente lo que devuelve new_findings(pkg)."""
    fake_dir = tmp_path / "verification"
    monkeypatch.setattr(findings_module, "_FINDINGS_DIR", fake_dir)
    result = write_findings("higyrus")
    written = result.read_text(encoding="utf-8")
    assert written == new_findings("higyrus")


def test_write_findings_does_not_overwrite_when_overwrite_false(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """write_findings NO sobreescribe el archivo cuando overwrite=False."""
    fake_dir = tmp_path / "verification"
    monkeypatch.setattr(findings_module, "_FINDINGS_DIR", fake_dir)
    # Escrita inicial.
    write_findings("higyrus")
    # Modificar el archivo en disco.
    path = findings_path("higyrus")
    path.write_text("contenido modificado", encoding="utf-8")
    # Segunda llamada sin overwrite — debe preservar el contenido modificado.
    write_findings("higyrus", overwrite=False)
    assert path.read_text(encoding="utf-8") == "contenido modificado"


def test_write_findings_does_overwrite_when_overwrite_true(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """write_findings sobreescribe el archivo cuando overwrite=True."""
    fake_dir = tmp_path / "verification"
    monkeypatch.setattr(findings_module, "_FINDINGS_DIR", fake_dir)
    # Escrita inicial.
    write_findings("higyrus")
    # Modificar el archivo en disco.
    path = findings_path("higyrus")
    path.write_text("contenido modificado", encoding="utf-8")
    # Segunda llamada con overwrite=True — debe restaurar el esqueleto.
    write_findings("higyrus", overwrite=True)
    assert path.read_text(encoding="utf-8") == new_findings("higyrus")
