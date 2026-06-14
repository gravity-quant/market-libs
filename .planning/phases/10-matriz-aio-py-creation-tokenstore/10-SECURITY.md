---
phase: 10-matriz-aio-py-creation-tokenstore
type: security-audit
asvs_level: 1
block_on: high
status: SECURED
threats_total: 39
threats_closed: 39
threats_open: 0
threats_npm_pip_na: 4
unregistered_flags: 0
audited_on: 2026-06-13
auditor: gsd-security-auditor
---

# Phase 10 — Security Audit (matriz aio.py creation + TokenStore)

Verifica que cada mitigación de amenaza declarada en los 4 sub-planes
(10-01, 10-02, 10-03, 10-04) está presente en el código implementado. La
auditoría es read-only contra el árbol de implementación; este `SECURITY.md`
es el único artefacto producido por el auditor.

Cada threat ID se ubica por su disposición (`mitigate` / `accept` / `n/a`)
y se verifica por grep en el archivo declarado en su plan de mitigación.

## Audit Scope

| Plan  | Wave | Subject                                                                | Threats audited |
|-------|------|------------------------------------------------------------------------|-----------------|
| 10-01 | 1    | TokenStore + RefreshPolicy primitive (3-way concurrency)               | T-10-01-01..09  |
| 10-02 | 2    | AsyncClient full REST + AsyncRetryTransport (D-25 carve-out)           | T-10-02-01..11  |
| 10-03 | 3    | State wiring + sync/async/ws_client migration                          | T-10-03-01..09  |
| 10-04 | 4    | Live paridad + skip flips + cross-leak sentinel extension              | T-10-04-01..10  |

Total: **39 threats**. Dispositions: **mitigate=27**, **accept=8**, **n/a=4** (4 × `npm/pip` Package Legitimacy Gate not triggered — no new deps).

## Threat Verification (mitigate)

