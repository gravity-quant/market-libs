# Phase 8: Retries, Backoff, Structured Logging — Research

**Researched:** 2026-06-12
**Domain:** Python HTTP-client reliability (retries + backoff) and observability (structured logging + redaction) via `tenacity` 9.1.4 wrapping `httpx.HTTPTransport`/`AsyncHTTPTransport`, applied 4× (one per package) on top of the Phase 7 `_core.py` + transport-shell architecture
**Confidence:** HIGH — every locked decision (D-01..D-32 in CONTEXT.md) is verified against (a) the actual tenacity 9.1.4 source code installed locally, (b) the Phase 7 codebase state on disk, (c) official tenacity docs, and (d) RFC 9110 §10.2.3 (`Retry-After`) and PEP 562. `tenacity` `[OK]` per slopcheck pre-install scan.

## Summary

Phase 8 is a **mechanical, low-uncertainty delivery** — every architectural decision has been locked across CONTEXT.md D-01..D-32, the existing Phase 7 baseline already exposes the exact hooks the retry transport needs (the `RequestSpec.idempotent: bool = False` forward-declared field, the `_core.py` builders, the `_request(spec)` transport shell), and the only new runtime dependency (`tenacity>=9.1.0,<10`) was already vetted against three alternatives in `.planning/research/STACK.md` with the rationale fully documented. The work for each of the 4 packages is: (1) wire `RequestSpec.idempotent=True` on GET builders + login/refresh, (2) add `_transport.py` (sync) and `_atransport.py` (async, NOT in matriz) housing a `RetryTransport(httpx.HTTPTransport)` / `AsyncRetryTransport(httpx.AsyncHTTPTransport)` subclass that wraps a `tenacity.Retrying` / `AsyncRetrying` loop honoring `Retry-After` (cap 60s) + full-jitter exponential backoff, (3) add `_logging.py` with a `RedactingFilter(logging.Filter)` that scrubs Bearer/X-Auth-Token/password leaks even when the consumer enables DEBUG, (4) attach `NullHandler` to `logging.getLogger("<pkg>")` in `__init__.py`, (5) wire 401 re-auth-once into the shell `_request()` (NEVER into the retry transport's `retry_on=` predicate), and (6) extend `Client.__init__` / `AsyncClient.__init__` / `configure()` with two minimal kwargs (`max_retries=2`, `http_client=None`).

The single highest-risk pitfall to be paranoid about is **Pitfall 4 / RELY-03 — retry of a mutating POST**. In matriz, `new_order`, `replace_order`, and `cancel_order` are technically `GET` (Primary API quirk), so the standard "retry if method ∈ idempotent_methods" heuristic from `httpx-retries` would silently retry them. The locked gate is `request.extensions["idempotent"]` set by the shell `_request()` from `RequestSpec.idempotent` — driver of the gate is the explicit builder flag, NEVER the HTTP method. The cross-package guard test (`verification/test_retry_mutation_gate.py`) is parametrized over the 4 packages and asserts exactly 1 outgoing wire request for any mutating builder mocked against 503. This regression test must land in Plan 1 (cross-cutting infra) and stay red until Plan 5 (matriz) closes — that's the design intent of D-21.

**Primary recommendation:** Implement exactly as the CONTEXT.md decisions specify. The planner should NOT introduce alternative patterns (custom Wait subclass for Retry-After is OK if simpler than parsing inside `handle_request`; everything else is locked). The execution risk is mechanical (4 packages × duplicated code) not architectural.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Retry mechanism + 401 boundary**

- **D-01:** `RetryTransport(httpx.HTTPTransport)` subclass per-package, sync = `_transport.py`, async = `_atransport.py::AsyncRetryTransport(httpx.AsyncHTTPTransport)`. Gate via `request.extensions["idempotent"]` (set by shell `_request()` pre-send from `RequestSpec.idempotent`). Transport sees only status codes + network errors — NEVER domain exceptions.
- **D-02:** 401 re-auth in shell `_request()`, not in transport. Pattern: `try: _raise_for_response(resp) except <Pkg>AuthError: state.token=None; _ensure_token(); req.headers["Authorization"]=...; resp=http.send(req); _raise_for_response(resp)`. Exactly one re-auth. `AuthError` NEVER in `retry_on=`.
- **D-03:** Auth-flow request (`build_login_request`, `build_refresh_request`) marked `idempotent=True` explicitly.
- **D-04:** `Retry-After` cap 60s + cap-then-retry. Server `Retry-After: <delta-seconds>` or `Retry-After: <HTTP-date>` > 60s → sleep 60s then retry. Exhaust → propagate `RateLimitError`.
- **D-05:** Retry exhaust → original `APIError`/`RateLimitError` of last response — zero surface change, no `RetryExhaustedError`, no `.attempts` attribute.
- **D-06:** `max_attempts=2` uniform cross-package (1 initial + 1 retry). `max_retries=N` config kwarg means N retries (= attempts-1 — total `max_retries+1` requests when retries happen).
- **D-07:** `retry_on=` set locked: status codes `408, 409, 429, ≥500`; exceptions `httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout`. NEVER: `<Pkg>AuthError`, `<Pkg>APIError`, `PrimaryAPIError`, `HigyrusAPIError`, `ValueError`, `RuntimeError`.
- **D-08:** Backoff full-jitter, base=1s, max=30s, exp=2. `delay = random.uniform(0, min(max, base*2^attempt))`. Aligned with `tenacity.wait_exponential_jitter`.

**Logging structure**

- **D-09:** 8 canonical fields + 1 conditional (`account_id`). Per-log: `package`, `method`, `url` (query-redacted), `status_code`, `attempt`, `duration_ms`, `request_id`, `endpoint_name`. `account_id` conditional on higyrus + matriz via `RequestSpec.account_id`.
- **D-10:** `RedactingFilter(logging.Filter)` per package in `_logging.py`. Rewrites `record.msg`/`record.args`/`record.__dict__` values in-place via regex pass (Bearer / X-Auth-Token / `password=` / `refresh_token=` / JSON `{"password":"..."}` / IOL refresh_token / matriz auth_basic). Duplicated 4× (NOT importable from `verification/`).
- **D-11:** `account_id` propagation via new `RequestSpec.account_id: str | None = None` field in higyrus + matriz `RequestSpec` (ambito/iol keep their shape).
- **D-12:** Levels: DEBUG req/resp without body/headers; INFO auth events; WARNING retry attempts with `retry_reason` field; ERROR terminal failures.
- **D-13:** One logger per package = `logging.getLogger("<pkg>")` — no sub-loggers (`<pkg>.transport`, `<pkg>.auth`).
- **D-14:** Library does NOT touch `httpx`/`httpcore` loggers — consumer decides.

**Public API surface**

- **D-15:** Minimal kwargs added to `Client/AsyncClient.__init__` + `configure()`: `max_retries: int = 2`, `http_client: httpx.Client | None = None` (`httpx.AsyncClient` for AsyncClient). NOT exposed: `retry_backoff_*`, `retry_jitter`, `retry_on=`, `log_level`.
- **D-16:** `http_client=` used AS-IS, caller responsible. If caller passes `http_client=httpx.Client(transport=...)`, package uses it tal cual without auto-wrapping with `RetryTransport`.
- **D-17:** Drop `log_level` kwarg. Consumer uses `logging.getLogger("<pkg>").setLevel(...)`.
- **D-18:** `max_retries` only Client/configure() level (no per-call). `Client.with_options()` deferred to v1.2.
- **D-19:** `max_retries=0` bypasses retry loop entirely → 1 outgoing request total.
- **D-20:** Default `max_retries=2` documented as "subject to tuning in future minor versions".

**Plan slicing + guard tests**

- **D-21:** 6 planes per-package serial: Plan 1 infra cross-cutting tests-first; Plans 2-5 per-package (ámbito → iol → higyrus → matriz); Plan 6 CI green gate.
- **D-22:** matriz `auth_basic` redaction: filter detects `auth_basic` tuple in `extra` or `Authorization: Basic ...` in headers, splits to `auth_basic_user=<user>` + `auth_basic_password='<redacted>'`.
- **D-23:** matriz Risk API — `RetryTransport` YES (5xx/429/network retry), 401 re-auth NO (no token to refresh; `AuthError` immediate). Shell `_request()` branches: if `spec.auth_basic is not None`, skip re-auth on `AuthError`.
- **D-24:** matriz 200-OK with `status=="ERROR"` NEVER retries. `PrimaryAPIError` NEVER in `retry_on=`. Body-consume-then-raise pattern from Phase 7 D-06 preserved.
- **D-25:** matriz `_atransport.py` NOT created in Plan 5 — Phase 10 territory. Plan 5 only delivers `matriz_client/_transport.py` (sync). matriz snapshot: only `Client` gains kwargs; `AsyncClient` (stub) keeps current signature.
- **D-26:** New cross-cutting guard test files in `verification/`:
  - `test_retry_mutation_gate.py` — parametrize × 4 paquetes; mock 503 on POST sans `idempotent=True` → exactly 1 wire request; mock 503 on GET (idempotent default `True`) → N attempts.
  - `test_retry_401_reauth.py` — parametrize × auth packages (iol/higyrus/matriz); mock 401→200 → 2 wire requests + refreshed header; mock 401→401 → 2 requests + `AuthError`.
  - `test_logging_root_unchanged.py` — assert `logging.root.handlers` unchanged after import of all 4 packages.
  - `test_logging_no_token_leak.py` — caplog × 4 packages with `configure(token="SECRET-LITERAL-12345")` + fire mocked request → assert NO record contains the literal in `getMessage()`/`args`/`extra`.
  - `test_retry_after_cap.py` — mock 429 with `Retry-After: 600` → delay ≤ 60s + retry happens.
  - `test_async_cancellation.py` — parametrize × async packages (ambito/iol/higyrus); matriz `skip`. `asyncio.wait_for(client.get_X(), timeout=0.5)` + mock 503→503 → `TimeoutError` without waiting full retry budget.
- **D-27:** CI grep rule via planner discretion: (a) ruff `flake8-logging` LOG015 if available, OR (b) plain grep step in `.github/workflows/ci.yml`, OR (c) pytest regression. Preference: combo (ruff LOG015 + grep for `logging.basicConfig`).
- **D-28:** Snapshot público update per-plan atomic. Each Plan 2-5 adds the 2 new kwargs (`max_retries`, `http_client`) in `Client.__init__`, `AsyncClient.__init__`, `configure()` signatures.

**`_ensure_token()` × RetryTransport × request_id**

- **D-29:** Login goes through same `state.http_client` (atravesa `RetryTransport`). `_ensure_token()` `httpx.Client.send(login_request)` via `state.http_client`. `build_login_request` marks `idempotent=True` (D-03). 5xx/connection transient → retry. 401 → `AuthError` immediate (no recursive re-auth — shell re-auth attempt UNA vez only). Risk API similar but sin re-auth (D-23).
- **D-30:** `request_id = uuid.uuid4().hex` generated UNA vez in `_request()` pre-send. Passed via `request.extensions["request_id"]`. All retry attempts share the same id. `attempt` field (1, 2, ...) distinguishes. NOT sent to server (no `X-Request-ID` header — v1.2 backlog).

**tenacity integration shape**

- **D-31:** `Retrying` / `AsyncRetrying` as iterator inside `handle_request`:
  ```python
  for attempt in Retrying(
      stop=stop_after_attempt(self.max_attempts),
      wait=wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0),
      retry=retry_if_exception_type(_RETRYABLE_EXC) | retry_if_result(self._is_retryable_status),
      reraise=True,
  ):
      with attempt:
          response = self._inner.handle_request(request)
          response.read()
          if self._is_retryable_status(response):
              raise _RetryableStatus(response)
          return response
  ```
  Sentinel `_RetryableStatus` is NOT a subclass of `<Pkg>APIError`.
- **D-32:** `AsyncRetryTransport` backoff uses `await asyncio.sleep(delay)`. `asyncio.CancelledError` propagates naturally. Verified via tenacity 9.1.4 source inspection (see Verification Notes below).

### Claude's Discretion

The planner decides:
- **State shared location:** `_transport.py` and `_logging.py` live in `packages/<pkg>/src/<pkg>/` (private modules). Each package self-contained (4× duplication acceptable per project constraint).
- **`RetryTransport` internal structure:** Sentinel exception name (`_RetryableStatus` vs `_TenacityRetryFlag`), `retry_if_exception_type` vs `retry_if_exception` vs `retry_if_result`. Planner adjusts detail.
- **Naming of new `RequestSpec` fields:** Phase 8 adds `account_id: str | None = None` (higyrus + matriz) and `endpoint_name: str` (4 paquetes). Recommendation: `endpoint_name` for clarity (cross-package).
- **Retry-After parsing snapshot:** RFC 9110 §10.2.3 supports `delta-seconds` (int) AND `HTTP-date` (RFC 1123). Recommendation: day 1 — delta-seconds only + log WARNING if HTTP-date detected (forward-compat for v1.2).
- **Logging formatter in testing:** caplog default mode in pytest 8.3 — planner verifies `caplog.set_level(logging.DEBUG, logger="<pkg>")` works correctly with filters attached.
- **Exact `extra={}` field naming:** `attempt` (matches tenacity `attempt_number` semantically, shorter).
- **Test cadence per plan:** `uv run pytest packages/<pkg>/` + `uv run pytest verification/test_retry_*.py verification/test_logging_*.py` + `uv run pytest verification/test_public_surface.py verification/test_sync_async_isolation.py` + `uv run lint-imports` pre-commit.
- **ruff vs grep vs flake8-logging for D-27:** ruff `LOG015` (root-logger-call) covers `logging.root` calls. `logging.basicConfig` is NOT covered by ruff LOG rules — requires explicit grep CI step.

### Deferred Ideas (OUT OF SCOPE)

- `client.with_options(max_retries=N)` per-call override → v1.2+ backlog.
- `Client.from_env()` classmethod → v1.2+ backlog.
- `request_id` sent via `X-Request-ID` header to server → v1.2+ backlog.
- DEBUG payload con body redacted opt-in (env var) → v1.2+.
- Sub-loggers per concern (`<pkg>.transport`, `<pkg>.auth`, `<pkg>.retry`) → v1.2+.
- JSON formatter built-in → v1.2+.
- `max_retries` configurable via env var `MARKET_LIBS_MAX_RETRIES` → v1.2+.
- Per-package tuning of `max_retries` default → uniform = 2 v1.1; v1.2 if telemetry suggests otherwise.
- Auto-wrap caller's `http_client` transport with `RetryTransport` → v1.2 if UX feedback justifies.
- `max_elapsed_seconds` retry budget cap → v1.2+ backlog.
- Automatic `Idempotency-Key` header for retried POSTs → v1.2+.
- `PrimaryAPIErrorTransient` / `PrimaryAPIErrorPermanent` classification → v1.2.
- HTTP-date format in `Retry-After` parsing → recommend defer to v1.2; day 1 only delta-seconds.
- Telemetry export hook (OpenTelemetry) → v1.2+.
- Detect + warn when `http_client=` lacks `RetryTransport` → v1.2.
- **matriz `_atransport.py` + async REST surface** → **Phase 10** (REFAC-04 + TokenStore + spike-findings validated patterns).
- **TokenStore 3-way concurrent (sync + asyncio + ws_client daemon thread)** → **Phase 10** (spike 001c + 003 patterns).
- Deferred bug fixes (F-09 matriz ERROR-MAP / BUG-01, F-02 higyrus / BUG-02, IOL refresh persistence / BUG-03, HIGY multi-account / BUG-04) → **Phase 9** (consume Phase 8 retry+logging infra).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RELY-01 | Retries transparentes via `tenacity` para status codes 408/409/429/≥500 + connection errors (`ConnectError`, `ConnectTimeout`, `ReadTimeout`); default `max_attempts=2`; aplica a 4 paquetes. | §"Standard Stack" — tenacity 9.1.4 confirmed in registry + source inspection; §"Architecture Patterns" Pattern 1 (RetryTransport core loop); §"Code Examples" — `_RETRYABLE_EXC` and `_RETRYABLE_STATUS` sets defined verbatim. CONTEXT.md D-01, D-06, D-07. |
| RELY-02 | Backoff exponencial **full jitter** (AWS-recommended); honra `Retry-After` con cap configurable de 60 s. | §"Architecture Patterns" Pattern 2 (Retry-After custom Wait). CONTEXT.md D-04, D-08. tenacity `wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0)` covers full-jitter math. `wait_retry_after` custom wait pattern documented in §"Code Examples". |
| RELY-03 | Mutation-aware retry gate — `idempotent: bool = False` per `_request()`; GET endpoints lo marcan `True`; POST/PATCH NUNCA retry sin `idempotent=True`; regression test asegura exactly UN request outgoing por POST mockeado contra 503. | §"Code Examples" — mutation gate test pattern. §"Don't Hand-Roll" — using `request.extensions["idempotent"]` instead of method allowlist. CONTEXT.md D-01, D-26 (`test_retry_mutation_gate.py`). Critical for matriz: `new_order` / `cancel_order` are HTTP GET (Primary API quirk) — method-based gate would silently retry them. |
| RELY-04 | Manejo explícito de 401 en `_request()` con **exactly one** re-auth attempt (clear token → `_ensure_token()` → retry once); `AuthError` y `<Pkg>APIError`/`PrimaryAPIError`/`HigyrusAPIError` NUNCA en `retry_on=` tuple. | §"Architecture Patterns" Pattern 3 (401 re-auth boundary). §"Common Pitfalls" Pitfall 1 (auth in retry_on storms). CONTEXT.md D-02, D-23, D-29. matriz Risk API special: re-auth NOT attempted (no token to refresh). |
| LOG-01 | `logging.getLogger("<pkg>")` por paquete + `NullHandler` en `__init__.py`; NUNCA `logging.basicConfig()` ni handlers en `logging.root`; CI grep rule prohíbe ambos en `packages/*/src/`; regression test asegura `logging.root.handlers` unchanged tras `import <pkg>`. | §"Architecture Patterns" Pattern 4 (library logging contract). §"Don't Hand-Roll" — stdlib `logging` only. CONTEXT.md D-13, D-14, D-27 (CI grep). Ruff LOG015 covers root-logger calls; `logging.basicConfig` requires explicit grep step. |
| LOG-02 | `RedactingFilter` por paquete con Bearer/`X-Auth-Token`/`password=`/IOL refresh_token/Higyrus JSON password redaction (duplicado 4×, no importable de `verification/`); regression test (`caplog`) asegura NO substring de token aunque consumer habilite DEBUG. | §"Code Examples" — `RedactingFilter` template per package. §"Common Pitfalls" Pitfall 3 (credentials in DEBUG). CONTEXT.md D-10, D-22 (matriz auth_basic), D-26 (`test_logging_no_token_leak.py`). 4 distinct redaction patterns documented per package. |
| LOG-03 | Convención de niveles (DEBUG req/resp / INFO auth / WARNING retries / ERROR terminal) + structured `extra={}` con `package`, `method`, `url`, `status_code`, `attempt`, `duration_ms`; `account_id` (higyrus, matriz) cuando aplica. | §"Architecture Patterns" Pattern 5 (structured extra=). CONTEXT.md D-09 (8 canonical fields + 1 conditional), D-11 (`account_id` propagation via `RequestSpec.account_id`), D-12 (level conventions). Field names verified against `logging.LogRecord` reserved attribute list (Pitfall 17 prevention). |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Retry on transport errors (5xx/429/connect) | Transport (`_transport.py`/`_atransport.py`) | — | Status codes + network errors are transport-level concerns; tenacity-wrapped `httpx.HTTPTransport` subclass sees raw `httpx.Request` and `httpx.Response` without domain exception coupling. |
| Mutation gate (idempotent flag) | Builder (`_core.py`) | Transport (reads `request.extensions["idempotent"]`) | The decision "is this endpoint idempotent?" is a per-endpoint semantic — set by the builder. The transport reads the gate via `request.extensions` set by the shell `_request()` pre-send. Cannot live in transport alone because matriz `new_order` is HTTP GET (would retry under method-only gate). |
| 401 re-auth-once | Shell `_request()` (Client method) | — | The shell owns the auth state (`state.token`) and the `_ensure_token()` flow. The transport sees raw responses without knowledge of `<Pkg>AuthError`. Re-auth requires calling `_ensure_token()` AND re-sending with refreshed Authorization header — coordinated only at the shell. |
| Auth-flow retry (login/refresh transient errors) | Transport | Shell (sets `idempotent=True` via builder) | `build_login_request` / `build_refresh_request` set `idempotent=True` → transport retries 5xx/network errors. 401 → `AuthError` immediate (no recursive re-auth — the shell re-auth attempt happens UNA vez per business call). |
| Structured logging (req/resp + retry attempts) | Transport (`_transport.py`/`_atransport.py`) | Shell `_request()` (generates `request_id`, sets `extensions`) | The transport emits the DEBUG req/resp + WARNING retry attempt logs since it owns the retry loop and can inspect `attempt.retry_state`. The shell `_request()` generates the `request_id` and propagates `endpoint_name` / `account_id` via `request.extensions` so the transport can pull them into `extra={...}`. |
| Credential redaction | `_logging.py` (`RedactingFilter`) | — | Per package, duplicated 4× — preserves the no-shared-internals constraint. Filter attached to `logging.getLogger("<pkg>")` in `__init__.py`. Cannot live in `verification/` (drivers-only). |
| `NullHandler` library convention | `__init__.py` (per package) | — | Standard Python library convention — `__init__.py` is the unique attach point. |
| `RetryTransport` per-instance state | `_state.py` (`http_client` field) | `Client.__init__` (constructs `httpx.Client(transport=RetryTransport(...))`) | The `RetryTransport` is owned by the `httpx.Client` (or `AsyncClient`) instance stored in `state.http_client`. Created lazily in `_ensure_http_client()` with the `RetryTransport` baked in unless caller passed `http_client=` (D-16). |
| `request_id` UUID generation | Shell `_request()` | Transport (reads from `request.extensions["request_id"]`) | Generated UNA vez per business-call in `_request()` pre-send. All retry attempts of the same request share the same id — `attempt` field distinguishes. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **tenacity** | `>=9.1.0,<10` (current 9.1.4) | Retry wrapper inside `RetryTransport.handle_request`; `Retrying`/`AsyncRetrying` as iterators with `wait_exponential_jitter` + `retry_if_exception_type` + `retry_if_result`. | Only library with: (a) `py.typed` confirmed (verified via source inspection at `/jd/tenacity/py.typed`); (b) sync+async via single import (`Retrying`/`AsyncRetrying`); (c) per-call gate control via `retry=` predicate; (d) zero runtime deps; (e) Apache-2.0 license. Phase research already vetted vs httpx-retries, backoff, roll-our-own — see `.planning/research/STACK.md` §A. **Already locked in CONTEXT.md D-31.** [VERIFIED: PyPI registry — version 9.1.4 confirmed via `importlib.metadata.version('tenacity')` against `uv run --with tenacity python`; `[OK]` per slopcheck install scan] |
| **httpx** | `>=0.27` (already pinned) | `BaseTransport` / `AsyncBaseTransport` subclassing. `RetryTransport(httpx.HTTPTransport)` and `AsyncRetryTransport(httpx.AsyncHTTPTransport)`. `request.extensions` dict for cross-shell-transport metadata propagation. | Existing dependency. No version bump needed. [VERIFIED: existing in `packages/*/pyproject.toml`] |
| **stdlib `logging`** | bundled | Library logger contract: `getLogger("<pkg>")` + `NullHandler` in `__init__.py`; `RedactingFilter(logging.Filter)` per package. | Zero new deps. Library convention per Python logging cookbook ("Configuring logging for a library"). Already verified via `.planning/research/STACK.md` §B. [CITED: https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library] |
| **stdlib `uuid`** | bundled | `uuid.uuid4().hex` for `request_id` per business-call (D-30). | Zero deps. [CITED: stdlib] |

### Supporting (existing, NO new deps)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pytest-httpx** | `>=0.34` (already dev-dep) | Mock HTTP responses for guard tests in `verification/` — `httpx_mock.add_response(status_code=503)` + `httpx_mock.get_requests()` for wire-request-count assertions (mutation gate, 401 chain, Retry-After cap). | All `verification/test_retry_*.py` guard tests. [VERIFIED: existing in `[dependency-groups] dev` at pyproject.toml:23-33] |
| **pytest-asyncio** | `>=0.24` (already dev-dep, `asyncio_mode="auto"`) | Async guard tests for `AsyncRetryTransport` cancellation propagation + async re-auth-once. | `test_async_cancellation.py` (D-26). [VERIFIED: existing config at pyproject.toml:102] |
| **stdlib `re`** | bundled | Regex patterns inside `RedactingFilter` for Bearer / X-Auth-Token / password / refresh_token. | `_logging.py` per package. [CITED: stdlib] |
| **stdlib `random`** | bundled | Full-jitter calculation if NOT using tenacity's `wait_exponential_jitter` directly (D-08 cross-checks with `random.uniform(0, min(max, base*2^attempt))`). | Only if `wait_exponential_jitter` formula divergence requires custom Wait subclass. Recommended: use tenacity's primitive. [CITED: stdlib] |

### Alternatives Considered (already rejected — DO NOT re-litigate)

| Instead of | Could Use | Why Rejected |
|------------|-----------|--------------|
| `tenacity` | `httpx-retries` | Transport-level `allowed_methods` is HTTP-method-only — matriz `new_order` is HTTP GET (Primary API quirk) → mutation gate via method allowlist would silently retry order creation. `tenacity` `retry=` predicate + `request.extensions["idempotent"]` is the correct gate level. (Detailed in `.planning/research/STACK.md` §A.) |
| `tenacity` | `backoff` | Stale (last release 2022-10-05), no `py.typed` → breaks mypy strict. (`.planning/research/STACK.md` §A.) |
| `tenacity` | Roll-our-own transport | ~150 LOC × 4 packages = 600 LOC vs ~3 LOC per call-site with tenacity. (`.planning/research/STACK.md` §A.) |
| stdlib `logging` | `structlog` 26.x | `structlog.configure()` is process-global — library code calling it would clobber consumer apps. Adds runtime dep × 4 packages. (`.planning/research/STACK.md` §B.) |
| stdlib `logging` | `loguru` | Global `from loguru import logger` mutates process-wide state. Windows-only sub-deps (`colorama`, `win32-setctime`). (`.planning/research/STACK.md` §B.) |
| `request.extensions["idempotent"]` | HTTP-method-based gate (`request.method in {"GET", "HEAD"}`) | matriz `build_new_order_request` returns `RequestSpec(method="GET", path="/rest/order/newSingleOrder", ...)` — method gate WOULD retry on 503 → duplicate order risk. The explicit builder flag is non-negotiable. |
| Custom Wait subclass for Retry-After | Inspect `Retry-After` header inside `handle_request` before raising sentinel | A custom `wait_retry_after(fallback=wait_exponential_jitter(...))` subclass that reads `retry_state.outcome.result()` is cleaner — separates concerns. See §"Architecture Patterns" Pattern 2. Either approach is acceptable per Claude's Discretion. |

**Installation (per-package, applied to 4 packages):**

```bash
# Each package pyproject.toml [project] dependencies:
#   "tenacity>=9.1.0,<10"

uv add --package iol-client "tenacity>=9.1.0,<10"
uv add --package higyrus-client "tenacity>=9.1.0,<10"
uv add --package ambito-financiero-client "tenacity>=9.1.0,<10"
uv add --package matriz-client "tenacity>=9.1.0,<10"
uv sync --all-packages --all-extras --dev --frozen
```

**Version verification (confirmed during this research):**

```bash
$ uv run --with tenacity python -c "import importlib.metadata; print(importlib.metadata.version('tenacity'))"
9.1.4

$ uv run --with tenacity python -c "from tenacity import Retrying, AsyncRetrying, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type, retry_if_result; print('OK')"
OK
```

[VERIFIED: tenacity 9.1.4 importable, exposes all APIs Phase 8 needs. Release date verified via PyPI JSON metadata.]

## Package Legitimacy Audit

The only NEW external dependency in Phase 8 is `tenacity`. All other packages (httpx, pytest, pytest-asyncio, pytest-httpx) are existing.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `tenacity` | PyPI | 12+ years (first release ~2014) | ~50M/month per PyPI metadata | github.com/jd/tenacity | `[OK]` (confirmed via `slopcheck install tenacity`) | **Approved** — `py.typed` confirmed, Apache-2.0, zero runtime deps, 9.1.4 (released within current 12 months per readthedocs changelog), already vetted by `.planning/research/STACK.md` §A vs alternatives. |

**Packages removed due to slopcheck `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** none.

**Slopcheck output verbatim:**

```
slopcheck checking 1 package(s) on pypi before install...

  Installing: tenacity
  Running: pip install tenacity

  [OK] tenacity (pypi)

==================================================
  scanned 1 packages
  1 OK
```

Note: slopcheck's downstream `pip install` failed in this environment (no `pip` binary in the venv slopcheck ran in), but the legitimacy check ran to completion and reported `[OK]` for `tenacity` before the subprocess failure. Installation in the workspace is via `uv add --package <pkg> tenacity>=9.1.0,<10`, not pip, so the slopcheck install failure is environment-specific and does not affect the Phase 8 plan.

[VERIFIED: tenacity is the canonical Python retry library, used by countless projects including anthropic/openai SDKs (per `.planning/research/STACK.md` sources). Not a hallucination; not a slopsquat target.]

## Architecture Patterns

### System Architecture Diagram

```
                  Caller (top-level fn or Client.get_X())
                              │
                              ▼
                  Client._request(spec: RequestSpec)
                              │
              ┌───────────────┼───────────────┐
              │ 1. Generate   │ 2. Set        │ 3. _ensure_token()
              │    request_id │    extensions │    (skipped if
              │    = uuid4    │    idempotent │     spec.auth_basic)
              │               │    request_id │
              │               │    endpoint_  │
              │               │    name       │
              │               │    account_id │
              └───────────────┼───────────────┘
                              ▼
                  state.http_client.send(request)
                  (httpx.Client wired with RetryTransport)
                              │
                              ▼
              RetryTransport.handle_request(request)
              ┌───────────────────────────────────┐
              │  if not extensions["idempotent"]: │
              │      return super().handle(req)   │  ◄─── MUTATION GATE
              │                                   │       (D-01, RELY-03)
              │  for attempt in Retrying(         │
              │      stop=stop_after_attempt(N+1),│
              │      wait=wait_retry_after(       │
              │          fallback=wait_exp_jitter)│
              │      retry=retry_if_exc OR        │
              │            retry_if_result(       │
              │            status in {408,409,    │
              │              429, 5xx})           │
              │      reraise=True,                │
              │  ):                               │
              │      with attempt:                │
              │          resp = super().handle(   │
              │              request)             │
              │          resp.read()              │
              │          if retryable_status:     │
              │              raise _RetryableSt(resp)│
              │          return resp              │
              │                                   │
              │  # Emit WARNING per retry attempt │
              │  # Emit DEBUG req/resp            │
              │  # Emit ERROR on terminal failure │
              └───────────────────────────────────┘
                              │
                              ▼ httpx.Response
              Client._request continues:
                              │
                              ▼
              try:  _raise_for_response(resp)
              except <Pkg>AuthError:                 ◄─── 401 RE-AUTH ONCE
                  if spec.auth_basic is not None:        (D-02, RELY-04)
                      raise  # Risk API: no re-auth     (D-23)
                  state.token = None
                  _ensure_token()
                  request.headers["Auth"] = ...refresh
                  resp = state.http_client.send(request) (D-29 — login goes
                  _raise_for_response(resp)              through RetryTransport
              return resp                                 too)
                              │
                              ▼ httpx.Response
              Caller: _core.parse_<endpoint>_response(resp)
                              │
                              ▼ typed result (dict/list/Model)


    Logging side-channel (all stages):
        logging.getLogger("<pkg>") + NullHandler (in __init__.py)
                              │
                              ▼
        RedactingFilter — scrubs:
          • Bearer xxx  → Bearer ***
          • X-Auth-Token: xxx → X-Auth-Token: ***
          • password=xxx → password=***
          • "password":"xxx" → "password":"***"
          • IOL refresh_token=xxx → refresh_token=***
          • matriz auth_basic password
                              │
                              ▼
        Consumer-attached handler (NOT our concern)
        - logging.root.handlers MUST be untouched (LOG-01)
```

### Recommended Project Structure (per package)

```
packages/<pkg>/src/<pkg>/
├── __init__.py          # Re-exports; attaches NullHandler + RedactingFilter
├── _state.py            # _ClientState (unchanged; http_client now holds Client with RetryTransport)
├── _core.py             # RequestSpec gains `endpoint_name` + (higy/matriz) `account_id`;
│                        # builders mark `idempotent=True` for GETs + login/refresh
├── _transport.py        # NEW — RetryTransport(httpx.HTTPTransport) with tenacity loop
├── _atransport.py       # NEW (except matriz — D-25) — AsyncRetryTransport
├── _logging.py          # NEW — RedactingFilter(logging.Filter) + attach()
├── client.py            # Shell adds: request_id gen, extensions, 401 re-auth-once, log calls
├── aio.py               # Shell mirror (matriz aio.py stays stub Phase 6 — D-25)
├── exceptions.py        # UNCHANGED — Phase 8 does not touch exception hierarchy
└── (models.py, types.py, etc. — UNCHANGED per package)
```

### Pattern 1: `RetryTransport` core loop (D-01, D-31)

**What:** subclass `httpx.HTTPTransport` (and `httpx.AsyncHTTPTransport`) per package; gate mutation via `request.extensions["idempotent"]`; wrap retry logic in tenacity's `Retrying`/`AsyncRetrying` iterator.

**When to use:** Every Plan 2-5 (per package). The pattern is duplicated 4× verbatim with package-specific imports.

**Example (sync canary — ambito Plan 2):**

```python
# Source: tenacity 9.1.4 — verified via `inspect.getsource(Retrying)` + `inspect.getsource(AttemptManager)`
# Source: httpx 0.27+ — BaseTransport.handle_request signature
from __future__ import annotations

import logging
import time
import uuid
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from tenacity import (
    Retrying,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential_jitter,
)

from ambito_financiero_client import _logging  # for the per-package logger

_RETRYABLE_EXC = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
)
_RETRYABLE_STATUS = frozenset({408, 409, 429, *range(500, 600)})
_RETRY_AFTER_CAP_S = 60.0


