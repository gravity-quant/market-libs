# Phase 8: Retries, Backoff, Structured Logging - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** 8-Retries, Backoff, Structured Logging
**Areas discussed:** Retry mechanism + 401 boundary, Logging fields + redacción + account_id, Public API surface, Plan slicing y guard tests org, _ensure_token() × RetryTransport, request_id correlation, matriz Risk API auth_basic, asyncio.CancelledError respect, matriz 200-OK status=ERROR retry, tenacity sync+async API, max_retries default BC promise

---

## Retry mechanism + 401 boundary

### Q1: ¿Dónde vive la lógica de retry?

| Option | Description | Selected |
|--------|-------------|----------|
| RetryTransport subclass (Recommended) | httpx.HTTPTransport + AsyncHTTPTransport subclass per paquete; gate via request.extensions['idempotent']; transport ve solo status/network errors; composable | ✓ |
| tenacity decorator en _core.execute_with_retry | _core.py expone execute_with_retry(spec, send_fn); ve idempotent directo; transport vanilla; alineado con RefreshPolicy spike 003 | |
| Mixto: transport + _core | Transport status+network, _core policy + 401 re-auth + logging | |

### Q2: ¿Dónde aterriza el "exactly one" 401 re-auth?

| Option | Description | Selected |
|--------|-------------|----------|
| Shell _request() del Client (Recommended) | try _raise_for_response → AuthError → state.token=None → _ensure_token() → retry once; AuthError nunca en retry_on=; 401 sobre POST idempotent=False igual re-auth+retry | ✓ |
| RetryTransport con re_auth_fn callable | Transport recibe re_auth_fn= callable; encapsulado pero transport conoce auth (impureza) | |
| 401 NO triggerea re-auth | Propaga AuthError inmediato; rompe roadmap success-criterion #3 | |

### Q3: Retry-After > 60s en 429

| Option | Description | Selected |
|--------|-------------|----------|
| Cap at 60s y retry (Recommended) | Sleep 60s + retry; si insiste agota max_attempts → RateLimitError; "transparente" para caller | ✓ |
| Propagate RateLimitError inmediato | Sin sleep; caller decide; spike 003 RateLimitedRefreshError pattern | |
| Honor Retry-After full sin cap | Sleep exacto del server; bloqueante; peligroso para latency-sensitive | |

### Q4: Retry budget exhaust

| Option | Description | Selected |
|--------|-------------|----------|
| APIError/RateLimitError nativo (Recommended) | Response final via flow normal; zero-surface-change; logs cuentan la historia | ✓ |
| RetryExhaustedError wrapping con causa | Nueva excepción per paquete; 4× replicado; posible breaking change | |
| APIError con .attempts attribute | Same type + extra field; zero breaking; cost: APIError signature de los 4 paquetes cambia | |

### Q5: Auth-flow request (login/refresh) retry

| Option | Description | Selected |
|--------|-------------|----------|
| Marked idempotent=True (Recommended) | build_login_request / build_refresh_request setean idempotent=True; retry sobre 5xx/429/connection; spike 003 pattern aligned | ✓ |
| POST normal fail-fast | login/refresh dejan idempotent=False; sin retry; AuthError inmediato | |
| Solo network errors no 5xx | Retry connect/timeout pero NO 5xx; protege contra token-double-issue | |

### Q6: max_attempts default

| Option | Description | Selected |
|--------|-------------|----------|
| Uniforme 2 cross-paquete (Recommended) | Default roadmap; alineado con anthropic/openai SDK; predecible | ✓ |
| Uniforme 3 cross-paquete | Más aggressive; mejor para matriz/iol blips; peor latency p99 | |
| Per-paquete tuneado | ambito=1, iol=2, higyrus=2, matriz=3; refleja perfil real; 4 magic numbers | |

### Q7: retry_on= exception set

| Option | Description | Selected |
|--------|-------------|----------|
| Roadmap default (Recommended) | 408/409/429/≥5xx + httpx.ConnectError + ConnectTimeout + ReadTimeout; AuthError/PrimaryAPIError/HigyrusAPIError NUNCA | ✓ |
| + httpx.WriteTimeout + httpx.PoolTimeout | Roadmap + 2 más del httpx.TransportError family | |
| Stricter (drop 408 y 409) | Solo 429 + ≥5xx + Connect/Read family; conservador | |

### Q8: Backoff parameters

| Option | Description | Selected |
|--------|-------------|----------|
| base=1s/max=30s/exp=2/full-jitter (Recommended) | random.uniform(0, min(max, base*2^attempt)); alineado tenacity.wait_exponential_jitter + AWS + spike 003 | ✓ |
| base=0.5s aggressive | Primer retry más rápido (≤1s); mejor UX blips; más presión server | |
| Honor tenacity defaults | multiplier=1, exp_base=2, min=0, max=∞; necesita override igual | |

