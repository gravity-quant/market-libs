---
phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets
plan: 03
subsystem: docs
tags: [documentation, breaking-change, readme, null-object, iol-client, accounting, phase-39-handoff]

# Dependency graph
requires:
  - phase: 38-01-null-objects-para-puntas-en-iol
    provides: "La ruptura que el callout describe, ya en `main`: `Cotizacion.puntas: list[Punta]` y `Titulo.puntas: Punta`, más los números de línea vigentes de `models.py`"
  - phase: 36-market-data-null-objects
    provides: "El precedente de formato D-10 — la sección `## Unreleased — BREAKING` de `packages/market-data-client/README.md:7-33`, mismo milestone v1.7"
  - phase: 35-null-object-nobj
    provides: "`35-RETIRED-TRIPLES.md`, el ledger que Phase 39 usa como término medio de su resta, y su párrafo 'Two limits with named destinations' que declara la obligación que este plan salda"
provides:
  - "Callout `## Unreleased — BREAKING` en el README de iol, sin número de versión asumido, con la tabla de migración de 2 filas y la asimetría de truthiness dicha en prosa"
  - "`35-RETIRED-TRIPLES.md` con las seis referencias de fuente resueltas contra HEAD — cero refs stale sobrevivientes"
  - "`## Phase 38 addendum` — el registro durable que Phase 39 lee: 2 filas de campo agregadas, 0 triples retirados en ambas columnas, con la invariancia nombrada como el hallazgo"
  - "Puntero cruzado a `38-CENSUS.md` desde el archivo que Phase 39 ya trata como fuente única del término medio"
affects: [38-04-censo, 39-contabilidad-triples, 40-bump-breaking-coordinado]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Disclosure de ruptura sin versión: `## Unreleased — BREAKING` anclado en el último tag publicado, dejando el bump a la fase que lo posee"
    - "Corrección de ledger todo-o-nada: o todas las referencias de fuente stale se arreglan o ninguna — un ledger autoritativo en un párrafo y equivocado en otro es peor que uno sin corregir"
    - "Contribución de fase a un ledger ajeno vía addendum delimitado, no reescribiendo su tabla ni su contabilidad de filas"

key-files:
  created: []
  modified:
    - packages/iol-client/README.md
    - .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md

key-decisions:
  - "Las dos referencias a `models.py` se escribieron `:235` / `:334` — verificadas contra HEAD — y NO `:213` / `:301` como pedía la tabla del plan: esos números se midieron en `cf79e65`, antes de que las reescrituras de docstring de 38-01 los corrieran (Rule 1)"
  - "El párrafo 'la zero es un hecho sobre `Optional`' no se borró ni se reescribió: se corrigió su tiempo verbal ('are declared today' → 'were declared at 242b9f3') y se le agregó un párrafo que registra que su última cláusula predictiva ('its zero stops being zero') quedó falsificada por la medición"
  - "`_kind_of` se citó `_decode.py:369-373` (def + cuerpo), no `:369` solo — el plan dejaba el rango a criterio y pedía confirmarlo contra el archivo"

patterns-established:
  - "El callout de ruptura nombra la consecuencia de runtime, no sólo el cambio de anotación: la mitad que mypy no atrapa se escribe aparte y con nombre"

requirements-completed: [NOBJ-IOL-01]

# Metrics
duration: 8min
completed: 2026-08-29
status: complete
---

# Phase 38 Plan 03: README breaking callout + contabilidad para Phase 39 — Summary

