# Phase 31: Endpoints de ops + estructura uniforme - Context

**Gathered:** 2026-08-23 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Los 5 endpoints de ops que todavía devuelven `dict[str, Any]` devuelven modelos tipados, y los 6
paquetes presentan la misma estructura de archivos para que el próximo endpoint nazca con lugar
donde vivir. Requirements: TYP-02, TYP-03. Paraleliza con Phase 30 (ya completa) — ambas dependen
solo de Phase 29.

Alcance fijo (criterios ya refinados en roadmap): `higyrus.get_health` y
`market-data.get_health`/`get_health_feed`/`add_holidays`/`delete_holiday` a modelos tipados en
sync y async (cero `dict[str, Any]` en firmas ni shims); test de request byte-idéntico para
`add_holidays`/`delete_holiday` (mutaciones ya publicadas en v0.4.0 — cambio estrictamente
response-only); el mutating-gate (`_ensure_mutation_allowed()` como primer statement literal de
los 8 métodos de mutación, ningún builder cambia `idempotent=`) queda intacto; `models.py` +
`types.py` presentes (mínimos, con docstring) en los 6 paquetes, verificable por un check de
existencia que corre en CI. El gate AST de superficie (cero `Any`/`dict[str, Any]`) y D-16 son
Phase 32, NO esta fase.
</domain>

<decisions>
## Implementation Decisions

### Diseño de modelos
- **D-01:** Las 5 formas de respuesta se derivan de los schemas capturados en vivo en
  `.planning/verification/schemas/`, no de mocks ni de OpenAPI: `higyrus.get_health` → `Health`
  (`{status: str}`, 1 modelo); market-data gana ~7 modelos nuevos — `Health`/`HealthAuth` (`get_health`),
  `HealthFeed`/`FeedIngestor`/`FeedMarket`/`FeedPipeline` (`get_health_feed`, 3 niveles de nesting,
  `last_error`/`last_write_error` declarados `str | None`), `AddHolidaysResult`
  (`{days: list[CalendarDay], note: str, saved: int}`) y `DeleteHolidayResult`
  (`{day: str, deleted: bool}`). `add_holidays.days[]` **reutiliza `CalendarDay` existente**
  (`market_data_client/models.py:608-635`) — el schema vivo coincide campo por campo, incluidos
  los dos campos de hora `str | None` — nunca declarar un modelo de elemento paralelo.
- **D-02:** Cada paquete extiende su **propio `SafeModel` existente** verbatim — la base plana de
  higyrus (`higyrus_client/models.py:41-54`) y la base de market-data con el paso
  `_apply_mapping_policy` (`market_data_client/models.py:160-179`, reach top-level-only, pinneado
  por `test_no_mapping_carrying_model_is_ever_a_nested_field_type`). Ningún modelo nuevo declara un
  campo `dict[...]`; ninguno lleva `received_at` (health/holidays no son snapshots ni tienen
  staleness).
- **D-03:** `SafeModel.to_dict()` se agrega a las bases de higyrus y market-data, copiado verbatim
  de `iol_client/models.py:80-93` (precedente Phase 30, D-08 de `30-CONTEXT.md`). Necesario porque
  `main_market_data.py:628-643,2381-2389` y `main_higyrus.py:670,685` llaman `len()`/
  `isinstance(dict)` sobre el resultado — una dataclass frozen+slots rompe eso sin el escape hatch.
- **D-04:** `higyrus.get_health` conserva su comportamiento **raise-on-non-dict** existente
  (`HigyrusAPIError(status_code=0, ...)`, pinneado por `tests/test_core.py:412-415` y
  `tests/test_async_client.py:198-206`) y el carve-out 204→instancia zero-valued (no `{}`,
  precedente Phase 7 CR-02). `market-data.get_health`/`get_health_feed` **ganan** un guard
  equivalente (`parse_health_response` hoy no tiene ninguno).

