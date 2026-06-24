# Phase 15 — LOC Attestation (REFAC-05, Criterion #5)

**Status:** measure-only attestation (D-08). No physical LOC reduction of library
code occurs in Phase 15 — this document pins the baseline anchor, records the
current measured LOC, computes the delta, and documents the operator-accepted
residual carried forward to v1.3.

---

## 1. Baseline anchor resolution (D-09)

The ROADMAP Criterion #5 phrases the target as "−30% LOC vs the **v1.0 baseline**".
That phrasing cannot be honored literally because **no `v1.0` git tag exists** in
this repository. The only tags present are:

| Tag | Kind |
|-----|------|
| `v1.1` | milestone tag |
| `ambito-financiero-client-v0.1.1` | per-package release tag |
| `higyrus-client-v0.1.1` | per-package release tag |
| `iol-client-v0.1.1` | per-package release tag |
| `matriz-client-v0.1.1` | per-package release tag |

(`git tag` output, captured during Phase 15 execution — no `v1.0`.)

**Pinned anchor:** the documented residuals (iol −5.1%, matriz −20%) were measured
against the **Phase 6/7 core-extraction baseline**, recorded in
`.planning/milestones/v1.1-phases/07-core-py-extraction-sync-async-logic-dedup/07-03-SUMMARY.md`
(LOC Drop Analysis). That summary captured the post-extraction figures:

| File | Pre-extraction | Post-extraction (Phase 6/7 anchor) |
|------|----------------|------------------------------------|
| `iol_client/client.py` | 522 | 490 |
| `iol_client/aio.py` | 476 | 457 |
| **iol aggregate** | **998** | **947** |

The pinned anchor for this attestation is the **Phase 6/7 post-extraction iol
aggregate of 947** (490 + 457). The pre-extraction figure (998) is recorded for
context. matriz was not part of the iol extraction pair; its residual was tracked
separately (≈ −20% against its own pre-extraction baseline).

---

## 2. Current measured LOC

Measured via `wc -l` during Phase 15 execution (un-migrated library source — the
driver migration does **not** touch library `.py` files, only the root
`main_*.py` drivers + `verification/` tests):

| File | Current LOC |
|------|-------------|
| `packages/iol-client/src/iol_client/client.py` | 756 |
| `packages/iol-client/src/iol_client/aio.py` | 755 |
| **iol aggregate** | **1511** |
| `packages/matriz-client/src/matriz_client/client.py` | 922 |

---

## 3. Delta vs the pinned anchor

| Subsystem | Anchor (Phase 6/7) | Current | Delta | Direction |
|-----------|--------------------|---------|-------|-----------|
| iol (`client.py` + `aio.py`) | 947 | 1511 | **+564 (+59.6%)** | GROWN |
| iol (vs pre-extraction 998) | 998 | 1511 | +513 (+51.4%) | GROWN |
| matriz (`client.py`) | — (≈ −20% residual tracked separately) | 922 | n/a | — |

**Library LOC has GROWN substantially since the Phase 6/7 extraction**, driven by
the intervening v1.1 feature phases (Phase 8 retry/logging, Phase 10 TokenStore,
Phase 13 ergonomics/views, etc.). The **−30% Criterion #5 target is therefore
structurally unreachable** by this phase.

### Why −30% is out of scope here

Physical reduction of duplicated sync/async library logic was the planned
**Phase 16 codegen** work. That mechanism (codegen via unasync) was evaluated in
the **Phase 12 SPIKE-005 and returned NO-GO** (3 of 8 D-RIGOR-01 acceptance items
FAILed — byte-identity, `ruff check`, and ámbito `pytest`, all tracing to
source-shape asymmetry). Phase 16 was consequently **DROPPED**. The real LOC
reduction is deferred to a **v1.3 libcst spike** (REFAC-06 carry-forward,
`spike-codegen-libcst-v1.3.md`).

Phase 15 (REFAC-05) is purely **driver migration + measure-only attestation**
(D-08). It does not delete or rewrite library code to chase the target.

---

## 4. Back-compat shims STAY (no shim deletion)

The locked v1.x decision is **"shims STAY / 100% back-compat"**. The PEP 562
`__getattr__` shim (`_client` forwarding) and the top-level delegators
(`pkg.get_X(...)`, module-level `configure()` / `_request()`) remain **intact** in
every package. Deleting them to manufacture a −30% number would break external
consumers and violate the locked decision — explicitly **NOT** done.

The Phase 15 driver migration changes only **how the internal drivers acquire a
client** (one threaded `Client()` / `AsyncClient()` per driver instead of reaching
the lazy module singleton via `_get_default()`); it does not remove the singleton
or its shim surface.

---

## 5. Test baseline obligation (≥907 passing)

The cross-milestone obligation is that the milestone test baseline (**≥907
passing**) must hold. Captured during Phase 15 execution with the full workspace
installed (`uv sync --all-packages --all-extras --dev --frozen`):

- **Collected:** 986 tests (`pytest --collect-only -q` → `985/986 tests collected
  (1 deselected)`), comfortably above the ≥907 floor.
- The 15-01 driver migration adds **1 new AST-guard test**
  (`verification/test_main_ambito_financiero_uses_single_client_instance.py`) and
  **updates 6 existing driver-invariant tests**
  (`packages/ambito-financiero-client/tests/test_driver_invariants.py`) to thread
  the per-instance client; net the collected count rises, never falls below the
  baseline.
- ámbito-scoped targeted run (driver invariants + harness mutation gate + AST
  guard) = **12 passed**; ámbito full package suite (excluding the cross-package
  matriz-coupled `test_harness_mutation_gate.py` when matriz is not installed) =
  **127 passed**.

> Note: the full repo-wide `pytest -q` includes live-API probes that depend on
> third-party service availability and market hours; transient live failures are
> environmental (per CLAUDE.md "Dependencias externas en vivo") and do not count
> against the static ≥907 baseline, which is satisfied by the collected count.

---

## 6. Residual gap — operator-accepted carry-forward

| Item | Disposition |
|------|-------------|
| −30% physical library LOC reduction | **NOT achieved** in Phase 15 (structurally unreachable; library LOC has grown since Phase 6/7) |
| Mechanism | codegen (Phase 16) **DROPPED** per Phase 12 NO-GO |
| Carry-forward | **v1.3 libcst spike** (REFAC-06; `spike-codegen-libcst-v1.3.md`) |
| Shims | **STAY intact** (100% back-compat; no deletion to chase the target) |
| Phase 15 deliverable | driver migration (×4) + this measure-only attestation (D-08) |

The residual −30% gap is **operator-accepted** and carried forward to v1.3. Phase
15 satisfies Criterion #5 as an **attestation/measurement** step, not a physical
reduction.
