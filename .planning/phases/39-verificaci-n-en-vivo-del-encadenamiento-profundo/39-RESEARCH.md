# Phase 39: Verificación en vivo del encadenamiento profundo - Research

**Researched:** 2026-08-29
**Domain:** Live-API verification harness (Python 3.12 / httpx / uv monorepo) — driver extension, census accounting, safety-gate policy
**Confidence:** HIGH (everything material was verified by reading HEAD source, running the test suite, and probing DNS in this session)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Clasificación PASS/SKIPPED de los dos bloqueos heredados**

- **D-01:** `main_verify.py` clasifica hoy mal ambos bloqueos heredados, y esta fase debe corregir la clasificación como parte de cumplir SC-1 literalmente ("PASS o SKIPPED con causa medida y destino nombrado, nunca como cero"):
  - **matriz** hoy sale `FAILED` — el `sys.exit(1)` de D-MATZ-33 (`main_matriz.py` ~línea 2558-2566) no matchea el regex `_ENV_SKIP` (`^SKIPPED \S.*:`) de `main_verify.py`. Con D-02 (abajo), matriz debería dejar de necesitar esta rama en la práctica (corre PASS), pero la clasificación igual debe quedar correcta para el caso general (si el sandbox bbsa dejara de responder, por ejemplo).
  - **higyrus** hoy sale `RAN` (falso limpio) — el `ConnectError` de DNS es absorbido por `_RESIDUAL_PROBE_EXCEPTIONS` dentro de `probe_login_sync` (`main_higyrus.py:144-151`) como `FINDING`, no como `SKIPPED`, y el driver sigue con exit 0. Esta fase debe distinguir "vendor inalcanzable" (DNS) de una divergencia real y reportar `SKIPPED — LIVE-HIGY-33` si el DNS sigue sin resolver cuando se corra.

**D-MATZ-33 — ampliar el allowlist a bbsa.matrizoms.com.ar (decisión del operador)**

- **D-02:** El assert D-MATZ-33 (`main_matriz.py`, hostname check) se **amplía** en esta fase para aceptar explícitamente `bbsa.matrizoms.com.ar` además de `remarkets`, vía un allowlist explícito de hosts conocidos-seguros — **no** un substring genérico ni un debilitamiento del check. Ejemplo de forma (implementación exacta es de discreción del planner/executor):
  ```python
  if not ("remarkets" in base or base == "https://api.bbsa.matrizoms.com.ar"):
      sys.exit(1)  # D-MATZ-33: allowlist explícito, no substring genérico
  ```
  **Decisión explícita del operador** (checkpoint, no auto-resuelta) — el sandbox bbsa fue confirmado por el operador el 2026-08-29 como real, seguro, no-remarkets, no-prod, con `login()` + `get_segments()` ya verificados funcionando ahí (ver memoria `project_matriz_bbsa_sandbox.md`). Esto **desbloquea matriz para correr en vivo esta fase**, resolviendo la mitad de `LIVE-MATZ-33` que era resoluble desde dentro del proyecto (la otra mitad — la prohibición P-05 de rodear la política para hosts *no* confirmados — sigue vigente sin cambios). El cambio debe documentarse en el código (comentario) y en el reporte de esta fase como una decisión de seguridad explícita, siguiendo el mismo patrón de gate humano que D-08/D-18 en fases anteriores — no un ajuste silencioso.

**Cadenas profundas a agregar por driver (SC-1)**

- **D-03 (iol — gap principal):** `main_iol.py` no referencia `.puntas` en ningún lugar hoy. Esta fase agrega el ejercicio de `titulo.puntas.precioCompra` y/o `cotizacion.puntas[0].precioCompra` **dentro de los probes existentes** que ya obtienen `Cotizacion`/`Titulo` (p. ej. `probe_get_quote_sync`/`_async`, `probe_get_instruments_by_type_sync`/`_async`) — no como un probe nuevo, siguiendo la convención "una llamada HTTP por concepto de probe" que ya sigue el resto del driver. Debe correr en **ambas** superficies (sync + async).
- **D-04 (higyrus — cadena tipada real):** Los probes actuales de higyrus trabajan mayormente sobre dicts crudos (`_raw_request_sync`/`_async`). Esta fase suma **al menos una cadena real sobre el wrapper tipado** — ej. `posicion.parking[...]` (`Posicion.parking: list[Parking]`, `models.py:316`) o una cadena equivalente sobre `Cuenta.domicilios`/`.personasRelacionadas` — en simetría con iol/matriz/market-data, todos ejercitando al menos una cadena `.modelo.campo` real contra la API en vivo, no sólo la ejecución silenciosa de la función tipada.
- **D-05 (matriz):** Con D-02 desbloqueando el sandbox, matriz debe ejercitar `snapshot.last.price` / `.bids` / `.offers` / `.settlement` / `.close` / `.open_interest` (los 6 alias de Phase 37) contra el sandbox bbsa real, en sync y async donde aplique — matriz no tiene superficie async nativa (`matriz_client` no tiene `aio.py`, sólo REST sync + `ws_client` en thread daemon), así que "ambas superficies" para matriz se satisface con REST + WS, no con un `aio.py` inexistente.
- **D-06 (ambito — sin cadena, declarado por diseño):** `ambito_financiero_client.models` no declara ninguna clase (`__all__: list[str] = []`, decisión deliberada de Phase 29/31). Esta fase **no debe inventar un modelo** para ambito sólo para tener algo que encadenar — eso repetiría exactamente el anti-patrón que Phase 37 SC-1 prohibió para matriz ("modelo inventado presentado como observado"). El cumplimiento de SC-1 para ambito se satisface **declarando la ausencia medida** (como hizo `38-CENSUS.md` con higyrus/ámbito/wallets) — el driver de ambito sigue ejercitando sus endpoints reales (que ya existen), pero sin pretender una cadena de modelo que el paquete no tiene.
- **D-07 (market-data — fuera de alcance):** No se toca `main_market_data.py` en esta fase — ya cumple su parte desde Phase 36 (SC-5, `.market_data.last.price` etc. ya ejercitados en `main_market_data.py`).

**Fix in-cycle de divergencias CONFIRMED (SC-3)**

- **D-08:** Toda divergencia CONFIRMED encontrada durante esta fase se corrige **in-cycle**: espejo sync/async del fix + un test de regresión **mockeado** que la pinea (mismo patrón que todas las fases previas de v1.7 — 36/37/38). No se difiere ninguna divergencia real a menos que sea explícitamente aprobada por el operador con destino nombrado (mismo patrón que `LIVE-HIGY-33`/`LIVE-MATZ-33`).

**`verify_cycle_closure` — PASS no-vacuo (SC-3)**

- **D-09:** `verify_cycle_closure()` (`verification/cycle_report.py:123`) hoy devuelve `(True, [])` tanto si no hay findings reales como si el archivo de findings ni existe — exactamente el "PASS vacuo" que SC-3 prohíbe explícitamente. Esta fase necesita una verificación adicional (wrapper o extensión de la función — decisión de implementación, no de producto) que confirme **evidencia positiva** de que el driver corrió contra la API en vivo (p. ej. conteo de probes ejecutados > 0, o un timestamp de corrida reciente) antes de aceptar el PASS, para cada paquete medido.

**Contraste del censo contra Fase 33 / 29-SIZING (SC-4)**

- **D-10:** El contraste de esta corrida contra `33-CENSUS.md` (`.planning/milestones/v1.6-phases/33-verificaci-n-en-vivo-en-modo-estricto-fixes/33-CENSUS.md`) y `29-SIZING.md` (`.planning/milestones/v1.6-phases/29-decoder-observable/29-SIZING.md`) debe usar la **misma unidad** que esos artefactos ya establecieron: triples distintos `(slug, model, field_path, kind)` de `DivergenceHandler.seen` (`verification/divergences.py:112-196`) — **no** el conteo `FINDING=N` del SUMMARY del driver ni el conteo crudo de entradas del findings-file. `33-CENSUS.md` ya documentó un factor ~2× de duplicación por superficie (`surface-in-title-write-new` escribe un finding por superficie por triple) que reaparecería si se usa la unidad equivocada, y documentó que el piso de `29-SIZING.md` cuenta registros sumados por archivo (una misma triple en dos archivos del corpus cuenta dos veces) mientras `handler.seen` cuenta triples distintas (cuenta una vez) — hay que reconciliar sobre esa diferencia, no ignorarla.
- **D-11:** El reporte de esta fase debe declarar explícitamente, por separado, cuántas divergencias de la Fase 33 desaparecieron por **colapso de política Null Object** (ya no se registran porque Phase 35 las volvió silenciosas) frente a cuántas desaparecieron por **corrección real** (fix efectivo en Phases 36-38 o en esta misma fase) — esto es SC-4 literal: "para que la baja de números no pueda leerse como un falso limpio". La contabilidad debe cruzar con `35-RETIRED-TRIPLES.md` (el ledger que Phase 38 D-12 dejó pendiente de actualizar para esta fase — ver Canonical References).

**Casos límite a probar (SC-2)**

- **D-12:** Para cada paquete que efectivamente corra, la corrida debe incluir intencionalmente (no sólo esperar que ocurran) los casos límite que sólo produce la API en vivo: mercado cerrado, fila no-data, campo ausente, respuesta 204/vacía — ninguna cadena debe lanzar `AttributeError` ni `TypeError` en ninguno de esos casos. Para matriz esto implica correr **dentro de una ventana de sesión de trading ARG** si se quiere distinguir "mercado cerrado" (null legítimo) de "campo mal modelado" — precedente P-12 de Phase 33.

