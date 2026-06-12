# Codebase Structure

**Analysis Date:** 2026-05-27

## Directory Layout

```
market-libs/                          # uv workspace root (not published)
├── packages/                         # All publishable packages
│   ├── ambito-financiero-client/     # Ámbito Financiero FX rate client
│   │   ├── src/
│   │   │   └── ambito_financiero_client/
│   │   │       ├── __init__.py       # Public API + __version__
│   │   │       ├── client.py         # Sync implementation
│   │   │       ├── aio.py            # Async implementation
│   │   │       ├── _parsing.py       # Argentine decimal parser (private)
│   │   │       └── exceptions.py     # Exception hierarchy
│   │   ├── tests/
│   │   │   ├── conftest.py           # Shared fixtures (configure + monkeypatch)
│   │   │   ├── test_client.py        # Sync tests
│   │   │   └── test_async_client.py  # Async tests
│   │   └── pyproject.toml            # Package metadata + hatchling build
│   │
│   ├── higyrus-client/               # Higyrus brokerage back-office client
│   │   ├── src/
│   │   │   └── higyrus_client/
│   │   │       ├── __init__.py
│   │   │       ├── client.py
│   │   │       ├── aio.py
│   │   │       ├── _params.py        # Date/bool/None param helpers (private)
│   │   │       ├── models.py         # SafeModel frozen dataclasses
│   │   │       └── exceptions.py
│   │   ├── tests/
│   │   │   ├── conftest.py
│   │   │   ├── test_client.py
│   │   │   └── test_async_client.py
│   │   ├── documentation/            # API docs / reference (not distributed)
│   │   └── pyproject.toml
│   │
│   ├── iol-client/                   # Invertir Online (IOL) trading client
│   │   ├── src/
│   │   │   └── iol_client/
│   │   │       ├── __init__.py
│   │   │       ├── client.py
│   │   │       ├── aio.py
│   │   │       └── exceptions.py
│   │   ├── tests/
│   │   │   ├── conftest.py
│   │   │   ├── test_client.py
│   │   │   └── test_async_client.py
│   │   └── pyproject.toml
│   │
│   ├── matriz-client/                # MATBA ROFEX Primary API client (REST + WS)
│   │   ├── src/
│   │   │   └── matriz_client/
│   │   │       ├── __init__.py
│   │   │       ├── client.py         # REST implementation (sync only)
│   │   │       ├── ws_client.py      # WebSocket streaming client
│   │   │       ├── models.py         # Frozen safe-access dataclasses
│   │   │       ├── types.py          # Literal type aliases (Side, OrderType…)
│   │   │       └── exceptions.py
│   │   ├── tests/
│   │   │   ├── conftest.py
│   │   │   ├── test_client.py
│   │   │   ├── test_ws_client.py
│   │   │   ├── test_models.py
│   │   │   ├── test_types.py
│   │   │   └── test_exceptions.py
│   │   ├── documentation/            # API specs / reference (not distributed)
│   │   └── pyproject.toml
│   │
│   └── wallets-client/               # Internal wallets service client (stub)
│       ├── src/
│       │   └── wallets_client/
│       │       ├── __init__.py
│       │       ├── client.py
│       │       ├── aio.py
│       │       └── exceptions.py
│       ├── tests/
│       │   ├── conftest.py
│       │   ├── test_client.py
│       │   └── test_async_client.py
│       └── pyproject.toml
│
├── main_ambito_financiero.py         # Dev smoke-test script
├── main_higyrus.py                   # Dev smoke-test script
├── main_iol.py                       # Dev smoke-test script
├── main_matriz.py                    # Dev smoke-test script
├── main_wallets.py                   # Dev smoke-test script
├── pyproject.toml                    # Workspace root: uv config, ruff, mypy, pytest
├── uv.lock                           # Locked dependency tree (committed)
├── README.md
├── dist/                             # Build output (not committed)
├── .venv/                            # Workspace virtual env (not committed)
├── .mypy_cache/                      # mypy incremental cache (not committed)
├── .pytest_cache/                    # pytest cache (not committed)
├── .ruff_cache/                      # ruff cache (not committed)
├── .github/
│   └── workflows/                    # CI workflows
└── .planning/
    └── codebase/                     # GSD codebase map documents
```

