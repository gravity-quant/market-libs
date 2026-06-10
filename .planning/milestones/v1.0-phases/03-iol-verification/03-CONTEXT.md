# Phase 3: IOL Verification - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase ejecuta el **segundo ciclo end-to-end de verificación en vivo** del monorepo,
sobre el target de **mayor riesgo silencioso de shape drift**: `iol-client` devuelve
`dict[str, Any]` crudo sin validación, lo que significa que cualquier cambio en el
wire de Invertir Online (`api.invertironline.com`) puede silenciosamente romper a los
callers sin que un test mockeado lo detecte.

Aplica el mismo loop **driver → finding → fix → mocked regression** establecido en
Phase 2 (Ámbito), pero con tres complicaciones nuevas: (1) **auth real** (OAuth
password grant) con **riesgo de lockout** si el probe 401 se dispara mal; (2) **shape
drift detection** explícito vía mapa campo→tipo observado vs asumido; (3) **fix
in-cycle dual sync+async** del bug conocido `grant_type=refresh_token` + fallback a
password (IOL-07).

**En alcance:**

- Ejercitar la superficie pública sync+async del `iol-client` contra
  `https://api.invertironline.com`:
  - Auth flow: `login()` explícito up-front + lazy-auth en primer call (IOL-01)
  - Happy-path sweep de las 4 funciones públicas: `get_quote`, `get_historical_quotes`,
    `get_instruments`, `get_instruments_by_type`, con retención del payload crudo
    (IOL-02)
  - Mapa campo→tipo observado del payload de cada endpoint, comparado contra los
    fields asumidos por los callers (IOL-03)
  - Validación in-vivo de: clave `["titulos"]` en `get_instruments_by_type`, formato
    de fecha del path histórico, campos numéricos como JSON number no string (IOL-04)
  - Mapeo de 401 con credenciales inválidas (IOL-05) — opt-in
  - Paridad estructural sync↔async por endpoint (IOL-06)
- **Implementar `grant_type=refresh_token` + fallback a password grant** en
  `client.py` y `aio.py` con tests sync y async cubriendo refresh exitoso y fallback
  (IOL-07) — fix DE FASE, no opportunistic
- Driver `main_iol.py` reescrito de smoke-test mínimo a probes nombrados D-01..D-04
- Auto-generar `.planning/verification/iol-client-findings.md` y poblarlo vía
  `append_finding(...)` (helper DRY de Phase 2, ya con preservación de prosa humana,
  validación de slug, single-line title — CR-01/CR-02/WR-04 ya mergeados)
- Schema snapshots committeable por endpoint en
  `.planning/verification/schemas/iol-client/<func>.json` con envelope D-21 y
  no-overwrite-on-drift D-25
- Tests mockeados nuevos en `test_client.py` + `test_async_client.py` (secciones
  `# ------ Verified live (Phase 3) ------` y `# ------ Regressions ------`),
  incluyendo regression tests para el fix del refresh_token
- Suite completa verde: `uv run pytest -q` + mypy strict + ruff check + format

**Fuera de alcance:**

- Verificación en vivo de Higyrus / Matriz — Phases 4-5
- Re-tocar harness `verification/*` o `conftest.py` — Phase 1 lockeada; sólo se
  AGREGAN call sites a `append_finding`, no se modifica el helper
- Tests `@pytest.mark.live` propios de IOL — el marker existe (Phase 1) pero esta
  fase sigue el patrón Phase 2: driver-only para live, mocked-only en pytest
- Fix opportunistic de bugs descubiertos DURANTE el live run que no sean el
  refresh_token explícito — se documentan como findings OPEN para clasificación
  humana ex-post (nota MVP del Phase 2 context honorada)
- Refactor del cliente a clase / instancias / deduplicación sync-async — PROJECT.md
  explícitamente fuera de scope para todo el ciclo de verificación
- Disparar 401/403/429/5xx con loops o retries — anti-feature (riesgo de lockout
  + IP-ban)
- Cambiar la jerarquía de exceptions (`IOLAuthError`, `IOLAPIError`,
  `IOLRateLimitError`) — sólo se ejercitan; cualquier propuesta de cambio queda
  como finding OPEN

</domain>

<decisions>
## Implementation Decisions

### Auth-once safety & lockout management (NEW for IOL)

- **D-IOL-1:** **Probe 401 (IOL-05) opt-in vía `VERIFY_IOL_BAD_CREDS=1`.** Mirror
  exacto del patrón de Phase 2 (D-12 `VERIFY_ANTIBOT`). Sin la env var, el probe
  imprime `PROBE auth_401: SKIPPED (opt-in via VERIFY_IOL_BAD_CREDS=1)` y el driver
  sigue. **Single-shot, sin retry, sin sleep, sin loops** (D-14 mirror) — IOL
  bloquea cuentas tras N intentos fallidos consecutivos; un solo attempt
  deliberado por corrida es el techo permitido.

