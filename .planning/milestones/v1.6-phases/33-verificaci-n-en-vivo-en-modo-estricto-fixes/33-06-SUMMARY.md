---
phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
plan: 06
subsystem: testing
tags: [live-verification, literal-census, raw-wire, dt-07, d-lock, response-vs-input, skip-with-cause]

requires:
  - phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
    provides: "el pre-flight de autenticación y el registro `SKIPPED — base URL fuera de política` de matriz, más `33-CENSUS.md` (33-05)"
  - phase: 29-decoder-observable
    provides: "`29-DLOCK-RESPONSE-LITERAL.md` (D-09) y el hallazgo de que el corpus de sizing es type-only"
  - phase: 30-iol-typed
    provides: "`iol_client.models.Titulo` con `mercado` / `plazo` declarados `str`"
  - phase: 31-ops-endpoints
    provides: "`iol_client/types.py` como placeholder deliberado (TYP-03)"
provides:
  - "`scripts/literal_census_33.py` — censo de wire crudo por path, con `--selftest` offline y el gate remarkets-only aplicado antes del login"
  - "`33-LITERALS.md` — el censo, la disposición record-only de los cuatro alias de matriz, y el cierre de DT-07 con su evidencia"
  - "DT-07 **CERRADO**: `Titulo.mercado` / `Titulo.plazo` quedan `str` permanente, decidido sobre 2 191 filas de wire"
  - "la falsificación documentada de `29-DLOCK-RESPONSE-LITERAL.md:140-142` con su evidencia de código"
  - "`LIVE-MATZ-33` ampliado con el censo de valores pendiente de los 7 campos de matriz"
affects: [33-07]

actuals:
  tokens: 9800
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "censo por *path* con índices de lista colapsados a `[]`, para que dos modelos distintos con la misma clave de wire (`Segment.marketId` vs `InstrumentId.marketId`) no se mezclen en una fila"
    - "el censo registra el **tipo de runtime** al lado del valor, porque la rama `Literal` del walker valida sólo el tipo de los miembros — 'qué tipo llegó' es tan parte del censo como 'qué valor llegó'"
    - "`--selftest` offline con un valor deliberadamente fuera-de-set (`ZZZZZZ`) y un par de variantes de caja (`bCBA`/`bcba`): un SKIP queda distinguible de un extractor roto, y se prueba que el censo no normaliza"
    - "el gate de política corre ANTES del login: un SKIP no cuesta ni un round trip contra un host fuera de política"

key-files:
  created:
    - scripts/literal_census_33.py
    - .planning/phases/33-verificaci-n-en-vivo-en-modo-estricto-fixes/33-LITERALS.md
  modified:
    - packages/iol-client/src/iol_client/types.py
    - packages/iol-client/src/iol_client/models.py
    - .planning/ROADMAP.md

key-decisions:
  - "DT-07 se cierra en `str` **permanente** y no como diferimiento: el conjunto RESPONSE de `mercado` es `{\"1\"}` y el de `plazo` es `{\"T0\",\"T1\"}`, mientras que los parámetros de ENTRADA homónimos del propio cliente van por default en `\"bcba\"` y `\"t2\"`. Numérico-vs-nombre en un campo, disjuntos por caja en el otro. Un `Literal` derivado de la respuesta rechazaría los defaults de la librería"
  - "El censo de matriz se registra `SKIPPED — base URL fuera de política` y el script lleva el mismo gate D-MATZ-33 que el driver. No se rodeó el assert y no se reapuntó `PRIMARY_BASE_URL` a remarkets: misma decisión que 33-05, mismas dos razones (superficie de órdenes + credenciales emitidas para el host demo)"
  - "El censo lee el wire crudo por el transporte del propio cliente y NO el stream de divergencias: `literal_enforced=False` en las cinco `POLICY` hace que `walk_field:521-534` retorne temprano y nunca llame al sink. `29-DLOCK-RESPONSE-LITERAL.md:140-142` afirma lo contrario y queda falsificado por el código shipeado"
  - "La corrección del párrafo del D-lock NO se aplica en este plan: el artefacto está firmado (sebadlf, 2026-08-18) y corregir un artefacto firmado es decisión del firmante. Se registra la evidencia para que no haya que re-derivarla y se rutea a `LIVE-MATZ-33`"
  - "`Cotizacion.plazo` se registra como NO-EVIDENCIA con etiqueta explícita en el stdout del script y en el artefacto — pero el eco `t2` → `T2` sí prueba la normalización de caja, que es la mitad del argumento de DT-07"
  - "El dominio de ENTRADA de `mercado`/`plazo` queda **sin destino a propósito**: es scope rechazado (D-10), no trabajo pendiente. Darle un ticket lo haría parecer una deuda"