## Directory Purposes

**`packages/`:**
- Purpose: Contains all five publishable client packages as uv workspace members
- Contains: One directory per package, each independently versioned and buildable
- Key files: Each package has its own `pyproject.toml` with `hatchling` as the build backend

**`packages/<name>/src/<pkg_name>/`:**
- Purpose: `src`-layout source root for the package (prevents accidental imports of the uninstalled package)
- Contains: `__init__.py`, `client.py`, `aio.py` (when applicable), `exceptions.py`, and optional `models.py`, `types.py`, `ws_client.py`, `_*.py`
- Key constraint: Package name uses underscores (Python import name); directory name uses hyphens (PyPI distribution name)

**`packages/<name>/tests/`:**
- Purpose: Package-level test suite, co-located with the package being tested
- Contains: `conftest.py` for shared fixtures, `test_client.py` (sync), `test_async_client.py` (async), and additional `test_*.py` for models/types/exceptions in complex packages

**`packages/<name>/documentation/`:**
- Purpose: Reference materials (API specs, vendor docs) for development; not included in wheel distribution
- Present in: `higyrus-client/`, `matriz-client/`

**Root `main_*.py` scripts:**
- Purpose: Manual smoke-test and development exploration scripts; not distributed, not tested by CI
- Run with: `uv run --package <pkg-name> python main_<name>.py`

## Key File Locations

**Entry Points:**
- `packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py`: Public API for ambito client
- `packages/higyrus-client/src/higyrus_client/__init__.py`: Public API for higyrus client
- `packages/iol-client/src/iol_client/__init__.py`: Public API for iol client
- `packages/matriz-client/src/matriz_client/__init__.py`: Public API for matriz client (REST + WS)
- `packages/wallets-client/src/wallets_client/__init__.py`: Public API for wallets client

**Configuration:**
- `pyproject.toml`: Workspace root — uv workspace members, shared dev dependencies, ruff, mypy, pytest config
- `packages/<name>/pyproject.toml`: Per-package metadata, runtime dependencies, hatchling build config
- `uv.lock`: Locked full dependency tree; must be committed

**Core Logic:**
- `packages/iol-client/src/iol_client/client.py`: IOL sync client — OAuth, quotes, instruments
- `packages/iol-client/src/iol_client/aio.py`: IOL async client
- `packages/higyrus-client/src/higyrus_client/client.py`: Higyrus sync — accounts, movements, positions
- `packages/higyrus-client/src/higyrus_client/aio.py`: Higyrus async
- `packages/higyrus-client/src/higyrus_client/models.py`: Higyrus response dataclasses
- `packages/higyrus-client/src/higyrus_client/_params.py`: Higyrus query param serialization
- `packages/matriz-client/src/matriz_client/client.py`: Primary API REST client
- `packages/matriz-client/src/matriz_client/ws_client.py`: Primary API WebSocket client
- `packages/matriz-client/src/matriz_client/models.py`: Primary API response dataclasses
- `packages/matriz-client/src/matriz_client/types.py`: Primary API Literal type aliases
- `packages/ambito-financiero-client/src/ambito_financiero_client/client.py`: Ámbito sync client
- `packages/ambito-financiero-client/src/ambito_financiero_client/_parsing.py`: AR decimal parser
- `packages/wallets-client/src/wallets_client/client.py`: Wallets sync client (stub)

**Testing:**
- `packages/iol-client/tests/conftest.py`: Reference fixture — configure + monkeypatch token pattern
- `packages/matriz-client/tests/test_models.py`: Tests for SafeModel deserialization
- All test roots discovered from `packages/` per workspace `pyproject.toml`

## Naming Conventions

