"""CR-04 -- main_matriz.py ``_first_dict`` distinguishes no_data / wrong_type / ok.

Pre-Phase-11 ``_first_dict`` collapse 3 distinct cases into a single ``None``
return: (a) ok = list-with-first-dict -> return dict; (b) no_data = empty list
-> return None silently (LEGITIMATE); (c) wrong_type = non-list-payload OR
first-element-not-a-dict -> return None silently (BUG: caller cannot
distinguish from no_data).

Phase 11 CR-04 fix: ``_first_dict`` accepts a new ``fname=`` kwarg; when set,
case (c) emits a SHAPE finding via ``append_finding`` so the diagnostic trail
correctly identifies the wrong_type case. Case (a) returns the dict; case (b)
remains silent (no_data is legitimate, empty payloads are expected during
off-market windows).
"""

from __future__ import annotations

from pathlib import Path

import main_matriz
import pytest

from verification import findings as findings_module


@pytest.fixture(autouse=True)
def _isolate_findings_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Aisla el directorio de findings a tmp_path para que cada test sea hermético."""
    monkeypatch.setattr(findings_module, "_FINDINGS_DIR", tmp_path)
    # Reset el contador de fids para fids deterministicos.
    main_matriz._fid_counter = 0


def test_first_dict_ok_returns_dict_no_finding(tmp_path: Path) -> None:
    """Caso (a) ok: list[dict, ...] -> returns first dict, NO finding emitted."""
    result = main_matriz._first_dict([{"a": 1, "b": 2}], fname="get_segments")
    assert result == {"a": 1, "b": 2}
    # Ningún finding debe haberse emitido.
    findings_file = tmp_path / "matriz-client-findings.md"
    if findings_file.exists():
        text = findings_file.read_text(encoding="utf-8")
        assert "get_segments: payload" not in text


def test_first_dict_empty_list_returns_none_no_finding(tmp_path: Path) -> None:
    """Caso (b) no_data: [] -> returns None, NO finding emitted (legitimate)."""
    result = main_matriz._first_dict([], fname="get_segments")
    assert result is None
    findings_file = tmp_path / "matriz-client-findings.md"
    if findings_file.exists():
        text = findings_file.read_text(encoding="utf-8")
        assert "get_segments: payload" not in text


def test_first_dict_non_list_payload_emits_shape_finding(tmp_path: Path) -> None:
    """Caso (c1) wrong_type: payload no es list -> returns None AND emits SHAPE."""
    # Pasar un dict (no list) -- es el wrong_type clasico que el bug-pre-Phase-11
    # ocultaba como si fuera no_data.
    result = main_matriz._first_dict({"not": "a list"}, fname="get_segments")
    assert result is None
    findings_file = tmp_path / "matriz-client-findings.md"
    assert findings_file.exists(), "expected findings file to be created"
    text = findings_file.read_text(encoding="utf-8")
    assert "get_segments" in text
    assert "payload no es list" in text or "no es list" in text


def test_first_dict_first_element_not_dict_emits_shape_finding(tmp_path: Path) -> None:
    """Caso (c2) wrong_type: list[non-dict] -> returns None AND emits SHAPE."""
    # list cuyo primer elemento NO es dict (e.g. list de strings).
    result = main_matriz._first_dict(["not-a-dict"], fname="get_segments")
    assert result is None
    findings_file = tmp_path / "matriz-client-findings.md"
    assert findings_file.exists()
    text = findings_file.read_text(encoding="utf-8")
    assert "get_segments" in text
    assert "no es dict" in text or "payload[0]" in text


def test_first_dict_no_fname_silent_no_finding(tmp_path: Path) -> None:
    """Backwards-compat: fname=None -> silent fallback, NO finding emitted.

    Garantiza que los call-sites pre-existing que no pasan fname siguen
    obteniendo el comportamiento legacy (silent None para wrong_type).
    """
    result = main_matriz._first_dict({"not": "a list"})  # fname omitted (None)
    assert result is None
    findings_file = tmp_path / "matriz-client-findings.md"
    if findings_file.exists():
        text = findings_file.read_text(encoding="utf-8")
        assert "payload no es list" not in text
