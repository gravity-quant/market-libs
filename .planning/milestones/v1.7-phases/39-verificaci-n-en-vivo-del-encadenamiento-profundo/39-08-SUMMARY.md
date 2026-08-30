---
phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo
plan: 08
subsystem: verification
tags: [census, null-object, retired-triples, matriz-client, higyrus-client, iol-client, ambito-financiero-client, live-verification]

# Dependency graph
requires:
  - phase: 39-07
    provides: "los cuatro sobres de evidencia de corrida, los cuatro ledgers dispositionados y la ventana horaria registrada — la población del censo"
  - phase: 35
    provides: "35-RETIRED-TRIPLES.md — el término medio de colapso de política que la resta necesita"
  - phase: 38
    provides: "38-CENSUS.md — el formato de censo validado que este artefacto reusa"
provides:
  - "39-CENSUS.md: el contraste de la corrida contra el censo de la Fase 33 y contra el piso ratificado de 29-SIZING, con el split política-vs-corrección exigido por SC-4"
  - "La resta de matriz cerrada exacta en las DOS columnas de unidad: 14 − 5 − 2 = 7 (triples distintos) y 24 − 6 − 4 = 14 (registros)"
  - "El addendum de la Fase 39 al ledger de triples retiradas, que cierra por nombre la cuenta que la Fase 38 dejó pendiente"
  - "La deuda de retiro de las Fases 36 y 37 registrada como UNMEASURED con destino nombrado NOBJ-RETIRE-3637 en vez de plegada dentro de 'corregido'"
affects: [40-publicacion, cierre-de-milestone-v1.7]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reconciliación por dos costuras independientes (sobre de evidencia vs parseo de títulos SHAPE) antes de reportar un total: el acuerdo de las dos ES evidencia de que el censo está sano, y su desacuerdo se explica en vez de resolverse eligiendo una"
    - "Toda resta nombra la columna de unidad en cada término; el error de columna se descarta ANTES de hipotetizar un hallazgo real"

key-files:
  created:
    - .planning/phases/39-verificaci-n-en-vivo-del-encadenamiento-profundo/39-CENSUS.md
  modified:
    - .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md

key-decisions:
  - "El delta 9-vs-7 entre las dos costuras NO se resuelve eligiendo una: son los dos triples que el fix in-cycle F-43/F-44 cerró entre la emisión pre-fix y la captura post-fix del sobre. El delta ES el fix"
  - "El factor de duplicación por superficie del ledger de matriz es 1× y no el ~2× que la Fase 33 documentó — declarado como asimetría medida con causa NO determinada y destino HARN-VERIF-01, en vez de inventarle una causa"
  - "iol F-01 NO se re-emitió, contra lo que el plan anticipaba; se escribe la medición y no la predicción, con las dos razones independientes que la explican"
  - "F-01 de iol queda FUERA de las tres columnas del split por construcción (es hand-written, no pertenece a la población del walker) y su exclusión se declara explícitamente en vez de quedar silenciosa"
  - "NOBJ-RETIRE-3637 se crea como etiqueta de bookkeeping para la deuda de retiro de 36/37, siguiendo la convención LIVE-<PKG>-<NN> ya vigente — no es una decisión nueva de alcance"

patterns-established:
  - "Todo cero se declara por enumeración con su causa nombrada; un SKIPPED se escribe UNMEASURED y nunca cero"
  - "El addendum a un ledger sólo agrega: si un número previo resultara incorrecto se corrige EN el addendum, nunca editando el original"

requirements-completed: [LIVE-NOBJ-01]

# Metrics
duration: 22m
completed: 2026-08-30
status: complete
---

# Phase 39 Plan 08: censo en vivo y cierre del ledger de triples retiradas Summary

**La resta de matriz cerró exacta en las dos columnas de unidad —14 − 5 (colapso de política) − 2 (corrección real) = 7 triples distintos medidos, y 24 − 6 − 4 = 14 registros— así que ninguna de las 14 divergencias del piso ratificado quedó sin columna, y la baja de números no puede leerse como un falso limpio.**

## Performance

- **Duration:** ~22 min
- **Completed:** 2026-08-30
- **Tasks:** 3 (3 auto, 0 checkpoints)
- **Files modified:** 2 (1 creado, 1 ampliado append-only)

## Accomplishments

