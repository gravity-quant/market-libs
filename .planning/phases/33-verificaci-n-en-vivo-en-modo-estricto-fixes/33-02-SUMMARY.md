---
phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
plan: 02
subsystem: testing
tags: [decode-divergence, probe-context, findings, fid-seed, strict-decode, matriz, higyrus]

requires:
  - phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
    provides: "`verification/divergences.py` — `probe_context`, `endpoint_scope`, `divergence_capture`, `DivergenceHandler`, y la convención de título lockeada `surface-in-title-write-new` (plan 33-01)"
  - phase: 29-decoder-observable
    provides: "el walker observable, el record congelado de seis claves y los `<Pkg>DecodeError` por paquete"
  - phase: 15-driver-migration
    provides: "el patrón ONE Client per main() que `strict_decode` respeta como kwarg de constructor"
provides:
  - "`main_matriz.py` y `main_higyrus.py` sobreviven al modo estricto: los dos drivers que morían con traceback y cero findings ahora corren hasta su SUMMARY"
  - "63 sitios de probe decorados (matriz 46/46 + higyrus 17 restantes → 19/19), cada uno con endpoint sin interpolar y superficie explícita"
  - "`main_matriz.py::_seed_fid_counter` — el allocator de matriz arranca en F-11, por encima de sus diez fids terminales"
  - "el formato de línea SUMMARY unificado que 33-04 parsea para el censo: `DIVERGENCES=N HANDLER_ERRORS=N`"
  - "el par de helpers bare/`_pair` que resuelve las dos formas canónicas de retorno de probe en ambos drivers"
affects: [33-03, 33-04, 33-05, 33-06, 33-07]

actuals:
  tokens: 9800
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "decorador de binding aplicado mecánicamente sobre un censo AST, con la propia consulta AST como gate RED/GREEN en lugar de un archivo de test nuevo"
    - "seam de fallback tipado en dos variantes (escalar y 2-tuple) cuando un driver tiene más de una forma canónica de retorno de probe"
    - "angostamiento de un `except` de clase-base a la familia que el docstring ya enumeraba, para des-sombrear un handler externo"

key-files:
  created: []
  modified:
    - main_matriz.py
    - main_higyrus.py

key-decisions:
  - "Dos helpers de fallback por driver, no uno: matriz y higyrus tienen CADA UNO dos formas canónicas de retorno de probe (2-tuple con payload vs `ProbeResult` pelado). Un único fallback con forma de 2-tuple habría metido una tupla en una `list[ProbeResult]` / `dict[str, ProbeResult]` y el `r.name` / `r.status` del loop de impresión habría explotado con `AttributeError` — bajo modo estricto, exactamente el crash que este plan existe para eliminar"
  - "Los dos probes de login de higyrus angostan su primer bracket de `HigyrusClientError` a `HigyrusAPIError`: `HigyrusDecodeError` es hermano, no subclase, y la base lo tragaba — una divergencia de forma en login habría salido reclasificada como AUTH Y habría seteado `_auth_failed`, cascadeando SKIPPED a los 17 probes restantes"
  - "Superficie `sync` para los probes sin sufijo (`field_type_map`, `schema_snapshot`, `parity_sync_async`, `auth_401`, `multi_account_iteration`, y los 18 del sweep de matriz que usan nombres pelados): es la superficie que su código realmente ejercita y la que sus propios `append_finding` ya declaran"
  - "Endpoint `\"-\"` (el default del `ContextVar`) para los dos probes por driver que no hacen ninguna llamada en vivo (`field_type_map`, `schema_snapshot`): inventarles un endpoint sería atribuir una divergencia a un endpoint que ese probe nunca tocó"
  - "Formato de línea SUMMARY idéntico en los dos drivers (`... FINDING=N DIVERGENCES=N HANDLER_ERRORS=N`) para que 33-04 parsee una sola forma"
  - "Cero `endpoint_scope` en matriz (ningún probe llama a más de un client function en su `try`); uno en higyrus (`probe_multi_account_iteration`) más uno fuera de probe (`_capture_async_query_string`)"

patterns-established:
  - "RED/GREEN por censo AST: la consulta AST del `<acceptance_criteria>` se corre ANTES del cambio y se registra su salida no vacía (46/46 y 17/19 sin decorar, exit 1), y después se re-corre para el GREEN — sin fabricar un archivo de test que colisionaría con el gate que 33-04 tiene asignado"
  - "Verificación conductual del seam por triple forma: se falsifica con un cliente falso que levanta el `<Pkg>DecodeError` y se comprueba que las tres formas de probe (2-tuple sync, escalar sync, escalar async) devuelven la forma correcta y que los `ContextVar` quedan reseteados"

