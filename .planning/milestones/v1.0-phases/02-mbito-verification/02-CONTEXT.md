# Phase 2: Ámbito Verification - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase ejecuta el **primer ciclo end-to-end de verificación en vivo** del monorepo,
sobre el target de menor riesgo: `ambito-financiero-client`. Cierra el loop completo
**driver → finding → fix → mocked regression** sobre la única función pública del
paquete (`get_dollar_banco_nacion`) en sus dos superficies (`client.py` + `aio.py`),
y deja committeado el **primer schema snapshot estructural** (DRIFT-01) del monorepo.

**En alcance:**
- Ejercitar `get_dollar_banco_nacion` sync y async contra `https://mercados.ambito.com`
  cubriendo: happy path, paridad sync↔async, `parse_ar_decimal` adversarial (≥1000,
  detección de corrupción ×100), `NoDataError` para fecha sin cotización, probe
  anti-bot (UA default de httpx vs UA hardcodeado), y captura de schema estructural
- Auto-generar `.planning/verification/ambito-financiero-client-findings.md` desde
  `verification.findings` y poblarlo durante el run vía un nuevo helper
  `append_finding()` (extensión a `verification/findings.py`)
- Commitear el primer snapshot estructural en
  `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json`
- Codificar los invariantes verificados en vivo como tests mockeados nuevos en
  `packages/ambito-financiero-client/tests/test_client.py` y `test_async_client.py`
  (sección `# ------ Verified live (Phase 2) ------`)
- Para cada bug que llegue a `FIXED`: fix duplicado en `client.py` + `aio.py` y test
  de regresión mockeado por superficie en la sección `# ------ Regressions ------` con
  docstring `Regression: ... (finding F-NN)`
- Todo el suite mockeado + `mypy --strict` + `ruff check` deben pasar verdes

**Fuera de alcance:**
- Verificación en vivo de otros clientes (IOL, Higyrus, Matriz) — Phases 3-5
- Tests `@pytest.mark.live` propios de Ámbito (driver-only para vivo; el marker
  `live` registrado en Phase 1 queda disponible pero esta fase no escribe live tests)
