# Phase 43: `market-data-client` — forma de `Instrument`/`Segment` + 5 claves `extra` tipadas - Research

**Researched:** 2026-08-31
**Domain:** Python dataclass shape correction en un paquete publicado (`market-data-client` v0.6.0) — decode walker, gates estáticos AST, y re-derivación de fixtures de test
**Confidence:** HIGH (todo medido y ejecutado en este árbol en esta sesión; cero afirmaciones de entrenamiento sobre el repo)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### `Instrument` — disposición campo por campo

- **D-01:** `Instrument` mantiene `symbol: str`, `segment: str`, `expired: bool` (los tres están
  en el wire, sin cambio).
- **D-02:** `Instrument` agrega `market_id: str`, `currency: str`, `days_to_maturity: int`,
  `maturity: str`, `outright: bool`, `subscribed: bool` — medidos en `42-WIRE-READ.md` §2, cero
  divergencia con el baseline del 2026-07-31 (delta vacío).
- **D-03:** `Instrument` agrega `active: bool | None = None` — **no** `bool` sin `| None`. La
  única fila medida trae `active: null` (F-205, `market-data-client-findings.md:1591`); declararlo
  no-nullable convertiría esa `extra` en una `missing` permanente sobre cada lectura de catálogo,
  que es exactamente la regresión que el criterio 3 de la fase prohíbe por nombre (aunque ese
  criterio habla de las 5 claves de HARN-02, el mismo principio de evidencia aplica acá).
- **D-04:** `Instrument.marketId: str` queda como **alias aditivo** (D-22, precedente verbatim de
  `Symbol.marketId` en `models.py:817-901`): se agrega `market_id` como campo wire-correcto, se
  sobre-escribe `Instrument.from_api` para espejar `market_id` → `marketId` **sólo** cuando
  `marketId` está ausente del payload (nunca pisa un valor explícito), llamando a
  `super(Instrument, cls).from_api(payload)` en dos argumentos explícitos (el `@dataclass(slots=True)`
  reconstruye la clase, así que el `super()` de cero argumentos rompe). `marketId` queda documentado
  como DEPRECATED, remoción programada para el próximo MAJOR. **Nunca** se renombra directamente —
  prohibido en `REQUIREMENTS.md § Out of Scope`.
- **D-05:** `Instrument.instrumentType: str` se **remueve**. El wire nunca lo manda (F-212/F-213,
  `market-data-client-findings.md`) y toda instancia liberada lo lee `""` — mismo patrón que la
  remoción no-breaking de `CalendarConfig.businessDays`/`CalendarDay.date`/`.marketId`/
  `.isBusinessDay` (`models.py:916-921`).

#### `Segment` — disposición campo por campo

- **D-06:** `Segment` se reemplaza por completo: `marketSegmentId`, `marketId`, `description`
  quedan **removidos** (no alias-mapeados — son nombres distintos del wire, no una variante de
  spelling de la misma clave, así que el mecanismo D-22 no aplica aquí). Se **agregan**
  `segment: str` y `live_instruments: int`.
  - **Rechazado explícitamente:** alias-mapear `marketSegmentId → segment` bajo D-22. La
    precondición de D-22 es una MISMA clave con spelling camelCase/snake_case distinto
    (`marketId`/`market_id`); `marketSegmentId` vs `segment` es un nombre diferente, no una
    variante de spelling.
  - Los tres campos declarados hoy son disjuntos del wire y `_core.py:1042-1051` ya documenta en
    prosa que toda fila de `Segment` decodifica vacía — ningún consumidor liberado puede haber
    leído nunca un valor poblado, mismo argumento D-13 de no-breaking.
- **D-07:** El antes/después de `get_segments()` (criterio 2) se demuestra **offline**, contra
  `.planning/verification/captures/market-data-wire-segments-42.json` (presente en disco,
  gitignored) + las entradas del censo F-214…F-218 — sin segunda corrida en vivo, sin segundo
  checkpoint humano bloqueante. `42-WIRE-READ.md` §4.1 advierte que `_emit_shape` está **inerte**
  para `Instrument`/`Segment` (el sample se computa como `raw[0] if isinstance(raw, list)` y el
  wire es un envelope `dict`), así que un "cero findings de `_emit_shape`" post-fix sería un falso
  verde — la evidencia real está en el censo de divergencias, no en el SHAPE-diff del driver.

#### HARN-02 — las 5 claves `extra` restantes

- **D-08:** `FeedIngestor.subscription` se tipa como una **nueva dataclass anidada
  `FeedSubscription(SafeModel)`**, no-opcional, siguiendo el precedente `FeedMarket`/`FeedPipeline`
  (`models.py:1195-1261`). `dict[str, Any]` **no es una opción disponible**: dos gates duros lo
  bloquean — (1) `tools/check_surface_types.py` (paso `surface-types` del job `lint`) reddenea
  cualquier campo de clase exportada anotado como mapping sin tipar (`_FIELD_EXEMPTIONS` tiene una
  única entrada, `UnknownFrame.raw`, y `FeedIngestor` está exportado); (2) `_decode.py` no tiene
  rama `dict` — `walk_field` cae a `return value` sin caminar ni reportar. Los 15 campos se declaran
  verbatim del blob medido (F-71, `market-data-client-findings.md:950`): `chunk_size: int`,
  `chunks: int`, `confirm_seconds: int`, `delivered_count: int`, `forced_reconnects: int`,
  `last_reconnect_reason: str`, `quarantined_count: int`, `quarantined_symbols: list[str]`,
  `requested: int`, `sent: int`, `smd_rejections: int`, `smd_resends: int`, `smd_unattributed: int`,
  `unconfirmed_count: int`, `unconfirmed_symbols: list[str]` (elemento no observado poblado —
  asunción ya registrada en `research/SUMMARY.md:141` con confianza LOW; autocorrectiva vía censo
  de divergencias si resulta mal tipada).
- **D-09:** `FeedIngestor.last_error_age_seconds: int | None = None` y
  `FeedIngestor.last_error_at: str | None = None` — **nullable**, no planos. Ambas claves están
  ausentes del baseline sano del 2026-07-31 (`last_error: NoneType`, sin las dos compañeras) y
  presentes en toda captura posterior junto con un `last_error` poblado — son condicionales a que
  exista un error, no siempre presentes. Declararlas no-nullable emitiría `missing` en cada llamada
  sana a `/health/feed`, que es precisamente lo que el criterio 3 prohíbe.
- **D-10:** `Symbol.note: str | None = None` — nullable. Presente en los acks de escritura
  (`create-symbol-sync-response.json`, `update-symbol-sync-response.json`: `"note": "str"`) y
  ausente en las filas de `GET /symbols` (`get-symbols-probe-prefix-sync.json`) — un solo modelo
  sirve los 4 endpoints (`_core.py:1086-1094`), mismo argumento de condicionalidad que D-09.
- **D-11:** `HealthFeed.symbols_never_delivered: int` — **plano, no nullable**. Ausente sólo del
  baseline stale del 2026-07-31 y presente en las tres capturas posteriores; aplica la doctrina de
  restraint option-b ya usada en el resto de `HealthFeed` (`models.py:1146-1156`).

#### Fixtures y tests — alcance de re-derivación

- **D-12:** 9 sitios de test necesitan tocarse (ninguno se renombra para que siga pasando —
  prohibido por criterio 4): `tests/test_reference_models.py` (líneas 41-55 valores viejos, línea
  183 `_ALL_MODELS`, línea 219-228 set exacto de campos de `Symbol` — debe ganar `"note"`);
  `tests/test_reference_core.py` (líneas 167-176, 185-190, bodies hand-built con claves viejas de
  `Segment`); `tests/test_reference_client.py` + su gemelo async
  `tests/test_reference_async_client.py` (línea ~78-81, mismo body stale
  `{"marketSegmentId": "DDF", "marketId": "ROFX", "description": "Dolar"}`);
  `tests/test_decode.py` (línea 664-673 `(".marketId", "missing")` sobre `Instrument`, línea
  676-689 claves viejas de `Segment`, **y** línea 1339-1360 que asserta
  `overriding == {"MarketDataSnapshot", "Symbol"}` exacto — el nuevo override de
  `Instrument.from_api` (D-04) rompe este set y debe pasar a 3 elementos, mientras que
  `overriding & nested_types == set()` sigue en pie porque nada declara un campo tipado
  `Instrument`); `tests/test_core.py` (línea 1185-1199 asserta
  `optionals == {"FeedIngestor.last_error", "FeedPipeline.last_write_error"}` exacto — cada nuevo
  `| None` de D-03/D-09/D-10 rompe este set); `tests/test_public_surface_market_data.py`
  (línea 103-121, cada subclase de `SafeModel` en `models.py` debe estar en `models.__all__` —
  `FeedSubscription` debe agregarse ahí). `tests/test_reference_envelope_unwrap.py` ya usa la forma
  real del wire (agregado en Phase 33) y **no** necesita re-derivarse, sólo aserciones más ricas.
- **D-13:** La aserción "conjunto de claves de la fixture ⊆ baseline medido" (criterio 4) es un
  **helper nuevo, explícitamente escrito**, que compara contra una fuente medida committeada (el
  blob "Actual" de F-202/F-71 en el ledger, o una fixture nueva `_MEASURED_HEALTH_FEED_43` con las
  5 claves) — **no** contra ni refresca ningún baseline `.planning/verification/schemas/market-data-client/*.json`.
  Esos baselines son write-once (D-25): `42-WIRE-READ.md` §3 los marca explícitamente
  NO-AUTORITATIVOS para esta fase, y `_write_schema_snapshot` nunca pisa un baseline que difiere.
  `tests/test_core.py::test_captured_payloads_match_the_committed_live_schemas` (línea 1055-1062)
  sigue aseverando **igualdad** contra `get-health-feed.json` sin tocarse — la fixture del
  2026-07-31 es un subconjunto estricto de la forma medida en 2026-08-31, así que ambas aserciones
  conviven sin conflicto.

#### CI y alcance dual sync/async

- **D-14:** `client.py` y `aio.py` requieren **cero cambios de fuente**. Ambas superficies llaman
  al mismo objeto función: los parsers `parse_instruments_response`, `parse_segments_response`,
  `parse_symbols_response`, `parse_health_response` y `parse_health_feed_response` en `_core.py`
  son genéricos (`Model.from_api(item)`, ninguna referencia a nombre de campo) y las dos
  superficies delegan al mismo `_core.py` bajo la arquitectura REFAC-03 — es estructural, no una
  conveniencia. El único cambio no-código: el docstring de `_core.py:1042-1051` que hoy documenta
  que el fix de `Segment` está deliberadamente diferido pasa a ser falso y debe reescribirse.
- **D-15:** "Los 4 gates de CI de v1.6" = los 4 jobs de `.github/workflows/ci.yml`
  (`lint`, `pre-commit`, `typecheck`, `test`); el de mayor riesgo real para esta fase es `lint`
  (paso `surface-types`, por D-08), no `test`. El allowlist de `verification/` en el job `lint`
  asertan **cotas inferiores** sobre un ledger append-only, así que un fix de forma no puede
  reddenearlas.