---

## Logging fields + redacción + account_id

### Q1: Field set canónico

| Option | Description | Selected |
|--------|-------------|----------|
| Roadmap mínimo | package, method, url, status_code, attempt, duration_ms; account_id condicional; 6+1 fields | |
| Roadmap + request_id UUID + endpoint_name (Recommended) | + request_id (cross-attempt correlation) + endpoint_name (e.g., 'get_segments'); 8+1 fields | ✓ |
| Roadmap + retry_reason + base_url | + retry_reason + base_url (matriz Primary vs Risk); diagnóstico preciso pero base_url no aporta fuera de matriz | |

### Q2: RedactingFilter layer

| Option | Description | Selected |
|--------|-------------|----------|
| logging.Filter en _logging.py per paquete (Recommended) | RedactingFilter(Filter) reescribe record.msg + args + __dict__ in-place; patrones inline duplicados 4×; caplog regression test | ✓ |
| Redacción call-site sin filter | Helper redact_url/redact_headers manual antes del log; no magic | |
| LoggerAdapter wrapping con context push | Adapter override process(); structured context inherente | |

### Q3: account_id propagation

| Option | Description | Selected |
|--------|-------------|----------|
| RequestSpec carry + transport copia a extra (Recommended) | Nuevo field RequestSpec.account_id opcional (higyrus + matriz); builder seta desde id_cuenta kwarg; transport copia a extra | ✓ |
| _request() arg explícito + extra inyectado | Methods forward id_cuenta a self._request(spec, account_id=); 4-6 sites per paquete | |
| Inferido via contextvars per task | _logging.set_account_id en wrappers; landmine asyncio cross-loop | |

### Q4: Niveles + payload

| Option | Description | Selected |
|--------|-------------|----------|
| Roadmap mínimo (Recommended) | DEBUG req/resp (sin body, sin headers); INFO auth events; WARNING retry; ERROR terminal | ✓ |
| Roadmap + DEBUG payload opcional | LOG_REQUEST_BODY=1 env var + configure() opt-in; body redacted; bigger leak surface | |
| Más verbose INFO | INFO cada request; dev-friendly; mayor noise prod | |

### Q5: Logger naming

| Option | Description | Selected |
|--------|-------------|----------|
| Un logger por paquete (Recommended) | logging.getLogger('matriz_client'); 4 loggers total; consumer setea level con 1 statement | ✓ |
| Sub-loggers por concern | matriz_client.transport / .auth / .retry; consumer puede mute por concern; 12-16 loggers total | |
| Un logger + getChild() para test isolation | Helper para tests; no aporta production value | |

### Q6: httpx loggers interaction

| Option | Description | Selected |
|--------|-------------|----------|
| Library no toca — consumer decide (Recommended) | Cada paquete solo configura su logger + NullHandler; 'httpx'/'httpcore' default WARNING; zero hijacking | ✓ |
| Suppress 'httpx' y 'httpcore' default | __init__.py setLevel(WARNING) para ambos; cost: parcial Pitfall 6 violation | |
| Re-emit relevante via nuestro logger | Asumimos httpx logs redundantes; opción A en práctica | |

---

## Public API surface

### Q1: Extender o zero-change

| Option | Description | Selected |
|--------|-------------|----------|
| Extender mínimo: max_retries + log_level + http_client (Recommended) | 3 kwargs nuevos en Client/AsyncClient/configure(); snapshot crece predecible | ✓* |
| Zero-surface-change | Sin cambios; defaults fijos en _transport.py; customización via subclass; http_client= no disponible | |
| Extender amplio: + backoff base/max + jitter | 6 kwargs nuevos; aligned con with_options pattern | |

*Modificado por Q2 (drop log_level) → finalmente max_retries + http_client (2 kwargs).

### Q2: log_level semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Drop log_level del kwarg set (Recommended) | Consumer hace logging.getLogger('<pkg>').setLevel() directo; sin side effect global desde dentro del paquete | ✓ |
| log_level setea getLogger(<pkg>).setLevel() | Sugar pero múltiples Clients pisan level; global state mutation | |
| log_level per-Client via LoggerAdapter | Filtra records por level scoped a instancia; más código; más tests | |

### Q3: http_client= semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Use AS-IS, caller responsible (Recommended) | http_client= se usa tal cual; caller installs RetryTransport o no; power-user path | ✓ |
| Wrap caller's transport automáticamente | Auto-wrap con RetryTransport; mágico; harder debug | |
| Detect + warn | Warning si no tiene RetryTransport; compromiso | |

### Q4: max_retries override scope

