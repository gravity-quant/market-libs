---
phase: 03-iol-verification
plan: 02
subsystem: iol-verification-driver
tags: [verification, driver, probes, live-api, schema-snapshot, oauth, dual-sync-async]
requires:
  - "03-01: cliente IOL con _refresh_token state, _refresh() y _ensure_token fallback (sync+async)"
  - "Phase 2 helpers verificación: verification.findings.append_finding, write_findings, schema_of, safe_print, require_env"
  - "main_ambito_financiero.py como analog directo (estructura, _next_fid, _last_business_day, schema envelope D-21, antibot try/finally, IN-03 contextlib.suppress)"
provides:
  - "main_iol.py reescrito como driver completo con 15 probes nombrados en orden D-IOL-5"
  - "ProbeResult dataclass + _next_fid + _last_business_day helpers reutilizables por probes"
  - "Cascade SKIPPED via _auth_failed flag module-level (D-IOL-3)"
  - "_write_or_check_schema helper interno para 4 schema snapshots (D-25 no-overwrite-on-drift)"
  - "Driver listo para primer live run controlado por humano (Plan 03-03 Task 3.2)"
affects:
  - "Driver run manual `uv run --package iol-client python main_iol.py` — no se ejecuta en este plan"
  - "Tests pytest preexistentes (189) corren sin regresiones; el driver NO entra al testpaths"
tech-stack:
  added: []
  patterns:
    - "Probe shape: cada probe captura excepciones (IOLAuthError → AUTH, IOLAPIError → ERROR-MAP, Exception genérica → ERROR-MAP) y emite append_finding + ProbeResult FINDING"
    - "Cascade SKIPPED: flag módulo `_auth_failed` único compartido sync+async; cada probe downstream chequea al inicio"
    - "Single asyncio.run con contextlib.suppress(Exception) sobre await aio.aclose() (D-IOL-6, IN-03 mirror)"
    - "safe_print con secrets dinámicos `[IOL_USER, IOL_PASSWORD, iol_client.client._refresh_token]` evaluados después de los probes para incluir refresh_token capturado"
    - "Pitfall 2: probe_field_type_map llama `iol_client.client._request` directo al endpoint by_type para capturar envelope crudo (el wrapper público silenciosamente devuelve [] si falta 'titulos')"
    - "WR-01: `exc.status_code` typed directo en todos los handlers, nunca fallback a args"
    - "D-25 no-overwrite-on-drift: _write_or_check_schema escribe en primera corrida, compara en runs subsiguientes, NO sobreescribe si difiere → append_finding SHAPE OPEN"
    - "Try/finally con restore obligatorio en probe_auth_401 (D-IOL-2): `iol_client.configure(password=original_password)` en finally"
key-files:
  created: []
  modified:
    - "main_iol.py (1630 líneas; reescrito desde smoke test de 33 líneas)"
