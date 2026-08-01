---
phase: 27-verificaci-n-en-vivo-segura-fixes
plan: 07
subsystem: market-data-client
tags: [verification, live, fixes, symbols, idempotency, findings, re-baseline, cycle-closure]

# Dependency graph
requires:
  - phase: 27-verificaci-n-en-vivo-segura-fixes
    plan: 06
    provides: "la evidencia medida — clave `id` tipo int, las 8 shapes de mutación, los veredictos de idempotencia por conteo de filas y el SHAPE-diff de Symbol contra la primera fila poblada"
  - phase: 27-verificaci-n-en-vivo-segura-fixes
    plan: 01
    provides: "el serializer que preserva bullets desconocidos — sin él las 30 promociones habrían borrado la prosa de F-01..F-36"
provides:
  - "`symbol_id: int | str` en las cuatro rutas de llamada — ENSANCHADO, nunca angostado; el contrato v0.3.x publicado queda intacto"
  - "`Symbol` reconciliado: cinco campos wire agregados, `marketId` conservado como alias deprecated y por primera vez POBLADO desde el wire"
  - "`parse_symbols_response` desenvuelve el envelope real preservando `list[Symbol]` — el fix no-breaking de D-22"
  - "`build_add_holidays_request` corregido a `idempotent=True` sobre medición, con prueba dispatch-level en ambas superficies"
  - "el short-circuit de `idempotent=False` re-fijado a nivel transport, que el flip habría borrado en silencio"
  - "66 findings, CERO OPEN: 50 FIXED con link de regresión resoluble, 16 EXPECTED adjudicadas"
  - "`get-symbols.json` re-baselineado deliberadamente con la shape REAL de una fila de Symbol"
  - "re-run confirmatorio en vivo: PASS=41 FAIL=0 SKIPPED=0 FINDING=2, ambos sweeps PASS, cycle_closure PASS"
affects: [28-publicacion]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ensanchar en vez de angostar cuando el tipo correcto contradice al publicado (D-22): el tipo correcto se ofrece, el viejo sigue andando"
    - "Alias deprecated POBLADO en vez de renombrado: la compatibilidad no cuesta dejar el campo muerto"
    - "Un fix cuya verificación no puede distinguirlo de su ausencia no está verificado — el detector se arregla junto con el defecto"
    - "Corregir un flag no debe borrar la cobertura del mecanismo que el flag maneja"

key-files:
  created:
    - .planning/phases/27-verificaci-n-en-vivo-segura-fixes/27-07-SUMMARY.md
  modified:
    - packages/market-data-client/src/market_data_client/_core.py
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/src/market_data_client/client.py
    - packages/market-data-client/src/market_data_client/aio.py
    - packages/market-data-client/tests/test_symbols_write.py
    - packages/market-data-client/tests/test_symbols_write_async.py
    - packages/market-data-client/tests/test_calendar_write.py
    - packages/market-data-client/tests/test_calendar_write_async.py
    - packages/market-data-client/tests/test_reference_models.py
    - packages/market-data-client/tests/test_reference_core.py
    - packages/market-data-client/tests/test_core.py
    - packages/market-data-client/tests/test_transport.py
    - main_market_data.py
    - .planning/verification/market-data-client-findings.md
    - .planning/verification/schemas/market-data-client/get-symbols.json

decisions:
  - "`symbol_id` ENSANCHA a `int | str` en vez de angostar a `int`: v0.3.0/v0.3.1 publicaron `str` (D-22)"
  - "El ítem D-08 de percent-encoding queda DISUELTO, no diferido otra vez: el path param es un entero y un entero no puede contener `/`"
  - "`Symbol.marketId` NO se renombra; se agrega `market_id` al lado y `from_api` espeja el wire dentro del alias"
  - "`build_add_holidays_request`: `idempotent` False → True sobre medición (upsert por fecha, 1 fila tras doble-fire)"
  - "`build_delete_holiday_request`: flag MANTENIDO en True — idempotente en estado; el 404 del retry cambia la identidad del error, no el resultado"
  - "`build_preview_calendar_config_request`: flag MANTENIDO — la diferencia de bodies es contenido dependiente del reloj, medida como `market_after.local_time`"
  - "F-48/F-50 y sus espejos quedan EXPECTED, no FIXED: no hubo cambio de código que arreglar y un FIXED sin fix sería un PASS falso"

metrics:
  duration: "~75 min"
  completed: 2026-08-01

status: complete
---

# Phase 27 Plan 07: Close the cycle Summary

