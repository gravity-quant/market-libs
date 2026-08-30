---
phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo
reviewed: 2026-08-30T03:22:54Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - .github/workflows/ci.yml
  - main_ambito_financiero.py
  - main_higyrus.py
  - main_iol.py
  - main_matriz.py
  - packages/higyrus-client/tests/test_deep_chain_edges.py
  - packages/iol-client/tests/test_deep_chain_edges.py
  - packages/matriz-client/src/matriz_client/_core.py
  - packages/matriz-client/src/matriz_client/models.py
  - packages/matriz-client/tests/test_deep_chain_edges.py
  - packages/matriz-client/tests/test_instruments_flat_identifier_shape.py
  - verification/__init__.py
  - verification/run_evidence.py
  - verification/test_cycle_closure_phase33.py
  - verification/test_main_higyrus_deep_chain.py
  - verification/test_main_higyrus_skip_line_shape.py
  - verification/test_main_iol_deep_chain.py
  - verification/test_main_matriz_deep_chain.py
  - verification/test_main_matriz_skip_line_shape.py
  - verification/test_main_verify_classification.py
  - verification/test_run_evidence.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 39: Code Review Report

**Reviewed:** 2026-08-30T03:22:54Z
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

This phase widens the matriz-client venue allowlist (`_VENUE_ALLOWLIST`) to a
second sandbox host, adds a run-evidence envelope (`verification/run_evidence.py`)
and a non-vacuous cycle-closure predicate to `main_matriz.py`, spends several new
"deep chain" dereferences in the three live drivers (`main_iol.py`,
`main_higyrus.py`, `main_matriz.py`), and fixes a real data-loss bug in
`matriz_client._core` where `byCFICode`/`bySegment` elements return a flat
`{marketId, symbol}` shape instead of the nested `{instrumentId: {...}}` shape
`Instrument` expects.

Targeted verification of the areas called out for this review:

- **Hostname allowlist gate (`main_matriz.py::_venue_token`)**: correct. Uses
  `urlsplit(...).hostname` (not a substring/`endswith`/`in` check), re-parses
  scheme-less input as authority-only, and is exercised by a strong parametrized
  test suite (`test_main_matriz_skip_line_shape.py`) covering suffix-hostile
  hosts, userinfo-embedding attacks, and malformed URLs. No injection/spoofing
  path found.
- **`verification/mutation_gate.py`**: confirmed absent from this diff (not in
  `git diff --stat`, and `verification/__init__.py`'s import of `mutating_allowed`
  from that module is unchanged).
- **New `verification/*.py` files paired with a CI allowlist entry**: all 7 new
  `test_*.py` files added this phase (`test_main_verify_classification.py`,
  `test_main_matriz_skip_line_shape.py`, `test_main_higyrus_skip_line_shape.py`,
  `test_run_evidence.py`, `test_main_iol_deep_chain.py`,
  `test_main_higyrus_deep_chain.py`, `test_main_matriz_deep_chain.py`) are present
  in the `.github/workflows/ci.yml` "driver locks" allowlist. One gap found on an
  *existing* file that received substantial new phase-39 content — see WR-01.
- **New dereferences in `main_*.py` living inside a `try` body**: verified for
  all sites — `quote.puntas[...]` / `titulo.puntas.precioCompra` (iol, 4 sites,
  sync+async ×2 probes), `posicion.parking[...]` (higyrus, 2 sites, sync+async),
  and the six `MarketDataSnapshot` alias dereferences (matriz, 2 sites,
  sync+async). All are inside the `try:` block, never in `except`/`else`/`finally`.
- **`_core._normalize_instrument_element` (flat vs. nested identifier fix)**:
  correct and conservative — additive-only (a nested `instrumentId` key, even
  `None`, short-circuits to a no-op), doesn't fabricate `cficode`, and is wired
  only into the two affected parsers (`parse_get_instruments_by_cfi_response`,
  `parse_get_instruments_by_segment_response`), not into
  `parse_get_all_instruments_response`. Backed by a thorough regression suite
  covering the flat shape, the nested control, and four degenerate-element cases.

## Warnings

### WR-01: `test_cycle_closure_phase33.py` carries this phase's D-09 tests but is not in the CI allowlist

**File:** `.github/workflows/ci.yml:79-91`, `verification/test_cycle_closure_phase33.py`
**Issue:** The repo's own convention (documented inline in `ci.yml`, "driver locks
de matriz y market-data") is that any test file under `verification/` must be
added to the explicit `uv run pytest -q verification/test_*.py \ ...` allowlist
in the `lint` job, because the `test` job always passes an explicit
`packages/<pkg>` path that overrides `testpaths` — so `verification/` is
otherwise **never** exercised in CI, even though `pyproject.toml`'s
`testpaths = ["packages", "tests", "verification"]` nominally includes it.

`verification/test_cycle_closure_phase33.py` received ~260 lines of *new* Phase
39 content in this diff (commit `dde0f10`), including the tests that pin the
core D-09 behavior this phase delivers:
`test_el_loop_consulta_la_evidencia_de_corrida`,
`test_sin_evidencia_el_veredicto_es_skipped_con_destino_nombrado`,
`test_la_causa_medida_del_sobre_viaja_al_detalle`,
`test_un_paquete_limpio_que_corrio_da_pass`,
`test_no_correr_no_escribe_finding`, etc. — all of which import and exercise
`main_matriz._cycle_closure_verdict` / `_cycle_closure_destination` /
`_cycle_closure_loop`.

