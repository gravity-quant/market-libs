# Phase 8: Retries, Backoff, Structured Logging - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 8 entrega dos capacidades indivisibles sobre los 4 paquetes (ámbito, iol, higyrus, matriz) construidas encima de los shells transport de Phase 7:

1. **Reliability (RELY-01..04)** — `RetryTransport(httpx.HTTPTransport)` (sync) + `RetryTransport(httpx.AsyncHTTPTransport)` (async) por paquete con:
   - Retry sobre `408/409/429/≥5xx` HTTP + `httpx.ConnectError`/`ConnectTimeout`/`ReadTimeout`
   - Backoff exponencial full-jitter (base=1s, max=30s, exp=2) — `random.uniform(0, min(max, base*2^attempt))`
   - `Retry-After` honored con cap 60s
   - Mutation gate vía `request.extensions["idempotent"]` (set por shell `_request()` desde `RequestSpec.idempotent`); POST/PATCH NUNCA retry sin `idempotent=True`
   - 401 re-auth exactly-once en el shell `_request()` (no en transport): try parse → `AuthError` → `state.token=None` → `_ensure_token()` → 1 retry
   - `AuthError`/`PrimaryAPIError`/`<Pkg>APIError` NUNCA entran al `retry_on=`

2. **Observability (LOG-01..03)** — `_logging.py` por paquete con:
   - `logging.getLogger("<pkg>")` + `NullHandler` adjuntado en `__init__.py`
   - `RedactingFilter(logging.Filter)` per paquete (duplicado 4×, NO importable de `verification/`) que reescribe `record.msg` + `record.args` + `record.__dict__` in-place; cubre Bearer, X-Auth-Token, `password=`, `refresh_token=`, JSON `{"password":"..."}`, IOL refresh_token, matriz auth_basic password
   - Niveles roadmap mínimo: DEBUG req/resp (sin body, sin headers), INFO auth events, WARNING retry attempts, ERROR terminal failures
   - Structured fields obligatorios: `package`, `method`, `url` (query-redacted), `status_code`, `attempt`, `duration_ms`, `request_id` (UUID4 per business-call), `endpoint_name`; `account_id` cuando aplique (higyrus, matriz)
   - Library NO toca loggers `httpx`/`httpcore` (consumer decide)

3. **Public API surface mínima** — `Client/AsyncClient.__init__` + `configure()` por paquete extienden con 2 nuevos kwargs:
   - `max_retries: int = 2` (subject to tuning; `max_retries=0` disable retries completamente)
   - `http_client: httpx.Client | None = None` (test injection; usado AS-IS sin auto-wrap del transport — caller responsible)

**Orden serial per-package locked:** ámbito → iol → higyrus → matriz (idem Phase 6 D-05 / Phase 7 D-13). Cada paquete = 1 commit atómico (retries + logging + tests + snapshot update + Client/AsyncClient/configure() extension).

**Phase 8 NO entrega:**
- `matriz_client/aio.py` REST surface (Phase 10 REFAC-04 + TokenStore)
- `matriz_client/_atransport.py` (Phase 10 lo crea junto con aio.py REST)
- Deferred bug fixes (F-09 matriz ERROR-MAP, F-02 higyrus, IOL refresh persistence, HIGY multi-account) → Phase 9
- TokenStore 3-way concurrent (Phase 10, spike-findings validados)
- `client.with_options()` per-call override → v1.2+ backlog
- `request_id` enviado via `X-Request-ID` header al server → v1.2+

**Carry-forward Phase 7:**
- `RequestSpec.idempotent: bool = False` ya forward-declared en los 4 RequestSpecs (D-13 Phase 7). Phase 8 lo wirea y agrega defaults `True` a los GET endpoints + login/refresh.
- `_core.py` per paquete ya existe (builders+parsers). Phase 8 NO toca `_core.py` excepto: agregar `RequestSpec.account_id: str | None = None` opcional a higyrus + matriz RequestSpec; marcar `idempotent=True` en `build_<endpoint>_request` para GETs + login/refresh.
- `import-linter` rule (D-09 Phase 7) sigue activa: `_core.py` no puede importar `client.py`/`aio.py`/`_transport.py`/`_atransport.py`.
- B8 alias pattern (`_raise_for_response`, matriz `_unwrap`) intacto.
- Snapshot público (Phase 6 D-09): Phase 8 actualiza per-paquete agregando solo los 2 nuevos kwargs (max_retries, http_client) en Client/AsyncClient/configure() signatures.

</domain>

<decisions>
## Implementation Decisions

### Retry mechanism + 401 boundary

- **D-01: RetryTransport como `httpx.HTTPTransport` subclass per-paquete.** Sync = `_transport.py::RetryTransport(httpx.HTTPTransport)`; async = `_atransport.py::AsyncRetryTransport(httpx.AsyncHTTPTransport)`. Cada uno wraps el underlying transport. Gate de mutación vía `request.extensions["idempotent"]` seteado por el shell `_request()` pre-send (lee de `RequestSpec.idempotent`). El transport ve solo status codes / network errors — NUNCA domain exceptions. Composable via `httpx.Client(transport=...)`. Research SUMMARY §Architecture: este es el patrón locked.

- **D-02: 401 re-auth en el shell `_request()` del Client (no en el transport).** Patrón: `resp = self._http.send(req); try: _raise_for_response(resp) except <Pkg>AuthError: self._state.token = None; self._ensure_token(); req.headers["Authorization"] = ...; resp = self._http.send(req); _raise_for_response(resp); return resp`. Exactly-one re-auth attempt. `AuthError` NUNCA entra al `retry_on=` del transport (Pitfall 5 prevention). 401 sobre POST con `idempotent=False`: re-auth+retry-once IGUAL sucede (el 401 NO es "mutación confirmada"; el server rechazó pre-processing).

- **D-03: Auth-flow request (login, refresh) marcado `idempotent=True`.** `_core.build_login_request(state)` y `_core.build_refresh_request(state)` (iol) setean `RequestSpec.idempotent=True` explícito. El POST de auth-flow se retry-a en 5xx/429/connection-errors como un GET. Justificación: login = "give me un token con estas credentials" → replay-safe semánticamente. Cubre el caso transient-auth-server-blip. Aligned con spike-findings 003 RefreshPolicy pattern para Phase 10.

