# Stack Research — v1.1 Tech Debt Cleanup

**Domain:** Python HTTP client libraries (4 packages in monorepo) — additions for retries, structured logging, sync/async dedup, and singleton→Client refactor.
**Researched:** 2026-06-10
**Confidence:** HIGH (every recommendation verified via Context7 + PyPI metadata + source inspection)
**Scope:** STACK ADDITIONS ONLY — the v1.0 stack (Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy strict, pre-commit) is NOT under review.

---

## TL;DR Decision Matrix

| Subquestion | Recommendation | Confidence | Why (one-liner) |
|-------------|----------------|------------|-----------------|
| A) Retries/backoff | **`tenacity` 9.1.4** (with no transport, used as decorator at the request layer) | HIGH | Only option that (a) gives full mutating-allowed gate control per-call, (b) shares a single decorator across sync+async, (c) has `py.typed` + mypy-strict-clean, (d) zero runtime deps |
| B) Structured logging | **stdlib `logging`** (zero deps) — adopt structured patterns via `LoggerAdapter` + `extra={...}` + `NullHandler` per package | HIGH | The only choice that ships zero new runtime deps, is breakage-proof for downstream consumers, and integrates trivially with existing `verification/redaction.py` Bearer-masking |
| C) Singleton→Client refactor | **Zero deps** — pure design pattern (`@dataclass` Client + module-level singleton instance + thin top-level functions delegating to it) | HIGH | This is a refactor, not a library problem. No idiom lib exists for this and none is needed. |
| D) Sync/async dedup | **Zero deps** — extract pure helpers (request-builders, parsers) + parametric request injection. Do NOT pull `unasync`, `anyio`, or `hishel`. | HIGH | The codebase is small (4 pkgs × ~500 LOC each), the deduplication target is endpoint-shaped logic, and the pattern is well-established. Adding a code-gen step is over-engineering. |
| E) mypy strict impact | None of the recommended adds break mypy strict | HIGH | `tenacity` ships `py.typed`; `logging` is already covered by mypy bundled stubs; design-pattern refactors don't change typing surface |

---

## Recommended Stack Additions

### Core Additions (Runtime Dependencies)

| Technology | Version | Purpose | Why Recommended | Integration Notes | Risks |
|------------|---------|---------|-----------------|-------------------|-------|
| **tenacity** | `>=9.1.0,<10` (current: 9.1.4) | Retries with exponential backoff + jitter for 5xx/429/connection errors | Decorator API works identically for sync (`@retry`) and async (`@retry` auto-detects coroutines via `AsyncRetrying`). `wait_exponential_jitter(multiplier, max, jitter)` is purpose-built for this. `retry_if_exception_type` + `retry_if_exception` give per-call gate control needed by `mutating_allowed` (no retry of mutations). Has `py.typed` marker — mypy strict compatible. Zero runtime deps. | Add as runtime dep in each of 4 package `pyproject.toml` files. Wrap `_request()` (not endpoint functions) so retry logic is centralized per package. Pass a `retry=` callable into `_request()` that the caller controls per-endpoint (mutations pass `retry=stop_after_attempt(1)`). | None significant. Apache-2.0 license. ~187 code snippets in Context7 / active community. |

### Zero-Dependency Patterns (NO new libraries)

| Concern | Approach | Why No Library | Implementation Sketch |
|---------|----------|----------------|------------------------|
| **Structured logging** | stdlib `logging` with `LoggerAdapter` + `extra=` payloads + per-package `NullHandler` default | Pulling `structlog`/`loguru` adds a runtime dep that downstream consumers must reconcile with their own logging stack. stdlib `logging` is THE library-friendly choice — consumers wire handlers/formatters. | Each package: `_logger = logging.getLogger("<pkg_name>")` at module top. Add `logging.NullHandler()` to it. Emit structured records: `_logger.info("request", extra={"method": "GET", "url": redacted_url, "duration_ms": ...})`. Wire `verification/redaction.py:_redact_bearer` into a `logging.Filter` mounted on the package logger. |
| **Singleton→Client refactor** | `@dataclass(slots=True)` `Client` class holding state + module-level `_default_client: Client \| None = None` + top-level functions delegating to `_default_client` (backward-compat compat layer) | This is a refactor pattern, not a library gap. Any "singleton pattern" lib (e.g., `singleton-decorator`) adds noise without value. | `class Client: base_url: str; token: str \| None; ...`. Top-level `def get_quote(symbol) -> dict: return _get_default_client().get_quote(symbol)`. `configure()` becomes `_default_client = Client(base_url=..., ...)`. |
| **Sync/async dedup** | Extract pure helpers (`_build_quote_request(symbol) -> Request`, `_parse_quote_response(resp) -> dict`) — sync `Client.get_quote` and `AsyncClient.get_quote` both call them, differing only in `.send()` await. | `unasync` codegen would require build-step integration with hatchling, breaking direct-from-source debugging. `anyio` would force a runtime dep into every package for a problem that's solved by good factoring. `hishel` is a caching layer, off-topic. | Per package: move request construction and response parsing into pure functions in `_request_helpers.py`. Each endpoint becomes ~5 LOC in `client.py` and ~5 LOC in `aio.py`, both calling the same helpers. Reduces the "deuda conocida" (duplicated logic across sync+async) without code-gen. |

