# Phase 15 — Final Cross-Driver Stability Gate

**Scope:** Closes Criterion #2 (finding-title / probe-name stability across all 4
driver migrations) and Criterion #4 (≥907-test baseline preserved). Authored in
Wave 4 (Plan 15-04), the last wave of the driver-migration phase.

**Baseline anchor:** `71bf201` — `test(11-03): live re-run × 3 packages — Task 2
sequential live runs` (reachable in this repo). This is the pre-Phase-15
committed-findings snapshot.

---

## Criterion #2 — STATIC title/fid/probe-name diff (D-06 / D-07)

### Method

This is a **STATIC git-diff check** over the four committed findings files. It does
**NOT** re-run any live probe. Per D-07, the `actual=` / `diff=` bytes of OPEN
findings are non-deterministic live data and are explicitly **OUT of scope** here —
live re-verification is deferred to Phase 17 (LIVE-03).

The gate is scoped to the **finding-identity lines**:
- the `### F-NN -- <title>` detail headers (parsed by `_DETAIL_HEADER_RE` at
  `verification/findings.py:192`),
- the `| F-NN | ... |` classification-table id rows,
- probe-name literals inside the BEGIN/END auto-generated zones.

Command run:

```bash
git diff 71bf201..HEAD -- \
  .planning/verification/ambito-financiero-client-findings.md \
  .planning/verification/iol-client-findings.md \
  .planning/verification/higyrus-client-findings.md \
  .planning/verification/matriz-client-findings.md
```

### Result — PASS (zero title/fid/probe-name drift)

**ZERO `### F-NN -- <title>` detail-header lines changed** across all four findings
files:

```
git diff 71bf201..HEAD -- .../*-findings.md | grep -E '^[-+]### F-[0-9]'
  → (no matches) — ZERO title-header lines changed
```

Diff stat: only `iol-client-findings.md` differs vs baseline
(`19 insertions(+), 3 deletions(-)`). The other three findings files
(ambito, higyrus, matriz) are byte-identical to baseline.

The non-empty `iol-client-findings.md` delta consists exclusively of items that are
**out of scope** for this gate:

| Changed line | Kind | Disposition |
|--------------|------|-------------|
| `- Timestamp: 2026-06-14T05:11:31… → 10:56:00…` | Run-Context ART timestamp | Non-deterministic live data — OUT of scope (D-07) |
| `\| F-02 \| AUTH \| sync \| OPEN \| → FIXED` | Finding **Status** disposition | **Changed-classification** finding — OUT of scope (D-06 scopes the gate to *unchanged-classification* findings) |
| `**Status:** \`OPEN\` → \`FIXED\`` (detail body) | Status disposition mirror | Same changed-classification finding |
| `+ **Classification:** / **Rationale:** / **Resolution:** …` | Operator-disposition annotation block | Not a title/fid/probe-name line |

**Provenance check:** the iol F-02 status change was committed in `4d2d23e`
("ci(phase-11): close v1.1 milestone — LIVE-01 + CI green final + iol F-02 inline
fix"), i.e. a **Phase 11** operator disposition. It is **not** produced by any
Phase 15 wave. The `fid=F-02` identifier and its title
(`### F-02 -- _token_expires_at no se renovó tras refresh path`) are **byte-identical**
across the diff — only the Status disposition moved OPEN→FIXED.

**Conclusion:** No Phase 15 driver migration (Wave 1 ámbito, Wave 2 iol, Wave 3
higyrus, Wave 4 matriz) altered any finding title, `F-NN` id, or probe-name literal.
The migrations changed only **how** each client is acquired (module-singleton
`_get_default()` / `_base_url` → threaded `Client()` / `AsyncClient()` instance),
never the `append_finding(...)` literals (D-06). **Criterion #2 CLOSED.**

---

## Criterion #4 — ≥907-test baseline attestation (D-08)

### Method

Attested via a **COLLECTION count** (`pytest --collect-only`), which does NOT run
live financial APIs (avoids the live-API hang documented in the wave runbook).

```bash
uv run --frozen --all-packages pytest --collect-only -q 2>/dev/null | tail -1
```

### Result — PASS

```
988/989 tests collected (1 deselected) in 0.36s
```

**988 tests collected** — comfortably ≥ the 907 milestone baseline. The four new
per-driver AST-guard tests
(`test_main_{ambito_financiero,iol,higyrus,matriz}_uses_single_client_instance`) are
additive on top of the prior baseline; the matriz guard is confirmed present in the
collected set. **Criterion #4 CLOSED.**

Cross-reference: `.planning/phases/15-driver-migration-4-refac-05/15-LOC-ATTESTATION.md`
(Plan 01 LOC/test attestation).

---

## Out of scope (recorded, not run here)

- **Live re-verification** of OPEN findings' `actual=`/`diff=` bytes → Phase 17
  (LIVE-03). Those bytes are non-deterministic live data (market hours, available
  data, rate limits) and are not part of the static stability gate.
- **Per-package LIVE smoke (D-11, matriz):** operator-driven, requires matriz
  credentials. The matriz `.env` is absent in this execution environment, so the
  live smoke is **operator-deferred** (not a plan failure). See 15-04-SUMMARY.md.

---

## Summary

| Criterion | Check | Result |
|-----------|-------|--------|
| #2 | STATIC title/fid/probe-name diff vs `71bf201` (4 findings files) | **PASS — zero drift** |
| #4 | ≥907-test baseline (collection count) | **PASS — 988 collected** |
