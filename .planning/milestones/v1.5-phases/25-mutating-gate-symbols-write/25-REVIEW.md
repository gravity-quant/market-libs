---
phase: 25-mutating-gate-symbols-write
reviewed: 2026-07-31T20:55:55Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - packages/market-data-client/src/market_data_client/__init__.py
  - packages/market-data-client/src/market_data_client/_core.py
  - packages/market-data-client/src/market_data_client/_state.py
  - packages/market-data-client/src/market_data_client/aio.py
  - packages/market-data-client/src/market_data_client/client.py
  - packages/market-data-client/src/market_data_client/exceptions.py
  - packages/market-data-client/src/market_data_client/models.py
  - packages/market-data-client/tests/conftest.py
  - packages/market-data-client/tests/test_core.py
  - packages/market-data-client/tests/test_models.py
  - packages/market-data-client/tests/test_mutation_gate.py
  - packages/market-data-client/tests/test_public_surface_market_data.py
  - packages/market-data-client/tests/test_symbols_write_async.py
  - packages/market-data-client/tests/test_symbols_write.py
findings:
  critical: 0
  warning: 5
  info: 2
  total: 7
status: issues_found
---

# Phase 25: Code Review Report

**Reviewed:** 2026-07-31T20:55:55Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Reviewed the mutating-gate + symbols-write implementation across `_core.py`, `_state.py`,
`client.py`, `aio.py`, `models.py`, `exceptions.py`, `__init__.py`, and the six test files.

The security-critical surface holds up under adversarial scrutiny. I traced every attack
angle called out for this phase and found **no BLOCKER**:

- **Host-gate correctness (verified sound):** The exact-hostname comparison uses
  `urlsplit(...).hostname != expected` — no substring/`endswith`/prefix escape (test (d)
  proves the `…bbsa.com.ar.attacker.example` superstring is refused). `.hostname` is
  case-normalized (lowercased) by urllib and correctly strips port + userinfo, so
  `https://develop.host@evil.com/` resolves `actual="evil.com"` and is refused. A malformed
  base_url yielding `actual=None` fails closed (`None != expected` → refuse). The default
  `_DEFAULT_EXPECTED_HOST` resolves to a concrete non-`None` string, so the default path
  cannot silently disable the check.
- **Zero-side-effect refusal (verified):** `_ensure_mutation_allowed()` is the literal first
  statement of all three mutators on BOTH shells, and it is a pure state read (no `await`, no
  I/O). The refusal tests assert `httpx_mock.get_requests() == []` even with the token
  force-expired — proving no token grant and no HTTP dispatch precede the gate.
- **Sentinel correctness (verified):** `None` carry-forward in both `__init__` and `configure`
  cannot reset a prior `mutating_allowed=True` opt-in when only `base_url` is reconfigured
  (test (f)); `False` is distinguishable from unset because a fresh `_ClientState` defaults the
  flag to `False` and the sentinel only skips assignment on `None`.
- **Gate parity (verified):** `_ensure_mutation_allowed` is byte-identical across `client.py`
  and `aio.py`; the three mutator methods dispatch identically.
- **Idempotency, serialization, credential redaction (verified):** All three symbols builders
  carry `idempotent=True` (DM-03); `to_dict()` emits `market_id` unconditionally (D-10) and
  drops no required field; the 1-500 batch bound is inclusive with no off-by-one; `__repr__`
  redacts secret + token.

The findings below are robustness gaps, a sync/async surface-parity divergence, and stale
documentation — none of which breach the gate itself.

## Warnings

### WR-01: `parse_latest_response` lacks the envelope/non-list guard its sibling `parse_market_data_response` already has

**File:** `packages/market-data-client/src/market_data_client/_core.py:619-637`
**Issue:** `parse_market_data_response` (lines 588-616) was reconciled against the real develop
wire (LIVE-MD-01) and now unwraps a dict envelope via `raw.get("items", [])`, accepts a bare
list, and guards `if not isinstance(rows, list): rows = []`. Its sibling `parse_latest_response`
was NOT given the same treatment and iterates `raw` directly:

```python
raw = resp.json()
if raw is None:
    return []
return [MarketDataSnapshot.from_api(item, received_at=received_at) for item in raw]
```

Both `/marketdata` and `/marketdata/latest` are served by the same API. If the latest endpoint
also wraps rows in the `{count, items, ...}` envelope (highly likely, given the sibling did),
then `for item in raw` iterates the dict KEYS — feeding strings like `"items"`/`"count"` into
`from_api`, which tolerantly returns empty snapshots. Result: `get_latest` /
`get_latest_batch` silently return garbage rows instead of the real data. Worse, a scalar body
(`true`, a number) raises `TypeError: '...' object is not iterable` — a crash the sibling parser
explicitly guards against. The parser docstring defers shape reconciliation to Phase 23, but the
sibling was already reconciled, so this is a real asymmetry, not a uniform deferral.
**Fix:** Mirror the sibling's unwrap + guard:
```python
raw = resp.json()
if raw is None:
    return []
if isinstance(raw, dict):
    rows = raw.get("items", [])
elif isinstance(raw, list):
    rows = raw
else:
    rows = []
if not isinstance(rows, list):
    rows = []
return [MarketDataSnapshot.from_api(item, received_at=received_at) for item in rows]
```

### WR-02: Async `_send_auth_request` docstring contradicts its own code on `max_attempts`

