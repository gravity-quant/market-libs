# Requirements: market-libs — v1.2 Architecture + Auth/Ergonomics Carry-forwards

**Milestone goal:** Cerrar la deuda arquitectónica residual de v1.1 — migrar los 4 drivers `main_*.py` a consumir `Client`/`AsyncClient` directamente (cierra el LOC drop residual iol -5.1% / matriz -20%), agregar IOL refresh_token disk persistence, y exponer `client.with_options(max_retries=N)` cross-package. La evaluación de codegen single-source para eliminar la duplicación estructural sync/async se difiere a v1.3 con un libcst spike (Phase 12 NO-GO 2026-06-14 — strict D-RIGOR-01 reading, 3/8 items FAIL por source-shape asymmetry; ver `.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md`).

**Scope packages:** `iol-client`, `higyrus-client`, `ambito-financiero-client`, `matriz-client`. Excluido: `wallets-client` (stub).

**Non-breaking:** v1.2 es un bump minor — la API pública top-level (`pkg.get_X(...)`, `pkg.configure(...)`) se mantiene 100% backwards-compatible vía el PEP 562 shim ya existente desde v1.1.

---

## v1.2 Requirements

### Arquitectura sync/async dedup (REFAC)

- [x] **REFAC-05**: Driver migration × 4 packages — `main_ambito_financiero.py`, `main_iol.py`,
  `main_higyrus.py`, `main_matriz.py` consumen `Client`/`AsyncClient` instancias directamente
  (no más top-level `pkg.get_X(...)` ni `_get_default()._state.<attr>` patterns). **ONE Client
  per `main()` run** invariante (anti-Pitfall 1/2: evita OAuth churn IOL + TokenStore corruption
  matriz). AST regression-guard `test_main_<pkg>_uses_single_client_instance` por driver. Probe
  names UNCHANGED (anti-Pitfall 15: finding-title stability vs LIVE-01 baseline `71bf201`).
  Per-package serial: ámbito → iol → higyrus → matriz.

### Auth/Token persistence (SEC)

- [x] **SEC-01**: IOL refresh_token disk persistence (IOL only). `iol_client/_token_cache.py`
  con read-on-init + write-on-rotate atómico (write-then-rename), `platformdirs >=4.0,<5`
  para `user_data_dir('iol-client')` default (`~/.local/share/iol-client/refresh_token.json` en
  Linux, `~/Library/Application Support/iol-client/refresh_token.json` en macOS), opt-in
  `Client(token_cache_path=Path(...))` override, `os.chmod(path, 0o600)` POSIX permissions,
  `fcntl.flock` inter-process locking (anti-Pitfall 9), failed-refresh-cleanup deletes bad
  disk token (anti-Pitfall 8 stale-token-after-OOB-rotation). 8+ regression tests cubren
  los 4 paths del v1.1 BUG-03 lifecycle × disk (refresh→success, refresh→401→password
  fallback, preserve-on-omit, rotate-on-provide). Cross-cutting: integra con
  `_refresh_policy.py` fail-cache TTL reset. Log redaction: `_token_cache.py` usa
  `logging.getLogger(__name__)` dentro de `iol_client.*` para que `RedactingFilter` v1.1
  LOG-02 aplique (anti-Pitfall 7); `caplog` regression test confirma sentinel substring
  ausente en records.

### Client ergonomics (ERG)

- [x] **ERG-01**: `client.with_options(max_retries=N)` per-call override × 4 packages
  (anthropic/openai pattern). Shallow clone del `Client` que comparte underlying
  `httpx.Client` + `_ClientState` (anti-Pitfall 13: resource leak). Override threads via
  `request.extensions["max_attempts"]` extension (mirror del v1.1 mutation gate
  `request.extensions["idempotent"]` pattern). **Critical invariant**: mutation gate
  PERSIST irrespective of max_retries — `client.with_options(max_retries=10).new_order(...)`
  en matriz Primary executes EXACTLY 1 outgoing request bajo 503 (anti-Pitfall 14:
  duplicate-order money-on-the-line). Mutation gate regression test parametrizado por
  paquete antes de Phase merge. ~15 LOC adicionales en cada `_transport.py` + `_atransport.py`
  para la per-request extension. Per-package serial: ámbito → higyrus → matriz → iol
  (iol último porque interactúa con SEC-01 disk cache).

