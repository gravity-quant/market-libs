---
phase: 29-decoder-observable
plan: 08
subsystem: api
tags: [decoder, observability, contextvars, websocket, threading, concurrency, resilience]

# Dependency graph
requires:
  - phase: 29-decoder-observable
    plan: 06
    provides: "matriz's `_decode.py` (walker, `POLICY`, `STRICT_DECODE`, `open_request_scope`), `MatrizDecodeError`, `_ClientState.strict_decode` and the two REST bind sites this plan is the third, non-`_request` sibling of"
  - phase: 29-decoder-observable
    plan: 05
    provides: "The executed proof that a plain `threading.Thread` reads the ContextVar DEFAULT and never the spawning thread's value — the fact this plan acts on"
  - phase: 29-decoder-observable
    plan: 01
    provides: "29-AGGREGATION-CONTRACT.md lock 6 (one decode scope per decoded unit; a process-lifetime scope is explicitly rejected)"
provides:
  - "`ws_client._bind_decode_mode_for_ws(default)` — the connect-time snapshot of `_ClientState.strict_decode`, mirroring `_acquire_token_for_ws`"
  - "`ws_client._ws_strict_decode` — the module-level snapshot, cleared by `ws_disconnect` so a reconnection re-reads the flag"
  - "`_handle_open` binding the snapshot INSIDE the daemon thread — the only decode path in the repo that never passes through `_request`"
  - "`_handle_message` opening a fresh decode scope per frame (lock 6) and catching `MatrizDecodeError` only, routing it to `_on_error` so a strict decode cannot tear down `run_forever` for every subscriber"
  - "`test_ws_decode_mode.py` — 8 tests, incl. the non-inheritance assertion and repeated dispatch under one open"
  - "The executed answer to research assumption A1, on CPython 3.12.13 AND 3.13.12"
affects: [29-09, 29-10, 33-driver-runs]

actuals:
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Cross-thread propagation of a ContextVar by explicit value snapshot + re-`set()` on the receiving thread, rather than by a stored `copy_context()` — re-entrancy-free by construction and free of the stored context's accumulating-writes problem"
    - "The snapshot is taken on the caller's thread at connect and bound on the daemon thread at open: two halves, two threads, each in the only place it can legally run"
    - "A test harness whose fake `run_forever` IS the daemon-thread body, so 'the exception tore the connection down' is an observable outcome rather than an argument"
    - "Mutation-checking a new mechanism by deleting it and recording which tests fail, instead of asserting the tests are meaningful"

key-files:
  created:
    - packages/matriz-client/tests/test_ws_decode_mode.py
  modified:
    - packages/matriz-client/src/matriz_client/ws_client.py

key-decisions:
  - "Research assumption A1 is CONFIRMED, and measured rather than reasoned: `contextvars.Context.run()` raises `RuntimeError: cannot enter context ... is already entered` on nested re-entry AND on a concurrent overlapping entry from a second thread. Repeated *sequential* runs are fine. Measured identically on CPython 3.12.13 and 3.13.12 (both CI matrix versions)."
  - "Two further measured facts, not in the research, make `copy_context()` worse than A1 alone suggests: writes performed inside a stored `Context` PERSIST across runs (so a decode scope opened there would live for the whole connection and violate lock 6), and the stored `Context` is process-global module state, so a second connection would contend with the first. The `_handle_open` re-`set()` has none of these properties."
  - "The mode is bound ONCE at open (the daemon thread's context is stable for its lifetime) but the decode SCOPE is opened per FRAME, not once at open. A frame is the WebSocket analogue of one HTTP response; a scope spanning the connection is a process-lifetime scope in all but name, and lock 6 rejects it by name. This is an addition to the plan's literal instruction — see Deviations."
  - "The `MatrizDecodeError` catch wraps `_parse_frame` ONLY, never `_on_message(frame)`. An error raised by consumer callback code keeps its previous behaviour; only the decode itself is guarded."
  - "The fallback log goes to `logging.getLogger(\"matriz_client\")`, not to a `__name__`-derived child. `RedactingFilter` is attached to the package logger and a filter only sees records logged directly to its own logger — a child logger would bypass redaction on propagation."
  - "`_ws_strict_decode` is `bool | None`, and `None` collapses to `False` at the bind. `None` distinguishes 'no connection established yet' from 'observable mode was explicitly snapshotted', which is what makes the `ws_disconnect` reset assertable."

