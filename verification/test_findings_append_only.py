"""HARN-07 / HARN-09 — append_finding preserves operator content cross-runs.

Invariant: after N re-runs of ``append_finding`` against a temp findings file
that has operator-added narrative (BEFORE ``<!-- BEGIN AUTO-GENERATED -->``
and AFTER ``<!-- END AUTO-GENERATED -->``), the operator content survives
byte-identical (modulo the ART block timestamp refresh, which is permitted by
contract). Operator-added bullet labels (``Classification:``, ``Rationale:``,
``Resolution:``) INSIDE existing finding sections also survive verbatim when
the finding status is promoted off OPEN (existing preservation guard kicks
in — line 473 of ``verification/findings.py``).

The regression covers HARN-07 (zone parser) + HARN-09 (operator bullets).
"""

from __future__ import annotations

import hashlib

import pytest

from verification.findings import append_finding, findings_path, new_findings, write_findings

_OPERATOR_PREFIX_BLOB = (
    "## Operator Narrative\n"
    "Classification: NO-FIX (out of scope v1.1)\n"
    "Rationale: matriz-only divergence, acknowledged limitation.\n"
    "\n"
)

_OPERATOR_SUFFIX_BLOB = (
    "\n"
    "## Operator Triage Notes\n"
    "Rationale: matriz-only divergence\n"
    "Resolution: documented in CYCLE-REPORT.md\n"
)


def _seed_with_operator_content(tmp_path, prefix: str, suffix: str) -> None:
    """Crea el archivo skeleton + inyecta operator prefix arriba y suffix abajo."""
    skeleton = new_findings("test-pkg")
    text = prefix + skeleton + suffix
    (tmp_path / "test-pkg-findings.md").write_text(text, encoding="utf-8")


def test_markers_present_in_freshly_written_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``new_findings`` emite los markers BEGIN/END exactly once each en el skeleton."""
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    path = write_findings("test-pkg")
    text = path.read_text(encoding="utf-8")
    assert text.count("<!-- BEGIN AUTO-GENERATED -->") == 1, (
        f"BEGIN marker count != 1 in skeleton:\n{text}"
    )
    assert text.count("<!-- END AUTO-GENERATED -->") == 1, (
        f"END marker count != 1 in skeleton:\n{text}"
    )


def test_operator_prefix_survives_N_runs(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """HARN-07 — operator narrative ABOVE el marker BEGIN sobrevive N=3 re-runs."""
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    _seed_with_operator_content(tmp_path, _OPERATOR_PREFIX_BLOB, "")

    prefix_sha_initial = hashlib.sha256(_OPERATOR_PREFIX_BLOB.encode()).hexdigest()

    for _ in range(3):
        append_finding(
            "test-pkg",
            fid="F-01",
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="dummy title",
            expected="e",
            actual="a",
            diff="d",
        )

    final = findings_path("test-pkg").read_text(encoding="utf-8")
    assert _OPERATOR_PREFIX_BLOB in final, (
        f"operator prefix NOT preserved after 3 runs.\n--- final ---\n{final}"
    )
    # SHA256 stability of the operator prefix substring.
    idx = final.index(_OPERATOR_PREFIX_BLOB)
    prefix_sha_final = hashlib.sha256(
        final[idx : idx + len(_OPERATOR_PREFIX_BLOB)].encode()
    ).hexdigest()
    assert prefix_sha_initial == prefix_sha_final


def test_operator_suffix_survives_N_runs(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """HARN-07 — operator narrative BELOW el marker END sobrevive N=3 re-runs."""
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    _seed_with_operator_content(tmp_path, "", _OPERATOR_SUFFIX_BLOB)

    suffix_sha_initial = hashlib.sha256(_OPERATOR_SUFFIX_BLOB.encode()).hexdigest()

    for _ in range(3):
        append_finding(
            "test-pkg",
            fid="F-01",
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="dummy title",
            expected="e",
            actual="a",
            diff="d",
        )

    final = findings_path("test-pkg").read_text(encoding="utf-8")
    assert _OPERATOR_SUFFIX_BLOB in final, (
        f"operator suffix NOT preserved after 3 runs.\n--- final ---\n{final}"
    )
    idx = final.index(_OPERATOR_SUFFIX_BLOB)
    suffix_sha_final = hashlib.sha256(
        final[idx : idx + len(_OPERATOR_SUFFIX_BLOB)].encode()
    ).hexdigest()
    assert suffix_sha_initial == suffix_sha_final


def test_operator_bullets_inside_findings_survive(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HARN-09 — Classification/Resolution bullets INSIDE finding sections sobreviven.

    Si un humano promueve F-01 a EXPECTED y añade bullets ``- **Classification:**``
    y ``- **Resolution:**`` dentro de la sección, el preservation guard existente
    (line 473) en ``append_finding`` evita re-serializar — sólo refresca ART block.
    """
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)

    # Inicialmente OPEN.
    append_finding(
        "test-pkg",
        fid="F-01",
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title="some shape diff",
        expected="cliente espera X",
        actual="API devuelve sin X",
        diff="key X ausente",
    )

    # Operator promueve a EXPECTED + añade bullets adicionales.
    path = findings_path("test-pkg")
    text = path.read_text(encoding="utf-8")
    # Promote Index row + Detalle meta.
    text = text.replace("| F-01 | SHAPE | sync | OPEN |", "| F-01 | SHAPE | sync | EXPECTED |")
    text = text.replace(
        "**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`",
        "**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `EXPECTED`",
    )
    # Inject operator bullets at end of F-01 section (after `- **Diff:**`).
    operator_bullets = (
        "- **Classification:** NO-FIX (rationale: scope v1.1)\n"
        "- **Rationale:** matriz-only divergence acknowledged\n"
        "- **Resolution:** acknowledged limitation, documented\n"
    )
    text = text.replace(
        "- **Diff:** key X ausente\n",
        "- **Diff:** key X ausente\n" + operator_bullets,
    )
    path.write_text(text, encoding="utf-8")

    # Re-run append_finding 3 veces con status="OPEN" -- debe NO-OP (preservation guard).
    for _ in range(3):
        append_finding(
            "test-pkg",
            fid="F-01",
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="some shape diff",
            expected="cliente espera X",
            actual="API devuelve sin X",
            diff="key X ausente",
        )

    final = path.read_text(encoding="utf-8")
    assert "**Classification:** NO-FIX (rationale: scope v1.1)" in final, (
        f"Operator Classification bullet lost.\n--- final ---\n{final}"
    )
    assert "**Rationale:** matriz-only divergence acknowledged" in final, (
        f"Operator Rationale bullet lost.\n--- final ---\n{final}"
    )
    assert "**Resolution:** acknowledged limitation, documented" in final, (
        f"Operator Resolution bullet lost.\n--- final ---\n{final}"
    )
    # Status promotion también preservado.
    assert "| F-01 | SHAPE | sync | EXPECTED |" in final
