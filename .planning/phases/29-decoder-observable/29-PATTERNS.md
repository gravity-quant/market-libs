# Phase 29: Decoder observable - Pattern Map

**Mapped:** 2026-08-18
**Files analyzed:** 28 new/modified source+test files (+5 artifacts, +2 throwaway scripts)
**Analogs found:** 26 / 28

> Note on line numbers: every excerpt below was read from the working tree at
> branch `milestone/v1.5-mutations`. Where RESEARCH.md cites a slightly different
> line range (e.g. `_state.py:100-107`), the numbers here are the **verified**
> ones.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/{higyrus,matriz,market-data,iol,ambito}-client/src/*/_decode.py` (NEW ×5) | utility (private, verbatim-copy) | transform | `higyrus_client/_params.py` (verbatim-copy private helper) + `higyrus_client/models.py:48-89` (`_coerce` body) | exact (composite) |
| `higyrus_client/models.py` (MOD) | model | transform | itself — `SafeModel.from_api:37-45` + `_coerce:48-89` | exact (self) |
| `market_data_client/models.py` (MOD) | model | transform | `higyrus_client/models.py` (near-verbatim twin, 2107 chars, 2-line delta) | exact |
| `matriz_client/models.py` (MOD) | model | transform | `matriz_client/models.py:74-116` (`_convert` + `_SafeModel`) | exact (self, divergent semantics) |
| `*/_state.py` (MOD ×5) | config | request-response | `market_data_client/_state.py:98-105` (`mutating_allowed` / `expected_host`, D-14) | exact |
| `*/_logging.py` (MOD ×5) | middleware (log filter) | event-driven | `higyrus_client/_logging.py:86-100` (canonical body ×4) + `matriz_client/_logging.py:135-157` (D-22 declared variant) | exact |
| `*/client.py` `Client._request` (MOD ×5) | controller | request-response | `market_data_client/client.py:339-396` | exact |
| `*/aio.py` `AsyncClient._request` (MOD ×5) | controller | request-response | `market_data_client/aio.py:346` (mirror of the sync method, C-3) | exact |
| `matriz_client/ws_client.py` (MOD ×1) | service | streaming / event-driven | `ws_client.py:96-99` (`_handle_message`) + `:123-140` (`_acquire_token_for_ws`) + `:148-187` (`ws_connect`) | exact (self) |
| `packages/*/tests/test_decode.py` (NEW ×5) | test | transform | `packages/market-data-client/tests/test_models.py` + `higyrus-client/tests/test_logging.py:25-40` (`_make_record`) | role-match |
| `packages/*/tests/test_logging.py` (MOD ×5) — decode caplog sentinel | test | event-driven | `verification/test_logging_no_token_leak.py:41-90` (SEC-01) — **relocated in-package**, Pitfall 10 | exact |
| `packages/market-data-client/tests/test_decode_concurrency.py` (NEW) | test | event-driven | `packages/higyrus-client/tests/test_event_hooks_thread_safety.py` | role-match |
| `packages/matriz-client/tests/test_ws_decode_mode.py` (NEW) | test | streaming | matriz `tests/` WS suites + `ws_client.py:96-99` | role-match |
| `tools/check_decode_intactness.py` (NEW) | config / CI script | batch | `.github/workflows/ci.yml:42-51` (`lint-logging` grep gate) | partial (no `tools/` dir exists yet) |
| `.github/workflows/ci.yml` (MOD) | config | batch | `ci.yml:42-51` | exact |
| `<scratch>/sizing.py` (throwaway) | utility | batch | `verification/safemodel_diff.py:94` + `verification/schema.py:27-40` | exact |
| `<scratch>/spike_timing.py` (throwaway) | utility | batch | `.planning/spikes/SPIKE-005-codegen-tool-choice` / `SPIKE-006-*` (ephemeral `uv run --with`) | role-match |
| `29-SEMANTICS-MATRIX.md`, `29-DLOCK-MSGSPEC.md`, `29-DLOCK-RESPONSE-LITERAL.md`, `29-AGGREGATION-CONTRACT.md`, `29-SIZING.md` | doc artifacts | — | `.planning/spikes/*/` write-ups | n/a (docs) |

**Wallets exemption (D-02):** `packages/wallets-client/src/wallets_client/` contains only
`__init__.py aio.py client.py exceptions.py py.typed` — **no** `_logging.py`, `_state.py`,
`_core.py`, `models.py`. Confirmed by directory listing. No analog needed; document the
exemption, do not bootstrap (Phase 31 TYP-03).

---

## Pattern Assignments

### `*/src/*/_decode.py` — NEW ×5 (utility, transform)

Two analogs compose here: `_params.py` supplies the **module shape** for a
verbatim-copied private helper; `models.py::_coerce` supplies the **algorithm**.

**Analog A — module shape:** `packages/higyrus-client/src/higyrus_client/_params.py:1-26`

```python
"""Helpers for building Higyrus API query params.

The Higyrus API has consistent conventions that differ from the ``requests``
defaults, so every endpoint wrapper funnels its kwargs through these helpers
before handing them to :func:`higyrus_client.client._request`:
...
"""

from __future__ import annotations

from datetime import date
from typing import Any

__all__ = ["drop_none", "format_bool", "format_date"]
```

Copy this shape exactly: module docstring stating purpose + who calls it, mandatory
`from __future__ import annotations` (C-6), stdlib-only imports, explicit sorted
`__all__`. Note `_params.py` has **no** cross-package import and no runtime state —
that is the property the intactness test enforces on `_decode.py`.

**Analog B — the walker algorithm to evolve:**
`packages/higyrus-client/src/higyrus_client/models.py:48-89`

```python
def _coerce(value: Any, hint: Any) -> Any:
    """Coerce ``value`` to match ``hint``, substituting safe defaults for ``None``."""
    origin = get_origin(hint)
    args = get_args(hint)

    # Optional[T] / T | None: explicit opt-in to nullable — a missing value
    # stays None instead of collapsing to a typed zero.
    if origin is Union or origin is UnionType:
        if value is None:
            return None
        non_none = [a for a in args if a is not NoneType]
        if len(non_none) == 1:
            return _coerce(value, non_none[0])
        return value

    if origin is list:
        if not isinstance(value, list):
            return []
        inner = args[0] if args else Any
        return [_coerce(item, inner) for item in value]

    if isinstance(hint, type) and issubclass(hint, SafeModel):
        return hint.from_api(value)

    if hint is str:
        return value if isinstance(value, str) else ""
    if hint is bool:
        return value if isinstance(value, bool) else False
    if hint is int:
        # bool is a subclass of int in Python — exclude it so bool payloads
        # don't collapse into "cantidad=True".
        if isinstance(value, bool):
            return 0
        return value if isinstance(value, int) else 0
    if hint is float:
        if isinstance(value, bool):
            return 0.0
        if isinstance(value, int | float):
            return float(value)
        return 0.0

    return value
```

**Branch order is load-bearing** — copy it: Union → list → SafeModel → str → bool →
int (with the `bool`-is-`int` guard) → float → bare `return value`. The bare
`return value` fall-through is where matriz's `Literal` fields land today; the walker
adds an explicit `get_origin(hint) is Literal` branch **before** it (Pitfall 12,
D-09: never enforce membership).

The exact per-branch delta is `sink(path, kind, declared, observed)` emitted
immediately before each `return <default>`, plus the `path` keyword threaded through
the recursive calls. The **return values must not change** — that is the 872-test
zero-edit gate (DT-05).

**Import set to copy** (`models.py:23-27`):

```python
from __future__ import annotations

from dataclasses import dataclass, fields
from types import NoneType, UnionType
from typing import Any, Self, Union, cast, get_args, get_origin, get_type_hints
```

`cast(Any, cls)` in `fields(cast(Any, cls))` (`models.py:43`) is the existing
mypy-strict discipline for `get_type_hints`-driven code — reuse it, do not invent a
`# type: ignore`.

**Extra-key detection is NOT expressible in `_coerce`** — verified:

```python
# packages/higyrus-client/src/higyrus_client/models.py:37-45
    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Build an instance from an API payload, with safe defaults."""
        data: dict[str, Any] = payload if isinstance(payload, dict) else {}
        hints = get_type_hints(cls)
        kwargs: dict[str, Any] = {}
        for field in fields(cast(Any, cls)):
            kwargs[field.name] = _coerce(data.get(field.name), hints[field.name])
        return cls(**kwargs)
```

`data.get(field.name)` never enumerates `set(data)`. The `walk_model` wrapper (the
new code) is the only place extra-key detection can live. Also note
`hints = get_type_hints(cls)` on line 41 — this is the 58.9 µs/call to wrap in
`functools.lru_cache` (RESEARCH Pitfall 2).

---

### `matriz_client/models.py` (model, transform) — the divergent policy

**Analog:** itself, `packages/matriz-client/src/matriz_client/models.py:61-116`

```python
def _strip_optional(tp: Any) -> Any:
    """Return ``T`` from ``T | None`` / ``Optional[T]``; pass through otherwise."""
    if get_origin(tp) in (Union, types.UnionType):
        args = [a for a in get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp


def _convert(tp: Any, value: Any) -> Any:
    """Coerce ``value`` to the shape declared by ``tp``, applying safe defaults."""
    inner = _strip_optional(tp)
    origin = get_origin(inner)

    if origin is list:
        items = value if isinstance(value, list) else []
        (item_tp,) = get_args(inner)
        if _is_model(item_tp):
            return [item_tp.from_api(v) for v in items]
        return list(items)

    if origin is dict:
        return value if isinstance(value, dict) else {}

    if _is_model(inner):
        return inner.from_api(value) if isinstance(value, dict) else inner.empty()

    return value
```

```python
class _SafeModel:
    """Mixin providing safe ``from_api``/``empty`` constructors for dataclasses."""

    # Declared so pyright accepts ``cls`` as a dataclass; populated by ``@dataclass``.
    __dataclass_fields__: ClassVar[dict[str, Any]]

    @classmethod
    def from_api(cls, data: Any) -> Self:
        if not isinstance(data, dict):
            return cls.empty()
        hints = get_type_hints(cls)
        return cls(**{f.name: _convert(hints[f.name], data.get(f.name)) for f in fields(cls)})

    @classmethod
    def empty(cls) -> Self:
        hints = get_type_hints(cls)
        return cls(**{f.name: _convert(hints[f.name], None) for f in fields(cls)})
```

Four differences from higyrus that the `DecodePolicy` constant must encode, all
visible above and all confirmed:

| Axis | higyrus / market-data | matriz (this file) |
|---|---|---|
| argument order | `_coerce(value, hint)` | `_convert(tp, value)` — **reversed** |
| missing scalar | typed zero (`""`/`0`/`0.0`/`False`) | `None` (falls to bare `return value`) |
| non-dict payload | `{}` then all defaults | `cls.empty()` — **early return, line 108-109** |
| nested model missing | `X.from_api(None)` | `inner.empty()` — line 90 |
| `dict` hint | no branch (falls through) | explicit `{}` branch — line 86-87 |
| slots | `@dataclass(frozen=True, slots=True)` | `@dataclass(frozen=True)`, **no slots** |
| `empty()` | absent | present (used by `_convert`) |

`fields(cls)` here is **not** wrapped in `cast(Any, ...)` — the `__dataclass_fields__:
ClassVar` declaration on line 104 does that job instead. Preserve whichever form each
package already uses; do not harmonize (C-2 / D-07).

---

### `*/_state.py` — MOD ×5 (config, request-response)

**Analog:** `packages/market-data-client/src/market_data_client/_state.py:84-107`

```python
@dataclass(slots=True)
class _ClientState:
    """Per-instance state for a market-data Client / AsyncClient.

    Defaults are computed via ``field(default_factory=...)`` so that env
    vars set AFTER module import (e.g. by ``load_dotenv()`` or test
    monkeypatching of ``os.environ``) take effect on each new instance.
    """

    base_url: str = field(default_factory=_env_base_url)
    client_id: str = field(default_factory=_env_client_id)
    client_secret: str = field(default_factory=_env_client_secret)
    audience: str = field(default_factory=_env_audience)
    auth0_token_url: str = field(default_factory=_env_auth0_token_url)
    # Gate de mutaciones (D-13/D-01/D-02). Viven SÓLO en el ``_ClientState``
    # compartido — nunca en un ``__slots__`` de instancia — así un view de
    # ``with_options`` hereda el estado del gate del parent (D-14).
    # ``mutating_allowed`` refuse-by-default: una mutación NO se dispara sin
    # opt-in explícito. ``expected_host`` arranca en el host develop; ``None``
    # deshabilita SÓLO la pata del host (la del flag sigue vigente).
    mutating_allowed: bool = False
    expected_host: str | None = _DEFAULT_EXPECTED_HOST
