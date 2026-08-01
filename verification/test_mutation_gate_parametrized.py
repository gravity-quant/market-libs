"""Cobertura adversarial del doble gate genérico ``mutating_allowed_for`` (D-01).

``verification.mutation_gate.mutating_allowed`` valida la base URL de **matriz**
(``matriz_client.client._base_url``) contra el sandbox remarkets. Invocado desde
otro driver su segunda pata es **vacua**: la variable de entorno sola habilitaría
escrituras contra cualquier host. ``mutating_allowed_for`` es la versión
package-agnostic — recibe las tres entradas de la decisión (nombre de la variable,
base URL resuelta y host esperado) y no importa ningún paquete cliente.

Estos tests son security-load-bearing: cada URL adversarial tiene su propio caso
parametrizado para que un fallo nombre el bypass exacto. Cubren:

- la pata del opt-in (sólo el literal ``"1"`` habilita),
- la pata del host (igualdad EXACTA de ``urlsplit(...).hostname``),
- fail-closed ante URLs malformadas (``hostname is None``),
- la decisión deliberada de comparar hostname y NO netloc (un puerto explícito
  sigue matcheando),
- que la línea de rechazo es la misma que imprime el gate de matriz y que NO
  contiene dos puntos (``main_verify.py`` clasificaría el paquete entero como
  SKIPPED, ver ``main_verify.py:42``).
"""

from __future__ import annotations

import pytest
from verification.mutation_gate import mutating_allowed_for

_HOST = "market-data-develop.bbsa.com.ar"
_GOOD_URL = f"https://{_HOST}/api"
_SKIP_LINE = "SKIPPED (mutating, guard off)\n"
_ENV = "T_MUT_PARAMETRIZED"


def _call(base_url: str) -> bool:
    return mutating_allowed_for(env_var=_ENV, base_url=base_url, expected_host=_HOST)


def test_flag_on_with_expected_host_allows_and_prints_nothing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(_ENV, "1")

    assert _call(_GOOD_URL) is True
    assert capsys.readouterr().out == ""


def test_flag_absent_blocks_and_prints_verbatim_line(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv(_ENV, raising=False)

    assert _call(_GOOD_URL) is False
    assert capsys.readouterr().out == _SKIP_LINE


@pytest.mark.parametrize("value", ["true", "0", "yes", "", "1 ", "01", "TRUE"])
def test_env_value_other_than_literal_one_is_off(
    value: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Sólo el literal ``"1"`` opta por mutar (T-27-14)."""
    monkeypatch.setenv(_ENV, value)

    assert _call(_GOOD_URL) is False
    assert capsys.readouterr().out == _SKIP_LINE


@pytest.mark.parametrize(
    "base_url",
    [
        pytest.param(f"https://{_HOST}.attacker.example/api", id="superstring-host"),
        pytest.param(f"https://evil.{_HOST}/api", id="subdomain-prefixed-host"),
        pytest.param(f"https://attacker.example/?h={_HOST}", id="host-only-in-query"),
        pytest.param(f"https://attacker.example/{_HOST}/api", id="host-only-in-path"),
        pytest.param(f"https://{_HOST}@attacker.example/api", id="userinfo-smuggled"),
        pytest.param("https://market-data-develop-bbsa.com.ar/api", id="hyphen-variant"),
        pytest.param("https://market-data.bbsa.com.ar/api", id="production-shaped"),
    ],
)
def test_adversarial_hosts_are_blocked_even_with_flag_on(
    base_url: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Igualdad EXACTA de hostname: ningún substring/superstring habilita (T-27-02)."""
    monkeypatch.setenv(_ENV, "1")

    assert _call(base_url) is False, f"host no-develop no debió permitir mutación: {base_url}"
    assert capsys.readouterr().out == _SKIP_LINE


@pytest.mark.parametrize(
    "base_url",
    [
        pytest.param("", id="empty"),
        pytest.param("not a url", id="scheme-less-prose"),
        pytest.param("://", id="bare-scheme-separator"),
        pytest.param("https://[oops/api", id="unmatched-ipv6-bracket"),
    ],
)
def test_malformed_urls_fail_closed(
    base_url: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``hostname is None`` (o un parse que revienta) → rechazo, nunca excepción."""
    monkeypatch.setenv(_ENV, "1")

    assert _call(base_url) is False
    assert capsys.readouterr().out == _SKIP_LINE


def test_explicit_port_still_matches_because_hostname_not_netloc(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Decisión deliberada: se compara ``hostname``, no ``netloc``.

    ``market-data-develop.bbsa.com.ar:8443`` es el MISMO host detrás de otro
    puerto, así que sigue habilitado. Se afirma explícitamente para que sea una
    decisión y no un accidente del parser.
    """
    monkeypatch.setenv(_ENV, "1")

    assert _call(f"https://{_HOST}:8443/api") is True
    assert capsys.readouterr().out == ""


def test_refusal_line_has_no_colon() -> None:
    """La línea de rechazo NO puede llevar dos puntos (``main_verify.py:42``).

    ``_ENV_SKIP = ^SKIPPED \\S.*:`` clasifica el paquete ENTERO como SKIPPED. El
    único emisor legítimo de esa forma es ``verification/env_gate.py``.
    """
    from verification import mutation_gate

    line = mutation_gate._SKIP_LINE
    assert ":" not in line
    assert line == "SKIPPED (mutating, guard off)"


def test_gate_does_not_import_any_client_package() -> None:
    """La pata del host es propia: el módulo genérico no toca ningún cliente."""
    import inspect

    from verification import mutation_gate

    src = inspect.getsource(mutation_gate.mutating_allowed_for)
    assert "import " not in src, "mutating_allowed_for no debe importar ningún paquete cliente"
