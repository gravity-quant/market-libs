---
phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets
plan: 01
subsystem: api
tags: [python, dataclasses, mypy-strict, null-object, iol-client, safemodel, pytest]

# Dependency graph
requires:
  - phase: 30-modelos-tipados-iol
    provides: "Cotizacion / Punta / Titulo / Instrumento como SafeModel frozen dataclasses, y el round-trip to_dict() contra los schemas committeados"
  - phase: 35-null-object-nobj
    provides: "La rama de colapso NOBJ-02 del walker (_decode.py:448-452 para listas, :504-505 para modelos anidados), SafeModel.empty() y SafeModel.__bool__"
  - phase: 36-market-data-null-objects
    provides: "El precedente D-04 del mismo retype sobre MarketDataSnapshot.entries, y la clase de defecto D-05 (falsa procedencia en docstrings)"
provides:
  - "Cotizacion.puntas declarado list[Punta] — no-Optional, sin default de dataclass"
  - "Titulo.puntas declarado Punta — Null Object, no-Optional, sin default de dataclass"
  - "Garantía de acceso encadenado sin guard: quote.puntas[0].precioCompra y titulo.puntas.precioCompra typechequean bajo mypy --strict y no levantan"
  - "7 aserciones migradas en test_models.py que fijan la semántica Null Object (idioma D-06: bool(...) is False + == Punta.empty())"
  - "verification/snapshots/iol-client-surface.txt regenerado — la firma posicional pública de iol-client refleja las dos anotaciones"
affects: [38-02-ratchet-check-surface-types, 38-03-readme-breaking-callout, 38-04-censo, 39-contabilidad-triples, 40-bump-breaking-coordinado]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Null Object por anotación: el colapso lo implementa el walker congelado, no un default de dataclass ni un __post_init__"
    - "Absorción de deriva de round-trip en el valor ESPERADO del test, nunca en la captura de wire committeada"

key-files:
  created: []
  modified:
    - packages/iol-client/src/iol_client/models.py
    - packages/iol-client/tests/test_models.py
    - packages/iol-client/tests/test_null_object.py
    - verification/snapshots/iol-client-surface.txt

key-decisions:
  - "Cero default_factory y cero reordenamiento de campos: el colapso a [] / Punta.empty() lo produce el walker NOBJ-02, no un default de Python (D-01)"
  - "La deriva del round-trip de la serie histórica se absorbe en el valor esperado del test con la causa dicha; la captura live 2026-06-06 queda intacta (T-38-02)"
  - "Sin edit espejo en client.py / aio.py: ambas superficies delegan en los parsers de _core.py y no contienen ninguna referencia a puntas — la obligación sync/async se descarga por demostración (surface_parity verde), no por duplicación"
  - "_decode.py permanece byte-frozen; el borde de validación de entrada no se ensancha — un puntas mal tipado sigue emitiendo su registro y levantando bajo strict_decode"

patterns-established:
  - "Idioma de aceptación D-06 en par: bool(x) is False junto a x == Modelo.empty(), nunca el predicado de truthiness solo"
  - "Procedencia citada por línea: cada docstring que explica un cero de divergencia nombra la rama del walker que lo produce (D-05)"

requirements-completed: [NOBJ-IOL-01]

# Metrics
duration: 6min
completed: 2026-08-29
status: complete
---

# Phase 38 Plan 01: Null Objects para `puntas` en iol-client — Summary

**`Cotizacion.puntas` es ahora `list[Punta]` y `Titulo.puntas` es `Punta`, ambos no-Optional y sin default de dataclass: `titulo.puntas.precioCompra` typechequea bajo mypy --strict y devuelve `0.0` cuando el wire no mandó libro, sin un solo guard de nulidad.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-08-29T20:02:52Z
- **Completed:** 2026-08-29T20:08:31Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Los dos últimos links `None` de la cadena de decode de iol quedaron cerrados. `null`, clave ausente y `[]` colapsan los tres a la lista vacía (Cotizacion) o a la instancia vacía y falsy (Titulo), **con cero registros de divergencia** — medido, no supuesto.
- La superficie pública de `iol-client` quedó congelada con las anotaciones nuevas: el snapshot regenerado difiere en exactamente 2 líneas y sólo en el token de `puntas`; orden de campos y las otras 18 anotaciones de cada firma son byte-idénticas.
- El borde de validación de entrada (ASVS V5) no se ensanchó: un `puntas` mal tipado sigue emitiendo su registro (`Cotizacion/.puntas/type/list/int` y `Punta/.puntas/non_dict/Punta/int`) y sigue levantando `IOLDecodeError` bajo `strict_decode`. Verificado empíricamente además de por la suite.
- La 7ª aserción que rompía —el round-trip de la serie histórica, que no menciona `puntas` en ninguna de sus tres líneas— quedó migrada absorbiendo la deriva en el valor **esperado**, con la causa nombrada y citando el caveat de lossiness ya publicado en el README. La captura live del 2026-06-06 no se tocó.
- 4 pasajes de procedencia en `models.py` y 3 docstrings en los tests reescritos para citar la rama de colapso correcta en lugar del retorno temprano de la rama Union — la clase de defecto D-05 (falsa procedencia sobre una rama que ya no corre) queda cerrada en la misma pasada.

