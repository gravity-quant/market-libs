---
phase: 04
slug: higyrus-verification
status: secured
threats_open: 0
threats_closed: 24
threats_total: 24
asvs_level: 1
mode: retroactive-STRIDE
register_authored_at_plan_time: false
created: 2026-06-09
---

# SECURITY.md — Phase 04 (higyrus-verification) Retroactive STRIDE Audit

**Phase:** 04 — higyrus-verification
**ASVS Level:** 1
**Mode:** retroactive-STRIDE (PLANs no incluían `<threat_model>` formal a tiempo de planeación; el registro se construyó desde la implementación)
**Generated:** 2026-06-09
**Block-on:** high

## Adversarial stance & methodology

Los 4 PLANs (04-01..04-04) NO traían un `<threat_model>` STRIDE estructurado al momento de planeación. Para esta auditoría se construyó el registro a partir de los archivos de implementación de Phase 4 (driver + cliente + tests + artefactos `.planning/verification/`), aplicando STRIDE sobre la superficie nueva o modificada por la fase. Cada threat se verifica con **grep / file inspection** en los sitios concretos — no se acepta "la documentación lo dice".

Archivos auditados (READ-ONLY):

- `main_higyrus.py` (2380 LOC)
- `packages/higyrus-client/src/higyrus_client/client.py`
- `packages/higyrus-client/src/higyrus_client/aio.py`
- `packages/higyrus-client/src/higyrus_client/exceptions.py`
- `packages/higyrus-client/src/higyrus_client/_params.py`
- `packages/higyrus-client/src/higyrus_client/models.py`
- `packages/higyrus-client/.env.example`
- `packages/higyrus-client/tests/test_client.py`
- `packages/higyrus-client/tests/test_async_client.py`
- `packages/higyrus-client/tests/conftest.py`
- `verification/redaction.py`
- `.gitignore`
- `.planning/verification/schemas/higyrus-client/{get-health,get-listado-cuentas,get-movimientos,get-posicion-valuada,get-posiciones}.json`
- `.planning/verification/higyrus-client-findings.md`

## Trust boundaries (Phase 4 surface)

| # | Boundary | Description |
|---|----------|-------------|
| TB-1 | env vars → `higyrus_client.client` / `aio` module-level globals (`_user`, `_password`, `_client_id`, `_base_url`, `_token`) | Cargado via `load_dotenv()` en import; mutado por `configure()` |
| TB-2 | `higyrus_client.login()` → wire HTTP `POST /api/login` con body `{clientId, username, password}` | Credenciales viajan sobre TLS al backend Higyrus |
| TB-3 | Backend Higyrus → `resp.json()` (Authorization token cacheado `_token`) | Token sobrevive 23h en proceso |
| TB-4 | `_request(...)` wrapper → cada endpoint público (`get_health` / `get_movimientos` / `get_posicion_valuada` / `get_listado_cuentas` / `get_posiciones`) | Validación de forma del payload via `if not isinstance: raise HigyrusAPIError(0, …)` |
| TB-5 | Driver `main_higyrus.py` → stdout/findings/schemas | Defense-in-depth: `safe_print` con `secrets=[user, password, sync_token_snapshot, async_token_snapshot]`; D-HIGY-2 stdout solo conteos |
| TB-6 | Driver → `.planning/verification/schemas/higyrus-client/*.json` (5 snapshots committeados) | Envelope D-21; `schema` solo type names via `schema_of(payload)` |
| TB-7 | Driver → `.planning/verification/higyrus-client-findings.md` (committeado) | Operador inspeccionó pre-commit (revisión humana) |
| TB-8 | `probe_auth_401` → `higyrus_client.configure(password=HIGYRUS_PASSWORD+"_INVALID")` → live POST /api/login | Opt-in via `VERIFY_HIGYRUS_BAD_CREDS=1`; single-shot; try/finally restore |

## STRIDE Threat Register & Verification

### Closed (mitigated)