**La ruptura de `puntas` quedó publicada donde un consumidor la lee —con la asimetría dicha: `Titulo.puntas` sigue siendo falsy pero ya no es el valor nulo del lenguaje, así que un `is None` deja de disparar en silencio— y `35-RETIRED-TRIPLES.md` dejó de citar líneas que no existen, con un addendum que le dice a Phase 39 que Phase 38 movió el roster y no la aritmética.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-08-29T20:35:00Z
- **Completed:** 2026-08-29T20:42:40Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- El README de iol abre con un callout de ruptura **sin número de versión**: ancla en el tag `iol-client-v0.3.0` (que existe — verificado con `git tag -l`), da la razón por la que `main` carga un break sin bumpear (la Fase 40 lo hace en una sola pasada), y deja el bump intacto. Ni `pyproject.toml` ni `__version__` se movieron.
- La prosa del callout nombra **la asimetría entre las dos filas**, que es la parte que la tabla sola no transmite: `Cotizacion.puntas` va de valor nulo a `[]` (falsy antes, falsy después — ninguna rama cambia), mientras que `Titulo.puntas` va de valor nulo a `Punta.empty()` — sigue falsy vía `SafeModel.__bool__`, **pero ya no es `None`**, así que un consumidor que ramifique por identidad contra la nada deja de tomar esa rama sin levantar, sin romper el build y sin una palabra de mypy.
- Las **seis** referencias de fuente derivadas de `35-RETIRED-TRIPLES.md` quedaron corregidas, no las dos que nombra D-12. Arreglar dos y dejar cuatro habría producido exactamente el ledger medio-corregido que RESEARCH Pitfall 7 describe. El grep de supervivientes stale devuelve `0`.
- El addendum de Phase 38 registra los dos números medidos (2 filas de campo, 0 triples retirados) **con la razón escrita**: los dos campos no emitían nada antes (retorno temprano de la rama `Union`) y no emiten nada ahora (brazos de colapso NOBJ-02). Dos ramas distintas, la misma salida observable. La invariancia es el hallazgo.
- La contabilidad de Phase 35 quedó intacta: 35 filas de campo, la igualdad con el conteo D-17 de `35-CONTEXT.md:112-116` sin tocar, y la fila de cero explícito de iol en su lugar. La contribución de Phase 38 vive en una sección delimitada, como manda Part B del plan.

## Task Commits

1. **Task 1: callout `## Unreleased — BREAKING` en el README de iol** — `1863cc0` (docs)
2. **Task 2: corrección de refs stale + addendum de Phase 38 en `35-RETIRED-TRIPLES.md`** — `fd809fb` (docs)

## Files Created/Modified

- `packages/iol-client/README.md` — nueva sección `## Unreleased — BREAKING` insertada en la línea 5, entre el párrafo de intro y `## Instalación` (la posición idéntica que usa el README de market-data). Cuatro partes en el orden del template D-10: heading sin versión, blockquote con el tag ancla y la razón, tabla de migración de exactamente 2 filas de datos, y un párrafo de prosa con dos bullets que separan la fila simétrica de la asimétrica. Cierra con la ganancia de acceso encadenado (`titulo.puntas.precioCompra` siempre válido) y la nota de que un `puntas` mal tipado sigue emitiendo y sigue levantando bajo `strict_decode`. El `## Changelog` no se tocó.
- `.planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md` — seis referencias corregidas en tres sitios (la sección "Why every row's retired kind is `missing`", la fila de iol de la tabla principal, y el párrafo "the zero is a fact about `Optional`"), más un párrafo agregado a ese último que registra el desenlace medido de Phase 38 y apunta al addendum, más la sección `## Phase 38 addendum` al final con cuatro subsecciones numeradas. 82 inserciones / 12 supresiones.

### Referencias corregidas (todas verificadas leyendo el archivo fuente, no transcritas)

| Lo que nombra | Citaba | Escrito ahora | Verificado en |
|---|---|---|---|
| `Cotizacion.puntas` (declaración) | `models.py:154` | `models.py:235` | `puntas: list[Punta]` |
| `Titulo.puntas` (declaración) | `models.py:242` | `models.py:334` | `puntas: Punta` |
| retorno temprano de la rama `Union` | `_decode.py:431-435` | `_decode.py:440-446` | `if origin is Union or origin is UnionType:` … `return value` |
| rama de lista no-`Optional` | `_decode.py:443-445` | `_decode.py:448-452` | `if origin is list:` … `return []` |
| rama WR-02 de modelo anidado | `_decode.py:482-484` | `_decode.py:504-505` | `if value is None:` … `SILENT_SINK` |
| `_kind_of` | `_decode.py:363-367` | `_decode.py:369-373` | `def _kind_of` + cuerpo completo |

