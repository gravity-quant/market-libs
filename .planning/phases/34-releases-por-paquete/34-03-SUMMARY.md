---
phase: 34-releases-por-paquete
plan: 03
subsystem: release-ops
tags: [release, git-tag, github-release, human-checkpoint, release-memory, d-11]
requires:
  - "34-02 — `origin/main` == a89fa45, merge commit real de dos padres"
  - "34-02 — árbol mergeado con `version = \"0.3.0\"` y `version = \"0.5.0\"`"
  - "34-02 — la branch `milestone/v1.5-mutations` sobrevivió al merge"
provides:
  - "git-tag:iol-client-v0.3.0 — anotado, sobre a89fa45, en origin"
  - "git-tag:market-data-client-v0.5.0 — anotado, sobre el MISMO a89fa45, en origin"
  - "gh-release:iol-client-v0.3.0 — público, wheel + sdist"
  - "gh-release:market-data-client-v0.5.0 — público, wheel + sdist"
  - "release memory de market-data-client refrescada en sus seis regiones (commit 60fc58b)"
  - "aprobación humana literal registrada para el gate D-08(b)"
affects:
  - "PUB-TYP-01 — satisfecho: ambos paquetes públicamente instalables por tag y por wheel"
  - "Phase 34 — última plan de la fase; la fase queda completa"
  - "futuro — `iol-client-releases.md` sigue deliberadamente sin crear (deferral disponible)"
tech-stack:
  added: []
  patterns:
    - "tag anotado sobre SHA re-resuelto en vivo (`git rev-parse origin/main`), nunca sobre branch HEAD ni sobre un literal leído de un SUMMARY"
    - "push de tag POR NOMBRE, uno por uno — nunca `--tags` (existía un tag local-only `v1.3` que un push masivo habría publicado)"
    - "dos tags sobre un mismo merge commit → dos corridas independientes de `release.yml`, ambas vigiladas y verificadas por separado"
    - "aserción D-11 por sha256 del archivo, no por diff de directorio — el diff dir-wide arrastra baseline obsoleto"
key-files:
  created:
    - .planning/phases/34-releases-por-paquete/34-03-SUMMARY.md
  modified:
    - .claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md
decisions:
  - "El gate humano D-08(b) se resolvió con un \"approved\" literal del operador; NO se auto-aprobó pese a `auto_advance: true`, `mode: yolo` y el `gate=\"blocking\"` del task"
  - "Se refrescó la memory existente de market-data-client; NO se creó `iol-client-releases.md` — el deferral de CONTEXT § Deferred Ideas queda intacto y disponible"
  - "La aserción (f) del plan (diff dir-wide de `.github/workflows`) usa baseline obsoleto; el invariante real de D-11 se asertó por sha256 de `release.yml` y por diff desde el commit base de la fase"
metrics:
  duration: "~5 min"
  completed: "2026-08-27"
  tasks: "3 de 3"
  commits: 1
  files-changed: 1
status: complete
---

# Phase 34 Plan 03: Dos tags sobre un merge commit, dos Releases públicos, memory refrescada — Summary

Segundo gate humano bloqueante (D-08b) respondido con un `approved` literal; **dos** tags anotados
creados sobre el **mismo** merge commit `a89fa45` y pusheados **por nombre**; **dos** corridas
independientes de `release.yml` en verde publicando cuatro artefactos; y la release memory de
market-data-client refrescada en sus seis regiones. **PUB-TYP-01 cerrado.**

## Artefactos producidos

| Artefacto | Valor |
|---|---|
| `MERGE_SHA` (re-resuelto en vivo) | **`a89fa45602b52d509e15664d96a074af7eb1a337`** |
| Padres | `1c5f8f210e77e71c40faf602b8470569582e6221` + `e5eeb8ad0e5f3eaeb0b5713f256a28e497fa30d3` |
| Tag 1 | **`iol-client-v0.3.0`** → `a89fa45`, `git cat-file -t` = `tag` (anotado) |
| Tag 2 | **`market-data-client-v0.5.0`** → `a89fa45`, `git cat-file -t` = `tag` (anotado) |
| Run `release.yml` (iol) | **`33118792322`** — `success` |
| Run `release.yml` (market-data) | **`33118800550`** — `success` |
| Release 1 | https://github.com/gravity-quant/market-libs/releases/tag/iol-client-v0.3.0 (`2026-08-27T21:35:01Z`) |
| Release 2 | https://github.com/gravity-quant/market-libs/releases/tag/market-data-client-v0.5.0 (`2026-08-27T21:35:04Z`, `Latest`) |
| Commit de memory | **`60fc58b`** en `milestone/v1.5-mutations` |

