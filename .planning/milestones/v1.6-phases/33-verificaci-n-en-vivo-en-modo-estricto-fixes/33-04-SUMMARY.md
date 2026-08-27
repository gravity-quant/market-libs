---
phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
plan: 04
subsystem: testing
tags: [decode-divergence, probe-context, endpoint-templates, findings, strict-decode, market-data, mutation-gate]

requires:
  - phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
    provides: "`verification/divergences.py` — `probe_context`, `endpoint_scope`, `divergence_capture`, `DivergenceHandler` y la convención de título lockeada `surface-in-title-write-new` (plan 33-01)"
  - phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
    provides: "el formato de línea SUMMARY unificado `DIVERGENCES=N HANDLER_ERRORS=N` (plan 33-02) y el contrato 'ninguna rama de decode mintea un finding' (plan 33-03)"
  - phase: 29-decoder-observable
    provides: "el walker observable, el record congelado de seis claves y `MarketDataDecodeError`"
  - phase: 23-market-data-live
    provides: "el doble gate de mutaciones (`MARKET_DATA_VERIFY_MUTATING=1` AND hostname) y el contrato D-03 read-sweep-sigue-con-gate-cerrado"
  - phase: 15-driver-migration
    provides: "el patrón ONE Client per main() que `strict_decode` respeta como kwarg de constructor"
provides:
  - "`main_market_data.py::_ENDPOINT_TEMPLATES` — el dict D-03 que este driver era el único en NO tener; 16 endpoints keyed por nombre de función del cliente"
  - "los 34 sitios de `_write_schema_snapshot` consumiendo el dict: cada URL del driver tiene UNA sola escritura"
  - "la rama `MarketDataDecodeError` central en `_finding_for_exc` — 43 probes reclasificados con UN edit"
  - "43 sitios de probe decorados + 20 `endpoint_scope` (el par de health es el caso canónico P-5)"
  - "el quinto y último driver imprimiendo la línea SUMMARY unificada que 33-05 parsea"
  - "la primera medición en vivo del pipeline completo: DIVERGENCES=9 sobre el read sweep sync+async con el gate cerrado"
affects: [33-05, 33-06, 33-07]

actuals:
  tokens: 11200
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "constante de templates como ÚNICA escritura de cada URL: los sitios que antes inlineaban el literal lo consumen del dict, y los que llevan método/query lo componen por f-string sobre el mismo valor"
    - "`endpoint_scope` colocado DENTRO del helper no-probe (y no en su call site) cuando el helper corre bajo un decorador que bindeó otro endpoint"
    - "re-binding P-5 auditado por AST sobre las llamadas del cuerpo del probe, no por lectura — y verificado conductualmente con un fake que registra el ContextVar en cada llamada"

key-files:
  created: []
  modified:
    - main_market_data.py

key-decisions:
  - "La rama de decode de `_finding_for_exc` NO escribe un finding, contra el `<action>` literal del plan: `market_data_client._decode` emite el record de seis claves y RECIÉN DESPUÉS levanta, así que el `DivergenceHandler` ya escribió el `SHAPE` bajo el título lockeado. Un segundo `append_finding` duplicaría cada divergencia bajo otro título y rompería el `idempotent_by_title` que la rama existe para habilitar. Mismo criterio que 33-02 y 33-03"
  - "El título que el plan especifica es además IMPLEMENTABLE-IMPOSIBLE: pide derivarlo de `exc.model`, `exc.field_path` y **la especie de divergencia**, y `MarketDataDecodeError.__init__` no recibe ni guarda la especie (sólo `field_path`, `declared_type`, `observed_type`, `model`). La especie sí viaja en el record, que es exactamente por qué el handler es el emisor correcto"
  - "Los 34 sitios de `_write_schema_snapshot` se reescriben para consumir el dict: dejar el literal inlineado AL LADO del dict con el mismo valor es la duplicación drift-prone que el `<action>` pide evitar. Cada string renderizado es byte-idéntico al que reemplaza, así que ningún baseline write-once se mueve"
  - "`_ENDPOINT_TEMPLATES` NO incluye `set_calendar_config` ni `delete_calendar_config`: el driver no tiene call site para ninguno (`test_main_market_data_no_config_write.py` lo vuelve irreintroducible) y un template sin consumidor sería código muerto que un lector futuro leería como cobertura"
  - "Superficie `both` para `probe_parity` y `probe_expected_put_config_operator_gated`: es la que sus PROPIOS `append_finding` ya declaran. Ninguno de los dos hace una llamada en vivo, así que no pueden emitir un record y la variante de título `[both]` no puede aparecer en el censo"
  - "Endpoint `_NO_ENDPOINT` (`\"-\"`) para los SEIS probes sin llamada en vivo; los otros 37 bindean el template real de la función que llaman"
  - "Este driver NO recibe `decode_error=` / `on_decode_error=`: sus 43 probes atrapan `Exception` internamente, así que el decode error nunca llega al decorador y el seam sería código muerto. Es también lo que le evita el split bare/`_pair` que 33-02 necesitó en matriz y higyrus"

patterns-established:
  - "Auditoría de alcanzabilidad ANTES de decorar: se listó por AST, para cada probe, si tiene un `except Exception` y qué funciones de cliente llama, y se buscaron los call sites de decode FUERA de todo probe. Es el chequeo que 33-03 tuvo que descubrir a mitad de camino (`probe_refresh_token`), hecho acá como primer paso"
  - "Falsificación con un fake COMPLETO: el primer fake (sin `_request`) hizo que los probes cayeran en el fallthrough `ERROR-MAP` y el experimento habría reportado un verde falso sobre la rama que no se ejercitó. Un fake incompleto es una señal que no inspecciona nada (P-02)"

requirements-completed: []