patterns-established:
  - "Un `Literal` no se cierra porque el conjunto observado sea chico: se cierra cuando el conjunto observado es el conjunto correcto. Un censo RESPONSE sobre un campo cuyo homónimo de INPUT tiene otro vocabulario es evidencia POSITIVA de que no se puede cerrar"
  - "Cuando un artefacto firmado contradice el código shipeado, el ejecutor registra la falsificación con su evidencia y rutea la corrección al firmante — no la aplica ni la ignora"

requirements-completed: []

coverage:
  - id: D34
    description: "El censo se toma del wire crudo y no del stream de divergencias, con la razón probada en el código: `literal_enforced=False` en las cinco `POLICY` hace que la rama `Literal` de `walk_field` retorne temprano sin llamar al sink (criterio 3, D-08)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "`grep -n '^POLICY = DecodePolicy' packages/*/src/*/_decode.py` → 5 líneas, séptimo posicional `False` en las cinco"
        status: pass
      - kind: other
        ref: "`_decode.py:521-534` transcripto en `33-LITERALS.md`: `member_ok = value in args if policy.literal_enforced else True` → fijo en True"
        status: pass
    human_judgment: false
  - id: D35
    description: "Los cuatro alias RESPONSE de matriz tienen disposición explícita record-only y ninguno se ensancha, cierra ni enforcea (criterio 3, D-09)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "`git diff --stat packages/matriz-client/src/matriz_client/{types,models}.py` → vacío"
        status: pass
      - kind: unit
        ref: "`uv run pytest packages/matriz-client/tests/test_decode.py packages/matriz-client/tests/test_types.py -q` → 84 passed"
        status: pass
      - kind: other
        ref: "las 7 filas de la tabla llevan `SKIPPED — base URL fuera de política` con su endpoint y `rows=0`; ninguna celda dice conjunto vacío"
        status: pass
    human_judgment: true
    rationale: "Decidir que un SKIP con causa nombrada es el resultado correcto —en vez de rodear el gate D-MATZ-33 para conseguir el número— es un juicio de política de seguridad contra presión de completitud, no un chequeo mecánico."
  - id: D36
    description: "DT-07 queda cerrado como `str` permanente con la evidencia RESPONSE registrada y su insuficiencia para un `Literal` de INPUT enunciada (criterio 3, D-10)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "2 191 filas `titulos[]` sobre los 6 tipos; `mercado` distinct=['1'], `plazo` distinct=['T0','T1'], types=['str'] en las 2 191"
        status: pass
      - kind: other
        ref: "contraste con los defaults de INPUT del propio cliente: `client.py:519` `mercado='bcba'`, `client.py:520` `plazo='t2'` — disjuntos de lo observado"
        status: pass
      - kind: other
        ref: "AST: `packages/iol-client/src/iol_client/types.py` sin `ClassDef` y sin ningún `Name` `Literal`; `__all__` sigue vacío"
        status: pass
    human_judgment: true
    rationale: "Que un conjunto observado de 2 191 filas sea insuficiente para cerrar un `Literal` no se decide por conteo: se decide entendiendo que el censo es RESPONSE-side y que el homónimo de INPUT tiene otro vocabulario."
  - id: D37
    description: "Ningún payload crudo del censo entró a git; el staging gitignored es el único hogar del wire (T-33-32, C-4)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "`git status --porcelain .planning/verification/captures/` → vacío tras las 7 escrituras del censo"
        status: pass
      - kind: other
        ref: "scan mecánico de los 20 valores de los cuatro `.env` contra `33-LITERALS.md` + los 3 archivos de código tocados: 0 coincidencias; 0 CUIT-like; 0 token-like"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-08-27
status: complete
---

# Phase 33 Plan 06: censo de `Literal` en vivo y cierre de DT-07 Summary

