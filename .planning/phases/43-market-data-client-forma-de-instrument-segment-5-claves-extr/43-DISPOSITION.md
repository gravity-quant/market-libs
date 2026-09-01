# Phase 43 — Disposición campo por campo, evidencia medida y seguimiento

**Fecha:** 2026-09-01 · **Requisitos:** `SHAPE-01`, `HARN-02` · **Planes:** 43-01, 43-02, 43-03
**Fuente de forma:** la lectura FRESCA del wire del 2026-08-31 (`42-WIRE-READ.md` § 2), **no** los
baselines committeados de `.planning/verification/schemas/market-data-client/`, que esa misma
sección marca **NO-AUTORITATIVOS** para forma.

Este archivo es la evidencia de los criterios 1, 2, 3 y 5 de la fase. Todo lo que afirma está
**medido en la corrida de este plan** y la medición está pegada; nada se hereda de un reporte.

**Restricción de seguridad activa (T-43-11 / T-42-05).** Los captures crudos de la Phase 42 viven en
`.planning/verification/captures/`, excluido por `.gitignore` con el comentario de que son capturas
crudas con PII y nunca committeables; `42-WIRE-READ.md` § 5 prohíbe transcribir la clave `payload`
a git. Este archivo **sí** se commitea, así que la restricción aplica en su forma más estricta:
abajo hay **nombres de clave, conteos de fila y tipos de Python**, y **cero valores** del crudo.
Todo valor que aparece en este documento es **sintético** y está marcado como tal.

**Verificación capture-vs-artefacto ejecutada.** Se extrajeron los **69 valores escalares distintos**
de los dos captures y se buscó cada uno en este archivo con match de palabra completa. Resultado:
**una** coincidencia, y es benigna y explicada — `maturity` vale `2026-08-31` en las **50/50** filas
del capture de `/instruments`, que es la **misma fecha de la corrida**, y este documento usa
`2026-08-31` sólo en prosa como fecha de la lectura, un dato ya committeado en `42-WIRE-READ.md` y
en los summaries 43-01/43-02. **Ninguna fila, ningún valor de `segment` y ningún valor de
`live_instruments` fue transcrito.** Los valores sintéticos de § 2 usan el prefijo `GSDPROBE`/`GSD` y
una `maturity` deliberadamente distinta (`2026-12-31`) para que la separación sea visible.

---

## 1. Tabla de disposición campo por campo (criterio 1)

Regla dura de completitud: **cero filas sin disponer**. La unión de (campos declarados antes del
cambio) con (claves del wire fresco) aparece entera, y cada fila lleva exactamente una de las cuatro
disposiciones: `alias aditivo` / `remover` / `agregar` / `mantener`.

### 1.1 `Instrument` — `GET /instruments`

Conteo esperado: **12 filas** = 5 declarados antes + 10 claves medidas − 3 en ambos conjuntos.
Key-set medido (50 filas, todas homogéneas): `active`, `currency`, `days_to_maturity`, `expired`,
`market_id`, `maturity`, `outright`, `segment`, `subscribed`, `symbol`.

| Campo | Origen | Disposición | Tipo final | Evidencia | Decisión |
|---|---|---|---|---|---|
| `symbol` | ambos | **mantener** | `str` | `42-WIRE-READ.md` § 2 — presente 50/50 filas; cero records en el ledger | D-01 |
| `segment` | ambos | **mantener** | `str` | `42-WIRE-READ.md` § 2 — presente 50/50 filas; cero records en el ledger | D-01 |
| `expired` | ambos | **mantener** | `bool` | `42-WIRE-READ.md` § 2 — presente 50/50 filas; cero records en el ledger | D-01 |
| `marketId` | declarado-hoy | **alias aditivo** | `str` | `F-212` (sync) / `F-236` (async): `missing (declared=str, observed=NoneType)` | D-04 |
| `market_id` | clave-del-wire | **agregar** | `str` | `F-208` (sync) / `F-232` (async): `extra (declared=-, observed=str)` | D-02 |
| `currency` | clave-del-wire | **agregar** | `str` | `F-206` (sync) / `F-230` (async): `extra (declared=-, observed=str)` | D-02 |
| `days_to_maturity` | clave-del-wire | **agregar** | `int` | `F-207` (sync) / `F-231` (async): `extra (declared=-, observed=int)` | D-02 |
| `maturity` | clave-del-wire | **agregar** | `str` | `F-209` (sync) / `F-233` (async): `extra (declared=-, observed=str)` | D-02 |
| `outright` | clave-del-wire | **agregar** | `bool` | `F-210` (sync) / `F-234` (async): `extra (declared=-, observed=bool)` | D-02 |
| `subscribed` | clave-del-wire | **agregar** | `bool` | `F-211` (sync) / `F-235` (async): `extra (declared=-, observed=bool)` | D-02 |
| `active` | clave-del-wire | **agregar** | `bool \| None = None` | `F-205` (sync) / `F-229` (async): `extra (declared=-, observed=NoneType)` — `null` en 50/50 | D-03 |
| `instrumentType` | declarado-hoy | **remover** | — | `F-213` (sync) / `F-237` (async): `missing (declared=str, observed=NoneType)`; el wire nunca mandó la clave | D-05 |

