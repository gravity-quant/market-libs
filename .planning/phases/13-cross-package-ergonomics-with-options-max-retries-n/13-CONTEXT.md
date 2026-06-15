# Phase 13: Cross-Package Ergonomics (`with_options(max_retries=N)`) - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 13 entrega un único surface ergonómico — `client.with_options(max_retries=N)` —
duplicado a través de los 4 paquetes verificables (ámbito, higyrus, matriz, iol),
en sus dos superficies (`client.py` sync + `aio.py` async). El método retorna un
**view** (shallow clone vía `Client.__new__(Client)`) que **comparte** `_state`
del padre — incluidos `http_client`, `token`, `refresh_token`, y (matriz) `token_store` —
sobrescribiendo solamente `_max_retries` del view. El override se thread via
`request.extensions["max_attempts"]` (mirror exacto del v1.1 Phase 8 patrón
`request.extensions["idempotent"]`).

**Critical merge gate (anti-Pitfall 14):** el mutation gate de v1.1 sigue siendo
la autoridad absoluta sobre permiso de retry. `client.with_options(max_retries=10)
.new_order(...)` en matriz Primary ejecuta EXACTAMENTE 1 outgoing request bajo
503 mockeado — el `extensions["max_attempts"]` solo TIGHTENS o LOOSENS el cap
para calls idempotent; para non-idempotent (POST/PATCH + matriz mutating GETs
new_order/cancel_order/replace_order) se ignora y se cae al pass-through de
1 outgoing request. Money-on-the-line.

**Critical merge gate (anti-Pitfall 13):** zero resource leak. View comparte
`_state.http_client` (no nueva pool TCP), `_state.token` (no re-auth), y
(matriz) `_state.token_store` (no re-build del 3-way concurrent primitive).

**Per-package serial order:** ámbito → higyrus → matriz → iol. iol last porque
interactúa con Phase 14 disk persistence (SEC-01).

**Phase 13 NO entrega:**

- `with_options(timeout=...)` / `with_options(headers=...)` / `with_options(http_client=...)`
  — scope-locked a `max_retries` only por PROJECT.md:40; defer a v1.3.
- `Client.from_env()` classmethod — SKIPPED en v1.2 por REQUIREMENTS §Future
  (industry survey 7 SDKs encontró ZERO con este patrón).
- Driver migration (Phase 15 REFAC-05) — drivers `main_*.py` quedan unchanged
  en esta phase; Phase 15 decide adoption per driver.
- Live re-verification (Phase 17 LIVE-03) — re-runs `main_*.py --live × 4` post-
  migration; Phase 13 solo entrega tests mocked.
- IOL disk persistence (Phase 14 SEC-01) — independiente; iol last en el serial
  por safety, no por dependency.

**Carry-forward de Phase 8 (no se re-toca):**

- `RetryTransport(httpx.HTTPTransport)` + `AsyncRetryTransport(httpx.AsyncHTTPTransport)`
  per-paquete (Phase 8 D-01). Phase 13 EXTIENDE su `handle_request` para leer
  `max_attempts = request.extensions.get("max_attempts", self._max_attempts)`.
- `request.extensions["idempotent"]` mutation gate (Phase 8 D-01) — la nueva
  `extensions["max_attempts"]` se evalúa DESPUÉS del idempotent gate; orden
  preserva mutation gate como FIRST gate.
- `_validate_max_retries()` helper (Phase 8 WR-06) — Phase 13 lo reutiliza
  verbatim para validar el `with_options(max_retries=N)` arg.
- `_ClientState` per paquete (Phase 6) — sigue siendo el shared object.
- B8 alias `_raise_for_response` (Phase 7 D-04) — intacto.
- Snapshot público `verification/snapshots/<pkg>-surface.txt` (Phase 6 D-06 +
  Phase 8 D-28) — Phase 13 lo extiende per-paquete con `Client.with_options`
  + `AsyncClient.with_options` entries (atomicidad per-Plan idiom).

</domain>

<decisions>
## Implementation Decisions

### View lifecycle + chaining

- **D-V1: `_is_view: bool` flag en `__slots__`; lifecycle methods no-op si True.**
  Cada `Client` y `AsyncClient` agrega `_is_view` a `__slots__` (default False
  para constructor normal; True solo cuando `with_options` lo setea). `close()`
  / `__exit__` (sync) y `aclose()` / `__aexit__` (async) chequean `_is_view`
  primero y son no-op si True. Idéntico al patrón anthropic/openai SDK
  (`with_options` returns view that does NOT own the http_client). Cero
  foot-gun: un view se puede usar dentro de `with` block sin riesgo de cerrar
  el `http_client` del padre. ~3 LOC extra por clase × 4 paquetes × 2 surfaces.
  Aplica a 4 paquetes sync + 3 paquetes async (matriz async lo recibe igual
  porque Phase 10 ya creó `aio.py` 852 LOC).

- **D-V2: Chaining inner-wins, view-of-view OK, padre intacto.**
  `c.with_options(5).with_options(10)._max_retries == 10` y
  `c._max_retries == 2` (sin tocar al original). Cada llamada produce una
  shallow clone fresca: `Client.__new__(Client)` + `view._state = parent._state`
  + `view._max_retries = N` + `view._is_view = True`. Predictable, idiomático
  anthropic. Test en Plan 1 cross-cutting.