- **D-IOL-2:** **Inyección de bad-creds vía `configure(password=IOL_PASSWORD + "_INVALID")`
  + try/finally restore.** Mirror exacto del patrón D-15 de Phase 2 (`probe_antibot`
  con `configure(user_agent=BAD_UA)` + finally `configure(user_agent=GOOD_UA)`).
  Una sola env var (`IOL_PASSWORD`) sigue siendo la fuente de verdad; el sufijo
  `_INVALID` garantiza un password que no coincide con ningún valor real. El
  `finally` SIEMPRE restaura `password=IOL_PASSWORD` original, incluso si la llamada
  levanta o si la corrida es interrumpida — crash-proof contra dejar el state
  global con creds rotas. No se introducen variables de entorno dedicadas
  (`IOL_INVALID_USER`/`IOL_INVALID_PASSWORD`) — innecesarias y agregan setup.

- **D-IOL-3:** **`login()` explícito up-front + fail-fast con cascade SKIPPED.**
  El driver llama `iol_client.login()` (sync) y `await aio.login()` (async) UNA
  sola vez al inicio del run, como un probe nombrado `probe_login_sync` /
  `probe_login_async`. Resultados:
  - Si `login()` **succeeds**: todos los probes downstream usan el token cacheado
    via lazy-auth (`_ensure_token` no re-disparará el password grant porque
    `_token_expires_at` está vigente). Auth-once discipline.
  - Si `login()` **levanta `IOLAuthError`** (credenciales reales rechazadas o
    cuenta lockeada): el driver marca **TODOS los probes downstream como
    `SKIPPED("auth failed: <reason>")` en cascada**, emite el summary final con
    los conteos, y **sale con exit 0** (D-04 honrado — el findings file ya tiene
    el F-NN de la falla de auth). Sin re-tries. Sin loop. Sin reabrir el client.
  - Cualquier otro error inesperado en `login()` propaga como crash inesperado
    (D-04 lo permite explícitamente para fallas no clasificables).

- **D-IOL-4:** **Probe 401 corre ÚLTIMO en la secuencia** (mirror D-13 de Phase 2,
  donde `probe_antibot` también va último). Razones:
  - Si la corrida default no setea `VERIFY_IOL_BAD_CREDS=1`, el probe imprime
    SKIPPED y nada cambia.
  - Si se setea: el `try/finally` muta `_password` global momentáneamente y lo
    restaura. Como ya corrieron todos los probes anteriores con el state correcto,
    aun una falla del restore (raro) no afecta este run.
  - Aísla el riesgo: el único probe que toca state de auth real está en el último
    paso. Pareja conceptual del anti-bot que también es destructivo del state UA.

### Driver structure & lifecycle (carry-forward from Phase 2 + adaptaciones)

- **D-IOL-5:** **Secuencia de probes en `main_iol.py`** (orden ejecución, todos
  con stdout verbatim `PROBE <name>: <status> <detail>` per D-02 Phase 2):
  1. `probe_login_sync` — `iol_client.login()` (IOL-01). Si falla → cascade SKIPPED.
  2. `probe_login_async` — `await aio.login()` (IOL-01). Si falla → cascade SKIPPED
     para los async siguientes (los sync ya pasaron).
  3. `probe_get_quote_sync` — `iol_client.get_quote("GGAL")` (IOL-02).
  4. `probe_get_quote_async` — `await aio.get_quote("GGAL")` (IOL-02).
  5. `probe_get_historical_quotes_sync` — GGAL últimos 5 días hábiles (IOL-02).
  6. `probe_get_historical_quotes_async` — espejo (IOL-02).
  7. `probe_get_instruments_sync` — `pais="argentina"` (IOL-02).
  8. `probe_get_instruments_async` — espejo (IOL-02).
  9. `probe_get_instruments_by_type_sync` — `instrument_type="acciones"` (IOL-02 + IOL-04 envelope).
  10. `probe_get_instruments_by_type_async` — espejo (IOL-02 + IOL-04 envelope).
  11. `probe_parity_sync_async` — diff estructural payload sync vs async por
      endpoint (IOL-06).
  12. `probe_field_type_map` — `schema_of(raw)` por endpoint comparado contra
      `_ASSUMED_FIELDS` hardcoded; emite findings SHAPE OPEN por discrepancia
      (IOL-03 + IOL-04 detail).
  13. `probe_schema_snapshot` — 4 snapshots, uno por endpoint, en
      `.planning/verification/schemas/iol-client/<func>.json` con envelope D-21
      y D-25 no-overwrite-on-drift (DRIFT-01 mirror).
  14. `probe_refresh_token` — fuerza `_token_expires_at = 0` para gatillar
      `_ensure_token` → vía refresh_token path; verifica que la nueva auth NO
      re-disparó password grant (IOL-07 in-vivo verification del fix).
  15. `probe_auth_401` — **ÚLTIMO**, opt-in via `VERIFY_IOL_BAD_CREDS=1` (D-IOL-1,
      D-IOL-2, D-IOL-4). Single-shot. (IOL-05.)

