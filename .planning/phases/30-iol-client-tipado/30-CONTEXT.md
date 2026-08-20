# Phase 30: `iol-client` tipado - Context

**Gathered:** 2026-08-19 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

El consumidor de `iol-client` accede a cotizaciones, series históricas e instrumentos por **atributo tipado** — un typo lo caza mypy en el editor, no el servidor en producción. Requirement: TYP-01. Primera superficie que ejercita el decoder observable de Phase 29 end-to-end.

Alcance fijo (criterios ya refinados en roadmap): `models.py` nuevo derivado de los schemas capturados en vivo (`.planning/verification/schemas/iol-client/*.json`), 16 firmas migradas (4 funciones × método/shim × sync/async) a modelos — cero `Any`/`dict[str, Any]` —, `main_iol.py` a acceso por atributo en sus 2 sitios reales, fixture RED de typecheck, `to_dict()` como escape hatch en el mismo release, README con callout de ruptura alimentando el bump 0.2.0→0.3.0 (que ejecuta F34). `mercado`/`plazo` quedan `str` (DT-07 → F33); ningún campo RESPONSE gana `Literal` (D-09 de F29).
</domain>

<decisions>
## Implementation Decisions

### Diseño de modelos
- **D-01:** 4 dataclasses `frozen=True, slots=True` sobre 2 formas de wire — `Cotizacion` (compartida por `get_quote` y cada fila de `get_historical_quotes`: mismas 20 claves camelCase), `Punta` anidado, `Instrumento` (2 claves) y `Titulo` (filas de `titulos`, 21 claves) — con base `SafeModel` copiada del template **mínimo de higyrus** (`higyrus_client/models.py:41-54`, 14 líneas: `from_api` delegando a `_decode.walk_model`, sin `empty()`, sin mapping-axis, sin `received_at`). Ni el SafeModel de market-data (mapping-axis + overrides sin campo que los justifique) ni el de matriz (política missing→`None`, opuesta al `_decode.POLICY` typed-zeros de iol).
- **D-02:** `puntas` se declara **`list[Punta] | None` en `Cotizacion`** y **`Punta` singular en `Titulo`** — `Punta` = 4 campos `float` (`cantidadCompra`/`cantidadVenta`/`precioCompra`/`precioVenta`), única forma de elemento observada en todo el corpus. El elemento de la lista de `get_quote` es **inobservado** (la captura 2026-06-06 registró `[]`) — la confirmación es trabajo de la corrida estricta de F33 (postura evidencia-primero de DT-07). NO usar `list[dict[str, Any]]` pass-through (esquiva el gate de F32 por tecnicismo).
- **D-03:** Todo campo que el corpus registra como `NoneType` se declara **`T | None`**: `descripcionTitulo`/`plazo`/`puntas` en la forma histórica; `fechaVencimiento`/`precioEjercicio`/`tipoOpcion` en `Titulo`. Razón: el walker de F29 trata Optional como opt-in explícito sin divergencia (`_decode.py:436-442`); no-Optional pre-carga el censo de F33 con ~6 divergencias garantizadas que no son defectos (misma clase que S-5 de F29).
- **D-04:** `cantidadOperaciones` respeta el corpus por-modelo: `int` en `Cotizacion` (quote/histórico), `float` en `Titulo` — dos declaraciones distintas, no una unificada que reportaría divergencia en cada llamada.

### Wiring en `_core` + decoder F29
- **D-05:** Los 4 parsers de `_core.py:327-360` se reescriben **in place** para retornar modelos, cada uno decorado con `@_decode._response_parser` (dueño del `DecodeScope` per-response: dedupe colapsa un `list[Model]` a 1 registro por campo), espejando el patrón higyrus `_core.py:457-500`. `_core` → `models` → `_decode` no viola ningún contrato de import-linter; no se necesita contrato nuevo.
- **D-06:** `parse_get_instruments_by_type_response` conserva el unwrap del envelope (`data.get("titulos", [])`) como paso raw-dict ANTES de construir modelos — el envelope `titulos` no se modela. `parse_get_instruments_response` gana guard `isinstance(raw, list)` (hoy retorna `Any` pass-through; el wire real es una lista top-level `[{instrumento, pais}]`). Los **~12 tests que mockean `get_instruments` como dict `{"instrumentos": …}`** (forma que el schema vivo contradice) se **re-mockean mecánicamente** como lista — lo usan solo como llamada autenticada barata; el payload es incidental. NO adoptar leniency dict-o-lista (reintroduce el bug del `[]` silencioso).

