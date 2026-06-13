# Phase 10: matriz `aio.py` Creation + TokenStore - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 10 entrega la superficie async REST completa de `matriz-client` espejando
`client.py`, más el `TokenStore` 3-way concurrent que coordina compartición de
token entre 3 callers (sync REST + async REST + `ws_client.py` daemon thread).
La superficie async no duplica builders/parsers — usa el `_core.py` que dejó
Phase 7. Phase 10 también ship el `_atransport.py` que Phase 8 dejó carve-out
(D-25) para evitar tech debt premature.

**Entregables atómicos:**

1. **`packages/matriz-client/src/matriz_client/aio.py` — full REST mirror.**
   `AsyncClient` con las 22 signatures de `client.Client`: lifecycle
   (`__init__`/`aclose`/`__aenter__`/`__aexit__`/`__repr__`), auth
   (`login`/`_ensure_token`/`_risk_auth`), 22 endpoints (`get_segments`,
   `get_all_instruments`, `get_instruments_details`, `get_instrument_detail`,
   `get_instruments_by_cfi`, `get_instruments_by_segment`, `new_order`,
   `replace_order`, `cancel_order`, `get_order_status`, `get_order_history`,
   `get_active_orders`, `get_filled_orders`, `get_all_orders`,
   `get_order_by_exec_id`, `get_market_data`, `get_trades`, `get_positions`,
   `get_detailed_positions`, `get_account_report`). 22 module-level
   `async def` delegators que invocan `_get_default().<method>()`. Estado
   async independiente del sync via `_default_async_client._state`. PEP 562
   shim back-compat (`aio._token`, `aio._base_url`, etc. forwardeados a
   `_get_default()._state.*`).

2. **`packages/matriz-client/src/matriz_client/_token_store.py` (NEW)** —
   `TokenStore` class + `build_token_store(state, *, max_retries, fail_cache_s=30.0)`
   factory. Pattern: Double-Checked Locking — `threading.Lock` para state
   mutations (cross-loop atomic) + per-loop lazy `asyncio.Lock` para herd
   prevention intra-loop + refresh corre dentro de `asyncio.to_thread()`
   para no bloquear el event loop > 5ms. `ttl_seconds = 23 * 3600`
   (matriz token).

3. **`packages/matriz-client/src/matriz_client/_refresh_policy.py` (NEW)** —
   `RefreshPolicy(max_retries, base_backoff_s, max_backoff_s, jitter,
   fail_cache_s)` decorator que envuelve un `refresh_fn`. Lógica:
   classification por exception type → `PermanentRefreshError` propaga
   inmediato sin retry; `TransientRefreshError` retry con exp backoff +
   jitter hasta `max_retries`; `RateLimitedRefreshError` respeta
   `retry_after_seconds`; cuando se exhausta el retry budget, cachea la
   última exception por `fail_cache_s` segundos (DOS prevention al auth
   server). Permanent errors NO se fail-cachean.

4. **`packages/matriz-client/src/matriz_client/_refresh.py` (NEW)** —
   `MatrizRefresh(http_client, base_url, username, password)` adapter
   pluggable que ejerce el endpoint de login y mapea httpx exceptions →
   `RefreshError` subclasses. Adapter es el contrato pluggable: future
   paquetes (iol con OAuth, ámbito sin auth) implementarían su propio
   adapter sin tocar `RefreshPolicy`/`TokenStore`.

5. **`packages/matriz-client/src/matriz_client/_refresh_errors.py` (NEW)** —
   `PermanentRefreshError`, `TransientRefreshError`, `RateLimitedRefreshError`
   exception hierarchy. `RateLimitedRefreshError.retry_after_seconds`
   carries el valor del `Retry-After` header.

6. **`packages/matriz-client/src/matriz_client/_atransport.py` (NEW)** —
   `AsyncRetryTransport` mirror del Phase 8 `_transport.RetryTransport`
   pero sobre `httpx.AsyncHTTPTransport` + `tenacity.AsyncRetrying`. Pattern
   ya establecido en `packages/iol-client/src/iol_client/_atransport.py`
   (intra-package imports de constants `_RETRYABLE_STATUS`, `_RETRYABLE_EXC`,
   etc. desde el sync `_transport.py`). Phase 8 D-25 carve-out cerrado.

7. **`packages/matriz-client/src/matriz_client/_state.py` (MODIFY)** —
   Agregar campo `token_store: TokenStore | None = None`. NO se toca el
   campo `account_id: str | None` muerto (ORP-01 — Phase 11 CR-08 scope).
   NO se toca el resto del schema (`base_url`, `username`, `password`,
   `token`, `token_expires_at`, `http_client`).

8. **`packages/matriz-client/src/matriz_client/ws_client.py` (MODIFY mínimo)** —
   Reemplazar el actual `_rest._get_default()._ensure_token()` por
   `state.token_store.get_sync()`. NO se re-arquitecta el daemon-thread
   loop; NO se cambia el WebSocket lifecycle. PEP 562 shim
   (`matriz_client.client._token`) sigue funcionando como red de seguridad
   para callers legacy.

9. **`packages/matriz-client/src/matriz_client/client.py` (MODIFY mínimo)** —
   Sync `Client._ensure_token()` migra a `state.token_store.get_sync()`.
   `_get_default()` instancia `token_store` lazy via `build_token_store(state, ...)`.

10. **`main_matriz.py` (EXTEND)** — Probes async mirror para cada probe sync
    relevante; mismo patrón de `main_iol.py` (probes sync + async interleaved
    en el mismo `main()`, sin flag). Outcome reporting paridad sync↔async.
    LIVE-02 satisfecho cuando el async run reproduce el mismo set de
    PASS/FINDING/SKIPPED que el sync.

**Tests:**

- `packages/matriz-client/tests/test_token_store.py` (NEW) — Unit + stress:
  - 1 refresh ante N callers concurrentes (sync + async + simulated daemon)
  - Cross-loop atomicity (multi-event-loop scenario)
  - `asyncio.to_thread` libera el event loop > 5ms budget
  - Token TTL expiration triggers refresh
  - Fail-cache prevents auth-server DOS (10 concurrent callers post-failure → 0 new auth hits)
  - Permanent errors NO se cachean (retry-able después de credential update)
- `packages/matriz-client/tests/test_refresh_policy.py` (NEW) — Unit:
  - Classification por exception type
  - Exp backoff + jitter envelope
  - Retry-After honored para `RateLimitedRefreshError`
  - Retry budget exhaustion → fail-cache trigger
- `packages/matriz-client/tests/test_async_client.py` (NEW) — Mirror sync
  endpoints con pytest-httpx + pytest-asyncio. Sigue patrón
  `packages/iol-client/tests/conftest.py` (autouse `_configure_async`
  fixture que aterriza pre-issued token).
- `packages/matriz-client/tests/test_fixture_reaches_production.py`
  (MODIFY) — El 1 skip permanente que apunta a "Phase 10 REFAC-04 +
  TokenStore" flipea a active test.
- `verification/test_async_cancellation.py` (MODIFY) — Skip permanente
  que apunta a Phase 10 flipea a active test.