```

`strict_decode: bool = False` goes **in this exact block**, immediately after
`expected_host`, with a Spanish comment in the same register citing D-03/D-14.

Two hard rules readable straight off the excerpt:
1. **Plain default, no `field(default_factory=_env_...)`.** Every env-backed field
   above uses a factory; `mutating_allowed` deliberately does not. D-03 forbids an env
   var carrier — copy `mutating_allowed`, not `base_url`.
2. **Never in the `Client.__slots__`.** The whole point of the `mutating_allowed`
   comment is that a `with_options` view shares the `_ClientState` object and thus
   inherits the flag.

Also note `@dataclass(slots=True)` on `_ClientState` itself (line 84): the new field
must be declared in the class body, never `setattr`-ed at runtime.

---

### `*/_logging.py` — MOD ×5 (middleware, event-driven)

**Analog (canonical, 4 copies byte-identical):**
`packages/higyrus-client/src/higyrus_client/_logging.py:86-100`

```python
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: _redact(v) if isinstance(v, str) else v for k, v in record.args.items()
                }
            else:
                record.args = tuple(_redact(a) if isinstance(a, str) else a for a in record.args)
        # Scan record.__dict__ for sentinel substrings in extra= values.
        for key, value in list(record.__dict__.items()):
            if isinstance(value, str) and any(m in value for m in _REDACTION_MARKERS):
                record.__dict__[key] = _redact(value)
        return True
