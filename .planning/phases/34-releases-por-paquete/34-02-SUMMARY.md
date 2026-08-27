---
phase: 34-releases-por-paquete
plan: 02
subsystem: release-ops
tags: [release, pull-request, ci-gate, merge-commit, human-checkpoint, mypy]
requires:
  - "34-01 — HEAD == origin/milestone/v1.5-mutations (precondición de `gh pr edit 12`)"
  - "34-01 — cuatro sitios de versión bumpeados (iol 0.3.0, market-data 0.5.0)"
provides:
  - "gh-pr:12 actualizado en su lugar y MERGED"
  - "git-ref:origin/main == a89fa45 — merge commit real con dos padres"
  - "árbol mergeado con `version = \"0.3.0\"` y `version = \"0.5.0\"`"
  - "aprobación humana literal registrada para el gate D-08(a)"
affects:
  - "34-03 — el ancla de AMBOS tags es a89fa45 (recomputar con `git rev-parse origin/main`)"
  - "34-03 — la branch `milestone/v1.5-mutations` sobrevivió; el commit de memory va ahí"
tech-stack:
  added: []
  patterns:
    - "assert-by-count sobre `gh pr checks`, nunca por ausencia de la palabra fail"
    - "`gh pr edit` en lugar de `gh pr create` — el vehículo se actualiza, no se reemplaza"
    - "`gh pr merge --merge` — merge commit real, dos padres, nunca squash ni rebase"
    - "espejo local de CI job-por-job, no step-por-step parcial (lección de este plan)"
key-files:
  created:
    - .planning/phases/34-releases-por-paquete/34-02-SUMMARY.md
  modified:
    - packages/market-data-client/tests/test_models.py
decisions:
  - "El gate humano D-08(a) se resolvió con una respuesta literal del operador (\"approved\"); no se auto-aprobó pese a `auto_advance: true` y `mode: yolo` en config.json"
  - "La falla de `Type check (mypy)` se corrigió en el test (narrowing), nunca en `ci.yml` (D-11)"
metrics:
  duration: "~14 min"
  completed: "2026-08-27"
  tasks: "3 de 3"
  commits: 1
  files-changed: 1
status: complete
---

# Phase 34 Plan 02: PR #12 actualizado, gate de CI probado por conteo, merge a `main` — Summary

PR #12 actualizado **en su lugar** (nunca cerrado, nunca reemplazado) al título de release de dos
paquetes; una falla real de CI heredada de la Phase 33 detectada y corregida en el test (no en el
workflow); gate probado por **conteo exacto** 15/15 con 2 filas iol-client y 2 market-data-client;
checkpoint humano bloqueante respondido con un "approved" literal; y `origin/main` avanzado a un
merge commit real de **dos padres** cuyo árbol lleva ambas versiones. **Ningún tag creado.**

## Artefactos producidos

| Artefacto | Valor |
|---|---|
| PR | **#12** — https://github.com/gravity-quant/market-libs/pull/12 |
| Título final | `release: iol-client v0.3.0 + market-data-client v0.5.0 (tipado homogéneo de la superficie pública, fases 29-34)` |
| Estado final del PR | `MERGED` (`mergedAt` `2026-08-27T20:24:45Z`) |
| `MERGE_SHA` | **`a89fa45602b52d509e15664d96a074af7eb1a337`** |
| Padre 1 (`main` previo) | `1c5f8f210e77e71c40faf602b8470569582e6221` |
| Padre 2 (head de release) | `e5eeb8ad0e5f3eaeb0b5713f256a28e497fa30d3` |
| Subject del merge | `Merge pull request #12 from gravity-quant/milestone/v1.5-mutations` |
| Método de merge | **`gh pr merge 12 --merge`** — sin `--squash`, sin `--rebase`, sin flag de borrado de branch |

## Task 1 — actualizar PR #12 y probar el gate por conteo

### Precondiciones (las tres, recomputadas en vivo)

| Aserción | Resultado |
|---|---|
| `gh auth status` | exit 0 — cuenta `sebadlf`, scopes `gist, read:org, repo, workflow`. **El token nunca se imprimió** (`gh` ya lo redacta a `gho_***`) |
| `git status --porcelain` vacío | ✅ |
| `git rev-parse HEAD` == `git rev-parse origin/milestone/v1.5-mutations` | ✅ `47d4b8e` == `47d4b8e` (falsa antes de 34-01; su push es lo que la hizo verdadera) |