- `verification/test_sync_async_isolation.py` (MODIFY) — Skip permanente
  que apunta a Phase 10 flipea a active test (cross-leak sentinel cubre
  matriz async ahora).

**Carry-forward Phase 6-9 (NO re-discutido, locked):**

- **Per-package serial pattern** (Phase 6 D-05 / Phase 7 D-13 / Phase 8 D-21 /
  Phase 9 D-11): Phase 10 es matriz-only — ámbito/iol/higyrus ya tienen
  `aio.py` y no se tocan.
- **1 commit atómico por plan**: Phase 6/7/8/9 idiom.
- **Snapshot público (Phase 6 D-09)**: matriz public API CRECE (AsyncClient
  + 22 module-level async delegators). Plan green-gate REGENERA el
  snapshot — el diff es esperado y deseado. NO debe regenerar para
  ámbito/iol/higyrus (zero diff esperado ahí).
- **`from __future__ import annotations` mandatory** en cada archivo nuevo.
- **Import-linter contracts** (Phase 7 D-09): `aio.py` puede importar de
  `_core.py` (allowed direction). `_core.py` NO puede importar de
  `aio.py`/`client.py` (forbidden, enforced). Phase 10 respeta esto.
- **Cross-leak sentinel test** (Phase 7 D-10 — `verification/test_sync_async_isolation.py`):
  el sentinel ya separa sync↔async state via per-instance `_ClientState`.
  Phase 10 lo extiende al async path nuevo de matriz.
- **`_state` per-instancia** (Phase 6 D-IOL-09 idiom): `AsyncClient._state`
  es independiente del `Client._state` aunque sean el mismo módulo.
  TokenStore se monta sobre `_state.token_store` per-instance.
- **Mutation gate** (Phase 8 D-15 / D-24): `new_order`/`cancel_order`/
  `replace_order` siguen siendo `idempotent=False` en `RequestSpec` y
  pasan por `AsyncRetryTransport` sin retry. Pitfall 4 NO regresses.
- **RedactingFilter** (Phase 8 LOG-02): el `_logging.py` per paquete sigue
  cubriendo los nuevos call sites async (regex patterns se aplican al
  package logger, transport agnostic).
- **D-25 carve-out cerrado** — Phase 8 dejó `_atransport.py` matriz ABSENT
  intencionalmente. Phase 10 lo crea (matriz only — los otros 3 paquetes
  ya tienen `_atransport.py`).
- **PEP 562 shim back-compat**: `aio._token`, `aio._base_url`,
  `aio._token_expires_at`, etc. siguen forwardeados a
  `_get_default()._state.*` para no romper callers legacy. NO se agregan
  attributos al `_DENIED_LEGACY` set en Phase 10.
- **NO tocar `_state.py:55 account_id`** (ORP-01) — Phase 11 CR-08 scope.

**Phase 10 NO entrega:**

- **HARN-07..10, CR-01..08, LIVE-01** — Phase 11 territory (full 4-package
  live re-verification + harness hardening).
- **prod-vs-remarkets** (D-MATZ-27): defer a v1.2 explicit; v1.1 sigue
  remarkets-only.
- **WebSocket live verification**: `ws_client.py` daemon-thread NO se
  verifica live ni se refactoriza más allá del `_ensure_token()` swap.
- **iol async TokenStore migration**: iol ya tiene `_state.token` +
  `_ensure_token()` async con `token_lock` double-checked desde Phase 6;
  el patrón conceptualmente compatible con TokenStore pero no se
  refactoriza (no hay 3-way pressure: iol no tiene daemon thread).
  Defer a v1.2 si emerge.
- **Disk persistence del token matriz** — los procesos siguen re-login
  on restart; spike-findings cubre solo in-memory in-process.
- **Generated-code dual-emit (sync/async desde un mismo source)** — defer
  a v1.2 (REQUIREMENTS Future Requirements).
- **`Client(account_id=X)` constructor pattern** — Phase 9 D-08 lo defer
  a v1.2.

</domain>

<decisions>
## Implementation Decisions

### Module layout (TokenStore + RefreshPolicy + adapter + errors)

- **D-01: 4 archivos nuevos para máxima cohesión + 1 modify a `_state.py`.**

  | File | Responsibility | Est. LOC |
  |------|---------------|----------|
  | `_token_store.py` | `TokenStore` class + `build_token_store()` factory + Double-Checked Locking impl | ~120 |
  | `_refresh_policy.py` | `RefreshPolicy` decorator: retry + exp backoff + jitter + fail-cache | ~80 |
  | `_refresh.py` | `MatrizRefresh` adapter: httpx → token, maps exceptions a RefreshError subclasses | ~60 |
  | `_refresh_errors.py` | `PermanentRefreshError`, `TransientRefreshError`, `RateLimitedRefreshError` hierarchy | ~30 |
  | `_state.py` (modify) | `+1 field: token_store: TokenStore \| None = None` | +1 |

  Justificación: convention `_*.py` chico-y-focused ya establecida en
  matriz (`_core.py` 924, `_state.py` 55, `_transport.py` 239, `_logging.py`
  small). Separar adapter de errors de policy de store mantiene
  testability per-archivo + import-linter contracts más simples.
  Alternativas rechazadas: 3 archivos (errors inline en `_refresh.py`)
  pierde la separación pluggable adapter/errors; 1 archivo concentrado
  hace `_token_store.py` ~290 LOC y mezcla 4 concerns.

- **D-02: TokenStore vive en `_token_store.py`, NO en `_state.py`.**

  ROADMAP literal Phase 10 Success #2: "TokenStore (en `_state.py` o
  `_token_store.py`)". Operator decision: `_token_store.py`. Justificación:
  `_state.py` queda chico (singleton-state container only); `_token_store.py`
  encapsula la primitiva de concurrencia con su test suite dedicada.
  `_state.token_store: TokenStore | None = None` field es el bridge.

### Policy knob exposure (public API)

- **D-03: Solo `max_retries` expuesto en `configure()` + `AsyncClient.__init__`.**

  Phase 8 ya expone `max_retries` en `matriz_client.configure(max_retries=N)`
  y `Client(max_retries=N)`. Phase 10 reusa ese mismo knob — el
  `RefreshPolicy` recibe `max_retries` del state. Los otros 4 knobs
  (`fail_cache_s`, `base_backoff_s`, `max_backoff_s`, `jitter`) quedan
  hardcoded en `build_token_store()` con los defaults del spike:
  - `fail_cache_s = 30.0`
  - `base_backoff_s = 1.0`
  - `max_backoff_s = 30.0`
  - `jitter = 0.25`

  Justificación: principle of least surprise + no growth de signature
  (matriz `configure()` ya tiene 6 params + max_retries de Phase 8;
  agregar 4 más bloatea el shape). Los defaults están validados por
  Spike 003 contra el caso 10-concurrent-callers-post-failure → 0 new
  auth hits. v1.2 expone si emerge use case real (logs operacionales
  podrían surface un need para `fail_cache_s` tuning).

- **D-04: `ttl_seconds = 23 * 3600` hardcoded, NO expuesto.**

  Matriz token TTL es 24h server-side; el cliente refreshea 1h antes
  (idiom Phase 6 carry-over). NO se expone porque cambiar TTL sin
  coordinar con el server es bug; siempre fixed.