```

Gap (a) is the `isinstance(value, str)` guard on the `__dict__` scan; gap (b) is that
`_REDACTION_MARKERS` are literal anchors:

```python
# higyrus_client/_logging.py:58-65
_REDACTION_MARKERS: tuple[str, ...] = (
    "Bearer ",
    "X-Auth-Token",
    "password=",
    '"password"',
    '"token"',
    "cuit=",
)
```

and `_redact` is a chain of marker-anchored regexes (`_logging.py:68-75`):

```python
def _redact(text: str) -> str:
    """Apply higyrus redaction passes in order. Idempotent on already-redacted text."""
    redacted = _BEARER_RE.sub("Bearer ***", text)
    redacted = _X_AUTH_TOKEN_RE.sub(r"\1***", redacted)
    redacted = _PASSWORD_URLENC_RE.sub(r"\1***", redacted)
    redacted = _PASSWORD_JSON_RE.sub(r"\1***\2", redacted)
    redacted = _TOKEN_JSON_RE.sub(r"\1***\2", redacted)
    return _CUIT_QUERY_RE.sub(r"\1***", redacted)
```

This is the concrete evidence for D-05: nothing in `_redact` can catch a bare wire
value. The record contract carries the guarantee; the filter fix is defense in depth.
**Per-package marker/regex sets differ by design** (higyrus has `cuit=`, iol has
`refresh_token` shapes — see the module docstring at `_logging.py:18-20`) — the
intactness test normalizes the `filter` **body**, never the marker tuple.

**Analog (declared variant):** `packages/matriz-client/src/matriz_client/_logging.py:135-157`

```python
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            ...
        # D-22: detect `auth_basic` tuple in extras and split it BEFORE the
        # generic record.__dict__ scan (otherwise the tuple would survive as a
        # non-string field and leak the password).
        if "auth_basic" in record.__dict__:
            split = _redact_auth_basic_tuple(record.__dict__["auth_basic"])
            if split is not None:
                del record.__dict__["auth_basic"]
                record.__dict__.update(split)
        # Scan record.__dict__ for sentinel substrings in extra= values.
        for key, value in list(record.__dict__.items()):
            if isinstance(value, str) and any(m in value for m in _REDACTION_MARKERS):
                record.__dict__[key] = _redact(value)
        return True