requirements-completed: []

coverage:
  - id: D8
    description: "Los 46 probes de `main_matriz.py` y los 19 de `main_higyrus.py` cargan `probe_context` con endpoint sin interpolar y superficie coincidente con el sufijo de la función (criterio 1, D-02)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "censo AST sobre ambos drivers: `undecorated == []`, exit 0 (RED previo: 46 y 17 nombres, exit 1)"
        status: pass
      - kind: other
        ref: "`grep -v '^#' main_matriz.py | grep -c 'probe_context('` = 46; idem higyrus = 19"
        status: pass
    human_judgment: false
  - id: D9
    description: "Un probe que levanta `<Pkg>DecodeError` devuelve su forma canónica con status FINDING en vez de propagar; el driver sobrevive hasta su SUMMARY (criterio 1, D-05)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "falsificación con cliente falso — matriz: `probe_get_segments` → 2-tuple FINDING, `probe_error_bogus_symbol` → ProbeResult FINDING, `probe_error_bogus_symbol_async` → ProbeResult FINDING"
        status: pass
      - kind: other
        ref: "falsificación con cliente falso — higyrus: `probe_login_sync` → ProbeResult FINDING con `_auth_failed` intacto en False, `probe_get_listado_cuentas_sync` → 2-tuple FINDING"
        status: pass
    human_judgment: false
  - id: D10
    description: "`main_matriz.py` emite fids por encima de F-10, así que los primeros diez findings de cada corrida dejan de ser un no-op silencioso (P-3 / T-33-11)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "`import main_matriz; _fid_counter` 0 → `_seed_fid_counter()` → 10 → `_next_fid()` = `F-11`"
        status: pass
      - kind: other
        ref: "orden en `main()`: `write_findings(_PKG)` < `_seed_fid_counter()` < primer probe"
        status: pass
    human_judgment: false
  - id: D11
    description: "Ninguno de los dos drivers gana un guard de Exception amplio; el contrato de aislamiento per-probe queda intacto (D-06 / T-33-10)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_main_drivers_bare_except.py::test_no_bare_except_in_driver[main_matriz.py]"
        status: pass
      - kind: unit
        ref: "verification/test_main_drivers_bare_except.py::test_no_bare_except_in_driver[main_higyrus.py]"
        status: pass
    human_judgment: false
  - id: D12
    description: "`strict_decode=_STRICT` viaja por exactamente un `Client` y un `AsyncClient` por driver; el gate AST de single-Client sigue verde (Pitfall 1 / TokenStore)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_main_matriz_uses_single_client_instance.py (2 casos)"
        status: pass
      - kind: unit
        ref: "verification/test_main_higyrus_uses_single_client_instance.py"
        status: pass
    human_judgment: false
  - id: D13
    description: "El decorador no introdujo ninguna rotura nueva en los dos archivos canario que invocan probes directamente (carry-forward 3 de 33-01)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: other
        ref: "`test_matriz_sweep_snapshot.py` + `test_main_matriz_login_fail_uniformity.py`: 19 failed / 3 passed / 19 errors, set de node ids idéntico pre y post"
        status: pass
    human_judgment: true
    rationale: "Decidir que un set rojo idéntico cuenta como 'sin regresión' —y no como 'sigue roto'— es un juicio de scope contra la línea base committeada, no un chequeo mecánico."

duration: 15min
completed: 2026-08-26
status: complete
---

# Phase 33 Plan 02: matriz + higyrus onto the divergence mechanism Summary

**Los dos drivers que bajo `MARKET_LIBS_STRICT_DECODE=1` morían con traceback y cero findings ahora
corren hasta su SUMMARY: 63 sitios de probe quedan bindeados a su endpoint y superficie, el allocator
de fids de matriz arranca por encima de sus diez fids terminales, y en el camino se cerraron tres
canales de falso limpio que el plan no había previsto — dos formas de retorno de probe por driver que
un único fallback habría roto, y un `except` de clase-base en login que se tragaba el decode error y
cascadeaba SKIPPED a los 17 probes restantes.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-08-26T23:42:38Z
- **Completed:** 2026-08-26T23:57:28Z
- **Tasks:** 2 de 2
- **Files created/modified:** 2 (917 insertions, 267 deletions)

## Accomplishments

