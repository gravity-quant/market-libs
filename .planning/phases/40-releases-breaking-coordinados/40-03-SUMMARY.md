---
phase: 40-releases-breaking-coordinados
plan: 03
subsystem: release-mechanics
tags: [release, git-tag, github-release, checkpoint, blocking-human, irreversible, post-publish-verification]
requires:
  - "plan 40-02 complete: PR #15 MERGED, `origin/main` at a real two-parent merge commit"
  - "authenticated `gh` CLI with `repo` + `workflow` scopes"
  - "operator go/no-go at the D-07(b) pre-tag-push gate — RESOLVED: literal reply `approved`"
provides:
  - "git-tag:market-data-client-v0.6.0 — annotated, on the re-resolved merge SHA, pushed to origin"
  - "git-tag:iol-client-v0.4.0 — annotated, on the re-resolved merge SHA, pushed to origin"
  - "git-tag:matriz-client-v0.3.0 — annotated, on the re-resolved merge SHA, pushed to origin"
  - "git-tag:higyrus-client-v0.3.0 — annotated, on the re-resolved merge SHA, pushed to origin"
  - "gh-release:market-data-client-v0.6.0 — public Release with wheel + sdist"
  - "gh-release:iol-client-v0.4.0 — public Release with wheel + sdist"
  - "gh-release:matriz-client-v0.3.0 — public Release with wheel + sdist"
  - "gh-release:higyrus-client-v0.3.0 — public Release with wheel + sdist"
  - "post-publish consumability proof: 4 public wheels installed into a throwaway py3.12 venv, deep chains green against the INSTALLED distributions"
affects:
  - "github.com/gravity-quant/market-libs — 4 new public Releases (permanent)"
  - "PUB-NOBJ-01 — publication actually happened; requirement moves Pending → Complete"
  - "milestone v1.7 — Phase 40 closed, milestone content fully published"
tech-stack:
  added: []
  patterns:
    - "re-resolve the tag anchor live from `git rev-parse origin/main`; treat the SUMMARY literal as a cross-check, never as the source"
    - "prove a merge is real by parent COUNT (3 whitespace fields), never by the subject line"
    - "push tags one BY NAME per command; never `git push --tags` when stale local tags exist"
    - "watch N concurrent release runs individually — `concurrency.group` is per-`github.ref`, so one green says nothing about the others"
    - "workflow immutability asserted by sha256 identity across refs, NOT by the Phase 34 tag-baseline diff form"
    - "post-publish consumability proven by installing the PUBLIC wheel URL into a throwaway interpreter and asserting `__file__` lands in venv site-packages"
key-files:
  created:
    - .planning/phases/40-releases-breaking-coordinados/40-03-SUMMARY.md
  modified:
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md
decisions:
  - "D-07(b) satisfied by a literal operator reply `approved`; recorded verbatim, NOT auto-issued despite auto_advance + yolo both active"
  - "MERGE_SHA re-resolved live = 8e0013f2ac7f0361df1ad4893cf0de8f6c773751 — MATCHES the 40-02 cross-check literal"
  - "All 4 tags anchor the SAME merge commit; all 4 are annotated (`git cat-file -t` == `tag`)"
  - "The plan's stale `wallets-client-v*` count == 2 clause was OVERRIDDEN, not satisfied — real count is 1 and is unchanged from pre-phase; no tag was created or deleted to make it pass"
  - "Two verify blocks failed under zsh due to absent word-splitting, not due to any release defect; re-run verbatim under bash and passed"
  - "OQ-3 standing: no in-repo release-memory file exists to refresh; this plan authors no memory task"
metrics:
  duration: "~4 min (re-verify + tag + push + 4 runs + post-publish install)"
  completed: 2026-08-30
  tasks_completed: 3
  tasks_total: 3
  commits: 1
status: complete
---

# Phase 40 Plan 03: Tags anotados + Releases públicas + verificación post-publicación — Summary

Los cuatro tags anotados fueron creados sobre el merge commit **re-resuelto en vivo**, pusheados
**uno por uno por nombre**, sus cuatro corridas de `release.yml` fueron observadas
**individualmente** hasta `success`, las cuatro Releases públicas llevan wheel + sdist con los
filenames exactos, y —lo que convierte "el pipeline dio verde" en "un consumidor puede usar esto"—
los cuatro wheels fueron instalados **desde sus URLs públicas** en un intérprete Python 3.12
descartable fuera del repo, donde las cadenas profundas corren en verde contra la **distribución
instalada**. `release.yml` no cambió un solo byte: mismo sha256 en **diez** refs.

