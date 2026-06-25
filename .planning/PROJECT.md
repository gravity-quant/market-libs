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

**v1.2 Architecture + Auth/Ergonomics Carry-forwards shipped** (2026-06-25) — 5 phases (12-15, 17; Phase 16 dropped) / 18 plans / 4/4 active requirements satisfied (REFAC-05, SEC-01, ERG-01, LIVE-03) / pytest ≥989 green on Python 3.12 + 3.13; shipped via PR #2. The residual v1.1 architectural debt is now closed: the four internal drivers (`main_*.py`) each construct **exactly one** `Client()` + one `AsyncClient()` per `main()` run with every probe threaded through that instance (AST single-Client regression guard per driver), closing the iol/matriz LOC-drop residual; `client.with_options(max_retries=N)` is live across all 4 packages as a shared-view clone that threads the override via `request.extensions["max_attempts"]` while the matriz mutation gate still executes exactly 1 outgoing `new_order` under 503; IOL gained `_token_cache.py` refresh_token disk persistence (atomic write-then-rename + `fcntl.flock` + 0600 + `platformdirs` default + failed-refresh cleanup + caplog no-leak, sync+async). The one architectural unknown — unasync/codegen single-source (REFAC-06) — returned a signed **NO-GO** at Phase 12 (source-shape asymmetry, 3/8 D-RIGOR-01 items FAIL, 0 unfixable hunks) and is deferred to v1.3 with a dedicated `libcst` spike (Phase 16 dropped). Final live re-verification × 4 packages PASS (operator dispositions captured; cycle closure × 4 PASS vs baseline `verification-cycle-2026-Q2`; 0-BLOCKER integration audit). The public top-level `pkg.get_X(...)` API stayed 100% backwards-compatible via the PEP 562 shim — v1.2 was a non-breaking minor.

## Next Milestone: v1.3 (planning)

Not yet started. Run `/gsd:new-milestone` to define scope. Leading carry-forward candidate is **REFAC-06** (unasync/codegen single-source) via a `libcst >=1.8.0,<2` spike per the Phase 12 NO-GO decision D-NOGO-01 (`.planning/todos/pending/spike-codegen-libcst-v1.3.md`), plus the standing deferrals (prod-vs-remarkets matriz verification D-MATZ-27, `matriz_client.ws_client` live verification, token encryption at-rest). See ROADMAP.md Backlog.

<details>
<summary>v1.2 Current Milestone block (shipped 2026-06-25, archived for reference)</summary>

**Goal:** Cerrar la deuda arquitectónica residual de v1.1 — migrar los 4 drivers `main_*.py` a consumir `Client`/`AsyncClient` directamente (cierra el LOC drop residual iol -5.1% / matriz -20%), eliminar la duplicación estructural sync/async vía unasync/codegen single-source, agregar IOL refresh_token disk persistence (secure token storage), y exponer ergonomics cross-package (`Client.from_env()` + `client.with_options(max_retries=N)`).

**Outcome:** 5/6 phases delivered (Phase 16 codegen DROPPED per Phase 12 NO-GO); 4/4 active requirements satisfied (REFAC-05, SEC-01, ERG-01, LIVE-03); REFAC-06 deferred to v1.3; integration audit 0-BLOCKER. `Client.from_env()` was SKIPPED (industry survey of 7 SDKs found ZERO with the pattern; implicit env fallback already exists). Full archive: [`milestones/v1.2-ROADMAP.md`](./milestones/v1.2-ROADMAP.md).

**Target features (as planned):**

### Arquitectura sync/async dedup
- Driver migration × 4 packages (`main_ambito` → `main_iol` → `main_higyrus` → `main_matriz`) a consumir `Client`/`AsyncClient` directamente vía instancias — cierra el LOC drop residual (iol -5.1%, matriz client.py -20%). **✓ Phase 15 (REFAC-05)**
- Single-source sync/async via unasync/codegen approach — spike-validated antes del plan. **✗ Phase 12 NO-GO; REFAC-06 → v1.3 libcst spike**
- Re-verificación live `main_*.py --live × 4` al cierre del milestone (LIVE-01-equivalent). **✓ Phase 17 (LIVE-03)**

### Auth/Token persistence + Client ergonomics
- IOL refresh_token disk persistence — secure token storage. **✓ Phase 14 (SEC-01)**
- `Client.from_env()` classmethod × 4 packages. **— SKIPPED (no industry precedent; implicit env fallback exists)**
- `client.with_options(max_retries=N)` per-call override × 4 packages. **✓ Phase 13 (ERG-01)**

**Non-breaking constraint:** v1.2 minor — top-level `pkg.get_X(...)` API 100% backwards-compatible vía el PEP 562 shim de v1.1; solo migraron los drivers `main_*.py` internos.