- **El criterio 1 deja de tener dos agujeros del tamaño de un driver.** matriz (46 probes) y higyrus
  (19) son los dos únicos paquetes cuyo `<Pkg>DecodeError` es **hermano** de su `<Pkg>APIError` y no
  figura en su `_RESIDUAL_PROBE_EXCEPTIONS`; con cero guards de Exception amplios (AST-gated), el
  modo estricto los mataba en el primer diverge. Ahora el decorador intercepta, el `DivergenceHandler`
  escribe el `SHAPE`, y el driver sigue.
- **Ninguna ruta de endpoint interpolada llega a un finding.** Los 63 decoradores toman el template
  verbatim de `_ENDPOINT_TEMPLATES` — `/rest/risk/position/getPositions/{account_id}` y
  `/api/cuentas/{id_cuenta}/movimientos` viajan con el placeholder puesto, verificado
  conductualmente (T-33-08).
- **El allocator de matriz deja de tirar sus primeros diez findings a la basura.** Los diez fids
  committeados de matriz son **todos** no-`OPEN` (7 `NO-FIX`, 2 `EXPECTED`, 1 `FIXED`), es decir el
  caso peor del short-circuit de `append_finding`: no-op silencioso mientras `FINDING=N` los sigue
  contando. Con el seed, el primer fid de la corrida es `F-11`.
- **La unidad del censo sale impresa por los dos drivers, con la misma forma de línea.** `DIVERGENCES`
  es `len(handler.seen)` y no el conteo de findings — con la superficie en el título hay ~2 findings
  por triple, y confundirlos rompería el contraste contra el piso ≥96. `HANDLER_ERRORS` hace visible
  cualquier falla del sink, que si no se pierde en el scrollback.
- **Los dos archivos canario no se movieron ni un node id.** 19 failed / 3 passed / 19 errors antes y
  después, exactamente los 17/17 y 2/2 que `33-BASELINE.md` predice.

## Probes que requirieron `endpoint_scope` (P-5)

Auditado por AST: se listaron, por probe, todas las llamadas a un client function dentro de su cuerpo,
y se marcó como caso P-5 todo probe con más de un endpoint distinto.

| Driver | Probe | Endpoints | Tratamiento |
|---|---|---|---|
| `main_matriz.py` | — | — | **Ninguno.** Los 46 probes llaman a lo sumo un endpoint. Los dos casos que a primera vista parecen múltiples no lo son: `probe_get_instruments_by_cfi_sanity` (+ su par async) itera 8 CFI codes **contra el mismo** `/rest/instruments/byCFICode`, y `probe_field_type_map` / `probe_schema_snapshot` no hacen ninguna llamada en vivo (operan sobre `payloads` ya capturados), por eso llevan endpoint `"-"`. |
| `main_higyrus.py` | `probe_multi_account_iteration` | `get_listado_cuentas` (fuente 2) → `get_movimientos` (loop) | Decorador bindea `get_listado_cuentas`; el loop de `get_movimientos` va dentro de `endpoint_scope(_ENDPOINT_TEMPLATES["get_movimientos"])`. Verificado conductualmente: la primera llamada ve `/api/cuentas/listadoCuentas` y la segunda `/api/cuentas/{id_cuenta}/movimientos`. |
| `main_higyrus.py` | `_capture_async_query_string` (call site en `_async_main`, **no** es un probe) | `get_movimientos` | Único call site de decode en vivo del driver fuera de todo `probe_*`. Se le puso `endpoint_scope` para que el `diff` del finding no diga `via -`. La superficie sigue en `"-"` — ver carry-forward 2. |

## Formato exacto de la línea SUMMARY (33-04 la parsea)

Ambos drivers imprimen la MISMA forma, vía `safe_print(..., secrets=secrets)`:

```
SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N DIVERGENCES=N HANDLER_ERRORS=N
```

f-strings verbatim:

```python
# main_matriz.py
f"SUMMARY: PASS={counts['PASS']} FAIL={counts['FAIL']} "
f"SKIPPED={counts['SKIPPED']} FINDING={counts['FINDING']} "
f"DIVERGENCES={len(handler.seen)} HANDLER_ERRORS={len(handler.errors)}"

# main_higyrus.py
f"SUMMARY: PASS={n_pass} FAIL={n_fail} SKIPPED={n_skip} FINDING={n_find} "
f"DIVERGENCES={len(handler.seen)} HANDLER_ERRORS={len(handler.errors)}"
```