- Modificación del marker / flag `--live` o cualquier cambio al harness ya
  construido en Phase 1 (verification/* + conftest.py + .gitignore + pyproject.toml)
- Cambios al pipeline `capture → anonymize → fixture` ya disponible — esta fase es
  el primer **uso** del pipeline, no su construcción
- Cubrir DRIFT-02 (per-package findings report final + cierre de fixes) —
  responsabilidad de Phase 5 según roadmap (DRIFT-02 anclado a Phase 5)
- Disparar 403/429 con loops o retries (anti-feature por riesgo de IP-ban)

</domain>

<decisions>
## Implementation Decisions

### Driver Structure & Output (`main_ambito_financiero.py`)

- **D-01:** Probes organizados como **sub-funciones nombradas** al tope del módulo
  (`probe_happy_sync`, `probe_happy_async`, `probe_parity_sync_async`,
  `probe_parse_decimal_adversarial`, `probe_no_data`, `probe_antibot`,
  `probe_schema_snapshot`). `main()` las invoca en orden. Self-contained,
  composable, fácil saltear una individual en debug. Marca el patrón para Phases 3-5
  con muchos más endpoints.

- **D-02:** Output a stdout = **plain text, una línea por probe + summary final**.
  Formato verbatim p.ej. `PROBE happy_sync: PASS`, `PROBE no_data: PASS`,
  `PROBE antibot: SKIPPED (opt-in via VERIFY_ANTIBOT=1)`,
  `PROBE parse_decimal: FINDING F-02 (OPEN)`. El summary final emite conteos por
  estado. Consistente con la convención verbatim `SKIPPED <pkg>: missing X, Y` de
  HARN-01; `main_verify.py` lo agrega sin parser nuevo.

- **D-03:** **Driver auto-genera el findings file**. El driver llama
  `write_findings("ambito-financiero-client")` al inicio (crea el esqueleto si no
  existe; no-op si existe) y usa el nuevo helper `append_finding(...)` (D-10) para
  agregar cada hallazgo OPEN detectado durante el run. El ART block del header se
  refresca con el timestamp/base_url del run actual.

- **D-04:** **El driver continúa todos los probes; exit 0 siempre**, salvo crash
  inesperado. Los hallazgos son el output esperado, no errores de proceso. Permite
  cubrir toda la superficie en un solo run aun con bugs presentes.

### Live Tests vs Driver-Only

- **D-05:** **Driver-only para verificación viva.** `main_ambito_financiero.py`
  hace TODOS los probes vivos, escribe findings, captura payloads y commitea el
  schema snapshot. Los únicos tests bajo `packages/ambito-financiero-client/tests/`
  son **mockeados**: invariantes lockeados + regresiones de bugs FIXED. Esto fija el
  patrón para Phases 3-5. (El marker `@pytest.mark.live` y el flag `--live` siguen
  registrados en `conftest.py` desde Phase 1 — disponibles para uso futuro, no
  ejercitados acá.)

- **D-06:** **Una regresión mockeada por superficie por bug FIXED**: un test en
  `test_client.py` (sync) + un test en `test_async_client.py` (async), aun si el bug
  se observó solo en una superficie. Refleja el constraint dual sync/async del
  proyecto (toda fix se espeja).

- **D-07:** Identificador en `Regression: ... (issue #NNN)` = **ID del finding**:
  `"""Regression: parse_ar_decimal rompe ante dot-decimal `1415.00` (finding F-02)."""`.
  El findings file (`.planning/verification/ambito-financiero-client-findings.md`)
  es la fuente de verdad; no hay dependencia de GitHub Issues.

- **D-08:** **Phase 2 agrega tests mockeados nuevos que codifican invariantes
  verificadas en vivo**, aun si no se encuentra ningún bug. Mínimo a codificar:
  - URL exacta emitida: `/dolarnacion/historico-general/YYYY-MM-DD/YYYY-MM-DD`
    (un caso con día > 12, p.ej. `2026-04-21/2026-04-21`)
  - Shape: la respuesta cruda es `list[list[str]]`, row 0 = header
    `["Fecha","Compra","Venta"]`, row 1+ = datos
  - `parse_ar_decimal("1.415,00") == 1415.0` (caso real ≥ 1000)
  - `get_dollar_banco_nacion(date)` levanta `AmbitoFinancieroNoDataError`
    cuando `len(rows) < 2`
  Si el cliente o el servidor drift en el futuro, estos tests rompen y avisan.

- **D-09:** Los tests nuevos viven en `test_client.py` y `test_async_client.py`
  **existentes**, con divisores de sección: `# ------ Verified live (Phase 2) ------`
  para invariantes y `# ------ Regressions ------` para regresiones de bug. Un
  archivo por superficie, una sola convención.

- **D-10:** **Phase 2 extiende `verification/findings.py` con
  `append_finding(...)`**. Firma propuesta (open detail a Claude):
  ```python
  def append_finding(
      pkg: str,
      *,
      fid: str,                  # "F-01", "F-02", ...
      class_: str,               # uno de FINDING_CLASSES
      surface: str,              # "sync" | "async" | "both"
      status: str,               # uno de STATUS_LIFECYCLE
      title: str,
      expected: str,
      actual: str,
      diff: str,
      regression: str | None = None,  # path al test si existe
  ) -> Path: ...
  ```
  Idempotente por `fid` (no duplica). Si el archivo no existe, crea el esqueleto
  primero. Re-runs convergen sin pisar status humanos ya promovidos
  (CONFIRMED/FIXED/EXPECTED/NO-FIX). Marca el patrón DRY para Phases 3-5.

- **D-11:** **Lifecycle async** en el driver: un único `asyncio.run(_async_main())`
  al final del driver. `_async_main` ejecuta los probes async en serie y termina
  con `await aio.aclose()`. Un solo event loop, cliente compartido, cierre limpio.

### Anti-Bot Probe Safety (AMB-06)

- **D-12:** **Opt-in via env var `VERIFY_ANTIBOT=1`**. Sin la var, el probe imprime
  `PROBE antibot: SKIPPED (opt-in via VERIFY_ANTIBOT=1)` y sigue. Mismo patrón que
  `VERIFY_MUTATING=1` (HARN-02). Reduce el riesgo de acumular 403s contra
  `mercados.ambito.com` desde la misma IP durante desarrollo iterativo.

- **D-13:** El probe anti-bot corre **último** en la secuencia del driver. Si una
  llamada con UA inválida resultara en un ban temporal, los probes anteriores ya
  emitieron sus resultados.

- **D-14:** **One-shot estructural, sin retry ni sleep.** Una sola llamada al
  endpoint con UA inválida. Si la respuesta es 403 (esperado) → finding
  `EXPECTED` terminal de clase `ANTI-BOT`. Si no es 403 → finding `OPEN` `ANTI-BOT`
  con la respuesta real observada (D-18). No hay reintento, no hay backoff.

- **D-15:** El probe usa `configure(user_agent=BAD_UA)` antes de la llamada y
  `configure(user_agent=GOOD_UA)` dentro de `try/finally` para restaurar el estado
  del módulo aun si la llamada lanza. Ejercita la API pública del cliente
  (`configure()` es la entrada diseñada para esto).

- **D-16:** **UA inválida = default de httpx**, `f"python-httpx/{httpx.__version__}"`.
  Es exactamente el caso que el docstring del cliente cita (`"La API responde 403
  con UA tipo python-httpx/..."`) y motivó hardcodear el UA de browser.

- **D-17:** **Solo sync** en el probe anti-bot. La defensa la implementa el
  servidor (filtro por UA), no es comportamiento dual del cliente. Una sola
  llamada con UA inválida alcanza. La paridad de `_raise_for_response` entre
  `client.py` y `aio.py` se verifica por code-read en el probe de paridad
  (`probe_parity_sync_async`), no por re-disparar el 403 dos veces a la misma IP.

- **D-18:** **Si la respuesta NO es 403** (200, 429, timeout, otro): registrar
  `OPEN ANTI-BOT` con `actual` = detalle exacto de la respuesta real. Cada caso
  significa algo distinto (defensa relajada / rate-limit / red), y se delega al
  humano la clasificación final a CONFIRMED/EXPECTED/NO-FIX.

### Schema Snapshot (DRIFT-01)

- **D-19:** **Ubicación**: `.planning/verification/schemas/<pkg>/<slug>.json`.
  Para Phase 2: `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json`.
  Coherente con `.planning/verification/<pkg>-findings.md` y
  `.planning/verification/captures/` (gitignored). Sub-dir por paquete, escala
  limpio para Phases 3-5.

- **D-20:** **Slug = nombre de función del cliente** (snake_case → kebab-case):
  `get-dollar-banco-nacion.json`. Estable, refleja el comportamiento público, no
  detalles del path del wire. Escala a clientes donde una función compone varios
  paths (IOL/Higyrus/Matriz).

- **D-21:** **Formato JSON con wrapper de metadata + schema** (un solo archivo):
  ```json
  {
    "endpoint": "/dolarnacion/historico-general/{from}/{to}",
    "client_function": "get_dollar_banco_nacion",
    "captured_at": "2026-05-29T...",
    "base_url": "https://mercados.ambito.com",
    "sample_date": "2026-05-21",
    "schema": [["str"]]
  }
  ```
  Diff-friendly, traceable a una corrida concreta. El campo `schema` es el output
  exacto de `verification.schema.schema_of(raw)` — PII-free por construcción.

- **D-22:** **Un solo archivo current por endpoint**; git history es la historia.
  Cada re-corrida regenera el snapshot (sujeto a D-25). Sin proliferación de files
  timestamped.

### AMB-02 — Detección de corrupción ×100 en `parse_ar_decimal`

- **D-23:** **Doble check**: estructural + sanity de rango.
  1. **Estructural:** el string crudo `venta` capturado en vivo debe contener `,`
     (separador decimal AR esperado). Si no contiene `,` → finding `PARAM` clase
     OPEN (`"wire emite dot-decimal en lugar de AR-decimal"`).
  2. **Rango plausible:** el float resultante de `parse_ar_decimal(venta)` debe
     estar en `100 <= venta_parseada <= 100000`. Si está fuera → finding
     `SHAPE`/`PARAM` OPEN. Bounds iniciales (margen amplio sobre USD/ARS histórico
     y futuro razonable); Claude puede ajustar durante implementación.
  Doble guarda contra el caso silencioso donde `"1415.00"` →
  `parse_ar_decimal` → `141500.0` (×100 corruption).

### Date Selection (probes)

- **D-24:** **Derivado de `today` con helpers determinísticos**, sin anchors
  hardcoded.
  - `probe_happy_sync` / `probe_happy_async` / `probe_schema_snapshot`:
    `_last_business_day(today)` (helper ya existente en `main_ambito_financiero.py`).
  - `probe_parse_decimal_adversarial`: cualquier día hábil reciente sirve
    (USD/ARS ~ 1000+; reusar la misma fecha que happy).
  - `probe_no_data`: fecha futura conservadora (`today + 60d` como draft).
  - **AMB-03 sample con día > 12**: helper nuevo
    `_last_business_day_with_day_gt_12(today)` que retrocede desde
    `_last_business_day(today)` hasta encontrar uno con `date.day > 12` — cubre el
    requisito de DD/MM-vs-MM/DD disambiguation sin anchor fijo.
  Cada run se mueve naturalmente con el calendario sin tocar código.

### Drift Detection en re-runs del schema snapshot

- **D-25:** Cuando el driver re-corre y el `schema_of` actual difiere del snapshot
  committeado, el driver:
  1. Emite finding `SHAPE` OPEN con `expected` = schema committeado y
     `actual` = schema de este run (vía `append_finding`).
  2. **NO sobreescribe el archivo** — deja el snapshot committeado intacto para
     revisión humana.
  El humano decide si commit la nueva versión (drift real → re-correr con
  `--accept-drift` o equivalente, detalle a Claude) o si investiga el cliente.
  Visibilidad máxima del drift, sin pisar evidencia.

### Redaction en este driver

- **D-26:** **`safe_print` con `secrets=()` por uniformidad cross-paquetes.**
  Ámbito no tiene credenciales (HARN-03 no aplica directo), pero pasar todos los
  prints del driver por `safe_print(text, secrets=())` mantiene el patrón uniforme
  para Phases 3-5 donde `secrets` se llena con `(IOL_PASSWORD, IOL_USER, ...)`.
  Permite extender la lista sin reescribir los call sites.

### Claude's Discretion

- Nombres exactos de las sub-funciones probe más allá de las convenciones
  citadas en D-01 (p.ej., `probe_parse_decimal_adversarial` vs
  `probe_parse_ar_decimal`).
- Texto exacto de las líneas de status a stdout más allá de los verbatim
  heredados de Phase 1 (`SKIPPED <pkg>: missing X, Y`).
- Estructura interna de `append_finding` (parser tactic del markdown, dedup
  por `fid`, lugar exacto del insert en el índice y la sección detalle).
- Bounds finales del sanity de rango plausible en D-23 (100/100000 son draft).
- Convención de filename de snapshot cuando un endpoint sea compartido por dos
  funciones del cliente (Phase 2 tiene una sola función — no aplica acá).
- Schema exacto (keys, order, naming) del JSON envelope de D-21.
- Fecha futura para `probe_no_data` (D-24 sugiere `today + 60d`).
- Mecánica del `--accept-drift` o equivalente en D-25 (env var, flag, edición
  manual del archivo).
- Si `append_finding` modifica o no el ART block del header en cada call (vs un
  helper separado `refresh_art_block`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 2: Ámbito Verification" — goal, mode (mvp), 5
  success criteria, dependencies (Phase 1)
- `.planning/REQUIREMENTS.md` §"Verificación ambito-financiero-client (AMB)" —
  AMB-01..06 texto completo
- `.planning/REQUIREMENTS.md` §"Detección de drift y cierre (DRIFT)" — DRIFT-01
  (primer snapshot real, anclado a Phase 2) y la nota cross-cutting
- `.planning/REQUIREMENTS.md` §"Out of Scope" — anti-features (nunca disparar
  403/429/5xx en vivo con loops, riesgo de IP-ban / lockout)
- `.planning/REQUIREMENTS.md` §"Convención transversal" — todo fix de lógica se
  espeja en `client.py` + `aio.py` con regresión mockeada
- `.planning/PROJECT.md` §"Key Decisions" — `main_*.py` como vehículo, dual
  sync/async, regresión mockeada por fix

### Phase 1 outputs (precedentes LOCK)
- `.planning/phases/01-safety-harness-verification-infrastructure/01-CONTEXT.md` —
  D-01 a D-16 del harness (drivers manuales, mockeados-only en CI, marker live,
  ubicación `verification/`, formato findings, lifecycle de status, pipeline de
  fixtures, schema-snapshot tooling, UA hardcodeado, etc.)
- `.planning/phases/01-safety-harness-verification-infrastructure/01-01-SUMMARY.md`
  — root conftest.py + `--live` flag, `verification/redaction.py`
- `.planning/phases/01-safety-harness-verification-infrastructure/01-02-SUMMARY.md`
  — `verification/env_gate.py` (require_env), `verification/mutation_gate.py`
- `.planning/phases/01-safety-harness-verification-infrastructure/01-03-SUMMARY.md`
  — `main_verify.py` agregador, gating de drivers, patrón de import zero-config
- `.planning/phases/01-safety-harness-verification-infrastructure/01-04-SUMMARY.md`
  — `verification/schema.py` (schema_of), `verification/capture.py`,
  `verification/anonymize.py`, `verification/findings.py`, `pythonpath=["."]`
- `.planning/verification/FINDINGS-TEMPLATE.md` — plantilla documentada de
  hallazgos clasificados (ART header, 7 clases fijas D-09, ciclo de estados D-08,
  pipeline capture → anonymize → fixture D-10/D-11)

### Codebase maps (estado actual del target)
- `.planning/codebase/INTEGRATIONS.md` — sección "Financial News Portal (Ámbito
  Financiero)": no-auth, browser UA hardcodeado, endpoint
  `/dolarnacion/historico-general/{from}/{to}`, base default `mercados.ambito.com`
- `.planning/codebase/TESTING.md` — pytest config (`asyncio_mode = "auto"`,
  `--strict-markers`), pytest-httpx pattern (`url=` con full query string),
  autouse fixtures por paquete, convención `Regression: ... (issue #NNN)` en
  docstring, async tests sin decorador
- `.planning/codebase/CONVENTIONS.md` — naming (snake_case, ruff line-length=100,
  double quotes, `from __future__ import annotations` obligatorio), mypy strict

### Implementación actual del cliente (target a verificar)
- `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` —
  superficie sync; `_DEFAULT_USER_AGENT` hardcodeado de browser; `configure()` con
  `base_url` y `user_agent`; `_raise_for_response` mapea 401/403→AuthError,
  429→RateLimitError, otros→APIError; `get_dollar_banco_nacion(date)` con
  `date.strftime("%Y-%m-%d")` en path y `parse_ar_decimal` sobre `rows[1][2]`
- `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py` —
  superficie async; `_client` lazy con `asyncio.Lock()`; `aclose()` para liberar
  el client; mismo `_raise_for_response` y misma lógica de
  `get_dollar_banco_nacion` espejada (deuda conocida: lógica duplicada)
- `packages/ambito-financiero-client/src/ambito_financiero_client/_parsing.py` —
  `parse_ar_decimal(value: str) -> float` con
  `float(value.replace(".", "").replace(",", "."))` (target de AMB-02)
- `packages/ambito-financiero-client/src/ambito_financiero_client/exceptions.py` —
  jerarquía: `AmbitoFinancieroClientError` → `AmbitoFinancieroAPIError`
  (`AmbitoFinancieroAuthError`, `AmbitoFinancieroRateLimitError`),
  `AmbitoFinancieroNoDataError`
- `packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py` —
  `__all__` público: `configure`, `get_dollar_banco_nacion`, 5 exceptions
  (`parse_ar_decimal` NO es público — internal helper)
- `packages/ambito-financiero-client/tests/test_client.py` — tests mockeados
  actuales (sync); se le hacen append los nuevos según D-08/D-09
- `packages/ambito-financiero-client/tests/test_async_client.py` — tests
  mockeados actuales (async); idem
- `packages/ambito-financiero-client/.env.example` — Ámbito no requiere creds;
  AMBITO_BASE_URL opcional

### Driver actual + harness ya construido
- `main_ambito_financiero.py` — driver actual (smoke-test mínimo); se reescribe
  según D-01..D-04 con los 7 probes
- `verification/__init__.py` — barrel: `Denylist`, `anonymize`, `capture`,
  `mutating_allowed`, `new_findings`, `redact`, `require_env`, `safe_print`,
  `schema_of`, `write_findings`
- `verification/findings.py` — `FINDING_CLASSES`, `STATUS_LIFECYCLE`,
  `findings_path`, `new_findings`, `write_findings` — Phase 2 extiende con
  `append_finding` (D-10)
- `verification/schema.py` — `schema_of(payload)`: claves+tipos, PII-free por
  construcción (D-12 de Phase 1)
- `verification/capture.py` — `capture(pkg, endpoint, payload)`: vuelca a
  `.planning/verification/captures/<pkg>-<endpoint>.json` gitignored
- `verification/anonymize.py` — `Denylist` + `anonymize(...)`: pipeline manual
  para fixtures committeables (Phase 2: probablemente no se necesita anonimizar
  porque las cotizaciones FX no son PII; se usa solo si algún payload trae datos
  sensibles)
- `verification/redaction.py` — `redact(value)`, `safe_print(text, secrets)`
  (D-26)
- `verification/env_gate.py` — `require_env(...)` (no necesario para Ámbito; sin
  creds)
- `conftest.py` (root) — `--live` flag, marker `live` registrado, deselect
  default; `sys.path` con repo root para que `verification/` sea importable

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`main_ambito_financiero.py:_last_business_day(today)`** — helper ya
  existente; se reutiliza tal cual para los probes happy/schema_snapshot y se
  extiende con `_last_business_day_with_day_gt_12(today)` (D-24).
- **`verification/__init__.py` barrel** — todos los helpers necesarios ya
  exportados; no requiere agregar nuevos exports salvo `append_finding`
  cuando se extienda `findings.py` (D-10).
- **`verification.schema.schema_of`** — único primitivo necesario para DRIFT-01;
  retorna `[["str"]]` para el payload de Ámbito; PII-free por construcción.
- **`verification.findings.new_findings` + `write_findings`** — esqueleto del
  findings file. `write_findings(pkg)` es no-op si el file existe, perfecto para
  ser idempotente en runs sucesivos.
- **`verification.capture.capture`** — útil opcionalmente para volcar el payload
  crudo de la respuesta de Ámbito al staging gitignored, si en algún momento se
  necesita reproducirlo como fixture mockeado.
- **Convención `Regression: ... (issue #NNN)` en docstring** (TESTING.md) — se
  adopta literal con `(finding F-NN)` por D-07.
- **pytest-httpx `httpx_mock.add_response(url=...)`** — los nuevos tests
  mockeados (D-08, D-09) usan exactamente este patrón con URL completa (incluye
  query string si la hubiere — Ámbito no tiene query params en el endpoint).
- **Autouse fixtures `_configure_sync`/`_configure_async`** existentes en
  `packages/ambito-financiero-client/tests/conftest.py` — los tests nuevos
  heredan el setup sin modificación.

### Established Patterns
- **Estado singleton a nivel de módulo** (`_base_url`, `_user_agent`, `_client`)
  en `client.py` y `aio.py`. El probe anti-bot toca este estado vía `configure()`
  con try/finally para restaurarlo (D-15).
- **Doble superficie sync/async espejada** — toda lógica nueva en `client.py` se
  espeja en `aio.py`; las regresiones (D-06) y los invariantes lockeados (D-08,
  D-09) siempre van en pares sync+async.
- **Tests deterministas con `base_url="https://api.test"`** vía autouse fixture —
  el patrón ya está en `tests/conftest.py`; los tests nuevos lo respetan.
- **`from __future__ import annotations` al tope** de todo módulo nuevo
  (CONVENTIONS.md).
- **`ruff` line-length=100, double quotes, 4 espacios; `mypy --strict`** — todo
  código nuevo debe pasar antes de commit.
- **PROJECT.md "no shared code between *publishable* packages"** — Ámbito no
  importa nada del resto del monorepo (correcto); el driver y `verification/`
  viven fuera de `packages/`.

### Integration Points
- **`main_ambito_financiero.py`** — único punto de entrada del flujo vivo de
  Phase 2; se reescribe (no archivo nuevo).
- **`verification/findings.py`** — recibe la nueva función `append_finding(...)`
  (D-10); el barrel `verification/__init__.py` debe re-exportarla.
- **`.planning/verification/`** — recibe el findings file
  `ambito-financiero-client-findings.md` (generado por driver) y el sub-dir
  `schemas/ambito-financiero-client/` con
  `get-dollar-banco-nacion.json` committeable.
- **`packages/ambito-financiero-client/tests/test_client.py` y
  `test_async_client.py`** — append de secciones nuevas.

</code_context>

<specifics>
## Specific Ideas

- **Probes del driver** (orden D-13, D-24 para fechas):
  1. `probe_happy_sync` — `get_dollar_banco_nacion(_last_business_day(today))`
     captura `rows` crudo + valor parseado, verifica shape `list[list[str]]`,
     header row 0 = `["Fecha","Compra","Venta"]`
  2. `probe_happy_async` — espejo async; comparte el `asyncio.run` global (D-11)
  3. `probe_parity_sync_async` — llama ambas superficies a la misma fecha y
     compara estructuralmente (mismo tipo, mismas claves, mismo float al
     parsear)
  4. `probe_parse_decimal_adversarial` — captura `venta_raw` del happy run,
     aplica doble check D-23 (estructural + rango), emite finding si falla
  5. `probe_no_data` — usa `today + 60d`; verifica que levanta
     `AmbitoFinancieroNoDataError`
  6. `probe_schema_snapshot` — calcula `schema_of(rows)`; si existe el archivo
     committeado, compara y emite finding SHAPE OPEN sin sobreescribir (D-25);
     si no existe, escribe el archivo con metadata D-21
  7. `probe_antibot` — gate `VERIFY_ANTIBOT=1`; `configure(user_agent=BAD_UA)`
     con try/finally; espera 403; clasifica resultado (D-14, D-18)
- **Verbatim status strings sugeridos** (ajustables por Claude):
  - `PROBE <name>: PASS`
  - `PROBE <name>: FAIL`
  - `PROBE <name>: SKIPPED (<reason>)`
  - `PROBE <name>: FINDING <fid> (<status>)`
- **AMB-03 sample con día > 12** — `_last_business_day_with_day_gt_12(today)`
  retrocede de `_last_business_day(today)` día a día hasta `date.day > 12`.
- **AMB-02 bounds plausibles draft** — `100 <= venta_parseada <= 100000`
  (USD/ARS histórico ~3 a futuro razonable; bounds amplios para no generar
  falsos positivos).
- **Metadata sample del schema snapshot** — el campo `sample_date` registra la
  fecha usada en el probe que generó el snapshot (típicamente la misma que
  `probe_happy_sync`).

</specifics>

<deferred>
## Deferred Ideas

- **Anonymize() para el payload de Ámbito** — las cotizaciones FX son
  información pública (sin PII); el pipeline `capture → anonymize → fixture` se
  ejercita en pleno en Phases 3-5 (Higyrus tiene cuentas/movimientos con PII
  real). En Phase 2 `verification.capture.capture` puede usarse opcionalmente
  para staging, pero `anonymize` no es necesario para generar fixtures
  committeables (el payload no tiene PII).
- **`@pytest.mark.live` tests para Ámbito** — disponibles para uso futuro
  (marker registrado en Phase 1) pero esta fase elige driver-only (D-05).
- **DRIFT-02 (informe final + cierre de fixes per-package)** — anclado a Phase 5
  por roadmap; cada fase produce su propio findings + regresiones + snapshot
  pero el informe consolidado vive después.
- **Mecánica de `--accept-drift`** en D-25 — Phase 2 implementa el flujo
  "detectar + no sobreescribir + emitir finding"; el comando para aceptar el
  drift como nueva baseline (env var, flag CLI, edición manual del JSON +
  re-corrida) queda a discreción de Claude durante implementación o de una fase
  futura si se vuelve recurrente.
- **Refactor a clase `Client` por instancia / deduplicación sync-async** —
  PROJECT.md lo marca explícitamente fuera de scope para todo el ciclo de
  verificación; los fixes de Phase 2 mantienen la duplicación espejada (D-06).
- **Disparar 403/429/5xx en vivo con loops** — anti-feature documentada en
  REQUIREMENTS Out of Scope; el probe anti-bot es one-shot por D-14.

</deferred>

---

*Phase: 02-mbito-verification*
*Context gathered: 2026-05-29*