- **D-04: Retry-After cap 60s + cap-then-retry behavior.** Si server responde `Retry-After: <delta-seconds>` o `Retry-After: <HTTP-date>` con valor > 60s, el RetryTransport hace `sleep(60s)` y retry. Si el server insiste con 429, agota `max_attempts` y propaga `RateLimitError`. Coherente con la semántica "transparente" del retry. AWS Architecture Blog recomienda cap como jitter ceiling.

- **D-05: Retry exhaust → APIError/RateLimitError nativo del response final.** Zero-surface-change. El último response pasa por `_raise_for_response` normal y surfacea como `APIError(503)` / `RateLimitError` igual que sin retry. NO se introduce `RetryExhaustedError` ni `.attempts` attribute. El log WARNING per attempt + ERROR terminal cuenta la historia completa. Pattern aligned con anthropic/openai SDK.

- **D-06: max_attempts default uniforme = 2 cross-paquete.** Total req count = 2 (1 inicial + 1 retry). Cap conservador alineado con anthropic/openai SDK. Mismo valor para los 4 paquetes (ámbito incluido — aunque sin auth, sus endpoints público scrape pueden ser flaky). Override per-instance via `Client(max_retries=N)` o `configure(max_retries=N)`. No per-call override (D-13).

- **D-07: `retry_on=` set lockeado del roadmap.** Status codes: `408, 409, 429`, todos `≥500`. Exceptions: `httpx.ConnectError`, `httpx.ConnectTimeout`, `httpx.ReadTimeout`. NUNCA: `<Pkg>AuthError`, `<Pkg>APIError`, `PrimaryAPIError`, `HigyrusAPIError`, `ValueError`, `RuntimeError`. RFC 9110 + httpx transport errors canónicos.

- **D-08: Backoff full-jitter, base=1s, max=30s, exp=2.** Cada attempt: `delay = random.uniform(0, min(max, base * 2^attempt))`. Attempt 1 → 0–2s, attempt 2 → 0–4s, capped at 30s. Alineado con `tenacity.wait_exponential_jitter`. Mismo patrón que RefreshPolicy del spike 003 (`base_backoff_s=1.0`, `max_backoff_s=30.0`). Para `max_attempts=2` efectivamente 1 retry con delay ≤ 2s normalmente.

### Logging structure

- **D-09: Field set canónico (8 obligatorios + 1 condicional).** Cada log record carries: `package`, `method`, `url` (query string scrubbed para PII tipo cuit higyrus), `status_code`, `attempt`, `duration_ms`, `request_id`, `endpoint_name`. Condicional: `account_id` (higyrus + matriz, vía `RequestSpec.account_id`). El `request_id` se genera UNA vez en `_request()` pre-send y persiste cross-retry-attempts (D-14). El `endpoint_name` se extrae del builder name (e.g., `get_segments`) — propagado por `RequestSpec.endpoint_name: str` (nuevo field).

- **D-10: `RedactingFilter(logging.Filter)` en `_logging.py` per paquete.** Cada `__init__.py` adjunta el filter al `getLogger(<pkg>)` + `NullHandler`. El filter reescribe `record.msg` (si es str con template), `record.args` (tuple/dict), y `record.__dict__` values con regex pass: Bearer pattern, X-Auth-Token, `password=`, `refresh_token=`, JSON `{"password":"..."}`, IOL refresh_token, matriz auth_basic password. Duplicado 4× verbatim (NO importable de `verification/`). Pitfall 7 prevention: caplog regression test verifica que el token literal NO aparece en ningún `record.getMessage()` incluso con consumer en DEBUG.

- **D-11: `account_id` propagation vía `RequestSpec.account_id`.** Nuevo field opcional `account_id: str | None = None` en higyrus + matriz `RequestSpec` (ambito/iol mantienen su shape). Builder `build_<endpoint>_request(state, ..., id_cuenta=X)` setea `account_id=X`. Transport copia `spec.account_id` a `extra={"account_id": ...}` si non-None. Zero-leak: si el caller no pasa id_cuenta, no se loguea.

- **D-12: Niveles roadmap mínimo.** DEBUG: cada request out + response in con fields canónicos solamente (sin body, sin headers). INFO: auth events (login start, login success, token refresh start/success). WARNING: cada retry attempt (con `retry_reason` field: `"5xx"`, `"429"`, `"connect_error"`, `"401_reauth"`, attempt N/max). ERROR: terminal failures (post retry exhaust o AuthError final). Sin opt-in adicional para bodies/headers (defer to v1.2).

- **D-13: Un logger por paquete = `logging.getLogger("<pkg>")`.** Sin sub-loggers por concern (no `<pkg>.transport`, no `<pkg>.auth`). Consumer setea level con un solo statement: `logging.getLogger("matriz_client").setLevel(DEBUG)`. 4 loggers total cross-monorepo.

- **D-14: Library NO toca loggers `httpx` ni `httpcore`.** Consumer decide. Aligned con Pitfall 6 (library no toca root ni 3rd-party). Zero hijacking risk. Si consumer quiere DEBUG en httpx, lo hace explícito.

### Public API surface

- **D-15: Extender mínimo `Client/AsyncClient.__init__` + `configure()` con 2 kwargs.**
  - `max_retries: int = 2` — disponible en los 4 paquetes (ámbito incluido para consistencia)
  - `http_client: httpx.Client | None = None` (Client) / `httpx.AsyncClient | None = None` (AsyncClient) — test injection sin monkeypatch transport (research P2)
  - NO se exponen `retry_backoff_*`, `retry_jitter`, `retry_on=` — esos quedan literal en `_transport.py`/`_atransport.py` per paquete.
  - NO se expone `log_level` (D-17).

- **D-16: `http_client=` use AS-IS, caller responsible.** Si el caller pasa `http_client=httpx.Client(transport=...)`, el paquete lo usa tal cual sin envolver con RetryTransport. Use cases: (a) tests con `MockTransport`/`pytest-httpx` — zero retry magic; (b) custom transport por compliance/proxy. Power-user path. Docstring documenta el contrato.

