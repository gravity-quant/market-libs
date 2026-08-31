# Phase 42 — Lectura fresca del wire de `/instruments` y `/segments`

> **Qué es este documento.** La evidencia **committeada** y **PII-free** producida por el criterio 5
> de la Phase 42, y la precondición cross-fase que `REQUIREMENTS.md § Dependencias cross-fase`
> declara: *"Lectura fresca del wire de `/instruments` + `/segments` — producida en Phase 42
> (criterio 5), consumida por Phase 43 (SHAPE-01)"*.
>
> **Por qué existe en vez de sólo las capturas.** El payload crudo vive en
> `.planning/verification/captures/`, que está gitignored (`.gitignore:53`). Si la Phase 43 corre en
> otro clone, otro worktree, o después de un `git clean -xdf`, esas capturas **no existen**. Este
> archivo sí. Por eso lleva el `schema_of` adentro (D-08, mitad 2).

---

## 1. Sobre de la lectura

Corrida en vivo del driver completo contra el target `develop`, autenticada por Auth0
`client_credentials`. Habilitada por el checkpoint humano bloqueante del plan 42-01
(`gate="blocking-human"`, respuesta del operador transcrita verbatim en `42-01-SUMMARY.md`).

| Endpoint | `client_function` | `captured_at` (UTC ISO, verbatim del envelope) | `base_url` | `n_rows` | Filas medidas | Captura (staging gitignored) |
|----------|-------------------|------------------------------------------------|------------|----------|---------------|------------------------------|
| `/instruments` | `get_instruments` | `2026-08-31T21:27:42.854194+00:00` | `https://market-data-develop.bbsa.com.ar/api` | `null` | `50` (`len(items)`) | `.planning/verification/captures/market-data-wire-instruments-42.json` |
| `/instruments/segments` | `get_segments` | `2026-08-31T21:27:43.256969+00:00` | `https://market-data-develop.bbsa.com.ar/api` | `null` | `4` (`len(segments)`) | `.planning/verification/captures/market-data-wire-segments-42.json` |

**Comando exacto que produjo la corrida:**

```
uv run --package market-data-client python main_market_data.py
```

**Exit code del driver: `0`.**

Línea de resumen del driver, verbatim:

```
SUMMARY: PASS=23 FAIL=0 SKIPPED=18 FINDING=2 DIVERGENCES=18 HANDLER_ERRORS=0
```

Y las dos líneas de probe que produjeron esta lectura:

```
PROBE instruments_sync: PASS instruments=50
PROBE segments_sync: PASS segments=4
```

**Corrida de LECTURA.** `MARKET_DATA_VERIFY_MUTATING` **no** se seteó en ninguna invocación, así que
las 18 pruebas mutantes salieron `SKIPPED (mutating, guard off)` y
`mutation_gate_refusal_sync` / `_async` confirmaron el rechazo con `0 HTTP, 0 Auth0`.
`git hash-object verification/mutation_gate.py` = `6bdaec006cc16f7c8dbfac41701712a9085c691b`,
idéntico al valor pinneado (T-42-02).

### Por qué `n_rows` es `null` — y por qué eso es un dato, no un defecto

`n_rows` se computa como `len(raw) if isinstance(raw, list) else None`. Salió `null` en los dos
endpoints porque **el wire no devuelve un array desnudo**: devuelve un *sobre paginado*. El conteo
real de filas está en la columna "Filas medidas" de la tabla, derivado de la colección de adentro
del sobre (`items` para `/instruments`, `segments` para `/instruments/segments`).

Que el top level sea un `dict` y no una `list` es una propiedad de forma que la Phase 43 necesita
saber, y tiene una consecuencia operativa concreta documentada en § 4.1.

---

## 2. Schema medido

`schema_of(raw)` reduce el payload a **claves + nombres de tipo, nunca valores**
(`verification/schema.py:27-40`). Es PII-free por construcción: cada hoja de los dos bloques de
abajo es un nombre de tipo Python, no un dato del wire.

