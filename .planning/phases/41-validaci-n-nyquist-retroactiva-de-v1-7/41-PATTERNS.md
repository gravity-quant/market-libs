# Phase 41: Validación Nyquist retroactiva de v1.7 - Pattern Map

**Mapped:** 2026-08-31
**Files analyzed:** 7 (5 in-place edits + 1 seeded artifact + 1 optional rollup)
**Analogs found:** 7 / 7

> **Phase character:** this phase writes **zero Python and zero product source**. Every deliverable is
> a markdown artifact under `.planning/`. "Role" and "data flow" below are therefore mapped onto the
> documentation-artifact tier, not the client-library tier. No `client.py`/`aio.py`/`models.py`
> analog is relevant — CLAUDE.md's dual sync/async mirroring rule does not apply (RESEARCH.md
> § Project Constraints confirms this row as **NO**).

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.planning/milestones/v1.7-phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-VALIDATION.md` | validation artifact (edit in place) | append-section + front-matter transform | `.planning/milestones/v1.1-phases/09-deferred-bug-fixes/09-VALIDATION.md` (§ Validation Audit) | exact |
| `.planning/milestones/v1.7-phases/36-market-data-client-market-data-tipado-revocaci-n-de-la-fase-/36-VALIDATION.md` | validation artifact (edit in place) | append-section + front-matter transform | same | exact |
| `.planning/milestones/v1.7-phases/37-matriz-client-dicts-residuales-tipados-alias/37-VALIDATION.md` | validation artifact (edit in place) | append-section + front-matter transform | same | exact |
| `.planning/milestones/v1.7-phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-VALIDATION.md` | validation artifact (edit in place) | append-section + front-matter transform | same | exact |
| `.planning/milestones/v1.7-phases/39-verificaci-n-en-vivo-del-encadenamiento-profundo/39-VALIDATION.md` | validation artifact (edit in place) | append-section + front-matter transform | same | exact |
| `.planning/phases/41-.../41-VALIDATION.md` | validation artifact (seeded, then self-audited) | same, applied to this phase (D-10) | same | exact |
| `.planning/phases/41-.../41-ROLLUP.md` **(OPTIONAL, D-01)** | secondary read index | aggregate/transform (read-only over the 5) | `.planning/milestones/v1.7-phases/39-.../39-CENSUS.md` | role-match |

**Structural note (measured):** all five target files share an identical section skeleton —
`## Test Infrastructure` → `## Sampling Rate` → `## Per-Task Verification Map` → `## Wave 0
Requirements` → `## Manual-Only Verifications` → `## Validation Sign-Off`. The audit section is
**appended after `## Validation Sign-Off`**, matching `01-VALIDATION.md:106` and
`09-VALIDATION.md:327`. In `06-VALIDATION.md:118` it sits *before* sign-off; prefer the 01/09
placement (append at end) — it is the majority precedent and avoids reflowing the sign-off block.

---

## Pattern Assignments

### The five `{N}-VALIDATION.md` files (35–39)

**Primary analog:** `.planning/milestones/v1.1-phases/09-deferred-bug-fixes/09-VALIDATION.md`
**Secondary analog (richer, multi-table):** `.planning/milestones/v1.1-phases/06-compat-safety-net-client-class-skeleton/06-VALIDATION.md`
**Tertiary analog (`partial` semantics):** `.planning/milestones/v1.1-phases/07-core-py-extraction-sync-async-logic-dedup/07-VALIDATION.md`

#### 1. Audit-section opener + metric block — copy from `09-VALIDATION.md:327-338`

```markdown
## Validation Audit 2026-06-13

Retroactive Nyquist audit run via `/gsd-validate-phase 9`. Input state A
(VALIDATION.md existed pre-audit). No subagent required (zero gaps).

| Metric | Count |
|--------|-------|
| Requirements audited | 4 (BUG-01..04) |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated to manual-only | 0 |
| Test files re-verified on disk | 5 |
| Targeted regression suite | 26 passed in 0.09s |
```

