# Phase 37: `matriz-client` — dicts residuales tipados + alias - Context

**Gathered:** 2026-08-29 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

La implementación de referencia del patrón Null Object (`matriz-client`) queda ella misma sin
`dict[str, Any]` en su superficie pública y expone la misma ergonomía de alias que market-data
(Phase 36), compartida por la superficie REST y los frames de WebSocket. Requisitos: NOBJ-MTZ-01,
NOBJ-MTZ-02. Restricción heredada innegociable: `matriz-client` sigue bloqueado para corridas en
vivo por el assert de política D-MATZ-33 (`main_matriz.py:2548`, destino `LIVE-MATZ-33`) — no se
rodea bajo ninguna circunstancia en esta fase.

Paquetes disjuntos con 36 (`market-data-client`) y 38 (`iol-client` + auditoría higyrus/ámbito/
wallets) — este phase toca **solo** `matriz-client` y, por la naturaleza cross-package del gate,
`tools/check_surface_types.py` (ver D-01 abajo). No toca `packages/market-data-client/`,
`packages/iol-client/`, ni ningún otro paquete cliente.
</domain>

<decisions>
## Implementation Decisions

### D-01 — Gate extension (`tools/check_surface_types.py`)
- **D-01a:** El gate compartido `tools/check_surface_types.py` (step del job `lint`, cross-package,
  usado por los 6 paquetes) gana una dimensión nueva de escaneo: anotaciones de campo de dataclass
  (`ast.AnnAssign` dentro de una `ClassDef` exportada), no solo tipos de retorno de función como
  hoy. Confirmado por ejecución real: `uv run python tools/check_surface_types.py` reporta
  "0 violations" HOY con los 5 sitios `dict[str, Any]` en su lugar — el gate estructuralmente
  nunca los mira (`_candidates_for` solo produce `FunctionDef`/`AsyncFunctionDef`,
  `tools/check_surface_types.py:495-514`). Vive en el gate compartido, no en un test matriz-local
  (mismo argumento D-05/D-12 que el propio script documenta: cross-package by nature, y
  `verification/` nunca ejecuta en CI).
- **D-01b:** El predicado de campo es **angosto**: banea `dict[str, Any]` y `Any` desnudo
  únicamente — NO cada mención de `Any` en la anotación (a diferencia del predicado de retorno
  existente, `_annotation_mentions_any`). Medido: un predicado amplio reenrojecería
  `market-data-client` (`CalendarConfig.warnings: list[Any]` y `CalendarConfigPreview.warnings:
  list[Any]`, ambos exportados — `packages/market-data-client/src/market_data_client/models.py:
  943,1034`), un paquete fuera de alcance de esta fase (disjunto con 36/38). Fuera de alcance:
  tocar o exentar `warnings` de market-data — eso es decisión de otra fase si se decide abordar.
- **D-01c:** `UnknownFrame.raw` es la única exención declarada del predicado de campo, atada por
  nombre de clase+campo (no por naming pattern genérico como el resto de las exenciones DT-06),
  con motivo explícito en el código del gate: el escape hatch documentado de frames desconocidos
  (ya justificado en el docstring existente de `UnknownFrame`, Phase 29/35).
- **D-01d:** Se agrega un fixture RED al estilo `packages/iol-client/tests/test_surface_types_red.py`
  que prueba que el gate detecta un campo `dict[str, Any]` reintroducido — necesario porque el
  gate hoy es vacuamente verde sobre esta clase de violación.

### D-02 — `AccountReport.portfolio`
- **D-02:** `portfolio` se retipa a `float | None` (hoja escalar D-NO-03), NO a un modelo/mapping.
  Evidencia: `packages/matriz-client/documentation/Primary-API.md:1894` muestra
  `"portfolio": 60240` — un número, no un objeto — y ese valor coincide con
  `"totalMarketValue": 60240` de `detailedPosition` para la misma cuenta (`:1706`), consistente
  con ser un valor de mercado de cuenta. Sale por completo del trabajo de mapping-fields; deja de
  pasar por `_mapping_value`/`_apply_mapping_policy`.

### D-03 — Envelope unwrap de los parsers Risk (`_core.py`)
- **D-03:** El fix de envelope-unwrap de `get_detailed_positions`/`get_account_report` es
  **in-scope** de esta fase, junto con el tipado. Evidencia de la sospecha: ambos parsers
  (`_core.py:914-918`, `:941-945`) pasan el body raíz verbatim a `from_api` bajo el comentario
  "NO envelope key, D-07", pero el vendor doc muestra body envuelto
  (`{"status":"OK","detailedPosition":{...}}` en `Primary-API.md:1701-1703`,
  `{"status":"OK","accountData":{...}}` en `:1817-1819`), y el endpoint hermano
  `get_positions` SÍ desenvuelve (`_core.py:885-889`, `unwrap(data, "positions", path)`). Ningún
  test actual lo cubriría (codifican la forma plana). Tipar sin corregir el unwrap dejaría
  `report`/`detailedAccountReports` decodificando siempre desde el nivel equivocado — campos
  tipados pero inertes. El fix se espeja sync/async (D-NO-06) con regresión mockeada nueva.
  **Si en la ejecución se determina que el envelope NO está roto** (evidencia contraria
  encontrada), esta decisión se revierte sin bloquear el resto de la fase — no es una precondición
  dura de las otras decisiones.

