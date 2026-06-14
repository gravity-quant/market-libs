# Pitfalls Research

**Domain:** Python HTTP-client monorepo refactor (v1.1 Tech Debt Cleanup over v1.0 verified baseline)
**Researched:** 2026-06-10
**Confidence:** HIGH (based on existing codebase state, CONCERNS.md tech debt, TESTING.md fixture patterns, and WR-01..WR-08 from Phase 5 code review)

## Scope

These pitfalls are SPECIFIC to adding the v1.1 refactor surface (Client class per instance, sync/async dedup, matriz `aio.py`, retries with backoff/jitter, structured logging, driver bundle, deferred fixes, WR-01..WR-08) to the existing v1.0 system:

- 4 packages with module-level singleton state (`_token`, `_client`, `_base_url`, `_user`, `_password`)
- Dual sync/async surfaces with INDEPENDENT state per surface
- 277 mocked pytest tests using `monkeypatch.setattr(pkg.client, "_token", ...)` and `pkg.configure(...)`
- `verification/` harness with `env_gate`, `mutation_gate` (double-gate `VERIFY_MUTATING=1` AND remarkets URL exact match), `redaction.py`, `findings.py`, `cycle_report.py`, `safemodel_diff.py`
- 14 classified findings from v1.0 baseline `verification-cycle-2026-Q2`
- 8 open code review concerns WR-01..WR-08
- 2 deferred bugs (F-09 matriz ERROR-MAP, F-02 higyrus `get_listado_cuentas=0`) and 2 deferred capabilities (IOL refresh_token persistence, HIGY multi-account iteration)

---

## Critical Pitfalls

### Pitfall 1: Client class refactor silently breaks 277 tests' `monkeypatch.setattr(pkg.client, "_token", ...)` fixtures

**What goes wrong:**
After the refactor, `_token`, `_user`, `_base_url`, `_client` are moved from module-level globals to instance attributes of a new `Client` class. The existing `conftest.py` autouse fixtures and tests do:
```python
monkeypatch.setattr(iol_client.client, "_token", "test-token", raising=False)
monkeypatch.setattr(_client, "_user", "")
```
With `raising=False`, these calls SILENTLY succeed by adding attributes to the module that NO production code reads anymore. Tests show green; production paths use `_default_client._token`, not `pkg.client._token`. Authentication flows are never actually exercised by the fixtures.

