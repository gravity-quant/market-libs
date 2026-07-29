# Deferred Items — Phase 20

Out-of-scope discoveries logged during execution (not fixed in the surfacing plan).

## From Plan 20-04 (sync client shell)

- **`uv.lock` missing the `market-data-client` workspace member.** Running
  `uv sync --all-packages --all-extras --dev --frozen` (needed to install the
  package for ruff/mypy/import verification) regenerated `uv.lock` to register
  `market-data-client` as a workspace member (31-line insertion: member list +
  `[[package]]` block + `[package.metadata]`). This is a scaffold-level gap
  (Plan 01 created `pyproject.toml` but the lock was never regenerated), NOT
  caused by `client.py`. Out of scope for 20-04 (`files_modified: client.py`
  only), so it was NOT committed here. Should be captured by the package
  scaffold / release-prep plan (PUB-MD-01) via `uv lock`. The worktree's local
  `uv.lock` edit is discarded on worktree removal — regenerable with `uv lock`.