### Wiring en `_core` + mutating-gate
- **D-05:** Los dos parsers compartidos se **dividen en cuatro** — `parse_health_response`
  (hoy sirve `get_health` Y `get_health_feed`, `_core.py:280-285`) y
  `parse_calendar_write_response` (hoy sirve `add_holidays` Y `delete_holiday`,
  `_core.py:1083-1114`) ya no pueden compartirse: las formas vivas de cada par son no
  relacionadas. Cada parser nuevo lleva `@_decode._response_parser` (todos los demás parsers
  model-building del monorepo lo tienen; los dos que se reemplazan hoy NO, porque hoy no
  construyen modelos).
- **D-06:** Esta fase **no es zero-edit** — múltiples mocks existentes (`test_calendar_write.py`,
  `test_calendar_write_async.py`, ~132 líneas de referencias a `add_holidays`/`delete_holiday` en
  tests de market-data, 18 hits de `"status": "ok"` en tests de higyrus) fijan formas que el wire
  vivo contradice (ej. `{created, skipped}` mockeado vs. `{days, note, saved}` real) y se
  re-mockean mecánicamente a la forma del schema vivo, siguiendo el precedente Phase 30-03. Blast
  radius comparable a esa fase, no un cambio quirúrgico.
- **D-07:** **No existe hoy** el guard AST que ROADMAP.md asume verde para `_ensure_mutation_allowed()`
  como primer statement — grep del repo no encuentra ningún check AST de orden de statements sobre
  `client.py`/`aio.py` de market-data (el único test con "gate" en el nombre,
  `verification/test_main_market_data_no_gate_bypass.py`, parsea el *driver*, no el cliente). La
  invariante hoy solo está cubierta conductualmente (`test_calendar_write.py:403-467`,
  `test_calendar_write_async.py:382-420`, `test_mutation_gate.py`: refused → zero HTTP requests).
  Esta fase **construye** el guard AST desde cero (o, alternativa documentada pero no preferida,
  restatea el criterio 3 explícitamente contra los tests conductuales existentes) — Claude decide
  cuál al planificar, con preferencia por construir el guard AST (paridad con el precedente
  `test_main_matriz_has_no_singleton_path_references` de Phase 15/30).
- **D-08:** El test de request byte-idéntico (criterio 2) es una pieza **nueva** — no hay patrón
  reusable en el repo hoy (los tests existentes comparan método/path/un header/body via
  `json.loads` pieza por pieza, nunca el set completo de headers ni el query string). Se construye
  como una captura-y-compara: tupla congelada `(method, str(url), sorted(headers.items()),
  content_bytes)` capturada del código pre-cambio y pinneada como literal — comparación de **bytes
  crudos**, nunca `json.loads(...)`, para no perder drift de key-ordering en `HolidaysIn.to_dict()`
  (`models.py:487-489`).

### Estructura uniforme (models.py + types.py)
- **D-09:** El criterio 4 son **7 archivos nuevos, no 4**: `types.py` en **5** paquetes (higyrus,
  iol, market-data, ambito, wallets — solo matriz tiene uno hoy, 130 líneas en
  `matriz_client/types.py`), más `models.py` en ambito y wallets. higyrus/iol/market-data ya
  tienen `models.py` pero no `types.py` — y no tienen contenido `Literal` real para poner ahí
  todavía (el D-lock de Phase 29 prohíbe `Literal` en campos RESPONSE; la promoción de
  `mercado`/`plazo` de iol queda diferida a Phase 33). Los 5 `types.py` nuevos son **placeholders
  con docstring**, no contenido funcional.
