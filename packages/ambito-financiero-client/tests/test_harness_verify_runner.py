"""Tests del clasificador del runner agregado ``main_verify`` (HARN-01 / D-14).

Cubre el contrato de clasificación de líneas (WR-01): sólo la línea del env-gate
``SKIPPED <pkg>: ...`` (con dos puntos) cuenta como SKIP de credenciales; la línea
del mutation gate ``SKIPPED (mutating, guard off)`` (sin dos puntos) NO debe
confundir una corrida exitosa con un SKIP.
"""

from __future__ import annotations

from main_verify import _ENV_SKIP


def test_env_gate_skip_line_is_classified_as_skip() -> None:
    assert _ENV_SKIP.match("SKIPPED iol-client: missing IOL_USER, IOL_PASSWORD")
    assert _ENV_SKIP.match("SKIPPED wallets-client: missing WALLETS_TOKEN")


def test_mutation_gate_line_is_not_a_credentials_skip() -> None:
    # WR-01: esta línea aparece en TODA corrida matriz con el guard apagado; no
    # debe clasificar la corrida como SKIPPED.
    assert _ENV_SKIP.match("SKIPPED (mutating, guard off)") is None


def test_arbitrary_payload_lines_are_not_skips() -> None:
    for line in ("RAN ok", "200 OK", "   algún payload: con dos puntos", ""):
        assert _ENV_SKIP.match(line) is None