**El ciclo cerró, y cerró midiendo.** Cada divergencia que el run armado registró está
arreglada, espejada en ambas superficies, respaldada por un test mockeado y verificada por un
segundo run en vivo que la vio desaparecer. El findings file termina con **cero findings OPEN**.

## Tasks completed

| # | Task | Commit |
|---|------|--------|
| 1 | Ensanche de `symbol_id` + reconciliación de `Symbol` | `5cc9ac1` |
| 2 | `parse_symbols_response` + flags de idempotencia | `3c9d31c` |
| 3a | Ajustes del driver para que el re-run pueda observar los fixes | `2f03ff6` |
| 3b | Promoción de F-37..F-62 con links de regresión | `752e4a1` |
| 3c | Re-baseline + re-run confirmatorio + cierre | `6c57e36` |

---

## Lo que se arregló, y por qué esa forma y no otra

### 1. `symbol_id: str` → `int | str` (D-09 / D-22) — F-44 / F-54

El id de fila es un ENTERO: lo dice la OpenAPI en vivo (`{"type": "integer"}`) y lo confirma el
wire (`"id": int` en cada fila de `GET /symbols` **y** en el body de `POST /symbols`).

Lo tentador era angostar a `int`. **Habría roto a todos los consumidores publicados**: v0.3.0 y
v0.3.1 están tageadas con `str`. Se ensanchó a `int | str` en las **cuatro** rutas —
`_core.build_update_symbol_request`, `Client.update_symbol`, `AsyncClient.update_symbol` y los dos
shims module-level. El tipo correcto queda disponible; el viejo sigue andando.

**El ítem de percent-encoding queda DISUELTO, no diferido.** Phase 25 lo difirió a Phase 27
sobre la premisa de que un `symbol_id` podía ser `"DLR/DIC26"` y contener un `/`. La premisa era
falsa: el parámetro es un entero. No hay nada que encodear, y una capa de quoting sólo podría
corromper un id legítimo. Los docstrings ahora dicen eso explícitamente para que ningún lector
futuro lo re-abra, y un test asserta la ausencia de encoding en ambas superficies.

### 2. `Symbol` reconciliado (D-10 / D-22) — F-42..F-47 / F-52..F-57

Se agregaron los cinco campos wire-only medidos: `id`, `market_id`, `created_at`, `updated_at`,
`received_at`, todos con default para que `from_api` sobre un payload parcial siga sin levantar.

`received_at` en `Symbol` es un campo **de wire** (timestamp de ingesta del server), no el stamp
de cliente de `MarketDataSnapshot`. Mismo nombre, procedencia opuesta. El docstring del módulo lo
dice, y el test parametrizado que asserta "ningún modelo de referencia tiene `received_at`"
excluye `Symbol` explícitamente en vez de ser waiveado en silencio.

**`marketId` no se renombró.** El SHAPE-diff mostró `marketId` model-only y `market_id` wire-only
en el mismo diff, o sea el camelCase estaba simplemente mal. Pero `Symbol` es superficie de
lectura publicada desde v0.2.0 y su read path nunca estuvo roto —a diferencia de `CalendarDay`,
cuyo retipado se justificó justamente porque nadie podía haberla leído poblada—, así que un
rename es breaking y D-22 lo prohíbe acá.

La salida no fue dejar el alias muerto: **`Symbol.from_api` espeja el `market_id` del wire dentro
de `marketId`**. Antes de este fix el alias quedaba en `""` para siempre contra un payload real;
ahora lleva el valor correcto. El mirror sólo LLENA una clave ausente, así que un fixture viejo
que mande `marketId` explícito conserva el suyo.

Nota de implementación: `@dataclass(slots=True)` **reconstruye** la clase, así que un `super()`
de cero argumentos adentro de `from_api` levanta `TypeError` — la celda `__class__` apunta a la
clase pre-slots. Se usa `super(Symbol, cls)` con el comentario que lo explica.

### 3. `parse_symbols_response` (D-11 / D-22) — F-41 / F-51

El body viejo era `[Symbol.from_api(item) for item in raw]`. Contra un objeto JSON bare eso itera
las **claves**, así que cada mutación producía un `Symbol` all-default por clave — medido en vivo
como *"body objeto JSON de 6 clave(s); parse_symbols_response devolvió 6 Symbol, 6 all-default"*
en ambas superficies. Es el mismo modo de falla que tenía `parse_calendar_response` antes de D-12.

