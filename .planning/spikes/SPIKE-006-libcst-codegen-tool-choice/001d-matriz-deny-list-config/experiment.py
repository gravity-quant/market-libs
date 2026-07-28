"""Spike 001d (SPIKE-006): matriz deny-list intactness — sha256 before/after a
per-module libcst transform (D-RIGOR-02 item 10b).

Adapted from SPIKE-005 001d. The ONLY structural change: the codegen engine is swapped
from ``unasync.unasync_files(fpath_list=[aio.py])`` to a **per-module libcst transform**
of the sandbox ``aio.py`` ONLY. libcst has no ``fpath_list`` concept — the deny-list is
honored by SCOPE: the 4 deny-listed files are never handed to ``cst.parse_module`` at all,
so the tool physically cannot mutate them (the libcst equivalent of unasync's file-list
scope).

The 4 locked files (ARCHITECTURE.md, Phase 10; D-09 — CONFIRMED, not renegotiated):

- ``_token_store.py``   — 3-way TokenStore (threading.Lock + asyncio.Lock + ws thread)
- ``_refresh_policy.py``— retry + backoff + fail-cache; sync-only by design
- ``_refresh.py``       — MatrizRefresh adapter
- ``ws_client.py``      — WebSocket daemon thread

Method:

1. ``shutil.copytree`` the entire ``matriz_client/`` package to a sandbox (production
   source is read-only — never mutated; Anti-Pitfall 2).
2. sha256 of ``aio.py`` + the 4 deny-list files BEFORE.
3. ``cst.parse_module`` the sandbox ``aio.py`` ONLY, apply a minimal ``AsyncToSync`` pass
   (strip ``async`` on ``FunctionDef``; unwrap ``await``), write ``module.code`` back.
   NOTE: a *trivial round-trip* would be lossless (``cst.parse_module(s).code == s``) and
   leave ``aio.py`` byte-identical — which would defeat the "aio.py transformed" half of
   the gate. A real (if minimal) transform is required to prove SCOPE, not a no-op.
4. sha256 of the same 5 files AFTER.
5. PASS iff all 4 deny-list files are byte-identical pre/post AND ``aio.py`` differs.

Run from repo root (ephemeral libcst — D-05, never added to dev deps):

    uv run --with 'libcst>=1.8.0,<2' python \
      .planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001d-matriz-deny-list-config/experiment.py
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

import libcst as cst

# --- paths ----------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[4]
MATRIZ_DIR = REPO_ROOT / "packages/matriz-client/src/matriz_client"
SPIKE = Path(__file__).resolve().parent
WORK = SPIKE / "matriz_copy"
SHA_BEFORE = SPIKE / "sha256_before.txt"
SHA_AFTER = SPIKE / "sha256_after.txt"

DENY_LIST: list[str] = [
    "_token_store.py",
    "_refresh_policy.py",
    "_refresh.py",
    "ws_client.py",
]
TARGET = "aio.py"

# --- preflight ------------------------------------------------------------

if not MATRIZ_DIR.exists():
    sys.stderr.write(f"FATAL: matriz source dir missing: {MATRIZ_DIR}\n")
    raise SystemExit(2)

for name in [TARGET, *DENY_LIST]:
    if not (MATRIZ_DIR / name).exists():
        sys.stderr.write(f"FATAL: expected file missing: {MATRIZ_DIR / name}\n")
        raise SystemExit(2)


# --- minimal AsyncToSync transform (per-module; guarantees aio.py changes) ---


class AsyncToSync(cst.CSTTransformer):
    """Strip ``async`` from function defs and unwrap ``await`` — the smallest real
    transform sufficient to prove ``aio.py`` was rewritten. NOT the full Plan-02 suite.
    Pure ``CSTNode → CSTNode``: holds no cross-module state and performs no I/O."""

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if updated_node.asynchronous is not None:
            return updated_node.with_changes(asynchronous=None)
        return updated_node

    def leave_Await(
        self, original_node: cst.Await, updated_node: cst.Await
    ) -> cst.BaseExpression:
        return updated_node.expression


# --- step 1: sandbox setup ------------------------------------------------

shutil.rmtree(WORK, ignore_errors=True)
shutil.copytree(MATRIZ_DIR, WORK / "matriz_client")
print(f"[step 1] copytree -> {WORK / 'matriz_client'}")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- step 2: pre-run sha256 ----------------------------------------------

pre_hashes: dict[str, str] = {
    name: sha256_of(WORK / "matriz_client" / name) for name in [TARGET, *DENY_LIST]
}
SHA_BEFORE.write_text(
    "\n".join(f"{name}: {pre_hashes[name]}" for name in [TARGET, *DENY_LIST]) + "\n"
)
print(f"[step 2] pre-hashes written to {SHA_BEFORE}")

# --- step 3: per-module libcst transform of aio.py ONLY ------------------
# CRITICAL: only aio.py is parsed. The 4 deny-list files are never handed to libcst —
# the deny-list is enforced by SCOPE (file selection), not by an exclude= parameter.

work_aio = WORK / "matriz_client" / TARGET
print(f"[step 3] cst.parse_module({TARGET}) + AsyncToSync().visit() — aio.py ONLY")
module = cst.parse_module(work_aio.read_text())
transformed = module.visit(AsyncToSync())
work_aio.write_text(transformed.code)
print("[step 3] transform written back to sandbox aio.py")

# --- step 4: post-run sha256 ---------------------------------------------

post_hashes: dict[str, str] = {
    name: sha256_of(WORK / "matriz_client" / name) for name in [TARGET, *DENY_LIST]
}
SHA_AFTER.write_text(
    "\n".join(f"{name}: {post_hashes[name]}" for name in [TARGET, *DENY_LIST]) + "\n"
)
print(f"[step 4] post-hashes written to {SHA_AFTER}")

# --- step 5: verdict ------------------------------------------------------

intactness: dict[str, bool] = {n: pre_hashes[n] == post_hashes[n] for n in DENY_LIST}
aio_transformed = pre_hashes[TARGET] != post_hashes[TARGET]

# --- step 6: cleanup sandbox (deterministic artifact policy) -------------
# Spike artifacts are sha256_before.txt + sha256_after.txt only; the sandbox is fully
# regenerable from experiment.py.
shutil.rmtree(WORK, ignore_errors=True)

print()
print("=== Verdict ===")
for name in DENY_LIST:
    print(f"  {name}: intact={'PASS' if intactness[name] else 'FAIL'}")
print(f"  {TARGET}: transformed={'PASS' if aio_transformed else 'FAIL'}")

all_intact = all(intactness.values())
verdict_pass = all_intact and aio_transformed
print(f"SPIKE 001d VERDICT (item 10b): {'PASS' if verdict_pass else 'FAIL'}")
print(f"Sandbox cleaned up: {WORK}")

sys.exit(0 if verdict_pass else 1)
