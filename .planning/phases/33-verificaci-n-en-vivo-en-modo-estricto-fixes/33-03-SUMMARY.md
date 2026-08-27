---
phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
plan: 03
subsystem: testing
tags: [decode-divergence, probe-context, findings, fid-seed, strict-decode, iol, ambito]

requires:
  - phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
    provides: "`verification/divergences.py` — `probe_context`, `endpoint_scope`, `divergence_capture`, `DivergenceHandler` y la convención de título lockeada `surface-in-title-write-new` (plan 33-01)"
  - phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
    provides: "el formato de línea SUMMARY unificado (`DIVERGENCES=N HANDLER_ERRORS=N`) y el par de helpers bare/`_pair` (plan 33-02)"
  - phase: 30-iol-tipado
    provides: "`IOLDecodeError`, los 4 modelos de iol, el renderer sancionado único `_redacted_exc` (AD-30-09-01) y el lock AST que lo pinea"
  - phase: 15-driver-migration
    provides: "el patrón ONE Client per main() que `strict_decode` respeta como kwarg de constructor"
provides:
  - "`main_iol.py` clasifica una divergencia de decode como `SHAPE` con detail determinístico, en vez de `ERROR-MAP` con título único por probe"
  - "22 sitios de probe más decorados (iol 15/15 + ambito 7/7), cada uno con endpoint sin interpolar y superficie explícita"
  - "`main_ambito_financiero.py::_seed_fid_counter` — el allocator de ambito arranca en F-02, por encima de su único fid terminal"
  - "el cuarto y quinto driver imprimiendo la línea SUMMARY unificada que 33-04 parsea"
  - "el contrato `detail: str` para los helpers `_shape_probe_result*` de iol — el precedente `_emit_crash_report` extendido al camino atrapado"
affects: [33-04, 33-05, 33-06, 33-07]

actuals:
  tokens: 8200
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "helper de fallback que recibe TEXTO ya renderizado en vez de la excepción, para no estrenar un segundo renderer bajo un censo AST de renderers"
    - "rama de excepción hermana insertada por script sobre líneas de `ast.ExceptHandler`, con la consulta AST del propio `<acceptance_criteria>` como gate RED/GREEN"
    - "cero medido en vez de cero asumido: el driver sin divergencias posibles igual instala el pipeline y imprime `seen` y `errors` al lado del conteo de probes"

key-files:
  created: []
  modified:
    - main_iol.py
    - main_ambito_financiero.py

key-decisions:
  - "`_shape_probe_result` / `_shape_probe_result_pair` de iol reciben `detail: str` (texto YA renderizado por `_redacted_exc`), NO la excepción — un helper que tomara la excepción se vuelve un segundo renderer bajo `test_the_driver_declares_exactly_one_exception_renderer`, y cada `except` que se la pasara es una delegación no sancionada bajo `test_no_except_handler_in_the_driver_renders_its_exception_raw`. Es exactamente el contrato que `_emit_crash_report` documenta desde 30-12, extendido del camino de crash al camino atrapado"
  - "Ninguno de los dos drivers mintea un finding en la rama de decode: el `SHAPE` ya lo escribió el `DivergenceHandler` bajo el título lockeado. El `<action>` del plan pedía un `append_finding(class_=\"SHAPE\")` acá; escribirlo habría duplicado cada divergencia bajo un segundo título y roto el mismísimo `idempotent_by_title` que la rama existe para habilitar (contrato de `on_decode_error`, 33-01-SUMMARY.md)"
  - "`probe_refresh_token` recibe una rama de decode aunque NO tiene handler amplio — es el único sitio ALCANZABLE del driver que quedaba descubierto: `IOLDecodeError` es HERMANO de `IOLAPIError`, así que la escalera existente lo dejaba propagar y el modo estricto mataba el driver en el probe 14 de 15"
  - "Los 3 probes de iol sin llamada en vivo (`parity_sync_async`, `field_type_map`, `schema_snapshot`) bindean el endpoint `\"-\"` (el default del `ContextVar`); los 7 de ambito bindean el `_ENDPOINT_TEMPLATE` único del paquete aunque 4 no llamen en vivo, porque con un solo endpoint no hay atribución errónea posible"
  - "ambito NO recibe ninguna rama de decode en sus 6 handlers amplios: el paquete declara cero clases de modelo, así que `AmbitoFinancieroDecodeError` es estructuralmente inalcanzable (D-12) y la rama sería código muerto demostrable"
  - "Cero `endpoint_scope` en probes de ambos drivers; uno en `main_iol.py::_capture_raw_wire`, que es el único sitio del monorepo que toca 4 endpoints en una llamada"

patterns-established:
  - "Un lock AST de redacción restringe la FORMA del fix, no sólo su corrección: el diseño obvio (`helper(name, surface, exc)`) es el que el lock rechaza, y el diseño correcto ya estaba escrito en el driver como precedente"
  - "Rama alcanzable vs rama de uniformidad se declaran por separado y se cuentan por separado: 12 ramas de decode, 10 alcanzables — reportar 12 como cobertura sería la señal que no inspecciona nada que P-02 prohíbe"

requirements-completed: []

