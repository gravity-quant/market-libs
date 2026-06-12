# Phase 4: Higyrus Verification - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase ejecuta el **tercer ciclo end-to-end de verificación en vivo** del monorepo,
sobre el target con la **trampa de FALSE PASS por SafeModel**: `higyrus-client` usa
modelos `@dataclass(frozen=True)` con `from_api` tolerante que substituye defaults
tipados (`""`, `0`, `0.0`, `[]`) por cualquier clave ausente del payload. Un test
mockeado siempre pasa aunque el wire haya cambiado silenciosamente.

Aplica el mismo loop **driver → finding → fix → mocked regression** establecido en
Phase 2 (Ámbito) y Phase 3 (IOL), con tres complicaciones nuevas: (1) **diff
bidireccional explícito** entre claves del payload crudo y `get_type_hints` del
modelo (HIGY-03), recursivo en nested models, para detectar el field-drop silencioso;
(2) **PII real en los payloads** (cuentas, titulares, CBU, domicilios,
personasRelacionadas) — primer ciclo de verificación con datos personales reales;
(3) **fix dual sync+async in-cycle** de los 10 sites de `assert isinstance(raw, list/dict)`
en `client.py` + `aio.py` (HIGY-04), reemplazándolos por `HigyrusAPIError` tipado
con `status_code=0` sentinel.

**En alcance:**

- Ejercitar la superficie pública sync+async de `higyrus-client` contra Higyrus en vivo:
  - Auth flow: `login()` explícito up-front + lazy-auth en primer call (HIGY-01)
  - Happy-path sweep de los 5 endpoints públicos: `get_health`, `get_listado_cuentas`,
    `get_movimientos`, `get_posicion_valuada`, `get_posiciones`, con retención del
    payload crudo (HIGY-02)
  - Diff bidireccional recursivo de claves wire vs `get_type_hints(Model)` para los
    4 endpoints con modelos: `Cuenta`, `Movimiento`, `Posicion`, `PosicionValuada`
    (incluyendo nested `DisposicionesGenerales`, `Domicilio[]`, `PersonaRelacionada[]`,
    `MedioComunicacion[]`, `CuentaBancaria[]`, `Administrador→{Agente,Operador,Sucursal}`,
    `Parking[]`) — emisión de finding `SHAPE OPEN` por cada discrepancia, ambas
    direcciones (HIGY-03)
  - Verificación del error envelope `"errors"` (HIGY-05) via probe always-on con
    `id_cuenta` inválido en `get_movimientos`
  - Empty/204 path: `get_listado_cuentas`/`get_movimientos`/`get_posiciones` que
    retornan `[]` y NO `None` ni crash (HIGY-07)
  - Paridad sync↔async por endpoint estructural (HIGY-06), incluyendo verificación
    in-vivo de la deviation conocida del `drop_none` en async `_request`
  - Probe 401 con bad credentials (HIGY-AUTH) — opt-in via `VERIFY_HIGYRUS_BAD_CREDS=1`,
    último en la secuencia
- **Implementar fix dual de `assert isinstance` → `HigyrusAPIError(0, [...])`** en
  los 5 endpoints sync (`client.py`) y los 5 async (`aio.py`) con 10 regression tests
  mockeados — fix DE FASE, no opportunistic (HIGY-04)
- Driver `main_higyrus.py` reescrito de smoke-test mínimo a probes nombrados
  con stdout verbatim (mirror D-IOL-5)
- Auto-generar `.planning/verification/higyrus-client-findings.md` y poblarlo vía
  `append_finding(...)` (helper DRY de Phase 2 ya hardened)
- Schema snapshots committeables por endpoint en
  `.planning/verification/schemas/higyrus-client/<func>.json` con envelope D-21 y
  no-overwrite-on-drift D-25 — 5 snapshots (uno por endpoint)
- Tests mockeados nuevos en `test_client.py` + `test_async_client.py` (secciones
  `# ------ Verified live (Phase 4) ------` y `# ------ Regressions ------`),
  incluyendo los 10 regression tests del fix HIGY-04
- Suite completa verde: `uv run pytest -q` + mypy strict + ruff check + format

**Fuera de alcance:**

- Verificación en vivo de Matriz — Phase 5
- Re-tocar harness `verification/*` o `conftest.py` — Phase 1 lockeada; sólo se
  AGREGAN call sites a `append_finding`, no se modifica el helper
- Tests `@pytest.mark.live` propios de Higyrus — el marker existe (Phase 1) pero
  esta fase sigue el patrón Phase 2/3: driver-only para live, mocked-only en pytest
- Fix opportunistic de bugs descubiertos DURANTE el live run que no sean los 10
  sites de `assert isinstance` explícitos — se documentan como findings OPEN para
  clasificación humana ex-post (nota MVP del Phase 2 context honorada)
- Refactor del cliente a clase / instancias / deduplicación sync-async — PROJECT.md
  explícitamente fuera de scope para todo el ciclo de verificación
- Anonymize de payloads + commit de fixtures crudos anonimizados — Phase 4 mantiene
  el patrón Phase 2/3: solo schemas committeables (PII-free por construcción), no
  fixtures con valores. `verification.capture()` queda disponible para captures/
  gitignored
- Disparar 401/403/429/5xx con loops o retries — anti-feature (riesgo de lockout)
- Iterar TODAS las cuentas del listado en los probes — un sample fijo (`cuentas[0]`
  o `HIGYRUS_SAMPLE_CUENTA` env var) cubre HIGY-02/03; iteración multi-cuenta
  queda deferred
- Cambiar la jerarquía de exceptions con nueva subclase — el fix HIGY-04 reusa
  `HigyrusAPIError` con `status_code=0` sentinel; sin `HigyrusShapeError` nueva

</domain>

<decisions>
## Implementation Decisions

### PII handling (HIGY-specific, NEW for this phase)

