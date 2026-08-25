---
phase: 32-gates-de-homogeneidad-d-16
plan: 03
subsystem: testing
tags: [decision-gate, semver, public-api, httpx, sync-async-parity, market-data-client]

# Dependency graph
requires:
  - phase: 32-01
    provides: "CI-green baseline across the four jobs — the parity suite that surfaces D-09 can only be trusted against a green tree"
  - phase: 31-endpoints-de-ops-estructura-uniforme
    provides: "D-12 step-en-lint pattern for cross-package gates; the three-package roster of verification/test_async_configure_resource_warning.py that this decision explicitly does NOT touch"
provides:
  - "The recorded D-09 disposition: option-a selected (add http_client to market_data_client.aio.configure), option-b rejected"
  - "Explicit authorisation for Plan 32-04 Task 2 to edit the public configure signature of an already-published package"
  - "The semver consequence for the Phase 34 re-publish, stated before any code depends on it"
affects: [32-04, 32-06, 34-publish, phase-33-live-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One-way-door decision gate: an irreversible public-surface change gets a decision-only plan before the plan that implements it"
    - "Auto-resolution provenance disclosure: under auto_advance, the SUMMARY states whether a developer answered or the researched default was applied"

key-files:
  created:
    - .planning/phases/32-gates-de-homogeneidad-d-16/32-03-SUMMARY.md
  modified: []

key-decisions:
  - "D-09 resuelto a option-a: market_data_client.aio.configure recibe http_client: httpx.AsyncClient | None = None; option-b (allowlistear configure del chequeo de hints completo) queda rechazada"
  - "La seleccion fue AUTO-RESUELTA al default investigado, no respondida por el desarrollador — el plan 32-03 autoriza explicitamente esa resolucion y exige declararla"
  - "Consecuencia semver: market-data-client gana un parametro publico keyword-only → entrada de changelog minor-worthy en Phase 34, nunca un major"
  - "El roster de tres paquetes de verification/test_async_configure_resource_warning.py queda INTACTO por D-12, cualquiera fuera la seleccion"

patterns-established:
  - "Decision-only plan: cero archivos fuente tocados, verificado por git status --porcelain sobre packages/tools/.github/pyproject.toml"

requirements-completed: []

# Metrics
duration: 4min
completed: 2026-08-25
status: complete
---

# Phase 32 Plan 03: D-09 decision gate Summary

**D-09 resuelto a option-a por auto-resolucion al default investigado: `market_data_client.aio.configure` recibira `http_client: httpx.AsyncClient | None = None` en el plan 32-04, con consecuencia semver minor para el re-publish de la Phase 34 — cero archivos fuente tocados por este plan.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-25T21:18:42Z
- **Completed:** 2026-08-25T21:22:30Z
- **Tasks:** 1 (checkpoint:decision)
- **Files modified:** 0 source files (1 planning artefact created)

## D-09 disposition

### Seleccion: `option-a` — cerrar la deriva agregando el parametro

`market_data_client.aio.configure` recibe un parametro keyword-only nuevo,
`http_client: httpx.AsyncClient | None = None`, espejando el
`http_client: httpx.Client | None = None` que `market_data_client.client.configure` ya expone en
la octava posicion keyword. La implementacion la ejecuta el **Plan 32-04 Task 2**; este plan solo
la autoriza.

### Opcion rechazada: `option-b` — allowlistear `configure` del chequeo de hints completo

`option-b` proponia eximir `configure` de la comparacion `get_type_hints()` y contrastar unicamente
el conjunto de nombres de parametros, lo que seguiria cazando el `http_client` ausente sin exigir
tipos identicos. **Queda rechazada.** Como el plan 32-04 ya no implementa ninguna excepcion de
normalizacion para `configure`, no hay "forma exacta del allowlist" que registrar aqui; la clausula
condicional del `<action>` del plan (registrar esa forma *si* se elegia option-b) no aplica, y el
Plan 32-04 Task 2 **no** se dropea.

### Provenance de la seleccion: AUTO-RESUELTA, no respondida por el desarrollador

Esta seleccion fue **auto-resuelta a la recomendacion investigada**; **ningun desarrollador la
respondio explicitamente**. La fase corre bajo `workflow.auto_advance: true` y `mode: yolo`
(`.planning/config.json`), y el propio `<action>` del plan 32-03 anticipa y autoriza este camino:
*"if this checkpoint is auto-resolved rather than answered by the developer, option-a is the
default, and the SUMMARY must say the selection was auto-resolved to the researched recommendation
rather than answered explicitly."* Queda dicho aqui para que el registro no sea repudiable
(T-32-10).

Vale notar que option-a no es un default arbitrario: es la misma opcion que
`32-CONTEXT.md` § "Claude's Discretion" ya marcaba como recomendada *pendiente de confirmacion en
planning* ("Recomendado: (1)... pero confirmar en planning dado el impacto de superficie publica"),
y la que `32-RESEARCH.md` § Pattern 4 califica de HIGH confidence. La auto-resolucion convierte esa
recomendacion en disposicion; no la origina.

### Rationale

Dejar la deriva abierta significa elegir conservar exactamente la clase de divergencia silenciosa
que este milestone existe para eliminar: el docstring de `aio.py` afirma hoy que su semantica
"ESPEJA exactamente la superficie sync `client.configure`" mientras le falta un parametro que esa
superficie sync si tiene — es deriva **documentada como inexistente**, y de los seis paquetes
market-data es el unico con la asimetria. El constraint "Dual sync/async" de `CLAUDE.md`
("cualquier fix de logica debe espejarse en `client.py` y `aio.py` del mismo paquete") vuelve el
cierre obligatorio antes que discrecional. El costo es minimo y esta enteramente precedentado:
`AsyncClient.__init__` ya acepta y asigna `http_client: httpx.AsyncClient | None`,
`_ClientState.http_client` ya esta tipado `httpx.Client | httpx.AsyncClient | None`, y
`aio.aclose()` ya hace el `isinstance`-assert y el await — la superficie de cambio se reduce a la
firma, un bloque carry-forward, un `import warnings` a nivel modulo (verificado ausente hoy en
`aio.py` de market-data) y la linea de docstring que sobre-afirma. La unica objecion seria —que un
`def configure` sin `async` no puede `await` el `aclose()` del cliente viejo antes de reemplazarlo—
es la misma que matriz e iol ya contestaron emitiendo un `ResourceWarning` y reemplazando igual
(`matriz_client/aio.py:805-814`); higyrus y ambito la contestan con un rebuild path. Cuatro de los
cinco otros paquetes ya threadean `http_client` en su `configure` async. Ademas, cerrar la deriva
permite que el test de paridad compare `get_type_hints()` completo, que es lo que el criterio 3
pide literalmente, en vez de estrenar la primera excepcion de normalizacion de la fase para
acomodar un defecto — precisamente el anti-patron contra el que advierte el framing de tabla de
reglas de `check_decode_intactness.py` ("never weaken the check into a vacuous one").

Costo aceptado, escrito para que no se lea como gratis: el parametro entra en la superficie publica
de un paquete ya publicado y no puede retirarse despues sin romper compatibilidad, y se agrega un
camino de emision de `ResourceWarning` que un consumidor corriendo bajo `-W error` podria pisar.

### Consecuencia semver para la Phase 34

**`market-data-client` gana un parametro publico keyword-only con default, lo que es puramente
aditivo y no source-breaking: corresponde una entrada de changelog minor-worthy en el re-publish de
la Phase 34, nunca un major.**

El paquete esta publicado hoy en **v0.4.0** (`packages/market-data-client/pyproject.toml:3`). La
irreversibilidad no esta en publicarlo sino en retirarlo: una vez shipeado, quitar el parametro si
seria un cambio breaking. Riesgo residual declarado (assumption A3 de `32-RESEARCH.md`): no se
relevo si algun consumidor envuelve o subclasea `configure` posicionalmente, y no se sabe si algo
fuera de este repo consume `market-data-client` v0.4.0 — STATE.md registra el desconocido
equivalente para `iol-client` como item abierto de la Phase 30. El argumento de irreversibilidad de
option-a asume que esa respuesta no cambia el calculo para un keyword-only aditivo.

### Scope boundary: el roster de tres paquetes queda intacto

`verification/test_async_configure_resource_warning.py:27` declara
`_ASYNC_PACKAGES = ["ambito_financiero_client", "iol_client", "higyrus_client"]` — tres paquetes,
market-data excluido. **Ese roster no se toca, cualquiera hubiera sido la seleccion de D-09.**
Enrolar market-data ahi es uno de los ~6 rosters fuera de scope que **D-12** difiere explicitamente
como deuda documentada; no es parte de esta decision y no se pliega dentro de ella (T-32-11). Que
el plan 32-04 haga emitir un `ResourceWarning` a `market_data_client.aio.configure` **no** habilita
inscribirlo en ese roster dentro de la Phase 32.

## Accomplishments

- La unica decision one-way de la Phase 32 quedo tomada y registrada antes de que ningun codigo
  dependa de ella
- La opcion rechazada y la consecuencia semver quedaron por escrito, no inferidas del silencio
- La provenance (auto-resolucion vs respuesta del desarrollador) quedo declarada, cerrando T-32-10
- El limite de scope contra el roster de D-12 quedo restated, cerrando T-32-11
- Cero archivos fuente modificados, cerrando T-32-12

## Task Commits

1. **Task 1: Decide the D-09 disposition** — `docs` commit del SUMMARY (ver metadata abajo)

_Este plan es decision-only: no produce commits de codigo._

## Files Created/Modified

- `.planning/phases/32-gates-de-homogeneidad-d-16/32-03-SUMMARY.md` — la disposicion D-09 registrada

Ningun archivo fuente fue modificado. Verificado:
`git status --porcelain -- packages tools .github pyproject.toml` sin output.

## Decisions Made

- **option-a seleccionada, option-b rechazada** (ver § D-09 disposition arriba)
- **La seleccion fue auto-resuelta** al default investigado bajo `auto_advance`/`yolo`, con
  autorizacion explicita en el `<action>` del plan — no la respondio el desarrollador
- **La clausula condicional de option-b no aplica**: no se registra forma de allowlist porque no se
  eligio option-b; el Plan 32-04 Task 2 sigue vivo
- **Nada del roster de D-12 se pliega en esta decision** aunque option-a introduzca un
  `ResourceWarning` en market-data

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Todos los hechos que el plan cita fueron re-verificados contra el working tree antes de
registrar la disposicion: la firma sync con `http_client` en posicion keyword 8
(`client.py:762-775`), su ausencia en la firma async (`aio.py:776-788`), el docstring que afirma
"ESPEJA exactamente", la ausencia de `import warnings` a nivel modulo en el `aio.py` de market-data,
la version publicada 0.4.0, y el roster de tres entradas de
`verification/test_async_configure_resource_warning.py:27`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Plan 32-04 Task 2 esta autorizado a proceder.** Debe agregar
  `http_client: httpx.AsyncClient | None = None` a `market_data_client.aio.configure`, threadearlo
  al `_state` con el shape `ResourceWarning` de `matriz_client/aio.py:805-814`, agregar
  `import warnings` a nivel modulo (hoy ausente), y corregir la linea de docstring que sobre-afirma
  paridad. **Prohibicion vigente del plan 32-03:** un parametro publico aceptado y descartado esta
  fuera de la mesa — la decision autoriza el parametro, no un no-op.
- **Plan 32-04 Task 1** ya no necesita ninguna excepcion de normalizacion para `configure` mas alla
  de la regla sancionada `httpx.Client ↔ httpx.AsyncClient`, que cubre las cinco divergencias
  legitimas. Con D-09 cerrada, esa regla deja la suite de paridad verde en los seis paquetes.
- **Phase 34** debe cargar en el changelog de `market-data-client` la adicion del parametro publico
  keyword-only como entrada minor-worthy.
- **Deuda diferida sin cambios:** el roster de tres paquetes de
  `verification/test_async_configure_resource_warning.py` sigue excluyendo market-data por D-12.

---
*Phase: 32-gates-de-homogeneidad-d-16*
*Completed: 2026-08-25*