| Option | Description | Selected |
|--------|-------------|----------|
| Solo Client/configure() (Recommended) | Locked en construcción; nuevo Client para override; with_options() defer v1.2 | ✓ |
| Client + Client.with_options(max_retries=N) per-call | Anthropic/openai pattern; shallow-copy semantics | |
| Client + kwarg per-call: get_X(*, max_retries=None) | 50+ methods agregan kwarg; anti-pattern | |

### Q5: max_retries=0 behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Disable retries completamente (Recommended) | 1 outgoing total; bypass del retry loop; opt-out claro | ✓ |
| max_retries=0 = ValueError | Validate en __init__; forces sensible defaults | |
| max_retries=0 = max_retries=2 silent coerce | Silent surprise; worst | |

---

## Plan slicing y guard tests org

### Q1: Plan slicing

| Option | Description | Selected |
|--------|-------------|----------|
| Per-package serial: 1 CI gate + 4 per-pkg + 1 green gate (Recommended) | 6 planes; idem Phase 6 D-05 / Phase 7 D-12; revertible per-paquete | ✓ |
| Feature-first: retries×4 + logging×4 + CI gate | 9 planes; cada archivo se toca 2 veces; 50% más plans | |
| Per-package serial ATÓMICO sin Plan 1 infra | 5 planes; cross-cutting cae en primer paquete; ámbito (sin auth) no ejercita 401 | |

### Q2: Guard tests org

| Option | Description | Selected |
|--------|-------------|----------|
| verification/ parametrizado cross-paquete (Recommended) | test_retry_mutation_gate.py + test_retry_401_reauth.py + test_logging_*.py parametrizados × 4 paquetes; Phase 7 D-10 pattern | ✓ |
| Per-paquete dentro de packages/<pkg>/tests/ | Replicado 4×; tests viajan con wheel; mantenimiento duplicado | |
| Mix: cross-cutting en verification/ + pkg-específicos en packages/ | Pragmático pero menos uniforme | |

### Q3: CI grep rule

| Option | Description | Selected |
|--------|-------------|----------|
| ruff custom rule via configuración existente (Recommended) | Prohibir 'logging.basicConfig' y 'logging.root'; mismo idiom que Phase 7 import-linter | ✓ |
| Plain grep en CI step | Shell script en CI; simple pero frágil | |
| pytest regression via importlib check | Test en pytest no en lint; más costoso | |

### Q4: Snapshot update strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Per-package: cada plan (2-5) actualiza su snapshot atómico (Recommended) | Mismo Phase 6 D-06; Plan 6 green gate verifica diff vs baseline Phase 7 | ✓ |
| Plan 1 (infra) actualiza los 4 snapshots | Plan 1 modifica 4 paquetes; anti-pattern cross-package commit | |
| Sin update — regen al final | Plans 2-5 con tests rojos; anti-pattern | |

### Q5: matriz async-side in Plan 5

| Option | Description | Selected |
|--------|-------------|----------|
| Skip todo lo async-side (Recommended) | Solo _transport.py sync para matriz; _atransport.py defer Phase 10; pytest.skip en guard tests async branch | ✓ |
| Crear _atransport.py vacío con stub | Código listo pero dead, untested; YAGNI smell | |
| Plan 5 hace todo + aio.py REST skeleton | Absorbe scope Phase 10; viola dependency declared | |

---

## _ensure_token() × RetryTransport

### Q1: Login va por el RetryTransport o naked

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, atraviesa con idempotent=True (Recommended) | Login va por state.http_client (con RetryTransport); idempotent=True (Area 1 D-03); 401 → AuthError inmediato; no recursión porque 401 re-auth exactly-one | ✓ |
| No, naked httpx call branch para login | Temporary client sin transport; dos paths HTTP; naked path sin retry transient | |
| Token endpoint exent via skip_retry extension | Mágico; flag adicional; conflict con idempotent=True | |

---

## request_id correlation cross-retry-attempts

### Q1: Per business-call o per attempt

| Option | Description | Selected |
|--------|-------------|----------|
| Uno per business-call (Recommended) | uuid4() UNA vez pre-send; todos los attempts comparten; attempt field distingue; anthropic SDK pattern | ✓ |
| Uno per wire attempt | Nuevo UUID per retry; no correlation trivial; anti-pattern observability | |
| Per business-call + X-Request-ID header al server | Header adicional; APIs pueden rechazar headers desconocidos | |

---

## matriz Risk API auth_basic + 2 base URLs

### Q1: RetryTransport + 401 re-auth para Risk API

| Option | Description | Selected |
|--------|-------------|----------|
| RetryTransport sí, 401 re-auth NO (Recommended) | Mismo state.http_client con retry; spec.auth_basic is not None → skip re-auth; 401 = AuthError directo | ✓ |
| RetryTransport sí, 401 re-auth sí uniforme | Mismo treatment Primary; pero refresh useless para Risk; 1 wasted retry | |
| Risk exent de TODO | skip_retry=True extension; sin retry sin re-auth; fail-fast | |