```

The **ordering invariant is stated in the comment itself**: the `auth_basic` split
must stay before the generic scan. The recursion fix lands *after* the D-22 block and
*replaces* the generic scan loop in all 5 copies. This is the existing, sanctioned
per-package divergence the intactness test must model as a named variant, not a
failure (Pitfall 5).

---

### `*/client.py` `Client._request` — MOD ×5 (controller, request-response)

**Analog:** `packages/market-data-client/src/market_data_client/client.py:339-396`

```python
    def _request(self, spec: _core.RequestSpec) -> httpx.Response:
        """Dispatch a request against ``base_url`` with per-spec auth branching.
        ...
        """
        headers = dict(spec.headers or {})
        if spec.authenticated:
            self._ensure_token()
            assert self._state.token is not None
            headers["Authorization"] = f"Bearer {self._state.token}"

        request_id = uuid.uuid4().hex
        http = self._ensure_http_client()
        ...
        resp = http.send(req)
        try:
            _raise_for_response(resp)
        except MarketDataAuthError:
            if not spec.authenticated:
                raise
            # Exactly-one re-auth: consume body, clear token, re-authenticate,
            # retry the SAME request once. A persistent 401 re-raises below.
            resp.read()
            self._state.token = None
            self._ensure_token()
            ...
            resp = http.send(req)
            resp.read()
            _raise_for_response(resp)
        return resp
