# Coding Conventions

**Analysis Date:** 2026-05-27

## Naming Patterns

**Files:**
- Source modules: `snake_case.py` (e.g., `client.py`, `aio.py`, `exceptions.py`, `models.py`)
- Private/internal modules: leading underscore `_snake_case.py` (e.g., `_params.py`, `_parsing.py`)
- Test files: `test_<subject>.py` (e.g., `test_client.py`, `test_async_client.py`, `test_models.py`)
- Shared fixtures: `conftest.py` per package

**Functions and methods:**
- Public API functions: `snake_case` matching the domain language, often `get_<resource>` (e.g., `get_quote`, `get_listado_cuentas`, `get_movimientos`)
- Private internal helpers: `_snake_case` prefix (e.g., `_request`, `_ensure_token`, `_raise_for_response`, `_get`)
- Async counterparts: same name as sync, located in the `aio` submodule (not prefixed with `async_`)

**Variables:**
- Module-level state: `_snake_case` with leading underscore (e.g., `_base_url`, `_token`, `_token_ts`, `_client`)
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `DEFAULT_BASE_URL`, `_REQUEST_TIMEOUT`, `_TOKEN_TTL_SECONDS`)
- Local variables: `snake_case`

**Types and classes:**
- Exception classes: `<Client>Error` base, `<Client>APIError`, `<Client>AuthError`, `<Client>RateLimitError` (e.g., `IOLClientError`, `HigyrusAPIError`, `HigyrusAuthorizationError`)
- Model dataclasses: `PascalCase` matching wire/domain names (e.g., `Cuenta`, `Movimiento`, `PosicionValuada`, `MarketDataSnapshot`)
- `Literal` type aliases: `PascalCase` (e.g., `InstrumentType`, `Side`, `OrderType`, `MarketId`)

**Wire field names on models:**
- Fields inside dataclasses follow the **wire format verbatim** — camelCase from the JSON API (e.g., `idCuenta`, `fechaDesde`, `tipoTitulo`, `marketSegmentId`)
- Python-facing function parameters use `snake_case` for those same concepts (e.g., `id_cuenta`, `fecha_desde`, `tipo_titulo`)

## Code Style

**Formatting:**
- Tool: Ruff formatter (v0.7+)
- Line length: 100 characters
- Quote style: double quotes
- Indent: 4 spaces

**Linting:**
- Tool: Ruff linter with rule sets: E, W (pycodestyle), F (pyflakes), I (isort), B (flake8-bugbear), UP (pyupgrade), SIM (flake8-simplify), RUF, ASYNC, PIE, PT (pytest-style), RET (return), TID (tidy-imports)
- E501 (line-too-long) is ignored — formatter handles it
- S101 (assert use) is ignored only inside `**/tests/**`
- Type checking: mypy in strict mode (`strict = true`, `disallow_untyped_defs = true`, `warn_return_any = true`)

**Future annotations:**
- Every module starts with `from __future__ import annotations` — this is mandatory and applied uniformly

## Import Organization

**Order (enforced by Ruff isort):**
1. `__future__` imports (`from __future__ import annotations`)
2. Standard library imports
3. Third-party imports (`httpx`, `dotenv`)
4. Local package imports (absolute, e.g., `from iol_client.exceptions import ...`)

**Style:**
- No wildcard imports
- No relative imports (enforced by TID)
- `load_dotenv()` called at module level immediately after imports in client modules

**Path aliases:** None — packages use their full package name (`iol_client`, `higyrus_client`, etc.)

## Module Structure Pattern

Every package follows the same layout:

```
src/<pkg>/
    __init__.py     # Flat re-export namespace + __all__ + __version__
    client.py       # Sync HTTP client (module-level state)
    aio.py          # Async HTTP client (module-level state, independent from sync)
    exceptions.py   # Exception hierarchy
    models.py       # Dataclasses (when API returns typed responses)
    _params.py      # Private param-formatting helpers (when needed)
    _parsing.py     # Private parsing helpers (when needed)
```

## Error Handling

**Strategy:** Raise typed exceptions — never return error codes or raw HTTP responses to callers.

**Pattern — `_raise_for_response`:**
Every client module defines a private `_raise_for_response(resp)` function that maps HTTP status codes to specific exception types:
```python
def _raise_for_response(resp: httpx.Response) -> None:
    if resp.status_code in (401, 403):
        raise XAuthError(resp.status_code, resp.text)
    if resp.status_code == 429:
        raise XRateLimitError(resp.status_code, resp.text)
    if resp.is_error:
        raise XAPIError(resp.status_code, resp.text)
```

