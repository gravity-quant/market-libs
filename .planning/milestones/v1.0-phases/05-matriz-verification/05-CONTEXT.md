# Phase 5: Matriz Verification - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase ejecuta el **cuarto y último ciclo end-to-end de verificación en vivo** del
monorepo, sobre el target con la **superficie más grande y la única superficie
destructiva** del proyecto: `matriz-client` (Primary API v1.21 / MATBA ROFEX) contra
**remarkets** (sandbox). Es **sync-only** — no existe `aio.py`; el "async" del
paquete es solo la capa WebSocket que queda fuera de scope.

Aplica el mismo loop **driver → finding → fix → mocked regression** establecido en
Phases 2-4, con seis complicaciones específicas de Matriz:

1. **Surface más grande del ciclo**: 19 funciones REST públicas + 11 modelos
   `_SafeModel`. Auth en 2 modos: `X-Auth-Token` (default) + HTTP Basic Auth
   (Risk API §9). Multiple envelope keys: `["segments"]`, `["instruments"]`,
   `["instrument"]`, `["order"]`, `["orders"]`, `["marketData"]`, `["trades"]`,
   `["positions"]`.

2. **Solo superficie destructiva del ciclo (MATZ-06 mock-only)**: `new_order`,
   `replace_order`, `cancel_order` se ejercitan **EXCLUSIVAMENTE por mock** —
   nunca live, ni siquiera en remarkets. Hay que lockear el quirk **GET-as-write**
   verbatim para que no se "corrija" accidentalmente.

3. **Market-hours dependency (MATZ-07)**: `get_market_data` y `get_trades`
   dependen de sesión activa. Esta fase introduce un **guard probe-based via
   staleness de `LA.date`**, sin tabla horaria que mantener.

4. **Doble fix de fase opportunistic in-cycle**:
   - **MATZ-04 envelope fix**: 13 sites de `_get(...)[key]` reemplazados por
     helper `_unwrap(data, key, endpoint)` privado que levanta `PrimaryAPIError`
     tipado en lugar de `KeyError` no mapeado.
   - **`_token` assert fix**: 1 site de `assert _token is not None` en `_request`
     reemplazado por `if _token is None: raise RuntimeError(...)` (concern
     documentado en CONCERNS.md L52-55).

5. **Helper promotion (DRIFT-02 antesala)**: `_diff_safemodel_bidirectional`
   (Phase 4 inline en main_higyrus.py, D-HIGY-4 deferred con condicional
   "si Phase 5 confirma compatibilidad") **se promueve a
   `verification/safemodel_diff.py` + barrel export**, con refactor de
   main_higyrus.py para usar el helper centralizado.

6. **Cierre del ciclo (DRIFT-02)**: Append `## Cycle Closure` a los 4
   `<pkg>-findings.md` existentes + nuevo `CYCLE-REPORT.md` consolidado con
   stats per-package + cross-cycle + open questions (prod-vs-remarkets gap como
   finding EXPECTED terminal) + schemas summary. Validación automática vía
   `verification/cycle_report.py:verify_cycle_closure(pkg)` invocada por el
   driver.

**En alcance:**

- Ejercitar la superficie pública sync (REST) de `matriz-client` contra
  `https://api.remarkets.primary.com.ar`:
  - Auth flow: `login()` explícito up-front + lazy-auth en primer call (MATZ-01)
  - Happy-path sweep read-only de:
    - Segments: `get_segments` (envelope `["segments"]`)
    - Instruments: `get_all_instruments` (envelope `["instruments"]`),
      `get_instruments_details` (envelope `["instruments"]`),
      `get_instrument_detail` (envelope `["instrument"]`),
      `get_instruments_by_cfi` (envelope `["instruments"]`),
      `get_instruments_by_segment` (envelope `["instruments"]`)
    - Market data: `get_market_data` (envelope `["marketData"]`),
      `get_trades` (envelope `["trades"]`)
    - Order reads (account-scoped): `get_active_orders`, `get_filled_orders`,
      `get_all_orders` (envelope `["orders"]`) — requieren `PRIMARY_ACCOUNT`
    - Order reads (ID-scoped, opt-in): `get_order_status`, `get_order_history`,
      `get_order_by_exec_id` (envelope `["order"]`/`["orders"]`) — requieren
      `MATRIZ_SAMPLE_CL_ORD_ID`/`MATRIZ_SAMPLE_PROPRIETARY`/`MATRIZ_SAMPLE_EXEC_ID`
    - Risk API (HTTP Basic Auth): `get_positions` (envelope `["positions"]`),
      `get_detailed_positions` (sin envelope, DetailedPosition es el wrap),
      `get_account_report` (sin envelope, AccountReport es el wrap) —
      requieren `PRIMARY_ACCOUNT`
    - retención del payload crudo en cada caso (MATZ-02)
  - Diff bidireccional de claves wire vs `get_type_hints(Model)` para los 11
    modelos `_SafeModel`, recursivo en nested models (`InstrumentDetail.segment`,
    `Order.instrumentId`, `MarketDataSnapshot.{BI,OF,LA,SE,OI,CL}`,
    `MarketDataSnapshot.LA→MarketDataEntryValue`, etc.). Reusa el helper
    promovido `verification.safemodel_diff` (MATZ-03)
  - Envelope key verification (MATZ-04): para cada envelope key arriba,
    confirmar presencia live. Si falta → finding SHAPE OPEN con candidate de fix
    in-cycle vía `_unwrap`
  - 3 error probes always-on `{"status":"ERROR"}` → `PrimaryAPIError` (MATZ-05):
    (1) bogus symbol en `get_market_data`,
    (2) invalid account en `get_active_orders`,
    (3) malformed CFI code en `get_instruments_by_cfi`
    distinción HTTP 4xx (no mapeado → finding ERROR-MAP OPEN) vs
    `{"status":"ERROR"}` (mapeado → PASS)
  - Probe `field_type_map` bidireccional recursivo (MATZ-03)
  - Probe `schema_snapshot` por endpoint con envelope D-21 + D-25
    no-overwrite-on-drift
  - **Market-hours guard probe-based (MATZ-07)**: assertions de market data solo
    sobre shape/type/presence. Si `LA.date` es más viejo que 2h → emite finding
    `NO-DATA` OPEN, downstream PASS-shape (sin asserts de valor)

- **Fix opportunistic dual MATZ-04 + `_token` assert**:
  - `_unwrap(data, key, endpoint)` privado en `packages/matriz-client/src/matriz_client/client.py`,
    aplicado a los 13 sites de `_get(...)[key]`
  - `if _token is None: raise RuntimeError("token unavailable after _ensure_token")`
    en lugar del `assert _token is not None` en `_request` (línea 157, rama
    no-auth_basic)
  - 13 regression tests mockeados para MATZ-04 (uno por endpoint con envelope)
  - 1 sentinel test para `_token` RuntimeError

- **Mock-only contract para mutaciones (MATZ-06)** — TODOS verbatim, ninguno
  live:
  - 5 tests de `new_order`: baseline LIMIT + 4 con cada optional toggled
    (MARKET sin price, displayQty+iceberg=True, expireDate+GTD,
    cancelPrevious=True)
  - 1 test de `replace_order` con envelope `["order"]` y construcción de params
  - 1 test de `cancel_order` con envelope `["order"]`
  - **1 sentinel test del GET-as-write quirk**:
    `test_new_order_uses_GET_method_per_primary_api_quirk(httpx_mock)` con
    docstring que cita §6.3 de la spec y advierte "never refactor to POST
    without API confirmation"

- **Helper promotion**: `verification/safemodel_diff.py` con la signature ya
  validada en Phase 4 (`_diff_safemodel_bidirectional(payload, model_cls, path)
  -> Iterator[tuple[str, str, str]]`), barrel export en `verification/__init__.py`,
  refactor de `main_higyrus.py` para consumir el helper centralizado en lugar
  de la copia inline

- Driver `main_matriz.py` reescrito de smoke-test mínimo a probes nombrados con
  stdout verbatim (mirror D-IOL-5 / D-HIGY-10), incluyendo el `verify_cycle_closure`
  invocado para los 4 paquetes al final

- Auto-generar / append `.planning/verification/matriz-client-findings.md`
  vía `append_finding(...)` (helper hardened en Phase 2)

- Schema snapshots committeables por endpoint en
  `.planning/verification/schemas/matriz-client/<func>.json` con envelope D-21
  y D-25 no-overwrite-on-drift

- Tests mockeados nuevos en `packages/matriz-client/tests/test_client.py`
  (secciones `# ------ Verified live (Phase 5) ------` y
  `# ------ Regressions ------`), incluyendo:
  - Invariantes de URL exacta + envelope unwrap para los endpoints read-only
  - 13 regression tests del MATZ-04 envelope fix
  - 1 sentinel del `_token` RuntimeError fix
  - 8 tests del mock-only contract MATZ-06 (5 new_order + 1 replace + 1 cancel
    + 1 sentinel GET-quirk)

