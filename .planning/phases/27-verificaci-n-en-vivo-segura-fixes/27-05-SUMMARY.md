---
phase: 27-verificaci-n-en-vivo-segura-fixes
plan: 05
subsystem: verification-harness
tags: [verification, mutation, calendar, holidays, idempotency, ast-guard, residue, driver, live]

# Dependency graph
requires:
  - phase: 27-verificaci-n-en-vivo-segura-fixes
    plan: 04
    provides: "_mutate_raw_sync/_async, _emit_cleanup_finding, _skipped_when_gated, _gate_open, _discover_row_id, _prefixed_rows y los identificadores GSDPROBE/"
  - phase: 27-verificaci-n-en-vivo-segura-fixes
    plan: 03
    provides: "el doble gate, MARKET_DATA_VERIFY_MUTATING, el allocator de fids seedeado y probe_expected_put_config_operator_gated"
  - phase: 27-verificaci-n-en-vivo-segura-fixes
    plan: 02
    provides: "el unwrap del envelope days[] en parse_calendar_response — sin él la confirmación del holiday no podría existir"
provides:
  - "probe_preview_calendar_config_{sync,async} — la única cobertura live de config, con el 'Writes nothing' VERIFICADO por comparación antes/después en vez de creído (T-27-26)"
  - "el ciclo create -> verify -> revert COMPLETO de holidays en ambas superficies, con días disjuntos 2099-12-29 / 2099-12-30"
  - "_mutate_status_sync/_async — despacho con gate que devuelve el status observado aunque el server responda error, sin confundir nunca un refusal del gate con un status"
  - "veredictos D-19 medidos y registrados EN AMBAS DIRECCIONES como EXPECTED + dedupe by title, para POST /calendar/holidays, DELETE /calendar/holidays/{day} y POST /calendar/config/preview"
  - "probe_residue_sweep_{sync,async} — la red debajo de los finally: reconoce los identificadores dedicados, reintenta una vez y nombra lo que sobrevive"
  - "probe_health_feed_recheck_sync — nuestra propia contaminación del ingestor clasificada EXPECTED, nunca SHAPE"
  - "probe_snapshot_rebaseline_notice_sync — la política D-17/D-26 escrita en el findings file"
  - "dos AST guards: la superficie de config que persiste es inalcanzable (D-06) y ningún identificador de snapshot de mutación puede derivar un baseline de lectura (T-27-29)"
affects: [27-06-armed-run, 27-07-close-cycle]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Verificar el no-op en vez de creerlo: el 'Writes nothing' del preview se prueba leyendo la config antes y después y comparando; la diferencia, si la hubiera, es un finding OPEN"
    - "Medición-como-finding: un veredicto de idempotencia no es un defecto en ninguna de sus dos ramas, así que se registra con status EXPECTED + idempotent_by_title en lugar de OPEN — evidencia durable sin inflar el conteo de divergencias"
    - "Status observado a través del mapeo de errores: _mutate_status_* captura sólo MarketDataAPIError (la única que lleva status_code) para que un 404 legítimo sea un DATO y no un fallo, mientras el refusal del gate sigue propagando"
    - "Cleanup tolerante al camino feliz: el reintento defensivo del DELETE trata el 404 como el estado deseado, así que el finding de cleanup señala fallos reales en vez de ruido en cada corrida"
    - "Sweep que reconoce pero no invade: reporta cualquier residuo en el año dedicado y borra exclusivamente las filas que este driver creó"

key-files:
  created:
    - verification/test_main_market_data_no_config_write.py
    - verification/test_main_market_data_snapshot_identifiers.py
  modified:
    - main_market_data.py

status: complete
---

# Phase 27 Plan 05: Calendar cycle, residue sweep y política de snapshots Summary

La mitad de calendar del ciclo destructivo más las tres redes terminales: config
**preview-only** con el *"Writes nothing"* verificado en vez de asumido, el único ciclo
`create -> verify -> revert` completo de la fase (holidays), el sweep de residuos, la
reclasificación de nuestra propia contaminación del ingestor y la política de snapshots.
**Nada de este plan corrió como mutación contra develop: el gate estuvo cerrado en las dos
corridas y los 18 probes destructivos reportaron skip a nivel probe.**

## Tasks completed

