# 33-CENSUS.md — volumen real de divergencias contra el piso ratificado de la Phase 29

**Corrida:** 2026-08-27, UTC 00:45–00:57 (ARG 21:45–21:57, miércoles).
**Pre-flight:** `uv run python scripts/preflight_33.py` — 3 de 4 paquetes credencializados
autenticaron; ámbito es `n/a` por diseño.
**Mercado ARG:** **cerrado** en toda la ventana de corrida (21:45–21:57 hora local). Ningún
número de esta corrida proviene de una sesión de trading activa.

---

## Method

**La unidad del censo es la 4-tupla distinta `(slug, model, field_path, kind)` tomada de
`DivergenceHandler.seen`.** Es la única unidad que el harness produce y que se puede poner
al lado de `29-SIZING.md` sin traducir. Se agrega a `.seen` **antes** de llamar al sink,
así que una falla de escritura del archivo de findings no puede hacer que el censo se
reporte más chico (decisión de 33-01).

Dos números que **no** son comparables con el piso, y por qué:

- **El conteo de findings `SHAPE` escritos no lo es.** Bajo la convención de título
  lockeada en 33-01 (`surface-in-title-write-new`) la superficie va *dentro* del título,
  así que la identidad de dedupe cross-run es de seis componentes
  `(model, field_path, kind, declared, observed, surface)` y un mismo triple se escribe
  una vez por superficie. En esta corrida: 24 triples → 48 findings `SHAPE` de censo
  (más 22 de `schema drift`, ver más abajo). El factor ~2× es exactamente el que 33-01
  predijo.
- **El `FINDING=N` de la línea SUMMARY del driver tampoco lo es.** Cuenta probes cuyo
  `ProbeResult.status` es `FINDING`, no divergencias.

**El `_next_fid()` no es un contador de findings escritos.** El `DivergenceHandler` pide un
fid por **cada record**, y `append_finding(..., idempotent_by_title=True)` descarta el
write cuando el título ya existe. Un record que se repite (el walker emite por respuesta, y
`/marketdata` devuelve 100 snapshots) consume un fid y no escribe un bloque. Eso es el
dedupe content-addressed intencional, **no** la pérdida P-3.

### Corrección de unidad: el piso `≥96` es una suma de REGISTROS, no de triples distintos

`33-RESEARCH.md` Pattern 6 afirma que `handler.seen` es "la misma unidad que contó
`29-SIZING.md`". **No lo es, y la diferencia es material.** La columna `Count` de la tabla
de corpus de `29-SIZING.md` es *"the number of unique divergence records emitted by the
shipped walker for that file"* — única **dentro del archivo**, sumada **a través de** los 43
archivos. El mismo `(model, field_path, kind)` que aparece en dos archivos de corpus suma
dos veces al piso y una sola vez a `handler.seen`.

Contraste, derivado fila por fila de la tabla de corpus de `29-SIZING.md`:

| Paquete | Piso ratificado (suma de registros) | Equivalente en triples distintos | Origen de la diferencia |
|---|---:|---:|---|
| `higyrus-client` | ≥ 22 | 22 | Tres archivos, tres modelos disjuntos: no hay solapamiento. |
| `matriz-client` | ≥ 24 | 14 | Filas 38/39 son los mismos 3 triples de `Instrument`; 40/41 los mismos 7 de `InstrumentDetail`. |
| `market-data-client` | ≥ 50 | 22 | Filas 20-25 comparten los triples de `Symbol`; 30/31 comparten los 12 de `CalendarConfig`. |
| **Total** | **≥ 96** | **58** | |

**Este documento contrasta contra ambas columnas y lo dice en cada fila.** Contrastar un
conteo de triples distintos contra un piso de suma-de-registros produciría un "por debajo
del piso" fabricado por la unidad, que es precisamente el falso negativo que P-02 prohíbe —
en el sentido inverso al habitual: reportaría pérdida donde no la hay, y enterraría la
pregunta real.

---

## Per-package table

