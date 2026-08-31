# Phase 42: Re-chequeos en vivo — DNS de higyrus + port del gate de venue + censo `Literal` de matriz - Context

**Gathered:** 2026-08-31 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Los dos bloqueos en vivo que v1.7 dejó abiertos dejan de ser incógnitas — higyrus produce un
veredicto medido en vez de un silencio, y matriz produce el censo de valores `Literal` de RESPONSE
que el plan 33-06 dejó abierto — con el gate de venue del script de censo endurecido a igualdad
exacta de hostname **antes** de la primera llamada de red. Requisitos: LIVE-01, LIVE-02.

Depende de la Phase 41 (auditoría de historia congelada) ya completa. Los 5 criterios de éxito de
`ROADMAP.md § Phase 42` están LOCKED — no se re-discuten acá; este documento captura CÓMO
implementarlos.
</domain>

<decisions>
## Implementation Decisions

### Venue gate port (criterio 1)

- **D-01:** `scripts/literal_census_33.py` importa `main_matriz._VENUE_ALLOWLIST` y
  `main_matriz._venue_token` directamente (reemplazando el `if "remarkets" not in base:` stale de
  la línea 192) — NO se duplica el dict con un test de igualdad separado. El test de "single
  source" es de identidad de objeto (`is`), no de contenido (`==`): con import, la divergencia
  entre sitios es estructuralmente imposible en vez de sólo detectada por un pin test. `main_matriz`
  es importable sin costo: cero side-effects fuera de `if __name__ == "__main__":` (línea 3162), ya
  lo importan 8 archivos de `verification/` a nivel de test, y `pythonpath = ["."]`
  (`pyproject.toml:109`) hace innecesario cualquier `sys.path` hack.
- **D-02:** El checkpoint humano bloqueante del criterio 1 se enmarca como **confirmación de
  fidelidad del port** — "¿el port reusa fielmente la lógica ya aprobada en D-02 de la Phase 39?" —
  no como una re-autorización de bbsa desde cero. `bbsa.matrizoms.com.ar` ya es un host autorizado
  a nivel de sistema (Phase 39 D-02, `39-CONTEXT.md`); lo que es nuevo es que
  `literal_census_33.py` específicamente nunca hizo una llamada de red hasta ahora. Precedente de
  forma: `.planning/milestones/v1.7-phases/39-verificaci-n-en-vivo-del-encadenamiento-profundo/39-01-PLAN.md:87-141`
  — `<task type="checkpoint:human-verify" gate="blocking-human">`, cero archivos tocados, el
  operador transcribe "approved" verbatim en el SUMMARY, gatea la siguiente task.
- **D-03 (falsification test):** El test de spoofing es un archivo nuevo que espeja
  `verification/test_main_matriz_skip_line_shape.py:24-40`, que ya ejercita `main_matriz._venue_token`
  contra un sufijo hostil (`<host>.attacker.example`) y la variante userinfo
  (`https://<host>@attacker.example`) — se reusa el mismo patrón de casos contra
  `literal_census_33.py`'s uso importado.

### Alcance de iol en la corrida (criterio 2, indirectamente)

- **D-04:** La corrida en vivo de la Phase 42 llama a `census_matriz()` directamente (no `main()`
  sin modificar, que también dispara `census_iol()`). Credenciales de IOL están presentes en
  `packages/iol-client/.env`, así que `main()` sin cambios SÍ ejecutaría `census_iol()` de verdad —
  pero DT-07 (el requisito que `census_iol()` sirve) ya está **CERRADO**
  (`.planning/STATE.md:405`, censo vivo de 33-06 sobre 2191 filas) y LIVE-02 nombra únicamente los 5
  campos de matriz. Ejecutar `census_iol()` de nuevo es tráfico en vivo contra IOL sin ningún
  criterio de éxito de esta fase que lo consuma.
- **Forma del cambio (discreción del planner):** llamar a `census_matriz()` desde afuera del script
  (sin tocar `main()`/`literal_census_33.py` más allá del port D-01), o agregar un flag
  `--matriz-only` a `main(argv)` espejando el patrón existente de `--selftest` (línea 355) — ambas
  formas satisfacen D-04 igual de bien; el planner elige.

### Re-chequeo de higyrus (criterio 2)

