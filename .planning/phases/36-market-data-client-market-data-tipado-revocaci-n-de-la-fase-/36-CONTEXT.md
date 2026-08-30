# Phase 36: `market-data-client` — `market_data` tipado + revocación de la Fase 33 - Context

**Gathered:** 2026-08-29 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

El consumidor de `market-data-client` escribe `snapshot.market_data.last.price` y esa expresión
compila bajo mypy strict y nunca lanza — con el payload real, con `market_data` ausente, con
`null` y con la fila no-data. Alcance = **solo `market-data-client`** (paraleliza con Phase 37
matriz y Phase 38 iol/auditoría, ambas fuera de este alcance). No incluye bump de versión ni
publicación (Phase 40) ni verificación en vivo contra develop (Phase 39) — esta fase tipa y
revierte, la verificación real llega después.

Requirements: NOBJ-MD-01, NOBJ-MD-02.
</domain>

<decisions>
## Implementation Decisions

### Modelos nuevos + alias (D-NO-05)

- **D-01:** Tres clases nuevas en `models.py`, copia local del patrón matriz (sin import
  cross-package, D-NO-06): `BookLevel {price: float | None, size: int | None}`,
  `EntryValue {price: float | None, size: int | None, date: int | None}`,
  `MarketDataEntries` (contenedor) con `BI`/`OF: list[BookLevel]` (default `field(default_factory=list)`),
  `LA`/`SE`/`CL`/`OI: EntryValue` (Null Object vía `field(default_factory=EntryValue.empty)`).
- **D-02:** El roster de escalares de `MarketDataEntries` incluye SOLO las 10 claves observadas
  en la captura real de Phase 33 (`BI`, `CL`, `HI`, `LA`, `LO`, `OF`, `OI`, `OP`, `SE`, `TV`) — no
  el set más amplio de matriz (`IV`/`EV`/`NV`/`ACP`). Un campo real no modelado llega como "extra"
  no fatal (divergencia reportada, no crash) hasta que Phase 39 lo corrija in-cycle.
- **D-03:** Las propiedades alias (`last → LA`, `bids → BI`, `offers → OF`, `settlement → SE`,
  `close → CL`, `open_interest → OI`) son `@property` de solo lectura simples, SIN caché/memoización
  — la forma exacta ya está fijada por el fixture `_AliasShaped`/`_AliasFree` de
  `packages/market-data-client/tests/test_null_object.py:191-201` (criterio 5 de Phase 35). El
  roster `_safemodel_classes()` de ese mismo archivo espera exactamente 3 clases nuevas
  (`>= 16`, medido en 16 pre-Phase-36).

### Reversión SC-2 (Fase 33) + baja de la maquinaria de mapping

- **D-04:** `MarketDataSnapshot.entries: list[str]` (sin `| None`) y
  `MarketDataSnapshot.market_data: MarketDataEntries` (sin `| None`, Null Object nunca `None`) —
  ambos vuelven a REQUIRED sin default explícito a nivel dataclass; el walker
  (`_decode.py:436-506`) ya colapsa `null`/ausente a `[]`/instancia vacía SIN emitir divergencia
  para campos no-opcionales de tipo lista/modelo (política NOBJ-02, Phase 35). `staleness_seconds`
  y `note` quedan `| None` (hojas, D-NO-03) — sin cambios.
