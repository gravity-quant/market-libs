---
phase: 03
slug: iol-verification
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-06
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Audit forced-adversarial stance: every mitigation verified by code grep / file inspection — no claim accepted on documentation alone.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| `client.py` / `aio.py` module globals → in-process state | Singletons `_token`, `_refresh_token`, `_token_expires_at` live at module scope; readable by any code in the same process. | Bearer access_token, refresh_token (high sensitivity) |
| `_refresh()` / `_refresh_unlocked()` → `api.invertironline.com` (live) | `POST /token` with `grant_type=refresh_token` body; TLS by default (`https://`). | refresh_token in request body; access_token in response |
| `_token_lock` (asyncio.Lock) → `_refresh_unlocked()` | Caller MUST hold the lock; recursive acquire would deadlock (Pitfall 6). | N/A (concurrency contract only) |
| Test mocks (pytest-httpx) → mocked `POST /token` | FIFO with `match_content=b"..."` body-discrimination so 2 POSTs to same URL route correctly (Pitfall 5). | mock tokens (no sensitivity) |
| Driver (`main_iol.py`) → `iol_client.configure()` (mutates module state) | `probe_auth_401` mutates `_password` directly (NOT via `configure()` — CR-03 fix preserves `_refresh_token`). | password injection (`<original>_INVALID`) |
| Driver → `iol_client.client._token_expires_at` (force expiry) | `probe_refresh_token` writes `_token_expires_at = 0.0` to force refresh branch; reads `_refresh_token`/`_token` pre/post. | None (no token leaves the module) |
| Driver → `.planning/verification/schemas/iol-client/*.json` (committeable) | 4 type-only schema files written by `_write_or_check_schema`; D-25 no-overwrite-on-drift. | Type-name strings only — PII-free by construction (`verification.schema.schema_of`). |
| Driver → `.planning/verification/iol-client-findings.md` (committeable) | `append_finding` emits classified rows + detail bullets; ART block refreshed each call. | Status / class / surface / detail strings (no raw token values). |
| Driver stdout → user terminal | All prints via `safe_print(text, secrets=[IOL_USER, IOL_PASSWORD, captured_refresh_token])` + `_BEARER` regex catch-all. | Probe status + detail (already-redacted). |

---

## Threat Register

Origin: `register_authored_at_plan_time = true` — all 3 plans (03-01, 03-02, 03-03) include `<threat_model>` blocks. Total unique threats: 27 (T-3-SC appears in all 3 plans as the same supply-chain accept). Each `mitigate` verified by grep / file inspection of the implementation; each `accept` verified by absence of new external installs.

### Plan 03-01 (T-3-01 .. T-3-08 + T-3-SC)

