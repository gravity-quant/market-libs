# Technology Stack

**Analysis Date:** 2026-05-27

## Languages

**Primary:**
- Python 3.12+ — all source code across all packages

**Secondary:**
- None

## Runtime

**Environment:**
- CPython 3.12.11 (active venv at `.venv/`, managed by uv)
- Python 3.13 also supported (tested in CI matrix)

**Package Manager:**
- uv 0.9.0
- Lockfile: `uv.lock` (present, 758 lines, committed to repo)

## Frameworks

**HTTP Client:**
- httpx >=0.27 — sync (`httpx.Client`) and async (`httpx.AsyncClient`) HTTP for all five packages

**WebSocket Client:**
- websocket-client >=1.8.0 — used exclusively in `packages/matriz-client/` for MATBA ROFEX Primary API streaming; runs event loop in a background daemon thread

**Testing:**
- pytest >=8.3 — test runner, configured in root `pyproject.toml`
- pytest-asyncio >=0.24 — async test support (`asyncio_mode = "auto"`)
- pytest-httpx >=0.34 — HTTP request mocking for httpx clients
- pytest-cov >=6.0 — coverage reporting

**Build:**
- hatchling — build backend for each package (wheel + sdist)
- uv build — invoked by CI release workflow

## Key Dependencies

**Critical:**
- `httpx >=0.27` — the sole HTTP transport for all packages; sync and async variants used side by side
- `python-dotenv >=1.0` — loads `.env` files at module import time via `load_dotenv()` in every client module
- `websocket-client >=1.8.0` — only `matriz-client` uses this; required for WebSocket streaming

**Development Tools:**
- `ruff >=0.7` — linter and formatter (replaces black + isort + flake8)
- `mypy >=1.13` — strict type checking (`strict = true` in root config)
- `pre-commit >=4.0` — git hooks running ruff and mypy

## Configuration

**Environment:**
- Each package reads credentials from environment variables via `python-dotenv`
- `.env.example` files are present in each package directory as templates
- No `.env` file at monorepo root; per-package `.env` files exist in `packages/higyrus-client/` and `packages/matriz-client/`
- All packages expose a `configure()` function for runtime overrides without restarting the process

**Build:**
- Root `pyproject.toml`: workspace definition, dev dependencies, ruff config, mypy config, pytest config, coverage config
- Per-package `pyproject.toml`: package metadata, runtime dependencies, build system (hatchling)
- Ruff config: `line-length = 100`, `target-version = "py312"`, double quotes, space indentation
- Mypy config: `strict = true`, `python_version = "3.12"`, `explicit_package_bases = true`
- Pytest config: `asyncio_mode = "auto"`, `--import-mode=importlib`, `--strict-markers`
- Pre-commit config: `.pre-commit-config.yaml` — trailing whitespace, YAML/TOML checks, ruff, mypy

## Workspace Structure

**Monorepo layout** (`tool.uv.workspace`):
- `packages/iol-client/` — `iol-client` v0.1.1 (Invertir Online, HTTP sync+async)
- `packages/higyrus-client/` — `higyrus-client` v0.1.1 (Higyrus financial ops, HTTP sync+async)
- `packages/ambito-financiero-client/` — `ambito-financiero-client` v0.1.1 (Ámbito Financiero, HTTP sync+async, no auth)
- `packages/wallets-client/` — `wallets-client` v0.1.0 (Wallets, HTTP sync+async, static Bearer token)
- `packages/matriz-client/` — `matriz-client` v0.1.1 (MATBA ROFEX Primary API, HTTP REST + WebSocket)

All packages: `requires-python = ">=3.12"`, MIT license, `hatchling` build backend, `src/` layout.

## Platform Requirements

**Development:**
- uv 0.9.0+
- Python 3.12 or 3.13
- `uv sync --all-packages --all-extras --dev --frozen` to install workspace

**Production:**
- Packages are distributed as standalone wheels (no shared internal dependencies between packages)
- No deployment target — these are client libraries consumed by other projects

## CI/CD

**CI:** GitHub Actions (`.github/workflows/ci.yml`)
- Triggers on push/PR to `main` (ignores `.md` and `.gitignore` changes)
- Jobs: lint (ruff check + format), pre-commit hooks, typecheck (mypy), tests
- Test matrix: 5 packages × 2 Python versions (3.12, 3.13)
- Uses `astral-sh/setup-uv@v3` with cache enabled

**Release:** GitHub Actions (`.github/workflows/release.yml`)
- Triggers on tags matching `*-client-v*` pattern (e.g., `iol-client-v0.1.1`)
- Validates tag version matches `pyproject.toml` version
- Builds wheel + sdist with `uv build --package <package>`
- Creates GitHub Release with auto-generated notes and attaches artifacts
- Does NOT publish to PyPI

---

*Stack analysis: 2026-05-27*
