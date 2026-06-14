# market-libs — Verificación en vivo de clientes

## What This Is

Ciclo de verificación exhaustiva de las librerías cliente del monorepo `market-libs`.
El objetivo es ejercitar la API pública completa de cada cliente verificable —en sus
superficies **sync** (`client.py`) y **async** (`aio.py`)— contra las **APIs financieras
en vivo**, detectar bugs y discrepancias entre el comportamiento del cliente y lo que
devuelve el servicio real, y corregirlos en el mismo ciclo. El vehículo de verificación
son los scripts `main_*.py` de la raíz, hoy mínimos, que se extienden para cubrir toda
la superficie de cada paquete.

Alcance: 4 de los 5 paquetes — `iol-client`, `higyrus-client`, `matriz-client` y
`ambito-financiero-client`.

## Core Value

Confianza de que cada cliente refleja fielmente el comportamiento real de su API: cada
divergencia entre el cliente y el servicio en vivo debe ser detectada, documentada y
corregida.

## Current State

**v1.1 Tech Debt Cleanup shipped** (2026-06-14) — 6 phases / 30 plans / 29/29 requirements satisfied / 907 tests green on Python 3.12. Milestone audit `passed` with 29/29 cross-phase integration wired and 9/9 E2E flows complete. The four packages now share a consistent architectural shape: `Client`/`AsyncClient` classes per package backed by `_ClientState` (with the public `pkg.get_X(...)` API preserved 100% via a PEP 562 shim), pure `_core.py` builders/parsers with import-linter contracts blocking re-coupling, `RetryTransport`/`AsyncRetryTransport` with full-jitter backoff + mutation-aware gate + `Retry-After` cap, per-package `RedactingFilter` over `logging.getLogger("<pkg>")`, and the four v1.0 deferred bugs (BUG-01..04) closed with regression coverage. Matriz now has a full async REST surface (`aio.py` 852 LOC) backed by a 3-way concurrent `TokenStore` (`threading.Lock` callable from sync REST, asyncio context via `asyncio.to_thread`, and the `ws_client` daemon thread). Driver hardening landed via `verification/findings.py` append-only BEGIN/END parser + content-addressed dedupe + operator-field preservation. Live re-verification × 4 packages PASS (operator dispositions: ambito/iol/higyrus/matriz all `no_new_findings`; iol F-02 PROBE_STALE fixed inline via the INT-01 idiom at `main_iol.py:1289`).

## Next Milestone Goals (v1.2 — planning)

Tentative scope inherited from v1.1 backlog and v1.0 carry-forwards (final selection happens in `/gsd-new-milestone`):

- **prod-vs-remarkets verification** for matriz (D-MATZ-27 REQUIRED handoff — v1.0 deferred, v1.1 explicitly out of scope).
- **`matriz_client.ws_client` live verification** (WebSocket streaming over daemon thread; v1.0/v1.1 deferred).
- **IOL refresh_token disk persistence** (v1.1 BUG-03 closed in-instance; disk-persisted secure token storage carried forward).
- **Driver migration** to consume the `Client`/`AsyncClient` classes directly (closes the LOC-drop SC#3 partial on iol -5.1% and matriz client.py -20% that v1.1 documented as operator-accepted).
- **Generated-code parity tooling** (one source, dual emit via `unasync` / codegen — closes the known sync/async duplication tech debt).
- **Automatic `Idempotency-Key` header** for retried mutating POSTs (belt-and-suspenders on the mutation gate).
- **`findings.toml` machine-readable side-file** alongside the markdown findings.
- **`client.with_options(max_retries=N)` per-call override** (anthropic/openai pattern).
- **Verification scope extension to `wallets-client`** if real endpoints land.

<details>
<summary>v1.1 Current Milestone block (shipped, archived for reference)</summary>

**Goal:** Saldar la deuda técnica arquitectónica y los hallazgos diferidos de v1.0 — refactor a clase Client por instancia (con compat layer no-breaking), deduplicación sync/async con creación de `aio.py` para matriz-client, retries/backoff con jitter, logging estructurado, fix de los 4 findings/bugs deferred, hardening del harness y cierre de los 8 concerns del code review final de Phase 5.

**Target features:**
- Refactor "clase `Client` por instancia" en los 4 paquetes — eliminar singleton de módulo, mantener API top-level vía compat layer (no breaking).
- Deduplicación lógica sync/async por paquete + creación de `aio.py` para `matriz-client` (hoy sync-only) y su verificación live.
- Retries/backoff transparente con jitter para 5xx/429/connection-errors — respeta el `mutating_allowed` double-gate (no retry de mutaciones).
- Logging estructurado con stdlib `logging` por paquete — integrado con `verification/redaction.py` (Bearer + patrones existentes).
- Fixes pendientes: F-09 matriz ERROR-MAP, higyrus F-02 (`get_listado_cuentas=0`), IOL refresh_token persistence, HIGY multi-account iteration.
- Driver bug bundle: D-MATZ-27 dedupe + `verification/findings.py` append-only (preserva rationale operator) — aplica a los 4 drivers.
- Code review concerns WR-01..WR-08 (8 ítems del review final de Phase 5).

**Out of scope para v1.1:**
- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff) — defer a v1.2
- `matriz_client.ws_client` live verification (capa WebSocket) — defer a v1.2
- Extender alcance a `wallets-client` o nuevos paquetes — defer
- Nuevos endpoints o superficies live nuevas — defer

