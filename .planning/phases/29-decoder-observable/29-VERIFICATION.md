---
phase: 29-decoder-observable
verified: 2026-08-19T23:47:56Z
status: human_needed
score: 5/5 roadmap success criteria verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Decide WR-04: should a dataclass-default field (e.g. Symbol.id: int = 0, market_id: str = '', created_at/updated_at, every matriz field(default_factory=X.empty)) be exempted from `missing` divergence reporting the way `T | None` already is?"
    expected: "One of two outcomes, both defensible and mutually exclusive per 29-REVIEW-FIX.md: (a) YES — apply the `_MISSING`-sentinel patch to all five `_decode.py` copies, add an eighth axis to `29-SEMANTICS-MATRIX.md`, and re-ratify `29-SIZING.md`'s floor downward; or (b) NO — record the current behaviour (every absent-but-defaulted field is `missing` WARNING / strict-fatal) as the eighth axis in the matrix so Phase 33 budgets against it knowingly."
    why_human: "This is a semantics change to what 'optional' means for every model in the repo, collides with signed lock 2 of 29-AGGREGATION-CONTRACT.md and the ratified 29-SIZING.md floor, and the code reviewer explicitly declined to guess at it (29-REVIEW-FIX.md, WR-04 'Deferred Issues' section). Currently every normal payload that omits a defaulted field (e.g. a `/marketdata/latest` no-data row, or any matriz nested default) emits a WARNING and raises in strict mode — correct per the letter of lock 2, but not yet operator-ratified as intended. Present in the shipped code today; not a code defect, a pending one-way-door decision."
---

# Phase 29: Decoder observable Verification Report

**Phase Goal:** Ninguna sustitución de campo vuelve a ser silenciosa — todo consumidor de las 6 libs recibe cada divergencia entre el modelo y el wire como un registro estructurado del logger del paquete, y los drivers pueden pedir modo estricto sin cambiar el comportamiento tolerante del runtime.
**Verified:** 2026-08-19T23:47:56Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Note on scope correction

