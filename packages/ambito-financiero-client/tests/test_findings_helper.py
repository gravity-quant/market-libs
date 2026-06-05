"""Tests del harness de verificación: append_finding (HARN-05/D-10).

Estos tests prueban los invariantes críticos de ``append_finding``:

- Creación del esqueleto si el archivo no existe.
- Idempotencia por ``fid`` (re-llamada con mismo ``fid`` actualiza, no duplica).
- Preservación de status promovido por humano (CONFIRMED/FIXED/EXPECTED/NO-FIX).
- Refresco del ART block (Timestamp + base_url + market_hours) en cada call.
- Validación de ``class_`` contra ``FINDING_CLASSES``.
- Validación de ``status`` contra ``STATUS_LIFECYCLE``.
- Re-export vía barrel ``verification``.

Viven bajo ``packages/<pkg>/tests/`` porque ``testpaths=["packages"]`` no colecta
``verification/``; el módulo ``verification`` se resuelve porque la raíz del repo
está en ``sys.path`` (Patrón 1 de la investigación).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from verification import findings
from verification.findings import FINDING_CLASSES, STATUS_LIFECYCLE, append_finding


@pytest.fixture(autouse=True)
def _isolate_findings_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirige el directorio de findings al ``tmp_path`` del test."""
    monkeypatch.setattr(findings, "_FINDINGS_DIR", tmp_path)


def test_append_finding_creates_skeleton_if_missing(tmp_path: Path) -> None:
    """Test 1: si el archivo no existe, append_finding lo crea con el esqueleto + row F-01."""
    pkg = "test-pkg-create"
    path = append_finding(
        pkg,
        fid="F-01",
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title="t",
        expected="e",
        actual="a",
        diff="d",
    )
    assert path.exists()
    assert path == tmp_path / f"{pkg}-findings.md"
    text = path.read_text(encoding="utf-8")
    # Encabezado del archivo presente (esqueleto)
    assert f"# Findings: {pkg}-client" in text
    # Tabla de índice contiene el F-01
    assert "| F-01 | SHAPE | sync | OPEN |" in text
    # Sección de detalle con header del finding
    assert "### F-01 -- t" in text
    # Bullets de detalle
    assert "- **Expected:** e" in text
    assert "- **Actual:** a" in text
    assert "- **Diff:** d" in text


def test_append_finding_is_idempotent_by_fid(tmp_path: Path) -> None:
    """Test 2: dos llamadas con el mismo fid OPEN actualizan, no duplican."""
    pkg = "test-pkg-idempotent"
    append_finding(
        pkg,
        fid="F-01",
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title="primero",
        expected="e1",
        actual="a1",
        diff="d1",
    )
    path = append_finding(
        pkg,
        fid="F-01",
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title="segundo",
        expected="e2",
        actual="a2",
        diff="d2",
    )
    text = path.read_text(encoding="utf-8")
    # Una sola fila en el índice para F-01
    assert text.count("| F-01 |") == 1
    # El title/expected/actual/diff actualizados se ven en el archivo
    assert "### F-01 -- segundo" in text
    assert "- **Expected:** e2" in text
    assert "- **Actual:** a2" in text
    assert "- **Diff:** d2" in text
    # El primer payload ya no aparece
    assert "### F-01 -- primero" not in text


def test_append_finding_preserves_human_promoted_status(tmp_path: Path) -> None:
    """Test 3: si el status humano fue promovido (CONFIRMED), no se pisa por un OPEN posterior."""
    pkg = "test-pkg-preserve"
    path = append_finding(
        pkg,
        fid="F-02",
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title="bug-original",
        expected="exp-original",
        actual="act-original",
        diff="diff-original",
    )
    # Humano promueve status a CONFIRMED editando el archivo manualmente
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "| F-02 | SHAPE | sync | OPEN |",
        "| F-02 | SHAPE | sync | CONFIRMED |",
    )
    text = text.replace(
        "**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`",
        "**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `CONFIRMED`",
    )
    path.write_text(text, encoding="utf-8")
    # Segunda llamada con un payload nuevo + status OPEN: NO debe pisar CONFIRMED
    append_finding(
        pkg,
        fid="F-02",
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title="nuevo-titulo-no-aplicar",
        expected="nuevo-exp",
        actual="nuevo-act",
        diff="nuevo-diff",
    )
    text_final = path.read_text(encoding="utf-8")
    # El status se mantiene CONFIRMED en el índice
    assert "| F-02 | SHAPE | sync | CONFIRMED |" in text_final
    # El title/expected/actual originales se preservan (no se reemplazan)
    assert "### F-02 -- bug-original" in text_final
    assert "- **Expected:** exp-original" in text_final
    assert "- **Actual:** act-original" in text_final
    # No aparece el payload nuevo
    assert "nuevo-titulo-no-aplicar" not in text_final
    assert "nuevo-exp" not in text_final