| Threat ID | Category | Component | Disposition | Evidence |
|-----------|----------|-----------|-------------|----------|
| T-4-S1 | Spoofing | `probe_auth_401` debe RESTAURAR `HIGYRUS_PASSWORD` original aunque el `login()` con bad password levante (sino: estado corrupto + sesión bloqueada en próximos runs) | mitigate | `main_higyrus.py:2050-2117` — bloque `try: configure(password=bad_password); …; finally: higyrus_client.configure(password=original_password)`; el `finally` es OBLIGATORIO en todos los exit paths |
| T-4-S2 | Spoofing | login con credenciales faltantes/inválidas debe levantar `HigyrusAuthError` (no httpx.HTTPStatusError genérica) | mitigate | `client.py:101-127` + `aio.py:111-141` — WR-01 fix: `if not resp.is_success: _raise_for_response(resp)` antes de leer token; `_raise_for_response` mapea 401→`HigyrusAuthError`, 403→`HigyrusAuthorizationError`, 429→`HigyrusRateLimitError` |
| T-4-S3 | Spoofing | login que retorne 200 OK pero sin `token` en JSON no debe dejar el cliente en estado "logged in" | mitigate | `client.py:121-127` + `aio.py:131-137` — `if not isinstance(token, str) or not token: raise HigyrusAuthError(...)`; el `_token` global no se actualiza |
| T-4-T1 | Tampering | `assert isinstance(raw, list/dict)` strippeable bajo `python -O` deja procesar payloads mal tipados silenciosamente | mitigate | `client.py:222,267,318,354,387` + `aio.py:244,284,331,363,392` — 10 sites con `if not isinstance(raw, T): raise HigyrusAPIError(status_code=0, errors=[{"title":"shape mismatch", ...}])`; `grep -c "assert isinstance" ambos == 0` (Plan 04-01) |
| T-4-T2 | Tampering | httpx por defecto encodea `/` como `%2F` en query; Higyrus IIS rechaza `dd/mm/yyyy` rejected → potencial confusión de error vs. tampering en wire | mitigate | `client.py:182-191` + `aio.py:205-214` — `url = f"{url}?{urlencode(clean_params, doseq=True, quote_via=quote, safe='/')}"`; regression tests `test_request_preserves_literal_slash_in_query{,_async}` |
| T-4-T3 | Tampering | Pasar `json=None` a `httpx` envía `null` body con Content-Type application/json en GET (no equivale a omitir kwarg) | mitigate | `client.py:195-198` + `aio.py:217-220` — `kwargs: dict = {"headers": …}; if json_body is not None: kwargs["json"] = json_body`; WR-02 fix |
| T-4-T4 | Tampering | Schema baseline JSON file alterado en re-runs (drift no detectado) | mitigate | `main_higyrus.py:_write_or_check_schema` (line 409) D-25 no-overwrite: si el archivo existe, compara y emite finding SHAPE OPEN; NO sobreescribe |
| T-4-R1 | Repudiation | Falta de timestamp + run context en findings markdown (sin trazabilidad) | mitigate | `higyrus-client-findings.md:3-6` — `## Run Context (ART)` con timestamp ISO-8601, base URL, run params |
| T-4-I1 | Information Disclosure | `HIGYRUS_PASSWORD` o `HIGYRUS_USER` aparece en stdout/findings al imprimir un error o repr(exc) | mitigate | `main_higyrus.py:2266-2278` — `secrets.append(_password_env)` SIEMPRE (sin threshold), `secrets.append(_user_env)` con threshold `len >= 4`; `safe_print()` en `verification/redaction.py:43-61` enmascara via 2 capas (lista de secrets + regex `Bearer` fallback) |
| T-4-I2 | Information Disclosure | `_token` (Bearer) aparece en stdout/findings tras login sync o async | mitigate | `main_higyrus.py:2285-2289` (sync snapshot por valor), `main_higyrus.py:2181,2215` (async snapshot por valor dentro de `_async_main`), `main_higyrus.py:2332-2333` (apendeado a `secrets`); además `verification/redaction.py:31` regex `_BEARER` enmascara cualquier `Bearer <token>` reflejado |
| T-4-I3 | Information Disclosure | `probe_auth_401` resetea `_token = None` vía `configure()`, nulificando snapshot de redacción mid-run | mitigate | snapshots tomados POR VALOR (no por referencia) en `main_higyrus.py:2285-2287` y `main_higyrus.py:2181`; los valores apendeados a `secrets` antes del probe 18 sobreviven al `configure(password=...+"_INVALID")` |
| T-4-I4 | Information Disclosure | Schema JSONs committeados contienen PII real (nombres de titulares, CBUs, CUITs, IDs de cuenta de clientes terceros) | mitigate | `schema_of(payload)` reduce a type names (`str`, `int`, `float`, `NoneType`); inspección manual de los 5 schemas en `.planning/verification/schemas/higyrus-client/*.json` confirma SOLO type names en `schema`; `sample_params.id_cuenta="5208"` es ID del operador (cuenta de prueba propia), no de cliente tercero |
| T-4-I5 | Information Disclosure | Driver stdout imprime conteos de `len(payloads)` pero no contenidos | mitigate | D-HIGY-2 stdout discipline: `safe_print(f"PROBE {name}: {status} {detail}")` con `detail` = conteo + shape descriptor; ej. `main_higyrus.py:2365` |
| T-4-I6 | Information Disclosure | `.env` file con credenciales reales committeado por accidente | mitigate | `.gitignore:31` `.env` global → `git check-ignore packages/higyrus-client/.env` exits 0 (gitignored); `git ls-files | grep -i env` retorna solo `.env.example` (template) |
| T-4-I7 | Information Disclosure | `verification/captures/` (raw payloads PII) committed por accidente | mitigate | `.gitignore:34` `.planning/verification/captures/` (entry directo); confirmado |
| T-4-I8 | Information Disclosure | Tests sync/async hardcodean credenciales reales | mitigate | `tests/test_client.py:28,30` + `tests/test_async_client.py:27,29` solo usan sentinels (`"tok-123"`, `"tok-async"`); `conftest.py` precarga `_token = "test-token"` y `base_url = "https://api.test"`, todo sintético |
| T-4-I9 | Information Disclosure | El findings markdown menciona `cuenta 5208` y URL `https://becerra.aunesa.com/Irmo` (datos del operador, no terceros) | accept | El operador inspeccionó pre-commit (per Plan 04-03 Task 3.2 acceptance criteria). El base_url es la URL del backend, no PII de terceros. La cuenta 5208 es la propia del operador (per D-HIGY-11 override), no de un cliente tercero |
| T-4-D1 | DoS | Endpoint shape mismatch en loop de retry interno consume CPU/red | accept | El cliente no tiene retry interno — un solo request por wrapper; el raise propaga inmediatamente |
| T-4-D2 | DoS | `probe_auth_401` reintenta múltiples veces y bloquea cuenta del operador | mitigate | `main_higyrus.py:2050-2114` — single-shot; sin retry, sin sleep, sin loop; `time.sleep` count en main_higyrus.py == 0 (per `<verify>` de 04-02) |
| T-4-D3 | DoS | `_TOKEN_TTL_SECONDS = 23 * 3600` evita re-login en cada call (sin presión sobre `/api/login`) | mitigate | `client.py:57` + `aio.py:46` — TTL 23h; `_ensure_token()` reusa cached token mientras esté vigente |
| T-4-E1 | Elevation of Privilege | `_resolved_cuenta` resuelto por probe 5 podría ser de un cliente tercero (no controlado por operador) | mitigate | `main_higyrus.py:_SAMPLE_CUENTA` (env override per D-HIGY-11); cuando F-02 emitió 0 cuentas, el operador forzó `HIGYRUS_SAMPLE_CUENTA=5208` (cuenta propia) via CLI |
| T-4-E2 | Elevation of Privilege | Caller que catcheaba `AssertionError` ya no atrapa el nuevo raise tipado | accept | Documentado en D-HIGY-7: la jerarquía pública es `HigyrusClientError → HigyrusAPIError`; catcheo de `AssertionError` consumía implementation detail no contractual |
| T-4-SC1 | Supply-chain | `urllib.parse.quote, urlencode` agregados a imports — stdlib, no nuevo paquete | accept | stdlib; no nuevo dependency; `uv.lock` no cambia |
| T-4-SC2 | Supply-chain | Plan 04 NO instala nuevos paquetes externos | accept | No `pip/uv add` ejecutado; `uv.lock` sin diff (Plan 04-01 SUMMARY confirma `tech-stack.added: []`) |