## Estado del plan

| Task | Tipo | Estado |
|---|---|---|
| 1 — Gate humano bloqueante pre-push de tags (D-07b) | `checkpoint:human-verify` `gate="blocking"` | ✅ RESUELTA — `approved` literal del operador |
| 2 — Crear/pushear los 4 tags anotados + verificar Releases | `auto` | ✅ COMPLETA |
| 3 — Verificación post-publicación desde los wheels públicos | `auto` | ✅ COMPLETA |

---

## Task 1 — Gate humano bloqueante D-07(b): RESUELTO con un `approved` literal

### Respuesta del operador, verbatim

> approved

- **Timestamp de la resolución:** 2026-08-30
- **Canal:** respuesta directa del operador humano al checkpoint bloqueante, vía `AskUserQuestion`.
- **Explícitamente NO auto-emitida.** `.planning/config.json` tiene `workflow.auto_advance: true`,
  `workflow._auto_chain_active: true` y `mode: yolo` — **los tres activos, ninguno la satisfizo**.
  No se infirió del silencio, no se derivó de una respuesta ambigua, no fue una selección por
  defecto y el agente no se la auto-emitió.
- **Segundo e independiente** respecto del gate de merge D-07(a), que el plan 40-02 ya ejerció por
  separado con su propio `approved` literal. Los dos **no** se colapsaron: ocurrieron en planes
  distintos, en corridas distintas, sobre operaciones irreversibles de tipo distinto (merge vs
  publicación).
- **Una sola aprobación cubrió los cuatro tags** (D-09). El gate **no** se dividió en uno por
  paquete; no se volvió a preguntar por el segundo, tercero ni cuarto tag.

### Re-verificación en vivo ANTES de tagear (agente de continuación fresco)

Esta corrida es un agente de continuación **fresco**. Nada se heredó de la corrida previa: todo se
volvió a medir contra el estado vivo antes de tocar el namespace de tags.

| Re-verificación | Resultado |
|---|---|
| `git fetch origin main --tags` | ✅ |
| `git rev-parse origin/main` | ✅ `8e0013f2ac7f0361df1ad4893cf0de8f6c773751` |
| Cross-check contra el literal de `40-02-SUMMARY.md` | ✅ **COINCIDE** (el literal se usó sólo como cross-check) |
| `git rev-list --parents -n1 origin/main \| wc -w` | ✅ **3** — commit + exactamente DOS padres |
| Padre 1 / Padre 2 | `20ebb78d9fbc7a0517693c2b9d9fdad733d15667` / `ee1813123e0d64f7c5dc02c12ca5e2f8739b8953` |
| Subject | `Merge pull request #15 from gravity-quant/milestone/v1.7-nobj-null-objects` |
| Los 4 tags de la ronda, `git tag -l` (local) | ✅ los cuatro **vacíos** |
| Los 4 tags de la ronda, `git ls-remote --tags origin` | ✅ los cuatro **vacíos** |
| `git status --porcelain` | ✅ vacío |
| `gh auth status` | ✅ exit 0, cuenta `sebadlf`, scopes `gist, read:org, repo, workflow`. **El token nunca se imprimió** |

**Bloque `<automated>` de la Task 1, corrido verbatim:**

```
PASS — merge intact, no tag created or pushed before the operator reply
```

Confirma lo esencial del gate: en el momento de la respuesta del operador **no existía ningún tag de
esta ronda, ni local ni en `origin`**, y el merge seguía intacto.

### Versiones del árbol mergeado, leídas con el awk de `release.yml:47`

`awk -F'"' '/^version[[:space:]]*=/{print $2; exit}'` — la expresión del propio pipeline, nunca un
parser de TOML ni `importlib.metadata`, porque cualquier otro lector puede discrepar con el gate que
decide si el release publica.

| Paquete | Versión en `origin/main` | Se taguea | Version-match |
|---|---|---|---|
| `market-data-client` | **0.6.0** | ✅ sí | ✅ pasa |
| `iol-client` | **0.4.0** | ✅ sí | ✅ pasa |
| `matriz-client` | **0.3.0** | ✅ sí | ✅ pasa |
| `higyrus-client` | **0.3.0** | ✅ sí (`A-fold-higyrus`) | ✅ pasa |
| `ambito-financiero-client` | 0.2.0 | ❌ no (D-01, aditivo) | — |
| `wallets-client` | 0.2.0 | ❌ no (D-01, aditivo) | — |

