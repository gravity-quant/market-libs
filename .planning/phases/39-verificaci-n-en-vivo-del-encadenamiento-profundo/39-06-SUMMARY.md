---
phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo
plan: 06
subsystem: testing
tags: [deep-chain, null-object, ast-lock, matriz, venue-segregation, schema-baseline, zero-http, ci]

# Dependency graph
requires:
  - phase: 39-01
    provides: "_VENUE_ALLOWLIST + _venue_token() — la única fuente de verdad de venues, reutilizada como clave de nombre de baseline"
  - phase: 39-03
    provides: "Wave 2 — precondición de orden de olas"
  - phase: 39-05
    provides: "verification/test_main_higyrus_deep_chain.py — la variante hermana recién aterrizada (test de cero-HTTP-adicional) y la ubicación real de la allowlist (step de driver locks del job `lint`)"
  - phase: 36-...
    provides: "verification/test_main_market_data_deep_chain.py — el analog exacto (_protected_node_ids, piso por probe WR-06, los MISMOS seis nombres de alias)"
  - phase: 37-...
    provides: "MarketDataSnapshot con las 6 propiedades alias (NOBJ-MTZ-02, D-16) invisibles al walker"
  - phase: 39-02
    provides: "packages/matriz-client/tests/test_deep_chain_edges.py — la semántica de borde de los 6 alias con mercado cerrado, pinneada sobre el baseline committeado"
provides:
  - "verification/test_main_matriz_deep_chain.py — lock AST de los 6 alias en los 2 probes de market data de matriz, en la allowlist de CI"
  - "main_matriz.py gasta los 6 alias en sync (MarketDataSnapshot.from_api sobre el payload en mano) y en async (snapshot tipado de AsyncClient.get_market_data), ambos dentro del cuerpo de un try"
  - "probe_get_market_data_async con cuerpo propio: deja de delegar en _ainvoke, que descartaba el resultado"
  - "Baselines de schema de matriz segregados por venue (<slug>.<venue>.json); los 8 de remarkets renombrados sin tocar contenido"
  - "Test AST de que el driver NO importa ws_client — la lectura REST+WS de 'ambas superficies' queda estructuralmente prohibida"