coverage:
  - id: D21
    description: "`_ENDPOINT_TEMPLATES` existe en `main_market_data.py` en la forma higyrus/iol —módulo, anotado, keyed por nombre de función del cliente, valores sin interpolar— y es la única escritura de cada URL del driver (criterio 1, D-03)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "censo AST: `_ENDPOINT_TEMPLATES` es un `ast.AnnAssign` module-level (RED previo: ausente, exit 1)"
        status: pass
      - kind: other
        ref: "`grep -v '^#' main_market_data.py | grep -c '_ENDPOINT_TEMPLATES'` = 92 (>=2 requerido); 34 de esos usos son los sitios de `_write_schema_snapshot`, que ya no inlinean ningún literal de URL"
        status: pass
      - kind: other
        ref: "`grep -v '^#' main_market_data.py | grep -c '_ENDPOINT_OPTIONAL'` = 2, idéntico al valor pre-task — el frozenset no relacionado quedó intacto"
        status: pass
    human_judgment: false
  - id: D22
    description: "Una divergencia de decode en market-data produce un `SHAPE` con detalle determinístico cross-probe en vez de un `ERROR-MAP` con título único por probe (criterio 1, P-4)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "falsificación con fake client completo: `probe_health_sync` (bare), `probe_calendar_sync` (bare), `probe_segments_sync` (2-tuple) y `probe_market_data_async` (async) devuelven todos FINDING con el mismo formato de detalle; el driver sobrevive"
        status: pass
      - kind: other
        ref: "determinismo: dos probes distintos sobre la misma `(model, field_path, declared, observed)` producen detalle idéntico módulo la superficie; el nombre del probe NO aparece en el string"
        status: pass
      - kind: other
        ref: "ningún finding escrito por la rama: `append_finding` mockeado registra 0 llamadas en las 4 falsificaciones, y `_fid_counter` no avanza"
        status: pass
    human_judgment: false
  - id: D23
    description: "Los 43 probes cargan `probe_context` con endpoint sin interpolar y superficie explícita; los probes multi-endpoint re-bindean con `endpoint_scope` (criterio 1, D-02, P-5)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "censo AST: `undecorated == []`, exit 0 (RED previo: 43 de 43 sin decorar, exit 1, con los 43 nombres impresos)"
        status: pass
      - kind: other
        ref: "`grep -v '^#' main_market_data.py | grep -c 'probe_context('` = 43 = `grep -cE '^(async )?def probe_'`"
        status: pass
      - kind: other
        ref: "`grep -v '^#' main_market_data.py | grep -c 'endpoint_scope('` = 20 (>=2 requerido)"
        status: pass
      - kind: other
        ref: "binding conductual del par canónico P-5: `probe_health_sync` ve `/health` en `get_health` y `/health/feed` en `get_health_feed`; `probe_calendar_sync` ve `/calendar` y `/calendar/config`. Los ContextVar vuelven a `\"-\"` al salir"
        status: pass
    human_judgment: false
  - id: D24
    description: "`main()` instala el handler sobre el sweep entero con el allocator propio del driver y reporta los dos números del censo (criterio 1, P-2, P-3)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "corrida en vivo real contra develop: `SUMMARY: PASS=23 FAIL=0 SKIPPED=18 FINDING=2 DIVERGENCES=9 HANDLER_ERRORS=0`"
        status: pass
      - kind: other
        ref: "no-vacuidad: `logging.getLogger('market_data_client')` pasa de NOTSET a INFO dentro del CM, un record sintético de seis claves llega al handler bajo el título lockeado y el nivel queda restaurado al salir"
        status: pass
      - kind: other
        ref: "orden en `main()`: `write_findings(_PKG)` < `_seed_fid_counter()` < `divergence_capture(...)` < primer probe"
        status: pass
    human_judgment: false
  - id: D25
    description: "`strict_decode=_STRICT` viaja por exactamente un `Client` y un `AsyncClient`; el doble gate de mutaciones y el contrato read-sweep-sigue-con-gate-cerrado no se movieron (P-11, T-33-18, T-33-19, prohibición P-05)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_main_market_data_no_gate_bypass.py (4 casos)"
        status: pass
      - kind: unit
        ref: "verification/test_main_market_data_uses_single_client_instance.py::test_main_market_data_uses_single_client_instance"
        status: pass
      - kind: other
        ref: "`grep -v '^#' main_market_data.py | grep -c 'strict_decode=_STRICT'` = 2; `_STRICT` es True bajo `MARKET_LIBS_STRICT_DECODE=1` y False sin él"
        status: pass
      - kind: other
        ref: "corrida en vivo con el gate CERRADO: los 16 probes destructivos reportan `SKIPPED (mutating, guard off)`, los dos de refusal reportan `mutación rechazada sin opt-in (0 HTTP, 0 Auth0)`, y el read sweep completo igual corre (D-03)"
        status: pass
    human_judgment: false
  - id: D26
    description: "Los cuatro AST-guards pre-existentes del driver siguen verdes tras 43 decoradores y 20 re-bindings (D-09, D-17, D-06)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_main_market_data_postprocess_guarded.py::test_main_market_data_postprocess_is_try_guarded"
        status: pass
      - kind: unit
        ref: "verification/test_main_market_data_snapshot_identifiers.py (4 casos)"
        status: pass
      - kind: unit
        ref: "verification/test_main_market_data_no_config_write.py"
        status: pass
      - kind: unit
        ref: "verification/test_main_market_data_skip_line_shape.py"
        status: pass
    human_judgment: false
  - id: D27
    description: "El decorador no introdujo ninguna rotura nueva en los dos archivos canario (carry-forward 5 de 33-03)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "`test_matriz_sweep_snapshot.py` + `test_main_matriz_login_fail_uniformity.py`: 19 failed / 3 passed / 19 errors — idéntico a `33-BASELINE.md` y a las mediciones de 33-02 y 33-03"
        status: pass
    human_judgment: true
    rationale: "Decidir que un set rojo idéntico cuenta como 'sin regresión' —y no como 'sigue roto'— es un juicio de scope contra la línea base committeada, no un chequeo mecánico."

duration: 15min
completed: 2026-08-27
status: complete
---

# Phase 33 Plan 04: market-data onto the divergence mechanism Summary