- **D-IOL-6:** **Lifecycle async** — un único `asyncio.run(_async_main(...))`
  que ejecuta todos los probes async en secuencia y termina con `await aio.aclose()`
  dentro de un bloque `contextlib.suppress(Exception)` para honrar D-04 (IN-03 fix
  de Phase 2 ya estableció el patrón). El `_async_main` orquesta los probes 2/4/6/8/10
  y devuelve los payloads necesarios para los probes 11 (parity), 12 (field map) y
  13 (schema snapshot) sin abrir un segundo event loop.

- **D-IOL-7:** **`safe_print(text, secrets=[IOL_PASSWORD, IOL_USER, _refresh_token])`**.
  Lista de secrets ahora NO vacía (a diferencia de Phase 2). `_refresh_token` se
  agrega dinámicamente al lista una vez capturado por el primer `login()`. Cubre
  T-3-* de Information Disclosure: el access_token, el refresh_token, y el username
  nunca pueden aparecer accidentalmente en stdout aun si un payload los reflejara.

### Refresh token + password fallback (IOL-07 — fix in-cycle)

- **D-IOL-8:** **Estado nuevo en client.py y aio.py: `_refresh_token: str | None = None`.**
  Mirror exacto del singleton existente `_token`. El barrel `iol_client/__init__.py`
  NO re-exporta `_refresh_token` (es state privado). `configure()` resetea ambos
  (`_token = None; _refresh_token = None; _token_expires_at = 0.0`).

- **D-IOL-9:** **`login()` captura ambos tokens.** El payload del `POST /token`
  con `grant_type=password` devuelve `{"access_token": str, "refresh_token": str,
  "expires_in": int}`. La función actual captura sólo `access_token`; el fix
  agrega `refresh_token = data.get("refresh_token")`. Si la respuesta no incluye
  `refresh_token` (no es OAuth-spec compliant), se loggea como finding OPEN clase
  AUTH y se guarda `None` — el fallback a password grant lo cubre.

- **D-IOL-10:** **`_ensure_token()` con fallback en dos niveles** (mirror sync+async):
  ```
  def _ensure_token() -> None:
      if _token and time.time() < _token_expires_at:
          return
      # Token expirado o ausente.
      if _refresh_token:
          try:
              _refresh()  # POST /token con grant_type=refresh_token
              return
          except IOLAuthError:
              # Refresh inválido (revocado, expirado, etc.) — fallback a password.
              pass
      login()  # password grant
  ```
  `_refresh()` es función privada nueva: `POST /token` con
  `grant_type=refresh_token&refresh_token={_refresh_token}`. Si succeeds, actualiza
  `_token`, `_refresh_token` (rotación opcional según server), y `_token_expires_at`.
  Si retorna 4xx, levanta `IOLAuthError` que el `_ensure_token` atrapa y cae al
  password grant. La duplicación dual sync/async se preserva (mismo
  `_refresh()` separado por surface, con sus locks correspondientes en aio.py).

- **D-IOL-11:** **Probe in-vivo `probe_refresh_token`**:
  - Verifica que `_refresh_token` quedó cacheado tras `login()` del paso 1
    (sino → finding AUTH OPEN, AMB-06-style).
  - Fuerza `_token_expires_at = 0.0` (simula expiry).
  - Llama un endpoint autenticado (`get_instruments("argentina")`).
  - Verifica que la corrida tuvo éxito **sin re-disparar password grant**. Cómo:
    Phase 2 estableció el patrón de leer state de módulo privado para verificación
    (mutation_gate.py:55 — `mutation_gate` lee `matriz_client.client._base_url`).
    Acá monkey-checkeamos `_token` antes y después: si cambió Y `_refresh_token`
    no es None Y `expires_at` se renovó → el refresh path funcionó. Si pasa al
    password grant → finding AUTH OPEN (refresh no funciona en vivo aunque los
    tests mockeados pasen).
  - **Cautela contra lockout** (D-IOL-1 spirit): el probe NO ejercita la rama
    "refresh inválido → fallback a password" en vivo — esa cobertura se queda
    como mocked-only para no consumir attempts del password grant innecesariamente.

