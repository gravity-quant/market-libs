# Phase 34: Releases por paquete - Context

**Gathered:** 2026-08-27 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Publicar por el pipeline de tags existente los **dos paquetes cuya superficie pública cambió**
en el milestone v1.6: `iol-client` (dict→modelo, Phase 30) y `market-data-client` (4 endpoints
de ops tipados en Phase 31 + 3 disposiciones `fix-shape-now` lockeadas en el plan 33-07). El
código ya está construido, verificado en vivo y fixeado in-cycle por las Fases 29-33; esta fase
cubre únicamente **release prep + publish**: completar el changelog de `market-data-client`,
bump de versión en ambos paquetes, refresh de `uv.lock`, actualizar el PR existente, confirmar
CI verde, y —con doble go/no-go explícito del operator— mergear y taggear los dos paquetes.

**Fuera de alcance:** cualquier cambio funcional a los paquetes; re-publicar `higyrus-client`,
`ambito-financiero-client`, `matriz-client` o `wallets-client` (sin cambios de superficie);
editar `.github/workflows/release.yml` o `.github/workflows/ci.yml`; versionado repo-wide.
</domain>

<decisions>
## Implementation Decisions

### Alcance del bump (locked por evidencia, sin corrección)

- **D-01:** Se bumpean **exactamente dos** paquetes: `iol-client` **0.2.0 → 0.3.0** y
  `market-data-client` **0.4.0 → 0.5.0**. Ningún otro paquete se toca — verificado en vivo
  (`packages/iol-client/pyproject.toml:3` = `0.2.0`, `packages/market-data-client/pyproject.toml:3`
  = `0.4.0`, ninguno bumpeado todavía). Precomputado en `33-07-SUMMARY.md:183-186`
  (dispositions `SC-1`/`SC-2`/`SC-3`, todas `fix-shape-now`, todas `market-data-client`) y en
  `ROADMAP.md` § Phase 34 criterio 1.

- **D-02:** La rama msgspec del criterio 2 (README declarando pérdida de closure puro-Python) **no
  aplica** — `29-DLOCK-MSGSPEC.md` está firmado `decision: no-go-stdlib-only`; msgspec nunca se
  instaló en el workspace (cero hits en `uv.lock` o cualquier `pyproject.toml`).

### Changelog de `market-data-client` — gap real a cerrar antes de bumpear

- **D-03:** `packages/iol-client/README.md` ya tiene su sección `### v0.3.0` completa (escrita en
  Phase 30, commit history confirma), con el callout dict→modelo, el flip de truthiness y
  `to_dict()`. **No necesita cambios.**

- **D-04:** `packages/market-data-client/README.md` tiene una sección `### v0.5.0 — sin publicar
  todavía` (escrita en Phase 31, commit `bf04b2f`) que documenta **sólo** los 4 endpoints de ops
  (`get_health`, `get_health_feed`, `add_holidays`, `delete_holiday`). **Le faltan los 3 breaks
  lockeados por 33-07** (SC-1 `preview_calendar_config` cambia de retorno a un modelo de preview
  dedicado; SC-2 `MarketDataSnapshot.entries`/`.market_data`/`.staleness_seconds` pasan a `| None`;
  SC-3 `Symbol.created_at`/`.updated_at` pasan a `str | None`). **La Task de prep debe ampliar
  esta sección con los 3 breaks antes de bumpear la versión** — sin esto, el criterio 1 (callout
  de changelog) queda incumplido para el paquete. Al bumpear, el título de la sección pasa de
  "sin publicar todavía" a la fecha real de publicación.

### Vehículo de PR (decidido por el operator)

- **D-05:** **Actualizar el PR #12 existente**, no cerrarlo ni abrir uno nuevo. PR #12
  (`milestone/v1.5-mutations` → `main`, `MERGEABLE`, abierto 2026-08-26) quedó desactualizado:
  local está 44 commits adelante de `origin/milestone/v1.5-mutations` (todo Phase 33 nunca se
  pusheó). El flujo: pushear los 44 commits pendientes a origin, luego retitular/actualizar el
  body del PR para cubrir fases 29-34 y ambas versiones. Consistente con el precedente D-08/D-09
  de Phase 28 (una branch de milestone, un solo PR → `main`, `.planning/` incluido).

- **D-06:** Mantener los artefactos `.planning/` en el PR — mismo criterio que D-09 de Phase 28.