**El criterio 3 se cierra por la mitad que se podía cerrar, y la otra mitad queda registrada
como faltante en vez de fabricada: `DT-07` pasa de "diferido pendiente de censo" a **`str`
permanente, decidido**, con 2 191 filas de wire detrás y con la razón positiva —el conjunto que
IOL emite (`mercado={"1"}`, `plazo={"T0","T1"}`) es disjunto del que sus propios parámetros de
entrada mandan por default (`"bcba"`, `"t2"`)—; mientras que los siete campos de matriz se
registran `SKIPPED — base URL fuera de política`, sin rodear el gate D-MATZ-33 y sin que ningún
alias se mueva un byte. En el camino se falsificó, con el código shipeado en la mano, el párrafo
del D-lock firmado que decía que el stream de divergencias era el mecanismo de censo.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-27T01:10Z
- **Completed:** 2026-08-27T01:22Z
- **Tasks:** 2 de 2
- **Files created/modified:** 5 (2 nuevos, 3 modificados)

## Salida del censo (verbatim)

`scripts/literal_census_33.py` quedó **committeado** (`5c36b5f`), así que su texto completo no
se reproduce acá — la reproducibilidad la da el archivo.

### Self-test offline (sin red, sin credenciales)

```
$ uv run python scripts/literal_census_33.py --selftest
selftest-matriz synthetic details[].currency: rows=1 types=['str'] distinct=['ARS']
selftest-matriz synthetic details[].orderTypes[]: rows=2 types=['str'] distinct=['LIMIT', 'MARKET']
selftest-matriz synthetic instruments[].cficode: rows=2 types=['str'] distinct=['FXXXSX', 'ZZZZZZ']
selftest-matriz synthetic instruments[].instrumentId.marketId: rows=2 types=['str'] distinct=['ROFX']
selftest-matriz synthetic orders[].ordType: rows=2 types=['str'] distinct=['LIMIT', 'MARKET']
selftest-matriz synthetic segments[].marketId: rows=1 types=['str'] distinct=['ROFX']
selftest-iol synthetic titulos[].mercado: rows=2 types=['str'] distinct=['bCBA', 'bcba']
selftest-iol synthetic titulos[].plazo: rows=2 types=['str'] distinct=['t1', 't2']
SELFTEST: PASS
```

Los dos casos plantados son deliberados: `ZZZZZZ` está **fuera** del conjunto declarado de
`CFICode` y el censo lo reporta (que es exactamente lo que el stream de divergencias no haría), y
`bCBA`/`bcba` prueba que el censo **no normaliza caja** — load-bearing para la conclusión de
DT-07.

### Corrida en vivo

```
$ uv run python scripts/literal_census_33.py
matriz-client: SKIPPED — base URL fuera de política (D-MATZ-33: la verificación es remarkets-only)
iol-client get_instruments_by_type[obligacionesNegociables] titulos[].mercado: rows=883 types=['str'] distinct=['1']
iol-client get_instruments_by_type[obligacionesNegociables] titulos[].plazo: rows=883 types=['str'] distinct=['T1']
iol-client get_instruments_by_type[titulosPublicos] titulos[].mercado: rows=207 types=['str'] distinct=['1']
iol-client get_instruments_by_type[titulosPublicos] titulos[].plazo: rows=207 types=['str'] distinct=['T1']
iol-client get_instruments_by_type[cedears] titulos[].mercado: rows=972 types=['str'] distinct=['1']
iol-client get_instruments_by_type[cedears] titulos[].plazo: rows=972 types=['str'] distinct=['T1']
iol-client get_instruments_by_type[acciones] titulos[].mercado: rows=99 types=['str'] distinct=['1']
iol-client get_instruments_by_type[acciones] titulos[].plazo: rows=99 types=['str'] distinct=['T1']
iol-client get_instruments_by_type[letras] titulos[].mercado: rows=29 types=['str'] distinct=['1']
iol-client get_instruments_by_type[letras] titulos[].plazo: rows=29 types=['str'] distinct=['T1']
iol-client get_instruments_by_type[cauciones] titulos[].mercado: rows=1 types=['str'] distinct=['1']
iol-client get_instruments_by_type[cauciones] titulos[].plazo: rows=1 types=['str'] distinct=['T0']
--- iol agregado sobre los 6 tipos ---
iol-client get_instruments_by_type[TOTAL] titulos[].mercado: rows=2191 types=['str'] distinct=['1']
iol-client get_instruments_by_type[TOTAL] titulos[].plazo: rows=2191 types=['str'] distinct=['T0', 'T1']
iol-client get_quote plazo: NO-EVIDENCIA (eco de los defaults enviados) distinct=['T2']
CENSUS: matriz=SKIPPED iol=RAN
```

**Ventana:** ARG miércoles 22:15–22:20, mercado **cerrado**. Está declarado en el artefacto: el
conjunto observado es un piso incluso como censo RESPONSE.

