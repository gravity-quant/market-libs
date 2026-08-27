# Phase 33: Verificación en vivo en modo estricto + fixes - Context

**Gathered:** 2026-08-26 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

La nueva decodificación observable (Phase 29) queda verificada contra las APIs reales — el
momento donde aparecen las divergencias que la tolerancia silenciosa venía ocultando, y todas
se documentan y corrigen en el mismo ciclo. Alcance fijo (ROADMAP § Phase 33, 5 criterios):

1. Los 4 drivers verificables (`main_ambito_financiero.py`, `main_iol.py`, `main_higyrus.py`,
   `main_matriz.py`) + `main_market_data.py` corren en modo estricto contra sus APIs reales;
   cada divergencia entra al pipeline de findings existente vía un handler de logging
   (`verification/divergences.py`), con endpoint + FQN del modelo + superficie (sync|async).
2. Cada divergencia confirmada se corrige in-cycle, espejada sync/async, con test de regresión
   mockeado por fix.
3. Los `Literal` se cierran con evidencia real: iol `mercado`/`plazo` (DT-07) se promueven o se
   documentan como `str` permanente; los RESPONSE pre-existentes de matriz (`CFICode`/`MarketId`/
   `OrderType`/`Currency`) se resuelven según el D-lock de la Phase 29 con censo vivo.
4. `verify_cycle_closure` PASS por paquete y schema snapshots reconciliados contra el baseline.
5. El volumen real se contrasta contra el piso de sizing de la Phase 29 (`≥ 96` total,
   `higyrus ≥22` / `matriz ≥24` / `market-data ≥50` / iol y ambito N/A); si lo excede, re-scope
   explícito con findings diferidos a fase destino nombrada.

Fuera de este límite: releases/bumps de versión (Phase 34), nuevos endpoints o modelos que no
estén ya cubiertos por Phases 30/31 (TYP-02/TYP-03 ya cerradas), ampliar/cerrar los Literals de
RESPONSE de matriz (D-09 lo prohíbe explícitamente este milestone), `wallets-client` (fuera de
alcance del proyecto completo).
</domain>

<decisions>
## Implementation Decisions

### Divergence handler architecture (`verification/divergences.py`)

- **D-01:** El handler es una subclase de `logging.Handler` colgada del logger de cada uno de
  los 5 paquetes tipados (`ambito_financiero_client`, `higyrus_client`, `iol_client`,
  `matriz_client`, `market_data_client`), que mapea el `extra` de 6 claves (`package`,
  `divergence`, `field_path`, `declared_type`, `observed_type`, `model`) a
  `append_finding(pkg, class_="SHAPE", status="OPEN", idempotent_by_title=True, expected=…,
  actual=…, diff=…, …)` — diseño ya firmado en `29-AGGREGATION-CONTRACT.md` Lock 10, no se
  re-discute. `SHAPE` ya existe en `FINDING_CLASSES` (`verification/findings.py`), no se crea
  clase nueva.
- **D-02:** `endpoint` y `surface` (sync|async) llegan al handler vía un mecanismo owned by
  `verification/divergences.py` (contextvar o equivalente) que el driver setea antes de cada
  llamada al probe, reusando la convención existente `_ENDPOINT_TEMPLATES` /
  `probe_<func>_<sync|async>` — NUNCA agregando claves al registro de 6 claves de `_decode.py`
  (frozen por el gate de intactness 6-way entre paquetes). Recomendado: un decorator
  `@probe(endpoint, surface)` que en un solo edit por función de probe (a) bindea el contexto y
  (b) captura `<Pkg>DecodeError` para que el modo estricto no mate el driver — resuelve D-02 y
  D-05 en el mismo lugar.
- **D-03:** `main_market_data.py` necesita un `_ENDPOINT_TEMPLATES` nuevo (hoy solo tiene
  `_ENDPOINT_OPTIONAL`, no relacionado); los otros 4 drivers reusan el suyo existente.

### Modo estricto: modelo de ejecución y supervivencia del driver

- **D-04:** El modo estricto solo no alcanza para el censo completo — levanta en la PRIMERA
  divergencia por respuesta (ej. S-2 predice 9 campos fabricados en `CalendarConfig`, estricto
  reporta 1). La corrida de cada driver es de **dos pasadas**: pasada observable
  (`strict_decode=False`, handler activo) primero para el censo completo, pasada estricta
  después para probar que el raise efectivamente dispara. Esto es lo que hace comparable el
  censo vivo contra el piso `≥ 96` de la Phase 29 (D-06 de 29-CONTEXT).
- **D-05:** `<Pkg>DecodeError` es HERMANO de `<Pkg>APIError` (no subclase) en los 5 paquetes —
  ningún manejo de excepciones existente en ningún driver lo captura hoy. Activar
  `strict_decode=True` sin más cambios mata el driver con traceback y cero findings. Fix:
  agregar `<Pkg>DecodeError` al tuple de excepciones capturadas por cada probe (via el
  decorator de D-02, o equivalente).