This file is **not** in the `ci.yml` allowlist (checked against both the
pre-diff and post-diff list). Every other newly-added `verification/test_*.py`
file this phase was correctly wired in; this one — despite carrying the phase's
own regression tests for its headline feature — was missed because it pre-dates
Phase 39 (added in Phase 33) and the new content was appended to an existing
file rather than a new one, so it fell outside the "new file → add to allowlist"
mental checklist. The practical effect: a future regression in
`_cycle_closure_verdict`'s SKIPPED/PASS/FAIL branching, in the destination-naming
table, or in the AST-level guards against re-introducing the vacuous
`findings_path`-based predicate, will not be caught by CI — only by a manual
`pytest verification/` run.

**Fix:** Add `verification/test_cycle_closure_phase33.py` to the `lint` job's
allowlist in `.github/workflows/ci.yml`:
```yaml
      - name: driver locks de market-data y matriz (...)
        run: |
          uv run pytest -q \
            verification/test_main_market_data_deep_chain.py \
            verification/test_safemodel_diff_null_object_links.py \
            verification/test_main_matriz_risk_envelope_keys.py \
            verification/test_safemodel_diff_mapping_recursion.py \
            verification/test_main_verify_classification.py \
            verification/test_main_matriz_skip_line_shape.py \
            verification/test_main_higyrus_skip_line_shape.py \
            verification/test_run_evidence.py \
            verification/test_main_iol_deep_chain.py \
            verification/test_main_higyrus_deep_chain.py \
            verification/test_main_matriz_deep_chain.py \
            verification/test_cycle_closure_phase33.py
```

### WR-02: higyrus vendor-unreachable classification handles DNS-resolution failure but not connection-timeout, undermining D-01's own goal

**File:** `main_higyrus.py:669-684` (`probe_login_sync`), `main_higyrus.py:750-757` (`probe_login_async`)
**Issue:** Phase 39's D-01 fix exists specifically to stop a network condition
that has nothing to do with the client ("the vendor isn't rejecting us — it
isn't *there*") from being written as an `AUTH OPEN` finding into the versioned
`.planning/verification/higyrus-client-findings.md` ledger. The fix narrowly
targets `httpx.ConnectError` (DNS `gaierror` / connection refused). The
docstring explicitly acknowledges the gap it leaves open:

> `` `httpx.ConnectTimeout` NO entra acá (no es subclase): un timeout sigue
> cayendo en el bracket residual. ``

Because `httpx.ConnectTimeout` is a sibling of `httpx.ConnectError` under
`httpx.TransportError` rather than a subclass, a transient connection timeout to
the same unreachable/absent vendor host falls straight into
`_RESIDUAL_PROBE_EXCEPTIONS` (which includes `httpx.HTTPError`, `ConnectTimeout`'s
ultimate superclass) and is written as an `AUTH OPEN` finding — precisely the
"false clean turned false dirty" failure mode D-01 was written to eliminate,
just triggered by a slow/unreachable host instead of a non-resolving one. Given
that the host behind `HIGYRUS_BASE_URL` is documented elsewhere in this same
review context as being DNS-unreachable from the CI/dev network, a connect
*timeout* (as opposed to immediate refusal) is a plausible outcome depending on
network path (e.g. a firewall silently dropping SYN packets rather than
returning RST/unreachable), and would currently pollute the committed ledger
with a spurious finding on every such run.

**Fix:** Extend the vendor-unreachable branch to also catch `httpx.ConnectTimeout`
(and arguably `httpx.PoolTimeout`, which can also result from an unreachable
host holding connections open), mirroring the existing `httpx.ConnectError`
handling in both `probe_login_sync` and `probe_login_async`:
```python
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        _vendor_unreachable = True
        _vendor_unreachable_reason = f"sync login: {type(exc).__name__}: {exc}"
        _auth_failed = True
        _auth_failure_reason = f"sync login: {_VENDOR_UNREACHABLE_DETAIL}"
        return ProbeResult("login_sync", "SKIPPED", _VENDOR_UNREACHABLE_DETAIL)
```
If this widening is intentionally deferred, it should at minimum be tracked as a
named follow-up item rather than left as a silently-accepted gap in a docstring,
since it directly undercuts this phase's own stated goal for this code path.

## Info

### IN-01: `write_run_evidence`'s `triples` parameter is a 4-tuple, named after a 3-element concept

**File:** `verification/run_evidence.py:97-138`
**Issue:** `write_run_evidence(triples: Iterable[tuple[str, str, str, str]], ...)` —
the parameter and the module's prose consistently call these "triples"
(`(slug, model, field_path, kind)`), and the module docstring itself says "Una
triple es `(slug, model, field_path, kind)`" while enumerating four elements.
This is inherited terminology from `DivergenceHandler.seen`'s naming elsewhere in
the codebase (not introduced by this phase), so it's not a functional defect,
but it is a naming inconsistency that could confuse a future reader trying to
match the type annotation (`tuple[str, str, str, str]`, 4 elements) against the
word "triple" (conventionally 3).
**Fix:** No action required; noting for awareness only. If ever revisited,
consider renaming to `records`/`quads` or updating the docstring to clarify that
"triple" here refers to the pre-Phase-39 census unit name rather than tuple
arity.

---

_Reviewed: 2026-08-30T03:22:54Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
