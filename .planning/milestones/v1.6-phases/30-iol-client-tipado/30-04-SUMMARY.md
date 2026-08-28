---
phase: 30-iol-client-tipado
plan: 04
subsystem: api
tags: [python, typing, iol-client, verification-harness, docs, changelog, driver]

# Dependency graph
requires:
  - phase: 30-iol-client-tipado
    provides: "Planes 30-01/02/03 — los 4 modelos (`Cotizacion`, `Punta`, `Instrumento`, `Titulo`), `SafeModel.to_dict()`, y las 16 firmas migradas"
  - phase: 29-decoder-observable
    provides: "`_decode.py` — el walker congelado que garantiza el tipo declarado en cada atributo"
provides:
  - "`main_iol._as_wire` — el adaptador de frontera driver → harness de verificación"
  - "`main_iol.py` leyendo por atributo en sus 2 sitios reales de consumo, sin guard de tipo"
  - "Los 4 sitios de frontera con `schema_of` no-vacuos; el envelope de by_type intacto"
  - "5 re-mocks residuales del envelope de `get_instruments` en `verification/`"
  - "`packages/iol-client/README.md` — sección de uso real + `## Changelog` con `### v0.3.0`"
  - "El texto de ruptura dict→modelo que alimenta el bump 0.2.0 → 0.3.0 de Phase 34"