| # | Task | Commit |
|---|------|--------|
| 1 | Probes de preview-only + AST guard D-06 contra la superficie de config que persiste | `9242243` |
| 2 | Ciclo holidays create -> verify -> delete en ambas superficies | `6451aa0` |
| 3 | Sweep terminal de residuos, recheck de `/health/feed`, política de snapshots + guard T-27-29 | `37aee0c` |

## What shipped

### Config: preview-only, y el no-op probado en vez de creído (D-06 / T-27-26)

`delete_calendar_config` **resetea a los defaults del servidor**; no restaura el valor
previo. Se leyó `client.py:620-632` y `_core.build_delete_calendar_config_request` para
confirmarlo antes de aceptar la premisa, porque de ahí sale toda la decisión: un DELETE **no
puede** funcionar como cleanup de un PUT, y como `market_hours` es compartida por todo
consumidor de develop, un PUT real la dejaría alterada sin ruta de vuelta. De ahí que la
cobertura live sea únicamente `POST /calendar/config/preview`.

Pero el plan no se conforma con no escribir: verifica que el endpoint *tampoco* escriba.
`probe_preview_calendar_config_sync` / `_async` leen `get_calendar_config()` **antes**,
disparan el preview cuatro veces (una por el método público —criterio 1 del ROADMAP y lo
que ejercita el gate in-package—, dos con la misma ventana por el helper con gate para el
doble-fire D-19, y una con una ventana de 5 minutos para observar cómo se reporta un
preview que dispara el confirm-gate del servidor) y **re-leen** la config. La igualdad
campo a campo es la prueba en vivo del *"Writes nothing"*; una diferencia es un
`ERROR-MAP` OPEN que registra **nombres** de campo, nunca valores (T-27-30).

El `MarketHoursIn` del eco se construye desde la config vigente, así que aunque el servidor
persistiera —justamente lo que el probe verifica que no pasa— el valor escrito sería el que
ya estaba. `updated_by` es `"gsd-verification-harness"`, un literal: **ningún campo del
preview se deriva del entorno**, porque ese body se snapshotea.

Se snapshotea **sólo el body del eco**, no el de la ventana estrecha: ésta trae `warnings`
poblados y el tipo de esa lista derivaría el baseline en cuanto el servidor tocara el texto.

**`verification/test_main_market_data_no_config_write.py`** hace la decisión estructural en
vez de convencional. Tres tests: (1) ningún *call site* invoca `set_calendar_config` /
`delete_calendar_config` ni sus builders; (2) esos nombres no aparecen **siquiera como
atributo o referencia**, así que tampoco se pueden alcanzar indirectamente
(`fn = client.set_calendar_config` seguido de `fn(...)` evadiría un chequeo de call sites);
(3) el guard es no-vacuo porque exige que la superficie de *preview* **sí** esté invocada —
tanto el método público como su builder—, de modo que un rename lo deja RED en vez de
ciego. Trabaja sobre el AST y no sobre strings, así que un docstring que menciona el
endpoint no es un falso positivo.

### Holidays: el único ciclo revert-completo de la fase (D-07/D-08/D-19/D-27)

```
_HOLIDAY_YEAR   = 2099
_HOLIDAY_SYNC   = "2099-12-29"     _HOLIDAY_ASYNC = "2099-12-30"
_PROBE_HOLIDAYS = (_HOLIDAY_SYNC, _HOLIDAY_ASYNC)
```

El año 2099 es load-bearing y está documentado como tal en el código: `GET /calendar` sólo
acepta `year` en 2000..2100, así que 2099 es a la vez **legible de vuelta** —condición sin la
cual el paso de confirmación no existiría— y lo bastante lejano como para no colisionar
jamás con un feriado real. Días **disjuntos** por superficie, por la misma razón que los
símbolos: el observable de idempotencia es el conteo de filas.

**`probe_add_holidays_*`** dispara el método público y luego un re-fire idéntico por el
helper con gate. `closed=True` con **ambos horarios en `None`** es deliberado: reproduce
exactamente la shape del `days[0]` commiteado en `get-calendar.json`, que es precisamente lo
que impide que este ciclo derive esa baseline (D-26). Un día repetido **no** se trata como
error — el spec lo documenta como *"Add **or update**"*, así que el 200 del re-fire es lo
esperado y un 422 sería la sorpresa (Pitfall 7).

