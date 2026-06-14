---
spike: 005
sub: 001d
name: matriz-deny-list-config
type: standard
validates: "Given the matriz codegen deny-list (_token_store.py, _refresh_policy.py, ws_client.py), when a per-file Rule(fromdir=aio.py-only) configuration is simulated AND sha256 of deny-listed files is computed before+after, then deny-listed files are byte-identical (zero mutation)"
verdict: TBD
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

<!-- Filled in Plan 02 -->
