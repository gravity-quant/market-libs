# Phase 32: Gates de homogeneidad + D-16 - Research

**Researched:** 2026-08-25
**Domain:** CI enforcement tooling — stdlib AST gates, runtime introspection parity tests, config-list reconciliation (Python 3.12 monorepo, no shared code between packages)
**Confidence:** HIGH (every claim below was executed against the working tree today, not recalled)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Alcance real de D-16 (criterio 4)**

- **D-01:** El framing del roadmap ("reconciliar 4 listas") está **stale**. De las 4, sólo mypy
  `files` (`pyproject.toml:97`) tiene un gap de código real — falta `packages/market-data-client/src`,
  y es **zero-fix**: `uv run mypy packages/market-data-client/src` ya pasa limpio hoy.
  Import-linter `root_packages` (`pyproject.toml:149-156`) **ya** incluye `market_data_client` con
  su contrato `_core` (WR-05 de Phase 31, `pyproject.toml:182-187`) y `uv run lint-imports` corre
  verde hoy. El loop mypy-tests de `ci.yml` (línea real hoy: **95**, no 85 como cita el roadmap) ya
  itera los 6 paquetes. El commit atómico del criterio 4 tiene, por tanto, una sola edición
  sustantiva de código (la línea de `files`) — el resto es documentación/pruebas, no enrollment.
- **D-02:** La única pieza real que falta de D-16 es una **prueba RED del contrato import-linter
  `market_data_client._core does not depend on transport modules`** — no existe ningún precedente
  de RED-fixture para import-linter en todo el repo (grep de `lint-imports`/`importlinter` sobre
  código no-planning: sólo `pyproject.toml`, los dos scripts de `tools/`, 3 docstrings de `_core.py`
  y `ci.yml`). Mecanismo exacto: Claude's Discretion (ver abajo).

**Gate AST de superficie (criterios 1-2)**

- **D-03:** El gate **debe recorrer métodos de clases exportadas** (`Client`, `AsyncClient`,
  `SafeModel` y subclases en `__all__`), no sólo funciones de módulo. Verificado empíricamente:
  **cero** funciones de módulo exportadas retornan `Any`/`dict[str, Any]` en los 6 paquetes hoy; los
  únicos 9 hits son métodos `to_dict()` (el `SafeModel.to_dict` de iol/higyrus + 7 request-models de
  market-data). Que el criterio 1 nombre la exención `to_dict()` es la prueba de que los métodos
  están en scope — si el gate no los mirara, esa exención sería letra muerta y el gate sería vacuo
  para el vector de regresión más probable (`Client.get_x() -> dict[str, Any]` nuevo). Resolución de
  `__all__` a sitio de definición vía los `ImportFrom` explícitos de cada `__init__.py` — ningún
  paquete usa star-imports (CLAUDE.md dice lo contrario; está stale).
- **D-04:** `tools/check_surface_types.py` expone la lógica de chequeo como función(es) testeables
  con **raíz inyectable** (parámetro `root: Path`), no como `REPO_ROOT` module-level como los dos
  gates cross-package existentes (`check_uniform_structure.py`, `check_decode_intactness.py` —
  ninguno de los dos tiene test hoy, precisamente por carecer de esto). Necesario porque el criterio
  2 exige una fixture RED automatizada que ejerza el checker contra un árbol sintético roto.
- **D-05:** El gate va como **step nuevo del job `lint` existente** — mismo patrón que
  `decode-intactness`/`uniform-structure` — siguiendo el D-12 de Phase 31, **no** como job de CI
  nuevo. Esto **resuelve explícitamente** una contradicción: `ROADMAP.md:25` dice literalmente "job
  de CI nuevo", pero el D-12 ya lockeado en `31-CONTEXT.md` fija el patrón "step en `lint`". Se
  prioriza el D-lock sobre la prosa del roadmap-summary; debe quedar anotado así en el plan/summary
  de la fase para que nadie lo lea como una contradicción sin resolver.

**Test de paridad sync/async (criterio 3)**

- **D-06:** El test **no puede comparar por `__all__`** — 4 de 6 `client.py` (iol, higyrus,
  market-data, wallets) y 3 de 6 `aio.py` (iol, market-data, wallets) carecen de `__all__`; un test
  basado en eso pasaría vacuamente (`[] == []`) en la mitad de los paquetes. Debe derivar nombres
  públicos por introspección runtime (`dir()` filtrado por `__module__ == mod.__name__`) y comparar
  `get_type_hints()` sobre ese conjunto.
- **D-07:** El test corre **in-package** como 6 archivos delgados bajo `packages/<pkg>/tests/`, cada
  uno delegando en un **helper de introspección compartido** (nunca 6 copias del walker — repetiría
  el problema que `check_decode_intactness.py` existe para prevenir en `_decode.py`). Viable porque
  `pythonpath = ["."]` (`pyproject.toml:110`) hace importable la raíz desde tests de paquete —
  "Patrón 1", ya usado por 8 archivos (ej. `packages/ambito-financiero-client/tests/test_harness_schema.py:9-20`).
  Ubicación exacta del helper (`verification/` vs `tools/`): Claude's Discretion (ver abajo).
- **D-08:** Los lower bounds de no-vacuidad son **enteros literales por paquete**, medidos hoy
  (nombres públicos con `__module__` propio, client/aio): ambito 2/3, iol 6/7, higyrus 7/8,
  matriz 22/23, market-data 19/20, **wallets 1/2** — nunca un umbral uniforme. El bound de wallets
  (N=1, sólo `configure`) es un piso casi-vacuo para ese paquete específicamente y debe quedar
  documentado como tal, no ocultado detrás de un número que parece robusto.
- **D-09:** El test **encontrará una divergencia real el primer día**: `market_data_client.aio.configure`
  (`aio.py:776-788`) no acepta `http_client`, mientras `client.configure` (`client.py:762-775`) sí —
  pese a que el docstring de `aio.py:797-798` afirma que la semántica "espeja exactamente" la
  superficie sync. Es drift documentado-como-inexistente. Qué hacer con este hallazgo específico:
  Claude's Discretion (ver abajo) — no se resuelve en esta discusión, pero el test debe poder
  correr (ya sea porque se corrigió o porque se allowlisteó explícitamente) sin quedar rojo sin
  explicación.

**Roster explícito: wallets + `_PACKAGES` (criterio 4)**

- **D-10:** `wallets_client` **queda excluido** de `root_packages` de import-linter — razón
  **estructural**, no de preferencia: es el único paquete pre-Phase-7 (singletons de módulo directos
  en `client.py:33-35`) y **no tiene `_core.py`** (ni `_state.py`/`_transport.py`/`_decode.py`/
  `_logging.py`) — no existe `source_modules` contra el cual escribir un contrato `forbidden` como
  los 5 existentes. Debe quedar dicho explícitamente en el commit/docs de D-16, no implícito.
- **D-11:** `verification/test_public_surface.py::_PACKAGES` **se mantiene en sus 4 entradas**
  actuales (market-data y wallets excluidos) — se documenta con un **comentario inline**, sin tocar
  la lista ni regenerar un snapshot. Razón: `verification/` nunca corre en CI (`ci.yml` job `test`
  pasa `packages/${{ matrix.package }}` explícito, que pisa `testpaths`), así que un snapshot nuevo
  quedaría rojo-invisible tras el primer cambio de superficie — el mismo riesgo que
  `30-CONTEXT.md:D-09` ya identificó para iol. La cobertura real de market-data ya existe in-package
  (`packages/market-data-client/tests/test_public_surface_market_data.py`, que sí corre en la
  matrix) — el comentario debe referenciarlo por path.
- **D-12:** El scope del criterio 4 se limita a las 4 listas que nombra explícitamente. Existen
  ~6 otros rosters de paquetes dispersos en `verification/` (`test_async_cancellation.py`,
  `test_logging_no_token_leak.py`, `test_max_retries_validation.py`,
  `test_findings_dedupe_by_title.py`, `test_async_configure_resource_warning.py`,
  `test_sync_async_isolation.py`) y en `tools/check_decode_intactness.py`
  (`IN_SCOPE_PACKAGES`/`EXEMPT_PACKAGES`) — quedan **fuera de scope**, anotados como deuda diferida,
  no silenciados ni "arreglados de paso".

### Claude's Discretion

- Mecanismo del RED-proof de D-02: (a) test automatizado por subprocess contra un módulo temporal
  que viole el contrato (hay precedente de subprocess en tests, ej.
  `verification/test_main_iol_exception_redaction.py`, pero `lint-imports` tarda decenas de segundos
  sobre 69 archivos) vs (b) demostración manual documentada en el SUMMARY de la fase, siguiendo el
  precedente exacto de `packages/iol-client/tests/test_typed_surface_red.py` (Phase 30 D-10, cuyo
  docstring dice explícitamente "non-vacuity fue verificado a mano... registrado en 30-01-SUMMARY.md").
  Nota: el criterio 4 dice sólo "RED-probado" (sin exigir test automatizado), mientras el criterio 2
  sí dice explícitamente "y el test lo prueba" para el gate de superficie — asimetría deliberada en
  el texto del roadmap que favorece (b) como opción más barata y igualmente conforme al criterio.
- Ubicación del helper compartido de D-07: `verification/` (precedente "Patrón 1" ya usado por 8
  archivos) vs `tools/` (precedente de tooling cross-package stdlib-only, D-12 de Phase 31).
- Mecanismo exacto de la fixture RED de D-04: `tmp_path` sintético vs fixture de archivos
  committeados bajo `tools/fixtures/` vs inyección de source-string/AST — dentro de la restricción
  de raíz inyectable de D-04.