### `_async_locks` lifecycle

- **D-05: Accept-and-document (process-lifetime leak).**

  `_async_locks: dict[int, asyncio.Lock]` keyed por `id(loop)`. NO se
  limpia. Document tradeoff:
  - **Production (1 long-lived event loop)**: 0 leak.
  - **Tests (`asyncio.run()` repetido)**: ~80B leaked por test. CI ~785
    tests = ~63KB leaked al final del run — manejable, sin afectar
    coverage o stability.
  - **Multi-loop apps (raros)**: ~80B per dead loop. Si una app crea
    1M loops, ~80MB. Anti-pattern documentado.

  Justificación: el blueprint del spike NO especificó cleanup mechanism;
  implementación simple sin edge cases sutiles (vs WeakKeyDictionary que
  requiere asyncio.AbstractEventLoop weakly-referenceable + un guard
  test). v1.2 backlog si emerge presión real (perfil de memoria muestra
  growth en multi-loop). El docstring de TokenStore documenta el
  tradeoff explícito.

  Alternativas rechazadas:
  - **`weakref.WeakKeyDictionary`**: cleanest semantic pero adds
    complexity + asyncio loop weakref edge cases.
  - **Explicit `aclose()` cleanup**: push lifecycle al caller — Pitfall #12
    (atexit/__del__-driven cleanup) carryover desde Phase 6 dice "caller
    responsible" pero NO es estructural enforcement.

### Live verification entry point (LIVE-02)

- **D-06: Claude's discretion — extender `main_matriz.py` con probes async paired.**

  ROADMAP da choice: `main_matriz.py --async` flag vs `verify_async()`
  function vs script separado. User no eligió esta área de discusión —
  el planner decide con la recomendación del orquestador:

  **Recomendación:** seguir el patrón `main_iol.py` (probes sync + async
  interleaved en el mismo `main()`, sin flag). Cada probe sync existente
  gana un probe async paired con misma signature. Outcome reporter
  compara y reporta PASS/FAIL/DRIFT entre las dos surfaces. Probes que
  no son async-aplicables (e.g., probes que dependen de WebSocket layer
  ws_client) skipean async con razón documentada.

  Razones:
  - Paridad sync↔async es el verdadero outcome de LIVE-02 — interleaving
    los expone juntos.
  - Match con `main_iol.py` reduce cognitive load del operador
    cross-driver.
  - NO requiere un flag (`--async`) que dilute el `main_matriz.py` script.

  El planner puede revisar y proponer alternativa si encuentra signal
  en el código que justifique flag-based (e.g., si los probes async
  triplican el runtime del script y el operador quiere correrlos solo
  on-demand).

### Plan slicing & wave orchestration

- **D-07: 4 planes — Wave 1 (TokenStore primitive) → Wave 2 (async surface) → Wave 3 (integration) → Wave 4 (green gate).**

  - **Plan 10-01 — TokenStore + RefreshPolicy + adapter + errors (Wave 1).**
    Crear los 4 archivos nuevos del decision D-01 + unit tests +
    integration stress test (sigue patrón Spike 002 — 205-caller). NO
    se modifica `client.py`, `aio.py`, `ws_client.py`, `_state.py`
    todavía. Outcome: TokenStore es importable y testeable standalone.
    1 commit atómico.

  - **Plan 10-02 — AsyncRetryTransport (`_atransport.py`) + async surface (`aio.py`) (Wave 2).**
    Crear `_atransport.py` mirroring `_transport.py` (mismo patrón iol
    `_atransport.py`). Reemplazar el 103-LOC stub `aio.py` con full REST
    surface: AsyncClient class con 22 endpoints + 22 module-level
    `async def` delegators + PEP 562 shim back-compat. NO toca `client.py`
    sync ni `ws_client.py` todavía. Tests: `test_async_client.py` mirror
    sync endpoints con pytest-httpx + pytest-asyncio + autouse fixture
    `_configure_async`. 1 commit atómico.

  - **Plan 10-03 — TokenStore wiring + `ws_client.py` migration (Wave 3).**
    Modificar `_state.py` (+1 field `token_store`); modificar `client.py`
    (sync `_ensure_token()` → `state.token_store.get_sync()`); modificar
    `aio.py` (`_aensure_token()` → `await asyncio.to_thread(state.token_store.get_sync)`
    o `state.token_store.get_async()`); modificar `ws_client.py`
    (`_rest._get_default()._ensure_token()` → `state.token_store.get_sync()`).
    Tests: cross-thread refresh regression (sync caller holds lock 100ms,
    async caller awaits, mismo token); ws_client smoke (mockeado, sin
    socket real). 1 commit atómico.

  - **Plan 10-04 — Live verification paridad + green gate (Wave 4).**
    Extender `main_matriz.py` con probes async paired (D-06). Operator
    runs live; outcome paridad sync↔async documentado en PLAN. Full
    pytest matriz (Python 3.12 + 3.13) + ruff + mypy strict +
    lint-imports + lint-logging grep + cross-leak sentinel
    (`verification/test_sync_async_isolation.py` ahora cubriendo matriz
    async — el skip Phase 10 forward-reference se elimina) + snapshot
    público REGEN (matriz: AsyncClient + 22 async delegators; otros 3
    paquetes: zero diff) + Phase 6 fixture-reaches-production: el skip
    matriz async se elimina (3rd guard activo, total = 8 active / 0 skips
    relacionados a Phase 10). 1 commit atómico (validation + snapshot
    delta + operator checkpoint).

- **D-08: 1 commit atómico por plan (no per-feature).**

  - Plan 10-01: 1 commit (TokenStore primitive + tests, standalone).
  - Plan 10-02: 1 commit (AsyncRetryTransport + AsyncClient REST surface + tests).
  - Plan 10-03: 1 commit (state wiring + sync/async/ws_client migration + cross-thread tests).
  - Plan 10-04: 1 commit (live verification + snapshot regen + validation).

- **D-09: Live re-verification scope = matriz async paridad (NO full 4-package).**

  Phase 10 corre live solo matriz async paired con sync. Full 4-package
  live re-verification (LIVE-01) sigue siendo Phase 11 final gate.
  Operator decide en Plan 10-04 si el live run se hace pre-commit o
  como manual step documentado en el PLAN (recomendación: manual,
  por blast radius — Phase 9 D-13 idiom).

### Claude's Discretion

El planner decide:

- **Naming exacto del campo en `_state.py`**: `token_store: TokenStore | None`
  vs `_token_store` con leading underscore (consistency con `_token_lock`
  del iol pattern). Recomendación: sin underscore, porque el field es
  parte del schema visible internamente; underscore es para "literally
  private at import" (PEP 562 forwarded names).
- **Naming del adapter class**: `MatrizRefresh` (spike blueprint) vs
  `MatrizRefreshAdapter` (más explícito). Recomendación: `MatrizRefresh`
  per blueprint — el rol "adapter" es implícito por la signature.