**`probe_calendar_after_holiday_*`** lee `get_calendar(year=2099)`, que sólo devuelve filas
pobladas gracias al unwrap del envelope `days[]` que shippeó el plan 27-02. Además del
conteo, compara el resultado **parseado** contra el crudo: si el día está en el wire pero no
en `list[CalendarDay]`, eso es una regresión de ese fix y se emite como `ERROR-MAP` OPEN.
El SHAPE-diff de `CalendarDay` corre contra un item real creado por nosotros — es la primera
validación en vivo del set de campos reconciliado en 27-02.

**`probe_delete_holiday_*`** dispara el DELETE público y luego uno idéntico por
`_mutate_status_*` (ver abajo), porque **el status del segundo es el observable**: `200` =
idempotente de punta a punta; `404` = idempotente en estado pero **no** en status, y bajo el
`idempotent=True` actual de `build_delete_holiday_request` un retry del `RetryTransport`
convertiría ese 404 en `MarketDataAPIError`. Luego re-lee el calendario y afirma la
ausencia.

#### `_mutate_status_sync` / `_async` — el status como dato, no como fallo

`_request` levanta `MarketDataAPIError` ante cualquier status de error, así que un 404
legítimo del segundo DELETE sería indistinguible de un fallo de transporte. Los helpers
nuevos capturan **sólo** `MarketDataAPIError` —la única que lleva `status_code`— y devuelven
`(status, body)`. `MarketDataMutationNotAllowedError` **no** es subclase suya, así que un
refusal del gate sigue propagando y jamás se confunde con un status observado. Siguen
pasando por `_mutate_raw_*`, de modo que el gate se evalúa antes que cualquier HTTP.

#### El `finally` que no genera ruido (D-08)

El reintento defensivo del DELETE trata el **404 como el estado deseado** y no emite
finding: el día ya no está, que es exactamente lo que se buscaba. Cualquier otro error —y
cualquier excepción no-API— sí va por `_emit_cleanup_finding`. Sin esa distinción, el camino
feliz habría emitido un finding de cleanup en **cada** corrida armada, que es la forma más
rápida de volver inservible un canal de alerta. Los `finally` siguen libres de `_emit_shape`
y `_write_schema_snapshot` (Pitfall 5) y conservan su `try/except` propio, así que los tres
tests del guard de cleanup los cubren.

### Idempotencia: medida, registrada en ambas direcciones, no corregida

Tres veredictos D-19 nuevos, todos emitidos **cualquiera sea el resultado** con
`status="EXPECTED"` e `idempotent_by_title=True`:

| Endpoint | Observable | Rama A | Rama B |
|---|---|---|---|
| `POST /calendar/holidays` | conteo de días en el envelope | 1 fila ⇒ upsert por fecha ⇒ `idempotent=False` es conservador de más | ≥2 ⇒ apendea ⇒ el flag es correcto y la prosa del spec no describe el comportamiento real |
| `DELETE /calendar/holidays/{day}` | status del segundo fire | `200` ⇒ idempotente punta a punta | `404` ⇒ idempotente en estado, no en status |
| `POST /calendar/config/preview` | igualdad de los dos bodies | idénticos | distintos |

Ninguna de las dos ramas de ninguna fila es un defecto, y por eso ninguna sale como OPEN:
son la evidencia de revalidación de DM-03 que el criterio 3 exige. **El flag
`idempotent=False` de `build_add_holidays_request` no se tocó**, pese a que la OpenAPI en
vivo dice *"Idempotent by date, so re-seeding is safe"*: D-19/D-20 piden evidencia
**medida**, la mide 27-06 y el flip lo decide 27-07.

### Sweep terminal, recheck del feed y política de snapshots

**`probe_residue_sweep_{sync,async}`** es la red **debajo** de los `finally`, no su
reemplazo: atrapa lo que ellos no pudieron revertir, incluido residuo de una corrida
anterior. Lee las dos superficies por sus identificadores dedicados (símbolos `GSDPROBE/`
activos vía `prefix=` server-side, y días del año 2099), reintenta la limpieza **una** vez
si el gate está abierto, re-lee, y si algo sobrevive emite un `ERROR-MAP` OPEN que **nombra
exactamente qué**. Corre con el gate abierto o cerrado porque sus dos lecturas son GETs: con
el gate cerrado no puede limpiar, pero sí reportar —que es justo lo que un operador necesita
antes del próximo run—. El reintento borra **exclusivamente** días de `_PROBE_HOLIDAYS`:
2099 es un año dedicado, pero borrar una fila que este driver no creó sería un daño peor que
el residuo que se quiere limpiar.

