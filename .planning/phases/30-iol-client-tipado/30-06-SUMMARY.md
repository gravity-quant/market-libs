---
phase: 30-iol-client-tipado
plan: 06
subsystem: testing
tags: [verification-harness, schema-drift, iol-client, raw-wire, pytest, gap-closure]

# Dependency graph
requires:
  - phase: 30-iol-client-tipado
    provides: "modelos tipados de iol-client (Cotizacion/Instrumento/Titulo) + el driver main_iol.py migrado a acceso por atributo, cuya proyección de vuelta a dict es lo que CR-01 encontró estructuralmente ciego"
  - phase: 29-decoder-observable
    provides: "el walker por-campo que coerciona todo campo no-opcional a su tipo declarado y descarta claves no declaradas — la causa mecánica de la ceguera"
provides:
  - "main_iol.py::_capture_raw_wire — captura del body crudo de los 4 endpoints, una vez cada uno, vía los builders de _core"
  - "probe_field_type_map y probe_schema_snapshot como funciones puras de un raw_wire suministrado (sin I/O)"
  - "verification/test_main_iol_raw_wire_drift.py — lock offline de las tres clases de drift + canario de ceguera de la proyección"
  - "invariante corpus-support sobre _ASSUMED_QUOTE_FIELDS, enforceada offline"
  - "sanity de InstrumentType que discrimina forma, no cardinalidad"
affects: [33-live-strict-verification, 32-gate-superficie]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Captura separada del chequeo: el helper hace la I/O, los probes son funciones puras del payload capturado — lo que los vuelve testeables offline sin credenciales ni mocking de HTTP"
    - "Anti-vacuidad por siembra de fids: los fids de captura fallida siembran finding_fids, de modo que un probe cuyo insumo nunca llegó no puede reportar PASS"
    - "Ausencia vs None: un endpoint no capturado está ausente del dict, nunca presente con valor None — 'no capturado' y 'capturado como null' no se pueden confundir"

key-files:
  created:
    - verification/test_main_iol_raw_wire_drift.py
  modified:
    - main_iol.py

key-decisions:
  - "AD-30-06-01: restaurar la detección de drift por wire crudo, no por logging.Handler — los 4 baselines committeados son documentos schema_of(raw) y ningún stream de log records se reconstruye en uno"
  - "El cuerpo sintético de los tests se deriva del bloque schema del baseline committeado en vez de transcribirse: el test sigue al baseline en lugar de derivar de él"
  - "El Client de los tests se construye explícito (base_url/username/password) en vez de vía iol_client.configure(), para no filtrar estado global a otros tests de la sesión"
  - "Un tipo top-level inesperado en get_quote / get_historical_quotes es un finding SHAPE, no un skip silencioso — el guard viejo se saltaba el bucle entero y reportaba 'sin drift'"

patterns-established:
  - "Pitfall 2 generalizado: las HTTP calls duplicadas del harness se justifican cuando el wrapper silencia justamente el drift que el probe existe para atrapar; ahora son 4 endpoints, no 1"
  - "Regla forma-no-cardinalidad para los sanity checks de listas, citando _core.py::parse_get_instruments_response"

requirements-completed: [TYP-01]

# Metrics
duration: 100min
completed: 2026-08-20
status: complete
---

# Phase 30 Plan 06: Restauración de la detección de drift por wire crudo (CR-01)

**`probe_schema_snapshot` y `probe_field_type_map` vuelven a ser función de lo que la API devolvió, no de lo que los modelos declaran: las tres clases de drift que CR-01 probó invisibles (float→str, clave agregada, clave quitada) se detectan de nuevo en los 4 endpoints, y una captura fallida ya no puede reportarse como PASS.**

## Performance

- **Duration:** ~100 min (incluye dos corridas completas de `verification/`, ~14 min cada una)
- **Started:** 2026-08-20T20:30Z (aprox.)
- **Completed:** 2026-08-20T22:12Z
- **Tasks:** 3
- **Files modified:** 2 (1 creado, 1 modificado)

## Accomplishments