**Outcome:** 6/6 phases delivered; 29/29 requirements satisfied; integration audit `passed`. Full archive: [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md).

</details>

## Requirements

### Validated

<!-- Inferido del codebase existente (ver .planning/codebase/). -->

- ✓ Monorepo uv con 5 paquetes cliente HTTP independientes y publicables — existing
- ✓ Superficie sync (`client.py`) en los 5 paquetes — existing
- ✓ Superficie async (`aio.py`) en iol, higyrus, ambito, wallets — existing
- ✓ Estrategias de auth por paquete (OAuth2 IOL, Bearer Higyrus, X-Auth-Token Matriz/Primary, sin auth Ámbito) — existing
- ✓ Jerarquía de excepciones tipadas por paquete — existing
- ✓ Refresco de token perezoso con caché y TTL por paquete — existing
- ✓ Suites de pytest con HTTP mockeado (`pytest-httpx`), sync y async — existing
- ✓ CI en GitHub Actions (ruff, mypy strict, pytest; matriz 3.12/3.13) — existing
- ✓ Scripts `main_*.py` de smoke-test manual (login + 1-2 funciones) — existing
- ✓ Harness de verificación en vivo: gate de credenciales (`require_env`), doble gate de mutación (`mutating_allowed`, hostname remarkets exacto), redacción (`redact`/`safe_print` + patrón Bearer), marker `@pytest.mark.live` con `--live`, formato de hallazgos clasificado y pipeline payload→anonimización→fixture (HARN-01..06) — Validado en Phase 1 (2026-05-28)
- ✓ Verificación completa de `ambito-financiero-client` (sync+async) contra API pública — Validado en Phase 2
- ✓ Verificación completa de `iol-client` (sync+async) contra IOL en vivo — Validado en Phase 3
- ✓ Verificación completa de `higyrus-client` (sync+async) contra Higyrus en vivo, con fix in-cycle de 10 sites envelope-key indexing + 6 sites httpx %2F wire encoding — Validado en Phase 4 (2026-06-09)
- ✓ Verificación sync (REST) de `matriz-client` contra Primary/remarkets en vivo, con fix in-cycle de 18 sites envelope-key indexing + _token RuntimeError guard + §6.3 GET-as-write docstrings + 19 regressions — Validado en Phase 5 (2026-06-10)
- ✓ DRIFT-02 cycle closure: baseline `verification-cycle-2026-Q2` con `CYCLE-REPORT.md` consolidado (4 pkgs, 14 findings, 18 schemas, `verify_cycle_closure × 4`) y commit canónico forensic-localizable — Validado en Phase 5 (2026-06-10)
- ✓ Bug/discrepancia documentado por cada paquete: 1 ámbito + 1 iol + 2 higyrus + 10 matriz = 14 findings con clasificación operator-driven (CONFIRMED/FIXED/EXPECTED/NO-FIX) — Validado en Phases 2-5
- ✓ Regression tests mockeados por cada bug confirmado fixeado in-cycle (24+ higyrus en Phase 4 + 19 matriz + 4 code-review-BLOCKER regressions en Phase 5) — Validado en Phases 4-5
- ✓ REFAC-03 `_core.py` extraction per paquete (ambito/iol/higyrus/matriz): builders/parsers puros + auth-flow primitives en `_core.py`, `client.py`/`aio.py` colapsados a transport shells, `import-linter` v2.11 + 4 forbidden contracts en CI, cross-leak sentinel test `SYNC-/ASYNC-sentinel-<pkg>` runtime guard, B8 alias `aio._raise_for_response is client._raise_for_response is _core.raise_for_response` preservado. CR-03 cerrado (`parse_envelope_response` body-consume-before-raise HTTP/2 safe). CR-05 cerrado (15 sweep probes migradas a `_envelope_probe(envelope_key=...)` + 2 risk con `envelope_key=None` + 3 custom side-effect preserved). Code review in-cycle: 6/6 critical+warning fixed con regression tests (CR-01 higyrus raise_for_response 2xx guard + CR-02 parse_get_health_response 204 handling + WR-01..04). LOC drop partial: ámbito -31.2% + higyrus -33% PASS, iol -5.1% + matriz client.py -20% deviation documentada (back-compat surface; v1.2 driver migration cierra el gap). 527 passed + 2 skipped en suite final. — Validado en Phase 7 (2026-06-12)
- ✓ RELY-01..04 + LOG-01..03 retries + structured logging cross-paquete: `_transport.py` (sync `RetryTransport(httpx.HTTPTransport)`) + `_atransport.py` (`AsyncRetryTransport`, 3 paquetes — matriz deferred a Phase 10 REFAC-04 per D-25) + `_logging.py` (`RedactingFilter(logging.Filter)` per-paquete con patrones de Bearer/X-Auth-Token/password=/IOL refresh_token/Higyrus JSON password/matriz auth_basic tuple-split per D-22) duplicados 4×. `tenacity 9.1.4` agregado a runtime deps de los 4 paquetes (Apache-2.0, `py.typed`, zero-deps). Backoff full-jitter (base=1s, max=30s, exp=2), Retry-After cap 60s, mutation gate vía `request.extensions["idempotent"]` (matriz mutating new_order/cancel_order/replace_order builders KEEP `idempotent=False` per Pitfall 4 CRITICAL — duplicate-order risk MITIGATED). 401 re-auth-once en shell `_request()` (AuthError NUNCA en retry_on=); D-23 matriz Risk API auth_basic carve-out skip re-auth; D-24 PrimaryAPIError NUNCA retry. Public API: `Client/AsyncClient.__init__` + `configure()` ganan `max_retries: int = 2` + `http_client` kwargs (validated non-negative int per WR-06 fix). 6 cross-cutting guard tests parametrizados en `verification/` (mutation gate, 401 reauth, Retry-After cap, root logger unchanged, no token leak, async cancellation). Code review in-cycle: 7/7 critical+warning fixed con regression tests (CR-01 + CR-02 guard tests rewritten to exercise real Risk surface; WR-01 atomic token-clear+ensure-token async; WR-02 `resp.read()` before 401 carve-out raise; WR-06 max_retries validation; WR-07 `aio.configure()` ResourceWarning; WR-08 matriz typed exception map). 755 passed + 3 skipped (vs 527 Phase 7 baseline → +228 net, +128 regression tests post-review-fix). matriz `aio.py` line count = 103 (Phase 6 stub UNCHANGED per D-25). — Validado en Phase 8 (2026-06-13)
- ✓ BUG-01..04 deferred bug fixes: **BUG-01** (F-09 matriz CFI ERROR-MAP) hybrid Literal+regex guard pre-HTTP en `_core.py::build_get_instruments_by_cfi_request` (Pattern S5: `\A[A-Z]{6}\Z` anchors + `_CFI_LITERAL_VALUES = frozenset(get_args(CFICode))` + `isinstance(cfi_code, str)` post-review guard). Deviation D-02: guard vive en builder, no en `raise_for_response` (que solo ve `httpx.Response`). 16 parametric tests cubren 3 buckets (literal-known × 2, regex forward-compat × 2, malformed × 12 incl. trailing whitespace + non-str). F-09 CONFIRMED→FIXED; `cycle_closure_matriz_client` FAIL→PASS live confirmed; `probe_error_malformed_cfi` PASS live. **BUG-02** (F-02 higyrus `get_listado_cuentas=0`) bucket (a) NO-FIX account-state-conditional autorizado por operator después de live triage N=3: `get_listado_cuentas` devuelve `[]` 3/3 consistente mientras `get_movimientos=139` + `get_posiciones=76` + `get_posicion_valuada=390` en la misma sesión — server-side envelope HTTP 200 con body vacío legítimo (token actual sin scope a cuentas en estado=alta). Contract guard `test_get_listado_cuentas_url_con_estado_alta` (existing) preserva regresiones client-side. **BUG-03** (IOL refresh_token persistence) 8 regression tests (4 sync + 4 async) cubren los 4 paths del lifecycle: refresh→success, refresh→401→password fallback, preserve-on-omit (CR-01 FALSE), rotate-on-provide (CR-01 TRUE) — cero cambios en `packages/iol-client/src/` porque el código ya estaba en producción desde Phase 6 D-IOL-10 (test-only consolidation). **BUG-04** (HIGY multi-account iteration) D-08 per-call only locked (constructor `Client(account_id=X)` deferred a v1.2): mocked test `test_multi_account.py` (2 cuentas, wire URLs distintas) + driver probe `probe_multi_account_iteration` en `main_higyrus.py` (source order: `HIGYRUS_SAMPLE_CUENTAS` CSV > live `get_listado_cuentas` > SKIPPED); live PASS con cuentas 5208,56227. D-09 cross-package cleanup: `_state.account_id` removido de higyrus AND iol (cross-leak sentinel preserved). Phase 6 migration drift surfaced en `main_higyrus.py` y reparado: 21 sites migrados de `{higyrus_client.client,aio}._base_url` → `_get_default()._state.base_url` (initial shim-extension approach `67ca550` reverted en `c1371fb` por violar contract Phase 6/7). Code review in-cycle: 4/4 warnings fixed (`8e48e3b`) con +6 parametric tests para CFI edge cases (trailing newline/whitespace + non-str bypass). 782 passed + 3 skipped (matriz Phase 10 stub) vs 760 baseline Phase 8 → +22 net. — Validado en Phase 9 (2026-06-13)
- ✓ REFAC-04 + LIVE-02 matriz async REST surface + TokenStore 3-way concurrency: `matriz_client/aio.py` (103-LOC stub → 852 LOC full REST mirror que delega a `_core` builders/parsers; D-25 invariant lifted). `_atransport.py` (173 LOC `AsyncRetryTransport`) cierra el carve-out de Phase 8. `_token_store.py:54` expone `threading.Lock` callable desde sync REST, ws_client daemon thread, y asyncio context (vía `asyncio.to_thread` offload); per-loop `asyncio.Lock` lazy-initialized via `_get_async_lock()` evita thundering-herd inter-loop. `_refresh_policy.py` agrega retry/backoff/fail-cache para prevenir DOS del auth server. BUG-01 CFI guard ahora reachable desde async (`aio.py:447-450` → `_core.build_get_instruments_by_cfi_request`); 3 D-25 skips pre-existentes (`test_fixture_reaches_production`, `test_async_cancellation`, `test_sync_async_isolation`) ahora son tests activos + 1 nuevo (`test_matriz_sync_async_state_and_token_store_instance_isolation`). LIVE-02 paridad sync/async: 19 paired probes en una sola `main()` interleaved (sin `--async` flag, per D-06), 0 divergences, operator signoff 2026-06-14. — Validado en Phase 10 (2026-06-14)
- ✓ HARN-07..10 + CR-01/02/04/06/07/08 + LIVE-01 harness hardening + code-review close-out + live re-verification: `verification/findings.py` (640 LOC) implementa BEGIN/END zone parser + append-only contract + content-addressed `idempotent_by_title` dedupe + cross-run preservation de campos operator (Classification/Rationale/Regression/Resolution); los 4 drivers (`main_*.py`) consumen la nueva API; `main_matriz.py` D-MATZ-27 EXPECTED finding idempotently deduped (HARN-10). 18 sweep probes en `main_matriz.py` migrados a helper único `_envelope_probe(envelope_key=...)` (CR-05); `probe_schema_snapshot` sample_params alineado con PRIMARY_ACCOUNT (CR-01); `probe_login_sync` unificado a `"FINDING"` (CR-02); `_first_dict` distingue no_data/wrong_type/ok (CR-04); 27 sitios de `except Exception` narrowed con AST regression-guard (CR-06: 10 matriz + 17 higyrus); `_capture_*_query_string` en `main_higyrus.py` lock-protected (CR-07); spike-artifact ruff exclusion + `main_higyrus.py:767` line-length (CR-08). LIVE-01 milestone-final gate ejecutado 2026-06-14: baseline `4d48e07` → head `71bf201`, dispositions ambito/higyrus/matriz=`no_new_findings`, iol F-02 PROBE_STALE FIXED inline usando idiom INT-01 en `main_iol.py:1289` (módulo namespace write shadowing PEP 562 `__getattr__`; root cause = probe stale, no bug del client `_refresh()`). 21/21 security threats verificados (HARN + CR + LIVE-01). 907 tests passing (+125 vs Phase 9 baseline). — Validado en Phase 11 (2026-06-14)