- **D-HIGY-1:** **Solo schemas committeables**, mirror exacto del patrón Phase 2/3.
  `.planning/verification/schemas/higyrus-client/<endpoint>.json` con `schema_of()`
  (claves + tipos, PII-free por construcción). Los tests mockeados usan **valores
  sintéticos inline** (e.g., `{"id": "CTA-001", "titular": "<x>", ...}`). **NO se
  committean payloads crudos NI fixtures anonimizadas**, aunque el roadmap SC#5
  dice "account data anonymized in fixtures" — la decisión del operador es
  preservar consistencia con el patrón establecido. `verification.capture()` queda
  disponible para `captures/` gitignored para inspección manual del operador.

- **D-HIGY-2:** **Driver stdout = conteos + shape, nunca valores.** Cada probe
  imprime `PROBE <name>: PASS (N items, shape <descriptor>)` (e.g., `PROBE
  get_listado_cuentas_sync: PASS (3 cuentas, list[dict])`). NUNCA imprime el
  contenido de ningún payload (titular, CBU, denominación, etc.). El field-type-map
  y el schema_of son seguros (claves+tipos). El operador puede leer `captures/`
  gitignored si necesita ver datos crudos. `safe_print(text, secrets=[HIGYRUS_USER,
  HIGYRUS_PASSWORD, _token])` cubre los secrets canónicos.

### SafeModel diff bidireccional (HIGY-03)

- **D-HIGY-3:** **Recursivo en nested models.** El diff baja a cada nested
  `SafeModel`: `Cuenta` → `DisposicionesGenerales`, `Domicilio[]`,
  `PersonaRelacionada[]`, `MedioComunicacion[]`, `CuentaBancaria[]`, `Administrador`
  → `Agente`/`Operador`/`Sucursal`. `Posicion` → `Parking[]`. Recorre vía
  `get_type_hints` recursivamente; para `list[X]` con `X` subclase de `SafeModel`,
  toma el primer elemento del payload como sample. Sin type drift check (la coerción
  de `_coerce` lo absorbe silenciosamente — el diff de campos es lo que detecta el
  FALSE PASS).

- **D-HIGY-4:** **Helper `_diff_safemodel_bidirectional(payload, model_cls, path)`
  inline en `main_higyrus.py`** como función privada module-level. Mirror del
  patrón D-IOL-14 (`_ASSUMED_FIELDS` también vivían en `main_iol.py`). YAGNI: hasta
  que Phase 5/Matriz confirme misma forma de diff (los modelos de Matriz pueden
  tener `Optional[T]` y envelope keys distintos), no se promueve a
  `verification/safemodel_diff.py`. Phase 5 copia el patrón si confirma compatibilidad.

- **D-HIGY-5:** **Un finding `SHAPE OPEN` por discrepancia, ambas direcciones**
  (mirror D-IOL-15):
  - `SHAPE` "`<path>.<key>: model declara, wire no emite (FALSE PASS riesgo)`" —
    dirección `model \ wire`. Es el trap silencioso, candidato a bug.
  - `SHAPE` "`<path>.<key>: wire emite, model ignora (info)`" — dirección
    `wire \ model`. Es información (posible feature nueva del backend), no es
    bug del cliente; queda OPEN para clasificación humana ex-post.
  - Path qualifier completo: e.g.,
    `.cuenta.administrador.operador.idExterno`, `.movimiento.idMovimientos[0]`.
  - Si la primera corrida emite 30 findings, es OK: el ciclo OPEN→CONFIRMED→FIXED
    filtra ruido manualmente.

- **D-HIGY-6:** **Probe `field_type_map` cubre 4 endpoints** (los 4 con models):
  `get_listado_cuentas` (`Cuenta`), `get_movimientos` (`Movimiento`),
  `get_posiciones` (`Posicion`), `get_posicion_valuada` (`PosicionValuada`).
  `get_health` retorna `dict[str, Any]` crudo — no aplica diff bidireccional;
  el driver solo asserta `isinstance(raw, dict)` y que tenga al menos una clave.

### `assert isinstance` fix dual sync+async (HIGY-04)

- **D-HIGY-7:** **Fix de fase obligatorio** (mirror IOL-07). Reemplazar los 5
  `assert isinstance(raw, list/dict)` en `packages/higyrus-client/src/higyrus_client/client.py`
  (líneas 208, 244, 286, 313, 337) y los 5 en
  `packages/higyrus-client/src/higyrus_client/aio.py` (líneas 233, 264, 302, 325, 345)
  por:
  ```python
  if not isinstance(raw, <expected_type>):
      raise HigyrusAPIError(
          status_code=0,
          errors=[{
              "title": "shape mismatch",
              "detail": f"expected {<expected_type>}, got {type(raw).__name__}",
          }],
      )
  ```
  Justificación: el fix es trivial, el riesgo de regresión bajo, y `AssertionError`
  no es API contract documentado (la jerarquía de excepciones documentada es
  `HigyrusClientError → HigyrusAPIError → ...`). Callers que catchean
  `AssertionError` deberían haber catcheado el base class.

- **D-HIGY-8:** **`status_code=0` sentinel para shape mismatch detectado client-side.**
  El HTTP fue 200 OK, pero el cliente detectó anomalía. Usar `status_code=0` como
  sentinel: indica «no hubo error HTTP, el cliente lo generó». Sin nueva subclase
  (`HigyrusShapeError` rechazado). Documentar el sentinel en el docstring de
  `HigyrusAPIError`:
  ```python
  status_code: HTTP status devuelto, o 0 si el error fue detectado client-side
      (e.g., shape mismatch tras un 2xx exitoso).
  ```

- **D-HIGY-9:** **10 regression tests mockeados** (5 por surface) en sección
  `# ---- Regressions ----` de `test_client.py` + `test_async_client.py`. Docstring
  por test:
  `"""Regression: assert isinstance(raw, <T>) reemplazado por HigyrusAPIError tipado (finding F-NN)."""`
  Cada test mockea `httpx_mock.add_response(json=<wrong_shape>)` y verifica que
  el cliente levanta `HigyrusAPIError` con `e.status_code == 0` y
  `e.errors[0]["title"] == "shape mismatch"`. Mocked-only; no se ejercita en vivo
  (el wire actual probablemente respeta la shape — el fix es prophylactic).