- Qué hacer con el hallazgo de D-09 (`market_data_client.aio.configure` sin `http_client`):
  (1) corregirlo agregando el parámetro — cierra el drift y alinea el docstring con la realidad,
  pero es un cambio de superficie pública en un paquete candidato a re-publish en Phase 34; o
  (2) allowlistear `configure` del chequeo de hints completo y comparar sólo el set de nombres de
  parámetros — sigue cazando el `http_client` faltante sin exigir tipos idénticos, más laxo que la
  letra del criterio 3 ("compara `get_type_hints()`"). Recomendado: (1), porque dejarlo sin
  corregir perpetúa exactamente el tipo de divergencia silenciosa que este milestone existe para
  eliminar — pero confirmar en planning dado el impacto de superficie pública.

### Deferred Ideas (OUT OF SCOPE)

- Fix real de `market_data_client.aio.configure` (agregar `http_client`) vs allowlist explícito —
  Claude's Discretion arriba; se resuelve en planning, no en esta discusión
- Los ~6 rosters de paquetes fuera del scope del criterio 4 (ver D-12) — deuda documentada, no
  scope de Phase 32
- Actualización de `CLAUDE.md` (afirma que matriz no tiene `aio.py` y que los `__init__.py` usan
  star-imports — ambas stale) — fuera de scope de esta fase, nota lateral únicamente
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GATE-TYP-01 | CI falla si la homogeneidad se degrada: (a) gate AST de superficie — cero `Any`/`dict[str, Any]` en retornos de funciones exportadas en `__all__` con exenciones DT-06; (b) test de paridad sync/async por introspección no-vacuo con lower bounds y fixtures RED; (c) cierre de D-16 reconciliando las 4 listas de enrollment + contrato import-linter de `market_data_client._core` + decisión sobre wallets | (a) → § Gate Simulation Results (319 defs scanned, 0 non-exempt hits, exemption taxonomy verified); § Pattern 1/2. (b) → § Sync/Async Parity: Measured Ground Truth (the 6 divergences a naive test finds, the normalization rule required); § Pattern 3. (c) → § D-16: Measured State of the 4 Lists; § Pitfall 1 (import-linter cost premise corrected); § Pattern 4 |
</phase_requirements>

---

## Summary

Every factual claim in CONTEXT.md was re-executed against the working tree today. **The
decision content of D-01 through D-12 holds** — the phase is correctly scoped and the locked
decisions are sound. But three things need the planner's attention before it writes tasks.

**First, and most consequential: CI is red right now, for reasons unrelated to this phase.** The
`typecheck` job's "mypy (tests por paquete)" loop fails on **3 of 6 packages with 33 errors total**
(matriz 29, higyrus 2, ambito 2), all inside Phase 29's `test_decode.py` / `test_ws_decode_mode.py`.
The last CI run was 2026-08-18; Phases 29, 30 and 31 have never been CI-validated. Success criterion
5 ("la matriz completa de CI queda verde con los gates nuevos activos") therefore contains
pre-existing remediation work that no one has budgeted. Everything else is green: ruff, the two
existing gates, `lint-imports`, global `mypy` on src, and all 1682 tests across the six packages.

**Second, the sync/async parity test will not find one divergence — it finds six**, and five of them
are *legitimate and permanent*. A naive `get_type_hints(sync) == get_type_hints(async)` comparison
reports `configure(http_client=)` as divergent in **all five** packages that have it, because the
sync surface correctly takes `httpx.Client` and the async surface correctly takes
`httpx.AsyncClient`. The test needs a sanctioned normalization rule (`httpx.Client ↔ httpx.AsyncClient`),
structurally identical to the normalization-rule table in `check_decode_intactness.py`. Only *after*
that rule does the D-09 finding stand alone as the single real drift. Without the rule the test is
red across the board on day one and the D-09 signal is buried.

**Third, D-02's cost premise is wrong in a way that flips its recommendation.** CONTEXT states
`lint-imports` "tarda decenas de segundos sobre 69 archivos". Measured today, cold (no `.grimp_cache`
exists in this repo): **~0.07 s**, three runs in a row, because import-linter 2.11 sits on grimp 3.14
which has a Rust core. A subprocess-driven automated RED test is therefore cheap, and the argument
that favoured the manual-demonstration route evaporates.

**Primary recommendation:** Plan four workstreams — (0) unbudgeted: fix the 33 pre-existing mypy
errors, since criterion 5 cannot pass without it; (1) `tools/check_surface_types.py` with an
injectable `root: Path` plus a `tmp_path` RED fixture; (2) a shared parity helper in `tools/` with a
documented `httpx.Client↔AsyncClient` normalization rule and per-package integer lower bounds; (3)
the one-line mypy `files` edit plus a subprocess-based import-linter RED test and the two
documentation comments.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Surface-type gate (`Any`/`dict[str,Any]` in exported returns) | Repo tooling (`tools/`, stdlib AST) | CI `lint` job | Cross-package by nature; must never import a package module (`load_dotenv()` side effects at import time). Static text/AST read only. |
| RED proof of the surface gate | Package test suite (`packages/<pkg>/tests/`) | — | Must execute in the 6×2 matrix; `verification/` never runs in CI. Needs the injectable-root seam from D-04. |
| Sync/async parity assertion | Package test suite (in-package, 6 thin files) | Shared helper at repo root | Requires *runtime* introspection (`get_type_hints`), which AST cannot do; must import both `client.py` and `aio.py`. |
| Parity walker logic | Repo tooling (single shared module) | — | Six copies would recreate exactly the drift `check_decode_intactness.py` exists to prevent. |
| mypy `files` enrollment | Root config (`pyproject.toml`) | CI `typecheck` job | Single declarative list; global mypy invocation. |
| import-linter contract enforcement | Root config (`pyproject.toml`) | CI `lint` job | Already complete; only the RED proof is missing. |
| import-linter RED proof | Package test suite (subprocess) | — | Needs a real `lint-imports` invocation against a mutated tree; cannot be asserted statically. |
| `_PACKAGES` roster documentation | Source comment (`verification/`) | — | Documentation-only per D-11; list is explicitly not edited. |

---

## Project Constraints (from CLAUDE.md)

Actionable directives extracted from `./CLAUDE.md` that constrain this phase:

| Directive | Impact on Phase 32 |
|-----------|--------------------|
| Python 3.12+, uv, pytest, ruff, mypy **strict** — all extensions must pass existing CI | New `tools/check_surface_types.py` and the parity helper must pass `ruff check`, `ruff format --check` and (if imported by a package test) per-package `mypy --strict` |
| **No shared code between packages, by design** | The parity helper lives at repo root (`tools/` or `verification/`), NOT inside a package. It is test/CI infrastructure, not shipped code — this does not violate the constraint. |
| **Dual sync/async**: any logic fix must be mirrored in `client.py` and `aio.py` of the same package | Directly binds the D-09 fix: adding `http_client` to `market_data_client.aio.configure` *is* the mirroring obligation, not a discretionary nicety |
| Credentials live in per-package `.env`; never commit `.env` nor expose credentials in logs/reports/tests | Gates must be pure static reads or import-only introspection — no live calls, no credential access. Both existing `tools/` gates state this explicitly in their docstrings. |
| `from __future__ import annotations` mandatory in every module | Applies to new files; also the reason `get_type_hints()` (not `__annotations__`) is the correct introspection primitive — see Pitfall 3 |
| Ruff: line-length 100, double quotes, 4-space indent; rule sets incl. `PT` (pytest-style), `TID` (no relative imports), `RET`, `SIM` | New test files must use `PT`-compliant pytest style; helper imports must be absolute |
| No wildcard imports; no relative imports | Confirms the AST-resolvable `ImportFrom` assumption of D-03 |
| **GSD Workflow Enforcement**: no direct repo edits outside a GSD workflow | Research phase performed read-only operations plus non-mutating command invocations; no source files were modified |

---

## Verification of CONTEXT.md Claims

Each claim was re-executed today. Nothing below is recalled.

### Claims CONFIRMED exactly

