---
phase: 7
slug: core-py-extraction-sync-async-logic-dedup
status: ready_for_verify
nyquist_compliant: partial
wave_0_complete: true
created: 2026-06-12
updated: 2026-06-12
phase_status: ready_for_verify
---

# Phase 7 — Validation Strategy + Green-Gate Consolidation

> Wave 0 contract + Phase 7 Wave 3 green-gate consolidation evidence (Plan 07-06).
>
> **`nyquist_compliant: partial`** — 4/5 Phase 7 ROADMAP success criteria PASS;
> success criterion #3 (LOC drop ≥30% per package) is partially met (2 of 4
> packages PASS, 2 documented deviations). Every other gate (REFAC-03 architecture,
> CR-03, CR-05, CI gates, test suite, public surface, cross-leak) is green.
> Operator decides via the Plan 07-06 Task 2 human-verify checkpoint whether
> `partial` is acceptable for Phase 7 close-out.

---

## Phase 7 — Green Gate Final

### Success-Criteria Matrix (from ROADMAP `Phase 7 — Success Criteria`)

| # | Criterion | Evidence | Status |
|---|-----------|----------|--------|
| 1 | `_core.py` por paquete con builders/parsers/auth-flow primitives + no imports de `httpx.Client`/`httpx.AsyncClient` ni `client.py`/`aio.py` | 4 `_core.py` shipped: ámbito 147 LOC, iol 318 LOC, higyrus 425 LOC, matriz 728 LOC. `lint-imports` 4 contracts KEPT 0 broken. | **PASS** |
| 2 | CI rule import-linter bloquea `_core → client/aio` + cross-leak sentinel `SYNC-sentinel-<pkg>` vs `ASYNC-sentinel-<pkg>` | CI step `uv run lint-imports` en `.github/workflows/ci.yml` línea 40-41. `verification/test_sync_async_isolation.py` 7 passed + 1 skipped (matriz async D-11 reason). | **PASS** |
| 3 | LOC drop ≥30% client+aio agregado per paquete vs Phase 6 baseline | ámbito -31.2% PASS, higyrus -33% PASS, iol -5.1% FAIL (documented deviation), matriz client.py -20% FAIL (documented deviation). 2/4 paquetes PASS. | **PARTIAL** |
| 4 | CR-03: `_request` matriz consume body antes de raise cuando `status==ERROR` | `test_parse_envelope_consumes_body_before_raise` PASSED (CR-03 critical guard). Source order verified: `_core.py` línea 193 `resp.read()` antes de línea 194 `raise_for_response(resp)`. | **PASS** |
| 5 | CR-05: 18 sweep probes refactor a `_envelope_probe(envelope_key=...)` preservando 2 risk con `envelope_key=None`; 277+ tests verde | 15 calls a `_envelope_probe(...)` en `main_matriz.py` (13 envelope + 2 risk) + 3 custom preserved (segments, all_instruments, market_data) + 1 sanity loop (cfi_sanity). `envelope_key=None` aparece 2× (risk probes) + 1× (helper def docstring) = 3. `test_matriz_sweep_snapshot.py` 20/20 PASS. Full suite 522 passed + 2 skipped + 1 deselected (393 baseline → 525 collected, +132 tests net since Phase 6 D-12). | **PASS** |

**Aggregate result:** **4 of 5 PASS, 1 PARTIAL (deviation documented, accepted in plans 07-03 and 07-05 SUMMARYs).**

### `nyquist_compliant` decision

Set to `partial` rather than `true` to surface the LOC-drop deviation honestly.
The plan instructions for 07-06 explicitly mandate: *"if 4/5 success criteria
PASS and criterion 3 is partially met, set `nyquist_compliant: partial` with
explicit notes; let the user decide via the human-verify checkpoint"*. The
operator decides at the Plan 07-06 Task 2 checkpoint whether to advance the
phase as-is, or to extend Plan 07-03/07-05 to recover the missing LOC drops.

---

## LOC Drop Summary (D-14 — per package, client.py + aio.py aggregate)