class _RetryableStatus(Exception):
    """Internal sentinel: signals a retryable status code to the tenacity loop.

    NOT a subclass of any <Pkg>APIError — keeps D-07 invariant (domain
    exceptions never in retry_on=).
    """

    def __init__(self, response: httpx.Response) -> None:
        super().__init__(f"retryable status: {response.status_code}")
        self.response = response


def _is_retryable_status(response: httpx.Response | None) -> bool:
    return response is not None and response.status_code in _RETRYABLE_STATUS


def _parse_retry_after(value: str) -> float | None:
    """Parse RFC 9110 §10.2.3 Retry-After (delta-seconds OR HTTP-date)."""
    try:
        return float(value)
    except ValueError:
        try:
            target = parsedate_to_datetime(value).timestamp()
            return max(0.0, target - time.time())
        except (TypeError, ValueError):
            return None


class RetryTransport(httpx.HTTPTransport):
    """`httpx.HTTPTransport` subclass with bounded retries + full-jitter backoff.

    D-01 — Gate: `request.extensions["idempotent"]` set by the shell
    `_request()` from `RequestSpec.idempotent`. Non-idempotent → pass-through.

    D-07 — `retry_on`: HTTP 408/409/429/5xx and httpx ConnectError /
    ConnectTimeout / ReadTimeout. Domain exceptions never reach this layer
    (the shell `_request()` calls `_raise_for_response` AFTER `handle_request`).

    D-04 — `Retry-After` honored with cap 60 s (delta-seconds + HTTP-date).
    """

    def __init__(self, *, max_attempts: int = 2, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._max_attempts = max(max_attempts, 1)
        self._logger = logging.getLogger("ambito_financiero_client")

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if not request.extensions.get("idempotent", False):
            return super().handle_request(request)
        if self._max_attempts <= 1:
            return super().handle_request(request)

        request_id = request.extensions.get("request_id", "")
        endpoint_name = request.extensions.get("endpoint_name", "")
        account_id = request.extensions.get("account_id")
        start = time.monotonic()
        attempt_number = 0

        last_exc: BaseException | None = None
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(self._max_attempts),
                wait=wait_exponential_jitter(
                    initial=1.0, max=30.0, exp_base=2, jitter=1.0
                ),
                retry=(
                    retry_if_exception_type(_RETRYABLE_EXC)
                    | retry_if_exception_type(_RetryableStatus)
                ),
                reraise=True,
            ):
                with attempt:
                    attempt_number = attempt.retry_state.attempt_number
                    response = super().handle_request(request)
                    response.read()  # body-consume before status check
                    if _is_retryable_status(response):
                        # honor Retry-After cap 60s before re-raising
                        retry_after = response.headers.get("Retry-After")
                        if retry_after is not None:
                            delay = _parse_retry_after(retry_after)
                            if delay is not None and delay > 0:
                                time.sleep(min(delay, _RETRY_AFTER_CAP_S))
                        self._logger.warning(
                            "retry attempt",
                            extra={
                                "package": "ambito_financiero_client",
                                "method": request.method,
                                "url": str(request.url),
                                "status_code": response.status_code,
                                "attempt": attempt_number,
                                "request_id": request_id,
                                "endpoint_name": endpoint_name,
                                "retry_reason": f"status_{response.status_code}",
                                **({"account_id": account_id} if account_id else {}),
                            },
                        )
                        raise _RetryableStatus(response)
                    return response
        except _RetryableStatus as exc:
            return exc.response  # exhausted — return last response unmolested
        except _RETRYABLE_EXC as exc:
            last_exc = exc
            duration_ms = int((time.monotonic() - start) * 1000)
            self._logger.error(
                "retry exhausted (transport error)",
                extra={
                    "package": "ambito_financiero_client",
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": None,
                    "attempt": attempt_number,
                    "duration_ms": duration_ms,
                    "request_id": request_id,
                    "endpoint_name": endpoint_name,
                },
                exc_info=False,
            )
            raise
