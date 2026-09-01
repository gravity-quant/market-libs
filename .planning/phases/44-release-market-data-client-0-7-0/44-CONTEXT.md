# Phase 44: Release `market-data-client` 0.7.0 - Context

**Gathered:** 2026-08-31 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

La corrección de forma de `Instrument`/`Segment` hecha en la Phase 43 (fix, sin publicar) llega a
los consumidores como una release **0.7.0** publicada: bump en los 4 sitios de versión, changelog +
tabla de migración vieja→nueva campo por campo en `README.md`, y las dos operaciones irreversibles
(merge del PR, push de los tags) pasan por dos gates humanos independientes que esta vez están
**escritos** literalmente como `gate="blocking-human"` en el archivo de plan — no sólo respetados
por accidente de prosa u override del orchestrator, como ocurrió en las Phases 34 y 40.
Requisito: `PUB-01`. Depende de Phase 43 (completa).

**Fuera de alcance:** cualquier cambio funcional nuevo a `market-data-client` más allá de lo que
Phase 43 ya construyó y lo que este documento fold-ea explícitamente (ver D-06); editar
`.github/workflows/release.yml` o `.github/workflows/ci.yml`; publicar cualquiera de los otros 5
paquetes del monorepo.
</domain>

<decisions>
## Implementation Decisions

### Los 4 sitios de versión