patterns-established:
  - "When a plan flags a mechanism choice as depending on an unverified assumption, settle it with a scratch measurement FIRST and record the interpreter version — the answer changed nothing here, but the two side facts it surfaced did change the design"
  - "Mutation-check a propagation mechanism: delete the bind, run the suite, record which tests fail. A propagation test that still passes without the propagation is worthless"
  - "A 'clean' payload for a strict-mode liveness assertion is harder to find than it looks; on this surface the only genuinely divergence-free frame is the walker-EXEMPT `UnknownFrame`"

requirements-completed: [DEC-01]

coverage:
  - id: D1
    description: "The daemon thread receives the mode by explicit propagation, not by inheritance"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_plain_thread_does_not_inherit_the_decode_mode — spawning thread holds True, worker reads False and `DECODE_SCOPE` None, and a frame really decodes observably in there"
        status: pass
      - kind: test
        ref: "test_strict_mode_reaches_the_daemon_thread_and_routes_its_error — `rec.threads[0] != threading.current_thread().name` and `rec.modes == [True]`, i.e. the mode was observed ON the daemon thread"
        status: pass
      - kind: command
        ref: "Mutation check: deleting `_decode.STRICT_DECODE.set(...)` from `_handle_open` fails 3 tests (strict routing, strict repeated dispatch, reconnection)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The snapshot is read from _ClientState at connect time, before the thread is constructed (D-03, D-04)"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "`grep -n` — `_bind_decode_mode_for_ws(default)` at ws_client.py line **276**, `threading.Thread(target=_ws.run_forever, ...)` at line **294**. 276 < 294. `grep -c 'strict_decode'` = 9 (criterion asked >= 2)"
        status: pass
      - kind: test
        ref: "test_connect_snapshots_the_mode_before_the_thread_starts — `_ws._ws_strict_decode is True` and it equals `_get_default()._state.strict_decode`; no env var is read anywhere on the path"
        status: pass
    human_judgment: false
  - id: D3
    description: "The bind runs on the daemon thread, not on the caller's thread"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "The `STRICT_DECODE.set` is at ws_client.py line 117, inside `_handle_open`, which `WebSocketApp.run_forever` invokes; `ws_connect` (line 261+) contains no `.set()`"
        status: pass
      - kind: test
        ref: "The recorded `threads[0]` in the strict and observable tests is `Thread-N (run_forever)`, asserted `!=` the test's own thread name"
        status: pass
    human_judgment: false
  - id: D4
    description: "A strict-mode frame decode raises with the exact field path and does NOT kill the connection loop (T-29-43)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_strict_mode_reaches_the_daemon_thread_and_routes_its_error — `field_path == '.timestamp'`, `declared_type == 'int'`, `observed_type == 'str'`; `app.escaped == []`, `not app.loop_ended.is_set()`, `ws_is_connected()`; then a walker-exempt frame is still DELIVERED and a second divergent frame routes a SECOND error, so the loop is pumping rather than merely un-crashed"
        status: pass
      - kind: test
        ref: "test_strict_mode_error_is_logged_when_no_error_callback_is_registered — with `_on_error is None` the handler still does not raise; exactly one `failed strict decode` record carrying `.timestamp`"
        status: pass
      - kind: command
        ref: "`git diff -U0 | grep '^\\+.*except'` shows exactly one added clause: `except MatrizDecodeError as exc:`. No broad clause was added to production code"
        status: pass
    human_judgment: false
  - id: D5
    description: "The same frame in observable mode returns a model and emits records"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_observable_mode_returns_a_frame_and_emits_records — a `MarketDataFrame` with the pre-Phase-29 values (`type == 'Md'`, `instrumentId == MarketDataFrame.empty().instrumentId`), `errors == []`, `modes == [False]`, and `.timestamp` present in the emitted divergence paths"
        status: pass
    human_judgment: false
  - id: D6
    description: "The mechanism is verified against REPEATED frame dispatch, closing research assumption A1"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "Scratch measurement M1-M5 on CPython 3.12.13 and 3.13.12 — sequential `ctx.run()` OK; nested and concurrent-overlapping both raise `RuntimeError: cannot enter context ... is already entered`; writes inside a stored `Context` persist across runs; a plain thread + one `.set()` reads True on every subsequent get. A1 CONFIRMED"
        status: pass
      - kind: test
        ref: "test_repeated_dispatch_is_stable_under_one_open (5 frames, one open: 5 models, `modes == [False]*5`, `escaped == []`, loop live, and 5 DISTINCT scope objects) + test_repeated_dispatch_is_stable_in_strict_mode_too (5 routed errors, all `.timestamp`, `modes == [True]*5`, loop live)"
        status: pass
      - kind: command
        ref: "Mutation check: deleting the per-frame `open_request_scope()` fails both repeated-dispatch tests — in strict mode the shared dedupe set swallows `.timestamp` and the second raise comes from a different field, which is exactly the lock-6 false pass"
        status: pass
    human_judgment: false
  - id: D7
    description: "Disconnect + reconnect re-snapshots the mode (T-29-46)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_reconnecting_re_snapshots_the_mode — connect observable, feed, `ws_disconnect()`, assert `_ws_strict_decode is None`, reconnect strict, assert `modes == [True]` and one routed `MatrizDecodeError`"
        status: pass
      - kind: command
        ref: "`_ws_strict_decode = None` at ws_client.py line 314, inside `ws_disconnect`, added to its `global` statement"
        status: pass
    human_judgment: false
  - id: D8
    description: "The frame path emits the same six-key type-not-value record as every other path (T-29-45)"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "Structural: `_parse_frame` calls the same `Model.from_api` that Plan 06 wired to `walk_model`; no emitter, record key or `_emit` call was added by this plan (`git diff` touches no `_decode.py` line). The routed exception carries `field_path` / `declared_type` / `observed_type` / `model` and no wire value"
        status: pass
      - kind: test
        ref: "matriz's Plan 06 caplog sentinel (`test_logging.py::test_decode_sentinel_never_leaks_credential`) still green in the 409-test run"
        status: pass
    human_judgment: true
    rationale: "This plan adds no emission surface, so the inherited Plan 06 posture applies unchanged: the six all-str keys are type-not-value by construction, which a human must read `_emit` to confirm. What IS new here is the fallback `_LOGGER.warning('...: %s', exc)` — its interpolated value is `str(MatrizDecodeError)`, which is built from a field path and two type names only. A human should confirm that remains true if the exception's `__str__` is ever extended."
  - id: D9
    description: "No pre-existing test file was edited and no behaviour regressed"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "`git diff --numstat 32cc4a3 -- packages/matriz-client/tests/` reports 2 paths, both `N  0` (Plan 06's files); `test_ws_decode_mode.py` is new. `git diff --diff-filter=D --name-only 32cc4a3..HEAD` is empty"
        status: pass
      - kind: test
        ref: "`uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q --no-cov` → **1082 passed** (criterion asked for >= 872)"
        status: pass
    human_judgment: false

