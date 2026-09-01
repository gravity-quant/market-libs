---
phase: 45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti
plan: 03
subsystem: testing
tags: [harness, dedupe, drift, findings, ast-lock, fid, iol, higyrus, matriz, ambito]

# Dependency graph
requires:
  - phase: 45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti
    plan: 02
    provides: "El patrón de referencia (`_seen_drift_keys` + `_drift_digest` + guarda antes de `_next_fid()`) sobre `main_market_data.py`, más los 3 arms de runtime de D-04"
  - phase: 39-matriz-venue-segregation
    provides: "`main_matriz._schema_path()` — el baseline segregado por `(func_name, venue)` que obliga a que la identidad de la clave de dedupe de matriz sea `file_path.name` y no `func_name`"
  - phase: 33-divergence-handler
    provides: "`verification/test_finding_count_consistency.py` (P-3) — el invariante que D-03 no puede relajar, y el modelo de aislamiento por `monkeypatch(_FINDINGS_DIR)`"
provides:
  - "Los 6 sitios de drift restantes de D-02 con guarda de dedupe intra-proceso, cada uno con el no-op de SU contrato de retorno (tupla `(\"PASS\", …)` ×3, `ProbeResult(…, \"PASS\", …)` ×1, `continue` ×2)"
  - "`verification/test_drift_dedupe_falsification.py` arms 4-6: lock por AST del ORDEN (guarda < fid < finding) y de la FORMA del no-op sobre los 7 sitios, más el arm de runtime del contrato de tupla en higyrus"
  - "Censo por AST de los sitios de drift (7, repartidos 1/3/1/1/1) como piso Y techo — un sitio nuevo sin guarda pone el lock rojo"