**Los cuatro assets publicados:**

| Release | Assets |
|---|---|
| `iol-client-v0.3.0` | `iol_client-0.3.0-py3-none-any.whl`, `iol_client-0.3.0.tar.gz` |
| `market-data-client-v0.5.0` | `market_data_client-0.5.0-py3-none-any.whl`, `market_data_client-0.5.0.tar.gz` |

## Task 1 — gate humano bloqueante D-08(b)

**Checkpoint emitido:** `2026-08-27T21:33:18Z`.
**Respuesta del operador, verbatim:**

```
approved
```

**Timestamp de la respuesta:** `2026-08-27T21:34:30Z`.

**Presentado al operador** (todo re-resuelto en vivo, nada leído de un SUMMARY como fuente de
verdad): el `MERGE_SHA` con sus dos padres y el conteo `wc -w` = 3; ambas versiones del árbol
mergeado leídas con **la misma expresión awk que usa el pipeline** (`release.yml:47`); los dos
literales de tag validados **bajo bash contra el regex literal de `release.yml:28`**, con paquete y
versión parseados y el directorio verificado; la constatación de que ninguno de los dos tags existía
todavía (ni local ni en `origin`) y de que reusar `iol-client-v0.2.0` / `market-data-client-v0.4.0`
sería rechazado; el contenido de ambos releases (source-breaking, con callout); la intactitud de
`release.yml`; y la declaración explícita de que los Releases son **públicos y efectivamente
permanentes**, que un tag no se puede re-apuntar limpiamente, y que **una sola aprobación cubre
ambos tags**.

**Procedencia de la aprobación.** Respuesta literal del operador, relayed por el orquestador. **No**
auto-emitida por el agente, **no** de `auto_advance`, **no** de yolo mode, **no** inferida de
silencio ni de una respuesta ambigua. Importa concretamente: `.planning/config.json` tiene
`workflow.auto_advance: true` y `mode: "yolo"`, y el task está autorizado `gate="blocking"` (no
`gate="blocking-human"`), combinación que bajo la regla por defecto de `checkpoints.md` se
auto-aprobaría. La prosa del plan (`<action>`, `<acceptance_criteria>`, `must_haves.prohibitions`) y
D-08 sobrescriben ese default. Es **la misma inconsistencia de autoría** que 34-02 documentó para el
gate (a) — vale la pena corregir el atributo en futuros planes en vez de depender de la prosa.

**Estado en el momento del gate — nada irreversible había ocurrido:** árbol limpio, ambos
`git tag -l` vacíos, ninguno de los dos tags en `git ls-remote --tags origin`, y **cero** ejecuciones
de `git tag` o `git push` antes de la respuesta.

**Los dos gates de D-08 no se colapsaron** (el de merge se resolvió en 34-02 a las `20:24:40Z`; éste
a las `21:34:30Z`) **y este gate no se partió en dos**: una sola aprobación cubrió ambos tags, no se
preguntó dos veces, y no se avanzó sobre un tag mientras se esperaba por el otro.

## Task 2 — tags, push, dos pipelines, cuatro assets

### (a) Re-resolución y re-aserción antes de tagear

| Aserción | Requerido | Obtenido |
|---|---|---|
| `git rev-parse origin/main` | resuelve | `a89fa45…` — **idéntico** al cross-check de 34-02 |
| `git rev-list --parents -n1 \| wc -w` | 3 | **3** |
| `iol-client/pyproject.toml` bajo el awk de `release.yml:47` | `0.3.0` | **`0.3.0`** |
| `market-data-client/pyproject.toml`, mismo awk | `0.5.0` | **`0.5.0`** |

El SHA de 34-02 se usó **sólo como cross-check**; el ancla salió de `git rev-parse origin/main`.

### (b) Creación — anotados, sobre el SHA explícito

`git tag -a <name> "$MERGE_SHA" -m "<msg>"` para ambos. Nunca `git tag <name>` sin commit-ish (que
habría tageado el branch HEAD — que en este momento estaba **un commit adelante** de `origin`, así
que la forma sin commit-ish habría producido un Release apuntando a un commit fuera de la historia de
`main`). Verificado **antes** del push: ambos `type=tag`, ambos `anchor=a89fa45`.