# Metrics
duration: 9min
completed: 2026-08-19
status: complete
---

# Phase 29 Plan 08: the websocket daemon thread Summary

**matriz's WebSocket daemon thread — the one decode path in the repository that never passes through `_request` and that inherits nothing from the thread that spawned it — now receives the decode mode by an explicit two-halves hand-off, and a strict-mode decode there routes its error instead of killing the connection for every subscriber.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-08-19T13:20:19Z
- **Completed:** 2026-08-19T13:29:19Z
- **Tasks:** 2
- **Files modified:** 1 created, 1 modified

## The measurement: research assumption A1, settled

The plan required settling A1 empirically before choosing a mechanism, because the choice depended on the answer. A scratch script measured five things; **A1 is confirmed**, and two facts it did not anticipate turned out to matter more than A1 itself.

Measured on **CPython 3.12.13** (`main, Mar 25 2026, 03:16:06, Clang 22.1.1` — the active workspace venv) and re-run identically on **CPython 3.13.12** (the other CI matrix version):

| # | Measurement | Result |
|---|-------------|--------|
| M1 | Five *sequential* `ctx.run(read)` calls on one stored `Context` | `[True, True, True, True, True]`, no error |
| M2 | A `ctx.run()` *nested* inside a run of the same `Context` | `RuntimeError('cannot enter context: <Context …> is already entered')` |
| M3 | Two threads with genuinely *overlapping* `ctx.run()` (forced with an `Event` handshake) | thread A `True`; thread B `RuntimeError('… is already entered')` |
| M4 | Do writes inside a stored `Context` persist across runs? | **Yes** — `[1, 2, 3]` across three runs; the main thread's own var stayed `0` |
| M5 | The recommended alternative: plain thread + one `.set()` | `before=False`, `after=[True, True, True]`; main thread unaffected |