Ahora recorre una escalera de shapes: envelope `items[]` → objeto symbol plano → lista bare →
colapso a `[]`. **El tipo de retorno `list[Symbol]` no cambia**: se desenvuelve el envelope en vez
de pasarlo crudo, que es la realización no-breaking que `parse_latest_response` ya había
establecido. Los contadores escalares del envelope (`created`, `reactivated`, `requested`) no se
exponen; hacerlo exigiría cambiar el tipo de retorno y por lo tanto un major.

La discriminación es por CLAVE, no por adivinanza: `items` marca el envelope batch, un `symbol`
top-level marca una fila plana, `items` gana si ambos aparecen. Un test fija esa precedencia.

### 4. Flags de idempotencia — decididos sobre la medición, uno por uno

| Builder | Flag viejo | Flag nuevo | Observable medido | Veredicto |
|---|---|---|---|---|
| `build_create_symbol_request` | `True` | `True` | 1 fila tras doble-fire | CONFIRMADO, sin cambio |
| `build_create_symbols_request` | `True` | `True` | 1 fila por identificador | CONFIRMADO, sin cambio |
| `build_update_symbol_request` | `True` | `True` | 1 fila tras doble-fire | CONFIRMADO, sin cambio |
| **`build_add_holidays_request`** | **`False`** | **`True`** | **1 fila para 2099-12-29 y 1 para 2099-12-30 tras doble-fire → UPSERT por fecha** | **CORREGIDO** |
| `build_delete_holiday_request` | `True` | `True` | 404 en el 2º fire | MANTENIDO, adjudicado |
| `build_preview_calendar_config_request` | `True` | `True` | bodies distintos; difieren en `market_after.local_time` | MANTENIDO, adjudicado |

**El flip (F-49 / F-59).** Phase 26 escribió el único `idempotent=False` del paquete razonando que
un replay duplicaría feriados. La medición dijo lo contrario. **La dirección importa para la
severidad**: este flag era CONSERVADOR DE MÁS, no permisivo de más — costaba un retry perdido,
nunca estado duplicado. El valor viejo era el lado seguro, y eso queda registrado.

**El caso sutil (F-50 / F-60).** El `DELETE` es idempotente en **estado** pero no en **status**:
el segundo fire devuelve 404. Se examinó en vez de despacharlo, porque es el único caso donde
"idempotente" significa dos cosas distintas:

- Lo que el flag gobierna es la **seguridad de replay del estado**, y por esa medida el endpoint
  califica: un replay no puede borrar un segundo día ni resucitar una fila.
- El 404 aparece cuando el primer intento ya borró server-side pero su respuesta se perdió. Eso
  cambia la **identidad** del error, no el resultado: sin retry el caller habría levantado igual
  sobre el 5xx transitorio. Nadie termina creyendo que borró cuando no borró, ni borrando dos veces.
- Pasarlo a `False` cambiaría cero seguridad de datos por perder cobertura de retry sobre fallos
  transitorios reales. Estrictamente peor.

Se mantiene en `True` **con un test que fija la consecuencia** (`503` seguido de `404` → 2 requests,
`MarketDataAPIError`), en ambas superficies. Queda EXPECTED, no FIXED: no hubo cambio de código.

**La adjudicación del preview (F-48 / F-58).** 27-06 midió "bodies DISTINTOS" y dejó la causa
explícitamente sin medir. Ahora está medida: el driver reporta los NOMBRES de las rutas que
difieren, y el re-run devolvió **`difieren=['market_after.local_time']`** en ambas superficies —
una única ruta, y es una proyección de reloj. La evidencia decisiva es independiente de la
hipótesis: el probe leyó `GET /calendar/config` antes y después y la encontró idéntica campo a
campo. Body distinto con config igual es exactamente la firma de un endpoint compute-only.

**Lo que el flip casi rompe en silencio.** `build_add_holidays_request` era el único builder
`idempotent=False`, así que el par de tests dispatch-level de `test_calendar_write.py` era la
**única** prueba de que el short-circuit del retry existe. Corregir el flag habría borrado esa
cobertura sin que nada fallara. Se re-fijó donde realmente vive —a nivel transport, con
`RequestSpec` sintéticas— en **ambas** superficies, así que ningún builder tiene que conservar un
valor particular para que la garantía siga probada.

---

## Tests nuevos — `file.py::test_name`

43 tests nuevos (344 → **387** en el paquete). Cada uno verificado: el archivo nombrado contiene
`def <test_name>(`.

**`packages/market-data-client/tests/test_reference_models.py`**
`::test_symbol_field_set_matches_reconciled_wire` ·
`::test_symbol_from_api_populated_wire_row` ·
`::test_symbol_from_api_partial_leaves_row_id_at_typed_default` ·
`::test_symbol_row_id_is_an_int_not_a_string` ·
`::test_symbol_market_id_alias_mirrors_wire_snake_case` ·
`::test_symbol_explicit_camel_case_payload_key_still_wins` ·
`::test_symbol_received_at_is_a_wire_field_not_a_client_stamp`

