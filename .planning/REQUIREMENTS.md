# Requirements: market-libs — v1.1 Tech Debt Cleanup

**Milestone goal:** Saldar la deuda técnica arquitectónica y los hallazgos diferidos
de v1.0 — refactor a clase Client por instancia (con compat layer no-breaking),
deduplicación sync/async con creación de `aio.py` para matriz-client, retries con
backoff + jitter, logging estructurado, fix de los 4 findings diferidos, hardening
del harness y cierre de los 8 concerns del code review final de Phase 5.

**Scope packages:** `iol-client`, `higyrus-client`, `ambito-financiero-client`,
`matriz-client`. Excluido: `wallets-client` (stub).

**Non-breaking:** v1.1 es un bump minor — la API pública (top-level functions
`pkg.get_X(...)`, `pkg.configure(...)`) se mantiene 100% backwards-compatible vía
compat layer sobre la clase `Client` interna.

---

## v1.1 Requirements

### Refactor arquitectónico (REFAC)

- [ ] **REFAC-01**: Safety net previo al refactor — golden public-surface snapshot
  + "fixture-reaches-production" guard test por paquete; baseline de test count,
  assertion count y coverage% registrados antes de cada phase.
- [ ] **REFAC-02**: Clase `Client` (sync) + `AsyncClient` (async) por paquete con
  `close()`/`aclose()`, sync/async context manager, estado scoped a instancia
  (`base_url`, credenciales, token, http client, refresh_token); top-level
  functions (`pkg.get_X(...)`) y `configure(...)` quedan delegando en un
  default-client lazy module-level, vía PEP 562 `__getattr__` shim.
- [ ] **REFAC-03**: Módulo `_core.py` por paquete con builders/parsers puros
  (`RequestSpec`, `raise_for_response`, `unwrap_envelope`, auth-flow helpers);
  `client.py` y `aio.py` quedan como shells de transporte (~30-50 LOC por
  endpoint) llamando a `_core`; CI rule (import-linter / grep) que prohíbe
  `_core.py` importar `client.py` o `aio.py`.
- [ ] **REFAC-04**: `matriz_client/aio.py` mirroring full REST surface (mismas
  signatures que `client.py`) con `_state` async independiente + `TokenStore`
  con `threading.Lock` callable desde asyncio context y desde `ws_client.py`
  daemon thread.

### Reliability — retries + backoff (RELY)

- [ ] **RELY-01**: Retries transparentes via `tenacity` para status codes
  408/409/429/≥500 + connection errors (`ConnectError`, `ConnectTimeout`,
  `ReadTimeout`); default `max_attempts=2`; aplica a los 4 paquetes.
- [ ] **RELY-02**: Backoff exponencial con **full jitter** (AWS-recommended);
  honra `Retry-After` header en 429 y 503 con cap configurable de 60 s.
- [ ] **RELY-03**: Mutation-aware retry gate — `idempotent: bool = False` por
  `_request()`; GET endpoints lo marcan `True` explícitamente; POST/PATCH NUNCA
  se reintentan sin `idempotent=True`; regression test asegura exactamente UN
  request outgoing por POST mockeado contra 503.
- [ ] **RELY-04**: Manejo explícito de 401 en `_request()` con **exactly one**
  re-auth attempt (clear token → `_ensure_token()` → retry once); `AuthError` y
  `<Pkg>APIError`/`PrimaryAPIError`/`HigyrusAPIError` NUNCA entran al
  `retry_on=` tuple de tenacity.

### Structured logging (LOG)

- [ ] **LOG-01**: `logging.getLogger("<pkg>")` por paquete + `NullHandler` en
  `__init__.py`; nunca `logging.basicConfig()` ni handlers en `logging.root`;
  CI grep rule que prohíbe ambos en `packages/*/src/`; regression test
  asegura `logging.root.handlers` unchanged tras `import <pkg>`.
- [ ] **LOG-02**: `RedactingFilter` por paquete con lógica de Bearer/`X-Auth-Token`/
  `password=`/IOL refresh_token/Higyrus JSON password redaction (duplicado 4x,
  no importable de `verification/`); regression test (`caplog`) asegura que no
  hay substring de token en records aunque consumer habilite DEBUG.
- [ ] **LOG-03**: Convención de niveles + structured `extra={}`:
  DEBUG=request/response (sin body por default), INFO=auth events, WARNING=
  retries, ERROR=terminal failures; fields obligatorios:
  `package`, `method`, `url`, `status_code`, `attempt`, `duration_ms`;
  `account_id` (higyrus, matriz) cuando aplica.

