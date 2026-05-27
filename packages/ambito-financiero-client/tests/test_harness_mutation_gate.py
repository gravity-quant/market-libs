"""Unit tests for the harness mutation gate (HARN-02 / D-16).

Cubre el doble gate de :func:`verification.mutation_gate.mutating_allowed`:

- flag ``VERIFY_MUTATING`` ausente -> bloqueado, imprime la línea verbatim,
- flag activa + base URL remarkets -> permitido, sin output,
- **adversarial**: flag activa pero base URL de prod -> bloqueado (no bypass),
- flag con valor distinto de ``"1"`` -> tratado como apagado.

La base URL se lee en vivo desde ``matriz_client.client._base_url`` al momento
del guard (Pitfall 5), por eso los tests parchean ese atributo de módulo.
"""

from __future__ import annotations

import pytest
from verification.mutation_gate import mutating_allowed

import matriz_client

_SKIP_LINE = "SKIPPED (mutating, guard off)\n"


def test_flag_off_blocks_and_prints_verbatim_line(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("VERIFY_MUTATING", raising=False)
    # Aun con una URL remarkets, sin la flag debe bloquear.
    monkeypatch.setattr(
        matriz_client.client,
        "_base_url",
        "https://api.remarkets.primary.com.ar",
        raising=False,
    )

    result = mutating_allowed()

    assert result is False
    captured = capsys.readouterr()
    assert captured.out == _SKIP_LINE


def test_flag_on_with_remarkets_url_allows_and_prints_nothing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("VERIFY_MUTATING", "1")
    monkeypatch.setattr(
        matriz_client.client,
        "_base_url",
        "https://api.remarkets.primary.com.ar",
        raising=False,
    )

    result = mutating_allowed()

    assert result is True
    captured = capsys.readouterr()
    assert captured.out == ""


def test_flag_on_with_prod_url_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Test de seguridad load-bearing: aunque la flag esté activa, una base URL
    # de producción (sin 'remarkets') nunca debe permitir mutaciones.
    monkeypatch.setenv("VERIFY_MUTATING", "1")
    monkeypatch.setattr(
        matriz_client.client,
        "_base_url",
        "https://api.primary.com.ar",
        raising=False,
    )

    result = mutating_allowed()

    assert result is False
    captured = capsys.readouterr()
    assert captured.out == _SKIP_LINE


def test_flag_set_to_non_one_is_treated_as_off(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        matriz_client.client,
        "_base_url",
        "https://api.remarkets.primary.com.ar",
        raising=False,
    )
    for value in ("true", "0", "yes", ""):
        monkeypatch.setenv("VERIFY_MUTATING", value)
        result = mutating_allowed()
        assert result is False
        captured = capsys.readouterr()
        assert captured.out == _SKIP_LINE
