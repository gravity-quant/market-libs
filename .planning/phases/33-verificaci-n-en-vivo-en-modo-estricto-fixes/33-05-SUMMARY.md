---
phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
plan: 05
subsystem: testing
tags: [live-verification, census, ast-gate, preflight, auth, findings, schema-snapshots, strict-decode]

requires:
  - phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
    provides: "`verification/divergences.py` + la convención de título lockeada `surface-in-title-write-new` (33-01)"
  - phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
    provides: "los 130 probes decorados y la línea SUMMARY unificada `DIVERGENCES=N HANDLER_ERRORS=N` en los cinco drivers (33-02, 33-03, 33-04)"
  - phase: 29-decoder-observable
    provides: "el piso de sizing ratificado `>=96`, la tabla de corpus de 43 archivos y las cinco estructurales S-1..S-5"
  - phase: 23-market-data-live
    provides: "el doble gate de mutaciones y el contrato D-03 read-sweep-sigue-con-gate-cerrado"
provides:
  - "`verification/test_probe_context_coverage.py` — el único lugar del repo donde los cinco drivers se cuentan juntos (130 probes, piso por driver, match sufijo->superficie)"
  - "`verification/test_finding_count_consistency.py` — la clase de regresión P-3 con control fail-first sin seedear"
  - "`scripts/preflight_33.py` — prueba de autenticación en vivo por paquete con semántica SKIP-not-raise y cero fuga de credenciales"
  - "`33-CENSUS.md` — el volumen real contra el piso ratificado, con la corrección de unidad registros-vs-triples y el re-scope nombrado"
  - "cuatro destinos nombrados en `ROADMAP.md` § Backlog: `LIVE-MATZ-33`, `LIVE-HIGY-33`, `TYP-MD-EXTRA-33`, `HARN-DRIFT-33`"
  - "77 findings nuevos en `market-data-client-findings.md` (48 SHAPE de censo + 22 de schema drift + 7 de probe)"
affects: [33-06, 33-07]

actuals:
  tokens: 12400
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "gate AST con piso numérico por driver Y piso del subconjunto estrictamente chequeable, para que ninguna de las dos aserciones pueda volverse vacua por separado"
    - "exención escrita como allowlist por nombre completo, nunca como patrón: un probe nuevo no puede entrar a la exención sin editar el gate"
    - "pre-flight que mide autenticación (no presencia de variables) e imprime sólo `type(exc).__name__`"
    - "reconciliación fid<->bloque por argumento estructural (`min(asignado) > max(preexistente)`) más clasificación enumerada de los gaps, en vez de una igualdad que el dedupe intencional vuelve falsa"

key-files:
  created:
    - verification/test_probe_context_coverage.py
    - verification/test_finding_count_consistency.py
    - scripts/preflight_33.py
    - .planning/phases/33-verificaci-n-en-vivo-en-modo-estricto-fixes/33-CENSUS.md
  modified:
    - .planning/verification/market-data-client-findings.md
    - .planning/ROADMAP.md

key-decisions:
  - "El piso `>=96` de 29-SIZING.md es una SUMA DE REGISTROS sobre 43 archivos de corpus, NO un conteo de triples distintos: el equivalente comparable con `handler.seen` es 58 (higyrus 22, matriz 14, market-data 22). 33-RESEARCH Pattern 6 afirmaba que eran la misma unidad y no lo son. El censo contrasta contra ambas columnas y lo declara en cada fila"
  - "La aserción literal del plan «fids emitidos == bloques nuevos» es falsa por construcción: el handler pide un fid por CADA record y `idempotent_by_title=True` descarta el write de un título repetido. La forma decidible es «ningún fid asignado pudo chocar con un finding terminal», que se prueba estructuralmente (min asignado 67 > max preexistente 66) y se completa clasificando los 54 gaps como dedupe intencional, probado offline"
  - "El pase 1 de market-data corre con `MARKET_DATA_VERIFY_MUTATING=1` y el pase 2 sin él: el plan dice que el hazard P-11 es disparar el ciclo destructivo DOS veces en una sesión, lo que implica exactamente una. Sin el gate abierto el piso >=50 no es contrastable (carry-forward 3 de 33-04) y S-2 reporta 0 de sus 12 triples"
  - "matriz NO se corrió rodeando el assert D-MATZ-33 ni reapuntando `PRIMARY_BASE_URL` a remarkets: las credenciales del `.env` fueron emitidas para el host demo y mandarlas a otro vendor sería una fuga disfrazada de fix de config. Se registra `SKIPPED — base URL fuera de política`, nunca cero"
  - "higyrus se registra `SKIPPED — vendor inalcanzable` con la causa medida (DNS `gaierror`, credenciales presentes), no `AUTH FAIL` a secas: la distinción decide el destino de reparación"
  - "El `DIVERGENCES=0` de iol se investigó antes de aceptarlo: el canal se probó vivo con 17 triples sobre un payload sintético. Un cero sin esa prueba habría sido indistinguible de un canal muerto (P-02)"

patterns-established:
  - "Un cero de censo nunca se acepta sin una prueba positiva de que el canal por el que tendría que haber llegado algo está vivo"
  - "Una aserción del plan que resulta falsa por construcción se reemplaza por la propiedad decidible más cercana Y se documenta por qué, en vez de relajarse hasta pasar"
  - "Un SKIP con causa medida es un resultado; un cero es una afirmación de limpieza que necesita respaldo"

requirements-completed: []