| Claim | Verification |
|-------|-------------|
| D-01: `uv run mypy packages/market-data-client/src` passes clean | `Success: no issues found in 13 source files` [VERIFIED: command output] |
| D-01: global mypy with market-data added is zero-fix | Ran mypy with all six `src` paths explicitly: `Success: no issues found in 75 source files` [VERIFIED: command output] |
| D-01: `lint-imports` green with `market_data_client` enrolled | `Contracts: 5 kept, 0 broken.` — all five `_core` contracts KEPT, including `market_data_client._core` [VERIFIED: command output] |
| D-01: `ci.yml` mypy loop already iterates 6 packages, at line 95 | `ci.yml:95` is `for pkg in higyrus-client wallets-client matriz-client iol-client ambito-financiero-client market-data-client; do` [VERIFIED: file read] |
| D-03: zero exported **module-level** functions return `Any`/`dict[str, Any]` | Gate simulation: 0 non-exempt hits across all six packages [VERIFIED: executed simulation] |
| D-03: exactly **9** `to_dict()` hits, = iol + higyrus `SafeModel` + 7 market-data request models | Confirmed. See § Gate Simulation Results for the exact nine. [VERIFIED] |
| D-03: no package uses star-imports; all `__init__.py` use explicit `ImportFrom` | Confirmed across all six `__init__.py`. Zero `import *`. [VERIFIED: grep + AST resolution succeeded for 100% of `__all__` names] |
| D-03: CLAUDE.md's star-import claim is stale | Confirmed stale [VERIFIED] |
| D-06: 4 of 6 `client.py` lack `__all__` (iol, higyrus, market-data, wallets) | Exactly right [VERIFIED: runtime `hasattr(m, "__all__")`] |
| D-06: 3 of 6 `aio.py` lack `__all__` (iol, market-data, wallets) | Exactly right — note higyrus `aio.py` **has** `__all__` while its `client.py` does not [VERIFIED] |
| D-07: "Patrón 1" already used by **8** files | Exactly 8 package-test files import repo-root modules (`from verification.…`): 7 in ambito, 1 in iol (`test_models.py`) [VERIFIED: grep] |
| D-09: `market_data_client.aio.configure` lacks `http_client`; sync has it | Confirmed, and it is the **only** package with this asymmetry [VERIFIED: AST signature diff across all 12 modules] |
| D-09: line spans `aio.py:776-788`, `client.py:762-775`, docstring `aio.py:797-798` | All three exact [VERIFIED: file read] |
| D-10: `wallets_client` has no `_core.py`/`_state.py`/`_transport.py`/`_decode.py`/`_logging.py` | Confirmed — `wallets_client/` contains only `__init__.py`, `aio.py`, `client.py`, `exceptions.py`, `models.py`, `py.typed`, `types.py` [VERIFIED: directory listing] |
| D-11: `_PACKAGES` has 4 entries, excludes market-data and wallets | Confirmed at `verification/test_public_surface.py:46-51` [VERIFIED] |
| D-11: `ci.yml` job `test` passes an explicit per-package path that overrides `testpaths` | Confirmed: `ci.yml:124-126` passes `packages/${{ matrix.package }}` on the pytest command line while `pyproject.toml:106` sets `testpaths = ["packages", "tests", "verification"]` [VERIFIED] |
| D-11: `packages/market-data-client/tests/test_public_surface_market_data.py` exists and covers the gap | Confirmed; its own docstring states the `verification/` exclusion as its raison d'être [VERIFIED: file read] |
| D-12: the ~6 out-of-scope rosters exist | Confirmed. Additionally: `test_async_configure_resource_warning.py::_ASYNC_PACKAGES` has only 3 entries (ambito, iol, higyrus) and `test_sync_async_isolation.py::_PACKAGES` has 4 — both exclude market-data [VERIFIED] |

### Claims CORRECTED — planner must not use CONTEXT.md's version

| # | CONTEXT.md says | Reality (measured today) | Impact |
|---|-----------------|--------------------------|--------|
| C-1 | D-02: "`lint-imports` tarda **decenas de segundos** sobre 69 archivos" | **~0.07 s**, measured 3× consecutively via `subprocess.run`. No `.grimp_cache` directory exists in the repo, so this is a cold number. import-linter 2.11 / grimp 3.14 has a Rust core. | **Flips the Claude's-Discretion recommendation for D-02.** The cost objection to an automated subprocess RED test does not exist. See § Recommendation R-1. |
| C-2 | D-08: lower bounds are "ambito 2/3, iol 6/7, higyrus 7/8, matriz 22/23, market-data 19/20, wallets 1/2" measured as "nombres públicos con `__module__` propio" | Those numbers are correct **only if classes are excluded**. Under D-06's literal metric (`dir()` filtered by `__module__`, which *includes* `Client`/`AsyncClient`) the numbers are **3/4, 7/8, 8/9, 23/24, 20/21, 1/2**. | D-06 and D-08 use **different metrics**. If the planner implements D-06 literally and pins D-08's integers, every package except wallets fails by exactly 1. The plan must state the metric explicitly. See § Measured Surface Counts. |
| C-3 | D-09 implies a **single** divergence on day one | A naive `get_type_hints()` comparison finds **6**: five legitimate `httpx.Client` vs `httpx.AsyncClient` on `configure(http_client=)`, plus the one real market-data drift. | The parity test needs a normalization rule or it is red in all six packages, not one. See § Sync/Async Parity: Measured Ground Truth. |
| C-4 | Line refs: `pyproject.toml:149-156` (root_packages), `:182-187` (market-data contract), `:110` (pythonpath) | Actual: `root_packages` = **147-153**; market-data contract = **182-186**; `pythonpath` = **109** (`testpaths` = 106). Only `files` at **97** is exact. | Cosmetic drift, but the planner was told to rely on exact line numbers. Use the corrected values. |
| C-5 | Line refs: `ci.yml:37-38` (lint-imports), `:49-59` (decode/uniform), `:118-122` (job `test`) | Actual: `lint-imports` = **40-41**; `decode-intactness` = **51-55**, `uniform-structure` = **56-60**; job `test` step = **122-128**, matrix package list = **107-113**. `:95` (mypy loop) is exact. | Same as C-4. The new `lint` step appends after **line 60**. |
| C-6 | Criterion 1 exemption "`_request` que devuelve `httpx.Response`" | Under the literal rule (fail on `Any`/`dict[str, Any]` returns), **no `_request` anywhere returns `Any`** — all the method-form ones return `httpx.Response` and are thus never candidates. And every module-level `_request` is `_`-prefixed *and* absent from every `__all__`. The exemption is dead letter unless the gate also bans raw `httpx.Response` on the exported surface. | Harmless, but the planner should either drop it or make the gate's second rule (ban `httpx.Response` on the surface) explicit. See § Open Question OQ-2. |
| C-7 | CLAUDE.md: "No async support in matriz: `matriz_client` has no `aio.py`" (echoed as a contradiction in the research brief) | **`packages/matriz-client/src/matriz_client/aio.py` exists** and exports 24 public names including a full `AsyncClient`. CONTEXT.md's D-08 (matriz has both) is **correct**; CLAUDE.md is **stale**. | Resolves the contradiction flagged in the research brief. Do not plan around a missing matriz `aio.py`. |
| C-8 | (not mentioned anywhere) | **CI is currently RED.** `mypy (tests por paquete)` fails on matriz (29), higyrus (2), ambito (2). Last CI run: 2026-08-18. Phases 29/30/31 never CI-validated. | **Blocks success criterion 5.** See § The Criterion-5 Blocker. |

---

## The Criterion-5 Blocker (unbudgeted work)

Success criterion 5 requires "la matriz completa de CI (6 paquetes × py3.12 + py3.13) verde con los
gates nuevos activos". Measured baseline of every CI job today:

| CI job / step | Status | Detail |
|---|---|---|
| `lint` · `uv lock --check` | PASS | `Resolved 48 packages` |
| `lint` · `ruff check .` | PASS | `All checks passed!` |
| `lint` · `ruff format --check .` | PASS | `231 files already formatted` |
| `lint` · `lint-imports` | PASS | `Contracts: 5 kept, 0 broken.` |
| `lint` · `lint-logging` grep | PASS | no matches in `packages/*/src/` |
| `lint` · `decode-intactness` | PASS | Checks A–D all green; digest `ac14868282ad0a5c` matches `CANONICAL_DIGEST` |
| `lint` · `uniform-structure` | PASS | all 6 packages carry `models.py` + `types.py` |
| `typecheck` · `mypy` (src global) | PASS | `Success: no issues found in 62 source files` |
| `typecheck` · **`mypy` (tests por paquete)** | **FAIL** | **33 errors across 3 of 6 packages** |
| `test` · all 6 packages | PASS | 1682 tests: ambito 200, wallets 4, iol 242, higyrus 236, market-data 573, matriz 427 |

Breakdown of the failing loop (locked mypy **1.20.2**, `uv lock --check` passes, so CI installs the
identical version):

| Package | Errors | Files | Error codes |
|---------|--------|-------|-------------|
| `matriz-client` | 29 | `tests/test_decode.py`, `tests/test_ws_decode_mode.py` | 20 × `attr-defined` (`"LogRecord" has no attribute …`), 6 × `comparison-overlap` (`Non-overlapping …`), 3 × `arg-type` |
| `higyrus-client` | 2 | `tests/test_decode.py` | 1 × `func-returns-value`, 1 × `unused-ignore` |
| `ambito-financiero-client` | 2 | `tests/test_decode.py` | 1 × `func-returns-value` (`SILENT_SINK(...)` only ever returns `None`), 1 × `unused-ignore` |

All failing files are Phase 29 artifacts (`git log` on them shows `fix(29): WR-01 …` / `fix(29):
WR-02 …`). The dominant class — `LogRecord has no attribute <custom>` — is the standard consequence
of `caplog`-based assertions on custom `LogRecord` attributes under `--strict`, and is fixed by
`getattr(record, "field")` or a typed cast, not by weakening config.

**Planner guidance:** treat this as a **Wave 0** prerequisite. It is genuinely out of the phase's
stated scope, but criterion 5 is unachievable without it, and it is far cheaper to fix here than to
discover during Phase 34's release CI. Flag it explicitly in the plan rather than silently folding
it in. Note the `paths-ignore: ["**.md"]` trigger in `ci.yml:6-8,11-13` means the recent docs-only
commits never fired CI — the red state has been invisible.

---

## Measured Surface Counts (resolves C-2)

Public names per module, `dir()` filtered by `__module__ == mod.__name__`, measured today:

| Package | client (incl. classes) | aio (incl. classes) | client (excl. classes) | aio (excl. classes) | CONTEXT D-08 |
|---------|---:|---:|---:|---:|---|
| `ambito_financiero_client` | 3 | 4 | 2 | 3 | 2/3 |
| `iol_client` | 7 | 8 | 6 | 7 | 6/7 |
| `higyrus_client` | 8 | 9 | 7 | 8 | 7/8 |
| `matriz_client` | 23 | 24 | 22 | 23 | 22/23 |
| `market_data_client` | 20 | 21 | 19 | 20 | 19/20 |
| `wallets_client` | 1 | 2 | 1 | 2 | 1/2 |

