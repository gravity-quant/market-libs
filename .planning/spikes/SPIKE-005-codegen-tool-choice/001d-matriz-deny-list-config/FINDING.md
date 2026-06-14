# FINDING: Matriz Deny-List Intactness

**Verdict:** PASS

All 4 deny-listed files (`_token_store.py`, `_refresh_policy.py`, `_refresh.py`,
`ws_client.py`) are sha256-byte-identical pre/post a simulated unasync codegen
run with `fpath_list=[aio.py]`. The target file `aio.py` is sha256-different
pre/post (transformed). Conclusion: scoping `fpath_list` to ONLY `aio.py` is
sufficient to honor the deny-list — no `exclude=` param or directory-level
filter is required (and unasync 0.6.0 doesn't expose one).

## Deny-List Scope

| File | Role | LOC | Why deny-listed |
|------|------|-----|-----------------|
| `_token_store.py` | 3-way TokenStore (sync REST + async REST + ws daemon) | 176 | Owns `threading.Lock` + `asyncio.Lock` cross-loop primitive — cannot be mechanically rewritten by token replacement. Architectural invariant locked in ARCHITECTURE.md (Phase 10 spike research). |
| `_refresh_policy.py` | retry + backoff + fail-cache | 125 | Pure sync (operates inside `asyncio.to_thread`). Async path delegates via TokenStore. No async/await tokens to strip. |
| `_refresh.py` | MatrizRefresh adapter | (small) | Sync `httpx.Client`-based refresh adapter. Async path delegates. |
| `ws_client.py` | WebSocket daemon thread | 359 | Uses `websocket-client` library; daemon-thread event loop; no `asyncio` primitives in module body. Always sync from Python's perspective. |

These 4 files are LOCKED per ARCHITECTURE.md research; the spike CONFIRMS, does
NOT renegotiate (Anti-Pitfall: modifying the deny-list).

## Sha256 Transcript

```
_token_store.py:
  pre:  3df15ef2a6c53c14ef1aba1ca596cca486bfa03b894cdbf9dc35be5d1a5f3696
  post: 3df15ef2a6c53c14ef1aba1ca596cca486bfa03b894cdbf9dc35be5d1a5f3696
  intact: PASS

_refresh_policy.py:
  pre:  b7eb342367fcfda21da7daa4285a3db06bfe51706901fcd886e9245e29d542a2
  post: b7eb342367fcfda21da7daa4285a3db06bfe51706901fcd886e9245e29d542a2
  intact: PASS

_refresh.py:
  pre:  80403c3a8f65448eb850bd66150a76b334635969fd51ff70019365042a7f442f
  post: 80403c3a8f65448eb850bd66150a76b334635969fd51ff70019365042a7f442f
  intact: PASS

ws_client.py:
  pre:  c1338ba99257719add83437c5a9515865f511cced6e9913406515d59269c6d9f
  post: c1338ba99257719add83437c5a9515865f511cced6e9913406515d59269c6d9f
  intact: PASS

aio.py:
  pre:  03e5ea1cf1fcc3ef3f49f94329ee308abf01db867ad65098519daa9a5520ca5b
  post: 7275e33aff7112d2dd2395290cfb0421f35636d91e5fd265a8e4bc90c56bf896
  transformed: PASS  (post MUST differ from pre)
```

Captured in `verification_transcripts.txt` (committed); also persisted as
`sha256_before.txt` + `sha256_after.txt` (single-line per file, terse format
useful for diff-based merge gates).

## How the Deny-List Is Achieved in unasync 0.6.0

The unasync 0.6.0 API:

```python
unasync.unasync_files(
    fpath_list=[...],   # explicit list of files to transform
    rules=[
        unasync.Rule(fromdir=..., todir=..., additional_replacements={...}),
    ],
)
```

There is **no `exclude=` parameter** in either `unasync_files` or `Rule`. The
deny-list is achieved **by NOT listing the deny-listed files in `fpath_list`**:

```python
# Phase 16 codegen invocation (per-package, recommended pattern):
unasync.unasync_files(
    fpath_list=[str(MATRIZ_DIR / "aio.py")],  # <- ONLY aio.py
    rules=[unasync.Rule(
        fromdir=str(MATRIZ_DIR) + "/",
        todir=str(MATRIZ_DIR) + "/",
        additional_replacements=MATRIZ_REPLACEMENTS,
    )],
)
# _token_store.py, _refresh_policy.py, _refresh.py, ws_client.py are NEVER
# passed to unasync_files — therefore they cannot be mutated.
```

This is the **stronger guarantee**: the deny-listed files don't appear in any
arg passed to the tool, so they cannot be transformed even by an
incorrectly-configured Rule. The sha256 verification in this experiment confirms
this empirically: 4 files × 64 hex digits × byte-identical pre/post.

## Anti-Pitfall 6 Compliance

The spike never opens the deny-listed files for write:

1. `shutil.copytree` — read-only against `packages/matriz-client/src/matriz_client`;
   creates a sandbox under `001d-matriz-deny-list-config/matriz_copy/`.
2. `hashlib.sha256(path.read_bytes())` — read-only on the sandbox copies.
3. `unasync.unasync_files(fpath_list=[<sandbox>/aio.py])` — explicitly scoped to
   the sandbox aio.py only. The 4 deny-listed files are bytes on disk; the tool
   never touches them.
4. Post-run sha256 confirms zero change.

The sandbox (`matriz_copy/`) is cleaned up at script end (deterministic artifact
policy — same as 001a Step 6b `__pycache__` cleanup); only the sha256
transcripts and the experiment script itself are committed.

`git status --porcelain packages/` returns 0 — production matriz code is never
written to.

## Recommended Phase 16 Implementation

```python
# scripts/codegen.py (Phase 16)
from __future__ import annotations

import unasync
from pathlib import Path

PACKAGES = ["ambito-financiero-client", "iol-client", "higyrus-client", "matriz-client"]
ROOT = Path(__file__).resolve().parents[1]

PER_PKG_RULES: dict[str, dict[str, str]] = {
    "ambito-financiero-client": {
        "AsyncClient": "Client",
        "AsyncRetryTransport": "RetryTransport",
        "_atransport": "_transport",
        "AmbitoFinancieroAsyncClient": "AmbitoFinancieroClient",
        "_default_async_client": "_default_client",
        "aclose": "close",
    },
    "iol-client": {...},     # filled per Phase 16 Rule finalization
    "higyrus-client": {...},
    "matriz-client": {
        "AsyncClient": "Client",
        "AsyncRetryTransport": "RetryTransport",
        "_atransport": "_transport",
        "aclose": "close",
        "_aensure_token": "_ensure_token",
    },
}

for pkg in PACKAGES:
    pkg_short = pkg.removesuffix("-client").replace("-", "_") + "_client"
    pkg_dir = ROOT / "packages" / pkg / "src" / pkg_short
    aio_path = pkg_dir / "aio.py"
    if not aio_path.exists():
        # wallets-client has no aio yet; skip
        continue
    unasync.unasync_files(
        fpath_list=[str(aio_path)],  # <- DENY-LIST enforced by file scope
        rules=[unasync.Rule(
            fromdir=str(pkg_dir) + "/",
            todir=str(pkg_dir) + "/",
            additional_replacements=PER_PKG_RULES[pkg],
        )],
    )
    # Post-process: ruff format + rename aio.py → client.py if Rule writes in place,
    # or use distinct fromdir/todir if separate _aio/_sync layout per Phase 16 design.
```

**Make target** (pre-commit + CI gate):

```makefile
codegen:
	uv run --with unasync python scripts/codegen.py
	uv run ruff format packages/*/src/*/client.py

codegen-check:
	uv run --with unasync python scripts/codegen.py --check
	# fails CI if the in-repo client.py differs from a fresh codegen run
```

**Pre-commit hook** (recommended Phase 16 hook, complements the marker hook from
001b):

```yaml
- id: codegen-clean
  name: codegen-clean
  entry: uv run --with unasync python scripts/codegen.py --check
  language: system
  files: \.py$
  pass_filenames: false
```

This guarantees that whenever a developer edits aio.py, codegen runs and the
diff is captured BEFORE the commit is created.

## D-SCOPE-02 Linkage

001c established that matriz `aio.py` has zero bare `asyncio.<attr>` references
in code body (the audit's classifier emitted 109 rows with 0 unresolved). 001d
establishes that the deny-list of 4 files is byte-intact under a simulated
codegen run. Together, these prove:

- The matriz codegen scope (aio.py-only) is structurally compatible with the
  unasync token-replacement model.
- The deny-listed files cannot be mutated by an incorrectly-configured Rule
  because they are not passed to the tool's `fpath_list`.
- Phase 16's matriz codegen target is well-defined and risk-bounded.

## Slopcheck

No new install — reuses transient `uv run --with unasync` environment from Plan
01. unasync 0.6.0 legitimacy verified at Plan 01 start; recorded in
`001a/FINDING.md`.

## Linkage

- `experiment.py` — read-only sandbox + sha256 verification.
- `verification_transcripts.txt` — per-file sha256 pre/post + intact verdict.
- `sha256_before.txt` / `sha256_after.txt` — single-line-per-file machine-readable
  hashes (useful for `diff` based merge gates).
- `001c/FINDING.md` — matriz Rule Config Draft (consumed here as
  `MATRIZ_REPLACEMENTS`).
- ARCHITECTURE.md — locks the 4-file deny-list (this experiment CONFIRMS, never
  renegotiates).