Mensajes:
- `iol-client v0.3.0 — dict→modelo tipado en las 16 firmas (TYP-01)`
- `market-data-client v0.5.0 — endpoints de ops tipados (TYP-02/TYP-03) + tres fixes de forma (LIVE-TYP-01)`

### (c) Push — por nombre, uno por uno

```
git push origin iol-client-v0.3.0          →  * [new tag]  iol-client-v0.3.0
git push origin market-data-client-v0.5.0  →  * [new tag]  market-data-client-v0.5.0
```

Sin `--force`, sin `--tags`. **La prohibición de `--tags` no era teórica:** existe un tag local-only
`v1.3` (presente en local, ausente de `origin`) que un push masivo habría publicado. Sigue ausente de
`origin` tras ambos pushes.

### (d) Dos pipelines independientes

Los dos tags sobre un mismo commit dispararon **dos runs separados**, ambos vigilados a completion:

| Run | Tag | Conclusión |
|---|---|---|
| `33118792322` | `iol-client-v0.3.0` | **`success`** |
| `33118800550` | `market-data-client-v0.5.0` | **`success`** |

Ambos corrieron los nueve steps en verde, incluido `Verificar versión del pyproject == versión del
tag`. Anotaciones **no fatales** en el run de market-data, registradas y no accionadas: deprecación de
Node 20 en `actions/checkout@v4` / `astral-sh/setup-uv@v3`, y dos fallas del **cache de uv**
(`Failed to save` con un HTML de indisponibilidad de servicio, `Failed to restore: 400`). El cache es
opcional; el build y la publicación tuvieron éxito. **No se editó, re-creó ni re-corrió `release.yml`.**

### (e)/(f) Verificación de artefactos y de tags

Gate automatizado del plan (con la corrección de (f) explicada en la Desviación 1): **`PASS`**.

| Aserción | Estado |
|---|---|
| Ambos tags anotados (`git cat-file -t` = `tag`) | ✅ |
| Ambos en `origin` (`git ls-remote --tags`) | ✅ |
| `git rev-list -n1 <tag>` == `git rev-parse origin/main` para **ambos** | ✅ ambos `a89fa45` |
| El commit tageado sigue con dos padres | ✅ `wc -w` = 3 |
| 4 assets con nombre exacto | ✅ |
| Ningún tag creado para los otros cuatro paquetes | ✅ higyrus/ámbito/matriz/wallets sin tags nuevos |
| Ningún tag ni Release borrado o re-apuntado | ✅ los 16 Releases previos intactos, `gh release list` completo |
| Sin credenciales impresas | ✅ sólo `gh auth status`, que ya redacta a `gho_***` |

## Task 3 — memory refrescada en sus seis regiones

Commit **`60fc58b`** en `milestone/v1.5-mutations`, un solo archivo, 76 inserciones / 23 supresiones.
Gate automatizado del plan: **`PASS`**.

| Región | Cambio | Verificación |
|---|---|---|
| 1 — `description:` | nombra v0.5.0 como último release, clase de bump + headline, v0.4.0 entre las superadas | ✅ |
| 2 — `Latest published:` | `market-data-client-v0.5.0`, 2026-08-27, `a89fa45`, PR #12, run `33118800550`, declarado SOURCE-BREAKING | ✅ |
| 3 — sección de versión | nueva `**v0.5.0 adds …**` (4 endpoints tipados + 8 modelos + `to_dict()` + flip de truthiness + SC-1/SC-2/SC-3 + tolerancia preservada); v0.4.0/v0.3.1/v0.3.0 retituladas | ✅ 3 secciones con el sufijo |
| 4 — `**Scope note:**` | reescrita a v0.5.0: superficie de mutación sin cambios tras el mismo gate opt-in; lo nuevo es la superficie de ops **tipada** y verificada en **strict decode** bajo LIVE-TYP-01, que es lo que reveló las tres divergencias | ✅ `grep -c` = **1**; residuo y handle `GSDPROBE/` preservados |
| 5 — `**Prior releases:**` | v0.4.0 demotada a la cabeza con fecha/SHA/PR; v0.3.1/v0.3.0/v0.2.0 conservadas; cierre re-versionado a v0.5.0; v0.1.0 sigue marcada buggy | ✅ |
| 6 — dos líneas de install | ambas re-apuntadas | ✅ línea git: `v0.5.0` **×2** y `market-data-client-v` **×2**; línea wheel: `v0.5.0` **×1**, `market-data-client-v` **×1**, `market_data_client-0.5.0-py3-none-any.whl` **×1**, `market_data_client-0.` **×1** — cero tokens obsoletos |