### Claude's Discretion

- Forma exacta del wrapper/extensión para el PASS no-vacuo de `verify_cycle_closure` (D-09) — decisión de implementación.
- Redacción exacta del reporte de contraste Fase 33 vs Fase 39 (D-10/D-11) — sigue el formato de censo ya validado (`35-RETIRED-TRIPLES.md`, `33-CENSUS.md`, `38-CENSUS.md`), layout libre.
- Probe exacto elegido en higyrus para la cadena tipada de D-04 (`Posicion.parking` vs `Cuenta.domicilios` vs otro) — cualquiera que ejercite una cadena `.modelo.campo` real basta.
- Nombre y ubicación exacta del artefacto de censo de esta fase (`39-CENSUS.md` o similar).

### Deferred Ideas (OUT OF SCOPE)

- Reparar `verification/` (pytest harness roto, HARN-VERIF-01) — deuda pre-existente, no tocada por esta fase (los drivers `main_*.py` son un sistema distinto de `verification/`'s pytest suite rota).
- Resolver S-3/S-4/S-5 de matriz (`33-CENSUS.md`) más allá de lo que el censo de esta fase mida naturalmente al correr — no es un objetivo explícito de LIVE-NOBJ-01, pero puede resolverse como efecto colateral de D-02/D-05 si el censo lo permite.
- Censo de valores RESPONSE Literal de matriz (`33-LITERALS.md`, 7 campos) — mismo bloqueo histórico, no en alcance explícito de esta fase salvo que surja naturalmente.
- Publicación/versión/changelog de los paquetes que cambiaron — Phase 40 (PUB-NOBJ-01).

### ⚠ Researcher note on D-05 (verified contradiction, planner must reconcile)

D-05's parenthetical premise — *"`matriz_client` no tiene `aio.py`, sólo REST sync + `ws_client` en thread daemon"* — is **false at HEAD**. `packages/matriz-client/src/matriz_client/aio.py` exists with a complete `AsyncClient` (including `get_market_data`), and `main_matriz.py` already runs ~19 `surface="async"` probes via `_async_main()` while importing `ws_client` **zero** times. The *decision* (exercise the 6 aliases on both surfaces) is unaffected and locked; only its stated justification is stale. The planner should read "ambas superficies" for matriz as **`client.py` + `aio.py`**, exactly as for iol and higyrus. See `## State of the Art` for the evidence.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIVE-NOBJ-01 | Los drivers `main_*.py` ejercitan el encadenamiento profundo (sync + async) contra las APIs en vivo en los paquetes verificables; toda divergencia detectada se corrige in-cycle con espejo sync/async y regresión mockeada (`REQUIREMENTS.md:37`) | **SC-1 (cadena real, ambas superficies):** Pattern 1 (AST deep-chain lock, verbatim precedent from `test_main_market_data_deep_chain.py`), Pattern 2 (typed chain with no second HTTP call, for higyrus), Code Examples for iol/matriz insertion sites with exact line numbers. **SC-1 (PASS/SKIPPED classification):** Pitfalls 2, 3, 4 + the D-01 code example (stdout, colon shape, no finding on the unreachable path). **SC-2 (no AttributeError/TypeError on live edges):** Pitfall 9 (existing `LA.date` staleness discriminator), Pitfall 10 (`try`-body containment enforced by AST), Validation Architecture edge-case test rows. **SC-3 (in-cycle fix + non-vacuous closure):** Pattern 3 (harden at the probe layer; the market-data predicate is the *wrong* one for the three zero-finding packages) + Open Question 2 (coverage gap: 3 of 4 drivers never call `verify_cycle_closure`). **SC-4 (census contrast):** Pattern 4 (the census unit exists in-process but is never persisted — two seams offered), Pitfall 7 (the records-vs-triples column trap, matriz's absent `census_33`, the missing Phase 36/37 middle terms). **Cross-cutting:** Runtime State Inventory (git-committed ledgers mutated by running; the matriz remarkets-vs-bbsa snapshot venue cross; the `ci.yml` allowlist that makes new guards inert). **Security:** the D-02 gate widening is independently mitigated by `mutation_gate.py`'s untouched exact-hostname remarkets check. |

</phase_requirements>

## Summary

This is **not** a library-selection phase. Zero new dependencies, zero new frameworks. Every capability Phase 39 needs already ships in this repo: the divergence handler, the schema-snapshot machinery, the findings ledger, the probe-context decorator, and a fully-worked precedent for every artifact the phase must produce. The research question that actually matters is *"what is the current shape of the code CONTEXT.md points at, and what has drifted since CONTEXT.md was written?"* — and the answer is: **one CONTEXT decision rests on a false premise, and four unstated blockers will bite the executor if the planner does not sequence around them.**