### Out of Scope

<!-- Límites explícitos con su razón, para no re-incorporarlos. -->

- `wallets-client` — stub sin endpoints reales y con URL placeholder; nada que verificar en vivo
- Superficie async de `matriz-client` — no existe `aio.py`; su "async" es solo la capa WebSocket
- Streaming WebSocket de `matriz-client` — capa basada en thread daemon; fuera de alcance este ciclo
- Publicación a PyPI — no forma parte de la verificación
- Refactors arquitectónicos (clase `Client` por instancia, deduplicación sync/async, retries/backoff, logging estructurado) — tech debt conocido, no es el foco de este ciclo

## Context

- **Current state (post-v1.1):** 4 de 5 paquetes están **verificados end-to-end contra sus APIs reales** Y comparten una arquitectura coherente: `Client`/`AsyncClient` classes per package con `_ClientState` per-instance detrás de un PEP 562 shim que preserva 100% la API top-level; pure `_core.py` builders/parsers con import-linter contracts; `RetryTransport`/`AsyncRetryTransport` con full-jitter backoff + mutation gate + Retry-After cap (60s) + exactly-one 401 re-auth; per-package `RedactingFilter` sobre `logging.getLogger("<pkg>")` con `NullHandler`. Matriz tiene full async REST surface (`aio.py` 852 LOC) con `TokenStore` 3-way concurrente (sync REST + asyncio + ws_client daemon thread comparten un único `threading.Lock`). `wallets-client` sigue stub (sin endpoints reales).
- **Stats v1.1 cycle:**
  - 907 mocked tests passing on Python 3.12 (vs 277 al cierre de v1.0 → +630 net; +122 vs último audit pre-Phase-11)
  - 6 phases / 30 plans / 29 requirements (REFAC-01..04, RELY-01..04, LOG-01..03, BUG-01..04, HARN-07..10, CR-01..08, LIVE-01..02)
  - 179 commits + 307 archivos tocados + 76,286 insertions / 3,538 deletions
  - Test suite delta: 277 → 785 (Phase 9 baseline) → 907 (post-Phase 10 + Phase 11)
  - 4 v1.0-deferred bugs cerrados (2 con override operator-autorizado: BUG-02 bucket (a) NO-FIX + BUG-01 D-02 builder-side guard)
  - 8 code-review concerns cerrados (CR-01..08); LIVE-01 final gate PASS × 4 paquetes con iol F-02 fixed inline via INT-01 idiom
  - Audit: 29/29 reqs satisfied, 9/9 E2E flows complete, 29/29 integration wired, 0 BLOCKER, 1 cosmetic WARNING cerrada (ORP-01)
  - Quick tasks: 3 (260611-u0v CI fixes, 260613-nwb INT-01 hotfix, 260614-de5 DOC-01..04 close-out)
