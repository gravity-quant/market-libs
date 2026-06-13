"""TokenStore — 3-way concurrent token store (Phase 10 REFAC-04).

Double-Checked Locking pattern (Spike 001c port):

- ``threading.Lock`` guards token state (cross-context atomic: sync REST,
  ``ws_client`` daemon thread, ``asyncio.to_thread`` offload all converge).
- ``asyncio.Lock`` instances are lazy per event loop (intra-loop
  thundering-herd prevention).
- Refresh runs in a worker thread via ``asyncio.to_thread`` to free the loop
  during network I/O (>5ms budget validated in spike).

``_async_locks`` lifecycle (D-05 — accept-and-document): keyed by
``id(loop)``, NOT cleared on loop death. Production (1 long-lived loop) leaks
0 bytes; multi-loop tests leak ~80B per dead loop. See
``.planning/codebase/CONCERNS.md`` for the v1.2 backlog (swap to
``weakref.WeakKeyDictionary`` if growth emerges).
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matriz_client._state import _ClientState

__all__ = ["TokenSnapshot", "TokenStore", "build_token_store"]

_MATRIZ_TOKEN_TTL_SECONDS: int = 23 * 3600  # D-04 — matriz token TTL.


@dataclass(frozen=True, slots=True)
class TokenSnapshot:
    """Immutable view of the cached token at the moment of a successful read."""

    value: str
    refreshed_at: float
    refresh_call_id: int


class TokenStore:
    """3-way concurrent token store using Double-Checked Locking."""

    def __init__(self, *, ttl_seconds: int, refresh_fn: Callable[[int], str]) -> None:
        self._ttl = ttl_seconds
        self._refresh_fn = refresh_fn
        self._token: str | None = None
        self._refreshed_at: float = 0.0
        self._refresh_count: int = 0
        self._state_lock = threading.Lock()
        # Per-event-loop asyncio.Lock cache; keyed by ``id(loop)``. NOT
        # cleared on loop death (D-05 — see module docstring).
        self._async_locks: dict[int, asyncio.Lock] = {}

    # --- State access helpers ------------------------------------------------

    def _read_state(self) -> tuple[str | None, float, int]:
        """Snapshot ``(token, refreshed_at, refresh_count)`` under ``_state_lock``."""
        with self._state_lock:
            return self._token, self._refreshed_at, self._refresh_count

    def _do_refresh_if_needed(self) -> TokenSnapshot:
        """Refresh-or-return; CALLER MUST HOLD ``_state_lock``."""
        now = time.monotonic()
        if self._token is None or (now - self._refreshed_at) > self._ttl:
            self._refresh_count += 1
            self._token = self._refresh_fn(self._refresh_count)
            self._refreshed_at = time.monotonic()
        token = self._token
        assert token is not None  # refresh_fn returned a non-empty token.
        return TokenSnapshot(
            value=token,
            refreshed_at=self._refreshed_at,
            refresh_call_id=self._refresh_count,
        )

    def _refresh_under_state_lock(self) -> TokenSnapshot:
        """Acquire ``_state_lock`` and refresh-if-needed (used by ``asyncio.to_thread``)."""
        with self._state_lock:
            return self._do_refresh_if_needed()

    # --- Sync API (sync REST, ws_client daemon, asyncio.to_thread offload) ---

    def get_sync(self) -> TokenSnapshot:
        """Return the cached token, refreshing under ``_state_lock`` if needed."""
        with self._state_lock:
            return self._do_refresh_if_needed()

    # --- Async API (async REST surface) --------------------------------------

    def _get_async_lock(self, loop: asyncio.AbstractEventLoop) -> asyncio.Lock:
        """Lazily create / fetch the per-loop ``asyncio.Lock`` (cross-loop safe)."""
        key = id(loop)
        lock = self._async_locks.get(key)
        if lock is not None:
            return lock
        # Init under the threading.Lock — safe vs. another loop's coroutine
        # initializing the same loop's lock concurrently.
        with self._state_lock:
            lock = self._async_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._async_locks[key] = lock
        return lock

    async def get_async(self) -> TokenSnapshot:
        """Return the cached token; refresh via ``asyncio.to_thread`` to free the loop."""
        loop = asyncio.get_running_loop()
        async_lock = self._get_async_lock(loop)

        # Fast path — no async lock acquired if token already fresh.
        token, refreshed_at, refresh_count = self._read_state()
        if token is not None and (time.monotonic() - refreshed_at) <= self._ttl:
            return TokenSnapshot(
                value=token, refreshed_at=refreshed_at, refresh_call_id=refresh_count
            )

        # Slow path — acquire the per-loop asyncio.Lock to suppress
        # thundering herd within THIS loop.
        async with async_lock:
            token, refreshed_at, refresh_count = self._read_state()
            if token is not None and (time.monotonic() - refreshed_at) <= self._ttl:
                return TokenSnapshot(
                    value=token, refreshed_at=refreshed_at, refresh_call_id=refresh_count
                )
            # Offload refresh to a worker thread — frees the event loop.
            return await asyncio.to_thread(self._refresh_under_state_lock)

    # --- Invalidation (Plan 10-03 401 re-auth-once consumer) -----------------

    def invalidate(self) -> None:
        """Clear the cached token so the next ``get_*`` triggers a fresh refresh.

        Plan 10-03 will use this to handle 401-after-cached-token-read by
        forcing a re-auth-once before the second request attempt.
        """
        with self._state_lock:
            self._token = None
            self._refreshed_at = 0.0


def build_token_store(state: _ClientState, *, max_retries: int) -> TokenStore:
    """Compose ``MatrizRefresh`` + ``RefreshPolicy`` into a wired ``TokenStore``.

    Knobs other than ``max_retries`` are hardcoded per D-03 (the spike-validated
    defaults). ``ttl_seconds`` is hardcoded per D-04. State is consumed for
    credentials + ``http_client``; the caller (Plan 10-03) is responsible for
    ensuring ``state.http_client`` is a ``httpx.Client`` before invocation.
    """
    # Defer imports to function body — avoids creating an eager
    # ``matriz_client._refresh`` import edge from ``_token_store`` for callers
    # that only need the ``TokenStore`` / ``TokenSnapshot`` symbols.
    from matriz_client._refresh import MatrizRefresh
    from matriz_client._refresh_policy import RefreshPolicy

    adapter = MatrizRefresh(
        http_client=state.http_client,  # type: ignore[arg-type]  # narrow at Plan 10-03 call site
        base_url=state.base_url,
        username=state.username,
        password=state.password,
    )
    policy = RefreshPolicy(
        max_retries=max_retries,
        base_backoff_s=1.0,
        max_backoff_s=30.0,
        jitter=0.25,
        fail_cache_s=30.0,
    )
    return TokenStore(
        ttl_seconds=_MATRIZ_TOKEN_TTL_SECONDS,  # D-04 — 1h before 24h server-side expiry.
        refresh_fn=policy.wrap(adapter),
    )
