"""Contrato del sobre de evidencia de corrida (Phase 39, D-09 + D-10).

Estructural y offline: sólo escribe y lee JSON bajo un ``tmp_path``. Ningún
paquete se importa, ninguna red se toca, ningún cliente se construye.

Lo que este archivo pinea, en una frase: que el sobre pueda decir *"esta corrida
ejecutó N probes y vio estas triples"* — y, cuando N es cero, *por qué* y *hacia
dónde*. Sin eso, la ausencia de findings y la ausencia de corrida son el mismo
silencio, que es exactamente el PASS vacuo que D-09 prohíbe.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from verification import run_evidence
from verification.run_evidence import (
    probes_executed,
    read_run_evidence,
    run_evidence_path,
    write_run_evidence,
)

_TRIPLES = [
    ("iol-client", "Quote", ".ultimoPrecio", "type_mismatch"),
    ("iol-client", "Quote", ".apertura", "missing_field"),
    ("iol-client", "Instrument", ".simbolo", "type_mismatch"),
]

_COUNTS = {"PASS": 12, "FAIL": 0, "SKIPPED": 2, "FINDING": 1}


@pytest.fixture
def evidence_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirige el directorio de sobres a ``tmp_path``.

    El directorio real (``.planning/verification/run-evidence/``) se deriva de
    ``__file__`` y nunca de un input; acá se sustituye el global del módulo para
    que la suite no escriba en el árbol versionado.
    """
    target = tmp_path / "run-evidence"
    monkeypatch.setattr(run_evidence, "_RUN_EVIDENCE_DIR", target)
    return target


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------


def test_round_trip_preserva_las_tres_triples(evidence_dir: Path) -> None:
    """Escribir 3 triples y leerlas devuelve las mismas 3."""
    write_run_evidence("iol-client", driver="main_iol.py", triples=_TRIPLES, counts=_COUNTS)
    envelope = read_run_evidence("iol-client")

    assert envelope is not None
    assert envelope["n_triples"] == 3
    assert [tuple(t) for t in envelope["triples"]] == sorted(_TRIPLES)


def test_el_sobre_lleva_los_campos_del_contrato(evidence_dir: Path) -> None:
    """Las claves del sobre son exactamente las declaradas — ni una más."""
    write_run_evidence("iol-client", driver="main_iol.py", triples=_TRIPLES, counts=_COUNTS)
    envelope = read_run_evidence("iol-client")

    assert envelope is not None
    assert set(envelope) == {
        "slug",
        "driver",
        "captured_at",
        "counts",
        "probes_executed",
        "n_triples",
        "triples",
        "skipped",
    }, (
        "el set de claves del sobre cambió. Este sobre se versiona: cada campo "
        "nuevo es una superficie nueva de information disclosure (T-39-10). "
        "Agregar un campo que transporte un valor de wire está prohibido."
    )
    assert envelope["slug"] == "iol-client"
    assert envelope["driver"] == "main_iol.py"
    assert envelope["counts"] == _COUNTS
    assert envelope["skipped"] is None


def test_probes_executed_es_la_suma_de_los_conteos(evidence_dir: Path) -> None:
    """El predicado de no-vacuidad es el conteo de probes, no el de findings."""
    write_run_evidence("iol-client", driver="main_iol.py", triples=_TRIPLES, counts=_COUNTS)

    assert probes_executed("iol-client") == 15  # 12 + 0 + 2 + 1
    envelope = read_run_evidence("iol-client")
    assert envelope is not None
    assert envelope["probes_executed"] == 15


def test_captured_at_es_iso8601_utc(evidence_dir: Path) -> None:
    """``captured_at`` parsea como datetime con timezone UTC."""
    import datetime as dt

    write_run_evidence("iol-client", driver="main_iol.py", triples=_TRIPLES, counts=_COUNTS)
    envelope = read_run_evidence("iol-client")

    assert envelope is not None
    parsed = dt.datetime.fromisoformat(envelope["captured_at"])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == dt.timedelta(0)


# ---------------------------------------------------------------------------
# Determinismo
# ---------------------------------------------------------------------------


def test_el_orden_de_las_triples_es_estable(evidence_dir: Path) -> None:
    """Dos escrituras con el mismo contenido en distinto orden dan el mismo orden."""
    write_run_evidence("iol-client", driver="main_iol.py", triples=_TRIPLES, counts=_COUNTS)
    first = read_run_evidence("iol-client")

    write_run_evidence(
        "iol-client",
        driver="main_iol.py",
        triples=list(reversed(_TRIPLES)),
        counts=_COUNTS,
    )
    second = read_run_evidence("iol-client")

    assert first is not None
    assert second is not None
    assert first["triples"] == second["triples"], (
        "el orden de las triples depende del orden de iteración del set del "
        "handler. Un sobre no determinístico produce diffs de git espurios y "
        "hace imposible contrastar dos corridas por diferencia de conjuntos."
    )


def test_un_set_de_python_produce_orden_estable(evidence_dir: Path) -> None:
    """La entrada real es ``handler.seen``, un ``set``. El sobre igual ordena."""
    write_run_evidence("iol-client", driver="main_iol.py", triples=set(_TRIPLES), counts=_COUNTS)
    envelope = read_run_evidence("iol-client")

    assert envelope is not None
    assert [tuple(t) for t in envelope["triples"]] == sorted(_TRIPLES)


def test_las_triples_se_deduplican(evidence_dir: Path) -> None:
    """Una triple repetida en la entrada aparece una sola vez en el sobre."""
    write_run_evidence(
        "iol-client",
        driver="main_iol.py",
        triples=[*_TRIPLES, _TRIPLES[0]],
        counts=_COUNTS,
    )
    envelope = read_run_evidence("iol-client")

    assert envelope is not None
    assert envelope["n_triples"] == 3


