# 29-WALLETS-EXEMPTION.md — why `wallets-client` carries no decode walker

**Phase:** 29-decoder-observable
**Decision:** D-02 (intactness by hash plus ban-list grep over the copies, with
`wallets-client` carrying a *documented exemption* rather than a bootstrap)
**Status:** active for the whole of Phase 29
**Machine-visible counterpart:** the `EXEMPT_PACKAGES` constant in
`tools/check_decode_intactness.py`

---

## The short version

This monorepo has six packages. Phase 29 ships the decode walker to **five** of
them. `wallets-client` is the sixth, and it does not receive a copy — not because
it was forgotten, but because it has no structure to attach one to. Every
per-package criterion in Phase 29 is therefore to be read as **five packages plus
this documented exemption**, never as six.

Bootstrapping `wallets-client` into the shape the other five share is the scope of
**Phase 31** ("Endpoints de ops + estructura uniforme"), whose success criterion 4
requires all six packages to present the same file layout. Its enrollment in the
repository's four cross-cutting package lists is settled explicitly by **Phase 32**
(D-16 reconciliation). Neither is this phase.

---

## The evidence

### Which modules it has, and which it lacks

`packages/wallets-client/src/wallets_client/` contains exactly four modules:

| Module | Present |
| --- | --- |
| `__init__.py` | yes |
| `client.py` | yes |
| `aio.py` | yes |
| `exceptions.py` | yes |

Every other package in the workspace carries, at minimum, the following — and
`wallets-client` carries **none** of them:

| Module | higyrus | market-data | matriz | iol | ámbito | **wallets** |
| --- | --- | --- | --- | --- | --- | --- |
| `_state.py` | yes | yes | yes | yes | yes | **no** |
| `_logging.py` | yes | yes | yes | yes | yes | **no** |
| `_core.py` | yes | yes | yes | yes | yes | **no** |
| `_transport.py` / `_atransport.py` | yes | yes | yes | yes | yes | **no** |
| `models.py` | yes | yes | yes | — | — | **no** |
| `_decode.py` (Phase 29) | yes | yes | yes | yes | yes | **no** |

### No per-instance client state object

The other five packages hold their configuration on a shared, per-instance
`_ClientState` dataclass, which is where Phase 29 adds `strict_decode: bool = False`
and which `with_options(...)` views inherit by reference. `wallets-client` has no
such object. It is still on the original module-level singleton pattern:

```python
# packages/wallets-client/src/wallets_client/client.py
_base_url: str = os.getenv("WALLETS_BASE_URL", "https://api.wallets.example").rstrip("/")
_token: str = os.getenv("WALLETS_TOKEN", "")
_client = httpx.Client(timeout=_REQUEST_TIMEOUT)
```

There is no `Client` class and no `AsyncClient` class anywhere in its source — the
only classes it declares are the four exceptions in `exceptions.py`. **There is
therefore no place to put the mode flag.** Putting it on a module global would
reintroduce exactly the process-wide, un-scoped configuration that `_ClientState`
and the `ContextVar` carrier exist to replace, and it would be un-inheritable by a
`with_options` view because there are no views.

### No bind site of the shape the other packages have

Phase 29 binds the decode mode with two statements at the top of each `_request`
**method**, in `client.py` and in `aio.py`, so the mode is scoped to one request
and one response decode. `wallets-client`'s request functions are **module-level
functions**, not methods:

```
packages/wallets-client/src/wallets_client/client.py:57:def _request(
packages/wallets-client/src/wallets_client/aio.py:73:async def _request(
```

A module-level `_request` has no `self._state` to read the flag from. The bind
site the other five packages share does not exist here, and manufacturing one
would mean designing the client-state object — which is Phase 31's job, not a
side effect of a decoder phase.

### Nothing to decode

`wallets-client` declares no response models. It has no `models.py` and no
`SafeModel`-shaped classes, so there is no `from_api` call site for a walker to
serve. A copy of `_decode.py` here would be dead code on a published wheel with
no consumer scheduled — strictly worse than ámbito's deliberately dormant copy,
which at least sits beside a client-state object and two live bind sites.

---

## Which Phase 29 criteria this reading affects

The five-plus-one reading affects exactly three families of criteria. Each is
listed here so a reader auditing the phase does not mistake an absence for a gap:

1. **The `RedactingFilter` fix (D-05).** The bounded-recursion generic scan lands
   inside the `# --- decode-intactness: generic-scan begin/end ---` marker region
   of `_logging.py`. `wallets-client` has no `_logging.py`, so it receives no
   filter fix and contributes no scan region. Check B in
   `tools/check_decode_intactness.py` hashes **five** regions.
2. **The caplog credential sentinels.** Every in-scope package gained a
   `test_decode_sentinel_never_leaks_credential` test in its `tests/test_logging.py`.
   `wallets-client`'s test suite is `test_client.py` and `test_async_client.py`
   only — it has no `test_logging.py`, because it has no logging module to test.
   It therefore carries no decoder sentinel.
3. **The intactness roster.** `tools/check_decode_intactness.py` holds the copy
   topology in two constants: `IN_SCOPE_PACKAGES` (five entries) and
   `EXEMPT_PACKAGES` (one entry, `wallets-client`, carrying this reason and the
   resolving phase). Check D asserts both halves — that each in-scope package
   still has a `_decode.py`, and that the exempt package has **not** acquired one.

---

## How the two records are kept from drifting apart

This document and the checker reference each other **by name**, so neither can be
updated in isolation without the mismatch being visible:

- `tools/check_decode_intactness.py` names this file in its `EXEMPTION_DOC`
  constant, prints that path in Check D's green summary line, and cites it in both
  of Check D's failure messages.
- This document names `IN_SCOPE_PACKAGES` and `EXEMPT_PACKAGES`, the two constants
  that encode the topology described above.

Check D also fails if a package appears under `packages/` that is on **neither**
list, so a seventh package cannot enter the workspace without a deliberate
decision recorded in one of the two constants.

## What happens when the exemption ends

When Phase 31 gives `wallets-client` the shared file layout, Check D will start
failing the moment a `_decode.py` appears there — by design (threat T-29-51). The
fix at that point is a three-part edit, not a suppression:

1. Move the `wallets-client` entry from `EXEMPT_PACKAGES` into `IN_SCOPE_PACKAGES`.
2. Add its `_decode.py` and its marker-delimited `_logging.py` scan region, so
   Checks A and B hash six copies instead of five.
3. Supersede this document, recording the phase that closed the exemption.