### D-04 — Provenance de payloads no observados en vivo
- **D-04a:** `packages/matriz-client/documentation/Primary-API.md` (vendor doc committeado en el
  propio paquete) cuenta como evidencia admisible para tipar, pero bajo una **tercera clase de
  procedencia nueva**: `vendor-documented, unmeasured` — distinta de `baseline` (captura viva
  committeada, ej. `.planning/verification/schemas/matriz-client/get-instrument-detail.json`) y de
  `capture` (nueva corrida en vivo, no disponible en esta fase por D-MATZ-33). Nunca se presenta
  como si fuera una captura real.
- **D-04b:** Formato de la declaración de procedencia: el patrón de dos artefactos ya establecido
  en Phase 36 — (1) un párrafo de docstring por clase citando la fuente exacta (path + rango de
  líneas de `Primary-API.md`, o el nombre del archivo baseline + fecha de captura), espejo de
  `MarketDataEntries`' docstring de Phase 36 (`market_data_client/models.py:314-316`: "Live-capture
  provenance: ..."); (2) una entrada en el ledger existente
  `.planning/verification/matriz-client-findings.md` (ya usa columnas `Class`/`Status`, ya soporta
  `NO-FIX`/`EXPECTED` terminal) para cualquier fila que quede como declarada-no-observada. NO se
  crea un nuevo formato de registro de procedencia.
- **D-04c:** `tickPriceRanges` es la única de las cuatro fields con baseline de captura viva real
  (`get-instrument-detail.json`, 2026-06-10) — las otras tres (`report`, `detailedAccountReports`,
  `portfolio` si terminara siendo modelo) dependen de `vendor-documented, unmeasured` (D-04a) o
  quedan explícitamente declaradas no observadas si D-07 (abajo) decide un modelo mínimo sin
  siquiera esa evidencia.

### D-05 — `tickPriceRanges`
- **D-05:** Se retipa a `dict[str, TickPriceRange]` (mapping string-keyed), NO a
  `list[TickPriceRange]`. Las tres muestras observadas (baseline committeado + 2 muestras del
  vendor doc en `Primary-API.md:330,378,454`) coinciden en 3 campos (`lowerLimit`, `tick`,
  `upperLimit`) pero todas tienen una sola key (`"0"`) — nada observado establece que las keys
  sean contiguas/ordenadas, así que aplanar a lista asertaría una propiedad de secuencia no
  demostrada. Requiere D-06 (upgrade del axis de mapping) para decodificar correctamente.

### D-06 — Fate de `_mapping_value` / `_apply_mapping_policy`
- **D-06:** El axis (`models.py:99-197`) se **actualiza**, no se elimina. A diferencia de la
  eliminación de Phase 36 (válida porque `market_data` pasó a ser un modelo anidado que el walker
  ya sabe decodificar vía su rama `_is_model`), un hint `dict[str, Model]` sigue sin match en
  ninguna rama de `walk_field` (`_decode.py`: no tiene rama `dict` — cae al pass-through bare de
  `:555`), así que el axis sigue siendo necesario para que los valores internos se decodifiquen
  como modelos y no como dicts crudos. El axis gana el tipo de elemento y enruta cada valor a
  través de `_decode.walk_field` (mismo sink, mismo strict mode, mismo dedupe) en vez de solo
  coercionar el contenedor externo a `{}`. **No se toca `_decode.py`** — el walker compartido
  byte-verbatim entre paquetes queda intacto (D-NO-06, `check_decode_intactness.py`); el axis sigue
  viviendo en `matriz_client/models.py` como mecanismo call-site matriz-only.
- Tras D-02 (portfolio pasa a escalar) y la disposición de `report`/`detailedAccountReports`
  (D-07), el axis puede terminar aplicándose solo a `tickPriceRanges` — eso es aceptable y no
  requiere generalizarlo más allá de lo que estos campos necesitan.

