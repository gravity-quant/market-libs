# Feature Research — v1.1 Tech Debt Cleanup

**Domain:** Python HTTP client libraries (financial APIs) — refactor + retries + logging + driver-harness fixes
**Researched:** 2026-06-10
**Confidence:** HIGH (cross-referenced httpx official docs, anthropic SDK, openai SDK, stripe SDK, Python stdlib logging HOWTO, RFC 9110, AWS Architecture Blog on jitter)
**Scope note:** This document covers ONLY the v1.1 NEW features. v1.0 already-built capabilities (auth, exception hierarchy, SafeModel, `configure()`, dual sync/async, verification harness) are out of scope and not re-researched.

---

## Executive Summary — What This Research Establishes

The five v1.1 refactor axes (A. Client class, B. sync/async parity, C. retries+backoff, D. structured logging, E. findings append-only) all have well-established convention sets in the modern Python HTTP-client ecosystem. The findings below cite **anthropic-sdk-python**, **openai-python**, **stripe-python**, **httpx** (the underlying transport already used), and stdlib Python `logging` as reference behaviors. The recommendations in each table are not speculation — they're the table stakes that callers of every modern Python SDK expect.

The single most important shape: **a `Client` class per package whose public methods mirror today's top-level functions, plus a lazy `DEFAULT_CLIENT` instance backing thin top-level convenience functions that call `DEFAULT_CLIENT.<method>(...)`**. This is the pattern OpenAI shipped in v1.0 and Anthropic mirrors; it's the canonical "instance API + module-level convenience" answer.

The single most important pitfall to bake in: **never auto-retry POST/mutation without an idempotency signal**. In v1.1 this means honoring the existing v1.0 `mutating_allowed` double-gate as a non-retryable axis by default, and only retrying methods that are idempotent per RFC 9110 (GET/HEAD/PUT/DELETE) or that carry an explicit Idempotency-Key.

---

## Axis A — Client Class API Surface

**Question:** What methods does a well-designed Client class expose? What state lives in the instance vs. module-level? What's the convention for "default global instance" used by top-level convenience functions?

### A.1 Table Stakes

| Feature | Why Expected | Complexity | Notes / Reference |
|---------|--------------|------------|-------------------|
| `Client(*, base_url=None, username=None, password=None, timeout=..., max_retries=...)` constructor | Every modern SDK exposes a class with kwargs for credentials + transport tuning (anthropic `Anthropic(api_key=..., max_retries=...)`, openai `OpenAI(api_key=..., timeout=..., max_retries=...)`, stripe `StripeClient(api_key, max_network_retries=...)`) | S | All kwargs keyword-only; instance owns its own `httpx.Client`. Dependency: v1.0 `configure()` signature already establishes the kwarg names — reuse them verbatim for non-breaking parity. |
| `client.close()` (sync) / `await client.aclose()` (async) | httpx requires explicit close to release the connection pool; every wrapper SDK exposes the same name (anthropic `close()`, openai `close()`, httpx `aclose()`). | S | Idempotent — second call is a no-op. Closes the underlying `httpx.Client`, clears the cached `_token`. |
| Sync context manager: `with Client(...) as c:` (`__enter__` / `__exit__`) | Standard Python resource-management protocol; httpx documents it as the recommended use ("recommended way to use a Client is as a context manager"). | S | `__enter__` returns `self`; `__exit__` calls `close()`. Calling code uses `with Client() as c: c.get_quote(...)`. |
| Async context manager: `async with Client(...) as c:` (`__aenter__` / `__aexit__`) | Same as above for the async surface; mandatory for safe pool cleanup across event loops (today's v1.0 bug class — `aio.py` state pinned to one loop). | S | `__aenter__` returns `self`; `__aexit__` calls `aclose()`. |
| Instance-scoped state (no module globals leak in) | The whole point of the refactor; each `Client` instance owns its own `_base_url`, `_token`, `_token_ts`, `_http`. Two instances must not share state. | M | Anthropic SDK pattern: `self._client = httpx.Client(...)`. Multi-account use case (HIGY-multi-account fix) literally requires this. |
| Top-level convenience functions remain importable (non-breaking compat layer) | Existing callers do `import iol_client; iol_client.get_quote("GGAL")`. v1.1 must not break that. | M | Mirrors openai-python v1.0 migration: `openai.chat.completions.create(...)` lazily instantiates a module-private `_ModuleClient` from env on first use. Same pattern here: `iol_client.get_quote(...)` → `_get_default_client().get_quote(...)`. |
| Lazy default-client backing convenience funcs | OpenAI's pattern: top-level helpers create the default client on first use, reading env vars at that moment. Avoids import-time side effects beyond `load_dotenv()`. | S | Module-level `_default_client: Client \| None = None`; helper `_get_default_client()` instantiates on demand and caches. `configure(...)` mutates the lazy default (back-compat). |
| `configure(...)` continues to work and resets the default-client's token | v1.0 callers and tests rely on it. Preserve signature: `configure(*, base_url=None, username=None, password=None)`. | S | Implementation: `configure()` recreates the default `Client` instance (or mutates it) and clears its token. Test fixtures (every package's `conftest.py`) keep working unchanged. |
| Method names == today's function names | Zero cognitive shift for callers. `get_quote` stays `client.get_quote`. Anthropic ships `client.messages.create`; openai ships `client.chat.completions.create`; we ship `client.get_quote`. | S | No naming opportunity-cost: don't rename existing endpoints "while we're refactoring" — that's a separate change with separate review cost. |