### Development Tools — No Changes

| Tool | Status |
|------|--------|
| `ruff >=0.7` | UNCHANGED — existing rule set already covers `tenacity` usage |
| `mypy >=1.13` strict | UNCHANGED — `tenacity` ships `py.typed`, `logging` is bundled in typeshed |
| `pytest >=8.3` + `pytest-asyncio >=0.24` + `pytest-httpx >=0.34` | UNCHANGED — used as-is for regression tests on new retry/logging behavior |
| `pre-commit >=4.0` | UNCHANGED |

---

## Installation

### Per-package pyproject.toml change (apply to iol, higyrus, ambito, matriz)

```toml
# packages/<pkg>/pyproject.toml
dependencies = [
    "httpx>=0.27",
    "python-dotenv>=1.0",
    "tenacity>=9.1.0,<10",     # NEW
]
```

`matriz-client` keeps `websocket-client>=1.8.0` (out of scope for v1.1).

### No root pyproject.toml dev-dependency changes required

`tenacity` brings zero transitive deps. `logging` is stdlib.

```bash
# Apply across the workspace and lock
uv add --package iol-client "tenacity>=9.1.0,<10"
uv add --package higyrus-client "tenacity>=9.1.0,<10"
uv add --package ambito-financiero-client "tenacity>=9.1.0,<10"
uv add --package matriz-client "tenacity>=9.1.0,<10"
uv sync --all-packages --all-extras --dev
```

---

## Subquestion-by-Subquestion Rationale

### A) Retries/Backoff: Why `tenacity` (not `httpx-retries`, not `backoff`, not roll-our-own)

#### Candidates Evaluated

| Library | Version | py.typed | Sync+Async | Jitter | Per-Call Gate | Released | Verdict |
|---------|---------|----------|------------|--------|---------------|----------|---------|
| **tenacity** | 9.1.4 | YES | YES (decorator auto-detects coroutines, plus `AsyncRetrying` class) | YES (`wait_exponential_jitter`, `wait_random_exponential`) | YES (`retry=` callable per `@retry` application, can be parameterized via decorator wrapping) | Active (2024-2026) | **WINNER** |
| httpx-retries | 0.5.0 | YES | YES (single `RetryTransport` implements both base classes) | YES (`backoff_jitter` 0.0-1.0, default 1.0) | PARTIAL (transport-level: `allowed_methods` + `status_forcelist`) | 2026-04-20 (active) | Rejected — see below |
| backoff | 2.2.1 | NO | YES (decorator detects coroutines) | YES (`backoff.expo` with `factor=`) | YES (`giveup=` callable) | 2022-10 (stale) | Rejected — see below |
| Roll-our-own (httpx Transport) | n/a | n/a | requires writing both BaseTransport + AsyncBaseTransport | manual | manual | n/a | Rejected — see below |

#### Why tenacity wins

1. **`mutating_allowed` per-call gate fits decorator API perfectly.** v1.0's double-gate (hostname check + flag) for mutations is a per-call decision, not a transport-level one. Wrapping `_request()` with `@retry(retry=_should_retry(mutating))` lets the caller pass `mutating=True` to short-circuit retry, while idempotent reads retry. With `httpx-retries`, mutations would need a separate `httpx.Client` instance per call mode, multiplying client management complexity (especially given the singleton→Client refactor in scope).

2. **`wait_exponential_jitter` is the right primitive.** Google Cloud Storage retry strategy — `multiplier * 2^n + random(0, jitter)` — is the published recommendation for retrying API clients without thundering herd. tenacity ships this directly.