- **AsyncClient `_aensure_token` impl**: usa `asyncio.to_thread(get_sync)`
  vs implementa `get_async()` nativo. Recomendación: `get_async()` nativo
  per spike blueprint (no extra thread hop si ya estamos en async context;
  el `to_thread` se usa SOLO durante el refresh sync inner para liberar
  el loop).
- **AsyncClient PEP 562 `_DENIED_LEGACY` extensions**: si se agregan,
  alinear con el sync `client.py` shim. Recomendación: NO agregar denials
  en Phase 10 — los `_token`, `_token_expires_at`, `_base_url` etc.
  siguen forwardeados (back-compat).
- **`token_store` constructor injection vs lazy init**: AsyncClient debería
  recibir el token_store de afuera o construir uno lazy en `_get_default()`?
  Recomendación: lazy en `_get_default()` (matches Phase 6 `_default_client`
  idiom); explicit injection es overkill para v1.1 (defer a v1.2 si testing
  isolation lo justifica).
- **`test_async_client.py` layout**: 1 file con paramétrización por endpoint
  vs 1 file por concern (auth, query, mutation, etc.). Recomendación:
  1 file por concern (`test_async_auth.py`, `test_async_queries.py`,
  `test_async_mutations.py`) — affinity con la sync test structure.
- **probe async naming en `main_matriz.py`**: `probe_X_async()` vs
  `probe_async_X()`. Recomendación: `probe_X_async()` (suffix idiom),
  match con `main_iol.py`.
- **Snapshot diff documentation en Plan 10-04 VALIDATION.md**: incluir
  el full snapshot diff inline o solo summary count? Recomendación:
  full diff inline (forensics + the regen is the deliverable).
- **TokenStore docstring expansion**: cubrir el tradeoff de `_async_locks`
  process-lifetime leak (D-05) en el docstring vs en docs externos.
  Recomendación: docstring inline + sección dedicated en CONCERNS.md
  (codebase map).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & milestone

- `.planning/PROJECT.md` — v1.1 milestone "Tech Debt Cleanup"; target
  feature "Crear `matriz_client.aio.AsyncClient` con full REST mirror
  + `TokenStore` 3-way concurrent".
- `.planning/REQUIREMENTS.md` §"Refactor arquitectónico (REFAC)" —
  REFAC-04 literal: "`matriz_client/aio.py` mirroring full REST surface
  (mismas signatures que `client.py`) con `_state` async independiente
  + `TokenStore` con `threading.Lock` callable desde asyncio context
  y desde `ws_client.py` daemon thread"; §"Live re-verification (LIVE)"
  — LIVE-02 literal: "`matriz-client` async REST (`aio.py`) verificada
  live como parte de `main_matriz.py --async` o equivalente; mismo set
  de probes que la superficie sync".
- `.planning/ROADMAP.md` §"Phase 10" — 5 success criteria: 22 endpoints
  mirror, TokenStore 3-way con cross-thread regression, live paridad,
  ws_client migration, CI green; "Research flag: yes" (resuelto vía
  spike-findings skill auto-loaded).
- `.planning/STATE.md` — stopped_at "Phase 09 complete (4/4) — ready
  to discuss Phase 10"; current focus "Phase 10 — matriz aio.py +
  tokenstore".

### Spike findings (auto-loaded skill — Phase 10's primary blueprint)

- `.claude/skills/spike-findings-market-libs/SKILL.md` — Implementation
  blueprint, requirements, composition pattern. **CRITICAL** lectura
  obligatoria antes de planning. Resume: TokenStore 3-way + RefreshPolicy
  + their composition. 5 spikes processed (001a/b/c, 002, 003); 001c y
  003 son los winners.
- `.claude/skills/spike-findings-market-libs/references/tokenstore-3way.md`
  — Double-Checked Locking pattern detallado. Lock primitive + per-loop
  lazy `asyncio.Lock` + `asyncio.to_thread` para refresh. 205-caller
  stress test passes con 1 refresh, 0 errors, P95 cached async read
  < 0.01ms.
- `.claude/skills/spike-findings-market-libs/references/refresh-policy.md`
  — Decorator over `refresh_fn`. Transient/Permanent/RateLimited
  classification via exception types. **Fail-cache prevents auth-server
  DOS** — validated: 10 concurrent sync callers post-failure → 0 new
  auth server hits.
- `.claude/skills/spike-findings-market-libs/sources/001c-tokenstore-double-checked-locking/`
  — Spike source completo del winning lock pattern.
- `.claude/skills/spike-findings-market-libs/sources/002-tokenstore-3way-integration-stress/`
  — 205-caller stress validation. Use como reference para el test
  layout en `test_token_store.py`.
- `.claude/skills/spike-findings-market-libs/sources/003-tokenstore-refresh-policy/`
  — Winning retry pattern. Composes con 001c.

### Codebase maps (Phase 8/9 las dejó actualizadas; siguen vigentes)

- `.planning/codebase/ARCHITECTURE.md` §"Module-Level State Pattern" —
  `_state.py` canónico post-Phase-6; Phase 10 lo extiende con `token_store`
  field; §"Component Responsibilities" — table con `<pkg>._core`,
  `_state`, `_transport` que Phase 10 expande para matriz.
- `.planning/codebase/CONVENTIONS.md` — naming conventions, mypy strict
  patterns, `from __future__ import annotations` mandatory en archivos
  nuevos; `_snake_case` para módulos privados.
- `.planning/codebase/TESTING.md` — pytest-httpx + pytest-asyncio
  patterns; autouse `configure()` fixtures Phase 6 migration; cross-leak
  sentinel pattern.
- `.planning/codebase/STRUCTURE.md` — file inventory por paquete;
  Phase 10 agrega 4 archivos nuevos a matriz + modifica 4 existentes.
- `.planning/codebase/CONCERNS.md` — agregar entry para "`_async_locks`
  process-lifetime leak documented tradeoff" como nota operacional
  (Plan 10-01 escribe esto).

### Prior phases (Phase 6-9 carry-forward)

- `.planning/phases/06-compat-safety-net-client-class-skeleton/06-CONTEXT.md`
  — D-IOL-09 `token_lock` double-checked locking idiom (iol async
  pattern que Phase 10 generaliza a TokenStore matriz); D-09 snapshot
  público convention (Plan 10-04 lo REGENERA para matriz, zero diff
  para los otros 3); D-25 carve-out del matriz aio.py stub que Phase 10
  destraba.
- `.planning/phases/07-core-py-extraction-sync-async-logic-dedup/07-CONTEXT.md`
  — D-09 import-linter contracts (`_core.py` no importa `aio.py`/`client.py`;
  Phase 10 respeta); D-10 cross-leak sentinel test (Plan 10-04 lo extiende
  para matriz async); D-04 B8 alias pattern (`aio.py` importa
  `raise_for_response` de `_core.py`, NO duplica).
- `.planning/phases/08-retries-backoff-structured-logging/08-CONTEXT.md`
  — D-25 carve-out: matriz `_atransport.py` ABSENT en Phase 8, Phase 10
  lo crea (Plan 10-02); D-15 mutation gate (matriz `new_order`,
  `cancel_order`, `replace_order` siguen `idempotent=False`, Plan 10-02
  preserva); D-10 RedactingFilter (cobertura async heredada, no se
  modifica el regex).