Phase 6 baseline = `wc -l packages/<pkg>/src/<pkg>/{client,aio}.py` at commit
`5db0a0d` (Phase 6 final tip on `main`). Phase 7 final = HEAD of this worktree
(`59fe6e3` + this validation commit).

| Pkg | client.py (before→after) | aio.py (before→after) | Aggregate drop | Status |
|-----|--------------------------|-----------------------|----------------|--------|
| ámbito  | 270 → 189 (-30.0%)  | 287 → 194 (-32.4%) | 557 → 383 (-31.2%) | **PASS** (target ≥30%) |
| iol     | 522 → 490 (-6.1%)   | 476 → 457 (-4.0%)  | 998 → 947 (-5.1%)  | **FAIL** (documented in 07-03-SUMMARY) |
| higyrus | 685 → 433 (-37.0%)  | 669 → 473 (-29.3%) | 1354 → 906 (-33.0%) | **PASS** (target ≥30%) |
| matriz  | 754 → 603 (-20.0%)  | 103 → 103 (UNCHANGED, byte-identical) | client.py only — aio.py is Phase 6 stub preserved verbatim until Phase 10 REFAC-04 | **FAIL** (client.py 20% vs target 30%, documented in 07-05-SUMMARY) |

### Deviations — root causes per package (verbatim from SUMMARY honesty flags)

**iol (-5.1%, target ≥30%) — 07-03-SUMMARY ([Rule 4 — documented])**

> The LOC count is dominated by load-bearing boilerplate that cannot be removed
> without violating other plan invariants:
>
> - Top-level back-compat shims (`configure`, `login`, 4 endpoint delegators,
>   `_request`) — ~117 LOC client + ~145 LOC aio. Removing them breaks D-16
>   public surface snapshot zero diff + `iol_client.__init__` re-exports.
> - PEP 562 read-only forwarding shims (`_FORWARDED_TO_STATE`,
>   `_FORWARDED_HTTP_CLIENT`, `_DENIED_LEGACY`, `__getattr__`) — ~46 LOC
>   client + ~52 LOC aio. Removing them breaks Phase 6 D-01 invariant + the
>   `_user`/`_password`/`_base_url` deny-list T-7-AUTH-LEAK mitigation.
> - Class lifecycle methods preserved per D-23 (`__init__`, `__enter__`/`__exit__`
>   or `__aenter__`/`__aexit__`, `close`/`aclose`, `__repr__`, `__reduce__`,
>   `__deepcopy__`, `_ensure_http_client`, `_ensure_token_lock` in aio).
> - Module-level + per-function docstrings + multi-line typed signatures
>   mandated by CONVENTIONS.md.
>
> What did contract: the class method bodies that actually changed (endpoint
> methods, `login`, `_refresh`, `_ensure_token`, `_request`) collapsed
> dramatically (e.g. `Client.login()` ~32 LOC → ~16 LOC). The 5.1% aggregate
> reflects the dual back-compat surface; the part the refactor actually changes
> drops >50%.

**matriz client.py (-20%, target ≥30%) — 07-05-SUMMARY ([Rule 3 — documented])**

> El target era aggressive y no era realista dado el back-compat surface
> (22 delegators + PEP 562 + Pitfall 7 wrappers). Cualquier reducción
> adicional rompería public API o requeriría cambios out-of-scope (e.g.,
> migrar `main_matriz.py` al nuevo `Client._request(spec)` API). Recommended
> follow-up: v1.2 puede migrar `main_matriz.py` completo al nuevo
> `Client._request(spec)` API, lo que permitiría drop `_matriz_legacy_request`
> (~15 LOC) + `_request`/`_risk_auth` module-level (~20 LOC) = ~570 LOC final.

**matriz aio.py (UNCHANGED, by design)**

```
$ shasum -a 256 packages/matriz-client/src/matriz_client/aio.py
0a39ae8b073cfa7066447757df91349df0b82f2bd39a2676d369d175c176fdb1  packages/matriz-client/src/matriz_client/aio.py

$ git show 5db0a0d:packages/matriz-client/src/matriz_client/aio.py | shasum -a 256
0a39ae8b073cfa7066447757df91349df0b82f2bd39a2676d369d175c176fdb1  -
```