**Exception hierarchy per package:**
```
<Client>ClientError (base, inherits Exception)
  └── <Client>APIError (status_code + message/errors stored as attributes)
        ├── <Client>AuthError (401/403)
        ├── <Client>AuthorizationError (403 only, when distinct from 401)
        └── <Client>RateLimitError (429)
```

**Attribute preservation:** Every `APIError` stores `status_code` and error payload as attributes for programmatic inspection. Higyrus extends this with `errors: list[dict]` and `timestamp: str | None` matching the API error envelope.

**assert for internal invariants:**
`assert _token is not None` is used after `_ensure_token()` calls to satisfy the type checker — not for user-facing validation.

## Logging

No logging framework is used. No `logging` calls appear in any package. Internal state changes (token refresh, etc.) are silent.

## Comments

**Module docstrings:**
- Every module has a module-level docstring describing: purpose, API usage examples (as `::` code blocks), environment variables, and any auth flow specifics
- Example pattern:
  ```python
  """Cliente HTTP sincrónico para Invertir Online (IOL).

  API a nivel módulo::

      import iol_client
      iol_client.login()

  Variables de entorno:
  - ``IOL_USER`` (requerido)
  """
  ```

**Function docstrings:**
- Public functions: one-line summary + endpoint path in backtick-rst format (e.g., `Endpoint: ``GET /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion````)
- Private functions: one-line summary, no endpoint detail needed
- Inline comments: used sparingly for non-obvious decisions

**Code comments (inline):**
- Section dividers with `# ---...---` separating logical blocks (auth, internals, endpoint groups) within large modules

**Language:** Docstrings and comments are mixed Spanish/English — public-facing docstrings in Spanish, some internal comments in English (especially in `matriz-client`)

## Function Design

**Size:** Functions are small and single-purpose. Endpoint wrappers are typically 5-15 lines. Internal helpers (`_raise_for_response`, `_ensure_token`) are under 10 lines.

**Parameters:**
- Positional arguments for required domain identifiers (e.g., `simbolo`, `id_cuenta`, `fecha_desde`)
- Keyword-only arguments (`*`) for optional/defaulted params (e.g., `mercado: str = "bcba"`, `plazo: str = "t2"`)
- `None` as default for truly optional API params, then dropped via `drop_none()`

**Return Values:**
- Typed with concrete types, never raw `httpx.Response` (except in internal `_request` helpers)
- Model dataclasses for structured responses, `dict[str, Any]` or `list[dict[str, Any]]` for unstructured/pass-through payloads
- `list[Model]` for collections, with `if raw is None: return []` guard for 204 responses

## Module-Level State Pattern

All packages use **module-level global state** (no class instances exposed to callers):

```python
_base_url: str = os.getenv("ENV_VAR", "default").rstrip("/")
_user: str = os.getenv("USER_VAR", "")
_token: str | None = None
_token_ts: float = 0.0
_client = httpx.Client(timeout=_REQUEST_TIMEOUT)
```

A `configure(*, base_url=None, username=None, password=None)` function (keyword-only args) allows runtime reconfiguration and resets the cached token.

Async modules add `asyncio.Lock()` instances for token and client management:
```python
_token_lock = asyncio.Lock()
_client_lock = asyncio.Lock()
```

## Model Design (SafeModel / dataclasses)

**Pattern (higyrus-client and matriz-client):**
- Models are `@dataclass(frozen=True, slots=True)` — immutable and memory-efficient
- Inherit from `SafeModel` base class
- Constructed exclusively via `Model.from_api(payload: Any)` classmethod — never `Model(field=value)` directly
- `from_api` tolerates `None`, non-dict, or partial payloads, substituting safe defaults: `str → ""`, `int → 0`, `float → 0.0`, `bool → False`, `list[X] → []`, nested `SafeModel → X.from_api(None)`
- Wire field names are camelCase verbatim (matching JSON keys)
- `Optional[T]` / `T | None` fields default to `None` (explicit opt-in to nullable)
- An `empty()` classmethod is available for tests and defaults

**Simpler packages (iol-client, wallets-client, ambito-financiero-client):**
Return `dict[str, Any]` or `list[dict[str, Any]]` — no model layer

## Exports

**`__init__.py` pattern:**
- Explicit `__all__` list with all public names
- `__version__` string (e.g., `"0.1.1"`)
- Re-exports from `client`, `exceptions`, `models` submodules
- `aio` submodule is importable as `from <pkg> import aio` but not re-exported into the flat namespace

---

*Convention analysis: 2026-05-27*
