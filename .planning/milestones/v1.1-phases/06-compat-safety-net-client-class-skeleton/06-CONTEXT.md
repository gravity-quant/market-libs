# Phase 6: Compat Safety Net + Client Class Skeleton - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 6 entrega dos cosas indivisibles:

1. **Red de seguridad (REFAC-01)** — `verification/test_public_surface.py` que snapshotea cada
   atributo público y signature de los 4 paquetes (`iol-client`, `higyrus-client`,
   `ambito-financiero-client`, `matriz-client`), más un test `fixture-reaches-production`
   guard por paquete que verifica que un sentinel monkeypatched aparece en el wire
   request (header de auth nativo de cada paquete). La red queda en su lugar **antes**
   del primer refactor; los 277 tests baseline deben quedar verde antes y después.

2. **Esqueleto de clase Client (REFAC-02)** — `Client` (sync) y `AsyncClient` (async) por
   paquete con `close()`/`aclose()`, sync/async context manager, estado scoped a
   instancia en `_ClientState` (dataclass con `base_url`, credenciales, token,
   `token_expires_at`, `http_client`, `refresh_token`). La API top-level
   (`pkg.get_X(...)`, `pkg.configure(...)`, `pkg.login()`) sigue funcionando 100% sin
   cambios para callers vía PEP 562 `__getattr__` shim a nivel de módulo, y los 277
   tests mockeados pasan verde después del refactor (conftest migrado a
   `configure(token=..., token_expires_at=...)`).

**No entrega:** `_core.py` extracción (Phase 7), retries/backoff (Phase 8), structured
logging (Phase 8), deferred bug fixes (Phase 9), matriz `aio.py` (Phase 10), harness
hardening (Phase 11). Nada del scope v1.0 (verificación live) se re-toca.

**Orden de ejecución locked:** ámbito → iol → higyrus → matriz (per-package serial, v1.0
lesson). Cada paquete es 1 commit atómico para Client/shim/conftest/drop-globals.

</domain>

<decisions>
## Implementation Decisions

### Shim de compatibilidad (PEP 562)

- **D-01:** Solo `__getattr__` read-only a nivel de módulo (`client.py` y `aio.py` de
  cada paquete). **NO** `ModuleType` subclass con `__setattr__`. Pitfall #1 se
  cierra vía migración de conftest, no vía mecanismo bidireccional.
- **D-02:** Atributos forwarded por el shim: **solo token-related** —
  `_token`, `_token_ts` (iol), `_token_expires_at`, `_token_lock` (aio). El resto de
  globals legacy (`_user`, `_password`, `_base_url`, `_client`) se eliminan; cualquier
  lectura post-refactor recibe `AttributeError`. Excepción: `_client` SÍ se forwarda
  (resuelve a `_default()._state.http_client`) para preservar el patrón de
  `main_higyrus.py` que muta `_client.event_hooks` (CR-07 queda diferido a Phase 11).
- **D-03:** Forwarding **silencioso** — sin `DeprecationWarning`, sin env-var opt-in.
  El target de v1.1 es zero-noise non-breaking; cualquier deprecation surface se
  introduce en v1.2/v2.0.
- **D-04:** Conftest de cada paquete migra de
  `monkeypatch.setattr(pkg.client, "_token", "test-token", raising=False)` +
  `monkeypatch.setattr(pkg.client, "_token_expires_at", 9_999_999_999.0, raising=False)`
  a `pkg.configure(token="<sentinel>", token_expires_at=9_999_999_999.0)`. La
  extensión de `configure()` con `token=...`/`token_expires_at=...` es prerrequisito
  del shim.

### Granularidad de planes en la fase

- **D-05:** **5 planes** en la phase:
  - Plan 1 — REFAC-01: golden public-surface snapshot × 4 pkgs + fixture-reaches-production
    guard × 4 pkgs. Tests-only (sin tocar producción); 277 tests siguen verde.
  - Plans 2–5 — REFAC-02 per package, orden serial ámbito → iol → higyrus → matriz.
    Cada uno es **1 commit atómico** que incluye: `_state.py` + `Client`/`AsyncClient`
    + shim PEP 562 + migración de conftest del paquete + remoción de globals legacy
    module-level. Si Plan 3 (iol) explota, Plans 1+2 (ámbito) quedan mergeables.
- **D-06:** Snapshot ownership: el plan REFAC-01 freezea el snapshot del estado
  **PRE-refactor**. Cada plan REFAC-02 actualiza el snapshot del paquete tocado
  añadiendo entradas nuevas (`Client`, `AsyncClient`, `close`, `aclose`, etc.) pero
  nunca removiendo. El test del snapshot falla si una entrada baseline desaparece
  → garantiza zero breaking change accidental.