3. **`retry_if_exception_type(httpx.ConnectError, httpx.ReadTimeout, ...)` + `retry_if_exception` lambdas** cleanly express "retry on 5xx, 429, connection errors" by inspecting `XAPIError.status_code` from the existing exception hierarchy. No need to refactor `_raise_for_response`.

4. **Sync+async with one decorator.** `@retry(...)` on a coroutine auto-uses `AsyncRetrying`; on a sync function uses `Retrying`. After the sync/async dedup, both surfaces apply the same decorator to their respective `_request()`.

5. **`py.typed` marker confirmed** at `tenacity/py.typed` in the repo. Inline annotations throughout (verified via source inspection of `__init__.py`). mypy strict compatible.

6. **Zero runtime deps.** `pyproject.toml` lists no `requires_dist`. Optional deps for docs/tests only. Won't pollute the workspace lock.

7. **Apache-2.0 license**, MIT-compatible.

#### Why httpx-retries was rejected (despite being attractive on paper)

httpx-retries has excellent defaults (`status_forcelist = [429, 502, 503, 504]`, `backoff_jitter = 1.0`, parses `Retry-After` header) and ships `py.typed`. But three blockers:

- **Transport-level == process-level**. `allowed_methods` is a single list per Transport instance. To get "no retry on mutations" you'd need two transports per package (one mutating-safe, one not) wired to two `httpx.Client` instances. The v1.1 refactor to `Client` class makes this awkward — every `Client(...)` constructor would need both transports and a method-aware `.send()` wrapper, which is more code than the tenacity decorator approach.
- **Doesn't integrate with the existing exception hierarchy**. v1.0 already maps 5xx → `XAPIError`, 429 → `XRateLimitError`, 401/403 → `XAuthError` in `_raise_for_response()`. With tenacity, "retry on `XAPIError` if status_code >= 500 OR isinstance `XRateLimitError`" is one lambda. With httpx-retries, retries happen pre-raise — meaning the exception mapping happens AFTER retries, which is fine, but it means the retry decision can't see the typed exception.
- **One person, ~14 releases over 14 months** (first release 2023-03, latest 2026-04). Maintained but small surface. Tenacity has ~10x the community + Context7 score.

httpx-retries is a great choice for projects without an existing exception hierarchy. We have one. tenacity wins.

#### Why backoff was rejected

- **Last release 2022-10-05** (2.2.1). Effectively unmaintained.
- **No `py.typed` marker.** Would need `# type: ignore` everywhere, breaking mypy strict promise.
- **Python `>=3.7,<4.0`** constraint — already lagging current 3.13 support.
- API is nice but tenacity offers everything backoff does plus current maintenance.

#### Why roll-our-own was rejected

- Writing both `BaseTransport.handle_request` and `AsyncBaseTransport.handle_async_request` is ~150 LOC per package × 4 packages = ~600 LOC of duplicated retry plumbing. tenacity's `@retry` is ~3 LOC per call site.
- Jitter, exponential backoff, `Retry-After` honoring are all well-tested in tenacity. Rolling our own re-implements known-solved problems.

#### Suggested usage pattern (per package, inside the Client refactor)

```python
# packages/<pkg>/src/<pkg>/_retry.py
from __future__ import annotations
import httpx
from tenacity import (
    retry_if_exception, stop_after_attempt, wait_exponential_jitter,
)
from <pkg>.exceptions import XAPIError, XRateLimitError

def _is_retriable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.ConnectError | httpx.ReadTimeout | httpx.WriteTimeout):
        return True
    if isinstance(exc, XRateLimitError):
        return True
    if isinstance(exc, XAPIError) and 500 <= exc.status_code < 600:
        return True
    return False

DEFAULT_RETRY_KWARGS = dict(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=0.5, max=8.0, jitter=2.0),
    retry=retry_if_exception(_is_retriable),
    reraise=True,
)
```

```python
# Inside Client._request (sync) and AsyncClient._request (async)
from tenacity import retry, AsyncRetrying, Retrying

def _request(self, method: str, path: str, *, mutating: bool = False, ...):
    if mutating:
        # Single-attempt: respect the mutating_allowed double-gate by not retrying.
        return self._do_request(method, path, ...)
    for attempt in Retrying(**DEFAULT_RETRY_KWARGS):
        with attempt:
            return self._do_request(method, path, ...)
```

