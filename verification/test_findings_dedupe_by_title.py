"""HARN-08 / HARN-10 -- content-addressed dedupe by title in ``append_finding``.

Invariant (parametric x 4 packages): cuando ``append_finding`` se invoca
N=5 veces con DISTINTOS ``fid`` pero MISMO ``title`` y
``idempotent_by_title=True``, el archivo de findings contiene exactamente
**una** ocurrencia del title. Esto cierra HARN-08 (cross-driver content-addressed
dedupe) y HARN-10 (matriz ``D-MATZ-27`` EXPECTED terminal dedupe en 1 run).

Backwards-compat: omitir el kwarg preserva el comportamiento legacy fid-based —
el run repetido con MISMO fid actualiza in-place, con fids distintos crea
entradas separadas.
"""

from __future__ import annotations

import pytest

from verification.findings import append_finding, findings_path

_PACKAGES = ["ambito-financiero-client", "iol-client", "higyrus-client", "matriz-client"]

_DEDUPE_TITLE = "prod-vs-remarkets divergence acknowledged"


@pytest.mark.parametrize("pkg", _PACKAGES)
def test_idempotent_by_title_does_not_duplicate(
    pkg: str, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """5 calls con distintos fid + mismo title + idempotent_by_title=True → 1 entrada."""
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    for i in range(5):
        append_finding(
            pkg,
            fid=f"F-{i:02d}",
            class_="SHAPE",
            surface="sync",
            status="EXPECTED",
            title=_DEDUPE_TITLE,
            expected="verification limited to remarkets sandbox",
            actual="prod shape unverified",
            diff="N/A (acknowledged limitation)",
            idempotent_by_title=True,
        )

    text = findings_path(pkg).read_text(encoding="utf-8")
    occurrences = text.count(_DEDUPE_TITLE)
    assert occurrences == 1, (
        f"expected 1 occurrence of title, got {occurrences} in {pkg} file\n--- text ---\n{text}"
    )


@pytest.mark.parametrize("pkg", _PACKAGES)
def test_idempotent_by_title_preserves_existing_finding(
    pkg: str, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El second call con mismo title y idempotent_by_title=True es no-op."""
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)

    # First call — finding original con fid=F-00.
    append_finding(
        pkg,
        fid="F-00",
        class_="SHAPE",
        surface="sync",
        status="EXPECTED",
        title=_DEDUPE_TITLE,
        expected="original-expected",
        actual="original-actual",
        diff="original-diff",
        idempotent_by_title=True,
    )

    # Second call — distinto fid pero MISMO title; debe ser no-op (no actualiza
    # los fields original).
    append_finding(
        pkg,
        fid="F-99",
        class_="SHAPE",
        surface="sync",
        status="EXPECTED",
        title=_DEDUPE_TITLE,
        expected="WOULD-OVERWRITE-EXPECTED",
        actual="WOULD-OVERWRITE-ACTUAL",
        diff="WOULD-OVERWRITE-DIFF",
        idempotent_by_title=True,
    )

    text = findings_path(pkg).read_text(encoding="utf-8")
    # Original fields preservados.
    assert "original-expected" in text, (
        f"original Expected field overwritten — idempotent_by_title broke contract\n{text}"
    )
    assert "original-actual" in text
    assert "original-diff" in text
    # Mutaciones del segundo call NO aplicadas.
    assert "WOULD-OVERWRITE-EXPECTED" not in text
    assert "WOULD-OVERWRITE-ACTUAL" not in text
    # El fid no añadido.
    assert "F-99" not in text


@pytest.mark.parametrize("pkg", _PACKAGES)
def test_idempotent_by_title_default_false_still_duplicates(
    pkg: str, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Backwards-compat: sin el kwarg, 5 calls con fids distintos crean 5 entradas."""
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    for i in range(5):
        append_finding(
            pkg,
            fid=f"F-{i:02d}",
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title=_DEDUPE_TITLE,
            expected="e",
            actual="a",
            diff="d",
            # Sin idempotent_by_title: default False.
        )

    text = findings_path(pkg).read_text(encoding="utf-8")
    # Sin el kwarg, cada fid genera su propio bloque -- title aparece 5 veces
    # en los headers de detalle.
    title_occurrences = text.count(_DEDUPE_TITLE)
    assert title_occurrences == 5, (
        f"expected 5 occurrences without idempotent_by_title, got {title_occurrences} in {pkg}"
    )
    # Y los 5 fids aparecen en la Index table.
    for i in range(5):
        assert f"| F-{i:02d} |" in text, f"F-{i:02d} missing from index in {pkg}"
