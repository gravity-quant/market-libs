# Phase 7: `_core.py` Extraction — Sync/Async Logic Dedup - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 7 elimina la duplicación de lógica entre `client.py` y `aio.py` por paquete extrayendo helpers puros a un nuevo módulo `_core.py` por paquete. El delivery indivisible:

1. **`_core.py` por paquete (REFAC-03)** — Contiene:
   - `RequestSpec` (dataclass per-package, fields propios a cada paquete)
   - `build_<endpoint>_request(state, ...) → RequestSpec` (builders puros)
   - `parse_<endpoint>_response(resp) → typed result` (parsers puros)
   - `build_login_request(state) → RequestSpec` + `parse_login_response(status, body, headers) → tuple` (auth-flow puro)
   - `raise_for_response`, `unwrap_envelope` (y demás helpers stateless ya module-level en Phase 6)

   `_core.py` **NO importa** `httpx.Client`/`httpx.AsyncClient` ni `client.py`/`aio.py` del mismo paquete. Bloqueo enforced por **import-linter declarativo** (config en `pyproject.toml`).

2. **`client.py` / `aio.py` colapsan a transport shells** — Sólo dispatch `httpx.Client.request(...)` vs `await httpx.AsyncClient.request(...)` + glue al builder/parser de `_core.py`. Endpoint groups (`§4 Segments`, `§5 Instruments`, etc.) miden ≤30-50 LOC en el shell; LOC drop ≥30% client+aio agregado por paquete vs baseline Phase 6 post-refactor.

3. **CR-03 cerrado (matriz)** — `_core.parse_envelope_response(resp, endpoint)` consume body (`resp.read()` + `.json()`) ANTES de cualquier raise. Futuro `httpx.Client(http2=True)` no introduce resource leak en el connection pool.

4. **CR-05 cerrado (matriz)** — `main_matriz.py` define `_envelope_probe(name, path, envelope_key=None, model_from_api=None)` que dedupea las 18 sweep probes (~95% boilerplate). Las 2 risk probes (`probe_get_detailed_positions`, `probe_get_account_report`) preservan `envelope_key=None`. Snapshot test pre-refactor por probe (ProbeResult contra payload canned) como guard.