**Regiones intocadas, verificadas byte-idénticas por `diff` contra `git show HEAD:<file>`** (no por
inspección visual): el párrafo de intro, el bloque `**Runtime config (env / .env)**` (sigue con
`MARKET_DATA_AUTH0_TOKEN_URL`) y la línea `Related:`. Las tres reportaron `IDENTICAL`.

La memory está en **inglés** y el changelog del README en español: se transmitieron los mismos
hechos, sin copia literal. **Ningún valor de credencial** entró al archivo — el bloque de runtime
config nombra sólo VARIABLES.

### Decisión explícita sobre archivos de memory

- **Refrescado:** `market-data-client-releases.md` (ya existía; dejarlo obsoleto instruía activamente
  a instalar una versión superada). Refrescar un artefacto existente **no es** el item que CONTEXT
  difirió.
- **NO creado:** `iol-client-releases.md`. Crear un archivo de memory nuevo **es exactamente** el item
  diferido en CONTEXT § Deferred Ideas; ningún criterio del ROADMAP lo exige y esta fase no lo abrió.
  Verificado con `test ! -e`. **Queda disponible para que una fase futura lo tome deliberadamente y
  no por accidente** — `iol-client` v0.3.0 ya está publicado y sería el contenido natural.

## Desviaciones del plan

### 1. [aserción con baseline obsoleto, invariante real intacto] La aserción (f) de Task 2 falla sobre `ci.yml`

- **Encontrado en:** Task 2 (f), al correr el `<automated>` del plan — salió exit 1.
- **Realidad:** `git diff --name-only <prior-tag>..<new-tag> -- .github/workflows` devuelve
  **`.github/workflows/ci.yml`** (1 línea, no 0) para **ambos** rangos.
- **Diagnóstico — los commits son todos anteriores a la Phase 34:** `c1a7f90` (32-02, gate de
  surface-types), `60e4d97` (31, mypy de tests de market-data), `f1d1cd6` (31-02,
  uniform-structure), `b37b95c` (29-09, decode-intactness) y, sólo en el rango de iol, `1f295b3`
  (24-01, market-data al matrix de CI). Son precisamente los gates que corrieron en verde. La
  aserción viene del precedente de la Phase 28, **single-package y sin trabajo de CI intermedio**;
  su baseline (el tag de release anterior) quedó obsoleto en cuanto Phases 29-32 tocaron `ci.yml`.
- **Invariante real de D-11 — "ningún workflow modificado *por esta fase*": SE CUMPLE, por dos
  medidas independientes.**
  - `git diff --name-only 97ccee2..origin/main -- .github/workflows` → **0 archivos**, y
    `git log 97ccee2..origin/main -- .github/workflows` → **0 commits** (baseline = HEAD previo a la
    fase).
  - `release.yml` — el pipeline que de verdad importa — **byte-idéntico por sha256 en los cuatro
    refs**: `7109ff0b6819c596…` en `iol-client-v0.2.0`, `market-data-client-v0.4.0`,
    `iol-client-v0.3.0` y `market-data-client-v0.5.0`. Diff de `release.yml` = **0** contra ambos
    tags previos.
- **Acción:** se re-corrió el gate con (f) apuntada al invariante real (`release.yml` por archivo +
  diff desde el commit base de la fase) → **`PASS`**. **No se parcheó ningún workflow, no se editó el
  `PLAN.md`, y no se reportó la aserción literal como verde.** Es la misma clase de hallazgo que la
  Desviación 3 de 34-02 y la Desviación 2 de 34-01 — **tercera aparición del mismo baseline obsoleto
  en la fase**, lo que sugiere corregir la forma de la aserción en el patrón, no plan por plan.

### 2. [contexto operativo, sin acción] La branch local estaba un commit adelante de `origin` al tagear

- **Encontrado en:** preparación del checkpoint.
- **Qué pasó:** `HEAD` de `milestone/v1.5-mutations` estaba en `94fb04f`
  (`docs(34-02): complete PR update + merge plan`, el commit de docs de 34-02 con `commit_docs: true`)
  mientras `origin/milestone/v1.5-mutations` seguía en `e5eeb8a`.
- **Por qué importa:** hace **concreta** la advertencia del plan sobre `git tag` sin commit-ish. Un
  `git tag <name>` bare habría anclado en `94fb04f`, que **no es ancestro de `origin/main`**
  (verificado: `git merge-base --is-ancestor origin/main HEAD` → falso), produciendo un Release
  apuntando a un commit fuera de la historia de `main`. La forma `git tag -a <name> "$MERGE_SHA"` lo
  evita por construcción.