```

### Pattern 2: `Retry-After` custom Wait (alternative to inline parsing)

**What:** Subclass `tenacity.wait_base` to inspect `retry_state.outcome.result()` for the `Retry-After` header before falling back to exponential-jitter. Cleaner separation of concerns.

**When to use:** If the planner prefers a tenacity-native shape over inline `time.sleep` inside `handle_request`. Either approach satisfies D-04.

**Example:**

```python
# Source: https://zeitbach.com/blog/2024/08/15/honoring-the-retry-after-header-with-tenacity
# Adapted: only triggers on 429/503 — other 5xx use fallback
from tenacity import wait_base, RetryCallState
from tenacity.wait import wait_exponential_jitter


class wait_retry_after(wait_base):
    def __init__(self, fallback: wait_base, *, cap_s: float = 60.0) -> None:
        self.fallback = fallback
        self.cap_s = cap_s

    def __call__(self, retry_state: RetryCallState) -> float:
        outcome = retry_state.outcome
        if outcome is not None and outcome.failed:
            exc = outcome.exception()
            if isinstance(exc, _RetryableStatus):
                response = exc.response
                if response.status_code in (429, 503):
                    retry_after = response.headers.get("Retry-After")
                    if retry_after is not None:
                        delay = _parse_retry_after(retry_after)
                        if delay is not None:
                            return min(max(delay, 0.0), self.cap_s)
        return self.fallback(retry_state)


