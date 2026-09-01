# Phase 45: Limpieza del harness — dedupe de drift, comentarios stale, destino de `verification/` de matriz - Context

**Gathered:** 2026-09-01 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

El harness de verificación deja de mentir en dos direcciones — deja de inflar el ledger con
bloques duplicados y deja de arrastrar en silencio archivos que nunca corren — y la deuda de
`verification/` de matriz, rota desde la Phase 15, recibe una decisión escrita en vez de rodar
un milestone más. Requisitos: **HARN-01**, **HARN-03**, **HARN-04**. Sin superficie nueva —
v1.8 es puramente cierre de backlog documentado (`PROJECT.md`, `REQUIREMENTS.md § v2
Requirements`).

**Depends on:** Phase 41 (consolidar el enrolamiento en CI de cualquier lock que genere) y
Phase 42 (decisión de orden explícita del milestone: el dedupe aterriza DESPUÉS de las
corridas en vivo — `ROADMAP.md:53`).
</domain>

<decisions>
## Implementation Decisions

### HARN-01 — mecanismo de dedupe de schema drift

- **D-01:** El dedupe se implementa como **dedupe intra-run únicamente** (reset por corrida),
  no como título content-addressed cross-run. Justificación: el problema MEDIDO (22 bloques
  para 8 snapshots, `HARN-DRIFT-33`) proviene de un run de dos pases, no de runs separados en
  el tiempo — el dedupe intra-run lo resuelve por completo. Es además la opción de menor riesgo:
  un título content-addressed (digest del diff embebido en el título) es más código nuevo y es
  exactamente la superficie donde `PITFALLS.md` Pitfall 9 advierte que un bug de implementación
  volvería a tragarse una divergencia real — el mismo modo de falla que este proyecto existe
  para eliminar. Si una MISMA divergencia sin arreglar persiste día tras día en corridas
  separadas, seguirá escribiendo un bloque nuevo por corrida — eso es status quo (verboso, no
  lossy), no una regresión.
  - **Si esto es incorrecto:** si el operador prefería colapso cross-run permanente, el
    mecanismo cambia a título content-addressed y el test de falsificación tiene que probar
    además que un digest distinto sobre el mismo endpoint escribe un bloque nuevo.

- **D-02:** Alcance de sitios a corregir — **los 5 sitios "schema drift" MÁS los 2 sitios
  hermanos "type drift" de `main_iol.py`** (7 sitios en total, 5 drivers):
  - `main_market_data.py:511` — `f"schema drift en {client_function}"`
  - `main_iol.py:1754` — `f"Schema drift en {func_name}"`
  - `main_higyrus.py:590` — `f"Schema drift en {func_name}"`
  - `main_matriz.py:584` — `f"Schema drift en {func_name}"`
  - `main_ambito_financiero.py:608` — `"Schema drift en get_dollar_banco_nacion"`
  - `main_iol.py:1617` — `f"type drift on \`{key}\` in get_quote"`
  - `main_iol.py:1685` — `f"type drift on \`{key}\` in get_historical_quotes[0]"`
  - Justificación: los 2 sitios hermanos comparten EXACTAMENTE el mismo hazard (título
    endpoint/key-scoped y libre de contenido) que los 5 sitios nombrados en el backlog
    (`HARN-DRIFT-33`); dejarlos sin tocar deja un hazard idéntico sin corregir a dos líneas de
    distancia del fix, en una fase cuyo tema es precisamente cerrar esta clase de rot.

- **D-03:** Reordenar la asignación de fid en los 7 sitios: `_next_fid()` se llama **después**
  de la decisión de dedupe, nunca antes — nunca relajar `verification/test_finding_count_consistency.py`
  (P-3). Si P-3 se pone rojo durante la implementación, es el test haciendo su trabajo.

- **D-04:** Test de falsificación obligatorio (uno o varios, cubriendo los 7 sitios o al menos
  representativo por driver): (a) la MISMA divergencia repetida dentro de una corrida →
  colapsa a 1 bloque; (b) una divergencia DISTINTA sobre el MISMO endpoint dentro de la misma
  corrida → sigue escribiendo un bloque nuevo. Sin (b), el test no prueba dedupe — prueba
  supresión.

### HARN-03 — comentario stale + IN-06 + retiro de IN-05

- **D-05:** Corregir `tools/check_surface_types.py:47` y `:58` — `330` → `336` definitions
  scanned (valor medido, verificar con el propio gate antes de escribir el número).