</details>

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
- ✓ REFAC-05 driver migration × 4: los 4 drivers internos (`main_ambito_financiero.py`, `main_iol.py`, `main_higyrus.py`, `main_matriz.py`) construyen **exactamente una** `Client()` sync en `main()` + una `AsyncClient()` async en `_async_main()`, threadeadas como parámetro a cada probe; cero call-sites `_get_default()` / `pkg.get_X(...)` / `_get_default()._state.<attr>` en código (shims back-compat PEP 562 + delegators QUEDAN intactos). AST-guard por driver (`verification/test_main_<pkg>_uses_single_client_instance.py`, ≤2 ctors, matchea `ast.Name` + `ast.Attribute`); el guard de matriz se reforzó con `test_main_matriz_has_no_singleton_path_references` (no-vacuo) tras code-review WR-01/WR-02. Gate de estabilidad de títulos: `git diff 71bf201..HEAD` estático sobre los 4 `*-findings.md` = cero cambios title/fid/probe-name (D-07; sin re-run live). D-03 forced-refresh write-site (`main_iol.py`) escribe sobre la instancia threadeada exacta. Plan 15-05 cerró el gap de los 18 sweep probes sync de matriz (segundo login / TokenStore split). LOC-drop = attestation-only (D-08; codegen Phase 16 DROPPED). 988→989 tests collected (≥907 baseline); package suites verdes. Live smokes operator-deferred (D-11; gate milestone-final = Phase 17 LIVE-03). — Validado en Phase 15 (2026-06-24)
- ✓ ERG-01 `client.with_options(max_retries=N)` × 4 packages: shallow-clone Client/AsyncClient "view" (`_is_view` flag) que comparte el underlying `httpx.Client` + `_ClientState` + token del parent (sin resource leak, sin re-auth — `test_with_options_shares_http_client_and_token` × 4); el override viaja por `request.extensions["max_attempts"]` que `RetryTransport.handle_request`/`AsyncRetryTransport.handle_async_request` leen con fallback al constructor default (mirror del v1.1 `idempotent` extension). **CRITICAL merge gate**: `client.with_options(max_retries=10).new_order(...)` en matriz Primary ejecuta EXACTAMENTE 1 request bajo 503 (mutation gate evalúa idempotent FIRST; `test_with_options_does_not_bypass_mutation_gate_matriz` httpx_mock `len(requests)==1`) — anti-Pitfall 14 duplicate-order. Per-package serial ámbito → higyrus → matriz → iol (iol último, coexiste con SEC-01); cross-cutting `verification/test_with_options.py` (13 tests) lands once. — Validado en Phase 13 (2026-06-15)
- ✓ SEC-01 IOL refresh_token disk persistence: `iol_client/_token_cache.py` con read-on-init + write-on-rotate atómico (write-then-rename), `fcntl.flock` inter-process locking, `os.chmod(0o600)` POSIX + parent dir 0700, `platformdirs.user_data_dir("iol-client", "market-libs")` default + `IOL_TOKEN_CACHE_PATH` env override + `Client(token_cache_path=Path(...))` opt-in kwarg, CI-detection (`os.environ["CI"]=="true"`) rehúsa default-path persistence (anti-Pitfall 10). 3 CRITICAL merge gates GREEN: caplog no-leak sentinel (anti-Pitfall 7), 20-thread concurrent-write race exactamente-un-token (anti-Pitfall 9), failed-refresh-401 cleanup deletes stale token antes del password fallback (anti-Pitfall 8). 11 verification tests (3 gates + 8 BUG-03 lifecycle × {sync, async}); async mirror dispatcha load/save/delete vía `asyncio.to_thread`; `platformdirs >=4.0,<5` runtime dep en iol-client ONLY (otros 3 paquetes intactos). Code-review CR-01 (`configure()` no limpia el on-disk cache) deferred a v1.3. — Validado en Phase 14 (2026-06-24)
- ✓ LIVE-03 final live re-verification × 4: post-migration LIVE-01-equivalent gate. Operator dispositions capturadas para ambito/iol/higyrus/matriz en `17-VALIDATION.md`; schema snapshot vs baseline `verification-cycle-2026-Q2` sin drift; `verify_cycle_closure × 4` PASS (iol F-02 FIXED finding linkeado a regression test → `(False,['F-02'])`→`(True,[])`); 4 gates determinísticos credential-free attestados GREEN (static title-stability vs `71bf201`, sync/async isolation, credential-leak, public-surface); REQUIREMENTS.md traceability flip REFAC-05/SEC-01/ERG-01/LIVE-03 → Complete; 0-BLOCKER integration audit; pytest final ≥989 + CI matrix verde Python 3.12 + 3.13. Phase 17 STOPS short of ship per D-04; milestone shipped vía PR #2. — Validado en Phase 17 (2026-06-25)