**La fila del alias, explícitamente.** `marketId` se dispone como **`alias aditivo`**, nunca como
rename. `Instrument` es superficie **publicada** desde v0.2.0 y `REQUIREMENTS.md` § Out of Scope
prohíbe el rename directo; el precedente aplicable es **D-22** (`Symbol.marketId`), copiado verbatim:
el campo wire-correcto se agrega al lado y `Instrument.from_api` espeja `market_id` sobre `marketId`
**antes** de que el walker vea el payload, así que el alias —que contra un payload real estaba
permanentemente en `""`— pasa a llevar el valor real y no dispara un record `extra` espurio. El
espejo **rellena** una clave ausente y nunca pisa una explícita, y copia el dict en vez de mutar el
del caller. Remoción programada para el próximo MAJOR.

**Por qué `active` es el único `| None`.** El miembro `bool` de la unión **nunca fue observado**: es
una **asunción declarada**, autocorrectiva vía el censo de divergencias. Declararlo `bool` plano
habría convertido una `extra` medida en un `missing` **permanente sobre cada lectura de catálogo**
— exactamente el flip que el criterio 3 prohíbe.

### 1.2 `Segment` — `GET /instruments/segments`

Conteo esperado: **5 filas** = 3 declarados antes + 2 medidas, **sin intersección**.
Key-set medido (4 filas, todas homogéneas): `segment` (str), `live_instruments` (int).

| Campo | Origen | Disposición | Tipo final | Evidencia | Decisión |
|---|---|---|---|---|---|
| `segment` | clave-del-wire | **agregar** | `str` | `F-215` (sync) / `F-239` (async): `extra (declared=-, observed=str)` — 4/4 filas | D-06 |
| `live_instruments` | clave-del-wire | **agregar** | `int` | `F-214` (sync) / `F-238` (async): `extra (declared=-, observed=int)` — 4/4 filas | D-06 |
| `marketSegmentId` | declarado-hoy | **remover** | — | `F-216` (sync) / `F-240` (async): `missing (declared=str, observed=NoneType)` | D-06 |
| `marketId` | declarado-hoy | **remover** | — | `F-217` (sync) / `F-241` (async): `missing (declared=str, observed=NoneType)` | D-06 |
| `description` | declarado-hoy | **remover** | — | `F-218` (sync) / `F-242` (async): `missing (declared=str, observed=NoneType)` | D-06 |

`Segment` **no** se alias-mapea bajo D-22, y el rechazo es explícito: la precondición de ese
precedente es **una misma clave con variante de spelling** camelCase/snake_case, mientras que
`marketSegmentId` y `segment` son simplemente **nombres distintos**. El modelo se reemplaza, no se
extiende, y no lleva override de `from_api`.

**Remoción no-breaking (argumento D-13).** Los tres campos removidos de `Segment` y el
`instrumentType` de `Instrument` no pueden haber tenido nunca un valor poblado en ningún consumidor
liberado: sus claves no existen en el wire, así que toda instancia decodificó cadenas vacías. Para
`Segment` el caso es más fuerte todavía — los dos key-sets eran **disjuntos**, así que la fila
entera salía vacía (medido en § 2).

### 1.3 Las 5 claves de HARN-02

