# Phase 24: Release prep + publish v0.1.0 - Context

**Gathered:** 2026-07-31 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Publicar `market-data-client-v0.1.0` por el **mismo pipeline** que el resto de los paquetes
del monorepo (per-package tag → `release.yml` → GitHub Release con wheel + sdist). El paquete
en sí (código, tests, README, versión) ya fue construido en las Fases 20–23; esta fase cubre
únicamente **release prep + publish**: sumar el paquete al gate de CI, alinear la documentación
del monorepo (CLAUDE.md + MEMORY), abrir el PR → main, y —con go-ahead explícito— mergear y
taggear.

**Fuera de alcance:** cualquier cambio funcional al paquete; versionado repo-wide/workspace;
mutaciones/streaming/otros diferidos a v1.5+.
</domain>

<decisions>
## Implementation Decisions

### CI + Release Pipeline
- **D-01:** Agregar `market-data-client` a `matrix.package` en `.github/workflows/ci.yml`
  (hoy lista solo los otros 5, `ci.yml:97-102`). Es el **único** cambio necesario en archivos
  de workflow.
- **D-02:** **No** tocar `.github/workflows/release.yml`. Es genérico: parsea el tag con regex
  `^([a-z][a-z0-9-]*-client)-v<version>$`, valida que exista `packages/<pkg>`, verifica
  `pyproject.version == tag`, buildea wheel+sdist y crea el Release con `--generate-notes`.
  `market-data-client-v0.1.0` matchea sin edits.
- **D-03:** Regenerar/confirmar `uv.lock` con `uv sync --all-packages ... --frozen` verde.
  El lockfile ya contiene `market-data-client` (aparece `M` en git status); validar que
  esté al día, no re-crearlo desde cero.

### Documentación del monorepo
- **D-04:** Actualizar `CLAUDE.md` — agregar `market-data-client` (6º paquete, HTTP sync+async,
  Auth0 client-credentials) al listado de paquetes (`CLAUDE.md:72`) y a las tablas de
  Component Responsibilities / Architecture (`CLAUDE.md:171`).
- **D-05:** Actualizar MEMORY (index + pointer) reflejando el paquete publicado.

### Release Vehicle (branch & PR)
- **D-06:** Shippear desde la **branch existente `release/v0.2.0-bump`**. Abrir **un** PR
  `release/v0.2.0-bump` → `main` que arrastra todo el paquete `market-data-client`
  (Fases 20–23) + los edits de esta fase (ci.yml, CLAUDE.md, MEMORY). **No** construir una
  branch cherry-pickeada nueva.
- **D-07:** **Mantener** los artefactos `.planning/` en el PR (ya están trackeados en el repo
  a lo largo de milestones previos; CI ignora cambios `.md` para triggering). Sin filtrado
  (`/gsd-pr-branch` no se usa).

### Merge & Tag (acciones irreversibles — gated por go-ahead)
- **D-08:** El agente **conduce** todo el flujo: edits → abrir PR → confirmar CI verde →
  **mergear el PR** → **pushear el tag `market-data-client-v0.1.0`** (que dispara `release.yml`).
- **D-09:** El merge y el push del tag son irreversibles/outward-facing: el agente **confirma
  explícitamente en el punto de merge** antes de ejecutar (go/no-go final del usuario). Requiere
  working tree limpio + auth `gh`.
- **D-10:** El tag se crea sobre el **merge commit en `main`** con el formato per-package exacto
  `market-data-client-v0.1.0`.

### Version Scope
- **D-11:** **Solo per-package.** Ship únicamente `market-data-client v0.1.0`. **No** existe
  una versión repo-wide/workspace "v0.2.0" que bumpear — el nombre de la branch es incidental.
  El cambio en el `pyproject.toml` raíz es solo el alta del workspace member.

### Claude's Discretion
- Formato/wording exacto de las filas nuevas en CLAUDE.md y del pointer de MEMORY (seguir el
  patrón de las entradas existentes de los otros paquetes).
- Título/cuerpo del PR (seguir convención del repo; el Release usa `--generate-notes`).
- Orden de commits dentro de la fase (edits agrupados lógicamente).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — Phase 24 detail + success criteria (4 items)
- `.planning/REQUIREMENTS.md` — PUB-MD-01 (línea 29)
- `.github/workflows/ci.yml` — `matrix.package` (líneas 97-102) — punto de edición D-01
- `.github/workflows/release.yml` — pipeline genérico de tag→Release (no editar, referencia D-02)
- `packages/market-data-client/pyproject.toml` — `version = "0.1.0"`, hatchling targets
- `packages/market-data-client/src/market_data_client/__init__.py` — `__version__ = "0.1.0"` (línea 106)
- `packages/market-data-client/README.md` — README ya completo (uso, env vars, auth Auth0)
- `CLAUDE.md` — listado de paquetes (línea 72) + tablas de arquitectura (línea 171) — puntos de edición D-04
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`release.yml` genérico** — ya soporta cualquier `<package>-client-vX.Y.Z`; cero trabajo de
  pipeline nuevo. Valida dir + version-match, buildea con `uv build --package`, crea Release.
- **Patrón de matriz de CI** — `matrix.package` es una lista simple; agregar una entrada replica
  el gate (tests + coverage) para el nuevo paquete en py3.12 y py3.13.
- **READMEs de paquetes previos** — ya usados como template; el README de market-data-client
  sigue el mismo patrón y está completo.
- **Convención de tag per-package** — `iol-client-v0.1.1`, etc.; `market-data-client-v0.1.0`
  es la aplicación directa.

### Established Patterns
- **Versionado per-package** — cada paquete tiene su propia `version` en pyproject + su propio
  tag; no hay versión monorepo. (Confirma D-11.)
- **Alineación version/`__version__`** — pyproject `0.1.0` == `__version__` `0.1.0` (ya alineados).
- **`.planning/` trackeado en repo** — milestones previos commitearon artefactos de planning a
  main; mantenerlos en el PR es consistente (D-07).

### Integration Points
- `ci.yml` `matrix.package` — donde entra el nuevo paquete al gate (13→15 checks aprox.; el número
  exacto lo produce CI, no es una decisión).
- Tag `market-data-client-v0.1.0` sobre el merge commit → dispara `release.yml` → GitHub Release.
- Working tree / branch `release/v0.2.0-bump` — la unidad de merge (218 files / +23k vs main,
  contiene todo el milestone v1.4 sin mergear).
</code_context>

<specifics>
## Specific Ideas

- El tag debe ser **exactamente** `market-data-client-v0.1.0` (matchea el regex de release.yml
  y el patrón trigger `*-client-v*`).
- El agente confirma explícitamente antes de mergear y antes de pushear el tag (D-09).
</specifics>

<deferred>
## Deferred Ideas

- **Versión repo-wide/workspace "v0.2.0"** — descartada explícitamente (D-11); si en el futuro
  se quiere un versionado del monorepo, es su propia decisión de milestone.
- **Filtrado de `.planning/` del PR** (`/gsd-pr-branch`) — considerado y descartado (D-07).

### Reviewed Todos (not folded)
None — no pending todos matched Phase 24.
</deferred>