- **Acción:** ninguna sobre el tagging (el ancla siempre fue el SHA explícito). Se le divulgó al
  operador en el checkpoint. El commit de memory de Task 3 (`60fc58b`) se apiló encima, así que la
  branch local queda **dos** commits adelante de `origin`; ambos llegan a `main` en un PR futuro.

## Ubicación del commit de memory

`60fc58b` vive en **`milestone/v1.5-mutations`**, NO en `main` (verificado:
`git branch --contains HEAD -a | grep -c remotes/origin/main` → **0**). La branch sobrevivió al merge
porque `delete_branch_on_merge` es `false`. **Alcanzará `main` en un PR futuro** — es el patrón
establecido y **el release NO está bloqueado por eso**: ambos Releases ya están públicos.

## Prohibiciones del plan — verificación explícita

| Prohibición | Estado |
|---|---|
| Nunca borrar ni re-apuntar un tag o Release ya publicado | ✅ los 16 Releases previos intactos; ningún `tag -d`, ningún `release delete` |
| Nunca pushear con `--tags` bare; nunca con force | ✅ push por nombre ×2; el tag local-only `v1.3` sigue ausente de `origin` |
| Ningún checkpoint satisfecho por el agente, `auto_advance`, yolo o silencio | ✅ `approved` literal del operador, registrado verbatim con timestamp |
| Nunca parchear `release.yml` / `ci.yml` para hacer pasar un pipeline | ✅ `release.yml` byte-idéntico por sha256 en los 4 refs; 0 commits de workflow en la fase |
| Nunca imprimir el token ni credencial alguna | ✅ sólo `gh auth status`, que ya redacta |
| No crear tags para los cuatro paquetes sin cambios | ✅ higyrus/ámbito/matriz/wallets sin tags nuevos |
| No crear `iol-client-releases.md` | ✅ `test ! -e` |

## Estado al cerrar

| Aserción | Estado |
|---|---|
| `origin/main` | `a89fa45` — sin tocar por este plan |
| `git-tag:iol-client-v0.3.0` | **en `origin`**, anotado, sobre `a89fa45` |
| `git-tag:market-data-client-v0.5.0` | **en `origin`**, anotado, sobre `a89fa45` |
| Releases públicos | **2 creados**, 4 assets, ambos runs `success` |
| Ambos gates de D-08 | **resueltos** con aprobación literal, independientes, nunca colapsados |
| Memory de market-data-client | refrescada, commit `60fc58b` en la branch de release |
| `iol-client-releases.md` | **no creado** — deferral intacto |
| PUB-TYP-01 | **satisfecho** |
| Phase 34 | **completa** — éste era el último plan |

## Known Stubs

Ninguno. Este plan no agregó lógica: operaciones de `git`/`gh` más la edición de un documento de
prosa en inglés. Cero archivos bajo `packages/` tocados.

## Threat Flags

Ninguna. No se introdujo superficie de red, auth, acceso a archivos ni schema. Los threats del
registro con disposición `mitigate` quedaron todos ejercidos y verdes: **T-34-03** (tags anotados
sobre el SHA re-resuelto, literales exactos validados contra el regex del pipeline), **T-34-06**
(segundo checkpoint humano — aprobación literal, no auto-advance), **T-34-02** (ambas versiones del
árbol re-asertadas antes de tagear; el pipeline las revalidó de forma independiente), **T-34-11**
(ningún tag ni Release borrado o re-apuntado; la falla de aserción (f) se surfaceó en vez de
parchearse), **T-34-07** (sin credenciales impresas; ambos bodies por `--generate-notes`; la memory
nombra sólo variables de entorno), **T-34-12** (las seis regiones refrescadas, ambas líneas de
install asertadas por conteo exacto de ocurrencias, un solo `Scope note`).

## Self-Check: PASSED

- `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md` — existe en disco, modificado y commiteado.
- `.planning/phases/34-releases-por-paquete/34-03-SUMMARY.md` — existe en disco.
- Commit `60fc58b` — existe en `git log` sobre `milestone/v1.5-mutations`.
- Tags `iol-client-v0.3.0` y `market-data-client-v0.5.0` — existen local y en `origin`, ambos anotados, ambos sobre `a89fa45`.
- Releases `iol-client-v0.3.0` y `market-data-client-v0.5.0` — existen en GitHub con sus dos assets cada uno.
- Runs `33118792322` y `33118800550` — ambos `success`.