- **D-16:** La fase toca **sólo** `models.py` + tests (y el docstring de D-14). Sin bump de
  versión en ningún sitio (`pyproject.toml`, `__init__.py.__version__`, `uv.lock`) — el release es
  la Phase 44. `tests/test_version_metadata.py:39-54` queda verde trivialmente al no tocar ninguno
  de los tres sitios.

### Claude's Discretion

Ninguno — las 4 áreas de assumptions fueron confirmadas sin corrección por el usuario.

### Deferred Ideas (OUT OF SCOPE)

Ninguna — sin scope creep detectado durante la discusión. El release (`market-data-client-v0.7.0`)
permanece en la Phase 44 por diseño del milestone.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **SHAPE-01** | Corregir los campos declarados de `Instrument`/`Segment` en `market-data-client` contra una lectura fresca del wire real (no el baseline congelado de 2026-07-31), con disposición individual por campo (alias aditivo / remover / agregar, siguiendo el precedente D-22 de `Symbol.marketId`) y fixtures de test re-derivadas — no renombradas para que sigan pasando | §"Wire medido — verificación independiente" (los 50 filas del capture re-analizadas), §"Patrón 1: alias aditivo D-22", §"Mapa completo de sitios afectados" (11 sitios, no 9), §"Pitfall 1" (`main_market_data.py`) |
| **HARN-02** | Tipar las 5 claves `extra` restantes de `market-data-client` (`Health`/`HealthFeed`/`Symbol`), en el mismo cambio de `models.py` que SHAPE-01 (mismo archivo, mismo release) | §"Patrón 2: modelo anidado tipado", §"Mecánica del walker: cuándo se emite `missing` vs `extra`" (prueba de por qué `| None` suprime el record), §"Pitfall 2/3" (los dos tests de `test_core.py` no listados en D-12) |
</phase_requirements>

---

## Summary

Esta fase no tiene incertidumbre de dominio: CONTEXT.md fija campo por campo qué se agrega, qué se
remueve y qué se aliasea, y `42-WIRE-READ.md` fija el wire. Lo que sí tenía incertidumbre —y es lo
que esta investigación resolvió— son las **mecánicas**: qué exactamente reddenea el gate
`surface-types`, si el walker de decode reporta o no una anotación `| None`, y **cuántos sitios de
test realmente rompen**. La respuesta a la tercera pregunta es la contribución principal: son
**11 sitios, no los 9 de D-12**, y los dos faltantes están ambos en `tests/test_core.py`, ambos
disparados por el único campo *plano* nuevo (`HealthFeed.symbols_never_delivered`, D-11).

Las cinco premisas mecánicas de CONTEXT.md se verificaron ejecutando el código, y **las cinco son
correctas**: (1) `_FIELD_EXEMPTIONS` tiene exactamente una entrada (`UnknownFrame.raw`) y el
predicado `_field_annotation_is_untyped_mapping` cubre `dict`/`Mapping`/`defaultdict`/… en las tres
envolturas opcionales, así que `dict[str, Any]` en `FeedIngestor` es imposible; (2) `walk_field`
efectivamente no tiene rama `dict` y cae a `return value` (`_decode.py:555`); (3) el capture
`market-data-wire-segments-42.json` **existe** en disco (849 bytes, 4 filas); (4) `surface-types`
es el paso 8 del job `lint`; (5) los parsers de `_core.py` son field-agnostic y ni `client.py` ni
`aio.py` tocan un nombre de campo.

**Hallazgo nuevo con impacto de alcance:** `main_market_data.py:1541-1542` lee
`s.marketSegmentId` sobre las `Segment` de `market-data-client`. D-16 declara que la fase toca
"sólo `models.py` + tests". Ese sitio no es ni `models.py` ni un test, no está cubierto por mypy
(cuyo `files` se limita a `packages/*/src`) ni por el hook de pre-commit (`files: ^packages/.*/src/`),
y está envuelto en un `try/except Exception` que lo convertiría en un FINDING silencioso de handler
en vez de un crash. Es exactamente el modo de falla que el code review de la Phase 37 (CR-01)
documentó. La Phase 44 (release) consume "models.py corregido con los 4 gates verdes" como
precondición y **no** cubre el driver, así que si no se arregla acá no lo arregla nadie.

**Primary recommendation:** Un solo plan de 4 waves — (1) `models.py`; (2) los 11 sitios de test
re-derivados con valores sintéticos sobre key-sets medidos; (3) el docstring de `_core.py` +
`main_market_data.py:1541-1542`; (4) el helper nuevo de D-13 + evidencia offline del criterio 2.
El único gate de riesgo real es `test` (no `lint`, contra D-15): el gate `surface-types` pasa por
construcción con los tipos que D-08/D-09/D-10 ya fijan, mientras que 11 aserciones de conjunto
exacto rompen a la vez.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Declaración de forma (`Instrument`, `Segment`, `Symbol`, `FeedIngestor`, `HealthFeed`, `FeedSubscription`) | Model layer (`models.py`) | — | Es el único sitio de declaración de campos; `dataclasses.fields()` es la fuente de verdad para el walker, `to_dict()` y los gates [VERIFIED: `models.py` leído completo, §Instrument/Segment/Symbol/Health] |
| Pre-procesamiento de payload (alias mirror D-22) | Model layer (`from_api` override) | — | Debe correr **antes** del walker para que `marketId` sea una clave presente de un campo declarado y no dispare `extra`; documentado en `models.py:888-892` [VERIFIED: `models.py:878-901`] |
| Desenvolvimiento de envelope (`items[]` / `segments[]`) | Parser layer (`_core.py`) | — | Ya correcto post-Phase-33 (F-82/F-83/F-102/F-103 = `FIXED`); field-agnostic [VERIFIED: `_core.py:1009-1074` leído] |
| Reporte de divergencia (`extra`/`missing`/`type`/`non_dict`) | Decode walker (`_decode.py`) | Censo (`verification/divergences.py`) | El walker emite el record de 6 claves; el handler del censo lo traduce a finding SHAPE [VERIFIED: `_decode.py:584-613`, `divergences.py:139-187`] |
| Superficie pública sync/async | `client.py` / `aio.py` | — | **Sin cambios** — ambas delegan al mismo objeto función de `_core.py` (REFAC-03) [VERIFIED: D-14 confirmado por lectura de los parsers] |
| Consumo en el driver de verificación en vivo | `main_market_data.py` | — | **Tier olvidado por D-16** — dereferencia `.marketSegmentId` fuera de mypy y de pre-commit [VERIFIED: `main_market_data.py:1541-1542`, `pyproject.toml:97`, `.pre-commit-config.yaml`] |

---

## Wire medido — verificación independiente del capture

D-07 depende de que `.planning/verification/captures/market-data-wire-segments-42.json` exista en
disco. **Existe** — y también el de instruments. Ambos fueron re-analizados en esta sesión, no
sólo listados:

| Archivo | Tamaño | `captured_at` | Filas |
|---------|--------|---------------|-------|
| `market-data-wire-segments-42.json` | 849 B | `2026-08-31T21:27:43.256969+00:00` | 4 |
| `market-data-wire-instruments-42.json` | 16 468 B | `2026-08-31T21:27:42.854194+00:00` | 50 |

[VERIFIED: `ls -la` + `json.load` ejecutados en esta sesión]

### `Instrument` — las 50 filas, no sólo la primera

`42-WIRE-READ.md` §2 advierte que `schema_of` describe **la primera fila**. Esa nota abre la
pregunta que D-03 necesita cerrada: ¿`active: null` es una propiedad de esa fila o de todas? Se
midieron las 50:

```
n items: 50
keysets distintos: 1  →  ('active','currency','days_to_maturity','expired',
                          'market_id','maturity','outright','segment','subscribed','symbol')

active            {'NoneType': 50}     ← null en las 50, sin excepción
currency          {'str': 50}
days_to_maturity  {'int': 50}
market_id         {'str': 50}
maturity          {'str': 50}
outright          {'bool': 50}
subscribed        {'bool': 50}
symbol            {'str': 50}
segment           {'str': 50}
expired           {'bool': 50}
```

[VERIFIED: script `python3 -c` sobre el capture, ejecutado en esta sesión]

**Consecuencia para el planner:** D-03 (`active: bool | None = None`) queda respaldado por 50/50
observaciones, no por 1. Y el key-set es **homogéneo** — no hay fila con claves distintas, así que
un test de "key-set de fixture ⊆ key-set medido" tiene una única forma objetivo. Nótese que
`bool | None` es una declaración de nulabilidad **sin evidencia del miembro `bool`**: el wire nunca
mandó un booleano ahí. Es el mismo tipo de asunción semi-observada que `FeedIngestor.last_error`
(`models.py:1271-1275`) y debe documentarse igual.

### `Segment` — las 4 filas

```json
[{"segment": "DDA",  "live_instruments": 407},
 {"segment": "DDF",  "live_instruments": 70},
 {"segment": "DUAL", "live_instruments": 47},
 {"segment": "MERV", "live_instruments": 9151}]
```

[VERIFIED: payload del capture, leído en esta sesión]

**Restricción de uso, crítica:** `.gitignore:53` excluye `.planning/verification/captures/` con el
comentario *"staging de capturas crudas (PII) — nunca committeable (D-11)"*, y `42-WIRE-READ.md`
§5 (T-42-05) prohíbe transcribir la clave `payload` a git. **Un test no puede leer este archivo**:
en CI no existe. El precedente ya establecido en este paquete es el correcto —
`test_reference_envelope_unwrap.py:37-68` y `test_core.py:939-944` declaran *"Values are synthetic;
only the KEY SET and the value TYPES come from the live baseline"*. El capture sirve como
verificación **manual, de una sola vez, en tiempo de ejecución del plan**; la evidencia
reproducible va a un fixture sintético con el key-set real.

---

## Standard Stack

Esta fase **no instala ni actualiza ninguna dependencia externa**. El stack es el ya congelado en
`uv.lock` y en `CLAUDE.md`.

### Core (ya presente — sin cambio)

| Librería | Versión | Propósito en esta fase | Por qué es la estándar |
|----------|---------|------------------------|------------------------|
| `dataclasses` (stdlib) | py3.12 | `@dataclass(frozen=True, slots=True)` para los modelos | Patrón único del monorepo; `SafeModel` lo asume [VERIFIED: `models.py:786`, `:802`, `:1195`…] |
| `typing.get_type_hints` (stdlib, vía `_decode.hints_for`) | py3.12 | Resolución de anotaciones bajo `from __future__ import annotations` | Es lo que el walker usa; `lru_cache`-wrapped [VERIFIED: `_decode.py`, `test_core.py:1187`] |
| `pytest` + `pytest-httpx` | >=8.3 / >=0.34 | Re-derivación de las fixtures | Runner del monorepo [CITED: root `pyproject.toml`] |
| `ruff` | >=0.7 (pre-commit pin v0.15.12) | `ruff check` + `ruff format --check` | Paso 4-5 del job `lint` [VERIFIED: `.github/workflows/ci.yml:36-39`] |
| `mypy` strict | >=1.13 (pre-commit pin v1.13.0) | `typecheck` job | `files = ["packages/*/src"]` + tests por paquete [VERIFIED: `pyproject.toml:97`, `ci.yml:123-132`] |

