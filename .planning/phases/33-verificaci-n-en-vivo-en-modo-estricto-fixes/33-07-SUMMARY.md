---
phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
plan: 07
subsystem: market-data-client
tags: [live-verification, in-cycle-fixes, shape-change, semver-breaking, findings-triage, cycle-closure, non-vacuity, sync-async-parity]

requires:
  - phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
    provides: "`33-CENSUS.md` con los 24 triples en vivo de market-data, la disposición de S-1..S-5 y los cuatro destinos de re-scope (33-05)"
  - phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
    provides: "DT-07 cerrado y la disposición record-only de los cuatro alias `Literal` de matriz (33-06)"
  - phase: 29-decoder-observable
    provides: "el walker por-campo, el modo estricto por `ContextVar`, los 12 locks del contrato de agregación y las cinco estructurales S-1..S-5 de `29-SIZING.md`"
  - phase: 31-ops-endpoints
    provides: "`market_data_client.models` con `FeedMarket`/`FeedIngestor`/`HealthFeed` y la disciplina T-31-17 (ningún campo sobre-declarado `Optional`)"
provides:
  - "`CalendarConfigPreview` + `PreviewMarket` — el sobre de veredicto de `POST /calendar/config/preview` deja de decodificarse como `CalendarConfig`"
  - "`_core.parse_preview_calendar_config_response` — el parser que separa preview de config"
  - "el desenvolvimiento del sobre en `parse_instruments_response` y `parse_segments_response` (S-1)"
  - "`MarketDataSnapshot.entries` / `.market_data` / `.staleness_seconds` y `Symbol.created_at` / `.updated_at` ensanchados a `Optional`"
  - "el guard de `Optional` en `_apply_mapping_policy`, sin el cual el ensanche de `market_data` era inefectivo"
  - "cuatro archivos de regresión mockeados bajo `packages/market-data-client/tests/` — la única ruta que CI corre — cada uno en forma sync y async"
  - "triage completo y exhaustivo de los 76 findings `OPEN` (38 FIXED / 6 EXPECTED / 32 NO-FIX); cero quedan `OPEN`"
  - "`verification/test_cycle_closure_phase33.py` — cierre de ciclo con piso numérico por paquete y exención argumentada para las dos filas de piso cero"
  - "`SHAPE-MD-REF-33` en `ROADMAP.md` § Backlog — la mitad de forma de S-1 que este ciclo NO cerró, con su razón registrada"
  - "el bump set de la Phase 34 ampliado: `market-data-client` 0.4.0 → **0.5.0**, source-breaking"
affects: [34-releases-por-paquete]

actuals:
  tokens: 21500
  tasks: 3
  commits: 9

tech-stack:
  added: []
  patterns:
    - "un cambio de forma de modelo publicado sólo se aplica si el operator lo autorizó nominalmente; el que no está en la lista se rutea, no se cuela junto a los que sí"
    - "el RED de un fix que introduce nombres nuevos se escribe como ASERCIÓN DE VALOR (`to_dict()` contra el body real) y no por importación del nombre futuro: así el fallo reporta el defecto y no un `ImportError`"
    - "un ensanche a `Optional` admite `None` y nada más — cada familia lleva un test dedicado que prueba que un valor de tipo equivocado sigue siendo divergencia y sigue siendo fatal en estricto"
    - "un test que pineaba la semántica vieja se REFORMULA sobre un portador nuevo, nunca se borra: la propiedad sobrevive aunque su ejemplo cambie"
    - "una exención de no-vacuidad se argumenta positivamente (AST + evidencia de corrida) o se declara honestamente vacua con su destino nombrado; nunca se escribe `>= 0`"

key-files:
  created:
    - packages/market-data-client/tests/test_reference_envelope_unwrap.py
    - packages/market-data-client/tests/test_preview_calendar_config_envelope.py
    - packages/market-data-client/tests/test_snapshot_no_data_row.py
    - packages/market-data-client/tests/test_symbol_write_ack_timestamps.py
    - verification/test_cycle_closure_phase33.py
    - .planning/phases/33-verificaci-n-en-vivo-en-modo-estricto-fixes/33-07-SUMMARY.md
  modified:
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/src/market_data_client/_core.py
    - packages/market-data-client/src/market_data_client/client.py
    - packages/market-data-client/src/market_data_client/aio.py
    - packages/market-data-client/src/market_data_client/__init__.py
    - packages/market-data-client/tests/test_decode.py
    - packages/market-data-client/tests/test_models.py
    - packages/market-data-client/tests/test_calendar_write.py
    - packages/market-data-client/tests/test_calendar_write_async.py
    - packages/market-data-client/tests/test_public_surface_market_data.py
    - .planning/verification/market-data-client-findings.md
    - .planning/phases/33-verificaci-n-en-vivo-en-modo-estricto-fixes/33-CENSUS.md
    - .planning/ROADMAP.md

key-decisions:
  - "Las tres disposiciones `fix-shape-now` se aplicaron y la consecuencia de semver NO se absorbió acá: `__version__` y `pyproject` siguen en 0.4.0 a propósito, porque la opción que el operator eligió dice literalmente «que la Phase 34 cargue la consecuencia». El bump 0.4.0 → 0.5.0 queda escrito en el criterio 1 de la Phase 34, no ejecutado en la 33"
  - "S-1 se cerró a MEDIAS y la otra mitad se ruteó a `SHAPE-MD-REF-33` en vez de arreglarse: corregir los campos declarados de `Instrument`/`Segment` es un cuarto cambio de forma de modelo publicado, y el checkpoint 33-07 Task 1 gatea esa clase. El operator autorizó tres y éste no estaba entre ellos (T-33-44)"
  - "El ensanche de `MarketDataSnapshot.market_data` era inefectivo sin tocar `_apply_mapping_policy`: `_is_mapping` desenvuelve `Optional` (tiene que hacerlo), así que el pase seguía substituyendo `{}` y reportando `missing` una línea después de que el walker honró el `| None`. El guard vive en el pase de market-data, NO en `_mapping_value`, que sigue byte-idéntico al de matriz"
  - "Los cuatro campos del record de divergencia quedaron byte-verbatim en las 76 promociones; sólo se movió `status` (+ `regression` en los 38 FIXED). La razón de cada disposición vive en `33-CENSUS.md`, no dentro del finding: P-01 prohíbe componer un campo del finding con algo fuera de las seis claves"
  - "Las dos filas de piso cero del gate de no-vacuidad no llevan `>= 0`. ámbito lleva una exención argumentada por AST + la línea SUMMARY verbatim de su corrida; higyrus lleva la declaración explícita de que su verde es HONESTAMENTE vacuo por ausencia de medición, con `LIVE-HIGY-33` aseverado como destino"
  - "El criterio 1 se surfacea como GATE HUMANO ABIERTO (PARCIAL, 3 de 5 paquetes medidos), no se da por cerrado. La aceptación del operator de la cobertura parcial no convierte 3 en 5"