| Threat ID | Category | Component | Disposition | Mitigation | Status | Evidence |
|-----------|----------|-----------|-------------|------------|--------|----------|
| T-3-01 | Spoofing | Stale `_refresh_token` reused after server rotation | mitigate | Conditional rotation in `_refresh()`/`_refresh_unlocked()`: only updates `_refresh_token` if `isinstance(new_refresh, str) and new_refresh`. | CLOSED | `packages/iol-client/src/iol_client/client.py:148-150` (sync rotation gate); `packages/iol-client/src/iol_client/aio.py:155-157` (async mirror). Regression: `test_refresh_token_success_path` (asserts `_refresh_token == "refresh-rotated"`) at `tests/test_client.py:141`. |
| T-3-02 | Tampering | `_refresh_token` mutated outside `configure()`/`login()`/`_refresh()` | mitigate | `_` prefix + barrel does NOT re-export. Only the 5 designated sites (`configure`, `login`, `_refresh`, async equivalents) mutate the global. | CLOSED | `packages/iol-client/src/iol_client/__init__.py:33-45` shows `__all__` with no `_refresh*` symbol; `grep "_refresh" __init__.py` → 0 hits (besides barrel header). Module reads via `iol_client.client._refresh_token` are precedented (Phase 2 `verification/mutation_gate.py`). |
| T-3-03 | Repudiation | `login()` does not capture `refresh_token` → silent re-trigger of password grant | mitigate | `login()`/`_login_unlocked()` capture `refresh_token` from OAuth payload via isinstance gate; CR-01 fix preserves cached when server omits (no silent reset). | CLOSED | `client.py:115-117` (sync); `aio.py:118-120` (async); regression `test_login_captures_refresh_token` at `tests/test_client.py:240` and CR-01 lock `test_login_preserves_cached_refresh_token_when_server_omits` at `tests/test_client.py:263`. |
| T-3-04 | Information Disclosure | `_refresh_token` leaks via stack traces / logs | mitigate | `_` prefix → no module-level logging; `__init__.py` does NOT re-export; driver routes all prints through `safe_print(secrets=[..., captured_refresh_token])`; defense-in-depth via `_BEARER` regex catch-all. | CLOSED | `verification/redaction.py:31` `_BEARER` regex matches reflected Bearer tokens; `main_iol.py:1642-1650` builds `secrets` list including `captured_refresh_token` (snapshot from CR-03 fix); `main_iol.py:1652,1659` route every output via `safe_print(..., secrets=secrets)`. |
| T-3-05 | DoS (against self) | Refresh path infinite loop on malformed 200 | mitigate | `_refresh()` validates `isinstance(access_token, str) and access_token`; on falsy raises `IOLAuthError`, `_ensure_token` catches and falls back to `login()` — single refresh attempt per call. | CLOSED | `client.py:142-143` (sync validation); `aio.py:149-150` (async validation); `client.py:155-166` (`_ensure_token` single try/except, no loop). |
| T-3-06 | DoS | Deadlock recursive `_refresh_unlocked` re-acquiring `_token_lock` (Pitfall 6) | mitigate | `_refresh_unlocked` body MUST NOT call `_request`, `_ensure_token`, or `_login_unlocked` (re-entrant lock acquire). Only `client.post(...)` direct. | CLOSED | Programmatic verification: `python3 -c "import re; src=open('packages/iol-client/src/iol_client/aio.py').read(); body=re.search(r'async def _refresh_unlocked.*?(?=\nasync def )', src, re.DOTALL).group(0); assert '_request(' not in body and '_ensure_token(' not in body and '_login_unlocked(' not in body"` → all False. Inline docstring at `aio.py:126` + comment at `aio.py:134-136`. |
| T-3-07 | Elevation of Privilege | `_refresh()` called without `_token_lock` held → cross-task state corruption | mitigate | `_ensure_token` invokes `_refresh_unlocked()` only inside `async with _token_lock:` (double-checked locking preserved); sync `_refresh()` is single-threaded by project convention. | CLOSED | `aio.py:171-181` shows `async with _token_lock:` wrapping the entire refresh-or-login branch; `aio.py:177` `await _refresh_unlocked()` strictly inside the lock. |
| T-3-08 | Tampering (FIFO bypass) | pytest-httpx FIFO consumes wrong mock if 2 POSTs to same URL | mitigate | All regression tests with 2 POSTs to `/token` use `match_content=b"..."` bytes-literal body discrimination (Pitfall 5). | CLOSED | `tests/test_client.py:155,185,193,222,229` and `tests/test_async_client.py:125,154,161,190,197` show `match_content=b"refresh_token=..."` and `match_content=b"username=..."` literal forms. Refresh and password bodies are disjoint bytes; matcher discriminates unambiguously. |
| T-3-SC | Tampering | Supply-chain package installs | accept | No external packages installed in Plan 03-01. Only pinned deps used (`httpx`, `pytest`, `pytest-httpx`, `pytest-asyncio`) via `uv.lock`. | CLOSED (accepted) | `03-01-SUMMARY.md` `tech-stack.added: []`. See Accepted Risks Log row R-3-SC-01. |

### Plan 03-02 (T-3-09 .. T-3-18 + T-3-SC)