The async surface uses `AsyncRetrying` identically with `async for attempt in AsyncRetrying(...)`.

---

### B) Structured Logging: Why stdlib `logging` (not structlog, not loguru)

#### Candidates Evaluated

| Library | Version | py.typed | Library-Friendly | New Runtime Dep | Verdict |
|---------|---------|----------|------------------|-----------------|---------|
| **stdlib `logging`** | stdlib | typeshed (bundled with mypy) | YES (`NullHandler` idiom) | NO | **WINNER** |
| structlog | 26.1.0 | YES | partial — `structlog.stdlib.recreate_defaults()` integrates with stdlib but the doc warns config is application-scoped | YES | Rejected — see below |
| loguru | 0.7.3 | partial | partial — has `logger.disable("mylib")` pattern but global singleton | YES (`colorama`, `win32-setctime` on Windows) | Rejected — see below |

#### Why stdlib `logging` wins for library code

1. **THE Python library convention** is `logging.getLogger(__name__) + NullHandler()`. Every library in the PyData/HTTP stack (requests, urllib3, httpx, sqlalchemy) does this. Consumers wire handlers/formatters at app startup.

2. **Zero new runtime deps**. The v1.1 milestone explicitly forbids heavy deps. Adding `structlog` or `loguru` to 4 publishable wheels forces every downstream app to inherit them, even if it already standardized on the other choice.

3. **Structured data via `extra={...}`** works today:

   ```python
   _logger = logging.getLogger("iol_client")
   _logger.addHandler(logging.NullHandler())  # at module init, library convention
   
   _logger.info(
       "http_request_complete",
       extra={
           "method": method,
           "url": url,             # passes through redaction filter below
           "status_code": resp.status_code,
           "duration_ms": elapsed_ms,
           "attempt": attempt_n,
       },
   )
   ```

   Consumers attach a `JsonFormatter` (e.g., `python-json-logger`) at their end if they want JSON output. We don't impose that choice.

4. **Redaction integration is trivial.** Mount a `logging.Filter` on the package logger that calls the existing `verification/redaction.py:_redact_bearer` pattern on `record.msg` and stringifiable `record.args` / `extra`. ~15 LOC per package, zero new deps.

   ```python
   # packages/<pkg>/src/<pkg>/_logging.py
   from __future__ import annotations
   import logging, re
   _BEARER_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+")
   class _BearerRedactionFilter(logging.Filter):
       def filter(self, record: logging.LogRecord) -> bool:
           if isinstance(record.msg, str):
               record.msg = _BEARER_PATTERN.sub(r"\1[REDACTED]", record.msg)
           if record.args:
               record.args = tuple(_BEARER_PATTERN.sub(r"\1[REDACTED]", str(a)) for a in record.args)
           return True
   _logger = logging.getLogger(__name__.rsplit(".", 1)[0])
   _logger.addHandler(logging.NullHandler())
   _logger.addFilter(_BearerRedactionFilter())
   ```

5. **mypy strict already covered.** `logging` is in typeshed (bundled with mypy). No new typing stubs to install. `LoggerAdapter` is fully typed.

6. **Backward-compat is automatic.** Downstream code that already adds a handler to `logging.getLogger("iol_client")` works unchanged after v1.1.

#### Why structlog was rejected for the runtime path

structlog is excellent for **applications**. For **libraries**, even the structlog docs route through `structlog.stdlib.ProcessorFormatter` so the consumer can decide how to render. At that point you're paying for a dep to set up something that stdlib `logging` does natively.

Two specific blockers:
- **`structlog.configure()` is process-global.** Library code calling `structlog.configure()` would clobber a consumer's app config. The only safe pattern is "use `structlog.get_logger()` and hope the consumer configured it" — but that's identical in caller surface to `logging.getLogger()` with more dependencies.
- **Adds `structlog>=26.x` runtime dep × 4 packages.** Marginal value over stdlib `logging` for the v1.1 use case (request/response telemetry with redaction). Reserve for the consuming app if they want it.

If we were building an **app**, structlog 26.1.0 (released 2026-06-06, has `py.typed`) would be the choice. We're building libs.

#### Why loguru was rejected for the runtime path