**A1 was right.** A stored `copy_context()` is safe only while dispatch is strictly serial, and raises the moment it is not.

**And two facts beyond A1 make it the wrong mechanism here regardless:**

1. **M4 — a stored `Context` accumulates.** `open_request_scope()` called inside `ctx.run(...)` would write the scope *into the stored context*, where it would survive every subsequent frame. That is a connection-lifetime dedupe set: the second identical divergence decodes silently clean, which is precisely the false pass aggregation-contract lock 6 exists to eliminate. The `copy_context()` shape does not merely risk a `RuntimeError` — it structurally breaks lock 6.
2. **A stored `Context` is process-global module state.** A second `ws_connect` would either contend with the first or need its own snapshot, reintroducing the lifecycle problem the mode snapshot already solves with a plain `bool`.

The `_handle_open` re-`set()` the research recommended has none of these properties, and M5 confirms it does exactly what is needed. It is the mechanism shipped; `copy_context()` is documented in `_bind_decode_mode_for_ws`'s docstring as the fallback, citing this measurement.

## Accomplishments

- **The hand-off is two halves on two threads, each in the only place it can legally run.** `_bind_decode_mode_for_ws(default)` reads `default._state.strict_decode` into a module-level snapshot at **line 276** of `ws_connect`, on the caller's thread — 18 lines before the `threading.Thread(...)` construction at **line 294**, and immediately after `_acquire_token_for_ws`, the existing precedent for handing main-thread state to this same daemon thread. `_handle_open` binds that snapshot at **line 117**, and `run_forever` invokes it *on the daemon thread*, which is the only context where the bind can be visible to the frame path.
- **The docstring carries the fact, not just the decision.** `_bind_decode_mode_for_ws` cites D-04 in the same style `_acquire_token_for_ws` cites REFAC-04, and states the two facts it exists for: a plain thread starts with an empty execution context and inherits no `ContextVar` value, and the frame path never passes through `_request`, so there is no other route by which the mode could arrive.
- **The non-inheritance fact is now asserted in the package that depends on it.** Plan 05 proved it in `market-data-client`. `test_plain_thread_does_not_inherit_the_decode_mode` restates it here against matriz's own `_decode` and `_parse_frame`, so a future refactor that replaces the explicit hand-off with an assumption about inheritance fails in the file that owns the mechanism.
- **A strict-mode decode can no longer tear the connection down.** `_handle_message` catches `MatrizDecodeError` around the frame parse only, routes it to `_on_error` when one is registered and to the package logger otherwise, and returns. The guarded block excludes `_on_message(frame)`, so an error from consumer callback code keeps its existing behaviour, and nothing broader than the package decode error is caught.
- **The test harness makes "the connection was torn down" observable rather than arguable.** `_FakeWebSocketApp.run_forever` *is* the daemon-thread body: it calls `on_open`, then pumps queued frames into `on_message` serially, and lets an escaping exception end the loop and land in `app.escaped` with `app.loop_ended` set. Every strict-mode test asserts `escaped == []` and `not loop_ended.is_set()` — and then keeps feeding frames to prove the loop is genuinely pumping, not merely un-crashed.
- **Both halves of the mechanism were mutation-checked.** Deleting the `STRICT_DECODE.set` from `_handle_open` fails 3 tests. Deleting the per-frame `open_request_scope()` fails 2 — and the strict-mode failure is instructive: with a shared scope the dedupe set swallows `.timestamp` and the second frame's raise arrives from a different field entirely, which is exactly the lock-6 false pass in miniature.
- **1082 tests pass across the three fanned-out packages** (criterion: ≥ 872), with zero deleted lines in every pre-existing test file.