**`probe_health_feed_recheck_sync`** clasifica un `ingestor.last_error` poblado como
`EXPECTED` + auto-infligido, **nunca** `SHAPE`. El spec documenta que un símbolo no validado
contra el exchange aflora justo ahí; llamarlo drift sería una misatribución y además
inflaría el conteo de divergencias del criterio 4 con ruido propio. Registra el **tipo** del
campo, jamás su valor.

**`probe_snapshot_rebaseline_notice_sync`** deja la política D-17/D-26 escrita en el mismo
archivo donde vive la evidencia: `get-calendar.json` **no** derivará (`schema_of` muestrea
sólo `days[0]` y la shape del feriado de prueba es idéntica al item commiteado);
`get-symbols.json` **sí** derivará de forma permanente, porque el símbolo revertido vive en
`active=False` para siempre y `probe_symbols_sync` lee justamente con `active=False` — y por
eso se **re-baselinea a propósito** en 27-07 en vez de excluirse: excluirlo apagaría la
detección de drift sobre un endpoint de lectura de primera clase, mientras que
re-baselinearlo captura por primera vez la shape real de `Symbol` (hoy el baseline es
`"schema": []`).

## Inventario de identificadores de snapshot (insumo del re-baseline de 27-07)

34 usos de `client_function` en el driver. Los **nueve identificadores de lectura** aparecen
dos veces cada uno —una por superficie— y eso es deliberado desde Phase 23: la baseline
pertenece al **endpoint**, no a la superficie. Los **dieciséis restantes** son únicos y
disjuntos de ese conjunto.

**Lecturas (compartidas sync+async, x2 cada una — baselines YA commiteados):**

| `client_function` | Archivo |
|---|---|
| `get_health` | `get-health.json` |
| `get_health_feed` | `get-health-feed.json` |
| `get_market_data` | `get-market-data.json` |
| `get_latest` | `get-latest.json` |
| `get_instruments` | `get-instruments.json` |
| `get_segments` | `get-segments.json` |
| `get_symbols` | `get-symbols.json` ← **el único que se re-baselinea en 27-07** |
| `get_calendar` | `get-calendar.json` |
| `get_calendar_config` | `get-calendar-config.json` |

**Mutaciones y lecturas filtradas (x1 cada una — archivos que aterrizan en el run armado 27-06):**

| `client_function` | Archivo que se escribirá | Plan |
|---|---|---|
| `create_symbol_sync_response` | `create-symbol-sync-response.json` | 27-04 |
| `create_symbol_async_response` | `create-symbol-async-response.json` | 27-04 |
| `create_symbols_batch_sync_response` | `create-symbols-batch-sync-response.json` | 27-04 |
| `create_symbols_batch_async_response` | `create-symbols-batch-async-response.json` | 27-04 |
| `update_symbol_sync_response` | `update-symbol-sync-response.json` | 27-04 |
| `update_symbol_async_response` | `update-symbol-async-response.json` | 27-04 |
| `get_symbols_probe_prefix_sync` | `get-symbols-probe-prefix-sync.json` | 27-04 |
| `get_symbols_probe_prefix_async` | `get-symbols-probe-prefix-async.json` | 27-04 |
| `preview_calendar_config_sync_response` | `preview-calendar-config-sync-response.json` | **27-05** |
| `preview_calendar_config_async_response` | `preview-calendar-config-async-response.json` | **27-05** |
| `add_holidays_sync_response` | `add-holidays-sync-response.json` | **27-05** |
| `add_holidays_async_response` | `add-holidays-async-response.json` | **27-05** |
| `get_calendar_year_2099_sync` | `get-calendar-year-2099-sync.json` | **27-05** |
| `get_calendar_year_2099_async` | `get-calendar-year-2099-async.json` | **27-05** |
| `delete_holiday_sync_response` | `delete-holiday-sync-response.json` | **27-05** |
| `delete_holiday_async_response` | `delete-holiday-async-response.json` | **27-05** |

