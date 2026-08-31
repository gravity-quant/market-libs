---
phase: 38
slug: iol-client-auditor-a-de-higyrus-mbito-wallets
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: false
not_verifiable_retroactively: 0
audited_commit_sha: 37a83fe693a303a551f4374f48fe6fc5521804f7
audit_baseline_head: 6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5
frozen_tree_verified: true
wave_0_complete: false
created: 2026-08-29
updated: 2026-08-31
last_audited: 2026-08-31
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` >= 8.3 with `pytest-asyncio` (`asyncio_mode = "auto"`), `pytest-httpx` >= 0.34 |
| **Config file** | root `pyproject.toml`, `[tool.pytest.ini_options]` (`--import-mode=importlib`, `--strict-markers`, `pythonpath = ["."]`) |
| **Quick run command** | `uv run --package iol-client pytest packages/iol-client -q` |
| **Full suite command** | `uv run --package iol-client pytest packages/iol-client -q && uv run --package higyrus-client pytest packages/higyrus-client -q && uv run --package ambito-financiero-client pytest packages/ambito-financiero-client -q && uv run --package wallets-client pytest packages/wallets-client -q && uv run python tools/check_decode_intactness.py && uv run python tools/check_uniform_structure.py && uv run python tools/check_surface_types.py && uv run mypy packages/iol-client && uv run ruff check packages/iol-client` |
| **Estimated runtime** | ~15s quick / ~90s full suite |

---

## Sampling Rate

- **After every task commit:** Run `uv run --package iol-client pytest packages/iol-client -q` (or the affected package's leg) + `uv run ruff check <touched paths>`
- **After every plan wave:** Run all four package suites + the three `tools/` gates + `uv run mypy packages/iol-client`
- **Before `/gsd-verify-work`:** Full suite must be green — 289 / 289 / 208+1 / 10 as the floor (any decrease is a regression, an increase is expected from the new RED test)
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 38-01-01 | 01 | 0 | NOBJ-AUD-01 | — | N/A | unit (RED fixture) | `pytest packages/iol-client/tests/test_surface_types_red.py -k optional_model_field -q` | ❌ W0 | ✅ (VN 2026-08-31) |
| 38-01-02 | 01 | 0 | NOBJ-AUD-01 | — | N/A | unit (RED fixture) | `pytest packages/iol-client/tests/test_surface_types_red.py -k optional_literal_alias -q` | ❌ W0 | ✅ (VN 2026-08-31) |
| 38-02-01 | 02 | 1 | NOBJ-IOL-01 | — | N/A | unit | `pytest packages/iol-client/tests/test_models.py -k puntas -q` | ✅ | ✅ (VN 2026-08-31) |
| 38-02-02 | 02 | 1 | NOBJ-IOL-01 | — | N/A | unit | `pytest packages/iol-client/tests/test_models.py -k round_trip -q` | ✅ | ✅ (VN 2026-08-31) |
| 38-03-01 | 03 | 2 | NOBJ-IOL-01 | — | N/A | static | `uv run mypy packages/iol-client` | ✅ | ✅ (VN 2026-08-31) |
| 38-03-02 | 03 | 2 | NOBJ-IOL-01 | — | N/A | snapshot | `uv run python verification/regen_snapshots.py && git diff --stat verification/snapshots/iol-client-surface.txt` | ✅ | ✅ (VN 2026-08-31) |
| 38-04-01 | 04 | 2 | NOBJ-AUD-01 | — | N/A | unit | `pytest packages/matriz-client/tests/test_surface_types_red.py -q` (read-only regression check) | ✅ | ✅ (VN 2026-08-31) |
| 38-05-01 | 05 | 3 | NOBJ-AUD-01 | — | N/A | doc review | `checkpoint:human-verify` on `38-CENSUS.md` | ❌ manual | ⬜ histórico |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · ⬜ histórico (VERIFIED-HISTORICALLY, auditoría 2026-08-31) · ⬜ no re-verificable (NOT-VERIFIABLE-RETROACTIVELY, auditoría 2026-08-31)*

---

## Wave 0 Requirements

- [ ] `packages/iol-client/tests/test_surface_types_red.py` — add `test_an_optional_model_field_is_caught` (covers NOBJ-AUD-01 D-11 lower bound)
- [ ] `packages/iol-client/tests/test_surface_types_red.py` — add `test_an_optional_literal_alias_field_is_spared` (covers the D-01b narrowness corollary — must NOT reflag the 10 matriz `Literal | None` leaves)
- [ ] No framework install needed; no `conftest.py` changes needed

`tdd_mode` is enabled: the 7 migrated assertions in `test_models.py` (D-04, plus the round-trip assertion found in research) are themselves the RED step for the source change — write them before flipping the `puntas` annotations and confirm they fail for the stated reason, not by collection error.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `38-CENSUS.md` has zero rows without a disposition | NOBJ-AUD-01 | Census completeness (SC-2) is a documentation contract, not an executable assertion | Read `38-CENSUS.md`, confirm every row (higyrus/ámbito/wallets) has a disposition value; confirm zero-violation packages are enumerated, not omitted |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter
- [x] Audit 2026-08-31: 9 filas dispuestas (7 VERIFIED-NOW / 2 VERIFIED-HISTORICALLY / 0 NOT-VERIFIABLE-RETROACTIVELY); 0 archivos de lock nuevos; nyquist_compliant sigue en false

**Approval:** pending

---

## Validation Audit 2026-08-31

Auditoría Nyquist retroactiva de la Phase 38, corrida a mano contra el árbol congelado de v1.7 según
el contrato `41-AUDIT-CONTRACT.md` (Phase 41, NYQ-01). Estado de entrada: `status: draft`,
`nyquist_compliant: false`, 9 filas sin disponer —8 del mapa por tarea más 1 de
`## Manual-Only Verifications`, de las cuales **dos son revisión de un documento** y una **muta el
árbol de trabajo**—; **sin subagente** — la auditoría lee y dispone, no repara (D-06a).