- **Global `logger` singleton** — `from loguru import logger` mutates process-wide state. The `logger.disable("mylib")` pattern is a workaround but still couples our 4 libs to loguru's lifecycle.
- **Windows-only deps** (`colorama`, `win32-setctime`) — not a blocker (they're conditional) but adds to lock complexity for no functional gain.
- **Cannot be the receiving end of stdlib `logging` records** without an adapter (`InterceptHandler` recipe). Inverts the library-friendly direction.

#### Logging level conventions to adopt

| Level | What to log | Example |
|-------|-------------|---------|
| `DEBUG` | Request URL (post-redaction), headers (redacted), retry attempts | `"http_request_start"`, `"retry_attempt"` |
| `INFO` | Successful request completion with duration + status | `"http_request_complete"` |
| `WARNING` | Retry triggered, token refresh, non-fatal API errors | `"retry_triggered"`, `"token_refreshed"` |
| `ERROR` | Auth failure, exhausted retries, 5xx returning to caller | `"auth_failed"`, `"retry_exhausted"` |

---

### C) Singleton→Client Refactor: Zero New Deps

This is **pure design pattern work**. Confirmed: no Python idiom library is worth pulling.

#### Recommended pattern

```python
# packages/<pkg>/src/<pkg>/client.py (sync)
from __future__ import annotations
from dataclasses import dataclass, field
import httpx, logging, time

@dataclass(slots=True)
class Client:
    base_url: str
    username: str = ""
    password: str = ""
    _http: httpx.Client = field(default_factory=lambda: httpx.Client(timeout=30.0))
    _token: str | None = None
    _token_ts: float = 0.0
    
    def login(self) -> None: ...
    def _ensure_token(self) -> None: ...
    def _request(self, method: str, path: str, *, mutating: bool = False, **kw) -> httpx.Response: ...
    def get_quote(self, symbol: str) -> dict[str, Any]: ...
    def close(self) -> None: self._http.close()
    def __enter__(self) -> Client: return self
    def __exit__(self, *exc) -> None: self.close()


# --- Backward-compat module-level singleton + top-level functions ---
_default: Client | None = None

def _get_default() -> Client:
    global _default
    if _default is None:
        _default = Client(
            base_url=os.getenv("X_BASE_URL", "https://..."),
            username=os.getenv("X_USER", ""),
            password=os.getenv("X_PASS", ""),
        )
    return _default

def configure(*, base_url: str | None = None, username: str | None = None,
              password: str | None = None) -> None:
    global _default
    # Build a fresh Client so token cache is reset (same semantics as v1.0).
    _default = Client(
        base_url=base_url or os.getenv("X_BASE_URL", "..."),
        username=username or os.getenv("X_USER", ""),
        password=password or os.getenv("X_PASS", ""),
    )

def login() -> None: _get_default().login()
def get_quote(symbol: str) -> dict[str, Any]: return _get_default().get_quote(symbol)
# ... one thin delegator per public function
```

This preserves the v1.0 top-level API verbatim (`iol_client.get_quote("GGAL")` still works), satisfies the no-breaking-change constraint for v1.1 minor bump, and unlocks `Client(...)` instances for callers who want per-instance state (tests, multi-tenant).

#### What was considered and rejected

- **`singleton-decorator`** / similar libraries — solve a problem we don't have (we WANT module-level singleton + Client both)
- **`dependency-injector`** — overkill for a 4-package lib monorepo, adds heavy runtime dep
- **`pydantic` for the Client dataclass** — would force runtime dep + add validation overhead we don't need; `@dataclass(slots=True)` is enough

---

### D) Sync/Async Dedup: Zero New Deps (Pure Extract-Helpers)

The deduplication problem in v1.0 is: each endpoint exists twice — once in `client.py`, once in `aio.py` — with identical request-building and response-parsing logic but differing only at `httpx.Client.send()` vs `await httpx.AsyncClient.send()`.

#### Recommended pattern: extract pure functions

```python
# packages/<pkg>/src/<pkg>/_endpoints.py  (NEW — pure functions, no I/O)
from __future__ import annotations
import httpx
from <pkg>.models import Quote

def build_get_quote(base_url: str, symbol: str, *, plazo: str = "t2") -> httpx.Request:
    return httpx.Request("GET", f"{base_url}/quotes/{symbol}", params={"plazo": plazo})

def parse_quote_response(resp: httpx.Response) -> Quote:
    return Quote.from_api(resp.json())
```

```python
# Sync endpoint in client.py becomes:
def get_quote(self, symbol: str, *, plazo: str = "t2") -> Quote:
    self._ensure_token()
    req = _endpoints.build_get_quote(self.base_url, symbol, plazo=plazo)
    req.headers["Authorization"] = f"Bearer {self._token}"
    resp = self._http.send(req)
    _raise_for_response(resp)
    return _endpoints.parse_quote_response(resp)

# Async endpoint in aio.py becomes:
async def get_quote(self, symbol: str, *, plazo: str = "t2") -> Quote:
    await self._ensure_token()
    req = _endpoints.build_get_quote(self.base_url, symbol, plazo=plazo)
    req.headers["Authorization"] = f"Bearer {self._token}"
    resp = await self._http.send(req)
    _raise_for_response(resp)
    return _endpoints.parse_quote_response(resp)
```

The dedup target — params building, URL composition, response model construction — moves into pure helpers. The thin layer that differs (await vs sync) stays in two places, but is ~3 lines per endpoint instead of ~15. Acceptable duplication for the "no shared internals across packages" constraint.

#### What was considered and rejected

| Library/Tool | Version | Why Rejected |
|--------------|---------|--------------|
| **unasync** | 0.6.0 (2024-05) | Code-gen tool: write async, transform to sync at build time. Used by elasticsearch-py and httpx itself. **Rejected** because: (a) requires hatchling integration to run the transform pre-build, complicating CI; (b) sync code becomes derived/non-debuggable as the primary surface; (c) the v1.0 codebase already has both surfaces hand-written — the win is small; (d) adds setuptools + tokenize-rt to dev deps. |
| **anyio** | n/a | Abstraction over asyncio/trio — would let async code call sync code via thread pool. Off-topic: we don't want sync code in async paths (blocks event loop) or vice versa. Adds runtime dep × 4 packages for no payoff. |
| **hishel** | n/a | HTTP caching layer for httpx. Different problem entirely (caching ≠ dedup). |
| **httpx itself** | n/a | The recommended pattern (extract `httpx.Request` builders + response parsers, dispatch differs sync/async) IS the httpx-native idiom — no new lib needed. |

For matriz-client specifically, this dedup work is BLOCKED on the prerequisite "create `aio.py` for matriz" (which itself depends on the Client refactor). Sequencing: Client refactor → matriz `aio.py` skeleton (mirrors `client.py` 1:1) → extract `_endpoints.py` → sync+async converge on helpers.

---

### E) Type-Checking Impact on mypy Strict Mode

| Addition | mypy Strict Impact | Mitigation Needed |
|----------|--------------------|--------------------|
| **tenacity 9.1.4** | None — ships `py.typed` marker (verified in source). Inline `t.Callable[..., WrappedFnReturnT]`-style annotations throughout `__init__.py`. | None. May need `# type: ignore[misc]` once on `@retry(...)` if the decorator's return-type narrowing trips on `disallow_untyped_defs` for a particular call site — but this is rare. |
| **stdlib `logging`** | None — fully typed in typeshed (bundled with mypy >=1.13). `LoggerAdapter`, `Filter`, `Handler` all have complete stubs. | None. |
| **Client refactor (`@dataclass`)** | None — `dataclasses` is fully typed. `slots=True` requires Python 3.10+ which we have. | None. |
| **`_endpoints.py` pure helpers** | None — pure typed functions over `httpx.Request` / `httpx.Response`, both fully typed by httpx 0.27+. | None. |

**No new type stub packages required.** No changes to `[tool.mypy]` config needed.

---

## Alternatives Considered (Summary)

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `tenacity` decorator at `_request()` | `httpx-retries` transport | Greenfield project without an existing exception hierarchy, where transport-level method allowlist is sufficient |
| stdlib `logging` + `NullHandler` | `structlog` 26.x | Building an **app** (not a library) where the entire log pipeline is yours and you want first-class JSON/console output and contextvars |
| `@dataclass` `Client` + module singleton compat layer | `pydantic.BaseModel` Client | If you need runtime validation of init params or JSON serialization of the Client config — neither is needed here |
| Extract pure helpers in `_endpoints.py` | `unasync` codegen | Large async-first codebase (10k+ LOC) where maintaining two surfaces by hand has measurable cost — not our case |

---

## What NOT to Add (Explicit Veto List)

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **`backoff` (litl/backoff)** | No `py.typed` marker → breaks mypy strict promise. Last release 2022-10 (unmaintained). `requires-python = ">=3.7,<4.0"` already trailing. | `tenacity` |
| **`urllib3` (direct)** | Adding urllib3 alongside httpx means two HTTP stacks in lockfile. urllib3's `Retry` API is what httpx-retries wraps; if we wanted urllib3 semantics we'd use httpx-retries. | `tenacity` |
| **`requests`** | We're an httpx-only shop. requests is sync-only, no async path. | n/a |
| **`structlog`** for the libraries | Adds runtime dep × 4 packages. Library code shouldn't `structlog.configure()` (process-global). | stdlib `logging` |
| **`loguru`** for the libraries | Global singleton `logger` couples downstream consumers. Windows-only sub-deps. | stdlib `logging` |
| **`unasync`** | Build-step complexity for a 4-package, modest-size monorepo. The win (single source) doesn't justify the codegen pipeline. | Hand-written sync+async sharing pure helpers in `_endpoints.py` |
| **`anyio`** as a dep | We're committed to asyncio, not trio. No need for the abstraction layer at the package level. | Direct `asyncio` (already what `aio.py` uses) |
| **`hishel`** | HTTP caching — solves a different problem. Live verification specifically wants to NOT cache (we want to see real responses). | n/a |
| **`pydantic`** for Client config | Runtime validation overhead for init-time-only data; would force pydantic dep × 4 packages. | `@dataclass(slots=True)` |
| **`asgiref`** | Server-side async/sync bridging — not applicable to client libraries. | n/a |
| **`tenacity` extension libs** (e.g., `tenacity-aiohttp`) | We're httpx, not aiohttp. Stock tenacity is sufficient. | Stock `tenacity` |

---

## Stack Patterns by Variant

**If a single package needs custom retry semantics (e.g., matriz Primary API has different rate limits):**
- Override `DEFAULT_RETRY_KWARGS` per package in its own `_retry.py` (already isolated by the no-shared-internals constraint)
- e.g., matriz could use `stop_after_attempt(5)` instead of `3` if Primary API justifies it

**If we later want JSON-formatted log output:**
- Application-side: consumers wire `python-json-logger` (or `structlog.stdlib.ProcessorFormatter`) on the package logger
- We do NOT impose this; the lib emits structured records via `extra=` and lets the app format

**If a consumer wants per-instance retry tuning:**
- Client refactor exposes `Client(retry_kwargs={...})` — top-level `configure()` accepts the same; default keeps v1.0 behavior

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `tenacity 9.1.4` | `httpx >=0.27` | No shared deps. tenacity wraps sync/async callables, doesn't know about httpx. |
| `tenacity 9.1.4` | `python >=3.10` | Project requires `>=3.12`, well within tenacity's window. |
| `tenacity 9.1.4` | `mypy 1.13` strict | Has `py.typed`; verified inline annotations. |
| `stdlib logging` | typeshed (mypy 1.13 bundled) | Full type stubs ship with mypy. |
| `stdlib logging` | `verification/redaction.py` | Wire `_redact_bearer` into a `logging.Filter` on the package logger. No code dep changes in `verification/`. |
| `@dataclass(slots=True)` | Python `>=3.10` | We have `>=3.12`. |
| `tenacity` + `pytest-httpx` | OK | pytest-httpx mocks at the httpx transport level; tenacity wraps at the call-site level. No conflict — retry decorators will see mocked responses normally. Regression tests for retry behavior just need to set up multiple `mock.add_response()` calls for the same URL. |

---

## Integration Risk Audit (v1.1 Constraint Check)

| Constraint | Status with Recommended Stack |
|------------|-------------------------------|
| Cannot break CI (ruff + mypy strict + 277 pytest tests) | ✓ `tenacity` is `py.typed`; stdlib `logging` covered by typeshed; no ruff rule conflicts (verified via rule set list) |
| Cannot break public API on minor bump | ✓ Top-level functions preserved via compat layer; `Client` class is additive; logging emits to a logger that's silent by default (`NullHandler`) |
| Cannot introduce shared internals between packages | ✓ All recommendations apply 4× independently. Each package gets its own `_retry.py` + `_logging.py` + `_endpoints.py`. No new shared module under `verification/` (which is harness, not lib code). |
| Cannot pull heavy deps with C extensions or wide trees | ✓ `tenacity` is pure-Python, zero runtime deps. No other lib additions. |
| Must work on Python 3.13 too | ✓ tenacity 9.1.4 is tested on 3.13 (per PyPI classifiers); httpx-retries 0.5.0 also classifies 3.13/3.14 (for reference even though rejected) |
| CI matrix unchanged | ✓ No new CI steps. Existing `uv sync --all-packages --all-extras --dev --frozen` covers it. |

---

## Sources

### Context7 (HIGH confidence — authoritative library docs)

- `/jd/tenacity` — Retrying library for Python (187 snippets, score 82.1). Fetched: `wait_exponential_jitter`, `AsyncRetrying`, `retry_if_exception`, decorator auto-detection for coroutines.
- `/websites/tenacity_readthedocs_io_en` — Tenacity readthedocs mirror (45 snippets, score 86.7). Cross-verified API.
- `/will-ockmore/httpx-retries` — HTTPX Retries transport (55 snippets). Fetched: `RetryTransport` sync+async, `Retry(total, backoff_factor, backoff_jitter)`, default `allowed_methods` (HEAD/GET/PUT/DELETE/OPTIONS/TRACE — note: PUT/DELETE included by default), default `status_forcelist=[429, 502, 503, 504]`, `respect_retry_after_header`.
- `/hynek/structlog` — Structlog (192 snippets, score 86.6). Fetched: `ProcessorFormatter` for stdlib integration, library-vs-application configuration warning.
- `/websites/structlog_en_stable` — Structlog stable docs (1331 snippets, score 93). Cross-verified.
- `/delgan/loguru` — Loguru (506 snippets, score 89.4). Fetched: `logger.disable("mylib")` library pattern, configure recipe.
- `/litl/backoff` — Backoff (20 snippets, score 91). Fetched: `@backoff.on_exception(backoff.expo)`, `giveup` keyword.

### Official sources / PyPI (HIGH confidence)

- https://pypi.org/pypi/tenacity/json — version 9.1.4, no runtime deps, requires-python `>=3.10`, Apache-2.0
- https://pypi.org/pypi/structlog/json — version 26.1.0 (2026-06-06), `Typing :: Typed`, requires-python `>=3.10`
- https://pypi.org/pypi/httpx-retries/json — version 0.5.0 (2026-04-20), requires `httpx>=0.20.0`, requires-python `>=3.10`
- https://pypi.org/pypi/backoff/json — version 2.2.1 (2022-10-05, **stale**), requires-python `>=3.7,<4.0`
- https://pypi.org/pypi/loguru/json — version 0.7.3 (2024-12-06), Windows conditional deps
- https://pypi.org/pypi/unasync/json — version 0.6.0 (2024-05-03), deps `tokenize-rt`, `setuptools`
- https://api.github.com/repos/will-ockmore/httpx-retries/releases — verified active maintenance, latest 0.5.0 published 2026-04-20

### Source inspection (HIGH confidence)

- https://github.com/jd/tenacity/tree/main/tenacity — confirmed `py.typed` file present (PEP 561 compliant)
- https://github.com/hynek/structlog/tree/main/src/structlog — confirmed `py.typed` present
- https://github.com/will-ockmore/httpx-retries/tree/main/httpx_retries — confirmed `py.typed` present; `transport.py` implements both `httpx.BaseTransport` and `httpx.AsyncBaseTransport`; `retry.py` uses `asyncio.sleep` (asyncio-native, not anyio)
- https://will-ockmore.github.io/httpx-retries/behaviour/ — confirmed `Retry-After` header honored by default

### Existing codebase context (HIGH confidence — read directly)

- `/Users/sebadlf/development/becerra/market-libs/.planning/PROJECT.md` — v1.1 milestone goals, constraints
- `/Users/sebadlf/development/becerra/market-libs/.planning/codebase/STACK.md` — v1.0 baseline stack
- `/Users/sebadlf/development/becerra/market-libs/.planning/codebase/ARCHITECTURE.md` — singleton pattern, dual sync/async surface
- `/Users/sebadlf/development/becerra/market-libs/.planning/codebase/CONVENTIONS.md` — `from __future__ import annotations`, ruff rule set, mypy strict expectations
- `/Users/sebadlf/development/becerra/market-libs/pyproject.toml` — workspace config, dev deps
- `/Users/sebadlf/development/becerra/market-libs/packages/iol-client/pyproject.toml` — package-level dep declaration pattern

---

*Stack research for: market-libs v1.1 Tech Debt Cleanup additions*
*Researched: 2026-06-10*
*Confidence: HIGH — all picks verified via Context7 + source inspection; alternatives explicitly evaluated and rejected with reasons*