- **D-05:** El re-chequeo corre el driver completo `main_higyrus.py` (no `scripts/preflight_33.py`).
  Sólo el driver completo sobrescribe `.planning/verification/run-evidence/higyrus-client.json` con
  un `captured_at` fresco vía `write_run_evidence()` — es la única prueba durable y timestampeada de
  "re-confirmado en esta sesión". `preflight_33.py` imprime pero no persiste nada en disco.
- **D-06:** Si higyrus sigue `SKIPPED` tras esta corrida, el destino `LIVE-HIGY-33` se renombra a
  `LIVE-HIGY-42` — el criterio 2 lo exige literalmente ("destino renombrado") y la convención de
  nombres embebe la fase de origen (`LIVE-MATZ-33` sigue el mismo patrón). Sitios a tocar:
  `main_higyrus.py` (`_VENDOR_UNREACHABLE_SKIP_LINE`, `_VENDOR_UNREACHABLE_EVIDENCE`),
  `main_matriz.py` (`_CYCLE_CLOSURE_DESTINATION["higyrus-client"]`), y ~8 archivos de test que
  pinnean el string literal `"LIVE-HIGY-33"` (`verification/test_cycle_closure_phase33.py`,
  `verification/test_main_higyrus_skip_line_shape.py`,
  `verification/test_main_verify_classification.py`, `verification/test_run_evidence.py`,
  `verification/test_main_higyrus_deep_chain.py`). Si el DNS resuelve limpio esta vez, el rename es
  moot — la rama SKIPPED nunca dispara.
- **Nota de redacción (no bloquea, informa al planner):** `_vendor_unreachable_reason` (contiene
  `f"...{type(exc).__name__}: {exc}"`, potencialmente con el hostname sin resolver) se setea pero
  nunca se imprime ni persiste — es una decisión de redacción ya lockeada (D-HIGY-15). "Excepción y
  diagnóstico citados" (criterio 2) tiene que salir de la prosa del propio reporte de la sesión, no
  del stdout/evidence committeado del driver, igual que el diagnóstico original `socket.gaierror`
  de `LIVE-HIGY-33` en el backlog fue prosa del operador, no output del driver.

### Lectura fresca del wire de market-data-client (criterio 5)

- **D-07:** El mecanismo es `verification.capture.capture(...)` en los dos puntos donde
  `main_market_data.py` ya tiene el JSON crudo en mano (probes de instruments ~línea 975-980,
  segments ~línea 1004) — el mismo patrón que `literal_census_33.py` ya usa para matriz/iol. **NO**
  se reusa `_write_schema_snapshot` para este propósito: es write-once / no-overwrite-on-drift por
  diseño (D-25) y por lo tanto no puede producir un artefacto fechado en esta sesión — los baselines
  committeados (`get-instruments.json`, `get-segments.json`) están fechados 2026-07-31 (confirmado
  vía `git log`) y seguirían así sin cambio aunque el driver corra hoy.
- **D-08 (abierto para planning, no para discuss):** `capture()` no se auto-timestampea. Se necesita
  o bien un envelope wrapper (espejando la forma `{"captured_at": ..., ...}` que ya usa
  `_write_schema_snapshot`) o una cita explícita del timestamp en el SUMMARY del plan. El requisito
  en sí —evidencia fechada que Phase 43 pueda citar como no-stale— está LOCKED; la forma concreta
  queda a discreción del planner.

### Claude's Discretion

- Forma exacta del cambio D-04 (llamada externa a `census_matriz()` vs. flag `--matriz-only`).
- Forma exacta del envelope/timestamp de D-08 (wrapper JSON vs. cita en SUMMARY).
- Si el DNS de higyrus resuelve limpio en esta corrida, D-06 (rename) no aplica — el planner no
  necesita ramificar el plan para ambos casos por adelantado; el resultado de D-05 decide en
  ejecución si D-06 dispara.

### Folded Todos

Ninguno — `todo.match-phase 42` devolvió 0 coincidencias.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning o implementar.**

- `.planning/ROADMAP.md` § Phase 42 (líneas 98-111) — goal, 5 criterios de éxito LOCKED, depends-on
- `.planning/ROADMAP.md` líneas 49-56 — notas de sizing y restricciones del milestone v1.8
  (incluye la corrección explícita de que el gate del script está STALE, no "listo")