### A.2 Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `client.with_options(...)` per-request overrides | Anthropic and OpenAI ship this: `client.with_options(max_retries=5).messages.create(...)`. Lets callers tweak timeout/retries for one call without mutating the long-lived client. | M | Returns a shallow-copy `Client` sharing the same `httpx.Client` / token but with overridden options. Useful for matriz one-off mutating calls that want `max_retries=0`. Marker: P2 — value-add but not table stakes. |
| `Client.from_env()` classmethod | Explicit, discoverable alternative to "magic" env-reading constructor. anthropic-sdk-python and many SDKs expose this. | S | Calling `Client.from_env()` reads `IOL_USER`/`IOL_PASSWORD`/`IOL_BASE_URL`. The plain `Client()` constructor would also fall back to env, so `from_env()` is mainly documentation. |
| Pluggable `http_client` injection | `Client(http_client=httpx.Client(transport=mock))` lets tests inject a mock or proxy without monkeypatching. openai/anthropic both accept this. | M | Already partially possible today (the harness uses `pytest-httpx`); a formal kwarg makes the injection point explicit and removes the need for monkeypatching `_client`. |

### A.3 Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Inheritance hierarchy `BaseClient` shared across packages | "DRY across the 4 packages" | Project's existing architectural constraint (CLAUDE.md: "Sin código compartido entre paquetes (por diseño)"); each package is a standalone wheel. Inter-package coupling would break the publish-each-package-independently invariant. | Duplicate the `Client` skeleton per package. Lift truly identical helpers into a private `_base.py` **within each package** only. |
| Class methods that mutate global module state | Mixed instance+module state = the worst of both worlds; bugs like HIGY multi-account come from exactly this. | Defeats the purpose of the refactor. | Instance owns its state. Module-level convenience funcs delegate to `_default_client`. |
| Renaming existing methods "to follow newer conventions" | Refactor scope creep. | Breaking change for callers; unrelated to tech-debt cleanup. | Keep names. Renames are a separate dedicated proposal. |
| `client.async_get_quote(...)` (async methods on the same class) | Looks compact ("one client for everything"). | Confuses sync/async semantics, breaks mypy, and contradicts the established `pkg.aio.Client` mirror pattern (anthropic ships `AsyncAnthropic`; openai ships `AsyncOpenAI`). | Separate `Client` (sync) in `client.py` and `AsyncClient` in `aio.py`. Same method names on both. |
| Auto-`__del__` cleanup | "User forgot to close, do it for them" | `__del__` ordering at interpreter shutdown is famously unreliable; httpx itself recommends explicit `close()` / context manager. | Document context-manager pattern; ship `close()`/`aclose()`. |

**Dependencies on v1.0:** `configure()` signature (Architecture L160-172), env-var names (INTEGRATIONS), `_token`/`_token_ts` semantics (Architecture L152-156). The compat layer **must** preserve all three exactly.

---

## Axis B — Sync/Async Parity

**Question:** When a lib offers both sync and async, what's the expected API symmetry? What's the user expectation about being able to use both from the same process? About independent state vs shared cache?

### B.1 Table Stakes

