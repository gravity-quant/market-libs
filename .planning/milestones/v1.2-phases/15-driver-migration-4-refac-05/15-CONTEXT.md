# Phase 15: Driver Migration × 4 (REFAC-05) - Context

**Gathered:** 2026-06-24 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrar los 4 drivers internos `main_*.py` (ámbito → iol → higyrus → matriz) para que
cada `main()` construya **exactamente una** instancia `Client()` (sync) y, dentro de su
único `_async_main()`, **una** `AsyncClient()` — y que esas instancias se threadeen como
parámetro a cada probe. Hoy cada probe alcanza el singleton independientemente vía
`_get_default()` / `aio._get_default()` o vía top-level `pkg.get_X(...)`.

**Dentro de scope:** los 4 archivos driver de la raíz del repo + un test AST-guard por
driver en `verification/`. **Fuera de scope (NO tocar):** los shims de back-compat de la
librería — el PEP 562 `__getattr__` shim y los top-level delegators `pkg.get_X(...)`
QUEDAN intactos (100% backwards-compatible para consumidores externos). Solo migran los
drivers internos. La re-verificación live full × 4 es Phase 17 (LIVE-03), no esta phase.
matriz `ws_client` no se usa en el driver → sin concern de ws-token-sharing en Phase 15.
</domain>

<decisions>
## Implementation Decisions

### Migration mechanics — cómo cada driver obtiene su client

- **D-01: Una `Client()` sync en `main()` + una `AsyncClient()` en `_async_main()`,
  threadeadas como parámetro a cada probe.** Cada probe (`def probe_*`) cambia su
  **signature** para aceptar `client` (sync) o `aclient` (async) y reemplaza cada
  call-site `_get_default().get_X(...)` / `pkg.get_X(...)` por `client.get_X(...)`.
  Construcción bare `Client()` / `AsyncClient()` sin args (env-driven `_ClientState`)
  es el drop-in directo de `_get_default()`. Evidencia: probes son funciones
  module-level sin parámetro client (`main_ambito_financiero.py:131,219,301`;
  `main_iol.py:219,336`; `main_matriz.py:453`); async batched en un solo
  `asyncio.run(_async_main(...))`.

- **D-02: sync `Client` y async `AsyncClient` son instancias SEPARADAS — no hay una sola
  instancia que abarque ambas superficies.** El `AsyncClient` se crea y `aclose()`ea
  dentro de `_async_main()` (una por `asyncio.run`); el sync `Client` vive en `main()`.
  El gate "≤2 constructores (1 sync + 1 async)" acomoda explícitamente este split.
  NUNCA compartir el `httpx.Client` sync hacia código async (violación event-loop, ver
  CLAUDE.md anti-patterns). Drivers ya hacen `await aio.aclose()` al final del batch
  async (`main_ambito_financiero.py:678`; `main_matriz.py:2046`).

### INT-01 `_state` read migration

- **D-03: Cada sitio `_get_default()._state.<attr>` → `client._state.<attr>` (o
  `aclient._state.<attr>` async), sustitución mecánica 1:1.** Counts por driver:
  ámbito ~8 código (+ 2 docstring que se DEJAN intactos), iol 17, higyrus ~19, matriz 6
  (todos async). El único write-site `main_iol.py:1289` (`token_expires_at = 0.0`,
  forced-refresh test) → `client._state.token_expires_at = 0.0` — debe escribir sobre la
  MISMA instancia que las probes siguientes leen, o el test de forced-refresh se silencia
  (no-op) y una regresión real pasa inadvertida. Occurrences en docstrings
  (`main_ambito_financiero.py:561,563`) NO se reescriben (es prosa operator-facing).

### AST-guard test (CRITICAL merge gate)

- **D-04: `test_main_<pkg>_uses_single_client_instance` vive en `verification/`,
  modelado sobre `verification/test_main_drivers_bare_except.py`** (parametrizado,
  `ast.parse((_REPO_ROOT / driver).read_text())` + `ast.walk`). Cuenta nodos `ast.Call`
  cuyo `func` construye `Client` / `AsyncClient` y asserta **≤2 por driver**. Las
  llamadas `with_options(...)` son method-calls (`ast.Attribute`), NO se cuentan → views
  quedan ilimitados.