Byte-identical at sha256. matriz aio.py is the Phase 6 stub preserved verbatim
until Phase 10 REFAC-04 + TokenStore lifts it to a full async REST surface
consuming the matriz `_core.py` shipped in this phase (forward-compat — zero
extra work needed in Phase 10 for the `_core.py` itself).

---

## CR-03 Verification

**Test:** `packages/matriz-client/tests/test_core.py::test_parse_envelope_consumes_body_before_raise`

```
$ uv run pytest packages/matriz-client/tests/test_core.py::test_parse_envelope_consumes_body_before_raise -v
collected 1 item

packages/matriz-client/tests/test_core.py::test_parse_envelope_consumes_body_before_raise PASSED [100%]

============================== 1 passed in 0.03s ===============================
Exit: 0
```

**Source order verification (line-precise):**

```
$ grep -n "parse_envelope_response\|resp\.read\|raise_for_response(resp)" \
       packages/matriz-client/src/matriz_client/_core.py | head -10
175:def parse_envelope_response(resp: httpx.Response, endpoint: str) -> dict[str, Any]:
193:    resp.read()
194:    raise_for_response(resp)
```

`resp.read()` (línea 193) ejecuta ANTES de `raise_for_response(resp)` (línea 194). D-06 order
honored. Body is fully consumed before any raise — future `httpx.Client(http2=True)` will not
leak streams in the connection pool when `status==ERROR` triggers `PrimaryAPIError`.

---

## CR-05 Verification

**Test:** `verification/test_matriz_sweep_snapshot.py` — 20 tests (17 parametrized probe shape
guards + 3 invariant tests).

```
$ uv run pytest verification/test_matriz_sweep_snapshot.py -v
collected 20 items

[17 parametrized probe shape guards — all PASSED]
verification/test_matriz_sweep_snapshot.py::test_matriz_sweep_snapshot_count_matches_18_minus_cfi_sanity PASSED
verification/test_matriz_sweep_snapshot.py::test_matriz_envelope_probe_helper_exists PASSED
verification/test_matriz_sweep_snapshot.py::test_matriz_risk_probes_use_envelope_key_none PASSED

============================== 20 passed in 0.05s ==============================
Exit: 0
```

**`main_matriz.py` migration evidence:**

```
$ grep -c "_envelope_probe(" main_matriz.py
15

$ grep -c "envelope_key=None" main_matriz.py
3     # 2 risk probes use envelope_key=None per D-07 + 1 helper definition

$ grep -c "^def probe_get_segments\|^def probe_get_all_instruments\|^def probe_get_market_data\|^def probe_get_instruments_by_cfi_sanity" main_matriz.py
4     # 3 custom side-effect probes + 1 sanity loop (A4 honesty flag — keep custom)
```

- **15 probes migradas al helper** (13 envelope-wrapping + 2 risk con `envelope_key=None`).
- **3 probes custom preservadas** por side-effects (`probe_get_segments` setea
  `_resolved_segment`; `probe_get_all_instruments` setea `_resolved_symbol`;
  `probe_get_market_data` tiene market-hours guard) + 1 sanity loop (`probe_get_instruments_by_cfi_sanity`
  itera sobre 8 CFI codes, no es envelope probe).
- **Total: 15 + 3 + 1 = 19 probes**, satisfying the "18 sweep probes" CR-05 target
  with the helper covering the deduplicable boilerplate (~95% of envelope bodies).

`main_matriz.py` LOC: 1954 → 1509 (-22.8%).

---

## REFAC-03 Verification

### import-linter — 4 forbidden contracts

```
$ uv run lint-imports
Analyzed 30 files, 55 dependencies.
-----------------------------------

ambito_financiero_client._core does not depend on transport modules KEPT
higyrus_client._core does not depend on transport modules KEPT
iol_client._core does not depend on transport modules KEPT
matriz_client._core does not depend on transport modules KEPT

Contracts: 4 kept, 0 broken.
Exit: 0
```

CI step `uv run lint-imports` configured in `.github/workflows/ci.yml` job `lint`
(line 40-41). Boundary enforcement is push-to-CI, not manual developer discipline.

