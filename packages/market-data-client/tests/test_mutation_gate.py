"""Tests adversariales del gate de mutaciones (GATE-MD-01, Plan 25-01).

Estos son tests a NIVEL HELPER: ``_ensure_mutation_allowed()`` es una lectura
pura de estado (sin IO), así que se ejercita directamente — todavía no existe
ningún método mutador (los end-to-end de cero-request-en-refusal via
``create_symbol`` llegan en el Plan 03).

Cubren, para AMBAS superficies (sync ``market_data_client`` + async ``aio``):
  (a) refuse-by-default → ``MarketDataMutationNotAllowedError``
  (b) gate abierto + host coincidente → no lanza
  (c) gate abierto + host distinto → lanza (mismatch exacto)
  (d) host substring-attacker → lanza (prueba match EXACTO, no substring)
  (e) ``expected_host = None`` deshabilita SÓLO la pata del host (flag vigente)
  (f) sentinel carry-forward: ``configure(base_url=...)`` no resetea el flag
  (g) herencia del gate en views (``with_options``, ``_state`` compartido)
"""

from __future__ import annotations

import pytest

import market_data_client
from market_data_client import aio
from market_data_client.exceptions import MarketDataMutationNotAllowedError

# Host develop real (default de ``expected_host``) y su superstring adversarial.
_DEVELOP_HOST = "market-data-develop.bbsa.com.ar"
_ATTACKER_HOST = "market-data-develop.bbsa.com.ar.attacker.example"
# Host del conftest (base_url sembrado en el default singleton).
_CONFTEST_HOST = "market-data-develop.test"


# ----------------------------------------------------------------------
# (a) refuse-by-default
# ----------------------------------------------------------------------


def test_default_client_refuses_mutation_sync() -> None:
    client = market_data_client.Client()  # mutating_allowed default False
    with pytest.raises(MarketDataMutationNotAllowedError):
        client._ensure_mutation_allowed()


async def test_default_client_refuses_mutation_async() -> None:
    client = aio.AsyncClient()  # mutating_allowed default False
    with pytest.raises(MarketDataMutationNotAllowedError):
        client._ensure_mutation_allowed()


# ----------------------------------------------------------------------
# (b) gate abierto + host coincidente → no lanza
# ----------------------------------------------------------------------


def test_gate_open_matching_host_passes_sync() -> None:
    client = market_data_client.Client(
        mutating_allowed=True,
        base_url=f"https://{_DEVELOP_HOST}/api",
        expected_host=_DEVELOP_HOST,
    )
    client._ensure_mutation_allowed()  # gate abierto: no debe levantar


async def test_gate_open_matching_host_passes_async() -> None:
    client = aio.AsyncClient(
        mutating_allowed=True,
        base_url=f"https://{_DEVELOP_HOST}/api",
        expected_host=_DEVELOP_HOST,
    )
    client._ensure_mutation_allowed()  # gate abierto: no debe levantar


# ----------------------------------------------------------------------
# (c) gate abierto + host distinto → lanza
# ----------------------------------------------------------------------


def test_gate_open_host_mismatch_refuses_sync() -> None:
    client = market_data_client.Client(
        mutating_allowed=True,
        base_url="https://other.example/api",
        expected_host=_DEVELOP_HOST,
    )
    with pytest.raises(MarketDataMutationNotAllowedError):
        client._ensure_mutation_allowed()


async def test_gate_open_host_mismatch_refuses_async() -> None:
    client = aio.AsyncClient(
        mutating_allowed=True,
        base_url="https://other.example/api",
        expected_host=_DEVELOP_HOST,
    )
    with pytest.raises(MarketDataMutationNotAllowedError):
        client._ensure_mutation_allowed()


# ----------------------------------------------------------------------
# (d) host substring-attacker → lanza (match EXACTO, nunca substring/endswith)
# ----------------------------------------------------------------------


