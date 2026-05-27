"""Cobertura unitaria de redact() y safe_print() (HARN-03).

Incluye el guard de secreto vacío/corto (Pitfall 3 — `str.replace("", marker)`
inserta el marcador entre cada caracter, bug verificado concourse #4656).
"""

from __future__ import annotations

import pytest
from verification.redaction import redact, safe_print


def test_redact_devuelve_prefijo_y_elipsis() -> None:
    result = redact("supersecret-token")
    assert result == "supe…"
    assert result != "supersecret-token"
    # Prueba estructural: el valor completo nunca se devuelve.
    assert len(result) == 5


def test_redact_vacio_devuelve_marcador() -> None:
    assert redact("") == "<empty>"
    assert redact(None) == "<empty>"


def test_redact_corto_devuelve_solo_elipsis() -> None:
    # len(value) <= keep -> demasiado corto para mostrar prefijo de forma segura.
    assert redact("ab") == "…"
    assert redact("abcd") == "…"


def test_redact_keep_personalizado() -> None:
    assert redact("supersecret-token", keep=6) == "supers…"


def test_safe_print_enmascara_secreto_conocido(capsys: pytest.CaptureFixture[str]) -> None:
    safe_print("x supersecret-token y", ["supersecret-token"])
    captured = capsys.readouterr()
    assert captured.out == "x ‹REDACTED› y\n"  # noqa: RUF001


def test_safe_print_secreto_vacio_o_corto_no_corrompe(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Pitfall 3: secretos vacíos/cortos NUNCA se insertan entre caracteres.
    safe_print("hello world", ["", "ab"])
    captured = capsys.readouterr()
    assert captured.out == "hello world\n"
    assert "‹REDACTED›" not in captured.out  # noqa: RUF001