**D-08's integers are the "excl. classes" column.** Wallets matches in both columns only because it
has no `Client`/`AsyncClient` class at all.

The name-set delta is perfectly uniform and structural:

| Package | only in `client` | only in `aio` |
|---------|------------------|---------------|
| all five class-bearing packages | `{Client}` | `{AsyncClient, aclose}` |
| `wallets_client` | `{}` | `{aclose}` |

There is **no** module-level `close` shim on any sync surface — `aclose` genuinely has no sync
counterpart at module level. A name-set parity assertion therefore needs exactly two sanctioned
rules: `Client ↔ AsyncClient`, and `aclose` allowed as async-only.

### Class-level parity (a second, cleaner axis)

| Package | `Client` public methods | `AsyncClient` public methods | Delta |
|---------|---:|---:|---|
| `ambito_financiero_client` | 3 | 3 | `close` ↔ `aclose` |
| `iol_client` | 7 | 7 | `close` ↔ `aclose` |
| `higyrus_client` | 8 | 8 | `close` ↔ `aclose` |
| `matriz_client` | 23 | 23 | `close` ↔ `aclose` |
| `market_data_client` | 20 | 20 | `close` ↔ `aclose` |
| `wallets_client` | — | — | **no `Client`/`AsyncClient` pair exists** |

This axis is *stronger and cleaner* than the module-level one: the sets are equal-sized in all five
packages with a single sanctioned rename. Recommend asserting **both** axes. Note wallets must be
explicitly skipped on the class axis (with a stated reason), not silently — that is precisely the
Phase 15 WR-01/WR-02 vacuity failure mode.

---

## Sync/Async Parity: Measured Ground Truth (resolves C-3)

A naive `typing.get_type_hints(sync_fn) == typing.get_type_hints(async_fn)` over every shared
module-level non-class name yields:

| Package | shared names | divergences | detail |
|---------|---:|---:|--------|
| `ambito_financiero_client` | 2 | 1 | `configure()` param `http_client`: sync `httpx.Client \| None` vs async `httpx.AsyncClient \| None` |
| `iol_client` | 6 | 1 | same |
| `higyrus_client` | 7 | 1 | same |
| `matriz_client` | 22 | 1 | same |
| `market_data_client` | 19 | 1 | `configure()` param `http_client`: sync `httpx.Client \| None` vs async **`<MISSING>`** ← the D-09 drift |
| `wallets_client` | 1 | 0 | `configure(base_url, token)` — identical both sides |

**Five of the six divergences are correct behaviour.** The async surface *must* accept an
`httpx.AsyncClient`. Only market-data's is a defect, and it is defective in a different way (missing
entirely, not type-shifted).

Consequently the parity helper needs a **normalization rule table**, exactly analogous to the eight
numbered rules in `check_decode_intactness.py`'s docstring. Minimum viable rule set:

1. `httpx.Client` in a sync hint ≡ `httpx.AsyncClient` in the corresponding async hint.
2. Name `Client` on the sync side ≡ `AsyncClient` on the async side.
3. `aclose` (module and method) is async-only; `close` is sync-only.
4. Return types: async functions annotate the *awaited* type, so `-> Cotizacion` on both sides is
   already correct — no rule needed. (Verified: no `Coroutine`/`Awaitable` annotations appear.)

Anything beyond these four is drift. Recording them as an explicit, commented table is what keeps
the test from being weakened ad-hoc later.

**Non-vacuity guard proven safe:** `typing.get_type_hints()` resolved successfully on **347 of 347**
public callables across all twelve modules — **zero** failures. There is no `TYPE_CHECKING`-only
import that would make the helper silently skip a function. [VERIFIED: executed]

---

## Gate Simulation Results (validates D-03 and D-04)

I implemented and ran a faithful simulation of the proposed `tools/check_surface_types.py`:
resolve each package's `__all__` → definition site via the explicit `ImportFrom` statements in
`__init__.py` → walk module-level `FunctionDef`/`AsyncFunctionDef` **and** the body of every
exported `ClassDef` → flag any return annotation containing `Any`.

```
TOTAL defs scanned across 6 packages: 319
NON-EXEMPT HITS (gate would FAIL on these): 0
EXEMPTED hits: 22   →   dunder: 12, to_dict: 9, underscore: 1
```

**Every `__all__` name in all six packages resolved to a definition site** — no unresolved names, no
star-imports, no dynamic exports. AST-only resolution is sound.

### The 22 exempted hits, exhaustively

| Reason | Count | Exact members |
|--------|------:|---------------|
| `to_dict()` serialize-out | 9 | `iol_client.SafeModel.to_dict`, `higyrus_client.SafeModel.to_dict`, and market-data's `LatestRequest`, `NewSymbol`, `NewSymbols`, `SymbolPatch`, `MarketHoursIn`, `HolidayIn`, `HolidaysIn` |
| dunder | 12 | `__reduce__` × 5 pairs-ish and `__deepcopy__` — specifically: ambito `Client`/`AsyncClient` `__reduce__`+`__deepcopy__` (4), higyrus same (4), iol `Client`/`AsyncClient` `__reduce__` (2), matriz `Client`/`AsyncClient` `__reduce__` (2) |
| `_`-prefixed helper | 1 | `matriz_client.Client._matriz_legacy_request` → `dict[str, Any]` |

Two subtleties the planner must encode:

- **`to_dict` is defined 10 times but only 9 are `__all__`-reachable.** `market_data_client.models.SafeModel`
  is *not* in `__all__` (its 7 request subclasses are, and each defines its own `to_dict`). By
  contrast iol's and higyrus's `SafeModel` **are** in `__all__`. The count 9 in criterion 1 is
  correct — but only under `__all__`-scoped resolution. A gate that walked `models.py` wholesale
  would report 10 and the criterion's number would look wrong.
- **`_matriz_legacy_request` is reachable only as a *method*.** No `__all__` in any package contains
  a single underscore-prefixed name (verified across all six). The module-level
  `matriz_client.client._matriz_legacy_request` is therefore invisible to an `__all__`-scoped gate;
  it is the *method* `Client._matriz_legacy_request` that the gate reaches — which is exactly D-03's
  argument for walking exported-class bodies, and is direct empirical proof that D-03 is right.

### Injectable-root feasibility (D-04)

Confirmed: both existing gates hardcode `REPO_ROOT = Path(__file__).resolve().parent.parent` at
module level (`check_uniform_structure.py:59`, `check_decode_intactness.py:129`) and neither has a
test. `tools/` has **no `__init__.py`** but is importable as an implicit namespace package thanks to
`pythonpath = ["."]`:

```
$ uv run python -c "import tools.check_uniform_structure as m; print('import OK', m.REPO_ROOT)"
import OK /Users/admin/development/market-libs
```

`uv run mypy tools/check_uniform_structure.py` also succeeds today, so a `tools/`-resident module
typechecks cleanly under strict mode when pulled in by a package test. Note `tools/*.py` is **not**
in mypy's global `files` (which covers `packages/*/src` only), so it is unchecked *unless* a
package test imports it — which the D-04 RED fixture will do, thereby enrolling it. That is a
desirable side effect worth stating in the plan.

---

## D-16: Measured State of the 4 Lists

| # | List | Location (corrected) | Current state | Work required |
|---|------|---------------------|---------------|---------------|
| 1 | mypy `files` | `pyproject.toml:97` | 5 packages — **`packages/market-data-client/src` absent** | **The one real code edit.** Zero-fix: verified `Success: no issues found in 75 source files` with it added |
| 2 | import-linter `root_packages` | `pyproject.toml:147-153` | 5 entries, **includes `market_data_client`** | None. Contract at `:182-186` exists and is KEPT |
| 3 | `ci.yml` mypy-tests loop | `.github/workflows/ci.yml:95` | 6 packages, complete | None |
| 4 | `verification/test_public_surface._PACKAGES` | `verification/test_public_surface.py:46-51` | 4 entries | Inline comment only (D-11) |

**Deliverables that remain:** (a) the `files` one-liner; (b) the import-linter RED proof; (c) the
`_PACKAGES` comment referencing `packages/market-data-client/tests/test_public_surface_market_data.py`;
(d) the explicit written rationale for wallets' exclusion (D-10).

For (d) there is a ready-made precedent to mirror: `check_decode_intactness.py:188-201` encodes
wallets' exemption as a **typed `ExemptPackage` dataclass carrying `reason` and `resolved_by`
fields**, pointing at `.planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md`. Notably its
`resolved_by` string already reads *"…with enrollment settled by **Phase 32's D-16 reconciliation**"* —
i.e. this phase is the named resolver of that pointer, and D-10's decision should be written back
there so the forward reference does not dangle.

---

## Standard Stack

No new dependencies. Everything this phase needs is installed, locked, and already used by CI.

### Core