- **El split que SC-4 exige quedó completo y verificable.** Las 14 triples del piso de matriz, las 22 del piso de higyrus y los ceros de iol/ámbito/wallets están cada una en exactamente una columna: colapso de política, corrección real, o sigue-abierto. Ninguna quedó fuera.
- **La aritmética cierra sin residuo en las dos columnas de unidad**, usando el término medio del ledger de la Phase 35 como único insumo y sin re-derivarlo.
- **Las dos costuras se reconciliaron y su única discrepancia quedó explicada por causa**, no resuelta eligiendo una.
- **El ledger de triples retiradas quedó sin deuda abierta hacia la Fase 40**: la cuenta de la Fase 38 se cerró por nombre, y la única deuda que queda (36/37) está registrada con destino nombrado.
- **matriz recibió su primer censo en vivo del proyecto**, con el caveat de venue declarado en vez de aplicado en silencio.

## Task 1 — población por las dos costuras y reconciliación aritmética

Sin artefacto propio por diseño (el plan declara `files: (ninguno todavía)`); el borrador vive dentro de `39-CENSUS.md`, que la Task 2 committeó.

**Costura 1 — sobres de evidencia (`handler.seen`).** Comando y salida verbatim:

```
$ uv run --frozen python -c "... json.loads(p.read_text())['n_triples'] ... ['probes_executed'] ..."
ambito-financiero-client.json 0 7
higyrus-client.json 0 0
iol-client.json 0 15
matriz-client.json 7 50
$ echo $?
0
```

**Costura 2 — parseo de títulos `SHAPE` deduplicado por `(model, field_path, kind)`:** ámbito 0, higyrus 0, iol 0, matriz **9**.

**La única discrepancia, con su causa:** matriz 9 vs 7. Los dos de más son `(Instrument, .marketId, extra)` y `(Instrument, .symbol, extra)` — `F-43`/`F-44`, ambos `FIXED`. Se emitieron en el pase **pre-fix** de la misma corrida autoritativa; el sobre se escribió **post-fix** (`captured_at 02:49:48`). El ledger es append-only y conserva la emisión; el sobre es una foto puntual. **Ninguna costura está mal: el delta ES el fix in-cycle.**

**El error de columna de unidad se descartó primero, como manda el ledger, y no había ninguno.** El término medio de matriz está expresado en las dos columnas a la vez (6 registros / 5 triples distintos) y se leyó la correcta en cada término. Las cinco filas cuya etiqueta en el piso es el `non_dict` pre-WR-02 se emparejaron sobre `(slug, field_path)` con el `kind` leído del ledger de la Phase 35 y no de `29-SIZING.md`.

**Los dos términos no derivables, marcados `UNMEASURED` con destino nombrado:**

1. **No existe artefacto de retiro de las Fases 36 y 37** (verificado por listado de directorio). Lo derivable se derivó de los rosters de `36-CONTEXT.md` y `37-CONTEXT.md`; lo que no, quedó `UNMEASURED` con destino **`NOBJ-RETIRE-3637`**. Nunca plegado dentro de "corregido".
2. **matriz no tiene censo de la Fase 33** — quedó `SKIPPED` por el bloqueo de política, así que su resta contra la Fase 33 no es computable y nunca lo será. `UNMEASURED`, con el piso ratificado como único contraste y el caveat de venue declarado.

## Task 2 — `39-CENSUS.md`

429 líneas (mínimo exigido: 120). Verificación automatizada, salida verbatim:

```
$ wc -l …/39-CENSUS.md                       429
$ grep -c "UNMEASURED" …/39-CENSUS.md         10
$ grep -c "LIVE-HIGY-33\|LIVE-MATZ-33" …      7
$ grep -c "field_path" …/39-CENSUS.md          4
```

Secciones obligatorias, todas presentes: unidad y método con las dos unidades rechazadas nombradas; alcance y fuera-de-alcance con destino por cada excluido; clasificación por paquete con la línea `SUMMARY` verbatim y el conteo de probes como evidencia positiva de corrida; contraste contra la Fase 33 y contra el piso con la columna nombrada en cada término; el split de D-11; la ausencia medida de ámbito con comando y salida; la tabla de casos límite de D-12 con la ventana horaria; limitaciones de cobertura; arrastre explícito de iol `F-01`; ceros por enumeración.

**El split, en números:**

