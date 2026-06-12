# Milestones

## v1.0 Verification cycle (Shipped: 2026-06-10)

**Phases completed:** 5 phases, 18 plans, 27 tasks

**Key accomplishments:**

- Root conftest live/offline split (`--live` deselect-by-default), the importable non-published `verification/` package, and defense-in-depth `redact`/`safe_print` credential masking — all unit-proven including the empty-secret corruption guard.
- Two stdlib-only hard safety gates — a credential `require_env` emitting the verbatim `SKIPPED <pkg>: missing X, Y` line, and a `mutating_allowed` double-gate (`VERIFY_MUTATING=1` AND a live-resolved `remarkets` base URL) that fails safe even against a prod-URL bypass — each TDD-proven.
- AMB-01..AMB-06 verificados en vivo contra mercados.ambito.com; cero bugs detectados; baseline DRIFT-01 + Phase 2 findings file committeados al repo.
- OAuth2 `grant_type=refresh_token` with fallback to password grant implemented in IOL client `client.py` + `aio.py` dual surfaces, plus 4+4 pytest-httpx regression tests locking the four code paths (login capture, refresh success, refresh→password fallback, both fail).
- Fix dual sync+async: `_request` ahora pre-attachea el query string con `urlencode(... safe="/")` para preservar `/` literal en el wire, evitando que Higyrus IIS rechace el formato `dd/mm/yyyy` con HTTP 400.
- Live run contra remarkets PASS=17/FAIL=0/SKIPPED=9/FINDING=2; suite mockeada Phase 5 lockea 12 invariantes Verified-live + 11 MATZ-06 mock-only contract con 3 sentinels GET-quirk §6.3; cycle_closure × 4 pkgs PASS confirma DRIFT-02 helper promotion funcionando end-to-end
- DRIFT-02 baseline canónico creado: 4 findings files con `## Cycle Closure` + `CYCLE-REPORT.md` consolidando 14 findings / 18 schemas / 4 paquetes; `verify_cycle_closure × 4` reporta 3 PASS (ámbito/iol/higyrus sin CONFIRMED/FIXED) + 1 FAIL (matriz F-09 deferred) — la FAIL es la señal DRIFT-02 activa por diseño

---