| Tool | Version (verified) | Purpose | Why standard here |
|------|--------------------|---------|-------------------|
| `ast` (stdlib) | py3.12.13 | Surface gate parsing | Mandated stdlib-only by D-12/Phase 31; both existing gates use it [VERIFIED: `uv run python --version`] |
| `typing.get_type_hints` (stdlib) | py3.12.13 | Parity hint resolution | Only correct primitive under `from __future__ import annotations`; 347/347 resolve [VERIFIED] |
| `inspect` (stdlib) | py3.12.13 | Callable classification | Already used by `verification/test_public_surface.py:56-71` |
| `pytest` | 9.0.3 | Both RED fixtures | Runs in the 6×2 matrix [VERIFIED: `pytest --version`] |
| `mypy` | 1.20.2 (locked) | `typecheck` job | Pinned in `uv.lock:589-591`; floor is `>=1.13` [VERIFIED] |
| `ruff` | 0.15.12 | `lint` job | [VERIFIED: `ruff --version`] |
| `import-linter` | 2.11 | Boundary contracts | `pyproject.toml:33` pins `>=2.11,<3` [VERIFIED] |
| `grimp` | 3.14 | import-linter graph engine | Rust core — source of the ~0.07 s runtime that corrects C-1 [VERIFIED: `importlib.metadata.version`] |
| `uv` | 0.11.3 | Workspace/runner | [VERIFIED: `uv --version`] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ast` for the surface gate | Runtime import + `inspect` | Would execute `load_dotenv()` and client construction at gate time — both existing `tools/` gates reject this explicitly in their docstrings. Do not. |
| `get_type_hints()` for parity | raw `__annotations__` | Returns unresolved **strings** under PEP 563, making `httpx.Client` vs `httpx.AsyncClient` a string compare and silently missing alias/import differences. Do not. |
| `inspect.signature()` for parity | — | Order-**sensitive**; market-data's async `configure` reorders `base_url` from position 1 to 5 relative to sync. Since all params are keyword-only this reordering is semantically irrelevant, so a signature compare would fire a false positive. `get_type_hints()` returns a dict and is order-insensitive — **this is a concrete reason to prefer it**. |
| Subprocess `mypy` for the RED proof | in-suite `type: ignore` assertion | Phase 30 D-10 already rejected subprocess-mypy; `test_typed_surface_red.py` uses the `warn_unused_ignores` self-invalidating trick instead. Reuse that idea where applicable. |

## Package Legitimacy Audit

**Not applicable — this phase installs zero external packages.** Every tool it uses is either Python
stdlib or already present in the committed `uv.lock` and exercised by CI today. `uv lock --check`
passes, so no lockfile movement is required or expected.

Per CLAUDE.md, any lockfile change would move `uv.lock` and force a `uv lock --check` re-validation
in the `lint` job's first step; the stdlib-only constraint (D-12/Phase 31, restated in
`check_uniform_structure.py:36-41`) exists precisely to avoid this.

---

## Architecture Patterns

### System Architecture Diagram

```
                        ┌─────────────────────────────────────┐
                        │      git push / pull_request        │
                        │  (paths-ignore: **.md, .gitignore)  │
                        └──────────────┬──────────────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
   ┌─────────────────┐        ┌─────────────────┐       ┌──────────────────────┐
   │  job: lint      │        │ job: typecheck  │       │ job: test (6×2 matrix)│
   │  (single run)   │        │  (single run)   │       │  py3.12 + py3.13      │
   └────────┬────────┘        └────────┬────────┘       └──────────┬────────────┘
            │                          │                            │
   ruff check                  mypy (src global)          pytest packages/<pkg>
   ruff format --check           ├─ files = 5 pkgs                  │
   lint-imports ◄──── contracts  │  ▲ D-16 EDIT: +market-data       │
   lint-logging (grep)           │                                  │
   decode-intactness             mypy (tests per package)           │
   uniform-structure               ▲ 33 ERRORS TODAY (blocker)      │
   ══════════════════                                               │
   ► check_surface_types.py  ◄── NEW STEP (D-05, after line 60)     │
       │                                                            │
       │  reads packages/*/src/*/__init__.py  (AST only, no import) │
       │       └─► __all__ → ImportFrom → defsite module            │
       │              └─► module funcs + exported class bodies      │
       │                     └─► return annotation contains "Any"?  │
       │                            └─► exempt? (dunder/_/to_dict)  │
       │                                   └─► ::error:: + exit 1   │
       │                                                            │
       └── check_surface_types(root: Path) ◄── injectable seam ─────┤
                    ▲                                               │
                    │                                    ┌──────────▼──────────┐
                    └──── RED fixture (tmp_path tree) ───┤ packages/<pkg>/tests│
                                                         │  ├ surface RED      │
                                                         │  ├ parity test ×6 ──┼──┐
                                                         │  └ import-linter RED│  │
                                                         └─────────────────────┘  │
                                                                                  │
                            shared parity helper (tools/ or verification/) ◄──────┘
                                    │  imports <pkg>.client + <pkg>.aio (runtime)
                                    │  dir() filter by __module__
                                    │  get_type_hints() both sides
                                    │  apply normalization rules (httpx.Client↔AsyncClient,
                                    │       Client↔AsyncClient, close/aclose)
                                    └─► assert names_equal AND hints_equal AND count >= LOWER_BOUND
```

### Recommended Structure

```
tools/
├── check_decode_intactness.py     # existing template (docstring, ::error::, roster)
├── check_uniform_structure.py     # existing template (simpler, closer fit)
├── check_surface_types.py         # NEW — gate, with check_surface_types(root: Path)
└── surface_parity.py              # NEW — shared introspection helper (D-07)

packages/<pkg>/tests/
├── test_surface_parity.py         # NEW ×6 — thin, delegates to tools.surface_parity
└── (one package only) test_surface_types_red.py     # NEW — D-04 RED fixture
└── (market-data only) test_core_boundary_red.py     # NEW — D-02 import-linter RED

verification/test_public_surface.py  # comment only, list untouched (D-11)
pyproject.toml:97                    # +packages/market-data-client/src
.github/workflows/ci.yml             # +1 step after line 60
```

### Pattern 1 — `tools/` gate skeleton (copy `check_uniform_structure.py`)

`check_uniform_structure.py` is the better template than `check_decode_intactness.py`: it is 166
lines, single-check, and already encodes the anti-vacuity discipline this phase needs.

```python
# Source: tools/check_uniform_structure.py:71-77, 136-161 (verbatim structure)
class CheckFailure(Exception):
    """Raised by a check with a fully formed, operator-readable message."""


def _fail(message: str) -> CheckFailure:
    return CheckFailure(message)