### Live re-verification (LIVE)

- [x] **LIVE-03**: `main_*.py --live × 4 packages` final gate post-migration (LIVE-01-equivalent).
  Operator dispositions per package (ambito/iol/higyrus/matriz), no new findings outside in-cycle
  classified set vs baseline `verification-cycle-2026-Q2` + v1.1 LIVE-01 head `71bf201`. Schema
  snapshot comparison, cycle closure markers, milestone audit. Confirma que driver migration
  (REFAC-05) + codegen (REFAC-06 if shipped) + IOL disk persistence (SEC-01) + with_options
  (ERG-01) no introdujeron regresiones observables en wire behavior contra APIs en vivo.

---

## In-cycle bug-fix convention (v1.0/v1.1 carry-forward)

No hay backlog de bugs pre-conocido para v1.2. Durante REFAC-05 (driver migration) y LIVE-03
(re-verificación final), los findings que surjan se clasifican con la taxonomía operator-driven
(CONFIRMED/FIXED/EXPECTED/NO-FIX) y se cierran con regression test mockeado en el mismo phase.
Esto sigue el patrón validado en v1.0 (14 findings clasificados) y v1.1 (4 BUG-IDs + iol F-02
PROBE_STALE fix inline). Tracking via `verification/findings.py` append-only con BEGIN/END zones
+ content-addressed dedupe (v1.1 HARN-07/08/09).

---

## Future Requirements (Defer to v1.3+)

- **REFAC-06** (deferred per Phase 12 NO-GO 2026-06-14): unasync/codegen single-source
  para `client.py`/`aio.py` transport shells × 4 packages. NO-GO root cause: strict
  D-RIGOR-01 FAIL on 3 of 8 items (1 byte-identical, 4 ruff check, 6 ámbito pytest) due
  to source-shape asymmetry between sync-first authored aio.py (v1.1 Phase 7) and
  async-first codegen direction; 0 Recipe-2 class-3 (unfixable) hunks. Re-evaluation
  requires a v1.3 spike on `libcst >=1.8.0,<2` (AST-level codemod — preserves
  whitespace + comments natively + can detect-and-rewrite source-shape asymmetries that
  unasync token-replacement cannot). See `.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md`
  and `.planning/todos/pending/spike-codegen-libcst-v1.3.md`.
- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff — diferido desde v1.0/v1.1)
- `matriz_client.ws_client` live verification (WebSocket streaming en daemon thread — diferido v1.0/v1.1)
- Extender alcance de verificación a `wallets-client` (cuando tenga endpoints reales)
- `cryptography.fernet` token encryption at-rest (operator authorization requerida; threat-boundary expansion)
- Automatic `Idempotency-Key` header para retried mutating POSTs (belt-and-suspenders sobre mutation gate)
- `findings.toml` machine-readable side-file alongside markdown findings
- `request_id` UUID per `_request()` invocation threaded through retry log records
- `max_elapsed_seconds` retry budget cap as belt-and-suspenders
- ERR-01 (mocked 403/429/5xx mapping), ERR-02 (mocked token TTL refresh) — v2 requirements del v1.0 backlog
- `Client.from_env()` classmethod × 4 (SKIPPED en v1.2 — industry survey 7 SDKs encontró ZERO
  con este patrón; v1.1 ya implementa implicit env fallback en constructor vía `_ClientState`
  + `load_dotenv()`. Pattern documentation lives en CLAUDE.md / README en lugar de classmethod
  redundante.)

---

## Out of Scope (v1.2 explicit exclusions)

- **prod vs remarkets en matriz** — D-MATZ-27 sigue REQUIRED pero queda para v1.3; v1.2 sigue
  remarkets-only (mutating gate exige hostname remarkets exacto).
