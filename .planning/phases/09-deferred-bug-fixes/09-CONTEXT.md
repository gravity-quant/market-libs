# Phase 9: Deferred Bug Fixes - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 9 cierra los 4 hallazgos diferidos de v1.0 (`BUG-01..BUG-04`), aprovechando
que toda la infraestructura habilitante (per-instance `Client`, `_core.py` single-site,
retries+backoff+structured logging) ya aterrizó en Phases 6-8. Cada fix vive en
`_core.py` per paquete (o, donde corresponde, en transport shell / `_state.py`) y
propaga automáticamente a `client.py` + `aio.py` (en los 3 paquetes con superficie
async — matriz sigue sin `aio.py`, defer Phase 10 per D-25 Phase 8).

**Entregables atómicos (por bug):**

1. **BUG-01 — matriz F-09 ERROR-MAP (CFI inválido).** Guard hybrid en
   `build_get_instruments_by_cfi_request`: si `cfi_code` está en el `CFICode`
   `Literal` (9 valores actuales) → pass. Si no, pero matchea `^[A-Z]{6}$`
   (ISO 10962 forward-compat) → pass. Si nada de lo anterior → `raise
   PrimaryAPIError(status="ERROR", description=f"CFI inválido: {cfi_code!r}")`
   pre-HTTP. Regression test cubre 3 buckets (literal-known, regex-forward-compat,
   malformed). Live re-run de `main_matriz.py` flipea el FAIL de
   `cycle_closure_matriz_client` (DRIFT-02) → PASS.

2. **BUG-02 — higyrus F-02 `get_listado_cuentas=0`.** Quick triage:
   re-correr `main_higyrus.py --live` con Phase 8 `_logging.py` en DEBUG,
   comparar request/response vs el smoke pre-Phase-4 (los 4 hipótesis del
   finding: session side-effect login_sync+login_async, rate-limit silencioso,
   cambio real de permisos, server-side bug). Outcome decide path final:
   - (a) Reproducible + transient → NO-FIX clasificación; Phase 8 retries
     amortiguan; mocked regression test cubre 'should-return-non-empty-when-
     accounts-known' como contract guard.
   - (b) NO reproducible → FIXED-by-environment; mocked regression test
     cubre el path "non-empty list" como guard contra regresión.
   - (c) Reproducible + client-side root cause → fix en `_core.py` (single-site)
     + mocked regression test bloquea el bug; finding clasifica FIXED.
   Time-box: 1 plan; outcome documentado en `.planning/verification/higyrus-client-findings.md`
   con `Resolution: <a|b|c>` + (si fix) `Regression: <path>::<test>`.

3. **BUG-03 — IOL refresh_token in-instance.** El código YA está implementado
   (Phase 6 D-IOL-10 + Phase 7 D-04 alias): `_state.refresh_token` per
   instancia (`packages/iol-client/src/iol_client/_state.py:80`), `_ensure_token()`
   intenta refresh antes de password (`client.py:277`, `aio.py:259`), CR-01
   conditional rotation preservada (`parse_login_response` retorna `None`
   cuando el server omite refresh_token; el shell `if refresh is not None:
   state.refresh_token = refresh`). **Phase 9 entrega solamente los
   regression tests mockeados** que ejercitan los 4 paths críticos del
   lifecycle de una sola instancia `Client`/`AsyncClient`:
   - refresh→success (token expirado + refresh_token presente → POST /token
     grant_type=refresh_token → 200 → nuevo Bearer + opcionalmente nuevo
     refresh_token rotado);
   - refresh→401→password fallback (refresh_token revocado/expirado → 401
     IOLAuthError → catch interno → password grant → 200 → nuevo Bearer);
   - refresh con server que NO rota refresh_token (parse_login_response
     retorna `(token, expires_at, None)`; assert `state.refresh_token`
     preservado);
   - refresh con server que SÍ rota refresh_token (assert `state.refresh_token`
     actualizado al nuevo valor).
   Tests sync (`packages/iol-client/tests/test_refresh_token_lifecycle.py`) +
   async mirror (`tests/test_refresh_token_lifecycle_async.py`). NO se
   modifica `_core.py` ni `client.py`/`aio.py`.

4. **BUG-04 — HIGY multi-account iteration.** Decision operator: **per-call
   only** (D-08 abajo). Los 4 endpoints account-dependent (`get_movimientos`,
   `get_posiciones`, `get_posicion_valuada`, + `get_listado_cuentas` con
   `id_cuenta: list[str] | None`) mantienen `id_cuenta` posicional/kwarg
   per-call (status quo Phase 6/7). El `_state.account_id` forward-declared
   (Phase 6 D-13 — higyrus + iol) **se remueve** porque no se va a usar
   (D-09 abajo). Regression tests:
   - Mocked: 2 cuentas mockeadas, loop sobre ambas via `for acct in [a, b]:
     client.get_movimientos(id_cuenta=acct, ...)`, assert ambas requests
     correctamente targeteadas con `id_cuenta` en path/params.
   - Live: `main_higyrus.py --live` itera sobre cuentas reales del `.env`
     (operator confirmó ≥2 cuentas disponibles); driver puede aceptar
     `HIGYRUS_SAMPLE_CUENTAS` env var nuevo (CSV) para hardcode/override.

**Carry-forward Phase 6-8 (NO re-discutido, locked):**

- **`_core.py` single-site fix pattern** (Phase 7 REFAC-03) — los builders/parsers
  son shared; el fix en `_core.py` propaga automáticamente a `client.py` y
  `aio.py`. Cross-leak sentinel test (Phase 7 D-10) sigue activo.
- **Per-package serial idiom** (Phase 6 D-05 / Phase 7 D-13 / Phase 8 D-21):
  orden ámbito → iol → higyrus → matriz. Phase 9 sigue (iol → higyrus → matriz;
  ámbito no tiene bugs en este lote).
- **1 commit atómico por unidad de trabajo** (per package o per bug; D-10 abajo).
- **Snapshot público** (Phase 6 D-09): actualizado per-plan SOLO si la signature
  cambia. BUG-01..04 no cambian signatures públicas → snapshot **sin cambios**
  esperado (validar en green gate).
- **401 re-auth-once + retries/backoff/logging** (Phase 8) ya cross-cutting; los
  fixes NO duplican ni re-implementan esa infra.
- **`_core.raise_for_response`** (Phase 7 + Phase 8 WR-08 enhancement) intacto
  — BUG-01 NO toca este helper (deviation explícita vs literal de ROADMAP que
  decía '_core.raise_for_response'); el guard de CFI vive en el builder porque
  `raise_for_response` solo ve HTTP status, no params (D-02 abajo).