### Out of Scope

<!-- Límites explícitos con su razón, para no re-incorporarlos. -->

- `wallets-client` — stub sin endpoints reales y con URL placeholder; nada que verificar en vivo
- Streaming WebSocket de `matriz-client` — capa basada en thread daemon; live verification deferida a v1.3
- prod-vs-remarkets verification en matriz (D-MATZ-27 REQUIRED handoff) — sigue remarkets-only; defer a v1.3
- Publicación a PyPI — no forma parte de la verificación
- Token encryption at-rest (Fernet/keyring) — trust boundary unchanged vs plaintext `.env`; plaintext file + 0600 + flock es la opción correcta para el threat model actual; defer a v1.3 con operator authorization explícita
- Codegen single-source sync/async (REFAC-06) — unasync NO-GO en Phase 12 (source-shape asymmetry); deferred a v1.3 con `libcst` spike
- `Client.from_env()` classmethod — SKIPPED en v1.2: industry survey de 7 SDKs encontró ZERO con el patrón; implicit env fallback ya existe vía constructor + `load_dotenv()`

<!-- Resuelto: la superficie async de matriz (`aio.py` 852 LOC) se creó en v1.1 Phase 10; los refactors arquitectónicos (clase Client por instancia, dedup sync/async vía _core.py, retries/backoff, logging estructurado) shipearon en v1.1; la driver migration + with_options + disk persistence shipearon en v1.2. -->


## Context

