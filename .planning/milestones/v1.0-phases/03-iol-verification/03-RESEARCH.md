# Phase 3: IOL Verification - Research

**Researched:** 2026-06-06
**Domain:** OAuth password+refresh grant lifecycle + dual sync/async live-API verification + raw-`dict` shape drift detection
**Confidence:** HIGH for stack/architecture/Phase-2-inheritance · MEDIUM for IOL refresh wire payload (cross-referenced 3 public OAuth wrappers + IOL Help page heading; the Help page itself returns 403 to non-browser fetchers and Context7 has no IOL coverage) · LOW for IOL lockout policy (no public threshold documentation)

## Summary

Phase 3 is Phase 2's lifecycle (driver-only live + mocked-only pytest + classified findings + schema snapshots + Verified-live/Regressions sections) applied to a client with three new dimensions: (1) **real OAuth auth with lockout risk** on `api.invertironline.com`; (2) **silent shape-drift detection** because IOL returns raw `dict[str, Any]` with zero validation — a missing envelope key like `["titulos"]` is swallowed by `data.get("titulos", [])`; (3) **a known bug fix in-cycle** (IOL-07: `_refresh_token` not captured, no refresh path, password grant fires on every expiry).

The Phase 2 driver and harness are reused verbatim: the `append_finding` helper is hardened post-review (CR-01 prose preservation, CR-02 single-line title invariant, WR-04 pkg slug validation), the driver pattern is locked (typed `exc.status_code`, single HTTP per probe, `contextlib.suppress(Exception)` around `aclose`), and the schema snapshot envelope (D-21) plus no-overwrite-on-drift (D-25) is already proven against Ámbito. CONTEXT.md locks 22 decisions (D-IOL-1..22) covering all auth-once safety, the 15-probe ordered sequence, the dual sync/async refresh implementation, the field→type map, and the test sections.

**Primary recommendation:** Implement the 15 probes exactly per D-IOL-5; implement `_refresh()` as a new private function that mirrors `login()` (sync) and `_login_unlocked()` (async) — but with `grant_type=refresh_token&refresh_token={_refresh_token}` body and **inside the existing `_token_lock` for async** via a double-checked-locking pattern; treat the refresh response as **possibly rotating** the refresh_token (capture `data.get("refresh_token")` if present, keep old otherwise — verified against three public IOL wrappers); register four mocked refresh tests per surface (success, fallback-to-password, both-fail, login-captures-refresh) using **registration-order FIFO** of `pytest-httpx` (verified against official docs); for the `["titulos"]` envelope drift, the field-type-map probe must call `_request` **directly** to inspect the raw payload (not `get_instruments_by_type`, which swallows the key).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Auth-once safety & lockout management (NEW for IOL):**

- **D-IOL-1:** Probe 401 (IOL-05) opt-in via `VERIFY_IOL_BAD_CREDS=1`. Mirror exacto del patrón Phase 2 (D-12 `VERIFY_ANTIBOT`). Sin la env var, el probe imprime `PROBE auth_401: SKIPPED (opt-in via VERIFY_IOL_BAD_CREDS=1)` y el driver sigue. Single-shot, sin retry, sin sleep, sin loops (D-14 mirror).
- **D-IOL-2:** Inyección de bad-creds vía `configure(password=IOL_PASSWORD + "_INVALID")` + try/finally restore. Mirror exacto del patrón D-15 Phase 2. Una sola env var (`IOL_PASSWORD`) sigue siendo la fuente de verdad; el `finally` SIEMPRE restaura `password=IOL_PASSWORD` original.
- **D-IOL-3:** `login()` explícito up-front + fail-fast con cascade SKIPPED. El driver llama `iol_client.login()` (sync) y `await aio.login()` (async) UNA sola vez al inicio del run. Si `login()` levanta `IOLAuthError` → TODOS los probes downstream marcados como `SKIPPED("auth failed: <reason>")` en cascada, summary final + exit 0 (D-04 honrado). Cualquier otro error inesperado en `login()` propaga como crash inesperado.
- **D-IOL-4:** Probe 401 corre ÚLTIMO en la secuencia (mirror D-13 de Phase 2).

**Driver structure & lifecycle (carry-forward from Phase 2 + adaptaciones):**

- **D-IOL-5:** Secuencia de 15 probes en `main_iol.py` con stdout verbatim `PROBE <name>: <status> <detail>`:
  1. `probe_login_sync` — `iol_client.login()` (IOL-01)
  2. `probe_login_async` — `await aio.login()` (IOL-01)
  3. `probe_get_quote_sync` — `iol_client.get_quote("GGAL")` (IOL-02)
  4. `probe_get_quote_async` — `await aio.get_quote("GGAL")` (IOL-02)
  5. `probe_get_historical_quotes_sync` — GGAL últimos 5 días hábiles (IOL-02)
  6. `probe_get_historical_quotes_async` — espejo (IOL-02)
  7. `probe_get_instruments_sync` — `pais="argentina"` (IOL-02)
  8. `probe_get_instruments_async` — espejo (IOL-02)
  9. `probe_get_instruments_by_type_sync` — `instrument_type="acciones"` (IOL-02 + IOL-04 envelope)
  10. `probe_get_instruments_by_type_async` — espejo
  11. `probe_parity_sync_async` — diff estructural (IOL-06)
  12. `probe_field_type_map` — `schema_of(raw)` por endpoint vs `_ASSUMED_*` (IOL-03 + IOL-04)
  13. `probe_schema_snapshot` — 4 snapshots D-21 + D-25 (DRIFT-01 mirror)
  14. `probe_refresh_token` — fuerza `_token_expires_at = 0` y verifica el refresh path (IOL-07 in-vivo)
  15. `probe_auth_401` — ÚLTIMO, opt-in (D-IOL-1, D-IOL-2, D-IOL-4)

- **D-IOL-6:** Lifecycle async — un único `asyncio.run(_async_main(...))` + `await aio.aclose()` dentro de `contextlib.suppress(Exception)` (IN-03 pattern de Phase 2). El `_async_main` orquesta probes 2/4/6/8/10 y devuelve payloads para 11/12/13.
- **D-IOL-7:** `safe_print(text, secrets=[IOL_PASSWORD, IOL_USER, _refresh_token])`. Lista de secrets NO vacía (a diferencia de Phase 2); `_refresh_token` se agrega dinámicamente tras el primer `login()`.

**Refresh token + password fallback (IOL-07 — fix in-cycle):**

- **D-IOL-8:** Estado nuevo en `client.py` y `aio.py`: `_refresh_token: str | None = None`. Mirror del singleton `_token`. Barrel `__init__.py` NO re-exporta. `configure()` resetea ambos.
- **D-IOL-9:** `login()` captura ambos tokens. Si `refresh_token` no está en la respuesta → finding OPEN clase AUTH y `_refresh_token = None`.
- **D-IOL-10:** `_ensure_token()` con fallback en dos niveles (mirror sync+async):
  ```
  if _token and time.time() < _token_expires_at: return
  if _refresh_token:
      try: _refresh(); return
      except IOLAuthError: pass
  login()
  ```
  `_refresh()` = `POST /token` con `grant_type=refresh_token&refresh_token={_refresh_token}`. Si succeeds: actualiza `_token`, `_refresh_token` (rotación opcional), `_token_expires_at`. Si 4xx: `IOLAuthError` → fallback a password.
- **D-IOL-11:** Probe in-vivo `probe_refresh_token`. Verifica `_refresh_token` cacheado tras `login()`; fuerza `_token_expires_at = 0.0`; llama un endpoint autenticado; verifica que NO se re-disparó password grant (observar `_token` change + `_refresh_token` no None + nuevo `expires_at`). NO ejercita la rama "refresh inválido → fallback a password" en vivo.
- **D-IOL-12:** Tests mockeados duales para IOL-07 (`Verified live` + `Regressions`):
  - `test_refresh_token_success_path` (sync) + async
  - `test_refresh_fails_falls_back_to_password` (sync) + async
  - `test_refresh_and_password_both_fail` (sync) + async
  - `test_login_captures_refresh_token` (sync) + async

**Field→type map + drift detection (IOL-03, IOL-04):**

- **D-IOL-13:** Reutilizar `verification.schema.schema_of(payload)`. Único primitivo. PII-free por construcción.
- **D-IOL-14:** Caller assumptions hardcoded en `main_iol.py` como constantes module-level (`_ASSUMED_QUOTE_FIELDS`, `_ASSUMED_HISTORICAL_FIELDS`, `_ASSUMED_INSTRUMENTS_BY_TYPE_ENVELOPE`).
- **D-IOL-15:** Tres clases de finding del `probe_field_type_map` (todos surface=both, status=OPEN): `SHAPE` "missing assumed key"; `SHAPE` "type drift"; `SHAPE` "unexpected key" (info-only).

**Schema snapshots por endpoint (DRIFT-01 mirror):**

- **D-IOL-16:** 4 snapshots committeable en `.planning/verification/schemas/iol-client/`: `get-quote.json`, `get-historical-quotes.json`, `get-instruments.json`, `get-instruments-by-type.json`. Envelope D-21 + D-25 no-overwrite-on-drift.
- **D-IOL-17:** Para `get_instruments_by_type`: 1 snapshot baseline (`acciones`) + sanity check de los 6 (sólo `isinstance(list)` + `len > 0` + `isinstance(list[0], dict)`).

**Endpoint sweep parameters:**

- **D-IOL-18:** Símbolo fijo `GGAL` (`_SAMPLE_SYMBOL = "GGAL"`), país `argentina`, plazo `t2` default.
- **D-IOL-19:** Rango histórico = `_last_business_day(today) - 5d` to `_last_business_day(today)` (D-24 Phase 2 mirror).

**Sync↔async parity (IOL-06):**

- **D-IOL-20:** `probe_parity_sync_async` compara estructura, NO valores (precio cambia entre calls). Discrepancia → finding `SYNC-ASYNC-DRIFT` OPEN.

**Verified-live tests + Regressions sections (D-08/D-09 Phase 2 mirror):**

- **D-IOL-21:** Append a `test_client.py` + `test_async_client.py`: `# ------ Verified live (Phase 3) ------` y `# ------ Regressions ------`. Invariantes mínimos: URL exactas por endpoint (IOL-02), `data["titulos"]` unwrap (IOL-04), `ultimoPrecio` es int/float (IOL-04), formato path histórico `YYYY-MM-DD/YYYY-MM-DD/sinAjustar` con day > 12 (IOL-04). Regressions: 4 tests de IOL-07 por surface (D-IOL-12).

**Redaction + logging discipline:**