- `.planning/phases/09-deferred-bug-fixes/09-CONTEXT.md` — D-09
  `_state.account_id` removal en higyrus + iol (matriz NO se tocó, ORP-01
  carryover); D-13 live re-verification scope = bug-driven (Phase 10
  D-09 sigue el idiom: live solo en matriz, no full × 4 paquetes).

### Implementation sites (relevantes para planner + executor)

**Reference paquetes (NO se modifican — son patrones a espejar):**

- `packages/iol-client/src/iol_client/aio.py` (614 LOC) — reference pattern
  para AsyncClient full REST. Note: usa `_atransport.py` + `_core.py`;
  importa `raise_for_response` de `_core` (B8 lock-in D-04).
- `packages/iol-client/src/iol_client/_atransport.py` — reference pattern
  para `AsyncRetryTransport` en matriz. Intra-package imports de constants
  del sync `_transport.py` (`_RETRYABLE_STATUS`, `_RETRYABLE_EXC`, etc.).
- `packages/iol-client/tests/conftest.py` (lines 1-80) — reference para
  autouse `_configure_async` fixture en `packages/matriz-client/tests/conftest.py`
  (pytest-asyncio idiom).
- `packages/iol-client/src/iol_client/client.py` (`_ensure_token`,
  `_token_lock`) — reference del double-checked locking idiom que Phase 10
  generaliza a TokenStore.

**Matriz target files (Phase 10 modifies o creates):**

- `packages/matriz-client/src/matriz_client/aio.py` (103 LOC stub actual)
  — Plan 10-02 lo reemplaza con full REST surface. Honrar B8 docstring
  forward-looking note (líneas 19-21): import `_raise_for_response` de
  `_core`, NO duplicar.
- `packages/matriz-client/src/matriz_client/client.py` (771 LOC actual) —
  Plan 10-03 modifica `_ensure_token()` para delegar a
  `state.token_store.get_sync()`; `_get_default()` lazy init de
  `token_store` via `build_token_store(state, max_retries=...)`.
- `packages/matriz-client/src/matriz_client/_core.py` (924 LOC) — NO se
  modifica. Plan 10-02 importa builders/parsers desde acá para el async
  surface.
- `packages/matriz-client/src/matriz_client/_state.py` (55 LOC) — Plan 10-03
  agrega `token_store: TokenStore | None = None` field. NO toca el resto.
- `packages/matriz-client/src/matriz_client/_transport.py` (239 LOC) —
  reference para `_atransport.py` (Plan 10-02 lo crea con `tenacity.AsyncRetrying`).
- `packages/matriz-client/src/matriz_client/ws_client.py` (339 LOC) —
  Plan 10-03 swap del `_rest._get_default()._ensure_token()` a
  `state.token_store.get_sync()`. Líneas exactas:
  - `ws_client.py:145`: `default = _rest._get_default()`
  - `ws_client.py:146`: `default._ensure_token()` → swap a `default._state.token_store.get_sync()`
  - `ws_client.py:147`: `assert default._state.token is not None` → preservar (post-condition de get_sync)
  - `ws_client.py:157`: `header={"X-Auth-Token": default._state.token}` → preservar.
- `main_matriz.py` — Plan 10-04 extiende con probes async paired.

**Matriz nuevos archivos (Phase 10 crea):**

- `packages/matriz-client/src/matriz_client/_token_store.py` (Plan 10-01).
- `packages/matriz-client/src/matriz_client/_refresh_policy.py` (Plan 10-01).
- `packages/matriz-client/src/matriz_client/_refresh.py` (Plan 10-01).
- `packages/matriz-client/src/matriz_client/_refresh_errors.py` (Plan 10-01).
- `packages/matriz-client/src/matriz_client/_atransport.py` (Plan 10-02).
- `packages/matriz-client/tests/test_token_store.py` (Plan 10-01).
- `packages/matriz-client/tests/test_refresh_policy.py` (Plan 10-01).
- `packages/matriz-client/tests/test_async_client.py` o equivalentes
  por concern (Plan 10-02).

**Tests existentes con skips a flipear (Plan 10-04):**

- `packages/matriz-client/tests/test_fixture_reaches_production.py:64` —
  skip "matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore"
  → active.
- `verification/test_async_cancellation.py:82` — skip "Phase 10 REFAC-04
  + TokenStore" → active.
- `verification/test_sync_async_isolation.py:176` — skip "Phase 10
  REFAC-04 + TokenStore" → active.

### Findings / Audits (forensic context)

- `.planning/v1.1-MILESTONE-AUDIT.md` (2026-06-13T20:30Z) — Phase 10
  status "NOT STARTED, UNBLOCKED". Score 16/29 — 2 REQ-IDs (REFAC-04,
  LIVE-02) unsatisfied porque Phase 10 no iniciada.
- `.planning/v1.1-INTEGRATION-CHECK.md` (2026-06-13T20:xxZ) — Claim 3
  BUG-01 CFI guard async PARTIAL (no reachable hasta Phase 10 ship aio.py
  REST). Plan 10-02 lo flipea a WIRED implícitamente (no se modifica
  `_core.py`, solo se llama el builder desde async path).
- `.planning/quick/260613-nwb-fix-int-01-main-iol-py-crashea-con-attri/260613-nwb-SUMMARY.md`
  — INT-01 quick fix (main_iol.py `_base_url`). Phase 10 NO se ve
  afectada pero el patrón "_get_default()._state.X" es el idiom que el
  nuevo matriz async debería seguir.

### Forward references (no leer todavía)

- `.planning/ROADMAP.md` §"Phase 11" — HARN-07..10, CR-01..08, LIVE-01
  (full 4-package live re-verification final gate post-Phase-10). Phase 10
  NO toca este territory.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **iol async REST surface (`packages/iol-client/src/iol_client/aio.py`, 614 LOC)** —
  Plan 10-02 espeja el shape (AsyncClient class con __aenter__/__aexit__,
  `_aensure_token` con `token_lock` double-checked locking, module-level
  async delegators).
- **iol `_atransport.py`** — reference para `matriz/_atransport.py` (Plan 10-02).
  Pattern: import constants del sync `_transport.py`, usar
  `tenacity.AsyncRetrying` + `async for` + `async with`,
  `await asyncio.sleep` para Retry-After honor (Pitfall 16: preserva
  asyncio.CancelledError).
- **iol-client `conftest.py` autouse `_configure_async` fixture** (lines 49-65) —
  reference exacto para `packages/matriz-client/tests/conftest.py`.
- **Phase 6 `_ClientState` pattern (`packages/matriz-client/src/matriz_client/_state.py`)** —
  Plan 10-03 lo extiende +1 field. NO toca el resto del schema (Phase 6
  D-13 forward-decl removal Phase 9 D-09 ya cubrió higyrus + iol; matriz
  `account_id` queda ORP-01 carryover).
- **Spike sources `001c` + `002` + `003`** — pueden copiar/adaptar el
  TokenStore impl directamente, ya validados con stress test 205-caller.
