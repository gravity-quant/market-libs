"""Stub async surface for matriz-client (Phase 6 Plan 06).

This module ships ONLY the ``AsyncClient`` lifecycle scaffold (``__init__``,
``__aenter__``, ``__aexit__``, ``aclose``, ``__repr__``, ``__reduce__``,
``__deepcopy__``). The full async REST surface (``configure``, ``login``,
``get_segments``, ``new_order``, etc.) lands in Phase 10 REFAC-04 once the
shared ``TokenStore`` infrastructure is in place.

Why a stub? CONTEXT.md success criterion 3 — "Los 4 paquetes exponen Client y
AsyncClient" — needs to hold at the end of Phase 6 without crossing into
Phase 10 scope. RESEARCH.md Open Q #1 resolved the deferral by shipping
lifecycle-only here; ``isinstance`` checks and dependency injection in
downstream code now work.

Calling any REST method (e.g. ``await c.get_segments()``) on this stub raises
``AttributeError`` because no such methods exist. Switch to ``matriz_client``
top-level (sync) until Phase 10 ships the async surface.

B8 (forward-looking): when Phase 10 grows this module, the shared
``_raise_for_response`` helper MUST be imported from ``matriz_client.client``
— do NOT duplicate the error-mapping logic in this file.
"""

from __future__ import annotations

from typing import Any, Self

import httpx

from matriz_client._state import _ClientState

__all__ = ["AsyncClient"]


class AsyncClient:
    """Stub asynchronous REST client for the MATBA ROFEX Primary API.

    Phase 6 Plan 06 lifecycle-only stub. Phase 10 REFAC-04 grows the REST
    surface; until then, prefer ``matriz_client`` (sync) for actual requests
    or call sync methods through an executor.

    Args:
        base_url: Primary API base URL. Defaults to ``PRIMARY_BASE_URL`` env.
        username: ``PRIMARY_USER`` env override.
        password: ``PRIMARY_PASSWORD`` env override.
        token: Pre-existing token (will be wired into ``_state.token`` when
            Phase 10 implements the REST surface).
        token_expires_at: Unix timestamp at which the token expires.
    """

    __slots__ = ("_state",)

    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        token_expires_at: float | None = None,
    ) -> None:
        self._state = _ClientState()
        if base_url is not None:
            self._state.base_url = base_url.rstrip("/")
        if username is not None:
            self._state.username = username
        if password is not None:
            self._state.password = password
        if token is not None:
            self._state.token = token
        if token_expires_at is not None:
            self._state.token_expires_at = token_expires_at

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Idempotently close the underlying ``httpx.AsyncClient``, if any."""
        http_client = self._state.http_client
        if http_client is not None and isinstance(http_client, httpx.AsyncClient):
            await http_client.aclose()
        self._state.http_client = None

    def __repr__(self) -> str:
        return (
            f"AsyncClient(base_url={self._state.base_url!r}, "
            f"username={self._state.username!r}, "
            f"password='***', "
            f"token='***')"
        )

    def __reduce__(self) -> Any:
        raise NotImplementedError(
            "matriz_client.aio.AsyncClient is not picklable: it holds live HTTP/socket state"
        )

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        raise NotImplementedError(
            "matriz_client.aio.AsyncClient cannot be deep-copied: it holds live HTTP/socket state"
        )