- **D-V3: AsyncClient mismo idiomático sync — sin defer.**
  `AsyncClient.with_options(*, max_retries: int) -> AsyncClient` espejo exacto
  del sync. Misma `_is_view` flag protege `aclose()` y `__aexit__`. Cero
  divergencia surface sync/async. Aplica a ámbito, higyrus, matriz, iol
  (los 4 tienen `aio.py` desde Phase 10 que cubrió el matriz aio.py 852 LOC).
  Validación: `_validate_max_retries` importado de `client.py` (precedent
  Phase 8 — `aio.py` ya importa `_validate_max_retries` y `_max_retries` shape
  de `client.py` per Phase 8 D-15).

- **D-V4: View es snapshot del `_state` que el padre tenía al construirse;
  `configure()` posterior NO afecta al view.** `configure()` reemplaza el
  `_default_client` con un nuevo `Client` que tiene su propio `_state`. Los
  views creados desde el `_default_client` viejo siguen apuntando al `_state`
  original. Comportamiento natural y predecible (anthropic-style). Documentar
  en docstring de `with_options`. NO se agregan tests extra — el comportamiento
  emerge naturalmente del shallow-clone shape.

- **D-V5: Snapshot público per-paquete agrega solo class methods.**
  Cada Plan 2-5 actualiza su `verification/snapshots/<pkg>-surface.txt`
  agregando exactamente:
  - `Client.with_options(*, max_retries: int) -> Client`
  - `AsyncClient.with_options(*, max_retries: int) -> AsyncClient`

  NO se expone top-level `<pkg>.with_options(...)` (with_options es method-
  on-instance, no singleton-delegator). El PEP 562 shim (Phase 6 D-01) NO
  forwardea `with_options` — los callers deben usar `_get_default().with_options(...)`
  o construir un `Client()` explícito. Idiom Phase 8 D-28 (snapshot atómico
  per-paquete commit).

### matriz TokenStore × view interaction

- **D-T1: View max_retries es HTTP-only; TokenStore (matriz refresh policy)
  queda gobernado por el Client constructor.** Aislación explícita entre
  HTTP-level retry cap (que el view puede sobrescribir per-call) y auth-server
  retry cap (que es long-lived state del TokenStore + RefreshPolicy). El view
  NUNCA toca `_state.client_max_retries` ni triggerea re-build del TokenStore.
  Anti-Pitfall extendido a auth-server load: un caller que hace
  `client.with_options(max_retries=10).get_segments(...)` NO escala el cap de
  retries del refresh_fn — el TokenStore sigue con el cap del constructor.
  Aplica solo a matriz (único paquete con `build_token_store(state, max_retries=...)`
  parametrizado).

- **D-T2: View comparte `_state.token_store`; concurrencia 3-way Phase 10
  unchanged.** El view shallow-clone NO crea TokenStore propio; consume el
  shared `_state.token_store` que ya está sincronizado vía `threading.Lock`
  (sync REST + ws_client daemon thread) + `asyncio.Lock` per-loop (async REST,
  via `_get_async_lock()`). El spike-findings Phase 10 (auto-loaded vía
  `Skill("spike-findings-market-libs")`) sigue siendo el contract. Cero
  impacto en la concurrencia 3-way validada en Phase 10 LIVE-02.

- **D-T3: Nuevo field `_state.client_max_retries: int` solo en matriz.**
  Agregado a `packages/matriz-client/src/matriz_client/_state.py::_ClientState`
  (NOT frozen; ya es mutable per Phase 10). Constructor del `Client` y
  `AsyncClient` lo setea = `max_retries` arg. `_ensure_token()` (sync en
  `client.py:253` + async en `aio.py:~306`) lo lee:
  `build_token_store(state, max_retries=state.client_max_retries)`. ~3 LOC
  en `_state.py` + ~2 LOC en `client.py` + ~2 LOC en `aio.py` = ~7 LOC matriz.

- **D-T4: Field `client_max_retries` NO se duplica a ámbito/iol/higyrus.**
  YAGNI: solo matriz tiene `build_token_store(state, max_retries=...)`
  parametrizado. Los demás paquetes no consumen el field. Revisar en v1.3 si
  el libcst codegen spike (per Phase 12 NO-GO carry-forward) prefiere shape
  uniforme cross-paquete para emisión. Por ahora, divergencia matriz-only
  documentada (igual que B7 ámbito divergence sin `token_lock`).

- **D-T5: Test `test_with_options_does_not_rebind_tokenstore_max_retries`
  en `packages/matriz-client/tests/` (matriz-specific, NO cross-cutting).**
  Mocked: construir `Client(max_retries=2)` + `view = c.with_options(10)`;
  forzar primer `_ensure_token` desde view (mock `_core.token_is_fresh = False`
  + mock `httpx` para refresh endpoint); assert que `build_token_store` se
  llamó con `max_retries=2`, NO 10. Lives in matriz tests (no `verification/`)
  porque es matriz-specific y los demás paquetes harían skip.

- **D-T6: Sin auditoría adicional para iol/higyrus auth-flow.**
  `_send_auth_request()` (iol + higyrus + matriz `_send_auth_request` para
  Risk API) ya está cubierto por el mutation-gate cross-cutting de Phase 8.
  Login y refresh están marcados `idempotent=True` (Phase 8 D-03), así que el
  view's `extensions["max_attempts"]` SÍ se honra para esos calls — pero el
  test cross-cutting de Plan 1 (`test_with_options_max_attempts_extension_honored`)
  cubre el behavior. NO se agregan tests específicos para auth-flow override.