```

The bind is a **single new line inserted before `headers = dict(spec.headers or {})`**:

```python
        _decode.STRICT_DECODE.set(self._state.strict_decode)   # D-03: NO reset
```

Three facts read off this exact body that the planner must not re-derive:
- `_request` **returns `resp`** (line 396) — the decode happens later, in the caller:
  `resp = self._request(spec); return _core.parse_health_response(resp)`
  (`client.py:405-406`). A `try/finally: reset()` would unbind before the decoder reads.
- The **re-auth carve-out re-sends the same request** (lines 388-395). Only the final
  response reaches a parser, so the divergence collector must be scoped to the decode
  entry, never to `_request` (Pitfall 8).
- The mirror site is `market_data_client/aio.py:346` — same signature, `async def`
  (C-3). market-data is the model to copy because it has **only** the method; the
  other four packages additionally carry a module-level shim
  (`higyrus client.py:653`, `iol client.py:685`, `matriz client.py:889`,
  `ambito client.py:296`, and the four `aio.py` twins) that delegates to the default
  client — bind on the **method** only, and add the shim-delegation test
  (RESEARCH Open Question 2).

Full site inventory verified by grep — 9 method sites (5 sync + 4 async; matriz `aio.py:435`,
iol `aio.py:434`, higyrus `aio.py:325`, ambito `aio.py:162`, market-data `aio.py:346`,
plus the 5 sync methods) and 8 module shims which need no bind.
`wallets_client/client.py:57` and `aio.py:73` are module-level functions with no
`_ClientState` — the D-02 exemption.

---

### `matriz_client/ws_client.py` — MOD ×1 (service, streaming)

**Analog:** itself, three sites.

Decode site (`ws_client.py:81-99`) — the only decode path in the repo that never
passes through `_request`:

```python
def _parse_frame(data: dict[str, Any]) -> PrimaryWsMessage:
    """Wrap ``data`` in the safe-access frame model matching its ``type``."""
    type_name = data.get("type", "")
    if type_name == "Md":
        return MarketDataFrame.from_api(data)
    if type_name == "or":
        return ExecutionReportFrame.from_api(data)
    return UnknownFrame.from_api(data)


def _handle_message(ws: websocket.WebSocketApp, raw: str) -> None:
    if _on_message is not None:
        data: dict[str, Any] = json.loads(raw)
        _on_message(_parse_frame(data))