affects: [39-07, 39-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Baseline write-once keyeado por (func_name, venue): el token sale del allowlist cerrado, nunca de un fragmento de la URL de entrada"
    - "Lock AST con raíz de cadena en un ast.Name local (no en un Attribute intermedio) para modelos cuyos alias cuelgan directo del objeto"
    - "Lock de EXACTAMENTE 1 llamada emisora de HTTP por probe: prohíbe el round trip extra en sync y a la vez exige que async obtenga su objeto del cliente tipado"
    - "Cuando el probe sostiene UN objeto y no una colección, el test WR-06 de colecciones se reemplaza por 'cada alias gastado al menos una vez en cada probe'"

key-files:
  created:
    - verification/test_main_matriz_deep_chain.py
  modified:
    - main_matriz.py
    - .github/workflows/ci.yml
    - packages/matriz-client/src/matriz_client/models.py
    - packages/matriz-client/tests/test_deep_chain_edges.py
  renamed:
    - ".planning/verification/schemas/matriz-client/*.json → *.remarkets.json (8 archivos, renombre puro)"

key-decisions:
  - "El probe async recibe CUERPO PROPIO en vez de extender _ainvoke con un consumidor: el helper genérico es compartido por ~16 probes de paridad y agregarle un parámetro de consumo habría cambiado una firma que 16 sitios usan para ganar un solo caso; el mapeo de excepciones se replicó byte-paralelo (misma familia, mismo orden, mismos títulos, mismo nombre de probe)"
  - "MatrizDecodeError NO se captura localmente: no es subclase de PrimaryAPIError ni de nada en _RESIDUAL_PROBE_EXCEPTIONS, así que un raise de modo estricto desde from_api sigue viajando al decorador probe_context (on_decode_error=_shape_probe_result_pair) y produce el finding SHAPE de siempre, sin doble emisión"
  - "El try de la cadena sync es NUEVO, no el existente: el try original sólo envuelve _sync_matriz_request y la extracción del sub-dict marketData vive fuera; la condición dura (toda desreferencia en el CUERPO de un try) se cumple"
  - "La rama de FINDING de la cadena sync devuelve `md`, no None: el payload crudo se obtuvo bien y sigue siendo válido para el mapa de tipos y el snapshot de schema — sólo la cadena tipada falló"
  - "El nombre del dict se conserva como _SCHEMA_FILES aunque sus valores ahora sean slugs: renombrarlo habría obligado a tocar verification/test_main_matriz_schema_snapshot_alignment.py, que el plan pide mantener sin churn"
  - "El nombre de venue es <slug>.<venue>.json, con el token resuelto por _venue_token sobre la base_url que _write_or_check_schema YA recibe — sin segunda tabla de venues"
  - "Un hostname fuera del allowlist cae en el literal _VENUE_SENTINEL en vez de lanzar: camino inalcanzable en producción (el gate D-MATZ-33 sale antes), pero fail-safe y no fail-hard"
  - "El nombre local del snapshot es `snapshot` en AMBAS superficies, a propósito: una asimetría de nombres exigiría dos raíces de cadena y dejaría una superficie fuera de la vista del guard"

patterns-established:
  - "Cada archivo nuevo bajo verification/ entra a la allowlist de ci.yml en el MISMO commit que lo vuelve verde (no en el commit RED)"
  - "Una consecuencia querida de un cambio de artefacto se escribe en el sitio de código que la produce, con destino explícito al censo"

requirements-completed: [LIVE-NOBJ-01]

# Metrics
duration: 6min
completed: 2026-08-30
status: complete
---

# Phase 39 Plan 06: Los 6 alias de `MarketDataSnapshot` en las dos superficies de matriz + baselines segregados por venue Summary

**Un lock AST que exige que los dos probes de market data de `main_matriz.py` gasten los seis alias de la Phase 37 (`last`, `bids`, `offers`, `settlement`, `close`, `open_interest`) en sus dos superficies REALES —`client.py` y `aio.py`, no REST+WS— dentro del cuerpo de un `try` y sin costar una sola llamada HTTP adicional; más la segregación por venue de los baselines write-once de schema, que aterriza ANTES de la primera corrida bbsa para que ésta capture líneas base frescas en vez de emitir hasta 8 findings `SHAPE OPEN` que describirían una diferencia entre venues.**

## Performance

- **Duration:** ~6 min
- **Tasks:** 3 (1 RED, 1 GREEN, 1 refactor de artefacto)
- **Files modified:** 5 (1 creado, 4 modificados) + 8 renombrados

## Accomplishments

- **La premisa vencida de CONTEXT quedó cerrada con un test, no con una nota.** `39-CONTEXT.md` justificaba D-05 diciendo que `matriz_client` no tiene `aio.py` y que por eso "ambas superficies" debía leerse REST + WebSocket. HEAD lo falsifica: `aio.py` existe con un `AsyncClient` completo cuyo `get_market_data` devuelve `MarketDataSnapshot` tipado, el driver ya corre ~19 probes async e importa `ws_client` **cero** veces. `test_the_driver_never_imports_ws_client` congela ese hecho por AST, así que un lector futuro que encuentre sólo la frase vencida no puede "restaurar" una superficie WS sin poner un test en rojo. **La decisión D-05 quedó intacta; sólo su justificación estaba vencida, y este plan no propone ningún camino WS.**
- **La mitad async era el gap real, y era invisible.** `probe_get_market_data_async` delegaba en `_ainvoke`, el helper genérico que mapea excepciones y **descarta el resultado**: la llamada tipada se hacía, el `MarketDataSnapshot` se construía, y se tiraba sin desreferenciar un solo alias mientras el probe reportaba PASS. Ahora el probe tiene cuerpo propio y gasta los seis.
- **La cadena sync es gratis por razones estructurales.** `MarketDataSnapshot.from_api(md)` sobre el sub-dict `marketData` ya obtenido es literalmente el mismo constructor que `_core.parse_get_market_data_response` invoca sobre el mismo sub-dict: mismo walker, mismo sink, mismo contexto de decode estricto. `test_neither_probe_adds_an_http_call` exige **exactamente una** llamada emisora de request por probe, lo que corta dos derivas opuestas a la vez — que alguien "arregle" la cadena sync con un segundo round trip (duplicando el request del concepto market-data y la emisión de divergencias), y que alguien reconstruya el snapshot async desde un payload que el probe nunca pidió.
- **Los seis alias no pueden mover el conteo de divergencias, y eso está escrito en el sitio.** Son propiedades de sólo lectura, invisibles a `typing.get_type_hints` y a `dataclasses.fields` (Phase 35 criterio 5, D-16) y por lo tanto invisibles a `_decode.walk_model`. El comentario junto a las desreferencias lo dice con esas palabras, para que la lectura del censo no le atribuya a esta cadena un cambio de números que estructuralmente no puede causar.
- **La segregación por venue aterrizó ANTES de que corra bbsa.** Hasta HEAD el baseline se elegía **sólo** por nombre de función; `base_url` viajaba dentro del sobre pero no formaba parte de la clave. Con D-25 (no sobrescribir un baseline que difiere), la primera corrida contra bbsa habría diffeado formas de bbsa contra líneas base capturadas contra remarkets el 2026-06-10 y emitido hasta 8 findings `SHAPE OPEN` describiendo una diferencia **entre venues**, no un defecto del cliente — exactamente el ruido que SC-4 existe para evitar. Ahora el nombre es `<slug>.<venue>.json` y esa primera corrida captura lo suyo.
- **Los 8 baselines de remarkets sobrevivieron intactos.** `git mv` puro: el commit reporta **0 líneas agregadas y 0 borradas** en los ocho archivos. Siguen siendo válidos para una futura corrida contra remarkets.

## Task Commits

1. **Task 1 (RED): lock AST de los 6 alias de `MarketDataSnapshot`** — `d318a5f` (test)
2. **Task 2 (GREEN): los 6 alias en sync y async + cableado a CI** — `ef5296a` (feat)
3. **Task 3: segregar por venue los baselines write-once de schema** — `ffbdb75` (refactor)

_TDD: RED verificado antes del GREEN — **5 failed / 3 passed**… en rigor **5 failed / 4 passed**. Los 4 verdes son los que no dependen de la cadena: presencia de los dos probes por nombre, el gate de `try` (vacuamente cierto sin accesos), la ausencia de import de `ws_client` (la propiedad ya valía; el lock la congela) y el de exactamente-1-HTTP (ídem). Los 5 rojos nombraron el probe sync sin `MarketDataSnapshot.from_api`, los dos probes sin desreferencia, el agregado (0 de 12), el piso por probe (0 de 6 cada uno) y los 12 pares (probe, alias) sin gastar. Tras el GREEN: 9 passed._

## Files Created/Modified

- **`verification/test_main_matriz_deep_chain.py`** (nuevo, 9 tests, ~390 líneas). Constantes: `_DRIVER` = `main_matriz.py`; `_ALIAS_NAMES` = los seis nombres **copiados verbatim** del analog de market-data; `_READ_PROBES` = los dos probes; `_SNAPSHOT_LOCAL = "snapshot"`; `_MIN_CHAINED_ACCESSES_BY_PROBE = {sync: 6, async: 6}` con `_MIN_CHAINED_ACCESSES = sum(...)`; `_TYPED_CONSTRUCTOR = ("MarketDataSnapshot", "from_api")` restringido a `_TYPED_CONSTRUCTOR_PROBES` (sólo el sync — el async recibe el objeto ya tipado); `_HTTP_CALL_NAMES` + `_HTTP_CALLS_PER_PROBE = 1`; `_FORBIDDEN_IMPORT = "ws_client"`. `_protected_node_ids` copiado verbatim del analog; `_chain_rooted_at` es **nuevo** (ver Decisions). El driver se `ast.parse`-a, nunca se importa.
- **`main_matriz.py`**:
  - `probe_get_market_data` — bloque nuevo entre la rama de forma incorrecta y la guarda de antigüedad: `snapshot = MarketDataSnapshot.from_api(md)` + las seis desreferencias (`snapshot.last.price`, `len(snapshot.bids)`, `len(snapshot.offers)`, `snapshot.settlement.price`, `snapshot.close.price`, `snapshot.open_interest.size`) dentro del cuerpo de un `try` propio, con `except _RESIDUAL_PROBE_EXCEPTIONS` → `append_finding(class_="ERROR-MAP")` y `ProbeResult(..., "FINDING", ...)` devolviendo `md`. El detalle de PASS incorpora los seis valores.
  - `probe_get_market_data_async` — cuerpo propio: mismos gates de SKIPPED, `try` con `await aclient.get_market_data(...)` + las mismas seis desreferencias, y las dos ramas de `except` (`PrimaryAPIError` primero, `_RESIDUAL_PROBE_EXCEPTIONS` después) replicadas byte-paralelo a `_ainvoke`. Detalle de PASS simétrico al sync.
  - `_SCHEMA_FILES` — de `dict[str, Path]` (17 rutas completas) a `dict[str, str]` (17 slugs). Claves sin cambios.
  - `_schema_path(func_name, base_url)` — **función nueva**: `_SCHEMA_DIR / f"{slug}.{venue}.json"` con `venue = _venue_token(base_url) or _VENUE_SENTINEL`. Su docstring es el sitio donde vive la explicación de la segregación, con destino explícito al censo del 39-08.
  - `_VENUE_SENTINEL = "unknown-venue"` — literal cerrado para el camino inalcanzable.
  - `_write_or_check_schema` — una línea: `file_path = _schema_path(func_name, base_url)`. La política D-25 y la forma del sobre quedan intactas.
- **`.github/workflows/ci.yml`** — `verification/test_main_matriz_deep_chain.py` agregado a la lista explícita del step "driver locks" del job `lint` (ahora 11 archivos).
- **`.planning/verification/schemas/matriz-client/`** — los 8 archivos renombrados a `*.remarkets.json` con `git mv`, contenido byte-idéntico.

## Decisions Made

- **`_chain_rooted_at` es nuevo, y tenía que serlo.** Los dos locks hermanos usan `_chain_reaches(node, attribute)` porque sus cadenas pasan por un **Attribute** intermedio (`.market_data`, `.parking`). Los seis alias de matriz cuelgan **directo** del snapshot, así que la raíz de la cadena es un `ast.Name` y una caminata que busca un atributo nunca habría matcheado — el lock habría sido silenciosamente vacuo. La función nueva camina `Attribute` / `Subscript` / `Call` hasta el `Name` y compara el identificador.
- **El test de colecciones del analog se reemplazó, no se omitió.** `_CHAINED_COLLECTIONS_BY_PROBE` existe en los dos hermanos porque sus probes traen **colecciones** de wrappers y una segunda colección podría consumirse con `len()` sola (WR-06). Los probes de matriz traen **un** snapshot: ese test no tiene sujeto acá. En su lugar, `test_every_alias_is_spent_in_every_probe` assertea la propiedad que sí está en riesgo para una cadena de objeto único — que los seis nombres aparezcan al menos una vez en **cada** probe, de modo que ninguno alcance su piso de 6 desreferenciando `last` seis veces y dejando `open_interest` sin ejercitar. La decisión está escrita en el docstring del módulo y en el del test, como pedía el plan.
- **Cuerpo propio para el probe async, no un consumidor en `_ainvoke`.** El plan autorizaba cualquiera de las dos. `_ainvoke` lo comparten ~16 probes de paridad: agregarle un parámetro de consumo habría cambiado una firma usada por 16 sitios para ganar un solo caso. El costo del cuerpo propio es la duplicación del mapeo de excepciones, y se pagó de forma literal — misma familia, mismo orden (`PrimaryAPIError` antes que `_RESIDUAL_PROBE_EXCEPTIONS`, que lo contiene), mismos títulos con el prefijo `aio.`, mismo `surface="async"`, mismo nombre de probe (clave de findings).
- **`MatrizDecodeError` no se captura localmente, a propósito.** Es subclase de `MatrizClientError` y **no** de `PrimaryAPIError`, así que no está en `_RESIDUAL_PROBE_EXCEPTIONS`. Un raise de modo estricto desde `from_api` sigue viajando al decorador `probe_context(..., on_decode_error=_shape_probe_result_pair)` y produce el finding `SHAPE` de siempre. Capturarlo acá habría minteado un segundo finding bajo otro título. Misma decisión que 39-05.
- **El discriminador de mercado cerrado no se tocó (D-12).** La guarda de antigüedad de `LA.date` sigue siendo el **único**. Los seis valores de la cadena se **reportan** en el detalle del `ProbeResult`; no se usan para clasificar nada. Hay un comentario en el sitio que lo dice.
- **La rama de FINDING de la cadena sync devuelve `md`.** El payload crudo se obtuvo bien y `main()` lo usa para el mapa de tipos y el snapshot de schema; sólo la cadena tipada falló. Devolver `None` habría descartado una captura válida por un defecto en una observación posterior a la captura.
- **`_SCHEMA_FILES` conserva su nombre.** Sus valores ahora son slugs, no rutas, pero renombrarlo a `_SCHEMA_SLUGS` habría obligado a tocar `verification/test_main_matriz_schema_snapshot_alignment.py`, que itera `main_matriz._SCHEMA_FILES` y que el plan pide dejar sin churn. El comentario del dict dice explícitamente que los valores son slugs y remite a `_schema_path`.
- **El sobre no cambió de forma.** `base_url` sigue registrándose adentro; ahora además es parte de la clave del nombre, lo que hace el artefacto autoconsistente (el archivo dice contra qué venue se capturó, y su nombre también).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tres citas de provenance apuntando a archivos que el renombre acababa de eliminar**

- **Found during:** Task 3
- **Issue:** Tres comentarios/docstrings dentro de `packages/matriz-client/` citan baselines de matriz por su ruta exacta como fuente de sus constantes: `models.py:569` (`TickPriceRange`, provenance D-04a) y `tests/test_deep_chain_edges.py:31` y `:66` (el payload de la suite mockeada del plan 39-02, que es el baseline committeado copiado verbatim). Tras el `git mv` esas tres rutas ya no existían. Ninguna es una lectura de archivo —son prosa— así que nada se rompió, pero quedaban como referencias colgantes: la misma clase de deuda que el plan 39-01 encontró y arregló bajo Rule 2 (fuente que contradice su propio comportamiento).
- **Fix:** Las tres citas se actualizaron al nombre nuevo (`*.remarkets.json`). Cero cambios de código o de datos.
- **Files modified:** `packages/matriz-client/src/matriz_client/models.py`, `packages/matriz-client/tests/test_deep_chain_edges.py`
- **Verification:** `git grep` de las rutas viejas no devuelve nada bajo `matriz-client`; los 596 tests del paquete siguen verdes.
- **Committed in:** `ffbdb75`

---

**Total deviations:** 1 auto-fixed (1 bug). Es consecuencia directa del renombre de la Task 3, no scope creep.

**Impact on plan:** Ninguno sobre el diseño. Los dos archivos extra están fuera de `files_modified` del plan pero dentro del paquete que la Task 3 modifica, y el cambio es de tres líneas de prosa.

Cero dependencias nuevas (T-39-SC). Cero probes nuevos, cero llamadas HTTP nuevas, cero renombres de probe, cero deleciones en los tres commits.

## Issues Encountered

- **`ruff` marcó `SIM114` en la primera versión de `_chain_rooted_at`** (dos ramas `elif` con el mismo cuerpo `current = current.value`). Se combinaron en `isinstance(current, ast.Attribute | ast.Subscript)`; el comportamiento es idéntico y el RED se re-verificó tras el cambio. También hizo falta un `ruff format` sobre el archivo nuevo antes del commit RED.

## Verificación

| Criterio | Resultado |
|---|---|
| `pytest -q verification/test_main_matriz_deep_chain.py` (RED, Task 1) | 5 failed / 4 passed |
| `pytest -q verification/test_main_matriz_deep_chain.py` (GREEN, Task 2) | 9 passed |
| `pytest -q packages/matriz-client` | 596 passed |
| `pytest -q` de los 4 locks de matriz (deep-chain, schema-alignment, risk-envelope, skip-line) | 37 passed |
| Allowlist completa de CI (11 archivos, incluido el nuevo) | 107 passed |
| `ruff check .` / `ruff format --check .` / `mypy` | 0 / 277 files formatted / Success: no issues found in 75 source files |
| `grep -c 'test_main_matriz_deep_chain.py' .github/workflows/ci.yml` | 1 (≥ 1) |
| `grep -c 'MarketDataSnapshot.from_api' main_matriz.py` | 2 (1 código + 1 comentario) |
| `grep -c open_interest main_matriz.py` | 4 (2 desreferencias + 2 detalles de PASS) |
| `git grep -n ws_client main_matriz.py` | vacío (exit 1) |
| `ls .planning/verification/schemas/matriz-client/ \| grep -c remarkets` | 8 |
| `git show --stat ffbdb75` sobre los 8 baselines | 8 files changed, **0 insertions(+), 0 deletions(-)** — renombre puro |
| `git diff` de `ws_client.py` y `verification/mutation_gate.py` desde el inicio de la fase | vacío (byte-idénticos) |
| Deletions en los 3 commits de tarea | ninguna |
| Untracked tras los 3 commits | ninguno |

**Smoke test de `_schema_path` por import** (sin correr el driver):

| `base_url` | Nombre resuelto |
|---|---|
| `https://api.remarkets.primary.com.ar` | `get-segments.remarkets.json` (= el archivo renombrado) |
| `https://api.bbsa.matrizoms.com.ar` | `get-market-data.bbsa.json` (fresco, no diffea contra remarkets) |
| `https://evil.example` | `get-trades.unknown-venue.json` (centinela, no lanza) |
| `https://[oops/api` (imparseable) | `get-trades.unknown-venue.json` (centinela, no lanza) |

## TDD Gate Compliance

Secuencia completa en el historial: `d318a5f` `test(39-06): …` (RED) → `ef5296a` `feat(39-06): …` (GREEN) → `ffbdb75` `refactor(39-06): …`. El RED se corrió y se verificó rojo **por la razón correcta** antes de escribir una línea de implementación: los mensajes nombraron el probe sync sin `MarketDataSnapshot.from_api`, los dos probes sin desreferencia, el agregado en 0 de 12, el piso por probe en 0 de 6 y los 12 pares `(probe, alias)` sin gastar. El commit `ffbdb75` es un `refactor` de artefacto (Task 3), no la fase REFACTOR del ciclo TDD.

## Known Stubs

Ninguno. Las doce desreferencias son código en el camino caliente de los dos probes.

Lo que el lock **no** puede afirmar, y que el censo del 39-08 debe registrar como limitación medida:

- **El lock es estructural, no de corrida.** Garantiza que el código existe, está bien ubicado y no cuesta un request extra; no garantiza que la API haya devuelto un book poblado. La corrida real es del plan 39-07.
- **La rama de mercado cerrado la aporta la suite mockeada.** Con el segmento cerrado el baseline committeado muestra `BI`/`OF` en lista vacía y `LA`/`SE`/`OI`/`CL`/`OP` en `null`: los seis alias devuelven Null Objects falsy y el detalle de PASS mostrará `last=None bids=0 offers=0 …`. Esa evidencia de borde ya está pinneada por `packages/matriz-client/tests/test_deep_chain_edges.py` (plan 39-02); una corrida en vivo fuera de horario **no** la ejercita de otro modo.
- **Los baselines de bbsa todavía no existen.** Se capturan en el plan 39-07, en el que serán 8+ archivos nuevos `*.bbsa.json` con status PASS "escrito …" — **no** findings `SHAPE OPEN`. El censo debe leer esa primera corrida como captura, no como ausencia de deriva.

## Threat Flags

Ninguno. Las superficies tocadas ya estaban en el `<threat_model>` del plan:

- **T-39-20** (token de venue como componente de nombre de archivo) — mitigado: el token sale de `_venue_token`, que consulta `_VENUE_ALLOWLIST` —un dict cerrado de dos entradas con valores literales— por igualdad exacta de hostname; un hostname desconocido, sin host o imparseable produce el literal `_VENUE_SENTINEL`, nunca un fragmento de la URL. El directorio se deriva de `__file__`. Verificado por los cuatro casos del smoke test de arriba, incluida la URL imparseable.
- **T-39-21** (findings de deriva entre venues leídos como defectos del cliente) — mitigado: la segregación aterrizó en este plan, **antes** del 39-07, y el caveat está escrito en el docstring de `_schema_path` con destino explícito al censo.
- **T-39-22** (eslabón roto fuera del `try`) — mitigado: las doce desreferencias viven en el cuerpo de un `try` y `test_every_chained_access_sits_inside_the_probe_try_body` lo pinea con `_protected_node_ids`, que excluye `except` / `else` / `finally`.
- **T-39-23** (superficie WS reintroducida) — mitigado: `test_the_driver_never_imports_ws_client` por AST sobre los nodos `Import` / `ImportFrom`; `ws_client.py` byte-idéntico.
- **T-39-24** (valores de market data en el detalle del `ProbeResult`) — mitigado: se agregan precios, conteos de niveles y un tamaño de interés abierto. Cero identificadores de cuenta; el driver ya emite todo por `safe_print(..., secrets=[...])` con `PRIMARY_USER`, `PRIMARY_PASSWORD` y el token.
- **T-39-SC** — cero dependencias nuevas.

## Next Phase Readiness

- **Los cuatro drivers verificables tienen ahora cadena real, lock AST y CI.** iol (39-04), higyrus (39-05), market-data (Phase 36) y matriz (este plan). SC-1 queda satisfecho en su mitad de código para los cuatro.
- **Precondición del 39-07 cumplida.** La segregación por venue estaba explícitamente marcada como "MUST land before any live matriz run in Wave 6". Está aterrizada y verificada por import.
- **Insumo directo para el censo (39-08):** los dos detalles de PASS transcriben `last=… bids=… offers=… settlement=… close=… oi=…`, leíbles del stdout sin instrumentación extra, y el caveat de segregación por venue está escrito en `_schema_path` para copiarlo en vez de re-derivarlo.
- **Pendiente heredado de 39-01, sin cambios:** el finding terminal `EXPECTED` anterior de matriz queda **superseded**; el título nuevo crea un finding nuevo en la primera corrida en vivo y el viejo debe recibir disposición explícita en 39-07, no borrarse.
- **Sin cambios en:** `packages/matriz-client/src/matriz_client/ws_client.py` y `verification/mutation_gate.py` (order entry sigue fail-closed bajo bbsa por su `_SANDBOX_HOST` remarkets-only).

## Self-Check: PASSED

- `verification/test_main_matriz_deep_chain.py` — FOUND en disco.
- `.planning/verification/schemas/matriz-client/get-segments.remarkets.json` — FOUND en disco (8 de 8 renombrados presentes).
- Commit `d318a5f` — FOUND en el historial.
- Commit `ef5296a` — FOUND en el historial.
- Commit `ffbdb75` — FOUND en el historial.

---
*Phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo*
*Completed: 2026-08-30*