## Los nueve campos, por resultado

### matriz — 7 campos, `SKIPPED — base URL fuera de política`

Ninguna fila dice "cero valores observados": todas dicen `SKIPPED` con causa y endpoint. La
distinción es la de T-33-37 y la misma que 33-05 estableció.

| Campo | Modelo | Alias | Conjunto declarado | Observado | Filas |
|---|---|---|---|---|---:|
| `marketId` | `Segment` (`:283`) | `MarketId` | `ROFX` | SKIPPED | 0 |
| `marketId` | `InstrumentId` (`:262`) | `MarketId` | `ROFX` | SKIPPED | 0 |
| `cficode` | `Instrument` (`:291`) | `CFICode` | 9 códigos | SKIPPED | 0 |
| `cficode` | `InstrumentDetail` (`:303`) | `CFICode` | 9 códigos | SKIPPED | 0 |
| `currency` | `InstrumentDetail` (`:315`) | `Currency` | `ARS`, `USD` | SKIPPED | 0 |
| `orderTypes` | `InstrumentDetail` (`:316`) | `list[OrderType]` | 4 tipos | SKIPPED | 0 |
| `ordType` | `Order` (`:352`) | `OrderType` | 4 tipos | SKIPPED | 0 |

**Lo que sí se pudo afirmar sin wire:** los cuatro alias decodifican **sin enforcement** hoy, y
un valor fuera de set vuelve byte-por-byte inalterado — `POLICY` de matriz pasa
`literal_enforced=False` **y** `scalar_passthrough=True` (`_decode.py:136`), así que ni corre el
chequeo de membresía ni se toma el fallback de escalar. Los 84 casos de `test_decode.py` +
`test_types.py` pinean eso y siguen verdes.

**Ningún valor observado cayó fuera de su conjunto declarado — porque no hubo ninguna
observación.** No se normalizó nada porque no había nada que normalizar.

### iol — 2 campos, medidos

| Campo | Declarado | Observado | Tipo runtime | Filas |
|---|---|---|---|---:|
| `Titulo.mercado` (`models.py:228`) | `str` | **`{"1"}`** | `str` ×2 191 | 2 191 |
| `Titulo.plazo` (`models.py:231`) | `str` | **`{"T0", "T1"}`** | `str` ×2 191 | 2 191 |
| `Cotizacion.plazo` (`get_quote`) | `str \| None` | `{"T2"}` — **NO-EVIDENCIA** | `str` | 1 |

## El texto exacto agregado a `iol_client/types.py`

```
**DT-07 is CLOSED: ``mercado`` and ``plazo`` stay ``str``, permanently.** The
live census ran in Phase 33 (plan 33-06) over 2 191 ``Titulo`` rows across the
six instrument types, and it is the census -- not its absence -- that decides
the outcome. The RESPONSE side emits ``mercado`` as ``{"1"}`` and ``plazo`` as
``{"T0", "T1"}``, while the INPUT parameters these very functions default to are
``mercado="bcba"`` and ``plazo="t2"``: the two vocabularies are numeric-vs-name
for one field and disjoint-by-case for the other. A ``Literal`` closed on the
observed response set would reject the library's own defaults, and the set a
vendor *emits* is in no case provably the set it *accepts* -- the only way to
observe the input domain is a deliberate 4xx sweep against a live brokerage
account, which D-10 rejects. An incomplete ``Literal`` breaks legitimate caller
input, which is strictly worse than ``str``. Evidence, row counts and full
reasoning:
``.planning/phases/33-verificaci-n-en-vivo-en-modo-estricto-fixes/33-LITERALS.md``.

This closure is scoped to those two RESPONSE fields. :data:`iol_client.InstrumentType`
is a ``Literal`` over an **input** parameter and is a different question that the
D-lock explicitly leaves open; it is unaffected.
```

El archivo sigue sin un solo alias `Literal`, sin `ClassDef`, y con `__all__` vacío.

## Task Commits

1. **Task 1: censo de wire crudo** — `5c36b5f` (feat, `scripts/literal_census_33.py`)
2. **Task 2: `33-LITERALS.md` + cierre de DT-07** — `35043ef` (docs, artefacto + `types.py` + `models.py` + ROADMAP)

## Files Created/Modified

- `scripts/literal_census_33.py` *(nuevo, ~370 líneas)* — walker de wire crudo por path con
  índices colapsados a `[]`, registro de tipo de runtime junto al valor, escritura de todo
  payload vía `verification.capture.capture(...)`, gate remarkets-only pre-login y `--selftest`
  offline.
