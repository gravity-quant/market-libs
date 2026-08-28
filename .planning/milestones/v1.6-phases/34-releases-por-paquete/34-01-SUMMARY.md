---
phase: 34-releases-por-paquete
plan: 01
subsystem: release-prep
tags: [release, changelog, semver, uv-lock, ci-mirror, credential-scan]
requires:
  - "Phase 30 — iol-client dict→modelo (16 firmas)"
  - "Phase 31 — market-data-client: cuatro endpoints de ops tipados"
  - "Phase 33 (33-07) — dispositions SC-1/SC-2/SC-3 locked `fix-shape-now`"
provides:
  - "packages/iol-client @ 0.3.0 en sus dos sitios de versión"
  - "packages/market-data-client @ 0.5.0 en sus dos sitios de versión"
  - "changelog `### v0.5.0` completo (7 rupturas) y des-provisionalizado"
  - "uv.lock registrando ambos workspace members bumpeados"
  - "git-ref:origin/milestone/v1.5-mutations == local HEAD (fast-forward)"
affects:
  - "34-02 — desbloquea `gh pr edit 12` (precondición HEAD == origin)"
  - "34-03 — fija los literales de tag `iol-client-v0.3.0` y `market-data-client-v0.5.0`"
tech-stack:
  added: []
  patterns:
    - "assert-by-count, nunca por ausencia de la palabra fail"
    - "pytest scopeado por paquete; nunca un `uv run pytest` bare"
    - "`uv lock` una sola vez, después de ambos edits de pyproject (D-11)"
    - "push fast-forward plano; `--force` / `--force-with-lease` prohibidos"
key-files:
  created:
    - .planning/phases/34-releases-por-paquete/34-01-SUMMARY.md
  modified:
    - packages/market-data-client/README.md
    - packages/iol-client/pyproject.toml
    - packages/iol-client/src/iol_client/__init__.py
    - packages/market-data-client/pyproject.toml
    - packages/market-data-client/src/market_data_client/__init__.py
    - uv.lock
    - .gitignore
decisions:
  - "Memory files: refrescar el `market-data-client-releases.md` existente en 34-03; NO crear `iol-client-releases.md`"
  - "Las dos aserciones de `<verify>` con baseline en tags de release se corrigieron al invariante real (versión, y scope-a-esta-fase); ver Deviations"
metrics:
  duration: "~10 min"
  completed: "2026-08-27"
  tasks: "3 de 3"
  commits: 5
  files-changed: 11
status: complete
---

# Phase 34 Plan 01: Prep reversible del release de dos paquetes — Summary

Changelog de `market-data-client` completado con las siete rupturas y des-provisionalizado, cuatro
sitios de versión bumpeados en dos paquetes, `uv.lock` refrescado con churn exacto 2/2, los quince
gates de CI espejados en verde localmente, scan de credenciales limpio sobre los 375 archivos que
pasan a ser públicos, y la branch de release publicada por fast-forward plano.

## Qué se hizo

### Task 1 — changelog: los tres breaks de forma de la Phase 33

Commit **`ac421c5`** — 1 archivo (`packages/market-data-client/README.md`).

Se **append**earon (no se reescribió) los tres breaks dentro de la sección `### v0.5.0` existente,
entre el último bullet de Phase 31 y el heading `### v0.4.0`:

| Id | Contenido | Forma |
|---|---|---|
| SC-1 | `preview_calendar_config` declarada `-> CalendarConfig` contra un sobre de dry-run distinto (nueve campos fantasma poblados con zero-value; `valid`, `requires_confirmation` y `market_after` descartados) → `CalendarConfigPreview` | tabla antes/después + los cuatro sitios de declaración |
| SC-2 | `MarketDataSnapshot.entries` / `.market_data` / `.staleness_seconds` → `\| None` (fila no-data de `GET /marketdata/latest`) | bold lead + 3 campos en backticks |
| SC-3 | `Symbol.created_at` / `.updated_at` → `str \| None` (ausentes de los tres acks de escritura) | 2 campos en backticks |

Framing agregado que hace explícito el total: **siete rupturas de fuente**, no cuatro (cuatro
dict→modelo de Phase 31 + estos tres fixes de forma de Phase 33).

