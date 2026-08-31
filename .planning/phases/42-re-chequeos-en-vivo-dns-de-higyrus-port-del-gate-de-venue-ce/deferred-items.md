# Deferred Items — Phase 42

Hallazgos fuera del alcance de los planes de esta fase. Se registran acá en vez de
arreglarse, por la regla de límite de alcance: sólo se auto-corrige lo que las tasks
de esta fase causaron.

---

## D42-DEF-01 — Exposición pre-existente del base URL del vendor en `higyrus-client-findings.md`

- **Descubierto en:** plan 42-03, Task 1 (chequeo de no-fuga de la sesión)
- **Archivo:** `.planning/verification/higyrus-client-findings.md`, **línea 5** del header
- **Forma de la línea (valor elidido):** `- Resolved base URL / env: <BASE_URL_ELIDIDA>`
- **Clase:** exposición de dato de entrada del tipo que **T-39-04 / C-4** prohíbe

### Por qué NO se corrigió en esta fase

1. **Es pre-existente, no causado por esta sesión.** `git status --porcelain` sobre el
   archivo es vacío: es byte-idéntico a HEAD. El último commit que lo tocó es `fbb69c3`
   (Phase 17, `test(17-02)`), y el header viene de `e8307a6` (Phase 11, migración
   HARN-07). La corrida de esta fase **no lo modificó** — el corte temprano de
   vendor-unreachable de `main_higyrus.py:2908` sale antes de cualquier `append_finding`.
2. **Es un ledger versionado y append-only por diseño** (HARN-07). Reescribir su header
   a mano sería exactamente la clase de manipulación de evidencia que
   `verification/test_finding_count_consistency.py` y el precedente T-39-12 existen para
   impedir, y arriesga el triage de operador de los 2 findings que el archivo lleva.
3. **La política T-39-04 se escribió en la Phase 39**, después de que este header se
   generara. El archivo es evidencia de la era anterior a la política, no una violación
   nueva de ella.

### Alcance del chequeo de no-fuga que SÍ pasó

Los artefactos **de esta sesión** están limpios (`LEAK-CHECK ... CLEAN`):
`/tmp/42-higyrus-probe.log`, `/tmp/42-higyrus-run.log`,
`.planning/verification/run-evidence/higyrus-client.json`, y el `42-03-SUMMARY.md`.

### Destino sugerido

**Phase 45 (HARN-01 / HARN-03 / HARN-04)** — es la fase que ya tiene mandato para tocar
el harness de findings y que debe decidir por escrito qué se repara y qué se acepta como
deuda. La decisión pendiente es de tres vías, y ninguna es automática:

- **(a) Redactar el header** de los 4 ledgers de `verification/` con un `<REDACTED>`, y
  cambiar `verification/findings.py` para que nunca vuelva a escribir un base URL
  resuelto. Requiere reescribir historia committeada de evidencia → necesita decisión
  humana explícita.
- **(b) Aceptar la deuda formalmente** con su razón escrita: el `.planning/` de este repo
  no es público y el hostname ya vive en `packages/higyrus-client/.env` local.
- **(c) Cambiar sólo `findings.py` hacia adelante** y dejar los headers históricos como
  están, documentando la fecha de corte de la política.

**No decidir esto en la Phase 42** es deliberado: la 42 mide alcanzabilidad en vivo, y
mezclar una redacción de evidencia histórica con una corrida en vivo confunde qué
artefacto respalda qué afirmación.

---

## D42-DEF-02 — El SHAPE-diff del driver está INERTE para `Instrument` y `Segment`

- **Descubierto en:** plan 42-04, Task 2 (corrida en vivo) al reconciliar de dónde salían
  los 28 findings de divergencia campo por campo
- **Archivo:** `main_market_data.py`, líneas `1001` / `1041` (sync) y `1381` / `1407` (async)
- **Clase:** guard silenciosamente inerte — no emite falso positivo, emite **nada**

### El hecho medido

Los cuatro probes de `/instruments` y `/instruments/segments` derivan su muestra con:

```python
sample = raw[0] if isinstance(raw, list) and raw else None
if isinstance(sample, dict):
    _emit_shape(sample, Instrument, "Instrument", "sync", base_url)
```

El wire de estos dos endpoints devuelve un **sobre paginado** (`dict` con `items` /
`segments` adentro), no un array desnudo — verificado en vivo el 2026-08-31 y
transcrito en `42-WIRE-READ.md § 2`. Por lo tanto `isinstance(raw, list)` es `False`,
`sample` queda en `None`, y `_emit_shape` **nunca corre** para estos dos modelos.

Corroboración en el ledger: existen findings con el formato de `_emit_shape`
(`"wire-only field … en MarketDataSnapshot"`, `"… en Symbol"`, `"… en CalendarConfig"`
— modelos cuyo `raw` sí es lista o dict-de-fila) y **cero** con ese formato para
`Instrument` o `Segment`.

### Por qué NO se corrigió en esta fase

1. **Es pre-existente.** No lo causó ninguna task de este plan: la Task 1 sólo agregó dos
   llamadas a `capture()` y no tocó ni `sample`, ni `_emit_shape`, ni
   `_write_schema_snapshot`. La condición viene de que el plan 33-07 arregló el
   desenvolvimiento del sobre en el cliente, pero el driver siguió muestreando como si el
   wire fuera un array.
2. **No hay pérdida de evidencia.** El censo de divergencias del decode
   (`verification/divergences.py:176`) produjo la disposición campo por campo completa
   —28 findings, F-205…F-218 y F-229…F-242— que es exactamente lo que la Phase 43
   consume. Arreglarlo hoy no agregaría información, sólo duplicaría la que ya está.
3. **Arreglarlo exige otra corrida en vivo.** El criterio 5 pide **una** lectura fresca
   del wire; re-correr el driver para regenerar el mismo dato con otro emisor gasta
   tráfico contra un servicio de terceros sin producir un hecho nuevo.

### Destino sugerido

**Phase 43 (SHAPE-01, criterio 2)** — la fase que tiene que demostrar *"el antes/después
se demuestra con la medición, no se afirma"* para `get_segments()`. El riesgo concreto y
accionable: si la Phase 43 usa `_emit_shape` como la medición del después, va a ver **cero
findings** para `Instrument`/`Segment` tanto si arregló el modelo como si no —
un **falso verde**. Dos caminos, ambos legítimos:

- **(a)** Arreglar el muestreo del driver para que descienda al sobre
  (`raw["items"]` / `raw["segments"]`) antes de tomar `raw[0]`, y recién entonces usar
  `_emit_shape` como evidencia del antes/después.
- **(b)** Usar el censo de divergencias del decode como la medición del antes/después
  (es el que ya funciona), y dejar el muestreo del driver como está, documentando que
  para estos dos endpoints el SHAPE-diff es redundante por diseño.

Elegir (b) sin escribir la razón deja el guard inerte y sin marca, que es la forma en que
esto se volvió invisible la primera vez.
