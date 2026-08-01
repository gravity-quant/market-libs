"""HARN-07 / HARN-09 / D-23 — append_finding preserves operator content cross-runs.

Invariant: after N re-runs of ``append_finding`` against a temp findings file
that has operator-added narrative (BEFORE ``<!-- BEGIN AUTO-GENERATED -->``
and AFTER ``<!-- END AUTO-GENERATED -->``), the operator content survives
byte-identical (modulo the ART block timestamp refresh, which is permitted by
contract).

Operator-added bullet labels (``Classification:``, ``Rationale:``,
``Resolution:``) INSIDE existing finding sections survive through **two**
independent mechanisms, and the distinction matters:

1. **Same-fid re-run** — the non-OPEN short-circuit in ``append_finding``
   returns before re-serializing, so the file is never rewritten. This is the
   only guarantee this module claimed before Phase 27.
2. **New-fid append (D-23)** — a brand-new ``fid`` bypasses that short-circuit
   and forces a full re-serialization of the whole file. Until Phase 27 the
   ``_parse_findings`` → ``_serialize_findings`` round trip captured every
   bullet but forwarded only ``Expected``/``Actual``/``Diff``/``Regression``,
   so every neighbour finding's human-triage prose was silently destroyed
   (reproduced against the real 36-finding market-data file: ``Classification:``
   36→0, ``Resolution:`` 34→0, 22,201→11,561 bytes). ``_Finding.extra_bullets``
   now round-trips the unknown labels, which is what the D-23 tests below lock.

The regressions cover HARN-07 (zone parser), HARN-09 (operator bullets under
the short-circuit) and D-23 (operator bullets under re-serialization).
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


# ---------------------------------------------------------------------------
# D-23 — unknown bullets survive a FULL re-serialization (new-fid append)
# ---------------------------------------------------------------------------

_TRIAGE_BULLETS = (
    "- **Classification:** FIXED\n"
    "- **Rationale:** wire reconciled against develop\n"
    "- **Resolution:** fixed in quick task 260731-jim\n"
)


def _seed_promoted_finding_with_triage(
    tmp_path, *, fid: str = "F-01", regression: str | None = None
) -> None:
    """Crea ``fid`` vía append_finding, lo promueve a FIXED e inyecta triage prose.

    Reproduce la forma real de ``.planning/verification/market-data-client-findings.md``:
    bullets operator-added (``Classification``/``Rationale``/``Resolution``) dentro
    del bloque de detalle de un finding con status humano promovido.
    """
    append_finding(
        "test-pkg",
        fid=fid,
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title=f"neighbour finding {fid}",
        expected=f"expected {fid}",
        actual=f"actual {fid}",
        diff=f"diff {fid}",
        regression=regression,
    )
    path = findings_path("test-pkg")
    text = path.read_text(encoding="utf-8")
    text = text.replace(f"| {fid} | SHAPE | sync | OPEN |", f"| {fid} | SHAPE | sync | FIXED |")
    text = text.replace(
        "**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`",
        "**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `FIXED`",
    )
    anchor = f"- **Diff:** diff {fid}\n"
    if regression is not None:
        anchor += f"- **Regression:** {regression}\n"
    text = text.replace(anchor, anchor + _TRIAGE_BULLETS)
    path.write_text(text, encoding="utf-8")


def _append_brand_new_fid(fid: str = "F-99") -> None:
    """Fuerza la re-serialización completa del archivo (fid nuevo => no short-circuit)."""
    append_finding(
        "test-pkg",
        fid=fid,
        class_="SHAPE",
        surface="async",
        status="OPEN",
        title=f"brand new finding {fid}",
        expected="e-new",
        actual="a-new",
        diff="d-new",
    )


def test_unknown_bullets_survive_new_fid_append(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """D-23 — un fid NUEVO re-serializa todo; los bullets del vecino sobreviven.

    Labels, valores y orden relativo se preservan. Antes de Phase 27 los tres
    bullets desaparecían porque ``_Finding`` sólo transportaba cuatro labels.
    """
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    _seed_promoted_finding_with_triage(tmp_path)

    _append_brand_new_fid()

    final = findings_path("test-pkg").read_text(encoding="utf-8")
    assert "- **Classification:** FIXED" in final, (
        f"Classification bullet lost on new-fid append.\n--- final ---\n{final}"
    )
    assert "- **Rationale:** wire reconciled against develop" in final, (
        f"Rationale bullet lost on new-fid append.\n--- final ---\n{final}"
    )
    assert "- **Resolution:** fixed in quick task 260731-jim" in final, (
        f"Resolution bullet lost on new-fid append.\n--- final ---\n{final}"
    )
    # Orden relativo de captura preservado (dicts son insertion-ordered).
    assert (
        final.index("**Classification:**")
        < final.index("**Rationale:**")
        < final.index("**Resolution:**")
    ), f"relative bullet order not preserved.\n--- final ---\n{final}"
    # Y el finding nuevo efectivamente se agregó.
    assert "### F-99 -- brand new finding F-99" in final


def test_triage_bullet_counts_unchanged_after_new_fid_append(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-23 — el conteo de Classification/Resolution es idéntico antes y después.

    Esta es la forma exacta del bug reproducido contra el archivo real
    (``Classification:`` 36→0, ``Resolution:`` 34→0).
    """
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    for fid in ("F-01", "F-02", "F-03"):
        _seed_promoted_finding_with_triage(tmp_path, fid=fid)

    path = findings_path("test-pkg")
    before = path.read_text(encoding="utf-8")
    counts_before = {
        label: before.count(f"- **{label}:**")
        for label in ("Classification", "Rationale", "Resolution")
    }
    assert counts_before == {"Classification": 3, "Rationale": 3, "Resolution": 3}

    _append_brand_new_fid()

    after = path.read_text(encoding="utf-8")
    counts_after = {
        label: after.count(f"- **{label}:**")
        for label in ("Classification", "Rationale", "Resolution")
    }
    assert counts_after == counts_before, (
        f"triage bullet counts changed: {counts_before} -> {counts_after}"
    )