| Feature | Why Expected | Complexity | Notes / Reference |
|---------|--------------|------------|-------------------|
| Identical method names sync vs. async | Anthropic ships `Anthropic` and `AsyncAnthropic` with exact-mirror method names. OpenAI ships `OpenAI` and `AsyncOpenAI` likewise. Today's v1.0 already does this (function names match). Carry forward. | S | `client.get_quote("GGAL")` (sync) ↔ `await aclient.get_quote("GGAL")` (async). No `async_` or `a_` prefix. |
| Identical kwargs and return types | Mypy and IDE expectations: a typed user writing async code shouldn't have to look up a different signature. | S | Same dataclasses, same Literals, same exception types. Today's v1.0 honors this; v1.1 keeps honoring it post-dedup. |
| Independent state per surface (sync `_default_client` and async `_default_client` don't share) | Sync and async clients use different httpx instances (`httpx.Client` vs `httpx.AsyncClient`) — these are not interchangeable. | S | Already true in v1.0 (separate `client.py` and `aio.py` modules). Carry forward; don't merge state. |
| Both surfaces work from same process | Many callers will use the sync surface in REPL/scripts and async in production. They must coexist. | S | Today: works because they're independent modules. Carry forward. |
| Logic dedup: shared internal helpers, NOT shared external state | The deduplication target. Per-package internal `_core.py` (or `_internal.py`) that holds the URL-building, header-construction, response-parsing, error-mapping — both `client.py` and `aio.py` call those helpers. State and the actual `httpx.*` instance stay separate. | M | Reference: this is exactly the pattern OpenAI/Anthropic use internally — generated code shares logic, sync/async stubs differ only in await placement. |
| `aio.py` for matriz-client (parity with iol/higyrus/ambito/wallets) | Today matriz has no `aio.py`; v1.0 even documents the "no async support in matriz" anti-pattern. v1.1 closes the gap for the REST surface. | L | Must mirror the sync REST API exactly. WebSocket (`ws_client.py`) stays out of scope per PROJECT.md (defer v1.2). |
| Independent token cache per surface (sync token ≠ async token) | Today's behavior. A sync `login()` and an async `await aio.login()` produce separate cached tokens. Don't try to share — they're bound to different httpx clients anyway. | S | Tests already rely on this (`conftest.py` fixtures separate). |

### B.2 Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Generated-code parity guarantee (one source, two emit paths) | Anthropic/OpenAI use Stainless to generate both surfaces from one OpenAPI spec; impossible parity drift. | XL | OUT OF SCOPE for v1.1. Achieving this for hand-written market-libs would require building a code generator. Document as v2 consideration; don't attempt now. |
| Async `Client` accepts shared `httpx.AsyncClient` | When the caller's app already has a global AsyncClient (FastAPI lifespan pattern), letting them inject it avoids double pool. | M | Same hook as Axis A.2 ("Pluggable http_client injection"). Worth doing once, applies to both surfaces. |

### B.3 Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| `nest_asyncio` to call async from sync | "Convenience" | Hides event-loop bugs, breaks in production, performance trap. The CLAUDE.md anti-pattern "Importing aio module in sync context" already documents this. | Sync callers use sync `Client`. If they need async, use `asyncio.run(...)`. |
| `asyncio.to_thread(sync_func)` wrappers in `aio.py` | "Cheap way to add matriz aio.py" | Doesn't get any async benefit; ties up threadpool slots; mocks behave differently. | Write a real native-async `aio.py` for matriz with `httpx.AsyncClient`. This is the L-complexity item. |
| Shared `httpx` instance across sync and async | "Save resources" | `httpx.Client` and `httpx.AsyncClient` have different APIs and lifecycle constraints. | Two separate instances; that's the point. |
| Reusing `aio` `_client` across event loops | Already documented as v1.0 anti-pattern (Architecture L213-217). v1.1 refactor must not silently lift this constraint. | Causes "AsyncClient bound to different loop" errors. | Per-instance `Client` means callers create one per loop; `aclose()` in teardown remains required. |

**Dependencies on v1.0:** `aio.py` event-loop binding semantics (Architecture L213-217), test fixture pattern (`aclose()` in teardown), shared types pattern (`iol_client.aio` importing `InstrumentType` from `iol_client.client` — Architecture L195).

---

## Axis C — Retries / Backoff Behavior

**Question:** Which status codes? Retry vs raise? Idempotency for POST? Jitter type? Retry-After?

### C.1 Table Stakes

| Feature | Why Expected | Complexity | Notes / Reference |
|---------|--------------|------------|-------------------|
| Retry on 429 + 5xx (specifically 408, 409, 425, 429, 500, 502, 503, 504) | Anthropic SDK default: 408, 409, 429, ≥500 (2 retries). OpenAI SDK same: 408, 409, 429, ≥500. Stripe same family. This is the consensus list. | S | The user's question mentioned 429/502/503/504; the modern list is broader. Confirmed. |
| Retry on connection errors (`httpx.ConnectError`, `httpx.ConnectTimeout`, `httpx.ReadError` at request-start) | Anthropic/OpenAI both retry connection-level transient failures. httpx's built-in `HTTPTransport(retries=N)` only handles `ConnectError`/`ConnectTimeout` — broader coverage requires a wrapper. | S | The package's retry layer wraps `_request()`, not the httpx transport. |
| Default max attempts = 2 retries (i.e. 3 total attempts) | Anthropic default. OpenAI default. Stripe default `max_network_retries=0` (must opt-in), but 2 retries is the de-facto consensus among AI SDKs. | S | Configurable via `Client(max_retries=2)` and `client.with_options(max_retries=...)`. |
| **Honor `Retry-After` header on 429** | MDN: "Always check for Retry-After first when handling a 429. It's the most reliable signal from the server." All major SDKs (anthropic, openai, stripe) honor it. | S | Accept both formats per RFC: integer seconds OR HTTP-date (IMF-fixdate). Cap honored Retry-After at a sane max (e.g. 60s) to prevent server-induced deadlocks — see Anthropic SDK issue cited where `Retry-After: 120` caused agent deadlocks. |
| **Idempotency by method** (default) — only retry idempotent methods | Per RFC 9110: GET, HEAD, OPTIONS, PUT, DELETE are idempotent. POST and PATCH are NOT. urllib3 default `allowed_methods` follows this exact list. | S | Critical for matriz-client (`newSingleOrder`, `cancelById`, `replaceById` are POSTs that mutate). Default: do not retry POST/PATCH unless idempotency-keyed. |
| **Honor v1.0 `mutating_allowed` double-gate as non-retryable axis** | Existing harness contract: any operation gated by `mutating_allowed` is a financial-state mutation. PROJECT.md explicitly says: "retries/backoff transparente con jitter ... respeta el `mutating_allowed` double-gate (no retry de mutaciones)". | S | Implementation: the retry decision considers (method, mutating_allowed). If method is POST/PATCH OR mutating_allowed is true, retry attempts = 0 unless explicit Idempotency-Key kwarg is passed. |
| Exponential backoff with **full jitter** | AWS Architecture Blog: "For most services, full jitter is the right default. It is the simplest to reason about and gives the best server-side behaviour." Anthropic SDK uses exponential backoff with jitter. OpenAI same. | S | Formula: `sleep = random.uniform(0, min(cap, base * 2 ** attempt))`. Base ~0.5s, cap ~60s. |
| Per-request timeout, separate from total retry budget | httpx timeout is per attempt. The OpenAI SDK explicitly documents: "Remember that timeout is per-request attempt; a request with 2 retries could take up to 3 * timeout plus backoff time." | S | Already true since httpx is the transport. Just document it. |
| Surface terminal failure as the same typed exception today | A retried-then-final 429 raises `RateLimitError` (existing type). 5xx-then-final raises `APIError`. Connection error final raises a transport error. | S | Reuses existing v1.0 exception hierarchy without expansion. |
| Configurable per-Client and per-call | `Client(max_retries=N)` for the long-lived config; `client.with_options(max_retries=M)` for one call. Standard SDK shape (anthropic, openai both expose this). | M | Per-call override = Axis A.2 differentiator. |

### C.2 Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Caller-supplied `Idempotency-Key` header for explicit POST retry opt-in | Stripe Python's pattern: "Idempotency keys are automatically generated and added to requests, when not given, to guarantee that retries are safe." | M | For market-libs the financial-mutation use case is too rare and the gate is operator-driven (`mutating_allowed`); auto-generating Idempotency-Keys here would conflict with the existing harness gate. P3 — defer. |
| Logging at WARN on each retry attempt with attempt/elapsed/status | OpenAI feature request explicitly asks for this. Anthropic SDK ships it. | S | Naturally lives in Axis D (logging). Cross-cut: each retry emits `WARN` log with `{attempt, status_code, retry_after, sleep_seconds}`. |
| Total elapsed-time cap (in addition to max attempts) | Belt-and-suspenders against a long Retry-After chain. Not standard in anthropic/openai but useful when called from CI. | M | Optional kwarg `max_elapsed_seconds`. P2. |
| Decorrelated jitter | Per Thom Wright critique: full jitter can collapse to near-zero waits under sustained throttling; decorrelated is more conservative. | M | AWS Blog: "decorrelated jitter is worth picking when you care more about latency variance than peak server load." Live-API verification cycle prefers stability → could argue for it. **Recommend**: ship full jitter as v1.1 default (simplest, AWS-recommended), document decorrelated as future option. |

### C.3 Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-retry POST/PATCH by default | "Just make the network resilient" | Causes duplicate orders on matriz (`newSingleOrder`), duplicate operations on higyrus. The exact failure mode RFC 9110 warns about. PROJECT.md explicitly forbids it. | Default: no retry on non-idempotent methods. Operator opts in per-call. |
| Retry on 400/401/403/404 | "More resilience" | These are caller errors. Retrying re-sends a bad request. Anthropic SDK explicitly does NOT retry these. | Map to typed exception immediately (existing `_raise_for_response` behavior). |
| Infinite retry loop ("until success") | Looks robust | Cascading failure; agents deadlock under sustained 429 (see hermes-agent issue cited). | Hard cap on attempts (default 2) AND hard cap on elapsed time. |
| Retry inside `_ensure_token()` token refresh | "Resilient auth" | Doubles up with the request-level retry; can cause 4x the load on the auth endpoint. | Token refresh has its own single-shot path; the request-level retry handles 401-after-refresh by allowing one re-login per request, not by retrying the request itself. |
| Per-package custom retry library (tenacity, backoff, stamina) | "Best-of-breed" | Adds a runtime dep to every package; the constraint is each package is a standalone wheel. The retry logic is ~50 LOC; write it inline. | Hand-rolled in `_retry.py` per package (same dedup pattern as `_params.py`). Zero new deps. |
| Honoring an unbounded `Retry-After` value (e.g. 86400) | "Trust the server" | Locks up the calling process. The Anthropic hermes-agent issue is precisely this footgun. | Cap honored Retry-After at the configured backoff cap (e.g. 60s default). |

**Dependencies on v1.0:** existing exception types (`<Pkg>RateLimitError`, `<Pkg>APIError`), `_raise_for_response` mapping (CONVENTIONS L84-93), `verification/mutation_gate.py` (the `mutating_allowed` flag). The retry layer **must** check the mutation_gate state before retrying any POST/PATCH against `*.primary.com.ar` or any other mutation-capable host.

---

## Axis D — Structured Logging

**Question:** What's the expected default? What events at which level? Structured fields? Credential redaction?

### D.1 Table Stakes

| Feature | Why Expected | Complexity | Notes / Reference |
|---------|--------------|------------|-------------------|
| Per-package logger named `logging.getLogger("<pkg>")` | Python stdlib HOWTO: "create a module level logger with `getLogger(__name__)`". Hierarchical naming so callers can configure `iol_client.*` independently. | S | Each `client.py` and `aio.py`: `logger = logging.getLogger(__name__)`. Each `__init__.py` adds NullHandler. |
| **NullHandler attached in `__init__.py`** | Python stdlib HOWTO: "strongly advised that you do not add any handlers other than NullHandler to your library's loggers". Prevents stderr noise when callers haven't configured logging. | S | One line in each `<pkg>/__init__.py`: `logging.getLogger("<pkg>").addHandler(logging.NullHandler())`. |
| Library does NOT call `logging.basicConfig()` or set any handler/level | Python stdlib HOWTO explicit: "It is strongly advised that you do not log to the root logger in your library." Doing so steals control from the application. | S | Hard rule. CI lint or code-review concern. |
| Log levels follow stdlib convention | DEBUG/INFO/WARNING/ERROR levels with standard semantics. The question proposes a level map that matches stdlib: DEBUG=request/response, INFO=auth events, WARNING=retries, ERROR=terminal failures. Adopt as-is. | S | Confirmed correct by Python HOWTO level table. |
| **Credentials redacted in every log line** | Project security constraint: "nunca commitear .env ni exponer credenciales en logs, reportes o tests" (CLAUDE.md). The v1.0 harness already has `verification/redaction.py` (Bearer + patterns). | M | The library logger must redact at format time. Implementation: a `RedactingFormatter` mixin OR (preferred for libraries) call the existing `verification/redaction.py` redact() before passing the message — but `verification/` is harness, not publishable. **Recommendation:** copy the regex set into each package's `_logging.py` (same dedup pattern). Match the `verification/redaction.py` patterns: `Authorization: Bearer ***`, `X-Auth-Token: ***`, `password=***`, etc. |
| Body logging is OPT-IN (default OFF) | Bodies may contain PII or credentials (matriz order responses include account numbers). Anthropic/OpenAI default to NOT logging bodies; debug-level body logging requires explicit env or kwarg. | S | Document `<PKG>_LOG_BODY=1` env or `Client(log_bodies=True)` kwarg. |
| Structured field convention via `extra={}` | Python stdlib mechanism. Conventional field names: `package`, `method`, `url`, `status_code`, `attempt`, `duration_ms`, `account_id?`, `request_id?`. | S | Example: `logger.debug("HTTP request", extra={"method": "GET", "url": redact(url), "attempt": 1})`. JSON formatter (caller-configured) renders structured. |
| Don't break callers who haven't configured logging | NullHandler ensures zero output. Mandatory regression test: `import iol_client; iol_client.configure(...)` produces no stderr output. | S | Direct consequence of NullHandler discipline. |

### D.1 Level Map (Recommended Default)

| Level | What Gets Logged | Fields |
|-------|------------------|--------|
| DEBUG | Outgoing request line, incoming response status + duration, retry sleep computation | `method`, `url` (redacted), `status_code`, `duration_ms`, `attempt`, `sleep_seconds` |
| INFO | Auth events: token acquired, token refreshed, token invalidated by configure() | `event` (one of `auth.acquired`/`auth.refreshed`/`auth.cleared`), `ttl_seconds`, account-id if multi-account |
| WARNING | Retry triggered (attempt N/M); rate-limit detected; transient transport error caught | `attempt`, `status_code` or `error_type`, `retry_after`, `next_sleep` |
| ERROR | Terminal failure after all retries; auth failure (401/403 final); unexpected transport error not eligible for retry | `status_code`, `final_attempt`, `exception_type`, `endpoint` |

### D.2 Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `LogRecord` extra includes a `request_id` UUID per `_request()` invocation | Traces a single logical call across DEBUG (start), WARNING (retries), ERROR/DEBUG (final). | S | Generate `uuid4().hex[:8]` per `_request()`; thread through retries; include in every related log entry. P2. |
| Account-id field in multi-account contexts (higyrus, matriz) | Disambiguates concurrent calls against different accounts. Directly serves the HIGY multi-account fix. | S | When the public function takes `id_cuenta`/`accountId`, include it in `extra`. P2. |
| Body redaction patterns merge with verification/redaction.py | Single source of truth for redaction regex. | M | Today verification/ is the harness; v1.1 could lift a stable redaction-pattern dataset into each package (duplicate but versioned). P2. |
| Log shape compatible with structlog/json-loggers if caller configures them | `extra={}` already works with any stdlib-compatible formatter; mention in docs. | S | Zero implementation work beyond following stdlib `extra` pattern. |

### D.3 Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Library configures its own format/handler | "Looks nice out of the box" | Steals control from the application; Python HOWTO explicitly forbids. | NullHandler only. Document the JSON-formatter example in README for callers who want structured output. |
| Logging request/response bodies by default | "Easier debugging" | Leaks PII, credentials, financial data into application logs. Direct CLAUDE.md violation. | Bodies opt-in via env or kwarg; redaction-on by default even when opted in. |
| Adopting structlog/loguru as a runtime dep | "Better logging" | Adds a runtime dep to every publishable package; the v1.0 constraint (zero shared deps, hatchling wheel each) makes this expensive. | Stdlib `logging` with `extra={}`. Caller is free to install structlog and configure it themselves. |
| Synchronous `print()` in any code path | "Quick debug" | Already absent in v1.0 (zero print calls). v1.1 must not introduce. | Use the package logger. |
| Capturing/logging Authorization header values "for debugging" | "Diagnose auth issues" | Direct security violation. | Log only `auth.<event>` semantic markers (acquired/refreshed/cleared); never the token value. |

**Dependencies on v1.0:** existing `verification/redaction.py` regex set, security constraint from CLAUDE.md, no-current-logging baseline (CONVENTIONS L110-111 confirms zero-log status today). Logging in the library MUST coexist with the verification driver harness (which has its own `safe_print` / `redact`); they're independent layers and should not couple.

---

## Axis E — Findings File Append-Only / Dedupe

**Question:** What's the expected behavior for an "append-only" findings file with idempotent finding entries? How is operator-added rationale preserved across re-runs?

### E.1 Table Stakes

| Feature | Why Expected | Complexity | Notes / Reference |
|---------|--------------|------------|-------------------|
| **Stable finding-IDs (deterministic from finding payload)** | Idempotency requires the driver to recognize "I already wrote this one." Stable ID = hash of `(package, probe_name, error_class, normalized_message)` or operator-assigned `F-NN` slug. | S | The v1.0 convention already uses `F-09`-style IDs in matriz findings; carry forward as the dedup key. New finding without explicit ID → driver synthesizes from probe context. |
| **Append-only writes** — never delete, never reorder | The findings file is the audit trail of the cycle. Reordering breaks the forensic-localizable property (PROJECT.md) that the v1.0 baseline relies on. | S | Implementation: driver re-runs scan existing file, build set of IDs present, only append entries whose ID is absent. |
| **Operator-added sections preserved verbatim** | Operator classifies (CONFIRMED/FIXED/EXPECTED/NO-FIX), writes `Rationale:`, writes `Regression:` paths. Re-running the driver MUST NOT clobber those. | M | Implementation: driver only writes the auto-generated body. Operator-edited fields (`Classification:`, `Rationale:`, `Regression:`, `Resolution:`) live in a stable position; driver code reads them, never overwrites them. Markdown structure must support unambiguous parsing — recommend YAML frontmatter per finding OR clearly-delimited operator-section per finding (`<!-- operator-section-start -->` / `end`). |
| **Dedup is content-addressed, not line-number addressed** | A finding's location in the file should not affect whether it's a duplicate. | S | Hash/ID compares finding identity, not position. |
| **D-MATZ-27 fix specifically** | Today's matriz driver appends duplicates of the same finding across re-runs. v1.1 must resolve. | M | Direct implementation of the above. Same logic applies to all four drivers. |
| Driver writes `Cycle: <id>` field on first occurrence | v1.0 ratified the convention (PROJECT.md L88): every finding is tagged with the cycle that first observed it. Append-only means subsequent cycles don't overwrite the original cycle tag. | S | First write: `Cycle: verification-cycle-2026-Q3`. Re-run in same cycle: skip. Re-run in next cycle: still skip (the finding already exists); driver may instead append `Reobserved-in: <cycle-id>` to a separate operator-readable log. |
| Validation that re-running the driver is idempotent (no-op when nothing changed) | The success criterion: `git status` after a driver re-run with no new findings = clean. | S | Pytest regression: run driver twice in succession against a captured mock; second run produces zero diff. |

### E.2 Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `Re-observed: <cycle-id>` append to existing finding when seen again | Tracks finding lifecycle across cycles without losing the original timestamp. | M | Operator-readable, machine-parseable. P2 — useful for v1.2+ cycles but not required for v1.1 fix scope. |
| Programmatic `findings.add(...)` API in `verification/findings.py` | Centralizes the dedup logic — drivers don't reinvent it. | S | The PROJECT.md already cites `verification/findings.py append-only` as a v1.1 deliverable. Implementation likely already in the harness's mind; this just formalizes the API shape. |
| Auto-generated `findings.toml` machine-readable side-file | Markdown is operator-friendly; TOML enables tooling (cycle-report aggregation, dashboard). | M | P3. v1.1 keeps markdown as source of truth. |

### E.3 Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Driver rewrites the entire findings file on each run | "Easier than parsing the existing file" | Destroys operator rationale; loses cycle-of-first-observation tag; breaks forensic-localizability. | Append-only with content-addressed dedup. |
| Truncating findings older than N cycles | "Keep the file small" | Loses audit trail; breaks the "DRIFT-02 baseline" property where the cycle-report aggregates historical state. | Don't truncate. If size becomes a real concern (it won't at current scale), archive older cycles to a separate file. |
| Auto-classifying findings (CONFIRMED/EXPECTED/NO-FIX) without operator | "Save operator work" | Classification is judgment based on context the driver can't see (is the API contract documented to behave this way?). v1.0 explicitly operator-drives it. | Driver writes only the raw observation; classification stays operator's call. |
| Mutating a finding's operator-edited fields when re-observed | "Update with latest info" | Operator wrote `Rationale: Expected per Primary API §6.3 docstring` for a reason. Re-run shouldn't second-guess. | Driver reads, never writes, operator fields. |
| Reordering findings by ID/date "for cleanliness" | "More readable" | Breaks line-based git diff history; breaks `git blame`-based forensics. | Append-only literally means append at end. |