Semántica que 33-04 y 33-05 **no** pueden confundir:

- `DIVERGENCES` = `len(DivergenceHandler.seen)` = triples distintos
  `(slug, model, field_path, kind)`. **Ésta es la unidad del censo**, la única directamente
  comparable con `29-SIZING.md` sin traducir.
- `FINDING` = probes cuyo `ProbeResult.status` es `"FINDING"`. No es ni el conteo de findings escritos
  ni el del censo.
- `HANDLER_ERRORS` = `len(DivergenceHandler.errors)`. **Un valor distinto de cero invalida el censo de
  esa corrida** (P-02: un verde producido por una excepción tragada del handler es un falso limpio).

Los tres campos nuevos van DESPUÉS de los cuatro originales, así que cualquier parser existente que
lea por prefijo sigue funcionando.

## `test_matriz_sweep_snapshot.py`: set pre y post decorador

Medido con `uv run pytest verification/test_matriz_sweep_snapshot.py verification/test_main_matriz_login_fail_uniformity.py -q --tb=no -rfE`.

| | Pre (antes de la Task 1) | Post (ambas tasks) |
|---|---|---|
| Resumen | `19 failed, 3 passed, 19 errors` | `19 failed, 3 passed, 19 errors` |
| `test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved` | 17 FAILED + 17 ERROR | 17 FAILED + 17 ERROR |
| `test_main_matriz_login_fail_uniformity.py::test_probe_login_sync_returns_FINDING_on_authentication_error` | FAILED + ERROR | FAILED + ERROR |
| `test_main_matriz_login_fail_uniformity.py::test_probe_login_sync_returns_FINDING_on_unexpected_exception` | FAILED + ERROR | FAILED + ERROR |

**Set de node ids idéntico, sin deltas.** Coincide exactamente con el 17/17 y 2/2 que el
carry-forward 3 de `33-01-SUMMARY.md` exigía comparar. La causa raíz sigue siendo la única ya
registrada en `33-BASELINE.md` (ambos archivos invocan los probes sin el parámetro `client` que la
migración REFAC-05 de la Phase 15 introdujo) y sigue ruteada a `HARN-VERIF-01`. El decorador **no**
agregó ni quitó rojo.

## Task Commits

1. **Task 1: matriz — seed the fid allocator, thread the strict flag, decorate all 46 probes** — `f4a767b` (feat)
2. **Task 2: higyrus — decorate the remaining 17 probes and install the handler in main()** — `71d6c15` (feat)
3. **Alineación del docstring de módulo de matriz con el SUMMARY real** — `b7f6b71` (docs; ver Deviations, #4)

## Files Created/Modified

- `main_matriz.py` — `max_existing_fid` / `probe_context` / `divergence_capture` al bloque de
  imports, `MatrizDecodeError` al import de paquete, `_STRICT`, `_seed_fid_counter()`,
  `_shape_probe_result` + `_shape_probe_result_pair`, `probe_context` sobre los 46 probes,
  `strict_decode=_STRICT` en los dos constructores, `divergence_capture` alrededor del sweep, y la
  línea SUMMARY extendida.
- `main_higyrus.py` — `divergence_capture` / `endpoint_scope` al bloque de imports, split de
  `_shape_probe_result` en bare + `_pair`, `probe_context` sobre los 17 probes restantes,
  `endpoint_scope` en `probe_multi_account_iteration` y en el capture async, angostamiento del
  bracket de los dos probes de login, `divergence_capture` alrededor del sweep, y la línea SUMMARY
  extendida.

## Decisions Made

1. **Dos helpers de fallback por driver.** Ver Deviations #1 — es la decisión de mayor radio del plan.
2. **`surface` para los probes sin sufijo.** El plan dice "set `surface` from the function's own
   suffix", pero 5 probes de higyrus (`parity_sync_async`, `field_type_map`, `schema_snapshot`,
   `auth_401`, `multi_account_iteration`) y los 24 sync de matriz (que usan nombres pelados como
   `probe_get_segments`) no tienen sufijo. Se les asignó la superficie que su código **realmente
   ejercita**, que es además la que sus propios `append_finding` ya declaran: `sync` en los 29 casos.
   `probe_parity_sync_async` compara sync contra async pero su única llamada en vivo es la sync
   (`_capture_sync_query_string`); el query async le llega ya capturado por parámetro.