**`packages/market-data-client/tests/test_reference_core.py`**
`::test_parse_symbols_response_unwraps_flat_create_body` ·
`::test_parse_symbols_response_unwraps_flat_patch_body` ·
`::test_parse_symbols_response_unwraps_batch_items_envelope` ·
`::test_parse_symbols_response_no_longer_yields_all_default_rows` ·
`::test_parse_symbols_response_read_path_is_unregressed` ·
`::test_parse_symbols_response_dict_without_rows_returns_empty` ·
`::test_parse_symbols_response_non_list_items_returns_empty` ·
`::test_parse_symbols_response_scalar_body_returns_empty` ·
`::test_parse_symbols_response_items_wins_over_flat_symbol_key`

**`packages/market-data-client/tests/test_symbols_write.py`** (y el espejo idéntico en
**`test_symbols_write_async.py`**)
`::test_update_symbol_accepts_int_row_id` ·
`::test_update_symbol_still_accepts_str_row_id` ·
`::test_update_symbol_int_and_str_forms_hit_the_same_path` ·
`::test_update_symbol_applies_no_percent_encoding` ·
`::test_update_symbol_module_shim_accepts_int_row_id` ·
`::test_create_symbol_returns_real_rows_not_key_blanks` ·
`::test_create_symbols_returns_real_rows_from_items_envelope` ·
`::test_update_symbol_returns_real_rows` ·
`::test_symbols_mutations_still_return_lists_of_symbol`

**`packages/market-data-client/tests/test_calendar_write.py`**
`::test_add_holidays_retries_three_times_on_repeated_503` (reemplaza al
`test_add_holidays_not_retried_on_repeated_503` de Phase 26, que assertaba lo contrario) ·
`::test_delete_holiday_retry_after_lost_response_surfaces_404`

**`packages/market-data-client/tests/test_calendar_write_async.py`** — la superficie async no tenía
NINGUNA cobertura dispatch-level de retry; se agregó completa:
`::test_add_holidays_retries_three_times_on_repeated_503` ·
`::test_delete_holiday_retries_three_times_on_repeated_503` ·
`::test_delete_holiday_retry_after_lost_response_surfaces_404`

**`packages/market-data-client/tests/test_transport.py`**
`::test_non_idempotent_spec_is_not_retried_sync` ·
`::test_idempotent_spec_is_retried_sync` ·
`::test_non_idempotent_spec_is_not_retried_async` ·
`::test_idempotent_spec_is_retried_async`

**`packages/market-data-client/tests/test_core.py`**
`::test_build_update_symbol_request_accepts_int_row_id` ·
`::test_build_update_symbol_request_int_and_str_forms_agree` ·
`::test_build_add_holidays_request_is_idempotent` (reemplaza a
`test_build_add_holidays_request_is_not_idempotent`)

Todos los tests que patchean sleep usan `monkeypatch.setattr(time, "sleep", ...)` en sync y un
`asyncio.sleep` falso en async: ningún test paga jitter real.

---

## Mapeo fid → regresión escrito en el findings file

| fid (sync / async) | Estado | Test de regresión |
|---|---|---|
| F-51 / F-41 | FIXED | `test_symbols_write{,_async}.py::test_create_symbol_returns_real_rows_not_key_blanks` |
| F-52 / F-42 | FIXED | `test_reference_models.py::test_symbol_market_id_alias_mirrors_wire_snake_case` |
| F-53 / F-43 | FIXED | `test_reference_models.py::test_symbol_from_api_populated_wire_row` |
| F-54 / F-44 | FIXED | `test_reference_models.py::test_symbol_row_id_is_an_int_not_a_string` |
| F-55 / F-45 | FIXED | `test_reference_models.py::test_symbol_field_set_matches_reconciled_wire` |
| F-56 / F-46 | FIXED | `test_reference_models.py::test_symbol_received_at_is_a_wire_field_not_a_client_stamp` |
| F-57 / F-47 | FIXED | `test_reference_models.py::test_symbol_from_api_populated_wire_row` |
| F-59 / F-49 | FIXED | `test_calendar_write{,_async}.py::test_add_holidays_retries_three_times_on_repeated_503` |
| F-60 / F-50 | EXPECTED | `test_calendar_write{,_async}.py::test_delete_holiday_retry_after_lost_response_surfaces_404` |
| F-58 / F-48 | EXPECTED | — (adjudicado, sin cambio de código) |
| F-37..F-40, F-63..F-66 | EXPECTED | — (observaciones del read sweep) |
| F-61, F-62 | EXPECTED | — (re-baseline deliberado / limitación operativa) |

