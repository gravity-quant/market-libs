# Phase 20: Scaffold + Auth0 client-credentials + fundaciones de transporte - Context

**Gathered:** 2026-07-29 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Levantar el paquete `market-data-client` (import `market_data_client`, dist `market-data-client`)
espejando la estructura de `iol-client`, con **autenticación Auth0 client-credentials** (token cache
TTL + refresh, dual sync/async) y las **fundaciones de transporte** (retries full-jitter, logging
redactado, jerarquía de excepciones tipadas, `configure()`, endpoints de health). Primera fase del
milestone v1.4 (AUTH-MD-01, CORE-MD-01).

**Fuera de alcance en esta fase** (fases posteriores o v1.5+): endpoints de market data y reference
data (Phases 21-22), modelos `SafeModel` de respuesta, verificación en vivo (Phase 23), release
(Phase 24), y —diferido a v1.5+— cache de token en disco, validación de firma JWT, mutaciones,
streaming SSE, y el patrón `with_options(max_retries=N)` (queda para Phase 21).
</domain>

<decisions>
## Implementation Decisions

### Module Decomposition & File Set
- **D-01:** Espejar el layout de módulos privados de `iol-client`: `_core.py` (builders/parsers puros
  de Auth0 + `raise_for_response` + chequeo de frescura de token), `_state.py` (`_ClientState`
  dataclass no-frozen, `slots=True`), `_transport.py` / `_atransport.py`, `_logging.py`, `client.py`
  (sync), `aio.py` (async), `exceptions.py`, `__init__.py` (`__all__` + `__version__="0.1.0"`),
  `py.typed`. Más `.env.example`, `README.md`, `tests/`.
- **D-02:** **OMITIR `_token_cache.py`** — el cache de token en disco está diferido a v1.5+ (D-04 del
  plan fuente); no se agrega la dependencia `platformdirs`. Deps de runtime del paquete:
  `httpx>=0.27`, `python-dotenv>=1.0`, `tenacity>=9.1,<10` (build: hatchling).
- **D-03:** **NO agregar `models.py` ni `types.py`** en esta fase — los modelos de respuesta
  (`SafeModel` con `received_at`) están agendados para Phases 21/22 (D-05).
- **D-04:** El builder/parser del token Auth0 vive en `_core.py`, junto a `raise_for_response` (mismo
  hogar que iol usa para sus builders/parsers de auth).

### Auth0 client_credentials Token Lifecycle
- **D-05:** Flujo de **grant único** `client_credentials`: en `_core.py`, UN builder
  (`build_token_request`, `grant_type=client_credentials`, form-encoded con `client_id` +
  `client_secret` + `audience`, POST a `MARKET_DATA_AUTH0_TOKEN_URL`) y UN parser
  (`parse_token_response` → `(token, expires_at)`). **Sin** `build_refresh_request`, **sin** campo de
  estado `refresh_token`, **sin** lógica de rotación condicional (CR-01 de iol). Re-autenticar con el
  mismo grant **ES** el refresh.
- **D-06:** `_ensure_token()` re-corre el grant `client_credentials` cuando el token cacheado está
  stale. TTL derivado de la respuesta: `expires_at = time.time() + expires_in - buffer` con
  `buffer ≈ 60s` (constante `_TOKEN_TTL_BUFFER_SECONDS`, espejando iol `_state.py`).
- **D-07:** **Fallback cuando `expires_in` está ausente = ~1 hora (3600s).** Punto medio conservador
  (no el 900s de iol, que dispararía re-auth horaria innecesaria sobre tokens Auth0 de ~24h; tampoco
  falla ruidosamente). Sólo aplica al caso de campo ausente; el caso normal siempre deriva de
  `expires_in`.

### Health Endpoints (anonymous path)
- **D-08:** `GET /health` y `GET /health/feed` requieren un **camino de request no autenticado**: sin
  header `Authorization` y **sin** disparar `_ensure_token()`.
- **D-09:** Implementación mediante una **flag `authenticated: bool = True` en el request spec
  interno** — health pasa `authenticated=False` para saltar la inyección del token. Un solo code path
  (no un helper `_request_anonymous` separado), espejado sync/async.

### Transport, Retry, Logging & Concurrency
- **D-10:** Espejar `_transport.py` / `_atransport.py` de iol **verbatim**: set retryable
  (`408/409/429/5xx` + `ConnectError`/`ConnectTimeout`/`ReadTimeout`),
  `wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0)`, cap de `Retry-After` a
  60s, mutation-gate idempotente. Único cambio: `_LOGGER_NAME = "market_data_client"`.
- **D-11:** `_logging.py` reutiliza la estructura `RedactingFilter` / `attach()` de iol, pero **cambia
  los patrones de credencial**: redactar `Bearer` / `access_token` (JSON) **más `client_secret`**
  (body form-encoded del token + JSON). Cero fugas de credencial en logs es gate de CORE-MD-01.