### Actualización en su lugar (D-05)

`gh pr edit 12 --title ... --body-file <file>`. **No** se corrió `gh pr close`, **no** se corrió
`gh pr create`. `gh pr list --state open --base main` devuelve exactamente **1** PR y su número es
**12** — la historia de review adjunta quedó intacta.

Título anterior — `milestone v1.6: tipado homogéneo de la superficie pública (phases 29-32)` —
obsoleto en dos ejes: nombraba fases 29-32 cuando el head lleva 29-34, y no nombraba versión alguna.

Body (en `--body-file`, para que el Markdown multilínea sobreviva al quoting del shell) cubre:
ambas transiciones exactas (`0.2.0` → `0.3.0`, `0.4.0` → `0.5.0`), que ambos paquetes son
source-breaking con su callout de changelog, las siete rupturas de market-data (4 de Phase 31 + los
tres fixes de forma SC-1/SC-2/SC-3 de Phase 33), el flip de truthiness y el escape hatch `to_dict()`
de iol, el span de fases 29-34, la inclusión deliberada de `.planning/` (D-06), y que los otros
cuatro paquetes no se bumpean ni se publican. **Sin credenciales ni secretos.**

### El gate de CI — por conteo, nunca por ausencia de "fail"

Run final **`33112548317`**, head `e5eeb8a`:

```
Lint y formato (ruff)                        pass
Tests · ambito-financiero-client · py3.12    pass
Tests · ambito-financiero-client · py3.13    pass
Tests · higyrus-client · py3.12              pass
Tests · higyrus-client · py3.13              pass
Tests · iol-client · py3.12                  pass
Tests · iol-client · py3.13                  pass
Tests · market-data-client · py3.12          pass
Tests · market-data-client · py3.13          pass
Tests · matriz-client · py3.12               pass
Tests · matriz-client · py3.13               pass
Tests · wallets-client · py3.12              pass
Tests · wallets-client · py3.13              pass
Type check (mypy)                            pass
pre-commit hooks                             pass
```

| Aserción | Requerido | Obtenido |
|---|---|---|
| `gh pr checks 12 \| wc -l` | 15 | **15** |
| `gh pr checks 12 \| awk -F'\t' '$2=="pass"' \| wc -l` | 15 | **15** |
| `grep -c 'Tests · iol-client · py3\.1[23]'` | 2 | **2** |
| `grep -c 'Tests · market-data-client · py3\.1[23]'` | 2 | **2** |

El conteo sigue siendo 15 con dos paquetes bumpeados: `matrix.package` (`ci.yml:113-119`) lista los
seis paquetes incondicionalmente → 6 × 2 = 12 checks de test + 3 jobs no-matrix
(`Lint y formato (ruff)`, `pre-commit hooks`, `Type check (mypy)`). Invariante a cuántos paquetes
toca el PR.

**Por qué el conteo y no un grep de "fail":** ninguna fila quedó `pending`, `skipping` ni
`cancelled`, y la tabla no está vacía — los cuatro estados que un check de ausencia-de-falla leería
como verde. `cancel-in-progress: true` (`ci.yml:20`) hace `cancelled` genuinamente alcanzable, y
`paths-ignore: ["**.md", ".gitignore"]` hace alcanzable el caso de **cero checks**. Este plan tocó
ambos casos degenerados en vivo: ver Desviaciones 1 y 2.

### Diff stat presentado

`376 files changed, 87176 insertions(+), 3490 deletions(-)` — de los cuales **237** bajo
`.planning/`, mantenidos a propósito (D-06). No se corrió `/gsd-pr-branch` ni filtrado alguno.

## Task 2 — gate humano bloqueante D-08(a)

**Presentado al operador:** URL y número del PR (12), la salida literal de `gh pr checks 12` con los
cuatro totales contados (15 filas / 15 `pass` / 2 iol-client / 2 market-data-client), el diff stat,
ambas transiciones exactas de versión, la desviación del fix de mypy con su commit y su
justificación, el matiz de `ci.yml` en el diff (ver Desviación 3), y la declaración explícita de que
`main` **no tiene branch protection**.

