# Architecture Research

**Domain:** Integrating an observable msgspec decoder + typed models into 6 self-contained HTTP client packages (market-libs v1.6 "Tipado homogéneo")
**Researched:** 2026-08-18
**Confidence:** HIGH for the integration mechanics (every claim below is read off the repo at `adb82f5`/`milestone/v1.5-mutations` or measured with `uv run --with msgspec --no-project`); MEDIUM for divergence-volume estimates (needs the F29 exploratory run).

> Scope note: this document answers *how the new pieces attach to the existing architecture*. It does not re-litigate DT-01..DT-09.

---

## 0. Corrections to the brief (read from actual code)

Three premises in the research prompt do not match the repo. They change the design.

| Premise in brief | What the code says | Consequence |
|---|---|---|
| "iol = module globals + Client class" vs "market-data = `_ClientState`" | **Both are identical.** `iol_client/_state.py:75-103` declares `@dataclass(slots=True) _ClientState`, exactly like `market_data_client/_state.py:84-114`. iol's module globals are a **read-only PEP 562 shim** (`iol_client/client.py:737-756`) that *forwards* `_token`/`_token_expires_at`/`_refresh_token`/`_client` to `_get_default()._state.*`, with `_user`/`_password`/`_base_url` explicitly denied (`client.py:734`). There is no writable module state in either package. | **One insertion pattern serves all 6 packages.** No per-architecture branch is needed. |
| "`SafeModel`/`_coerce` duplicated verbatim 3×" | **Two different implementations.** `higyrus_client/models.py` and `market_data_client/models.py:66-125` are byte-identical modulo two docstring/comment words (verified with `diff`). `matriz_client/models.py:60-115` is a **different design**: `_SafeModel` mixin + `_convert`, an `empty()` constructor, all fields `Optional` with defaults, and **scalars pass through completely unvalidated** (`_convert` returns `value` unchanged for anything that is not `list`/`dict`/model). | The "copy verbatim 6×" (DT-03) is really "**write once, copy 5×, and reconcile matriz separately**". matriz is the highest-divergence-risk package (§6). |
| "AST surface gate + parity test plug into CI" | **`verification/` is never executed by CI.** `ci.yml:112-118` runs `pytest packages/${{ matrix.package }}` — an explicit path argument that overrides `testpaths` (`pyproject.toml:106`). The pre-commit mypy hook is scoped `files: ^packages/.*/src/`. So `verification/test_public_surface.py`, `test_sync_async_isolation.py`, `test_with_options.py` etc. run **only locally**. | GATE-TYP-01 needs a **new CI job**, not just a new test file. This is the single most important finding for Phase 32. |

---

## 1. Standard Architecture — where the new pieces land

### 1.1 Current per-package layering (verified)

```
┌──────────────────────────────────────────────────────────────────────┐
│ __init__.py      __all__ + __version__ + _logging.attach()           │
│                  (iol_client/__init__.py:29, 5 of 6 packages)        │
├──────────────────────────────────────────────────────────────────────┤
│ client.py (sync)                     aio.py (async)                  │
│  class Client                         class AsyncClient              │
│   ._state: _ClientState  ◄── SHARED ──►  ._state: _ClientState       │
│   ._request(spec) -> httpx.Response     ._request(spec) -> Response  │
│   .with_options() → view (shares _state, _is_view=True)              │
│  module shims (PEP 562 __getattr__, read-only)                       │
├──────────────────────────────────────────────────────────────────────┤
│ _core.py — PURE. build_*(state) -> RequestSpec | parse_*(resp) -> T  │
│            import-linter: MUST NOT import client.py / aio.py         │
├──────────────────────────────────────────────────────────────────────┤
│ models.py (3/6)   types.py (1/6)   exceptions.py   _state.py         │
│ _transport.py  _atransport.py  _logging.py  _params.py   (dup 6×)    │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Insertion points for v1.6

```
┌──────────────────────────────────────────────────────────────────────┐
│ client.py / aio.py   ── MODIFIED: 1 line at top of each _request     │
│                          _decode.bind(self._state.strict_decoding)   │
│                       ── MODIFIED: Client.__init__ / configure()     │
│                          gain strict_decoding kwarg (mirror of       │
│                          mutating_allowed, market-data client.py)    │
├──────────────────────────────────────────────────────────────────────┤
│ _core.py             ── UNCHANGED call shape. parse_* keep the       │
│                          (resp) -> T signature. Only the return      │
│                          TYPE changes (iol: dict → Quote).           │
├──────────────────────────────────────────────────────────────────────┤
│ models.py            ── MODIFIED: SafeModel.from_api body only       │
│                          (signature preserved, DT-05)                │
│ _decode.py   ★ NEW   ── msgspec detector + ContextVar mode carrier   │
│                          + divergence emitter (logger of the pkg)    │
│ types.py     ★ NEW×5 ── Literal aliases                              │
│ exceptions.py        ── MODIFIED: + <Pkg>DecodeError                 │
├──────────────────────────────────────────────────────────────────────┤
│ _state.py            ── MODIFIED: + strict_decoding: bool = False    │
└──────────────────────────────────────────────────────────────────────┘