| Clave | Modelo | Tipo final | Nullable | Evidencia medida que respalda la nulabilidad o su ausencia | Decisión |
|---|---|---|---|---|---|
| `subscription` | `FeedIngestor` | `FeedSubscription` (modelo anidado de 15 campos) | **no** | `F-70` (sync): `- -> dict at FeedIngestor.ingestor.subscription`; el blob de `F-71`/`F-202` trae las 15 claves pobladas. No-opcional porque la ausencia ya la cubre el Null Object (NOBJ-02) y porque `D-NO-01` de `check_surface_types.py` reddenea `Model \| None` en clase exportada | D-08 |
| `last_error_age_seconds` | `FeedIngestor` | `int \| None = None` | **sí** | `F-68` (sync) / `F-88` (async). **AUSENTE** del baseline sano del 2026-07-31 (donde `last_error` es `null`) y **PRESENTE** en toda captura posterior junto a un `last_error` poblado → condicional a que exista un error | D-09 |
| `last_error_at` | `FeedIngestor` | `str \| None = None` | **sí** | `F-69` (sync) / `F-89` (async). Misma condicionalidad, mismo par de estados medidos | D-09 |
| `symbols_never_delivered` | `HealthFeed` | `int` (**plano**) | **no** | `F-67` (sync) / `F-87` (async). Ausente **sólo** del baseline stale del 2026-07-31; poblada como `int` en las tres capturas posteriores → doctrina option-b: un `Optional` sobre-declarado absorbería un futuro `null` sin dejar record | D-11 |
| `note` | `Symbol` | `str \| None = None` | **sí** | `F-140` (sync) / `F-109` (async), ambos sobre `/symbols/{symbol_id}`. Presente en los acks de escritura, ausente de las filas de `GET /symbols`; un solo modelo sirve los cuatro endpoints → condicional **por forma de respuesta** | D-10 |

Los 15 campos de `FeedSubscription` van todos planos: las 15 claves volvieron pobladas en la captura
medida. La única asunción declarada es el **tipo de elemento** de `unconfirmed_symbols`, que llegó
como lista vacía y se tipa `list[str]` espejando a su hermana poblada `quarantined_symbols`; una
elección equivocada aflora como record `type` en el próximo censo, no en silencio.

---

## 2. Antes/después medido de `get_segments()` (criterio 2, D-07)

La demostración es **OFFLINE**. El servicio en vivo no se vuelve a golpear en esta fase.

### 2.a Estado ANTES — citado del ledger append-only

`.planning/verification/market-data-client-findings.md`, corrida del 2026-08-31, las dos superficies:

```
### F-214 -- Segment.live_instruments: extra (declared=-, observed=int) [sync]
### F-215 -- Segment.segment: extra (declared=-, observed=str) [sync]
### F-216 -- Segment.marketSegmentId: missing (declared=str, observed=NoneType) [sync]
### F-217 -- Segment.marketId: missing (declared=str, observed=NoneType) [sync]
### F-218 -- Segment.description: missing (declared=str, observed=NoneType) [sync]
### F-238 -- Segment.live_instruments: extra (declared=-, observed=int) [async]
### F-239 -- Segment.segment: extra (declared=-, observed=str) [async]
### F-240 -- Segment.marketSegmentId: missing (declared=str, observed=NoneType) [async]
### F-241 -- Segment.marketId: missing (declared=str, observed=NoneType) [async]
### F-242 -- Segment.description: missing (declared=str, observed=NoneType) [async]
```

Las **dos** claves del wire como `extra` y los **tres** campos declarados como `missing`, en sync y
en async: key-sets disjuntos, confirmado por medición y no por lectura del código.

### 2.b Key-set y conteo de filas del capture del 42 — leídos en tiempo de ejecución de este plan

Leído de `.planning/verification/captures/market-data-wire-segments-42.json` (gitignored). Se
transcriben **sólo** claves, conteos y tipos:

```
top-level keys: ['base_url', 'captured_at', 'client_function', 'endpoint', 'n_rows', 'payload', 'schema']
envelope keys (payload): ['catalogue', 'segments']
ROW COUNT: 4
ROW KEY-SET (clave -> filas presentes / tipo Python):
  live_instruments: 4/4  ['int']
  segment:          4/4  ['str']
```

Y el gemelo de `/instruments`, por completitud de la tabla § 1.1:

```
envelope keys (payload): ['catalogue', 'count', 'items', 'limit', 'offset', 'total']
ROW COUNT: 50
  active: 50/50 ['NoneType']   currency: 50/50 ['str']       days_to_maturity: 50/50 ['int']
  expired: 50/50 ['bool']      market_id: 50/50 ['str']      maturity: 50/50 ['str']
  outright: 50/50 ['bool']     segment: 50/50 ['str']        subscribed: 50/50 ['bool']
  symbol: 50/50 ['str']
```

`active` llegó `NoneType` en **50 de 50** filas — la medición que respalda D-03.

### 2.c ANTES ejecutado — la forma pre-fix sobre una fila sintética del key-set medido

Réplica exacta de la `Segment` publicada hasta v0.6.0 (el field-set que `F-216`/`F-217`/`F-218`
reportan como declarado), decodificando la misma fila sintética:

```
=== ANTES (replica medida de la forma pre-fix) sobre la MISMA fila sintetica ===
  fields declarados: ['marketSegmentId', 'marketId', 'description']
  s.marketSegmentId  = ''
  s.marketId         = ''
  s.description      = ''
  divergence records = [('.description', 'missing'), ('.live_instruments', 'extra'),
                        ('.marketId', 'missing'), ('.marketSegmentId', 'missing'),
                        ('.segment', 'extra')]
  todos los campos vacios: True
```

**Cinco** records y una fila de tres cadenas vacías — el mismo 2+3 que el ledger reportó en vivo.

### 2.d Estado DESPUÉS — decodificación ejecutada, fila sintética del key-set medido

```
=== DESPUES — Segment.from_api sobre una fila sintetica del key-set medido ===
  fields declarados: ['segment', 'live_instruments']
  s.segment          = 'GSDPROBE-SEG'
  s.live_instruments = 7
  bool(s)            = True
  divergence records = []

=== DESPUES — Instrument.from_api sobre una fila sintetica del key-set medido ===
  fields declarados: ['symbol', 'marketId', 'segment', 'expired', 'market_id', 'currency',
                      'days_to_maturity', 'maturity', 'outright', 'subscribed', 'active']
  i.symbol           = 'GSDPROBE/SYM'
  i.marketId         = 'GSDMKT'
  i.segment          = 'GSDPROBE-SEG'
  i.expired          = False
  i.market_id        = 'GSDMKT'
  i.currency         = 'GSD'
  i.days_to_maturity = 42
  i.maturity         = '2026-12-31'
  i.outright         = True
  i.subscribed       = True
  i.active           = None
  divergence records = []
```

Los valores de arriba son **sintéticos** (prefijo `GSDPROBE`, `GSD`, fechas inventadas). Lo que se
hereda del crudo es exclusivamente el **key-set** y los **tipos**. Nótese que `i.marketId` sale
poblado sin que la fila lo traiga: es el espejo de D-04 en acción, y por eso no hay record `extra`.

### 2.e El test reproducible que lo pinnea — porque el capture es perecedero y el test no

`packages/market-data-client/tests/test_reference_envelope_unwrap.py`, aserciones de **valor**
agregadas en el plan 43-01:

- `test_get_segments_unwraps_the_segments_envelope` → `result[0].segment == "SEG1"` y
  `result[0].live_instruments == 7`
- `test_get_segments_unwraps_the_segments_envelope_async` → idéntico, gemelo async
- `test_get_instruments_unwraps_the_items_envelope` (+ gemelo async) → vía el helper de módulo
  `_assert_instrument_row_is_populated`

El desenvolvimiento del sobre por sí solo sólo probaba el **conteo**; un test que hace `isinstance`
sobre una fila entera vacía pasa **vacuamente**. Ésa es la razón por la que las aserciones de valor
existen y por la que el criterio 2 queda reproducible desde la suite sola.

### 2.f Por qué el SHAPE-diff del driver NO sirve como evidencia acá (D-07)

`main_market_data.py` construye el sample del SHAPE-diff así, en los cuatro sitios de reference-data:

```python
sample = raw[0] if isinstance(raw, list) and raw else None   # :1002 (instruments), :1041 (segments)
if isinstance(sample, dict):
    _emit_shape(sample, Segment, "Segment", "sync", base_url)
```

El wire de estos dos endpoints es un **sobre de tipo dict** (`{catalogue, segments}` /
`{catalogue, count, items, limit, offset, total}`, § 2.b). Con `raw` dict, `isinstance(raw, list)`
es falso → `sample = None` → el `if` no entra → **el diff se saltea en silencio**. Un "cero findings
de SHAPE" post-fix sobre estos dos modelos sería un **falso verde**: el diff estaba inerte antes del
fix y sigue inerte después. La evidencia real del criterio 2 es la de arriba — el **censo de
divergencias** (§ 2.a) más el **capture** (§ 2.b) más los **tests** (§ 2.e).