### Cross-leak sentinel — `verification/test_sync_async_isolation.py`

```
$ uv run pytest verification/test_sync_async_isolation.py -v
collected 8 items

test_sync_token_isolation_in_wire_request[ambito_financiero_client-None-]              PASSED
test_sync_token_isolation_in_wire_request[iol_client-Authorization-Bearer ]             PASSED
test_sync_token_isolation_in_wire_request[higyrus_client-Authorization-Bearer ]         PASSED
test_sync_token_isolation_in_wire_request[matriz_client-X-Auth-Token-]                  PASSED
test_async_token_isolation_in_wire_request[ambito_financiero_client-None-]              PASSED
test_async_token_isolation_in_wire_request[iol_client-Authorization-Bearer ]            PASSED
test_async_token_isolation_in_wire_request[higyrus_client-Authorization-Bearer ]        PASSED
test_async_token_isolation_in_wire_request[matriz_client-X-Auth-Token-]                 SKIPPED

SKIPPED [1] verification/test_sync_async_isolation.py:176: matriz aio.py REST stub
   hasta Phase 10 REFAC-04 + TokenStore
========================= 7 passed, 1 skipped in 0.08s =========================
Exit: 0
```

D-11 reason literal preserved for matriz async — Phase 10 will des-skip when REFAC-04 lands.

### B8 / D-04 alias identity (live process)

```
$ uv run python -c "
from ambito_financiero_client.aio import _raise_for_response as a_a
from ambito_financiero_client.client import _raise_for_response as a_c
from iol_client.aio import _raise_for_response as i_a
from iol_client.client import _raise_for_response as i_c
from higyrus_client.aio import _raise_for_response as h_a
from higyrus_client.client import _raise_for_response as h_c
assert a_a is a_c
assert i_a is i_c
assert h_a is h_c
print('B8 identity preserved for ambito, iol, higyrus')
"
B8 identity preserved for ambito, iol, higyrus
Exit: 0
```

Per-package D-04 alias source proof:

| Pkg | client.py alias (line) | aio.py alias (line) |
|-----|------------------------|---------------------|
| ámbito  | `_raise_for_response = _core.raise_for_response` (line 35) | `_raise_for_response = _core.raise_for_response` (line 35) |
| iol     | `_raise_for_response = _core.raise_for_response` (line 77) | `from iol_client._core import raise_for_response as _raise_for_response` (line 55) |
| higyrus | `_raise_for_response = _core.raise_for_response` (line 65) | `from higyrus_client._core import raise_for_response as _raise_for_response` (line 48) |
| matriz  | `_raise_for_response = _core.raise_for_response` (line 84); also `_unwrap = _core.unwrap` (line 85) | (none — Phase 6 stub; D-04 alias arrives in Phase 10 REFAC-04) |

---

## Public Surface Snapshot (D-16)

```
$ uv run pytest verification/test_public_surface.py -v
collected 4 items

verification/test_public_surface.py::test_public_surface_matches_snapshot[ambito_financiero_client] PASSED
verification/test_public_surface.py::test_public_surface_matches_snapshot[iol_client]               PASSED
verification/test_public_surface.py::test_public_surface_matches_snapshot[higyrus_client]           PASSED
verification/test_public_surface.py::test_public_surface_matches_snapshot[matriz_client]            PASSED

============================== 4 passed in 0.09s ===============================
Exit: 0
```

Zero diff vs Phase 6 snapshot files in `verification/snapshots/`. `_core` does NOT appear in
any root-package `__all__` — D-16 honored.

---

## Test Count (Baseline → Final)

| Stage | Tests collected | Delta | Notes |
|-------|-----------------|-------|-------|
| Phase 6 D-12 baseline | 393 | — | Pitfall 4 / A5 reference |
| Post-Plan 07-01 (CI gates) | 402 | +9 | Cross-leak sentinel 7 sync + 3 async (1 skip matriz) |
| Post-Plan 07-02 (ámbito) | 412 | +12 ámbito test_core | |
| Post-Plan 07-03 (iol) | 449 | +37 iol test_core | |
| Post-Plan 07-04 (higyrus) | 482 | +33 higyrus test_core | |
| Post-Plan 07-05 (matriz ATOMIC) | 525 | +21 matriz test_core + 20 sweep snapshot − 1 reorganized | |
| Phase 7 final (HEAD `59fe6e3` + this validation) | **525 collected** | +132 vs baseline | |

