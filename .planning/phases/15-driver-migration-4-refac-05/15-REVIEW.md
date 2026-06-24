---
phase: 15-driver-migration-4-refac-05
reviewed: 2026-06-24T00:00:00Z
depth: deep
files_reviewed: 8
files_reviewed_list:
  - main_ambito_financiero.py
  - main_iol.py
  - main_higyrus.py
  - main_matriz.py
  - verification/test_main_ambito_financiero_uses_single_client_instance.py
  - verification/test_main_iol_uses_single_client_instance.py
  - verification/test_main_higyrus_uses_single_client_instance.py
  - verification/test_main_matriz_uses_single_client_instance.py
findings:
  blocker: 0
  warning: 3
  info: 2
  total: 5
status: issues
---

# Phase 15: Code Review Report

**Reviewed:** 2026-06-24
**Depth:** deep (cross-file: driver ↔ package client/_core ↔ AST-guard tests)
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 15 migrated the four verification drivers (ambito, iol, higyrus, matriz) to
thread a single sync `Client()` and a single async `AsyncClient()` through every
`probe_*`, replacing `_get_default()` / `pkg.get_X(...)` singleton call sites with
threaded-instance calls, and replacing module-level `_request` shims with instance
`client._request(RequestSpec(...))` + explicit raise.

Three of the four drivers (**ambito, iol, higyrus**) are clean, byte-faithful
mechanical migrations. I traced every probe in each: client identity is threaded
correctly, the IOL forced-refresh write-site writes and reads the same instance,
the raw `_request` adaptations exactly replicate the legacy module-shim raise/parse
semantics, sync/async boundaries are respected, finding `title=`/`fid=`/`class_=`
literals are unchanged, and credential redaction reads the same instance that
performed the login (no secret leak). No BLOCKER-class defects were found.

The **matriz** driver has a substantive gap: the migration's stated single-client
invariant is only partially achieved on the sync side. The 18 sync read-sweep
probes still route through the module-level singleton (`_matriz_request` →
`_get_default()`), while login + the 3 error probes use the threaded `client`. At
runtime this produces TWO independent live logins against the remarkets auth server
and uses two client identities for sync calls — the exact TokenStore-churn class of
risk the migration set out to remove. The AST guard does not catch this because it
counts only `Client()`/`AsyncClient()` literals in the driver source, not the
singleton constructed inside the package. The team documented this as an intentional
scope carve-out, but the documented rationale ("constructs no client") understates
the runtime consequence, so it is surfaced here as a WARNING for a fix-or-accept
decision.

## Warnings

### WR-01: matriz sync read-sweep probes bypass the threaded client → second live login + split client identity

**File:** `main_matriz.py:357-360, 517, 528-531, 582-585, 702-708, 781-785, 1063` (and helper sites `240, 257, 887`); cross-ref `packages/matriz-client/src/matriz_client/client.py:889-897` (`_request` → `_get_default()._matriz_legacy_request`)

**Issue:**
`main()` constructs one threaded `client = Client()` (`:2104`) and calls
`probe_login_sync(client)` (`:2140`), which authenticates **that** instance
(`client._state.token`). But the 18 read-sweep probes are invoked with no `client`
argument (`result, raw = probe_fn()`, `:2168`) and reach the live API through the
`_sweep_probe` helper, which calls the module-level shim:

```python
base_url = primary.client._base_url           # singleton read (:357)
raw = _matriz_request("GET", path, ...)        # -> _get_default()._matriz_legacy_request (:360)
```

`_matriz_request` is `from matriz_client.client import _request as _matriz_request`
(`:81`), and `client._request` (the package shim, `:889`) delegates to
`_get_default()` — a **separate** singleton `Client()` (`client.py:681-685`) with
its own `_ClientState` and its own TokenStore (`Client.__init__` builds a fresh
`_ClientState()`; the TokenStore is built lazily in `login()` from `self._state`).