## Task Commits

1. **Task 1: explicit mode hand-off + message-handler hardening** — `4047b8b` (feat)
2. **Task 2: eight tests over a real-daemon-thread harness** — `178693b` (test)

## Files Created/Modified

- `packages/matriz-client/src/matriz_client/ws_client.py` (+121 / −5) — module docstring paragraph on the D-04 hand-off; `_LOGGER = logging.getLogger("matriz_client")`; `_decode` and `MatrizDecodeError` imports; the `_ws_strict_decode: bool | None = None` module global; `_handle_open` gains the bind, the scope open and a docstring explaining why it runs where it runs; `_handle_message` gains the per-frame scope, the narrow catch and the routing; `_bind_decode_mode_for_ws` alongside `_acquire_token_for_ws`; the call site in `ws_connect`; the reset in `ws_disconnect`. **No public symbol added** — `__all__` is unchanged and `verification/test_public_surface.py` passes against the unregenerated snapshot.
- `packages/matriz-client/tests/test_ws_decode_mode.py` (470 lines, **created**) — 8 tests, two autouse fixtures (pristine decode carriers; pristine `ws_client` singletons *and* the default client's `strict_decode` flag, which the package conftest's teardown deliberately does not touch), the `_FakeWebSocketApp` harness and a `connect(strict=...)` factory that drives a **real** `ws_connect` end to end.

## Decisions Made

