# Phase 40: Releases breaking coordinados - Context

**Gathered:** 2026-08-30 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Los paquetes cuya superficie pública cambió durante v1.7 (Phases 35-39) quedan publicados por el
pipeline de tags existente, cada uno con bump **breaking**, callout de changelog **primero** en
el README y una tabla de migración vieja→nueva ejecutable por el consumidor. Ninguna operación
irreversible (merge del PR, push de tags) ocurre sin aprobación humana explícita — dos
checkpoints independientes, nunca colapsados ni auto-aprobados pese a `auto_advance: true` +
`mode: yolo` activos en `.planning/config.json`. Requisito: `PUB-NOBJ-01`. Depende de Phase 39
(completa).

**Fuera de alcance:** cualquier cambio funcional nuevo a los paquetes (el código ya está
construido y verificado en vivo por las Fases 35-39); editar `.github/workflows/release.yml` o
`.github/workflows/ci.yml`; versionado repo-wide (`v1.1`…`v1.6` son tags de milestone, no de
paquete, y no se tocan).
</domain>

<decisions>
## Implementation Decisions

### Alcance del bump

- **D-01:** Se bumpean **exactamente tres** paquetes confirmados por evidencia de v1.7:
  `market-data-client` **0.5.0 → 0.6.0** (Phase 36 — `market_data` dict→Null Object tipado),
  `iol-client` **0.3.0 → 0.4.0** (Phase 38 — `Cotizacion.puntas`/`Titulo.puntas` pierden
  `| None`), `matriz-client` **0.2.0 → 0.3.0** (Phase 37 — `AccountReport.portfolio` retipado +
  dos campos `dict[str, Any]` → modelos tipados + fix de envelope-unwrap). `ambito-financiero-client`
  y `wallets-client` NO se tocan — Phase 38 (NOBJ-AUD-01) midió 0 violaciones en ambos.

- **D-02 [checkpoint explícito, no resuelto en discuss — corregido tras research]:**
  `higyrus-client` carga una ruptura **ya shippeada en código pero nunca publicada**:
  `get_health()` devuelve `Health` tipado desde Phase 31 (v1.5, commit `bf04b2f`),
  `pyproject.toml` sigue en `0.2.0`, y el README todavía dice "el bump lo hace la Phase 34" —
  afirmación que Phase 34 mismo invalidó (D-01 de `34-CONTEXT.md` excluyó higyrus explícitamente;
  `34-01-SUMMARY.md` clasificó el diff como "aditivo", no ameritando bump). Ningún artefacto de
  planning reasigna esta deuda a ninguna fase. Consistente con el precedente del proyecto
  (D-08/D-18: nunca resolver en silencio una decisión scope-adjacent), esto **no se decide acá**
  — se presenta como pregunta explícita, pero **NO** en el checkpoint pre-merge (D-07/(a)) como
  se pensó originalmente: la fase de research (`40-RESEARCH.md`, OQ-1) encontró que resolver esto
  *después* del bump/lock/push rompería D-10 (un "aprobar" ahí exigiría un **segundo** `uv lock`
  para el cuarto paquete). **Corrección:** este checkpoint se **hoistea a un gate bloqueante al
  inicio mismo del primer plan** (antes de tocar cualquier `pyproject.toml` o correr `uv lock`),
  para que el conjunto final de paquetes a bumpear (3 o 4) y el único `uv lock` de D-10 se
  calculen correctamente desde el arranque — no como un ítem más del checkpoint (a).
  - Si el operador aprueba foldear: higyrus se suma como **cuarto** paquete bumpeado
    (`0.2.0 → 0.3.0`), con su sección de changelog reescrita al formato `## Unreleased —
    BREAKING` (reemplazando la sección obsoleta `### v0.3.0 — sin publicar todavía`), y entra en
    el mismo `uv lock` único de D-10.
  - Si el operador declina: la sección del README se corrige de todos modos (deja de citar
    "Phase 34" como ejecutor, ya shippeada sin este cambio) y se reasigna a un destino concreto
    o se marca explícitamente "pendiente, sin fase asignada" — no se re-difiere en silencio una
    tercera vez.

### Changelog de `matriz-client` — se escribe desde cero