Consequences:
- The threaded `client` is logged-in but its token is never used by the sweeps. The
  singleton lazily authenticates on the first sweep — a **second independent live
  login** against the remarkets auth server per run. This is the TokenStore-churn /
  OAuth-churn risk class the migration was meant to eliminate (and which the matriz
  AST-guard docstring explicitly claims to prevent).
- Sync surface now uses two client identities: login + error probes
  (`probe_error_bogus_symbol(client)` etc., `:1138` calls `client.get_market_data`)
  exercise the threaded token; the 18 read-sweeps exercise the singleton token.
- The captured redaction token (`token = getattr(client._state, "token", None)`,
  `:2142`) is the threaded instance's token; if the singleton's lazily-acquired
  token string differs, sweep-path detail strings that surface a token would not be
  covered by `secrets`. (Low likelihood — sweep details emit shapes/counts — but the
  redaction invariant is no longer "one token, captured once".)

This is a documented scope carve-out (`15-04-SUMMARY.md` "Scope notes"), but the
rationale ("those probes ... construct no client ... do not affect the AST ctor
count") addresses only the AST metric, not the runtime double-login / split-identity
behavior. The other three drivers fully migrated their `_request`-based diagnostic
sites (e.g. higyrus `_raw_request_sync`/`_raw_request_async` thread the instance;
iol `probe_field_type_map` threads `client._request`), so matriz is the lone
outlier.

**Fix:** Thread `client` into the sweep path so the whole sync surface shares one
identity and one login. Either give `_sweep_probe` a `client: Client` parameter and
replace the singleton calls with the instance:

```python
def _sweep_probe(client: Client, name, path, *, envelope_key=None, request_params=None,
                 auth_basic_fn=None, pass_detail=None):
    base_url = client._state.base_url
    auth = auth_basic_fn(client) if auth_basic_fn is not None else None
    raw = _raw_matriz_request_sync(client, "GET", path, params=request_params, auth_basic=auth)
    ...
```

mirroring higyrus's `_raw_request_sync` (which builds a `RequestSpec`, calls
`client._request(spec)`, then replicates the legacy raise/parse). Also thread the
risk-auth source (`_risk_auth` → `client._risk_auth()`) and the `primary.client._base_url`
reads at `:1063, 240, 257, 887`. If the carve-out is intentionally retained,
strengthen the AST-guard/summary to state explicitly that the matriz sync read-sweep
is a deliberate *second* live client and document the resulting two-login behavior,
so the guard's "single-Client invariant / TokenStore-corruption mitigation"
docstring is not misleading.

### WR-02: matriz AST guard is vacuous for the sweep path it claims to protect

**File:** `verification/test_main_matriz_uses_single_client_instance.py:15-18, 44-66`

**Issue:**
The guard's docstring states the `<= 2` bound "is the TokenStore-corruption
mitigation (anti-Pitfall 1) ... constructing more than one `AsyncClient` risks OAuth
churn / token corruption. Capping construction at one sync + one async client
directly prevents that." But the walker only counts `Client()` / `AsyncClient()`
constructor `Call` nodes **in the driver source** (`ast.Name`/`ast.Attribute` whose
name is in `_CTOR_NAMES`). It cannot observe the singleton `Client()` constructed
**inside `matriz_client.client._get_default()`** that the sweep probes drive via
`_matriz_request`. The guard therefore passes (2 ctors in the driver) while the
running driver actually instantiates and authenticates three client identities
(threaded sync, package singleton via sweeps, threaded async). The test gives false
assurance precisely for the corruption vector it documents (see WR-01).

**Fix:** Tie the invariant to the behavior it claims to guarantee. Add an assertion
that the driver source contains no `_matriz_request` / `_risk_auth` / `_get_default`
/ `primary.client._base_url` CODE references (the SUMMARY already asserts
"`_get_default()` CODE sites in driver | 0", so encode it as a test), or — once
WR-01 is fixed — assert the sweep helper takes a `client` parameter. At minimum,
soften the docstring so it does not assert a runtime guarantee the AST walk cannot
provide.

