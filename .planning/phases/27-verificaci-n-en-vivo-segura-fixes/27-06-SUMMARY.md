---
phase: 27-verificaci-n-en-vivo-segura-fixes
plan: 06
subsystem: verification-harness
tags: [verification, live, armed-run, mutation, evidence, idempotency, residue, symbols, calendar]

# Dependency graph
requires:
  - phase: 27-verificaci-n-en-vivo-segura-fixes
    plan: 05
    provides: "el ciclo de calendar, los dos residue sweeps, la política de snapshots y el inventario de 16 identificadores de mutación"
  - phase: 27-verificaci-n-en-vivo-segura-fixes
    plan: 04
    provides: "_mutate_raw_*, _discover_row_id, los seis identificadores GSDPROBE/ y los ocho probes de symbols"
  - phase: 27-verificaci-n-en-vivo-segura-fixes
    plan: 03
    provides: "el doble gate, MARKET_DATA_VERIFY_MUTATING y el allocator de fids seedeado en 36"
  - phase: 27-verificaci-n-en-vivo-segura-fixes
    plan: 01
    provides: "el serializer que preserva bullets desconocidos — sin él las 26 findings nuevas habrían borrado la prosa de triage de F-01..F-36"
provides:
  - "EVIDENCIA MEDIDA: el id de fila del symbol vive bajo la clave `id`, tipo int, presente TANTO en el item de GET /symbols COMO en el body del POST /symbols"
  - "EVIDENCIA MEDIDA: las tres respuestas de mutación de symbols SÍ contienen algo con forma de symbol — A6 confirmada, el fix no-breaking de D-22 existe"
  - "EVIDENCIA MEDIDA: veredictos de idempotencia por CONTEO DE FILAS para los 8 endpoints de mutación"
  - "16 baselines write-once — el primer registro de shapes que la OpenAPI en vivo declara sólo como `object` bare"
  - "F-37..F-62 en el findings file, con la prosa de F-01..F-36 intacta"
  - "residuo probado CERO: 6 filas GSDPROBE/ todas active=false, 0 días en 2099"
affects: [27-07-close-cycle]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Evidencia antes que conclusión: cada veredicto se registra como lo que el server devolvió, y la decisión (flip de flag, cambio de modelo) queda explícitamente para 27-07"

key-files:
  created:
    - .planning/verification/schemas/market-data-client/create-symbol-sync-response.json
    - .planning/verification/schemas/market-data-client/create-symbol-async-response.json
    - .planning/verification/schemas/market-data-client/create-symbols-batch-sync-response.json
    - .planning/verification/schemas/market-data-client/create-symbols-batch-async-response.json
    - .planning/verification/schemas/market-data-client/update-symbol-sync-response.json
    - .planning/verification/schemas/market-data-client/update-symbol-async-response.json
    - .planning/verification/schemas/market-data-client/get-symbols-probe-prefix-sync.json
    - .planning/verification/schemas/market-data-client/get-symbols-probe-prefix-async.json
    - .planning/verification/schemas/market-data-client/preview-calendar-config-sync-response.json
    - .planning/verification/schemas/market-data-client/preview-calendar-config-async-response.json
    - .planning/verification/schemas/market-data-client/add-holidays-sync-response.json
    - .planning/verification/schemas/market-data-client/add-holidays-async-response.json
    - .planning/verification/schemas/market-data-client/get-calendar-year-2099-sync.json
    - .planning/verification/schemas/market-data-client/get-calendar-year-2099-async.json
    - .planning/verification/schemas/market-data-client/delete-holiday-sync-response.json
    - .planning/verification/schemas/market-data-client/delete-holiday-async-response.json
  modified:
    - .planning/verification/market-data-client-findings.md

decisions:
  - "El flag `idempotent=` NO se tocó en ningún builder: este plan mide, 27-07 decide (D-20)"
  - "`get-symbols.json` NO se re-baselineó en este run — las lecturas corren antes de las mutaciones, así que la baseline sigue `[]`. Derivará en el PRÓXIMO run; el re-baseline sigue siendo de 27-07"

metrics:
  duration: "~35 min"
  completed: 2026-08-01

status: complete
---

# Phase 27 Plan 06: Armed destructive run Summary

**El run existió.** El ciclo destructivo corrió una vez contra
`market-data-develop.bbsa.com.ar` bajo la autorización del operator, con `FAIL=0`, `SKIPPED=0`
y residuo cero. Las tres preguntas que sólo el server podía contestar están contestadas por
medición, no por prosa del spec.

## Tasks completed