### Driver smoke / canary use

- **D-D1: Cero cambios a drivers `main_*.py` en Phase 13.**
  Phase 13 entrega solo el surface en `packages/*/src/`. Los 4 drivers quedan
  unchanged. Phase 15 (REFAC-05 driver migration) decide adoption per driver
  cuando reformatea cada `main_*.py` para consumir `Client()`/`AsyncClient()`
  directamente. Phase scope limpia: ergonomics surface only. Tests mocked en
  `verification/` + per-paquete cubren el behavior; live re-verification
  vive en Phase 17 LIVE-03.

- **D-D2: `13-SUMMARY.md` incluye sección "Forward references for Phase 15".**
  Documenta el surface disponible con 2-3 ejemplos concretos de uso para que
  el `gsd-phase-researcher` de Phase 15 los descubra sin re-investigar.
  Ejemplos a incluir (a confirmar en planning):
  - `client.with_options(max_retries=5).get_quote("RARE")` (idempotent GET
    con cap aumentado para símbolos flaky).
  - `client.with_options(max_retries=0).get_movimientos(...)` (debug
    iteration, sin retry magic).
  - `client.with_options(max_retries=10).new_order(...)` (matriz — NOTA:
    mutation gate prevalece; 10 attempts solo aplica a calls idempotent).

### Plan slicing

- **D-P1: 5 planes — 1 cross-cutting tests-first + 4 per-package serial.**
  - **Plan 1 — Cross-cutting tests + RetryTransport extension wiring
    (tests-first, RED en HEAD):** los 4 tests cross-cutting de D-P2 + cambio
    al `RetryTransport.handle_request` y `AsyncRetryTransport.handle_request`
    para leer `request.extensions.get("max_attempts", self._max_attempts)`
    × 4 paquetes (el cambio del transport es pequeño y va junto con los
    tests; sin él los tests serían siempre RED). NO toca `client.py`/`aio.py`
    del paquete; el view method aterriza Plans 2-5.
  - **Plan 2 — `with_options` ámbito (canary, no auth):**
    `Client.with_options` + `AsyncClient.with_options` + `_is_view` flag +
    no-op `close()`/`__exit__`/`aclose()`/`__aexit__` + snapshot update +
    per-paquete mocked tests (incluyendo `test_with_options_close_is_noop`).
    Ámbito = canary porque no auth, no account_id, no TokenStore — el
    cambio más pequeño antes de higyrus/matriz/iol.
  - **Plan 3 — `with_options` higyrus:** mismo idiom + RedactingFilter
    permanece intacto + account_id propagation no cambia.
  - **Plan 4 — `with_options` matriz (incluye D-T1..T6):** misma estructura
    + nuevo field `_state.client_max_retries: int` + `_ensure_token()` lo
    consume + `test_with_options_does_not_rebind_tokenstore_max_retries`
    en matriz tests + matriz auth_basic (Risk API) sigue funcionando con
    extension passthrough.
  - **Plan 5 — `with_options` iol (last; interactúa con Phase 14 SEC-01):**
    mismo idiom + 401 re-auth path del shell `_request()` sigue intacto
    + green gate consolidado al final del Plan 5 (`uv run pytest` full
    monorepo + `uv run ruff check` + `uv run ruff format --check` +
    `uv run mypy --strict` + `uv run lint-imports` + `pre-commit run
    --all-files`). NO Plan 6 separado (scope chico vs Phase 8).