- **`verification/test_sync_async_isolation.py`** (Phase 7 D-10) — el
  cross-leak sentinel test ya existe; Plan 10-02/03 lo extiende para
  cubrir matriz async (eliminar el skip Phase 10 forward-reference).
- **Phase 8 `_transport.RetryTransport` mutation gate** — `req.extensions["idempotent"]`
  protocol; Plan 10-02 `AsyncRetryTransport` lee del mismo lugar (single
  source of truth, no nuevo protocol).
- **`_logging.py` RedactingFilter** — cobertura automática para async
  call sites; NO se modifica regex en Phase 10.

### Established Patterns

- **Per-package serial delivery** — Phase 10 es matriz-only (los otros 3
  paquetes ya tienen `aio.py`). Plan slicing: 10-01 (primitive) → 10-02
  (transport + async surface) → 10-03 (integration) → 10-04 (live + gate).
- **1 commit atómico por plan** — Phase 6/7/8/9 idiom.
- **`from __future__ import annotations` mandatory** en archivos nuevos.
- **Single-site fix en `_core.py`** (Phase 7 REFAC-03) — Phase 10 NO toca
  `_core.py` (builders/parsers ya están).
- **Mutation gate** (Phase 8): non-idempotent ops siguen `idempotent=False`
  en `RequestSpec`; Plan 10-02 AsyncClient hereda automáticamente
  (no nuevo gate, el `_atransport.py` mirror lee del mismo `req.extensions`).
- **PEP 562 shim (Phase 6)** — Plan 10-02 AsyncClient mantiene el shim
  `__getattr__` con `_FORWARDED_TO_STATE`/`_FORWARDED_HTTP_CLIENT` para
  back-compat de `aio._token`, `aio._base_url`, etc.
- **`assert state.token is not None` post `_ensure_token()`** — Phase 6
  pattern para mypy strict narrowing. Plan 10-03 async path mantiene
  el assert.
- **B8 lock-in alias pattern** (Phase 7 D-04) — `aio.py` importa
  `raise_for_response` de `_core` (NO duplica). Plan 10-02 sigue.
- **Conditional rotation pattern** (Phase 6 D-IOL-10) — NO aplica a matriz
  (sin OAuth refresh_token), pero el patrón general "state updates ONLY
  if parser returned non-None" guía cualquier estado mutable nuevo
  (e.g., el `state.token = new_token` solo si el refresh succeeded —
  fail-cache NO toca state).

### Integration Points

- **Plan 10-01 (TokenStore + RefreshPolicy primitive) — files created:**
  - `packages/matriz-client/src/matriz_client/_token_store.py` (NEW).
  - `packages/matriz-client/src/matriz_client/_refresh_policy.py` (NEW).
  - `packages/matriz-client/src/matriz_client/_refresh.py` (NEW).
  - `packages/matriz-client/src/matriz_client/_refresh_errors.py` (NEW).
  - `packages/matriz-client/tests/test_token_store.py` (NEW).
  - `packages/matriz-client/tests/test_refresh_policy.py` (NEW).
  - `packages/matriz-client/tests/test_refresh_errors.py` (NEW, opcional).

- **Plan 10-02 (AsyncRetryTransport + async REST surface) — files modified/created:**
  - `packages/matriz-client/src/matriz_client/_atransport.py` (NEW).
  - `packages/matriz-client/src/matriz_client/aio.py` (REPLACE stub con full REST).
  - `packages/matriz-client/src/matriz_client/__init__.py` (potentially
    update `__all__` para exportar AsyncClient si no estaba ya).
  - `packages/matriz-client/tests/test_async_client.py` (NEW, o split por
    concern: test_async_auth, test_async_queries, test_async_mutations).
  - `packages/matriz-client/tests/conftest.py` (EXTEND con autouse
    `_configure_async` fixture, mirror iol-client).
  - `packages/matriz-client/tests/test_atransport.py` (NEW, mirror sync
    `_transport` test suite Phase 8).

- **Plan 10-03 (state wiring + sync/async/ws_client migration) — files modified:**
  - `packages/matriz-client/src/matriz_client/_state.py` (+1 field
    `token_store: TokenStore | None`).
  - `packages/matriz-client/src/matriz_client/client.py` (modify
    `_ensure_token()` → `state.token_store.get_sync()`; `_get_default()`
    lazy init de `token_store`).
  - `packages/matriz-client/src/matriz_client/aio.py` (modify
    `_aensure_token()` → `state.token_store.get_async()`).
  - `packages/matriz-client/src/matriz_client/ws_client.py` (líneas 145-147
    swap `_ensure_token()` → `token_store.get_sync()`).
  - `packages/matriz-client/tests/test_token_store_integration.py` (NEW)
    — cross-thread refresh regression (sync caller holds 100ms, async
    awaits, returns mismo token).
  - `packages/matriz-client/tests/test_ws_client_token_integration.py`
    (NEW, mockeado).

- **Plan 10-04 (live verification + green gate) — files modified/created:**
  - `main_matriz.py` (EXTEND con probes async paired).
  - `packages/matriz-client/tests/test_fixture_reaches_production.py`
    (modify — flipear skip).
  - `verification/test_async_cancellation.py` (modify — flipear skip).
  - `verification/test_sync_async_isolation.py` (modify — flipear skip
    + extender para matriz async).
  - `verification/snapshots/matriz-client-surface.txt` (REGEN — diff
    documenta la growth de AsyncClient + 22 async delegators).
  - `.planning/phases/10-matriz-aio-py-creation-tokenstore/10-VALIDATION.md`
    (NEW — Nyquist + CI evidence + snapshot delta + Phase 10 dependency
    closure summary).

- **Snapshot público (Phase 6 D-09) — MATRIZ DIFF ESPERADO en Phase 10.**
  Plan 10-04 regenera + valida que el diff sea exactamente la growth
  de async surface (AsyncClient + 22 async delegators) y nada más.
  Para los otros 3 paquetes: zero diff esperado.

- **Import-linter contracts (Phase 7 D-09)** — Plan 10-02 verifica que
  `aio.py` solo importa `_core.py` + `_atransport.py` + `_state.py` (NO
  importa `client.py` excepto para `_validate_max_retries`/`InstrumentType`
  shared utilities, idéntico al iol pattern). `_core.py` NO importa
  `aio.py` (forbidden direction).

- **Pre-existing 108 ruff errors en `.planning/spikes/` y
  `.claude/skills/spike-findings-market-libs/sources/`** (Phase 8 carry-over):
  NO se intentan corregir en Phase 10. Tracked en deferred-items.md.

</code_context>

<specifics>
## Specific Ideas