coverage:
  - id: D28
    description: "Los 130 probes de los cinco drivers cargan el decorador con superficie válida y coincidente con el sufijo del nombre, probado por un gate AST con piso numérico por driver (criterio 1)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_probe_context_coverage.py::test_every_probe_carries_probe_context (5 casos parametrizados)"
        status: pass
      - kind: unit
        ref: "verification/test_probe_context_coverage.py::test_total_probe_coverage_is_one_hundred_and_thirty"
        status: pass
      - kind: other
        ref: "falsificación: quitar un decorador de main_iol.py -> 2 rojos; declarar surface='async' en un probe _sync -> 1 rojo. Ambos experimentos revertidos"
        status: pass
    human_judgment: false
  - id: D29
    description: "La clase de regresión P-3 está pineada con un control fail-first: el arm sin seedear escribe menos bloques que fids emitidos (P-3)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_finding_count_consistency.py::test_emitted_fid_count_matches_new_finding_blocks"
        status: pass
      - kind: unit
        ref: "verification/test_finding_count_consistency.py::test_unseeded_allocator_silently_loses_findings"
        status: pass
      - kind: other
        ref: "falsificación: usar el allocator sin seedear en el arm seedeado -> 'assert 3 == 4'. Revertido"
        status: pass
    human_judgment: false
  - id: D30
    description: "Cada paquete en scope tiene un resultado de autenticación en vivo registrado, sin fuga de credencial ni de cuerpo de excepción (D-13, T-33-24, T-33-28)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "uv run python scripts/preflight_33.py -> 5 líneas de estado, exit 1 (higyrus AUTH FAIL ConnectError)"
        status: pass
      - kind: other
        ref: "scan mecánico de los 20 valores de los cuatro .env contra la salida del pre-flight: 0 coincidencias"
        status: pass
    human_judgment: false
  - id: D31
    description: "Los pases observable y estricto completaron para los tres paquetes que pudieron correr, con HANDLER_ERRORS=0 en los cuatro pases y el pase estricto de market-data provablemente no-mutante (P-05, P-11, T-33-27)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "6 líneas SUMMARY verbatim registradas; HANDLER_ERRORS=0 en las cuatro corridas con handler"
        status: pass
      - kind: other
        ref: "pase 2 de market-data invocado con `MARKET_LIBS_STRICT_DECODE=1` y SIN `MARKET_DATA_VERIFY_MUTATING`: 19 probes reportan SKIPPED (mutating, guard off), los 2 de refusal reportan 0 HTTP / 0 Auth0"
        status: pass
      - kind: other
        ref: "git status --porcelain packages/ vacío después de las seis corridas"
        status: pass
    human_judgment: false
  - id: D32
    description: "El censo reporta el volumen en vivo por paquete contra el piso ratificado, dispone las cinco estructurales y rutea todo diferimiento a un destino nombrado que existe en ROADMAP (criterio 5)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "las siete secciones presentes; grep S-1..S-5 = 15 ocurrencias; ninguna celda Destination dice TBD/later/a futuro"
        status: pass
      - kind: other
        ref: "los cuatro destinos (LIVE-MATZ-33, LIVE-HIGY-33, TYP-MD-EXTRA-33, HARN-DRIFT-33) resuelven a entradas de ROADMAP § Backlog agregadas en el mismo commit"
        status: pass
    human_judgment: true
    rationale: "Decidir que un delta de -2 contra el sizing es cambio real de wire y no pérdida de censo, y elegir qué se difiere y adónde, es un juicio de scope contra evidencia, no un chequeo mecánico."
  - id: D33
    description: "Los snapshots de schema quedan reconciliados: cada entrada del delta clasificada, incluidas las nueve de matriz declaradas-y-ausentes (criterio 4)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "git status --porcelain .planning/verification/schemas/ vacío; 22 findings de drift clasificados por endpoint; las 9 write-once de matriz explicadas como consecuencia registrada del SKIP"
        status: pass
    human_judgment: true
    rationale: "Que un delta de archivo vacío cuente como 'reconciliado' —y no como 'no se miró'— depende de entender el contrato D-25 detectar-sin-re-basear; es un juicio, no un grep."

duration: 16min
completed: 2026-08-27
status: complete
---

# Phase 33 Plan 05: gates pre-run, corridas en vivo de dos pases y `33-CENSUS.md` Summary

**El criterio 1 pasa de "cableado" a "medido" en tres de los cinco paquetes, y la diferencia
entre un censo limpio y uno que pierde registros en silencio queda decidida con evidencia en
vez de con supuestos: los tres canales de pérdida se descartaron positivamente, el cero de iol
se probó como inspección real y no como canal muerto, y los dos paquetes que no pudieron
correr quedan registrados como `SKIPPED` con su causa medida — nunca como cero. En el camino
apareció el hallazgo de método que cambia cómo se lee todo el contraste: el piso `≥96` es una
suma de registros sobre 43 archivos de corpus, no un conteo de triples distintos.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-08-27T00:45:51Z
- **Completed:** 2026-08-27T01:01:42Z
- **Tasks:** 3 de 3
- **Files created/modified:** 6 (4 nuevos, 2 modificados)

## Salida del pre-flight (verbatim)

```
$ uv run python scripts/preflight_33.py
higyrus-client: AUTH FAIL ConnectError
iol-client: AUTH OK
matriz-client: AUTH OK
market-data-client: AUTH OK
ambito-financiero-client: n/a (sin auth por diseño)
EXIT=1
```

`scripts/preflight_33.py` quedó **committeado** (`8ebc5de`), así que su texto completo no se
reproduce acá: la reproducibilidad la da el archivo. Contrato en una línea: una línea de
estado por paquete, sólo `type(exc).__name__`, nunca `str(exc)` / `repr(exc)` / una
credencial, nunca levanta hacia afuera, exit distinto de cero si alguno falló.