- `.planning/REQUIREMENTS.md` — LIVE-01, LIVE-02 (texto exacto de los dos requisitos)
- `.planning/research/SUMMARY.md` — § Phase 2 (rationale, pitfalls 1/2/3/8 evitados)
- `main_matriz.py` — `_VENUE_ALLOWLIST` (línea 139), `_venue_token` (línea ~232), comentarios D-02
  (líneas 115-137)
- `scripts/literal_census_33.py` — `census_matriz` (línea 175), `census_iol` (línea 241), `main`
  (línea 353), gate stale (línea 192)
- `main_higyrus.py` — rama `_vendor_unreachable` (líneas 669-684), `write_run_evidence` (líneas
  2916-2922), cascade D-HIGY-10 (líneas 222-254)
- `main_market_data.py` — `_write_schema_snapshot` (líneas 457-522), probe sites instruments/segments
  (líneas ~975, ~1004)
- `verification/mutation_gate.py` — `_SANDBOX_HOST` remarkets-only, criterio 4 (byte-idéntico)
- `verification/capture.py` — mecanismo `capture()` (líneas 42-51)
- `.planning/milestones/v1.7-phases/39-verificaci-n-en-vivo-del-encadenamiento-profundo/39-01-PLAN.md`
  — precedente de forma del checkpoint `gate="blocking-human"`
- `.planning/milestones/v1.7-phases/39-verificaci-n-en-vivo-del-encadenamiento-profundo/39-CONTEXT.md`
  — autorización original D-02 de bbsa
- `.planning/verification/schemas/market-data-client/get-instruments.json`,
  `get-segments.json` — baseline 2026-07-31, marcado no-autoritativo para SHAPE-01
- `verification/test_main_matriz_skip_line_shape.py:24-40` — patrón del test de spoofing a espejar
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `main_matriz._venue_token(base_url)` — fail-closed, exact-hostname, ya testeable por import
  (diseñado explícitamente así en Phase 39 plan 01)
- `verification.capture.capture(pkg, label, raw)` — dump crudo a staging gitignored, ya usado por
  matriz/iol en `literal_census_33.py`
- `write_run_evidence(...)` en `main_higyrus.py` — overwrite con `captured_at` fresco en cada corrida
- `--selftest` flag existente en `literal_census_33.py` (línea 355) — patrón a espejar si se agrega
  `--matriz-only`

### Established Patterns
- Allowlist exacto por hostname, fail-closed (`_venue_token` devuelve `None` en cualquier caso
  imparseable/no listado)
- SKIPPED con causa medida + destino nombrado, nunca un cero silencioso (D-13, D-HIGY-10)
- Schema snapshot write-once / no-overwrite-on-drift (D-25) — deliberadamente NO sirve para
  "evidencia fresca fechada"
- Checkpoint humano bloqueante: `gate="blocking-human"`, cero archivos tocados hasta la aprobación,
  operador transcribe "approved" verbatim

### Integration Points
- `scripts/literal_census_33.py` pasa a importar `main_matriz` (nueva dependencia intra-repo,
  ambos son scripts de raíz, no packages — no viola la restricción de "sin código compartido entre
  paquetes", que aplica a `packages/`)
- Los `capture()` calls nuevos en `main_market_data.py` alimentan directamente la Phase 43
  (precondición de evidencia documentada en `REQUIREMENTS.md § Dependencias cross-fase`)
</code_context>

<specifics>
## Specific Ideas

Ninguna referencia particular más allá de las decisiones de arriba — las 5 áreas cubren toda la
superficie de implementación que research y el análisis de codebase identificaron como
genuinamente subdeterminada por el ROADMAP.
</specifics>

<deferred>
## Deferred Ideas

Ninguna — el análisis se mantuvo dentro del boundary de la fase. La re-confirmación de DT-07 (censo
iol) queda explícitamente NO absorbida en esta fase (D-04) por estar ya cerrada y fuera del texto
de LIVE-02; si algún futuro audit la cuestiona, es una fase/corrida separada.

### Reviewed Todos (not folded)

Ninguno — `todo.match-phase 42` devolvió 0 coincidencias.
</deferred>