### Driver structure & lifecycle (carry-forward Phases 2-3 + HIGY-specific)

- **D-HIGY-10:** **Secuencia de probes en `main_higyrus.py`** (orden ejecución,
  todos con stdout verbatim `PROBE <name>: <status> <detail>` per D-02 Phase 2):
  1. `probe_login_sync` — `higyrus_client.login()` (HIGY-01). Si falla → cascade SKIPPED.
  2. `probe_login_async` — `await aio.login()` (HIGY-01). Si falla → cascade SKIPPED
     para los async siguientes (los sync ya pasaron).
  3. `probe_get_health_sync` — `higyrus_client.get_health()` (HIGY-02). Assert dict + keys ≥ 1.
  4. `probe_get_health_async` — `await aio.get_health()` (HIGY-02).
  5. `probe_get_listado_cuentas_sync` — `get_listado_cuentas(estado="alta")` (HIGY-02).
     **Resuelve `_resolved_cuenta`** = `cuentas[0].id` (o `HIGYRUS_SAMPLE_CUENTA`
     env var si seteada).
  6. `probe_get_listado_cuentas_async` — espejo (HIGY-02).
  7. `probe_get_movimientos_sync` — `get_movimientos(_resolved_cuenta, today-30d, today)` (HIGY-02).
  8. `probe_get_movimientos_async` — espejo (HIGY-02).
  9. `probe_get_posicion_valuada_sync` — `get_posicion_valuada(_resolved_cuenta,
     tipo_cuenta="propia", nivel="detalle", desde=today, hasta=today)` (HIGY-02).
     Si Higyrus rechaza el `tipo_cuenta`/`nivel`, emite finding `PARAM OPEN`.
  10. `probe_get_posicion_valuada_async` — espejo (HIGY-02).
  11. `probe_get_posiciones_sync` — `get_posiciones(_resolved_cuenta, fecha=today)` (HIGY-02).
  12. `probe_get_posiciones_async` — espejo (HIGY-02).
  13. `probe_parity_sync_async` — diff estructural payload sync vs async por endpoint
      (HIGY-06). **Verifica in-vivo la deviation conocida del `drop_none`** (CONCERNS.md):
      compara `httpx.URL.params` emitidos sync vs async para el mismo call con
      params optional=None. Si difieren → finding `SYNC-ASYNC-DRIFT OPEN` con detalle.
  14. `probe_field_type_map` — diff bidireccional recursivo (HIGY-03). Itera los 4
      endpoints con models. Emite un finding `SHAPE OPEN` por discrepancia
      (D-HIGY-5). Final: `PROBE field_type_map: PASS` o `PROBE field_type_map: FINDING
      F-NN, F-MM (OPEN)`.
  15. `probe_schema_snapshot` — 5 snapshots (DRIFT-01 mirror): uno por endpoint en
      `.planning/verification/schemas/higyrus-client/<func>.json` con envelope D-21
      y D-25 no-overwrite-on-drift.
  16. `probe_errors_envelope_sync` — **always-on**. `get_movimientos("INVALID-CUENTA-XXXXX",
      today, today)` esperando un 4xx con `errors=[{title, detail}]`. Assert
      `isinstance(e.errors, list)` y `e.errors[0]` tiene `"title"` y `"detail"`.
      (HIGY-05).
  17. `probe_errors_envelope_async` — espejo always-on (HIGY-05).
  18. `probe_auth_401` — **ÚLTIMO**, opt-in via `VERIFY_HIGYRUS_BAD_CREDS=1`
      (mirror D-IOL-1, D-IOL-2, D-IOL-4). Single-shot, sin retry, sin sleep,
      sin loops. `configure(password=HIGYRUS_PASSWORD + "_INVALID")` + try/finally
      restore al password real. Solo sync (no async: el cliente comparte
      `_password` global por surface — un solo attempt total).

- **D-HIGY-11:** **`_resolved_cuenta` resolution** — inicialmente `None`. El probe 5
  (`probe_get_listado_cuentas_sync`) lo setea:
  ```python
  _SAMPLE_CUENTA: str | None = os.getenv("HIGYRUS_SAMPLE_CUENTA")  # opcional override

  def probe_get_listado_cuentas_sync():
      global _resolved_cuenta
      cuentas = higyrus_client.get_listado_cuentas(estado="alta")
      _captured["listadoCuentas"] = cuentas
      if _SAMPLE_CUENTA:
          _resolved_cuenta = _SAMPLE_CUENTA
      elif cuentas:
          _resolved_cuenta = cuentas[0].id
      else:
          return ProbeResult("get_listado_cuentas_sync", "SKIPPED",
                             "no cuentas en estado=alta — downstream SKIPPED")
      return ProbeResult(...)
  ```
  Cada probe downstream que necesita `_resolved_cuenta` checkea al inicio:
  ```python
  if _resolved_cuenta is None:
      return ProbeResult("<name>", "SKIPPED", "no _resolved_cuenta resuelto")
  ```

- **D-HIGY-12:** **Date ranges derivados de `today`**, mirror D-IOL-19 (sin anchors
  hardcoded):
  - `get_movimientos`: `fecha_desde = today - timedelta(days=30)`,
    `fecha_hasta = today`. 30 días calendario maximiza probabilidad de capturar
    payload no vacío en cuenta real para que el diff bidireccional tenga shape
    para inspeccionar.
  - `get_posicion_valuada`: `desde = hasta = today`. Snapshot del día.
  - `get_posiciones`: `fecha = today`.
  - HIGY-07: si `raw == []` → ProbeResult PASS (no FAIL). El driver lo loggea
    como `PROBE <name>: PASS (0 items — empty path verified)`.