**Verificación de no-fuga (mecánica, no por lectura):** se parsearon los 20 valores de los
cuatro `.env` de paquete y se buscó cada uno como substring en la salida. **0 coincidencias.**

### Diagnóstico de higyrus (acotado, sin imprimir host ni credenciales)

```
HIGYRUS_BASE_URL set: True
HIGYRUS_USER set: True
HIGYRUS_PASSWORD set: True
scheme: https | host is private-ip-literal: False
DNS resolution FAILED: gaierror
```

Es **alcanzabilidad de red**, no rechazo de credenciales. El host es plausiblemente
interno/VPN desde esta red. Por D-13 se registra `SKIPPED — vendor inalcanzable`, se rutea al
camino de operador-corre-y-pega de la Phase 23, y **no se reintentó en loop ni se intentó
rodear la falla**.

## Los seis pases: transcripciones verbatim

### ámbito — pase 1 (observable) y pase 2 (`MARKET_LIBS_STRICT_DECODE=1`)

Las dos corridas devolvieron transcripción **idéntica**:

```
PROBE happy_sync: PASS precio=1530.0
PROBE happy_async: PASS precio=1530.0
PROBE parity_sync_async: PASS sync==async=1530.0
PROBE parse_decimal: PASS venta=1530.0
PROBE no_data: PASS NoDataError para 2026-10-25
PROBE schema_snapshot: PASS schema sin drift
PROBE antibot: SKIPPED (opt-in via VERIFY_ANTIBOT=1)
SUMMARY: PASS=6 FAIL=0 SKIPPED=1 FINDING=0 DIVERGENCES=0 HANDLER_ERRORS=0
```

**El cero de D-12 queda afirmado positivamente**, no inferido de una ausencia: conteo de
probes distinto de cero (6 PASS) **y** `len(handler.seen) == 0` **y**
`len(handler.errors) == 0`. Un driver que no hubiera corrido daría los mismos ceros en las
dos últimas señales y un cero también en la primera.

### iol — pase 1 (observable) y pase 2 (estricto)

También idénticas entre sí:

```
PROBE login_sync: PASS _token cached, _refresh_token=<cached>
PROBE login_async: PASS _token cached, _refresh_token=<cached>
PROBE get_quote_sync: PASS ultimoPrecio=7070.0
PROBE get_quote_async: PASS ultimoPrecio=7070.0
PROBE get_historical_quotes_sync: PASS len=1379
PROBE get_historical_quotes_async: PASS len=1379
PROBE get_instruments_sync: PASS type=list
PROBE get_instruments_async: PASS type=list
PROBE get_instruments_by_type_sync: PASS sample=acciones len=99; 6 types OK
PROBE get_instruments_by_type_async: PASS sample=acciones len=99
PROBE parity_sync_async: PASS 4 endpoints, drift=0, skipped=0
PROBE field_type_map: PASS 3 endpoints checked (get_quote, get_historical_quotes, get_instruments_by_type), no drift
PROBE schema_snapshot: PASS written=[] matched=['get_quote', 'get_historical_quotes', 'get_instruments', 'get_instruments_by_type'] skipped=[]
PROBE refresh_token: PASS refresh path verified — token rotated, _refresh_token=rotated
PROBE auth_401: SKIPPED (opt-in via VERIFY_IOL_BAD_CREDS=1)
SUMMARY: PASS=14 FAIL=0 SKIPPED=1 FINDING=0 DIVERGENCES=0 HANDLER_ERRORS=0
```

### market-data — pase 1 (observable, gate de mutaciones ABIERTO)

Invocación verbatim: `MARKET_DATA_VERIFY_MUTATING=1 uv run --package market-data-client python main_market_data.py`

```
SUMMARY: PASS=39 FAIL=0 SKIPPED=0 FINDING=4 DIVERGENCES=24 HANDLER_ERRORS=0
```

Líneas salientes de la transcripción:

```
PROBE calendar_sync: PASS days=11 config_tz='America/Argentina/Buenos_Aires'
PROBE create_symbol_sync: FINDING F-138 (OPEN)
PROBE create_symbols_batch_sync: PASS 1 fila por identificador; public_rows=0 refire_status=200
PROBE update_symbol_sync: PASS revertido; public_rows=1 refire_status=200
PROBE preview_calendar_config_sync: PASS config sin cambios; doble-fire idéntico=False difieren=['market_after.local_time'] eco_warnings=1 ventana_estrecha_warnings=3
PROBE add_holidays_sync: PASS 2099-12-29; wire_keys=3 saved=1 refire_status=200
PROBE delete_holiday_sync: PASS 2099-12-29 borrado; second_status=404; F-168 (EXPECTED)
PROBE residue_sweep_sync: PASS sin residuo (reintento=False)
PROBE cycle_closure: PASS 50 CONFIRMED/FIXED con regresión
```

**SKIPPED=0**: los 16 probes destructivos ejercitaron su superficie tipada, que es
precisamente lo que hace contrastable el piso `≥50` y lo que hizo visibles los 12 triples de
S-2. Los dos sweeps de residuo cerraron con `sin residuo (reintento=False)`.

### market-data — pase 2 (estricto, gate de mutaciones CERRADO)

**Invocación verbatim** (`MARKET_DATA_VERIFY_MUTATING` **ausente**, T-33-27 / P-05 / P-11):

```
MARKET_LIBS_STRICT_DECODE=1 uv run --package market-data-client python main_market_data.py
```