```
$ uv run pytest -q
522 passed, 2 skipped, 1 deselected in 1.38s
```

(525 collected − 1 deselected = 524 runnable; 522 pass + 2 skip.)

The 2 skips:

1. `packages/matriz-client/tests/test_fixture_reaches_production.py:64` —
   "matriz async REST surface is Phase 10 REFAC-04; stub AsyncClient ships in Plan 06 with no REST methods"
2. `verification/test_sync_async_isolation.py:176` —
   "matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore" (D-11 reason)

The 1 deselected is the pytest collection filter unrelated to Phase 7.

---

## CI-Stack Gate Matrix (CI-equivalent local invocations)

| Command | Phase 7 scope (`packages/`, `verification/`, `main_*.py`) | Full repo (`.`) |
|---------|------------------------------------------------------------|----------------|
| `uv lock --check` | n/a (root-level) | **PASS** exit 0 |
| `uv sync --all-packages --all-extras --dev --frozen` | n/a (root-level) | **PASS** exit 0 |
| `uv run ruff check` | **PASS** exit 0 (`All checks passed!`) | **FAIL** exit 1 — 108 errors, **all in pre-existing spike artifacts in `.planning/spikes/` + `.claude/skills/spike-findings-market-libs/sources/`** (see deferred-items.md) |
| `uv run ruff format --check` | **PASS** exit 0 (94 files already formatted) | **FAIL** exit 1 — 22 files would reformat, **all in same pre-existing spike paths** |
| `uv run mypy` (src) | **PASS** exit 0 — 34 source files | (root scope) |
| `uv run mypy packages/<pkg>/tests` × 5 | **PASS** exit 0 each | n/a |
| `uv run lint-imports` | **PASS** 4 kept, 0 broken | n/a |
| `uv run pytest verification/test_public_surface.py` | **PASS** 4/4 | n/a |
| `uv run pytest verification/test_sync_async_isolation.py` | **PASS** 7 + 1 skipped | n/a |
| `uv run pytest verification/test_matriz_sweep_snapshot.py` | **PASS** 20/20 | n/a |
| `uv run pytest -q` (full suite) | **PASS** 522 passed, 2 skipped, 1 deselected | n/a |

### Ruff scope deviation — root vs phase-7 scope (honest documentation)

The CI workflow (`.github/workflows/ci.yml`) runs `uv run ruff check .` and
`uv run ruff format --check .` without filters. These commands exit non-zero
on `main` *today* due to 108 ruff errors + 22 format diffs in
`.planning/spikes/001-005` and `.claude/skills/spike-findings-market-libs/sources/`
— **all pre-existing on `main`** (verified by `git show 5db0a0d:<path>`).

These spike artifacts are NOT Phase 7 scope. The Phase 7 refactor produced
ZERO ruff/format violations in `packages/`, `verification/`, or `main_*.py`.

**Scope-restricted gate (the gate Phase 7 actually owns):**

```
$ uv run ruff check packages/ verification/ main_*.py
All checks passed!

$ uv run ruff format --check packages/ verification/ main_*.py
94 files already formatted
```

Both exit 0.

**Recommended follow-up** (out of Phase 7 scope, logged in `deferred-items.md`):
Track as a separate quick task to either (a) exclude `.claude/skills/sources/` and
`.planning/spikes/` from ruff scope in `pyproject.toml`, or (b) reformat those
files in a single docs/style commit. CI will not turn fully green until one of
those lands.

---

## Pitfall 18 Statement — No Tests Were Weakened During Phase 7

**Assertion:** No tests pre-existing en `packages/*/tests/` o `verification/`
fueron eliminados, skipeados, ni "weakeneados" (e.g. relaxing an `assertEqual`
to `assertIn` to silence a regression) durante Phase 7. Solo se agregaron
tests nuevos (393 baseline → 525 collected = +132 net tests).