**What to keep:** the two-sentence provenance line (mechanism + input state + "no subagent"), and the
last two metric rows — they are *re-execution evidence*, not checkbox flips. This is exactly the
D-04/D-10 bar.
**What to change per phase 41:** date becomes `2026-08-31`; add rows `Rows disposed`,
`VERIFIED-NOW`, `VERIFIED-HISTORICALLY`, `NOT-VERIFIABLE-RETROACTIVELY`, `New lock files written` (0
per D-08), `NOT ENFORCED rows` (per D-07). The counts must sum to the phase's row total (13/11/14/9/15
→ 62).

#### 2. Per-row disposition table — the new 4-column table (D-07)

No in-repo table has all four columns yet. Nearest shape is `09-VALIDATION.md:340-347` (3-column
coverage cross-check) — extend it. Header locked by RESEARCH.md Pattern 2:

```markdown
| Row | Disposition | Evidence (this session) | CI enforcement surface |
|-----|-------------|-------------------------|------------------------|
```

Evidence-cell house style, from the existing analog (`09-VALIDATION.md:343`): backticked full test
node id or command, then the result. For Phase 41 the result **must** carry a non-zero `passed`
count (Pitfall 2). Enforcement cells use `job <name>, ci.yml:<lines>` or the literal `NOT ENFORCED`.

#### 3. Multi-table audit body — copy the sectioning from `06-VALIDATION.md:118-166`

```markdown
## Validation Audit — 2026-06-11

**Auditor:** Nyquist adversarial auditor
**Phase state at audit time:** Merged to main (commit `fd7ab43`), ... Full suite 389 passed, 1 skipped, 1 deselected.

### Audit Findings
[criterion/coverage table]

### Secondary Gaps Found
[Task ID | Gap | Impact]

### Gaps Resolved
[Test | Gap Covered | Result]

### Escalations

None. All phase requirements have automated verification. No implementation bugs found.
```

**Copy:** the bolded `**Auditor:**` / `**Phase state at audit time:**` header pair — this is where
D-02's dual SHA declaration goes (`v1.7` commit `37a83fe693a303a551f4374f48fe6fc5521804f7` + audit
HEAD + the empty-`git diff` proof). Copy the `### Escalations` closing section verbatim in shape.
**Diverge:** `### Secondary Gaps Found` / `### Gaps Resolved` become `### Command corrections`
(Pattern 3, exactly two rows: `37-04b`, `39-01-03`) — because D-06(a) forbids writing tests, no gap
may be "resolved" by new code.

#### 4. Prose paragraph justifying the manual-only rows — copy from `09-VALIDATION.md:349-355`

```markdown
Manual-only verifications (BUG-02 live triage, BUG-04 live iteration,
BUG-01 cycle_closure flip) remain as documented in §Manual-Only
Verifications — each backed by a regression test that guards the
client-side contract, so the manual gates are scoped to live API
behavior that mocked tests cannot reproduce.

Audit verdict: **Phase 9 remains Nyquist-compliant.** No new test files
generated; no escalations.
```

**Directly applicable to:** Phase 38 (1 manual row) and Phase 39 (4 manual rows).
**Verdict-line divergence (D-09):** never `remains Nyquist-compliant`. Use the PARTIAL wording:
`Audit verdict: **Phase {N} is PARTIAL** — status draft → validated, nyquist_compliant remains
false ({k} rows NOT-VERIFIABLE-RETROACTIVELY / manual). No new test files generated; no escalations.`
Keep the `No new test files generated` clause verbatim — it is the D-08 zero-count assertion.

#### 5. Front-matter transform — the target state

Current state, all five (`35-VALIDATION.md:1-10`, identical in 36/37/38; 39 lacks the two comments):

```yaml
---
phase: 35
slug: fundaci-n-null-object-bool-pol-tica-del-walker
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-28
---
```

Target state — edit `status` only, add `updated` + `last_audited`. The key precedent for the extra
keys is `09-VALIDATION.md:1-13`:

```yaml
status: approved
nyquist_compliant: true
...
created: 2026-06-13
updated: 2026-06-13
approved_by: operator
approved_on: 2026-06-13
last_audited: 2026-06-13
```