- **WebSocket layer** — `matriz_client.ws_client` no se verifica live ni se refactoriza; la capa
  daemon-thread queda intacta. SEC-01 disk persistence NO toca el TokenStore 3-way (que ya
  cubre WebSocket sharing).
- **`wallets-client`** — sigue stub; no se extiende.
- **Token encryption at-rest** (Fernet/keyring) — trust boundary unchanged vs plaintext `.env`;
  defer a v1.3 con operator authorization explícita.
- **`keyring` (OS keychain integration)** — rechazado (headless CI requires null-backend, macOS
  GUI prompt blocks unattended, Linux requires SecretStorage+jeepney). Plaintext file + 0600 +
  fcntl es la opción correcta para el threat model actual (developer/CI tool).
- **Codegen para `_core.py`** — `_core.py` ya es single-source desde v1.1 Phase 7. Codegen
  REFAC-06 aplica solo a transport shells `client.py`/`aio.py`.
- **Codegen para matriz `_token_store.py`, `_refresh_policy.py`, `ws_client.py`** — estructuras
  con sync/async paths no-isomorphic; explicitly en deny-list.
- **Cambios breaking en API pública** — v1.2 sigue minor; top-level `pkg.get_X(...)` API
  preservada 100% vía PEP 562 shim (sin cambios desde v1.1).
- **Refactors de excepciones** — la jerarquía `<Pkg>ClientError` → `APIError` →
  `AuthError`/`RateLimitError` se mantiene; sin nuevos tipos.
- **PyPI publication** — fuera del alcance del milestone.

---

## Operational Gates (pre-Phase 1 prerequisites)

- **CI Python 3.13 baseline confirmation** — empujar v1.1 head (`71bf201`) a remote y confirmar
  GitHub Actions matrix verde en 3.12 + 3.13 ANTES de planificar Phase 1. Cierra los 3 deferred
  human-verification items de v1.1 Phases 7/8/9. Si CI rojo, fix se aplica como quick-task previo
  al primer phase de v1.2 (anti-Pitfall 17: atribución de breaks ambigua entre v1.1 baseline vs
  v1.2 changes).

---

## Traceability

*Filled by roadmap (see `ROADMAP.md`)*

| REQ-ID   | Phase                       | Status                                             |
|----------|-----------------------------|----------------------------------------------------|
| REFAC-05 | Phase 15                    | Complete (Phase 17 LIVE-03 gate, 17-VALIDATION.md) |
| REFAC-06 | Defer to v1.3               | Deferred (Phase 12 NO-GO 2026-06-14)               |
| SEC-01   | Phase 14                    | Complete (Phase 17 LIVE-03 gate, 17-VALIDATION.md) |
| ERG-01   | Phase 13                    | Complete (Phase 17 LIVE-03 gate, 17-VALIDATION.md) |
| LIVE-03  | Phase 17                    | Complete (Phase 17 LIVE-03 gate, 17-VALIDATION.md) |

Phase 12 (Codegen Spike) was the spike-before-plan research flag for REFAC-06. It returned
**NO-GO** on 2026-06-14 under strict D-RIGOR-01 reading (3 of 8 evidence items FAIL, all
tracing to source-shape asymmetry; 0 unfixable hunks). Per locked decision D-NOGO-01,
REFAC-06 defers to v1.3 with a dedicated libcst spike; Phase 16 is DROPPED from the v1.2
schedule; Phase 17 (LIVE-03) is unblocked to run immediately after Phases 14 + 15.

**Coverage:** 4/5 requirements mapped to v1.2 phases (REFAC-05 → Phase 15; SEC-01 →
Phase 14; ERG-01 → Phase 13; LIVE-03 → Phase 17). REFAC-06 deferred to v1.3 per Phase 12
NO-GO.

---

*Total: 5 requirements across 4 categories. Created 2026-06-14 for v1.2 Architecture + Auth/Ergonomics Carry-forwards milestone. REFAC-06 deferred to v1.3 per Phase 12 NO-GO 2026-06-14.*