| # | Task | Commit |
|---|------|--------|
| 1 | Pre-flight: re-fetch del contrato, claim check, credenciales, run desarmado, baseline limpia | (sin cambios en repo — read-only) |
| 2 | Autorización del operator | satisfecha por referencia a `deferred-items.md` |
| 3 | Run armado, captura de evidencia, verificación de residuo | `2b3a4cc` |

---

## Task 1 — Pre-flight

### Re-fetch del contrato en vivo (T-27-33)

`https://market-data-develop.bbsa.com.ar/api/openapi.json`, re-fetch 2026-08-01.

- **30.218 bytes** — **idéntico** al tamaño que RESEARCH registró el 2026-08-01 (línea 334).
- `sha256 = 6d48e3bb9fea49b3bfe5da6d8e5cdbdc2845469adb9778898c0963b25a653159`
- `openapi = "3.1.0"`, `info.version = "0.1.0"`

**Claim check, ítem por ítem:**

| # | Claim load-bearing | Resultado | Evidencia re-fetcheada |
|---|---|---|---|
| 1 | No existe `DELETE` bajo `/symbols` | **CONFIRMADO** | `/symbols ['GET','POST']`, `/symbols/batch ['POST']`, `/symbols/{symbol_id} ['PATCH']` |
| 2 | El path param de `PATCH /symbols/{symbol_id}` sigue tipado integer | **CONFIRMADO** | `symbol_id path {"type": "integer", "title": "Symbol Id"}` |
| 3 | Toda respuesta de mutación sigue siendo `object` bare sin schema | **CONFIRMADO** (los 8) | cada 2xx: `{"type":"object","additionalProperties":true,"title":"Response …"}` |
| 4a | `GET /symbols` sigue siendo array | **CONFIRMADO** | `{"type":"array","items":{"type":"object","additionalProperties":true}}` |
| 4b | `GET /calendar` sigue siendo object | **CONFIRMADO** | `{"type":"object","additionalProperties":true}` |
| 5 | El `year` de `GET /calendar` sigue aceptando 2099 | **CONFIRMADO** | `{"type":"integer","maximum":2100,"minimum":2000}` |
| 6 | El query param `prefix` de `GET /symbols` sigue existiendo | **CONFIRMADO** | `prefix query {"anyOf":[{"type":"string"},{"type":"null"}], "description":"Symbol prefix, e.g. DLR/"}` |
| 7 | `POST /calendar/holidays` sigue descrito como upsert idempotente por fecha | **CONFIRMADO** | `'Add or update calendar entries. Idempotent by date, so re-seeding is safe.'` |

**Ninguna claim cambió.** El contrato es el que los planes 27-01..27-05 asumieron.

### Credenciales y alcanzabilidad

```
curl -sS -o /dev/null -w '%{http_code}' https://market-data-develop.bbsa.com.ar/api/health
200
```

```
MARKET_DATA_CLIENT_ID present
MARKET_DATA_CLIENT_SECRET present
MARKET_DATA_AUDIENCE present
MARKET_DATA_AUTH0_TOKEN_URL present
MARKET_DATA_VERIFY_MUTATING = None
exit=0
```

Sólo nombre y presencia — **ningún valor ni longitud impresos** (T-27-34). El gate estaba en su
estado seguro por defecto (variable ausente) antes del run armado.

### Run desarmado

Exit **0**. Los 18 probes destructivos reportaron el skip a nivel probe y
`PROBE cycle_closure: PASS 34 CONFIRMED/FIXED con regresión` apareció.

```
SUMMARY: PASS=23 FAIL=0 SKIPPED=18 FINDING=2
```

Los dos sweeps ya reportaban `PASS sin residuo (reintento=False)` **antes** de armar, y
`PROBE symbols_sync: PASS symbols=0` — o sea la línea base limpia que 27-05 midió seguía
vigente al momento de armar.

El run desarmado reescribió el findings file (allocando F-37..F-41) y se **revirtió** con
`git checkout -- <ese único archivo>`, verificando el retorno al sha base, para que el corpus
commiteado fuera enteramente del run armado.

### Baseline pre-run medida

| Métrica | Valor |
|---|---|
| `.planning/verification/schemas/market-data-client/` | **9** archivos (los nueve de lectura) |
| findings file, bytes | 26.226 |
| findings file, sha256 | `5fadf738d059437b9030f92e6f2d87ac8f52bf40da4b3c12741fe5d8e8e22ef6` |
| `Classification:` / `Resolution:` / `Regression:` | **36 / 34 / 34** |
| bloques `### F-` | 36 (F-01..F-36) |
| `git status --porcelain` | vacío |

---

## Task 2 — Autorización del operator

**Concedida, registrada por referencia** en
`.planning/phases/27-verificaci-n-en-vivo-segura-fixes/deferred-items.md` § "Operator
authorization — armed destructive run (plan 27-06 task 2)", con fecha 2026-08-01.