- **D-P2: Plan 1 tests cross-cutting (4 tests + 1 mutation-gate extension):**
  - `test_with_options_shares_http_client_and_token` × 4 paquetes —
    parametrize: assert `view._state is parent._state` y
    `view._state.http_client is parent._state.http_client` (anti-Pitfall 13;
    SC#1 ROADMAP).
  - **`test_with_options_does_not_bypass_mutation_gate_matriz` (CRITICAL
    MERGE GATE)** — matriz-only: `c.with_options(max_retries=10).new_order(...)`
    con httpx_mock 503; assert `len(httpx_mock.get_requests()) == 1`.
    Anti-Pitfall 14 / SC#2 ROADMAP. Esta es la condición de merge.
  - `test_with_options_max_attempts_extension_honored` parametrize × paquetes
    con GET idempotent (ámbito `get_dollar_banco_nacion`, iol `get_quote`,
    higyrus `get_movimientos`, matriz `get_segments`); mock 503 N veces;
    assert view's `max_retries=10` produce 11 wire requests; padre con
    default produce 3 (`max_retries=2 + 1`). SC#3 ROADMAP.
  - `test_with_options_chaining_inner_wins` × 4 paquetes — chain
    `c.with_options(5).with_options(10)`; assert `_max_retries == 10` y
    `c._max_retries == 2`. Cubre D-V2.

  Estos 4 tests viven en `verification/test_with_options.py` (archivo nuevo).
  No se mezclan con `verification/test_retry_mutation_gate.py` existente
  (Phase 8 D-26) — separación clara de scope (Phase 13 own file).

- **D-P3: `test_with_options_close_is_noop` vive en `packages/<pkg>/tests/`,
  NO en `verification/`.** Per Plan 2-5 mocked tests per-paquete. Sigue
  idiom Phase 6 lifecycle tests (`close()` idempotente, pickle/deepcopy
  raise, etc.) que viven en `packages/<pkg>/tests/test_client.py` y
  `test_async_client.py`. Focused, mocked, sin parametrize cross-cutting.

- **D-P4: Snapshot público per-paquete atómico en cada Plan 2-5.**
  Cada Plan 2-5 corre `regen_snapshots.py --packages <pkg>` (o equivalente
  manual) y conmita el diff junto con su impl. Idiom Phase 6 D-06 / Phase 8
  D-28. Atomicidad máxima: si Plan 3 (higyrus) rompe, Plans 1+2 quedan
  mergeable sin pollute del snapshot. Cada commit contiene solo 2 entries
  nuevas en el `<pkg>-surface.txt`.

### Claude's Discretion

El planner decide:

- **Naming exacto del extension key.** `"max_attempts"` vs `"max_retries"`
  en `request.extensions`. Recommendation: `"max_attempts"` (matches lo que
  el RetryTransport ya almacena internamente como `self._max_attempts`, y
  matches la semántica del tenacity loop `stop_after_attempt(N)`). El view's
  `_max_retries=N` se traduce a `extensions["max_attempts"] = N + 1` al
  setear (mismo factor que `RetryTransport(max_attempts=self._max_retries + 1)`
  de Phase 8).

- **Dónde setear `request.extensions["max_attempts"]`.** En el shell
  `_request()` de cada `Client.py` y `aio.py`, junto a las otras extensions
  (`idempotent`, `request_id`, `endpoint_name`, opcional `account_id`).
  Solo cuando el caller es un view con `_max_retries` distinto al constructor
  default — o siempre (uniforme). Recommendation: SIEMPRE (incluso cuando
  el caller es el Client original) — uniformidad simplifica el shape del
  test cross-cutting y elimina branches en el shell.

- **`_max_retries` accessor desde el shell.** El shell `_request()` ya tiene
  acceso a `self._max_retries`. Para el view, `self._max_retries` ya está
  sobrescrito por D-V2. El extension se setea `self._max_retries + 1`
  uniformemente. Implementación: `req.extensions["max_attempts"] = self._max_retries + 1`.

- **`__repr__` del view.** Si el view tiene `_is_view=True`, el `__repr__`
  puede indicarlo (e.g., `<view of AmbitoFinancieroClient(...) max_retries=5>`).
  Cosmético, no afecta surface tests. Planner decide; recomendación: incluir
  para debug ergonomics.

- **PEP 562 shim impact.** El shim de cada paquete (`__getattr__` en
  `__init__.py` o `client.py` per-paquete) NO necesita forwardear
  `with_options` porque es method-on-class, no module-level. Phase 13 NO
  toca el shim. Solo el snapshot público se actualiza.

- **Mocking `_core.token_is_fresh` en D-T5 test.** El test mockea via
  monkeypatch o directly setting `_state.token = None` + `_state.token_expires_at = 0.0`
  para forzar `_ensure_token` a refrescar. Planner elige el patrón más limpio
  vs los existing matriz tests.

- **`test_with_options_max_attempts_extension_honored` endpoint selection
  per paquete.** Planner elige 1 GET idempotent representativo por paquete
  (no es necesario parametrizar más de uno). Recommendation: el endpoint
  más simple sin params extras complejos.

### Folded Todos

Ninguno. `cross_reference_todos` step encontró 0 matches relevantes
(`matriz-driver-findings-file-handling` ya resuelto en Phase 11).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & milestone v1.2

- `.planning/PROJECT.md` — v1.2 milestone goals, scope, Key Decisions table;
  REQUIREMENTS §ERG-01 — `with_options(max_retries=N)` × 4 packages;
  PROJECT.md:40 — scope lock a `max_retries` only (no `timeout`/`headers`/
  `http_client` en v1.2).
- `.planning/REQUIREMENTS.md` §"Client ergonomics (ERG)" — ERG-01 spec con
  los 5 success criteria que Phase 13 satisface. §"Future Requirements
  (Defer to v1.3+)" — `Client.from_env()` SKIPPED rationale (industry
  survey 7 SDKs).
- `.planning/ROADMAP.md` §"Phase 13: Cross-Package Ergonomics" — los 5 SC
  oficiales. §"Phase 14: IOL Disk Persistence" — iol last en serial porque
  interactúa. §"Phase 15: Driver Migration × 4" — adoption de `with_options`
  per driver en Phase 15. §"Phase 17: Final Live Re-verification × 4" —
  re-verification post-Phase-13/14/15.
- `.planning/STATE.md` §"Decisions" + §"Blockers/Concerns" §"Phase 13" —
  Pitfall 14 (`with_options(max_retries=10).new_order(...)` bypass mutation
  gate) marcado como CRITICAL merge gate test antes de Phase 13 merge.

### Prior phase (Phase 8 — RetryTransport + mutation gate, direct dependency)

- `.planning/milestones/v1.1-phases/08-retries-backoff-structured-logging/08-CONTEXT.md`
  — D-01 (RetryTransport `httpx.HTTPTransport` subclass + mutation gate vía
  `request.extensions["idempotent"]`); D-15 (kwargs `max_retries` +
  `http_client` en Client/AsyncClient/configure()); D-18 (with_options
  deferred to v1.2+; Phase 13 cumple ese defer); D-19 (`max_retries=0`
  bypass + `max_retries=N → max_attempts=N+1` mapping); D-21 (5-Plan
  per-paquete serial idiom — Phase 13 sigue); D-26 (cross-cutting tests
  pattern en `verification/`); D-28 (snapshot atómico per-paquete);
  D-30 (`request_id` UUID per-business-call vía extensions); D-31
  (Retrying loop dentro de handle_request — Phase 13 lo EXTIENDE para leer
  `max_attempts` extension); WR-06 (`_validate_max_retries()` helper —
  Phase 13 lo reutiliza verbatim).