- **D-HIGY-13:** **Lifecycle async** — un único `asyncio.run(_async_main(...))`
  que ejecuta todos los probes async en secuencia y termina con `await aio.aclose()`
  dentro de un bloque `contextlib.suppress(Exception)` para honrar D-04 (IN-03 fix
  de Phase 2 ya estableció el patrón). El `_async_main` orquesta los probes
  pares (2/4/6/8/10/12/17) y devuelve los payloads necesarios para los probes
  13 (parity), 14 (field map) y 15 (schema snapshot) sin abrir un segundo event loop.

- **D-HIGY-14:** **Env vars del driver** (en `.env` y `.env.example`):
  - `HIGYRUS_USER`, `HIGYRUS_PASSWORD`, `HIGYRUS_BASE_URL` — obligatorias
    (`require_env` gate).
  - `HIGYRUS_CLIENT_ID` — opcional, default `""` (ya documentada en client.py).
  - `HIGYRUS_SAMPLE_CUENTA` — **opcional**, override del `cuentas[0].id`.
  - `HIGYRUS_SAMPLE_TIPO_CUENTA` — opcional, default `"propia"` (para
    `get_posicion_valuada`).
  - `HIGYRUS_SAMPLE_NIVEL` — opcional, default `"detalle"` (para
    `get_posicion_valuada`).
  - `VERIFY_HIGYRUS_BAD_CREDS` — opt-in para `probe_auth_401`, mirror exacto
    `VERIFY_IOL_BAD_CREDS` y `VERIFY_ANTIBOT` de Phase 2/3.

- **D-HIGY-15:** **`safe_print(text, secrets=[HIGYRUS_USER, HIGYRUS_PASSWORD, _token])`**.
  Lista de secrets se inicializa al cargar el módulo con
  `[HIGYRUS_USER, HIGYRUS_PASSWORD]` desde env. `_token` se agrega dinámicamente
  tras el primer `login()` (mirror D-IOL-7 con `_refresh_token`, pero acá solo
  hay access token — no hay refresh_token en Higyrus). Cubre T-3-* de Information
  Disclosure: el token y el username nunca pueden aparecer accidentalmente en
  stdout aun si un payload los reflejara.

### Schema snapshots por endpoint (DRIFT-01 mirror)

- **D-HIGY-16:** **5 snapshots committeables** en
  `.planning/verification/schemas/higyrus-client/`:
  - `get-health.json` (sin params)
  - `get-listado-cuentas.json` (`estado=alta` como sample)
  - `get-movimientos.json` (`_resolved_cuenta` + rango 30d como sample)
  - `get-posicion-valuada.json` (`_resolved_cuenta` + `propia`/`detalle`/`today` como sample)
  - `get-posiciones.json` (`_resolved_cuenta` + `today` como sample)
  Todos con envelope D-21 (endpoint, client_function, captured_at, base_url,
  sample_params, schema). D-25 lifecycle: no-overwrite en drift, emite finding
  SHAPE OPEN.

### Verified-live tests + Regressions sections (D-08/D-09 Phase 2 mirror)

- **D-HIGY-17:** En `packages/higyrus-client/tests/test_client.py` y
  `test_async_client.py`, agregar las **dos secciones verbatim**:
  - `# ------ Verified live (Phase 4) ------`
  - `# ------ Regressions ------`
  Lockear los invariantes mínimos (mocked, pytest-httpx):
  - HIGY-02: URLs exactas emitidas por cada endpoint (path verbatim, query string
    con `drop_none` aplicado para los 4 params optional de `get_movimientos` y
    los 6 de `get_posicion_valuada`).
  - HIGY-03: invariante de `from_api` tolerancia: payload mockeado con claves
    parciales devuelve un model con defaults tipados (e.g., `Cuenta.titular == ""`
    cuando wire emite payload sin `titular`).
  - HIGY-04: 10 regression tests del fix `assert isinstance` → `HigyrusAPIError`
    (D-HIGY-9), uno por endpoint por surface (5+5).
  - HIGY-05: invariante del parseo de `"errors"` envelope (test mockea response
    400 con `{"timestamp": ..., "errors": [{"title": ..., "detail": ...}]}` y
    verifica `e.errors` poblado, `e.timestamp` capturado).
  - HIGY-07: invariante de empty path: payload `[]` o 204 → `[]` retornado,
    no `None` ni crash (un test por endpoint con returns list).
  - HIGY-06: si `probe_parity_sync_async` encuentra deviation en `drop_none`,
    su fix tiene regression test mockeado verificando el `httpx.URL.params`
    emitido sync vs async son idénticos.

### Redaction + logging discipline

- **D-HIGY-18:** Reuso de `safe_print(text, secrets=[...])` (D-26 Phase 2). La lista
  de secrets se inicializa al cargar el módulo con `[HIGYRUS_USER, HIGYRUS_PASSWORD]`
  desde env, y se EXTIENDE dinámicamente con `_token` tras el primer login. Si
  cualquier payload o exception incluyera estos valores, la línea stdout los
  enmascara. Adicionalmente: el driver NUNCA imprime contenido de payloads
  (D-HIGY-2), por lo que la superficie de leak es solo PROBE status lines y
  conteos.

### Claude's Discretion

Las siguientes decisiones quedan a discreción del implementador, ancladas a los
patrones LOCKEADOS arriba:

- Texto exacto de líneas verbatim del summary final (los conteos por estado siguen
  el formato Phase 2: `SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N`).
- Estructura interna de `_diff_safemodel_bidirectional` (iterativo vs recursivo,
  con `yield from` vs lista acumulada, etc.) y el formato exacto del `path`
  qualifier (e.g., `.a.b[0].c` vs `a.b[0].c`).
- Tactic exacta de la cascade SKIPPED tras `login()` failure (D-IOL-3 mirror):
  un flag module-level `_auth_failed: bool` que cada probe checkea al inicio vs
  un wrapper decorator vs early-return en cada probe.
