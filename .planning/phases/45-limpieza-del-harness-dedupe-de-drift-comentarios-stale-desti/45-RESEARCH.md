# Phase 45: Limpieza del harness — dedupe de drift, comentarios stale, destino de `verification/` de matriz - Research

**Researched:** 2026-09-01
**Domain:** Harness de verificación interno (drivers `main_*.py` de la raíz, `verification/`, gates de CI) — Python 3.12, pytest, AST-based locks. Sin superficie de paquete nueva.
**Confidence:** HIGH (todo lo que sigue está medido contra HEAD con comandos reproducibles; cero afirmaciones de training data sobre este repo)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**HARN-01 — mecanismo de dedupe de schema drift**

- **D-01:** El dedupe se implementa como **dedupe intra-run únicamente** (reset por corrida), no como título content-addressed cross-run. Justificación: el problema MEDIDO (22 bloques para 8 snapshots, `HARN-DRIFT-33`) proviene de un run de dos pases, no de runs separados en el tiempo — el dedupe intra-run lo resuelve por completo. Es además la opción de menor riesgo: un título content-addressed (digest del diff embebido en el título) es más código nuevo y es exactamente la superficie donde `PITFALLS.md` Pitfall 9 advierte que un bug de implementación volvería a tragarse una divergencia real — el mismo modo de falla que este proyecto existe para eliminar. Si una MISMA divergencia sin arreglar persiste día tras día en corridas separadas, seguirá escribiendo un bloque nuevo por corrida — eso es status quo (verboso, no lossy), no una regresión.
  - **Si esto es incorrecto:** si el operador prefería colapso cross-run permanente, el mecanismo cambia a título content-addressed y el test de falsificación tiene que probar además que un digest distinto sobre el mismo endpoint escribe un bloque nuevo.

- **D-02:** Alcance de sitios a corregir — **los 5 sitios "schema drift" MÁS los 2 sitios hermanos "type drift" de `main_iol.py`** (7 sitios en total, 5 drivers):
  - `main_market_data.py:511` — `f"schema drift en {client_function}"`
  - `main_iol.py:1754` — `f"Schema drift en {func_name}"`
  - `main_higyrus.py:590` — `f"Schema drift en {func_name}"`
  - `main_matriz.py:584` — `f"Schema drift en {func_name}"`
  - `main_ambito_financiero.py:608` — `"Schema drift en get_dollar_banco_nacion"`
  - `main_iol.py:1617` — `f"type drift on \`{key}\` in get_quote"`
  - `main_iol.py:1685` — `f"type drift on \`{key}\` in get_historical_quotes[0]"`
  - Justificación: los 2 sitios hermanos comparten EXACTAMENTE el mismo hazard (título endpoint/key-scoped y libre de contenido) que los 5 sitios nombrados en el backlog (`HARN-DRIFT-33`); dejarlos sin tocar deja un hazard idéntico sin corregir a dos líneas de distancia del fix, en una fase cuyo tema es precisamente cerrar esta clase de rot.

- **D-03:** Reordenar la asignación de fid en los 7 sitios: `_next_fid()` se llama **después** de la decisión de dedupe, nunca antes — nunca relajar `verification/test_finding_count_consistency.py` (P-3). Si P-3 se pone rojo durante la implementación, es el test haciendo su trabajo.

- **D-04:** Test de falsificación obligatorio (uno o varios, cubriendo los 7 sitios o al menos representativo por driver): (a) la MISMA divergencia repetida dentro de una corrida → colapsa a 1 bloque; (b) una divergencia DISTINTA sobre el MISMO endpoint dentro de la misma corrida → sigue escribiendo un bloque nuevo. Sin (b), el test no prueba dedupe — prueba supresión.

**HARN-03 — comentario stale + IN-06 + retiro de IN-05**

- **D-05:** Corregir `tools/check_surface_types.py:47` y `:58` — `330` → `336` definitions scanned (valor medido, verificar con el propio gate antes de escribir el número).
- **D-06:** Cerrar `IN-06` agregando `verification/test_public_surface.py` al allowlist explícito del job `lint` de `.github/workflows/ci.yml` (líneas 81-92 hoy). Verificar que el archivo pasa solo, antes de agregarlo.
- **D-07:** Retirar `IN-05` del backlog de `ROADMAP.md` — verificado en HEAD que `matriz_client/__init__.py:186` ya tiene `__version__ = "0.3.0"` (resuelto en Phase 40); es un retiro de texto, no un fix de código.

**HARN-04 — destino de `verification/` de matriz**

- **D-08 [decisión, no auto-aprobada — Recomendación aceptada, "Yes, proceed"]:** **Aceptar como deuda formalmente documentada**, no reparar, los dos archivos rotos: `verification/test_matriz_sweep_snapshot.py` (17 FAILED + 17 ERROR) y `verification/test_main_matriz_login_fail_uniformity.py` (2 FAILED + 2 ERROR) — causa raíz única: llaman a los probes de `main_matriz.py` sin el argumento `client`, firma pre-migración REFAC-05 (Phase 15).
  - Justificación: reparar significa re-derivar expectativas mockeadas para comportamiento ya verificado EN VIVO contra el vendor real a lo largo de 4 milestones (Phases 33/35/37/39) — evidencia más débil reemplazando evidencia más fuerte, a escala de 4 milestones de alcance. Ningún hallazgo de esta sesión ni de la investigación de fase identificó una aserción única que estos 2 archivos cubran y que no esté hoy cubierta por un test enrolado en CI.
  - **La decisión escrita tiene que nombrar explícitamente, por archivo:** (1) qué afirmaría cada archivo que un test hoy enrolado en CI no afirma — respuesta esperada: "nada adicional medido"; (2) el rol de canario de ambos archivos para el refactor de `probe_context` (planes 33-02/33-03) — declarar el rol **transferido** (a qué test/gate) o **abandonado explícitamente**, nunca dejarlo implícito; (3) qué pasa con los **3 tests que hoy pasan** dentro de esos 2 archivos — no se puede hacer `git rm` sin dar cuenta de ellos (moverlos a un archivo vivo, o justificar por qué se pierden).
  - El allowlist de CI se mantiene explícito de todas formas — no se enrola `verification/` en bloque como efecto colateral de esta decisión.
  - **Si esto es incorrecto:** si el operador prefiere reparar, la fase necesita un presupuesto declarado por adelantado (research estima "38 firmas de argumento", no trivial) y se convierte en su propia sub-fase con el mismo cuidado de mirror sync/async que cualquier fix de harness — nunca una re-escritura apurada de mocks contra comportamiento ya verificado en vivo.

**Alcance — `DRV-MD-SEG-43` (fold-in explícito)**

- **D-09 [confirmado por recomendación aceptada]:** Se **foldea** `DRV-MD-SEG-43` en esta fase: `main_market_data.py:1541-1542` dereferencia `Segment.marketSegmentId`, campo que la Phase 43 removió (`Segment` hoy declara `segment`/`live_instruments`, D-06 de `43-DISPOSITION.md`). Fix de 2 líneas, sin lógica, sin obligación de espejo sync/async por ser un dereference directo en un driver (no en `client.py`/`aio.py`).

**Alcance — los 40 locks inertes de `verification/`**

- **D-10 [confirmado por recomendación aceptada]:** Esta fase **NO** dispone individualmente los 40 archivos `verification/test_*.py` que Phase 41 declaró formalmente inertes. Se enrolan en el allowlist de CI ÚNICAMENTE los archivos que HARN-01/03/04 tocan directamente en esta fase:
  - `verification/test_public_surface.py` (D-06, HARN-03/IN-06)
  - `verification/test_finding_count_consistency.py`
  - `verification/test_findings_dedupe_by_title.py`
  - El/los archivo(s) nuevo(s) o casos nuevos del test de falsificación de D-04
  - `verification/test_matriz_sweep_snapshot.py` y `verification/test_main_matriz_login_fail_uniformity.py` **SOLO SI** D-08 se revierte a "reparar" (bajo la decisión actual, D-08 = aceptar deuda, así que estos 2 **no** se enrolan en esta fase)
  - El cierre de esta fase debe **re-declarar por escrito** (no silenciar) que los ~33-35 archivos restantes siguen inertes y fuera de alcance de v1.8.
  - **Si esto es incorrecto:** si el operador espera que Phase 45 sea el punto de disposición TERMINAL para los 40 archivos, el alcance de la fase crece sustancialmente más allá de sus 5 criterios de éxito actuales.

**Consolidación de `ci.yml`**

- **D-11:** Todos los edits de `.github/workflows/ci.yml` de esta fase llegan en **un** cambio consolidado (criterio de éxito 5 del ROADMAP), no dispersos entre planes.

### Claude's Discretion

- Nombre exacto y estructura del/los archivo(s) de test de falsificación de D-04 (nuevo archivo vs. casos agregados a `verification/test_findings_dedupe_by_title.py`).
- Redacción exacta de la decisión escrita y fechada de HARN-04 (D-08) — el contenido mínimo está locked arriba, el wording no.
- Orden de los planes/waves dentro de la fase (p. ej. HARN-03 mecánico primero, HARN-01 con su refactor de fid después, HARN-04 como decisión de checkpoint en cualquier punto).

### Deferred Ideas (OUT OF SCOPE)

- **Reparación completa de `verification/test_matriz_sweep_snapshot.py` / `test_main_matriz_login_fail_uniformity.py`** — diferida por D-08 (aceptar como deuda), no ejecutada en esta fase.
- **Disposición individual de los ~33-35 archivos `verification/` restantes** que hoy no corren en CI (fuera de los tocados por D-10) — permanece formalmente fuera de alcance de v1.8.
- **Enrolamiento mypy completo de `verification/`** — ya excluido explícitamente en `REQUIREMENTS.md § Out of Scope`, no forma parte de HARN-04.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **HARN-01** | Deduplicar los findings de `schema drift` correctamente — título content-addressed o dedupe sólo intra-run, preservando el invariante de conteo de fids (`test_finding_count_consistency.py`), con un test de falsificación que pruebe que una divergencia distinta en el mismo endpoint sigue escribiéndose | §"Hallazgo 1" (la premisa fáctica de D-01 es falsa — medida), §"Hallazgo 2" (mapa exacto de duplicación por driver), §"Hallazgo 3" (P-3 no detecta la violación en drivers), §"Patrón 1" (precedente `divergences.py`), §"Don't Hand-Roll" |
| **HARN-03** | Corregir el comentario stale de Phase 37 (`330`→`336` definiciones) + cerrar el gap `IN-06`; retirar `IN-05` (ya resuelto en Phase 40) | §"Hallazgo 4" (ambos bloques del docstring son mediciones históricas EXACTAS — verificado por worktree), §"Hallazgo 5" (el número medido hoy es **337**, no 336), §"Hallazgo 6" (`test_public_surface.py` pasa solo, cubre 4/6 paquetes, no incluye market-data), D-07 verificado en HEAD |
| **HARN-04** | Decidir explícitamente el destino de `verification/` de matriz — reparar con presupuesto declarado y enrolamiento en CI, o documentar formalmente como debt aceptada | §"Hallazgo 7" (los 3 tests verdes identificados por nombre + qué asevera cada uno), §"Hallazgo 8" (2 de 3 subsumidos por un test enrolado; el 3ro es auto-referencial), §"Hallazgo 9" (el archivo de login NO está cubierto — la "respuesta esperada" de D-08 no se sostiene para él), §"Hallazgo 10" (el rol de canario NO está transferido hoy) |
</phase_requirements>

---

## Summary

Esta fase no necesita librerías nuevas, ni patrones nuevos, ni investigación de ecosistema. Todo lo que hace falta ya existe en el repo. Lo que sí necesita —y lo que esta investigación produce— son **mediciones contra HEAD** que corrigen cuatro premisas fácticas que la cadena backlog → research → CONTEXT arrastró sin re-medir. Tres de esas correcciones cambian materialmente lo que el plan tiene que hacer.

