"""The websocket daemon thread receives the decode mode explicitly (Plan 29-08, D-04).

``ws_client.py`` runs its event loop in a background ``threading.Thread``, and
its frame path never passes through ``Client._request``. Those two facts
together make it the one decode path in the package that the phase's
``ContextVar`` carrier cannot reach on its own:

- a plain thread starts with an **empty execution context**, so every
  ``STRICT_DECODE.get()`` there returns the ``False`` default no matter what
  the spawning thread bound;
- ``_request`` — the only place the REST surface binds the mode — is never on
  the stack when a frame is parsed.

So the mode is handed over explicitly: ``_bind_decode_mode_for_ws`` snapshots
``_ClientState.strict_decode`` on the caller's thread inside ``ws_connect``,
and ``_handle_open`` binds that snapshot inside the daemon thread. The first
test below asserts the non-inheritance fact itself, so that a future refactor
cannot quietly replace the hand-off with an assumption about inheritance; the
rest assert that the hand-off works, in both modes, and stays stable across
repeated frames and across a reconnection.

The harness runs a **real daemon thread**: ``_FakeWebSocketApp.run_forever`` is
the thread body, it invokes ``on_open`` and then ``on_message`` exactly as
``websocket-client`` does, and — critically — it lets an exception escaping the
message handler end the loop, which is how a decode error would tear the
connection down for every subscriber in production.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest

import matriz_client
from matriz_client import _decode
from matriz_client import client as sync_client
from matriz_client import ws_client as _ws
from matriz_client._token_store import TokenStore
from matriz_client.exceptions import MatrizDecodeError
from matriz_client.models import MarketDataFrame, PrimaryWsMessage, UnknownFrame

_MESSAGE = "decode divergence"

# ``timestamp`` is declared ``int | None`` and arrives as a ``str``; the two
# nested models are absent. Under matriz's policy that is one ``type``
# divergence plus two ``non_dict`` divergences in observable mode, and a raise
# at ``.timestamp`` in strict mode.
_DIVERGENT_FRAME = '{"type": "Md", "timestamp": "not-an-int"}'

# An unmodeled frame type. ``UnknownFrame`` is exempt from the walker entirely
# (29-SEMANTICS-MATRIX.md Section 3(c)), so this is the one frame shape that is
# genuinely divergence-free even in strict mode — a partially populated ``Md``
# frame is not, because every absent field of ``MarketDataSnapshot`` reports.
_EXEMPT_FRAME = '{"type": "heartbeat", "ts": 1}'


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _pristine_decode_context() -> Iterator[None]:
    """Snapshot and restore both decode carriers around every test here.

    Required by the D-03 ``.set()``-without-reset discipline: any earlier test
    that drove a real ``_request`` leaves this thread's mode and scope bound,
    and the non-inheritance assertions would then compare against a leftover
    rather than against a known baseline.
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


@pytest.fixture(autouse=True)
def _pristine_ws_state() -> Iterator[None]:
    """Reset ``ws_client``'s module-level singletons around every test.

    Includes ``_ws_strict_decode`` and the default client's ``strict_decode``
    flag: the conftest teardown reconfigures credentials but deliberately does
    not touch the decode flag, so a strict test would otherwise leak into the
    next module.
    """
    _ws._ws = None
    _ws._ws_thread = None
    _ws._on_message = None
    _ws._on_error = None
    _ws._on_close = None
    _ws._ws_strict_decode = None
    _ws._connected.clear()
    try:
        yield
    finally:
        _ws._ws = None
        _ws._ws_thread = None
        _ws._on_message = None
        _ws._on_error = None
        _ws._on_close = None
        _ws._ws_strict_decode = None
        _ws._connected.clear()
        sync_client._get_default()._state.strict_decode = False