**Why it happens:**
- `raising=False` is the dominant pattern in TESTING.md (every package's `conftest.py`).
- The compat layer keeps top-level `iol_client.login()`, `iol_client.get_quote(...)` working, so the surface looks unchanged.
- The fixture appears to do something — but the assignment lands on a dead address.

**How to avoid:**
1. **Compat shim that DOES forward to the default Client instance via module-level `__getattr__` / `__setattr__`.** Implement at module level:
   ```python
   # client.py
   _default_client: Client | None = None

   def __getattr__(name: str) -> Any:
       if name in {"_token", "_user", "_password", "_base_url", "_client", "_token_ts"}:
           return getattr(_get_default_client(), name)
       raise AttributeError(name)

   def __setattr__(name: str, value: Any) -> None:  # NOTE: modules don't support __setattr__ natively
       ...
   ```
   Modules do not support `__setattr__` natively; use a `ModuleType` subclass installed in `sys.modules` (see Python data model "Customizing module attribute access"). This is the documented mechanism.

2. **Or use `proxy` descriptors via a `LegacyStateProxy` class** that is assigned as module-level `_token = LegacyAttr("token")` and reads/writes the default client.

3. **CI smoke test:** add a test that asserts the fixture writes ARE observable by production paths:
   ```python
   def test_monkeypatch_token_reaches_production_request(monkeypatch, httpx_mock):
       monkeypatch.setattr(iol_client.client, "_token", "sentinel-1234")
       httpx_mock.add_response(json={})
       iol_client.get_quote("GGAL")
       [req] = httpx_mock.get_requests()
       assert req.headers["Authorization"] == "Bearer sentinel-1234"
   ```
   This guard test must EXIST BEFORE the refactor lands.

**Warning signs:**
- Test suite passes after refactor but coverage on `Client.__init__` / `Client._ensure_token` flat-lines.
- Diff shows `monkeypatch.setattr(..., raising=False)` — `raising=False` is the silent failure surface.
- `mypy` reports `Module has no attribute "_token"` warnings that get `# type: ignore`d.

**Phase to address:**
Phase 1 (Client class refactor for first package — likely `ambito-financiero-client` as smallest blast radius). Must land the compat shim and guard test in the SAME phase, and MUST run the existing 277 tests green before adding new functionality.

---

### Pitfall 2: `configure()` only mutates the default Client, leaving user-instantiated `Client()` objects with stale credentials

**What goes wrong:**
Caller does:
```python
client_a = iol_client.Client(username="alice", password="...")
iol_client.configure(username="bob", password="...")  # changes default only
client_a.get_quote("GGAL")  # still uses alice's credentials
```
Caller expects `configure()` to be process-wide (which it WAS in v1.0). Surprise: it only touches the singleton. Multi-tenant code that accidentally calls `configure()` thinking it's harmless silently scopes the change to one client.

**Why it happens:**
- v1.0 semantics: `configure()` resets `_token` globally. v1.1 must preserve this for top-level callers.
- The intuitive refactor — `def configure(...): _default_client = Client(...)` — leaves orphaned `Client` instances un-reconfigured.
- The opposite trap is equally bad: making `configure()` mutate ALL live instances breaks per-instance isolation, which is the WHOLE POINT of the refactor.

**How to avoid:**
1. **Documentation contract:** `configure()` mutates ONLY the implicit default Client; explicitly-instantiated `Client(...)` objects are independent. Make this explicit in the module docstring AND in `Client.__init__` docstring.
2. **Type hint signature change:** make `configure()` return `Client` (the new default) so callers can read and copy explicitly:
   ```python
   def configure(*, base_url=None, ...) -> Client:
       global _default_client
       _default_client = Client(base_url=base_url, ...)
       return _default_client
   ```
3. **Test parity:** add a test that asserts `configure()` does NOT affect `Client()` instances:
   ```python
   def test_configure_does_not_affect_explicit_client_instances():
       c = iol_client.Client(username="alice")
       iol_client.configure(username="bob")
       assert c.username == "alice"
   ```

**Warning signs:**
- A caller's bug report: "I called `configure()` and my other client now has the new credentials" → docs are unclear.
- The opposite bug report: "I called `configure()` and my second client still has the old credentials" → caller expected global semantics.
- Either is fixable by clear docs; both signal docs aren't there yet.

**Phase to address:**
Phase 1 (Client class refactor, first package). Document the contract in PROJECT.md and in package docstrings; add the parity test in conftest.py.

---

### Pitfall 3: Sync/async dedup re-couples surfaces through hidden shared state, defeating the whole refactor

**What goes wrong:**
Shared "pure" helper module `_core.py` is extracted from `client.py` and `aio.py`. To keep it pure, it accepts state as parameters. But during extraction, a developer adds `from .client import _token, _base_url` to `_core.py` "just for the auth helper" — quietly re-coupling sync and async surfaces to the SYNC module's globals. Tests pass. In production, async callers silently share token cache with sync callers, masking real bugs (e.g., async refresh failures get covered by a sync refresh that already ran).

**Why it happens:**
- Extraction is mechanical; reviewers may not notice an `import` line in a "pure" helper.
- mypy strict does NOT flag this — the import is type-safe.
- Tests don't catch it because the autouse fixture pre-loads both `iol_client.client._token` and `iol_client.aio._token` with the same sentinel.

**How to avoid:**
1. **Helper modules MUST be passed state as parameters, never import module-level globals.** Code-review checklist item: `grep -E "^from \.(client|aio)" _core.py` should return ZERO matches.
2. **Lint rule:** add a custom ruff `TID` rule or a tested `import-linter` config that BANS `_core.py` from importing `client.py` and `aio.py`.
3. **Test fixture:** use DIFFERENT sentinels for sync and async tokens in `conftest.py`, so that a cross-import accidentally leaking one into the other surfaces a test failure:
   ```python
   monkeypatch.setattr(iol_client.client, "_token", "SYNC-sentinel", raising=False)
   monkeypatch.setattr(iol_client.aio, "_token", "ASYNC-sentinel", raising=False)
   ```

**Warning signs:**
- A test that mocks `iol_client.client._token` accidentally also affects async tests.
- `_core.py` has any `import` from `client.py` or `aio.py`.
- A test sets sync `_token = None` to test login flow, and the test passes because async `_token` was still valid.

**Phase to address:**
Phase 2 (Sync/async dedup, first package). The Phase 2 plan must include the import-linter config or the equivalent lint rule, run as a CI gate.

---

### Pitfall 4: Retries with backoff retry a POST that already mutated state, bypassing `mutating_allowed` double-gate intent

**What goes wrong:**
A new generic retry decorator is added to `_request()`. The driver issues a `cancel_order` POST against remarkets (mutating, gated by `VERIFY_MUTATING=1` AND remarkets URL match). The first attempt times out AFTER the server already cancelled the order. Retry triggers, second `cancel_order` returns 404 ("order not found"). The retry layer either:
- (a) Maps 404 → exception → cycle records a CONFIRMED finding for a non-bug;
- (b) Silently retries on 5xx and the order is cancelled, then a NEW order is created later in the same test and the retry of a `new_order` POST creates TWO orders.

**Why it happens:**
- Retry libraries (tenacity, urllib3 Retry) retry GET, POST, PUT, DELETE by default unless told otherwise.
- The `mutating_allowed` gate lives at the DRIVER level (in `verification/mutation_gate.py`), not inside the package's `_request`.
- Developers may assume "retry only on 5xx/429" is safe for POST — it is NOT for non-idempotent endpoints.

**How to avoid:**
1. **Retry is OPT-IN per method.** Default to GET-only retry. Add an explicit `idempotent: bool = False` keyword to `_request(method, path, *, idempotent=False, ...)`. Endpoint wrappers explicitly tag GETs as idempotent, mutating endpoints get `idempotent=False`.
2. **Document for matriz/Higyrus mutating endpoints:** every `new_order`, `cancel_order`, `replace_order` is NEVER retried, regardless of transport error. Document inline:
   ```python
   def new_order(...) -> ...:
       """Endpoint: POST /rest/order/newSingleOrder. Never retried (non-idempotent)."""
       return _request("POST", path, idempotent=False, ...)
   ```
3. **Regression test:** mock a 503 on a mutating POST and assert exactly ONE outgoing request:
   ```python
   def test_new_order_never_retried_on_503(httpx_mock):
       httpx_mock.add_response(method="POST", status_code=503)
       with pytest.raises(MatrizAPIError):
           matriz_client.new_order(...)
       assert len(httpx_mock.get_requests()) == 1
   ```

**Warning signs:**
- Retry decorator applied at `_request` level without per-call opt-in.
- Tests against mocked 503/504 show >1 request for POSTs.
- Live run shows duplicate orders or duplicate findings in the same probe.

**Phase to address:**
Phase 3 (Retries/backoff). The plan must include the idempotency tagging on every existing endpoint wrapper across the 4 packages as a checklist BEFORE enabling the retry decorator.

---

### Pitfall 5: Retry through expired token → 401 → retry → 401 → retry until cap (token never refreshed mid-retry)

**What goes wrong:**
`_ensure_token()` runs once at the START of `_request()`. The token is valid at that point. The first request fires, server takes 60 seconds (network slow), token expires server-side at second 30. Server returns 401. Retry decorator catches `AuthError` (or transport 401) and retries. Token is still cached locally as "fresh" (its TTL is 23h, not yet expired by local clock). All retries return 401. Retries are wasted; user sees AuthError after N attempts and 30 seconds of useless backoff.

**Why it happens:**
- Token TTL is a LOCAL estimate of expiry, not authoritative.
- Retry libraries retry on AuthError/HTTPStatusError, but don't know that they should re-auth between attempts.
- The 401 contract is: re-auth, then retry — but only ONCE.

**How to avoid:**
1. **Distinguish retryable transport errors from auth-retryable 401s.**
   - Transport errors (ConnectError, ReadTimeout, 5xx, 429): retry with backoff per the standard policy.
   - 401: re-authenticate (`_token = None; _ensure_token()`) and retry exactly ONCE.
2. **Never include `AuthError` in the retry decorator's `retry_on=` tuple.** Handle 401 explicitly in `_request()`:
   ```python
   def _request(method, path, *, idempotent=False, ...):
       _ensure_token()
       resp = _do_request(...)
       if resp.status_code == 401 and not _retried_auth:
           _token = None
           _ensure_token()
           resp = _do_request(...)  # one retry only
       _raise_for_response(resp)
       return resp.json()
   ```
3. **Regression test:** assert that after one 401 → 200, exactly TWO outgoing requests fired with refreshed token; after 401 → 401, exactly TWO requests fired and `AuthError` raised (not N retries).

**Warning signs:**
- Live `main_*.py` runs report "AuthError after 5 retries (15s)" instead of fast failure.
- Logs show 5x identical 401 responses with identical `Authorization` headers.
- The retry decorator's `retry_on` tuple includes `AuthError` or `HTTPStatusError`.

**Phase to address:**
Phase 3 (Retries/backoff). Plan must specify the "auth retry is special-cased, transport retry is the decorator" separation explicitly. WR-context: this overlaps with the IOL refresh_token deferred capability (Phase 5 fix item).

---

### Pitfall 6: Library configures root logger handlers (PROHIBITED for libraries per Python logging cookbook)

**What goes wrong:**
v1.1 adds structured logging. Developer does:
```python
# client.py
import logging
logging.basicConfig(format='%(asctime)s ...', level=logging.INFO)
logger = logging.getLogger(__name__)
```
Now every downstream caller that imports `iol_client` has their root logger reconfigured. FastAPI apps lose their JSON log structure. uvicorn's access logs change format. Caller files a "iol_client broke our logging" bug.

**Why it happens:**
- `logging.basicConfig` is the first example in the Python logging tutorial.
- Developers who learned logging from app code carry the pattern to library code.
- The "library best practice" of using `logging.NullHandler` is a known gotcha but isn't enforced by lint.

**How to avoid:**
1. **Library logging contract:** every package's top-level `__init__.py` adds:
   ```python
   import logging
   logging.getLogger(__name__).addHandler(logging.NullHandler())
   ```
   Source: official Python logging cookbook — "Configuring logging for a library".
2. **NEVER call `logging.basicConfig`, `logging.getLogger().addHandler(...)`, or `logging.root.setLevel(...)` from library code.**
3. **Lint rule:** ruff `G` (logging-format) won't catch this; add a manual grep CI check:
   ```bash
   ! grep -rn "logging.basicConfig\|logging.root\." packages/*/src/
   ```
4. **Regression test:** import any package in a test, assert root logger handler list is unchanged:
   ```python
   def test_import_does_not_modify_root_logger():
       before = list(logging.root.handlers)
       importlib.reload(iol_client)
       assert logging.root.handlers == before
   ```

**Warning signs:**
- `logging.basicConfig` appears anywhere in `packages/*/src/`.
- Caller reports "my log format changed after I imported iol_client".
- Tests that capture logs (caplog) suddenly see extra handlers.

**Phase to address:**
Phase 4 (Structured logging). Plan must reference Python logging cookbook and include the NullHandler boilerplate as a copy-paste recipe applied to all 4 packages.

---

### Pitfall 7: Logging at DEBUG level prints credentials despite `verification/redaction.py`

**What goes wrong:**
v1.1 adds `logger.debug("request: method=%s url=%s headers=%s", method, url, dict(req.headers))` to `_request()`. The `Authorization: Bearer <token>` header is in `req.headers`. `verification/redaction.py` is for DRIVERS, not for the library's own logging. When a downstream caller enables DEBUG (`logging.getLogger("iol_client").setLevel(logging.DEBUG)`), the Bearer token leaks into their logs. CI logs, Sentry, Datadog — all see the token.

**Why it happens:**
- `verification/redaction.py` is invoked by `safe_print()` in drivers — it does NOT intercept `logging` calls.
- "It's only at DEBUG" is the rationalisation; production systems routinely enable DEBUG for diagnostics.
- httpx's own Request.headers is a `Headers` object that DOES support custom `__repr__` but defaults to showing values.

**How to avoid:**
1. **Define a `_redact()` helper INSIDE each library, NOT in `verification/`.** Library code cannot import from `verification/` (it's a repo-root harness module, not packaged). Inline a `_redact_headers(headers)` that strips `Authorization`, `X-Auth-Token`, `Cookie`, `Set-Cookie`:
   ```python
   _SENSITIVE_HEADERS = frozenset({"authorization", "x-auth-token", "cookie", "set-cookie"})

   def _redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
       return {k: ("<redacted>" if k.lower() in _SENSITIVE_HEADERS else v) for k, v in headers.items()}
   ```
2. **NEVER log request bodies for auth endpoints.** Add a `_LOG_BODY_DENY_PATHS` set including `/token`, `/auth/login`, etc. Skip body logging for those.
3. **Test:** mock a request, capture logs via `caplog`, assert no log record contains the literal token string:
   ```python
   def test_request_does_not_log_bearer_token(caplog, httpx_mock):
       caplog.set_level(logging.DEBUG, logger="iol_client")
       monkeypatch.setattr(iol_client.client, "_token", "secret-token-XYZ")
       httpx_mock.add_response(json={})
       iol_client.get_quote("GGAL")
       assert all("secret-token-XYZ" not in r.getMessage() for r in caplog.records)
       assert all("secret-token-XYZ" not in str(r.args) for r in caplog.records)
   ```

**Warning signs:**
- `logger.debug` calls reference `req.headers` or `req` directly.
- No `_redact` helper exists inside the library.
- Test suite doesn't include a "no credentials in logs" assertion.

**Phase to address:**
Phase 4 (Structured logging). The plan must REQUIRE the in-library `_redact_headers` and the regression test for each of the 4 packages.

---

### Pitfall 8: matriz `aio.py` is created by copy-pasting `client.py` line-by-line — guaranteed sync/async drift on day 1

**What goes wrong:**
The fastest path to `matriz aio.py` is `cp client.py aio.py && sed -i 's/httpx.Client/httpx.AsyncClient/g; s/def /async def /g'`. This produces a working module, but every bug already present in `client.py` (the `_unwrap` envelope handling, the `_token` runtime guard, CR-01 `_request` returning non-dict, F-09 ERROR-MAP, etc.) is now duplicated. The 18 envelope-key indexing fixes from Phase 5 are duplicated. Future bugfixes require touching both files.

This is the EXACT tech debt v1.1 is supposed to ELIMINATE per the milestone goals ("deduplicación lógica sync/async"). Creating matriz `aio.py` by copying breaks the milestone goal at its inception.

**Why it happens:**
- "Get something working" pressure favors copy-paste.
- The dedup refactor (Phase 2) and matriz `aio.py` creation (Phase 5 in the v1.1 roadmap) may be plannned in either order; if `aio.py` is created BEFORE the dedup pattern is established, copy-paste is the only available option.
- Even with the dedup pattern, the temptation to "ship now, refactor later" produces a copy-paste `aio.py` that never gets refactored.

**How to avoid:**
1. **STRICT phase ordering:** matriz `aio.py` must be created AFTER the sync/async dedup pattern is established in at least one other package (e.g., `iol-client`). The pattern is the prerequisite, not a follow-up.
2. **No `aio.py` without `_core.py`.** The roadmap should treat matriz dedup as "first introduce `_core.py` extracted from `client.py`, then add `aio.py` as a thin async wrapper".
3. **Diff review checklist:** PR review must explicitly check that matriz `aio.py` and `client.py` share `_core.py` for envelope handling (`_unwrap`), error mapping (`_raise_for_response`), and auth flow. If both modules contain a function named `_unwrap`, the dedup failed.

**Warning signs:**
- `diff packages/matriz-client/src/matriz_client/{client,aio}.py | wc -l` is small (lots of overlap).
- A bugfix to `client.py._unwrap` is followed by an identical commit to `aio.py._unwrap`.
- WR-04 (driver `_first_dict` silent failure) shows up duplicated in both surfaces.

**Phase to address:**
Phase 2 (Sync/async dedup) must complete first. Phase 5 (matriz `aio.py`) consumes the pattern. Re-order if the roadmap puts them in the wrong sequence.

---

### Pitfall 9: matriz `aio.py` shares `_token` cache with `client.py` AND `ws_client.py` daemon thread — race conditions on token refresh

**What goes wrong:**
matriz has 3 surfaces post-v1.1: sync `client.py` (single-threaded), async `aio.py` (event loop), and `ws_client.py` (daemon thread). All three need a valid token. The temptation is to share `_token` across all three for "convenience". Result:

- sync thread calls `_ensure_token()` → refreshes → writes `_token`.
- daemon thread (`ws_client.py`) reads `_token` mid-refresh → reads partial state (or in CPython, atomic str assignment, but read-after-old-write race).
- async event loop (`aio.py`) holds `asyncio.Lock` for token refresh, but the daemon thread doesn't honor it.

Symptoms: intermittent 401s in WebSocket frames after a sync REST call triggers a refresh.

**Why it happens:**
- v1.0 already has `ws_client.py` reading `_rest._token` directly (`packages/matriz-client/src/matriz_client/ws_client.py:140-150`) — fragile area noted in CONCERNS.md.
- Adding `aio.py` introduces a THIRD reader/writer of `_token`. The fragility multiplies.
- `asyncio.Lock` and `threading.Lock` do NOT interoperate.

**How to avoid:**
1. **All three surfaces own their own token cache, with a SHARED refresh function that uses `threading.Lock` (works for all three contexts — async can grab a threading lock briefly).** The refresh function returns a new token; each caller stores it locally.
2. **Or: one canonical `TokenStore` class, instance-per-Client, with both `threading.Lock` AND `asyncio.Lock`-aware refresh paths.** The sync path uses `threading.Lock`, the async path uses a helper that wraps the threading.Lock in `asyncio.to_thread`.
3. **Regression test:** spawn a thread that holds the token-refresh lock for 100ms; assert that an async `_ensure_token()` await waits and then returns the same refreshed token, NOT a stale one.

**Warning signs:**
- `_token` is a module-level global with `client.py`, `aio.py`, and `ws_client.py` all reading it.
- No lock is held across the `_token = None; _token = login()` window.
- Live `main_matriz.py` runs occasionally fail with 401 after a long-running test session.

**Phase to address:**
Phase 5 (matriz `aio.py` creation). Plan must explicitly address `ws_client.py` token sharing. This is the hardest part of v1.1; deserves its own task in the phase plan.

---

### Pitfall 10: Driver bundle `findings.py` append-only refactor accidentally duplicates "auto-generated below" markers across runs

**What goes wrong:**
Per `matriz-driver-findings-file-handling.md`, the fix for the findings-file regeneration bug introduces a marker like `<!-- auto-generated below this line -->`. The naive implementation reads the file, appends new findings AFTER the marker, and writes back. On the second run:
- Marker is still in the file from the first run.
- New findings are appended AFTER the marker.
- But: the previous run's findings (which the new run's findings should REPLACE for dedupe) are still there.

Result: the file accumulates findings every run. The marker is duplicated if the read/write logic re-inserts it.

**Why it happens:**
- Append-only file mutation is harder than it looks: distinguishing operator content vs. auto-generated content requires CAREFUL parsing.
- The marker approach (split on `<!-- auto-generated... -->`) requires the SAME marker text every run, but a developer may iterate the marker phrasing across versions.

**How to avoid:**
1. **Atomic write semantics with explicit zones.** Define `<!-- BEGIN auto -->` and `<!-- END auto -->` markers. Read the file, split into 3 zones: before-begin, between-begin-end (replace this), after-end. Write back atomically.
2. **Test the parser separately.** Unit test for `verification/findings.py::append_finding`:
   ```python
   def test_append_finding_preserves_operator_content_above_marker(tmp_path):
       f = tmp_path / "findings.md"
       f.write_text("Operator content\n<!-- BEGIN auto -->\nold\n<!-- END auto -->\nMore operator content\n")
       append_finding(f, "F-01", "title", "details")
       text = f.read_text()
       assert "Operator content" in text
       assert "More operator content" in text
       assert text.count("<!-- BEGIN auto -->") == 1
       assert text.count("<!-- END auto -->") == 1
       assert "old" not in text  # auto zone replaced
       assert "F-01" in text
   ```
3. **D-MATZ-27 EXPECTED dedupe:** the dedupe key must be a STABLE identifier (e.g., `(finding_id, classification)` tuple), NOT a substring match on the title. Substring matches dedupe legitimate findings that happen to share a title prefix.

**Warning signs:**
- File grows linearly with N runs.
- Multiple `<!-- BEGIN auto -->` markers in the same file.
- Dedupe key is a substring match (`if "prod-vs-remarkets divergence" not in text:`) — fragile.

**Phase to address:**
Phase 6 (Driver bundle: `findings.py` refactor + D-MATZ-27 dedupe). Plan must include the marker-zone design and the unit test in `verification/tests/`.

---

## Moderate Pitfalls

### Pitfall 11: `Client` class accidentally enables pickling / `__deepcopy__` on an object holding httpx state

**What goes wrong:**
The new `Client` class is a regular Python class. `copy.deepcopy(client)` or `pickle.dumps(client)` SILENTLY succeed, copying the underlying `httpx.Client` (or `httpx.AsyncClient`) — which contains a connection pool, transport, possibly an open SSL context. The deepcopy is unusable; the pickle is unusable.

**Prevention:**
- Override `__deepcopy__` to raise `TypeError("Client is not deep-copyable; use Client(credentials=other.credentials) instead")`.
- Override `__reduce__` / `__getstate__` to raise `TypeError("Client is not picklable")`.
- Document in `Client.__init__` docstring.

**Phase to address:** Phase 1 (Client class refactor).

---

### Pitfall 12: Closing the default Client at interpreter shutdown causes `RuntimeError: Event loop is closed` for async

**What goes wrong:**
Developer adds `atexit.register(_default_client.close)` to ensure resources are cleaned up. For async clients, `_default_async_client.aclose()` is a coroutine; calling it from `atexit` requires an event loop. By the time `atexit` runs, the loop is closed (or never existed in pure-sync contexts). Result: traceback on every script exit.

**Prevention:**
- For sync `Client`: `atexit.register(self._sync_client.close)` is safe (httpx.Client.close is synchronous).
- For async `Client`: do NOT register `atexit` for aclose. Document that callers must call `await aclient.aclose()` themselves, OR use `async with Client(...) as c:` context manager.
- Provide `__enter__` / `__exit__` for sync and `__aenter__` / `__aexit__` for async.

**Phase to address:** Phase 1 (Client class refactor).

---

### Pitfall 13: 429 Retry-After header ignored by retry decorator — hammers the server during rate-limit

**What goes wrong:**
Retry decorator uses fixed exponential backoff (`base * 2**attempt + jitter`). When the server returns 429 with `Retry-After: 60`, the client retries in 0.5s, 1s, 2s — none of which respect the server's wait directive. Server may escalate to a longer ban or IP block.

**Prevention:**
- Retry policy on 429 MUST read `Retry-After` header (RFC 7231 §7.1.3, both delta-seconds and HTTP-date forms).
- If `Retry-After` exceeds a sane cap (e.g., 5 minutes), fail fast rather than wait.
- tenacity's `stop_after_attempt` + `wait_combine(wait_random_exponential, wait_from_response_header)` covers this.

**Phase to address:** Phase 3 (Retries/backoff).

---

### Pitfall 14: Jitter seeded once (constant across retries) — predictable backoff defeats thundering herd protection

**What goes wrong:**
```python
import random
JITTER = random.uniform(0, 1)  # ← seeded once at module import
def _backoff(attempt: int) -> float:
    return 2**attempt + JITTER  # always same jitter
```
All retries from the same process use the same jitter, defeating the whole point.

**Prevention:**
- Call `random.uniform(0, jitter_max)` INSIDE the backoff function, not at module level.
- Better: use `secrets.SystemRandom()` if jitter needs to be unpredictable across processes.
- Test: 100 calls to `_backoff(1)` should produce ~100 distinct values.

**Phase to address:** Phase 3 (Retries/backoff).

---

### Pitfall 15: Retries swallow `PrimaryAPIError` (status=ERROR application errors) — these MUST NOT be retried

**What goes wrong:**
matriz Primary API returns HTTP 200 with `{"status": "ERROR", "description": "Account not found"}`. The package raises `PrimaryAPIError`. If the retry decorator's `retry_on=(PrimaryAPIError,)` includes this (because `PrimaryAPIError` is a subclass of `MatrizAPIError`), the same application error is retried multiple times — useless.

**Prevention:**
- Retry policy: ONLY retry on TRANSPORT errors (`httpx.ConnectError`, `httpx.ReadTimeout`, `httpx.RemoteProtocolError`) and on HTTP 5xx + 429.
- NEVER retry on application errors (anything raised by `_raise_for_response` or the JSON status=ERROR check).
- Explicit `retry_on` tuple, no inheritance-based catch.
- Test: mock 200 OK with `{"status": "ERROR"}`, assert exactly ONE outgoing request.

**Phase to address:** Phase 3 (Retries/backoff).

---

### Pitfall 16: Retries delay user-visible cancellation on Ctrl-C — no asyncio cancel honored

**What goes wrong:**
Async retry decorator sleeps via `await asyncio.sleep(backoff)`. User Ctrl-C's. The asyncio.CancelledError propagates through the sleep. If the retry decorator catches `Exception` (CancelledError is BaseException in Python 3.8+ so this is OK), the cancellation is honored. But if the decorator catches `BaseException` (some old patterns) or wraps the sleep in a `try: ... except BaseException: pass`, Ctrl-C is silently swallowed and the next retry attempt fires.

**Prevention:**
- Retry decorator MUST NOT catch `BaseException`. Catch only `Exception` or specific exceptions.
- For the sync path: KeyboardInterrupt is BaseException, so `except Exception:` is safe.
- Test (async): start a task that retries on errors, cancel the task during a sleep, assert CancelledError propagates within 100ms.

**Phase to address:** Phase 3 (Retries/backoff).

---

### Pitfall 17: Structured `extra={}` fields collide with stdlib LogRecord attributes

**What goes wrong:**
```python
logger.info("request done", extra={"message": "OK", "name": "..."})
```
`LogRecord` has built-in attributes `message`, `name`, `levelname`, `pathname`, `lineno`, etc. Passing them in `extra` raises `KeyError: "Attempt to overwrite 'message' in LogRecord"` at runtime — but only if the logger is actually configured (in tests it may not be).

**Prevention:**
- Use a non-colliding prefix: `extra={"req_method": ..., "req_url": ..., "resp_status": ...}`.
- Or use `logger.makeRecord` with explicit keyword override checks.
- Add a unit test that emits a sample log record with the project's `extra` schema and checks no exception is raised.
- Reference: Python `logging.LogRecord` reserved attribute list (`asctime`, `created`, `exc_info`, `exc_text`, `filename`, `funcName`, `levelname`, `levelno`, `lineno`, `message`, `module`, `msecs`, `msg`, `name`, `pathname`, `process`, `processName`, `relativeCreated`, `stack_info`, `thread`, `threadName`).

**Phase to address:** Phase 4 (Structured logging).

---

### Pitfall 18: Refactor breaks 277 tests; "fix tests" becomes "weaken tests" silently

**What goes wrong:**
After the Client class refactor, 30 tests fail because `monkeypatch.setattr(pkg.client, "_token", ...)` no longer reaches production code. Developer "fixes" by changing assertions ("the test was over-specifying", "this is implementation detail"). The original invariant (that fixture-set token reaches the wire) is silently dropped. The test suite passes; the contract is no longer enforced.

**Prevention:**
- **Test refactor must be COMPENSATING, not LOWERING.** If a test was over-specifying, the COMMIT MESSAGE must explicitly say "test was over-specifying X; new test verifies the same invariant via Y".
- **Code review rule:** any PR that touches `tests/` and removes `assert` statements requires explicit justification.
- **Pre-refactor baseline:** before the refactor, record the test count, assertion count, and coverage percentage. After refactor, ALL three must be ≥ baseline. Coverage drops > 1% require explicit justification.
- **Add the "fixture reaches production" guard test (Pitfall 1) BEFORE the refactor**, so any silent fixture-failure surfaces immediately.

**Phase to address:** Every phase that touches `client.py` or `aio.py`. Phase 1 (Client class) is the most exposed.

---

### Pitfall 19: New matriz `aio.py` tests introduce `pytest-asyncio` flakiness

**What goes wrong:**
matriz has 0 existing async tests. Adding ~30 async tests in one phase triggers latent `pytest-asyncio` issues: event-loop scope mismatches, fixture teardown order bugs, `httpx.AsyncClient` reuse across loops (the documented anti-pattern in ARCHITECTURE.md). CI passes locally, flakes on GitHub Actions, or vice versa.

**Prevention:**
- Copy `packages/iol-client/tests/conftest.py` autouse async fixture verbatim — including the `await aio.aclose()` teardown step.
- Pin `pytest-asyncio` and `pytest-httpx` versions; don't rely on `>=`.
- Run new tests in isolation first (`pytest packages/matriz-client/tests/test_async_client.py -v`) before integrating with the full suite.
- Test parametrize with `pytest.mark.asyncio` explicitly even with `asyncio_mode = "auto"` for the first few tests to surface mode bugs.

**Phase to address:** Phase 5 (matriz `aio.py` creation).

---

### Pitfall 20: WR-01 (PRIMARY_ACCOUNT leak via PASS detail strings) regresses when adding a new mutating probe to matriz driver

**What goes wrong:**
WR-01 was identified in Phase 5 review: `main_matriz.py:1331,1391` interpolate `raw.get('account')` into `ProbeResult` detail strings, and `PRIMARY_ACCOUNT` is NOT in the `secrets` list. The fix is to add it to `secrets`. But a future contributor adding a new probe that uses `raw.get('account_id')` or `raw.get('cuit')` will re-introduce the leak because the redaction is opt-in.

**Prevention:**
- Promote the redaction to be COMPREHENSIVE: in `safe_print`, redact ALL substrings that are env-var values (cycle through env keys matching `PRIMARY_*`, `HIGYRUS_*`, `IOL_*` and add their values automatically).
- Document this expansion in `verification/redaction.py` and add a unit test that confirms a hypothetical new env var (`PRIMARY_FOO=secret-foo-1234`) is automatically redacted.
- Cross-package: ámbito, iol, higyrus drivers should benefit from the same auto-redaction.

**Phase to address:** Phase 6 (Driver bundle, WR-01..WR-08 close-out).

---

### Pitfall 21: WR-03 `_request` resource leak under HTTP/2 — switching to `http2=True` later silently regresses

**What goes wrong:**
WR-03 noted that the current `_request` flow doesn't explicitly close the response. With HTTP/1.1 this is fine. The latent risk: a future developer enables `httpx.Client(http2=True)` for performance and now every request leaks a stream until garbage collection.

**Prevention:**
- Refactor `_request` to use `with self._session.send(req) as resp:` or call `resp.close()` after extracting JSON.
- Add a comment near `httpx.Client(...)` construction: `# IMPORTANT: do not enable http2=True without auditing all _request flows for resp.close()`.
- mypy / ruff cannot catch this; rely on PR review and the comment.

**Phase to address:** Phase 6 (WR-03 close-out).

---

### Pitfall 22: WR-04 `_first_dict` silent failure regresses when adding new field_type_map probes

**What goes wrong:**
WR-04: `_first_dict` returns `None` for "no data", "non-list payload", and "non-dict first element" — three distinct cases collapsed into one. Adding new probes (e.g., for matriz `aio.py` regression) inherits the silent failure unless the helper is fixed.

**Prevention:**
- Replace `_first_dict` with a tuple return: `(first_dict, reason)` where reason is `Literal["ok", "no_data", "wrong_type"]`.
- Probes emit NO-DATA or WRONG-TYPE findings explicitly.
- Regression test: `_first_dict([])` returns `(None, "no_data")`, `_first_dict({})` returns `(None, "wrong_type")`, etc.

**Phase to address:** Phase 6 (WR-04 close-out), reused by Phase 5 (matriz `aio.py` regression sweep).

---

### Pitfall 23: WR-05 boilerplate refactor (18 sweep probes) lands without preserving each probe's idiosyncrasies

**What goes wrong:**
WR-05 recommends extracting `_envelope_probe()` to dedupe the 18 matriz sweep probes. The refactor MUST preserve the 2 risk probes (`probe_get_detailed_positions`, `probe_get_account_report`) that have NO envelope key. A mechanical refactor that doesn't read the existing tests carefully will break those two.

**Prevention:**
- Before refactoring, add a baseline test that asserts each of the 18 probes returns a `ProbeResult` with the expected status for a canned payload (snapshot test).
- Refactor INCREMENTALLY: extract 1 probe at a time, run the baseline test, commit. 18 atomic commits.
- Add an explicit `envelope_key: str | None = None` parameter so risk probes pass `envelope_key=None` to skip the check.

**Phase to address:** Phase 6 (WR-05 close-out).

---

### Pitfall 24: WR-06 `except Exception` tightening hides regressions in live driver runs

**What goes wrong:**
WR-06 recommends replacing `except Exception` with specific exception tuples. The drivers currently swallow unexpected exceptions and emit ERROR-MAP findings. Tightening to `except (httpx.HTTPError, json.JSONDecodeError, ValueError)` means a NEW exception type (e.g., a future `pydantic.ValidationError` if models migrate to Pydantic) PROPAGATES and aborts the driver mid-run, losing partial progress.

**Prevention:**
- Tighten incrementally: keep `except Exception` AND add specific arms BEFORE it. The specific arms log structured findings; the generic arm logs an ERROR-MAP with a stack trace BUT does not re-raise.
- Pattern:
  ```python
  try:
      ...
  except (httpx.HTTPError, json.JSONDecodeError) as exc:
      append_finding(fid, "EXPECTED", str(exc))
      return ProbeResult(name, "FINDING", ...)
  except Exception as exc:  # noqa: BLE001 — defensive catch-all
      append_finding(fid, "ERROR-MAP", repr(exc))  # explicit ERROR-MAP class
      log_stack_trace(exc)  # operator can debug
      return ProbeResult(name, "FAIL", ...)
  ```
- Cycle continues; operator sees the stack trace.

**Phase to address:** Phase 6 (WR-06 close-out).

---

### Pitfall 25: WR-07 `event_hooks` mutation without locking — async sweep tests against the shared singleton corrupt hooks

**What goes wrong:**
WR-07: `main_higyrus.py:233-318` mutates `aio._client.event_hooks` to capture query strings, then restores. Latent race condition if any concurrent caller exists. Adding matriz `aio.py` may introduce a similar capture helper; the same pattern is high-risk.

**Prevention:**
- For new capture helpers, INSTANTIATE a new `httpx.AsyncClient` for the capture instead of mutating the shared singleton. Cost: one extra TCP connection per probe — acceptable.
- If mutation is necessary, hold `aio._client_lock` for the duration of the swap+request+restore.
- Document this explicitly in the helper's docstring.

**Phase to address:** Phase 5 (matriz `aio.py`) and Phase 6 (WR-07 close-out).

---

### Pitfall 26: WR-08 line-length / PII key leakage regresses when adding new HIGY probes

**What goes wrong:**
WR-08: `main_higyrus.py:767` leaks `sorted(first.keys())` into the findings markdown, exposing PII-adjacent key names (`cbu`, `cuit`, `titular`). Adding new HIGY probes (e.g., for multi-account iteration deferred capability) may repeat the pattern.

**Prevention:**
- Provide a `_safe_key_descriptor(d: dict) -> str` helper in `verification/redaction.py` that returns `f"<{len(d)} keys, hidden>"`.
- Code-review checklist: any `dict.keys()` interpolated into a probe detail string must use the helper.
- Test: `_safe_key_descriptor({"cuit": "...", "cbu": "..."})` returns `"<2 keys, hidden>"`, NEVER the key names.

**Phase to address:** Phase 6 (WR-08 close-out, HIGY multi-account capability).

---

## Minor Pitfalls

### Pitfall 27: `typing.Protocol` for "client-like" too narrow → breaks subclasses

**What goes wrong:**
Defining `Protocol` for client-like objects (e.g., for the retry decorator to accept "anything with `_request`") is over-constrained: the Protocol locks in the exact `_request` signature. Subclasses or future variants with extra parameters fail Protocol checking.

**Prevention:** Keep Protocol methods to the minimum surface needed; use `*args, **kwargs` in Protocol signatures where appropriate. Or skip Protocol entirely and use duck-typing with explicit `hasattr` checks.

**Phase to address:** Phase 1 (Client class refactor).

---

### Pitfall 28: `from __future__ import annotations` + generic Client + dataclass fields — mypy edge cases

**What goes wrong:**
`from __future__ import annotations` makes all annotations strings. Combined with `Generic[T]` on `Client[T]` and dataclass fields, mypy strict may fail to resolve forward refs in certain configurations, especially with `slots=True`.

**Prevention:** Test the refactor with `mypy --strict` early. If issues arise, use `TYPE_CHECKING` guards for the generic parameter import and `typing.cast` in `__post_init__`.

**Phase to address:** Phase 1 (Client class refactor).

---

### Pitfall 29: structlog / tenacity stubs missing → mypy strict fails

**What goes wrong:**
Adding `tenacity` for retries or `structlog` for logging introduces dependencies without type stubs. mypy strict fails: `error: Cannot find implementation or library stub for module named "tenacity"`.

**Prevention:**
- Check `types-tenacity` exists (it doesn't — tenacity has inline types in recent versions; verify with `pip show tenacity` for `py.typed`).
- For libraries without stubs, add `[[tool.mypy.overrides]]` with `ignore_missing_imports = true` for ONLY the problematic module.
- Prefer libraries with inline types (`structlog` 23+ has `py.typed`, `tenacity` 8+ has it too).

**Phase to address:** Phase 3 (Retries), Phase 4 (Logging) — verify type compat before introducing the dependency.

---

### Pitfall 30: matriz cycle_report `_REPO_ROOT` symlink edge case (IN-related to CR-02)

**What goes wrong:**
CR-02 noted the path-traversal defence in `verification/cycle_report.py` doesn't guard `read_text` against `OSError` / `PermissionError`. Latent issue triggered on macOS where `/Users/<name>` may be symlinked.

**Prevention:**
- Wrap `read_text` in a `try/except OSError` and treat as "missing test file".
- Document `_REPO_ROOT` computation in module docstring.
- Add a test that mocks `Path.read_text` to raise `PermissionError`, assert cycle closure marks `missing` rather than crashing.

**Phase to address:** Phase 6 (CR-02 close-out).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Copy matriz `client.py` → `aio.py` instead of dedup-first | matriz async ready in 1 day | Two bug surfaces forever; future fixes 2x cost | Never — the milestone explicitly tackles dedup |
| `monkeypatch.setattr(..., raising=False)` everywhere | Tests don't break when attribute moves | Silent test failures after refactor | Only on attributes guaranteed to exist; use `raising=True` post-refactor |
| Retry decorator applied to `_request` blanket | One-line change | Retries non-idempotent mutations | Never — must be opt-in per call |
| `logging.basicConfig` "just in tests" | Quick test scaffolding | Test logger config leaks via import order | Never in library code; only in `main_*.py` drivers |
| `_token` shared globally in matriz across sync/async/ws | No new abstraction | 3-way race conditions | Never — token store class is mandatory |
| `<!-- auto-generated below -->` single-marker append | Quick findings.py fix | Marker duplication on re-runs | Only with BEGIN/END marker pair and parser test |
| `except Exception` blanket in drivers | Drivers don't abort | Real bugs classified as ERROR-MAP findings | Only as the OUTER catch-all with stack trace logging |
| `# type: ignore` on Protocol mismatches | mypy passes | Breaking changes go undetected | When alternative is rewriting type system; document each one |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| httpx + retries | Retry all methods by default | Tag GETs as `idempotent=True`, retry only those + transport errors |
| httpx + structured logging | `logger.debug("req=%s", req)` (leaks headers) | Use `_redact_headers(req.headers)` before logging |
| httpx + 401 + retry | Include `AuthError` in `retry_on=` | Handle 401 explicitly with one re-auth attempt |
| asyncio + threading (matriz ws_client) | Share `_token` mutable global | `TokenStore` class with `threading.Lock` (works in both contexts) |
| pytest-asyncio + httpx.AsyncClient | Reuse client across event loops | `await aclose()` in fixture teardown |
| pytest + monkeypatch + Client refactor | `monkeypatch.setattr(pkg.client, "_token", ...)` | Compat shim via `ModuleType.__getattr__/__setattr__`, plus guard test |
| python logging + library | `logging.basicConfig` in `__init__.py` | `logging.getLogger(__name__).addHandler(logging.NullHandler())` |
| tenacity + idempotency | Default retry on all methods | Explicit `retry_if_exception_type` tuple, never include `AuthError` |
| verification/findings.py + re-runs | Truncate and rewrite file | BEGIN/END marker zones with parser test |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Retry decorator without `Retry-After` honor | Server escalates rate limit; sustained 429s | Read `Retry-After` header; cap at 5min | First sustained rate-limit episode |
| `random.uniform` outside backoff function | Predictable backoff timing (thundering herd) | Compute jitter inside `_backoff(attempt)` call | Multi-process deployment hitting same endpoint |
| Async `httpx.AsyncClient` shared across event loops | `RuntimeError: Event loop is closed` mid-request | One client per loop; `aclose()` in teardown | Concurrent test runs or multi-loop apps |
| Token refresh inside per-request `_request` without lock (async) | Thundering herd: N concurrent requests all refresh | Double-checked locking with `asyncio.Lock` | First high-concurrency deployment |
| `httpx.Client(http2=True)` without `resp.close()` | Connection pool exhaustion | Use `with self._session.send(...) as resp:` | When http2 is enabled in `_session` construction |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| DEBUG logging of `Authorization` headers | Token leaks to log aggregator (Sentry, Datadog, CloudWatch) | In-library `_redact_headers()`; regression test asserting no token substring in caplog |
| DEBUG logging of request bodies for `/token` / `/login` endpoints | Password leaks to logs | `_LOG_BODY_DENY_PATHS` set; skip body logging for auth endpoints |
| `verification/redaction.py` used in drivers but library logs unredacted | Production deployments leak credentials even though drivers don't | Library has its OWN redact helper (NOT importing from verification/) |
| `PRIMARY_ACCOUNT` not in driver `secrets` list (WR-01) | Account ID in build logs | Auto-redact ALL env-var values matching `*_USER`, `*_PASSWORD`, `*_ACCOUNT`, `*_TOKEN`, `*_API_KEY` patterns |
| `dict.keys()` interpolated into findings markdown (WR-08) | PII-adjacent key names in committed files | `_safe_key_descriptor` helper that returns `<N keys, hidden>` |
| Pickle / deepcopy of Client containing token | Token written to pickle file on disk; deepcopy clone shares connection pool | Override `__deepcopy__`, `__reduce__` to raise |
| Retry of POST `cancel_order` after timeout | Duplicate cancel; or new order created during retry of `new_order` | Per-call `idempotent=False`; never retry mutating endpoints |
| `assert _token is not None` (CONCERNS.md) | Stripped under `-O`; runtime crash with unclear AttributeError | Replace with `if _token is None: raise RuntimeError(...)` |

---

## "Looks Done But Isn't" Checklist

- [ ] **Client class refactor:** Compat shim's `__getattr__` and `__setattr__` actually forward to default client — verify with the "fixture reaches production" guard test
- [ ] **Client class refactor:** `configure()` semantics documented AND tested with parity test (explicit instance unaffected by configure)
- [ ] **Client class refactor:** `__deepcopy__` and `__reduce__` overridden to raise
- [ ] **Client class refactor:** `__enter__`/`__exit__` and `__aenter__`/`__aexit__` present, atexit NOT used for async
- [ ] **Sync/async dedup:** `_core.py` does NOT import from `client.py` or `aio.py` (lint rule + grep CI check)
- [ ] **Sync/async dedup:** sync and async fixtures use DIFFERENT sentinel tokens to detect cross-leak
- [ ] **Retries:** `idempotent` keyword on `_request`; defaults to False; all GET endpoints tagged True
- [ ] **Retries:** 401 handled in `_request` (NOT in retry decorator); exactly ONE re-auth attempt
- [ ] **Retries:** `Retry-After` header honored on 429
- [ ] **Retries:** Jitter computed inside `_backoff(attempt)`, not at module level
- [ ] **Retries:** `PrimaryAPIError`, `HigyrusAPIError`, application errors NEVER in `retry_on=` tuple
- [ ] **Retries:** asyncio CancelledError propagates through retry sleeps (no `except BaseException`)
- [ ] **Logging:** `NullHandler` added in every `__init__.py`
- [ ] **Logging:** `_redact_headers` defined IN-LIBRARY (not imported from `verification/`)
- [ ] **Logging:** Regression test: caplog assertion that token substring never appears
- [ ] **Logging:** `extra={}` fields use non-colliding prefix; no `message`, `name`, etc.
- [ ] **Logging:** Auth endpoints (`/token`, `/login`) skip body logging
- [ ] **matriz `aio.py`:** Created AFTER sync/async dedup pattern is established; shares `_core.py`
- [ ] **matriz `aio.py`:** Token cache uses `TokenStore` class shared with `ws_client.py`, NOT raw module global
- [ ] **matriz `aio.py`:** Driver `main_matriz.py` extended with async probes mirroring sync probes
- [ ] **Driver bundle:** `findings.py` uses BEGIN/END marker zones; parser unit-tested for round-trip
- [ ] **Driver bundle:** D-MATZ-27 dedupe key is `(finding_id, classification)` tuple, not substring
- [ ] **Driver bundle:** Operator rationale lines preserved across re-runs (parser test asserts)
- [ ] **Test invariants:** 277-test baseline count and assertion count documented BEFORE refactor; post-refactor must match or exceed
- [ ] **Test invariants:** `monkeypatch.setattr(..., raising=False)` audit — convert to `raising=True` where attribute now reliably exists
- [ ] **CI:** Live `main_*.py` smoke runs PASS — driver bundle doesn't accumulate findings on re-runs
- [ ] **WR-01..WR-08:** All 8 concerns have a closing commit and a regression test (where applicable)

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Client class refactor breaks 277 tests silently (Pitfall 1) | MEDIUM | Add the "fixture reaches production" guard test; force-fail until compat shim is correct; revert the refactor commit and redo |
| Sync/async dedup re-couples (Pitfall 3) | LOW | Add the import-linter / grep CI rule; revert the `_core.py` import |
| Retry mutates state twice (Pitfall 4) | HIGH | Audit production logs for duplicate POSTs; manually reverse duplicated orders if any; add `idempotent` keyword as hotfix |
| Library configures root logger (Pitfall 6) | LOW | Remove `logging.basicConfig` calls; add NullHandler; document the breaking-fix in changelog |
| Token leaks in DEBUG logs (Pitfall 7) | HIGH | Rotate the leaked token IMMEDIATELY; add `_redact_headers`; audit log retention to determine exposure window |
| matriz `aio.py` is a copy of `client.py` (Pitfall 8) | HIGH | Rewrite matriz dedup as part of Phase 2 follow-up; accept 1-cycle delay |
| matriz token race conditions (Pitfall 9) | MEDIUM | Introduce `TokenStore` class; refactor all three surfaces to use it; regression test the race |
| `findings.py` accumulates duplicates (Pitfall 10) | LOW | Implement BEGIN/END markers; manually clean up existing duplicate findings; commit canonical baseline |
| WR-01 PRIMARY_ACCOUNT leak in logs (Pitfall 20) | MEDIUM | Audit CI logs for leaked account IDs; if leaked, document in findings; promote auto-redaction |
| 401 retry storm (Pitfall 5) | LOW | Patch `_request` to handle 401 explicitly with one re-auth; remove `AuthError` from `retry_on=` |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1: monkeypatch silent breakage | Phase 1 (Client class, package 1) | "Fixture reaches production" guard test in conftest.py; 277 tests still green |
| 2: configure() scope confusion | Phase 1 (Client class, package 1) | Parity test: explicit Client unaffected by configure() |
| 3: Dedup re-couples via import | Phase 2 (Sync/async dedup) | grep CI check / import-linter rule; cross-leak detection with distinct sentinels |
| 4: Retry mutates state | Phase 3 (Retries/backoff) | `idempotent` keyword on every endpoint; mutating POST never-retried regression test |
| 5: Retry through expired token | Phase 3 (Retries/backoff) | 401 → 200 test asserts exactly 2 requests (one with refreshed token) |
| 6: basicConfig in library | Phase 4 (Structured logging) | grep CI check: no `basicConfig` / `logging.root` in `packages/*/src/`; root-handlers unchanged test |
| 7: Credentials in DEBUG logs | Phase 4 (Structured logging) | caplog assertion: token substring never present |
| 8: matriz aio.py copy-paste | Phase 2 prerequisite to Phase 5 | matriz `client.py` and `aio.py` share `_core.py`; no duplicate `_unwrap` |
| 9: matriz token race (3-way) | Phase 5 (matriz aio.py) | Threading race test: concurrent refresh + read returns same token |
| 10: findings.py marker duplication | Phase 6 (Driver bundle) | BEGIN/END marker parser unit test |
| 11: Pickle/deepcopy Client | Phase 1 (Client class) | `pytest.raises(TypeError)` on `copy.deepcopy(client)` |
| 12: atexit close async client | Phase 1 (Client class) | No atexit registered for async; context manager test passes |
| 13: Ignore Retry-After | Phase 3 (Retries/backoff) | 429 with Retry-After: 60 → backoff is ≥60s test |
| 14: Constant jitter | Phase 3 (Retries/backoff) | 100x `_backoff(1)` produces ≥95 distinct values |
| 15: Retry PrimaryAPIError | Phase 3 (Retries/backoff) | Mock 200 + status=ERROR → exactly 1 request |
| 16: Swallow CancelledError | Phase 3 (Retries/backoff) | Async cancel test propagates within 100ms |
| 17: extra={} attribute collision | Phase 4 (Structured logging) | Unit test: sample log call with project's extra schema does not raise |
| 18: Weaken tests during fix | Every phase touching client/aio | Coverage and assertion-count baseline check |
| 19: pytest-asyncio flakiness in matriz | Phase 5 (matriz aio.py) | CI run × 3 with same seed; conftest.py copies iol-client pattern verbatim |
| 20: WR-01 PRIMARY_ACCOUNT regression | Phase 6 (WR-01) | Auto-redact env-var values; test new var auto-included |
| 21: WR-03 http2 resource leak | Phase 6 (WR-03) | resp.close() audit; comment near httpx.Client construction |
| 22: WR-04 _first_dict silent | Phase 6 (WR-04) and Phase 5 reuse | Tuple return; explicit NO-DATA/WRONG-TYPE findings |
| 23: WR-05 boilerplate refactor | Phase 6 (WR-05) | Per-probe snapshot test BEFORE refactor; 18 atomic commits |
| 24: WR-06 except Exception tightening | Phase 6 (WR-06) | Specific arms BEFORE generic; generic still emits ERROR-MAP with stack trace |
| 25: WR-07 event_hooks race | Phase 5 (matriz aio.py) + Phase 6 (WR-07) | New helpers instantiate a fresh AsyncClient; or hold `_client_lock` |
| 26: WR-08 PII key leakage | Phase 6 (WR-08) | `_safe_key_descriptor` helper; never serializes key names |
| 27: Protocol too narrow | Phase 1 (Client class) | Protocol uses *args/**kwargs; duck-typed alternative documented |
| 28: future annotations + Generic | Phase 1 (Client class) | mypy --strict run; TYPE_CHECKING guards if needed |
| 29: Missing stubs (tenacity/structlog) | Phase 3 / Phase 4 | Verify `py.typed` presence; mypy override scoped to module |
| 30: cycle_report symlink edge | Phase 6 (CR-02) | OSError-safe read_text; mock PermissionError test |

---

## Cross-Feature Integration Pitfalls

**Retries × Auth (Pitfalls 4, 5, 15):** The retry layer MUST NOT catch `AuthError`, `PrimaryAPIError`, `HigyrusAPIError`. 401 is handled explicitly in `_request()` with exactly one re-auth attempt. Application errors never retry. Transport errors and 5xx/429 retry per policy. ALL of this is per-package and must be mirrored sync↔async.

**Retries × `mutation_gate` (Pitfall 4):** The `verification/mutation_gate.py` double-gate (`VERIFY_MUTATING=1` AND remarkets hostname match) prevents accidental prod mutations at the DRIVER layer. The PACKAGE-layer retry must independently refuse to retry mutating endpoints, because the gate doesn't help if the first request already succeeded server-side.

**Logging × Redaction × Verification (Pitfall 7):** `verification/redaction.py` is a DRIVER concern. The library MUST have its own `_redact_headers` and `_redact_body` helpers. The library does NOT import from `verification/` (not a packaged dependency).

**Dedup × Tests × monkeypatch (Pitfalls 1, 3, 18):** The refactor moves state from module-level to instance-level. Existing tests use `monkeypatch.setattr(pkg.client, "_token", ...)`. The compat shim must route module-level attribute access to the default instance. The shim is the riskiest piece of the milestone; it deserves its OWN regression test suite.

**matriz aio.py × ws_client × Token Store (Pitfall 9):** Three surfaces (sync, async, daemon thread) accessing the same token cache require a SHARED concurrent-safe token store. `asyncio.Lock` doesn't help the daemon thread; `threading.Lock` works in all three contexts (the async path can grab a threading.Lock briefly via `asyncio.to_thread`).

**Driver bundle × CI re-runs (Pitfall 10):** The findings file must be IDEMPOTENT across re-runs. Adding a CI workflow that runs `main_*.py` automatically would catch this immediately; the current manual operator-driven runs delay detection.

---

## Sources

- `/Users/sebadlf/development/becerra/market-libs/.planning/codebase/CONCERNS.md` — module-level singleton state issues (HIGH), httpx client never closed, no retries/logging in current code, assert use in production code
- `/Users/sebadlf/development/becerra/market-libs/.planning/codebase/TESTING.md` — `monkeypatch.setattr(pkg.client, "_token", ..., raising=False)` autouse fixture pattern in every package's conftest.py
- `/Users/sebadlf/development/becerra/market-libs/.planning/codebase/CONVENTIONS.md` — module-level state pattern, asyncio.Lock for token refresh in async modules
- `/Users/sebadlf/development/becerra/market-libs/.planning/codebase/ARCHITECTURE.md` — anti-patterns documented (importing aio in sync context, sharing aio state across event loops), ws_client.py reads `_rest._token` directly (fragile)
- `/Users/sebadlf/development/becerra/market-libs/.planning/milestones/v1.0-phases/05-matriz-verification/05-REVIEW.md` — CR-01 (_request returns Any), CR-02 (symlink path traversal), WR-01..WR-08 detailed analysis
- `/Users/sebadlf/development/becerra/market-libs/.planning/todos/pending/matriz-driver-findings-file-handling.md` — D-MATZ-27 dedupe and append-only refactor requirements
- `/Users/sebadlf/development/becerra/market-libs/.planning/PROJECT.md` — v1.1 milestone scope, target features, key decisions
- Python logging cookbook: "Configuring logging for a library" — official guidance on `NullHandler`
- Python data model: "Customizing module attribute access" — `ModuleType` subclass with `__getattr__`/`__setattr__`
- Python `logging.LogRecord` documentation — reserved attribute names
- httpx documentation: `AsyncClient` event-loop binding, http2 connection pool semantics
- tenacity documentation: `retry_if_exception_type`, `wait_combine` patterns
- RFC 7231 §7.1.3 — `Retry-After` header semantics

---

*Pitfalls research for: market-libs v1.1 Tech Debt Cleanup refactor over verified v1.0 baseline*
*Researched: 2026-06-10*
*Confidence: HIGH (rooted in existing codebase concerns + Phase 5 code review + deferred-todos doc; cross-referenced against Python stdlib and library best practices)*