- **DRIFT-02 cierre del ciclo**:
  - Append `## Cycle Closure` a `<pkg>-findings.md` para los 4 paquetes
    verificados (`ambito-financiero-client`, `iol-client`, `higyrus-client`,
    `matriz-client`)
  - Nuevo `.planning/verification/CYCLE-REPORT.md` consolidado con 4
    dimensiones:
    (1) Stats per-package: findings totales/OPEN/CONFIRMED/FIXED/EXPECTED/NO-FIX
        + regression tests count + schemas committeados
    (2) Cross-cycle: total findings, total regression tests, bugs encontrados
        + fixados, patrones recurrentes (envelope-key indexing, false-pass
        SafeModel, etc.)
    (3) Open questions for downstream milestone (prod-vs-remarkets gap como
        finding EXPECTED terminal + items defer)
    (4) Schemas summary: lista de paths por paquete
  - Gap prod-vs-remarkets registrado como finding EXPECTED terminal en
    `.planning/verification/matriz-client-findings.md` con `class=SHAPE`,
    `status=EXPECTED`, `surface=sync`, `title=prod-vs-remarkets divergence
    acknowledged`, `expected=verification remarkets-only by safety policy`,
    `actual=prod shape unverified` (mirror del patrón EXPECTED de Phase 2
    anti-bot)
  - `verification/cycle_report.py` nuevo con `verify_cycle_closure(pkg) -> bool`
    que parsea `<pkg>-findings.md`, identifica findings CONFIRMED/FIXED, asserta
    que cada uno linkea a un regression test path existente
  - Driver invoca `verify_cycle_closure` para los 4 paquetes y emite
    `PROBE cycle_closure_<pkg>: PASS|FAIL`; FAIL si algún CONFIRMED carece de
    regression test → finding nuevo CYCLE-CLOSURE OPEN

- Suite completa verde: `uv run pytest -q` + `mypy --strict` + `ruff check`
  + `ruff format`

**Fuera de alcance:**

- Verificación async de `matriz-client` — el paquete es sync-only por diseño
  (no existe `aio.py`); su "async" es exclusivamente la capa WebSocket que está
  fuera de scope desde PROJECT.md
- Verificación WebSocket / `ws_client.py` — capa thread-based con background
  daemon thread; PROJECT.md explícitamente fuera de scope para todo el ciclo
- **Mutación live de órdenes (new_order / replace_order / cancel_order)** —
  PROJECT.md / REQUIREMENTS.md OUT OF SCOPE; nunca live ni siquiera en
  remarkets. Solo mock-only (MATZ-06)
- Verificación contra prod (`api.primary.com.ar`) — solo se ejercita contra
  `api.remarkets.primary.com.ar`. El gap prod-vs-sandbox queda registrado como
  finding EXPECTED terminal + nota explicit en CYCLE-REPORT.md
- Disparar 401/403/429/5xx con loops o retries — anti-feature (riesgo de
  lockout en remarkets)
- Probe auth_401 con bad creds — Matriz NO incluye este patrón (a diferencia
  de IOL/HIGY): los login fallidos contra Primary pueden afectar rate-limit
  counters del tenant; PROJECT.md explícitamente lo excluye del ciclo. La
  cobertura de bad-creds → AuthenticationError vive solo en mocked tests
  pre-existentes
- Verificación de la rama HTTP Basic Auth (Risk API) con credenciales
  inválidas en vivo — mismo riesgo de lockout; cobertura mockeada
- Fix opportunistic de bugs descubiertos DURANTE el live run que no sean los
  flagged: MATZ-04 envelope + `_token` assert — se documentan como findings
  OPEN para clasificación humana ex-post (consistencia con Phases 2-4 MVP
  note)
- Refactor del cliente a clase / instancias / deduplicación sync (no hay
  async) — PROJECT.md explícitamente fuera de scope; matriz es sync-only de
  todos modos
- Anonymize de payloads + commit de fixtures crudos anonimizados — Phase 5
  mantiene el patrón Phase 2/3/4: solo schemas committeables (PII-free por
  construcción `schema_of`), no fixtures con valores. `verification.capture()`
  queda disponible para captures/ gitignored. Matriz NO tiene PII (datos de
  trading sin información personal, solo accountId que es ID interno tenant)
- Cambiar la jerarquía de exceptions con nueva subclase `PrimaryShapeError` —
  D-MATZ-09 reusa `PrimaryAPIError` con `status='ERROR'` (sin nuevo
  status_code, mirror del rechazo Phase 4 D-HIGY-8)
- Cobertura de los 3 order reads ID-scoped (`get_order_status`,
  `get_order_history`, `get_order_by_exec_id`) cuando no hay
  `MATRIZ_SAMPLE_CL_ORD_ID`/`PROPRIETARY`/`EXEC_ID` env vars — quedan SKIPPED
  con mensaje claro
- WebSocket subscribe/order entry (`ws_subscribe_market_data`,
  `ws_subscribe_order_reports`, `ws_new_order`, `ws_cancel_order`) — toda la
  capa WS fuera de scope

</domain>

<decisions>
## Implementation Decisions

### Read-sweep samples & resolution flow (Area A)

- **D-MATZ-1:** **Sample symbol resuelto dinámicamente del primer instrument**.
  El probe `probe_resolve_sample` (o similar nombre) llama
  `_resolved_symbol = primary.get_all_instruments()[0].instrumentId.symbol`
  después del happy-path inicial. Override opcional `MATRIZ_SAMPLE_SYMBOL`
  para fijar uno (por si el operador quiere reproducibilidad cross-runs).
  Razón: los símbolos de Matriz son futuros con vencimiento (DLR/JUN26 etc.)
  que rotan; hardcoding requiere mantenimiento. Resolver dinámicamente se
  adapta a lo que remarkets exponga.

- **D-MATZ-2:** **Sample segment_id resuelto dinámicamente del primer segment**.
  Mirror del patrón D-MATZ-1: `_resolved_segment = primary.get_segments()[0].marketSegmentId`.
  Override opcional `MATRIZ_SAMPLE_SEGMENT` no contemplado por ahora (puede
  agregarse si el operador lo pide; YAGNI).

- **D-MATZ-3:** **`PRIMARY_ACCOUNT` obligatoria SOLO para los 6 probes que la
  necesitan, con SKIPPED selectivo si falta** (NO hard-gate del driver entero):
  - 3 Risk API probes: `get_positions`, `get_detailed_positions`,
    `get_account_report`
  - 3 Order reads account-scoped: `get_active_orders`, `get_filled_orders`,
    `get_all_orders`
  Si falta `PRIMARY_ACCOUNT` en env, cada uno de los 6 emite
  `PROBE <name>: SKIPPED (missing PRIMARY_ACCOUNT env var)`. El resto del
  sweep (segments, instruments, market data, trades, login) corre normal.
  Mirror Phase 4 D-HIGY-11 (cuenta resolution semejante).

- **D-MATZ-4:** **Order reads ID-scoped (3 probes) opt-in vía env vars**.
  `MATRIZ_SAMPLE_CL_ORD_ID`, `MATRIZ_SAMPLE_PROPRIETARY`, `MATRIZ_SAMPLE_EXEC_ID`
  como opcionales. Sin ellas, los 3 probes (`get_order_status`,
  `get_order_history`, `get_order_by_exec_id`) emiten SKIPPED
  `(no orders to query — set MATRIZ_SAMPLE_CL_ORD_ID/PROPRIETARY/EXEC_ID to enable)`.
  Razón: los IDs son tenant-specific y requieren orders pre-existentes; no se
  pueden descubrir desde la API sin colocar una orden (anti-feature).

- **D-MATZ-5:** **Market-hours guard probe-based (MATZ-07)**: el probe
  `probe_market_hours_check` (o inline dentro de `probe_get_market_data`)
  inspecciona el `LA.date` del payload. Si `LA.date` (epoch ms) es más viejo
  que **2 horas** respecto a `time.time() * 1000`, emite finding `NO-DATA`
  OPEN `"market-hours: LA.date stale by X hours"` y los downstream probes
  que asertan valor de `LA`/`SE`/`OP`/`HI`/`LO` skippean asserts de valor
  (mantienen asserts de shape). MATZ-07 ya pide "shape/type/presence only,
  never values" → el guard valida que la shape llega siempre; los asserts de
  presencia/tipo no dependen de market open.

- **D-MATZ-6:** **`get_instruments_by_cfi`: 1 CFI baseline (`ESXXXX`) + sanity
  type-only de los 8 restantes** (DBXXXX, OCASPS, OPASPS, FXXXSX, OPAFXS,
  OCAFXS, EMXXXX, DBXXFR). El baseline genera 1 schema snapshot completo en
  `.planning/verification/schemas/matriz-client/get-instruments-by-cfi-ESXXXX.json`.
  Los 8 sanity emiten solo `isinstance(list)` + `len >= 0` + (si len > 0)
  `isinstance(list[0], Instrument)`. Mirror D-IOL-17.

- **D-MATZ-7:** **`get_all_instruments` y `get_instruments_details` ambos
  cubiertos con 2 probes + 2 snapshots distintos**. Tienen modelos diferentes
  (`Instrument` minimal vs `InstrumentDetail` con 18 fields incluido nested
  `Segment`); el diff bidireccional necesita los 2 modelos por separado para
  detectar field-drops en cada uno. Costo aceptable: 2 GETs adicionales,
  2 snapshot files.

- **D-MATZ-8:** **`get_trades` con `date_from=today-7d, date_to=today`**.
  Rango de 7 días calendario maximiza probabilidad de capturar trades en
  remarkets aunque el día corriente esté muerto. Si retorna lista vacía →
  finding `NO-DATA` OPEN con info `"no trades for {_resolved_symbol} in
  last 7 days on remarkets"` y PASS-shape (mirror HIGY-07 empty path).

### MATZ-04 envelope fix (fix de fase, dual con Phase 4 pattern)

- **D-MATZ-9:** **`_unwrap` helper privado en `packages/matriz-client/src/matriz_client/client.py`**.
  Signature:
  ```python
  def _unwrap(data: dict[str, Any], key: str, endpoint: str) -> Any:
      """Return ``data[key]`` or raise ``PrimaryAPIError`` if missing.

      Args:
          data: Decoded JSON response from ``_request``/``_get``.
          key: Envelope key expected to wrap the payload (e.g., ``"order"``).
          endpoint: Path that produced the response, used for error context.

      Raises:
          PrimaryAPIError: If ``key`` is absent from ``data``.
      """
      if key not in data:
          raise PrimaryAPIError(
              status="ERROR",
              description=f"missing envelope key '{key}' in response from {endpoint}",
              message=None,
          )
      return data[key]
  ```
  **Sin nueva subclase `PrimaryShapeError`** (rechazo coherente con D-HIGY-8):
  callers que catchean `PrimaryAPIError` siguen funcionando. La condición
  shape-mismatch se distingue en `description` (string-based, suficiente).
  Sin sentinel numérico (matriz `PrimaryAPIError` no tiene `status_code`
  — usa `status='ERROR'` directo).

