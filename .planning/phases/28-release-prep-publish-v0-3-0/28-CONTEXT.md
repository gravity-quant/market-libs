# Phase 28: Release prep + publish v0.3.0 - Context

**Gathered:** 2026-08-01 (assumptions mode)
**Status:** Ready for planning

> **Nota de nomenclatura:** el directorio y el título de la fase dicen `v0-3-0` / `v0.3.0`
> porque así se escribió el ROADMAP en la creación del milestone. **La versión real que
> publica esta fase es `0.4.0`** (ver D-01). El nombre del directorio se mantiene sin cambios
> para no romper el tooling de GSD.

<domain>
## Phase Boundary

Publicar la superficie de **escritura de calendario** (Phase 26, MUT-MD-02) más los **fixes
in-cycle de la verificación en vivo** (Phase 27, LIVE-MUT-01) por el **mismo pipeline
per-package tag** que las cinco releases previas del monorepo (PR → merge → tag →
`release.yml` → GitHub Release con wheel + sdist).

El código ya está construido y verificado en vivo por las Fases 25–27; esta fase cubre
únicamente **release prep + publish**: bump de versión, entrada de changelog, refresh de
`uv.lock`, actualización del memory de releases, abrir el PR, confirmar CI verde, y —con
go/no-go explícito del operator— mergear y taggear.