- **D-06:** Cerrar `IN-06` agregando `verification/test_public_surface.py` al allowlist
  explícito del job `lint` de `.github/workflows/ci.yml` (líneas 81-92 hoy). Verificar que el
  archivo pasa solo, antes de agregarlo.

- **D-07:** Retirar `IN-05` del backlog de `ROADMAP.md` — verificado en HEAD que
  `matriz_client/__init__.py:186` ya tiene `__version__ = "0.3.0"` (resuelto en Phase 40); es
  un retiro de texto, no un fix de código.

### HARN-04 — destino de `verification/` de matriz

- **D-08 [decisión, no auto-aprobada — Recomendación aceptada, "Yes, proceed"]:** **Aceptar
  como deuda formalmente documentada**, no reparar, los dos archivos rotos:
  `verification/test_matriz_sweep_snapshot.py` (17 FAILED + 17 ERROR) y
  `verification/test_main_matriz_login_fail_uniformity.py` (2 FAILED + 2 ERROR) — causa raíz
  única: llaman a los probes de `main_matriz.py` sin el argumento `client`, firma
  pre-migración REFAC-05 (Phase 15).
  - Justificación: reparar significa re-derivar expectativas mockeadas para comportamiento ya
    verificado EN VIVO contra el vendor real a lo largo de 4 milestones (Phases 33/35/37/39) —
    evidencia más débil reemplazando evidencia más fuerte, a escala de 4 milestones de alcance.
    Ningún hallazgo de esta sesión ni de la investigación de fase identificó una aserción
    única que estos 2 archivos cubran y que no esté hoy cubierta por un test enrolado en CI.
  - **La decisión escrita tiene que nombrar explícitamente, por archivo:** (1) qué afirmaría
    cada archivo que un test hoy enrolado en CI no afirma — respuesta esperada: "nada
    adicional medido"; (2) el rol de canario de ambos archivos para el refactor de
    `probe_context` (planes 33-02/33-03) — declarar el rol **transferido** (a qué test/gate) o
    **abandonado explícitamente**, nunca dejarlo implícito; (3) qué pasa con los **3 tests que
    hoy pasan** dentro de esos 2 archivos — no se puede hacer `git rm` sin dar cuenta de ellos
    (moverlos a un archivo vivo, o justificar por qué se pierden).
  - El allowlist de CI se mantiene explícito de todas formas — no se enrola `verification/`
    en bloque como efecto colateral de esta decisión.
  - **Si esto es incorrecto:** si el operador prefiere reparar, la fase necesita un presupuesto
    declarado por adelantado (research estima "38 firmas de argumento", no trivial) y se
    convierte en su propia sub-fase con el mismo cuidado de mirror sync/async que cualquier
    fix de harness — nunca una re-escritura apurada de mocks contra comportamiento ya
    verificado en vivo.

### Alcance — `DRV-MD-SEG-43` (fold-in explícito)