def test_append_finding_refreshes_art_block(tmp_path: Path) -> None:
    """Test 4: ART block (Timestamp + base_url + market_hours) se refresca en cada call."""
    pkg = "test-pkg-art"
    path = append_finding(
        pkg,
        fid="F-01",
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title="t",
        expected="e",
        actual="a",
        diff="d",
        base_url="https://x.test",
        market_hours="abierto",
    )
    text = path.read_text(encoding="utf-8")
    # Resolved base URL reemplazado
    assert "https://x.test" in text
    # Market hours reemplazado
    assert "abierto" in text
    # Timestamp parseable como ISO-8601
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- Timestamp:", "- **Timestamp:**")):
            # extraer el valor después de los dos puntos finales
            value = stripped.split(":", 1)[1].strip()
            # quitar markdown bold residual si está
            value = value.strip("`").strip()
            # parseable por fromisoformat
            parsed = dt.datetime.fromisoformat(value)
            assert parsed.tzinfo is not None
            break
    else:
        raise AssertionError("No se encontró línea Timestamp en el ART block")


def test_append_finding_rejects_invalid_class(tmp_path: Path) -> None:
    """Test 5: class_ debe estar en FINDING_CLASSES; ValueError si no."""
    pkg = "test-pkg-bad-class"
    with pytest.raises(ValueError, match=r"BOGUS|FINDING_CLASSES"):
        append_finding(
            pkg,
            fid="F-01",
            class_="BOGUS",
            surface="sync",
            status="OPEN",
            title="t",
            expected="e",
            actual="a",
            diff="d",
        )


def test_append_finding_rejects_invalid_status(tmp_path: Path) -> None:
    """Test 6: status debe estar en STATUS_LIFECYCLE; ValueError si no."""
    pkg = "test-pkg-bad-status"
    with pytest.raises(ValueError, match=r"WIP|STATUS_LIFECYCLE"):
        append_finding(
            pkg,
            fid="F-01",
            class_="SHAPE",
            surface="sync",
            status="WIP",
            title="t",
            expected="e",
            actual="a",
            diff="d",
        )


def test_append_finding_returns_existing_path(tmp_path: Path) -> None:
    """Test 7: retorna el Path al archivo y existe."""
    pkg = "test-pkg-return"
    path = append_finding(
        pkg,
        fid="F-01",
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title="t",
        expected="e",
        actual="a",
        diff="d",
    )
    assert isinstance(path, Path)
    assert path.exists()
    assert path.name == f"{pkg}-findings.md"


def test_append_finding_validates_constants_visible() -> None:
    """Test 8 (smoke): FINDING_CLASSES y STATUS_LIFECYCLE están exportados y son tuplas."""
    assert isinstance(FINDING_CLASSES, tuple)
    assert isinstance(STATUS_LIFECYCLE, tuple)
    assert "SHAPE" in FINDING_CLASSES
    assert "OPEN" in STATUS_LIFECYCLE


def test_append_finding_is_exported_by_barrel() -> None:
    """Test 9 (smoke): append_finding está re-exportado por el barrel verification."""
    from verification import append_finding as barrel_ap

    assert barrel_ap is append_finding
    import verification

    assert "append_finding" in verification.__all__


# ------ Regressions ------


