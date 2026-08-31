# Pitfalls Research

**Domain:** Backlog/debt closeout inside a high-discipline live-verification monorepo (v1.8 "Cierre de deuda post-v1.7")
**Researched:** 2026-08-31
**Measured against:** working tree at `e55398d` (all code claims below were re-derived by reading/running the repo, not quoted from planning prose)
**Confidence:** HIGH for repo-measured claims · LOW for the three web-sourced generalities (see Sources)

---

## Framing

The four v1.8 groups are not "small". Each one sits on top of a *signed* precedent, and the
characteristic failure of a debt-closeout milestone in this project is not "the fix was wrong"
— it is **the fix was right and the ceremony around it was skipped**, so a shipped
guarantee gets quietly weaker without anyone deciding to weaken it.

Three project-specific properties make that failure easy here:

1. **Silent-vs-visible is the product.** The core value is "cada divergencia … debe ser
   detectada, documentada y corregida". Any change that makes a divergence *less* visible is
   a regression of the product, even if it makes a file tidier. HARN-01 is exactly this shape.
2. **Every source-breaking change so far has been operator-signed.** 33-07 Task 1 authorized
   *three* shape changes and explicitly refused a fourth (this one). Phases 24/28/34/40 each
   put the irreversible publish behind two independent human gates that were never collapsed
   despite `auto_advance: true` + `mode: yolo`. There is no precedent for a shape change
   landing without that.
3. **"It ran" ≠ "it is enforced".** Measured at HEAD: `verification/` holds **52**
   `test_*.py` files; `ci.yml` runs **12** of them by explicit allowlist. 40 locks are inert
   by construction. A retroactive validation pass that greps for file existence, or runs a
   test locally, certifies nothing about what CI enforces.

---

## Critical Pitfalls

### Pitfall 1: LIVE-01 marked "resolved" on a *different* root cause

**What goes wrong:**
`LIVE-HIGY-33`'s recorded root cause is narrow and specific: the hostname does not resolve
(`socket.gaierror` → `httpx.ConnectError`), credentials present, scheme `https` — **network
reachability, not credential rejection**. v1.8 re-probes, gets *some* failure or *some*
success, and the item is flipped. Two symmetric errors:

- **False "still blocked, same cause."** `main_higyrus.py:669` catches `httpx.ConnectError`
  only, and the code comment at `:678` states outright that `httpx.ConnectTimeout` is **not**
  a subclass and does not enter that branch. If the host now resolves but hangs (VPN
  half-open, firewall drop), the run falls to the generic branch and produces a `FINDING` or
  `FAILED` instead of the `SKIPPED higyrus-client: vendor host unreachable (DNS) —
  LIVE-HIGY-33` line. Someone reading the summary sees "still failing" and re-stamps the same
  cause on evidence that does not support it.
- **False "resolved."** DNS resolving is *not* resolution. The item's deliverable is the
  **22 uncontrasted triples** (`Movimiento` 9, `PosicionValuada` 11, `Posicion` 2) from the
  `29-SIZING.md` floor. A driver that connects and logs in but never contrasts the census
  leaves LIVE-HIGY-33 open while the checkbox says closed.

**Why it happens:**
The backlog entry is prose ("DNS aún sin resolver"), so re-probing feels like a yes/no
question. It is not: the entry encodes a *measured exception class* and a *numeric census
target*, and only both together close it.

**How to avoid:**
- Define the acceptance criterion up front as two independent facts: (a) the measured
  exception type/errno of this run, recorded verbatim, compared to `gaierror`; (b) the 22
  triples contrasted, or an explicit statement that they were not.
- Decide *before* the run whether to widen the unreachable branch to `ConnectTimeout`
  (closing the documented WR-02 / D39 scope gap) or to re-declare it out of scope. Do not
  discover this mid-run and patch the classifier to make the output read nicely.
- If the cause changed, that is a **new** backlog entry with a new measured cause, not a
  re-stamp of LIVE-HIGY-33.

**Warning signs:**
Any sentence of the form "re-probed, still blocked" without a pasted exception type. A
`FINDING`/`FAILED` classification on higyrus where the last two milestones produced `SKIPPED`.
The census section of the phase report saying "N/A" rather than "not measured because X".

**Phase to address:** the live phase (see Phasing, Phase A).

---

### Pitfall 2: LIVE-02 blocked by a stale third copy of the venue policy — then "quickly fixed" the unsafe way

**What goes wrong:**
`ROADMAP.md § Backlog` asserts that `scripts/literal_census_33.py` "ya tiene el gate
remarkets-only listo para correr contra el sandbox `bbsa` ahora desbloqueado". **That is false
at HEAD.** Measured:

| Copy | Location | Form | Admits `bbsa`? |
|---|---|---|---|
| Driver | `main_matriz.py:139` `_VENUE_ALLOWLIST` | exact hostname equality, 2 entries | **yes** (Phase 39 D-02) |
| Census script | `scripts/literal_census_33.py:192` | `if "remarkets" not in base:` (substring) | **no** — will SKIP |
| Mutation gate | `verification/mutation_gate.py:73` `_SANDBOX_HOST` | exact, remarkets only | **no — deliberately** (T-39-02 keeps order entry fail-closed under bbsa) |

So the census run SKIPs on its first attempt. The pitfall is what happens next: under time
pressure someone edits line 192 inline to make the run go. The two bad edits are
(a) `if "bbsa" not in base and "remarkets" not in base:` — which restores exactly the
substring weakness D-02 removed (`https://api.remarkets.primary.com.ar.attacker.example`
passes; so does a `…@attacker.example` userinfo form), and (b) widening
`verification/mutation_gate.py` "for consistency", which silently re-arms order entry on a
venue where it is currently refused by construction.