Per `29-CONTEXT.md` (authoritative over the literal ROADMAP.md text, as instructed): the
copy topology is **5 packages + a documented `wallets-client` exemption**, not a literal
6×. This is verified directly against the codebase (`find packages -name _logging.py`
returns exactly 5 files; `29-WALLETS-EXEMPTION.md` documents why `wallets-client` has no
`_ClientState`, no `_logging.py`, no `_core.py`, no `models.py`, and no bind site).
`REQUIREMENTS.md`'s DEC-01 prose bundles in "los drivers `main_*.py` corren en modo
estricto (divergencia → finding)" — that clause maps to Phase 33 (LIVE-TYP-01) per the
roadmap's phase table and `29-CONTEXT.md`'s deferred-items list ("Handler
`verification/divergences.py`... Phase 33"); the phase goal string given for this
verification only requires drivers to be **able to request** strict mode, which is
verified below.

## Post-execution context accounted for

A code review (`29-REVIEW.md`) found 4 Critical + 7 Warning findings after all 10
SUMMARYs were written. A fix pass (`29-REVIEW-FIX.md`) resolved 10 of 11. This
verification checks the **current, fixed state of the codebase**, not the SUMMARY-time
claims:

- All 10 fix commits (`b9c0048`, `b9cdb48`, `9711806`, `f3484c7`, `d90f472`, `fd5b490`,
  `7d06016`, `2c31790`, `b8c1806`, `3d12a9d`) exist in `git log` and each maps to the
  finding it claims to fix, verified by reading the current source at the cited lines.
- `1531 passed, 1 deselected` reproduced independently in this verification (matches the
  claimed gate exactly).
- `tools/check_decode_intactness.py` reproduced independently: exit 0, Check A hash
  `ac14868282ad0a5c` matching `CANONICAL_DIGEST`, Check B `684191c7cdc5ff9c`, Check C/D
  clean.
- `ruff check .`, `ruff format --check .`, `mypy` all reproduced clean.
- WR-04 is a **deliberate, documented deferral** requiring an operator decision — not a
  code defect and not silently dropped. Recorded above as the single human-verification
  item.

## Goal Achievement

### Observable Truths (mapped to the 5 ROADMAP.md Success Criteria for Phase 29)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A payload with missing/wrong-type/extra/non-dict/None field decodes without raising in observable mode, emits exactly one structured record per divergent field via `logging.getLogger("<pkg>")`, flat/all-str/top-level/type-not-value, never the wire value; a caplog sentinel per package (5) proves no credential leak; the `RedactingFilter` fix ships to all 5 copies of `_logging.py`. | ✓ VERIFIED | `packages/*/src/*/_decode.py` `_emit()` builds all 6 record values from constants/type names only (read at higyrus copy, byte-identical per Check A hash). `isinstance(value, str)` guard present in all 5 `_logging.py` copies (grep confirmed). 87/87 logging tests pass including 5 `test_decode_sentinel_never_leaks_credential`. CR-04 fix (`_safe_key`) sanitizes the one place a wire-derived string could reach `field_path` (the `extra` kind's key name) — verified present in source and covered by new per-package tests. |
| 2 | In strict mode the same divergence raises with the exact field path; mode travels by a `ContextVar` bound from `_ClientState` at the top of `_request` (never env var, never module global); a concurrency test proves survival across interleaved async tasks and explicit (non-inherited) propagation to matriz's `ws_client` daemon thread. | ✓ VERIFIED | `_decode.STRICT_DECODE.set(self._state.strict_decode)` confirmed at the top of `_request`/`AsyncClient._request` in all 5×2 (sync+async) surfaces, no reset (grep, all 10 sites). `strict_decode: bool = False` on `_ClientState`, `bool \| None = None` on all 4 entry points × 5 packages (grep confirmed, no env-var factory found). `test_interleaved_async_tasks_do_not_clobber_each_others_mode`, `test_each_task_gets_its_own_decode_scope` (market-data) and `test_plain_thread_does_not_inherit_the_decode_mode`, `test_connect_snapshots_the_mode_before_the_thread_starts`, `test_strict_mode_reaches_the_daemon_thread_and_routes_its_error` (matriz ws) all pass. WR-06 fix (mode snapshotted on the `WebSocketApp` instance, not a module global cleared by `ws_disconnect`) verified present at `ws_client.py:79-137` and covered by `test_ws_connect_stamps_the_mode_on_the_app_instance` / `test_handle_open_warns_when_the_mode_was_never_handed_over`. |
| 3 | SafeModel suites of the 3 packages stay green with zero test-file edits; `from_api` preserves signature/contract (DT-05); matriz keeps its own semantics (missing→None, no slots, `empty()`, scalar passthrough), reconciled via a 6-way table written **before** decoder code, parameterized per package, never harmonized in silence. | ✓ VERIFIED (with 2 documented, deliberate exceptions) | `29-SEMANTICS-MATRIX.md` exists (261 lines), 6 numbered rows, 7 `DecodePolicy` fields with per-package constants, 3 exemptions cited to file:line, signed as Plan 01 (before Plan 02's walker). `matriz.POLICY = DecodePolicy(None, None, None, None, "empty_classmethod", True, False)` differs from higyrus/market-data's `("", 0, 0.0, False, "from_api_none", False, False)` — confirmed 5/7 fields differ, `test_policy_is_not_the_higyrus_constant` pins it. 1531 tests pass. Two test files were deliberately edited as part of the post-review fix pass, both documented and justified: `market-data-client/tests/test_models.py:154` (`is None`→`== {}`, pins the CR-03 defect fix) and `matriz-client/tests/test_logging.py` (WR-05 fail-closed fix pinned a previously vulnerability-asserting test). These are review-driven defect fixes, not silent harmonization of the zero-edit merge gate. |
| 4 | Both D-locks signed as phase artifacts with evidence both sides: (a) msgspec dual-engine vs stdlib-only, walker load-bearing either way; (b) RESPONSE fields never closed as `Literal`, reaching retroactively to matriz's 9 `types.py` aliases. | ✓ VERIFIED | `29-DLOCK-MSGSPEC.md`: 3-arm benchmark (Arm A uncached / Arm B shipped walker / Arm C msgspec), absolute 100ms budget vs measured 19.37–20.69ms (4.8× headroom) → `NO-GO`, `Signed: sebadlf`, `2026-08-19`. `uv.lock`/`pyproject.toml` byte-unchanged (grep for "msgspec" returns nothing; no commit touches `uv.lock` since the market-data v0.4.0 bump, well before this phase). `29-DLOCK-RESPONSE-LITERAL.md` signed; walker's `Literal` branch (`_decode.py:521-534`) never enforces membership (`policy.literal_enforced` is `False` in all 5 copies, D-09 states not a tunable), validates only runtime type. |
| 5 | Decode helper copied verbatim in 5 packages (+ documented wallets exemption) with a hash + ban-list intactness test; exploratory sizing run over the corpus publishes a per-package floor (`≥ N`, never `N`) as the declared Phase 33 budget. | ✓ VERIFIED | `tools/check_decode_intactness.py` reproduced: exit 0, Check A (5→1 hash matching pinned `CANONICAL_DIGEST`), Check B (5 filter scan regions→1 hash), Check C (ban-list scoped to `_decode.py`), Check D (5 in-scope + `wallets-client` exempt). CI wires it at `.github/workflows/ci.yml:51-55`. `29-SIZING.md` re-bases the corpus onto `.planning/verification/schemas/` (D-08, documented reason ROADMAP's named corpus is payload-empty) — higyrus `≥22`, matriz `≥24`, market-data `≥50`, iol/ambito correctly reported `N/A` (not `0`) with a written reason (no `models.py` yet). Signed `"ratified" — sebadlf`. |

**Score:** 5/5 ROADMAP success criteria verified (0 present-but-behavior-unverified). One item (WR-04) is a documented, in-scope deferred design decision, not a failed or unverified truth — routed to human verification per the task's explicit instruction, not scored as a gap.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/{higyrus,market-data,matriz,iol,ambito-financiero}-client/src/*/_decode.py` | Canonical walker, verbatim ×5 | ✓ VERIFIED | 5 files present, Check A hash-identical, canonical digest pinned. |
| `packages/*/src/*/_logging.py` (5) | Bounded-recursion `RedactingFilter` fix | ✓ VERIFIED | `isinstance(value, str)` guard + `_MAX_SCAN_DEPTH=4`/`_MAX_SCAN_ENTRIES=64` present in all 5; Check B hash-identical scan regions. |
| `packages/*/src/*/_state.py` (5) | `strict_decode: bool = False` field | ✓ VERIFIED | Confirmed via `_ClientState` field + `strict_decode` kwarg on 4 entry points × 5 packages. |
| `packages/matriz-client/src/matriz_client/ws_client.py` | Explicit mode propagation to daemon thread | ✓ VERIFIED | `_DECODE_STRICT_ATTR` stamped on `WebSocketApp` by `ws_connect`, read by `_handle_open`; WR-06 fix confirmed present, not reverted to the module-global race. |
| `tools/check_decode_intactness.py` | Hash + ban-list intactness gate | ✓ VERIFIED | Ran directly, exit 0, 4 checks pass; WR-07 fix (pinned `CANONICAL_DIGEST`, filename-scoped ban list) present. |
| `.planning/phases/29-decoder-observable/29-SEMANTICS-MATRIX.md` | 6-way `from_api` table | ✓ VERIFIED | 6 rows, 7 policy axes, 3 exemptions, amended post-review (WR-01, WR-02, WR-03 sections added). |
| `.planning/phases/29-decoder-observable/29-AGGREGATION-CONTRACT.md` | 12-lock record/scope/redaction contract, signed | ✓ VERIFIED | Signed `sebadlf`; amended post-review (lock 6 retirement mechanism, lock 11 sanitization). |
| `.planning/phases/29-decoder-observable/29-DLOCK-RESPONSE-LITERAL.md` | D-09 sign-off | ✓ VERIFIED | Signed `sebadlf`, 9 matriz aliases named. |
| `.planning/phases/29-decoder-observable/29-DLOCK-MSGSPEC.md` | D-lock (a) sign-off | ✓ VERIFIED | Signed `sebadlf`, NO-GO, evidence both sides recorded. |
| `.planning/phases/29-decoder-observable/29-SIZING.md` | Sizing floor, ratified | ✓ VERIFIED | Signed/ratified `sebadlf`. |
| `.planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md` | Documented `wallets-client` exemption | ✓ VERIFIED | Matches actual `wallets-client` file layout (no `_state.py`/`_logging.py`/`_core.py`/`models.py`). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `higyrus_client/models.py::SafeModel.from_api` | `_decode.py::walk_model` | delegation | ✓ WIRED | `_decode.walk_model(cls, payload, policy=_decode.POLICY, sink=...)`, 872-test merge gate green. |
| `market_data_client/models.py::MarketDataSnapshot.from_api` | `_decode.py::walk_model` + `_apply_mapping_policy` | delegation + CR-03 mapping pass | ✓ WIRED | Both `SafeModel.from_api` and `MarketDataSnapshot.from_api` call `_apply_mapping_policy` after the walk; `market_data` field no longer silently `None`. |
| `matriz_client/_core.py` (20 parsers) + `ws_client.py::_parse_frame` | `_decode.py::_response_parser` | decorator | ✓ WIRED | 20 `@_decode._response_parser` sites in matriz `_core.py` + 1 in `ws_client.py`, matching the review-fix's claimed count. |
| `<pkg>/client.py`/`aio.py::_request` (×5×2) | `_decode.py::STRICT_DECODE`/`open_request_scope` | bind at request top | ✓ WIRED | Confirmed at all 10 sites (5 packages × sync/async), `.set()` with no reset, matching D-03. |
| `matriz_client/ws_client.py::ws_connect` | `_decode.py::STRICT_DECODE` (daemon thread) | explicit attribute stamp, not inheritance | ✓ WIRED | `setattr(_ws, _DECODE_STRICT_ATTR, ...)` before thread start; `_handle_open` reads it, warns if absent. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full decode-affected test suite (5 packages) | `uv run pytest packages/{higyrus,matriz,market-data,iol,ambito-financiero}-client -q --no-cov` | `1531 passed, 1 deselected in 91.81s` | ✓ PASS (matches claimed gate exactly) |
| Intactness gate | `uv run python tools/check_decode_intactness.py` | exit 0, digest `ac14868282ad0a5c` matches pin | ✓ PASS |
| Strict-mode dedupe fix (CR-02) | `pytest -k strict_mode_raises_on_every_visit` (higyrus) | 14 passed | ✓ PASS |
| Deterministic emission ordering (backstop-marked truth, Plan 02) | `pytest -k emission_order` (higyrus) | 2 passed | ✓ PASS |
| Async/thread concurrency (criterion 2) | `pytest test_decode_concurrency.py test_ws_decode_mode.py` | 1 + 14 passed | ✓ PASS |
| Static analysis | `uv run ruff check .` / `ruff format --check .` / `uv run mypy` | all clean | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|--------------|-------------|--------|----------|
| DEC-01 | 29-01 through 29-10 (all 10 plans) | Decoder observable across 5 packages + wallets exemption | ✓ SATISFIED | See Observable Truths above. No orphaned requirements: REQUIREMENTS.md maps DEC-01 to Phase 29 only, and all 10 plans declare `requirements: [DEC-01]`. |

REQUIREMENTS.md's DEC-01 prose additionally names "los drivers `main_*.py` corren en modo
estricto (divergencia → finding)" — confirmed **not yet done** (`grep strict_decode
main_*.py` finds no call sites) and **not required by this phase's goal string**, which
only requires drivers to be *able to* request strict mode (verified). That capability
belongs to Phase 33 (LIVE-TYP-01) per the roadmap's requirement-to-phase table and
`29-CONTEXT.md`'s deferred-items list. Not a gap of Phase 29.

### Anti-Patterns Found

None blocking. No `TBD`/`FIXME`/`XXX` markers in any file touched by this phase
(`_decode.py`, `_logging.py`, `_state.py`, `models.py`, `ws_client.py`,
`check_decode_intactness.py` — all checked, zero matches). 4 Info-tier findings from
`29-REVIEW.md` (IN-01 dead `open_request_scope()` call, IN-02 `_MAX_SCAN_ENTRIES=64`
redaction bypass at the boundary, IN-03 matriz missing one parity assertion, IN-04 latent
multi-arm `Union` pass-through with no current model triggering it) remain unfixed by
design (declared out of the `critical_warning` fix-pass scope in `29-REVIEW-FIX.md`).
None of the four affects the phase goal today — IN-04 is explicitly latent ("No shipped
model declares such a field today"). Not blocking, noted for awareness.

### Human Verification Required

1. **WR-04 — dataclass-default fields and `missing` reporting**
   - **Test:** Decide whether a field declared with a `dataclasses.Field.default` /
     `default_factory` (e.g. `Symbol.id: int = 0`, `market_id: str = ""`,
     `created_at`/`updated_at`, every matriz `field(default_factory=X.empty)`) should be
     treated as an implicit opt-out of `missing` reporting, the way `T | None` already is.
   - **Expected:** An explicit operator ruling, recorded as either (a) an accepted
     `_MISSING`-sentinel patch across all 5 `_decode.py` copies plus an eighth axis in
     `29-SEMANTICS-MATRIX.md` plus a re-ratified (lower) `29-SIZING.md` floor, or (b) an
     explicit "no, current behaviour is intended" ruling recorded as the eighth axis so
     Phase 33 budgets against it knowingly.
   - **Why human:** One-way-door semantics change affecting every model in the repo,
     colliding with a signed lock (`29-AGGREGATION-CONTRACT.md` lock 2) and a ratified
     sizing floor. Both outcomes are internally consistent; picking one without the
     operator is exactly the kind of unilateral one-way-door call `29-REVIEW-FIX.md`
     itself declined to make. This is a live, present behavior in shipped code today
     (confirmed: `walk_model` supplies a value for every declared field regardless of
     `dataclasses.Field.default`), not a hypothetical.

### Gaps Summary

No blocking gaps. All 5 ROADMAP.md success criteria are verified against the current,
post-review-fix state of the codebase, independently reproduced (test suite, intactness
gate, static analysis) rather than taken from SUMMARY.md or REVIEW-FIX.md claims. The
sole open item is a deliberately deferred, explicitly-flagged design decision (WR-04)
that the code review itself declined to resolve without operator input — it does not
represent unfinished or silently-dropped work, and per this task's explicit instruction it
is routed to human verification rather than scored as a gap.

---

_Verified: 2026-08-19T23:47:56Z_
_Verifier: Claude (gsd-verifier)_
