---
phase: 38
slug: iol-client-auditor-a-de-higyrus-mbito-wallets
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-29
---

# Phase 38 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register authored at plan time in the four PLAN.md `<threat_model>` blocks
> (`38-01` T-38-01..05, `38-02` T-38-06..10, `38-03` T-38-11..14, `38-04` T-38-15..19,
> plus `T-38-SC` declared once per plan). This audit verifies each declared
> disposition against the implemented tree — it does not scan for new threats.

**Audit method.** Every row below was closed by an independently executed command or
probe run by the auditor at `HEAD = a75adc0`, not by reading `38-VERIFICATION.md` or a
SUMMARY claim. Where a mitigation's evidence was a runtime behaviour, the auditor wrote
and ran its own probe rather than trusting the phase's own test names.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| upstream IOL wire JSON → `_decode.walk_model` | The only untrusted input in this phase's blast radius. Phase 38 changes what the walker is asked to produce for two fields; it does not change the walker. | Untrusted vendor JSON |
| repository source tree → CI `lint` job | `tools/check_surface_types.py` executes in CI over every file under `packages/`. Anything it does at scan time (an import, an `eval`, a filesystem read outside `packages/`) runs with the CI job's environment and credentials. | Source files, CI env |
| the ratchet control → future contributors | The gate is a *control*. Weakening it is the attack, and it looks exactly like a routine fix. | Gate verdicts |
| repository working tree → later phases | Derived artifacts (surface snapshot) and committed evidence (wire schema captures, `35-RETIRED-TRIPLES.md`, `38-CENSUS.md`) are consumed as ground truth by Phases 39/40. | Audit records, counts |
| introspection tooling → per-package `.env` | Enumerating higyrus's fields by *importing* the package would run `load_dotenv()` and construct an HTTP client. | Credentials |
| repository documentation → downstream consumers | The iol README is what a consumer installing from `main` reads to decide whether their code still works. | Breaking-change disclosure |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Verification Evidence (auditor-executed) | Status |
|-----------|----------|-----------|----------|-------------|------------------------------------------|--------|
| T-38-01 | Tampering | `_decode` input-validation boundary (ASVS V5) | high | mitigate | **Walker frozen:** `tools/check_decode_intactness.py` exit 0 (Checks A-D, 5 copies → one hash `a1f00c824348164c`); `git diff --name-only c45aa64..HEAD -- .../_decode.py` empty. **Silence is licensed only for null/absent** — auditor probe on the committed corpus rows: `puntas=None` and `puntas` absent → 0 divergence records and no raise under `STRICT_DECODE=True`, for both `Cotizacion` and `Titulo`. **Wrong-typed still fires** — `{**row, "puntas": 7}` emits a divergence with all 6 record keys present (`Cotizacion` → `divergence='type' declared='list' observed='int' field_path='.puntas'`; `Titulo` → `divergence='non_dict' declared='Punta' observed='int'`) and raises `IOLDecodeError: decode divergence in Cotizacion.puntas: declared list, observed int` under `strict_decode`. No coercion was added. | closed |
| T-38-02 | Repudiation | `.planning/verification/schemas/iol-client/get-historical-quotes.json` | medium | mitigate | **Wire capture not rewritten:** `git log -1` on the file → `fd7ab43` (Phase 06); the file appears in no Phase-38 commit; `git status --porcelain .planning/verification/schemas/` empty. **Drift absorbed in EXPECTED with stated cause:** `packages/iol-client/tests/test_models.py:379` — `esperado = {**_committed_schema("get-historical-quotes")[0], "puntas": []}`, with the cause written at `:370-377` ("la deriva se absorbe acá, en el valor ESPERADO, con la causa dicha"). | closed |
| T-38-03 | Tampering | `verification/snapshots/iol-client-surface.txt` | medium | mitigate | **Diff bounded:** `git diff --stat c45aa64..HEAD` → `2 insertions(+), 2 deletions(-)`, exactly the two `puntas` annotation tokens (`list[Punta] \| None`→`list[Punta]`, `Punta \| None`→`Punta`). **Not hand-edited:** auditor re-ran `uv run python verification/regen_snapshots.py`; `git status --porcelain verification/snapshots/` empty afterwards — the committed file is byte-identical to generator output. | closed |
| T-38-04 | Information Disclosure | `iol_client` logger (ASVS V7) | low | accept | See `AR-38-01`. Rationale verified in its load-bearing direction: record emitter is inside the byte-frozen `_decode.py`; shape is the 6 flat all-str keys `_RECORD_KEYS` (`_decode.py:92-99`), confirmed 6/6 present at runtime; only type names and a `_safe_key`-neutralized path reach a record, never a payload value (`_decode.py:346-366`). `verification/test_logging_no_token_leak.py` untouched by Phase 38 (last commit `042bcbd`, Phase 30) and **5 passed**. Auditor measured emission volume pre- vs post-38 on a populated-but-defective book: **delta = 0** in every case constructed (see Note 1). | closed (accepted) |
| T-38-05 | Spoofing / Elevation | iol OAuth flow, `IOL_USER` / `IOL_PASSWORD` | high | accept | See `AR-38-02`. Verified out of blast radius: `models.py` is the only source file in the 38-01 diff (`3f67e20`/`f93cb2a`/`6ffdc15` touch only `models.py`, two test files, the snapshot and `.planning/`). Its 48/15 line churn reduces to **two annotation lines**; everything else is docstring prose. A credential-pattern grep over the entire Phase-38 source diff (`packages/ tools/ verification/ main_*.py`) for `password\|secret\|token\|api_key\|credential\|load_dotenv\|getenv\|os.environ\|bearer\|IOL_USER\|IOL_PASSWORD` returns only two docstring lines in `check_surface_types.py` explaining why the gate never imports a package. | closed (accepted) |
| T-38-06 | Tampering | the ratchet control (`tools/check_surface_types.py`) | high | mitigate | **No exemptions added:** `git diff c45aa64..HEAD -- tools/check_surface_types.py \| grep -c '^+.*_FIELD_EXEMPTIONS\['` → `0`; the only `+` lines matching `exempt` are prose. **No bound lowered:** the diff has exactly 5 deletions, all refactor lines from widening `_adjudicate_field` into a two-predicate OR; no numeric assertion decreased. Floors are strengthened, not weakened (`assert result.fields >= 400` added). **matriz untouched:** `git diff --name-only c45aa64..HEAD -- packages/matriz-client/` empty, incl. its `test_surface_types_red.py`. **Over-narrowing detectable:** both spare-side fixtures present and passing (`test_an_optional_literal_alias_field_is_spared`, `test_an_optional_list_of_any_field_is_spared`); `pytest packages/iol-client/tests/test_surface_types_red.py -q` → **16 passed**. | closed |
| T-38-07 | Information Disclosure / Elevation | CI `lint` job env, per-package `.env` (ASVS V14) | high | mitigate | **AST-verified, not grep-verified** (a grep would be fooled by the file's own prose about `issubclass`). Auditor parsed the gate with `ast` and enumerated every `Import`/`ImportFrom` node: `[(228,'__future__'), (230,'ast'), (231,'sys'), (232,'collections.abc'), (233,'dataclasses'), (234,'pathlib')]` — six stdlib nodes, **zero package imports at any scope**. Dangerous-call scan over all `ast.Call` nodes: `eval`/`exec`/`compile`/`__import__`/`issubclass`/`getattr`/`open` → **empty set**. The three textual `get_type_hints`/`issubclass` hits (lines 28-29, 753) are docstrings stating why they are *not* used. No `importlib`, `subprocess`, or `os.system` anywhere. `load_dotenv()` therefore cannot run in the lint step. | closed |
| T-38-08 | Denial of Service | CI `lint` job runtime | low | accept | See `AR-38-03`. Rationale verified: AST loop audit of the gate → **zero `While` nodes**, 16 `For` nodes all over finite iterables; the re-export chain is bounded by `for _ in range(_MAX_RESOLUTION_HOPS)` with `_MAX_RESOLUTION_HOPS = 8` (`:322`, `:927`). The `rglob("*.py")` at `:793` is confined to `import_root` = `packages/<pkg>/src/<pkg>/`, derived from `packages_dir.iterdir()` (`:1112`) — no read outside `packages/`. The anti-vacuity guard at `:1113-1117` fails loudly on an empty `packages/` rather than reporting green. | closed (accepted) |
| T-38-09 | Repudiation | the gate's summary line | medium | mitigate | **Live gate output, auditor-executed:** `uv run python tools/check_surface_types.py` → `6 packages, 186 __all__ names, 336 definitions scanned, 442 fields scanned, 13 constant/alias exports, 24 exempted (dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1), 0 violations`, exit 0 — the exemption taxonomy is verbatim the string the plan asserted unchanged. **Vacuous green is mechanically impossible:** `test_gate_is_green_on_the_real_tree` asserts floors `packages >= 6`, `definitions >= 300`, `fields >= 400`, `exempted >= 20` (`test_surface_types_red.py:106-110`), all satisfied with margin at 442. | closed |
| T-38-10 | Spoofing | none | low | accept | See `AR-38-04`. Verified rather than assumed: no identity, session, or token construct appears in the Phase-38 source diff (same credential-pattern grep as T-38-05 → zero non-prose hits). No auth file is in the phase's changed-file list. | closed (accepted) |
| T-38-11 | Repudiation | `packages/iol-client/README.md` breaking disclosure | medium | mitigate | **Runtime consequence named, not just the type change:** `README.md:28-35` states that `Titulo.puntas` goes `None → Punta.empty()` and that a consumer branching by identity against nothing (`if titulo.puntas is None:`, `assert titulo.puntas is None`) **"deja de tomar esa rama, en silencio"** — and explicitly that it "no rompe el build y mypy no dice una palabra… Es la mitad de la ruptura que ninguna herramienta atrapa". The asymmetry between the two rows is stated at `:20-22`; the migration table is at `:14-17`; the callout is the first `##` section (`:5`). `:41-42` additionally re-states that a wrong-typed `puntas` still emits and still raises. | closed |
| T-38-12 | Tampering | `35-RETIRED-TRIPLES.md` (Phase 39's subtraction input) | high | mitigate | **All-six-or-none stale-reference check passes:** exactly six `iol_client/models.py:NNN` references exist (lines 68 ×2, 152 ×2, 270, 271) and all six read `:235` / `:334`, which resolve at HEAD (`models.py:235 puntas: list[Punta]`, `:334 puntas: Punta`). Zero stale refs remain. **Phase-35 row set not rewritten:** the four diff hunks are at `@@ -28`, `@@ -65`, `@@ -149`, `@@ -239`; the only main-table line touched is the `iol-client` *explicit-zero* row (a reference correction anchored to `242b9f3`), never one of the 35 retired field rows. The `35 field rows` / D-17 invariant text (`:52`, `:95`) does not appear on either side of the diff. **Delimited addendum:** `grep -c '^## Phase 38 addendum$'` → `1` (at `:253`), and hunk `@@ -239,3 +247,65 @@` is a pure append. | closed |
| T-38-13 | Repudiation | `.planning/verification/<pkg>-findings.md` auto-generated ledgers | medium | mitigate | `git status --porcelain .planning/verification/` empty, **and** — stronger than the declared criterion — no path under `.planning/verification/` appears anywhere in `git diff --name-only c45aa64..HEAD`. The run-scoped marker/ID/Status schema was never opened. | closed |
| T-38-14 | Information Disclosure | README content | low | accept | See `AR-38-05`. Verified: the README diff's `+` lines contain no `password`/`secret`/`apikey`/`bearer`/`IOL_USER`/`IOL_PASSWORD`/`.env`/`localhost`/`127.0.0.1`, and add **zero URLs** of any kind. Only public type signatures and the public tag `iol-client-v0.3.0`. | closed (accepted) |
| T-38-15 | Repudiation | `38-CENSUS.md` as an audit record | medium | mitigate | **Command-plus-verbatim-output form present:** `## SC-3 closing evidence — commands executed, output verbatim` (`:268`) carries Grep 1 (`:274-298`) and Grep 2 (`:300`) as literal ```bash``` blocks with their full pasted output, plus the four suite `-q` tails (`:335`) and the gate invocation (`:29`). **No-estimates provenance paragraph present:** `## Method and limits — no number in this file is an estimate` (`:364-388`) names all four producing runs. **Numbers are reproducible, not asserted:** the auditor independently re-derived the higyrus population with its own stdlib-`ast` scan → `142` total fields, `15` field-carrying classes, `10` model links, `0` optional-bearing, `0` mapping — exact agreement with the census, and `142 − 131` scalar leaves (`:115`) = the 11 link/collection rows of Table A. | closed |
| T-38-16 | Repudiation | the vacuous-green failure mode | high | mitigate | **Every zero declared by enumeration with its cause:** `## The enumerated zeros` (`:208`) with `### ambito-financiero-client — zero by enumeration, not zero by cleanliness` (`:210`) and `### wallets-client — zero by enumeration, and a stub besides` (`:235`); the phrase `zero by enumeration` also carries the mapping-field zero (`:76`) and the wallets domain-return zero (`:154`). **Wallets green carries its qualification:** `:262` — "wallets' `0 violations` is a **zero by enumeration** over an empty population, twice over", with `__all__` (`__init__.py:22-28`) cited as 4 exception classes plus `configure` and no domain function. **Full candidate population enumerated:** Tables A + B enumerate all 142 higyrus fields, not only violations. | closed |
| T-38-17 | Tampering | `.planning/verification/<pkg>-findings.md` auto-generated ledgers | medium | mitigate | The census was written as its own file (`38-CENSUS.md`, 426 lines) inside the phase directory. `.planning/verification/` is absent from the phase's full changed-file list and `git status --porcelain` on it is empty. The census states the reason itself at `:386-388` (run-scoped marker schema, OPEN→FIXED lifecycle, D-07). | closed |
| T-38-18 | Information Disclosure | per-package `.env` credentials (ASVS V14) | high | mitigate | **Introspection never imported the package:** the census records the method at `:379-383` ("parsing the module with stdlib `ast`, deliberately **not** by importing `higyrus_client` and **not** by `get_type_hints`"). The auditor did not take this on trust — it re-derived every headline higyrus number from `ast.parse()` alone with `higyrus_client` confirmed absent from `sys.modules`, reproducing `142/15/10/0/0` exactly. `load_dotenv()` therefore never ran. **No credential value recorded:** auditor grep of the census for `password\|secret\|api_key\|bearer\|token\|IOL_/HIGYRUS_/MATRIZ_/AUTH0\|client_secret\|base64-shaped blobs` returns only file paths, type annotations and the prose sentence describing the `.env` discipline itself. **Snippet not committed:** no new `tools/` file in the phase diff. | closed |
| T-38-19 | Tampering | unsourced counts propagating from prior artifacts | medium | mitigate | `## Discrepancies named rather than absorbed` (`:346`) writes the **measured** number with its producing command in each case: row 1 — CONTEXT D-11 says 11 matriz `Literal`-alias optional leaves but lists 10 line numbers; the census writes **10** (`532,552,553,561,607,619,660,661,662,669`) with the grep output pasted. Row 2 — CONTEXT D-09's taxonomy is corrected to the run's verbatim `dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1`, noting the module-level `_request` shims are out of the candidate set, not exempted. Row 4 corrects a shifted README line range. Auditor re-ran Grep 1 independently → 10 lines, matching. | closed |
| T-38-SC | Tampering | `uv`/PyPI supply chain | low | accept | See `AR-38-06`. Verified across the phase's **full** commit range: `git diff --name-only c45aa64..HEAD -- uv.lock` → empty, and `-- '*pyproject.toml'` → empty. Zero package-manager installs; no new dependency and no version string moved. The single lockfile refresh remains Phase 40's. | closed |

*Status: open · closed · closed (accepted)*
*Severity: critical > high > medium > low — only open threats at or above `workflow.security_block_on` count toward `threats_open`*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

**Totals:** 20 threats — 14 `mitigate` (all closed), 6 `accept` (all logged below). `threats_open: 0`.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-38-01 | T-38-04 | The divergence channel's shape cannot grow: the emitter lives in a byte-frozen `_decode.py` and every record is the same six flat all-str keys (`package`, `divergence`, `field_path`, `declared_type`, `observed_type`, `model`). Only type names and a `_safe_key`-neutralized path ever reach a record; no payload value does. `test_logging_no_token_leak.py` pins that no credential reaches a log line and was untouched by this phase. Measured emission volume is never greater post-38 than pre-38. | sebadlf (operator, via UAT approval 2026-08-29T22:04:57Z covering the phase diff) | 2026-08-29 |
| AR-38-02 | T-38-05 | The iol OAuth flow and `IOL_USER`/`IOL_PASSWORD` are outside this phase's blast radius. `models.py` is the only source file in the 38-01 diff and its only executable change is two type annotations. No auth code, no `.env` read, no credential path was touched anywhere in the phase. | sebadlf (operator, via UAT approval) | 2026-08-29 |
| AR-38-03 | T-38-08 | `_class_names` adds one bounded `rglob("*.py")` + parse pass per package over a committed tree of a few hundred files, confined to `packages/<pkg>/src/<pkg>/`. The gate contains zero `while` loops and its only chain-following loop is capped at `_MAX_RESOLUTION_HOPS = 8`. A pathological input would have to be committed first, at which point the existing anti-vacuity guards fail loudly rather than looping. CI-runtime cost is accepted as negligible. | sebadlf (operator, via UAT approval) | 2026-08-29 |
| AR-38-04 | T-38-10 | No identity, session, or token construct is involved anywhere in this phase. Trivially closed; recorded so the STRIDE register has no silent omission. | sebadlf (operator, via UAT approval) | 2026-08-29 |
| AR-38-05 | T-38-14 | The iol README carries no credential, no endpoint secret and no internal hostname. Phase 38 added only public type signatures, a migration table and a reference to the public tag `iol-client-v0.3.0` — zero URLs added. | sebadlf (operator, via UAT approval) | 2026-08-29 |
| AR-38-06 | T-38-SC | Phase 38 performs no package-manager install: `uv.lock` and every `pyproject.toml` are byte-identical across the phase's full commit range. No third-party package legitimacy audit is applicable because no dependency entered or moved. Phase 40 owns the single coordinated lockfile refresh and version bump. | sebadlf (operator, via UAT approval) | 2026-08-29 |

---

## Notes and Residual Observations

**Note 1 — T-38-04's rationale is directionally right but imprecise (documentation nit, not a gap).**
The plan-time text claims the phase "emits strictly FEWER records than before". The auditor
measured this rather than accepting it, comparing the pre-38 shape (`list[Punta] | None`,
`Punta | None`) against the post-38 shape under the same frozen walker:

- `puntas` null/absent — pre-38: 0 records (walker `Union` early return); post-38: 0 records
  (NOBJ-02 collapse arms). **Equal, not fewer.**
- `puntas` populated but internally defective — pre-38: 4 records; post-38: the **same 4**
  records, identical `field_path`/`declared_type`/`observed_type` triples. The `Optional`
  wrapper only short-circuits on a `None` *value*, so de-Optionalizing does not open a new
  descent path into `Punta` elements. **Delta = 0.**

The correct statement is "never more", not "strictly fewer". The security-load-bearing half of
the rationale — the leak surface cannot grow — is verified and holds. No action required; recorded
so a future reader does not treat "strictly fewer" as a measured fact.

**Note 2 — the phase's largest new executing surface is the CI gate, and it is fully mapped.**
`tools/check_surface_types.py` gained 206 lines that run in the CI `lint` job. This is genuinely
new executing code, but it is not unregistered attack surface: T-38-06 (weakening), T-38-07
(credential read via import), T-38-08 (runtime) and T-38-09 (vacuous green) cover it, and all four
were closed against AST-level evidence rather than grep.

---

## Unregistered Flags

**None.** All four `38-0N-SUMMARY.md` files declare `## Threat Flags` → "Ninguna superficie
nueva." The auditor cross-checked this against the phase's actual changed-file list rather than
accepting the declaration:

| Changed path | Mapped to |
|---|---|
| `packages/iol-client/src/iol_client/models.py` | T-38-01, T-38-05 |
| `packages/iol-client/tests/{test_models,test_null_object,test_surface_types_red}.py` | T-38-02 (EXPECTED override), T-38-06/09 (gate fixtures) — test-only |
| `packages/iol-client/README.md` | T-38-11, T-38-14 |
| `tools/check_surface_types.py` | T-38-06, T-38-07, T-38-08, T-38-09 |
| `verification/snapshots/iol-client-surface.txt` | T-38-03 |
| `.planning/phases/35-.../35-RETIRED-TRIPLES.md` | T-38-12 |
| `.planning/phases/38-.../38-CENSUS.md` | T-38-15, T-38-16, T-38-17, T-38-18, T-38-19 |
| `.planning/{REQUIREMENTS,ROADMAP,STATE}.md`, phase artifacts | workflow bookkeeping, no surface |
| `uv.lock`, `*/pyproject.toml` | **not changed** — T-38-SC |

No path in the phase diff lacks a mapping. No network path, endpoint, auth flow, user-input
handler, or dependency entered the tree.

---

## Gate Evidence (auditor-executed at HEAD `a75adc0`)

| Command | Result |
|---|---|
| `uv run python tools/check_surface_types.py` | exit 0 — `442 fields scanned`, `24 exempted (dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1)`, `0 violations` |
| `uv run python tools/check_decode_intactness.py` | exit 0 — Checks A/B/C/D pass, canonical digest `a1f00c824348164c` |
| `uv run python tools/check_uniform_structure.py` | exit 0 |
| `uv run --package iol-client pytest packages/iol-client -q` | `293 passed` |
| `uv run --package iol-client pytest packages/iol-client/tests/test_surface_types_red.py -q` | `16 passed` |
| `uv run pytest verification/test_logging_no_token_leak.py -q` | `5 passed` |
| `uv run mypy packages/iol-client` | `Success: no issues found in 30 source files` |
| `uv run ruff check tools/check_surface_types.py packages/iol-client` | `All checks passed!` |
| `uv run python verification/regen_snapshots.py` then `git status --porcelain verification/snapshots/` | empty — snapshot is machine-reproducible |
| `git status --porcelain` (whole tree) | empty |
| `git diff --name-only c45aa64..HEAD -- uv.lock '*pyproject.toml'` | empty |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-29 | 20 | 20 | 0 | gsd-security-auditor (adversarial verification against the implemented tree at `a75adc0`; register authored at plan time in the four PLAN.md `<threat_model>` blocks; ASVS L1. Every row closed by an auditor-executed command, AST parse, or purpose-written runtime probe — no row closed on the strength of `38-VERIFICATION.md` or a SUMMARY claim. Two custom probes were written for T-38-01 and T-38-04; the higyrus census population was independently re-derived for T-38-15/T-38-18.) |

---

## Sign-Off

- [x] All 20 threats have a disposition (14 mitigate / 6 accept / 0 transfer)
- [x] All 14 `mitigate` threats closed against located, executed evidence
- [x] All 6 `accept` threats recorded in the Accepted Risks Log (AR-38-01..06)
- [x] No implementation file modified by this audit
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-29