- `.planning/milestones/v1.1-phases/08-retries-backoff-structured-logging/08-RESEARCH.md`
  — patrón base de `_transport.py` / `_atransport.py` per-paquete.

### Prior phase (Phase 10 — matriz aio.py + TokenStore, matriz-specific dep)

- `.planning/milestones/v1.1-phases/10-matriz-aio-py-creation-tokenstore/10-CONTEXT.md`
  — matriz `aio.py` 852 LOC creation; TokenStore 3-way concurrency
  (`threading.Lock` callable desde asyncio context); `_get_async_lock()`
  per-loop lazy init; `build_token_store(state, max_retries=N)` shape que
  Phase 13 D-T1..T3 preservan.
- `.claude/skills/spike-findings-market-libs/SKILL.md` — TokenStore 3-way
  primitive + RefreshPolicy retry/backoff/fail-cache (auto-loaded). Phase 13
  D-T2 garantiza que el view NO rompe estos patterns.

### Prior phase (Phase 6 — Client/AsyncClient skeleton, baseline)

- `.planning/milestones/v1.1-phases/06-compat-safety-net-client-class-skeleton/06-CONTEXT.md`
  — D-01 (PEP 562 shim — Phase 13 NO lo toca); D-06 (snapshot público
  pattern — Phase 13 sigue); D-13 (Client.__init__ kwargs minimal);
  D-14 (configure() replaces _default_client semantics); D-18 (Client.__repr__
  credential redaction — Phase 13 view __repr__ sigue patrón).

### Research (v1.2)

- `.planning/research/SUMMARY.md` §"Stack Additions for v1.2" + §"Watch Out
  For — 4 HIGHEST-RISK Pitfalls" — Pitfalls 13 + 14 son los que Phase 13
  tiene que cerrar.
- `.planning/research/ARCHITECTURE.md` §2.5 "`with_options()` Integration"
  — view shape (`Client.__new__(Client)` + share `_state` + override
  `_max_retries`); anthropic SDK pattern reference; `_is_view` flag
  rationale; view `close()` mitigation (D-V1 source).
- `.planning/research/ARCHITECTURE.md` §4.3 "`with_options()` Per-Call Flow"
  — secuencia exacta del thread del `max_attempts` extension; integración
  con `_ensure_http_client()` cached transport (D-P1 Plan 1 source).
- `.planning/research/PITFALLS.md` §Pitfall 13 — `with_options()` resource
  leak; D-V1 / D-V2 / D-V3 mitigation (shared `_state.http_client`).