- **D-05: El walker DEBE matchear AMBOS estilos de constructor: bare `ast.Name(id="Client")`
  y module-qualified `ast.Attribute(attr="Client")` (`iol_client.Client(...)`).** El plan
  DEBE pinear el estilo de import exacto que cada driver usa (clase importada bare vs
  módulo-cualificada) para que walker y driver code coincidan — si el walker solo matchea
  `Name` y el driver usa `Attribute`, el gate cuenta cero constructores y pasa
  vacuamente (false-green que anula el merge gate). Considerar scoping por `main()` /
  `_async_main()` si algún helper también construye.

### Probe-name / finding-title stability (CRITICAL merge gate)

- **D-06: La estabilidad de títulos se preserva NO tocando los literales `title=` / `fid=`
  / `class_=` / probe-name args de `append_finding(...)`** — la migración cambia solo el
  CÓMO se obtiene el client (la expresión target de la llamada y la fuente del valor
  `base_url=`), nunca los string literals. `append_finding` deduplica content-addressed
  por título (`verification/findings.py:192,595`) → títulos idénticos producen auto-zones
  byte-idénticas.

- **D-07: Verificación del gate vía `git diff baseline..HEAD` ESTÁTICO sobre los archivos
  findings committeados, scoped a líneas title/fid/probe-name — SIN re-correr probes
  live.** Los bytes `actual=` / `diff=` de findings OPEN son inherentemente no
  determinísticos (varían con datos live); un check "re-run live + diff completo" fallaría
  criterion #2 por volatilidad de datos no relacionada al refactor. La re-verificación
  live full se difiere a Phase 17 (LIVE-03).
  [Decisión del usuario: "Static diff, title/fid-scoped".]

### LOC-drop criterion #5 — attestation / measure-only

- **D-08: Criterion #5 (-30% LOC) se trata como paso de MEDICIÓN / ATESTACIÓN, no de
  reducción física de LOC de librería.** Se registra el LOC actual de librería
  (iol `client.py`+`aio.py`; matriz `client.py`) vs el baseline anchor, se documenta el
  residual gap, y se confirma que el baseline de 907 tests se mantiene. La reducción real
  de LOC de librería era el trabajo de Phase 16 codegen — **DROPPED** (Phase 12 NO-GO);
  el cierre real se difiere a v1.3. Los shims de back-compat QUEDAN intactos.
  [Decisión del usuario: "Attestation / measure-only". La alternativa — borrar shims para
  alcanzar -30% — violaría la decisión locked "shims STAY / 100% back-compat" y rompería
  consumidores externos.]

- **D-09: El plan DEBE pinear el baseline anchor exacto antes de computar el delta.** El
  ROADMAP criterion #5 dice "vs v1.0 baseline", pero los residuales conocidos (iol -5.1%,
  matriz -20%) se midieron contra el baseline de extracción Phase 6/7 (ver
  `07-03-SUMMARY.md`: iol client.py 522→490, aio.py 476→457). LOC actual medido:
  iol client.py=756, aio.py=755 (agregado 1511); matriz client.py=922. El planner
  resuelve cuál anchor aplica (v1.0 pre-REFAC tag vs Phase 6 baseline) y documenta el
  delta resultante — único ítem de medición que requiere recuperar dato histórico interno.

### Ergonomics scope

- **D-10: Migración mínima — bare `Client()` / `AsyncClient()` (env-driven), sin
  showcasing de `with_options()` / `from_env()`.** Phase 15 queda como refactor mecánico
  ajustado; los views `with_options` no agregan constructor calls de todos modos, así que
  pueden usarse si surge necesidad puntual, pero no es objetivo exhibir las ergonomics de
  Phase 13. [Decisión del usuario: "Minimal construction only".]

### Orden de migración