- **D-MATZ-10:** **13 sites de `_get(...)[key]` reemplazados por
  `_unwrap(_get(path, ...), key, path)`**. Lista exhaustiva:
  1. `get_segments` — `["segments"]` en `/rest/segment/all`
  2. `get_all_instruments` — `["instruments"]` en `/rest/instruments/all`
  3. `get_instruments_details` — `["instruments"]` en `/rest/instruments/details`
  4. `get_instrument_detail` — `["instrument"]` en `/rest/instruments/detail`
  5. `get_instruments_by_cfi` — `["instruments"]` en `/rest/instruments/byCFICode`
  6. `get_instruments_by_segment` — `["instruments"]` en `/rest/instruments/bySegment`
  7. `new_order` — `["order"]` en `/rest/order/newSingleOrder`
  8. `replace_order` — `["order"]` en `/rest/order/replaceById`
  9. `cancel_order` — `["order"]` en `/rest/order/cancelById`
  10. `get_order_status` — `["order"]` en `/rest/order/id`
  11. `get_order_history` — `["orders"]` en `/rest/order/allById`
  12. `get_active_orders` — `["orders"]` en `/rest/order/actives`
  13. `get_filled_orders` — `["orders"]` en `/rest/order/filleds`
  14. `get_all_orders` — `["orders"]` en `/rest/order/all`
  15. `get_order_by_exec_id` — `["order"]` en `/rest/order/byExecId`
  16. `get_market_data` — `["marketData"]` en `/rest/marketdata/get`
  17. `get_trades` — `["trades"]` en `/rest/data/getTrades`
  18. `get_positions` — `["positions"]` en `/rest/risk/position/getPositions/{account}`
  (NOTA: el conteo real son 18 sites; el conteo "13" inicial era un estimado.
  El planner confirma el conteo final al inspeccionar `client.py`. Sin envelope
  unwrap: `get_detailed_positions` y `get_account_report` retornan el dict
  raíz directamente al model — esos 2 NO se tocan.)

- **D-MATZ-11:** **18 regression tests mockeados para MATZ-04** (uno por
  envelope key wrap, sección `# ------ Regressions ------` en
  `packages/matriz-client/tests/test_client.py`). Por test:
  - `httpx_mock.add_response(json={"some_other_key": [...]})` (sin la
    envelope key esperada)
  - `with pytest.raises(PrimaryAPIError) as exc_info:` la función pública
  - `assert "missing envelope key 'X'" in exc_info.value.description`
  Docstring: `"""Regression: PrimaryAPIError tipado en lugar de KeyError no
  mapeado cuando envelope key falta (finding F-NN)."""`

### `_token` assert fix (fix opportunistic — CONCERNS.md L52-55)

- **D-MATZ-12:** **`assert _token is not None` (line 157) reemplazado por
  `if _token is None: raise RuntimeError(...)`**. Scope mínimo: solo el
  assert en la rama no-auth_basic; la rama `if auth_basic` queda intacta
  (es semánticamente correcto que `_token` sea None ahí — Risk API no usa
  token). 1 línea de cambio:
  ```python
  # antes:
  _ensure_token()
  assert _token is not None
  resp = _session.request(..., headers={"X-Auth-Token": _token})

  # después:
  _ensure_token()
  if _token is None:
      raise RuntimeError(
          "matriz_client.client: _ensure_token() did not populate _token"
      )
  resp = _session.request(..., headers={"X-Auth-Token": _token})
  ```
  Razón: `assert` es stripped por `python -O`; un crash en producción se
  convertiría en `NoneType has no attribute` (peor diagnóstico).

- **D-MATZ-13:** **1 sentinel test del `_token` RuntimeError**:
  `test_request_raises_runtime_error_if_ensure_token_leaves_none(monkeypatch)`.
  Mockea `_ensure_token` con un noop (deja `_token = None`), llama `_request`
  y verifica `pytest.raises(RuntimeError, match="did not populate _token")`.
  Docstring: `"""Regression: defensive guard against _ensure_token returning
  without populating _token (CONCERNS.md L52-55, finding F-NN)."""`.
  Sin docstring ".

### MATZ-06 Mock-only contract para mutaciones (Area B)

- **D-MATZ-14:** **5 tests de `new_order` cubriendo cada rama del param
  building**:
  1. `test_new_order_baseline_limit_day_with_price` — LIMIT, DAY, price set,
     defaults para cancelPrevious/iceberg
  2. `test_new_order_market_without_price` — MARKET sin price (omite
     `price` del query string)
  3. `test_new_order_with_iceberg_and_display_qty` — iceberg=True,
     displayQty=10 (incluye `displayQty` en query)
  4. `test_new_order_with_expire_date_and_gtd` — timeInForce=GTD,
     expireDate="20261231" (incluye `expireDate`)
  5. `test_new_order_with_cancel_previous_true` — cancelPrevious=True
     (verifica `str(True)="True"` en query string)
  Cada test asserta:
  - `httpx_mock.add_response(url="<full URL with query string verbatim>",
    method="GET", json={"order": {"clientId": "C1", "proprietary": "P1"}})`
  - Return value es `NewOrderResponse(clientId="C1", proprietary="P1")`

- **D-MATZ-15:** **1 test de `replace_order`** + **1 test de `cancel_order`**
  cubriendo URL exacta con query string verbatim, envelope unwrap `["order"]`,
  y retorno typed `NewOrderResponse`.

- **D-MATZ-16:** **1 sentinel test del GET-as-write quirk**:
  ```python
  def test_new_order_uses_GET_method_per_primary_api_quirk(httpx_mock):
      """GET-as-write quirk: Primary API mandates GET for order mutations (§6.3).

      Never refactor to POST without explicit API confirmation — this test
      breaks if anyone changes the method.
      """
      httpx_mock.add_response(
          url="https://api.test/rest/order/newSingleOrder?marketId=ROFX&symbol=X&side=BUY&...",
          method="GET",
          json={"order": {"clientId": "C", "proprietary": "P"}},
      )
      matriz_client.new_order("X", "BUY", 1, "ACC", price=100.0)
      [request] = httpx_mock.get_requests()
      assert request.method == "GET", "Primary API §6.3 mandates GET for order submission"
  ```
  Idem 1 sentinel para `replace_order` y `cancel_order` (3 sentinels en total).

- **D-MATZ-17:** **Docstring expand en client.py** para new_order /
  replace_order / cancel_order: agregar advertencia explicit "**WARNING:
  Submission uses HTTP GET per Primary API §6.3 spec — this is intentional,
  not a bug. Never refactor to POST without API confirmation.**" (texto del
  warning a discreción del implementador, el contenido es lo importante).

### Helper promotion: `verification.safemodel_diff` (DRIFT-02 antesala)

- **D-MATZ-18:** **Promover `_diff_safemodel_bidirectional` a
  `verification/safemodel_diff.py`**. La signature ya validada por Phase 4
  D-HIGY-4:
  ```python
  def diff_safemodel_bidirectional(
      payload: Any,
      model_cls: type,
      path: str = "",
  ) -> Iterator[tuple[str, str, str]]:
      """Yields (path, direction, key) tuples.

      direction ∈ {'model-only' (FALSE PASS risk), 'wire-only' (info)}.

      Recursive on nested ``_SafeModel`` fields. For ``list[X]`` with
      ``X`` a ``_SafeModel`` subclass, samples first element of payload.
      """
  ```
  Renombrar de `_diff_safemodel_bidirectional` (privado-inline en
  main_higyrus.py) a `diff_safemodel_bidirectional` (público committeable).

- **D-MATZ-19:** **Barrel export en `verification/__init__.py`**:
  agregar `diff_safemodel_bidirectional` a los exports existentes
  (`append_finding`, `Denylist`, `anonymize`, `capture`, `mutating_allowed`,
  `new_findings`, `redact`, `require_env`, `safe_print`, `schema_of`,
  `write_findings`).

- **D-MATZ-20:** **Refactor de `main_higyrus.py` para consumir el helper
  centralizado**. Reemplazar la copia inline de `_diff_safemodel_bidirectional`
  por `from verification import diff_safemodel_bidirectional`. Tests
  pre-existentes de Phase 4 deben seguir verdes (la signature es idéntica).
  Si la copia inline tiene differences ad-hoc no documentadas en D-HIGY-4,
  documentarlas como findings retroactivos.

- **D-MATZ-21:** **`main_matriz.py` usa el helper desde el barrel** —
  `from verification import diff_safemodel_bidirectional`. Aplicado a los
  11 modelos `_SafeModel`: Segment, Instrument, InstrumentDetail (recursivo
  en Segment + InstrumentId), Order (recursivo en InstrumentId), Trade,
  MarketDataSnapshot (recursivo en MarketDataLevel + MarketDataEntryValue),
  Position, DetailedPosition, AccountReport, NewOrderResponse (cubierto por
  mock-only — pero el helper también puede ejercitarse mockeado).

### MATZ-05 Error-path live (Area C)

