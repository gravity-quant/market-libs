# Phase 41: Validación Nyquist retroactiva de v1.7 - Context

**Gathered:** 2026-08-31 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Auditar retroactivamente las cinco fases de v1.7 (35, 36, 37, 38, 39) que nunca corrieron
`/gsd-validate-phase` — cada una quedó con `status: draft` / `nyquist_compliant: false` en su
`{N}-VALIDATION.md`. El resultado es una disposición explícita de 3 vías (`VERIFIED-NOW` /
`VERIFIED-HISTORICALLY` / `NOT-VERIFIABLE-RETROACTIVELY`) por criterio auditado, producida contra
el árbol de v1.7 **congelado** — sin tocar una sola línea de fuente de v1.8 hasta que las cinco
disposiciones queden escritas. Fuera de alcance: `NYQUIST-32-33` (mismo gap, milestone anterior;
permanece en `REQUIREMENTS.md § Out of Scope` sin absorber), y cualquier fix de código motivado
por lo que la auditoría encuentre (eso, si aplica, es trabajo de otra fase).
</domain>

<decisions>
## Implementation Decisions

### Artifact shape & write target

- **D-01:** El resultado se escribe **in place** en los 5 `{N}-VALIDATION.md` existentes, archivados
  bajo `.planning/milestones/v1.7-phases/{35,36,37,38,39}-*/` — se les añade una sección fechada
  `## Validation Audit {date}`, no se crean cinco archivos `41-*` nuevos ni un documento
  consolidado como fuente de verdad. Un rollup consolidado, si se produce, es un índice secundario
  bajo `.planning/phases/41-*/`, no el artefacto autoritativo.
- **D-02:** El SHA declarado en cada artefacto es el commit del tag `v1.7`
  (`37a83fe693a303a551f4374f48fe6fc5521804f7`), acompañado de la prueba de que el árbol auditado
  sigue intacto: `git diff v1.7 HEAD -- . ':(exclude).planning'` está vacío (verificado en esta
  sesión — los tres commits desde el tag tocan sólo `.planning/`). Si por algún motivo se declara
  también el HEAD de la sesión de auditoría, se declaran **ambos**, nunca sólo HEAD sin la prueba
  de identidad del árbol.

### Unit of disposition (denominador del criterio 2)

- **D-03:** El denominador de "cero filas sin disponer" (criterio 2) son las filas de la **Per-Task
  Verification Map** más las **Manual-Only Verifications** de cada `{N}-VALIDATION.md` — medido 51
  filas totales entre las 5 fases — **no** los 25 criterios de éxito ya cerrados en v1.7
  `ROADMAP.md`, y no una unión de ambos.
- **D-04:** Se espera que `VERIFIED-NOW` domine sobre `VERIFIED-HISTORICALLY`: los 15 archivos de
  test citados en los 4 mapas poblados (36-39) ya existen en disco y son re-ejecutables — las
  celdas `⬜`/`❌` son bookkeeping stale de plan-time, no gaps reales. Cada fila `VERIFIED-NOW` debe
  citar el comando **y su output real de esta sesión** — nunca flippear una celda sin re-ejecutar.
  `VERIFIED-HISTORICALLY` queda reservado para evidencia de artefacto único e irrepetible (p.ej. el
  doc-review de `38-CENSUS.md`). `NOT-VERIFIABLE-RETROACTIVELY` para filas que dependen de red en
  vivo o de un checkpoint humano que no se puede re-derivar (p.ej. las 4 filas manual-only de
  Phase 39).
- **D-05:** Phase 35 es una excepción estructural: su mapa tiene una única fila placeholder
  (`"(filled by planner)"`). Antes de disponer, sus ~14 bloques `<verify><automated>` reales deben
  reconstruirse desde `35-01..05-PLAN.md` y disponerse individualmente — nunca disponer la fila
  placeholder como si fuera la unidad completa (eso certificaría "1/1, 100%" sin decir nada).

### Cómo se invoca `/gsd-validate-phase`

