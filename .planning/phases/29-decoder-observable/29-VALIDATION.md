---
phase: 29
slug: decoder-observable
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-18
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (pytest-asyncio auto mode, pytest-httpx) |
| **Config file** | pyproject.toml (root — testpaths, strict-markers, importlib mode) |
| **Quick run command** | `uv run pytest packages/<pkg>/tests -q` (package under edit) |
| **Full suite command** | `uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q` (872-test merge gate) then `uv run pytest -q` |
| **Estimated runtime** | ~64 seconds (merge gate); full workspace longer |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/<pkg>/tests -q`
- **After every plan wave:** Run the 872-test merge gate (3 SafeModel packages) — must stay green with zero test edits
- **Before `/gsd-verify-work`:** Full suite must be green + ruff + ruff-format + mypy --strict
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-T1 semantics matrix | 29-01 | 1 | DEC-01 | T-29-04 | per-package semantics declared, never harmonized | artifact grep | `grep -cE '^\| [1-6] \|' .planning/phases/29-decoder-observable/29-SEMANTICS-MATRIX.md` | ❌ W0 | ⬜ pending |
| 01-T2 aggregation contract + Literal D-lock | 29-01 | 1 | DEC-01 | T-29-01, T-29-02, T-29-03 | record schema is flat/all-str/top-level/type-not-value; emitter cannot raise | artifact grep | `grep -q append_finding .planning/phases/29-decoder-observable/29-AGGREGATION-CONTRACT.md` | ❌ W0 | ⬜ pending |
| 01-T3 policy sign-off | 29-01 | 1 | DEC-01 | T-29-05 | one-way-door decisions attributable | manual | operator signature (see Manual-Only) | ❌ artifact | ⬜ pending |
| 02-T1 walker RED→GREEN | 29-02 | 2 | DEC-01 | T-29-06..T-29-10 | type-not-value record; reserved-key safety; emitter never raises | unit | `uv run pytest packages/higyrus-client/tests/test_decode.py -q --no-cov -x` | ❌ W0 | ⬜ pending |
| 02-T2 higyrus models delegation | 29-02 | 2 | DEC-01 | T-29-11 | `from_api` signature and return contract preserved | unit | `uv run pytest packages/higyrus-client -q --no-cov` | ❌ W0 | ⬜ pending |
| 02-T3 zero-edit merge gate + snapshot regen | 29-02 | 2 | DEC-01 | T-29-11 | no test weakened to make the change pass | integration | `uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q --no-cov` + `git diff --name-only` | ✅ suites exist | ⬜ pending |
| 03-T1 strict_decode carrier | 29-03 | 3 | DEC-01 | T-29-16, T-29-17, T-29-18 | mode carried by state + ContextVar only; view inheritance | unit | `uv run pytest packages/higyrus-client -q --no-cov` + `uv run pytest verification/test_public_surface.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 03-T2 filter fix + decoder sentinel | 29-03 | 3 | DEC-01 | T-29-13, T-29-14, T-29-15 | no credential literal on any of the three record surfaces; bounded recursion | unit | `uv run pytest packages/higyrus-client/tests/test_logging.py packages/higyrus-client/tests/test_decode.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 04-T1 three-arm timing spike | 29-04 | 3 | DEC-01 | T-29-SC, T-29-19, T-29-21 | third-party package executed only in an ephemeral env; no manifest mutated | script + artifact | `git diff --quiet HEAD -- uv.lock pyproject.toml 'packages/*/pyproject.toml'` | ❌ artifact | ⬜ pending |
| 04-T2 msgspec D-lock sign-off | 29-04 | 3 | DEC-01 | T-29-20 | decision attributable; adoption gated | manual | operator signature (see Manual-Only) | ❌ artifact | ⬜ pending |
| 05-T1 market-data copy + carrier + filter | 29-05 | 4 | DEC-01 | T-29-22, T-29-28 | verbatim copy; type-not-value emission; bounded filter recursion | unit | `uv run pytest packages/market-data-client -q --no-cov` + `uv run mypy packages/market-data-client/src` | ❌ W0 | ⬜ pending |
| 05-T2 market-data models delegation | 29-05 | 4 | DEC-01 | T-29-24, T-29-26 | client stamp cannot be overridden from the wire; slots-safe super preserved | unit | `uv run pytest packages/market-data-client -q --no-cov` | ❌ W0 | ⬜ pending |
| 05-T3 async non-clobbering + sentinel | 29-05 | 4 | DEC-01 | T-29-23, T-29-25 | interleaved tasks isolated; plain thread does not inherit | unit | `uv run pytest packages/market-data-client/tests/test_decode_concurrency.py packages/market-data-client/tests/test_logging.py packages/market-data-client/tests/test_decode.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 06-T1 matriz copy + carrier + filter order | 29-06 | 4 | DEC-01 | T-29-30, T-29-35 | package-specific pre-scan still runs before the generic scan | unit | `uv run pytest packages/matriz-client -q --no-cov` + `uv run pytest verification/test_public_surface.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 06-T2 matriz models delegation | 29-06 | 4 | DEC-01 | T-29-31, T-29-32, T-29-33, T-29-34 | Literal membership never enforced; matriz semantics preserved; defaults constructor silent | unit | `uv run pytest packages/matriz-client -q --no-cov` | ❌ W0 | ⬜ pending |
| 06-T3 matriz sentinel + merge gate | 29-06 | 4 | DEC-01 | T-29-29 | no credential literal on any record surface | unit + integration | `uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q --no-cov` | ❌ W0 | ⬜ pending |
| 07-T1 iol copy + carrier + filter + tests | 29-07 | 4 | DEC-01 | T-29-36..T-29-41 | verbatim copy; standalone import; no credential leak | unit | `uv run pytest packages/iol-client -q --no-cov` + `uv run mypy packages/iol-client/src` | ❌ W0 | ⬜ pending |
| 07-T2 ambito copy + carrier + filter + tests | 29-07 | 4 | DEC-01 | T-29-36..T-29-41 | verbatim copy; standalone import; no credential leak | unit | `uv run pytest packages/ambito-financiero-client packages/iol-client -q --no-cov` + `uv run pytest verification/test_public_surface.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 08-T1 ws mode propagation | 29-08 | 5 | DEC-01 | T-29-42, T-29-43, T-29-46 | daemon thread receives mode explicitly; strict decode cannot kill the loop | unit | `uv run pytest packages/matriz-client -q --no-cov` + `uv run mypy packages/matriz-client/src` | ❌ W0 | ⬜ pending |
| 08-T2 ws mode test file | 29-08 | 5 | DEC-01 | T-29-44, T-29-45 | non-inheritance asserted; repeated dispatch stable | unit | `uv run pytest packages/matriz-client/tests/test_ws_decode_mode.py -q --no-cov -x` | ❌ W0 | ⬜ pending |
| 09-T1 intactness checker | 29-09 | 5 | DEC-01 | T-29-47, T-29-48, T-29-49, T-29-52 | copies cannot drift silently; ban-list rejects opt-outs | script | `uv run python tools/check_decode_intactness.py` | ❌ W0 | ⬜ pending |
| 09-T2 CI wiring + wallets exemption | 29-09 | 5 | DEC-01 | T-29-50, T-29-51 | the gate runs in a job that actually executes | script + YAML parse | `uv run python tools/check_decode_intactness.py` + workflow parse assertion | ❌ W0 | ⬜ pending |
| 10-T1 sizing run + floor report | 29-10 | 5 | DEC-01 | T-29-54, T-29-55, T-29-56, T-29-57, T-29-58 | corpus is type-only; no live call; no package source mutated | script + artifact | `git diff --quiet HEAD -- packages/` + 43-row assertion | ❌ artifact | ⬜ pending |
| 10-T2 floor ratification | 29-10 | 5 | DEC-01 | T-29-53 | downstream budget attributable to a signature | manual | operator signature (see Manual-Only) | ❌ artifact | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Sampling continuity:** no three consecutive tasks lack an automated verify. The
three manual tasks (01-T3, 04-T2, 10-T2) are each preceded by an automated task
in the same plan and are separated by at least one automated task across the
wave order.