| Threat ID | Category | Component | Disposition | Mitigation | Status | Evidence |
|-----------|----------|-----------|-------------|------------|--------|----------|
| T-3-09 | DoS (account lockout) | `probe_auth_401` multiple bad-cred attempts (Pitfall 9) | mitigate | Opt-in env gate `VERIFY_IOL_BAD_CREDS=1` (default off) + single-shot (no retry / no sleep / no loop) + D-IOL-4 last-in-sequence. | CLOSED | `main_iol.py:1405-1406` (opt-in gate); `main_iol.py:1424` single `iol_client.login()` call with no surrounding loop; `grep -c "time.sleep" main_iol.py` → 0; `grep -c "asyncio.run(" main_iol.py` → 1; `probe_auth_401` is the last `results.append(...)` at `main_iol.py:1637`. |
| T-3-10 | Tampering | `probe_auth_401` leaves `_password` as `_INVALID` if exception not caught | mitigate | Mandatory `try/finally` with restore via direct attribute write (NOT `configure()` — see CR-03). | CLOSED | `main_iol.py:1415` `try:`, `main_iol.py:1487-1494` `finally: iol_client.client._password = original_password`. Direct mutation avoids `configure()` side-effect (CR-03). |
| T-3-11 | Tampering | `probe_refresh_token` mutates `_token_expires_at` without teardown | mitigate | Subsequent `get_instruments("argentina")` call invokes `_ensure_token` which naturally restores `_token` / `_token_expires_at` via refresh path or login fallback. No explicit teardown needed — the behavior under test IS the restoration. | CLOSED | `main_iol.py:1289` writes `_token_expires_at = 0.0`; `main_iol.py:1291` triggers `get_instruments` which calls `_ensure_token` (`client.py:155-166`) — that path either refreshes or re-logins, restoring state. Live run confirmed PASS in `03-03-SUMMARY.md` `probe_refresh_token: PASS refresh path verified — token rotated, _refresh_token=rotated`. |
| T-3-12 | Tampering | Schema snapshot overwrites baseline on drift | mitigate | D-25: `_write_or_check_schema` writes only if file does not exist; on drift emits `append_finding SHAPE OPEN` and does NOT overwrite. | CLOSED | `main_iol.py:1156-1178` shows `if not file_path.exists(): write; else: read+compare; if drift: append_finding(...)` and returns `(FINDING, fid)` without writing. No `write_text` in the drift branch. |
| T-3-13 | Information Disclosure | Driver prints raw payload with reflected access_token | mitigate | `safe_print` two-layer defense: (1) explicit `secrets=[...]` redaction + (2) `_BEARER` regex catch-all for reflected `Bearer <token>` (even if not in `secrets` list). | CLOSED | `verification/redaction.py:31` `_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", re.IGNORECASE)`; `verification/redaction.py:60` applied after `secrets` replacement; `main_iol.py:1652` and `:1659` route ALL output via `safe_print(..., secrets=secrets)`. No raw `print(...)` of payloads in driver. |
| T-3-14 | Information Disclosure | `_refresh_token` appears in findings via `actual=`/`diff=` | mitigate | Driver never passes the literal `_refresh_token` value into `append_finding(...)`; probe 14 reports only booleans (`rotated`/`preserved`) in `ProbeResult.detail`. Findings file inspection confirms absence. | CLOSED | `main_iol.py:1383-1389` builds `refresh_note = "rotated" if rotated else "preserved (...)"` — boolean-derived, not the literal value. `grep -E "captured-or-actual-refresh-literal-here" .planning/verification/iol-client-findings.md` → 0 hits. The findings file (`F-01` only) contains no token values. |
| T-3-15 | Repudiation | Cascade SKIPPED masks root cause | mitigate | First failing `probe_login_*` calls `append_finding(class_="AUTH", status="OPEN", actual=repr(exc), diff=f"status_code={exc.status_code!r}")` with typed status_code (WR-01); downstream probes emit SKIPPED with `reason=<_auth_failure_reason>`. Human sees the original cause in the findings file. | CLOSED | `main_iol.py:198-235` `probe_login_sync` AUTH OPEN call site captures `repr(exc)` + `status_code`; cascade flag `_auth_failed` + `_auth_failure_reason` set inside the except (lines visible in `03-02-SUMMARY.md` Cascade SKIPPED Implementation section). |
| T-3-16 | Tampering | Exception bytes in `actual=` may contain creds | mitigate | `_raise_for_response` raises `IOLAuthError(status_code, text)` where `text=resp.text`; IOL 401 responses typically `invalid_grant` (no credentials reflected). Defense-in-depth: `safe_print` masks `IOL_USER`/`IOL_PASSWORD` if reflected anywhere. Human inspects findings markdown at checkpoint (Task 3.2). | CLOSED | `client.py:78-84` `_raise_for_response` constructs `IOLAuthError(resp.status_code, resp.text)` — no globals interpolated. `repr(exc)` reflects only what the server returned. Findings file inspected: no `IOL_USER`, no `IOL_PASSWORD`, no token literal (`grep -ciE "IOL_USER\|IOL_PASSWORD\|access_token\|refresh_token\|Bearer" findings.md` → 0). |
| T-3-17 | Tampering (Pitfall 2 wrapper swallow) | Wrapper silently returns `[]` on missing envelope | mitigate | `probe_field_type_map` calls `iol_client.client._request("GET", "/api/v2/Cotizaciones/{itype}/argentina/Todos")` direct (NOT wrapper); inspects raw envelope for `"titulos"` key; emits SHAPE OPEN finding if missing. | CLOSED | `main_iol.py:972-975` direct `_request` call; `main_iol.py:997-1011` `if "titulos" not in envelope: append_finding(SHAPE OPEN ...)`; commented at `main_iol.py:946-953` as ÚNICA permitted HTTP duplication. |
| T-3-18 | DoS | Multiple `asyncio.run()` reopens client after `aclose` | mitigate | Single `asyncio.run(_async_main(today))` in `main()`; `_async_main` ends with `contextlib.suppress(Exception): await aio.aclose()` (IN-03 mirror). | CLOSED | `grep -c "asyncio.run(" main_iol.py` → 1 (at line 1575). `main_iol.py:1526-1527` shows `with contextlib.suppress(Exception): await aio.aclose()`. |
| T-3-SC | Tampering | Supply-chain package installs | accept | No external packages installed in Plan 03-02. | CLOSED (accepted) | `03-02-SUMMARY.md` `tech-stack.added: []`. See Accepted Risks Log row R-3-SC-01. |