- `.planning/phases/33-.../33-LITERALS.md` *(nuevo)* — las cuatro secciones del criterio 3.
- `packages/iol-client/src/iol_client/types.py` — DT-07 CERRADO; cero `Literal` agregados.
- `packages/iol-client/src/iol_client/models.py` — los dos docstrings que apuntaban hacia
  adelante (`Titulo`, `Instrumento`) registran el resultado. Cero anotaciones cambiadas.
- `.planning/ROADMAP.md` — `LIVE-MATZ-33` ampliado.

## Decisions Made

Además de las del frontmatter, en ejecución:

1. **El censo registra el tipo de runtime al lado del valor.** La rama `Literal` del walker
   valida **sólo** el tipo de los miembros del alias, así que "qué tipo llegó" es tan parte del
   censo como "qué valor llegó". Es lo que permitió afirmar que las 2 191 filas de iol llegan
   `str` y, con eso, explicar positivamente el `DIVERGENCES=0` de 33-05 en vez de tratarlo como
   un misterio: no había nada **de tipo** que reportar, y valores no se reportan nunca.
2. **El gate de matriz corre antes del login.** Un SKIP de política no debe costar ni un round
   trip contra un host fuera de política — sería una request que la política existe para evitar.
3. **`--selftest` lleva un valor fuera-de-set plantado a propósito.** Sin él, un extractor roto
   y un endpoint sin datos producen la misma tabla vacía, que es el falso limpio de P-02. Con él,
   el SKIP de matriz es demostrablemente "no corrió", no "no encontró".
4. **El dominio de ENTRADA queda sin destino a propósito.** Ver Deviations #3.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] El censo de matriz no puede correr sin rodear el gate D-MATZ-33, y rodearlo está prohibido**

- **Found during:** Task 1, al construir el `Client()` de matriz
- **Issue:** El plan pide un censo de los siete campos RESPONSE de matriz sobre wire vivo, y siete
  de los nueve campos del alcance son de matriz. Pero `PRIMARY_BASE_URL` apunta a un host que no
  es el sandbox de remarkets, al que la política de la Phase 5 (**D-MATZ-33**) restringe toda
  verificación del paquete. El plan ofrece la categoría `SKIPPED — credenciales` para un paquete
  que no autentica, y matriz **sí** autentica (`preflight_33.py` → `AUTH OK`): esa categoría
  habría descrito mal la causa y habría mandado la reparación al lugar equivocado.
- **Fix:** El script lleva **el mismo gate** que el driver, aplicado antes del login, y registra
  `SKIPPED — base URL fuera de política (D-MATZ-33)` — la categoría que 33-05 creó para
  exactamente esta situación. **No se rodeó el assert y no se reapuntó `PRIMARY_BASE_URL` a
  remarkets**, por las dos mismas razones que 33-05: (a) matriz tiene superficie de entrada de
  órdenes y el gate es el mecanismo que impide que una verificación toque una venue que no es la
  acordada (P-05); (b) las credenciales del `.env` fueron emitidas para el host demo y mandarlas
  a otro vendor sería una fuga disfrazada de fix de configuración. Las siete filas de la tabla
  llevan su alias, su conjunto declarado, su endpoint y el marcador — nunca un conjunto vacío.
  Ruteado a `LIVE-MATZ-33`, que ya existía en ROADMAP § Backlog y se amplió con este requisito.
- **Files modified:** `scripts/literal_census_33.py`, `33-LITERALS.md`, `.planning/ROADMAP.md`
- **Verification:** `git diff --stat packages/matriz-client/src/matriz_client/{types,models}.py`
  vacío; 84 tests de decode/types verdes; el SKIP se imprime sin emitir una sola request
- **Committed in:** `5c36b5f` + `35043ef`

---

**2. [Rule 1 - Bug] `29-DLOCK-RESPONSE-LITERAL.md:140-142` afirma que el stream de divergencias es el mecanismo de censo, y el código shipeado lo falsifica**