Ninguno de los dieciséis colisiona con un archivo existente bajo
`.planning/verification/schemas/market-data-client/` (los nueve que hay son exactamente los
de la primera tabla).

## Orden de registro de probes (ambas superficies)

**`_async_main` (18):** `health_async`, `market_data_async`, `latest_async`,
`instruments_async`, `segments_async`, `symbols_async`, `calendar_async`, `no_data_async`,
`mutation_gate_refusal_async`, `create_symbol_async`, `symbols_after_create_async`,
`create_symbols_batch_async`, `update_symbol_async`, **`preview_calendar_config_async`**,
**`add_holidays_async`**, **`calendar_after_holiday_async`**, **`delete_holiday_async`**,
**`residue_sweep_async`**.

**`main()` (26 en total, en orden de impresión):** `health_sync`, `market_data_sync`,
`latest_sync`, `instruments_sync`, `segments_sync`, `symbols_sync`, `calendar_sync`,
`param_encoding_sync`, `no_data_sync`, `auth_fail_sync`, `mutation_gate_refusal_sync`,
→ *(todo el bloque async de arriba)* → `create_symbol_sync`, `symbols_after_create_sync`,
`create_symbols_batch_sync`, `update_symbol_sync`, **`preview_calendar_config_sync`**,
**`add_holidays_sync`**, **`calendar_after_holiday_sync`**, **`delete_holiday_sync`**,
**`residue_sweep_sync`**, `parity_sync_async`, **`health_feed_recheck_sync`**,
**`snapshot_rebaseline_notice_sync`**, `expected_put_config_operator_gated`,
`cycle_closure`.

Todo read probe y su snapshot corren antes de cualquier mutación; cada sweep es lo último de
su superficie; `cycle_closure` es lo último de todo, así que ve el findings file completo del
run.

## Verification

- **Guards del driver + findings** (13 archivos: los dos nuevos, los cinco de 27-03/27-04,
  `test_cycle_closure_market_data.py`, `test_mutation_gate_parametrized.py`,
  `test_findings_fid_seed.py`, `test_findings_append_only.py`,
  `test_findings_dedupe_by_title.py`, `test_main_drivers_bare_except.py`) → **75 passed**.
- `packages/market-data-client/tests` → **344 passed**.
- `ruff check .` → all checks passed. `ruff format --check .` → 201 files already formatted.
  `mypy main_market_data.py packages/market-data-client/src` → no issues, 12 source files.
- Acceptance AST one-liners, todas exit 0: los dos probes de preview existen y ni
  `set_calendar_config` / `delete_calendar_config` ni sus builders aparecen como atributo ni
  como llamada, mientras `preview_calendar_config` sí; paridad sync/async completa en las
  tres familias de holidays; **exactamente 2** sitios de constructor `Client`/`AsyncClient`;
  los cuatro probes terminales nuevos existen.
  `grep -c '2099-12-29'` → 1 y `grep -c '2099-12-30'` → 1 (el piso pedido era 1 en cada uno;
  ambos se usan por referencia a la constante, y `_PROBE_HOLIDAYS` los agrupa).

### Corridas con el gate cerrado

Las credenciales están presentes, así que las dos corridas (tras la task 2 y tras la task 3)
fueron **read sweeps en vivo** reales contra develop. `MARKET_DATA_VERIFY_MUTATING` no está
puesta en el entorno ni en ningún `.env`, así que el gate estuvo cerrado y **se despacharon
cero mutaciones**. Exit code **0** en ambas.

Los 18 probes destructivos reportaron el skip a nivel probe, verbatim
`PROBE <name>: SKIPPED (mutating, guard off)` — incluido
`PROBE add_holidays_sync: SKIPPED (mutating, guard off)`, el que la acceptance criterion de
la task 2 pide literal. Los dos sweeps corrieron y la última línea antes del summary fue
`PROBE cycle_closure: PASS 34 CONFIRMED/FIXED con regresión`.

**Línea `SUMMARY:` verbatim (corrida final):**

```
SUMMARY: PASS=23 FAIL=0 SKIPPED=18 FINDING=2
```

Contra la línea base de 27-04 (`PASS=21 FAIL=0 SKIPPED=8 FINDING=2`): `SKIPPED` sube en 10
—los 8 probes destructivos nuevos más los 2 terminales gate-skipped— y `PASS` sube en 2, que
son exactamente los dos sweeps de residuo. `FINDING` no se movió: el read sweep está intacto.