- **D-03:** `packages/matriz-client/README.md` no tiene ninguna sección de Changelog hoy (a
  diferencia de iol-client/market-data-client, que ya tienen `## Unreleased — BREAKING` escrito
  por sus propias fases). Esta fase debe **autoría completa** de esa sección, cubriendo lo medido
  en `37-01-SUMMARY.md`…`37-05-SUMMARY.md`:
  - `AccountReport.portfolio`: `dict[str, Any]` (vía mapping) → `float | None` (hoja escalar).
  - `InstrumentDetail.tickPriceRanges`: `dict[str, Any]` → `dict[str, TickPriceRange]`.
  - `DetailedPosition.report`: `dict[str, Any]` → `dict[str, dict[str, InstrumentPositionReport]]`.
  - `AccountReport.detailedAccountReports`: `dict[str, Any]` → `dict[str, DetailedAccountReport]`.
  - Fix de envelope-unwrap en `get_detailed_positions`/`get_account_report` (antes decodificaban
    desde el nivel de anidamiento equivocado, devolviendo modelos con todos los campos en su
    default) — documentar como corrección de comportamiento, no solo de tipo.
  - Las **6 alias properties** nuevas (`bids`/`offers`/`last`/`settlement`/`close`/
    `open_interest`) van documentadas aparte como **aditivas, no breaking** — no entran en la
    tabla de migración.

- **D-04:** `matriz-client` es el único de los 6 paquetes sin `__version__` en `__init__.py`.
  Verificado: `release.yml:47` lee la versión **solo** de `pyproject.toml` (nunca de
  `__init__.py`), y matriz ya publicó dos releases (`v0.1.1`, `v0.2.0`) sin `__version__` sin
  incidente. **No es un requisito** para pasar el pipeline — agregarlo es discrecional, solo por
  consistencia con la convención de Exports documentada en `CLAUDE.md`.

### Vehículo de PR — branch nueva, no reuse