```
PROBE market_data_sync:  FINDING SHAPE [sync]  MarketDataDecodeError model=MarketDataSnapshot path=.staleness_seconds declared=float observed=NoneType
PROBE latest_sync:       FINDING SHAPE [sync]  MarketDataDecodeError model=MarketDataSnapshot path=.entries declared=list observed=NoneType
PROBE instruments_sync:  FINDING SHAPE [sync]  MarketDataDecodeError model=Instrument path= declared=Instrument observed=str
PROBE segments_sync:     FINDING SHAPE [sync]  MarketDataDecodeError model=Segment path= declared=Segment observed=str
PROBE market_data_async: FINDING SHAPE [async] MarketDataDecodeError model=MarketDataSnapshot path=.staleness_seconds declared=float observed=NoneType
PROBE latest_async:      FINDING SHAPE [async] MarketDataDecodeError model=MarketDataSnapshot path=.entries declared=list observed=NoneType
PROBE instruments_async: FINDING SHAPE [async] MarketDataDecodeError model=Instrument path= declared=Instrument observed=str
PROBE segments_async:    FINDING SHAPE [async] MarketDataDecodeError model=Segment path= declared=Segment observed=str
PROBE create_symbol_sync: SKIPPED (mutating, guard off)
PROBE parity_sync_async: SKIPPED (un segments probe falló antes)
SUMMARY: PASS=14 FAIL=0 SKIPPED=19 FINDING=10 DIVERGENCES=8 HANDLER_ERRORS=0
```

**El raise fira, y el bajo-conteo es la evidencia de que fira:** 8 triples contra los 24 del
pase observable. El modo estricto se detiene en la **primera** divergencia estricta-fatal por
respuesta, exactamente el motivo por el cual el censo se cuenta del pase 1 y no de éste.
Los 19 SKIPPED son los 16 destructivos más los 3 que dependen de ellos.

### higyrus y matriz — sin pases

- **higyrus:** el pre-flight lo bloqueó (arriba).
- **matriz:** el pre-flight dio `AUTH OK` —las credenciales autentican— pero el driver aborta
  antes del primer probe:

  ```
  ABORT: PRIMARY_BASE_URL='https://api.demo.matrizoms.com.ar' is not a remarkets sandbox URL
         — Phase 5 verification is remarkets-only by safety policy
  ```

  Es el assert de hostname **D-MATZ-33** (`main_matriz.py:2550`), sin override, exit 1. Es la
  misma política que la prohibición P-05 protege: matriz tiene superficie de entrada de
  órdenes y el gate remarkets-only es el mecanismo que impide que un sweep toque una venue
  real. No se rodeó, y tampoco se reapuntó `PRIMARY_BASE_URL` al sandbox de remarkets: las
  credenciales del `.env` fueron emitidas para el host demo y mandarlas a otro vendor sería
  una fuga de credenciales disfrazada de fix de configuración.

## Conteos por paquete

| Paquete | Triples distintos | Findings SHAPE | `extra` (triples) | Handler errors | Bloques `### F-` nuevos |
|---|---:|---:|---:|---:|---:|
| `ambito-financiero-client` | 0 | 0 | 0 | 0 | 0 |
| `higyrus-client` | SKIPPED | — | — | — | 0 |
| `iol-client` | 0 | 0 | 0 | 0 | 0 |
| `market-data-client` | **24** | 48 censo + 22 drift | **8** | **0** | **77** |
| `matriz-client` | SKIPPED | — | — | — | 0 |

Los 24 triples de market-data, por modelo:

| Modelo | `missing` | `extra` | `non_dict` |
|---|---:|---:|---:|
| `CalendarConfig` (S-2) | 9 | 3 | — |
| `MarketDataSnapshot` | 3 | — | — |
| `Symbol` | 2 | 1 | — |
| `FeedIngestor` (TYP-02) | — | 3 | — |
| `HealthFeed` (TYP-02) | — | 1 | — |
| `Instrument` (S-1) | — | — | 1 |
| `Segment` (S-1) | — | — | 1 |
| **Total** | **14** | **8** | **2** |

## ¿Corrió el pase 1 de matriz dentro de una sesión de trading de ARG?

**No, y por partida doble.** (1) matriz no corrió en absoluto. (2) La ventana entera de
ejecución fue **ARG 21:45–21:57 de un miércoles**, con el mercado **cerrado**; aunque el
assert D-MATZ-33 no hubiera existido, la captura habría sido de mercado cerrado. **S-5 queda
`COULD-NOT-DECIDE`** y su destino (`LIVE-MATZ-33`) lleva el requisito de ventana horaria
escrito. Un `null` de mercado cerrado no se distingue de un error de modelado (P-12), y
marcarlo resuelto desde esta captura habría sido exactamente el falso limpio que P-02 prohíbe.

## Reconciliación P-3 (el número que decide si el censo es real)

| Magnitud (market-data, ambos pases) | Valor |
|---|---:|
| `max_existing_fid` antes de la corrida (= seed) | 66 |
| Rango de fids asignados | `F-67` … `F-197` |
| Asignaciones totales | 131 |
| Bloques `### F-` nuevos escritos | 77 |
| Gaps (asignados y no escritos) | 54 |

**La igualdad literal que el plan pide —«fids emitidos == bloques nuevos»— es falsa por
construcción**, y descubrirlo es un resultado, no un obstáculo. El `DivergenceHandler` pide un
fid por **cada record** y llama a `append_finding(..., idempotent_by_title=True)`; un record
que se repite (el walker emite por respuesta y `/marketdata` devuelve 100 snapshots) consume
un fid y no escribe un bloque. Eso es el dedupe content-addressed **intencional**, no el
hazard P-3.

La forma decidible de la propiedad, que sí se aseveró:

1. **El short-circuit por status no-`OPEN` es estructuralmente inalcanzable en esta corrida.**
   El fid mínimo asignado (67) es estrictamente mayor que el fid máximo preexistente (66), así
   que ninguna asignación pudo chocar contra un finding terminal. Ése es el hazard P-3 y no
   pudo ocurrir.