### `/instruments` → `get_instruments`

```json
{
  "catalogue": {
    "age_seconds": "float",
    "instruments": "int",
    "last_error": "NoneType",
    "stale": "bool"
  },
  "count": "int",
  "items": [
    {
      "active": "NoneType",
      "currency": "str",
      "days_to_maturity": "int",
      "expired": "bool",
      "market_id": "str",
      "maturity": "str",
      "outright": "bool",
      "segment": "str",
      "subscribed": "bool",
      "symbol": "str"
    }
  ],
  "limit": "int",
  "offset": "int",
  "total": "int"
}
```

### `/instruments/segments` → `get_segments`

```json
{
  "catalogue": {
    "age_seconds": "float",
    "instruments": "int"
  },
  "segments": [
    {
      "live_instruments": "int",
      "segment": "str"
    }
  ]
}
```

**Nota de lectura para la Phase 43:** por la semántica de `schema_of` sobre listas
(`[schema_of(primer_elemento)]`), los objetos dentro de `items` y `segments` describen la forma de
la **primera fila** de una colección de 50 y 4 filas respectivamente. `active: "NoneType"` significa
que esa clave vino `null` **en esa fila**, no que el campo sea siempre nulo — es exactamente el mismo
alcance de muestreo que tiene el baseline del 2026-07-31 contra el que se compara, así que el delta
de § 4 es una comparación entre iguales.

---

## 3. NO AUTORITATIVO — marca explícita del baseline del 2026-07-31

Los dos baselines committeados

- `.planning/verification/schemas/market-data-client/get-instruments.json`
  (`captured_at: 2026-07-31T16:49:30.691111+00:00`)
- `.planning/verification/schemas/market-data-client/get-segments.json`
  (`captured_at: 2026-07-31T16:49:31.056229+00:00`)

quedan declarados **NO AUTORITATIVOS** para SHAPE-01. La referencia de la Phase 43 es **esta lectura
fresca** (§ 1 y § 2), no esos archivos. Es la instrucción que el ROADMAP ya daba en el nivel de
milestone:

> *"SHAPE-01 se corrige contra la lectura fresca de la Phase 42, no contra el baseline congelado del
> 2026-07-31. Ese es el motivo de que vivo vaya antes que shape, y no al revés."* — `ROADMAP.md:54`

### Por qué no se refrescaron los baselines

**No es un olvido: es el contrato.** `_write_schema_snapshot` (`main_market_data.py:457-522`) es
**write-once / no-overwrite-on-drift por diseño (D-25)**:

- Primer run: escribe el envelope y termina.
- Runs subsiguientes con schema **igual**: no-op.
- Runs subsiguientes con schema **distinto**: emite un finding `SHAPE` OPEN y **nunca** pisa el
  baseline — literalmente `"baseline schema difiere; NO se sobreescribe (D-25)"`.

Por eso el baseline no puede producir la evidencia fresca de esta fase, y por eso esta fase produce
un artefacto aparte en vez de refrescarlo. La corrida de hoy **verificó** esa propiedad en vez de
asumirla: después de la corrida los dos archivos siguen con su `captured_at` del **2026-07-31** y
ninguno de los dos aparece en `git status --porcelain` (T-42-15).

`_write_schema_snapshot` **no se modificó** en esta fase, ni se le agregó un modo overwrite.

---

## 4. Delta contra el baseline

Comparación clave por clave del `schema` fresco contra el `schema` de cada baseline committeado,
recorriendo el árbol completo (incluidas las claves anidadas bajo `catalogue`, `items[]` y
`segments[]`):

### `Instrument` (`/instruments`)

- Claves presentes en la lectura fresca y **ausentes** en el baseline: **ninguna**.
- Claves presentes en el baseline y **ausentes** en la lectura fresca: **ninguna**.
- Nombres de tipo en claves compartidas: **sin cambios**.