## Decisions Made

- **Las dos referencias a `models.py` se escribieron `:235` y `:334`, no `:213` y `:301`.** Ver Deviations — es el único punto donde este plan se aparta de su propia tabla, y apartarse era la única lectura consistente con el criterio de verdad del plan.
- **`_kind_of` se citó como rango `369-373`, no como línea suelta `369`.** El plan dejaba el rango explícitamente a criterio ("pick the range that actually covers the body and confirm it before writing"); `369` es el `def` y `373` el `return "type"` final. El regex de verificación del plan (`_decode\.py:(…|369)`) matchea igual, porque `369-373` lo contiene como substring.
- **El párrafo "the zero is a fact about `Optional`" se corrigió en tiempo verbal y se le agregó un desenlace, en vez de dejarlo o reescribirlo.** Decía "are declared `Optional` **today**" y cerraba prediciendo que en Phase 38 "its zero stops being zero". Lo primero es hoy falso y lo segundo quedó falsificado por la medición (el cero se quedó en cero). Borrarlo habría perdido la predicción; dejarlo intacto habría dejado dos afirmaciones falsas en el ledger. El párrafo agregado preserva el argumento histórico y registra el resultado, que es la forma auditable.
- **La fila de cero explícito de iol se conservó y las 2 filas nuevas se presentaron como *adiciones* al roster.** RESEARCH F-10 sugería *reemplazar* la fila; Part B del plan lo prohíbe porque llevaría la tabla de 35 a 37 filas y rompería la igualdad con el conteo D-17. Se siguió el plan, y el addendum dice explícitamente por qué las dos afirmaciones son consistentes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Las líneas `models.py:213` / `:301` de la tabla del plan estaban stale**

- **Found during:** Task 2, en el paso de verificación que el propio plan ordena ("Verify each replacement against the current source file before writing it — do not transcribe blindly")
- **Issue:** La tabla de correcciones del plan (y `must_haves.artifacts[].contains`, y el primer criterio de aceptación de Task 2) mandan escribir `iol_client/models.py:213` para `Cotizacion.puntas` y `:301` para `Titulo.puntas`. Contra HEAD esas líneas son **prosa dentro de docstrings**, no declaraciones: `:213` cae en el bullet de `cantidadOperaciones` de `Cotizacion` y `:301` en el bullet de `puntas` mal tipado de `Titulo`. Las declaraciones reales están en `:235` (`puntas: list[Punta]`) y `:334` (`puntas: Punta`). El origen del drift está documentado: `38-RESEARCH.md:532` midió la tabla contra `HEAD = cf79e65`, y 38-01 —que este plan declara como dependencia— reescribió cuatro pasajes de docstring en `models.py`, corriendo ambas declaraciones hacia abajo.
- **Fix:** Se escribieron `:235` y `:334`, verificados con `grep -n "puntas" packages/iol-client/src/iol_client/models.py` antes de escribir. Escribir `:213`/`:301` habría recreado exactamente el defecto que Task 2 existe para arreglar — un ledger citando líneas que no resuelven — y habría violado el tercer `must_haves.truth` del propio plan ("every `iol_client/models.py` and `_decode.py` reference in it resolves to the branch or declaration it names at the current HEAD"), que es el criterio de verdad por encima de la tabla.
- **Files modified:** `.planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md`
- **Commit:** `fd809fb`

**Consecuencia sobre la verificación:** el primer comando de verify de Task 2 se corrió con el regex ajustado a `(235|334)` en lugar de `(213|301)`. Devuelve **4**, el valor exacto que el criterio esperaba. El `must_haves.artifacts` que pide `contains: "iol_client/models.py:213"` queda **deliberadamente no satisfecho**; el string presente es `iol_client/models.py:235`, que es el correcto.

### Criterios de aceptación con conteo impreciso (sin cambio de comportamiento)