- **The mode binds once, the scope opens per frame.** The plan's action says to bind the mode and open a decode scope in the open handler. The mode bind belongs there — the daemon thread's context is stable for its lifetime, and binding once is what makes the mechanism re-entrancy-free. The *scope* does not: a scope opened once at open lives for the whole connection, which for a long-lived market-data subscription means the 10,000th divergent frame reports nothing. A frame is the WebSocket analogue of one HTTP response, which is the unit lock 6 names. Both are done: `_handle_open` binds the mode and opens a scope (so the thread is never left with an unbound one), and `_handle_message` opens a fresh scope per frame. Tracked as a Rule 2 deviation below.
- **`UnknownFrame` is the only genuinely clean frame on this surface.** The strict-mode liveness assertion needed a frame that decodes without diverging. A partially populated `Md` frame is not one — every absent field of `MarketDataSnapshot` reports, so even a "good-looking" payload raises under strict mode. `UnknownFrame` is exempt from the walker entirely (matrix Section 3(c)), which makes `{"type": "heartbeat", "ts": 1}` the one payload that is divergence-free in strict mode. That it is *delivered* to the message callback while a divergent `Md` frame is *routed* to the error callback, on the same live connection, is a stronger liveness assertion than a quiet loop would have been.
- **The fallback log goes to the package logger, not a `__name__` child.** `RedactingFilter` is attached to `logging.getLogger("matriz_client")`, and a filter attached to a logger only sees records logged *directly* to it — records propagating up from a `matriz_client.ws_client` child would bypass it. The same reasoning `_decode._LOGGER` already follows, restated in a source comment.
- **`_ws_strict_decode` is `bool | None`.** `None` means "no connection established in this process yet" and collapses to `False` at the bind. The tri-state is what makes the `ws_disconnect` reset assertable (`is None`) rather than indistinguishable from an explicitly observable connection.
- **The catch wraps `_parse_frame` only.** `_on_message(frame)` sits outside the `try`. A consumer callback that raises `MatrizDecodeError` for its own reasons must not be silently swallowed by this library's error routing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] A single connection-lifetime decode scope would violate aggregation-contract lock 6**

- **Found during:** Task 1, while reading lock 6 against the plan's action text.
- **Issue:** The plan's action says to "bind the snapshot into the ContextVar and open a decode scope" in the connection-open handler. Binding the *mode* once there is correct and is what makes the mechanism re-entrancy-free. Opening the *scope* once there is not: `DecodeScope` holds the `(model, field_path, kind)` dedupe set, so one scope for the connection means the second identical divergence — and every one after it — decodes silently clean. Lock 6 rejects a process-lifetime scope by name, for exactly this reason ("it would make the second identical response decode silently clean, which is the false pass this milestone exists to eliminate"). A market-data subscription is precisely the long-lived, high-repetition case where that goes wrong.
- **Fix:** `_handle_open` still binds the mode and opens a scope (so the thread is never left with an unbound one from frame zero); `_handle_message` additionally opens a fresh scope per frame, treating a frame as the WebSocket analogue of one HTTP response.
- **Proof it matters:** with the per-frame scope removed, `test_repeated_dispatch_is_stable_under_one_open` fails on scope identity and `test_repeated_dispatch_is_stable_in_strict_mode_too` fails because the shared dedupe set swallows `.timestamp` and the second raise arrives from a different field.
- **Files modified:** `packages/matriz-client/src/matriz_client/ws_client.py`
- **Commit:** `4047b8b`

**2. [Rule 1 - Bug] Ruff flagged an unused `noqa` in the test harness**

- **Found during:** Task 2, on `uv run ruff check .`.
- **Issue:** `except BaseException as exc:  # noqa: BLE001` — `BLE001` is not in the enabled rule set, so the directive was unused (RUF100).
- **Fix:** Replaced the directive with a comment explaining why the clause is deliberately broad (it stands in for `run_forever` dying, and the tests assert the list stays empty).
- **Files modified:** `packages/matriz-client/tests/test_ws_decode_mode.py`
- **Commit:** `178693b`

### Clarifications to acceptance criteria

**1. Task 2 asked for four tests; eight were written.** The four required ones are `test_plain_thread_does_not_inherit_the_decode_mode`, `test_strict_mode_reaches_the_daemon_thread_and_routes_its_error`, `test_observable_mode_returns_a_frame_and_emits_records` and `test_repeated_dispatch_is_stable_under_one_open`. The optional fifth (reconnection) was observable through the harness and is present. Three more were added: the connect-time snapshot assertion, the no-`on_error`-registered fallback path, and repeated dispatch under *strict* mode — the last because the observable-mode repeated-dispatch test alone does not exercise the raise path across frames.

**2. The strict-mode liveness assertion uses an exempt frame, not a "clean" one.** The plan's phrasing implies a clean frame exists; on this surface it does not (see Decisions). `UnknownFrame` is used instead, and a second divergent frame is fed as well, so both the delivery path and the routing path are shown alive after the first error.