5. **Cross-leak guard test (success-criterion #2)** — `verification/test_sync_async_isolation.py` parametrizado sobre 4 paquetes: `configure(token="SYNC-sentinel-<pkg>")` (sync) + `configure(token="ASYNC-sentinel-<pkg>")` (async) verifican que cada surface usa su sentinel en el wire request. matriz `pytest.skip("matriz aio.py REST stub hasta Phase 10 REFAC-04")`.

**Phase 7 NO entrega:** retries/backoff/tenacity (Phase 8), structured logging (Phase 8), refresh_token in-instance persistence (Phase 9 BUG-03), matriz aio.py REST surface (Phase 10 REFAC-04 + TokenStore), `_envelope_probe` cross-package promotion (este phase queda driver-only para matriz).

**Orden serial por paquete locked:** ámbito → iol → higyrus → matriz (idem Phase 6 D-05, lesson v1.0). Cada paquete = 1 commit atómico que incluye: `_core.py` extraction + shell migration + snapshot update + 277 tests baseline verde.

**Carry-forward Phase 6:**
- `_state.py` per paquete ya existe (Phase 6); Phase 7 lo consume sin modificarlo (los fields ya están).
- B8 pattern (`_raise_for_response` stateless compartido vía `aio.py` import de `client.py`) se EXTIENDE: el helper se MUEVE a `_core.py`, y `client.py` mantiene un alias module-level `_raise_for_response = _core.raise_for_response` (y `_unwrap = _core.unwrap` en matriz) para no romper imports legacy de tests/drivers.
- Snapshot público (`verification/test_public_surface.py`) iguale 1:1 vs Phase 6: `_core.py` es privado, no aparece en el snapshot; los aliases preservan los atributos legacy.
- PEP 562 shim de `client.py`/`aio.py` (D-01..D-04 Phase 6) sigue intacto — no se toca.

</domain>

<decisions>
## Implementation Decisions

### `_core.py` shape — RequestSpec + auth-flow factoring

- **D-01: Per-package `RequestSpec` dataclasses.** Cada paquete define su propio `@dataclass(frozen=True, slots=True) RequestSpec` en su `_core.py` con los fields que necesita (matriz: `auth_basic: tuple[str, str] | None`; iol: refresh-aware; higyrus: `json_body` + URL-encoding flag; ámbito: minimal). **NO** hay shared `RequestSpec` cross-package — consistente con la project constraint "no shared internals between packages". Forward-compat con Phase 8: cuando RELY-03 (`idempotent: bool = False`) aterrice, cada RequestSpec lo agrega independientemente (4× replicación; aceptado).

- **D-02: Auth-flow factorizado como builders + parsers puros.** `_core.build_login_request(state) → RequestSpec` + `_core.parse_login_response(status, body, headers) → (token, expires_at, refresh_token?)`. El transport shell ejecuta el HTTP call (`httpx.Client.post(...)` sync o `await httpx.AsyncClient.post(...)` async) y feed al parser. iol agrega `_core.build_refresh_request(state) → RequestSpec` + `_core.parse_refresh_response(...) → (token, expires_at, refresh_token?)` (mismo patrón). `_core.py` 100% sin I/O.

- **D-03: Shell `_request` retorna `httpx.Response` cruda.** Endpoint method llama `_core.parse_<endpoint>(resp) → typed result` que hace `resp.read()` + `.json()` + valida shape + raise typed exception si aplica + retorna typed result. Cambia el contrato actual de higyrus (devolvía `dict | list | None`) y matriz (devolvía `dict`) — ahora todos retornan Response. **Plus:** Phase 8 retry transport puede inspeccionar `resp.status_code` / `resp.headers` libremente (e.g., `Retry-After`).

- **D-04: Helpers stateless se mueven a `_core.py` con shim re-export.** `_core.raise_for_response` y `_core.unwrap` son las fuentes únicas. `client.py` define aliases module-level: `_raise_for_response = _core.raise_for_response` (los 3 paquetes con auth) y `_unwrap = _core.unwrap` (matriz). Tests y `main_matriz.py` que importan `_unwrap` directamente siguen funcionando. Snapshot público igual.

- **D-05: Endpoint groups = secciones del docstring del API.** La métrica "≤30-50 LOC por endpoint group" del success-criterion #3 se mide por secciones existentes en `client.py`/`aio.py` (matriz: `§4 Segments`, `§5 Instruments`, `§6 Orders`, `§7 Market Data`; higyrus: Cuentas, Movimientos, Posiciones; iol: Quotes, Instruments; ámbito: Cotizaciones). Cada group post-refactor ≤30-50 LOC en el shell.

### CR-03 + CR-05 closure

- **D-06: CR-03 absorbido por `_core.parse_envelope_response`.** El parser ejecuta `resp.read()` explícito, luego `resp.json()`, luego check `if raw["status"] == "ERROR": raise PrimaryAPIError(...)`. Body 100% consumido antes de cualquier raise. Shell sólo dispara `data = _core.parse_envelope_response(resp, endpoint_path)`. Self-contained: futuro `http2=True` no requiere auditoría del flow.

- **D-07: CR-05 `_envelope_probe` driver-only en `main_matriz.py`.** Signature: `_envelope_probe(name: str, path: str, *, envelope_key: str | None = None, model_from_api: Callable[[Any], Any] | None = None) -> ProbeResult`. Las 2 risk probes (`probe_get_detailed_positions`, `probe_get_account_report`) pasan `envelope_key=None` (omite `_unwrap`). `verification/` NO recibe la promotion (otros drivers no la consumen).

- **D-08: Refactor 18 probes atomic en el plan matriz.** El plan REFAC-03 matriz incluye en el MISMO commit: `_core.py` extraction + CR-03 fix + `_envelope_probe` helper + 18 probes migradas + snapshot test guard. Snapshot test pre-refactor registra `ProbeResult(name, status, ...)` de cada probe contra payload canned vía `pytest-httpx` (en `verification/test_matriz_sweep_snapshot.py` o equivalente — planner decide ubicación exacta). Si algo rompe, revert atómico del commit.

### CI gates — import-linter + cross-leak sentinel test

- **D-09: `import-linter` declarativo bloquea `_core.py → client.py`/`aio.py` imports.** Library `import-linter` agregada a `[dependency-groups] dev` del root `pyproject.toml`. Config en `[tool.importlinter]` del root o en `.importlinter` (planner decide ubicación; preferir `pyproject.toml` para consistencia con ruff/mypy config). 4 contracts: `<pkg>._core` forbids `<pkg>.client`, `<pkg>.aio` (uno por paquete). CI step `lint-imports` en `.github/workflows/ci.yml` (job lint o nuevo job).

- **D-10: Cross-leak sentinel test parametrizado en `verification/test_sync_async_isolation.py`.** 1 archivo cross-cutting, parametrize sobre `["iol_client", "higyrus_client", "ambito_financiero_client", "matriz_client"]`. Por paquete: configure sync con token `"SYNC-sentinel-<pkg>"`, configure async con token `"ASYNC-sentinel-<pkg>"`, fire 1 request en cada surface, assert wire header (auth nativo de cada paquete) tiene el sentinel correspondiente. **Convención de sentinel naming locked en Phase 6 D-12 / specifics** — Phase 7 lo IMPLEMENTA.

- **D-11: matriz `pytest.skip` con motivo explícito.** El test parametrizado para matriz skip con reason `"matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore"`. Visible en CI output, no silenciado, forward-tracked. Plan Phase 10 explicitará "des-skip matriz" como tarea cuando aio.py REST aterrice.

### Plan slicing & cadence

- **D-12: 6 planes en la phase.** Total:
  - **Plan 1 — CI gates infrastructure (tests-only, NO toca paquetes):** `import-linter` setup + config en `pyproject.toml` + 4 contracts (1 por paquete) + `verification/test_sync_async_isolation.py` parametrizado + matriz skip. Tests pasan en HEAD (los contracts no fallan porque ningún `_core.py` existe aún → contracts pasan vacíos; sentinel test usa el flow sync vigente y verifica fixture-reaches-production sentinel). Plan 1 NO bloquea Plan 2 (no introduce dependencia en `_core.py`); plan 2-5 RECONFIRMA contracts a medida que `_core.py` aparece.
  - **Plan 2 — REFAC-03 ámbito (canary):** `ambito_financiero_client/_core.py` con builders/parsers; `client.py`/`aio.py` colapsan a shells. ámbito sin auth (no auth-flow primitives needed); el patrón se prueba en el paquete más simple antes de iol/higyrus/matriz.
  - **Plan 3 — REFAC-03 iol:** `iol_client/_core.py` con auth-flow (login + refresh-with-password-fallback) + builders/parsers; `client.py`/`aio.py` shells. iol valida el patrón auth-flow más complejo (refresh_token chain).
  - **Plan 4 — REFAC-03 higyrus:** `higyrus_client/_core.py` con builders/parsers preservando URL-encoding quirks (no `%2F`, `doseq=True`); shells. higyrus tiene 685+669 LOC, el paquete más voluminoso por endpoint count.
  - **Plan 5 — REFAC-03 matriz + CR-03 + CR-05 (ATOMIC):** `matriz_client/_core.py` (RequestSpec con `auth_basic` opcional) + `parse_envelope_response` que cierra CR-03 + `main_matriz.py` `_envelope_probe` helper + 18 probes migradas + snapshot test guard + cross-leak skip update (referencia forward Phase 10). 1 commit atómico (D-08).
  - **Plan 6 — CI green gate consolidation:** full pytest + ruff + ruff format + mypy strict + snapshot diff vs Phase 6 + `lint-imports` + cross-leak guard test en matrix Python 3.12 + 3.13. Mismo patrón que Phase 6 Plan 7 (06-07-PLAN.md).

- **D-13: Orden serial idem Phase 6.** ámbito → iol → higyrus → matriz. Si Plan 3 (iol) rompe algo no esperado, Plans 1+2 (gates + ámbito) ya están mergeables; revert atómico de Plan 3 no afecta el avance previo. Lesson v1.0 + Phase 6 confirmada (matriz último por máxima superficie + scope CR-03/CR-05).

- **D-14: LOC metric per-package vs Phase 6 baseline.** Baseline = `wc -l packages/<pkg>/src/<pkg>/{client,aio}.py` en HEAD del commit final de Phase 6 (5db0a0d o cercano — operator confirma). Cada plan SUMMARY.md incluye: `LOC drop: client.py X→Y (-Z%), aio.py A→B (-C%), aggregate -W%`. Success-criterion ≥30% drop **agregado client+aio** por paquete. Si un paquete específico no llega (improbable — la dedup tiende a 50%+), el planner DEBE documentar por qué (e.g., ámbito sin auth puede tener drop más chico).

### ámbito-financiero special case

- **D-15: ámbito recibe full refactor `_core.py` como canary.** Aunque ámbito no tiene auth ni token-refresh, tiene parsing HTML/JSON duplicado entre `client.py` y `aio.py`. ámbito (Plan 2) es el canary que prueba el RequestSpec + parsers pattern antes de iol/higyrus/matriz. Cumple literalmente success-criterion #1 ("por cada paquete, `_core.py` contiene ..."). Drop esperado ≥30% por la deduplicación de parsers.

### Snapshot público preservation

- **D-16: `_core.py` NO aparece en `verification/test_public_surface.py`.** Phase 6 D-09 limitó el snapshot a `__all__` + signatures + submodules expuestos públicamente. `_core.py` es privado (no aparece en `__all__`, no expuesto). Re-export shims (`_raise_for_response`, `_unwrap`) preservados como atributos module-level — los tests que `from <pkg>.client import _unwrap` siguen funcionando. Snapshot iguale 1:1 vs Phase 6 (zero diff en `verification/snapshots/<pkg>-surface.txt`). Si por error un plan añade `_core` a `__all__` de algún paquete, el snapshot diff lo flagueará.

### Claude's Discretion

El planner decide (basado en research RESEARCH.md de la phase + Phase 6 patrones):

- **Estructura interna exacta de cada `_core.py`** — orden de declaraciones, agrupación por endpoint group, número de helpers privados intermedios. El research recomienda agrupar por sección del API (D-05); la implementación lo refina.
- **Naming de funciones en `_core.py`** — e.g., `build_get_quote_request` vs `quote_request` vs `get_quote_spec`. Preferencia: `build_<endpoint_name>_request` (consistente, mecánicamente derivable del nombre del método público).
- **Ubicación exacta del snapshot test guard para las 18 matriz probes** — `verification/test_matriz_sweep_snapshot.py` vs `packages/matriz-client/tests/test_main_matriz_probes.py`. Preferencia: `verification/` (consistente con que main_matriz.py vive en repo root y consume helpers de `verification/`).
- **`pyproject.toml` vs `.importlinter` file para import-linter config** — preferencia `pyproject.toml` `[tool.importlinter]` por consistencia con ruff/mypy/pytest config; planner valida que import-linter 2.x lo soporte.
- **Forward-decl de Phase 8 `idempotent` field** — el planner decide si declararlo ahora como `idempotent: bool = False` en cada `RequestSpec` (forward-compat, Phase 8 sólo cambia defaults) o esperar a Phase 8 para añadirlo. Preferencia: declararlo ahora (zero-cost, forward-compat documentada).
- **Snapshot test mechanics para 18 matriz probes** — capa exacta de mocking (pytest-httpx vs httpx.MockTransport), payload canned format (inline en test vs JSON fixture en `tests/fixtures/`). Phase 6 06-02-PLAN.md tiene precedentes que el planner puede mirror.
- **Test cadence per plan** — `uv run pytest packages/<pkg>/` + `uv run pytest verification/test_public_surface.py` + `uv run pytest verification/test_sync_async_isolation.py` + `uv run lint-imports` pre-commit, mismo idiom que Phase 6 D-07.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & milestone

- `.planning/PROJECT.md` — v1.1 milestone goals, scope, key decisions; menciona la dedup sync/async como target del milestone y la constraint "no shared internals between packages" (justifica D-01 per-package RequestSpec).
- `.planning/REQUIREMENTS.md` §"Refactor arquitectónico (REFAC)" — REFAC-03 (Phase 7 requirement principal); §"Code Review concerns (CR)" — CR-03 (matriz `_request` response body) y CR-05 (18 sweep probes refactor).
- `.planning/ROADMAP.md` §"Phase 7" — goal + 5 success criteria explícitos; §"Phase 6" para entender el handoff (Client class skeleton ya entregado); §"Phase 8/10" para entender forward-references (Phase 8 mete `idempotent` en RequestSpec; Phase 10 destapa matriz aio.py REST + des-skipea sentinel test).
- `.planning/STATE.md` §"Decisions" — orden serial per-package locked; §"Blockers/Concerns" §"Phase 7" — Pitfall #3 (re-coupling sync/async via `_core.py` imports) marcado como gate de merge.

### Prior phase (Phase 6, handoff)

- `.planning/phases/06-compat-safety-net-client-class-skeleton/06-CONTEXT.md` — D-04 (`configure(token=..., token_expires_at=...)` extension), D-09 (snapshot scope), D-12 (sentinel naming convention `SYNC-sentinel-<pkg>` / `ASYNC-sentinel-<pkg>`), D-21 (B8 helper sharing pattern que Phase 7 EXTIENDE moviendo helpers a `_core.py`).
- `.planning/phases/06-compat-safety-net-client-class-skeleton/06-RESEARCH.md` — patterns base del Client class que Phase 7 consume.
- `.planning/phases/06-compat-safety-net-client-class-skeleton/06-PATTERNS.md` — mapeo de archivos nuevos vs analogs existentes; Phase 7 sigue el mismo formato.
- `.planning/phases/06-compat-safety-net-client-class-skeleton/06-07-PLAN.md` — plantilla para Plan 6 (CI green gate); Phase 7 Plan 6 mirror.
- `.planning/phases/06-compat-safety-net-client-class-skeleton/06-02-PLAN.md` — plantilla para guard tests con pytest-httpx; Phase 7 cross-leak test + snapshot test guards siguen el mismo idiom.

### Research (v1.1)

- `.planning/research/SUMMARY.md` §"Architecture Approach" — 5-module pattern locked (`_state.py` ✅ Phase 6, `_core.py` este phase, `_transport.py`/`_atransport.py`/`_logging.py` Phase 8).
- `.planning/research/SUMMARY.md` §"Phase 2: `_core.py` Extraction" — esta phase corresponde a "Phase 2" del research (renombrada Phase 7 en roadmap v1.1).
- `.planning/research/PITFALLS.md` §"Pitfall 3" — `_core.py` re-coupling via accidental `from .client import _token`; D-09 (import-linter) es la mitigación structural; D-10 (cross-leak sentinel test) es el regression guard.
- `.planning/research/PITFALLS.md` §"Pitfall 8" — matriz `aio.py` copy-paste prevention; Phase 7 sienta la prereq `matriz/_core.py` que Phase 10 consume sin riesgo de copy-paste.
- `.planning/research/PITFALLS.md` §"Pitfall 18" — refactor breaks 277 tests then "fixes" them by weakening; guard: snapshot público sin diff + cross-leak sentinel test + 277 baseline verde antes Y después de cada plan.
- `.planning/research/PITFALLS.md` §"Pitfall 21" — CR-03 (matriz `_request` resp.close() missing), prevención en D-06.
- `.planning/research/PITFALLS.md` §"Pitfall 23" — CR-05 (18 sweep probes refactor preserva risk probes con envelope_key=None), prevención en D-07.

### Codebase maps (vigentes)

- `.planning/codebase/ARCHITECTURE.md` §"Module-Level State Pattern" + §"Layers" — entiende cómo `client.py` y `aio.py` están organizados hoy; Phase 7 los colapsa preservando las layers.
- `.planning/codebase/CONVENTIONS.md` — naming conventions (`_core.py` private module, `RequestSpec` PascalCase, builders/parsers snake_case); `from __future__ import annotations` mandatory.
- `.planning/codebase/CONCERNS.md` §"Module-Level Singleton" y §"Sync/Async Duplication" — justifica el refactor.
- `.planning/codebase/TESTING.md` — autouse fixtures actuales con `configure(token=..., token_expires_at=...)` (Phase 6 migration), siguen siendo el patrón post-Phase-7.

### CR concerns origin (Phase 5 review)

- `.planning/milestones/v1.0-phases/05-matriz-verification/05-REVIEW.md` — texto completo de CR-03 (WR-03) y CR-05 (WR-05) con line numbers exactos. Phase 7 Plan 5 (matriz) DEBE leerlo para preservar los detalles de cada concern.

### Forward references (no leer todavía)

- `.planning/ROADMAP.md` §"Phase 8" — `RequestSpec.idempotent: bool = False` aterrizará aquí; D-13 forward-decl es opcional.
- `.planning/ROADMAP.md` §"Phase 9" — BUG-01/02/03/04 cada uno será un single-site fix en `_core.py` del paquete correspondiente (consume Phase 7 deliverable).
- `.planning/ROADMAP.md` §"Phase 10" — REFAC-04 destapa matriz aio.py REST surface y des-skipea el sentinel test del Plan 1.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`_state.py` per paquete (Phase 6)** — `_ClientState` dataclass con `base_url`, credenciales, `token`, `token_expires_at`, `http_client`, `refresh_token` (iol), `client_id` (higyrus). Phase 7 lo consume sin tocar — el RequestSpec builder recibe `state: _ClientState` y lee fields.
- **`_raise_for_response` y `_unwrap` ya stateless module-level** — iol/higyrus/matriz los tienen así desde Phase 6 D-21 (B8 pattern); Phase 7 los MUEVE a `_core.py` con shim re-export (D-04). Zero churn de imports legacy si planner sigue D-04 literal.
- **`pytest-httpx` mocking pattern** — Phase 6 06-02-PLAN.md tiene precedentes de guard tests con httpx_mock; Phase 7 cross-leak sentinel test y matriz 18 probes snapshot test los mirror.
- **`verification/test_public_surface.py` y `verification/snapshots/<pkg>-surface.txt`** — Phase 6 baseline; Phase 7 verifica que `_core.py` NO entra al snapshot (D-16) corriendo el test pre-commit.
- **`verification/regen_snapshots.py`** — script Phase 6; Phase 7 NO lo invoca (snapshot debe quedarse igual). Si por error algún plan añade entradas al snapshot, el commit incluye el regen + justificación.
- **PEP 562 `__getattr__` shim de `client.py`/`aio.py` (Phase 6 D-01)** — Phase 7 NO lo toca. Los aliases `_raise_for_response = _core.raise_for_response` viven como atributos module-level normales (no via shim).

### Established Patterns

- **B8 helper sharing pattern (Phase 6 D-21):** `aio.py` importa `_raise_for_response` directamente de `client.py` (no duplica). Phase 7 cambia el origen: `aio.py` y `client.py` AMBOS importan de `_core.py`. El alias `client._raise_for_response = _core.raise_for_response` preserva back-compat.
- **`@dataclass(slots=True)` para `_ClientState`** — patrón Phase 6; Phase 7 lo reusa para `RequestSpec(frozen=True, slots=True)` (frozen porque RequestSpec es input puro, no muta).
- **Endpoint groups con divider comments** — `# -- Segments (§4) --` en matriz; higyrus y iol siguen patrón similar. Phase 7 preserva los dividers en los shells post-refactor; sirve para medir D-05.
- **`assert state.token is not None` después de `_ensure_token()`** — iol/higyrus/matriz lo tienen para mypy narrowing. Phase 7 lo preserva en el shell `_request` (el RequestSpec builder lo asume non-None).
- **higyrus URL-encoding quirk** — `urlencode(clean_params, doseq=True, quote_via=quote, safe="/")` para preservar `/` literal (Higyrus IIS rechaza `%2F`). Va en `higyrus_client/_core.build_<endpoint>_request` que retorna la URL ya construida o un RequestSpec con el field URL-pre-encoded.
- **matriz `_request` cubierto en checks** — el body-shape check (`isinstance(raw, dict)`) + status==ERROR check viven hoy en `client._request`. Phase 7 los MUEVE a `_core.parse_envelope_response`. CR-03 fix (D-06) se hace acá.

### Integration Points

- **`packages/<pkg>/src/<pkg>/_core.py`** — NUEVO módulo per paquete (4 archivos). Contiene RequestSpec + builders + parsers + auth-flow primitives.
- **`packages/<pkg>/src/<pkg>/client.py`** — colapsa a transport shell. Mantiene alias `_raise_for_response = _core.raise_for_response` y (matriz) `_unwrap = _core.unwrap`. PEP 562 shim Phase 6 intacto.
- **`packages/<pkg>/src/<pkg>/aio.py`** — colapsa a transport shell async. Mismo alias pattern. (matriz aio.py sigue stub Phase 6 → Phase 10.)
- **`pyproject.toml` root** — agrega `import-linter` a `[dependency-groups] dev`; agrega `[tool.importlinter]` config con 4 contracts (uno por paquete).
- **`.github/workflows/ci.yml`** — agrega step `uv run lint-imports` al job lint (o nuevo job según planner).
- **`verification/test_sync_async_isolation.py`** — NUEVO test parametrizado sobre 4 paquetes (D-10).
- **`verification/test_matriz_sweep_snapshot.py`** (o equivalente) — NUEVO test guard para las 18 probes pre/post CR-05 refactor.
- **`main_matriz.py`** — recibe el `_envelope_probe` helper + 18 probes migradas (Plan 5).
- **`packages/matriz-client/src/matriz_client/client.py` y `aio.py`** — aio.py sigue stub; client.py colapsa via `_core.py` matriz.
- **`packages/<pkg>/tests/conftest.py`** — sin cambios esperados (Phase 6 ya migró a `configure(token=...)`).

</code_context>

<specifics>
## Specific Ideas

- **`RequestSpec` field naming convention (matriz example):**
  ```python
  # matriz_client/_core.py
  @dataclass(frozen=True, slots=True)
  class RequestSpec:
      method: str
      path: str
      params: dict[str, Any] | None = None
      headers: dict[str, str] | None = None
      auth_basic: tuple[str, str] | None = None  # matriz Risk API only
      # idempotent: bool = False  # forward-decl Phase 8 RELY-03 (D-13 discretion)
  ```
- **`import-linter` contract example (pyproject.toml `[tool.importlinter]`):**
  ```toml
  [[tool.importlinter.contracts]]
  name = "matriz_client._core does not depend on transport modules"
  type = "forbidden"
  source_modules = ["matriz_client._core"]
  forbidden_modules = ["matriz_client.client", "matriz_client.aio"]
  ```
  4 contracts (iol/higyrus/ambito/matriz). Verificar que `import-linter` 2.x soporta forbidden contracts en pyproject.toml (planner confirma).
- **Cross-leak sentinel test pattern (verification/test_sync_async_isolation.py):**
  ```python
  PACKAGES = [
      ("iol_client", "Authorization", "Bearer "),  # header_name, value_prefix
      ("higyrus_client", "Authorization", "Bearer "),
      ("matriz_client", "X-Auth-Token", ""),
      # ambito has no auth → use base_url custom value as sentinel proxy
  ]
  @pytest.mark.parametrize("pkg_name, header_name, value_prefix", PACKAGES)
  def test_sync_async_token_isolation(pkg_name, header_name, value_prefix, httpx_mock):
      pkg = importlib.import_module(pkg_name)
      if pkg_name == "matriz_client":
          pytest.skip("matriz aio.py REST stub hasta Phase 10 REFAC-04")
      sync_sentinel = f"SYNC-sentinel-{pkg_name}"
      async_sentinel = f"ASYNC-sentinel-{pkg_name}"
      pkg.configure(token=sync_sentinel, token_expires_at=9_999_999_999.0)
      pkg.aio.configure(token=async_sentinel, token_expires_at=9_999_999_999.0)
      # fire sync request, assert wire header == sync_sentinel
      # fire async request, assert wire header == async_sentinel
  ```
  Planner ajusta la API exacta (per-package configure signatures) y el body del test; el shape va por acá.
- **`_envelope_probe` signature target (main_matriz.py):**
  ```python
  def _envelope_probe(
      name: str,
      path: str,
      *,
      envelope_key: str | None = None,
      model_from_api: Callable[[Any], Any] | None = None,
  ) -> ProbeResult:
      """Sweep probe helper: GET path, optionally unwrap envelope_key,
      optionally map model_from_api over the result, emit ProbeResult."""
      ...
  ```
- **Commit message pattern Phase 7:**
  - Plan 1: `feat(verification): import-linter setup + cross-leak sync/async isolation test (REFAC-03)`
  - Plans 2-5: `refactor(<pkg>): extract _core.py — collapse client.py/aio.py to transport shells (REFAC-03)`
  - Plan 5 specifically: `refactor(matriz): extract _core.py + close CR-03 (body consume) + CR-05 (_envelope_probe x18) (REFAC-03, CR-03, CR-05)`
  - Plan 6: `ci(phase-07): green gate — full pytest + ruff + mypy + snapshot + lint-imports + isolation guard (REFAC-03)`
- **LOC drop reporting format en cada SUMMARY.md** (Plans 2-5):
  ```
  LOC drop vs Phase 6 baseline (commit 5db0a0d):
  - client.py: 685 → 320 (-53%)
  - aio.py:    669 → 305 (-54%)
  - _core.py:  0 → 220 (NEW)
  - Aggregate client+aio: 1354 → 625 (-54%)  ✓ ≥30%
  ```

</specifics>

<deferred>
## Deferred Ideas

- **`_envelope_probe` promoted to `verification/probes.py` cross-package** — D-07 lo mantiene driver-only en matriz. Si en v1.2 otros drivers adoptan el mismo patrón, se promociona entonces (mismo precedente que safemodel_diff/cycle_report de Phase 5 v1.0).
- **`RequestSpec.idempotent: bool = False` forward-decl** — D-13 lo deja a discreción del planner (preferencia: declararlo). Si se difiere, Phase 8 RELY-03 lo agrega per-package en 4 cambios independientes.
- **Generated-code parity tooling (unasync/codegen)** — research SUMMARY P3 defer to v1.2+. Phase 7 deja el patrón LISTO para codegen futuro (sync y async shells son mecánicamente espejos), pero no introduce la herramienta.
- **import-linter `independence` o `layered` contracts** — Phase 7 usa solo `forbidden` contracts. Si v1.2 quiere reglas de capas estrictas (e.g., `_core.py` no puede importar `exceptions.py`), se agrega entonces.
- **Cross-leak sentinel test desktopear matriz** — Phase 10 plan DEBE incluir "des-skip matriz en verification/test_sync_async_isolation.py" como tarea explícita.
- **CR-05 cross-package promotion** — driver helpers de iol/higyrus/ambito siguen sus propios patrones; si en v1.2 hay otro CR sobre sweep probes en iol/higyrus, se promociona el helper.
- **`Client.with_options(max_retries=N)` per-call override (anthropic pattern)** — v1.2+ backlog (no afecta Phase 7).
- **Cambio de `_request` para usar `with http.send(...) as resp:` context-manager** — Opción C de Área 2 / CR-03; descartada por churn vs. beneficio. D-06 alcanza el mismo objetivo más barato.

</deferred>

---

*Phase: 7-`_core.py` Extraction — Sync/Async Logic Dedup*
*Context gathered: 2026-06-12*