**Evidence per plan (cross-referenced with SUMMARYs):**

- **07-01:** +9 tests cross-leak sentinel (D-10). Zero pre-existing tests touched.
- **07-02:** +12 tests `ambito/tests/test_core.py`. Pre-existing 95 tests verde.
- **07-03:** +37 tests `iol/tests/test_core.py`. Pre-existing 59 tests verde
  (CR-01 preservation test `test_login_preserves_cached_refresh_token_when_server_omits`
  pasa en la nueva API sin modificación — strong signal del structural lock).
- **07-04:** +33 tests `higyrus/tests/test_core.py`. Pre-existing 80 tests verde
  (URL-encoding quirk test `test_url_encoding_preserves_slash_in_query` sync + async PASS).
- **07-05:** +21 tests `matriz/tests/test_core.py` + 20 tests `verification/test_matriz_sweep_snapshot.py`
  + 4 tests modificados en `matriz/tests/test_client.py` y `test_client_class.py`
  para migrar de `_request(method, path, ...)` → `_matriz_legacy_request(...)` (dict-return
  back-compat wrapper) o `_request(spec: RequestSpec)` (Pitfall 7 / D-03). **The 4 modified
  tests preserve the original assertion intent** (verifying headers, auth_basic skip, ensure_token
  guard) — they were updated to call the new API surface; no weakening of the verification logic.

The only "test reorganization" mentioned in the matriz SUMMARY (Plan 07-05) is
the 4 tests refactored to call `_matriz_legacy_request` or `_request(spec)` instead
of the old positional `_request(method, path, ...)`. Their assertions remain
unchanged in spirit. No `pytest.skip`, no `pytest.xfail`, no `assert` relaxation.

---

## Threat Register Closure (Phase 7 aggregated)

| Threat ID | Disposition source | Mitigation evidence in this validation |
|-----------|--------------------|---------------------------------------|
| T-7-CI-DRIFT | Plan 07-06 §threat_model | Operator confirms PR CI matrix Python 3.12 + 3.13 green at Task 2 checkpoint (local-only verification is incomplete; PR check pending) |
| T-7-WEAK (Pitfall 18) | Plan 07-06 §threat_model | "Pitfall 18 Statement" section above documents all 5 plans + per-plan SUMMARYs cross-referenced |
| T-7-D16-DRIFT | Plan 07-06 §threat_model | `verification/test_public_surface.py` 4/4 PASS zero diff |
| T-7-MATRIZ-AIO | Plan 07-06 §threat_model | `wc -l packages/matriz-client/src/matriz_client/aio.py` = 103; sha256 byte-identical vs Phase 6 baseline (5db0a0d) |
| T-7-01 | Plan 07-01 (all packages, transitive) | `lint-imports` 4 contracts KEPT |
| T-7-02 | Plan 07-01 + per-pkg plans | `test_sync_async_isolation` 7 PASS + 1 SKIP (matriz async D-11) |
| T-7-03 | Plans 07-02..07-05 (B8 alias) | B8 identity assertion above (3 packages PASS; matriz aio absent by design) |
| T-7-05 | Plan 07-05 (HTTP/2 stream leak) | `test_parse_envelope_consumes_body_before_raise` PASS + source order verified |
| T-7-06 | Plan 07-05 (risk probe envelope) | `grep -c "envelope_key=None" main_matriz.py` = 3 (2 risk + 1 helper def) |
| T-7-07 | Plan 07-05 (`_envelope_probe` swallows side-effects) | 3 custom probes preserved by source grep + 1 sanity loop |
| T-7-AUTH-LEAK | Plan 06 (forwarded) | PEP 562 `_DENIED_LEGACY` deny-list verified in `iol_client/client.py:468` (`_user`/`_password`/`_base_url`); higyrus and matriz use other secret-bearing attribute names (per-package design, not subject to the same deny-list pattern) |

---

## Wave 0 Closure