**Auditor:** Phase 41 (`/gsd-execute-phase 41`, plan 41-05) — auditoría de lectura y disposición
**Árbol auditado:** commit de `v1.7` `37a83fe693a303a551f4374f48fe6fc5521804f7`; HEAD de la sesión
de auditoría `6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5`; identidad probada con
`git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0 (diff vacío)

| Metric | Count |
|--------|-------|
| Filas auditadas (denominador) | 9 |
| VERIFIED-NOW | 7 |
| VERIFIED-HISTORICALLY | 2 |
| NOT-VERIFIABLE-RETROACTIVELY | 0 |
| Correcciones de comando | 0 |
| Archivos de test nuevos escritos | 0 |
| Filas NOT ENFORCED en CI | 3 |
| Suite de re-ejecución de esta sesión | `311 passed in 13.91s` (`uv run pytest packages/iol-client -q`) |

**Nota de clave:** el denominador de esta fase es **9 = 8 filas de mapa + 1 fila manual-only**
(§2.1 del contrato). Las 8 filas del mapa reciben `38-r01`..`38-r08` en su orden de aparición y la
única fila de `## Manual-Only Verifications` recibe `38-m01` (§2.3). Los Task ID de este mapa **sí**
son únicos —a diferencia de los de la Phase 37—, pero la clave ordinal se aplica igual para que las
cinco tablas de disposición de la Phase 41 sean sumables con el mismo patrón.

### Disposición por fila