---

## 3. Criterio 3 — ninguna `extra` se convirtió en `missing`

Probado, no afirmado, por `test_measured_health_feed_payload_produces_zero_divergence_records`
(`packages/market-data-client/tests/test_core.py`): el payload medido del 2026-08-31 decodifica con
la lista de records **vacía** — ni `extra`, ni `missing`, ni `type`.

| Clave | Record contra un payload sano | Record contra la fixture congelada del 2026-07-31 |
|---|---|---|
| `FeedIngestor.subscription` | ninguno | ninguno |
| `FeedIngestor.last_error_age_seconds` | ninguno | ninguno |
| `FeedIngestor.last_error_at` | ninguno | ninguno |
| `HealthFeed.symbols_never_delivered` | ninguno | **`missing`** (único, y correcto — ver abajo) |
| `Symbol.note` | ninguno | ninguno |

**La mecánica, no la afirmación:**

- `last_error_age_seconds` y `last_error_at` son `| None`, y la rama **`Union`** de `walk_field`
  retorna temprano **sin llamar al sink** (`_decode.py:437-444`). Una clave ausente no puede
  producir un record.
- `subscription` es un **modelo anidado no-opcional**, así que la clave ausente colapsa al Null
  Object bajo `SILENT_SINK` (`_decode.py:495-503`, NOBJ-02) — también sin emitir.
- `symbols_never_delivered` es **plano** por D-11, así que contra un payload que no trae la clave la
  rama escalar llama al sink con `_kind_of(None) == "missing"`. Bajo la doctrina option-b **ésa es
  la señal que se quería**: la clave está en el wire real, la fixture es del 2026-07-31 y es vieja,
  y el record lo dice. Declararla `int | None` habría hecho desaparecer ese record **y** el de
  cualquier `null` futuro.

Tests reproducibles que lo pinnean:
`test_health_feed_from_api_drops_an_undeclared_key_and_reports_it_once` (asserta la lista **exacta**
de records: `[(".brand_new_wire_key", "extra"), (".symbols_never_delivered", "missing")]`, en el
orden del walker — claves sobrantes primero y ordenadas, después los campos declarados en orden de
declaración) y `test_healthy_feed_payload_emits_no_missing_for_the_conditional_error_fields`.

**El punto ciego que se cerró.** Antes, `ingestor.subscription` era **un** record `extra` y sus 15
campos **no existían para el walker**: `walk_field` no tiene rama para mappings y cae al `return
value` final sin caminar ni reportar. Tiparlo como `dict[str, Any]` habría dejado ese punto ciego en
su lugar de forma **permanente**; tiparlo como modelo anidado devuelve el sub-objeto entero al
alcance del censo.

**Criterio 4, de paso.** `test_every_fixture_key_is_a_measured_wire_key` asserta que la fixture
congelada es **subconjunto** de la medición, nunca superset ni solapamiento — sin tocar un solo
baseline write-once: `_MEASURED_HEALTH_FEED_43` es fixture **nueva**, `_CAPTURED_HEALTH_FEED` quedó
byte-idéntica, y ningún test fue renombrado ni borrado en los planes 43-01 y 43-02.

---

## 4. Criterio 5 — D-14 **medido**, no asumido

La afirmación a probar: `client.py` y `aio.py` requieren **cero** cambios de fuente porque las dos
superficies delegan al **mismo objeto función** del parser.

### 4.a Ninguna de las dos superficies dereferencia por nombre un campo removido ni uno agregado

```
$ grep -nE "\.(symbol|marketId|segment|expired|market_id|currency|days_to_maturity|maturity|\
outright|subscribed|active|instrumentType|marketSegmentId|description|live_instruments)\b" \
    packages/market-data-client/src/market_data_client/{client,aio}.py
(sin salida — exit status 1, cero coincidencias)
```

Los nombres `segment`, `market_id`, `active` y `subscribed` **sí** aparecen en los dos archivos,
pero como **parámetros de query de la request** de `get_instruments()` (`client.py:547-551`,
`aio.py:549-553`), que van a `_core.build_instruments_request`. Son filtros de entrada, no accesos
a atributos del modelo de respuesta. El grep de arriba discrimina por el punto de dereferencia
justamente para no confundir las dos cosas — y devuelve cero.