**Copy:** `updated:` and `last_audited:` keys (both `2026-08-31`).
**Do NOT copy:** `nyquist_compliant: true`, `approved_by`, `approved_on`. D-09 pins
`nyquist_compliant: false` on all five; there is no operator approval in `mode: yolo`.
**`partial` precedent (do not adopt as a value):** `07-VALIDATION.md:5` uses
`nyquist_compliant: partial` with a prose block explaining the split. That *string value* is a
one-off in this repo and D-09 explicitly names `false`, not `partial` — but `07-VALIDATION.md:14-20`
is the right **prose model** for explaining a PARTIAL outcome under the H1 title:

```markdown
> **`nyquist_compliant: partial`** — 4/5 Phase 7 ROADMAP success criteria PASS;
> success criterion #3 (LOC drop ≥30% per package) is partially met (2 of 4
> packages PASS, 2 documented deviations). Every other gate ... is green.
```

Mirror that shape as a one-paragraph note next to the audit verdict, phrased as
`nyquist_compliant stays false because …`.

#### 6. Sign-off checklist append — copy from `06-VALIDATION.md:170`

The existing sign-off blocks in 35–39 all end with an **unchecked** `- [ ] nyquist_compliant: true
set in frontmatter` and `**Approval:** pending`. `06-VALIDATION.md` shows the convention for adding a
dated audit line to that list rather than rewriting it:

```markdown
- [x] Audit 2026-06-11: all 22 tasks GREEN; 3 secondary gaps filled with new automated tests; no escalations
```

Phase 41 append (per file):
`- [x] Audit 2026-08-31: {n} rows disposed ({a} VERIFIED-NOW / {b} VERIFIED-HISTORICALLY / {c} NOT-VERIFIABLE-RETROACTIVELY); 0 new lock files; nyquist_compliant stays false`
Leave the pre-existing `- [ ] nyquist_compliant: true` box **unchecked** — checking it is precisely
the Pitfall-1 / criterion-3 violation.

---

### `35-VALIDATION.md` — additional pattern (D-05 map rebuild)

Phase 35 is the only file whose `## Per-Task Verification Map` must be **rewritten**, not just
appended to. Current content (`35-VALIDATION.md:41-43`):

```markdown
| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner) | — | — | NOBJ-01 / NOBJ-02 | — | N/A | unit | see plans | — | ⬜ pending |
```

**Row-shape analog to copy:** `38-VALIDATION.md:43-50` — the best-populated, most regular 10-column
map in the set:

```markdown
| 38-02-01 | 02 | 1 | NOBJ-IOL-01 | — | N/A | unit | `pytest packages/iol-client/tests/test_models.py -k puntas -q` | ✅ | ⬜ pending |
| 38-03-01 | 03 | 2 | NOBJ-IOL-01 | — | N/A | static | `uv run mypy packages/iol-client` | ✅ | ⬜ pending |
| 38-05-01 | 05 | 3 | NOBJ-AUD-01 | — | N/A | doc review | `checkpoint:human-verify` on `38-CENSUS.md` | ❌ manual | ⬜ pending |
```

Copy exactly: column order, the `—` / `N/A` filler convention, `Test Type` vocabulary
(`unit` / `static` / `snapshot` / `unit (RED fixture)` / `doc review`), backticked commands, the
`✅` / `❌ W0` / `❌ manual` File-Exists vocabulary, and the trailing legend line
`*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*`.
Task IDs for the 12 reconstructed rows follow `{plan}-{task}` → `35-01-01 … 35-05-02`, sourced from
`35-01..05-PLAN.md` `<task>`/`<verify><automated>` blocks (RESEARCH.md § Row Inventory table).

---

### `41-ROLLUP.md` (optional secondary index)

**Analog:** `.planning/milestones/v1.7-phases/39-.../39-CENSUS.md`

Copy its opening move: a bolded thesis paragraph naming *the way this document is most easily
misread*, then a `## Unidad y método` section pinning the counting unit before any arithmetic:

```markdown
**Esta corrida reporta menos divergencias que el piso ratificado, y ése es exactamente el
resultado que más fácil se lee mal.** ...

## Unidad y método

**La unidad de este censo es la 4-tupla distinta `(slug, model, field_path, kind)` ...**
```

For Phase 41 the unit paragraph pins **62 rows** (13+11+14+9+15) and explicitly rejects the two
wrong denominators: the 51 as-declared rows (pre-D-05) and the 25 v1.7 ROADMAP success criteria
(D-03). Document language is Spanish, matching every v1.7 artifact.

---

## Shared Patterns

### Section placement
**Source:** `01-VALIDATION.md:106`, `09-VALIDATION.md:327`
**Apply to:** all 5 files + `41-VALIDATION.md`
Append `## Validation Audit 2026-08-31` at end of file, preceded by `---`. (`06-VALIDATION.md:118`
inserts before sign-off — the minority pattern; do not follow.)

### Date-in-heading convention
**Source:** `01-VALIDATION.md:106` (`## Validation Audit 2026-05-27`), `09-VALIDATION.md:327`
**Apply to:** all 6 audit sections. Use the no-dash form (2 of 3 precedents); `06` uses
`## Validation Audit — 2026-06-11`.

### Evidence-cell style
**Source:** `09-VALIDATION.md:343-346`
**Apply to:** every `VERIFIED-NOW` cell
Backticked node id/command → outcome → parenthetical count. Trim transcripts to the summary line
(`N passed in Xs`) per CLAUDE.md's credential-exposure constraint (RESEARCH.md § Project Constraints).

### Metric-block-plus-table composition
**Source:** `09-VALIDATION.md:332-347` (block + table), `06-VALIDATION.md:124-166` (block + 3 tables)
**Apply to:** all 5 — RESEARCH.md § Alternatives explicitly requires *both* the stock metric block
and the per-row disposition table.

### Explicit "no escalations / no new tests" closing line
**Source:** `06-VALIDATION.md:166` (`### Escalations` / `None.`), `09-VALIDATION.md:356`
(`No new test files generated; no escalations.`)
**Apply to:** all 5 — this is the written form of D-08's expected zero lock count.

### Spanish-language body
**Source:** `01-VALIDATION.md:110-115` (audit prose in Spanish), all v1.7 artifacts
**Apply to:** the 5 v1.7 files and the rollup. The `09`/`06` precedents are English (v1.1 era);
copy their *structure*, write the prose in Spanish to match the surrounding v1.7 documents.

---

## No Analog Found

| File / Element | Role | Data Flow | Reason |
|----------------|------|-----------|--------|
| The 4th column, "CI enforcement surface" (D-07) | table column | transform | **No in-repo precedent.** No existing audit table names a `ci.yml` job+line per row. Build it from RESEARCH.md § CI Enforcement Map; the `NOT ENFORCED` vocabulary is new to this phase. |
| A `VERIFIED-NOW` / `VERIFIED-HISTORICALLY` / `NOT-VERIFIABLE-RETROACTIVELY` disposition vocabulary | table cell values | transform | Nearest kin is Phase 33's `COULD-NOT-DECIDE` and `39-CENSUS.md`'s per-cell provenance — same *spirit* (never clean by default, always named evidence), different token set. Define the three values in a legend line under the table, mirroring the `*Status: ⬜ pending · ✅ green …*` legend convention. |
| `40-VALIDATION.md` | — | — | **Explicitly NOT an analog.** RESEARCH.md § Anti-Patterns: its `nyquist_compliant: true` was set by plan-check, not validate-phase, and it carries no `## Validation Audit` section. Do not copy from it. |

---

## Metadata

**Analog search scope:** `.planning/milestones/*/*/`*`-VALIDATION.md` (30 files), `.planning/milestones/v1.7-phases/39-*/39-CENSUS.md`
**Files scanned:** 30 VALIDATION.md front-matters + 4 read in full-section detail (01, 06, 07, 09) + 5 targets (35–39)
**Audit-section precedents in repo:** 3 (`01`:2026-05-27, `06`:2026-06-11, `09`:2026-06-13)
**Pattern extraction date:** 2026-08-31