---

**Total deviations:** 2 auto-fixed (one Rule 2, one Rule 1). Two acceptance-criterion clarifications.
**Impact on plan:** None on scope — both files touched are in `files_modified`. The Rule 2 fix adds one line to `_handle_message` that the plan did not enumerate; it is the minimum needed to keep lock 6 true on the frame path.

## Issues Encountered

- The first draft's strict-mode liveness check fed a fully-shaped `Md` frame expecting it to decode cleanly. It does not: `MarketDataSnapshot` declares fourteen fields, and every absent one reports, so the "clean" frame raised at `.marketData.BI`. Resolved by switching to the walker-exempt `UnknownFrame`, which is a better assertion anyway.
- `uv run --python 3.13` (used to repeat the A1 measurement on the second CI matrix version) **tears down and recreates `.venv`** rather than using an ephemeral environment. The workspace was restored with `uv sync --all-packages --all-extras --dev --frozen --python 3.12` and the full matriz suite re-run green before committing. Worth knowing before anyone reaches for that flag mid-task again.

## Verification

- `uv run pytest packages/matriz-client/tests/test_ws_decode_mode.py -q --no-cov` — **8 passed**.
- `uv run pytest packages/matriz-client -q --no-cov` — **409 passed** (401 before this plan's tests + 8).
- `uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q --no-cov` — **1082 passed** (criterion: ≥ 872).
- `uv run mypy packages/matriz-client/src` — Success: no issues found in 17 source files.
- `uv run ruff check .` — All checks passed. `uv run ruff format --check .` — 214 files already formatted.
- `uv run lint-imports` — Contracts: 4 kept, 0 broken.
- `uv run pytest verification/test_public_surface.py -q --no-cov` — 4 passed; **no snapshot regeneration needed**, since every symbol added is private.
- `grep -c 'strict_decode' packages/matriz-client/src/matriz_client/ws_client.py` — **9** (criterion: ≥ 2).
- **Call-site ordering (recorded per the acceptance criterion):** `_bind_decode_mode_for_ws(default)` at **line 276**; `threading.Thread(target=_ws.run_forever, daemon=True)` at **line 294**. 276 < 294.
- `_decode.STRICT_DECODE.set(...)` at **line 117**, inside `_handle_open`; `ws_connect` contains no `.set()` call. `_ws_strict_decode = None` at **line 314**, inside `ws_disconnect`, with the variable added to its `global` statement.
- `git diff -U0 -- ws_client.py | grep '^\+.*except'` — exactly one added exception clause, `except MatrizDecodeError as exc:`.
- **Mutation check 1:** removing the `_handle_open` bind → 3 failed / 5 passed (`…routes_its_error`, `…strict_mode_too`, `…re_snapshots_the_mode`).
- **Mutation check 2:** removing the per-frame `open_request_scope()` → 2 failed / 6 passed (both repeated-dispatch tests). The source file was restored byte-identically afterwards (verified by comparison, not by assumption).
- **A1 measurement** — M1-M5 above, on CPython 3.12.13 and 3.13.12.
- Zero-edit gate: `git diff --numstat 32cc4a3 -- packages/matriz-client/tests/` reports 2 paths, both with **0 deleted lines**; `git diff --diff-filter=D --name-only 32cc4a3..HEAD` is empty.

## Prohibitions status

Both plan prohibitions were carried as `flagged-unverified` and are now satisfied:

- *"The daemon thread must NEVER be assumed to inherit the decode mode."* — Not assumed anywhere: the hand-off is explicit and the assumption's *negation* is asserted. `test_plain_thread_does_not_inherit_the_decode_mode` binds `True` on the spawning thread and asserts the worker reads `False`, `DECODE_SCOPE` is `None`, and a real frame decodes observably in there. The mutation check closes the loop from the other side: with the explicit bind deleted, three tests fail, so the mechanism cannot be silently removed in favour of the wrong assumption.
- *"Frame decoding must NEVER raise out of the daemon thread's message handler in observable mode."* — Satisfied, and satisfied more broadly than stated. In observable mode the walker does not raise at all (`DecodeScope.__call__` only raises when `STRICT_DECODE.get()` is true), so the observable path is safe by construction. The added guard covers the *strict* path, where a raise is expected and where an escape would be fatal for every subscriber: `MatrizDecodeError` is caught, routed and swallowed, and `app.escaped == []` / `not app.loop_ended.is_set()` are asserted in three separate tests. The guard is deliberately narrow — an unrelated exception, and any exception from `_on_message` itself, keeps its previous behaviour.

## TDD Gate Compliance

Neither task carries `tdd="true"` in the plan, and the plan's `type` is `execute`, not `tdd`. Task 1 is a mechanism whose correctness depended on a measurement that had to run first; Task 2 is test-only. In place of a RED gate, **both halves of Task 1's mechanism were mutation-checked** after Task 2 landed — the bind and the per-frame scope were each deleted in turn and the failing tests recorded (3 and 2 respectively), which establishes the same property a RED commit would have: the tests fail without the implementation.

## Known Stubs

None. Every symbol added is on a live path: `_bind_decode_mode_for_ws` runs on every `ws_connect`, the bind runs on every connection open, the per-frame scope and the decode guard run on every inbound frame, and the `ws_disconnect` reset runs on every disconnect.

## Threat Flags

None. This plan adds no network endpoint, no auth path, no file access and no schema at a trust boundary. The three boundaries it touches are the plan's own T-29-42 through T-29-46, each with a named mitigation and a test above. The one new emission — the `_LOGGER.warning` fallback when no `on_error` is registered — interpolates `str(MatrizDecodeError)`, which is composed of a field path and two type names and carries no wire value; it is logged to the redaction-filtered package logger.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **DEC-01's last uncovered decode path is closed.** Every decode in the five fanned-out packages now reaches the walker with a mode bound from `_ClientState`: the REST paths through the `_request` bind sites, and matriz's frame path through this hand-off.
- **Carried forward for Plan 09 (intactness gate):** `ws_client.py` is **not** one of the copied files and must not be swept into the hash check. It imports `_decode` but adds no line to it — `git diff` touches no `_decode.py` line in this plan, so matriz's copy is still the six-line delta Plan 06 recorded.
- **Carried forward for Plan 10 / whoever documents the public surface:** `strict_decode` now affects WebSocket frames as well as REST responses, and the mode is captured **at `ws_connect` time**. A caller who flips the flag on a live connection sees no change until the next connect. That is deliberate (the snapshot is what makes the mechanism re-entrancy-free) and it is user-visible behaviour worth one sentence in the docs.
- **Carried forward for Phase 33 (driver runs):** a strict-mode driver that opens a WebSocket subscription will see divergences arrive on the `on_error` callback, not as raised exceptions. `main_matriz.py` must register an `on_error` if it intends to treat a frame divergence as a finding — without one they are logged and the run continues.
- **Carried forward for anyone extending the message handler:** the `MatrizDecodeError` catch wraps `_parse_frame` only, and widening it would silently swallow consumer callback errors. If a second recoverable exception type is ever added, add it to the same narrow clause rather than broadening it.
- **Tooling note:** `uv run --python <other>` recreates `.venv`. Use it deliberately and re-sync afterwards.
- **No blockers.**

## Self-Check: PASSED

Created file verified present on disk: `packages/matriz-client/tests/test_ws_decode_mode.py`. Modified file verified present: `packages/matriz-client/src/matriz_client/ws_client.py`. Both task commits (`4047b8b`, `178693b`) verified present in git history.

---
*Phase: 29-decoder-observable*
*Completed: 2026-08-19*