Alcance autorizado, y **lo que efectivamente se escribió coincide exactamente**:

| Autorizado | Ejecutado |
|---|---|
| Crear y revertir a `active=false`: los 6 `GSDPROBE/P27-*` | los 6, todos revertidos — verificado |
| Crear y borrar: holidays `2099-12-29`, `2099-12-30` | ambos creados y borrados — verificado |
| **Nunca escribir** `PUT`/`DELETE /calendar/config` | **cero escrituras**; sólo el preview compute-only, con la config verificada idéntica antes/después |

**Nada fuera de esa lista se ejecutó.**

---

## Task 3 — Run armado

Comando, una sola vez, con el opt-in **sólo** en el shell invocante (nunca en un `.env`, nunca
exportado a un perfil):

```
MARKET_DATA_VERIFY_MUTATING=1 uv run --package market-data-client python main_market_data.py
```

### Línea `SUMMARY:` verbatim

```
SUMMARY: PASS=39 FAIL=0 SKIPPED=0 FINDING=4
```

Exit code **0**. `SKIPPED=0` es la prueba de que el gate armó: **ninguna** línea del transcript
contiene `SKIPPED (mutating, guard off)`, el string que en un run armado significaría cero
evidencia en vivo (T-27-37).

Contra la baseline desarmada (`PASS=23 FAIL=0 SKIPPED=18 FINDING=2`): los 18 skips se
convirtieron en ejecuciones reales, `PASS` sube 16 y `FINDING` sube 2 (las dos misparse de
`create_symbol`, una por superficie).

### Transcript completo, verbatim

```
PROBE health_sync: PASS health+feed ok
PROBE market_data_sync: PASS snapshots=100
PROBE latest_sync: PASS latest=1 batch=1
PROBE instruments_sync: PASS instruments=6
PROBE segments_sync: PASS segments=2
PROBE symbols_sync: PASS symbols=0
PROBE calendar_sync: PASS days=11 config_tz='America/Argentina/Buenos_Aires'
PROBE param_encoding_sync: PASS filtros falsy preservados
PROBE no_data_sync: FINDING F-38 (OPEN)
PROBE auth_fail_sync: PASS 401 -> MarketDataAuthError
PROBE mutation_gate_refusal_sync: PASS mutación rechazada sin opt-in (0 HTTP, 0 Auth0)
PROBE health_async: PASS health+feed ok
PROBE market_data_async: PASS snapshots=100
PROBE latest_async: PASS latest=1 batch=1
PROBE instruments_async: PASS instruments=6
PROBE segments_async: PASS segments=2
PROBE symbols_async: PASS symbols=0
PROBE calendar_async: PASS days=11 config_tz='America/Argentina/Buenos_Aires'
PROBE no_data_async: FINDING F-40 (OPEN)
PROBE mutation_gate_refusal_async: PASS mutación rechazada sin opt-in (0 HTTP, 0 Auth0)
PROBE create_symbol_async: FINDING F-41 (OPEN) refire_status=200
PROBE symbols_after_create_async: PASS 1 fila; id descubierto en clave 'id' (prefijo devolvió 1 filas)
PROBE create_symbols_batch_async: PASS 1 fila por identificador; public_rows=5 refire_status=200
PROBE update_symbol_async: PASS revertido; public_rows=5 refire_status=200
PROBE preview_calendar_config_async: PASS config sin cambios; doble-fire idéntico=False eco_warnings=0 ventana_estrecha_warnings=3
PROBE add_holidays_async: PASS 2099-12-30; public_keys=3 refire_status=200
PROBE calendar_after_holiday_async: PASS 1 fila(s) para 2099-12-30; F-49 (EXPECTED, dedupe by title)
PROBE delete_holiday_async: PASS 2099-12-30 borrado; second_status=404; F-50 (EXPECTED)
PROBE residue_sweep_async: PASS sin residuo (reintento=False)
PROBE create_symbol_sync: FINDING F-51 (OPEN) refire_status=200
PROBE symbols_after_create_sync: PASS 1 fila; id descubierto en clave 'id' (prefijo devolvió 4 filas)
PROBE create_symbols_batch_sync: PASS 1 fila por identificador; public_rows=5 refire_status=200
PROBE update_symbol_sync: PASS revertido; public_rows=5 refire_status=200
PROBE preview_calendar_config_sync: PASS config sin cambios; doble-fire idéntico=False eco_warnings=0 ventana_estrecha_warnings=3
PROBE add_holidays_sync: PASS 2099-12-29; public_keys=3 refire_status=200
PROBE calendar_after_holiday_sync: PASS 1 fila(s) para 2099-12-29; F-59 (EXPECTED, dedupe by title)
PROBE delete_holiday_sync: PASS 2099-12-29 borrado; second_status=404; F-60 (EXPECTED)
PROBE residue_sweep_sync: PASS sin residuo (reintento=False)
PROBE parity_sync_async: PASS segments sync==async (2)
PROBE health_feed_recheck_sync: PASS ingestor.last_error sigue vacío tras las mutaciones
PROBE snapshot_rebaseline_notice_sync: PASS F-61 (EXPECTED, dedupe by title)
PROBE expected_put_config_operator_gated: PASS F-62 (EXPECTED, dedupe by title)
PROBE cycle_closure: PASS 34 CONFIRMED/FIXED con regresión
SUMMARY: PASS=39 FAIL=0 SKIPPED=0 FINDING=4
```