- **Current state (post-v1.2):** 4 de 5 paquetes están **verificados end-to-end contra sus APIs reales** con la deuda arquitectónica residual cerrada: los 4 drivers `main_*.py` consumen una única `Client()`/`AsyncClient()` por run (REFAC-05); `client.with_options(max_retries=N)` disponible × 4 como shared-view clone (ERG-01); IOL tiene refresh_token disk persistence con flock+0600+atomic+failed-refresh-cleanup (SEC-01); re-verificación live × 4 PASS post-migration (LIVE-03). REFAC-06 (codegen single-source) deferred a v1.3 (Phase 12 NO-GO). pytest ≥989 verde en Python 3.12 + 3.13; shipped vía PR #2.
- **Stats v1.2 cycle:** 5 phases (12-15, 17; Phase 16 dropped) / 18 plans / 40 tasks / 4 requirements (REFAC-05, SEC-01, ERG-01, LIVE-03; REFAC-06 deferred). Git range `74b22bf`→`a7dbc8f` (2026-06-14 → 2026-06-25); source delta 43 files +3,364 / −531 LOC. Test suite 907 (v1.1 close) → ≥989. `platformdirs >=4.0,<5` added a iol-client runtime deps. Known deferred at close: 6 (4 stale quick-task status files, REFAC-06→v1.3 libcst spike todo, Phase 15 UAT gap superseded by Phase 17).
- **State (heredado v1.1):** 4 de 5 paquetes comparten una arquitectura coherente: `Client`/`AsyncClient` classes per package con `_ClientState` per-instance detrás de un PEP 562 shim que preserva 100% la API top-level; pure `_core.py` builders/parsers con import-linter contracts; `RetryTransport`/`AsyncRetryTransport` con full-jitter backoff + mutation gate + Retry-After cap (60s) + exactly-one 401 re-auth; per-package `RedactingFilter` sobre `logging.getLogger("<pkg>")` con `NullHandler`. Matriz tiene full async REST surface (`aio.py` 852 LOC) con `TokenStore` 3-way concurrente (sync REST + asyncio + ws_client daemon thread comparten un único `threading.Lock`). `wallets-client` sigue stub (sin endpoints reales).
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
| Codegen tool-choice spike-before-plan + strict D-RIGOR-01 reading → NO-GO (v1.2 Phase 12) | REFAC-06 (unasync single-source) era el único unknown arquitectónico; un 8-item evidence checklist con lectura estricta evita shipear codegen frágil | ✓ Good — NO-GO honesto (3/8 FAIL, root cause = source-shape asymmetry sync-first aio.py vs async-first codegen, 0 unfixable hunks); REFAC-06 → v1.3 libcst spike; Phase 16 DROPPED; Phase 17 unblocked early. Decision firmada por operator |
| `with_options` como shared-view clone vía `request.extensions["max_attempts"]` (v1.2 Phase 13 ERG-01) | Override per-call sin re-instanciar ni re-auth; el extension viaja en el httpx request (mismo patrón que el mutation gate `idempotent`) | ✓ Good — view comparte `httpx.Client` + `_ClientState` + token; mutation gate evalúa idempotent FIRST → matriz `new_order` bajo 503 = exactamente 1 request irrespective of `max_retries=10` (anti-Pitfall 14) |
| Plaintext disk token + 0600 + `fcntl.flock` (rechazado keyring/Fernet) para SEC-01 (v1.2 Phase 14) | Threat model es developer/CI tool: keyring requiere null-backend headless / GUI prompt bloquea unattended; trust boundary == plaintext `.env` existente | ✓ Good — atomic write-then-rename + flock 20-thread race + failed-refresh cleanup + caplog no-leak; `platformdirs` default; CI rehúsa default-path. Fernet/keyring deferred a v1.3 con operator auth |
| ONE Client per `main()` run enforced por AST regression-guard (v1.2 Phase 15 REFAC-05) | Multiple Client instances → OAuth churn (iol) + TokenStore corruption (matriz); el invariante necesita un gate mecánico, no convención | ✓ Good — AST-walker test ≤2 ctors por driver (matriz guard hardened a non-vacuous tras WR-01/WR-02); finding-title stability static-clean vs `71bf201`; cierra LOC-drop residual iol/matriz |
| `Client.from_env()` SKIPPED tras industry survey (v1.2 Phase 13/scope) | El patrón estaba en el roadmap pero un survey de 7 SDKs (anthropic/openai/etc.) encontró ZERO con el classmethod; el constructor ya hace implicit env fallback vía `load_dotenv()` | ✓ Good — evitó superficie redundante; documentado en REQUIREMENTS Future + Out of Scope |

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
*Last updated: 2026-06-25 after v1.2 milestone — **v1.2 Architecture + Auth/Ergonomics Carry-forwards shipped** (5 phases 12-15+17, Phase 16 dropped / 18 plans / 40 tasks / 4-of-4 active reqs REFAC-05+SEC-01+ERG-01+LIVE-03 satisfied / pytest ≥989 green on Python 3.12+3.13 / PR #2). Driver migration to single Client per run (REFAC-05), `with_options(max_retries=N)` × 4 (ERG-01), IOL refresh_token disk persistence (SEC-01), and final live re-verification × 4 (LIVE-03) all landed; REFAC-06 codegen single-source returned NO-GO at Phase 12 (source-shape asymmetry) and defers to v1.3 with a libcst spike; `Client.from_env()` SKIPPED (no industry precedent). 6 deferred items acknowledged at close (see STATE.md / MILESTONES.md). Next: `/gsd:new-milestone` for v1.3. Prior footer below for reference.*

<details>
<summary>Prior footer (v1.2 in-progress, Phase 15)</summary>

*2026-06-24 — Phase 15 (Driver Migration × 4, REFAC-05) complete: the 4 internal drivers each build exactly one sync `Client()` + one async `AsyncClient()`, threaded into every probe (zero `_get_default()`/`pkg.get_X` code call-sites; back-compat shims preserved); per-driver AST-guard tests (matriz guard hardened to non-vacuous after code-review WR-01/WR-02 and plan 15-05 migrated the 18 matriz sync sweep probes off the singleton path); finding-title stability gate static-clean vs `71bf201`; LOC-drop attestation-only (D-08; codegen Phase 16 DROPPED); 989 tests collected (≥907). Live smokes operator-deferred (D-11; milestone-final live re-verification = Phase 17 LIVE-03). Phase 14 (IOL Disk Persistence, SEC-01) complete: `iol_client/_token_cache.py` atomic flock+0600 disk persistence with failed-refresh cleanup + no-token-leak caplog guard, sync+async wired, D-T4 iol-only scope. Known follow-up: code-review CR-01 (`configure()` credential rotation does not clear the on-disk cache) deferred to v1.3. v1.2 milestone started 2026-06-14 (Architecture + Auth/Ergonomics Carry-forwards). Scope locked at 2 clusters: (1) Arquitectura sync/async dedup = driver migration × 4 + unasync/codegen single-source via spike-before-plan flag + final live re-verification; (2) Auth/Token persistence + Client ergonomics = IOL refresh_token disk persistence + `Client.from_env()` × 4 + `client.with_options(max_retries=N)` × 4. In-cycle bug-fix pattern (v1.0/v1.1) carries forward for findings that surface during driver migration. v1.1 shipped 2026-06-14 (6 phases / 30 plans / 29/29 reqs / 907 tests / audit `passed`); v1.0 shipped 2026-06-10 (5 phases / 18 plans / 35/35 reqs / 277 tests / DRIFT-02 baseline `verification-cycle-2026-Q2`).*

</details>