## Task Commits

1. **Task 1: RED — migrar las 7 aserciones, renombrar el test de semántica retirada, corregir la prosa** — `3f67e20` (test)
2. **Task 2 + Task 3: GREEN — flip de las dos anotaciones + snapshot regenerado** — `f93cb2a` (feat)

_Task 3 no lleva commit propio por diseño del plan: el docstring de `verification/regen_snapshots.py` exige commitear el snapshot regenerado en el **mismo** commit que el cambio de fuente que lo justifica. Task 3 se ejecutó antes de commitear Task 2, así que ambos entraron juntos en `f93cb2a` en lugar de commitear y después enmendar._

## Files Created/Modified

- `packages/iol-client/src/iol_client/models.py` — `Cotizacion.puntas: list[Punta]` (línea 235) y `Titulo.puntas: Punta` (línea 334), ambos sin `field(default_factory=...)` y sin mover de posición. Reescritos: el bullet de `Cotizacion` que agrupaba `puntas` con los dos campos que siguen Optional, la frase espejo de `Titulo`, y los dos pasajes del docstring de módulo que hedgeaban la garantía de acceso encadenado.
- `packages/iol-client/tests/test_models.py` — 7 aserciones migradas, `test_puntas_nula_queda_nula` renombrado a `test_puntas_nula_colapsa_a_lista_vacia`, el round-trip de serie histórica con el valor esperado corregido y comentado, 2 docstrings de procedencia reescritos y los 2 bullets del docstring de módulo que enumeran las formas de `puntas`.
- `packages/iol-client/tests/test_null_object.py` — una sola frase del docstring de `_perturb` corregida: afirmaba como hecho que `Titulo.puntas` es `Punta | None` (RESEARCH F-5). Cero cambios de lógica; el piso del roster (`>= 4`, línea 226) intacto.
- `verification/snapshots/iol-client-surface.txt` — regenerado con `regen_snapshots.py`. Líneas 11 y 21: `puntas: 'list[Punta] | None'` → `'list[Punta]'` y `puntas: 'Punta | None'` → `'Punta'`.

## Decisions Made

- **Task 2 y Task 3 en un solo commit.** El plan lo pide explícitamente (regla del docstring de `regen_snapshots.py`) y da dos caminos: commitear Task 2 y enmendar, o commitear los dos juntos. Se eligió el segundo — no deja un commit intermedio con la fuente cambiada y el snapshot desactualizado, que es exactamente el estado que `verification/test_public_surface.py` reprueba.
- **`test_titulo_from_api_empty_dict_yields_typed_zeros` recibe el par D-06 completo**, no sólo la aserción de igualdad. En estado RED la mitad de truthiness pasa sola (`bool(None) is False`), así que el par no aporta señal RED extra — pero es la mitad que atrapa la regresión futura en la que `puntas` pase a ser cualquier valor falsy que no sea el Null Object (RESEARCH Pitfall 4).
- **Las dos aserciones `is not None` de las líneas 264 y 389 se dejaron en pie.** RESEARCH A4: `warn_unreachable` está apagado, así que siguen siendo legales; sacarlas es higiene, no requisito, y habría ensanchado el diff del commit RED sin ganancia.

## Deviations from Plan

None - plan executed exactly as written.

Los tres criterios de aceptación numéricos del plan salieron exactos sin ajuste: `7 failed, 19 passed` en el gate RED con las 7 node IDs enumeradas y todas `AssertionError`; `289 passed` restaurado en GREEN; y `2 added / 2 deleted` en el snapshot, con `git diff | grep -c '^[+-]'` devolviendo 6.

## Issues Encountered

None.

## TDD Gate Compliance

Secuencia de gates verificada en el log:

1. **RED** — `3f67e20` `test(38-01): ...` — 7 tests fallando con `AssertionError` contra `models.py` sin tocar (`git status --porcelain packages/iol-client/src/` vacío en el momento del commit).
2. **GREEN** — `f93cb2a` `feat(38-01): ...` — los 7 en verde, suite completa de vuelta en 289.
3. **REFACTOR** — no aplicado. El cambio GREEN es un flip de dos anotaciones; no hay nada que limpiar y un commit `refactor` vacío sería ruido.

