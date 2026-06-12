# Codebase Concerns

**Analysis Date:** 2026-05-27

## Tech Debt

**Module-level global state (all packages):**
- Issue: Every client stores credentials, token, and HTTP session as module-level globals. This design works for single-process, single-credential usage but prevents multi-tenant or per-request credential scoping without monkey-patching.
- Files: `packages/matriz-client/src/matriz_client/client.py` (L58-66), `packages/iol-client/src/iol_client/client.py` (L50-55), `packages/higyrus-client/src/higyrus_client/client.py` (L50-58), `packages/wallets-client/src/wallets_client/client.py` (L34-36), `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` (L42-44)
- Impact: Impossible to use two different credentials in the same process (e.g., two IOL accounts) without forking separate processes. Tests must patch internal `_token`, `_user`, etc. directly.
- Fix approach: Introduce an optional `Client` class that holds state per-instance, keeping the module-level API as a convenience singleton. This is a breaking change so version accordingly.

**wallets-client is a skeleton with no domain endpoints:**
- Issue: `wallets_client.client` and `wallets_client.aio` only expose the internal `_request` helper. No actual endpoint functions exist. The default `_base_url` is a placeholder (`https://api.wallets.example`).
- Files: `packages/wallets-client/src/wallets_client/client.py`, `packages/wallets-client/src/wallets_client/aio.py`
- Impact: The package is not usable for any real business logic. Publishing it at v0.1.0 is misleading.
- Fix approach: Either implement endpoint functions matching the Wallets API spec or mark the package explicitly as a stub in its README and hold it at pre-release (0.0.x) until it has real coverage.

**iol-client has no account/portfolio/order endpoints:**
- Issue: Only market data and instrument listing functions are implemented (`get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type`). IOL's API covers orders, portfolio, account balances, and more — none of which are present.
- Files: `packages/iol-client/src/iol_client/client.py`, `packages/iol-client/src/iol_client/aio.py`
- Impact: Using this client for anything beyond price queries requires callers to call `_request` directly against undocumented paths.
- Fix approach: Add typed endpoint wrappers for the IOL portfolio, order, and account endpoints.

**IOL sync client does not use the `refresh_token`:**
- Issue: IOL's OAuth2 password grant returns both `access_token` and `refresh_token`. The client ignores `refresh_token` and re-authenticates from scratch (password grant) on every token expiry.
- Files: `packages/iol-client/src/iol_client/client.py` (L85-108), `packages/iol-client/src/iol_client/aio.py` (L88-111)
- Impact: Every token refresh sends the user's password over the wire unnecessarily. If IOL adds IP-based brute-force detection, repeated password grants could trigger lockouts.
- Fix approach: Store `refresh_token` alongside `access_token` and attempt `grant_type=refresh_token` first; fall back to password grant only on refresh failure.

**Duplicate code between sync and async modules:**
- Issue: Each package duplicates virtually identical logic between `client.py` (sync) and `aio.py` (async): the `configure()` function, `_raise_for_response()`, the `_request` plumbing, and all endpoint wrappers. Changes to one must be manually mirrored to the other.
- Files: All `*/client.py` and `*/aio.py` pairs across all five packages.
- Impact: Any bug or behavior change must be applied twice per package (ten files total for five packages), increasing the chance of divergence over time. The Higyrus async `_request` already has slight deviations from its sync counterpart in the `drop_none` param handling path.
- Fix approach: Extract shared pure logic (param building, error classification, token TTL math) into a shared internal helper module per package. Keep the sync/async split only at the I/O boundary.

**ambito-financiero-client hardcodes a browser User-Agent:**
- Issue: The client sends a Chrome browser User-Agent because the Ámbito Financiero API returns 403 for `python-httpx/...` agents. This is a fragile workaround that mimics a browser.
- Files: `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` (L36-44), `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py` (L32-64)
- Impact: The spoofed agent string references Chrome 124 (released in 2024). If Ámbito Financiero tightens bot detection (e.g., requires JS challenges, checks for specific Chrome versions, or adds header consistency checks), the client will silently break with no clear error.
- Fix approach: Monitor Ámbito's response; update the agent string as browser versions evolve. Consider extracting `_DEFAULT_USER_AGENT` to a named constant with an explicit comment noting the version to update. Long-term: investigate whether Ámbito offers an official API key path.

## Security Considerations

**Credentials exposed in module-level string variables:**
- Risk: `_user` and `_password` are stored as plain `str` in module globals for the lifetime of the process. They are readable via `module._password` from any code in the same process.
- Files: `packages/matriz-client/src/matriz_client/client.py` (L59-60), `packages/iol-client/src/iol_client/client.py` (L52-53), `packages/higyrus-client/src/higyrus_client/client.py` (L52-53)
- Current mitigation: No mitigation; credentials are intentionally stored for re-authentication.
- Recommendations: No immediate action needed for CLI/script use. If these clients run inside a web framework (FastAPI, Django) serving multiple users, revisit to scope credentials per-request via dependency injection rather than module globals.