- **D-MATZ-22:** **3 error probes always-on con condiciones distintas**:
  1. **bogus symbol en `get_market_data`** — `primary.get_market_data("ZZZZZZ-NOT-A-SYMBOL")`.
     Espera `PrimaryAPIError` con `status="ERROR"`.
  2. **invalid account en `get_active_orders`** — `primary.get_active_orders("INVALID-ACCT-XXXXX")`.
     Espera `PrimaryAPIError` con `status="ERROR"` (no requiere `PRIMARY_ACCOUNT`
     env var — este probe pasa un account inválido a propósito).
  3. **malformed CFI code en `get_instruments_by_cfi`** —
     `primary.get_instruments_by_cfi(cast(CFICode, "INVALID-CFI"))`. Requiere
     `cast()` porque mypy strict rechazaría el literal directo. Espera
     `PrimaryAPIError` con `status="ERROR"`. Si el server retorna HTTP 400 en
     lugar de `{"status":"ERROR"}` → finding `ERROR-MAP` OPEN.
  Always-on (sin opt-in env var) porque son lookups read-only sin auth-flow
  involucrado — diferente de IOL/HIGY `auth_401` que dispara intentos de
  login fallidos (lockout risk real).

- **D-MATZ-23:** **Distinguir HTTP 4xx no mapeado de `{"status":"ERROR"}`
  mapeado**. Cada error probe estructura:
  ```python
  try:
      primary.get_market_data("ZZZZZZ-NOT-A-SYMBOL")
  except PrimaryAPIError as e:
      # PASS: error mapping correcto
      if e.status == "ERROR":
          return ProbeResult("error_bogus_symbol", "PASS",
                             f"PrimaryAPIError as expected: {e.description}")
  except httpx.HTTPStatusError as e:
      # FINDING: bug — error HTTP no mapeado a la jerarquía
      finding_id = append_finding(
          pkg="matriz-client",
          class_="ERROR-MAP",
          surface="sync",
          status="OPEN",
          title="HTTP 4xx not mapped to PrimaryAPIError",
          expected="PrimaryAPIError wrap for any error response",
          actual=f"httpx.HTTPStatusError {e.response.status_code} raw",
          diff="...",
      )
      return ProbeResult("error_bogus_symbol", "FINDING", f"{finding_id} (OPEN)")
  ```
  Sin fix in-cycle del wrapping (defer al downstream milestone si CONFIRMED).

- **D-MATZ-24:** **Posición en la secuencia: después del happy-path sweep
  + field-type-map, antes de schema snapshots**. Razón: si el error probe
  rompe state inesperadamente (raro pero posible: throttling per-IP, error
  rate counter del server), el schema snapshot ya está generado. Mirror
  parcial D-IOL-4 / D-HIGY-10 #18 (ultimo en secuencia) — adaptado porque
  matriz error probes son menos riesgosos que un auth-failed deliberado.

### DRIFT-02 closing report + prod-vs-remarkets gap (Area D)

- **D-MATZ-25:** **Append `## Cycle Closure` a `<pkg>-findings.md` para los
  4 paquetes verificados** (ambito-financiero-client, iol-client,
  higyrus-client, matriz-client). Sección al final del archivo con:
  - **Conteo de findings por status**: OPEN / CONFIRMED / FIXED / EXPECTED /
    NO-FIX
  - **Lista de regression tests linkados a findings FIXED** (formato:
    `F-NN: <test_file>::<test_name>`)
  - **Validación**: para cada finding CONFIRMED/FIXED, asserción de que
    `<test_file>::<test_name>` existe en el suite (verificación automática
    vía D-MATZ-28)
  - **Fecha del cierre** (timestamp del run del Phase 5 driver)

- **D-MATZ-26:** **Nuevo `.planning/verification/CYCLE-REPORT.md` consolidado**
  con 4 dimensiones:

  **(1) Stats per-package** — tabla con columnas: Package | Findings Total |
      OPEN | CONFIRMED | FIXED | EXPECTED | NO-FIX | Regression Tests |
      Schemas Committed
      Filas: ambito-financiero-client, iol-client, higyrus-client,
      matriz-client; total cycle.

  **(2) Cross-cycle**:
      - Total findings emitidos en el ciclo
      - Total regression tests agregados
      - Total bugs encontrados + fixados (CONFIRMED→FIXED, contado)
      - **Patrones recurrentes** (descripción narrativa, ej:
        "envelope-key indexing detected as KeyError unmapped en 3 de 4
        paquetes (IOL ya tenía wrap; HIGY/MATZ se fixaron in-cycle)",
        "False-pass SafeModel: detectado en HIGY (campo `cantidad: float`
        cuando wire emite string), MATZ (TBD del live run)", etc.)

  **(3) Open questions for downstream milestone**:
      - **prod-vs-remarkets gap** (matriz-client): finding EXPECTED terminal
        F-NN (D-MATZ-27) recordado como handoff para milestone futuro
        "verify matriz against prod with appropriate safety harness"
      - Items deferred del ciclo (iteración multi-cuenta de HIGY, refresh_token
        persistente de IOL, etc. — fuera del ciclo pero documentados para
        downstream)

  **(4) Schemas summary**: lista de paths committeados por paquete:
      ```
      ambito-financiero-client (1):
        .planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json
      iol-client (4):
        .planning/verification/schemas/iol-client/get-quote.json
        ...
      higyrus-client (5):
        .planning/verification/schemas/higyrus-client/get-health.json
        ...
      matriz-client (~16):
        .planning/verification/schemas/matriz-client/get-segments.json
        ...
      ```