### 4.b Las dos superficies llaman al MISMO objeto función

```
=== (b1) el _core alcanzado desde cada superficie es el MISMO modulo ===
client._core is _core: True
aio._core    is _core: True

=== (b2) identidad del objeto funcion alcanzado desde cada superficie ===
client -> _core.parse_segments_response is _core.parse_segments_response: True
aio    -> _core.parse_segments_response is _core.parse_segments_response: True
client -> _core.parse_instruments_response is _core.parse_instruments_response: True
aio    -> _core.parse_instruments_response is _core.parse_instruments_response: True

=== (b3) call sites: ambas superficies llaman _core.parse_X, ninguna redefine ===
client.py:570:        return _core.parse_instruments_response(resp)
client.py:576:        return _core.parse_segments_response(resp)
aio.py:572:        return _core.parse_instruments_response(resp)
aio.py:578:        return _core.parse_segments_response(resp)
```

**Nota de método.** El plan 43-03 especificaba la medición como
`client.parse_segments_response is _core.parse_segments_response`. Eso levanta `AttributeError`: los
parsers **no** están re-exportados en la superficie, se alcanzan como atributo del módulo `_core`
importado. La medición de arriba prueba la **misma** afirmación por el camino de referencia real —
el módulo alcanzado desde cada superficie es idéntico (`is`), el objeto función alcanzado desde cada
superficie es idéntico (`is`), y los cuatro call sites son la única forma en que las superficies
tocan los parsers. Si alguno hubiera impreso `False`, D-14 sería falso, las dos superficies
necesitarían cambio y eso excedería el alcance lockeado.

### 4.c El diff acumulado de la fase no lista ninguna de las dos superficies

```
$ git diff --name-only 396c717 HEAD
.planning/REQUIREMENTS.md
.planning/ROADMAP.md
.planning/STATE.md
.planning/phases/43-.../43-01-SUMMARY.md
.planning/phases/43-.../43-02-SUMMARY.md
packages/market-data-client/src/market_data_client/models.py
packages/market-data-client/tests/test_core.py
packages/market-data-client/tests/test_decode.py
packages/market-data-client/tests/test_models.py
packages/market-data-client/tests/test_reference_async_client.py
packages/market-data-client/tests/test_reference_client.py
packages/market-data-client/tests/test_reference_core.py
packages/market-data-client/tests/test_reference_envelope_unwrap.py
packages/market-data-client/tests/test_reference_models.py

$ git diff --name-only 396c717 HEAD | grep -cE "market_data_client/(client|aio)\.py|^main_market_data\.py"
0
```

Los gemelos async de los tests del plan 43-01 pasan **sin ningún cambio de fuente en `aio.py`** —
la corrección de forma llega a las dos superficies gratis porque los parsers son field-agnostic.

### 4.d Prosa de fuente reconciliada (la única que la corrección volvió falsa)

`_core.py::parse_segments_response` declaraba que la corrección de forma estaba **DELIBERADAMENTE**
diferida y ruteaba al backlog `SHAPE-MD-REF-33`. Ambas afirmaciones pasaron a ser falsas. Medición
post-edición:

```
DELIBERATELY present: False
SHAPE-MD-REF-33 present: False
segments+received_at survive: True
```

El resto del docstring quedó **verbatim**: la descripción del sobre y su clave de desenvolvimiento,
la referencia cruzada a `parse_instruments_response`, el bug S-1 de la Phase 33 con sus findings, el
párrafo de compatibilidad del body de lista pelada y sus guardas de colapso a `[]`, el orden
body-consume-then-raise, y la nota de que no hay stamp `received_at` (D-05).

`parse_instruments_response` se revisó por la misma clase de prosa obsoleta y **queda intacto**: su
docstring es **field-agnostic** por diseño — describe el sobre, el bug de desenvolvimiento y las
guardas, y no afirma nada sobre el field-set declarado de `Instrument`
(`'instrumentType' in doc` → `False`).

### 4.e Gate de no-publicación (D-16)

```
$ uv run python -c "import market_data_client; print(market_data_client.__version__)"
0.6.0
$ grep -n '^version = ' packages/market-data-client/pyproject.toml
3:version = "0.6.0"
```