**Dependencies on v1.0:** existing `verification/findings.py` (PROJECT.md cites as deliverable), existing F-NN ID convention, existing operator-section conventions (`Classification:`, `Rationale:`, `Regression:`), forward-looking ratified convention from Phase 5 Op A (`Regression: <path>::<test>` field). The append-only rewrite **must** read and preserve all four operator-edited field names verbatim.

---

## Feature Dependencies

```
[Axis A: Client class]
    └──enables──> [Axis B: sync/async parity refactor]
                       └──enables──> [matriz aio.py creation]

[Axis A: Client class]
    └──prerequisite for──> [HIGY multi-account fix]
                                  (multi-account needs instance-scoped state)

[Axis A: Client class]
    └──prerequisite for──> [IOL refresh_token persistence]
                                  (instance-scoped _refresh_token attribute)

[Axis C: Retries/backoff]
    └──requires──> [verification/mutation_gate.py]
                          (existing v1.0 — retry layer reads it to gate POST/PATCH)

[Axis C: Retries/backoff]
    └──enhances──> [Axis D: structured logging]
                          (retries WARN-log per attempt; trivially structured)

[Axis D: structured logging]
    └──requires──> [redaction patterns]
                          (copy from verification/redaction.py into per-package _logging.py)

[Axis E: findings append-only]
    └──standalone, no v1.1 cross-deps──> [4 drivers consume it]

[Axis A] ──coexists-with──> [v1.0 module-level convenience funcs]
                                   (compat layer; must remain non-breaking)
```