- **D-05:** A diferencia de Phase 34 (que actualizó el PR #12 existente sobre una branch de
  milestone ya viva), **no existe ninguna branch ni PR de v1.7** hoy: `main` local está 180
  commits adelante de `origin/main` (HEAD remoto = merge de PR #14, cierre de v1.6), sin PR
  abierto (`gh pr list` vacío) y sin branch remota de v1.7. Esta fase crea una branch nueva —
  `milestone/v1.7-nobj-null-objects` (seleccionado, sigue el patrón `milestone/v1.5-mutations`
  ya usado) — pushea los 180 commits pendientes, y abre un PR nuevo a `main` cubriendo las Fases
  35-40 y las versiones bumpeadas.

- **D-06:** Conteo de CI verde = **exactamente 15 checks** (12 del matrix de test — 6 paquetes ×
  py3.12/py3.13 — más 3 jobs no-matrix: `lint`, `pre-commit`, `typecheck`), mismo cálculo que
  Phase 34 sobre el mismo `ci.yml` sin editar desde entonces. El criterio 2 del ROADMAP
  ("6 paquetes × py3.12/py3.13 más los 4 gates") se lee como 4 **job definitions** (`lint`,
  `pre-commit`, `typecheck`, `test` — este último fan-out en 12), no 4 jobs adicionales sobre el
  matrix.

### Ops irreversibles — dos gates, no tres (más un gate de alcance previo)

- **D-07 [corregido tras research]:** Exactamente **dos checkpoints humanos bloqueantes** para
  las operaciones irreversibles, implementados como dos `PLAN.md` separados (`autonomous: false`
  cada uno), espejando literalmente el split `34-02-PLAN.md`/`34-03-PLAN.md`: (a) antes de
  mergear el PR, (b) antes de pushear los tags. Nunca colapsados, nunca auto-aprobados pese a
  `auto_advance: true` + `mode: yolo` (confirmados activos en `.planning/config.json`). **Las
  preguntas D-02 (higyrus) y D-12 (market_id/active) NO viven en el checkpoint (a)** — la
  investigación (`40-RESEARCH.md` OQ-1) encontró que resolverlas ahí, después del bump/lock/push,
  rompe D-10 (exigiría un segundo `uv lock`) y enrojecería tests ya verdes. Ambas se resuelven en
  un **gate de alcance independiente, previo, al inicio del primer plan** (`checkpoint:decision`
  bloqueante antes de tocar cualquier `pyproject.toml`) — decisión del operador confirmada en
  discuss-phase (2026-08-30): hoistear, no dejarlas en el checkpoint (a). Este gate de alcance no
  cuenta contra el "exactamente dos" de operaciones irreversibles del criterio 4 del ROADMAP —
  no mergea ni taggea nada, solo fija el conjunto de paquetes/cambios antes de que el resto de la
  fase corra.

- **D-08:** El merge usa **merge commit real** (`gh pr merge --merge`) — nunca squash, nunca
  rebase.

- **D-09:** Cada tag es una **annotated tag** creada sobre el SHA del merge commit **re-resuelto
  en vivo post-merge** (no la branch HEAD pre-merge). Una sola aprobación de checkpoint (b) cubre
  el push de **todos** los tags de esta ronda (3 o 4, según D-02) en una misma operación.

- **D-10:** `uv.lock` se refresca **exactamente una vez**, después de bumpear todos los
  `pyproject.toml` de la ronda, antes de abrir el PR.

- **D-11:** Verificación post-publicación: instalar desde el wheel público de cada paquete
  publicado y ejercer una cadena profunda ya existente en el paquete instalado (criterio 3 del
  ROADMAP).

### Divergencia sin corregir de `market-data-client` (`market_id`/`active`)

- **D-12 [checkpoint explícito, no resuelto en discuss — corregido tras research]:**
  `36-DEFERRED-market-data-leaves.md` documenta una divergencia medida y no corregida
  (`market_id`/`active` llegan `null` sobre campos no-`Optional`, `strict_decode` levanta) y
  nombra explícitamente "el bump coordinado de Phase 40" como el checkpoint natural para
  resolverla. Pero el alcance de esta fase (`PUB-NOBJ-01`) es **publicar rupturas ya decididas**,
  no decidir rupturas nuevas — Phase 39 no tocó ni resolvió este ítem. No se resuelve en silencio
  en ninguna dirección — pero, igual que D-02, **no vive en el checkpoint (a)**: aprobar el
  ensanche ahí (después del bump/lock/push) dejaría ≥6 aserciones ya verdes de
  `packages/market-data-client/tests/test_snapshot_no_data_row.py` rojas sin ruta de vuelta
  limpia. Se resuelve en el **mismo gate de alcance previo que D-02** (inicio del primer plan,
  antes de tocar `pyproject.toml`/`uv lock`).
  - Si el operador aprueba ensanchar los campos ahora: se suma como una fila más a la tabla de
    migración de `market-data-client`, dentro del mismo bump breaking, y el plan incluye
    actualizar las ≥6 aserciones de `test_snapshot_no_data_row.py` (sync + async) como parte del
    mismo ciclo — no una regresión post-hoc.
  - Si declina: la nota "espera checkpoint del operador" del README se corrige para no seguir
    apuntando a "Phase 40" como destino futuro (esta fase deja de ser un destino vigente en
    cuanto se publique) — se reasigna a una fase concreta o se marca "pendiente, sin fase
    asignada".

### Claude's Discretion

- Wording exacto de la nueva sección de changelog de `matriz-client` (seguir la voz/formato ya
  establecido por iol-client/market-data-client: español, tabla antes/después, línea líder en
  negrita).
- Título y body exactos del PR nuevo.
- Si agregar o no `__version__` a `matriz_client/__init__.py` (discrecional per D-04).
- Agrupamiento y orden de commits dentro de la fase.

### Folded Todos

Ninguno — `todo.match-phase 40` devolvió 0 matches.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` § Phase 40 — 4 criterios de éxito + `Requirements: PUB-NOBJ-01`
- `.planning/REQUIREMENTS.md` (línea 38) — texto completo de `PUB-NOBJ-01`
- `.planning/milestones/v1.6-phases/34-releases-por-paquete/34-CONTEXT.md` — precedente directo:
  D-08/D-09/D-10/D-11 (dos checkpoints, merge commit real, tag sobre SHA de merge, uv.lock único)
- `.planning/milestones/v1.6-phases/34-releases-por-paquete/34-02-PLAN.md` y `34-03-PLAN.md` —
  template literal de los dos plans de checkpoint bloqueante
- `.planning/milestones/v1.6-phases/34-releases-por-paquete/34-01-SUMMARY.md` — deviation 1,
  clasificación del diff aditivo de higyrus como no-bump-worthy (contexto de D-02)
- `packages/iol-client/README.md` — sección `## Unreleased — BREAKING` ya escrita (Phase 38),
  usar como referencia de formato para D-03
- `packages/market-data-client/README.md` — sección `## Unreleased — BREAKING` ya escrita (Phase
  36) + nota de divergencia `market_id`/`active` sin corregir
- `packages/matriz-client/README.md` — sin sección de Changelog; a crear desde cero (D-03)
- `.planning/phases/37-matriz-client-dicts-residuales-tipados-alias/37-01-SUMMARY.md` a
  `37-05-SUMMARY.md` — fuente de los cambios exactos de matriz para D-03
- `.planning/phases/36-market-data-client-market-data-tipado-revocaci-n-de-la-fase-/36-DEFERRED-market-data-leaves.md`
  — detalle de la divergencia `market_id`/`active` (D-12)
- `.planning/phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-CENSUS.md` — censo de 0
  violaciones en higyrus/ámbito/wallets
- `packages/higyrus-client/README.md` — sección obsoleta `### v0.3.0 — sin publicar todavía`
  citando "Phase 34" (D-02)
- `packages/higyrus-client/src/higyrus_client/client.py:450` — `get_health()` ya devuelve
  `Health` en código de producción
- `.github/workflows/release.yml` — regex de tag, gate de version-match (lee solo
  `pyproject.toml`) — **no editar**
- `.github/workflows/ci.yml` — 4 job definitions / 15 checks totales — **no editar**
- `.planning/config.json` — `auto_advance: true`, `mode: yolo`, `git.branching_strategy: "none"`
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`release.yml` genérico** — soporta cualquier `<pkg>-client-vX.Y.Z` sin edits; quinta vez que
  se reusa sin tocar el archivo.
- **Formato `## Unreleased — BREAKING`** — ya establecido en iol-client y market-data-client;
  matriz-client debe seguir el mismo formato pero escribirlo desde cero.
- **`34-02-PLAN.md` / `34-03-PLAN.md`** — template literal para los dos plans de checkpoint
  bloqueante (`autonomous: false`, `user_setup` con `gh auth status`,
  `<task type="checkpoint:decision" gate="blocking">`).

### Established Patterns

- Versionado per-package, sin versión monorepo.
- Alineación `pyproject.version` == `uv.lock` workspace member, hard-enforced por `release.yml`
  (NO exige `__version__` en `__init__.py` — solo `market-data-client` tiene un test que ata
  ambos, deuda pre-existente y aceptada, no un requisito de CI).
- `.planning/` trackeado y mergeado a `main` en cada release.
- Merge commit real + tag sobre el SHA del merge commit.

### Integration Points

- 3 o 4 tags (según D-02) sobre el **mismo** merge commit → cada uno dispara su propia corrida de
  `release.yml` → 3-4 GitHub Releases independientes.
- `ci.yml` `matrix.package` × `python-version` = 6 × 2 = 12 jobs de test + 3 jobs no-matrix = 15
  checks totales.
- Branch nueva → PR nuevo → 15 checks → checkpoint (a) [incluye D-02 y D-12] → merge real → tags
  sobre SHA re-resuelto → checkpoint (b) → push tags → N corridas de `release.yml` → N releases →
  verificación post-publicación instalando desde wheel público.
</code_context>

<specifics>
## Specific Ideas

- Las filas exactas de la tabla de migración de `matriz-client` deben sintetizarse a partir de
  `37-01-SUMMARY.md`…`37-05-SUMMARY.md` (contenido locked por D-03, wording a discreción).
- Los ítems D-02 (higyrus) y D-12 (market_id/active) son decisiones reales que deben presentarse
  explícitamente al operador en el checkpoint (a) — ningún agente las resuelve en silencio,
  consistente con el precedente D-08/D-18 del proyecto de nunca auto-resolver decisiones
  scope-adjacent.
</specifics>

<deferred>
## Deferred Ideas

- Cualquier corrección funcional a `market_id`/`active` de `market-data-client` más allá de lo
  que el operador apruebe en el checkpoint — si se declina, se convierte en una fase futura
  correctamente nombrada, no en un carry-forward silencioso (D-12).
- Agregar `__version__` a `matriz_client/__init__.py` — discrecional, no requerido (D-04).
- El bump de `higyrus-client` — si el operador declina foldearlo, necesita una reasignación real,
  no un "en algún momento" tácito (D-02).

### Reviewed Todos (not folded)

Ninguno — `todo.match-phase 40` devolvió 0 matches.
</deferred>