| Paquete | Colapso de política | Corrección real | Sigue abierto | Total |
|---|---:|---:|---:|---:|
| `matriz-client` (triples distintos) | 5 | 2 | 7 | **14** |
| `matriz-client` (registros) | 6 | 4 | 14 | **24** |
| `higyrus-client` | 2 | 0 | 20 (`UNMEASURED`, `LIVE-HIGY-33`) | **22** |
| `iol-client` | 0 | 0 | 0 | **0** |
| `ambito-financiero-client` / `wallets-client` | 0 por enumeración | 0 | 0 | **0** |

**Casos límite de D-12.** Ventana declarada: sábado 2026-08-29 23:34 ART, **mercado cerrado**. El discriminador usado fue la guarda de antigüedad existente (D-MATZ-5), no una inferencia: las siete entradas llegaron en `null`, así que `LA` no es dict y la rama de `LA.date` no se ejecutó. Ningún endpoint devolvió 204 en vivo en ningún paquete: esa mitad es íntegramente la suite mockeada del plan 39-02.

## Task 3 — addendum de la Fase 39 al ledger de triples retiradas

149 líneas agregadas, **0 borradas** (`git diff --numstat` → `149  0`). El addendum no reescribe historia.

- **La cuenta pendiente de la Fase 38 queda cerrada por nombre:** `## Phase 38 addendum` §3, *"Phase 39's middle term is unchanged"*. Esa sección afirmó sin poder testearlo que el término medio (higyrus 2, iol 0, market-data 0, matriz 5 distinct / 6 records) seguía intacto. Phase 39 corrió la resta con exactamente esos valores y cerró sin residuo: **la afirmación se sostuvo.**
- **Resultado por paquete:** matriz 5/6 confirmadas ausentes en vivo, **0 reaparecidas**; higyrus no testeable (`SKIPPED`, DNS); iol invariancia confirmada en vivo con 15 probes.
- **Primer censo en vivo de matriz declarado con su caveat de venue:** el piso se midió contra un corpus remarkets 2026-06-10, la corrida usó bbsa. Declarado, no aplicado en silencio.
- **El hallazgo del addendum:** la predicción de este ledger sobre `Instrument.instrumentId` se confirmó exactamente — y el silencio que predijo estaba tapando un defecto real de pérdida total de datos (9160 instrumentos sin símbolo). El retiro no es el defecto y el defecto no es una falla del retiro; lo que el episodio demuestra es que una triple retirada compra silencio, y el silencio sólo es seguro mientras algo más esté mirando.
- **La deuda de 36/37 queda registrada, no arrastrada en silencio**, con destino `NOBJ-RETIRE-3637`.

## Files Created/Modified

- `.planning/phases/39-…/39-CENSUS.md` — creado; el censo con el split política-vs-corrección, la reconciliación por dos costuras y los ceros por enumeración
- `.planning/phases/35-…/35-RETIRED-TRIPLES.md` — ampliado append-only con `## Phase 39 addendum` (6 sub-secciones)

## Task Commits

1. **Task 1** — sin commit por diseño: el plan declara `files: (ninguno todavía)` y el borrador vive en el artefacto de la Task 2
2. **Task 2: `39-CENSUS.md`** — `89dabec` (docs)
3. **Task 3: addendum al ledger** — `dc4e5cb` (docs)

## Decisions Made

Ver `key-decisions` en el frontmatter. La decisión de fondo: **cuando las dos costuras no coincidieron, no se eligió una.** Se identificó el par exacto que las separa, se ubicó su causa en el eje temporal de la corrida (pre-fix vs post-fix) y se contabilizó en la columna que le corresponde. Lo mismo con el factor de duplicación 1× vs ~2×: se declara la asimetría medida y se dice que la causa **no** se determinó, en vez de fabricarle una explicación plausible.

## Deviations from Plan

### Correcciones de premisa del plan, escritas como medición

**1. [Rule 1 — Bug de premisa] El plan afirmaba que iol `F-01` "se re-emitió en esta corrida"**
- **Found during:** Task 2, al redactar la sección de arrastre explícito
- **Issue:** La medición lo falsifica: iol corrió con `FINDING=0 DIVERGENCES=0` y la zona AUTO-GENERATED del ledger quedó byte-idéntica. `F-01` **no** se re-emitió.
- **Fix:** Se escribió la medición, no la predicción, con las dos razones independientes que la explican: (a) `F-01` es un finding escrito a mano en la Phase 3 y no pertenece a la población de ninguna costura; (b) la divergencia subyacente está materialmente resuelta desde la Phase 30. Se declara además que su no-re-emisión **no** es un fix y su permanencia **no** es una regresión, y que el operador no firmó la promoción a terminal.
- **Files modified:** `39-CENSUS.md`
- **Commit:** `89dabec`

