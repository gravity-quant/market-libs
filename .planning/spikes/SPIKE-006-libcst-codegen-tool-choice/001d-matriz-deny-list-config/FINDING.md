# 001d — Matriz Deny-List Intactness Under libcst (D-RIGOR-02 item 10b)

**Verdict:** PASS — 4/4 deny-list files sha256-byte-identical pre/post; `aio.py` transformed.

## What This Proves

libcst has no `exclude=` / `fpath_list` parameter — the matriz 4-file deny-list is honored
by **SCOPE**: only `aio.py` is ever handed to `cst.parse_module`. The 4 deny-listed files
are never parsed, so the tool physically cannot mutate them. This is the libcst equivalent
of unasync's `fpath_list` scope (SPIKE-005 001d). D-09 CONFIRMED — not renegotiated.

The 4 locked files (ARCHITECTURE.md, Phase 10):

- `_token_store.py` — 3-way TokenStore (threading.Lock + asyncio.Lock + ws thread)
- `_refresh_policy.py` — retry + backoff + fail-cache; sync-only by design
- `_refresh.py` — MatrizRefresh adapter
- `ws_client.py` — WebSocket daemon thread

## Method (adapted from SPIKE-005 001d)

Same `shutil.copytree` → sha256_before → transform → sha256_after skeleton. The only
structural change: `unasync.unasync_files(fpath_list=[aio.py])` is dropped for a per-module
libcst transform of the sandbox `aio.py` only:

```python
module = cst.parse_module(work_aio.read_text())   # aio.py ONLY
work_aio.write_text(module.visit(AsyncToSync()).code)
```

Production source is read-only (Anti-Pitfall 2): the transform runs on a `shutil.copytree`
sandbox that is deleted at the end of the run. `git diff --exit-code packages/` is clean.

### Why not a "trivial round-trip"

The plan offered "the `AsyncToSync` pass OR a trivial round-trip." A trivial round-trip is
**lossless** (`cst.parse_module(s).code == s`), so it would leave `aio.py` byte-identical and
DEFEAT the "aio.py transformed" half of the gate (`pre["aio.py"] != post["aio.py"]`). A real
(if minimal) transform is required to prove SCOPE rather than a no-op. The minimal
`AsyncToSync` pass used here strips `async` from `FunctionDef` and unwraps `await` — enough
to guarantee `aio.py` changes while remaining a pure `CSTNode → CSTNode` transformer (no
cross-module state, no I/O — an item-9 purity preview).

## Result (2026-07-02)

| File | sha256 pre == post | Status |
|------|--------------------|--------|
| `_token_store.py` | equal | intact PASS |
| `_refresh_policy.py` | equal | intact PASS |
| `_refresh.py` | equal | intact PASS |
| `ws_client.py` | equal | intact PASS |
| `aio.py` | **differs** | transformed PASS |

```
aio.py            pre  7d4c57c7...bf20   post 39a7e603...aa03   (DIFFERS — transformed)
_token_store.py   pre  3df15ef2...3696   post 3df15ef2...3696   (identical)
_refresh_policy.py pre b7eb3423...42a2   post b7eb3423...42a2   (identical)
_refresh.py       pre  80403c3a...442f   post 80403c3a...442f   (identical)
ws_client.py      pre  c1338ba9...6d9f   post c1338ba9...6d9f   (identical)
```

See `sha256_before.txt` / `sha256_after.txt` for full digests.

## D-RIGOR-02 Item 10b

**PASS.** All 4 deny-list files byte-identical pre/post AND `aio.py` transformed. The
per-module libcst transform scope is sufficient to honor the deny-list, exactly as unasync's
`fpath_list` scope was in SPIKE-005. `uv.lock` unchanged after the ephemeral libcst run (D-05).

## Linkage

- sha256: `001d-matriz-deny-list-config/sha256_before.txt`, `.../sha256_after.txt`
- Evidence: `evidence-checklist.txt` §item 10b
- Prior art: `.planning/spikes/SPIKE-005-codegen-tool-choice/001d-matriz-deny-list-config/FINDING.md`