- `main_iol.py::_capture_raw_wire` captura el body crudo de los 4 endpoints usando los builders de `iol_client._core` (no paths hardcodeados), con un `try/except` por endpoint: un endpoint que falla emite un finding `ERROR-MAP` y no aborta los otros tres.
- `probe_field_type_map` y `probe_schema_snapshot` pasaron a ser funciones puras de un `raw_wire` suministrado; ninguno hace HTTP. Esa costura es lo que hace posible el lock de regresión offline.
- Las dos ramas `elif observed[key] != expected_type` (get_quote y get_historical_quotes[0]) — que CR-01 probó muertas — vuelven a ser alcanzables.
- WR-02 y WR-06 retirados: ninguna corrida viva puede emitir un finding de clave asumida imposible de cerrar, y un listado de instrumentos legítimamente vacío ya no es defecto de forma.
- Los 4 baselines committeados quedan byte-idénticos y ningún archivo bajo `packages/` fue tocado.

## Task Commits

1. **Task 1: RED — lock de regresión offline para la detección de drift por wire crudo** — `b5cd36e` (test)
2. **Task 2: GREEN — captura del wire crudo y recableado de los probes 12 y 13** — `f0db7b9` (fix)
3. **Task 3: Retiro de los dos findings garantizadamente falsos (WR-02, WR-06) + corrección del docstring de `_as_wire`** — `a5ab7d4` (fix)

## Files Created/Modified

- `verification/test_main_iol_raw_wire_drift.py` (nuevo, 337 líneas) — 7 funciones de test (9 casos con la parametrización), todas offline: sin red, sin credenciales, sin `httpx_mock`.
- `main_iol.py` — `_capture_raw_wire` nuevo; firmas de los probes 12 y 13 cambiadas; `main()` actualizado; `_ASSUMED_QUOTE_FIELDS` con una entrada menos; predicado de sanity de `probe_get_instruments_by_type_sync` corregido; docstrings de módulo y de `_as_wire` corregidos.

## RED literal de la Task 1 (antes de la Task 2)

Comando: `uv run pytest verification/test_main_iol_raw_wire_drift.py -q -p no:randomly --tb=line`

Resultado: **`8 failed, 1 passed in 0.03s`**

### Fallas por razón de *firma* (7 casos)

```
E   TypeError: probe_schema_snapshot() missing 3 required positional arguments: 'historical', 'instruments', and 'by_type_envelope'
    test_probe_schema_snapshot_passes_raw_wire_through_unmodified

E   TypeError: probe_schema_snapshot() missing 3 required positional arguments: 'historical', 'instruments', and 'by_type_envelope'
    test_probe_schema_snapshot_detects_type_drift_added_key_and_removed_key[type_drift_ultimoPrecio]

E   TypeError: probe_schema_snapshot() missing 3 required positional arguments: 'historical', 'instruments', and 'by_type_envelope'
    test_probe_schema_snapshot_detects_type_drift_added_key_and_removed_key[added_key_simbolo]

E   TypeError: probe_schema_snapshot() missing 3 required positional arguments: 'historical', 'instruments', and 'by_type_envelope'
    test_probe_schema_snapshot_detects_type_drift_added_key_and_removed_key[removed_key_montoOperado]

E   TypeError: probe_schema_snapshot() missing 3 required positional arguments: 'historical', 'instruments', and 'by_type_envelope'
    test_probe_schema_snapshot_passes_on_unmutated_body

E   TypeError: probe_field_type_map() missing 1 required positional argument: 'instruments_by_type_envelope'
    test_probe_field_type_map_detects_raw_type_drift

E   TypeError: probe_field_type_map() missing 1 required positional argument: 'instruments_by_type_envelope'
    test_probe_field_type_map_reports_finding_when_capture_failed
```

### Falla por razón de *comportamiento* (1 caso)

```
E   AssertionError: claves asumidas ausentes del baseline: ['simbolo']
    assert not ['simbolo']
    test_assumed_quote_fields_are_all_present_in_committed_baseline
```

Esta falla NO la cerró la Task 2 — la cerró la Task 3 (WR-02). Tras la Task 2 el archivo quedó en `1 failed, 8 passed`, con esta única falla remanente; tras la Task 3, `9 passed`.

### Test que pasó desde el principio, por diseño

`test_model_projection_is_blind_to_all_three_drift_classes` (el canario) pasó **antes** de la Task 2 y sigue pasando después. Es correcto y está dicho explícitamente en su docstring: el test asserta la **ceguera que hoy existe** en la proyección del modelo, no la corrección. No es un test que nunca fue rojo por descuido — es la falsificación del verificador vuelta permanente. Si algún día el decoder empieza a preservar claves no declaradas, este test falla ruidosamente y el fundamento de CR-01 debe revisarse; ése es el resultado correcto.

## Reproducción post-fix de la tabla CR-01

