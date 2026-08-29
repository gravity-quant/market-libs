# Phase 36 — deferred items (out of scope discoveries)

Logged per the executor scope-boundary rule: discovered while running a wider gate
than the plan required, NOT caused by this phase, NOT fixed here.

## Pre-existing failures in the repo-root `verification/` suite

Measured 2026-08-29 during Plan 36-02 with `uv run pytest -q` (whole workspace,
919 s) and `uv run pytest verification -q` (827 s).

**Every failure in the workspace run lives in `verification/`.** The six package
suites under `packages/` are fully green (`23 failed` in the workspace run ==
`23 failed` in the `verification/`-only run).

| Module | Count | Domain | Touched by Phase 36? |
|--------|-------|--------|----------------------|
| `verification/test_matriz_sweep_snapshot.py` | 17 failed + 17 errors | matriz | No |
| `verification/test_main_matriz_login_fail_uniformity.py` | 2 failed + 2 errors (`verification/divergences.py:293: TypeError`) | matriz | No |
| `verification/test_cycle_closure_phase33.py::test_cycle_closure_is_not_vacuous[ambito-financiero-client]` | 1 failed (`FileNotFoundError`) | ámbito | No |
| `verification/test_cycle_closure_phase33.py::test_cycle_closure_is_not_vacuous[higyrus-client]` | 1 failed (`FileNotFoundError`) | higyrus | No |

Plan 36-02's diff touches **seven files, all under `packages/market-data-client/`**
(`git diff --stat d2bdd28..HEAD`). It contains zero matriz, ámbito or higyrus
files, and the no-shared-code constraint (DT-03) means it structurally cannot
reach them.

`verification/` has never run in CI — ROADMAP Phase 32 (`GATE-TYP-01`) records
"`verification/` nunca corrió en CI" and scopes the new CI job. That is why these
failures have been able to accumulate unnoticed.

**Not deferred, fixed in-cycle:** two of the 23 — `test_cycle_closure_market_data.py`
and `test_cycle_closure_phase33.py::test_cycle_closure_is_green[market-data-client]`
— WERE caused by Plan 36-02 (a test rename orphaned six `Regression:` bullets) and
were fixed at commit `3f6d5ca`. See `36-02-SUMMARY.md` § Deviations, deviation 2.

**Suggested destination:** the Phase 32 CI-gate follow-up, or a dedicated
`/gsd-audit-fix` pass. Fixing them from inside Phase 36 would put matriz, ámbito
and higyrus files in a market-data-client plan's diff.