Dos criterios de Task 2 especifican un número que `grep -c` (que cuenta **líneas**, no ocurrencias) no puede devolver. Ninguno indica un problema en el trabajo:

- **`grep -c '35 field rows'` → esperado 1, real 2.** El archivo ya traía 2 ocurrencias **antes** de este plan (`git show HEAD~1:… | grep -c` devuelve 2, en las líneas 52 y 95). El intento del criterio —que la contabilidad de filas de Phase 35 y su referencia cruzada a D-17 queden intactas— se cumple: la línea 95 (`**35 field rows**, matching the D-17 count in 35-CONTEXT.md:112-116`) no se tocó.
- **Primer verify de Task 2 → esperado 4 "each appearing twice".** Devuelve 4 líneas, pero por 6 ocurrencias (`grep -oE | wc -l` = 6): la fila de la tabla principal lleva ambas referencias en una sola línea física, y las 2 filas del addendum agregan una cada una. Las cuatro ocurrencias que el criterio enumera (fila principal ×2, párrafo de prosa ×2) están todas presentes.

## Issues Encountered

None. No hubo colisión de archivos con 38-02 (que ya había commiteado `tools/check_surface_types.py` y los fixtures de test): los dos planes tocan conjuntos disjuntos, verificado con `git status --short` vacío al arrancar y después de cada commit.

## Verification Results

| Check | Comando | Resultado |
|---|---|---|
| Callout presente, exactamente una vez | `grep -c '^## Unreleased — BREAKING$' packages/iol-client/README.md` | `1` |
| Orden de headings | `awk '/^## /{print NR": "$0}' … \| head -2` | `5: ## Unreleased — BREAKING`, `44: ## Instalación` |
| Tag ancla nombrado | `grep -c 'iol-client-v0.3.0'` | `1` |
| Razón del break sin bumpear | `grep -c 'Fase 40'` | `1` |
| **Ninguna versión asumida** | `grep -v '^#' README.md \| grep -c 'v0\.4\.0'` | `0` |
| Alternativa estricta en la tabla | `grep -c 'Punta.empty()'` | `2` |
| Tabla de migración | inspección | exactamente 2 filas de datos |
| Scope del diff de iol | `git diff --name-only -- packages/iol-client/` | sólo `README.md` |
| `pyproject.toml` intacto | `git diff --name-only -- packages/iol-client/pyproject.toml` | vacío |
| Refs `models.py` corregidas | `grep -cE 'iol_client/models\.py:(235\|334)'` | `4` (6 ocurrencias) |
| Refs `_decode.py` corregidas | `grep -cE '_decode\.py:(440-446\|448-452\|504-505\|369-373)'` | `9` líneas; las 4 presentes |
| **Cero refs stale sobrevivientes** | grep de las 6 formas viejas, excluyendo comentarios | `0` |
| Contabilidad de Phase 35 intacta | `grep -n 'matching the D-17 count'` | línea 95, sin cambios |
| Addendum presente | `grep -c '^## Phase 38 addendum$'` | `1` |
| Puntero al censo | `grep -c '38-CENSUS.md'` | `2` |
| Tabla del addendum | `awk '/^## Phase 38 addendum$/,0' \| grep -cE '^\\\| iol-client \\\|'` | `2` filas, ambas `iol-client`, ambas kind `missing` |
| `.planning/verification/` intacto | `git status --porcelain .planning/verification/` | vacío |
| Scope del diff de fases | `git diff --name-only -- .planning/phases/` | sólo `35-RETIRED-TRIPLES.md` |
| Scope total de los 2 commits | `git diff --name-only HEAD~2..HEAD` | exactamente los 2 archivos previstos |
| Suite de iol sin mover | `uv run --package iol-client pytest packages/iol-client -q` | `292 passed` |
| Trailing whitespace | `grep -nP ' +$'` sobre ambos archivos | ninguno |