coverage:
  - id: D14
    description: "Los 15 probes de `main_iol.py` y los 7 de `main_ambito_financiero.py` cargan `probe_context` con endpoint sin interpolar y superficie explícita (criterio 1, D-02)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "censo AST sobre ambos drivers: `undecorated == []`, exit 0 (RED previo: iol 15/15 y ambito 7/7 sin decorar, exit 1)"
        status: pass
      - kind: other
        ref: "`grep -v '^#' main_iol.py | grep -c 'probe_context('` = 15; idem ambito = 7"
        status: pass
      - kind: other
        ref: "binding conductual: `probe_get_quote_sync` ve `/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion` (sin interpolar) + `sync`; `probe_happy_sync` ve `/dolarnacion/historico-general/{from}/{to}` + `sync`"
        status: pass
    human_judgment: false
  - id: D15
    description: "Una divergencia de decode en iol produce un `SHAPE` con detail determinístico cross-probe en vez de un `ERROR-MAP` con título único por probe (criterio 1, P-4)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "censo AST: 12 `except IOLDecodeError` (>=12 requerido), cada uno ADELANTE de su handler amplio"
        status: pass
      - kind: other
        ref: "falsificación con cliente falso — 2-tuple sync, 2-tuple async, bare sync (`refresh_token`), bare sync (`auth_401`), loop de sanity: las 5 formas devuelven su forma correcta con status FINDING; el driver sobrevive"
        status: pass
      - kind: other
        ref: "determinismo: `probe_get_quote_sync` y `probe_get_quote_async` sobre la MISMA divergencia producen detail idéntico módulo la superficie"
        status: pass
      - kind: other
        ref: "ningún finding escrito por la rama: `git status --porcelain .planning/verification/` vacío tras las falsificaciones"
        status: pass
    human_judgment: false
  - id: D16
    description: "`main_iol.py` sigue declarando exactamente un renderer de excepciones (`_redacted_exc`) y ningún handler renderiza su excepción cruda (AD-30-09-01)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_main_iol_exception_redaction.py::test_the_driver_declares_exactly_one_exception_renderer"
        status: pass
      - kind: unit
        ref: "verification/test_main_iol_exception_redaction.py::test_no_except_handler_in_the_driver_renders_its_exception_raw"
        status: pass
      - kind: unit
        ref: "verification/test_main_iol_exception_redaction.py::test_the_census_detects_the_sanctioned_renderer_in_the_real_driver"
        status: pass
    human_judgment: false
  - id: D17
    description: "`main_ambito_financiero.py` emite fids por encima de `F-01`, así que su primer finding deja de ser un no-op silencioso (P-3 / T-33-15)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "`import main_ambito_financiero; _fid_counter` 0 -> `_seed_fid_counter()` -> 1 -> `_next_fid()` = `F-02`"
        status: pass
      - kind: other
        ref: "orden AST en `main()`: `write_findings`@773 < `_seed_fid_counter`@780 < primer probe@796"
        status: pass
    human_judgment: false
  - id: D18
    description: "El `DIVERGENCES=0` de ambito es una medición, no una ausencia: el pipeline está instalado y demostrablemente captura (T-33-16 / D-12)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "no-vacuidad: `logging.getLogger('ambito_financiero_client')` pasa de NOTSET a INFO dentro del CM, un record sintético de seis claves SÍ llega al handler (`seen == {('ambito-financiero-client','Fake','.f','missing')}`, `errors == []`), y nivel+handlers quedan restaurados al salir"
        status: pass
      - kind: other
        ref: "premisa estructural D-12 re-verificada: `ambito_financiero_client.models` declara 0 `ClassDef`"
        status: pass
      - kind: other
        ref: "el SUMMARY imprime `DIVERGENCES` y `HANDLER_ERRORS` SIEMPRE, junto al conteo de probes"
        status: pass
    human_judgment: false
  - id: D19
    description: "`strict_decode=_STRICT` viaja por exactamente un `Client` y un `AsyncClient` por driver; el gate AST de single-Client sigue verde"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_main_iol_uses_single_client_instance.py::test_main_iol_uses_single_client_instance"
        status: pass
      - kind: unit
        ref: "verification/test_main_ambito_financiero_uses_single_client_instance.py"
        status: pass
    human_judgment: false
  - id: D20
    description: "El decorador no introdujo ninguna rotura nueva en los dos archivos canario (carry-forward 4 de 33-02)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "`test_matriz_sweep_snapshot.py` + `test_main_matriz_login_fail_uniformity.py`: 19 failed / 3 passed / 19 errors — idéntico a `33-BASELINE.md` y a la medición de 33-02"
        status: pass
    human_judgment: true
    rationale: "Decidir que un set rojo idéntico cuenta como 'sin regresión' —y no como 'sigue roto'— es un juicio de scope contra la línea base committeada, no un chequeo mecánico."

duration: 14min
completed: 2026-08-27
status: complete
---

# Phase 33 Plan 03: iol + ambito onto the divergence mechanism Summary

