"""Guard test: monkeypatched sentinel token reaches the wire-level Authorization header.

This file is the Pitfall #1 safety net for ``iol-client``: it proves that a sentinel
value written to the legacy module-level ``_token`` state actually ends up in the
``Authorization: Bearer <sentinel>`` header of an outgoing httpx request. Without this
test, a ``monkeypatch.setattr(... raising=False)`` after a Client-class refactor could
silently land on a dead attribute and every authed test in the package would still
mock-pass while authenticating with ``None``.

Phase 06 Plan 02 LEGACY pattern: this file uses ``monkeypatch.setattr(pkg.client,
"_token", sentinel, raising=False)`` because it must run green against PRE-refactor
code where ``configure()`` does NOT yet accept ``token=``. Plan 03 (iol) will migrate
this file in-place to ``iol_client.configure(token=...)`` as part of the per-package
refactor commit.

See: .planning/phases/06-compat-safety-net-client-class-skeleton/06-RESEARCH.md Pitfall #1.
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

import iol_client


def test_iol_sync_sentinel_token_reaches_authorization_header(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SYNC: sentinel monkeypatched onto ``_token`` reaches the Authorization header."""
    monkeypatch.setattr(iol_client.client, "_token", "SYNC-sentinel-iol", raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 9_999_999_999.0, raising=False)

    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    iol_client.get_instruments("argentina")

    [req] = httpx_mock.get_requests()
    assert req.headers["Authorization"] == "Bearer SYNC-sentinel-iol"