- **D-MATZ-27:** **Gap prod-vs-remarkets como finding EXPECTED terminal en
  `matriz-client-findings.md`** (ROADMAP SC#4 explícito: "every finding is
  labeled `remarkets` with the prod-vs-sandbox gap recorded as an explicit
  open question"). Append vía `append_finding`:
  ```python
  append_finding(
      pkg="matriz-client",
      fid="F-XX",  # asignado por el helper
      class_="SHAPE",
      surface="sync",
      status="EXPECTED",
      title="prod-vs-remarkets divergence acknowledged",
      expected="verification limited to remarkets sandbox by safety policy "
               "(REQUIREMENTS.md Out of Scope)",
      actual="prod (api.primary.com.ar) shape unverified; sandbox shape "
             "committeed in .planning/verification/schemas/matriz-client/",
      diff="N/A (acknowledged limitation, not detected drift)",
      regression=None,  # EXPECTED no requiere regression
  )
  ```
  Mirror del patrón EXPECTED de Phase 2 anti-bot (terminal, no acción
  downstream necesaria desde matriz-client).

- **D-MATZ-28:** **`verification/cycle_report.py` nuevo con
  `verify_cycle_closure(pkg: str) -> tuple[bool, list[str]]`**:
  ```python
  def verify_cycle_closure(pkg: str) -> tuple[bool, list[str]]:
      """Asserta que todos los findings CONFIRMED/FIXED de un paquete tienen
      regression test path existente.

      Returns:
          (ok, missing_regressions)
          ok = True si todos los CONFIRMED/FIXED linkean a test existente;
               False en caso contrario.
          missing_regressions = lista de fids sin regression test válido.
      """
      findings_file = Path(f".planning/verification/{pkg}-findings.md")
      # parsea findings, filtra status ∈ {CONFIRMED, FIXED}, verifica que
      # cada uno tenga campo `regression:` poblado y que el path tenga forma
      # válida `<test_file>::<test_name>` (sin necesitar test discovery — el
      # parse es estructural, no de pytest)
      ...
  ```
  El driver `main_matriz.py` lo invoca al final del run para los 4 paquetes:
  ```python
  for pkg in ("ambito-financiero-client", "iol-client", "higyrus-client",
              "matriz-client"):
      ok, missing = verify_cycle_closure(pkg)
      status = "PASS" if ok else "FAIL"
      detail = "" if ok else f" — missing regressions: {', '.join(missing)}"
      print(f"PROBE cycle_closure_{pkg.replace('-', '_')}: {status}{detail}")
      if not ok:
          # emite finding CYCLE-CLOSURE OPEN
          append_finding(pkg=pkg, class_="ERROR-MAP", surface="sync",
                         status="OPEN",
                         title=f"cycle closure: {len(missing)} CONFIRMED/FIXED "
                               "without regression test",
                         ...)
  ```
  El test class no está en el FINDING_CLASSES vocabulary de Phase 1
  (`SHAPE/AUTH/ERROR-MAP/PARAM/SYNC-ASYNC-DRIFT/NO-DATA/ANTI-BOT`); usamos
  `ERROR-MAP` como el más cercano a "regression test mapping fallido".
  Discrecional: si el planner ve preferible agregar `CYCLE-CLOSURE` al
  vocabulary, requiere update en `verification/findings.py` (Phase 1 lockeada
  — pero esta clase agregada no rompe lifecycle).

### Driver structure & lifecycle (carry-forward Phases 2-4 + Matriz-specific)

- **D-MATZ-29:** **Secuencia de probes en `main_matriz.py`** (orden ejecución,
  todos con stdout verbatim `PROBE <name>: <status> <detail>` per D-02 Phase 2).
  Conteo aproximado: **~25 probes** (vs 18 Phase 4 / 15 Phase 3 / 7 Phase 2).
  Tabla LITERAL:

  ```
  Sequence:
  1. probe_login_sync — primary.login() (MATZ-01). Si falla → cascade SKIPPED.
  2. probe_get_segments — read + envelope ["segments"]; resuelve
     _resolved_segment = segments[0].marketSegmentId (MATZ-02)
  3. probe_get_all_instruments — read + envelope ["instruments"]; resuelve
     _resolved_symbol = instruments[0].instrumentId.symbol (MATZ-02)
  4. probe_get_instruments_details — read + envelope ["instruments"] (MATZ-02)
  5. probe_get_instrument_detail — _resolved_symbol; envelope ["instrument"]
     (MATZ-02, MATZ-04)
  6. probe_get_instruments_by_cfi_ESXXXX — baseline CFI; envelope
     ["instruments"] (MATZ-02)
  7. probe_get_instruments_by_cfi_sanity — itera los 8 CFI restantes con
     type-only assertions (D-MATZ-6)
  8. probe_get_instruments_by_segment — _resolved_segment; envelope
     ["instruments"] (MATZ-02)
  9. probe_get_market_data — _resolved_symbol; default entries; envelope
     ["marketData"]; aplica market-hours guard D-MATZ-5 (MATZ-02, MATZ-07)
  10. probe_get_trades — _resolved_symbol; rango 7d; envelope ["trades"]
      (MATZ-02)
  11. probe_get_active_orders — _resolved_account si presente; envelope
      ["orders"]; SKIPPED selectivo si falta PRIMARY_ACCOUNT (MATZ-02)
  12. probe_get_filled_orders — idem (MATZ-02)
  13. probe_get_all_orders — idem (MATZ-02)
  14. probe_get_order_status — SKIPPED si falta MATRIZ_SAMPLE_CL_ORD_ID +
      MATRIZ_SAMPLE_PROPRIETARY; envelope ["order"] (MATZ-02)
  15. probe_get_order_history — idem; envelope ["orders"] (MATZ-02)
  16. probe_get_order_by_exec_id — SKIPPED si falta MATRIZ_SAMPLE_EXEC_ID;
      envelope ["order"] (MATZ-02)
  17. probe_get_positions — SKIPPED si falta PRIMARY_ACCOUNT; envelope
      ["positions"]; HTTP Basic Auth (Risk) (MATZ-02)
  18. probe_get_detailed_positions — idem; DetailedPosition (sin envelope
      key, dict raíz) (MATZ-02)
  19. probe_get_account_report — idem; AccountReport (sin envelope key)
      (MATZ-02)
  20. probe_field_type_map — diff bidireccional recursivo sobre los 11 modelos
      _SafeModel; reusa verification.diff_safemodel_bidirectional (MATZ-03)
  21. probe_error_bogus_symbol — get_market_data("ZZZZZZ-..."); espera
      PrimaryAPIError; distinguir HTTP 4xx → finding ERROR-MAP OPEN
      (MATZ-05 #1)
  22. probe_error_invalid_account — get_active_orders("INVALID-..."); idem
      (MATZ-05 #2)
  23. probe_error_malformed_cfi — get_instruments_by_cfi(cast(CFICode,
      "INVALID-CFI")); idem (MATZ-05 #3)
  24. probe_schema_snapshot — generar/comparar los snapshots por endpoint
      (D-MATZ-6 + envelope D-21 + D-25 no-overwrite-on-drift)
  25. probe_cycle_closure — verify_cycle_closure para los 4 paquetes
      (D-MATZ-28); emite finding ERROR-MAP OPEN si falta regression para
      algún CONFIRMED
  ```

- **D-MATZ-30:** **No hay `_async_main` ni `asyncio.run`** — matriz es
  sync-only. Lifecycle más simple que Phases 2-4. El driver es un único
  `main()` síncrono.

- **D-MATZ-31:** **Cascade SKIPPED tras `login()` failure** mirror D-IOL-3 /
  D-HIGY-DISCRETION: flag module-level `_auth_failed: bool = False` set por
  `probe_login_sync`. Cada probe downstream checkea
  `if _auth_failed: return ProbeResult("<name>", "SKIPPED", "auth failed")`.
  Implementación discrecional (early-return, decorator, etc.).

- **D-MATZ-32:** **`safe_print(text, secrets=[PRIMARY_USER, PRIMARY_PASSWORD,
  _token])`**. Lista de secrets se inicializa al cargar el módulo con
  `[PRIMARY_USER, PRIMARY_PASSWORD]` desde env. `_token` se agrega
  dinámicamente tras el primer `login()` (mirror D-IOL-7 / D-HIGY-15). Cubre
  T-3-* de Information Disclosure.

- **D-MATZ-33:** **Env vars del driver** (`.env.example` + driver):
  - `PRIMARY_USER`, `PRIMARY_PASSWORD` — obligatorias (`require_env` gate)
  - `PRIMARY_BASE_URL` — opcional, default
    `https://api.remarkets.primary.com.ar` (ya documentada). **Assert
    hostname remarkets** belt-and-suspenders al inicio del driver (mirror
    HARN-02 spirit) — si el operador setea prod, ABORT con loud message.
  - `PRIMARY_ACCOUNT` — opcional (driver level), gate selectivo para 6
    probes (D-MATZ-3)
  - `MATRIZ_SAMPLE_SYMBOL` — opcional override del `_resolved_symbol`
  - `MATRIZ_SAMPLE_CL_ORD_ID`, `MATRIZ_SAMPLE_PROPRIETARY`,
    `MATRIZ_SAMPLE_EXEC_ID` — opt-in para los 3 order reads ID-scoped

### Verified-live tests + Regressions sections

- **D-MATZ-34:** En `packages/matriz-client/tests/test_client.py`, agregar
  las **dos secciones verbatim** (sin `test_async_client.py` — matriz no
  tiene async):
  - `# ------ Verified live (Phase 5) ------`
  - `# ------ Regressions ------`
  Lockear los invariantes mínimos (mocked, pytest-httpx):
  - MATZ-02: URLs exactas emitidas por cada endpoint del happy path
  - MATZ-04: invariante de envelope unwrap para los 18 endpoints (cubierto
    por las 18 regression tests D-MATZ-11)
  - MATZ-05: invariantes del mapping `{"status":"ERROR"}` → `PrimaryAPIError`
    para los 3 error scenarios (mockeado complementa el live probe)
  - MATZ-06: 8 tests mock-only del contract (5 new_order + 1 replace + 1
    cancel + 3 sentinels GET-quirk = 11 tests en total para mutaciones)
  - `_token` fix: 1 sentinel D-MATZ-13

### Claude's Discretion

Las siguientes decisiones quedan a discreción del implementador, ancladas a
los patrones LOCKEADOS arriba:

- Texto exacto del docstring expand en client.py para new_order /
  replace_order / cancel_order (el contenido del warning a discreción, lo
  importante es citar §6.3 spec y "never refactor without API confirmation").
- Texto exacto del RuntimeError message en `_token` fix.
- Tactic exacta de la cascade SKIPPED tras login failure (flag module-level
  vs decorator vs early-return).
- Formato exacto del path qualifier en `diff_safemodel_bidirectional`
  (e.g., `.snapshot.LA.price` vs `snapshot.LA.price`).
- Cómo el probe `field_type_map` itera los 11 modelos: una pasada por
  endpoint (vinculando payload retenido a su modelo) vs una pasada por
  modelo (necesita un payload-sample por modelo).
- String literal de bogus symbol ("ZZZZZZ-NOT-A-SYMBOL" sugerido), invalid
  account ("INVALID-ACCT-XXXXX" sugerido), malformed CFI ("INVALID-CFI"
  sugerido) — pueden ajustarse mientras sean sintácticamente válidos pero
  semánticamente inválidos.
- Conteo exacto de regression tests de MATZ-04: el draft dice "13 sites"
  pero la enumeración real son 18 envelope-key wraps. El planner confirma
  al inspeccionar `client.py`. La decisión locked es "1 regression test por
  cada `_get(...)[key]` wrap reemplazado", el conteo se ajusta a lo real.
- Si el helper promovido a `verification/safemodel_diff.py` se llama
  `diff_safemodel_bidirectional` (sugerido) o conserva nombre privado
  `_diff_safemodel_bidirectional` con underscore (el export es público;
  preferiblemente sin underscore).
- Si el CFI sanity probe (D-MATZ-6) emite findings por cada CFI con shape
  divergente o solo el `acciones`-baseline tiene snapshot.
- Si el `cycle_closure` probe usa `ERROR-MAP` class (sugerido por proximidad)
  o agrega `CYCLE-CLOSURE` al vocabulary de findings (requiere update mínimo
  en `verification/findings.py` para extender `FINDING_CLASSES`; el planner
  decide en base a YAGNI vs vocabulary cleanliness).
- Si el assert hostname remarkets (D-MATZ-33) usa `assert` o `if/raise` —
  recomendado `if/raise` por consistencia con D-MATZ-12.
- Conteo exacto de schemas committeados: cubre cada endpoint del happy path
  + ID-scoped condicionales (~16-19 snapshots).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements

- `.planning/ROADMAP.md` §"Phase 5: Matriz Verification" — goal, mode (mvp), 5
  success criteria, dependencies (Phase 4)
- `.planning/REQUIREMENTS.md` §"Verificación matriz-client (MATZ)" — MATZ-01..07
  texto completo
- `.planning/REQUIREMENTS.md` §"Detección de drift y cierre (DRIFT)" —
  DRIFT-02 (per-package report, anclado a Phase 5)
- `.planning/REQUIREMENTS.md` §"Out of Scope" — anti-features (loops, retries,
  lockout risk, mutación live de órdenes, prod-vs-sandbox)
- `.planning/REQUIREMENTS.md` §"Convención transversal" — toda regla cross-cycle
  (matriz es sync-only, sin mirror async)
- `.planning/PROJECT.md` §"Key Decisions" — `main_*.py` como vehículo, regresión
  mockeada por fix, excluir WebSocket/async de matriz
- `.planning/PROJECT.md` §"Out of Scope" — WebSocket streaming, refactors
  arquitectónicos

### Phase 1 outputs (LOCKED, base del harness)

- `.planning/phases/01-safety-harness-verification-infrastructure/01-CONTEXT.md`
  — D-01..D-16 del harness (drivers manuales, mockeados-only en CI, marker
  live, ubicación `verification/`, formato findings, lifecycle de status,
  pipeline capture→anonymize→fixture, schema_of, secrets discipline)
- `.planning/verification/FINDINGS-TEMPLATE.md` — plantilla con 7 clases fijas
  (SHAPE/AUTH/ERROR-MAP/PARAM/SYNC-ASYNC-DRIFT/NO-DATA/ANTI-BOT) y ciclo de
  estados (OPEN→CONFIRMED→FIXED + terminales EXPECTED/NO-FIX)

### Phase 2 outputs (LOCKED, lifecycle establecido)

- `.planning/phases/02-mbito-verification/02-CONTEXT.md` — D-01..D-26 del
  lifecycle (driver con probes nombrados, stdout verbatim, write_findings +
  append_finding, schema snapshot envelope D-21 + D-25 no-overwrite,
  secciones Verified-live + Regressions, dual sync+async, safe_print)
- `.planning/phases/02-mbito-verification/02-01-SUMMARY.md` —
  `append_finding(...)` helper hardened
- `.planning/phases/02-mbito-verification/02-REVIEW.md` — code review
  post-mortem; Phase 5 hereda CR-01/CR-02/WR-04 hardening (preservación de
  prosa humana, validación de pkg slug, single-line title invariant)
- `verification/findings.py` — `append_finding`, `FINDING_CLASSES`,
  `STATUS_LIFECYCLE`

### Phase 3 outputs (LOCKED, patrón opt-in 401 + auth-once)

- `.planning/phases/03-iol-verification/03-CONTEXT.md` — D-IOL-1..D-IOL-22
  del patrón opt-in probe destructivo + cascade SKIPPED + `safe_print` con
  secrets dinámicos. Matriz NO replica el `auth_401` opt-in (riesgo de
  lockout más alto que IOL, REQUIREMENTS.md Out of Scope explícito)
- `.planning/phases/03-iol-verification/03-SECURITY.md` — mitigations T-1-* a
  T-5-*; Phase 5 hereda Information Disclosure (`safe_print` + driver sin
  valores en stdout)

### Phase 4 outputs (LOCKED, SafeModel diff bidireccional)

- `.planning/phases/04-higyrus-verification/04-CONTEXT.md` — D-HIGY-1..D-HIGY-18
  del patrón SafeModel diff bidireccional recursivo (D-HIGY-3 nested models,
  D-HIGY-4 signature `_diff_safemodel_bidirectional`, D-HIGY-5 sub-clasificación
  de findings por dirección model-only/wire-only). **D-HIGY-4 explícitamente
  difiere la promoción del helper a `verification/safemodel_diff.py` con
  condicional "si Phase 5/Matriz confirma compatibilidad" — Phase 5 confirma
  y promueve (D-MATZ-18).**
- `.planning/phases/04-higyrus-verification/04-CONTEXT.md` §Deferred Ideas —
  ítem "Promover `_diff_safemodel_bidirectional` a `verification/safemodel_diff.py`"
  triggered en Phase 5
- `.planning/phases/04-higyrus-verification/04-01-SUMMARY.md` — patrón fix
  HIGY-04 de fase (10 sites `assert isinstance` → typed exception); Phase 5
  replica el patrón con MATZ-04 (18 sites `_get(...)[key]` → `_unwrap` +
  typed PrimaryAPIError)
- `.planning/phases/04-higyrus-verification/04-02-SUMMARY.md` — driver
  main_higyrus.py con 18 probes nombrados, bidirectional diff helper inline,
  schema snapshot pattern. Phase 5 escala a ~25 probes con el helper
  promovido. **Refactor in-cycle de main_higyrus.py (D-MATZ-20) reemplaza
  la copia inline.**
- `.planning/phases/04-higyrus-verification/04-04-PLAN.md` (Wave 2.5
  opportunistic) — patrón "in-cycle fix de bug descubierto durante live run"
  validado; Phase 5 ya planea 2 fixes opportunistic (MATZ-04 envelope + `_token`
  assert) up-front en el plan
- `.planning/phases/04-higyrus-verification/04-SECURITY.md` (retroactive
  STRIDE, 24/24 closed) — patrón replicado en Phase 5

### Codebase maps

- `.planning/codebase/INTEGRATIONS.md` §"Derivatives Exchange (MATBA ROFEX /
  Primary API)" — auth dual (X-Auth-Token + HTTP Basic Risk API), 24h TTL
  refreshed 23h, default base `https://api.remarkets.primary.com.ar`,
  enumeración completa de los 23 REST endpoints, WS auth shared token