**Branch protection verificada en vivo, no asumida:**
`GET repos/gravity-quant/market-libs/branches/main/protection` → **`404 Not Found`**. GitHub habría
mergeado este PR con checks rojos, pendientes o cancelados. El conteo 15/15 y esta aprobación fueron
el único control de acceso sobre la operación.

**Respuesta del operador, verbatim:**

```
approved
```

**Timestamp de la respuesta:** `2026-08-27T20:24:40Z` (checkpoint emitido `2026-08-27T20:18:38Z`).

**Procedencia de la aprobación.** Fue una respuesta literal del operador, relayed por el
orquestador. **No** fue auto-emitida por el agente, **no** vino de `auto_advance`, **no** vino de
yolo mode, y **no** se infirió de silencio ni de una respuesta ambigua. Esto importa de forma
concreta acá: `.planning/config.json` tiene `workflow.auto_advance: true` y `mode: "yolo"`, y el
`gate="blocking"` del task (en vez de `gate="blocking-human"`) habría hecho que la regla por defecto
de `checkpoints.md` lo auto-aprobara. La prosa explícita del plan (`<action>`,
`<acceptance_criteria>`, `must_haves.prohibitions`) y D-08 sobrescriben ese default; el gate se trató
como `blocking-human` y la ejecución se detuvo de verdad hasta recibir la respuesta.

**Estado en el momento del gate — nada irreversible había ocurrido:** árbol limpio,
`HEAD == origin/milestone/v1.5-mutations` (`e5eeb8a`), ambos `git tag -l` vacíos, `origin/main`
sin tocar (`1c5f8f2`), y cero ejecuciones de `gh pr merge`, `git tag` o `git push` de tag antes de
la respuesta.

## Task 3 — merge con commit real de dos padres

`gh pr merge 12 --merge`, exit 0. Luego `git fetch origin main --tags`.

| Aserción | Requerido | Obtenido |
|---|---|---|
| `git rev-list --parents -n1 origin/main \| wc -w` | 3 | **3** |
| `git log -1 --format=%s origin/main` | empieza con `Merge pull request` | **`Merge pull request #12 from gravity-quant/milestone/v1.5-mutations`** |
| `git show origin/main:packages/iol-client/pyproject.toml` bajo el awk de `release.yml:47` | `0.3.0` | **`0.3.0`** |
| `git show origin/main:packages/market-data-client/pyproject.toml` bajo el mismo awk | `0.5.0` | **`0.5.0`** |
| `gh pr view 12 --json state` | `MERGED` | **`MERGED`** |
| `git ls-remote --heads origin milestone/v1.5-mutations` | devuelve ref | **`e5eeb8a refs/heads/milestone/v1.5-mutations`** |
| `git tag -l 'iol-client-v0.3.0'` | vacío | **vacío** |
| `git tag -l 'market-data-client-v0.5.0'` | vacío | **vacío** |

Las versiones se leyeron con **la misma expresión que usa el pipeline**
(`awk -F'"' '/^version[[:space:]]*=/{print $2; exit}'`, `release.yml:47`), no con un grep propio, así
que el gate de version-match de `release.yml` pasará para ambos tags en 34-03. Extra (el pipeline no
lo valida, así que la deriva embarcaría en verde): el árbol mergeado también lee
`__version__ = "0.3.0"` y `__version__ = "0.5.0"` en sus dos `__init__.py`.

`delete_branch_on_merge` es `false` y no se pasó flag de borrado: la branch sobrevivió y sigue
apuntando a `e5eeb8a`, disponible para el commit de memory de 34-03.

## Desviaciones del plan

### 1. [Rule 1 — bug bloqueante] `Type check (mypy)` estaba ROJO al llegar; corregido en el test, nunca en el workflow

- **Encontrado en:** Task 1 (c), primer snapshot de `gh pr checks 12`.
- **Estado heredado:** run `33112018009` (head `47d4b8e`, el estado que dejó 34-01) reportaba
  **15 filas, 14 `pass`, 1 `fail`** — `Type check (mypy)`. El mismo fallo está en el run anterior
  `33111749119` (head `ea57b63`): **precede a este plan y no lo introdujo este plan.**