The single most important finding: **`matriz_client` HAS a full native async surface (`aio.py` with `AsyncClient.get_market_data`), and `main_matriz.py` already runs ~19 async probes including `probe_get_market_data_async`.** CONTEXT.md D-05 (and `CLAUDE.md`'s architecture section, and `PROJECT.md`) all state matriz has no `aio.py` and that "both surfaces" must be satisfied by REST+WS. That is stale by several phases. D-05 is therefore *easier* than CONTEXT assumes (real sync + real async, mirroring iol/higyrus) and the WS path is a red herring — `main_matriz.py` does not import `ws_client` at all.

The second most important finding: **matriz's 8 committed schema snapshots were captured against `api.remarkets.primary.com.ar` on 2026-06-10, and D-02 points the driver at `api.bbsa.matrizoms.com.ar`.** The snapshot file key is the function name, not the base URL, so the first bbsa run will diff bbsa payload shapes against remarkets baselines and emit one `SHAPE` drift finding per structural difference between two *different venues*. Those are venue-comparison artifacts, not client-vs-API divergences, and if they are not segregated before the run they will corrupt exactly the census that SC-4 exists to make honest.

**Primary recommendation:** Sequence the phase as (Wave 0) harness corrections that must land *before* any live run — D-01 classification, D-02 allowlist, D-09 non-vacuous closure, matriz snapshot venue segregation, and a triple-dump mechanism; then (Wave 1) the per-driver chain additions D-03/D-04/D-05/D-06 plus their AST locks wired into `ci.yml`; then (Wave 2) the live runs, in-cycle fixes (D-08), and the census artifact (D-10/D-11). Running live before Wave 0 lands writes garbage into git-committed ledgers that then have to be unwound.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| PASS/SKIPPED/FAILED classification (D-01) | Harness runner (`main_verify.py`) + each driver's exit path | — | The runner classifies by scanning child **stdout** for a line the child must emit; both halves must change together |
| D-MATZ-33 hostname allowlist (D-02) | Driver (`main_matriz.py` `main()`) | — | It is a driver-level anti-prod guard; the *mutation* gate lives separately in `verification/mutation_gate.py` and must NOT be touched |
| Deep-chain exercise (D-03/D-04/D-05) | Driver probe bodies | Package `models.py` (already delivered by 36/37/38) | Phases 36-38 shipped the types; this phase only *spends* them |
| Declared absence for ámbito (D-06) | Census artifact (markdown) | — | Nothing to run; the deliverable is a measured statement, not code |
| In-cycle divergence fix (D-08) | Package `client.py` + `aio.py` (mirrored) | `packages/<pkg>/tests/` (mocked regression) | Regression tests must live under `packages/`, which CI actually runs |
| Non-vacuous cycle closure (D-09) | Driver probe (`probe_cycle_closure`) | `verification/cycle_report.py` | market-data already hardened this at the *probe* layer, not the library layer — follow that seam |
| Census unit extraction (D-10/D-11) | `DivergenceHandler.seen` in-process, or SHAPE-title parse of the findings file | Census markdown artifact | The unit exists in memory but is never persisted; this is a real gap |
| Edge-case forcing (D-12) | Driver probe bodies | — | Market-closed / no-data / 204 are all driver-side decisions about *what to call and when* |

## Runtime State Inventory

> Phase 39 is not a rename, but it **mutates git-committed ledgers and write-once baselines as a side effect of running**. That is the same class of hazard, so the inventory applies.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data (git-committed, driver-mutated)** | `.planning/verification/<pkg>-findings.md` (5 files). Every driver run calls `append_finding`, which **writes to the working tree**. Current statuses: ámbito 1 EXPECTED; higyrus 1 EXPECTED + 1 NO-FIX; iol 1 FIXED + **1 OPEN (F-01 `missing simbolo` in `get_quote`)**; matriz 1 FIXED + 9 NO-FIX + 2 EXPECTED; market-data 88 FIXED + 23 EXPECTED + 32 NO-FIX. | Plan must state, per package, which new findings are expected and who dispositions them. **A DNS-failed higyrus run today writes an `AUTH OPEN` finding** (`main_higyrus.py:639`/`:703`) — which would redden the existing gate `verification/test_cycle_closure_phase33.py` (`assert "OPEN" not in statuses` for higyrus). D-01's SKIPPED interception must happen **before** `append_finding`, not after. |
| **Write-once baselines** | `.planning/verification/schemas/matriz-client/*.json` — 8 files, all `base_url: https://api.remarkets.primary.com.ar`, `captured_at: 2026-06-10`. `_write_or_check_schema` (`main_matriz.py:360-410`) keys the file by **`func_name` only**; `base_url` is recorded in the envelope but is not part of the key, and D-25 forbids overwrite-on-drift. | **Decide before the run.** Options: (a) key snapshot files by venue (`get-market-data.bbsa.json`), (b) capture a fresh bbsa baseline in a separate dir, (c) accept the drift findings but classify them `EXPECTED` with a venue-cross rationale. Doing nothing produces up to 8 bogus `SHAPE OPEN` findings that then pollute the SC-4 census. |
| **OS-registered state** | None. Drivers are one-shot `uv run` processes. Verified: no launchd/cron/pm2 registration in repo. | None |
| **Secrets / env vars** | Per-package `.env` present for higyrus, iol, market-data, matriz (no root `.env`, none committed). Verified key names only, never values. `PRIMARY_BASE_URL` = `https://api.bbsa.matrizoms.com.ar/` (trailing slash); `_default_base_url()` (`matriz_client/_state.py:41`) and `Client.__init__` (`client.py:143`) both `.rstrip("/")`, so `client._state.base_url == "https://api.bbsa.matrizoms.com.ar"` — **D-02's exact-equality allowlist works as written**. | None. Do not add or rename env vars. |
| **Build artifacts** | None relevant — no codegen, no egg-info drift in scope. | None |
| **CI wiring (the silent one)** | `.github/workflows/ci.yml:79-84` runs a **hand-maintained explicit allowlist** of 4 `verification/` test files. The `test` job passes an explicit path that overrides `testpaths`, so **`verification/` as a directory never runs in CI**. The file's own comment records that Phase 36's brand-new deep-chain lock shipped **inert** for exactly this reason (WR-01). | Every AST lock this phase adds under `verification/` MUST be appended to that list in the same commit, or it is decoration. |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | all runs | ✓ | 0.11.3 | — |
| CPython 3.12 (workspace venv) | all runs | ✓ | 3.12.13 (uv-managed) | — |
| `pytest` + `pytest-httpx` + `pytest-asyncio` | regression tests, AST locks | ✓ | collects 431 tests under `verification/` with **0 collection errors** | — |
| IOL live API (`api.invertironline.com`) | D-03 live run | ✓ DNS resolves | — | — |
| matriz bbsa sandbox (`api.bbsa.matrizoms.com.ar`) | D-05 live run | ✓ DNS resolves | — | — |
| Higyrus vendor host (`cliente.aunesa.com`) | D-04 live run | ✗ **`gaierror` — does not resolve** | — | **No fallback.** `LIVE-HIGY-33` is still live as of this session. |
| ámbito public site | D-06 smoke | ✓ (no auth by design) | — | — |
| ARG trading-session window | D-12 matriz market-closed discrimination | ⚠️ time-dependent | — | Run out-of-hours and classify `NO-DATA` explicitly (`main_matriz.py:1022-1045` already has the `LA.date` staleness guard) |

**Missing dependencies with no fallback:**
- Higyrus DNS. **This is measured, not assumed** — probed in this session. D-04's live half cannot execute; the plan must produce `SKIPPED higyrus-client: vendor unreachable (DNS) — LIVE-HIGY-33` and still land the *code* half of D-04 (the typed chain + its AST lock + a mocked regression), so the phase delivers a falsifiable artifact rather than a deferral.

**Pre-existing red/hanging tests (HARN-VERIF-01, out of scope but load-bearing for sequencing):** measured per-file this session —
- `verification/test_cycle_closure_phase33.py` — **2 failed**, cause is a *stale path*: it reads `.planning/phases/33-.../33-CENSUS.md`, which was archived to `.planning/milestones/v1.6-phases/33-.../33-CENSUS.md`. One-line fix; this file is D-09's closest precedent so the planner will touch it anyway.
- `verification/test_main_matriz_login_fail_uniformity.py` — 2 failed, 2 errors.
- `verification/test_matriz_sweep_snapshot.py` — 17 failed, 3 passed, 17 errors (`pytest_httpx`: "mocked but not requested" — the fixture `configure()`s the module-level default client while the probes now take an explicit `Client` instance; stale vs. the instance refactor). **Consequence: the natural regression net for matriz probe edits is already red**, so D-05 cannot lean on it.
- `verification/test_retry_after_cap.py`, `verification/test_with_options.py` — exceed 45s (real backoff sleeps). Not failures, but budget the executor's time.
- Everything else (40 files) green.

## Standard Stack

### Core (all already in-repo — nothing to install)
| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| `DivergenceHandler` | `verification/divergences.py:112-188` | Logging handler translating the frozen 6-key decode record into a `SHAPE` finding; `.seen` is the census unit | The **only** unit directly comparable to `29-SIZING.md` without translation; wired to all 5 drivers since Phase 29/33 [VERIFIED: source read] |
| `probe_context` / `endpoint_scope` | `verification/divergences.py:230-304` | ContextVar binding of endpoint+surface around a probe; also the `decode_error` → `ProbeResult` seam | Every existing probe uses it; a new probe without it produces mis-attributed findings |
| `append_finding` | `verification/findings.py:583` | Ledger writer; `idempotent_by_title=True` gives content-addressed cross-run dedupe | Human-promoted statuses (CONFIRMED/FIXED/EXPECTED/NO-FIX) are preserved automatically |
| `verify_cycle_closure` | `verification/cycle_report.py:123-176` | Structural CONFIRMED/FIXED → regression-test linkage check | The function D-09 must harden **around**, not inside (see Pattern 3) |
| `require_env` | `verification/env_gate.py:32-41` | Prints the verbatim `SKIPPED <pkg>: missing …` line the runner matches | Checks env-var **presence only** — never reachability. This is precisely why higyrus reports `RAN` today |
| `mutating_allowed()` | `verification/mutation_gate.py:107-131` | Double gate: `VERIFY_MUTATING=1` **AND** exact hostname `api.remarkets.primary.com.ar` | **Security-load-bearing for D-02** — see Security Domain |
| `schema_of` / `_write_or_check_schema` | `verification/schema.py:27`, `main_matriz.py:360` | Keys-and-types-only structural snapshot, D-25 no-overwrite-on-drift | PII-free by construction; the SHAPE-diff infra D-12 reuses |
| `SafeModel.from_api` | e.g. `higyrus_client/models.py:60-65` | Routes through `_decode.walk_model(..., sink=current_sink())` | **Key enabler for D-04** — see Pattern 2 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `handler.seen` as census unit | Driver `SUMMARY FINDING=N`, or raw findings-file block count | **Forbidden by D-10 and by `33-CENSUS.md:19-30`.** `FINDING=N` counts probes, not divergences; the file count carries a ~2× per-surface duplication because surface is embedded in the dedupe title |
| Editing `verify_cycle_closure` itself | Wrapping it at the probe layer | `main_market_data.py:3375-3412` already hardens at the probe layer and 3 tests pin the library's current `(True, [])` contract. Editing the library reddens `test_cycle_closure_market_data.py` + `test_cycle_closure_phase33.py` for no gain |
| A new `probe_puntas_*` in iol | Extending existing quote/instrument probes | D-03 locks the latter; also the driver's "one HTTP call per probe concept" convention (`main_iol.py:641` WR-03) |
| matriz "both surfaces" = REST + WS | matriz "both surfaces" = `client.py` + `aio.py` | **The WS premise is false at HEAD.** `matriz_client/aio.py` exists with a full `AsyncClient`; `main_matriz.py` has ~19 `surface="async"` probes and imports `ws_client` **zero** times |

**Installation:** none. `uv sync --all-packages --all-extras --dev --frozen` is the only setup step.

## Package Legitimacy Audit

**Not applicable — this phase installs zero external packages.** Verified: no new third-party dependency is implied by any of D-01…D-12; every capability is satisfied by stdlib (`ast`, `json`, `re`, `contextvars`, `logging`) plus packages already pinned in `uv.lock`. No `[SLOP]`, no `[SUS]`, nothing for the planner to gate.

If a plan ends up proposing a dependency, that is a signal the plan drifted from the phase — the correct response is to re-read this section, not to add the package.

## Architecture Patterns

### System Architecture Diagram

```
                      ┌──────────────────────────────────────────┐
                      │  main_verify.py  (aggregate runner)      │
                      │  for each of 6 (uv-package, script):     │
                      │    subprocess.run(uv run --package …)     │
                      │    scan child STDOUT for ^SKIPPED \S.*:  │──┐
                      │    else returncode!=0 → FAILED           │  │ D-01
                      │    else → RAN                            │  │ widens
                      └────────────────┬─────────────────────────┘  │ this
                                       │ (isolated process per pkg) │ decision
             ┌─────────────────────────┼─────────────────────────┐  │
             ▼                         ▼                         ▼  ▼
   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
   │  main_iol.py     │    │ main_higyrus.py  │    │ main_matriz.py   │  … + ámbito
   │                  │    │                  │    │                  │
   │ require_env ─────┼─┐  │ require_env ─────┼─┐  │ require_env      │
   │                  │ │  │                  │ │  │ D-MATZ-33 host   │◄── D-02
   │                  │ │  │  [DNS ConnectErr]│ │  │  gate → exit 1   │    allowlist
   │                  │ │  │   ↓ absorbed as  │ │  │  (stderr today)  │
   │                  │ │  │   AUTH FINDING   │◄┼──┼── D-01 must turn  │
   │                  │ │  │   exit 0 = "RAN" │ │  │   both into a     │
   │                  │ │  │                  │ │  │   stdout SKIPPED  │
   │ write_findings   │ │  │ write_findings   │ │  │  line             │
   │ _seed_fid_counter│ │  │ _seed_fid_counter│ │  │                  │
   │        │         │ │  │        │         │ │  │        │         │
   │   ┌────▼─────────────────────────────────────────────────▼────┐  │
   │   │  with divergence_capture((pkg_logger,), next_fid=…):      │  │
   │   │    logger NOTSET → INFO; handler attached                 │  │
   │   │                                                           │  │
   │   │   sync probes ──► client.<method>() ──► parser ──►        │  │
   │   │                     │                    walk_model       │  │
   │   │                     │                       │             │  │
   │   │   DEEP CHAIN  ◄─────┘   6-key record ◄──────┘             │  │
   │   │   (D-03/04/05                │                            │  │
   │   │    add here)                 ▼                            │  │
   │   │                        DivergenceHandler.emit             │  │
   │   │                          ├─► .seen.add(triple) ◄── CENSUS │  │
   │   │                          └─► append_finding(SHAPE, OPEN)  │  │
   │   │                                    │                      │  │
   │   │   asyncio.run(_async_main()) ──► same path, surface=async  │  │
   │   │                                                           │  │
   │   │   schema_snapshot probe ──► schema_of(raw) vs committed   │  │
   │   │                              baseline ──► SHAPE drift     │  │
   │   └───────────────────────────────────────────────────────────┘  │
   │        │                                                          │
   │        ▼ (matriz + market-data only)                              │
   │   probe_cycle_closure ──► verify_cycle_closure(pkg) ──┐           │
   │        (D-09 hardens the non-vacuity assertion here)  │           │
   │        │                                              ▼           │
   │        ▼                              .planning/verification/     │
   │   PROBE lines (safe_print, secrets redacted)          <pkg>-findings.md
   │   SUMMARY: PASS=… FINDING=… DIVERGENCES=len(handler.seen) HANDLER_ERRORS=…
   └───────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
                     39-CENSUS.md  ── set-difference vs 33-CENSUS.md
                                   ── minus 35-RETIRED-TRIPLES.md (policy)
                                   ── contrast vs 29-SIZING.md floor
```

### Recommended Project Structure (no new dirs)

```
main_verify.py                    # D-01: classification
main_iol.py                       # D-03: .puntas in existing quote/by_type probes
main_higyrus.py                   # D-01 (DNS→SKIPPED) + D-04 (typed chain)
main_matriz.py                    # D-02 (allowlist) + D-05 (6 aliases, sync+async)
main_ambito_financiero.py         # untouched (D-06 is a declaration, not code)
main_market_data.py               # UNTOUCHED (D-07)
verification/
  cycle_report.py                 # read-only; harden at the probe layer instead
  test_main_iol_deep_chain.py     # NEW AST lock  ─┐
  test_main_higyrus_deep_chain.py # NEW AST lock   ├─ MUST be added to ci.yml:80-84
  test_main_matriz_deep_chain.py  # NEW AST lock  ─┘
  test_cycle_closure_phase33.py   # stale _CENSUS path → repoint to milestones/
packages/<pkg>/tests/             # D-08 mocked regressions live HERE (CI runs these)
.planning/phases/39-…/39-CENSUS.md  # D-10/D-11 artifact
.github/workflows/ci.yml          # append new locks to the explicit allowlist
```

### Pattern 1: The deep-chain AST lock (the phase's non-vacuity mechanism)

**What:** A `verification/test_main_<pkg>_deep_chain.py` that `ast.parse`s the driver (never imports it — drivers have import-time `load_dotenv()` side effects) and asserts (a) the named probes exist, (b) each dereferences an alias reachable through the chain, (c) every dereference sits inside a `try` **body**, (d) a per-probe numeric floor, (e) every fetched collection is chained, not just `len()`-ed.

**When to use:** For all three of D-03, D-04, D-05.

**Why it is the right shape:** `probe(...) → ProbeResult(name, "PASS", f"rows={len(rows)}")` passes green while every link in the chain is broken — `len()` never touches the chain. The lock is what converts "the chain type-checks" into "the chain is exercised", and the per-probe floor plus the per-collection assertion are what stop a later refactor from thinning it back out.

**Example (verbatim precedent, all 6 tests green in this session):**
```python
# Source: verification/test_main_market_data_deep_chain.py (Phase 36 SC-5)
_ALIAS_NAMES = frozenset({"bids", "offers", "last", "settlement", "close", "open_interest"})

def _chain_reaches(node: ast.expr, attribute: str) -> bool:
    """True if the receiver chain under ``node`` passes through ``.<attribute>``."""
    current: ast.expr | None = node
    while current is not None:
        if isinstance(current, ast.Attribute):
            if current.attr == attribute:
                return True
            current = current.value
        elif isinstance(current, ast.Subscript):
            current = current.value
        elif isinstance(current, ast.Call):
            current = current.func
        else:
            return False
    return False

def _protected_node_ids(func) -> set[int]:
    """Ids of nodes reachable from the BODY of some ``try`` — except/else/finally excluded."""
    protected: set[int] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Try):
            for stmt in node.body:
                for descendant in ast.walk(stmt):
                    protected.add(id(descendant))
    return protected
```

Note the docstring of that file names Phase 39 explicitly: *"the driver that will run against develop in Phase 39 has to SPEND that shape, not merely count rows."* This phase is its intended consumer.

### Pattern 2: Typed chain without a second HTTP call (resolves the D-04 tension)

**What:** higyrus's probes fetch raw dicts via `_raw_request_sync` / `_raw_request_async` (`main_higyrus.py:335-377`) and stash them in `payloads[...]` for `field_type_map` and `schema_snapshot`. They never call the typed `client.get_posiciones()`. D-04 wants a real `.modelo.campo` chain, but the driver's convention is one HTTP call per probe concept.

**Resolution:** `SafeModel.from_api(payload)` (`higyrus_client/models.py:60-65`) routes through `_decode.walk_model(cls, payload, policy=POLICY, sink=current_sink())` — **the same walker, the same sink, the same emission path** the client's own parser uses (`_core.parse_get_posiciones_response` → `_parse_list_or_raise(resp, Posicion)`). So constructing `Posicion.from_api(row)` from the already-fetched raw payload:
- costs **zero** additional HTTP calls,
- emits the identical divergence records into `handler.seen`,
- and **inherits strict mode**: `_decode.STRICT_DECODE` is a `ContextVar` set inside `Client._request` (`higyrus_client/client.py:375`) with *deliberately no reset* (the decode happens after `_request` returns), so a `from_api` call made after the request in the same context still sees `strict_decode=True` during the P2 strict pass.

```python
# D-04 shape — no extra HTTP, real chain, strict-mode-correct
rows = _raw_request_sync(client, "GET", path, params=params)   # already there
payloads["get_posiciones"] = rows                               # already there
posiciones = [Posicion.from_api(r) for r in (rows or [])]       # NEW — same walker
n_parking = sum(len(p.parking) for p in posiciones)             # NEW — real chain
first_dias = posiciones[0].parking[0].diasParking if (posiciones and posiciones[0].parking) else None
```
`Posicion.parking: list[Parking]` is at `higyrus_client/models.py:316`. Alternatives named in D-04 also exist: `Cuenta.domicilios` / `.personasRelacionadas` (`:463-464`) — but those come off `get_listado_cuentas`, whose live behaviour is documented as returning `[]` (finding F-02, status NO-FIX, 3/3 consecutive runs). **`Posicion.parking` is the better pick**: `get_posiciones` returned 76 items in the same historical run.

### Pattern 3: Non-vacuous cycle closure, hardened at the probe layer (D-09)

**What:** `verify_cycle_closure(pkg)` returns `(True, [])` in three distinct situations — file absent (`cycle_report.py:142-143`), no CONFIRMED/FIXED finding, and genuinely-all-linked. Only the third is a real pass.

**The existing precedent:** `main_market_data.py:3375-3412` already wraps it:
```python
ok, missing = verify_cycle_closure(_PKG)
path = findings_path(_PKG)
text = path.read_text(encoding="utf-8") if path.exists() else ""
n_closed = len(_CLOSED_STATUS_RE.findall(text))
if ok and n_closed == 0:
    ok = False
    missing = ["<ningún finding CONFIRMED/FIXED: el cierre de ciclo sería vacuo>"]
```

**The trap:** that hardening asserts *findings exist*, which is the wrong criterion for three of this phase's four packages. Measured counts of CONFIRMED/FIXED at HEAD: ámbito **0**, higyrus **0**, iol **1**, matriz **1**. Copying the market-data predicate verbatim would turn ámbito and higyrus **FAIL** for having nothing wrong with them.

**The right criterion is the one CONTEXT D-09 states and `test_cycle_closure_phase33.py` already models:** positive evidence that *the driver ran*, not evidence that findings exist. The phase-33 test does this for ámbito by asserting the verbatim `SUMMARY: PASS=6 …` line (a **non-zero probe count** beside the two zeros) appears in the census, reasoning explicitly that *"a driver that never ran would show the same two zeros AND a zero probe count."* Generalize on `n_probes_executed > 0` (plus, optionally, a fresh run timestamp), and fall back to the finding-count predicate only where a floor genuinely exists.

**Coverage gap to close:** only `main_matriz.py` (`:2653-2682`, looping 4 packages) and `main_market_data.py` call `verify_cycle_closure` at all. `main_iol.py`, `main_higyrus.py` and `main_ambito_financiero.py` never do. "PASS no-vacuo **para cada paquete medido**" therefore needs a decision: extend matriz's 4-package loop (already covers ámbito/iol/higyrus/matriz) with the non-vacuity predicate, or add per-driver probes. The matriz loop is the cheaper seam — but note it only runs if matriz runs, which D-02 now makes true.

### Pattern 4: Emitting the census unit (currently impossible)

**What:** All four in-scope drivers print `DIVERGENCES={len(handler.seen)}` — a *count*, never the triples. D-10 requires a **set difference** against `33-CENSUS.md`, which needs the members.

**Two viable seams:**
1. **Persist `handler.seen`** — after the `with divergence_capture(...)` block, dump `sorted(handler.seen)` to a run artifact (JSON). Privacy-safe by construction: a triple is `(slug, model, field_path, kind)`, all four of which already appear verbatim inside committed finding titles (`divergences.py:176`); no wire value is involved.
2. **Re-derive from the findings file** — parse `SHAPE` titles, whose format is fixed at `f"{model}{path}: {kind} (declared={declared}, observed={observed}) [{surface}]"`, and de-duplicate on `(model, path, kind)`, collapsing the documented ~2× per-surface factor.

Seam 1 is exact and cheap; seam 2 is how `33-CENSUS.md` was actually built and works retroactively. Recommend seam 1 for this run, seam 2 as the cross-check — agreement between the two is itself evidence the census is sound.

### Anti-Patterns to Avoid

- **Adding a `verification/` test without touching `ci.yml`.** It will never execute. This is a documented, already-committed defect from Phase 36 (WR-01) and the CI comment says so in prose.
- **Putting D-08's mocked regression under `verification/`.** The `test` job runs `pytest packages/<pkg>` per package × 2 Pythons. Regressions belong in `packages/<pkg>/tests/`.
- **Weakening the D-MATZ-33 check to a substring.** `"bbsa" in base` matches `https://api.bbsa.matrizoms.com.ar.attacker.example`. D-02 says explicit allowlist; `mutation_gate.py:85-90` documents this exact attack class (plus the `https://host@attacker.example` userinfo variant).
- **Touching `verification/mutation_gate.py`.** Its `_SANDBOX_HOST` is remarkets-only by design and keeps order entry fail-closed under bbsa. Widening it is a different, much larger decision than D-02.
- **Inventing an ámbito model to have something to chain.** D-06 forbids it; Phase 37 SC-1 forbids "modelo inventado presentado como observado". `ambito_financiero_client/models.py` is `__all__: list[str] = []` and its docstring says the absence is deliberate — that docstring is itself asserted by `test_cycle_closure_phase33.py::_ambito_declares_zero_models`.
- **Running live before Wave 0 lands.** Every run writes into git-committed ledgers and can burn write-once baselines.
- **Treating `matriz` as sync-only.** Stale premise; see State of the Art.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detect a broken deep chain | A "did it PASS?" review note | AST lock, Pattern 1 | `len(rows)` PASSes with every link broken |
| Count divergences | Parse `SUMMARY FINDING=N` | `DivergenceHandler.seen` | `FINDING=N` counts probes; the ~2× surface duplication is documented and reappears if you use the wrong unit |
| Contrast against Phase 33 / 29-SIZING | Ad-hoc subtraction | `35-RETIRED-TRIPLES.md` §*How Phase 39 should use this* | It states the formula, the middle term per package, the records-vs-triples column caveat, and the WR-02 `kind` caveat |
| Redact secrets in driver stdout | Manual string munging | `safe_print(..., secrets=[...])` | Already handles token/user/password/account, used at every emission site |
| Structural payload comparison | Custom differ | `schema_of` + `_write_or_check_schema` | Keys-and-types only, PII-free by construction, D-25 no-overwrite |
| Decide "did the driver run?" | Infer from absence of errors | Non-zero probe count in the verbatim SUMMARY line | The absence-of-evidence trap is exactly what SC-3/SC-4 forbid; `test_cycle_closure_phase33.py` already argues this |
| Guard mutations under a new venue | New host check in the driver | `verification/mutation_gate.py` unchanged | Exact-hostname, fail-closed, already correct |

**Key insight:** every "should I build X?" in this phase has an existing answer somewhere in `verification/` or in a v1.6/v1.7 census artifact. The failure mode here is not under-engineering — it is re-deriving a unit or a predicate slightly differently from the artifact it must be compared against, producing a number that looks like a result and is actually a translation error.

## Common Pitfalls

### Pitfall 1: The matriz snapshot venue cross
**What goes wrong:** First bbsa run diffs against remarkets-captured baselines; up to 8 `SHAPE OPEN` "schema drift" findings appear that describe a *venue difference*, not a client defect. `33-CENSUS.md` already had to separate 48 census findings from 22 drift findings for market-data — same trap, now with an added venue axis.
**Why:** `_write_or_check_schema` keys on `func_name`; `base_url` is envelope metadata, not part of the key.
**How to avoid:** Decide venue segregation in Wave 0, before matriz runs.
**Warning sign:** matriz `schema_snapshot` probe returns `FINDING` with several fids on the very first bbsa run.

### Pitfall 2: `SKIPPED` line shape collision
**What goes wrong:** D-01 adds a skip line that either fails to match `_ENV_SKIP` (`^SKIPPED \S.*:`, `main_verify.py:42`) or *over*-matches, so a successful read sweep gets classified as a skip.
**Why:** The colon is load-bearing and deliberate. `mutation_gate.py:14-17` documents it: `SKIPPED (mutating, guard off)` has **no** colon precisely so the classifier ignores it. `_SKIP_LINE` is asserted by ámbito back-compat tests.
**How to avoid:** Emit `SKIPPED <pkg>: <measured cause> — <named destination>` (colon present, no space after `SKIPPED` before a non-space token). Add a shape test alongside the existing `verification/test_main_market_data_skip_line_shape.py`.
**Warning sign:** a green matriz run reported `SKIPPED` by `main_verify.py`.

### Pitfall 3: The higyrus DNS failure writes an OPEN finding
**What goes wrong:** `httpx.ConnectError` ⊂ `httpx.HTTPError` ⊂ `_RESIDUAL_PROBE_EXCEPTIONS` (`main_higyrus.py:144-151`), caught at `:639`/`:703`, which calls `append_finding(class_="AUTH", status="OPEN")` and sets `_auth_failed=True` (cascading all 18 probes to SKIPPED) — then `main()` just `return`s, exit 0, classified `RAN`.
**Why:** The catch-all was written for *unexpected* residuals; unreachability was never distinguished from a rejection.
**How to avoid:** Detect unreachability **before** `append_finding` (e.g. narrow `httpx.ConnectError` / `socket.gaierror` ahead of the residual bracket), emit the SKIPPED line, and return without writing a finding.
**Warning sign:** a new `F-03 … AUTH … OPEN` block in `higyrus-client-findings.md` — which also reddens `test_cycle_closure_phase33.py`'s `assert "OPEN" not in statuses`.

### Pitfall 4: matriz's ABORT prints to stderr
**What goes wrong:** D-01 wants matriz's exit-1 path classified `SKIPPED`, but `_run_driver` only scans `result.stdout` (`main_verify.py:76`) and the ABORT goes to `stderr` (`main_matriz.py:2561-2565`).
**Why:** The runner deliberately never re-emits child stdout (T-01-14/HARN-03), so it reads only the classification line.
**How to avoid:** Print the classification line to **stdout** (keep or drop the stderr detail). Note the current ABORT interpolates `PRIMARY_BASE_URL={base!r}` — a base URL, already recorded in committed findings ART blocks, but confirm before promoting it to stdout.
**Warning sign:** matriz still classified `FAILED` after the D-01 change.

### Pitfall 5: matriz's terminal EXPECTED finding becomes false
**What goes wrong:** `main_matriz.py:2691-2709` writes, every run, `title="prod-vs-remarkets divergence acknowledged"` with `expected="verification limited to remarkets sandbox by safety policy (REQUIREMENTS.md Out of Scope)"`. After D-02 both clauses are wrong, and the cited `REQUIREMENTS.md` Out of Scope table no longer contains a remarkets row (verified at HEAD).
**Why:** The text was written when remarkets-only was the whole policy.
**How to avoid:** Update it in the same commit as D-02. Because it uses `idempotent_by_title=True`, a **new** title creates a **new** finding rather than updating the old — plan the disposition of the superseded one explicitly.
**Warning sign:** two near-identical EXPECTED terminals in `matriz-client-findings.md`.

### Pitfall 6: Copying market-data's cycle-closure predicate to zero-finding packages
**What goes wrong:** ámbito and higyrus have 0 CONFIRMED/FIXED findings; the `n_closed == 0 → FAIL` predicate fails them for being clean.
**How to avoid:** Use probe-count evidence (Pattern 3).
**Warning sign:** `probe_cycle_closure` FAILs for ámbito.

### Pitfall 7: Census arithmetic that does not balance
**What goes wrong:** `census_39 ≈ census_33 − retired − fixed_in_36_37_38` fails to reconcile.
**Why (in the order `35-RETIRED-TRIPLES.md` says to check):** (b) **unit-column mix-up** — a distinct-triple count contrasted against a records floor; matriz's middle term is **6 records / 5 distinct triples** and reading the wrong column silently breaks the sum. Then (a) a live field in a shape the static roster did not anticipate — a real finding.
**Extra hazard specific to this phase:** **Phases 36 and 37 never produced their own retirement accounting.** `35-RETIRED-TRIPLES.md` scopes to classes shipped at `242b9f3` and says explicitly that 36/37/38's new non-`Optional` links "belong to their own phases' accounting". Phase 38 paid its debt (the *Phase 38 addendum*, measured: iol retires **0**). There is no `36-RETIRED*` or `37-RETIRED*` artifact — verified by directory listing. So Phase 39 must derive market-data's and matriz's 36/37 middle terms itself, or declare them unmeasured with a named destination.
**Additional matriz caveat:** matriz has **no** `census_33` at all (it was SKIPPED), so its subtraction is not computable. Phase 39 produces matriz's *first* live census, and the only available contrast is the `29-SIZING.md` floor (≥24 records / 14 distinct triples) minus 5 retired ⇒ ~9 distinct triples expected — **against a different venue than the corpus that produced the floor**. State that caveat in the artifact; do not quietly compare.

### Pitfall 8: A guard added under `verification/` that never runs
Covered in Runtime State Inventory; repeated here because it has already happened once in this repo, to this exact kind of guard.

### Pitfall 9: Market-closed vs. mis-modelled field (D-12)
**What goes wrong:** matriz `LA`/`SE`/`CL`/`OI` come back empty out-of-session and get read as broken modelling.
**How to avoid:** `probe_get_market_data` already has the `LA.date` staleness guard (`main_matriz.py:1022-1045`, >2h ⇒ `NO-DATA` finding + PASS-shape). Reuse it as the discriminator and record the run window in the census — `33-CENSUS.md` opens by stating the market was closed for its entire window (precedent P-12). If a session-hours run is not achievable, say so; do not infer.

### Pitfall 10: Deep-chain dereference outside the `try` body
**What goes wrong:** A `None`/broken link raises uncaught, propagates out of the probe, flips the package to `FAILED` in `main_verify.py`, and loses the whole run instead of degrading to a finding (the D-09 never-FAILED contract).
**How to avoid:** Put every dereference inside the probe's `try` **body** — not in `except`/`else`/`finally` — and pin it with the AST lock's `_protected_node_ids` test.

## Code Examples

### D-03 — iol `.puntas` in the existing typed probes
```python
# Site: main_iol.py:637-730 (probe_get_quote_sync) and :733-799 (async mirror).
# `client.get_quote()` already returns a typed `Cotizacion`; the chain is a pure add.
# Cotizacion.puntas: list[Punta]  (iol_client/models.py:235)
# Punta                            (iol_client/models.py:167)
    try:
        quote = client.get_quote(_SAMPLE_SYMBOL)
        ...
        # NEW — inside the SAME try body (Pitfall 10)
        book_bid = quote.puntas[0].precioCompra if quote.puntas else None
        n_levels = len(quote.puntas)
    except IOLDecodeError as exc:
        return _shape_probe_result_pair("get_quote_sync", "sync", _redacted_exc(exc))
```
```python
# Site: main_iol.py:1114 / :1264 (probe_get_instruments_by_type_{sync,async}).
# Titulo.puntas is a SINGULAR Punta Null Object (iol_client/models.py:334) — no None guard;
# branch on truthiness, which is falsy exactly when it equals Punta.empty().
        first_bid = titulos[0].puntas.precioCompra if titulos else None
```
**Live-wire evidence this chain is real:** committed finding `iol-client F-01` records the observed `get_quote` key list, and `puntas` is in it. (That same finding is a still-`OPEN` `missing simbolo` divergence — a scalar leaf, so Phase 35's Null Object policy does **not** collapse it; a Phase 39 run will re-emit it and D-11's accounting must place it.)

### D-05 — matriz, both real surfaces
```python
# SYNC gap: main_matriz.py:959-1046 fetches the RAW dict via _sync_matriz_request and
# returns `md` — it never builds a MarketDataSnapshot. The only current use of the model
# in the sync path is the field_type_map diff at :1359. Close the gap with from_api on
# the payload already in hand (same walker, same sink, no second HTTP call — Pattern 2):
    md = raw.get("marketData")
    ...
    snap = MarketDataSnapshot.from_api(md)          # NEW, inside the try body
    last_px   = snap.last.price                     # LA  -> MarketDataEntryValue.price
    n_bids    = len(snap.bids)                      # BI  -> list[MarketDataLevel]
    n_offers  = len(snap.offers)                    # OF
    settle_px = snap.settlement.price               # SE
    close_px  = snap.close.price                    # CL
    oi_val    = snap.open_interest.price            # OI
```
```python
# ASYNC: main_matriz.py:2013-2032 ALREADY calls the typed aclient.get_market_data(...)
# through the generic _ainvoke helper, which only maps exceptions and never touches the
# result. Give the probe its own body (or extend _ainvoke with a consumer callback) so
# the same six aliases are dereferenced on the async surface too.
```
The six aliases are read-only `@property` views at `matriz_client/models.py:755-783`; `OP`/`HI`/`LO`/`TV` are bare scalars and deliberately have no alias. Because properties are invisible to `typing.get_type_hints` and `dataclasses.fields`, they are invisible to `walk_model` and add **no** decode path — so exercising them cannot change the divergence count. That is a Phase 35 SC-5 guarantee, and it means the six dereferences are pure observation.

### D-01 — classification, both halves
```python
# main_matriz.py main(), replacing the substring check at :2560
_SAFE_HOSTS = ("https://api.bbsa.matrizoms.com.ar",)   # operator-approved 2026-08-29
base = client._state.base_url                          # already rstrip("/")-normalised
if "remarkets" not in base and base not in _SAFE_HOSTS:
    # D-01: stdout (main_verify only scans stdout) + env-gate line shape (colon required)
    print(f"SKIPPED {_PKG}: base URL outside D-MATZ-33 allowlist — LIVE-MATZ-33")
    sys.exit(0)
```
```python
# main_higyrus.py — ahead of the _RESIDUAL_PROBE_EXCEPTIONS bracket at :639
    except httpx.ConnectError:
        # Unreachability, not a divergence: no finding is written (Pitfall 3).
        print(f"SKIPPED {_PKG}: vendor host unreachable (DNS) — LIVE-HIGY-33")
        raise SystemExit(0) from None
```
*(Both snippets are shapes, not prescriptions — exact placement is executor discretion per CONTEXT. The load-bearing parts are: stdout, the colon, a measured cause, a named destination, and no `append_finding` on the unreachable path.)*

## State of the Art

| Old claim (in CONTEXT.md / CLAUDE.md / PROJECT.md) | Actual state at HEAD | Verified how | Impact on the plan |
|---|---|---|---|
| "matriz no tiene `aio.py`, sólo REST sync + `ws_client` en thread daemon" (D-05, CLAUDE.md Architecture, "No async support in matriz") | `packages/matriz-client/src/matriz_client/aio.py` exists with a full `AsyncClient` (25 methods incl. `get_market_data`, TokenStore-shared state) | directory listing + `__all__` + method enumeration | **D-05's "both surfaces" is sync + async, exactly like iol/higyrus.** Simpler and stronger than the REST+WS reading |
| implied: matriz driver is sync-only (`main_matriz.py:2523` docstring still says "sync-only (D-MATZ-30)") | ~19 `surface="async"` probes exist, orchestrated by `_async_main()` at `:2714`; `ws_client` is imported **zero** times by the driver | grep | The async mirror site already exists; D-05 extends it rather than creating it |
| `main_matriz.py` D-MATZ-33 assert "~line 2558-2566" | **exact at HEAD**: client ctor `:2556`, `base = client._state.base_url` `:2559`, `if "remarkets" not in base:` `:2560`, `sys.exit(1)` `:2566` | read | no drift |
| `main_higyrus.py:144-151` `_RESIDUAL_PROBE_EXCEPTIONS` | **exact at HEAD** | read | no drift |
| `main_verify.py:37-42,60-81` | **exact at HEAD** | read | no drift |
| `verification/cycle_report.py:123` `verify_cycle_closure`, vacuous at `:142-143` | **exact at HEAD** | read | no drift |
| `verification/divergences.py:112-196` `DivergenceHandler.seen` | class `:112`, `.seen` `:136`, `emit` `:139-188` (file is 319 lines) | read | no drift |
| `higyrus_client/models.py:316` `Posicion.parking`; `:463-466` `Cuenta` lists | **exact at HEAD** (`domicilios` `:463`, `personasRelacionadas` `:464`) | read | no drift |
| `33-CENSUS.md` at `.planning/phases/33-…/` | **archived** to `.planning/milestones/v1.6-phases/33-…/33-CENSUS.md` | file probe; it is why `test_cycle_closure_phase33.py` is red | CONTEXT's path is correct; the *test's* hardcoded path is not |
| `main_verify.py` runs "the five drivers" (docstring) | `_DRIVERS` has **six** entries (adds market-data) | read | D-01's classification change must not break market-data or wallets |
| matriz terminal finding cites "REQUIREMENTS.md Out of Scope" for remarkets-only | current `REQUIREMENTS.md` Out of Scope table has no remarkets row | grep | stale citation to fix with D-02 |

**Deprecated / superseded:**
- The REST+WS reading of "both surfaces" for matriz — superseded by the real `aio.py`.
- `primary.client._base_url` (used at ~20 sites in `main_matriz.py`) is a PEP-562 legacy alias forwarding to `_state.base_url` (`matriz_client/client.py:935`). Not broken; just note the driver mixes both idioms, and the D-02 gate reads the instance form.

## Project Constraints (from CLAUDE.md)

Directives extracted verbatim in force for this phase; the planner must verify compliance:

1. **Stack fixed:** Python 3.12+, uv, httpx, pytest + pytest-httpx, ruff, mypy **strict**. Every edit must pass the existing CI unchanged.
2. **No cross-package code sharing** (DT-03). Fixes land inside each package; no new shared module, no import across `packages/*`.
3. **Dual sync/async mirroring is mandatory:** any logic fix must be applied to both `client.py` and `aio.py` of the same package. (Reinforced by D-08.)
4. **Secrets:** credentials live in per-package `.env`; never commit `.env`, never expose credentials in logs, reports, or tests. All driver output goes through `safe_print(..., secrets=[...])`.
5. **`from __future__ import annotations` at the top of every module** — mandatory and applied uniformly.
6. **Ruff:** line-length 100, double quotes, 4 spaces, rule sets E/W/F/I/B/UP/SIM/RUF/ASYNC/PIE/PT/RET/TID. No relative imports, no wildcard imports. `S101` only exempt under `**/tests/**`.
7. **mypy strict:** `disallow_untyped_defs`, `warn_return_any`. New probe helpers need full annotations.
8. **Models are constructed exclusively via `Model.from_api(payload)`** — never `Model(field=value)` directly. (Directly relevant to Pattern 2 and the D-05 snippet.)
9. **Wire-verbatim field names** (camelCase); Python-facing params snake_case. Do not rename wire fields to reach a chain.
10. **Anti-pattern, named in CLAUDE.md:** *mutating module state without `configure()`*. The existing driver tests already trip on this (`test_matriz_sweep_snapshot.py`).
11. **GSD workflow enforcement:** no direct repo edits outside a GSD command.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx 0.34+, pytest-cov |
| Config file | root `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["packages", "tests", "verification"]`, `--import-mode=importlib`, `--strict-markers`) |
| Quick run command | `uv run --frozen python -m pytest -q verification/test_main_<pkg>_deep_chain.py` |
| Full suite command | `uv run --frozen python -m pytest -q packages/<pkg>` (per-package, what CI runs) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| LIVE-NOBJ-01 / SC-1 (iol) | `probe_get_quote_{sync,async}` + `probe_get_instruments_by_type_{sync,async}` each dereference `.puntas.*`, inside a `try` body, above a per-probe floor | unit (AST) | `pytest -q verification/test_main_iol_deep_chain.py` | ❌ Wave 0/1 |
| LIVE-NOBJ-01 / SC-1 (higyrus) | the chosen posiciones probe builds `Posicion` and dereferences `.parking[...]`, both surfaces | unit (AST) | `pytest -q verification/test_main_higyrus_deep_chain.py` | ❌ Wave 0/1 |
| LIVE-NOBJ-01 / SC-1 (matriz) | `probe_get_market_data{,_async}` dereference all **6** aliases off a `MarketDataSnapshot`, inside a `try` body | unit (AST) | `pytest -q verification/test_main_matriz_deep_chain.py` | ❌ Wave 0/1 |
| LIVE-NOBJ-01 / SC-1 (ámbito) | ámbito still declares **zero** model classes and empty `__all__` (the measured-absence claim stays true) | unit (AST) | `pytest -q verification/test_cycle_closure_phase33.py` (`_ambito_declares_zero_models`) | ✅ exists (currently red on a stale path) |
| SC-1 (classification) | the new skip line matches `_ENV_SKIP` and `SKIPPED (mutating, guard off)` still does **not** | unit | `pytest -q verification/test_main_<pkg>_skip_line_shape.py` | ❌ Wave 0 (mirror `test_main_market_data_skip_line_shape.py`) |
| SC-1 (classification) | `_run_driver` maps: env-skip→SKIPPED, new measured-skip→SKIPPED, rc!=0→FAILED, else RAN; market-data + wallets unaffected | unit | `pytest -q verification/test_main_verify_classification.py` | ❌ Wave 0 |
| SC-2 (edge cases) | no chain raises `AttributeError`/`TypeError` on empty/absent/204/`null` payloads | unit (mocked) | `pytest -q packages/<pkg>/tests/test_deep_chain_edges.py` | ❌ Wave 1 |
| SC-2 (never-FAILED) | every chained dereference sits in the probe's `try` **body** | unit (AST) | part of each deep-chain lock | ❌ Wave 1 |
| SC-3 (in-cycle fix) | each CONFIRMED divergence pinned by a mocked regression, sync **and** async | unit (mocked) | `pytest -q packages/<pkg>/tests/` | ❌ per-fix (unknown until the run) |
| SC-3 (non-vacuous closure) | closure PASS requires positive run evidence, per package | unit | extend `verification/test_cycle_closure_phase33.py` | ✅ exists (extend + repoint `_CENSUS`) |
| SC-4 (census) | `39-CENSUS.md` exists, uses the `(slug, model, field_path, kind)` unit, names its column, splits policy-collapse vs. real fix | manual (artifact review) | — | ❌ Wave 2 |
| D-12 (live edges) | market-closed / no-data / absent-field / 204 intentionally exercised per running package | manual (live run + census transcription) | — | ❌ Wave 2 |