- **D-17: Drop `log_level` del kwarg set.** Consumer hace `logging.getLogger("<pkg>").setLevel(...)` directo. Patrón stdlib normal. Setear level de un logger global desde dentro del paquete es side-effect-on-shared-resource (Pitfall-adjacent). Recommended set quedó: `max_retries` + `http_client`.

- **D-18: `max_retries` solo Client/configure() level (no per-call).** Locked en construcción de la instancia. Para customizar, caller crea nuevo `Client(max_retries=N)`. NO `Client.with_options(max_retries=N)` ni `get_X(*, max_retries=None)`. with_options() queda P2 backlog (v1.2+). 1 Client = 1 retry policy.

- **D-19: `max_retries=0` disable retries completamente.** Transport hace bypass del retry loop → 1 outgoing request total. Uso: test fixtures, debugging, opt-out global via `configure(max_retries=0)`. Semántica natural: N retries adicionales.

- **D-20: Default = `subject to tuning`.** Docstring de `Client.__init__` y `configure()` documenta `default=2; subject to change in future minor versions for tuning`. Aligned con anthropic SDK. No BC promise on default. Caller que necesite valor fijo: `Client(max_retries=2)` explicit.

### Plan slicing & guard tests organization

- **D-21: 6 planes en la phase (per-package serial idiom Phase 6/7).** Total:
  - **Plan 1 — Infra cross-cutting (tests-first, NO toca paquetes):** `RetryTransport` scaffold genérico documentado + `_logging.py` template + guard tests cross-cutting en `verification/` (mutation gate, 401→200 chain, no-token-en-caplog, `logging.root` unchanged) parametrizados sobre 4 paquetes (matriz async branch skipped, ver D-25) + ruff custom rule (o equivalente) contra `logging.basicConfig`/`logging.root` en `packages/*/src/`. Tests fallan rojo en HEAD esperando la infra de Plans 2-5.
  - **Plan 2 — RELY+LOG ámbito (canary):** `ambito_financiero_client/_transport.py` + `_atransport.py` + `_logging.py` + Client/AsyncClient/configure() extension + snapshot update + tests. ámbito sin auth, sin account_id, sin Risk API — el canary más simple antes de iol/higyrus/matriz.
  - **Plan 3 — RELY+LOG iol:** + auth-flow `idempotent=True` (login + refresh-with-password-fallback) + RedactingFilter cubriendo IOL refresh_token + 401 re-auth path via `_ensure_token()`.
  - **Plan 4 — RELY+LOG higyrus:** + RequestSpec.account_id + RedactingFilter cubriendo Higyrus JSON password + url query-redaction (cuit PII) + 401 re-auth.
  - **Plan 5 — RELY+LOG matriz (sync-only):** + `matriz_client/_transport.py` ONLY (NO `_atransport.py`, D-25) + RequestSpec.account_id + auth_basic redaction (D-22) + Risk API 401-no-reauth path (D-23) + status=ERROR no-retry guard (D-24) + cross-leak sentinel update.
  - **Plan 6 — CI green gate consolidation:** full pytest + ruff + mypy strict + import-linter + cross-leak sentinel + lint-imports + new logging.root regression + retry mutation gate parametrizado + 401 chain parametrizado en matriz Python 3.12 + 3.13. Mismo patrón Phase 6 Plan 7 / Phase 7 Plan 6.

- **D-22: matriz auth_basic redaction policy.** RedactingFilter detecta `auth_basic` field en `record.__dict__` o `Authorization: Basic ...` en headers (cuando se loguee). Loguea `auth_basic_user=<user>` y `auth_basic_password='<redacted>'`. Si el record tiene `auth_basic` tuple en extra, lo splittea a `auth_basic_user` + redacted password. Aligned con Phase 6 D-18 (`Client.__repr__` credentials redaction).

- **D-23: matriz Risk API — RetryTransport sí, 401 re-auth NO.** Risk API requests pasan por el mismo `state.http_client` (mismo RetryTransport) y reciben 5xx/429/connection retry como Primary. PERO el 401 re-auth path NO aplica: Risk auth_basic NO tiene token a refrescar; un 401 de Risk = credenciales inválidas → `AuthError` inmediato. El shell `_request()` detecta vía `spec.auth_basic is not None` (Risk path) y skip re-auth attempt. Caller ve AuthError directo. Implementación: branch en el except `<Pkg>AuthError` del shell — si `spec.auth_basic`, re-raise sin retry.

- **D-24: matriz 200-OK con `status=="ERROR"` NUNCA retry.** `PrimaryAPIError` NUNCA entra al `retry_on=` (D-07, roadmap LOCK). Independiente del description (transient/permanent). Caller decide después del raise. Razones: (1) status==ERROR es application-level (la API ya procesó el request — retry no cambia outcome); (2) parsing "transient" del free-text description es frágil; (3) caller-determined retry preserva agency. Aligned con Pitfall 15. `_core.parse_envelope_response` (D-06 Phase 7) sigue tal cual — body-consume-then-raise PrimaryAPIError.

- **D-25: matriz `_atransport.py` NO se crea en Plan 5.** Phase 10 (REFAC-04) lo creará cuando tape el aio.py REST surface. Phase 8 entrega solo `matriz_client/_transport.py` (sync). Snapshot público de matriz: solo Client gana `max_retries` + `http_client` kwargs; AsyncClient (stub Phase 6) mantiene su signature actual. Plan 5 SUMMARY.md documenta "forward ref Phase 10". Guard test parametrizado en `verification/` usa `pytest.skip("matriz aio.py REST stub hasta Phase 10")` para el async branch (mismo patrón Phase 7 D-11).