def main() -> int:
    checks = (check_surface_types,)          # tuple of zero-arg callables
    failures = 0
    for check in checks:
        try:
            print(check())                   # success message on stdout
        except CheckFailure as exc:
            failures += 1
            print(f"::error::Phase 32 GATE-TYP-01 surface types -- {exc}", file=sys.stderr)
    if failures:
        print(
            f"::error::surface-types gate FAILED ({failures} of {len(checks)} checks)",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Four conventions to carry over verbatim, all present in both existing gates:

1. **Roster from disk, never hardcoded.** `check_uniform_structure.py:43-51` documents this as a
   design rule: a seventh package must be checked automatically, "rather than silently exempted by
   omission (criterion 4)".
2. **Unresolvable is a *problem*, never a *skip*** — `check_uniform_structure.py:120-127`.
3. **An empty scan is itself a failure** — `check_uniform_structure.py:106-118`. This is the
   anti-vacuity primitive; the surface gate's analogue is "zero `__all__` names resolved" and "zero
   definitions scanned" (my simulation scanned 319 — a natural lower bound).
4. **A `WHY THIS IS A `tools/` SCRIPT IN THE `lint` JOB` docstring section** —
   `check_uniform_structure.py:21-34` spells out both rejected alternatives. D-05's roadmap
   contradiction should be recorded in exactly this slot.

### Pattern 2 — `__all__` → definition site via explicit `ImportFrom`

Verified sound: 100% of `__all__` names in all six packages resolve.

```python
# Verified against all 6 packages today (0 unresolved names)
init_tree = ast.parse((root / "packages" / d / "src" / m / "__init__.py").read_text())
site: dict[str, str] = {}
for node in ast.walk(init_tree):
    if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(f"{m}."):
        submodule = node.module.split(".", 1)[1]        # "client", "models", "ws_client", ...
        for alias in node.names:
            site[alias.asname or alias.name] = submodule
```

Note `matriz_client/__init__.py` imports from **8** distinct submodules including `ws_client` and
`types`, and both matriz and higyrus have **two separate `ImportFrom` blocks from `.client`** —
`ast.walk` handles this naturally; a "first match wins" shortcut would not.

`__all__` itself must be read from the AST too (not by importing the package). All six define it as
a plain module-level list literal.

### Pattern 3 — non-vacuous parity assertion (lower + upper bound)

Directly modelled on `verification/test_main_matriz_uses_single_client_instance.py:97-99`, whose
docstring states the principle: *"Lower bound (>=1) is the non-vacuity guard: the un-migrated driver
constructs zero classes … and so FAILS RED."*

```python
# Per-package literal bounds (D-08). NOTE the metric: module-level public names
# EXCLUDING the Client/AsyncClient class. See § Measured Surface Counts.
_LOWER_BOUNDS = {
    "ambito_financiero_client": (2, 3),
    "iol_client": (6, 7),
    "higyrus_client": (7, 8),
    "matriz_client": (22, 23),
    "market_data_client": (19, 20),
    # wallets_client is a near-vacuous floor BY CONSTRUCTION: its only public
    # module-level name is `configure` (sync) / `configure` + `aclose` (async).
    # It is the one pre-Phase-7 package -- no Client/AsyncClient class pair at
    # all -- so this bound asserts almost nothing and MUST NOT be read as
    # coverage. Raising it is the job of the phase that gives wallets a Client.
    "wallets_client": (1, 2),
}
```

The wallets comment is not decoration — D-08 explicitly requires the near-vacuity be "documentado
como tal, no ocultado detrás de un número que parece robusto."

### Pattern 4 — the `ResourceWarning` async-configure precedent (settles the D-09 fix)

The obvious objection to adding `http_client` to `market_data_client.aio.configure` is that
`configure` is a **plain `def`, not `async def`**, in every `aio.py` — so it cannot `await
old_client.aclose()` before swapping. The sync `client.configure` *does* close the old one
(`client.py`, `state.http_client.close()`).

**This is already solved, uniformly, in 4 of the 5 other packages.** matriz and iol emit a
`ResourceWarning` instead of closing:

```python
# Source: packages/matriz-client/src/matriz_client/aio.py:805-814 (verbatim)
    if http_client is not None:
        if client._state.http_client is not None and client._state.http_client is not http_client:
            warnings.warn(
                "matriz_client.aio.configure(): replacing a live httpx.AsyncClient "
                "(via http_client=) without awaiting aclose() leaks the connection "
                "pool. Call `await matriz_client.aio.aclose()` before configure(...).",
                ResourceWarning,
                stacklevel=2,
            )
        client._state.http_client = http_client
```

(higyrus and ambito instead thread `http_client=` into a rebuild path — a second valid shape.)

Blast radius of applying this to market-data is small and fully precedented:
- `AsyncClient.__init__` at `aio.py:119` **already accepts** `http_client: httpx.AsyncClient | None`
  and assigns it at `:155-156`.
- `_ClientState.http_client` is typed `httpx.Client | httpx.AsyncClient | None`
  (`_state.py:119`) — no type change needed.
- `aio.aclose()` at `:184-188` already asserts `isinstance(..., httpx.AsyncClient)` and awaits.
- Purely **additive** keyword-only parameter → not source-breaking → no semver major implication for
  the Phase 34 re-publish (still a minor-worthy surface addition to note in the changelog).

This materially strengthens the case for Claude's-Discretion option **(1) fix it**, which CONTEXT
already recommended pending planning confirmation.

### Anti-Patterns to Avoid

- **Comparing `__all__` between `client.py` and `aio.py`.** Half the modules lack it; the test
  passes as `[] == []`. This is D-06 and it is the literal Phase 15 WR-01/WR-02 failure mode.
- **Raw `hs == ha` on `get_type_hints()`.** Red in all 6 packages on day one (§ C-3).
- **`inspect.signature()` equality.** False-positives on market-data's keyword-only param reordering.
- **Importing package modules inside the `tools/` gate.** Triggers `load_dotenv()` and client
  construction. Both existing gates call this out explicitly.
- **A uniform numeric threshold for lower bounds.** D-08 forbids it; wallets(1) and matriz(22) differ
  by 22×.
- **Hardcoding the package roster in the new gate.** `check_uniform_structure.py:43-51` documents
  why: a seventh package must not be exempted by omission.
- **Silently skipping wallets on the class-parity axis.** It has no `Client`/`AsyncClient` at all —
  skip it *loudly*, with an asserted reason.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Resolving PEP 563 string annotations | Manual `eval()` of `__annotations__` with hand-built globalns | `typing.get_type_hints(fn)` | Handles module globals, `TYPE_CHECKING` blocks, and `X \| None` normalization. Verified 347/347 success. |
| Import-boundary checking | Custom AST import walker | `import-linter` `forbidden` contracts (already configured) | 5 contracts exist and are KEPT; grimp does the graph in ~0.07 s |
| Detecting a "kind" for a public object | `type(obj).__name__` switch | `verification/test_public_surface.py:56-71` `_kind()` | Already solved, incl. the `iscoroutinefunction` **before** `isfunction` ordering trap |
| `inspect.signature` on non-introspectable objects | bare call | `_stringify_signature()` wrapper at `verification/test_public_surface.py:74-85` | Catches `TypeError`/`ValueError` on `typing.Literal` aliases and C callables |
| Normalizing per-package legitimate differences | ad-hoc `if pkg == "matriz"` branches | An explicit numbered rule table in the module docstring | `check_decode_intactness.py:44-82` — "A red gate means a copy drifted; the fix is to revert the drift or to add a rule here with a stated reason — never to weaken the check into a vacuous one." |
| Recording a package exemption | a comment | typed `ExemptPackage(package, reason, resolved_by)` dataclass | `check_decode_intactness.py:162-201` — machine-visible, and Check D fails if the exempt package acquires the artifact |
| Proving a `type: ignore`-based RED fixture stays live | periodic manual review | `warn_unused_ignores = true` self-invalidation | `packages/iol-client/tests/test_typed_surface_red.py:21-41` — "The ignore is the *assertion*, not a suppression… it cannot rot into a no-op" |

**Key insight:** every primitive this phase needs already exists in this repo, written by earlier
phases, with the rationale recorded in a docstring. The phase is an assembly job, not an invention
job. The single genuinely new thing is the `httpx.Client ↔ AsyncClient` normalization rule.

---

## Common Pitfalls

### Pitfall 1: Assuming `lint-imports` is slow (kills the automated RED proof for no reason)
**What goes wrong:** CONTEXT.md's D-02 states the subprocess route costs "decenas de segundos",
steering the plan to a manual demonstration.
**Reality:** measured 0.07 s, three consecutive `subprocess.run` invocations, with **no**
`.grimp_cache` present in the repo. import-linter 2.11 / grimp 3.14 has a Rust core.
**How to avoid:** budget the automated subprocess RED test; it is affordable.
**Warning signs:** a plan that cites cost as the reason for choosing manual demonstration.

### Pitfall 2: The parity test goes red in all six packages on day one
**What goes wrong:** raw hint equality flags the correct `httpx.Client`/`httpx.AsyncClient`
asymmetry as drift in five packages, drowning the one genuine finding.
**Why:** the async surface must take an `AsyncClient` — this is required correctness, not drift.
**How to avoid:** implement the four normalization rules (§ Sync/Async Parity) *before* wiring the
test into CI.
**Warning signs:** a task that says "assert `get_type_hints(sync) == get_type_hints(async)`" with no
normalization step.

### Pitfall 3: `__annotations__` instead of `get_type_hints()`
**What goes wrong:** every module carries `from __future__ import annotations` (mandatory per
CLAUDE.md), so `__annotations__` yields **strings**. `"httpx.Client | None"` vs
`"httpx.AsyncClient | None"` compares as unequal strings while `"Cotizacion"` vs
`"models.Cotizacion"` compares unequal despite being the same type.
**How to avoid:** always `typing.get_type_hints()`.
**Warning signs:** string comparison of annotations anywhere in the helper.

### Pitfall 4: D-06 and D-08 use different metrics (off-by-one in 5 of 6 packages)
**What goes wrong:** D-06 prescribes `dir()` filtered by `__module__` (**includes** `Client`);
D-08's integers are the class-**excluded** counts. Implementing D-06 literally and pinning D-08's
numbers fails by exactly 1 everywhere except wallets.
**How to avoid:** state the metric in one place in the helper docstring and derive both. Both column
sets are tabulated in § Measured Surface Counts.
**Warning signs:** bounds and extraction written in different tasks/waves without a shared helper.

### Pitfall 5: Assuming matriz has no `aio.py`
**What goes wrong:** CLAUDE.md's Architecture section says "No async support in matriz". It is
**stale**. `packages/matriz-client/src/matriz_client/aio.py` exists with 24 public names and a full
`AsyncClient` (23 public methods).
**How to avoid:** matriz is a full participant in the 6-package parity matrix.
**Warning signs:** any plan with 5 parity test files instead of 6.

### Pitfall 6: The AST gate must parse PEP 695 generic syntax
**What goes wrong:** all five `_decode.py` copies contain
`def _response_parser[**P, R](fn: Callable[P, R]) -> Callable[P, R]:` (PEP 695), a **syntax error**
on Python ≤3.11. A system `python3` (3.9 on this machine) crashes the gate with `SyntaxError`.
**How to avoid:** always invoke via `uv run python tools/check_surface_types.py`, mirroring
`ci.yml:55` and `:60`. `requires-python = ">=3.12"` guarantees the interpreter.
**Warning signs:** a bare `python tools/...` in a CI step or pre-commit hook.

### Pitfall 7: Silently skipping wallets on the class-parity axis
**What goes wrong:** wallets has **no** `Client`/`AsyncClient` pair. A `getattr(mod, "Client", None)`
guard that returns early makes wallets pass vacuously — the exact WR-01/WR-02 pattern.
**How to avoid:** assert the absence explicitly (`assert not hasattr(client_mod, "Client")`) so the
day wallets *gains* a `Client`, the skip fails and forces enrollment. Same shape as Check D in
`check_decode_intactness.py:635-641` ("exempt package has acquired a `_decode.py`").
**Warning signs:** `if Client is None: return` with no assertion.

### Pitfall 8: Treating criterion 5 as free
**What goes wrong:** 33 pre-existing mypy errors block the `typecheck` job. Discovered only when the
phase's PR opens.
**How to avoid:** budget Wave 0 for it. See § The Criterion-5 Blocker.
**Warning signs:** a plan whose only CI-green task is "verify CI passes".

### Pitfall 9: The `_request` exemption is dead letter as written
**What goes wrong:** effort spent implementing an exemption that can never fire.
**Why:** no `_request` returns `Any`/`dict[str, Any]` *and* is reachable from `__all__`. Method-form
`_request` returns `httpx.Response` (not a candidate under the literal rule); module-form `_request`
is `_`-prefixed and absent from every `__all__`.
**How to avoid:** either drop it, or decide deliberately that the gate has a *second* rule banning
raw `httpx.Response` on the exported surface — in which case the exemption becomes load-bearing. See
OQ-2.

---

## Runtime State Inventory

Included because D-16 is a configuration-list reconciliation — the failure mode is state that lives
outside the files being edited.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | **None** — no database, cache or datastore keyed on package names. `iol_client/_token_cache.py` stores auth tokens on disk but is keyed on credentials, not package identity. | None |
| Live service config | **GitHub Actions only.** No branch protection / required-status-check names were inspected — if `lint` or `typecheck` are named required checks, **adding a step does not change the job name**, so no settings update is needed (this is a further argument for D-05's step-in-`lint` over a new job, which *would* need the check name registering). | Verify no new required check is implied |
| OS-registered state | **None** — no scheduled tasks, daemons or services. | None |
| Secrets / env vars | **None touched.** Per-package `.env` files exist (higyrus, matriz) and `.env.example` templates are committed. Gates are static/import-only and must never read them. | None — but assert no credential access in the new code |
| Build artifacts | **`*.egg-info` directories exist** under `packages/*/src/`. `check_uniform_structure.py:68` already filters `_BUILD_ARTIFACT_SUFFIX = ".egg-info"` when resolving import roots — **the new gate must do the same** or it will find 2 candidate directories and report an unresolvable import root. Also `__pycache__` dirs are present under every `src/<pkg>/` and under `tools/`. | Reuse the `.egg-info` filter verbatim |
| Uncommitted working state | `.gsd/` and 4 files under `.planning/research/.cache/` are untracked; `uv.lock` is clean and `uv lock --check` passes. | None |

---

## Code Examples

### Reading `__all__` from AST without importing the package

```python
# Every one of the 6 packages defines __all__ as a plain module-level list literal.
def _all_names(init_tree: ast.Module) -> list[str]:
    for node in init_tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else (
            [node.target] if isinstance(node, ast.AnnAssign) else []
        )
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                value = node.value
                if not isinstance(value, (ast.List, ast.Tuple)):
                    raise _fail("__all__ is not a list/tuple literal")
                return [
                    el.value for el in value.elts
                    if isinstance(el, ast.Constant) and isinstance(el.value, str)
                ]
    raise _fail("no module-level __all__ found")   # a problem, never a skip
```

### The exemption predicate (matches the measured taxonomy exactly)

```python
def _is_exempt(name: str) -> str | None:
    """Return the DT-06 exemption reason, or None if the def is in scope."""
    if name.startswith("__") and name.endswith("__"):
        return "dunder"          # 12 hits today: __reduce__, __deepcopy__, __getattr__
    if name.startswith("_"):
        return "private-helper"  # 1 hit today: matriz Client._matriz_legacy_request
    if name == "to_dict":
        return "serialize-out"   # 9 hits today (see the exhaustive list in RESEARCH)
    return None
```

### Injectable root (the D-04 seam) with a `tmp_path` RED fixture

```python
# tools/check_surface_types.py
REPO_ROOT = Path(__file__).resolve().parent.parent   # default only

def check_surface_types(root: Path = REPO_ROOT) -> str:
    ...

def main() -> int:
    ...   # calls check_surface_types() with the default
```

```python
# packages/<pkg>/tests/test_surface_types_red.py  -- D-04 RED fixture
from tools.check_surface_types import CheckFailure, check_surface_types


def test_gate_is_green_on_the_real_tree() -> None:
    """Upper bound: today's tree has zero non-exempt hits."""
    assert "0 violation" in check_surface_types()


def test_gate_fails_on_an_injected_regression(tmp_path: Path) -> None:
    """Lower bound (non-vacuity): a deliberately broken tree MUST fail RED."""
    pkg = tmp_path / "packages" / "fake-client" / "src" / "fake_client"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        "from fake_client.client import get_thing\n__all__ = ['get_thing']\n"
    )
    (pkg / "client.py").write_text(
        "from typing import Any\ndef get_thing() -> dict[str, Any]: ...\n"
    )
    with pytest.raises(CheckFailure, match="get_thing"):
        check_surface_types(root=tmp_path)
```

`tmp_path` is recommended over committed fixture files: nothing new lands under `packages/` (which
would trip `check_decode_intactness.py`'s Check D roster and `check_uniform_structure.py`'s
`models.py`/`types.py` requirement), and the regression is visible inline in the test.

### import-linter RED proof by subprocess (~0.07 s, per Pitfall 1)

```python
def test_core_boundary_contract_is_red_when_violated(tmp_path: Path) -> None:
    """D-02: prove the market_data_client._core contract actually catches a violation."""
    core = Path("packages/market-data-client/src/market_data_client/_core.py")
    original = core.read_text(encoding="utf-8")
    try:
        core.write_text(original + "\nfrom market_data_client import client  # noqa: F401\n")
        result = subprocess.run(["uv", "run", "lint-imports"], capture_output=True, text=True)
        assert result.returncode != 0
        assert "market_data_client._core does not depend on transport modules BROKEN" in result.stdout
    finally:
        core.write_text(original, encoding="utf-8")
```

Caveat: this mutates a tracked file inside a `try/finally`. If the plan prefers no mutation of
tracked source, the alternative is to copy the tree to `tmp_path` with a generated
`.importlinter` config — more machinery, but no risk of leaving a dirty tree if the process is
killed mid-test. Flagged as OQ-3.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Codegen sync/async (REFAC-06, `unasync`, then `libcst`) | **Affirmative introspection test** | DT-04; two signed NO-GOs (SPIKE-005 v1.2/Phase 12, SPIKE-006 v1.3/Phase 18) | The parity test *is* the substitute deliverable — DT-09 makes it first-class, not nice-to-have |
| Gates as new CI jobs | Steps in the existing `lint` job | Phase 31 D-12 | D-05; overrides `ROADMAP.md:25` prose |
| Snapshot files in `verification/` | In-package tests in the 6×2 matrix | Phase 25 onward | `verification/` has **never** executed in CI |
| Byte-comparing copies | Normalize-then-hash with a numbered rule table | Phase 29 DEC-01 | The design template for the parity normalization rules |
| Mutual-agreement hashing | Mutual agreement **+ a pinned canonical digest** | Phase 29 code review WR-07 | A uniform edit across all copies passes a mutual check vacuously — the general lesson for every gate this phase writes |
| `dict[str, Any]` returns on the public surface | Typed models via `SafeModel` | Phases 29-31 | Why the gate finds 0 violations today — it is a *ratchet*, not a migration tool |

**Deprecated / stale in-repo documentation (flag, do not fix — out of scope per CONTEXT):**
- `CLAUDE.md` — "No async support in matriz: `matriz_client` has no `aio.py`" → **false**
- `CLAUDE.md` — "No wildcard imports" is correct, but the research brief's reading of star-imports in
  `__init__.py` is not supported: all six use explicit `ImportFrom` (D-03 is right)
- `ROADMAP.md:25` — "job de CI nuevo" → superseded by D-05/Phase 31 D-12
- `ROADMAP.md:181` / `tipado_homogeneo.md:137` — "`ci.yml:85`" → the loop is at **line 95**
- `tipado_homogeneo.md:137` — "`root_packages` de import-linter (hoy 4)" → **5** today (Phase 31 WR-05)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The 33 mypy errors are fixable by editing test code only (no `pyproject.toml` strictness relaxation) | Criterion-5 Blocker | If a config change is needed, that is a policy decision requiring user sign-off, not a mechanical fix |
| A2 | GitHub branch protection does not name a required status check that a new `lint` step would alter | Runtime State Inventory | Not inspected (needs repo admin API). Low risk — adding a *step* does not rename the *job* |
| A3 | Adding `http_client` to `market_data_client.aio.configure` is purely additive and not source-breaking | Pattern 4 | If a consumer subclasses/wraps `configure` positionally it could break — but the param is keyword-only, so risk is near zero |
| A4 | The Phase 29 mypy errors were introduced by Phase 29 and are not a mypy-version regression | Criterion-5 Blocker | `uv.lock` last moved at `bd920c6` (pre-Phase-29) and CI was green on 2026-08-18 with the same pinned mypy 1.20.2, so the variable is the source, not the tool. An isolated cross-check with mypy 1.13 was inconclusive (workspace not installed in the isolated env). |
| A5 | `wallets_client/client.py:33-35` holds the module-level singletons cited by D-10 | D-10 verification | Only the *absence* of `_core.py` etc. was verified (which is the load-bearing half of D-10); the exact line span was not |

---

## Open Questions (RESOLVED)

1. **OQ-1 — Where does the shared parity helper live: `tools/` or `verification/`?**
   - What we know: both work. `tools/` is importable as a namespace package (no `__init__.py`) and
     `uv run mypy tools/check_uniform_structure.py` passes. `verification/` has `__init__.py` and is
     already imported by 8 package tests ("Patrón 1").
   - What's unclear: `verification/` carries the connotation "never runs in CI" — which is precisely
     the trap D-05/D-11 keep warning about, even though a *helper imported by an in-package test*
     does run.
   - **Recommendation: `tools/`.** It groups with the other two cross-package gates, matches Phase 31
     D-12's "stdlib-only cross-package tooling" precedent, and avoids placing CI-load-bearing code in
     a directory the codebase repeatedly documents as CI-invisible. Being pulled into the
     per-package mypy runs by the importing tests is a bonus (it is otherwise unchecked).

2. **OQ-2 — Does the surface gate ban raw `httpx.Response` on the exported surface, or only `Any`?**
   - What we know: criterion 1 lists `_request` returning `httpx.Response` among the exemptions,
     but under an `Any`-only rule no `_request` is ever a candidate (§ C-6, Pitfall 9).
   - What's unclear: whether DT-06's author intended a second rule.
   - **Recommendation:** implement the `Any`-only rule (the literal criterion) and keep the
     `_`-prefix exemption, which subsumes every `_request`. Note in the gate docstring that the
     `_request`/`httpx.Response` clause of DT-06 is subsumed and therefore not separately coded, so a
     future reader does not think it was forgotten.

3. **OQ-3 — Does the import-linter RED test mutate a tracked file, or build a tmp tree?**
   - What we know: mutating `_core.py` inside `try/finally` is ~6 lines and ~0.07 s; a tmp-tree copy
     with a generated config is ~30 lines and needs an `.importlinter` file.
   - What's unclear: tolerance for a test that could leave a dirty tree if SIGKILLed.
   - **Recommendation:** the `try/finally` mutation, guarded by a `monkeypatch`-free explicit restore
     and marked with a comment. Cheap, and the failure mode (dirty tree) is loud and trivially
     recovered with `git checkout`. If the planner disagrees, the tmp-tree variant is the safe
     fallback — decide once, in the plan.

4. **OQ-4 — Does Wave 0 (33 mypy errors) belong in this phase or a separate fix?**
   - What we know: criterion 5 cannot pass without it. It is not in GATE-TYP-01's text.
   - **Recommendation:** include it as Wave 0 with an explicit note that it is pre-existing debt
     surfaced by research, not phase scope creep. Alternative: a `/gsd-quick` fix landed first, so
     the phase starts from green. Either is defensible; the plan must pick one and say so.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | Everything | ✓ | 0.11.3 | — |
| Python 3.12 | Gate AST (PEP 695), CI matrix | ✓ | 3.12.13 (active venv) | — |
| Python 3.13 | CI matrix leg | ✓ | 3.13.12 (uv-managed) | — |
| ruff | `lint` job | ✓ | 0.15.12 | — |
| mypy | `typecheck` job | ✓ | 1.20.2 (locked) | — |
| pytest | Both RED fixtures, parity tests | ✓ | 9.0.3 | — |
| pytest-asyncio | existing suites | ✓ | (locked, `asyncio_mode="auto"`) | — |
| import-linter | D-02 RED proof | ✓ | 2.11 | — |
| grimp | import-linter engine | ✓ | 3.14 | — |
| `gh` CLI | CI-history inspection (research only) | ✓ | authenticated | — |
| Network / live APIs | **not needed** | n/a | — | Phase 32 is entirely static + import-only; live verification is Phase 33 |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio (`asyncio_mode = "auto"`) |
| Config file | `pyproject.toml:102-120` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest packages/<pkg> -q` |
| Full suite command | `uv run pytest packages -q` (1682 tests) |
| CI per-leg command | `uv run --python <ver> pytest packages/<pkg> --cov=packages/<pkg>/src …` (`ci.yml:124-128`) |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | Exists? |
|-----|----------|-----------|-------------------|---------|
| GATE-TYP-01(a) | Gate reports green on today's clean tree | unit | `uv run python tools/check_surface_types.py` | ❌ Wave 1 |
| GATE-TYP-01(a) | Gate runs in real CI | CI step | new step in `ci.yml` `lint` after line 60 | ❌ Wave 1 |
| GATE-TYP-01(b) | Gate fails RED on an injected `dict[str, Any]` return | unit | `uv run pytest packages/<pkg>/tests/test_surface_types_red.py -x` | ❌ Wave 1 |
| GATE-TYP-01(b) | Parity names match, per package | unit | `uv run pytest packages/<pkg>/tests/test_surface_parity.py -x` | ❌ Wave 2 (×6) |
| GATE-TYP-01(b) | Parity hints match after normalization | unit | same file | ❌ Wave 2 |
| GATE-TYP-01(b) | Lower bound ≥ N per package (non-vacuity) | unit | same file | ❌ Wave 2 |
| GATE-TYP-01(b) | wallets' missing `Client` asserted, not skipped | unit | `packages/wallets-client/tests/test_surface_parity.py` | ❌ Wave 2 |
| GATE-TYP-01(c) | mypy covers market-data src globally | typecheck | `uv run mypy` → expect 75 files | ❌ Wave 3 (one-line) |
| GATE-TYP-01(c) | `_core` contract is RED-proven | integration | `uv run pytest packages/market-data-client/tests/test_core_boundary_red.py -x` | ❌ Wave 3 |
| GATE-TYP-01(c) | `_PACKAGES` rationale documented | manual/review | comment at `verification/test_public_surface.py:46` | ❌ Wave 3 |
| Criterion 5 | Full CI matrix green | CI | all jobs | ❌ **Wave 0 — 33 errors** |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/<pkg> -q` for the touched package, plus
  `uv run python tools/check_surface_types.py` when the gate is touched
- **Per wave merge:** `uv run ruff check . && uv run mypy && uv run pytest packages -q`
- **Phase gate:** every `ci.yml` job green, including the currently-red per-package mypy loop

### Wave 0 Gaps

- [ ] `packages/matriz-client/tests/test_decode.py` + `test_ws_decode_mode.py` — 29 mypy errors
- [ ] `packages/higyrus-client/tests/test_decode.py` — 2 mypy errors
- [ ] `packages/ambito-financiero-client/tests/test_decode.py` — 2 mypy errors
- [ ] No framework install needed — pytest/mypy/ruff all present and locked

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`. This phase adds **no runtime code paths, no
network I/O and no data handling** — it adds CI tooling and tests. The relevant surface is the
tooling itself.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | Gates never authenticate; no credential access |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No runtime authz surface |
| V5 Input Validation | **partially** | The gate's only input is repository source it already trusts. Still: parse with `ast.parse` (never `eval`/`exec`), and treat unparseable files as a **failure**, not a skip |
| V6 Cryptography | no | `hashlib.sha256` is used only as a content fingerprint in the existing decode gate; no new crypto |
| V7 Error Handling & Logging | **yes** | Gate failure messages embed file paths and source lines. They must never print a `.env` value — enforced by construction: the gate reads only `packages/*/src/**/*.py` |
| V12 Files & Resources | **yes** | The RED fixtures write to `tmp_path` (pytest-managed) or restore a tracked file in `finally` |
| V14 Configuration | **yes** | `pyproject.toml` / `ci.yml` edits — the phase's core deliverable |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Gate imports a package and triggers `load_dotenv()` + client construction | Information Disclosure | AST/text reads only — stated as a docstring invariant in both existing gates |
| Subprocess with shell interpolation of repo content | Tampering | Fixed argv list, `shell=False`. Precedent: `check_decode_intactness.py:366-386` — *"Fixed argv, no shell, no interpolated user input"* |
| A credential value leaking into a CI failure annotation | Information Disclosure | Gate scope excludes `.env`; failure messages print paths + source lines from `src/` only |
| RED test leaves a mutated tracked file on abnormal exit | Tampering / Integrity | `try/finally` restore, or prefer `tmp_path` (see OQ-3) |
| A weakened gate passing vacuously (the phase's own threat model) | Repudiation | Lower bounds + RED fixtures — the entire point of criteria 2 and 3 |

---

## Sources

### Primary (HIGH confidence — executed against the working tree today)
- `uv run mypy` / `mypy packages/*/tests` / `mypy packages/market-data-client/src` — enrollment and blocker findings
- `uv run lint-imports` (×5, incl. a cold run with `.grimp_cache` absent) — contract state and timing
- `uv run pytest packages/<pkg> -q` × 6 — 1682 tests green
- `uv run ruff check . && uv run ruff format --check .` — lint baseline
- `uv run python tools/check_decode_intactness.py`, `tools/check_uniform_structure.py` — gate baseline
- Custom AST + runtime introspection scripts (surface counts, parity deltas, gate simulation over 319 defs, `get_type_hints` on 347 callables)
- `gh run list --workflow=ci.yml` — last CI run 2026-08-18, all green
- File reads: `pyproject.toml`, `.github/workflows/ci.yml`, `tools/check_uniform_structure.py`, `tools/check_decode_intactness.py`, `verification/test_public_surface.py`, `verification/test_main_matriz_uses_single_client_instance.py`, `packages/iol-client/tests/test_typed_surface_red.py`, `packages/market-data-client/tests/test_public_surface_market_data.py`, market-data `client.py`/`aio.py` `configure`, matriz `aio.py:790-830`
- `.planning/ROADMAP.md` § Phase 32, `.planning/REQUIREMENTS.md` GATE-TYP-01, `.planning/future-plans/tipado_homogeneo.md` DT-04/DT-06/DT-09, `.planning/milestones/v1.2-phases/15-driver-migration-4-refac-05/15-REVIEW.md` WR-01

### Secondary (MEDIUM confidence)
- `.planning/config.json` — `nyquist_validation: true`, `security_enforcement: true`, ASVS L1
- `uv.lock` — mypy 1.20.2 pin, `>=1.13` floor

### Tertiary (LOW confidence)
- `CLAUDE.md` architecture section — **demonstrated stale** on matriz `aio.py`; treat as unreliable for this phase

No external web sources were consulted: every question was answerable from the repository itself, and
repository state is authoritative over any published documentation for this phase.

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — zero new dependencies; all versions read from the live environment
- Architecture / patterns: **HIGH** — every pattern extracted verbatim from a committed file with line refs
- Measured counts & parity deltas: **HIGH** — executed, reproducible scripts
- Pitfalls: **HIGH** — 8 of 9 observed directly; Pitfall 8 (criterion-5 blocker) reproduced end-to-end
- Criterion-5 blocker root cause: **MEDIUM-HIGH** — the failure is certain; the attribution to Phase 29 rests on `git log` provenance plus the 2026-08-18 green CI with an identical mypy pin (A4)
- Recommendations for the 4 discretion items: **HIGH** for D-02 (measured) and D-09 (4-package precedent); **MEDIUM** for helper location and RED-fixture mechanism (judgment calls with real tradeoffs)

**Research date:** 2026-08-25
**Valid until:** ~2026-09-24 (30 days) — but **invalidated immediately** by any CI run, lockfile
change, or edit to `pyproject.toml` / `ci.yml`. The measured counts (319 defs, 347 callables, 9
`to_dict`, per-package bounds) must be re-measured if any package surface changes before planning.