affects: [45-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lock por AST con tabla declarativa por archivo: `{driver: (cantidad de sitios, multiconjunto de formas de no-op)}` — el orden dentro del archivo no es contrato, la composición sí"
    - "Biyección ordenada guarda↔fid↔finding por línea dentro de cada archivo, en vez de 'existe una guarda anterior': sin ella, en un módulo con 3 sitios la guarda de uno 'cubre' a otro por ser simplemente anterior"
    - "Identidad de clave de dedupe = identidad del ARTEFACTO comparado (`file_path.name`), no del nombre de función, cuando el baseline está segregado por una dimensión extra (venue)"
    - "Pertenencia sobre un local ligado (`drift_key`), nunca sobre una tupla literal inline — mantiene una sola convención con el lock de substring-membership ya enrolado en CI"

key-files:
  created: []
  modified:
    - main_iol.py
    - main_higyrus.py
    - main_matriz.py
    - main_ambito_financiero.py
    - verification/test_drift_dedupe_falsification.py

key-decisions:
  - "En `main_matriz.py` la identidad de la clave es `file_path.name`, NO `func_name`: desde la Phase 39 el baseline se elige por `(func_name, venue)`, así que con `func_name` a secas dos drifts de venues distintos que compartieran `actual_schema` colapsarían pese a tener `expected` distintos — pérdida de censo"
  - "Los no-ops NO se uniformaron: 4 formas distintas para 7 sitios, según el contrato de retorno de cada función. Un `return` desnudo en un helper anotado `-> tuple[str, str]` devuelve `None` y su caller hace `status, detail = ...`"
  - "El detalle del no-op de los 3 sitios de tupla empieza por `file_path.name` y jamás por `escrito`: el caller clasifica con `elif detail.startswith(\"escrito\")` y lo contaría como baseline recién escrito"
  - "Copia local de `_seen_drift_keys`/`_drift_digest` por driver (4 copias nuevas), sin helper compartido: `CLAUDE.md` prohíbe código compartido entre unidades y `verification/findings.py` está vedado como sitio de estado por ser append-only"
  - "Las ramas hermanas `missing assumed key` de `main_iol.py` NO se tocaron — D-02 nombra 7 sitios y ésas quedan fuera a propósito; el límite se declara por escrito en el cierre (plan 45-05)"

patterns-established:
  - "Doble demostración de no-vacuidad, una por arm: invertir el orden en un driver (arm 4) y uniformar un no-op en otro (arm 5), pegar los dos rojos, restaurar y verificar por `grep` que ninguna reversión quedó en el árbol"

requirements-completed: []  # HARN-01 sigue PARCIAL hasta el enrolamiento en CI del plan 45-05
requirements-partial:
  - "HARN-01 — los 7 sitios de D-02 están corregidos y pinneados, pero el archivo de lock todavía NO corre en CI (lo enrola el plan 45-05, D-11)"

# Metrics
duration: 8min
completed: 2026-09-01
status: complete
---

# Phase 45 Plan 03: Dedupe en los 6 sitios de drift restantes + lock por AST Summary

**Los 7 sitios de drift de D-02 quedan cerrados con cuatro formas distintas de no-op —una por contrato de retorno— y un lock por AST sobre los 5 drivers que pinea tanto el orden (guarda antes del fid) como la forma, con las dos violaciones demostradas en rojo por separado.**

## Performance

- **Duration:** ~8 min
- **Tasks:** 3 (2 de implementación + 1 de lock)
- **Files created:** 0 · **Files modified:** 5

## Accomplishments

- **Los 6 sitios restantes no se uniformaron.** Cada uno recibió el no-op que su propia función puede devolver. El fix copy-paste que el `<critical_finding_from_pattern_mapper>` advertía habría roto tres sitios de forma inmediata (`TypeError` al desempaquetar `None`) y dos más de forma silenciosa (`finding_fids` inflado).
- **El lock por AST es lo que sobrevive a esta fase.** Los arms 4 y 5 recorren los 5 drivers, encuentran los 7 `append_finding` de drift por su título normalizado, y exigen la biyección `guarda < fid < finding` más el multiconjunto de formas de no-op declarado por archivo. Un sitio de drift nuevo sin guarda pone el censo en 8 y el arm 4 en rojo.
- **La identidad de la clave de matriz es el baseline, no la función.** Es la única desviación deliberada de forma respecto de los otros cuatro drivers, y la razón queda como comentario de una línea en el propio sitio.

## Mediciones pedidas por el `<output>` del plan

### 1. Los 6 arms en verde

```
uv run pytest -q verification/test_drift_dedupe_falsification.py
......                                                                   [100%]
6 passed in 0.17s
```

`--collect-only -q` lista exactamente 6 ítems:

```
test_same_drift_on_both_surfaces_collapses_to_one_block
test_distinct_drift_on_same_endpoint_does_not_collapse
test_dedupe_no_op_leaves_the_fid_not_burned
test_the_seven_drift_sites_decide_dedupe_before_burning_a_fid
test_each_dedupe_no_op_matches_its_own_return_contract
test_higyrus_dedupe_no_op_returns_a_tuple_the_caller_can_unpack

6 tests collected in 0.05s
```

Con las primitivas vecinas en la misma corrida:

```
uv run pytest -q verification/test_drift_dedupe_falsification.py \
  verification/test_finding_count_consistency.py \
  verification/test_findings_dedupe_by_title.py \
  verification/test_findings_fid_seed.py
...........................                                              [100%]
27 passed in 0.20s
```

`git diff --quiet HEAD -- verification/test_finding_count_consistency.py` → **exit 0**: P-3 verde y sin un carácter editado.

### 2. Demostración de no-vacuidad del arm 4 (orden invertido en ámbito) — ROJO

Con `fid = _next_fid()` movido temporalmente ARRIBA de la guarda en `main_ambito_financiero.py`:

```
>       assert violations == [], "\n".join(violations)
E       AssertionError: main_ambito_financiero.py: guarda en línea 640, `_next_fid()` en 639,
E       `append_finding` en 643 — el orden exigido es guarda < fid < finding. Con el fid arriba
E       de la guarda, el no-op quema un número y el driver reporta un censo mayor que el que
E       escribió (D-03).
E       assert ['main_ambito...ibió (D-03).'] == []

=========================== short test summary info ============================
FAILED verification/test_drift_dedupe_falsification.py::test_the_seven_drift_sites_decide_dedupe_before_burning_a_fid
1 failed in 0.13s
```

El mensaje nombra las tres líneas concretas (`640` / `639` / `643`) y por qué el orden importa. Tras `git checkout -- main_ambito_financiero.py`: `grep -c 'TEMPORAL-DEMO-45-03' main_ambito_financiero.py` → **0**, `git status --porcelain main_ambito_financiero.py` → **vacío**.

### 3. Demostración de no-vacuidad del arm 5 (no-op uniformado en higyrus) — ROJO

Con el no-op de `main_higyrus.py` cambiado temporalmente a un `return` desnudo:

```
>       assert violations == [], "\n".join(violations)
E       AssertionError: main_higyrus.py: formas de no-op ['return-desnudo'], se esperaban
E       ['return-tupla-("PASS", …)']. Un `return` desnudo en un helper que declara
E       `tuple[str, str]` devuelve `None` y su caller desempaqueta una tupla; un `return`
E       desnudo donde el caller espera un `ProbeResult` es el mismo hazard. Uniformar los 7
E       no-ops rompe al menos tres sitios (T-45-12).
E       assert ['main_higyru...s (T-45-12).'] == []

=========================== short test summary info ============================
FAILED verification/test_drift_dedupe_falsification.py::test_each_dedupe_no_op_matches_its_own_return_contract
1 failed in 0.11s
```

Nótese que **el arm 4 seguía verde** con el no-op uniformado (el orden no se movió) y **el arm 5 seguía verde** con el orden invertido (la forma no se movió): son dos propiedades ortogonales y por eso necesitan dos arms. Tras restaurar: `grep -c 'TEMPORAL-DEMO-45-03' main_higyrus.py` → **0**.

### 4. Los 7 sitios con el no-op efectivamente escrito (archivo + línea, HEAD post-Task 3)

| # | Sitio | Contrato de retorno | Componente `func` de la clave | Guarda (línea) | No-op escrito (línea) |
|---|---|---|---|---|---|
| 1 | `main_market_data.py::_write_schema_snapshot` | `None` | `client_function` | `544` | `return` desnudo — `547` (**45-02**, no tocado acá) |
| 2 | `main_iol.py::_write_or_check_schema` | `tuple[str, str]` | `func_name` | `1809` | `return ("PASS", f"{file_path.name} drift ya reportado en esta corrida")` — `1814` |
| 3 | `main_iol.py` type drift en `get_quote` | rama inline, acumula `finding_fids` | `f"get_quote:{key}"` | `1655` | `continue` — `1656` |
| 4 | `main_iol.py` type drift en `get_historical_quotes[0]` | ídem | `f"get_historical_quotes[0]:{key}"` | `1733` | `continue` — `1734` |
| 5 | `main_higyrus.py::_write_or_check_schema` | `tuple[str, str]` | `func_name` | `618` | `return ("PASS", f"{file_path.name} drift ya reportado en esta corrida")` — `623` |
| 6 | `main_matriz.py::_write_or_check_schema` | `tuple[str, str]` | **`file_path.name`** | `616` | `return ("PASS", f"{file_path.name} drift ya reportado en esta corrida")` — `621` |
| 7 | `main_ambito_financiero.py::probe_schema_snapshot` | `ProbeResult` | `"get_dollar_banco_nacion"` (literal) | `639` | `return ProbeResult("schema_snapshot", "PASS", "drift ya reportado en esta corrida")` — `643` |

**Cuatro formas para siete sitios.** Ninguna de las 3 tuplas empieza su detalle con `escrito`, así que el `elif detail.startswith("escrito")` del caller no las clasifica como baseline recién escrito. Los 2 `continue` no llevan `finding_fids.append`.

### 5. Gates

```
uv run python -c "import main_iol, main_higyrus, main_matriz, main_ambito_financiero, main_market_data"  → exit 0
uv run mypy main_iol.py main_higyrus.py main_matriz.py main_ambito_financiero.py  → Success: no issues found
uv run ruff check .                        → All checks passed!
uv run ruff format --check .               → 280 files already formatted
uv run lint-imports                        → Contracts: 5 kept, 0 broken.
uv run python tools/check_decode_intactness.py   → Checks A/B/C/D OK
uv run python tools/check_uniform_structure.py   → all 6 packages OK
uv run python tools/check_surface_types.py       → 187 / 337 / 467, 0 violations
git status --porcelain .planning/verification/   → (vacío)
```

Locks de driver ya enrolados en CI, en la misma corrida (incluido el de substring-membership de matriz, que la forma de la guarda podía haber activado):

```
uv run pytest -q verification/test_main_higyrus_deep_chain.py \
  verification/test_main_matriz_deep_chain.py \
  verification/test_main_matriz_risk_envelope_keys.py \
  verification/test_main_matriz_skip_line_shape.py \
  verification/test_main_higyrus_skip_line_shape.py
...................................................                      [100%]
51 passed in 0.33s
```

## Task Commits

1. **Task 1 — los 3 sitios de `main_iol.py`** — `ee72b4f` (`feat(45-03): dedupe intra-proceso en los 3 sitios de drift de main_iol (HARN-01)`), +63 / −0
2. **Task 2 — higyrus, matriz y ámbito** — `3de6368` (`feat(45-03): dedupe intra-proceso en higyrus, matriz y ambito (HARN-01)`), +114 / −0
3. **Task 3 — arms 4-6** — `a573a91` (`test(45-03): arms 4-6 — locks AST de orden y forma del no-op sobre los 7 sitios`), +402 / −11

## Files Created/Modified

- **`main_iol.py` (+63 / −0).** `import hashlib`; `_seen_drift_keys` + `_drift_digest()` junto a `_fid_counter`; guarda en los 3 sitios. Los 2 sitios de type drift ligan su clave a `(f"get_quote:{key}", digest)` y `(f"get_historical_quotes[0]:{key}", digest)` sobre el par `[expected_type, observed]`.
- **`main_higyrus.py` (+37 / −0)**, **`main_matriz.py` (+41 / −0)**, **`main_ambito_financiero.py` (+36 / −0).** Misma copia local de los dos artefactos; una guarda cada uno.
- **`verification/test_drift_dedupe_falsification.py` (+402 / −11).** Docstring extendido con el porqué de los locks por AST (P-3 es un property test con allocator local que no importa ni parsea ningún driver: verde con el orden viejo y verde con el nuevo, `45-RESEARCH.md` Pitfall B). Tabla declarativa `_EXPECTED_SITES` (5 drivers → cantidad de sitios + multiconjunto de formas). Helpers de detección compartidos por los arms 4 y 5 (`_title_literal`, `_is_drift_title`, `_drift_sites`, `_dedupe_guards`, `_no_op_shape`). Fixture de aislamiento nueva para higyrus.

**Lo que deliberadamente NO se tocó:** los títulos de los 7 findings (round-trip del parser de `findings.py` y CR-02 de título single-line intactos), la firma de `append_finding` (ningún kwarg nuevo), el `surface="sync"` de matriz, las ramas hermanas `missing assumed key` de iol, y las ramas `except (OSError, json.JSONDecodeError)` de baseline ilegible.

## Decisions Made

- **`file_path.name` como identidad en matriz.** Es la lectura correcta del componente `func` de D-01 ENMENDADA para ese driver, no una excepción arbitraria: `_schema_path()` elige el baseline por `(func_name, venue)` desde la Phase 39, así que `file_path.name` **es** la identidad de aquello contra lo que se comparó. Con `func_name` a secas, dos venues distintos con el mismo `actual_schema` y distinto `expected` colapsarían — exactamente la pérdida de censo que la fase existe para eliminar.
- **Normalización a minúsculas en la detección de títulos.** `main_market_data` escribe `"schema drift en …"` y los otros cuatro `"Schema drift en …"`. Sin el `lower()` el censo por AST daría 3 sitios y los 4 drivers restantes quedarían fuera del lock **sin que nada se pusiera rojo** — un lock silenciosamente parcial es peor que ninguno.
- **Biyección ordenada en vez de 'existe una guarda anterior'.** En `main_iol.py` los 3 sitios viven en el mismo módulo y dos de ellos en la misma función; con la formulación laxa, la guarda del sitio 3 satisfaría al sitio 4 por ser simplemente anterior en el archivo. El arm 4 empareja guardas y sitios por orden de línea con `strict=True` y exige `guarda < fid < finding` para cada par.
- **Pertenencia sobre un local ligado (`drift_key`).** `verification/test_main_matriz_skip_line_shape.py` (enrolado en CI) marca como ofensa cualquier `ast.Compare` con `In` cuyo lado izquierdo sea un literal string. Ese lock corre sólo sobre `main_matriz.py`, pero la misma forma se replicó en los 5 drivers para no tener dos convenciones. Verificado: ese archivo sigue verde.
- **El censo de 7 es piso Y techo.** El arm 4 falla tanto si aparece un sitio nuevo sin guarda como si desaparece uno. Agregar una entrada a `_EXPECTED_SITES` es un acto deliberado del editor, no un efecto automático.

## Deviations from Plan

Ninguna desviación de conducta. Sin auto-fixes bajo Rules 1-3; sin instalación de paquetes (consistente con `T-45-SC`).

**Una corrección de medición del plan, sin impacto en el resultado:** el criterio de aceptación de la Task 1 pedía `grep -c 'missing assumed key' main_iol.py` = **4** ("2 en `get_quote`, 2 en `get_historical_quotes[0]`"). El valor real en HEAD es **2** — hay **una** rama `if key not in observed:` por bucle, no dos; el plan contó las ramas hermanas por par de bucles en vez de por bucle. Lo que el criterio protege sí se verificó y se cumple: `git diff main_iol.py | grep 'missing assumed key\|key not in observed'` → **sin coincidencias**, las ramas hermanas quedaron intactas y fuera del alcance de D-02.

## TDD Gate Compliance

La Task 3 está marcada `tdd="true"`, pero su sujeto es código que las Tasks 1 y 2 del **mismo plan** ya habían entregado: el archivo es un *lock* sobre una implementación existente, no el driver de una implementación nueva. Escribir los arms primero los habría dejado rojos por la ausencia de las guardas —un rojo que ya se demostró en 45-02 con el mismo mecanismo— y no por la propiedad que este plan protege.

El plan resuelve esto explícitamente sustituyendo el gate RED por **dos demostraciones dirigidas de no-vacuidad** (criterios de aceptación 3 y 4 de la Task 3): romper el orden en un driver y la forma en otro, pegar cada rojo, y restaurar. Ambas están en §2 y §3 de este documento, y cada una pone rojo **sólo** al arm que le corresponde — evidencia más fuerte que un RED genérico, porque prueba que los dos arms son independientes y que ninguno es vacío.

Secuencia verificada en `git log`: `ee72b4f` (feat) → `3de6368` (feat) → `a573a91` (test). Sin fase REFACTOR: la implementación son 4 bloques análogos sin duplicación que limpiar más allá de la copia local deliberada.

## Verificación de las amenazas del `<threat_model>`

| Threat ID | Mitigación entregada | Evidencia |
|---|---|---|
| T-45-10 (los 6 sitios restantes) | Digest sobre el par `[expected, actual]` en las 6 claves + arms 4/5 por AST sobre los 7 sitios; matriz con identidad de baseline segregado por venue | 6 arms verdes; tabla de §4 con las 7 líneas |
| T-45-11 (`finding_fids` de los 2 type drift de iol) | El no-op es `continue` sin `append`; el arm 5 asserta que ningún cuerpo de guarda llama a `_next_fid` ni a `append_finding` | `git diff -U0 main_iol.py` muestra exactamente 2 líneas `+` con `continue`; arm 5 verde |
| T-45-12 (no-op con forma equivocada) | Arm 5 (forma por sitio) + arm 6 (contrato de tupla en runtime) + rojo de §3 | `assert ['return-desnudo'] == ['return-tupla-("PASS", …)']` con el no-op uniformado |
| T-45-13 (tampering del ledger committeado) | `monkeypatch` de `_FINDINGS_DIR`, `_SCHEMA_DIR` y `_SCHEMA_FILES` en la fixture nueva de higyrus | `git status --porcelain .planning/verification/` vacío tras cada corrida |
| T-45-14 (lock de substring-membership de matriz) | La pertenencia se prueba sobre `drift_key`, un local ligado, en los 5 drivers | `verification/test_main_matriz_skip_line_shape.py` verde dentro de los 51 passed |
| T-45-SC | accept — sin dependencias nuevas (`hashlib`/`json` son stdlib) | `uv.lock` sin tocar |

## Issues Encountered

Ninguno. `main_higyrus._SCHEMA_FILES` se construye en tiempo de import con rutas absolutas bajo `.planning/verification/schemas/`, así que patchear sólo `_SCHEMA_DIR` no habría alcanzado para la fixture del arm 6 — el plan ya lo anticipaba en su `<read_first>` y la fixture reemplaza también el dict.

## Requirements

**`HARN-01` sigue PARCIAL — su checkbox en `REQUIREMENTS.md` se deja abierto deliberadamente.** Los **7 de 7** sitios de D-02 están corregidos y pinneados, y las tres propiedades (colapso, no-colapso, fid no quemado) más las dos estructurales (orden, forma) tienen lock. Lo que falta para cerrarlo es el enrolamiento de `verification/test_drift_dedupe_falsification.py` en el allowlist explícito del job `lint` de `.github/workflows/ci.yml`: hasta entonces el lock existe pero **no corre en CI**, y D-11 exige que ese edit llegue en el cambio consolidado del plan 45-05. Marcar el requisito completo acá afirmaría en el ledger una protección que ninguna corrida automática ejerce todavía.

## User Setup Required

None — no external service configuration required. Este plan no corre drivers en vivo ni lee ningún `.env`; todo el ejercicio es contra `tmp_path`.

## Next Phase Readiness

- **45-05 tiene el archivo listo para el allowlist consolidado (D-11):** `verification/test_drift_dedupe_falsification.py`, 6 arms verdes standalone. Su docstring ya declara ese enrolamiento como pendiente de ese plan.
- **45-05 tiene dos cosas más que declarar por escrito**, ambas nombradas en el plan: (a) que las ramas hermanas `missing assumed key` de `main_iol.py` quedan fuera de D-02 a propósito, y (b) el censo de sitios de drift = 7 como límite deliberado.
- **Sin bloqueos.** Espejo parcial de CI limpio (§5), `.planning/verification/` intacto.

## Self-Check: PASSED

- `main_iol.py` — FOUND (modificado, `_seen_drift_keys` ×7, mypy limpio)
- `main_higyrus.py` — FOUND (modificado, `_seen_drift_keys` ×3)
- `main_matriz.py` — FOUND (modificado, `_seen_drift_keys` ×3, clave = `file_path.name` línea 615)
- `main_ambito_financiero.py` — FOUND (modificado, `_seen_drift_keys` ×3)
- `verification/test_drift_dedupe_falsification.py` — FOUND (6 arms, 6 collected)
- Commit `ee72b4f` — FOUND (Task 1)
- Commit `3de6368` — FOUND (Task 2)
- Commit `a573a91` — FOUND (Task 3)

---
*Phase: 45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti*
*Completed: 2026-09-01*