**La lección de 27-01 se aplicó explícitamente.** El gate no puede saber si un test es
*relevante*, sólo si resuelve. Para `market_id` (F-55/F-45) el link apunta a propósito a la
aserción de **set de campos exacto**, no a un test que lea el campo: un test que sólo leyera los
campos nuevos seguiría verde si faltara alguno o si el alias publicado se hubiera borrado en
silencio. Ningún link fue elegido por estar bien formado; cada uno falla sin su propio fix.

Y ninguna finding se promovió sin fix. F-48/F-58 y F-50/F-60 quedan **EXPECTED** justamente porque
no hubo cambio de código: marcarlas FIXED habría sido un PASS falso, que es la amenaza T-27-40.

---

## Los tres ajustes al driver, y por qué eran obligatorios

Sin ellos el re-run no habría podido distinguir un fix que anda de uno roto.

1. **`_describe_symbols_misparse` juzgaba la FORMA del body, no el RESULTADO.** Devolvía una
   descripción para todo body que no fuera una lista. Con el envelope ya desenvuelto habría
   seguido emitiendo el finding D-11 **para siempre**: el fix nunca habría podido verificarse a sí
   mismo. Ahora se apoya en la firma real del defecto —filas all-default— y pasa cuando el parseo
   produjo filas pobladas.
2. **`_DEPRECATED_ALIAS`** excluye `Symbol.marketId` del direction model-only del SHAPE-diff. Su
   ausencia del wire es por diseño y permanente (D-22 conserva el alias; `from_api` lo puebla), así
   que el finding sería garantizado-falso y se le habría asignado un fid nuevo en cada run futuro.
   Es el mismo mecanismo, con la misma forma de justificación, que ya existía para `received_at`.
3. **El probe de preview reporta qué rutas de clave difieren** — nombres solamente, nunca valores
   (T-27-34). Convierte la adjudicación de F-48/F-58 en una observación en vez de un argumento.

---

## Re-baseline de `get-symbols.json` (D-17 / D-26) — F-61

El baseline commiteado era `"schema": []`, capturado contra un catálogo vacío. 27-06 predijo que
derivaría en el próximo run, y derivó: la lectura ahora ve las 6 filas `GSDPROBE/` inactivas.

Se **re-baselineó**, no se excluyó. Excluir `get_symbols` apagaría la detección de drift sobre un
endpoint de lectura de primera clase; re-baselinearlo la restaura **y** captura por primera vez la
shape real de una fila de `Symbol`. El archivo se borró para que el camino write-once del driver
lo re-escribiera.

```json
"schema": [{"active":"bool","created_at":"str","id":"int","market_id":"str",
            "received_at":"NoneType","symbol":"str","updated_at":"str"}]
```

Sólo nombres de tipo, cero valores. **`get-calendar.json` NO derivó**, exactamente como el
análisis de 27-05 predijo — la predicción se verificó contra el run en vez de asumirse.

---

## El re-run confirmatorio

```
MARKET_DATA_VERIFY_MUTATING=1 uv run --package market-data-client python main_market_data.py
```

Línea `SUMMARY:` verbatim:

```
SUMMARY: PASS=41 FAIL=0 SKIPPED=0 FINDING=2
```

Contra el run armado de 27-06 (`PASS=39 FAIL=0 SKIPPED=0 FINDING=4`): **`PASS` sube 2 y `FINDING`
baja 2** — exactamente los dos findings D-11, uno por superficie, que dejaron de existir.

Líneas que prueban que cada fix se verificó a sí mismo:

```
PROBE create_symbol_sync: PASS public_rows=1 refire_status=200
PROBE create_symbol_async: PASS public_rows=1 refire_status=200
PROBE symbols_sync: PASS symbols=6
PROBE symbols_after_create_sync: PASS 1 fila; id descubierto en clave 'id' (prefijo devolvió 6 filas)
PROBE preview_calendar_config_sync: PASS config sin cambios; doble-fire idéntico=False difieren=['market_after.local_time'] eco_warnings=0 ventana_estrecha_warnings=3
PROBE preview_calendar_config_async: PASS config sin cambios; doble-fire idéntico=False difieren=['market_after.local_time'] eco_warnings=0 ventana_estrecha_warnings=3
PROBE residue_sweep_async: PASS sin residuo (reintento=False)
PROBE residue_sweep_sync: PASS sin residuo (reintento=False)
PROBE cycle_closure: PASS 50 CONFIRMED/FIXED con regresión
```