- **D-IOL-22:** Reuso de `safe_print(text, secrets=[...])`. Lista se inicializa con `[IOL_USER, IOL_PASSWORD]` y se EXTIENDE con `_refresh_token` tras primer login.

### Claude's Discretion

- Texto exacto de líneas verbatim del summary final (siguen formato Phase 2: `SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N`).
- Estructura interna de `_refresh()` y nombres de helpers privados (`_token_payload`, `_refresh_payload`, etc.).
- Cómo se distingue rotación de refresh_token vs no-rotación (el cliente acepta y guarda el nuevo si viene; sino, mantiene el existente).
- Tactic exacta de cascade SKIPPED tras `login()` failure (D-IOL-3): flag module-level `_auth_failed: bool` vs wrapper decorator vs early-return en cada probe.
- Cómo el probe 14 (`probe_refresh_token`) verifica que el refresh funcionó (D-IOL-11 sugiere observar `_token` change + `_refresh_token` no None + nuevo `expires_at`).
- Bounds plausibles para sanity check de precios en `probe_get_quote` (e.g., `0 < ultimoPrecio < 1_000_000`). Discrecional si añadirlo.
- Timing exacto del `_token_expires_at = 0.0` injection en `probe_refresh_token`.
- Si `probe_get_instruments` también ejercita un país inválido (D-IOL-13 sugiere que NO — rama de error fuera del scope vivo).

### Deferred Ideas (OUT OF SCOPE)