verification/divergences.py  ★ NEW  — logging.Handler → findings (driver side)
tools/check_surface_types.py ★ NEW  — AST gate (cross-package)
.github/workflows/ci.yml     ── MODIFIED: new `gates:` job (see §7)
```

### 1.3 New vs modified, per package

| Package | `_decode.py` | `models.py` | `types.py` | `exceptions.py` | `_state.py` | `client.py`/`aio.py` |
|---|---|---|---|---|---|---|
| `market-data-client` | NEW (canonical, written first) | MODIFY (`from_api` body; `MarketDataSnapshot.from_api` + `Symbol.from_api` need pre-injection — §3.4) | NEW (min: `MarketId`, entry-type codes) | +`MarketDataDecodeError` | +`strict_decoding` | 1 line × 2 (`client.py:339`, `aio.py`) + ctor/`configure` kwarg |
| `higyrus-client` | NEW (verbatim copy) | MODIFY (`from_api` body only — identical base to market-data) | NEW (min) | +`HigyrusDecodeError` | +`strict_decoding` | 1 line × 2 |
| `iol-client` | NEW (verbatim copy) | **NEW file** (§6) | NEW (`Mercado`, `Plazo`, move `InstrumentType` here) | +`IOLDecodeError` | +`strict_decoding` | 1 line × 2 + 16 signatures (TYP-01) |
| `matriz-client` | NEW (verbatim copy) | MODIFY (**different base** `_SafeModel`/`_convert`/`empty()` — needs its own reconciliation, §6.3) | EXISTS (`types.py`, 130 LOC) | +`MatrizDecodeError` | +`strict_decoding` | 1 line × 2 |
| `ambito-financiero-client` | NEW (verbatim copy, currently unused) | **NEW file** (empty/structural, TYP-03) | NEW (empty) | +`AmbitoDecodeError` | +`strict_decoding` | 1 line × 2 (or skip — returns `float`) |
| `wallets-client` | **SKIP or empty** — no `_core.py`, no `_state.py`, no models, stub only | NEW (empty, TYP-03) | NEW (empty) | — | — | — |

---

## 2. DECISION 1 — Decode boundary: bytes vs dict

### 2.1 The `_request` boundary is architecturally excluded

`Client._request(spec) -> httpx.Response` is a **generic** dispatcher: `iol_client/client.py:429-491` and `market_data_client/client.py:339-393` are identical in shape and know nothing about the target type. Type information exists **only** in the parser that the endpoint method calls next (`client.py:508-510`: `spec = _core.build_...` → `resp = self._request(spec)` → `return _core.parse_get_quote_response(resp)`). Phase 7 D-03 locked "transport shell consumes `httpx.Response`" (`iol_client/_core.py:5`).

So "bytes → `msgspec.json.decode` at the `_request` boundary" is not an option; the real choice is **inside the parser** (`resp.content` is available there) vs **inside `from_api`** (dict).

### 2.2 The two candidates

| | **A. bytes in the parser** — `msgspec.json.decode(resp.content, type=list[Quote])` | **B. dict in `from_api`** — `msgspec.convert(payload, type=cls)` ✅ RECOMMENDED |
|---|---|---|
| Skips `resp.json()` | Yes — single parse pass | No — double pass (stdlib json then convert) |
| Error path quality | `Expected `bool`, got `str` - at `$.expired`` (measured) | Identical string (measured — both paths produce the same `ValidationError`) |
| Envelope handling | **Breaks.** `parse_symbols_response` (`market-data `_core.py:958-1021`) branches list-vs-object; `parse_calendar_response` (`:1024-1057`) reaches into `days[]`; `parse_get_instruments_by_type_response` (`iol `_core.py:354-360`) reads `data["titulos"]`; higyrus has 10 envelope-key sites (Phase 4). All were **live-verified fixes** — re-expressing them as msgspec wrapper types re-litigates Phase 27 work. | Untouched. Envelope logic keeps operating on the dict; only the leaf construction changes. |
| DT-05 (`from_api` preserved) | Needs a **second** decode implementation for `from_api`, because `from_api` receives a dict. Two code paths to keep in sync × 6 packages. | One implementation serves both parsers and direct `from_api` callers. |
| `received_at` client stamp (D-01) | Post-processing required after decode (`dataclasses.replace` on a frozen slots class) | Pre-injection into the dict before convert — 1 line |
| Merge gate "3 suites green, zero test changes" | High risk: parser tests build `httpx.Response(200, json=…)` and assert on parsed output; behaviour of the envelope branches would shift | Low risk: the fast path returns the same values `_coerce` returns today |
| Perf | ~2× faster on large payloads | Irrelevant at observed sizes (largest live payload is `get_instruments_by_type` ≈ a few hundred rows) |

**Verdict: B (dict, `msgspec.convert`, inside `from_api`).** The decisive argument is not performance, it is **blast radius**: option A puts the change inside ~30 live-verified parsers across 6 packages; option B puts it inside **one function per package** (`SafeModel.from_api`) plus two overrides in market-data.

Keep `msgspec.json.decode(bytes, …)` in the back pocket for a future perf phase — the model classes are identical either way, so B does not foreclose A.

### 2.3 msgspec cannot *replace* `_coerce` — it *demotes* it

Measured (`msgspec 0.21.1`, `uv run --with msgspec --no-project`):

```
convert({... "expired":"no"}, type=Instrument)  → ValidationError: Expected `bool`, got `str` - at `$.expired`
convert({"symbol":"a","marketId":"b"},   ...)   → ValidationError: Object missing required field `segment`
convert({... , "EXTRA":1},               ...)   → OK (extra keys ignored by default)
convert(None / [1,2],                    ...)   → ValidationError: Expected `object`, got `null` / `array`
```

msgspec **raises** where `_coerce` **substitutes**. Under DT-02 (observable, *not* fatal) the tolerant behaviour must survive. Therefore:

```python
# _decode.py (per package, copied verbatim — DT-03)
def decode_model(cls, payload, *, path=""):
    try:
        return msgspec.convert(payload, type=cls, strict=True)   # DETECT (fast path)
    except msgspec.ValidationError as exc:
        if _strict_mode():                                        # drivers
            raise <Pkg>DecodeError(str(exc), model=cls.__name__, path=path) from exc
        _emit_divergence(cls, exc, path)                          # observable
        return _coerce_all(cls, payload)                          # REPAIR (legacy)
```

`_coerce` survives as the **cold/repair path only**. Frame this honestly in the Phase 29 plan: the plan text says "`_coerce` reemplazado"; what is achievable while honouring DT-02 + DT-05 is "`_coerce` demoted behind an msgspec detector". Well-formed payloads (the overwhelming majority) never touch `_coerce` again.

### 2.4 Measured blind spots of the detector (must be documented, not discovered in F33)

| Case | msgspec strict behaviour (measured) | Implication |
|---|---|---|
| wire `int` where model says `float` (`3` → `3.0`) | **Silently widened, no error** | Same as today's `_coerce` (`models.py:121-122`). No regression, but the decoder will *not* catch it. |
| wire `"123.5"` where model says `float` | `ValidationError` at `$.ultimoPrecio` | This is the divergence class the milestone exists to catch. Do **not** pass `strict=False` — that coerces it silently (measured: `convert(..., strict=False)` → `123.5`). |
| multiple bad fields in one payload | **Only the first error is reported** (`{"symbol":1,"marketId":2,...}` → only `$.symbol`) | One divergence record per decode. Enumerating *all* divergences in one live run needs repeated decodes or the `_coerce` repair pass to also report. See §5.3. |
| `Literal[...]` field with an unlisted value | `ValidationError: Invalid enum value 'ZZZZZZ' - at `$.cficode`` | **matriz risk**: `matriz_client/models.py` types fields as `CFICode`, `MarketId`, `OrderType`, `Currency`… from `types.py`. Today `_convert` passes them through unvalidated. Under the decoder every unlisted enum value from Primary becomes a divergence. This is the top F33 volume driver — and DT-07's "Literal set from live evidence" applies retroactively to matriz's existing aliases. |
| nested error path | `Object missing required field `precioVenta` - at `$.puntas[0]`` | Path strings are precise enough to be a finding title verbatim. |

---

## 3. DECISION 2 — Where the mode flag lives

### 3.1 The constraint that decides it

The decode site is `Model.from_api(payload)` — a **classmethod with no access to client state**, whose signature is frozen by DT-05. The nearest state-bearing frame is the endpoint method (`self._state`), two calls up:

```
Client.get_quote(...)              ← has self._state          (client.py:497)
  └─ self._request(spec)           ← has self._state          (client.py:429)
  └─ _core.parse_get_quote_response(resp)   ← PURE, only (resp)   (_core.py:327)
       └─ Quote.from_api(payload)  ← classmethod, no state    (models.py:73)
```

`_core` may not import `client`/`aio` (import-linter, `pyproject.toml:163-167`), and parsers take only `httpx.Response`.

### 3.2 Options evaluated

| Carrier | Verdict |
|---|---|
| **Extra kwarg on `parse_*` and `from_api`** | Rejected. Touches ~30 parsers × 6 packages, and threading `strict=` through `from_api` weakens DT-05 (every nested `_coerce`→`from_api` recursion has to forward it). |
| **`resp.request.extensions["decode_strict"]`** (the shell already writes `idempotent`/`request_id`/`endpoint_name`/`max_attempts` there — `client.py:459-465`) | Rejected as *sole* carrier. Package test suites build bare `httpx.Response(200, json=…)` with **no request attached** (e.g. `higyrus/tests/test_core.py:60`, `ambito/tests/test_core.py:92`, ~40 sites) — `resp.request` raises `RuntimeError` there. Would need a try/except at every read and breaks the "zero test changes" merge gate the moment anything asserts on it. Viable as a *secondary* signal for `endpoint_name` enrichment only. |
| **Module-level global in `_decode.py`** | Rejected. Two `AsyncClient`s with different modes on the same event loop would clobber each other between `await` points. Real hazard: the drivers run interleaved sync/async probes (`main_matriz.py` 19 paired probes in one `main()`). |
| **`_ClientState.strict_decoding` only** | Necessary but not sufficient — invisible from `from_api`. |
| **`ContextVar` in `_decode.py`, bound from `_ClientState` at the top of `_request`** ✅ | Recommended. |

### 3.3 Recommended design

```python
# <pkg>/_decode.py   (copied verbatim per package — DT-03)
_STRICT: ContextVar[bool] = ContextVar("<pkg>_decode_strict", default=False)

def bind(strict: bool) -> None:        # called by the transport shells
    _STRICT.set(strict)

@contextmanager
def strict_mode(value: bool = True):   # drivers / parser-level unit tests
    tok = _STRICT.set(value)
    try: yield
    finally: _STRICT.reset(tok)
```

```python
# <pkg>/_state.py  — one new field, next to mutating_allowed
strict_decoding: bool = False
```

```python
# <pkg>/client.py :429  and  aio.py — literally the first statement of _request
def _request(self, spec: RequestSpec) -> httpx.Response:
    _decode.bind(self._state.strict_decoding)
    ...
```

**Why this is correct, point by point:**

- **`with_options` views inherit for free.** `with_options` shares `_state` by reference (`iol_client/client.py:326`: `view._state = self._state`). Putting `strict_decoding` on `_ClientState` reuses the exact precedent that `_state.py:98-105` documents for `mutating_allowed`/`expected_host`: *"Viven SÓLO en el `_ClientState` compartido — nunca en un `__slots__` de instancia — así un view de `with_options` hereda el estado del gate del parent (D-14)."* Do **not** put it in `Client.__slots__` (`client.py:128`) — that is the mistake the Phase 25 comment was written to prevent.
- **`bind()` in `_request` is safe.** Between `_request` returning and the parser running there is **no `await` and no other statement** (`client.py:508-510`). The value is re-bound on *every* request, so two clients with different modes interleaved in the same task each set it immediately before their own parse.
- **Async isolation is free.** asyncio copies the `Context` per `Task`, so a `set()` inside one task never leaks to a sibling — exactly the property a module global lacks.
- **Drivers get strict mode without touching runtime defaults.** `Client(strict_decoding=True)` / `configure(strict_decoding=True)` — a plain `bool` kwarg, symmetric with `mutating_allowed` (`market_data_client/client.py` ctor), no msgspec type in any public signature (DT-01 preserved).
- **Direct `Model.from_api(dict)` calls** (tests, `verification/safemodel_diff.py` consumers, fixtures) hit the ContextVar default `False` = observable. Zero test churn.
- **Escape hatch for `_core` unit tests**: `with _decode.strict_mode(): _core.parse_x(resp)`.

**Precedence rule to write into the plan:** an explicit `strict_mode()` context manager wins over `_state.strict_decoding` for the duration of the block, because `_request` only calls `bind()` on the *next* request; a driver that wraps a whole probe in `strict_mode()` and issues no further requests keeps its value. If a probe issues a request *inside* the block, `bind()` overwrites it — therefore **drivers should set `strict_decoding=True` on the Client, not use the context manager**, and reserve the context manager for offline decoding of captured payloads.

### 3.4 Two market-data overrides need pre-injection

`MarketDataSnapshot.from_api(payload, *, received_at)` (`models.py:150-168`) injects the client stamp *bypassing* `_coerce`. Under msgspec, `received_at: float` is a **required field absent from the wire**, so a naive `convert()` would fail on every single response and permanently take the slow path. Fix — inject into the dict *before* convert, preserving D-01 (wire value never wins):

```python
data = payload if isinstance(payload, dict) else {}
return _decode.decode_model(cls, {**data, "received_at": received_at})
```

`Symbol.from_api` (`models.py:485-502`) already pre-processes (`market_id` → `marketId` mirror) and composes cleanly — keep the mirror, then delegate. Note its explicit two-arg `super(Symbol, cls)` comment at `:497-501` (slots rebuild the class): keep that idiom if the delegation stays a `super()` call.

---

## 4. Traced call chains (the exact edit sites)

### 4.1 market-data-client — `get_market_data`

```
Client.get_market_data(...)                 client.py  (endpoint method)
 └ _core.build_market_data_request(state)   _core.py                    [unchanged]
 └ Client._request(spec)                    client.py:339   ★ + _decode.bind(...)
    └ http.send(req)  ← RetryTransport, extensions idempotent/request_id/
                        endpoint_name/max_attempts (client.py:372-377)
 └ _core.parse_market_data_response(resp)   _core.py:846-874            [unchanged]
    ├ resp.read()                                  :858
    ├ received_at = time.time()                    :859   ← D-01 stamp, ONE per response
    ├ raise_for_response(resp)                     :860
    ├ raw = resp.json()                            :863
    ├ <envelope/rows unwrap>                       :864-873              [unchanged]
    └ MarketDataSnapshot.from_api(item, received_at=received_at)  :874
        └ models.py:150  ★ REWRITE BODY → _decode.decode_model(cls, {**data, "received_at": ...})
```

Reference parsers (`parse_instruments_response` `:926`, `parse_segments_response` `:942`, `parse_symbols_response` `:958`, `parse_calendar_response` `:1024`, `parse_calendar_config_response` `:1060`) all end in `Model.from_api(item)` and need **zero** edits — they inherit the new behaviour through `SafeModel.from_api` (`models.py:73-81`).

Untyped ops endpoints for TYP-02: `parse_health_response` (`_core.py:280-284`) and `parse_calendar_write_response` (`_core.py:1076-1104`) still `return dict[str, Any]` — these are the Phase 31 targets.

### 4.2 iol-client — `get_quote`

```
Client.get_quote(simbolo, *, mercado, plazo)  client.py:497-510
 └ _core.build_get_quote_request(...)          _core.py:234-256   ★ mercado/plazo → Literal (DT-07)
 └ Client._request(spec)                       client.py:429      ★ + _decode.bind(...)
 └ _core.parse_get_quote_response(resp)        _core.py:327-332
    ├ resp.read() / raise_for_response(resp)          :329-330
    ├ data: dict[str, Any] = resp.json()              :331
    └ return data                              ★ → return Quote.from_api(data)
```

Then, mechanically, per endpoint: `client.py` method annotation, `client.py` module shim annotation, `aio.py` method annotation, `aio.py` module shim annotation = **4 sites × 4 endpoints = 16** (matches the plan). Shim sites: `client.py:647`, `:657`, `:671`, `:676`; same offsets in `aio.py`. Plus `__init__.py:53-72` `__all__` gains the model names, and `verification/snapshots/iol-client-surface.txt` must be regenerated (`python verification/regen_snapshots.py`) — the golden-file test at `verification/test_public_surface.py:153` will otherwise fail locally.

---

## 5. Divergence records — flow, shape, and the findings lifecycle

### 5.1 Logger identity (per package, already wired)

`_logging.attach()` runs at import time from `__init__.py` (`iol_client/__init__.py:29`, and the same line in ambito/higyrus/matriz/market-data — **wallets has none**). It attaches a `NullHandler` + `RedactingFilter` to `logging.getLogger("<pkg_module_name>")` (`market_data_client/_logging.py:97-101`), idempotently, and never touches the root logger (CI grep gate, `ci.yml:42-50`).

The decoder must therefore use `logging.getLogger("<pkg>")` — the **same** name `_transport.py` uses (`_LOGGER_NAME`, `_transport.py:155`) — not a child logger with a new name, otherwise nothing is guaranteed about filter attachment. (A child `"<pkg>.decode"` would also work since filters on the parent are *not* applied to records logged via a child — `logging.Filter` on a logger only filters records logged **directly** on it. **Use the package logger itself.** This is a real footgun: a `getLogger("market_data_client.decode")` record would bypass `RedactingFilter` entirely.)

### 5.2 Record shape — mirror `_transport.py`

`_transport.py:196-208` establishes the house style: `logger.warning("<short message>", extra={...})`. Adopt it verbatim so downstream consumers see one schema:

```python
logger.warning(
    "decode divergence",
    extra={
        "package": _LOGGER_NAME,          # same key as _transport.py:197
        "model": cls.__name__,            # "MarketDataSnapshot"
        "field_path": "$.entries[0]",     # msgspec path, verbatim
        "expected": "float",
        "observed": "str",
        "reason": "type_mismatch" | "missing_field" | "not_an_object" | "invalid_enum",
        "endpoint_name": ...,             # optional, from resp.request.extensions
    },
)
```

**Never put the payload (or a payload slice) in the record.** `RedactingFilter.filter` (`_logging.py:71-85`) scrubs `record.msg`, `record.args`, and *string* values in `record.__dict__` — but only against 4 known markers (`Bearer `, `client_secret=`, `"client_secret"`, `"access_token"`, `_logging.py:47-52`), and it does **not** recurse into dicts/lists inside `extra`. A `extra={"payload": {...}}` would be a credential-leak vector past the filter. Field paths + type names are safe by construction. Add this as an explicit assertion in the Phase 29 caplog sentinel test (the SEC-01 precedent, `verification/test_logging_no_token_leak.py`).

### 5.3 Driver side — how a record becomes a finding

Today's divergence pipeline is **static structural diff**, not runtime:

```
probe → client.get_x()                 → typed models
      → _raw_via_request_sync(...)     → raw wire dict  (re-fetch via _core builder)
      → diff_safemodel_bidirectional(sample, Model)   verification/safemodel_diff.py
      → _emit_shape(...)               main_market_data.py:572-610
      → append_finding(class_="SHAPE", status="OPEN", ...)  verification/findings.py:583
```

`diff_safemodel_bidirectional` is deliberately **duck-typed** (`safemodel_diff.py:49-60`: `is type` + `is_dataclass` + `callable(from_api)`) so it works across packages without importing any of them. That is the template for the new piece.

**Recommended new module: `verification/divergences.py`** — a `logging.Handler` the driver installs on `logging.getLogger(<pkg>)` for the duration of `main()`:

```python
class DivergenceCollector(logging.Handler):
    """Collect 'decode divergence' records; expose them as finding rows."""
    records: list[dict[str, Any]]
    def emit(self, record): ...   # filter on record.__dict__.get("reason")
```

Then in the driver: `for d in collector.drain(): append_finding(_PKG, fid=_next_fid(), class_="SHAPE", ...)`.

Why a collector and not just strict mode:

| | Strict mode (raise) | Observable + collector |
|---|---|---|
| Divergences seen per probe per run | **1** (first raise aborts the probe) | all of them |
| Interaction with existing probe `try/except` | Lands in `_finding_for_exc` / `except Exception` (already narrowed by CR-06, `verification/test_main_drivers_bare_except.py`) → needs a dedicated `except <Pkg>DecodeError` arm per probe | zero probe changes |
| Fit for the F29 **exploratory sizing run** (the plan's #1 risk mitigation) | poor — under-counts | **exactly right** |
| Fit for the F33 **gate** | good — a divergence is a hard failure | needs an explicit `if collector.records: FAIL` |

**Use both, in this order:** observable + collector for enumeration (F29 sizing run and F33 discovery), then flip `strict_decoding=True` for the cycle-closure gate once the findings are triaged. Note `FINDING_CLASSES` (`verification/findings.py:77-86`) is a closed tuple — `SHAPE` covers type/missing-field divergences; **do not** add a new class unless the roadmap accepts touching the findings schema and every existing `-findings.md`.

Also note `append_finding(..., idempotent_by_title=True)` (`findings.py:597`, HARN-08) — the divergence titles are content-addressable (`"type_mismatch $.ultimoPrecio en Quote (str, expected float)"`), so re-runs dedupe for free and human triage (`CONFIRMED`/`EXPECTED`/`NO-FIX`) survives (`findings.py:607-609`).

---

## 6. iol-client models — scope, from measured payloads

### 6.1 The evidence is already committed

`.planning/verification/schemas/iol-client/*.json` are **live-captured field→type maps** from `api.invertironline.com` on 2026-06-06 (written by `probe_schema_snapshot`, D-25 no-overwrite). These, not the docstrings, are the source of truth for Phase 30.

| Endpoint | Wire shape (measured) | Proposed model |
|---|---|---|
| `get_quote` → `Cotizacion` | **object**, 20 keys: `apertura` float, `cantidadOperaciones` **int**, `cierreAnterior` float, `descripcionTitulo` str, `fechaHora` str, `interesesAbiertos` float, `laminaMinima` int, `lote` int, `maximo` float, `minimo` float, `moneda` str, `montoOperado` float, `plazo` str, `precioAjuste` float, `precioPromedio` float, `puntas` **`[]`**, `tendencia` str, `ultimoPrecio` float, `variacion` float, `volumenNominal` float | `Quote` |
| `get_historical_quotes` → `seriehistorica` | **list of objects, same 20 keys**, but `descripcionTitulo` **null**, `plazo` **null**, `puntas` **null** | **reuse `Quote`** with those three as `… | None` |
| `get_instruments` | **list of objects, 2 keys**: `instrumento` str, `pais` str | `InstrumentKind` (2 fields) — the current `-> Any` (`_core.py:343`) is over-cautious; the shape is trivial |
| `get_instruments_by_type` | **envelope** `{"titulos": [ … ]}`; rows have 21 keys: `apertura` float, `cantidadOperaciones` **float**, `descripcion` str, `fecha` str, `fechaVencimiento` null, `laminaMinima` int, `lote` int, `maximo` float, `mercado` str, `minimo` float, `moneda` str, `plazo` str, `precioEjercicio` null, `puntas` **object** `{cantidadCompra, cantidadVenta, precioCompra, precioVenta}` all float, `simbolo` str, `tipoOpcion` null, `ultimoCierre` float, `ultimoPrecio` float, `variacionPorcentual` float, `volumen` float | `TituloCotizacion` + `Punta` (nested) |

### 6.2 Two measured traps that a single shared model would walk into

1. **`puntas` is polymorphic across endpoints.** `[]` (array) on `get_quote`, `null` on `seriehistorica`, and a **single object** of 4 floats on `get_instruments_by_type`. Measured: `convert({"puntas": {...}}, type=Quote)` → `Expected `array | null`, got `object` - at `$.puntas``. → `Quote.puntas: list[Punta] | None = None`, `TituloCotizacion.puntas: Punta | None = None`. **Do not share the field type.**
2. **`cantidadOperaciones` is `int` on quote/historical and `float` on the by-type rows.** Under strict decoding `float`-typed models accept ints (widening is silent, §2.4) but `int`-typed models reject floats. → declare it `float` on both models, or `int` on `Quote` only after F33 confirms.

Also: `puntas: []` was captured *while the array was empty* — the element shape is **unknown**. Declare `Punta` from the by-type object and mark `Quote.puntas` element type as a Phase-33 confirmation item (this is a genuine "measured absence", not a guess).

Consequence for `main_iol.py`: only **2** call sites actually consume returned data by string key (`main_iol.py:316`, `:395` — `quote.get("ultimoPrecio")`). `main_iol.py:1032` (`envelope["titulos"]`) reads a **raw re-fetch** through `_core.RequestSpec`, not a client return, and `probe_field_type_map` (`:957`) deliberately compares `schema_of(raw)` against `_ASSUMED_*` (`:111-121`) — that probe stays dict-based by design. The plan's "6 sitios" is an overcount; scope it at **2 migrations + 1 review**.

### 6.3 matriz needs its own reconciliation, not a copy

`matriz_client/models.py` uses a different base (`_SafeModel` + `_convert` + `empty()`, `:60-115`), and its field types are `Literal` aliases from `types.py`. Two specific hazards for Phase 29/31:

- `Model.from_api(non_dict)` currently returns `cls.empty()` (`:107-108`), and nested non-dicts return `inner.empty()` (`:86`). msgspec raises on both. The observable fallback must preserve `empty()` semantics, not the higyrus `""`/`0.0` semantics.
- `Instrument.instrumentId: InstrumentId = field(default_factory=InstrumentId.empty)` (`:152`) — a `default_factory` referencing a classmethod of another model. Validate this decodes before committing matriz to the shared helper.
- Every `Literal` field is a latent divergence under strict decoding (measured: `Invalid enum value`). DT-07's "close the set with live evidence" must be applied to matriz's **existing** aliases in F33, not only to iol's new `mercado`/`plazo`.

---

## 7. Gates — where they plug in (and the CI hole)

### 7.1 Existing cross-package infrastructure

| Mechanism | Location | Runs in CI? |
|---|---|---|
| mypy strict, src | `pyproject.toml:97` (`files = [...]`, **5 packages — market-data absent**) → `ci.yml:81` `uv run mypy` | ✅ |
| mypy, tests | `ci.yml:83-89` loop over **5 packages — market-data absent** | ✅ |
| import-linter | `pyproject.toml:140-173` — `root_packages` has **4**, 4 `forbidden` contracts, **no `market_data_client._core` contract** → `ci.yml:41` | ✅ |
| ruff / ruff-format | `ci.yml:36-39` | ✅ |
| LOG-01 grep gate | `ci.yml:42-50` (inline bash over `packages/*/src/`) | ✅ |
| pre-commit (ruff + mypy `files: ^packages/.*/src/`) | `.pre-commit-config.yaml` | ✅ |
| Package tests | `ci.yml:112-118` — `pytest packages/<pkg>` × 6 pkgs × py3.12/3.13 | ✅ |
| **`verification/` meta-tests** (`test_public_surface.py`, `test_sync_async_isolation.py`, `test_with_options.py`, `test_logging_no_token_leak.py`, 25 files) | repo root `verification/`, reachable only via `testpaths` (`pyproject.toml:106`) | ❌ **NEVER** — the explicit `packages/<pkg>` path argument overrides `testpaths` |

That last row is the load-bearing finding: **the existing public-surface golden-file gate has never run in CI.** DT-09 says the new gates are first-class deliverables; putting them in `verification/` alone would reproduce the same silence.

### 7.2 Recommended placement

| New gate | Where | Why |
|---|---|---|
| **AST surface gate** (zero `Any`/`dict[str, Any]` in `__all__` return annotations, DT-06 exemptions) | `tools/check_surface_types.py` (standalone script, stdlib `ast` only, no imports of the packages) + a thin `verification/test_surface_types.py` wrapper for local runs | Must be cross-package by nature. As a *script* it can run in the existing `lint` job next to the LOG-01 grep (`ci.yml:42`) with zero new workflow surface. Using `ast` (not `import` + `get_type_hints`) avoids importing 6 packages in the lint job and sidesteps `from __future__ import annotations` string-hint resolution. |
| **sync/async parity test** (DT-04) | **In-package**, one file per package: `packages/<pkg>/tests/test_sync_async_parity.py` | This is the **market-data precedent**: `packages/market-data-client/tests/test_public_surface_market_data.py` exists precisely because the cross-package nets exclude that package (PROJECT.md Phase 25 note). In-package tests ride the existing 6×2 matrix (`ci.yml:97-104`) for free, on both Python versions. It also needs `get_type_hints()` at runtime, which wants a real import. |
| **New `gates:` CI job** running `uv run pytest verification/ -q` | `ci.yml` | Optional but strongly recommended: it retro-actively activates ~25 existing meta-tests. Expect an initial red run — `verification/test_matriz_sweep_snapshot.py` has known pre-existing failures (17-19, phase-07 era, noted in PROJECT.md). Budget for triage or scope the job to a selected file list. |

**Non-vacuity requirement (Phase 15 WR-01/WR-02 precedent, cited in the plan).** Both gates must fail on a seeded violation. Concretely: the parity test must assert a **non-empty** discovered name set before comparing (`assert len(sync_names) >= N`), and the AST gate must be unit-tested against a fixture module that declares `def f() -> dict[str, Any]` in `__all__` and assert it is reported.

**Gate blind spot to decide explicitly:** DT-06 covers *return annotations*. It does **not** cover `Any` on **model fields** — `MarketDataSnapshot.market_data: dict[str, Any]` (`models.py:145`), `CalendarConfig.warnings: list[Any]` (`:558`), `InstrumentDetail.tickPriceRanges: dict[str, Any]` (matriz `models.py`). `snapshot.market_data["typo"]` remains an unchecked typo vector even after v1.6. Either extend the gate to fields of exported models with a documented exemption list, or write the carve-out into DT-06 so it is a decision rather than an oversight.

### 7.3 D-16 closure checklist (exact edits)

1. `pyproject.toml:97` — append `"packages/market-data-client/src"` to mypy `files`.
2. `pyproject.toml:141-146` — add `"market_data_client"` to `root_packages`.
3. `pyproject.toml` — new contract, copying the shape at `:169-173`:
   `market_data_client._core does not depend on transport modules` / `forbidden_modules = ["market_data_client.client", "market_data_client.aio"]`.
4. `ci.yml:85` — add `market-data-client` to the mypy-tests `for pkg in …` loop.
5. Expect fallout: `market_data_client/tests` has never been mypy-checked; budget a fix pass in the same plan.

---

## 8. Recommended build order

```
F29  DEC-01  ─────────────────────────────────────────────► load-bearing
  29a  msgspec dep decision + _decode.py in market-data-client
       (canonical implementation; the package with the most models)
  29b  _state.strict_decoding + ctor/configure kwarg + bind() in
       client.py/aio.py _request  ×2 surfaces
  29c  SafeModel.from_api rewrite + the 2 overrides (MarketDataSnapshot
       received_at pre-injection, Symbol mirror)   ← MERGE GATE:
       189 market-data tests green with ZERO test edits
  29d  copy verbatim → higyrus (identical base, cheap)
  29e  matriz reconciliation (DIFFERENT base — _SafeModel/empty()/Literals)
  29f  ambito + iol + wallets: _decode.py present (iol's is used in F30)
  29g  verification/divergences.py collector
  29h  ★ EXPLORATORY STRICT RUN — observable+collector against all 4 live
       APIs, count divergences, DO NOT fix. Gate for committing F30-F32.
                    │
      ┌─────────────┴──────────────┐
      ▼                            ▼
F30  TYP-01 iol                   F31  TYP-02/03 ops models
  models.py from the 4 committed    higyrus.get_health,
  schema snapshots (§6.1)           market-data health/health_feed/
  16 signatures + _core parsers      add_holidays/delete_holiday
  mercado/plazo Literal (PROVISIONAL  models.py+types.py in all 6
    until F33 closes the set)        (ambito/wallets structural only)
  regen verification/snapshots/      ⚠ add_holidays/delete_holiday are
    iol-client-surface.txt             PUBLISHED v0.4.0 mutations —
  main_iol.py:316,:395 → attribute     verify the mutation gate contract
      └─────────────┬──────────────┘   (_ensure_mutation_allowed must
                    ▼                   remain the literal first statement)
F32  GATE-TYP-01
  AST surface gate (tools/, wired into ci.yml lint job)
  per-package sync/async parity tests (rides the 6×2 matrix)
  optional `gates:` job for verification/
  D-16 closure (5 edits, §7.3)
                    ▼
F33  LIVE-TYP-01   strict_decoding=True on all 6 drivers
  close Literal sets with evidence (iol mercado/plazo AND matriz's
    existing CFICode/MarketId/OrderType/Currency aliases)
  fix divergences in-cycle, mirrored sync/async, mocked regression tests
  cycle closure per package
                    ▼
F34  PUB-TYP-01    iol 0.2.0→0.3.0 (source-breaking, callout)
  + market-data / higyrus / matriz only if their surface changed
  double human gate (D-18)
```

**Hard dependencies:** 29c before anything else (the `from_api` contract is what every downstream phase relies on). 29h gates the *scope commitment* of 30-32 — if the exploratory run surfaces >N divergences, cut F31 or defer matriz. F30/F31 are parallelizable (different packages, only iol and market-data/higyrus respectively). F32 must come **after** F30/F31 (the gate would fail against the pre-migration surface) but its **D-16 half is independent** and can be pulled forward into F29 to widen the mypy net before the model work lands — recommended.

**Soft dependency worth respecting:** regenerate `verification/snapshots/iol-client-surface.txt` in the *same commit* as the F30 signature change, or the golden-file test (`verification/test_public_surface.py:153`) fails for anyone running the full local suite.

---

## 9. Anti-patterns to avoid

### A. Putting `strict_decoding` in `Client.__slots__`
**What people do:** `__slots__ = ("_is_view", "_max_retries", "_state", "_strict")` (`client.py:128`).
**Why it's wrong:** `with_options()` builds the view with `type(self).__new__` and copies only `_state`/`_max_retries`/`_is_view` (`client.py:325-329`) — the view would silently lose the mode. This is the exact bug `_state.py:98-105` was written to prevent for `mutating_allowed`.
**Instead:** field on `_ClientState`.

### B. Logging divergences to a child logger
**What people do:** `logging.getLogger(f"{__name__}.decode")`.
**Why it's wrong:** `logging.Filter` attached to a logger applies only to records logged **on that logger**, not to records propagating from children. `RedactingFilter` (`_logging.py:100`) is attached to `logging.getLogger("<pkg>")` — a child's records bypass it.
**Instead:** log on the package logger, distinguish with `extra={"reason": ...}`.

### C. Putting payload fragments in the log record
**Why it's wrong:** `RedactingFilter` scrubs only string values in `record.__dict__` against 4 markers (`_logging.py:47-52`) and never recurses into nested dicts.
**Instead:** model name + msgspec `field_path` + expected/observed **type names** only. Lock it with a caplog sentinel test (SEC-01 precedent).

### D. `msgspec.convert(..., strict=False)`
**Why it's wrong:** measured — `"123.5"` → `123.5` silently. That is precisely the Pydantic-lenient behaviour DT-01 rejected.
**Instead:** always `strict=True`; leniency is the *repair* branch's job and is always accompanied by a record.

### E. Assuming one strict run enumerates all divergences
**Why it's wrong:** measured — `convert` reports only the **first** error per object.
**Instead:** the observable + collector path for enumeration; strict only as the closure gate.

### F. Adding the gates to `verification/` and calling it done
**Why it's wrong:** §7.1 — that directory never executes in CI.
**Instead:** script in the `lint` job + in-package tests on the existing matrix.

### G. Re-expressing envelope unwrapping as msgspec wrapper types
**Why it's wrong:** the unwrap logic in `parse_symbols_response` / `parse_calendar_response` / higyrus's 10 envelope sites is **live-verified** output of Phases 4, 5 and 27. Rewriting it re-opens closed findings.
**Instead:** decode at the leaf (`from_api`), leave envelope code untouched.

---

## 10. Integration points

### External / dependency

| Item | Integration | Notes |
|---|---|---|
| `msgspec 0.21.1` | runtime dep of 6 wheels (or an `extra` — the plan flags this as an F29 decision) | Verified on PyPI: **48 wheels**, including `cp312`/`cp313` × `macosx_11_0_arm64`, `macosx_10_13_x86_64`, `manylinux_2_17` x86_64 + aarch64, `musllinux_1_2` x86_64 + aarch64, `win_amd64`, `win_arm64`, plus an sdist. `requires_python >=3.10`. **No free-threaded (`cp313t`) and no `cp314` wheels** — a 3.14 consumer would need a compiler. Given that coverage, an unconditional runtime dep is defensible; the `extra` + `_coerce`-fallback design would mean shipping *both* code paths permanently, which is worse than the risk it hedges. Recommend: unconditional dep, pinned `>=0.19,<1`, revisit if a 3.14 consumer appears. |

### Internal boundaries

| Boundary | Communication | Notes |
|---|---|---|
| `client.py`/`aio.py` → `_decode` | one `bind()` call per `_request` | The **only** coupling; `_decode` imports nothing from the shells, so no import-linter contract is violated |
| `_core.parse_*` → `models.from_api` | unchanged call | `_core` already imports `models` (market-data `_core.py` imports `MarketDataSnapshot` etc.) |
| `models` → `_decode` | direct import | `_decode` must import **only** stdlib + `msgspec` + `logging` to stay importable from `models` without cycles |
| `_decode` → `_logging` | none — just `logging.getLogger("<pkg>")` | `_logging.attach()` already ran at package import (`__init__.py`) |
| driver (`main_*.py`) → `verification.divergences` | `logging.Handler` attached to the package logger | Duck-typed on record fields, imports no client package — same discipline as `verification/safemodel_diff.py:49-60` |
| `tools/check_surface_types.py` → packages | **`ast` only, no import** | Keeps the lint job free of package imports and of `from __future__ import annotations` hint-resolution problems |

---

## Sources

- Repo at `adb82f5` (branch `milestone/v1.5-mutations`) — all `file:line` citations read directly.
  - `packages/iol-client/src/iol_client/{client.py,_core.py,_state.py,__init__.py}`
  - `packages/market-data-client/src/market_data_client/{client.py,_core.py,models.py,_state.py,_logging.py,_transport.py}`
  - `packages/{higyrus,matriz}-client/src/*/models.py`
  - `verification/{__init__.py,findings.py,safemodel_diff.py,test_public_surface.py}`
  - `main_iol.py`, `main_market_data.py`, `pyproject.toml`, `.github/workflows/ci.yml`, `.pre-commit-config.yaml`
  - `.planning/verification/schemas/iol-client/*.json` (live captures, 2026-06-06)
- Empirical: `msgspec 0.21.1` behaviour measured 2026-08-18 via `uv run --with msgspec --no-project` — mixin-base frozen+slots dataclass decode, `Any`-typed containers, error-path strings, first-error-only reporting, int→float widening, `Literal` enum validation, polymorphic-field rejection, `strict=False` leniency.
- PyPI JSON API for `msgspec 0.21.1` wheel/platform coverage.
- `.planning/future-plans/tipado_homogeneo.md` (DT-01..DT-09), `.planning/PROJECT.md` (v1.6 milestone block, D-16 backlog origin).

---
*Architecture research for: market-libs v1.6 — observable decoder + typed models integration*
*Researched: 2026-08-18*