- **D-12:** Concurrencia con el patrón per-loop **`asyncio.Lock` double-checked** de iol
  (`aio.py`) — **NO** el `TokenStore` de matriz (ese está scopeado a concurrencia 3-way con el daemon
  thread de WebSocket, diferido acá). **Sin** decorador `RefreshPolicy` fail-cache en esta fase.

### Env Vars & Exceptions
- **D-13:** `.env.example` con: `MARKET_DATA_CLIENT_ID`, `MARKET_DATA_CLIENT_SECRET`,
  `MARKET_DATA_AUDIENCE`, `MARKET_DATA_AUTH0_TOKEN_URL`, `MARKET_DATA_BASE_URL` (default
  `https://market-data-develop.bbsa.com.ar/api`).
- **D-14:** Jerarquía de excepciones: `MarketDataError → MarketDataAPIError → MarketDataAuthError`,
  `MarketDataRateLimitError`. Mapeo en `raise_for_response`: 401/403→Auth, 429→RateLimit, otros
  errores→APIError.

### Claude's Discretion
- Nombres exactos de constantes/funciones internas dentro del patrón iol (mientras respeten las
  convenciones de naming del monorepo).
- Estrategia concreta de tests dentro de lo requerido por los success criteria: mock del endpoint de
  token Auth0 (pytest-httpx), test de refresh por expiración de TTL en sync + async, test de
  redacción con `caplog`, smoke de health.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.future_plans/market_data.md` — plan fuente del milestone v1.4 con las D-locks (D-01..D-07) y la
  superficie completa de la API primary-extractor.
- `.planning/REQUIREMENTS.md` — AUTH-MD-01, CORE-MD-01 (criterios de aceptación de esta fase).
- `.planning/ROADMAP.md` § "Phase Details (v1.4)" → Phase 20 (success criteria).
- `packages/iol-client/src/iol_client/` — paquete plantilla a espejar (`_core.py`, `_state.py`,
  `_transport.py`, `_atransport.py`, `_logging.py`, `client.py`, `aio.py`, `exceptions.py`,
  `__init__.py`, `pyproject.toml`, `tests/`). **Espejar el layout; NO copiar** `_token_cache.py` ni la
  máquina de refresh_token.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`iol-client` como plantilla completa** (`packages/iol-client/src/iol_client/`): layout de módulos,
  `_ClientState` (`_state.py`, dataclass no-frozen `slots=True`), `RetryTransport` full-jitter
  (`_transport.py:54-61` constantes), `RedactingFilter` + `attach()` (`_logging.py`), patrón
  `asyncio.Lock` double-checked (`aio.py`), y `raise_for_response` + builders/parsers en `_core.py`.
- **`pyproject.toml` de iol** como base para el del nuevo paquete (hatchling, `py.typed`), **restando**
  `platformdirs` (diferido).
- **Convenciones de tests** de iol (`conftest.py`, fixtures pytest-httpx, tests de redacción y de
  ciclo de refresh sync/async) como molde para los tests de Phase 20.

### Established Patterns
- **Sin código compartido entre paquetes** (por diseño): toda la lógica de auth/transport/logging se
  duplica dentro de `market-data-client`; no se introducen dependencias cruzadas.
- **Dual sync/async**: cualquier lógica se espeja en `client.py` y `aio.py`; estado singleton a nivel
  de módulo por superficie.
- **Auth lazy**: token obtenido en la primera llamada, cacheado, refrescado antes de expirar.
- `configure()` como único punto de mutación controlada del estado (credenciales + base URL), que
  resetea el token cacheado.

### Integration Points
- **Auth0 client_credentials** difiere del grant password/refresh de iol: es de grant único (sin
  `refresh_token`), por lo que se elimina la mitad de la maquinaria de auth de iol.
- **Health sin auth**: nuevo camino de request anónimo (flag `authenticated=False`) que no existe en
  iol —iol autentica todas sus llamadas—.
- **CI matrix** (`ci.yml`) y el pipeline de release por tag `*-client-v*` se tocan en Phase 24, no
  acá; pero el nombre `market-data-client` ya debe respetar el regex del release.
</code_context>

<specifics>
## Specific Ideas

- **Fallback de TTL = 3600s** (~1 hora) elegido explícitamente por el usuario sobre las alternativas
  900s (iol) y "fallar ruidosamente".
- **Health anónimo vía flag `authenticated: bool`** en el request spec (elegido sobre un helper
  `_request_anonymous` separado): un solo code path, menos duplicación.
</specifics>

<deferred>
## Deferred Ideas

- `_token_cache.py` (cache de token en disco + `platformdirs`) y validación de firma JWT → v1.5+.
- `models.py` / `types.py` con `SafeModel` de respuesta → Phases 21/22.
- `with_options(max_retries=N)` (clon shared-view, patrón Phase 13) → Phase 21.
- Máquina de `refresh_token` / rotación condicional (CR-01) → N/A para client_credentials (no aplica).
- Endpoints de market data / instruments / symbols / calendar → Phases 21-22.
- Streaming SSE `GET /marketdata/stream`, mutaciones (symbols/calendar) → v1.5+.

### Reviewed Todos (not folded)
None — no pending todos matched this phase.
</deferred>
