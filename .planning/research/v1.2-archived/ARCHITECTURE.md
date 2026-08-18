# ARCHITECTURE RESEARCH — v1.2 Architecture + Auth/Ergonomics Carry-forwards

**Domain:** v1.2 milestone integration analysis for 4 financial-API HTTP client packages (Python 3.12+, httpx sync+async, tenacity, per-package standalone wheels).
**Researched:** 2026-06-14
**Confidence:** HIGH (post-v1.1 architecture is fully validated — 907 tests + LIVE-01 PASS × 4)

---

## 0. Scope Recap

The v1.1 architecture is **frozen for v1.2**:
- `Client` + `AsyncClient` classes per package, backed by `_ClientState` (per-instance frozen-slots dataclass).
- PEP 562 `__getattr__` shim in `pkg.client` + `pkg.aio` modules preserves top-level `pkg.get_X(...)` API for external consumers.
- `_core.py` (pure builders/parsers) cannot import `client.py`/`aio.py` (import-linter contract).
- Identity invariant B8: `aio._raise_for_response is client._raise_for_response is _core.raise_for_response`.
- matriz-only: `TokenStore` 3-way concurrency + `_refresh_policy` + `ws_client.py` daemon thread.
- Drivers `main_*.py` consume top-level `pkg.get_X(...)` via the PEP 562 shim; use INT-01 idiom (`_get_default()._state.base_url`) for state access.

The v1.2 milestone (`.planning/PROJECT.md:26-45`) layers SIX features on top, all non-breaking:
1. Driver migration × 4 (`main_*.py` → instantiate `Client()`).
2. unasync/codegen single-source (spike-validated).
3. Final live re-verification (LIVE-01-equivalent).
4. IOL refresh_token disk persistence.
5. `Client.from_env()` × 4.
6. `client.with_options(max_retries=N)` × 4.

---

## 1. System Overview — Target v1.2 Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  External consumers (UNCHANGED — top-level API preserved 100%)              │
│      import iol_client                                                       │
│      iol_client.login()                                                      │
│      quote = iol_client.get_quote("GGAL")                                    │
│      # PEP 562 shim still delegates to _get_default().get_quote(...)         │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
┌─────────────────────────────────────────────────────────────────────────────┐
│  In-repo drivers (MIGRATED in v1.2 — direct Client instantiation)            │
│      from iol_client import Client                                           │
│      client = Client.from_env(max_retries=2)                                 │
│      with client:                                                            │
│          quote = client.get_quote("GGAL")                                    │
│          rare_call = client.with_options(max_retries=5).get_instruments(...) │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  pkg/client.py + pkg/aio.py — generated from single source (v1.2)           │
│   - codegen approach TBD via Phase 0 spike                                   │
│   - Identity invariant B8 preserved (alias still resolves to _core)         │
│   - Top-level shims still here for compat (pkg.login(), pkg.get_X(...))     │
│   - Adds: Client.from_env(), client.with_options(...)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  pkg/_core.py (UNCHANGED — already single-source via Phase 7)                │
│  pkg/_state.py (UNCHANGED, but IOL gains optional disk-cache hook)          │
│  pkg/_transport.py + pkg/_atransport.py (UNCHANGED)                          │
│  pkg/_logging.py (UNCHANGED)                                                 │
│  iol_client/_token_cache.py (NEW — IOL-only disk persistence)               │
│  pkg/_env.py (NEW — per-package env-var contract for from_env())             │
│  matriz_client/_token_store.py + _refresh_policy.py (UNCHANGED)              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Question-by-Question Integration Analysis

### 2.1 Driver Migration Integration

**(A) Where does the new `Client()` instance live?**

Decision: **One module-level `Client()` per driver script, instantiated inside `main()` once**, NOT one per probe.

- Probes inherit the cached token, refresh_token, http_client, RetryTransport — instantiating per-probe would cause N OAuth handshakes against IOL (rate-limit risk) and bypass `TokenStore`'s 3-way concurrency primitive in matriz.
- Module-level singleton replicates exactly the shape of `_get_default()` in v1.1, just lifted into the driver — see `main_iol.py:1556-1672` `main()` for the canonical shape.
- The migrated `main_iol.py` will look like:
  ```python
  def main() -> None:
      if not require_env(_PKG, ["IOL_USER", "IOL_PASSWORD"]):
          return
      client = Client.from_env(max_retries=2)
      with client:
          # all probes receive `client` as positional arg
          probe_login_sync(client)
          probe_get_quote_sync(client, ...)
          ...
  ```
- State leakage between probes is **the same as today** (the shim delegates to one default — cycle_closure depends on this for `_refresh_token` snapshot at `main_iol.py:1643`). No regression.

**(B) Harness module changes** (`verification/`):

Three sites need work; all are mechanical:

1. `verification/mutation_gate.py:55` — reads `matriz_client.client._base_url` via PEP 562 shim. **No change** — the shim stays; this module STILL reads from default. The migrated driver can also pass `client.state.base_url` to a future `mutating_allowed(base_url=...)` overload, but the shim path keeps working.

2. `verification/test_async_configure_resource_warning.py:66-71` — reads `pkg.aio._get_default()._state.http_client`. **No change** — `_get_default()` survives v1.2 (back-compat for external + harness).

3. `verification/test_sync_async_isolation.py:287-312` — reads sync/async default states for matriz. **No change** — semantic preserved.

**The PEP 562 shim does NOT go away in v1.2.** External consumers depend on it. The driver migration eliminates the *driver's* dependency on the shim, but the shim still ships in the package.

**(C) PEP 562 shim removal in `__init__.py`?**

**The shim stays forever.** Documented in `PROJECT.md:45` as a hard constraint: *"v1.2 sigue siendo minor — el top-level `pkg.get_X(...)` API queda 100% backwards-compatible para callers existentes vía el PEP 562 shim de v1.1; solo migran los drivers `main_*.py` internos del repo."*

Two distinct shim sites exist:
1. `pkg/__init__.py` re-exports of top-level names (`get_quote`, `login`, etc.) — **STAY** (external API surface).
2. `pkg/client.py` module-level `__getattr__` for legacy `_token` / `_base_url` reads (e.g., `iol_client/client.py:595-614`) — **STAY** for harness + external test consumers.

**(D) Can any back-compat delegators be removed?**

Audit of `iol_client/client.py:418-566` top-level shims:

