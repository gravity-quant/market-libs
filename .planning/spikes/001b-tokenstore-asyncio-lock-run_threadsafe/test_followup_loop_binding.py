"""Follow-up: confirm the asyncio.Lock loop-binding failure mode and characterize it.

The 3-way integration test failed with:
   RuntimeError: ... got Future <Future pending> attached to a different loop

We want to confirm:
1. The failure is purely about loop ownership of the Lock (not a race).
2. Even WITHOUT the bridge, if 2 loops touch the same asyncio.Lock, it fails.
3. The only way to make 001b work is if all callers share ONE loop.
"""

from __future__ import annotations

import asyncio
import threading

from store import TokenStoreAsyncioOnly


async def slow_refresh(call_id: int) -> str:
    await asyncio.sleep(0.01)
    return f"tok-{call_id}"


# --- Failure case 1: two threads each with their own loop --------------


def case_two_loops_break():
    """Show that even without the bridge, two distinct loops fail to share the store."""
    print("\n--- case_two_loops_break ---")
    store = TokenStoreAsyncioOnly(ttl=10.0, refresh_fn=slow_refresh)

    barrier = threading.Barrier(2)
    errors: list[tuple[str, BaseException]] = []
    tokens: list[str] = []

    def runner(name: str):
        async def main():
            snap = await store.get_async()
            tokens.append((name, snap.value))

        barrier.wait()
        try:
            asyncio.run(main())
        except BaseException as e:
            errors.append((name, e))

    t1 = threading.Thread(target=runner, args=("A",))
    t2 = threading.Thread(target=runner, args=("B",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print(f"  tokens captured: {tokens}")
    print(f"  errors raised:  {[(n, type(e).__name__, str(e)[:80]) for n, e in errors]}")
    if errors:
        print("  → confirms: asyncio.Lock cannot be safely shared across loops")
    else:
        print("  → no errors? race might have spared us; re-run multiple times")


# --- Workaround: single loop with all callers as coroutines -----------


def case_single_loop_works():
    """Show that if all callers live on the same loop, asyncio.Lock works fine."""
    print("\n--- case_single_loop_works ---")
    store = TokenStoreAsyncioOnly(ttl=10.0, refresh_fn=slow_refresh)

    async def main():
        # All "callers" are coroutines on the same loop
        results = await asyncio.gather(*(store.get_async() for _ in range(20)))
        return results

    results = asyncio.run(main())
    unique = {r.value for r in results}
    print(f"  20 coros on 1 loop → {len(unique)} unique tokens, {store.stats()['refresh_count']} refreshes")
    print("  → confirms: single-loop is fine")


# --- The fatal real-world scenario ---------------------------------------


def case_real_world_matriz_pattern():
    """Reproduce the matriz scenario:
       - Main thread might be running async (asyncio.run(main()))
       - Daemon thread (ws_client) is sync and has NO loop
       - Sync Client API methods are also sync and have NO loop

       The daemon thread + sync API need a way to call into the loop.
       asyncio.run_coroutine_threadsafe needs a *running* loop.
       If the loop is the user's main loop (via asyncio.run(main())), then
       sync callers from OUTSIDE of asyncio.run can't piggyback on it.

       Concretely: as soon as you have 2 distinct event loops anywhere
       (e.g., main script does asyncio.run(thing1()) then asyncio.run(thing2())),
       the asyncio.Lock breaks.
    """
    print("\n--- case_real_world_matriz_pattern ---")
    store = TokenStoreAsyncioOnly(ttl=10.0, refresh_fn=slow_refresh)

    # User calls asyncio.run TWICE (e.g., two separate scripts, or hot-reload, or
    # async test runner restarting the loop between tests):

    async def first_run():
        return await store.get_async()

    async def second_run():
        return await store.get_async()

    print("  call asyncio.run() the first time...")
    try:
        snap1 = asyncio.run(first_run())
        print(f"    → got {snap1.value}")
    except BaseException as e:
        print(f"    → FAILED: {type(e).__name__}: {str(e)[:80]}")

    print("  call asyncio.run() the second time on the same store...")
    try:
        snap2 = asyncio.run(second_run())
        print(f"    → got {snap2.value}")
    except BaseException as e:
        print(f"    → FAILED: {type(e).__name__}: {str(e)[:80]}")
    print("  → if even THIS fails, asyncio.Lock is unusable for long-lived Client instances")


if __name__ == "__main__":
    case_two_loops_break()
    case_single_loop_works()
    case_real_world_matriz_pattern()
