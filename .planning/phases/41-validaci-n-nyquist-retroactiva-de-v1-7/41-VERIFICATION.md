---
phase: 41-validaci-n-nyquist-retroactiva-de-v1-7
verified: 2026-08-31T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 41: Validación Nyquist retroactiva de v1.7 — Verification Report

**Phase Goal:** Las cinco fases de v1.7 que nunca corrieron su validación dejan de tener cobertura desconocida — cada criterio queda con una disposición explícita y con la evidencia que la sostiene nombrada, producida contra el árbol de v1.7 congelado y antes de que v1.8 toque una sola línea de fuente.
**Verified:** 2026-08-31
**Status:** passed
**Re-verification:** No — initial verification

This is a goal-backward verification with independent re-execution: every command cited by the five audited artifacts as evidence was re-run directly by this verifier (not copy-pasted from SUMMARY/VALIDATION claims), and the disposition arithmetic was independently recomputed from the raw table text with `awk`/`grep`, not read off the artifacts' own summary tables.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth (ROADMAP Success Criterion) | Status | Evidence |
|---|-------|--------|----------|
| 1 | Artefacto de validación existe para las 5 fases (35–39), cada uno declara el SHA del árbol v1.7, y ningún byte de fuente de v1.8 cambió antes del cierre | ✓ VERIFIED | All 5 `{N}-VALIDATION.md` exist and each declares `audited_commit_sha: 37a83fe693a303a551f4374f48fe6fc5521804f7` / `audit_baseline_head: 6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5` / `frozen_tree_verified: true` in frontmatter (grep-confirmed identical across all 5). Independently re-ran `git rev-parse v1.7^{commit}` → matches the declared SHA exactly. Independently re-ran `git diff --quiet v1.7^{commit} HEAD -- . ':(exclude).planning'` at verification time → **exit 0** (frozen-tree invariant holds right now, not just at audit time). |
| 2 | Cada criterio auditado lleva exactamente una de las 3 disposiciones con evidencia nombrada, y el conteo cierra contra el total enumerado — cero filas sin disponer | ✓ VERIFIED | Independently extracted every `### Disposición por fila` table (bounded between the header and the `*Disposiciones:` legend line, exactly as the contract specifies) and counted disposition tokens per row with `awk`+`grep`, not trusting the artifacts' own Metric blocks. Result: 35→13 (12 VN/1 VH/0 NVR), 36→11 (11/0/0), 37→14 (14/0/0), 38→9 (7/2/0), 39→15 (10/1/4). **Sum = 62 rows, exactly matching row count in every file** (proves zero undisposed + zero double-disposed, per-file, not just in aggregate). Total split: 54 VERIFIED-NOW / 4 VERIFIED-HISTORICALLY / 4 NOT-VERIFIABLE-RETROACTIVELY = 62 — matches the claimed 54/4/4 split exactly. Anti-vacuity re-checked independently: zero rows contain `deselected` without `passed` across all 5 files. Spot-re-executed 5 of the cited commands directly (two R-02 corrected selectors, one R-04 redacted command, the market-data deep-chain lock, the matriz skip-line-shape lock) — all ran green with the exact pass counts claimed. |
| 3 | Ningún `nyquist_compliant` pasa a `true` por flip mecánico; toda fase con ítems NOT-VERIFIABLE-RETROACTIVELY lo declara en su propio front-matter | ✓ VERIFIED | grep-confirmed `nyquist_compliant: false` in all 5 files (zero `true`). `not_verifiable_retroactively` key present in all 5: `0` in 35/36/37/38, `4` in 39 — matching the independently-recomputed NVR count for Phase 39 exactly. Phase 39's front-matter is the only one carrying a nonzero value, and it is declared in-file (not just in prose or in the cross-phase rollup). |
| 4 | Todo test/lock del auditor está enrolado en CI o declarado inerte por escrito con ruteo a Phase 45; un lock que no corre no cuenta como cobertura | ✓ VERIFIED | `git status --porcelain verification/` → empty (zero new files written). `ls verification/test_*.py \| wc -l` → 52 (matches the contract's pre-recorded baseline exactly — no drift). `git diff --quiet <baseline> HEAD -- .github/workflows/ci.yml` → exit 0 (CI file untouched). Allowlist independently counted at `ci.yml:81-92` → 12 entries (line numbers independently re-derived with `grep -n`, matching every cited line reference in the 5 artifacts and the contract). The formal inert declaration for the 40 unenrolled locks, with explicit Phase 45 routing, exists verbatim in `41-ROLLUP.md` § "Declaración inerte (criterio 4)". |
| 5 | Alcance acotado a las 5 fases nombradas; `NYQUIST-32-33` sigue en el backlog con texto intacto | ✓ VERIFIED | `git diff <baseline> HEAD -- .planning/REQUIREMENTS.md \| grep NYQUIST-32-33` → empty (byte-identical, that row untouched). Independently ran `git diff --stat <baseline> HEAD -- . ':(exclude).planning'` → **empty output, exit 0** — confirms zero files outside `.planning/` changed anywhere in the phase's commit range (not just "no product .py files" — literally nothing outside `.planning/`, including no `.yml`/`.toml`). Full `git diff --name-status` shows exactly the 5 target `VALIDATION.md` files + this phase's own artifacts + `REQUIREMENTS.md`/`ROADMAP.md`/`STATE.md` checkbox updates + one untracked research-cache JSON — no scope creep into Phases 18/25/29/30/32/33's own draft `VALIDATION.md` files. |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified)

### Independent Re-Derivation of Criterion 2 Arithmetic (not trusting the artifacts' own tables)

| Phase | Rows (independently counted) | VN | VH | NVR | Sum == Rows? |
|-------|-------------------------------|----|----|-----|--------------|
| 35 | 13 | 12 | 1 | 0 | ✅ |
| 36 | 11 | 11 | 0 | 0 | ✅ |
| 37 | 14 | 14 | 0 | 0 | ✅ |
| 38 | 9 | 7 | 2 | 0 | ✅ |
| 39 | 15 | 10 | 1 | 4 | ✅ |
| **Total** | **62** | **54** | **4** | **4** | **✅ (54+4+4=62)** |

Every row's disposition column was extracted directly from the raw markdown (not copied from any Metric block or narrative claim) and matches the ROLLUP's claimed 54/4/4 split exactly.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.../35-.../35-VALIDATION.md` | Audit section, transformed front-matter | ✓ VERIFIED | `status: validated`, `nyquist_compliant: false`, both SHAs present, `## Validation Audit 2026-08-31` appended after Sign-Off per contract §5.1 |
| `.../36-.../36-VALIDATION.md` | Audit section, transformed front-matter | ✓ VERIFIED | Same shape; 11/11/0/0 disposed |
| `.../37-.../37-VALIDATION.md` | Audit section, transformed front-matter | ✓ VERIFIED | Same shape; ordinal-key scheme correctly disambiguates non-unique Task IDs (`37-01-xx` ×3 etc.) |
| `.../38-.../38-VALIDATION.md` | Audit section, transformed front-matter | ✓ VERIFIED | Same shape; R-06 citations cross-checked against `38-VERIFICATION.md` `human_verification[0].confirmed: 2026-08-29T22:04:57Z` — timestamp independently confirmed present in that file |
| `.../39-.../39-VALIDATION.md` | Audit section, transformed front-matter, `not_verifiable_retroactively: 4` | ✓ VERIFIED | Only file with nonzero NVR count; declared correctly |
| `41-AUDIT-CONTRACT.md` | Shared disposition contract (R-01..R-09, denominator, CI map) | ✓ VERIFIED | 38.5KB, all 8 sections present, denominator arithmetic (13/11/14/9/15=62) matches independently-derived counts |
| `41-ROLLUP.md` | Cross-phase rollup, inert declaration, criterion 5 gates | ✓ VERIFIED | Explicitly non-authoritative index citing the 5 VALIDATION.md files as source of truth; inert declaration + Phase 45 routing present verbatim |
| `41-VALIDATION.md` (own, D-10 self-audit) | Phase 41 audits itself with the same bar | ✓ VERIFIED | 16-row self-disposition, `nyquist_compliant: false` (fails R-09 on its own 3 corrected commands), fully consistent with the rest of the phase's rigor |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `41-AUDIT-CONTRACT.md` disposition rules | 5 `{N}-VALIDATION.md` audit sections | Shared R-01..R-09 + front-matter template consumed by each Wave-2 plan | ✓ WIRED | All 5 files use identical front-matter shape, identical table legend, identical `## Validation Audit 2026-08-31` skeleton — confirms the contract was actually consumed, not independently re-invented per plan |
| Frozen-tree invariant (§1.2) | Every Wave-2/Wave-3 task's `<verify><automated>` | `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` re-run per task | ✓ WIRED | Re-verified at end-of-verification time independently — still exit 0 |
| `41-ROLLUP.md` criterion-4 inert declaration | Phase 45 (HARN-03/HARN-04) | Cross-phase precondition row in `REQUIREMENTS.md § Traceability` | ✓ WIRED | Confirmed present: `"Locks generados por el auditor, pendientes de enrolar en CI — producida en Phase 41 (criterio 4), consumida por Phase 45 (criterio 5)"` |

### Behavioral Spot-Checks (independent re-execution, not copied from artifacts)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| R-02 correction `37-r11` substitute test actually passes | `uv run pytest packages/matriz-client/tests/test_null_object.py -k "rest_parsed_snapshot or ws_frame_parsed_snapshot" -x -q` | `2 passed, 72 deselected in 0.01s` | ✓ PASS |
| R-02 correction `39-r03` substitute test actually passes | `uv run pytest -q verification/test_main_matriz_skip_line_shape.py` | `19 passed in 0.07s` | ✓ PASS |
| R-04 redacted-command `36-r11` substitute lock actually passes | `uv run pytest verification/test_main_market_data_deep_chain.py -q` | `6 passed in 0.09s` | ✓ PASS |
| Frozen-tree invariant holds *now*, not just at audit time | `git diff --quiet v1.7^{commit} HEAD -- . ':(exclude).planning'` | exit 0 | ✓ PASS |
| Zero non-`.planning` files changed in the entire phase commit range | `git diff --stat <baseline> HEAD -- . ':(exclude).planning'` | empty output | ✓ PASS |
| `verification/` tree unchanged (52 files, allowlist 12) | `ls verification/test_*.py \| wc -l` / `.github/workflows/ci.yml` allowlist count | 52 / 12 | ✓ PASS |
| `ci.yml` byte-unchanged since baseline | `git diff --quiet <baseline> HEAD -- .github/workflows/ci.yml` | exit 0 | ✓ PASS |
| `NYQUIST-32-33` row byte-identical | `git diff <baseline> HEAD -- .planning/REQUIREMENTS.md \| grep NYQUIST-32-33` | empty | ✓ PASS |
| Pre-existing unrelated matriz test failure (disclosed by requester) | `uv run pytest -q verification/test_main_matriz_login_fail_uniformity.py` | `2 failed, 2 errors` — `TypeError: probe_login_sync() missing 1 required positional argument: 'client'` | ✓ CONFIRMED pre-existing, not a Phase 41 regression (file byte-unchanged in this phase's diff; traces to Phase 11) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| NYQ-01 | All 7 plans (41-01..41-07) | Correr `/gsd-validate-phase` retroactivo sobre las 5 fases de v1.7 con disposición de 3 vías, sin flip mecánico | ✓ SATISFIED | `REQUIREMENTS.md` line 17 checkbox `[x]`, traceability table line 59 `NYQ-01 \| Phase 41 \| Complete` — both independently confirmed present, and the underlying disposition work independently re-verified above. No orphaned requirements: `grep "Phase 41" REQUIREMENTS.md` returns only NYQ-01 and its two traceability rows. |

### Anti-Patterns Found

| File | Line(s) | Pattern | Severity | Impact |
|------|---------|---------|----------|--------|
| `37-VALIDATION.md` | 49–62 (Task ID / Plan columns) | Literal `TBD` in 14 rows of the **pre-existing, untouched** `## Per-Task Verification Map` table | ℹ️ Info | **Not a Phase 41 defect.** Confirmed via `git show <baseline>:<file> \| grep -c "| TBD |"` → 14 before and 14 after Phase 41 touched the file — byte-identical, unchanged by this phase. The audit contract's R-03/R-04 explicitly forbid rewriting historical `Task ID`/`Plan` cells ("no se toca... su contradicción con la realidad medida es el hallazgo"), and the audit section explicitly names the related defect (non-unique Task IDs) as its own finding #1. The disposition work covering these 14 rows was fully completed (all 14 disposed VERIFIED-NOW); the stale `TBD` is inert historical metadata in an adjacent column, not evidence of incomplete verification. |
| `39-VALIDATION.md` | 47–56 (Task ID / Plan columns) | Same `TBD` pattern, 11 rows | ℹ️ Info | Same rationale — `git show` confirms 11 before/11 after, unchanged by this phase. All 11 corresponding map rows fully disposed. |
| `verification/test_main_matriz_login_fail_uniformity.py` | n/a | Pre-existing test failure (`TypeError`, missing positional arg) | ℹ️ Info (disclosed, out of scope) | Confirmed unrelated: file untouched in this phase's diff (`git diff --stat` empty for `verification/`), traces to Phase 11, is one of the 40 not-CI-enrolled locks named by the phase's own inert declaration. Fixing it here would violate the frozen-tree invariant (criterion 1). Correctly left alone. |

No blocker-level anti-patterns found. No secrets/credentials leaked in the diff (independently grepped for `://`, `@host`, `token`, `password`, `Bearer` across the full phase diff — the handful of hits are all literal pytest identifiers like `test_venue_token_resolves_by_exact_hostname`, not credential values).

### CLAUDE.md Compliance Check

Independently confirmed this phase touches **zero** `.py` files anywhere in the repository (`git diff --stat <baseline> HEAD -- . ':(exclude).planning'` is empty). The dual sync/async mirroring rule, the Python/mypy/ruff tech-stack constraints, and the per-package `.env` handling rules are therefore genuinely not applicable — this was verified, not assumed, by checking the actual diff rather than trusting the phase's docs-only self-description. The one project constraint that *does* apply — "nunca commitear `.env` ni exponer credenciales en logs, reportes o tests" — was independently checked via the credential-pattern grep above and found clean.

### Human Verification Required

None. Every ROADMAP success criterion was mechanically verifiable via direct command re-execution (`git diff`, `git rev-parse`, `grep`, `awk`, `pytest`), and this verifier re-ran the load-bearing commands independently rather than trusting the artifacts' self-reported results. No behavior-dependent (state-transition/cancellation/cleanup) truths are present in this phase — it is a pure documentation/audit phase with no runtime state machine to exercise.

### Gaps Summary

No gaps. All 5 ROADMAP success criteria for Phase 41 are independently verified against the actual codebase state, not against SUMMARY.md or the artifacts' own narrative claims. The phase's own rigor is unusually high for a retroactive audit: every disposition traces to a re-executed command, every correction (R-02/R-03/R-04) is transparently disclosed with before/after evidence, arithmetic is derived rather than declared, and the phase explicitly refuses to launder its own bookkeeping defects (e.g., Phase 41's own self-audit correctly stays `nyquist_compliant: false` because 3 of its own 16 rows needed command corrections). Independent re-derivation of every load-bearing number (row counts, disposition splits, line numbers in `ci.yml`, SHA values) matches the claimed values exactly with no discrepancies found.

---

_Verified: 2026-08-31_
_Verifier: Claude (gsd-verifier)_