2. **Los 54 gaps son dedupe por título, probado y no afirmado.** Experimento offline sobre un
   findings file temporal: cinco `append_finding` con el mismo título consumen 5 fids y
   escriben **1** bloque; y con el allocator seedeado por `max_existing_fid` el próximo fid
   siempre cae por encima de todo fid terminal del archivo.
3. **La propiedad queda pineada como regresión** en
   `verification/test_finding_count_consistency.py`, cuyo arm sin seedear demuestra que la
   pérdida existe, es medible y es silenciosa.

**`HANDLER_ERRORS=0` en los cuatro pases con handler** (P-2), y **`extra` de market-data = 8
triples / 16 findings**, distinto de cero (el tell P-1). El tell P-1 de matriz no pudo
medirse.

## Delta de snapshots de schema, clasificado

```
$ git status --porcelain .planning/verification/schemas/
(vacío)
```

| Categoría | Archivos | Explicación |
|---|---:|---|
| Nuevos (rama write-once) | **0** | Las **nueve** entradas de `_SCHEMA_FILES` de matriz declaradas y ausentes (orders / positions / account-report) sólo se materializan en una corrida exitosa. matriz abortó → **consecuencia registrada del SKIP**, no omisión del harness. |
| Modificados (drift absorbido) | **0** | Contrato D-25: detectar y reportar, nunca re-basear en automático. |
| Drift detectado y reportado | **22 findings** | 8 snapshots distintos: `get_health_feed` ×4, `get_calendar` ×4, `get_calendar_config` ×4, y ×2 `get_market_data`, `get_latest`, `create_symbols_batch_*_response`, `preview_calendar_config_*_response`, `get_calendar_year_2099_*`. |

Los `×4` revelan un defecto de higiene: `_write_or_check_schema` llama a `append_finding`
**sin** `idempotent_by_title=True`, así que un mismo drift escribe un bloque por superficie y
por pase, con títulos byte-idénticos. No hay pérdida de censo. **No se arregló acá** (la
Task 2 prohíbe editar el driver). Destino: `HARN-DRIFT-33`.

## Shortlist para 33-07, ordenada por consecuencia

**19 triples confirmados, todos de `market-data-client`, todos `OPEN`:**

1. **S-3 no está en la lista, y esa ausencia es el titular.** `29-SIZING.md` lo llama *"the
   highest-consequence finding in the set"* y **no se pudo medir**: matriz no corrió. Va a
   `LIVE-MATZ-33` sin disposición, no a 33-07.
2. **S-1 — `Instrument` / `Segment` `non_dict` (2 triples).** El más consecuente de los que
   **sí** se midieron: los parsers no desenvuelven el sobre, así que cada fila del catálogo
   decodifica a un modelo all-default. Confirmado por dos vías independientes (24 triples del
   pase observable, y el raise del pase estricto en las cuatro superficies). El caveat que
   `29-SIZING.md` dejó abierto —"puede que el servidor haya introducido el sobre después"—
   queda cerrado: el wire de hoy manda el sobre y el parser de hoy no lo desenvuelve.
3. **S-2 — `CalendarConfig` contra el sobre de preview (12 triples).** Confirmado **campo por
   campo** contra la predicción de `29-SIZING.md`: exactamente los 9 `missing` y los 3 `extra`
   nombrados. Sólo visible con el gate de mutaciones abierto. El sobre quiere su propio modelo.
4. **`MarketDataSnapshot.entries` / `.market_data` / `.staleness_seconds` `missing` (3
   triples)** sobre la forma no-data de `/marketdata/latest` — candidatos a `Optional`.
5. **`Symbol.created_at` / `.updated_at` `missing` (2 triples)** en los acks de write —
   candidatos a `Optional`.

Los 5 triples restantes del censo de 24 son `extra` y van a `TYP-MD-EXTRA-33` (informativos
por política: locks 3 y 4 de la Phase 29).

## Task Commits

1. **Task 1: gates pre-run + pre-flight** — `56128e7` (test, los dos gates) → `8ebc5de` (feat, el pre-flight)
2. **Task 2: corridas en vivo de dos pases** — `fea5a8e` (docs, los 77 findings nuevos)
3. **Task 3: `33-CENSUS.md` + destinos de re-scope** — `d1328b5` (docs, censo + ROADMAP § Backlog)

## Files Created/Modified

- `verification/test_probe_context_coverage.py` *(nuevo, ~230 líneas)* — gate AST sobre los
  cinco drivers: piso por driver (7/19/15/43/46 = 130), piso del subconjunto con sufijo (89),
  superficie en `{sync, async, both}`, y match sufijo→superficie con allowlist explícito para
  los probes de paridad.
- `verification/test_finding_count_consistency.py` *(nuevo, ~185 líneas)* — la clase P-3 con
  su control fail-first sin seedear.
- `scripts/preflight_33.py` *(nuevo, ~120 líneas)* — el pre-flight de autenticación.
- `.planning/phases/33-.../33-CENSUS.md` *(nuevo)* — las siete secciones del criterio 5.
- `.planning/verification/market-data-client-findings.md` — 77 bloques nuevos (`F-67`…`F-197`).
- `.planning/ROADMAP.md` — cuatro entradas nuevas en § Backlog → *Deferred to v1.7+*.

## Decisions Made

Además de las del frontmatter, en ejecución:

1. **La exención de la regla sufijo→superficie es un allowlist por nombre completo, no un
   patrón.** `probe_parity_sync_async` termina en `_async` y declara `surface="sync"` porque
   compara las dos superficies desde adentro. Escribirlo como `if name.endswith("_sync_async")`
   habría dejado la puerta abierta a que un probe nuevo entre a la exención sin que nadie lo
   note; el allowlist obliga a editar el gate.