- **Causa raíz** (step `mypy (tests por paquete)`, `packages/market-data-client/tests/test_models.py`):

  ```
  :118: error: Value of type "dict[str, Any] | None" is not indexable  [index]
          assert snap.market_data["BI"][0]["price"] == 1
  :119: error: Value of type "dict[str, Any] | None" is not indexable  [index]
          assert snap.market_data["OI"] is None
  ```

  **SC-2 de la Phase 33** ensanchó `MarketDataSnapshot.market_data` a `dict[str, Any] | None`
  (`models.py:306`). El test indexaba sin narrowing.
- **Por qué 34-01 no lo vio:** su espejo local corrió `uv run mypy` — el step **`mypy (src global)`**,
  75 archivos, verde — pero **no** el segundo step del mismo job, el loop
  `for pkg in …; do uv run mypy packages/$pkg/tests; done` (`ci.yml:98-105`), que es donde vivía la
  falla. Espejar un job por uno solo de sus steps es el agujero; la tabla de 11 gates de 34-01 tiene
  una fila "mypy" que en realidad cubría medio job.
- **Fix — commit `e5eeb8a`, 3 líneas agregadas, un solo archivo de test:**
  `assert snap.market_data is not None` antes de los dos accesos. Ese payload trae `market_data`
  poblado, así que el narrowing es **además una aserción real sobre el parseo**, no un cast de
  conveniencia. Comentario in-place citando 0.5.0 / Phase 33 / SC-2.
- **Nunca se tocó `ci.yml` ni `release.yml` (D-11).** Ningún archivo de `src/`. Ningún otro test.
- **Re-espejo local completo antes de pushear** — esta vez el job entero, los dos steps, los seis
  paquetes:

  | Gate | Resultado |
  |---|---|
  | `uv run mypy` (src global) | Success: no issues found in 75 source files |
  | `uv run mypy packages/<pkg>/tests` × 6 | 12 / 4 / 25 / 16 / 20 / **34** archivos, los seis Success |
  | `uv run ruff check .` | All checks passed! |
  | `uv run ruff format --check .` | 254 files already formatted |
  | `uv run pytest packages/market-data-client -q` | **609 passed** |
  | `uv run pre-commit run --all-files` | 9 hooks Passed, cero reescrituras |

- **Push:** `47d4b8e..e5eeb8a` — notación de dos puntos sin prefijo `+`: **fast-forward plano**. Sin
  `--force`, sin `--force-with-lease`, sin rebase.
- **Re-aserción del gate desde cero** tras el nuevo run: 15 / 15 / 2 / 2, tal como manda Task 1 (e).
- **Divulgado al operador en el checkpoint antes de pedir la aprobación**, con la opción explícita de
  abortar si prefería que el fix fuera un cambio revisado por separado.

### 2. [operativo, no bug] `gh pr checks 12 --watch` devolvió "no checks reported" y salió con 0

- **Encontrado en:** Task 1 (c), inmediatamente después del push de `e5eeb8a`.
- **Qué pasó:** GitHub todavía no había creado los check runs del nuevo commit, así que `--watch`
  imprimió `no checks reported on the 'milestone/v1.5-mutations' branch` y **salió con código 0**.
- **Por qué importa:** es exactamente el caso degenerado de "cero checks" que el plan advierte. Un
  gate de ausencia-de-falla lo habría leído como verde y habría mergeado un PR sin ninguna
  verificación. **El conteo `TOTAL = 15` es lo que lo atrapa.**
- **Acción:** se confirmó con `gh run list` que el run `33112548317` estaba `queued` para `e5eeb8a`,
  se esperó a que los checks se registraran y recién ahí se corrió `--watch` hasta completion. No se
  asertó nada contra la tabla vacía.

### 3. [aserción con baseline obsoleto, invariante real intacto] `ci.yml` sí aparece en el diff del PR