### Sampling Rate
- **Per task commit:** `uv run --frozen ruff check . && uv run --frozen ruff format --check . && uv run --frozen mypy` + the touched deep-chain lock.
- **Per wave merge:** `uv run --frozen python -m pytest -q packages/<touched-pkg>` + the full explicit `verification/` allowlist from `ci.yml:80-84` **including the newly appended files**.
- **Phase gate:** all four `tools/check_*.py` gates + 6 packages × py3.12/3.13 + the widened allowlist green, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `verification/test_main_verify_classification.py` — covers SC-1 classification (D-01)
- [ ] `verification/test_main_matriz_skip_line_shape.py` / `..._higyrus_...` — covers the colon-shape contract (Pitfall 2)
- [ ] `verification/test_main_iol_deep_chain.py` — covers SC-1 (D-03)
- [ ] `verification/test_main_higyrus_deep_chain.py` — covers SC-1 (D-04)
- [ ] `verification/test_main_matriz_deep_chain.py` — covers SC-1 (D-05)
- [ ] `packages/<pkg>/tests/test_deep_chain_edges.py` ×3 — covers SC-2 with mocked empty/absent/204 payloads
- [ ] **`.github/workflows/ci.yml:80-84`** — append every new `verification/` file to the explicit allowlist, same commit (else all of the above are inert)
- [ ] `verification/test_cycle_closure_phase33.py` — repoint `_CENSUS` to `.planning/milestones/v1.6-phases/33-…/33-CENSUS.md` (turns 2 red green) and extend for D-09
- [ ] Framework install: none required

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`. This phase contains one genuinely security-relevant change (D-02) and several handling-of-secrets surfaces.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Credentials only from per-package `.env` via `python-dotenv`; never logged. `safe_print(secrets=[...])` redacts user/password/token/account at every emission site |
| V3 Session Management | partial | Token TTL + `TokenStore` 3-way primitive already shipped (matriz). Phase 39 must not add a second login path |
| V4 Access Control | **yes — the core of D-02** | Two independent gates: driver-level anti-prod allowlist (`main_matriz.py`) and mutation gate (`verification/mutation_gate.py`). D-02 widens **only** the first |
| V5 Input Validation | yes | `SafeModel.from_api` tolerant decode; `findings._PKG_SLUG_RE` path-traversal guard; `_regression_is_resolvable` rejects absolute paths and `..` and enforces repo-root containment |
| V6 Cryptography | no | No crypto introduced or modified |
| V7 Error Handling & Logging | yes | Findings are **git-committed public artifacts forever**: `divergences.py` composes titles from the 6-key record + endpoint + surface only, **never** a wire value (P-01 / T-33-01). Any new emission must obey the same rule |
| V12 Files & Resources | yes | Snapshot/finding writes stay under `.planning/verification/`; `_SCHEMA_DIR` is derived from `__file__`, not from input |

### Known Threat Patterns for this change

| Pattern | STRIDE | Standard Mitigation | Status in this phase |
|---|---|---|---|
| Substring hostname match lets `…bbsa.matrizoms.com.ar.attacker.example` through | Spoofing / Elevation | Exact-equality allowlist, never `in`/`endswith` | D-02 mandates the allowlist form; `mutation_gate.py:85-90` documents the attack verbatim |
| Userinfo smuggling: `https://api.bbsa.matrizoms.com.ar@attacker.example` | Spoofing | Compare `urlsplit(url).hostname`, not the raw string | The **driver** gate compares the whole normalised base URL string, so equality already excludes it; the mutation gate compares `.hostname` |
| Widening the anti-prod gate also enables order entry against a new venue | Tampering / Destruction | Independent second gate | **Verified mitigated:** `mutation_gate._SANDBOX_HOST = "api.remarkets.primary.com.ar"` with exact-hostname match ⇒ under bbsa, mutations are fail-closed **automatically**, no code change required. Also, matriz's `sweep_probes` list (`main_matriz.py:2615-2634`) contains **no** `new_order`/`replace_order`/`cancel_order` — the sweep is read-only. **Do not touch `mutation_gate.py`.** |
| Credential leakage into git-committed findings/census | Information Disclosure | `safe_print` + title composed only of type/path metadata | Applies to any new emission; the triple dump (Pattern 4) is metadata-only and therefore safe |
| Base URL / host promoted from stderr to stdout by D-01 | Information Disclosure (low) | Base URLs already appear in committed findings ART blocks | Confirm intent; prefer emitting the *policy verdict* rather than the URL |
| Path traversal via a crafted finding `Regression:` value | Tampering | `_regression_is_resolvable` (`cycle_report.py:90-120`) | Already mitigated; D-09's wrapper must not bypass it |
| Silent sink failure hiding divergences | Repudiation | `handler.errors` tallied and printed as `HANDLER_ERRORS=N` every run | Already in all 4 drivers; **a non-zero value invalidates the census** — the plan must treat it as a gate, not a note |