**Package directories (distribution name):**
- Pattern: `kebab-case` — e.g., `iol-client`, `ambito-financiero-client`

**Python import names:**
- Pattern: `snake_case` — e.g., `iol_client`, `ambito_financiero_client`
- Derived directly from the distribution name by replacing `-` with `_`

**Source files:**
- Public modules: `snake_case.py` — `client.py`, `aio.py`, `models.py`, `types.py`, `exceptions.py`, `ws_client.py`
- Private helpers: Leading underscore — `_params.py`, `_parsing.py`

**Module-level private variables:**
- Pattern: Single leading underscore — `_base_url`, `_token`, `_client`, `_token_expires_at`
- Constants: `SCREAMING_SNAKE_CASE` — `_TOKEN_TTL_SECONDS`, `_REQUEST_TIMEOUT`, `DEFAULT_BASE_URL`

**Exception classes:**
- Pattern: `<PrefixCamelCase>Error` — e.g., `IOLClientError`, `HigyrusAuthError`, `PrimaryAPIError`

**Model classes:**
- Pattern: `PascalCase` matching the domain entity — e.g., `Cuenta`, `Movimiento`, `MarketDataSnapshot`, `Order`

**Type aliases:**
- Pattern: `PascalCase` Literal aliases — e.g., `Side`, `OrderType`, `MarketId`

**Test files:**
- Pattern: `test_<subject>.py` — `test_client.py`, `test_async_client.py`, `test_models.py`

## Where to Add New Code

**New endpoint in an existing client:**
- Add the function to `packages/<name>/src/<pkg>/client.py` following the `_request()` → domain function pattern
- Mirror it in `packages/<name>/src/<pkg>/aio.py` if the package has an async surface
- Export it from `packages/<name>/src/<pkg>/__init__.py` (both `from … import` and `__all__`)
- Add test in `packages/<name>/tests/test_client.py` and `test_async_client.py`

**New response model:**
- Add frozen dataclass to `packages/<name>/src/<pkg>/models.py` inheriting from `SafeModel` (higyrus pattern) or using the introspection approach (matriz pattern)
- Export from `__init__.py`

**New type alias / Literal:**
- Add to `packages/<name>/src/<pkg>/types.py` (matriz) or inline in `client.py` as a module-level `Literal` (iol pattern for `InstrumentType`)

**New package (new financial service):**
- Create `packages/<new-service>-client/` directory
- Add `src/<new_service_client>/` with `__init__.py`, `client.py`, `aio.py`, `exceptions.py`
- Add `pyproject.toml` using `hatchling` build backend, `httpx>=0.27` and `python-dotenv>=1.0` as runtime deps
- Register in root `pyproject.toml` under `[tool.uv.workspace] members` and `[tool.uv.sources]`
- Follow env var naming convention: `<SERVICE>_BASE_URL`, `<SERVICE>_USER`, `<SERVICE>_PASSWORD` (or `<SERVICE>_TOKEN` for static tokens)

**Private helper module:**
- Name it `_<purpose>.py` (leading underscore signals private)
- Place inside `packages/<name>/src/<pkg>/`
- Do NOT export from `__init__.py`

## Special Directories

**`.venv/`:**
- Purpose: Shared workspace virtual environment managed by uv
- Generated: Yes (by `uv sync`)
- Committed: No

**`dist/`:**
- Purpose: Built wheel/sdist artifacts from `uv build`
- Generated: Yes
- Committed: No

**`.mypy_cache/`:**
- Purpose: mypy incremental type-check cache
- Generated: Yes
- Committed: No

**`.planning/codebase/`:**
- Purpose: GSD codebase map documents consumed by `/gsd-plan-phase` and `/gsd-execute-phase`
- Generated: By GSD map agents
- Committed: Yes (part of the planning workflow)

**`packages/<name>/documentation/`:**
- Purpose: Vendor API reference material for development reference
- Generated: No (manually added)
- Committed: Yes (present in higyrus-client and matriz-client)

---

*Structure analysis: 2026-05-27*