# Usage inside RetryTransport.handle_request:
#   wait=wait_retry_after(
#       fallback=wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0),
#       cap_s=_RETRY_AFTER_CAP_S,
#   )
```

**Note for planner:** the tenacity custom-wait approach requires `attempt.retry_state.set_result(response)` to be called before raising the sentinel — OR the sentinel exception's `response` attribute must be inspected via `outcome.exception().response`. The example above uses the latter (cleaner).

### Pattern 3: 401 re-auth-once boundary in shell `_request()` (D-02, D-23, RELY-04)

**What:** The shell `_request()` catches the typed `<Pkg>AuthError` raised by `_raise_for_response` AFTER `handle_request` returns. Resets `state.token`, calls `_ensure_token()`, re-sends with refreshed Authorization header, and re-checks. NEVER includes `AuthError` in the transport's `retry_on=` predicate.

**When to use:** All 3 auth packages (iol, higyrus, matriz). Skip for ambito (no auth). matriz Risk API special-cases: if `spec.auth_basic is not None`, re-raise `AuthError` immediately (D-23).

**Example (iol — the most complex auth flow):**

```python
# Source: synthesized from CONTEXT.md D-02 + D-23 + D-29 + existing iol client.py:_request structure
from iol_client._core import RequestSpec
from iol_client.exceptions import IOLAuthError


def _request(self, spec: RequestSpec) -> httpx.Response:
    self._ensure_token()
    assert self._state.token is not None  # mypy narrowing

    request_id = uuid.uuid4().hex
    http = self._ensure_http_client()
    url = f"{self._state.base_url}{spec.path}"
    headers = {
        "Authorization": f"Bearer {self._state.token}",
        **(spec.headers or {}),
    }
    req = http.build_request(
        spec.method,
        url,
        params=spec.params,
        json=spec.json_body,
        headers=headers,
    )
    req.extensions["idempotent"] = spec.idempotent
    req.extensions["request_id"] = request_id
    req.extensions["endpoint_name"] = spec.endpoint_name
    if getattr(spec, "account_id", None) is not None:
        req.extensions["account_id"] = spec.account_id

    resp = http.send(req)
    try:
        _raise_for_response(resp)
    except IOLAuthError:
        # D-23 Risk API exclusion (iol has no Risk API — but the pattern is uniform).
        if getattr(spec, "auth_basic", None) is not None:
            raise
        # D-02: exactly-one re-auth attempt.
        self._state.token = None
        self._ensure_token()
        assert self._state.token is not None
        req.headers["Authorization"] = f"Bearer {self._state.token}"
        resp = http.send(req)
        _raise_for_response(resp)
    return resp
```

### Pattern 4: Library logging contract (LOG-01)

**What:** `__init__.py` adjuncts `NullHandler` + `RedactingFilter` to the package logger. Never `logging.basicConfig`. Never `logging.root` calls.

**When to use:** Every package's `__init__.py`. The attach is idempotent (re-import does not duplicate handlers — `addHandler` is a no-op for `NullHandler` instances by identity check via `not any(isinstance(h, logging.NullHandler) for h in logger.handlers)`).

**Example:**

```python
# Source: Python Logging HOWTO — "Configuring logging for a library"
# packages/iol-client/src/iol_client/__init__.py
from iol_client import _logging
_logging.attach()
# Local import is NOT re-exported in __all__ — internal wiring only.
del _logging
```

```python
# packages/iol-client/src/iol_client/_logging.py
from __future__ import annotations

import logging
import re

_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._\-]+")
_X_AUTH_TOKEN_RE = re.compile(r"(X-Auth-Token\s*:\s*)[A-Za-z0-9._\-]+", re.IGNORECASE)
_PASSWORD_URLENC_RE = re.compile(r"(password=)[^&\s]+")
_PASSWORD_JSON_RE = re.compile(r'("password"\s*:\s*")[^"]+(")')
_REFRESH_TOKEN_URLENC_RE = re.compile(r"(refresh_token=)[^&\s]+")
_REFRESH_TOKEN_JSON_RE = re.compile(r'("refresh_token"\s*:\s*")[^"]+(")')


def _redact(text: str) -> str:
    text = _BEARER_RE.sub("Bearer ***", text)
    text = _X_AUTH_TOKEN_RE.sub(r"\1***", text)
    text = _PASSWORD_URLENC_RE.sub(r"\1***", text)
    text = _PASSWORD_JSON_RE.sub(r"\1***\2", text)
    text = _REFRESH_TOKEN_URLENC_RE.sub(r"\1***", text)
    text = _REFRESH_TOKEN_JSON_RE.sub(r"\1***\2", text)
    return text