**Sobre el `292 passed`:** el plan pedía "unchanged from plan 38-01's result", que fue `289`. El valor de hoy es `292`, y la diferencia **no viene de este plan** — viene de 38-02, el plan hermano de la misma ola, que agregó 3 tests al fixture RED de iol y lo dejó documentado en `38-02-SUMMARY.md:138` (`292 passed` = 289 baseline + 3 nuevos). Este plan es documentation-only y no tocó un solo archivo `.py`: el criterio real ("un cambio de conteo significa que algo más se movió") se cumple, porque el conteo es idéntico al post-estado de 38-02.

## Threat Mitigations Verified

| Threat ID | Verificación |
|---|---|
| T-38-11 (Repudiation / disclosure incompleta) | El callout no describe el retype como cambio de anotación solamente. El segundo bullet de la prosa dice literalmente que `Titulo.puntas` "ya no es el valor nulo del lenguaje" y que un consumidor que ramifique por identidad contra la nada "deja de tomar esa rama, en silencio: no levanta, no rompe el build y mypy no dice una palabra". Da los tres patrones concretos a auditar (`is None`, `assert … is None`, `or fallback` escrito para atrapar el `None`). |
| T-38-12 (Tampering / input de la resta de Phase 39) | Los dos mecanismos ejercidos: el grep de supervivientes stale devuelve `0` (todo-o-nada satisfecho), y la tabla principal de Phase 35 conserva sus 35 filas, su fila de cero explícito de iol y su igualdad con D-17 — la contribución de Phase 38 vive en la sección delimitada. |
| T-38-13 (Repudiation / ledgers auto-generados) | `git status --porcelain .planning/verification/` vacío después de ambos commits. Ningún archivo bajo `.planning/verification/` entró en el diff. |
| T-38-14, T-38-SC (aceptados) | El README agregado nombra sólo firmas de tipo públicas y un tag público — cero credenciales, cero endpoints internos. Cero instalaciones de paquetes, cero strings de versión movidos, `uv.lock` sin tocar. |

## Known Stubs

Ninguno. Los dos artefactos están completos: el callout describe una ruptura que ya está en `main` (landeada por 38-01, verificada en `models.py:235` y `:334`), y el addendum registra números medidos, no estimados.

La única referencia adelantada es el puntero a `38-CENSUS.md`, que 38-04 crea. Es intencional y está mandado por el plan (Part C, punto 4): el addendum es el lado angosto de un cruce asimétrico, y 38-04 cierra el otro lado. No es un stub — es una dependencia de orden dentro de la misma fase.

## Threat Flags

Ninguna superficie nueva. Este plan editó dos archivos markdown: cero código ejecutado, cero dependencias movidas, cero credenciales leídas, cero llamadas de red, cero endpoints o paths de auth nuevos.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **38-04 (censo)** desbloqueado y con su contraparte lista: `35-RETIRED-TRIPLES.md` ya apunta a `38-CENSUS.md`, así que 38-04 sólo tiene que cerrar el cruce desde su lado (referenciar el addendum para la contabilidad de triples retiradas en vez de duplicarla).
- **Phase 39** tiene el término medio explícito y sin ambigüedad de columna: higyrus 2, iol 0, market-data 0, matriz 5 (triples distintas) / matriz 6 (registros), con el `0` de iol acompañado de la razón que impide leerlo como "iol ya estaba limpio".
- **Phase 40** sigue siendo dueña del bump: el callout es literalmente el insumo que Phase 40 convierte en entrada de Changelog cuando asigne el número. Ni `pyproject.toml` ni `__version__` ni `uv.lock` se movieron acá.
- Sin blockers.

## Self-Check: PASSED

- `packages/iol-client/README.md` verificado en disco, con `## Unreleased — BREAKING` en la línea 5.
- `.planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md` verificado en disco, con `## Phase 38 addendum` presente una vez.
- `38-03-SUMMARY.md` verificado en disco.
- Commits `1863cc0` y `fd809fb` verificados con `git log --oneline`.
- Los seis números de línea citados en la tabla de correcciones re-verificados leyendo `models.py` y `_decode.py` directamente, no transcritos de RESEARCH.

---
*Phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets*
*Completed: 2026-08-29*