- **D-09 [confirmado por recomendación aceptada]:** Se **foldea** `DRV-MD-SEG-43` en esta
  fase: `main_market_data.py:1541-1542` dereferencia `Segment.marketSegmentId`, campo que la
  Phase 43 removió (`Segment` hoy declara `segment`/`live_instruments`, D-06 de
  `43-DISPOSITION.md`). Fix de 2 líneas, sin lógica, sin obligación de espejo sync/async por
  ser un dereference directo en un driver (no en `client.py`/`aio.py`).
  - Justificación: `44-CONTEXT.md` D-06 lo difirió EXPLÍCITAMENTE a esta fase ("es su tema, no
    el de una fase de release" — `ROADMAP.md:62,175` nombra la Phase 45 como "Limpieza del
    harness"); dejarlo sin tocar en la única fase de limpieza de harness de todo el milestone
    lo empuja a v1.9 sin ninguna razón nueva.
  - No está cubierto por `verification/test_main_market_data_deep_chain.py` (parsea el driver
    por AST sin importarlo) ni por ningún gate estático (mypy del root no mira archivos de la
    raíz del repo) — medido en `43-DISPOSITION.md § 5`.

### Alcance — los 40 locks inertes de `verification/`

- **D-10 [confirmado por recomendación aceptada]:** Esta fase **NO** dispone individualmente
  los 40 archivos `verification/test_*.py` que Phase 41 declaró formalmente inertes
  (`41-ROLLUP.md`, 52 en disco − 12 enrolados = 40). Se enrolan en el allowlist de CI
  ÚNICAMENTE los archivos que HARN-01/03/04 tocan directamente en esta fase:
  - `verification/test_public_surface.py` (D-06, HARN-03/IN-06)
  - `verification/test_finding_count_consistency.py` (necesario para que el criterio 2 de
    HARN-01 — "el invariante de fids sigue verde" — signifique algo en CI, no sólo en local)
  - `verification/test_findings_dedupe_by_title.py` (primitiva existente que HARN-01
    consume; hoy inerte pese a ya estar escrita)
  - El/los archivo(s) nuevo(s) o casos nuevos del test de falsificación de D-04
  - `verification/test_matriz_sweep_snapshot.py` y
    `verification/test_main_matriz_login_fail_uniformity.py` **SOLO SI** D-08 se revierte a
    "reparar" (bajo la decisión actual, D-08 = aceptar deuda, así que estos 2 **no** se
    enrolan en esta fase)
  - Justificación: `PITFALLS.md` advierte explícitamente contra "enrolar `verification/` en
    bloque" — convertiría una limpieza acotada en un yak-shave de alcance no medido (piénsese
    en el precedente ya escrito para mypy: "Enrolamiento mypy completo de `verification/` ...
    no forma parte de HARN-04", `REQUIREMENTS.md § Out of Scope`). El mismo principio se
    extiende por analogía al enrolamiento de pytest en CI para los ~33-35 archivos restantes
    que ningún requisito de esta fase toca.
  - El cierre de esta fase debe **re-declarar por escrito** (no silenciar) que los
    ~33-35 archivos restantes siguen inertes y fuera de alcance de v1.8 — la "declaración
    inerte" de Phase 41 queda satisfecha por esta re-declaración explícita, no por
    enrolamiento total.
  - **Si esto es incorrecto:** si el operador espera que Phase 45 sea el punto de disposición
    TERMINAL para los 40 archivos (no sólo para los que HARN-01/03/04 tocan), el alcance de la
    fase crece sustancialmente más allá de sus 5 criterios de éxito actuales en `ROADMAP.md` y
    eso debería reflejarse explícitamente ahí antes de planificar.

### Consolidación de `ci.yml`

- **D-11:** Todos los edits de `.github/workflows/ci.yml` de esta fase llegan en **un** cambio
  consolidado (criterio de éxito 5 del ROADMAP), no dispersos entre planes — coherente con que
  Phase 41 deliberadamente NO tocó `ci.yml` para dejarle esta consolidación a esta fase
  (`41-ROLLUP.md:209-212`). Verificado: el único cambio a `ci.yml` desde 2026-08-31 es
  `7cc103a` (Phase 42-01, el gate de venue del censo) — Phase 45 es la primera fase del
  milestone en tocarlo de nuevo.

### Checkpoint de resolución post-research (2026-09-01)

45-RESEARCH.md midió que las premisas fácticas de D-01, D-05 y D-08 eran falsas en HEAD (ver
`45-RESEARCH.md § Open Questions`, Q1-Q3). Presentado al operador vía checkpoint; las tres
respuestas resuelven y **enmiendan** los locks originales — el texto original de D-01/D-05/D-08
arriba se conserva sin editar como evidencia de procedencia, estas enmiendas son la fuente de
verdad para planear:

- **D-01 ENMENDADA (Q1):** la clave de dedupe es **`(func, digest)`** — ignora `surface`,
  conserva contenido. Medido: dentro de un proceso cada `(client_function, surface)` se visita
  una sola vez, así que una clave que incluya `surface` no puede colapsar nada (D-01 original
  literal entrega 0 bloques colapsados). `(func, digest)` colapsa el par sync/async idéntico
  (22→11) y sigue escribiendo un bloque nuevo si sync/async difieren, porque el digest cambia —
  el brazo (b) del test de falsificación de D-04 protege exactamente este caso. El criterio de
  éxito 1 del ROADMAP ("deja de escribir un bloque nuevo por pase") se satisface para el caso
  medido (duplicación sync/async dentro de un proceso), no para un hipotético "por pase" literal
  cross-proceso — el planner debe verificar la aritmética 22→11 contra el ledger real, no contra
  22→22 ni 22→8.

- **D-05 ENMENDADA (Q2):** en `tools/check_surface_types.py:47`, dejar las cifras `183 / 330`
  como están (cita histórica byte-idéntica del árbol pre-Phase-37, verificada por `git worktree`
  contra `00ffb2f~1`) y **agregar el pin de commit**: algo como
  `Before Phase 37 (medido en 00ffb2f~1) this gate printed::`. En `:58`, reemplazar el bloque
  congelado por el **valor medido hoy** — `337` definitions scanned (no 336), más los otros dos
  números que también están stale (`186→187`, `442→467`) — y fecharlo (`medido 2026-09-01`) o
  pinnearlo al commit igual que `:47`. Corregir las **tres** cifras de `:58`, no sólo la de
  definitions. El planner DEBE re-correr `tools/check_surface_types.py` para confirmar el valor
  antes de escribirlo — no copiar `337` de este documento sin verificar.

- **D-08 ENMENDADA (Q3):** el rol de canario de `probe_context` se **transfiere de verdad**:
  `verification/test_probe_context_coverage.py` se agrega al allowlist explícito de CI en el
  mismo cambio consolidado de D-11 — un archivo más de los que D-10 enumeraba originalmente.
  Verificar que pasa solo (6/6 medido en research) antes de agregarlo. La decisión escrita de
  HARN-04 debe nombrar esta transferencia explícitamente (no "transferido" sin enrolamiento —
  eso sería renombrar el abandono).

- **D-10 ENMENDADA (consecuencia de Q3):** la lista de archivos a enrolar en el allowlist de CI
  crece en uno: agregar `verification/test_probe_context_coverage.py` a la lista original de D-10.

- **Q4 (no bloqueante, resuelto con la recomendación del research):** la fila de deuda de
  `test_main_matriz_login_fail_uniformity.py` (que sí asevera algo que ningún test enrolado
  asevera hoy — Hallazgo 9) se cierra con ~3 líneas grep-assertables agregadas a un archivo ya
  enrolado en CI, si es viable sin presupuesto adicional significativo; si no es viable, se
  descarta por escrito en el documento de decisión de HARN-04 (nunca queda implícito).

- **Q5 (no bloqueante, resuelto con la recomendación del research):** el gap de gate de mypy
  sobre los drivers `main_*.py` de la raíz (ningún gate de CI apunta ahí, medido en Hallazgo 12
  / Pitfall D) se **declara por escrito** en el cierre de fase con destino nombrado en el
  backlog v1.9 — apuntar mypy a los 5 drivers dentro de esta fase es scope creep no medido, no
  se ejecuta en esta fase.

### Claude's Discretion

- Nombre exacto y estructura del/los archivo(s) de test de falsificación de D-04 (nuevo archivo
  vs. casos agregados a `verification/test_findings_dedupe_by_title.py`).
- Redacción exacta de la decisión escrita y fechada de HARN-04 (D-08) — el contenido mínimo
  está locked arriba (enmendado), el wording no.
- Orden de los planes/waves dentro de la fase (p. ej. HARN-03 mecánico primero, HARN-01 con su
  refactor de fid después, HARN-04 como decisión de checkpoint en cualquier punto).
- Viabilidad exacta del cierre de Q4 (login debt) sin presupuesto adicional — si el planner mide
  que requiere más de ~3 líneas, aplica la salida "descartar por escrito".

### Folded Todos

Ninguno vía `todo.match-phase` (0 matches) — pero ver D-09 (`DRV-MD-SEG-43`, folded desde el
backlog del ROADMAP, no desde `.planning/todos/`).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md:45-63,188-294` — notas de sizing del milestone (orden explícito
  dedupe-después-de-vivo, advertencia HARN-01-no-es-un-kwarg), Phase Details de la 45, y las
  entradas de backlog completas `HARN-DRIFT-33` / cosmético Phase 37 / `HARN-VERIF-01` /
  `DRV-MD-SEG-43` / `SURF-MD-FEEDSUB-43`
- `.planning/REQUIREMENTS.md:29-34,44-67` — texto exacto de HARN-01/03/04, tabla Out of Scope,
  tabla de Traceability
- `.planning/research/PITFALLS.md:349-478` — Pitfalls 9 (dedupe pierde censo), 10 (invariante
  de fid), 12 (HARN-04 scope-creep) — el análisis técnico más profundo disponible para esta
  fase, con mecánica citada por archivo y línea
- `.planning/research/STACK.md:196-225` — tabla de sitios de dedupe medidos por AST, nota sobre
  `.subscription` como precedente de modelo local (no aplica a esta fase, referencia cruzada)
- `.planning/research/FEATURES.md` — categorización de HARN-01..04 (ver tabla ejecutiva al
  inicio del archivo)
- `.planning/phases/41-validaci-n-nyquist-retroactiva-de-v1-7/41-ROLLUP.md:160-276` —
  declaración inerte formal de los 40 locks, ruteo explícito a esta fase, y la nota de que
  Phase 41 deliberadamente no tocó `ci.yml`
- `.planning/phases/44-release-market-data-client-0-7-0/44-CONTEXT.md:71-88` — D-05/D-06
  originales que foldearon `SURF-MD-FEEDSUB-43` en Phase 44 (ya resuelto) y difirieron
  `DRV-MD-SEG-43` a esta fase
- `.planning/phases/43-market-data-client-forma-de-instrument-segment-5-claves-extr/43-DISPOSITION.md § 5`
  — medición completa del gap `DRV-MD-SEG-43` (por qué ningún gate estático lo detecta)
- `verification/findings.py:583-700` — implementación actual de `append_finding` /
  `idempotent_by_title` (primitiva HARN-08/10 de Phase 11, ya wired en ~8 sitios terminal)
- `verification/test_findings_dedupe_by_title.py` — cobertura mockeada existente de la
  primitiva `idempotent_by_title` (no cubre la rama drift, que es el gap de esta fase)
- `verification/test_finding_count_consistency.py` — el invariante P-3 que D-03 no puede
  relajar
- `.github/workflows/ci.yml:22-93` — job `lint`, el allowlist explícito hoy en líneas 81-92
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `verification/findings.py::append_finding(..., idempotent_by_title: bool = False)` — la
  primitiva de dedupe ya existe, ya documentada in-place como Phase 11 HARN-08/10, y ya
  correcta en ~8 sitios terminal (`EXPECTED`/`NO-FIX`, títulos genuinamente idénticos
  cross-run). El gap de esta fase es SOLO la rama drift (título endpoint-scoped, contenido
  variable) — no hace falta escribir una segunda primitiva, hace falta usar la existente con
  el título correcto y en el orden correcto respecto de `_next_fid()`.
- `verification/test_findings_dedupe_by_title.py` — 3 tests parametrizados sobre 4 paquetes
  que ya prueban el contrato genérico de `idempotent_by_title` (colapso, preservación de
  campos originales, comportamiento legacy sin el kwarg). Extender, no reemplazar.

### Established Patterns

- **Ladder de excepción D-09** (`_finding_for_exc` en cada driver): las divergencias de forma
  degradan a finding, nunca a crash. El fix de dedupe debe preservar este contrato — un no-op
  de dedupe sigue siendo un camino sin excepción.
- **Convención `surface-in-title-write-new`** (lockeada, citada en el docstring de
  `_finding_for_exc` en `main_market_data.py:401-409`): el primer sitio que escribe un finding
  para una divergencia de forma es la única fuente — no debe haber doble escritura del mismo
  evento bajo dos títulos.
- **Precedente de gate consolidado** (Phase 32 D-05, Phase 42-01): los steps de CI
  cross-package viven como *step* dentro del job `lint` existente, no como job nuevo.

### Integration Points

- Los 5 drivers `main_*.py` en la raíz del repo (no en `packages/`) — el punto de integración
  para D-01/D-02/D-03/D-04.
- `.github/workflows/ci.yml` job `lint`, líneas 81-92 (allowlist explícito) — punto de
  integración para D-06 y D-10.
- `tools/check_surface_types.py` líneas 47 y 58 — punto de integración para D-05.
- `main_market_data.py:1541-1542` — punto de integración para D-09.
</code_context>

<specifics>
## Specific Ideas

- El test de falsificación de D-04 debe nombrar explícitamente en su docstring qué escenario
  NO debe colapsar (divergencia distinta, mismo endpoint) — no sólo qué escenario SÍ debe
  colapsar, siguiendo la advertencia de `PITFALLS.md`: "Any test named 'dedupe' that only
  asserts the collapse and not the non-collapse."
- La decisión escrita de HARN-04 (D-08) debe vivir en un artefacto de fase nombrado (p. ej.
  `45-HARN-04-DECISION.md` o equivalente dentro del `SUMMARY.md` de su plan) con fecha —
  "decisión escrita y fechada" es literal en el criterio de éxito 3 del ROADMAP.
</specifics>

<deferred>
## Deferred Ideas

- **Reparación completa de `verification/test_matriz_sweep_snapshot.py` /
  `test_main_matriz_login_fail_uniformity.py`** — diferida por D-08 (aceptar como deuda), no
  ejecutada en esta fase.
- **Disposición individual de los ~33-35 archivos `verification/` restantes** que hoy no corren
  en CI (fuera de los tocados por D-10) — permanece formalmente fuera de alcance de v1.8; sería
  candidato a un milestone propio si se decide perseguir cobertura completa de CI sobre todo el
  directorio.
- **Enrolamiento mypy completo de `verification/`** — ya excluido explícitamente en
  `REQUIREMENTS.md § Out of Scope`, no forma parte de HARN-04.

### Reviewed Todos (not folded)

Ninguno — `todo.match-phase 45` devolvió 0 matches.
</deferred>