### Dependency Notes

- **Axis A is a prerequisite for B**: deduplicating sync/async logic into `_core.py` helpers is much cleaner once the `Client` class exists, because the helpers can be `Client`-aware (operating on `self._http`, `self._token`, etc.) instead of operating on module globals.
- **Axis A unlocks the HIGY multi-account fix**: today's singleton can't represent "logged in as two accounts simultaneously" because there's one `_token`. With `Client` instances, two clients = two tokens. The fix becomes natural rather than a workaround.
- **Axis A unlocks IOL refresh_token persistence**: storing `_refresh_token` and `_access_token_expires_at` on `self` is cleaner than two new module globals per surface.
- **Axis C requires the mutation_gate**: the retry layer must NOT retry POSTs against `*.primary.com.ar` unless the v1.0 `mutating_allowed` flag is true AND an Idempotency-Key is present. The mutation_gate already exists in `verification/`.
- **Axis C enhances Axis D**: each retry attempt emits a WARNING log line with structured fields — same axis can be implemented in one pass.
- **Axis D requires redaction patterns**: NOT a direct module import (verification/ is harness, not publishable from packages); instead, duplicate the regex set into each package's `_logging.py`. Same "no shared deps" constraint that applies to auth and exceptions.
- **Axis E is the most standalone**: it lives in `verification/findings.py` (the harness), not in the packages themselves. Drivers use it. No coupling to A/B/C/D.