```

Thread creation site (`ws_client.py:184-185`) — the D-04 non-inheritance boundary:

```python
    _ws_thread = threading.Thread(target=_ws.run_forever, daemon=True)
    _ws_thread.start()
```

Precedent for "explicitly hand main-thread state to the daemon thread"
(`ws_client.py:123-140`) — this is the shape to mirror for the mode:

```python
def _acquire_token_for_ws(default: _rest.Client) -> None:
    """Acquire the REST token for the daemon-thread WebSocket connection.

    Phase 10 Plan 10-03 REFAC-04 — 3-way TokenStore wiring. The daemon
    thread participates in the cross-context lock by calling
    ``state.token_store.get_sync()`` directly.
    ...
    """
    default._ensure_token()  # lazy-inits state.token_store if needed
    assert default._state.token_store is not None
    snap = default._state.token_store.get_sync()
    default._state.token = snap.value  # mirror for back-compat header read
```

Called from `ws_connect` at line 165-167 with `default = _rest._get_default()` —
that is exactly where a `strict_decode` snapshot is read. Copy the shape: a small named
`_…_for_ws(default)` helper called from `ws_connect` before the thread starts, with a
docstring citing D-04 the way this one cites REFAC-04. RESEARCH recommends re-`set()`ing
the ContextVar inside `_handle_open` over storing a `copy_context()` (re-entrancy, A1).

`UnknownFrame.from_api` (`models.py:383-391`) is a hand-written duck-typed
implementation that is **not** a `_SafeModel` and retains the whole payload in `raw` —
leave it untouched (Pitfall 13, row 6 of the D-07 matrix).

---

### `packages/*/tests/test_logging.py` — MOD ×5, decode caplog sentinel

**Analog A (assertion surface):** `verification/test_logging_no_token_leak.py:41-60`

```python
_SECRET_LITERAL = "SECRET-LITERAL-12345"
_PACKAGES = ["ambito_financiero_client", "iol_client", "higyrus_client", "matriz_client"]


@pytest.mark.parametrize("pkg_name", _PACKAGES)
def test_token_literal_never_appears_in_log_records(
    pkg_name: str,
    caplog: pytest.LogCaptureFixture,
    httpx_mock: HTTPXMock,
) -> None:
    """LOG-02: even with DEBUG enabled, token literal MUST NOT leak to records."""
    pkg = importlib.import_module(pkg_name)
    ...
        caplog.set_level(logging.DEBUG, logger=pkg_name)
```

The three-surface assertion (docstring lines 10-13) is the contract to reproduce:
`record.getMessage()`, `str(record.args)`, and `record.__dict__` string values.

**Do not extend this file.** It lives in `verification/`, which `ci.yml` never
executes (the tests job passes `packages/${{ matrix.package }}` explicitly, overriding
`testpaths`). The sentinel must travel in-package.

**Analog B (in-package host + record builder):**
`packages/higyrus-client/tests/test_logging.py:25-40, 80-86`

```python
def _make_record(
    msg: str, args: object = None, extra: dict[str, object] | None = None
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="higyrus_client",
        level=logging.DEBUG,
        pathname=__file__,
        lineno=0,
        msg=msg,
        args=args,  # type: ignore[arg-type]
        exc_info=None,
    )
    if extra:
        for k, v in extra.items():
            setattr(record, k, v)
    return record


def test_record_dict_scan_redacts_extra_field() -> None:
    """LOG-02: string values in record.__dict__ (extra={...}) get scrubbed."""
    f = RedactingFilter()
    record = _make_record("ok", extra={"weird_field": "Bearer leaky-token-xxx", "safe": "ok"})
    f.filter(record)
    assert record.__dict__["weird_field"] == "Bearer ***"
    assert record.__dict__["safe"] == "ok"
```

**Caveat for the reserved-key test (Pitfall 1):** this `_make_record` uses `setattr`
and therefore **cannot** reproduce the `KeyError` — `Logger.makeRecord` raises, not
`LogRecord.__init__`. The crit-1g test must go through a real
`logger.warning(msg, extra={...})` call (or `Logger.makeRecord` directly), not through
`_make_record`. Also note `test_account_id_not_redacted` (`:166-178`) — the existing
precedent that an identifier-shaped `extra` key is deliberately **not** redacted, which
is why the divergence record must never carry values.

---

### `tools/check_decode_intactness.py` — NEW (CI script, batch)

**Analog:** `.github/workflows/ci.yml:42-51` — the only in-CI cross-package source gate.

```yaml
      - name: lint-logging (Phase 8 LOG-01 — no logging.basicConfig / logging.root in package src)
        run: |
          # Match actual code calls only, not docstring/comment references:
          #   logging.basicConfig(...)  — call with paren
          #   logging.root.<identifier> — attribute access (not bare "logging.root" in docstrings)
          if grep -rnE --include='*.py' 'logging\.basicConfig\s*\(|logging\.root\.\w' packages/*/src/; then
            echo "::error::Phase 8 LOG-01 violated — package source must not call logging.basicConfig or logging.root.*"
            exit 1
          fi