- **Tech stack mantenido:** Python 3.12+, uv, httpx (sync+async), pytest+pytest-httpx, ruff (rule sets E/W/F/I/B/UP/SIM/RUF/ASYNC/PIE/PT/RET/TID), mypy strict, `tenacity 9.1.4` (zero-deps, py.typed, Apache-2.0). CI matrix Python 3.12 + 3.13 verde (3.13 confirmación humana pendiente por phase). Sin cambios arquitectónicos al nivel de monorepo: los packages siguen siendo standalone wheels sin shared internals (por diseño — duplicación intencional 4×).
- **Harness module** `verification/`: además de los módulos v1.0 (redaction, env_gate, mutation_gate, findings, schema, capture, anonymize, safemodel_diff, cycle_report), Phase 11 reemplazó `findings.py` por una implementación append-only con BEGIN/END zone parser, content-addressed `idempotent_by_title` dedupe, y operator-field preservation cross-runs (Classification/Rationale/Regression/Resolution); idempotent re-run = git-clean.
- **Spike findings auto-loaded:** `Skill("spike-findings-market-libs")` cubre los dos blockers de Phase 10 (TokenStore 3-way concurrency primitive + refresh policy con retry/backoff/fail-cache) — ambos validados in-flight y reflejados en `_token_store.py:54` + `_refresh_policy.py`.
- **Mapa de codebase disponible:** `.planning/codebase/` (ARCHITECTURE, STACK, STRUCTURE, TESTING, CONCERNS, CONVENTIONS, INTEGRATIONS) — actualizar antes del próximo cycle si v1.2 cambia el shape de los packages (p.ej. driver migration o unasync codegen).