3. **Endpoint `"-"` para los probes sin llamada en vivo.** `field_type_map` y `schema_snapshot` en
   ambos drivers operan sobre payloads ya capturados. `"-"` es el default del `ContextVar` y significa
   exactamente "ningún endpoint bindeado"; inventarles uno habría atribuido una divergencia a un
   endpoint que ese probe nunca tocó.
4. **`_RESIDUAL_PROBE_EXCEPTIONS` de matriz intacto.** Confirmado conductualmente que
   `MatrizDecodeError` no cae en él: hereda de `MatrizClientError`, mientras la tupla lista
   `PrimaryAPIError`, `httpx.HTTPError`, `OSError`, `AttributeError`, `TypeError`, `ValueError` y
   `KeyError`. Meterlo ahí lo habría mapeado a `ERROR-MAP` con título único por probe, que
   `idempotent_by_title` no puede deduplicar.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Un solo `_shape_probe_result` habría roto 37 probes bajo modo estricto**

- **Found during:** Task 1 (y espejado en la Task 2)
- **Issue:** El plan especifica un `_shape_probe_result` que "returns the driver's canonical 2-tuple",
  asumiendo que cada driver tiene UNA forma canónica de retorno de probe. No es así, en ninguno de los
  dos. En matriz, 18 probes del sweep devuelven `(ProbeResult, raw_payload | None)` porque `main()`
  acumula sus payloads, pero los otros 28 (login, `field_type_map`, los 3 error probes,
  `schema_snapshot` y **los 22 async**) devuelven un `ProbeResult` pelado. En higyrus el split es 8 y
  11. Con un único fallback de forma 2-tuple, cualquier decode error en uno de esos 39 probes habría
  hecho que `results.append(probe_error_bogus_symbol(client))` metiera una **tupla** en una
  `list[ProbeResult]`, y el `r.name` del loop de impresión habría reventado con `AttributeError` —
  es decir, el driver habría seguido muriendo bajo modo estricto, sólo que más tarde y con peor
  diagnóstico. mypy no lo detecta: `probe_context` devuelve `_F` vía `cast`.
- **Fix:** Dos helpers por driver — `_shape_probe_result(...) -> ProbeResult` (la forma base) y
  `_shape_probe_result_pair(...) -> tuple[ProbeResult, None]` (que envuelve a la anterior). Cada probe
  recibe el que corresponde a su firma. En higyrus eso implicó re-apuntar los dos probes de health que
  el plan 01 ya había decorado, de `_shape_probe_result` a `_shape_probe_result_pair` — un rename, sin
  cambio de comportamiento, hecho para que los dos drivers usen UNA sola convención de nombres (33-04
  lee los dos).
- **Files modified:** `main_matriz.py`, `main_higyrus.py`
- **Verification:** falsificación con clientes falsos que levantan el `<Pkg>DecodeError` — las tres
  formas (2-tuple sync, escalar sync, escalar async) devuelven cada una su forma correcta con status
  `FINDING`.
- **Committed in:** `f4a767b` / `71d6c15`

**2. [Rule 2 - Missing critical] Los dos probes de login de higyrus se tragaban el decode error y cascadeaban SKIPPED**

- **Found during:** Task 2, al verificar conductualmente el seam
- **Issue:** `probe_login_sync` y `probe_login_async` capturan `HigyrusClientError` — la clase **base**
  del paquete. `HigyrusDecodeError` es hermano de `HigyrusAPIError`, pero ambos cuelgan de esa base,
  así que el bracket lo atrapaba. Consecuencia doble: (a) una divergencia de forma salía reclasificada
  como finding `AUTH`, y (b) el handler setea `_auth_failed = True`, que cascadea `SKIPPED` a los 17
  probes restantes — el censo entero de la corrida colapsado por una divergencia de forma en login.
  Y con eso, el `probe_context` de esos dos probes era código muerto: reportar 19/19 decorados como
  cobertura cuando 2 no pueden dispararse nunca es precisamente el "señal que no inspeccionó nada"
  que P-02 prohíbe. Hoy `parse_login_response` no pasa por `_decode._response_parser`, así que el
  swallow es latente y no activo — pero la latencia es del tamaño del sweep entero.
- **Fix:** Angostado el primer bracket de `HigyrusClientError` a `HigyrusAPIError` en ambos probes.
  La lista que el docstring de `probe_login_sync` ya enumeraba (`HigyrusAuthError` 401,
  `HigyrusAuthorizationError` 403, `HigyrusRateLimitError` 429, `HigyrusAPIError` otros non-2xx) **es
  exactamente** la familia `HigyrusAPIError`; el `Decode` nunca fue intencional ahí. El angostamiento
  pierde únicamente `HigyrusDecodeError`, que es el que ahora intercepta el decorador. El plan pide
  dejar la escalera intacta, y la escalera que el plan describe (`HigyrusAuthError` → `HigyrusAPIError`
  → decode → residual) es justamente la que este cambio restaura; el `HigyrusClientError` era la
  desviación.