- **D-06:** El skill se invoca 5 veces (una por fase 35-39), con dos desviaciones obligatorias del
  camino stock:
  (a) en el gate de "fix gaps" **nunca** se toma la rama que spawnea `gsd-nyquist-auditor` para
  escribir tests nuevos — la auditoría es de lectura/disposición, no de reparación;
  (b) la resolución de requirements/roadmap apunta explícitamente a
  `.planning/milestones/v1.7-REQUIREMENTS.md` y `.planning/milestones/v1.7-ROADMAP.md` — **nunca**
  a los archivos raíz (`REQUIREMENTS.md`/`ROADMAP.md`), que hoy contienen el roster de v1.8
  (`NYQ-01`, `LIVE-01`, etc.) y no resuelven contra los IDs de v1.7 (`NOBJ-01`, `NOBJ-MD-01`, etc.)
  que las fases 35-39 referencian.
- **D-07:** Cada fila dispuesta como `VERIFIED-NOW`/`VERIFIED-HISTORICALLY` lleva una **cuarta
  columna** nombrando su superficie de enforcement real en CI (job + línea del `ci.yml`, o
  `NOT ENFORCED` si no corre en CI) — así es como el criterio 4 se satisface también para locks
  **pre-existentes**, no sólo para los que el auditor pudiera generar. (Medido: 52 archivos calzan
  `verification/test_*.py`; sólo 12 están en el allowlist explícito de `ci.yml`.)

### Front-matter semantics & mechanical-closure risk

- **D-08:** "Lock" en el criterio 4 significa un **archivo de test ejecutable nuevo** que el
  auditor escribe a disco (el sentido ya establecido en el repo, p.ej. "AST lock" en
  `39-VALIDATION.md`) — no el propio `{N}-VALIDATION.md` ni el flag de front-matter. El conteo
  esperado es **cero**: el criterio 4 es una cláusula de contingencia, no un entregable esperado.
  Si de todas formas se escribe uno, queda declarado inerte por escrito con su enrolamiento en CI
  ruteado explícitamente a la Phase 45 (precondición ya registrada en `REQUIREMENTS.md`).
- **D-09:** El estado final esperado en front-matter es `status: draft → validated` en los 5, pero
  `nyquist_compliant` se queda en **`false`** en efectivamente los 5 (estado PARTIAL, no
  compliant) — Phase 39 sola tiene 4 filas manual-only no reproducibles (corridas en vivo contra
  red real). Ningún `nyquist_compliant` pasa a `true` salvo donde la disposición sea `VERIFIED-NOW`
  re-ejecutada en esta sesión (y aun así, sólo si **todas** las filas de esa fase cierran limpias,
  cosa que no se espera para ninguna de las 5).
- **D-10 (riesgo a vigilar — no una decisión de implementación, una restricción de calidad):**
  El riesgo principal es "staleness laundering" — flippear mecánicamente las ~45 casillas `⬜`
  stale a `✅` en un commit sin comando/output re-ejecutado. Contramedida: toda fila `VERIFIED-NOW`
  cita comando + output real de esta sesión. Además, la propia Phase 41 recibirá su propio
  `41-VALIDATION.md` auto-sembrado (`nyquist_validation: true` en `config.json`) — ese tampoco se
  flippea mecánicamente; se disponen sus filas con la misma vara que las cinco que audita.

### Claude's Discretion

- Formato exacto de la sección `## Validation Audit {date}` dentro de cada VALIDATION.md (tabla vs.
  prosa) — mientras cumpla D-01/D-07/D-09, queda a discreción del planner/executor.
- Si producir o no un rollup consolidado bajo `.planning/phases/41-*/` como índice de lectura
  rápida — no es requisito, es una conveniencia opcional (D-01).

### Folded Todos