Los 44 probes registrados en 27-04-SUMMARY y 27-05-SUMMARY aparecen todos, en el orden que
esos planes documentaron. `residue_sweep_sync`, `residue_sweep_async` y `cycle_closure`: **PASS**.

---

# EL REGISTRO DE EVIDENCIA MEDIDA

Esto es el entregable real del plan. Todo lo de abajo es lo que el server devolvió, no una
conclusión derivada del spec.

## 1. Dónde vive el `symbol_id` entero (D-10 / A1)

**La clave es `id`. El tipo es `int`. Aparece en las dos superficies de lectura Y en el body
de escritura.**

- Ambos probes de descubrimiento coinciden:
  `PASS 1 fila; id descubierto en clave 'id' (prefijo devolvió N filas)`, sync y async.
  `_discover_row_id` no tuvo que caer al fallback ni emitir la finding de key-names.
- El item real de `GET /symbols?prefix=GSDPROBE/`
  (`get-symbols-probe-prefix-sync.json` — la **primera fila poblada de symbol jamás
  observada** en este repo):

```json
"schema": [
  {
    "active": "bool",
    "created_at": "str",
    "id": "int",
    "market_id": "str",
    "received_at": "NoneType",
    "symbol": "str",
    "updated_at": "str"
  }
]
```

- Y el body de `POST /symbols` **también** trae `"id": "int"`, así que el ciclo no depende de
  releer el catálogo para conocer el id.

**Consecuencia para 27-07:** `Symbol` necesita un campo `id: int`, y el `symbol_id: str` del
cliente contradice tanto el spec (`integer`) como el wire (`int`). La evidencia soporta el
ensanchado a `int | str` que D-10 propone.

## 2. Shape real de los 8 bodies de mutación (D-11 / A6)

La OpenAPI declara los ocho como `object` bare con `additionalProperties: true`, así que
**ninguna de estas shapes era conocible offline**. Ahora las 16 están commiteadas (una por
superficie; sync y async resultaron **idénticas en shape** en los 8 casos).

| Endpoint | Top-level | ¿Contiene algo con forma de symbol/day? |
|---|---|---|
| `POST /symbols` | objeto plano | **SÍ** — es un symbol: `active, created, id, market_id, note, symbol` |
| `POST /symbols/batch` | envelope | **SÍ** — `items: [{active, created, id, market_id, symbol}]` + `created:int, note:str, reactivated:int, requested:int` |
| `PATCH /symbols/{symbol_id}` | objeto plano | **SÍ** — es un symbol: `active, id, market_id, note, symbol` |
| `POST /calendar/holidays` | envelope | **SÍ** — `days: [{close_time, closed, day, description, open_time}]` + `note:str, saved:int` |
| `DELETE /calendar/holidays/{day}` | objeto plano | no — `{day: str, deleted: bool}` (acuse de recibo) |
| `POST /calendar/config/preview` | objeto | no aplica — `{market_after:{…}, requires_confirmation:bool, valid:bool, warnings:[]}` |
| `PUT /calendar/config` | **no observado** | preview-only por D-06; AST-guarded, nunca escrito |
| `DELETE /calendar/config` | **no observado** | ídem |

**A6 CONFIRMADA, y esto es la respuesta que 27-07 más necesitaba:** las tres respuestas de
mutación de symbols **sí** contienen algo desenvolvible a `Symbol`. Las dos planas son un
symbol directo (envolver en lista de 1); la de batch trae `items[]`. **Por lo tanto el fix
no-breaking de D-22 existe** — `parse_symbols_response` puede devolver `list[Symbol]` real
preservando el tipo de retorno publicado, sin escalar la decisión de versión antes de Phase 28.

**El bug D-11, medido:**

> F-41 / F-51 — `**Actual:** body objeto JSON de 6 clave(s); parse_symbols_response devolvió
> 6 Symbol, 6 all-default`