Columna pre-fix tomada de `30-REVIEW.md` § CR-01 (verificada dos veces: code review y verificación de fase). Columna post-fix ejecutada acá contra el baseline committeado real `get-quote.json` (20 claves, `ultimoPrecio: float`, `montoOperado: float`, sin clave `simbolo`).

| Mutación sobre el wire crudo de `get_quote` | Pre-fix (proyección del modelo) | Post-fix (wire crudo) | Evidencia |
|---|---|---|---|
| `ultimoPrecio` float→str | `False` — no detectada | **FINDING (SHAPE)** | `test_..._detects_type_drift_added_key_and_removed_key[type_drift_ultimoPrecio]` PASSED |
| clave `simbolo` agregada | `False` — no detectada | **FINDING (SHAPE)** | `test_..._detects_type_drift_added_key_and_removed_key[added_key_simbolo]` PASSED |
| clave `montoOperado` quitada | `False` — no detectada | **FINDING (SHAPE)** | `test_..._detects_type_drift_added_key_and_removed_key[removed_key_montoOperado]` PASSED |
| cuerpo **sin mutar** | PASS (vacuo) | **PASS (discriminante)** | `test_probe_schema_snapshot_passes_on_unmutated_body` PASSED — status PASS y cero findings |

3 de 3 detectadas donde antes eran 0 de 3, y el probe sigue discriminando en la dirección negativa (sin drift → PASS, no un FINDING inventado).

Complementos verificados en la misma corrida:

- `probe_field_type_map` sobre wire crudo con `ultimoPrecio` string → `FINDING`, con finding titulado `type drift on \`ultimoPrecio\` in get_quote` — la rama que la proyección volvía inalcanzable.
- `probe_field_type_map(client, {}, ["F-01"])` → `FINDING`, nunca `PASS`.
- El canario confirma que la columna pre-fix sigue siendo `False` en las tres: la proyección del modelo produce el mismo `schema_of` para el cuerpo limpio y para las tres mutaciones.

Corrida verbatim post-fix:

```
verification/test_main_iol_raw_wire_drift.py::test_probe_schema_snapshot_passes_raw_wire_through_unmodified PASSED
verification/test_main_iol_raw_wire_drift.py::test_probe_schema_snapshot_detects_type_drift_added_key_and_removed_key[type_drift_ultimoPrecio] PASSED
verification/test_main_iol_raw_wire_drift.py::test_probe_schema_snapshot_detects_type_drift_added_key_and_removed_key[added_key_simbolo] PASSED
verification/test_main_iol_raw_wire_drift.py::test_probe_schema_snapshot_detects_type_drift_added_key_and_removed_key[removed_key_montoOperado] PASSED
verification/test_main_iol_raw_wire_drift.py::test_probe_schema_snapshot_passes_on_unmutated_body PASSED
verification/test_main_iol_raw_wire_drift.py::test_probe_field_type_map_detects_raw_type_drift PASSED
verification/test_main_iol_raw_wire_drift.py::test_probe_field_type_map_reports_finding_when_capture_failed PASSED
verification/test_main_iol_raw_wire_drift.py::test_assumed_quote_fields_are_all_present_in_committed_baseline PASSED
verification/test_main_iol_raw_wire_drift.py::test_model_projection_is_blind_to_all_three_drift_classes PASSED

============================== 9 passed in 0.03s ===============================
```

## Decisión de enfoque AD-30-06-01 (restatement)

**Pregunta:** ¿restaurar la detección de drift vía wire crudo, o vía un `logging.Handler` que convierta los registros de divergencia de decodificación en findings SHAPE?

**Elegida:** wire crudo. **Reversibilidad:** two-way.

**Razón (por qué NO el handler de logging):** `30-REVIEW.md` CR-01 ofrece ambas y señala la de wire crudo como la correcta. Dos motivos la vuelven no meramente preferible sino necesaria.

1. **La ruta del handler es lossy donde importa.** CR-01 registra que una clave *removida* y un `null` sobre un campo no-opcional emergen ambos como `missing`, colapsando dos clases de drift que el snapshot mantiene distintas.
2. **Y, decisivo:** los cuatro baselines committeados son documentos `schema_of(raw_wire)`, congelados byte a byte desde 2026-06-06 y re-confirmados sin cambios por la verificación de esta fase. Ningún stream de log records se reconstruye en un documento `schema_of`, así que `_write_or_check_schema` no tendría contra qué comparar y `probe_schema_snapshot` **no podría restaurarse en absoluto** por esa vía. El handler agregaría una segunda señal, más débil, al lado de un probe que seguiría ciego. El wire crudo restaura el probe.