**assert statements used for runtime invariants in production code:**
- Risk: Python's `-O` (optimize) flag strips `assert` statements. Any code path that relies on an `assert` for a runtime check (not a test assertion) will silently pass through the check in optimized builds.
- Files: `packages/matriz-client/src/matriz_client/client.py` (L157: `assert _token is not None`), `packages/matriz-client/src/matriz_client/ws_client.py` (L140), `packages/iol-client/src/iol_client/client.py` (L126), `packages/iol-client/src/iol_client/aio.py` (L139), `packages/higyrus-client/src/higyrus_client/client.py` (L176), `packages/higyrus-client/src/higyrus_client/aio.py` (L200, L233, L264, L302, L325, L345)
- Current mitigation: None of the packages run with `-O` in their documented invocations. The asserts around `_token is not None` would surface as `AttributeError` anyway since `_token` is already narrowed by the `_ensure_token()` call above.
- Recommendations: Replace `assert _token is not None` with `if _token is None: raise RuntimeError(...)` for production invariants. For `assert isinstance(raw, list)` / `assert isinstance(raw, dict)` in higyrus endpoints, convert to proper type checks that raise `HigyrusAPIError` with a descriptive message.

## Performance Bottlenecks

**Synchronous httpx clients never closed (resource leak):**
- Problem: `httpx.Client` instances created at module import time for matriz, iol, higyrus, wallets, and ambito sync clients are never explicitly closed. There is no `close()` or context-manager support on any sync client module.
- Files: `packages/matriz-client/src/matriz_client/client.py` (L65: `_session = httpx.Client(...)`), `packages/iol-client/src/iol_client/client.py` (L55: `_client = httpx.Client(...)`), `packages/higyrus-client/src/higyrus_client/client.py` (L58), `packages/wallets-client/src/wallets_client/client.py` (L36), `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` (L44)
- Cause: The sync modules expose no `close()` function and the `httpx.Client` is not used as a context manager.
- Improvement path: Add a `close()` function to each sync client module and expose it in `__all__` (matching how `aio.aclose()` exists for async). Alternatively, use `atexit.register` to close on process exit.

**No retry or backoff logic for transient failures:**
- Problem: All HTTP requests fail immediately on network errors or 5xx responses. There is no retry with exponential backoff.
- Files: All `_request` functions across all five packages.
- Cause: By design (thin client), but makes the libraries fragile in production environments with intermittent connectivity.
- Improvement path: Add optional `max_retries` parameter to `configure()` functions. Use httpx transport or a thin retry wrapper (e.g., `tenacity`) only on idempotent GET requests; never retry order mutations.

## Fragile Areas

**WebSocket module accesses private REST client internals:**
- Files: `packages/matriz-client/src/matriz_client/ws_client.py` (L65: `url = _rest._base_url`, L140: `assert _rest._token is not None`, L150: `header={"X-Auth-Token": _rest._token}`)
- Why fragile: `ws_client` directly reads `_rest._base_url` and `_rest._token` — private module variables. Any rename or structural change to `client.py` silently breaks `ws_client.py`.
- Safe modification: Before changing `_base_url` or `_token` variable names in `client.py`, grep for all references in `ws_client.py`. Long-term: expose a public accessor `get_token()` or `get_base_url()` from `client.py`.
- Test coverage: The existing tests in `test_ws_client.py` do monkeypatch `_rest._base_url` and `_rest._token`, so breakage is detectable.

**Ambito async `configure()` does not rebuild the AsyncClient when user_agent changes:**
- Files: `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py` (L44-52)
- Why fragile: If `_client` is already initialized (i.e., a request has been made), calling `configure(user_agent="...")` updates `_client.headers["User-Agent"]` directly. However, if `_client` is `None` (not yet initialized), the update is lost — the stored `_user_agent` is used only at `_ensure_http_client()` time. The sync `client.py` has the same pattern but directly mutates `_client.headers` since the client is always initialized at module load.
- Safe modification: In `aio.configure()`, if `_client is not None`, update the headers. If `_client is None`, store in `_user_agent` as now. This is already what the code does, so the issue only manifests if `aclose()` is called and then `configure(user_agent=...)` is called before the next request — the user agent reverts to whatever was set at close time since `_ensure_http_client()` re-reads `_user_agent`. Actually this is fine — track this if future behavior changes `_user_agent` default.

**Token TTL relies on `time.time()` without clock skew handling:**
- Files: All `_ensure_token()` implementations — `packages/matriz-client/src/matriz_client/client.py` (L91-95), `packages/iol-client/src/iol_client/client.py` (L111-114), `packages/higyrus-client/src/higyrus_client/client.py` (L130-134), and their `aio.py` counterparts.
- Why fragile: If the system clock jumps backward (NTP correction, VM resume), `time.time() - _token_ts` may become negative or very small, effectively making a fresh token appear as though it needs refresh. Conversely, a large forward jump may cause an unexpired token to be treated as expired.
- Safe modification: This is low-risk in practice. Document the assumption. If deploying in VMs with frequent snapshots/resume cycles, add a sanity check: `max(0, time.time() - _token_ts)`.