- **D-IOL-12:** **Tests mockeados duales para IOL-07** en
  `test_client.py` + `test_async_client.py` sección `Verified live (Phase 3)` y
  `Regressions`:
  - `test_refresh_token_success_path` (sync) + `test_async_refresh_token_success_path`
    (async): mock `POST /token` 1 con password grant returning access+refresh,
    expirar el token, mock `POST /token` 2 con `grant_type=refresh_token` returning
    new access+refresh, verificar que `_request` lo usa sin re-disparar password.
  - `test_refresh_fails_falls_back_to_password` (sync) + async mirror: mock refresh
    401 → mock password grant success → verificar que el segundo POST fue con
    `grant_type=password`.
  - `test_refresh_and_password_both_fail` (sync) + async mirror: ambos 401 →
    `IOLAuthError` levantado.
  - `test_login_captures_refresh_token` (sync) + async mirror: el primer login()
    setea `_refresh_token` desde el payload.

### Field→type map + drift detection (IOL-03, IOL-04)

- **D-IOL-13:** **Reutilizar `verification.schema.schema_of(payload)`** del Phase 1.
  Genera la estructura observada `{key: type_name}` recursiva, PII-free por
  construcción (sólo nombres de tipos, no valores). Un único primitivo necesario.

- **D-IOL-14:** **Caller assumptions hardcoded en `main_iol.py` como constantes
  module-level**, en lugar de un archivo externo:
  ```python
  _ASSUMED_QUOTE_FIELDS: dict[str, str] = {
      "ultimoPrecio": "float",      # IOL-04: numeric, JSON number
      "simbolo": "str",
      # ... otros campos que los callers asumen
  }
  _ASSUMED_HISTORICAL_FIELDS: dict[str, str] = {
      "fechaHora": "str",
      "ultimoPrecio": "float",
      # ...
  }
  _ASSUMED_INSTRUMENTS_BY_TYPE_ENVELOPE: dict[str, str] = {
      "titulos": "list",            # IOL-04: envelope key
  }
  ```
  Es state público del driver, fácil de auditar en PR review, no requiere un
  archivo nuevo committeable. El `probe_field_type_map` los recorre y emite
  findings por cada discrepancia.

- **D-IOL-15:** **Tres clases de finding del `probe_field_type_map`** (todas con
  surface=both, status=OPEN):
  - `SHAPE` "missing assumed key `<key>` in `<endpoint>`" — el wire NO tiene la
    clave que el caller asume.
  - `SHAPE` "type drift on `<key>`: assumed `<expected>`, observed `<actual>`" —
    la clave existe pero el tipo cambió.
  - `SHAPE` "unexpected key `<key>` in `<endpoint>` not in caller assumptions" —
    el wire tiene una clave nueva (info only, candidato a extender callers; no
    es bug del cliente).
  La tercera (extra key) es información, no riesgo, así que se sub-clasifica como
  `actual=...` describing the key sin tocar OPEN (humano decide si registrar).

### Schema snapshots por endpoint (DRIFT-01 mirror)

- **D-IOL-16:** **4 snapshots committeable** en
  `.planning/verification/schemas/iol-client/`:
  - `get-quote.json` (símbolo GGAL como sample)
  - `get-historical-quotes.json` (rango fijo: últimos 5 días hábiles desde today)
  - `get-instruments.json` (pais=argentina)
  - `get-instruments-by-type.json` (instrument_type=acciones como sample)
  Todos con envelope D-21 (endpoint, client_function, captured_at, base_url,
  sample_params, schema). D-25 lifecycle: no-overwrite en drift, emite finding
  SHAPE OPEN.

- **D-IOL-17:** **Para `get_instruments_by_type`: un solo `instrument_type`
  (`acciones`) baseline + sanity check de los 6**. El driver:
  - Genera schema snapshot SÓLO con `acciones` (el más estable y de mayor
    cobertura).
  - Como sanity, llama los 6 types y compara que todos retornen una shape
    `list[dict]` (sin schema_of cada uno — sólo type assertion: `isinstance(list)`
    y `len(list) > 0` y `isinstance(list[0], dict)`). Si alguno difiere, emite
    finding `SHAPE` OPEN especificando el type.
  - Evita 6 GETs por type cada corrida (HTTP overhead) y 6 snapshot files que
    drift cada uno por separado.

### Endpoint sweep parameters (sample selection)

- **D-IOL-18:** **Símbolo fijo `GGAL`** para `get_quote` y `get_historical_quotes`.
  Stock líquido de BCBA, alta probabilidad de existir hoy, mañana y en N meses.
  Hardcoded en `main_iol.py` como constante `_SAMPLE_SYMBOL = "GGAL"`. País por
  defecto `"argentina"` para `get_instruments*`. Plazo por defecto `"t2"` para
  `get_quote` (default del cliente, sin override).

- **D-IOL-19:** **Rango histórico = `_last_business_day(today) - 5d` to
  `_last_business_day(today)`** — 5 días hábiles back, derivado de `today` (D-24
  Phase 2 mirror, sin anchors hardcoded). Suficiente para asertar shape `list[dict]`
  con `len >= 5` sin pegarle a una serie larga.