2. **El gate lleva dos pisos, no uno.** El piso de probes por driver impide que pase con cero
   probes; el piso del subconjunto con sufijo impide que la aserción de superficie —la parte
   con dientes— se vuelva vacua si alguien borra los sufijos. Uno solo dejaba un agujero.
3. **El pre-flight entra a market-data por `_ensure_token()`.** El paquete no expone `login()`
   y el grant de client-credentials de Auth0 vive ahí. Un chequeo que no dispare el round trip
   real habría sido justamente el verde que no inspecciona nada.
4. **El cero de iol se investigó antes de aceptarlo.** Ver Deviations #3.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] La aserción «fids emitidos == bloques nuevos» del plan es falsa por construcción**

- **Found during:** Task 2, al reconciliar el pase 1 de market-data
- **Issue:** El `<action>` pide *"Assert per package that the emitted-fid count equals the
  new-block count — a mismatch is the P-3 failure mode"*. Pero el `DivergenceHandler` pide un
  fid por **cada record** y pasa `idempotent_by_title=True`; un record repetido (el walker
  emite por respuesta y `/marketdata` devuelve 100 snapshots) consume un fid y no escribe un
  bloque. Medido: 131 asignaciones, 77 bloques, 54 gaps. Aplicar la aserción literalmente
  habría reportado una falla P-3 masiva donde sólo hay dedupe intencional — un falso positivo
  que habría bloqueado el censo entero.
- **Fix:** Se reemplazó por la propiedad decidible más cercana, que **sí** cubre el hazard
  real: (a) el fid mínimo asignado (67) > el fid máximo preexistente (66), así que el
  short-circuit por status no-`OPEN` —el hazard P-3— es estructuralmente inalcanzable; (b) los
  54 gaps se clasificaron como dedupe por título con un experimento offline (mismo título ×5 →
  5 fids, 1 bloque). Las dos quedan escritas en `33-CENSUS.md` § Under-floor investigation.
- **Files modified:** ninguno (el defecto estaba en la aserción del plan)
- **Verification:** experimento offline sobre findings dir temporal; `git status --porcelain
  .planning/verification/` vacío después
- **Committed in:** `fea5a8e` (registrado en el mensaje de commit) + `d1328b5` (censo)

---

**2. [Rule 1 - Bug] `33-RESEARCH.md` Pattern 6 afirma que `handler.seen` y el piso `≥96` son la misma unidad, y no lo son**

- **Found during:** Task 3, al armar la tabla por paquete
- **Issue:** La columna `Count` de la tabla de corpus de `29-SIZING.md` es *"the number of
  unique divergence records emitted by the shipped walker for that file"* — única **dentro del
  archivo**, sumada **a través de** 43 archivos. `handler.seen` es un set de triples distintos
  a través de la **corrida entera**. El mismo `(model, field_path, kind)` presente en dos
  archivos de corpus suma dos veces al piso y una sola vez a `seen`. Contrastar 24 contra 50
  habría reportado un "por debajo del piso" fabricado por la unidad y habría disparado una
  investigación de pérdida de censo donde no hay ninguna — el falso negativo de P-02, en su
  dirección inversa.
- **Fix:** Se derivó, fila por fila de la tabla de corpus, el equivalente en triples distintos:
  higyrus 22 (sin solapamiento), matriz 14 (filas 38/39 y 40/41 comparten triples),
  market-data 22 (filas 20-25 comparten `Symbol`, 30/31 comparten `CalendarConfig`), total
  **58**. `33-CENSUS.md` contrasta contra **ambas** columnas y lo declara en cada fila.
  Resultado real: market-data 24 en vivo ≥ 22 equivalente, y el delta de −2 neto de TYP-02
  queda explicado campo por campo por cambio real de wire/modelo.
- **Files modified:** `33-CENSUS.md` (nueva subsección en `## Method`)
- **Verification:** la derivación cita las filas 4-6, 14-16, 20-25, 30-31 y 38-42 de
  `29-SIZING.md` por número
- **Committed in:** `d1328b5`

---

**3. [Rule 2 - Missing critical] Un `DIVERGENCES=0` no se puede aceptar sin probar que el canal está vivo**

- **Found during:** Task 2, tras el pase 1 de iol
- **Issue:** iol devolvió `DIVERGENCES=0` en los dos pases. El plan sólo obliga a investigar un
  resultado **por debajo del piso**, y iol no tiene piso — así que el cero pasaba sin
  inspección. Pero un cero producido por un canal muerto (P-1: el logger nunca subió de nivel)
  es indistinguible a ojo de un cero producido por un modelo correcto, y reportarlo como
  "iol limpio" habría sido exactamente el verde que no inspecciona nada que P-02 prohíbe.
- **Fix:** Experimento de no-vacuidad sobre un findings dir temporal: con
  `divergence_capture(("iol_client",))` instalado se verificó que el logger pasa de `NOTSET` a
  `INFO` (nivel 20) y que un payload con una clave fabricada produce **17 triples** capturados
  con `handler.errors == []`. El canal está vivo end to end para iol, así que el cero en vivo
  es resultado de mirar. Registrado en `33-CENSUS.md` § Under-floor investigation punto 2.
- **Files modified:** `33-CENSUS.md`
- **Verification:** `git status --porcelain .planning/verification/` vacío después del
  experimento (escribió sobre `tmp`)
- **Committed in:** `d1328b5`

---

**4. [Rule 3 - Blocking] `matriz` autentica pero el driver aborta por política de seguridad — no es un `AUTH FAIL` y no se puede rodear**

