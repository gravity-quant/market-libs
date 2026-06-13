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

## Current Milestone: v1.1 Tech Debt Cleanup

**Goal:** Saldar la deuda técnica arquitectónica y los hallazgos diferidos de v1.0 —
refactor a clase Client por instancia (con compat layer no-breaking), deduplicación
sync/async con creación de `aio.py` para matriz-client, retries/backoff con jitter,
logging estructurado, fix de los 4 findings/bugs deferred, hardening del harness y
cierre de los 8 concerns del code review final de Phase 5.

**Target features:**
- Refactor "clase `Client` por instancia" en los 4 paquetes — eliminar singleton de módulo, mantener API top-level vía compat layer (no breaking).
- Deduplicación lógica sync/async por paquete + creación de `aio.py` para `matriz-client` (hoy sync-only) y su verificación live.
- Retries/backoff transparente con jitter para 5xx/429/connection-errors — respeta el `mutating_allowed` double-gate (no retry de mutaciones).
- Logging estructurado con stdlib `logging` por paquete — integrado con `verification/redaction.py` (Bearer + patrones existentes).
- Fixes pendientes: F-09 matriz ERROR-MAP, higyrus F-02 (`get_listado_cuentas=0`), IOL refresh_token persistence, HIGY multi-account iteration.
- Driver bug bundle: D-MATZ-27 dedupe + `verification/findings.py` append-only (preserva rationale operator) — aplica a los 4 drivers.
- Code review concerns WR-01..WR-08 (8 ítems del review final de Phase 5).

**Out of scope para este milestone:**
- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff) — defer a v1.2
- `matriz_client.ws_client` live verification (capa WebSocket) — defer a v1.2
- Extender alcance a `wallets-client` o nuevos paquetes — defer
- Nuevos endpoints o superficies live nuevas — defer

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

### Out of Scope

<!-- Límites explícitos con su razón, para no re-incorporarlos. -->

- `wallets-client` — stub sin endpoints reales y con URL placeholder; nada que verificar en vivo
- Superficie async de `matriz-client` — no existe `aio.py`; su "async" es solo la capa WebSocket
- Streaming WebSocket de `matriz-client` — capa basada en thread daemon; fuera de alcance este ciclo
- Publicación a PyPI — no forma parte de la verificación
- Refactors arquitectónicos (clase `Client` por instancia, deduplicación sync/async, retries/backoff, logging estructurado) — tech debt conocido, no es el foco de este ciclo

## Context

- **Current state (post-v1.0):** 4 de 5 paquetes (`ambito-financiero-client`, `iol-client`, `higyrus-client`, `matriz-client`) están **verificados end-to-end contra sus APIs reales** vía drivers `main_*.py` ejecutados manualmente. El 5° paquete (`wallets-client`) sigue stub. Cada paquete tiene un findings file `.planning/verification/<pkg>-findings.md` con clasificación operator-driven, schemas snapshot committeables PII-free (envelope D-21), y secciones `## Cycle Closure` con cycle ID + counts + verify_cycle_closure result. El meta-baseline DRIFT-02 vive en `.planning/verification/CYCLE-REPORT.md`.
- **Stats v1.0 cycle:**
  - 277 mocked tests passing (vs ~50 al inicio del ciclo)
  - 18 schema snapshots committed (1 ámbito + 4 iol + 5 higyrus + 8 matriz)
  - 14 findings clasificados (1 ámbito + 1 iol + 2 higyrus + 10 matriz) — 1 CONFIRMED + 4 EXPECTED + 9 NO-FIX + 0 FIXED-tagged-this-cycle (los 16+6 higyrus fixes Phase 4 son in-cycle pero predatan la convención `Regression:` field)
  - 5 phase canonical commits + 1 cycle-wide canonical baseline forensic-localizable via `git log --grep="DRIFT-02 cycle closure"`
  - 4 BLOCKERs del code review final de Phase 5 fixeados con regression tests (2 Critical + 2 PII Warning)
- **Tech stack mantenido:** Python 3.12+, uv, httpx (sync+async), pytest+pytest-httpx, ruff (rule sets E/W/F/I/B/UP/SIM/RUF/ASYNC/PIE/PT/RET/TID), mypy strict — todo el CI permanece verde. Sin cambios arquitectónicos: los packages siguen siendo standalone wheels sin shared internals (por diseño).
- **Harness module** `verification/` (no publicable, vive en repo root): `redaction`, `env_gate`, `mutation_gate`, `findings`, `schema`, `capture`, `anonymize`, `safemodel_diff`, `cycle_report` — todos consumidos por los 4 drivers vía import del barrel. Phase 5 promovió `safemodel_diff` y `cycle_report` desde inline-en-drivers a módulos del harness (cross-package duck-typed) para que matriz pudiera invocar `verify_cycle_closure × 4 pkgs`.
- **Convención forward-looking ratificada (operator decision Phase 5 Op A):** desde cycle-2026-Q3+ / Phase 6+, cada CONFIRMED → FIXED transition appendea `Regression: <path>::<test>` al bullet del finding. Historical findings (Phases 2-4) inherit Phase-level audit via SUMMARY counts.
- **Mapa de codebase disponible:** `.planning/codebase/` (ARCHITECTURE, STACK, STRUCTURE, TESTING, CONCERNS, CONVENTIONS, INTEGRATIONS) — vigente, actualizar si vuelve a haber un próximo cycle.

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
| F-09 deferred + cycle_closure FAIL como señal DRIFT-02 (Phase 5 Op A) | Operator decidió no fixear F-09 en este cycle; el FAIL es la señal que cierra DRIFT-02 (el ciclo detecta su propio gap) | ⚠️ Revisit en v1.1 — convención forward-looking ratificada (Regression: `<path>::<test>` field desde Phase 6); F-09 fix esperado en próximo cycle |

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
*Last updated: 2026-06-13 — Phase 8 retries + backoff + structured logging complete (6/6 plans, 755 tests +228 net vs Phase 7, RELY-01..04 + LOG-01..03 closed; tenacity 9.1.4 wired cross-paquete; matriz Risk API D-23 carve-out + D-24 status=ERROR no-retry + D-25 aio.py deferred; in-cycle code review fix: 7/7 findings closed con +128 regression tests, CR-01/CR-02 guard tests rewritten to exercise real Risk surface, WR-01..02/06..08 hardening landed). v1.1 milestone continues with Phase 9 (deferred bug fixes: F-09 matriz ERROR-MAP, F-02 higyrus get_listado_cuentas=0, IOL refresh_token persistence, HIGY multi-account). v1.0 archived (5 phases / 18 plans / 35/35 requirements / 277 tests / DRIFT-02 baseline `verification-cycle-2026-Q2`).*