### Deferred bug fixes (BUG)

- [ ] **BUG-01**: F-09 matriz ERROR-MAP — diferido en Phase 5 v1.0; fix en
  `_core.raise_for_response` (cubre sync y async desde 1 site) + regression
  test mockeado; cierra el FAIL de `verify_cycle_closure` DRIFT-02.
- [ ] **BUG-02**: F-02 higyrus `get_listado_cuentas=0` — investigación y fix en
  `_core.py` (single-site, cubre sync+async); regression test mockeado +
  re-verificación live (puede quedar FINDING vs FIXED según root cause).
- [ ] **BUG-03**: IOL refresh_token persistence between invocations — usar
  `_ClientState.refresh_token` (in-memory por instancia, deferred a disk
  persistence para v1.2); regression tests para refresh→success y
  refresh→password fallback en el ciclo de vida de una instancia.
- [ ] **BUG-04**: HIGY multi-account iteration — API soporta múltiples cuentas
  asociadas; `Client` instance permite multi-account (`Client(account_id=X)`
  por cuenta, OR `client.get_X(account_id=Y)` per-call — operator decision en
  planning); regression test live con ≥2 cuentas.

### Harness hardening (HARN-07+)

- [ ] **HARN-07**: `verification/findings.py` append-only con BEGIN/END zone
  parser; lectura de archivo existente + merge + write atómico; preserva todo
  contenido fuera de la zona generada.
- [ ] **HARN-08**: Content-addressed dedupe by finding ID — cierra D-MATZ-27
  (dedupe de "prod-vs-remarkets divergence acknowledged" terminal); aplica a
  los 4 drivers; idempotent re-run = git-clean.
- [ ] **HARN-09**: Operator field preservation cross-runs — campos
  `Classification:`, `Rationale:`, `Regression:`, `Resolution:` añadidos por el
  operador sobreviven verbatim a re-runs del driver; regression test con re-run
  N veces vs estado inicial.
- [ ] **HARN-10**: `main_matriz.py` dedupe de `D-MATZ-27 EXPECTED` terminal
  finding por idempotencia (no requiere N re-runs para detectar duplicación).

### Code Review concerns (CR — cierra WR-01..WR-08)

- [ ] **CR-01** (WR-01): `main_matriz.py:1722-1746` `probe_schema_snapshot`
  registra placeholder en `sample_params` mientras el snapshot file path
  refleja `PRIMARY_ACCOUNT` live; alinear ambos.
- [ ] **CR-02** (WR-02): `probe_login_sync` retorna `"FAIL"` mientras el resto
  del driver usa `"FINDING"` para fallos de auth; unificar a `FINDING`.
- [ ] **CR-03** (WR-03): `packages/matriz-client/src/matriz_client/client.py:166-174`
  `_request` no consume response body antes de raise cuando `data.status=="ERROR"`
  — potential connection-pool resource leak con HTTP/2; consumir body explícito.
- [ ] **CR-04** (WR-04): `main_matriz.py:172-179` `_first_dict` silenciosamente
  acepta non-list / empty-list inputs; distinguir y reportar.
- [ ] **CR-05** (WR-05): `main_matriz.py:300-1394` 18 sweep probes con
  ~95% boilerplate duplicado — refactor a helper único; previene drift entre
  probes (con `_core.py` + `Client` ya en v1.1 esto se simplifica).
- [ ] **CR-06** (WR-06): `main_matriz.py` + `main_higyrus.py` bare `except
  Exception` a nivel módulo (≥20 sites entre ambos) — narrow a `except
  Exception as e` capturando solo lo necesario; nunca enmascarar `KeyboardInterrupt`.
- [ ] **CR-07** (WR-07): `main_higyrus.py:233-318` `_capture_sync_query_string` /
  `_capture_async_query_string` mutan `event_hooks` sin lock — multi-event-loop
  callers corrompen hooks; usar lock o per-request hook injection.
- [ ] **CR-08** (WR-08): `main_higyrus.py:767` line lengths >100 cols dentro de
  f-string `dict.keys()` — split o silenciar con `# noqa`.

### Live re-verification (LIVE)