| Row | Disposition | Evidence (this session) | CI enforcement surface |
|-----|-------------|-------------------------|------------------------|
| 38-r01 · 38-01-01 | VERIFIED-NOW | `uv run pytest packages/iol-client/tests/test_surface_types_red.py -k optional_model_field -q` → `1 passed, 15 deselected in 0.01s`, exit 0 — deselect parcial, no total (§6.2) (R-01) | job `test`, `ci.yml:133-166` (paso de tests en `ci.yml:154-160`; leg `iol-client` de la matriz 6 paquetes × py3.12/3.13) |
| 38-r02 · 38-01-02 | VERIFIED-NOW | `uv run pytest packages/iol-client/tests/test_surface_types_red.py -k optional_literal_alias -q` → `1 passed, 15 deselected in 0.01s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 38-r03 · 38-02-01 | VERIFIED-NOW | `uv run pytest packages/iol-client/tests/test_models.py -k puntas -q` → `5 passed, 21 deselected in 0.01s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 38-r04 · 38-02-02 | VERIFIED-NOW | `uv run pytest packages/iol-client/tests/test_models.py -k round_trip -q` → `4 passed, 22 deselected in 0.01s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 38-r05 · 38-03-01 | VERIFIED-NOW | `uv run mypy packages/iol-client` → `Success: no issues found in 31 source files`, exit 0 (R-01) | job `typecheck`, `ci.yml:122-123` (step `mypy (src global)`) más `ci.yml:124-131` (step `mypy (tests por paquete)`, bucle que incluye `iol-client`): entre los dos cubren el mismo árbol que el comando del mapa recorre de una sola pasada |
| 38-r06 · 38-03-02 | VERIFIED-NOW | `uv run python verification/regen_snapshots.py && git diff --stat verification/snapshots/iol-client-surface.txt` → exit 0; el generador reescribió los **4** snapshots (`ambito-financiero-client` 10 símbolos, `iol-client` 19, `higyrus-client` 31, `matriz-client` 68) y la salida fue **byte-idéntica**: `git diff --stat verification/snapshots/iol-client-surface.txt` sin ninguna línea, `git diff --stat verification/snapshots/` sin ninguna línea y `git status --porcelain verification/` vacío tras la corrida (R-01) | **NOT ENFORCED** — `verification/regen_snapshots.py` no aparece en `.github/workflows/ci.yml`: ni en el job `lint` (que allowlistea 12 archivos `verification/test_*.py` en `ci.yml:81-92`, ninguno de ellos éste) ni en ningún otro job. La deriva de snapshot sólo se detecta corriendo el script a mano |
| 38-r07 · 38-04-01 | VERIFIED-NOW | `uv run pytest packages/matriz-client/tests/test_surface_types_red.py -q` → `19 passed in 0.22s`, exit 0 — chequeo de regresión de sólo-lectura sobre el paquete vecino, sin deselect (R-01) | job `test`, `ci.yml:133-166` (leg `matriz-client`; es la única fila del mapa de la Phase 38 que corre fuera de `iol-client`) |
| 38-r08 · 38-05-01 | VERIFIED-HISTORICALLY | Revisión de documento (`checkpoint:human-verify` sobre `38-CENSUS.md`), no re-derivable. Artefacto citado: la **confirmación humana fechada** registrada en el front-matter de `38-VERIFICATION.md`, clave `human_verification[0].confirmed: 2026-08-29T22:04:57Z`, cuyo `<expected>` enumera literalmente lo que el lector confirmó (toda fila de ambas tablas con celda de disposición y de evidencia no vacías; los tres paquetes representados; los ceros de ámbito y wallets por enumeración explícita y no por tabla vacía; la condición de stub de wallets; la discrepancia 10-vs-11 contra D-11 nombrada y no absorbida). El censo sigue en disco: `.planning/milestones/v1.7-phases/38-…/38-CENSUS.md`, 426 líneas. Cruzado con `38-VERIFICATION.md` truth #4 y truth #14 (R-06) | **NOT ENFORCED (por naturaleza)** — una revisión de completitud documental no es una aserción ejecutable; ningún job de `ci.yml` la cubre ni podría cubrirla |
| 38-m01 · (manual-only fila 1) | VERIFIED-HISTORICALLY | Misma conducta declarada desde la otra tabla: *"`38-CENSUS.md` tiene cero filas sin disposición"* (SC-2). Artefacto citado: la misma confirmación humana fechada `2026-08-29T22:04:57Z` del front-matter de `38-VERIFICATION.md` (`human_verification[0].confirmed`), más `38-CENSUS.md` en disco (426 líneas) y el sign-off del lector en `38-UAT.md`. La auditoría **no** re-hizo la lectura del censo con criterio propio: eso sustituiría la evidencia registrada por un juicio de 2026-08-31 (R-06, §3 del contrato) | **NOT ENFORCED (por naturaleza)** — la propia celda `Why Manual` del mapa lo dice: *"Census completeness (SC-2) is a documentation contract, not an executable assertion"* |

*Disposiciones: `VERIFIED-NOW` = comando re-ejecutado en esta sesión, verde, con conteo distinto de
cero · `VERIFIED-HISTORICALLY` = artefacto fechado citado, no re-derivable ·
`NOT-VERIFIABLE-RETROACTIVELY` = requería red en vivo, ventana de mercado o checkpoint humano no
reproducible. Calificadores: `(comando corregido)` R-02 · `(ruta corregida)` R-03 ·
`(comando redactado retroactivamente)` R-04.*

### Correcciones de comando

Ninguna.

Las siete filas automatizadas de esta fase corren **exactamente como el mapa las escribió**: ningún
selector `-k` quedó vacío, ninguna ruta bajo `.planning/` fue invalidada por la mudanza del
milestone, y ninguna celda de comando delegaba la decisión al planner. Es la única de las cinco
fases auditadas por la Phase 41 cuyo contrato de verificación no necesitó ninguna reparación para
poder correr. Los cuatro deselects que aparecen (`38-r01`..`38-r04`) son **parciales**, con conteo de
pasados distinto de cero en los cuatro casos, de modo que el guardia anti-vacuidad de la §6.2 del
contrato no se disparó ni una vez.

### Por qué las dos filas de revisión siguen siendo manuales

`38-r08` y `38-m01` son la **misma conducta declarada desde dos tablas distintas**: que
`38-CENSUS.md` no tenga ninguna fila sin disposición (SC-2). El mapa la registra como `doc review`
resuelta por `checkpoint:human-verify`; la tabla `## Manual-Only Verifications` la registra otra vez
con su justificación explícita — *"Census completeness (SC-2) is a documentation contract, not an
executable assertion"*. Las dos se cuentan por separado porque el denominador de la §2.1 del
contrato cuenta **filas**, no conductas; disponerlas juntas dejaría una fila del artefacto sin
disposición.