`create_symbol` pasó de `FINDING` a `PASS` en ambas superficies. **Cero findings SHAPE de `Symbol`
volvieron a emitirse** — las doce de 27-06 desaparecieron. Ninguna divergencia sobrevivió a su
propio fix.

Los únicos 4 bloques nuevos son F-63..F-66: las dos derivas de tipos de `get_market_data` y los dos
probes de no-data, o sea las mismas condiciones ya adjudicadas en F-37..F-40. Se promovieron a
EXPECTED bajo la misma adjudicación. **El findings file termina con 66 bloques y CERO OPEN.**

### Residuo — barrido independiente, read-only, posterior al run

```
=== TERMINAL RESIDUE SWEEP (independent, read-only) ===
GET /symbols?prefix=GSDPROBE/ -> 6 row(s)
GET /symbols?prefix=GSDPROBE/&active=true -> 0 row(s)  <-- must be 0
GET /symbols?prefix=GSDPROBE/&active=false -> 6 row(s)  <-- must be 6
GET /calendar?year=2099 -> 0 day(s)  <-- must be 0
SWEEP RESULT: PASS
```

Las 6 filas son exactamente las 6 autorizadas (`GSDPROBE/P27-{SYNC,ASYNC}`, `-B1`, `-B2`), todas
`active=false`. Los identificadores son estables, así que el segundo run **no agregó ninguna fila
nueva**. Cero días en 2099. Cero escrituras a `PUT`/`DELETE /calendar/config` — ambos probes de
preview reportaron `config sin cambios`. **El alcance autorizado no se excedió en ningún punto.**

Bonus de evidencia: el sweep leyó `id` y `market_id` poblados en las 6 filas a través del modelo
reconciliado — la prueba end-to-end, contra el wire real, de que los campos nuevos se pueblan.

---

## Verification

| Gate | Resultado |
|---|---|
| `ruff check .` | **All checks passed!** |
| `ruff format --check .` | **201 files already formatted** |
| `mypy packages/market-data-client/src` | **Success: no issues found in 11 source files** |
| `pytest packages/market-data-client/tests -q` | **387 passed** (baseline 27-02: 344) |
| Guards de driver + findings harness (12 archivos) | **52 passed** |
| `verify_cycle_closure("market-data-client")` | **`(True, [])`** |
| Re-run en vivo | **exit 0, `FAIL=0`, ambos sweeps PASS, `cycle_closure` PASS** |
| Escaneo de credenciales sobre lo commiteado | **PASS** — 0 ocurrencias de `Bearer `, `eyJ`, `client_secret`, `access_token`, `Authorization`; única URL, la de develop |
| `git diff --diff-filter=D HEAD~1 HEAD` | vacío — ningún archivo trackeado borrado |

Conteos del findings file: 66 bloques `### F-`, 66 `Classification:`, 52 `Regression:`, 0 OPEN. La
prosa de F-01..F-36 quedó intacta: `git diff | grep '^-### F-'` → **vacío**.

Por presupuesto no se corrió el sweep completo de `verification/` (~14 min, dominado por un test
que duerme de verdad). Los 19 failures + 19 errors pre-existentes por el drift de firmas de matriz
(Phase 15) y el fallo worktree-only de
`test_phase06_nyquist_gaps.py::test_snapshot_regen_is_idempotent` siguen en `deferred-items.md` y
no son de este plan.

---

## Deviations from Plan

**1. [Rule 2 — funcionalidad crítica faltante] Se ajustó `main_market_data.py`, que el plan no lista en `files_modified`.**
- **Found during:** task 3, al razonar qué vería el re-run.
- **Issue:** `_describe_symbols_misparse` juzgaba la forma del body en vez del resultado, así que
  habría re-emitido el finding D-11 aunque el fix funcionara. El fix no habría podido verificarse
  a sí mismo, y el criterio de aceptación "ninguna divergencia sobrevive a su propio fix" habría
  sido imposible de satisfacer. En la misma línea, `marketId` habría re-emitido un SHAPE model-only
  con fid nuevo en cada run futuro.
- **Fix:** los tres ajustes descritos arriba. Los 52 guards del driver siguen verdes.
- **Commit:** `2f03ff6`

