"""Spike 001d: matriz deny-list intactness — sha256 before/after simulated codegen run.

Validates that scoping ``unasync.unasync_files(fpath_list=[aio.py-only])`` is sufficient
to honor the matriz deny-list (4 files locked by ARCHITECTURE.md):

- ``_token_store.py`` — 3-way TokenStore primitive (threading.Lock + asyncio.Lock + ws)
- ``_refresh_policy.py`` — retry + backoff + fail-cache; sync-only by design
- ``_refresh.py`` — MatrizRefresh adapter
- ``ws_client.py`` — WebSocket daemon thread

Method (per Recipe 1 + Wave 4 of 12-RESEARCH.md):

1. Copy the entire ``packages/matriz-client/src/matriz_client/`` directory to a
   sandbox under this experiment dir (``matriz_copy/``). Production source is
   never mutated — read-only access via ``shutil.copytree``.
2. Compute sha256 for ``aio.py`` + each of the 4 deny-listed files BEFORE the
   simulated codegen run.
3. Invoke ``unasync.unasync_files(fpath_list=[<aio.py>], rules=[<matriz Rule>])``.
   The ``fpath_list`` contains ONLY ``aio.py``; the 4 deny-listed files are
   never passed to the tool.
4. Compute sha256 for the same 5 files AFTER the run.
5. Verdict PASS iff (a) all 4 deny-listed files' sha256 are byte-identical
   pre/post, AND (b) ``aio.py`` sha256 differs pre/post (was transformed).

CONVENTIONS.md §"To Avoid": never imports from ``packages/*/src/``; uses
``shutil.copytree`` + ``hashlib`` + ``subprocess`` only.

Run from repo root:

    uv run --with unasync python .planning/spikes/SPIKE-005-codegen-tool-choice/001d-matriz-deny-list-config/experiment.py
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

import unasync

# --- paths ----------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[4]
MATRIZ_DIR = REPO_ROOT / "packages/matriz-client/src/matriz_client"
SPIKE = Path(__file__).resolve().parent
WORK = SPIKE / "matriz_copy"
TRANSCRIPTS = SPIKE / "verification_transcripts.txt"
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
    src = MATRIZ_DIR / name
    if not src.exists():
        sys.stderr.write(f"FATAL: expected file missing: {src}\n")
        raise SystemExit(2)

# --- step 1: sandbox setup ------------------------------------------------

# Recreate WORK each run (deterministic spike artifact).
shutil.rmtree(WORK, ignore_errors=True)

# Copy ENTIRE matriz_client/ to sandbox/matriz_client/. shutil.copytree only
# reads from source — production code is never written to.
shutil.copytree(MATRIZ_DIR, WORK / "matriz_client")
print(f"[step 1] copytree -> {WORK / 'matriz_client'}")

# --- step 2: pre-run sha256 ---------------------------------------------


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


pre_hashes: dict[str, str] = {}
for name in [TARGET, *DENY_LIST]:
    pre_hashes[name] = sha256_of(WORK / "matriz_client" / name)

SHA_BEFORE.write_text(
    "\n".join(f"{name}: {pre_hashes[name]}" for name in [TARGET, *DENY_LIST]) + "\n"
)
print(f"[step 2] pre-hashes written to {SHA_BEFORE}")

# --- step 3: simulated codegen run --------------------------------------
# Matriz Rule draft from 001c/FINDING.md — superset of ámbito + matriz-specific.
# CRITICAL: fpath_list contains ONLY aio.py. The 4 deny-listed files are never
# passed to unasync — the scoping is achieved by file list, not by an exclude= param.

MATRIZ_REPLACEMENTS: dict[str, str] = {
    # Inherited from ámbito (001a/FINDING.md):
    "AsyncClient": "Client",
    "AsyncRetryTransport": "RetryTransport",
    "_atransport": "_transport",
    "aclose": "close",
    # Matriz-specific:
    "_aensure_token": "_ensure_token",
}

work_aio = WORK / "matriz_client" / TARGET
print(f"[step 3] running unasync.unasync_files(fpath_list=[{TARGET}], ...)")
unasync.unasync_files(
    fpath_list=[str(work_aio)],
    rules=[
        unasync.Rule(
            fromdir=str(WORK / "matriz_client") + "/",
            todir=str(WORK / "matriz_client") + "/",
            additional_replacements=MATRIZ_REPLACEMENTS,
        )
    ],
)
print("[step 3] unasync.unasync_files() complete")

# --- step 4: post-run sha256 --------------------------------------------

post_hashes: dict[str, str] = {}
for name in [TARGET, *DENY_LIST]:
    post_hashes[name] = sha256_of(WORK / "matriz_client" / name)

SHA_AFTER.write_text(
    "\n".join(f"{name}: {post_hashes[name]}" for name in [TARGET, *DENY_LIST]) + "\n"
)
print(f"[step 4] post-hashes written to {SHA_AFTER}")

# --- step 5: verdict + transcripts --------------------------------------

# Per-file intactness for deny-list + transformation for aio.py
intactness: dict[str, bool] = {
    name: pre_hashes[name] == post_hashes[name] for name in DENY_LIST
}
aio_transformed = pre_hashes[TARGET] != post_hashes[TARGET]

with TRANSCRIPTS.open("w") as fh:
    fh.write(
        "# Spike 001d — matriz deny-list intactness sha256 transcripts\n"
        f"# Sandbox: {WORK}/matriz_client/\n"
        f"# Codegen fpath_list: [{TARGET}]  (deny-listed files NEVER passed to unasync)\n"
        f"# Method: shutil.copytree → sha256_before → unasync.unasync_files → sha256_after\n\n"
    )
    for name in DENY_LIST:
        ok = intactness[name]
        fh.write(f"{name}:\n")
        fh.write(f"  pre:  {pre_hashes[name]}\n")
        fh.write(f"  post: {post_hashes[name]}\n")
        fh.write(f"  intact: {'PASS' if ok else 'FAIL'}\n\n")
    fh.write(f"{TARGET}:\n")
    fh.write(f"  pre:  {pre_hashes[TARGET]}\n")
    fh.write(f"  post: {post_hashes[TARGET]}\n")
    fh.write(
        f"  transformed: {'PASS' if aio_transformed else 'FAIL'}  "
        "(post MUST differ from pre)\n"
    )

all_intact = all(intactness.values())
verdict_pass = all_intact and aio_transformed

# --- step 6: cleanup sandbox (deterministic artifact policy) ------------
# The sandbox is fully regenerable from experiment.py; do NOT leave 200KB of
# derived files in the spike directory. Spike artifacts are the
# verification_transcripts.txt + sha256_before.txt + sha256_after.txt only.
shutil.rmtree(WORK, ignore_errors=True)

print()
print("=== Verdict ===")
for name in DENY_LIST:
    print(f"  {name}: intact={'PASS' if intactness[name] else 'FAIL'}")
print(f"  {TARGET}: transformed={'PASS' if aio_transformed else 'FAIL'}")
print(f"SPIKE 001d VERDICT: {'PASS' if verdict_pass else 'FAIL'}")
print(f"Transcripts written to {TRANSCRIPTS}")
print(f"Sandbox cleaned up: {WORK}")

sys.exit(0 if verdict_pass else 1)