Confirmado en vivo en ambas superficies: contra un objeto bare el parser de lectura itera las
**claves** y produce un `Symbol` all-default por clave. Se capturó, no se arregló (es de 27-07).

**Nota de seguridad:** los 16 snapshots son salida de `schema_of` — sólo nombres de tipo,
**cero valores**. Verificado por escaneo antes de commitear.

## 3. Idempotencia medida por CONTEO DE FILAS (D-19 / D-27 / DM-03)

El veredicto es el conteo leído de vuelta del server. Los status codes son contexto: en un
re-run el primer POST ya devuelve 200, así que el status **no** es el observable.

| Endpoint | Observable medido | Resultado | Flag declarado | Veredicto |
|---|---|---|---|---|
| `POST /symbols` | filas tras doble-fire | **1 fila**; `refire_status=200` | `idempotent=True` | **CONFIRMADO** — el server dedupea |
| `POST /symbols/batch` | filas por identificador | **1 fila por identificador**; `public_rows=5 refire_status=200` | `idempotent=True` | **CONFIRMADO** |
| `PATCH /symbols/{symbol_id}` | filas tras doble-fire | **1 fila**; `public_rows=5 refire_status=200` | `idempotent=True` | **CONFIRMADO** |
| `POST /calendar/holidays` | días en el envelope tras doble-fire | **1 fila** para 2099-12-29 y 1 para 2099-12-30 → **UPSERT por fecha** | `idempotent=False` | **DEMASIADO CONSERVADOR** (F-49/F-59) |
| `DELETE /calendar/holidays/{day}` | status del 2º fire | **404** en ambas superficies | `idempotent=True` | **DEMASIADO PERMISIVO en status** (F-50/F-60) |
| `POST /calendar/config/preview` | igualdad de los 2 bodies | **DISTINTOS** en ambas superficies | `idempotent=True` | **medición divergente** (F-48/F-58) |

**Los flags no se tocaron.** D-20 hace autoritativa la realidad medida y el flip lo decide
27-07 sobre esta tabla.

Notas que 27-07 debe adjudicar, marcadas como tales:

- **`POST /calendar/holidays`** — la prosa del spec en vivo (*"Add or update … Idempotent by
  date, so re-seeding is safe"*) queda **confirmada por medición**, no sólo leída. Phase 26
  declaró `idempotent=False`; el conteo dice que el server hace upsert. Este es el único caso
  donde spec y medición coinciden **y** el flag del cliente discrepa de ambos.
- **`DELETE /calendar/holidays/{day}`** — idempotente en **estado** (el día no vuelve), no en
  **status** (404 al segundo fire). Riesgo concreto registrado en F-50/F-60: con
  `idempotent=True`, un retry del `RetryTransport` convertiría ese 404 en `MarketDataAPIError`.
- **`POST /calendar/config/preview`** — dos previews de la **misma** ventana devolvieron bodies
  distintos, en ambas superficies. *Hipótesis no verificada, para que 27-07 la descarte o la
  confirme:* el body contiene campos que dependen del reloj (`market_after.local_time`,
  `market_after.next_transition`), lo que explicaría la diferencia sin implicar escritura. La
  **medición** es la diferencia; la causa **no** está medida y no debe darse por sentada.

## 4. Reconciliación de `Symbol` — SHAPE-diff contra la primera fila poblada

Seis findings SHAPE por superficie (F-42..F-47 async, F-52..F-57 sync):

| Dirección | Campo |
|---|---|
| **model-only** (existe en `Symbol`, no en el wire) | `marketId` |
| **wire-only** (existe en el wire, no en `Symbol`) | `created_at`, `id`, `market_id`, `received_at`, `updated_at` |

**Respuesta a la Open Question 2 de RESEARCH: sí, `Symbol.marketId` debe ser `market_id`.**
El wire usa snake_case como todo el resto de esta API. La evidencia es directa: `marketId` es
model-only y `market_id` es wire-only en el mismo diff.

## 5. `parse_latest_response` (D-14) — verificación, no re-fix

`PROBE latest_sync: PASS latest=1 batch=1` y `PROBE latest_async: PASS latest=1 batch=1`. El
unwrap de `items` ya shippeado sigue comportándose en el read sweep en vivo. **No se reabrió.**

## 6. Assumptions Log A1..A7

| # | Claim | Disposición | Evidencia |
|---|---|---|---|
| **A1** | El id entero viene en los items de `GET /symbols` bajo una clave tipo `id` | **CONFIRMADA** | clave `id`, tipo `int`, en el item **y** en el body del POST — el plan B ("guardar el id de la respuesta de creación") no hizo falta, pero también está disponible |
| **A2** | El `prefix` de `GET /symbols` hace match de prefijo real server-side | **CONFIRMADA** | `prefix=GSDPROBE/` devolvió 1 → 4 → 6 filas conforme el ciclo creaba; el sweep independiente devolvió las 6. Sin filtrado client-side |
| **A3** | `GET /calendar?year=2099` devuelve los días de ese año en `days[]` | **CONFIRMADA** | `PASS 1 fila(s) para 2099-12-29` y `… 2099-12-30`; baseline `get-calendar-year-2099-*.json` con `days[]` poblado |
| **A4** | Un símbolo sintético no rompe nada aguas abajo más allá de `last_error` | **CONFIRMADA (más fuerte de lo asumido)** | `health_feed_recheck_sync: PASS ingestor.last_error sigue vacío tras las mutaciones` — ni siquiera se pobló `last_error`. Sin reconnect-loop, sin impacto operativo |
| **A5** | Los 34 findings FIXED legacy pueden apuntar a los tests de reconciliación | **CONFIRMADA** | `cycle_closure: PASS 34 CONFIRMED/FIXED con regresión` |
| **A6** | El body de las mutaciones de symbols contiene algo con forma de symbol | **CONFIRMADA** | ver § 2 — plano en POST/PATCH, `items[]` en batch. **No hay que escalar la decisión de versión** |
| **A7** | `SYMBOL_REFRESH_SECONDS` es lo bastante largo como para que la ventana activa no dispare suscripción | **CONFIRMADA** | `last_error` vacío tras el ciclo completo; la ventana activa (segundos) no alcanzó a un refresh |

**Ninguna assumption fue refutada.**

---

## Residuo — barrido terminal

### Sweeps del propio driver (verbatim)

```
PROBE residue_sweep_async: PASS sin residuo (reintento=False)
PROBE residue_sweep_sync: PASS sin residuo (reintento=False)
```

`reintento=False` significa que no hubo nada que reintentar: los `finally` de cada probe ya
habían revertido todo.

### Sweep independiente, read-only, posterior al commit (verbatim)

```
=== TERMINAL RESIDUE SWEEP (independent, read-only) ===
GET /symbols?prefix=GSDPROBE/ -> 6 row(s)
raw helper available: False
GET /symbols?prefix=GSDPROBE/&active=true -> 0 row(s)  <-- must be 0
GET /symbols?prefix=GSDPROBE/&active=false -> 6 row(s)  <-- must be 6
   inactive row: GSDPROBE/P27-ASYNC
   inactive row: GSDPROBE/P27-ASYNC-B1
   inactive row: GSDPROBE/P27-ASYNC-B2
   inactive row: GSDPROBE/P27-SYNC
   inactive row: GSDPROBE/P27-SYNC-B1
   inactive row: GSDPROBE/P27-SYNC-B2
GET /calendar?year=2099 -> 0 day(s)  <-- must be 0
SWEEP RESULT: PASS
```

**Estado final de develop, medido y no supuesto:**

- **6** filas `GSDPROBE/`, exactamente las 6 autorizadas, **todas `active=false`**, **0 activas**.
  Permanentes por diseño (no existe `DELETE /symbols`), acotadas y no-crecientes porque los
  identificadores son estables en vez de por-run.
- **0** días en 2099 — los dos feriados creados fueron borrados dentro del ciclo.
- `market_hours` **sin tocar**: ambos probes de preview reportaron `config sin cambios`,
  comparando la config leída antes y después campo a campo. Cero `PUT`, cero `DELETE` sobre
  `/calendar/config`.

**Nada quedó activo ni sin borrar. No hay nada que escalar al orchestrator por residuo.**

---

## Higiene del findings file (T-27-35)

| Métrica | Pre-run | Post-run | Veredicto |
|---|---|---|---|
| `Classification:` | 36 | **36** | intacto |
| `Resolution:` | 34 | **34** | intacto |
| `Regression:` | 34 | **34** | intacto |
| bloques `### F-` | 36 | 62 | +26 |
| rango de fids nuevo | — | **F-37 .. F-62** | todos por encima de F-36 |

`git diff | grep '^-### F-'` → **vacío**: no se borró ningún bloque de finding. Las 109
deletions del diff son el reflow de re-serialización, no pérdida de prosa. **El fix del harness
de 27-01 aguantó** contra 26 escrituras nuevas.

### Findings Phase 27 registradas (F-37..F-62)

- **F-37, F-39** — schema drift en `get_market_data` (read sweep, pre-existente al armado)
- **F-38, F-40** — `market_data` vacío para prefix inexistente (OPEN)
- **F-41, F-51** — D-11: `create_symbol` parsea la escritura con el parser de lectura (OPEN)
- **F-42..F-47 / F-52..F-57** — SHAPE de `Symbol`: `marketId` model-only; `created_at`, `id`,
  `market_id`, `received_at`, `updated_at` wire-only (OPEN)
- **F-48, F-58** — D-19 preview: doble-fire devolvió bodies distintos (EXPECTED)
- **F-49, F-59** — D-19 holidays: dedupea por fecha, 1 fila tras doble-fire (EXPECTED)
- **F-50, F-60** — D-19 delete: segundo DELETE devolvió 404 (EXPECTED)
- **F-61** — política de snapshots y re-baseline deliberado de `get-symbols.json` (EXPECTED)
- **F-62** — `PUT`/`DELETE /calendar/config` operator-gated fuera del run (EXPECTED, D-06)

---

## Snapshots nuevos (9 → 25 archivos)

Los 16 identificadores del inventario de 27-05 aterrizaron, **ninguno faltante, ninguno extra**:

`create-symbol-{sync,async}-response`, `create-symbols-batch-{sync,async}-response`,
`update-symbol-{sync,async}-response`, `get-symbols-probe-prefix-{sync,async}`,
`preview-calendar-config-{sync,async}-response`, `add-holidays-{sync,async}-response`,
`get-calendar-year-2099-{sync,async}`, `delete-holiday-{sync,async}-response`.

**`get-symbols.json` NO cambió** y sigue siendo `"schema": []`. Motivo: el orden de probes de
27-04 pone todas las lecturas **antes** de toda mutación, así que `probe_symbols_sync` leyó un
catálogo todavía vacío (`PASS symbols=0`). La deriva que 27-05 anticipó ocurrirá en el
**próximo** run, cuando las 6 filas inactivas ya existan al momento de la lectura. El
re-baseline deliberado sigue siendo de **27-07**, y ahora con la ventaja de que
`get-symbols-probe-prefix-sync.json` ya documenta la shape real que tomará.

---

## Verification

- Run armado: exit **0**, `FAIL=0`, `SKIPPED=0`, `cycle_closure: PASS`, ambos sweeps `PASS`.
- `ruff check .` → all checks passed. `ruff format --check .` → 201 files already formatted.
- `packages/market-data-client/tests` + los 9 guards del driver y del findings harness →
  **411 passed** en 0.86s.
- Escaneo de credenciales sobre **todo** lo commiteado (diff del findings file + los 25 JSON):
  ninguno de los 4 valores de credencial aparece; 0 ocurrencias de `Bearer `, `eyJ`,
  `client_secret`, `access_token`, `Authorization`; la única URL presente es la de develop ya
  registrada. **RESULT: PASS**.
- `git diff --diff-filter=D HEAD~1 HEAD` → vacío: el commit no borró ningún archivo trackeado.

Por el presupuesto del executor no se corrió el sweep completo de `verification/` (~14 min,
dominado por un test que duerme de verdad). Los 19 failures + 19 errors pre-existentes por el
drift de firmas de matriz (Phase 15) y el fallo worktree-only de
`test_phase06_nyquist_gaps.py::test_snapshot_regen_is_idempotent` siguen registrados en
`deferred-items.md` y no son de este plan.

## Deviations from Plan

**1. [Rule 3 — blocker de entorno] El worktree no tenía el `.env` (gitignored), así que se copió desde el repo principal.**
- **Found during:** task 1, chequeo de credenciales — `.venv/bin/python` no existía y
  `packages/market-data-client/.env` tampoco, porque `git worktree` no materializa archivos
  ignorados. Sin eso el driver habría salido **SKIPPED** y el plan no habría producido evidencia.
- **Fix:** `cp` del `.env` del repo principal al mismo path relativo del worktree. Está cubierto
  por `.gitignore:47` (verificado con `git check-ignore -v`), así que es **incommiteable**; se
  confirmó que `git status --porcelain` siguió vacío tras la copia. El archivo se borra al
  cerrar el plan y el worktree se elimina después. Ninguna credencial entró en git, en un log
  ni en un artefacto.
- **Files:** ninguno trackeado.

**2. [Interpretación] El run desarmado de la task 1 se revirtió antes de armar.**
El plan pide correr el driver desarmado y luego dejar el árbol limpio para que el diff
post-run sea inequívoco. El run desarmado escribe el findings file (alocó F-37..F-41), así que
se revirtió con `git checkout --` sobre ese único archivo, verificando el retorno al sha base
`5fadf738…22ef6`. Sin eso, el corpus commiteado habría mezclado fids del smoke desarmado con
los del run armado, y el rango de Phase 27 no habría sido atribuible a una sola corrida.

**3. [Rule 2 — verificación faltante] Se agregó un sweep de residuo independiente además del del driver.**
Los sweeps del driver reportan *"sin residuo"*, que por diseño significa **cero símbolos
activos y cero días en 2099** — pero **no** afirma que las 6 filas existan y estén inactivas,
que es exactamente lo que la autorización del operator acota. Se corrió un script read-only
aparte (sólo GETs) que verifica las tres condiciones por separado: 6 filas totales, 0 activas,
6 inactivas por nombre, 0 días en 2099. Convierte "no vi residuo" en "medí el estado final
completo y coincide con lo autorizado".

Sin cambios de código fuente. Sin dependencias nuevas. Sin checkpoints Rule 4. `uv.lock` intacto.

## Threat model

Las siete dispositions `mitigate` del plan, ejecutadas:

- **T-27-31** (persistencia del opt-in): `MARKET_DATA_VERIFY_MUTATING=1` se usó como prefijo de
  **un solo comando**. Verificado ausente del entorno antes del run (`= None`) y no escrito en
  ningún `.env` ni perfil. Su ausencia sigue siendo el estado por defecto.
- **T-27-32** (escritura no autorizada): checkpoint humano satisfecho por la autorización
  registrada en `deferred-items.md`; lo escrito coincide **exactamente** con el alcance
  concedido, verificado ítem por ítem contra la lista.
- **T-27-33** (contrato stale): re-fetch completo, 7 claims re-verificadas una por una, todas
  confirmadas, mismo byte size que RESEARCH.
- **T-27-34** (information disclosure): salida por `safe_print`; snapshots por `schema_of`
  (nombres de tipo, cero valores); chequeo de credenciales con presencia y longitud solamente;
  escaneo automatizado de todo lo commiteado → PASS.
- **T-27-35** (pérdida silenciosa de findings): conteos de prosa comparados contra la baseline
  de la task 1 → 36/34/34 sin mover; fids nuevos todos ≥ F-37; cero headers borrados.
- **T-27-36** (estado huérfano): ambos sweeps PASS + sweep independiente PASS; residuo final
  medido y dentro de lo autorizado.
- **T-27-37** (éxito vacuo): `SKIPPED=0` y cero ocurrencias de `SKIPPED (mutating, guard off)`
  en el transcript armado. El run **no** fue vacuo.
- **T-27-SC**: ningún paquete instalado; `uv.lock` intacto.

Sin superficie de seguridad nueva. Sin **Threat Flags**.

## Known Stubs

Ninguno. Este plan no produce código; produce evidencia, y toda la evidencia está medida y
commiteada.

## Deferred / not mine

- **El flip de `idempotent=`** en `build_add_holidays_request` y, si 27-07 lo decide,
  en `build_delete_holiday_request` y `build_preview_calendar_config_request`. Este plan mide;
  D-20 hace autoritativa la medición; **27-07 decide**.
- **El fix de D-11** (`parse_symbols_response` contra bodies de escritura) y **el de D-10**
  (`Symbol.id`, `symbol_id: int | str`, `marketId` → `market_id`): la evidencia está completa y
  soporta un fix no-breaking; la implementación es de 27-07.
- **El re-baseline de `get-symbols.json`**: sigue `[]`; derivará en el próximo run.
- **La causa** de que el doble preview devuelva bodies distintos: medida como diferencia, no
  diagnosticada. 27-07 debe adjudicarla antes de tocar el flag.
- Los 19 failures + 19 errors pre-existentes de `verification/` (drift de matriz, Phase 15).

## Requirement

`LIVE-MUT-01` — **la evidencia en vivo existe**. Los criterios 1, 2 y 3 del ROADMAP tienen
respaldo real: las 8 mutaciones ejercitadas en ambas superficies detrás del gate, identificadores
dedicados con ciclo de cleanup completo, residuo cero medido, configuración real de mercado
intacta, e idempotencia **medida** por conteo de filas en vez de asumida por prosa. El
requirement se marca completo en **27-07**, cuando los fixes que esta evidencia habilita estén
aplicados y re-verificados en vivo.

## Self-Check: PASSED

- `.planning/verification/market-data-client-findings.md` — FOUND (62 bloques `### F-`,
  prosa 36/34/34 intacta)
- Los 16 snapshots nuevos bajo `.planning/verification/schemas/market-data-client/` — los 16
  FOUND; el directorio pasó de 9 a 25 archivos
- Commit `2b3a4cc` — presente en `git log`
- `STATE.md` / `ROADMAP.md` — **no modificados** (orchestrator-owned)
- Residuo en develop — verificado por sweep independiente: 6 filas `GSDPROBE/` todas
  `active=false`, 0 días en 2099
