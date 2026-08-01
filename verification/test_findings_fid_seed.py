"""D-16 / D-24 — ``max_existing_fid`` seeds a driver's fid allocator above recorded findings.

Failure mode this closes: every driver keeps a module-level ``_fid_counter`` that
resets to ``0`` on each run, so run N+1 re-issues ``F-01``, ``F-02``, ... But
``append_finding`` short-circuits on any fid whose recorded status is **not**
``OPEN`` — and by construction a findings file that has been through human triage
holds only promoted statuses (``.planning/verification/market-data-client-findings.md``
carries F-01..F-36, all ``EXPECTED`` or ``FIXED``, none ``OPEN``). The result is a
write that silently becomes a no-op while the driver's SUMMARY still reports
``FINDING=N``: the run claims success having lost its deliverable.

``idempotent_by_title=True`` provably does **not** substitute for this. The title
check runs before the fid short-circuit, but it only no-ops when the title
**already exists**; a genuinely new finding carries a new title, sails past the
title check, and is then swallowed by the fid short-circuit anyway.
:func:`test_naive_allocator_write_is_swallowed_then_seeded_allocator_lands` pins
both halves of that argument.
"""

from __future__ import annotations

import pytest

from verification.findings import append_finding, findings_path, max_existing_fid, write_findings


def _add_promoted_finding(fid: str, *, title: str | None = None) -> None:
    """Agrega ``fid`` y lo promueve a FIXED — la forma real de un archivo triageado."""
    append_finding(
        "test-pkg",
        fid=fid,
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title=title or f"legacy finding {fid}",
        expected=f"expected {fid}",
        actual=f"actual {fid}",
        diff=f"diff {fid}",
    )
    path = findings_path("test-pkg")
    text = path.read_text(encoding="utf-8")
    text = text.replace(f"| {fid} | SHAPE | sync | OPEN |", f"| {fid} | SHAPE | sync | FIXED |")
    text = text.replace(
        "**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`",
        "**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`",
    )
    path.write_text(text, encoding="utf-8")


def test_max_existing_fid_returns_highest_detail_header(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F-01 .. F-36 (la forma del archivo real de market-data) devuelve 36."""
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    for n in range(1, 37):
        _add_promoted_finding(f"F-{n:02d}")

    assert max_existing_fid("test-pkg") == 36


def test_max_existing_fid_returns_zero_when_file_missing(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un paquete sin archivo de findings devuelve 0 — no debe raisear (primer run)."""
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    assert not findings_path("no-such-pkg-xyz").exists()
    assert max_existing_fid("no-such-pkg-xyz") == 0


def test_max_existing_fid_returns_zero_for_empty_skeleton(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un skeleton fresco (sin bloques de finding) devuelve 0."""
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    write_findings("test-pkg")
    assert max_existing_fid("test-pkg") == 0


def test_max_existing_fid_handles_fids_wider_than_two_digits(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sin asunción de ancho fijo: F-100 gana sobre F-99.

    El archivo de market-data cruzará 99 en ciclos posteriores; un allocator que
    asuma dos dígitos volvería a colisionar con fids ya registrados.
    """
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    _add_promoted_finding("F-99")
    _add_promoted_finding("F-100")

    assert max_existing_fid("test-pkg") == 100


def test_max_existing_fid_skips_non_numeric_fid_suffixes(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un fid no numérico (``F-XYZ``) se saltea en vez de crashear el helper."""
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    _add_promoted_finding("F-07")
    path = findings_path("test-pkg")
    text = path.read_text(encoding="utf-8")
    text += "\n### F-XYZ -- hand-written finding\n\n- **Expected:** e\n"
    path.write_text(text, encoding="utf-8")

    assert max_existing_fid("test-pkg") == 7


def test_max_existing_fid_propagates_pkg_slug_validation(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un slug rechazado propaga el error de ``findings_path`` — sin nueva superficie de traversal."""
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    with pytest.raises(ValueError, match="invalid pkg slug"):
        max_existing_fid("../etc/passwd")


def test_naive_allocator_write_is_swallowed_then_seeded_allocator_lands(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-16/D-24 — el modo de falla exacto: un write que se vuelve no-op silencioso.

    Primera mitad: un allocator que resetea a 0 re-emite ``F-01`` sobre un finding
    ya promovido a FIXED; el short-circuit lo traga y el finding nuevo NUNCA
    aparece en el archivo. Segunda mitad: seedeando el contador con
    ``max_existing_fid`` el write efectivamente aterriza.
    """
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    for n in range(1, 4):
        _add_promoted_finding(f"F-{n:02d}")
    path = findings_path("test-pkg")

    # --- allocator ingenuo (reset a 0): re-emite F-01 -> swallowed.
    naive_counter = 0
    naive_counter += 1
    naive_fid = f"F-{naive_counter:02d}"
    assert naive_fid == "F-01"
    append_finding(
        "test-pkg",
        fid=naive_fid,
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title="brand new divergence discovered this run",
        expected="e",
        actual="a",
        diff="d",
    )
    assert "brand new divergence discovered this run" not in path.read_text(encoding="utf-8"), (
        "expected the naive allocator's write to be swallowed by the non-OPEN short-circuit"
    )

    # --- allocator seedeado: arranca por encima del fid más alto registrado.
    seeded_counter = max_existing_fid("test-pkg")
    seeded_counter += 1
    seeded_fid = f"F-{seeded_counter:02d}"
    assert seeded_fid == "F-04"
    append_finding(
        "test-pkg",
        fid=seeded_fid,
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title="brand new divergence discovered this run",
        expected="e",
        actual="a",
        diff="d",
    )

    final = path.read_text(encoding="utf-8")
    assert "### F-04 -- brand new divergence discovered this run" in final, (
        f"seeded allocator write did not land.\n--- final ---\n{final}"
    )
    assert "| F-04 | SHAPE | sync | OPEN |" in final
    # Y los findings legacy siguen intactos.
    assert max_existing_fid("test-pkg") == 4