patterns-established:
  - "Un cambio de contrato de un wheel publicado no se aplica «de paso» junto a los autorizados: si no está nominalmente en la disposición, se rutea con destino nombrado aunque el fix esté a tres líneas de distancia"
  - "Arreglar un defecto que tapaba a otro obliga a registrar el que queda expuesto en el mismo commit — el fix no puede dejar un hallazgo nuevo sin destino"
  - "El RED de un fix que crea nombres nuevos se escribe para fallar por VALOR, no por importación"

requirements-completed: []

coverage:
  - id: D38
    description: "Cada divergencia confirmada que el operator dispuso arreglar está corregida dentro de su paquete, espejada en las dos superficies vía el módulo compartido, sin introducir dependencia cross-package (criterio 2, C-2, C-3)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "packages/market-data-client/tests/test_reference_envelope_unwrap.py (6 casos, sync+async), test_preview_calendar_config_envelope.py (5), test_snapshot_no_data_row.py (6), test_symbol_write_ack_timestamps.py (5) — 22 passed"
        status: pass
      - kind: unit
        ref: "packages/market-data-client/tests/test_surface_parity.py — 3 passed tras cada fix"
        status: pass
      - kind: other
        ref: "los cuatro fixes viven en _core.py / models.py, por donde despachan client.py y aio.py; ningún import cross-package agregado (ruff TID + import-linter verdes)"
        status: pass
    human_judgment: false
  - id: D39
    description: "Cada fix carga un test de regresión MOCKEADO bajo `packages/<pkg>/tests/`, probado fail-first, en forma sync y async, y el bullet `Regression:` del finding resuelve a él (criterio 2, P-8, T-33-41, T-33-43)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "RED registrado por commit: 182b410 (5 rojos), 978d2ff (3 rojos por valor), 6f5ef36 (4 rojos), 24aa142 (4 rojos)"
        status: pass
      - kind: other
        ref: "`grep -rc 'Regression:.*verification/' .planning/verification/*-findings.md` → 0 en los cinco archivos"
        status: pass
      - kind: other
        ref: "los 22 tests usan pytest-httpx con token pre-sembrado por conftest; cero requests reales, cero grants de Auth0"
        status: pass
    human_judgment: false
  - id: D40
    description: "Todo finding `OPEN` que la corrida en vivo escribió tiene disposición explícita; nada quedó `OPEN` y nada se silenció (criterio 5, P-03)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "partición exhaustiva y disjunta aseverada ANTES de promover: 38 FIXED + 6 EXPECTED + 32 NO-FIX == los 76 OPEN, con assert de igualdad de conjuntos"
        status: pass
      - kind: other
        ref: "`33-CENSUS.md` § Re-scope enmendado: fila nueva SHAPE-MD-REF-33 con paquete, modelo, field path, especie y destino; cero celdas TBD/later/a futuro"
        status: pass
      - kind: other
        ref: "SHAPE-MD-REF-33 resuelve a una entrada de ROADMAP § Backlog agregada en el MISMO commit (68caaae)"
        status: pass
    human_judgment: true
    rationale: "Decidir que la mitad de forma de S-1 se rutea en vez de arreglarse —teniendo el fix a la vista y el resto del paquete ya abierto— es un juicio de alcance contra un gate de contrato, no un chequeo mecánico."
  - id: D41
    description: "`verify_cycle_closure` devuelve `(True, [])` para los cinco paquetes y el conteo inspeccionado se movió por encima del baseline medido en todo paquete que recibió promociones (criterio 4, D-11, P-7, T-33-40)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_cycle_closure_phase33.py — 11 passed (5 parametrizados x2 + el gate de la propia exención)"
        status: pass
      - kind: other
        ref: "conteos pre → post: ámbito 0→0, higyrus 0→0, iol 1→1, matriz 1→1, market-data 50→88 (+38)"
        status: pass
      - kind: other
        ref: "no-vacuidad probada por 4 falsificaciones, todas revertidas: demote de F-82 → 'assert 87 >= 88'; Regression rota → not green ['F-102']; ClassDef plantada en ámbito → cae la exención D-12; LIVE-HIGY-33 renombrado → cae P-03"
        status: pass
    human_judgment: true
    rationale: "Decidir que la fila de higyrus lleve una vacuidad DECLARADA en vez de un piso numérico —y que eso es más honesto que un `>= 0` que pasaría por la razón equivocada— es un juicio sobre qué significa una aserción, no un conteo."
  - id: D42
    description: "Ninguna copia de `_decode.py`, ningún alias `Literal` de matriz y ningún `uv.lock` se movieron; `verification/` no empeoró respecto de `33-BASELINE.md` (P-04, T-33-45, P-13)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "`uv run python tools/check_decode_intactness.py` exit 0 (5 copias → un hash ac14868282ad0a5c); `git diff --stat` vacío sobre `packages/*/src/*/_decode.py`, sobre `matriz_client/types.py` y sobre `uv.lock`"
        status: pass
      - kind: other
        ref: "`uv run pytest verification -q --tb=no -rfE` → 19 failed / 387 passed / 19 errors contra el baseline 19/368/19: MISMO set rojo node-id por node-id, +19 verdes nuevos"
        status: pass
    human_judgment: false

duration: 42min
completed: 2026-08-26
status: complete
---

# Phase 33 Plan 07: fixes in-cycle, triage completo y criterio 4 no-vacuo Summary

**Los 19 triples que el censo dirigió a este plan quedaron cerrados —ninguno recortado, ninguno
agregado— y el criterio 4 deja de ser un verde que no inspecciona nada: `market-data-client` pasa
de 50 a 88 findings `CONFIRMED`/`FIXED` inspeccionados, con piso numérico derivado de mediciones y
probado por falsificación. El resultado con más filo, sin embargo, es lo que este plan **no**
arregló: al desenvolver el sobre de S-1 apareció una divergencia de forma que el `non_dict` terminal
venía tapando, el fix estaba a tres líneas, y no se aplicó — porque el operator autorizó
nominalmente tres cambios de forma y ése no era uno. Quedó ruteado a `SHAPE-MD-REF-33`, visible y
fatal en estricto en vez de silencioso.**

## Performance

- **Duration:** 42 min
- **Started:** 2026-08-27T01:42Z
- **Completed:** 2026-08-27T02:24Z
- **Tasks:** 3 de 3
- **Files created/modified:** 19 (6 nuevos, 13 modificados)

---

## Shape-change dispositions (locked)