Verificado en fuente antes de escribir, no asumido: `CalendarConfigPreview` y `PreviewMarket` están
ambos en el `__all__` del paquete y en el de `models.py`; los cuatro sitios de declaración de
`preview_calendar_config` son `client.py:696` (método), `client.py:1016` (shim), `aio.py:696` y
`aio.py:1044`. Se evitó afirmar el conteo total de campos de `CalendarConfig` (11 declarados vs. "9
ausentes" del 33-07) porque los dos números no cierran contra un único campo coincidente; el texto
dice "nueve estaban ausentes", que es lo que 33-07 sí afirma.

`packages/iol-client/README.md` **no se tocó** (D-03): `git diff --name-only HEAD~1..HEAD` sobre ese
path devolvió `0`.

### Task 2 — de-provisionalización + cuatro sitios de versión

Commit **`a305053`** — 2 archivos (iol-client `pyproject.toml` + `__init__.py`) → `0.2.0` → **`0.3.0`**.
Commit **`dbd2da9`** — 3 archivos (market-data-client `README.md` + `pyproject.toml` + `__init__.py`)
→ `0.4.0` → **`0.5.0`**.

De-provisionalización (el trap sin análogo en Phase 28):
- Heading `### v0.5.0 — sin publicar todavía` → exactamente `### v0.5.0`. Esto es lo que habilita el
  slice `awk '/^### v0\.5\.0$/'`, y es la prueba más fuerte de que el retitle pasó.
- Se **eliminó completo** el preámbulo de cuatro oraciones ("El bump de `pyproject.toml` y el tag los
  hace la Phase 34… una rueda cuya metadata dice `0.4.0`"). Ambas afirmaciones se volvieron falsas en
  el mismo commit. No se suavizó ni se reformuló en hedge: se removió, y la sección abre directo en
  el bold lead de los cuatro endpoints de ops.

Los cuatro sitios leen su target y coinciden por paquete; el slice de la sección sigue conteniendo
los diez tokens de identificador de la Task 1 (la de-provisionalización no borró contenido).

### Task 3 — lock, espejo de CI, scan y push

Commit **`b5132b1`** — 1 archivo (`uv.lock`).
Commit **`ea57b63`** — 5 archivos (`.gitignore` + 4 de cache de research; ver Deviations).

**Churn de `uv.lock`: exactamente `2 2`** (2 inserciones, 2 eliminaciones). El diff son literalmente
las dos líneas `version` de los dos workspace members (`uv.lock:384` y `:488`). Cero re-resolución de
dependencias de terceros — `Resolved 48 packages` antes y después. Un solo `uv lock`, corrido después
de ambos edits de `pyproject.toml` (D-11).

**Espejo local de CI — los quince gates, todos en verde:**

| # | Gate | Resultado |
|---|---|---|
| 1 | `uv lock --check` | Resolved 48 packages, exit 0 |
| 2 | `uv sync --all-packages --all-extras --dev --frozen` | reinstaló iol@0.3.0 y market-data@0.5.0 |
| 3 | `uv run ruff check .` | All checks passed! |
| 4 | `uv run ruff format --check .` | 254 files already formatted |
| 5 | `uv run lint-imports` | Contracts: 5 kept, 0 broken |
| 6 | `lint-logging` (LOG-01) | sin matches |
| 7 | `check_decode_intactness.py` (Phase 29) | 5 regiones → un hash `684191c7cdc5ff9c` |
| 8 | `check_uniform_structure.py` (Phase 31) | 6 paquetes con `models.py` + `types.py` |
| 9 | `check_surface_types.py` (Phase 32) | 180 nombres, 319 defs, **0 violations** |
| 10 | `uv run mypy` | Success: no issues found in 75 source files |
| 11 | `uv run pre-commit run --all-files` | 9 hooks Passed, **cero reescrituras** |

**pytest scopeado — los seis paquetes de la matriz de CI, no sólo los dos bumpeados:**

| Paquete | Resultado |
|---|---|
| `iol-client` | **272 passed** |
| `market-data-client` | **609 passed** |
| `higyrus-client` | 239 passed |
| `ambito-financiero-client` | 203 passed, 1 deselected |
| `matriz-client` | 430 passed |
| `wallets-client` | 7 passed |

Nunca se corrió un `uv run pytest` bare (el `testpaths` raíz incluye `verification/`, con fallas
matriz fuera de scope que ningún job de CI ejecuta).

**Scan de credenciales sobre `git diff origin/main...HEAD`** — 375 archivos, 86 890 inserciones,
3 490 eliminaciones, el diff completo que pasa a ser público:

| Check | Patrón | Resultado |
|---|---|---|
| JWT | `eyJ[A-Za-z0-9_-]{20,}` | **limpio, cero matches** |
| client_secret | `client_secret\s*[=:]\s*.{0,2}[A-Za-z0-9_-]{20,}` | **limpio, cero matches** |
| `.env` trackeado | `git ls-files \| grep '(^\|/)\.env$'` | **vacío** — sólo los seis `.env.example` |

Ningún valor coincidente fue impreso en ningún momento (no hubo coincidencias; el protocolo era
reportar archivo y línea únicamente).

**Push — conteo recomputado en vivo, no heredado:**

| Medición | Valor |
|---|---|
| `git rev-list --count origin/milestone/v1.5-mutations..HEAD` (pre-push) | **54** |
| `git rev-list --count HEAD..origin/milestone/v1.5-mutations` | **0** (fast-forward posible) |
| Figura obsoleta en `34-CONTEXT.md` | 44 — **no usada** |
| Figura de `34-PATTERNS.md` (2026-08-27) | 47 — también ya obsoleta |

`git push origin milestone/v1.5-mutations` → `af80e85..ea57b63`. Notación de dos puntos sin prefijo
`+`: fast-forward plano. **Sin `--force`, sin `--force-with-lease`, sin `git rebase`, sin
`git merge origin/main`.** Sanity de D-07: `HEAD..origin/main` son exactamente los cuatro merge
commits de los PRs #8/#9/#10/#11 — divergencia cosmética, ningún rebase justificado.

## Desviaciones del plan

### 1. [Rule 1 — verificación defectuosa] La aserción de "paquetes no tocados" comparaba archivos enteros, no versiones

- **Encontrado en:** Task 2, `<verify><automated>`
- **Problema:** el loop asertaba
  `git diff --name-only iol-client-v0.2.0..HEAD -- packages/$P/pyproject.toml packages/$P/src/*/__init__.py == 0`.
  Falló con `UNCHANGED PACKAGE TOUCHED: higyrus-client`. El pathspec matchea el **archivo completo**,
  no la línea de versión, y el baseline es un tag anterior a las Phases 29-33.
- **Diagnóstico:** los diffs son puramente **aditivos** y de fases anteriores: `higyrus-client` (+4:
  `HigyrusDecodeError`, `Health`), `ambito-financiero-client` (+2: `AmbitoFinancieroDecodeError`),
  `matriz-client` (+2: `MatrizDecodeError`) — líneas de import y de `__all__` de las Phases 29/31.
  `wallets-client` sin cambios.
- **Invariante real (el de `must_haves`): "ningún paquete fuera de los dos tiene versión cambiada".
  **SE CUMPLE.** Comparación de valores, no de archivos:

  | Paquete | `pyproject.toml` | `__version__` |
  |---|---|---|
  | higyrus-client | 0.2.0 → 0.2.0 | `0.2.0` → `0.2.0` |
  | ambito-financiero-client | 0.2.0 → 0.2.0 | `0.2.0` → `0.2.0` |
  | matriz-client | 0.2.0 → 0.2.0 | (sin `__version__`) |
  | wallets-client | 0.2.0 → 0.2.0 | `0.2.0` → `0.2.0` |

- **Acción:** se corrió la aserción corregida (comparación de valores de versión contra
  `iol-client-v0.2.0`). El `PLAN.md` **no** se editó.

### 2. [Rule 1 — verificación defectuosa] La aserción de workflows usaba un baseline anterior a las Phases 29-32

- **Encontrado en:** Task 3 (c)
- **Problema:** `git diff --name-only iol-client-v0.2.0..HEAD -- .github/workflows` devolvió **1**, no
  `0`, contra ambos tags. El plan lo trata como violación dura de D-11.
- **Diagnóstico:** el archivo es `ci.yml`, y los commits que lo tocaron son **todos anteriores a la
  Phase 34**: `c1a7f90` (32-02, surface-types gate), `60e4d97` (31, mypy de tests de market-data),
  `f1d1cd6` (31-02, uniform-structure), `b37b95c` (29-09, decode-intactness), `1f295b3` (24-01).
  Son exactamente los gates que este plan acaba de correr en verde localmente.
- **Invariante real de D-11 ("ningún archivo bajo `.github/workflows/` modificado *por esta fase*"):
  **SE CUMPLE.**
  - `git diff --name-only 97ccee2..HEAD -- .github/workflows` → **`0`** (baseline = HEAD previo al plan).
  - `release.yml` — el pipeline de release, lo que de verdad importa — **byte-intacto** desde
    **ambos** tags previos: `0` contra `iol-client-v0.2.0` y `0` contra `market-data-client-v0.4.0`.
  - El conteo de checks sigue siendo **15**: `matrix.package` lista 6 paquetes × 2 pythons = 12, más
    `lint` + `pre-commit` + `mypy`. Consistente con `34-PATTERNS.md`.
- **Acción:** se corrió la aserción corregida. Ningún workflow fue editado.

### 3. [Rule 3 — bloqueante] Árbol sucio: sentinela de runtime + cache de research sin trackear

- **Encontrado en:** Task 3, precondición de árbol limpio (requerida también por 34-02)
- **Problema:** `.gsd/dispatch-isolation-sentinel.json` sin trackear y cuatro
  `.planning/research/.cache/*.json` sin trackear, ninguno creado por este plan.
- **Fix (commit `ea57b63`):**
  - `.gsd/` → `.gitignore`. Es output de runtime del harness (sentinela de dispatch de la Phase 30) y
    tenía **0 archivos trackeados**, así que ignorarlo no saca nada del repo.
  - Los 4 archivos de cache → **commiteados**, porque ya hay **9** archivos trackeados en ese mismo
    directorio: la convención establecida es trackearlos, no ignorarlos. Se inspeccionaron y son
    findings de research en texto plano, cubiertos además por el scan de credenciales.

### 4. [ordering, no bug] `test_dunder_version_matches_installed_distribution_metadata` falló transitoriamente en Task 2

- **Encontrado en:** Task 2, `uv run pytest packages/market-data-client -q` → `1 failed, 608 passed`
- **Causa:** el test compara `__version__` contra `importlib.metadata.version("market-data-client")`.
  En Task 2 el `pyproject`/`__init__` ya decían `0.5.0` pero el `uv.lock` todavía decía `0.4.0`, así
  que `uv run` sincronizó el venv contra el lock viejo y la metadata `.dist-info` seguía en `0.4.0`.
- **Por qué no es un bug:** es consecuencia directa y esperada de D-11, que **manda** diferir el único
  `uv lock` a la Task 3. En CI no puede ocurrir: `uv sync --frozen` corre antes de pytest.
- **Resolución:** tras `uv lock` + `uv sync` en Task 3, `market-data-client` pasa a **609 passed, 0
  failed**. No se cambió ni una línea de código ni de test.

## Decisión sobre memory files (de `<scope_decisions>`, registrada explícitamente)

- **Refrescar** el `market-data-client-releases.md` existente en
  `.claude/projects/-Users-admin-development-market-libs/memory/` — es trabajo de **34-03 Task 3**,
  no de este plan. Hoy instruye a todo agente futuro a instalar `market-data-client-v0.4.0`, así que
  dejarlo stale desinforma activamente. Es un refresh de un artefacto existente, no el ítem
  "crear archivos de memory in-repo" que CONTEXT difirió.
- **NO crear** `iol-client-releases.md`. Crear un memory file nuevo **es** exactamente el ítem
  diferido, ningún criterio de ROADMAP lo pide, y esta fase no lo abre.
- Nota: `34-CONTEXT.md` § Verification/Risk Notes afirma que no existe memory file para ninguno de los
  dos paquetes. Es **incorrecto** — `market-data-client-releases.md` existe (ya corregido en
  `34-PATTERNS.md`).

## Estado al cerrar

| Aserción | Estado |
|---|---|
| `git rev-parse HEAD` == `git rev-parse origin/milestone/v1.5-mutations` | ✅ |
| `git tag -l 'iol-client-v0.3.0'` | vacío ✅ — ningún tag creado |
| `git tag -l 'market-data-client-v0.5.0'` | vacío ✅ |
| PR #12 | **OPEN, sin tocar** ✅ — sin `gh pr edit`, sin merge, sin comentario |
| Checkpoints humanos agregados por este plan | **cero** ✅ (D-08: los dos gates viven en 34-02 y 34-03) |
| Todo lo hecho acá | reversible con un commit ✅ |

## Lo que desbloquea

- **34-02** puede correr su bloque de precondiciones: `gh auth status`, árbol limpio y
  `HEAD == origin/milestone/v1.5-mutations` — la tercera aserción, falsa al empezar este plan
  (54 commits de adelanto), ahora es verdadera.
- **34-03** tiene fijados los dos literales de tag, ambos validables contra el gate awk de
  `release.yml:42-51`: `iol-client-v0.3.0` ↔ `version = "0.3.0"` y
  `market-data-client-v0.5.0` ↔ `version = "0.5.0"`.

## Known Stubs

Ninguno. Este plan no agrega lógica de negocio: edita prosa de changelog, cuatro literales de versión
y un lockfile generado.

## Threat Flags

Ninguna. No se introdujo superficie de red, de auth, de acceso a archivos ni de schema. Los threats
del registro con disposición `mitigate` que le tocan a este plan (T-34-01 scan de credenciales,
T-34-02 alineación de versiones, T-34-03 set de paquetes, T-34-04 churn del lock, T-34-05 no-force)
fueron todos ejercidos y quedaron verdes; su evidencia está arriba.

## Self-Check: PASSED

Los ocho archivos declarados existen en disco y los seis commits declarados existen en `git log`.