- Cómo el probe 13 (`probe_parity_sync_async`) inspecciona los params emitidos:
  monkey-patch del `httpx.Client.request` o captura del `request.url.query`
  desde el response — la API de pytest-httpx no está disponible acá (es live).
- Si el probe 5 (`probe_get_listado_cuentas_sync`) usa `estado="alta"` o no
  filtra: el roadmap no lo especifica. `"alta"` da el sample más útil; sin filtro
  da más cuentas pero también más payload (potencial PII redundante en stdout
  de conteos).
- Cómo se sub-clasifican findings de dirección A (`wire \ model`, info) vs
  dirección B (`model \ wire`, FALSE PASS) en el findings file: usar `detail`
  con prefijo `(info)` vs `(FALSE PASS riesgo)` es la convención sugerida.
- El timing exacto de la check de tipos en `_diff_safemodel_bidirectional` para
  detectar `Optional[T]` (los models actuales no usan `T | None` salvo
  potenciales adiciones futuras): si encuentra Optional, no emite finding
  dirección B (es explícitamente nullable, no FALSE PASS).
- Bounds plausibles del `cantidad` field en `Movimiento` (e.g., `|cantidad| <
  1e9` para detectar corrupción): el roadmap no lo pide y los valores legítimos
  de movimientos pueden ser muy variados — discrecionalmente NO se agregan
  bounds checks en Phase 4.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements

- `.planning/ROADMAP.md` §"Phase 4: Higyrus Verification" — goal, mode (mvp), 5
  success criteria, dependencies (Phase 3)
- `.planning/REQUIREMENTS.md` §"Verificación higyrus-client (HIGY)" — HIGY-01..07
  texto completo
- `.planning/REQUIREMENTS.md` §"Out of Scope" — anti-features (loops, retries,
  lockout risk)
- `.planning/REQUIREMENTS.md` §"Convención transversal" — fix dual sync+async
  con regresión mockeada por superficie
- `.planning/PROJECT.md` §"Key Decisions" — `main_*.py` como vehículo,
  dual sync/async, regresión mockeada por fix

### Phase 1 outputs (lockedados, base del harness)

- `.planning/phases/01-safety-harness-verification-infrastructure/01-CONTEXT.md` —
  D-01..D-16 del harness (drivers manuales, mockeados-only en CI, marker live,
  ubicación `verification/`, formato findings, lifecycle de status, pipeline
  capture→anonymize→fixture, schema_of, secrets discipline)
- `.planning/verification/FINDINGS-TEMPLATE.md` — plantilla con 7 clases fijas
  (SHAPE/AUTH/ERROR-MAP/PARAM/SYNC-ASYNC-DRIFT/NO-DATA/ANTI-BOT) y ciclo de
  estados (OPEN→CONFIRMED→FIXED + terminales EXPECTED/NO-FIX)

### Phase 2 outputs (lockedados, lifecycle establecido)

- `.planning/phases/02-mbito-verification/02-CONTEXT.md` — D-01..D-26 del lifecycle
  (driver con probes nombrados, stdout verbatim, write_findings + append_finding,
  schema snapshot envelope D-21 + D-25 no-overwrite, secciones Verified-live +
  Regressions, dual sync+async, safe_print)
- `.planning/phases/02-mbito-verification/02-01-SUMMARY.md` — `append_finding(...)`
  helper en `verification/findings.py` con preservación de status humano
- `.planning/phases/02-mbito-verification/02-02-SUMMARY.md` — driver
  `main_ambito_financiero.py` con 7 probes nombrados, anti-bot try/finally,
  schema snapshot con drift detection
- `.planning/phases/02-mbito-verification/02-03-SUMMARY.md` — Verified-live +
  Regressions sections en test files, baseline schema DRIFT-01 committeado
- `.planning/phases/02-mbito-verification/02-REVIEW.md` — code review post-mortem;
  CR-01/CR-02/WR-04 fix del `append_finding` y WR-01/03/IN-03 patterns del driver
- `verification/findings.py` — `append_finding(...)` con `_replace_art_block`,
  `_validate_pkg_slug`, validación CR-02; `_Finding` dataclass; lifecycle
  preservación de status humano (CONFIRMED/FIXED/EXPECTED/NO-FIX)

### Phase 3 outputs (lockedados, patrón opt-in 401 + auth-once)

- `.planning/phases/03-iol-verification/03-CONTEXT.md` — D-IOL-1..D-IOL-22 del
  patrón opt-in 401 con `configure(password+'_INVALID')` + try/finally restore
  (D-IOL-1, D-IOL-2), `login()` upfront + fail-fast cascade SKIPPED (D-IOL-3),
  probe 401 último en secuencia (D-IOL-4), secuencia de probes nombrados (D-IOL-5),
  lifecycle async con `asyncio.run` único (D-IOL-6), schema snapshots por
  endpoint (D-IOL-16), Verified-live + Regressions sections (D-IOL-21), reuso
  de `safe_print` con secrets dinámicos (D-IOL-22)
- `.planning/phases/03-iol-verification/03-SECURITY.md` — verificación de las
  27 mitigations de threat model (T-1-* a T-5-*); Phase 4 hereda mismas
  mitigations adaptadas a Higyrus (T-3-* Information Disclosure: `safe_print`
  + driver sin valores en stdout)
- `.planning/phases/03-iol-verification/03-VERIFICATION.md` — UAT pendiente
  de IOL-05 live opt-in (no afecta Phase 4)

### Codebase maps

- `.planning/codebase/INTEGRATIONS.md` — auth por paquete, endpoints, base URLs
  conocidas (Higyrus usa Bearer 24h TTL, login en `POST /api/login`)
- `.planning/codebase/TESTING.md` — pytest config (`asyncio_mode = "auto"`,
  `--strict-markers`), pytest-httpx pattern (`url=` con full query string),
  autouse fixtures por paquete, convención `Regression: ... (issue #NNN)` →
  `(finding F-NN)` per D-07 Phase 2
- `.planning/codebase/CONVENTIONS.md` — naming, ruff line-length=100,
  double quotes, `from __future__ import annotations` obligatorio, mypy strict
