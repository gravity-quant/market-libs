---
phase: 06
slug: compat-safety-net-client-class-skeleton
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-11
verified: 2026-06-11
---

# Phase 06 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
>
> Verification of the threat register declared at plan time across the 7 plans
> (06-01..06-07) plus the post-merge quick-task fixes (260611-u0v). Every threat
> with a `mitigate` disposition was verified against the implementation; the
> single `accept` threat (T-06-13) is recorded in the Accepted Risks Log; the
> `N/A` rows (T-06-SC) are closed by inspecting the squash diff.

---

## Trust Boundaries

Unified across plans 06-01..06-07.

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Test suite → committed snapshot files | CI compares public-surface enumeration vs `verification/snapshots/*.txt`. A malicious/accidental snapshot edit could mask a regression. | Public symbol names + signatures from `__all__` (no secrets). |
| Operator → regen script | `python verification/regen_snapshots.py` rewrites the baselines; diff lands in a commit reviewed at PR time. | Same as above. |
| Phase 6 → future phases (entry-baseline) | `verification/baselines/phase-06-baseline.txt` anchors the pre-refactor test count and coverage%. Retroactive edits could mask later regressions. | Test IDs + counts + coverage% + git_sha anchor. |
| Test → production code path | Guard tests monkeypatch sentinel tokens onto module state and assert the wire request carries them. The whole point of T-06-03 is that this boundary must not have a silent gap. | Sentinel tokens (`SYNC-sentinel-<pkg>`, `ASYNC-sentinel-<pkg>` — non-secret literals). |
| Caller → `Client` instance state | Each `Client()` owns its `_state`; explicit instances must not be mutated by top-level `configure(...)` (Pitfall #2). | Per-instance credentials + token + http_client. |
| PEP 562 shim → legacy module reads | Read-only forwarding via `__getattr__`. Writes to module attributes still land in the module dict (not state); migrated test bodies write to `_state` directly. | Token, http_client, base_url (matriz only). |
| AsyncClient concurrent `_ensure_http_client` (ambito only — B7 divergence) | No lock: a concurrent first-call could create two `httpx.AsyncClient` instances, leaking one. Accepted for low-frequency FX polling. | httpx.AsyncClient instance. |
| ws_client.py → matriz `Client` default singleton | Daemon thread reads `_rest._get_default()._state.{base_url,token}` and calls `_ensure_token()`. | Token + base_url across thread boundary. |
| verification/mutation_gate.py → matriz `_base_url` | Read-only check that gates destructive operations to remarkets sandbox host only. Reads `matriz_client.client._base_url` through the PEP 562 shim (Open Q #4). | Sandbox-vs-prod hostname check. |
| Cross-package test (ambito → matriz state) | `packages/ambito-financiero-client/tests/test_harness_mutation_gate.py` exercises matriz's mutation gate. Migrated to `matriz_client.configure(base_url=url)` (Pitfall #4). | base_url override. |

---

## Threat Register

Unified register from the 7 plans' `<threat_model>` blocks. Each `mitigate` row
was verified by grep + read of the cited implementation file.

| Threat ID | Category | Component | Disposition | Mitigation | Status | Evidence |
|-----------|----------|-----------|-------------|------------|--------|----------|
| T-06-01 (Plan 01) | Tampering | `verification/regen_snapshots.py` snapshot header | mitigate | "DO NOT EDIT BY HAND" header (8 lines `#`, line 8 == `#`); test strips header before equality compare; W3 structural pinning | closed | `verification/regen_snapshots.py`; `verification/test_public_surface.py` `_strip_header` validates 8-line `#` block |
| T-06-01 (Plan 02) | Tampering | guard `monkeypatch.setattr(pkg.client, "_token", ...)` with `raising=False` | mitigate | Per-package guard tests prove sentinel reaches wire; Plans 03-06 each migrated their own guard to `configure(token=...)` | closed | `packages/{iol,higyrus,matriz}-client/tests/test_fixture_reaches_production.py` all use `pkg.configure(token=..., token_expires_at=...)`; ambito uses `configure(base_url=...)` (no auth) |
| T-06-01 (Plan 03) | Tampering | PEP 562 shim allowlist for ambito | mitigate | Shim forwards ONLY `_client`; reads of `_base_url`/`_user_agent` raise `AttributeError` | closed | `packages/ambito-financiero-client/src/ambito_financiero_client/client.py:258-270`; `aio.py:275-287`; `_FORWARDED_HTTP_CLIENT = "_client"` only |
| T-06-01 (Plan 04) | Tampering | PEP 562 shim IOL allowlist (incl. `_refresh_token` per Pitfall #3) | mitigate | `_FORWARDED_TO_STATE` includes `_token`, `_token_expires_at`, `_refresh_token`; aio additionally forwards `_token_lock`; explicit deny-list for `_user`/`_password`/`_base_url` | closed | `packages/iol-client/src/iol_client/client.py:485-520` (`_refresh_token` line 491); `aio.py:450-476` (`_refresh_token` line 454, `_token_lock` line 456); `_DENIED_LEGACY` frozenset |
| T-06-01 (Plan 05) | Tampering | PEP 562 shim higyrus allowlist + `_token_ts → token_expires_at` rename mapping | mitigate | `_FORWARDED_TO_STATE` maps `_token_ts → token_expires_at`; aio also forwards `_token_lock`; unknown names raise `AttributeError` | closed | `packages/higyrus-client/src/higyrus_client/client.py:666-685`; `aio.py:654-669` (rename `_token_ts → token_expires_at` line 656) |
| T-06-01 (Plan 06) | Tampering | PEP 562 shim matriz allowlist + Open Q #4 `_base_url` extension | mitigate | Allowlist includes `_token`, `_token_ts`, `_base_url`; HTTP client names `_session`/`_client` forwarded; `_user`/`_password` raise `AttributeError` | closed | `packages/matriz-client/src/matriz_client/client.py:730-754` (`_base_url` line 733, `_session`/`_client` line 739) |
| T-06-02 (Plan 03) | Information Disclosure | ambito `Client.__repr__` | mitigate | No credentials/tokens in ambito; repr shows base_url + user_agent + `client_open` boolean | closed | `packages/ambito-financiero-client/src/ambito_financiero_client/client.py:130-139`; `aio.py:125-134` |
| T-06-02 (Plan 04) | Information Disclosure | iol `Client.__repr__` / `AsyncClient.__repr__` | mitigate | Redacts password, token, refresh_token (`'***'` when set, `None` when unset) | closed | `packages/iol-client/src/iol_client/client.py:149-160`; `aio.py:120-130` (`password_repr`, `token_repr`, `refresh_repr`) |
| T-06-02 (Plan 05) | Information Disclosure | higyrus `Client.__repr__` / `AsyncClient.__repr__` | mitigate | Redacts password and token; shows client_id (tenant id, not secret) | closed | `packages/higyrus-client/src/higyrus_client/client.py:171-180`; `aio.py:145-154` (`password='***'`, `token='***'`) |
| T-06-02 (Plan 06) | Information Disclosure | matriz `Client.__repr__` / stub `AsyncClient.__repr__` | mitigate | Hardcoded `password='***'`, `token='***'` literals; shows base_url + username | closed | `packages/matriz-client/src/matriz_client/client.py:181-187`; `aio.py:87-93` |
| T-06-03 (Plan 03) | Tampering | ambito conftest migration | mitigate | Ambito has no token — autouse fixture only sets base_url via `configure()`; `monkeypatch` parameter dropped | closed | `packages/ambito-financiero-client/tests/conftest.py:16-27` (only `ambito.configure(base_url=...)`) |
| T-06-03 (Plan 04) | Tampering | iol conftest + 15+ inline monkeypatch sites | mitigate | conftest uses `iol_client.configure(base_url=..., token=..., token_expires_at=...)`; inline sites migrated to `_get_default()._state.<field>` writes; W2 grep gate proved 0 remaining hits | closed | `packages/iol-client/tests/conftest.py:26-52`; quick-task `260611-u0v` qualified 14 sites to `iol_client.client._get_default()` |
| T-06-03 (Plan 05) | Tampering | higyrus conftest + inline sites incl. `_base_url=""` (Pitfall #4) | mitigate | conftest uses `higyrus_client.configure(...)`; inline `_base_url=""` migrated to `configure(base_url="")` | closed | `packages/higyrus-client/tests/conftest.py:23-50`; SUMMARY 06-05 documents grep returns 0 hits |
| T-06-03 (Plan 06) | Tampering | matriz conftest + cross-package ambito test + inline sites | mitigate | conftest uses `matriz_client.configure(...)`; cross-package test migrated to `matriz_client.configure(base_url=url)` | closed | `packages/matriz-client/tests/conftest.py:20-37` (`matriz_client.configure(token=..., token_expires_at=...)`) |
| T-06-04 (Plan 03) | Denial of Service | ambito `Client.close()` / `AsyncClient.aclose()` idempotency | mitigate | `if self._state.http_client is not None: ...; self._state.http_client = None` pattern | closed | `packages/ambito-financiero-client/src/ambito_financiero_client/client.py:120-128`; `aio.py:118-123` |
| T-06-04 (Plan 04) | Denial of Service | iol `Client.close()` / `AsyncClient.aclose()` idempotency | mitigate | Same idempotent pattern; tests enforce | closed | `packages/iol-client/src/iol_client/client.py:141-147`; `aio.py:112-118` |
| T-06-04 (Plan 05) | Denial of Service | higyrus `Client.close()` / `AsyncClient.aclose()` idempotency | mitigate | Same idempotent pattern under `_client_lock` in async | closed | `packages/higyrus-client/src/higyrus_client/client.py:163-169`; `aio.py:135-143` |
| T-06-04 (Plan 06) | Denial of Service | matriz `Client.close()` / stub `AsyncClient.aclose()` idempotency | mitigate | Same idempotent pattern | closed | `packages/matriz-client/src/matriz_client/client.py:174-179`; `aio.py:80-85` |
| T-06-05 (Plan 04) | Information Disclosure | iol `refresh_token` in `__repr__` | mitigate | Redact in repr: `refresh_token={'***' if self._state.refresh_token else None}` | closed | `packages/iol-client/src/iol_client/client.py:153, 159`; `aio.py:123, 129` (`refresh_repr` line) |
| T-06-06 (Plan 05) | Tampering | higyrus URL-encoding `safe="/"` quirk | mitigate | Preserved verbatim in `Client._request` and `AsyncClient._request`; regression test guards | closed | SUMMARY 06-05 cites `test_url_encoding_preserves_slash_in_query` + async mirror; ruff/mypy clean on 12 source files |
| T-06-07 (Plan 06) | Elevation of Privilege | mutation gate bypass via `_base_url` shim | mitigate | Shim only changes storage location; gate logic in `verification/mutation_gate.py:55` compares against sandbox hostname unchanged | closed | SUMMARY 06-07 audit detail: "sandbox=True / prod=False / no VERIFY_MUTATING=False" passed; `mutation_gate.py` untouched |
| T-06-08 (Plan 01) | Information Disclosure | snapshot file contents | accept | Snapshot lines contain only public symbol names + signatures from `__all__`; `_state` and credentials are NOT in `__all__` | closed | See Accepted Risks Log; `verification/snapshots/*.txt` inspected — only type annotation names like `token: 'str \| None' = None`, no real credentials |
| T-06-09 (Plan 02) | Information Disclosure | sentinel strings (`SYNC-sentinel-<pkg>`) in CI logs | accept | Non-secret literal strings used only in tests; intentionally distinct for forensic localization | closed | See Accepted Risks Log; sentinels are visible by design in `packages/*/tests/test_fixture_reaches_production.py` |
| T-06-10 (Plan 07) | Tampering | snapshot file regression unnoticed | mitigate | Operator review of `git diff verification/snapshots/`; D-06 additive-only invariant + W3 header invariant | closed | SUMMARY 06-07: "Snapshot regen idempotent (regen + git diff --exit-code, exit 0)"; D-06 additive verified by SUMMARY 06-03/04/05/06 |
| T-06-11 (Plan 07) | Denial of Service | CI matrix flaky failure | accept | Operator re-runs; persistent failures revert offending plan | closed | See Accepted Risks Log; SUMMARY 06-07 reports 11/11 PASS on 3.12 + 3.13 |
| T-06-12 (Plan 01) | Tampering | `verification/baselines/phase-06-baseline.txt` retroactive edit | mitigate | File embeds `git_sha:` field at capture time; PR review is the final gate | closed | `verification/baselines/phase-06-baseline.txt:10` (`git_sha: d6aa845d900893e26c2b14c9769a738691af7766`) |
| T-06-13 (Plan 03) | Resource exhaustion | leaked `httpx.AsyncClient` from B7 lock-less `_ensure_http_client` | accept | Documented in `_ensure_http_client` docstring + `_state.py`; bounded by process lifetime; low-frequency FX polling | closed | See Accepted Risks Log; `packages/ambito-financiero-client/src/ambito_financiero_client/_state.py:14-21` documents acceptable-leak rationale |
| T-06-14 (Plan 07) | Tampering | mutation_gate audit miss | mitigate | Plan 07 Task 1 step 8 audited sandbox-vs-prod; PASS recorded | closed | SUMMARY 06-07: "AUDIT PASSED: mutation_gate.py works correctly with matriz shim (sandbox=True, prod=False)" |
| T-06-SC | Tampering | npm/pip/cargo installs | N/A | No new dependencies added across the 7 plans + quick-task | closed | `git show fd7ab43 -- pyproject.toml` shows only `testpaths`/`pythonpath` additions; no `dependencies` or `dev` block changed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

### Additional verification spot-checks (free finds)

- **Committed `.env` files:** none. `git ls-files` shows only `.env.example`
  templates across the 5 packages — no real `.env` leaked.
- **Snapshot files:** inspected; contain only type-annotation strings such as
  `token: 'str | None' = None` — these are signature surface, not credentials.
- **Insecure HTTP URLs:** none introduced; matriz `_state.py` default
  base_url is the production HTTPS sandbox `https://api.remarkets.primary.com.ar`.
- **`# noqa` / `# type: ignore` additions:** none added in Phase 6 source.
  `verification/safemodel_diff.py` carries 2 pre-existing `type: ignore` comments
  and `verification/redaction.py` carries 1 pre-existing `noqa: RUF001` — none
  attributable to Phase 6 changes.
- **W5 closure (matriz `_ensure_token` callable shim):** `grep` confirms no
  module-level `def _ensure_token` in `packages/matriz-client/src/matriz_client/client.py`;
  test `test_no_module_level_ensure_token_callable` (line 246 of test_client_class.py)
  enforces `"_ensure_token" not in matriz_client.client.__dict__`.
- **B7 ambito divergence:** `packages/ambito-financiero-client/src/ambito_financiero_client/_state.py:62-64`
  omits `token_lock`; `aio.py` AsyncClient `__slots__ = ("_state",)` only.
- **B8 shared helper identity:** every package's `aio.py` imports
  `_raise_for_response` from `client.py` (explicit re-export alias for mypy strict).

### Unregistered Flags

None — every SUMMARY.md `## Threat Flags` section explicitly states "No new
threat surface introduced". All declared mitigations map back to a threat ID
in the register above.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-08 | T-06-08 | Snapshot file contents are public-surface enumeration only; `__all__` excludes credential globals (`_state` is private). Confirmed by inspection of all 4 snapshot files in `verification/snapshots/`. | gsd-security-auditor + Plan 01 author | 2026-06-11 |
| AR-06-09 | T-06-09 | `SYNC-sentinel-<pkg>` / `ASYNC-sentinel-<pkg>` strings are non-secret literals chosen for forensic localization at failed-test time. They are visible in CI logs by design — they are not real tokens. | gsd-security-auditor + Plan 02 author | 2026-06-11 |
| AR-06-11 | T-06-11 | CI matrix flakes are operationally handled via re-run; persistent failures trigger plan revert. No code-level mitigation in scope for Phase 6. | gsd-security-auditor + Plan 07 author | 2026-06-11 |
| AR-06-13 | T-06-13 | Ambito has no auth and no token refresh race; the asyncio.Lock pattern is unnecessary. A concurrent first-call race in `AsyncClient._ensure_http_client` could leak at most one `httpx.AsyncClient` per accidental race per process. Acceptable for low-frequency FX rate polling. Documented in `_state.py:14-21` + `aio.py` `_ensure_http_client` docstring. | gsd-security-auditor + Plan 03 author | 2026-06-11 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-11 | 28 | 28 | 0 | gsd-security-auditor (Opus 4.7) |

Notes:
- 23 threats with `mitigate` disposition verified by grep + read of the cited
  files. Every mitigation pattern was located in the implementation at the
  cited file:line.
- 4 threats with `accept` disposition recorded in the Accepted Risks Log
  (T-06-08, T-06-09, T-06-11, T-06-13).
- 1 threat marked `N/A` (T-06-SC) closed by inspecting the squash-commit
  diff: only `testpaths` and `pythonpath` added to `[tool.pytest.ini_options]`;
  no dependency changes in any `pyproject.toml`.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-11
