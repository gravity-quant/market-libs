"""TokenStore prototype using only threading.Lock.

Strategy:
- Sync callers acquire `self._lock` directly via `with self._lock:`.
- Async callers offload the locked op to a worker thread via `asyncio.to_thread`.
- Daemon-thread callers (simulating ws_client) acquire `with self._lock:` directly.

The bet is that `threading.Lock` provides atomicity across all 3 contexts and that the
thread-hop overhead of `asyncio.to_thread` is acceptable for token-refresh frequency
(infrequent — ~once per 23h in matriz's case, but bursty during refresh windows).

We measure:
1. Correctness: exactly 1 refresh per expired-token window even with N concurrent callers.
2. Event-loop blocking: max ms the event loop is blocked while the lock is held.
3. Per-call overhead: median latency for cached-token reads (the hot path).
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass


@dataclass
class TokenSnapshot:
    value: str
    refreshed_at: float
    refresh_call_id: int


class TokenStoreThreadingOnly:
    """Token store using only threading.Lock + asyncio.to_thread for async callers."""

    def __init__(self, ttl: float, refresh_fn) -> None:
        self._lock = threading.Lock()
        self._ttl = ttl
        self._refresh_fn = refresh_fn  # callable[[int], str]
        self._token: str | None = None
        self._refreshed_at: float = 0.0
        self._refresh_count: int = 0  # observability: how many times refresh was called

    # --- sync API (REST sync + ws_client daemon thread share this) -------

    def get_sync(self) -> TokenSnapshot:
        now = time.monotonic()
        with self._lock:
            if self._token is None or (now - self._refreshed_at) > self._ttl:
                self._refresh_count += 1
                # NOTE: refresh_fn is called *inside* the lock. This blocks
                # whoever holds the lock for the duration of the refresh.
                self._token = self._refresh_fn(self._refresh_count)
                self._refreshed_at = time.monotonic()
            return TokenSnapshot(
                value=self._token,
                refreshed_at=self._refreshed_at,
                refresh_call_id=self._refresh_count,
            )

    # --- async API (REST async uses this) --------------------------------

    async def get_async(self) -> TokenSnapshot:
        # Offload the entire locked operation to the thread pool. The event loop
        # is freed during the await — other coroutines can run.
        return await asyncio.to_thread(self.get_sync)

    # --- observability ----------------------------------------------------

    def stats(self) -> dict:
        with self._lock:
            return {
                "token": self._token,
                "refresh_count": self._refresh_count,
                "refreshed_at": self._refreshed_at,
            }
