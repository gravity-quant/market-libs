"""Unit tests for the harness env-var gate (HARN-01 / D-15).

Cubre el contrato de :func:`verification.env_gate.require_env`:

- imprime la línea verbatim ``SKIPPED <pkg>: missing X, Y`` cuando faltan vars,
- lista sólo las vars realmente ausentes (caso parcial),
- devuelve ``True`` sin imprimir nada cuando están todas,
- nunca lanza excepción ni llama a ``sys.exit`` (el driver decide salir).

Se usan los nombres canónicos de IOL (``IOL_USER`` / ``IOL_PASSWORD``) para que
las aserciones de stdout sean concretas.
"""

from __future__ import annotations

import pytest

from verification.env_gate import require_env


def test_all_missing_prints_verbatim_skipped_line_and_returns_false(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("IOL_USER", raising=False)
    monkeypatch.delenv("IOL_PASSWORD", raising=False)

    result = require_env("iol-client", ["IOL_USER", "IOL_PASSWORD"])

    assert result is False
    captured = capsys.readouterr()
    assert captured.out == "SKIPPED iol-client: missing IOL_USER, IOL_PASSWORD\n"


def test_partial_missing_lists_only_absent_var(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("IOL_USER", "alice")
    monkeypatch.delenv("IOL_PASSWORD", raising=False)

    result = require_env("iol-client", ["IOL_USER", "IOL_PASSWORD"])

    assert result is False
    captured = capsys.readouterr()
    assert captured.out == "SKIPPED iol-client: missing IOL_PASSWORD\n"


def test_all_present_returns_true_and_prints_nothing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("IOL_USER", "alice")
    monkeypatch.setenv("IOL_PASSWORD", "secret")

    result = require_env("iol-client", ["IOL_USER", "IOL_PASSWORD"])

    assert result is True
    captured = capsys.readouterr()
    assert captured.out == ""


def test_never_raises_or_exits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IOL_USER", raising=False)
    monkeypatch.delenv("IOL_PASSWORD", raising=False)

    # Si require_env llamara a sys.exit, esto levantaría SystemExit y el test
    # fallaría; el contrato (Pitfall 6) es devolver un bool sin salir.
    result = require_env("iol-client", ["IOL_USER", "IOL_PASSWORD"])

    assert result is False