- **D-07:** Test cadence por plan REFAC-02:
  `uv run pytest packages/<pkg>/` + `uv run pytest verification/test_public_surface.py`
  pre-commit. Cubre el paquete tocado (zero regression dentro) + el safety net
  global (zero spillover entre paquetes). CI sigue corriendo full matrix completa.

### Mecanismo del public-surface snapshot

- **D-08:** Storage: **text file per paquete** en
  `verification/snapshots/<pkg>-surface.txt`. Una línea por símbolo público
  (sorted), incluye nombre + tipo (function/class/module attr) + signature
  stringified. Git diff humano captura cambios en code review.
- **D-09:** Scope del snapshot: **top-level (`__all__`) + signatures + submodules
  públicos exposed** (`pkg.client`, `pkg.aio`, `pkg.models`, `pkg.exceptions`,
  `pkg.types` cuando aplique). NO incluye atributos privados (`_token`, `_client`) —
  esos pertenecen al shim y son volátiles. El test registra que el shim
  `__getattr__` existe pero no enumera qué forwarda.
- **D-10:** Test único: `verification/test_public_surface.py` con sweep × 4 paquetes
  (corre con `uv run pytest verification/test_public_surface.py`). Sin per-package
  test file (replicar 4× para un test puramente comparativo es boilerplate sin
  beneficio; el snapshot file ya es per-pkg).
- **D-11:** Regeneración intencional: script
  `verification/regen_snapshots.py` que reescribe los 4 archivos. El operador
  commitea el diff junto con el cambio que lo justifica. El test del CI compara
  strict-equal vs el archivo committed → pasa solo si el commit incluye la
  actualización del snapshot. Forensic-localizable via
  `git log -- verification/snapshots/<pkg>-surface.txt`.
- **D-12:** Fixture-reaches-production guard scope: **1 test sync + 1 test async
  por paquete** sobre el auth header nativo:
  - `iol`: `Authorization: Bearer <SENTINEL>`
  - `higyrus`: `Authorization: Bearer <SENTINEL>` (body password redaction es
    tema de LOG-02 Phase 8)
  - `matriz`: `X-Auth-Token: <SENTINEL>`
  - `ambito`: no-auth → verifica que `base_url` customizado vía `configure()`
    aparece en la URL del request (proxy de que la configuración alcanza el wire).
  Total: 4 sync + 4 async = 8 tests. **No** se incluye cross-leak SYNC-sentinel
  vs ASYNC-sentinel guard en Phase 6; ese test está explícitamente requerido por
  Phase 7 REFAC-03 success-criterion #2.

### Signature de `Client.__init__`

- **D-13:** Kwargs de `__init__`: **solo los equivalentes a `configure()`
  vigente + extensión token/token_expires_at**. Por paquete:
  - `iol`: `Client(*, username=None, password=None, base_url=None, token=None, token_expires_at=None)`
  - `higyrus`: `Client(*, username=None, password=None, base_url=None, token=None, token_expires_at=None)`
  - `matriz`: `Client(*, username=None, password=None, base_url=None, token=None, token_expires_at=None)`
  - `ambito`: `Client(*, base_url=None)`
  `_ClientState` internamente lleva `refresh_token`/`account_id`/`http_client` pero
  **NO** se exponen como kwargs en Phase 6 — esos llegan en Phase 8 (`http_client=`
  para retry transport injection) y Phase 9 (`refresh_token` BUG-03, `account_id`
  BUG-04).
- **D-14:** Semántica de `pkg.configure(**kwargs)` post-refactor: **reemplaza
  `_default_client` con nueva instancia `Client(**kwargs)`**. Sin mutación in-place
  de `_default._state`. Preserva semántica v1.0 (reset de `_token`/`_client`).
  Instancias `Client()` explícitas del caller NO se ven afectadas por
  `configure()`.
- **D-15:** Lifecycle del `_default_client`: **lazy en primer acceso**. `client.py`
  al import deja `_default_client = None`; cualquier llamada top-level
  (`pkg.get_X(...)`) o lectura via shim dispara `_get_default()` que construye
  `Client()` leyendo env vars. Mantiene el patrón v1.0 (`load_dotenv()` al import,
  instancia construida cuando se la necesita).
