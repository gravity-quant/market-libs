# Deferred items — Phase 27

Out-of-scope discoveries logged during execution. Per the SCOPE BOUNDARY rule these were
**not** fixed: they are pre-existing failures in files unrelated to the plan's change surface.

## 1. `verification/test_main_matriz_login_fail_uniformity.py` — signature drift (2 failures + 2 errors)

- **Found during:** plan 27-01, task 1 verification (`uv run pytest verification -q`)
- **Symptom:** `TypeError: probe_login_sync() missing 1 required positional argument: 'client'`
- **Root cause:** `main_matriz.py:486` is `def probe_login_sync(client: Client)` since Phase 15
  (commits `d1927f5` "migrate main_matriz.py to single sync + single async client" and `1fbc83f`
  "route matriz sync sweep probes through threaded Client"). The test still calls it with no
  argument. A cascading `httpx_mock` teardown error ("responses mocked but not requested")
  follows from the probe never issuing its request.
- **Proven pre-existing:** reverting `verification/findings.py` to its pre-Phase-27 state
  (`git checkout -- verification/findings.py`) reproduces the identical 19 failures + 19 errors,
  so the plan-27-01 serializer change is not implicated.

## 2. `verification/test_matriz_sweep_snapshot.py` — same signature drift (17 failures + 17 errors)

- **Found during:** same run
- **Symptom / cause:** identical to item 1 — the parametrized `test_matriz_probe_envelope_shape_preserved`
  cases call Phase-15-migrated matriz probes without the now-required `client` argument.
- **Proven pre-existing:** same revert experiment.

**Total pre-existing:** 19 failed, 19 errors, 220 passed in `verification/` (829s wall — the
duration is dominated by `test_retry_after_cap.py::test_retry_after_capped_at_60s`, which sleeps
for real).

## 3. `append_finding` same-fid update on an **OPEN** finding still drops `extra_bullets`

- **Found during:** plan 27-01, task 1 implementation
- **Detail:** the D-23 fix round-trips unknown bullets through `_parse_findings` →
  `_serialize_findings`. But `append_finding`'s same-fid replacement path builds a fresh
  `_Finding` with an empty `extra_bullets`, so triage prose a human added to a finding that is
  **still OPEN** is lost when the driver re-runs that same fid. The non-OPEN short-circuit
  already protects every promoted finding (CONFIRMED/FIXED/EXPECTED/NO-FIX), which is the case
  the phase actually depends on.
- **Why deferred:** plan 27-01 explicitly bounds the blast radius — "Do not change
  `append_finding`'s public signature ... This is an additive fix to a module shared by five
  drivers; blast radius must stay at the serializer." Carrying `existing[fid].extra_bullets`
  into the replacement `_Finding` is a one-line follow-up if a later phase wants it.