### Migración del driver + harness
- **D-07:** Los "2 sitios reales" de acceso por atributo son `main_iol.py:316` y `:395` (`quote.get("ultimoPrecio")` → `quote.ultimoPrecio`). Además hay **≥5 sitios estructurales** que consumen vía `verification.schema.schema_of` y deben recibir `to_dict()` (`:918-919` parity probe, `:1066`, `:1102`, `:1164` `_write_or_check_schema`): sin eso la próxima corrida viva escribe `"schema": "Cotizacion"` en los baselines committeados y F33 arranca corrupto. Esta es la razón operativa del criterio 5.
- **D-08:** `to_dict()` = **`dataclasses.asdict(self)`** (recursivo: `Punta` anidado se aplana a dict plano), anotado `-> dict[str, Any]`. Primer `to_dict()` sobre un modelo de *response* en el monorepo (los de market-data son request models); F32 ya lo nombra en su lista de exenciones. Round-trip lossy conocido y aceptado: `null` de wire decodificado a Optional-default y claves no declaradas desaparecen del snapshot — blind spot documentado, contrastable en F33.

### Gates, prueba RED, release
- **D-09:** El gate de intactness de F29 **no se toca** (`tools/check_decode_intactness.py` hashea solo `_decode.py`; iol ya enrolado; `models.py` nuevo no afecta el digest). Sí se **regenera `verification/snapshots/iol-client-surface.txt`** (`verification/regen_snapshots.py`) — pinnea firmas con retornos y quedaría rojo invisible en CI (verification/ no corre en CI). Ruff no necesita exención camelCase (`N` no está en `select`).
- **D-10:** La fixture RED de typecheck vive en **`packages/iol-client/tests/`** (path typechequeado por el loop mypy de `ci.yml:85-94`) como typo de atributo deliberado con `# type: ignore[attr-defined]` bajo `warn_unused_ignores = true` — no-vacua en ambas direcciones (atributo existente → ignore unused → mypy error; typo cazado → ignore lo absorbe). NUNCA en `main_iol.py` (mypy no lo typechequea: `files` = `packages/*/src`). Sin subprocess-mypy (maquinaria nueva, ~10s de CI).
- **D-11:** Phase 30 **no bumpea `__version__`** (queda `"0.2.0"`); escribe la sección de changelog `### v0.3.0` en `packages/iol-client/README.md` (precedente: `market-data-client/README.md:123-193`) registrando la ruptura dict→modelo incluido el flip de truthiness; F34 ejecuta el bump (evita desincronizar el tag pipeline y un tag 0.3.0 antes de la verificación viva de F33).
- **D-12:** El README de iol hoy documenta una API que **no existe** (`IOLClient(token=...)`, `get_portfolio()` — cero apariciones en `src/`). El callout de ruptura es ilegible contra una descripción ficticia → **se corrige la sección de Uso en el mismo commit** del changelog (scope aceptado, no expansión).

### Claude's Discretion
- Nombres exactos de las clases (`Cotizacion`/`Punta`/`Instrumento`/`Titulo` son los sugeridos), orden de campos, y si `Cotizacion` histórica amerita docstring aclarando la nulabilidad diferencial — dentro de D-01/D-03.
- Forma exacta de la fixture RED (nombre del test/archivo) dentro de D-10.
- Detalle de los re-mocks de D-06 (payload mínimo por sitio).

### Folded Todos
None — no pending todos matched this phase.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — § Phase 30 (los 5 success criteria refinados; el criterio 4 fija `str` para `mercado`/`plazo` este milestone)
- `.planning/future-plans/tipado_homogeneo.md` — plan fuente con DT-01..DT-09 (DT-05 `from_api` preservado, DT-07 Literal diferido, DT-08 bump 0.3.0)
- `.planning/verification/schemas/iol-client/*.json` — los 4 schemas capturados en vivo (2026-06-06), fuente de verdad de los modelos (get-quote / get-historical-quotes / get-instruments / get-instruments-by-type)
- `.planning/phases/29-decoder-observable/29-CONTEXT.md` + `29-SEMANTICS-MATRIX.md` — semánticas del decoder, D-locks (msgspec NO-GO, RESPONSE-Literal abierto)
- `.planning/codebase/` — mapas (ARCHITECTURE, CONVENTIONS, STRUCTURE, CONCERNS)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `higyrus_client/models.py:41-54` — template `SafeModel` mínimo a copiar verbatim (D-01)
- `higyrus_client/_core.py:457-500` — patrón de parser model-returning (`@_decode._response_parser` + `_parse_list_or_raise(resp, Model)` + one-liners tipados) (D-05)
- `iol_client/_decode.py` — decoder F29 ya presente y enrolado en intactness: `POLICY` :140 (typed-zeros, `literal_enforced=False`), `walk_model` :541, branch Optional sin sink :436-442, `_response_parser` :312; modo bindeado en `client.py:459-460` / `aio.py:461-462`
- `market_data_client/README.md:123-193` — precedente de sección Changelog (D-11)
- `verification/regen_snapshots.py` — regeneración del golden file de superficie (D-09)