| Symbol | File:Line | Used by external consumers? | Used by drivers (v1.1)? | After driver migration |
|--------|-----------|-----------------------------|-------------------------|------------------------|
| `_get_default()` | `client.py:423` | NO (private name) | YES (`main_iol.py:191,265,408,...` — 13+ sites) | **KEEP** — used by harness `test_async_configure_resource_warning.py:66`, `mutation_gate.py:53` (indirectly via shim), `__init__.py:38` re-export |
| `configure()` | `client.py:431` | YES (documented top-level API) | YES (test conftest sites) | **KEEP** |
| `login()` | `client.py:500` | YES (top-level API) | YES (`main_iol.py:193`) | **KEEP** for consumers; driver migrates to `client.login()` |
| `get_quote()` | `client.py:505` | YES (top-level API) | YES (`main_iol.py:267`) | **KEEP** for consumers; driver migrates to `client.get_quote()` |
| `get_historical_quotes()`, `get_instruments()`, `get_instruments_by_type()` | `client.py:515-540` | YES | YES | **KEEP** |
| `_request()` shim | `client.py:543-566` | YES (private but used by `main_iol.py:972`) | YES | **KEEP** for Pitfall 2 envelope-check sites (e.g., `main_iol.py:972`) — driver migration could call `client._request(spec)` instead, eliminating need; but the back-compat shim should remain for external diagnostic use |
| `__getattr__` PEP 562 shim | `client.py:595-614` | YES (harness `mutation_gate.py:55`) | YES (drivers read `_refresh_token`, `_token`) | **KEEP**; driver migration could move all reads to `client._state.X`, but external harness + consumers still need it |

**Net: zero symbols can be deleted from v1.2.** Driver migration is purely a *consumption* change; it doesn't reduce surface area on the library side. The LOC drop comes from the codegen feature, not from removing shims.

---

### 2.2 unasync/codegen Integration

This feature is flagged **spike-before-plan** in `PROJECT.md:34`. The spike picks the tool; my job is to identify the constraints any chosen tool must satisfy.

**Hard constraints any codegen approach must satisfy:**

1. **Identity invariant B8 preserved.** Current at `iol_client/client.py:78` (`_raise_for_response = _core.raise_for_response`) + same line in `aio.py`. The generated `aio.py` MUST emit the same alias assignment so `test_alias_identity` stays green.
2. **Import-linter contracts unchanged.** `_core` cannot import `client`/`aio` (pyproject.toml `[[tool.importlinter.contracts]]` × 4 packages). The codegen tool can read `_core.py` but generated files must not be `_core` itself.
3. **mypy strict must pass on the generated file** — the generated `aio.py` (or `client.py`) is committed and type-checked exactly like hand-written code.
4. **ruff format-stable** — generated file must already match `ruff format` output, or the pre-commit hook will fight regen.
5. **Each generated method's docstring is preserved** (Spanish docstrings have specific endpoint paths that are public-API contract — see `client.py:362-364`).

**Source-of-truth decision (recommended approach for spike to validate):**