---

## MVP Definition (v1.1 = the MVP for this milestone)

### Must Land In v1.1

- [x] **Axis A** — `Client` class per package + lazy default-client backing top-level convenience funcs + sync `close()`/context-manager + async `aclose()`/async-context-manager. Compat layer non-breaking. (Complexity: M per package × 4 packages.)
- [x] **Axis B** — Per-package `_core.py` (or equivalent) with deduped logic; `client.py` and `aio.py` become thin sync/async stubs over the shared helpers. PLUS matriz-client gets a brand-new `aio.py` mirroring REST surface. (Complexity: M for dedup × 4 + L for matriz aio creation.)
- [x] **Axis C** — Retry layer with: 408/409/429/5xx + connection errors, max_retries=2 default, full jitter exponential backoff, Retry-After honored (capped at 60s), idempotency-by-method (no POST/PATCH retry without explicit opt-in), mutation_gate check before retry, per-Client and per-call config. (Complexity: M, one implementation × 4 packages.)
- [x] **Axis D** — Stdlib `logging` per package: `getLogger(__name__)`, NullHandler attached in `__init__.py`, DEBUG/INFO/WARNING/ERROR level map, structured `extra={}`, redaction in formatter, body-logging opt-in. (Complexity: S-M per package × 4.)
- [x] **Axis E** — `verification/findings.py` append-only API; D-MATZ-27 dedupe; operator fields (Classification/Rationale/Regression/Resolution) preserved verbatim across re-runs; idempotent re-run = git-clean. (Complexity: M, one implementation.)
- [x] **4 deferred fixes** as standalone work items: F-09 matriz ERROR-MAP, higyrus F-02 (`get_listado_cuentas=0`), IOL refresh_token persistence, HIGY multi-account. (Complexity: S-M each.)
- [x] **WR-01..WR-08** — code review concerns from Phase 5. (Complexity: assumed S-M each per v1.0 review tradition; needs phase-level research per concern.)