**2. [Interpretación] Los tests del parser van a `test_reference_core.py`, no a `test_core.py`.**
El plan nombra `test_core.py` para la cobertura directa del parser, pero los tests hermanos de
`parse_symbols_response` (y de los otros parsers de referencia) viven en `test_reference_core.py`.
Se pusieron con sus hermanos. `test_core.py` sí recibió los tests de builder que le corresponden.

**3. [Rule 2] Se agregó cobertura dispatch-level de retry a la superficie async, que no tenía ninguna.**
El plan pide el par dispatch-level "en ambas superficies". `test_calendar_write_async.py` no tenía
NINGÚN test de retry — el par de Phase 26 existía sólo en sync. Se agregaron los tres async
(`add_holidays` retry, `delete_holiday` control positivo, y el caso 503→404).

**4. [Rule 2] Se re-fijó el short-circuit de `idempotent=False` a nivel transport.**
El flip dejó al paquete sin ningún builder `idempotent=False`, lo que habría borrado en silencio
la única prueba de que el flag hace algo. Cuatro tests nuevos en `test_transport.py` con
`RequestSpec` sintéticas, sync y async, con control positivo.

**5. [Rule 3 — blocker de entorno] El worktree no tenía `.env` ni `.venv`.**
- **Fix:** se copió el `.env` del repo principal al mismo path relativo (cubierto por
  `.gitignore:47`, verificado con `git check-ignore -v`) y **se borró al terminar**. Se confirmó
  que nunca apareció en `git status`. Para los tests se usó el intérprete del repo principal con
  `PYTHONPATH=packages/market-data-client/src`, que hace que `market_data_client` y `verification`
  resuelvan al **worktree** (verificado imprimiendo `__file__`), en vez de `uv run --package`, que
  reescribiría el `.venv`. **Ningún valor ni longitud de credencial se imprimió en ningún momento.**

**6. [Interpretación] El run desarmado previo se revirtió antes de armar.**
Se corrió el driver desarmado primero para validar el read sweep con el `Symbol` reconciliado
(ahí es donde `_DEPRECATED_ALIAS` importa) y para que el re-baseline write-once de
`get-symbols.json` se capturara sin mutaciones de por medio. Ese run alocó F-63..F-67, así que el
findings file se revirtió con `git checkout --` sobre ese único archivo antes de armar, para que
el corpus commiteado viniera enteramente del run armado — la misma disciplina que usó 27-06.

**7. [Ampliación] Se promovieron también F-63..F-66, que el run confirmatorio emitió.**
El plan cubre F-37..F-62. El re-run agregó cuatro recurrencias de condiciones ya adjudicadas.
Dejarlas OPEN habría cerrado el ciclo con 4 findings abiertos que ya tenían veredicto bajo otro
fid. Se promovieron a EXPECTED apuntando a la misma adjudicación.

Sin checkpoints Rule 4. Sin dependencias nuevas. `uv.lock` intacto.

---

## Threat model

Las dispositions `mitigate` del plan, ejecutadas:

- **T-27-38** (duplicación silenciosa de datos): el único flag contradicho por la medición se
  corrigió, con prueba dispatch-level de conteo exacto de requests y sleeps en **ambas**
  superficies. Los dos casos adjudicados-sin-cambio quedaron con la adjudicación escrita, y el del
  `DELETE` con test que fija la consecuencia. El short-circuit se re-fijó a nivel transport para
  que la corrección no borrara su propia cobertura.
- **T-27-39** (romper el contrato publicado): `symbol_id` ensanchó en vez de angostar; las tres
  mutaciones siguen devolviendo `list[Symbol]`; `marketId` se conservó. Verificado por inspección
  de firma sobre las 4 rutas y las 6 mutaciones, y por una aserción de set de campos exacto. **No
  hizo falta escalar ninguna decisión de versión**: la evidencia de 27-06 (A6 confirmada) hizo
  alcanzable la realización no-breaking.
- **T-27-40** (PASS de verificación falso): ninguna finding se promovió sin fix implementado.
  `verify_cycle_closure` → `(True, [])` y una aserción independiente confirma que toda finding
  `CONFIRMED`/`FIXED` lleva link resoluble. Los links se eligieron por relevancia, no por estar
  bien formados.
- **T-27-41** (apagar la detección de drift): re-baseline deliberado, no exclusión; diff revisado
  antes de commitear; el acto queda registrado en F-61.
- **T-27-42** (estado huérfano en develop): ambos sweeps PASS + sweep independiente PASS. Los
  identificadores estables hicieron que el segundo run no agregara ninguna fila nueva.
- **T-27-43** (information disclosure): snapshots por `schema_of` (nombres de tipo, cero valores);
  la prosa de resolución nombra cambios de código y paths de test, nunca payloads; escaneo
  automatizado sobre lo commiteado → PASS.
