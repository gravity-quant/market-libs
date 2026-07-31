# Phase 23: Verificación en vivo contra develop + fixes - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-07-30
**Phase:** 23-verificaci-n-en-vivo-contra-develop-fixes
**Mode:** assumptions
**Areas analyzed:** Driver structure & `--live` gating, Public-surface coverage, Divergence
handling & in-cycle fixes, Harness integration artifacts, Live-environment access risk

## Assumptions Presented

### Driver structure & `--live` gating
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| No `--live` argparse flag; gate via `require_env` on 4 Auth0 vars, SKIPPED + exit 0 when absent; source-plan `--live` phrase reconciled as the existing offline/skip split | Likely | `main_ambito_financiero.py` (no argparse), `verification/env_gate.py:32-41`, `main_verify.py:41` (`_ENV_SKIP`) + `:61` (flag-less subprocess), `client.py:25-30,29-30` |

### Public-surface coverage
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Exercise all 10 methods on BOTH `Client`/`AsyncClient` + shims (2 anonymous health, 8 authenticated read); probes cover happy-path, sync↔async parity, param-encoding, received_at/staleness, no-data, auth-fail; diff all 7 `SafeModel`s | Confident | `client.py:352-497`, `aio.py:365-511`, `__init__.py:40-101`, `models.py:118-275,181-188` |

### Divergence handling & in-cycle fixes
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Document via `append_finding` with only 7 closed classes (SHAPE/AUTH/ERROR-MAP/PARAM/SYNC-ASYNC-DRIFT/NO-DATA/ANTI-BOT); received_at→SHAPE, params→PARAM, 401→AUTH; fix mirrored sync/async in models.py + `_core` parsers; each fix links a mocked pytest-httpx regression for cycle closure PASS | Confident | `findings.py:76-84,565-566`, `safemodel_diff.py:130-141`, `_core.py:527,548`, `models.py:19-23,146-164`, `cycle_report.py:47,123-176` |

### Harness integration artifacts
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| New AST guard `test_main_market_data_uses_single_client_instance.py`; append driver to `main_verify.py._DRIVERS`; `write_findings("market-data-client")` bootstrap; schema dir `.planning/verification/schemas/market-data-client/`; capture/anonymize minimal | Confident | `verification/test_main_ambito_financiero_uses_single_client_instance.py:45-57`, `main_verify.py:28-34`, `findings.py:137`, `main_ambito_financiero.py:64,713,717` |

### Live-environment access risk
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Degrades gracefully: missing creds → SKIPPED + exit 0; base_url defaults to develop; network-unreachable / closed-market caught per-probe as NO-DATA/skip, never a crash → FAILED | Likely | `env_gate.py:36-41`, `main_verify.py:75-80`, `client.py:29-30`, `main_ambito_financiero.py:698-699,745-746` |

## Corrections Made

No corrections — all assumptions confirmed ("Yes, proceed").

## External Research

None. All evidence codebase-internal. The one genuine unknown — real develop payload shapes vs.
the PROVISIONAL models (`models.py:19-23`) — is resolved by the phase's live run at execution
time (OpenAPI deliberately not vendored), not by external docs.

## Analyzer Correction Noted

Auth0 env-var names are `MARKET_DATA_CLIENT_ID`, `MARKET_DATA_CLIENT_SECRET`,
`MARKET_DATA_AUDIENCE`, `MARKET_DATA_AUTH0_TOKEN_URL` (all required) + `MARKET_DATA_BASE_URL`
(optional, defaults to develop URL) — NOT the `MARKET_DATA_AUTH0_CLIENT_ID` / `_AUDIENCE`
spellings the source plan implied. Source of truth: `client.py:25-30`.