- `.planning/codebase/TESTING.md` — pytest config (`asyncio_mode = "auto"`,
  `--strict-markers`), pytest-httpx pattern (`url=` con full query string),
  autouse fixtures por paquete, convención `Regression: ... (issue #NNN)` →
  `(finding F-NN)` per D-07 Phase 2
- `.planning/codebase/CONVENTIONS.md` — naming, ruff line-length=100,
  double quotes, `from __future__ import annotations` obligatorio, mypy
  strict
- `.planning/codebase/CONCERNS.md` L52-55 — `assert _token is not None` en
  matriz-client client.py L157 flagged como issue (`-O` strips asserts);
  fix in-cycle Phase 5 vía D-MATZ-12
- `.planning/codebase/CONCERNS.md` §"Fragile Areas" — `ws_client.py` accede
  `_rest._base_url`/`_rest._token` (Phase 5 NO toca esa interfaz; WS out of
  scope, pero el rename del private state debería evitar romper WS)
- `.planning/codebase/ARCHITECTURE.md` — estado singleton, **matriz NO tiene
  aio.py** (sync-only por diseño), jerarquía de exceptions, anti-pattern
  "Importing aio module in sync context" no aplica a matriz

### Implementación actual del cliente (target a verificar)

- `packages/matriz-client/src/matriz_client/client.py` — superficie sync REST;
  416 líneas:
  - `login()` (L98-123) — POST /auth/getToken con headers X-Username/X-Password;
    token en X-Auth-Token response header; 24h TTL refresh 23h
  - `_ensure_token()` (L91-95) — re-login si token o time.time() - _token_ts
    >= _TOKEN_TTL
  - `_request()` (L131-173) — auth dual: X-Auth-Token (default) o HTTP Basic
    via `auth_basic`. **L157 `assert _token is not None`** TARGET del fix
    D-MATZ-12. **L167-172** `if data.get("status") == "ERROR": raise
    PrimaryAPIError(...)` — el mecanismo que MATZ-05 ejercita
  - `_get(path, **params)` (L176-179) — wrapper con `drop_none` inline
  - **18 endpoints públicos**: 1 segments, 5 instruments, 9 orders, 2 market
    data, 3 risk (HTTP Basic). Cada uno hace `_get(...)[key]` o
    `_request(..., auth_basic=)[key]` con envelope key — TARGETS del fix
    MATZ-04 D-MATZ-10
- `packages/matriz-client/src/matriz_client/aio.py` — **NO EXISTE**
  (matriz es sync-only). Phase 5 NO crea este archivo
- `packages/matriz-client/src/matriz_client/models.py` — 11 modelos
  `_SafeModel` (395 líneas):
  - Identifiers: `InstrumentId`, `AccountId`
  - Segments/Instruments: `Segment`, `Instrument`, `InstrumentDetail` (incluye
    nested `Segment`)
  - Orders: `NewOrderResponse`, `Order` (nested `InstrumentId`), `OrderReport`
  - Market data: `MarketDataLevel`, `MarketDataEntryValue`,
    `MarketDataSnapshot` (nested `MarketDataLevel[]` + `MarketDataEntryValue`),
    `Trade`
  - Risk: `Position`, `DetailedPosition`, `AccountReport`
  - WS frames: `MarketDataFrame`, `ExecutionReportFrame`, `UnknownFrame` (WS
    out of scope, NO se diffea)
  - Base `_SafeModel.from_api` (L106-111) tolerante; usa `get_type_hints` →
    TARGET del diff bidireccional D-MATZ-18
- `packages/matriz-client/src/matriz_client/types.py` — Literal type aliases:
  `Side`, `OrderType`, `TimeInForce`, `MarketId`, `SegmentId`, `CFICode`,
  `MarketDataEntry`, `OrderStatus`, `Currency`. **9 CFI codes** (D-MATZ-6
  sanity sweep)
- `packages/matriz-client/src/matriz_client/exceptions.py` — jerarquía:
  `MatrizClientError` → `PrimaryAPIError(status, description, message)` →
  `AuthenticationError`. **D-MATZ-9** rechaza nueva subclase
  `PrimaryShapeError`; reusa `PrimaryAPIError(status='ERROR', ...)` para
  shape mismatches
- `packages/matriz-client/src/matriz_client/__init__.py` — `__all__` público:
  19 REST functions + 11 modelos + 9 Literals + 1 base exception + 7 WS
  functions (WS NO se ejercita)
- `packages/matriz-client/src/matriz_client/ws_client.py` — **OUT OF SCOPE**;
  Phase 5 NO toca este módulo. Si el rename de `_base_url`/`_token` afecta
  `ws_client.py:L65,L140,L150`, regenerar el assert apropiado o documentar
  como finding (no fix in-cycle; defer a milestone WS)
- `packages/matriz-client/tests/conftest.py` — autouse fixture
  `_configure_sync`; precarga `_token = "test-token"` y `_token_ts = reciente`
  para evitar disparar login en endpoints autenticados. Phase 5 los Verified-live
  + Regressions tests heredan el setup. Para el sentinel `_token` fix
  D-MATZ-13, el test monkeypatch sobre el state precargado
- `packages/matriz-client/tests/test_client.py` — tests mockeados
  pre-existentes; se le hace append de las secciones Verified-live + Regressions