- **D-01:** Los "4 sitios de versión" del criterio 2 del ROADMAP son: `packages/market-data-client/pyproject.toml:3`,
  `packages/market-data-client/src/market_data_client/__init__.py:163`, y **dos** líneas de
  `README.md` — `:15` (URL de instalación `git+...@market-data-client-v0.6.0`) y `:24` (nombre del
  wheel `market_data_client-0.6.0-py3-none-any.whl`, que aparece dos veces en esa misma línea).
  **`uv.lock` NO es uno de los 4 sitios** — es un artefacto aparte, refrescado exactamente una vez
  (D-02) después de que los 4 sitios estén bumpeados. `test_version_metadata.py` tampoco es un
  sitio: parsea `pyproject.toml` en tiempo de ejecución y verifica consistencia, no hardcodea nada.
  Precedente: `43-03-SUMMARY.md` cita el defecto exacto que se comete si se saltea un sitio README —
  Phase 34 shippeó un README con changelog de v0.5.0 pero comando de instalación apuntando a v0.4.0
  (Critical de code review, corregido en PR #13 de seguimiento).

- **D-02:** `uv lock` corre **exactamente una vez**, después de bumpear los 4 sitios, antes de abrir
  el PR. `release.yml` **no se edita** — séptima reutilización sin cambios (sexto release de
  `market-data-client` más 6 releases previos de otros paquetes desde que el archivo se tocó por
  última vez el 2026-05-09).

### Changelog y tabla de migración en README

- **D-03:** Se agrega una sección `### v0.7.0` insertada **directamente arriba** de `### v0.6.0`
  (`README.md:125`) — **sin** sección "Unreleased" de staging. Ninguna sección "Unreleased" existe
  hoy en ningún README del monorepo (ni market-data-client ni iol-client, que también van directo a
  `### vX.Y.Z`); esta fase no introduce el patrón por primera vez. Formato exacto: párrafo en
  negrita con el callout de ruptura, luego tabla de migración de dos columnas, luego prosa —
  espejando literalmente la forma de la sección `### v0.6.0` ya escrita (`README.md:127-152`).

- **D-04:** La tabla de migración se transcribe desde `43-DISPOSITION.md` § 1.1 (Instrument) y
  § 1.2 (Segment), como **dos tablas separadas** — no una sola fusionada — convirtiendo el formato
  de 6 columnas de ingeniería (Campo/Origen/Disposición/Tipo final/Evidencia/Decisión) al formato
  de 2 columnas del README (expresión vieja → expresión nueva). Razón para no fusionar: los dos
  modelos cubren endpoints distintos (`GET /instruments` vs `GET /instruments/segments`) con
  semánticas de ruptura distintas — Instrument es mayormente aditivo + 1 remoción; Segment es un
  reemplazo íntegro (key-sets disjuntos, D-13 de la Phase 43, `Segment` **no** se alias-mapea bajo
  el precedente D-22 porque no hay variante de spelling, son nombres distintos). Fusionar arriesga
  que un consumidor confunda la remoción de `Segment.marketId` (sin reemplazo) con la preservación
  como alias aditivo de `Instrument.marketId` (D-04 de la Phase 43) — el par más confundible de todo
  el cambio.
  - Fila de Instrument a documentar explícitamente: `marketId` se preserva como **alias aditivo**
    (nunca rename) sobre `market_id`, remoción programada para el próximo MAJOR — no un breaking
    silencioso.
  - Filas de Segment: `segment`/`live_instruments` agregados; `marketSegmentId`/`marketId`/
    `description` removidos sin reemplazo (siempre decodificaban `""` — remoción no-breaking en la
    práctica, D-13).

### Alcance — fold de deuda de la Phase 43 (única decisión Unclear, confirmada por el operador)

- **D-05 [confirmado — "Yes, proceed" sobre el fold parcial]:** Se **foldea** `SURF-MD-FEEDSUB-43`
  en esta fase: agregar `"FeedSubscription"` al `__all__` de
  `packages/market-data-client/src/market_data_client/__init__.py` (hoy tiene `FeedIngestor`,
  `FeedMarket`, `FeedPipeline` pero no `FeedSubscription`, pese a que sí está en `models.__all__`).
  Justificación: es un fix de una línea en un archivo que esta fase ya abre para el bump de
  `__version__` (D-01), en el mismo paquete que se publica — el wheel 0.7.0 sale con una superficie
  consistente. Verificar corriendo `uv run python tools/check_surface_types.py` inmediatamente
  después del edit, **antes** de pushear la branch — si el gate se pone rojo, es recuperable
  pre-merge pero bloquea el gate de merge hasta corregirse.

- **D-06:** Se **difiere** `DRV-MD-SEG-43` a la Phase 45. Es un archivo de harness/driver
  (`main_market_data.py:1541-1542`, dereferencia `Segment.marketSegmentId` ya removido, degrada en
  silencio vía `except Exception`), no está cubierto por ninguno de los 5 criterios de éxito del
  ROADMAP de esta fase (que son 100% mecánica de release), y `ROADMAP.md:62,175` nombra la Phase 45
  explícitamente como "Limpieza del harness" — es su tema, no el de una fase de release. Consecuencia
  aceptada: el probe de paridad de segments queda ciego en el próximo run en vivo hasta la Phase 45.

### Mecánica de los dos gates

- **D-07:** No existe branch ni PR de v1.8 hoy — medido: `git rev-list --count origin/main..HEAD` =
  **84** (main local 84 commits adelante), `HEAD..origin/main` = **0**, `gh pr list --state all` sin
  PR abierto (el más alto es #15, MERGED, de `milestone/v1.7-nobj-null-objects`). Esta fase crea una
  branch nueva siguiendo el patrón `milestone/vX.Y-slug` (ambos precedentes — #12 de
  `milestone/v1.5-mutations`, #15 de `milestone/v1.7-nobj-null-objects` — lo siguieron), pushea los
  84 commits pendientes (fast-forward), y abre un PR nuevo cubriendo la Phase 44 (más cualquier
  trabajo de v1.8 previo aún no publicado en ese PR).

- **D-08 [el ítem crítico de esta fase — motivo de su propia existencia separada de la 43]:**
  Exactamente **dos** checkpoints humanos bloqueantes, implementados como **dos `PLAN.md`
  separados** (`autonomous: false` cada uno): (a) antes de `gh pr merge --merge` (nunca squash, nunca
  rebase), (b) antes de pushear los tags anotados. Cada uno debe llevar literalmente
  `<task type="checkpoint:decision" gate="blocking-human">` o
  `<task type="checkpoint:human-verify" gate="blocking-human">` — **nunca** `gate="blocking"` a
  secas. Esto ya salió mal **en las tres fases precedentes con este patrón**, no en una: `40-01-PLAN.md:305`,
  `40-02-PLAN.md:259` y `40-03-PLAN.md:172` usan `gate="blocking"`, y `PROJECT.md:71` registra la
  misma falla de autoría en los dos checkpoints de la Phase 34 (`34-02`/`34-03`). Las cuatro veces,
  sólo un override explícito del orchestrator evitó la auto-aprobación bajo `auto_advance: true` +
  `mode: yolo` (ambos confirmados activos ahora mismo en `.planning/config.json`). El criterio 4 del
  ROADMAP exige que la autoría se verifique **en el propio archivo de plan** — un grep post-hoc de
  `gate="blocking"` (sin `-human`) sobre los dos plans debe devolver cero resultados antes de
  considerar la fase cerrada.

- **D-09:** El tag anotado se crea sobre el SHA del merge commit **re-resuelto en vivo post-merge**
  (no la branch HEAD pre-merge). Una sola aprobación del checkpoint (b) cubre el push del único tag
  de esta ronda (`market-data-client-v0.7.0` — ningún otro paquete se publica, D-11).

- **D-10:** Todos los bloques `<verify>` corren vía `bash -c` — Phase 40 midió que fallan bajo zsh
  (word-splitting) en esta máquina (`Shell: zsh` confirmado). Todo conteo se re-deriva en vivo, nunca
  se hardcodea — Phase 40 encontró un conteo stale (`wallets-client-v*` asumido en 2, real 1).
  Baseline de tags **medido ahora** (pre-fase): `iol-client` 4 (v0.1.1/v0.2.0/v0.3.0/v0.4.0),
  `higyrus-client` 3, `matriz-client` 3, `ambito-financiero-client` 2, `wallets-client` 1,
  `market-data-client` 7 (v0.1.0→v0.6.0 incl. v0.3.1). Post-fase: los cinco primeros deben quedar
  **idénticos**, `market-data-client` debe pasar a **8**.

- **D-11:** El gate de merge (checkpoint a) cuenta **15/15 checks de CI explícitamente**, nunca por
  ausencia-de-fallo — `ci.yml` define 4 jobs (`lint`, `pre-commit`, `typecheck`, `test`) con `test`
  en matrix de 6 paquetes × 2 versiones de Python = 12, total 15. Precedente: en Phase 34 este conteo
  explícito atrapó tanto un fail real de mypy como una carrera transitoria de "cero checks
  reportados" que un check de ausencia-de-fallo habría dejado pasar.

- **D-12:** Verificación post-publicación (criterio 1 del ROADMAP): instalar desde el **wheel
  público** en un entorno descartable **fuera del repo** y ejercer una cadena profunda ya existente
  en el paquete instalado — no basta con leer el reporte de la corrida de `release.yml`.

### Claude's Discretion

- Wording exacto de la prosa de la sección `### v0.7.0` del changelog (seguir la voz/formato ya
  establecido: español, tabla antes/después, línea líder en negrita).
- Nombre exacto de la branch nueva (dentro del patrón `milestone/v1.8-...`) y título/body del PR.
- Si además de `SURF-MD-FEEDSUB-43` conviene agregar `__version__`-adjacent cosmética discrecional
  (ninguna identificada; matriz-client's missing `__version__` es un ítem de otro paquete, no toca
  esta fase).
- Agrupamiento y orden de commits dentro de la fase.

### Folded Todos

Ninguno — `todo.match-phase 44` devolvió 0 matches.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` § Phase 44 — 5 criterios de éxito + `Requirements: PUB-01`
- `.planning/REQUIREMENTS.md` (línea 26) — texto completo de `PUB-01`
- `.planning/phases/43-market-data-client-forma-de-instrument-segment-5-claves-extr/43-DISPOSITION.md`
  § 1.1 (Instrument, 12 filas) y § 1.2 (Segment, 5 filas) — contenido exacto de la tabla de
  migración, ya escrito y listo para transcribir (D-04)
- `.planning/phases/43-market-data-client-forma-de-instrument-segment-5-claves-extr/43-03-SUMMARY.md`
  (línea 264) — las tres entradas concretas que la Phase 43 deja para la 44
- `.planning/ROADMAP.md` (líneas 240-241) — `DRV-MD-SEG-43` y `SURF-MD-FEEDSUB-43`, texto completo
  de ambos hallazgos de backlog (D-05/D-06)
- `.planning/research/PITFALLS.md` — Pitfall 14 (colapso del gate, 3ª ocurrencia) y la sección
  "Looks Done But Isn't" § Release — checklist literal a satisfacer
- `.planning/milestones/v1.7-phases/40-releases-breaking-coordinados/40-CONTEXT.md` — precedente
  directo inmediato: D-05 (branch nueva), D-07/D-08 (dos gates), D-09 (tag sobre SHA post-merge),
  D-10 (uv.lock único), D-11 (verificación post-publicación instalando el wheel)
- `.planning/milestones/v1.7-phases/40-releases-breaking-coordinados/40-01-PLAN.md`,
  `40-02-PLAN.md`, `40-03-PLAN.md` — template de los 3 plans (prep autónomo + 2 checkpoints), **con
  el defecto de autoría (`gate="blocking"` sin `-human`) a corregir, no a copiar verbatim**
  (D-08)
- `.planning/milestones/v1.6-phases/34-releases-por-paquete/34-CONTEXT.md` y `34-02-PLAN.md`/
  `34-03-PLAN.md` — mismo defecto de autoría, segunda ocurrencia
- `packages/market-data-client/README.md` — sección `## Changelog` (línea 123), `### v0.6.0`
  (línea 125) como plantilla de forma exacta para `### v0.7.0`; líneas 15 y 24 (2 de los 4 sitios
  de versión, D-01)
- `packages/market-data-client/pyproject.toml:3`, `src/market_data_client/__init__.py:163` — los
  otros 2 sitios de versión (D-01)
- `packages/market-data-client/src/market_data_client/models.py:894-895` — `Segment` ya shippeado
  (Phase 43) como `segment: str` / `live_instruments: int`, base de la tabla de migración
  - `packages/market-data-client/src/market_data_client/models.py:106` (`models.__all__`) vs
  `packages/market-data-client/src/market_data_client/__init__.py:104-156` (`__all__` del
  paquete) — el gap de `FeedSubscription` a cerrar (D-05)
- `main_market_data.py:1541-1543` — el dereference de `DRV-MD-SEG-43`, explícitamente **no**
  tocado en esta fase (D-06)
- `.github/workflows/release.yml` — regex de tag, gate de version-match, lee solo
  `pyproject.toml` — **no editar** (D-02)
- `.github/workflows/ci.yml` — 4 job definitions / 15 checks totales (D-11)
- `.planning/config.json` — `auto_advance: true`, `mode: "yolo"`, `git.branching_strategy: "none"`
  confirmados activos ahora — la condición exacta bajo la cual D-08 importa
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`release.yml` genérico** — soporta cualquier `<pkg>-client-vX.Y.Z` sin edits; séptima vez que
  se reusa sin tocar el archivo.
- **Formato `### vX.Y.Z` + tabla de migración de 2 columnas** — ya establecido en market-data-client
  (v0.5.0, v0.6.0) e iol-client; ningún README del monorepo usa una sección "Unreleased".
- **`40-01-PLAN.md`/`40-02-PLAN.md`/`40-03-PLAN.md`** — template estructural para prep autónomo +
  2 checkpoints bloqueantes, **corrigiendo** el atributo `gate` a `blocking-human` (no copiarlo tal
  cual).
- **Precedente D-22 (alias aditivo sin rename)** — ya aplicado por la Phase 43 a
  `Instrument.marketId`; documentar en la tabla de migración como aditivo, no como parte de la
  ruptura.

### Established Patterns

- Versionado per-package, sin versión monorepo.
- 4 sitios de versión = pyproject + `__init__.py` + 2 líneas de README (no `uv.lock`, no el test de
  metadata — D-01).
- Merge commit real + tag anotado sobre el SHA del merge commit re-resuelto post-merge.
- Branch nueva por milestone, nunca push directo a `main` para releases.

### Integration Points

- 1 tag (`market-data-client-v0.7.0`) sobre el merge commit → dispara `release.yml` → 1 GitHub
  Release con wheel + sdist.
- `ci.yml` `matrix.package` × `python-version` = 6 × 2 = 12 jobs de test + 3 jobs no-matrix = 15
  checks totales.
- Branch nueva → PR nuevo → 15 checks → checkpoint (a) → merge real → tag sobre SHA re-resuelto →
  checkpoint (b) → push tag → 1 corrida de `release.yml` → 1 release → verificación
  post-publicación instalando desde wheel público fuera del repo.
</code_context>

<specifics>
## Specific Ideas

- Las filas exactas de ambas tablas de migración deben sintetizarse a partir de
  `43-DISPOSITION.md` § 1.1 y § 1.2 (contenido locked por D-04, wording a discreción).
- El fold de `SURF-MD-FEEDSUB-43` (D-05) es la única decisión que el operador confirmó
  explícitamente en esta sesión sobre una recomendación marcada "Unclear" — verificar el gate de
  `check_surface_types.py` inmediatamente después del edit, antes de pushear.
</specifics>

<deferred>
## Deferred Ideas

- `DRV-MD-SEG-43` (`main_market_data.py:1541-1542`) — diferido explícitamente a la Phase 45 (D-06),
  no un carry-forward silencioso: queda nombrado en el ROADMAP con su medición completa de por qué
  ningún gate estático lo detecta hoy.
- Agregar `__version__` a `matriz_client/__init__.py` — de otro paquete, no toca esta fase.

### Reviewed Todos (not folded)

Ninguno — `todo.match-phase 44` devolvió 0 matches.
</deferred>