- **D-26: Guard tests cross-cutting en `verification/` parametrizado.** Archivos nuevos:
  - `verification/test_retry_mutation_gate.py` — parametrize × 4 paquetes; mock 503 sobre POST sin `idempotent=True` y assert exactly 1 outgoing request. Mock 503 sobre GET (idempotent default `True` post-Phase-8) y assert N attempts.
  - `verification/test_retry_401_reauth.py` — parametrize × paquetes con auth (iol/higyrus/matriz). Mock 401→200 chain y assert 2 outgoing requests + headers refrescados. Mock 401→401 chain y assert exactly 2 requests + AuthError raised.
  - `verification/test_logging_root_unchanged.py` — record `logging.root.handlers` antes; importar los 4 paquetes; assert unchanged. Cross-cutting unique test (no parametrize necesario).
  - `verification/test_logging_no_token_leak.py` — caplog x 4 paquetes; configure(token=`"SECRET-LITERAL-12345"`); fire request mockeado; assert NO record contiene la string literal en ningún `getMessage()`/`args`/`extra` value.
  - `verification/test_retry_after_cap.py` — mock 429 con `Retry-After: 600`; assert delay ≤ 60s + retry happens. Cross-cutting.
  - `verification/test_async_cancellation.py` — parametrize × paquetes con async (ambito/iol/higyrus); matriz skip. `asyncio.wait_for(client.get_X(), timeout=0.5)` cuando server mockea 503→503; assert TimeoutError no espera retry completo.

- **D-27: CI grep rule via ruff custom config (o equivalente).** Implementación a discreción del planner: (a) ruff rule extension via `flake8-logging` plugin (`LOG001`/`LOG002`), o (b) plain grep step en `.github/workflows/ci.yml` lint job (`! grep -rn 'logging\.basicConfig\|logging\.root' packages/*/src/`), o (c) pytest regression usando `inspect` (D-26 ya cubre `logging.root.handlers` unchanged). Preferencia: si ruff soporta nativamente, esa via; sino plain grep. Aligned con import-linter pattern de Phase 7 D-09 (declarative en pyproject.toml o yaml).

- **D-28: Snapshot público update per-plan atómico.** Mismo idiom Phase 6 D-06: cada Plan 2-5 actualiza su `verification/snapshots/<pkg>-surface.txt` agregando los 2 kwargs nuevos (`max_retries`, `http_client`) en signatures de `Client.__init__`, `AsyncClient.__init__`, `configure()` (los 3). Nunca remueve entries. Plan 6 green gate corre diff vs baseline Phase 7 que solo los kwargs nuevos aparecen. Forensic-localizable via `git log -- verification/snapshots/<pkg>-surface.txt`.

### `_ensure_token()` × RetryTransport × request_id

- **D-29: Login va por el mismo state.http_client (atraviesa RetryTransport).** `_ensure_token()` hace `httpx.Client.send(login_request)` via `state.http_client` que YA tiene RetryTransport instalado. El `build_login_request` marca `idempotent=True` (D-03). 5xx/connection transient → retry. 401 → AuthError inmediato (no retry). NO hay recursión infinita porque el 401 re-auth en shell (D-02) solo se intenta UNA vez. Si ese login 401, AuthError final. Risk API similar pero sin re-auth (D-23).

- **D-30: `request_id` per business-call (cross-retry-attempts).** `_request()` genera `request_id = uuid.uuid4().hex` UNA vez antes del primer send. Pasado al RetryTransport via `request.extensions["request_id"]`. Todos los retry attempts del mismo request comparten el `request_id` — grep correlation natural. El `attempt` field (1, 2, ...) distingue. NO se envía al server (no `X-Request-ID` header — defer to v1.2). Anthropic SDK pattern. Test (D-26): caplog assert same `request_id` across 2 attempts.

### tenacity integration shape

- **D-31: `Retrying` / `AsyncRetrying` como iterator dentro de `handle_request`.** Patrón:
  ```python
  def handle_request(self, request):
      for attempt in Retrying(
          stop=stop_after_attempt(self.max_attempts),
          wait=wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0),
          retry=retry_if_exception_type(_RETRYABLE_EXC) | retry_if_result(self._is_retryable_status),
          reraise=True,
      ):
          with attempt:
              response = self._inner.handle_request(request)
              response.read()
              if self._is_retryable_status(response):
                  raise _RetryableStatus(response)  # internal sentinel
              return response
  ```
  Async equivalent con `AsyncRetrying` + `async for`. Logging WARNING per attempt vía `attempt.retry_state` inspect (tenacity expone `attempt_number`, `next_action`, `outcome.exception()`). Sentinels privados (`_RetryableStatus`) NO heredan de `<Pkg>APIError` para evitar collision con D-07.

- **D-32: `asyncio.CancelledError` respect via `asyncio.sleep`.** `AsyncRetryTransport` backoff usa `await asyncio.sleep(delay)`. `asyncio.CancelledError` se propaga normalmente. tenacity `AsyncRetrying` lo soporta out of the box. Test (D-26): `asyncio.wait_for(client.get_X(), timeout=0.5)` cuando 503+503 mockeado → TimeoutError sin esperar retry completo. Pitfall 16 prevention.

### Claude's Discretion

El planner decide:

- **Ubicación exacta del state shared.** `_transport.py` y `_logging.py` viven en `packages/<pkg>/src/<pkg>/` (private modules). Si el planner ve valor en factorizar comunes a `_transport_base.py` PER PAQUETE (duplicado 4×, no shared internals), OK. Preferencia: cada paquete tiene los 2 archivos (`_transport.py`, `_logging.py`) self-contained.
- **Estructura interna de `RetryTransport`.** Sentinel exception name (`_RetryableStatus` vs `_TenacityRetryFlag`), uso de `retry_if_exception_type` vs `retry_if_exception` vs `retry_if_result` — research RESEARCH.md de la phase guía. Phase 8 D-31 da el shape; el planner ajusta detalle.
- **Naming exact de los nuevos fields del `RequestSpec`.** Phase 8 agrega: `account_id: str | None = None` (higyrus + matriz), `endpoint_name: str` (los 4 paquetes). El nombre exacto puede ser `endpoint: str` si el planner ve más natural — mantener consistente cross-paquete.
- **Snapshot del Retry-After parsing.** RFC 7231 §7.1.3 soporta `delta-seconds` (int) y `HTTP-date` (RFC 1123). Parser puede usar `email.utils.parsedate_to_datetime` para HTTP-date. El planner decide si soportar ambos formatos día 1 o solo delta-seconds (más común). Recommendation: solo delta-seconds + log WARNING si HTTP-date detectado (forward-compat).
- **Logging formatter en testing.** caplog default mode capta records pero NO aplica filters por defecto en algunas versiones de pytest. Planner verifica que `caplog.set_level(logging.DEBUG, logger="<pkg>")` + filter attached funciona en pytest 8.3 (D-10 test scenario).
- **Exact `extra={}` field naming inside the transport.** `attempt` vs `retry_attempt` vs `attempt_number` — planner picks consistent name cross-paquete. Recommendation: `attempt` (matches tenacity's `attempt_number` semantically, shorter).
- **Test cadence per plan.** `uv run pytest packages/<pkg>/` + `uv run pytest verification/test_retry_*.py verification/test_logging_*.py` + `uv run pytest verification/test_public_surface.py verification/test_sync_async_isolation.py` + `uv run lint-imports` pre-commit. Mismo idiom Phase 7 D-13.
- **ruff vs grep vs flake8-logging para D-27.** El planner valida si ruff 0.7+ soporta `flake8-logging` rules out-of-box (LOG001/LOG002). Si sí, usar ruff. Sino, plain grep step en CI.

### Folded Todos

- **matriz-driver-findings-file-handling** (score 0.6) — el todo refers a HARN-07/08/10 (Phase 11). NO se folda en Phase 8; se mantiene en `.planning/todos/pending/` para Phase 11. Reviewed but not folded (ver Reviewed Todos en `<deferred>`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & milestone

- `.planning/PROJECT.md` — v1.1 milestone goals, scope, key decisions; menciona retries/backoff + structured logging como targets del milestone; constraint "no shared internals between packages" (justifica D-10 RedactingFilter duplicado 4×).
- `.planning/REQUIREMENTS.md` §"Reliability — retries + backoff (RELY)" — RELY-01/02/03/04 son los reqs principales de retries; §"Structured logging (LOG)" — LOG-01/02/03 son los reqs de logging; §"Future Requirements (Defer to v1.2+)" — `client.with_options(max_retries=N)`, `Client.from_env()`, `request_id` via header — confirma D-18, D-30 deferrals.
- `.planning/ROADMAP.md` §"Phase 8" — goal + 5 success criteria explícitos; §"Phase 7" para entender baseline (RequestSpec.idempotent ya forward-declared); §"Phase 9/10" para entender forward-references (Phase 9 BUGs lands sobre Phase 8 retry+logging infra; Phase 10 crea `_atransport.py` matriz + TokenStore).
- `.planning/STATE.md` §"Decisions" — Mutation gate mandatory; AuthError nunca en retry_on=; §"Blockers/Concerns" §"Phase 8" — Pitfall #4 (retry de mutating POST) y Pitfall #6 (library logging.basicConfig) marcados como gates de merge.

### Prior phase (Phase 7, handoff)

- `.planning/phases/07-core-py-extraction-sync-async-logic-dedup/07-CONTEXT.md` — D-13 (RequestSpec.idempotent forward-decl), D-09 (import-linter rule), D-10 (cross-leak sentinel test parametrizado), D-04 (B8 alias pattern), D-06 (`parse_envelope_response` body-consume CR-03 closure — Phase 8 NO toca esto), D-16 (snapshot público scope: `_core.py` private).
- `.planning/phases/07-core-py-extraction-sync-async-logic-dedup/07-RESEARCH.md` — patterns base de `_core.py` que Phase 8 consume; no se duplica.
- `.planning/phases/07-core-py-extraction-sync-async-logic-dedup/07-PATTERNS.md` — mapeo de archivos nuevos vs analogs; Phase 8 sigue el mismo formato.
- `.planning/phases/07-core-py-extraction-sync-async-logic-dedup/07-06-PLAN.md` — plantilla para Plan 6 (CI green gate); Phase 8 Plan 6 mirror.
- `.planning/phases/07-core-py-extraction-sync-async-logic-dedup/07-05-PLAN.md` — plantilla matriz para Plan 5 (atomic + snapshot test guard); Phase 8 Plan 5 sigue idiom similar pero sin scope CR.

### Prior phase (Phase 6, baseline classes)

- `.planning/phases/06-compat-safety-net-client-class-skeleton/06-CONTEXT.md` — D-04 (`configure(token=..., token_expires_at=...)`), D-13 (`Client.__init__` kwargs minimal — Phase 8 EXTIENDE con max_retries+http_client), D-14 (`configure()` semantics: replaces _default_client), D-18 (`Client.__repr__` credential redaction — pattern aligned con D-22 auth_basic redaction).
- `.planning/phases/06-compat-safety-net-client-class-skeleton/06-02-PLAN.md` — pytest-httpx guard test pattern reusable para D-26 tests.

### Research (v1.1)

- `.planning/research/SUMMARY.md` §"Architecture Approach" — 5-module pattern locked: `_state.py` ✅ Phase 6, `_core.py` ✅ Phase 7, `_transport.py`/`_atransport.py`/`_logging.py` este phase.
- `.planning/research/SUMMARY.md` §"Phase 3: Retries, Backoff, and Structured Logging" — esta phase corresponde al "Phase 3" del research (renombrada Phase 8 en roadmap v1.1).
- `.planning/research/STACK.md` — `tenacity>=9.1.0,<10` único runtime addition; `py.typed` confirmed; zero deps; rationale vs httpx-retries.
- `.planning/research/FEATURES.md` — P1 retry+logging features explicit; P2 deferred (with_options, Client.from_env, request_id header).
- `.planning/research/PITFALLS.md` §"Pitfall 4" — Retry de mutating POST; D-01/D-07 mitigation (idempotent gate + retry_on= sin domain exceptions).
- `.planning/research/PITFALLS.md` §"Pitfall 5" — Retry storm en expired token; D-02 mitigation (401 en shell, no en retry_on=).
- `.planning/research/PITFALLS.md` §"Pitfall 6" — Library configures root logger; D-14 + D-27 mitigation (NullHandler + ruff/grep CI rule + D-26 regression test).
- `.planning/research/PITFALLS.md` §"Pitfall 7" — DEBUG prints credentials; D-10 mitigation (RedactingFilter + caplog regression test).
- `.planning/research/PITFALLS.md` §"Pitfall 13" — 429 Retry-After ignored; D-04 mitigation (cap 60s + honor).
- `.planning/research/PITFALLS.md` §"Pitfall 14" — Jitter seeded once; D-08 mitigation (full-jitter via `random.uniform` per attempt).
- `.planning/research/PITFALLS.md` §"Pitfall 15" — Retries swallow PrimaryAPIError; D-24 mitigation (NUNCA en retry_on=).
- `.planning/research/PITFALLS.md` §"Pitfall 16" — Retries delay cancellation; D-32 mitigation (asyncio.sleep + propagate CancelledError).
- `.planning/research/PITFALLS.md` §"Pitfall 17" — Structured extra={} collide stdlib LogRecord; D-09 field set elegido sin colisiones (`package`/`method`/`url`/`status_code`/`attempt`/`duration_ms`/`request_id`/`endpoint_name`/`account_id` — ninguno colisiona).

### Codebase maps (vigentes — Phase 7 las dejó actualizadas)

- `.planning/codebase/ARCHITECTURE.md` §"Module-Level State Pattern" — `_state.py` ya canónico post-Phase-6; `_core.py` post-Phase-7; `_transport.py`/`_atransport.py`/`_logging.py` aterrizan en esta phase.
- `.planning/codebase/CONVENTIONS.md` — naming conventions: private modules `_snake_case.py`, `from __future__ import annotations` mandatory, double quotes, line=100. Phase 8 sigue todo.
- `.planning/codebase/CONCERNS.md` §"No retries" + §"No structured logging" — justifica el delivery.
- `.planning/codebase/TESTING.md` — pytest-httpx pattern + autouse fixtures con `configure(token=...)` (Phase 6 migration); Phase 8 tests extend.

### Spike findings (auto-loaded)

- `.claude/skills/spike-findings-market-libs/SKILL.md` §"RefreshPolicy (retry semantics) — from Spike 003" — patrón validado para retry + backoff + fail-cache: alineado con D-04 (Retry-After), D-07 (PermanentError no retry), D-08 (full-jitter base/max). **Nota:** RefreshPolicy es para Phase 10 (refresh_fn wrap), NO se aplica directo a Phase 8 request-level retry — pero los principios son los mismos. NO importar el código del spike (vive en `.planning/spikes/003-tokenstore-refresh-policy/`); SOLO los principios.

### Phase 5 v1.0 (CR-03 reference)

- `.planning/milestones/v1.0-phases/05-matriz-verification/05-REVIEW.md` — CR-03 (matriz `_request` body consume) ya cerrado en Phase 7 D-06. Phase 8 NO re-toca.

### Forward references (no leer todavía)

- `.planning/ROADMAP.md` §"Phase 9" — BUG-01 (F-09 matriz ERROR-MAP) consume `_core.raise_for_response` ya enhanced; BUG-04 (HIGY multi-account) usa el `account_id` field declarado en Phase 8 D-11.
- `.planning/ROADMAP.md` §"Phase 10" — `_atransport.py` matriz lands (Phase 8 D-25 deferral); TokenStore 3-way (spike-findings validated).
- `.planning/ROADMAP.md` §"Phase 11" — CR-07 (`event_hooks` lock missing) cierre; tendrá interacción con logging si hooks emiten log records.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`_state.py` per paquete (Phase 6)** — `_ClientState` dataclass con `base_url`, credenciales, `token`, `token_expires_at`, `http_client`. Phase 8 lo consume sin tocarlo; el `http_client` es donde el RetryTransport vive. Si el caller pasa `http_client=` via D-15, ese reemplaza `state.http_client` en `__init__` directamente.
- **`_core.py` per paquete (Phase 7)** — `RequestSpec` con `idempotent: bool = False` forward-declared (D-13 Phase 7); builders `build_<endpoint>_request`; parsers `parse_<endpoint>_response`; `raise_for_response`; matriz `parse_envelope_response`. Phase 8 EXTIENDE `RequestSpec` con `account_id` (higyrus + matriz) y `endpoint_name` (los 4); marca `idempotent=True` en los GET builders + login/refresh.
- **`verification/test_public_surface.py` y `verification/snapshots/<pkg>-surface.txt`** — Phase 6/7 baseline; Phase 8 actualiza per-paquete con los 2 nuevos kwargs (D-28).
- **`verification/regen_snapshots.py`** — script Phase 6; Phase 8 NO lo invoca normalmente; cada plan updatea su snapshot manual (D-28 + Phase 6 D-11 pattern).
- **`verification/test_sync_async_isolation.py`** (Phase 7 D-10) — cross-leak sentinel test parametrizado. Phase 8 lo EXTIENDE con assertions de logging (no token leak en records cross-surface). matriz async branch sigue skipped (D-25).
- **PEP 562 `__getattr__` shim** — Phase 6 D-01. Phase 8 NO lo toca. Los nuevos kwargs (`max_retries`, `http_client`) se exponen via `configure()` directo, no via shim.
- **B8 alias pattern** — Phase 7 D-04. Phase 8 NO lo toca.
- **`@dataclass(frozen=True, slots=True) RequestSpec`** — Phase 7. Phase 8 agrega fields (`account_id`, `endpoint_name`) — agrega defaults para back-compat.

### Established Patterns

- **Per-package serial delivery (ámbito → iol → higyrus → matriz)** — Phase 6 D-05, Phase 7 D-13. Phase 8 D-21 sigue. Si Plan 3 (iol) rompe, Plans 1+2 quedan mergeable.
- **1 commit atómico por paquete** — Phase 6 D-05, Phase 7 D-12. Phase 8 D-21 plan slicing.
- **`assert state.token is not None` post `_ensure_token()` para mypy narrowing** — iol/higyrus/matriz. Phase 8 preserva en shell `_request()`; el 401 re-auth path NO requiere assert (después del retry, el `_raise_for_response` levanta si sigue 401).
- **Importance of `from __future__ import annotations`** — mandatory uniformly. Phase 8 nuevos archivos incluyen.
- **`load_dotenv()` al import de `client.py`** — Phase 6 D-19. Phase 8 NO toca.
- **`configure()` replaces `_default_client` con nueva instancia** — Phase 6 D-14. Phase 8 los kwargs `max_retries` y `http_client` van por aquí (configure crea nuevo Client con los kwargs).

### Integration Points

- **`packages/<pkg>/src/<pkg>/_transport.py`** — NUEVO módulo per paquete (4 archivos). Contiene `RetryTransport(httpx.HTTPTransport)`. Standalone, no importa de `_core.py` (no es un builder/parser).
- **`packages/<pkg>/src/<pkg>/_atransport.py`** — NUEVO módulo per paquete (3 archivos — matriz NO en Phase 8). Contiene `AsyncRetryTransport(httpx.AsyncHTTPTransport)`.
- **`packages/<pkg>/src/<pkg>/_logging.py`** — NUEVO módulo per paquete (4 archivos). Contiene `RedactingFilter`, `get_logger()` factory, redaction patterns (duplicated 4×).
- **`packages/<pkg>/src/<pkg>/__init__.py`** — Agrega `_logging.attach()` (que adjunta NullHandler + RedactingFilter al `getLogger(<pkg>)`). Re-exports del Client/AsyncClient signatures con los 2 nuevos kwargs (snapshot publico actualizado).
- **`packages/<pkg>/src/<pkg>/client.py`** — Shell `_request()` ya colapsado por Phase 7. Phase 8 modifica:
  - Genera `request_id = uuid.uuid4().hex` pre-send
  - Setea `request.extensions["idempotent"] = spec.idempotent`
  - Setea `request.extensions["request_id"] = request_id`
  - Try `_raise_for_response`; on `<Pkg>AuthError` + `spec.auth_basic is None` (no Risk) → re-auth flow + retry-once
  - Emite log records DEBUG/INFO/WARNING/ERROR con structured fields
  - `_default_client._state.http_client` ahora trae `RetryTransport` por default; o el `http_client=` kwarg si se pasó
- **`packages/<pkg>/src/<pkg>/aio.py`** — análogo en async (3 paquetes; matriz NO).
- **`packages/<pkg>/src/<pkg>/_core.py`** — Mínimo cambio:
  - `RequestSpec` adds `endpoint_name: str` (mandatory) + (higyrus, matriz) `account_id: str | None = None`
  - GET builders y login/refresh marcan `idempotent=True`
  - POST/PATCH builders mantienen `idempotent=False` default (NO se cambia en Phase 8 ni se debe; mutation gate)
- **`packages/<pkg>/src/<pkg>/_state.py`** — Sin cambios estructurales. `http_client` field receives el `httpx.Client(transport=RetryTransport(...))` por default.
- **`pyproject.toml` per-paquete** — Agrega `tenacity>=9.1.0,<10` a `[project] dependencies` de los 4 paquetes (no a `[dependency-groups] dev` del root). Aligned con "no shared internals" (cada paquete su propia dep).
- **`pyproject.toml` root** — Phase 8 puede agregar ruff config para custom rule (D-27 alternative b); `[tool.importlinter]` config de Phase 7 sigue activa (sin cambios).
- **`.github/workflows/ci.yml`** — Phase 8 puede agregar step `lint-logging` si D-27 opta por grep (alternative b). Sino, no changes.
- **`verification/test_retry_mutation_gate.py`, `verification/test_retry_401_reauth.py`, `verification/test_logging_root_unchanged.py`, `verification/test_logging_no_token_leak.py`, `verification/test_retry_after_cap.py`, `verification/test_async_cancellation.py`** — NUEVOS guard tests cross-cutting (D-26).
- **`packages/<pkg>/tests/conftest.py`** — Sin cambios esperados (Phase 6 ya migró a `configure(token=...)`). Si el test ahora usa `http_client=MockTransport`, ese kwarg llega via configure().

</code_context>

<specifics>
## Specific Ideas

- **`RequestSpec` extension pattern (higyrus + matriz example):**
  ```python
  # matriz_client/_core.py
  @dataclass(frozen=True, slots=True)
  class RequestSpec:
      method: str
      path: str
      params: dict[str, Any] | None = None
      headers: dict[str, str] | None = None
      auth_basic: tuple[str, str] | None = None  # Phase 7
      idempotent: bool = False  # Phase 7 forward-decl
      endpoint_name: str = ""  # Phase 8 NEW — set by builder, used in logs
      account_id: str | None = None  # Phase 8 NEW (matriz, higyrus only)
  ```

- **`RetryTransport` core loop (D-31):**
  ```python
  # ambito_financiero_client/_transport.py (canary)
  from __future__ import annotations
  import httpx
  from tenacity import (
      Retrying, stop_after_attempt, wait_exponential_jitter,
      retry_if_exception_type, retry_if_result,
  )

  _RETRYABLE_EXC = (
      httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout,
  )
  _RETRYABLE_STATUS = {408, 409, 429, *range(500, 600)}

  class RetryTransport(httpx.HTTPTransport):
      def __init__(self, *, max_attempts: int = 2, **kwargs):
          super().__init__(**kwargs)
          self._max_attempts = max_attempts

      def handle_request(self, request: httpx.Request) -> httpx.Response:
          if not request.extensions.get("idempotent", False):
              return super().handle_request(request)
          for attempt in Retrying(
              stop=stop_after_attempt(self._max_attempts),
              wait=wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0),
              retry=retry_if_exception_type(_RETRYABLE_EXC),
              reraise=True,
          ):
              with attempt:
                  response = super().handle_request(request)
                  if response.status_code in _RETRYABLE_STATUS:
                      # honor Retry-After (cap 60s) BEFORE next sleep
                      ...
                      raise _RetryableStatus(response)
                  return response
  ```
  Planner ajusta los detalles del Retry-After parsing y del logging vía `attempt.retry_state`.

- **`_logging.py` per-package shape (higyrus example):**
  ```python
  # higyrus_client/_logging.py
  from __future__ import annotations
  import logging
  import re

  _BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._-]+")
  _AUTH_PASSWORD_RE = re.compile(r"password=([^&\s]+)")
  _JSON_PASSWORD_RE = re.compile(r'"password"\s*:\s*"([^"]+)"')

  class RedactingFilter(logging.Filter):
      def filter(self, record: logging.LogRecord) -> bool:
          if isinstance(record.msg, str):
              record.msg = self._redact(record.msg)
          if record.args:
              record.args = tuple(
                  self._redact(a) if isinstance(a, str) else a
                  for a in record.args
              )
          # Optional: scan record.__dict__ for sensitive fields
          return True

      @staticmethod
      def _redact(text: str) -> str:
          text = _BEARER_RE.sub("Bearer ***", text)
          text = _AUTH_PASSWORD_RE.sub("password=***", text)
          text = _JSON_PASSWORD_RE.sub('"password":"***"', text)
          return text

  def attach() -> None:
      logger = logging.getLogger("higyrus_client")
      logger.addHandler(logging.NullHandler())
      logger.addFilter(RedactingFilter())
  ```

- **`__init__.py` attaches logging (every package):**
  ```python
  # higyrus_client/__init__.py
  from higyrus_client import _logging
  _logging.attach()
  del _logging  # NOT re-exported
  ```

- **D-26 mutation gate guard test shape:**
  ```python
  # verification/test_retry_mutation_gate.py
  import pytest
  PACKAGES_WITH_POST = ["iol_client", "matriz_client"]

  @pytest.mark.parametrize("pkg_name", PACKAGES_WITH_POST)
  def test_post_never_retries_without_idempotent(pkg_name, httpx_mock):
      pkg = importlib.import_module(pkg_name)
      pkg.configure(token="X", token_expires_at=9_999_999_999.0)
      # mock 503 for matriz new_order POST
      httpx_mock.add_response(status_code=503)
      with pytest.raises(pkg.exceptions.<Pkg>APIError):
          pkg.new_order(...)
      assert len(httpx_mock.get_requests()) == 1  # NO retry
  ```

- **Commit message patterns Phase 8:**
  - Plan 1: `feat(verification): RetryTransport + _logging scaffolds + cross-cutting guard tests (RELY-01..04, LOG-01..03)`
  - Plans 2-5: `feat(<pkg>): retries + structured logging — RetryTransport, RedactingFilter, account_id (RELY-01..04, LOG-01..03)`
  - Plan 5 specifically: `feat(matriz): retries + structured logging — sync-only (aio.py defer Phase 10) + Risk API 401-no-reauth (RELY-01..04, LOG-01..03)`
  - Plan 6: `ci(phase-08): green gate — full pytest + ruff + mypy + snapshot + lint-imports + retry mutation gate + logging.root unchanged (RELY-01..04, LOG-01..03)`

- **LOC delta reporting format en SUMMARY.md (Plans 2-5):**
  ```
  Phase 8 delta vs Phase 7 baseline:
  - _transport.py:  0 → 95 (NEW)
  - _atransport.py: 0 → 95 (NEW)            [matriz: N/A — Phase 10]
  - _logging.py:    0 → 65 (NEW)
  - _core.py:       180 → 195 (+8%; RequestSpec.endpoint_name + account_id + idempotent=True markers)
  - client.py:      320 → 360 (+12%; 401 re-auth + log calls)
  - aio.py:         305 → 345 (+13%; mismo)  [matriz: N/A]
  ```

</specifics>

<deferred>
## Deferred Ideas

- **`client.with_options(max_retries=N)` per-call override** — anthropic/openai SDK pattern. D-18 lo defer. v1.2+ backlog.
- **`Client.from_env()` classmethod** — explicit env-reading. v1.2+ backlog (research P2).
- **`request_id` enviado vía `X-Request-ID` header al server** — D-30 keeps log-local. v1.2+ backlog.
- **DEBUG payload con body redacted opt-in (env var `LOG_REQUEST_BODY=1`)** — D-12 defer. v1.2+.
- **Sub-loggers por concern** (`<pkg>.transport`, `<pkg>.auth`, `<pkg>.retry`) — D-13 defer. v1.2+ si llega use case (consumer-side filtering).
- **JSON formatter built-in** — D-14 defer (consumer instala si quiere). v1.2+.
- **`max_retries` configurable via env var `MARKET_LIBS_MAX_RETRIES`** — D-20 defer. v1.2+.
- **Per-paquete tuneo de defaults** (ámbito=1, matriz=3) — D-06 mantiene uniforme. Si telemetry sugiere otra cosa, v1.2.
- **Wrap caller's http_client transport con RetryTransport automáticamente** — D-16 mantiene "use AS-IS". v1.2 si UX feedback lo justifica.
- **`max_elapsed_seconds` retry budget cap as belt-and-suspenders** — research P2. v1.2+.
- **Automatic `Idempotency-Key` header for retried POSTs** — research v1.2+ backlog. Phase 8 NO lo entrega.
- **`PrimaryAPIErrorTransient` / `PrimaryAPIErrorPermanent` classification** — D-24 mantiene `PrimaryAPIError` único sin classification del description. v1.2 si patrón emerge.
- **HTTP-date format en Retry-After parsing** — Claude's Discretion + recommendation a delta-seconds only día 1; planner valida. v1.2 si server lo usa.
- **Telemetry export hook** — opt-in callback para forward log records a OpenTelemetry. v1.2+.
- **Detect + warn cuando `http_client=` no tiene RetryTransport** — D-16 alternative C rejected. v1.2 si UX feedback.

### Reviewed Todos (not folded)

- **matriz-driver-findings-file-handling.md** (matched score 0.6) — el todo refers a HARN-07 (findings.py append-only) + HARN-08 (content-addressed dedupe) + HARN-10 (D-MATZ-27 dedupe), todos Phase 11 scope. NO se folda en Phase 8 (que es retries+logging). Sigue en `.planning/todos/pending/` esperando Phase 11.

</deferred>

---

*Phase: 8-Retries, Backoff, Structured Logging*
*Context gathered: 2026-06-12*