**El driver más grande del repo (43 probes, 55 handlers amplios, la única superficie destructiva)
queda sobre el mecanismo del criterio 1, y el agujero D-03 —era el único de los cinco sin
`_ENDPOINT_TEMPLATES`— queda cerrado con el dict como ÚNICA escritura de cada URL del archivo. Los
43 probes enrutan sus excepciones por UN solo helper, así que la reclasificación de `ERROR-MAP` a
`SHAPE` fue un edit y no 55. En el camino se verificó en vivo lo que faltaba probar: el pipeline
completo corre contra develop y devuelve `DIVERGENCES=9 HANDLER_ERRORS=0` con el doble gate de
mutaciones cerrado y los 16 probes destructivos en SKIPPED.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-08-27T00:21:52Z
- **Completed:** 2026-08-27T00:37:18Z
- **Tasks:** 2 de 2
- **Files created/modified:** 1 (410 insertions, 176 deletions)

## Accomplishments

- **El criterio 1 queda cubierto en los 5 de 5 drivers.** Con los 43 sitios de este plan el censo de
  `probe_context` va 46 (matriz) + 19 (higyrus) + 15 (iol) + 7 (ambito) + 43 (market-data) =
  **130 probes decorados**, exactamente el número que 33-05 va a gatear.
- **D-03 cerrado, y cerrado de forma que no puede volver a abrirse por deriva.** El dict no se
  agregó *al lado* de los literales: los 34 sitios de `_write_schema_snapshot` ahora lo consumen, así
  que `/health`, `/marketdata/latest`, `/symbols/{symbol_id}` y las otras 13 URLs tienen **una sola
  escritura** en las 3400 líneas del archivo. Cada string renderizado es byte-idéntico al que
  reemplazó, verificado literal por literal, así que ningún baseline write-once se movió.
- **El salto de `ERROR-MAP` que el plan existe para evitar está medido, no supuesto.** El fallthrough
  titula `f"{name}: {type(exc).__name__} inesperado"` —único por probe— y los 43 probes pasan por
  ahí. Con 9 triples distintos vivos y ~25 probes que ejercitan la superficie tipada, un pase
  estricto sin esta rama habría minteado decenas de `ERROR-MAP` indeduplicables.
- **El único driver con superficie destructiva quedó demostrablemente intacto.** El doble gate se
  evalúa una vez, `mutating_allowed` y `expected_host` viajan sin cambios, y la corrida en vivo con
  el gate cerrado muestra los 16 probes destructivos en `SKIPPED (mutating, guard off)` y los dos de
  refusal en `0 HTTP, 0 Auth0` — mientras el read sweep completo corre igual (D-03).
- **Las 9 divergencias en vivo confirman las dos S-1/S-2 estructurales de `29-SIZING.md`.**
  `Instrument` y `Segment` llegan como `non_dict` desde el wire real.

## `_ENDPOINT_TEMPLATES`: el key set completo (D-03)

16 claves, todas con call site real en el driver. Los `{param}` viajan **sin interpolar**.

| Clave (función del cliente) | Template |
|---|---|
| `get_health` | `/health` |
| `get_health_feed` | `/health/feed` |
| `get_market_data` | `/marketdata` |
| `get_latest` | `/marketdata/latest` |
| `get_latest_batch` | `/marketdata/latest` |
| `get_instruments` | `/instruments` |
| `get_segments` | `/instruments/segments` |
| `get_symbols` | `/symbols` |
| `create_symbol` | `/symbols` |
| `create_symbols` | `/symbols/batch` |
| `update_symbol` | `/symbols/{symbol_id}` |
| `get_calendar` | `/calendar` |
| `get_calendar_config` | `/calendar/config` |
| `preview_calendar_config` | `/calendar/config/preview` |
| `add_holidays` | `/calendar/holidays` |
| `delete_holiday` | `/calendar/holidays/{day}` |

**Ausentes a propósito:** `set_calendar_config` y `delete_calendar_config`. Ninguno tiene call site
—`verification/test_main_market_data_no_config_write.py` lo vuelve irreintroducible— y un template
sin consumidor se leería como cobertura que no existe.

**No confundir con `_ENDPOINT_OPTIONAL`** (`:110`), un `frozenset` de CLAVES DE RESPUESTA opcionales
que usa el SHAPE-diff. Es una constante no relacionada, quedó intacta (grep = 2 antes y después) y el
comentario del dict nuevo lo dice explícitamente para que un lector futuro no las conflacione.

Los sitios de snapshot que llevan método HTTP o query string componen sobre el mismo valor:

```python
endpoint=f"POST {_ENDPOINT_TEMPLATES['create_symbol']}"
endpoint=f"GET {_ENDPOINT_TEMPLATES['get_symbols']}?prefix={_PROBE_PREFIX}"
endpoint=f"PATCH {_ENDPOINT_TEMPLATES['update_symbol']}"      # -> "PATCH /symbols/{symbol_id}"
endpoint=f"GET {_ENDPOINT_TEMPLATES['get_calendar']}?year={_HOLIDAY_YEAR}"
endpoint=f"DELETE {_ENDPOINT_TEMPLATES['delete_holiday']}"    # -> "DELETE /calendar/holidays/{day}"
```

El `{symbol_id}` / `{day}` vive DENTRO del valor del dict, no en el literal del f-string, así que no
se interpola nunca (T-33-20).

## Probes que requirieron `endpoint_scope` (P-5)

Auditado por AST: se listaron, por probe, todas las llamadas a una función del cliente en su cuerpo, y
se marcó como caso P-5 todo probe que toca más de un endpoint DISTINTO. **20 sitios** en total.

