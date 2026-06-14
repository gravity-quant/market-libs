---
phase: 12
slug: codegen-spike
status: populated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-14
populated: 2026-06-14
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> **Note:** Phase 12 is a SPIKE phase. "Validation" here is not a pytest suite — it is the
> 8-item D-RIGOR-01 evidence checklist (re-run end-to-end in Plan 03 Task 12-03-01) plus
> the 5 ROADMAP success criteria. The Per-Task Verification Map below lists every spike
> task with its automated command (copied verbatim from each plan's `<verify>` block).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | shell scripts + Python stdlib (`ast`, `hashlib`, `importlib.util`, `subprocess`) + `uv run --with unasync` + `uv run ruff` + `uv run mypy` + `uv run lint-imports` + `uv run --package ambito-financiero-client pytest` |
| **Config file** | none (spike is throwaway; no pyproject.toml / pytest.ini edits — Phase 16 GO branch would add codegen verify-clean to root config) |
| **Quick run command** | `bash` per-experiment via `uv run --with unasync python .planning/spikes/SPIKE-005-codegen-tool-choice/<sub>/<experiment>.py` (e.g., `uv run --with unasync python .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/experiment.py`) |
| **Full suite command** | run all 4 sub-experiments (001a/b/c/d) + Plan 03 Task 12-03-01 evidence-checklist.txt regeneration (8 D-RIGOR-01 items + timebox + aggregate verdict) |
| **Estimated runtime** | ~30-60 min total across all 4 sub-experiments + 8-item evidence re-run (most time is `uv run --with unasync` cold-start + mypy strict on ámbito; matriz audit is ast.walk over 852 LOC, ~1 sec) |

---

## Sampling Rate

- **After every task commit:** spike experiments are NOT test-like; the gate is the FINDING.md verdict per sub-experiment. Each task's `<verify><automated>` block re-runs the experiment artifact checks.
- **After every plan wave:** 12-VALIDATION.md per-task verification map row marked ✅ / ❌ for the wave's tasks.
- **Before phase close-out (Plan 03 Task 12-03-01):** all 5 ROADMAP success criteria mapped + 8-item D-RIGOR-01 evidence checklist re-run end-to-end + operator-signed DECISION.md (Task 12-03-02).
- **Max feedback latency:** 1 day (D-SCOPE-03 hard timebox; > 24h triggers AUTO-NO-GO).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | REFAC-06 | T-12-01-SC | Operational pre-gate before any package install; no `.env` read, no packages/ mutation | signoff | `<human-check>Operator types "approved" OR provides documented exception</human-check>` | N/A (checkpoint) | ⬜ pending |
| 12-01-02 | 01 | 1 | REFAC-06 | T-12-01-SC, T-12-01-02 | Spike bootstrap never reads `.env`; never writes under `packages/`; slopcheck re-verified on `unasync` install | experiment | `test -d .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output && ... && grep -q '\| 005 \| codegen-tool-choice \|' .planning/spikes/MANIFEST.md && grep -q '^nyquist_compliant: true$' .planning/phases/12-codegen-spike/12-VALIDATION.md && test "$(git status --porcelain packages/ \| wc -l \| tr -d ' ')" = "0"` | ✅ post-task | ⬜ pending |
| 12-01-03 | 01 | 1 | REFAC-06 | T-12-01-02, T-12-01-05 | Spike experiment.py uses shutil.copy + subprocess only; never imports from packages/*/src/; never mutates packages/; FINDING.md verdict gated on transcripts | experiment | `test -f .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py && test -f .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/diff_vs_v1.1_client.txt && grep -qE '^\*\*Verdict:\*\* (PASS\|FAIL)' .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/FINDING.md && grep -q 'B8 IDENTITY' .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/run_log.txt && test "$(git status --porcelain packages/ \| wc -l \| tr -d ' ')" = "0"` | ✅ post-task | ⬜ pending |
| 12-02-01 | 02 | 2 | REFAC-06 | T-12-02-04 | Marker prepended via str.__add__ (deterministic ordering); never mutates 001a output | experiment | `test -f .planning/spikes/SPIKE-005-codegen-tool-choice/001b-ambito-marker-future-compat/client_with_marker.py && head -1 .../client_with_marker.py \| grep -q '@generated' && grep -cE '^=== (ruff check\|ruff format --check\|mypy --strict\|ast\.parse) ===$' .../verification_transcripts.txt \| grep -q '^4$' && head -1 .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py \| grep -qv '^# @generated'` | ✅ post-task | ⬜ pending |
| 12-02-02 | 02 | 3 | REFAC-06 | T-12-02-03 | Audit walks matriz aio.py read-only; ast.parse never executes code; zero DENY-LIST-VIOLATION rows enforced via grep gate; audit.py actually executed (not hand-crafted) | experiment | `test -f .planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit/matriz-aio-constructs.md && test "$(grep -cE '\| (REVIEW\|TBD\|DENY-LIST-VIOLATION) \|' .../matriz-aio-constructs.md)" = "0" && grep -q 'MERGE GATE PASS' .../matriz-aio-constructs.md && test -f .planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit/audit-run.log && grep -q "Audit written to" .../audit-run.log` | ✅ post-task | ⬜ pending |
| 12-02-03 | 02 | 4 | REFAC-06 | T-12-02-01 | sha256 comparison runs in sandbox (`WORK/matriz_copy/`); deny-listed files never passed to unasync (fpath_list scope only contains aio.py) | experiment | `test -f .planning/spikes/SPIKE-005-codegen-tool-choice/001d-matriz-deny-list-config/verification_transcripts.txt && grep -q '_token_store.py:' .../verification_transcripts.txt && grep -q '_refresh_policy.py:' .../verification_transcripts.txt && grep -q 'ws_client.py:' .../verification_transcripts.txt && grep -qE '^\*\*Verdict:\*\* (PASS\|FAIL)' .../FINDING.md && test "$(git status --porcelain packages/ \| wc -l \| tr -d ' ')" = "0"` | ✅ post-task | ⬜ pending |
| 12-03-01 | 03 | 5 | REFAC-06 | T-12-03-03, T-12-03-05 | Item-6 ámbito pytest runs in `/tmp/spike-005-ambito-test-<ts>/` sandbox (NOT packages/); sandbox cleaned at task end; DECISION.md frontmatter parseable YAML | evidence-checklist | `test -f .planning/spikes/SPIKE-005-codegen-tool-choice/evidence-checklist.txt && test -f .planning/spikes/SPIKE-005-codegen-tool-choice/DECISION.md && grep -cE '^=== D-RIGOR-01 item [1-8]:' .../evidence-checklist.txt \| grep -q '^8$' && grep -q '=== TIMEBOX CHECK (D-SCOPE-03) ===' .../evidence-checklist.txt && grep -qE 'Final: (GO\|NO-GO)$' .../evidence-checklist.txt && grep -qE '^decision: (TBD\|GO\|NO-GO)$' .../DECISION.md && test "$(ls /tmp/spike-005-ambito-test-* 2>/dev/null \| wc -l \| tr -d ' ')" = "0"` | ✅ post-task | ⬜ pending |
| 12-03-02 | 03 | 5 | REFAC-06 | T-12-03-02, T-12-03-04 | Operator signoff captured in DECISION.md frontmatter (signoff_date + signoff_by); audit trail in git history; YAML-parseable | signoff | `<human-check>Operator response matches (GO\|NO-GO) YYYY-MM-DD <name>; DECISION.md frontmatter updated; MANIFEST.md SPIKE-005 row no longer TBD</human-check>` | N/A (checkpoint) | ⬜ pending |
| 12-03-03 | 03 | 6 | REFAC-06 | T-12-03-01 | PRECONDITION read of DECISION.md `decision: GO`; SKIP if NO-GO; never mutates packages/; SKILL.md frontmatter shape validated | close-out | `grep -q '^decision: GO$' .planning/spikes/SPIKE-005-codegen-tool-choice/DECISION.md && test -d .claude/skills/spike-findings-codegen-market-libs/ && test -f .claude/skills/spike-findings-codegen-market-libs/SKILL.md && grep -q 'spike-findings-codegen-market-libs' CLAUDE.md && test -f .planning/phases/12-codegen-spike/12-SUMMARY.md && grep -q '^decision: GO$' .planning/phases/12-codegen-spike/12-SUMMARY.md && grep -q '^phase_16_status: PROCEED$' .planning/phases/12-codegen-spike/12-SUMMARY.md` | ✅ post-task (GO branch) | ⬜ pending |
| 12-03-04a | 03 | 6 | REFAC-06 | T-12-03-01 | PRECONDITION read of DECISION.md `decision: NO-GO`; SKIP if GO; spike-only writes (`.planning/spikes/`, `.claude/skills/`, `.planning/todos/pending/`); MANIFEST.md row flipped; never mutates packages/ | close-out | `grep -q '^decision: NO-GO$' .planning/spikes/SPIKE-005-codegen-tool-choice/DECISION.md && test -f .planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md && grep -q '## Root Cause Analysis' .../NO-GO.md && test -f .planning/todos/pending/spike-codegen-libcst-v1.3.md && test -f .claude/skills/spike-findings-codegen-market-libs/SKILL.md && grep -q 'NO-GO' .claude/skills/spike-findings-codegen-market-libs/SKILL.md && grep -q '\| 005 \| codegen-tool-choice .* NO-GO' .planning/spikes/MANIFEST.md` | ✅ post-task (NO-GO branch) | ⬜ pending |
| 12-03-04b | 03 | 6 | REFAC-06 | T-12-03-01 | PRECONDITION read of NO-GO.md existence (from 12-03-04a); REQUIREMENTS.md + ROADMAP.md + CLAUDE.md + 12-SUMMARY.md edits; never mutates packages/ | close-out | `test -f .planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md && grep -q 'REFAC-06.*deferred per Phase 12 NO-GO' .planning/REQUIREMENTS.md && grep -q 'Defer to v1.3' .planning/REQUIREMENTS.md && grep -q '4/5 requirements mapped' .planning/REQUIREMENTS.md && grep -q 'DROPPED.*Phase 12 NO-GO' .planning/ROADMAP.md && grep -q 'spike-findings-codegen-market-libs' CLAUDE.md && test -f .planning/phases/12-codegen-spike/12-SUMMARY.md && grep -q '^decision: NO-GO$' .planning/phases/12-codegen-spike/12-SUMMARY.md && grep -q '^phase_16_status: DROPPED$' .planning/phases/12-codegen-spike/12-SUMMARY.md` | ✅ post-task (NO-GO branch) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Branching:** Tasks 12-03-03 (GO) and 12-03-04a + 12-03-04b (NO-GO) are mutually exclusive — exactly one branch executes based on the operator signoff in 12-03-02. The opposite branch SKIPS per its PRECONDITION read of DECISION.md frontmatter.

---

## Wave 0 Requirements

Wave 0 (bootstrap) is satisfied by Plan 01 Task 12-01-02:

- [ ] `.planning/spikes/SPIKE-005-codegen-tool-choice/` (top-level spike directory with README.md frontmatter `spike: 005`)
- [ ] `.planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/` (sub-directory + README.md + experiment.py placeholder + output/ + FINDING.md placeholder)
- [ ] `.planning/spikes/SPIKE-005-codegen-tool-choice/001b-ambito-marker-future-compat/` (sub-directory + README.md + experiment.py placeholder + FINDING.md placeholder)
- [ ] `.planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit/` (sub-directory + README.md + audit.py placeholder + FINDING.md placeholder)
- [ ] `.planning/spikes/SPIKE-005-codegen-tool-choice/001d-matriz-deny-list-config/` (sub-directory + README.md + experiment.py placeholder + FINDING.md placeholder)
- [ ] `.planning/spikes/MANIFEST.md` row for SPIKE-005 appended (status=in-progress at bootstrap)
- [ ] `.planning/phases/12-codegen-spike/12-VALIDATION.md` populated (this file — `nyquist_compliant: true` + `wave_0_complete: true` + Per-Task Verification Map filled)

*Note:* No new pytest config or framework install. The spike reuses the repo's existing ruff/mypy/pytest/import-linter stack; `unasync` is installed transiently via `uv run --with unasync`.

---

## ROADMAP Success Criteria → Testable Assertion

The phase ships when ALL applicable assertions pass. SC#4 and SC#5 are mutually exclusive (one per decision branch).

| SC # | Description | Testable Assertion | Owning Task |
|------|-------------|---------------------|-------------|
| SC#1 | Byte-identical round-trip ámbito (modulo `ruff format`) | `diff -u packages/ambito-financiero-client/src/ambito_financiero_client/client.py .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py` exits 0 (empty diff) | 12-01-03, re-run in 12-03-01 (D-RIGOR-01 item 1) |
| SC#2 | B8 identity preserved on generated output | 001a `experiment.py` Step 8 assertion passes: `mod._raise_for_response is aio._raise_for_response is _core.raise_for_response` AND `run_log.txt` contains `B8 IDENTITY: PASS` | 12-01-03, re-run in 12-03-01 (D-RIGOR-01 item 2) |
| SC#3 | Matriz construct audit — zero TBD/REVIEW rows | `grep -cE '\| (REVIEW\|TBD\|DENY-LIST-VIOLATION) \|' .planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit/matriz-aio-constructs.md` returns 0 AND file contains `MERGE GATE PASS` line | 12-02-02 |
| SC#4 (GO branch) | GO Rule config + `@generated` marker captured in DECISION.md | DECISION.md frontmatter `decision: GO` AND body contains per-package `unasync.Rule(...)` config blocks for ambito/iol/higyrus/matriz (4 blocks) AND a recommended `@generated` marker syntax block AND a Phase 16 production integration recommendation section | 12-03-02 (signoff), 12-03-03 (artifact production) |
| SC#5 (NO-GO branch) | NO-GO defer-to-v1.3 close-out | REQUIREMENTS.md REFAC-06 moved to "Future Requirements (Defer to v1.3+)" AND ROADMAP.md Phase 16 marked `DROPPED` (status column + summary checklist) AND `.planning/todos/pending/spike-codegen-libcst-v1.3.md` exists with frontmatter `target_milestone: v1.3` | 12-03-04b |

---

## D-RIGOR-01 8-Item Evidence Checklist Contract

This is the canonical contract for the spike. All 8 items MUST PASS for a GO decision. ANY single FAIL triggers NO-GO (per D-RIGOR-01 + D-SCOPE-03). The evidence is collected end-to-end in Plan 03 Task 12-03-01 (`evidence-checklist.txt`). The map below shows each item's source sub-experiment + verification command.

| # | Evidence Item | Source Sub-Experiment | Verification Command (re-run in 12-03-01) | Source Artifact |
|---|---------------|-----------------------|--------------------------------------------|------------------|
| 1 | Byte-identical round-trip ámbito | 001a (Plan 01 Task 12-01-03) | `diff -u packages/ambito-financiero-client/src/ambito_financiero_client/client.py .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py` (must exit 0) | `001a/diff_vs_v1.1_client.txt` |
| 2 | B8 identity preserved on generated | 001a (Plan 01 Task 12-01-03) | Re-load via `importlib.util.spec_from_file_location` + assert `mod._raise_for_response is aio._raise_for_response is _core.raise_for_response` (re-run from `001a/experiment.py` Step 8) | `001a/run_log.txt` |
| 3 | `uv run ruff format --check` clean (format-stable / idempotent) | 001a (Plan 01) + 001b (Plan 02 Task 12-02-01) | `uv run ruff format --check .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py` (exit 0) | re-run captured in 12-03-01 `evidence-checklist.txt` |
| 4 | `uv run ruff check` clean (incl. ASYNC1xx) | 001b (Plan 02 Task 12-02-01) | `uv run ruff check .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py` (exit 0) | re-run captured in 12-03-01 `evidence-checklist.txt` |
| 5 | `uv run mypy --strict` clean | 001b (Plan 02 Task 12-02-01) | `uv run mypy --strict .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py` (exit 0) | re-run captured in 12-03-01 `evidence-checklist.txt` |
| 6 | Ámbito mocked pytest suite green vs generated | sandbox per Anti-Pitfall 2 in Plan 03 Task 12-03-01 | Create `/tmp/spike-005-ambito-test-<ts>/`, `cp -r packages/ambito-financiero-client/` into it, overwrite `<sandbox>/src/ambito_financiero_client/client.py` with the generated file, then `cd <sandbox> && uv run --package ambito-financiero-client pytest -q` (exit 0); cleanup `rm -rf /tmp/spike-005-ambito-test-*` at task end | re-run captured in 12-03-01 `evidence-checklist.txt` |
| 7 | `uv run lint-imports` 4 existing contracts intact | 12-03-01 Task (against production `packages/`, confirms no regression) | `uv run lint-imports` (exit 0) | re-run captured in 12-03-01 `evidence-checklist.txt` |
| 8 | `@generated` marker compatible with `from __future__ import annotations` | 001b (Plan 02 Task 12-02-01) | Re-confirm from `001b/verification_transcripts.txt` (all 4 sub-commands: `ruff check`, `ruff format --check`, `mypy --strict`, `ast.parse` exit 0) | `001b/verification_transcripts.txt` |

**Aggregate gate (12-03-01 builds the AGGREGATE VERDICT block):**

- **GO** iff 8/8 items PASS AND matriz audit unresolved rows == 0 (SC#3) AND timebox status == `WITHIN-CAP` (D-SCOPE-03).
- **NO-GO** if ANY of: any item FAILs, matriz unresolved rows > 0, timebox `OVER-CAP`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| v1.1 head `71bf201` confirmed CI-green on Python 3.13 | REFAC-06 (operational pre-gate) | Requires a human to look at GitHub Actions UI (or `gh run list`) for a specific historical commit | Plan 01 Task 12-01-01 — see its `<how-to-verify>` block: open https://github.com/<owner>/market-libs/actions, locate the run for `71bf201`, confirm conclusion=success AND matrix includes Python 3.12 AND 3.13 |
| Operator binary GO/NO-GO signoff on DECISION.md | REFAC-06 (decision artifact) | Binary judgment requires human signoff; cannot be auto-derived (recommended decision is auto-computed in 12-03-01 but signoff is operator-only) | Plan 03 Task 12-03-02 — see its `<resume-signal>`: operator responds with `(GO\|NO-GO) YYYY-MM-DD <name>` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify OR Wave 0 dependencies satisfied (checkpoint tasks use `<human-check>` per workflow rules)
- [x] Sampling continuity: no 3 consecutive auto tasks without automated verify
- [x] Wave 0 covers all MISSING references (Plan 01 Task 12-01-02 + this file)
- [x] No watch-mode flags
- [x] Feedback latency < 1 day (D-SCOPE-03 cap)
- [x] `nyquist_compliant: true` set in frontmatter
- [x] `wave_0_complete: true` set in frontmatter (will be marked complete after Task 12-01-02 runs)

**Approval:** approved 2026-06-XX