def test_substring_attacker_host_refused_sync() -> None:
    client = market_data_client.Client(
        mutating_allowed=True,
        base_url=f"https://{_ATTACKER_HOST}/api",
        expected_host=_DEVELOP_HOST,
    )
    with pytest.raises(MarketDataMutationNotAllowedError):
        client._ensure_mutation_allowed()


async def test_substring_attacker_host_refused_async() -> None:
    client = aio.AsyncClient(
        mutating_allowed=True,
        base_url=f"https://{_ATTACKER_HOST}/api",
        expected_host=_DEVELOP_HOST,
    )
    with pytest.raises(MarketDataMutationNotAllowedError):
        client._ensure_mutation_allowed()


# ----------------------------------------------------------------------
# (e) expected_host = None deshabilita SÓLO la pata del host (flag vigente)
# ----------------------------------------------------------------------


def test_expected_host_none_disables_host_leg_sync() -> None:
    client = market_data_client.Client(
        mutating_allowed=True,
        base_url="https://any-host.example/api",
    )
    # ``None`` en el field: la pata del host se saltea (el constructor usa el
    # sentinel None como "no cambiar", así que se setea el field directamente).
    client._state.expected_host = None
    client._ensure_mutation_allowed()  # gate abierto: no debe levantar
    # Pero el flag sigue siendo la primera pata: sin opt-in, refuse aunque el
    # host esté deshabilitado.
    client._state.mutating_allowed = False
    with pytest.raises(MarketDataMutationNotAllowedError):
        client._ensure_mutation_allowed()


async def test_expected_host_none_disables_host_leg_async() -> None:
    client = aio.AsyncClient(
        mutating_allowed=True,
        base_url="https://any-host.example/api",
    )
    client._state.expected_host = None
    client._ensure_mutation_allowed()  # gate abierto: no debe levantar
    client._state.mutating_allowed = False
    with pytest.raises(MarketDataMutationNotAllowedError):
        client._ensure_mutation_allowed()


# ----------------------------------------------------------------------
# (f) sentinel carry-forward: configure(base_url=...) no resetea el flag
# ----------------------------------------------------------------------


def test_configure_base_url_does_not_reset_flag_sync() -> None:
    market_data_client.configure(mutating_allowed=True, expected_host=_CONFTEST_HOST)
    # Un configure() posterior que OMITE mutating_allowed NO debe apagarlo.
    market_data_client.configure(base_url=f"https://{_CONFTEST_HOST}/api")
    default = market_data_client.client._get_default()
    assert default._state.mutating_allowed is True
    default._ensure_mutation_allowed()  # gate abierto: no debe levantar


async def test_configure_base_url_does_not_reset_flag_async() -> None:
    aio.configure(mutating_allowed=True, expected_host=_CONFTEST_HOST)
    aio.configure(base_url=f"https://{_CONFTEST_HOST}/api")
    default = aio._get_default()
    assert default._state.mutating_allowed is True
    default._ensure_mutation_allowed()  # gate abierto: no debe levantar


# ----------------------------------------------------------------------
# (g) herencia del gate en views (with_options comparte _state)
# ----------------------------------------------------------------------


def test_view_inherits_gate_sync() -> None:
    client = market_data_client.Client(
        mutating_allowed=True,
        base_url=f"https://{_CONFTEST_HOST}/api",
        expected_host=_CONFTEST_HOST,
    )
    view = client.with_options(max_retries=0)
    view._ensure_mutation_allowed()  # gate abierto (view hereda estado): no debe levantar


async def test_view_inherits_gate_async() -> None:
    client = aio.AsyncClient(
        mutating_allowed=True,
        base_url=f"https://{_CONFTEST_HOST}/api",
        expected_host=_CONFTEST_HOST,
    )
    view = client.with_options(max_retries=0)
    view._ensure_mutation_allowed()  # gate abierto (view hereda estado): no debe levantar