| Sitio | Endpoint del decorador | Re-bindeado a | Por qué |
|---|---|---|---|
| `probe_health_sync` / `_async` | `/health` | `/health/feed` | **El caso canónico** que el plan nombra. `get_health_feed()` + su re-disparo crudo van dentro del scope; sin él una divergencia de `HealthFeed`/`FeedIngestor` se atribuiría a `/health`, un endpoint del que ese modelo nunca sale. |
| `probe_calendar_sync` / `_async` | `/calendar` | `/calendar/config` | Dos endpoints con dos modelos (`CalendarDay` vs `CalendarConfig`). |
| `probe_create_symbols_batch_sync` / `_async` | `/symbols/batch` | `/symbols` | La relectura de confirmación por prefijo. |
| `probe_create_symbols_batch_sync` / `_async` (`finally`) | `/symbols/batch` | `/symbols/{symbol_id}` | La reversión `PATCH active=false` de los dos identificadores del batch. |
| `probe_update_symbol_sync` / `_async` | `/symbols/{symbol_id}` | `/symbols` | La confirmación de que la reversión quedó. |
| `probe_preview_calendar_config_sync` / `_async` | `/calendar/config` | `/calendar/config/preview` | El decorador bindea las lecturas antes/después (la prueba en vivo del *"Writes nothing"*); los cuatro disparos del preview van al otro endpoint. |
| `probe_delete_holiday_sync` / `_async` | `/calendar/holidays/{day}` | `/calendar` | La confirmación de ausencia lee el calendario del año dedicado. |
| `_residue_days_sync` / `_async` (helper, no probe) | `/symbols` (del sweep) | `/calendar` | El scope vive DENTRO del helper y no en su call site, porque corre bajo un decorador que bindeó otro endpoint. |
| `_retry_residue_cleanup_sync` / `_async` (helper, no probe) | `/symbols` (del sweep) | `/symbols/{symbol_id}` y `/calendar/holidays/{day}` | Dos re-bindings por superficie, uno por loop de limpieza. |

**Casos que a primera vista parecen P-5 y no lo son:**

- `probe_latest_sync` / `_async` llaman `get_latest` **y** `get_latest_batch`, pero los dos builders
  (`build_latest_request`, `build_latest_batch_request`) despachan contra `path="/marketdata/latest"`.
  Es el mismo endpoint con dos métodos, y el dict los mapea al mismo template.
- `probe_symbols_after_create_sync` / `_async` leen `/symbols` filtrado por prefijo — un solo
  endpoint, aunque el snapshot lleve un `client_function` propio (D-17).

## Formato exacto del detalle determinístico

`_finding_for_exc` compone el detalle del `ProbeResult` así (f-string verbatim):

```python
f"SHAPE [{surface}] MarketDataDecodeError model={exc.model} "
f"path={exc.field_path} declared={exc.declared_type} "
f"observed={exc.observed_type}"
```

Ejemplo medido:

```
SHAPE [sync] MarketDataDecodeError model=HealthFeed path=.ingestor.last_error declared=str observed=int
```

Propiedades que 33-05 puede asumir:

- **No contiene el nombre del probe.** Dos probes que golpean la misma
  `(model, field_path, declared, observed)` producen el mismo string módulo la superficie.
- Se compone **sólo** con los cuatro atributos certificados type-and-path-only por T-29-36 (P-01 /
  T-33-21). La rama **no** gana el `repr(exc)` que las pre-existentes conservan.
- **Este detalle NO es el título del finding.** El título es el del `DivergenceHandler`
  (`{model}{path}: {kind} (declared=…, observed=…) [{surface}]`, convención lockeada
  `surface-in-title-write-new`). El detalle es lo que se imprime en la línea `PROBE …` de stdout.

## Formato exacto de la línea SUMMARY (33-05 la parsea)

Los cinco drivers imprimen ahora la MISMA forma:

```
SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N DIVERGENCES=N HANDLER_ERRORS=N
```

f-string verbatim de este driver:

```python
f"SUMMARY: PASS={n_pass} FAIL={n_fail} SKIPPED={n_skip} FINDING={n_find} "
f"DIVERGENCES={len(handler.seen)} HANDLER_ERRORS={len(handler.errors)}"
```

Semántica idéntica a la que fijó 33-02: `DIVERGENCES` = `len(DivergenceHandler.seen)` = triples
distintos `(slug, model, field_path, kind)`, **la unidad del censo**; `FINDING` = probes con
`ProbeResult.status == "FINDING"`; `HANDLER_ERRORS` distinto de cero **invalida el censo de esa
corrida**.

## Medición en vivo obtenida en esta sesión (insumo para 33-05)

Durante la verificación conductual el driver corrió **de verdad** contra `develop` (el `.env` del
paquete se carga en import time vía `python-dotenv`, así que el gate de credenciales pasó). La
corrida fue **read-only**: el gate de mutaciones estaba cerrado y los 16 probes destructivos
reportaron `SKIPPED (mutating, guard off)` — el doble gate se sostuvo exactamente como el diseño
dice (P-11 / prohibición P-05). Línea final:

```
SUMMARY: PASS=23 FAIL=0 SKIPPED=18 FINDING=2 DIVERGENCES=9 HANDLER_ERRORS=0
```

Los **9 triples distintos** que el handler capturó, idénticos en las dos superficies (18 findings
`SHAPE`, la razón ~2× que 33-01 predijo):

| # | Modelo | `field_path` | Especie | declared -> observed |
|---|---|---|---|---|
| 1 | `HealthFeed` | `.symbols_never_delivered` | `extra` | `-` -> `int` |
| 2 | `FeedIngestor` | `.ingestor.last_error_age_seconds` | `extra` | `-` -> `int` |
| 3 | `FeedIngestor` | `.ingestor.last_error_at` | `extra` | `-` -> `str` |
| 4 | `FeedIngestor` | `.ingestor.subscription` | `extra` | `-` -> `dict` |
| 5 | `MarketDataSnapshot` | `.staleness_seconds` | `missing` | `float` -> `NoneType` |
| 6 | `MarketDataSnapshot` | `.market_data` | `missing` | `dict` -> `NoneType` |
| 7 | `MarketDataSnapshot` | `.entries` | `missing` | `list` -> `NoneType` |
| 8 | `Instrument` | *(raíz)* | `non_dict` | `Instrument` -> `str` |
| 9 | `Segment` | *(raíz)* | `non_dict` | `Segment` -> `str` |