- `.planning/codebase/CONCERNS.md` — la deviation conocida de `drop_none` en
  Higyrus async `_request` (HIGY-06 candidate; el driver debe verificar o
  negar in-vivo via `probe_parity_sync_async`)
- `.planning/codebase/ARCHITECTURE.md` — estado singleton, dual sync/async,
  configure() como override point, jerarquía de exceptions

### Implementación actual del cliente (target a verificar)

- `packages/higyrus-client/src/higyrus_client/client.py` — superficie sync;
  `login()` (líneas 92-128) POST `/api/login` con Bearer 24h; `_request` con
  `drop_none(params)` (línea 178); `get_health` (205), `get_movimientos` (217),
  `get_posicion_valuada` (248), `get_listado_cuentas` (290), `get_posiciones`
  (317). 5 sites con `assert isinstance(raw, list/dict)` (líneas 208, 244, 286,
  313, 337) — TARGETS del fix HIGY-04.
- `packages/higyrus-client/src/higyrus_client/aio.py` — superficie async; mismo
  set de funciones espejado; `aclose()` para liberar el AsyncClient; `_token_lock`
  + `_client_lock` para serializar accesos concurrentes; `_request` con
  `drop_none(params)` (línea 206); 5 sites con `assert isinstance(raw, list/dict)`
  (líneas 233, 264, 302, 325, 345) — TARGETS del fix HIGY-04 mirror.
- `packages/higyrus-client/src/higyrus_client/models.py` — `SafeModel` base
  class + `_coerce` (líneas 30-100); models top-level: `Cuenta` (con nested
  `DisposicionesGenerales`/`Domicilio[]`/`PersonaRelacionada[]`/
  `MedioComunicacion[]`/`CuentaBancaria[]`/`Administrador→{Agente,Operador,Sucursal}`),
  `Movimiento`, `Posicion` (con `Parking[]`), `PosicionValuada`. **Documentación
  en docstrings menciona que el wire usa ASCII sin acentos** (PDF mostraba
  acentos como artefactos OCR) y `cantidad: float` aunque el PDF labelaba
  como int.
- `packages/higyrus-client/src/higyrus_client/exceptions.py` — jerarquía:
  `HigyrusClientError` → `HigyrusAPIError(status_code, errors, timestamp)` →
  (`HigyrusAuthError`/`HigyrusAuthorizationError`/`HigyrusRateLimitError`).
  `errors` y `timestamp` preservados del envelope (HIGY-05 path verification).
  `status_code=0` sentinel queda documentado en docstring para shape mismatch
  client-side (D-HIGY-8).
- `packages/higyrus-client/src/higyrus_client/_params.py` — `drop_none`,
  `format_date`, `format_bool` helpers. `drop_none` es el target verification
  de HIGY-06.
- `packages/higyrus-client/src/higyrus_client/__init__.py` — `__all__` público:
  `configure`, `login`, `get_health`, `get_movimientos`, `get_posicion_valuada`,
  `get_listado_cuentas`, `get_posiciones`, 4 exceptions, 4 models top-level
  y nested.
- `packages/higyrus-client/tests/conftest.py` — autouse fixtures
  `_configure_sync` / `_configure_async`; precarga `_token = "test-token"` y
  `_token_ts` reciente para evitar disparar login en endpoints autenticados
  durante tests.
- `packages/higyrus-client/tests/test_client.py` — tests mockeados pre-existentes;
  se le hace append de las secciones Verified-live + Regressions (D-HIGY-17).
- `packages/higyrus-client/tests/test_async_client.py` — espejo async; idem.
- `packages/higyrus-client/.env.example` — `HIGYRUS_USER`, `HIGYRUS_PASSWORD`,
  `HIGYRUS_BASE_URL` requeridos; `HIGYRUS_CLIENT_ID` opcional. Phase 4 agrega
  como opcionales: `HIGYRUS_SAMPLE_CUENTA`, `HIGYRUS_SAMPLE_TIPO_CUENTA`,
  `HIGYRUS_SAMPLE_NIVEL`, `VERIFY_HIGYRUS_BAD_CREDS`.

### Driver actual + harness ya construido

- `main_higyrus.py` — driver actual (smoke-test mínimo, solo `get_health` +
  `get_listado_cuentas`); se reescribe según D-HIGY-10 con los 18 probes.
- `verification/findings.py` — `append_finding(...)` ya hardened (CR-01/CR-02/
  WR-04 post-Phase-2 review); Higyrus driver lo usa directamente.
- `verification/__init__.py` — barrel: `append_finding`, `Denylist`,
  `anonymize`, `capture`, `mutating_allowed`, `new_findings`, `redact`,
  `require_env`, `safe_print`, `schema_of`, `write_findings`.
- `verification/schema.py` — `schema_of(payload)`: claves+tipos, PII-free por
  construcción. Phase 4 lo usa para los 5 snapshots.
- `verification/redaction.py` — `redact(value)`, `safe_print(text, secrets=[...])`
  (D-HIGY-15).
- `verification/env_gate.py` — `require_env(pkg, [vars])`: skip-and-continue si
  faltan HIGYRUS_USER / HIGYRUS_PASSWORD / HIGYRUS_BASE_URL (HARN-01).
- `verification/capture.py` — `capture(pkg, endpoint, payload)` para `captures/`
  gitignored (disponible para inspección manual del operador; Phase 4 no
  commitea fixtures crudos).
- `verification/anonymize.py` — `anonymize(payload, Denylist)` disponible pero
  **no usado en Phase 4** (decisión D-HIGY-1: solo schemas, no fixtures
  anonimizadas).
- `conftest.py` (root) — `--live` flag, marker `live` registrado, deselect
  default; `sys.path` con repo root para `verification/` importable.

### Documentación externa

