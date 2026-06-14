# Phase 6: Compat Safety Net + Client Class Skeleton — Research

**Researched:** 2026-06-10
**Domain:** Python HTTP-client architectural refactor (4 packages, module-singleton → per-instance `Client`/`AsyncClient`)
**Confidence:** HIGH

## Summary

Phase 6 lands two atomic blocks of work that together form the v1.1 foundation:

1. **REFAC-01 — Compat safety net:** A snapshot test (`verification/test_public_surface.py`) that enumerates every public symbol and signature across the 4 packages (iol/higyrus/matriz/ambito) plus 8 "fixture-reaches-production" guard tests (1 sync + 1 async per package) that monkeypatch a sentinel token and assert it lands in the outgoing wire request. The net must be green BEFORE any package refactor begins (Pitfall #1 mitigation).

2. **REFAC-02 — Client/AsyncClient class skeleton:** For each of the 4 packages, introduce `_state.py` with an `@dataclass(slots=True) _ClientState` and `Client`/`AsyncClient` classes that own this state. The pre-existing top-level module functions (`pkg.get_X`, `pkg.configure`, `pkg.login`) continue to work transparently via a lazy `_default_client` singleton + PEP 562 `__getattr__` shim that forwards the small set of token-related legacy globals (`_token`, `_token_ts`/`_token_expires_at`, `_refresh_token`, `_token_lock`, `_client`) to the default instance. Tests' `monkeypatch.setattr(pkg.client, "_token", ...)` semantics are preserved via conftest migration to `pkg.configure(token=..., token_expires_at=...)`.

**Primary recommendation:** Process strictly in the order locked by CONTEXT.md (ámbito → iol → higyrus → matriz), one atomic commit per package that ships `_state.py` + `Client` + `AsyncClient` + PEP 562 shim + conftest migration + deletion of module-level globals. The snapshot test and 8 guard tests ship FIRST in a tests-only plan so the safety net is in place before the first refactor lands. Use `@dataclass(slots=True)` for `_ClientState`, never override `Client.__init__` with `frozen=True`, and keep redaction logic inline in each package's `client.py` (no import from `verification/`).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Shim de compatibilidad (PEP 562)**

- **D-01:** Solo `__getattr__` read-only a nivel de módulo (`client.py` y `aio.py` de cada paquete). **NO** `ModuleType` subclass con `__setattr__`. Pitfall #1 se cierra vía migración de conftest, no vía mecanismo bidireccional.
- **D-02:** Atributos forwarded por el shim: **solo token-related** — `_token`, `_token_ts` (iol), `_token_expires_at`, `_token_lock` (aio). El resto de globals legacy (`_user`, `_password`, `_base_url`, `_client`) se eliminan; cualquier lectura post-refactor recibe `AttributeError`. Excepción: `_client` SÍ se forwarda (resuelve a `_default()._state.http_client`) para preservar el patrón de `main_higyrus.py` que muta `_client.event_hooks` (CR-07 queda diferido a Phase 11).
- **D-03:** Forwarding **silencioso** — sin `DeprecationWarning`, sin env-var opt-in. El target de v1.1 es zero-noise non-breaking; cualquier deprecation surface se introduce en v1.2/v2.0.
- **D-04:** Conftest de cada paquete migra de `monkeypatch.setattr(pkg.client, "_token", "test-token", raising=False)` + `monkeypatch.setattr(pkg.client, "_token_expires_at", 9_999_999_999.0, raising=False)` a `pkg.configure(token="<sentinel>", token_expires_at=9_999_999_999.0)`. La extensión de `configure()` con `token=...`/`token_expires_at=...` es prerrequisito del shim.

**Granularidad de planes en la fase**

- **D-05:** **5 planes** en la phase: Plan 1 — REFAC-01 (snapshot + guards, tests-only); Plans 2–5 — REFAC-02 per package, orden serial ámbito → iol → higyrus → matriz. Cada uno es **1 commit atómico** que incluye: `_state.py` + `Client`/`AsyncClient` + shim PEP 562 + migración de conftest del paquete + remoción de globals legacy module-level.
- **D-06:** Snapshot ownership: el plan REFAC-01 freezea el snapshot del estado **PRE-refactor**. Cada plan REFAC-02 actualiza el snapshot del paquete tocado añadiendo entradas nuevas (`Client`, `AsyncClient`, `close`, `aclose`, etc.) pero nunca removiendo.
- **D-07:** Test cadence por plan REFAC-02: `uv run pytest packages/<pkg>/` + `uv run pytest verification/test_public_surface.py` pre-commit. CI sigue corriendo full matrix completa.

**Mecanismo del public-surface snapshot**

- **D-08:** Storage: **text file per paquete** en `verification/snapshots/<pkg>-surface.txt`. Una línea por símbolo (sorted), incluye nombre + tipo (function/class/module attr) + signature stringified.
- **D-09:** Scope del snapshot: **top-level (`__all__`) + signatures + submodules públicos exposed** (`pkg.client`, `pkg.aio`, `pkg.models`, `pkg.exceptions`, `pkg.types` cuando aplique). NO incluye atributos privados (`_token`, `_client`).
- **D-10:** Test único: `verification/test_public_surface.py` con sweep × 4 paquetes. Sin per-package test file.
- **D-11:** Regeneración intencional: script `verification/regen_snapshots.py` que reescribe los 4 archivos. El operador commitea el diff junto con el cambio que lo justifica.
- **D-12:** Fixture-reaches-production guard scope: **1 test sync + 1 test async por paquete** sobre el auth header nativo: `iol` (`Authorization: Bearer <SENTINEL>`), `higyrus` (`Authorization: Bearer <SENTINEL>`), `matriz` (`X-Auth-Token: <SENTINEL>`), `ambito` (no-auth → verifica que `base_url` customizado vía `configure()` aparece en la URL). Total 8 tests. **No** cross-leak SYNC vs ASYNC guard en Phase 6.

**Signature de `Client.__init__`**

- **D-13:** Kwargs de `__init__`: **solo los equivalentes a `configure()` vigente + extensión token/token_expires_at**. `_ClientState` internamente lleva `refresh_token`/`account_id`/`http_client` pero **NO** se exponen como kwargs en Phase 6.
- **D-14:** Semántica de `pkg.configure(**kwargs)` post-refactor: **reemplaza `_default_client` con nueva instancia `Client(**kwargs)`**. Sin mutación in-place de `_default._state`. Preserva semántica v1.0 (reset de `_token`/`_client`). Instancias `Client()` explícitas del caller NO se ven afectadas por `configure()`.
- **D-15:** Lifecycle del `_default_client`: **lazy en primer acceso**.
- **D-16:** `AsyncClient` cleanup: **caller-responsible**. Implementa `aclose()` + `__aenter__`/`__aexit__`. Sin `atexit` handler. Sin `ResourceWarning` automático en `__del__`.
- **D-17:** Validación de credenciales: **lazy** — `Client()` sin credenciales NO raisea en `__init__`; `_ensure_token()` levanta `<Pkg>AuthError` en el primer call que necesite auth.
- **D-18:** `Client.__repr__()` redacta credenciales y token: muestra `<Pkg>Client(base_url='https://api.test', username='alice', password='***', token='***')`.

**Continuidad de patrones top-level**

- **D-19:** `load_dotenv()` se sigue llamando a nivel módulo de `client.py` (no `aio.py`, no `Client.__init__`).
- **D-20:** `pkg.login()` se mantiene como **función top-level** implementada como shim `def login(): return _get_default().login()`.
- **D-21:** Driver hooks: `main_higyrus.py` mutación de `pkg.client._client.event_hooks` funciona transparente porque el shim forwarda `_client` → `_default._state.http_client`. **`main_higyrus.py` NO se toca en Phase 6**.
- **D-22:** matriz `Client.login()` parsea `response.headers["X-Auth-Token"]` (no body) y store en `self._state.token`. El shim forwarda `pkg.client._token` → `_default._state.token`.

**Pickle/deepcopy contract**

- **D-23:** `Client.__reduce__()` raisea `TypeError(...)`. Aplica idéntico a `AsyncClient`. `__deepcopy__` también raisea.

### Claude's Discretion

El planner decide (basado en research):

- Estructura interna exacta de `_state.py` (dataclass shape, slots, default factories). El research recomienda `@dataclass(slots=True) _ClientState`.
- Implementación del `_get_default()` (módulo-level function vs cached property sobre el módulo).
- Convención de sentinels en conftest (`SYNC-sentinel-<pkg>` vs `test-token-<pkg>-sync` vs UUID-based). Mantener distinguibles sync vs async.
- Lugar exacto del `regen_snapshots.py` script y format del output.
- Si `Client` y `AsyncClient` heredan de un mismo `BaseClient` por paquete o son clases independientes.

### Deferred Ideas (OUT OF SCOPE)

- Cross-leak SYNC-sentinel vs ASYNC-sentinel guard test — Phase 7 REFAC-03.
- `http_client=` kwarg en `Client.__init__` — Phase 8 retry transport.
- `Client.from_env()` classmethod — backlog.
- `client.with_options(max_retries=N)` per-call override — Phase 8.
- `refresh_token` y `account_id` kwargs en `Client.__init__` — Phase 9 (BUG-03, BUG-04).
- CR-07 lock en `_capture_*_query_string` — Phase 11.
- CR-08 line length en `main_higyrus.py:767` — Phase 11.
- Disk persistence del refresh_token (IOL) — v1.2.
- `Client.__init__` con `use_dotenv=False` opt-out — diferido.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REFAC-01 | Safety net previo al refactor — golden public-surface snapshot + "fixture-reaches-production" guard test por paquete; baseline de test count, assertion count y coverage% registrados antes de cada phase. | "Standard Stack" section enumerates `inspect.signature` + golden text file pattern; "Code Examples" provides the snapshot enumerator and guard test template; "Common Pitfalls" #1 explains why `raising=False` silently breaks fixtures and how the guard catches it. |
| REFAC-02 | Clase `Client` (sync) + `AsyncClient` (async) por paquete con `close()`/`aclose()`, sync/async context manager, estado scoped a instancia (`base_url`, credenciales, token, http client, refresh_token); top-level functions (`pkg.get_X(...)`) y `configure(...)` quedan delegando en un default-client lazy module-level, vía PEP 562 `__getattr__` shim. | "Architecture Patterns" section provides the canonical `_ClientState` + `Client` + `_default_client` + PEP 562 shim recipe; "Per-Package Divergence Matrix" enumerates exact globals to migrate for each of the 4 packages; "Conftest Migration Pattern" maps current `monkeypatch.setattr` calls to the new `configure(token=...)` signature. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech stack:** Python 3.12+, uv, httpx (sync+async), pytest+pytest-httpx, ruff, mypy strict — every change must pass existing CI.
- **Arquitectura:** estado singleton a nivel de módulo, sin código compartido entre paquetes (by design). Phase 6 keeps "no shared internals" — `_state.py`, `Client`, `AsyncClient`, snapshot regen logic duplicated 4× across packages.
- **Dual sync/async:** every fix lives in BOTH `client.py` y `aio.py` of the same package (matriz still has no `aio.py` — Phase 10 territory).
- **Seguridad:** credenciales nunca en logs ni en reports; `Client.__repr__` redaction (D-18) is the relevant Phase 6 mechanism.
- **Dependencias externas en vivo:** Phase 6 is OFFLINE — no live tests. 277 mocked tests must stay green.
- **GSD enforcement (CLAUDE.md):** All edits must go through GSD commands; use `/gsd-execute-phase` for planned phase work.
- **`from __future__ import annotations`** is mandatory at the top of every module (project-wide convention) — applies to new `_state.py`.
- **No relative imports** (TID ruff rule) — `_state.py` must be imported as `from <pkg>._state import _ClientState`.
- **`@dataclass(frozen=True, slots=True)`** pattern is established in `SafeModel` (higyrus/matriz). `_ClientState` and `Client` should use `slots=True` for consistency; frozen=False because `_state.token` must be re-writable.
- **Line length 100, double quotes, 4-space indent** (ruff format).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Public-surface enumeration | `verification/` (harness) | — | Tests live in `verification/test_public_surface.py` (per D-10); snapshot regen script lives in `verification/regen_snapshots.py` (per D-11). Harness is repo-internal, not published with packages. |
| Fixture-reaches-production guard | `packages/<pkg>/tests/` | — | Each guard test is package-scoped (uses pytest-httpx against that package's auth header). Cannot live in `verification/` because `verification/` modules are not importable from published wheels. |
| `_ClientState` dataclass | `packages/<pkg>/src/<pkg>/_state.py` (new) | — | One file per package, no cross-package import (project constraint). |
| `Client` / `AsyncClient` classes | `packages/<pkg>/src/<pkg>/client.py` and `aio.py` | `_state.py` for state | Classes own behavior; `_state.py` owns just the data dataclass. Phase 7 moves pure logic to `_core.py`; Phase 6 keeps logic inside `Client` methods. |
| PEP 562 `__getattr__` shim | `packages/<pkg>/src/<pkg>/client.py` (and `aio.py`) | — | Read-only shim at module level. Must NOT live in `_state.py` because shim must intercept module-level reads from `pkg.client._token` etc. |
| Lazy `_default_client` | `packages/<pkg>/src/<pkg>/client.py` (and `aio.py`) | — | One module-level None-initialized variable plus a `_get_default()` helper per surface. State independence sync ↔ async preserved by having TWO `_default_*_client` singletons. |
| `configure(token=..., token_expires_at=...)` | `packages/<pkg>/src/<pkg>/client.py` (and `aio.py`) | — | Top-level function; replaces `_default_client` with new instance (D-14). New kwargs `token` and `token_expires_at` (and for IOL: `refresh_token` is internal-only per D-13, NOT a kwarg; we MUST surface this gap — see "Common Pitfalls #3"). |
| Conftest migration | `packages/<pkg>/tests/conftest.py` | — | Migrate autouse fixtures from `monkeypatch.setattr(pkg.client, "_token", ...)` to `pkg.configure(token=...)`. Test bodies that monkeypatch `_token`/`_refresh_token`/`_token_expires_at` continue to use monkeypatch because the read-only shim resolves their reads correctly. |
| 277 mocked tests untouched | `packages/<pkg>/tests/test_*.py` | — | All passing after the shim is in place; the conftest migration is the only test code change required for fixtures. Test bodies that READ `pkg.client._token` keep working (shim forwards reads). Test bodies that WRITE `pkg.client._token` (the test_client.py inline `monkeypatch.setattr`) keep working because monkeypatch DOES write to the module dict and the shim only intercepts on `AttributeError` (i.e., when the attribute is NOT in the module dict). |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | >=0.27 [VERIFIED: existing pyproject.toml] | Sync + async HTTP client; existing dependency. `_ClientState.http_client` will be typed `httpx.Client | httpx.AsyncClient`. | The 4 packages already use httpx exclusively; no change needed. [VERIFIED: codebase grep] |
| `dataclasses` (stdlib) | Py 3.12 [VERIFIED: pyproject.toml `requires-python = ">=3.12"`] | `@dataclass(slots=True)` for `_ClientState` and (recommended) for `Client`/`AsyncClient`. | `slots=True` is the project idiom (already in `higyrus_client.models.SafeModel`, `matriz_client.models.*`). [VERIFIED: codebase grep] |
| `inspect` (stdlib) | Py 3.12 | `inspect.signature`, `inspect.getmembers`, `inspect.isfunction`, `inspect.isclass` for snapshot enumeration. | Standard library, no new dep. `signature()` accepts plain functions, classes, and `functools.partial`. [CITED: docs.python.org/3/library/inspect.html] |
| `pytest-httpx` | >=0.34 [VERIFIED: existing dev-dependencies] | Intercept outgoing wire requests, assert `Authorization` / `X-Auth-Token` header contains the sentinel. | Already in the dev-dependencies group; used by every existing test file. [VERIFIED: codebase grep] |
| `pytest-asyncio` | >=0.24 [VERIFIED: existing dev-dependencies], `asyncio_mode = "auto"` [VERIFIED: pyproject.toml] | Async test runner for the 4 async guard tests + matriz async TBD (matriz `aio.py` is Phase 10). | Already in the dev group. The conftest pattern (sync + async autouse) is already established (`packages/iol-client/tests/conftest.py`). [VERIFIED] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typing` (stdlib) | Py 3.12 | `Self` for `Client.__enter__ -> Self`, `TYPE_CHECKING` for any forward refs. | `Self` is preferred over a quoted `"Client"` return type since Python 3.11. [CITED: PEP 673] |
| `dotenv` (`python-dotenv`) | existing | `load_dotenv()` at top of each `client.py` (D-19 preserves this pattern). | Phase 6 does NOT add `load_dotenv()` to `aio.py` or `Client.__init__`. [VERIFIED: existing code] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-written text snapshot file (per D-08) | `syrupy`, `pytest-snapshot`, `snapshottest` | Snapshot libraries add a dependency and store snapshots in their own format. D-08 locks "text file per paquete" with sorted lines for human-readable diffs. Adding `syrupy` would violate "no new runtime deps unless required" and break the deterministic `git log -- verification/snapshots/<pkg>-surface.txt` forensic pattern (D-11). REJECTED. |
| `ModuleType` subclass with `__setattr__` | sys.modules[__name__] = MyModule(...) | PEP 726 (`__setattr__` for modules) is not accepted; `ModuleType` subclass works but is brittle (some Python introspection tools assume plain modules). D-01 locks read-only `__getattr__` only. CONTEXT.md explicitly rejects this because the conftest migration is the chosen mitigation, not bidirectional forwarding. [CITED: PEP 562, PEP 726] |
| `Protocol` for "client-like" type | Concrete `Client` class with no Protocol | Pitfall #27 in `.planning/research/PITFALLS.md` warns Protocols lock in `_request` signature, breaking subclasses. Phase 6 has no subclassing requirement. REJECTED unless Phase 8 needs it for retry decoration. |
| Frozen dataclass for `_ClientState` | Non-frozen with `slots=True` | `_state.token`, `_state.token_expires_at`, and `_state.refresh_token` are MUTATED on every `_ensure_token()`. Frozen requires `dataclasses.replace`, which allocates a new `_ClientState` and breaks identity (any code that holds `state` reference sees stale data). REJECTED — `_ClientState` is NOT frozen. |

**Installation:** No new package installs required. All dependencies already in `pyproject.toml`.

**Version verification:** Nothing to verify — Phase 6 adds no runtime or dev deps.

## Package Legitimacy Audit

> No external packages installed by this phase. All work is internal restructuring + tests-only additions using already-installed dev dependencies.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none) | — | — | — | — | — | N/A — phase introduces no new packages |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                       ┌────────────────────────────────────┐
                       │   pytest runner / IDE / driver     │
                       └───────────────┬────────────────────┘
                                       │
                ┌──────────────────────┼───────────────────────┐
                │                      │                       │
       import pkg            from pkg import aio       c = pkg.Client(...)
       pkg.get_quote(...)    await aio.get_quote(...)  c.get_quote(...)
                │                      │                       │
                ▼                      ▼                       ▼
   ┌────────────────────────┐   ┌────────────────────────┐
   │ pkg/client.py (sync)   │   │ pkg/aio.py (async)    │
   │                        │   │                        │
   │ load_dotenv()          │   │                        │
   │                        │   │                        │
   │ # top-level functions  │   │ # top-level functions  │
   │ def configure(*,       │   │ async def configure... │
   │   base_url, username,  │   │ def configure(*, ...,  │
   │   password, token,     │   │   token, token_exp): - │
   │   token_expires_at):   │   │   _default_async =     │
   │   _default = Client(.) │   │     AsyncClient(...)   │
   │                        │   │                        │
   │ def get_quote(...):    │   │ async def get_quote... │
   │   return _get_def..    │   │   return await _get_d  │
   │     .get_quote(...)    │   │     .get_quote(...)    │
   │                        │   │                        │
   │ # PEP 562 shim         │   │ # PEP 562 shim         │
   │ _FORWARDED_NAMES = {   │   │ _FORWARDED_NAMES = {   │
   │   "_token",            │   │   "_token",            │
   │   "_token_expires_at", │   │   "_token_expires_at", │
   │   "_refresh_token",    │   │   "_refresh_token",    │
   │   "_client",           │   │   "_token_lock",       │
   │ }                      │   │   "_client",           │
   │ def __getattr__(name): │   │ }                      │
   │   if name in _FW:      │   │ def __getattr__(name): │
   │     d = _get_default() │   │   ...                  │
   │     return getattr(    │   │                        │
   │       d._state, ...)   │   │                        │
   │   raise AttributeError │   │                        │
   │                        │   │                        │
   │ # The class            │   │ # The class            │
   │ @dataclass(slots=True) │   │ @dataclass(slots=True) │
   │ class Client:          │   │ class AsyncClient:     │
   │   _state: _ClientState │   │   _state: _ClientState │
   │   def __init__(*,...): │   │   def __init__(*,...): │
   │   def login(...): ...  │   │   async def login...   │
   │   def get_quote(...):  │   │   async def get_quote: │
   │     self._request(...) │   │     await self._request│
   │   def close(): ...     │   │   async def aclose():  │
   │   __enter__/__exit__   │   │   __aenter__/__aexit__ │
   │   __repr__ (redacted)  │   │   __repr__ (redacted)  │
   │   __reduce__/__deep__  │   │                        │
   │     -> TypeError       │   │                        │
   │                        │   │                        │
   │ _default_client = None │   │ _default_async = None  │
   │ def _get_default():    │   │ def _get_default():    │
   │   global _default_..   │   │   global _default_..   │
   │   if not _default_..:  │   │   if not _default_..:  │
   │     _default_..=Client │   │     _default_..=AsCl   │
   │   return _default_..   │   │   return _default_..   │
   └────────────────────────┘   └────────────────────────┘
              ▲
              │ (forwarded)
              │
              ▼
     ┌────────────────────────────┐
     │ pkg/_state.py (NEW)        │
     │                            │
     │ @dataclass(slots=True)     │
     │ class _ClientState:        │
     │   base_url: str = ""       │
     │   username: str = ""       │
     │   password: str = ""       │
     │   token: str | None = None │
     │   token_expires_at: float  │
     │     = 0.0                  │
     │   refresh_token: str|None  │
     │     = None  # iol only;    │
     │     others keep at None    │
     │   account_id: str | None   │
     │     = None  # higyrus,     │
     │     forward-declare        │
     │     for Phase 9 BUG-04     │
     │   http_client: httpx.Client│
     │     | httpx.AsyncClient    │
     │     | None = None          │
     │   token_lock: asyncio.Lock │
     │     | None = None  # aio   │
     │                            │
     │   def redacted_repr(): ... │
     └────────────────────────────┘
```

**Data flow trace — top-level sync call after Phase 6:**

1. Caller does `iol_client.get_quote("GGAL")`.
2. `iol_client/__init__.py` re-exports `get_quote` from `iol_client.client`.
3. `iol_client.client.get_quote("GGAL")` is the compat-layer top-level function. It calls `_get_default()`.
4. `_get_default()` checks if `_default_client is None`; if so, instantiates `Client()` (which reads env vars via `_ClientState`'s default factories).
5. Returns `_default_client.get_quote("GGAL")`.
6. `Client.get_quote(self, ...)` calls `self._request("GET", path, ...)`.
7. `self._request` calls `self._ensure_token()` which mutates `self._state.token` and `self._state.token_expires_at`.
8. Outgoing request uses `headers={"Authorization": f"Bearer {self._state.token}"}`.

**Data flow trace — legacy fixture read:**

1. Test does `assert iol_client.client._token == "tok-iol"` (existing test pattern).
2. Python attribute lookup on the module finds no `_token` attribute (it was removed in REFAC-02).
3. PEP 562 `__getattr__("_token")` fires.
4. `_token` is in `_FORWARDED_NAMES`; the shim returns `_get_default()._state.token`.
5. Test sees the expected value.

**Data flow trace — legacy fixture monkeypatch:**

1. Test does `monkeypatch.setattr(iol_client.client, "_token", None, raising=False)` (in a test body, NOT in conftest).
2. `monkeypatch.setattr` writes `_token` directly to `iol_client.client.__dict__`.
3. Subsequent reads of `iol_client.client._token` find it in the module dict — PEP 562 `__getattr__` is NOT invoked.
4. BUT: production code reads `self._state.token`, not `iol_client.client._token` — so this monkeypatch lands on a dead address.
5. **MITIGATION:** the conftest must do `pkg.configure(token=...)` not `monkeypatch.setattr`. Inline test-body monkeypatches that simulate "token expired / refresh stale" scenarios (IOL `test_refresh_token_success_path` etc.) must be rewritten to use `pkg.configure(token=None, token_expires_at=0.0, refresh_token="...")` or some equivalent.

⚠ **This is the single biggest scope gap surfaced by the codebase audit** — see "Common Pitfalls #3" below.

### Recommended Project Structure (per package)

```
packages/<pkg>/src/<pkg>/
├── __init__.py            # unchanged — re-exports Client, AsyncClient additionally
├── client.py              # restructured: load_dotenv() at top, configure(), get_X() shims, PEP 562 __getattr__, Client class, _default_client
├── aio.py                 # restructured: configure(), async get_X() shims, PEP 562 __getattr__, AsyncClient class, _default_async_client
├── _state.py              # NEW — @dataclass(slots=True) _ClientState
├── exceptions.py          # unchanged
├── models.py              # unchanged (higyrus, matriz only)
├── _params.py / _parsing.py / types.py  # unchanged
└── py.typed               # unchanged

verification/
├── test_public_surface.py     # NEW — single test sweeping all 4 packages
├── regen_snapshots.py         # NEW — operator-run script to refresh snapshots
└── snapshots/
    ├── iol-client-surface.txt        # NEW — committed; pre-refactor baseline updated per package commit
    ├── higyrus-client-surface.txt    # NEW
    ├── matriz-client-surface.txt     # NEW
    └── ambito-financiero-client-surface.txt  # NEW

packages/<pkg>/tests/
├── conftest.py             # migrated to pkg.configure(token=..., token_expires_at=...)
├── test_client.py          # unchanged; reads via PEP 562 shim still work
├── test_async_client.py    # unchanged (matriz has no test_async_client.py — Phase 10)
└── test_fixture_reaches_production.py  # NEW per package — 2 tests (sync + async)
```

### Pattern 1: PEP 562 `__getattr__` shim at module level

**What:** Define a module-level `__getattr__(name)` that forwards reads of legacy global names to the default client's state.
**When to use:** ALWAYS in Phase 6 — it's the entire backward-compat mechanism per CONTEXT.md D-01.
**Example:**

```python
# packages/iol-client/src/iol_client/client.py
# Source: PEP 562 (peps.python.org/pep-0562/) + CONTEXT.md D-02

from __future__ import annotations

from typing import Any

from iol_client._state import _ClientState

# ... Client class definition ...

_default_client: Client | None = None


def _get_default() -> Client:
    global _default_client
    if _default_client is None:
        _default_client = Client()  # reads env vars via _ClientState defaults
    return _default_client


# PEP 562 shim — D-02 enumerates the forwarded names for iol-client.
_FORWARDED_TO_STATE: dict[str, str] = {
    "_token": "token",
    "_token_expires_at": "token_expires_at",
    "_refresh_token": "refresh_token",  # IOL-specific
    # _password: NOT FORWARDED per D-02 (but see Pitfall #3)
    # _user: NOT FORWARDED per D-02
    # _base_url: NOT FORWARDED per D-02
}

_FORWARDED_HTTP_CLIENT = "_client"  # D-02 exception: forwarded for main_higyrus.py compat


def __getattr__(name: str) -> Any:
    """PEP 562 read-only shim (D-01, D-02).

    Reads of legacy module-level globals are forwarded to the lazy default
    client's state. WRITES land on the module dict directly (PEP 562 does
    not intercept __setattr__ for plain modules); tests that monkeypatch
    these names must migrate to pkg.configure(token=..., ...) — handled in
    the conftest of each package.
    """
    if name in _FORWARDED_TO_STATE:
        return getattr(_get_default()._state, _FORWARDED_TO_STATE[name])
    if name == _FORWARDED_HTTP_CLIENT:
        # main_higyrus.py mutates _client.event_hooks; preserve by forwarding
        # to the underlying httpx.Client. CR-07 (lock for event_hooks mutation)
        # is deferred to Phase 11.
        return _get_default()._state.http_client
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

### Pattern 2: `_ClientState` dataclass + lazy env defaults

**What:** A `@dataclass(slots=True)` holding all per-instance state. Defaults come from env vars read at instance construction time (NOT at class definition time — env vars set after import must work).
**Example:**

```python
# packages/iol-client/src/iol_client/_state.py
# Source: CONTEXT.md D-13, D-17, D-19 + existing constants from client.py:43-56

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field

import httpx

DEFAULT_BASE_URL = "https://api.invertironline.com"
_REQUEST_TIMEOUT = 30.0
_TOKEN_TTL_BUFFER_SECONDS = 60


def _env_base_url() -> str:
    return os.getenv("IOL_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _env_user() -> str:
    return os.getenv("IOL_USER", "")


def _env_password() -> str:
    return os.getenv("IOL_PASSWORD", "")


@dataclass(slots=True)
class _ClientState:
    """Per-instance state for IOL Client / AsyncClient.

    NOT frozen — token/token_expires_at/refresh_token are mutated on
    _ensure_token() refresh.
    """
    base_url: str = field(default_factory=_env_base_url)
    username: str = field(default_factory=_env_user)
    password: str = field(default_factory=_env_password)
    token: str | None = None
    token_expires_at: float = 0.0
    refresh_token: str | None = None  # IOL-specific; other pkgs keep at None
    account_id: str | None = None  # forward-declared for Phase 9 BUG-04 (higyrus)
    http_client: httpx.Client | httpx.AsyncClient | None = None
    token_lock: asyncio.Lock | None = None  # AsyncClient only
```

### Pattern 3: `Client.__enter__`/`__exit__` and lazy http_client

**What:** Sync context manager opens the `httpx.Client` lazily (mirroring v1.0 module-level lazy semantics) and closes it on exit. `close()` is the explicit equivalent.
**Example:**

```python
# packages/iol-client/src/iol_client/client.py

from typing import Self

class Client:
    """Sync client; instance state in self._state.

    Pickle / deepcopy contract (D-23): NOT supported. Use multiprocessing
    fork start method or rebuild from configure() in worker.
    """
    __slots__ = ("_state",)

    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        token_expires_at: float | None = None,
    ) -> None:
        self._state = _ClientState()
        if base_url is not None:
            self._state.base_url = base_url.rstrip("/")
        if username is not None:
            self._state.username = username
        if password is not None:
            self._state.password = password
        if token is not None:
            self._state.token = token
        if token_expires_at is not None:
            self._state.token_expires_at = token_expires_at

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._state.http_client is not None:
            self._state.http_client.close()
            self._state.http_client = None

    def __repr__(self) -> str:
        # D-18: redact credentials and token
        return (
            f"<IOLClient(base_url={self._state.base_url!r}, "
            f"username={self._state.username!r}, "
            f"password={'***' if self._state.password else ''!r}, "
            f"token={'***' if self._state.token else None!r})>"
        )

    def __reduce__(self):  # D-23
        raise TypeError(
            "IOLClient is not picklable; use multiprocessing's fork start "
            "method or recreate in worker via iol_client.Client(...)"
        )

    def __deepcopy__(self, memo):  # D-23
        raise TypeError("IOLClient is not deepcopy-safe (httpx.Client owns "
                        "TCP pool + SSL context)")
```

### Pattern 4: `AsyncClient` with lazy http_client + per-instance asyncio.Lock

**What:** Mirror of the sync class with `__aenter__`/`__aexit__`/`aclose()`. The `asyncio.Lock` lives on `_state.token_lock` and is created lazily (NOT in `__init__` — asyncio.Lock no longer needs a running loop in 3.10+, but creating it lazily avoids any loop-binding surprises).
**Example:**

```python
# packages/iol-client/src/iol_client/aio.py

import asyncio

class AsyncClient:
    __slots__ = ("_state", "_client_lock")

    def __init__(self, *, base_url=None, username=None, password=None,
                 token=None, token_expires_at=None) -> None:
        self._state = _ClientState()
        # ... same field copy as sync Client ...
        # Locks created lazily on first use (avoid binding to a loop in __init__)
        self._client_lock: asyncio.Lock | None = None

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._state.http_client is not None:
            assert isinstance(self._state.http_client, httpx.AsyncClient)
            await self._state.http_client.aclose()
            self._state.http_client = None
```

### Pattern 5: Public-surface snapshot test

**What:** A single pytest module that, for each of the 4 packages, enumerates public attributes (`__all__` + public submodules) via `inspect`, serializes to a deterministic text format, and compares against a committed text file.
**Example:**

```python
# verification/test_public_surface.py
# Source: D-08, D-09, D-10 + inspect.signature docs

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import Any

import pytest

_PACKAGES = [
    "ambito_financiero_client",
    "iol_client",
    "higyrus_client",
    "matriz_client",
]
_SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def _kind(obj: Any) -> str:
    if inspect.isclass(obj):
        return "class"
    if inspect.isfunction(obj) or inspect.ismethod(obj):
        return "function"
    if inspect.iscoroutinefunction(obj):
        return "coroutine"
    if inspect.ismodule(obj):
        return "module"
    return type(obj).__name__


def _stringify_signature(obj: Any) -> str:
    try:
        sig = inspect.signature(obj)
    except (TypeError, ValueError):
        return ""
    return str(sig)


def _enumerate_surface(pkg_name: str) -> list[str]:
    pkg = importlib.import_module(pkg_name)
    names = sorted(getattr(pkg, "__all__", []))
    lines: list[str] = []
    for name in names:
        obj = getattr(pkg, name)
        kind = _kind(obj)
        sig = _stringify_signature(obj) if kind in ("class", "function", "coroutine") else ""
        lines.append(f"{name} : {kind} : {sig}")
    return lines


def _snapshot_path(pkg_name: str) -> Path:
    slug = pkg_name.replace("_", "-")
    return _SNAPSHOT_DIR / f"{slug}-surface.txt"


@pytest.mark.parametrize("pkg_name", _PACKAGES)
def test_public_surface_matches_snapshot(pkg_name: str) -> None:
    """Golden-file test: assert package public surface matches the committed
    snapshot. Regenerate via `python verification/regen_snapshots.py`."""
    actual = "\n".join(_enumerate_surface(pkg_name)) + "\n"
    expected = _snapshot_path(pkg_name).read_text()
    assert actual == expected, (
        f"\nPublic surface of {pkg_name} drifted from snapshot at "
        f"{_snapshot_path(pkg_name)}.\n"
        f"Run `python verification/regen_snapshots.py` to refresh "
        f"AFTER verifying the change is intentional.\n"
    )
```

### Pattern 6: Fixture-reaches-production guard test (per package)

**What:** `monkeypatch.setattr` (or `pkg.configure(token=...)`) a sentinel, fire a real `get_X(...)` call against `httpx_mock`, assert the sentinel ends up in the wire request's auth header.
**Example:**

```python
# packages/iol-client/tests/test_fixture_reaches_production.py
# Source: CONTEXT.md D-12 + Pitfall #1 mitigation

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

import iol_client
from iol_client import aio


def test_sync_configure_token_reaches_wire(httpx_mock: HTTPXMock) -> None:
    """REFAC-01 guard: monkeypatched sentinel must reach Authorization header."""
    iol_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="SYNC-sentinel-iol",
        token_expires_at=9_999_999_999.0,
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json=[],
    )
    iol_client.get_instruments("argentina")
    [req] = httpx_mock.get_requests()
    assert req.headers["Authorization"] == "Bearer SYNC-sentinel-iol"


async def test_async_configure_token_reaches_wire(httpx_mock: HTTPXMock) -> None:
    aio.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="ASYNC-sentinel-iol",
        token_expires_at=9_999_999_999.0,
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json=[],
    )
    await aio.get_instruments("argentina")
    [req] = httpx_mock.get_requests()
    assert req.headers["Authorization"] == "Bearer ASYNC-sentinel-iol"
```

For ambito (no auth), assert `base_url` reaches the URL instead of header (per D-12):

```python
def test_ambito_sync_configure_base_url_reaches_wire(httpx_mock):
    ambito_financiero_client.configure(base_url="https://configured.test")
    httpx_mock.add_response(
        url="https://configured.test/dolarnacion/historico-general/2026-01-02/2026-01-02",
        json=[["Fecha","Compra","Venta"], ["02/01/2026","1.000,00","1.100,00"]],
    )
    ambito_financiero_client.get_dollar_banco_nacion(dt.date(2026, 1, 2))
    [req] = httpx_mock.get_requests()
    assert "configured.test" in str(req.url)
```

For matriz: header is `X-Auth-Token` (D-12), not `Authorization`.

### Pattern 7: Snapshot regen script

**What:** Operator-run Python script that rewrites the 4 text files. Committed alongside the change that justified the surface change.

```python
# verification/regen_snapshots.py
# Source: D-11

from __future__ import annotations

from pathlib import Path

# Re-use the enumeration logic from the test module
from verification.test_public_surface import _PACKAGES, _enumerate_surface, _snapshot_path


def main() -> None:
    for pkg_name in _PACKAGES:
        lines = _enumerate_surface(pkg_name)
        text = "\n".join(lines) + "\n"
        _snapshot_path(pkg_name).write_text(text)
        print(f"Wrote {_snapshot_path(pkg_name)} ({len(lines)} symbols)")


if __name__ == "__main__":
    main()
```

### Anti-Patterns to Avoid

- **`ModuleType` subclass with `__setattr__`:** REJECTED by D-01. Use read-only `__getattr__` only.
- **`frozen=True` on `_ClientState`:** breaks token refresh (state.token must mutate). Use `slots=True` only.
- **`Client.__init__` raising on missing credentials:** D-17 locks lazy validation; raise in `_ensure_token()`, not in `__init__`.
- **Creating `asyncio.Lock()` at module level:** existing code does this (`packages/iol-client/src/iol_client/aio.py:39`). The lock is created in a no-loop context — works in Python 3.10+ but is a footgun. After the refactor, locks live on `_ClientState.token_lock` and should be created lazily in `_ensure_token()` first call.
- **`atexit.register(client.close)`:** D-16 explicitly forbids — sync close is safe but async close has no loop. Document the contract; don't auto-register.
- **`load_dotenv()` in `Client.__init__`:** D-19 keeps `load_dotenv()` at module top of `client.py` only. Not in `aio.py`, not in `__init__`.
- **Importing `verification/redaction.py` from inside a package:** the published wheels do not include `verification/`. Redaction logic for `__repr__` must be inlined (a simple `'***' if value else ''` is fine).
- **Re-exporting `_ClientState` from `__init__.py`:** keep it private (`_state.py` private module + leading underscore class name).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Public-API introspection | Walk `pkg.__dict__` filtering by name | `inspect.signature(obj)` + `inspect.isfunction/isclass` + sorted `__all__` | `inspect.signature` handles `*` keyword-only markers, `=` defaults, return annotations, `partial`, and async wrappers correctly. Hand-walking misses defaulted-to-None args and gets the order wrong. [CITED: docs.python.org/3/library/inspect.html] |
| Async context manager idiom | Implement `__aenter__`/`__aexit__` manually with try/finally on every endpoint method | `async with AsyncClient(...) as c:` plus a single `_aenter/_aexit` pair returning `self` | Standard `contextlib`-style pattern; misuse leads to "RuntimeError: Event loop is closed" pitfall #12. |
| Token expiry tracking | Hand-roll a thread-safe expiry counter | `_state.token_expires_at: float` (absolute epoch seconds) compared against `time.time()` | The 4 existing packages already use this pattern — preserve it. Don't change semantics in Phase 6. |
| Module-level read forwarding | `getattr` hacks via `__init__` re-assignment | PEP 562 `def __getattr__(name)` at module top level | PEP 562 is the documented Python mechanism (since 3.7). [CITED: peps.python.org/pep-0562/] |

**Key insight:** Phase 6 is a discipline phase, not a discovery phase. Every pattern is already standard in Python; the work is mechanical application without breaking 277 tests.

## Per-Package Divergence Matrix (critical for planner)

| Concern | ambito | iol | higyrus | matriz |
|---------|--------|-----|---------|--------|
| Existing `aio.py`? | YES | YES | YES | **NO** (Phase 10 territory) |
| Token model | None (public API) | OAuth2 password grant + refresh_token | Bearer (POST `/api/login`) | Bearer in `X-Auth-Token` header (POST `/auth/getToken`) |
| Token expiry field | N/A | `_token_expires_at: float` (absolute, with 60s buffer) | `_token_ts: float` (timestamp, TTL = 23h compared in `_ensure_token`) | `_token_ts: float` (same as higyrus, TTL = 23h) |
| `configure()` kwargs (current) | `base_url`, `user_agent` | `base_url`, `username`, `password` | `base_url`, `username`, `password`, `client_id` | `base_url`, `username`, `password` |
| `configure()` kwargs (Phase 6 extension per D-13) | `base_url`, `user_agent` (UNCHANGED — no token to inject) | `+token`, `+token_expires_at` | `+token`, `+token_expires_at` | `+token`, `+token_expires_at` |
| Has `_refresh_token` global? | NO | **YES** | NO | NO |
| Has `_client_id` global? | NO | NO | **YES** | NO |
| Token lock pattern (async) | `_client_lock` only (no token cache) | `_token_lock` + `_client_lock` (double-lock) | `_token_lock` + `_client_lock` | N/A (no `aio.py`) |
| Auth header in `_request` | (no auth) | `Authorization: Bearer <token>` | `Authorization: Bearer <token>` | `X-Auth-Token: <token>` |
| HTTP Basic Auth fallback | No | No | No | YES (Risk API §9 — see `_risk_auth()`) |
| Module-level `httpx.Client` (sync) | `_client = httpx.Client(...)` created at import | Same | Same | `_session = httpx.Client(...)` (renamed) |
| Phase 6 globals to remove from module level | `_base_url`, `_user_agent`, `_client` | `_base_url`, `_user`, `_password`, `_token`, `_token_expires_at`, `_refresh_token`, `_client` | `_base_url`, `_client_id`, `_user`, `_password`, `_token`, `_token_ts`, `_client` | `_base_url`, `_user`, `_password`, `_token`, `_token_ts`, `_session` |
| Phase 6 globals KEPT/forwarded by PEP 562 shim (per D-02) | `_client` (sync only) — for any driver compat | `_token`, `_token_expires_at`, `_refresh_token` (**needs review**, see Pitfall #3), `_client` | `_token`, `_token_ts`, `_client` | `_token`, `_token_ts`, `_session` (named `_session` not `_client`, see test_client.py imports) |
| `ws_client.py` interactions | N/A | N/A | N/A | reads `_rest._base_url`, `_rest._token`, calls `_rest._ensure_token()` — **the shim must forward `_base_url` AND `_ensure_token()` must remain a top-level callable, OR ws_client must be updated to use `_rest._get_default()._state.base_url` / `.token`** |

⚠ **Matriz scope clarification:** CONTEXT.md D-22 says matriz `Client.login()` parses `response.headers["X-Auth-Token"]`. matriz has NO `aio.py` today (D-08 lists 4 packages including matriz; Plan 5 must also create `AsyncClient` for matriz). **But matriz `aio.py` (REST async surface) is Phase 10 (REFAC-04), not Phase 6.** This contradiction must be resolved: CONTEXT.md success criterion 3 says "Los 4 paquetes exponen `Client` (sync) y `AsyncClient` (async)" — for matriz this means a stub `AsyncClient` class with `__aenter__`/`__aexit__`/`aclose()` + a forward-declared body that raises `NotImplementedError` on REST methods, OR matriz is exempt from `AsyncClient` in Phase 6 and the success criterion refers only to sync `Client` for matriz. **OPEN QUESTION FOR PLANNER** — see "Open Questions" section.

## Conftest Migration Pattern

Current (4 packages — see `packages/<pkg>/tests/conftest.py`):

```python
@pytest.fixture(autouse=True)
def _configure_sync(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    iol_client.configure(base_url="https://api.test", username="u", password="p")
    monkeypatch.setattr(iol_client.client, "_token", "test-token", raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 9_999_999_999.0, raising=False)
    yield
    iol_client.configure(base_url="https://api.test", username="", password="")
```

After Phase 6:

```python
@pytest.fixture(autouse=True)
def _configure_sync() -> Iterator[None]:
    iol_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    yield
    iol_client.configure(base_url="https://api.test", username="", password="")
```

**Key:** `monkeypatch` is no longer needed in autouse fixtures because `configure()` replaces `_default_client` with a fresh instance and Phase 6's `configure()` signature accepts `token=` and `token_expires_at=` directly (D-04). The teardown `configure(...)` call in the existing fixtures already serves as cleanup.

Per-package conftest changes summary:
- **ambito:** trivial — no token to inject, only `base_url` (and `user_agent` if a test uses it).
- **iol:** add `token=` + `token_expires_at=` kwargs. `refresh_token=` is **not** currently in the conftest, so the autouse fixture migration is clean.
- **higyrus:** add `token=` + `token_expires_at=` (note higyrus uses `_token_ts` internally — `configure(token_expires_at=...)` should set `state.token_expires_at = token_expires_at`; but higyrus current `_ensure_token` compares `time.time() - _token_ts < _TOKEN_TTL_SECONDS`. **The semantic mapping is: `token_expires_at` for the Client API means "wall-clock time when token becomes invalid"; internally, higyrus's `Client._ensure_token` can compute the boolean check from `state.token_expires_at` directly, OR store `state.token_ts = token_expires_at - _TOKEN_TTL_SECONDS` to preserve existing arithmetic.** Recommend: change higyrus internal field to `token_expires_at: float` (drop the `_token_ts` name) for consistency across packages — the project skill conventions allow this rename since it's an internal field, and CONTEXT.md D-04 explicitly locks the EXTERNAL name as `token_expires_at`.
- **matriz:** add `token=` + `token_expires_at=`; same internal mapping note as higyrus.

## Inline Test-Body Migration (CRITICAL — surfaces a CONTEXT.md gap)

The autouse conftest is the easy migration. The hard cases are inline `monkeypatch.setattr(pkg.client, "_token", ...)` calls in test bodies (e.g., `packages/iol-client/tests/test_client.py:147-149, 177-179, 215-217, 244-245, 275-277, 307, 314`). These do operations like:

```python
# test_client.py:147-149
monkeypatch.setattr(iol_client.client, "_token", None, raising=False)
monkeypatch.setattr(iol_client.client, "_token_expires_at", 0.0, raising=False)
monkeypatch.setattr(iol_client.client, "_refresh_token", "refresh-cached", raising=False)
```

**Why these still work after Phase 6 (mostly):**
- `monkeypatch.setattr` writes the name directly into `iol_client.client.__dict__`. PEP 562 `__getattr__` only fires on `AttributeError`, so subsequent reads find the value in `__dict__` and do NOT consult the shim.
- BUT: production code (`Client._request`, `Client._ensure_token`) reads `self._state.token`, NOT `iol_client.client._token`. The monkeypatched value is on the wrong object.

**Therefore:** every inline `monkeypatch.setattr(pkg.client, "_token", X, raising=False)` in a test body lands on a dead address after Phase 6, just like Pitfall #1 warned.

**Required mitigations (planner must add tasks for):**

1. Extend `configure()` to also accept `refresh_token=...` for iol (currently D-13 says NO — needs revisit). OR provide a `_get_default()` test helper that returns the default client so tests can do `iol_client._get_default()._state.token = None`.
2. Rewrite the ~15 inline monkeypatch sites in `test_client.py` and `test_async_client.py` to use the new mechanism. This is part of the per-package REFAC-02 plan, NOT a separate plan.
3. The 8 fixture-reaches-production guard tests (REFAC-01) must SPECIFICALLY catch this for at least the simple `_token` case via the conftest migration; the test bodies' monkeypatches are caught when those tests run after the refactor lands.

**Recommended pattern for inline monkeypatch migration:**

Either (a) expose `_get_default()` as `pkg.client._get_default()` (public-ish helper) so tests can write to its `._state` directly, or (b) extend `Client.configure_instance(...)` as a sibling of top-level `configure()` that callers can use against a specific instance. Plan should pick one and stick with it across the 4 packages.

## Runtime State Inventory

> Phase 6 is a refactor phase (string-level rename of module globals → instance attributes). Runtime state inventory applies.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no databases, no file persistence of credentials/tokens. Process-level only. | none |
| Live service config | None — no n8n / datadog / cloudflare. Just `.env` files. | none |
| OS-registered state | None — no Task Scheduler, no pm2, no systemd, no launchd. | none |
| Secrets/env vars | `IOL_USER`, `IOL_PASSWORD`, `IOL_BASE_URL`, `HIGYRUS_USER`, `HIGYRUS_PASSWORD`, `HIGYRUS_BASE_URL`, `HIGYRUS_CLIENT_ID`, `PRIMARY_USER`, `PRIMARY_PASSWORD`, `PRIMARY_BASE_URL`, `AMBITO_BASE_URL`. These env var **names** are unchanged; only the code that consumes them moves from module-level `os.getenv` to `_ClientState` default factories. | none — code edit only. |
| Build artifacts / installed packages | `packages/<pkg>/src/<pkg>/__pycache__/` — invalidated automatically by mtime on `.py` file edit; no `egg-info` issue (uv handles editable installs). After Phase 6, callers who imported `from iol_client.client import _token` (we know of zero such callers) would break, but none exist (confirmed by repo-wide grep — only test files reference `_token`, and they do so via `iol_client.client._token`, not `from`-import). | none beyond standard `uv sync` after pull. |

**Nothing found in category "Stored data":** Verified — `grep -r "_token\|_refresh_token" packages/ | grep -v test_` finds only client.py / aio.py / ws_client.py source lines; no caching to disk, no database persistence. The 4 packages are all stateless across process restarts.

## Common Pitfalls

### Pitfall 1: `raising=False` monkeypatch silently breaks after the refactor

**What goes wrong:** Existing conftest fixtures use `monkeypatch.setattr(pkg.client, "_token", "test-token", raising=False)`. With `raising=False`, the call writes to the module's `__dict__` even if `_token` no longer exists as a module attribute. Production code reads `self._state.token`, the monkeypatched value lands on a dead address, and the test passes — but it's testing nothing.

**Why it happens:** `raising=False` is the documented workaround for "this attribute may not exist yet" in pytest. Combined with PEP 562 read-shim (which only fires on AttributeError), the write goes to `__dict__` and never reaches `_state`.

**How to avoid:**
1. Migrate the autouse conftest to `pkg.configure(token=..., token_expires_at=...)` BEFORE the production refactor lands in the same atomic commit.
2. Ship the 8 fixture-reaches-production guard tests (REFAC-01) FIRST and confirm they pass against the pre-refactor code (proving the test infrastructure works) and re-confirm after each per-package REFAC-02 lands.
3. Inline test-body monkeypatches (15+ sites in IOL test_client.py / test_async_client.py) must migrate concurrently in the same per-package commit.

**Warning signs:** Test passes after refactor but doesn't actually exercise `Client._ensure_token`. Coverage report shows `_ensure_token` body uncovered.

### Pitfall 2: PEP 562 `__getattr__` shadowed by stale module dict entry

**What goes wrong:** A test does `monkeypatch.setattr(iol_client.client, "_token", "X", raising=False)` BEFORE the test executes. The value `"X"` ends up in `iol_client.client.__dict__["_token"]`. The PEP 562 shim never fires for that read. Even after the test finishes and pytest restores the monkeypatch, if the module restore is incomplete (e.g., `raising=False` caused `delattr` to be a no-op), the next test inherits the dead-address state.

**Why it happens:** `monkeypatch.delattr` with `raising=False` on a never-existed attribute silently no-ops. The fix is "monkeypatch.setattr" cleanup: `monkeypatch` does track inserted attributes and removes them at teardown by default, but the edge case is fragile.

**How to avoid:** After the conftest migrates to `configure(token=...)`, no more `monkeypatch.setattr(pkg.client, "_token", ...)` in autouse. The inline test-body cases are individual rewrites; document a project convention "writes to `pkg.client._<global>` are prohibited after Phase 6; use `pkg._get_default()._state.<field>` or `pkg.configure(...)` instead."

### Pitfall 3: `_refresh_token` (IOL) is heavily monkeypatched but NOT in CONTEXT.md D-02 forwarded set

**What goes wrong:** CONTEXT.md D-02 enumerates the PEP 562 forwarded names: `_token`, `_token_ts` (iol), `_token_expires_at`, `_token_lock` (aio), and `_client`. It does NOT list `_refresh_token`. But `_refresh_token` is heavily monkeypatched in IOL test bodies (test_client.py:149, 179, 217, 245, 277, 307, 314 — 7+ sites) AND asserted in test bodies (test_client.py:170, 208, 260, 290, 311, 316 — 6+ sites).

If the shim does NOT forward `_refresh_token`, all those `assert iol_client.client._refresh_token == "..."` reads raise `AttributeError` after the refactor — even with conftest migrated.

**Why it happens:** D-02 was written from the conftest perspective, not the test-body perspective. IOL is the only package with `_refresh_token`; CONTEXT.md drafted under the (incorrect) assumption that conftest migration covers all test patching.

**How to avoid:**
1. **Recommend to planner:** add `_refresh_token` to the IOL shim's `_FORWARDED_TO_STATE` mapping (`_refresh_token` → `state.refresh_token`). This is the lowest-risk fix; D-02 is exhaustive for non-IOL packages but IOL has an extra field. Mark as an addendum to D-02.
2. **Alternative:** rewrite each `assert iol_client.client._refresh_token == X` to `assert iol_client._get_default()._state.refresh_token == X` (mechanical sed). Bigger test churn but keeps D-02 verbatim.
3. **Cannot ignore:** all 13+ IOL test sites must be addressed in Plan 3 (REFAC-02 iol-client), one way or the other.

### Pitfall 4: `_password`/`_user`/`_base_url` direct writes in tests after the refactor

**What goes wrong:** `packages/iol-client/tests/test_client.py:315` does `iol_client.client._password = "another"`. After the refactor, this assignment lands on the module dict (PEP 562 does NOT intercept `__setattr__` per D-01). Production reads `self._state.password`, the test's `_password` is dead.

Also: `packages/matriz-client/tests/test_client.py:21-22` does `monkeypatch.setattr(_client, "_user", "")` and `monkeypatch.setattr(_client, "_password", "")` — same problem.

Also: `packages/higyrus-client/tests/test_client.py:62` does `monkeypatch.setattr(higyrus_client.client, "_base_url", "")` — same problem.

Also: `packages/ambito-financiero-client/tests/test_harness_mutation_gate.py:99,110` does `monkeypatch.setattr(matriz_client.client, "_base_url", url)` — same problem.

**How to avoid:** Each of these 5+ sites needs migration to `pkg.configure(...)` or to writing on `pkg._get_default()._state.<field>` directly. The harness test (`test_harness_mutation_gate.py`) writes to matriz from an ambito test; this is brittle and needs careful migration since the mutation gate reads from `matriz_client.client._base_url` directly. Recommend the planner reviews `verification/mutation_gate.py` to see exactly how `_base_url` is consumed.

### Pitfall 5: `_session` vs `_client` naming inconsistency in matriz

**What goes wrong:** matriz uses `_session = httpx.Client(...)` instead of `_client = httpx.Client(...)`. CONTEXT.md D-02 says `_client` is forwarded for `main_higyrus.py` compat. But matriz tests reference `_client._token`, `_client._ensure_token()` (these are imports of the module, aliased) — see `packages/matriz-client/tests/test_client.py:11-12`. The `_session` global is NOT in D-02's forwarded list.

If a downstream driver (or test) reads `matriz_client.client._session`, it gets `AttributeError`. Audit shows no current test reads `_session` directly; main_matriz.py does not appear to either.

**How to avoid:** Either rename matriz's `_session` to `_client` for consistency (one mechanical edit; tests already use the module-as-`_client` alias, no conflict), OR add `_session` to matriz's shim forwarded list. Recommend the rename for consistency across the 4 packages.

### Pitfall 6: `asyncio.Lock()` created at module-level binds to no loop (current code)

**What goes wrong:** `packages/iol-client/src/iol_client/aio.py:39-40` creates `_token_lock = asyncio.Lock()` at module import time. In Python 3.10+ this works (Lock doesn't bind until first use), but it's a known footgun: if the import happens in one event loop and the lock is used in another, behavior is undefined.

**How to avoid:** In Phase 6, move the lock into `_ClientState.token_lock: asyncio.Lock | None = None` and create lazily in `AsyncClient._ensure_token()` first call. This is a tiny code change but matters because Phase 6 introduces a `Client()` instance pattern (potentially many instances), and re-creating a single module-level lock per instance would defeat per-instance isolation.

### Pitfall 7: `Client.__init__` argument collision with current `configure()` semantics

**What goes wrong:** Current `iol_client.configure(username="bob")` sets ONLY username and resets `_token` (this is intentional — credential rotation). The Phase 6 `configure()` per D-14 *replaces* `_default_client` with a new instance, which means a single-kwarg `configure(username="bob")` now needs to read base_url/password from the EXISTING default (or env). Mechanically, this means `configure()` should do:

```python
def configure(*, base_url=None, username=None, password=None, token=None, token_expires_at=None):
    global _default_client
    prior = _get_default() if _default_client is not None else None
    new = Client(
        base_url=base_url if base_url is not None else (prior._state.base_url if prior else None),
        username=username if username is not None else (prior._state.username if prior else None),
        # ... etc
        token=token,  # Always reset token (preserves v1.0 semantics)
        token_expires_at=token_expires_at,
    )
    _default_client = new
```

Or simpler: continue mutating `_default_client._state` in place from `configure()` and document the override semantics. But D-14 says "replaces", not "mutates". **OPEN QUESTION FOR PLANNER:** which exact rule does `configure()` apply for partial-kwarg calls?

### Pitfall 8: Snapshot file regenerated by accident in CI

**What goes wrong:** Operator runs `python verification/regen_snapshots.py` locally to fix a CI failure, then commits without reviewing the diff. A change to a public symbol that was unintended gets silently committed.

**How to avoid:** The PR template / commit checklist must require a 1-line description of what symbol changed and why. The snapshot file format includes a top comment (D-08 spec: "Comments al top del file declaran el snapshot version + `regen_snapshots.py` command que lo regenera") that calls out the regen command, but the human gate is via PR review.

### Pitfall 9: `inspect.signature(cls)` returns the constructor signature, not the class signature

**What goes wrong:** `inspect.signature(Client)` returns the signature of `__init__` (which is what we want for the snapshot). But `inspect.signature(SomeAbstractClass)` may raise `ValueError` if `__init__` is inherited from `object` without explicit args. The snapshot helper must handle `ValueError` gracefully.

**How to avoid:** Wrap `signature(obj)` in try/except `(TypeError, ValueError)` and return empty signature on failure. Shown in Pattern 5 example.

### Pitfall 10: `inspect.signature` does not expose `Self` return types in stringified output

**What goes wrong:** `Client.__enter__(self) -> Self` stringifies to `(self) -> typing.Self`. The text is deterministic but may surprise developers who expect just "Self". This is a cosmetic concern; the diff is stable.

**How to avoid:** Document the stringification convention in the snapshot file header. No code change needed.

## Code Examples

### Snapshot helper — enumerate per-package surface

See Pattern 5 above. Add this top-of-file comment block to each generated snapshot file:

```
# Public surface snapshot for iol-client.
# Generated by: python verification/regen_snapshots.py
# Format: <name> : <kind> : <signature>
# Sort: stable alphabetical by name.
# DO NOT EDIT BY HAND. To accept an intentional change, run the regen script
# above and commit the diff alongside the source change that justifies it.
#
```

### Inline `__repr__` redaction (per package, no `verification/` import)

```python
def __repr__(self) -> str:
    s = self._state
    pwd = "'***'" if s.password else "''"
    tok = "'***'" if s.token else "None"
    return (
        f"IOLClient(base_url={s.base_url!r}, username={s.username!r}, "
        f"password={pwd}, token={tok})"
    )
```

### `_get_default()` lazy singleton

```python
_default_client: Client | None = None


def _get_default() -> Client:
    """Lazy module-level default Client; constructed on first access.

    Mirror in aio.py with _default_async_client / AsyncClient.
    """
    global _default_client
    if _default_client is None:
        _default_client = Client()
    return _default_client
```

### Top-level shim functions

```python
def configure(**kwargs: Any) -> None:
    """Override credentials/URL/token on the default Client (D-14).

    Replaces the default Client with a fresh instance; explicit Client(...)
    instances created by the caller are NOT affected.
    """
    global _default_client
    _default_client = Client(**kwargs)


def login() -> str:
    """Authenticate the default Client (D-20)."""
    return _get_default().login()


def get_quote(simbolo: str, *, mercado: str = "bcba", plazo: str = "t2"):
    return _get_default().get_quote(simbolo, mercado=mercado, plazo=plazo)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-rolled `def __getattr__` in module via `sys.modules[__name__].__class__` hack | PEP 562 `def __getattr__(name)` at module level | Python 3.7 (PEP 562 accepted) | Standard mechanism since 2018; supported in mypy strict. [CITED: peps.python.org/pep-0562] |
| `from typing import TYPE_CHECKING` + quoted `"Client"` for self-return types | `from typing import Self` | Python 3.11 (PEP 673) | Cleaner for `__enter__`, `__aenter__`. [CITED: PEP 673] |
| Module-level `httpx.Client()` global | `httpx.Client` instance held by `_ClientState`, created lazily | Phase 6 (this phase) | Enables per-instance lifecycle; preserves v1.0 lazy construction semantic via `_get_default()`. |
| `@dataclass(frozen=True, slots=True)` for SafeModel | Same for `_ClientState` (NOT frozen — token must mutate) | Phase 6 | `slots=True` ensures no accidental attribute typos go unflagged; `frozen=False` is required for mutable token. |

**Deprecated/outdated:**
- `pytest-snapshot` and `syrupy` and `snapshottest` — REJECTED for this phase, see Alternatives Considered.
- `unittest.mock.patch` for module attributes — pytest's `monkeypatch` is the project idiom.
- Module-level `ModuleType` subclass with custom `__setattr__` — REJECTED by D-01.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The test count "277" exists pre-refactor; no test is currently skipped/xfail that would flip after the refactor. | Summary, Per-Package Divergence | Verified — `uv run pytest --collect-only` returns 277/278 collected (1 deselected). [VERIFIED: collect-only run] |
| A2 | `inspect.signature` on a `@dataclass(slots=True)` class returns `__init__` signature including the autogenerated args. | Standard Stack, Pattern 5 | Risk: snapshot might show `*, base_url, username, password, ...` with default values inlined. Diff stability assumed by D-08. [ASSUMED — verify by running `inspect.signature(Client)` after class is built] |
| A3 | `monkeypatch.setattr` to a PEP-562-shimmed module writes to the module `__dict__` and shadows the shim. | Pattern 1, Pitfall 2, Pitfall 4 | If this is wrong, the inline test-body monkeypatches won't shadow and behavior is different. Empirically correct (PEP 562 only intercepts on AttributeError) but worth a 1-line unit test in Plan 1. [ASSUMED — easy to verify with a tiny test module] |
| A4 | matriz's success criterion 3 "los 4 paquetes exponen `Client` y `AsyncClient`" applies to matriz despite no `aio.py` existing today. | Per-Package Divergence, Open Questions | Risk: if matriz is exempt, Plan 5 ships only sync `Client`; if not exempt, Plan 5 must also create a stub `AsyncClient` (with `aio.py`, no REST methods, just lifecycle) that Phase 10 fleshes out. [ASSUMED — see Open Questions #1] |
| A5 | Adding `_refresh_token` to the IOL shim forwarded set (Pitfall #3 mitigation) does not violate CONTEXT.md "Decisions Locked". | Pitfall #3, Conftest Migration | D-02 enumeration is explicit but does not say "only these"; treating it as additive is a reasonable interpretation but the user should confirm. Risk if user disagrees: tests in IOL test_client.py break and must be rewritten to `_get_default()._state.refresh_token`. [ASSUMED — needs user confirmation in discuss-phase or planner decision] |
| A6 | `configure()` should accept all current kwargs PLUS `token` / `token_expires_at` (and, per Pitfall #3 mitigation, possibly `refresh_token` for iol). | Conftest Migration Pattern, Pitfall #7 | D-13 lists exact kwarg sets; the planner must respect D-13 unless user revises. [VERIFIED against D-13] |
| A7 | `httpx.Client.event_hooks` mutation through the shim's forwarded `_client` (per D-02 exception) works because the shim returns the underlying `httpx.Client` object and mutation is in-place on its `event_hooks` dict. | D-02 / D-21, Pattern 1 | Mechanically correct; `dict.update()` and `dict[key] = value` on the returned object's `event_hooks` mutates the live instance. [VERIFIED: standard Python semantics] |
| A8 | The 8 fixture-reaches-production guard tests can be run BEFORE the production refactor lands (they will pass against current code) AND will catch any per-package regression as REFAC-02 lands. | REFAC-01 plan ordering | The guard tests use `pkg.configure(token=...)` — which currently doesn't accept `token=` kwarg. So either (a) D-04's `configure(token=...)` extension is added in REFAC-01 first (couples REFAC-01 with a tiny `configure()` extension in each package's existing client.py), or (b) the guard tests start as `monkeypatch.setattr(pkg.client, "_token", ...)` (current pattern) and are MIGRATED to `configure(token=...)` as each REFAC-02 plan lands. **Recommend (b)** — REFAC-01 is tests-only, no production code changes. [ASSUMED — see Open Questions #2] |

**Empty? No — 4 assumptions explicitly need user/planner confirmation before execution: A2, A4, A5, A8.**

## Open Questions

1. **Matriz `AsyncClient` scope in Phase 6.**
   - What we know: CONTEXT.md success criterion 3 says "Los 4 paquetes exponen `Client` (sync) y `AsyncClient` (async)". Matriz has no `aio.py` today. ROADMAP Phase 10 (REFAC-04) creates matriz `aio.py` with the full REST async surface. CONTEXT.md `<deferred>` says "matriz `aio.py` — Phase 10".
   - What's unclear: does Phase 6 ship a stub `AsyncClient` for matriz (just `__init__`, `__aenter__`/`__aexit__`, `aclose()` — no REST methods)? Or is matriz exempt from `AsyncClient` and the success criterion really means "los 3 paquetes con `aio.py` exponen `AsyncClient`"?
   - Recommendation: ship the **stub** `AsyncClient` in `packages/matriz-client/src/matriz_client/aio.py` as a new file containing only `class AsyncClient` (no module-level `_default_async_client`, no top-level `configure`/`get_X` functions). Phase 10 grows it. This satisfies the success criterion's literal text while staying compatible with Phase 10's scope. Open for user to confirm in discuss-phase if needed.

2. **REFAC-01 conftest pattern for the guard tests.**
   - What we know: D-04 says conftest migrates to `configure(token=..., token_expires_at=...)`. REFAC-01 is tests-only (D-05 says Plan 1 doesn't touch production code).
   - What's unclear: if REFAC-01 is tests-only but Plan 1's 8 guard tests rely on `configure(token=...)` (which doesn't exist yet), then Plan 1 must EITHER (a) add the `configure(token=...)` extension to each package's existing `client.py`/`aio.py` (a 3-line addition that doesn't break v1.0 semantics) — making Plan 1 NOT pure tests-only; OR (b) Plan 1's guards use the legacy `monkeypatch.setattr(pkg.client, "_token", ...)` pattern initially and migrate inline when each REFAC-02 lands.
   - Recommendation: (a) — extend `configure(...)` with `token=` and `token_expires_at=` (and `refresh_token=` for iol) in Plan 1 as a 3-line addition per package's existing `client.py` and `aio.py`. This is non-breaking (current callers don't pass these kwargs) and lets Plan 1's guards use the eventual pattern from the start.

3. **`_refresh_token` shim forwarding for IOL.**
   - What we know: 13+ test sites in iol-client read or write `_refresh_token` directly; D-02 does not list `_refresh_token` in the forwarded set.
   - What's unclear: should the planner add `_refresh_token` to the IOL shim's forwarded set as an addendum to D-02? Or rewrite the 13 test sites?
   - Recommendation: extend the IOL shim's `_FORWARDED_TO_STATE` to include `_refresh_token` → `state.refresh_token`. Treat as additive to D-02 (D-02 enumerated common cases; IOL has one extra field). Surface this decision in the planner output so the user sees and confirms.

4. **`_base_url` write in `test_harness_mutation_gate.py` (ambito tests writing to matriz module).**
   - What we know: `packages/ambito-financiero-client/tests/test_harness_mutation_gate.py:99,110` does `monkeypatch.setattr(matriz_client.client, "_base_url", url)` from an AMBITO test file. The harness `verification/mutation_gate.py` reads `matriz_client.client._base_url` to check whether mutations are gated to the remarkets sandbox.
   - What's unclear: D-02 explicitly says `_base_url` is NOT forwarded by the shim. After matriz Plan 5 lands, this test will fail because the monkeypatch lands on a dead address AND the shim does NOT forward `_base_url`. The mutation gate logic itself reads via getattr through the shim, so `verification/mutation_gate.py` may need to be updated to call `matriz_client._get_default()._state.base_url` instead.
   - Recommendation: Plan 5 (matriz REFAC-02) must also update `verification/mutation_gate.py` to use `matriz_client._get_default()._state.base_url`, and update `test_harness_mutation_gate.py:99,110` to use `matriz_client.configure(base_url=url)`. This is a tightly-coupled trio of changes.

5. **`configure()` partial-kwarg semantics post-refactor.**
   - What we know: D-14 says `configure(**kwargs)` REPLACES the default. Current v1.0 `configure(username="bob")` mutates ONLY username (preserves base_url, resets token).
   - What's unclear: if D-14 means "replace with new instance built from kwargs", a single-kwarg `configure(username="bob")` would lose base_url (the new instance reads env defaults instead). Is that intentional, or should `configure()` carry forward unset fields from the prior default?
   - Recommendation: carry forward unset fields from the prior default Client's `_state`, then reset token. This preserves v1.0 semantics literally. The planner can document this in `Client.__init__` docstring.

## Environment Availability

> Phase 6 has no external dependencies — only repo-internal code/test changes plus the dev dependencies already present.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All packages | ✓ | 3.12.11 [VERIFIED: CLAUDE.md] | — |
| uv | dev workflow | ✓ | 0.9.0 [VERIFIED: CLAUDE.md] | — |
| pytest | tests | ✓ | >=8.3 [VERIFIED: dev-dependencies] | — |
| pytest-httpx | guard tests | ✓ | >=0.34 [VERIFIED: dev-dependencies] | — |
| pytest-asyncio | async guard tests | ✓ | >=0.24 [VERIFIED: dev-dependencies] | — |
| ruff | format/lint | ✓ | >=0.7 [VERIFIED] | — |
| mypy | strict typecheck | ✓ | >=1.13 [VERIFIED] | — |
| httpx | runtime | ✓ | >=0.27 [VERIFIED] | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.3 + pytest-asyncio >=0.24 + pytest-httpx >=0.34 + pytest-cov >=6.0 [VERIFIED: pyproject.toml] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `asyncio_mode = "auto"`, `--strict-markers`, `--import-mode=importlib`, `pythonpath = ["."]`, `testpaths = ["packages", "tests"]` |
| Quick run command | `uv run pytest packages/<pkg>/ verification/test_public_surface.py -x` |
| Full suite command | `uv run pytest -ra` (covers `packages/` + `tests/`, sweeps 277 tests + new) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REFAC-01 | Public surface of every package matches a committed snapshot | snapshot | `uv run pytest verification/test_public_surface.py -x` | ❌ Wave 0 (4 snapshot files + test file + regen script) |
| REFAC-01 | Sentinel monkeypatched/configured token reaches outgoing wire request `Authorization` (iol/higyrus) / `X-Auth-Token` (matriz) / `base_url` reaches URL (ambito), sync surface | unit (guard) | `uv run pytest packages/<pkg>/tests/test_fixture_reaches_production.py -x` | ❌ Wave 0 (4 new test files, 1 per pkg) |
| REFAC-01 | Same, async surface | unit (guard) | same command | ❌ Wave 0 (4 new test files) |
| REFAC-02 (per pkg) | `pkg.Client` exists, has `close`, `__enter__`, `__exit__`, `__repr__` redacts, `__reduce__` raises | unit | `uv run pytest packages/<pkg>/tests/test_client_class_skeleton.py -x` | ❌ Wave 0 per package |
| REFAC-02 (per pkg) | `pkg.AsyncClient` exists, has `aclose`, `__aenter__`, `__aexit__` (matriz: stub, see Open Q #1) | unit | same | ❌ Wave 0 per package |
| REFAC-02 (per pkg) | `pkg.configure(token=..., token_expires_at=...)` updates default's state and is picked up by next `pkg.get_X` | unit | same | ❌ Wave 0 per package |
| REFAC-02 (per pkg) | Explicit `pkg.Client(username="alice")` is NOT affected by `pkg.configure(username="bob")` (Pitfall #2 mitigation from PITFALLS.md) | unit | same | ❌ Wave 0 per package |
| REFAC-02 (per pkg) | PEP 562 shim — `pkg.client._token` read returns `_get_default()._state.token`; reads of non-forwarded names raise `AttributeError` | unit | same | ❌ Wave 0 per package |
| REFAC-02 (per pkg) | `pkg.Client.__reduce__()` raises `TypeError`; `copy.deepcopy(c)` raises | unit | same | ❌ Wave 0 per package |
| REFAC-02 (per pkg) | Snapshot of pkg updated to include new public symbols (`Client`, `AsyncClient`, etc.); old symbols preserved | snapshot | `uv run pytest verification/test_public_surface.py::test_public_surface_matches_snapshot[<pkg>] -x` | ❌ Wave 0 (snapshots regenerated per plan) |
| REFAC-02 (regression) | 277 baseline tests still pass | regression | `uv run pytest -ra` | ✓ exists (the baseline) |

### Sampling Rate
- **Per task commit:** `uv run pytest packages/<pkg>/ verification/test_public_surface.py -x` (quick path, ~30 s)
- **Per wave merge:** `uv run pytest -ra` (full sweep including driver/harness tests)
- **Phase gate:** Full suite green + `ruff check . && ruff format --check . && mypy packages/<pkg>/src` before `/gsd-verify-work`. Re-run on Python 3.12 AND 3.13 (CI matrix) — already automatic in GitHub Actions.

### Wave 0 Gaps
- [ ] `verification/test_public_surface.py` — new test file (covers REFAC-01)
- [ ] `verification/snapshots/ambito-financiero-client-surface.txt` — baseline snapshot for ambito
- [ ] `verification/snapshots/iol-client-surface.txt` — baseline snapshot for iol
- [ ] `verification/snapshots/higyrus-client-surface.txt` — baseline snapshot for higyrus
- [ ] `verification/snapshots/matriz-client-surface.txt` — baseline snapshot for matriz
- [ ] `verification/regen_snapshots.py` — new operator script
- [ ] `packages/ambito-financiero-client/tests/test_fixture_reaches_production.py` — new
- [ ] `packages/iol-client/tests/test_fixture_reaches_production.py` — new
- [ ] `packages/higyrus-client/tests/test_fixture_reaches_production.py` — new
- [ ] `packages/matriz-client/tests/test_fixture_reaches_production.py` — new
- [ ] `packages/<pkg>/tests/test_client_class_skeleton.py` (× 4 packages, NEW; alternatively interleave into existing `test_client.py` / `test_async_client.py` — operator decision per plan)
- [ ] Framework install: none — all already in dev deps.

## Security Domain

### Applicable ASVS Categories (Level 1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Existing — IOL OAuth password grant + refresh token; Higyrus Bearer; Matriz Bearer in `X-Auth-Token`. Phase 6 does NOT change auth flows; it relocates state from module globals to instance `_state.token`. The threat model is unchanged. |
| V3 Session Management | yes | Token lifecycle: lazy login, cache, TTL-based refresh (IOL: 900 s with 60 s buffer, refresh_token fallback; Higyrus/Matriz: 23 h TTL). After Phase 6, lifecycle lives on `_ClientState.token` + `token_expires_at` (and `refresh_token` for IOL). No persistence to disk. Caller-owned instance lifecycle — Phase 6 makes this explicit. |
| V4 Access Control | no | Access control is enforced server-side. The client just forwards credentials. |
| V5 Input Validation | partially | Existing — wire validation via `SafeModel.from_api`, `_unwrap_envelope` (matriz). Phase 6 doesn't change validation; the new `Client.__init__` does NO validation of credentials (lazy per D-17). |
| V6 Cryptography | no | httpx provides TLS; no app-level crypto. |
| V8 Data Protection | yes | **Phase 6 specific:** `Client.__repr__` (D-18) MUST redact password and token. The inline redaction pattern (`'***' if value else ''`) replaces what `verification/redaction.py` would do — but the latter is not importable from the published wheels. Audit each of the 4 packages to confirm `__repr__` redacts. Test it. |
| V9 Communications | yes | TLS via httpx default — unchanged. Phase 6 does not add new network calls. |
| V14 Configuration | yes | `.env` files are gitignored and project-specific (CLAUDE.md constraint). `Client(password="...")` constructor accepts password as a kwarg — callers must avoid putting secrets in shell history. Document in `__init__` docstring. |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Token leak via `print(client)` / `repr(client)` | Information Disclosure | `Client.__repr__` redacts (D-18); add a regression unit test per package: `assert "real-token" not in repr(Client(token="real-token"))` |
| Token leak via `pickle.dumps(client)` and inspection of pickle bytes | Information Disclosure | `Client.__reduce__` raises (D-23). Add a regression test per package. |
| Token leak via `copy.deepcopy(client)` (memo may end up logged) | Information Disclosure | `Client.__deepcopy__` raises (D-23). Add a regression test per package. |
| Credential leak via `Client.__init__(password="...")` showing up in traceback args | Information Disclosure | `__init__` doesn't store password as a positional arg attribute; password lives in `_state.password`. `slots=True` prevents accidentally adding it elsewhere. |
| Cross-instance token leak via shared `_ClientState` | Information Disclosure | Each `Client()` instance owns its own `_state`. Document and unit-test the per-instance independence (which is Pitfall #2 from PITFALLS.md). |
| Snapshot test inadvertently logging credentials | Information Disclosure | Snapshot enumerates `__all__` only — credentials are not in `__all__` (`_state` is private). Snapshot file should NOT contain any token or password. Manually inspect the first generated snapshots. |

## Sources

### Primary (HIGH confidence)
- Python `inspect` module docs (`docs.python.org/3/library/inspect.html`) — `signature()`, `getmembers()`, `isclass()`, `isfunction()`, `iscoroutinefunction()`.
- PEP 562 — Module `__getattr__` and `__dir__` (peps.python.org/pep-0562/) — read-only module attribute customization since Python 3.7.
- PEP 726 — Module `__setattr__` and `__delattr__` (peps.python.org/pep-0726/) — NOT accepted; confirms why D-01 chose read-only shim only.
- PEP 673 — `Self` type — for `__enter__`/`__aenter__` return types in Python 3.11+.
- Existing codebase (read in full):
  - `packages/iol-client/src/iol_client/client.py` (260 LOC) — module-level singletons, OAuth refresh_token flow, `_TOKEN_TTL_BUFFER_SECONDS=60`, `_token_expires_at` field.
  - `packages/iol-client/src/iol_client/aio.py` (264 LOC) — async mirror with `_token_lock`, `_client_lock`, double-checked locking pattern.
  - `packages/higyrus-client/src/higyrus_client/client.py` (398 LOC) — Bearer token, `_token_ts` + `_TOKEN_TTL_SECONDS = 23 * 60 * 60`, structured `_raise_for_response` with errors/timestamp parsing.
  - `packages/matriz-client/src/matriz_client/client.py` (496 LOC) — `_session` named (not `_client`), `X-Auth-Token` header, `_unwrap` envelope helper, `_TOKEN_TTL = 23 * 60 * 60`, `_risk_auth()` HTTP Basic Auth fallback.
  - `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` (89 LOC) — no auth, `_user_agent` global.
  - All 4 `__init__.py` files — current `__all__` exports.
  - All 4 `conftest.py` files — current autouse fixture patterns.
  - `packages/iol-client/tests/test_client.py` and `test_async_client.py` — 15+ inline `monkeypatch.setattr` sites; multiple direct `client._password = ...` mutations.
  - `packages/matriz-client/tests/test_client.py` — `monkeypatch.setattr(_client, "_user", "")` and `_password`, `_token`, `_ensure_token`, `login` patches.
  - `packages/matriz-client/src/matriz_client/ws_client.py` — reads `_rest._base_url`, `_rest._token`, calls `_rest._ensure_token()` (relevant to Open Q #4 / matriz shim scope).
  - `packages/ambito-financiero-client/tests/test_harness_mutation_gate.py` — writes to `matriz_client.client._base_url` from ambito tests (Open Q #4).
- Pre-existing v1.1 research artifacts:
  - `.planning/research/SUMMARY.md` — confirms 5-module pattern recommendation (`_state.py`, `_core.py`, `_transport.py`, `_atransport.py`, `_logging.py`); Phase 6 ships `_state.py` only.
  - `.planning/research/PITFALLS.md` Pitfalls #1, #2, #3, #11, #12, #18 — directly inform Phase 6 mitigations.
  - `.planning/research/ARCHITECTURE.md` — diagrammed the target architecture; Phase 6 ships the Client + shim subset.
  - `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/TESTING.md`, `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/CONCERNS.md`.
- `pyproject.toml` (root) — confirms dev deps, ruff/mypy/pytest config.
- `verification/redaction.py` — confirms redaction philosophy; NOT importable from published wheels (the inline `__repr__` pattern must duplicate the core idea).

### Secondary (MEDIUM confidence)
- WebSearch — PEP 562 patterns, snapshot testing libraries (used to confirm `syrupy`/`pytest-snapshot`/`snapshottest` exist as alternatives, all rejected per D-08).
- WebSearch — `inspect.signature` and golden file testing patterns.

### Tertiary (LOW confidence)
- None — all Phase 6 decisions are backed by either CONTEXT.md, codebase grep, or Python standard library docs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dependency is already installed and used in the codebase.
- Architecture: HIGH — PEP 562 + lazy default singleton is a documented pattern; `@dataclass(slots=True)` is the project idiom.
- Pitfalls: HIGH — pitfalls are mostly drawn from `.planning/research/PITFALLS.md` (HIGH confidence per its own metadata) plus 4 newly surfaced from this phase's codebase audit (Pitfalls #3, #4, #5, #6 in this doc).
- Per-package divergence: HIGH — every divergence is verified against current code with line numbers.
- Open questions: HIGH — questions are precisely articulated with recommended resolutions; planner can adopt the recommendations or push back individually.

**Research date:** 2026-06-10
**Valid until:** 2026-07-10 (30 days; the underlying httpx/pytest stack is stable; no library version drift expected).