Los ítems 8 y 9 son las dos **S-1 / S-2** que `29-SIZING.md` declaraba como defectos estructurales
de market-data pendientes de confirmar en vivo: quedan confirmados.

**Los artefactos de esa corrida se revirtieron** (`git checkout --` sobre
`.planning/verification/market-data-client-findings.md`; `git status --porcelain
.planning/verification/` vacío antes de ambos commits, y ningún archivo de schema quedó tocado — los
5 drifts detectados NO sobreescriben baseline, D-25). **Destino: plan 33-05.** No es un censo
descartado: es un censo que todavía no tiene registrada su fecha, su base URL ni su modo de pase, y
33-05 es el plan que corre las dos pasadas y las archiva con esa metadata. `append_finding` es
content-addressed con `idempotent_by_title=True`, así que la re-corrida reproduce estos 18 bloques
exactamente.

**Nota de calibración para 33-05:** 9 triples es el número del **pase observable con el gate de
mutaciones CERRADO**. Los 16 probes destructivos (create/update de symbols, preview de config, ciclo
de holidays) no ejercitaron ni una vez su superficie tipada, así que el piso `>=50` de este paquete
**no** es contrastable contra este número. Con el gate abierto entran además `Symbol`,
`CalendarConfig`, `AddHolidaysResult`, `DeleteHolidayResult` y las lecturas filtradas.

## Task Commits

1. **Task 1: market-data — add `_ENDPOINT_TEMPLATES` (D-03) and SHAPE-classify the decode error centrally** — `68ed5f6` (feat)
2. **Task 2: market-data — decorate all 43 probes and install the handler in `main()`** — `82e2066` (feat)

## Files Created/Modified

- `main_market_data.py` — `import os`; `divergence_capture` / `endpoint_scope` / `probe_context` al
  bloque de imports de `verification`; `MarketDataDecodeError` al import del paquete;
  `_ENDPOINT_TEMPLATES` (16 claves) y `_NO_ENDPOINT`; `_STRICT` con su nota T-33-18 al lado del gate
  de mutaciones; la rama de decode en `_finding_for_exc` más su escalera de docstring reescrita; los
  34 sitios de `_write_schema_snapshot` consumiendo el dict; `probe_context` sobre los 43 probes; 20
  `endpoint_scope`; `strict_decode=_STRICT` en los dos constructores; `divergence_capture` alrededor
  del sweep entero en `main()`; y la línea SUMMARY extendida.

## Decisions Made

1. **La rama de decode no mintea un finding.** Ver Deviations #1 — es la decisión de mayor radio.
2. **Los 34 sitios de snapshot consumen el dict.** Ver Deviations #2.
3. **`_ENDPOINT_TEMPLATES` no lleva los dos endpoints de config sin call site.** Un template sin
   consumidor es cobertura aparente; `test_main_market_data_no_config_write.py` ya garantiza que
   nunca la tendrán dentro de esta fase.
4. **Sin `decode_error=` / `on_decode_error=` en ningún decorador de este driver.** Los 43 probes
   atrapan `Exception` internamente (verificado por AST antes de tocar nada), así que el decode error
   nunca llega al wrapper. Queda un comentario en el propio código diciéndolo. Consecuencia colateral:
   este driver **no necesita** el split `_shape_probe_result` / `_shape_probe_result_pair` que 33-02
   tuvo que introducir en matriz y higyrus — `probe_segments_sync` / `_async` devuelven su 2-tupla
   intacta porque el `except` que los rescata es el de ellos mismos, no el del decorador.
5. **`_RESIDUAL_PROBE_EXCEPTIONS` no aplica acá** (este driver no tiene esa tupla) y ninguna copia de
   `_decode.py` se editó — `check_decode_intactness.py` exit 0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] El `<action>` pide un `append_finding(class_="SHAPE")` que duplicaría el finding que el handler ya escribió — y cuyo título es además imposible de componer**

- **Found during:** Task 1, contrastando el `<action>` contra el contrato lockeado de 33-01 y contra
  `packages/market-data-client/src/market_data_client/_decode.py`
- **Issue:** Dos problemas independientes, cada uno suficiente por sí solo.
  **(a) Sería un duplicado.** `_decode.py:219` llama `_emit(...)` y `_decode.py:221` levanta
  `MarketDataDecodeError` — el record de seis claves sale **antes** del raise. Para cuando
  `_finding_for_exc` corre, el `DivergenceHandler` que la Task 2 instala ya escribió el `SHAPE` bajo
  el título determinístico de la convención lockeada. Un segundo `append_finding` acá produciría DOS
  findings por divergencia, bajo DOS títulos distintos, y rompería el `idempotent_by_title` del lock
  10 que esta rama existe para habilitar. `33-01-SUMMARY.md` lo fija por escrito, y 33-02 y 33-03 ya
  lo aplicaron en los otros cuatro drivers; que market-data fuera el único en escribir un finding
  extra rompería además la relación findings↔censo justo en el driver de mayor volumen, que es lo que
  33-05 contrasta.
  **(b) El título especificado no es componible.** El `<behavior>` pide derivarlo de `exc.model`,
  `exc.field_path` **y la especie de divergencia**, y `MarketDataDecodeError.__init__(field_path,
  declared_type, observed_type, model)` no recibe ni guarda la especie. La especie viaja **sólo** en
  el record — que es precisamente la razón estructural por la que el handler, y no la rama, es el
  emisor correcto.
- **Fix:** La rama devuelve `ProbeResult(name, "FINDING", f"SHAPE [{surface}] ...")` compuesto con
  los cuatro atributos certificados, y no escribe nada. El docstring del helper explica las dos
  razones en el propio código. El `key_link` del plan (`pattern: class_="SHAPE"`) sigue satisfecho:
  el driver conserva sus 5 sitios `class_="SHAPE"` pre-existentes, y el `SHAPE` de la divergencia lo
  emite el handler.