### Defer To v1.2 (already documented in PROJECT.md)

- [ ] prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff)
- [ ] `matriz_client.ws_client` live verification (WebSocket layer)
- [ ] `wallets-client` scope extension
- [ ] New endpoints / new live surfaces

### Future Consideration (v2+)

- [ ] Generated-code parity tooling (Axis B.2 — one source, two emit paths)
- [ ] Automatic Idempotency-Key generation for retried POSTs (Axis C.2 — would conflict with current operator gate)
- [ ] `findings.toml` machine-readable side-file (Axis E.2)
- [ ] Decorrelated jitter as alternative backoff (Axis C.2)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `Client` class with `close()`/context manager (A.1) | HIGH (unblocks multi-account, persistent refresh, dedup) | M | P1 |
| Lazy default-client convenience-func compat layer (A.1) | HIGH (non-breaking is non-negotiable) | S | P1 |
| `_core.py` sync/async dedup (B.1) | HIGH (kills the duplication tech debt root cause) | M | P1 |
| matriz `aio.py` creation (B.1) | HIGH (parity with all other packages) | L | P1 |
| Retry on 408/409/429/5xx + connection (C.1) | HIGH (transient resilience without breaking POST) | M | P1 |
| Full-jitter exponential backoff (C.1) | HIGH (AWS-recommended default) | S | P1 |
| Honor `Retry-After` with cap (C.1) | HIGH (table stake, prevents deadlock) | S | P1 |
| Idempotency-by-method default (C.1) | HIGH (prevents matriz duplicate orders) | S | P1 |
| Read `mutation_gate` before any POST/PATCH retry (C.1) | HIGH (project-specific requirement, PROJECT.md mandates) | S | P1 |
| `getLogger(__name__)` + NullHandler (D.1) | HIGH (no-noise default, callers can opt-in) | S | P1 |
| Level map (DEBUG req/INFO auth/WARN retry/ERROR terminal) (D.1) | HIGH (matches stdlib + ecosystem conventions) | S | P1 |
| Redaction in log formatter (D.1) | HIGH (security non-negotiable) | M | P1 |
| Findings append-only + content-addressed dedup (E.1) | HIGH (D-MATZ-27 directly) | M | P1 |
| Operator-fields preserved across re-runs (E.1) | HIGH (preserves operator rationale; PROJECT.md mandates) | M | P1 |
| `client.with_options(...)` per-call config (A.2) | MEDIUM (ergonomic but not required) | M | P2 |
| Pluggable `http_client` injection (A.2) | MEDIUM (testing ergonomic) | M | P2 |
| `Client.from_env()` classmethod (A.2) | LOW (discoverability) | S | P2 |
| WARN log per retry with `extra` fields (C.2 / D.1 cross-cut) | HIGH (debuggability) | S | P1 (free in C+D combined pass) |
| `max_elapsed_seconds` retry budget cap (C.2) | MEDIUM (belt-and-suspenders) | M | P2 |
| `request_id` per `_request()` invocation (D.2) | MEDIUM (traces across retries) | S | P2 |
| Account-id field in `extra` for higyrus/matriz (D.2) | MEDIUM (multi-account debug) | S | P2 |
| `Re-observed: <cycle-id>` finding lifecycle marker (E.2) | LOW (nice for v1.2 cycle reports) | M | P3 |
| Idempotency-Key auto-generation (C.2) | LOW (conflicts with mutation_gate) | M | P3 |
| Decorrelated jitter alternative (C.2) | LOW (full jitter sufficient) | M | P3 |
| Generated-code parity tooling (B.2) | LOW (huge cost) | XL | P3 / out of scope |

---

## Competitor Reference Behaviors