Los tres sitios de versión (`pyproject.toml`, `__init__.py::__version__`, `uv.lock`) quedan en el
valor de **entrada** de la fase, sin cambio. El release es la **Phase 44** por precedente lockeado.

---

## 5. Ítem de seguimiento — el dereference del driver

**Sitio:** `main_market_data.py:1541-1542`, dentro de `probe_parity_sync_async`.

```python
try:
    ids_sync = sorted(s.marketSegmentId for s in seg_sync)
    ids_async = sorted(s.marketSegmentId for s in seg_async)
except Exception as exc:  # D-09: la comparación nunca crashea el driver
    return _finding_for_exc(exc, name=name, surface="both", base_url=base_url)
```

**Qué hace.** Dereferencia `Segment.marketSegmentId`, el campo que **D-06 removió** en el plan 43-01.

**Por qué ningún gate estático lo detecta — medido, no supuesto:**

| Gate | Alcance configurado | Ve el driver? |
|---|---|---|
| `typecheck` (mypy) | `files = [...seis rutas `packages/*/src`...]` (`pyproject.toml:97`) | **no** — el driver vive en la raíz del repo |
| `pre-commit` (hook mypy) | `files: ^packages/.*/src/` (`.pre-commit-config.yaml:32`) | **no** — mismo motivo |
| `verification/test_main_market_data_deep_chain.py` | parsea el driver con `ast` **sin importarlo**; audita cadenas de acceso profundo de market data | **no** — no resuelve atributos |

Apuntar mypy al archivo a mano **sí** lo levanta, y eso cierra la pregunta de si el gap es de
tipabilidad o de alcance de gate:

```
$ uv run mypy main_market_data.py
main_market_data.py:1542: error: "Segment" has no attribute "marketSegmentId"  [attr-defined]
            ids_async = sorted(s.marketSegmentId for s in seg_async)
                               ^~~~~~~~~~~~~~~~~
Found 2 errors in 1 file (checked 1 source file)
```

Es **de alcance de gate**. El error existe y es trivialmente detectable; el CI simplemente no mira
ese archivo.

**Consecuencia.** El `try/except Exception` de la línea siguiente lo degrada a un **FINDING
silencioso de handler** en la próxima corrida en vivo, **no** a un crash: el probe de paridad
sync↔async de segments queda ciego sin que nadie lo note. Es exactamente el modo de falla que el
code review **CR-01 de la Phase 37** documentó.

**Disposición de esta fase: NO se corrige acá.** D-16 lockea el alcance de la Phase 43 a `models.py`
+ tests + el docstring de D-14, y este sitio no es ninguno de los tres. Corregirlo en silencio sería
un cambio fuera de alcance; descartarlo en silencio sería perder el hallazgo.

**Destino nombrado.** Entrada de backlog **`DRV-MD-SEG-43`** en `.planning/ROADMAP.md` § Backlog →
*Nuevos en v1.8 (from Phase 43)*. Candidato para la **Phase 44** (que ya toca el paquete para el
release y publica la tabla de migración vieja→nueva donde este campo aparece) o para la **Phase 45**
(limpieza del harness, que es donde vive el archivo). Corrección estimada: **2 líneas, sin lógica**;
no dispara la regla dual sync/async de `CLAUDE.md` por ser un dereference, no lógica de cliente.

---

## 6. Ítems de seguimiento menores

**`FeedSubscription` ausente del `__all__` del paquete.** La clase nueva del plan 43-02 quedó en
`models.__all__` pero **no** en el `__all__` de
`packages/market-data-client/src/market_data_client/__init__.py`. Es una inconsistencia con
`FeedMarket` y `FeedPipeline`, que sí están en los dos.

**Efecto secundario real, no cosmético:** `tools/check_surface_types.py` resuelve candidatos desde el
`__all__` de cada `__init__.py` hacia afuera, así que los **15 campos** de la clase nueva **no**
quedan escaneados por el gate. El `0 violations` que este documento reporta en § 7 es verdadero pero
**no cubre esta clase**.

**Disposición: no se corrige acá** (D-16). Destino nombrado: entrada de backlog
**`SURF-MD-FEEDSUB-43`** en `.planning/ROADMAP.md`; candidato para la **Phase 44**, que ya toca
`__init__.py` para el bump de versión.

---