- `.planning/research/PITFALLS.md` §Pitfall 14 — `with_options(max_retries=N)`
  × mutation gate; CRITICAL test `test_with_options_max_retries_does_not_bypass_mutation_gate`
  (D-P2 SC#2 source). Money-on-the-line.
- `.planning/research/PITFALLS.md` §Section "with_options × disk persistence"
  (Pitfalls 8, 14) — interacción con Phase 14 SEC-01; iol last serial
  rationale.
- `.planning/research/STACK.md` — sin nuevas runtime deps en Phase 13;
  `tenacity 9.1.4` ya presente desde Phase 8.
- `.planning/research/FEATURES.md` — `with_options(max_retries=N)` listed
  como P1 v1.2 feature.

### Codebase maps (vigentes; actualizadas Phase 11)

- `.planning/codebase/ARCHITECTURE.md` §"Module-Level State Pattern" —
  `_state.py` per-paquete; `_transport.py`/`_atransport.py`/`_logging.py`
  Phase 8.
- `.planning/codebase/CONVENTIONS.md` — naming + `from __future__ import
  annotations` mandatory + double quotes + line=100.
- `.planning/codebase/TESTING.md` — pytest-httpx pattern + autouse fixtures
  con `configure(token=...)`. Phase 13 reutiliza.

### Forward references (Phase 14, 15, 17 — no leer todavía)

- `.planning/ROADMAP.md` §"Phase 14: IOL Disk Persistence" — iol Plan 5 de
  Phase 13 last serial position porque Phase 14 SEC-01 introduce
  `Client(token_cache_path=...)` que coexiste con el view (no integra
  directamente — el view comparte `_state` que ya incluye el cache state).
- `.planning/ROADMAP.md` §"Phase 15: Driver Migration × 4" — D-D1 + D-D2
  forward refs; los drivers `main_*.py` adoptan `with_options` en Phase 15
  cuando refactorizan.
- `.planning/ROADMAP.md` §"Phase 17: Final Live Re-verification × 4 (LIVE-03)"
  — re-verifica que `with_options` no introdujo regresiones observables
  en wire behavior contra APIs reales.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`_validate_max_retries()` helper per paquete** (Phase 8 WR-06).
  Lives en cada `client.py` (`packages/<pkg>/src/<pkg>/client.py:41-62`
  ámbito, equivalente en los 4 paquetes). Validates non-negative int,
  rejects bool. Phase 13 lo invoca al principio de `with_options(max_retries=N)`
  antes de cualquier mutación. `aio.py` ya lo importa de `client.py`
  (precedent Phase 8); Phase 13 mantiene el pattern.

- **`_ClientState` mutable dataclass per paquete** (Phase 6 D-13).
  `packages/<pkg>/src/<pkg>/_state.py`. Shared entre Client y AsyncClient
  (mismo `_state` referenciable). El view comparte el mismo `_state` instance.
  matriz `_state.py` recibe nuevo field `client_max_retries: int` (D-T3).

- **`RetryTransport.handle_request()` + `AsyncRetryTransport.handle_request()`**
  (Phase 8 D-01). `packages/<pkg>/src/<pkg>/_transport.py` +
  `_atransport.py` × 4 paquetes. Phase 13 EXTIENDE línea por línea:
  reemplaza `stop=stop_after_attempt(self._max_attempts)` con
  `stop=stop_after_attempt(request.extensions.get("max_attempts", self._max_attempts))`.
  Cambio idéntico × 8 archivos (4 paquetes × 2 surfaces).

- **`Client._request(spec)` shell + `AsyncClient._request(spec)` shell**
  per paquete (Phase 6 + Phase 8). Sets `request.extensions["idempotent"]`,
  `["request_id"]`, `["endpoint_name"]`, opcional `["account_id"]`.
  Phase 13 agrega `req.extensions["max_attempts"] = self._max_retries + 1`
  uniformemente (claude's discretion — uniforme vs branch).

- **`build_token_store(state, *, max_retries)`** matriz only
  (`packages/matriz-client/src/matriz_client/_token_store.py:146`).
  Constructor del TokenStore parametrizado. Phase 13 D-T3 cambia el
  `max_retries` arg al llamarlo desde `_ensure_token()` para usar
  `state.client_max_retries` (en vez de `self._max_retries`).

- **`verification/snapshots/<pkg>-surface.txt`** × 4 paquetes. Phase 13
  D-V5 + D-P4 lo extiende per Plan 2-5 con 2 entries nuevas
  (`Client.with_options`, `AsyncClient.with_options`).

- **`verification/regen_snapshots.py`** — script Phase 6. Phase 13 lo
  ejecuta per-paquete en Plans 2-5.

- **`verification/test_retry_mutation_gate.py`** (Phase 8 D-26). Existing
  matriz `new_order` test. Phase 13 D-P2 NO lo extiende — los tests
  cross-cutting de Phase 13 viven en archivo NUEVO
  `verification/test_with_options.py` para scope separation.

- **`packages/<pkg>/tests/conftest.py`** — sin cambios (Phase 6 patterns
  intactos: `configure(token=...)` autouse).

### Established Patterns

- **Per-package serial delivery (ámbito → higyrus → matriz → iol)** —
  Phase 8 D-21 idiom (que mismo Phase 13 sigue con orden ajustado: iol last
  por Phase 14 SEC-01 interaction). Cada paquete = 1 commit atómico.

- **Tests-first cross-cutting (Plan 1 RED en HEAD)** — Phase 8 D-21 Plan 1
  idiom. Phase 13 lo replica.

- **`_max_retries=N → _max_attempts=N+1`** — Phase 8 D-19 (max_retries=N
  retries adicionales = N+1 total attempts; anthropic/openai SDK semantics).
  Phase 13 preserva: `view._max_retries` se traduce a
  `extensions["max_attempts"] = N + 1` al setear.

- **`_validate_max_retries()` early** — Phase 8 WR-06. Phase 13 lo invoca
  primero en `with_options()` antes de crear el view.

- **Snapshot atómico per-Plan** — Phase 6 D-06 / Phase 8 D-28. Phase 13
  D-P4 sigue.

- **`from __future__ import annotations` mandatory** — toda nueva código.
  Phase 13 sigue.

### Integration Points

- **`packages/<pkg>/src/<pkg>/client.py` — NUEVA función `with_options`:**
  ```python
  def with_options(self, *, max_retries: int) -> Self:
      _validate_max_retries(max_retries)
      view = type(self).__new__(type(self))
      view._state = self._state       # SHARE
      view._max_retries = max_retries  # OVERRIDE
      view._is_view = True            # FLAG (D-V1)
      return view
  ```
  ~10 LOC per `client.py` × 4 paquetes.

- **`packages/<pkg>/src/<pkg>/aio.py` — NUEVA función `with_options`:**
  mirror sync. ~10 LOC per `aio.py` × 4 paquetes.

- **`packages/<pkg>/src/<pkg>/client.py` — `close()` modification:**
  ```python
  def close(self) -> None:
      if getattr(self, "_is_view", False):
          return  # views don't own the http_client (D-V1)
      ...  # existing logic
  ```
  ~2 LOC per `close()` × 4 paquetes; mismo para `aclose()` × 4 paquetes
  (excluyendo matriz async — Phase 10 ya creó aio.py con su propio aclose).

- **`packages/<pkg>/src/<pkg>/_transport.py` + `_atransport.py` —
  `handle_request()` modification:**
  ```python
  # Phase 8:
  stop=stop_after_attempt(self._max_attempts),
  # Phase 13:
  stop=stop_after_attempt(request.extensions.get("max_attempts", self._max_attempts)),
  ```
  ~1 LOC change per file × 4 paquetes × 2 surfaces = 8 LOC total.

- **`packages/<pkg>/src/<pkg>/client.py` + `aio.py` — `_request()` shell
  extension set:**
  ```python
  req.extensions["max_attempts"] = self._max_retries + 1
  ```
  Junto a las otras extensions. ~1 LOC per shell × ~7 shells (4 sync + 3
  async; matriz aio Phase 10 included).

- **`packages/matriz-client/src/matriz_client/_state.py` — agrega field:**
  ```python
  @dataclass(slots=True)
  class _ClientState:
      ...
      client_max_retries: int = 2
  ```
  ~1 LOC matriz only (D-T3).

- **`packages/matriz-client/src/matriz_client/client.py:253` + `aio.py:~306`
  — `_ensure_token()` modification:**
  ```python
  # Phase 10:
  self._state.token_store = build_token_store(self._state, max_retries=self._max_retries)
  # Phase 13 (matriz only):
  self._state.token_store = build_token_store(self._state, max_retries=self._state.client_max_retries)
  ```
  ~2 LOC change matriz only (D-T3).

- **`packages/matriz-client/src/matriz_client/client.py:__init__` +
  `aio.py:__init__` — set `client_max_retries`:**
  ```python
  self._state.client_max_retries = max_retries
  ```
  ~2 LOC matriz only.

- **`verification/test_with_options.py`** — NUEVO archivo Phase 13 Plan 1
  con 4 tests cross-cutting (D-P2).

- **`packages/<pkg>/tests/test_client.py` + `test_async_client.py`** —
  agrega per-paquete `test_with_options_*` (close-is-noop, basic returns,
  chaining edge cases) en Plan 2-5.

- **`packages/matriz-client/tests/`** — agrega
  `test_with_options_does_not_rebind_tokenstore_max_retries` (D-T5) en
  Plan 4.

- **`verification/snapshots/<pkg>-surface.txt`** — actualiza per-paquete
  en Plans 2-5 con 2 entries nuevas (D-V5).

- **No nuevas runtime deps.** Phase 13 NO agrega ni a `pyproject.toml`
  per-paquete ni al root. `tenacity 9.1.4` ya presente desde Phase 8.

- **`pre-commit run --all-files`** debe pasar al final del Plan 5.

</code_context>

<specifics>
## Specific Ideas

- **View constructor pattern (D-V1, todos los paquetes):**
  ```python
  def with_options(self, *, max_retries: int) -> Self:
      """Return a new Client view with overridden options.

      The view shares this Client's _state and underlying httpx.Client
      (no re-auth, no connection pool fragmentation). Only the per-call
      max_retries differs.

      Use for one-off requests that need different retry behavior::

          # Bump retries for a flaky symbol
          quote = client.with_options(max_retries=5).get_quote("RARE")

          # Disable retries entirely for debug
          movs = client.with_options(max_retries=0).get_movimientos(...)

      The view's close()/__exit__/aclose()/__aexit__ are no-ops — they
      do NOT touch the parent's http_client. Closing the parent (or
      letting the parent fall out of scope) closes the shared pool.

      Chaining returns a fresh view each time; the inner call wins::

          client.with_options(5).with_options(10)._max_retries  # 10
          client._max_retries                                    # 2 (intact)

      `configure()` called on the module AFTER with_options() does NOT
      affect existing views (the view holds the _state instance from the
      time of construction).
      """
      _validate_max_retries(max_retries)
      view = type(self).__new__(type(self))
      view._state = self._state       # SHARE — anti-Pitfall 13
      view._max_retries = max_retries  # OVERRIDE
      view._is_view = True            # FLAG for close()/exit no-op
      return view
  ```

- **RetryTransport extension wiring (Plan 1):**
  ```python
  # _transport.py Phase 8 line:
  for attempt in Retrying(
      stop=stop_after_attempt(self._max_attempts),
      ...
  ):
  # Phase 13 replacement:
  effective_max_attempts = request.extensions.get("max_attempts", self._max_attempts)
  for attempt in Retrying(
      stop=stop_after_attempt(effective_max_attempts),
      ...
  ):
  ```
  Identical change × `_atransport.py` × 4 paquetes.

- **Shell `_request` extension set (uniform):**
  ```python
  # Existing Phase 8:
  req.extensions["idempotent"] = spec.idempotent
  req.extensions["request_id"] = request_id
  req.extensions["endpoint_name"] = spec.endpoint_name
  # Phase 13 addition:
  req.extensions["max_attempts"] = self._max_retries + 1
  ```
  Setea siempre (uniforme; el view's `self._max_retries` ya está sobrescrito).

- **D-P2 CRITICAL merge gate test shape (matriz new_order):**
  ```python
  # verification/test_with_options.py
  def test_with_options_does_not_bypass_mutation_gate_matriz(httpx_mock):
      """Anti-Pitfall 14 — duplicate orders money-on-the-line.

      with_options(max_retries=10).new_order(...) MUST execute EXACTLY 1
      outgoing request under 503 — mutation gate (Phase 8 D-01) remains
      the absolute authority on retry permission.
      """
      import matriz_client
      matriz_client.configure(
          base_url="https://api.test",
          username="u", password="p",
          token="test-token", token_expires_at=9_999_999_999.0,
      )
      httpx_mock.add_response(status_code=503)
      client = matriz_client._get_default()
      with pytest.raises(matriz_client.exceptions.MatrizClientError):
          client.with_options(max_retries=10).new_order(
              symbol="GGAL", side="BUY", quantity=1, price=100.0,
              account="test-acct",
          )
      assert len(httpx_mock.get_requests()) == 1  # NO retry
  ```

- **D-T5 matriz TokenStore test shape:**
  ```python
  # packages/matriz-client/tests/test_with_options.py
  def test_with_options_does_not_rebind_tokenstore_max_retries(
      monkeypatch, httpx_mock,
  ):
      """D-T1 — view's max_retries is HTTP-only; TokenStore stays gobernado
      por el Client constructor (state.client_max_retries).
      """
      import matriz_client
      from matriz_client import _token_store as ts

      build_calls = []
      orig_build = ts.build_token_store

      def spy(state, *, max_retries):
          build_calls.append(max_retries)
          return orig_build(state, max_retries=max_retries)

      monkeypatch.setattr(ts, "build_token_store", spy)

      client = matriz_client.Client(
          base_url="https://api.test",
          username="u", password="p",
          max_retries=2,
      )
      view = client.with_options(max_retries=10)
      # Force first _ensure_token from view
      client._state.token = None
      client._state.token_expires_at = 0.0
      httpx_mock.add_response(json={"status": "OK", "token": "fresh"})
      view._ensure_token()
      assert build_calls == [2]  # NOT 10 — view's max_retries did NOT leak
  ```

- **Commit message patterns (Plans 1-5):**
  - Plan 1: `feat(verification): RetryTransport reads max_attempts extension + cross-cutting with_options tests (ERG-01)`
  - Plan 2: `feat(ambito-financiero-client): Client.with_options(*, max_retries) + AsyncClient.with_options + _is_view lifecycle (ERG-01)`
  - Plan 3: `feat(higyrus-client): Client.with_options(*, max_retries) + AsyncClient.with_options + _is_view lifecycle (ERG-01)`
  - Plan 4: `feat(matriz-client): Client.with_options(*, max_retries) + state.client_max_retries TokenStore isolation + _is_view lifecycle (ERG-01)`
  - Plan 5: `feat(iol-client): Client.with_options(*, max_retries) + AsyncClient.with_options + _is_view lifecycle + green gate (ERG-01)`

- **LOC delta estimate (Plans 2-5 per-paquete):**
  ```
  client.py:           +12 LOC (with_options method + close() _is_view check)
  aio.py:              +12 LOC (mismo)
  _transport.py:       +0 LOC (Plan 1 ya tocó)
  _atransport.py:      +0 LOC (Plan 1 ya tocó)
  _state.py:           +1 LOC matriz only (client_max_retries field)
  tests/test_client.py:+~25 LOC (mocked tests)
  tests/test_async_client.py:+~25 LOC
  tests/test_with_options.py (matriz only): +~40 LOC
  snapshots/<pkg>-surface.txt: +2 entries
  TOTAL per paquete: ~80 LOC (matriz: ~125 LOC con TokenStore test)
  ```

</specifics>

<deferred>
## Deferred Ideas

- **`with_options(timeout=...)` per-call timeout** — research ARCHITECTURE
  §2.5 path "Other options"; PROJECT.md:40 scope lock; defer a v1.3.
- **`with_options(headers={...})` per-call headers** — mismo; defer a v1.3.
- **`with_options(http_client=...)` per-call httpx swap** — mismo; defer a v1.3.
- **`Client.from_env()` classmethod × 4 packages** — SKIPPED en v1.2 por
  REQUIREMENTS §Future ("industry survey 7 SDKs encontró ZERO con este patrón;
  v1.1 ya implementa implicit env fallback en constructor vía `_ClientState`
  + `load_dotenv()`"). Pattern documentation lives en CLAUDE.md / README en
  lugar de classmethod redundante.
- **`request.extensions["max_attempts"]` per-call override from caller
  directly (without view)** — i.e., el caller pasa `extra={"max_attempts": N}`
  al método get_X. Power-user path. NO en v1.2 (only via `with_options` view
  surface). v1.3+ si UX feedback lo justifica.
- **`with_options(max_retries=N)` exposure via top-level module function**
  (`<pkg>.with_options(...)`) — D-V5 reject explícito (with_options es
  method-on-instance, no singleton-delegator). v1.3 si patrón emerge.
- **`_is_view` flag promoted to ámbito/iol/higyrus uniformly via codegen**
  (D-T4 carry-forward) — revisar en v1.3 libcst spike post-NO-GO Phase 12.
- **TokenStore-rebind-on-with_options as explicit policy choice** — D-T1
  decide HTTP-only isolation; un escenario donde el caller QUIERE rebind
  el TokenStore retry cap (e.g., auth server bajo carga conocida) sería
  v1.3+ con surface adicional como `client.with_options(token_refresh_retries=N)`.
- **Driver smoke probe usando `with_options`** (D-D1 carry-forward) —
  Phase 15 driver migration decide adoption per driver. Phase 17 LIVE-03
  re-verifica.
- **`__repr__` del view explícito** (Claude's Discretion) — planner decide;
  cosmético; v1.3 ajusta si UX feedback.

### Reviewed Todos (not folded)

- **`matriz-driver-findings-file-handling.md`** — ya `.planning/todos/completed/`
  desde Phase 11. NO se folda en Phase 13 (sin relación al surface
  `with_options`).

</deferred>

---

*Phase: 13-Cross-Package Ergonomics (`with_options(max_retries=N)`)*
*Context gathered: 2026-06-14*