- `documentation/higyrus-docs.pdf` — PDF de referencia del backend. Útil para
  identificar valores documentados de `tipo_cuenta`/`nivel` de
  `get_posicion_valuada` (pp. 49-52, 103+), pero **OCR-fragile**: la doc PDF
  muestra acentos en claves donde el wire usa ASCII (verificado en `models.py`).
  Tratar como referencia, no source-of-truth.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`verification.findings.append_finding`** — helper DRY committeado y hardened
  en Phase 2. Higyrus lo usa con `pkg="higyrus-client"`; idempotente por `fid`,
  preserva prosa humana en status promovidos, valida class/status/title/pkg
  slug.
- **`verification.findings.write_findings`** — esqueleto del findings file. No-op
  si existe; perfecto para idempotencia en runs sucesivos.
- **`verification.schema.schema_of`** — único primitivo para schema snapshots
  (D-HIGY-16). PII-free por construcción.
- **`verification.redaction.safe_print`** — con `secrets=[HIGYRUS_USER,
  HIGYRUS_PASSWORD, _token]` (D-HIGY-15). El regex `_BEARER` interno cubre
  tokens reflejados aun sin secrets enumerados.
- **`verification.env_gate.require_env`** — el driver llama
  `require_env("higyrus-client", ["HIGYRUS_USER", "HIGYRUS_PASSWORD",
  "HIGYRUS_BASE_URL"])` al inicio; si faltan, imprime `SKIPPED higyrus-client:
  missing ...` y exit 0.
- **`verification.capture.capture`** — disponible para staging gitignored. Phase 4
  lo invoca opcionalmente para que el operador pueda inspeccionar payloads crudos
  manualmente (e.g., debug del field-type-map), pero los archivos no se commitean.
- **pytest-httpx `httpx_mock.add_response(url=..., method=...)`** — patrón
  estándar de los tests existentes en `packages/higyrus-client/tests/`. Los nuevos
  Verified-live tests usan exactamente el mismo patrón con URL full incluyendo
  query string para los 5 endpoints (que tienen multiple optional params via
  `drop_none`).
- **Autouse fixtures `_configure_sync`/`_configure_async`** de
  `packages/higyrus-client/tests/conftest.py` — los Verified-live tests heredan
  el setup sin modificación. Para los 10 tests del fix HIGY-04 (shape mismatch),
  el setup precarga `_token` para que el `_request` llegue al body parsing y
  el `if not isinstance` se dispare.
- **`SafeModel.from_api` + `get_type_hints`** — la fuente de truth de qué espera
  el cliente. El probe `field_type_map` usa `get_type_hints(Cuenta)` y compara
  contra `set(raw.keys())` por endpoint. Recursivo para nested models.

### Established Patterns

- **Estado singleton a nivel de módulo** (`_base_url`, `_client_id`, `_user`,
  `_password`, `_token`, `_token_ts`, `_client`) en `client.py` y `aio.py`.
  Phase 4 NO agrega state nuevo al cliente — el fix HIGY-04 es solo cambio de
  `assert` por `raise`, sin nuevos globals.
- **Doble superficie sync/async espejada** — todo fix de lógica (HIGY-04 en
  particular) se duplica en `client.py` y `aio.py`. Los locks async son
  `_token_lock = asyncio.Lock()` y `_client_lock = asyncio.Lock()`; ninguna
  decisión Phase 4 toca el path de auth (no hay refresh_token a la IOL).