- **D-06:** NO se agrega un `except Exception` de nivel superior a `main_matriz.py` ni a
  `main_higyrus.py` — `verification/test_main_drivers_bare_except.py` lo prohíbe explícitamente
  vía AST gate para esos dos drivers y es una regresión de CI si se intenta. El catch debe ser
  por-probe (o por el decorator compartido), nunca un guard global bare-except.
- **D-07:** El catch manual existente de `HigyrusDecodeError` en `probe_get_health_sync`/`_async`
  (Phase 31) se elimina y se reemplaza por el mecanismo compartido — mantenerlo generaría un
  finding duplicado del que ya produce el handler automático (rompe el `idempotent_by_title`
  de Lock 10). No se replica ese patrón hand-rolled en los ~130 probes restantes.

### Cierre de Literals con evidencia real (criterio 3)

- **D-08:** El walker NO emite ningún registro para un valor `Literal` fuera de set con tipo de
  runtime correcto (`policy.literal_enforced=False` en las 5 copias corta antes del sink). El
  stream de divergencias del handler de D-01 por sí solo NO produce el censo de Literals que
  pide el criterio 3 — se necesita un mecanismo separado: recolectar los valores crudos del wire
  que los drivers ya capturan (schema snapshots / raw payloads), no derivarlo de los findings
  SHAPE.
- **D-09:** Los 7 campos RESPONSE de matriz ya tipados con los 4 Literal aliases pre-existentes
  (`marketId`/`cficode`/`currency`/`orderTypes`/`ordType` en `models.py`) se resuelven
  **confirmando que decodean sin enforcement y registrando los valores observados** — NUNCA
  ampliando ni cerrando los aliases (D-09/`29-DLOCK-RESPONSE-LITERAL.md` lo prohíbe
  explícitamente este milestone; una ampliación sería su propia decisión con su propio artefacto
  firmado, fuera de este ciclo).
- **D-10:** `mercado`/`plazo` de iol (DT-07) quedan **`str` permanente, documentado como decisión
  explícita** — los drivers solo envían los defaults actuales (`"bcba"`/`"t2"`), sin evidencia
  del conjunto aceptado por el vendor. Un `Literal` incompleto rompe llamadas legítimas (peor que
  `str`). NO se agrega un sweep de prueba de valores candidatos contra la cuenta real de
  brokerage en este ciclo — la ausencia de evidencia ES la evidencia que cierra `str`.

### Vacuidad del gate, alcance del censo y disponibilidad de credenciales (criterios 4-5)

- **D-11:** `verify_cycle_closure` solo inspecciona findings con status `CONFIRMED`/`FIXED`
  (`verification/cycle_report.py`) — un finding recién escrito por el handler en `OPEN` no
  cuenta. El criterio 4 solo es significativo DESPUÉS de que la triage (humana u operator-driven,
  igual que en fases previas) promueva las divergencias confirmadas a `CONFIRMED`/`FIXED` con
  link de regresión. No reportar "criterio 4 PASS" de una corrida donde el gate nunca inspeccionó
  un finding real.
- **D-12:** `ambito-financiero-client` es un no-op estructural bajo modo estricto (cero clases de
  modelo, cero llamadas al walker) — contribuye cero divergencias por construcción. Se incluye en
  el criterio 1 solo como smoke-test (correr en modo estricto y confirmar cero findings), sin
  presupuesto de triage/fix.
- **D-13:** Las corridas credencializadas están disponibles in-repo para iol/higyrus/matriz/
  market-data (`.env` presente en los 4 paquetes; ausente solo en ambito, consistente con su
  diseño sin auth) — market-data YA NO depende del workaround operator-paste de la Phase 23. La
  validez real de las credenciales es no verificable desde este entorno (contenido de `.env` no
  legible por permisos). El plan de Phase 33 debe incluir un pre-flight check por driver que
  confirme autenticación real (no-SKIP) antes de que cualquier número de censo cuente como
  válido; si un driver SKIPea por falta/expiración de creds, cae al fallback operator-runs-and-
  pastes documentado en Phase 23 para ese paquete específicamente.
- **D-14:** El riesgo de corrupción de schema snapshots por sitios estructurales de iol
  (30-CONTEXT D-07) YA ESTÁ CERRADO — `to_dict()` está confinado al parity probe
  (`main_iol.py:1215-1216`); los 4 sitios de snapshot consumen wire crudo vía
  `_capture_raw_wire`, sin cambios necesarios. No es un blocker de criterio 4.

### Claude's Discretion

- Forma exacta del decorator/mecanismo de D-02 (nombre, firma, si vive en
  `verification/divergences.py` o en un módulo nuevo) — research/planning decide la
  implementación concreta, la restricción es solo "no toca el registro de 6 claves de
  `_decode.py`".