**El delta es vacío. El schema es idéntico al del 2026-07-31.**

### `Segment` (`/instruments/segments`)

- Claves presentes en la lectura fresca y **ausentes** en el baseline: **ninguna**.
- Claves presentes en el baseline y **ausentes** en la lectura fresca: **ninguna**.
- Nombres de tipo en claves compartidas: **sin cambios**.

**El delta es vacío. El schema es idéntico al del 2026-07-31.**

### Qué significa un delta vacío (y qué NO significa)

**Significa** que el wire no se movió en un mes, así que la descripción del backlog
`SHAPE-MD-REF-33` sigue siendo una descripción fiel del wire de hoy, re-medida en vivo: `Instrument`
declara `marketId` e `instrumentType` que el wire no manda, y no declara `market_id`, `currency`,
`days_to_maturity`, `maturity`, `outright`, `subscribed` ni `active` que sí manda; `Segment` declara
`marketSegmentId`, `marketId` y `description` mientras el wire manda `segment` y `live_instruments`
— **conjuntos disjuntos**. La Phase 43 puede trabajar sobre esa base sin re-medir.

**NO significa** que los baselines pasen a ser autoritativos. La marca de § 3 se mantiene: son
autoritativos *cero* archivos fechados 2026-07-31; lo que es autoritativo es la medición de hoy, que
resulta coincidir. Un delta vacío es un **resultado** de la re-medición, no una excusa para no
haberla hecho — y la distinción importa porque la Phase 43 debe poder citar una fecha de esta
sesión.

### 4.1. Observación operativa para la Phase 43: de dónde salió la disposición campo por campo

La corrida produjo, por primera vez en el ledger de `market-data-client`, los **28 findings de
divergencia campo por campo** de `Instrument` y `Segment` (14 triples distintos × las dos
superficies) que el criterio 1 de la Phase 43 consume directamente:

| Modelo | Especie | Campos | FIDs sync | FIDs async |
|--------|---------|--------|-----------|------------|
| `Instrument` | `extra` (wire manda, modelo no declara) | `active`, `currency`, `days_to_maturity`, `market_id`, `maturity`, `outright`, `subscribed` | F-205 … F-211 | F-229 … F-235 |
| `Instrument` | `missing` (modelo declara, wire no manda) | `marketId`, `instrumentType` | F-212, F-213 | F-236, F-237 |
| `Segment` | `extra` | `live_instruments`, `segment` | F-214, F-215 | F-238, F-239 |
| `Segment` | `missing` | `marketSegmentId`, `marketId`, `description` | F-216, F-217, F-218 | F-240, F-241, F-242 |

**De dónde salen — y de dónde NO.** Salen del **censo de divergencias del decode**
(`verification/divergences.py:176`, la línea `DIVERGENCES=18` del SUMMARY). **No** salen de
`_emit_shape`, el SHAPE-diff del propio driver.

`_emit_shape` **no se ejecutó** para estos dos endpoints. La razón es la forma del sobre documentada
en § 1: los dos probes derivan su muestra con
`sample = raw[0] if isinstance(raw, list) and raw else None` (`main_market_data.py:1001` y `:1041`),
y como `raw` es el **sobre paginado** (`dict`) y no un array desnudo, `sample` queda en `None` y el
SHAPE-diff se saltea en silencio. Verificable en el ledger: existen findings con el formato de
`_emit_shape` (`"wire-only field … en MarketDataSnapshot"`, `"… en Symbol"`, `"… en CalendarConfig"`)
y **cero** con ese formato para `Instrument` o `Segment`.