- **Encontrado en:** preparación del checkpoint, paso 5 de `<how-to-verify>` ("confirmar que ningún
  archivo bajo `.github/workflows/` aparece en el diff").
- **Realidad:** `git diff --name-only origin/main...HEAD -- .github/workflows` devuelve
  **`.github/workflows/ci.yml`**, no vacío.
- **Diagnóstico:** los cuatro commits que lo tocaron son **todos anteriores a la Phase 34** —
  `c1a7f90` (32-02, gate de surface-types), `60e4d97` (31, mypy de tests de market-data),
  `f1d1cd6` (31-02, uniform-structure), `b37b95c` (29-09, decode-intactness). Son precisamente los
  gates que acaban de correr en verde. Es la misma clase de hallazgo que la Desviación 2 de 34-01.
- **Invariante real de D-11 ("ningún workflow modificado *por esta fase*"): SE CUMPLE.**
  - `git diff --name-only 97ccee2..HEAD -- .github/workflows` → **`0`** (baseline = HEAD previo a la fase).
  - `release.yml` — el pipeline que de verdad importa — **byte-intacto** desde **ambos** tags previos:
    `0` archivos de diferencia contra `iol-client-v0.2.0` y contra `market-data-client-v0.4.0`.
- **Acción:** se le presentó el matiz al operador de forma explícita en el checkpoint en vez de
  reportar la aserción literal como verde o como violación. Ningún workflow fue editado. El
  `PLAN.md` no se editó.

## Prohibiciones del plan — verificación explícita

| Prohibición | Estado |
|---|---|
| Nunca reescribir historia (`--squash` / `--rebase` / cualquier force) | ✅ merge con `--merge`, dos padres; el único push fue fast-forward `47d4b8e..e5eeb8a` |
| Nunca reportar un gate como verde salvo por conteo positivo exacto | ✅ y se ejercitó en vivo: un `fail` real y una tabla vacía, ambos atrapados |
| Ningún checkpoint satisfecho por el agente, `auto_advance`, yolo o silencio | ✅ "approved" literal del operador, registrado verbatim con timestamp |
| Nunca cerrar #12 ni abrir un PR de reemplazo | ✅ `gh pr edit 12`; exactamente 1 PR abierto contra `main` y era el 12 |
| Ningún tag creado ni pusheado en este plan | ✅ ambos `git tag -l` vacíos al cerrar |
| Nunca parchear `ci.yml` / `release.yml` para hacer pasar un gate (D-11) | ✅ el fix fue en el test |
| Nunca imprimir el token ni credencial alguna | ✅ solo `gh auth status`, que ya redacta |

## Estado al cerrar

| Aserción | Estado |
|---|---|
| `origin/main` | **`a89fa45`** — merge commit, 2 padres (`1c5f8f2`, `e5eeb8a`) |
| PR #12 | `MERGED` |
| `origin/milestone/v1.5-mutations` | vive, en `e5eeb8a` |
| `git tag -l 'iol-client-v0.3.0'` | **vacío** — ningún tag creado en este plan |
| `git tag -l 'market-data-client-v0.5.0'` | **vacío** |
| Segundo gate humano (D-08b) | **pendiente** — vive en 34-03, cubre ambos tags en una sola aprobación |
| Releases públicos | ninguno creado |

## Lo que desbloquea

- **34-03** tiene su ancla de tag: `a89fa45`, un merge commit real de dos padres cuyo árbol satisface
  el gate awk de `release.yml:42-51` para **ambos** tags. Debe **recomputarlo** con
  `git rev-parse origin/main` (el valor de acá es cross-check, no fuente de verdad).
- La branch de release sobrevivió al merge, así que el commit de refresh de
  `market-data-client-releases.md` puede landear ahí como manda 34-03 Task 3.

## Known Stubs

Ninguno. Este plan no agregó lógica: operaciones de `git`/`gh` más un narrowing de tres líneas en un
test existente.

## Threat Flags

Ninguna. No se introdujo superficie de red, auth, acceso a archivos ni schema. Los threats del
registro con disposición `mitigate` que le tocan a este plan quedaron todos ejercidos y verdes:
T-34-05 (gate por conteo — atrapó un `fail` real y una tabla vacía), T-34-06 (checkpoint humano —
aprobación literal, no auto-advance), T-34-09 (estrategia de merge — dos padres asertados),
T-34-10 (vehículo correcto — `gh pr edit`, 1 PR abierto y es el 12), T-34-03a (ningún tag creado;
árbol mergeado pre-verificado), T-34-07 (sin credenciales en body ni en output).

## Self-Check: PASSED

`packages/market-data-client/tests/test_models.py` y este SUMMARY existen en disco; el commit
`e5eeb8a` y el merge commit `a89fa45` existen en `git log`.