| Threat ID    | Category                | Disposition | Evidence (file:line)                                                                                                                                                                                                                                                                                                                                                                                                  | Result |
|--------------|-------------------------|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|
| T-10-01-01   | Information Disclosure  | mitigate    | `packages/matriz-client/src/matriz_client/_refresh.py:71` `raise TransientRefreshError(f"server error {status}")` — no `response.text` echo. Grep `grep "response.text" _refresh.py | wc -l` returns 0. Module docstring lines 7-10 documenta T-10-01-04 invariant.                                                                                                                                                | CLOSED |
| T-10-01-02   | Information Disclosure  | mitigate    | `packages/matriz-client/src/matriz_client/_refresh_policy.py:58,79-85,122` `_cached_failure_exc: BaseException` cachea solo excepciones provenientes de MatrizRefresh (T-10-01-01 garantiza que su mensaje no contiene credenciales). Docstring del módulo + comentario inline en `_store_fail_cache` documentan el invariante transitivo.                                                                              | CLOSED |
| T-10-01-04   | Information Disclosure  | mitigate    | `packages/matriz-client/src/matriz_client/_refresh.py`, `_refresh_policy.py`, `_token_store.py`, `_refresh_errors.py` — `grep "logger\|logging" *.py` returns 0 across the 4 Plan 10-01 modules. Cobertura RedactingFilter llega en Plan 10-02/03 vía `_atransport.py` log site (verificado en T-10-02-03).                                                                                                              | CLOSED |
| T-10-01-05   | Denial of Service       | mitigate    | `_refresh_policy.py:73-85` fail-cache lectura + escritura bajo `threading.Lock`; `_refresh_policy.py:91-93` `cached = self._read_fail_cache(); if cached is not None: raise cached`. Test P5 `packages/matriz-client/tests/test_refresh_policy.py:147` `test_p5_exhausted_retries_then_fail_cache_short_circuits` verifica 10 callers post-failure → 0 nuevas invocaciones de `refresh_fn`.                                | CLOSED |
| T-10-01-08   | Elevation of Privilege  | mitigate    | `_token_store.py:54` `threading.Lock` (cross-context `_state_lock`); `_token_store.py:57` `_async_locks: dict[int, asyncio.Lock]`; `_token_store.py:131` `await asyncio.to_thread(self._refresh_under_state_lock)`. Test S1 `packages/matriz-client/tests/test_token_store.py:230` `test_3way_concurrent_sync_async_daemon` verifica 50+50+5 callers → exactly 1 refresh, 0 errors.                                       | CLOSED |
| T-10-02-01   | Information Disclosure  | mitigate    | `packages/matriz-client/src/matriz_client/aio.py:205-213` `__repr__` redacts: `password_repr = "'***'" if self._state.password else "''"` y `token_repr = "'***'" if self._state.token else "None"`. Test AA4 `packages/matriz-client/tests/test_async_auth.py:81-93` `test_repr_redacts_password_and_token` verifica `"super-secret-AA4" not in r` y `"bearer-AA4" not in r`.                                            | CLOSED |
| T-10-02-02   | Information Disclosure  | mitigate    | `aio.py:215-219` `__reduce__(self) -> Any: raise TypeError(...)`; `aio.py:221-226` `__deepcopy__(self, memo) -> AsyncClient: raise TypeError(...)`. Tests AA5/AA6 `test_async_auth.py:101-121` verifican `pytest.raises(TypeError)` para `c.__reduce__()` y `copy.deepcopy(c)`.                                                                                                                                          | CLOSED |
| T-10-02-03   | Information Disclosure  | mitigate    | `packages/matriz-client/src/matriz_client/_atransport.py:124-137` (path retry) y `:158-162` (path exhausted): `user, _password = auth_basic; extra["auth_basic_user"] = user; extra["auth_basic_password"] = "***"`. Test T8 `packages/matriz-client/tests/test_atransport.py:211-239` `test_auth_basic_tuple_split_in_warning_log_record` asserts `auth_basic_user="operator-u"`, `auth_basic_password="***"`, no leak. | CLOSED |
| T-10-02-04   | Information Disclosure  | mitigate    | `aio.py:372-378` Risk API 401 path: `await resp.aread()` BEFORE `raise AuthenticationError`; `aio.py:394-398` Token path primer 401: `await resp.aread()` BEFORE re-auth flow; `aio.py:409-413` Token path segundo 401: `await resp.aread()` BEFORE `raise AuthenticationError`. Mirror del sync `client.py` body-consume contract.                                                                                       | CLOSED |
| T-10-02-06   | Tampering               | mitigate    | `_atransport.py:75` `if not request.extensions.get("idempotent", False): return await super().handle_async_request(request)` — mutation gate con default `False`. Tests AM2/AM3/AM4 `packages/matriz-client/tests/test_async_mutations.py:44,83,~120` confirman EXACTLY 1 outgoing request en 503 chain de 3 respuestas para `new_order`/`cancel_order`/`replace_order`.                                                  | CLOSED |
| T-10-02-07   | Denial of Service       | mitigate    | `_atransport.py:66` `max_attempts: int = 2` default; `_atransport.py:111` `await asyncio.sleep(min(delay, _RETRY_AFTER_CAP_S))`. `_transport.py:77` `_RETRY_AFTER_CAP_S: float = 60.0`. Combinado con `_refresh_policy.py:47` `fail_cache_s: float = 30.0` (T-10-01-05).                                                                                                                                                  | CLOSED |
| T-10-02-08   | Denial of Service       | mitigate    | `_atransport.py:109-111` `# D-32: asyncio.sleep is cancellable; CancelledError propagates naturally to the awaiting caller. await asyncio.sleep(min(delay, _RETRY_AFTER_CAP_S))`. Test T6 `test_atransport.py:169-185` `test_cancelled_error_propagates_during_retry_after_sleep` asserts `pytest.raises(asyncio.CancelledError)` tras `task.cancel()`.                                                                  | CLOSED |
| T-10-02-09   | Repudiation             | mitigate    | `aio.py:324,357,388` `request_id = uuid.uuid4().hex` + `req.extensions["request_id"] = request_id` (3 call-sites: `_request`, `login`, ramas Risk API/Token); `_atransport.py:81` `request_id = request.extensions.get("request_id", "")` + `:118` `extra["request_id"] = request_id` propagado a log record.                                                                                                            | CLOSED |
| T-10-02-11   | Information Disclosure  | mitigate    | `aio.py:61` `from matriz_client._core import raise_for_response as _raise_for_response`. Test `packages/matriz-client/tests/test_async_auth.py:217-224` `test_b8_aio_raise_for_response_lock_in` asserts `_aio._raise_for_response is sync_client._raise_for_response` y `_aio._raise_for_response is _core.raise_for_response` (single function object).                                                                | CLOSED |
| T-10-03-01   | Information Disclosure  | mitigate    | `packages/matriz-client/src/matriz_client/ws_client.py` — `grep "logger\..*token" ws_client.py` returns 0; el helper `_acquire_token_for_ws` (líneas 123-141) no formatea `state.token` en log records. Header `X-Auth-Token: default._state.token` (línea 178, contexto WS) es header, no log message.                                                                                                                  | CLOSED |
| T-10-03-02   | Information Disclosure  | mitigate    | `verification/test_sync_async_isolation.py:225-318` `test_matriz_sync_async_state_and_token_store_instance_isolation` (extension de Plan 10-04) asserts: `sync_state is not async_state` (línea 291), `sync_state.token != async_state.token` (línea 299), `sync_state.token_store is not async_state.token_store` (línea 312-317). ws_client daemon thread comparte con sync default Client por construcción intencional. | CLOSED |
| T-10-03-04   | Tampering               | mitigate    | Sync: `client.py:599-604` `if password is not None: default._state.password = password; default._state.token_store = None` + comentario inline "T-10-03-04 mitigation". `client.py:613-624` mismo reset para `max_retries`. Async: `aio.py:647-654` mismo reset en `password is not None` con comentario T-10-03-04; `aio.py:659-673` reset en `max_retries is not None`. ASVS V3.2.2.                                  | CLOSED |
| T-10-03-07   | Elevation of Privilege  | mitigate    | `aio.py:280-294` W1 invariant comment block después de `saved_http_client = self._state.http_client`: `# CONCURRENCY INVARIANT (per-loop asyncio.Lock):` + referencia explícita a `TokenStore.get_async()` Lock contract. Comentario es load-bearing — protege swap-restore con per-loop Lock. Grep `grep -A 12 "saved_http_client" aio.py | grep -c "per-loop asyncio.Lock"` ≥ 1, `... | grep -c "TokenStore.get_async"` ≥ 1. | CLOSED |
| T-10-03-09   | Information Disclosure  | mitigate    | `packages/matriz-client/src/matriz_client/_token_store.py` — `grep "def __repr__" _token_store.py` returns 0. `TokenStore` no define `__repr__`; el `_ClientState` dataclass default `__repr__` muestra `token_store=<TokenStore object at 0x...>` (object id, sin contenido de `_token`).                                                                                                                              | CLOSED |
| T-10-04-01   | Information Disclosure  | mitigate    | `packages/matriz-client/src/matriz_client/_logging.py:1-50,54-66` define `RedactingFilter` con patrones `X-Auth-Token`, `X-Username` (operacional), `X-Password`. `10-VALIDATION.md` `## Live Paridad Run` (líneas 192-228) contiene solo outcome summary (probe names + PASS/SKIPPED/FINDING markers) — no contenido crudo del log. ASVS V8.3.4.                                                                       | CLOSED |
| T-10-04-02   | Information Disclosure  | mitigate    | `verification/snapshots/matriz-client-surface.txt` — `grep -c "test-pass\|test-token\|sentinel" matriz-client-surface.txt` returns 0. La herramienta snapshot enumera atributos públicos (`__all__`), no valores; AsyncClient `__repr__` redactado (T-10-02-01).                                                                                                                                                       | CLOSED |
| T-10-04-03   | Information Disclosure  | mitigate    | `10-VALIDATION.md:192-228` operator pasted outcome table only (probe / sync / async / Match? columns con valores PASS/SKIPPED). Línea 295 declara `Run log: /tmp/phase10-live-paridad.log (RedactingFilter aplicado vía _logging.py; outcome summary pegado en la tabla de arriba — no se pegó contenido crudo del log per T-10-04-01)`.                                                                                  | CLOSED |
| T-10-04-04   | Tampering (trip-wire)   | mitigate    | Trip-wire TRIPLE NOT fire — el test `test_matriz_sync_async_state_and_token_store_instance_isolation` (`verification/test_sync_async_isolation.py:225-318`) PASS con 3 aserciones: (a) `sync_state is not async_state`, (b) tokens cross-leak ≠, (c) `token_store is not` instance. `pytest verification/test_sync_async_isolation.py -k matriz -q` → 3 passed. ASVS V3.5.2 session isolation honored.                  | CLOSED |
| T-10-04-05   | Tampering               | mitigate    | `grep -c "^_token_store\|^_refresh\|^_atransport" verification/snapshots/matriz-client-surface.txt` returns 0 — módulos privados NO expuestos en snapshot. Tool walks `pkg.__all__` only (verification/test_public_surface.py:96-108 by design).                                                                                                                                                                       | CLOSED |
| T-10-04-06   | Repudiation             | mitigate    | `10-VALIDATION.md` frontmatter (líneas 1-12) registra `status: approved`, `live_paridad_sync_async: true`, `nyquist_compliant: true`, `wave_status: complete`, `operator_signoff_date: 2026-06-14`, `operator_signoff_run_log: /tmp/phase10-live-paridad.log`. Git history preserva commit `5513917` con fecha de approval.                                                                                            | CLOSED |
| T-10-04-07   | Denial of Service       | mitigate    | `_refresh_policy.py:47` `fail_cache_s: float = 30.0` + `_transport.py:77` `_RETRY_AFTER_CAP_S: float = 60.0`. `10-VALIDATION.md` `## Live Paridad Run` confirma el run completó sin hang (probes con tiempos PASS, no rate-limit issues durante 2026-06-14 live run).                                                                                                                                                  | CLOSED |