- **D-11: Serial per-package en orden ámbito → iol → higyrus → matriz** (menor blast
  radius primero; mismo orden que ROADMAP criterion #3 y precedente v1.0). Cada driver
  pasa su LIVE smoke per-package existente al final de su migración (operator-driven, NO
  el gate milestone-final de Phase 17).

### Claude's Discretion

- Forma exacta del helper threading (parámetro posicional vs keyword en las signatures de
  probe) — a criterio del planner, siempre que el AST-gate (≤2 constructores) se satisfaga
  verdaderamente.
- Si el AST-walker necesita scoping a nivel `FunctionDef` de `main()`/`_async_main()` vs
  whole-file — depende de si helpers construyen instancias; el planner decide tras
  inspeccionar.

### Folded Todos

Ninguno. El único todo matcheado (`spike-codegen-libcst-v1.3.md`, score 0.6) pertenece al
spike libcst de v1.3 — fuera de scope de driver migration. Ver `<deferred>`.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — Phase 15 success criteria (5 ítems, 2 CRITICAL merge gates)
- Drivers a migrar: `main_ambito_financiero.py`, `main_iol.py`, `main_higyrus.py`,
  `main_matriz.py` (raíz del repo)
- AST-test precedent: `verification/test_main_drivers_bare_except.py` (único AST-walker del
  repo; `_REPO_ROOT`, parametrizado, `ast.walk`)
- Library `Client`/`AsyncClient` surface:
  - `packages/iol-client/src/iol_client/client.py:110,161,264,565` + `aio.py:70,258,572`
  - `packages/matriz-client/src/matriz_client/client.py:113,681` + `aio.py:136,710`
  - `packages/ambito-financiero-client/src/ambito_financiero_client/client.py:77,161,254`
- Findings stability mechanics: `verification/findings.py:192,595` (append-only,
  content-addressed dedupe por título) + `.planning/verification/*-findings.md`
- LOC baseline anchor (D-09): `.planning/milestones/v1.1-phases/07-core-py-extraction-sync-async-logic-dedup/07-03-SUMMARY.md`
  (iol client.py 522→490, aio.py 476→457) + git tags v1.0 archivados
- CLAUDE.md ARCHITECTURE §6 (PEP 562 shim + back-compat delegators que QUEDAN) +
  anti-patterns (no compartir httpx.Client sync hacia async)
- INT-01 idiom write-site precedent: `main_iol.py:1289`
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **AST-walker precedent** `verification/test_main_drivers_bare_except.py` — copiar idioma
  (`_REPO_ROOT`, `@pytest.mark.parametrize("driver", [...])`, `ast.parse` + `ast.walk`)
  para los 4 nuevos `test_main_<pkg>_uses_single_client_instance`.
- **Library `Client`/`AsyncClient` constructors** ya existen y toman solo kwargs →
  `Client()` / `AsyncClient()` sin args es drop-in directo de `_get_default()`.
- **`with_options()` views** (`client.py:264`) disponibles pero no requeridos (D-10).
- **`append_finding` content-addressed dedupe** (`findings.py`) — preserva auto-zones
  byte-idénticas si los títulos no cambian.

### Established Patterns

- Probes son funciones module-level `def probe_*` sin parámetro client; `main()` las llama
  posicionalmente y colecta `ProbeResult`.
- Async siempre batched en un único `asyncio.run(_async_main(...))` por driver → el
  `AsyncClient` vive naturalmente para esa coroutine.
- Serial per-package (ámbito → iol → higyrus → matriz), menor blast radius primero.
- INT-01 idiom: `_get_default()._state.<attr>` reads (module namespace write shadowing
  PEP 562 `__getattr__`).

### Integration Points

- Driver migration NO toca la librería — solo `main_*.py` + tests en `verification/`.
- El gate de probe-name stability se ancla al baseline LIVE-01 `71bf201` (v1.1).
- 907-test baseline debe preservarse (`pytest` ≥907 passing) cross-milestone.
- matriz TokenStore 3-way + IOL OAuth refresh: construir múltiples Clients arriesga
  corrupción de TokenStore / churn de OAuth → de ahí el gate ≤2 constructores.
</code_context>

<specifics>
## Specific Ideas

- Forced-refresh write-site `main_iol.py:1289` (`token_expires_at = 0.0`) debe operar
  sobre la instancia threadeada exacta — caso de prueba sensible.
- Gate de stability via diff estático sobre findings committeados, scoped a title/fid —
  evita false-fails por volatilidad de datos live (D-07).
</specifics>

<deferred>
## Deferred Ideas

- Reducción física de LOC de librería a -30% — diferida a v1.3 (mecanismo = codegen,
  Phase 16 DROPPED por Phase 12 NO-GO). Phase 15 solo mide/atesta (D-08).
- Re-verificación live full × 4 packages — es Phase 17 (LIVE-03), no esta phase.
- Showcasing de `with_options()` / `from_env()` ergonomics en drivers — no objetivo (D-10).

### Reviewed Todos (not folded)

- `spike-codegen-libcst-v1.3.md` (score 0.6, área codegen) — pertenece al spike libcst de
  v1.3 para REFAC-06 carry-forward, NO a driver migration. Permanece en
  `.planning/todos/pending/` para v1.3.
</deferred>