- [ ] **LIVE-01**: `main_*.py --live` × 4 paquetes (iol, higyrus, ambito, matriz)
  pasa sin regresiones del baseline `verification-cycle-2026-Q2` después de
  todos los refactors; `verify_cycle_closure × 4 pkgs` reporta el estado
  esperado (PASS para los 3 limpios + estado actualizado para matriz post-BUG-01).
- [ ] **LIVE-02**: `matriz-client` async REST (`aio.py`) verificada live como
  parte de `main_matriz.py --async` o equivalente; mismo set de probes que la
  superficie sync.

---

## Future Requirements (Defer to v1.2+)

- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff)
- `matriz_client.ws_client` live verification (WebSocket streaming en daemon thread)
- IOL refresh_token disk persistence (secure token storage)
- Generated-code parity tooling (one source, dual emit via unasync/codegen)
- Automatic `Idempotency-Key` header para retried POSTs
- `findings.toml` machine-readable side-file
- `client.with_options(max_retries=N)` per-call override (anthropic/openai pattern)
- `Client.from_env()` classmethod for explicit env-reading
- `request_id` UUID per `_request()` invocation threaded through retry log records
- `max_elapsed_seconds` retry budget cap as belt-and-suspenders
- Extender alcance de verificación a `wallets-client` (cuando tenga endpoints reales)
- ERR-01 (mocked 403/429/5xx mapping), ERR-02 (mocked token TTL refresh) — v2
  requirements del v1.0 backlog

---

## Out of Scope (v1.1 explicit exclusions)

- **prod vs remarkets en matriz** — D-MATZ-27 sigue REQUIRED pero queda para v1.2;
  v1.1 sigue remarkets-only (mutating gate exige hostname remarkets exacto).
- **WebSocket layer** — `matriz_client.ws_client` no se verifica live ni se refactoriza;
  la capa daemon-thread queda intacta (sólo `_token` sharing vía `TokenStore` cambia).
- **Nuevos paquetes** — no se extiende a `wallets-client` ni se agregan nuevos clientes.
- **Nuevos endpoints / superficies live nuevas** — la superficie pública de cada paquete
  se mantiene; nada nuevo, sólo refactor y fixes.
- **Cambios breaking en API pública** — v1.1 es minor; cualquier cambio breaking
  se difiere a v2.0 (la clase `Client` se expone, pero las top-level functions
  siguen funcionando idénticas).
- **Refactors de excepciones** — la jerarquía `<Pkg>ClientError` → `APIError` →
  `AuthError`/`RateLimitError` se mantiene; sin nuevos tipos ni cambios de nombres.
- **PyPI publication** — fuera del alcance del milestone (sigue la convención del
  proyecto).

---

## Traceability

*Filled by roadmap (see `ROADMAP.md`)*

| REQ-ID   | Phase     | Status |
|----------|-----------|--------|
| REFAC-01 | Phase 6   | Open   |
| REFAC-02 | Phase 6   | Open   |
| REFAC-03 | Phase 7   | Open   |
| REFAC-04 | Phase 10  | Open   |
| RELY-01  | Phase 8   | Open   |
| RELY-02  | Phase 8   | Open   |
| RELY-03  | Phase 8   | Open   |
| RELY-04  | Phase 8   | Open   |
| LOG-01   | Phase 8   | Open   |
| LOG-02   | Phase 8   | Open   |
| LOG-03   | Phase 8   | Open   |
| BUG-01   | Phase 9   | Open   |
| BUG-02   | Phase 9   | Open   |
| BUG-03   | Phase 9   | Open   |
| BUG-04   | Phase 9   | Open   |
| HARN-07  | Phase 11  | Open   |
| HARN-08  | Phase 11  | Open   |
| HARN-09  | Phase 11  | Open   |
| HARN-10  | Phase 11  | Open   |
| CR-01    | Phase 11  | Open   |
| CR-02    | Phase 11  | Open   |
| CR-03    | Phase 7   | Open   |
| CR-04    | Phase 11  | Open   |
| CR-05    | Phase 7   | Open   |
| CR-06    | Phase 11  | Open   |
| CR-07    | Phase 11  | Open   |
| CR-08    | Phase 11  | Open   |
| LIVE-01  | Phase 11  | Open   |
| LIVE-02  | Phase 10  | Open   |

**Coverage:** 29/29 requirements mapped to exactly one phase ✓

---

*Total: 29 requirements across 7 categories. Created 2026-06-10 for v1.1
Tech Debt Cleanup milestone. Traceability table populated 2026-06-10 by
roadmap.*