- **Found during:** Task 1, al elegir la fuente del censo
- **Issue:** El párrafo firmado dice *"the observable divergence stream is the census-gathering
  mechanism: every out-of-set value that shows up in a Phase 33 driver run is evidence"*. Es
  falso: `literal_enforced` es `False` en las **cinco** constantes `POLICY`
  (`_decode.py:136/136/140/141/136`), así que `member_ok = value in args if
  policy.literal_enforced else True` queda fijo en `True` y `walk_field:521-534` toma el
  `return value` temprano para todo valor fuera de set con el tipo correcto. El sink nunca se
  llama. Consecuencia material: **el `DIVERGENCES=0` de iol de 33-05 no era evidencia de que los
  valores estuvieran dentro del set declarado** — era evidencia de que nadie los miró. Haber
  tomado el censo de esa fuente habría producido tablas vacías reportadas como "todo dentro de
  set": el falso limpio exacto que P-02 prohíbe.
- **Fix:** El censo se toma del **payload crudo**, por el transporte del propio cliente
  (`_core.build_*_request` → `Client._request` → `.json()`), sin agregar capa HTTP. La
  falsificación queda escrita en `33-LITERALS.md § Method` con las cinco líneas `POLICY` y el
  bloque de código citados. **El D-lock NO se editó**: está firmado (sebadlf, 2026-08-18) y
  corregir un artefacto firmado es decisión del firmante, no del ejecutor. La corrección se
  rutea a `LIVE-MATZ-33`, que es donde el párrafo vuelve a ser load-bearing, con la evidencia
  adjunta para que no haya que re-derivarla.
- **Files modified:** `33-LITERALS.md`, `.planning/ROADMAP.md` (ninguna copia de `_decode.py`)
- **Verification:** `grep -n '^POLICY = DecodePolicy' packages/*/src/*/_decode.py` → 5 líneas,
  séptimo posicional `False` en las cinco; `uv run pytest packages/iol-client
  packages/matriz-client -q` → 702 passed
- **Committed in:** `35043ef`

---

**3. [Rule 2 - Missing critical] El plan pide rutear "todo lo que no se resuelve" a un destino nombrado, y una de las tres cosas abiertas no debe tener destino**

- **Found during:** Task 2, al escribir `## Carry-forward`
- **Issue:** El dominio de **ENTRADA** de `mercado`/`plazo` queda sin observar. Rutearlo a un
  ticket lo habría dejado como deuda pendiente en el backlog, cuando es **scope rechazado**: la
  única forma de observarlo es el barrido deliberado de 4xx contra una cuenta de brokerage viva
  que D-10 rechaza y que la prohibición P-05 prohíbe. Un lector futuro habría leído el ticket
  como trabajo por hacer y lo habría hecho.
- **Fix:** La fila lleva `Ninguno — deliberadamente sin destino`, con la razón escrita y la
  condición de re-apertura explícita (una fuente que no requiera tráfico de error: documentación
  verificable del vendor, o un endpoint de catálogo de plazos). Las otras dos filas del
  carry-forward sí llevan destino nombrado (`LIVE-MATZ-33` en ambas).
- **Files modified:** `33-LITERALS.md`
- **Verification:** cero celdas `TBD` / `later` / `a futuro` en la sección
- **Committed in:** `35043ef`

---

**4. [Rule 1 - Bug] `iol_client/models.py` seguía apuntando hacia adelante a la decisión que este plan tomó**

- **Found during:** Task 2, tras editar `types.py`
- **Issue:** El plan enumera sólo `types.py` en `files_modified`, pero `models.py:214-231`
  (`Titulo`) y `:174-179` (`Instrumento`) dicen *"la promoción a `Literal` es trabajo de Phase 33
  con un censo vivo detrás (D-09 / DT-07)"*. Dejarlos habría producido un paquete donde
  `types.py` dice CERRADO y `models.py` dice pendiente, sobre el mismo campo — la clase de
  inconsistencia que hace que un lector futuro no sepa cuál creer.
- **Fix:** Edición **de docstring solamente** en los dos lugares, registrando el resultado con
  su evidencia y su puntero a `33-LITERALS.md`. **Cero anotaciones cambiadas, cero `Literal`
  agregados**, `Titulo.mercado` y `Titulo.plazo` siguen `str`.
- **Files modified:** `packages/iol-client/src/iol_client/models.py`
- **Verification:** `uv run pytest packages/iol-client packages/matriz-client -q` → 702 passed;
  `uv run mypy` → Success en 75 archivos; el AST gate de `types.py` sigue en 0
- **Committed in:** `35043ef`

---