Selección del operator en el checkpoint bloqueante de la Task 1, **verbatim**:

```
SC-1: fix-shape-now
SC-2: fix-shape-now
SC-3: fix-shape-now
```

Los tres candidatos, con su identidad reconstruida de `33-CENSUS.md` § Structural findings por
CONTENIDO (no por etiqueta), y las tres son `market-data-client`:

| Id | Hallazgo | Findings en vivo | Disposición |
|---|---|---|---|
| **SC-1** (= **S-2**) | `preview_calendar_config` declarado `-> CalendarConfig` pero el wire devuelve un sobre de preview distinto — 9 campos declarados ausentes, 3 campos reales descartados | `F-121`..`F-132` [async], `F-152`..`F-163` [sync] | **`fix-shape-now`** |
| **SC-2** | `MarketDataSnapshot.entries` / `.market_data` / `.staleness_seconds` declarados no-`Optional` llegan `null` en la fila no-data | `F-72`/`F-73`/`F-75` [sync], `F-92`/`F-93`/`F-95` [async] | **`fix-shape-now`** |
| **SC-3** | `Symbol.created_at` / `.updated_at` declarados `str`, ausentes de los tres acks de escritura | `F-141`/`F-142` [sync], `F-110`/`F-111` [async] | **`fix-shape-now`** |

**Las tres son source-breaking y las tres se suman al bump set de la Phase 34: `market-data-client`
0.4.0 → 0.5.0.** Quedó escrito en `ROADMAP.md` § Phase 34 criterio 1, junto al `iol-client`
0.2.0 → 0.3.0 que DT-08 ya tenía registrado — **dos** paquetes source-breaking, no uno, y los dos
necesitan callout de changelog.

**`__version__` y `pyproject` NO se movieron en esta fase, a propósito.** La opción que el operator
eligió dice literalmente *"Fix the model shape in this phase and let **Phase 34** carry the semver
consequence"*. Bumpear acá habría shipeado un `0.5.0` que nadie publicó y habría duplicado la
decisión de release. Los docstrings dicen *"BREAKING since 0.5.0"* como nota de changelog
hacia adelante, que es su rol.

**Ninguna disposición fue `defer-shape-to-named-phase`**, así que no hay destinos que la Task 2
tuviera que agregar por esta vía. El destino nuevo que sí se agregó (`SHAPE-MD-REF-33`) nació de un
hallazgo distinto — ver Deviations #1.

**S-3, S-4 y S-5 (matriz) siguen `COULD-NOT-DECIDE` y ruteados a `LIVE-MATZ-33`.** Este plan no
tocó una sola línea de `matriz-client`: `git diff --stat` sobre `matriz_client/types.py` está
vacío y las 84 pruebas de decode/types del paquete siguen verdes.

---

## Los cuatro fixes, con su evidencia RED

Ordenados por consecuencia, como el censo los ordenó.

### 1. S-1 — los dos parsers de catálogo no desenvolvían el sobre

| | |
|---|---|
| **Paquete / modelos** | `market-data-client` — `Instrument`, `Segment` |
| **Field path** | raíz (`non_dict`) |
| **Superficies tocadas** | `_core.py` (una sola: `client.py` y `aio.py` despachan por ahí) |
| **Regresión** | `packages/market-data-client/tests/test_reference_envelope_unwrap.py` — 6 casos |
| **RED** | commit `182b410`: **5 rojos**. `get_instruments` devolvía **6** filas all-default (una por clave del sobre `{catalogue, count, items, limit, offset, total}`), `get_segments` **2**. El sexto caso —la lista pelada— ya pasaba y debía seguir pasando |
| **GREEN** | `adaaa38` — 6 passed |
| **Findings** | `F-82`/`F-83` [sync], `F-102`/`F-103` [async] → `FIXED` |