def test_serializer_output_unchanged_when_no_unknown_bullets(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-23 — la preservación es puramente aditiva: sin bullets extra, nada cambia.

    Un archivo cuyos findings sólo tienen los cuatro bullets canónicos se
    serializa exactamente igual que antes del cambio: el bloque de detalle es
    byte-idéntico al golden y el set de labels emitidos no crece.
    """
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    append_finding(
        "test-pkg",
        fid="F-01",
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title="plain finding",
        expected="e1",
        actual="a1",
        diff="d1",
    )
    path = findings_path("test-pkg")
    golden_block = (
        "### F-01 -- plain finding\n"
        "\n"
        "**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`\n"
        "\n"
        "- **Expected:** e1\n"
        "- **Actual:** a1\n"
        "- **Diff:** d1\n"
    )
    assert golden_block in path.read_text(encoding="utf-8")

    _append_brand_new_fid()

    final = path.read_text(encoding="utf-8")
    # El bloque de F-01 sigue byte-idéntico tras la re-serialización completa.
    assert golden_block in final, f"F-01 block changed.\n--- final ---\n{final}"
    # Y no aparecieron labels nuevos en ninguna parte del archivo.
    emitted_labels = {
        line.split("**")[1].rstrip(":") for line in final.splitlines() if line.startswith("- **")
    }
    assert emitted_labels == {"Expected", "Actual", "Diff"}, emitted_labels


def test_regression_bullet_not_duplicated_into_extras(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-23 — ``Regression`` sigue siendo first-class y NO se duplica en los extras.

    Un finding que lleva ``Regression`` **y** bullets desconocidos debe emitir
    exactamente un ``- **Regression:**`` tras el round trip.
    """
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
    regression = (
        "packages/market-data-client/tests/test_models.py::test_from_api_none_does_not_raise"
    )
    _seed_promoted_finding_with_triage(tmp_path, regression=regression)

    _append_brand_new_fid()

    final = findings_path("test-pkg").read_text(encoding="utf-8")
    assert final.count("- **Regression:**") == 1, (
        f"Regression bullet duplicated or lost.\n--- final ---\n{final}"
    )
    assert f"- **Regression:** {regression}" in final
    # Y los extras siguen presentes junto al Regression canónico.
    assert "- **Classification:** FIXED" in final