**Consecuencia práctica:** la evidencia **no se perdió** —el censo de divergencias la produjo
completa, y es la que está tabulada arriba— pero el SHAPE-diff del driver está **inerte** justo para
los dos modelos que la Phase 43 tiene que arreglar. Es una condición **preexistente** del driver, no
introducida por esta fase, y queda anotada en `deferred-items.md` de esta fase. La Phase 43 debería
saberlo antes de apoyarse en `_emit_shape` para demostrar su antes/después del criterio 2: hoy ese
camino no reporta nada para `Instrument`/`Segment`, así que un "cero findings" post-fix sería un
falso verde.

---

## 5. Dónde vive el crudo y por qué no está acá

El payload crudo de los dos endpoints vive **exclusivamente** en:

- `.planning/verification/captures/market-data-wire-instruments-42.json`
- `.planning/verification/captures/market-data-wire-segments-42.json`

Ese directorio está **gitignored** (`.gitignore:53`, con el comentario
*"Verificación en vivo: staging de capturas crudas (PII) — nunca committeable (D-11)"*). Es el
**único hogar legal** del payload crudo con PII (C-4 / D-11 / T-33-32), y `capture()` escribe
únicamente ahí por construcción (`verification/capture.py:33-50`). Los dos archivos existen sólo en
el working tree del ejecutor de esta corrida.

De cada envelope, lo único que cruzó a git es lo que está en este documento: `captured_at`,
`endpoint`, `client_function`, `base_url`, conteos de filas, rutas de archivo y la salida de
`schema_of`. La clave `payload` **no se transcribió** y no debe transcribirse nunca (T-42-05).

**La consecuencia práctica para la Phase 43:** si corre en otro clone, en otro worktree, o después de
un `git clean -xdf`, las dos capturas **no van a existir** — y este documento es toda la evidencia
disponible. Por eso lleva el schema adentro en vez de limitarse a apuntar a las rutas. Si la Phase 43
necesita el crudo (valores concretos, no forma), tiene que **re-correr el driver en vivo** con su
propia autorización humana; no puede recuperarlo de git, por diseño.

---

## 6. Qué NO decide este documento

Esta lectura es una **medición**, no una disposición. La Phase 42 no adelanta ni prejuzga nada de lo
que sigue, que es trabajo de la Phase 43 (SHAPE-01 / HARN-02):

- **La disposición campo por campo** de `Instrument` y `Segment` — qué campo se remueve, cuál se
  agrega, cuál se mantiene y cuál queda como alias. Este documento aporta la evidencia (§ 2 y § 4.1);
  la decisión es del criterio 1 de la Phase 43.
- **El alias aditivo de `Instrument.marketId`** siguiendo el precedente D-22 de `Symbol.marketId`
  — el ROADMAP ya lo direcciona como *alias aditivo, nunca rename*, pero disponerlo es de la Phase 43.
- **El tipado de las 5 claves `extra`** (`HealthFeed.symbols_never_delivered`,
  `FeedIngestor.last_error_age_seconds` / `.last_error_at` / `.subscription`, `Symbol.note`) —
  HARN-02, fuera del alcance de estos dos endpoints.
- **La disposición de semver** del cambio de forma. Es source-breaking sobre un paquete publicado
  desde v0.2.0; el release es la Phase 44, no ésta.
- **La limpieza del ledger de findings.** Esta corrida apendeó 40 bloques `### F-` (F-202 … F-245),
  de los cuales 12 son duplicados cosméticos de bloques ya existentes (10 `schema drift` sobre otros
  cinco endpoints + 2 `NO-DATA`). Ese churn es **ruido conocido y aceptado** (`42-RESEARCH.md`
  Assumptions Log A4 / `ROADMAP.md:53`: el harness de hoy es *"ruidoso pero no lossy"*), y el dedupe
  es la Phase 45 (HARN-01) precisamente para que las corridas en vivo ocurran sobre el harness
  conocido-lossless.

---

*Producido por: `42-04-PLAN.md` (Phase 42, criterio 5) — D-07 / D-08.*
*Corrida: 2026-08-31, exit code 0.*
*Consumido por: Phase 43 (SHAPE-01), criterios 1 y 2.*