- **D-10:** `wallets-client` recibe `models.py` + `types.py` **docstring-only, con `__all__:
  list[str] = []`** — sin `SafeModel`, sin clases, sin importar `_decode`. Verificado contra
  `tools/check_decode_intactness.py`: Check D (líneas ~625-662) nunca inspecciona `models.py`/
  `types.py`, solo la presencia/ausencia de `_decode.py`. Dar a wallets un `SafeModel` real
  rompería su import (no tiene módulo `_decode` del que importar) y enrojecería su leg completo de
  CI matrix. La exención de Phase 29 (`29-WALLETS-EXEMPTION.md`) **sigue válida sin editar**
  `tools/check_decode_intactness.py` — el prosa de ese doc queda desactualizada (dice "no
  `models.py`") pero nada se pone rojo; Claude decide si vale la pena una nota de actualización
  liviana al doc o dejarlo como está para que Phase 32/una fase futura lo supere formalmente.
- **D-11:** `ambito-financiero-client` recibe el mismo tratamiento docstring-only que wallets —
  `models.py`/`types.py` vacíos pero presentes, sin `SafeModel` (ámbito ya tiene su propio patrón
  de parsing sin modelos, `_parsing.py::parse_ar_decimal`, que esta fase no toca).
- **D-12:** El check de existencia para el criterio 4 se implementa como **script nuevo
  stdlib-only bajo `tools/`**, cableado como step adicional del job `lint` **existente** en
  `ci.yml` — mismo patrón que el step `decode-intactness` ya presente (cross-package por
  naturaleza, no puede vivir en el job `test` per-package, y `verification/` nunca corre en CI
  como documenta el propio comentario inline de `ci.yml`). Nunca un test pytest bajo
  `verification/`.

### Cobertura de tipos fuera de esta fase
- **D-13:** Los 4 modelos nuevos de market-data **no** quedan cubiertos por mypy en CI esta fase —
  `market-data-client/src` está ausente de `files` en `pyproject.toml:97` y del loop mypy de
  `ci.yml:85` (enrolamiento = D-16, Phase 32). Es un gap esperado, no algo a cerrar acá. Correr
  `uv run mypy packages/market-data-client/src` localmente como paso de aceptación aunque CI no lo
  corra. higyrus SÍ está enrolado, así que su modelo `Health` nuevo sí queda strict-typechecked
  por CI.

### Claude's Discretion
- Nombres exactos de las clases nuevas de market-data (`Health`/`HealthAuth`/`HealthFeed`/
  `FeedIngestor`/`FeedMarket`/`FeedPipeline`/`AddHolidaysResult`/`DeleteHolidayResult` son los
  sugeridos por la evidencia) — dentro de D-01.
- Construir el guard AST vs. restatear el criterio 3 contra tests conductuales (D-07) — preferencia
  documentada por el guard AST, decisión final en planning.
- Si actualizar la prosa de `29-WALLETS-EXEMPTION.md` o dejarla para una fase futura (D-10).
- Forma exacta del script de existence-check (nombre de archivo, mensajes de error) dentro de D-12.

### Folded Todos
None — no pending todos matched this phase.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — § Phase 31 (los 4 success criteria refinados)
- `.planning/future-plans/tipado_homogeneo.md` — plan fuente, § Phase 31, D-locks DT-01..DT-09
  (DT-06 exenciones del gate AST, DT-03 no-shared-code)
- `.planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md` — por qué wallets no recibe
  `_decode.py`, y qué se rompe si se le da uno prematuramente (D-10)
- `.planning/phases/29-decoder-observable/29-DLOCK-RESPONSE-LITERAL.md` — por qué los `types.py`
  nuevos son placeholders sin contenido `Literal` (D-09)
- `.planning/phases/29-decoder-observable/29-AGGREGATION-CONTRACT.md` — por qué cada parser nuevo
  necesita `@_decode._response_parser` (D-05)
- `.planning/phases/30-iol-client-tipado/30-CONTEXT.md` — precedente directo: D-08 `to_dict()`
  (D-03 acá), D-06 re-mocking mecánico (D-06 acá), D-05 wiring de parsers decorados (D-05 acá)
- `.planning/verification/schemas/market-data-client/` y
  `.planning/verification/schemas/higyrus-client/` (si existe) — schemas vivos, fuente de verdad
  de los 5 modelos (D-01)
- `tools/check_decode_intactness.py` — Check D (roster `IN_SCOPE_PACKAGES`/`EXEMPT_PACKAGES`),
  para confirmar que D-10/D-11 no lo rompen
- `.github/workflows/ci.yml` — step `decode-intactness` del job `lint`, patrón a espejar para el
  nuevo existence-check (D-12)
- `.planning/codebase/` — mapas (ARCHITECTURE, CONVENTIONS, STRUCTURE, CONCERNS)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `iol_client/models.py:80-93` — `to_dict()` verbatim template a copiar en higyrus y market-data
  (D-03)
- `higyrus_client/models.py:41-54` — `SafeModel` base plana a extender (higyrus)
- `market_data_client/models.py:160-179` — `SafeModel` base con `_apply_mapping_policy` (D-04),
  `:608-635` `CalendarDay` a reutilizar en `AddHolidaysResult.days` (D-01)
- `market_data_client/models.py:200-265` — patrón `received_at` client-stamped, NO aplica a los
  modelos de esta fase
- `higyrus_client/_core.py:457` y `iol_client/_core.py:329,344,412` — patrón de parser decorado
  `@_decode._response_parser` (D-05)
- `verification/test_main_market_data_no_gate_bypass.py:72` — AST parsing del driver, patrón a
  adaptar (no reusar directo) para el guard AST de client.py/aio.py (D-07)
- `packages/market-data-client/tests/test_calendar_write.py:258-272,345-357` — captura de request
  pieza-por-pieza, base a extender para el byte-identical test (D-08)

### Established Patterns
- Parsers a dividir: `market_data_client/_core.py:280-285` (`parse_health_response`, sirve
  `get_health`+`get_health_feed`, usado en `client.py:429,435`) y `_core.py:1083-1114`
  (`parse_calendar_write_response`, sirve ambos endpoints de holidays)
- Mutation gate: `_ensure_mutation_allowed()` definida en `client.py:265`/`aio.py:222`, primer
  statement literal de 8 métodos (`client.py:574,585,600,642,656,676,699,721`;
  `aio.py:582,593,608,650,664,685,708,730`)
- Blast radius de tests a re-mockear: `test_calendar_write.py`, `test_calendar_write_async.py`
  (~132 líneas de refs), 18 hits de `"status": "ok"` en tests de higyrus
- `tools/check_decode_intactness.py:625-662` — Check D, roster de paquetes; ni `models.py` ni
  `types.py` entran en su alcance

### Integration Points
- `higyrus_client/client.py`/`aio.py` — `get_health` método + shim, sync + async (4 sitios)
- `market_data_client/client.py`/`aio.py` — `get_health`/`get_health_feed`/`add_holidays`/
  `delete_holiday`, método + shim, sync + async (hasta 16 sitios)
- `main_market_data.py:628-643,2381-2389` y `main_higyrus.py:670,685` — sitios del driver que
  necesitan `to_dict()` (D-03), mismo patrón que los sitios D-07 de `30-CONTEXT.md`
- `.github/workflows/ci.yml` job `lint` — donde se cablea el nuevo existence-check (D-12)
- `pyproject.toml:97` (mypy `files`) y `ci.yml:85` (loop mypy-tests) — market-data ausente, fuera
  de alcance de esta fase (D-13, Phase 32 D-16)
</code_context>

<specifics>
## Specific Ideas

- El operator confirmó el set completo de assumptions sin correcciones (incl. reutilizar
  `CalendarDay`, dividir ambos parsers compartidos, construir el guard AST desde cero, y el
  tratamiento docstring-only de wallets/ámbito sin tocar `check_decode_intactness.py`).
</specifics>

<deferred>
## Deferred Ideas

- Contenido real de `Literal` en los `types.py` nuevos de higyrus/iol/market-data/ambito/wallets —
  Phase 33 (censo vivo, DT-07 / D-lock RESPONSE-Literal de Phase 29)
- Enrolamiento de `market-data-client` en mypy `files`/import-linter/`ci.yml:85` loop — Phase 32
  (D-16)
- Gate AST de superficie (cero `Any`/`dict[str, Any]` en `__all__`) — Phase 32 (GATE-TYP-01)
- Actualización formal de `29-WALLETS-EXEMPTION.md` reconociendo que wallets ahora tiene
  `models.py`/`types.py` vacíos — decisión abierta (D-10), posiblemente Phase 32 o una nota liviana
  en esta fase

### Reviewed Todos (not folded)
None — no pending todos matched this phase.
</deferred>