**Los dos drivers que ya sobrevivían al modo estricto dejan de clasificar mal: `main_iol.py` deja de
mintear una divergencia de forma como `ERROR-MAP` con título único por probe —el defecto que hacía que
cada corrida viva ensuciara el censo con fids nuevos que `idempotent_by_title` no puede colapsar— y
`main_ambito_financiero.py` deja de tirar a la basura su primer finding de cada corrida. En el camino
aparecieron dos cosas que el plan no había previsto: el lock AST de redacción de iol RECHAZA la forma
de helper que el plan especifica, y `probe_refresh_token` —sin handler amplio, con `IOLDecodeError`
hermano de `IOLAPIError`— era un sitio alcanzable donde el modo estricto mataba el driver en el probe
14 de 15.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-08-27T00:02:18Z
- **Completed:** 2026-08-27T00:16:41Z
- **Tasks:** 2 de 2
- **Files created/modified:** 2 (411 insertions, 106 deletions)

## Accomplishments

- **El criterio 1 queda cubierto en 4 de los 5 drivers.** Con los 22 sitios de este plan, el censo de
  `probe_context` va 46 (matriz) + 19 (higyrus) + 15 (iol) + 7 (ambito) = **87 probes decorados**, cada
  uno con endpoint sin interpolar y superficie explícita.
- **La reclasificación de iol está hecha donde realmente intercepta.** El plan tenía razón sobre el
  diagnóstico: el decorador wrappea desde afuera y el `except Exception` propio del probe atrapa el
  decode error primero, así que un `decode_error=` sobre el decorador habría sido código muerto en este
  archivo. Las 12 ramas van adentro, adelante del handler amplio.
- **`probe_refresh_token` deja de matar el driver.** Es el único sitio alcanzable de `main_iol.py` sin
  handler amplio: su escalera atrapa `IOLAuthError` y `IOLAPIError`, y `IOLDecodeError` cuelga de
  `IOLClientError` como HERMANO de `IOLAPIError`, no como subclase. Bajo modo estricto una divergencia
  en `get_instruments` propagaba, el `sys.excepthook` imprimía el ABORT y los probes 15 y el SUMMARY
  entero no corrían.
- **El allocator de ambito deja de tirar su primer finding.** El único fid committeado del paquete es
  `F-01` con status `EXPECTED` — terminal, es decir el caso peor del short-circuit de preservación de
  `append_finding`: no-op **silencioso** mientras `FINDING=N` lo sigue contando. Con el seed, el primer
  fid de la corrida es `F-02`.
- **El cero de ambito es un número medido.** El pipeline se instala igual, y la no-vacuidad se demostró
  con un record sintético que SÍ llega al handler. Un `DIVERGENCES=0` producido por un pipeline no
  instalado y uno producido por un paquete con cero clases de modelo son indistinguibles sin esto.
- **Los dos archivos canario no se movieron ni un node id.** 19 failed / 3 passed / 19 errors, exacto
  contra `33-BASELINE.md` y contra la medición de 33-02.

## Probes que requirieron `endpoint_scope` (P-5)

Auditado por AST: se listaron, por probe, todas las llamadas a un client function dentro de su cuerpo y
se marcó como caso P-5 todo probe con más de un endpoint distinto.

| Driver | Sitio | Endpoints | Tratamiento |
|---|---|---|---|
| `main_iol.py` | **ningún probe** | — | Los 15 probes llaman a lo sumo un endpoint. El caso que a primera vista parece múltiple no lo es: `probe_get_instruments_by_type_sync` itera 6 `InstrumentType` **contra el mismo** `/api/v2/Cotizaciones/{instrument_type}/{pais}/Todos`. Los 3 probes sin llamada en vivo (`parity_sync_async`, `field_type_map`, `schema_snapshot`) llevan endpoint `"-"`. |
| `main_iol.py` | `_capture_raw_wire` (**no** es un probe; `main()` lo llama fuera de todo `probe_*`) | `get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type` | **El único caso P-5 del plan.** Cada `client._request(spec)` va dentro de `endpoint_scope(_ENDPOINT_TEMPLATES[func_name])`. Sin eso las cuatro capturas quedarían atribuidas a `"-"`. La **superficie** sigue en `"-"` — mismo carry-forward que el capture async de higyrus (33-02 carry-forward 2). |
| `main_ambito_financiero.py` | — | — | **Ninguno.** El paquete tiene **un solo** endpoint (`_ENDPOINT_TEMPLATE`, singular — no es un dict), así que P-5 es estructuralmente inaplicable. |

## Formato exacto del detail determinístico de iol

`_shape_probe_result` compone el detail del `ProbeResult` así (f-string verbatim):

```python
return ProbeResult(probe_name.removeprefix("probe_"), "FINDING", f"SHAPE [{surface}] {detail}")
```

donde `detail` es siempre `_redacted_exc(exc)`, que para un `IOLDecodeError` emite verbatim:

```python
f"IOLDecodeError model={exc.model} path={exc.field_path} "
f"declared={exc.declared_type} observed={exc.observed_type}"
```

Ejemplo medido:

```
SHAPE [sync] IOLDecodeError model=Cotizacion path=.ultimoPrecio declared=float observed=str
```

Propiedades que 33-04 y 33-05 pueden asumir:

- El detail **no contiene el nombre del probe**. Dos probes distintos que golpean la misma
  `(model, field_path, declared, observed)` producen el mismo string módulo la superficie — medido
  entre `probe_get_quote_sync` y `probe_get_quote_async`.