- **`_atransport.py` matriz NO se crea** — Phase 10 territory (D-25 Phase 8
  preserved). Phase 9 NO toca `matriz/_state.py` ni intenta `aio.py` REST.

**Phase 9 NO entrega:**

- `matriz_client/aio.py` REST surface ni `_atransport.py` (Phase 10).
- TokenStore 3-way concurrent (Phase 10, spike-findings validados).
- BUG-03 disk persistence del refresh_token (defer a v1.2 explicit por ROADMAP
  + REQUIREMENTS BUG-03 lit "deferred a disk persistence para v1.2").
- BUG-04 `Client(account_id=X)` constructor pattern (D-08 abajo, defer a v1.2 si
  hay UX feedback).
- BUG-04 propagation de `account_id` a `request.extensions` (sigue siendo
  per-call via `RequestSpec.account_id` Phase 8 D-11; sin cambios).
- HARN-07/08/09/10 y CR-01..08 (Phase 11 territory).
- `main_*.py --live` × 4 (LIVE-01 / LIVE-02) — Phase 9 corre live solo donde
  los bugs lo requieren (matriz BUG-01 cycle_closure; higyrus BUG-02 triage +
  BUG-04 ≥2 cuentas); el full × 4 final gate sigue siendo Phase 11.

</domain>

<decisions>
## Implementation Decisions

### BUG-01 — matriz F-09 ERROR-MAP (CFI inválido)

- **D-01: Hybrid Literal + ISO 10962 regex guard en el builder.**
  En `packages/matriz-client/src/matriz_client/_core.py::build_get_instruments_by_cfi_request`:
  ```python
  _CFI_ISO_RE = re.compile(r"^[A-Z]{6}$")
  _CFI_LITERAL_VALUES = frozenset(get_args(CFICode))  # 9 values from types.py

  def build_get_instruments_by_cfi_request(state, cfi_code):
      if cfi_code not in _CFI_LITERAL_VALUES and not _CFI_ISO_RE.match(cfi_code):
          raise PrimaryAPIError(
              status="ERROR",
              description=f"CFI inválido: {cfi_code!r} (no está en CFICode Literal ni matchea ^[A-Z]{{6}}$)",
              message=None,
          )
      return RequestSpec(...)
  ```
  Tres buckets de input → tres outcomes:
  - **Literal-known** (e.g., `"ESXXXX"`): pass → HTTP request normal.
  - **Regex forward-compat** (e.g., `"ABXXXX"` — 6 majúsculas, no en Literal):
    pass → HTTP request normal (tolerancia a CFIs futuros sin lib bump).
  - **Malformed** (e.g., `"INVALID-CFI"` con guión + 11 chars, `"esxxxx"`
    minúsculas, `"E2XXXX"` con dígito): raise `PrimaryAPIError(status="ERROR")`
    pre-HTTP.

- **D-02: Deviation explícito vs literal ROADMAP `_core.raise_for_response()`.**
  ROADMAP success #1 dice "fixeado en `_core.raise_for_response()` de matriz".
  Operator + planner deviation justificada: `raise_for_response` solo recibe
  el `httpx.Response` (HTTP status code) — no ve el `cfi_code` param que se
  envió. El guard tiene que vivir aguas arriba, donde el cfi_code es visible:
  en `build_get_instruments_by_cfi_request`. La excepción levantada (`PrimaryAPIError(status="ERROR")`)
  es la misma que `raise_for_response` levantaría — el contrato observable
  (probe pattern: `except PrimaryAPIError as exc: if exc.status == "ERROR":
  PASS`) se preserva. Esto se documenta en `09-CONTEXT.md` (este doc) y en
  el `09-XX-PLAN.md` correspondiente para que el ejecutor no se confunda.