La más importante: **la premisa fáctica de D-01 es falsa**. D-01 justifica "dedupe intra-run únicamente" diciendo que el problema medido "proviene de un run de dos pases" y que "el dedupe intra-run lo resuelve por completo". Medido: el runner de dos pases corre el driver **dos veces como dos procesos separados** (`main_market_data.py:193-211` — el segundo pase se invoca con `MARKET_LIBS_STRICT_DECODE=1`, leído del entorno en tiempo de import). Y dentro de **un** proceso, cada par `(client_function, surface)` se visita **exactamente una vez** (34 sitios de llamada estáticos → 34 pares distintos, medido por AST). Por lo tanto un dedupe intra-run cuya clave incluya la superficie es **provablemente inerte**: no puede colapsar nada. Si la clave excluye la superficie, colapsa el par sync+async dentro de cada pase (22 bloques → 11 en la corrida de 33-05), pero eso contradice la convención lockeada `surface-in-title-write-new` y ciega una divergencia genuina sync≠async de forma. El plan tiene que elegir conscientemente entre esas dos ramas — no puede satisfacer el criterio de éxito 1 sin hacerlo.

La segunda: **el "comentario stale" de HARN-03 nunca estuvo mal**. Reconstruí ambos árboles con `git worktree` y corrí el gate: el bloque de la línea 47 ("Before Phase 37") imprime byte-idéntico `183 __all__ names, 330 definitions scanned, 13 constant/alias exports, 23 exempted` en `00ffb2f~1` (el último commit antes de la Phase 37), y el bloque de la línea 58 ("After Phase 37") imprime byte-idéntico `186 / 330 / 442` en `00a9821` (el commit que lo escribió). Ambos son citas históricas exactas de su árbol declarado. Lo que está roto no es el dígito: es que ninguno de los dos bloques está **fechado ni pineado a un commit**, así que un lector razonable lee el segundo como "lo que el gate imprime hoy" — y hoy imprime `187 / 337 / 467`. Aplicar D-05 literalmente (cambiar `330` → `336` en ambas líneas) **introduciría un error fáctico en un registro histórico exacto** y además escribiría un número que ya es incorrecto. El propio D-05 trae la escotilla: "verificar con el propio gate antes de escribir el número".

La tercera: **el invariante P-3 no detecta la violación que Pitfall 10 describe**. `verification/test_finding_count_consistency.py` es un property test sobre `append_finding` con su propio allocator local (`_make_allocator`); no parsea ni importa ningún driver. Reordenar `_next_fid()` en los 7 sitios no puede ponerlo rojo, y dejarlo en su orden actual tampoco. El criterio de éxito 2 ("P-3 sigue verde sin aflojarse") se cumple trivialmente y por lo tanto **no mide nada**. El peso de probar D-03 recae enteramente sobre el test de falsificación nuevo, que tiene que asertar el orden en los drivers (por AST o por conteo fid-vs-bloques sobre el helper real), no sólo sobre `append_finding`.