| Paquete | Piso 29-SIZING (registros) | Piso equiv. (triples distintos) | Triples distintos en vivo | Findings SHAPE escritos | `extra` (triples) | Handler errors | Veredicto |
|---|---|---|---:|---:|---:|---:|---|
| `ambito-financiero-client` | **N/A — no cero** | N/A | **0** | 0 | 0 | 0 | **Cero afirmado, no inferido.** Smoke D-12. |
| `higyrus-client` | ≥ 22 | 22 | **SKIPPED — vendor inalcanzable** | — | — | — | Sin medición. No es cero. |
| `iol-client` | **N/A — primera medición, sin presupuesto previo** | N/A | **0** | 0 | 0 | 0 | Canal probado vivo; el cero es inspección real. |
| `market-data-client` | ≥ 50 | 22 | **24** | 48 (censo) + 22 (drift) | 8 | 0 | **Supera el piso equivalente** (24 ≥ 22). |
| `matriz-client` | ≥ 24 | 14 | **SKIPPED — base URL fuera de política** | — | — | — | Sin medición. No es cero. |

### Líneas SUMMARY verbatim

```
ambito      P1 obs    SUMMARY: PASS=6  FAIL=0 SKIPPED=1  FINDING=0  DIVERGENCES=0  HANDLER_ERRORS=0
ambito      P2 strict SUMMARY: PASS=6  FAIL=0 SKIPPED=1  FINDING=0  DIVERGENCES=0  HANDLER_ERRORS=0
iol         P1 obs    SUMMARY: PASS=14 FAIL=0 SKIPPED=1  FINDING=0  DIVERGENCES=0  HANDLER_ERRORS=0
iol         P2 strict SUMMARY: PASS=14 FAIL=0 SKIPPED=1  FINDING=0  DIVERGENCES=0  HANDLER_ERRORS=0
market-data P1 obs    SUMMARY: PASS=39 FAIL=0 SKIPPED=0  FINDING=4  DIVERGENCES=24 HANDLER_ERRORS=0
market-data P2 strict SUMMARY: PASS=14 FAIL=0 SKIPPED=19 FINDING=10 DIVERGENCES=8  HANDLER_ERRORS=0
```

`market-data` base URL resuelta: `https://market-data-develop.bbsa.com.ar/api`
(registrada en el ART block del findings file).

### Notas por fila

**`ambito-financiero-client` — cero por construcción, afirmado positivamente.**
El paquete tiene cero clases de modelo (D-12), por lo tanto cero llamadas al walker. El
cero **no** se infiere de una ausencia: se afirma con tres señales simultáneas —
6 probes en PASS (conteo de probes distinto de cero), `len(handler.seen) == 0`, y
`len(handler.errors) == 0`. Un driver que no hubiera corrido daría los mismos ceros en las
últimas dos y un conteo de probes de cero en la primera.

**`iol-client` — primera medición, sin presupuesto previo. NO se le retro-adjudica un piso.**
`29-SIZING.md` reportó `N/A, not zero` porque el paquete no tenía `models.py` al momento del
sizing; la Phase 30 se lo dio. La regla de re-scope está escrita contra pisos por paquete
que iol no tiene, y `29-SIZING.md` es enfático en que sus números son **pisos, nunca
estimaciones**: fabricar uno acá sería inventar una referencia.

El `DIVERGENCES=0` de iol se investigó antes de aceptarlo (ver `## Under-floor
investigation`): el canal está **provablemente vivo**. Con `divergence_capture(("iol_client",))`
instalado, el logger `iol_client` sube de `NOTSET` a `INFO` (nivel 20) y un payload
sintético con una clave fabricada produce **17 triples** capturados y `handler.errors == []`.
El cero en vivo es por lo tanto un resultado de inspección: el wire real de IOL coincide
exactamente con `Cotizacion` en los 4 endpoints ejercitados.

**`higyrus-client` — `SKIPPED — vendor inalcanzable`, NO cero.**
El pre-flight imprimió `higyrus-client: AUTH FAIL ConnectError`. Diagnóstico acotado (sin
imprimir host ni credenciales): las tres variables (`HIGYRUS_BASE_URL`, `HIGYRUS_USER`,
`HIGYRUS_PASSWORD`) **están presentes**, el esquema es `https` y el hostname **no resuelve
por DNS** (`gaierror`). Es una falla de alcanzabilidad de red, no un rechazo de credenciales:
el host es plausiblemente interno/VPN desde esta red. Por D-13 el paquete se registra como
SKIPPED y se rutea al camino de operador-corre-y-pega de la Phase 23. **No se reintentó en
loop ni se intentó rodear la falla.**