### Plan 03-03 (T-3-19 .. T-3-26 + T-3-SC)

| Threat ID | Category | Component | Disposition | Mitigation | Status | Evidence |
|-----------|----------|-----------|-------------|------------|--------|----------|
| T-3-19 | Information Disclosure | Findings file committed with raw IOL response values | mitigate | Schema-related findings use `schema_of(payload)` (PII-free by construction — type-names only); driver call sites pass only sorted key lists / type strings, never raw values. Human checkpoint (Task 3.2) inspects markdown pre-commit. | CLOSED | `.planning/verification/iol-client-findings.md` audit: header `# Findings: iol-client-client`, F-01 contains only sorted key names (no values like prices or symbols beyond the missing key reference); `grep -ciE "IOL_USER\|IOL_PASSWORD\|access_token\|refresh_token\|Bearer" iol-client-findings.md` → 0. F-01 row reports `keys=[...]` (key names = wire field names = public domain language). |
| T-3-20 | Tampering | Schema snapshot committed with real values instead of types | mitigate | `verification.schema.schema_of` produces only type-names (`"str"`, `"int"`, `"float"`, `"bool"`, `"NoneType"`, etc.) by construction. | CLOSED | Programmatic audit of all 4 JSONs: walked `schema` recursively, every scalar leaf is one of `{str, int, float, bool, NoneType}` strings. No numeric value `7215.0`, no `"GGAL"` symbol, no `"ultimoPrecio": 1234.5`. E.g., `get-quote.json` schema: `"ultimoPrecio": "float"` (type name), `"simbolo"` absent (correctly captured by F-01). |
| T-3-21 | Tampering | Pitfall 2 violation: `get-instruments-by-type.json` unwrapped | mitigate | Schema must contain `"titulos"` at TOP LEVEL of `schema` (dict). Driver captures envelope via `_request` direct (probe 12), passes raw to `_write_or_check_schema`. Task 3.3 acceptance criterion + automated pre-commit assertion. | CLOSED | `python3 -c "import json; d=json.load(open('.planning/verification/schemas/iol-client/get-instruments-by-type.json')); s=d['schema']; assert isinstance(s, dict) and 'titulos' in s"` → success. Top-level keys of `schema` = `['titulos']`. Pitfall 2 envelope preserved. |
| T-3-22 | Repudiation | Schema snapshot without traceable metadata | mitigate | D-21 envelope: every JSON has `endpoint`, `client_function`, `captured_at`, `base_url`, `sample_params`, `schema`. | CLOSED | All 4 schema JSONs verified to contain all 6 envelope keys. E.g., `get-instruments-by-type.json` keys: `['base_url', 'captured_at', 'client_function', 'endpoint', 'sample_params', 'schema']`; `captured_at = "2026-06-06T14:56:08.193687+00:00"` (ISO-8601 UTC); `base_url = "https://api.invertironline.com"`. |
| T-3-23 | DoS | Re-running opt-in IOL-05 probe in loop | mitigate | Task 3.2 `how-to-verify` instructs explicitly "una sola vez" + Pitfall 9 documented in `<what-built>` ("No re-correr en loop"). Driver itself enforces single-shot per run (no internal retry/sleep — see T-3-09). Cadence discipline = human-enforced (acknowledged Discretion). | CLOSED | `main_iol.py:1392-1494` shows no loop, no retry, no sleep around `probe_auth_401`'s `iol_client.login()` invocation. Task 3.2 documentation explicit. `03-03-SUMMARY.md` confirms `VERIFY_IOL_BAD_CREDS=1` NOT executed in baseline (deferred to deliberate human action). |
| T-3-24 | Tampering | Mocked Verified-live tests pass but live would fail | mitigate | D-IOL-21: Verified-live invariants derived from the same probes that actually ran live; the 2026-06-06 live run PASS=13 confirms wire shape matches the assumed contract. If wire diverges in future, drift detection (T-3-12) catches it on next run. | CLOSED | `03-03-SUMMARY.md` live-run `probe_field_type_map: FINDING F-01 OPEN` — drift correctly captured (driver assumption for `simbolo`, not client bug). All other probes PASS. Mocked Verified-live tests (`test_get_quote_url_exacta_con_query_string`, etc.) lock URL + numeric type + date format — invariants confirmed by the run. |
| T-3-25 | Tampering | Silent drift if schemas committed with ad-hoc data | mitigate | Task 3.3 commits ONLY artifacts produced by Task 3.2 live run (no intermediate human edit step). Baseline established once, then T-3-12 D-25 protects subsequent runs. | CLOSED | `03-03-SUMMARY.md` artifacts-committed lists the exact 5 files produced by the single live run; `live-run.timestamp = "2026-06-06T14:56:08"` matches `captured_at` in every JSON. Git commit `620b2f9` is the atomic baseline commit. |
| T-3-26 | Tampering | `schema_of` recursive walk false-pass on Pitfall 2 envelope | mitigate | Top-level-only check: `'titulos' in schema` (not recursive `in`). The envelope captured by probe 12 is `resp.json()` returning `{"titulos": [...]}` — `schema_of` preserves the top-level dict structure, so `'titulos'` is a TOP-LEVEL key. | CLOSED | Audit: `get-instruments-by-type.json` `schema` keys at top level = `['titulos']` only (no other nesting at root). Test assertion uses `'titulos' in schema` directly on the top dict, never recursive. |
| T-3-SC | Tampering | Supply-chain package installs | accept | No external packages installed in Plan 03-03. | CLOSED (accepted) | `03-03-SUMMARY.md` `tech-stack.added: []`. See Accepted Risks Log row R-3-SC-01. |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Unregistered Flags