La evidencia que las sostiene es una **confirmación humana con timestamp registrada en disco**:
`38-VERIFICATION.md`, front-matter, `human_verification[0].confirmed: 2026-08-29T22:04:57Z`. Ese
bloque no es un resumen de la revisión: contiene el `<expected>` completo que el lector confirmó,
enumerando lo que había que ver (celdas de disposición y evidencia no vacías en ambas tablas, los
tres paquetes representados, los ceros de ámbito y wallets por enumeración y no por tabla vacía, la
condición de stub de wallets, la discrepancia 10-vs-11 contra D-11 nombrada). El censo sigue en
disco, 426 líneas, y `38-VERIFICATION.md` truth #4 y truth #14 lo cruzan con un re-derivado
independiente por AST del verificador de plan-time.

Lo que **no** se hizo, y es el punto: la auditoría no volvió a abrir `38-CENSUS.md` para juzgar por
sí misma si sus disposiciones son "reales o de relleno". Esa lectura ya ocurrió, la hizo una persona,
tiene fecha, y está registrada. Repetirla hoy produciría un juicio de 2026-08-31 sobre un artefacto
de 2026-08-29 y lo presentaría como si fuera la verificación original — que es exactamente la
sustitución que R-06 prohíbe. La conducta es una revisión de completitud documental: un grep puede
confirmar que las celdas están, sólo un lector puede confirmar que dicen algo. Por eso siguen siendo
manuales hoy, siguen sin cubrirse en CI, y su `Status` en el mapa es `⬜ histórico` y **no** la marca
verde (§5.5 del contrato: un ✅ sobre una fila `doc review` es staleness laundering aunque la
disposición sea correcta).

### Hallazgos de bookkeeping

Dos. Ninguno cambia una disposición; los dos se **nombran** en vez de corregirse en silencio.

1. **Dos celdas `File Exists` afirman que el archivo de test falta, y hoy existe y corre verde.** Las
   filas `38-01-01` y `38-01-02` del mapa llevan `❌ W0` sobre
   `packages/iol-client/tests/test_surface_types_red.py`. El archivo existe en disco (24 480 bytes) y
   su suite completa da `16 passed in 0.19s`; los dos selectores que esas filas declaran
   (`-k optional_model_field`, `-k optional_literal_alias`) seleccionan 1 test cada uno y pasan.
   Es bookkeeping de **plan-time**: las celdas describen el estado *antes* de la Wave 0, y nunca se
   actualizaron al cerrarla —lo mismo que delata `wave_0_complete: false`, y lo mismo que la Phase 37
   presenta en diez de sus catorce filas—. No es un gap de cobertura. **Las celdas `File Exists` y
   `wave_0_complete` no se tocan:** su contradicción con la realidad medida **es** el hallazgo, y
   corregirlas lo borraría.