### Sync↔async parity (IOL-06)

- **D-IOL-20:** **`probe_parity_sync_async` compara estructura, no valores.** Para
  cada uno de los 4 endpoints:
  - Capturar el payload sync (de los probes 3/5/7/9).
  - Capturar el payload async (de los probes 4/6/8/10).
  - Comparar `schema_of(sync) == schema_of(async)` (estructural).
  - Comparar set de keys de top-level (`set(sync.keys()) == set(async.keys())` o
    para listas: shape estructural igual).
  - **NO comparar valores numéricos** — el precio cambió entre los dos calls
    si la sesión está abierta. Sólo shape.
  - Discrepancia → finding `SYNC-ASYNC-DRIFT` OPEN con detalle del endpoint.

### Verified-live tests + Regressions sections (D-08/D-09 Phase 2 mirror)

- **D-IOL-21:** En `packages/iol-client/tests/test_client.py` y `test_async_client.py`,
  agregar las **dos secciones verbatim**:
  - `# ------ Verified live (Phase 3) ------`
  - `# ------ Regressions ------`
  Lockear los invariantes mínimos (mocked, pytest-httpx):
  - IOL-02: URL exactas emitidas por cada endpoint (path + query string verbatim)
  - IOL-04: `get_instruments_by_type` unwraps `data["titulos"]` antes de retornar
    (test mockea `{"titulos": [...]}` y verifica que el cliente devuelve la lista
    sin el envelope)
  - IOL-04: campo numérico llega como float / int (test mockea `{"ultimoPrecio": 1234.5}`
    y verifica `isinstance(quote["ultimoPrecio"], (int, float))`)
  - IOL-04: el formato del path histórico es `YYYY-MM-DD/YYYY-MM-DD/sinAjustar`
    (test verifica URL exacta con day > 12 para evitar ambigüedad DD/MM)
  Regressions: IOL-07 tests del refresh_token (los 4 tests por surface descritos
  en D-IOL-12). Si aparecen findings nuevos durante el live run y son promovidos
  a FIXED, sus regression tests también van acá.

### Redaction + logging discipline

- **D-IOL-22:** Reuso de `safe_print(text, secrets=[...])` (D-26 Phase 2). La lista
  de secrets se inicializa al cargar el módulo con `[IOL_USER, IOL_PASSWORD]` desde
  env, y se EXTIENDE dinámicamente con `_refresh_token` tras el primer login. Si
  cualquier payload o exception incluyera estos valores, la línea stdout los
  enmascara.

### Claude's Discretion

Las siguientes decisiones quedan a discreción del implementador, ancladas a los
patrones LOCKEADOS arriba:

- Texto exacto de líneas verbatim del summary final (los conteos por estado siguen
  el formato Phase 2: `SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N`).
- Estructura interna de `_refresh()` y nombres exactos de los helpers privados
  (`_token_payload`, `_refresh_payload`, etc.).
- Cómo se distingue una rotación de refresh_token (server-side) vs no-rotación —
  el cliente lo acepta y guarda el nuevo si viene; sino, mantiene el existente.
- Tactic exacta de la cascade SKIPPED tras `login()` failure (D-IOL-3): un flag
  module-level `_auth_failed: bool` que cada probe checkea al inicio vs un wrapper
  decorator vs early-return en cada probe.
- Cómo el probe 14 (`probe_refresh_token`) verifica que el path de refresh
  funcionó (D-IOL-11 sugiere observar `_token` change + `_refresh_token` no None
  + nuevo `expires_at`; implementador puede usar otra heurística más limpia).
- Bounds plausibles para el sanity check de precios en `probe_get_quote` (e.g.,
  `0 < ultimoPrecio < 1_000_000` para detectar corrupción ×100 estilo AMB-02
  D-23). Discrecionalmente: si añadir o no este check; Phase 2 lo agregó para
  Ámbito porque el cliente parseaba el wire, pero IOL devuelve raw — el riesgo
  es menor.
- El timing exacto del `_token_expires_at = 0.0` injection en `probe_refresh_token`
  (antes o después de un call exitoso, si invalidar el token antes del call o
  forzarlo a expirar durante).
- Si `probe_get_instruments` debe samplear `pais="argentina"` solamente o también
  ejercitar el comportamiento ante un país inválido. D-IOL-13 sugiere que la
  rama de error queda fuera del scope vivo (riesgo de error rate count en el
  server).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements

- `.planning/ROADMAP.md` §"Phase 3: IOL Verification" — goal, mode (mvp), 5 success
  criteria, dependencies (Phase 2)
- `.planning/REQUIREMENTS.md` §"Verificación iol-client (IOL)" — IOL-01..07
  texto completo
