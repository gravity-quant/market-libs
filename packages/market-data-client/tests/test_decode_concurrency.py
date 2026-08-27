"""The decode mode is per-context: interleaved async tasks, and plain threads.

Phase 29 Plan 05 (DEC-01), T-29-25. The decode mode travels by ``ContextVar``
rather than by parameter because the walker is reached from ~30 pure parser
functions that hold no reference to a ``Client``. That choice is only safe if
the carrier's isolation properties are the ones the design assumes, so this
module asserts them directly rather than trusting the stdlib docs:

- **Two coroutines on ONE event loop share a thread.** ``asyncio.gather`` wraps
  each coroutine in a ``Task``, and a ``Task`` COPIES the current context at
  creation. A ``.set()`` inside one task is therefore invisible to its sibling
  and invisible to the parent — which is what makes the D-03
  ``.set()``-without-reset discipline safe on the async surface, where a plain
  module global or a thread-local would leak one caller's mode into another's.
- **A plain (non-asyncio) thread starts with an EMPTY context.** It does not
  inherit the spawning thread's values; every ``ContextVar`` read there returns
  the DEFAULT. That is the fact matriz's websocket path depends on — its
  background daemon thread would silently run in observable mode no matter what
  the REST client was configured with — and it is why Plan 08 has to bind the
  mode explicitly on the websocket side instead of relying on inheritance.

market-data is the natural home for this proof: it is the only package in the
fan-out with a full ``aio.py`` mirror AND the ``_ClientState`` flag precedent.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest

from market_data_client import _decode
from market_data_client._decode import POLICY, DecodeScope, walk_model
from market_data_client.exceptions import MarketDataDecodeError
from market_data_client.models import SafeModel

_MESSAGE = "decode divergence"


@pytest.fixture(autouse=True)
def _pristine_decode_context() -> Iterator[None]:
    """Snapshot and restore both carriers around every test in this module.

    Required by the D-03 ``.set()``-without-reset discipline: any earlier test
    that drove a real ``_request`` leaves this context's mode and scope bound,
    and the parent-context assertions below would then be asserting about a
    leftover rather than about a known baseline.
    """
    mode = _decode.STRICT_DECODE.get()
    scope = _decode.DECODE_SCOPE.get()
    _decode.STRICT_DECODE.set(False)
    _decode.DECODE_SCOPE.set(None)
    try:
        yield
    finally:
        _decode.STRICT_DECODE.set(mode)
        _decode.DECODE_SCOPE.set(scope)


@dataclass(frozen=True, slots=True)
class _Row(SafeModel):
    """A minimal divergent-payload target, declared locally on purpose.

    A shipped model gaining or losing a field must not be able to turn a
    carrier regression green.
    """

    symbol: str
    size: int


# The payload diverges twice: ``symbol`` is wrong-typed and ``size`` is absent.
_DIVERGENT: dict[str, Any] = {"symbol": 7}


def _divergences(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.getMessage() == _MESSAGE]


# ---------------------------------------------------------------------------
# Interleaved async tasks (T-29-25)
# ---------------------------------------------------------------------------


async def test_interleaved_async_tasks_do_not_clobber_each_others_mode(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Two tasks, one loop, two modes — and each keeps its own.

    The two ``asyncio.Event`` handoffs force a REAL interleave rather than a
    lucky serialization: the strict task sets its mode and then suspends, the
    observable task runs while that ``set()`` is live in the sibling context,
    and the strict task only resumes after the observable task has finished its
    own decode. Both tasks assert the mode they see BOTH before and after the
    suspension point, so a leak in either direction fails the test.
    """
    strict_ready = asyncio.Event()
    observable_done = asyncio.Event()
    observed: dict[str, list[bool]] = {"strict": [], "observable": []}

    async def strict_task() -> None:
        _decode.STRICT_DECODE.set(True)
        _decode.open_request_scope()
        observed["strict"].append(_decode.STRICT_DECODE.get())
        strict_ready.set()
        # Suspend here: the sibling runs while this task's ``set()`` is live.
        await observable_done.wait()
        observed["strict"].append(_decode.STRICT_DECODE.get())
        with pytest.raises(MarketDataDecodeError) as excinfo:
            walk_model(_Row, _DIVERGENT, policy=POLICY, sink=DecodeScope())
        assert excinfo.value.field_path == ".symbol"

    async def observable_task() -> None:
        # Resume only once the sibling has already bound strict mode.
        await strict_ready.wait()
        observed["observable"].append(_decode.STRICT_DECODE.get())
        _decode.open_request_scope()
        kwargs = walk_model(_Row, _DIVERGENT, policy=POLICY, sink=DecodeScope())
        assert _Row(**kwargs) == _Row("", 0)
        observed["observable"].append(_decode.STRICT_DECODE.get())
        observable_done.set()

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        await asyncio.gather(strict_task(), observable_task())

    # Neither task ever observed the other's mode, at either checkpoint.
    assert observed["strict"] == [True, True]
    assert observed["observable"] == [False, False]

    # The observable task really decoded and really reported — the strict task's
    # raise did not suppress it, and it did not raise itself.
    paths = {r.field_path for r in _divergences(caplog)}  # type: ignore[attr-defined]
    assert {".symbol", ".size"} <= paths

    # The PARENT context is untouched by either task's ``set()``.
    assert _decode.STRICT_DECODE.get() is False
    assert _decode.DECODE_SCOPE.get() is None


