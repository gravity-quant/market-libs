"""Snapshot guard for the 18 ``main_matriz.py`` sweep probes (CR-05).

Phase 7 Plan 5 D-08 — Esta es la guarda que detecta drift accidental en
cualquiera de las 18 probes durante la migración a ``_envelope_probe``. Cada
probe se ejercita contra un payload canned (vía ``pytest-httpx``) y se valida
que ``ProbeResult.status == "PASS"`` con detail esperado.

Cobertura del shape pre/post-refactor:

- 13 envelope probes "limpios" (list o dict envelope) — usan
  ``_envelope_probe(envelope_key="...")``.
- 2 risk probes (``probe_get_detailed_positions``, ``probe_get_account_report``)
  — preservan ``envelope_key=None`` (D-07).
- 3 custom probes (``probe_get_segments``, ``probe_get_all_instruments``,
  ``probe_get_market_data``) — quedan custom por side-effects / market-hours
  guard (RESEARCH A4 honesty flag). Snapshot las cubre con shape PASS asserts.

Las 18 probes (3 + 13 + 2) en orden D-MATZ-29 #2-#19. ``probe_get_instruments_by_cfi_sanity``
(D-MATZ-29 #7) NO es uno de los 18 sweep probes — es un sanity sweep separado.

Idiom (per ``packages/matriz-client/tests/test_fixture_reaches_production.py``):
``httpx_mock.add_response(url=..., json=...)`` + invoke probe + assert ProbeResult.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import main_matriz
import pytest
from pytest_httpx import HTTPXMock

import matriz_client

# Canned values para inputs de las probes con side-effect.
_CANNED_SEGMENT = "DDF"
_CANNED_SYMBOL = "DLR/DIC23"
_CANNED_ACCOUNT = "TEST-ACCT-01"
_CANNED_CL_ORD_ID = "cl-ord-001"
_CANNED_PROPRIETARY = "PBCP"
_CANNED_EXEC_ID = "exec-001"


@pytest.fixture(autouse=True)
def _configure_matriz_and_canned_state() -> Iterator[None]:
    """Pre-seed matriz_client config + main_matriz globals con valores canned.

    El driver `main_matriz` usa globals (`_resolved_segment`, `_resolved_symbol`,
    `_PRIMARY_ACCOUNT`, etc.) que normalmente se resuelven en vivo durante el
    sweep. Para los snapshot tests pre-seedeamos con canned values para que las
    probes downstream (#5, #8, #10, etc.) tengan input válido.
    """
    matriz_client.configure(
        base_url="https://api.test",
        username="test-user",
        password="test-pass",
        token="snapshot-token",
        token_expires_at=9_999_999_999.0,
    )
    # Reset driver state.
    main_matriz._auth_failed = False
    main_matriz._auth_failure_reason = ""
    main_matriz._resolved_segment = _CANNED_SEGMENT
    main_matriz._resolved_symbol = _CANNED_SYMBOL
    main_matriz._PRIMARY_ACCOUNT = _CANNED_ACCOUNT
    main_matriz._SAMPLE_CL_ORD_ID = _CANNED_CL_ORD_ID
    main_matriz._SAMPLE_PROPRIETARY = _CANNED_PROPRIETARY
    main_matriz._SAMPLE_EXEC_ID = _CANNED_EXEC_ID
    main_matriz._fid_counter = 0
    yield
    # Reset driver state post-test.
    main_matriz._auth_failed = False
    main_matriz._resolved_symbol = None
    main_matriz._resolved_segment = None
    matriz_client.configure(
        base_url="https://api.test",
        username="",
        password="",
    )


# Mapeo de canned URL → canned payload + expected (status, detail_substring).
# Format: (probe_name, mock_url, mock_response_json, expected_status, detail_substring)
_PROBE_FIXTURES: list[tuple[str, str, dict[str, Any], str, str]] = [
    # 1. Custom side-effect probe (sets _resolved_segment)
    (
        "probe_get_segments",
        "https://api.test/rest/segment/all",
        {"status": "OK", "segments": [{"marketSegmentId": "DDF", "marketId": "ROFX"}]},
        "PASS",
        "1 segments",
    ),
    # 2. Custom side-effect probe (sets _resolved_symbol)
    (
        "probe_get_all_instruments",
        "https://api.test/rest/instruments/all",
        {
            "status": "OK",
            "instruments": [
                {"instrumentId": {"marketId": "ROFX", "symbol": "DLR/DIC23"}, "cficode": "FXXXSX"}
            ],
        },
        "PASS",
        "1 instruments",
    ),
    # 3. Migrated to _envelope_probe (envelope_key="instruments")
    (
        "probe_get_instruments_details",
        "https://api.test/rest/instruments/details",
        {"status": "OK", "instruments": [{"instrumentId": {"symbol": "X"}}]},
        "PASS",
        "1 instrument details",
    ),
    # 4. Migrated (envelope_key="instrument"; depends on _resolved_symbol)
    (
        "probe_get_instrument_detail",
        f"https://api.test/rest/instruments/detail?symbol={_CANNED_SYMBOL}&marketId=ROFX",
        {"status": "OK", "instrument": {"instrumentId": {"symbol": _CANNED_SYMBOL}}},
        "PASS",
        f"symbol={_CANNED_SYMBOL}",
    ),
    # 5. Migrated
    (
        "probe_get_instruments_by_cfi_ESXXXX",
        "https://api.test/rest/instruments/byCFICode?CFICode=ESXXXX",
        {"status": "OK", "instruments": [{"instrumentId": {"symbol": "Y"}}]},
        "PASS",
        "1 ESXXXX instruments",
    ),
    # 6. Migrated (envelope_key="instruments"; depends on _resolved_segment)
    (
        "probe_get_instruments_by_segment",
        f"https://api.test/rest/instruments/bySegment?MarketSegmentID={_CANNED_SEGMENT}&MarketID=ROFX",
        {"status": "OK", "instruments": [{"instrumentId": {"symbol": "Z"}}]},
        "PASS",
        f"segment={_CANNED_SEGMENT}",
    ),
    # 7. Custom (market-hours guard) — uses _resolved_symbol
    (
        "probe_get_market_data",
        f"https://api.test/rest/marketdata/get?marketId=ROFX&symbol={_CANNED_SYMBOL}&entries=BI%2COF%2CLA%2COP%2CCL%2CSE%2COI",
        {"status": "OK", "marketData": {"LA": {}}},
        "PASS",
        f"symbol={_CANNED_SYMBOL}",
    ),
    # 8. Migrated trades (envelope_key="trades")
    (
        "probe_get_trades",
        # date_from/date_to dependen del día — pytest-httpx por defecto matchea por URL
        # pero podemos usar un wildcard URL aquí con assert_all_responses_were_requested=False;
        # más simple usar match_url=path only — pero pytest-httpx requiere URL exacta.
        # Solución: no settear url, sino method/path en `add_response`.
        "https://api.test/rest/data/getTrades",
        {"status": "OK", "trades": [{"symbol": _CANNED_SYMBOL, "price": 100.0}]},
        "PASS",
        "1 trades",
    ),
    # 9. Migrated orders
    (
        "probe_get_active_orders",
        f"https://api.test/rest/order/actives?accountId={_CANNED_ACCOUNT}",
        {"status": "OK", "orders": [{"orderId": "o1"}]},
        "PASS",
        "1 active orders",
    ),
    # 10. Migrated
    (
        "probe_get_filled_orders",
        f"https://api.test/rest/order/filleds?accountId={_CANNED_ACCOUNT}",
        {"status": "OK", "orders": [{"orderId": "o2"}, {"orderId": "o3"}]},
        "PASS",
        "2 filled orders",
    ),
    # 11. Migrated
    (
        "probe_get_all_orders",
        f"https://api.test/rest/order/all?accountId={_CANNED_ACCOUNT}",
        {"status": "OK", "orders": []},
        "PASS",
        "0 total orders",
    ),
    # 12. Migrated (envelope_key="order", dict envelope)
    (
        "probe_get_order_status",
        f"https://api.test/rest/order/id?clOrdId={_CANNED_CL_ORD_ID}&proprietary={_CANNED_PROPRIETARY}",
        {"status": "OK", "order": {"orderId": "o9", "clOrdId": _CANNED_CL_ORD_ID}},
        "PASS",
        f"clOrdId={_CANNED_CL_ORD_ID}",
    ),
    # 13. Migrated
    (
        "probe_get_order_history",
        f"https://api.test/rest/order/allById?clOrdId={_CANNED_CL_ORD_ID}&proprietary={_CANNED_PROPRIETARY}",
        {"status": "OK", "orders": [{"orderId": "h1"}]},
        "PASS",
        "1 history rows",
    ),
    # 14. Migrated
    (
        "probe_get_order_by_exec_id",
        f"https://api.test/rest/order/byExecId?execId={_CANNED_EXEC_ID}",
        {"status": "OK", "order": {"orderId": "ox", "execId": _CANNED_EXEC_ID}},
        "PASS",
        f"execId={_CANNED_EXEC_ID}",
    ),
    # 15. Migrated (envelope_key="positions"; auth_basic for Risk)
    (
        "probe_get_positions",
        f"https://api.test/rest/risk/position/getPositions/{_CANNED_ACCOUNT}",
        {"status": "OK", "positions": [{"symbol": "S1"}]},
        "PASS",
        "1 positions",
    ),
    # 16. Risk probe — envelope_key=None (D-07) — auth_basic
    (
        "probe_get_detailed_positions",
        f"https://api.test/rest/risk/detailedPosition/{_CANNED_ACCOUNT}",
        {"account": _CANNED_ACCOUNT, "totalDailyDiffPlain": 0.0, "totalMarketValue": 1.0},
        "PASS",
        "account received",
    ),
    # 17. Risk probe — envelope_key=None (D-07) — auth_basic
    (
        "probe_get_account_report",
        f"https://api.test/rest/risk/accountReport/{_CANNED_ACCOUNT}",
        {"accountName": _CANNED_ACCOUNT, "marketMember": "BCBA"},
        "PASS",
        "accountName received",
    ),
]


@pytest.mark.parametrize(
    ("probe_name", "url", "response_json", "expected_status", "expected_detail_substring"),
    _PROBE_FIXTURES,
)
def test_matriz_probe_envelope_shape_preserved(
    httpx_mock: HTTPXMock,
    probe_name: str,
    url: str,
    response_json: dict[str, Any],
    expected_status: str,
    expected_detail_substring: str,
) -> None:
    """D-08 snapshot guard: each of the 17 sweep probes preserves
    ``ProbeResult`` shape pre/post the ``_envelope_probe`` refactor.

    Note: 17 in `_PROBE_FIXTURES` (the 18 sweep probes minus
    ``probe_get_instruments_by_cfi_sanity`` which is a CFI loop sanity probe,
    not an envelope probe per D-MATZ-29 #7 split).
    """
    if probe_name == "probe_get_trades":
        # Trades URL has dynamic dateFrom/dateTo (today-7d / today); match by method+path.
        httpx_mock.add_response(method="GET", json=response_json)
    else:
        httpx_mock.add_response(url=url, json=response_json)

    probe_fn = getattr(main_matriz, probe_name)
    result, _payload = probe_fn()

    assert result.status == expected_status, (
        f"{probe_name}: expected status {expected_status!r}, got {result.status!r} "
        f"(detail={result.detail!r})"
    )
    assert expected_detail_substring in result.detail, (
        f"{probe_name}: expected detail to contain {expected_detail_substring!r}, "
        f"got {result.detail!r}"
    )


def test_matriz_sweep_snapshot_count_matches_18_minus_cfi_sanity() -> None:
    """Sanity: the snapshot covers 17 = 18 sweep probes minus `cfi_sanity`."""
    assert len(_PROBE_FIXTURES) == 17, (
        f"Expected 17 fixtures (18 sweep probes minus cfi_sanity which is the loop "
        f"sweep — D-MATZ-29 #7); got {len(_PROBE_FIXTURES)}"
    )


def test_matriz_envelope_probe_helper_exists() -> None:
    """A8 honesty flag — the helper must exist in main_matriz (CR-05 close)."""
    assert callable(main_matriz._envelope_probe), "_envelope_probe helper missing"


def test_matriz_risk_probes_use_envelope_key_none() -> None:
    """D-07: the 2 risk probes (`probe_get_detailed_positions`,
    `probe_get_account_report`) MUST call ``_envelope_probe(envelope_key=None)``.
    """
    src = (main_matriz.__file__ or "").replace(".pyc", ".py")
    if not src.endswith(".py"):
        pytest.skip("Cannot read main_matriz source file")
    with open(src) as f:
        text = f.read()
    # Both risk probes must appear with envelope_key=None.
    for probe in ("probe_get_detailed_positions", "probe_get_account_report"):
        # Look for the probe body referencing envelope_key=None.
        idx = text.find(f"def {probe}(")
        assert idx >= 0, f"{probe} not found in main_matriz.py"
        # Body up to next def.
        rest = text[idx:]
        next_def = rest.find("\ndef ", 10)
        body = rest[: next_def if next_def > 0 else len(rest)]
        assert "envelope_key=None" in body, (
            f"{probe} body must include `envelope_key=None` (D-07); body={body[:300]}"
        )