**Reversible** porque el cambio está confinado a un archivo de driver más un archivo de test nuevo: no se tocó código de paquete, ni un baseline committeado, ni una API publicada. Un futuro que prefiera el handler puede sumarlo como señal complementaria sin deshacer nada de esto.

## Estado de las prohibiciones (`must_haves.prohibitions`)

Las cuatro son descriptor-less: disponen flagged-unverified salvo que este SUMMARY aporte evidencia. Las cuatro **se sostienen**.

| Prohibición | Estado | Evidencia |
|---|---|---|
| Ningún probe reporta PASS precisamente cuando está roto: una captura fallida, una comparación no ejecutada o un payload ausente produce FINDING o SKIPPED explícito, jamás PASS | **SOSTENIDA** | `capture_fids` siembra `finding_fids` en el probe 12 (`finding_fids: list[str] = list(capture_fids)`), así que un fid de captura fallida fuerza FINDING antes de mirar nada. Un endpoint ausente del `raw_wire` va a `skipped` en el probe 13 (nunca a `matched`). El string de detalle del PASS del probe 12 reporta cuántos endpoints estaban efectivamente presentes en `raw_wire`, no un conteo fijo. Guard ejecutable: `test_probe_field_type_map_reports_finding_when_capture_failed` PASSED. Además, un tipo top-level inesperado en `get_quote`/`get_historical_quotes` ahora emite SHAPE en vez de saltear el bucle en silencio (era un modo de PASS-cuando-roto pre-existente en la misma familia). |
| Ningún body crudo llega a disco ni a un campo de finding: la salida de `schema_of` es lo único que se escribe a un snapshot o a findings | **SOSTENIDA** | `_write_or_check_schema` serializa `schema_of(raw_payload)`, nunca su entrada — el helper quedó **sin modificar** por este plan. En el probe 12 los argumentos de `append_finding` son `sorted(keys)` y nombres de tipo. El `except` de la captura registra `repr(exc)` y `type(exc).__name__`, nunca el body. Los tests asseran que el findings file committeado y los 4 baselines quedan sin tocar tras una corrida: `git diff --exit-code .planning/verification/iol-client-findings.md` y `.../schemas/iol-client/` salen 0 con el árbol limpio. |
| Ningún probe reporta un defecto de forma cuando la respuesta es legítima: una lista vacía y una clave asumida que el baseline no registra no son drift | **SOSTENIDA** | WR-06: verificación ad-hoc de las cuatro direcciones sobre `probe_get_instruments_by_type_sync` con un `Client` stubbeado — `[]` en los 6 types → `PASS`; los 6 poblados → `PASS`; un no-list → `FINDING (bad_types=['letras: shape=dict'])`; una lista no vacía cuyo elemento 0 no es `Titulo` → `FINDING (bad_types=['letras: shape=list[dict]'])`. WR-02: `simbolo` eliminada de `_ASSUMED_QUOTE_FIELDS`; `uv run python -c "...unsupported assumed keys..."` imprime `[]`; `test_assumed_quote_fields_are_all_present_in_committed_baseline` PASSED lo vuelve invariante permanente. |
| Ninguna corrida sobreescribe un baseline committeado ante drift (D-25): el drift produce finding, nunca un write | **SOSTENIDA** | `_write_or_check_schema` sin modificar: la rama de drift emite el finding y retorna sin escribir. Los tres casos de `test_..._detects_type_drift_added_key_and_removed_key` asseran `tmp_schema.read_bytes() == before` tras un resultado FINDING. Los 4 baselines committeados: `git diff --exit-code .planning/verification/schemas/iol-client/` → exit 0. |

## Assumptions flaggeadas

### `FA-EDGE-TYP-01` — **sigue unresolved** (no auto-resuelta)

El probe determinístico de edges no pudo clasificar TYP-01 en ninguna categoría y no devolvió ruta de verificación (`EDGE_ABSENT=1`, requisito `unclassified`). Este plan **no** reclama haber descargado una obligación de cobertura de edges para TYP-01. Reclama la cosa más angosta y verificable independientemente que sus tests asertan: las tres clases de drift se detectan por la ruta del probe, la proyección del modelo se prueba incapaz de detectarlas, y una captura fallida no puede reportar PASS. Se registra unresolved, no resuelta.