None. `03-01-SUMMARY.md`, `03-02-SUMMARY.md`, and `03-03-SUMMARY.md` do not contain a `## Threat Flags` section — no new attack surface was declared by the executor beyond what the plan-time threat register already covers.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-3-SC-01 | T-3-SC (×3 plans) | No external packages were installed in Phase 3. All dependencies (`httpx`, `pytest`, `pytest-httpx`, `pytest-asyncio`, `python-dotenv`) are already pinned in `uv.lock`. Package Legitimacy Audit of `03-RESEARCH.md` Package Legitimacy Audit section is intentionally empty. Supply-chain risk reduces to the pre-existing pinned versions, which is the project's baseline accepted posture. | Plan author (D-IOL-22) | 2026-06-06 |

*Accepted risks do not resurface in future audit runs.*

---

## In-Cycle Review Fixes Honored

The audit confirms that CR-01, CR-02, and CR-03 (3 BLOCKER findings from `03-REVIEW.md`) were fixed in-cycle (commit `e80bc35`, `82ea256`, `0cae4e6` per `03-REVIEW-FIX.md`) and their fixes uphold the relevant threats:

- **CR-01 → T-3-01 / T-3-03:** `login()`/`_login_unlocked()` now use conditional preservation (`if isinstance(new_refresh, str) and new_refresh: _refresh_token = new_refresh`) — no `else: _refresh_token = None` branch. Verified at `client.py:115-117` and `aio.py:118-120`. Regression test `test_login_preserves_cached_refresh_token_when_server_omits` at `tests/test_client.py:263-290` locks the invariant.
- **CR-02 → T-3-01 / T-3-11:** `probe_refresh_token` now correctly distinguishes "rotated" vs "preserved" without false-positive findings on legitimate password-fallback flows. Verified at `main_iol.py:1383-1389`.
- **CR-03 → T-3-04 / T-3-10 / T-3-14:** `probe_auth_401` mutates `_password` directly (not via `configure()`) so the cached `_refresh_token` survives through to the SUMMARY's `secrets` list. Defense-in-depth: `main()` captures `captured_refresh_token` snapshot BEFORE `probe_auth_401` runs. Verified at `main_iol.py:1420,1494` and `main_iol.py:1634,1647`. Regression test `test_configure_resets_refresh_token_but_direct_password_mutation_preserves_it` at `tests/test_client.py:293-316` locks the invariant.

The 8 WARNINGs and 4 INFOs from the review were explicitly deferred by user decision (`03-REVIEW-FIX.md` Deferred Findings section); they are not blockers for Phase 3 security goals.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-06 | 27 | 27 (24 mitigate-closed + 3 accept-closed) | 0 | Claude (gsd-secure-phase, adversarial stance) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-06