- Se compone **sólo** con los cuatro atributos certificados type-and-path-only por T-29-36, vía el
  único renderer sancionado. Ningún valor del wire puede aparecer ahí (P-01 / T-33-13).
- **Este detail NO es el título del finding.** El título es el del `DivergenceHandler`
  (`{model}{path}: {kind} (declared=…, observed=…) [{surface}]`, convención lockeada
  `surface-in-title-write-new`). El detail es lo que se imprime en la línea `PROBE …` de stdout.

## Formato exacto de la línea SUMMARY (33-04 la parsea)

Los cuatro drivers ya migrados imprimen la MISMA forma:

```
SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N DIVERGENCES=N HANDLER_ERRORS=N
```

f-strings verbatim de este plan:

```python
# main_iol.py
f"SUMMARY: PASS={n_pass} FAIL={n_fail} SKIPPED={n_skip} FINDING={n_find} "
f"DIVERGENCES={len(handler.seen)} HANDLER_ERRORS={len(handler.errors)}"

# main_ambito_financiero.py
f"SUMMARY: PASS={n_pass} FAIL={n_fail} SKIPPED={n_skip} FINDING={n_find} "
f"DIVERGENCES={len(handler.seen)} HANDLER_ERRORS={len(handler.errors)}"
```

Semántica idéntica a la que fijó 33-02: `DIVERGENCES` = `len(DivergenceHandler.seen)` = triples
distintos `(slug, model, field_path, kind)`, **la unidad del censo**; `FINDING` = probes con
`ProbeResult.status == "FINDING"`; `HANDLER_ERRORS` distinto de cero **invalida el censo de esa
corrida**.

## Ramas de decode de iol: 12 escritas, 10 alcanzables

El `<acceptance_criteria>` pide `>= 12` ramas `except IOLDecodeError`. Se escribieron 12. **No son 12
de cobertura**, y decirlo es parte del entregable (P-02):

| Sitio | Alcanzable hoy | Por qué |
|---|---|---|
| `probe_get_quote_sync` / `_async` | sí | `parse_get_quote_response` es `@_decode._response_parser` |
| `probe_get_historical_quotes_sync` / `_async` | sí | vía `_parse_list_or_raise` |
| `probe_get_instruments_sync` / `_async` | sí | vía `_parse_list_or_raise` |
| `probe_get_instruments_by_type_sync` (try principal) | sí | `parse_get_instruments_by_type_response` decorado |
| `probe_get_instruments_by_type_sync` (loop de sanity D-IOL-17) | sí | mismo parser, 6 llamadas |
| `probe_get_instruments_by_type_async` | sí | ídem |
| `probe_refresh_token` | sí | `client.get_instruments("argentina")` |
| `probe_auth_401` | **no** | sólo llama `client.login()`, y `parse_login_response` **no** está decorado con `@_decode._response_parser` |
| `_capture_raw_wire` | **no** | corre `client._request` + `resp.json()`; ningún parser decorado corre acá |

**10 alcanzables, 2 de uniformidad.** Las dos inalcanzables están declaradas como tales en un comentario
en el propio código, no sólo acá. La de `_capture_raw_wire` existe además contra el hazard WR-08 que el
docstring de esa función ya nombraba por su cuenta (un reordenamiento futuro que meta un `from_api` bajo
ese `DecodeScope`).

El plan contaba "12 broad-Exception handlers"; el censo AST real da **11** (10 en probes + 1 en
`_capture_raw_wire`). La doceava rama es `probe_refresh_token`, que no tiene handler amplio y era el
agujero alcanzable — ver Deviations #2.

## Task Commits

1. **Task 1: iol — SHAPE-classify the decode error ahead of the broad handler, decorate 15 probes** — `7b55a56` (feat)
2. **Task 2: ambito — seed the fid allocator, thread the strict flag, decorate 7 probes** — `98ed909` (feat)

## Files Created/Modified

- `main_iol.py` — `divergence_capture` / `endpoint_scope` / `probe_context` al bloque de imports,
  `max_existing_fid` ya estaba; `_STRICT`, `_LOGIN_ENDPOINT`, `_NO_ENDPOINT`, `_shape_probe_result` +
  `_shape_probe_result_pair`, `probe_context` sobre los 15 probes, 12 ramas `except IOLDecodeError`,
  `endpoint_scope` sobre los 4 specs de `_capture_raw_wire`, `strict_decode=_STRICT` en los dos
  constructores, `divergence_capture` alrededor del sweep y la línea SUMMARY extendida.
- `main_ambito_financiero.py` — `divergence_capture` / `probe_context` / `max_existing_fid` a los
  imports, `_STRICT`, `_LOGGER_NAMES`, `_seed_fid_counter()` y su call site entre `write_findings` y el
  primer probe, `probe_context` sobre los 7 probes, `strict_decode=_STRICT` en los dos constructores,
  `divergence_capture` alrededor del sweep y la línea SUMMARY extendida.

## Decisions Made

1. **Los helpers de iol reciben `detail: str`, no la excepción.** Ver Deviations #1 — es la decisión de
   mayor radio del plan y la impone un lock, no una preferencia.
2. **Ninguna rama mintea un finding.** El `<action>` del plan pide un `append_finding(class_="SHAPE")`
   dentro de `_shape_probe_result`. No se hizo: ver Deviations #3.