- Formato exacto del censo de Literals de D-08/D-09/D-10 (script ad-hoc vs. extensión de un
  probe existente) — igual que el spike de sizing de la Phase 29, puede ser artefacto no
  committeado si el reporte final sí queda documentado.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` § Phase 33 (los 5 success criteria, verbatim origin de esta fase)
- `.planning/future-plans/tipado_homogeneo.md` § "Phase 33 — Verificación en vivo + fixes" y
  tabla DT-01..DT-09 (DT-07 en particular)
- `.planning/phases/29-decoder-observable/29-SIZING.md` — piso ratificado `≥96` total, findings
  estructurales S-1..S-5, mapping table de los 43 archivos, breakdown por kind
- `.planning/phases/29-decoder-observable/29-AGGREGATION-CONTRACT.md` — Lock 10 (spec firmada
  del handler `verification/divergences.py`), vocabulario del registro, dedupe triple
- `.planning/phases/29-decoder-observable/29-DLOCK-RESPONSE-LITERAL.md` — D-09, por qué los
  Literal de RESPONSE nunca se cierran este milestone
- `.planning/phases/29-decoder-observable/29-SEMANTICS-MATRIX.md` — políticas por paquete
  (`missing_*`, `scalar_passthrough`, `literal_enforced`)
- `.planning/phases/30-iol-client-tipado/30-CONTEXT.md` — D-02 (`puntas` sin observar), D-07/D-08
  (schema snapshots + `to_dict()`)
- `verification/findings.py` — `append_finding`, `FINDING_CLASSES`, `STATUS_LIFECYCLE`
- `verification/cycle_report.py` — `verify_cycle_closure` (vacuidad sobre status OPEN)
- `verification/test_main_drivers_bare_except.py` — AST gate contra `except Exception` en
  `main_matriz.py`/`main_higyrus.py`
- `main_higyrus.py:600-800` — precedente hand-rolled de `HigyrusDecodeError` (a eliminar per D-07)
- `packages/matriz-client/src/matriz_client/models.py` — 7 campos RESPONSE con los 4 Literal
  aliases pre-existentes (D-09)
- `packages/iol-client/src/iol_client/types.py` — placeholder vacío para `mercado`/`plazo`
  (DT-07)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `_decode.py` (copiado verbatim en los 5 paquetes tipados): `STRICT_DECODE: ContextVar[bool]`,
  `open_request_scope()`, `DecodeScope.__call__` (emite ANTES de raisear en modo estricto —
  garantiza que el handler de D-01 vea el registro incluso cuando el probe después captura la
  excepción).
- `<pkg>.Client(strict_decode=...)` / `AsyncClient(strict_decode=...)` / `configure(strict_decode=...)`
  ya existen y funcionan en los 5 paquetes — activar modo estricto es solo pasar el kwarg, sin
  cambios de librería.
- `verification/findings.py::append_finding` — pipeline existente, `idempotent_by_title=True` ya
  soporta exactamente el patrón de dedupe que necesita el handler automático.
- `_ENDPOINT_TEMPLATES` en `main_higyrus.py`/`main_iol.py`/`main_matriz.py` — convención
  reusable para D-02/D-03.

### Established Patterns

- `_RESIDUAL_PROBE_EXCEPTIONS` por driver: tuple de excepciones builtin capturadas
  genéricamente en cada probe boundary — patrón a extender (no reemplazar) con
  `<Pkg>DecodeError`.
- `ProbeResult` + clasificación PASS/FAIL/FINDING/SKIPPED por probe — el nuevo mecanismo de
  D-02 debe seguir produciendo un `ProbeResult` coherente cuando un probe recibe
  `<Pkg>DecodeError`.

### Integration Points

- El handler de D-01 se conecta a los loggers `ambito_financiero_client`, `higyrus_client`,
  `iol_client`, `matriz_client`, `market_data_client` — mismos nombres que `_LOGGER_NAME` en
  cada `_decode.py`.
- `main_market_data.py` ya tiene el patrón `require_env` (D-01 de Phase 23) para SKIP sin creds
  — el pre-flight check de D-13 se apoya en ese mismo patrón, extendido a los otros 4 drivers si
  no lo tienen ya.
</code_context>

<specifics>
## Specific Ideas

No se pidieron referencias visuales o de producto específicas — esta fase es enteramente
verificación-interna contra APIs en vivo, sin superficie de usuario.
</specifics>

<deferred>
## Deferred Ideas

- Ampliar o cerrar (enforcement) los Literal aliases pre-existentes de matriz
  (`CFICode`/`MarketId`/`OrderType`/`Currency`) — explícitamente fuera de este milestone
  (D-09), requeriría su propio artefacto firmado en una fase futura si se decide alguna vez.
- Sweep de prueba de valores candidatos de `mercado`/`plazo` contra la cuenta real de iol para
  intentar cerrar el `Literal` con más confianza — descartado en D-10 por generar tráfico 4xx
  deliberado contra un brokerage en vivo; si se hiciera, sería un plan aparte, no parte de este
  ciclo.

### Reviewed Todos (not folded)

Ninguno — `gsd_run query todo.match-phase 33` no encontró todos pendientes relevantes al scope
de esta fase.

</deferred>
