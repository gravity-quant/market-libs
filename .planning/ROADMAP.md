# Roadmap: market-libs — Verificación en vivo de clientes

## Milestones

- ✅ **v1.0 Verification cycle** — Phases 1-5 (shipped 2026-06-10) — see [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Tech Debt Cleanup** — Phases 6-11 (shipped 2026-06-14) — see [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Architecture + Auth/Ergonomics Carry-forwards** — Phases 12-17 (shipped 2026-06-25) — see [`milestones/v1.2-ROADMAP.md`](./milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Codegen Single-Source (libcst)** — Phases 18-19 (closed 2026-07-03 on signed SPIKE-006 NO-GO; Phase 19 REFAC-06 dropped) — see [`milestones/v1.3-ROADMAP.md`](./milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 market-data-client** — Phases 20-24 (shipped 2026-07-31) — nuevo paquete cliente (solo lectura) contra la API primary-extractor con Auth0 client-credentials, verificado en vivo y publicado v0.1.0 — see [`milestones/v1.4-ROADMAP.md`](./milestones/v1.4-ROADMAP.md)
- ✅ **v1.5 market-data-client · mutaciones** — Phases 25-28 (shipped 2026-08-17) — superficie de **escritura** (symbols + calendar) detrás de mutating-gate default-refuse, verificada en vivo (create→verify→revert) y publicada `market-data-client-v0.4.0` — see [`milestones/v1.5-ROADMAP.md`](./milestones/v1.5-ROADMAP.md)

## Phases

## Progress

| Phase                                                       | Milestone | Plans | Status      | Completed  |
|-------------------------------------------------------------|-----------|-------|-------------|------------|
| 1. Safety Harness & Verification Infrastructure             | v1.0      | 4/4   | Complete    | 2026-05-28 |
| 2. Ámbito Verification                                      | v1.0      | 3/3   | Complete    | 2026-06-05 |
| 3. IOL Verification                                         | v1.0      | 3/3   | Complete    | 2026-06-06 |
| 4. Higyrus Verification                                     | v1.0      | 4/4   | Complete    | 2026-06-08 |
| 5. Matriz Verification                                      | v1.0      | 4/4   | Complete    | 2026-06-10 |
| 6. Compat Safety Net + Client Class Skeleton                | v1.1      | 7/7   | Complete    | 2026-06-11 |
| 7. `_core.py` Extraction — Sync/Async Logic Dedup           | v1.1      | 6/6   | Complete    | 2026-06-12 |
| 8. Retries, Backoff, Structured Logging                     | v1.1      | 6/6   | Complete    | 2026-06-13 |
| 9. Deferred Bug Fixes                                       | v1.1      | 4/4   | Complete    | 2026-06-13 |
| 10. matriz `aio.py` Creation + TokenStore                   | v1.1      | 4/4   | Complete    | 2026-06-14 |
| 11. Harness Hardening + Code Review + Live Re-verification  | v1.1      | 3/3   | Complete    | 2026-06-14 |
| 12. Codegen Spike                                           | v1.2      | 4/3   | Complete    | 2026-06-14 |
| 13. Cross-Package Ergonomics (`with_options`)               | v1.2      | 5/5   | Complete    | 2026-06-15 |
| 14. IOL Disk Persistence                                    | v1.2      | 3/3   | Complete    | 2026-06-24 |
| 15. Driver Migration × 4                                    | v1.2      | 5/4   | Complete    | 2026-06-24 |
| 16. Codegen Single-Source (DROPPED — Phase 12 NO-GO)        | v1.2      | -     | Dropped     | 2026-06-14 |
| 17. Final Live Re-verification × 4                          | v1.2      | 3/3   | Complete    | 2026-06-25 |
| 18. libcst Codegen Tool-Choice Spike (SPIKE-006)            | v1.3      | 3/3   | Complete    | 2026-07-03 |
| 19. Codegen Single-Source × 4 (DROPPED — Phase 18 NO-GO)    | v1.3      | -     | Dropped     | 2026-07-03 |
| 20. Scaffold + Auth0 client-credentials + transport         | v1.4      | 6/6   | Complete    | 2026-07-29 |
| 21. Market data (read) + models                             | v1.4      | 4/4   | Complete    | 2026-07-30 |
| 22. Instruments/segments/symbols/calendar (read) + models   | v1.4      | 2/2   | Complete    | 2026-07-30 |
| 23. Live verification against develop + fixes               | v1.4      | 2/2   | Complete    | 2026-07-31 |
| 24. Release prep + publish v0.1.0                           | v1.4      | 2/2   | Complete    | 2026-07-31 |
| 25. Mutating-gate + Symbols write                           | v1.5      | 3/3 | Complete    | 2026-07-31 |
| 26. Calendar write                                          | v1.5      | 4/4 | Complete    | 2026-08-01 |
| 27. Safe live verification + fixes                          | v1.5      | 7/7 | Complete   | 2026-08-01 |
| 28. Release prep + publish v0.3.0                           | v1.5      | 3/3 | Complete    | 2026-08-12 |

## Backlog

*(Candidate items for next milestone; see `.planning/todos/pending/` + v1.0/v1.1/v1.2/v1.3 milestone audits deferred sections)*

### Deferred to v1.6+ (from v1.5)

- **D-16 — enrolar `market-data-client` en el typecheck global** — el paquete sigue ausente de tres listas: el `files` de mypy del root (`pyproject.toml:97`, hoy 5 paquetes), el `root_packages` de import-linter (`pyproject.toml:141-146`, hoy 4) y el loop mypy-tests per-package de `ci.yml:85` (hoy 5). Enrolarlo requiere además **escribir un contrato de import-linter** para `market_data_client._core` (los otros 4 paquetes ya tienen el suyo). Es un gap de **COBERTURA de typecheck, no un CI failure**: todos los checks package-scoped están verdes hoy, y la cobertura real de mypy sobre este paquete la da el hook de pre-commit scoped `files: ^packages/.*/src/` (`.pre-commit-config.yaml:32`). Diferido desde Phase 24 y re-confirmado en Phase 28 (**rechazado** enrolarlo en el PR de release: expandiría el diff). Se archiva acá explícitamente para que deje de rodar en silencio release tras release.

### Deferred to v1.5+ (from v1.4 — market-data-client v2 requirements)

- **MUT-MD-01 / MUT-MD-02** — market-data-client mutations: symbols (`POST /symbols`, `POST /symbols/batch`, `PATCH /symbols/{id}`) + calendar (`PUT/DELETE /calendar/config`, `POST /calendar/config/preview`, `POST /calendar/holidays`, `DELETE /calendar/holidays/{day}`) — require the security mutating-gate
- **STREAM-MD-01** — market-data-client SSE streaming (`GET /marketdata/stream`, `interval` param) via a dedicated transport (matriz `ws_client` pattern)
- **SEC-MD-01** — market-data-client Auth0 token disk cache (`_token_cache.py` + platformdirs, atomic + flock + 0600)
- **SEC-MD-02** — market-data-client JWT signature validation (RS256 against Auth0 JWKS)
- **LIVE-MD-01 real credentialed sweep** — the apparatus is verified; the actual live run against `market-data-develop.bbsa.com.ar` still awaits Auth0 creds + VPN/allowlist

### Deferred to v1.4+ (from v1.3 planning)

- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff — still deferred through v1.0/v1.1/v1.2/v1.3/v1.4)
- `matriz_client.ws_client` live verification (WebSocket streaming en daemon thread)
- `cryptography.fernet` token encryption at-rest (operator authorization required; threat-boundary expansion)
- Code-review CR-01 v1.2 Phase 14 (`configure()` no limpia el on-disk token cache de IOL)
- Extender alcance de verificación a `wallets-client` (cuando tenga endpoints reales)

### Resolved in v1.3 — REFAC-06 permanently shelved

- **REFAC-06** — codegen single-source for `client.py`/`aio.py` transport shells × 4 packages. **Permanently shelved 2026-07-03**: two dedicated spikes (unasync SPIKE-005 in v1.2 Phase 12, libcst SPIKE-006 in v1.3 Phase 18) both returned a signed NO-GO for the same content-absence / source-shape-asymmetry root cause under the un-migrated D-02 bar. The duplicate `client.py`/`aio.py` shells are now an **accepted structural feature** of the codebase (the known dual-surface duplication documented in CLAUDE.md). Do not re-open without a new tool class that can synthesize content-absent constructs, or a decision to relax the no-source-migration constraint (D-02). See `.planning/spikes/SPIKE-006-libcst-codegen-tool-choice/DECISION.md` + `Skill("spike-findings-codegen-market-libs")`.

### Deferred to v1.2+ (from v1.1 planning — REFAC-05/SEC-01/ERG-01 shipped in v1.2)

- Automatic `Idempotency-Key` header para retried POSTs
- `findings.toml` machine-readable side-file
- `Client.from_env()` classmethod for explicit env-reading (SKIPPED v1.2 — industry survey found ZERO SDKs with this pattern; implicit env fallback already exists)
- `request_id` UUID per `_request()` invocation threaded through retry log records
- `max_elapsed_seconds` retry budget cap as belt-and-suspenders
- ERR-01 (mocked 403/429/5xx mapping), ERR-02 (mocked token TTL refresh) — v2 requirements del v1.0 backlog