## Verification Results

| Check | Resultado |
|---|---|
| `pytest packages/iol-client -q` | `289 passed` (baseline F-13 restaurado) |
| `pytest packages/higyrus-client -q` | `289 passed` |
| `pytest packages/ambito-financiero-client -q` | `208 passed, 1 deselected` |
| `pytest packages/wallets-client -q` | `10 passed` |
| `mypy packages/iol-client` | `Success: no issues found in 30 source files` |
| `ruff check` + `ruff format --check` | limpio, 30 archivos |
| `tools/check_decode_intactness.py` | exit 0 — 5 copias reducen al hash canónico `a1f00c824348164c` |
| `tools/check_uniform_structure.py` | exit 0 |
| `tools/check_surface_types.py` | exit 0 — `0 violations` (el predicado no se ensancha hasta 38-02) |
| `pytest packages/*/tests/test_surface_parity.py` | `18 passed` (6 paquetes — descarga SC-4 por demostración) |
| `pytest verification/test_public_surface.py` | `4 passed` |
| `git diff --numstat -- verification/snapshots/` | 1 archivo, `2 / 2` |
| `git diff --name-only -- uv.lock` | vacío |
| `git diff --name-only HEAD~2..HEAD` | exactamente los 4 archivos previstos |

Verificación empírica adicional de los criterios de éxito del plan (script descartable, no commiteado):

- `titulo.puntas.precioCompra` → `0.0` con la clave ausente, `0.0` con `null`, `3.0` con el dict poblado (polimorfismo de Phase 30 intacto). `bool(...)` es `False` en los dos primeros y `True` en el tercero; `== Punta.empty()` sostiene en los dos primeros.
- `quote.puntas` → `[]` con clave ausente, con `null` y con `[]`; `quote.puntas[0].precioCompra` → `3.0` con la lista poblada.
- `mypy --strict` sobre ese script: `Success` — el acceso encadenado no necesita narrowing.

## Threat Mitigations Verified

| Threat ID | Verificación |
|---|---|
| T-38-01 (Tampering / ASVS V5) | `puntas: 7` sigue emitiendo `('Cotizacion', '.puntas', 'type', 'list', 'int')` y `('Punta', '.puntas', 'non_dict', 'Punta', 'int')`, y levanta `IOLDecodeError` bajo `strict_decode` en ambos modelos. El silencio queda licenciado sólo para null/ausente. |
| T-38-02 (Repudiation) | `git status --porcelain .planning/verification/schemas/` vacío en el commit RED y en el GREEN — la captura 2026-06-06 no se reescribió. |
| T-38-03 (Tampering / snapshot) | Snapshot regenerado por script, nunca editado a mano; diff acotado a 2 líneas / 2 tokens y verificado con `grep -c '^[+-]' == 6`. |
| T-38-04, T-38-05, T-38-SC | Aceptados sin cambio: `models.py` es el único archivo de fuente en el diff, no se tocó ningún path de credenciales, y `uv.lock` no se movió. |

## Known Stubs

Ninguno. El plan no introduce placeholders: las dos anotaciones están cableadas contra el walker que ya implementa la semántica, y las 7 aserciones migradas afirman valores medidos.

## Threat Flags

Ninguna superficie nueva. El plan no agrega endpoint, path de auth, lectura de credencial, dependencia ni archivo ejecutable.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **38-02 (ratchet en `tools/check_surface_types.py`)** desbloqueado: los 2 sitios que el predicado D-11 enrojecería ya están arreglados, así que el gate widening puede aterrizar con cero colateral (RESEARCH F-6). El gate hoy imprime `0 violations` con el predicado angosto.
- **38-03 (callout BREAKING en el README de iol)** desbloqueado y ahora verídico: la ruptura que el callout describe está en `main`.
- **38-04 (censo)** desbloqueado: el roster cambió, la aritmética no (RESEARCH F-10 — 2 filas de campo agregadas, 0 triples retirados).
- **Phase 40** sigue siendo dueña del bump de versión: ni `__version__` ni ningún `pyproject.toml` se tocó acá.
- Sin blockers.

## Self-Check: PASSED

- 4 archivos de código verificados en disco; `38-01-SUMMARY.md` verificado en disco.
- Commits `3f67e20` y `f93cb2a` verificados con `git log --oneline --all`.
- Números de línea citados re-verificados contra el archivo (`models.py:235` y `:334`).

---
*Phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets*
*Completed: 2026-08-29*