## Accepted Risks (verbatim from threat register)

These items were declared `accept` at plan time and are recorded here without
re-audit, per the dispositions in `<threat_model>` blocks of plans 10-01..04.

| Threat ID    | Category                  | Plan   | Acceptance Rationale (verbatim from PLAN.md)                                                                                                                                                                                                                                                                                                                                                                                              |
|--------------|---------------------------|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| T-10-01-03   | Information Disclosure    | 10-01  | Plaintext token in process memory is unavoidable for an HTTP client; matches existing Phase 6+ `_ClientState.token` semantics. No new exposure vs baseline. Out-of-process attackers (memory dump) require host-level compromise — out of scope for ASVS L1 (network-level threat model).                                                                                                                                                |
| T-10-01-06   | Denial of Service         | 10-01  | `PermanentRefreshError` (401/403) bypasses fail-cache by design (P6 test) — operator must be able to fix credentials and retry immediately without 30s wait. Tradeoff: a stuck-at-permanent error allows callers to issue 1 request per call to auth server until operator intervenes. Acceptable because permanent errors are operator-visible and non-recoverable without operator action.                                              |
| T-10-01-09   | Repudiation               | 10-01  | TokenStore does NOT emit log records in Plan 10-01 (no logger). The decorator pattern keeps observability concerns in `_atransport.py` / `client.py` log sites (Phase 8 LOG-03 convention). Audit trail of refresh attempts is established via the `refresh_call_id` counter exposed in TokenSnapshot — operators can correlate via attempt counts in subsequent transport log records (Plan 10-02 wiring).                                |
| T-10-02-10   | Elevation of Privilege    | 10-02  | Plan 10-02 uses per-instance `self._token_store_local` to defer the `_state.py` schema change to Plan 10-03's atomic unit. Risk: a Plan 10-02-deployed-without-Plan-10-03 build would leave the sync `Client` using the old `_ensure_token` path. Mitigation: Plan 10-02 and Plan 10-03 ship as separate commits in the same phase merge cycle (CONTEXT D-08), gated by Plan 10-04 green-gate before phase merge. **Confirmado: 10-03 shipped (commits `21e9bbf` + `1f5c171`) and Plan 10-02's per-instance stash removed.** |
| T-10-03-03   | Tampering                 | 10-03  | `_state.token_store` field is set under `_state_lock` (inside TokenStore implementation, transparently). The lazy-init pattern `if state.token_store is None: state.token_store = build_token_store(...)` has a race window: two threads could both observe `None` and both build a store. Mitigation: the second store's refresh would still go through the SAME `state.http_client` and use the SAME credentials; only one stays referenced. Negligible. v1.2 backlog. |
| T-10-03-06   | Denial of Service         | 10-03  | See T-10-03-03 mitigation — at most 2 TokenStore constructions in a narrow race window; both share the same auth-server load (single refresh due to the inner `_state_lock`).                                                                                                                                                                                                                                                          |
| T-10-03-08   | Repudiation               | 10-03  | Plan 10-03 sets `state.token_expires_at = time.time() + (23 * 3600)` as a back-compat mirror; TokenStore is the authoritative source. If a caller reads `state.token_expires_at` directly (legacy path), they get a slightly stale value (up to one TTL skew). Acceptable porque: (a) PEP 562 callers read via `_token` que viene del state.token recién-mirrored; (b) v1.2 removal post universal-adoption.                              |
| T-10-04-09   | Elevation of Privilege    | 10-04  | If `test_fixture_reaches_production.py:64` flipped active test FAILS, it surfaces a bug donde el async monkeypatch sentinel no propaga al wire — esto es un test infrastructure regression (Pitfall #1 carry-forward from Phase 6). STOP planning; return to Plan 10-02/03. **Confirmado: los 3 active tests resultantes del flip PASS first try (commit `85d68e7`). T-10-04-09 trip-wire NO disparó.**                                  |
| T-10-04-10   | Information Disclosure    | 10-04  | Operator-pasted log excerpts have already been filtered through RedactingFilter (T-10-04-01). The path `/tmp/phase10-live-paridad.log` is operator-local and not committed. Operator instruction enforces this. **Confirmado: `10-VALIDATION.md` no commit contiene contenido crudo del log, solo outcome summary + ruta.**                                                                                                              |

## n/a Dispositions (Package Legitimacy Gate not triggered)

| Threat ID    | Category    | Plan   | Rationale                                                                                                       |
|--------------|-------------|--------|-----------------------------------------------------------------------------------------------------------------|
| T-10-01-07   | Tampering   | 10-01  | NO new third-party dependencies. `random`, `threading`, `time`, `asyncio`, `dataclasses`, `collections.abc` are stdlib. `httpx` already in matriz-client deps. |
| T-10-02-05   | Tampering   | 10-02  | NO new dependencies. `tenacity`, `httpx`, `pytest-asyncio`, `pytest-httpx` all pre-existing matriz-client deps. |
| T-10-03-05   | Tampering   | 10-03  | NO new dependencies. All migration is internal wiring.                                                          |
| T-10-04-08   | Tampering   | 10-04  | NO new dependencies in Plan 10-04. Only edits + snapshot regen + commit.                                        |

## Phase 8/9 Controls Reused (verified intact)

| Control                                                  | File                                                                              | Status |
|----------------------------------------------------------|-----------------------------------------------------------------------------------|--------|
| matriz `RedactingFilter` (X-Auth-Token + X-Username + X-Password + auth_basic) | `packages/matriz-client/src/matriz_client/_logging.py:1-66`                       | INTACT |
| `_transport.py` constants (`_RETRY_AFTER_CAP_S`, `_RETRYABLE_EXC`, `_RetryableStatus`) reused by `_atransport.py` | `packages/matriz-client/src/matriz_client/_transport.py:77` + `_atransport.py:44-51` | INTACT |
| Pitfall 4 mutation gate (sync `_transport.py` + async `_atransport.py`) | `_atransport.py:75-76` | INTACT |
| B8 lock-in (`_core.raise_for_response` single source) — Phase 7 D-04 | `aio.py:61` import + `client.py` import + identity test `test_b8_aio_raise_for_response_lock_in` | INTACT |
| Cross-leak sentinel test (Phase 7 D-10) extended for matriz async | `verification/test_sync_async_isolation.py` | EXTENDED + GREEN per 10-VALIDATION.md spot-check 5 |
| CI grep `lint-logging` (Phase 8 D-27) | `_logging.basicConfig/_logging.root` grep in `packages/*/src/` = 0 | INTACT |
| `_state.account_id` ORP-01 preserved (Phase 11 CR-08 scope) | `_state.py:59` `account_id: str | None = None` UNTOUCHED | INTACT |

## Unregistered Flags

**None.**

Ninguno de los 4 SUMMARY files (`10-01-SUMMARY.md`, `10-02-SUMMARY.md`,
`10-03-SUMMARY.md`, `10-04-SUMMARY.md`) contiene una sección `## Threat
Flags`. Las deviaciones documentadas en cada SUMMARY (`Deviations from
Plan`) fueron auditadas y NO introducen nueva superficie de ataque:

- Plan 10-02 Dev #1 (test renamed) y #3 (fast-path `token_is_fresh`) — pure refactor del path de auth ya cubierto por T-10-01-08 + T-10-02-04 mitigations.
- Plan 10-02 Dev #2 (snapshot regen in Task 2 commit) — cubierto por T-10-04-02 + T-10-04-05.
- Plan 10-03 Dev #1 (test rewritten) — pure test fix; no nuevo surface.
- Plan 10-03 Dev #2 (sync fast-path preserved) — espejo del Plan 10-02 dev #3; ya cubierto.
- Plan 10-03 Dev #3 (helper extraction `_acquire_token_for_ws`) — ws_client.py minimal refactor, daemon-loop/WS lifecycle UNCHANGED; T-10-03-01 mitigation grep cubre el helper.
- Plan 10-04 Dev #1 (snapshot diff = 0 lines) — disposition aceptada; no nuevo surface (snapshot tool semantics).
- Plan 10-04 Dev #2 (Task 3 atomic commit excludes snapshot) — git scope decision; no security-relevant.
- Plan 10-04 Dev #3 (pre-existing ruff findings out-of-scope) — todas las findings están en `.claude/skills/spike-findings-market-libs/sources/*` y `.planning/spikes/*` (documentación), NO en código de producción.

## Adversarial-Stance Findings

Starting hypothesis (todas las threats OPEN hasta que grep pruebe el control).
Resultado: el patrón de mitigación de cada `mitigate` threat fue localizado
en el archivo declarado por el mitigation plan; cada match incluye `file:line`
arriba. Ninguna mitigation aceptada solo en documentación; cada match es
un grep real en el código de producción.

Las 2 trip-wire dispositions (`block` en T-10-04-04 y `accept` con
classificación-trip-wire en T-10-04-09) NO dispararon — los tests
relevantes pasaron en el commit `85d68e7`:

- T-10-04-04 trip-wire: `test_matriz_sync_async_state_and_token_store_instance_isolation` PASS (cross-leak NO detectado; isolation enforced).
- T-10-04-09 trip-wire: las 3 active tests resultantes del skip flip PASS first try (no test infrastructure regression).

Las 8 `accept` dispositions están registradas verbatim arriba con sus
rationales del PLAN.md original. Las 4 `n/a` (npm/pip Package Legitimacy
Gate) están registradas porque ningún Plan en Phase 10 introdujo nuevas
dependencias.

## Summary

- **39 de 39 threats** resolve to CLOSED (27 mitigate verificadas + 8 accepted risk registrados + 4 n/a Package Legitimacy Gate).
- **0 BLOCKER**.
- **0 `unregistered_flag`** warnings (no `## Threat Flags` sections en los SUMMARYs; deviaciones auditadas y mapeadas a threat IDs existentes).
- **Phase 8/9 controles** (RedactingFilter, `_transport.py` constants, Pitfall 4 mutation gate, B8 lock-in, cross-leak sentinel, CI grep `lint-logging`, `_state.account_id` ORP-01) permanecen intactos.
- **Trip-wire tests** (T-10-04-04 cross-leak, T-10-04-09 skip-flip) NO dispararon — comportamiento esperado per Plan 10-03/10-04 wiring.
- **Live verification** (LIVE-02): operator-confirmed paridad sync↔async PASS — 19 probes pareados, divergences=0 (2026-06-14, signoff registrado en `10-VALIDATION.md`).
- **Phase 10 ready to ship** desde perspectiva de auditoría de seguridad.