**2. [Rule 2 — Funcionalidad crítica faltante] El factor de duplicación ~2× no se materializó y el plan no preveía esa comprobación**
- **Found during:** Task 1, al construir la costura 2
- **Issue:** El ledger de matriz tiene 9 bloques `SHAPE` de título mecánico para 9 triples, los 9 con `[async]` y ninguno con `[sync]` (confirmado también contra el historial en `3280cd2`, `19f8265` y `eeefe73`). Un lector futuro que aplique la conversión ~2× de `33-CENSUS.md` a este ledger obtendría un número equivocado.
- **Fix:** Declarado como asimetría medida en `## Unidad y método` y en `## Limitaciones de cobertura`, con causa **no determinada en esta fase** y destino nombrado `HARN-VERIF-01`. No afecta la aritmética, porque la unidad del censo es `handler.seen`, que no lleva superficie.
- **Files modified:** `39-CENSUS.md`
- **Commit:** `89dabec`

---

**Total deviations:** 2, ambas de premisa del plan corregidas por medición. Ninguna arquitectónica; ninguna requirió Rule 4. Cero dependencias nuevas (T-39-SC respetado): el trabajo es markdown más lecturas de artefactos existentes.

## Issues Encountered

- **La causa de la asimetría de superficie del ledger de matriz no se determinó.** Se descartó por historial que hubiera existido alguna vez un título mecánico `[sync]`. Se prefirió declararla `no determinada` con destino nombrado antes que cerrarla con una hipótesis. No bloquea nada: la unidad del censo es insensible a la superficie.

## Known Stubs

Ninguno. Los únicos términos sin valor numérico son los cuatro `UNMEASURED` declarados —el retiro de la Fase 36, el estado previo del retiro de la Fase 37, la resta de matriz contra la Fase 33, y el censo en vivo de higyrus— y los cuatro llevan destino nombrado (`NOBJ-RETIRE-3637`, `LIVE-MATZ-33`, `LIVE-HIGY-33`).

## Threat Flags

Ninguna superficie de seguridad nueva. No se tocó una sola línea de código de paquete: los dos archivos modificados son artefactos de planificación en markdown. `T-39-31` respetado — el censo transcribe 4-tuplas (metadata de tipo y de path), líneas `SUMMARY` ya redactadas por `safe_print` y comandos con su salida; ningún valor de wire, ninguna credencial, ningún identificador de cuenta, ninguna base URL con credenciales embebidas. `T-39-34` respetado — el addendum al ledger muestra 0 líneas borradas.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Listo para la Fase 40 (publicación).** El censo y el ledger están en disco y no queda deuda abierta sin nombre: la cuenta de la Fase 38 está cerrada, y la de las Fases 36/37 está registrada con destino `NOBJ-RETIRE-3637` a saldar en el cierre del milestone v1.7.
- **Destinos nombrados vivos que la Fase 40 heredará:** `LIVE-HIGY-33` (DNS), `LIVE-POS-39` (roster de la hoja `InstrumentPositionReport`), `LIVE-NOBJ-01` (iol `F-01` arrastrado), `HARN-VERIF-01` (deuda de harness, D39-03/D39-04 y la asimetría de superficie), `NOBJ-RETIRE-3637`.
- **`LIVE-MATZ-33` queda cerrado para corridas futuras** por la ampliación D-02 del allowlist a bbsa, pero la resta histórica contra la Fase 33 sigue siendo permanentemente no derivable y así está declarada.

## Self-Check: PASSED

- `.planning/phases/39-…/39-CENSUS.md` — FOUND (429 líneas; `UNMEASURED` ×10, `field_path` ×4, `LIVE-*-33` ×7)
- `.planning/phases/35-…/35-RETIRED-TRIPLES.md` — FOUND (`git diff --numstat` → `149  0`: 0 líneas borradas)
- Commits `89dabec`, `dc4e5cb` — FOUND
- Verificación automatizada de la Task 1 — exit 0, una línea por slug con triples y probes

---
*Phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo*
*Completed: 2026-08-30*
