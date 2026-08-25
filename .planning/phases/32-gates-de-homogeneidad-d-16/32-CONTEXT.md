# Phase 32: Gates de homogeneidad + D-16 - Context

**Gathered:** 2026-08-25 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

CI falla si la homogeneidad se degrada — sin código compartido entre paquetes, los gates son lo
único que impide que las seis superficies diverjan en tres releases. Requirement: GATE-TYP-01.
Depende de Phases 30 y 31 (ambas completas). Dos entregables de primera clase (DT-09): el gate AST
de superficie y el test de paridad sync/async por introspección — más el cierre de D-16
(reconciliación de las listas de enrollment de `market-data-client`). Fuera de scope: cualquier fix
de tipado de superficie más allá de lo que el gate detecte hoy (la superficie ya está limpia,
Phases 29-31 hicieron esa migración); la verificación en vivo (Phase 33); cualquier release
(Phase 34).
</domain>

<decisions>
## Implementation Decisions

### Alcance real de D-16 (criterio 4)
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

### Gate AST de superficie (criterios 1-2)
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

### Test de paridad sync/async (criterio 3)
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

### Roster explícito: wallets + `_PACKAGES` (criterio 4)
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

### Folded Todos
None — no pending todos matched this phase.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — § Phase 32 (los 5 success criteria) — nota: el wording "job de CI nuevo"
  del criterio 1 está en tensión con D-05/D-12 (ver arriba); usar el D-lock, no la prosa
- `.planning/future-plans/tipado_homogeneo.md` — D-locks DT-01..DT-09, esp. DT-04 (paridad
  sync/async como sustituto de REFAC-06), DT-06 (exenciones exactas del gate de superficie), DT-09
  (gate + test de paridad son entregables de primera clase)
- `.planning/phases/31-endpoints-de-ops-estructura-uniforme/31-CONTEXT.md` — D-12 (patrón
  "step-en-`lint`" para gates cross-package, precedente directo de D-05), D-09/D-10/D-11
  (estructura uniforme, wallets/ambito docstring-only)
- `.planning/phases/30-iol-client-tipado/30-CONTEXT.md` — D-10, precedente de RED-fixture-como-
  demostración-manual (`test_typed_surface_red.py`), citado en Claude's Discretion arriba
- `.planning/milestones/v1.2-phases/15-driver-migration-4-refac-05/15-REVIEW.md` (WR-01/WR-02,
  líneas ~61-164) — caso de estudio canónico de un AST guard vacuo, citado por el criterio 3
- `tools/check_uniform_structure.py`, `tools/check_decode_intactness.py` — template de
  implementación completo para `tools/check_surface_types.py` (convención de docstring,
  roster-leído-de-disco, output `::error::`)
- `verification/test_main_matriz_uses_single_client_instance.py` — patrón de AST gate no-vacuo con
  lower+upper bound, referencia directa para el diseño del gate de superficie
- `packages/market-data-client/tests/test_public_surface_market_data.py` — cobertura in-package
  existente que fundamenta D-11
- `pyproject.toml:97` (mypy `files`), `:149-156` (import-linter `root_packages`), `:182-187`
  (contrato `market_data_client._core`) — estado actual de las listas de D-16
- `.github/workflows/ci.yml:37-38` (step `lint-imports`), `:49-59` (steps `decode-intactness`/
  `uniform-structure`), `:95` (loop mypy-tests, 6 paquetes), `:118-122` (job `test`, path explícito
  que pisa `testpaths`)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/check_uniform_structure.py` / `tools/check_decode_intactness.py` — template completo a
  seguir para `tools/check_surface_types.py` (docstring convention, roster leído de `packages/` en
  disco, salida `::error::`, stdlib-only)
- `verification/test_main_matriz_uses_single_client_instance.py` — patrón de AST walker no-vacuo
  (lower+upper bound de ctor sites) + su postmortem WR-02 en `15-REVIEW.md` como caso de estudio de
  gate vacuo
- "Patrón 1" (`pythonpath = ["."]`, `pyproject.toml:110`) — import cross-package desde tests de
  paquete, ya usado por 8 archivos (ej. `packages/ambito-financiero-client/tests/test_harness_schema.py:9-20`)

### Established Patterns
- Los 6 `__init__.py` usan `ImportFrom` explícito, nunca star-imports — resoluble por AST puro
- Ningún `__all__` de módulo cubre la superficie real completa; ésta vive en métodos de
  `Client`/`AsyncClient`/`SafeModel` — confirmado: 0 funciones de módulo con `Any`/`dict[str, Any]`,
  9 métodos `to_dict()` son los únicos hits hoy
- El job `lint` de `ci.yml` ya aloja 2 gates cross-package stdlib-only — home natural del 3ro
- `verification/` nunca corre en CI (el job `test` pasa un path per-package que pisa `testpaths`) —
  cualquier gate/test que deba gatear CI real no puede vivir ahí

### Integration Points
- `.github/workflows/ci.yml` job `lint` (step nuevo) y job `typecheck` (mypy `files` en
  `pyproject.toml:97`, agregar `packages/market-data-client/src`)
- `packages/<pkg>/tests/` (6 archivos nuevos de paridad) + helper compartido (ubicación: Claude's
  Discretion) + `packages/market-data-client/src/market_data_client/aio.py:776-788` (`configure`,
  candidato a fix de D-09)
- `[tool.importlinter]` en `pyproject.toml` (prueba RED nueva del contrato `market_data_client._core`
  ya existente — `root_packages`/contratos NO se editan, ya están completos)
- `verification/test_public_surface.py` (comentario nuevo junto a `_PACKAGES`, la lista NO se edita)
</code_context>

<specifics>
## Specific Ideas

- El operador confirmó el set completo de assumptions sin correcciones — incluido el hallazgo de
  que `market_data_client.aio.configure` le falta `http_client` pese a que su propio docstring
  afirma paridad exacta con la superficie sync (D-09).
</specifics>

<deferred>
## Deferred Ideas

- Fix real de `market_data_client.aio.configure` (agregar `http_client`) vs allowlist explícito —
  Claude's Discretion arriba; se resuelve en planning, no en esta discusión
- Los ~6 rosters de paquetes fuera del scope del criterio 4 (ver D-12) — deuda documentada, no
  scope de Phase 32
- Actualización de `CLAUDE.md` (afirma que matriz no tiene `aio.py` y que los `__init__.py` usan
  star-imports — ambas stale) — fuera de scope de esta fase, nota lateral únicamente

### Reviewed Todos (not folded)
None — no pending todos matched this phase.
</deferred>