### Alternatives Considered

| En vez de | Se podría usar | Tradeoff |
|-----------|----------------|----------|
| `FeedSubscription(SafeModel)` (D-08) | `dict[str, Any]` | **No disponible** — reddenea `surface-types`; ver §"El gate `surface-types`, exactamente" |
| `FeedSubscription(SafeModel)` (D-08) | `TypedDict` | El walker sólo tiene rama `_is_model` para dataclasses (`_decode.py:459`); un `TypedDict` cae al `return value` final igual que un `dict` y nunca se camina [VERIFIED: `_decode.py:459-506`, `:555`] |
| Fixture nueva `_MEASURED_HEALTH_FEED_43` (D-13) | Extender `_CAPTURED_HEALTH_FEED` | Rompería `test_captured_payloads_match_the_committed_live_schemas` (igualdad exacta contra el baseline write-once del 2026-07-31) [VERIFIED: `test_core.py:1055-1062`] |

**Installation:** ninguna. Esta fase no agrega paquetes.

---

## Package Legitimacy Audit

**N/A — cero paquetes externos instalados en esta fase.**

El cambio es enteramente interno (`models.py` + tests + un docstring + un dereference de driver).
No hay `uv add`, no hay edición de `[project.dependencies]` en ningún `pyproject.toml`, y D-16
prohíbe explícitamente tocar `uv.lock`. El paso `uv lock --check` del job `lint`
(`ci.yml:32-33`) queda verde por no-op. [VERIFIED: alcance derivado de CONTEXT.md D-14/D-16 +
lectura de `ci.yml`]

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### Diagrama del flujo que esta fase modifica

```
                      ┌──────────────────────────────────────────┐
   HTTP response ───► │  _core.py :: parse_<x>_response          │  FIELD-AGNOSTIC
   (envelope dict)    │  raw.get("items"|"segments") → rows      │  sin cambios (D-14)
                      └────────────────┬─────────────────────────┘
                                       │ por cada row
                                       ▼
                      ┌──────────────────────────────────────────┐
                      │  Model.from_api(payload)                 │
                      │  ┌────────────────────────────────────┐  │
                      │  │ ¿override en la clase?             │  │
                      │  │  Symbol            → mirror        │  │
                      │  │  MarketDataSnapshot → received_at  │  │
                      │  │  Instrument (NUEVO, D-04) → mirror │  │◄─ rompe el set exacto
                      │  └───────────────┬────────────────────┘  │   de test_decode.py:1360
                      └──────────────────┼───────────────────────┘
                                         ▼
                      ┌──────────────────────────────────────────┐
                      │  _decode.walk_model(cls, payload)        │
                      │                                          │
                      │  set(payload) - fields  → "extra"  ─────┐│
                      │  por cada field declarado:              ││
                      │     walk_field(payload.get(name), hint) ││
                      └──────────────────┬──────────────────────┼┘
                                         ▼                      │
                      ┌──────────────────────────────────────┐  │
                      │  walk_field — orden de ramas:        │  │
                      │  1. Union/|None  → value is None ────┼──┼──► RETORNA None
                      │  2. list         → recursión         │  │    SIN EMITIR NADA
                      │  3. _is_model    → None ⇒ Null Object│  │    (la clave de D-03/D-09/D-10)
                      │                     SILENT_SINK      │  │
                      │  4. str/bool/int/float → sink(...)  ─┼──┤
                      │  5. Literal      → sink(...)         │  │
                      │  6. (SIN rama dict) → return value  ─┼──┼──► NO CAMINA, NO REPORTA
                      └──────────────────────────────────────┘  │    (la clave de D-08)
                                                                ▼
                      ┌──────────────────────────────────────────┐
                      │  logger "market_data_client" (6 claves)  │
                      │  → verification/divergences.py           │
                      │    DivergenceHandler.emit                │
                      │    seen.add((slug, model, path, kind))   │
                      │    append_finding(class_="SHAPE")        │
                      └──────────────────────────────────────────┘
```

### Mecánica del walker: cuándo se emite `missing`, cuándo `extra`, cuándo nada

Esta es la mecánica sobre la que descansan D-03, D-08, D-09, D-10 y D-11. Se leyó el código, no se
asumió.

**`extra`** — `walk_model` calcula `sorted(set(payload) - {f.name for f in fields})` y emite un
record por clave sobrante, con `declared="-"` y `observed=type(valor).__name__`
[VERIFIED: `_decode.py:587-593`].

**`missing`** — sólo puede salir de una rama escalar. `_kind_of(value)` devuelve `"missing"` sii
`value is None`; toda rama escalar (`str`/`bool`/`int`/`float`/`Literal`) llama al sink con ese
kind cuando el valor no es del tipo esperado [VERIFIED: `_decode.py:367-371`, `:508-553`].
Una clave **ausente** llega como `data.get(name) → None`, indistinguible de un `null` explícito.

**Nada** — tres caminos silencian el record por completo:

| Anotación | Payload | Qué emite | Fuente |
|-----------|---------|-----------|--------|
| `T \| None` | `None` o clave ausente | **nada** — la rama `Union` retorna `None` antes de cualquier sink | `_decode.py:438-444` |
| `NestedModel` (no-opcional) | `None` o clave ausente | **nada** — NOBJ-02: colapsa al Null Object con `SILENT_SINK` | `_decode.py:502-503` |
| cualquiera | payload no-dict a nivel raíz | **un solo** `non_dict`; los campos se silencian (lock 8) | `_decode.py:594-601` |

**Aplicación campo por campo de las decisiones locked:**

| Campo nuevo | Tipo | Contra `_CAPTURED_HEALTH_FEED` (2026-07-31, sin la clave) | Contra el wire de hoy (con la clave) |
|-------------|------|-----------------------------------------------------------|--------------------------------------|
| `Instrument.active` | `bool \| None` | — | nada (rama Union) ✔ |
| `FeedIngestor.last_error_age_seconds` | `int \| None` | **nada** ✔ | nada ✔ |
| `FeedIngestor.last_error_at` | `str \| None` | **nada** ✔ | nada ✔ |
| `FeedIngestor.subscription` | `FeedSubscription` | **nada** (NOBJ-02) ✔ | camina los 15 campos ✔ |
| `Symbol.note` | `str \| None` | nada ✔ | nada ✔ |
| `HealthFeed.symbols_never_delivered` | `int` (plano, D-11) | **UN record `missing`** ⚠ | nada ✔ |

**La última fila es la que rompe dos tests que D-12 no lista.** Ver §"Common Pitfalls" 2 y 3.

### Patrón 1 — Alias aditivo D-22 (para `Instrument.marketId`, D-04)

Copiar verbatim de `Symbol` (`models.py:878-901`). Los cuatro elementos son load-bearing:

```python
@dataclass(frozen=True, slots=True)
class Instrument(SafeModel):
    # ... campos sin default primero ...
    symbol: str
    marketId: str           # DEPRECATED alias, D-22 — no se renombra jamás
    segment: str
    expired: bool
    market_id: str
    currency: str
    days_to_maturity: int
    maturity: str
    outright: bool
    subscribed: bool
    active: bool | None = None      # ← ÚNICO con default ⇒ debe ir último

    @classmethod
    def from_api(cls, payload: Any) -> Self:
        # (1) el mirror corre ANTES del walker: después de él `marketId` es un campo
        #     declarado con clave presente, así que NO dispara `extra` — el cliente
        #     sintetizó esa clave, el vendor no la mandó (models.py:888-892)
        if isinstance(payload, dict) and "marketId" not in payload and "market_id" in payload:
            # (2) copia, nunca mutación in-place del payload del caller
            payload = {**payload, "marketId": payload["market_id"]}
        # (3) super() de DOS argumentos explícitos: @dataclass(slots=True) RECONSTRUYE
        #     la clase, así que la celda __class__ del super() de cero argumentos apunta
        #     a la clase pre-slots y levanta TypeError (models.py:896-900)
        return super(Instrument, cls).from_api(payload)
```

[VERIFIED: patrón copiado de `models.py:869-901`, con sus tres comentarios justificativos]

**(4) Orden de campos con default.** `@dataclass` exige que todo campo sin default preceda a los
que tienen default. `active: bool | None = None` es el único con default en `Instrument`, así que
va último. En `FeedIngestor` ya existe `last_error: str | None = None` al final; los tres campos
nuevos se insertan así:

```python
    market: FeedMarket
    pipeline: FeedPipeline
    subscription: FeedSubscription          # ← sin default: ANTES de last_error
    last_error: str | None = None
    last_error_age_seconds: int | None = None
    last_error_at: str | None = None
```

[VERIFIED: `models.py:1288-1303` — orden actual leído]

En `Symbol`, `note: str | None = None` va al final (después de `received_at`), respetando el bloque
con default que ya arranca en `id: int = 0` [VERIFIED: `models.py:869-876`].

### Patrón 2 — Modelo anidado tipado (para `FeedSubscription`, D-08)

Copiar de `FeedMarket`/`FeedPipeline` (`models.py:1195-1261`). Cuatro invariantes que los tests
del paquete ya pinnean y que `FeedSubscription` debe respetar:

1. **Declararse ANTES de `FeedIngestor`** en el archivo. El comentario de bloque
   `models.py:1137` dice *"Declared in DEPENDENCY ORDER so every nested type exists before its
   parent"*. Técnicamente `from __future__ import annotations` haría funcionar la forward-ref, pero
   la convención del archivo es explícita [VERIFIED: `models.py:1133-1144`].
2. **Sin override de `from_api`**. `test_health_models_declare_no_from_api_override`
   (`test_core.py:1163-1170`) lo pinnea; y el walker construye modelos anidados con
   `hint(**walk_model(...))`, nunca con `hint.from_api(value)`, así que un override anidado sería
   silenciosamente saltado [VERIFIED: `_decode.py:459-506`, `test_core.py:1163-1170`].
3. **Ningún campo `dict[...]`**. Los 15 campos de F-71 son escalares y `list[str]`, así que se
   cumple naturalmente [VERIFIED: F-71, `market-data-client-findings.md:950`].
4. **Ningún campo `received_at`**. `test_health_models_declare_no_received_at`
   (`test_core.py:1172-1181`) [VERIFIED].

**Además — restricción del gate `surface-types` que CONTEXT.md no menciona:**
`FeedIngestor.subscription` **no puede** declararse `FeedSubscription | None`. El predicado
`_field_annotation_is_optional_model` (`tools/check_surface_types.py:799-881`, regla D-NO-01)
reddenea todo campo de clase exportada anotado `Model | None` o `list[Model] | None`, donde "Model"
= cualquier nombre ligado por un `class` en el import-root del paquete. D-08 ya dice "no-opcional";
esta es la razón mecánica, y es un segundo gate independiente del de mapping [VERIFIED: código leído
+ `_adjudicate_field` en `:1074-1084`].