### Q2: auth_basic redaction

| Option | Description | Selected |
|--------|-------------|----------|
| auth_basic_user only, redact password (Recommended) | Loguea user='<user>' password='***'; aligned con Phase 6 D-18 Client.__repr__; audit-friendly | ✓ |
| auth_basic completo redacted '<basic auth>' | Sin detalle del user; harder diagnose | |
| Drop auth_basic del extra completely | Internal-only; zero leak risk pero zero observability | |

---

## asyncio.CancelledError respect (Pitfall 16)

### Q1: Backoff sleep cancel-aware

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, sleep usa asyncio.sleep + propagate CancelledError (Recommended) | tenacity.AsyncRetrying out of the box; wait_for(timeout=) interrumpe mid-retry | ✓ |
| Catch CancelledError + re-raise como nuestra excepción | Anti-pattern asyncio; CancelledError debe propagarse | |
| Sleep con time.sleep blocking | Bloquea event loop; anti-pattern | |

---

## matriz 200-OK con status=ERROR retry

### Q1: PrimaryAPIError retry?

| Option | Description | Selected |
|--------|-------------|----------|
| NUNCA retry, PrimaryAPIError final (Recommended) | PrimaryAPIError NUNCA en retry_on=; aligned con Pitfall 15; caller-determined retry preserva agency | ✓ |
| Retry condicional si description match transient | Classification del description; frágil; rompe regla 'PrimaryAPIError nunca en retry_on=' | |
| Always retry-once safety net | Anti-pattern; enmascara app errors; double-charging risk | |

---

## tenacity sync+async API integration shape

### Q1: API choice

| Option | Description | Selected |
|--------|-------------|----------|
| Retrying/AsyncRetrying como iterator dentro de handle_request (Recommended) | for attempt in Retrying(...): with attempt; integra con httpx transport boundary; logging via retry_state | ✓ |
| @retry decorator sobre handle_request | Más declarativo; harder access retry_state; before/after hooks | |
| Custom retry loop sin tenacity | Sin dep; pero re-implementar full jitter + Retry-After + stop conditions; roadmap LOCK tenacity | |

---

## Deprecation timeline para defaults

### Q1: BC promise

| Option | Description | Selected |
|--------|-------------|----------|
| Subject to tuning (Recommended) | Docstring 'default=2; subject to change in future minor versions'; aligned anthropic SDK; permite ajuste si telemetry sugiere | ✓ |
| BC promise hard — default 2 hasta v2.0 | Caller puede confiar; restrictivo si telemetry sugiere otra cosa | |
| Configurable via env var MARKET_LIBS_MAX_RETRIES | Superficie nueva; cross-paquete global; contradice 'fixed defaults' | |

---

## Claude's Discretion

- Ubicación exacta `_transport.py` / `_logging.py` (planner)
- Estructura interna del RetryTransport (sentinel exception name)
- Naming exact RequestSpec fields (`endpoint_name` vs `endpoint`)
- Retry-After parsing format (delta-seconds only vs +HTTP-date) — recomendación: solo delta-seconds + WARNING para HTTP-date
- Logging formatter en testing (caplog interaction con filter)
- Exact extra={} field naming (`attempt` vs `retry_attempt` vs `attempt_number`)
- Test cadence per plan (mismo idiom Phase 7 D-13)
- ruff vs grep vs flake8-logging para CI rule D-27

## Deferred Ideas

- `client.with_options(max_retries=N)` per-call override → v1.2+
- `Client.from_env()` classmethod → v1.2+
- `request_id` via `X-Request-ID` header al server → v1.2+
- DEBUG payload con body redacted opt-in → v1.2+
- Sub-loggers por concern → v1.2+
- JSON formatter built-in → v1.2+
- `max_retries` via env var → v1.2+
- Per-paquete tuneo de defaults → v1.2 si telemetry sugiere
- Auto-wrap caller's http_client transport → v1.2 si UX feedback
- `max_elapsed_seconds` retry budget cap → v1.2+
- Automatic `Idempotency-Key` header for retried POSTs → v1.2+
- `PrimaryAPIErrorTransient`/`Permanent` classification → v1.2 si patrón emerge
- HTTP-date format en Retry-After → planner valida, v1.2 si server lo usa
- Telemetry export hook (OpenTelemetry) → v1.2+
- Detect + warn cuando http_client= sin RetryTransport → v1.2 si UX feedback

### Reviewed Todos (not folded)

- **matriz-driver-findings-file-handling.md** — Phase 11 scope (HARN-07/08/10), no Phase 8.