decisions:
  - "Cascade SKIPPED implementado vía flag único `_auth_failed: bool` compartido entre surfaces sync y async (D-IOL-3 Discretion). Si CUALQUIER login falla, todos los probes downstream emiten SKIPPED — el más estricto. Alternativa con flags separados sync/async se descartó por simplicidad: un sync OK + async fail haría SKIPPED a los async pero NO retroactivamente a los sync ya ejecutados."
  - "Propagación de payloads sync entre probes vía tuple-return (no cache module-level). Probes 3/5/7/9 devuelven `(ProbeResult, payload | None)` y main() guarda el payload en variables locales que luego pasa a probes 11/12/13. Async análogo via _async_main tupla de 9 elementos."
  - "_next_fid() usa counter global persistente entre probes — los fids se incrementan en orden de aparición (login_sync → login_async → quote_sync → quote_async → ...). No se resetea al inicio de main() porque cada run del driver es una sesión independiente y el findings file es append-only por fid (idempotente)."
  - "Sanity check de los 6 InstrumentType se incluye DENTRO de probe_get_instruments_by_type_sync (probe 9), no como sub-probe separado de probe 12. Comentario explícito en el código: WR-03 (single HTTP call per probe) aplica al CONCEPTO de probe; los 6 HTTP calls al mismo endpoint by_type con types distintos son verificación del MISMO endpoint cubierto por D-IOL-17, no duplicación del concepto-probe."
  - "Pitfall 2 resuelto: el envelope check de `get_instruments_by_type` (clave 'titulos') vive en probe 12 (`probe_field_type_map`), NO en probe 9. probe 12 hace una HTTP call adicional vía `iol_client.client._request` directo al endpoint by_type para capturar el envelope crudo. Es la única duplicación HTTP permitida, documentada inline. probe 9 usa el wrapper público y NO tiene visibilidad del envelope (por construcción del wrapper)."
  - "Async no replica el sanity check de los 6 InstrumentType: el probe 10 solo ejercita el sample principal. Razón: los 6 endpoints son idénticos sync vs async módulo el lock pattern; la paridad estructural se verifica en probe 11 (parity_sync_async) sobre el sample principal. Replicar el sanity en async duplicaría 6 HTTP calls innecesariamente."
  - "probe_refresh_token éxito heurística: (a) `_refresh_token != None` antes del call (si None → finding sin proceder); (b) tras forzar `_token_expires_at = 0.0` y disparar un endpoint autenticado: `_refresh_token` post != None (no se perdió, Pitfall 3); (c) `_token_expires_at` renovado > time.time(); (d) `_token` cambió (token_before != token_after). Cualquier check fallido emite finding AUTH OPEN con detalle específico. Reporta `rotated` vs `preserved` en el detail del ProbeResult según si `refresh_after != refresh_before`. NO ejercita la rama refresh-fails-fallback-to-password en vivo (D-IOL-11 explícito — mocked-only)."
  - "safe_print evalúa secrets DESPUÉS de los probes (no antes): la lista comprensión recorre `os.getenv('IOL_USER')`, `os.getenv('IOL_PASSWORD')`, `iol_client.client._refresh_token` AL FINAL de main(), de modo que el _refresh_token capturado por login() o por refresh path está incluido en la redacción de las líneas PROBE y SUMMARY. Filtro `if v and len(v) >= 4` evita el bug `replace('', marker)` documentado en verification/redaction.py."
  - "Schema snapshot del endpoint `get_instruments_by_type` usa el envelope CRUDO (con clave 'titulos') capturado por probe 12, NO el unwrapped list devuelto por el wrapper público. Razón: el snapshot debe detectar drift de la clave envelope (IOL-04). Si probe 12 no logró capturar el envelope (HTTP error), el snapshot se SALTA para by_type (queda registrado en `skipped=` del detail)."
  - "probe_field_type_map clases de finding emitidas (D-IOL-15):"
  - "  • SHAPE: missing envelope key 'titulos' (Pitfall 2 hit)"
  - "  • SHAPE: envelope['titulos'] no es list"
  - "  • SHAPE: get_instruments_by_type tipo top-level no-dict"
  - "  • SHAPE: missing assumed key `<key>` in get_quote / get_historical_quotes[0]"
  - "  • SHAPE: type drift on `<key>` in get_quote / get_historical_quotes[0]"
  - "  • ERROR-MAP: _request directo a by_type falló (defensa para Pitfall 2)"
metrics:
  duration: "47 minutos"
  completed: "2026-06-06"
---

# Phase 3 Plan 02: Rewrite main_iol.py driver Summary

Re-escritura completa de `main_iol.py` desde un smoke test de 33 líneas a un driver de verificación en vivo de 1630 líneas con 15 probes nombrados en orden D-IOL-5; ejercita la superficie pública sync+async del cliente IOL contra `api.invertironline.com`, verifica el fix IOL-07 in-vivo (Plan 03-01) vía `probe_refresh_token`, produce 4 schema snapshots committeables (D-21 envelope, D-25 no-overwrite) y findings clasificados (SHAPE/AUTH/ERROR-MAP/PARAM/SYNC-ASYNC-DRIFT) cuando detecta drift contra el contrato asumido.