### Anti-Patterns to Avoid

- **Refrescar `.planning/verification/schemas/market-data-client/*.json`.** Son write-once (D-25).
  `42-WIRE-READ.md` §3 los declara NO-AUTORITATIVOS para esta fase y confirma que la corrida del
  42 los dejó intactos (`git status --porcelain` limpio, T-42-15). El baseline registra el **wire**,
  no el modelo — corregir el modelo no lo invalida.
- **Agregar las 5 claves a `_CAPTURED_HEALTH_FEED`** (`test_core.py:962-1004`) para "arreglar" el
  round-trip. Rompe `test_captured_payloads_match_the_committed_live_schemas` (`:1055-1062`), que
  compara `_schema_of(payload)` contra el baseline committeado por **igualdad**. D-13 lo prohíbe;
  la resolución es una fixture nueva.
- **Renombrar un test para que siga pasando.** Prohibido por el criterio 4 de la fase y por
  SHAPE-01 verbatim (*"fixtures de test re-derivadas — no renombradas para que sigan pasando"*).
- **Alias-mapear `marketSegmentId → segment`.** Rechazado explícitamente en D-06: D-22 aplica a una
  MISMA clave con spelling distinto, no a nombres distintos.
- **Apoyarse en `_emit_shape` para demostrar el antes/después.** Está inerte para
  `Instrument`/`Segment`: el sample se deriva con `raw[0] if isinstance(raw, list) and raw else None`
  y el wire es un envelope `dict`, así que `sample is None` y el SHAPE-diff se saltea en silencio.
  Un "cero findings" post-fix sería un falso verde [CITED: `42-WIRE-READ.md` §4.1; VERIFIED:
  `_emit_shape(sample, Instrument, ...)` en `main_market_data.py:1003` / `:1383`, `Segment` en
  `:1043` / `:1409`].

---

## El gate `surface-types`, exactamente

D-08 apoya su argumento principal en este gate. Se leyó completo (`tools/check_surface_types.py`,
1273 líneas) y se ejecutó.

**Ubicación en CI:** job `lint`, **paso 8 de 9**, línea `ci.yml:61-66`, comando
`uv run python tools/check_surface_types.py` [VERIFIED: `ci.yml` leído].

**Baseline ejecutado en esta sesión:**

```
surface types: 6 packages, 186 `__all__` names, 336 definitions scanned,
442 fields scanned, 13 constant/alias exports,
24 exempted (dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1),
0 violations
```

[VERIFIED: `uv run python tools/check_surface_types.py`, ejecutado 2026-08-31]

**Cómo elige candidatos.** Resuelve desde el `__all__` de cada `__init__.py` hacia afuera
(`scan_surface_types:1144-1158`). Sólo un binding que sea `ast.ClassDef` aporta campos, y sólo
`ast.AnnAssign` con target `ast.Name` a nivel de cuerpo de clase (`_field_candidates_for:1010-1034`).

**Los dos predicados de campo** (OR-eados, mensajes distintos — `_adjudicate_field:1074-1084`):

| Predicado | Qué reddenea | Función |
|-----------|--------------|---------|
| Untyped mapping (D-01b) | base ∈ {`dict`,`Dict`,`Mapping`,`MutableMapping`,`defaultdict`,`DefaultDict`,`OrderedDict`}, con o sin parámetros, tras pelar `X \| None` / `Optional[X]` / `Union[X, None]`; un valor `Any` en cualquier profundidad; una anotación citada que no parsea | `_field_annotation_is_untyped_mapping:677-747` |
| Optional model link (D-NO-01) | `Model \| None` o `list[Model] \| None` donde `Model` es cualquier `ClassDef` del import-root | `_field_annotation_is_optional_model:799-881` |

**La única exención:** `_FIELD_EXEMPTIONS = {"UnknownFrame.raw": "ws-catch-all"}` — una entrada,
keyed por nombre calificado `Clase.campo`, nunca por nombre simple (`:314-316`). El comentario del
bloque advierte explícitamente que la remedia a un rojo es **tipar el campo, nunca ensanchar la
tabla** (`:312-313`) [VERIFIED].

**Veredicto para esta fase:** los tipos que D-01…D-11 fijan son todos escalares, `list[str]`,
`X | None` sobre escalares (`bool`/`int`/`str` no son `ClassDef` del import-root) y un modelo
anidado no-opcional. **Cero violaciones nuevas.** El delta de conteo es informativo, no aserido:

| Clase | Campos ahora | Campos después | Δ |
|-------|--------------|----------------|---|
| `Instrument` | 5 | 11 | +6 |
| `Segment` | 3 | 2 | −1 |
| `Symbol` | 8 | 9 | +1 |
| `FeedIngestor` | 16 | 19 | +3 |
| `HealthFeed` | 7 | 8 | +1 |
| `FeedSubscription` | — | 15 | +15 (sólo si se exporta en el `__all__` del paquete) |
| **Total scanned** | **442** | **452 o 467** | |

El gate **no asserta un piso numérico** en el árbol real: la única anti-vacuidad es
`definitions_total == 0 and fields_total == 0` (`:1201-1218`), un piso de cero. Ningún test del
repo compara el string de salida contra un valor fijo [VERIFIED: `grep -rl "check_surface_types"`
devolvió sólo el propio archivo].

---

## Don't Hand-Roll

| Problema | No construir | Usar en su lugar | Por qué |
|----------|--------------|------------------|---------|
| Tolerancia a payload parcial/nulo en `FeedSubscription` | `__post_init__` con defaults, o un `from_api` propio | Heredar `SafeModel` sin override | `SafeModel.from_api`/`.empty()`/`__bool__` ya dan tolerancia + Null Object; un override anidado se saltea silenciosamente [VERIFIED: `models.py:133-207`, `_decode.py:459-506`] |
| Espejar `market_id → marketId` | Un `field(default_factory=...)` o una property | El override `from_api` de dos argumentos del patrón D-22 | Una property no aparece en `dataclasses.fields()` y por tanto es invisible al walker, a `to_dict()` y a los tests de field-set [VERIFIED: `models.py:878-901`] |
| Detectar campos `| None` en un test | Parsear anotaciones a mano | `_decode.hints_for(cls)` + el helper local `_strip_optional` | Ya existe en `test_core.py:63` y `test_decode.py:49`, y respeta `from __future__ import annotations` |
| Capturar records de divergencia en un test | Un handler de logging propio | El helper local `_from_api(factory, caplog, payload)` | Ya existe en `test_core.py:1043-1051` y en `test_decode.py`; abre un scope fresco, sin el cual el dedupe por triple `(model, path, kind)` de un test previo apaga las aserciones |
| Aislar el estado de decode entre tests | `monkeypatch` sobre `_decode` | La fixture `pristine_decode_context` | `test_core.py:1019-1041`; opt-in, no autouse — documenta exactamente el modo de falla por orden de tests |

**Key insight:** todo lo que esta fase necesita en el lado de tests ya existe como helper local en
`test_core.py` / `test_decode.py`. Lo único genuinamente nuevo es el helper de subconjunto de D-13.

---

## Mapa completo de sitios afectados

D-12 enumera 9 sitios de test. **Se midieron 11.** Los dos adicionales son reales y ambos
disparados por `HealthFeed.symbols_never_delivered: int` (D-11), el único campo nuevo *plano* que
no aparece en la fixture congelada del 2026-07-31.

### Fuente

| # | Archivo · líneas | Cambio | Estado en D-16 |
|---|------------------|--------|----------------|
| S1 | `src/market_data_client/models.py:786-813` | `Instrument` + `Segment` reemplazados; `Instrument.from_api` nuevo | ✅ cubierto |
| S2 | `src/market_data_client/models.py:869-876` | `Symbol.note: str \| None = None` | ✅ cubierto |
| S3 | `src/market_data_client/models.py:1195-1343` | `FeedSubscription` nuevo (antes de `FeedIngestor`); +3 campos en `FeedIngestor`; +1 en `HealthFeed`; actualizar el bloque de comentarios `:1146-1156` (hoy dice "exactamente DOS campos qualify") | ✅ cubierto |
| S4 | `src/market_data_client/models.py:95-123` | `"FeedSubscription"` en `models.__all__` (orden alfabético: entre `FeedPipeline` y `Health`) | ✅ cubierto |
| S5 | `src/market_data_client/__init__.py:80-82`, `:114-119` | `FeedSubscription` en el import y en el `__all__` del paquete — consistencia con `FeedMarket`/`FeedPipeline` | ⚠️ *"sólo models.py"* es impreciso; mismo paquete, cambio trivial |
| S6 | `src/market_data_client/_core.py:1042-1051` | Docstring de `parse_segments_response`: el párrafo "DELIBERATELY not fixed here" pasa a ser falso | ✅ cubierto (D-14) |
| **S7** | **`main_market_data.py:1541-1542`** | **`s.marketSegmentId` → `s.segment`** | ❌ **fuera del alcance declarado por D-16** |

### Tests

| # | Archivo · anclas medidas | Aserción actual | Por qué rompe |
|---|--------------------------|-----------------|---------------|
| T1 | `test_reference_models.py:41-47` | `inst.marketId == ""`, `inst.instrumentType == ""` | `instrumentType` deja de existir → `AttributeError` |
| T2 | `test_reference_models.py:50-54` | `seg.marketSegmentId == ""`, `.marketId`, `.description` | los tres dejan de existir |
| T3 | `test_reference_models.py:219-228` | set exacto de campos de `Symbol` (8 nombres) | debe ganar `"note"` |
| T4 | `test_reference_core.py:167-176` | body `[{"symbol": "GGAL", "marketId": "M"}, …]` | `marketId` explícito gana sobre el mirror; sobrevive pero es fixture stale → re-derivar |
| T5 | `test_reference_core.py:185-190` | `body = [{"marketSegmentId": "S1", "marketId": "M"}]`; `isinstance(result[0], Segment)` | pasa vacuamente con dos filas vacías; hay que re-derivar al key-set real |
| T6 | `test_reference_client.py:44-52`, `:78-87` | `"instrumentType": "E"`; `result[0].marketSegmentId == "DDF"` | `AttributeError` en `:87` |
| T7 | `test_reference_async_client.py:40-48`, `:74-83` | gemelo async idéntico | ídem |
| T8 | `test_decode.py:664-673` | `(".marketId", "missing") in _tuples(records)` sobre `Instrument.from_api({"symbol": ...})` | con el override D-04 y sin `market_id` en el payload el mirror no dispara, así que `marketId` sigue emitiendo `missing`… **pero** el test ahora también verá `missing` de 5 escalares nuevos. La aserción es `in`, no igualdad, así que **sobrevive** — re-derivar igual para que documente la forma nueva |
| T9 | `test_decode.py:676-689` | payload con las 3 claves viejas de `Segment` + `vendorNuevo`; `obj.marketSegmentId == "DDF"` | `AttributeError`; además las 3 claves viejas pasan a ser `extra` |
| T10 | `test_decode.py:1339-1360` | `overriding == {"MarketDataSnapshot", "Symbol"}` **exacto** | `Instrument` gana un override → set de 3 |
| T11 | `test_core.py:1183-1199` | `optionals == {"FeedIngestor.last_error", "FeedPipeline.last_write_error"}` **exacto**, sobre la tupla `(Health, HealthAuth, HealthFeed, FeedIngestor, FeedMarket, FeedPipeline)` | +`FeedIngestor.last_error_age_seconds`, +`FeedIngestor.last_error_at` |
| T12 | `test_public_surface_market_data.py:102-121` | `subclasses <= set(models.__all__)` | `FeedSubscription` debe estar en `models.__all__` |
| **T13** | **`test_core.py:1145-1150`** | **`HealthFeed.from_api(_CAPTURED_HEALTH_FEED).to_dict() == _CAPTURED_HEALTH_FEED`** | **NO EN D-12** — ver Pitfall 2 |
| **T14** | **`test_core.py:1125-1137`** | **`records == [(".brand_new_wire_key", "extra")]` exacto** | **NO EN D-12** — ver Pitfall 3 |