- `.planning/REQUIREMENTS.md` §"Out of Scope" — anti-features (loops, retries,
  IP-ban/lockout risk)
- `.planning/REQUIREMENTS.md` §"Convención transversal" — fix dual sync+async
  con regresión mockeada por superficie
- `.planning/PROJECT.md` §"Key Decisions" — `main_*.py` como vehículo,
  dual sync/async, regresión mockeada por fix

### Phase 1 outputs (lockedados, base del harness)

- `.planning/phases/01-safety-harness-verification-infrastructure/01-CONTEXT.md` —
  D-01..D-16 del harness (drivers manuales, mockeados-only en CI, marker live,
  ubicación `verification/`, formato findings, lifecycle de status, pipeline
  capture→anonymize→fixture, schema_of, UA hardcodeado)
- `.planning/verification/FINDINGS-TEMPLATE.md` — plantilla con 7 clases fijas
  (SHAPE/AUTH/ERROR-MAP/PARAM/SYNC-ASYNC-DRIFT/NO-DATA/ANTI-BOT) y ciclo de
  estados (OPEN→CONFIRMED→FIXED + terminales EXPECTED/NO-FIX)

### Phase 2 outputs (lockedados, mismo lifecycle aplicado)

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
  Phase 3 hereda CR-01/CR-02/WR-04 fix del `append_finding` (preservación de
  prosa humana, validación de pkg slug, single-line title invariant) y WR-01/03/
  IN-03 patterns del driver (typed status_code, single HTTP call per probe,
  contextlib.suppress(Exception) en aclose)
- `verification/findings.py` — `append_finding(...)` con `_replace_art_block`,
  `_validate_pkg_slug`, validación CR-02; `_Finding` dataclass; lifecycle
  preservación de status humano (CONFIRMED/FIXED/EXPECTED/NO-FIX)

### Codebase maps

- `.planning/codebase/INTEGRATIONS.md` §"IOL" — auth OAuth password grant,
  endpoint `/token`, refresh_token expected pero no implementado, base default
  `https://api.invertironline.com`, riesgo de lockout
- `.planning/codebase/TESTING.md` — pytest config (`asyncio_mode = "auto"`,
  `--strict-markers`), pytest-httpx pattern (`url=` con full query string),
  autouse fixtures por paquete, convención `Regression: ... (issue #NNN)` →
  `(finding F-NN)` per D-07
- `.planning/codebase/CONVENTIONS.md` — naming, ruff line-length=100,
  double quotes, `from __future__ import annotations` obligatorio, mypy strict
- `.planning/codebase/CONCERNS.md` — IOL password-grant lockout risk explícito

### Implementación actual del cliente (target a verificar)

- `packages/iol-client/src/iol_client/client.py` — superficie sync; `login()`
  (líneas 85-110) actualmente NO captura `refresh_token` (bug IOL-07); `_request`
  con Bearer; `get_quote`, `get_historical_quotes`, `get_instruments`,
  `get_instruments_by_type` (líneas 140-208); `_DEFAULT_USER_AGENT` no
  hardcodeado (a diferencia de Ámbito — IOL no tiene anti-bot por UA)
- `packages/iol-client/src/iol_client/aio.py` — superficie async; mismo set de
  funciones espejado; `aclose()` para liberar el AsyncClient; `_token_lock` +
  `_client_lock` para serializar accesos concurrentes
- `packages/iol-client/src/iol_client/exceptions.py` — jerarquía:
  `IOLClientError` → `IOLAPIError` → (`IOLAuthError`, `IOLRateLimitError`).
  `IOLAPIError.__init__` siempre setea `self.status_code = status_code` —
  important para WR-01 mirror en probes (usar `.status_code` directo, no
  `args[0]` fallback)
- `packages/iol-client/src/iol_client/__init__.py` — `__all__` público:
  `configure`, `login`, `get_quote`, `get_historical_quotes`, `get_instruments`,
  `get_instruments_by_type`, 4 exceptions, `InstrumentType` literal
- `packages/iol-client/tests/conftest.py` — autouse fixtures
  `_configure_sync` / `_configure_async`; precarga `_token = "test-token"` y
  `_token_expires_at = 9_999_999_999.0` para evitar disparar login en endpoints
  autenticados durante tests
- `packages/iol-client/tests/test_client.py` — 8 tests mockeados pre-existentes;
  se le hace append de las secciones Verified-live + Regressions (D-IOL-21)
- `packages/iol-client/tests/test_async_client.py` — espejo async; idem
- `packages/iol-client/.env.example` — `IOL_USER`, `IOL_PASSWORD` requeridos;
  `IOL_BASE_URL` opcional

### Driver actual + harness ya construido

- `main_iol.py` — driver actual (smoke-test mínimo, sólo login()); se reescribe
  según D-IOL-5 con los 15 probes
