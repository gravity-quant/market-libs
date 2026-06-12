"""TokenStore prototype using asyncio.Lock + run_coroutine_threadsafe for sync callers.

Strategy:
- Async callers use `async with self._lock:` natively — no thread hop.
- Sync callers MUST know about a running event loop. They call
  `asyncio.run_coroutine_threadsafe(self.get_async(), loop).result()`.

The bet is that pure-asyncio gives us the lowest hot-path latency for async callers
(the matriz Phase 10 deliverable will likely be heavy in async), at the cost of forcing
sync callers (matriz current sync Client + ws_client daemon thread) to track and use
the loop.

The store itself is approach-agnostic — it just has `async def get()`. The "3-way"
question becomes how the wrapper layer (`get_sync()` helper) is built.

We measure:
1. Correctness: 1 refresh per expired-token window.
2. Sync caller complexity: how heavy is the wrapper?
3. Operational cost: does the loop need to be long-lived? Owned by whom?
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


class TokenStoreAsyncioOnly:
    """Token store using only asyncio.Lock. Sync callers need a running loop."""

    def __init__(self, ttl: float, refresh_fn) -> None:
        # NOTE: asyncio.Lock() is bound to the event loop that creates it. If we
        # create it lazily inside get_async() (after the loop starts), it binds
        # correctly. If we create it in __init__ from main thread before any
        # loop runs, it can still work but matiplotlib bind-when-first-used.
        self._lock: asyncio.Lock | None = None
        self._ttl = ttl
        self._refresh_fn = refresh_fn  # async callable[[int], str]
        self._token: str | None = None
        self._refreshed_at: float = 0.0
        self._refresh_count: int = 0

    async def get_async(self) -> TokenSnapshot:
        if self._lock is None:
            self._lock = asyncio.Lock()
        now = time.monotonic()
        async with self._lock:
            if self._token is None or (now - self._refreshed_at) > self._ttl:
                self._refresh_count += 1
                # Refresh fn is awaited *inside* the lock. Other coroutines
                # cannot acquire the lock until refresh completes, but they
                # CAN run other unrelated code on the loop.
                self._token = await self._refresh_fn(self._refresh_count)
                self._refreshed_at = time.monotonic()
            return TokenSnapshot(
                value=self._token,
                refreshed_at=self._refreshed_at,
                refresh_call_id=self._refresh_count,
            )

    def stats(self) -> dict:
        return {
            "token": self._token,
            "refresh_count": self._refresh_count,
            "refreshed_at": self._refreshed_at,
        }


class LoopAwareSyncBridge:
    """Sync wrapper that exposes get_sync() backed by an asyncio loop in a background thread.

    This is the "wrapper that makes 001b workable for sync callers". It owns
    a thread + a loop, and routes sync get_sync() calls through
    `asyncio.run_coroutine_threadsafe(self._store.get_async(), self._loop).result()`.

    The cost: the wrapper must be started + stopped, the loop thread is long-lived,
    and sync callers must hold a reference to the bridge (not just the store).
    """

    def __init__(self, store: TokenStoreAsyncioOnly) -> None:
        self._store = store
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    def start(self) -> None:
        """Spin up a dedicated thread running a fresh event loop."""

        def _runner():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._ready.set()
            try:
                self._loop.run_forever()
            finally:
                self._loop.close()

        self._thread = threading.Thread(target=_runner, daemon=True, name="TokenStoreLoopThread")
        self._thread.start()
        self._ready.wait(timeout=5.0)
        if self._loop is None:
            raise RuntimeError("loop failed to start within 5s")

    def stop(self) -> None:
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5.0)

    def get_sync(self) -> TokenSnapshot:
        if self._loop is None:
            raise RuntimeError("bridge not started; call start() first")
        # Submit the coroutine to the loop's thread; block this thread until done.
        fut = asyncio.run_coroutine_threadsafe(self._store.get_async(), self._loop)
        return fut.result(timeout=30.0)
