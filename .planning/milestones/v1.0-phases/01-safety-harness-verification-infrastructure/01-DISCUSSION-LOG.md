# Phase 1: Safety Harness & Verification Infrastructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 1-safety-harness-verification-infrastructure
**Areas discussed:** Execution model, Harness location, Findings format, Fixtures + PII, Schema-snapshot scope, Redaction, Driver orchestration

---

## Execution Model

| Option | Description | Selected |
|--------|-------------|----------|
| Drivers explore, mock asserts | `main_*.py` = manual live-exploration vehicle; mocked regression tests are the only thing in CI; `@live` registered but off | ✓ |
| `@live` tests as the vehicle | Live verification written as `@pytest.mark.live` tests, drivers become trivial smoke | |
| Hybrid: drivers + some `@live` | Drivers for open exploration + a small set of `@live` tests for assertions worth formalizing | |

**User's choice:** Drivers explore, mock asserts.
**Notes:** Respects PROJECT.md's "vehicle = main_*.py" decision and keeps CI deterministic/offline.

### Follow-up — proving the `@live` marker works

| Option | Description | Selected |
|--------|-------------|----------|
| A trivial `@live` proof test | One minimal `@pytest.mark.live` test that demonstrates deselect-without-`--live` / select-with-`--live`; no network; copyable example | ✓ |
| Register + flag-behavior test only | Register marker + test the flag via pytest config, no real `@live` test | |

**User's choice:** A trivial `@live` proof test.
**Notes:** Makes the phase goal's "proven" literally true and leaves a pattern for Phases 2-5.

---

## Harness Location

| Option | Description | Selected |
|--------|-------------|----------|
| `verification/` module at root | Local non-published module outside `packages/` (redact, env_gate, findings, capture), imported by drivers | ✓ |
| Single `_harness.py` at root | One file with all helpers; simpler, risk of becoming a junk drawer | |
| Duplicated per driver | Each `main_*.py` carries its own copy; mirrors package isolation but duplicates security-sensitive redaction in 4-5 places | |

**User's choice:** `verification/` module at root.
**Notes:** The "no shared code" constraint applies to publishable packages; this tooling is not published, so a single source of truth avoids security-code drift.

---

## Findings Format

| Option | Description | Selected |
|--------|-------------|----------|
| Index table + section per finding | Run-context header + summary table (ID, class, surface, status) + detailed section per finding (expected-vs-actual, linked test/issue) | ✓ |
| Table only | Single markdown table, one row per finding; compact but no room for expected-vs-actual diffs | |
| Sections only | One heading per finding, no scannable index | |

**User's choice:** Index table + section per finding.

### Follow-up — finding status lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| OPEN→CONFIRMED→FIXED + EXPECTED | Full lifecycle with a terminal EXPECTED/NO-FIX state for confirmed-correct behavior; no severity field | ✓ |
| OPEN → CLOSED (binary) | Simpler but loses confirmed-but-unfixed vs not-a-bug distinction | |
| With severity field | Lifecycle + critical/major/minor severity per finding | |

**User's choice:** OPEN→CONFIRMED→FIXED + EXPECTED, no separate severity field (kept lean).

---

## Fixtures + PII Anonymization

| Option | Description | Selected |
|--------|-------------|----------|
| PII denylist + synth + manual gate | Per-package PII-key denylist replaced with type/format-preserving synthetic values + mandatory manual review before commit | ✓ |
| Allowlist of safe keys | Keep only allowlisted keys, placeholder the rest; safer default but breaks fixtures whose bug depends on an unlisted value | |
| 100% manual review | Dev hand-edits each fixture, no scrubber; contradicts HARN-06's "pipeline" | |

**User's choice:** PII denylist + synthetic + mandatory manual gate.

### Follow-up — pipeline mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Two stages: gitignored staging → anonymize | Driver dumps raw payload to gitignored `captures/` → anonymization step emits committable fixture + test stub | ✓ |
| One stage: capture+anonymize inline | Single helper captures and anonymizes; raw and clean coexist, easier to commit the wrong one | |
| Manual copy to fixture | Dev copies payload by hand; contradicts HARN-06 | |

**User's choice:** Two stages — gitignored staging → anonymize. Raw PII never enters git by construction.

---

## Schema-Snapshot Scope (Phase 1 vs Phase 2)

| Option | Description | Selected |
|--------|-------------|----------|
| Tooling in Phase 1, first use in Phase 2 | Snapshot tool built as generic infra in `verification/`; first real snapshot committed in Phase 2 (DRIFT-01) | ✓ |
| Defer all to Phase 2 | Build nothing in Phase 1; Phase 2 builds it when first needed | |

**User's choice:** Tooling in Phase 1, first use in Phase 2.
**Notes:** Roadmap's Phase-1 summary line includes schema-snapshot tooling; this keeps "Phase 1 = all plumbing built and proven."

---

## Redaction

| Option | Description | Selected |
|--------|-------------|----------|
| `redact()` + `safe_print` defense in depth | Explicit `redact()` (short prefix + `…`) + `safe_print` that masks known credential values even in raw dict prints | ✓ |
| `redact()` explicit only | Helper the dev must remember to wrap each sensitive value; raw dict print leaks the token | |
| Global stdout interceptor | Replace `sys.stdout` to mask everything matching secret patterns; max coverage but fragile/surprising | |

**User's choice:** `redact()` + `safe_print` defense in depth. Makes "tokens never printed in full" structural.

---

## Driver Orchestration / SKIPPED

| Option | Description | Selected |
|--------|-------------|----------|
| Thin runner + independent drivers | `main_verify.py` runs all 5, aggregates RAN/SKIPPED, never halts on SKIPPED; each driver still runnable solo; per-driver `require_env([...])` | ✓ |
| Independent drivers only | No aggregate runner; "not blocking" = clean exit code 0 so a shell loop continues | |
| Runner as sole entry point | Aggregate runner is the normal flow, `main_*.py` become thin; loses comfortable per-client runs | |

**User's choice:** Thin runner + independent drivers.
**Notes:** The verification cycle proceeds client-by-client (Phases 2-5), so first-class individual runs matter.

---

## Claude's Discretion

- Exact file split inside `verification/` (one module vs several submodules).
- Exact prefix length / masking format for `redact()` (4 chars + `…` is the default intent).
- Internal structure of the schema-snapshot file format (keys + types, not values).
- Whether the aggregate runner invokes drivers via subprocess or in-process import.

## Deferred Ideas

- Open research item (Phase 1 planning): how `verification/` is importable under
  `uv run --package <pkg>` — workspace member vs `sys.path` vs dev-only config.
- prod-vs-sandbox gap for Matriz — recorded as an explicit open question for downstream, not closed this cycle.
- v2 error-edge mock coverage (ERR-01, ERR-02) — deferred to v2, not this milestone.