class _FakeWebSocketApp:
    """A stand-in for ``websocket.WebSocketApp`` whose loop runs on the thread.

    ``run_forever`` is the daemon-thread body: it calls ``on_open`` and then
    pumps queued frames into ``on_message``, one at a time, serially — the same
    shape the real client has. An exception escaping ``on_message`` ends the
    loop and is recorded in :attr:`escaped`, so the tests can assert that a
    strict-mode decode error did **not** tear the connection down.
    """

    def __init__(
        self,
        url: str,
        header: dict[str, str] | None = None,
        on_open: Callable[[Any], None] | None = None,
        on_message: Callable[[Any, str], None] | None = None,
        on_error: Callable[[Any, Exception], None] | None = None,
        on_close: Callable[[Any, int | None, str | None], None] | None = None,
    ) -> None:
        self.url = url
        self.header = header
        self._on_open = on_open
        self._on_message = on_message
        self._inbox: queue.Queue[str | None] = queue.Queue()
        self._dispatched = threading.Semaphore(0)
        self.escaped: list[BaseException] = []
        self.loop_ended = threading.Event()
        self.sent: list[str] = []

    def run_forever(self) -> None:
        try:
            if self._on_open is not None:
                self._on_open(self)
            while True:
                raw = self._inbox.get()
                if raw is None:
                    return
                try:
                    if self._on_message is not None:
                        self._on_message(self, raw)
                finally:
                    self._dispatched.release()
        except BaseException as exc:
            # Deliberately broad: this stands in for ``run_forever`` dying, and
            # the tests assert this list stays EMPTY.
            self.escaped.append(exc)
        finally:
            self.loop_ended.set()

    def feed(self, raw: str, *, timeout: float = 5.0) -> None:
        """Push one frame and block until the daemon thread has dispatched it."""
        self._inbox.put(raw)
        assert self._dispatched.acquire(timeout=timeout), "frame was never dispatched"

    def close(self) -> None:
        self._inbox.put(None)

    def send(self, raw: str) -> None:
        self.sent.append(raw)


@dataclass
class _Recorder:
    """Everything the callbacks observed, plus the fake app driving the thread."""

    app: _FakeWebSocketApp
    messages: list[PrimaryWsMessage] = field(default_factory=list)
    errors: list[Exception] = field(default_factory=list)
    modes: list[bool] = field(default_factory=list)
    scopes: list[_decode.DecodeScope | None] = field(default_factory=list)
    threads: list[str] = field(default_factory=list)


@pytest.fixture
def connect(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., _Recorder]]:
    """Return a factory that runs a real ``ws_connect`` against the fake app."""
    created: list[_FakeWebSocketApp] = []

    def _factory(*, strict: bool) -> _Recorder:
        matriz_client.configure(
            base_url="https://api.test",
            username="ws-user",
            password="ws-pass",
            token="pre-warm-token",
            token_expires_at=9_999_999_999.0,
            strict_decode=strict,
        )
        default = sync_client._get_default()
        # The preseeded token means ``_ensure_token`` fast-paths and never
        # lazy-inits the store, so install one (same shape as
        # ``test_ws_client_token_integration.py``) to satisfy the helper.
        default._state.token_store = TokenStore(ttl_seconds=10, refresh_fn=lambda cid: "WS-TOKEN")

        rec: _Recorder | None = None

        def on_message(msg: PrimaryWsMessage) -> None:
            assert rec is not None
            rec.messages.append(msg)
            rec.modes.append(_decode.STRICT_DECODE.get())
            rec.scopes.append(_decode.DECODE_SCOPE.get())
            rec.threads.append(threading.current_thread().name)

        def on_error(exc: Exception) -> None:
            assert rec is not None
            rec.errors.append(exc)
            rec.modes.append(_decode.STRICT_DECODE.get())
            rec.threads.append(threading.current_thread().name)

        def _build(*args: Any, **kwargs: Any) -> _FakeWebSocketApp:
            app = _FakeWebSocketApp(*args, **kwargs)
            created.append(app)
            return app

        monkeypatch.setattr("matriz_client.ws_client.websocket.WebSocketApp", _build)
        _ws.ws_connect(on_message=on_message, on_error=on_error, timeout=5.0)
        assert _ws.ws_is_connected()
        rec = _Recorder(app=created[-1])
        return rec

    try:
        yield _factory
    finally:
        for app in created:
            app.close()


def _divergences(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.getMessage() == _MESSAGE]


# ---------------------------------------------------------------------------
# 1. The fact the whole mechanism exists for
# ---------------------------------------------------------------------------