El caveat que `29-SIZING.md` dejó abierto (*"puede que el servidor haya introducido el sobre después
de que se escribió el cliente"*) ya lo había cerrado 33-05; este plan lo arregló. Es el mismo modo
de falla que `parse_calendar_response` tenía antes de D-12 y `parse_symbols_response` antes de D-11.

**Cerrado a medias, y la mitad restante tiene destino** — ver Deviations #1.

### 2. SC-1 / S-2 — el sobre de preview recibió su propio modelo

| | |
|---|---|
| **Paquete / modelo** | `market-data-client` — `CalendarConfig` → **`CalendarConfigPreview`** + **`PreviewMarket`** |
| **Field path** | 9 `missing` (`.close`, `.editable`, `.enabled`, `.env_bypass`, `.open`, `.pre_open_minutes`, `.source`, `.timezone`, `.updated_by`) + 3 `extra` (`.market_after`, `.requires_confirmation`, `.valid`) |
| **Superficies tocadas** | `models.py`, `_core.py`, `client.py:695`, `aio.py:695`, los dos shims module-level, `__init__.py` |
| **Regresión** | `packages/market-data-client/tests/test_preview_calendar_config_envelope.py` — 5 casos |
| **RED** | commit `978d2ff`: **3 rojos**, todos por **aserción de valor** (`to_dict()` contra el body real), no por `ImportError` — el fallo reporta el `CalendarConfig` de ceros tipados fabricado. Ver Deviations #2 |
| **GREEN** | `46f97f6` — 5 passed |
| **Findings** | `F-121`..`F-132` [async], `F-152`..`F-163` [sync] → `FIXED` (24) |

`29-SIZING.md` predijo este set **campo por campo** y la corrida en vivo devolvió exactamente esos
12. `POST /calendar/config/preview` contesta *"¿sería válida esta ventana, y necesita segunda
opinión?"*, no *"¿cuál es la configuración?"*: las dos formas no comparten una sola clave.

Dos decisiones de modelado dentro del fix:

- **`PreviewMarket` NO reusa `FeedMarket`**, que se le parece mucho. `FeedMarket` declara además
  `enabled` y `last_business_day`, y ninguna de las dos existe en este sobre: reusarlo habría
  fabricado dos `missing` permanentes por llamada — el mismo defecto, un nivel más abajo.
- **Ningún campo se declaró `| None`.** Las dos capturas committeadas muestran todos los campos
  poblados, y un `Optional` sobre-declarado esconde ese campo del censo para siempre (T-31-17, la
  lógica option-b de 31-04 aplicada acá).

El **request quedó byte-idéntico** y eso está pineado, no afirmado: el endpoint se publicó en
v0.4.0 y el cambio es RESPONSE-ONLY. Mismo criterio que `test_v040_request_pin.py`.

### 3. SC-2 — la fila sin datos de `/marketdata` es forma legítima

| | |
|---|---|
| **Paquete / modelo** | `market-data-client` — `MarketDataSnapshot` |
| **Field path** | `.entries`, `.market_data`, `.staleness_seconds` (`missing`) |
| **Superficies tocadas** | `models.py` (definición + `_apply_mapping_policy`) |
| **Regresión** | `packages/market-data-client/tests/test_snapshot_no_data_row.py` — 6 casos |
| **RED** | commit `6f5ef36`: **4 rojos** — dos por valor (`[]`/`{}`/`0.0` fabricados) y dos por el `MarketDataDecodeError` que el modo estricto levantaba |
| **GREEN** | `9992653` — 6 passed |
| **Findings** | `F-72`/`F-73`/`F-75` [sync], `F-92`/`F-93`/`F-95` [async] → `FIXED` (6) |

**Por qué ensanchar y no substituir en el parser.** `fix-parser-keep-shape` estaba disponible como
opción y es la equivocada acá: fabricar `0.0` / `[]` / `{}` para un `null` que el vendor manda
legítimamente es re-introducir el cero tipado silencioso que este milestone existe para eliminar.
La opción lo dice con todas las letras y el operator eligió el ensanche.

**El ensanche admite `None` y NADA más.** Un `entries` que llega `str` sigue siendo divergencia y
sigue siendo fatal en estricto: hay un test dedicado
(`test_a_wrong_typed_value_is_still_a_divergence`) precisamente para que el fix no haya cambiado
una substitución silenciosa por una amnistía.

**El fix no estaba completo sin tocar `_apply_mapping_policy`** — ver Deviations #3.

### 4. SC-3 — el ack de escritura de symbols no trae timestamps

| | |
|---|---|
| **Paquete / modelo** | `market-data-client` — `Symbol` |
| **Field path** | `.created_at`, `.updated_at` (`missing`) |
| **Superficies tocadas** | `models.py` |
| **Regresión** | `packages/market-data-client/tests/test_symbol_write_ack_timestamps.py` — 5 casos |
| **RED** | commit `24aa142`: **4 rojos** — dos por los `''` fabricados y dos por el raise estricto sobre `.created_at`. El quinto caso (el control de `GET /symbols`, que sí manda los dos) ya pasaba |
| **GREEN** | `96a6b74` — 609 passed en el paquete |
| **Findings** | `F-141`/`F-142` [sync], `F-110`/`F-111` [async] → `FIXED` (4) |

`Symbol` sirve **cuatro** endpoints con tres formas de body y sólo una manda los dos timestamps.
La declaración vieja (`str = ""`) fabricaba dos strings vacíos en cada escritura —indistinguibles
de una fila real con timestamps en blanco— y hacía **fatal toda escritura** bajo `strict_decode`.

---

## Triage: los 76 findings `OPEN`, ninguno sobreviviente

La partición se aseveró **exhaustiva y disjunta contra el archivo real antes de promover nada**
(`assert planned == opens`), así que no pudo quedar uno afuera por olvido:

| Disposición | N | Qué son | Destino |
|---|---:|---|---|
| `FIXED` | **38** | Las cuatro familias de arriba | Cada uno con `Regression:` resolviendo a `packages/market-data-client/tests/…` |
| `EXPECTED` | **6** | 4 `NO-DATA` (`market_data` vacío para el prefix inexistente `__no_such_symbol__`) + 2 `ERROR-MAP` (el `422` del vendor sobre un símbolo que el exchange no lista) | — comportamiento correcto del vendor **y** del cliente |
| `NO-FIX` | **32** | 10 `extra` + 22 `schema drift` | `TYP-MD-EXTRA-33` y `HARN-DRIFT-33` |
| **Total** | **76** | | |

Sobre los dos `ERROR-MAP`: el `422` trae *"el exchange no lista este símbolo"*. Es el servidor
rechazando correctamente y el cliente mapeando correctamente a `MarketDataAPIError`. `EXPECTED` es
la lectura honesta; `FIXED` habría sido una mentira y `OPEN` habría dejado un no-defecto pendiente.

Sobre los 22 de `schema drift`: todos son crecimiento de claves del vendor, y los baselines **no**
se re-basearon (contrato D-25: detectar y reportar, nunca absorber). `NO-FIX` con destino
`HARN-DRIFT-33`, que además absorbe el defecto de higiene del `idempotent_by_title` faltante.

**Los cuatro campos del record quedaron byte-verbatim en las 76 promociones.** Sólo se movió
`status` (y se agregó `regression` en los 38 `FIXED`). La razón de cada disposición vive en
`33-CENSUS.md` y acá, **no dentro del finding**: P-01 prohíbe componer un campo del finding con
algo que no sean las seis claves del record más el endpoint y la superficie, y meter prosa de
triage en `Diff:` habría sido exactamente eso.

**La fidelidad del round-trip se midió antes de promover, no se asumió:**
`_parse_findings` → `_serialize_findings` sobre el archivo real dio **0 líneas de diff**, así que
las 76 llamadas a `append_finding` no pudieron destruir prosa de operador (D-23 / CR-01). Ese
chequeo importaba: el short-circuit de preservación de `append_finding` mira el status
**existente**, no el nuevo, así que promover un `OPEN` re-serializa el archivo entero.

---

## Criterio 4: conteos inspeccionados, pre y post

| Paquete | `verify_cycle_closure` | Pre-fase (medido) | Post-fase | Δ | Piso del gate |
|---|---|---:|---:|---:|---|
| `ambito-financiero-client` | `(True, [])` | **0** | **0** | +0 | *exención argumentada (D-12)* |
| `higyrus-client` | `(True, [])` | **0** | **0** | +0 | *vacuidad declarada (`LIVE-HIGY-33`)* |
| `iol-client` | `(True, [])` | **1** | **1** | +0 | `>= 1` |
| `matriz-client` | `(True, [])` | **1** | **1** | +0 | `>= 1` |
| `market-data-client` | `(True, [])` | **50** | **88** | **+38** | `>= 88` |

**Un PASS con el conteo sin moverse es la señal de alarma, no un resultado** — y cuatro de las
cinco filas están exactamente ahí. Por eso ninguna de las dos filas de piso cero lleva `>= 0`:

- **ámbito** lleva la propiedad D-12 aseverada **positivamente**: cero `ClassDef` y `__all__` vacío
  probados por AST sobre `ambito_financiero_client/models.py` (leído como texto, sin importar el
  paquete), **más** la línea SUMMARY verbatim de su pase estricto transcripta en el censo — que es
  la evidencia de que el driver **corrió** (6 probes en PASS) y no simplemente no hizo nada.
- **higyrus** lleva la vacuidad **declarada**: su verde es honestamente vacuo por ausencia de
  medición, el test asevera que el censo lo dice con esas palabras (`SKIPPED — vendor
  inalcanzable`) y que `LIVE-HIGY-33` sigue nombrado. Taparlo con un piso que pasaría por la razón
  equivocada habría sido peor que no tener el test.
- Un tercer test pinea que **sólo esos dos** pueden llegar a la rama de exención, así que un
  paquete cuyo piso caiga a cero por una edición de baseline aterriza ruidosamente en vez de
  adquirir en silencio una exención que nadie argumentó.

### No-vacuidad probada por falsificación (4 experimentos, todos revertidos)

| # | Experimento | Resultado |
|---|---|---|
| A | Demote de `F-82` de `FIXED` a `OPEN` | `assert 87 >= 88` con el mensaje nombrando baseline 50 + promociones 38 |
| B | `Regression:` de `F-102` apuntando a un test inexistente | `cycle closure is NOT green … ['F-102']` |
| C | Una `ClassDef` plantada en `ambito_financiero_client/models.py` | `ambito … now declares 1 model class(es). D-12 no longer holds` |
| D | `LIVE-HIGY-33` renombrado a `MAS-ADELANTE` en el censo | `lost its named destination … exactly what P-03 forbids` |

`git status` de `.planning/verification/`, `.planning/phases/` y `packages/ambito-financiero-client/`
quedó vacío después de los cuatro.

---

## Criterio 1: **GATE HUMANO ABIERTO** (no cerrado)

33-05 dejó por escrito que 33-07 tenía que surfacear esto en vez de darlo por cerrado. Estado
textual, registrado también en `33-CENSUS.md`:

> El criterio 1 está **PARCIAL — 3 de 5 paquetes medidos en vivo**. Los cinco drivers están
> **cableados** (130/130 probes decorados, probado por `test_probe_context_coverage.py`), pero
> `higyrus-client` (host que no resuelve por DNS) y `matriz-client` (assert de política
> remarkets-only D-MATZ-33) no pudieron **correr**. Ninguna de las dos causas es resoluble desde
> dentro de este plan.

La cobertura parcial fue **aceptada por el operator** para este ciclo. **La aceptación no convierte
3 en 5** y no se registra como si lo hiciera: `LIVE-HIGY-33` y `LIVE-MATZ-33` siguen abiertos y el
gate de no-vacuidad de higyrus asevera, en código, que su verde es vacuo.

Consecuencia para `LIVE-TYP-01`: ver `## Self-Check`.

---

## Task Commits

| Task | Commits |
|---|---|
| **1** — disposición de cambios de forma | *(sin commit propio: la Task 1 prohíbe escribir código y su salida es esta sección del SUMMARY)* |
| **2** — triage + los cuatro fixes | `182b410` (RED S-1) → `adaaa38` (GREEN S-1) → `978d2ff` (RED SC-1) → `46f97f6` (GREEN SC-1) → `6f5ef36` (RED SC-2) → `9992653` (GREEN SC-2) → `24aa142` (RED SC-3) → `96a6b74` (GREEN SC-3) → `68caaae` (triage + censo + ROADMAP) |
| **3** — criterio 4 no-vacuo | `264f678` |

---

## Files Created/Modified

**Nuevos**

- `packages/market-data-client/tests/test_reference_envelope_unwrap.py` *(146 líneas)* — S-1, 6 casos.
- `packages/market-data-client/tests/test_preview_calendar_config_envelope.py` *(183)* — SC-1, 5 casos.
- `packages/market-data-client/tests/test_snapshot_no_data_row.py` *(161)* — SC-2, 6 casos.
- `packages/market-data-client/tests/test_symbol_write_ack_timestamps.py` *(152)* — SC-3, 5 casos.
- `verification/test_cycle_closure_phase33.py` *(268)* — 11 casos.

**Modificados**

- `market_data_client/models.py` — `PreviewMarket` + `CalendarConfigPreview`; tres campos de
  `MarketDataSnapshot` y dos de `Symbol` ensanchados; guard de `Optional` en
  `_apply_mapping_policy`.
- `market_data_client/_core.py` — desenvolvimiento del sobre en los dos parsers de catálogo;
  `parse_preview_calendar_config_response` nuevo.
- `market_data_client/client.py` / `aio.py` — tipo de retorno de `preview_calendar_config` en el
  método y en el shim module-level de cada superficie.
- `market_data_client/__init__.py` — dos nombres nuevos re-exportados y en `__all__`.
- `tests/test_decode.py`, `tests/test_models.py`, `tests/test_calendar_write{,_async}.py`,
  `tests/test_public_surface_market_data.py` — reformulación de lo que pineaba la semántica vieja.
- `.planning/verification/market-data-client-findings.md` — 76 promociones.
- `33-CENSUS.md` — § Re-scope enmendada, triage tabulado, criterio 1 surfaceado.
- `.planning/ROADMAP.md` — `SHAPE-MD-REF-33` nuevo; `TYP-MD-EXTRA-33` de 8 a 5 triples; bump set de
  la Phase 34 ampliado.

---

## Decisions Made

Además de las del frontmatter, en ejecución:

1. **La versión no se bumpeó acá.** Ver `## Shape-change dispositions`. `uv.lock` tampoco se tocó
   (`git diff --stat uv.lock` vacío): la Phase 34 lo refresca **exactamente una vez**, que es su
   contrato.
2. **Los 8 tests que pineaban la semántica pre-ensanche se reformularon, no se borraron.** La
   propiedad CR-03 (*un `dict[...]` REQUERIDO nunca es un `None` silencioso*) se re-ancló sobre un
   fixture module-local `_RequiredMapping`, porque después de SC-2 ningún modelo shipeado declara
   un mapping requerido. Borrar las filas habría retirado un contrato vivo porque cambió su
   ejemplo. El lock 8 (`non_dict` terminal) se sigue aseverando sobre el **set de records**, que es
   la propiedad, aunque el valor pasó de `{}` a `None`.
3. **El RED de SC-1 se escribió para fallar por VALOR.** Ver Deviations #2.
4. **`_mapping_value` quedó byte-idéntico al de matriz.** El guard vive en
   `_apply_mapping_policy`, que es el pase específico de market-data. Ver Deviations #3.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Arreglar S-1 destapó una divergencia de forma que el `non_dict` terminal escondía, y arreglarla habría sido un cuarto cambio de contrato sin autorizar**

- **Found during:** Task 2, al escribir el fixture del RED de S-1 contra el baseline
  `get-instruments.json`
- **Issue:** Mientras el parser iteraba las CLAVES del sobre, cada fila decodificaba con un
  `non_dict` **terminal** en la raíz — y el lock 8 suprime los records por campo debajo de un
  `non_dict`, así que el walker nunca llegaba a los campos. El censo lo registró como **1 triple
  por modelo** y `29-SIZING.md` ya advertía que ese conteo *"subestima el radio de daño"*. Al
  desenvolver el sobre, el walker llega a los campos y aparece lo que estaba tapado:
  **`Instrument`** declara `marketId` e `instrumentType`, que el wire no manda, y no declara
  `market_id`, `currency`, `days_to_maturity`, `maturity`, `outright`, `subscribed` ni `active`,
  que sí manda; **`Segment`** declara `marketSegmentId`/`marketId`/`description` contra un wire que
  manda `segment` y `live_instruments` — **conjuntos disjuntos**, así que toda fila de
  `get_segments()` sale con sus tres campos vacíos.
- **Fix:** El desenvolvimiento se aplicó; la corrección de forma **no**. Es un cambio de modelo
  **publicado desde v0.2.0**, y el checkpoint bloqueante 33-07 Task 1 existe exactamente para esa
  clase (T-33-44). El operator autorizó **tres** cambios de forma nominalmente y éste no estaba
  entre ellos; aplicarlo "de paso" porque el paquete ya estaba abierto habría sido el cambio de
  contrato sin decisión que el checkpoint previene. Se creó el destino **`SHAPE-MD-REF-33`** en
  `ROADMAP.md` § Backlog **en el mismo commit** que lo referencia, con el diff campo por campo
  contra los dos baselines, y se agregó como fila nueva en `33-CENSUS.md` § Re-scope declarada
  explícitamente como *"FILA NUEVA (33-07)"* — no existía cuando 33-05 escribió esa tabla.
- **Por qué el resultado igual es una mejora neta:** antes, `get_instruments()` devolvía 6 filas
  all-default y **una** divergencia; ahora devuelve las filas reales con `symbol`/`segment`/
  `expired` **poblados** (3 de 5 campos declarados) y las dos que faltan **reportadas** campo por
  campo y fatales bajo `strict_decode`. La divergencia pasó de silenciosa a visible, que es
  literalmente el core value de este milestone.
- **Files modified:** `_core.py` (docstring de `parse_segments_response` con la razón registrada en
  el sitio que la constriñe), `33-CENSUS.md`, `.planning/ROADMAP.md`
- **Verification:** `SHAPE-MD-REF-33` resuelve a una entrada de ROADMAP agregada en `68caaae`;
  cero celdas `TBD`/`later`/`a futuro` en la sección
- **Committed in:** `adaaa38` + `68caaae`

---

**2. [Rule 3 - Blocking] El RED de SC-1 no podía fallar por la razón correcta si importaba el nombre que el fix todavía no había creado**

- **Found during:** Task 2, primera corrida del RED de SC-1
- **Issue:** El plan exige que el RED *"falle por la razón correcta — una aserción sobre el valor o
  el error levantado, no un `ImportError`"*. Pero el fix de SC-1 **crea** `CalendarConfigPreview` y
  `PreviewMarket`, así que la forma natural del test (`from market_data_client import
  CalendarConfigPreview`) revienta en **colección**, antes de ejecutar una sola aserción:
  `ImportError: cannot import name 'CalendarConfigPreview'`. Ese rojo no dice nada sobre el
  defecto — dice que un símbolo no existe.
- **Fix:** Se reordenó el test para que la **primera** aserción de cada caso sea de valor
  (`result.to_dict() == _PREVIEW_ENVELOPE`) y los nombres nuevos se resuelvan **en tiempo de
  llamada** vía `models.CalendarConfigPreview`, después de esa línea. El RED entonces falla
  mostrando el `CalendarConfig` de ceros tipados que el parser fabricaba, que es la evidencia del
  defecto; y el test committeado conserva igual las aserciones fuertes de tipo. Queda registrado
  como patrón: *el RED de un fix que introduce nombres nuevos se escribe para fallar por valor*.
- **Files modified:** `packages/market-data-client/tests/test_preview_calendar_config_envelope.py`
- **Verification:** `978d2ff` → 3 rojos, los tres con `AssertionError` sobre el dict
- **Committed in:** `978d2ff`

---

**3. [Rule 1 - Bug] El ensanche de `market_data` a `Optional` era inefectivo: el pase de mapping lo deshacía una línea después**

- **Found during:** Task 2, GREEN de SC-2
- **Issue:** `walk_field` honra `T | None` correctamente — *"a missing value stays `None` instead of
  collapsing to a typed zero, and is NOT a divergence"*. Pero `_apply_mapping_policy` corre
  **después** del walker, y su predicado `_is_mapping` **desenvuelve `Optional`** antes de mirar el
  origen — tiene que hacerlo, o un campo `dict[...] | None` se saltearía el pase entero y volvería
  a quedarse con lo que trajera el payload (el agujero que CR-03 cerró). Consecuencia: apenas
  `market_data` se ensanchó, el pase seguía llamando a `_mapping_value(None, …)`, que emitía
  `missing` y devolvía `{}` — **substituyendo el cero tipado y reportando la divergencia que el
  ensanche acababa de declarar legítima**. El ensanche habría quedado cosmético en la anotación y
  falso en runtime.
- **Fix:** Un guard en `_apply_mapping_policy`: bajo un hint `Optional`, un `None` se deja pasar
  intacto. Restaura en el call site el contrato que el walker ya aplica. **El guard NO se puso en
  `_mapping_value`**, que es un port verbatim del de matriz y cuya identidad es deliberada; vive en
  el pase específico de market-data. Un campo mapping **requerido** no lo toca (CR-03 sigue
  vigente, re-anclado sobre el fixture `_RequiredMapping`), y un valor de **tipo equivocado** sigue
  ruteando por `_mapping_value` bajo cualquiera de las dos anotaciones.
- **Files modified:** `packages/market-data-client/src/market_data_client/models.py`,
  `packages/market-data-client/tests/test_decode.py`
- **Verification:** `test_optional_mapping_field_keeps_none_and_reports_nothing` y
  `test_strict_mode_does_not_raise_on_a_null_optional_mapping_field` son las dos filas que se
  ponen rojas si el guard desaparece; `test_absent_required_mapping_field_…` y
  `test_strict_mode_raises_on_an_absent_required_mapping_field` son las que se ponen rojas si el
  guard se pasa de ancho
- **Committed in:** `9992653`

---

**4. [Rule 1 - Bug] La afirmación del plan sobre el short-circuit de `append_finding` es al revés, y aplicarla literal habría dejado el triage sin verificar**

- **Found during:** Task 2, antes de promover
- **Issue:** El `<action>` dice que hay que promover vía `append_finding` porque *"any non-`OPEN`
  status short-circuits into an in-place ART-block refresh"*. El short-circuit **existe**, pero
  mira el status **del finding existente**, no el que se pasa: `if fid in existing and
  existing[fid].status != "OPEN"`. Los 76 estaban `OPEN`, así que **cada promoción re-serializa el
  archivo entero** — exactamente el round-trip con pérdida que la nota quería evitar. Confiar en la
  frase habría significado hacer 76 re-serializaciones creyendo que ninguna reescribía nada.
- **Fix:** Se **midió** la fidelidad del round-trip antes de tocar nada: `_parse_findings` →
  `_serialize_findings` sobre el archivo real dio **0 líneas de diff**, así que en ESTE archivo la
  re-serialización es demostrablemente inocua (no hay prosa de operador por-finding que perder).
  Con eso probado se promovió vía la API sancionada, sin editar el markdown a mano. La medición
  queda escrita en `33-CENSUS.md` para que no haya que re-derivarla, y la advertencia queda: el día
  que un findings file tenga bullets `**Notes:**` por finding, este chequeo previo deja de dar cero
  y hay que cambiar de estrategia.
- **Files modified:** ninguno (el defecto estaba en la afirmación del plan)
- **Verification:** diff del round-trip = 0 líneas; los 143 bloques previos siguen presentes tras
  las 76 promociones (143 antes, 143 después)
- **Committed in:** `68caaae` (registrado en el mensaje de commit)

---

**Total deviations:** 4 auto-fixed (2× Rule 1, 1× Rule 2, 1× Rule 3)

**Impact on plan:** Ninguno sobre el alcance. La **#1** es el resultado más consecuente del plan y
la única que agrega trabajo al backlog: es un hallazgo que el fix mismo destapó, y se registra en
vez de arreglarse porque el gate de contrato existe para eso. La **#3** es la que decide si SC-2
funcionó de verdad o sólo en la anotación. La **#4** evita hacer 76 escrituras sobre una premisa
falsa. **Cero scope creep:** no se tocó ningún archivo de `matriz-client`, `iol-client`,
`higyrus-client`, `wallets-client` ni `ambito-financiero-client`; ninguna copia de `_decode.py`;
ningún driver `main_*.py`; ningún alias `Literal`; `uv.lock` intacto; y no se reparó ninguna de las
19 fallas ni ninguno de los 43 errores de mypy pre-existentes de `verification/` (P-13).

---

## Authentication Gates

Ninguno. Este plan no hizo una sola request de red: los 22 tests de regresión son mockeados con
`pytest-httpx` sobre el token pre-sembrado del `conftest`, y los gates de cierre de ciclo son
estructurales (regex sobre markdown + `ast.parse` sobre un archivo). La prohibición P-05 se
satisface por construcción, no por disciplina.

Los dos gates de autenticación que la fase arrastra —`higyrus-client` (DNS) y `matriz-client`
(política remarkets-only)— siguen abiertos y siguen ruteados; ver `## Criterio 1`.

---

## Issues Encountered

- **El criterio 1 no está cerrado y este plan no lo cierra.** 3 de 5 paquetes medidos en vivo. Es
  el gate humano que 33-05 pidió surfacear, y está surfaceado en tres lugares: el censo, este
  SUMMARY y una aserción ejecutable dentro de `test_cycle_closure_phase33.py`.
- **`iol-client` conserva un finding `OPEN` (`F-01`)** y se dejó intacto a propósito: es de la
  corrida LIVE-03 de 2026-06-25, **no** lo escribió la corrida de la Phase 33, y el triage de este
  plan tiene alcance escrito sobre *"every `OPEN` SHAPE finding the live run wrote"*. Promoverlo
  habría sido inflar el conteo de no-vacuidad con un finding que este ciclo no inspeccionó.
- **`SHAPE-MD-REF-33` es deuda nueva creada por un fix**, no deuda descubierta. Vale registrarlo
  así: el trabajo del backlog subió como consecuencia directa de destapar algo, que es el precio
  normal de quitar una capa de silencio.
- **`.planning/config.json` quedó modificado en el working tree** (`_auto_chain_active`) por el paso
  de init del workflow, no por este plan. No se commiteó: mismo criterio que 33-04, 33-05 y 33-06.
- **`.gsd/` y cuatro archivos de `.planning/research/.cache/` estaban sin trackear antes de que este
  plan arrancara** (visibles en el `git status` inicial). Son output de runtime de la tooling,
  ajenos a este plan; no se commitearon ni se ignoraron acá para no mezclar un cambio de
  configuración del repo con el diff de la fase.

---

## Carry-forwards

1. **La Phase 34 tiene DOS paquetes source-breaking, no uno.** `iol-client` 0.2.0 → 0.3.0 (DT-08) y
   ahora `market-data-client` 0.4.0 → **0.5.0**. Los dos necesitan callout de changelog, y el de
   market-data tiene tres ítems: el tipo de retorno de `preview_calendar_config`, los tres campos
   `Optional` de `MarketDataSnapshot` y los dos de `Symbol`. Está escrito en el criterio 1 de la
   Phase 34.
2. **`SHAPE-MD-REF-33` decide su semver según cuándo se haga:** antes del release de la Phase 34 se
   suma al mismo bump; después, abre su propio ciclo breaking. Conviene decidirlo **antes** de
   taggear.
3. **El criterio 1 queda PARCIAL.** `LIVE-HIGY-33` y `LIVE-MATZ-33` son los destinos. Mientras
   estén abiertos, ninguna fase puede reportar el criterio 1 como cerrado sin mentir, y el gate de
   higyrus lo asevera en código.
4. **`TYP-MD-EXTRA-33` bajó de 8 triples a 5.** Las tres claves del sobre de preview dejaron de ser
   `extra` porque `CalendarConfigPreview` las declara. El ROADMAP está actualizado; quien lo tome
   no debería buscar las tres que ya no están.
5. **El gate de no-vacuidad lleva números que hay que re-medir, no editar.** Si `market-data` cae
   por debajo de 88, el mensaje del assert dice explícitamente que la lectura correcta es *"se
   demotearon, borraron o nunca se promovieron findings"*, **no** *"el piso está viejo"*.
6. **`verification/` sigue en 19 failed / 19 errors** por `HARN-VERIF-01`, sin cambios. Este plan
   sumó 11 verdes y no tocó un solo rojo.

---

## Known Stubs

Ninguno. Los cuatro fixes están cableados a fuentes reales y ejercitados end-to-end por los
shells: los tests despachan por `Client` / `AsyncClient` reales contra un transport mockeado, no
por los parsers de `_core` en aislamiento, así que el tipo de retorno declarado, los shims
module-level y el re-export de `__init__` quedan todos en el camino ejercitado.

`CalendarConfigPreview` y `PreviewMarket` no son placeholders: sus siete + cuatro campos salen
verbatim de las dos capturas committeadas del endpoint, y ninguno se declaró `Optional`
especulativamente (T-31-17).

Las celdas `SKIPPED` que este plan hereda de `33-CENSUS.md` **no son stubs pendientes de
completar** — son el resultado, con su causa medida y su destino nombrado.

---

## TDD Gate Compliance

| Gate | Commits | Evidencia |
|---|---|---|
| RED | `182b410`, `978d2ff`, `6f5ef36`, `24aa142` | 5 / 3 / 4 / 4 rojos respectivamente, **cada uno por aserción de valor o por el error levantado**, nunca por `ImportError` ni por desajuste de conteo de mocks (ver Deviations #2 para el caso que hubo que reordenar) |
| GREEN | `adaaa38`, `46f97f6`, `9992653`, `96a6b74` | 6 / 5 / 6 / 5 passed en los archivos nuevos; 609 passed en el paquete; 1755 passed en `packages` |
| RED (Task 3) | — | El gate de cierre de ciclo pasa al escribirse, como todo gate escrito contra un estado que otro commit ya dejó correcto. La no-vacuidad se demuestra por **falsificación**: cuatro experimentos, cuatro rojos distintos, cuatro reversiones (tabla arriba) |

Sin fase REFACTOR: ninguno de los cuatro fixes la necesitó. Las reformulaciones de tests existentes
no son refactor —cambian lo que se asevera, no cómo— y viajan en el commit GREEN que las hace
necesarias, que es donde son legibles.

---

## Verification Evidence

| Gate | Resultado |
|---|---|
| `uv run pytest packages -q` | **1755 passed**, 1 deselected |
| `uv run pytest packages/market-data-client -q` | **609 passed** (era 591 al empezar el plan) |
| `uv run pytest packages/market-data-client/tests/test_surface_parity.py -q` | **3 passed** tras cada fix |
| `uv run pytest verification/test_cycle_closure_phase33.py -q` | **11 passed** (≥10 requerido: 5 paquetes × 2 + el gate de la exención) |
| Subconjunto dirigido del harness (5 archivos) | **27 passed** |
| `uv run pytest verification -q --tb=no -rfE` | **19 failed / 387 passed / 19 errors** |
| Delta contra `33-BASELINE.md` (19 / 368 / 19) | **Mismo set rojo, node id por node id.** +19 verdes: 11 de este plan + 8 de 33-05. **Cero regresiones** |
| `verify_cycle_closure` × 5 | `(True, [])` en los cinco, `missing == []` |
| Conteo inspeccionado, market-data | **50 → 88** (+38) |
| Conteo inspeccionado, otros cuatro | 0→0, 0→0, 1→1, 1→1 — sin promociones, con exención argumentada o piso real |
| Falsificación A (demote de `F-82`) | `assert 87 >= 88` — revertida |
| Falsificación B (`Regression:` rota) | `not green … ['F-102']` — revertida |
| Falsificación C (`ClassDef` en ámbito) | `D-12 no longer holds` — revertida |
| Falsificación D (`LIVE-HIGY-33` renombrado) | `exactly what P-03 forbids` — revertida |
| `grep -rc 'Regression:.*verification/' .planning/verification/*-findings.md` | **0** en los cinco archivos |
| Findings `OPEN` en `market-data-client` tras el triage | **0** (eran 76) |
| Bloques `### F-` antes / después del triage | **143 / 143** — cero perdidos |
| Round-trip `_parse_findings`→`_serialize_findings` (medido pre-triage) | **0 líneas de diff** |
| `uv run python tools/check_decode_intactness.py` | exit 0 — 5 copias → un hash `ac14868282ad0a5c` |
| `uv run python tools/check_surface_types.py` | exit 0 — 180 nombres de `__all__`, 319 definiciones, **0 violaciones** |
| `uv run python tools/check_uniform_structure.py` | exit 0 — 6 paquetes con `models.py` + `types.py` |
| `git diff --stat` sobre `packages/*/src/*/_decode.py` | **vacío** |
| `git diff --stat packages/matriz-client/src/matriz_client/types.py` | **vacío** (P-04) |
| `git diff --stat uv.lock` | **vacío** |
| `uv run mypy` | Success: no issues found in 75 source files |
| `uv run mypy verification/test_cycle_closure_phase33.py` | Success |
| `uv run ruff check . && uv run ruff format --check .` | limpio, **254 archivos** formateados |
| Deleciones en los 9 commits | **0** |
| Scan de fuga: 20 valores de los 4 `.env` contra los 6 artefactos nuevos | **0 coincidencias** |
| CUIT-like (11 dígitos) / token-like (`Bearer`, `eyJ…`) en los artefactos nuevos | **0 / 0** |
| Celdas `TBD` / `later` / `a futuro` en `33-CENSUS.md` § Re-scope | **0** (la única ocurrencia del texto es la frase que enuncia la regla) |
| Destinos que resuelven en `ROADMAP.md` § Backlog | `LIVE-MATZ-33`, `LIVE-HIGY-33`, `TYP-MD-EXTRA-33`, `HARN-DRIFT-33`, **`SHAPE-MD-REF-33`** ✓ |

---

## Self-Check: PASSED

- Los **6** archivos de `key-files.created` existen en disco.
- Los **9** hashes declarados (`182b410`, `adaaa38`, `978d2ff`, `46f97f6`, `6f5ef36`, `9992653`,
  `24aa142`, `96a6b74`, `68caaae`, `264f678`) existen en `git log`.
- Los conteos de rojos del RED están copiados de la salida de pytest de esta sesión, no
  parafraseados; cada uno se puede reproducir haciendo checkout del commit RED correspondiente.
- La partición del triage suma exactamente: 38 + 6 + 32 = **76**, y la igualdad de conjuntos contra
  los `OPEN` reales del archivo se aseveró **en el script, antes de promover**, no después.
- El delta de `verification/` reconcilia por construcción: 387 − 368 = **19** = 11 (este plan) +
  8 (33-05, posteriores a la medición del baseline sobre `0a9fdae`), con el set rojo idéntico.
- Los fids citados en cada fila de fix se verificaron uno por uno contra los títulos del archivo de
  findings antes de escribir esta tabla.
- **`LIVE-TYP-01` queda deliberadamente en `Pending`, y ahora la razón es medible, no prudencial.**
  Los siete planes de la Phase 33 cargan ese ID. Cerrarlo acá exigiría afirmar el criterio 1, y el
  criterio 1 está **PARCIAL con 2 de 5 paquetes sin medir en vivo** — una completitud
  demostrablemente falsa. El requisito se cierra cuando `LIVE-HIGY-33` y `LIVE-MATZ-33` cierren, no
  cuando se acaben los planes de la fase. Mismo precedente que 33-01, 33-03, 33-04, 33-05 y 33-06.
