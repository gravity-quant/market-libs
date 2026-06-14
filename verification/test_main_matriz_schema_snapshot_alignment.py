"""CR-01 -- main_matriz.py ``probe_schema_snapshot`` sample_params vs path alignment.

Pre-Phase-11, ``probe_schema_snapshot`` documenta sample_params con literales
``<PRIMARY_ACCOUNT>``, ``<MATRIZ_SAMPLE_CL_ORD_ID>`` etc, mientras que la columna
``endpoint`` (poblada desde ``_ENDPOINT_TEMPLATES``) usa el estilo ``{account_id}``.
Esa divergencia genera un envelope inconsistente: el lector no puede
correlacionar facilmente el placeholder en el path con el valor en sample_params.

CR-01 fix: alinear sample_params al estilo ``{name}`` que ya usan los path
templates. El envelope nunca contiene valores live (placeholder-everywhere).
"""

from __future__ import annotations

import re
from pathlib import Path

import main_matriz
import pytest

import matriz_client
from verification import findings as findings_module


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Aisla findings dir + reset state."""
    monkeypatch.setattr(findings_module, "_FINDINGS_DIR", tmp_path)
    matriz_client.configure(base_url="https://api.test", username="u", password="p")
    main_matriz._auth_failed = False
    main_matriz._resolved_symbol = None
    main_matriz._resolved_segment = None
    main_matriz._fid_counter = 0


def _extract_sample_params() -> dict[str, dict[str, object]]:
    """Llamar a probe_schema_snapshot con payloads vacios para extraer la dict
    sample_params via introspeccion del source (no via run).

    Hacemos un parse simple: leer la funcion source y extraer el dict literal.
    Alternativa mas robusta: invocar el codigo y monkey-patchear _write_or_check_schema
    para capturar los args. Vamos por la version invocada (mas robusta).
    """
    captured: dict[str, dict[str, object]] = {}

    def _spy(
        func_name: str,
        endpoint_template: str,
        sample_params: dict[str, object],
        raw_payload: object,
        base_url: str,
    ) -> tuple[str, str]:
        # ``raw_payload`` y ``base_url`` son consumidos por la firma original pero
        # no se usan aqui -- solo capturamos sample_params para introspeccion.
        del raw_payload, base_url
        captured[func_name] = {"endpoint": endpoint_template, "sample_params": sample_params}
        return ("PASS", "spy")

    main_matriz._write_or_check_schema = _spy  # type: ignore[assignment]
    # Pasar payloads non-None para que el loop entre. Usamos un dict trivial.
    payloads = {k: {"dummy": True} for k in main_matriz._SCHEMA_FILES}
    main_matriz.probe_schema_snapshot(payloads, "https://api.test")
    return captured


def test_sample_params_use_placeholder_style_not_literal_brackets() -> None:
    """Phase 11 CR-01: cero literales ``<XXX>``-style en sample_params.

    Pre-fix usaba ``"<PRIMARY_ACCOUNT>"``, ``"<MATRIZ_SAMPLE_CL_ORD_ID>"`` etc.
    Post-fix solo usa ``{name}``-style alineado con los path templates.
    """
    captured = _extract_sample_params()
    placeholder_pattern = re.compile(r"^<[A-Z_]+>$")
    violations: list[tuple[str, str, str]] = []
    for func_name, payload in captured.items():
        sample_params = payload["sample_params"]
        assert isinstance(sample_params, dict)
        for key, value in sample_params.items():
            if isinstance(value, str) and placeholder_pattern.match(value):
                violations.append((func_name, key, value))
    assert not violations, (
        f"sample_params uses pre-Phase-11 ``<NAME>`` style for "
        f"{len(violations)} entries: {violations}"
    )


def test_account_id_placeholder_consistent_across_endpoint_and_sample_params() -> None:
    """Para los 3 risk probes, ``{account_id}`` aparece en el path Y como
    valor (no key) en sample_params: simetria explicita."""
    captured = _extract_sample_params()
    for func_name in ("get_positions", "get_detailed_positions", "get_account_report"):
        entry = captured[func_name]
        endpoint = entry["endpoint"]
        sp = entry["sample_params"]
        assert isinstance(endpoint, str)
        assert isinstance(sp, dict)
        # El path template debe usar ``{account_id}``.
        assert "{account_id}" in endpoint, (
            f"{func_name}: expected '{{account_id}}' in endpoint, got {endpoint!r}"
        )
        # sample_params debe documentar el mismo placeholder.
        assert sp.get("account_id") == "{account_id}", (
            f"{func_name}: sample_params['account_id'] != '{{account_id}}'; got {sp!r}"
        )


def test_query_param_account_id_uses_placeholder_in_sample_params() -> None:
    """Para los 3 order probes con account-en-query, sample_params usa
    ``{account_id}`` (no el valor live ni ``<PRIMARY_ACCOUNT>``)."""
    captured = _extract_sample_params()
    for func_name in ("get_active_orders", "get_filled_orders", "get_all_orders"):
        sp = captured[func_name]["sample_params"]
        assert isinstance(sp, dict)
        assert sp.get("accountId") == "{account_id}", (
            f"{func_name}: sample_params['accountId'] != '{{account_id}}'; got {sp!r}"
        )