- **Files modified:** `main_higyrus.py`
- **Verification:** `probe_login_sync` con un cliente falso que levanta `HigyrusDecodeError` devuelve
  `ProbeResult(login_sync, FINDING, "SHAPE [sync] Cuenta.saldo declared=float observed=str")` y
  `_auth_failed` queda en `False`. `uv run pytest packages/higyrus-client -q` → 239 passed.
- **Committed in:** `71d6c15`

**3. [Rule 2 - Missing critical] El único call site de decode en vivo fuera de un probe quedaba sin endpoint**

- **Found during:** Task 2, en la auditoría P-5
- **Issue:** `_capture_async_query_string` llama a `aclient.get_movimientos(...)` desde `_async_main`,
  fuera de todo `probe_*`, así que ninguna divergencia suya quedaba bindeada y el `diff` del finding
  habría dicho `via -`. Es el único caso de este tipo en el driver (el capture sync sí vive dentro de
  `probe_parity_sync_async`, que está decorado).
- **Fix:** `endpoint_scope(_ENDPOINT_TEMPLATES["get_movimientos"])` alrededor del call site.
- **Files modified:** `main_higyrus.py`
- **Verification:** `uv run ruff check .`, `uv run mypy`, `uv run pytest packages/higyrus-client -q`
  verdes; el gate de bare-except sigue verde.
- **Committed in:** `71d6c15`
- **Nota:** la **superficie** sigue en `"-"` en ese call site. Ver carry-forward 2 — no es un hueco del
  censo, y cerrarlo requiere un `surface_scope` en `verification/divergences.py`, fuera de los
  `<files>` de este plan.

**4. [Rule 1 - Bug] El docstring de módulo de matriz anunciaba un SUMMARY que el driver ya no imprime**

- **Found during:** redacción de este SUMMARY
- **Issue:** El docstring seguía documentando `SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N`. El plan
  33-04 parsea esa línea para el censo; un docstring que describe un formato distinto del real es una
  ruta falsa para quien lo lea antes que al código.
- **Fix:** Docstring alineado, con la semántica de los dos campos nuevos.
- **Files modified:** `main_matriz.py`
- **Verification:** `uv run ruff check .` y `uv run mypy` verdes.
- **Committed in:** `b7f6b71`

---

**Total deviations:** 4 auto-fixed (3× Rule 2, 1× Rule 1)
**Impact on plan:** Ninguno sobre el scope. Las tres de Rule 2 son requisitos de corrección sin los
cuales el entregable declarado del plan —"los dos drivers corren hasta completarse bajo modo
estricto"— sería falso: dos de ellas producen un crash o un colapso del sweep, y la tercera una
atribución errónea. Cero scope creep: no se tocó ninguna copia de `_decode.py`, ni
`_RESIDUAL_PROBE_EXCEPTIONS` en ninguno de los dos drivers, ni ninguna de las 19 fallas pre-existentes
de `verification/`, ni ninguno de los 43 errores pre-existentes de `uv run mypy verification`.

## Issues Encountered

- **La Task 1 y la Task 2 no admiten un RED de archivo de test nuevo.** Los `<files>` de ambas tasks
  son sólo el driver, y el gate a nivel driver (`verification/test_probe_context_coverage.py`,
  `test_finding_count_consistency.py`) está explícitamente asignado al plan 33-04 por el
  carry-forward 2 de `33-01-SUMMARY.md`; crearlo acá habría colisionado. El RED se demostró con el
  **censo AST del propio `<acceptance_criteria>`**, corrido antes del cambio: `main_matriz.py`
  46 probes / 46 sin decorar (exit 1) y `main_higyrus.py` 19 / 17 sin decorar (exit 1). Post-cambio,
  ambos exit 0 con lista vacía. Mismo precedente de falsificación que la Task 3 del plan 33-01.
- **Se usó `git stash` una vez por error, contra la prohibición explícita del workflow.** Ocurrió en
  el árbol principal (no en un worktree, donde el stash es compartido y el riesgo real), la entrada
  contenía exactamente `main_higyrus.py` con parent `f4a767b` —verificado con
  `git stash show --name-only` y `git rev-parse stash@{0}^` antes de tocarla— y se restauró de
  inmediato. `git stash list` quedó vacío y el conteo de `probe_context` volvió a 19. Cero pérdida.
