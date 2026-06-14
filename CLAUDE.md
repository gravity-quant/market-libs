<!-- GSD:project-start source:PROJECT.md -->
## Project

**market-libs — Verificación en vivo de clientes**

Ciclo de verificación exhaustiva de las librerías cliente del monorepo `market-libs`.
El objetivo es ejercitar la API pública completa de cada cliente verificable —en sus
superficies **sync** (`client.py`) y **async** (`aio.py`)— contra las **APIs financieras
en vivo**, detectar bugs y discrepancias entre el comportamiento del cliente y lo que
devuelve el servicio real, y corregirlos en el mismo ciclo. El vehículo de verificación
son los scripts `main_*.py` de la raíz, hoy mínimos, que se extienden para cubrir toda
la superficie de cada paquete.

Alcance: 4 de los 5 paquetes — `iol-client`, `higyrus-client`, `matriz-client` y
`ambito-financiero-client`.

**Core Value:** Confianza de que cada cliente refleja fielmente el comportamiento real de su API: cada
divergencia entre el cliente y el servicio en vivo debe ser detectada, documentada y
corregida.

### Constraints

- **Tech stack**: Python 3.12+, uv, httpx (sync+async), pytest+pytest-httpx, ruff, mypy strict — toda extensión y fix debe respetar el stack y pasar el CI existente.
- **Arquitectura**: estado singleton a nivel de módulo; sin código compartido entre paquetes (por diseño). Los fixes se aplican dentro de cada paquete, sin introducir dependencias cruzadas.
- **Dual sync/async**: cualquier fix de lógica debe espejarse en `client.py` y `aio.py` del mismo paquete (deuda conocida: la lógica está duplicada).
- **Seguridad**: las credenciales viven en `.env` por paquete; nunca commitear `.env` ni exponer credenciales en logs, reportes o tests.
- **Dependencias externas en vivo**: la verificación depende de la disponibilidad y el estado real de servicios de terceros; resultados pueden variar por horario de mercado, datos disponibles o rate limits.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12+ — all source code across all packages
- None
## Runtime
- CPython 3.12.11 (active venv at `.venv/`, managed by uv)
- Python 3.13 also supported (tested in CI matrix)
- uv 0.9.0
- Lockfile: `uv.lock` (present, 758 lines, committed to repo)
## Frameworks
- httpx >=0.27 — sync (`httpx.Client`) and async (`httpx.AsyncClient`) HTTP for all five packages
- websocket-client >=1.8.0 — used exclusively in `packages/matriz-client/` for MATBA ROFEX Primary API streaming; runs event loop in a background daemon thread
- pytest >=8.3 — test runner, configured in root `pyproject.toml`
- pytest-asyncio >=0.24 — async test support (`asyncio_mode = "auto"`)
- pytest-httpx >=0.34 — HTTP request mocking for httpx clients
- pytest-cov >=6.0 — coverage reporting
- hatchling — build backend for each package (wheel + sdist)
- uv build — invoked by CI release workflow
## Key Dependencies
- `httpx >=0.27` — the sole HTTP transport for all packages; sync and async variants used side by side
- `python-dotenv >=1.0` — loads `.env` files at module import time via `load_dotenv()` in every client module
- `websocket-client >=1.8.0` — only `matriz-client` uses this; required for WebSocket streaming
- `ruff >=0.7` — linter and formatter (replaces black + isort + flake8)
- `mypy >=1.13` — strict type checking (`strict = true` in root config)
- `pre-commit >=4.0` — git hooks running ruff and mypy
## Configuration
- Each package reads credentials from environment variables via `python-dotenv`
- `.env.example` files are present in each package directory as templates
- No `.env` file at monorepo root; per-package `.env` files exist in `packages/higyrus-client/` and `packages/matriz-client/`
- All packages expose a `configure()` function for runtime overrides without restarting the process
- Root `pyproject.toml`: workspace definition, dev dependencies, ruff config, mypy config, pytest config, coverage config
- Per-package `pyproject.toml`: package metadata, runtime dependencies, build system (hatchling)
- Ruff config: `line-length = 100`, `target-version = "py312"`, double quotes, space indentation
- Mypy config: `strict = true`, `python_version = "3.12"`, `explicit_package_bases = true`
- Pytest config: `asyncio_mode = "auto"`, `--import-mode=importlib`, `--strict-markers`
- Pre-commit config: `.pre-commit-config.yaml` — trailing whitespace, YAML/TOML checks, ruff, mypy
## Workspace Structure
- `packages/iol-client/` — `iol-client` v0.1.1 (Invertir Online, HTTP sync+async)
- `packages/higyrus-client/` — `higyrus-client` v0.1.1 (Higyrus financial ops, HTTP sync+async)
- `packages/ambito-financiero-client/` — `ambito-financiero-client` v0.1.1 (Ámbito Financiero, HTTP sync+async, no auth)
- `packages/wallets-client/` — `wallets-client` v0.1.0 (Wallets, HTTP sync+async, static Bearer token)
- `packages/matriz-client/` — `matriz-client` v0.1.1 (MATBA ROFEX Primary API, HTTP REST + WebSocket)
## Platform Requirements
- uv 0.9.0+
- Python 3.12 or 3.13
- `uv sync --all-packages --all-extras --dev --frozen` to install workspace
- Packages are distributed as standalone wheels (no shared internal dependencies between packages)
- No deployment target — these are client libraries consumed by other projects
## CI/CD
- Triggers on push/PR to `main` (ignores `.md` and `.gitignore` changes)
- Jobs: lint (ruff check + format), pre-commit hooks, typecheck (mypy), tests
- Test matrix: 5 packages × 2 Python versions (3.12, 3.13)
- Uses `astral-sh/setup-uv@v3` with cache enabled
- Triggers on tags matching `*-client-v*` pattern (e.g., `iol-client-v0.1.1`)
- Validates tag version matches `pyproject.toml` version
- Builds wheel + sdist with `uv build --package <package>`
- Creates GitHub Release with auto-generated notes and attaches artifacts
- Does NOT publish to PyPI
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Source modules: `snake_case.py` (e.g., `client.py`, `aio.py`, `exceptions.py`, `models.py`)
- Private/internal modules: leading underscore `_snake_case.py` (e.g., `_params.py`, `_parsing.py`)
- Test files: `test_<subject>.py` (e.g., `test_client.py`, `test_async_client.py`, `test_models.py`)
- Shared fixtures: `conftest.py` per package
- Public API functions: `snake_case` matching the domain language, often `get_<resource>` (e.g., `get_quote`, `get_listado_cuentas`, `get_movimientos`)
- Private internal helpers: `_snake_case` prefix (e.g., `_request`, `_ensure_token`, `_raise_for_response`, `_get`)
- Async counterparts: same name as sync, located in the `aio` submodule (not prefixed with `async_`)
- Module-level state: `_snake_case` with leading underscore (e.g., `_base_url`, `_token`, `_token_ts`, `_client`)
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `DEFAULT_BASE_URL`, `_REQUEST_TIMEOUT`, `_TOKEN_TTL_SECONDS`)
- Local variables: `snake_case`
- Exception classes: `<Client>Error` base, `<Client>APIError`, `<Client>AuthError`, `<Client>RateLimitError` (e.g., `IOLClientError`, `HigyrusAPIError`, `HigyrusAuthorizationError`)
- Model dataclasses: `PascalCase` matching wire/domain names (e.g., `Cuenta`, `Movimiento`, `PosicionValuada`, `MarketDataSnapshot`)
- `Literal` type aliases: `PascalCase` (e.g., `InstrumentType`, `Side`, `OrderType`, `MarketId`)
- Fields inside dataclasses follow the **wire format verbatim** — camelCase from the JSON API (e.g., `idCuenta`, `fechaDesde`, `tipoTitulo`, `marketSegmentId`)
- Python-facing function parameters use `snake_case` for those same concepts (e.g., `id_cuenta`, `fecha_desde`, `tipo_titulo`)
## Code Style
- Tool: Ruff formatter (v0.7+)
- Line length: 100 characters
- Quote style: double quotes
- Indent: 4 spaces
- Tool: Ruff linter with rule sets: E, W (pycodestyle), F (pyflakes), I (isort), B (flake8-bugbear), UP (pyupgrade), SIM (flake8-simplify), RUF, ASYNC, PIE, PT (pytest-style), RET (return), TID (tidy-imports)
- E501 (line-too-long) is ignored — formatter handles it
- S101 (assert use) is ignored only inside `**/tests/**`
- Type checking: mypy in strict mode (`strict = true`, `disallow_untyped_defs = true`, `warn_return_any = true`)
- Every module starts with `from __future__ import annotations` — this is mandatory and applied uniformly
## Import Organization
- No wildcard imports
- No relative imports (enforced by TID)
- `load_dotenv()` called at module level immediately after imports in client modules
## Module Structure Pattern
## Error Handling
## Logging
## Comments
- Every module has a module-level docstring describing: purpose, API usage examples (as `::` code blocks), environment variables, and any auth flow specifics
- Example pattern:
- Public functions: one-line summary + endpoint path in backtick-rst format (e.g., `Endpoint: ``GET /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion````)
- Private functions: one-line summary, no endpoint detail needed
- Inline comments: used sparingly for non-obvious decisions
- Section dividers with `# ---...---` separating logical blocks (auth, internals, endpoint groups) within large modules
## Function Design
- Positional arguments for required domain identifiers (e.g., `simbolo`, `id_cuenta`, `fecha_desde`)
- Keyword-only arguments (`*`) for optional/defaulted params (e.g., `mercado: str = "bcba"`, `plazo: str = "t2"`)
- `None` as default for truly optional API params, then dropped via `drop_none()`
- Typed with concrete types, never raw `httpx.Response` (except in internal `_request` helpers)
- Model dataclasses for structured responses, `dict[str, Any]` or `list[dict[str, Any]]` for unstructured/pass-through payloads
- `list[Model]` for collections, with `if raw is None: return []` guard for 204 responses
## Module-Level State Pattern
## Model Design (SafeModel / dataclasses)
- Models are `@dataclass(frozen=True, slots=True)` — immutable and memory-efficient
- Inherit from `SafeModel` base class
- Constructed exclusively via `Model.from_api(payload: Any)` classmethod — never `Model(field=value)` directly
- `from_api` tolerates `None`, non-dict, or partial payloads, substituting safe defaults: `str → ""`, `int → 0`, `float → 0.0`, `bool → False`, `list[X] → []`, nested `SafeModel → X.from_api(None)`
- Wire field names are camelCase verbatim (matching JSON keys)
- `Optional[T]` / `T | None` fields default to `None` (explicit opt-in to nullable)
- An `empty()` classmethod is available for tests and defaults
## Exports
- Explicit `__all__` list with all public names
- `__version__` string (e.g., `"0.1.1"`)
- Re-exports from `client`, `exceptions`, `models` submodules
- `aio` submodule is importable as `from <pkg> import aio` but not re-exported into the flat namespace
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## System Overview
```text
```
## Component Responsibilities
| Component | Responsibility | Key Files |
|-----------|----------------|-----------|
| `ambito_financiero_client` | Public FX rate scraping (no auth) | `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` |
| `higyrus_client` | Brokerage back-office (accounts, positions, movements) | `packages/higyrus-client/src/higyrus_client/client.py` |
| `iol_client` | IOL trading platform (quotes, instruments, OAuth) | `packages/iol-client/src/iol_client/client.py` |
| `matriz_client` | MATBA ROFEX Primary API (orders, market data, WS streaming) | `packages/matriz-client/src/matriz_client/client.py` |
| `wallets_client` | Internal wallets service (Bearer token, stub) | `packages/wallets-client/src/wallets_client/client.py` |
| `<pkg>.aio` | Async counterpart for ambito, higyrus, iol, wallets clients | `*/src/*/aio.py` |
| `matriz_client.ws_client` | WebSocket streaming (market data + execution reports) | `packages/matriz-client/src/matriz_client/ws_client.py` |
| `<pkg>.models` | Frozen safe-access dataclasses for API responses | `higyrus_client/models.py`, `matriz_client/models.py` |
| `<pkg>.exceptions` | Package-scoped exception hierarchy | `*/src/*/exceptions.py` |
| `<pkg>._params` / `<pkg>._parsing` | Internal serialization helpers | `higyrus_client/_params.py`, `ambito_financiero_client/_parsing.py` |
## Pattern Overview
- No class instances required by the caller; import the package and call functions directly
- Dual sync/async surface: `import pkg` (sync) and `from pkg import aio` (async) with independent state
- Lazy authentication: the token is obtained on the first API call, cached, and refreshed before expiry; callers may call `login()` eagerly but it is not required
- No shared code between packages; each package is self-contained with its own copy of auth and HTTP logic
- `configure()` is the runtime override point for credentials and base URL in all packages
## Layers
- Purpose: Re-exports all public symbols from `client.py`, `aio.py`, `models.py`, `exceptions.py`, `types.py`; defines `__version__`
- Location: `packages/<name>/src/<pkg>/__init__.py`
- Contains: `__all__` list, version string, star-import re-exports
- Depends on: client, aio, models, exceptions, types modules within the same package
- Used by: callers — application code, notebooks, tests
- Purpose: Module-level state, auth flow, HTTP dispatch, domain function implementations
- Location: `packages/<name>/src/<pkg>/client.py`
- Contains: `_base_url`, `_token`, `_client` (httpx.Client) globals; `configure()`, `login()`, `_ensure_token()`, `_request()`, public domain functions
- Depends on: `httpx`, `python-dotenv`, exceptions module, models (where present), params/parsing helpers
- Used by: `__init__.py`, `aio.py` (for shared types like `InstrumentType` in iol)
- Purpose: Async mirror of `client.py` with independent module-level state and asyncio locks
- Location: `packages/<name>/src/<pkg>/aio.py` (present in ambito, higyrus, iol, wallets; absent in matriz)
- Contains: Same globals as sync but typed as `httpx.AsyncClient | None`; `asyncio.Lock()` for token and client; `aclose()` coroutine
- Depends on: same deps as `client.py`; imports shared types from `client.py` (e.g., `InstrumentType`)
- Used by: `__init__.py`
- Purpose: Typed, frozen, safe-access dataclasses for deserializing API payloads
- Location: `packages/higyrus-client/src/higyrus_client/models.py`, `packages/matriz-client/src/matriz_client/models.py`
- Contains: `SafeModel` base class (higyrus); frozen `@dataclass` classes with `from_api(payload)` classmethods
- Depends on: `types.py` (matriz), stdlib dataclasses/typing
- Used by: `client.py`, `aio.py`, `__init__.py`
- Purpose: `Literal` type aliases for enum-like API parameters
- Location: `packages/matriz-client/src/matriz_client/types.py`
- Contains: `Side`, `OrderType`, `TimeInForce`, `MarketId`, `SegmentId`, `CFICode`, etc.
- Depends on: stdlib `typing` only
- Used by: `models.py`, `client.py`, `ws_client.py`, `__init__.py`
- Purpose: Private serialization utilities that should not be imported by callers
- Location: `packages/higyrus-client/src/higyrus_client/_params.py`, `packages/ambito-financiero-client/src/ambito_financiero_client/_parsing.py`
- Contains: `format_date()`, `format_bool()`, `drop_none()` (higyrus); `parse_ar_decimal()` (ambito)
- Depends on: stdlib only
- Used by: `client.py` and `aio.py` within the same package
- Purpose: Package-scoped exception hierarchy
- Location: `packages/<name>/src/<pkg>/exceptions.py`
- Contains: Base `<Pkg>ClientError(Exception)` → `<Pkg>APIError` → `<Pkg>AuthError`, `<Pkg>RateLimitError`
- Depends on: stdlib only
- Used by: `client.py`, `aio.py`, `__init__.py`
- Purpose: Real-time streaming over WebSocket (market data + execution reports + WS order entry); uses background daemon thread
- Location: `packages/matriz-client/src/matriz_client/ws_client.py`
- Contains: `ws_connect()`, `ws_disconnect()`, `ws_subscribe_market_data()`, `ws_subscribe_order_reports()`, `ws_new_order()`, `ws_cancel_order()`
- Depends on: `websocket-client` library, `matriz_client.client` (for token), `matriz_client.models`
- Used by: `__init__.py`
## Data Flow
### Primary Request Path (sync)
### Primary Request Path (async)
### WebSocket Streaming Path (matriz only)
- Each package defines its own `_TOKEN_TTL_*` constant (IOL: 900s with 60s buffer; Higyrus/Matriz: 23h)
- Sync clients: checked synchronously in `_ensure_token()` using `time.time()`
- Async clients: double-checked locking pattern inside `asyncio.Lock()` to prevent thundering herd
## Key Abstractions
- Purpose: Holds credentials, cached token, and a persistent HTTP client per package; eliminates the need for the caller to manage objects
- Examples: `_token`, `_base_url`, `_client` in every `client.py` and `aio.py`
- Pattern: `global` statement to mutate; `configure()` as the controlled mutation entry point
- Purpose: Tolerant deserialization — absent or wrong-type fields fall back to typed zero-values instead of raising
- Examples: `packages/higyrus-client/src/higyrus_client/models.py:30`, `packages/matriz-client/src/matriz_client/models.py`
- Pattern: `@dataclass(frozen=True)` + `from_api(cls, payload: Any) -> Self` classmethod using `get_type_hints()` introspection
- Purpose: Replaces env-var credentials and resets cached token without restarting the process; used heavily in tests via `monkeypatch`
- Examples: Every `client.py` and `aio.py` in the monorepo
- Pattern: keyword-only args, `global` mutation, sets `_token = None` to force re-auth
- Purpose: Package-scoped typed errors; callers can catch at `<Pkg>ClientError` base or at specific subclass
- Examples: `packages/iol-client/src/iol_client/exceptions.py`
- Pattern: `ClientError(Exception)` → `APIError(ClientError)` → `AuthError(APIError)`, `RateLimitError(APIError)`
## Entry Points
- Location: `main_iol.py`, `main_higyrus.py`, `main_matriz.py`, `main_ambito_financiero.py`, `main_wallets.py` at repo root
- Triggers: `uv run --package <pkg> python main_<name>.py`
- Responsibilities: Import the package, call one or two functions, print results; not part of any package distribution
- Location: `packages/<name>/src/<pkg>/__init__.py`
- Triggers: `import <pkg>` or `from <pkg> import aio`
- Responsibilities: Execute `load_dotenv()` (via `client.py` import), populate module-level globals from env vars
## Architectural Constraints
- **Threading:** Sync clients are single-threaded; `httpx.Client` is not shared across threads. Async clients use `asyncio.Lock()` to serialize token refresh and client creation. The `ws_client.py` runs a daemon thread for the WebSocket event loop — the REST token is shared between the REST module and the WS module within `matriz_client`.
- **Global state:** Every `client.py` and `aio.py` holds module-level singletons (`_token`, `_client`, etc.). State is process-wide per package. Test fixtures must `configure()` and monkeypatch to isolate state.
- **Circular imports:** None detected. `aio.py` may import shared types from `client.py` (e.g., `iol_client.aio` imports `InstrumentType` from `iol_client.client`) but `client.py` never imports from `aio.py`.
- **No shared library:** There is no shared internal package in this monorepo by design. Auth logic, exception hierarchies, and HTTP boilerplate are intentionally duplicated across packages to keep each publishable package self-contained.
- **No async support in matriz:** `matriz_client` has no `aio.py`. Async use requires the WebSocket layer (`ws_client.py`) or calling REST functions from a thread executor.
## Anti-Patterns
### Importing `aio` module in sync context
### Mutating module state without `configure()`
### Using the same `aio` state across multiple event loops
## Error Handling
- `_raise_for_response(resp)` is called after every HTTP response; maps 401/403 → `AuthError`, 429 → `RateLimitError`, any other error status → `APIError`
- `matriz_client` additionally checks the JSON payload for `"status": "ERROR"` (application-level errors from Primary API) and raises `PrimaryAPIError`
- `higyrus_client` parses the `"errors"` key from the JSON body and passes structured error details into the exception constructor
- Missing/malformed auth credentials raise the respective `AuthError` before any HTTP call is made
- `SafeModel.from_api()` never raises on missing fields — it substitutes safe defaults
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:knowledge-start -->
## Auto-loaded Knowledge

- **Spike findings for market-libs** (implementation patterns, constraints, gotchas — TokenStore 3-way concurrency primitive + refresh policy with retry/backoff/fail-cache, both validated for Phase 10) → `Skill("spike-findings-market-libs")`
- **Spike findings for codegen** (NO-GO from SPIKE-005; root cause + v1.3 libcst handoff scope) → `Skill("spike-findings-codegen-market-libs")`
<!-- GSD:knowledge-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