**Total deviations:** 4 auto-fixed (2× Rule 1, 1× Rule 2, 1× Rule 3)
**Impact on plan:** Ninguno sobre el scope. La #1 es el resultado más consecuente del plan y la
razón por la que siete de los nueve campos quedan sin medir — se registra como falta, no se
fabrica ni se resuelve rodeando una política de seguridad. La #2 cambia la fuente del censo
antes de que existiera un solo número, y de paso reinterpreta un cero de 33-05. Cero scope creep:
no se tocó ningún archivo de `matriz-client`, ninguna copia de `_decode.py`, ningún driver,
ninguna anotación, y no se reparó ninguna de las 19 fallas ni ninguno de los 43 errores de mypy
pre-existentes de `verification/`.

## Authentication Gates

- **`iol-client`** — `AUTH OK`; el censo corrió sus 7 requests (6 listados + 1 eco).
- **`matriz-client`** — autentica (`AUTH OK` en `preflight_33.py`), pero el censo **no llega a
  autenticar**: el gate de política corre antes del login. Ver Deviations #1.
- **`higyrus-client`** — irrelevante para este plan: no tiene ningún campo RESPONSE con alias
  `Literal` ni ninguno de los dos campos de DT-07. El SKIP de `LIVE-HIGY-33` no le quita nada a
  este censo, y el artefacto lo dice explícitamente para que la ausencia no se lea como omisión.
- **`ambito-financiero-client`, `market-data-client`** — fuera del alcance de los nueve campos.

## Issues Encountered

- **7 de los 9 campos del alcance quedaron sin medir**, todos de matriz, todos por la misma
  causa de política. El criterio 3 queda por lo tanto **parcialmente cerrado**: la disposición de
  los cuatro alias está tomada (record-only, confirmada por lectura de código y por 84 tests), y
  la mitad de valores observados sigue abierta. 33-07 tiene que surfacearlo, no darlo por cerrado.
- **El `29-DLOCK-RESPONSE-LITERAL.md` firmado contiene un párrafo falso** que este plan no puede
  corregir por sí mismo. Queda con evidencia adjunta y destino nombrado.
- **La ventana fue de mercado cerrado** (ARG miércoles 22:15). Para iol no invalida el censo
  —`get_instruments_by_type` devuelve el catálogo, no una sesión— pero sí lo hace un piso: un
  `plazo` `T3` o un `mercado` distinto de `"1"` podrían existir en otra ventana. Está declarado.
- **`.planning/config.json` quedó modificado en el working tree** (`_auto_chain_active`) por el
  paso de init del workflow, no por este plan. No se commiteó: mismo criterio que 33-04 y 33-05.

## Carry-forwards

1. **El censo de valores de matriz sigue abierto** — `LIVE-MATZ-33`, ampliado en este plan.
   `scripts/literal_census_33.py` ya lleva el gate y corre completo apenas haya un
   `PRIMARY_BASE_URL` de remarkets con credenciales emitidas para ese host.
2. **`29-DLOCK-RESPONSE-LITERAL.md:140-142` necesita corrección del firmante** — evidencia
   completa en `33-LITERALS.md § Method`, ruteado a `LIVE-MATZ-33`.
3. **DT-07 está cerrado y no vuelve a 33-07.** Cualquier trabajo futuro sobre `mercado`/`plazo`
   parte de `str` permanente, no de "pendiente de censo".
4. **El `DIVERGENCES=0` de iol de 33-05 hay que leerlo con el matiz de este plan**: es cierto
   para divergencias de **tipo** —las 2 191 filas llegan `str` como se declara— y estructuralmente
   mudo sobre valores. 33-07 no debe inferir de ese cero que los valores de iol están dentro de
   ningún conjunto.
5. **El dominio de ENTRADA de `mercado`/`plazo` es scope rechazado, no deuda.** Si alguien
   propone un barrido de 4xx para cerrarlo, la respuesta ya está escrita en D-10 y en P-05.

## Known Stubs

Ninguno. El script está cableado a fuentes reales: los 7 requests de iol salieron por el
transporte del propio cliente contra la API en vivo y sus payloads están en el staging
gitignored; el gate de matriz consulta `client._state.base_url` real, no un flag; y el
`--selftest` ejercita el mismo `collect_paths` que la corrida en vivo, no una copia. Las siete
celdas `SKIPPED` de la tabla de matriz **no son placeholders pendientes de completar** — son el
resultado, con su causa medida y su destino nombrado. Cada número de `33-LITERALS.md` sale de la
transcripción de esta sesión o de una línea de código citada por archivo y número.

## TDD Gate Compliance