### `FA-30-06-02` — **reversión deliberada, ejecutada**

`30-04-SUMMARY.md` §(c) dejó un carry-forward a la Phase 33 sosteniendo que, para los endpoints modelados de iol, "la señal autoritativa de drift ya no es el diff del snapshot de schema: es el censo de divergencias", y lo encuadró como un trade aceptado y no como un defecto. El code review y la verificación lo rechazaron ambos como BLOCKER.

**Este plan revierte ese trade para los probes de snapshot y de field-map: el diff del schema vuelve a ser autoritativo porque vuelve a leer el wire crudo.** El censo de divergencias sigue siendo una señal real y complementaria — sigue atrapando la asimetría `int`/`float` que el snapshot no puede ver, por construcción de `schema_of` — pero ya **no es un sustituto**.

**La Phase 33 debe leer AMBOS:** el diff del snapshot (autoritativo sobre claves agregadas/quitadas y sobre type-drift del wire) **y** el censo de divergencias (autoritativo sobre coerciones que el walker aplicó silenciosamente y que el snapshot no puede distinguir). La assumption se flaggea en vez de sobreescribirse en silencio para que la reversión quede auditable contra el registro previo.

### `FA-30-06-03` — **preservada, no cerrada** (WR-08 explícitamente fuera de scope)

`Client._request` bindea un `DecodeScope` que ningún parser decorado retira cuando el llamador es un `_request` crudo. La captura de este plan realiza tres de esos calls más (cuatro en total, contra uno antes). WR-08 está documentado como inalcanzable en el ordenamiento actual del driver y **este plan preserva ese ordenamiento**: la captura corre inmediatamente antes de los probes 12 y 13, que no realizan ningún `from_api` suelto, y el siguiente `_request` (probe 14) re-bindea antes de cualquier decode. No se arregla acá. El comentario en fuente dentro de `_capture_raw_wire` deja escrito que un reordenamiento futuro del driver debe revisarlo antes de volverlo alcanzable.

## Deviations from Plan

### 1. [Rule 3 — Blocking] El worktree no tenía el workspace instalado

- **Found during:** Task 1 (primera corrida de baseline)
- **Issue:** `uv run pytest verification` fallaba en colección con `ModuleNotFoundError: No module named 'matriz_client'` — el `.venv` del worktree estaba sin sincronizar.
- **Fix:** `uv sync --all-packages --all-extras --dev --frozen`.
- **Files modified:** ninguno (solo el `.venv`, gitignorado).
- **Verification:** colección limpia posterior; 299 tests colectados en `verification/`.

### 2. [Rule 2 — Missing critical] Un tipo top-level inesperado ya no se saltea en silencio

- **Found during:** Task 2
- **Issue:** El plan pedía "guard both against absence and against an unexpected top-level type; an unexpected type is itself a SHAPE finding, not a silent skip". El código previo usaba `if isinstance(observed, dict):` sin `else`, de modo que un payload de forma inesperada saltaba el bucle entero y el probe reportaba "sin drift". Es exactamente la clase de PASS-cuando-roto que la primera prohibición proscribe.
- **Fix:** ramas explícitas que emiten `SHAPE` para: `get_quote` top-level no-dict, `get_historical_quotes` top-level no-list, y `get_historical_quotes[0]` no-dict. Una serie vacía sigue siendo cardinalidad y no se reporta.
- **Files modified:** `main_iol.py`
- **Committed in:** `f0db7b9`

### 3. [Rule 3 — Blocking] `Client` explícito en vez de `iol_client.configure()` en los tests

- **Found during:** Task 1
- **Issue:** El plan sugería copiar del test de matriz la línea `configure(base_url="https://api.test", ...)`. Eso muta el singleton por-módulo de `iol_client`, y el estado sobrevive a la corrida del archivo: filtraría `base_url` y credenciales dummy a cualquier test posterior de la misma sesión (`verification/test_iol_disk_persistence.py` entre ellos).
- **Fix:** el fixture construye `Client(base_url=..., username=..., password=...)` explícito, que cumple el mismo objetivo declarado ("que `Client` construya sin tocar `.env`") sin mutar estado global. Documentado en el docstring del fixture.
- **Files modified:** `verification/test_main_iol_raw_wire_drift.py`
- **Committed in:** `b5cd36e`

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 missing critical)
**Impact on plan:** Ninguna amplía el scope. La #2 es la prohibición N.º 1 del propio plan aplicada a un sitio que el texto de la Task 2 pedía cubrir; las #1 y #3 son de entorno y de higiene de test.