- **D-16:** `AsyncClient` cleanup: **caller-responsible**. Implementa `aclose()`
  + `__aenter__`/`__aexit__`. Sin `atexit` handler (Pitfall #12 — no hay event loop
  al exit). Sin `ResourceWarning` automático en `__del__` (event loop puede estar
  cerrado en `__del__` y el warning se pierde o crashea). Documentamos el contrato
  en el docstring del módulo y de `AsyncClient`.
- **D-17:** Validación de credenciales: **lazy** — `Client()` sin credenciales NO
  raisea en `__init__`; `_ensure_token()` levanta `<Pkg>AuthError` en el primer
  call que necesite auth. Preserva el patrón v1.0 (`configure()` sin args es legit;
  el error llega cuando se necesita).
- **D-18:** `Client.__repr__()` redacta credenciales y token: muestra
  `<Pkg>Client(base_url='https://api.test', username='alice', password='***', token='***')`.
  Override del auto-repr de `@dataclass`. Consistente con
  `verification/redaction.py` policy. Aplica idéntico a `AsyncClient`.

### Continuidad de patrones top-level

- **D-19:** `load_dotenv()` se sigue llamando a nivel módulo de `client.py` (no
  `aio.py`, no `Client.__init__`). Compat 100% con .env discovery v1.0; tests
  existentes siguen funcionando sin cambios extra. `_ClientState` lee env vars como
  defaults en `__init__`.
- **D-20:** `pkg.login()` se mantiene como **función top-level** implementada
  como shim `def login(): return _get_default().login()`. El método
  `Client.login()` ejecuta el auth flow contra `self._state`. Back-compat 100%
  con docstrings v1.0.
- **D-21:** Driver hooks: `main_higyrus.py` mutación de `pkg.client._client.event_hooks`
  funciona transparente porque el shim forwarda `_client` → `_default._state.http_client`
  (la `httpx.Client` real) y el caller muta el dict in-place. **`main_higyrus.py`
  NO se toca en Phase 6**. CR-07 (lock missing en hook mutation multi-event-loop)
  queda diferido a Phase 11 como ya lo marca el ROADMAP.
- **D-22:** matriz `Client.login()` parsea `response.headers["X-Auth-Token"]`
  (no body) y store en `self._state.token`. El shim forwarda `pkg.client._token` →
  `_default._state.token`. Zero diferencia de wire vs v1.0.

### Pickle/deepcopy contract