- **D-05:** `_mapping_value`, `_apply_mapping_policy`, `_is_mapping`, `_strip_optional` se
  eliminan enteros de `models.py`, junto con sus tests de precondición
  (`test_core.py` líneas ~1156-1174 y ~1453-1454; `test_decode.py` líneas ~673-706, ~1328-1373) —
  no tienen otro uso en el paquete fuera de la maquinaria de mapping. El módulo `models.py` ya
  documenta esta baja explícitamente ("Phase 36 retires this paquete's mapping machinery
  outright", línea 259).
- **D-06:** `LatestRequest.entries: list[str] = field(default_factory=list)` (revierte el
  widening); `to_dict()` sigue omitiendo la clave `entries` cuando la lista está vacía
  (`if self.entries:` en vez del actual `is not None`) — se preserva la semántica actual de
  "ausente = todas" en vez de introducir `"entries": []` explícito, porque no hay evidencia en el
  repo de que el servidor distinga ambos casos.

### `test_snapshot_no_data_row.py` — migración de semántica

- **D-07:** Las aserciones `row.entries is None` / `row.market_data is None` pasan a
  `row.entries == []` / `bool(row.market_data) is False` (equivalente a
  `row.market_data == MarketDataEntries.empty()`); `row.staleness_seconds is None` NO cambia
  (hoja, sin tocar). El docstring del módulo debe referenciar la revocación del checkpoint 33-07
  (SC-2, "fix-shape-now") y el plan fuente `.future_plans/api-tipada-null-objects.md`.
- **D-08:** El docstring de `models.py` (línea 1 en adelante, y el bloque específico de
  `MarketDataSnapshot`) debe documentar explícitamente la revocación del widening de Phase 33
  con referencia al checkpoint que revoca, siguiendo el mismo patrón que ya usó Phase 33 para
  documentar el widening original.

### Versionado — fuera de alcance de esta fase

- **D-09:** Esta fase NO bumpea versión ni publica — ni `pyproject.toml`, ni `__version__`, ni
  CHANGELOG. El bump breaking + changelog callout + tabla de migración vieja→nueva quedan
  íntegramente para la Phase 40 (`PUB-NOBJ-01`), replicando el patrón v1.6 (Phase 30 tipó
  `iol-client`, Phase 34 publicó). `main_market_data.py` sí se actualiza para consumir por
  encadenamiento profundo en sus sitios reales (parte del alcance de esta fase, SC5).

### Claude's Discretion

- La ubicación exacta de las 3 clases nuevas dentro de `models.py` (sección "Market data" cerca
  de `MarketDataSnapshot`) y el orden de los campos dentro de `MarketDataEntries` quedan a
  discreción de la implementación, siguiendo el orden wire observado en la captura
  (`BI, CL, HI, LA, LO, OF, OI, OP, SE, TV`).
- El tratamiento de `_ENDPOINT_OPTIONAL = frozenset({"note", "entries"})` en
  `main_market_data.py` (usado por la herramienta de captura de schema, no por los modelos) no
  quedó decidido explícitamente — el planner debe verificar si sigue siendo correcto una vez que
  `entries` nunca es genuinamente ausente del payload modelado (aunque puede seguir ausente del
  wire crudo).

### Folded Todos

Ninguno — `todo.match-phase 36` no encontró coincidencias.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.future_plans/api-tipada-null-objects.md` — plan fuente completo del milestone v1.7, Fase B
  (= esta fase) con el inventario de violaciones y los principios D-NO-01..06.
- `.planning/ROADMAP.md` (sección "Phase 36", líneas 78-91) — goal + 5 success criteria formales.
- `.planning/REQUIREMENTS.md` — NOBJ-MD-01, NOBJ-MD-02 (texto de requisito verbatim).
- `.planning/verification/schemas/market-data-client/get-market-data.json` — captura real del
  wire de `/marketdata` (Phase 33), fuente de verdad para el roster de campos de
  `MarketDataEntries`.
- `packages/matriz-client/src/matriz_client/models.py` (líneas 387-428) — implementación de
  referencia del patrón Null Object (`MarketDataLevel`/`MarketDataEntryValue`/`MarketDataSnapshot`)
  a espejar como copia local, NO como import.
- `packages/market-data-client/tests/test_null_object.py` (líneas 178-311) — fixtures
  `_AliasShaped`/`_AliasFree` y tests de criterio 5 de Phase 35 que YA fijan la forma exacta del
  alias que esta fase debe introducir; el conteo `>= 16` en `test_the_model_roster_is_not_vacuous`.
  Comentario explícito: "The exact shape Phase 36 introduces: wire fields + a read-only alias."
- `packages/market-data-client/src/market_data_client/_decode.py` (líneas 417-529, especialmente
  436-506) — el walker que ya implementa el colapso silencioso null→vacío para campos
  modelo/lista no-opcionales (NOBJ-02); no requiere cambios, sólo debe dejar de necesitar el
  parche de mapping.
- `packages/market-data-client/tests/test_snapshot_no_data_row.py` — test completo a migrar de
  semántica `is None` a semántica de veracidad/lista vacía.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- El patrón Null Object completo (contenedor + entry escalar + lista de niveles) ya existe y
  funciona en producción en `matriz_client.models.MarketDataSnapshot` — es la implementación de
  referencia citada explícitamente por el plan fuente. Se copia el PATRÓN, nunca el código
  (D-NO-06, no-shared-code).
- El walker `_decode.py` ya soporta el colapso silencioso de campos modelo/lista no-opcionales
  desde Phase 35 (NOBJ-02) — no hace falta tocar `_decode.py` en esta fase, sólo dejar de
  necesitar el mapping-pass compensatorio que estaba ahí porque el walker no tiene rama `dict`.
- `SafeModel.empty()` / `__bool__()` (Phase 35, D-NO-04) ya están disponibles en la base de
  `market-data-client` y funcionan tal cual para las 3 clases nuevas — no requieren ningún cambio
  a la base.

### Established Patterns

- Todo modelo público sigue wire-verbatim en el nombre de campo (`LA`, `BI`, etc.), con alias
  `@property` de solo lectura para ergonomía (D-NO-05) — el walker es ciego a `@property` porque
  usa `get_type_hints()`/`dataclasses.fields()`, nunca `dir()` o introspección de atributos.
- Toda clase `SafeModel` nueva necesita: `@dataclass(frozen=True, slots=True)`, herencia de
  `SafeModel`, campos wire-verbatim, sin `received_at` salvo que sea un snapshot de primera clase
  (no es el caso de `BookLevel`/`EntryValue`/`MarketDataEntries` — son sub-estructuras, no
  snapshots).
- Todo cambio de lógica se espeja en `client.py` y `aio.py` (D-NO-06) — pero esta fase toca
  únicamente `models.py` y sus tests; `client.py`/`aio.py` no tienen lógica de decode propia que
  espejar (el decode vive todo en `models.py` vía `SafeModel.from_api`/`empty`), así que la
  paridad sync/async debería seguir sosteniéndose sin tocarlos — a confirmar en research/plan.

### Integration Points

- `main_market_data.py` consume `MarketDataSnapshot` en `probe_market_data_sync`/
  `probe_market_data_async` (líneas ~825-850, ~1136+) — debe actualizarse para ejercer
  encadenamiento profundo real (`snapshot.market_data.last.price`, etc.) en sus sitios reales,
  per SC5 del roadmap.
- `_ENDPOINT_OPTIONAL = frozenset({"note", "entries"})` en `main_market_data.py` (línea 115) es
  parte de la herramienta de captura de schema — su relación con el nuevo tipado no está resuelta
  y queda para research/plan (ver "Claude's Discretion").
</code_context>

<specifics>
## Specific Ideas

Ninguna referencia particular adicional del usuario — las asunciones presentadas fueron
confirmadas sin corrección ("Sí, proceder").
</specifics>

<deferred>
## Deferred Ideas

- Bump de versión, changelog callout y tabla de migración vieja→nueva de `market-data-client` —
  explícitamente Phase 40 (`PUB-NOBJ-01`), no esta fase.
- Verificación en vivo del encadenamiento profundo contra develop — explícitamente Phase 39
  (`LIVE-NOBJ-01`), no esta fase.
- Ampliar el roster de `MarketDataEntries` a los campos `IV`/`EV`/`NV`/`ACP` de matriz sin
  evidencia de wire propio — descartado por ahora (D-02); si aparecen en vivo en Phase 39, se
  corrigen in-cycle ahí.

### Reviewed Todos (not folded)

Ninguno — `todo.match-phase 36` no encontró coincidencias.
</deferred>