**Human checkpoint required.** D-02 is a loosening of a hostname safety gate. CONTEXT records operator sign-off dated 2026-08-29 (memory `project_matriz_bbsa_sandbox.md`), and the established pattern (D-08/D-18) is an explicit, non-collapsible checkpoint plus an in-code comment plus a phase-report entry. `mode: yolo` + `auto_advance: true` are active in `config.json` — the plan must make this checkpoint blocking anyway.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | The matriz bbsa sandbox is genuinely non-production and safe to sweep read-only | Security Domain, D-02 | Reads against a real venue. **Mitigated by operator sign-off (checkpoint, 2026-08-29) + the independent read-only mutation gate.** This is the operator's assertion, not Claude's inference — but it is not machine-verifiable and remains the phase's single largest trust dependency |
| A2 | Higyrus DNS will still fail at execution time | Environment Availability | If it resolves, D-04's live half becomes runnable and the plan needs a live path it did not budget. **Cheap to re-probe at execution start — recommend the plan do so rather than assume this session's result** |
| A3 | bbsa exposes the same `/rest/marketdata/get` entry codes (`BI,OF,LA,OP,CL,SE,OI`) as remarkets | D-05, Pitfall 1 | Missing entries would read as divergences. Partly self-correcting: `MarketDataSnapshot` Null Objects absorb absence without raising, and the 6 aliases are properties invisible to the walker — but the *schema snapshot* diff would still fire |
| A4 | `MATRIZ_SAMPLE_SYMBOL` / `PRIMARY_ACCOUNT` from `.env` are valid on bbsa | D-05, D-12 | Symbol-dependent probes SKIP. Partly mitigated: `_resolved_symbol` is resolved live from `get_all_instruments` (probe #3), so the sample env vars are overrides, not requirements |
| A5 | A trading-session-hours matriz run is achievable within the phase window | D-12 | Cannot distinguish market-closed from mis-modelled. Fallback: run out-of-hours, use the existing `LA.date` staleness guard, and record the window in the census (precedent: `33-CENSUS.md` did exactly this) |
| A6 | The three currently-red `verification/` files stay out of scope | Environment Availability | If the executor tries to green them, scope explodes. Exception: `test_cycle_closure_phase33.py` is a one-line path repoint the phase touches anyway for D-09 |
| A7 | No new external package is needed | Package Legitimacy Audit | If a plan proposes one, re-derive — this is a strong signal of drift |

## Open Questions

1. **How should the matriz remarkets-era schema baselines be handled under bbsa?**
   - What we know: file key is `func_name` only; `base_url` is envelope metadata; D-25 forbids overwrite-on-drift; 8 baselines exist, all remarkets, captured 2026-06-10.
   - What's unclear: whether the operator wants venue-keyed snapshot files, a parallel bbsa baseline directory, or drift findings classified `EXPECTED` with a venue rationale.
   - Recommendation: **decide in Wave 0, before any matriz run.** Venue-keying the filename is the least destructive (preserves the remarkets baseline untouched for a future remarkets run) and keeps the SC-4 census free of venue noise.

2. **Which seam carries D-09's non-vacuity for the three drivers that never call `verify_cycle_closure`?**
   - What we know: only matriz (4-package loop, `:2653-2682`) and market-data call it. iol/higyrus/ámbito do not.
   - What's unclear: whether "cada paquete medido" is satisfied by matriz's cross-package loop, or requires a per-driver probe.
   - Recommendation: extend matriz's loop with the probe-count predicate (cheapest, already covers all four in-scope slugs) and note the coupling — if matriz skips, the loop does not run.

3. **Who supplies the Phase 36/37 middle terms for the census?**
   - What we know: `35-RETIRED-TRIPLES.md` scopes to `242b9f3` and explicitly disclaims 36/37/38's new links; Phase 38 paid its debt via the addendum; there is no `36-RETIRED*` / `37-RETIRED*`.
   - What's unclear: whether Phase 39 derives them or declares them unmeasured with a destination.
   - Recommendation: derive what is derivable from `36-CONTEXT.md` / `37-CONTEXT.md` field rosters; for anything not derivable, declare it explicitly with a named destination rather than folding it silently into "fixed".

4. **Disposition of the pre-existing iol `F-01` (`missing simbolo`, OPEN)?**
   - What we know: it is a scalar leaf, so the Null Object policy does not collapse it; a Phase 39 run re-emits it; Phase 17 re-confirmed it OPEN as a documented baseline divergence with root-cause investigation deferred.
   - Recommendation: carry it forward as OPEN with its existing rationale, and account for it explicitly in the census so its persistence is not read as a new regression.

5. **Does the D-01 skip line for matriz reveal the base URL on stdout?**
   - Recommendation: emit the policy verdict and the destination (`LIVE-MATZ-33`), not the URL. Base URLs already live in committed findings ART blocks, so this is low-risk either way — but "least data on stdout" is the cheaper default.

## Sources

### Primary (HIGH confidence — read at HEAD in this session)
- `main_verify.py` (whole file, 102 lines) — `_DRIVERS`, `_ENV_SKIP`, `_run_driver`
- `main_matriz.py` — `:360-410`, `:930-1046`, `:1825-1875`, `:2013-2032`, `:2515-2745`
- `main_higyrus.py` — `:90-210`, `:300-410`, `:580-710`, `:2660-2854`
- `main_iol.py` — `:628-800`, `:1114`, `:1264`, `:2124`, `:2152`, `:2248-2261`
- `main_ambito_financiero.py` — `:505-570`, `:788-842`
- `main_market_data.py` — `:3360-3412` (the hardened `probe_cycle_closure`)
- `verification/{divergences,cycle_report,env_gate,mutation_gate,schema,findings}.py`
- `verification/test_main_market_data_deep_chain.py` (whole file), `verification/test_cycle_closure_phase33.py` (whole file), `verification/test_matriz_sweep_snapshot.py` (`:1-110`)
- `packages/{iol,higyrus,matriz,ambito-financiero}-client/src/*/models.py`, `matriz_client/{aio,_state,client}.py`, `higyrus_client/{client,_core,_decode}.py`
- `.github/workflows/ci.yml:30-159`; root `pyproject.toml:102-121`
- `.planning/{ROADMAP,REQUIREMENTS,STATE,PROJECT,config.json}`; `.planning/verification/*-findings.md` + `schemas/*/`
- `.planning/milestones/v1.6-phases/33-…/33-CENSUS.md`; `.planning/phases/35-…/35-RETIRED-TRIPLES.md`; `.planning/phases/38-…/{38-CENSUS,38-CONTEXT}.md`

### Executed measurements (HIGH confidence)
- `uv run --frozen python -m pytest verification/ -q --collect-only` → **431 tests, 0 collection errors**
- Per-file timed run of all 45 `verification/test_*.py` → 40 green, 3 red, 2 >45s (results tabulated above)
- DNS probe of the four configured hosts (key names read, values never printed): higyrus `gaierror`, matriz/iol resolve
- `uv --version` → 0.11.3; workspace Python 3.12.13
- Envelope inspection of all 8 matriz schema snapshots → all `base_url: https://api.remarkets.primary.com.ar`

### Tertiary (LOW confidence)
- Session memory `project_matriz_bbsa_sandbox.md` — operator assertion about bbsa safety. **Authoritative as a decision, not verifiable as a fact by this agent** (see A1).

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — no external dependencies; every component read at HEAD
- Architecture / seams: **HIGH** — all CONTEXT line references re-verified; the one contradiction (matriz async) confirmed from three independent angles (package files, `__all__`, driver probes)
- Pitfalls: **HIGH** for 1-8 and 10 (each traced to a specific line or an executed measurement); **MEDIUM** for 9 (depends on run timing)
- Environment: **HIGH** — measured this session; A2 recommends re-probing at execution time
- Census arithmetic: **MEDIUM** — the method is fully specified by `35-RETIRED-TRIPLES.md`, but two inputs (Phase 36/37 middle terms; matriz's absent `census_33`) are genuinely missing and are raised as Open Questions rather than papered over

**Research date:** 2026-08-29
**Valid until:** 2026-09-28 for the code facts (internal repo, stable); **the DNS and live-API facts are valid for hours, not weeks** — re-probe at execution start.