- **TokenStore composition (from spike blueprint, ratified):**

  ```python
  # packages/matriz-client/src/matriz_client/_token_store.py
  from __future__ import annotations

  import asyncio
  import threading
  import time
  from collections.abc import Callable
  from dataclasses import dataclass

  from ._refresh_policy import RefreshPolicy
  from ._refresh import MatrizRefresh
  from ._refresh_errors import (
      PermanentRefreshError, TransientRefreshError, RateLimitedRefreshError
  )


  class TokenStore:
      def __init__(self, ttl_seconds: int, refresh_fn: Callable[[], str]) -> None:
          self._ttl = ttl_seconds
          self._refresh_fn = refresh_fn
          self._token: str | None = None
          self._expires_at: float = 0.0
          self._lock = threading.Lock()
          self._async_locks: dict[int, asyncio.Lock] = {}
          # NB: dict NO cleared on loop death (D-05). Process-lifetime accept.
          # Document tradeoff: ~80B per dead loop. v1.2 backlog if growth matters.

      def get_sync(self) -> str:
          """Called from sync REST, ws_client daemon thread."""
          if self._token is not None and time.time() < self._expires_at:
              return self._token  # fast path, no lock
          with self._lock:
              # double-check after acquiring
              if self._token is not None and time.time() < self._expires_at:
                  return self._token
              new_token = self._refresh_fn()
              self._token = new_token
              self._expires_at = time.time() + self._ttl
              return new_token

      async def get_async(self) -> str:
          """Called from async REST inside event loop."""
          if self._token is not None and time.time() < self._expires_at:
              return self._token  # fast path
          loop = asyncio.get_running_loop()
          alock = self._async_locks.setdefault(id(loop), asyncio.Lock())
          async with alock:
              # double-check after acquiring per-loop lock
              if self._token is not None and time.time() < self._expires_at:
                  return self._token
              # offload refresh to thread (free the event loop)
              new_token = await asyncio.to_thread(self.get_sync)
              return new_token


  def build_token_store(state, *, max_retries: int) -> TokenStore:
      """Build a Phase-10 TokenStore composed with retry policy."""
      adapter = MatrizRefresh(
          http_client=state.http_client,
          base_url=state.base_url,
          username=state.username,
          password=state.password,
      )
      policy = RefreshPolicy(
          max_retries=max_retries,
          base_backoff_s=1.0,
          max_backoff_s=30.0,
          jitter=0.25,
          fail_cache_s=30.0,
      )
      return TokenStore(
          ttl_seconds=23 * 3600,
          refresh_fn=policy.wrap(adapter),
      )
  ```

- **RefreshPolicy decorator (spike pattern):**

  ```python
  # packages/matriz-client/src/matriz_client/_refresh_policy.py
  from __future__ import annotations

  import random
  import time
  from collections.abc import Callable
  from dataclasses import dataclass

  from ._refresh_errors import (
      PermanentRefreshError,
      TransientRefreshError,
      RateLimitedRefreshError,
  )


  @dataclass
  class RefreshPolicy:
      max_retries: int = 3
      base_backoff_s: float = 1.0
      max_backoff_s: float = 30.0
      jitter: float = 0.25
      fail_cache_s: float = 30.0

      def wrap(self, refresh_fn: Callable[[], str]) -> Callable[[], str]:
          cached_error: Exception | None = None
          cached_error_at: float = 0.0

          def wrapped() -> str:
              nonlocal cached_error, cached_error_at
              # fail-cache check (permanent errors don't get cached — checked at raise site)
              if cached_error is not None and time.monotonic() - cached_error_at < self.fail_cache_s:
                  raise cached_error
              last_exc: Exception | None = None
              for attempt in range(self.max_retries + 1):
                  try:
                      return refresh_fn()
                  except PermanentRefreshError as e:
                      # PROPAGATE IMMEDIATELY, do not cache, do not retry
                      raise
                  except RateLimitedRefreshError as e:
                      last_exc = e
                      sleep_s = min(e.retry_after_seconds or self.base_backoff_s * (2**attempt),
                                    self.max_backoff_s)
                      time.sleep(sleep_s * (1 + random.uniform(-self.jitter, self.jitter)))
                  except TransientRefreshError as e:
                      last_exc = e
                      sleep_s = min(self.base_backoff_s * (2**attempt), self.max_backoff_s)
                      time.sleep(sleep_s * (1 + random.uniform(-self.jitter, self.jitter)))
              # exhausted → fail-cache and re-raise
              assert last_exc is not None
              cached_error = last_exc
              cached_error_at = time.monotonic()
              raise last_exc

          return wrapped
  ```

- **AsyncClient skeleton (mirror iol pattern):**

  ```python
  # packages/matriz-client/src/matriz_client/aio.py
  from __future__ import annotations

  import asyncio
  import time
  from typing import Any, Self

  import httpx

  from matriz_client import _atransport, _core
  from matriz_client._core import RequestSpec
  from matriz_client._core import raise_for_response as _raise_for_response  # B8 D-04
  from matriz_client._state import _REQUEST_TIMEOUT, _ClientState, _TOKEN_TTL
  from matriz_client._token_store import build_token_store
  from matriz_client.client import _validate_max_retries
  from matriz_client.exceptions import PrimaryAPIError
  from matriz_client.types import (
      CFICode, MarketId, OrderType, Side, TimeInForce, SegmentId,
  )

  __all__ = ["AsyncClient", "configure", "login", "get_segments", ...]


  class AsyncClient:
      def __init__(
          self,
          base_url: str | None = None,
          username: str | None = None,
          password: str | None = None,
          token: str | None = None,
          token_expires_at: float | None = None,
          max_retries: int = 2,
      ) -> None:
          self._state = _ClientState(...)
          _validate_max_retries(max_retries)
          self._max_retries = max_retries
          # token_store lazy init en _aensure_token()
          self._state.token_store = None  # set on first call
          ...

      async def _aensure_token(self) -> None:
          if self._state.token_store is None:
              self._state.token_store = build_token_store(self._state, max_retries=self._max_retries)
          self._state.token = await self._state.token_store.get_async()

      async def get_segments(self) -> list[Segment]:
          await self._aensure_token()
          spec = _core.build_get_segments_request(self._state)
          resp = await self._request(spec)
          return _core.parse_get_segments_response(resp)

      # ... 21 endpoints más, todos siguen el mismo pattern ...

      async def aclose(self) -> None:
          if self._state.http_client is not None:
              await self._state.http_client.aclose()
              self._state.http_client = None

      async def __aenter__(self) -> Self:
          return self

      async def __aexit__(self, *exc: Any) -> None:
          await self.aclose()


  # Module-level singletons + delegators
  _default_async_client: AsyncClient | None = None

  def _get_default() -> AsyncClient:
      global _default_async_client
      if _default_async_client is None:
          _default_async_client = AsyncClient()
      return _default_async_client

  def configure(
      base_url: str | None = None,
      username: str | None = None,
      password: str | None = None,
      token: str | None = None,
      token_expires_at: float | None = None,
      max_retries: int | None = None,
  ) -> None:
      global _default_async_client
      _default_async_client = AsyncClient(
          base_url=base_url, username=username, password=password,
          token=token, token_expires_at=token_expires_at,
          max_retries=max_retries if max_retries is not None else 2,
      )

  async def login() -> str:
      return await _get_default().login()

  async def get_segments() -> list[Segment]:
      return await _get_default().get_segments()

  # ... 20 endpoint delegators más ...
  ```