```

Copy the shape for the ban-list half (`strict=False`, `msgspec.field(`): scoped to
`packages/*/src/`, `--include='*.py'`, a comment explaining why the regex is
call-shaped rather than name-shaped (so docstrings don't false-positive — the
`_decode.py` docstring will legitimately mention `strict`), and `::error::` +
`exit 1`. The step sits in the `lint` job alongside `lint-imports` (`ci.yml:40-41`).

`tools/` **does not exist** — this is a new top-level directory. Nearest structural
precedent is `verification/` (plain package-less scripts run via `uv run python`).

---

### `<scratch>/sizing.py` — throwaway (utility, batch)

**Analog A:** `verification/schema.py:27-40` — supplies the exact type vocabulary D-06
locks, and is the function the witness synthesizer inverts:

```python
def schema_of(payload: Any) -> Any:
    """Reduce un payload a su estructura: claves + tipos, nunca valores.

    - ``dict`` -> ``{clave: schema_of(valor)}`` con claves ordenadas.
    - ``list`` -> ``[schema_of(primer_elemento)]`` si no está vacía, si no ``[]``.
    - escalar -> el nombre de su tipo (``"str"`` | ``"int"`` | ``"float"`` |
      ``"bool"`` | ``"NoneType"`` | ...).
    """
    if isinstance(payload, dict):
        return {k: schema_of(v) for k, v in sorted(payload.items())}
    if isinstance(payload, list):
        # Tipo del primer elemento como muestra; lista vacía -> [].
        return [schema_of(payload[0])] if payload else []
    return type(payload).__name__
```

`type(payload).__name__` is literally the string the divergence record's
`declared_type`/`observed_type` must use — no `type_of()` helper.

**Analog B:** `verification/safemodel_diff.py` — `diff_safemodel_bidirectional` (line 94)
with duck-typed helpers `_is_optional:37`, `_is_safemodel_like:49`,
`_nested_safemodel_class:65`, `_is_list_of_safemodel:89`. Reuse rather than reimplement;
`_is_safemodel_like` is how it works cross-package without importing (C-2).

**Analog C (findings compatibility, D-06):** `verification/findings.py` —
`FINDING_CLASSES:77` and `append_finding:583`. The record keys must be consumable by
`append_finding` in Phase 33 without translation.

**Analog D (ephemeral-env discipline):** `.planning/spikes/SPIKE-005-codegen-tool-choice/`
and `SPIKE-006-libcst-codegen-tool-choice/` — the precedent for `uv run --with X
--no-project` with zero `pyproject.toml`/`uv.lock` mutation, plus `.planning/spikes/CONVENTIONS.md`
for the write-up shape. Both prior spikes ended NO-GO; a signed NO-GO is a valid outcome.

---

## Shared Patterns

### `extra=` key naming discipline (applies to `_decode.py` ×5)

**Source:** `packages/higyrus-client/src/higyrus_client/_transport.py:165-177`

```python
                        extra: dict[str, Any] = {
                            "package": _LOGGER_NAME,
                            "method": request.method,
                            "url": str(request.url),
                            "status_code": response.status_code,
                            "attempt": attempt_number,
                            "request_id": request_id,
                            "endpoint_name": endpoint_name,
                            "retry_reason": f"status_{response.status_code}",
                        }
                        if account_id:
                            extra["account_id"] = account_id
                        self._logger.warning("retry attempt", extra=extra)
```

This is the repo's only existing structured-`extra` emitter and it already dodges every
`LogRecord` reserved name (Pitfall 1): `package`, `method`, `url`, `status_code`,
`attempt`, `request_id`, `endpoint_name`, `retry_reason`, `account_id`. Note in
particular that it says `"method"` and `"url"`, not `"module"`/`"name"`. Copy the
convention verbatim: `"package": _LOGGER_NAME` as the first key, a short constant
message string (`"retry attempt"` → `"decode divergence"`), all values flat and
top-level. It is also **not** all-str (`status_code`/`attempt` are ints) — the decode
record tightens that to all-str per D-05, so this is a naming analog, not a typing one.

**Apply to:** all 5 `_decode.py` copies.

### Package logger acquisition + `NullHandler` opt-in

**Source:** `packages/higyrus-client/src/higyrus_client/_logging.py:103-116`

```python
def attach() -> None:
    """Attach NullHandler + RedactingFilter to the higyrus package logger.

    Idempotent — calling ``attach()`` multiple times does not duplicate the
    handler or filter. ...
    """
    logger = logging.getLogger("higyrus_client")
    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(RedactingFilter())
```

`_decode.py` must use `logging.getLogger("<pkg>")` — the **same** logger name — so the
already-installed `RedactingFilter` covers the new emission path for free. It must
**not** call `attach()` itself and must **not** add a handler. The
`logging.basicConfig`/`logging.root` ban is CI-enforced (`ci.yml:42-51`).

**Apply to:** all 5 `_decode.py` copies. The logger-name literal is one of the three
lines the intactness test normalizes (docstring package name, logger name, `POLICY`
constant).

### `@dataclass(slots=True)` two-arg `super()`

**Source:** `packages/market-data-client/src/market_data_client/models.py:497-502`
(cited in RESEARCH; do not alter)

Any `from_api` override touched this phase keeps `super(Symbol, cls).from_api(payload)`.
Affects market-data and higyrus only — matriz models are `@dataclass(frozen=True)` with
no slots (verified at `matriz models.py:124`), so they are immune.

**Apply to:** `market_data_client/models.py`, `higyrus_client/models.py`.

### Module docstring + `__all__` + `from __future__`

**Source:** `_params.py:1-25`, `models.py:1-27`, `_state.py:1-47`, `_logging.py:1-40`

Every private module in this repo opens with a multi-paragraph docstring that states
purpose, who may import it, and the design rationale ("Why NOT `frozen=True`" /
"Why `slots=True`" in `_state.py:10-18` is the strongest example), then
`from __future__ import annotations`, then a sorted explicit `__all__`.
`_logging.py:31-32` carries the exact sentence the `_decode.py` docstring needs:

```python
NOT importable from ``verification/`` — each paquete duplicates this module by
design (the "no shared internals between packages" constraint).
```

**Apply to:** all new modules.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tools/check_decode_intactness.py` | CI script | batch | No `tools/` directory exists. Closest is the inline `ci.yml:42-51` grep gate (a shell step, not a Python script) and `verification/*.py` (which is inert in CI). The **normalize-then-hash** half has no precedent anywhere in the repo — build from RESEARCH Pitfall 5's normalization rules. |
| `29-AGGREGATION-CONTRACT.md` (dedupe key + per-decode-call collector) | doc artifact | — | No aggregation/dedupe mechanism exists in any package. RESEARCH flags it as a **proposal** (A3), not a finding — the phase must decide it. Same for the strict-mode-on-`extra` question (A2). |

---

## Metadata

**Analog search scope:** `packages/*/src/*/`, `packages/*/tests/`, `verification/`,
`.github/workflows/ci.yml`, `.planning/spikes/`
**Files scanned:** 14 read in full or in targeted ranges; 6 directory/grep censuses
**Pattern extraction date:** 2026-08-18
