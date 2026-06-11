"""Skeleton tests for the ambito_financiero_client Client class (sync).

Plan 06-03 — REFAC-02 (ambito). Exercises the per-instance state model
(`_ClientState`), the lifecycle protocol (`__enter__`/`__exit__`/`close()`),
the PEP 562 read-only `__getattr__` shim (D-02 ambito row: only `_client`
forwarded), the redacted `__repr__`, the pickle/deepcopy bans (D-23) and the
`configure()` carry-forward semantics (RESEARCH.md Open Q #5).

AsyncClient mirror tests live in this same file but are appended in Task 2
of the same plan once `AsyncClient` and the aio.py shim land.
"""

from __future__ import annotations

import copy
import pickle

import pytest

import ambito_financiero_client
from ambito_financiero_client import Client
from ambito_financiero_client import client as ambito_client_mod

# --- Sync Client lifecycle ---------------------------------------------------


def test_client_context_manager_calls_close() -> None:
    """`with Client() as c: pass` closes the underlying httpx.Client on exit."""
    c = Client()
    with c:
        # Force the http client to materialize so close() has something to do.
        c._ensure_http_client()
        assert c._state.http_client is not None
    assert c._state.http_client is None


def test_close_is_idempotent() -> None:
    """Calling `close()` twice in a row must not raise (T-06-04 mitigation)."""
    c = Client()
    c.close()
    c.close()


def test_repr_contains_no_secrets_redacted() -> None:
    """`__repr__` shows `base_url` literally + the boolean `client_open` flag.

    Ambito has no credentials/tokens; the redaction reduces to the base_url
    plus the client_open boolean (matches the threat model T-06-02 entry).
    """
    c = Client(base_url="https://x")
    rep = repr(c)
    assert "https://x" in rep
    assert "client_open=False" in rep


def test_pickle_raises() -> None:
    """`pickle.dumps(Client())` raises `TypeError` (D-23)."""
    with pytest.raises(TypeError, match="not picklable"):
        pickle.dumps(Client())


def test_deepcopy_raises() -> None:
    """`copy.deepcopy(Client())` raises `TypeError` (D-23)."""
    with pytest.raises(TypeError, match="not deepcopy-safe"):
        copy.deepcopy(Client())


def test_configure_carry_forward() -> None:
    """RESEARCH.md Open Q #5 — `configure()` preserves prior fields when kwarg=None."""
    ambito_financiero_client.configure(base_url="https://a")
    assert ambito_client_mod._get_default()._state.base_url == "https://a"
    ambito_financiero_client.configure(user_agent="UA1")
    # base_url carried forward, user_agent updated.
    assert ambito_client_mod._get_default()._state.base_url == "https://a"
    assert ambito_client_mod._get_default()._state.user_agent == "UA1"


def test_explicit_client_unaffected_by_top_level_configure() -> None:
    """RESEARCH.md Pitfall #2 + CONTEXT.md D-14 — explicit Client() is isolated."""
    c = Client(base_url="https://explicit")
    ambito_financiero_client.configure(base_url="https://other")
    assert c._state.base_url == "https://explicit"


def test_pep_562_shim_forwards_http_client() -> None:
    """`client._client` (PEP 562 shim) resolves to the default Client's http_client."""
    # Force the default Client's http_client to materialize.
    default = ambito_client_mod._get_default()
    default._ensure_http_client()
    assert ambito_client_mod._client is default._state.http_client


def test_pep_562_shim_raises_for_unknown() -> None:
    """T-06-01 mitigation — only `_client` is forwarded; other reads raise."""
    with pytest.raises(AttributeError):
        ambito_client_mod._user  # noqa: B018