### Tests que NO rompen (verificados, para que el planner no los toque de más)

| Archivo | Por qué sobrevive |
|---------|-------------------|
| `test_reference_envelope_unwrap.py:37-68` | `_INSTRUMENTS_ENVELOPE` / `_SEGMENTS_ENVELOPE` ya usan el key-set real del wire (`market_id`, `currency`, …, `active: None`; `segment`, `live_instruments`). Agregado en Phase 33. Confirma D-12 |
| `test_reference_envelope_unwrap.py:120-139` | `test_bare_list_bodies_still_parse` manda `marketId` **explícito** → el mirror no lo pisa, la aserción `result[0].marketId == "ZZZ"` sigue verde. `"instrumentType": "E"` pasa a ser `extra` inerte |
| `test_decode.py:690-745` | `test_no_call_site_exempt_safemodel_appears_as_a_nested_field_type` deriva `exempt` dinámicamente y hace `assert "Instrument" not in rendered` por substring sobre cada hint. Ningún campo tiene un hint que contenga la subcadena "Instrument" → verde sin edición |
| `test_core.py:1055-1062` | `test_captured_payloads_match_the_committed_live_schemas` compara `_schema_of(_CAPTURED_HEALTH_FEED)` contra `get-health-feed.json`; si la fixture no se toca, sigue verde. **Confirma D-13** |
| `test_core.py:1152-1181` | Los tres tests parametrizados sobre las 6 clases de health (frozen / no-override / no-received_at) pasan con `FeedSubscription` agregado o no a la lista; agregarlo es lo consistente |
| `test_version_metadata.py` | D-16 no toca ninguno de los 3 sitios de versión |
| `test_surface_parity.py` | `assert_module_lower_bound` — cotas inferiores, no se rompen agregando |
| `verification/test_cycle_closure_phase33.py:57-83` | Pisos medidos sobre el ledger append-only: `_PRE_PHASE_BASELINE["market-data-client"] = 50`, `_PHASE_33_PROMOTIONS = 38`. Un fix de forma no borra findings pasados. **Confirma D-15** |
| `packages/matriz-client/**`, `verification/test_matriz_sweep_snapshot.py:90`, `scripts/literal_census_33.py:345`, `verification/snapshots/matriz-client-surface.txt` | Contienen `marketSegmentId` pero son el `Segment` de **matriz**, un modelo distinto en otro paquete. **No tocar** |

---

## Common Pitfalls

### Pitfall 1: `main_market_data.py:1541-1542` — el consumidor fuera de todo gate estático

**Qué sale mal:** `probe_parity` hace `sorted(s.marketSegmentId for s in seg_sync)` sobre las
`Segment` de este paquete. Al removerse el campo, el generador levanta `AttributeError`.

**Por qué pasa:** ningún gate lo detecta.
- `mypy` global: `files = ["packages/*/src", …]` — el driver de raíz no está incluido
  [VERIFIED: `pyproject.toml:97`].
- `pre-commit` mypy: `files: ^packages/.*/src/` — tampoco [VERIFIED: `.pre-commit-config.yaml`].
- `ruff check .` sí lo lee, pero ruff no hace inferencia de tipos.
- `verification/test_main_market_data_deep_chain.py` (que sí corre en el job `lint`) **parsea** el
  driver con `ast`, nunca lo importa, y sólo audita cadenas `….market_data.<alias>` — no toca
  `probe_parity` [VERIFIED: docstring `:26`, `_DRIVER = "main_market_data.py"`].

**Y peor:** el sitio está dentro de un `try/except Exception` que devuelve
`_finding_for_exc(exc, name="parity_sync_async", …)` (`main_market_data.py:1543-1544`). No hay
crash: la próxima corrida en vivo emite un FINDING de handler y el probe de paridad queda
degradado sin que nadie lo note.

**Cómo evitarlo:** cambiar a `s.segment` en las dos líneas. Es un dereference, no lógica, así que
no dispara la regla dual sync/async de CLAUDE.md.

**Precedente:** es literalmente el CR-01 de la Phase 37 — *"un driver no actualizado después de un
cambio de forma fabrica falsos positivos SHAPE en la próxima corrida en vivo"*
[CITED: `.planning/research/ARCHITECTURE.md` §Group 3, que ya lo había marcado como
*"Modified — load-bearing"*].

**Conflicto con D-16 que el planner debe resolver:** D-16 dice *"la fase toca sólo `models.py` +
tests (y el docstring de D-14)"*. Este sitio no es ninguno de los tres. La Phase 44 (release)
consume "models.py corregido con los 4 gates verdes" y no cubre el driver. Recomendación: incluirlo,
señalándolo como corrección de precisión de D-16, no como scope creep — el trabajo es de 2 líneas y
dejarlo fuera deja un defecto sin dueño.

---

### Pitfall 2: `test_health_feed_to_dict_round_trips_all_three_levels` (T13) — no está en D-12

**Qué sale mal:**

```python
# packages/market-data-client/tests/test_core.py:1145-1150
def test_health_feed_to_dict_round_trips_all_three_levels() -> None:
    wire = HealthFeed.from_api(_CAPTURED_HEALTH_FEED).to_dict()
    assert wire == _CAPTURED_HEALTH_FEED          # ← IGUALDAD EXACTA
```

`SafeModel.to_dict()` es `dataclasses.asdict(self)` puro (`models.py:228`): proyecta **todos** los
campos declarados, poblados o no. Con los 4 campos nuevos, `wire` gana
`symbols_never_delivered: 0`, `ingestor.subscription: {…15 ceros…}`,
`ingestor.last_error_age_seconds: None`, `ingestor.last_error_at: None` — cuatro claves que
`_CAPTURED_HEALTH_FEED` no tiene. La igualdad falla.

**Por qué es la trampa:** el arreglo "obvio" es agregar las claves a `_CAPTURED_HEALTH_FEED`. Eso
rompe `test_captured_payloads_match_the_committed_live_schemas` (`:1055-1062`), que compara la
misma fixture contra el baseline write-once del 2026-07-31 por igualdad. Es el conflicto que D-13
anticipa: la fixture congelada tiene que **quedar congelada**.

**Cómo evitarlo:** re-derivar el test contra la fixture nueva de D-13
(`_MEASURED_HEALTH_FEED_43`, con el key-set de F-202/F-71), o —si se quiere conservar la prueba de
round-trip sobre la fixture vieja— aseverar explícitamente el delta declarado:

```python
assert wire == {
    **_CAPTURED_HEALTH_FEED,
    "symbols_never_delivered": 0,
    "ingestor": {
        **_CAPTURED_HEALTH_FEED["ingestor"],
        "subscription": FeedSubscription.empty().to_dict(),
        "last_error_age_seconds": None,
        "last_error_at": None,
    },
}
```

Ambas rutas son "re-derivar", no "renombrar" — cumplen el criterio 4.

**Señal de alerta temprana:** el fallo se ve como un diff gigante de dict en pytest, no como un
`AttributeError`. Fácil de leer mal como "el walker se rompió".

---

### Pitfall 3: `test_health_feed_from_api_drops_an_undeclared_key_and_reports_it_once` (T14) — tampoco está en D-12

**Qué sale mal:**

```python
# packages/market-data-client/tests/test_core.py:1125-1137
payload = {**_CAPTURED_HEALTH_FEED, "brand_new_wire_key": "surprise"}
feed, records = _from_api(HealthFeed.from_api, caplog, payload)
assert [(r.field_path, r.divergence) for r in records] == [
    (".brand_new_wire_key", "extra")
]                                          # ← LISTA EXACTA, un solo elemento
```

`_CAPTURED_HEALTH_FEED` no tiene `symbols_never_delivered`. Declarado `int` **plano** (D-11), la
rama escalar de `walk_field` llama al sink con `_kind_of(None) == "missing"`. El resultado pasa a
tener **dos** records y la igualdad exacta falla.

**Los otros tres campos nuevos NO contribuyen** — y ésa es justamente la evidencia mecánica que
respalda D-09 y D-08:
- `last_error_age_seconds: int | None` y `last_error_at: str | None` → rama `Union`, retorno
  temprano, cero records (`_decode.py:438-444`).
- `subscription: FeedSubscription` no-opcional → NOBJ-02, colapsa al Null Object con `SILENT_SINK`,
  cero records (`_decode.py:502-503`).

**Cómo evitarlo:** re-derivar sobre la fixture nueva de D-13 (que sí trae la clave), o —si se
conserva la fixture vieja— aserir la lista de dos elementos con un comentario que explique por qué
el `missing` de `symbols_never_delivered` es correcto y esperado bajo la doctrina option-b.