- `verification/findings.py` — `append_finding(...)` ya hardened (CR-01/CR-02/
  WR-04 post-Phase-2 review); IOL driver lo usa directamente
- `verification/__init__.py` — barrel: `append_finding`, `Denylist`,
  `anonymize`, `capture`, `mutating_allowed`, `new_findings`, `redact`,
  `require_env`, `safe_print`, `schema_of`, `write_findings`
- `verification/schema.py` — `schema_of(payload)`: claves+tipos, PII-free por
  construcción (primitivo D-IOL-13)
- `verification/redaction.py` — `redact(value)`, `safe_print(text, secrets=[...])`
  (D-IOL-22)
- `verification/env_gate.py` — `require_env(pkg, [vars])`: skip-and-continue si
  faltan IOL_USER / IOL_PASSWORD (HARN-01)
- `conftest.py` (root) — `--live` flag, marker `live` registrado, deselect
  default; `sys.path` con repo root para `verification/` importable

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`verification.findings.append_finding`** — helper DRY committeado y hardened
  en Phase 2. IOL lo usa con `pkg="iol-client"`; idempotente por `fid`,
  preserva prosa humana en status promovidos, valida class/status/title/pkg
  slug.
- **`verification.findings.write_findings`** — esqueleto del findings file. No-op
  si existe; perfecto para idempotencia en runs sucesivos.
- **`verification.schema.schema_of`** — único primitivo para field→type maps
  (D-IOL-13). PII-free por construcción.
- **`verification.redaction.safe_print`** — con `secrets=[IOL_USER, IOL_PASSWORD,
  _refresh_token]` (D-IOL-22). El regex `_BEARER` interno cubre tokens reflejados
  aun sin secrets enumerados.
- **`verification.env_gate.require_env`** — el driver llama
  `require_env("iol-client", ["IOL_USER", "IOL_PASSWORD"])` al inicio; si
  faltan, imprime `SKIPPED iol-client: missing IOL_USER, IOL_PASSWORD` y exit 0.
- **`_last_business_day(today)` helper** — usado en Phase 2; copiar al
  `main_iol.py` para los probes de historical (D-IOL-19). Convención de fechas
  derivadas D-24 Phase 2.
- **pytest-httpx `httpx_mock.add_response(url=..., method=...)`** — patrón
  estándar de los tests existentes en `packages/iol-client/tests/`. Los nuevos
  Verified-live tests usan exactamente el mismo patrón con URL full incluyendo
  query string para `get_quote` y path completo para histórico.
- **Autouse fixtures `_configure_sync`/`_configure_async`** de
  `packages/iol-client/tests/conftest.py` — los Verified-live tests heredan el
  setup sin modificación. Para los tests de refresh_token (D-IOL-12), monkeypatch
  desactiva el precargado `_token` para que la rama de re-login se dispare.

### Established Patterns

- **Estado singleton a nivel de módulo** (`_base_url`, `_user`, `_password`,
  `_token`, `_token_expires_at`, `_client`) en `client.py` y `aio.py`. Phase 3
  agrega `_refresh_token` siguiendo el mismo patrón (D-IOL-8).
- **Doble superficie sync/async espejada** — todo fix de lógica (IOL-07 en
  particular) se duplica en `client.py` y `aio.py`. Los locks async son
  `_token_lock = asyncio.Lock()` y `_client_lock = asyncio.Lock()`; refresh
  debe respetarlos para evitar thundering herd.
- **`configure()` resetea estado cached** — patrón obligatorio: cualquier
  function nueva (`_refresh()`) que mute `_token` o `_refresh_token` debe
  invalidar coherentemente vía `configure()` reset semantics. Phase 2 ya lo
  ejercitó con `probe_antibot` cambiando `user_agent`.
- **Tests deterministas con `base_url="https://api.test"`** vía autouse fixture
  — los nuevos tests lo respetan.
- **`from __future__ import annotations`** al tope de todo módulo nuevo
  (CONVENTIONS.md). El nuevo `test_iol_invariants.py` (si hace falta para
  regression de driver invariants estilo Phase 2 IN-03) sigue la misma regla.
- **`ruff` line-length=100, double quotes, 4 espacios; `mypy --strict`** —
  todo código nuevo debe pasar antes de commit.
- **`contextlib.suppress(Exception)` para teardown** (Phase 2 IN-03) — el
  `_async_main` de IOL termina con
  `with contextlib.suppress(Exception): await aio.aclose()`.

### Integration Points

- **`main_iol.py`** — punto de entrada vivo de Phase 3; se reescribe (no archivo
  nuevo). Lifecycle análogo a Phase 2.
- **`packages/iol-client/src/iol_client/client.py` + `aio.py`** — reciben el fix
  IOL-07 (`_refresh_token` global, `_refresh()` privada, `_ensure_token()` con
  fallback dual). Mirror sync/async obligatorio.