## Constraints

- **Tech stack**: Python 3.12+, uv, httpx (sync+async), pytest+pytest-httpx, ruff, mypy strict — toda extensión y fix debe respetar el stack y pasar el CI existente.
- **Arquitectura**: estado singleton a nivel de módulo; sin código compartido entre paquetes (por diseño). Los fixes se aplican dentro de cada paquete, sin introducir dependencias cruzadas.
- **Dual sync/async**: cualquier fix de lógica debe espejarse en `client.py` y `aio.py` del mismo paquete (deuda conocida: la lógica está duplicada).
- **Seguridad**: las credenciales viven en `.env` por paquete; nunca commitear `.env` ni exponer credenciales en logs, reportes o tests.
- **Dependencias externas en vivo**: la verificación depende de la disponibilidad y el estado real de servicios de terceros; resultados pueden variar por horario de mercado, datos disponibles o rate limits.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Verificar contra APIs en vivo (no mock) | El objetivo es detectar divergencias reales cliente-vs-servicio, que el mock oculta | ✓ Good — v1.0 detectó 14 findings reales (1 ámbito + 1 iol + 2 higyrus + 10 matriz) que mock no expone |
| Vehículo = scripts `main_*.py` extendidos | Ya existen como smoke-test manual; extenderlos cubre toda la superficie sin nueva infraestructura | ✓ Good — Phase 2-5 expandieron de ~57 LOC smoke a 1500-2000 LOC drivers con ~25 probes nombrados cada uno |
| Cubrir sync + async | Ambas superficies pueden divergir; la lógica está duplicada y puede haber bugs solo en una | ✓ Good — Phase 4 fixeó 10+6 sites en `client.py` y `aio.py` de higyrus en paralelo; paridad sync↔async verificada |
| Reportar y arreglar en el mismo ciclo | El usuario quiere cerrar el loop: hallazgo → corrección | ✓ Good — higyrus +18 envelope + 6 wire encoding fixes, iol refresh_token fix, matriz envelope `_unwrap × 18` + `_token` raise — todos in-cycle |
| Cada fix con test de regresión mockeado | Evita que el bug regrese; sigue la convención existente del codebase | ✓ Good — Phase 4: 24 higyrus regressions; Phase 5: 19 matriz regressions + 4 code-review BLOCKER regressions; total ~52 nuevos regression tests cubriendo fixes |
| Excluir `wallets-client` | Es un stub sin endpoints reales ni servicio verificable | ✓ Good — no se tocó; sigue stub esperando endpoints reales |
| Excluir WebSocket/async de matriz | Capa thread-based sin contraparte async; fuera de foco | ⚠️ Revisit — confirmado como out-of-scope para v1.0; matriz async surface es candidato explícito para v1.1+ |
| Promotion de helpers cross-package (Phase 5 D-MATZ-18) | El `diff_safemodel_bidirectional` y `verify_cycle_closure` necesitaban duck-typing cross-package para servir a higyrus+matriz desde `verification/` | ✓ Good — `verification/safemodel_diff.py` + `verification/cycle_report.py` promovidos; main_higyrus.py retrofitted; verify_cycle_closure × 4 paquetes WIRED y ejercitado live |
| F-09 deferred + cycle_closure FAIL como señal DRIFT-02 (Phase 5 Op A) | Operator decidió no fixear F-09 en este cycle; el FAIL es la señal que cierra DRIFT-02 (el ciclo detecta su propio gap) | ✓ Good — Cerrado en v1.1 Phase 9 BUG-01: hybrid Literal+regex CFI guard en `_core.py`, `cycle_closure_matriz_client` FAIL→PASS live |
| PEP 562 `__getattr__` shim para preservar API top-level (v1.1 Phase 6) | Refactor a clase Client por instancia sin romper consumidores que importan `pkg.get_X(...)`; el shim delega lazy a un `_get_default()` singleton interno | ✓ Good — los 4 paquetes; baseline 277 tests verde post-refactor; `_FORWARDED_TO_STATE` mantiene compatibilidad con `mutation_gate.py` que lee `matriz_client.client._base_url` |
| `_core.py` extraction direction (v1.1 Phase 7) | `client.py`/`aio.py` colapsan a transport shells (~30-50 LOC por endpoint) que llaman a `_core` builders/parsers puros; import-linter bloquea la dirección inversa | ✓ Good — 4/5 SC PASS + 1 PARTIAL (LOC drop iol -5.1% / matriz -20% operator-accepted como v1.2 driver-migration target); CR-03 body-consume-before-raise HTTP/2 safe; CR-05 18 sweep probes a helper único |
| Mutation gate vía `request.extensions["idempotent"]` (v1.1 Phase 8 Pitfall 4) | `_transport` no debe importar de `_core` (decoupling); el flag viaja en el httpx request object | ✓ Good — matriz `new_order`/`cancel_order`/`replace_order` mantienen `idempotent=False`; mocked test `test_retry_mutation_gate.py` Pitfall 4 PASS asegura duplicate-order prevention |
| `AuthError`/`PrimaryAPIError`/`HigyrusAPIError` NUNCA en `retry_on=` (v1.1 Phase 8 D-24) | Las excepciones de API son señal definitiva, no transitorio — re-intentar amplifica el daño y enmascara root cause | ✓ Good — `RELY-04` re-auth-once vive en shell `_request()`, no en tenacity; verificado con `test_retry_401_reauth.py` (7 cases) |
| TokenStore con `threading.Lock` callable desde asyncio context (v1.1 Phase 10) | El ws_client daemon thread requiere `threading.Lock`; el async REST puede llamarlo vía `asyncio.to_thread` offload + per-loop `asyncio.Lock` para evitar thundering-herd inter-loop | ✓ Good — spike validó la receta antes del plan; `_token_store.py:54` + `_get_async_lock()` operacional; live paridad sync/async PASS con 19 paired probes (LIVE-02) |
| INT-01 idiom: `_get_default()._state.base_url` para acceso desde drivers (v1.1 quick-task 260613-nwb + Phase 11 F-02) | El refactor Phase 6 movió `_base_url` a `_DENIED_LEGACY`; los drivers `main_*.py` que escribían/leían el atributo directo necesitan migrar al state | ✓ Good — `main_iol.py` 15 sites + post-refactor F-02 PROBE_STALE FIX usando el mismo idiom; documentado como pattern oficial post-Phase-6 |
| Driver findings append-only con BEGIN/END zones (v1.1 Phase 11 HARN-07/08/09) | Re-runs de los drivers deben preservar campos operator (Classification/Rationale/Regression/Resolution) Y ser idempotent (re-run = git-clean) | ✓ Good — `verification/findings.py` 640 LOC + content-addressed `idempotent_by_title` dedupe; 4 drivers migrados; preserves operator-prefix con ART block refresh in-place |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-14 after v1.1 milestone — Tech Debt Cleanup shipped (6 phases / 30 plans / 29/29 requirements / 907 tests on Python 3.12 / audit `passed`). Phases 6–11 delivered: PEP 562 compat shim + Client/AsyncClient classes (REFAC-01/02); `_core.py` extraction with import-linter (REFAC-03 + CR-03/05); retries/backoff/logging (RELY-01..04 + LOG-01..03); 4 v1.0 deferred bugs closed with 2 operator overrides (BUG-01..04); matriz async REST + TokenStore 3-way concurrency (REFAC-04 + LIVE-02); harness hardening + 6 CR concerns + LIVE-01 final gate × 4 packages (HARN-07..10 + CR-01/02/04/06/07/08 + LIVE-01). v1.0 archived (5 phases / 18 plans / 35/35 requirements / 277 tests / DRIFT-02 baseline `verification-cycle-2026-Q2`). v1.2 planning starts via `/gsd-new-milestone` — candidate scope: prod-vs-remarkets verification, ws_client live, refresh_token disk persistence, driver migration to Client class, unasync/codegen for sync/async parity.*