- **Found during:** Task 2
- **Issue:** El plan rutea a `SKIPPED` sólo los paquetes que imprimen `AUTH FAIL`. matriz
  imprimió `AUTH OK` y aun así no puede correr: `main_matriz.py:2550` aborta con exit 1 porque
  `PRIMARY_BASE_URL` apunta a un host demo y la política de la Phase 5 restringe la
  verificación a remarkets (D-MATZ-33, sin override). No hay categoría en el plan para esto, y
  registrarlo como cero habría sido la afirmación de limpieza que P-03 prohíbe.
- **Fix:** Se creó la categoría `SKIPPED — base URL fuera de política` en el censo, con la
  causa citada verbatim. **No se rodeó el assert** (la prohibición P-05 existe precisamente
  para esta superficie: matriz tiene entrada de órdenes) **y no se reapuntó `PRIMARY_BASE_URL`
  al sandbox de remarkets** — las credenciales del `.env` fueron emitidas para el host demo y
  mandarlas a otro vendor sería una fuga de credenciales disfrazada de fix de configuración.
  Destino nombrado: `LIVE-MATZ-33`.
- **Files modified:** `33-CENSUS.md`, `.planning/ROADMAP.md`
- **Verification:** `uv run --package matriz-client python main_matriz.py` → exit 1, cero
  probes ejecutados; `.planning/verification/matriz-client-findings.md` sin cambios (10 bloques
  antes y después)
- **Committed in:** `d1328b5`

---

**Total deviations:** 4 auto-fixed (2× Rule 1, 1× Rule 2, 1× Rule 3)
**Impact on plan:** Ninguno sobre el scope, y dos de las cuatro son hallazgos de método que
cambian cómo se lee el censo. La #1 y la #2 evitan dos falsos positivos que habrían bloqueado
o distorsionado el contraste contra el piso; la #3 cierra un agujero que el plan dejaba
abierto por construcción; la #4 crea la categoría que faltaba en vez de forzar el resultado a
una que miente. Cero scope creep: no se tocó ningún fuente bajo `packages/`, ningún driver,
ninguna copia de `_decode.py`, ni se reparó ninguna de las 19 fallas ni ninguno de los 43
errores de mypy pre-existentes de `verification/`.

## Authentication Gates

- **`higyrus-client`** — el pre-flight midió `AUTH FAIL ConnectError`; el diagnóstico acotado
  lo clasificó como DNS `gaierror` con las tres credenciales presentes. Flujo normal de D-13,
  no una falla del plan: el paquete se registra `SKIPPED` y se rutea al camino de operador de
  la Phase 23. **No se reintentó en loop.**
- **`matriz-client`** — autenticó (`AUTH OK`). El bloqueo posterior es de política de
  seguridad del driver, no de auth; ver Deviations #4.
- **`iol-client`, `market-data-client`** — `AUTH OK`, ambos corrieron sus dos pases.
- **`ambito-financiero-client`** — `n/a` por diseño (scraping público, sin auth).

## Issues Encountered

- **Sólo 3 de los 5 paquetes pudieron correr.** El criterio 1 de la fase pide los cinco
  drivers contra sus APIs reales. Los cinco están **cableados** (130/130 probes decorados,
  probado por el gate AST), pero `higyrus-client` y `matriz-client` no pudieron **correr** por
  razones de entorno del operador — una de red, una de política de seguridad — y ninguna es
  resoluble desde dentro de este plan. **Es un gate humano** y `33-CENSUS.md` lo dice por
  escrito: 33-07 debe surfacearlo en lugar de dar el criterio 1 por cerrado.
- **El pase 1 de matriz no pudo correr dentro de una sesión de trading de ARG.** La ventana de
  ejecución fue ARG 21:45–21:57 de un miércoles. Aunque el assert D-MATZ-33 no hubiera
  existido, la captura habría sido de mercado cerrado y S-5 seguiría indecidible (P-12).
- **`.planning/config.json` quedó modificado en el working tree** (`_auto_chain_active`) por el
  paso de init del workflow, no por este plan. No se commiteó: mismo criterio que 33-04.

## Carry-forwards

1. **El criterio 1 NO está cerrado.** 3 de 5 paquetes medidos. `LIVE-HIGY-33` y `LIVE-MATZ-33`
   son los destinos, pero mientras estén abiertos el criterio queda parcial. 33-07 tiene que
   tratarlo como un gate humano, no como un detalle.
2. **S-3 sigue sin disposición y es el hallazgo de mayor consecuencia del set.** No se difirió
   por elección de scope: no se pudo medir. Cualquier trabajo sobre `matriz_client.Instrument`
   antes de medirlo violaría la regla escrita de `29-SIZING.md` (confirmar en vivo antes de
   tocar el modelo).
3. **El piso `≥96` hay que leerlo como suma de registros.** El equivalente en triples es 58.
   `33-LITERALS.md` (plan 33-06) y el triage de 33-07 tienen que usar la columna correcta o
   repetirán el error de unidad.
4. **El pase con el gate de mutaciones abierto es el único que ejercita `Symbol`,
   `CalendarConfig`, `AddHolidaysResult` y `DeleteHolidayResult`.** Un re-run de verificación
   de 33-07 con el gate cerrado va a reportar 8 triples y no 24; no es una regresión.
5. **`HARN-DRIFT-33` infla el archivo de findings de market-data**, que ya tiene 143 bloques.
   El triage de 33-07 va a ver 22 bloques de drift para 8 snapshots distintos.
6. **`33-BASELINE.md` sigue siendo el árbitro del rojo de `verification/`.** Este plan no lo
   movió: los dos archivos nuevos suman 8 casos verdes y no tocan ninguno de los 19 rojos.

## Known Stubs

