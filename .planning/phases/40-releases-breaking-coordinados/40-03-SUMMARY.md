---
phase: 40-releases-breaking-coordinados
plan: 03
subsystem: release-mechanics
tags: [release, git-tag, github-release, checkpoint, blocking-human, irreversible, awaiting-approval]
requires:
  - "plan 40-02 complete: PR #15 MERGED, `origin/main` at a real two-parent merge commit"
  - "authenticated `gh` CLI with `repo` + `workflow` scopes"
  - "operator go/no-go at the D-07(b) pre-tag-push gate — NOT YET GIVEN"
provides:
  - "a fully re-resolved, live-measured pre-push evidence pack for the D-07(b) gate"
  - "the exact 4-tag list, each string validated against `release.yml:28` and against its merged-tree version under the pipeline's own awk"
affects:
  - "nothing yet — this run created no tag, pushed nothing, and published nothing"
tech-stack:
  added: []
  patterns:
    - "re-resolve the tag anchor live from `git rev-parse origin/main`; treat the SUMMARY literal as a cross-check, never as the source"
    - "prove a merge is real by parent COUNT (3 whitespace fields), never by the subject line"
    - "validate a tag string against the pipeline's OWN regex and the pipeline's OWN awk version reader before proposing it"
    - "a blocking gate on an irreversible op is not satisfiable by `auto_advance`, `mode: yolo`, silence, or agent self-issue"
    - "workflow immutability asserted by sha256 identity across refs, NOT by the Phase 34 tag-baseline diff form"
key-files:
  created:
    - .planning/phases/40-releases-breaking-coordinados/40-03-SUMMARY.md
  modified: []
decisions:
  - "No tag was created locally, deliberately — plan Task 1 forbids any `git tag` before the operator reply, and 4 extra local tags would enlarge the very `git push --tags` hazard the phase prohibits"
  - "MERGE_SHA re-resolved live = 8e0013f2ac7f0361df1ad4893cf0de8f6c773751 — MATCHES the 40-02 cross-check literal"
  - "Plan Task 2 verify defect found pre-push: it asserts `wallets-client-v*` tag count == 2; the measured count is 1"
metrics:
  duration: "~6 min (pre-gate prep + evidence pack)"
  completed: null
  tasks_completed: 0
  tasks_total: 3
  commits: 1
status: awaiting-checkpoint
---

# Phase 40 Plan 03: Tags anotados + Releases públicas — Summary (DETENIDO EN EL GATE D-07(b))

Todo el trabajo automatizable **previo** al push irreversible está hecho y medido en vivo: el
`MERGE_SHA` re-resuelto, la forma de dos padres re-asertada, las seis versiones del árbol mergeado
leídas con el awk del propio `release.yml`, los cuatro strings de tag validados contra el regex del
propio `release.yml`, el digest de `release.yml` idéntico en seis refs, y el toolchain de la Task 3
probado. **Cero tags creados. Cero pushes. Cero Releases.** El plan está detenido en el segundo
checkpoint humano bloqueante (D-07(b)) esperando una respuesta literal del operador.

## Estado del plan

| Task | Tipo | Estado |
|---|---|---|
| 1 — Gate humano bloqueante pre-push de tags (D-07b) | `checkpoint:human-verify` `gate="blocking"` | ⏸️ **DETENIDA — esperando respuesta literal del operador** |
| 2 — Crear/pushear los 4 tags anotados + verificar Releases | `auto` | ⛔ NO INICIADA (bloqueada por Task 1) |
| 3 — Verificación post-publicación desde los wheels públicos | `auto` | ⛔ NO INICIADA (bloqueada por Task 2) |

---

## Prep pre-gate — todo re-medido en vivo, nada heredado de un literal

### `MERGE_SHA` re-resuelto (D-09) — y coincide con el cross-check

```
$ git fetch origin main --tags
$ git rev-parse origin/main
8e0013f2ac7f0361df1ad4893cf0de8f6c773751
```

