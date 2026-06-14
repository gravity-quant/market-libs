---
spike: 005
sub: 001d
name: matriz-deny-list-config
type: standard
validates: "Given the matriz codegen deny-list (_token_store.py, _refresh_policy.py, ws_client.py), when a per-file Rule(fromdir=aio.py-only) configuration is simulated AND sha256 of deny-listed files is computed before+after, then deny-listed files are byte-identical (zero mutation)"
verdict: PASS
related: [001c]
tags: [codegen, matriz, deny-list, sha256]
created: 2026-06-14
---

# Spike 005 / Sub-experiment 001d: Matriz Deny-list Config

## What This Validates

**Given** the matriz codegen deny-list locked in ARCHITECTURE.md (D-SCOPE-02): `_token_store.py`, `_refresh_policy.py`, `ws_client.py` (and adapter `_refresh.py` if present).

**When** a per-file `unasync.Rule(fromdir=<work>/, todir=<work>/)` is simulated with `fpath_list` scoped to ONLY `aio.py`, AND `sha256` is computed for every deny-listed file before the unasync run AND after.

**Then** the deny-listed files are byte-identical (sha256 equal pre/post — zero mutation), confirming that scoping `fpath_list` to `aio.py` alone is sufficient to honor the deny-list (no Rule-level exclusion needed beyond the file list).

## How to Run

```bash
cd /Users/sebadlf/development/becerra/market-libs
uv run --with unasync python .planning/spikes/SPIKE-005-codegen-tool-choice/001d-matriz-deny-list-config/experiment.py
```

The experiment runs in a sandbox (`WORK/matriz_copy/`) — production `packages/matriz-client/src/` is never mutated.

## What to Expect

`verification_transcripts.txt` contains a sha256 stanza per deny-listed file showing identical hashes pre/post. FINDING.md verdict PASS if all sha256 hashes match.

## Investigation Trail

**Run (2026-06-14):** Single pass — `shutil.copytree` copies all 17 matriz
files to a sandbox; sha256 computed for `aio.py` + 4 deny-listed files;
`unasync.unasync_files(fpath_list=[<aio.py>], rules=[...])` invoked with the
matriz Rule draft from 001c/FINDING.md; sha256 recomputed; sandbox cleaned up.

**All 4 deny-listed files byte-identical pre/post** (intactness = PASS each).
**`aio.py` transformed pre/post** (sha256 changed: `03e5ea1c…` → `7275e33a…`).
Verdict PASS. The unasync `fpath_list` scope mechanism is sufficient to honor
the deny-list — no `exclude=` param needed (and unasync 0.6.0 doesn't expose
one).

See `FINDING.md` for the full Deny-List Scope + Sha256 Transcript + How the
Deny-List Is Achieved in unasync 0.6.0 + Anti-Pitfall 6 Compliance +
Recommended Phase 16 Implementation sections.