## Scaling Limits

**Module-level singleton httpx clients:**
- Current capacity: One HTTP connection pool per package per process.
- Limit: Under high concurrency (many async tasks), the single `httpx.AsyncClient` per package is shared. `httpx` handles this with connection pooling internally, but the `asyncio.Lock()` used to lazily initialize the client is a choke point on first initialization only — subsequent calls skip the lock.
- Scaling path: The current design is fine for most use cases. For extreme throughput, callers can use multiple processes or accept the shared pool model.

## Dependencies at Risk

**`websocket-client` (sync WebSocket library in matriz-client):**
- Risk: `websocket-client` runs the WebSocket event loop in a background `threading.Thread`. It is a synchronous, thread-based library — not asyncio-compatible. This means `matriz-client` has no async WebSocket counterpart.
- Impact: Users who want async WebSocket streaming must either run the sync client in a thread executor or use a different library. The `aio` module pattern used by all other packages is absent for the WebSocket layer.
- Migration plan: Consider adding `websockets` or `httpx-ws` as an optional async WebSocket dependency and providing an async `ws_connect` counterpart.

**`python-dotenv` as a required runtime dependency:**
- Risk: All five packages list `python-dotenv` as a hard `dependency`, not optional. This means every downstream user of any client package gets `python-dotenv` installed even if they manage environment variables themselves (e.g., via Docker secrets, AWS SSM, or manual `os.environ` assignment).
- Impact: Minor dependency bloat for callers who do not use `.env` files.
- Migration plan: Move `load_dotenv()` calls behind a conditional import or make `dotenv` an optional extra. Alternatively, document that callers who do not use `.env` files should call `configure()` directly.

## Missing Critical Features

**No PyPI publishing in the release workflow:**
- Problem: The release workflow (`release.yml`) builds a wheel and sdist and creates a GitHub Release, but does not publish to PyPI. Packages can only be installed from GitHub Releases or via local workspace references.
- Blocks: Any downstream consumer who wants to `pip install iol-client` from PyPI cannot do so.

**No async WebSocket support in matriz-client:**
- Problem: The WebSocket layer (`ws_client.py`) is sync-only using `websocket-client` and a background thread. There is no `aio_ws_connect` or equivalent async interface.
- Blocks: Projects built entirely on `asyncio` (FastAPI, etc.) must use `loop.run_in_executor()` workarounds to use the WebSocket functionality.

**No structured logging:**
- Problem: None of the packages emit any log output (no `logging` module usage anywhere in production code). Auth failures, token refreshes, and retried requests are invisible unless the caller explicitly wraps calls.
- Blocks: Observability in production deployments. Debugging token expiry issues or transient network failures requires adding print statements or custom wrappers.

## Test Coverage Gaps

**No async test for matriz-client:**
- What's not tested: `matriz-client` has no `aio` module, so this is not applicable. However, the ws_client `ws_connect()` and `ws_disconnect()` integration paths (the actual `websocket.WebSocketApp.run_forever` lifecycle) are not tested — only unit-level frame parsing and message dispatch are covered.
- Files: `packages/matriz-client/tests/test_ws_client.py`
- Risk: A real WebSocket reconnect scenario or connection timeout edge case could fail silently.
- Priority: Medium

**No coverage minimum enforced:**
- What's not tested: The CI collects coverage XML files but does not fail the build if coverage drops below any threshold. There is no `--cov-fail-under` flag in the CI test command.
- Files: `.github/workflows/ci.yml` (L102-106), `pyproject.toml` (`[tool.coverage.report]` section has no `fail_under`)
- Risk: Coverage can silently regress without any CI gate.
- Priority: Medium

**wallets-client has minimal test surface:**
- What's not tested: `wallets-client` has only 3 sync tests and 1 async test, all at the `_request` plumbing level. There are no endpoint-level tests because no domain endpoints exist.
- Files: `packages/wallets-client/tests/test_client.py`, `packages/wallets-client/tests/test_async_client.py`
- Risk: When endpoints are added, there is no established test pattern to follow within the package.
- Priority: Low (blocked by the skeleton nature of the package)

**iol-client has no model layer tests:**
- What's not tested: IOL client endpoints return `dict[str, Any]` directly — there are no Pydantic models or dataclasses for IOL responses. This means malformed API responses cannot be tested for safety.
- Files: `packages/iol-client/src/iol_client/client.py` (all endpoints return raw `dict`)
- Risk: API shape changes from IOL silently produce wrong data rather than raising structured errors.
- Priority: Medium

---

*Concerns audit: 2026-05-27*