def test_plain_thread_does_not_inherit_the_decode_mode() -> None:
    """A ``threading.Thread`` starts with an EMPTY context — no inheritance.

    This is the load-bearing assertion of the file. If it ever flips, the
    explicit hand-off in ``ws_client`` becomes redundant; while it holds,
    removing that hand-off silently runs every streamed frame in observable
    mode. Mirrors Plan 05's proof in ``market-data-client``, restated here in
    the package that actually depends on it.
    """
    _decode.STRICT_DECODE.set(True)
    _decode.open_request_scope()
    seen: dict[str, Any] = {}

    def worker() -> None:
        seen["mode"] = _decode.STRICT_DECODE.get()
        seen["scope"] = _decode.DECODE_SCOPE.get()
        # And a frame really decodes observably in there, not strictly.
        seen["frame"] = _ws._parse_frame(json.loads(_DIVERGENT_FRAME))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=5.0)

    assert seen["mode"] is False
    assert seen["scope"] is None
    assert isinstance(seen["frame"], MarketDataFrame)
    # The spawning thread's own bind survived the worker untouched.
    assert _decode.STRICT_DECODE.get() is True
    assert _decode.DECODE_SCOPE.get() is not None


def test_connect_snapshots_the_mode_before_the_thread_starts(
    connect: Callable[..., _Recorder],
) -> None:
    """``ws_connect`` reads the flag from ``_ClientState``, not from the environment."""
    connect(strict=True)
    assert _ws._ws_strict_decode is True
    assert sync_client._get_default()._state.strict_decode is True


# ---------------------------------------------------------------------------
# 2. Explicit propagation: strict mode reaches the daemon thread
# ---------------------------------------------------------------------------


def test_strict_mode_reaches_the_daemon_thread_and_routes_its_error(
    connect: Callable[..., _Recorder],
) -> None:
    """A divergent frame raises inside the thread, is routed, and the loop lives.

    Three separate facts, all of which would be false without Plan 29-08:
    the daemon thread saw strict mode at all; the resulting
    :class:`MatrizDecodeError` reached the registered error callback instead of
    escaping; and ``run_forever`` was not torn down, so the remaining
    subscribers keep their connection.
    """
    rec = connect(strict=True)

    rec.app.feed(_DIVERGENT_FRAME)

    # The error was routed, not raised out of the handler.
    assert len(rec.errors) == 1
    err = rec.errors[0]
    assert isinstance(err, MatrizDecodeError)
    assert err.field_path == ".timestamp"
    assert err.declared_type == "int"
    assert err.observed_type == "str"
    # No frame was delivered to the message callback for a frame that failed.
    assert rec.messages == []
    # It ran on the daemon thread, and it saw strict mode there.
    assert rec.threads[0] != threading.current_thread().name
    assert rec.modes == [True]

    # The connection survived: nothing escaped run_forever and the loop is live.
    assert rec.app.escaped == []
    assert not rec.app.loop_ended.is_set()
    assert _ws.ws_is_connected()

    # And it keeps working. A walker-exempt frame is still delivered to the
    # message callback, and a second divergent frame still routes a second
    # error — so the loop is genuinely pumping, not merely un-crashed.
    rec.app.feed(_EXEMPT_FRAME)
    assert len(rec.messages) == 1
    assert isinstance(rec.messages[0], UnknownFrame)
    assert rec.messages[0].raw == {"type": "heartbeat", "ts": 1}

    rec.app.feed(_DIVERGENT_FRAME)
    assert len(rec.errors) == 2
    assert rec.app.escaped == []
    assert _ws.ws_is_connected()