**Residuo en develop, medido y no supuesto:** `residue_sweep_sync` y `residue_sweep_async`
reportaron ambos `PASS sin residuo (reintento=False)`. Es decir, hoy develop no tiene ningún
símbolo `GSDPROBE/` activo ni ningún día en 2099 — la línea base limpia contra la que 27-06
va a medir.

**Terminales EXPECTED que emite una corrida con el gate cerrado: ninguno nuevo.** El único
que se ejecuta es `expected_put_config_operator_gated`, y su finding ya existe desde 27-03,
así que el dedupe por título lo convierte en no-op. `health_feed_recheck_sync` y
`snapshot_rebaseline_notice_sync` se saltean con el gate cerrado a propósito (ver Deviation
2), de modo que `git diff --stat .planning/verification/` no muestra **ningún bloque de
finding nuevo** — sólo el reflow de re-serialización y el timestamp ART.

**Higiene del findings file.** Las dos corridas reescribieron
`.planning/verification/market-data-client-findings.md` con el reflow habitual. El invariante
de preservación de prosa de 27-01 se verificó **antes** de revertir y se sostuvo las dos
veces: `Classification:` **36**, `Resolution:` **34**, `Regression:` **34**. Cada corrida se
revirtió con `git checkout -- <ese único archivo>`; el archivo quedó byte-idéntico a su
estado base (sha256 `5fadf738…22ef6`, verificado tras cada revert). `git status` no mostró
ningún archivo untracked además del test nuevo, así que **no se creó ni se sobreescribió
ningún schema snapshot**. El corpus de findings pertenece al run armado, **27-06**.

## Deviations from Plan

**1. [Rule 2 — mitigación faltante] La acceptance criterion de unicidad de identificadores
es insatisfacible tal cual está escrita; se implementó el invariante real y se lo volvió
durable.**
- **Issue:** la one-liner de la task 3 exige `assert not dupes` sobre **todos** los
  `client_function=` del driver. Falla contra el código pre-existente: los nueve
  identificadores de lectura aparecen **dos veces cada uno** (una en el probe sync y otra en
  su espejo async) desde Phase 23, y comparten una sola baseline **a propósito** — esa
  baseline es la fuente de verdad del endpoint, no de la superficie. Satisfacer la one-liner
  literalmente habría requerido renombrar los nueve identificadores de lectura, creando nueve
  archivos nuevos y dejando huérfanos los nueve commiteados. El daño habría sido mucho mayor
  que la propiedad que se buscaba.
- **Resolución:** se implementó la propiedad que la one-liner *quiere* —"ningún identificador
  de mutación ni de lectura filtrada colisiona con nada"— y, como T-27-29 la lista como
  `mitigate` exigiendo "an automated inventory check", se la volvió **durable** en
  `verification/test_main_market_data_snapshot_identifiers.py` en vez de dejarla en una
  one-liner efímera: (a) todo identificador que no es de lectura aparece exactamente una vez;
  (b) los de lectura aparecen a lo sumo dos veces, así que una lectura FILTRADA que se
  colgara de una baseline sin filtrar deja el test RED; (c) ningún `probe_*` de mutación
  snapshotea bajo un identificador de lectura, afirmado **estructuralmente** por función y no
  por conteo; (d) no-vacuidad por piso de cantidad y por existencia real de los nueve nombres
  exceptuados. El inventario completo está en la sección de arriba, que es lo que el plan
  pedía como insumo de 27-07.
- **Files:** `verification/test_main_market_data_snapshot_identifiers.py`. **Commit:** `37aee0c`.

**2. [Interpretación] Los dos terminales nuevos se saltean con el gate cerrado.**
- **Issue:** el plan no dice si `probe_health_feed_recheck_sync` y
  `probe_snapshot_rebaseline_notice_sync` son gate-independientes, pero su acceptance
  criterion sí exige que una corrida con el gate cerrado no muestre **ningún bloque de
  finding nuevo**. Emitirlos gate-independientemente habría agregado un bloque nuevo en cada
  corrida de smoke y, en el caso del recheck, algo peor: con el gate cerrado no creamos
  ningún símbolo, así que un `last_error` poblado **no sería auto-infligido** y clasificarlo
  así sería exactamente la misatribución que ese probe existe para evitar.