2. **La fila `38-03-02` muta el árbol de trabajo, y el mapa no lo señala.** Su comando corre
   `verification/regen_snapshots.py`, que **escribe cuatro archivos** bajo `verification/snapshots/`
   (`ambito-financiero-client`, `iol-client`, `higyrus-client`, `matriz-client`) antes de que el
   `git diff --stat` los mire. La celda `Test Type` dice `snapshot` y la de comando muestra el `&&`,
   pero en ninguna parte del artefacto se advierte que re-correr esta fila **escribe**. La distinción
   importa para cualquier re-corrida futura: si la salida no fuera byte-idéntica, la fila ensuciaría
   el árbol como efecto colateral de verificarlo, y —en el contexto de esta auditoría— invalidaría en
   silencio el invariante del criterio 1 de toda la Phase 41. En esta corrida la salida **fue**
   byte-idéntica (los cuatro archivos reescritos, `git diff --stat verification/snapshots/` sin una
   sola línea, `git status --porcelain verification/` vacío), pero eso se **comprobó**, no se asumió.
   Vale dejarlo anotado: una fila de verificación que escribe al árbol necesita decirlo en su propia
   celda.

### Escalaciones

Ninguna. Las nueve filas cayeron bajo una regla del contrato sin necesidad de juicio propio: R-01
cubre las siete cuyo comando corre tal cual está escrito, y R-06 cubre las dos de revisión de
documento, cuya confirmación humana fechada existe en disco. El guardia anti-vacuidad de la §6.2
**no se disparó ninguna vez** —los cuatro deselects son parciales y todos reportan conteo de pasados
distinto de cero—, que es exactamente lo que `41-RESEARCH.md` había medido para esta fase; una
segunda fila de selección vacía habría sido la señal que la §3 manda escalar en vez de re-apuntar en
silencio, y no apareció. Las cuentas medidas coinciden con la distribución esperada de la §2.4 del
contrato — 7 / 2 / 0 — y con el conteo esperado de **3** filas `NOT ENFORCED`: la del regenerador de
snapshots más las dos de revisión de documento. Esas tres son superficies **preexistentes**, no
locks producidos por esta auditoría; se reportan acá y su destino queda ruteado al edit consolidado
de `.github/workflows/ci.yml` de la Phase 45 (§7 del contrato: se reporta, no se "arregla" — tocar
`.github/` acá rompería el invariante del criterio 1). El árbol quedó limpio después de correr el
regenerador: `git status --porcelain verification/` vacío y `ls verification/test_*.py | wc -l`
sigue en **52**, idéntico a la línea base de §1.5 del contrato.
Cero archivos de test nuevos; cero escalaciones.

Veredicto de auditoría: **Phase 38 queda PARTIAL** — status draft → validated,
nyquist_compliant sigue en false.

`nyquist_compliant` sigue en `false` porque R-09 falla por su condición **(b)**: la fase retiene
**dos** filas `VERIFIED-HISTORICALLY` (`38-r08` y `38-m01`). La condición (c) se cumple sin reservas
—cero correcciones de comando, cero de ruta, cero redacciones retroactivas: es la única de las cinco
fases cuyo contrato de verificación corrió intacto—, y (a) falla junto con (b) por las mismas dos
filas: 7 de 9 disponen `VERIFIED-NOW` plano, no 9. `not_verifiable_retroactively` queda en **0**: la
fase no conserva ningún ítem de esa clase, y decirlo con un cero explícito es información, no
ausencia de ella.

Conviene ser explícito sobre qué **no** significa este `false`, porque las dos filas históricas son
justamente las que están mejor documentadas de la fase. La conducta que declaran —el censo completo,
con disposición en cada fila— fue verificada: por el lector humano el 2026-08-29 con timestamp
registrado, y por el verificador de plan-time con un re-derivado independiente por AST que coincidió
número por número (142 campos, 15 clases, 10 campos de enlace). Lo que el flag codifica no es duda
sobre esa conducta, sino que **la fase no puede re-verificarse entera desde el árbol congelado**: dos
de sus nueve filas dependen de una lectura humana que no se re-deriva, y una tercera sólo se
comprueba corriendo a mano un script que CI no ejecuta. Una fase Nyquist-compliant es una que un
tercero puede re-correr de punta a punta y obtener la misma respuesta. La Phase 38 no lo es, y
`status: validated` + `nyquist_compliant: false` es precisamente cómo se dice eso sin quitarle valor
a la evidencia que sí existe.