### Open (BLOCKER)

Ninguno. Todas las mitigaciones declaradas (y descubiertas) están presentes en el código con file:line evidence.

### Accepted risks (documented)

| Threat ID | Category | Rationale |
|-----------|----------|-----------|
| T-4-I9 | Information Disclosure | Findings markdown menciona base_url backend + cuenta operador propia (no datos de cliente tercero). Operador firmó pre-commit per Plan 04-03 Task 3.2 |
| T-4-D1 | DoS | Cliente sin retry interno; un solo HTTP per wrapper |
| T-4-E2 | Elevation of Privilege | Cambio de tipo de excepción es API contract change documentado en D-HIGY-7; `HigyrusClientError` (base) sigue catcheable |
| T-4-SC1 | Supply-chain | stdlib only; sin dependencia nueva |
| T-4-SC2 | Supply-chain | Sin instalaciones externas |

### Threats explicitly verified end-to-end

- `grep -c "assert isinstance" packages/higyrus-client/src/higyrus_client/client.py` == 0 (T-4-T1)
- `grep -c "assert isinstance" packages/higyrus-client/src/higyrus_client/aio.py` == 0 (T-4-T1)
- `grep -c "shape mismatch" client.py` == 5, en aio.py == 5 (T-4-T1)
- `grep -c "status_code=0" client.py` == 5, en aio.py == 5 (T-4-T1)
- `grep -c "urlencode" client.py` == 2 (import + uso), `safe="/"` == 1; idem aio.py (T-4-T2)
- `grep -c "configure(password=original_password)" main_higyrus.py` >= 1 (T-4-S1, T-4-D2)
- `grep -c "_sync_token_snapshot" main_higyrus.py` y `_async_token_snapshot` con captura por valor (T-4-I2, T-4-I3)
- `grep -c "VERIFY_HIGYRUS_BAD_CREDS" main_higyrus.py` >= 2 (probe + docstring) (T-4-D2)
- `git check-ignore packages/higyrus-client/.env` exits 0 (T-4-I6)
- `git ls-files | grep env` retorna solo `.env.example` (T-4-I6)
- `time.sleep` count en main_higyrus.py == 0 (T-4-D2)
- Schemas committeados: solo type names en `schema`; `sample_params` contiene metadata (id_cuenta `5208`, fechas) — auditoría manual (T-4-I4)