class RedactingFilter(logging.Filter):
    """Scrub credential substrings from log records before emission.

    D-10: rewrites `record.msg`/`record.args`/`record.__dict__` values in-place.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: _redact(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            else:
                record.args = tuple(
                    _redact(a) if isinstance(a, str) else a for a in record.args
                )
        # Scan record.__dict__ values for string leaks in extra=.
        for key, value in list(record.__dict__.items()):
            if isinstance(value, str) and any(
                marker in value for marker in ("Bearer ", "password=", "refresh_token=", "X-Auth-Token")
            ):
                record.__dict__[key] = _redact(value)
        return True


def attach() -> None:
    """Attach NullHandler + RedactingFilter to the package logger."""
    logger = logging.getLogger("iol_client")
    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(RedactingFilter())
```

### Pattern 5: Structured `extra={}` field naming (LOG-03)

**What:** Use non-colliding keys for `extra=` kwargs. Verified against `logging.LogRecord` reserved attribute list (Pitfall 17 prevention).

**Locked field names (D-09):**

| Field | Type | Origin | Notes |
|-------|------|--------|-------|
| `package` | `str` | constant per package | e.g., `"iol_client"`. |
| `method` | `str` | `request.method` | `GET` / `POST` / etc. |
| `url` | `str` | `str(request.url)` | Query-string already URL-encoded by httpx; redaction handled by `RedactingFilter` for tokens-in-query. |
| `status_code` | `int \| None` | `response.status_code` | `None` for transport errors (no response). |
| `attempt` | `int` | `attempt.retry_state.attempt_number` | 1-indexed. Same `request_id` across attempts (D-30). |
| `duration_ms` | `int` | `int((time.monotonic() - start) * 1000)` | Per-attempt OR per-business-call — planner decides; recommendation: per-business-call (matches log emission point). |
| `request_id` | `str` | `uuid.uuid4().hex` generated UNA vez in shell `_request()` | Same across all retry attempts (D-30). |
| `endpoint_name` | `str` | `RequestSpec.endpoint_name` set by builder | e.g., `"get_segments"`, `"get_listado_cuentas"`. |
| `account_id` | `str` (conditional) | `RequestSpec.account_id` (higyrus + matriz only) | Omitted if `None`. |
| `retry_reason` | `str` (WARNING only) | e.g., `"status_503"`, `"connect_error"`, `"401_reauth"` | Distinguishes retry trigger. |

**Reserved attribute list verified (will NOT collide):** `asctime`, `created`, `exc_info`, `exc_text`, `filename`, `funcName`, `levelname`, `levelno`, `lineno`, `message`, `module`, `msecs`, `msg`, `name`, `pathname`, `process`, `processName`, `relativeCreated`, `stack_info`, `thread`, `threadName`. [CITED: Python logging documentation, `logging.LogRecord` attribute table]

### Anti-Patterns to Avoid

- **`retry_on=` includes `<Pkg>AuthError` or `<Pkg>APIError`:** Pitfall 5 — would loop on expired tokens with stale header. The shell `_request()` owns 401 re-auth-once; transport sees only transport-level signals. (D-07, RELY-04)
- **HTTP-method-based mutation gate:** matriz `new_order` is HTTP `GET`. Method allowlist (`{"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}` as default in httpx-retries) would silently retry order creation → duplicate orders. The locked gate is `request.extensions["idempotent"]` set by the builder. (Pitfall 4, RELY-03)
- **`logging.basicConfig()` in library code:** Pitfall 6 — clobbers downstream apps' log config. Use `NullHandler` only. CI grep step in `.github/workflows/ci.yml` enforces. (LOG-01, D-27)
- **`logging.root.addHandler(...)` or `logging.root.setLevel(...)`:** Same hijack risk. Ruff LOG015 + grep step blocks. (LOG-01)
- **`logger.debug(f"Authorization: {req.headers['Authorization']}")`:** Even without `extra=`, the f-string formats the token into `record.msg`. The `RedactingFilter` MUST run on `record.msg` (D-10). (Pitfall 7, LOG-02)
- **`extra={"message": "...", "name": "..."}`:** `LogRecord` reserved attribute collision — raises `KeyError` at runtime. Use prefixed names from D-09 only. (Pitfall 17)
- **`asyncio.sleep` replaced with `time.sleep` in async path:** Blocks the event loop AND swallows `asyncio.CancelledError`. tenacity's `AsyncRetrying.__call__` uses `await self.sleep(do)` natively — keep it that way. (Pitfall 16, D-32)
- **Importing `verification/redaction.py` from `_logging.py`:** `verification/` is harness-only (not packaged). Each package gets its own redaction patterns. (D-10, Pitfall 7)
- **Re-running `attach()` adds duplicate `NullHandler` / `RedactingFilter`:** Idempotency check via `not any(isinstance(h, logging.NullHandler) for h in logger.handlers)` is mandatory. (LOG-01)
- **Mutating `state.token` inside `RetryTransport.handle_request`:** Transport must be stateless wrt domain auth. Shell owns the auth state. (D-02)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry loop with exponential backoff + jitter + max-attempts | Custom `while attempts < N: try: ... except: time.sleep(...); attempts += 1` | `tenacity.Retrying` / `AsyncRetrying` | tenacity handles edge cases (`reraise`, predicates, `before_sleep` hooks, full-jitter math) tested across millions of installs. (See `.planning/research/STACK.md` §A; D-31.) |
| Mutation gate per request | HTTP-method allowlist (`if method == "GET": retry`) | `request.extensions["idempotent"]` set by `RequestSpec.idempotent` | matriz `new_order` uses HTTP `GET` (Primary API quirk) — method gate would silently retry order creation. Explicit builder flag is non-negotiable. (RELY-03, D-01) |
| `Retry-After` parsing | Custom int/datetime parser | `email.utils.parsedate_to_datetime` (stdlib) for HTTP-date + `float()` for delta-seconds | RFC 9110 §10.2.3 defines both forms; stdlib already covers both. (D-04) |
| Credential redaction in logs | `re.sub(r"Bearer .*", "***", msg)` ad-hoc per call site | `logging.Filter` subclass attached to the package logger | Filter runs on EVERY record automatically, including records emitted by downstream consumers using the same logger name. Ad-hoc redaction misses log records emitted by future code. (LOG-02, D-10) |
| Per-business-call request correlation | Compute `request_id` per attempt | `uuid.uuid4().hex` UNA vez in shell `_request()`, propagated via `request.extensions["request_id"]` | Same `request_id` across retries lets grep correlate naturally; `attempt` field distinguishes. (D-30) |
| Async retry with `time.sleep` | Custom `asyncio.sleep(2 ** n)` loop | `tenacity.AsyncRetrying` (uses native `await self.sleep(do)` — verified via source inspection) | Respects `asyncio.CancelledError` propagation. (D-32, Pitfall 16) |
| Test setup for retry behavior | Custom transport mock | `pytest-httpx` `httpx_mock.add_response(status_code=503)` repeated × N | Existing dev-dep. `httpx_mock.get_requests()` returns the wire-request list for count assertions. (D-26) |
| Login flow retry | Custom retry inside `_ensure_token()` | Mark `build_login_request` / `build_refresh_request` with `idempotent=True`; let `RetryTransport` handle it uniformly | login = "give me a token with these credentials" — replay-safe. 5xx transient blip → retry. 401 → `AuthError` immediate (no recursive re-auth, the shell re-auth attempt happens UNA vez per business call). (D-03, D-29) |

**Key insight:** Phase 8 is a layering exercise — the architecture from Phase 7 (`_core.py` builders, `_request(spec)` shell) is the foundation; tenacity sits between the shell and the wire as a transport subclass; `_logging.py` and `RedactingFilter` sit beside the package logger. Every "should I build this?" answer is NO — the standard primitives already exist. The only legitimate "build it" is the 4× duplication mandated by the no-shared-internals constraint.

## Common Pitfalls

### Pitfall 1: Retry includes `AuthError` → infinite loop on expired token

**What goes wrong:** `retry=retry_if_exception_type((IOLAuthError, httpx.ConnectError, ...))` would cause tenacity to retry on 401. The retry sends the SAME `Authorization: Bearer <expired>` header (transport does not refresh tokens). Server returns 401 again. tenacity hits `max_attempts`, then raises `IOLAuthError` after `2^N` seconds of pointless backoff.

**Why it happens:** Library authors instinctively put "common errors" in `retry_on`. `AuthError` looks common — but it's a domain-level signal, not transport-level.

**How to avoid:** D-07 LOCKED: `retry_on=` ONLY includes `httpx.ConnectError`, `httpx.ConnectTimeout`, `httpx.ReadTimeout` exceptions and status codes `408/409/429/≥500` via `retry_if_result(_is_retryable_status)` (or the `_RetryableStatus` sentinel). NEVER `<Pkg>AuthError`. The shell `_request()` catches `AuthError` POST-handle_request and does exactly-one re-auth + re-send (D-02).

**Warning signs:** Test `test_retry_401_reauth.py` (D-26) sees > 2 wire requests on 401→401 chain. Logs show repeating WARNING with identical Authorization header.

### Pitfall 2: matriz `new_order` retries on 503 → duplicate order

**What goes wrong:** matriz Primary API uses HTTP `GET` for order creation. A method-based mutation gate (`if request.method in {"GET", "HEAD"}: retry`) would silently retry `new_order` on 503. First request may have succeeded server-side (broker matched the order). Second retry creates a duplicate.

**Why it happens:** httpx-retries and similar libraries use method allowlists. Defaulting to "retry GETs" is universally safe — EXCEPT for this specific Primary API quirk.

**How to avoid:** D-01 LOCKED: mutation gate is `request.extensions["idempotent"]` set by the shell `_request()` from `RequestSpec.idempotent`. `build_new_order_request` returns `RequestSpec(method="GET", path="/rest/order/newSingleOrder", idempotent=False)` — the GET method does NOT override the explicit `idempotent=False`. Transport pass-through (no retry loop) when not idempotent.

**Warning signs:** `verification/test_retry_mutation_gate.py` (D-26) sees > 1 wire request when mock 503 against `pkg.new_order(...)`. Live `main_matriz.py --mutating` reports duplicate `clOrdId` findings.

### Pitfall 3: `logger.debug(req.headers)` leaks token in DEBUG

**What goes wrong:** `logger.debug("request: %s", req)` interpolates `req.headers["Authorization"] = Bearer abc123` into `record.args[0]`. Consumer enables DEBUG (`logging.getLogger("iol_client").setLevel(logging.DEBUG)`). Bearer token leaks to Sentry / Datadog / CloudWatch via consumer's handler.

**Why it happens:** Library author rationalizes "it's only DEBUG" — but production DEBUG enablement is routine for diagnostics.

**How to avoid:** D-10 LOCKED: `RedactingFilter` attached to package logger via `attach()` in `__init__.py`. Filter rewrites `record.msg` (string), `record.args` (tuple/dict), AND `record.__dict__` values BEFORE emission. Patterns cover Bearer / X-Auth-Token / `password=` / JSON `"password":"..."` / IOL refresh_token. Test `verification/test_logging_no_token_leak.py` (D-26) configures `token="SECRET-LITERAL-12345"` and asserts NO record contains the literal — even with DEBUG enabled.

**Warning signs:** `caplog.records` in tests show Bearer with full token. Production log aggregator alerts for "JWT detected in log message".

### Pitfall 4: `logging.basicConfig` in library code hijacks consumer

**What goes wrong:** Developer adds `logging.basicConfig(level=logging.INFO, format=...)` to `__init__.py`. Every consumer that imports the package loses their root logger config. FastAPI apps lose JSON log structure. uvicorn access logs change format.

**Why it happens:** `logging.basicConfig` is the first example in the Python logging tutorial. Carried over from app-code experience.

**How to avoid:** LOG-01 LOCKED: ONLY `NullHandler` attached. NEVER `logging.basicConfig`, NEVER `logging.root.addHandler/setLevel`. CI guard via combo of:
- **ruff LOG015** (`root-logger-call`) — catches `logging.root.<anything>` direct calls.
- **explicit grep step in `.github/workflows/ci.yml`** — catches `logging.basicConfig` (which ruff LOG rules do NOT cover, verified at docs.astral.sh/ruff).
- **regression test `verification/test_logging_root_unchanged.py`** (D-26) — captures `logging.root.handlers` before `import <pkg>` and asserts unchanged.

**Warning signs:** Consumer bug reports about log format changes after upgrading. CI grep step fails. Regression test fails.

### Pitfall 5: `asyncio.CancelledError` swallowed by retry loop

**What goes wrong:** Custom async retry uses `try: ... except Exception: time.sleep(2 ** n)`. `CancelledError` is `BaseException` in Python 3.8+ — caught by `except Exception` is fine — BUT `time.sleep` blocks the event loop AND CancelledError raised during sleep window does NOT propagate. Ctrl-C / `wait_for` timeout takes the full backoff budget to surface.

**Why it happens:** Authors who learned retry patterns from sync code carry the `time.sleep` instinct to async.

**How to avoid:** D-32 LOCKED: `AsyncRetryTransport.handle_async_request` uses `tenacity.AsyncRetrying` — the `__call__` impl uses `await self.sleep(do)` which is `asyncio.sleep` by default. `asyncio.CancelledError` propagates naturally (verified empirically in this research session via:

```bash
$ uv run --with tenacity python <test_cancellation_through_AsyncRetrying.py>
Cancelled during sleep — propagated correctly
```

— see Verification Notes below). Test `verification/test_async_cancellation.py` (D-26): `asyncio.wait_for(client.get_X(), timeout=0.5)` + mock 503→503 → `TimeoutError` raised within ~500ms, not after full retry budget.

**Warning signs:** Test takes longer than the `wait_for` timeout. Cancellation in production hangs requests until retry exhaustion.

### Pitfall 6: `extra={}` key collides with `LogRecord` reserved attribute

**What goes wrong:** `logger.info("done", extra={"message": "OK"})` raises `KeyError: "Attempt to overwrite 'message' in LogRecord"`. Only surfaces when the logger is actually configured (passes through tests with `NullHandler`).

**Why it happens:** "Message" / "name" / "module" are intuitive but reserved.

**How to avoid:** D-09 field set (`package`, `method`, `url`, `status_code`, `attempt`, `duration_ms`, `request_id`, `endpoint_name`, `account_id`, `retry_reason`) verified against the reserved attribute list (`asctime`, `created`, `exc_info`, `exc_text`, `filename`, `funcName`, `levelname`, `levelno`, `lineno`, `message`, `module`, `msecs`, `msg`, `name`, `pathname`, `process`, `processName`, `relativeCreated`, `stack_info`, `thread`, `threadName`) — none of the Phase 8 keys collide.

**Warning signs:** Random `KeyError` in production after enabling a non-NullHandler. Tests that use `caplog` (which configures a real handler) catch this.

### Pitfall 7: Token race during refresh in async (Pre-Phase-10 / NOT this phase)

**What goes wrong:** Async client refresh-token chain has N concurrent requests on expired token → N parallel logins. Not a Phase 8 concern for sync (`Client._ensure_token()` is single-threaded) and async iol/higyrus already have `asyncio.Lock` per state (Phase 6 work). matriz async REST is Phase 10 (TokenStore 3-way required).

**Why it happens (Phase 10 territory):** sync Client + async Client + ws_client daemon thread all reading/writing `_state.token`.

**How to avoid (Phase 8):** N/A — matriz `_atransport.py` deferred to Phase 10 (D-25). For iol/higyrus async: existing Phase 6 `asyncio.Lock` covers; Phase 8 adds RetryTransport ON TOP of that lock — no new race introduced.

**Warning signs (Phase 10 only):** Logs show > 1 login attempt per business-call burst. matriz integration tests show intermittent 401 after `AsyncClient.get_X()` + concurrent `ws_client` subscription.

### Pitfall 8: Snapshot diff "explodes" because `__init__.py` import of `_logging.attach()` adds attribute

**What goes wrong:** `verification/test_public_surface.py` enumerates `pkg.__all__` symbols. If `__init__.py` imports `_logging` and the `del _logging` cleanup is missed, `pkg._logging` becomes a module attribute. Snapshot diff flags it as new surface.

**Why it happens:** Developer forgets to `del _logging` after `attach()`.

**How to avoid:** Pattern 4 above uses `from <pkg> import _logging; _logging.attach(); del _logging`. The `del` removes the module attribute. Verified pattern: existing `from iol_client.aio import AsyncClient` in `__init__.py` does NOT leak `aio` as a top-level attr (it's still accessible via `iol_client.aio`, but NOT in `__all__`).

**Warning signs:** `test_public_surface_matches_snapshot[iol_client]` fails with `_logging : module : ...` diff line.

### Pitfall 9: `request.extensions` mutation across retries

**What goes wrong:** `request.extensions["request_id"]` set by shell before first `send()`. After retry, the SAME `httpx.Request` object is reused — extensions dict is shared. If `RetryTransport` mutates `extensions["attempt"]`, the value leaks back to the shell.

**Why it happens:** `httpx.Request.extensions` is a regular dict — by-reference.

**How to avoid:** Treat `request.extensions` as **read-only inside the transport** (D-01). Only the shell `_request()` writes (`idempotent`, `request_id`, `endpoint_name`, `account_id`). The transport reads. `attempt_number` is a local variable inside `handle_request`, NOT written to extensions.

**Warning signs:** Test `test_retry_401_reauth.py` reports inconsistent `request_id` values across attempts. Hard to debug — extensions leak is silent.

## Runtime State Inventory

Not applicable to Phase 8. Phase 8 is a greenfield addition (3 new module types per package) + 2 minor changes (`RequestSpec` field extensions in `_core.py`; `Client.__init__`/`configure()` signature extension). No rename / refactor / migration → no runtime state inventory.

## Code Examples

### Mutation gate guard test (D-26 — verification/test_retry_mutation_gate.py)

```python
# Source: synthesized from CONTEXT.md D-26 + existing verification/test_sync_async_isolation.py shape
from __future__ import annotations

import importlib

import pytest
from pytest_httpx import HTTPXMock

# matriz POST builders use HTTP GET (Primary API quirk) — mutation gate
# MUST be via RequestSpec.idempotent, not method.
_MUTATING_CALLS: list[tuple[str, str, dict]] = [
    (
        "iol_client",
        "_get_default()._request",  # iol has no built-in mutating endpoint;
        # planner picks the lowest-level mutating path (TODO at plan time)
        {},
    ),
    (
        "matriz_client",
        "new_order",  # matriz Primary API HTTP GET — but idempotent=False
        {"symbol": "GGAL", "side": "BUY", "qty": 1, "account": "test", "price": 100.0},
    ),
    # ámbito + higyrus mutating paths added at plan time per planner discretion.
]


@pytest.mark.parametrize(("pkg_name", "method_name", "kwargs"), _MUTATING_CALLS)
def test_mutating_call_never_retries_against_503(
    pkg_name: str,
    method_name: str,
    kwargs: dict,
    httpx_mock: HTTPXMock,
) -> None:
    """RELY-03: mutating POST (or matriz HTTP GET with idempotent=False) MUST emit
    exactly 1 wire request even against mock 503.

    Failure means the mutation gate is broken — duplicate orders / writes risk.
    """
    pkg = importlib.import_module(pkg_name)
    pkg.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )

    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)  # safety net — would be matched on retry

    fn = getattr(pkg, method_name)
    with pytest.raises(Exception):  # AuthError/APIError/RateLimitError — any
        fn(**kwargs)

    requests = httpx_mock.get_requests()
    assert len(requests) == 1, (
        f"{pkg_name}.{method_name} emitted {len(requests)} wire requests against "
        f"503 — mutation gate broken. Expected exactly 1."
    )
```

### 401 re-auth-once guard test (D-26 — verification/test_retry_401_reauth.py)

```python
# Source: synthesized from CONTEXT.md D-02, D-23, D-26 + existing test_sync_async_isolation.py
from __future__ import annotations

import importlib

import pytest
from pytest_httpx import HTTPXMock


# Risk API endpoints get NO re-auth retry (D-23) — matriz Risk excluded
_AUTH_PACKAGES = ["iol_client", "higyrus_client", "matriz_client"]


@pytest.mark.parametrize("pkg_name", _AUTH_PACKAGES)
def test_401_then_200_triggers_exactly_one_reauth(
    pkg_name: str,
    httpx_mock: HTTPXMock,
) -> None:
    """RELY-04: 401 → 200 chain emits exactly 2 wire requests with refreshed header.

    First request: original token (stale). Server returns 401.
    Shell catches AuthError, clears state.token, calls _ensure_token() (which
    triggers another wire request — login flow).
    Then re-sends original request with the NEW token. Server returns 200.

    Wire request count: 1 (original 401) + 1 (login) + 1 (retry with new token) = 3.
    Initial `token=` kwarg pre-populates state.token so _ensure_token skips
    the first time — but on 401, state.token=None forces re-login.
    """
    pkg = importlib.import_module(pkg_name)
    pkg.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="STALE-TOKEN",
        token_expires_at=9_999_999_999.0,
    )

    # 1st: 401 with stale token. 2nd: 200 from login flow. 3rd: 200 with fresh token.
    if pkg_name == "iol_client":
        httpx_mock.add_response(status_code=401)
        httpx_mock.add_response(
            url="https://api.test/token",
            json={"access_token": "FRESH-TOKEN", "expires_in": 900, "refresh_token": "R"},
        )
        httpx_mock.add_response(json={"instrumentos": []})
        pkg.get_instruments("argentina")
    elif pkg_name == "higyrus_client":
        # ... analogous setup with /api/login and a sample GET ...
        pass  # planner fills in
    elif pkg_name == "matriz_client":
        # /auth/getToken returns X-Auth-Token header
        httpx_mock.add_response(status_code=401)
        httpx_mock.add_response(
            url="https://api.test/auth/getToken",
            headers={"X-Auth-Token": "FRESH-TOKEN"},
        )
        httpx_mock.add_response(json={"status": "OK", "segments": []})
        pkg.get_segments()

    requests = httpx_mock.get_requests()
    assert len(requests) == 3, (
        f"{pkg_name}: expected 3 wire requests (1 stale + 1 login + 1 fresh), got {len(requests)}"
    )
    # Last request must have FRESH-TOKEN in Authorization / X-Auth-Token.
    last = requests[-1]
    auth_header_value = last.headers.get("Authorization") or last.headers.get("X-Auth-Token")
    assert "FRESH-TOKEN" in (auth_header_value or "")
```

### No-token-leak in caplog (D-26 — verification/test_logging_no_token_leak.py)

```python
# Source: synthesized from CONTEXT.md D-10, D-22, D-26
from __future__ import annotations

import importlib
import logging

import pytest
from pytest_httpx import HTTPXMock

_SECRET_LITERAL = "SECRET-LITERAL-12345"
_PACKAGES = ["ambito_financiero_client", "iol_client", "higyrus_client", "matriz_client"]


@pytest.mark.parametrize("pkg_name", _PACKAGES)
def test_token_literal_never_appears_in_log_records(
    pkg_name: str,
    caplog: pytest.LogCaptureFixture,
    httpx_mock: HTTPXMock,
) -> None:
    """LOG-02: even with DEBUG enabled, token literal MUST NOT leak to records.

    Configures the package with a sentinel token, fires a mocked request,
    and asserts the literal does not appear in:
      - record.getMessage()  (covers msg + args interpolation)
      - record.args (raw tuple/dict)
      - record.__dict__ (extra= keys)
    """
    pkg = importlib.import_module(pkg_name)
    if pkg_name == "ambito_financiero_client":
        # no auth — pass sentinel via base_url instead
        pkg.configure(base_url=f"https://{_SECRET_LITERAL}.test")
    else:
        pkg.configure(
            base_url="https://api.test",
            username="u",
            password=_SECRET_LITERAL,
            token=_SECRET_LITERAL,
            token_expires_at=9_999_999_999.0,
        )

    caplog.set_level(logging.DEBUG, logger=pkg_name)

    # Fire smoke endpoint (planner picks per package)
    if pkg_name == "ambito_financiero_client":
        import datetime as dt
        httpx_mock.add_response(
            json=[["Fecha", "Compra", "Venta"], ["02/01/2026", "1.000,00", "1.100,00"]],
        )
        pkg.get_dollar_banco_nacion(dt.date(2026, 1, 2))
    elif pkg_name == "iol_client":
        httpx_mock.add_response(json={"instrumentos": []})
        pkg.get_instruments("argentina")
    # ... etc

    for record in caplog.records:
        message = record.getMessage()
        assert _SECRET_LITERAL not in message, (
            f"{pkg_name}: token literal leaked in record.getMessage(): {message!r}"
        )
        if record.args:
            args_str = str(record.args)
            assert _SECRET_LITERAL not in args_str, (
                f"{pkg_name}: token literal leaked in record.args: {args_str!r}"
            )
        for key, value in record.__dict__.items():
            if isinstance(value, str):
                assert _SECRET_LITERAL not in value, (
                    f"{pkg_name}: token literal leaked in record.{key}: {value!r}"
                )
```

### `_logging.attach()` with idempotency (verified pattern)

```python
# Source: Python Logging HOWTO + Phase 8 CONTEXT.md D-10 + existing __init__.py shape
# in packages/iol-client/src/iol_client/__init__.py
from iol_client import _logging
_logging.attach()
del _logging  # NOT re-exported


# in packages/iol-client/src/iol_client/_logging.py — see Pattern 4 above for full body
```

### `logging.root.handlers` unchanged regression test (D-26)

```python
# Source: synthesized from CONTEXT.md D-26 + Pitfall 6
from __future__ import annotations

import importlib
import logging


def test_importing_packages_does_not_modify_logging_root() -> None:
    """LOG-01: importing all 4 packages MUST NOT add handlers to logging.root.

    Library code MUST attach NullHandler to its own logger (e.g.,
    logging.getLogger("iol_client")), not to logging.root. This test
    captures logging.root.handlers before any import side effect runs
    in this process, then re-imports the 4 packages and asserts the
    list is unchanged.
    """
    before = list(logging.root.handlers)

    # Re-import (the packages are already imported via conftest.py side
    # effects, but the test still catches drift via the snapshot).
    for pkg_name in [
        "ambito_financiero_client",
        "iol_client",
        "higyrus_client",
        "matriz_client",
    ]:
        importlib.import_module(pkg_name)

    after = list(logging.root.handlers)
    assert after == before, (
        f"logging.root.handlers drifted after package import.\n"
        f"  before: {before!r}\n"
        f"  after:  {after!r}\n"
        f"Library code MUST attach NullHandler to its own logger only "
        f"(see CONTEXT.md D-13, D-14)."
    )
```

### CI grep step for `logging.basicConfig` (D-27 alternative b)

```yaml
# .github/workflows/ci.yml — add to lint job
      - name: Forbid logging.basicConfig in library code (Phase 8 LOG-01)
        run: |
          if grep -rn --include='*.py' 'logging\.basicConfig\|logging\.root' packages/*/src/; then
            echo "::error::Library code MUST NOT call logging.basicConfig or logging.root.*"
            exit 1
          fi
```

Alternative — ruff config (covers `logging.root.*` only; basicConfig requires the grep step above):

```toml
# pyproject.toml [tool.ruff.lint]
select = [
    # ... existing rules ...
    "LOG",  # flake8-logging — includes LOG015 (root-logger-call)
]
```

[VERIFIED: ruff 0.7+ supports LOG015 per https://docs.astral.sh/ruff/rules/#flake8-logging-log. LOG015 catches `logging.root.<anything>()` — but does NOT catch `logging.basicConfig()`. Both are needed → use combo.]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No retries; transient 503 = caller's problem | `tenacity.Retrying` inside `RetryTransport(httpx.HTTPTransport)` with full-jitter exp backoff | Phase 8 (this) | Caller code unchanged; reliability improves silently. |
| No structured logging; failures only visible via exceptions | `logging.getLogger("<pkg>")` + `NullHandler` + structured `extra={}` + `RedactingFilter` | Phase 8 (this) | Consumer opts in via `logging.getLogger("<pkg>").setLevel(DEBUG)`; library never touches root. |
| HTTP-method-based retry gate (httpx-retries default) | Explicit `request.extensions["idempotent"]` from `RequestSpec.idempotent` | Phase 8 (this) | matriz Primary API HTTP-GET-for-mutation quirk handled correctly. |
| Single `monkeypatch.setattr(client, "_token", X, raising=False)` test setup | `configure(token=X, token_expires_at=Y)` + `RetryTransport` + `http_client=httpx.Client(transport=MockTransport(...))` option | Phase 6+ (already); D-15 extends with `http_client=` kwarg | Tests can inject `MockTransport` directly without monkeypatching transport. |
| Sync-only retry libraries (`backoff`, `urllib3.Retry`) | Sync + async unified by `tenacity` (`Retrying` / `AsyncRetrying`) | Phase 8 (this) | One implementation pattern, two surfaces. |

**Deprecated / outdated:**
- `monkeypatch.setattr(client, "_token", X, raising=False)` test idiom — already migrated in Phase 6 to `configure(token=X)`. Phase 8 does not re-introduce.
- `time.sleep(2 ** attempt)` ad-hoc retry — replaced by tenacity in transport.
- Inline `Bearer ***` redaction at log-call sites — replaced by `RedactingFilter` attached once.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `RetryTransport` per-package preferred over a single shared helper module. | Architecture Patterns Pattern 1 | LOW — project constraint "no shared internals between packages" already locks this. 4× duplication of ~95 LOC `_transport.py` is acceptable. |
| A2 | `Retry-After` HTTP-date format (RFC 1123) used by financial APIs is rare; day-1 delta-seconds-only with WARNING log if HTTP-date detected. | User Constraints — Claude's Discretion | LOW — D-04 caps at 60s regardless of format. Worst case: HTTP-date drops to fallback `wait_exponential_jitter`. Forward-compat to v1.2. |
| A3 | `LOG015` ruff rule + grep CI step for `logging.basicConfig` is sufficient enforcement. | Don't Hand-Roll + Common Pitfalls | LOW — both mechanisms verified: LOG015 at docs.astral.sh/ruff; grep covers basicConfig which LOG rules don't. Regression test `test_logging_root_unchanged.py` is a third belt-and-suspenders layer. |
| A4 | `caplog.set_level(logging.DEBUG, logger="<pkg>")` correctly applies `RedactingFilter` attached via `addFilter` in pytest 8.3. | Code Examples + Claude's Discretion | MEDIUM — pytest's caplog historically had quirks with filters. Planner verifies during Plan 1 implementation; if not, fallback is to wire filter on a `logging.NullHandler`-replacing test handler. Verified pattern: filter on logger via `logger.addFilter()` applies to ALL records emitted through that logger (verified in CPython logging behavior). |
| A5 | `wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0)` produces `delay ∈ [0, min(max, initial*exp_base^n + jitter)]`. The CONTEXT.md D-08 formula `random.uniform(0, min(max, base*2^attempt))` is the AWS "full jitter" pattern but tenacity's `wait_exponential_jitter` adds jitter to the exponential value rather than replacing it. | Standard Stack | LOW — both formulas avoid thundering herd; minor distribution difference. Planner verifies empirically during Plan 1 OR composes a custom `wait_base` for exact AWS-pattern match. tenacity docs: `min(initial * 2**n + random.uniform(0, jitter), maximum)`. |
| A6 | matriz mutating builders (`build_new_order_request`, `build_cancel_order_request`, `build_replace_order_request`) MUST be updated to NOT inherit `idempotent=True` default (they currently use the Phase 7 D-13 forward-declared default `False` — Phase 8 explicit-flag-it for clarity in the same plan). | Code Examples mutation gate test | LOW — `RequestSpec.idempotent: bool = False` is the default; Phase 8 only flips GET builders to `True`. Mutating builders already inherit `False` by Phase 7 D-13 design. |
| A7 | The shell `_request()` uses `httpx.Client.build_request()` + `Client.send(request)` (not the higher-level `client.request(method, url, ...)`) so that `request.extensions` can be populated BEFORE send. | Architecture Patterns Pattern 3 | LOW — `httpx.Client.build_request` is a documented public API. Existing Phase 7 transport shells use `client.request(...)` (which constructs Request internally) — Phase 8 plan MUST migrate to `build_request` + `send` to expose the extensions dict. |
| A8 | `account_id` in `RequestSpec` is conditional (higyrus + matriz only), and the shell `_request()` reads it via `getattr(spec, "account_id", None)` to avoid `AttributeError` in iol/ámbito where the field does not exist on the package's `RequestSpec`. | Code Examples 401 re-auth | LOW — `dataclass` does not error on `getattr(instance, "nonexistent", default)`. Pattern is idiomatic. |
| A9 | `RetryTransport` instance is shared with `_ensure_token()` (login goes through the same `state.http_client`). D-29 locks this. The login request has `idempotent=True` (D-03) so 5xx during login is retried. | Architecture Patterns Pattern 1 | LOW — confirmed in D-29 + CONTEXT.md decisions. The transport sees login like any other request. |
| A10 | The planner uses `tenacity` 9.1.4 (current) and pins `>=9.1.0,<10`. The minor version range allows future bugfixes without breaking changes. | Standard Stack | LOW — tenacity 9.x stable; semver pinning standard practice. |

**Note:** All claims tagged `[ASSUMED]` above relate to implementation details where the planner has flexibility per Claude's Discretion section in CONTEXT.md. They are NOT blockers — the planner picks the concrete approach during planning.

## Open Questions

1. **Should the planner pre-compute the `duration_ms` field per-attempt or per-business-call?**
   - What we know: D-09 lists `duration_ms` as a mandatory field; both interpretations are valid.
   - What's unclear: whether the WARNING-per-retry-attempt log should report cumulative duration or per-attempt duration.
   - Recommendation: per-business-call duration on the terminal log (ERROR or final DEBUG), and per-attempt duration on WARNING records. Planner decides during Plan 1 (cross-cutting infra).

2. **For ámbito (no auth, no token), should `Client.__init__` accept the `max_retries` kwarg?**
   - What we know: D-15 says ámbito gets the kwarg "for consistency".
   - What's unclear: does ámbito's snapshot file gain the kwarg the same way as the auth packages?
   - Recommendation: yes — D-28 says snapshot update per-plan atomic, and D-15 explicitly includes ámbito. Plan 2 (ámbito canary) updates `verification/snapshots/ambito-financiero-client-surface.txt` with the 2 new kwargs.

3. **Should `RetryTransport.__init__` accept `**httpx_kwargs` for `verify=`, `cert=`, `proxy=`, `timeout=` passthrough?**
   - What we know: `httpx.HTTPTransport.__init__` accepts `verify`, `cert`, `trust_env`, `proxy`, `uds`, `local_address`, `retries`, `socket_options`, `http1`, `http2`. Phase 8 likely needs `verify` for future TLS pinning + `proxy` for compliance.
   - What's unclear: minimum kwarg passthrough surface.
   - Recommendation: forward `**kwargs` via `super().__init__(**kwargs)` and document the contract in `_transport.py` module docstring. Already shown in Pattern 1 code.

4. **For matriz, does `AsyncClient.__init__` get the `max_retries`/`http_client` kwargs even though `_atransport.py` does not exist?**
   - What we know: D-25 says "AsyncClient (stub Phase 6) keeps its current signature".
   - What's unclear: snapshot diff — if AsyncClient kwargs are NOT added, the snapshot for matriz differs from the other 3 packages.
   - Recommendation: D-25 wins — matriz AsyncClient signature unchanged in Phase 8. Plan 5 SUMMARY.md documents the deviation explicitly with forward ref to Phase 10. Snapshot test (`test_public_surface_matches_snapshot[matriz_client]`) verifies the matriz-specific shape.

5. **Should the WARNING-per-retry log include the response body excerpt?**
   - What we know: D-12 says "DEBUG req/resp without body, without headers".
   - What's unclear: WARNING retry log — body excerpt for debuggability of WHY a 503 was retried (e.g., upstream cloudflare message vs application 503)?
   - Recommendation: NO — keep WARNING field set to the canonical D-09 fields. Body excerpts can leak PII. Consumer can add a custom handler that captures body via `response.text` at the call site if needed. Forward to v1.2 if telemetry requests it.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All packages | ✓ | 3.12.11 | Python 3.13 also supported (CI matrix) |
| uv 0.9.0+ | Workspace install | ✓ | 0.9.0+ | None — required |
| `httpx>=0.27` | Transport subclassing | ✓ | existing dep | None — required |
| `tenacity>=9.1.0,<10` | Retry loop | ✗ (new — to be added) | will install 9.1.4 | None — required, vetted |
| `python-dotenv>=1.0` | env loading | ✓ | existing dep | None |
| `pytest>=8.3` | Test runner | ✓ | existing dev-dep | None |
| `pytest-asyncio>=0.24` | Async cancellation guard test | ✓ | existing dev-dep | None |
| `pytest-httpx>=0.34` | HTTP mocking in guard tests | ✓ | existing dev-dep | None |
| `import-linter>=2.11,<3` | `_core.py` boundary enforcement | ✓ | existing dev-dep (Phase 7) | None |
| `ruff>=0.7` | Linting (LOG015) | ✓ | existing dev-dep | grep step fallback for `logging.basicConfig` (D-27 alt b) — already planned |
| `mypy>=1.13` strict | Type checking | ✓ | existing dev-dep | None — tenacity has `py.typed` |
| `pre-commit>=4.0` | Git hooks (ruff + mypy) | ✓ | existing dev-dep | None |

**Missing dependencies with no fallback:** none.

**Missing dependencies with fallback:** none.

**Net additions:** `tenacity>=9.1.0,<10` added to each of the 4 packages' `[project] dependencies`. Zero new dev deps.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx 0.34+, pytest-cov 6.0+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (lines 91-109) |
| Quick run command | `uv run pytest packages/<pkg>/tests/ -x` (per-package) |
| Full suite command | `uv run pytest packages tests verification` (workspace-wide) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| RELY-01 | `RetryTransport` retries 408/409/429/≥500 + ConnectError/ConnectTimeout/ReadTimeout; default `max_attempts=2` | unit + integration | `pytest packages/<pkg>/tests/test_transport.py -x` | ❌ Wave 0 (new test files per package) |
| RELY-01 | `Retry-After: 30` honored with delay applied | integration | `pytest verification/test_retry_after_cap.py -x` | ❌ Wave 0 (D-26) |
| RELY-02 | Full-jitter formula produces distinct values across attempts | unit | `pytest packages/<pkg>/tests/test_transport.py::test_jitter_distribution -x` | ❌ Wave 0 |
| RELY-02 | `Retry-After: 600` capped at 60s | integration | `pytest verification/test_retry_after_cap.py -x` | ❌ Wave 0 (D-26) |
| RELY-03 | POST/non-idempotent never retries | integration | `pytest verification/test_retry_mutation_gate.py -x` | ❌ Wave 0 (D-26) |
| RELY-03 | matriz `new_order` (HTTP GET, `idempotent=False`) does NOT retry on 503 | integration | included in `test_retry_mutation_gate.py` parametrize | ❌ Wave 0 |
| RELY-04 | 401 → 200 exactly 2+1 wire requests with refreshed token | integration | `pytest verification/test_retry_401_reauth.py -x` | ❌ Wave 0 (D-26) |
| RELY-04 | 401 → 401 exactly 2+1 wire requests + AuthError raised | integration | included in `test_retry_401_reauth.py` parametrize | ❌ Wave 0 |
| RELY-04 | matriz Risk API `spec.auth_basic is not None`: 401 → AuthError immediate (no re-auth) | integration | parametrize skip for non-matriz, custom for matriz | ❌ Wave 0 |
| LOG-01 | `logging.root.handlers` unchanged after import | unit | `pytest verification/test_logging_root_unchanged.py -x` | ❌ Wave 0 (D-26) |
| LOG-01 | CI grep step fails on `logging.basicConfig` in `packages/*/src/` | CI grep | `! grep -rn 'logging\.basicConfig' packages/*/src/` | ❌ Wave 0 (CI yaml change) |
| LOG-01 | ruff `LOG015` blocks `logging.root.<anything>` | lint | `uv run ruff check packages/` | ✓ (ruff exists; need to enable LOG rule set) |
| LOG-02 | Token literal never in `caplog.records[*].getMessage()` even at DEBUG | integration | `pytest verification/test_logging_no_token_leak.py -x` | ❌ Wave 0 (D-26) |
| LOG-02 | `RedactingFilter` scrubs Bearer / X-Auth-Token / password / refresh_token / JSON password / matriz auth_basic | unit per package | `pytest packages/<pkg>/tests/test_logging.py -x` | ❌ Wave 0 |
| LOG-03 | Required `extra={}` fields present + non-colliding | unit | `pytest packages/<pkg>/tests/test_logging.py -x` | ❌ Wave 0 |
| LOG-03 | `account_id` propagation (higyrus + matriz) when set on `RequestSpec` | unit | included in test_logging.py | ❌ Wave 0 |
| D-26 | Async cancellation propagates within 500ms when retry budget is 30s | async integration | `pytest verification/test_async_cancellation.py -x` | ❌ Wave 0 |
| D-28 | Public surface snapshot diff = exactly the 2 new kwargs per package | snapshot | `pytest verification/test_public_surface.py -x` | ✓ (file exists; snapshots updated per plan) |
| D-29 | Login goes through `RetryTransport` (transient retried; 401 immediate) | integration | `pytest packages/<pkg>/tests/test_transport.py::test_login_retries -x` | ❌ Wave 0 |
| D-30 | `request_id` consistent across retry attempts | unit | `pytest packages/<pkg>/tests/test_transport.py::test_request_id_persists -x` | ❌ Wave 0 |
| Cross-leak | sync token does not bleed into async surface | snapshot | `pytest verification/test_sync_async_isolation.py -x` | ✓ (exists; verify still PASS post-Phase-8) |
| import-linter | `_core.py` does not import `client.py` / `aio.py` / NEW `_transport.py` / `_atransport.py` | lint | `uv run lint-imports` | ✓ (config exists; planner extends contracts to include `_transport` / `_atransport`) |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/<pkg>/tests/ -x` (~30s per package) + `uv run pytest verification/test_retry_*.py verification/test_logging_*.py -x` (~10s)
- **Per wave merge (per plan 2-5):** above + `uv run pytest verification/test_public_surface.py verification/test_sync_async_isolation.py -x` + `uv run lint-imports`
- **Phase gate (Plan 6):** full suite — `uv run pytest packages tests verification` + `uv run ruff check .` + `uv run ruff format --check .` + `uv run mypy` + `uv run lint-imports` + CI grep for `logging.basicConfig`/`logging.root` on Python 3.12 AND 3.13 matrix.

### Wave 0 Gaps

Plan 1 (cross-cutting infra) MUST land the following test files BEFORE Plans 2-5 touch packages. Tests fail RED at HEAD (no `_transport.py` / `_logging.py` yet) and turn green as Plans 2-5 land their per-package implementations.

- [ ] `verification/test_retry_mutation_gate.py` — RELY-03; parametrized over the 4 packages (D-26).
- [ ] `verification/test_retry_401_reauth.py` — RELY-04; parametrized over auth packages (iol/higyrus/matriz) (D-26).
- [ ] `verification/test_retry_after_cap.py` — RELY-02; cross-cutting Retry-After cap 60s (D-26).
- [ ] `verification/test_logging_root_unchanged.py` — LOG-01; cross-cutting (D-26).
- [ ] `verification/test_logging_no_token_leak.py` — LOG-02; parametrized over 4 packages (D-26).
- [ ] `verification/test_async_cancellation.py` — D-32 Pitfall 16; parametrized over async packages (ámbito/iol/higyrus); matriz `pytest.skip("matriz aio.py REST stub hasta Phase 10 — D-25")` (D-26).
- [ ] Per-package `packages/<pkg>/tests/test_transport.py` (4 files) — unit tests for `RetryTransport` (mutation gate pass-through, retry on 503, Retry-After cap, jitter distribution, `request_id` persistence, login retries).
- [ ] Per-package `packages/<pkg>/tests/test_logging.py` (4 files) — `RedactingFilter` unit tests + `extra={}` schema validation + non-collision check.
- [ ] CI workflow change in `.github/workflows/ci.yml` — add grep step for `logging.basicConfig` / `logging.root.<...>` (Plan 1 if combo D-27 alt b chosen; otherwise Plan 6).
- [ ] Optional: enable `LOG` ruff rule set in `pyproject.toml` `[tool.ruff.lint]` select (Plan 1 or Plan 6).
- [ ] Per-package snapshot updates (`verification/snapshots/<pkg>-surface.txt`) — Plans 2-5 atomic (D-28).

**Cross-cutting test files land in Plan 1** (failing RED). Per-package test files land alongside the package implementation in Plans 2-5. Snapshot updates land in Plans 2-5 (per D-28).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes | 401 re-auth-once in shell `_request()` (D-02); auth-flow request (`build_login_request`) marked `idempotent=True` so transient 5xx during login is retried; `AuthError` NEVER in `retry_on=` so expired tokens don't loop. |
| V3 Session Management | yes (token caching) | `_state.token` + `token_expires_at` per-instance (Phase 6/7); Phase 8 preserves — does NOT add disk persistence (deferred Phase 9 BUG-03 / v1.2). |
| V4 Access Control | no | Library does not enforce access control — API server does. Library's role is to surface 401/403 via `AuthError`. |
| V5 Input Validation | partial | `RequestSpec` builders validate input shape (existing Phase 7); Phase 8 does not add input-validation surface. `_parse_retry_after` validates string-to-float and HTTP-date format safely (no eval, no shell). |
| V6 Cryptography | no | Library does not handle crypto. TLS via httpx (delegated to system). |
| V7 Error Handling and Logging | YES (LOG-01, LOG-02, LOG-03) | `RedactingFilter` blocks credential leaks in DEBUG logs (LOG-02). Library logger does NOT touch root (LOG-01). Structured `extra={}` enables consumer-side correlation without leaking PII (LOG-03). |
| V8 Data Protection | YES (token redaction) | `RedactingFilter` per package; CI grep for `logging.basicConfig`/`logging.root` to prevent root logger hijack; regression test asserts token literal never in caplog records. |
| V9 Communication | partial | TLS delegated to httpx. `RetryTransport` does not introduce new TLS surface. `Retry-After` HTTP-date parsing is bounded (cap 60s) → no DoS amplification. |
| V14 Config | yes | `max_retries=0` disables retries (D-19) for opt-out. No env var override day 1 (deferred v1.2). |

### Known Threat Patterns for Python HTTP-client retry + logging stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Token leaked in DEBUG log emitted from library to consumer's Sentry/Datadog | Information Disclosure | `RedactingFilter` attached at `__init__.py` scrubs token substrings before record emission (LOG-02, D-10). Regression test `test_logging_no_token_leak.py` (D-26). |
| Library configures root logger → consumer apps' logs hijacked | Tampering | `NullHandler` only (LOG-01). CI grep step + ruff LOG015 + regression test (D-26 + D-27). |
| Retry of mutating POST → duplicate side effect (matriz duplicate order) | Tampering | Mutation gate `request.extensions["idempotent"]` set by builder (D-01). Mutating builders inherit `idempotent=False`. Guard test `test_retry_mutation_gate.py` (D-26). |
| Retry of expired-token request → N requests with stale Authorization → potential rate-limit triggering | Denial of Service (self-induced) | `AuthError` NEVER in `retry_on=` (D-07). Shell `_request()` does exactly-one re-auth + re-send (D-02). Guard test `test_retry_401_reauth.py` (D-26). |
| Server returns 429 with `Retry-After: 600` → backoff loop misinterprets and floods | Denial of Service (server) | `_parse_retry_after` returns capped delay; `min(delay, 60.0)` enforced (D-04). Guard test `test_retry_after_cap.py` (D-26). |
| Async cancellation hangs for full retry budget on `wait_for` timeout | Availability | `AsyncRetrying` uses `asyncio.sleep` natively; `CancelledError` propagates (D-32; verified empirically in this research session — see Verification Notes). Guard test `test_async_cancellation.py` (D-26). |
| `request.extensions` dict mutated across retries → log fields leak between business calls | Information Disclosure (lower severity) | Treat `extensions` as read-only inside transport (Pitfall 9). Local variables for `attempt_number` etc. |
| `logging.LogRecord` reserved attribute collision via `extra=` → `KeyError` at runtime | Availability | D-09 field set (`package`, `method`, `url`, `status_code`, `attempt`, `duration_ms`, `request_id`, `endpoint_name`, `account_id`, `retry_reason`) verified non-colliding with LogRecord reserved list. |
| Stack trace in ERROR log emits Authorization header value (when exc carries `request` reference) | Information Disclosure | `exc_info=False` on ERROR transport log (see Pattern 1 example); if `exc_info=True` is needed later, `RedactingFilter` scrubs the traceback message too. |
| Future `httpx.Client(http2=True)` leaks stream when retry sentinel raised before `response.read()` | Availability + resource leak | Pattern 1 example: `response.read()` BEFORE the `_is_retryable_status` check (Phase 7 D-06 / CR-03 pattern carried forward into the transport). |

## Project Constraints (from CLAUDE.md)

- **Python 3.12+**, **uv**, **httpx (sync+async)**, **pytest+pytest-httpx**, **ruff**, **mypy strict** — all extensions and fixes MUST respect the stack and pass existing CI.
- **Per-package isolation** — singleton state per module; **NO shared code between packages by design**. Phase 8 fixes apply within each package — NO cross-package dependencies introduced. `_transport.py`, `_atransport.py`, `_logging.py` are duplicated 4× verbatim per package.
- **Dual sync/async** — any logic fix MUST be mirrored in `client.py` and `aio.py` of the same package. `RetryTransport` (sync) and `AsyncRetryTransport` (async) are mirrored per package (3× — matriz async deferred to Phase 10).
- **Secrets in `.env` per package** — NEVER commit `.env`; NEVER expose credentials in logs, reports, or tests. Phase 8 specifically: `RedactingFilter` enforces this at the logging layer.
- **External live dependencies** — verification depends on real third-party services availability + state; results vary by market hours / data / rate limits.
- **GSD Workflow Enforcement (project-level)** — direct repo edits outside a GSD workflow are prohibited. Phase 8 work happens via `/gsd-execute-phase`.

**Auto-loaded knowledge (`Skill("spike-findings-market-libs")`):** the validated TokenStore + RefreshPolicy patterns are PHASE 10 territory, NOT Phase 8. The RefreshPolicy classification (PermanentError / TransientError / RateLimitedError) is INSPIRATIONAL for Phase 8's retry decisions (D-04, D-07, D-08 align with the principles) but the spike code itself does NOT land in Phase 8. Do NOT import from `.planning/spikes/003-tokenstore-refresh-policy/`.

## Verification Notes (empirical findings from this research session)

**Tenacity 9.1.4 CancelledError propagation — VERIFIED empirically:**

```bash
$ uv run --with tenacity python -c "
import asyncio
from tenacity import AsyncRetrying, stop_after_attempt, retry_if_exception_type, wait_fixed

async def main():
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(5),
        wait=wait_fixed(10),  # long wait
        retry=retry_if_exception_type(Exception),
        reraise=True,
    ):
        with attempt:
            raise Exception('fail')

async def runner():
    task = asyncio.create_task(main())
    await asyncio.sleep(0.5)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print('Cancelled during sleep — propagated correctly')

asyncio.run(runner())
"
Cancelled during sleep — propagated correctly
```

[VERIFIED: D-32 holds. `asyncio.CancelledError` raised during `AsyncRetrying`'s `await self.sleep(do)` propagates. Confirmed for tenacity 9.1.4 source at `tenacity/asyncio/__init__.py::AsyncRetrying.__call__`.]

**Tenacity 9.1.4 `Retrying.__call__` source verified:**

```python
# inspect.getsource(tenacity.Retrying) — verified during this research session
def __call__(self, fn, *args, **kwargs):
    self.begin()
    retry_state = RetryCallState(retry_object=self, fn=fn, args=args, kwargs=kwargs)
    while True:
        do = self.iter(retry_state=retry_state)
        if isinstance(do, DoAttempt):
            try:
                result = fn(*args, **kwargs)
            except BaseException:  # noqa: B902
                retry_state.set_exception(sys.exc_info())
            else:
                retry_state.set_result(result)
        elif isinstance(do, DoSleep):
            retry_state.prepare_for_next_attempt()
            self.sleep(do)
        else:
            return do
```

The `except BaseException` catches `CancelledError` BUT the next iteration sees the exception via `retry_state.outcome.exception()` and consults the `retry=` predicate. Since `retry=retry_if_exception_type((httpx.ConnectError, ...))` does NOT match `CancelledError`, tenacity falls through to `reraise=True` → propagates.

[VERIFIED: D-07 + D-32 LOCKED. `retry_on=` restricted set ensures `CancelledError` propagates instead of being retried.]

**ruff `LOG015` covers `logging.root.*` but NOT `logging.basicConfig`:**

[VERIFIED: docs.astral.sh/ruff/rules/ — LOG001..LOG015 listed. `logging.basicConfig` is not in the rule set. D-27 combo decision (LOG015 + grep step) is necessary.]

## Sources

### Primary (HIGH confidence — Context7 / source inspection / official docs)

- **Tenacity 9.1.4 source** (verified locally during this research session): `tenacity.Retrying`, `tenacity.AsyncRetrying`, `tenacity.AttemptManager`, `tenacity.wait_exponential_jitter`, `tenacity.retry_if_exception_type`, `tenacity.retry_if_result`, `tenacity.stop_after_attempt`. All APIs Phase 8 depends on are present.
- **Tenacity ReadTheDocs** — https://tenacity.readthedocs.io/en/stable/ — pattern references for `Retrying` as iterator, `with attempt:` swallow semantics, `AsyncRetrying` differences from `Retrying`. [HIGH]
- **Tenacity PyPI** — https://pypi.org/pypi/tenacity/json — version 9.1.4, requires-python `>=3.10`, Apache-2.0, zero runtime deps. [HIGH]
- **Python Logging HOWTO** — https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library — `NullHandler` mandate, "library code should not configure logging". [HIGH]
- **Python `logging.LogRecord` documentation** — https://docs.python.org/3/library/logging.html#logrecord-attributes — reserved attribute list verified non-colliding with D-09 field set. [HIGH]
- **Ruff LOG rule documentation** — https://docs.astral.sh/ruff/rules/#flake8-logging-log — LOG001..LOG015 catalogued; `logging.basicConfig` NOT covered. [HIGH]
- **RFC 9110 §10.2.3 Retry-After** — delta-seconds and HTTP-date formats. [HIGH]
- **PEP 562 (Module __getattr__ / __setattr__)** — referenced indirectly for Phase 6 shim compat (no changes in Phase 8). [HIGH]
- **`.planning/research/SUMMARY.md` §"Phase 3"** — Phase 8 ≡ research "Phase 3"; standard patterns, no new research flags. [HIGH]
- **`.planning/research/STACK.md`** — full evaluation of tenacity vs httpx-retries / backoff / roll-our-own; structlog / loguru evaluation and rejection. [HIGH]
- **`.planning/research/PITFALLS.md` §"Pitfalls 4, 5, 6, 7, 13, 14, 15, 16, 17, 29"** — full mitigation playbook for Phase 8. [HIGH]
- **CONTEXT.md decisions D-01..D-32** — locked decisions are the source of truth for Phase 8 implementation. [HIGH]

### Secondary (HIGH confidence — verified existing codebase state)

- **`packages/ambito-financiero-client/src/ambito_financiero_client/{client,aio,_core,_state}.py`** — Phase 7 baseline shape for the canary plan. [VERIFIED: read during this research session]
- **`packages/iol-client/src/iol_client/{client,aio,_core,_state}.py`** — Phase 7 baseline; auth-flow + refresh_token rotation; `InstrumentType` Literal export. [VERIFIED]
- **`packages/higyrus-client/src/higyrus_client/{client,_core,_state}.py`** — Phase 7 baseline; URL-encoding quirk encapsulated in `_core`; `account_id` field placeholder absent (Phase 8 adds). [VERIFIED]
- **`packages/matriz-client/src/matriz_client/{client,aio,_core,_state}.py`** — Phase 7 baseline; Risk API `auth_basic` in `RequestSpec`; matriz `aio.py` is stub (D-25). [VERIFIED]
- **`verification/test_public_surface.py` + `verification/test_sync_async_isolation.py`** — Phase 6/7 baseline guard tests; Phase 8 D-26 adds 6 new tests to `verification/` parametrized similarly. [VERIFIED: read during this research session]
- **`pyproject.toml`** — workspace deps; `import-linter>=2.11,<3` in `[dependency-groups] dev`; `[tool.importlinter]` with 4 forbidden contracts (Phase 7). [VERIFIED]
- **`.github/workflows/ci.yml`** — existing lint / pre-commit / typecheck / test matrix jobs. Phase 8 may add a `lint-logging` grep step OR enable ruff LOG rules. [VERIFIED]

### Tertiary (MEDIUM-LOW confidence — pattern guidance not load-bearing)

- **Zeitbach blog: "Honoring the Retry-After header with Tenacity"** — https://zeitbach.com/blog/2024/08/15/honoring-the-retry-after-header-with-tenacity — custom `wait_retry_after(wait_base)` pattern. [MEDIUM — single blog, but the pattern is straightforward and verifiable against tenacity API.]
- **httpx-tenacity tutorial** — https://midnighter.github.io/httpx-tenacity/0.1/tutorial/ — confirms tenacity is the canonical retry library for httpx workflows. [MEDIUM]
- **AWS Architecture Blog "Exponential Backoff and Jitter"** — Full Jitter algorithm rationale. [HIGH — referenced indirectly via existing research STACK.md.]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — tenacity 9.1.4 verified via local install + slopcheck `[OK]` + APIs all importable. Existing Phase 7 baseline read on disk.
- Architecture: HIGH — patterns are direct application of CONTEXT.md decisions D-01..D-32 (locked). No discovery work needed.
- Pitfalls: HIGH — rooted in `.planning/research/PITFALLS.md` §"Pitfalls 4-7, 13-17, 29" + verified empirically (CancelledError propagation, `AttemptManager` swallow semantics, ruff LOG rule coverage gap).
- Testing: HIGH — Wave 0 gaps explicitly enumerated; D-26 guard test shapes documented; test infra (pytest-httpx, pytest-asyncio) already in place.
- Security: HIGH — RedactingFilter pattern verified; root-logger guards layered (ruff LOG015 + grep + regression test); mutation gate explicit.

**Research date:** 2026-06-12
**Valid until:** 2026-07-12 (30 days — tenacity 9.x stable; CONTEXT.md decisions locked; Phase 7 baseline unchanged on disk)