- **T-27-44** (shape fabricada): no aplica — 27-06 no terminó SKIPPED, la evidencia existía.
- **T-27-SC**: ningún paquete instalado; `uv.lock` intacto.

Sin superficie de seguridad nueva. Sin **Threat Flags**.

## Known Stubs

Ninguno.

---

## Para Phase 28 — la premisa de versión está VENCIDA

**`PUB-MUT-01` apunta a "publicar v0.3.0", y v0.3.0 y v0.3.1 ya están tageadas y publicadas.**
v0.3.0 ya contiene `create_symbol` / `create_symbols` / `update_symbol`. Phase 28 debe re-apuntar
el requirement a la próxima versión disponible.

La buena noticia es que **la decisión de major/minor no hay que escalarla**: todo lo de este plan
es no-breaking por construcción.

- `symbol_id` ensanchó (`str` → `int | str`): todo consumidor existente sigue type-checkeando.
- Las tres mutaciones siguen devolviendo `list[Symbol]`: sólo cambia el CONTENIDO, que antes eran
  filas en blanco. Ningún consumidor podía depender de un `Symbol` all-default.
- `Symbol` sólo **suma** campos, todos con default. `marketId` sigue existiendo y ahora está
  poblado — un consumidor que lo leyera recibía `""` y ahora recibe el valor real. Estrictamente
  una mejora.
- El flip de `idempotent` no es superficie pública; cambia comportamiento de retry hacia el lado
  seguro medido.

Así que **un minor alcanza**. Lo único a decidir es el número, no la magnitud.

Nota adicional para Phase 28: `marketId` queda marcado deprecated en el docstring, con remoción
prevista para el próximo MAJOR. Ese es el momento de sacarlo, no antes.

---

## Deferred / not mine

- **El drift de tipos de `get-market-data.json`** (F-37/F-39/F-63/F-65). El key set es idéntico;
  sólo cambian los tipos que `schema_of` infiere según haya o no datos de mercado. Re-baselinear
  fijaría la forma de mercado-cerrado y derivaría en cada run con datos. Un baseline que tolere
  ambos estados es un cambio al harness de snapshots, no a este ciclo.
- **Los emisores de drift y no-data alocan un fid nuevo por run** y no dedupean por título. Eso es
  deliberado y **no debería cambiarse a la ligera**: dos drifts con el mismo título pero distinto
  schema real son hallazgos distintos, y colapsarlos por título haría desaparecer al segundo en
  silencio. El costo es que el findings file crece ~4 bloques por run.
- **La cobertura en vivo de `PUT`/`DELETE /calendar/config`** (F-62) sigue requiriendo una decisión
  de operator sobre alterar la config compartida de develop.
- Los 19 failures + 19 errors pre-existentes de `verification/` (drift de matriz, Phase 15).

---

## Requirement

**`LIVE-MUT-01` — COMPLETO.** Los cinco criterios del ROADMAP tienen respaldo medido:

1. Las 8 mutaciones ejercitadas en ambas superficies detrás del doble gate.
2. Identificadores dedicados con ciclo de cleanup completo; configuración real de mercado intacta.
3. Idempotencia **medida** por conteo de filas, con los flags corregidos donde la medición
   contradijo la declaración.
4. **Toda divergencia registrada, arreglada en el mismo ciclo**, espejada sync y async, con al
   menos un test mockeado de regresión por fix.
5. **Cycle closure PASS**: `verify_cycle_closure("market-data-client")` → `(True, [])`, confirmado
   en vivo por `PROBE cycle_closure: PASS`.

## Self-Check: PASSED

- `.planning/phases/27-verificaci-n-en-vivo-segura-fixes/27-07-SUMMARY.md` — FOUND
- `.planning/verification/market-data-client-findings.md` — FOUND (66 bloques, 0 OPEN, 52 links)
- `.planning/verification/schemas/market-data-client/get-symbols.json` — FOUND (schema no vacío)
- Cada test citado en un bullet `Regression:` — verificado por `verify_cycle_closure` → `(True, [])`
- Commits `5cc9ac1`, `3c9d31c`, `2f03ff6`, `752e4a1`, `6c57e36` — presentes en `git log`
- `packages/market-data-client/.env` — **borrado del worktree**; nunca apareció en `git status`
- `STATE.md` / `ROADMAP.md` — **no modificados** (orchestrator-owned)
- Residuo en develop — 6 filas `GSDPROBE/` todas `active=false`, 0 días en 2099, config intacta