def test_append_finding_preserves_human_prose_on_promoted_status(tmp_path: Path) -> None:
    """Regression: CR-01 — prosa/bullets/notas añadidos por un humano al
    promover un finding a CONFIRMED/FIXED/EXPECTED/NO-FIX NO se descartan en
    el round-trip de la próxima llamada a ``append_finding``.

    El bug original: ``_serialize_findings`` solo emite los 4 bullets
    canónicos (Expected/Actual/Diff/Regression). En la preservation path,
    el código re-serializaba el archivo, descartando silenciosamente todo
    lo demás. Fix: refrescar el ART block in-place sin re-serializar.
    """
    pkg = "test-pkg-prose"
    path = append_finding(
        pkg,
        fid="F-07",
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title="bug shape",
        expected="exp",
        actual="act",
        diff="d",
    )
    # Humano promueve a CONFIRMED y añade prosa, bullets extra y un párrafo
    # de triage — exactamente el patrón que el bug erase silenciosamente.
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "| F-07 | SHAPE | sync | OPEN |",
        "| F-07 | SHAPE | sync | CONFIRMED |",
    )
    text = text.replace(
        "**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`",
        "**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `CONFIRMED`",
    )
    # Insertamos prosa libre + bullets extra después del bloque del finding.
    augmented = text + (
        "- **Notes:** confirmé esto el 2026-06-04 contra prod; ver thread en Slack\n"
        "- **Repro:** `python main_ambito_financiero.py`\n"
        "\n"
        "Párrafo libre con el razonamiento de triage: el wire emite un valor\n"
        "fuera del rango plausible cuando el sample_date cae en feriado.\n"
    )
    path.write_text(augmented, encoding="utf-8")

    # Segunda llamada con un payload nuevo + status OPEN: NO debe pisar la
    # prosa humana ni los bullets extra ni el párrafo de triage.
    append_finding(
        pkg,
        fid="F-07",
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title="payload-nuevo",
        expected="exp-nuevo",
        actual="act-nuevo",
        diff="d-nuevo",
    )
    final = path.read_text(encoding="utf-8")
    # Prosa humana preservada
    assert "**Notes:**" in final
    assert "confirmé esto el 2026-06-04" in final
    assert "**Repro:**" in final
    assert "Párrafo libre con el razonamiento de triage" in final
    assert "sample_date cae en feriado" in final
    # Status canónico preservado
    assert "| F-07 | SHAPE | sync | CONFIRMED |" in final
    # El payload nuevo NO se aplicó
    assert "payload-nuevo" not in final
    assert "exp-nuevo" not in final


def test_append_finding_rejects_multiline_title(tmp_path: Path) -> None:
    """Regression: CR-02 — title con `\\n` o `\\r` debe levantar ValueError
    inmediatamente, en lugar de ser truncado silenciosamente por el regex
    del header de detalle.
    """
    pkg = "test-pkg-multiline"
    with pytest.raises(ValueError, match=r"CR-02|single-line|sola línea"):
        append_finding(
            pkg,
            fid="F-01",
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="primera línea\nsegunda línea",
            expected="e",
            actual="a",
            diff="d",
        )
    with pytest.raises(ValueError, match=r"CR-02|single-line|sola línea"):
        append_finding(
            pkg,
            fid="F-01",
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="con CR\r",
            expected="e",
            actual="a",
            diff="d",
        )


def test_findings_path_rejects_path_traversal(tmp_path: Path) -> None:
    """Regression: WR-04 — ``findings_path``/``append_finding``/``write_findings``
    deben rechazar slugs de paquete que permitirían path traversal o que
    contengan separadores de path.
    """
    bad_slugs = [
        "../etc/passwd",
        "../../tmp/x",
        "x/../y",
        "x/y",
        "x\\y",
        "UPPERCASE",
        "with space",
        ".hidden",
        "-leading-dash",
        "",
    ]
    for bad in bad_slugs:
        with pytest.raises(ValueError, match=r"invalid pkg slug"):
            findings.findings_path(bad)
        with pytest.raises(ValueError, match=r"invalid pkg slug"):
            findings.write_findings(bad)
        with pytest.raises(ValueError, match=r"invalid pkg slug"):
            append_finding(
                bad,
                fid="F-01",
                class_="SHAPE",
                surface="sync",
                status="OPEN",
                title="t",
                expected="e",
                actual="a",
                diff="d",
            )
    # Slugs válidos pasan sin error
    valid_slugs = [
        "ambito-financiero-client",
        "iol-client",
        "x",
        "x1",
        "1x",
        "abc-def-ghi",
    ]
    for ok in valid_slugs:
        # findings_path no toca disco; solo valida
        path = findings.findings_path(ok)
        assert path.parent == tmp_path
        assert path.name == f"{ok}-findings.md"