## Files Created

(none — el plan modifica `main_iol.py` existente)

## Files Modified

| File | Change |
|------|--------|
| `main_iol.py` | Reescrito completo: 33 → 1630 líneas; 15 probes nombrados, ProbeResult dataclass, cascade SKIPPED via `_auth_failed`, single asyncio.run + IN-03 aclose suppress, schema snapshot helper con D-25, safe_print con secrets dinámicos. |

## Approach Used

Replicar el patrón Phase 2 (`main_ambito_financiero.py`) con 8 probes adicionales y 3 adaptaciones nuevas para IOL: (a) auth real OAuth con cascade SKIPPED flag; (b) probe_refresh_token in-vivo (verifica Plan 03-01); (c) Pitfall 2 envelope check para `get_instruments_by_type` vía `_request` directo. Mantener todos los invariantes Phase 2 (D-21 envelope schema, D-25 no-overwrite, IN-03 contextlib.suppress, WR-01 typed status_code, WR-03 single HTTP call concept).

## Final Driver Structure — Signatures

```python
ProbeResult(name: str, status: str, detail: str)  # frozen+slots dataclass

# Helpers
def _next_fid() -> str
def _last_business_day(today: dt.date) -> dt.date
def _write_or_check_schema(
    func_name: str, endpoint_template: str, sample_params: dict[str, Any],
    raw_payload: Any, base_url: str,
) -> tuple[str, str]  # (status, detail) — internal helper para probe 13

# Probes en orden D-IOL-5
def probe_login_sync() -> ProbeResult
async def probe_login_async() -> ProbeResult
def probe_get_quote_sync() -> tuple[ProbeResult, dict[str, Any] | None]
async def probe_get_quote_async() -> tuple[ProbeResult, dict[str, Any] | None]
def probe_get_historical_quotes_sync(today: dt.date) -> tuple[ProbeResult, list[dict[str, Any]] | None]
async def probe_get_historical_quotes_async(today: dt.date) -> tuple[ProbeResult, list[dict[str, Any]] | None]
def probe_get_instruments_sync() -> tuple[ProbeResult, Any]
async def probe_get_instruments_async() -> tuple[ProbeResult, Any]
def probe_get_instruments_by_type_sync() -> tuple[ProbeResult, list[dict[str, Any]] | None]
async def probe_get_instruments_by_type_async() -> tuple[ProbeResult, list[dict[str, Any]] | None]
def probe_parity_sync_async(
    quote_sync, quote_async, historical_sync, historical_async,
    instruments_sync, instruments_async, by_type_sync, by_type_async,
) -> ProbeResult
def probe_field_type_map(
    quote, historical, instruments_by_type_envelope,
) -> tuple[ProbeResult, dict[str, Any] | None]
def probe_schema_snapshot(
    today, quote, historical, instruments, by_type_envelope,
) -> ProbeResult
def probe_refresh_token() -> ProbeResult
def probe_auth_401() -> ProbeResult

# Async wrapper + entry point
async def _async_main(today: dt.date) -> tuple[...]  # 9-tuple con probes 2/4/6/8/10
def main() -> None
```

## Async Payload Propagation Pattern

`_async_main` corre los 5 probes async en secuencia dentro de un único `asyncio.run()` y termina con `await aio.aclose()` en `contextlib.suppress(Exception)` (D-IOL-6, IN-03). Devuelve una tupla de 9 elementos (5 ProbeResult + 4 payloads necesarios para probes 11/12/13 del lado async). `main()` desempaca esa tupla y luego corre los probes sync intercalando los resultados en orden D-IOL-5 (login_sync, login_async, quote_sync, quote_async, historical_sync, ...).

## Cascade SKIPPED Implementation

Flag único `_auth_failed: bool = False` + `_auth_failure_reason: str = ""` a nivel módulo. `probe_login_sync` y `probe_login_async` los setean en su except `IOLAuthError`. Cada probe downstream (3-15) chequea al inicio:

```python
if _auth_failed:
    return ProbeResult("<name>", "SKIPPED", f"auth failed: {_auth_failure_reason}"), None
```

Flag único (no separado sync/async) por simplicidad: si CUALQUIER login falla, los probes downstream skipean — incluso si solo falla async, los sync que aún no corrieron también skipean (los sync ya ejecutados quedan con su resultado real).

## probe_get_instruments_by_type Resolución de Tensiones

WR-03 (single HTTP call per probe) + D-IOL-17 (sanity 6 types) + Pitfall 2 (envelope check):

- **Probe 9 (sync):** wrapper público `get_instruments_by_type("acciones")` para el sample principal (1 HTTP call) + sanity loop sobre los 6 InstrumentType type-only assertion (`isinstance(list)` + `len > 0` + `isinstance(list[0], dict)`). Total: 7 HTTP calls al mismo endpoint by_type con types distintos. Comentario inline justifica que WR-03 aplica al CONCEPTO de probe, no al número exacto de HTTP requests cuando la verificación pertenece al MISMO endpoint cubierto por D-IOL-17.
- **Probe 10 (async):** solo el sample principal con `aio.get_instruments_by_type("acciones")`. Sin sanity loop (los 6 types son idénticos sync vs async módulo lock pattern; la paridad estructural se verifica en probe 11 sobre el sample principal).
- **Probe 12 (field_type_map):** captura el envelope crudo vía `iol_client.client._request("GET", "/api/v2/Cotizaciones/acciones/argentina/Todos")` directo (NO el wrapper). Esta es la ÚNICA duplicación HTTP permitida, documentada inline con el código de Pitfall 2. Razón: el wrapper público hace `data.get("titulos", [])` y devuelve `[]` silenciosamente si la clave falta, ocultando el drift IOL-04.

El envelope crudo capturado en probe 12 se devuelve también al main() (tuple-return) para que probe 13 (schema_snapshot) lo reuse sin volver a llamar al endpoint.

## probe_refresh_token Heurística de Éxito (D-IOL-11)

1. Verifica `iol_client.client._refresh_token is not None` antes del call (sino: finding AUTH OPEN "login() no capturó refresh_token" y retorna sin proceder).
2. Captura `token_before = iol_client.client._token`.
3. Fuerza `iol_client.client._token_expires_at = 0.0` para gatillar el branch refresh en `_ensure_token`.
4. Dispara un call autenticado barato: `iol_client.get_instruments("argentina")`.
5. Captura `token_after`, `refresh_after`, `expires_at_after`.
6. Tres chequeos en orden:
   - Si `refresh_after is None` → finding AUTH OPEN "refresh path borró _refresh_token (Pitfall 3 violation)".
   - Si `expires_at_after <= time.time()` → finding AUTH OPEN "_token_expires_at no se renovó".
   - Si `token_before == token_after` → finding AUTH OPEN "_token no cambió después de forzar expiry".
7. Éxito: `ProbeResult("refresh_token", "PASS", f"refresh path verified — token rotated, _refresh_token={'rotated' if refresh_after != refresh_before else 'preserved'}")`.

NO ejercita la rama refresh-fails-fallback-to-password en vivo (D-IOL-11 explícito — esa cobertura es mocked-only en tests del Plan 03-01).

## append_finding Call Sites en el Driver

48 call sites distribuidos por probe (orden de aparición):