- **Resolución:** ambos usan `_skipped_when_gated`. Semánticamente es exacto —el recheck es
  literalmente una *re*-verificación posterior a nuestras mutaciones, y la política de
  snapshots explica snapshots de mutación que con el gate cerrado no existen— y deja la
  corrida gate-off con cero bloques nuevos, que es la criterion literal. En el run armado
  27-06 ambos emiten normalmente. El razonamiento está escrito en los docstrings de los dos
  probes, no sólo acá.

**3. [Rule 1 — bug evitado] El reintento defensivo del DELETE trata el 404 como éxito.**
- **Issue:** el plan pide un `finally` que "re-attempts it defensively and routes any failure
  through the cleanup-finding helper". Literalmente, "any failure" incluye el 404 que el
  servidor devuelve cuando el día **ya fue borrado** — es decir, el camino feliz. Cada
  corrida armada habría emitido un finding de cleanup falso.
- **Fix:** el `finally` captura `MarketDataAPIError` y sólo emite si `status_code != 404`;
  cualquier otra excepción sigue yendo por `_emit_cleanup_finding` sin filtro. Los tres tests
  del guard de cleanup siguen verdes: hay emisor en el `finally`, no hay supresor y el
  cleanup tiene su propio `try/except`.
- **Files:** `main_market_data.py`. **Commit:** `6451aa0`.

**4. [Rule 3 — helper extraído] `_mutate_status_sync` / `_async`.**
El observable que D-19 pide para el DELETE es el **status del segundo fire**, pero `_request`
lo convierte en excepción. Sin este par de helpers el probe habría tenido que elegir entre
perder el dato o envolver el dispatch en un `try` que también se tragaría un refusal del
gate. Capturan sólo `MarketDataAPIError` (la única con `status_code`) y despachan por
`_mutate_raw_*`, así que el gate se sigue evaluando primero y
`MarketDataMutationNotAllowedError` sigue propagando.

**5. [Interpretación] "Both status codes" se registra como `public_keys=N refire_status=NNN`.**
Igual que la Deviation 5 de 27-04: el fire 1 va por el método **público** —que es lo que pide
el criterio 1 del ROADMAP— y los métodos públicos devuelven el body parseado, no un status.
El detalle registra entonces el tamaño del body público y el status del re-fire con gate. El
veredicto de idempotencia no depende de ninguno de los dos, por diseño.

**6. [Orden] `probe_parity` queda entre el sweep sync y los terminales.**
El plan pide "the sweep probes last on each surface, then the health-feed recheck, then…".
`probe_parity` no pertenece a ninguna superficie (`surface="both"`) y **no emite HTTP**:
sólo compara las dos listas de segments ya capturadas. Se lo dejó justo después del sweep
sync, así que la cadena terminal que el plan enumera queda intacta y el sweep sigue siendo lo
último que **toca develop** en su superficie.

Sin cambios arquitectónicos; sin checkpoints Rule 4; sin paquetes instalados; `uv.lock`
intacto.

## Threat model

Las siete dispositions `mitigate` están implementadas:

- **T-27-06** (tampering sobre la config que persiste): cobertura live preview-only + AST
  guard que prohíbe call sites **y referencias**, no-vacuo por exigir la superficie de
  preview; ambos endpoints siguen cubiertos por los tests mockeados del paquete y la
  limitación queda como finding EXPECTED.
- **T-27-26** (no-op no verificado): el *"Writes nothing"* se prueba con comparación
  antes/después y una diferencia es `ERROR-MAP` OPEN.
- **T-27-05** (estado huérfano): días disjuntos, delete en un `finally` enrutado por
  `_emit_cleanup_finding`, más el sweep terminal que reintenta y nombra a los sobrevivientes.
- **T-27-27** (duplicación por retry): veredicto por conteo de días del envelope, no por
  status ni por la prosa del spec; registrado en ambas direcciones y el flag intacto hasta
  27-07.
- **T-27-28** (drift misatribuido): `/health/feed` poblado se clasifica `EXPECTED` +
  auto-infligido con dedupe por título, nunca `SHAPE`.
- **T-27-29** (corrupción de baseline): identificador dedicado por mutación y por lectura
  filtrada, **probado por el guard automatizado nuevo**; la única deriva permanente e
  inevitable queda registrada como re-baseline deliberado.