- `packages/matriz-client/tests/test_models.py`,
  `packages/matriz-client/tests/test_exceptions.py`,
  `packages/matriz-client/tests/test_types.py`,
  `packages/matriz-client/tests/test_ws_client.py` — Phase 5 NO toca
- `packages/matriz-client/.env.example` — `PRIMARY_USER`, `PRIMARY_PASSWORD`,
  `PRIMARY_BASE_URL` requeridas. Phase 5 agrega como opcionales:
  `PRIMARY_ACCOUNT`, `MATRIZ_SAMPLE_SYMBOL`, `MATRIZ_SAMPLE_CL_ORD_ID`,
  `MATRIZ_SAMPLE_PROPRIETARY`, `MATRIZ_SAMPLE_EXEC_ID`

### Driver actual + harness ya construido

- `main_matriz.py` — driver actual (smoke-test mínimo, solo `get_segments` +
  `get_all_instruments`); se reescribe según D-MATZ-29 con los ~25 probes
- `verification/findings.py` — `append_finding(...)` hardened (CR-01/CR-02/
  WR-04 post-Phase-2); matriz driver lo usa directamente
- `verification/__init__.py` — barrel: `append_finding`, `Denylist`,
  `anonymize`, `capture`, `mutating_allowed`, `new_findings`, `redact`,
  `require_env`, `safe_print`, `schema_of`, `write_findings`. **Phase 5
  agrega: `diff_safemodel_bidirectional` (D-MATZ-19)**
- `verification/schema.py` — `schema_of(payload)`; PII-free por construcción.
  Phase 5 lo usa para ~16-19 snapshots
- `verification/redaction.py` — `redact(value)`, `safe_print(text, secrets=[...])`
  (D-MATZ-32)
- `verification/env_gate.py` — `require_env(pkg, [vars])`: skip-and-continue si
  faltan PRIMARY_USER / PRIMARY_PASSWORD (HARN-01)
- `verification/mutation_gate.py` — `mutating_allowed()` ya respeta hostname
  remarkets check. Phase 5 NO ejercita mutation gate live (mock-only contract
  MATZ-06), pero el helper queda disponible para belt-and-suspenders en el
  driver (D-MATZ-33 hostname assert)
- `verification/capture.py` — `capture(pkg, endpoint, payload)` para
  `captures/` gitignored (disponible para inspección manual; matriz NO
  commitea fixtures crudos)
- `verification/anonymize.py` — `anonymize(payload, Denylist)` disponible
  pero **no usado en Phase 5** (matriz no tiene PII como accounts/CBU; lo
  más sensible es `accountId` que es ID interno tenant, ya cubierto por
  schema-only commit policy)
- `conftest.py` (root) — `--live` flag, marker `live` registrado, deselect
  default; `sys.path` con repo root para `verification/` importable
- **Phase 5 agrega**: `verification/safemodel_diff.py` (D-MATZ-18),
  `verification/cycle_report.py` (D-MATZ-28)

### Phase 4 main_higyrus.py (TARGET del refactor in-cycle)

- `main_higyrus.py` — contiene la copia inline de
  `_diff_safemodel_bidirectional`. **D-MATZ-20 mandato del refactor**:
  reemplazar por `from verification import diff_safemodel_bidirectional`.
  Tests de Phase 4 (`packages/higyrus-client/tests/`) deben seguir verdes
  post-refactor

### Verification artifacts existentes (TARGETS del cierre DRIFT-02)

- `.planning/verification/ambito-financiero-client-findings.md` — Phase 2
  findings file (target del append `## Cycle Closure` D-MATZ-25)
- `.planning/verification/iol-client-findings.md` — Phase 3
- `.planning/verification/higyrus-client-findings.md` — Phase 4
- `.planning/verification/matriz-client-findings.md` — Phase 5 lo crea
  + append cycle closure + finding EXPECTED prod-vs-remarkets D-MATZ-27
- `.planning/verification/schemas/ambito-financiero-client/` (1 archivo)
- `.planning/verification/schemas/iol-client/` (4 archivos)
- `.planning/verification/schemas/higyrus-client/` (5 archivos)
- `.planning/verification/schemas/matriz-client/` (~16-19 archivos nuevos)
- **Phase 5 crea**: `.planning/verification/CYCLE-REPORT.md` (D-MATZ-26)

### STATE.md blockers (TARGETS del cierre)

- `.planning/STATE.md` §"Blockers/Concerns" "[Phase 5]: Matriz prod-vs-remarkets
  shape gap is unresolved; verification is remarkets-only and the gap must be
  recorded as an open question for a future milestone" — registrado como
  finding EXPECTED terminal D-MATZ-27 + nota en CYCLE-REPORT.md

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`verification.findings.append_finding`** — helper DRY committeado y
  hardened en Phase 2. Matriz lo usa con `pkg="matriz-client"`; idempotente
  por `fid`, preserva prosa humana en status promovidos, valida class/status/
  title/pkg slug. **El append `## Cycle Closure` D-MATZ-25 NO usa este helper
  — es una sección agregada al archivo directamente, no un finding.**
- **`verification.findings.write_findings`** — esqueleto del findings file;
  no-op si existe.
- **`verification.schema.schema_of`** — único primitivo para schema snapshots
  (~16-19 archivos). PII-free por construcción.
- **`verification.redaction.safe_print`** — con `secrets=[PRIMARY_USER,
  PRIMARY_PASSWORD, _token]` (D-MATZ-32). El regex `_BEARER` interno cubre
  tokens reflejados aun sin secrets enumerados.
- **`verification.env_gate.require_env`** — el driver llama
  `require_env("matriz-client", ["PRIMARY_USER", "PRIMARY_PASSWORD"])` al
  inicio; si faltan, imprime `SKIPPED matriz-client: missing PRIMARY_USER,
  PRIMARY_PASSWORD` y exit 0.
- **`verification.mutation_gate.mutating_allowed`** — ya existe y respeta
  hostname remarkets check. Phase 5 lo invoca como belt-and-suspenders
  (D-MATZ-33) para asegurarse de que el base URL no apunta a prod aun si
  `mutating_allowed()` lo permite.
- **`verification.capture.capture`** — disponible para staging gitignored;
  Phase 5 NO commitea fixtures crudos.
- **`_diff_safemodel_bidirectional` (inline en `main_higyrus.py`)** —
  signature ya validada en Phase 4. **TARGET del helper promotion D-MATZ-18:
  se mueve a `verification/safemodel_diff.py`, se exporta del barrel
  (D-MATZ-19), y `main_higyrus.py` se refactoriza para consumirlo (D-MATZ-20).**
- **`SafeModel.from_api` + `get_type_hints`** — la fuente de truth de qué
  espera el cliente para los 11 modelos matriz. El helper promovido lo
  ejercita igual que Phase 4 sobre los 4 modelos higyrus.
- **pytest-httpx `httpx_mock.add_response(url=..., method=...)`** — patrón
  estándar. Los nuevos Verified-live + Regressions tests usan exactamente el
  mismo patrón con URL full incluyendo query string para los endpoints
  matriz (que tienen multiple optional params).
- **Autouse fixture `_configure_sync`** en
  `packages/matriz-client/tests/conftest.py` — los Verified-live tests
  heredan el setup sin modificación. Para el sentinel `_token` fix
  D-MATZ-13, el test monkeypatchea sobre el state precargado.

### Established Patterns

- **Estado singleton a nivel de módulo** (`_base_url`, `_user`, `_password`,
  `_token`, `_token_ts`, `_session`) en `client.py`. Phase 5 NO agrega state
  nuevo al cliente — el fix MATZ-04 es helper privado, el fix `_token` es
  cambio de assert por raise.
- **Single surface sync** — matriz NO tiene `aio.py`. Los fixes MATZ-04 y
  `_token` aplican a una sola superficie (sin mirror async). **Nota
  importante**: la convención del proyecto "dual sync/async" NO aplica acá
  porque no hay async. Los regression tests viven solo en `test_client.py`.
- **`configure()` resetea estado cached** — patrón obligatorio. Phase 5 NO
  toca `configure()`; los tests existentes lo siguen ejercitando.
- **Tests deterministas con `base_url="https://api.test"`** vía autouse
  fixture — los nuevos tests lo respetan.
- **`from __future__ import annotations`** al tope de todo módulo nuevo
  (CONVENTIONS.md). `main_matriz.py` reescrito + `verification/safemodel_diff.py`
  + `verification/cycle_report.py` lo respetan.
- **`ruff` line-length=100, double quotes, 4 espacios; `mypy --strict`** —
  todo código nuevo debe pasar antes de commit.