### D-07 — Profundidad de modelado de `DetailedPosition.report` / `AccountReport.detailedAccountReports`
- **D-07:** Disposición **mínima**: solo se modelan los campos escalares con evidencia directa
  (ej. los tres `instrument*Size` del registro interno de `report`), NO el árbol completo de 2
  niveles + `detailedPositions` anidado que el vendor doc sugiere (`Primary-API.md:1707-1789`).
  Las claves no declaradas del payload real llegan como divergencias `extra` no-fatales
  (`_decode.py`, mecanismo ya existente), consistente con SC-1 ("nunca un modelo inventado
  presentado como observado") y con el propio precedente de `MarketDataEntries` (roster cerrado +
  reporting de divergencias para lo no declarado, `market_data_client/models.py:318-352`).
  El nivel exterior de mapping (`contractType` → `symbol` → registro) sigue tipado como
  `dict[str, dict[str, <modelo mínimo>]]` vía el axis D-06 — es la única forma honesta de
  representar dos niveles de keys abiertas sin inventar un enum de `contractType` ni una lista de
  símbolos.

### Claude's Discretion
- Naming exacto de las clases nuevas (`TickPriceRange`, modelo mínimo de `report`/
  `detailedAccountReports`) — sigue la convención `PascalCase` matching wire/domain existente.
- Ubicación exacta del párrafo de docstring de procedencia dentro de cada clase (formato libre
  mientras cite el path + evidencia, siguiendo el ejemplo de `MarketDataEntries`).
- Si D-03 (envelope fix) resulta no aplicar tras investigación en ejecución, decidir sin bloqueo
  cómo documentarlo (nota en el mismo docstring de procedencia).

### Folded Todos
Ninguno — `todo.match-phase 37` no encontró coincidencias (`todo_count: 0`).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — Phase 37 section (goal, success criteria, requirements, restricción
  D-MATZ-33)
- `.planning/REQUIREMENTS.md` — NOBJ-MTZ-01, NOBJ-MTZ-02 (líneas 28-29)
- `.future_plans/api-tipada-null-objects.md` — plan fuente del milestone v1.7: principios
  D-NO-01..06, Fase C (matriz-client), inventario de violaciones, riesgos
- `packages/matriz-client/src/matriz_client/models.py` — los 5 sitios `dict[str, Any]`
  (`InstrumentDetail.tickPriceRanges:344`, `DetailedPosition.report:481`,
  `AccountReport.detailedAccountReports:495`, `AccountReport.portfolio:496`,
  `UnknownFrame.raw:548`), el axis `_mapping_value`/`_apply_mapping_policy` (líneas 94-197),
  `MarketDataSnapshot` (líneas 418-441), `MarketDataFrame` (líneas 508-515)
- `packages/matriz-client/src/matriz_client/_core.py` — parsers Risk sin envelope unwrap
  (`:914-918`, `:941-945`) vs. `get_positions` que sí desenvuelve (`:885-889`)
- `packages/matriz-client/src/matriz_client/_decode.py` — walker compartido byte-verbatim
  (`walk_model`/`walk_field`, sin rama `dict`); NO se toca en esta fase
  (`tools/check_decode_intactness.py` lo bloquea)
- `packages/matriz-client/src/matriz_client/ws_client.py` — `_parse_frame`, construcción de
  `MarketDataFrame.from_api`/`UnknownFrame`
- `packages/matriz-client/documentation/Primary-API.md` — evidencia vendor-documented para
  `tickPriceRanges` (líneas 330, 378, 454), `DetailedPosition.report` (líneas 1707-1790),
  `detailedAccountReports` (líneas 1826-1890), `portfolio` (línea 1894), envelope keys
  `detailedPosition`/`accountData` (líneas 1701-1703, 1817-1819)
- `.planning/verification/schemas/matriz-client/get-instrument-detail.json` — único baseline de
  captura viva real entre los 4 campos (`tickPriceRanges`)
- `.planning/verification/matriz-client-findings.md` — ledger existente para declarar filas
  no-observadas (D-04b)
- `tools/check_surface_types.py` — gate a extender (D-01); leer docstring completo (líneas 1-120)
  antes de tocarlo, especialmente D-05/D-12 (por qué vive en `lint`, no en `test`/`verification/`)
- `packages/iol-client/tests/test_surface_types_red.py` — patrón de fixture RED a espejar (D-01d)
- `packages/matriz-client/tests/test_null_object.py` — fixtures de Phase 35 que ya prueban que las
  properties son invisibles al walker (`_AliasShaped`/`_AliasFree`, líneas 196-215,
  `test_property_aliases_are_invisible_to_get_type_hints`:292-311,
  `test_adding_a_property_alias_does_not_change_the_divergence_count`:314-326); roster floor
  `_safemodel_classes()` `>= 17` en línea 229 — subir tras agregar clases nuevas
  (mismo patrón que Phase 36 D-03, ver `.planning/phases/36-market-data-client-market-data-tipado-
  revocaci-n-de-la-fase-/36-CONTEXT.md:33-38`)