**Primary recommendation:** Planificar HARN-03 y D-09 como trabajo mecánico verificable (con los números re-medidos de esta investigación: `337`, no `336`), y llevar HARN-01 a un **checkpoint de decisión antes de implementar**, porque la clave de dedupe —incluir o no `surface`— determina si el entregable colapsa 22→11 o 22→22, y esa elección no está resuelta por D-01. HARN-04 ya es un checkpoint por diseño; esta investigación le entrega la evidencia por archivo que D-08 exige, incluyendo el hecho de que la "respuesta esperada" de D-08 (*"nada adicional medido"*) **se sostiene para `test_matriz_sweep_snapshot.py` y NO se sostiene para `test_main_matriz_login_fail_uniformity.py`**.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Dedupe de findings de drift (HARN-01) | Driver (`main_*.py`, raíz del repo) | Harness lib (`verification/findings.py`) | La decisión de "¿ya emití esto en esta corrida?" es estado **por proceso del driver**; `findings.py` es append-only por contrato y no debe ganar estado de sesión (ver §Don't Hand-Roll) |
| Asignación de fid (D-03) | Driver (`_next_fid()` module-level) | — | Cada driver tiene su propio `_fid_counter` + `_seed_fid_counter()`; el orden respecto del dedupe es una decisión de call-site, no de librería |
| Falsificación del dedupe (D-04) | `verification/test_*.py` | CI job `lint` (allowlist) | Los locks de driver viven en `verification/` y sólo cuentan como cobertura si están en el allowlist explícito (declaración inerte de Phase 41) |
| Corrección del docstring (D-05) | `tools/check_surface_types.py` | CI job `lint` step `surface-types` | El gate ya corre en CI; el docstring es prosa, no ejecutable — ningún gate lo verifica |
| Enrolamiento en CI (D-06/D-10/D-11) | `.github/workflows/ci.yml` job `lint` | — | Precedente lockeado (Phase 32 D-05, Phase 42-01): los gates cross-package son **steps** dentro de `lint`, nunca jobs nuevos |
| Fix de dereference `Segment` (D-09) | Driver (`main_market_data.py`) | — | El campo vive en `packages/market-data-client/src/.../models.py` y ya es correcto; el bug es puramente de consumo en el driver |
| Decisión escrita HARN-04 (D-08) | Artefacto de fase (`.planning/phases/45-.../`) | `ROADMAP.md` backlog | Es una decisión con base escrita, no un work item — Pitfall 12 lo dice explícitamente |

---

## Standard Stack

### Core

Esta fase **no introduce ninguna dependencia**. Todo el stack ya está en `uv.lock`.

| Herramienta | Versión (medida en HEAD) | Propósito | Por qué es la estándar acá |
|---------|-------|---------|--------------|
| pytest | **9.0.3** `[VERIFIED: uv run pytest --version]` | Runner de los locks de `verification/` y del test de falsificación D-04 | Ya es el runner de todo el repo (`pyproject.toml:102-118`) |
| Python | **3.12.13** (venv activo) `[VERIFIED: uv run python --version]` | Runtime | Matriz de CI: 3.12 + 3.13 |
| uv | **0.11.3** `[VERIFIED: uv --version]` | Gestión de workspace y ejecución | `uv sync --all-packages --all-extras --dev --frozen` |
| ruff | **0.15.12** `[VERIFIED: uv run ruff --version]` | Lint + formato de los edits de driver | Ya corre en CI job `lint` |
| mypy | **1.20.2** `[VERIFIED: uv run mypy --version]` | Typecheck — **no cubre los drivers de la raíz** (ver §Pitfall 4) | Ya corre en CI job `typecheck` |
| `git worktree` | git del sistema | Reconstruir árboles históricos para re-medir los números del docstring de D-05 | Único método no destructivo para verificar una cita histórica |

**Nota de drift de documentación:** `CLAUDE.md` declara `pytest >=8.3` y `CPython 3.12.11`; el árbol tiene pytest **9.0.3** y Python **3.12.13**. No es bloqueante para esta fase y no está en su alcance, pero si el plan toca `CLAUDE.md` por cualquier motivo, es un dato medido disponible. `[VERIFIED: comandos de versión ejecutados en HEAD]`

**Installation:** ninguna. `uv sync --all-packages --all-extras --dev --frozen` ya deja el árbol listo.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `set[str]` module-level en cada driver para el dedupe intra-run | Un registro compartido en `verification/findings.py` | **Rechazado.** `findings.py` es append-only por contrato con preservación de campos de operador (`STACK.md:219`: *"Refactorizarlo arriesga la garantía de preservación Classification/Rationale/Regression/Resolution"*). Meterle estado de sesión lo convierte en stateful y rompe el aislamiento por `monkeypatch(_FINDINGS_DIR)` del que dependen 4 archivos de test |
| `hashlib.sha256(json.dumps(actual_schema))` como parte de la CLAVE de dedupe | Digest embebido en el **título** | El digest en el título es exactamente lo que D-01 rechaza (más código nuevo, superficie de Pitfall 9). Un digest en la clave in-process no toca el artefacto humano y es reversible |
| Test de falsificación como archivo nuevo | Casos agregados a `verification/test_findings_dedupe_by_title.py` | Discreción explícita de CONTEXT. **Recomendación:** archivo nuevo. El archivo existente cubre el contrato genérico de `idempotent_by_title` sobre 4 paquetes parametrizados (12 tests verdes); el test de D-04 cubre la **rama drift de los drivers**, que es un sujeto distinto, y mezclarlos hace que el docstring del archivo (que hoy dice "HARN-08 / HARN-10") mienta sobre su alcance |

---

## Package Legitimacy Audit

**No aplica — esta fase no instala ningún paquete externo.** `[VERIFIED: CONTEXT.md D-01..D-11 no nombran ninguna dependencia nueva; el trabajo es edits de driver, edits de docstring, un test nuevo, un edit de ci.yml y un documento de decisión]`

| Package | Registry | Verdict | Disposition |
|---------|----------|---------|-------------|
| — (ninguno) | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

Si un plan propone instalar cualquier cosa, eso es señal de scope creep: `STACK.md § What NOT to Use` lista explícitamente `msgspec`/`pydantic`/`attrs`/`jsonschema`/`vcrpy`/`pytest-recording` como reaches plausibles y equivocados en este milestone.

---

## Hallazgos medidos

Cada hallazgo trae el comando que lo produjo. Todos corridos contra HEAD (`22bc8ed`, rama `milestone/v1.8-cierre-deuda-post-v1.7`) el 2026-09-01.

### Hallazgo 1 — El "run de dos pases" son DOS PROCESOS, no dos pases dentro de un run

`[VERIFIED: main_market_data.py:193-211 + grep en los 5 drivers]`

```
main_market_data.py:193
# Phase 33 (LIVE-TYP-01): flag del SEGUNDO pase. El runner de dos pases corre el
# driver una vez en modo observable (censo completo) y otra con
# ``MARKET_LIBS_STRICT_DECODE=1``, que prueba que el raise de modo estricto
# efectivamente dispara.
...
main_market_data.py:212
_STRICT: bool = os.getenv("MARKET_LIBS_STRICT_DECODE") == "1"
```

`_STRICT` se lee del entorno **en tiempo de import del módulo**. Cambiar de pase 1 a pase 2 requiere un proceso nuevo. Los 5 drivers tienen el mismo comentario (`main_higyrus.py:170`, `main_ambito_financiero.py:81`, `main_iol.py:197`, `main_matriz.py:324`).

**Consecuencia directa sobre D-01:** su justificación —*"el problema MEDIDO proviene de un run de dos pases … el dedupe intra-run lo resuelve por completo"*— descansa sobre leer "un run de dos pases" como un único proceso. No lo es. Un `set()` de proceso se vacía entre pase 1 y pase 2.

### Hallazgo 2 — Mapa exacto de la duplicación, por driver

`[VERIFIED: AST walk sobre los 5 drivers + parseo del findings file committeado]`

**`main_market_data.py`** — 34 sitios de llamada a `_write_schema_snapshot`, 25 `client_function` distintos, **34 pares `(client_function, surface)` distintos**. 9 funciones se llaman en ambas superficies:

```
get_calendar, get_calendar_config, get_health, get_health_feed,
get_instruments, get_latest, get_market_data, get_segments, get_symbols
```

El archivo de baseline se elige **sólo por `client_function`** (`main_market_data.py:474`: `_SCHEMA_DIR / f"{client_function.replace('_','-')}.json"`), así que sync y async comparan contra el MISMO baseline.

**`main_iol.py` / `main_higyrus.py` / `main_matriz.py`** — `_write_or_check_schema` tiene **exactamente un** sitio de llamada cada uno (iol:1827, higyrus:2309, matriz:1978), dentro de un `for` sobre `func_name`s distintos. Ningún `func_name` se repite en la iteración.

**`main_ambito_financiero.py`** — un solo sitio, una sola función, una vez por corrida.

**Los 2 sitios de type drift de `main_iol.py`** (:1617, :1685) — bucles sobre `_ASSUMED_QUOTE_FIELDS.items()` / `_ASSUMED_HISTORICAL_FIELDS.items()`, cada `key` visitada una vez, `surface="both"`.

> **Conclusión medida:** de los 7 sitios de D-02, **sólo el de `main_market_data.py` puede producir un duplicado dentro de un mismo proceso** — y sólo entre superficies. Los otros 6 son estructuralmente de visita única: un dedupe intra-run sobre ellos no puede disparar jamás.

### Hallazgo 3 — El ledger committeado prueba que los duplicados son byte-idénticos en contenido

`[VERIFIED: parseo de .planning/verification/market-data-client-findings.md]`

36 bloques `### F-` de drift. Para **cada** título duplicado, `distinct(expected, actual) == 1` — los bloques sync y async son idénticos en contenido:

| Título | n | distinct(exp,act) | surfaces | statuses |
|--------|---|-------------------|----------|----------|
| `schema drift en get_market_data` | 8 | **1** | sync, async | EXPECTED, NO-FIX, OPEN |
| `schema drift en get_health_feed` | 6 | **1** | sync, async | NO-FIX, OPEN |
| `schema drift en get_calendar` | 6 | **1** | sync, async | NO-FIX, OPEN |
| `schema drift en get_calendar_config` | 6 | **1** | sync, async | NO-FIX, OPEN |
| `schema drift en get_latest` | 4 | **1** | sync, async | NO-FIX, OPEN |
| (6 títulos ×1, superficie ya embebida en el nombre de la función) | 6 | 1 c/u | — | NO-FIX |

Dos lecturas críticas:

1. **El caso (b) de D-04 nunca ocurrió en producción, pero es estructuralmente alcanzable.** Ninguna corrida histórica produjo dos drifts *distintos* sobre el mismo endpoint. Pero sync y async comparten baseline y pueden divergir — es literalmente lo que la clase de finding `SYNC-ASYNC-DRIFT` existe para detectar. Un dedupe que ignore la superficie ciega ese caso.

2. **Un dedupe cross-run por título sería catastrófico, y ahora está medido.** Bajo `schema drift en get_market_data` conviven F-37 (`EXPECTED`), F-74 (`NO-FIX`) y F-203 (`OPEN`). El scan de título de `append_finding` corre **antes** de la guarda de status humano (`findings.py:665-669`), así que con `idempotent_by_title=True` un drift nuevo haría no-op contra F-37 (EXPECTED, de 2026) y **desaparecería de la cola OPEN del operador mientras el drift sigue vivo**. Esto es Pitfall 9 con nombres de fid concretos. **Es evidencia fuerte a favor de la elección de D-01 de NO ir cross-run** — vale la pena citarla en el plan.

**Aritmética del entregable** (corrida de 33-05, 22 bloques / 8 snapshots):

| Mecanismo | Resultado | Satisface criterio 1? |
|-----------|-----------|----------------------|
| Intra-run, clave incluye `surface` | 22 → **22** (inerte) | **No** |
| Intra-run, clave ignora `surface` | 22 → **11** | Parcialmente (colapsa por superficie, no "por pase") |
| Cross-run por título (rechazado por D-01) | 22 → **8** | Sí, al costo de Pitfall 9 — medido arriba |

### Hallazgo 4 — Los dos bloques del docstring de `check_surface_types.py` son citas históricas EXACTAS

`[VERIFIED: git worktree + ejecución del gate en cada árbol]`

| Bloque del docstring | Árbol declarado | Commit reconstruido | Salida medida | ¿Coincide? |
|---|---|---|---|---|
| `:47-49` "Before Phase 37" → `183 names, 330 defs, 13 const, 23 exempted` | último commit antes de la Phase 37 | `00ffb2f~1` | `183 __all__ names, 330 definitions scanned, 13 constant/alias exports, 23 exempted (dunder 13, private-helper 1, serialize-out 9), 0 violations` | **byte-idéntico** |
| `:58-60` "After Phase 37" → `186 names, 330 defs, 442 fields` | el árbol de la Phase 37 | `00a9821` (el commit que escribió el docstring) | `186 __all__ names, 330 definitions scanned, 442 fields scanned, 13 constant/alias exports, 24 exempted (…ws-catch-all 1), 0 violations` | **byte-idéntico** |

Ambos bloques nacieron en el mismo commit `00a9821` (`test(37-04): pin the out-of-scope spare and floor the new field counter`). Ninguno fue nunca incorrecto.

**El defecto real** es de framing, no de dígito: ninguno de los dos bloques está fechado ni pineado a un commit, y el segundo está introducido por *"**After Phase 37**, over a tree whose fields have since been typed::"* — que un lector de hoy lee como "lo que imprime ahora". Ese es el `IN-01` genuino.

### Hallazgo 5 — El número medido HOY es **337**, no 336

`[VERIFIED: uv run python tools/check_surface_types.py, determinístico — mismo md5 en dos corridas]`

```
surface types: 6 packages, 187 `__all__` names, 337 definitions scanned, 467 fields scanned,
13 constant/alias exports, 24 exempted (dunder 13, private-helper 1, serialize-out 9,
ws-catch-all 1), 0 violations
```

El `336` que aparece en `ROADMAP.md:198`, `REQUIREMENTS`, `STACK.md:195` y CONTEXT D-05 se midió **antes** de las Phases 43/44, que movieron la superficie de `market-data-client`. Las tres cifras del bloque `:58` están desactualizadas, no una: `186→187`, `330→337`, `442→467`.

**Este es el motivo por el que D-05 dice "verificar con el propio gate antes de escribir el número".** El planificador debe usar **337** y debe corregir las tres cifras, o el "fix del comentario stale" deja dos cifras stale al lado de la que arregló.

### Hallazgo 6 — `test_public_surface.py` pasa solo, y cubre 4 de 6 paquetes

`[VERIFIED: uv run pytest -q verification/test_public_surface.py → 4 passed; ls verification/snapshots/]`

- **4 passed en 0.04s** — la precondición explícita de D-06 ("verificar que el archivo pasa solo, antes de agregarlo") está **satisfecha**.
- Snapshots existentes: `ambito-financiero-client`, `higyrus-client`, `iol-client`, `matriz-client`. **`market-data-client` y `wallets-client` NO están cubiertos.**
- Último toque: `f93cb2a` (2026-08-29, Phase 38-01).

**Dos implicancias para el plan:**
1. **Bajo riesgo de enrolamiento.** El paquete cuya superficie está en movimiento (`market-data-client`, Phases 43/44) no está en el snapshot, así que enrolarlo no puede reddear CI por los cambios recientes.
2. **Es una red parcial, y el cierre de la fase debe decirlo.** Enrolar `test_public_surface.py` cierra `IN-06` literalmente, pero **no** da cobertura de superficie a `market-data-client`. Declararlo evita que un lector futuro lea "public surface enrolado en CI" como cobertura total.

### Hallazgo 7 — Los 3 tests verdes de HARN-04, identificados por nombre

`[VERIFIED: uv run pytest -v … | grep " PASSED"]`

Estado reproducido exactamente como lo predice Pitfall 12: **19 failed, 3 passed, 19 errors**.

Los 3 verdes están **todos** en `test_matriz_sweep_snapshot.py`; `test_main_matriz_login_fail_uniformity.py` tiene **cero** tests verdes.

| Test verde | Qué asevera |
|---|---|
| `test_matriz_sweep_snapshot_count_matches_18_minus_cfi_sanity` | `len(_PROBE_FIXTURES) == 17` — una tabla de fixtures **interna al propio archivo**. No toca código de producción |
| `test_matriz_envelope_probe_helper_exists` | `callable(main_matriz._envelope_probe)` — el helper existe |
| `test_matriz_risk_probes_unwrap_their_envelope_key` | por grep del source: las 2 risk probes citan `envelope_key="detailedPosition"` / `="accountData"` |

### Hallazgo 8 — 2 de los 3 verdes están SUBSUMIDOS por un test ya enrolado en CI; el 3ro es auto-referencial

`[VERIFIED: docstring de verification/test_main_matriz_risk_envelope_keys.py:22-30 + el docstring del propio test verde]`

`verification/test_main_matriz_risk_envelope_keys.py` **está en el allowlist de CI** (`ci.yml:83`) y declara tres capas:

> 1. `_envelope_probe` ya no ACEPTA `envelope_key=None` (el parámetro es `str` requerido).
> 2. Ninguna call site del driver pasa `envelope_key=None`.
> 3. Las dos risk probes citan exactamente las keys que `_core` desenvuelve.

La capa 1 subsume `test_matriz_envelope_probe_helper_exists` (un parámetro requerido implica que el helper existe) y es **estrictamente más fuerte**. La capa 3 subsume `test_matriz_risk_probes_unwrap_their_envelope_key` — y el propio test verde lo dice en su docstring:

> *"El lock estructural completo (incluido que `_envelope_probe` ya no ACEPTA `None`) vive en `verification/test_main_matriz_risk_envelope_keys.py`, **que además corre en CI**."*

**Esto es una auto-declaración in-code de superseded.** Es la evidencia más fuerte posible para el ítem (1) de D-08 y debería citarse verbatim en el documento de decisión.

El tercero (`_PROBE_FIXTURES == 17`) asevera la consistencia interna de una tabla que vive dentro del archivo mismo: si el archivo se retira, la aserción se queda sin sujeto. Su pérdida cuesta **cero cobertura de producción**.

### Hallazgo 9 — La "respuesta esperada" de D-08 se sostiene para un archivo y NO para el otro

`[VERIFIED: grep de probe_login en verification/ + lectura de main_matriz.py:807]`

D-08 anticipa que la respuesta al ítem (1) sea *"nada adicional medido"*. Medido:

| Archivo | ¿Aserción única no cubierta por CI? | Evidencia |
|---|---|---|
| `test_matriz_sweep_snapshot.py` | **No — "nada adicional medido" SE SOSTIENE** | Hallazgo 8: 2 verdes subsumidos por un test enrolado, 1 auto-referencial |
| `test_main_matriz_login_fail_uniformity.py` | **Sí — la respuesta esperada NO se sostiene** | Ningún test enrolado asevera que `probe_login_sync` devuelva `'FINDING'` (no `'FAIL'`). `test_main_matriz_skip_line_shape.py` está enrolado pero cubre la forma de la línea de skip, no la taxonomía del retorno de login. `test_main_higyrus_skip_line_shape.py` cubre **higyrus**, no matriz |

**Matiz que hace la disposición aceptable de todos modos:** la conducta que ese archivo guarda **está presente en HEAD** — `main_matriz.py:807` devuelve `ProbeResult("login_sync", "FINDING", f"{fid} (OPEN): AuthenticationError")`. Así que el archivo no cubre un bug abierto; cubre una **regresión potencial** que hoy nadie guarda.

La redacción honesta para el ítem (1) de D-08, por archivo, es entonces:
- sweep_snapshot → *"nada adicional medido; superseded in-code por `test_main_matriz_risk_envelope_keys.py`, que corre en CI"*
- login_fail_uniformity → *"una aserción única: `probe_login_sync` devuelve FINDING, no FAIL (CR-02 de la Phase 11). La conducta está presente y verificada en HEAD (`main_matriz.py:807`); lo que se acepta como deuda es la ausencia de un guardián de regresión, no un defecto abierto."*

> **Opción de bajo costo que el planificador puede querer evaluar en el checkpoint** (no una recomendación de ampliar alcance): esa aserción es grep-assertable en ~3 líneas y podría añadirse a un archivo **ya enrolado** (`test_main_matriz_skip_line_shape.py`), convirtiendo la fila de deuda en una fila cerrada sin enrolar ningún archivo nuevo ni reparar nada. Si se descarta, descartarlo por escrito.

### Hallazgo 10 — El rol de canario NO está transferido hoy, y su transferee natural es él mismo inerte

`[VERIFIED: grep -rln "probe_context" verification/ + grep de httpx_mock en los tests enrolados]`

El rol de canario existe porque los 2 archivos rotos **invocan los probes directamente**, no vía `main()`, y por eso ejercitan el seam `probe_context` (`HARN-VERIF-01`, planes 33-02/33-03).

Medido sobre los 13 archivos enrolados en CI:
- `test_main_matriz_deep_chain.py` — **0** usos de `httpx_mock`; es enteramente AST/`inspect`. **No invoca ningún probe en runtime.**
- `test_main_matriz_risk_envelope_keys.py` — AST + grep de source. **No invoca.**
- Ningún archivo enrolado referencia `probe_context`.

Los únicos archivos que referencian `probe_context` son `verification/__init__.py`, `verification/divergences.py`, `verification/test_divergences.py` y **`verification/test_probe_context_coverage.py`** — y ninguno de los tres tests está enrolado.

`verification/test_probe_context_coverage.py` es el transferee natural: **6 passed** hoy, y su docstring dice que es *"el único lugar del repo donde los cinco drivers se cuentan juntos"* con un piso numérico de 130 probes. Pero su propio docstring cierra con:

> *"**Alcance:** `verification/` no corre en CI (ver `33-BASELINE.md`); esto es un gate local de fase."*

**Consecuencia para D-08 ítem (2):** transferir el rol a un archivo que también es inerte **no es una transferencia** — es renombrar el abandono. Las dos salidas honestas son:
- **(a) Abandono explícito**, con la frase escrita ("el seam `probe_context` queda sin canario en CI a partir de esta fecha; el riesgo aceptado es que un refactor de `probe_context` no reddea ninguna pata de CI"), o
- **(b) Transferencia real**, enrolando `verification/test_probe_context_coverage.py` en el allowlist. Pasa hoy (6/6). Bajo la lectura de D-10 esto es defendible —HARN-04 lo "toca directamente" al designarlo transferee— pero es un archivo más que los 4 que D-10 enumera, y por lo tanto **requiere confirmación explícita del operador** antes de aterrizar en el edit consolidado de D-11.

### Hallazgo 11 — El censo de `verification/` se movió: hoy es 53 / 13 / 40, no 52 / 12 / 40

`[VERIFIED: ls verification/test_*.py | wc -l → 53; conteo del allowlist de ci.yml:80-93 → 13]`

| Medida | 41-ROLLUP (baseline) | HEAD (hoy) |
|--------|---------------------|-----------|
| Archivos `verification/test_*.py` en disco | 52 | **53** |
| Enrolados en el allowlist de `lint` | 12 | **13** |
| **Inertes** | **40** | **40** |

El delta viene de la Phase 42-01 (`7cc103a`), que agregó `test_literal_census_venue_gate.py` **y** su línea de allowlist a la vez. El número que importa —40 inertes— no cambió, pero la **re-declaración por escrito que exige D-10 debe usar 53 / 13 / 40**, no los 52 / 12 heredados de CONTEXT y de `41-ROLLUP.md`.

### Hallazgo 12 — `DRV-MD-SEG-43` reproducido exactamente; y el bug es peor que "un finding espurio"

`[VERIFIED: uv run mypy main_market_data.py]`

```
main_market_data.py:1541: error: "Segment" has no attribute "marketSegmentId"
            ids_sync = sorted(s.marketSegmentId for s in seg_sync)
main_market_data.py:1542: error: "Segment" has no attribute "marketSegmentId"
            ids_async = sorted(s.marketSegmentId for s in seg_async)
```

`Segment` en HEAD (`packages/market-data-client/src/market_data_client/models.py:870-895`) declara exactamente `segment: str` y `live_instruments: int`. Como es `@dataclass(frozen=True, slots=True)`, `s.marketSegmentId` levanta `AttributeError` en runtime — capturado por el `except Exception` de `:1543` y degradado vía `_finding_for_exc` a un finding `ERROR-MAP`.

**El costo real no es el finding espurio: es que `probe_parity` deja de comparar.** El probe existe para detectar `SYNC-ASYNC-DRIFT` sobre segments y hoy sale por la rama de excepción **siempre**, antes de comparar nada. Es un probe ciego que se reporta como FINDING. El fix es `s.segment` en ambas líneas (ambos campos son `str`; `sorted()`, `set()` y los `len()` de los mensajes siguen funcionando sin cambios).

---

## Architecture Patterns

### Diagrama del camino de emisión de findings de drift

```
                         ┌──────────────────────────────────────────┐
  Runner de 2 pases      │ PROCESO 1: MARKET_LIBS_STRICT_DECODE unset│
  (dos invocaciones)  ─► │ PROCESO 2: MARKET_LIBS_STRICT_DECODE=1    │
                         └──────────────────────────────────────────┘
                                          │  (estado de proceso se pierde entre ambos)
                                          ▼
                            main_*.py  main()  →  probes
                                          │
              ┌───────────────────────────┴────────────────────────────┐
              │                                                        │
      camino DRIFT (HARN-01)                              camino DECODE (ya resuelto)
              │                                                        │
   _write_schema_snapshot / _write_or_check_schema         market_data_client._decode
   (schema_of(wire) vs baseline committeado)                 emite record de 6 claves
              │                                                        │
              │  ┌── HOY: fid = _next_fid()  ◄── ORDEN A CORREGIR (D-03)│
              │  │                                            probe_context bindea
              │  ▼                                            endpoint + surface
              │ append_finding(                                        │
              │   title = "schema drift en {func}"   ◄─ CONTENT-FREE    ▼
              │   idempotent_by_title = False        ◄─ HOY      DivergenceToFindingHandler
              │ )                                              (verification/divergences.py:167)
              │                                                        │
              │  ┌── PROPUESTO: ¿(func, surface, digest) ya visto?      │ title = "{model}{path}: {kind}
              │  │      SÍ → return (sin quemar fid)                    │   (declared=…, observed=…) [{surface}]"
              │  │      NO → fid = _next_fid(); append_finding(...)     │ idempotent_by_title = True
              │  ▼                                                     ▼
              └────────────────────► verification/findings.py::append_finding
                                          │
                          ┌───────────────┴────────────────┐
                          │ 1. scan por TÍTULO (si el kwarg)│ ◄── corre ANTES de la guarda humana
                          │ 2. guarda de status humano      │     (findings.py:665-669)
                          │ 3. upsert por fid               │
                          └───────────────┬─────────────────┘
                                          ▼
                        .planning/verification/<pkg>-findings.md
                        (committeado al repo — por eso un dedupe
                         cross-run es permanente y no reversible)
```

Lo que el diagrama hace visible y la prosa no: **el camino DECODE ya resolvió este problema correctamente y el camino DRIFT nunca lo copió.** Ese es el patrón a reutilizar.

### Pattern 1: Título portador de identidad + `idempotent_by_title` (el precedente in-repo)

**What:** `verification/divergences.py:167-181` es el único lugar del repo donde `idempotent_by_title=True` se usa sobre contenido **variable** (no sobre un terminal). Funciona porque el título carga la identidad completa del evento.

**When to use:** Cuando dos eventos distintos deben producir dos bloques y dos eventos iguales uno solo — exactamente el contrato de D-04.

**Example:**
```python
# Source: verification/divergences.py:167-181 (HEAD)
_findings.append_finding(
    slug,
    fid=self._next_fid(slug),
    class_="SHAPE",
    surface=surface,
    status="OPEN",
    # Determinístico y portador de identidad: este string ES la
    # clave de dedupe cross-run (33-01-SUMMARY.md, selección
    # ``surface-in-title-write-new``).
    title=f"{model}{path}: {kind} (declared={declared}, observed={observed}) [{surface}]",
    expected=f"model declares {declared}",
    actual=f"wire sent {observed}",
    diff=f"{declared} -> {observed} at {model}{path} via {endpoint}",
    idempotent_by_title=True,
)
```

Cinco componentes en el título: `model`, `field_path`, `kind`, `declared`, `observed`, **más `[surface]`**. Un drift distinto → título distinto → bloque nuevo. Sin digest, sin hash, sin código nuevo.

**Dos advertencias sobre copiarlo tal cual al camino drift:**
1. Este sitio pasa `fid=self._next_fid(slug)` **inline como argumento** — es decir, asigna el fid ANTES de la decisión de dedupe. Tiene exactamente el hazard que D-03 prohíbe. **No copiar ese aspecto.** Es tolerable ahí porque la unidad de censo de ese handler es `self.seen` (un `set` de tuplas `(slug, model, path, kind)` poblado *antes* del sink, `divergences.py:165`), no el conteo de fids — un desacople deliberado que su propio docstring declara (`:122-123`: *"El conteo de findings NO lo es — con la superficie embebida en el título hay aproximadamente dos findings por triple"*).
2. `[surface]` en el título es **la convención lockeada `surface-in-title-write-new`** (citada en `main_market_data.py:401-409` y en CONTEXT § Established Patterns). Un dedupe de drift que ignore la superficie va en contra de ella para la clase drift.

### Pattern 2: Guarda intra-proceso antes de quemar el fid (la forma que D-03 exige)

**What:** Un `set` a nivel de módulo en cada driver, consultado antes de `_next_fid()`.

**When to use:** En los 7 sitios de D-02, **si** el checkpoint de HARN-01 resuelve la pregunta de la clave.

**Example (forma, no clave — la clave es la decisión abierta):**
```python
# Módulo, junto a _fid_counter:
_seen_drift_keys: set[tuple[str, ...]] = set()

# En el sitio de drift, ANTES de _next_fid():
key = (client_function, surface, _digest(actual_schema))   # ← clave: ver checkpoint
if key in _seen_drift_keys:
    return                      # no-op: NINGÚN fid consumido (D-03)
_seen_drift_keys.add(key)
fid = _next_fid()               # ← el fid se asigna DESPUÉS de la decisión
append_finding(..., fid=fid, title=f"schema drift en {client_function}", ...)
```

Por qué esta forma y no `idempotent_by_title=True`:
- No consulta el archivo committeado → no puede hacer no-op contra un bloque `EXPECTED` de otro milestone (Hallazgo 3, punto 2).
- Se resetea solo al terminar el proceso → cumple D-01 literalmente.
- El fid nunca se quema en un no-op → cumple D-03 por construcción.
- El título humano no cambia → cero riesgo sobre el round-trip del parser de `findings.py` y sobre la invariante CR-02 de título de una sola línea (`findings.py:639`).

**Cada driver necesita su propio `set` y su propio reset**, igual que cada uno tiene su propio `_fid_counter`. Los fixtures existentes ya resetean estado de driver por test (`test_main_matriz_login_fail_uniformity.py:38-40` hace `main_matriz._fid_counter = 0`), así que el test nuevo debe resetear el `set` de la misma forma o los tests se contaminan entre sí.

### Pattern 3: Gate cross-package como **step** del job `lint`, nunca job nuevo

**What:** Precedente lockeado (Phase 32 D-05, Phase 31 D-12, Phase 42-01). Los 4 gates cross-package (`decode-intactness`, `uniform-structure`, `surface-types`, `driver locks`) son steps consecutivos dentro de `lint`.

**Why:** El job `test` pasa un path explícito (`packages/${{ matrix.package }}`) que **pisa `testpaths`**, así que `verification/` nunca corre ahí — está documentado en 3 comentarios distintos de `ci.yml` (`:52-54`, `:57-59`, `:69-78`).

**Para D-11:** el edit consolidado es una extensión de la lista de `ci.yml:80-93`. Mantener el comentario de `:75-78` que explica *por qué* la lista es explícita — es la razón por la que el próximo lector no la reemplaza por `pytest verification/`.

### Anti-Patterns to Avoid

- **`idempotent_by_title=True,` como diff de una línea en los 7 sitios.** Es el warning sign literal de Pitfall 9 y ahora está **medido**: colapsaría contra bloques `EXPECTED`/`NO-FIX` ya triageados (Hallazgo 3).
- **Relajar `test_finding_count_consistency.py`.** Warning sign literal de Pitfall 10. Nota además que ese test **no puede volverse rojo por este trabajo** (Hallazgo 3 de la §Pitfalls) — si aparece un diff sobre él, es señal de que algo se está tocando por el motivo equivocado.
- **Cambiar `ci.yml` de la lista explícita a `pytest verification/`.** Enrolaría 40 archivos nunca corridos en CI. Prohibido por D-10, por `STACK.md:212` y por Pitfall 12.
- **Escribir `336` en el docstring.** El número medido es `337` (Hallazgo 5). Escribir un número que la propia investigación de la fase midió como incorrecto sería el mismo defecto que la fase existe para cerrar.
- **"Corregir" el bloque de la línea 47 al valor de hoy.** Es una cita histórica exacta de un árbol de hace 5 fases (Hallazgo 4). Cambiarla a `337` la vuelve falsa.
- **Refactorizar `verification/findings.py` para "deduplicar todo".** `STACK.md:219`: arriesga la garantía de preservación Classification/Rationale/Regression/Resolution. La primitiva ya existe y el gap no está ahí.
- **`git rm` de los 2 archivos de HARN-04 sin dar cuenta de los 3 verdes ni del canario.** Warning sign literal de Pitfall 12. (Notar: D-08 = aceptar como deuda **no implica borrar**; "aceptar deuda documentada" es compatible con dejar los archivos en disco con un puntero al documento de decisión.)

---

## Don't Hand-Roll

| Problema | No construir | Usar en su lugar | Por qué |
|---------|-------------|-------------|-----|
| Dedupe de findings por contenido | Una segunda primitiva de dedupe en `findings.py` | `append_finding(..., idempotent_by_title=True)` — ya existe, ya testeada (12 tests verdes sobre 4 paquetes) | CONTEXT § Reusable Assets es explícito: *"no hace falta escribir una segunda primitiva"*. El gap es el título y el orden, no la primitiva |
| Título portador de identidad | Un esquema de digest nuevo | El patrón de `divergences.py:176` — componentes concatenados, sin hash | Es determinístico, legible por humanos y ya lockeado como convención `surface-in-title-write-new` |
| Seed del allocator de fids | Un contador nuevo o un reset manual | `max_existing_fid(pkg)` + `_seed_fid_counter()` — ya en los 5 drivers | `verification/test_findings_fid_seed.py` documenta que `idempotent_by_title` **provably does not substitute** para el seed. Son mecanismos ortogonales; no fusionarlos |
| Verificar el número del gate | Contar definiciones a mano o por grep | `uv run python tools/check_surface_types.py` | Es el propio gate, determinístico (mismo md5 en corridas repetidas), y es lo que D-05 pide literalmente |
| Reconstruir qué imprimía el gate en el pasado | Estimar o asumir | `git worktree add --detach <path> <commit>` + correr el gate con el intérprete del venv actual | Único método no destructivo. Nota: el `python3` del sistema es demasiado viejo (`dataclass(slots=True)` falla); usar `.venv/bin/python` |
| Detectar el bug de `Segment` | Un test nuevo | `uv run mypy main_market_data.py` | Ya lo levanta. La razón por la que CI no lo hace es de **alcance de gate**, no de tipabilidad (`43-DISPOSITION.md § 5`) |

**Key insight:** Este repo ya resolvió cada sub-problema de esta fase al menos una vez. El trabajo es **transferir soluciones existentes al camino que no las recibió**, no inventar. Cualquier plan que introduzca un mecanismo nuevo está, con alta probabilidad, sin haber encontrado el precedente.

---

## Common Pitfalls

### Pitfall A: El dedupe intra-run aterriza y no colapsa nada (riesgo NUEVO, medido en esta investigación)

**What goes wrong:** Se implementa el `set` intra-proceso con la clave "correcta" `(func, surface, digest)`, el test de falsificación pasa (porque llama al helper dos veces a mano), CI queda verde, la fase se cierra — y la próxima corrida en vivo produce **exactamente los mismos 22 bloques**, porque dentro de un proceso ningún par `(func, surface)` se repite (Hallazgo 2).

**Why it happens:** D-01 asume que los dos pases son un run. No lo son (Hallazgo 1).

**How to avoid:** Resolver la clave de dedupe en un checkpoint **antes** de implementar (ver §Open Questions Q1). Y exigir que el criterio de aceptación de HARN-01 sea un **conteo medido de bloques emitidos**, no sólo "el test pasa".

**Warning signs:** Un plan cuyo criterio de aceptación de HARN-01 es sólo "el test de falsificación pasa". Un SUMMARY que no reporta un antes/después de conteo de bloques.

### Pitfall B: El criterio de éxito 2 se cumple vacuamente

**What goes wrong:** El plan corre `test_finding_count_consistency.py`, lo ve verde, y declara cumplido el criterio 2 ("el invariante de fids sigue verde sin aflojarse").

**Why it happens:** Ese archivo es un property test sobre `append_finding` **con su propio allocator local** (`_make_allocator`, `_emit`). No importa ningún driver, no parsea ningún driver. Su docstring dice que `_write_or_check_schema` *"comparte exactamente este hazard y queda cubierto por la misma propiedad"* — eso es cierto como **propiedad**, y falso como **detección**. El test es verde con el orden actual (fid antes) y verde con el orden nuevo (fid después). **Es incapaz de distinguirlos.**

**How to avoid:** El test de falsificación de D-04 tiene que llevar el peso de D-03. Dos formas complementarias:
- **Runtime:** invocar el helper de drift real del driver dos veces con la misma divergencia y asertar `fids_emitidos == bloques_nuevos` (que es la propiedad P-3 aplicada al sujeto correcto) **y** que el contador `_fid_counter` del driver no avanzó en el no-op.
- **AST:** asertar que en cada uno de los 7 sitios, la llamada a `_next_fid()` aparece **después** del `return`/`continue` de la guarda de dedupe. El repo tiene 6 precedentes de locks por AST sobre drivers (`test_main_*_deep_chain.py`, `test_main_matriz_risk_envelope_keys.py`).

**Warning signs:** Un plan que lista `test_finding_count_consistency.py` como la verificación del criterio 2 y nada más.

### Pitfall C: El test de falsificación prueba supresión, no dedupe (Pitfall 9 upstream)

**What goes wrong:** El test asevera sólo el colapso (misma divergencia → 1 bloque). Pasa. No prueba nada sobre pérdida de censo.

**How to avoid:** El brazo (b) es obligatorio y debe estar **nombrado en el docstring** (specific idea de CONTEXT). Con la clave `(func, surface, digest)`, el brazo (b) se construye variando **el digest** con `func` fijo. Si la clave elegida ignora `surface`, el brazo (b) debe además cubrir el caso `mismo func, misma superficie, contenido distinto`, que es donde la clave sin digest fallaría.

**Warning signs:** Un test llamado `test_*_dedupe_*` con una sola aserción. Un docstring que sólo describe el colapso.

### Pitfall D: mypy no mira los drivers de la raíz — el fix de D-09 no tiene gate que lo proteja

**What goes wrong:** Se arregla `s.marketSegmentId` → `s.segment`, CI queda verde, y el mismo bug reaparece la próxima vez que un modelo cambie de forma.

**Why it happens (MEDIDO, no supuesto — `43-DISPOSITION.md § 5`):** el `files` de mypy del root (`pyproject.toml:97`) lista seis rutas `packages/*/src`; el hook de pre-commit está scoped a `files: ^packages/.*/src/` (`.pre-commit-config.yaml:32`); y `verification/test_main_market_data_deep_chain.py` parsea el driver con `ast` **sin importarlo**.

**How to avoid:** Esta fase **arregla el sitio**; cerrar el gate (apuntar mypy a los 5 drivers de la raíz) es alcance mayor y no está en HARN-01/03/04 ni en los 5 criterios del ROADMAP. **Recomendación:** arreglar las 2 líneas y **declarar el gap del gate por escrito** en el cierre de la fase, con destino nombrado (backlog v1.9), en vez de dejarlo implícito. Escalarlo dentro de esta fase es scope creep; silenciarlo es exactamente la clase de rot que la fase existe para cerrar.

**Warning signs:** Un plan que agrega los 5 drivers al `files` de mypy "de paso" — eso levanta un número desconocido de errores nuevos en 3000+ líneas × 5 archivos, dentro de una fase de limpieza.

### Pitfall E: HARN-04 se lee como trabajo y crece (Pitfall 12 upstream)

**What goes wrong:** El plan estima HARN-04 en minutos, o hace `git rm` de los 2 archivos.

**How to avoid:** Es un **checkpoint de decisión** con un artefacto escrito y fechado (criterio 3 del ROADMAP, literal). Los tres ítems que D-08 exige ya tienen sus respuestas medidas en los Hallazgos 7-10; el trabajo restante es redactar, no investigar. Notar que "aceptar como deuda documentada" **no obliga a borrar los archivos**: dejarlos en disco con un puntero al documento de decisión preserva los 3 verdes sin enrolar nada.

**Warning signs:** Un plan que estima HARN-04 en minutos. Un `git rm` sin nota sobre los 3 verdes. Un diff de `ci.yml` que enrola los 2 archivos rotos (D-08 dice explícitamente que **no** se enrolan bajo la decisión actual).

### Pitfall F: Los edits de `ci.yml` se dispersan entre planes

**What goes wrong:** El plan de HARN-03 agrega `test_public_surface.py`, el de HARN-01 agrega el test nuevo, y el criterio 5 ("un cambio consolidado") queda incumplido con dos commits que tocan `ci.yml`.

**How to avoid:** D-11 es explícito. Estructurar los planes para que **exactamente uno** toque `.github/workflows/ci.yml`, al final, con las 4-5 líneas juntas. Verificable: `git log --oneline <base>..HEAD -- .github/workflows/ci.yml | wc -l` debe dar **1**.

**Warning signs:** Dos planes que ambos listan `.github/workflows/ci.yml` en sus archivos tocados.

---

## Code Examples

### Sitio de drift actual — market-data (el único con duplicación estructural)

```python
# Source: main_market_data.py:508-522 (HEAD)
    if committed.get("schema") == actual_schema:
        return
    fid = _next_fid()                                    # ← D-03: mover DESPUÉS del dedupe
    append_finding(
        _PKG,
        fid=fid,
        class_="SHAPE",
        surface=surface,                                 # ← la superficie SÍ viaja como campo…
        status="OPEN",
        title=f"schema drift en {client_function}",      # ← …pero NO está en el título
        expected=json.dumps(committed.get("schema"), ensure_ascii=False),
        actual=json.dumps(actual_schema, ensure_ascii=False),
        diff="baseline schema difiere; NO se sobreescribe (D-25)",
        base_url=base_url,
    )
```

### Sitio de drift actual — iol / higyrus / matriz (forma idéntica, retorno de tupla)

```python
# Source: main_higyrus.py:588-601 (HEAD) — main_iol.py:1752-1765 y main_matriz.py:583-596 son idénticos módulo `surface`
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="SHAPE",
        surface="both",                       # iol/higyrus="both", matriz="sync"
        status="OPEN",
        title=f"Schema drift en {func_name}",  # ← nótese la S mayúscula: NO matchea el de market-data
        expected=json.dumps(committed.get("schema"), ensure_ascii=False),
        actual=json.dumps(actual_schema, ensure_ascii=False),
        diff="comparar expected vs actual; NO se sobreescribe baseline (D-25)",
        base_url=base_url,
    )
    return ("FINDING", f"{fid}|{file_path.name}")   # ← el fid viaja al ProbeResult del caller
```

**Dos detalles que el plan debe manejar:**
1. **El contrato de retorno.** Estos 3 devuelven `("FINDING", "<fid>|<file>")` y el caller acumula en `finding_fids` / `fids`. Un no-op de dedupe necesita un tercer estado de retorno (p. ej. `("PASS", "drift ya reportado en esta corrida")`) — devolver `("FINDING", ...)` sin fid rompería el `detail.split("|", 1)` del caller. **`main_ambito_financiero.py` devuelve un `ProbeResult` directamente** y `main_market_data.py` devuelve `None` — los 3 contratos de retorno son distintos y el fix no es copy-paste entre drivers.
2. **La capitalización difiere.** market-data usa `"schema drift en …"` (minúscula), los otros 4 usan `"Schema drift en …"` (mayúscula). Cualquier lock por grep de título debe cubrir ambos.

### Los 2 sitios hermanos de type drift de iol (D-02)

```python
# Source: main_iol.py:1613-1630 (HEAD) — el de :1685 es el mismo patrón sobre historical_raw[0]
                elif observed[key] != expected_type:
                    fid = _next_fid()
                    append_finding(
                        _PKG,
                        fid=fid,
                        class_="SHAPE",
                        surface="both",
                        status="OPEN",
                        title=f"type drift on `{key}` in get_quote",  # ← key-scoped, content-free
                        expected=f"`{key}`: {expected_type}",
                        actual=f"`{key}`: {observed[key]}",
                        diff=f"tipo observado != asumido para `{key}`",
                        base_url=base_url,
                    )
                    finding_fids.append(fid)
```

**Nota de límite de alcance:** en el MISMO bucle, la rama `if key not in observed:` emite `f"missing assumed key \`{key}\` in get_quote"` — **4 sitios hermanos** (2 por `get_quote`, 2 por `get_historical_quotes[0]`) con el mismo hazard de título key-scoped. **D-02 nombra 7 sitios y NO incluye estos 4.** Es un límite deliberado; el plan no debe expandirlo. Si el cierre de la fase quiere ser honesto, puede declararlos por escrito como el mismo hazard fuera de alcance.

### El fix de D-09 (2 líneas)

```python
# Source: main_market_data.py:1541-1542 (HEAD) — dentro de probe_parity, en el try
        ids_sync = sorted(s.marketSegmentId for s in seg_sync)      # AttributeError en runtime
        ids_async = sorted(s.marketSegmentId for s in seg_async)
```
```python
# Fix (Segment declara `segment: str` y `live_instruments: int` — models.py:894-895)
        ids_sync = sorted(s.segment for s in seg_sync)
        ids_async = sorted(s.segment for s in seg_async)
```

Los mensajes del cuerpo (`f"sync == async ({len(ids_sync)} ids)"`, `only_sync = sorted(set(ids_sync) - set(ids_async))`) siguen funcionando sin cambios: `segment` es `str`, igual que el `marketSegmentId` que se creía tener. Verificación: `uv run mypy main_market_data.py` debe pasar de 2 errores a 0 en esas líneas.

### El allowlist de CI que D-11 consolida

```yaml
# Source: .github/workflows/ci.yml:79-93 (HEAD) — 13 archivos hoy
        run: |
          uv run pytest -q \
            verification/test_main_market_data_deep_chain.py \
            ... (11 más) ...
            verification/test_literal_census_venue_gate.py
```

D-10 agrega: `test_public_surface.py`, `test_finding_count_consistency.py`, `test_findings_dedupe_by_title.py`, y el/los archivo(s) de D-04 → **17 archivos**, o 18 si el checkpoint de canario resuelve enrolar `test_probe_context_coverage.py` (Hallazgo 10). Los 4 (o 5) pasan hoy en local — ver §Environment Availability.

---

## Runtime State Inventory

Esta fase **no** es un rename/refactor de strings, pero sí modifica el orden de asignación de un contador con estado y escribe en un artefacto committeado. Inventario acotado a eso:

| Categoría | Ítems encontrados | Acción requerida |
|-----------|-------------|------------------|
| **Datos almacenados** | `.planning/verification/*-findings.md` — 5 archivos committeados al repo. `market-data-client-findings.md` contiene **36 bloques de drift** con fids `F-37`..`F-244` y statuses `EXPECTED`/`NO-FIX`/`OPEN` | **Ninguna migración.** El dedupe intra-proceso no lee ni reescribe estos archivos. Si el plan derivara a cross-run, sí habría migración de datos — otro motivo para respetar D-01 |
| **Estado de módulo en proceso** | `_fid_counter` (los 5 drivers), `_auth_failed`, `_auth_failure_reason`, `_STRICT` (leído del entorno al import) | El `set` de dedupe nuevo es estado del mismo tipo. **Los tests deben resetearlo explícitamente**, siguiendo el precedente de `test_main_matriz_login_fail_uniformity.py:38-40` (`main_matriz._fid_counter = 0`) |
| **Baselines de schema** | `.planning/verification/schemas/*.json` — write-once (D-25, nunca se sobreescriben en drift) | **Ninguna.** El fix de dedupe no cambia la política D-25 |
| **Secretos / env vars** | `MARKET_LIBS_STRICT_DECODE`, `MARKET_DATA_VERIFY_MUTATING` y las credenciales de `.env` por paquete | **Ninguna.** Ningún nombre cambia. No se corre ningún driver en vivo en esta fase (el milestone ya decidió que el dedupe aterriza DESPUÉS de las corridas en vivo — `ROADMAP.md:53`) |
| **Estado registrado en el SO** | Ninguno — verificado: este repo no registra tareas, servicios ni procesos persistentes | **Ninguna** |
| **Artefactos de build** | Ninguno relevante — no hay bump de versión de paquete en esta fase (PUB-01 vive en la Phase 44) | **Ninguna** |
| **Configuración de servicio vivo** | `.github/workflows/ci.yml` — vive en git, no en una UI | **Ninguna migración**; es un edit de archivo, consolidado por D-11 |

---

## State of the Art

| Enfoque anterior | Enfoque actual | Cuándo cambió | Qué implica |
|--------------|------------------|--------------|--------|
| `verification/` no corría en ninguna pata de CI | Allowlist explícito, hand-maintained, hoy **13** archivos | Phase 36 (WR-01 encontró un lock recién entregado e inerte) | Cualquier lock nuevo de esta fase es **inerte hasta que entra al allowlist** — es lo que hace obligatorio a D-10 |
| `append_finding` sólo idempotente por `fid` | `idempotent_by_title` opt-in | Phase 11 (HARN-08/10) | La primitiva existe; el gap es el título y el orden |
| Título de divergencia sin superficie | `surface-in-title-write-new` — la superficie va en el título y una superficie distinta escribe bloque nuevo | Phase 33 (33-01-SUMMARY) | Es la convención lockeada contra la que se mide cualquier clave de dedupe de drift |
| `_fid_counter` sin seedear | `max_existing_fid()` + `_seed_fid_counter()` en los 5 drivers | Phase 33 (D-16/D-24) | `idempotent_by_title` **no** sustituye al seed — mecanismos ortogonales (`test_findings_fid_seed.py:12-18`) |
| `Segment` con `marketSegmentId`/`marketId`/`description` | `Segment` con `segment`/`live_instruments` | Phase 43 (D-06, lectura fresca del wire de 2026-08-31) | Deja `main_market_data.py:1541-1542` colgando — `DRV-MD-SEG-43` |
| Censo de `verification/`: 52 / 12 / 40 | **53 / 13 / 40** | Phase 42-01 (`7cc103a`) | La re-declaración de D-10 debe usar las cifras de hoy |
| Gate de superficie: `186 / 330 / 442` | **`187 / 337 / 467`** | Phases 38→43 (acumulado) | El "fix del comentario stale" debe corregir **tres** cifras, con el valor **337** |

**Deprecado / obsoleto:**
- El número **336** que circula en `ROADMAP.md:198`, `STACK.md:195` y CONTEXT D-05 — medido antes de las Phases 43/44. El valor de hoy es **337**.
- Las cifras **52 / 12** de `41-ROLLUP.md` y de CONTEXT D-10 — hoy **53 / 13** (el 40 inerte no cambió).
- `CLAUDE.md` declara `pytest >=8.3` y `CPython 3.12.11`; el árbol corre pytest **9.0.3** y Python **3.12.13**. Fuera de alcance, pero medido.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | El runner de dos pases se invoca como dos procesos separados de shell (no hay un wrapper que haga `importlib.reload` dentro de un proceso) | Hallazgo 1 | Bajo. `_STRICT` se lee al import (`main_market_data.py:212`), así que incluso un wrapper necesitaría reload explícito. No encontré ningún script runner en el repo (`grep "dos pases"` sólo devuelve los comentarios de los 5 drivers) — el runner parece ser operator-runs-and-pastes, consistente con `STACK.md:215`. Si existiera un wrapper single-process, el dedupe intra-run sí colapsaría entre pases y Q1 se vuelve más fácil, no más difícil |
| A2 | El caso (b) de D-04 (sync y async divergen en forma para el mismo endpoint) es alcanzable en producción | Hallazgo 3 | Bajo. Nunca ocurrió en los datos históricos (`distinct(exp,act)==1` en los 5 títulos duplicados), pero la clase de finding `SYNC-ASYNC-DRIFT` existe precisamente para ese evento y `probe_parity` existe para detectarlo. Si se juzga inalcanzable, la clave puede ignorar `surface` sin costo — pero esa es una decisión del operador, no una lectura de research |
| A3 | Enrolar `test_public_surface.py` no reddea CI en ninguna de las patas | Hallazgo 6 | Bajo. Pasa 4/4 en local sobre el intérprete 3.12.13; el job `lint` corre en ubuntu-latest con el mismo `uv sync --frozen`. El riesgo residual es una diferencia de plataforma en la serialización de firmas, que el formato del snapshot (texto determinístico, sin paths) hace improbable |
| A4 | La estimación "38 firmas de argumento" de D-08 para la rama "reparar" | CONTEXT D-08 | No re-medida en esta investigación (D-08 está locked en "aceptar deuda", así que el presupuesto de la rama alternativa no se ejercita). Si el operador revierte a "reparar", ese número **debe** re-medirse antes de planificar |

---

## Open Questions

**RESOLVED (2026-09-01):** Q1, Q2 y Q3 (bloqueantes) fueron presentadas al operador vía
checkpoint tras esta investigación y resueltas. Q4 y Q5 (no bloqueantes) se resolvieron con la
recomendación de este documento. Las cinco resoluciones están enmendadas en
`45-CONTEXT.md § Checkpoint de resolución post-research (2026-09-01)`, que es la fuente de
verdad para planning — este documento se conserva sin editar como evidencia de la medición
original.

### Q1 — ¿Qué es la clave de dedupe? (BLOQUEANTE para HARN-01)

**Lo que sabemos:** D-01 lockea "intra-run únicamente". Medido (Hallazgos 1-3): dentro de un proceso, cada `(client_function, surface)` se visita exactamente una vez, así que una clave que incluya `surface` **no puede colapsar nada**. Una clave que la ignore colapsa el par sync+async (22 → 11) pero va contra la convención lockeada `surface-in-title-write-new` y ciega un `SYNC-ASYNC-DRIFT` genuino de forma.

**Lo que no está claro:** cuál de las dos ramas quiere el operador. El criterio de éxito 1 dice *"deja de escribir un bloque nuevo **por pase**"*, que literalmente ninguna de las dos entrega (eso requeriría cross-run, que D-01 rechaza).

**Recomendación:** llevarlo a un **`checkpoint:human-verify` antes de la primera tarea de implementación de HARN-01**, presentando las tres columnas de aritmética del Hallazgo 3 y la evidencia de Pitfall 9 (los fids `F-37 EXPECTED` / `F-74 NO-FIX` / `F-203 OPEN` bajo un mismo título) que respalda seguir rechazando el cross-run. Las tres opciones a poner sobre la mesa:
- **(i)** Clave `(func, surface, digest)` — fiel a D-01 y a `surface-in-title-write-new`, **entregable: 0 bloques colapsados**. Honesta pero deja el criterio 1 sin sustancia; requiere re-redactar el criterio 1 en el ROADMAP.
- **(ii)** Clave `(func, digest)` (ignora superficie, **conserva el contenido**) — **entregable: 22 → 11**. Colapsa el par sync/async idéntico y sigue escribiendo bloque nuevo si sync y async difieren, porque el digest cambia. **Recomendada:** es la única que entrega colapso medible sin ninguna pérdida de censo, y el brazo (b) de D-04 la protege exactamente.
- **(iii)** Cross-run content-addressed — **entregable: 22 → 8**, requiere revertir D-01 y asumir Pitfall 9. No recomendada.

> Nota sobre (ii) y la convención: `surface-in-title-write-new` gobierna el **título** (que no cambia bajo (ii) — sigue siendo `schema drift en {func}`) y el camino **decode**. Aplicarla como restricción sobre la *clave in-process* del camino **drift** es una extensión por analogía, no una lectura literal. Vale explicitarlo en el checkpoint.

### Q2 — ¿Se corrige el bloque histórico de la línea 47? (BLOQUEANTE para HARN-03)

**Lo que sabemos:** ambos bloques son citas históricas exactas de su árbol declarado (Hallazgo 4, verificado por worktree). El valor de hoy es 337, no 336 ni 330 (Hallazgo 5).

**Lo que no está claro:** D-05 lockea "corregir `:47` y `:58`, 330 → 336". Ejecutarlo literalmente introduce un error fáctico en `:47` (que documenta el árbol pre-Phase-37) y escribe un número incorrecto en ambos.

**Recomendación:** el mismo checkpoint puede resolver las dos preguntas. Opción de menor daño y mayor fidelidad al espíritu de D-05 (*"el comentario dice el número medido"*):
- **`:47`** — dejar las cifras (`183 / 330`) y **añadir el pin de commit**: `Before Phase 37 (medido en 00ffb2f~1) this gate printed::`. La cita se vuelve verificable en vez de falsificada.
- **`:58`** — reemplazar el bloque congelado por el valor **medido hoy** (`187 __all__ names, 337 definitions scanned, 467 fields scanned, … 24 exempted …`) y fecharlo (`medido 2026-09-01`), o pinnearlo al commit igual que `:47` y agregar una tercera línea con el valor actual. Corregir **las tres** cifras, no sólo `330`.

Si el operador prefiere el literal de D-05, la investigación deja constancia de que `336` es incorrecto y de que `:47` es históricamente exacto — decisión suya, medición nuestra.

### Q3 — ¿El rol de canario se transfiere o se abandona? (BLOQUEANTE para HARN-04, ítem 2 de D-08)

**Lo que sabemos:** ningún archivo enrolado en CI ejercita el seam `probe_context` en runtime (Hallazgo 10). El transferee natural, `verification/test_probe_context_coverage.py`, pasa 6/6 hoy pero es él mismo inerte y su docstring lo declara ("gate local de fase").

**Recomendación:** las dos salidas honestas son abandono explícito, o transferencia real vía enrolamiento. Bajo D-10 la transferencia es defendible (HARN-04 lo "toca directamente" al designarlo), pero es un archivo más que los que D-10 enumera → **requiere confirmación del operador antes del edit consolidado de D-11**. La opción que **no** es admisible es escribir "transferido a `test_probe_context_coverage.py`" sin enrolarlo: sería renombrar el abandono.

### Q4 — ¿Se cierra la fila de deuda del archivo de login por 3 líneas? (no bloqueante)

**Lo que sabemos:** la "respuesta esperada" de D-08 (*"nada adicional medido"*) **no se sostiene** para `test_main_matriz_login_fail_uniformity.py` (Hallazgo 9): asevera algo que ningún test enrolado asevera. La conducta está presente en HEAD.

**Recomendación:** presentarlo en el checkpoint de HARN-04 como una opción de ~3 líneas grep-assertables dentro de un archivo **ya enrolado**. Si se descarta, descartarlo por escrito en el documento de decisión — es la diferencia entre "deuda decidida" y "deuda no vista".

### Q5 — ¿Se declara el gap de gate de mypy sobre los drivers de la raíz? (no bloqueante)

**Lo que sabemos:** `uv run mypy main_market_data.py` levanta `DRV-MD-SEG-43`, pero ningún gate de CI apunta ahí (Hallazgo 12, Pitfall D). Arreglar las 2 líneas no impide la reaparición.

**Recomendación:** arreglar el sitio (D-09) y **declarar el gap por escrito** en el cierre, con destino nombrado en el backlog v1.9. Apuntar mypy a los 5 drivers dentro de esta fase es scope creep de tamaño no medido.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | Todo | ✓ | 0.11.3 | — |
| Python 3.12 | Runtime del venv | ✓ | 3.12.13 | — |
| pytest | D-04, D-06, verificación | ✓ | 9.0.3 | — |
| ruff | Lint de los edits | ✓ | 0.15.12 | — |
| mypy | Verificación de D-09 | ✓ | 1.20.2 | — |
| `git worktree` | Verificar las citas históricas de D-05 | ✓ | git del sistema | — |
| `.venv/bin/python` | Correr el gate en árboles históricos | ✓ | 3.12.13 | El `python3` del sistema **falla** (`dataclass() got an unexpected keyword argument 'slots'`) — usar siempre el del venv |
| Red / credenciales de vendor | **NO requeridas** | n/a | — | Esta fase no corre ningún driver en vivo (`ROADMAP.md:53`: el dedupe aterriza DESPUÉS de las corridas en vivo, ya completadas en la Phase 42) |

**Missing dependencies with no fallback:** ninguna.
**Missing dependencies with fallback:** ninguna.

**Estado verde medido en HEAD (línea base antes de tocar nada):**

| Comando | Resultado |
|---------|-----------|
| `uv run python tools/check_surface_types.py` | `0 violations` (187 / 337 / 467) |
| `uv run pytest -q verification/test_public_surface.py` | **4 passed** |
| `uv run pytest -q verification/test_finding_count_consistency.py` | **2 passed** |
| `uv run pytest -q verification/test_findings_dedupe_by_title.py` | **12 passed** |
| `uv run pytest -q verification/test_probe_context_coverage.py` | **6 passed** |
| `uv run pytest -q verification/test_matriz_sweep_snapshot.py verification/test_main_matriz_login_fail_uniformity.py` | **19 failed, 3 passed, 19 errors** (rojo pre-existente, HARN-VERIF-01) |
| `uv run mypy main_market_data.py` | 2 errores en `:1541`/`:1542` (DRV-MD-SEG-43) |

---

## Validation Architecture

`workflow.nyquist_validation` es `true` en `.planning/config.json` `[VERIFIED: lectura del archivo]` — esta sección aplica.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest **9.0.3** (+ pytest-asyncio `asyncio_mode="auto"`, pytest-httpx, pytest-cov) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (líneas 102-118); `testpaths = ["packages", "tests", "verification"]`, `pythonpath = ["."]`, `--strict-markers`, `--strict-config` |
| Quick run command | `uv run pytest -q verification/test_findings_dedupe_by_title.py verification/test_finding_count_consistency.py verification/test_public_surface.py` |
| Full suite command | `uv run pytest -q` (cubre `packages/`, `tests/`, `verification/` — nótese que **incluye el rojo pre-existente de HARN-VERIF-01**, ver abajo) |
| Comando espejo de CI (el que importa) | `uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run python tools/check_decode_intactness.py && uv run python tools/check_uniform_structure.py && uv run python tools/check_surface_types.py && uv run pytest -q <allowlist de ci.yml>` |

> **Trampa de la suite completa:** `uv run pytest -q` a secas incluye `verification/`, que arrastra los **19 failed / 19 errors** pre-existentes de HARN-VERIF-01. Bajo D-08 ese rojo **no se repara en esta fase**, así que "suite completa verde" no es un gate alcanzable ni deseable. El gate real de la fase es el **espejo de CI**, que corre la allowlist explícita. Un plan que exija "pytest verde a secas" está fijando un criterio que D-08 hace imposible por diseño.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HARN-01 (a) | La MISMA divergencia repetida dentro de una corrida colapsa a 1 bloque `### F-` | unit | `uv run pytest -q verification/test_drift_dedupe_falsification.py -k collapse` | ❌ Wave 0 |
| HARN-01 (b) | Una divergencia **DISTINTA** sobre el MISMO endpoint sigue escribiendo un bloque nuevo | unit (falsificación) | `uv run pytest -q verification/test_drift_dedupe_falsification.py -k not_collapse` | ❌ Wave 0 |
| HARN-01 / D-03 | Un no-op de dedupe **no consume un fid** (`_fid_counter` no avanza) — ver Pitfall B | unit | `uv run pytest -q verification/test_drift_dedupe_falsification.py -k fid_not_burned` | ❌ Wave 0 |
| HARN-01 / D-02 | Los **7** sitios llaman `_next_fid()` **después** de la guarda de dedupe | AST lock | `uv run pytest -q verification/test_drift_dedupe_falsification.py -k call_order` | ❌ Wave 0 |
| HARN-01 / crit. 2 | P-3 sigue verde **sin diff** | regresión + gate de diff | `uv run pytest -q verification/test_finding_count_consistency.py` **y** `git diff --quiet <base> HEAD -- verification/test_finding_count_consistency.py` | ✅ existe (2 passed) — pero **no detecta** la violación en drivers (Pitfall B) |
| HARN-03 / D-05 | El docstring cita el número que el gate imprime hoy | manual + gate | `uv run python tools/check_surface_types.py` y comparar contra el docstring | ✅ gate existe; la comparación es manual-only (el docstring es prosa) |
| HARN-03 / D-06 | `test_public_surface.py` corre en CI | CI (allowlist) | `uv run pytest -q verification/test_public_surface.py` + inspección de `ci.yml` | ✅ existe (4 passed) |
| HARN-03 / D-07 | `matriz_client.__version__` existe | smoke | `uv run python -c "import matriz_client; print(matriz_client.__version__)"` → `0.3.0` | ✅ verificado en HEAD |
| HARN-04 / D-08 | Decisión escrita y fechada, con los 3 ítems nombrados | **manual-only** (checkpoint) | — | n/a — es un artefacto, no un test. Los Hallazgos 7-10 le dan la evidencia |
| D-09 | El driver no dereferencia campos inexistentes de `Segment` | typecheck | `uv run mypy main_market_data.py` → 0 errores en `:1541`/`:1542` | ✅ mypy existe (no está en CI para este path — Pitfall D) |
| D-11 / crit. 5 | Exactamente **un** commit toca `ci.yml` en toda la fase | gate de git | `test $(git log --oneline <base>..HEAD -- .github/workflows/ci.yml \| wc -l) -eq 1` | ❌ Wave 0 (verificación de cierre) |
| crit. 5 | CI verde en las 12 patas + `lint` + `pre-commit` + `typecheck` | CI | push / PR | ✅ workflow existe |

### Sampling Rate

- **Por commit de tarea:** `uv run ruff check . && uv run ruff format --check .` + el archivo de test que la tarea toca
- **Por merge de wave:** el **comando espejo de CI** completo (gates + allowlist), **no** `pytest -q` a secas
- **Gate de fase:** espejo de CI verde en local, luego CI verde en las 12 patas de la matriz + `lint` + `pre-commit` + `typecheck` (criterio 5)

### Wave 0 Gaps

- [ ] `verification/test_drift_dedupe_falsification.py` (nombre a discreción) — cubre HARN-01 (a), (b), fid-not-burned y call-order. **4 arms mínimo**, con el brazo (b) nombrado en el docstring (specific idea de CONTEXT + Pitfall C)
- [ ] Fixture de reseteo del `set` de dedupe + `_fid_counter` por driver, siguiendo el precedente de `test_main_matriz_login_fail_uniformity.py:38-40` y el `monkeypatch(_FINDINGS_DIR, tmp_path)` de los 4 archivos existentes
- [ ] Verificación de cierre del criterio 5 (un solo commit sobre `ci.yml`) — comando de gate, no un archivo de test
- [ ] Instalación de framework: **ninguna** — pytest 9.0.3 ya presente

**Nota de aislamiento (obligatoria, precedente 33-05):** los 4 archivos de test existentes que tocan findings monkeypatchean `verification.findings._FINDINGS_DIR` a `tmp_path`. El archivo nuevo **debe** hacerlo, y el gate de aceptación debe grepear `git status --porcelain .planning/verification/` después de correrlo — está documentado en `test_finding_count_consistency.py:28-31`. Un test de dedupe que escriba en los findings committeados corrompería el mismísimo artefacto que la fase está limpiando.

---

## Security Domain

`security_enforcement` no está desactivado en config, así que la sección aplica. Esta fase no toca autenticación, sesiones, criptografía ni entrada de red — es harness interno.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | **no** | Ningún cambio en flujos de token. `main_matriz.py:807` se **lee** (Hallazgo 9) pero no se modifica bajo D-08 |
| V3 Session Management | **no** | Sin sesiones |
| V4 Access Control | **no** | Sin control de acceso |
| V5 Input Validation | **no (marginal)** | El único input nuevo es `schema_of(payload)` del wire, que ya se procesa hoy; el dedupe sólo lo hashea/compara en memoria |
| V6 Cryptography | **no** | Si la Q1 resuelve usar un digest, es `hashlib.sha256` como **clave de igualdad**, no como control de seguridad. No hay decisión criptográfica que tomar |
| V7 Error Handling & Logging | **sí** | El ladder D-09 (`_finding_for_exc`) debe preservarse: un no-op de dedupe es un camino **sin excepción**. Ver Threat Patterns |
| V8 Data Protection | **sí (indirecta)** | Los findings se **commitean al repo**. El título y los campos `expected`/`actual` no deben ganar contenido nuevo sin revisar PII |

### Known Threat Patterns for este stack (harness de verificación en Python)

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| **Pérdida silenciosa de censo** — un dedupe se traga una divergencia real y el operador nunca la ve | **Repudiation / Information Disclosure (por omisión)** | El brazo (b) del test de falsificación (D-04). Es el control de seguridad primario de esta fase: el modelo de amenaza de este proyecto ES "una divergencia real que nunca llega a un humano" |
| **Fid quemado en un no-op** — el driver reporta `FINDING=N` con N > bloques escritos; el reporte miente | **Repudiation** | Asignar el fid después de la decisión (D-03) + el arm `fid_not_burned` del test nuevo |
| **PII en el ledger committeado** | Information Disclosure | `schema_of()` produce keys+types, PII-free **por construcción** (`main_market_data.py:466-467`). Si el fix cambia el contenido de `expected`/`actual`, esa propiedad debe re-verificarse. **La forma recomendada no los toca** |
| **Excepción nueva en un camino que hoy nunca levanta** | Denial of Service (del run completo) | El contrato del ladder D-09: las divergencias de forma degradan a finding, **nunca a crash**. Un `hashlib`/`json.dumps` sobre un schema con tipos no serializables podría levantar — el no-op de dedupe debe vivir dentro del mismo `try` o usar sólo estructuras ya serializadas (`actual_schema` ya pasó por `json.dumps` en el sitio actual) |
| **Enrolar `verification/` en bloque en CI** | (riesgo de proceso, no de seguridad) | D-10 + el comentario de `ci.yml:75-78`. Convertiría una limpieza acotada en 40 archivos nunca ejercitados enforzados de golpe |
| **Credenciales en `.env` por paquete** | Information Disclosure | **Sin cambios en esta fase.** No se corre ningún driver en vivo; no se toca ningún `.env` |

---

## Project Constraints (from CLAUDE.md)

Directivas accionables extraídas de `./CLAUDE.md`, con su lectura para esta fase:

| Directiva | Aplicación en Phase 45 |
|-----------|------------------------|
| **Stack: Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy strict — todo debe pasar el CI existente** | Vinculante. El criterio 5 es literalmente esto |
| **Sin código compartido entre paquetes (por diseño)** | Los 5 drivers deben recibir el fix **por separado**, cada uno con su propio `set`. No extraer un helper compartido a `verification/` "para no duplicar" — sería el mismo error que `STACK.md:210` prohíbe para los paquetes, y `findings.py` está explícitamente vedado como sitio de estado |
| **Dual sync/async: cualquier fix de lógica debe espejarse en `client.py` y `aio.py`** | **NO aplica.** Los 7 sitios de D-02 y el de D-09 viven en `main_*.py` de la **raíz**, no en `packages/*/src/`. CONTEXT D-09 lo dice explícitamente. Pero sí aplica en otro sentido: en `main_market_data.py` los sitios sync y async del **driver** deben recibir el mismo tratamiento |
| **Seguridad: credenciales en `.env` por paquete; nunca commitear `.env` ni exponer credenciales en logs, reportes o tests** | Vinculante para el test nuevo: fixtures mockeadas, `monkeypatch(_FINDINGS_DIR, tmp_path)`, cero red |
| **Dependencias externas en vivo: los resultados varían por horario de mercado / rate limits** | No aplica — esta fase no corre drivers en vivo (`ROADMAP.md:53`) |
| **GSD Workflow Enforcement: no editar el repo fuera de un comando GSD** | Vinculante para la ejecución |
| **Convenciones de código** (`from __future__ import annotations` obligatorio en todo módulo; `line-length=100`; comillas dobles; docstring de módulo con propósito; `snake_case`; `_privado` para internos; `SCREAMING_SNAKE_CASE` para constantes) | Vinculante para el archivo de test nuevo y para el `set` de dedupe (`_seen_drift_keys`, module-level, con prefijo `_`) |
| **Ruff: reglas E,W,F,I,B,UP,SIM,RUF,ASYNC,PIE,PT,RET,TID,LOG; S101 ignorado sólo bajo `**/tests/**`** | **Resuelto, no es un riesgo** `[VERIFIED: pyproject.toml:52-74]`: `S` (flake8-bandit) **no está en `select`**, así que `S101` nunca dispara en ningún path — la entrada de `per-file-ignores` para `**/tests/**` es defensiva/vestigial. `assert` en `verification/` es libre, como demuestran los 53 archivos existentes. **Lo que sí aplica al archivo de test nuevo:** `PT` (flake8-pytest-style — estilo de fixtures y `parametrize`), `RET` (flake8-return), `TID` (sin imports relativos) y `LOG`. Además `[tool.ruff] src = ["packages/*/src", "packages/*/tests"]` **no incluye `verification/` ni la raíz**, lo cual afecta la clasificación de first-party de `I` (isort): seguir el orden de imports de los archivos existentes de `verification/` en vez de asumir |
| **Docstrings: cada módulo con docstring de propósito** | Vinculante — y para el test de D-04 es además un requisito de contenido: el docstring debe nombrar el escenario que **NO** debe colapsar |

---

## Sources

### Primary (HIGH confidence — medido en este árbol, en esta sesión)

- `uv run python tools/check_surface_types.py` (HEAD y dos árboles históricos vía `git worktree`) — Hallazgos 4 y 5
- `uv run pytest -q` sobre 6 archivos de `verification/` — Hallazgos 6, 7, y la tabla de línea base de §Environment Availability
- `uv run mypy main_market_data.py` — Hallazgo 12
- AST walk sobre `main_market_data.py` (34 sitios, 25 funciones, 34 pares) — Hallazgo 2
- Parseo de `.planning/verification/market-data-client-findings.md` (36 bloques, hashes de `expected`/`actual`) — Hallazgo 3
- `ls verification/test_*.py | wc -l` + conteo del allowlist de `ci.yml:80-93` — Hallazgo 11
- `git log -L 44,60:tools/check_surface_types.py` — procedencia del docstring (commit `00a9821`)

### Primary (HIGH confidence — código y artefactos de este repo)

- `verification/findings.py:583-706` — `append_finding`, orden del scan de título vs. guarda de status humano
- `verification/divergences.py:120-188` — el precedente de título portador de identidad + `idempotent_by_title=True`
- `verification/test_finding_count_consistency.py` (176 líneas, completo) — alcance real del invariante P-3
- `verification/test_findings_dedupe_by_title.py`, `test_findings_fid_seed.py`, `test_probe_context_coverage.py`, `test_main_matriz_risk_envelope_keys.py`, `test_main_matriz_deep_chain.py`, `test_public_surface.py`
- `main_market_data.py` (:193-212, :375-417, :458-522, :1526-1562), `main_iol.py` (:1595-1700, :1720-1766), `main_higyrus.py` (:556-601), `main_matriz.py` (:541-596, :778-810), `main_ambito_financiero.py` (:578-625)
- `packages/market-data-client/src/market_data_client/models.py:870-896` — `Segment` en HEAD
- `.github/workflows/ci.yml` (completo), `pyproject.toml:102-118`, `.planning/config.json`
- `.planning/ROADMAP.md:188-300`, `.planning/REQUIREMENTS.md`, `.planning/research/PITFALLS.md:349-478`, `.planning/research/STACK.md:190-234`, `.planning/phases/41-.../41-ROLLUP.md:160-230`

### Secondary (MEDIUM confidence)

- `.planning/phases/45-.../45-CONTEXT.md` — decisiones locked (autoridad de decisión, pero cuatro de sus premisas fácticas fueron re-medidas y corregidas arriba: Hallazgos 1, 5, 11 y 9)
- `.planning/phases/43-.../43-DISPOSITION.md § 5` (vía la cita completa en `ROADMAP.md:253`) — medición del gap de gate de `DRV-MD-SEG-43`, **reproducida independientemente** en el Hallazgo 12

### Tertiary (LOW confidence)

- Ninguna. Cero WebSearch, cero Context7: el dominio de esta fase es enteramente interno a este repo y no hay librería externa involucrada.

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|------|-------|--------|
| Standard stack | **HIGH** | No hay stack nuevo; las versiones están medidas con los comandos de versión |
| Mapa de duplicación de drift (Hallazgos 1-3) | **HIGH** | AST + parseo del ledger committeado + lectura del mecanismo de dos pases, con los 3 métodos coincidiendo |
| Números del gate de superficie (Hallazgos 4-5) | **HIGH** | Reconstruidos con `git worktree` en 3 árboles; coincidencia byte-idéntica en 2 de 3 y salida determinística (md5 estable) |
| Evidencia de HARN-04 (Hallazgos 7-10) | **HIGH** | Estado de tests reproducido (19/3/19), tests verdes identificados por nombre, superseded auto-declarado in-code, ausencia de canario verificada por grep sobre los 13 archivos enrolados |
| Censo de `verification/` (Hallazgo 11) | **HIGH** | `ls` + conteo del allowlist; el delta rastreado hasta el commit `7cc103a` |
| Pitfalls | **HIGH** | 3 heredados de `PITFALLS.md` (9, 10, 12) reproducidos empíricamente; 3 nuevos (A, B, D) derivados de mediciones de esta sesión |
| Preferencia del operador sobre Q1/Q2/Q3 | **N/A — decisión, no hallazgo** | Presentadas como checkpoints con la evidencia y la aritmética; research no las resuelve |

**Research date:** 2026-09-01
**Valid until:** ~2026-10-01 para el análisis estructural (dominio interno, movimiento lento). **Excepción:** las cifras del gate de superficie (`187 / 337 / 467`) y el censo de `verification/` (`53 / 13 / 40`) **se invalidan con cualquier commit que agregue un export, un campo o un archivo de test** — re-medirlas en el momento de escribir el docstring y el documento de decisión, no copiarlas de acá.