- **Cross-thread refresh regression test (D-07 Plan 10-03):**

  ```python
  # packages/matriz-client/tests/test_token_store_integration.py
  import asyncio
  import threading
  import time

  import pytest

  from matriz_client._token_store import TokenStore


  @pytest.mark.asyncio
  async def test_async_caller_waits_for_concurrent_sync_refresh():
      """Sync thread holds refresh-lock for 100ms; async caller awaits and
      returns the SAME refreshed token (no stale, no duplicate refresh)."""
      refresh_count = 0
      def refresh_fn() -> str:
          nonlocal refresh_count
          time.sleep(0.1)  # simulate network 100ms
          refresh_count += 1
          return f"TOKEN-{refresh_count}"

      store = TokenStore(ttl_seconds=10, refresh_fn=refresh_fn)

      # sync thread starts refresh
      sync_token_holder: list[str] = []
      def sync_caller() -> None:
          sync_token_holder.append(store.get_sync())

      t = threading.Thread(target=sync_caller, daemon=True)
      t.start()

      # tiny delay to ensure sync caller acquired the lock
      await asyncio.sleep(0.01)

      # async caller should AWAIT (cannot acquire lock yet)
      async_token = await store.get_async()

      t.join()

      assert async_token == sync_token_holder[0] == "TOKEN-1"
      assert refresh_count == 1  # exactly one refresh
  ```

- **ws_client.py migration snippet (D-07 Plan 10-03):**

  ```python
  # packages/matriz-client/src/matriz_client/ws_client.py (líneas 145-147)

  # BEFORE:
  default = _rest._get_default()
  default._ensure_token()
  assert default._state.token is not None

  # AFTER:
  default = _rest._get_default()
  default._state.token = default._state.token_store.get_sync()
  assert default._state.token is not None
  ```

- **Commit message patterns Phase 10:**
  - Plan 10-01: `feat(matriz): TokenStore + RefreshPolicy primitive (Spike 001c+003) (REFAC-04)`
  - Plan 10-02: `feat(matriz): AsyncClient full REST mirror + AsyncRetryTransport (REFAC-04)`
  - Plan 10-03: `feat(matriz): wire TokenStore into Client/AsyncClient/ws_client + cross-thread regression (REFAC-04)`
  - Plan 10-04: `ci(phase-10): green gate — live paridad sync↔async + snapshot regen + 3 skips flipped (LIVE-02)`

- **Tests-count delta target (Plan 10-04 VALIDATION.md):**
  - Plan 10-01: +20 tests (TokenStore unit + stress 205-caller + RefreshPolicy unit).
  - Plan 10-02: +30 tests (async endpoints mirror + AsyncRetryTransport mirror).
  - Plan 10-03: +5 tests (cross-thread integration + ws_client wiring).
  - Plan 10-04: +0 nuevos (solo flipear 3 skips → active).
  - Total Phase 10: ~785 baseline + ~55 = ~840 tests verde.

- **Snapshot diff esperado (Plan 10-04 VALIDATION.md):**
  - matriz-client-surface.txt: +1 class (`AsyncClient`) + 22 module-level
    async delegators (`async def login`, `async def get_segments`, etc.) +
    1 module-level `configure` ya existente (no diff allí) + ~3 helpers
    privados. Total esperado: ~23-25 nuevas líneas.
  - iol/higyrus/ambito/wallets-client-surface.txt: zero diff.

</specifics>

<deferred>
## Deferred Ideas

- **WeakKeyDictionary cleanup para `_async_locks`** — D-05 picks
  accept-and-document. v1.2 si el perfil de memoria muestra growth en
  multi-loop apps. Cheap reverse cuando aparezca el use case.

- **Explicit `aclose()` cleanup del `_async_locks` entry** — D-05 rechaza
  push lifecycle al caller. v1.2 si Pitfall #12 trade-off emerge como
  blocker real.

- **Exposición de `fail_cache_s` / `base_backoff_s` / `max_backoff_s` /
  `jitter` en public API** — D-03 mantiene hardcoded internals. v1.2
  si logs operacionales surface need real de tuning (e.g., un deployment
  con auth server especialmente flakey beneficiaría de `fail_cache_s=60`).

- **TokenStore reuso en iol/higyrus** — REFAC-04 es matriz-only por
  diseño (D-25 carve-out). iol ya tiene `token_lock` + `_ensure_token`
  async; higyrus también. Conceptualmente compatible pero no migrate
  (no 3-way pressure: solo matriz tiene daemon thread). v1.2 si emerge
  refactor común (probablemente NO — el costo del migration outweigh
  el benefit).

- **AsyncClient explicit token_store injection** — `AsyncClient(token_store=ts)`
  signature para testing isolation. D-08 (Claude's discretion) recomienda
  lazy init en `_get_default()` per Phase 6 idiom. v1.2 si testing
  patterns lo justifican.

- **Generated-code dual-emit (sync/async desde un mismo source)** —
  REQUIREMENTS Future Requirements v1.2+. Phase 10 sigue duplicate-by-hand
  pattern de iol/higyrus/ámbito. Tradeoff: codegen reduce drift pero
  adds tooling complexity; defer hasta milestones futuros.

- **`MATRIZ_SAMPLE_INSTRUMENTS` env var** (mirror del `HIGYRUS_SAMPLE_CUENTAS`
  Phase 9 D-10) — Plan 10-04 live verification puede usar instruments
  hardcoded para reproducibility. v1.2 si la live paridad requiere
  un set canónico de instruments contra el que validar.

- **Live verification del WebSocket layer** — `matriz_client.ws_client`
  daemon-thread NO se verifica live en v1.1 (out of scope explícito en
  REQUIREMENTS.md). v1.2+.

- **`Client.from_env()` classmethod** — REQUIREMENTS Future. Phase 10
  sigue el env-reading pattern actual (`_state.py` reads env in
  `_default_base_url()`, etc.).

- **`Client.with_options(max_retries=N)` per-call override** — anthropic/openai
  pattern. REQUIREMENTS Future v1.2+.

- **disk persistence del matriz token** — Process restart = re-login.
  Aceptable mientras los tokens son 24h TTL y el process lifecycle es
  predictable (typical deploy patterns).

- **prod-vs-remarkets verification** — D-MATZ-27 REQUIRED handoff
  defer a v1.2 explicit (Out of Scope v1.1).

- **TODO matriz-driver-findings-file-handling** — folded en Phase 11
  HARN-07/08/10 (per STATE.md). NO se folda en Phase 10.

### Reviewed Todos (not folded)

- **`matriz-driver-findings-file-handling`** (`.planning/todos/pending/`,
  score 0.6) — review: el todo cubre `findings.py` append-only +
  content-addressed dedupe + operator field preservation. Phase 11
  HARN-07/HARN-08/HARN-09/HARN-10 scope explícito. NO se folda en
  Phase 10 (que es matriz aio.py + TokenStore territory).

</deferred>

---

*Phase: 10-matriz-aio-py-creation-tokenstore*
*Context gathered: 2026-06-13*
*Sources: spike-findings-market-libs skill (auto-loaded) + Phase 6-9 CONTEXT.md carry-over + v1.1 audit (2026-06-13T20:30Z) + ROADMAP.md §"Phase 10" + REQUIREMENTS.md §"REFAC-04, LIVE-02".*