- `get_quote` con múltiples símbolos (pase paramétrico sobre N stocks) — Phase 3.X o ciclo posterior.
- Verificación viva de `get_instruments_by_type` con los 6 InstrumentType (drift detection per-type) — ciclo futuro.
- Encoding del `_refresh_token` como secret persistido a disco — in-memory only.
- Throttling / rate-limit-aware retries en `_ensure_token` — fuera de scope (D-IOL-1 spirit).
- Anonymize() para payload de IOL — IOL devuelve datos públicos de mercado sin PII directa.
- Anti-bot probe — IOL no implementa anti-bot vía UA filtering.
- Test de auth-once discipline mockeado — verificación del fixture, no del cliente.
- Plausibility bounds en `get_historical_quotes`.
- Refactor a clase `Client` por instancia / deduplicación sync-async — PROJECT.md lo marca fuera de scope.
- DRIFT-02 (informe consolidado per-package) — anclado a Phase 5.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| IOL-01 | Verificar contra IOL en vivo el flujo de auth (`login()` explícito + lazy-auth en la primera llamada), sync y async | Probes 1+2 (`probe_login_sync` + `probe_login_async`, D-IOL-3); existing `login()`/`_ensure_token()` already implement up-front + lazy patterns — see [Code Examples §Auth flow current](#auth-flow-current); cascade-SKIPPED on `IOLAuthError` (D-IOL-3) implemented via module-level `_auth_failed` flag |
| IOL-02 | Barrido happy-path de `get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type` reteniendo el payload crudo, sync y async | Probes 3-10 (D-IOL-5); WR-03 mirror: single HTTP call per probe via `_request` direct (no double-call via wrapper) — see [Pitfalls §Double HTTP](#pitfall-1-doubling-http-calls-by-using-both-_request-and-the-public-wrapper); raw payload captured for probes 11/12/13 reuse |
| IOL-03 | Construir un mapa campo→tipo observado del `dict` crudo y compararlo con lo que asumen los callers | Probe 12 (`probe_field_type_map`) using `schema_of(raw)` + `_ASSUMED_*` constants (D-IOL-13, D-IOL-14); three SHAPE finding sub-classes (D-IOL-15); recursive `schema_of` already PII-free by construction |
| IOL-04 | Verificar en vivo la clave `["titulos"]`, formato fecha path histórico, campos numéricos como JSON number | Probe 9/10 + probe 12 envelope check via `_request` direct (NOT `get_instruments_by_type` which swallows missing key) — see [Pitfalls §Envelope swallow](#pitfall-2-the-titulos-envelope-key-is-swallowed-by-get_instruments_by_type); Verified-live tests assert URL with day > 12 (D-IOL-21) + `isinstance(ultimoPrecio, int \| float)` |
| IOL-05 | Verificar el mapeo del error 401 en vivo (credenciales inválidas vía `configure()`) | Probe 15 (`probe_auth_401`, ÚLTIMO, D-IOL-4) opt-in via `VERIFY_IOL_BAD_CREDS=1` (D-IOL-1); bad-creds via `configure(password=IOL_PASSWORD + "_INVALID")` + try/finally restore (D-IOL-2); single-shot, no retry |
| IOL-06 | Verificar paridad estructural sync↔async para cada endpoint | Probe 11 (`probe_parity_sync_async`, D-IOL-20) — structural-only via `schema_of(sync) == schema_of(async)`; never compares numeric values; per-endpoint finding `SYNC-ASYNC-DRIFT` OPEN on mismatch |
| IOL-07 | Implementar `grant_type=refresh_token` con fallback a password grant en `client.py` y `aio.py`, con tests que cubran refresh exitoso y fallback | New `_refresh_token` global + `_refresh()` private (D-IOL-8, D-IOL-9, D-IOL-10); dual sync/async with `_token_lock` double-checked locking in async (see [Architecture Patterns §Refresh path](#pattern-2-refresh-path-with-double-checked-locking-async)); 4 mocked tests per surface (D-IOL-12) using FIFO registration order — see [Code Examples §pytest-httpx refresh test](#pytest-httpx-refresh-token-test-pattern) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

These constraints are MANDATORY for all Phase 3 work:

- **Python 3.12+** target (CI matrix 3.12 + 3.13).
- **uv** for env management; `uv sync --all-packages --all-extras --dev --frozen` is the install path.
- **httpx >=0.27** (sync + async) is the only HTTP transport.
- **pytest >=8.3 + pytest-asyncio >=0.24 + pytest-httpx >=0.34**; `asyncio_mode = "auto"`, `--import-mode=importlib`, `--strict-markers`.
- **mypy --strict** must pass (`disallow_untyped_defs = true`, `warn_return_any = true`, `no_implicit_optional = true`).
- **ruff** line-length=100, double quotes, 4-space indent. Lint set: `E,W,F,I,B,UP,SIM,RUF,ASYNC,PIE,PT,RET,TID`. Tests have `S101` ignored.
- **Every module starts with `from __future__ import annotations`** — mandatory and applied uniformly.
- **No wildcard imports, no relative imports** (TID enforced).
- **Dual sync/async espejado por convención** — any logic fix in `client.py` must be mirrored in `aio.py`.
- **No shared library between packages** by design — auth logic, HTTP boilerplate, and exceptions are intentionally duplicated per package.
- **Credentials in `.env` per package; nunca commitear `.env`** ni exponer credenciales en logs, reportes o tests.
- **Module-level singleton state pattern** — `_token`, `_base_url`, `_client` are module globals mutated via `configure()`. New `_refresh_token` follows this pattern.
- **Pre-commit hooks** (`.pre-commit-config.yaml`) run ruff and mypy on every commit.
- **GSD workflow enforcement** — execute through `/gsd-execute-phase` (this RESEARCH.md is consumed by `gsd-planner`).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Live HTTP requests to `api.invertironline.com` | API / Backend (the IOL server) | — | The verification phase calls the live service; the client library is the user-of-API tier |
| OAuth `/token` password+refresh flow | API / Backend (IOL `/token` endpoint) + Client library (`iol_client.client._refresh`) | — | Auth state cached in client module globals; the server owns rotation policy |
| Module-level singleton state (`_token`, `_refresh_token`, `_client`) | Client library (`packages/iol-client/src/iol_client/`) | — | By project design — no shared module, no Client class; state per-process per-package |
| Raw payload retention for field→type map | Driver (`main_iol.py`) | — | The driver captures `resp.json()` from `_request` direct calls; never persists raw to disk (only `schema_of`) |
| Schema snapshot persistence (envelope D-21) | Filesystem (`.planning/verification/schemas/iol-client/*.json`) | Driver writer | Driver owns write; git tracks history |
| Findings classification + lifecycle | Filesystem (`.planning/verification/iol-client-findings.md`) | `verification/findings.py` helper | Helper owns parser/serializer; human owns status promotion |
| Mocked regression tests | Test layer (`packages/iol-client/tests/test_client.py`, `test_async_client.py`) | pytest-httpx HTTPXMock | Existing pattern from Phase 2; FIFO response order |
| Driver verbatim stdout (`PROBE ... PASS/FAIL/SKIPPED/FINDING`) | Driver process stdout via `safe_print` | `verification.redaction.safe_print` | Two-pass masking: secrets list + `Bearer` regex |
| Auth-once discipline + cascade SKIPPED | Driver process (`_auth_failed: bool` module flag) | — | Discretion per D-IOL-3; alternatives: decorator, early-return |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | >=0.27 | Sync (`httpx.Client`) + async (`httpx.AsyncClient`) HTTP for `iol-client` | Already the sole transport — required by project; no alternative considered [VERIFIED: `pyproject.toml` line 21, `packages/iol-client/src/iol_client/client.py` import] |
| `python-dotenv` | >=1.0 | Loads `.env` at module import (`load_dotenv()` in client + aio) | Already in use across all 5 packages [VERIFIED: `packages/iol-client/src/iol_client/client.py:30,43`] |
| `pytest` | >=8.3 | Test runner | Project standard; `asyncio_mode="auto"` + `--strict-markers` already configured [VERIFIED: root `pyproject.toml`] |
| `pytest-asyncio` | >=0.24 | Async test support (`auto` mode) | Required for `test_async_client.py` mirror tests [VERIFIED: `pyproject.toml` line 28] |
| `pytest-httpx` | >=0.34 | HTTP mock fixture (`HTTPXMock`) | Standard for `iol-client` tests; FIFO response matching by registration order [CITED: https://colin-b.github.io/pytest_httpx/] |
| `mypy` | >=1.13 | Strict type checking | `disallow_untyped_defs=true`, `warn_return_any=true` [VERIFIED: root `pyproject.toml`] |
| `ruff` | >=0.7 | Linter + formatter (replaces black + isort + flake8) | `line-length=100`, double quotes, target `py312` [VERIFIED: root `pyproject.toml`] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `verification/findings.py` | local | `append_finding(...)` idempotent helper | Each probe with a discrepancy: emit one finding per shape/auth/type drift. Already hardened (CR-01, CR-02, WR-04). |
| `verification/schema.py` | local | `schema_of(payload)` recursive reducer | `probe_field_type_map` (D-IOL-13) — one primitive only. PII-free by construction. |
| `verification/redaction.py` | local | `safe_print(text, secrets=[...])` | All driver stdout (D-IOL-7, D-IOL-22). Two-pass masking: explicit secrets + `Bearer\s+...` regex. |
| `verification/env_gate.py` | local | `require_env(pkg, [vars])` | Driver entry; skip-and-continue if `IOL_USER`/`IOL_PASSWORD` missing (HARN-01). |
| Python stdlib `contextlib.suppress` | 3.12 | `await aio.aclose()` cleanup envelope | IN-03 mirror — D-04 violation guard. |
| Python stdlib `datetime` (`dt.date.today`, `dt.timedelta`) | 3.12 | Date arithmetic for historical range | D-IOL-19 — `_last_business_day(today) - 5d` |
| Python stdlib `asyncio.Lock` (already in `aio.py`) | 3.12 | `_token_lock` + `_client_lock` | The refresh path must reuse `_token_lock` via double-checked locking (see [Pattern 2](#pattern-2-refresh-path-with-double-checked-locking-async)). |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pytest-httpx` registration-order FIFO | `is_reusable=True` per response | Would mask the regression case where code makes unexpected repeated requests — FIFO is the project default for refresh tests. [CITED: colin-b.github.io/pytest_httpx] |
| Module-level `_refresh_token` global | A new dataclass `_TokenState` holding `(access, refresh, expires_at)` | Project convention is module globals (CONCERNS.md). A dataclass would be a refactor, not a fix. Out of scope (PROJECT.md). |
| `requests` library | Stay on `httpx` | Project enforces `httpx` only; no change. |
| `httpx-oauth` for refresh flow | Hand-implement `_refresh()` | Adds a dependency for one method; project pattern is thin wrappers per package, no auth helper. |

**Installation:**
No new packages needed for Phase 3. All transitive deps already in `uv.lock`. Verify with:
```bash
uv sync --all-packages --all-extras --dev --frozen
```

**Version verification:**
- `httpx >=0.27` — verified via `pyproject.toml` line 21 (workspace dev deps).
- `pytest-httpx >=0.34` — verified via `pyproject.toml` line 30. The CHANGELOG documents `is_reusable` and `can_send_already_matched_responses` (added 0.31+). [CITED: https://github.com/Colin-b/pytest_httpx/blob/develop/CHANGELOG.md]
- All packages already pinned in `uv.lock` (758 lines, committed).

## Package Legitimacy Audit

Phase 3 installs **no new external packages**. All used packages are already in `uv.lock` and were verified at original install time.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `httpx` | PyPI | 9+ yrs | 100M+/wk | github.com/encode/httpx | n/a (existing) | Approved (existing) |
| `pytest-httpx` | PyPI | 5+ yrs | 5M+/wk | github.com/Colin-b/pytest_httpx | n/a (existing) | Approved (existing) |
| `pytest-asyncio` | PyPI | 9+ yrs | 30M+/wk | github.com/pytest-dev/pytest-asyncio | n/a (existing) | Approved (existing) |
| `python-dotenv` | PyPI | 11+ yrs | 80M+/wk | github.com/theskumar/python-dotenv | n/a (existing) | Approved (existing) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*Phase 3 is a verify-and-fix-in-place phase — no new dependencies. Slopcheck gate not exercised.*

## Architecture Patterns

### System Architecture Diagram

```text
                              ┌──────────────────────────────────────┐
                              │   main_iol.py  (driver, Phase 3)     │
                              │                                      │
                              │   require_env("iol-client", [...])   │
                              │           │                          │
                              │           ▼                          │
                              │   probe_login_sync ─┐                │
                              │                     ├─► IOLAuthError │
                              │   probe_login_async ┤    → cascade   │
                              │                     │      SKIPPED   │
                              │           ▼ (auth-once)              │
                              │   probes 3..10 (get_*_sync/async)    │
                              │           │ raw payloads             │
                              │           ▼                          │
                              │   probe_parity_sync_async            │
                              │   probe_field_type_map (schema_of)   │
                              │   probe_schema_snapshot (D-21/D-25)  │
                              │   probe_refresh_token (in-vivo)      │
                              │           ▼                          │
                              │   probe_auth_401 (opt-in, LAST)      │
                              │           ▼                          │
                              │   safe_print SUMMARY (D-IOL-7)       │
                              └─────────┬────────────────────────────┘
                                        │ uses
                ┌───────────────────────┼────────────────────────┐
                ▼                       ▼                        ▼
   ┌──────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
   │ iol_client (sync)    │   │ iol_client.aio      │   │ verification/       │
   │                      │   │ (async)             │   │                     │
   │  _token, _refresh_   │   │  _token, _refresh_  │   │  append_finding()   │
   │   token (NEW), _client│  │   token (NEW), _client│ │  schema_of()        │
   │  login() password    │   │  login() password   │   │  safe_print()       │
   │  _refresh() NEW      │   │  _refresh() NEW     │   │  require_env()      │
   │  _ensure_token       │   │  _ensure_token      │   │  write_findings()   │
   │   (refresh→password) │   │   (refresh→password)│   └─────────────────────┘
   │  get_quote, etc.     │   │  get_quote, etc.    │
   └──────────┬───────────┘   └──────────┬──────────┘
              │ HTTPS                    │ HTTPS
              ▼                          ▼
        ┌────────────────────────────────────────┐
        │   api.invertironline.com               │
        │                                        │
        │   POST /token  (password grant)        │
        │   POST /token  (refresh_token grant)   │
        │   GET  /api/v2/{mercado}/Titulos/...   │
        │   GET  /api/v2/Cotizaciones/{type}/... │
        └────────────────────────────────────────┘
                            │
                            ▼
        ┌────────────────────────────────────────┐
        │   Artifacts (committed)                │
        │                                        │
        │   .planning/verification/              │
        │     iol-client-findings.md             │
        │   .planning/verification/schemas/      │
        │     iol-client/                        │
        │       get-quote.json                   │
        │       get-historical-quotes.json       │
        │       get-instruments.json             │
        │       get-instruments-by-type.json     │
        │                                        │
        │   packages/iol-client/tests/           │
        │     test_client.py                     │
        │       # ------ Verified live ... ------ │
        │       # ------ Regressions ------       │
        │     test_async_client.py (mirror)      │
        └────────────────────────────────────────┘
```

### Recommended Project Structure

No new structure. Phase 3 reuses Phase 2 layout exactly:

```text
market-libs/
├── main_iol.py                       # REWRITTEN: 15 probes (was smoke-test)
├── verification/                     # No changes (already hardened post-Phase 2)
│   ├── findings.py                   #   append_finding (CR-01/CR-02/WR-04 fixed)
│   ├── schema.py                     #   schema_of (primitive)
│   ├── redaction.py                  #   safe_print
│   └── env_gate.py                   #   require_env
├── packages/iol-client/src/iol_client/
│   ├── client.py                     # MODIFIED: + _refresh_token, _refresh(), _ensure_token fallback
│   ├── aio.py                        # MODIFIED: mirror with _token_lock double-check
│   ├── exceptions.py                 # No changes
│   └── __init__.py                   # No changes (refresh state is private)
├── packages/iol-client/tests/
│   ├── conftest.py                   # No changes (autouse fixtures already preload _token)
│   ├── test_client.py                # APPENDED: Verified live (Phase 3) + Regressions sections
│   └── test_async_client.py          # APPENDED: mirror
└── .planning/verification/
    ├── iol-client-findings.md        # GENERATED by driver
    └── schemas/iol-client/           # GENERATED by driver (4 snapshots)
        ├── get-quote.json
        ├── get-historical-quotes.json
        ├── get-instruments.json
        └── get-instruments-by-type.json
```

### Pattern 1: Auth-once with cascade SKIPPED

**What:** Single explicit `login()` at the driver entry; if it raises `IOLAuthError`, set a module-level `_auth_failed: bool = True` and have every downstream probe early-return `ProbeResult(name, "SKIPPED", "auth failed")`. Implementation tactic is Discretion (D-IOL-3); the simplest is a module-level flag.

**When to use:** Driver entry (probes 1, 2). All probes 3-15 check the flag.

**Example:**
```python
# main_iol.py — Discretion implementation (D-IOL-3)
_auth_failed: bool = False
_auth_failure_reason: str = ""


def probe_login_sync() -> ProbeResult:
    global _auth_failed, _auth_failure_reason
    try:
        iol_client.login()
    except IOLAuthError as exc:
        _auth_failed = True
        _auth_failure_reason = f"sync login: {exc}"
        # Don't emit a finding here — the next driver run will retry; this is environmental, not a defect.
        return ProbeResult("login_sync", "FINDING", f"{_next_fid()} (OPEN)")
    return ProbeResult("login_sync", "PASS", "ok")


def probe_get_quote_sync() -> tuple[ProbeResult, dict[str, Any] | None]:
    if _auth_failed:
        return ProbeResult("get_quote_sync", "SKIPPED", f"auth failed: {_auth_failure_reason}"), None
    # ... normal logic
```

[ASSUMED: this is one of three discretion tactics in D-IOL-3; planner can pick. The flag is the simplest, no decorator magic, no import-time side effects.]

### Pattern 2: Refresh path with double-checked locking (async)

**What:** The async `_refresh()` must respect the existing `_token_lock` to avoid thundering-herd. When N concurrent `_request` calls find `_token` expired, only one should acquire the lock and perform the refresh; the others wait, see the freshly-cached token, and proceed.

**When to use:** `aio.py`'s `_ensure_token()` and new `_refresh()` private function.

**Example (verified pattern in existing `aio.py`):**
```python
# packages/iol-client/src/iol_client/aio.py — current pattern (already double-checked):
async def _ensure_token() -> None:
    # First check (lock-free fast path)
    if _token and time.time() < _token_expires_at:
        return
    async with _token_lock:
        # Second check inside lock (avoids thundering herd)
        if _token and time.time() < _token_expires_at:
            return
        await _login_unlocked()


# Phase 3 modification: extend the second-check branch with refresh fallback
async def _ensure_token() -> None:
    if _token and time.time() < _token_expires_at:
        return
    async with _token_lock:
        if _token and time.time() < _token_expires_at:
            return
        if _refresh_token:
            try:
                await _refresh_unlocked()  # NEW: inside the same lock
                return
            except IOLAuthError:
                pass  # fall through to password grant
        await _login_unlocked()


async def _refresh_unlocked() -> str:
    """Caller must hold `_token_lock`. Mirror of `_login_unlocked()`."""
    global _token, _refresh_token, _token_expires_at
    if not _refresh_token:
        raise IOLAuthError(0, "No refresh_token cached")
    client = await _ensure_http_client()
    resp = await client.post(
        f"{_base_url}/token",
        data={"refresh_token": _refresh_token, "grant_type": "refresh_token"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.is_error:
        _raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 900)
    if not isinstance(access_token, str) or not access_token:
        raise IOLAuthError(resp.status_code, "No access_token in refresh response")
    _token = access_token
    # IOL may rotate refresh_token; keep old if response doesn't include new one
    new_refresh = data.get("refresh_token")
    if isinstance(new_refresh, str) and new_refresh:
        _refresh_token = new_refresh
    _token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token
```

[ASSUMED: rotation behavior. Three public IOL wrappers (aairabella/iol-python-api, fedemoglia/iol-api, msap-uai/API-Invertironline) all read `refresh_token` from the password-grant response but don't document whether refresh-grant response also rotates it. The safe path is "accept new if present, keep old otherwise." The IOL Help page (api.invertironline.com/Help/Autenticacion) returns 403 to non-browser fetchers and Context7 has no IOL coverage. **User confirmation needed in discuss-phase: is rotation expected?**]

### Pattern 3: Sync mirror of refresh path

**What:** Sync surface has no locks. The mirror is straight code without `asyncio.Lock`.

**Example:**
```python
# packages/iol-client/src/iol_client/client.py — Phase 3 modification
_refresh_token: str | None = None  # NEW module global (D-IOL-8)


def configure(*, base_url=None, username=None, password=None) -> None:
    global _base_url, _user, _password, _token, _refresh_token, _token_expires_at
    # ... existing field updates ...
    _token = None
    _refresh_token = None   # NEW (D-IOL-8 reset)
    _token_expires_at = 0.0


def login() -> str:
    global _token, _refresh_token, _token_expires_at
    # ... existing POST /token password grant ...
    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")  # NEW (D-IOL-9)
    expires_in = data.get("expires_in", 900)
    if not isinstance(access_token, str) or not access_token:
        raise IOLAuthError(resp.status_code, "No access_token in response")
    _token = access_token
    # D-IOL-9: refresh_token may legitimately be missing; document as finding OPEN AUTH if so.
    # The driver checks `_refresh_token` post-login and emits the finding.
    _refresh_token = refresh_token if isinstance(refresh_token, str) and refresh_token else None
    _token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token


def _refresh() -> str:
    """POST /token with grant_type=refresh_token. Mirror of login() with refresh body."""
    global _token, _refresh_token, _token_expires_at
    if not _refresh_token:
        raise IOLAuthError(0, "No refresh_token cached")
    resp = _client.post(
        f"{_base_url}/token",
        data={"refresh_token": _refresh_token, "grant_type": "refresh_token"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.is_error:
        _raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 900)
    if not isinstance(access_token, str) or not access_token:
        raise IOLAuthError(resp.status_code, "No access_token in refresh response")
    _token = access_token
    new_refresh = data.get("refresh_token")
    if isinstance(new_refresh, str) and new_refresh:
        _refresh_token = new_refresh  # rotation; otherwise keep existing
    _token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token


def _ensure_token() -> None:
    if _token and time.time() < _token_expires_at:
        return
    if _refresh_token:
        try:
            _refresh()
            return
        except IOLAuthError:
            pass  # fall through to password grant (D-IOL-10)
    login()
```

### Pattern 4: Phase 2 driver patterns (inheritance map)

The driver inherits the following patterns from Phase 2 with verified post-review fixes:

| Pattern | Phase 2 source | What it solves | Apply in Phase 3 |
|---------|----------------|----------------|------------------|
| `ProbeResult` dataclass | `main_ambito_financiero.py:89-95` | Per-probe outcome with `name/status/detail` | Copy verbatim |
| `_fid_counter` module global + `_next_fid()` | `main_ambito_financiero.py:74-81` | Sequential `F-NN` IDs | Copy verbatim. IN-01 deferred (not blocking single-run driver). |
| `safe_print(line, secrets=[...])` final loop | `main_ambito_financiero.py:713-723` | Two-pass mask of stdout | Add `[IOL_USER, IOL_PASSWORD, _refresh_token]` to secrets (D-IOL-7) |
| `try/except` around each probe → finding OPEN | All probes in `main_ambito_financiero.py` | D-04 (exit 0 always) | Mirror per probe |
| Typed `exc.status_code` (WR-01 fix) | `main_ambito_financiero.py:585` | `IOLAPIError.__init__` always sets `self.status_code` — never use `exc.args[0]` fallback | Apply in `probe_auth_401` and any exception inspection |
| Single HTTP call per probe (WR-03 fix) | `main_ambito_financiero.py:150-152` | Call `_request` directly; do NOT also call the public wrapper | Apply in all probes 3-10 |
| `contextlib.suppress(Exception)` around `aclose` (IN-03 fix) | `main_ambito_financiero.py:670-671` | D-04 guard: aclose errors must not propagate | Apply in `_async_main` |
| `try/finally` for state mutation (D-15 pattern) | `main_ambito_financiero.py:574-647` (probe_antibot) | Even if probe raises, restore original state | Apply in `probe_auth_401` (D-IOL-2): restore `password=IOL_PASSWORD` |
| Read module-level state directly for diagnostics | `main_ambito_financiero.py:141` (`ambito.client._base_url`) | `base_url` argument to `append_finding` | Apply: `iol_client.client._base_url` |
| Schema snapshot envelope (D-21 + D-25) | `main_ambito_financiero.py:512-548` | Write-on-first-run, no-overwrite-on-drift, finding SHAPE OPEN | Apply per endpoint (4 snapshots, D-IOL-16) |

### Anti-Patterns to Avoid

- **Calling `get_instruments_by_type` then comparing schema.** The wrapper at `client.py:206` does `data.get("titulos", [])`. If the wire stops emitting `"titulos"`, the wrapper returns `[]` and the schema is `[]` — drift invisible. **Always use `_request` directly** in `probe_field_type_map` and capture `resp.json()` raw. (See [Pitfall 2](#pitfall-2-the-titulos-envelope-key-is-swallowed-by-get_instruments_by_type).)
- **Doubling HTTP calls** with `_request` + public wrapper for the same data. WR-03 from Phase 2 review explicitly forbids this — IP-ban risk + stale-snapshot mismatch.
- **`time.sleep`** anywhere in the driver. D-14 / Phase 2 verification confirms `grep -c 'time.sleep' = 0`. Single-shot, no retry, no backoff.
- **Multiple `asyncio.run()` calls.** D-IOL-6 + D-11 Phase 2: one `asyncio.run(_async_main(...))`. Two event loops break `aclose()` semantics on the `_client` singleton.
- **`assert _refresh_token is not None`** as a runtime check. CONCERNS.md: Python's `-O` strips asserts. Use `if _refresh_token is None: raise IOLAuthError(...)`.
- **Resetting `_refresh_token = None` outside `configure()` or `_refresh()` success.** Any other write breaks the singleton invariant and the audit trail.
- **Re-opening the AsyncClient after `aclose()`.** Per CONCERNS.md: if `aclose()` runs then a future probe calls `aio.*`, the lazy `_ensure_http_client()` re-creates it silently. The driver's `_async_main` calls `aclose()` only at the very end (D-IOL-6).
- **Mocking the refresh response with `is_reusable=True`.** This masks the regression "code makes unexpected repeated refresh calls." Use FIFO registration (default) for the 4 IOL-07 tests.
- **Comparing numeric values in `probe_parity_sync_async`.** Price changes between sync and async calls during open market. D-IOL-20: structural only via `schema_of()`.
- **Editing the existing 8 sync + 6 async tests.** D-IOL-21: append the two divider sections at the end; existing tests are pre-Phase-1 and remain untouched.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth refresh path | Custom polling logic, timer thread, sleeps | `_ensure_token()` lazy-check fallback (D-IOL-10) | Project pattern is lazy refresh on next request; no background tasks |
| Token expiry math | Custom clock | `time.time() + expires_in - _TOKEN_TTL_BUFFER_SECONDS` | Already in `client.py:107`; reuse verbatim |
| Findings markdown writer | Custom string formatting | `verification.findings.append_finding(...)` | Hardened post-Phase-2 (CR-01/CR-02/WR-04); preserves human prose |
| Schema reduction | Custom recursion | `verification.schema.schema_of(payload)` | Single primitive; PII-free by construction (D-IOL-13) |
| Stdout redaction | Manual replace calls | `verification.redaction.safe_print(text, secrets=[...])` | Two-pass: explicit secrets + `Bearer\s+\S+` regex |
| Env var gate | `os.getenv` + ad-hoc print | `verification.env_gate.require_env("iol-client", [...])` | HARN-01 verbatim format; returns bool, driver controls exit |
| Async lock | `threading.Lock` | Existing `asyncio.Lock` already in `aio.py` | Sync surface has no concurrency; async has `_token_lock` + `_client_lock` |
| `_last_business_day` | New function | Copy from `main_ambito_financiero.py:103-108` | D-24 + D-IOL-19 mirror; works for any date arithmetic |
| Date "future" for no-data tests | Custom calendar | `today + dt.timedelta(days=N)` | Phase 2 D-24 already established; not needed for IOL (no no-data probe) |
| Custom URL builder | f-string concat | Existing `_request(method, path, params={...})` | Path templates in client are fine; mirror in tests via `url=...` full string with query params (TESTING.md L113-121) |

**Key insight:** Phase 3 should NOT touch `verification/*.py` — Phase 1 + Phase 2 hardening locked it. All new code lives in `main_iol.py`, `iol_client/client.py` + `aio.py`, and the two test files. The single allowed "new" thing in `verification/` is **using** `append_finding` more, never modifying it.

## Runtime State Inventory

Phase 3 is **not** a rename/refactor phase. It is a verify-and-fix phase with new module-level state (`_refresh_token`). Runtime state worth listing:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — IOL client is stateless besides token cache. No DB, no disk cache. | None |
| Live service config | IOL account: `IOL_USER` / `IOL_PASSWORD` in `packages/iol-client/.env` (gitignored). No external dashboard config touched. | Driver reads from env; no service-side change |
| OS-registered state | None — no scheduled tasks, no systemd, no launchd | None |
| Secrets / env vars | `IOL_USER`, `IOL_PASSWORD` (required); `IOL_BASE_URL` (optional). No rename. New driver references same vars. | None — keys unchanged |
| Build artifacts | `packages/iol-client/src/iol_client/*.py` — auto-reloaded by `uv` on edit. No egg-info or compiled artifacts to invalidate. | None |
| Module-level state (in-process) | NEW: `_refresh_token: str \| None = None` in `client.py` AND `aio.py`. EXISTING: `_token`, `_token_expires_at`, `_user`, `_password`, `_base_url`, `_client`. | `configure()` MUST reset `_refresh_token` to None (D-IOL-8). All tests using autouse `_configure_sync`/`_configure_async` get reset for free. |
| Test fixtures | `packages/iol-client/tests/conftest.py` autouse pre-loads `_token`. Refresh tests in `Regressions` section must `monkeypatch.setattr(iol_client.client, "_token", None)` to force the refresh path. | Existing fixtures stay; refresh tests override per-test. |

**Verified non-impact:** No data migration, no service registration, no secrets rename. The only "carry" is the in-process `_refresh_token` global, fully scoped to the iol-client module.

## Common Pitfalls

### Pitfall 1: Doubling HTTP calls by using both `_request` and the public wrapper

**What goes wrong:** Probe captures raw payload by calling `_request("GET", path)` and then ALSO calls `iol_client.get_quote("GGAL")` to "cross-check the wrapper." Result: every probe doubles its HTTP traffic, and the two responses may differ (mid-tick price update mid-probe).

**Why it happens:** Phase 2 review found this in Ámbito driver (WR-03); the temptation is "verify the wrapper does what we think." But the wrapper is just `data.get(...)` or `resp.json()` — there's no logic worth verifying twice with a live call.

**How to avoid:** WR-03 fix established `resp = iol_client.client._request("GET", path); data = resp.json()` as the only call. Inspect `data` directly. The public wrapper is exercised by the mocked tests in `Verified live (Phase 3)` section.

**Warning signs:** Probe function has both `_request(...)` and `iol_client.<func>(...)` lines. Run count would be 2x what `D-IOL-5` documents (probe count vs HTTP requests in network capture).

### Pitfall 2: The `["titulos"]` envelope key is swallowed by `get_instruments_by_type`

**What goes wrong:** `client.py:206` does `data.get("titulos", [])`. If the wire changes and stops emitting `"titulos"`, the wrapper returns `[]` and the schema snapshot is `[]` — drift undetected.

**Why it happens:** The default-empty fallback in `dict.get(key, default)` is silent. `schema_of([])` returns `[]`; `schema_of({"titulos": [...]})` returns `{"titulos": [...]}` — different schemas, but only the first is observable from outside.

**How to avoid:** **`probe_field_type_map` for `get_instruments_by_type` MUST call `_request` directly**, capture `resp.json()`, and assert `"titulos" in data`. Emit a SHAPE finding OPEN if missing. The schema snapshot for this endpoint must also be of the **raw envelope** `{"titulos": [...]}`, not the unwrapped list.

**Warning signs:** The committed `get-instruments-by-type.json` schema is `[{"simbolo": "str", ...}]` (list-of-dict) instead of `{"titulos": [{"simbolo": "str", ...}]}` (dict-wrapping-list). If you see the unwrapped form, the probe is using the wrapper, not `_request`.

```python
# CORRECT — probe_field_type_map sub-routine for IOL-04
def probe_field_type_map_envelope_check() -> ProbeResult:
    resp = iol_client.client._request("GET", "/api/v2/Cotizaciones/acciones/argentina/Todos")
    data: dict[str, Any] = resp.json()  # capture raw envelope
    if "titulos" not in data:
        fid = _next_fid()
        append_finding(
            "iol-client", fid=fid, class_="SHAPE", surface="both", status="OPEN",
            title="missing envelope key 'titulos' in get_instruments_by_type",
            expected="dict with key 'titulos' (list[dict])",
            actual=f"keys={sorted(data.keys())}",
            diff="client.py:206 does data.get('titulos', []) — silently returns [] when missing",
            base_url=iol_client.client._base_url,
        )
        return ProbeResult("field_type_map_envelope", "FINDING", f"{fid} (OPEN)")
    return ProbeResult("field_type_map_envelope", "PASS", "envelope present")
```

### Pitfall 3: Refresh response without rotation breaks subsequent refreshes

**What goes wrong:** IOL refresh response may or may not include a new `refresh_token`. If the code does `_refresh_token = data["refresh_token"]` unconditionally and the server doesn't rotate, this raises KeyError. If you do `_refresh_token = data.get("refresh_token")` unconditionally, you set it to `None` on no-rotation, breaking the next refresh.

**Why it happens:** OAuth 2.0 spec section 1.5 says refresh responses "MAY include a new refresh token" (RFC 6749). IOL behavior is undocumented in public sources.

**How to avoid:**
```python
# In _refresh() (sync) and _refresh_unlocked() (async):
new_refresh = data.get("refresh_token")
if isinstance(new_refresh, str) and new_refresh:
    _refresh_token = new_refresh
# else: keep existing _refresh_token
```

**Warning signs:** A second refresh attempt raises `IOLAuthError(0, "No refresh_token cached")` even though the first refresh succeeded.

[ASSUMED: rotation behavior. **Discuss-phase user confirmation needed**: should the driver emit a finding if rotation is observed (i.e., new refresh_token differs from old)?]

### Pitfall 4: Module-level globals + mypy strict — `_refresh_token: str | None` narrowing

**What goes wrong:** `mypy --strict` flags `global _refresh_token` writes where the local narrow type might be lost. Worse: `_refresh_token` declared at module level as `str | None = None` and then narrowed inside a function via `if _refresh_token: ...` — mypy may not propagate the narrow across the function call boundary.

**Why it happens:** mypy's narrowing only applies within a single function scope. Cross-function narrowing requires assertion or a local copy.

**How to avoid:**
```python
def _refresh() -> str:
    global _token, _refresh_token, _token_expires_at
    refresh_token = _refresh_token  # local copy for narrow propagation
    if not refresh_token:
        raise IOLAuthError(0, "No refresh_token cached")
    # ... use `refresh_token` (the local) in the request body, not `_refresh_token`
    resp = _client.post(
        f"{_base_url}/token",
        data={"refresh_token": refresh_token, "grant_type": "refresh_token"},
        # ...
    )
```

**Warning signs:** mypy errors like `error: Argument "refresh_token" to "dict" has incompatible type "str | None"; expected "str"`. Fix: local copy + narrow.

### Pitfall 5: `pytest-httpx` FIFO consumption across mocked refresh tests

**What goes wrong:** A refresh test mocks two `POST /token` responses (one for password grant, one for refresh grant) but they're matched in registration order regardless of body. If you set up password-grant mock first but the code under test calls refresh first (because `_token` is pre-loaded but `_token_expires_at = 0`), the password mock is consumed for the refresh request.

**Why it happens:** [VERIFIED: docs.colin-b.github.io/pytest_httpx] "the first one not yet sent (according to the registration order) will be sent" — pytest-httpx does NOT discriminate by request body unless you pass `match_content=` or `match_json=`.

**How to avoid:** Either:
- (a) Register mocks in the order the code calls them: refresh-grant response first, password-grant fallback second.
- (b) Use `match_content=` to bind a specific mock to a specific request body:
  ```python
  httpx_mock.add_response(
      url="https://api.test/token",
      method="POST",
      match_content=b"refresh_token=refresh-1&grant_type=refresh_token",
      json={"access_token": "tok-2", "refresh_token": "refresh-2", "expires_in": 900},
  )
  httpx_mock.add_response(
      url="https://api.test/token",
      method="POST",
      match_content=b"username=u&password=p&grant_type=password",
      json={"access_token": "tok-1", "refresh_token": "refresh-1", "expires_in": 900},
  )
  ```
  This binds responses to bodies. Order then doesn't matter for the body discrimination, though registration order still matters if two mocks could match the same body.

**Warning signs:** Test asserts a specific token like `_token == "tok-after-refresh"` but gets `"tok-after-password"`, or vice versa. The mismatch tells you the wrong mock was consumed.

### Pitfall 6: `_token_lock` deadlock if `_refresh()` calls `_ensure_token()` recursively

**What goes wrong:** If the async `_refresh_unlocked()` is implemented inside `_token_lock` AND somewhere in its body calls back into `_ensure_token()` (which tries to acquire the same lock), the task deadlocks. `asyncio.Lock` is not reentrant.

**Why it happens:** During code review someone "helpfully" adds a `_ensure_http_client()` call inside `_refresh_unlocked()` — which is fine because that uses `_client_lock`, not `_token_lock`. But a future helper that wraps "make HTTP request with token" might re-enter `_ensure_token()`.

**How to avoid:**
- `_refresh_unlocked()` (called inside the lock) only does `client.post(...)` directly, never `_request(...)` (which calls `_ensure_token()`).
- Comment the invariant: `# Caller must hold _token_lock.`

**Warning signs:** Async test hangs at the refresh path. Add a `pytest.timeout(5)` marker and investigate the call graph.

### Pitfall 7: Cascade SKIPPED flag persists across re-imports in long-running test session

**What goes wrong:** `main_iol.py` sets `_auth_failed = True` (D-IOL-3) during a probe-13 dry-run. If the driver is imported as a module in a long-running notebook or repeated test run, the flag stays True for run #2.

**Why it happens:** Module-level mutable global; same as IN-01 in Phase 2 (`_fid_counter` deferred).

**How to avoid:** `main()` resets `_auth_failed = False` (and `_fid_counter = 0`) at the top of each invocation. Or scope both to a `RunState` dataclass passed through. Phase 2 deferred this; Phase 3 can also defer if `main()` is invoked once per process — but document it.

**Warning signs:** Notebook re-run shows all probes SKIPPED when nothing changed.

### Pitfall 8: `__future__ annotations` interaction with runtime type checks on `_refresh_token`

**What goes wrong:** With `from __future__ import annotations`, all annotations are strings. `isinstance(_refresh_token, str)` still works at runtime, but `get_type_hints()` (used by `SafeModel.from_api` in higyrus — not iol) requires the type to be resolvable. Not directly an issue for IOL (no SafeModel) but a thing to keep in mind.

**Why it happens:** The annotation `_refresh_token: str | None` is a string at runtime; only `typing.get_type_hints()` resolves it.

**How to avoid:** For IOL we never call `get_type_hints()` on the iol_client module. The narrowing pattern is `isinstance(value, str)` — never relies on annotation resolution. Safe to use `from __future__ import annotations` (required by project, CONVENTIONS.md).

**Warning signs:** Not expected for Phase 3.

### Pitfall 9: IOL lockout policy is unknown — opt-in probe must be true single-shot

**What goes wrong:** IOL almost certainly implements account lockout after N failed login attempts; the exact threshold (N) and window are undocumented in public sources. If `VERIFY_IOL_BAD_CREDS=1` is set and the developer re-runs the driver in a tight loop, the real account gets locked.

**Why it happens:** Best practice (OWASP, Auth0, Okta docs all confirm 3-10 attempts as common thresholds). IOL has not published a number.

**How to avoid:**
- D-IOL-1 + D-IOL-2 + D-IOL-4: probe 401 is OPT-IN (default off), runs LAST, single-shot (no retry, no loop).
- Document in `main_iol.py` docstring: "Each opt-in run consumes 1 failed-login attempt against the real IOL account. Run the probe sparingly and check the IOL dashboard for any lockout alerts."
- The driver MUST NOT default-on this probe in CI or scheduled jobs.

**Warning signs:** After running with `VERIFY_IOL_BAD_CREDS=1` repeatedly, the very next driver run (without the flag) returns `IOLAuthError` from `probe_login_sync`. That means the account is locked. **Stop running the driver until the lockout window expires** (likely 15-60 minutes per industry default).

[LOW confidence: IOL's exact threshold is not in the public docs. The defensive default — opt-in + single-shot + last — already mitigates the unknown.]

## Code Examples

### Auth flow (current, will not change in Phase 3)

```python
# packages/iol-client/src/iol_client/client.py:85-114 — verified current
def login() -> str:
    """Autentica contra POST /token (OAuth password grant) y cachea el token."""
    global _token, _token_expires_at
    if not _user or not _password:
        raise IOLAuthError(0, "IOL_USER y IOL_PASSWORD son requeridos")
    resp = _client.post(
        f"{_base_url}/token",
        data={"username": _user, "password": _password, "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.is_error:
        _raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 900)
    if not isinstance(access_token, str) or not access_token:
        raise IOLAuthError(resp.status_code, "No access_token in response")
    _token = access_token
    _token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token


def _ensure_token() -> None:
    if _token and time.time() < _token_expires_at:
        return
    login()
```

Phase 3 modification adds `_refresh_token` capture + `_refresh()` + fallback in `_ensure_token()` (see [Pattern 3](#pattern-3-sync-mirror-of-refresh-path)).

### pytest-httpx refresh-token test pattern

```python
# packages/iol-client/tests/test_client.py — Regressions section
# Test 1 of 4 per surface (D-IOL-12)


def test_refresh_token_success_path(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: _ensure_token uses cached _refresh_token instead of re-auth (finding F-NN for IOL-07)."""
    # Setup: clear precharged token from conftest autouse, set refresh_token cached.
    monkeypatch.setattr(iol_client.client, "_token", None, raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(iol_client.client, "_refresh_token", "refresh-cached", raising=False)

    # Mock 1: refresh grant succeeds with rotation.
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-cached&grant_type=refresh_token",
        json={"access_token": "tok-after-refresh", "refresh_token": "refresh-rotated", "expires_in": 900},
    )
    # Mock 2: an authenticated endpoint call that follows.
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    payload = iol_client.get_instruments()
    assert payload == {"instrumentos": []}
    assert iol_client.client._token == "tok-after-refresh"
    assert iol_client.client._refresh_token == "refresh-rotated"

    # Verify the password grant was NOT called.
    [token_request, _] = httpx_mock.get_requests()
    assert b"grant_type=refresh_token" in token_request.content
    assert b"grant_type=password" not in token_request.content


def test_refresh_fails_falls_back_to_password(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: refresh 4xx triggers fallback to password grant (finding F-NN for IOL-07)."""
    monkeypatch.setattr(iol_client.client, "_token", None, raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(iol_client.client, "_refresh_token", "refresh-stale", raising=False)

    # Mock 1: refresh fails with 400 (typical "invalid_grant").
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-stale&grant_type=refresh_token",
        status_code=400,
        text="invalid_grant",
    )
    # Mock 2: password grant succeeds.
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"username=u&password=p&grant_type=password",
        json={"access_token": "tok-via-password", "refresh_token": "refresh-fresh", "expires_in": 900},
    )
    # Mock 3: the authenticated endpoint.
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    iol_client.get_instruments()
    assert iol_client.client._token == "tok-via-password"
    assert iol_client.client._refresh_token == "refresh-fresh"


def test_refresh_and_password_both_fail(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: refresh 4xx + password 4xx surfaces IOLAuthError (finding F-NN for IOL-07)."""
    monkeypatch.setattr(iol_client.client, "_token", None, raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(iol_client.client, "_refresh_token", "refresh-stale", raising=False)
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-stale&grant_type=refresh_token",
        status_code=400,
    )
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"username=u&password=p&grant_type=password",
        status_code=401,
    )
    with pytest.raises(IOLAuthError) as excinfo:
        iol_client.get_instruments()
    assert excinfo.value.status_code == 401


def test_login_captures_refresh_token(httpx_mock: HTTPXMock) -> None:
    """Regression: login() captures refresh_token from password-grant response (finding F-NN for IOL-07)."""
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={"access_token": "tok-x", "refresh_token": "refresh-captured", "expires_in": 900},
    )
    iol_client.login()
    assert iol_client.client._token == "tok-x"
    assert iol_client.client._refresh_token == "refresh-captured"
```

Async mirror: same tests with `async def test_async_*`, `await aio.get_instruments()`, and `monkeypatch.setattr(aio, "_refresh_token", ...)`.

### Field→type map probe sketch

```python
# main_iol.py — probe_field_type_map (D-IOL-13/14/15)
_ASSUMED_QUOTE_FIELDS: dict[str, str] = {
    "ultimoPrecio": "float",
    "simbolo": "str",
    # ... other fields the callers assume; populate from a known sample at first run
}
_ASSUMED_INSTRUMENTS_BY_TYPE_ENVELOPE: dict[str, str] = {
    "titulos": "list",
}


def probe_field_type_map(
    quote_raw: dict[str, Any] | None,
    historical_raw: list[dict[str, Any]] | None,
    instruments_raw: Any,
    instruments_by_type_raw_envelope: dict[str, Any] | None,
) -> ProbeResult:
    """Compares observed schemas (schema_of) against _ASSUMED_*. Emits SHAPE findings per discrepancy."""
    fids: list[str] = []
    base_url = iol_client.client._base_url

    # 1. get_quote field→type map
    if quote_raw is not None:
        observed = schema_of(quote_raw)
        for key, expected_type in _ASSUMED_QUOTE_FIELDS.items():
            if key not in observed:
                fid = _next_fid()
                append_finding(
                    "iol-client", fid=fid, class_="SHAPE", surface="both", status="OPEN",
                    title=f"missing assumed key '{key}' in get_quote",
                    expected=f"{key}: {expected_type}",
                    actual=f"keys={sorted(observed.keys())}",
                    diff=f"caller code assumes data['{key}'] exists; wire omits it",
                    base_url=base_url,
                )
                fids.append(fid)
            elif observed[key] != expected_type:
                fid = _next_fid()
                append_finding(
                    "iol-client", fid=fid, class_="SHAPE", surface="both", status="OPEN",
                    title=f"type drift on '{key}' in get_quote",
                    expected=f"{key}: {expected_type}",
                    actual=f"{key}: {observed[key]}",
                    diff=f"assumed {expected_type}, observed {observed[key]}",
                    base_url=base_url,
                )
                fids.append(fid)

    # 2. envelope check for get_instruments_by_type — MUST use raw envelope, not unwrapped list
    if instruments_by_type_raw_envelope is not None:
        if "titulos" not in instruments_by_type_raw_envelope:
            fid = _next_fid()
            append_finding(
                "iol-client", fid=fid, class_="SHAPE", surface="both", status="OPEN",
                title="missing envelope key 'titulos' in get_instruments_by_type",
                expected="dict with key 'titulos' (list[dict])",
                actual=f"keys={sorted(instruments_by_type_raw_envelope.keys())}",
                diff="client.py:206 silently returns [] when 'titulos' missing",
                base_url=base_url,
            )
            fids.append(fid)

    # 3. historical, instruments — analogous loops

    if not fids:
        return ProbeResult("field_type_map", "PASS", "all assumed keys present and typed as expected")
    return ProbeResult("field_type_map", "FINDING", ", ".join(f"{f} (OPEN)" for f in fids))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `login()` only stores `access_token` | `login()` ALSO captures `refresh_token`; `_ensure_token` tries refresh before password | Phase 3 (IOL-07) | Password no longer transmitted on every 15-min expiry; reduces lockout risk per CONCERNS.md |
| Probes call `_request` + public wrapper for cross-check | Single `_request` call per probe; assert on raw `resp.json()` | Phase 2 review WR-03 | Halves HTTP traffic to live API; eliminates mid-tick stale-snapshot bug |
| `aclose()` raises bubble up through `asyncio.run` | `aclose()` wrapped in `contextlib.suppress(Exception)` | Phase 2 review IN-03 | Honors D-04 (exit 0 except on crash); cleanup errors are non-fatal |
| Exception status_code via `getattr(exc, "status_code", None) or exc.args[0]` | Direct `exc.status_code` (always set by `IOLAPIError.__init__`) | Phase 2 review WR-01 | Dead-code elimination; the fallback was actually incorrect (it'd compare `int` against `"[403] ..."` string) |
| Driver mocks one response per URL with `is_reusable=True` | FIFO registration + `match_content=` for grant discrimination | Phase 3 refresh tests | Catches regression "code calls refresh twice when it should call once" |

**Deprecated/outdated:**
- Hand-rolled retry loops in `_ensure_token`: never existed in iol-client, never will (out of scope).
- Custom UA spoofing: IOL doesn't anti-bot like Ámbito; no UA hardcoding needed in iol-client.
- Background token-refresh thread: would conflict with the lazy-on-call refresh pattern; never built.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | IOL refresh response MAY include a new `refresh_token` (rotation), not guaranteed | Patterns 2 + 3, Pitfall 3, Code Examples | If rotation IS guaranteed, our code is still safe (we just won't update); if rotation is FORBIDDEN, our code is also safe (we never get a new one to update). Conservative implementation is correct either way. |
| A2 | Cascade SKIPPED tactic uses a module-level `_auth_failed: bool` flag (3 tactics in D-IOL-3 are discretion) | Pattern 1 | If planner picks a different tactic (decorator, early-return per probe), the driver still satisfies D-IOL-3. Mostly cosmetic. |
| A3 | IOL account lockout threshold is < 10 attempts (industry default range) | Pitfall 9 | If threshold is much higher (e.g., 100), the opt-in single-shot probe is still safe — we never approach the limit. If threshold is much lower (3), the probe still respects single-shot per run. No code change needed; documentation matters. |
| A4 | `pytest-httpx` `match_content=bytes` is the correct API for binding mock responses to body content | Pitfall 5, Code Examples | If the API is `match_data=` instead, tests will fail to bind and the planner sees the error during initial implementation. Discovered fast. |
| A5 | The 4 mocked refresh tests per surface (sync + async, 8 total) are enough coverage for IOL-07 | D-IOL-12 | If the planner discovers a 5th edge case (e.g., refresh returns 200 with no access_token), it's added under same section. |
| A6 | The existing `conftest.py` autouse fixture (`_configure_sync`/`_configure_async`) does NOT reset `_refresh_token` — refresh tests must `monkeypatch.setattr(iol_client.client, "_refresh_token", "...")` explicitly | Runtime State Inventory, Code Examples | If we add the reset to `configure()` (D-IOL-8), the fixtures get it automatically. If a test forgets the monkeypatch, the refresh path won't fire and the test fails noisily. Correctable. |
| A7 | `_token_lock` deadlock under recursive `_ensure_token` calls is the right invariant to comment | Pitfall 6 | If a future maintainer adds a recursive call inside `_refresh_unlocked`, the async test hangs (test pytest timeout catches it). Defensive doc comment helps; not blocking. |
| A8 | IOL's `expires_in` defaults to 900 seconds (15 min) | Multiple sections | `client.py:102` reads `data.get("expires_in", 900)` — if IOL changes the value, the code adapts. If IOL omits the field, default works. No risk. |
| A9 | `match_content=` body order is `refresh_token=...&grant_type=...` (alphabetical or insertion?) — pytest-httpx may require exact byte-equal match | Code Examples | If the body order differs from what httpx serializes (`username=...&password=...&grant_type=...` order from a `dict`), the mock won't match. Fix: inspect `httpx_mock.get_requests()[0].content` in a debug run and use the exact bytes. Discovered fast in implementation. |

**Discuss-phase confirmation requested:**
- A1 (refresh rotation): Should the driver EMIT a finding if observed behavior contradicts our assumption ("rotation never happens" or "rotation always happens")?
- A3 (lockout threshold): Should the driver write a warning line to stdout the first time `VERIFY_IOL_BAD_CREDS=1` is set, naming a "max safe re-runs per hour" guideline?

## Open Questions

1. **Does IOL's refresh-grant response rotate the refresh_token?**
   - What we know: The IOL Help page (api.invertironline.com/Help/Autenticacion) returns 403 to non-browser fetchers; Context7 has no IOL coverage; three public wrappers (aairabella/iol-python-api, fedemoglia/iol-api, msap-uai/API-Invertironline) implement only the password grant. WSO2 + OAuth.net cite RFC 6749 §1.5 "MAY include a new refresh token."
   - What's unclear: IOL's exact behavior.
   - Recommendation: Implement defensively (Pitfall 3: `if isinstance(new_refresh, str) and new_refresh: _refresh_token = new_refresh`). The first live run of `probe_refresh_token` (D-IOL-11) will reveal it; emit an INFO finding documenting observed behavior.

2. **What is IOL's failed-login lockout threshold?**
   - What we know: Industry defaults are 3-10 attempts (OWASP, Auth0, Okta).
   - What's unclear: IOL's specific number and window.
   - Recommendation: D-IOL-1 + D-IOL-2 + D-IOL-4 (opt-in + single-shot + LAST) already mitigate the unknown. The Pitfall 9 documentation captures the warning signs.

3. **Does `pytest-httpx` `match_content=` accept `str` or only `bytes`?**
   - What we know: pytest-httpx CHANGELOG mentions `match_content` parameter; docs are sparse on type.
   - What's unclear: Whether `match_content="..."` is auto-encoded to bytes or rejected.
   - Recommendation: Use `bytes` literals (`b"refresh_token=..."`) for safety. First test run will reveal if `str` also works.

4. **Should the schema snapshot for `get_instruments_by_type` reflect the raw envelope or the unwrapped list?**
   - What we know: CONTEXT.md D-IOL-16 says "4 snapshots committeable" — one is for `get-instruments-by-type.json`.
   - What's unclear: Is the schema of the raw `{"titulos": [...]}` envelope, or the unwrapped `[...]`?
   - Recommendation: **The raw envelope** — Pitfall 2 documents why. The unwrapped list hides envelope-key drift. The probe (D-IOL-17) calls `_request` directly to capture the envelope.

5. **Does the autouse `_configure_async` fixture interact safely with refresh-token tests in `test_async_client.py`?**
   - What we know: The fixture awaits `await aio.aclose()` in teardown.
   - What's unclear: If a refresh test creates a new `_client` via `await aio.get_instruments()`, does the teardown's `aclose()` race with anything? Probably not — `asyncio_mode="auto"` runs each test in a fresh event loop instance.
   - Recommendation: Trust the existing pattern (Phase 2 verified 181 tests passing). If a hang appears, add `pytest.timeout(5)` to refresh tests and bisect.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All packages, driver | ✓ (active venv) | 3.12.11 | — |
| uv | env management | ✓ | 0.9.0 | — |
| `httpx` | iol-client | ✓ (locked) | >=0.27 | — |
| `pytest`, `pytest-asyncio`, `pytest-httpx` | tests | ✓ (locked) | per `pyproject.toml` | — |
| `mypy` strict, `ruff` | CI gates | ✓ (locked) | — | — |
| `verification/` package | driver helpers | ✓ (built in Phase 1 + Phase 2) | — | — |
| `.planning/verification/schemas/iol-client/` directory | snapshot writes | Auto-created by `mkdir(parents=True)` in probe | — | — |
| `packages/iol-client/.env` with `IOL_USER`/`IOL_PASSWORD` | live run | ⚠ User must provide (gitignored) | — | If missing: `require_env` prints SKIPPED, driver exits 0 — no fallback needed (HARN-01) |
| Live `api.invertironline.com` reachability | live run | ⚠ External; market hours optional | — | If 5xx or timeout: probe emits ERROR-MAP finding OPEN; driver continues |
| Real IOL account credentials | live run | ⚠ User-provided | — | If invalid: probe_login_sync emits AUTH finding; cascade SKIPPED for all downstream (D-IOL-3) |

**Missing dependencies with no fallback:** none

**Missing dependencies with fallback:** `IOL_USER`/`IOL_PASSWORD` (graceful skip via HARN-01); live API reachability (per-probe error handling continues the run).

## Validation Architecture

Nyquist validation is **enabled** (`workflow.nyquist_validation: true` in `.planning/config.json`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`) + pytest-httpx |
| Config file | `pyproject.toml` (root) `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest packages/iol-client -q` |
| Full suite command | `uv run pytest -q` |
| Type-check command | `uv run mypy verification main_iol.py packages/iol-client/` |
| Lint command | `uv run ruff check verification main_iol.py packages/iol-client/` |
| Format check | `uv run ruff format --check verification main_iol.py packages/iol-client/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| IOL-01 | `login()` succeeds + lazy-auth on first call (sync+async) | unit (mocked) | `uv run pytest packages/iol-client/tests/test_client.py::test_login_obtiene_access_token packages/iol-client/tests/test_async_client.py::test_async_login_obtiene_access_token -x` | ✅ (pre-existing) |
| IOL-01 | `login()` raises `IOLAuthError` on missing creds | unit (mocked) | `uv run pytest packages/iol-client/tests/test_client.py::test_login_falla_sin_credenciales -x` | ✅ (pre-existing) |
| IOL-01 | Live: `iol_client.login()` returns a non-empty access_token against `api.invertironline.com` | manual / driver | `uv run --package iol-client python main_iol.py` → expect `PROBE login_sync: PASS` + `PROBE login_async: PASS` | ❌ Wave 0 (driver rewrite) |
| IOL-02 | URL+query verbatim per endpoint (sync+async) | unit (mocked) | existing 8 sync + 6 async tests + 4 new Verified-live tests per surface | ✅ (8+6 pre-existing); ❌ Wave 0 for new |
| IOL-02 | Live: 4 endpoints return non-empty raw payloads sync+async | manual / driver | `main_iol.py` probes 3-10 emit PASS | ❌ Wave 0 |
| IOL-03 | `schema_of` builds a `dict[str, str]` from raw payload | unit | `uv run pytest verification/` (existing schema_of tests) | ✅ (Phase 1) |
| IOL-03 | Live: `probe_field_type_map` compares observed vs `_ASSUMED_*` and emits findings per discrepancy | manual / driver | `main_iol.py` probe 12; check `.planning/verification/iol-client-findings.md` | ❌ Wave 0 |
| IOL-04 | Mock: `get_instruments_by_type` unwraps `data["titulos"]` | unit (mocked) | `uv run pytest packages/iol-client/tests/test_client.py::test_get_instruments_by_type_extrae_titulos -x` | ✅ (pre-existing) |
| IOL-04 | Mock: numeric field arrives as int/float not str | unit (mocked) | new Verified-live test asserting `isinstance(quote["ultimoPrecio"], (int, float))` | ❌ Wave 0 |
| IOL-04 | Mock: historical path is `YYYY-MM-DD/YYYY-MM-DD/sinAjustar` with day > 12 | unit (mocked) | new Verified-live test with `dt.date(2026, 4, 21)` | ❌ Wave 0 |
| IOL-04 | Live: raw payload of `get_instruments_by_type` contains `"titulos"` key | manual / driver | `main_iol.py` probe 12 envelope sub-check (Pitfall 2) | ❌ Wave 0 |
| IOL-05 | Mock: 401 → `IOLAuthError` with `status_code=401` | unit (mocked) | `uv run pytest packages/iol-client/tests/test_client.py::test_request_propaga_auth_error -x` | ✅ (pre-existing) — but assert `status_code` per IN-05 |
| IOL-05 | Live: opt-in 401 probe with bad creds raises typed exception (single-shot) | manual / driver | `VERIFY_IOL_BAD_CREDS=1 uv run --package iol-client python main_iol.py` → `PROBE auth_401: FINDING F-NN (EXPECTED)` | ❌ Wave 0 |
| IOL-06 | Live: structural parity sync↔async for 4 endpoints | manual / driver | `main_iol.py` probe 11 emits PASS or FINDING SYNC-ASYNC-DRIFT | ❌ Wave 0 |
| IOL-07 | Mock: refresh path used when `_refresh_token` cached and `_token` expired (sync+async) | unit (mocked) | `uv run pytest -k test_refresh_token_success_path -x` | ❌ Wave 0 |
| IOL-07 | Mock: refresh 4xx falls back to password grant (sync+async) | unit (mocked) | `uv run pytest -k test_refresh_fails_falls_back_to_password -x` | ❌ Wave 0 |
| IOL-07 | Mock: both refresh and password 4xx raise `IOLAuthError` (sync+async) | unit (mocked) | `uv run pytest -k test_refresh_and_password_both_fail -x` | ❌ Wave 0 |
| IOL-07 | Mock: `login()` captures `refresh_token` from response (sync+async) | unit (mocked) | `uv run pytest -k test_login_captures_refresh_token -x` | ❌ Wave 0 |
| IOL-07 | Live: `probe_refresh_token` confirms in-vivo that forced expiry triggers refresh path | manual / driver | `main_iol.py` probe 14 emits PASS | ❌ Wave 0 |
| DRIFT-01 mirror | 4 schema snapshots committed; re-run produces "schema sin drift" | manual / driver | `main_iol.py` probe 13 first run writes; second run PASS | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/iol-client -q && uv run mypy packages/iol-client main_iol.py verification && uv run ruff check packages/iol-client main_iol.py verification`
- **Per wave merge:** `uv run pytest -q && uv run mypy . && uv run ruff check . && uv run ruff format --check .` (mirrors Phase 2 wave 3 gate)
- **Phase gate:** Full suite green + driver dry-run sync prints `SUMMARY: PASS=N FAIL=0 SKIPPED=N FINDING=N` (no FAIL ever, per D-04) before `/gsd-verify-work` runs.

### Wave 0 Gaps

- [ ] `main_iol.py` — rewrite from smoke test to 15 probes (D-IOL-5)
- [ ] `packages/iol-client/src/iol_client/client.py` — add `_refresh_token`, `_refresh()`, modify `login()` + `_ensure_token()` + `configure()` (D-IOL-8/9/10)
- [ ] `packages/iol-client/src/iol_client/aio.py` — mirror with `_token_lock` double-check
- [ ] `packages/iol-client/tests/test_client.py` — append `# ------ Verified live (Phase 3) ------` and `# ------ Regressions ------` sections + 4 IOL-04 invariants + 4 IOL-07 regressions
- [ ] `packages/iol-client/tests/test_async_client.py` — mirror sections + 4+4 tests
- [ ] `.planning/verification/iol-client-findings.md` — auto-generated by driver (first run)
- [ ] `.planning/verification/schemas/iol-client/{get-quote,get-historical-quotes,get-instruments,get-instruments-by-type}.json` — auto-generated by driver (first run)
- [ ] (No framework install needed — pytest-httpx + pytest-asyncio already locked)

## Security Domain

Security enforcement is implicit-enabled (no `security_enforcement: false` in config). The phase touches authentication and HTTP — both ASVS-relevant.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | OAuth 2.0 password+refresh grant (RFC 6749 §4.3+§6); credentials via env vars only; lockout-aware probe (D-IOL-1) |
| V3 Session Management | yes | Tokens in module globals; 15-min TTL with 60s pre-expiry buffer; `configure()` resets cache; never logged |
| V4 Access Control | n/a | Single-tenant client library; no authorization beyond "valid token" |
| V5 Input Validation | partial | `isinstance(access_token, str)` and `isinstance(data, dict)` guards in `login()`; the field→type map probe (D-IOL-13) IS structural validation against an in-memory assumption set |
| V6 Cryptography | n/a | TLS handled by `httpx`; we never roll our own crypto |
| V7 Error Handling | yes | Typed `IOLAuthError`/`IOLRateLimitError`/`IOLAPIError`; `safe_print` masks tokens/passwords (D-IOL-7, D-IOL-22) |
| V14 Configuration | yes | `.env` per package (gitignored); `.env.example` is the template; `IOL_BASE_URL` opt-in override |

### Known Threat Patterns for IOL Client Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Account lockout from repeated bad-creds | Denial of Service against self | D-IOL-1 (opt-in) + D-IOL-2 (try/finally restore) + D-IOL-4 (last in sequence) + Pitfall 9 docs |
| Token exposure via stdout / logs | Information Disclosure | `safe_print(text, secrets=[IOL_USER, IOL_PASSWORD, _refresh_token])` (D-IOL-7) + `_BEARER` regex fallback in `redaction.py` |
| Token theft via process memory | Information Disclosure | Module globals — same risk as `_user`/`_password`. CONCERNS.md L45-49: accepted for CLI use; revisit if running multi-tenant web framework. |
| Replay of stale `refresh_token` | Spoofing | If IOL invalidates on use (rotation), our code captures the new one. If IOL allows multi-use, that's IOL's policy — not the client's threat to mitigate. |
| MITM on `/token` endpoint | Tampering | `httpx` enforces TLS by default for `https://`; `_base_url` defaults to `https://api.invertironline.com`. No HTTP fallback. |
| Cross-process credential leak via globals | Information Disclosure | Out of scope per PROJECT.md (refactor to instance-scoped client deferred); credentials live in env, not in code |
| Path traversal in findings file slug | Tampering | Already mitigated post-Phase 2 (WR-04): `_validate_pkg_slug("iol-client")` rejects path-traversal inputs |
| `assert _token is not None` stripped under `-O` | Tampering | CONCERNS.md L51-55: not blocking; documented. Phase 3 follows same pattern (no `assert` for runtime invariants in new code where possible — use `if _refresh_token is None: raise IOLAuthError(...)` instead) |

## Sources

### Primary (HIGH confidence)

- **CONTEXT.md** (`.planning/phases/03-iol-verification/03-CONTEXT.md`) — 22 locked decisions D-IOL-1..22, canonical refs, code context, specifics, deferred ideas. The authoritative source for Phase 3 scope.
- **Phase 2 outputs:**
  - `.planning/phases/02-mbito-verification/02-CONTEXT.md` — D-01..D-26 lifecycle (driver structure, append_finding, schema envelope, Verified-live + Regressions sections)
  - `.planning/phases/02-mbito-verification/02-REVIEW.md` — CR-01 (prose preservation), CR-02 (single-line title), WR-01 (typed status_code), WR-03 (single HTTP per probe), WR-04 (pkg slug validation), IN-03 (contextlib.suppress)
  - `.planning/phases/02-mbito-verification/02-VERIFICATION.md` — verified Phase 2 driver pattern works (181 passed, exit 0, schema sin drift)
- **Existing iol-client code:**
  - `packages/iol-client/src/iol_client/client.py` — current sync surface (`login`, `_ensure_token`, `_request`, 4 endpoints; refresh_token NOT captured)
  - `packages/iol-client/src/iol_client/aio.py` — current async surface with `_token_lock`, `_client_lock`, double-checked locking in `_ensure_token`, `_login_unlocked`
  - `packages/iol-client/src/iol_client/exceptions.py` — `IOLAPIError.__init__` always sets `self.status_code = status_code` (confirms WR-01 mirror applies)
  - `packages/iol-client/tests/conftest.py` — autouse `_configure_sync`/`_configure_async` pre-loading `_token`, providing test isolation pattern
  - `packages/iol-client/tests/test_client.py`, `test_async_client.py` — 8 + 6 existing mocked tests, the pattern to extend
- **Phase 2 reference driver:** `main_ambito_financiero.py` — 7 probes implementing the verified WR-01/WR-03/IN-03 patterns
- **Harness:**
  - `verification/findings.py` — hardened `append_finding(...)` (CR-01/CR-02/WR-04)
  - `verification/schema.py` — `schema_of(payload)` primitive (D-IOL-13)
  - `verification/redaction.py` — `safe_print(text, secrets)` two-pass mask
  - `verification/env_gate.py` — `require_env(pkg, [vars])` for HARN-01
- **Project constraints:** `CLAUDE.md`, `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/TESTING.md` (pytest-httpx pattern + autouse fixtures)
- **pytest-httpx docs (verified):** [colin-b.github.io/pytest_httpx](https://colin-b.github.io/pytest_httpx/) confirms FIFO registration-order matching and `is_reusable`/`can_send_already_matched_responses` semantics
- **REQUIREMENTS.md** §"Verificación iol-client (IOL)" — IOL-01..07 verbatim

### Secondary (MEDIUM confidence)

- **`.planning/codebase/INTEGRATIONS.md`** — IOL OAuth password grant + endpoints + env vars
- **`.planning/codebase/CONCERNS.md`** — explicit "iol sync client does not use the `refresh_token`" tech debt entry (CONCERNS.md L25-29 confirms IOL-07 scope) + "Module-level global state" + "Credentials exposed in module-level string variables" + "assert statements stripped under -O"
- **`.planning/ROADMAP.md`** §"Phase 3: IOL Verification" — 5 success criteria
- **Search-corroborated IOL OAuth wire details:**
  - [iol-python-api source](https://github.com/aairabella/iol-python-api/blob/master/get_token.py) — confirms `Content-Type: application/x-www-form-urlencoded` + body `username=...&password=...&grant_type=password`
  - [fedemoglia/iol-api](https://github.com/fedemoglia/iol-api) — same body format
  - Multiple WebSearch results agree on: `POST /token` with `refresh_token=<value>&grant_type=refresh_token` body, `application/x-www-form-urlencoded`, response includes `access_token + refresh_token + expires_in`

### Tertiary (LOW confidence)

- **IOL Help page** ([api.invertironline.com/Help/Autenticacion](https://api.invertironline.com/Help/Autenticacion)) — returns 403 to non-browser fetchers; cannot directly verify wire payload format. Cross-referenced via 3 third-party wrappers above (MEDIUM via convergence).
- **IOL lockout threshold** — no public documentation. Industry defaults (OWASP, Auth0) 3-10 attempts. Defensive design (D-IOL-1 opt-in + single-shot) makes the exact threshold not load-bearing for the phase.
- **IOL refresh_token rotation behavior** — RFC 6749 §1.5 "MAY include a new refresh token". IOL behavior not documented. Defensive code (Pitfall 3) handles both rotation and no-rotation. First live run of `probe_refresh_token` (D-IOL-11) will reveal it.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages already pinned in `uv.lock`, no new deps
- Architecture: HIGH — mirrors Phase 2 lifecycle which is fully verified (181 passed, 10/10 truths in 02-VERIFICATION.md)
- Pitfalls: HIGH (1, 2, 4, 5, 6, 7) for Phase-2-inherited patterns; MEDIUM (3) for IOL refresh wire; MEDIUM-LOW (9) for IOL lockout policy
- IOL OAuth refresh wire format: MEDIUM — verified via convergence of 3 public wrappers + IOL Help page heading; not via direct documentation
- IOL lockout policy: LOW — no public threshold; defensive single-shot + opt-in mitigates

**Research date:** 2026-06-06
**Valid until:** 2026-07-06 (30 days for stable monorepo with stable IOL API; re-verify if IOL announces auth changes or if pytest-httpx releases a breaking change in matching semantics)