**Señal de alerta temprana:** este test es la prueba viva de que el criterio 3 ("una `extra` medida
no debe convertirse en una `missing` permanente") **se está evaluando bien**. Si al re-derivarlo
aparecen `missing` de `last_error_age_seconds` o `last_error_at`, es que alguien los declaró planos
contra D-09.

---

### Pitfall 4: `super()` de cero argumentos en `Instrument.from_api`

**Qué sale mal:** `TypeError: obj must be an instance or subtype of type` en runtime.

**Por qué pasa:** `@dataclass(slots=True)` **reconstruye** la clase; la celda implícita `__class__`
que captura un `super()` sin argumentos sigue apuntando a la clase pre-slots, que ya no es la que
está ligada al nombre global.

**Cómo evitarlo:** `super(Instrument, cls).from_api(payload)`, dos argumentos explícitos.

**Señal de alerta temprana:** falla en el primer `Instrument.from_api(...)` de cualquier test — es
ruidoso, no silencioso. [VERIFIED: comentario justificativo en `models.py:896-900`]

---

### Pitfall 5: el orden de campos de dataclass

**Qué sale mal:** `TypeError: non-default argument 'X' follows default argument` en **tiempo de
import**, así que revienta la colección entera de pytest, no un test.

**Por qué pasa:** `Instrument` hoy no tiene ningún campo con default; `active: bool | None = None`
introduce el primero. `FeedIngestor` ya tiene `last_error: str | None = None` al final, y
`subscription: FeedSubscription` (sin default) debe ir **antes**.

**Cómo evitarlo:** ver el bloque de código en §"Patrón 1".

---

### Pitfall 6: el capture gitignored no puede ser una dependencia de test

**Qué sale mal:** un test que hace `json.load(open(".planning/verification/captures/market-data-wire-segments-42.json"))`
pasa en la máquina del ejecutor y falla en CI con `FileNotFoundError`.

**Por qué pasa:** `.gitignore:53` excluye el directorio entero
(*"staging de capturas crudas (PII) — nunca committeable (D-11)"*), y `42-WIRE-READ.md` §5 (T-42-05)
prohíbe transcribir la clave `payload` a git.

**Cómo evitarlo:** el precedente ya establecido — fixtures con **valores sintéticos y key-set real**
(`test_core.py:939-944`: *"payloads whose per-leaf TYPES reproduce those captures exactly"*;
`test_reference_core.py:211-213`: *"Values are synthetic; the KEY SETS are real"*). El capture se
usa como verificación manual en tiempo de ejecución del plan y se cita en el SUMMARY, nunca se
importa desde un test.

---

## Code Examples

### `Segment` reemplazado (D-06)

```python
# packages/market-data-client/src/market_data_client/models.py — reemplaza :802-813
@dataclass(frozen=True, slots=True)
class Segment(SafeModel):
    """A market segment row from ``GET /instruments/segments``.

    Reconciled against the FRESH live wire read of 2026-08-31
    (``42-WIRE-READ.md`` §2, 4 rows measured). The three previously declared
    fields — ``marketSegmentId`` / ``marketId`` / ``description`` — exist NOWHERE
    on the wire; they were the PROVISIONAL A1/A2 guess. Their removal is
    NON-breaking by the D-13 argument: the wire key set and the old declared set
    were DISJOINT, so every row a released consumer ever read decoded to three
    empty strings and no populated value could have been observed.

    Not alias-mapped under D-22: that precedent covers ONE key with a
    camelCase/snake_case spelling variant (``marketId``/``market_id``);
    ``marketSegmentId`` vs ``segment`` are different names.
    """

    segment: str
    live_instruments: int
```

*(Fuente del key-set: `42-WIRE-READ.md` §2 + `market-data-wire-segments-42.json`, re-verificado en esta sesión.)*

### `FeedSubscription` (D-08) — declarar antes de `FeedIngestor`

```python
# packages/market-data-client/src/market_data_client/models.py — insertar entre :1261 y :1263
@dataclass(frozen=True, slots=True)
class FeedSubscription(SafeModel):
    """``ingestor.subscription`` inside ``GET /health/feed`` (Phase 43, HARN-02).

    Field set taken verbatim from the measured blob of F-71 / F-202
    (``market-data-client-findings.md``). ``dict[str, Any]`` is NOT an available
    alternative: ``tools/check_surface_types.py`` reddens any untyped mapping on
    an exported class (``_FIELD_EXEMPTIONS`` holds one entry, ``UnknownFrame.raw``),
    and ``_decode.walk_field`` has no ``dict`` branch — it falls through to
    ``return value`` without walking or reporting, so a mapping would be a
    permanent blind spot in the divergence census.

    No ``| None`` field: every one of the fifteen came back populated in the
    measured capture (option-b restraint, ``models.py:1146-1156``).

    ``unconfirmed_symbols`` is a DECLARED ASSUMPTION: the wire sent ``[]`` and the
    element type was never observed populated. ``list[str]`` mirrors its populated
    sibling ``quarantined_symbols``; a wrong guess surfaces LOUDLY in the next
    divergence census rather than silently.
    """

    chunk_size: int
    chunks: int
    confirm_seconds: int
    delivered_count: int
    forced_reconnects: int
    last_reconnect_reason: str
    quarantined_count: int
    quarantined_symbols: list[str]
    requested: int
    sent: int
    smd_rejections: int
    smd_resends: int
    smd_unattributed: int
    unconfirmed_count: int
    unconfirmed_symbols: list[str]
```

*(Fuente: F-71 blob "Actual", `market-data-client-findings.md:950` — 15 claves, leídas verbatim en esta sesión.)*

### El helper de subconjunto de D-13

```python
# packages/market-data-client/tests/test_core.py — nuevo
# El key-set MEDIDO en la corrida del 2026-08-31, tomado del blob "Actual" de
# F-202 (market-data-client-findings.md). Valores sintéticos, tipos y claves
# reales — el mismo contrato que _CAPTURED_HEALTH_FEED, contra una medición
# posterior. NO reemplaza ni refresca ningún baseline write-once (D-25).
_MEASURED_HEALTH_FEED_43: dict[str, Any] = { ... }


def _keys_recursive(payload: Any, prefix: str = "") -> set[str]:
    """Every dotted key path in a nested payload."""
    if not isinstance(payload, dict):
        return set()
    out: set[str] = set()
    for key, value in payload.items():
        path = f"{prefix}.{key}"
        out.add(path)
        out |= _keys_recursive(value, path)
    return out


def test_every_fixture_key_is_a_measured_wire_key() -> None:
    """Criterio 4: ninguna fixture inventa una clave que el wire nunca mandó."""
    measured = _keys_recursive(_MEASURED_HEALTH_FEED_43)
    assert _keys_recursive(_CAPTURED_HEALTH_FEED) <= measured
```

*(La igualdad `_CAPTURED_HEALTH_FEED ⊆ _MEASURED_HEALTH_FEED_43` es la afirmación de D-13
"la fixture del 2026-07-31 es un subconjunto estricto de la forma medida en 2026-08-31" —
verificable, y verde por construcción según el diff de F-71.)*

---

## Runtime State Inventory

Fase de refactor de forma sobre un paquete publicado. Categorías evaluadas explícitamente:

| Categoría | Encontrado | Acción requerida |
|-----------|------------|------------------|
| Stored data | **Ninguno** — el paquete no persiste nada; los modelos son proyecciones en memoria de respuestas HTTP. Los `.json` de `.planning/verification/schemas/` registran el **wire**, no el modelo, y son write-once (D-25) | ninguna |
| Live service config | **Ninguno** — no hay configuración externa que nombre un campo del modelo. `market-data-develop.bbsa.com.ar` es el servidor: su forma es la entrada, no la salida | ninguna |
| OS-registered state | **Ninguno** — verificado: no hay procesos registrados, cron, ni servicios que consuman este paquete en este repo | ninguna |
| Secrets / env vars | **Ninguno** — `MARKET_DATA_*` nombran credenciales y URLs, ningún campo de modelo. `MARKET_DATA_VERIFY_MUTATING` es un guard de mutación, no tocado | ninguna |
| Build artifacts / installed | **Presente pero auto-resuelto** — `packages/market-data-client/src/*.egg-info` y `.venv` sirven el paquete en modo editable vía `uv sync --frozen`; un cambio de `models.py` se recoge sin reinstalar (no hay compilación) | ninguna |
| **Consumidores in-repo del campo removido** | **`main_market_data.py:1541-1542`** (`.marketSegmentId`). Único hit fuera de `models.py` y de los tests, sobre este paquete. Los hits en `matriz-client`, `main_matriz.py:894`, `scripts/literal_census_33.py:345`, `verification/test_matriz_sweep_snapshot.py:90` y `verification/snapshots/matriz-client-surface.txt` son del `Segment` de **matriz** — modelo distinto, otro paquete, **no tocar** | **code edit de 2 líneas** — ver Pitfall 1 |

**Método:** `grep -rn "marketSegmentId\|instrumentType" --include="*.py" --include="*.json"` sobre el
árbol completo, con desambiguación manual por paquete. [VERIFIED: ejecutado en esta sesión]

---

## Environment Availability

| Dependencia | Requerida por | Disponible | Versión | Fallback |
|-------------|---------------|------------|---------|----------|
| `uv` | todo comando | ✓ | workspace sincronizado (`--frozen` OK) | — |
| Python 3.12 | runtime + matriz CI | ✓ | 3.12.11 (`.venv`) | 3.13 también en CI |
| `pytest` + `pytest-httpx` + `pytest-asyncio` | los 711 tests | ✓ | suite verde en 1.05 s | — |
| `ruff`, `mypy` | jobs `lint` / `typecheck` | ✓ | ejecutables vía `uv run` | — |
| `tools/check_surface_types.py` | gate D-08 | ✓ | ejecutado: `0 violations` | — |
| `.planning/verification/captures/market-data-wire-*-42.json` | evidencia offline D-07 | ✓ | segments 849 B / instruments 16 468 B, `captured_at` 2026-08-31 | **sin fallback** si se hace `git clean -xdf` → sólo queda `42-WIRE-READ.md` §2 (schema, sin valores) |
| Acceso en vivo a `market-data-develop.bbsa.com.ar` | **NO requerido** | n/a | — | D-07 lo declara explícitamente innecesario |
| Auth0 client-credentials | **NO requerido** | n/a | — | ídem |

**Missing dependencies with no fallback:** ninguna en el estado actual del working tree.
**Riesgo latente:** los dos captures son la única fuente de **valores** del wire y no están en git.
Si el plan se ejecuta en otro clone o tras un `git clean -xdf`, D-07 pierde su evidencia primaria y
queda sólo el schema de `42-WIRE-READ.md`. **Recomendación al planner:** poner la lectura del
capture en la Wave 1 (temprano) y transcribir el key-set —nunca los valores— al SUMMARY, para que
la evidencia sobreviva al árbol.

---

## Validation Architecture

### Test Framework

| Propiedad | Valor |
|-----------|-------|
| Framework | pytest 8.3+ · pytest-asyncio (`asyncio_mode = "auto"`) · pytest-httpx 0.34+ · pytest-cov |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["packages", "tests", "verification"]`, `--import-mode=importlib`, `--strict-markers`) |
| Quick run command | `uv run pytest packages/market-data-client -q --no-cov` |
| Full suite command | `uv run pytest packages/market-data-client --cov=packages/market-data-client/src --cov-report=term` |
| Baseline medido | **711 passed en 1.05 s** [VERIFIED: ejecutado en esta sesión] |

El quick run tarda ~1 s. **No hace falta un comando "rápido" distinto del completo por paquete** —
correr el suite entero después de cada tarea es viable.

### Phase Requirements → Test Map

| Req | Comportamiento | Tipo | Comando automatizado | ¿Existe? |
|-----|----------------|------|----------------------|----------|
| SHAPE-01 | `Instrument` declara exactamente los 10 campos del wire + el alias `marketId` | unit | `uv run pytest packages/market-data-client/tests/test_reference_models.py -x -q --no-cov` | ❌ Wave 0 — no existe test de field-set exacto para `Instrument` (sí para `Symbol`:219 y `CalendarConfig`:167 — **copiar ese patrón**) |
| SHAPE-01 | `Segment` declara exactamente `{segment, live_instruments}` | unit | ídem | ❌ Wave 0 — mismo patrón |
| SHAPE-01 | `Instrument.marketId` espeja `market_id` y un `marketId` explícito sigue ganando | unit | ídem | ❌ Wave 0 — gemelos de `test_symbol_market_id_alias_mirrors_wire_snake_case`:262 y `..._explicit_camel_case_payload_key_still_wins`:272 |
| SHAPE-01 | `Instrument.instrumentType` ya no existe | unit | ídem | ❌ Wave 0 — patrón de `assert not hasattr(..., "businessDays")` (`test_reference_models.py:180`) |
| SHAPE-01 (crit. 2) | `get_segments()` sobre el envelope real devuelve filas **pobladas**, no vacías | unit | `uv run pytest packages/market-data-client/tests/test_reference_envelope_unwrap.py -x -q --no-cov` | ⚠️ parcial — la fixture ya es correcta (`:65-68`), falta la aserción de valor (`result[0].segment == "SEG1"`, `.live_instruments == 7`) |
| SHAPE-01 (crit. 2) | Antes/después medido contra el capture del 42 | manual (1×) | lectura del capture + censo F-214…F-218 en el SUMMARY | n/a — evidencia documental, no test (Pitfall 6) |
| HARN-02 | Las 5 claves están declaradas y decodifican sin `extra` | unit | `uv run pytest packages/market-data-client/tests/test_core.py -x -q --no-cov` | ❌ Wave 0 — sobre `_MEASURED_HEALTH_FEED_43` |
| HARN-02 (crit. 3) | Ninguna `extra` medida se convierte en `missing` sobre un payload sano | unit | ídem | ⚠️ re-derivar T14 (`test_core.py:1125-1137`) — es exactamente esta prueba |
| HARN-02 (crit. 4) | Toda clave de fixture ⊆ key-set medido | unit | ídem | ❌ Wave 0 — helper de D-13 |
| SHAPE-01+HARN-02 | El set exacto de optionals refleja las decisiones | unit | ídem | ⚠️ re-derivar T11 (`test_core.py:1183-1199`) |
| SHAPE-01 | El set exacto de overrides refleja D-04 | unit | `uv run pytest packages/market-data-client/tests/test_decode.py -x -q --no-cov` | ⚠️ re-derivar T10 (`test_decode.py:1339-1360`) |
| D-14 | Superficie async idéntica a la sync | unit | `uv run pytest packages/market-data-client/tests/test_reference_async_client.py -x -q --no-cov` | ✓ existe; re-derivar fixtures (T7) |
| D-15 | Los 4 gates verdes | integration | `uv run ruff check . && uv run ruff format --check . && uv run python tools/check_surface_types.py && uv run mypy && uv run mypy packages/market-data-client/tests && uv run pytest packages/market-data-client -q` | ✓ todo existente |

### Sampling Rate

- **Por commit de tarea:** `uv run pytest packages/market-data-client -q --no-cov` (~1 s, 711→~730 tests)
- **Por merge de wave:** `+ uv run python tools/check_surface_types.py && uv run mypy && uv run mypy packages/market-data-client/tests`
- **Phase gate:** los 4 jobs de `ci.yml` reproducidos localmente (incluido `uv run pre-commit run --all-files`) antes de `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `test_reference_models.py::test_instrument_field_set_matches_reconciled_wire` — SHAPE-01
- [ ] `test_reference_models.py::test_segment_field_set_matches_reconciled_wire` — SHAPE-01
- [ ] `test_reference_models.py::test_instrument_market_id_alias_mirrors_wire_snake_case` — D-04
- [ ] `test_reference_models.py::test_instrument_explicit_camel_case_payload_key_still_wins` — D-04
- [ ] `test_core.py::_MEASURED_HEALTH_FEED_43` (fixture) + `_keys_recursive` + `test_every_fixture_key_is_a_measured_wire_key` — D-13 / criterio 4
- [ ] `test_core.py::test_feed_subscription_decodes_the_measured_blob` — D-08 (los 15 campos)
- [ ] `test_core.py::test_healthy_feed_payload_emits_no_missing_for_the_conditional_error_fields` — criterio 3 / D-09
- [ ] Instalación de framework: **ninguna** — todo presente

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`. Fase de refactor interno sin superficie de
red nueva, sin auth nueva, sin persistencia nueva.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | **no** | Auth0 client-credentials sin cambio; ningún modelo de esta fase lleva credenciales |
| V3 Session Management | **no** | El token vive en `TokenStore`, fuera de `models.py` |
| V4 Access Control | **no** | Sin cambio de endpoint ni de scope |
| V5 Input Validation | **sí** | `SafeModel.from_api` + `_decode.walk_model` es el control: coerción tolerante por campo, claves no declaradas **descartadas** (nunca `setattr` dinámico), tipos verificados por rama. `FeedSubscription` hereda el control entero sin código nuevo |
| V6 Cryptography | **no** | Ninguna operación cripto en el alcance |
| V7 Error Handling / Logging | **sí** | El sink de divergencias loguea `type(value).__name__`, **nunca el valor** (`_decode.py:449`, `:511`…). `FeedSubscription` no cambia eso. `DivergenceHandler.emit` nunca propaga (P-2, `divergences.py:182-187`) |
| V13 API / Web Service | parcial | El paquete es cliente, no servidor. La forma declarada es defensa en profundidad contra un vendor que cambia el payload |

### Known Threat Patterns for this stack

| Patrón | STRIDE | Mitigación estándar (ya en el árbol) |
|--------|--------|--------------------------------------|
| Clave de payload controlada por el vendor que sobre-escribe un campo del cliente | Tampering | El mirror D-22 corre **antes** del walker y **sólo rellena** una clave ausente — nunca pisa un valor explícito (`models.py:885-895`). El mismo invariante debe replicarse verbatim en `Instrument.from_api` |
| Un valor del wire que gana sobre un timestamp del cliente | Spoofing | `MarketDataSnapshot.received_at` bypassa el walker por diseño (`test_decode.py:764-771`). **No aplica a esta fase** — `Instrument` no lleva stamp de cliente (D-05, reference data unstamped) |
| Fuga de PII del wire a git a través de una fixture de test | Information Disclosure | `.gitignore:53` + T-42-05 + el patrón "valores sintéticos, key-set real". **Vector activo en esta fase** — ver Pitfall 6 |
| Fuga de PII en un log de divergencia | Information Disclosure | El record de 6 claves lleva **nombres de tipo**, nunca valores. Preservado sin cambio |
| Payload malformado que crashea el parseo | DoS | `SafeModel.from_api` es tolerante por contrato; `walk_model` nunca levanta bajo la política por defecto (`literal_enforced=False`, `scalar_passthrough` según policy) |

**Nada de esta fase introduce una superficie de amenaza nueva.** El único control que el planner
debe ejercer activamente es el de Pitfall 6 (no transcribir valores del capture a git).

---

## State of the Art

| Enfoque viejo | Enfoque actual | Cuándo cambió | Impacto en esta fase |
|---------------|----------------|---------------|----------------------|
| `_coerce(value, hint)` de dos argumentos, sin reporte | `_decode.walk_model` / `walk_field` con sink de 6 claves | Phase 29 (DEC-01) | Toda decisión de nulabilidad es ahora observable; `_coerce` sobrevive como shim (`models.py:232-246`) y `test_decode.py:651-662` lo pinnea |
| `dict[str, Any]` en la superficie exportada | Gate `surface-types` (D-01b + D-NO-01) | Phase 32 (GATE-TYP-01), campos en Phase 37, model-links en Phase 38 | Cierra `dict[str, Any]` como opción para D-08 |
| Modelo con mapping (`MarketDataSnapshot.market_data: dict`) + pase post-walk | Modelo anidado tipado (`MarketDataEntries`) — el eje mapping se retiró | Phase 36 (NOBJ-MD-02, D-05) | `SafeModel.from_api` es un walk puro (forma A de D-07); `FeedSubscription` encaja sin machinery extra |
| `X | None` para "quizás null" | Doctrina option-b / restraint: `| None` **sólo** con nulabilidad condicional medida | Phase 31 (checkpoint 31-04 Task 1) | Es la doctrina que D-03/D-09/D-10/D-11 aplican; `test_core.py:1183-1199` la pinnea con un set exacto |
| Parsers iterando las claves del envelope | Unwrap explícito por `items`/`segments` | Phase 33 (S-1, F-82/83/102/103 = `FIXED`) | Deja `_core.py` correcto y hace innecesario D-14 tocar los parsers |
| Baseline de schema sobre-escrito on drift | Write-once, emite finding, nunca pisa (D-25) | Phase 33 | Fundamenta D-13 y la marca NO-AUTORITATIVO de `42-WIRE-READ.md` §3 |

**Deprecado / obsoleto (a no reintroducir):**
- `test_no_mapping_carrying_model_is_ever_a_nested_field_type` — retirado con el eje mapping en
  Phase 36. No recrearlo.
- `verification/test_cycle_closure_market_data.py` — reemplazado por
  `test_cycle_closure_phase33.py`.
- `_apply_mapping_policy` / `_is_mapping` / `_mapping_value` — ausentes de este paquete desde
  Phase 36; `test_models.py:265` pinnea su ausencia.

---

## Assumptions Log

| # | Claim | Sección | Riesgo si es incorrecto |
|---|-------|---------|-------------------------|
| A1 | `FeedSubscription.unconfirmed_symbols: list[str]` — el wire mandó `[]`, el tipo de elemento nunca se observó poblado | Code Examples · Patrón 2 | **Bajo, autocorrectivo.** Un elemento no-`str` produce un record `type` en el próximo censo de divergencias, no un crash — `walk_field` sobre `list` recursa sin levantar (`_decode.py:446-457`). Ya registrado con confianza LOW en `research/SUMMARY.md:141` |
| A2 | `Instrument.active: bool | None` — el miembro `bool` de la unión nunca se observó (50/50 filas `null`) | Wire medido | **Bajo.** Mismo patrón semi-observado que `FeedIngestor.last_error` (`models.py:1271-1275`). Si el wire manda algo que no sea `bool`, sale un record `type` |
| A3 | Los 4 campos nuevos de health son los únicos que alteran el conteo de records de T14; ningún otro test con lista exacta de records toca `HealthFeed` | Pitfall 3 | **Bajo.** Derivado de `grep` sobre `records ==` en `tests/`; el riesgo residual es un test con igualdad de records que el grep no matcheó por formato |
| A4 | El delta de campos escaneados por `surface-types` (442 → 452/467) no está aserido en ningún lado | §El gate `surface-types` | **Muy bajo.** `grep -rl "check_surface_types"` devolvió sólo el propio archivo; la única anti-vacuidad es un piso de cero |
| A5 | Agregar `FeedSubscription` al `__all__` del **paquete** (no sólo al de `models`) es lo consistente | S5 | **Ninguno funcional.** `test_models_dunder_all_covers_every_safemodel_subclass` sólo exige `models.__all__`. Exportarlo también en el paquete es consistencia con `FeedMarket`/`FeedPipeline` y hace que el gate escanee sus 15 campos — deseable |
| A6 | Corregir `main_market_data.py:1541-1542` cabe en esta fase pese a la letra de D-16 | Pitfall 1 | **Medio — decisión de alcance, no técnica.** Si el planner lo excluye, la próxima corrida en vivo del driver degrada `probe_parity` a un FINDING de handler y nadie lo posee (la Phase 44 es release, no fix). **Requiere confirmación del usuario o una nota explícita del planner** |

---

## Open Questions

1. **¿`main_market_data.py:1541-1542` entra en esta fase?**
   - Qué sabemos: el sitio existe, se rompe con D-06, ningún gate estático lo detecta, y el
     `try/except` lo convierte en un FINDING silencioso en vez de un crash. `research/ARCHITECTURE.md`
     §Group 3 ya lo había marcado *"Modified — load-bearing"*.
   - Qué no está claro: D-16 dice "sólo `models.py` + tests", y la discusión de la fase corrió en
     modo assumptions sin que este sitio se planteara.
   - Recomendación: **incluirlo**, como corrección de precisión de D-16 y no como scope creep. Son
     2 líneas, sin lógica, sin obligación de espejo sync/async. La alternativa —diferirlo a la
     Phase 45— deja un defecto conocido sin dueño durante un release.

2. **¿Qué forma toma la evidencia offline del criterio 2 (D-07)?**
   - Qué sabemos: el capture existe hoy; está gitignored; T-42-05 prohíbe transcribir `payload`; el
     precedente del paquete es "valores sintéticos, key-set real".
   - Qué no está claro: si la evidencia va a un test (reproducible pero sintético) o a la prosa del
     SUMMARY (fiel al capture pero no reproducible).
   - Recomendación: **ambas.** Un test con la fixture sintética que ya existe
     (`_SEGMENTS_ENVELOPE`, con aserciones de valor agregadas) para la reproducibilidad, y una
     verificación manual de una sola vez contra el capture, transcrita al SUMMARY como key-set +
     conteos (nunca valores).

3. **¿Se toca `test_decode.py:664-673` (T8)?**
   - Qué sabemos: la aserción es `(".marketId", "missing") in _tuples(records)` — pertenencia, no
     igualdad. Con el payload `{"symbol": "DLR/DIC26"}` (sin `market_id`) el mirror D-04 no dispara,
     así que `marketId` sigue emitiendo `missing` y el test **sobrevive sin edición**.
   - Qué no está claro: si dejarlo pasando vacuamente es aceptable bajo el criterio 4.
   - Recomendación: re-derivarlo igual, agregando un caso con `market_id` presente que demuestre
     que el mirror **elimina** ese `missing`. Es la aserción que prueba D-04 en el lado del decode.

4. **¿Se actualiza el bloque de comentarios `models.py:1146-1156`?**
   - Qué sabemos: dice literalmente *"Exactly TWO fields qualify — `FeedIngestor.last_error` and
     `FeedPipeline.last_write_error`"*. Con D-09 pasan a ser cuatro.
   - Recomendación: sí — es prosa que pasa a ser falsa, exactamente el mismo caso que el docstring
     de `_core.py` que D-14 sí manda actualizar.

---

## Project Constraints (from CLAUDE.md)

| Directiva | Cómo la cumple esta fase |
|-----------|--------------------------|
| Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy strict; debe pasar el CI existente | Sin dependencias nuevas; los 4 jobs son el phase gate |
| Estado singleton a nivel de módulo; **sin código compartido entre paquetes** | El fix vive dentro de `market-data-client`; el `Segment` de matriz **no se toca** pese a compartir nombre de campo |
| Dual sync/async: todo fix de **lógica** se espeja en `client.py` y `aio.py` | **No aplica** — es un cambio de forma de modelo alcanzado por un único `_core.py` compartido (REFAC-03). D-14 lo declara y esta investigación lo confirmó leyendo los parsers |
| Credenciales en `.env` por paquete; nunca commitear `.env` ni exponer credenciales en logs/reportes/tests | Sin acceso a credenciales; sin corrida en vivo (D-07). El vector real acá es PII de payload, no credenciales — ver Pitfall 6 |
| Dependencias externas en vivo: resultados varían por horario/rate limits | Neutralizado: la fase es offline por diseño |
| Todo módulo arranca con `from __future__ import annotations` | `models.py` ya lo tiene; nada nuevo lo requiere |
| Modelos: `@dataclass(frozen=True, slots=True)` + `SafeModel` + construcción **exclusiva** vía `Model.from_api(payload)` | `FeedSubscription` lo sigue; los tests nunca construyen con kwargs directos |
| Nombres de campo verbatim del wire | `market_id`, `days_to_maturity`, `live_instruments`, `symbols_never_delivered` — snake_case porque el wire lo manda así; `marketId` sobrevive **sólo** como alias deprecado |
| `__all__` explícito con todos los nombres públicos | `FeedSubscription` en `models.__all__` (obligatorio, T12) y en el `__all__` del paquete (consistencia, A5) |
| Docstring de módulo + docstring de función pública con endpoint en rst-backtick | Toda clase nueva/modificada lleva docstring con procedencia de captura, siguiendo el patrón de `Symbol` / `FeedMarket` |
| **GSD Workflow Enforcement** — no editar fuera de un comando GSD | Esta investigación no editó ningún archivo del repo; sólo lectura + ejecución de gates y de la suite |

---

## Sources

### Primary (HIGH confidence) — leídos/ejecutados en esta sesión

- `packages/market-data-client/src/market_data_client/models.py` — `SafeModel:126-229`, `Instrument:786-800`, `Segment:802-813`, `Symbol:816-901`, `CalendarDay/CalendarConfig:904-955`, bloque health `:1133-1343`, `__all__:95-123`
- `packages/market-data-client/src/market_data_client/_decode.py` — `_kind_of:367-371`, `walk_field:417-555` (confirmado: **sin rama `dict`**), `walk_model:558-613`
- `packages/market-data-client/src/market_data_client/_core.py:975-1099` — los tres parsers
- `tools/check_surface_types.py` — `_MAPPING_BASES:273-283`, `_FIELD_EXEMPTIONS:314-316`, `_class_names:749-796`, `_field_annotation_is_optional_model:799-881`, `_field_candidates_for:1010-1034`, `_adjudicate_field:1037-1084`, `scan_surface_types:1087-1232`. **Ejecutado:** `0 violations`, 442 campos
- `verification/divergences.py:112-188` — `DivergenceHandler.emit`, la traducción record→finding
- `.github/workflows/ci.yml` — los 4 jobs; `surface-types` = paso 8 de `lint` (`:61-66`)
- `pyproject.toml` — `[tool.mypy] files` (`:97`), `[tool.pytest.ini_options] testpaths` (`:106`)
- `.pre-commit-config.yaml` — mypy `files: ^packages/.*/src/`
- `.gitignore:52-53` — captures gitignored
- `.planning/verification/captures/market-data-wire-{instruments,segments}-42.json` — **re-analizados** (50 y 4 filas, key-sets y tipos por columna)
- Tests leídos con anclas: `test_reference_models.py:1-289`, `test_reference_core.py:150-304`, `test_reference_client.py:55-110`, `test_reference_async_client.py:55-110`, `test_reference_envelope_unwrap.py:37-147`, `test_decode.py:650-745` y `:1320-1400`, `test_core.py:935-1210` y `:1460-1490`, `test_public_surface_market_data.py:90-130`, `test_surface_parity.py:1-40`
- `verification/test_cycle_closure_phase33.py:40-95` — los pisos medidos
- `main_market_data.py:1520-1560` — `probe_parity`; y el mapa de `_emit_shape` (`:1003`, `:1043`, `:1383`, `:1409`)
- **Ejecutado:** `uv run pytest packages/market-data-client -q --no-cov` → **711 passed en 1.05 s**

### Secondary (HIGH confidence) — artefactos de planning citados

- `.planning/phases/42-.../42-WIRE-READ.md` — §1 sobre, §2 schema medido, §3 marca NO-AUTORITATIVO, §4 delta vacío, §4.1 `_emit_shape` inerte, §5 política de crudo
- `.planning/verification/market-data-client-findings.md` — F-70/F-71 (`:944-951`, blob de `subscription` de 15 claves), F-109/F-140 (`Symbol.note`), F-202 (`:1567-1571`), índice F-205…F-242
- `.planning/research/ARCHITECTURE.md` §Group 3 — corrobora independientemente el hallazgo de `main_market_data.py` (con numeración de línea previa `:1507-1508`; la medición de hoy es `:1541-1542`)
- `.planning/research/SUMMARY.md:141` — la asunción LOW de `unconfirmed_symbols`
- `.planning/REQUIREMENTS.md:19-22, 45-49, 62-63, 82-83` — texto verbatim de SHAPE-01 / HARN-02 y Out of Scope
- `.planning/STATE.md:415` — el registro histórico de por qué 33-07 difirió este fix

### Tertiary (LOW confidence)

Ninguna. **Cero búsquedas web se ejecutaron**: el dominio es enteramente interno a este repo y toda
afirmación se resolvió leyendo o ejecutando código local. No hay ninguna fuente cuya única
respaldo sea conocimiento de entrenamiento.

---

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — no hay stack nuevo; el existente se leyó de `pyproject.toml`, `ci.yml` y `.pre-commit-config.yaml`, y se ejecutó
- Wire medido: **HIGH** — 50/50 filas de instruments y 4/4 de segments re-analizadas desde el capture, no citadas del schema de la primera fila
- Mecánica de gates: **HIGH** — `check_surface_types.py` leído entero y ejecutado (`0 violations`); `walk_field`/`walk_model` leídos rama por rama
- Mapa de sitios afectados: **HIGH** — 11 sitios de test con anclas de línea verificadas por `grep` + lectura; 2 de ellos (T13/T14) son hallazgos nuevos no listados en D-12
- Arquitectura (D-14, sin cambios en `client.py`/`aio.py`): **HIGH** — los tres parsers leídos, field-agnostic confirmado
- Pitfalls: **HIGH** para los 6 (cada uno con línea de código o comando de verificación); A6 (alcance de Pitfall 1) es **MEDIUM** por ser una decisión de alcance, no una medición
- Tipo de elemento de `unconfirmed_symbols` (A1) y miembro `bool` de `Instrument.active` (A2): **LOW** — no observados; ambos autocorrectivos vía censo

**Research date:** 2026-08-31
**Valid until:** indefinido para las afirmaciones de código (son propiedades del árbol en HEAD `11dc42b`); **las dos capturas del 42 son perecederas** — desaparecen con un `git clean -xdf` o en otro clone, y no se pueden recuperar de git por diseño (`42-WIRE-READ.md` §5)