**`matriz-client` — `SKIPPED — base URL fuera de política`, NO cero.**
El pre-flight imprimió `matriz-client: AUTH OK` — las credenciales **sí** autentican. El
driver, en cambio, aborta antes del primer probe:

```
ABORT: PRIMARY_BASE_URL='https://api.demo.matrizoms.com.ar' is not a remarkets sandbox URL
       — Phase 5 verification is remarkets-only by safety policy
```

Es el assert de hostname **D-MATZ-33** (`main_matriz.py:2550`), sin override, exit 1. Es la
misma política que la prohibición P-05 de este plan protege: la superficie de matriz
incluye entrada de órdenes, y el gate remarkets-only es el mecanismo que impide que un
sweep de verificación toque una venue real. **No se rodeó y no se debe rodear.** Tampoco se
reapuntó `PRIMARY_BASE_URL` al sandbox de remarkets: las credenciales del `.env` fueron
emitidas para el host demo, y mandarlas a un host de terceros distinto sería una fuga de
credenciales disfrazada de fix de configuración.

Consecuencia directa: **S-3, S-4 y S-5 no son decidibles en este ciclo**, y matriz no
contribuye ni un triple al censo.

---

## TYP-02 attribution

Divergencias que aparecen en vivo **porque un endpoint que era `N/A — dict sin modelar` en
el corpus de sizing ganó un modelo en la Phase 31**. Son visibles por ser nuevas-tipadas, no
por ser defectos nuevos; conflacionarlas con hallazgos nuevos corrompería la conversación de
re-scope.

| Paquete | Fila de corpus | Modelo Phase 31 | Triples en vivo | Especie |
|---|---|---|---:|---|
| `market-data-client` | 11 `get-health` | `Health` | 0 | — |
| `market-data-client` | 12 `get-health-feed` | `HealthFeed` / `FeedIngestor` | **4** | `extra` ×4 |
| `market-data-client` | 32-35 acks de calendar-write | `AddHolidaysResult` / `DeleteHolidayResult` | **0** | — (ejercitados con el gate ABIERTO; ninguna divergencia) |
| `higyrus-client` | 2 `get-health` | `Health` | SKIPPED | — |

Los 4 triples de TYP-02 en market-data son:

| Modelo | `field_path` | Especie | declared → observed |
|---|---|---|---|
| `HealthFeed` | `.symbols_never_delivered` | `extra` | `-` → `int` |
| `FeedIngestor` | `.ingestor.last_error_age_seconds` | `extra` | `-` → `int` |
| `FeedIngestor` | `.ingestor.last_error_at` | `extra` | `-` → `str` |
| `FeedIngestor` | `.ingestor.subscription` | `extra` | `-` → `dict` |

**Censo de market-data comparable con el piso, neto de TYP-02: 24 − 4 = 20 triples.**

Los cuatro acks de calendar-write **sí** se ejercitaron en vivo (el pase 1 corrió con el
gate de mutaciones abierto: `add_holidays` y `delete_holiday` reportaron PASS con
`wire_keys=3 saved=1` y `second_status=404`) y no produjeron ninguna divergencia. Eso es una
medición, no una omisión.

---

## Structural findings

Disposición de las cinco de `29-SIZING.md`, con la evidencia de esta corrida.

### S-1 — market-data: `parse_instruments_response` / `parse_segments_response` no desenvuelven el sobre — **CONFIRMADO**

Evidencia del pase observable: dos triples `non_dict`, uno por modelo, en las dos
superficies.

| Modelo | `field_path` | Especie | declared → observed |
|---|---|---|---|
| `Instrument` | *(raíz)* | `non_dict` | `Instrument` → `str` |
| `Segment` | *(raíz)* | `non_dict` | `Segment` → `str` |

Evidencia independiente del pase estricto: los cuatro probes correspondientes se detienen
con el raise, con el detalle determinístico:

```
PROBE instruments_sync:  FINDING SHAPE [sync]  MarketDataDecodeError model=Instrument path= declared=Instrument observed=str
PROBE segments_sync:     FINDING SHAPE [sync]  MarketDataDecodeError model=Segment    path= declared=Segment    observed=str
PROBE instruments_async: FINDING SHAPE [async] MarketDataDecodeError model=Instrument path= declared=Instrument observed=str
PROBE segments_async:    FINDING SHAPE [async] MarketDataDecodeError model=Segment    path= declared=Segment    observed=str
```

El caveat que `29-SIZING.md` dejó abierto ("puede que el servidor haya introducido el sobre
después de que se escribió el cliente") queda cerrado: el wire de hoy manda el sobre y el
parser de hoy no lo desenvuelve. El conteo de 2 registros **subestima el radio de daño**
—como el propio S-1 advierte— porque el walker deduplica a un record por modelo mientras
cada fila del catálogo decodifica a un modelo all-default.

**Destino: plan 33-07 (fix in-cycle).** Es el candidato número uno del presupuesto de fixes.

### S-2 — market-data: `preview_calendar_config` está tipado `CalendarConfig` pero el wire devuelve un sobre de preview — **CONFIRMADO, con la predicción exacta**

`29-SIZING.md` predijo *"nine declared `CalendarConfig` fields … absent … while three real
preview fields (`valid`, `requires_confirmation`, `market_after`) are discarded"*. La
corrida en vivo devuelve **exactamente esos 12 triples**:

| Especie | Campos |
|---|---|
| `missing` (9) | `.close`, `.editable`, `.enabled`, `.env_bypass`, `.open`, `.pre_open_minutes`, `.source`, `.timezone`, `.updated_by` |
| `extra` (3) | `.market_after`, `.requires_confirmation`, `.valid` |

**Sólo visible con el gate de mutaciones abierto**: los probes de preview están detrás del
doble gate. Un pase con el gate cerrado —como el que 33-04 midió— reporta 0 de estos 12.

**Destino: plan 33-07 (fix in-cycle).** El sobre de preview quiere su propio modelo (TYP-02).

### S-3 — matriz: `Instrument.instrumentId` ausente en byCFICode y bySegment — **COULD-NOT-DECIDE**

Motivo: `main_matriz.py` aborta antes del primer probe por el assert D-MATZ-33
(`PRIMARY_BASE_URL` no es remarkets). Cero probes de matriz corrieron, así que no hay wire
que confrontar contra el corpus de 2026-06-10.

`29-SIZING.md` lo llama *"the highest-consequence finding in the set"* y este plan no lo
mueve ni un milímetro. **No se marca resuelto y no se marca limpio.**

**Destino: `LIVE-MATZ-33` (ROADMAP § Backlog → Deferred to v1.7+).**

### S-4 — matriz: `InstrumentDetail` no declara siete campos que el wire manda — **COULD-NOT-DECIDE**

Mismo motivo que S-3. Los seis findings `NO-FIX` hand-written `F-03..F-08` que ya viven en
`.planning/verification/matriz-client-findings.md` siguen intactos —`append_finding` preserva
todo status no-`OPEN`— y el archivo no se movió en esta corrida (10 bloques antes, 10
después).

**Destino: `LIVE-MATZ-33`.**

### S-5 — matriz: `MarketDataSnapshot.LA/.SE/.OI/.CL` declarados no-`Optional` llegan `null` — **COULD-NOT-DECIDE, por partida doble**

Dos razones independientes, cada una suficiente:

1. matriz no corrió (D-MATZ-33).
2. **Aunque hubiera corrido, la captura habría sido de mercado cerrado.** La ventana de
   corrida fue ARG 21:45–21:57 de un miércoles; ninguna sesión de ARG está activa a esa
   hora. Un `null` de mercado cerrado es indistinguible de un error de modelado, que es
   exactamente el pitfall P-12 y exactamente lo que `29-SIZING.md` advierte sobre la captura
   original de 2026-06-10 (`BI` y `OF` vacíos).

**No se resuelve desde una captura de mercado cerrado.** El requisito de reprogramación
—correr el pase 1 de matriz dentro de una sesión de trading de ARG— queda escrito en el
destino.

**Destino: `LIVE-MATZ-33`, con el requisito de ventana horaria explícito.**

---

## Under-floor investigation

Dos resultados de esta corrida entran a esta sección. Ninguno se acepta con un encogimiento
de hombros.

### 1. `market-data`: 24 triples en vivo contra un piso ratificado de `≥ 50` — **NO es pérdida de censo**

El contraste correcto es contra el **equivalente en triples distintos, 22** (ver
`## Method`), no contra los 50 registros. Neto de TYP-02: **20 en vivo contra 22 de sizing,
delta de −2**, y los dos están individualmente explicados por cambio real de wire/modelo
entre 2026-07-31 y hoy:

| Modelo | Sizing (triples distintos) | En vivo | Delta | Explicación |
|---|---:|---:|---:|---|
| `MarketDataSnapshot` | 4 (`market_id`, `active`, `entries`, `staleness_seconds`) | 3 (`.entries`, `.market_data`, `.staleness_seconds`) | −1 | `market_id` y `active` **ya no divergen**: la reconciliación LIVE-MD-01 de la Phase 30 los dejó declarados y el wire los manda. `market_data` es un campo **nuevo** del modelo que la fila no-data de `/marketdata/latest` no manda → `missing` nuevo. Neto −2 +1. |
| `Symbol` | 4 (`extra` 2 + `missing` 2) | 3 (`missing` `.created_at`, `.updated_at`; `extra` `.note`) | −1 | Una de las dos claves `extra` del ack de write de 2026-08-01 ya no llega. |
| `Instrument` / `Segment` | 2 (`non_dict`) | 2 | 0 | S-1, idéntico. |
| `CalendarConfig` | 12 | 12 | 0 | S-2, idéntico campo por campo. |
| **Subtotal comparable** | **22** | **20** | **−2** | |
| TYP-02 (`HealthFeed`/`FeedIngestor`) | 0 (era `N/A`) | 4 | +4 | Nuevo-tipado en la Phase 31. |
| **Total en vivo** | | **24** | | |

**Los tres canales de pérdida silenciosa se descartaron positivamente, no por ausencia de
evidencia:**

- **P-1 (nivel de logger).** El tell es un conteo de `extra` en cero para un paquete cuyo
  piso es `extra`-dominante. market-data: **8 triples `extra` / 16 findings `extra`**. No es
  cero. El logger sube a `INFO` dentro del CM (verificado también en el canal de iol, donde
  se leyó `level == 20`).
- **P-2 (excepción del handler tragada).** `HANDLER_ERRORS=0` en los **cuatro** pases que
  corrieron. Un valor distinto de cero invalidaría el censo de esa corrida.
- **P-3 (allocator sin seedear).** Ver la reconciliación completa abajo.

**Reconciliación fid ↔ bloque (P-3), market-data, ambos pases:**

| Magnitud | Valor |
|---|---:|
| `max_existing_fid` antes de la corrida (= seed) | 66 |
| Rango de fids asignados | `F-67` … `F-197` |
| Asignaciones totales | 131 |
| Bloques `### F-` nuevos escritos | 77 |
| Gaps (asignados y no escritos) | 54 |

**El short-circuit por status no-`OPEN` —el hazard P-3 real— es estructuralmente
inalcanzable en esta corrida**: el fid mínimo asignado (67) es estrictamente mayor que el
fid máximo preexistente (66), así que ninguna asignación pudo chocar contra un finding
terminal. Los 54 gaps son por lo tanto `idempotent_by_title`, el dedupe content-addressed
intencional. Eso se **probó**, no se afirmó, con un experimento offline sobre un findings
file temporal: cinco `append_finding` con el mismo título consumen 5 fids y escriben
**1** bloque; y con el allocator seedeado por `max_existing_fid` el próximo fid siempre cae
por encima de todo fid terminal del archivo.

La propiedad queda además pineada como regresión en
`verification/test_finding_count_consistency.py`, cuyo arm **sin seedear** es el control
fail-first: demuestra que la pérdida existe, es medible, y es silenciosa.

### 2. `iol-client`: `DIVERGENCES=0` — **inspección real, no canal muerto**

Un cero no se acepta sin probar que el canal por el que tendría que haber llegado algo está
vivo. Experimento (sobre un findings dir temporal, sin tocar nada committeado):

```
logger level dentro del CM: 20        # NOTSET -> INFO, la subida es load-bearing
seen: 17 triples                      # Cotizacion: 1 extra + 16 missing
errors: []
```

Con `divergence_capture(("iol_client",))` instalado y un payload que declara una clave
fabricada, el walker de `iol_client` emite y el handler captura 17 triples distintos. El
canal funciona end to end para este paquete. Por lo tanto el `DIVERGENCES=0` de la corrida
en vivo es el resultado de mirar: en los 4 endpoints ejercitados
(`get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type`) el wire
real de IOL coincide con lo que `Cotizacion` declara. Los probes de paridad y de
`field_type_map` lo corroboran desde otro ángulo: `drift=0` sobre 4 endpoints, `no drift`
sobre 3.

### 3. `higyrus` y `matriz` — sin número, y eso es el resultado

Ninguno de los dos aporta un cero al censo. Un `SKIPPED` con causa registrada es un
resultado; un cero sería una afirmación de limpieza que ninguna medición respalda. Los pisos
`≥22` y `≥24` siguen **sin contrastar** y las rutas están nombradas en `## Re-scope`.

---

## Schema snapshot reconciliation

```
$ git status --porcelain .planning/verification/schemas/
(vacío)
```

**Cero delta a nivel de archivo.** Clasificación completa:

| Categoría | Archivos | Explicación |
|---|---:|---|
| Nuevos (rama write-once) | **0** | — |
| Modificados (drift absorbido) | **0** | — |
| Drift **detectado y reportado sin sobreescribir** | 22 findings | Rama de detección, no de escritura (D-25). |

**Las nueve escrituras write-once de matriz NO ocurrieron, y la razón es el SKIP.**
`_SCHEMA_FILES` de matriz declara 17 entradas y hay 8 archivos en disco; las nueve ausentes
(orders / positions / account-report) sólo se materializan en una corrida exitosa del driver,
y el driver abortó en el assert D-MATZ-33. **No es una omisión del harness: es una
consecuencia registrada del SKIP de matriz**, y se cierra con el mismo destino.

**Los 22 findings de `schema drift` de market-data**, por endpoint, escritos como clase
`SHAPE`, todos `OPEN`:

| Endpoint / snapshot | Bloques escritos |
|---|---:|
| `get_health_feed` | 4 |
| `get_calendar` | 4 |
| `get_calendar_config` | 4 |
| `get_market_data` | 2 |
| `get_latest` | 2 |
| `create_symbols_batch_{sync,async}_response` | 2 |
| `preview_calendar_config_{sync,async}_response` | 2 |
| `get_calendar_year_2099_{sync,async}` | 2 |

Ninguno de estos 22 sobreescribió su baseline: el `git status` de `schemas/` está vacío, que
es el contrato D-25 (detectar y reportar, nunca re-basear en automático). El drift es real —
el wire de `develop` cambió respecto de los baselines de 2026-07-31/08-01 — y es exactamente
la misma familia de cambio que las divergencias de decode de este censo describen campo por
campo.

**Defecto de higiene detectado, no absorbido:** `_write_or_check_schema` llama a
`append_finding` **sin** `idempotent_by_title=True`, así que un mismo drift escribe un bloque
nuevo por superficie y por pase — de ahí los `×4` de la tabla, con títulos byte-idénticos.
No es pérdida de censo (nada se descarta) pero infla el archivo de findings y hace que el
triage de 33-07 vea duplicados. **No se arregla acá** (la Task 2 prohíbe editar el driver).
**Destino: `HARN-DRIFT-33`.**

---

## Re-scope

Todo hallazgo confirmado o pendiente que el plan **33-07 no va a cerrar en este ciclo**,
con su destino nombrado. Ninguna celda dice `TBD`, `later` ni `a futuro`. La Phase 34 es
releases por paquete y **no** es un destino válido para trabajo de defectos.

| Paquete | Modelo | Field path | Especie | Destino | Rationale |
|---|---|---|---|---|---|
| `matriz-client` | `Instrument` | `.instrumentId` (+ `marketId`, `symbol` como `extra`) | `non_dict` + `extra` — **S-3** | `LIVE-MATZ-33` (ROADMAP § Backlog, v1.7+) | Sin medición en vivo: el driver aborta por la política remarkets-only (D-MATZ-33). Confirmar antes de tocar el modelo es un requisito escrito de `29-SIZING.md`. |
| `matriz-client` | `InstrumentDetail` | 7 claves no declaradas | `extra` — **S-4** | `LIVE-MATZ-33` | Idem. Informativo por política (lock 4), pero sin corroborar en vivo. |
| `matriz-client` | `MarketDataSnapshot` | `.LA`, `.SE`, `.OI`, `.CL` | `non_dict` — **S-5** | `LIVE-MATZ-33` (requiere ventana de sesión ARG) | Doblemente indecidible: sin corrida, y la ventana fue de mercado cerrado. Un `null` de mercado cerrado no distingue defecto de forma legítima (P-12). |
| `higyrus-client` | `Movimiento`, `PosicionValuada`, `Posicion` | 22 campos del piso ≥22 | `missing` | `LIVE-HIGY-33` (ROADMAP § Backlog, v1.7+) | El host del vendor no resuelve por DNS desde esta red. Credenciales presentes; es alcanzabilidad, no auth. |
| `market-data-client` | `HealthFeed` | `.symbols_never_delivered` | `extra` | `TYP-MD-EXTRA-33` (ROADMAP § Backlog, v1.7+) | `extra` es informativo por política (lock 3/4): crecimiento normal del vendor. Tiparlo es trabajo de superficie, no un fix de defecto. |
| `market-data-client` | `FeedIngestor` | `.ingestor.last_error_age_seconds`, `.ingestor.last_error_at`, `.ingestor.subscription` | `extra` | `TYP-MD-EXTRA-33` | Idem. Los tres son TYP-02: visibles porque `HealthFeed` se tipó en la Phase 31. |
| `market-data-client` | `Symbol` | `.note` | `extra` | `TYP-MD-EXTRA-33` | Idem. Clave del ack de write que el modelo no declara. |
| `market-data-client` | *(snapshots)* | 22 findings `schema drift` duplicados por superficie/pase | — | `HARN-DRIFT-33` (ROADMAP § Backlog, v1.7+) | `_write_or_check_schema` no pasa `idempotent_by_title=True`. Higiene del artefacto; no hay pérdida de censo. |

### Lo que 33-07 **sí** cierra en este ciclo

Seis triples confirmados en vivo, en dos familias, ordenados por consecuencia:

1. **S-1** — `Instrument` y `Segment` `non_dict` (2 triples). El más consecuente de los
   medidos: cada fila del catálogo decodifica a un modelo all-default.
2. **S-2** — `CalendarConfig` contra el sobre de preview (12 triples: 9 `missing` + 3
   `extra`). El sobre quiere su propio modelo.
3. `MarketDataSnapshot.entries` / `.market_data` / `.staleness_seconds` `missing` sobre la
   forma no-data de `/marketdata/latest` (3 triples) — candidatos a `Optional`.
4. `Symbol.created_at` / `.updated_at` `missing` en los acks de write (2 triples) —
   candidatos a `Optional`.

Total dirigido a 33-07: **19 triples** (2 + 12 + 3 + 2), todos de `market-data-client`, todos
`OPEN` en `.planning/verification/market-data-client-findings.md`. Los 5 triples restantes
del censo de 24 son los `extra` ruteados arriba.

### Criterio 1 de la fase: estado real

Los cinco drivers están **cableados** al mecanismo (130/130 probes decorados, probado por
`verification/test_probe_context_coverage.py`), pero sólo **3 de 5** pudieron **correr** contra
su API real en esta ventana. `higyrus-client` y `matriz-client` quedan sin corrida por
razones de entorno del operador —una de red, una de política de seguridad— y ninguna de las
dos es resoluble desde dentro de este plan. **Es un gate humano**: 33-07 debe surfacearlo en
lugar de dar el criterio 1 por cerrado.