Ninguno. Los tres artefactos de código están cableados a fuentes reales: el gate AST parsea los
cinco drivers reales del repo (no una lista mock), el gate de consistencia ejercita el
`append_finding` real sobre `tmp_path`, y el pre-flight dispara el round trip de
autenticación real de cada vendor. `33-CENSUS.md` no lleva ningún número derivado ni estimado:
cada celda sale de una transcripción de esta sesión o de una fila citada de `29-SIZING.md`.
Las celdas `SKIPPED` no son placeholders pendientes de completar — son el resultado, con su
causa medida y su destino nombrado.

## TDD Gate Compliance

| Gate | Commit | Evidencia |
|---|---|---|
| RED (Task 1) | — | No-vacuidad demostrada por **falsificación**, no por un RED sintético: los dos gates se escriben contra drivers que 33-02/33-03/33-04 ya dejaron cableados, así que pasan al escribirse. Tres experimentos, todos revertidos: quitar un decorador de `main_iol.py` → 2 rojos; declarar `surface="async"` en un probe `_sync` → 1 rojo; usar el allocator sin seedear en el arm seedeado → `assert 3 == 4`. |
| RED (interno) | `56128e7` | `test_unseeded_allocator_silently_loses_findings` **es** un RED permanente embebido en la suite: falla si el mecanismo de pérdida deja de existir. |
| GREEN | `56128e7` → `8ebc5de` | 8 passed (5 parametrizados + 1 total + 2 de consistencia); pre-flight con 5 líneas de estado y 0 fugas. |

Sin fase REFACTOR: no hizo falta.

## Verification Evidence

| Gate | Resultado |
|---|---|
| `uv run pytest verification/test_probe_context_coverage.py verification/test_finding_count_consistency.py -q` | **8 passed** (5 parametrizados + 1 total + 2 de consistencia) |
| Falsificación A — decorador removido de `main_iol.py` | 2 FAILED (caso `main_iol.py` + total) |
| Falsificación B — `surface="async"` sobre `probe_login_sync` | 1 FAILED con `assert not [('probe_login_sync', 'async', 'sync')]` |
| Falsificación C — arm seedeado con allocator sin seedear | 1 FAILED con `assert 3 == 4` |
| `grep -v '^#' verification/test_probe_context_coverage.py \| grep -c 130` | 5 (≥1 requerido) |
| `uv run python scripts/preflight_33.py` | 5 líneas de estado, exit 1 (higyrus) |
| Scan de fuga: 20 valores de `.env` contra la salida del pre-flight | **0 coincidencias** |
| `git status --porcelain .planning/verification/` tras correr los dos gates | vacío |
| `git status --porcelain packages/` tras las seis corridas | **vacío** |
| `git status --porcelain .planning/verification/schemas/` | **vacío** (delta cero; 22 drifts reportados sin re-basear, D-25) |
| `HANDLER_ERRORS` en los cuatro pases con handler | **0, 0, 0, 0** |
| `extra` de market-data (tell P-1) | 8 triples / 16 findings — **distinto de cero** |
| Reconciliación P-3 | seed 66; asignaciones `F-67`…`F-197` (131); bloques nuevos 77; gaps 54, todos dedupe por título |
| `min` fid asignado > `max` fid preexistente | 67 > 66 → short-circuit por status **inalcanzable** |
| No-vacuidad del canal de iol | logger `NOTSET`→`INFO` (20); 17 triples sobre payload sintético; `errors == []` |
| Triples distintos de market-data ≡ `DIVERGENCES` del pase 1 | 24 ≡ 24 (derivado de los títulos escritos, no del stdout) |
| Las 7 secciones de `33-CENSUS.md` | todas presentes |
| `grep -c 'S-1\|S-2\|S-3\|S-4\|S-5' 33-CENSUS.md` | 15 (≥5 requerido) |
| Celdas `TBD` / `later` / `a futuro` en el re-scope | **0** |
| Los 4 destinos resuelven en `ROADMAP.md` § Backlog | `LIVE-MATZ-33`, `LIVE-HIGY-33`, `TYP-MD-EXTRA-33`, `HARN-DRIFT-33` ✓ |
| Scan de valor de wire en `33-CENSUS.md` (cuentas / CUIT / tokens) | **0 coincidencias** |
| `uv run ruff check . && uv run ruff format --check .` | limpio, 248 archivos formateados |
| `uv run mypy verification` — errores en los dos archivos nuevos | **0** |
| `uv run mypy scripts/preflight_33.py` | Success |
| `uv run mypy` | Success: no issues found in 75 source files |
| `uv run python tools/check_decode_intactness.py` | exit 0 |

## Self-Check: PASSED

- Los 4 archivos declarados en `key-files.created` existen en disco.
- Los 4 hashes de commit declarados (`56128e7`, `8ebc5de`, `fea5a8e`, `d1328b5`) existen en
  `git log`.
- Las seis líneas SUMMARY están copiadas **verbatim** del stdout de esta sesión, no
  parafraseadas.
- La invocación del pase estricto de market-data está transcripta literalmente, con
  `MARKET_DATA_VERIFY_MUTATING` ausente.
- La tabla de 24 triples está derivada de los títulos que el handler escribió en el findings
  file, y coincide con el `DIVERGENCES=24` que el driver imprimió — dos caminos independientes
  al mismo número.
- **`LIVE-TYP-01` queda deliberadamente en `Pending`.** Los siete planes de la Phase 33 cargan
  ese ID; cerrarlo en el plan 5 de 7 sería una completitud falsa, y con 2 de 5 paquetes sin
  medir sería además una completitud demostrablemente falsa. Mismo precedente que 33-01
  (deviation #4), 33-03 y 33-04. Queda para 33-07.