- **HTTP Basic Auth en Risk API** — `_request(method, path, auth_basic=...)`
  con `httpx.BasicAuth(user, password)`. Phase 5 lo ejercita en
  `probe_get_positions`/`probe_get_detailed_positions`/
  `probe_get_account_report` (D-MATZ-29 #17-19). El probe respeta el
  HTTP Basic path en lugar de X-Auth-Token.
- **`PrimaryAPIError` con `status='ERROR'` para shape mismatch** — D-MATZ-9
  reusa la misma exception (sin subclase nueva). Callers que catchean
  `PrimaryAPIError` siguen funcionando; los que necesitan distinguir
  shape-mismatch vs application-error checkean
  `e.description.startswith("missing envelope key")` (string-based, igual
  que matriz ya distingue HTTP error de application error).

### Integration Points

- **`main_matriz.py`** — punto de entrada vivo de Phase 5; se reescribe
  (no archivo nuevo). Lifecycle análogo a Phases 2-3-4 pero sin
  `asyncio.run` (matriz es sync-only).
- **`main_higyrus.py`** — refactor in-cycle D-MATZ-20: reemplaza la copia
  inline de `_diff_safemodel_bidirectional` por
  `from verification import diff_safemodel_bidirectional`. Tests Phase 4
  siguen verdes.
- **`packages/matriz-client/src/matriz_client/client.py`** — recibe los
  fixes:
  - MATZ-04 (`_unwrap` helper + 18 envelope wraps reemplazados)
  - `_token` assert (1 línea L157)
  - Docstring expand new_order/replace_order/cancel_order (warning
    GET-as-write)
  Sin mirror async (matriz es sync-only).
- **`packages/matriz-client/src/matriz_client/exceptions.py`** — Phase 5 NO
  toca (rechazo de PrimaryShapeError D-MATZ-9). Posible micro-edit del
  docstring de `PrimaryAPIError.description` para documentar la convención
  "missing envelope key 'X'" como string-based marker (discrecional).
- **`packages/matriz-client/tests/test_client.py`** — append de las
  secciones `# ------ Verified live (Phase 5) ------` y
  `# ------ Regressions ------` con:
  - Invariantes URL+envelope+models para los 18 endpoints
  - 18 regression tests del envelope fix MATZ-04
  - 1 sentinel del `_token` RuntimeError
  - 8 tests del mock-only contract MATZ-06 (5 new_order + 1 replace + 1
    cancel + 3 sentinel GET-quirk — total 11)
- **`packages/matriz-client/.env.example`** — append de 5 env vars opcionales
  documentadas: `PRIMARY_ACCOUNT`, `MATRIZ_SAMPLE_SYMBOL`,
  `MATRIZ_SAMPLE_CL_ORD_ID`, `MATRIZ_SAMPLE_PROPRIETARY`,
  `MATRIZ_SAMPLE_EXEC_ID`
- **`.planning/verification/matriz-client-findings.md`** — generado por driver;
  D-MATZ-27 append del finding EXPECTED prod-vs-remarkets
- **`.planning/verification/schemas/matriz-client/`** — ~16-19 snapshot files
  committeables (1 por endpoint del happy path, sin contar las 3 ID-scoped
  condicionales)
- **`.planning/verification/{ambito-financiero,iol,higyrus}-client-findings.md`**
  — append `## Cycle Closure` D-MATZ-25 (modificación de archivos
  pre-existentes — verificar que `append_finding` NO los pisa, el append es
  agregar sección al final)
- **`.planning/verification/CYCLE-REPORT.md`** — archivo nuevo D-MATZ-26
- **`verification/safemodel_diff.py`** — archivo nuevo D-MATZ-18
- **`verification/cycle_report.py`** — archivo nuevo D-MATZ-28
- **`verification/__init__.py`** — barrel update D-MATZ-19 (agregar
  `diff_safemodel_bidirectional` y `verify_cycle_closure` a los exports)

</code_context>

<specifics>
## Specific Ideas

- **~25 probes en orden D-MATZ-29** — copiar la tabla literal arriba al
  planner. Conteo exacto depende de cuántos ID-scoped corren (3 opt-in env
  vars) y cuántos Risk API (PRIMARY_ACCOUNT-gated).
- **`_resolved_symbol` y `_resolved_segment` resolution flow** — set en los
  probes 2 (segments) y 3 (instruments). Cada probe downstream que los usa
  checkea no-None al inicio.
- **18 sites de envelope wrap** (D-MATZ-10) — copiar la lista enumerada al
  planner para la implementación del refactor.
- **5 new_order tests + 1 replace + 1 cancel + 3 sentinel GET = 11 tests
  mutaciones mockeadas** (D-MATZ-14, D-MATZ-15, D-MATZ-16).
- **3 error probes always-on con strings literales** — `"ZZZZZZ-NOT-A-SYMBOL"`,
  `"INVALID-ACCT-XXXXX"`, `cast(CFICode, "INVALID-CFI")` (todos discrecionales
  mientras sean sintácticamente válidos).
- **Threshold de staleness LA.date: 2 horas** (D-MATZ-5) — discrecional pero
  documentado.
- **`PrimaryAPIError(status='ERROR', description='missing envelope key X in
  Y')`** — shape mismatch usa este patrón string-based. Mock-only tests
  asertan substring `"missing envelope key"`.
- **Sentinel GET-quirk test pattern** (D-MATZ-16, ejemplo) —
  ```python
  def test_new_order_uses_GET_method_per_primary_api_quirk(httpx_mock):
      """GET-as-write quirk: Primary API mandates GET (§6.3)."""
      httpx_mock.add_response(url="...", method="GET",
                              json={"order": {"clientId": "C", "proprietary": "P"}})
      matriz_client.new_order("X", "BUY", 1, "ACC", price=100.0)
      [request] = httpx_mock.get_requests()
      assert request.method == "GET", "§6.3 mandates GET for order submission"
  ```
- **`verify_cycle_closure` invocation pattern** (D-MATZ-28) —
  ```python
  for pkg in ("ambito-financiero-client", "iol-client", "higyrus-client",
              "matriz-client"):
      ok, missing = verify_cycle_closure(pkg)
      status = "PASS" if ok else "FAIL"
      print(f"PROBE cycle_closure_{pkg.replace('-', '_')}: {status}")
  ```
- **Verbatim status strings (heredados de Phase 2 D-02)**:
  - `PROBE <name>: PASS [<detail>]`
  - `PROBE <name>: FAIL [<detail>]`
  - `PROBE <name>: SKIPPED (<reason>)`
  - `PROBE <name>: FINDING <fid>[, <fid>...] (<status>)`
- **Summary final** (heredado): `SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N`
- **Belt-and-suspenders hostname assert** (D-MATZ-33) —
  ```python
  if "remarkets" not in primary.client._base_url:
      print("ABORT: PRIMARY_BASE_URL is not a remarkets sandbox URL — "
            "Phase 5 verification is remarkets-only by safety policy")
      sys.exit(1)
  ```
  Aun si el operador setea prod por error, el driver aborta antes de tocar
  cualquier endpoint. Complementa el `mutating_allowed()` check existente.

</specifics>

<deferred>
## Deferred Ideas

- **Verificación live de Matriz contra prod (`api.primary.com.ar`)** —
  registrado como finding EXPECTED terminal D-MATZ-27. Requiere harness de
  safety específico para prod (gates más estrictos, read-only-only policy,
  rate-limiting awareness). Milestone futuro.
- **Probe `auth_401` con bad creds en Matriz** — NO se implementa (a
  diferencia de IOL/HIGY Phase 3/4). Razón: REQUIREMENTS.md Out of Scope
  explícito ("Disparar 401/403/429/5xx en vivo: riesgo de rate-limit/lockout
  de cuentas reales — anti-feature"). Mock-only cobertura ya existe en tests
  pre-existentes; live opt-in no se introduce.
- **Probe HTTP Basic Auth con bad creds en Risk API** — mismo razonamiento;
  mock-only.
- **Verificación live de WebSocket (`ws_client.py`)** — toda la capa WS
  fuera de scope para todo el ciclo de verificación (PROJECT.md). Requiere
  un milestone propio.
- **Verificación async de `matriz-client`** — `aio.py` NO existe por diseño
  (sync-only). Si en un milestone futuro se agrega `aio.py`, requiere su
  propio ciclo de verificación (Phase X separada).
- **Fix del wrapping HTTP 4xx → `PrimaryAPIError`** (CONCERN potencial de
  D-MATZ-23) — si el live run confirma que HTTP 4xx no está mapeado, queda
  como finding OPEN para el milestone siguiente. Phase 5 ya carga 2 fixes
  opportunistic (MATZ-04 envelope + `_token` assert); agregar un tercero
  expande scope.
- **Iteración multi-account / multi-symbol en los probes** — Phase 5 usa
  samples fijos (1 account, 1 symbol). Sweep paramétrico cross-account
  queda para un cycle futuro.
- **Persistencia del token Matriz a disco entre invocaciones** — el TTL
  es 24h; cada `python main_matriz.py` re-loguea. Persistir el token
  reduciría intentos de login pero introduce concerns de seguridad
  (storage encryption). Fuera de scope.
- **Test de auth-once discipline live** — los tests precargan `_token`;
  un test que ejercita "una sola llamada a login() por N requests
  autenticados" queda discrecional pero no load-bearing.
- **Plausibility bounds en `LA.price` / `OF[0].price` / `BI[0].price`** —
  Phase 5 valida shape/type/presence únicamente (MATZ-07). Range checks
  sobre values de market data quedan deferred (sería un cycle futuro con
  guards de horario más sofisticados).
- **Refactor de `_request` a `_request_token()` + `_request_basic()`** —
  refactor más grande del cliente. PROJECT.md fuera de scope para todo el
  ciclo.
- **Promote new `PrimaryShapeError(PrimaryAPIError)` subclass** — D-MATZ-9
  rechaza por consistencia con HIGY-04 (sentinel string-based). Si futuros
  ciclos detectan que callers necesitan distinguir programáticamente
  shape-mismatch vs application-error, promover a subclase (no romping
  binary compatibility).
- **Verificación de `get_instruments_by_cfi` con cada uno de los 9 CFI codes
  como snapshot independiente** — D-MATZ-6 solo committea 1 baseline +
  sanity-only de 8. Snapshot per-CFI quedaría deferred.
- **Verificación de los 6 InstrumentType de IOL en Phase 3 (deferred ya en
  Phase 3 deferred ideas)** — no afecta Phase 5.
- **Anti-bot probe en matriz** — matriz NO usa UA-filtering anti-bot (a
  diferencia de Ámbito). Si en el futuro Primary introduce UA checks, agregar
  como Phase X.
- **Throttling / rate-limit-aware retries en `_ensure_token`** — fuera de
  scope (anti-feature: sin retry loops, sin sleeps).

</deferred>

---

*Phase: 05-matriz-verification*
*Context gathered: 2026-06-09*