---

## Wave 0 Requirements

- [x] Existing infrastructure covers pytest/ruff/mypy; no new framework needed
- [ ] Per-package caplog sentinel tests are appended in-package (created in-phase, in-package so they run in the CI matrix — `verification/` never runs in CI because the tests job passes an explicit package path that overrides `testpaths`)
- [ ] `packages/<pkg>/tests/test_decode.py` ×5 — net-new, created by Plans 02, 05, 06, 07
- [ ] `packages/market-data-client/tests/test_decode_concurrency.py` — net-new, Plan 05
- [ ] `packages/matriz-client/tests/test_ws_decode_mode.py` — net-new, Plan 08
- [ ] `tools/check_decode_intactness.py` + `ci.yml` `lint`-job wiring — net-new, Plan 09
- [ ] Zero-edit merge-gate assertion (`git diff --name-only` / `--numstat` over the three SafeModel packages' test directories) — wired in Plan 02 Task 3 and re-asserted in Plans 05, 06, 08

**Baseline captured at plan time:** 872 tests collected across
`packages/higyrus-client packages/matriz-client packages/market-data-client`
(measured 2026-08-18 on branch `milestone/v1.5-mutations`). Every wave re-runs
this set; the count must not fall and no pre-existing test file may show deleted
lines.

**Packaging precondition verified at plan time (research assumption A6):** every
`pyproject.toml` declares the wheel target as a directory
(`packages = ["src/<pkg>"]`), never an explicit module list, so adding
`_decode.py` needs no manifest change and cannot be silently absent from a wheel.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| msgspec timing-spike D-lock sign-off (29-04 T2) | DEC-01 | Operator signs the D-lock artifact with three-arm benchmark numbers; a GO changes six wheels' dependency profile and the Phase 34 release set | Review `29-DLOCK-MSGSPEC.md`; compare arm B against arm C at the stated absolute budget; select `no-go-stdlib-only`, `go-msgspec-fast-path` or `defer` |
| Sizing-run floor sign-off, lower bound per package (29-10 T2) | DEC-01 | Floor becomes Phase 33's declared budget — operator ratifies | Review `29-SIZING.md`: 43 mapping rows, lower-bound floor table, kind breakdown, blind spot, freshness; reply `ratified` or state what must change |
| Strict-on-extra + RESPONSE-`Literal` policy sign-off (29-01 T3) | DEC-01 | Both are one-way doors that Phases 30-34 build on; reversing either after Phase 30 means re-editing shipped surface | Review `29-AGGREGATION-CONTRACT.md` lock 4 and `29-DLOCK-RESPONSE-LITERAL.md`; select `approve-as-drafted`, `strict-raises-on-extra` or `restore-occurrences` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
