"""TokenStore prototype using double-checked locking: threading.Lock + per-loop asyncio.Lock.

Strategy:
- Outer level: a `threading.Lock` protects the actual token state. This is the ONE source
  of truth for atomicity across sync, async, and daemon-thread callers.
- Inner level (async-only optimization): a per-loop `asyncio.Lock` prevents thundering
  herd within a single loop. This lock is created lazily, keyed by `id(loop)`, so each
  loop gets its own. Cross-loop sharing of asyncio.Lock is AVOIDED by design.

DCL pattern in get_async:
  1. Fast path: read token under `threading.Lock` (microseconds). If valid, return.
  2. Slow path: acquire the per-loop asyncio.Lock, then re-check under threading.Lock.
     If still expired, refresh. Otherwise some other coroutine refreshed it — return cached.

This mirrors the pattern used in matriz's current `client.py`/`aio.py` for token refresh
(continuity argument for Phase 10).

The refresh function is sync (called from inside the threading.Lock). Async callers
that need the refresh to be non-blocking can wrap it in asyncio.to_thread — but for
matriz's workload (rare refreshes), the slight blocking during refresh is acceptable.
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


class TokenStoreDCL:
    """Double-checked locking TokenStore.

    State protection: threading.Lock (the single source of truth).
    Async coordination: per-loop asyncio.Lock created lazily.
    """

    def __init__(self, ttl: float, refresh_fn) -> None:
        self._state_lock = threading.Lock()
        self._ttl = ttl
        self._refresh_fn = refresh_fn  # callable[[int], str] — sync; if async refresh
                                       # is needed, wrap inside or change signature
        self._token: str | None = None
        self._refreshed_at: float = 0.0
        self._refresh_count: int = 0

        # Per-loop asyncio.Lock cache. Keyed by id(loop). Protected by state_lock for
        # the rare event that 2 coroutines on different loops both initialize the same
        # loop's lock concurrently.
        self._async_locks: dict[int, asyncio.Lock] = {}

    # --- core state access (sync, used by all paths) ---------------------

    def _read_state(self) -> tuple[str | None, float, int]:
        with self._state_lock:
            return self._token, self._refreshed_at, self._refresh_count

    def _do_refresh_if_needed(self) -> TokenSnapshot:
        """Locked refresh-or-return. Called inside state_lock to do the actual work.

        Returns the current snapshot AFTER the lock is held. Caller already
        has the lock from `with self._state_lock:`.
        """
        # Assumes caller holds state_lock!
        now = time.monotonic()
        if self._token is None or (now - self._refreshed_at) > self._ttl:
            self._refresh_count += 1
            self._token = self._refresh_fn(self._refresh_count)
            self._refreshed_at = time.monotonic()
        return TokenSnapshot(
            value=self._token,
            refreshed_at=self._refreshed_at,
            refresh_call_id=self._refresh_count,
        )

    # --- sync API ---------------------------------------------------------

    def get_sync(self) -> TokenSnapshot:
        # Single-lock path: just acquire state_lock and refresh-if-needed.
        with self._state_lock:
            return self._do_refresh_if_needed()

    # --- async API (DCL pattern) ------------------------------------------

    def _get_async_lock(self, loop: asyncio.AbstractEventLoop) -> asyncio.Lock:
        """Get or create the per-loop asyncio.Lock. Thread-safe initialization."""
        key = id(loop)
        # Fast path: lock already exists
        lock = self._async_locks.get(key)
        if lock is not None:
            return lock
        # Slow path: create under state_lock to avoid races with another coroutine
        with self._state_lock:
            lock = self._async_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._async_locks[key] = lock
        return lock

    def _refresh_under_state_lock(self) -> TokenSnapshot:
        """Helper for asyncio.to_thread — acquires state_lock and refreshes.

        Called from get_async via asyncio.to_thread so the event loop is not
        blocked during the sync refresh. The state_lock acquisition is what
        guarantees cross-loop / cross-thread atomicity.
        """
        with self._state_lock:
            return self._do_refresh_if_needed()

    async def get_async(self) -> TokenSnapshot:
        loop = asyncio.get_running_loop()
        async_lock = self._get_async_lock(loop)

        # First fast-path check: is the token already valid?
        token, refreshed_at, _ = self._read_state()
        now = time.monotonic()
        if token is not None and (now - refreshed_at) <= self._ttl:
            return TokenSnapshot(value=token, refreshed_at=refreshed_at, refresh_call_id=self._refresh_count)

        # Slow path: acquire the per-loop asyncio.Lock to prevent thundering herd
        # within this loop. Other loops can't enter this critical section either
        # because they have their OWN asyncio.Lock — but cross-loop atomicity is
        # guaranteed by state_lock inside _refresh_under_state_lock.
        async with async_lock:
            # Double-check under async lock: maybe another coroutine refreshed already
            token, refreshed_at, _ = self._read_state()
            now = time.monotonic()
            if token is not None and (now - refreshed_at) <= self._ttl:
                return TokenSnapshot(value=token, refreshed_at=refreshed_at, refresh_call_id=self._refresh_count)

            # Refresh needed. Offload the (sync) refresh to a worker thread so the
            # event loop is NOT blocked. The threading.Lock inside guarantees
            # atomicity across all callers (sync/async/daemon/cross-loop).
            return await asyncio.to_thread(self._refresh_under_state_lock)

    # --- observability ----------------------------------------------------

    def stats(self) -> dict:
        with self._state_lock:
            return {
                "token": self._token,
                "refresh_count": self._refresh_count,
                "refreshed_at": self._refreshed_at,
                "active_loops": len(self._async_locks),
            }