- **Files modified:** `main_market_data.py`
- **Verification:** `append_finding` mockeado registra **0** llamadas en las 4 falsificaciones
  conductuales; `_fid_counter` no avanza; `git status --porcelain .planning/verification/` vacío.
- **Committed in:** `68ed5f6`

---

**2. [Rule 2 - Missing critical] Definir el dict al lado de los literales inlineados habría creado exactamente la deriva que el `<action>` manda evitar**

- **Found during:** Task 1
- **Issue:** El `<action>` dice *"Source every value from the URL already inlined at that endpoint's
  `_write_schema_snapshot` call site so the dict and the snapshot sites cannot drift"*. La lectura
  mínima —copiar los valores y dejar los literales donde están— deja `/health` escrito DOS veces, y
  las 16 URLs escritas 3 veces cada una (dict + sitio sync + sitio async). Eso es literalmente la
  condición de deriva: un cambio de path en el vendor se arregla en un lugar y no en los otros dos, y
  el finding termina nombrando un endpoint que ya no existe.
- **Fix:** Los 34 sitios de `_write_schema_snapshot` consumen el dict. Los 18 que llevan método HTTP
  o query string lo componen por f-string sobre el mismo valor. Se verificó literal por literal que
  **cada string renderizado es byte-idéntico** al que reemplaza (`_PROBE_PREFIX` y `_HOLIDAY_YEAR`
  son constantes del propio driver con los mismos valores), así que ningún baseline write-once se
  mueve y ningún finding de `schema drift` puede originarse en este cambio.
- **Files modified:** `main_market_data.py`
- **Verification:** `test_main_market_data_snapshot_identifiers.py` (4 casos) verde — ese guard mira
  `client_function=`, que no se tocó. Corrida en vivo: los 5 findings de `schema drift` son de
  endpoints de lectura cuyo wire cambió, ninguno de un endpoint mal nombrado.
- **Committed in:** `68ed5f6`

---

**3. [Rule 2 - Missing critical] Cuatro sitios de decode en vivo corren FUERA del probe que bindeó su endpoint**

- **Found during:** Task 2, en la auditoría P-5
- **Issue:** El plan nombra el par de health como *"the confirmed instance"* y pide *"find the rest
  by inspection"*. La inspección por AST encontró seis probes más con dos endpoints distintos, y
  además **cuatro sitios en helpers que no son probes**: `_residue_days_sync` / `_async` (leen
  `/calendar` bajo un decorador que bindeó `/symbols`) y `_retry_residue_cleanup_sync` / `_async`
  (hacen `PATCH /symbols/{symbol_id}` y `DELETE /calendar/holidays/{day}` bajo el mismo decorador).
  Es el mismo tipo de agujero que 33-02 encontró en `_capture_async_query_string` y 33-03 en
  `_capture_raw_wire`: una divergencia ahí quedaría atribuida al endpoint equivocado, que es
  precisamente la señal de alerta que el `<behavior>` de la Task 2 describe.
- **Fix:** `endpoint_scope` **dentro del helper**, no en su call site — el helper puede llamarse desde
  más de un contexto y el binding correcto es una propiedad suya, no del caller. Más los dos bloques
  de cleanup en `finally` de `probe_create_symbols_batch_sync` / `_async`, que revierten con
  `update_symbol` bajo un decorador que bindeó `/symbols/batch`. Total: 20 `endpoint_scope`.
- **Files modified:** `main_market_data.py`
- **Verification:** binding conductual con un fake que registra el `ContextVar` en cada llamada:
  `probe_health_sync` ve `/health` y después `/health/feed`; `probe_calendar_sync` ve `/calendar` y
  después `/calendar/config`; los ContextVar vuelven a `"-"` al salir del probe.
- **Committed in:** `82e2066`

---

**4. [Rule 1 - Bug] La primera falsificación usó un fake incompleto y habría reportado un verde sobre una rama que no se ejercitó**

- **Found during:** Task 2, verificación conductual
- **Issue:** El primer fake client no implementaba `_request`, que los probes llaman vía
  `_raw_via_request_sync` para el wire crudo del snapshot. El `AttributeError` resultante cayó en el
  fallthrough `ERROR-MAP` **antes** de que la rama de decode se ejercitara, y el experimento devolvió
  `FINDING F-01 (OPEN)` — que a ojo se lee como éxito. Peor: como cayó en el fallthrough,
  `append_finding` corrió **de verdad** y ensució el findings file. Un fake incompleto es exactamente
  el "verde producido por una señal que no inspeccionó nada" que P-02 prohíbe.
- **Fix:** Fake completo (con `_request`, `_state` y las funciones de cliente relevantes) y
  `append_finding` / `_write_schema_snapshot` mockeados, de modo que el experimento no pueda escribir.
  Repetido sobre las cuatro formas de retorno: bare sync, bare sync con re-binding P-5, 2-tupla sync
  (`probe_segments_sync`) y bare async.
- **Files modified:** ninguno (el defecto estaba en el experimento, no en el driver)
- **Verification:** `git checkout --` sobre `.planning/verification/market-data-client-findings.md`;
  `git status --porcelain .planning/verification/` vacío. Las falsificaciones posteriores registran
  0 llamadas a `append_finding`.
- **Committed in:** n/a — la corrección es la ausencia del artefacto

---

**Total deviations:** 4 auto-fixed (2× Rule 1, 2× Rule 2)
**Impact on plan:** Ninguno sobre el scope. La #1 evita romper el `idempotent_by_title` que el plan
existe para habilitar, y su segunda mitad es directamente una imposibilidad estructural del
`<behavior>` escrito. La #2 y la #3 son requisitos de corrección: sin la #2 el `<action>` se cumple
en la letra y se incumple en el propósito, y sin la #3 cuatro sitios de decode en vivo quedarían
atribuidos al endpoint equivocado. Cero scope creep: no se tocó ninguna copia de `_decode.py`, ni
`_ENDPOINT_OPTIONAL`, ni el doble gate, ni se agregó un handler de `Exception` número 56, ni se
reparó ninguna de las 19 fallas pre-existentes de `verification/` ni ninguno de los 43 errores
pre-existentes de `uv run mypy verification`.