**Async-first** is preferred over sync-first or pseudo-source. Reasons:
- Async is the more constrained form (must `await` everywhere); generating sync from async is a *deletion* of `async`/`await` keywords, mechanically safer than the inverse.
- `unasync` library (https://github.com/python-trio/unasync, MIT) implements exactly this: tokenize async file, strip `async def`/`await`/`AsyncClient`, emit sync. Known mature library used by `httpx` itself.
- matriz's `aio.py` is now 852 LOC (Phase 10) — generating `client.py` from it ensures parity going forward.

**Generated file location & lifecycle:**

| Option | Pro | Con | Recommendation |
|--------|-----|-----|----------------|
| A. Generated files git-tracked, regen via `uv run scripts/codegen.py` (spike Plan), regen check in pre-commit hook | Easy to review diffs; mypy/ruff see the same files devs see | Two-step edit (edit `aio.py`, regen, commit both) | **RECOMMENDED** — matches how `httpx` does it internally |
| B. Generated at build time via hatch build hook | Source repo only has `aio.py`; less duplication | mypy/ruff need to regen first — IDE friction; CI complexity | NOT recommended for monorepo with 4 packages |
| C. Single source `_core_template.py` generating both | Cleanest mental model | Heavy investment; harder to debug | Defer to v1.3 if v1.2 unasync proves insufficient |

The spike should validate Option A by demonstrating one package end-to-end (recommend: start with `ambito_financiero_client` — smallest, no auth, no async-specific lifecycle).

**Where does codegen apply?**

- **`client.py` / `aio.py` transport shells** — YES. ~30-50 LOC per endpoint, mostly mechanical await stripping.
- **`_core.py`** — NO. Already single-source; pure functions called by both shells.
- **`_transport.py` vs `_atransport.py`** — borderline. They share the retry policy logic but differ on `httpx.HTTPTransport` vs `httpx.AsyncHTTPTransport` base class. **Recommend out-of-scope for v1.2** — the spike can quantify the LOC overlap and operator can decide.
- **`_token_store.py`** (matriz) — NO. The `threading.Lock + asyncio.to_thread + per-loop asyncio.Lock` pattern is irreducibly bimodal; both surfaces share the same file.
- **`ws_client.py`** (matriz) — NO. Sync-only daemon thread by design.
- **`__init__.py`** — NO. Hand-written PEP 562 + re-exports.

**Import-linter updates needed?**

YES — minor. Add a contract block to exclude the generated file from "did not import from `client.py`" checks if the codegen scaffolding writes a registration step. Recommend adding:
```toml
[[tool.importlinter.contracts]]
name = "<pkg>._core does not depend on transport modules"
type = "forbidden"
source_modules = ["<pkg>._core"]
forbidden_modules = ["<pkg>.client", "<pkg>.aio"]
# No change — but ADD a sentinel test that imports both `client` and `aio`,
# verifies _raise_for_response identity equality, and runs as CI gate.
```

The B8 invariant gets a dedicated regression test (one already exists in `test_alias_identity` per Phase 7 verification) — codegen output must preserve it.

**Driver migration ordering vs codegen:**

The PROJECT.md ordering is: driver migration (Feature 1) → codegen (Feature 2). I agree with this. Reasons:
- Migrating drivers BEFORE codegen surfaces any API gaps (e.g., a probe needs `client.something()` that doesn't exist as a method but only as a top-level function) — fixing in migration phase is local.
- Codegen lands on top of stable, exercised method shells. If codegen-generated method signatures drift from human-written ones, the migrated drivers immediately fail.
- Live re-verification after both lands (Feature 3) — single re-verification cost, two features validated.

---

### 2.3 IOL refresh_token Disk Persistence Integration

This is **IOL-only** (the other 3 packages have no OAuth refresh_token). New module: `iol_client/_token_cache.py`.

**(A) Storage location:**

```python
# iol_client/_token_cache.py — NEW
from pathlib import Path
import os, platformdirs  # add to iol-client/pyproject.toml runtime deps

_APP = "iol-client"
_VENDOR = "market-libs"

def default_cache_path() -> Path:
    # Override hierarchy: env var > user_data_dir
    override = os.getenv("IOL_TOKEN_CACHE_PATH")
    if override:
        return Path(override).expanduser()
    return Path(platformdirs.user_data_dir(_APP, _VENDOR)) / "refresh_token.json"
```

Why `platformdirs` (Apache-2.0, zero-deps, py.typed) over hand-rolled paths:
- macOS: `~/Library/Application Support/market-libs/iol-client/refresh_token.json`
- Linux: `~/.local/share/market-libs/iol-client/refresh_token.json`
- Windows: `%APPDATA%/market-libs/iol-client/refresh_token.json`
- Already-validated pattern; aligns with tenacity-style zero-deps requirements.

Add `platformdirs >= 4.0` to `packages/iol-client/pyproject.toml` runtime deps only (not cross-package).

**(B) Integration with `_ClientState.refresh_token`:**

The disk cache layer is **opt-in via Client kwarg**. Default behavior unchanged (back-compat with all 907 tests):

```python
# iol_client/client.py
class Client:
    def __init__(
        self,
        *,
        ...,  # existing kwargs
        token_cache_path: Path | str | None = None,  # NEW — None = no disk cache
    ) -> None:
        ...
        self._token_cache: TokenCache | None = (
            TokenCache(Path(token_cache_path)) if token_cache_path is not None else None
        )
        # Lazy disk read on first auth attempt — NOT in __init__
        # (so a bad cache file doesn't crash Client construction)
```

In `_refresh()` (`client.py:264`) and `login()` (`client.py:251`):
```python
def login(self) -> str:
    spec = _core.build_login_request(self._state)
    resp = self._send_auth_request(spec)
    token, expires_at, refresh = _core.parse_login_response(resp)
    self._state.token = token
    self._state.token_expires_at = expires_at
    if refresh is not None:
        self._state.refresh_token = refresh
        if self._token_cache is not None:
            self._token_cache.write(refresh)  # NEW — best-effort write-on-rotate
    return token
```

In `_ensure_token()` (`client.py:277`):
```python
def _ensure_token(self) -> None:
    if _core.token_is_fresh(self._state):
        return
    # NEW — lazy disk read if memory cache empty
    if self._state.refresh_token is None and self._token_cache is not None:
        self._state.refresh_token = self._token_cache.read()  # may return None
    if self._state.refresh_token:
        try:
            self._refresh()
        except IOLAuthError:
            # NEW — invalidate disk cache on refresh failure (corrupt/revoked token)
            if self._token_cache is not None:
                self._token_cache.invalidate()
        else:
            return
    self.login()
```

**(C) Concurrency — multi-instance / multi-process:**

| Scenario | Solution |
|----------|----------|
| Same process, multiple `Client()` instances pointed at the same path | Each instance reads at first auth, writes on rotate. Last-write-wins. Acceptable per IOL semantics — rotation is rare; concurrent refresh is rare. |
| Multi-process (e.g., gunicorn workers) | **File locking via `fcntl.flock` (POSIX) + `msvcrt.locking` (Windows)** — wrap read/write in atomic exclusive lock. Use `filelock>=3.0` (zero-deps, py.typed, Unlicense) instead of hand-rolling. Add to runtime deps of iol-client only. |
| Sync `Client` + async `AsyncClient` in same process | Each has its own `_token_cache`. Disk file is the shared synchronization point — sync writes are seen by async on next read. |

**(D) Failure modes:**

| Failure | Behavior | Rationale |
|---------|----------|-----------|
| Missing file (first run) | `TokenCache.read()` returns `None` → fall through to `self.login()` (password grant) | Initial bootstrap |
| Corrupt file (invalid JSON, wrong schema) | Log WARNING via `_logging.py`, treat as missing, `read()` returns `None` | Tolerant — disk cache is opportunistic |
| Permission error on read | `read()` returns `None`, log WARNING with actionable message ("Cannot read X; check umask") | Don't crash auth; degrade gracefully |
| Permission error on write | Log WARNING, swallow exception (auth still succeeded) | Cache is best-effort, not critical path |
| Disk full | Log WARNING, swallow | Same — best-effort |

**No hard exceptions from the cache layer** — IOL auth must always succeed via password grant fallback.

**(E) Interaction with `_refresh_policy.py`?**

The `_refresh_policy.py` is **matriz-only**. IOL does not have an analogous policy module. The interaction question doesn't apply directly to IOL — IOL's refresh policy is just "try refresh, on AuthError fall through to password" (`client.py:280-289`).

If v1.3 generalizes refresh policy to IOL (DOS-prevention parity with matriz), the disk-cache write should reset the fail-cache TTL on successful read-from-disk — but this is a v1.3 concern. For v1.2: keep the policies independent.

---

### 2.4 `Client.from_env()` Integration

**(A) Env var names — per-package or shared prefix?**

Decision: **per-package, existing names** (no SDK envelope). Rationale:
- iol-client already documents `IOL_USER`, `IOL_PASSWORD`, `IOL_BASE_URL` (`PROJECT.md:90-92`, `_state.py:61-71`).
- higyrus uses `HIGYRUS_*`, matriz uses `PRIMARY_*`, ambito has none (no auth).
- Introducing `MARKETLIBS_*` would break the no-shared-internals constraint (`PROJECT.md:137`) — and would surprise consumers who already use existing names.
- The README at `packages/higyrus-client/README.md:32` documents `HigyrusClient.from_env()` as the existing pattern — consistent.

Per-package env-var contract:

| Package | Required | Optional | Notes |
|---------|----------|----------|-------|
| iol-client | `IOL_USER`, `IOL_PASSWORD` | `IOL_BASE_URL`, `IOL_TOKEN_CACHE_PATH` (new v1.2) | Existing names preserved |
| higyrus-client | `HIGYRUS_USER`, `HIGYRUS_PASSWORD` | `HIGYRUS_BASE_URL` | Existing |
| matriz-client | `PRIMARY_USER`, `PRIMARY_PASSWORD` | `PRIMARY_BASE_URL` | Existing |
| ambito-financiero-client | (none required — no auth) | `AMBITO_BASE_URL` | `from_env()` still useful for base_url override |

**(B) `load_dotenv()` behavior:**

Decision: **call `load_dotenv()` inside `from_env()` itself**, idempotent. Reasoning:
- Existing packages already call `load_dotenv()` at module import (`iol_client/client.py:68`, etc.). The `from_env()` call would inherit those values for free.
- But test scenarios that set env vars AFTER import (the `_state.py:62-63` factory pattern) must still work — `from_env()` should re-call `load_dotenv()` (which is no-op when `.env` already loaded) to defensively pick up late-set vars.
- python-dotenv's `load_dotenv()` is idempotent and cheap (~ms); no harm calling it.

**(C) Interaction with `__init__()` and `configure()`:**

```python
class Client:
    @classmethod
    def from_env(
        cls,
        *,
        base_url: str | None = None,
        max_retries: int | None = None,
        http_client: httpx.Client | None = None,
        token_cache_path: Path | str | None = None,
    ) -> Self:
        """Construct a Client reading credentials from environment vars.

        Required env vars: IOL_USER, IOL_PASSWORD.
        Optional: IOL_BASE_URL (default https://api.invertironline.com),
                  IOL_TOKEN_CACHE_PATH.

        Explicit kwargs override env vars.
        """
        load_dotenv()  # idempotent; re-reads .env in case of late init
        username = os.getenv("IOL_USER")
        password = os.getenv("IOL_PASSWORD")
        if not username or not password:
            raise IOLAuthError(
                "from_env() requires IOL_USER and IOL_PASSWORD in environment"
            )
        return cls(
            username=username,
            password=password,
            base_url=base_url or os.getenv("IOL_BASE_URL"),
            max_retries=max_retries if max_retries is not None else 2,
            http_client=http_client,
            token_cache_path=(
                token_cache_path
                or os.getenv("IOL_TOKEN_CACHE_PATH")
                or None
            ),
        )
```

**Precedence (lowest → highest):**

1. `_ClientState` `default_factory=_env_user` (existing — runs at `_ClientState()` construction)
2. `Client.from_env(base_url=...)` explicit kwargs (override env)
3. `Client(__init__)` direct construction (override env)
4. `configure(token=..., http_client=...)` runtime mutation
5. `client.with_options(max_retries=N)` per-call override (highest, scoped)

`from_env()` is a thin convenience over `__init__`. It does NOT call `configure()` — it constructs a fresh Client with overrides resolved at call time. Importantly: `from_env()` should **fail loud** if required env vars are missing (raises `IOLAuthError`), whereas plain `__init__()` is lazy (lets `_state.username=""` propagate to first login).

This distinguishes the two:
- `Client()` — lazy, env-friendly default, lets you swap creds later via `configure()`.
- `Client.from_env()` — eager, explicit, validates required env vars at construction.

**(D) Per-package serial roll-out:**

Order: **ambito → matriz → higyrus → iol** (reversed v1.1 order). Reasoning:
- ambito has no auth — simplest baseline, shakes out the API shape.
- matriz uses `TokenStore` — `from_env()` must wire the store on construction. Validates the pattern.
- higyrus is the templates target — README example already documents `HigyrusClient.from_env()` (so it's the most "expected" surface).
- iol last — interacts with the disk-cache feature (`IOL_TOKEN_CACHE_PATH`). Land disk cache first, then `from_env()` adds the env-var convenience layer.

---

### 2.5 `with_options()` Integration

**(A) Returns new wrapped Client vs mutate-and-restore:**

Decision: **return a new wrapper object that shares `_state` and `httpx.Client` but overrides `max_retries`**, à la anthropic/openai SDKs.

```python
class Client:
    def with_options(self, *, max_retries: int) -> Client:
        """Return a new Client view with overridden options.

        The returned client shares this client's _state and underlying
        httpx.Client (no re-auth needed). Only call-time options differ.

        Use for one-off requests that need different retry behavior::

            quote = client.with_options(max_retries=5).get_quote("RARE")
        """
        _validate_max_retries(max_retries)
        view = Client.__new__(Client)  # bypass __init__
        view._state = self._state       # SHARE — not a copy
        view._max_retries = max_retries  # OVERRIDE
        return view
```

Why this design:
- **No re-auth** — shared `_state` means the token, refresh_token, base_url stay (matches anthropic/openai behavior).
- **No connection pool fragmentation** — shared `httpx.Client` (lives in `_state.http_client`) means TCP pool stays warm.
- **Immutable composition** — `client.with_options(max_retries=5).with_options(max_retries=10)` chains predictably; the original `client` is untouched.
- **Type-safe** — returns `Client` (or `AsyncClient`), so all methods still resolve.
- **No `__exit__`/`close()` from the view** — the view shares state; closing it would close the parent's httpx client. Mitigation: override `__enter__`/`__exit__` on the view to be no-ops, or document "do not call close() on a with_options view."

**Risk — view close():** The current `close()` (`client.py:169-175`) sets `self._state.http_client = None`. If a view calls `close()`, it nukes the parent's httpx.Client. Mitigation: track `_is_view: bool` on the instance; `close()` is no-op if `_is_view = True`.

```python
def close(self) -> None:
    if getattr(self, "_is_view", False):
        return  # views don't own the http_client
    http_client = self._state.http_client
    ...
```

**(B) Anthropic comparison:**

The anthropic-sdk-python pattern (`Anthropic().with_options(max_retries=5)`) returns a *new client* sharing the same auth and httpx state. Our pattern matches.

Other options to allow override (deferred to v1.3 if needed):
- `with_options(timeout=...)` — per-call timeout
- `with_options(http_client=...)` — temporary httpx swap
- `with_options(headers={...})` — extra default headers

For v1.2: **only `max_retries`** per `PROJECT.md:40`. Scope-locked.

---

### 2.6 Build Order / Suggested Phase Decomposition

**Dependency DAG:**

```
                  [Phase 0: Spike — unasync/codegen approach selection]
                   - Pick tool: unasync vs custom Jinja2 vs LibCST transform
                   - Validate on ambito (smallest)
                   - Define source-of-truth direction (async-first recommended)
                   - Capture findings: identity B8 preservation; ruff format stability;
                     mypy strict pass on generated file
                   (spike-before-plan flag activates here per PROJECT.md:34)
                              │
                              ▼
                  [Phase 1: Cross-package ergonomics — from_env() + with_options()]
                   - 4 packages serial: ambito → matriz → higyrus → iol
                   - Per package: add Client.from_env() + with_options() to BOTH
                     client.py + aio.py; 4×2 = 8 hand-written class-method pairs
                   - Mocked tests (4 packages × 2 surfaces × ~4 tests)
                   - Why first: drivers + disk-cache will consume these
                              │
                              ▼
              ┌───────────────┴───────────────┐
              ▼                               ▼
[Phase 2a: IOL disk persistence]   [Phase 2b: Driver migration × 4]
 - iol-client only                  - 4 drivers serial:
 - _token_cache.py (new)              ambito → iol → higyrus → matriz
 - Client.__init__ kwarg              (per PROJECT.md:33; smallest to largest)
 - load on _ensure_token              - Each driver instantiates a Client at top of
 - write on login/_refresh              main(), passes to probes as positional arg
 - filelock + platformdirs           - INT-01 sites collapse to client._state.X reads
   to iol-client deps                - PEP 562 driver-side reads (e.g.
 - 8+ regression tests:                iol_client.client._refresh_token at
   first-run, rotate, corrupt,         main_iol.py:1271) migrate to
   permission-error, multi-           client._state.refresh_token
   process file-locking,             - Drivers gain from_env() for setup
   sync+async share-disk path        - LIVE-01-equivalent re-verification at end
 - independent of Phase 2b             of phase per driver
              └───────────────┬───────────────┘
                              ▼
                  [Phase 3: unasync codegen — single-source sync/async dedup]
                   - Per package: 4 serial (same order as v1.1)
                   - Generated client.py (or aio.py) replaces hand-written one
                   - Regen script in scripts/codegen.py
                   - Pre-commit hook verifies regen-clean (re-run = git-clean)
                   - Import-linter contracts unchanged
                   - B8 identity invariant test must remain green
                   - mypy strict pass on generated file
                              │
                              ▼
                  [Phase 4: Final live re-verification × 4 packages]
                   - LIVE-01 mirror — operator dispositions: no_new_findings
                   - All 4 drivers re-run with the migrated + codegen-generated shape
                   - In-cycle bugs surfaced get CONFIRMED/FIXED/EXPECTED/NO-FIX
                     classification + mocked regression test
                   - Milestone audit
```

**Why this order:**

1. **Phase 0 (spike) first** — `PROJECT.md:34` explicitly flags spike-before-plan. The codegen approach is the single architectural unknown. Auto-load findings into `Skill("spike-findings-market-libs")` to feed Phase 3.

2. **Phase 1 (ergonomics) before Phase 2b (driver migration)** — `from_env()` simplifies the driver migration significantly. `main_iol.py:1556-1560` currently calls `require_env(...)` then implicitly relies on env-var defaults at `_get_default()` construction time; the migrated driver becomes `client = Client.from_env(max_retries=2)` — explicit, validated, idiomatic.

3. **Phase 2a (IOL disk cache) parallelizable with Phase 2b** — they touch different files. Disk cache is IOL-only (`iol_client/_token_cache.py` is new); driver migration touches `main_*.py` (none of which interact with cache wiring). Operator can run them as parallel waves OR Phase 2a first if iol driver wants to exercise the disk cache during migration.

4. **Phase 3 (codegen) AFTER driver migration** — three reasons:
   - Migrated drivers exercise the public method surface end-to-end, surfacing any subtle API gap (e.g., a probe needs a method that doesn't exist as `client.X()` but only as `pkg.X()` top-level). Catching this in Phase 2b's per-package migration is local; catching it after codegen would be cross-phase debug.
   - Driver migration is a *consumption* change with predictable diff. Codegen is a *production* change with broad impact. Doing consumption first keeps risk staircased.
   - If codegen lands first, the drivers would need to migrate against a moving target — both refactors at once invite confusion.

5. **Phase 4 (LIVE-01 re-verification) last** — single re-verification cost validates all of Cluster 1 + Cluster 2 features simultaneously. Per `PROJECT.md:35` and v1.1 LIVE-01 precedent.

**Parallelization opportunities:**

- Phase 1 packages serial (per `PROJECT.md:39` "Per-package serial") — but within each package, sync + async can be parallel sub-tasks since they share `_core` builders.
- Phase 2a and Phase 2b are independent — can be concurrent waves.
- Phase 3 packages serial within phase (each package gets one codegen wave) — but the 4 codegen waves can be parallelized once Phase 3 first package validates the approach.

**Estimated phase count: 5** (Spike + 3 work phases + LIVE final gate). Matches v1.1's "6 phases" cadence within a tighter scope.

---

## 3. New Modules Per Package (Delta vs v1.1)

| New / Modified File | Package | Purpose | Imports From | Imported By |
|---------------------|---------|---------|--------------|-------------|
| `_token_cache.py` (NEW) | iol-client | Disk-persisted refresh_token, file-locked, opt-in | `pathlib`, `platformdirs`, `filelock`, stdlib `json` | `client.py`, `aio.py` |
| `Client.from_env()` classmethod (MODIFY) | All 4 | Eager env-var constructor; raises on missing required | `os`, `dotenv`, `_state` | Drivers, external consumers |
| `Client.with_options()` method (MODIFY) | All 4 | Return Client view sharing state, overriding max_retries | (none) | Drivers, external consumers |
| `Client._is_view` field (MODIFY) | All 4 | Flag to suppress `close()` on views | (none) | `close()`, `__exit__()` |
| `client.py` / `aio.py` (REPLACE) | All 4 | Generated single-source (codegen output) | `_core`, `_state`, `_transport` | `__init__.py`, drivers |
| `scripts/codegen.py` (NEW) | Repo root | Regen tool + pre-commit check | `unasync` (or chosen tool) | Pre-commit hook, devs |
| Pre-commit hook entry (MODIFY) | `.pre-commit-config.yaml` | Run `scripts/codegen.py --check` | (none) | CI gate |

**Cross-package status:** `from_env()` + `with_options()` + view-flag logic is duplicated 4× per the no-shared-internals constraint. The codegen tool reads each package's source files independently — no cross-package coupling introduced.

---

## 4. Data Flow Changes

### 4.1 Driver Migration Flow

**Before (v1.1):**
```
main() → pkg.fn(...) → PEP 562 shim → _get_default() → Client.fn(self, ...)
                                          ↓
                                      _ClientState (module-private singleton)
```

**After (v1.2):**
```
main() → client = Client.from_env(...)
         client.fn(...) → Client.fn(self, ...) → self._state (per-driver instance)
                                                       ↓
                                                  httpx + _core builders
```

Module-level `_get_default()` still exists but **the driver doesn't touch it** — its calls bypass the PEP 562 shim entirely. External consumers continue to go through the shim.

### 4.2 IOL Disk Cache Flow

**Login (first run, no disk cache file):**
```
Client.login() → _send_auth_request → _core.parse_login_response
              → self._state.refresh_token = new_refresh
              → self._token_cache.write(new_refresh)  # NEW
              → returns access_token
```

**Construction with disk cache, subsequent process startup:**
```
Client.from_env(token_cache_path=Path("~/.cache/iol")) → __init__()
   - self._state.refresh_token = None  # in-memory empty
   - self._token_cache = TokenCache(...)  # ready, NOT read
client.get_quote("GGAL") → _ensure_token()
   - state.refresh_token is None AND token_cache is not None
   - state.refresh_token = token_cache.read()  # disk read
   - if state.refresh_token: try self._refresh()
   - if _refresh raises IOLAuthError: token_cache.invalidate(); fallback self.login()
```

**Multi-process refresh (gunicorn workers):**
```
Worker A: _refresh() acquires filelock → reads disk → POST /token → writes new disk
Worker B: _refresh() waits on filelock → reads NEW disk → skip _refresh (token fresh)
```

### 4.3 `with_options()` Per-Call Flow

```
client = Client.from_env(max_retries=2)
view = client.with_options(max_retries=5)
   - view._state is client._state  # SAME object
   - view._max_retries = 5         # OVERRIDE
   - view._is_view = True          # close()-suppressed
view.get_instruments("argentina") → uses view._max_retries → wraps RetryTransport(max_attempts=6)
   # but!!! the underlying httpx.Client (in _state.http_client) was built with
   # client._max_retries=2 → max_attempts=3. The override doesn't propagate to
   # the cached httpx.Client.
```

**Critical integration point:** `_ensure_http_client()` at `client.py:207` caches the httpx.Client lazily with `transport=RetryTransport(max_attempts=self._max_retries + 1)` baked into the Transport. The current design caches the transport with the Client's `_max_retries`. `with_options(max_retries=5)` would NOT take effect because the cached transport already has `max_attempts=3`.

**Two options to fix:**

(a) `with_options` lazily builds a per-view `httpx.Client` with the overridden transport. Loses connection-pool sharing. Acceptable for rare overrides.

(b) Refactor `_transport.RetryTransport` to read `max_attempts` from `request.extensions["max_attempts"]` (similar to the `idempotent` flag — already a documented pattern from v1.1 Phase 8 `_core` ↔ `_transport` decoupling). The Client method shells set `req.extensions["max_attempts"] = self._max_retries + 1` before dispatch; transport reads it per-request, falls back to its constructor default if unset.

**Recommendation: (b) — extension-based override.** Matches v1.1 pattern. Allows view to share connection pool. Minimal code change. ~15 LOC in `_transport.py` + `_atransport.py` × 4 packages.

This integration point requires explicit attention in Phase 1's plan — `_transport.py` `handle_request` needs to read the new extension.

---

## 5. Key Abstractions (v1.2 Delta)

### `TokenCache` (iol-client only)

**Purpose:** Per-process best-effort disk persistence of OAuth refresh_token. Survives process restarts; avoids password grant on every cold start.

**Interface:**
```python
class TokenCache:
    def __init__(self, path: Path) -> None: ...
    def read(self) -> str | None: ...        # returns None on missing/corrupt/permission-error
    def write(self, refresh_token: str) -> None: ...  # best-effort; swallow errors with WARNING log
    def invalidate(self) -> None: ...        # delete file (called on revoked refresh)
```

**Concurrency:** `filelock.FileLock` wraps read/write. Lock file lives at `{path}.lock`.

### `Client.from_env()` classmethod

**Purpose:** Eager env-var-driven Client construction with validation. Replaces the ad-hoc `require_env(...)` + `Client()` dance in drivers.

**Per-package env-var contract:** see §2.4(A).

### `Client.with_options()` method

**Purpose:** Per-call retry-policy override sharing the same auth state and connection pool.

**Implementation:** view pattern with shared `_state` + overridden `_max_retries` + `_is_view = True`.

---

## 6. Architectural Constraints (v1.2)

| Constraint | Source | v1.2 enforcement |
|------------|--------|-------------------|
| No shared internals between packages | `PROJECT.md:137` | `from_env`, `with_options`, `_token_cache` duplicated 4× / IOL-only. Codegen runs per-package. |
| Top-level `pkg.get_X(...)` API 100% preserved | `PROJECT.md:45` | PEP 562 shim + back-compat delegators ALL stay. No deletions. |
| Identity invariant B8 (`aio._raise_for_response is client._raise_for_response is _core.raise_for_response`) | Phase 7 v1.1 | Codegen output MUST emit the alias `= _core.raise_for_response` literally. Regression test stays green. |
| Import-linter contracts (`_core` ↔ transport modules) | `pyproject.toml:127-150` | Unchanged. Generated `client.py`/`aio.py` still cannot be imported by `_core.py`. |
| matriz TokenStore 3-way concurrency primitive | `_token_store.py:46`, Phase 10 | UNCHANGED. `from_env()` + `with_options()` build instances that wire `_state.token_store = build_token_store(state, max_retries=N)`. |
| matriz ws_client.py daemon thread shared sync REST token | Phase 10 | UNCHANGED. Codegen does NOT touch ws_client.py. |
| Driver INT-01 idiom (`_get_default()._state.X`) | Quick task 260613-nwb, Phase 11 LIVE-01 F-02 | After driver migration, drivers no longer use `_get_default()`. INT-01 idiom remains documented as the pattern for ANY code that wants to read the singleton state (external consumers, harness). Drivers use `client._state.X` directly. |
| Per-package serial migration | v1.0/v1.1 precedent, `PROJECT.md:39` | Each phase walks 4 packages serially. Lessons compound iol → higyrus → matriz. |

---

## 7. Anti-Patterns to Avoid

### 7.1 Re-instantiating Client per probe

```python
# BAD — N OAuth handshakes, N httpx.Client instances, no shared retry state
for symbol in symbols:
    client = Client.from_env()
    quotes.append(client.get_quote(symbol))
```

Correct: one Client per driver, passed to each probe as positional arg. Mirrors v1.1 `_get_default()` semantics.

### 7.2 `with_options(...)` then `close()`

```python
client = Client.from_env()
view = client.with_options(max_retries=5)
view.close()  # would close the SHARED httpx.Client → next client.get_X() crashes
```

Mitigation: view's `close()` is no-op (via `_is_view` flag). Document explicitly in `with_options()` docstring.

### 7.3 Codegen circular regen

```python
# BAD — generated aio.py imports from client.py (which is also generated)
from iol_client.client import Client  # would create circular generation dependency
```

Codegen MUST emit each shell independently consuming only `_core`, `_state`, `_transport`/`_atransport`, `_logging`. No cross-shell imports (matches v1.1 Phase 7 invariant).

### 7.4 Disk-cache write inside RetryTransport

The cache write site is `Client.login()` / `Client._refresh()` — the high-level shell. NOT inside `_transport.RetryTransport.handle_request` which sees raw `httpx.Request` objects and has no awareness of auth flow semantics.

### 7.5 `from_env()` lazy in `__init__()`

The temptation: make `__init__()` always call `load_dotenv()` and read env vars. Already the case via `_state.py:62-71` factories. BUT `from_env()` adds VALIDATION (required vars must be present). Do not let `__init__` adopt this validation — would break `Client()` (zero-arg) tests that legitimately leave creds blank for monkeypatch-then-set.

---

## 8. Integration Point File:Line Citations

### Driver migration sites (must rewrite):

| Driver | Lines | Symbol | After migration |
|--------|-------|--------|-----------------|
| `main_iol.py:191,265,408,559,695,1270,1415` | `iol_client.client._get_default()._state.base_url` | `client._state.base_url` |
| `main_iol.py:226,343,487,620,805` | `aio._get_default()._state.base_url` | `async_client._state.base_url` |
| `main_iol.py:211,246,1271,1327,1328,1329,1503,1643` | `iol_client.client._refresh_token / _token / _token_expires_at` | `client._state.refresh_token / token / token_expires_at` |
| `main_iol.py:1294` | INT-01 idiom write `_get_default()._state.token_expires_at = 0.0` | `client._state.token_expires_at = 0.0` |
| `main_iol.py:972` | `iol_client.client._request("GET", ...)` (envelope check Pitfall 2) | `client._request(RequestSpec(method="GET", path=...))` |
| `main_iol.py:1425,1426,1427,1503` | `iol_client.client._password = ...` etc. (probe_auth_401 CR-03 mutation) | `client._state.password = ...` |
| Equivalent sites in `main_higyrus.py`, `main_matriz.py`, `main_ambito_financiero.py` | ~50-100 sites total per driver | Same idiom mapping |

### Library symbols that stay (back-compat surface):

| File:Line | Symbol | Why it must stay |
|-----------|--------|------------------|
| `packages/iol-client/src/iol_client/client.py:423` | `_get_default()` | External harness (`mutation_gate.py:55` via shim), `__init__.py:38` re-export |
| `packages/iol-client/src/iol_client/client.py:431` | top-level `configure(...)` | Documented public API; external test conftest pattern |
| `packages/iol-client/src/iol_client/client.py:500-540` | `login`, `get_quote`, etc. top-level shims | Documented public API per `PROJECT.md:45` |
| `packages/iol-client/src/iol_client/client.py:543-566` | `_request(...)` top-level shim | Used by external probes for envelope-key checks |
| `packages/iol-client/src/iol_client/client.py:595-614` | PEP 562 `__getattr__` | Harness + external consumer reads of `_token`, `_refresh_token`, `_client` |
| `packages/matriz-client/src/matriz_client/client.py:790-805` | PEP 562 + `_FORWARDED_TO_STATE` (NOTE: matriz DOES forward `_base_url` — different from iol) | `verification/mutation_gate.py:55` reads `matriz_client.client._base_url` |
| `packages/iol-client/src/iol_client/_state.py:74-92` | `_ClientState` dataclass | Codegen target consumer; disk-cache integration site |

### Codegen guard sites:

| File:Line | Invariant | Test |
|-----------|-----------|------|
| `packages/iol-client/src/iol_client/client.py:78` | `_raise_for_response = _core.raise_for_response` | Existing identity test (B8) — generated `aio.py` must include same |
| `pyproject.toml:127-150` | Four import-linter contracts | Codegen must not regress |
| `packages/iol-client/src/iol_client/__init__.py:27-30` | LOG-01 NullHandler attach pattern | Codegen does NOT touch `__init__.py` (manual file) |

---

## 9. Open Architectural Questions (Phase Flags)

1. **Codegen tool choice** — `unasync` vs custom Jinja2 vs LibCST. **Phase 0 spike resolves.**
2. **`with_options(timeout=...)`, `with_options(headers=...)`** — defer to v1.3 per scope lock (`PROJECT.md:40` only `max_retries`).
3. **IOL disk cache cross-process with concurrent refresh** — `filelock` pattern is sufficient per most-recent platformdirs usage at PyPI scale, but multi-worker production loads should be flagged as PITFALL (the worker fleet might thunder on refresh).
4. **`Client.from_env(**overrides)` accepting arbitrary kwargs vs explicit allowlist** — recommend explicit allowlist (only the kwargs `from_env()` will pass through to `__init__`). Open kwargs invite confusion about which take env precedence.
5. **Matriz `from_env()` must wire `TokenStore`** — `_state.token_store = build_token_store(state, max_retries=max_retries)` after construction. Document in Phase 1 plan.
6. **Driver smoke after Phase 2b but before Phase 3 codegen** — recommend running each driver `--live` once after migration as a per-phase exit gate (not as a milestone-final gate). Detects API gaps before codegen masks them.

---

## RESEARCH COMPLETE

**Project:** market-libs v1.2 Architecture + Auth/Ergonomics Carry-forwards
**Mode:** Project research — architecture integration
**Confidence:** HIGH (built on validated v1.1 architecture; 907 tests + LIVE-01 PASS × 4)

### Key Findings

- **PEP 562 shim + top-level delegators STAY FOREVER.** Driver migration eliminates the driver-side dependency on the shim but does not enable removal of any library-side symbols. Zero LOC reduction comes from removing back-compat; all v1.2 LOC drop comes from codegen.
- **Codegen target = transport shells only.** `client.py`/`aio.py` are generated single-source (async-first via unasync recommended); `_core.py`, `_state.py`, `_transport.py`/`_atransport.py`, `_token_store.py`, `ws_client.py`, `__init__.py` stay hand-written. Identity invariant B8 + import-linter contracts must be preserved by the codegen tool. Phase 0 spike-before-plan flag is active.
- **`with_options(max_retries=N)` requires `_transport.RetryTransport` refactor** — the cached `httpx.Client` has `max_attempts` baked into its Transport at construction time, so the view pattern needs to thread `max_attempts` through `request.extensions` (mirror of v1.1 Phase 8 `idempotent` extension pattern). This is a small but non-obvious integration cost.
- **IOL disk persistence integrates cleanly via opt-in kwarg.** `Client(token_cache_path=...)` lazy-reads on first `_ensure_token`, writes on `login`/`_refresh` rotation, file-locks via `filelock`, uses `platformdirs` for default paths. Failure modes degrade gracefully (cache is best-effort). IOL-only — no matriz/higyrus/ambito impact.
- **Suggested phase order: Spike (0) → Cross-package ergonomics from_env+with_options (1) → IOL disk persistence + Driver migration in parallel (2a/2b) → Codegen single-source (3) → LIVE-01-final gate (4).** Five phases total. Drivers consume Phase 1 features; codegen runs AFTER driver migration validates the public method surface.

### Files Cited (not created — findings returned directly per system reminder)

- `/Users/sebadlf/development/becerra/market-libs/.planning/PROJECT.md` (lines 26-45, 90-105, 119-132, 137-141)
- `/Users/sebadlf/development/becerra/market-libs/.planning/RETROSPECTIVE.md` (lines 12-47)
- `/Users/sebadlf/development/becerra/market-libs/.planning/research/v1.0-v1.1-archived/ARCHITECTURE.md` (prior v1.1 architecture, sections 1-13)
- `/Users/sebadlf/development/becerra/market-libs/packages/iol-client/src/iol_client/client.py` (lines 78, 169-175, 207-225, 251-275, 277-289, 291-349, 420-566, 577-614)
- `/Users/sebadlf/development/becerra/market-libs/packages/iol-client/src/iol_client/_state.py` (lines 60-92)
- `/Users/sebadlf/development/becerra/market-libs/packages/iol-client/src/iol_client/__init__.py` (lines 27-30, 32-68)
- `/Users/sebadlf/development/becerra/market-libs/packages/matriz-client/src/matriz_client/_token_store.py` (lines 46-143)
- `/Users/sebadlf/development/becerra/market-libs/packages/matriz-client/src/matriz_client/client.py:790-805` (PEP 562 shim — note `_base_url` IS forwarded in matriz, unlike iol)
- `/Users/sebadlf/development/becerra/market-libs/packages/matriz-client/src/matriz_client/_state.py` (TokenStore wiring field)
- `/Users/sebadlf/development/becerra/market-libs/main_iol.py` (driver migration target — 1675 LOC, ~13 INT-01 sites + 8 _refresh_token reads)
- `/Users/sebadlf/development/becerra/market-libs/verification/mutation_gate.py:55` (harness reads matriz `_base_url` via shim — STAYS as-is)
- `/Users/sebadlf/development/becerra/market-libs/verification/test_async_configure_resource_warning.py:66-71` (harness reads `pkg.aio._get_default()._state.http_client` — STAYS)
- `/Users/sebadlf/development/becerra/market-libs/verification/test_sync_async_isolation.py:287-312` (harness reads sync/async default states — STAYS)
- `/Users/sebadlf/development/becerra/market-libs/pyproject.toml:127-150` (4 import-linter contracts — codegen must not regress)
- `/Users/sebadlf/development/becerra/market-libs/packages/higyrus-client/README.md:32` (existing `HigyrusClient.from_env()` example documents the expected ergonomic shape)

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Driver migration (Q1) | HIGH | All citations exact; INT-01 idiom validated in v1.1 quick-task 260613-nwb + Phase 11 F-02 fix |
| Codegen integration (Q2) | MEDIUM | Spike-before-plan flag active; tool choice TBD. Invariants (B8, import-linter) firmly known. |
| IOL disk persistence (Q3) | HIGH | Pattern is well-established (filelock + platformdirs); failure modes mapped; back-compat clear |
| `from_env()` (Q4) | HIGH | Env var names already exist per package; precedence stack clear; README already documents the higyrus example |
| `with_options()` (Q5) | MEDIUM | View pattern is well-known (anthropic/openai); the `_transport` integration cost is a real architectural decision requiring Phase 1 plan attention |
| Build order (Q6) | HIGH | Dependencies are clean; matches v1.1 spike-before-plan + per-package serial precedent |

### Roadmap Implications

- 5 phases total: Spike + 3 work phases (ergonomics → disk+migration parallel → codegen) + LIVE final gate.
- Per `PROJECT.md:39` constraint, packages run serial within each phase (ambito → matriz → higyrus → iol for ergonomics; ambito → iol → higyrus → matriz for driver migration per `PROJECT.md:33`).
- LIVE-01-equivalent gate at milestone close re-uses the v1.1 pattern: re-run `main_*.py × 4` against live APIs, classify any new findings, milestone audit.
- Operator override block in VERIFICATION.md frontmatter remains the deviation-tracking pattern (per v1.1 Patterns Established).

### Open Questions

- Codegen tool choice (Phase 0 spike).
- Whether `with_options(timeout=...)` should land in v1.2 or be deferred to v1.3 — recommend deferring per scope lock at `PROJECT.md:40`.
- IOL disk cache multi-worker thunder-on-refresh — flag for PITFALLS.md as a moderate pitfall warranting mocked regression test for the `filelock` contention path.