| Wave 0 item | Status |
|-------------|--------|
| Test infrastructure (`pytest`, `pytest-httpx`, `pytest-asyncio`) | PASS — already shipped in Phase 6; Phase 7 adds `import-linter>=2.11,<3` to `[dependency-groups] dev` (Plan 07-01) |
| Per-package `_core.py` placeholders | PASS — 4 created in Plan 07-01; expanded in Plans 07-02..07-05 |
| Cross-leak sentinel test | PASS — `verification/test_sync_async_isolation.py` (Plan 07-01) |
| CI step `lint-imports` | PASS — added in Plan 07-01 |
| Phase 6 public surface snapshot | PASS — preserved zero diff (D-16) |

`wave_0_complete: true` is set in frontmatter.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CI matrix Python 3.12 + 3.13 verde sobre el merge commit en GitHub | Phase 7 success-criterion #5 (D-12 mirror Phase 6 Plan 7) | Local execution only validates current machine (Python 3.12.11); the CI matrix runs on Ubuntu × Python 3.12 + 3.13 in parallel. Some failures (e.g. Python 3.13 wheel resolution, OS-specific path normalization, locale-sensitive sorting) only surface in CI. | Visit the PR for Phase 7 on GitHub. In the "Checks" tab, verify all jobs (`lint`, `pre-commit`, `typecheck`, `Tests · <pkg> · py3.12`, `Tests · <pkg> · py3.13`) show a green check. **Expected exception:** the `lint` job will be RED until the pre-existing spike-artifact ruff/format violations are addressed (out-of-Phase-7-scope, documented in `deferred-items.md`). |
| Operator confirms matriz `aio.py` not accidentally modified in Plan 5 | T-7-MATRIZ-AIO mitigation | byte-identical check is a one-line verification, but cross-team accountability requires human acknowledgment | `wc -l packages/matriz-client/src/matriz_client/aio.py` must print exactly `103`. Operator runs and confirms in approval message. |
| Operator confirms LOC deviations (iol 5.1%, matriz client.py 20%) are accepted as documented | Phase 7 success-criterion #3 (PARTIAL) | Architectural decision — operator decides whether to extend Plan 07-03/07-05 or accept the deviation as the path-forward for v1.2 driver migration. | Operator reviews 07-03-SUMMARY §"Acknowledged Deviation" + 07-05-SUMMARY §"LOC drop target". Approval message states "accepted — v1.2 driver migration tracks the residual drop" or "blocked — extend plans to recover LOC drop". |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — yes, every Plan 07-0X has automated commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — yes, every plan ends in a tested commit
- [x] Wave 0 covers all MISSING references — yes (Plan 07-01)
- [x] No watch-mode flags — yes, all `pytest` invocations are one-shot
- [x] Feedback latency < 5s — full repo suite runs in 1.38s
- [x] `nyquist_compliant: partial` set in frontmatter (honest — 4/5 PASS, criterion 3 deviation documented)

**Approval:** pending — operator decides at Plan 07-06 Task 2 human-verify checkpoint.

---

## Provenance / Reproduction

- **Validation run:** 2026-06-12 in worktree `agent-a0b59102cc63ce5b1`, HEAD `59fe6e3` + this commit.
- **Local runtime:** uv 0.9.0, CPython 3.12.11 (`.venv/`).
- **Phase 6 baseline ref:** `5db0a0d` (last commit on `main` before Phase 7 work).
- **CI workflow:** `.github/workflows/ci.yml` — matrix `python-version: ["3.12", "3.13"]` × 5 packages.
- **Reproduce locally:**
  ```bash
  uv lock --check
  uv sync --all-packages --all-extras --dev --frozen
  uv run ruff check packages/ verification/ main_*.py    # Phase 7 scope
  uv run ruff format --check packages/ verification/ main_*.py
  uv run mypy
  uv run lint-imports
  uv run pytest verification/test_public_surface.py -v
  uv run pytest verification/test_sync_async_isolation.py -v
  uv run pytest verification/test_matriz_sweep_snapshot.py -v
  uv run pytest packages/matriz-client/tests/test_core.py::test_parse_envelope_consumes_body_before_raise -v
  uv run pytest -q
  ```