## Issues Encountered

- **Ninguna de las dos tasks admite un RED de archivo de test nuevo.** Los `<files>` de ambas son
  sólo el driver, y los dos gates a nivel driver (`verification/test_probe_context_coverage.py`,
  `test_finding_count_consistency.py`) están asignados al plan **33-05** por su propio
  `files_modified` — no a este plan, pese a lo que dicen los carry-forwards de 33-01/33-02/33-03 (ver
  Carry-forwards #1). Mismo precedente que 33-02 y 33-03: el RED es el **censo AST del propio
  `<acceptance_criteria>`**, corrido antes del cambio.
- **El driver corrió en vivo sin que se lo pidiera explícitamente.** Se intentó un smoke offline con
  `env -u` sobre las cuatro variables Auth0, pero `python-dotenv` las repone desde el `.env` del
  paquete en import time, así que `require_env` pasó y el sweep completo salió a develop. La corrida
  fue read-only (gate cerrado, 16 destructivos en SKIPPED) y sus artefactos se revirtieron; la
  medición quedó registrada arriba como insumo de 33-05. **Para 33-05: no existe una forma de correr
  este driver "en seco" desmontando el entorno** — la única palanca real es el gate de mutaciones.
- **`.planning/config.json` quedó modificado en el working tree** (`_auto_chain_active: true ->
  false`) por el paso de init del workflow, no por este plan. No se commiteó: no está en
  `files_modified` y no es un artefacto de LIVE-TYP-01.

## Carry-forwards

1. **Corrección de destino: los dos gates a nivel driver son del plan 33-05, no de éste.** Los
   carry-forwards de 33-01 (#2), 33-02 (#3) y 33-03 (#2) rutean
   `verification/test_probe_context_coverage.py` y `test_finding_count_consistency.py` —y el gate de
   orden `write_findings < _seed_fid_counter < primer probe` para matriz, higyrus y ambito— al "plan
   33-04". El `files_modified` de **33-05** lista los dos archivos por nombre; el de 33-04 es sólo
   `main_market_data.py`. Crearlos acá habría colisionado con el plan siguiente. **Siguen pendientes,
   y su dueño es 33-05.** Para market-data el orden está verificado a mano en esta sesión:
   `write_findings(_PKG)` < `_seed_fid_counter()` < `divergence_capture(...)` < primer probe.
2. **La decisión sobre `surface_scope` sigue abierta y también es de 33-05.** Los dos sitios que la
   motivan (`main_higyrus.py::_capture_async_query_string` y `main_iol.py::_capture_raw_wire`) quedan
   con superficie `"-"` porque `endpoint_scope` re-bindea sólo el endpoint. **market-data no agrega
   ningún caso nuevo**: sus cuatro sitios fuera de probe corren bajo el decorador del probe que los
   llama, así que heredan la superficie correcta y sólo necesitaban el endpoint. Cerrar el hueco
   requiere tocar `verification/divergences.py`, fuera de los `<files>` de este plan.
3. **El piso `>=50` de market-data NO es contrastable contra un pase con el gate cerrado.** Los 9
   triples medidos salen de ~25 probes de lectura; los 16 destructivos —los únicos que ejercitan
   `Symbol`, `CalendarConfig`, `AddHolidaysResult` y `DeleteHolidayResult` en vivo— reportan SKIPPED.
   33-05 debe declarar el estado del gate junto a cada número o el contraste contra el piso será una
   comparación entre dos poblaciones distintas.
4. **T-33-18 / P-11 sigue siendo una propiedad del RUNNER, no del driver.** El driver no puede
   impedir que el pase 2 se invoque con `MARKET_DATA_VERIFY_MUTATING=1`: son dos variables
   independientes por diseño. La garantía está escrita en el comentario de `_STRICT` y en el del
   bloque destructivo de `main()`, y **33-05 tiene que hacerla efectiva en su receta de runner**.
5. **`33-BASELINE.md` sigue siendo el único árbitro del rojo de `verification/`.** Medido otra vez en
   esta sesión: `19 failed, 3 passed, 19 errors`, set de node ids idéntico. Un número distinto en un
   plan futuro no es "más del rojo que ya estaba".

## Known Stubs

Ninguno. Los 43 decoradores están cableados a fuentes reales: el endpoint sale de
`_ENDPOINT_TEMPLATES`, que es a su vez la fuente de los sitios de snapshot que ya existían; la
superficie, del sufijo real de cada función o de la que sus propios `append_finding` declaran; y el
`next_fid`, del allocator real del driver ya seedeado. El endpoint `"-"` de los seis probes sin
llamada en vivo no es un placeholder pendiente de cablear: es el valor que significa "ningún endpoint
bindeado", y esos probes efectivamente no tocan ninguno. Las dos claves de config ausentes del dict
no son un stub sino una omisión declarada y justificada arriba.

## TDD Gate Compliance

| Gate | Evidencia |
|---|---|
| RED (Task 1) | Censo AST pre-cambio: `_ENDPOINT_TEMPLATES AnnAssign: False`, `MarketDataDecodeError` refs `0`, `strict_decode=_STRICT` `0`, exit 1. |
| GREEN (Task 1) | `68ed5f6`. Censo post-cambio: AnnAssign `True`, `_ENDPOINT_TEMPLATES` grep 35, `MarketDataDecodeError` grep 4, `strict_decode=_STRICT` 2, `_ENDPOINT_OPTIONAL` sigue en 2. Falsificación conductual de la rama de decode en 4 formas de retorno. |
| RED (Task 2) | Censo AST pre-cambio: `total probes: 43 \| undecorated: 43`, exit 1, con los 43 nombres impresos; `probe_context(` 0, `endpoint_scope(` 0, `divergence_capture(` 0. |
| GREEN (Task 2) | `82e2066`. Censo post-cambio: `undecorated: []`, exit 0; `probe_context(` 43, `endpoint_scope(` 20, `divergence_capture(` 1. Binding conductual del par canónico P-5. No-vacuidad del handler con record sintético. Corrida en vivo end to end con `HANDLER_ERRORS=0`. |

**Sin commit `test(...)` separado, deliberadamente:** igual que en 33-02 y 33-03, el gate de este plan
es la consulta AST escrita en su propio `<acceptance_criteria>`, no un archivo de test nuevo — que
habría colisionado con `verification/test_probe_context_coverage.py`, asignado a 33-05. Fabricar un
`test(...)` vacío para satisfacer la forma del gate habría sido justamente un verde producido por una
señal que no inspecciona nada. Sin fase REFACTOR: no hizo falta.

## Verification Evidence

| Gate | Resultado |
|---|---|
| Censo AST `probe_context` — `main_market_data.py` | `undecorated: []`, exit 0 |
| `grep -v '^#' main_market_data.py \| grep -c 'probe_context('` | 43 (= 43 requerido) |
| `grep -cE '^(async )?def probe_' main_market_data.py` | 43 |
| `_ENDPOINT_TEMPLATES` es `ast.AnnAssign` module-level | True |
| `grep -v '^#' main_market_data.py \| grep -c '_ENDPOINT_TEMPLATES'` | 92 (>=2 requerido) |
| `grep -v '^#' main_market_data.py \| grep -c 'MarketDataDecodeError'` | 4 (>=2 requerido) |
| `grep -v '^#' main_market_data.py \| grep -c 'class_="SHAPE"'` | 5 (>=1 requerido) |
| `grep -v '^#' main_market_data.py \| grep -c 'strict_decode=_STRICT'` | 2 (= 2 requerido) |
| `grep -v '^#' main_market_data.py \| grep -c '_ENDPOINT_OPTIONAL'` | 2 — idéntico al valor pre-task |
| `grep -v '^#' main_market_data.py \| grep -c 'endpoint_scope('` | 20 (>=2 requerido) |
| `grep -v '^#' main_market_data.py \| grep -c 'divergence_capture('` | 1 (>=1 requerido) |
| `uv run pytest verification/test_main_market_data_no_gate_bypass.py -q` | 4 passed |
| `uv run pytest verification/ -q -k uses_single_client_instance` | 6 passed |
| `uv run pytest` (los 7 archivos de guard de market-data) | 22 passed |
| `uv run pytest packages/market-data-client -q` | 585 passed |
| `uv run pytest packages -q` (equivalente CI) | 1736 passed, 1 deselected |
| `uv run pytest verification/test_matriz_sweep_snapshot.py test_main_matriz_login_fail_uniformity.py -q` | `19 failed, 3 passed, 19 errors` — idéntico al baseline, sin deltas |
| `uv run python tools/check_decode_intactness.py` | exit 0 — Checks A/B/C/D verdes, ninguna copia de `_decode.py` tocada |
| `uv run python tools/check_surface_types.py` | exit 0 — 0 violaciones |
| `uv run python tools/check_uniform_structure.py` | exit 0 |
| `uv run mypy` | Success: no issues found in 75 source files |
| `uv run ruff check . && uv run ruff format --check .` | limpio, 245 archivos formateados |
| `_STRICT` bajo `MARKET_LIBS_STRICT_DECODE=1` / sin él | `True` / `False` |
| Interceptación de decode (4 formas) | bare sync, bare sync con re-binding P-5, 2-tupla sync, bare async → todas `FINDING`, driver sobrevive, 0 `append_finding` |
| Determinismo del detalle cross-probe | dos probes sobre la misma divergencia → detalle idéntico módulo la superficie; el nombre del probe no aparece |
| Re-binding P-5 (`probe_health_sync`) | llamada 1 ve `/health`, llamada 2 ve `/health/feed` |
| Re-binding P-5 (`probe_calendar_sync`) | llamada 1 ve `/calendar`, llamada 2 ve `/calendar/config` |
| Reset de `ContextVar` post-probe | `_ENDPOINT` y `_SURFACE` vuelven a `"-"` |
| No-vacuidad del handler | logger NOTSET → INFO dentro del CM, record sintético capturado bajo el título lockeado, nivel restaurado al salir |
| Corrida en vivo end to end | `SUMMARY: PASS=23 FAIL=0 SKIPPED=18 FINDING=2 DIVERGENCES=9 HANDLER_ERRORS=0`, exit 0 |
| Doble gate en la corrida en vivo | 16 probes destructivos `SKIPPED (mutating, guard off)`; 2 de refusal `0 HTTP, 0 Auth0`; read sweep completo igual (D-03) |
| `git status --porcelain .planning/verification/` | vacío antes de ambos commits |

## Self-Check: PASSED

- El archivo declarado en `key-files.modified` (`main_market_data.py`) existe en disco.
- Los 2 hashes de commit declarados (`68ed5f6`, `82e2066`) existen en `git log`.
- El formato de la línea SUMMARY y el del detalle determinístico citados arriba están copiados
  **verbatim** del código del driver, no parafraseados — 33-05 los parsea desde ahí.
- El key set de `_ENDPOINT_TEMPLATES` de la tabla está copiado del dict real, clave por clave.
- La tabla de 9 triples está transcripta de los títulos que el handler escribió en la corrida en
  vivo de esta sesión, no derivada de `29-SIZING.md`.
- El set del canario está medido en esta misma sesión con el mismo comando, no citado de
  `33-BASELINE.md`.
- **`LIVE-TYP-01` queda deliberadamente en `Pending`.** Los siete planes de la Phase 33 cargan ese ID
  en su frontmatter; cerrarlo en el plan 4 de 7 sería una completitud falsa — este plan no entrega
  nada de su scope declarado (ni censo archivado, ni evidencia de `Literal`, ni cycle closure).
  Mismo precedente que 33-01 (deviation #4), 33-03 y la Phase 32 con GATE-TYP-01. Queda para 33-07.