async def test_each_task_gets_its_own_decode_scope() -> None:
    """Lock 6 across tasks: one task's dedupe set can never swallow another's record.

    A ``DECODE_SCOPE`` shared between sibling tasks would make the second
    concurrent response for the same endpoint decode silently clean — precisely
    the false pass this milestone exists to eliminate.
    """
    scopes: list[DecodeScope | None] = []

    async def one() -> None:
        _decode.open_request_scope()
        await asyncio.sleep(0)
        scopes.append(_decode.DECODE_SCOPE.get())

    await asyncio.gather(one(), one())

    assert len(scopes) == 2
    assert scopes[0] is not None
    assert scopes[1] is not None
    assert scopes[0] is not scopes[1]
    assert _decode.DECODE_SCOPE.get() is None


# ---------------------------------------------------------------------------
# Plain threads do NOT inherit (the fact Plan 08 acts on)
# ---------------------------------------------------------------------------


def test_plain_thread_sees_the_contextvar_default_not_the_main_thread_value() -> None:
    """A ``threading.Thread`` starts with an EMPTY context — no inheritance.

    Carried forward to Plan 08: matriz's websocket event loop runs in a
    background daemon thread, so a mode bound on the REST path in the main
    thread is NOT visible there. The websocket side must bind the mode itself;
    relying on inheritance would silently run every streamed frame in
    observable mode.
    """
    _decode.STRICT_DECODE.set(True)
    _decode.open_request_scope()
    seen: dict[str, Any] = {}

    def worker() -> None:
        seen["mode"] = _decode.STRICT_DECODE.get()
        seen["scope"] = _decode.DECODE_SCOPE.get()
        # And the decode really is observable in there, not strict.
        kwargs = walk_model(_Row, _DIVERGENT, policy=POLICY, sink=DecodeScope())
        seen["row"] = _Row(**kwargs)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert seen["mode"] is False
    assert seen["scope"] is None
    assert seen["row"] == _Row("", 0)
    # The main thread's own bind survived the worker untouched.
    assert _decode.STRICT_DECODE.get() is True
    assert _decode.DECODE_SCOPE.get() is not None


def test_thread_bind_does_not_leak_back_into_the_spawning_thread() -> None:
    """The isolation is symmetric: a worker's ``set()`` never reaches the parent."""
    _decode.STRICT_DECODE.set(False)

    def worker() -> None:
        _decode.STRICT_DECODE.set(True)
        assert _decode.STRICT_DECODE.get() is True

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert _decode.STRICT_DECODE.get() is False