affects: [32-gate-ast, 33-live-strict-run, 34-release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Normalizar modelo→wire en la **frontera** hacia el harness (`_as_wire`), no en cada sitio de llamada: los payloads llegan opacos y el adaptador pasa un dict crudo tal cual"
    - "Verificar **no-vacuidad** de un probe por aserción positiva (la reducción devuelve un dict) en vez de por ausencia de findings"
    - "Round-trip offline contra el baseline committeado: schema → payload sintético → modelo → `_as_wire` → `schema_of` → comparar, sin credenciales"
key-files:
  created:
    - .planning/phases/30-iol-client-tipado/deferred-items.md
  modified:
    - main_iol.py
    - packages/iol-client/README.md
    - verification/test_logging_no_token_leak.py
    - verification/test_retry_401_reauth.py
    - verification/test_retry_after_cap.py
    - verification/test_sync_async_isolation.py

key-decisions:
  - "El guard de tipo del precio se eliminó, no se relajó: `ultimoPrecio` está declarado `float` y el walker lo garantiza — dejarlo puesto implicaría no creerle al tipo que la fase entrega"
  - "`_as_wire` se aplica uniformemente en el bucle de snapshots en vez de en 3 de las 4 entradas de la tabla: el envelope crudo lo atraviesa intacto por construcción, así que el efecto es idéntico y no hay una rama que asuma un modelo"
  - "Los 5 re-mocks residuales se corrigieron del lado del test, no del parser — la misma disciplina que sostuvo 30-03"
  - "El sanity check de los 6 InstrumentType chequeaba `isinstance(fila, dict)`: se migró a `Titulo` porque si no cada corrida viva emitiría un finding SHAPE espurio con los 6 types adentro"
  - "Las 19 fallas de matriz de la suite completa son pre-existentes desde Phase 15 y quedan registradas en `deferred-items.md`, sin tocar"

patterns-established:
  - "Pattern 5: cuando un cambio de tipo atraviesa la frontera hacia un harness que reduce formas, la verificación correcta es una aserción de no-vacuidad (`isinstance(schema_of(x.to_dict()), dict)` **y** `not isinstance(schema_of(x), dict)`), porque el probe roto reporta PASS"

requirements-completed: [TYP-01]

# Metrics
duration: 31min
completed: 2026-08-20
status: complete
---

# Phase 30 Plan 04: driver, snapshot y README Summary

**Los tres instrumentos de medición que la migración dict→modelo habría dejado verdes y ciegos —el probe de paridad comparando dos veces el mismo nombre de clase y los dos probes de mapa de campos salteando su bucle entero— quedaron reparados en la frontera con un único adaptador, demostrados no-vacuos por aserción positiva, y respaldados por un round-trip offline que reproduce los 3 baselines committeados byte-idénticos; el README pasó de documentar una API inexistente a registrar la ruptura con su flip de truthiness.**

## Performance

- **Duration:** 31 min
- **Started:** 2026-08-20T03:09:08Z
- **Completed:** 2026-08-20T03:40:26Z
- **Tasks:** 3 (la 2 resultó verificación pura — ver deviación 1)
- **Files modified:** 7 (1 creado, 6 modificados)

## Accomplishments

- `main_iol.py` lee el precio **por atributo** en sus 2 sitios reales y el guard de tipo que lo envolvía desapareció por ser código muerto demostrable.
- `_as_wire` introducido y aplicado en los **4 sitios de frontera**; el envelope de by_type —capturado de una petición cruda— lo atraviesa intacto, que es lo correcto.
- **No-vacuidad demostrada por aserción**, no por ausencia de findings; y **round-trip 3/3 byte-idéntico** contra los baselines committeados, obtenido **sin credenciales**.
- **25 posiciones de anotación** re-tipadas a los modelos; las 2 del envelope de by_type quedaron intactas, verificado a mano.
- Un finding SHAPE espurio garantizado en cada corrida viva (los 6 `InstrumentType`) detectado y eliminado antes de existir.
- 5 mocks residuales del envelope viejo encontrados en `verification/` — invisibles porque ese directorio nunca corre en CI — y corregidos: `verification/ -k iol` pasó de **4 failed** a **61 passed**.
- README reescrito: superficie real + `### v0.3.0` con la ruptura, el flip de truthiness, el escape hatch con su pérdida conocida, los 5 tipos nuevos y el cambio de forma del listado. `__version__` sigue en `0.2.0`.

## Task Commits

| Task | Commit | Tipo |
|---|---|---|
| 1 — driver + adaptador de frontera | `7ce4756` | `refactor` |
| 2 — golden file de superficie | — | verificación pura, sin diff (deviación 1) |
| 3 — README | `ec2c2f7` | `docs` |
| Rule 1 — re-mocks residuales en `verification/` | `042bcbd` | `test` |

## Plan-mandated records

### (a) No-vacuidad y round-trip — la salida literal

**No-vacuidad** (el criterio que realmente importa: tres de los cuatro sitios de
frontera reportan PASS precisamente cuando están rotos):

```
NON-VACUITY OK
  schema_of(model)          -> 'Cotizacion'
  schema_of(model.to_dict())-> dict con 20 claves
```

Las tres aserciones del plan salieron 0: la reducción de la proyección **es** un
dict, la del modelo crudo **no** lo es (la premisa del plan sigue en pie), y una
lista de proyecciones se reduce a lista.

**Round-trip contra los 3 baselines committeados** — para cada archivo se derivó
un payload de wire desde la clave `schema` committeada, se construyeron los
modelos, se aplicó `_as_wire` y se redujo:

```
MATCH   get-quote.json
MATCH   get-historical-quotes.json
MATCH   get-instruments.json
ROUND-TRIP: 3/3 byte-identicos
```

Es la prueba end-to-end más fuerte de la fase y se obtiene **sin credenciales**.
`git diff --exit-code .planning/verification/schemas/iol-client/` sale 0: los 4
baselines siguen byte-idénticos.

### (b) El diff del snapshot de superficie

**Cero líneas** — y eso es el resultado correcto, no una omisión. El diff que el
plan esperaba (4 firmas modificadas + 5 clases agregadas) **ya está committeado**:
se acumuló incrementalmente en 30-01 (+3 clases, 1 firma), 30-02 (+1 clase, 2
firmas) y 30-03 (+1 clase, 1 firma), porque cada uno de esos planes disparó el
ritual de regeneración que 30-01 marcó como carry-forward. Ver deviación 1.

Estado verificado del archivo, que es lo que el plan quiere garantizar:

| Criterio | Resultado |
|---|---|
| `Cotizacion : class` / `Instrumento` / `Punta` / `SafeModel` / `Titulo` | 1 cada uno — **las 5 clases presentes** |
| Líneas de firma que nombran un modelo | 4 (`get_quote → 'Cotizacion'`, `get_historical_quotes → 'list[Cotizacion]'`, `get_instruments → 'list[Instrumento]'`, `get_instruments_by_type → 'list[Titulo]'`) |
| Header invariante | 8 líneas `#`, intactas |
| Idempotencia | `regen_snapshots.py` re-corrido → `git diff --exit-code verification/snapshots/` sale 0 |
| Otros snapshots | ninguno cambió |

La señal de alarma explícita del plan (Pitfall 3: "líneas modificadas pero
ninguna agregada → los modelos no llegaron al `__all__`") **no aplica**: las 5
clases están enumeradas, así que el export está bien y el gate AST de Phase 32
tendrá qué chequear.

### (c) Carry-forward FA-09 → Phase 33 — la señal autoritativa de drift cambió

**Para los endpoints modelados de iol, la señal autoritativa de drift ya no es el
diff del snapshot de schema: es el censo de divergencias.**

`to_dict()` proyecta el drift **afuera** por construcción. `asdict` serializa el
*modelo*, y el modelo es por definición la forma *declarada*: cualquier clave que
el wire traiga y el modelo no declare no puede sobrevivir la ida y vuelta, y
cualquier clave declarada que el wire no traiga aparece igual con su typed-zero.
La forma medida del efecto (RESEARCH Pitfall 5) es nítida:

```
wire:   [{"precioCompra": 3.0, "extraKey": 1}]
schema_of(to_dict()) -> [{"cantidadCompra":"float","cantidadVenta":"float",
                          "precioCompra":"float","precioVenta":"float"}]  ← COINCIDE con el baseline
divergence records   -> .puntas[].extraKey        extra
                        .puntas[].cantidadCompra  missing
                        .puntas[].cantidadVenta   missing
                        .puntas[].precioVenta     missing
```

El snapshot dice "sin drift"; el walker dice "cuatro divergencias". Los dos están
corriendo; **sólo uno sigue viendo la verdad**.

Esto es el trade que D-08 acepta a propósito, no un defecto a corregir. Pero
tiene una consecuencia operativa dura para Phase 33: **una corrida de F33 que lea
"sin drift de schema" y se detenga ahí estaría leyendo un instrumento que esta
fase desafiló deliberadamente.** F33 debe leer el **censo de divergencias** de
iol. El mismo razonamiento explica por qué el round-trip de la sección (a) puede
salir 3/3 y ser a la vez una prueba fuerte (demuestra que la migración no rompió
la frontera) y una prueba que **no** dice nada sobre el wire real.

Corolario menos obvio, ya pinneado por 30-01/30-02: la asimetría int/float de
`cantidadOperaciones` sí sigue siendo visible, porque la rama entera del walker
**reporta**. Es decir, el censo no perdió poder; lo ganó.

### (d) Estado de FA-04 (consumidores externos) para el framing del release de F34

**Sigue abierta.** Nadie confirmó si algo fuera de este repo consume
`iol-client` 0.2.0; la pregunta al operator está registrada como blocker en
STATE.md desde el arranque de la fase y este plan no la resolvió (no está en su
poder resolverla).

**No bloquea nada de esta fase.** La mitigación —`to_dict()` como escape hatch en
el mismo release que la ruptura, más el callout del README— es la correcta bajo
cualquiera de los dos resultados, y ya está entregada.

**Lo que sí depende de la respuesta es el framing del release de F34:**

| Si la respuesta es… | Consecuencia para F34 |
|---|---|
| No hay consumidor externo | El bump 0.2.0 → 0.3.0 es rutina; el changelog es documentación defensiva y nada más. |
| Hay consumidor externo | El changelog pasa a ser una **nota de migración** que hay que comunicar activamente, y el flip de truthiness es el ítem que más riesgo tiene de romper en silencio del otro lado. |

El texto del changelog fue redactado deliberadamente para ser correcto en los dos
escenarios: describe la ruptura y la ruta de migración sin afirmar ni negar que
exista alguien afectado, y sin prometer un bump que esta fase no ejecuta.

### (e) Las 25 posiciones de anotación (revisión humana, `verify-human` de la Task 1)

`main_iol.py` no lo typechequea mypy (su `files` cubre `packages/*/src`), así que
estas anotaciones son documentación y un error en ellas es **invisible al CI**.
Revisadas a mano sobre `git diff main_iol.py`:

| Sitio | Posiciones | De → a |
|---|---|---|
| Retornos de los 8 probes de endpoint | 8 | `dict[str, Any] \| None` → `Cotizacion \| None`; `list[dict[str, Any]] \| None` → `list[Cotizacion] \| None` / `list[Titulo] \| None`; `Any` → `list[Instrumento] \| None` |
| Parámetros de `probe_parity_sync_async` | 8 | los 4 pares sync/async, cada uno a su modelo |
| Parámetros de `probe_field_type_map` | 2 | `quote`, `historical` |
| Parámetros de `probe_schema_snapshot` | 3 | `quote`, `historical`, `instruments` |
| Tupla de retorno de `_async_main` | 4 | los 4 payloads |
| **Total** | **25** | |

**Las 2 anotaciones del envelope de instrumentos-por-tipo quedaron intactas**
(`instruments_by_type_envelope` y `by_type_envelope`, ambas
`dict[str, Any] | None`), verificado por ausencia en el diff, y se les agregó un
comentario que dice **por qué**: vienen de una petición cruda, no del wrapper del
cliente, y por lo tanto son inmunes a la migración. Ésa era la trampa que FA-08
señalaba.

*Nota de precisión:* el mensaje del commit `7ce4756` dice "22 anotaciones". El
conteo correcto es **25** — el error está en la prosa del commit, no en el código;
el desglose de arriba es el bueno.

## Decisions Made

- **El guard de tipo del precio se eliminó, no se relajó.** Era la opción
  visible: dejar `isinstance(ultimo, int | float)` no rompe nada. Pero
  `ultimoPrecio` está declarado `float` y el walker garantiza que un decimal
  llega al atributo (sustituye el typed-zero y **reporta** si el wire diverge).
  Conservarlo sería el driver diciendo que no le cree al tipo que la fase acaba
  de entregar. El guard de **ausencia** sobre `quote` sí se conservó: el probe
  sigue recibiendo un opcional, que es una cosa distinta.
- **`_as_wire` se aplica una sola vez en el bucle de snapshots, no en 3 de las 4
  entradas de la tabla.** El plan describe el efecto ("3 de los 4 destinos") y
  ésa es exactamente la semántica que resulta, porque el envelope crudo atraviesa
  el adaptador intacto por construcción. Ramificar la tabla para saltear
  explícitamente el cuarto destino habría agregado una rama que asume un modelo
  —justo lo que FA-08 advierte que no hay que hacer— sin cambiar el resultado.
- **La normalización vive en la frontera, no en cada sitio de llamada.** En el
  probe de paridad los payloads llegan genuinamente opacos (modelo, lista de
  modelos o dict crudo, según el endpoint), así que un `.to_dict()` por sitio
  requeriría saber de antemano qué es cada uno. En los dos probes de mapa de
  campos el tipo **sí** se conoce, y ahí se usa `.to_dict()` directo: es más
  legible y el gate del plan lo pide así.
- **Los 5 re-mocks residuales se corrigieron del lado del test.** La alternativa
  —darle al guard tolerancia dict-o-lista— habría puesto verde la suite sin tocar
  un mock, y es exactamente el bug del vacío silencioso que el milestone existe
  para eliminar. `[]` es el mock honesto: los 5 sitios son incidentales (afirman
  sobre headers, reauth, cap de `Retry-After` y aislamiento sync/async, nunca
  sobre el contenido) y el guard discrimina **forma**, no cardinalidad.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] La Task 2 resultó verificación pura: el diff que esperaba ya estaba committeado**

- **Found during:** Task 2
- **Issue:** El plan describe el diff esperado del golden file como "4 líneas de
  función modificadas + 5 líneas de clase agregadas", y su criterio
  `git status --porcelain verification/snapshots/ | wc -l` espera `1`. Al
  regenerar, el árbol quedó **limpio**: `wc -l` imprimió `0`. El plan asumía que
  el snapshot venía sin tocar desde el arranque de la fase, pero 30-01, 30-02 y
  30-03 lo regeneraron cada uno tras su propio cambio de superficie —el ritual
  por plan que 30-01 marcó como carry-forward y 30-02 confirmó—, así que el diff
  acumulado ya está en `c35071e`, `963b85c`, `ecd99dd` y `0e920b0`.
- **Fix:** ninguno necesario en el archivo. Se verificó el **estado final**, que
  es lo que el plan realmente quiere garantizar: las 5 clases presentes, las 4
  firmas nombrando modelos, header de 8 líneas intacto, idempotencia del script
  y ningún otro snapshot tocado. Ver record (b).
- **Files modified:** ninguno.
- **Verification:** `pytest verification/test_public_surface.py -q` → 4 passed.
- **Committed in:** n/a — sin cambio que committear.

**2. [Rule 1 - Bug] El sanity check de los 6 `InstrumentType` habría marcado los 6 como shape inesperada**

- **Found during:** Task 1
- **Issue:** `probe_get_instruments_by_type_sync` corre un sanity check
  type-only sobre los 6 `InstrumentType` y guardaba con
  `isinstance(titulos[0], dict)`. Tras la migración de 30-03 el wrapper devuelve
  `list[Titulo]`, así que el chequeo pasa a ser falso para **todos** los types:
  cada corrida viva habría emitido un finding SHAPE con los 6 adentro y el probe
  habría reportado FINDING en vez de PASS. No estaba en el inventario del plan
  (que enumera los sitios de `schema_of`, y éste no lo es) ni en el de RESEARCH.
- **Fix:** migrado a `isinstance(titulos[0], Titulo)`, con un comentario que
  registra por qué. Es el chequeo estrictamente más fuerte: nombra la clase en
  vez del contenedor.
- **Files modified:** `main_iol.py`
- **Verification:** ruff + format verdes; el probe conserva sus tres condiciones
  (es lista, no está vacía, el elemento es del tipo esperado).
- **Committed in:** `7ce4756`

**3. [Rule 1 - Bug] 5 mocks del envelope viejo de `get_instruments` sobrevivían en `verification/`**

- **Found during:** Task 2 (criterio `uv run pytest verification/ -q -k iol` sale 0)
- **Issue:** La corrida salió **4 failed, 57 passed**, todas con
  `IOLAPIError: [0] shape mismatch: expected list, got dict`. El Plan 30-03
  corrigió los 16 payloads de `packages/iol-client/tests/` a la lista top-level
  que la captura viva demuestra e instaló el guard que levanta (D-06), pero su
  inventario —derivado de un `grep` sobre `packages/iol-client/tests/`— no
  alcanzaba `verification/`, donde quedaban 5 sitios más:
  `test_logging_no_token_leak.py`, `test_retry_401_reauth.py`,
  `test_retry_after_cap.py` y `test_sync_async_isolation.py` (×2). Invisibles
  porque `verification/` **nunca corre en CI**. El quinto
  (`test_retry_after_cap.py`) ni siquiera aparecía en las 4 fallas: su nombre no
  matchea `-k iol`, así que estaba roto **y** deseleccionado — habría explotado
  la primera vez que alguien corriera el directorio entero.
- **Fix:** los 5 payloads a `json=[]`, del lado del test y no del parser. Son
  incidentales: esos tests afirman sobre el header de autorización, el reauth
  tras 401, el cap de `Retry-After` y el aislamiento sync/async, nunca sobre el
  contenido.
- **Files modified:** `verification/test_logging_no_token_leak.py`,
  `verification/test_retry_401_reauth.py`, `verification/test_retry_after_cap.py`,
  `verification/test_sync_async_isolation.py`
- **Verification:** los 4 archivos → 22 passed; `verification/ -q -k iol` → **61
  passed**; `grep -rn "instrumentos" verification/*.py` sin resultados.
- **Committed in:** `042bcbd`

### Fuera de alcance — registrado sin corregir

**4. [SCOPE BOUNDARY] 19 tests de matriz rotos desde Phase 15 en la suite completa**

- **Found during:** verificación paso 9 (`uv run pytest -q`)
- **Issue:** `19 failed, 1840 passed, 19 errors`. Los 19 son todos de matriz:
  17 en `test_matriz_sweep_snapshot.py` y 2 en
  `test_main_matriz_login_fail_uniformity.py`, con causa raíz única —
  `TypeError: probe_get_segments() missing 1 required positional argument: 'client'`.
  `main_matriz.py` ganó el parámetro `client` en `1fbc83f` (**2026-06-24**, Plan
  15-05); los tests datan del 2026-06-12 y 2026-06-14 y siguen llamándolos sin
  argumento. Llevan **dos meses** rotos, invisibles por el mismo gap de CI.
- **Acción:** **ninguna.** Phase 30 no toca matriz. Registrado en
  `.planning/phases/30-iol-client-tipado/deferred-items.md` como DEF-30-01, con
  la nota de que Phase 32 —la que arregla el gap de CI de `verification/`— es
  donde dejarán de ser invisibles.
- **Evidencia de que el resto está verde:** excluyendo esos dos archivos y el
  lento `test_with_options.py`, la suite sale **1824 passed, 0 failed**.

---

**Total deviations:** 3 auto-fixed (1 bloqueante de secuenciación, 2 bugs) + 1
fuera de alcance registrado. No surgió ninguna situación de Rule 4 y no se
necesitó ningún `checkpoint:decision` — el plan predijo que no habría ninguno
porque ninguna decisión de este plan es one-way.
**Impact on plan:** ninguno sobre el alcance. Las deviaciones 2 y 3 son
consecuencias de la migración de esta fase que los inventarios previos no
alcanzaron; ambas caen dentro de `verification/` y `main_iol.py`, que son los
artefactos que este plan posee.

## Prohibitions — status at close

| Prohibition | Status |
|---|---|
| La salida de `to_dict()` llega a `schema_of` y a nada más | **held** — los 4 sitios de `_as_wire`/`to_dict` alimentan `schema_of` exclusivamente. Ningún `append_finding` ni escritura de snapshot recibe la proyección; el escritor sigue serializando el resultado de `schema_of`, que emite claves y nombres de tipo, jamás valores. Verificado además por el lado duro: los 4 baselines siguen byte-idénticos. |
| Un probe no se declara verde por reportar PASS | **held** — la verificación central es la aserción de **no-vacuidad** en las dos direcciones (la proyección reduce a dict, el modelo crudo **no**) más el round-trip 3/3 contra los baselines. Ningún criterio de este plan se satisfizo con "el driver sigue en PASS". |
| El modo estricto de decodificación no se activa | **held** — `grep -n "strict_decode" main_iol.py` sin resultados; el driver no lo menciona en ninguna forma. Sigue siendo entregable de Phase 33. |
| `__version__` no se bumpea y `uv.lock` no se modifica | **held** — `iol_client.__version__ == "0.2.0"` verificado por aserción; `git diff --exit-code uv.lock packages/iol-client/src/iol_client/_decode.py` limpio; `git diff --exit-code packages/iol-client/src/` limpio en la tarea del README. Cero paquetes instalados. |
| El snapshot de superficie no se edita a mano | **held** — se corrió `verification/regen_snapshots.py` y no se tocó el archivo. Resultó sin diff porque los planes anteriores ya lo habían regenerado (deviación 1). |

## Verification — resultados

| # | Gate | Resultado |
|---|---|---|
| 1 | `pytest packages/iol-client -q` | **237 passed** (≥ 205 pedido) |
| 2 | `mypy packages/iol-client/src …/tests` | `Success: no issues found in 25 source files` |
| 3 | `ruff check . && ruff format --check .` | All checks passed / 218 files already formatted |
| 4 | `pytest verification/ -q -k iol` | **61 passed** (era 4 failed / 57 passed antes de la deviación 3) |
| 5 | `python tools/check_decode_intactness.py` | 0 — checks A–D verdes, digest `ac14868282ad0a5c` |
| 6 | `git diff --exit-code .planning/verification/schemas/iol-client/` | 0 — los 4 baselines byte-idénticos |
| 7 | `git diff --exit-code uv.lock …/_decode.py` | 0 |
| 8 | `__version__ == "0.2.0"` | 0 |
| 9 | `pytest -q` (monorepo completo) | 19 failed / 1840 passed — **las 19 son matriz pre-existente**; excluyéndolas, **1824 passed, 0 failed**. Ver deviación 4. |

## Issues Encountered

- **La suite completa no sale verde**, y no por esta fase: las 19 fallas son de
  matriz y datan de Phase 15. Documentadas en `deferred-items.md`. El gate 9 del
  plan asumía una suite verde de base; no lo era.
- **`verification/test_with_options.py` tarda ~12,5 minutos** por naturaleza
  (paths de retry/backoff con sleeps reales). Nota operativa que arrastran 30-01,
  30-02 y 30-03: no es un cuelgue. Corrió acá como parte del gate 9.
- **`.planning/phases/30-iol-client-tipado/30-PATTERNS.md` está sin trackear.**
  Es un artefacto de planificación de esta fase que ningún plan committeó. No lo
  agrego porque no es mío; queda señalado para el cierre de fase.

## User Setup Required

Ninguno — no hay configuración de servicio externo. Cero paquetes instalados;
`uv.lock` byte-idéntico.

## Next Phase Readiness

- **Los 5 criterios del ROADMAP para Phase 30 quedan cubiertos.** El 3 (driver
  por atributo) y el 5 (escape hatch + callout de ruptura en el mismo release)
  son los que cierra este plan; el 2 lo cerró 30-03; el 4 (mercado/plazo siguen
  `str`) se sostuvo en los cuatro planes.
- **Phase 33 debe leer el censo de divergencias, no el diff del snapshot**, para
  los endpoints modelados de iol. Ver record (c) — es el carry-forward más
  importante que deja esta fase, y es un instrumento que se desafiló a propósito.
- **Phase 34 hereda el texto del changelog listo y el bump sin hacer.**
  `__version__` sigue en `0.2.0`; la sección `### v0.3.0` ya está escrita y
  redactada para ser correcta con o sin consumidores externos (FA-04, record (d)).
- **Phase 32 hereda dos cosas del gap de CI de `verification/`:** el gate AST que
  va a chequear los 5 símbolos exportados (que el snapshot confirma presentes), y
  los 19 tests de matriz de DEF-30-01, que dejan de ser invisibles en cuanto ese
  directorio entre al CI.
- **Sin blockers nuevos.** FA-04 sigue abierta como pregunta al operator, sin
  bloquear nada.

---
*Phase: 30-iol-client-tipado*
*Completed: 2026-08-20*

## Self-Check: PASSED

Los 6 archivos modificados y los 2 creados existen en disco; los 3 commits de tarea resuelven en `git log`.