- **D-07:** No rebasear ni mergear `origin/main` en la branch — el patrón D-10 de Phase 28
  (divergencia cosmética vía merge-commits ya mergeados) se repite: `HEAD..main` son sólo los 4
  merge-commits de PRs #8/#9/#10/#11 ya contenidos en la historia de la branch.

### Ops irreversibles — dos gates, no tres (decidido por el operator)

- **D-08:** **Exactamente dos checkpoints humanos bloqueantes**, ambos explícitos e
  independientes, nunca colapsados: (a) antes de **mergear el PR**, y (b) antes de **pushear los
  tags**. El gate (b) cubre el push de **ambos** tags (`iol-client-v0.3.0` y
  `market-data-client-v0.5.0`) en una misma operación aprobada — no un gate separado por paquete.
  Hereda D-18 de Phase 28 literalmente (dos *tipos* de operación irreversible, no N gates por N
  tags).

- **D-09:** El PR se mergea con **merge commit real** (`gh pr merge --merge`) — nunca squash, nunca
  rebase — y ambos tags se pushean sobre ese mismo merge commit. Hereda D-11 de Phase 28: squashear
  orfanaría los SHAs que decenas de SUMMARY de fases 29-33 cross-referencian.

- **D-10:** Cada tag es una **annotated tag** creada sobre el SHA del merge commit (no sobre branch
  HEAD), para que el version-match gate de `release.yml` corra contra el árbol mergeado. Patrón
  idéntico a `28-03-PLAN.md`.

### `uv.lock` — refresh único

- **D-11:** `uv.lock` se refresca **exactamente una vez**, después de bumpear ambos `pyproject.toml`,
  antes de abrir/actualizar el PR — un solo `uv lock` cubre los dos workspace members. Ningún otro
  archivo de `.github/workflows/` se toca (`release.yml` es genérico por regex de tag; `ci.yml` ya
  lista los 6 paquetes en su matrix desde antes de esta fase).

### Claude's Discretion

- Wording exacto de los 3 breaks nuevos en la sección `### v0.5.0` de `market-data-client/README.md`
  (seguir el formato ya establecido: español, línea líder en negrita nombrando la clase de bump,
  tabla antes/después donde aplique).
- Título y body exactos del PR #12 actualizado.
- Si crear o no archivos de memory in-repo (`.claude/projects/.../memory/<pkg>-releases.md`) para
  `iol-client` y `market-data-client`, siguiendo el patrón D-04-sitio-5 de Phase 28 — no está
  exigido por ningún criterio de ROADMAP, es discrecional/buena práctica.
- Agrupamiento y orden de commits dentro de la fase.

### Folded Todos

Ninguno — `todo.match-phase 34` devolvió 0 matches.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` § Phase 34 — 4 success criteria + la nota de ampliación 2026-08-27 que
  suma `market-data-client` al bump set
- `.planning/REQUIREMENTS.md` — `PUB-TYP-01` (línea 30)
- `.planning/phases/33-verificaci-n-en-vivo-en-modo-estricto-fixes/33-07-SUMMARY.md` —
  líneas 178-198, `## Shape-change dispositions (locked)`: las 3 dispositions `fix-shape-now`
  (SC-1/SC-2/SC-3) que amplían el bump set, y la nota "La versión no se bumpeó acá" (líneas 445-447)
- `.planning/phases/29-decoder-observable/29-DLOCK-MSGSPEC.md` — decisión firmada
  `no-go-stdlib-only`; msgspec nunca entró como runtime dep
- `.planning/milestones/v1.5-phases/28-release-prep-publish-v0-3-0/28-CONTEXT.md` — precedente
  directo: D-11 (merge commit real), D-18 (doble gate independiente), D-08/D-09/D-10 (vehículo de
  branch/PR), formato de changelog establecido
- `.planning/milestones/v1.5-phases/28-release-prep-publish-v0-3-0/28-02-PLAN.md` y `28-03-PLAN.md`
  — implementación literal de los dos checkpoints como dos PLAN.md separados, `autonomous: false`
  cada uno
- `packages/iol-client/README.md` líneas ~112+ — sección `### v0.3.0` ya completa, usar como
  referencia de formato
- `packages/market-data-client/README.md` líneas ~125-166 — sección `### v0.5.0 — sin publicar
  todavía` a **ampliar** con los 3 breaks de 33-07
