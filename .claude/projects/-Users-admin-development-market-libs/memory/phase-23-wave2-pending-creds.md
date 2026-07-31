---
name: phase-23-wave2-pending-creds
description: Phase 23 Wave 2 (live market-data-client verification) is paused pending Auth0 credentials
metadata:
  type: project
---

Phase 23 (`verificación en vivo contra develop`) was executed **Wave 1 only** on 2026-07-30. Wave 1 (`23-01`) shipped the offline apparatus: `main_market_data.py` driver, the AST single-Client guard, `main_verify.py._DRIVERS` append, and bootstrapped `.planning/verification/market-data-client-findings.md` + `schemas/market-data-client/`. All green (ruff, mypy, AST guard, 134 package tests).

**Wave 2 (`23-02`) is intentionally NOT run.** It is the live sweep against develop + in-cycle `models.py`/`_core.py` fixes + mocked regressions + `verify_cycle_closure` gate. It was paused because **no market-data-client Auth0 credentials exist**: there is no `packages/market-data-client/.env`, and `MARKET_DATA_CLIENT_ID` / `MARKET_DATA_CLIENT_SECRET` / `MARKET_DATA_AUDIENCE` / `MARKET_DATA_AUTH0_TOKEN_URL` are unset.

**Why:** Without creds, `require_env` in the driver prints `SKIPPED market-data-client: missing ...` and exits 0. Running Wave 2 would then discover zero divergences, close the DRIFT cycle *vacuously*, and mark the phase complete without ever performing the live verification that is the phase's core value. Confirmed live: `uv run python main_market_data.py` → the SKIPPED line + exit 0.

**To resume a real Wave 2:** create `packages/market-data-client/.env` with the four `MARKET_DATA_*` vars (+ optional `MARKET_DATA_BASE_URL`; defaults to the develop target), confirm VPN/allowlist access to `https://market-data-develop.bbsa.com.ar/api`, then run `/gsd-execute-phase 23` (runs the remaining Wave 2).

Note: an uncommitted `uv.lock` change registering `market-data-client` as a workspace member is present in the working tree (pre-existing, out of scope — belongs to Phase 24 release work). See [[[]]] phase-23 context in `.planning/phases/23-verificaci-n-en-vivo-contra-develop-fixes/`.