Ninguno — `todo.match-phase 41` devolvió `todo_count: 0`.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` § Phase 41 (líneas 66-78) — los 5 criterios de éxito, ya lockeados, no se
  rediseñan.
- `.planning/REQUIREMENTS.md` (NYQ-01, tabla de traceability, precondición cross-fase líneas 79-84).
- `.planning/milestones/v1.7-phases/{35,36,37,38,39}-*/{N}-VALIDATION.md` — los 5 artefactos que se
  actualizan in-place. Rutas exactas:
  - `.planning/milestones/v1.7-phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-VALIDATION.md`
  - `.planning/milestones/v1.7-phases/36-market-data-client-market-data-tipado-revocaci-n-de-la-fase-/36-VALIDATION.md`
  - `.planning/milestones/v1.7-phases/37-matriz-client-dicts-residuales-tipados-alias/37-VALIDATION.md`
  - `.planning/milestones/v1.7-phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-VALIDATION.md`
  - `.planning/milestones/v1.7-phases/39-verificaci-n-en-vivo-del-encadenamiento-profundo/39-VALIDATION.md`
- `.planning/milestones/v1.7-phases/{N}-*/{N}-VERIFICATION.md` y `{N}-REVIEW.md` (por las 5 fases)
  — evidencia histórica de qué se verificó realmente, independiente del auto-reporte del propio
  VALIDATION.md.
- `.planning/milestones/v1.7-phases/35-.../{35-01..05}-PLAN.md` — fuente para reconstruir las
  filas reales de Phase 35 (D-05).
- `.planning/milestones/v1.7-REQUIREMENTS.md` y `.planning/milestones/v1.7-ROADMAP.md` — roster de
  requirement IDs correcto para resolver contra las fases 35-39 (D-06b); **no** los archivos raíz
  homónimos, que ya son de v1.8.
- `~/.claude/gsd-core/workflows/validate-phase.md` — comportamiento stock del skill; §4 (gate de
  fix-gaps) es la rama que D-06a excluye.
- `~/.claude/agents/gsd-nyquist-auditor.md` — agente que NO se debe spawnear en modo fix (D-06a).
- `.github/workflows/ci.yml` líneas 79-92 (allowlist explícito de `verification/` en el job
  `lint`) y líneas 52-67 (los 3 gates `tools/`) — fuente para la 4ª columna de enforcement (D-07).
- `.planning/config.json` (`workflow.nyquist_validation: true`) — por qué Phase 41 recibe su
  propio `41-VALIDATION.md` auto-sembrado (D-10).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- Los 5 `{N}-VALIDATION.md` ya tienen la infraestructura de tabla (`Per-Task Verification Map`,
  `Manual-Only Verifications`) — la auditoría llena/corrige columnas existentes, no inventa un
  formato nuevo.
- Los 15+ archivos de test citados en los mapas de 36-39 existen en disco y son re-ejecutables tal
  cual (verificado por el analyzer). No hace falta escribir tests nuevos para dar veredicto
  `VERIFIED-NOW` en la mayoría de las filas.

### Established Patterns

- El lifecycle `status: draft → validated`, `nyquist_compliant: false → true`, está documentado
  inline en el propio front-matter de 35/36/37/38 (comentario de 2 líneas citando
  `audit-milestone §5.5`) — PARTIAL (`validated` + `nyquist_compliant: false`) es un estado real y
  esperado, no un fallo del proceso.
- Precedente de disposición de 3 vías ya usado en el proyecto: Phase 33 (`COULD-NOT-DECIDE` para
  ítems bloqueados por política), censo de Phase 39 (`39-CENSUS.md`, provenance por celda) — Phase
  41 sigue el mismo espíritu (nunca "limpio" por defecto, siempre evidencia nombrada).

### Integration Points

- Precondición cross-fase ya registrada en `REQUIREMENTS.md`: "Locks generados por el auditor,
  pendientes de enrolar en CI" — producida en Phase 41 (criterio 4), consumida por Phase 45
  (criterio 5, edit consolidado de `ci.yml`).
- El árbol congelado de v1.7 (precondición de entrada del milestone) debe seguir intacto hasta que
  las 5 disposiciones queden escritas — cualquier commit de fuente de v1.8 antes de eso invalida la
  atribución (Phase 42 es la siguiente en tocar fuente).
</code_context>

<specifics>
## Specific Ideas

Ninguna referencia particular más allá de las decisiones ya capturadas arriba — el analyzer citó
líneas/archivos exactos para cada assumption, ya incorporados como evidencia en `<decisions>`.
</specifics>

<deferred>
## Deferred Ideas

- Reparar o regenerar tests que las celdas `⬜`/`❌` marcan como faltantes cuando en realidad ya
  existen (D-04) — no es trabajo de Phase 41, sólo se corrige el bookkeeping stale del mapa.
- Cualquier fix de código motivado por lo que la auditoría revele — fuera de esta fase por
  definición (Phase 41 no toca fuente).

### Reviewed Todos (not folded)

Ninguno — `todo.match-phase 41` devolvió `todo_count: 0`, no hubo candidatos que revisar.

None — el análisis se mantuvo dentro del alcance de la fase.
</deferred>