| Behavior | Anthropic SDK | OpenAI SDK | Stripe SDK | httpx (transport) | market-libs v1.1 plan |
|----------|---------------|------------|------------|-------------------|------------------------|
| Sync class | `Anthropic(...)` | `OpenAI(...)` | `StripeClient(...)` | `httpx.Client()` | `Client(...)` per package |
| Async class | `AsyncAnthropic(...)` | `AsyncOpenAI(...)` | (none — uses asyncio bridge) | `httpx.AsyncClient()` | `AsyncClient(...)` per package in `aio.py` |
| Module-level convenience | (none — explicit) | `openai.chat.completions.create(...)` (lazy default) | (none — explicit) | (none) | KEEP existing `pkg.get_quote(...)` (lazy default-client) |
| `close()` / `aclose()` | yes | yes | (managed) | yes | yes (table stake) |
| Context manager | yes | yes | yes | yes | yes (table stake) |
| `with_options(...)` per-call | yes | yes | (per-request `idempotency_key` kwarg) | (no) | P2 differentiator |
| Default retries | 2 attempts | 2 attempts | 0 (opt-in) | 0 (must wrap) | 2 attempts |
| Retried status codes | 408, 409, 429, ≥500 | 408, 409, 429, ≥500 | connection + 409 | (transport only: connect errors) | 408, 409, 425, 429, 500, 502, 503, 504 + connection |
| Honor `Retry-After` | yes (caused deadlock when unbounded → bug filed) | yes | yes | (no — caller responsibility) | yes, capped at 60s default |
| Idempotency for POST | (POST is mostly safe in their API surface) | (POST is mostly safe in their API surface) | Idempotency-Key auto-generated | (caller responsibility) | NO auto-retry on POST/PATCH by default; mutation_gate check |
| Jitter type | exponential + jitter (full-style) | exponential + jitter | exponential + jitter | (transport doesn't jitter) | full jitter (AWS-recommended) |
| Logger naming | `logging.getLogger("anthropic")` | `logging.getLogger("openai")` | `logging.getLogger("stripe")` | `logging.getLogger("httpx")` | `logging.getLogger("<pkg>")` per package |
| NullHandler | yes | yes | yes | yes | yes (stdlib HOWTO mandate) |
| Default body logging | OFF | OFF | OFF | OFF | OFF (opt-in) |

---

## Confidence Assessment

| Axis | Confidence | Reason |
|------|------------|--------|
| A. Client class API | HIGH | Cross-confirmed in anthropic, openai, stripe, httpx official docs. Module-level lazy default is the openai v1.0 pattern explicitly. |
| B. Sync/async parity | HIGH | All three reference SDKs ship the mirror pattern with identical method names. CONVENTIONS.md already enforces this. |
| C. Retries/backoff | HIGH | Cross-confirmed status code list (anthropic, openai), idempotency default (urllib3, RFC 9110), jitter recommendation (AWS Architecture Blog), Retry-After honoring (MDN + concrete Anthropic deadlock bug as warning). |
| D. Structured logging | HIGH | Python stdlib HOWTO is unambiguous on NullHandler + don't-configure-handlers; level conventions are stdlib-native; `extra={}` is the documented structured-field mechanism. |
| E. Findings append-only | MEDIUM | Pattern is project-internal (not an industry convention to cite); recommendations derive from v1.0's existing operator-driven workflow as documented in PROJECT.md Phase 5 ratification. Operator should validate the proposed YAML-frontmatter-or-delimited-section structure before implementation. |

---

## Gaps / Open Questions for Phase-Level Research

These are items that should be revisited when planning the specific phases:

1. **D — exact redaction regex set** to lift from `verification/redaction.py` into per-package `_logging.py`. Phase-level work needs to enumerate the current patterns and confirm they cover Bearer, X-Auth-Token, `password=`, IOL refresh_token, and Higyrus JSON `password` field.
2. **E — exact markdown/frontmatter structure** of the findings file (operator preference: YAML frontmatter per finding vs. delimited operator-section). Operator decision required before implementation.
3. **C — exact value of `max_elapsed_seconds` cap** if adopted as P2 (not required for v1.1, but if a phase picks it up, needs a number).
4. **WR-01..WR-08** code-review concerns are listed by ID in PROJECT.md but the concern content itself isn't in the research scope — each will need a 1-line research note at phase-planning time.
5. **A — multi-account API shape for HIGY fix**: does the caller pass a list of accounts to one `Client`, or instantiate one `Client` per account? Operator decision; recommend the latter (one `Client` per account = simplest model that uses the refactor naturally).
6. **C — Idempotency-Key opt-in API** if any v1.1 phase wants to enable explicit POST retry: kwarg on `_request()` vs. on the public method. Defer to phase-level.

---

## Sources

- [HTTPX Async Support](https://www.python-httpx.org/async/) — context manager recommendation, pool reuse
- [HTTPX Clients](https://www.python-httpx.org/advanced/clients/) — single global client pattern
- [HTTPX Transports](https://www.python-httpx.org/advanced/transports/) — built-in `httpx.HTTPTransport(retries=N)` handles only connect errors
- [Anthropic Python SDK retries — DeepWiki](https://deepwiki.com/anthropics/anthropic-sdk-python/4.4-request-lifecycle-and-retry-logic) — 2 retries default, 408/409/429/≥500, exponential backoff with jitter
- [Anthropic SDK source (_client.py)](https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/_client.py) — class shape reference
- [Anthropic SDK Retry-After 120s deadlock issue](https://github.com/NousResearch/hermes-agent/issues/26293) — concrete evidence to cap Retry-After
- [OpenAI Python — Error Handling and Retry Logic — DeepWiki](https://deepwiki.com/openai/openai-python/3.4-error-handling-and-retry-logic) — same retry shape as anthropic, per-request `timeout` = per-attempt
- [OpenAI Python — Module-Level API pattern — DeepWiki](https://deepwiki.com/openai/openai-python/2.3-module-level-api-usage) — lazy module-private `_ModuleClient` backing top-level helpers (referenced; not directly fetched)
- [OpenAI Python source (_base_client.py)](https://github.com/openai/openai-python/blob/main/src/openai/_base_client.py) — base client architecture
- [Stripe Idempotent Requests](https://docs.stripe.com/api/idempotent_requests) — automatic Idempotency-Key generation pattern (cited as differentiator, not adopted)
- [Stripe — Idempotency and Retry Logic (stripe-node DeepWiki)](https://deepwiki.com/stripe/stripe-node/3.5-idempotency-and-retry-logic) — opt-in `max_network_retries`, connection + 409 retried
- [Stripe Advanced Error Handling](https://docs.stripe.com/error-low-level) — auto-generated keys for retries
- [Python Logging HOWTO — official](https://docs.python.org/3/howto/logging.html) — library NullHandler mandate, level conventions, don't-log-to-root
- [Python logging.handlers (NullHandler)](https://docs.python.org/3/library/logging.handlers.html) — NullHandler reference
- [AWS Architecture Blog — Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/) — full jitter recommended default
- [AWS Builders' Library — Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) — operational analysis
- [Thom Wright — The problem with decorrelated jitter](https://thomwright.co.uk/2024/04/24/decorrelated-jitter/) — counterpoint analysis (cited; not adopted for v1.1)
- [MDN — Retry-After header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Retry-After) — RFC format (delta-seconds or HTTP-date), client honoring guidance
- [MDN — 429 Too Many Requests](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/429) — Retry-After is the reliable signal
- [RFC 9110 — HTTP Semantics — Idempotent methods](https://www.rfc-editor.org/rfc/rfc9110) — GET/HEAD/OPTIONS/PUT/DELETE idempotent; POST/PATCH not
- [Stamina — Hynek Schlawack](https://github.com/hynek/stamina) — opinionated retry wrapper (cited as comparison; not adopted; standalone-wheel constraint)
- [Python Structlog — Standard Library Logging](https://www.structlog.org/en/stable/standard-library.html) — `extra` field convention background

---

*Feature research for: market-libs v1.1 Tech Debt Cleanup*
*Researched: 2026-06-10*