| Campo | Valor medido |
|---|---|
| **`MERGE_SHA` (re-resuelto en vivo)** | **`8e0013f2ac7f0361df1ad4893cf0de8f6c773751`** |
| Padre 1 (`main` previo) | `20ebb78d9fbc7a0517693c2b9d9fdad733d15667` |
| Padre 2 (head del PR #15) | `ee1813123e0d64f7c5dc02c12ca5e2f8739b8953` |
| Subject | `Merge pull request #15 from gravity-quant/milestone/v1.7-nobj-null-objects` |
| Autor / fecha | `Sebastián de la Fuente <sebadlf@gmail.com>` · `2026-08-30T09:58:08-03:00` |
| Literal registrado en `40-02-SUMMARY.md` | `8e0013f2ac7f0361df1ad4893cf0de8f6c773751` — ✅ **COINCIDE** |

El literal del SUMMARY se usó **sólo como cross-check**; el ancla proviene de `git rev-parse`.

**Prueba de merge real por conteo de padres, no por el subject:**

```
$ git rev-list --parents -n1 origin/main
8e0013f2ac7f0361df1ad4893cf0de8f6c773751 20ebb78d9fbc7a0517693c2b9d9fdad733d15667 ee1813123e0d64f7c5dc02c12ca5e2f8739b8953
$ git rev-list --parents -n1 origin/main | wc -w
3
```

### Versiones del árbol mergeado, leídas con `awk -F'"' '/^version[[:space:]]*=/{print $2; exit}'`

Exactamente la expresión de `release.yml:47` — nunca un parser de TOML ni `importlib.metadata`,
porque cualquier otro lector puede discrepar con el gate que decide si el release publica.

| Paquete | Versión en `origin/main` | Se taguea | Resultado |
|---|---|---|---|
| `market-data-client` | **0.6.0** | ✅ sí | ✅ pasa el version-match |
| `iol-client` | **0.4.0** | ✅ sí | ✅ pasa el version-match |
| `matriz-client` | **0.3.0** | ✅ sí | ✅ pasa el version-match |
| `higyrus-client` | **0.3.0** | ✅ sí (por `A-fold-higyrus`) | ✅ pasa el version-match |
| `ambito-financiero-client` | 0.2.0 | ❌ no (D-01, aditivo) | — |
| `wallets-client` | 0.2.0 | ❌ no (D-01, aditivo) | — |

### Los cuatro strings de tag, validados contra el regex del propio `release.yml:28`

Regex ejercido literalmente en `bash`:
`^([a-z][a-z0-9-]*-client)-v([0-9]+\.[0-9]+\.[0-9]+([.+-][a-zA-Z0-9.+-]+)?)$`

| Tag propuesto | regex | pkg capturado | ver capturada | `packages/<pkg>/` existe | ver del árbol | match |
|---|---|---|---|---|---|---|
| `market-data-client-v0.6.0` | ✅ OK | `market-data-client` | `0.6.0` | ✅ | `0.6.0` | ✅ |
| `iol-client-v0.4.0` | ✅ OK | `iol-client` | `0.4.0` | ✅ | `0.4.0` | ✅ |
| `matriz-client-v0.3.0` | ✅ OK | `matriz-client` | `0.3.0` | ✅ | `0.3.0` | ✅ |
| `higyrus-client-v0.3.0` | ✅ OK | `higyrus-client` | `0.3.0` | ✅ | `0.3.0` | ✅ |

Los cuatro también satisfacen el trigger `on: push: tags: ["*-client-v*"]`.

### Ninguno de los cuatro colisiona con un tag existente

`git ls-remote --tags origin` en vivo, todos los `*-client-v*` publicados:

```
ambito-financiero-client-v0.1.1   higyrus-client-v0.1.1   iol-client-v0.1.1
ambito-financiero-client-v0.2.0   higyrus-client-v0.2.0   iol-client-v0.2.0
                                                          iol-client-v0.3.0
market-data-client-v0.1.0  v0.2.0  v0.3.0  v0.3.1  v0.4.0  v0.5.0
matriz-client-v0.1.1   matriz-client-v0.2.0   wallets-client-v0.2.0
```

Ninguno de los cuatro targets aparece. Reusar `market-data-client-v0.5.0`, `iol-client-v0.3.0`,
`matriz-client-v0.2.0` o `higyrus-client-v0.2.0` habría sido rechazado de plano y `release.yml`
nunca habría corrido.

### Assets esperados, derivados y cross-checkeados contra cuatro Releases previas

Convención confirmada **empíricamente** con `gh release view <prior-tag> --json assets`, no asumida:

| Release previa | Assets reales |
|---|---|
| `market-data-client-v0.5.0` | `market_data_client-0.5.0-py3-none-any.whl`, `market_data_client-0.5.0.tar.gz` |
| `iol-client-v0.3.0` | `iol_client-0.3.0-py3-none-any.whl`, `iol_client-0.3.0.tar.gz` |
| `matriz-client-v0.2.0` | `matriz_client-0.2.0-py3-none-any.whl`, `matriz_client-0.2.0.tar.gz` |
| `higyrus-client-v0.2.0` | `higyrus_client-0.2.0-py3-none-any.whl`, `higyrus_client-0.2.0.tar.gz` |

Por lo tanto los assets a exigir en la Task 2 (e) y las URLs a instalar en la Task 3 (b) son:

| Tag | Wheel | Sdist |
|---|---|---|
| `market-data-client-v0.6.0` | `market_data_client-0.6.0-py3-none-any.whl` | `market_data_client-0.6.0.tar.gz` |
| `iol-client-v0.4.0` | `iol_client-0.4.0-py3-none-any.whl` | `iol_client-0.4.0.tar.gz` |
| `matriz-client-v0.3.0` | `matriz_client-0.3.0-py3-none-any.whl` | `matriz_client-0.3.0.tar.gz` |
| `higyrus-client-v0.3.0` | `higyrus_client-0.3.0-py3-none-any.whl` | `higyrus_client-0.3.0.tar.gz` |

### Inmutabilidad de `release.yml` — forma CORREGIDA (sha256), no la forma rota de la Phase 34

```
HEAD                        7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
origin/main                 7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
iol-client-v0.3.0           7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
market-data-client-v0.5.0   7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
matriz-client-v0.2.0        7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
higyrus-client-v0.2.0       7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
```

`sort -u` → **1 línea**. `release.yml` es byte-idéntico en los seis refs medibles hoy; los cuatro
tags nuevos se sumarán a esta comparación en la Task 2 (f) y necesariamente heredarán el mismo blob,
porque anclan `origin/main`.

`git diff --name-only origin/main...HEAD -- .github/workflows` → **0 líneas**. Ningún workflow fue
editado por esta fase. No se usó la forma `git diff --name-only <prior-release-tag>..HEAD` de la
Phase 34, que es stale-by-construction y falló tres veces (RESEARCH P2 / STATE.md:389).

### Toolchain de la Task 3, probado por adelantado (reversible, fuera del repo)

| Comprobación | Resultado |
|---|---|
| `uv --version` | `uv 0.11.3` |
| `python3 --version` (del sistema) | **`Python 3.9.6`** — confirma RESEARCH P10: `--python 3.12` es load-bearing, no cosmético |
| `uv venv --python 3.12` en un `mktemp -d` | ✅ OK → `Python 3.12.13` |
| Repo público (URLs de Release resuelven sin auth) | ✅ `gravity-quant/market-libs`, `private=false` |

El directorio temporal fue borrado. Ningún archivo del repo fue tocado.

### `gh` y remote

| Comprobación | Resultado |
|---|---|
| `gh auth status` | ✅ exit 0, cuenta `sebadlf`, scopes `gist, read:org, repo, workflow`. **El token nunca se imprimió** (`gh` lo redacta) |
| `git remote -v` | `origin git@github.com:gravity-quant/market-libs.git` (SSH, fetch+push) |
| `git status --porcelain` | ✅ vacío |

---

## Estado del gate D-07(b): **PENDIENTE — sin respuesta del operador**

`.planning/config.json` tiene `workflow.auto_advance: true`, `workflow._auto_chain_active: true` y
`mode: yolo`. **Ninguno de los tres satisface este gate.** No se auto-aprobó, no se infirió del
silencio, no se derivó de una respuesta ambigua, y el agente no se la auto-emitió. La corrida se
detuvo y devolvió el control con el evidence pack completo.

Este es el **segundo y último** gate bloqueante de la fase, **independiente** del gate de merge
D-07(a) que el plan 40-02 ya ejerció y resolvió con un `approved` literal. Los dos **no** se
colapsaron ni se presentaron juntos.

### Verificación de que nada irreversible ocurrió

Bloque `<automated>` de la Task 1, corrido verbatim:

```
PASS — merge intact, no tag created or pushed before the operator reply
```

| Tag de la ronda | `git tag -l` (local) | `git ls-remote --tags origin` |
|---|---|---|
| `market-data-client-v0.6.0` | vacío ✅ | vacío ✅ |
| `iol-client-v0.4.0` | vacío ✅ | vacío ✅ |
| `matriz-client-v0.3.0` | vacío ✅ | vacío ✅ |
| `higyrus-client-v0.3.0` | vacío ✅ | vacío ✅ |

Cero `git tag`, cero `git push`, cero `gh release`. Ninguna corrida de `release.yml` disparada.

---

## Deviations from Plan

### 1. [Rule 4 — conflicto entre la instrucción del orquestador y la Task 1 del plan] Los 4 tags NO se crearon localmente

- **Found during:** prep de la Task 1, antes de ejecutar nada.
- **Conflicto:** el prompt del orquestador incluye como criterio de éxito *"4 annotated tags created
  locally on the live re-resolved merge SHA — NOT pushed yet"*. La Task 1 del PLAN lo **prohíbe
  explícitamente**, en tres lugares independientes:
  - `<acceptance_criteria>`: *"No `git tag` and no `git push` command was executed before the
    operator's reply"*.
  - `<done>`: *"at the moment of the reply no tag of this round existed locally or on `origin`"*.
  - `<verify><automated>`: aborta con `TAG CREATED BEFORE THE GATE: $T` y exit 1 si el tag existe.
- **Resolución: se siguió el PLAN.** Razones, en orden de peso:
  1. **Crear los tags ahora agranda el riesgo concreto que la fase entera prohíbe.** Hay **22 tags
     locales** (16 de paquete + `v1.1`…`v1.6`), y la prohibición central del plan es que un
     `git push --tags` publique lo que esté stale. Si el operador responde `abort`, quedarían **4
     tags locales huérfanos más** apuntando a un merge commit, en el mismo namespace que un
     `--tags` accidental publicaría. Crearlos ahora no compra nada y suma superficie de fallo.
  2. **No aporta valor.** D-09 obliga al agente de continuación a **re-resolver** `MERGE_SHA` en
     vivo de todos modos; los tags que crease ahora tendrían que re-verificarse contra ese valor.
     `git tag -a` es una operación de un segundo.
  3. **Rompería la auditabilidad del gate.** El `<automated>` de la Task 1 es precisamente lo que
     un agente de continuación corre para probar que nada irreversible pasó antes de la aprobación.
     Con los tags creados, ese bloque falla y la evidencia del gate se pierde.
- **Qué se hizo en su lugar:** *todo* lo demás que un agente puede hacer sin tocar el namespace de
  tags — re-resolución del SHA, forma de dos padres, seis versiones bajo el awk del pipeline, los
  cuatro strings validados contra el regex del pipeline, colisión de tags descartada contra
  `origin`, assets esperados cross-checkeados contra cuatro Releases reales, digest de `release.yml`
  en seis refs, y el toolchain de la Task 3 probado end-to-end.
- **Comandos exactos, listos para el agente de continuación** (ver § Handoff).
- **Commit:** ninguno (no se modificó ningún archivo).

### 2. [Rule 1 — defecto de aserción en la Task 2 del plan, detectado ANTES del push] El conteo de tags de `wallets-client` es 1, no 2

- **Found during:** prep de la Task 1, al inventariar el namespace de tags.
- **Aserción del plan** (Task 2 `<automated>`, penúltima cláusula):
  `test "$(git tag -l 'wallets-client-v*' | wc -l | tr -d ' ')" = "2"`.
- **Medido:** `wallets-client` tiene **exactamente 1** tag, local y remoto — `wallets-client-v0.2.0`.
  (`ambito-financiero-client` sí tiene 2: `v0.1.1` y `v0.2.0`, así que esa mitad de la aserción es
  correcta.) La cifra "15 stale local package tags" que el plan repite también está desfasada: el
  conteo real es **16**.
- **Impacto y por qué importa surfacearlo AHORA:** el `<automated>` de la Task 2 corre **después**
  del push irreversible. Tal como está escrito devolverá un **falso FAIL** con las cuatro Releases
  ya públicas. El riesgo real no es la aserción en sí: es que un agente que vea `FAIL` justo después
  de publicar intente "arreglarlo" borrando o re-apuntando tags, que es una **prohibición explícita**
  del plan. Detectarlo antes del gate convierte un susto post-publicación en una nota a pie de página.
- **Fix propuesto (NO aplicado — el plan es un artefacto aprobado y no se edita a mitad de ejecución):**
  la intención de la cláusula es *"el conteo de tags de los paquetes sin cambios no varió"*. La forma
  correcta es fijar el baseline medido: `ambito-financiero-client-v*` == `2` y `wallets-client-v*`
  == `1`. Las dos cláusulas que de verdad protegen contra publicar un paquete sin cambios —
  `test -z "$(git tag -l 'ambito-financiero-client-v0.3.0')"` y
  `test -z "$(git tag -l 'wallets-client-v0.3.0')"` — están **correctas** y hoy pasan.
- **Commit:** ninguno.

---

## Handoff al agente de continuación (post-aprobación)

Ejecutar **sólo** con un `approved` literal del operador. Con cualquier otra respuesta: parar,
`main` queda mergeado y nada se publica.

**Paso 0 — re-resolver, no confiar en el literal de arriba:**

```bash
git fetch origin main --tags
MERGE_SHA=$(git rev-parse origin/main)
test "$(git rev-list --parents -n1 "$MERGE_SHA" | wc -w | tr -d ' ')" -eq 3
```

**Paso 1 — crear los cuatro tags ANOTADOS sobre `$MERGE_SHA` explícito** (nunca `git tag <name>` sin
commit-ish, que taguearía el HEAD de la branch):

```bash
git tag -a market-data-client-v0.6.0 "$MERGE_SHA" -m "market-data-client v0.6.0 — market_data pasa a Null Object tipado MarketDataEntries (PUB-NOBJ-01)"
git tag -a iol-client-v0.4.0        "$MERGE_SHA" -m "iol-client v0.4.0 — Cotizacion.puntas y Titulo.puntas pierden | None (PUB-NOBJ-01)"
git tag -a matriz-client-v0.3.0     "$MERGE_SHA" -m "matriz-client v0.3.0 — cuatro retipados de modelo + fix de envelope-unwrap (PUB-NOBJ-01)"
git tag -a higyrus-client-v0.3.0    "$MERGE_SHA" -m "higyrus-client v0.3.0 — get_health devuelve Health tipado (PUB-NOBJ-01)"
```

**Paso 2 — pushear UNO POR UNO, por nombre. NUNCA `--tags`, NUNCA `--force`:**

```bash
git push origin market-data-client-v0.6.0
git push origin iol-client-v0.4.0
git push origin matriz-client-v0.3.0
git push origin higyrus-client-v0.3.0
```

**Paso 3** — `gh run watch` sobre **cada** corrida individualmente (4 corridas independientes;
`concurrency.group` es `release-${{ github.ref }}`, o sea por tag: ni serializan ni se cancelan).
Registrar los 4 run IDs. Verde en una no dice nada de las otras (RESEARCH P9).

**Paso 4** — verificar los assets de cada Release contra la tabla de filenames de arriba.

**Paso 5** — Task 3, con las URLs base
`https://github.com/gravity-quant/market-libs/releases/download/<tag>/<wheel>`.

**Ojo con la Deviation 2** al correr el `<automated>` de la Task 2: la cláusula de
`wallets-client-v*` == `2` dará FAIL espurio. **No** borrar ni re-apuntar ningún tag por eso.

## Known Stubs

Ninguno. Este plan no produce código de producto — sólo operaciones de git/gh y un artefacto de
planning.

## Threat Flags

Ninguna superficie de seguridad nueva. Estado de las mitigaciones del `<threat_model>` en este punto:

- **T-40-17** (push irreversible / Releases públicas) — **activa y sosteniéndose**: la corrida se
  detuvo en el checkpoint bloqueante con `auto_advance: true`, `_auto_chain_active: true` y
  `mode: yolo` los tres activos, y ninguno lo satisfizo.
- **T-40-18** (tag sobre el HEAD de branch) — **pre-mitigada**: `MERGE_SHA` re-resuelto en vivo y
  cross-checkeado; el handoff pasa `$MERGE_SHA` explícito a cada `git tag -a`.
- **T-40-19** (`git push --tags`) — **pre-mitigada**: hazard cuantificado (22 tags locales) y el
  handoff especifica un push por nombre, uno por comando. Reforzada al **no** crear los 4 tags
  todavía (Deviation 1).
- **T-40-20** (tag lightweight o string inválido) — **pre-mitigada**: los cuatro strings ejercidos
  contra el regex literal de `release.yml:28` y contra el awk de `release.yml:47`.
- **T-40-21** (patchear el workflow / borrar un tag para reintentar) — **pre-mitigada**: digest de
  `release.yml` idéntico en 6 refs; la Deviation 2 desactiva de antemano la tentación de "arreglar"
  un FAIL post-publicación borrando tags.
- **T-40-22** (slopsquat en el install post-publicación) — **pre-mitigada**: tabla de URLs completas
  derivada de assets reales; cero installs por nombre pelado.
- **T-40-25** (fuga de credenciales) — **mitigada**: `gh auth status` en vez de imprimir el token;
  nada se echoeó.

## Self-Check: PASSED

- `.planning/phases/40-releases-breaking-coordinados/40-03-SUMMARY.md` — existe en disco.
- `origin/main` == `8e0013f2ac7f0361df1ad4893cf0de8f6c773751`, con dos padres — verificado por
  `git rev-list --parents -n1` → 3 campos.
- Los cuatro tags de la ronda: `git tag -l` vacío y `git ls-remote --tags origin` vacío.
- `release.yml` sha256 `7109ff0b…` idéntico en los 6 refs medidos.
- Árbol de trabajo limpio.
- Cero corridas de `release.yml` disparadas por esta sesión.