| Probe | Class(es) emitidas | Total sites |
|-------|-------------------|-------------|
| probe_login_sync | AUTH | 1 |
| probe_login_async | AUTH | 1 |
| probe_get_quote_sync | AUTH, ERROR-MAP (×2), PARAM | 4 |
| probe_get_quote_async | AUTH, ERROR-MAP (×2) | 3 |
| probe_get_historical_quotes_sync | AUTH, ERROR-MAP (×2) | 3 |
| probe_get_historical_quotes_async | AUTH, ERROR-MAP (×2) | 3 |
| probe_get_instruments_sync | AUTH, ERROR-MAP (×2) | 3 |
| probe_get_instruments_async | AUTH, ERROR-MAP (×2) | 3 |
| probe_get_instruments_by_type_sync | AUTH, ERROR-MAP (×2), SHAPE (sanity 6) | 4 |
| probe_get_instruments_by_type_async | AUTH, ERROR-MAP (×2) | 3 |
| probe_parity_sync_async | SYNC-ASYNC-DRIFT (por endpoint que difiere) | 1 |
| probe_field_type_map | ERROR-MAP, SHAPE (envelope ×3), SHAPE (quote drift ×2), SHAPE (historical drift ×2) | 8 |
| probe_schema_snapshot | (vía _write_or_check_schema) SHAPE | 1 |
| probe_refresh_token | AUTH (×4), ERROR-MAP | 5 |
| probe_auth_401 | AUTH (EXPECTED), AUTH (OPEN ×3) | 4 |
| Helper _write_or_check_schema | SHAPE (D-25 drift) | 1 |

Total: 48 sitios. Los call sites con `status=OPEN` esperan revisión humana en checkpoint del Plan 03-03; `status=EXPECTED` es terminal documentado.

## safe_print Secrets — Orden de Evaluación

```python
secrets = [
    v
    for v in (
        os.getenv("IOL_USER"),
        os.getenv("IOL_PASSWORD"),
        iol_client.client._refresh_token,  # post-login, post-refresh
    )
    if v and len(v) >= 4
]
for r in results:
    safe_print(f"PROBE {r.name}: {r.status} {r.detail}".rstrip(), secrets=secrets)
safe_print(f"SUMMARY: ...", secrets=secrets)
```

La evaluación ocurre DESPUÉS de todos los probes, por lo que el `_refresh_token` capturado por probe_login_sync (o rotado por probe_refresh_token) ya está en el módulo y entra a la lista. El filtro `len(v) >= 4` evita el bug `replace("", marker)` documentado en `verification/redaction.py`.

## Deviations from Plan

None — plan executed exactly as written. Las únicas decisiones discrecionales (cascade SKIPPED flag único, fid counter global, sanity check en probe 9, envelope `_request` en probe 12) están explicitadas en la sección Decisions del frontmatter y discutidas en el cuerpo del plan como Discretion del implementador.

## Verifications

### Automated (Task 2.1)

| Check | Result |
|-------|--------|
| `uv run python -c "import main_iol; ..."` (19 entries) | All present |
| `uv run mypy main_iol.py` | Success: no issues |
| `uv run ruff check main_iol.py` | All checks passed |
| `uv run ruff format --check main_iol.py` | already formatted |
| Static invariants (`time.sleep` ausente, `asyncio.run(` count == 1, `VERIFY_IOL_BAD_CREDS` present, `_INVALID` present, `contextlib.suppress` present, `exc.args[0]` ausente) | All OK |
| `grep -v '^#' main_iol.py \| grep -c 'safe_print('` | 3 (≥ 2) |
| `grep -c 'append_finding(' main_iol.py` | 48 (≥ 6) |
| `grep -v '^#' main_iol.py \| grep -c 'iol_client.client._refresh_token'` | 4 (≥ 2) |
| `uv run pytest -q` | 189 passed, 1 deselected (live marker preexistente) — sin regresiones |

### Manual / Not Executed In This Plan

- Live run del driver contra `api.invertironline.com` — Plan 03-03 Task 3.2 con checkpoint humano.
- Commit de `.planning/verification/iol-client-findings.md` y `.planning/verification/schemas/iol-client/*` — Plan 03-03 Task 3.3.

## Self-Check: PASSED

- `main_iol.py` exists at `/Users/sebadlf/development/becerra/market-libs/.claude/worktrees/agent-afd63c14956bd34cb/main_iol.py` — FOUND
- Task commit `10dac31` — FOUND on `worktree-agent-afd63c14956bd34cb` branch

## What's Next

- **Plan 03-03 (Wave 3):** Tests Verified-live + Regressions sections + primer live run del driver con checkpoint humano + commit de findings markdown y 4 schema snapshots baseline.