### WR-03: matriz `_async_main` wrapper docstring claims one shared TokenStore singleton, contradicting the per-instance state model

**File:** `main_matriz.py:2021-2024`

**Issue:**
The module comment above `_async_main` states: "all async probes share one event
loop + **one AsyncClient default singleton**, then aclose() at the end." Post-Phase-15
the async probes do **not** use a default singleton — `_async_main` constructs a
dedicated `aclient = AsyncClient()` (`:2043`) and threads it into every async probe;
there is no `aio._get_default()` in the async path anymore. The stale "default
singleton" wording misdescribes the new ownership model and will mislead the next
reader reasoning about token/TokenStore sharing (especially relevant given WR-01,
where the sync-vs-async identity split actually matters).

**Fix:** Update the comment to match the code, e.g. "all async probes share one event
loop and one dedicated `AsyncClient` constructed here (not the module default), then
`aclose()` at the end." (The inline `# CRITICAL (anti-Pitfall 1)` block at `:2037-2042`
already states this correctly; the header comment just needs to agree with it.)

## Info

### IN-01: iol `probe_field_type_map` re-raise after `client._request` is dead code (faithful to legacy shim, but inert)

**File:** `main_iol.py:987-995`

**Issue:**
```python
resp = client._request(RequestSpec(method="GET", path=...))
if resp.is_error:
    _raise_for_response(resp)
envelope = resp.json()
```
The instance `Client._request` (`packages/iol-client/src/iol_client/client.py:429-491`)
already calls `_raise_for_response(resp)` internally (`:468` and `:490`) and raises
on every error status before returning. By the time control returns to the probe,
`resp.is_error` is always `False`, so the `if resp.is_error: _raise_for_response(resp)`
branch is unreachable. The accompanying comment ("`Client._request` (D-03) devuelve
el response crudo sin levantar") is inaccurate for the instance method — it raises.
This is harmless and intentionally mirrors the legacy module-level shim
(`client.py:704-707`), which contains the identical inert guard, so behavior is
preserved. Flagged only as a maintainability note.

**Fix:** Either drop the dead `if resp.is_error:` guard (the instance `_request`
already enforces the raise), or correct the comment to note that the guard is a
belt-and-suspenders no-op retained for parity with the legacy shim, not a live
raise path. The higyrus `_raw_request_sync`/`_raw_request_async` helpers carry the
same inert guard (`main_higyrus.py:262-263, 280-281`) for the same reason — apply the
same clarification there if touched.

### IN-02: higyrus `probe_auth_401` mutates the module singleton while the rest of the driver uses the threaded client (documented, but a consistency wart vs iol)

**File:** `main_higyrus.py:2116, 2118, 2186`

**Issue:**
`probe_auth_401` calls `higyrus_client.configure(password=bad_password)` /
`higyrus_client.login()` / `higyrus_client.configure(password=original_password)` on
the module-level default client, whereas iol's equivalent `probe_auth_401` mutates
the **threaded** `client._state` directly (`main_iol.py:1445-1447, 1523`). The higyrus
approach is documented (`:2110-2115`, D-03/T-15-05 out-of-scope) and defensible
(higyrus has no `refresh_token` to preserve, so `configure()`'s token reset is safe;
the good-creds threaded `client` is only read for `base_url`). It does, however, mean
the higyrus driver materializes a second live client (the singleton) when
`VERIFY_HIGYRUS_BAD_CREDS=1`, diverging from the per-driver pattern iol established.
Not a correctness defect — opt-in, last probe, no downstream consumers of the
singleton token — but an inconsistency a future reader may trip on.

**Fix:** For symmetry with iol (and to keep the "single threaded client" story
uniform), consider mutating `client._state.password` + `client._state.token` directly
and restoring via direct state assignment, as iol does. Otherwise leave a one-line
note cross-referencing iol's deviation so the asymmetry is intentional-by-record.

---

_Reviewed: 2026-06-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