## Unregistered flags

Los 4 SUMMARY.md de Phase 4 NO incluyen una sección `## Threat Flags`. Sin embargo, durante esta auditoría se identificaron las siguientes superficies nuevas (no pre-registradas en `<threat_model>` por ausencia de éstos):

| Surface | Where introduced | STRIDE coverage |
|---------|------------------|-----------------|
| `_sync_token_snapshot` + `_async_token_snapshot` capture-by-value | Plan 04-02 main_higyrus.py:2285-2289, 2181 | T-4-I2, T-4-I3 (CLOSED) |
| `probe_auth_401` opt-in `VERIFY_HIGYRUS_BAD_CREDS=1` | Plan 04-02 main_higyrus.py:2042-2117 | T-4-S1, T-4-D2 (CLOSED) |
| `urlencode(... safe="/")` URL pre-attach | Plan 04-04 client.py:190, aio.py:213 | T-4-T2 (CLOSED) |
| Schema snapshot envelope D-21 + D-25 no-overwrite | Plan 04-02 main_higyrus.py:409 | T-4-T4, T-4-I4 (CLOSED) |
| Sentinel `status_code=0` para client-side detection | Plan 04-01 exceptions.py:23, client.py:222 etc. | T-4-T1 (CLOSED) |
| `probe_auth_401` deviation: `configure(password=...)` directo (vs Phase 3 IOL CR-03) | Plan 04-02 main_higyrus.py:2051 | T-4-I3 mitigated por snapshots-by-value (CLOSED) |

Todas mapean a threats CLOSED en el registro retroactivo de esta SECURITY.md. Ninguna queda sin cobertura.

## Phase outcome

**SECURED — 24/24 threats CLOSED.**

- **Mitigated:** 19 threats con evidencia en file:line
- **Accepted (documented):** 5 threats con rationale
- **Open (BLOCKER):** 0

La fase no introduce nueva superficie de ataque sin mitigar. La implementación de los 4 Plans (04-01..04-04) cubre los controles defensivos declarados en `04-CONTEXT.md` D-HIGY-1..18 y los reviews WR-01..WR-04 aplicados durante el ciclo. La revisión humana pre-commit del Plan 04-02 Task 2.3 cubrió la inspección manual de los 5 schema snapshots y el findings markdown (T-4-I4, T-4-I9).

## Outstanding items (NO security-blocking)

Los siguientes hallazgos quedan documentados pero NO bloquean Phase 4:

- **F-01 EXPECTED** (SHAPE) — `Posicion.disponibleAjustado` FCI-conditional, documented in `models.py:197-199`. Polish futuro: upgrade a `float | None`.
- **F-02 OPEN** (NO-DATA) — `get_listado_cuentas` retorna 0 cuentas vs 8771 en smoke pre-fase. NO security-relevant (override D-HIGY-11 unblockea downstream). Causa raíz deferred fuera de Phase 4.
- **Cosmetic** — findings markdown header tiene doble `-client` (`# Findings: higyrus-client-client`). NO security-relevant; passes `grep -F` substring match per acceptance criteria.

---
**Auditor:** Claude (gsd-secure-phase, retroactive-STRIDE)
**Last verified:** 2026-06-09