- **Una corrida de verificación conductual ensució `.planning/verification/higyrus-client-findings.md`.**
  El primer experimento (previo al angostamiento del bracket de login) hizo que `probe_login_sync`
  llamara a `append_finding` de verdad, lo que refrescó el header de Run Context con el `base_url`
  falso `https://api.test`. Revertido con `git checkout --` sobre ese único archivo;
  `git status --porcelain .planning/verification/` quedó vacío antes de ambos commits. Los
  experimentos posteriores ya no escriben, que es precisamente el contrato de `_shape_probe_result`.

## Carry-forwards

1. **Los 18 probes del sweep sync de matriz no ejercitan la superficie tipada.** Van por
   `_sync_matriz_request` → `parse_envelope_response`, que devuelve el envelope crudo sin pasar por
   `_decode.walk_model`; los únicos sitios de matriz que decodifican modelos hoy son los 3 error
   probes sync y los 22 async (vía `aclient.*`). Es decir que el decorador está puesto en los 46, pero
   sólo ~25 pueden emitir un record. **Esto no es un defecto introducido acá** — es la forma que la
   migración 15-05 le dejó al driver — pero sí acota cuánto censo puede producir la superficie sync de
   matriz, y 33-04 debería medirlo antes de contrastar contra el piso.
2. **La superficie del capture async de higyrus queda en `"-"`.** `endpoint_scope` re-bindea el
   endpoint pero no la superficie, y `verification/divergences.py` no expone un `surface_scope`. **No
   es un hueco del censo**: `handler.seen` se indexa por `(slug, model, field_path, kind)`, sin
   endpoint ni superficie, y las mismas triples llegan bien atribuidas vía
   `probe_get_movimientos_async`. El efecto es una tercera variante de título (`[-]`) que ensucia la
   identidad de dedupe. Destino: **plan 33-04**, junto con el gate de `probe_context` coverage — ahí
   se decide si agregar `surface_scope` o mover el capture adentro de un probe.
3. **El gate de P-3 a nivel driver sigue pendiente para matriz y higyrus.** `_seed_fid_counter` existe
   y funciona en los dos (verificado empíricamente: matriz 0→10→`F-11`), pero ningún test asevera el
   orden obligatorio `write_findings` < `_seed_fid_counter` < primer probe, como sí hace
   `verification/test_main_iol_fid_seed.py` para iol. Destino: **plan 33-04** (ya era su carry-forward
   2 desde 33-01; este plan agrega matriz a la lista de drivers a espejar).
4. **`33-BASELINE.md` sigue siendo el único árbitro del rojo de `verification/`.** El plan 33-03 debe
   re-correr los mismos dos archivos canario tras tocar los otros tres drivers y comparar contra el
   mismo 17/17 y 2/2. Un número distinto no es "más del rojo que ya estaba".

## Known Stubs

Ninguno. Los 63 decoradores están cableados a fuentes reales: el endpoint sale de los
`_ENDPOINT_TEMPLATES` que los dos drivers ya usaban para sus snapshots, la superficie del sufijo real
de cada función, el `decode_error` de la excepción real de cada paquete, y el `next_fid` del allocator
real del driver. El endpoint `"-"` de los cuatro probes sin llamada en vivo no es un placeholder
pendiente de cablear: es el valor que significa "ningún endpoint bindeado", y esos probes
efectivamente no tocan ninguno.

## TDD Gate Compliance

| Gate | Evidencia |
|---|---|
| RED (Task 1) | Censo AST pre-cambio sobre `main_matriz.py`: `total probes: 46 | undecorated: 46`, exit 1, con los 46 nombres impresos. Fid allocator: `_fid_counter = 0` → `_next_fid()` daría `F-01`, que está `NO-FIX` (terminal → no-op silencioso). |
| GREEN (Task 1) | `f4a767b`. Censo AST post-cambio: `undecorated: []`, exit 0. Seed: `0 → 10 → F-11`. Falsificación conductual del seam en las tres formas de probe. |
| RED (Task 2) | Censo AST pre-cambio sobre `main_higyrus.py`: `total probes: 19 | undecorated: 17`, exit 1, con los 17 nombres impresos. |
| GREEN (Task 2) | `71d6c15`. Censo AST post-cambio: `undecorated: []`, exit 0. Falsificación conductual de las dos formas de probe, del aislamiento de la cascade de auth y del re-binding P-5. |