- **`packages/iol-client/tests/test_client.py` + `test_async_client.py`** —
  append de las secciones Verified-live + Regressions (D-IOL-21) con los tests
  de IOL-04 + IOL-07.
- **`.planning/verification/iol-client-findings.md`** — generado por driver.
- **`.planning/verification/schemas/iol-client/`** — 4 snapshot files
  committeable (D-IOL-16).

</code_context>

<specifics>
## Specific Ideas

- **15 probes en orden D-IOL-5** — copiar la tabla literal arriba al planner.
- **`_SAMPLE_SYMBOL = "GGAL"`** (D-IOL-18) — constante module-level.
- **`_SAMPLE_INSTRUMENT_TYPE: InstrumentType = "acciones"`** (D-IOL-17) —
  baseline para schema snapshot. Sanity check de los 6 con type-only assertion.
- **Cascade SKIPPED helper** — un flag module-level `_auth_failed: bool = False`
  set por `probe_login_sync` / `probe_login_async`. Cada probe downstream
  checkea `if _auth_failed: return ProbeResult("<name>", "SKIPPED", "auth failed")`.
  Implementación discrecional (D-IOL-3 Discretion).
- **`probe_field_type_map` salida** — un solo probe que itera los 4 endpoints
  y emite un finding por discrepancia. ProbeResult final: `PROBE field_type_map:
  PASS` (si no hay drift) o `PROBE field_type_map: FINDING F-NN, F-MM (OPEN)`
  (lista de fids).
- **`probe_parity_sync_async` salida** — análogo: un solo probe que itera los 4
  endpoints. ProbeResult final: PASS si todos match; FINDING list si discrepan.
- **Verbatim status strings (heredados de Phase 2 D-02)**:
  - `PROBE <name>: PASS [<detail>]`
  - `PROBE <name>: FAIL [<detail>]`
  - `PROBE <name>: SKIPPED (<reason>)`
  - `PROBE <name>: FINDING <fid>[, <fid>...] (<status>)`
- **Summary final (heredado de Phase 2 D-02)**:
  `SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N`
- **`_refresh()` request shape** (OAuth-spec):
  `POST /token` con body
  `grant_type=refresh_token&refresh_token={_refresh_token}` y header
  `Content-Type: application/x-www-form-urlencoded`. Espera mismo payload
  shape `{access_token, refresh_token?, expires_in}`.
- **Plausibility check del precio en `probe_get_quote`** (Discretion):
  `0 < ultimoPrecio < 1_000_000` como bounds amplios; si está fuera → finding
  PARAM OPEN.

</specifics>

<deferred>
## Deferred Ideas

- **`get_quote` con múltiples símbolos** — Phase 3 verifica con GGAL solo; un
  pase paramétrico sobre N stocks sería un Phase 3.X o cycle posterior.
- **Verificación viva de `get_instruments_by_type` con los 6 InstrumentType**
  — Phase 3 hace 1 snapshot baseline + sanity type check de los 6 (D-IOL-17);
  drift detection per-type sería un cycle futuro.
- **Encoding del refresh_token como secret persistido** — Phase 3 lo mantiene
  in-memory only. Persistirlo a disco para reuso cross-process (tipo OAuth
  client) está fuera de scope.
- **Throttling / rate-limit-aware retries** en `_ensure_token` — fuera de
  scope (D-IOL-1 spirit: sin retry loops, sin sleeps).
- **Anonymize() para el payload de IOL** — IOL devuelve datos públicos de
  mercado (precios, símbolos) sin PII directa (no usernames, no balances).
  Las fixtures committeable son seguras as-is. `verification.capture` queda
  disponible para staging gitignored, pero `anonymize` no se ejercita.
- **Anti-bot probe** — IOL no implementa anti-bot vía UA filtering (a
  diferencia de Ámbito); no hay analog necesario.
- **Test de auth-once discipline mockeado** — los tests precargan `_token`
  via autouse fixture; un test que ejercita "una sola llamada a login() por
  N requests autenticados" sería verificación del fixture, no del cliente.
  Discrecionalmente puede agregarse pero no es load-bearing.
- **Plausibility bounds en `get_historical_quotes`** — análogo al check de
  `get_quote` pero sobre serie. Phase 3 valida shape únicamente; range checks
  sobre histórico quedan deferred.
- **Refactor a clase `Client` por instancia / deduplicación sync-async** —
  PROJECT.md lo marca explícitamente fuera de scope para todo el ciclo de
  verificación.
- **DRIFT-02 (informe consolidado per-package)** — anclado a Phase 5;
  Phase 3 produce su parte (findings + 4 snapshots + regression tests)
  pero el informe consolidado vive después.

</deferred>

---

*Phase: 03-iol-verification*
*Context gathered: 2026-06-06*