| Gate | Commit | Evidencia |
|---|---|---|
| RED | — | No hay ciclo TDD formal: el plan es de censo y documentación (`type: execute`, ninguna task con `tdd="true"`), y no agrega comportamiento de librería — las dos ediciones bajo `packages/` son docstrings. La no-vacuidad se demuestra por **falsificación plantada**: `--selftest` incluye `ZZZZZZ` (fuera del set declarado de `CFICode`) y el par `bCBA`/`bcba`; si el walker filtrara por membresía o normalizara caja, los dos casos fallarían el self-test. |
| GREEN | `5c36b5f` → `35043ef` | `SELFTEST: PASS`; censo en vivo con 2 191 filas; 702 tests de iol+matriz verdes; `uv run mypy` Success en 75 archivos. |

Sin fase REFACTOR: no hizo falta.

## Verification Evidence

| Gate | Resultado |
|---|---|
| `uv run python scripts/literal_census_33.py --selftest` | `SELFTEST: PASS` — 8 paths, incluido el fuera-de-set plantado |
| `uv run python scripts/literal_census_33.py` | 1 línea SKIPPED (matriz) + 15 líneas de censo (iol) + eco NO-EVIDENCIA |
| Filas inspeccionadas, iol | **2 191** `titulos[]` sobre 6 tipos (883+207+972+99+29+1) |
| `Titulo.mercado` observado | `{"1"}`, `types=['str']` en las 2 191 |
| `Titulo.plazo` observado | `{"T0", "T1"}`, `types=['str']` en las 2 191 |
| `Cotizacion.plazo` (eco) | `{"T2"}` — etiquetado NO-EVIDENCIA en stdout y en el artefacto |
| `git status --porcelain .planning/verification/captures/` | **vacío** (7 payloads escritos, 0 en git) |
| `git diff --stat packages/matriz-client/src/matriz_client/{types,models}.py` | **vacío** |
| `uv run pytest packages/matriz-client/tests/test_decode.py packages/matriz-client/tests/test_types.py -q` | **84 passed** |
| `uv run pytest packages/iol-client packages/matriz-client -q` | **702 passed** |
| AST: `Literal` o `ClassDef` en `iol_client/types.py` | **0** — exit 0 |
| `grep -c 'DT-07' 33-LITERALS.md` | **6** (≥1 requerido) |
| `grep -c 'DT-07' packages/iol-client/src/iol_client/types.py` | **1** (≥1 requerido) |
| Las 4 secciones de `33-LITERALS.md` | todas presentes |
| Filas de la tabla de matriz | **7**, cada una con alias, set declarado, endpoint y marcador `SKIPPED` |
| `grep -n '^POLICY = DecodePolicy' packages/*/src/*/_decode.py` | 5 líneas, séptimo posicional `False` en las cinco |
| Scan de fuga: 20 valores de los 4 `.env` contra el artefacto + los 3 archivos de código | **0 coincidencias** |
| CUIT-like (11 dígitos) / token-like (`Bearer`, `eyJ…`) en `33-LITERALS.md` | **0 / 0** |
| Celdas `TBD` / `later` / `a futuro` en `## Carry-forward` | **0** |
| `uv run mypy` | Success: no issues found in 75 source files |
| `uv run mypy scripts/literal_census_33.py` | Success |
| `uv run ruff check . && uv run ruff format --check .` | limpio, 249 archivos formateados |
| Deleciones en los 2 commits | **0 / 0** |

## Self-Check: PASSED

- Los 2 archivos declarados en `key-files.created` existen en disco, y los 3 de
  `key-files.modified` están en el diff de `35043ef`.
- Los 2 hashes declarados (`5c36b5f`, `35043ef`) existen en `git log`.
- Las 17 líneas de salida del censo están copiadas **verbatim** del stdout de esta sesión.
- Los conteos por tipo suman el total reportado: 883+207+972+99+29+1 = **2 191**, que es el
  `rows` de la línea `[TOTAL]` — dos caminos independientes al mismo número.
- Los números de línea citados (`types.py:38/44/50/95`, `models.py:262/283/291/303/315/316/352`
  de matriz; `models.py:228/231`, `client.py:63/519/520` de iol; `_decode.py:136` ×5 y `:521`)
  se verificaron uno por uno con `grep -n` / `awk` antes de escribir el artefacto.
- **`LIVE-TYP-01` queda deliberadamente en `Pending`.** Los siete planes de la Phase 33 cargan
  ese ID; con 7 de los 9 campos del criterio 3 sin medir, cerrarlo acá sería una completitud
  demostrablemente falsa. Mismo precedente que 33-01, 33-03, 33-04 y 33-05. Queda para 33-07.