---

## Task 2 — Cuatro tags anotados, pusheados por nombre, cuatro Releases verificadas

### Los cuatro tags, creados sobre `$MERGE_SHA` explícito

Nunca `git tag <name>` sin commit-ish (que habría tagueado el HEAD de la branch, que en esta sesión
era `61c4c9c` en `milestone/v1.7-nobj-null-objects` — **fuera** del merge). El SHA se pasó explícito
a cada `git tag -a`.

| Tag | `git cat-file -t` | Anchor (`git rev-list -n1`) | Mensaje |
|---|---|---|---|
| `market-data-client-v0.6.0` | **`tag`** ✅ | `8e0013f2ac7f…` ✅ | `market-data-client v0.6.0 — market_data pasa a Null Object tipado MarketDataEntries (PUB-NOBJ-01)` |
| `iol-client-v0.4.0` | **`tag`** ✅ | `8e0013f2ac7f…` ✅ | `iol-client v0.4.0 — Cotizacion.puntas y Titulo.puntas pierden \| None (PUB-NOBJ-01)` |
| `matriz-client-v0.3.0` | **`tag`** ✅ | `8e0013f2ac7f…` ✅ | `matriz-client v0.3.0 — cuatro retipados de modelo + fix de envelope-unwrap (PUB-NOBJ-01)` |
| `higyrus-client-v0.3.0` | **`tag`** ✅ | `8e0013f2ac7f…` ✅ | `higyrus-client v0.3.0 — get_health devuelve Health tipado (PUB-NOBJ-01)` |

Los cuatro son **anotados** (`tag`, no `commit`), tagger `sebadlf <sebadlf@gmail.com>`, y los cuatro
comparten **el mismo anchor**: el merge commit de dos padres. Todos siguen el shape de mensaje
`<pkg> v<X.Y.Z> — <headline> (PUB-NOBJ-01)`.

### El push — uno por nombre, cuatro comandos

```
git push origin market-data-client-v0.6.0   →  * [new tag]  market-data-client-v0.6.0
git push origin iol-client-v0.4.0           →  * [new tag]  iol-client-v0.4.0
git push origin matriz-client-v0.3.0        →  * [new tag]  matriz-client-v0.3.0
git push origin higyrus-client-v0.3.0       →  * [new tag]  higyrus-client-v0.3.0
```

**Cero `git push --tags`** en toda la fase, y cero `--force` de cualquier clase. El hazard es
concreto y medido: hay **20 tags de paquete locales** más los milestone `v1.1`…`v1.6`; un push
mayorista habría publicado lo que estuviera stale. Ningún tag existente fue borrado ni re-apuntado,
y ninguna Release fue borrada.

### Las cuatro corridas de `release.yml` — observadas INDIVIDUALMENTE

Cuatro tags sobre un mismo commit dispararon **cuatro corridas independientes**.
`concurrency.group` es `release-${{ github.ref }}` (por tag), así que ni serializan ni se cancelan.
Verde en una no dice nada de las otras (RESEARCH P9), así que cada una se verificó por separado:

| Run ID | Tag (`headBranch`) | Conclusión | Creada | Terminada | URL |
|---|---|---|---|---|---|
| `33315928885` | `market-data-client-v0.6.0` | ✅ **success** | 14:05:50Z | 14:06:07Z | [run](https://github.com/gravity-quant/market-libs/actions/runs/33315928885) |
| `33315932932` | `iol-client-v0.4.0` | ✅ **success** | 14:05:55Z | 14:06:08Z | [run](https://github.com/gravity-quant/market-libs/actions/runs/33315932932) |
| `33315937584` | `matriz-client-v0.3.0` | ✅ **success** | 14:06:01Z | 14:06:15Z | [run](https://github.com/gravity-quant/market-libs/actions/runs/33315937584) |
| `33315942414` | `higyrus-client-v0.3.0` | ✅ **success** | 14:06:07Z | 14:06:26Z | [run](https://github.com/gravity-quant/market-libs/actions/runs/33315942414) |

Las cuatro solaparon en el tiempo, confirmando empíricamente que el `concurrency.group` per-tag no
las serializa. `gh run watch 33315942414 --exit-status` sobre la última. **Ninguna corrida fue
re-lanzada, ningún workflow fue editado, ningún tag fue borrado.**

### Las cuatro Releases públicas y sus assets, por filename exacto

| Release | Wheel | Sdist | draft | prerelease |
|---|---|---|---|---|
| [`market-data-client-v0.6.0`](https://github.com/gravity-quant/market-libs/releases/tag/market-data-client-v0.6.0) | `market_data_client-0.6.0-py3-none-any.whl` (96 778 B) | `market_data_client-0.6.0.tar.gz` (202 737 B) | `false` | `false` |
| [`iol-client-v0.4.0`](https://github.com/gravity-quant/market-libs/releases/tag/iol-client-v0.4.0) | `iol_client-0.4.0-py3-none-any.whl` (65 815 B) | `iol_client-0.4.0.tar.gz` (122 544 B) | `false` | `false` |
| [`matriz-client-v0.3.0`](https://github.com/gravity-quant/market-libs/releases/tag/matriz-client-v0.3.0) | `matriz_client-0.3.0-py3-none-any.whl` (94 210 B) | `matriz_client-0.3.0.tar.gz` (773 573 B) | `false` | `false` |
| [`higyrus-client-v0.3.0`](https://github.com/gravity-quant/market-libs/releases/tag/higyrus-client-v0.3.0) | `higyrus_client-0.3.0-py3-none-any.whl` (59 616 B) | `higyrus_client-0.3.0.tar.gz` (1 618 221 B) | `false` | `false` |

Los ocho filenames coinciden **exactamente** con los derivados en el evidence pack pre-gate a partir
de cuatro Releases previas reales — la convención fue confirmada empíricamente, no asumida.

### Inmutabilidad de `release.yml` — forma CORREGIDA (sha256), no la forma rota de la Phase 34

sha256 de `.github/workflows/release.yml` en **diez** refs, ahora incluyendo los cuatro tags nuevos:

```
HEAD                        7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
origin/main                 7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
iol-client-v0.3.0           7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
market-data-client-v0.5.0   7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
matriz-client-v0.2.0        7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
higyrus-client-v0.2.0       7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
market-data-client-v0.6.0   7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113   ← nuevo
iol-client-v0.4.0           7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113   ← nuevo
matriz-client-v0.3.0        7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113   ← nuevo
higyrus-client-v0.3.0       7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113   ← nuevo
```

`sort -u` → **1 línea**. `release.yml` es byte-idéntico en los diez refs; **sexta reutilización sin
editar un solo byte**.

`git diff --name-only origin/main...HEAD -- .github/workflows` → **0 líneas**.

No se usó la forma `git diff --name-only <prior-release-tag>..HEAD -- .github/workflows` de la
Phase 34, que es stale-by-construction (`ci.yml` difiere legítimamente entre refs por las Fases
36/37/39) y falló tres veces durante la ejecución de aquella fase (RESEARCH P2 / STATE.md:389).

### El negativo: ámbito y wallets no fueron publicados

| Paquete | Tags locales | Tags en `origin` | Tag nuevo de esta ronda |
|---|---|---|---|
| `ambito-financiero-client` | `v0.1.1`, `v0.2.0` (**2**) | idem | ❌ ninguno |
| `wallets-client` | `v0.2.0` (**1**) | idem | ❌ ninguno |

`git tag -l 'ambito-financiero-client-v0.3.0'` → vacío. `git tag -l 'wallets-client-v0.3.0'` →
vacío. Ambos conteos **idénticos al baseline pre-fase**: no se creó ni se borró ningún tag de estos
dos paquetes.

---

## Task 3 — Verificación post-publicación desde los wheels PÚBLICOS

Esta es la task sin precedente en los planes de este repositorio: la Phase 34 hizo el trabajo
equivalente en `34-UAT.md`, nunca como task de plan.

### El intérprete descartable

| Comprobación | Valor |
|---|---|
| `WORK` | `/var/folders/vk/…/T/tmp.awxDPV4gd0` — **fuera del repo**, verificado por prefijo |
| `uv --version` | `uv 0.11.3` |
| `python3 --version` (sistema) | **`Python 3.9.6`** — confirma RESEARCH P10: `--python 3.12` es **load-bearing**, no cosmético; sin él la resolución falla y es fácil malinterpretarlo como defecto de packaging |
| `uv venv --python 3.12` | ✅ → **`Python 3.12.13`** |
| Workspace agregado al venv | ❌ **no** — sólo los cuatro wheels y sus deps |

### Las cuatro URLs públicas instaladas (nunca por nombre pelado)

```
https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.6.0/market_data_client-0.6.0-py3-none-any.whl
https://github.com/gravity-quant/market-libs/releases/download/iol-client-v0.4.0/iol_client-0.4.0-py3-none-any.whl
https://github.com/gravity-quant/market-libs/releases/download/matriz-client-v0.3.0/matriz_client-0.3.0-py3-none-any.whl
https://github.com/gravity-quant/market-libs/releases/download/higyrus-client-v0.3.0/higyrus_client-0.3.0-py3-none-any.whl
```

Descargas **sin autenticación** (repo público) — ningún token intervino ni se imprimió. `uv` reportó
cada una resuelta explícitamente desde su URL:

```
+ higyrus-client==0.3.0     (from https://…/higyrus-client-v0.3.0/higyrus_client-0.3.0-py3-none-any.whl)
+ iol-client==0.4.0         (from https://…/iol-client-v0.4.0/iol_client-0.4.0-py3-none-any.whl)
+ market-data-client==0.6.0 (from https://…/market-data-client-v0.6.0/market_data_client-0.6.0-py3-none-any.whl)
+ matriz-client==0.3.0      (from https://…/matriz-client-v0.3.0/matriz_client-0.3.0-py3-none-any.whl)
```

Deps transitivas resueltas: `anyio 4.14.2`, `certifi 2026.7.22`, `h11 0.16.0`, `httpcore 1.0.9`,
`httpx 0.28.1`, `idna 3.19`, `platformdirs 4.11.5`, `python-dotenv 1.2.3`, `tenacity 9.1.4`,
`typing-extensions 4.16.0`, `websocket-client 1.9.1` — 15 paquetes en total.

**Cero installs por nombre pelado.** Ninguno de los seis paquetes está en PyPI, y un
`uv add market-data-client` resolvería otro proyecto si ese nombre apareciera alguna vez allí —
riesgo que `packages/market-data-client/README.md:38-40` ya documenta.

### Salida literal del script de cadenas profundas

```
interpreter: 3.12.13
prefix: /var/folders/vk/py62nz414svgr57b7wnh5_780000gn/T/tmp.awxDPV4gd0/.venv
  market_data_client.__file__ = …/tmp.awxDPV4gd0/.venv/lib/python3.12/site-packages/market_data_client/__init__.py
market-data-client 0.6.0 OK
  iol_client.__file__ = …/tmp.awxDPV4gd0/.venv/lib/python3.12/site-packages/iol_client/__init__.py
iol-client 0.4.0 OK
  matriz_client.__file__ = …/tmp.awxDPV4gd0/.venv/lib/python3.12/site-packages/matriz_client/__init__.py
matriz-client 0.3.0 OK
  higyrus_client.__file__ = …/tmp.awxDPV4gd0/.venv/lib/python3.12/site-packages/higyrus_client/__init__.py
higyrus-client 0.3.0 OK
ambito_financiero_client / wallets_client absent — OK
POST-PUBLISH VERIFICATION PASS
EXIT=0
```

**Los cuatro `__file__` caen dentro del `site-packages` del venv descartable.** Ésa es la prueba
dura de que las cadenas corrieron contra la **distribución instalada** y no contra el checkout del
repo — un refuerzo que el plan no pedía explícitamente pero que es exactamente lo que D-11 quiere
garantizar.

### `__version__` e `importlib.metadata`, ambos asertados

| Paquete | `__version__` | `importlib.metadata.version()` | Acuerdo |
|---|---|---|---|
| `market_data_client` | `0.6.0` | `0.6.0` | ✅ |
| `iol_client` | `0.4.0` | `0.4.0` | ✅ |
| `matriz_client` | **`0.3.0`** | `0.3.0` | ✅ |
| `higyrus_client` | `0.3.0` | `0.3.0` | ✅ |

Que ambos coincidan es lo que realmente prueba que **el código y la metadata del wheel viajaron
sincronizados**.

> **`matriz_client.__version__` es un sitio NUEVO.** matriz-client **no tenía `__version__`** antes
> de esta fase (D-04 / OQ-4); el plan 40-01 lo agregó. Que resuelva es un **hecho nuevo**, no una
> baseline de regresión.

### Las cadenas profundas, por paquete

| Paquete | Aserción (todas vía `from_api(None)` — sin red, sin credenciales) | Resultado |
|---|---|---|
| market-data 0.6.0 | `MarketDataSnapshot.from_api(None).market_data.last.price is None` — la cadena profunda **sin un solo guard de `None`** | ✅ |
| market-data 0.6.0 | `.market_data.bids == []` | ✅ |
| market-data 0.6.0 | `not .market_data` — el Null Object falsy que reemplaza a `is None` | ✅ |
| market-data 0.6.0 | `.entries == []` (nunca `None`) | ✅ |
| iol 0.4.0 | `Titulo.from_api(None).puntas.precioCompra == 0.0` — lo que antes exigía `titulo.puntas is None` | ✅ |
| iol 0.4.0 | `Cotizacion.from_api(None).puntas == []` — lo que antes exigía `quote.puntas or []` | ✅ |
| matriz 0.3.0 | `AccountReport.from_api(None).portfolio is None` (era `dict[str, Any]`, ahora `float \| None`) | ✅ |
| matriz 0.3.0 | `AccountReport.from_api(None).detailedAccountReports == {}` | ✅ |
| matriz 0.3.0 | `InstrumentDetail.from_api(None).tickPriceRanges == {}` | ✅ |
| matriz 0.3.0 | `DetailedPosition.from_api(None).report == {}` | ✅ |
| matriz 0.3.0 | alias views: snapshot `.bids == []` y `.last.price is None` | ✅ |
| higyrus 0.3.0 | `Health.from_api(None).status == ""` — lo que antes era `health["status"]` | ✅ |

### El negativo, asertado dentro del venv

`ambito_financiero_client` y `wallets_client` → `ModuleNotFoundError` en ambos. No fueron
instalados y no fueron publicados en esta ronda; no hay Release desde la cual instalarlos por
encima de `0.2.0`.

### Limpieza

Los dos directorios temporales (`tmp.awxDPV4gd0` y el `tmp.U9c2JfFMVw` del primer intento) fueron
borrados; `ls` confirma `No such file or directory` en ambos.
`git status --porcelain` → **vacío**. **Ningún archivo del repo fue modificado por esta task.**

---

## Deviations from Plan

### 1. [Rule 1 — defecto de aserción del plan, confirmado en ejecución] La cláusula `wallets-client-v*` == 2 es STALE; se OVERRIDEÓ, no se "arregló"

- **Found during:** Task 2, al correr el `<automated>` del plan (ya había sido detectada y
  surfaceada de antemano en el evidence pack pre-gate — ver `Deviation 2` de la corrida anterior).
- **Aserción del plan** (Task 2 `<automated>`, penúltima cláusula):
  `test "$(git tag -l 'wallets-client-v*' | wc -l | tr -d ' ')" = "2"`.
- **Medido:** `wallets-client` tiene **exactamente 1** tag, local y remoto: `wallets-client-v0.2.0`.
  (`ambito-financiero-client` sí tiene 2 — `v0.1.1` y `v0.2.0` — así que **esa mitad de la aserción
  es correcta y pasó**.) La cifra "15 stale local package tags" que el plan repite también estaba
  desfasada: el conteo real hoy es **20** (16 previos + los 4 de esta ronda).
- **Resolución: se overrideó esta cláusula específica, con justificación, y NO se tocó ningún tag.**
  La intención real de la cláusula es *"el conteo de tags de los paquetes sin cambios no varió"*, y
  esa intención **se cumple**: wallets sigue en 1, ámbito sigue en 2, exactamente el baseline
  pre-fase. Las dos cláusulas que de verdad protegen contra publicar un paquete sin cambios —
  `test -z "$(git tag -l 'ambito-financiero-client-v0.3.0')"` y
  `test -z "$(git tag -l 'wallets-client-v0.3.0')"` — están **correctas y pasaron**.
- **Por qué importa haberlo anticipado:** el `<automated>` corre **después** del push irreversible.
  El riesgo real nunca fue la aserción en sí, sino que un agente que vea `FAIL` justo después de
  publicar intente "arreglarlo" **creando o borrando tags**, que es una prohibición explícita del
  plan. Nada de eso ocurrió: cero tags creados fuera de los cuatro aprobados, cero tags borrados.
- **Forma correcta para futuros planes:** fijar el baseline medido —
  `ambito-financiero-client-v*` == `2` y `wallets-client-v*` == `1`.
- **Commit:** ninguno (el PLAN es un artefacto aprobado y no se edita a mitad de ejecución).

### 2. [Rule 3 — blocker de entorno, resuelto sin tocar nada publicado] Dos bloques `<verify>` fallaron bajo `zsh` por ausencia de word-splitting

- **Found during:** Task 2 (`<automated>` del plan) y Task 3 (`uv pip install $WHEELS`).
- **Síntoma 1 (Task 2):** `MISSING TAG: market-data-client-v0.6.0 iol-client-v0.4.0 matriz-client-v0.3.0 higyrus-client-v0.3.0`
  — los cuatro nombres concatenados como **un solo** `$T`.
- **Síntoma 2 (Task 3):** `uv` intentó descargar una URL única formada por las cuatro concatenadas y
  URL-encodeadas (`…whl%20https://…`), devolviendo **404**.
- **Causa raíz:** el shell de esta sesión es **`zsh`**, que **no** hace word-splitting de
  expansiones de parámetros sin comillas. Los bloques `<verify>` del plan están escritos asumiendo
  `bash`/POSIX (`for T in $TAGS`, `uv pip install $WHEELS`). **No es un defecto del release, ni del
  packaging, ni de las URLs.**
- **Por qué NO se trató como fallo de install de paquete:** la exclusión de la Rule 3 sobre
  package-manager installs existe para el riesgo de slopsquat — un paquete que no existe o cuyo
  nombre podría resolver a otra cosa. Acá el target es una **URL completa y explícita de un asset de
  Release de este mismo repositorio**, producido por `release.yml` con `uv build` sobre el árbol
  tagueado en esa misma corrida. El 404 fue de una URL malformada por el shell, no de un paquete
  inexistente. **No se sustituyó ningún nombre, no se reintentó con otro paquete, no se instaló nada
  por nombre pelado.**
- **Fix:** re-ejecutar los bloques **verbatim bajo `bash -c` / `bash -euo pipefail -c`**, y pasar las
  cuatro URLs como argumentos explícitos entrecomillados. Ambos pasaron a la primera.
- **Commit:** ninguno (no se modificó ningún archivo).

### 3. [Nota de medición] El conteo de tags locales de paquete que el plan cita está desfasado

- El plan y su `<threat_model>` repiten "15 stale local package tags". **Medido:** 16 antes de esta
  ronda, **20** después. La prohibición que esa cifra justifica —nunca `git push --tags`— se
  respetó al pie de la letra y su fuerza sólo **aumenta** con el conteo real.

---

## Verificación del plan — 9/9

1. ✅ El operador respondió `approved` de forma explícita y literal antes de que corriera cualquier
   comando de tag; registrada verbatim con su timestamp, **separada** del `approved` del merge de
   40-02, y **no** auto-emitida pese a `auto_advance` + `_auto_chain_active` + `mode: yolo` — D-07(b)
2. ✅ Esa **única** aprobación cubrió los **cuatro** tags; el gate no se dividió por paquete — D-09
3. ✅ `MERGE_SHA` re-resuelto en vivo con `git rev-parse origin/main` tras `git fetch`, cross-checkeado
   contra `40-02-SUMMARY.md` (coincide); ningún literal de documento se usó como ancla
4. ✅ Los cuatro tags son anotados, anclan `8e0013f2ac7f…`, llegaron a `origin`, y se pushearon **por
   nombre** — cero `git push --tags` en toda la fase, cero `--force`
5. ✅ Las cuatro corridas de `release.yml` observadas **individualmente** hasta `success`; los cuatro
   run IDs registrados (`33315928885`, `33315932932`, `33315937584`, `33315942414`)
6. ✅ Las cuatro Releases públicas listan **wheel y sdist** con los filenames exactos esperados
7. ✅ sha256 de `release.yml` idéntico en **10** refs (`sort -u` → 1 línea);
   `git diff --name-only origin/main...HEAD -- .github/workflows` → 0 líneas. La forma rota de la
   Phase 34 **no** se reutilizó
8. ✅ Cero tags y cero Releases para `ambito-financiero-client` y `wallets-client`; sus conteos
   quedaron idénticos al baseline pre-fase
9. ✅ Los cuatro paquetes instalan desde su wheel público en un venv Python 3.12 fresco **fuera** del
   repo, `__version__` concuerda con `importlib.metadata`, y las cadenas profundas corren en verde
   contra la distribución instalada (`__file__` en `site-packages`)

## Known Stubs

Ninguno. Este plan no produce código de producto — sólo operaciones de git/gh, artefactos publicados
y un artefacto de planning.

## Threat Flags

Ninguna superficie de seguridad nueva. Estado final de las mitigaciones del `<threat_model>`:

- **T-40-17** (push irreversible / Releases públicas) — **mitigada**: el checkpoint bloqueante se
  ejerció de verdad, con `auto_advance: true`, `_auto_chain_active: true` y `mode: yolo` los tres
  activos y ninguno satisfaciéndolo. El push corrió **sólo** tras un `approved` literal del operador.
- **T-40-18** (tag sobre el HEAD de branch) — **mitigada**: `MERGE_SHA` re-resuelto en vivo,
  cross-checkeado, forma de dos padres re-asertada antes de tagear, y el SHA pasado explícito a cada
  `git tag -a`. Los cuatro `git rev-list -n1 <tag>` == `$MERGE_SHA`. **Relevante en concreto:** el
  HEAD local de la sesión era `61c4c9c`, **no** el merge; sin el SHA explícito los cuatro tags
  habrían apuntado fuera de la historia de `main`.
- **T-40-19** (`git push --tags`) — **mitigada**: cuatro `git push origin <tag>` por nombre, un
  comando cada uno. Cero `--tags`, cero `--force`. Los 20 tags locales y los milestone `v1.1`…`v1.6`
  siguen sin publicarse por esta vía.
- **T-40-20** (tag lightweight o string inválido) — **mitigada**: los cuatro `git cat-file -t`
  reportan `tag`; los cuatro strings validados contra el regex de `release.yml:28` y contra el awk de
  `release.yml:47` **antes** del push, y las cuatro corridas confirmaron el version-match en vivo.
- **T-40-21** (patchear el workflow / borrar un tag para reintentar) — **mitigada**: sha256 de
  `release.yml` idéntico en 10 refs incluyendo los cuatro nuevos; cero workflows editados; cero tags
  borrados o re-apuntados; cero Releases borradas. El FAIL espurio de la Deviation 1 se overrideó con
  justificación en vez de "arreglarse" tocando tags.
- **T-40-22** (slopsquat en el install post-publicación) — **mitigada**: los cuatro installs por URL
  completa de asset de Release; `uv` confirmó la procedencia `(from https://…)` de cada uno. Cero
  installs por nombre pelado, incluso frente al 404 de la Deviation 2.
- **T-40-23** (declarar el release bueno sólo por el pipeline verde) — **mitigada**: cadenas
  profundas ejecutadas contra la distribución **instalada**, con `__file__` probando que resolvieron
  en `site-packages` y no en el checkout.
- **T-40-24** (inferir N corridas verdes de una sola) — **mitigada**: las cuatro consultadas
  individualmente por `databaseId`; los cuatro run IDs registrados con sus timestamps, que muestran
  solapamiento real.
- **T-40-25** (fuga de credenciales) — **mitigada**: `gh auth status` redactó el token; nada se
  echoeó; los mensajes de tag llevan sólo paquete, versión y headline; las Releases usan
  `--generate-notes`; las descargas fueron públicas y sin autenticación.
- **T-40-SC** (supply chain) — **mitigada**: la única operación con forma de install fue la Task 3,
  sobre los wheels de este mismo repositorio construidos por `release.yml` en la misma corrida.

## Scope decisions en pie

- **OQ-3 — sin refresh de release-memory in-repo.** `/Users/admin/.claude/projects/…/memory/`
  contiene sólo `MEMORY.md` y `project_matriz_bbsa_sandbox.md`;
  `market-data-client-releases.md` (el archivo que la Phase 34-03 Task 3 refrescaba) **no existe** en
  este checkout. No hay target, este plan no autoró memory task, y crear memory files nuevos sigue
  siendo el deferred item de la Phase 34.
- **RESEARCH P11 — ámbito y wallets deliberadamente no publicados.** Sus superficies se movieron
  **sólo aditivamente** desde sus tags publicados: medido y clasificado, no "sin cambios". D-01.

## Self-Check: PASSED

- `.planning/phases/40-releases-breaking-coordinados/40-03-SUMMARY.md` — existe en disco.
- Los cuatro tags existen local y en `origin`, los cuatro anotados, los cuatro anclando
  `8e0013f2ac7f0361df1ad4893cf0de8f6c773751` — verificado por `git cat-file -t`,
  `git rev-list -n1` y `git ls-remote --tags origin`.
- Las cuatro Releases públicas existen con wheel + sdist — verificado por
  `gh release view <tag> --json assets`.
- Los cuatro run IDs de `release.yml` concluyeron `success` — verificado individualmente por
  `gh run view <id>`.
- `release.yml` sha256 `7109ff0b…` idéntico en los 10 refs.
- Los cuatro wheels instalan desde URL pública y las cadenas profundas dan
  `POST-PUBLISH VERIFICATION PASS` con `EXIT=0`.
- Directorios temporales borrados; `git status --porcelain` vacío.
</content>
</invoke>