- **D-03: Live re-verification dentro de Phase 9 para flipear cycle_closure.**
  Después del fix, el plan corre `uv run python main_matriz.py` (NO `--live`
  flag; el driver YA es live cuando se invoca normal — el flag controla
  mutations). El probe `error_malformed_cfi` (`main_matriz.py:1194`) debe
  reportar PASS (porque ahora `PrimaryAPIError` se levanta antes del HTTP);
  el finding F-09 status flipea CONFIRMED → FIXED + `Resolution: <path>::<test>`
  + `Regression: tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code`.
  El probe 25 `cycle_closure_matriz_client` debería flipear FAIL → PASS en la
  siguiente corrida (la condición "matriz no tiene Open ERROR-MAP findings
  sin Regression" se satisface).

### BUG-02 — higyrus F-02 `get_listado_cuentas=0`

- **D-04: Quick triage + classify (time-box 1 plan).**
  Re-correr `main_higyrus.py` (live, default) con `logging.getLogger("higyrus_client")
  .setLevel(logging.DEBUG)` en el driver (probe-scoped, NO module-level — Pitfall
  6 Phase 8). Capture request/response shape; comparar contra el smoke pre-Phase-4
  (si el snapshot existe en `.planning/verification/schemas/higyrus-client/` o en
  git history del `main_higyrus.py` antes de Phase 4). Outcome decide path:
  - (a) **Reproducible + transient** (e.g., rate-limit silencioso post-Phase-8-retries,
    o session-mutating side effect del login_sync+login_async del driver):
    → clasificar como `NO-FIX (transient/account-state-conditional)`,
    documentar en finding `Resolution:`, los retries de Phase 8 RetryTransport
    ya amortiguan transients (5xx/connection-errors). Regression test mockeado
    cubre el path "should-return-non-empty-when-known-cuentas-exist" como
    contract guard (no como repro).
  - (b) **NO reproducible** (el live re-run devuelve N cuentas non-empty):
    → clasificar como `FIXED-by-environment (root cause exterior al cliente)`,
    documentar en finding `Resolution:`. Regression test mockeado cubre el
    happy path (Bearer + envelope) como guard.
  - (c) **Reproducible + client-side root cause** (e.g., el driver hace
    `login_sync()` luego `login_async()` y la 2da invalida la sesión del
    Bearer): → fix en `_core.py` (e.g., serialize/avoid login double-flow,
    o documentar como user-must-not-mix-sync-and-async-in-same-process).
    Mocked regression test bloquea el bug. Finding flipea OPEN → FIXED +
    `Regression:`.

- **D-05: Outcome decision criteria documented (driver run + classify in same plan).**
  El operator/executor decide qué bucket dispara basado en el output del live run:
  - Empty `[]` retornado nuevamente + Phase 8 logs muestran 200 OK + envelope
    vacío → bucket (a) si la siguiente corrida da non-empty (transient); bucket (c)
    si reproduce 100% del tiempo.
  - Non-empty list (`N >= 1`) retornada → bucket (b).
  - HTTP error 4xx/5xx (no era esperado) → finding actualizado con la nueva
    clase + path alternativo (escalación, no en scope Phase 9 quick triage).
  El plan documenta los 3 buckets con sus criterios de decisión inline para
  que el executor pueda clasificar sin necesidad de re-discusión.

### BUG-03 — IOL refresh_token in-instance (regression tests only)

- **D-06: Code is already in place; Phase 9 entrega solo regression tests.**
  Phase 6 D-IOL-10 ya implementó `_state.refresh_token` per instancia
  (`_state.py:80`), `_ensure_token()` con refresh→password fallback
  (`client.py:277`, `aio.py:259`), y CR-01 conditional rotation
  (`parse_login_response` + `if refresh is not None:` en `login()`/`_refresh()`).
  Phase 9 NO toca `_core.py`, `client.py`, `aio.py`, `_state.py` para BUG-03.

- **D-07: Cuatro paths críticos cubiertos (sync + async mirror).**
  Tests en `packages/iol-client/tests/test_refresh_token_lifecycle.py` (sync)
  + mirror `test_refresh_token_lifecycle_async.py`:
  1. **refresh→success path:** seed `state.refresh_token="seed-refresh-XYZ"`,
     `state.token_expires_at=0.0` (expired), mock `POST /token grant_type=refresh_token`
     → 200 `{"access_token":"NEW-TOK","expires_in":900,"refresh_token":"ROTATED-REFRESH"}`.
     Assert: `state.token=="NEW-TOK"`, `state.refresh_token=="ROTATED-REFRESH"`,
     `state.token_expires_at > now`, exactly 1 outgoing request (no fallback
     password call).
  2. **refresh→401→password fallback path:** seed `state.refresh_token="REVOKED-REFRESH"`,
     `state.token_expires_at=0.0`. Mock `POST /token` (refresh_token grant) → 401
     `{"error":"invalid_grant"}`, then mock `POST /token` (password grant) → 200
     `{"access_token":"NEW-TOK","expires_in":900,"refresh_token":"FRESH-REFRESH"}`.
     Assert: `state.token=="NEW-TOK"`, `state.refresh_token=="FRESH-REFRESH"`,
     exactly 2 outgoing requests (refresh attempt + password fallback), NO
     `IOLAuthError` raised to caller (silently caught + fallback).
  3. **refresh con server que NO rota refresh_token (CR-01 conditional preservation):**
     seed `state.refresh_token="STABLE-REFRESH"`. Mock refresh response → 200
     `{"access_token":"NEW-TOK","expires_in":900}` (NO `refresh_token` field).
     Assert: `state.token=="NEW-TOK"`, `state.refresh_token=="STABLE-REFRESH"`
     (preservado, NOT cleared, NOT replaced with `None`/empty).
  4. **refresh con server que SÍ rota refresh_token:** análogo path 3 pero
     respuesta incluye `"refresh_token":"NEW-ROTATED-REFRESH"`. Assert:
     `state.refresh_token=="NEW-ROTATED-REFRESH"`.

  Async mirror replica los 4 paths usando `AsyncClient`, `pytest-httpx` async
  patterns, y respeta el `token_lock` double-checked locking de `_ensure_token()`
  async (Phase 6 D-IOL-09).

### BUG-04 — HIGY multi-account iteration (per-call only)

- **D-08: Per-call only — operator picks el OR derecho de ROADMAP success #4.**
  ROADMAP literal: "habilitado vía `Client(account_id=X)` por cuenta O `client.get_X(account_id=Y)`
  per-call (operator decision en planning)". Operator decision: **per-call only**.
  - Los 4 endpoints account-dependent (`get_movimientos`, `get_posiciones`,
    `get_posicion_valuada`, `get_listado_cuentas` con `id_cuenta: list[str]`)
    mantienen `id_cuenta` como param posicional/kwarg per-call (status quo
    post-Phase-6).
  - Iteración multi-cuenta = caller loopea: `for acct in cuentas:
    client.get_movimientos(id_cuenta=acct, ...)`.
  - NO se introduce `Client(account_id=X)` constructor kwarg en Phase 9.
  - El `Client.__init__` y `configure()` signatures NO cambian → snapshot
    público SIN cambios esperado en BUG-04.
  - Defer a v1.2 backlog: constructor pattern + per-call override, si UX
    feedback lo justifica (anthropic/openai SDK pattern reference).

- **D-09: Remove `_state.account_id` forward-declared field de higyrus + iol.**
  El field es muerto post-D-08. Removerlo de `packages/higyrus-client/src/higyrus_client/_state.py`
  y `packages/iol-client/src/iol_client/_state.py`. Updatear:
  - Docstring del módulo + del `_ClientState` (removeer "forward-declared for
    Phase 9 BUG-04").
  - Cualquier referencia en tests/conftest.py que use `account_id=` en
    `configure()` (grep + fix).
  - Snapshot público (Phase 6 D-09): NO cambia porque `_state` es módulo
    privado y `_ClientState` no se exporta — el field no aparece en
    `verification/snapshots/<pkg>-surface.txt`.
  - `RequestSpec.account_id` (Phase 8 D-11, en `_core.py` higyrus + matriz)
    NO se toca — eso es un field DIFERENTE para log correlation propagation,
    no relacionado con BUG-04 multi-account API.

- **D-10: Live regression con ≥2 cuentas usando `.env` actual.**
  Operator confirmó ≥2 cuentas reales en `HIGYRUS_USER` actual. Live regression:
  - Driver `main_higyrus.py` extendido con un nuevo probe `probe_multi_account_iteration`
    que loopea sobre N cuentas (source: `get_listado_cuentas()` si retorna
    non-empty, o `HIGYRUS_SAMPLE_CUENTAS` CSV env var nuevo como override) y
    ejercita `get_movimientos`/`get_posiciones`/`get_posicion_valuada` por cada
    una. Assert: cada call retorna sin AuthError ni HigyrusAPIError; los IDs
    de cuenta vistos en logs son distintos.
  - Si BUG-02 quick triage produce bucket (a) o (c) y `get_listado_cuentas`
    sigue `[]`, el probe usa `HIGYRUS_SAMPLE_CUENTAS` (hardcoded 2+ cuentas
    conocidas) como source. NO bloquea BUG-04 cierre.
  - Mocked regression test (`packages/higyrus-client/tests/test_multi_account.py`):
    2 cuentas mockeadas (`"5208"`, `"9999"`), loop sobre ambas, assert wire
    requests tienen los `id_cuenta` correctos en path (`/api/cuentas/5208/movimientos`,
    `/api/cuentas/9999/movimientos`).

### Plan slicing & wave orchestration

- **D-11: 4 planes (Wave 1 || Wave 2 → Wave 3) en orden serial intra-package.**

  - **Wave 1 (parallel-safe — paquetes independientes):**
    - **Plan 09-01 — iol BUG-03:** regression tests sync + async (4 paths
      × 2 surfaces = 8 tests). NO modifica `_core.py`/`client.py`/`aio.py`.
      Tests en `packages/iol-client/tests/test_refresh_token_lifecycle.py`
      + `test_refresh_token_lifecycle_async.py`. 1 commit atómico.
    - **Plan 09-02 — higyrus BUG-02 + BUG-04 (combined per-package atomic):**
      - BUG-02 quick triage (D-04..D-05): re-run `main_higyrus.py` con DEBUG
        logging probe-scoped + classify outcome + actualizar finding
        `Resolution:`.
      - BUG-04 (D-08..D-10): remover `_state.account_id` higyrus, agregar
        `probe_multi_account_iteration` al driver + `HIGYRUS_SAMPLE_CUENTAS`
        env var optional + mocked regression test multi-cuenta.
      - 1 commit atómico (higyrus all bugs cerrados juntos).
      - **Nota cross-package:** Plan 09-02 también remueve `_state.account_id`
        de **iol** (D-09 cubre los dos paquetes) — micro-deviation del
        per-package atomic ideal porque la decisión D-09 cross-cuts ambos.
        Alternativa: si el operator prefiere atomic-puro per-package, el
        delete de `iol/_state.py::account_id` mueve a Plan 09-01 (BUG-03).
        Default: en Plan 09-02 ambos paquetes (más reflejo de la decisión).
        El planner final decide.

  - **Wave 2 (después de Wave 1):**
    - **Plan 09-03 — matriz BUG-01:** Literal+regex hybrid guard en
      `build_get_instruments_by_cfi_request` + mocked regression test
      (3 buckets) + live re-run de `main_matriz.py` que flipea
      `cycle_closure_matriz_client` FAIL → PASS + actualizar finding F-09
      CONFIRMED → FIXED. 1 commit atómico. Wave 2 porque depende de que iol
      y higyrus estén estables (los green-gate downstream incluyen los 4
      paquetes; matriz LAST es el idiom Phase 6/7/8 consistency).

  - **Wave 3 (después de Wave 2):**
    - **Plan 09-04 — Green gate consolidation:** full pytest matriz Python
      3.12 + 3.13 + ruff + ruff format + mypy strict + lint-imports +
      cross-leak sentinel + Phase 6 public-surface snapshot (zero diff
      esperado — BUG-01..04 NO cambian signatures) + new regression tests
      green (`tests/test_refresh_token_lifecycle*.py`, `tests/test_multi_account.py`,
      `tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code`) +
      operator checkpoint. NO toca código de paquetes — validation-only
      atomic commit en `.planning/phases/09-deferred-bug-fixes/09-VALIDATION.md`.

- **D-12: 1 commit atómico por plan (no per-bug).**
  - Plan 09-01: 1 commit (iol BUG-03 regression tests, sync + async).
  - Plan 09-02: 1 commit (higyrus BUG-02 + BUG-04 + `_state.account_id` removal
    en higyrus + iol; el cleanup cross-package es micro-acceptable porque es
    1 línea por paquete).
  - Plan 09-03: 1 commit (matriz BUG-01 guard + regression + live re-run
    confirmation + finding update).
  - Plan 09-04: 1 commit (`09-VALIDATION.md` con CI evidence + finding
    files commit si hay updates).

- **D-13: Live re-verification scope = bug-driven (NO full 4-package live).**
  Phase 9 corre live solo donde el bug lo requiere:
  - Plan 09-02: `main_higyrus.py` live (BUG-02 triage + BUG-04 multi-cuenta).
  - Plan 09-03: `main_matriz.py` live (BUG-01 fix verification + cycle_closure
    flip).
  - Plan 09-01 (iol): NO live — BUG-03 son regression tests mockeados solamente
    (el code change ya está en place desde Phase 6).
  - ámbito: NO live (no bugs en este lote).
  Full 4-package live re-verification es Phase 11 LIVE-01 (sigue siendo el
  final gate del milestone v1.1).

### Claude's Discretion

El planner decide:

- **Layout exacto de los regression tests sync/async iol (BUG-03).** ¿1 archivo
  con paramétrización `(sync, async)` o 2 archivos separados? Recomendación:
  2 archivos (`test_refresh_token_lifecycle.py` + `..._async.py`) per Phase 6
  conftest pattern; mejor separation of concerns para async/sync isolation.
- **Naming exacto del probe new en `main_higyrus.py` (BUG-04).**
  `probe_multi_account_iteration` o `probe_multi_account_sweep` — el planner
  ajusta según idiom existente del driver (verificar `main_higyrus.py` cómo
  nombra otros probes multi-target).
- **`HIGYRUS_SAMPLE_CUENTAS` env var format.** CSV (`"5208,9999"`) o
  whitespace-separated (`"5208 9999"`). Recomendación: CSV (más portable
  con `.env` files; `python-dotenv` no soporta arrays nativos).
- **Ubicación del live re-run de `main_matriz.py` dentro del Plan 09-03.**
  Como step pre-commit (after the fix, before write VALIDATION) o como step
  documentado en el `09-03-PLAN.md` que el operator ejecuta manualmente
  + paste evidence. Recomendación: step manual operator-executed por riesgo
  de mutating gate / order side-effects (matriz es el de mayor blast radius);
  el plan documenta el comando exacto y los probes esperados PASS.
- **Mocked regression test fixtures location para BUG-01.**
  `packages/matriz-client/tests/test_core.py` (nuevo test added) o nuevo
  archivo `tests/test_cfi_validation.py`. Recomendación: extender `test_core.py`
  (mantiene affinity con el lugar donde vive el builder/parser).
- **Buckets del BUG-02 outcome classification — formato del Resolution: line.**
  Free-text con marker `(a)/(b)/(c)` para forensic-localizable, o estructurado
  con tags. Recomendación: free-text con marker explícito + clasificación
  status según FINDINGS-TEMPLATE.md convention.
- **Si el planner detecta que `_state.account_id` removal rompe algún test
  preexistente** (improbable pero posible): si rompe, el planner decide
  si extiende Plan 09-02 con el fix, o si separa a sub-plan. Default:
  extiende Plan 09-02 (mantiene atomic).
- **Verbosidad del finding update post-fix.** El planner decide cuántas
  lines de prosa agregar al `## Cycle Closure` section de los findings
  files (mínimo: status flip + Regression: line; máximo: rationale + delta
  vs prior state). Recomendación: mínimo + 1-2 lines rationale para
  forensic-localizable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & milestone

- `.planning/PROJECT.md` — v1.1 milestone "Tech Debt Cleanup"; target features
  list incluye "Fixes pendientes: F-09 matriz ERROR-MAP, higyrus F-02
  (`get_listado_cuentas=0`), IOL refresh_token persistence, HIGY multi-account
  iteration"; constraint "no shared internals between packages" justifica
  que los fixes vivan en `_core.py` per paquete sin shared module.
- `.planning/REQUIREMENTS.md` §"Bug fixes (BUG)" — BUG-01/02/03/04 con texto
  literal de la decisión per-bug; §"Future Requirements (Defer to v1.2+)"
  confirma BUG-03 disk persistence deferred + BUG-04 constructor pattern
  defer si UX feedback emerge.
- `.planning/ROADMAP.md` §"Phase 9" — Goal + 5 success criteria; **success #1**
  dice `_core.raise_for_response()` (literal, deviation explícito por D-02);
  **success #4** dice "habilitado vía `Client(account_id=X)` O per-call
  (operator decision)" — D-08 elige per-call.
- `.planning/STATE.md` — stopped_at "Phase 8 complete (6/6) — ready to discuss
  Phase 9"; current focus "Phase 9 — deferred bug fixes".

### Findings files (per-package — read antes de plan/execute)

- `.planning/verification/matriz-client-findings.md` §"F-09" — CONFIRMED
  status, expected/actual/diff documentados, classification rationale "Gap
  real en error mapping del cliente". Plan 09-03 lo flipea a FIXED +
  Regression line.
- `.planning/verification/higyrus-client-findings.md` §"F-02" — OPEN status,
  4 hipótesis listadas en el detalle (las que Plan 09-02 quick triage va a
  separar). El finding incluye "Resolution: OPEN — investigación deferida
  fuera de scope de Phase 4. Candidato para polish post-milestone." — Plan
  09-02 cierra este OPEN.
- `.planning/verification/CYCLE-REPORT.md` — DRIFT-02 baseline `verification-cycle-2026-Q2`,
  matriz cycle_closure FAIL referenciado; Plan 09-03 documenta el flip.
- `.planning/verification/FINDINGS-TEMPLATE.md` — convention para
  `Resolution:` + `Regression:` fields (la convention forward-looking
  ratificada Phase 5 Op A).

### Prior phases (Phase 6-8 carry-forward)

- `.planning/phases/06-compat-safety-net-client-class-skeleton/06-CONTEXT.md`
  — D-IOL-10 refresh→password fallback (Plan 09-01 ejercita esto en regression
  tests); D-13 forward-decl de `account_id` (Plan 09-02 lo remueve por D-09);
  D-09 snapshot público convention (Plan 09-04 valida zero diff).
- `.planning/phases/07-core-py-extraction-sync-async-logic-dedup/07-CONTEXT.md`
  — D-09 import-linter rule (sigue activa, Plan 09-03 builder fix la respeta);
  D-04 B8 alias pattern (Plan 09-03 NO toca `raise_for_response`); D-10
  cross-leak sentinel test (Plan 09-04 lo corre).
- `.planning/phases/08-retries-backoff-structured-logging/08-CONTEXT.md`
  — D-01 RetryTransport (BUG-02 triage usa el DEBUG logging que vive aquí);
  D-09 field set canónico (`account_id` propagation via `RequestSpec` para
  log correlation — Phase 9 NO lo toca, es feature diferente vs BUG-04);
  D-10 RedactingFilter (Plan 09-02 driver re-run lo deja activo, no agrega
  patrones nuevos); D-11 `RequestSpec.account_id` propagation (NO confundir
  con `_state.account_id` que se remueve por D-09).

### Codebase maps (Phase 8 las dejó actualizadas; siguen vigentes)

- `.planning/codebase/ARCHITECTURE.md` §"Module-Level State Pattern" —
  `_state.py` canónico post-Phase-6 (Plan 09-02 D-09 remueve `account_id`);
  §"Module Structure Pattern" para nuevo test files.
- `.planning/codebase/CONVENTIONS.md` — naming conventions Plan 09-* sigue;
  `from __future__ import annotations` mandatory en nuevos archivos.
- `.planning/codebase/TESTING.md` — pytest-httpx pattern + autouse fixtures
  Phase 6 migration (`configure(token=..., token_expires_at=...)`) que Plan
  09-01 + Plan 09-02 mocked tests siguen.
- `.planning/codebase/CONCERNS.md` — sección "Bug backlog (deferred)" lista
  los 4 bugs; Phase 9 cierra los 4.

### Implementation sites (relevantes per-bug, para planner + executor)

**BUG-01 (matriz):**
- `packages/matriz-client/src/matriz_client/_core.py:423-441` — `build_get_instruments_by_cfi_request`
  + `parse_get_instruments_by_cfi_response` (el guard va en el builder).
- `packages/matriz-client/src/matriz_client/types.py:50-61` — `CFICode` Literal
  con 9 valores (source de `_CFI_LITERAL_VALUES`).
- `main_matriz.py:1194-1271` — `probe_error_malformed_cfi` (driver detect path
  pre + post fix).

**BUG-02 (higyrus):**
- `packages/higyrus-client/src/higyrus_client/_core.py:357-384` —
  `build_get_listado_cuentas_request` (URL-encoding quirk encapsulada,
  `idempotent=True`).
- `packages/higyrus-client/src/higyrus_client/_core.py:487-490` —
  `parse_get_listado_cuentas_response` (parser).
- `packages/higyrus-client/src/higyrus_client/_logging.py` — RedactingFilter
  + getLogger (Phase 8); driver re-run usa `.setLevel(DEBUG)` probe-scoped.

**BUG-03 (iol):**
- `packages/iol-client/src/iol_client/_state.py:80` — `refresh_token: str | None = None`
  (ya implementado).
- `packages/iol-client/src/iol_client/client.py:277-289` — `_ensure_token()`
  con refresh→password fallback (ya implementado, Plan 09-01 lo ejercita).
- `packages/iol-client/src/iol_client/aio.py:259-273` — async mirror.
- `packages/iol-client/src/iol_client/_core.py:142-226` — `build_login_request`
  / `parse_login_response` / `build_refresh_request` / `parse_refresh_response`
  (CR-01 conditional rotation: `if new_refresh: return new_refresh else None`).
- `packages/iol-client/src/iol_client/client.py:251-275` — `login()` + `_refresh()`
  con `if refresh is not None:` guard.

**BUG-04 (higyrus):**
- `packages/higyrus-client/src/higyrus_client/_state.py:98` — `account_id: str | None = None`
  (Plan 09-02 D-09 lo remueve).
- `packages/iol-client/src/iol_client/_state.py:84` — `account_id: str | None = None`
  (Plan 09-02 D-09 también lo remueve aquí, cross-package).
- `packages/higyrus-client/src/higyrus_client/client.py:347-422` — los 4
  endpoints account-dependent (mantienen `id_cuenta` per-call).
- `main_higyrus.py` — driver (Plan 09-02 agrega `probe_multi_account_iteration`).

### Spike findings (auto-loaded; reference para Phase 10, NO se aplica a Phase 9)

- `.claude/skills/spike-findings-market-libs/SKILL.md` — TokenStore 3-way +
  RefreshPolicy. Phase 9 NO usa estos patterns (son Phase 10 territory). Pero
  el iol refresh→password fallback de Plan 09-01 es **conceptually compatible**
  con el Spike 003 RefreshPolicy pattern: ambos manejan refresh failure con
  fallback semantics. Phase 9 NO refactoriza iol a usar RefreshPolicy (sería
  scope creep + premature optimization — iol no tiene 3-way concurrency
  pressure que matriz sí).

### Forward references (no leer todavía)

- `.planning/ROADMAP.md` §"Phase 10" — matriz `aio.py` REST surface + TokenStore;
  Plan 09-03 deja el matriz `aio.py` stub (103 LOC Phase 6) intacto.
- `.planning/ROADMAP.md` §"Phase 11" — HARN-07..10, CR-01..08, LIVE-01..02
  (full 4-package live re-verification final gate post-Phase-10).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`_state.refresh_token` per instancia (iol, Phase 6 D-IOL-10)** — Plan 09-01
  regression tests lo ejercitan; ya escrito y testeado via Phase 6 conftest
  migration. NO se toca.
- **`_ensure_token()` con refresh→password fallback (iol, Phase 6 D-IOL-10)** —
  Plan 09-01 ejercita ambos paths (success + fallback) con mocks; código vive
  en `client.py:277` (sync) y `aio.py:259` (async, con `token_lock` double-checked
  locking).
- **CR-01 conditional rotation (`if refresh is not None:` guard, Phase 6 D-IOL-10)** —
  Plan 09-01 test paths 3 + 4 ejercitan ambos branches del `if`.
- **`parse_login_response()` / `parse_refresh_response()` (iol `_core.py`)** —
  retornan `tuple[str, float, str | None]` con el `refresh_token` opcional;
  Plan 09-01 tests mockean responses con/sin `refresh_token` field para los
  4 paths.
- **`_logging.py` per paquete (Phase 8)** — Plan 09-02 driver re-run usa
  `logging.getLogger("higyrus_client").setLevel(DEBUG)` probe-scoped para
  capturar request/response shape durante BUG-02 quick triage; RedactingFilter
  asegura que credenciales no aparezcan en el output.
- **`pytest-httpx` mock pattern (Phase 6/7/8 baseline)** — Plan 09-01 + Plan
  09-02 + Plan 09-03 mocked regression tests siguen el pattern existente
  (autouse `configure()` fixture en `conftest.py`).
- **`verification/test_public_surface.py` + snapshots (Phase 6 D-09)** — Plan
  09-04 corre snapshot diff esperando zero changes en los 4 paquetes (BUG-01..04
  no cambian signatures públicas).
- **`verification/test_sync_async_isolation.py` (Phase 7 D-10) — cross-leak
  sentinel** — Plan 09-04 lo corre intacto.
- **Driver pattern para probes account-dependent en `main_higyrus.py`** — Plan
  09-02 agrega `probe_multi_account_iteration` siguiendo el shape de los
  probes existentes (PASS/FINDING/SKIPPED outcome + append_finding on FINDING).
- **Driver pattern para probes ERROR-MAP en `main_matriz.py`** — Plan 09-03
  NO agrega probe nuevo: el probe `probe_error_malformed_cfi` (`main_matriz.py:1194`)
  YA existe y detecta el caso; con el fix, debería reportar PASS (la branch
  `except PrimaryAPIError as exc: if exc.status == "ERROR": return PASS` que
  está implementada en el probe captura el outcome esperado).

### Established Patterns

- **Per-package serial delivery (ámbito → iol → higyrus → matriz)** — Phase 6
  D-05 / Phase 7 D-13 / Phase 8 D-21. Plan 09 D-11 sigue (ámbito skip — no
  bugs; iol/higyrus parallel-safe Wave 1; matriz Wave 2 LAST).
- **1 commit atómico por unidad (per plan en Phase 9)** — Phase 6/7/8 idiom.
- **Single-site fix en `_core.py`** — Phase 7 REFAC-03. Plan 09-03 (BUG-01) lo
  sigue. Plan 09-01 (BUG-03) NO modifica code (solo tests). Plan 09-02 (BUG-02)
  puede o no fix code según outcome (D-04 buckets).
- **Mocked regression test per bug** — convention v1.0 ratificada (Phase 5
  Op A) + Phase 7/8 idiom. Plan 09-* todos siguen.
- **Finding `Resolution:` + `Regression: <path>::<test>` line** — convention
  Phase 5 Op A. Plan 09-* updates findings con ambos fields.
- **`assert state.token is not None` post `_ensure_token()` para mypy strict
  narrowing** — Phase 6 pattern. Plan 09-01 regression tests NO necesitan
  reproducirlo (los tests son del flow, no del cliente).
- **`from __future__ import annotations` mandatory en nuevos archivos** — Plan
  09-01 + Plan 09-02 nuevos tests files siguen.

### Integration Points

- **Plan 09-01 (iol BUG-03) — files modified/created:**
  - `packages/iol-client/tests/test_refresh_token_lifecycle.py` (NEW, sync 4 tests).
  - `packages/iol-client/tests/test_refresh_token_lifecycle_async.py` (NEW, async 4 tests).
  - `packages/iol-client/tests/conftest.py` (potentially extended si hace falta
    nueva fixture; no esperado — pytest-httpx + `configure()` ya están).

- **Plan 09-02 (higyrus BUG-02 + BUG-04 + cross-package `_state.account_id` removal) — files modified/created:**
  - `packages/higyrus-client/src/higyrus_client/_state.py` (REMOVE `account_id` field + docstring update).
  - `packages/iol-client/src/iol_client/_state.py` (REMOVE `account_id` field + docstring update — cross-package D-09 cleanup).
  - `packages/higyrus-client/tests/test_multi_account.py` (NEW, mocked regression
    test 2-cuentas).
  - `main_higyrus.py` (agregar `probe_multi_account_iteration` + optional
    `HIGYRUS_SAMPLE_CUENTAS` env var read; agregar al main lifecycle probe list).
  - `.planning/verification/higyrus-client-findings.md` (update F-02 con outcome
    `Resolution:` + classification + si fix: `Regression:`).
  - `.planning/verification/CYCLE-REPORT.md` (potentially updated si bucket
    requires meta-baseline update — usually no).

- **Plan 09-03 (matriz BUG-01) — files modified/created:**
  - `packages/matriz-client/src/matriz_client/_core.py` (MODIFY
    `build_get_instruments_by_cfi_request` con Literal+regex guard + import
    `re` + `_CFI_ISO_RE` + `_CFI_LITERAL_VALUES`).
  - `packages/matriz-client/tests/test_core.py` (EXTEND con
    `test_get_instruments_by_cfi_validates_cfi_code` cubriendo 3 buckets).
  - `.planning/verification/matriz-client-findings.md` (update F-09 CONFIRMED →
    FIXED + `Resolution:` + `Regression: tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code`).
  - Manual operator live re-run de `main_matriz.py` (NO code change in driver;
    evidence pasted al PLAN o referenced en SUMMARY).

- **Plan 09-04 (Green gate) — files modified/created:**
  - `.planning/phases/09-deferred-bug-fixes/09-VALIDATION.md` (NEW, CI evidence
    + snapshot zero-diff confirmation + tests-count delta).

- **Snapshot público (Phase 6 D-09) — zero diff esperado para los 4 paquetes en
  Phase 9.** Plan 09-04 valida; si diff, investigation block (probable bug
  introducido por accident, e.g., el `_state.account_id` removal disparó un
  ripple change que tocó signature pública).

</code_context>

<specifics>
## Specific Ideas

- **BUG-01 hybrid guard pattern (matriz `_core.py`):**

  ```python
  # packages/matriz-client/src/matriz_client/_core.py
  from __future__ import annotations
  import re
  from typing import get_args
  from .types import CFICode

  _CFI_ISO_RE = re.compile(r"^[A-Z]{6}$")
  _CFI_LITERAL_VALUES = frozenset(get_args(CFICode))  # {"ESXXXX", "DBXXXX", ...}

  def build_get_instruments_by_cfi_request(
      state: _ClientState,
      cfi_code: CFICode,
  ) -> RequestSpec:
      """``GET /rest/instruments/byCFICode?CFICode=...`` con guard hybrid (BUG-01)."""
      if cfi_code not in _CFI_LITERAL_VALUES and not _CFI_ISO_RE.match(cfi_code):
          raise PrimaryAPIError(
              status="ERROR",
              description=f"CFI inválido: {cfi_code!r} (no está en CFICode Literal ni matchea ^[A-Z]{{6}}$)",
              message=None,
          )
      return RequestSpec(
          method="GET",
          path="/rest/instruments/byCFICode",
          params={"CFICode": cfi_code},
          idempotent=True,
          endpoint_name="get_instruments_by_cfi",
      )
  ```

- **BUG-01 regression test (3 buckets):**

  ```python
  # packages/matriz-client/tests/test_core.py
  import pytest
  from matriz_client._core import build_get_instruments_by_cfi_request, _ClientState
  from matriz_client.exceptions import PrimaryAPIError

  @pytest.mark.parametrize(
      "cfi,expect_raise",
      [
          ("ESXXXX", False),       # Literal-known → pass
          ("DBXXXX", False),       # Literal-known → pass
          ("ABXXXX", False),       # Regex forward-compat → pass
          ("ZQXXXX", False),       # Regex forward-compat (no Primary semantic) → pass
          ("INVALID-CFI", True),   # Malformed (hyphen + len 11) → raise
          ("esxxxx", True),        # Malformed (lowercase) → raise
          ("E2XXXX", True),        # Malformed (digit) → raise
          ("ABCDE", True),         # Malformed (len 5) → raise
          ("ABCDEFG", True),       # Malformed (len 7) → raise
          ("", True),              # Malformed (empty) → raise
      ],
  )
  def test_get_instruments_by_cfi_validates_cfi_code(cfi, expect_raise):
      state = _ClientState(base_url="https://api.example.com")
      if expect_raise:
          with pytest.raises(PrimaryAPIError) as exc_info:
              build_get_instruments_by_cfi_request(state, cfi)  # type: ignore[arg-type]
          assert exc_info.value.status == "ERROR"
          assert "CFI inválido" in exc_info.value.description
      else:
          spec = build_get_instruments_by_cfi_request(state, cfi)  # type: ignore[arg-type]
          assert spec.params == {"CFICode": cfi}
  ```

- **BUG-03 regression test pattern (path 1 — refresh→success):**

  ```python
  # packages/iol-client/tests/test_refresh_token_lifecycle.py
  def test_refresh_success_uses_refresh_token_grant(httpx_mock):
      import iol_client
      iol_client.configure(
          base_url="https://api.iol.test",
          username="u",
          password="p",
          token="STALE-TOK",
          token_expires_at=0.0,  # already expired
          refresh_token="seed-refresh-XYZ",
      )
      httpx_mock.add_response(
          method="POST",
          url="https://api.iol.test/token",
          match_content=b"refresh_token=seed-refresh-XYZ&grant_type=refresh_token",
          status_code=200,
          json={
              "access_token": "NEW-TOK",
              "expires_in": 900,
              "refresh_token": "ROTATED-REFRESH",
          },
      )
      iol_client.get_quote("AAPL")  # triggers _ensure_token() → _refresh() path
      # ... assertions per state.token / state.refresh_token / outgoing reqs count
  ```

- **BUG-04 mocked regression test pattern (2 cuentas):**

  ```python
  # packages/higyrus-client/tests/test_multi_account.py
  def test_multi_account_iteration_via_per_call_id_cuenta(httpx_mock):
      import higyrus_client
      higyrus_client.configure(
          base_url="https://higyrus.test",
          token="TOK",
          token_expires_at=9_999_999_999.0,
      )
      for acct in ("5208", "9999"):
          httpx_mock.add_response(
              method="GET",
              url=f"https://higyrus.test/api/cuentas/{acct}/movimientos?...",
              json={"data": []},
          )
      for acct in ("5208", "9999"):
          higyrus_client.get_movimientos(id_cuenta=acct, fecha_desde=..., fecha_hasta=...)
      requests = httpx_mock.get_requests()
      assert len(requests) == 2
      assert "/5208/" in str(requests[0].url)
      assert "/9999/" in str(requests[1].url)
  ```

- **BUG-04 live probe pattern (`main_higyrus.py`):**

  ```python
  def probe_multi_account_iteration() -> ProbeResult:
      """Probe N (BUG-04): iterate over ≥2 cuentas y ejerce endpoint account-dep."""
      # Source: env var override OR live get_listado_cuentas() OR hardcoded fallback
      cuentas_str = os.getenv("HIGYRUS_SAMPLE_CUENTAS", "").strip()
      if cuentas_str:
          cuentas = [c.strip() for c in cuentas_str.split(",") if c.strip()]
      else:
          live_cuentas = higyrus_client.get_listado_cuentas(estado="alta")
          cuentas = [c.idCuenta for c in live_cuentas[:2]] if len(live_cuentas) >= 2 else []
      if len(cuentas) < 2:
          return ProbeResult("multi_account_iteration", "SKIPPED",
                             "need ≥2 cuentas; set HIGYRUS_SAMPLE_CUENTAS=A,B")
      for acct in cuentas[:2]:
          try:
              higyrus_client.get_movimientos(id_cuenta=acct, ...)
          except HigyrusAPIError as exc:
              return ProbeResult("multi_account_iteration", "FINDING", f"{acct}: {exc}")
      return ProbeResult("multi_account_iteration", "PASS",
                         f"iterated {len(cuentas[:2])} cuentas successfully")
  ```

- **Commit message patterns Phase 9:**
  - Plan 09-01: `test(iol): BUG-03 refresh_token lifecycle regression tests sync + async (BUG-03)`
  - Plan 09-02: `fix(higyrus): BUG-02 triage + BUG-04 multi-account regression + remove _state.account_id (BUG-02, BUG-04)`
  - Plan 09-03: `fix(matriz): BUG-01 hybrid Literal+regex CFI validation + cycle_closure FAIL→PASS (BUG-01)`
  - Plan 09-04: `ci(phase-09): green gate — full pytest + ruff + mypy + snapshot zero-diff + cross-leak (BUG-01..04)`

- **Tests-count delta target (Plan 09-04 VALIDATION.md):**
  - Plan 09-01: +8 tests (4 sync + 4 async iol).
  - Plan 09-02: +N tests (mocked multi-account higyrus; +K si BUG-02 outcome
    requires nuevo regression). Estimate: +2-4.
  - Plan 09-03: +10 tests (3 buckets paramétrizados × 1 base = 10 cases).
  - Total Phase 9: ~755 baseline (Phase 8) + ~20 = ~775 tests verde.

</specifics>

<deferred>
## Deferred Ideas

- **`Client(account_id=X)` constructor pattern para higyrus + iol** — D-08
  picks per-call only. Defer a v1.2 si UX feedback lo justifica (anthropic/openai
  SDK pattern reference). Si se implementa, requeriría re-introducir
  `_state.account_id` que D-09 removió — cheap reverse.

- **`Client(account_id=X)` propagation a `request.extensions["account_id"]`
  para log correlation sin afectar routing** — opción C de la BUG-04 decision;
  rechazada en Phase 9 por ambig semantics (kwarg que solo afecta logs).
  v1.2 si emerge use case de "tag all requests with account from this
  Client".

- **Disk persistence del IOL `refresh_token` cross-process** — ROADMAP +
  REQUIREMENTS BUG-03 lit "deferred a disk persistence para v1.2". Phase 9
  cubre solo in-memory in-instance. v1.2 si el use case lo justifica
  (ahora mismo cada process restart re-hace login con password — aceptable).

- **Extend Literal-runtime-validation pattern a otros params (MarketId,
  SegmentId, Side, OrderType, TimeInForce de matriz)** — BUG-01 cubre solo
  CFI. Otros Literal types tienen el mismo gap latente (cast-bypass at
  runtime) pero no hay finding documentado. Si v1.2 o v1.3 detecta similar
  bugs, aplicar el mismo hybrid guard pattern. NO se hace pre-emptive en
  Phase 9 (scope creep + no operator-driven evidence yet).

- **Higyrus support contact for BUG-02 root cause if quick triage produces
  bucket (a) o (c)** — D-04 time-box es 1 plan. Si quick triage no resuelve
  con certeza, defer follow-up a v1.2 polish (los Phase 8 retries amortiguan).

- **BUG-02 isolated replay script + multi-session capture** — deeper
  investigation que el quick triage rechaza. v1.2 si emerge necesidad
  (probable NO — la opción FIXED-by-environment o NO-FIX transient son
  outcome esperado de la mayoría de findings de este tipo).

- **`HIGYRUS_SAMPLE_CUENTAS` env var promote a `verification/env_gate.py`
  registry** — Plan 09-02 lo introduce solo en `main_higyrus.py`. Si Phase
  11 LIVE-01 requiere el mismo pattern para otros paquetes (e.g.,
  `MATRIZ_SAMPLE_INSTRUMENTS`), refactor a registry shared. v1.2 territory.

- **Probe-scoped DEBUG logging via context manager helper** — Plan 09-02
  driver re-run usa `logging.getLogger("higyrus_client").setLevel(DEBUG)`
  manual. Si el pattern se repite (BUG-02 + futuras investigaciones), un
  helper `with debug_logging_for("higyrus_client"):` sería sintetic.
  v1.2 si emerge necesidad — `verification/` harness territory.

- **Sub-loggers por concern (`<pkg>.refresh`, `<pkg>.auth`)** — Phase 8 D-13
  rejected; sigue. Si BUG-02 quick triage muestra que el DEBUG noise es
  inmanejable, considerar para v1.2.

- **Per-test `httpx-mock` factory for refresh flow** — Plan 09-01 los 8
  tests usan `httpx_mock.add_response(...)` literal. Si emerge mucha
  duplicación, refactor a un `iol_refresh_mock_factory` fixture. v1.2.

### Reviewed Todos (not folded)

- No applicable — el todo `matriz-driver-findings-file-handling` (Phase 8
  reviewed) sigue gated en Phase 11 HARN-07/08/10. NO se folda en Phase 9
  (que es bugs únicamente).

</deferred>

---

*Phase: 9-Deferred Bug Fixes*
*Context gathered: 2026-06-13*