- **`configure()` resetea estado cached** — patrón obligatorio para el probe
  `auth_401` opt-in (D-HIGY-10 #18). El try/finally garantiza restore al
  password real.
- **Tests deterministas con `base_url="https://api.test"`** vía autouse fixture
  — los nuevos tests lo respetan.
- **`from __future__ import annotations`** al tope de todo módulo nuevo
  (CONVENTIONS.md). El `main_higyrus.py` reescrito lo respeta.
- **`ruff` line-length=100, double quotes, 4 espacios; `mypy --strict`** —
  todo código nuevo debe pasar antes de commit.
- **`contextlib.suppress(Exception)` para teardown** (Phase 2 IN-03) — el
  `_async_main` de Higyrus termina con
  `with contextlib.suppress(Exception): await aio.aclose()`.
- **`HigyrusAPIError(status_code, errors=[...], timestamp=...)`** —
  constructor existente toma 3 args. El fix HIGY-04 reusa la firma con
  `status_code=0` sentinel y `errors=[{"title": "shape mismatch", "detail": ...}]`
  sin `timestamp` (es client-side, no hay timestamp del server).

### Integration Points

- **`main_higyrus.py`** — punto de entrada vivo de Phase 4; se reescribe (no
  archivo nuevo). Lifecycle análogo a Phases 2-3.
- **`packages/higyrus-client/src/higyrus_client/client.py` + `aio.py`** —
  reciben el fix HIGY-04 (10 sites de `assert isinstance` → `raise
  HigyrusAPIError(0, [...])`. Mirror sync/async obligatorio.
- **`packages/higyrus-client/src/higyrus_client/exceptions.py`** — recibe edit
  del docstring de `HigyrusAPIError.status_code` para documentar el sentinel
  `0` (D-HIGY-8). Sin nuevas subclases.
- **`packages/higyrus-client/tests/test_client.py` + `test_async_client.py`** —
  append de las secciones Verified-live + Regressions (D-HIGY-17) con los
  tests de HIGY-02/03/04/05/07.
- **`packages/higyrus-client/.env.example`** — append de 4 env vars opcionales
  documentadas (D-HIGY-14).
- **`.planning/verification/higyrus-client-findings.md`** — generado por driver.
- **`.planning/verification/schemas/higyrus-client/`** — 5 snapshot files
  committeable (D-HIGY-16).

</code_context>

<specifics>
## Specific Ideas

- **18 probes en orden D-HIGY-10** — copiar la tabla literal arriba al planner.
- **`_resolved_cuenta` resolution flow** — D-HIGY-11 con override
  `HIGYRUS_SAMPLE_CUENTA` opcional.
- **`HIGYRUS_SAMPLE_TIPO_CUENTA` default `"propia"`, `HIGYRUS_SAMPLE_NIVEL`
  default `"detalle"`** (D-HIGY-14) — variables opcionales con defaults
  documentados. Finding `PARAM OPEN` si falla, listando valores documentados
  en `documentation/higyrus-docs.pdf` pp. 49-52 para que el operador setee
  la env var correcta.
- **`fecha_desde = today - 30d`** para `get_movimientos` (no 5 días hábiles
  como D-IOL-19): 30 días maximiza probabilidad de payload no vacío para que
  el diff bidireccional tenga shape a inspeccionar.
- **`fecha = today` para `get_posiciones`** y **`desde = hasta = today` para
  `get_posicion_valuada`** — snapshots del día.
- **`probe_errors_envelope` con `id_cuenta='INVALID-CUENTA-XXXXX'`** (D-HIGY-10 #16).
  String literal puede ajustarse discrecionalmente (e.g., `'NONEXISTENT-CTA'`)
  con tal que sea sintácticamente válido pero no exista en el tenant.
- **`probe_auth_401`** opt-in con `VERIFY_HIGYRUS_BAD_CREDS=1`, mirror exacto
  de `VERIFY_IOL_BAD_CREDS=1` (D-IOL-1 + D-IOL-2). Single-shot, sin retry.
- **Diff bidireccional helper signature** (D-HIGY-4):
  ```python
  def _diff_safemodel_bidirectional(
      payload: Any,
      model_cls: type,
      path: str = "",
  ) -> Iterator[tuple[str, str, str]]:
      """Yields (path, direction, key) tuples.
      direction ∈ {'model-only', 'wire-only'}.
      """
  ```
- **Cascade SKIPPED helper** — un flag module-level `_auth_failed: bool = False`
  set por `probe_login_sync` / `probe_login_async`. Cada probe downstream
  checkea `if _auth_failed: return ProbeResult("<name>", "SKIPPED", "auth failed")`.
  Implementación discrecional (mirror D-IOL-3 Discretion).
- **Verbatim status strings (heredados de Phase 2 D-02)**:
  - `PROBE <name>: PASS [<detail>]`
  - `PROBE <name>: FAIL [<detail>]`
  - `PROBE <name>: SKIPPED (<reason>)`
  - `PROBE <name>: FINDING <fid>[, <fid>...] (<status>)`
- **Summary final (heredado de Phase 2 D-02)**:
  `SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N`
- **Shape mismatch test pattern** (D-HIGY-9, ejemplo):
  ```python
  def test_get_health_raises_on_list_payload(httpx_mock):
      """Regression: assert isinstance(raw, dict) → HigyrusAPIError tipado (finding F-NN)."""
      httpx_mock.add_response(
          url="https://api.test/api/health",
          json=["unexpected", "list"],
      )
      with pytest.raises(HigyrusAPIError) as exc_info:
          higyrus_client.get_health()
      assert exc_info.value.status_code == 0
      assert exc_info.value.errors[0]["title"] == "shape mismatch"
  ```

</specifics>

<deferred>
## Deferred Ideas

- **Iterar TODAS las cuentas del listado en los probes (multi-cuenta sweep)** —
  Phase 4 usa un sample fijo (`cuentas[0]` o env var); iteración multi-cuenta
  con agregación de findings cross-cuenta sería un cycle posterior. La semántica
  de "missing en 3/10 cuentas" como finding requiere diseño extra.
- **Fixtures committeable anonimizadas via `verification.anonymize`** — el
  roadmap Phase 4 SC#5 lo sugiere ("account data anonymized in fixtures") pero
  D-HIGY-1 lo difiere por consistencia con Phase 2/3. Si en cycle futuro se
  decide commitar fixtures, la `verification.anonymize` + `Denylist` ya están
  listas; agregar `verification/denylists/higyrus_client.py` y usar fixtures
  en lugar de `httpx_mock.add_response(json=<inline>)`.
- **Promover `_diff_safemodel_bidirectional` a `verification/safemodel_diff.py`**
  — si Phase 5/Matriz confirma compatibilidad de modelos (mismo patrón
  `from_api` + `get_type_hints`), promover el helper a primitivo committeable
  y export del barrel. YAGNI hasta confirmar.
- **Type drift check** (e.g., wire `'1234'` string vs model `float`) — `_coerce`
  lo absorbe silenciosamente. Sería una clase de finding nueva. Útil pero no
  pedido por HIGY-03 — defer a cycle futuro.
- **Plausibility bounds en `cantidad` de `Movimiento` y `Posicion`** —
  análogo al check de `ultimoPrecio` en IOL (D-IOL-bounds). Phase 4 valida
  shape únicamente; range checks quedan deferred.
- **`probe_get_listado_cuentas` con `tipo_cuenta` u otros filtros** — Phase 4
  usa solo `estado="alta"`. Combinatoria de filtros queda deferred.
- **Test de auth-once discipline mockeado** — los tests precargan `_token`
  via autouse fixture; un test que ejercita "una sola llamada a login() por
  N requests autenticados" sería verificación del fixture, no del cliente.
  Discrecionalmente puede agregarse pero no es load-bearing.
- **`HigyrusShapeError(HigyrusAPIError)` subclase** — D-HIGY-8 lo rechaza:
  callers que necesitan distinguir HTTP-error vs client-detected-anomaly
  checkean `e.status_code == 0`. Si en el futuro el patrón se vuelve común
  (Phase 5 Matriz también lo necesita), promover a subclase.
- **Refactor a clase `Client` por instancia / deduplicación sync-async** —
  PROJECT.md lo marca explícitamente fuera de scope para todo el ciclo de
  verificación.
- **DRIFT-02 (informe consolidado per-package)** — anclado a Phase 5;
  Phase 4 produce su parte (findings + 5 snapshots + regression tests +
  fix HIGY-04 cerrado) pero el informe consolidado vive después.

</deferred>

---

*Phase: 04-higyrus-verification*
*Context gathered: 2026-06-06*