def test_strict_mode_error_is_logged_when_no_error_callback_is_registered(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Without an ``on_error`` the decode error still must not escape the handler."""
    _ws._on_message = lambda msg: None
    _ws._on_error = None
    _decode.STRICT_DECODE.set(True)

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        _ws._handle_message(object(), _DIVERGENT_FRAME)  # must not raise

    logged = [r for r in caplog.records if "failed strict decode" in r.getMessage()]
    assert len(logged) == 1
    assert ".timestamp" in logged[0].getMessage()


# ---------------------------------------------------------------------------
# 3. Observable mode still returns a model and reports
# ---------------------------------------------------------------------------


def test_observable_mode_returns_a_frame_and_emits_records(
    connect: Callable[..., _Recorder],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The default mode is unchanged behaviour plus reporting — never a raise."""
    rec = connect(strict=False)

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        rec.app.feed(_DIVERGENT_FRAME)

    assert rec.errors == []
    assert len(rec.messages) == 1
    frame = rec.messages[0]
    assert isinstance(frame, MarketDataFrame)
    # The pre-Phase-29 return value is byte-for-byte what it always was.
    assert frame.type == "Md"
    assert frame.instrumentId == MarketDataFrame.empty().instrumentId
    # The mode really was observable on the daemon thread.
    assert rec.modes == [False]

    paths = {r.field_path for r in _divergences(caplog)}  # type: ignore[attr-defined]
    assert ".timestamp" in paths


# ---------------------------------------------------------------------------
# 4. Repeated dispatch (the re-entrancy failure the research flagged)
# ---------------------------------------------------------------------------


def test_repeated_dispatch_is_stable_under_one_open(
    connect: Callable[..., _Recorder],
) -> None:
    """Five frames through one ``on_open``; the mechanism raises on none of them.

    This is the test that would catch research assumption A1. A stored
    ``contextvars.copy_context()`` re-entered per frame raises ``RuntimeError:
    cannot enter context ... is already entered`` on nested or overlapping
    entry — measured on CPython 3.12.13 for this plan, confirming A1. Binding
    the plain value once at open has no such failure mode, and this test pins
    that: no ``RuntimeError`` escapes, every frame decodes under the propagated
    mode, and each frame gets its **own** decode scope (lock 6 — a scope shared
    across frames would make the second identical divergence silently clean).
    """
    rec = connect(strict=False)

    for _ in range(5):
        rec.app.feed(_DIVERGENT_FRAME)

    assert len(rec.messages) == 5
    assert all(isinstance(m, MarketDataFrame) for m in rec.messages)
    # Every dispatch saw the propagated mode, not just the first.
    assert rec.modes == [False] * 5
    # Nothing escaped the loop — in particular no RuntimeError from the
    # propagation mechanism itself — and the connection is still up.
    assert rec.app.escaped == []
    assert not rec.app.loop_ended.is_set()
    assert _ws.ws_is_connected()
    # Lock 6: a fresh scope per frame, so frame N reports as loudly as frame 1.
    assert all(s is not None for s in rec.scopes)
    assert len({id(s) for s in rec.scopes}) == 5


def test_repeated_dispatch_is_stable_in_strict_mode_too(
    connect: Callable[..., _Recorder],
) -> None:
    """The same five frames in strict mode: five routed errors, one live loop."""
    rec = connect(strict=True)

    for _ in range(5):
        rec.app.feed(_DIVERGENT_FRAME)

    assert len(rec.errors) == 5
    assert all(isinstance(e, MatrizDecodeError) for e in rec.errors)
    assert all(e.field_path == ".timestamp" for e in rec.errors)  # type: ignore[attr-defined]
    assert rec.modes == [True] * 5
    assert rec.app.escaped == []
    assert not rec.app.loop_ended.is_set()


# ---------------------------------------------------------------------------
# 5. Reconnection re-reads the flag
# ---------------------------------------------------------------------------


def test_reconnecting_re_snapshots_the_mode(connect: Callable[..., _Recorder]) -> None:
    """Flipping the flag between connections takes effect on the next connect."""
    first = connect(strict=False)
    first.app.feed(_DIVERGENT_FRAME)
    assert first.modes == [False]
    assert first.errors == []

    _ws.ws_disconnect()
    # The snapshot is cleared, so nothing stale can survive into the next one.
    assert _ws._ws_strict_decode is None
    assert not _ws.ws_is_connected()

    second = connect(strict=True)
    assert _ws._ws_strict_decode is True
    second.app.feed(_DIVERGENT_FRAME)

    assert second.modes == [True]
    assert len(second.errors) == 1
    assert isinstance(second.errors[0], MatrizDecodeError)