**File:** `packages/market-data-client/src/market_data_client/aio.py:286-308`
**Issue:** The docstring states the method *"Propaga `idempotent`/`endpoint_name`/`request_id`
pero **NO setea `max_attempts`** (no hay override per-call)."* — but line 307 explicitly does
set it: `req.extensions["max_attempts"] = self._max_retries + 1`. The code is correct and
matches the sync shell (parity is preserved at runtime); the docstring is stale and actively
misleads a maintainer reasoning about auth-grant retry behavior — precisely the load-bearing
`with_options` retry-cap threading. A future reader could "fix" the code to match the wrong
docstring and silently break per-call retry caps on the auth grant.
**Fix:** Update the docstring to reflect that `max_attempts` IS set (auth-flow specs are
`idempotent=True`, so the per-call cap applies), matching the sync `_send_auth_request` doc.

### WR-03: Sync/async constructor + `configure` parity gap for `token` / `token_expires_at` / `http_client`

**File:** `packages/market-data-client/src/market_data_client/client.py:124-135` (and `configure` 605-617) vs `packages/market-data-client/src/market_data_client/aio.py:103-117` (and `configure` 620-631)
**Issue:** The dual sync/async constraint (CLAUDE.md) requires the two surfaces to mirror each
other. They diverge on state-seeding entry points:
- `AsyncClient.__init__` accepts `token`, `token_expires_at`, `http_client`; `Client.__init__`
  accepts none of them.
- Sync `configure` accepts `http_client`; async `configure` does not.

Net effect: `Client(token=...)` raises `TypeError` while `AsyncClient(token=...)` succeeds, and
`http_client` is settable via `configure` on sync but only via `__init__` on async. This is a
genuine cross-surface asymmetry in the public API of the same package. It is pre-existing (from
the Phase 20 shell build), not introduced by the gate wiring, but it remains a live parity
defect in files under review.
**Fix:** Align the two constructors and both `configure` signatures so `token`,
`token_expires_at`, and `http_client` are accepted (or intentionally omitted) identically on
both surfaces; if the omission is deliberate, document the rationale in each docstring.

### WR-04: Documented `expected_host=None` "disable host leg" is unreachable through the public API

**File:** `packages/market-data-client/src/market_data_client/client.py:154,668` — `packages/market-data-client/src/market_data_client/aio.py:138,677` — `packages/market-data-client/src/market_data_client/_state.py:102-103`
**Issue:** The `_ensure_mutation_allowed` docstrings and the `_state` comment state that
`expected_host = None` disables the host leg of the gate. But because both `__init__` and
`configure` use the `None`-sentinel `if expected_host is not None:` carry-forward, passing
`expected_host=None` is indistinguishable from "leave unchanged" — it never actually sets the
field to `None`. The only way to reach the documented disabled state is a direct private
mutation `client._state.expected_host = None` (exactly what test (e) does). This fails *closed*,
so there is no security exposure, but the documentation describes a security-relevant knob that
the public API cannot express — a caller who reads the docstring and relies on
`configure(expected_host=None)` to loosen the check will silently get the opposite (the check
stays enforced). Confusing during a security audit.
**Fix:** Either document that the host leg can only be disabled via internal state (and remove
the "pass None to disable" implication from the public-facing docstrings), or introduce an
explicit `disable_host_check: bool` flag so the intent is expressible and testable through the
public surface.

### WR-05: `parse_latest_response` return type/shape marked "PROVISIONAL" while the identical sibling was already reconciled

**File:** `packages/market-data-client/src/market_data_client/_core.py:619-628`
**Issue:** Beyond the missing guard (WR-01), the two sibling parsers now carry contradictory
docstrings: `parse_market_data_response` documents a reconciled LIVE-MD-01 envelope shape, while
`parse_latest_response` still says *"Return type is PROVISIONAL (A1/A2 — OpenAPI response shapes
not vendored)… Phase 23 reconciles."* Since both endpoints share the same service and envelope
convention, leaving one "reconciled" and one "provisional" is a maintenance trap — the next
reader cannot tell whether the divergence is intentional or an oversight.
**Fix:** Reconcile `parse_latest_response`'s shape handling and docstring in lockstep with its
sibling (folds naturally into the WR-01 fix), or add an explicit note explaining why the latest
endpoint's shape is still unconfirmed while `/marketdata` is not.

## Info

### IN-01: Async `_request` eagerly creates the token lock for anonymous (health) requests

**File:** `packages/market-data-client/src/market_data_client/aio.py:355`
**Issue:** `token_lock = self._ensure_token_lock()` runs unconditionally at the top of
`_request`, including on the `spec.authenticated is False` (health) branch that never uses the
lock. This lazily allocates an `asyncio.Lock` bound to the current loop for a code path that
does not need it. No correctness impact — just a needless allocation and a slightly misleading
signal that the anonymous path participates in token serialization.
**Fix:** Move `token_lock = self._ensure_token_lock()` inside the `if spec.authenticated:`
branch (and re-acquire it in the 401 re-auth carve-out, which is already inside that branch).

### IN-02: `NewSymbol.market_id` snake_case wire key vs `LatestRequest.marketId` camelCase — intra-package inconsistency (intentional, but flag-worthy)

**File:** `packages/market-data-client/src/market_data_client/models.py:209-213` vs `174-184`
**Issue:** `NewSymbol.to_dict()` emits the snake_case key `market_id` while `LatestRequest`
emits camelCase `marketId` in the same module. This is documented as intentional (Pitfall 3 /
A2, snake_case confirmed live in Phase 27, and explicitly listed as an accepted deferral for
this review). Recording it only so the inconsistency is not mistaken for a copy-paste bug in a
future pass; no action required for Phase 25.
**Fix:** None for this phase — revalidate the wire key against live develop in Phase 27 as
already planned.

---

_Reviewed: 2026-07-31T20:55:55Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