- **T-27-30** (information disclosure): `updated_by` identifica al harness y ningún campo del
  preview sale del entorno; el finding del feed registra el **tipo** del campo, nunca su
  valor; el diff de config registra **nombres** de campo, nunca valores; los snapshots pasan
  por `schema_of`, que no retiene valores; toda la salida va por `safe_print`.
- **T-27-SC**: no se instaló ningún paquete; `uv.lock` intacto.

Sin superficie de seguridad nueva más allá del threat model del plan — ningún endpoint nuevo,
ninguna ruta de auth nueva, ningún patrón de acceso a archivos nuevo. Sin **Threat Flags**.

## Known Stubs

Ninguno. No se introdujeron valores vacíos hardcodeados, placeholders ni data paths sin
cablear. Los 18 probes destructivos están completamente cableados y están inertes únicamente
porque el gate está cerrado, que es el estado buscado hasta que 27-06 lo arme.

## Deferred / not mine

- Los 19 failures + 19 errors en `verification/` por el drift de firmas de matriz (Phase 15)
  y el fallo worktree-only de `test_phase06_nyquist_gaps.py::test_snapshot_regen_is_idempotent`
  siguen sin cambios y son pre-existentes al SHA base — establecido de forma independiente
  por 27-01, 27-02, 27-03 y 27-04 y registrado en `deferred-items.md`. Nada de este plan toca
  matriz ni el script de regen. Por el presupuesto del executor no se corrió el sweep completo
  de `verification/` (~13 min, dominado por un test que duerme de verdad); se corrieron en su
  lugar los 13 archivos directamente relevantes, todos verdes.
- El **flip del flag `idempotent`** de `build_add_holidays_request` (y, si la medición lo
  pide, el de `build_delete_holiday_request`) es de **27-07**, sobre la evidencia que recoja
  **27-06**. Este plan mide y registra; no cambia flags.
- El **re-baseline de `get-symbols.json`** es de **27-07**.
- Nota para 27-06: `probe_health_sync` / `_async` siguen snapshoteando `get_health_feed`
  **al principio** del run, antes de cualquier mutación, así que dentro de una misma corrida
  el `last_error` que nosotros provoquemos no puede derivar ese baseline. El riesgo real es
  entre corridas, y está acotado porque los símbolos terminan `active=False` y el ingestor no
  los suscribe. Si aun así derivara, `probe_health_feed_recheck_sync` provee la explicación
  clasificada para no tratarlo como drift inexplicado.

## Requirement

`LIVE-MUT-01` — avanzado, no satisfecho. Este plan completa los criterios 2 y 3 del ROADMAP
para la superficie de **calendar**: la configuración real de mercado es ahora
**estructuralmente intocable** desde este driver, el ciclo `create -> verify -> revert` está
completo en ambas superficies con identificadores dedicados, y las tres idempotencias
asumidas de calendar quedan instrumentadas para decidirse por comportamiento medido en vez de
por prosa del spec. El run armado es 27-06 y el requirement se marca completo recién en
27-07.

## Self-Check: PASSED

- `main_market_data.py` — FOUND (contiene `probe_preview_calendar_config_sync`/`_async`,
  `probe_add_holidays_sync`/`_async`, `probe_calendar_after_holiday_sync`/`_async`,
  `probe_delete_holiday_sync`/`_async`, `probe_residue_sweep_sync`/`_async`,
  `probe_health_feed_recheck_sync`, `probe_snapshot_rebaseline_notice_sync`,
  `_mutate_status_sync`/`_async`, `_echo_market_hours`, `_config_field_diff`,
  `_PROBE_HOLIDAYS`, `2099-12-29`, `2099-12-30`)
- `verification/test_main_market_data_no_config_write.py` — FOUND
- `verification/test_main_market_data_snapshot_identifiers.py` — FOUND
- Commits `9242243`, `6451aa0`, `37aee0c` — todos presentes en `git log`
- `.planning/verification/market-data-client-findings.md` — byte-idéntico a base
  (sha256 `5fadf738d059437b9030f92e6f2d87ac8f52bf40da4b3c12741fe5d8e8e22ef6`)
- `.planning/verification/schemas/market-data-client/` — sin archivos nuevos ni modificados
- `STATE.md` / `ROADMAP.md` — no modificados (orchestrator-owned)