**Sin commit `test(...)` separado, deliberadamente:** el gate de este plan es la consulta AST escrita
en su propio `<acceptance_criteria>`, no un archivo de test nuevo — que además habría colisionado con
`verification/test_probe_context_coverage.py`, asignado al plan 33-04. Fabricar un `test(...)` vacío
para satisfacer la forma del gate habría sido justamente un verde producido por una señal que no
inspecciona nada. Sin fase REFACTOR: no hizo falta.

## Verification Evidence

| Gate | Resultado |
|---|---|
| Censo AST `probe_context` — `main_matriz.py` | `undecorated: []`, exit 0 |
| Censo AST `probe_context` — `main_higyrus.py` | `undecorated: []`, exit 0 |
| `grep -v '^#' main_matriz.py \| grep -c 'probe_context('` | 46 (= 46 requerido) |
| `grep -cE '^(async )?def probe_' main_matriz.py` | 46 |
| `grep -v '^#' main_matriz.py \| grep -c '_seed_fid_counter'` | 5 (≥2 requerido) |
| `grep -v '^#' main_matriz.py \| grep -c 'strict_decode=_STRICT'` | 2 |
| `grep -v '^#' main_matriz.py \| grep -c 'MatrizDecodeError'` | 50 (≥2 requerido) |
| `grep -v '^#' main_higyrus.py \| grep -c 'probe_context('` | 19 (= 19 requerido) |
| `grep -cE '^(async )?def probe_' main_higyrus.py` | 19 |
| `grep -v '^#' main_higyrus.py \| grep -c 'divergence_capture('` | 1 (≥1 requerido) |
| `grep -v '^#' main_higyrus.py \| grep -c 'endpoint_scope('` | 2 (probe P-5 + capture async) |
| `uv run pytest verification/test_main_drivers_bare_except.py -q` | 2 passed — cero guards de Exception amplios en los dos drivers |
| `uv run pytest verification/ -q -k uses_single_client_instance` | passed (matriz 2 casos + higyrus + los otros drivers) |
| `uv run pytest verification/test_matriz_sweep_snapshot.py verification/test_main_matriz_login_fail_uniformity.py -q` | `19 failed, 3 passed, 19 errors` — set de node ids idéntico al baseline |
| `uv run pytest packages/matriz-client -q` | 430 passed |
| `uv run pytest packages/higyrus-client -q` | 239 passed |
| `uv run pytest packages -q` (equivalente CI) | 1736 passed, 1 deselected |
| `uv run python tools/check_decode_intactness.py` | exit 0 — Checks A/B/C/D verdes, ninguna copia de `_decode.py` tocada |
| `uv run python tools/check_surface_types.py` | exit 0 |
| `uv run python tools/check_uniform_structure.py` | exit 0 |
| `uv run mypy` | Success: no issues found in 75 source files |
| `uv run ruff check . && uv run ruff format --check .` | limpio, 245 archivos formateados |
| Seed de fids de matriz | `_fid_counter` 0 → `_seed_fid_counter()` → 10 → `_next_fid()` = `F-11` |
| Interceptación de decode (matriz, 3 formas) | 2-tuple sync / escalar sync / escalar async → todas `FINDING`, driver sobrevive |
| Interceptación de decode (higyrus, 2 formas + cascade) | escalar y 2-tuple → `FINDING`; `_auth_failed` queda en `False` |
| Re-binding P-5 (`probe_multi_account_iteration`) | llamada 1 ve `/api/cuentas/listadoCuentas`, llamada 2 ve `/api/cuentas/{id_cuenta}/movimientos` |
| Reset de `ContextVar` post-probe | `_ENDPOINT` y `_SURFACE` vuelven a `"-"` |
| `git status --porcelain .planning/verification/` | vacío antes de ambos commits |

## Self-Check: PASSED

- Los 2 archivos declarados en `key-files.modified` existen en disco.
- Los 3 hashes de commit declarados (`f4a767b`, `71d6c15`, `b7f6b71`) existen en `git log`.
- El formato de línea SUMMARY citado en la sección homónima está copiado verbatim del código de los
  dos drivers, no parafraseado — 33-04 lo parsea desde ahí.
- El set pre/post de `test_matriz_sweep_snapshot.py` está medido en esta misma sesión con el mismo
  comando, no citado de `33-BASELINE.md`.
</content>
</invoke>