## Issues Encountered

- **`uv run pytest verification -q` no sale 0, ni antes ni después de este plan.** Baseline pre-cambio medido en este worktree: `19 failed, 271 passed, 19 errors in 827.50s`. Post-cambio: `19 failed, 280 passed, 19 errors in 828.65s`. El conjunto de fallas y errores es **idéntico** y enteramente ajeno a iol: 17 casos de `test_matriz_sweep_snapshot.py` (era phase-07, documentadas como pre-existentes en `PROJECT.md`) más 2 de `test_main_matriz_login_fail_uniformity.py`. El delta exacto es **+9 passed**, que son los 9 casos nuevos de este plan. Cero regresiones; el criterio "exits 0" del plan no era alcanzable desde el baseline y no es de este plan cerrarlo (toca `main_matriz.py`, fuera de scope).
- Cada corrida completa de `verification/` toma ~14 minutos, dominadas por las fallas de matriz. Los gates de este plan se corrieron scopeados y la suite completa se corrió dos veces (antes y después) para medir el delta.

## Verificación ejecutada

| # | Comando | Resultado |
|---|---|---|
| 1 | `uv run pytest verification/test_main_iol_raw_wire_drift.py -q` | **9 passed** |
| 2 | `uv run pytest verification -q` | 19 failed / 280 passed / 19 errors — idéntico al baseline salvo **+9 passed** |
| 3 | `uv run pytest packages/ -q` | **1567 passed, 1 deselected** |
| 4 | `uv run ruff check main_iol.py verification` + `ruff format --check` | ambos exit 0 |
| 5 | `git diff --exit-code .planning/verification/schemas/iol-client/` | exit 0 — los 4 baselines byte-idénticos |
| 6 | `git diff --exit-code packages/` | exit 0 — ningún fuente de paquete tocado |
| 7 | `uv run python -c "import main_iol"` | importa limpio tras el cambio de imports |
| 8 | `uv run python -c "...unsupported assumed keys..."` | `[]` |
| 9 | `git diff --exit-code .planning/verification/iol-client-findings.md` | exit 0 — los tests redirigen findings a `tmp_path` |

Guards pre-existentes re-corridos y verdes: `test_main_iol_uses_single_client_instance.py` (la captura toma el `client` threadeado y no construye ninguna instancia nueva), `test_main_drivers_bare_except.py`, `test_public_surface.py`, `test_iol_disk_persistence.py`.

## Nota de gate (CI vs local)

`verification/` está en `testpaths` del `pyproject.toml` raíz, así que `uv run pytest verification -q` colecta el archivo nuevo localmente, pero el job `test` del CI corre **por paquete** y no lo colecta. Es una propiedad pre-existente de todos los `verification/test_main_*.py` y no era de este plan cambiarla; queda dicha en el docstring del módulo para que un lector sepa que el gate es local / suite completa, no CI.

## Next Phase Readiness

- **Phase 33 (LIVE-TYP-01)** recupera la señal de la que dependía: el diff del snapshot vuelve a ser autoritativo. Debe leer **ambas** señales (diff del snapshot + censo de divergencias) por `FA-30-06-02`.
- El re-verificador puede reproducir la falsificación de CR-01 corriendo `uv run pytest verification/test_main_iol_raw_wire_drift.py -v`: las tres mutaciones contra el `get-quote.json` committeado, ahora las tres detectadas por la ruta del probe donde antes eran cero.
- **Costo en vivo introducido:** 3 GET autenticados adicionales por corrida sobre un token ya cacheado (T-30-06-04, disposición `accept`). La corrida ya emite ~15, seis de ellos en el loop de sanity de by-type.
- **Abierto y flaggeado:** WR-08 (`DecodeScope` no retirado en `_request` crudo) sigue inalcanzable pero con más call sites; cualquier reordenamiento del driver debe revisarlo. WR-01, WR-03, WR-04, WR-05 y WR-07 (más allá de su documentación) siguen registrados y fuera de scope de este cierre.

## Known Stubs

Ninguno. No hay valores hardcodeados, placeholders ni componentes sin fuente de datos introducidos por este plan.

## User Setup Required

Ninguno — no se requiere configuración de servicios externos. Todos los tests de este plan corren sin credenciales y sin red.

---
*Phase: 30-iol-client-tipado*
*Completed: 2026-08-20*