3. **Endpoint de los probes sin llamada en vivo.** En iol, `"-"` para los 3 (`parity_sync_async`,
   `field_type_map`, `schema_snapshot`) — mismo criterio que 33-02 aplicó a matriz y higyrus. En ambito,
   los 7 bindean el `_ENDPOINT_TEMPLATE` único **siguiendo el `<action>` literal del plan**: con un solo
   endpoint en todo el paquete no existe la atribución errónea que `"-"` previene en los otros drivers.
4. **Superficie de los probes sin sufijo.** Los 5 probes sync de iol sin sufijo (`parity_sync_async`,
   `field_type_map`, `schema_snapshot`, `refresh_token`, `auth_401`) y los 5 de ambito reciben `"sync"`,
   que es la superficie que su código realmente ejercita y la que sus propios `append_finding` ya
   declaran.
5. **`_RESIDUAL_PROBE_EXCEPTIONS` no se tocó en ninguno de los dos drivers** (iol no tiene esa tupla;
   ambito tampoco). Ninguna copia de `_decode.py` se editó — `check_decode_intactness.py` exit 0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] La firma de helper que el plan especifica ROMPE dos locks AST de `main_iol.py`**

- **Found during:** Task 1, al correr `pytest verification/ -q -k "iol and (redact or exc or crash)"`
- **Issue:** El plan especifica `_shape_probe_result(name: str, surface: str, exc: IOLDecodeError)`.
  Implementado así, **3 tests fallan**:
  `test_the_driver_declares_exactly_one_exception_renderer`,
  `test_the_census_detects_the_sanctioned_renderer_in_the_real_driver` y
  `test_no_except_handler_in_the_driver_renders_its_exception_raw`.
  Dos detectores independientes lo rechazan por dos vías distintas:
  (a) `_declared_exception_renderers` marca como renderer toda función con un parámetro anotado con un
  tipo de excepción cuyo cuerpo lo **lee o lo delega a un callee no sancionado**
  (`_CENSUS_SANCTIONED_DELEGATES = ("_redacted_exc", "type", "isinstance")`) — así que
  `_shape_probe_result_pair`, que le pasa la excepción a `_shape_probe_result`, aparecía como
  **segundo renderer** y el assert por igualdad contra `["_redacted_exc"]` fallaba;
  (b) `_raw_exception_renders` regla 5 marca **toda** delegación del nombre bindeado por un
  `except` a un callee fuera de `_SANCTIONED_DELEGATES`, así que las 12 ramas nuevas eran 12
  ofensas. Los tres tests son criterio de aceptación explícito de la Task 1, y `<files>` de la task
  es sólo `main_iol.py`: aflojar el lock no era una opción disponible (y habría sido exactamente el
  antipatrón de "encoger el censo para que entre").
- **Fix:** Los dos helpers reciben `detail: str` — texto YA renderizado — y cada uno de los 12 sitios
  llama `_shape_probe_result_pair("x", "sync", _redacted_exc(exc))`. `_redacted_exc` está sancionado en
  los dos detectores, y una llamada anidada como argumento es un `ast.Call`, no un `ast.Name`, así que
  la regla 5 no la ve. **El driver ya tenía escrito este patrón**: `_emit_crash_report(detail, tb)`, cuyo
  docstring desde 30-12 dice literalmente *"Por qué recibe texto ya renderizado y no la excepción. Un
  helper que tomara la excepción se volvería un segundo renderer bajo el censo de AD-30-09-01"*. El fix
  es extender ese contrato del camino de crash al camino atrapado, no inventar uno.
- **Files modified:** `main_iol.py`
- **Verification:** `uv run pytest verification/ -q -k "iol and (redact or exc or crash)"` → 66 passed.
- **Committed in:** `7b55a56`

---

**2. [Rule 2 - Missing critical] `probe_refresh_token` mataba el driver bajo modo estricto y el plan no lo cubría**

- **Found during:** Task 1, al auditar por AST qué probes pueden levantar `IOLDecodeError`
- **Issue:** El plan enumera los sitios a parchear por sus handlers amplios (`429, 567, 654, 730, 809,
  873, 936, 1019, 1043, 1144` y siblings). `probe_refresh_token` **no está** en esa lista porque no
  tiene handler amplio — su escalera es `IOLAuthError` → `IOLAPIError` y nada más. Pero llama
  `client.get_instruments("argentina")`, cuyo parser SÍ está decorado con `@_decode._response_parser`,
  y `IOLDecodeError` **no es subclase de `IOLAPIError`**: los dos cuelgan de `IOLClientError` como
  hermanos (el docstring de `exceptions.py:27` lo dice explícitamente). Bajo `MARKET_LIBS_STRICT_DECODE=1`
  una divergencia en `get_instruments` propagaba fuera del probe 14, el `sys.excepthook` imprimía el
  ABORT y **el probe 15 y la línea SUMMARY entera no corrían** — es decir, el driver perdía su censo
  completo. Exactamente el modo de falla que este plan existe para eliminar, en el único sitio que el
  plan no miraba.
- **Fix:** Rama `except IOLDecodeError` al final de la escalera de `probe_refresh_token`, devolviendo
  `_shape_probe_result("refresh_token", "sync", _redacted_exc(exc))`.