# ---------------------------------------------------------------------------
# Reescritura, no append
# ---------------------------------------------------------------------------


def test_la_segunda_escritura_reemplaza_a_la_primera(evidence_dir: Path) -> None:
    """El sobre describe LA ÚLTIMA corrida (T-39-12).

    Una corrida saltada tiene que poder invalidar el sobre de una corrida
    anterior; si el archivo acumulara, el sobre viejo se leería como evidencia
    de esta corrida.
    """
    write_run_evidence("matriz-client", driver="main_matriz.py", triples=_TRIPLES, counts=_COUNTS)
    assert probes_executed("matriz-client") == 15

    write_run_evidence(
        "matriz-client",
        driver="main_matriz.py",
        triples=[],
        counts={},
        skipped="base URL fuera del allowlist D-MATZ-33 — LIVE-MATZ-33",
    )

    envelope = read_run_evidence("matriz-client")
    assert envelope is not None
    assert envelope["triples"] == []
    assert envelope["n_triples"] == 0
    assert probes_executed("matriz-client") == 0


# ---------------------------------------------------------------------------
# Cero probes / ausencia / corrupción
# ---------------------------------------------------------------------------


def test_sobre_ausente(evidence_dir: Path) -> None:
    """Sin sobre: ``read`` devuelve ``None`` y ``probes_executed`` devuelve 0."""
    assert read_run_evidence("higyrus-client") is None
    assert probes_executed("higyrus-client") == 0


def test_cero_probes_con_causa_medida(evidence_dir: Path) -> None:
    """Un sobre de corrida saltada lleva 0 probes y la causa legible."""
    write_run_evidence(
        "higyrus-client",
        driver="main_higyrus.py",
        triples=[],
        counts={},
        skipped="vendor host unreachable (DNS) — LIVE-HIGY-33",
    )

    assert probes_executed("higyrus-client") == 0
    envelope = read_run_evidence("higyrus-client")
    assert envelope is not None
    assert envelope["skipped"] == "vendor host unreachable (DNS) — LIVE-HIGY-33"
    assert "LIVE-HIGY-33" in envelope["skipped"], (
        "la causa del skip perdió su destino nombrado. Un deferral sin destino "
        "es exactamente lo que P-03 prohíbe."
    )


def test_json_corrupto_no_lanza(evidence_dir: Path) -> None:
    """Un sobre ilegible se reporta como ausencia, nunca como excepción."""
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "iol-client.json").write_text("{ no soy json", encoding="utf-8")

    assert read_run_evidence("iol-client") is None
    assert probes_executed("iol-client") == 0


def test_json_valido_pero_no_objeto_no_lanza(evidence_dir: Path) -> None:
    """Un JSON top-level que no es objeto tampoco rompe el lector."""
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "iol-client.json").write_text("[1, 2, 3]", encoding="utf-8")

    assert read_run_evidence("iol-client") is None
    assert probes_executed("iol-client") == 0


def test_probes_executed_no_entero_devuelve_cero(evidence_dir: Path) -> None:
    """Un sobre editado a mano con basura en el conteo no promueve un PASS."""
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "iol-client.json").write_text(
        json.dumps({"probes_executed": "muchos"}), encoding="utf-8"
    )

    assert probes_executed("iol-client") == 0


# ---------------------------------------------------------------------------
# Guarda de slug (T-39-09 — path traversal)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hostile",
    [
        "../../etc/passwd",
        "..",
        "/etc/passwd",
        "iol-client/../../x",
        "IOL-CLIENT",
        "iol client",
        "",
        "-iol",
    ],
)
def test_slug_hostil_no_escribe_nada(hostile: str, evidence_dir: Path, tmp_path: Path) -> None:
    """Un slug fuera de la forma permitida levanta ``ValueError`` y no escribe."""
    with pytest.raises(ValueError, match="invalid pkg slug"):
        write_run_evidence(hostile, driver="main_iol.py", triples=_TRIPLES, counts=_COUNTS)

    escritos = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert escritos == [], f"un slug hostil escribió archivos: {escritos}"


def test_run_evidence_path_queda_bajo_el_directorio(evidence_dir: Path) -> None:
    """La ruta resuelta de un slug válido está contenida en el directorio."""
    path = run_evidence_path("ambito-financiero-client")

    assert path.parent == evidence_dir
    assert path.name == "ambito-financiero-client.json"


def test_la_guarda_de_slug_es_la_de_findings() -> None:
    """El módulo reutiliza el validador de ``verification.findings``.

    Un segundo regex de slug es una segunda superficie que puede divergir: si
    uno se afloja, el otro sigue verde y la protección se pierde en el sitio
    equivocado.
    """
    from verification import findings

    assert run_evidence._validate_pkg_slug is findings._validate_pkg_slug


# ---------------------------------------------------------------------------
# El directorio real
# ---------------------------------------------------------------------------


def test_el_directorio_real_deriva_de_file() -> None:
    """Sin monkeypatch, el directorio cuelga de ``.planning/verification/``."""
    assert run_evidence._RUN_EVIDENCE_DIR.name == "run-evidence"
    assert run_evidence._RUN_EVIDENCE_DIR.parent.name == "verification"
    assert run_evidence._RUN_EVIDENCE_DIR.parent.parent.name == ".planning"


def test_los_cuatro_nombres_se_reexportan() -> None:
    """``verification.__all__`` expone la superficie pública del módulo."""
    import verification

    for name in (
        "probes_executed",
        "read_run_evidence",
        "run_evidence_path",
        "write_run_evidence",
    ):
        assert name in verification.__all__
        assert hasattr(verification, name)