**Why it happens:**
The policy is duplicated three ways by design (no shared code between packages), Phase 39
widened only the copy it needed, and the roadmap prose then described the *intended* state as
if it were the shipped state.

**How to avoid:**
- Treat widening the census gate as the same class of change as Phase 39 D-02: a **blocking
  human checkpoint**, not a one-line edit. The code says so itself — `main_matriz.py:133-134`:
  *"Ampliar este mapping NO es un cambio de rutina: cada host nuevo exige un checkpoint humano
  bloqueante (prohibición P-05)."*
- Copy the driver's `_VENUE_ALLOWLIST` verbatim (exact-equality dict), never re-derive a
  predicate.
- Add a test that pins all three copies at once: census-gate allowlist **==** driver
  allowlist, and `mutation_gate._SANDBOX_HOST` **∉** the bbsa entry. Absent that, the next
  widening drifts again.
- Correct the ROADMAP sentence in the same commit. A backlog entry that overstates readiness
  is how the next reader skips the check.

**Warning signs:**
A diff to `scripts/literal_census_33.py` containing `in base` / `endswith`. Any diff to
`verification/mutation_gate.py` in a phase whose scope is a read-only census. The census
printing `SKIPPED — base URL fuera de política` and the phase report treating it as a vendor
problem.

**Phase to address:** Phase A, behind a blocking human checkpoint before any network call.

---

### Pitfall 3: The matriz RESPONSE-`Literal` census gets read as license to promote to `Literal`

**What goes wrong:**
The S-4 census measures *what values the vendor sends* for `marketId` / `cficode` /
`currency` / `orderTypes` / `ordType`. It is a measurement. The signed **D-lock (b)** from
Phase 29 says RESPONSE fields are **never** closed as `Literal` in this line of work. A census
that comes back with a small tidy value set invites exactly the promotion the lock forbids —
and the promotion would make an unseen vendor value fatal.

Two secondary traps in the same item:

- **Venue generalization.** `bbsa.matrizoms.com.ar` is a *different sandbox*, not remarkets
  (Phase 39 D-02 authorized it as a distinct confirmed-safe host). A vocabulary measured on
  bbsa is bbsa's vocabulary. Reporting it as "matriz's RESPONSE vocabulary" over-generalizes
  from one venue.
- **An owed correction with a named owner.** `29-DLOCK-RESPONSE-LITERAL.md:140-142` claims the
  divergence stream is the census mechanism; it is not (the `Literal` branch of `walk_field`
  returns early with `literal_enforced=False` and never calls the sink). That paragraph is in
  a **signed** artifact, so the correction belongs to the signatory — not to whoever happens to
  run the census.

**Why it happens:**
"We finally have the data" reads as "we can finally decide". The lock exists precisely because
data from one venue at one time is not the decision input.

**How to avoid:**
Write the census output as a value inventory with venue + timestamp in the header, and an
explicit line stating that D-lock (b) remains in force and this artifact does not revoke it.
Route the `29-DLOCK` paragraph correction as its own operator-signed edit.

**Warning signs:**
Any diff touching `matriz_client/types.py` `Literal` aliases during the census phase. A census
report whose header does not name the venue.

**Phase to address:** Phase A.

---

### Pitfall 4: Retroactive Nyquist validation that grades against what shipped

**What goes wrong:**
`VALIDATION.md` is, by its own text, a **pre-execution sampling contract** — "per-phase
validation contract for feedback sampling *during* execution", "Max feedback latency: ~30s".
Its value is catching defects while the phase runs. Run afterwards, the only honest deliverable
is a *coverage audit*. The failure mode is flipping `status: draft → validated` and
`nyquist_compliant: false → true` across 35-39 on the strength of "the suite is green today",
which:

- erases the true historical record (the milestone audit machinery explicitly distinguishes
  NOT-VALIDATED (`draft`) from PARTIAL (`validated` + `nyquist_compliant: false`) — the
  comment is inline in each file's front-matter);
- redefines each phase's criterion as "whatever the shipped artifact satisfies", because the
  artifact is now the only evidence available.

**Why it happens:**
The columns are `File Exists` and `Status` with ⬜/✅ boxes. Filling boxes is mechanical and
feels like the task. It is the cheapest possible reading of the task.

**How to avoid:**
Adopt the bar the v1.7 milestone-close already set for `40-VERIFICATION.md`: it re-confirmed
22/22 **against live state** (git, GitHub API, a real install from the published wheels), *not*
against the SUMMARY.md's claims. Apply the same rule per row, with three dispositions and no
undisposed rows (the "cero filas sin disponer" convention `38-CENSUS.md` / `39-CENSUS.md`
already established):

| Disposition | Meaning | Required evidence |
|---|---|---|
| `VERIFIED-NOW` | re-ran today | command + output + enforcement surface |
| `VERIFIED-HISTORICALLY` | evidence exists in the phase artifacts | artifact path + commit sha; provenance marked historical |
| `NOT-VERIFIABLE-RETROACTIVELY` | non-reproducible by nature | named, not graded, not ✅ |

**Warning signs:**
A commit that flips five `nyquist_compliant` flags with no per-row evidence table. Any ✅ on a
row whose "Test Type" column reads `manual`.

**Phase to address:** the validation-audit phase (Phase B), and it must run against a *frozen*
v1.7 state — see Pitfall 7.

---

### Pitfall 5: "Green locally" certifying a lock that CI never runs

**What goes wrong:**
Measured at HEAD: `ls verification/test_*.py | wc -l` = **52**; the `ci.yml` explicit allowlist
runs **12**. The comment above that allowlist says why — `verification/` carries pre-existing
red (HARN-VERIF-01), so the list is hand-maintained and *"cada guard nuevo se agrega a esta
lista a mano."* 39-VALIDATION.md's own Wave 0 list carries this as a requirement, citing the
Phase 36 code-review defect **WR-01**: a lock added to `verification/` without the matching
`ci.yml` line "es INERTE".

A retroactive pass that runs `pytest -q verification/test_main_iol_deep_chain.py` and marks ✅
has verified that the file passes on this laptop today. It has not verified that a regression
would be caught.

**Why it happens:**
`testpaths` in `pyproject.toml` includes `verification`, so local `pytest` picks these up
automatically. CI overrides it with explicit paths. The two environments disagree by design and
the disagreement is invisible from a local green.

**How to avoid:**
Every ✅ in the retroactive map carries an **enforcement column**: which CI job and which line
runs it, or `NOT ENFORCED`. Expect a non-trivial count of `NOT ENFORCED` — that count *is* the
finding, and it is more valuable than the checkmarks.

**Warning signs:**
An audit that reports 100% green. A phase report citing `testpaths` as proof of CI coverage.

**Phase to address:** Phase B.

---

### Pitfall 6: "Just fix the model" — SHAPE-01 skipping the ceremony every prior source-breaking change went through

**What goes wrong:**
`Instrument` and `Segment` are wrong in a way that is now *visible* rather than silent
(Phase 33 fixed the envelope unwrap; the field sets remain wrong). `Segment` is the extreme
case: declared `marketSegmentId` / `marketId` / `description` vs wire `segment` /
`live_instruments` — **disjoint sets**, so today every row from `get_segments()` decodes with
three empty strings. Fixing it is three lines of dataclass. That is the trap: the *code* change
is trivial and the *release* change is not.

The precedent chain is explicit and was measured in the repo:

| Step | Precedent | Where it lives |
|---|---|---|
| Operator disposition required for a published-model shape change | 33-07 Task 1 authorized SC-1/SC-2/SC-3 and **refused this one**; applying it anyway is the contract change T-33-44 prohibits | documented verbatim in `_core.py:1042-1051` |
| Source-breaking on a 0.x line ⇒ **minor** bump, never patch | 0.4.0 (28-01 D-01: a patch bump would violate any `~=0.3.1` pin), 0.5.0, 0.6.0 — all breaking, all minor | `README.md` changelog sections |
| README `### vX.Y.Z` section + old→new **migration table** | v0.5.0 and v0.6.0 both carry one | `packages/market-data-client/README.md:125-150` |
| Additive docstring record — never erase the prior verdict | "**BREAKING since 0.6.0 (Phase 40, D-12)**" appended below the Phase 33 and Phase 36 blocks | `models.py:476` |
| 4 version sites moved together | `pyproject.toml:3`, `__init__.py:163`, README install lines `:15` and `:24` | measured |
| Two independent human gates on merge + tag, never collapsed | Phases 24, 28, 34, 40 (D-08 / D-18) | — |

So SHAPE-01 is `market-data-client` **0.6.0 → 0.7.0**, with a migration table, a docstring
block appended (not rewritten), 4 version sites, and a double human gate.

**Why it happens:**
The item reads as a bug fix ("the declared shape is wrong"), and bug fixes do not usually carry
release ceremony. But this bug lives in a published wheel's public dataclass.

**How to avoid:**
Write the changelog entry and migration table **first**, before the model edit. If the table is
hard to write, that is the signal that the change needs its own operator disposition — which it
does regardless, since 33-07 explicitly withheld it.

**Warning signs:**
A plan whose files-modified list contains `models.py` but not `README.md` and
`pyproject.toml`. A proposed patch bump. A docstring edit that *replaces* the Phase 33
explanation instead of appending below it.

**Phase to address:** Phase C (fix) + Phase D (release) — separate, per precedent.

---

### Pitfall 7: SHAPE-01's mocked tests already encode the fabricated shape — and the tempting fix keeps them fabricated

**What goes wrong:**
Six test files assert the field names the wire never emits (measured):

```
packages/market-data-client/tests/test_reference_client.py:80        {"marketSegmentId": "DDF", "marketId": "ROFX", "description": "Dolar"}
packages/market-data-client/tests/test_reference_async_client.py:76  (same fixture, async surface)
packages/market-data-client/tests/test_reference_core.py:186         [{"marketSegmentId": "S1", "marketId": "M"}]
packages/market-data-client/tests/test_reference_models.py:52        assert seg.marketSegmentId == ""
packages/market-data-client/tests/test_reference_envelope_unwrap.py:129  "instrumentType": "E"
packages/market-data-client/tests/test_decode.py:681                 "marketSegmentId": "DDF"
```

These are mocks that agree with the *model* and disagree with *reality* — a green suite
certifying a wrong contract. The tempting repair is to rename the keys in the fixtures so the
suite stays green. That yields a mock that agrees with the *new* model and was still never
checked against the wire: the identical defect class v1.7 Phase 39 filed as debt ("un mock de
matriz codificaba una forma de instrumento anidada que el vendor nunca emite").

**Why it happens:**
Test fixtures were authored in v1.4 Phase 22 when the shape was explicitly "PROVISIONAL
(OpenAPI not vendored; Phase 23 reconciles)" — and Phase 23 never reconciled these two.

**How to avoid:**
Derive every fixture from the committed baselines
`.planning/verification/schemas/market-data-client/get-instruments.json` and `get-segments.json`,
and add one test asserting the fixture key-set is a subset of the baseline schema key-set. Then
a future fabricated fixture fails.

**Warning signs:**
A SHAPE-01 diff that touches `models.py` and the six test files but not the baselines, and does
not add a fixture-vs-baseline assertion.

**Phase to address:** Phase C.

---

### Pitfall 8: SHAPE-01 corrected against a month-old frozen baseline

**What goes wrong:**
Those two baselines carry `"captured_at": "2026-07-31T16:49:…"` — over a month old, from the
v1.5 Phase 27 era. And `_write_or_check_schema` is **write-once and never overwrites on drift**
(D-25): once the file exists, a changed wire shape produces a *finding*, never an updated
baseline. So the committed baseline is frozen at first capture, permanently. Correcting a
published model's declared shape against that artifact is fixing to the shape the vendor had
on 2026-07-31.

**Why it happens:**
The baseline is the most authoritative-looking artifact in the repo (JSON, committed,
schema-shaped). Its write-once semantics are documented in a driver comment, not in the file.

**How to avoid:**
Run the market-data driver live **before** the model edit (creds exist; this endpoint ran in
Phase 33) and use the fresh read as source of truth, with the frozen baseline as the second
opinion. Sequence this so the live phase precedes the shape phase (see Phasing). If the live
read cannot happen, say so and mark the correction provisional with a named destination —
never silently fall back to the frozen file.

**Warning signs:**
A plan citing `get-segments.json` as evidence without a `captured_at` date next to it. Zero
drift findings and zero live runs for these endpoints in the phase report.

**Phase to address:** Phase A (fresh read) → Phase C (fix).

---

### Pitfall 9: HARN-01 turns a cosmetic duplicate into permanent silent census loss

**What goes wrong — mechanics, measured:**
`verification/findings.py:665-671` — with `idempotent_by_title=True`, the title scan runs
**first**, before the human-status preservation guard and before the fid path, and no-ops on
*any* existing finding carrying that title (only the ART block is refreshed). The schema-drift
title is `f"schema drift en {client_function}"` (`main_market_data.py:517`) — **endpoint-scoped
and content-free**.

Turning the flag on at that call site therefore makes the *first* drift ever recorded for an
endpoint permanent, and swallows every *later, genuinely different* drift on that same
endpoint — forever, across runs, because the findings files are committed to the repo. The
backlog entry correctly notes that today "no hay pérdida de censo — nada se descarta". The
naive fix **creates** the loss, and creates it in exactly the shape this project exists to
eliminate: a real divergence that never reaches a human.

**Why it happens:**
`idempotent_by_title=True` is used correctly at 8 other call sites in the drivers — but every
one of those is a *terminal* whose title is genuinely content-identical across runs
(`EXPECTED`/`NO-FIX` terminals, D-MATZ-27). Drift is not a terminal; its content is what
changed.

**How to avoid:**
Content-address the *title*, not the call. Fold a short digest of the schema diff into the
title so a different drift produces a different title and dedupes only against itself; or
dedupe within a single run only (the 22-blocks-for-8-snapshots problem is a within-run
duplication across two passes × surfaces, not a cross-run one). Then add a falsification test:
seed one drift, assert the second identical drift no-ops **and** a *different* drift on the same
endpoint still writes a new block.

**Warning signs:**
A one-line diff adding `idempotent_by_title=True,` to `_write_or_check_schema`. Any test named
"dedupe" that only asserts the collapse and not the non-collapse.

**Phase to address:** Phase B or a harness phase — but never as an unreviewed one-liner.

---

### Pitfall 10: HARN-01 breaks the fid-count invariant, and the invariant gets relaxed instead

**What goes wrong:**
Both drift call sites do `fid = _next_fid()` **before** `append_finding(...)`. A title-dedupe
no-op therefore consumes a fid without writing a `### F-` block, breaking property **P-3**
pinned by `verification/test_finding_count_consistency.py`: *"la cantidad de fids emitidos tiene
que igualar la de bloques `### F-` nuevos."* That file's docstring names `_write_or_check_schema`
explicitly — *"comparte exactamente este hazard y queda cubierto por la misma propiedad"* — and
its whole reason for existing is the failure mode "el run pierde su entregable creyendo que
tuvo éxito". The tempting response to a newly-red P-3 is to relax it.

**How to avoid:**
Allocate the fid **after** the dedupe decision, not before. P-3 stays exactly as written. If
P-3 turns red during HARN-01, that is the test doing its job, not a stale assertion.

**Warning signs:**
A diff to `test_finding_count_consistency.py` inside a phase whose scope is "dedupe drift
findings". A driver `SUMMARY: … FINDING=N` where N exceeds the new blocks in the findings file.

**Phase to address:** same phase as HARN-01.

---

### Pitfall 11: HARN-02 changes decode *disposition*, not just typing

**What goes wrong:**
The 5 remaining `extra` keys (`HealthFeed.symbols_never_delivered`,
`FeedIngestor.ingestor.last_error_age_seconds` / `.last_error_at` / `.subscription`,
`Symbol.note`) are `extra`-species today, and `extra` is **informative by policy** (Phase 29
locks 3 & 4: emitted at INFO, never raises). Declaring them promotes them out of `extra` and
into `missing`-eligible fields. From then on, a vendor that *stops* sending one of them emits a
`missing` divergence that is **fatal under `strict_decode`** — the mode the live drivers run in.
Four of the five sit on `Health` / `HealthFeed`, i.e. the ops endpoints that every live run
touches first. The "coverage work, not defect repair" framing in the backlog is true about the
typing and false about the disposition.

**How to avoid:**
Decide `| None` / default **per field** against the measured baseline, under v1.7's D-NO-03
rule (scalar leaves may be `| None`; model/list links may not). Note `.subscription` is a
`dict` — under the Phase 37 field-dimension of `check_surface_types.py`, `dict[str, Any]` on an
exported class field is a gate failure, so it needs a real model or a documented exemption
(there is exactly one precedent exemption in the codebase: `UnknownFrame.raw`).

**Warning signs:**
Five fields all declared bare `str`/`int`. No live re-read of `/health/feed` in the same phase.
A `# type: ignore` or a new gate exemption added quietly.

**Phase to address:** bundle with Phase C (same package, same version bump) or split with a
named version disposition — do not leave it version-undecided.

---

### Pitfall 12: HARN-04 "repair" scope-creeps into re-testing four milestones of already-verified behavior

**What goes wrong:**
Measured now: `verification/test_matriz_sweep_snapshot.py` +
`verification/test_main_matriz_login_fail_uniformity.py` → **19 failed, 19 errors, 3 passed**.
Single root cause, unchanged since Phase 15: probes called without the `client` argument.

"Repair" sounds like fixing 38 call signatures. It is not. Those files call the probes
**directly**, and the probes have since acquired: `probe_context` / `divergence_capture`
decorators (Phase 33), Null Object decode semantics (Phase 35), typed dicts + the 6 aliases
(Phase 37), and the `byCFICode`/`bySegment` normalization fix (Phase 39). Repairing them means
re-deriving mocked expectations for behavior that has already been verified **against the live
vendor** — the weaker evidence class, at four milestones' worth of scope.

Two second-order traps:
- **Deleting the canary.** HARN-VERIF-01 warns in writing that these two files are the
  *canary* for the 33-02/33-03 `probe_context` refactor precisely because they bypass `main()`.
  Retiring them removes the only test that exercises that seam directly.
- **Deleting 3 passing assertions.** The suite is not uniformly red; a wholesale
  `git rm` throws away 3 currently-green tests.
- **Flipping CI to `pytest verification/`.** Repairing these two files removes the stated
  reason the CI list is explicit — and the immediate temptation is to enroll the directory,
  which would newly enforce **40** files that have never run in CI, with unmeasured blast
  radius, inside a debt-closeout milestone.

**How to avoid:**
Make HARN-04 a **decision with a written basis**, not a work item: for each of the two files,
state what it would assert that a currently-CI'd test does not. If the answer is "nothing", the
honest outcome is documented-accepted-debt (which is one of the two sanctioned outcomes in the
requirement text) with the canary role explicitly transferred or explicitly abandoned. Keep the
CI allowlist explicit either way; enrolling `verification/` wholesale is its own milestone.

**Warning signs:**
A plan estimating HARN-04 in minutes. A diff changing `ci.yml` from the 12-file list to
`verification/`. A `git rm` of either file with no note about the 3 passing tests or the canary.

**Phase to address:** as a checkpoint (decision), not an execution task; if the decision is
"repair", it becomes its own phase.

---

### Pitfall 13: Harness edits and live runs land in the wrong order

**What goes wrong:**
Every HARN item edits code the LIVE runs depend on (`findings.py` disposition, drift emission,
`Health`/`HealthFeed` typing). Two bad orderings, both easy to fall into:

- Harness edits land **after** the live runs → the live evidence was produced by the old
  harness, and the phase report describes behavior nobody exercised.
- Harness edits land **before** and untested → the live run is the *first* exercise of new
  harness code, against a non-reproducible external state. If the harness misbehaves, the run
  is unrepeatable and the window (market hours, DNS state) may not return.

**How to avoid:**
State the ordering in the roadmap as a decision, not an accident. Recommended: harness changes
that affect *what gets recorded* (HARN-01) land **before** the live phase with mocked
falsification tests; harness changes that affect *what gets decoded* (HARN-02) land **after**,
so the live run measures the current published contract first.

**Phase to address:** roadmap ordering.

---

### Pitfall 14: The release gate collapses because the plan attribute is wrong — for the third time

**What goes wrong:**
Phase 34's key-decision row records that both human checkpoints were authored as
`gate="blocking"` instead of `gate="blocking-human"`, and that only an explicit orchestrator
override kept them from auto-approving under `auto_advance: true` + `mode: yolo`. The recorded
follow-up — *"corregir el atributo … en el template/patrón de planes de release futuros, no
depender de que el orchestrator lo detecte cada vez"* — was never done; Phase 40 relied on the
same override again. SHAPE-01's release would be the third occurrence, and the first one where
the surrounding phase contains mostly-autonomous cleanup plans, which is precisely the context
where an override is least likely to be applied.

**How to avoid:**
Author the release plan with `gate="blocking-human"` literally. Do not co-locate the release
with autonomous plans (see Phasing). Close the Phase-34 follow-up in this milestone — it is
cheap and it is the third strike.

**Warning signs:**
`gate="blocking"` anywhere in a plan that merges or tags. A release phase with
`autonomous: true` plans in it.

**Phase to address:** Phase D.

---

## Technical Debt Patterns

| Shortcut | Immediate benefit | Long-term cost | When acceptable |
|---|---|---|---|
| `idempotent_by_title=True` on the drift branch | one-line diff; findings file stops growing | permanent, cross-run, silent loss of every *later different* drift per endpoint; inverts the product's core value | **never** — content-address the title instead |
| Relaxing P-3 (`test_finding_count_consistency`) so HARN-01 goes green | unblocks the dedupe | removes the only guard against "run reports FINDING=N having written 0" | **never** — reorder the fid allocation |
| Widening `scripts/literal_census_33.py` with a substring/`endswith` check | census runs today | re-introduces the spoofing class D-02 removed; three policy copies drift further | **never** — copy the exact-equality allowlist under a human checkpoint |
| Flipping 35-39 `nyquist_compliant: true` on a green suite | milestone audit reads clean | destroys the NOT-VALIDATED vs PARTIAL distinction; future audits inherit a false baseline | **never** |
| Marking a lock ✅ on local green without a CI line | fast audit | certifies inert guards (40 of 52 files today) | only with an explicit `NOT ENFORCED` column |
| Correcting `Instrument`/`Segment` against the 2026-07-31 frozen baseline | no live run needed | ships a "corrected" published shape that may already be stale; burns a breaking bump on possibly-wrong fields | only if the live read genuinely cannot run, and only marked provisional with a named destination |
| Patch bump for SHAPE-01 | avoids a version conversation | violates `~=` pins; breaks the 0.4.0/0.5.0/0.6.0 precedent chain | **never** — 0.7.0 |
| Renaming keys in the 6 mocked fixtures to keep the suite green | fast GREEN | a mock that agrees with the model and was never checked against the wire — the exact defect class already filed as v1.7 debt | **never** — derive from baselines |
| `git rm` the two broken matriz verification files | red goes away | loses the documented `probe_context` canary and 3 passing tests | acceptable **only** as an explicit signed retire-with-rationale, canary role reassigned |
| Enrolling `pytest verification/` in CI once matriz is repaired | "finally all tests run" | newly enforces 40 never-CI'd files inside a debt-closeout milestone | its own milestone, never a side effect |

---

## Integration Gotchas

| Integration | Common mistake | Correct approach |
|---|---|---|
| higyrus vendor host | Reading any failure as "same DNS blocker" | Record the measured exception class; `ConnectTimeout` is **not** a `ConnectError` subclass (`main_higyrus.py:678`) and takes a different branch |
| matriz `bbsa` sandbox | Assuming Phase 39's widening reached every caller | Only `main_matriz.py` was widened; `scripts/literal_census_33.py:192` and `verification/mutation_gate.py:73` were not — and the third one *must not* be |
| matriz order-entry surface | "Consistency" widening of `mutation_gate` | `_SANDBOX_HOST` staying remarkets-only is what keeps order entry fail-closed on bbsa with zero code change (T-39-02). Leave it |
| matriz market data | Running the census outside an ARG trading window | A market-closed `null` is indistinguishable from a modelling error (P-12). Record the window in the artifact header |
| market-data `/instruments`, `/segments` | Trusting the committed schema baseline as current | `_write_or_check_schema` is write-once and never overwrites on drift (D-25); these two are frozen at 2026-07-31 |
| market-data `/health`, `/health/feed` | Typing the `extra` keys without re-reading live | Declaring them makes future absence a `missing` divergence, fatal under `strict_decode` in the drivers |
| GitHub release pipeline | Assuming `<verify>` blocks run under bash | Phase 40 measured: the blocks assume bash word-splitting and fail under zsh on this machine; run them via `bash -c`. Also re-derive hard-coded tag counts (Phase 40 found the `wallets-client-v*` == 2 clause stale; real count is 1) |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---|---|---|
| Substring / `endswith` venue check in the census script | `api.remarkets.primary.com.ar.attacker.example` and `https://<confirmed-host>@attacker.example` both pass — the exact classes D-02 enumerates in `main_matriz.py:126-131` | Exact hostname equality against the shared allowlist dict, parsed with `urlsplit(...).hostname` |
| Widening `verification/mutation_gate.py` alongside the census gate | Re-arms order entry on a venue where it is currently refused by construction | Explicit test asserting `mutation_gate._SANDBOX_HOST` does **not** admit bbsa |
| Adding a venue without a human checkpoint | Milestone prohibition P-05; the codebase says so in-line | Blocking human checkpoint before any network call, recorded in the code comment + phase report (the Phase 39 D-02 pattern) |
| Interpolating the resolved base URL into a SKIP line | Leaks the input datum the policy verdict is about (T-39-04) | `_HOST_SKIP_LINE` is a literal on purpose — keep it literal |
| A live re-probe that prints credentials or resolved hosts on the new failure path | Credential/host leak on an untested branch | Route every new print through `safe_print(..., secrets=[...])`; the `ConnectTimeout` branch (if added) needs the same treatment as `ConnectError` |

---

## "Looks Done But Isn't" Checklist

- [ ] **LIVE-01 closed:** measured exception type recorded verbatim *and* the 22 triples
      (`Movimiento` 9 / `PosicionValuada` 11 / `Posicion` 2) contrasted — or an explicit
      "not measured because X". Not "re-probed, still blocked".
- [ ] **LIVE-02 closed:** census artifact header names the **venue** (bbsa ≠ remarkets) and the
      **time window**, and states that D-lock (b) remains in force. The `29-DLOCK` paragraph
      correction is routed to its signatory.
- [ ] **Venue policy:** all three copies inspected; census gate == driver allowlist by exact
      equality; `mutation_gate` untouched; a test pins all three; the ROADMAP sentence that
      overstated readiness is corrected.
- [ ] **NYQ-01:** every row has one of three dispositions, zero undisposed; every ✅ names its
      CI enforcement surface; the `NOT ENFORCED` count is reported as a first-class finding.
- [ ] **NYQ-01:** `status`/`nyquist_compliant` front-matter reflects what was actually
      re-verified, not what was convenient for the audit to read.
- [ ] **SHAPE-01:** fresh live read exists and postdates the 2026-07-31 baseline, or the
      correction is marked provisional.
- [ ] **SHAPE-01:** all 6 mocked fixtures re-derived from the baselines, plus a
      fixture-⊆-baseline assertion so the next fabricated fixture fails.
- [ ] **SHAPE-01:** sync **and** async surfaces mirrored, mocked regression per corrected
      field (the standing project convention).
- [ ] **SHAPE-01:** `0.7.0` across all 4 version sites; README `### v0.7.0` with an old→new
      migration table; docstring block **appended** below the Phase 33/36/40 record; truthiness
      flip called out (`Segment` rows go from always-truthy-with-empty-strings to falsy-when-empty).
- [ ] **SHAPE-01:** the 4 CI gates re-run green without any rule loosened —
      `check_decode_intactness.py`, `check_uniform_structure.py`, `check_surface_types.py`
      (incl. the Phase 37 field dimension), `surface_parity.py`.
- [ ] **HARN-01:** falsification test proves a *different* drift on the same endpoint still
      writes a new block. P-3 untouched and green.
- [ ] **HARN-02:** per-field `| None` decision recorded against measured evidence;
      `.subscription` modelled, not `dict[str, Any]`; version disposition named.
- [ ] **HARN-04:** written basis for repair-vs-retire; the 3 passing tests accounted for; the
      canary role reassigned or explicitly abandoned; CI allowlist still explicit.
- [ ] **Release:** `gate="blocking-human"` literal; two independent approvals; annotated tags
      on a real two-parent merge commit; post-publish install from the public wheel;
      `<verify>` blocks run under `bash -c` and their hard-coded counts re-derived.

---

## Recovery Strategies

| Pitfall | Recovery cost | Recovery steps |
|---|---|---|
| Drift dedupe already swallowed a real divergence | **HIGH** | Nothing in the findings file records the loss. Recover only by re-running the driver against a fresh wire read and diffing against the frozen baseline manually; assume the intervening period is uncensused |
| `nyquist_compliant` flags flipped without evidence | MEDIUM | Revert the front-matter; re-do as an evidence table. The commit is recoverable, the lost distinction is not once a later audit consumes it |
| SHAPE-01 published on a stale/wrong shape | **HIGH** | Another source-breaking bump (0.8.0) with another double human gate and another migration table; consumers migrate twice. This is why the fresh read must precede the fix |
| Census gate widened with a substring check and shipped | MEDIUM | Revert to exact equality, add the three-copy test, re-run the census — the census output itself stays valid if the host it hit was in fact the allowlisted one (verify, don't assume) |
| P-3 relaxed to unblock HARN-01 | LOW-MEDIUM | Restore the assertion, move the fid allocation after the dedupe decision, re-run. Cheap *if* caught in-cycle; expensive if a driver ran and over-reported in between |
| Matriz `verification/` files deleted, canary lost | LOW | Restore from git; the real cost is that the retire decision now needs re-litigating with the canary argument on the table |
| Release gate auto-approved under yolo | **HIGH / irreversible** | A published GitHub Release cannot be unpublished cleanly. Recovery is a follow-up release + changelog correction (the Phase 34 PR #13 precedent) |

---

## Phasing Recommendation (for roadmap construction)

**Do not bundle all four groups into one "cleanup" phase.** The groups differ on the two axes
that determine phase boundaries in this project: *reversibility* and *evidence class*.

| Group | Own phase? | Rationale |
|---|---|---|
| **LIVE-01 + LIVE-02** | **Yes — own phase** | Non-deterministic and externally gated (DNS, market hours, venue policy). Needs a blocking human checkpoint *before* any network call (venue widening, P-05). Its output is evidence, not code. Bundling it with deterministic work means one flaky external dependency stalls unrelated plans |
| **NYQ-01** | **Yes — own phase, and run it FIRST** | It audits a *frozen* v1.7 state. If it runs after SHAPE-01 or HARN-*, it audits a moving target and its findings become unattributable. It is also the only group that must produce zero source changes — mixing it with source work contaminates the audit |
| **SHAPE-01 (+ HARN-02)** | **Yes — own phase, stopping SHORT of publish** | Source-breaking on a published wheel; needs an operator disposition that 33-07 explicitly withheld, sync/async mirroring, mocked regressions, 6 fixture rewrites, and 4 CI gates green |
| **Release of `market-data-client` 0.7.0** | **Yes — own phase** | Locked precedent: Phases 24, 28, 34, 40 were each their own phase because *"el release tiene doble gate humano y no puede compartir fase con la verificación que lo habilita"* (v1.7 roadmap decision). Co-locating it with autonomous cleanup plans is the exact context in which the `gate="blocking"` authoring bug (Pitfall 14) collapses a gate |
| **HARN-01 / HARN-03** | **Bundle** — into the NYQ phase or a small cleanup phase | Small, deterministic, mocked-testable. HARN-01 is *not* trivial (Pitfalls 9-10) but it is fully offline |
| **HARN-04** | **Not a work item — a checkpoint** | It is a repair-vs-retire *decision*. Put it as a `checkpoint:decision` with a written basis. Only if the decision is "repair" does it become its own phase |

**Recommended order and why:**

1. **NYQ-01** — audits frozen v1.7 state; must precede any source change.
2. **LIVE-01 + LIVE-02** — and, critically, take the **fresh live read of `/instruments` and
   `/segments`** in this same phase. That read is SHAPE-01's evidence base (Pitfall 8), so live
   must precede shape.
3. **SHAPE-01 (+ HARN-02)** — fix, mirror, regress, gates green; stop short of publish.
4. **Release 0.7.0** — double independent human gate, `gate="blocking-human"` literal.
5. **HARN-01 / HARN-03** — interleave with 1 or 3; HARN-01 lands *before* the live phase if you
   want the live run to exercise the new drift behavior (Pitfall 13 — decide this explicitly).

**Deepest-research flag:** SHAPE-01 and HARN-01 are the two items whose naive one-line
implementation is actively harmful. Both warrant a discuss-phase with the operator before
planning. LIVE-02 warrants one too, but for policy (venue widening), not design.

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention phase | Verification |
|---|---|---|
| 1 — LIVE-01 resolved on a different cause | Phase A (live) | Phase report contains the verbatim exception class + the 22-triple contrast or a named non-measurement |
| 2 — stale census venue gate, unsafe quick-fix | Phase A, behind a human checkpoint | Test pinning census allowlist == driver allowlist and `mutation_gate` exclusion; ROADMAP sentence corrected in the same commit |
| 3 — census read as license to promote `Literal` | Phase A | No diff to `matriz_client/types.py`; census header names venue + window + re-affirms D-lock (b) |
| 4 — retroactive validation that grades to the artifact | Phase B (NYQ) | Every row disposed into one of 3 buckets; `40-VERIFICATION.md` (live-state re-confirmation) used as the bar |
| 5 — local green certifying an inert lock | Phase B | Enforcement column per row; `NOT ENFORCED` count reported (expect ≫ 0 against 40 non-CI'd files) |
| 6 — shape change skipping the release ceremony | Phase C + Phase D | Changelog + migration table authored *before* the model edit; 4 version sites; 2 independent approvals |
| 7 — fabricated mocked fixtures preserved | Phase C | Fixture-⊆-baseline assertion added and proven to fail on a fabricated fixture |
| 8 — corrected against a frozen 2026-07-31 baseline | Phase A → Phase C | Fresh read timestamp postdates the baseline, cited in the plan |
| 9 — drift dedupe loses census | Phase B / harness | Falsification test: different drift, same endpoint, still writes |
| 10 — P-3 relaxed | same phase as 9 | `test_finding_count_consistency.py` byte-unchanged and green |
| 11 — `extra` typing flips disposition to fatal | Phase C | Per-field `\| None` decision recorded; live `/health/feed` read in the same cycle; no new gate exemption |
| 12 — HARN-04 scope creep / canary loss | checkpoint | Written repair-vs-retire basis; CI allowlist still explicit; 3 passing tests accounted for |
| 13 — harness/live ordering | roadmap ordering | Ordering stated as a decision in the roadmap, not inferred |
| 14 — release gate collapse (3rd occurrence) | Phase D | `gate="blocking-human"` literal in the plan; Phase-34 template follow-up closed |

---

## Sources

**Primary — direct measurement of this repository at `e55398d`** (HIGH confidence; each claim
was produced by reading the file or running the command cited inline):

- `verification/findings.py:583-700` — `append_finding` ordering: title-dedupe **before**
  human-status preservation and before the fid path
- `verification/test_finding_count_consistency.py` (docstring) — property P-3 and its explicit
  statement that `_write_or_check_schema` shares the hazard
- `verification/test_findings_fid_seed.py` (docstring) — why `idempotent_by_title` does not
  substitute for a seeded allocator
- `main_market_data.py:470-522` — write-once schema baseline (D-25), drift title
  `schema drift en {client_function}`
- `main_matriz.py:116-160` — `_VENUE_ALLOWLIST`, exact-equality rationale, P-05 prohibition,
  the explicit "`mutation_gate.py` NO se toca" note
- `scripts/literal_census_33.py:192` — **still** `if "remarkets" not in base:` (substring)
- `verification/mutation_gate.py:73` — `_SANDBOX_HOST` remarkets-only
- `main_higyrus.py:669,678` — `ConnectError` branch; `ConnectTimeout` explicitly excluded
- `packages/market-data-client/src/market_data_client/models.py:787-814, 455-500` —
  `Instrument`/`Segment` declared shape; the D-12 additive-docstring precedent
- `packages/market-data-client/src/market_data_client/_core.py:1035-1075` — the deliberately
  unfixed half of S-1 and its routing to `SHAPE-MD-REF-33`
- `packages/market-data-client/README.md:110-175` — v0.6.0 / v0.5.0 changelog + migration-table
  format; version sites at `:15`, `:24`, `pyproject.toml:3`, `__init__.py:163`
- `packages/market-data-client/tests/test_reference_{client,async_client,core,models,envelope_unwrap}.py`,
  `tests/test_decode.py` — the 6 fixtures encoding the fabricated shape
- `.planning/verification/schemas/market-data-client/get-{instruments,segments}.json` —
  `captured_at: 2026-07-31`
- `.github/workflows/ci.yml` — 4 gate steps; the 12-file explicit `verification/` allowlist and
  its "cada guard nuevo se agrega a esta lista a mano" comment; `ls verification/test_*.py | wc -l` = 52
- `uv run pytest verification/test_matriz_sweep_snapshot.py verification/test_main_matriz_login_fail_uniformity.py`
  → **19 failed, 3 passed, 19 errors**
- `.planning/milestones/v1.7-phases/*/[35-40]-VALIDATION.md` — front-matter status lifecycle;
  39-VALIDATION.md's Manual-Only rows and the WR-01 inert-lock Wave-0 requirement
- `.planning/PROJECT.md` § Key Decisions — D-08/D-18 double gate, D-09 count-based CI gate,
  Phase 34 `gate="blocking"` authoring bug and its unclosed follow-up, Phase 39 D-02, the
  `40-VERIFICATION.md` retroactive-verification bar
- `.planning/ROADMAP.md` § Backlog — `LIVE-HIGY-33`, `LIVE-MATZ-33`, `SHAPE-MD-REF-33`,
  `HARN-DRIFT-33`, `TYP-MD-EXTRA-33`, `HARN-VERIF-01`
- `.planning/STATE.md` § Blockers/Concerns and § Decisions (Phase 40 zsh/`<verify>` and stale
  tag-count findings)

**Secondary — web (LOW confidence per `classify-confidence --provider websearch`; used only to
confirm that the project's existing conventions match the wider norm, never to override them):**

- SemVer 0.x in practice is `0.INCOMPATIBLE.COMPATIBLE`; breaking on a 0.x line takes a minor
  bump, and a rename without a deprecation window strands consumers — consistent with this
  project's 0.4.0/0.5.0/0.6.0 precedent. [semver #411](https://github.com/semver/semver/issues/411),
  [pandas policies](https://pandas.pydata.org/docs/development/policies.html),
  [Real Semantic Versioning](https://kidger.site/thoughts/real-sem-ver/)
- Retroactive/backfilled audit evidence is a weaker evidence class than contemporaneous
  system-generated records; the mitigations are deriving evidence from immutable system output
  and hash-linking so retroactive modification is detectable.
  [Adherent](https://www.adherent.com/blog/beyond-the-binder-building-an-audit-ready-compliance-evidence-system-that-stands-up-in-court/),
  [Scrut](https://www.scrut.io/post/audit-evidence-documentation-reporting)

---
*Pitfalls research for: v1.8 backlog closeout (market-libs)*
*Researched: 2026-08-31 against working tree `e55398d`*