- `.planning/phases/36-market-data-client-market-data-tipado-revocaci-n-de-la-fase-/36-CONTEXT.md`
  y `36-DEFERRED-market-data-leaves.md` — precedente directo: mismo milestone, mismo patrón de
  Null Object aplicado un phase antes, mismo formato de docstring de procedencia
  (`MarketDataEntries`), mismo mecanismo de "deferred to operator decision" si algo queda sin
  resolver
- `.planning/milestones/v1.6-phases/29-decoder-observable/29-SEMANTICS-MATRIX.md` — vocabulario de
  políticas por-campo (Section 3, exenciones a nivel de modelo) con el que este phase debe
  mantenerse consistente
- `.planning/research/ARCHITECTURE.md:397` — ya nombra este mismo blind spot del gate
  ("extender el gate a campos de modelos exportados con lista de exenciones documentada")
- `main_matriz.py:2517-2548` — assert de política D-MATZ-33 (hostname remarkets), no se rodea
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Patrón Null Object de referencia ya correcto en `MarketDataSnapshot`/`MarketDataEntryValue`/
  `MarketDataLevel` — sirve de plantilla directa para las clases nuevas de esta fase.
- `_SafeModel.empty()`/`__bool__` (Phase 35) ya garantizados en la base — las clases nuevas los
  heredan gratis sin trabajo adicional.
- Fixtures de Phase 35 (`test_null_object.py`) ya prueban invisibilidad de properties al walker —
  no se necesita escribir esa prueba desde cero, solo aplicarla a los alias nuevos.
- Ledger `matriz-client-findings.md` y su API programática (`main_matriz.py:398`) ya existen para
  declarar filas no-observadas sin inventar un formato nuevo.
- Patrón de docstring de procedencia de `MarketDataEntries` (Phase 36) — copiar la forma, no el
  contenido.

### Established Patterns
- D-NO-06: todo cambio de lógica se espeja `client.py`/`aio.py`; `_decode.py` se replica
  byte-verbatim (no se toca en esta fase).
- Gates existentes son ratchets, nunca se debilitan bajo presión (`check_surface_types.py:116-119`
  lo dice explícito) — si el predicado de campo reenrojece algo fuera de alcance, la respuesta es
  angostar el predicado (D-01b), no exentar por nombre libre ni tocar el paquete ajeno.
- "Roster cerrado + reporting de divergencias para extras" es el patrón ya aceptado (Phase 36,
  `MarketDataEntries`) para modelar un payload solo parcialmente observado — D-07 lo reusa.

### Integration Points
- `tools/check_surface_types.py` corre como step del job `lint` en `.github/workflows/ci.yml`
  (línea ~61-66) — cross-package, sin lista hardcodeada de paquetes (roster se lee de `packages/`
  en runtime).
- `_mapping_value`/`_apply_mapping_policy` se invoca desde `from_api` de las clases afectadas —
  cualquier cambio a su firma debe revisar todos los call sites en `models.py`.
- `_core.py` parsers Risk (`_parse_risk_response`, `get_detailed_positions`/`get_account_report`
  builders/parsers) — el fix de envelope (D-03) toca sync y su espejo async en `aio.py`.
</code_context>

<specifics>
## Specific Ideas

Ninguna referencia particular más allá de las decisiones ya capturadas arriba — el operator no
proveyó ejemplos adicionales durante esta sesión (modo assumptions, "Yes, proceed" tras revisión
del resumen completo).
</specifics>

<deferred>
## Deferred Ideas

- Exención o retipado de `CalendarConfig.warnings`/`CalendarConfigPreview.warnings`
  (`market-data-client`, `list[Any]`) descubierto como efecto colateral de extender el predicado
  del gate — explícitamente fuera de alcance de esta fase (D-01b), candidato para una fase futura
  de `market-data-client` o para el propio backlog de auditoría (Phase 38 cubre iol +
  higyrus/ámbito/wallets, no market-data).
- Modelado completo del árbol de 2 niveles de `DetailedPosition.report` (`detailedPositions`
  anidado con ~20 campos + `detailedDailyDiff` de 8) — deferido por D-07 hasta que exista una
  captura en vivo real (post `LIVE-MATZ-33`) que confirme la forma completa.
- Verificación en vivo real de las 3 fields Risk (`report`, `detailedAccountReports`, `portfolio`
  si termina requiriendo evidencia adicional) — bloqueada por D-MATZ-33 en esta fase; destino ya
  nombrado en el milestone (`LIVE-NOBJ-01`, Phase 39).

### Reviewed Todos (not folded)
Ninguno — `todo.match-phase 37` no encontró coincidencias.
</deferred>