- `packages/iol-client/pyproject.toml:3`, `packages/iol-client/src/iol_client/__init__.py` —
  sitios de version bump
- `packages/market-data-client/pyproject.toml:3`,
  `packages/market-data-client/src/market_data_client/__init__.py` — sitios de version bump
- `.github/workflows/release.yml` — regex de tag, validación tag-vs-pyproject — **no editar**
- `.github/workflows/ci.yml` — `matrix.package` (ya lista los 6 paquetes), pytest scope — **no
  editar**
- PR #12 (`gh pr view 12`) — vehículo existente a actualizar, no reemplazar
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`release.yml` genérico** — soporta cualquier `<pkg>-client-vX.Y.Z` sin edits; cuarta y quinta
  vez que se reusa sin tocar el archivo.
- **Formato de changelog del README** — ya establecido en ambos paquetes (iol completo, market-data
  parcial); seguir la misma voz/estructura.
- **Precedente de release en la misma branch** — PRs #8, #9, #10, #11 son el template exacto de
  vehículo, shape de PR, tipo de merge y colocación de tag; PR #12 ya sigue el mismo patrón, sólo
  desactualizado.
- **28-02-PLAN.md / 28-03-PLAN.md** — template literal para los dos plans de checkpoint bloqueante
  (`autonomous: false`, `user_setup` con `gh auth status`, `<task type="checkpoint:decision"
  gate="blocking">`).

### Established Patterns

- Versionado per-package, sin versión monorepo.
- Alineación `pyproject.version` == `__version__` == `uv.lock` workspace member, hard-enforced por
  `release.yml`.
- `.planning/` trackeado y mergeado a `main` en cada release.
- Merge commit real + tag sobre el SHA del merge commit.

### Integration Points

- Dos tags (`iol-client-v0.3.0`, `market-data-client-v0.5.0`) sobre el **mismo** merge commit →
  cada uno dispara su propia corrida de `release.yml` → dos GitHub Releases independientes.
- `ci.yml` `matrix.package` × `python-version` = 6 × 2 = 12 jobs de test + 3 jobs no-matrix
  (lint, pre-commit, typecheck) = 15 checks totales — mismo conteo que Phase 28 pese a que ahora
  son 2 paquetes los que cambian (el matrix ya corre los 6 siempre).
- PR #12 → `.github/workflows/ci.yml` (dispara los 15 checks) → merge → dos tags → dos corridas de
  `release.yml` → dos GitHub Releases con wheel+sdist cada una.
</code_context>

<specifics>
## Specific Ideas

- Los dos tags deben ser **exactamente** `iol-client-v0.3.0` y `market-data-client-v0.5.0`.
- La sección `### v0.5.0` de `market-data-client/README.md` debe nombrar explícitamente los 3
  breaks de 33-07 (no sólo los 4 de Phase 31) antes de que la versión se bumpee.
- El PR #12 necesita: (1) push de los 44 commits locales pendientes, (2) retitulado/actualización
  de body para reflejar el scope final (fases 29-34, ambos paquetes, ambas versiones).
- El segundo checkpoint (tag-push) autoriza pushear **ambos** tags en la misma aprobación — no
  hace falta pedir aprobación dos veces para el tag.

## Verification / Risk Notes

- Ningún archivo de memory in-repo existe todavía para `iol-client` ni `market-data-client`
  (`ls .claude/projects/.../memory/` no tiene entradas para ninguno de los dos) — a diferencia de
  Phase 28 donde ya existía uno para `market-data-client`. Si se decide crear estos archivos,
  es trabajo nuevo, no un refresh.
- `gh auth status` confirma sesión autenticada (`sebadlf`, scopes `repo`+`workflow`) — sin blocker
  de auth conocido.
</specifics>

<deferred>
## Deferred Ideas

- **Crear archivos de memory in-repo para `iol-client`/`market-data-client`** — discrecional, no
  exigido por ningún criterio; candidato a hacerse en el mismo ciclo si el tiempo lo permite, pero
  no es un gate de la fase.
- **Actualizar `CLAUDE.md`** (si sigue citando versiones viejas) — fuera de scope, mismo criterio
  que D-07 de Phase 28.

### Reviewed Todos (not folded)

Ninguno — `todo.match-phase 34` devolvió 0 matches.
</deferred>