- **Files modified:** `main_iol.py`
- **Verification:** falsificación con cliente falso — `probe_refresh_token` devuelve
  `ProbeResult(refresh_token, FINDING, "SHAPE [sync] IOLDecodeError model=Instrumento path=.pais
  declared=str observed=NoneType")` en vez de propagar.
- **Committed in:** `7b55a56`

---

**3. [Rule 1 - Bug] El `<action>` pide mintear un finding `SHAPE` que duplicaría el que el handler ya escribió**

- **Found during:** Task 1, contrastando el `<action>` contra el contrato lockeado de 33-01
- **Issue:** El `<action>` dice que `_shape_probe_result` *"allocates a fid, calls `append_finding(_PKG,
  …, class_="SHAPE", …, idempotent_by_title=True, …)`"*. Pero `33-01-SUMMARY.md` fija lo contrario y por
  escrito: *"`on_decode_error` NO debe escribir un finding. El `SHAPE` ya lo escribió el handler desde el
  record que `_decode` emitió justo antes de levantar. Mintear uno acá duplicaría la divergencia bajo
  otro título y rompería el `idempotent_by_title` del lock 10 (D-07)"*. El argumento vale idéntico acá:
  el punto de interceptación cambió (rama inline en vez de decorador) pero el orden de eventos no —
  `_decode` **emite el record y después levanta**, así que para cuando la rama corre el `DivergenceHandler`
  ya escribió el `SHAPE` bajo el título determinístico de la convención lockeada. Un segundo
  `append_finding` produciría dos findings por divergencia bajo dos títulos distintos, que es
  precisamente el defecto que el plan enuncia como su propio motivo de existir.
- **Fix:** Ninguna de las 12 ramas escribe un finding; sólo traducen la excepción a la forma canónica de
  retorno del probe. Es además lo que hacen los helpers homónimos de matriz y higyrus (33-02).
- **Files modified:** `main_iol.py`
- **Verification:** `git status --porcelain .planning/verification/` vacío después de las 5
  falsificaciones conductuales, ninguna de las cuales escribió un finding.
- **Committed in:** `7b55a56`

---

**4. [Rule 2 - Missing critical] `_capture_raw_wire` toca 4 endpoints y ninguna divergencia suya quedaba bindeada**

- **Found during:** Task 1, en la auditoría P-5 que el plan pide
- **Issue:** `main()` llama `_capture_raw_wire(client, today)` **fuera de todo `probe_*`**, así que el
  `ContextVar` de endpoint valía `"-"` durante sus cuatro `_request`. El plan lo nombra como "the obvious
  candidate" para `endpoint_scope` pero no lo enumera entre los sitios a parchear.
- **Fix:** Cada `client._request(spec)` va dentro de
  `endpoint_scope(_ENDPOINT_TEMPLATES[func_name])`. La **superficie** sigue en `"-"` — `endpoint_scope`
  re-bindea sólo el endpoint y `verification/divergences.py` no expone un `surface_scope`; ver
  carry-forward 2.
- **Files modified:** `main_iol.py`
- **Verification:** `uv run ruff check .`, `uv run mypy` y `uv run pytest packages/iol-client -q`
  (272 passed) verdes.
- **Committed in:** `7b55a56`

---

**Total deviations:** 4 auto-fixed (1× Rule 1, 2× Rule 2, 1× Rule 3)
**Impact on plan:** Ninguno sobre el scope. La #1 es de forma, no de función: el entregable declarado se
cumple, con la firma que los locks del driver admiten. La #2 y la #4 son requisitos de corrección — sin
la #2 el entregable *"iol clasifica una divergencia de decode como SHAPE"* sería falso en un sitio
alcanzable donde el driver directamente muere. La #3 evita romper el `idempotent_by_title` que el plan
existe para habilitar. Cero scope creep: no se tocó ninguna copia de `_decode.py`, ni `models.py` de
ambito, ni ninguno de los 6+11 handlers amplios pre-existentes (no se agregó ni se quitó ninguno), ni
ninguna de las 19 fallas pre-existentes de `verification/`, ni ninguno de los 43 errores pre-existentes
de `uv run mypy verification`.

## Issues Encountered

- **Ninguna de las dos tasks admite un RED de archivo de test nuevo.** Los `<files>` de ambas son sólo
  el driver, y el gate a nivel driver (`verification/test_probe_context_coverage.py`,
  `test_finding_count_consistency.py`) está asignado al plan 33-04 desde el carry-forward 2 de
  `33-01-SUMMARY.md`; crearlo acá habría colisionado. Mismo precedente que 33-02: el RED es el **censo
  AST del propio `<acceptance_criteria>`**, corrido antes del cambio — `main_iol.py` 15 probes / 15 sin
  decorar / 0 ramas de decode (exit 1) y `main_ambito_financiero.py` 7 / 7 sin decorar (exit 1).
  Post-cambio, ambos exit 0.
- **El plan cuenta 12 handlers amplios en `main_iol.py`; el censo AST da 11.** No es una discrepancia
  material —las líneas que el plan enumera existen todas— pero la doceava rama de decode no podía salir
  de un handler amplio inexistente. Salió de `probe_refresh_token` (Deviations #2), que además era el
  sitio que hacía falta arreglar de verdad.
- **Una corrida de verificación conductual ensució `.planning/verification/iol-client-findings.md`.**
  El experimento de binding de `ContextVar` levantaba un `RuntimeError` (no un `IOLDecodeError`), así que
  cayó en el handler amplio y `append_finding` corrió de verdad. Revertido con `git checkout --` sobre
  ese único archivo; `git status --porcelain .planning/verification/` quedó vacío antes de ambos commits.
  Los experimentos con `IOLDecodeError` no escriben, que es precisamente el contrato de
  `_shape_probe_result`.

## Carry-forwards

1. **La superficie de `_capture_raw_wire` queda en `"-"`.** `endpoint_scope` re-bindea el endpoint pero
   no la superficie. **No es un hueco del censo**: `handler.seen` se indexa por
   `(slug, model, field_path, kind)`, sin endpoint ni superficie. El efecto es una variante de título
   `[-]` que ensucia la identidad de dedupe, exactamente igual que el capture async de higyrus.
   Destino: **plan 33-04**, junto con el mismo caso de higyrus — se decide una sola vez si agregar
   `surface_scope` a `verification/divergences.py`.
2. **El gate de P-3 a nivel driver sigue pendiente para ambito.** `_seed_fid_counter` existe y funciona
   (0 → 1 → `F-02`, verificado, más el orden AST `write_findings` < seed < primer probe verificado a
   mano), pero ningún test lo asevera como sí hace `verification/test_main_iol_fid_seed.py` para iol.
   Destino: **plan 33-04**, que ya arrastra matriz y higyrus por lo mismo; ambito completa la lista de
   los cuatro drivers a espejar.
3. **`main_market_data.py` es el quinto driver y NO está en este plan ni en 33-02.** Los 87 probes
   decorados salen de cuatro drivers; el censo de 130 probes que 33-05 va a gatear incluye los de
   market-data. Ese driver ya tiene `_seed_fid_counter` (es el original del que iol lo copió) pero
   todavía no tiene `probe_context` ni `strict_decode`.
4. **La rama de decode de `probe_auth_401` y la de `_capture_raw_wire` son inalcanzables hoy** y así
   están declaradas en comentarios en el código. Si una fase futura decora `parse_login_response` con
   `@_decode._response_parser`, la primera pasa a alcanzable sin ningún cambio; la segunda depende del
   hazard WR-08.
5. **`33-BASELINE.md` sigue siendo el único árbitro del rojo de `verification/`.** Los planes que sigan
   deben re-correr los mismos dos archivos canario y comparar contra 17/17 y 2/2. Un número distinto no
   es "más del rojo que ya estaba".

## Known Stubs

Ninguno. Los 22 decoradores están cableados a fuentes reales: el endpoint sale de los
`_ENDPOINT_TEMPLATES` / `_ENDPOINT_TEMPLATE` que los drivers ya usaban para sus snapshots, la superficie
del sufijo real de cada función, y el `next_fid` del allocator real de cada driver. El endpoint `"-"` de
los 3 probes de iol sin llamada en vivo no es un placeholder pendiente de cablear: es el valor que
significa "ningún endpoint bindeado", y esos probes efectivamente no tocan ninguno. Las 2 ramas de
decode inalcanzables no son stubs sino uniformidad declarada — están contadas por separado en la tabla
"12 escritas, 10 alcanzables" y anotadas como tales en el propio código.

## TDD Gate Compliance

| Gate | Evidencia |
|---|---|
| RED (Task 1) | Censo AST pre-cambio sobre `main_iol.py`: `total probes: 15 \| undecorated: 15 \| decode branches: 0`, exit 1, con los 15 nombres impresos. |
| GREEN (Task 1) | `7b55a56`. Censo AST post-cambio: `probes 15 undecorated [] decode branches 12`, exit 0. Falsificación conductual del seam en las 5 formas de retorno. Los 3 tests de lock AST que el primer draft enrojeció, verdes. |
| RED (Task 2) | Censo AST pre-cambio sobre `main_ambito_financiero.py`: `probes: 7 undecorated: 7`, exit 1. `grep -c '_seed_fid_counter\|strict_decode=_STRICT'` → 0. |
| GREEN (Task 2) | `98ed909`. Censo AST post-cambio: `undecorated []`, exit 0. Seed `0 → 1 → F-02`, orden AST verificado, no-vacuidad del handler demostrada con un record sintético. |

**Sin commit `test(...)` separado, deliberadamente:** igual que en 33-02, el gate de este plan es la
consulta AST escrita en su propio `<acceptance_criteria>`, no un archivo de test nuevo — que habría
colisionado con `verification/test_probe_context_coverage.py`, asignado al plan 33-04. Fabricar un
`test(...)` vacío para satisfacer la forma del gate habría sido justamente un verde producido por una
señal que no inspecciona nada. Sin fase REFACTOR: no hizo falta.

## Verification Evidence

| Gate | Resultado |
|---|---|
| Censo AST `probe_context` + ramas de decode — `main_iol.py` | `undecorated: []`, `decode branches: 12`, exit 0 |
| Censo AST `probe_context` — `main_ambito_financiero.py` | `undecorated: []`, exit 0 |
| `grep -v '^#' main_iol.py \| grep -c 'probe_context('` | 15 (= 15 requerido) |
| `grep -cE '^(async )?def probe_' main_iol.py` | 15 |
| `grep -v '^#' main_iol.py \| grep -c 'strict_decode=_STRICT'` | 2 |
| `grep -v '^#' main_iol.py \| grep -c '_shape_probe_result'` | 14 (>= 13 requerido) |
| `grep -v '^#' main_iol.py \| grep -c 'divergence_capture('` | 1 |
| `grep -v '^#' main_iol.py \| grep -c 'endpoint_scope('` | 1 (`_capture_raw_wire`, P-5) |
| `grep -v '^#' main_ambito_financiero.py \| grep -c 'probe_context('` | 7 (= 7 requerido) |
| `grep -cE '^(async )?def probe_' main_ambito_financiero.py` | 7 |
| `grep -v '^#' main_ambito_financiero.py \| grep -c '_seed_fid_counter'` | 4 (>= 2 requerido) |
| `grep -v '^#' main_ambito_financiero.py \| grep -c 'strict_decode=_STRICT'` | 2 |
| `grep -v '^#' main_ambito_financiero.py \| grep -c 'max_existing_fid('` | 1 |
| `uv run pytest verification/ -q -k uses_single_client_instance` | 6 passed (iol + ambito + los otros drivers) |
| `uv run pytest verification/ -q -k "iol and (redact or exc or crash)"` | 66 passed — AD-30-09-01 y los locks de crash-path verdes |
| `uv run pytest verification/test_main_iol_fid_seed.py test_main_iol_raw_wire_drift.py test_main_iol_exception_redaction.py test_main_ambito_financiero_uses_single_client_instance.py test_main_drivers_bare_except.py test_logging_root_unchanged.py test_divergences.py -q` | 101 passed |
| `uv run pytest packages/iol-client -q` | 272 passed |
| `uv run pytest packages/ambito-financiero-client -q` | 203 passed, 1 deselected |
| `uv run pytest packages -q` (equivalente CI) | 1736 passed, 1 deselected |
| `uv run pytest verification/test_matriz_sweep_snapshot.py test_main_matriz_login_fail_uniformity.py -q` | `19 failed, 3 passed, 19 errors` — idéntico al baseline, sin deltas |
| `uv run python tools/check_decode_intactness.py` | exit 0 — Checks A/B/C/D verdes, ninguna copia de `_decode.py` tocada |
| `uv run python tools/check_surface_types.py` | exit 0 — 0 violaciones |
| `uv run python tools/check_uniform_structure.py` | exit 0 |
| `uv run mypy` | Success: no issues found in 75 source files |
| `uv run mypy verification` | 43 errores pre-existentes en 8 archivos; **0** de los dos drivers de este plan |
| `uv run ruff check . && uv run ruff format --check .` | limpio, 245 archivos formateados |
| Premisa D-12 (`ambito_financiero_client.models`) | 0 `ClassDef` — re-verificado por AST |
| Seed de fids de ambito | `_fid_counter` 0 → `_seed_fid_counter()` → 1 → `_next_fid()` = `F-02` |
| Orden AST en `main()` de ambito | `write_findings`@773 < `_seed_fid_counter`@780 < primer probe@796 |
| No-vacuidad del handler de ambito | logger NOTSET → INFO dentro del CM, record sintético capturado (`seen` con 1 triple, `errors` vacío), nivel y handlers restaurados al salir |
| Interceptación de decode (iol, 5 formas) | 2-tuple sync / 2-tuple async / bare sync ×2 / loop de sanity → todas `FINDING`, driver sobrevive |
| Determinismo del detail cross-probe | `probe_get_quote_sync` y `probe_get_quote_async` sobre la misma divergencia → detail idéntico módulo la superficie |
| Endpoint sin interpolar | `probe_get_quote_sync` ve `/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion`; `probe_happy_sync` ve `/dolarnacion/historico-general/{from}/{to}` |
| Reset de `ContextVar` post-probe | `_ENDPOINT` y `_SURFACE` vuelven a `"-"` en los dos drivers |
| `git status --porcelain .planning/verification/` | vacío antes de ambos commits |

## Self-Check: PASSED

- Los 2 archivos declarados en `key-files.modified` existen en disco.
- Los 2 hashes de commit declarados (`7b55a56`, `98ed909`) existen en `git log`.
- El formato de la línea SUMMARY y el del detail determinístico citados arriba están copiados
  **verbatim** del código de los dos drivers, no parafraseados — 33-04 los parsea desde ahí.
- El set del canario está medido en esta misma sesión con el mismo comando, no citado de
  `33-BASELINE.md`.
- **`LIVE-TYP-01` queda deliberadamente en `Pending`.** Los siete planes de la Phase 33 cargan ese ID
  en su frontmatter; cerrarlo en el plan 3 de 7 sería una completitud falsa — este plan no entrega
  nada de su scope declarado (ni corrida en vivo, ni evidencia de `Literal`, ni cycle closure).
  Mismo precedente que 33-01 (deviation #4) y que la Phase 32 con GATE-TYP-01. Queda para 33-07.