**Contexto crítico:** las versiones `v0.3.0` y `v0.3.1` **ya se publicaron mid-milestone**
(PR #8 → `ea92dd8`, PR #9 → `7b0e0b2`, ambos 2026-07-31), llevando a `main` el trabajo de
Phase 25 (mutating-gate + symbols write) más un quick-fix. El objetivo literal del ROADMAP
está consumido y se re-apunta a `0.4.0`.

**Fuera de alcance:** cualquier cambio funcional al paquete; enrolar `market-data-client` en
el mypy/import-linter cross-package; versionado repo-wide; los diferidos de v1.6+
(SSE streaming, disk token cache, JWT validation).
</domain>

<decisions>
## Implementation Decisions

### Versión y clasificación semver

- **D-01:** La release es **`0.4.0`** (minor), tag exacto **`market-data-client-v0.4.0`**.
  **NO** `0.3.0` (tag ya existe en `origin` — el push sería rechazado y `release.yml` nunca
  dispararía), **NO** `0.3.2` (el diff sin publicar agrega **13 nombres públicos nuevos** a
  `__all__`: `add_holidays`, `delete_holiday`, `set_calendar_config`, `delete_calendar_config`,
  `preview_calendar_config`, `MarketHoursIn`, `HolidayIn`, `HolidaysIn` + sus contrapartes
  `aio` — un patch bump violaría semver para todo pin `~=0.3.1`), **NO** `1.0.0` (ver D-03).
  Pre-computado independientemente en `26-RESEARCH.md:910` y `27-CONTEXT.md:222-224`.

- **D-02:** **Re-apuntar `PUB-MUT-01`** en `.planning/REQUIREMENTS.md` (línea 28) y el texto de
  Phase 28 en `.planning/ROADMAP.md` de `v0.3.0` → `v0.4.0`, dejando constancia de que
  `v0.3.0`/`v0.3.1` se publicaron mid-milestone. El requisito se satisface por la publicación
  de `0.4.0`, no por la de `0.3.0` (que ya ocurrió fuera del flujo de fases).

- **D-03:** El bump se declara **minor no-breaking** bajo la decisión ya lockeada **D-13**
  (`27-CONTEXT.md:139-143`), **con un callout explícito en el changelog**. El lado symbols es
  verificadamente no-breaking; el lado `CalendarDay` es técnicamente source-breaking y se
  documenta en vez de blindarse con shim.
  - **Symbols — no-breaking (verificado):** `5cc9ac1` **ensancha** `symbol_id: str → int | str`
    en los cuatro routes (`_core.build_update_symbol_request`, `Client.update_symbol`,
    `AsyncClient.update_symbol`, ambos shims de módulo) y **preserva** `Symbol.marketId` como
    alias deprecado espejado desde el wire `market_id` vía override de `from_api`; los cinco
    campos nuevos de `Symbol` (`id`, `market_id`, `created_at`, `updated_at`, `received_at`)
    tienen defaults. `3c9d31c` desenvuelve el envelope preservando `list[Symbol]`.
    Re-verificado independientemente en `27-VERIFICATION.md:136-153`.
  - **`CalendarDay` — source-breaking, aceptado:** `831f44f` **removió** `date` / `marketId` /
    `isBusinessDay` y los reemplazó por `day` / `closed` / `description` / `open_time` /
    `close_time`. `CalendarDay` está en `__all__` desde v0.2.0, así que `d.date` en un consumidor
    v0.3.1 sería `AttributeError`. D-13 lo pre-autoriza como no-breaking porque
    `parse_calendar_response` iteraba las claves del envelope — ningún consumidor pudo haber
    tenido nunca una instancia poblada. **Riesgo residual conocido:** `27-VERIFICATION.md`
    re-verificó **sólo D-22**; D-13 es el único claim de no-breaking que nunca se auditó
    independientemente.
  - **Mitigación elegida (operator, 2026-08-01):** honrar D-13 y shippear minor, pero el
    changelog de `v0.4.0` **debe nombrar explícitamente** el reemplazo de campos de
    `CalendarDay` (viejos → nuevos) para que sea descubrible y no silencioso.
    **Rechazado:** compat shim con aliases deprecados (el patrón de `Symbol.marketId`) —
    considerado y descartado. **Rechazado:** escalar a `1.0.0` — contradice D-13/D-22 lockeados
    y quema el major que el docstring de `Symbol` en `models.py` reserva para remover el alias
    `marketId`.

### Superficie de edición (exactamente 5 sitios; cero archivos de workflow)

- **D-04:** Los sitios de edición son **exactamente cinco**:
  1. `packages/market-data-client/pyproject.toml:3` — `version = "0.3.1"` → `"0.4.0"`
  2. `packages/market-data-client/src/market_data_client/__init__.py:134` —
     `__version__ = "0.3.1"` → `"0.4.0"`
  3. `packages/market-data-client/README.md:60-62` — insertar `### v0.4.0` inmediatamente
     **arriba** de `### v0.3.1` (formato establecido: español, línea líder en negrita que nombra
     la clase de bump, IDs de requisito citados inline — ver `README.md:84`
     `**Symbols write (MUT-MD-01):**` como modelo)
  4. `uv.lock:488` — refrescado vía `uv lock`
  5. El memory de releases **in-repo** en
     `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md`
     — `description:` del frontmatter (línea 3) + el bloque "**Latest published:**"

- **D-05:** **`uv.lock` SÍ necesita refresh** aunque ninguna dependencia haya cambiado:
  `uv.lock:487-489` carga el propio version string del workspace member
  (`name = "market-data-client"` / `version = "0.3.1"`). Precedente: el stat de PR #9 muestra
  `uv.lock | 2 +-` — exactamente el churn de dos líneas. Si no se refresca, falla el step
  "Verificar uv.lock sincronizado" (`ci.yml:32`) del job `lint`, bloqueando el PR en el check
  1 de 15.

- **D-06:** **No** tocar `.github/workflows/`. `ci.yml:103` ya lista `market-data-client` en
  `matrix.package` (agregado en Phase 24); `release.yml` es genérico —regex
  `^([a-z][a-z0-9-]*-client)-v([0-9]+\.[0-9]+\.[0-9]+...)$` en `release.yml:28`— y matchea
  `market-data-client-v0.4.0` sin edits. Hereda Phase 24 D-02.

- **D-07:** **No** tocar `CLAUDE.md:74` (que todavía dice `market-data-client v0.2.0`, dos
  releases atrás). Ningún release previo lo tocó: no aparece ni en `git show --stat ea92dd8`
  ni en `7b0e0b2`. Es un artefacto generado por `/gsd-map-codebase`, no un archivo de release
  mantenido a mano. Se deja como deuda de documentación conocida.

  **Nota:** `/Users/admin/.claude/projects/-Users-admin-development-market-libs/memory/` está
  **vacío** — el memory real vive **in-repo** bajo `.claude/projects/…` (ver D-04 sitio 5).

### Vehículo de release (branch + PR)

- **D-08:** Shippear desde la branch existente **`milestone/v1.5-mutations`**. **Un** PR
  `milestone/v1.5-mutations` → `main`. Hereda Phase 24 D-06.

- **D-09:** **Mantener** los artefactos `.planning/` en el PR; **no** usar `/gsd-pr-branch`.
  Precedente directo en esta misma branch: `git show --stat ea92dd8` (PR #8) y `7b0e0b2` (PR #9)
  ambos arrastran `.planning/PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md` y decenas
  de `.planning/phases/**`. Filtrarlos rompería la continuidad de artefactos de la que dependen
  las Fases 25-27 (`.planning/verification/market-data-client-findings.md`, ~60K de evidencia
  live, nunca llegaría a `main`). Hereda Phase 24 D-07.

- **D-10:** **No** rebasear ni mergear `origin/main` en la branch. El estado "2 behind" es
  **cosmético**: `origin/main^{tree}` == `7f051ae^{tree}` (commit propio de la branch y
  merge-base) == `b404a5dd526807d6934e499b16c3cb3da3ad25ad`, por lo que
  `git diff --stat HEAD...origin/main` sale **vacío** — `origin/main` no contiene ningún
  contenido que la branch no tenga; los dos commits "behind" son merge commits puros
  (`ea92dd8`, `7b0e0b2`). `git merge-tree --write-tree origin/main HEAD` da conflict-free.
  Un rebase de 95 commits sobre dos merge commits ya mergeados reescribiría historia publicada
  y podría orfanar la alcanzabilidad de los tags `v0.3.0`/`v0.3.1`.

- **D-11:** El PR se mergea con **merge commit real** (`gh pr merge --merge`) — **no** squash,
  **no** rebase — y el tag se pushea **sobre ese merge commit**. Hereda Phase 24 D-10.
  Precedente: `ea92dd8` es `Merge: 5903f75 cb67933`, `7b0e0b2` es `Merge: ea92dd8 7f051ae`.
  Un squash colapsaría 95 commits en uno, descartando el trail por-plan que los SUMMARY de
  `.planning/phases/27-*/` cross-referencian por SHA.

- **D-12:** Título del PR siguiendo la convención ya establecida en esta branch:
  `release: market-data-client v0.4.0 (<one-line scope>)`.

### Gate de CI

- **D-13:** El gate es **15 checks verdes**: `ci.yml` define 4 jobs (`lint:23`, `pre-commit:52`,
  `typecheck:70`, `test:91`); `test` abre en `matrix.package` (6 entradas, `:98-103`) ×
  `matrix.python-version` (`["3.12","3.13"]`, `:104`) = 12 → 3 + 12 = **15**.

- **D-14:** Los **19 failures pre-existentes de matriz en `verification/`** (documentados en
  `27-deferred-items.md` items 1-2: drift de firma `probe_login_sync(client)` de Phase 15 —
  "19 failed, 19 errors, 220 passed") **no pueden bloquear este PR**: **ningún job de CI corre
  `verification/`**. La única invocación de pytest en CI es `ci.yml:112-118`, scoped a
  `pytest packages/${{ matrix.package }}`; el `testpaths = ["packages", "tests", "verification"]`
  del root (`pyproject.toml:106`) nunca se ejercita en workflow alguno. El hook mypy de
  `pre-commit` está scoped `files: ^packages/.*/src/` (`.pre-commit-config.yaml:32`), tampoco
  llega. **No esperar un full-suite verde antes de abrir el PR** — bloquearía indefinidamente
  sobre failures fuera de scope que CI nunca ve.

- **D-15:** Gates verificados verdes localmente sobre la branch (2026-08-01, pre-planning):
  `ruff check` → "All checks passed!"; `ruff format --check` → "201 files already formatted";
  `mypy` → "Success: no issues found in 51 source files"; `lint-imports` → "Contracts: 4 kept,
  0 broken"; `pytest packages/market-data-client -q` → **387 passed**. El archivo modificado más
  grande es `main_market_data.py` (144K), bien bajo el default de 500K de
  `check-added-large-files` (`.pre-commit-config.yaml:9`). Sin riesgo de CI conocido del diff
  sin publicar.

- **D-16:** `market-data-client` **permanece ausente** del `files` de mypy del root
  (`pyproject.toml:97`, lista 5 paquetes), de `root_packages` de import-linter
  (`pyproject.toml:141-146`, lista 4) y del loop mypy-tests per-package de `ci.yml:85`.
  Phase 28 **no** cierra ese follow-up — ver `27-CONTEXT.md:442-445` ("Follow-up documentado
  desde Phase 24 (sigue diferido, **no es un CI failure**)"); los checks package-scoped pasan
  hoy. **Decisión del operator (2026-08-01):** mantener diferido y **archivarlo explícitamente
  en el backlog de v1.6** (ROADMAP § Backlog) para que deje de rodar silenciosamente release
  tras release. **Rechazado:** enrolarlo en este PR (expandiría el diff del release).

### Ops irreversibles (gated por go/no-go humano)

- **D-17:** El agente **conduce** todo el flujo: edits → `uv lock` → abrir PR → confirmar los
  15 checks verdes → mergear → pushear el tag. Hereda Phase 24 D-08.

- **D-18:** **Dos checkpoints humanos bloqueantes**, ambos explícitos: (a) antes de **mergear el
  PR**, y (b) antes de **pushear el tag**. Ambas ops son irrecuperables en la práctica — un tag
  pusheado dispara `release.yml` y crea un GitHub Release público. Hereda Phase 24 D-09; el
  patrón de checkpoint de operator sigue vigente en este milestone (ver la autorización
  "armed destructive run" en `27-deferred-items.md`, otorgada 2026-08-01). Requiere working tree
  limpio + auth `gh`.

### Claude's Discretion

- Wording exacto de la entrada `### v0.4.0` del changelog (siguiendo el formato establecido en
  `README.md:60-100`), siempre que incluya el callout de `CalendarDay` requerido por D-03.
- Cuerpo del PR (el GitHub Release usa `--generate-notes`).
- Agrupamiento y orden de commits dentro de la fase.
- Wording exacto de la entrada de backlog v1.6 requerida por D-16 y del re-apuntado de D-02.

### Folded Todos

Ninguno — `todo.match-phase 28` devolvió 0 matches.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — sección Phase 28 + 4 success criteria (nota: SC#3 dice `v0.3.0`;
  re-apuntar per D-02)
- `.planning/REQUIREMENTS.md` — PUB-MUT-01 (línea 28)
- `.planning/phases/27-verificaci-n-en-vivo-segura-fixes/27-CONTEXT.md` — D-13 (líneas 139-143,
  `CalendarDay` no-breaking rationale) y D-22 (líneas 214-224, nota a Phase 28 sobre `v0.4.0`);
  líneas 442-445 (follow-up mypy diferido)
- `.planning/phases/27-verificaci-n-en-vivo-segura-fixes/27-VERIFICATION.md` — líneas 136-153
  (re-verificación de no-breaking del lado symbols; **no** cubre D-13)
- `.planning/phases/27-verificaci-n-en-vivo-segura-fixes/deferred-items.md` — items 1-2
  (19 failures pre-existentes de matriz en `verification/`); autorización de operator del
  armed run
- `.planning/phases/26-calendar-write/26-CONTEXT.md` — decisiones lockeadas de calendar write
- `.planning/phases/26-calendar-write/26-RESEARCH.md:910` — pre-cómputo de `v0.4.0`
- `packages/market-data-client/pyproject.toml` — línea 3 (`version`)
- `packages/market-data-client/src/market_data_client/__init__.py` — línea 134 (`__version__`),
  `__all__` (13 nombres nuevos)
- `packages/market-data-client/README.md` — líneas 60-100 (formato de changelog establecido)
- `.github/workflows/ci.yml` — `matrix.package` (línea 103), pytest scope (líneas 112-118),
  uv.lock check (línea 32) — **no editar**
- `.github/workflows/release.yml` — regex de tag (línea 28), validación tag-vs-pyproject
  (líneas 42-51) — **no editar** (D-06)
- `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md`
  — sitio de edición 5 (D-04)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`release.yml` genérico** — soporta cualquier `<pkg>-client-vX.Y.Z` sin edits; valida
  directorio + match de versión, buildea wheel+sdist con `uv build --package`, crea el Release
  con `--generate-notes`. Cero trabajo de pipeline nuevo (tercera vez que se reusa para este
  paquete).
- **Formato de changelog del README** — tres entradas previas (`v0.3.1`, `v0.3.0`, `v0.2.0`)
  establecen voz y estructura: español, línea líder en negrita nombrando la clase de bump,
  IDs de requisito citados inline.
- **Precedente de release en esta misma branch** — PRs #8 y #9 son el template exacto de
  vehículo, shape de PR, tipo de merge y colocación de tag.
- **Memory de releases in-repo** — `market-data-client-releases.md` ya rastrea "Latest
  published" release por release; el commit `5e7f5c7` ("docs(memory): update market-data-client
  latest release to v0.3.0") confirma que es un sitio de edición recurrente.

### Established Patterns

- **Versionado per-package** — cada paquete tiene su propia `version` + su propio tag; no hay
  versión monorepo.
- **Alineación `pyproject.version` == `__version__`** — hard-enforced por `release.yml:42-51`
  (falla el build con `Tag (X) ≠ pyproject.toml (Y)`).
- **`.planning/` trackeado y mergeado a `main`** — consistente a lo largo de todos los
  milestones.
- **Merge commit real para que el tag tenga un commit distinto** — Phase 24 D-10, honrado por
  PR #8 y #9.
- **Alias deprecado en vez de remoción** para campos de modelo reconciliados contra el wire
  (patrón `Symbol.marketId`) — el major se reserva para la remoción.

### Integration Points

- Tag `market-data-client-v0.4.0` sobre el merge commit → dispara `release.yml` → GitHub
  Release con wheel + sdist.
- `ci.yml` `matrix.package` — el paquete ya está enrolado; 15 checks totales.
- Branch `milestone/v1.5-mutations` (95 commits ahead de `origin/main`, 2 behind cosméticos)
  — la unidad de merge.
</code_context>

<specifics>
## Specific Ideas

- El tag debe ser **exactamente** `market-data-client-v0.4.0` (matchea el regex de
  `release.yml:28` y el trigger `*-client-v*`).
- El changelog `### v0.4.0` **debe** nombrar explícitamente el reemplazo de campos de
  `CalendarDay` (`date`/`marketId`/`isBusinessDay` → `day`/`closed`/`description`/`open_time`/
  `close_time`) — requisito de D-03, no opcional.
- El agente confirma explícitamente **dos veces**: antes de mergear y antes de pushear el tag
  (D-18).
- Las versiones `v0.3.0` y `v0.3.1` ya están publicadas — cualquier plan que asuma lo contrario
  está mal.

## Verification / Risk Notes

- **Riesgo residual conocido (D-03):** D-13 (`CalendarDay` no-breaking) nunca fue auditado
  independientemente — `27-VERIFICATION.md` sólo re-verificó D-22. Se acepta con mitigación de
  changelog; si un consumidor real leía `CalendarDay.date`, SC#4 sería literalmente falso.
- **Blocker externo (no resoluble desde el repo):** la config de branch-protection /
  required-status-checks de `main` no está representada en el repo (sin ruleset file, sin
  CODEOWNERS). Si los 15 checks son *required* para mergear —o sólo reportados— sólo se puede
  leer vía `gh api repos/:owner/:repo/branches/main/protection`. Afecta cómo se **enforcea** el
  gate de "15 verdes", no cuál debe ser.
</specifics>

<deferred>
## Deferred Ideas

- **Compat shim de `CalendarDay`** (re-agregar `date`/`marketId`/`isBusinessDay` como aliases
  deprecados espejando `day`/`""`/`not closed`, patrón de `Symbol.marketId`) — considerado y
  descartado en favor del callout de changelog (D-03). Candidato si aparece un consumidor real
  afectado.
- **Enrolar `market-data-client` en el mypy `files` del root + import-linter `root_packages` +
  el loop mypy-tests de `ci.yml:85`** — diferido desde Phase 24; **a archivar explícitamente en
  el backlog de v1.6** per D-16 (requiere autorar un contract de import-linter para
  `market_data_client._core`).
- **Actualizar `CLAUDE.md:74`** (dice `v0.2.0`, tres releases atrás) — fuera del scope del
  release PR per D-07; candidato a `/gsd-quick` docs task.
- **Reparar los 19 failures pre-existentes de matriz en `verification/`** (drift de firma
  `probe_login_sync(client)` de Phase 15) — fuera de scope, CI no los ve (D-14); ya trackeado
  en `27-deferred-items.md`.
- **Versionado repo-wide/workspace** — descartado desde Phase 24 D-11; sigue descartado.

### Reviewed Todos (not folded)

Ninguno — `todo.match-phase 28` devolvió 0 matches.
</deferred>