- **D-23:** `Client.__reduce__()` raisea `TypeError(f"<Pkg>Client is not picklable; "
  "use multiprocessing's fork start method or recreate in worker")`. Aplica
  idéntico a `AsyncClient`. Documenta el contrato; falla loud antes de errores
  silenciosos en `multiprocessing.spawn` (Pitfall #11). `__deepcopy__` también
  raisea (httpx.Client no es deepcopy-safe sin más). El docstring de la clase
  documenta cómo recrear estado entre workers (rebuild desde env + `configure`).

### Claude's Discretion

El planner decide (basado en research):

- Estructura interna exacta de `_state.py` (dataclass shape, slots, default
  factories). El research recomienda `@dataclass(slots=True) _ClientState`; el
  planner ajusta si encuentra incompatibilidad con `httpx.Client` field.
- Implementación del `_get_default()` (módulo-level function vs cached property
  sobre el módulo).
- Convención de sentinels en conftest (`SYNC-sentinel-<pkg>` vs `test-token-<pkg>-sync`
  vs UUID-based). Mantener distinguibles sync vs async incluso si el cross-leak
  guard no se exige en Phase 6.
- Lugar exacto del `regen_snapshots.py` script y format del output (single binary
  vs per-pkg). Sugerencia: módulo simple en `verification/` que itera los 4
  paquetes.
- Si `Client` y `AsyncClient` heredan de un mismo `BaseClient` por paquete o son
  clases independientes. Sin shared internals entre paquetes; dentro del paquete
  el research no impone elección.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & milestone

- `.planning/PROJECT.md` — v1.1 milestone goals, scope, key decisions; menciona el shim
  PEP 562 como mecanismo de compat y `configure(token=..., token_expires_at=...)`
  como extensión locked.
- `.planning/REQUIREMENTS.md` §"Refactor arquitectónico (REFAC)" — REFAC-01 y REFAC-02
  son los requirements de Phase 6.
- `.planning/ROADMAP.md` §"Phase 6" — goal y 5 success criteria explícitos.
- `.planning/STATE.md` §"Decisions" y §"Blockers/Concerns" — Pitfall #1 marcado como
  blocker pre-refactor; orden serial por paquete locked.

### Research (v1.1)

- `.planning/research/SUMMARY.md` §"Architecture Approach" — recomendación del 5-module
  pattern por paquete (`_state.py`, `_core.py`, `_transport.py`, `_atransport.py`,
  `_logging.py`); Phase 6 entrega `_state.py` + `Client`/`AsyncClient`, el resto cae
  en Phase 7/8.
- `.planning/research/SUMMARY.md` §"Phase 0: Compat Safety Net and Golden Tests" — esta
  phase corresponde al "Phase 0" del research (renombrado a Phase 6 en el roadmap v1.1).
- `.planning/research/PITFALLS.md` §"Pitfall 1" — silent monkeypatch breakage; mandato
  de "fixture reaches production" guard ANTES del primer refactor.
- `.planning/research/PITFALLS.md` §"Pitfall 2" — `configure()` semantics: ONLY mutates
  default; explicit `Client()` instances unaffected. Test parity requirement.
- `.planning/research/PITFALLS.md` §"Pitfall 11" — pickle contract.
- `.planning/research/PITFALLS.md` §"Pitfall 12" — atexit async cleanup; no event loop
  at exit. Justifica D-16 (sin atexit handler).
- `.planning/research/ARCHITECTURE.md` — diagrams del Client class + shim flow.

### Codebase maps (vigentes)

- `.planning/codebase/TESTING.md` — autouse fixtures actuales con
  `monkeypatch.setattr` que necesitan migrar a `configure(token=...)`. Es la
  baseline del trabajo de conftest migration.
- `.planning/codebase/ARCHITECTURE.md` §"Module-Level State Pattern" — el patrón
  singleton que estamos refactorizando.
- `.planning/codebase/CONVENTIONS.md` — naming conventions de exceptions, modules,
  variables que se preservan post-refactor.
- `.planning/codebase/CONCERNS.md` — tech debt conocido del singleton state pattern
  (justifica el refactor).

### Forward references (no leer todavía)

- `.planning/ROADMAP.md` §"Phase 7" — REFAC-03 `_core.py` extraction depende del
  esqueleto Client de Phase 6; los cross-leak sentinels SYNC vs ASYNC son
  responsabilidad de Phase 7, no Phase 6.
- `.planning/ROADMAP.md` §"Phase 8" — `http_client=` kwarg llegará en Phase 8 para
  retry transport injection.
- `.planning/ROADMAP.md` §"Phase 9" — `refresh_token`/`account_id` kwargs llegarán
  en Phase 9 (BUG-03, BUG-04).
- `.planning/ROADMAP.md` §"Phase 11" — CR-07 (event_hooks lock missing) cierre.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`verification/` harness module** (`redaction`, `env_gate`, `mutation_gate`,
  `findings`, `schema`, `capture`, `anonymize`, `safemodel_diff`, `cycle_report`) —
  ya vigente. `verification/test_public_surface.py`, `verification/snapshots/` y
  `verification/regen_snapshots.py` aterrizan en este directorio como hermanos del
  resto, sin tocar lo existente.
- **`verification/redaction.py`** patterns — la lógica de redacción de
  `Client.__repr__` reutiliza el mismo concepto (Bearer/token masking), pero NO
  importa de `verification/` (los packages son standalone wheels). Reimplementación
  inline en `client.py` por paquete.
- **`configure()` actual** por paquete — punto de entrada existente; solo se extiende
  con nuevos kwargs `token=`, `token_expires_at=`. Signature backwards compatible.
- **Conftest autouse fixtures × 4 paquetes** (`packages/*/tests/conftest.py`) — fuente
  de verdad de qué attrs setea cada test runner; la migración a
  `configure(token=...)` se hace 1:1 con esos fixtures.

### Established Patterns

- **Module-level singleton state** (`_token`, `_token_ts`, `_client`, `_user`,
  `_password`, `_base_url`) — patrón que estamos REEMPLAZANDO. Post-refactor,
  `_default_client._state` lo absorbe; el shim PEP 562 preserva las lecturas
  legacy a token-related attrs.
- **Dual sync/async surfaces con state independiente** — patrón que se PRESERVA
  literal: `client.py` tiene `_default_sync_client`, `aio.py` tiene
  `_default_async_client`. NO se comparte estado (ése es el espíritu de Pitfall
  #3 que Phase 7 enforciará).
- **`@dataclass(frozen=True, slots=True)` para SafeModel** — research recomienda
  `@dataclass(slots=True)` para `_ClientState` y `Client` (no frozen porque
  necesita refresh interno de campos). Mismo idiom que ya existe en `higyrus_client.models`,
  `matriz_client.models`.
- **Tests function-level (no class-based) con `httpx_mock` fixture** — el test
  `verification/test_public_surface.py` y los fixture-reaches-production guards
  siguen este patrón.
- **`load_dotenv()` al import de `client.py`** — patrón conservado. Tests no
  dependen de `.env` real (configure() override en autouse).

### Integration Points

- **`packages/<pkg>/src/<pkg>/__init__.py`** — re-exports cambian para incluir
  `Client` y `AsyncClient` (top-level símbolos). El golden snapshot lo captura.
- **`packages/<pkg>/src/<pkg>/client.py`** — agrega `class Client`, deja el shim
  PEP 562 `__getattr__` para los globals legacy, elimina los `_token`/`_user`/
  etc. como variables module-level.
- **`packages/<pkg>/src/<pkg>/aio.py`** — análogo para async (paquetes ambito,
  iol, higyrus; matriz no tiene `aio.py` aún → Phase 10).
- **`packages/<pkg>/src/<pkg>/_state.py`** — nuevo módulo, contiene
  `@dataclass(slots=True) _ClientState`. Único módulo NUEVO en Phase 6.
- **`packages/<pkg>/tests/conftest.py`** — migra autouse fixtures a
  `pkg.configure(token=..., token_expires_at=..., base_url=..., username=..., password=...)`.
- **`verification/test_public_surface.py`** — nuevo, snapshot test único × 4
  paquetes.
- **`verification/snapshots/<pkg>-surface.txt`** × 4 — nuevos archivos
  committeados.
- **`verification/regen_snapshots.py`** — nuevo script ejecutable manual.
- **`main_higyrus.py`** — NO se toca (el shim preserva `pkg.client._client`
  access). CR-07 lock fix queda Phase 11.

</code_context>

<specifics>
## Specific Ideas

- **Convención de sentinels en conftest:** `SYNC-sentinel-<pkg>` vs `ASYNC-sentinel-<pkg>`
  para que sean trivialmente distinguibles aunque Phase 6 no exija el cross-leak
  guard. Phase 7 los reutilizará verbatim para el guard de REFAC-03.
- **Snapshot file format:** una línea por símbolo, ej:
  ```
  Client : class : (*, username=None, password=None, base_url=None, token=None, token_expires_at=None) -> None
  configure : function : (*, base_url=None, username=None, password=None, token=None, token_expires_at=None) -> None
  get_quote : function : (simbolo, *, mercado='bcba', plazo='t2') -> dict[str, Any]
  ```
  Sorted alphabetically para que git diff sea estable. Comments al top del file
  declaran el snapshot version + `regen_snapshots.py` command que lo regenera.
- **Phase 6 commit pattern:** mensaje del primer commit (REFAC-01) sigue convención
  `docs/feat(verification): public-surface snapshot baseline (REFAC-01)`. Cada
  REFAC-02 per pkg: `refactor(<pkg>): introduce Client class with PEP 562 compat shim (REFAC-02)`.
- **Phase 6 deliverable for downstream:** al final de Phase 6, `_state.py` por paquete
  existe con campos `refresh_token: str | None = None` y `account_id: str | None = None`
  forward-declared (Phase 8 y Phase 9 los pueblan; en Phase 6 quedan `None`). Esto
  evita un schema migration entre v1.1 phases.

</specifics>

<deferred>
## Deferred Ideas

- **Cross-leak SYNC-sentinel vs ASYNC-sentinel guard test** — `monkeypatch(pkg.client, "_token", "SYNC")`
  + `monkeypatch(pkg.aio, "_token", "ASYNC")` y verificar que cada surface usa el
  suyo. Explicitamente Phase 7 REFAC-03 success-criterion #2.
- **`http_client=` kwarg en `Client.__init__`** — para test injection sin
  monkeypatching. P2 backlog; viene con Phase 8 retry transport.
- **`Client.from_env()` classmethod** — explicit env-reading constructor (anthropic
  pattern). Backlog; no se requiere en v1.1.
- **`client.with_options(max_retries=N)` per-call override** — backlog; viene en Phase 8.
- **`refresh_token` y `account_id` kwargs en `Client.__init__`** — Phase 9 (BUG-03,
  BUG-04).
- **CR-07 lock en `_capture_*_query_string`** — Phase 11.
- **CR-08 line length en `main_higyrus.py:767`** — Phase 11 (no es Phase 6 scope).
- **Disk persistence del refresh_token (IOL)** — v1.2.
- **`Client.__init__` con `use_dotenv=False` opt-out** — diferido; no hay use case
  inmediato.

</deferred>

---

*Phase: 6-Compat Safety Net + Client Class Skeleton*
*Context gathered: 2026-06-10*
