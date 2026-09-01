---
phase: 44-release-market-data-client-0-7-0
reviewed: 2026-09-01T20:59:39Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - packages/market-data-client/pyproject.toml
  - packages/market-data-client/src/market_data_client/__init__.py
  - packages/market-data-client/README.md
findings:
  critical: 1
  warning: 1
  info: 0
  total: 2
status: issues_found
---

# Phase 44: Code Review Report

**Reviewed:** 2026-09-01T20:59:39Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

This is a docs/metadata-only phase: version bump (`pyproject.toml`, `__init__.py`), the
`FeedSubscription` export fix (SURF-MD-FEEDSUB-43), and a new `### v0.7.0` changelog entry in
`README.md`. Verified directly:

- Version string consistency: `pyproject.toml` (`version = "0.7.0"`) and `__init__.py`
  (`__version__ = "0.7.0"`) match. Confirmed via git history that all 4 claimed version sites
  (pyproject, `__init__.py`, and both README URL substitutions) were bumped together.
- `FeedSubscription` export: genuinely present in the `models` import block, in `__all__`
  (alphabetically placed), importable from package root, and matches the class actually defined
  in `models.py:1372`. `ruff check` and `mypy --strict` both pass clean on `__init__.py`.
- The two README migration tables (`Instrument`, `Segment`) were checked field-by-field against
  the live class declarations in `models.py` (lines 830-840 for `Instrument`, 894-895 for
  `Segment`) and against the pre-Phase-43 shape (`git show 2a3de99^:...models.py`). Both tables
  are accurate: the "7 gained / 1 lost" claim for `Instrument` and the "3 removed / 2 added"
  claim for `Segment` both match the actual dataclass fields, and the truthiness-flip claim for
  `Segment` matches `SafeModel.__bool__`'s documented semantics (`models.py:183`).

However, tracing the full diff between the 0.6.0 baseline and this commit (via
`git log -- .../models.py`) surfaced that the `### v0.7.0` changelog entry is materially
**incomplete**: it documents only the `Instrument`/`Segment` reconciliation and omits several
other model-surface changes that shipped in the same pre-0.7.0 window (Phase 43, commit
`327b3ce`), including a newly-**required** field on an already-published, already-exported class.
See CR-01. A second, lower-confidence gap around `SafeModel`'s export surface is filed as WR-01.

## Critical Issues

### CR-01: v0.7.0 changelog omits real breaking/additive changes shipped in the same release window

**File:** `packages/market-data-client/README.md:125-186`
**Issue:** The `### v0.7.0` changelog entry frames the entire release as "`Instrument` y
`Segment` se reconcilian..." and its two tables cover only those two models. But
`git log -- packages/market-data-client/src/market_data_client/models.py` shows the 0.6.0→0.7.0
window contains a second commit, `327b3ce` ("type the five measured extra keys"), landed in the
same phase (43) as the `Instrument`/`Segment` reconciliation and released together under this
same version bump. That commit shipped, undocumented in the changelog:

- A brand-new public model, `FeedSubscription` (15 fields) — exported in this very diff
  (`__init__.py`), yet the changelog text never explains what it is, why it now exists, or that
  it's reachable as `market_data_client.FeedSubscription`.
- `FeedIngestor.subscription: FeedSubscription` — a **new required field** (no default, placed
  before the class's first defaulted field; `models.py:1494`) on `FeedIngestor`, which has been
  publicly exported since v0.5.0. Any caller constructing `FeedIngestor(...)` directly (not via
  `from_api`) now needs an extra positional/keyword argument — this is exactly the class of
  change the rest of this changelog (and prior versions' entries) calls out explicitly as
  breaking.
- `FeedIngestor.last_error_age_seconds: int | None` and `FeedIngestor.last_error_at: str | None`
  — new optional fields (`models.py:1496-1497`).
- `HealthFeed.symbols_never_delivered: int` — a **new required field**, deliberately declared
  non-nullable per its own docstring (`models.py:1530-1537`), on `HealthFeed`, also public since
  v0.5.0.
- `Symbol.note: str | None` — new optional field.

A consumer who reads only this changelog (which is the documented, recommended migration path —
see the "Changelog" section header and the pattern established by every prior version's entry)
will not know that constructing `FeedIngestor` or `HealthFeed` directly now requires an extra
argument, and will not know `FeedSubscription` exists at all despite it being a top-level public
export as of this exact commit. This directly contradicts the phase's own stated purpose
(per `CLAUDE.md`: "cada divergencia... debe ser detectada, documentada y corregida") and the
review's mandate to confirm the changelog is accurate, not a stale/partial copy of what shipped.

**Fix:** Add a third table (or bullet list) to the `### v0.7.0` entry covering the Phase 43
"5 measured extra keys" commit, mirroring the style already used for `Instrument`/`Segment`:

```markdown
**`FeedIngestor` / `HealthFeed` / `Symbol` — `GET /health/feed`, `GET /symbols`**

| Antes (0.6.0 publicado) | Ahora (0.7.0) |
| --- | --- |
| — | `FeedSubscription` (`market_data_client.FeedSubscription`) — nuevo modelo público, 15 campos, anidado en `ingestor.subscription` |
| `FeedIngestor(...)` sin `subscription` | `FeedIngestor.subscription: FeedSubscription` — **campo requerido nuevo**, sin default; todo consumidor que construya `FeedIngestor` directamente (no vía `from_api`) necesita el argumento extra |
| — | `FeedIngestor.last_error_age_seconds` (`int \| None`) — nuevo |
| — | `FeedIngestor.last_error_at` (`str \| None`) — nuevo |
| — | `HealthFeed.symbols_never_delivered` (`int`) — **campo requerido nuevo**, no nullable |
| — | `Symbol.note` (`str \| None`) — nuevo |
```

## Warnings

### WR-01: `SafeModel` is public in `models.__all__` but not re-exported from the package root

**File:** `packages/market-data-client/src/market_data_client/__init__.py:72-100` (import block
and `__all__`)
**Issue:** `market_data_client.models.__all__` declares `SafeModel` as public
(`models.py:120`), but `__init__.py` does not import or re-export it — `SafeModel` is reachable
only via `from market_data_client.models import SafeModel`, not `from market_data_client import
SafeModel`. This is the exact bug class this phase just fixed for `FeedSubscription`
(SURF-MD-FEEDSUB-43): a name public in the submodule's `__all__` that never made it to the flat
package namespace. It's also inconsistent with the sibling package `higyrus_client`, whose
`__init__.py` does export `SafeModel` from its package root
(`packages/higyrus-client/src/higyrus_client/__init__.py:71,98`). The README references
`SafeModel.from_api()` as a concept multiple times (lines 240, 376) without ever showing which
import path a consumer should use, so this asymmetry is easy to miss.

This is filed as a warning rather than a blocker because it predates this phase's diff (it was
not touched by any of the three reviewed commits) and `check_surface_types.py` resolves its
candidate set starting from the package-root `__all__`, so it isn't silently breaking that gate
today. But it is a real, currently-shippable export-surface gap of the same shape the phase title
is about, and worth closing in the same pass rather than leaving as fresh debt.

**Fix:** Either (a) add `SafeModel` to the `from market_data_client.models import (...)` block and
`__all__` in `__init__.py`, matching `higyrus_client`'s precedent, or (b) if the omission is
intentional (e.g. `SafeModel` is meant to stay an internal base class despite being in
`models.__all__`), remove it from `models.__all__` and document the decision — the current state,
public in one `__all__` and absent from the other with no comment either way, is what should not
ship silently.

---

_Reviewed: 2026-09-01T20:59:39Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