### Established Patterns
- Las 16 firmas actuales (todas sin tipar): `get_quote` (`client.py:514-527` método / `:673-680` shim; `aio.py:536-546` / `:693-699`) → `dict[str, Any]`; `get_historical_quotes` (`client.py:529-547`/`:683-694`; `aio.py:548-562`/`:702-713`) → `list[dict[str, Any]]`; `get_instruments` (`client.py:549-556`/`:697-699`; `aio.py:564-568`/`:715-716`) → `Any`; `get_instruments_by_type` (`client.py:558-571`/`:702-708`; `aio.py:570-579`/`:719-725`) → `list[dict[str, Any]]`
- Parsers a migrar: `_core.py:327-360` (`parse_get_quote_response`, `parse_get_historical_quotes_response`, `parse_get_instruments_response` — retorna `Any` —, `parse_get_instruments_by_type_response` — unwrap `data.get("titulos", [])`). Builders `:234-319` intactos (`ajustada` ya es `Literal` de INPUT pre-DT-07; se conserva)
- Schemas: quote/histórico comparten las mismas 20 claves camelCase; `titulos` tiene 21 claves propias; `instruments` es lista top-level `[{instrumento: str, pais: str}]`
- `puntas` — 3 formas registradas para una clave: `[]` (quote, elemento inobservado), objeto 4-float (by-type), `NoneType` (histórico)
- import-linter: `iol_client._core` ↛ `client`/`aio` (`pyproject.toml:163-167`); `models` → `_decode` sin restricción

### Integration Points
- `main_iol.py` — sitios de atributo `:316`/`:395`; sitios `schema_of` que necesitan `to_dict()` `:918-919`/`:1066`/`:1102`/`:1164`; anotaciones de probes a actualizar (`:256`, `:340`, `:402`, `:482`, `:682`, `:804`, `:889-896`, `:953-956`, `:1203-1206`, `:1536-1542`); typechequeado por NADIE, sí ruff-checked
- Blast radius de tests: ~12 sitios mockean `get_instruments` como dict (`tests/test_client.py:87,90,180,217`; `test_async_client.py:142,177`; `test_refresh_token_lifecycle.py:66,118,159,201`; `test_refresh_token_lifecycle_async.py:71,118,152,188`; `test_fixture_reaches_production.py:43,64`; `test_core.py:354-356`) → re-mock a lista (D-06); asserts de dict-indexing en quote/histórico/titulos (`test_client.py:61,70,81,90,99,112-114,148,556` + espejos async) → migran a atributo
- `packages/iol-client/tests/test_decode.py` — fixtures module-local ya con la forma "que Phase 30 generará" (docstring :8-14)
- `verification/snapshots/iol-client-surface.txt` — golden file a regenerar; su test no corre en CI (solo local/full-suite)
- `__version__ = "0.2.0"` en `iol_client/__init__.py:75`; README de 44 líneas sin Changelog y con API ficticia (D-12)
</code_context>

<specifics>
## Specific Ideas

- El operator confirmó el set completo de assumptions sin correcciones (incl. `Cotizacion` unificada quote/histórico, `asdict` recursivo, fixture RED vía `type: ignore` + `warn_unused_ignores`, y la corrección del README ficticio en el mismo commit).
</specifics>

<deferred>
## Deferred Ideas

- Confirmación del elemento de `puntas` en `get_quote` (lista capturada vacía) — corrida estricta F33 con creds (D-02)
- Promoción `mercado`/`plazo` → `Literal` con censo vivo — F33 (DT-07)
- Bump `__version__` 0.2.0→0.3.0 + tag + release — F34 (PUB-TYP-01, D-11)
- Bootstrap de `types.py` en iol (estructura uniforme ×6) — F31 (TYP-03)

### Reviewed Todos (not folded)
None — no pending todos matched this phase.
</deferred>
