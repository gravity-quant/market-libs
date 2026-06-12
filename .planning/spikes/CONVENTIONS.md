# Spike Conventions

Patterns and stack choices established across spike sessions in this project. New spikes follow these unless the question requires otherwise.

## Stack

- **Language**: Python 3.12+ (matches project requirement). No transpilation, no virtualenv overhead inside spikes — runs with the system python or project `.venv`.
- **Stdlib first**: prefer stdlib (`threading`, `asyncio`, `dataclasses`, `time`) over external libraries for spike code. The TokenStore spikes deliberately excluded `aiologic` to keep dependencies minimal — same expectation for future spikes unless the question is specifically about a library's behavior.
- **Test framework for spikes**: each spike runs its own `test_*.py` file via plain `python3 test_store.py`. No pytest in spike code (intentionally — spike tests should be readable top-to-bottom without fixture/marker overhead).

## Structure

Per-spike directory layout:
```
.planning/spikes/NNN-descriptive-name/
├── README.md          # frontmatter + Given/When/Then + Investigation Trail + Results
├── store.py           # the prototype implementation (or whatever artifact name fits)
├── test_store.py      # primary test suite — runs all standard scenarios
└── test_*.py          # follow-up tests for surprising findings (per Investigation Trail)
```

Comparison spikes share the number with letter suffix: `001a-...`, `001b-...`, `001c-...`. Integration spikes that depend on a winner use the next major number: `002-...`.

## Patterns

### Observability inside spikes

Each test file maintains a `LOG` list protected by `_LOG_LOCK: threading.Lock` with rows shaped:
```python
{
    "ts": datetime.now(timezone.utc).isoformat(),
    "thread": threading.current_thread().name,
    "category": "refresh" | "sync_worker" | "async_runner" | ...,
    "msg": "...",
}
```
This is not exposed in stdout but is available for post-hoc introspection. Use `log(category, msg, **extra)` to record events; use `reset_log()` between tests for cleanliness.

### Measuring "is the event loop blocked"

The naive metric — gap between successive `asyncio.sleep(0)` ticks in a monitor coroutine — conflates "loop is busy" with "loop is idle waiting on I/O". The correct measurement is:
1. Start an independent background workload (e.g., 5 tasks ticking a counter every 1ms via `await asyncio.sleep(0.001)`).
2. Trigger the operation under test.
3. Verify the background workload made expected progress during the operation.

If the background workload stalled, the loop was blocked. If it progressed, the loop was free. See `001c/test_loop_freedom.py` for the canonical implementation.

### 3-way (or N-way) integration test pattern

When validating cross-context atomicity, the test must use:
- A `threading.Barrier(N)` to release N callers simultaneously
- N separate threads, each running their context's natural API (sync `with lock:`, async `asyncio.run(...)`, daemon `threading.Thread(daemon=True)`)
- A single shared subject (the store/lock/etc.)
- An assertion that all N contexts received the SAME observable state (token, value, etc.)
- An assertion that the count of mutating operations matches expectation (typically 1)

See `001c/test_store.py::test_3way_integration` for the canonical implementation.

### Refresh function in token-store-like spikes

The `refresh_fn` is **always sync** (`Callable[[int], str]`), even for stores that expose async APIs. Reasons:
- Real auth refresh functions are network calls — wrapping them async-side requires either `httpx.AsyncClient` (which adds complexity) or `asyncio.to_thread`.
- The store's `get_async()` wraps the sync refresh in `asyncio.to_thread` itself, decoupling caller concerns from refresh implementation.
- This matches what the production code will look like in matriz-client (the refresh hits `httpx.Client` which is sync).

## Tools & Libraries

- **`asyncio.to_thread`** (Python 3.9+): the canonical primitive for running blocking sync code from an async context without blocking the loop. Always available in stdlib, no version compatibility issues for Python 3.12 target.
- **`threading.Barrier(N)`**: the canonical primitive for releasing N callers simultaneously in tests. Avoid hand-rolled `time.sleep + race` patterns.
- **`concurrent.futures.ThreadPoolExecutor`**: for spawning N sync callers concurrently. Use `max_workers=N` to ensure no serialization at the executor level.

## To Avoid

- **`asyncio.Lock` shared across event loops**: confirmed broken (Spike 001b). Never share an `asyncio.Lock` instance between two loops. Either use `threading.Lock` for cross-loop atomicity, or create the `asyncio.Lock` lazily per-loop (see Spike 001c).
- **Lambda hacks for thread targets** that abuse `or` short-circuit to chain function calls: produces deadlocks when intermediate calls return truthy values (Spike 002 iteration 1). Use a named function instead.
- **`time.sleep` inside an `async def`**: blocks the event loop. Use `await asyncio.sleep(...)` if you're in async context.
- **Importing from `packages/*/src/`** in spike code: spikes must be self-contained. They explore patterns, not integrate with production code. (Production integration happens in the implementing phase plan.)

## Verdict Standard

A spike marked **VALIDATED** must have:
- Multiple distinct test scenarios (not just one happy path)
- At least one edge case explored (concurrency, timing, error path, etc.)
- An "Investigation Trail" section in the README documenting iterations (with at least one surprise or refinement noted)
- Concrete measurements (latency numbers, event counts, etc.) — not just "it works"

A spike marked **INVALIDATED** must explain WHY (specific failure mode, with reproducible steps and a quote from the actual error).

A spike marked **PARTIAL** is for "works under condition X but not Y" — must document the boundary.
