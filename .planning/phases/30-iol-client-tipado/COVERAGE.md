# Phase 30 — API Coverage Declaration

**Detector:** `api-coverage.cjs` returned `detected: true`.
**Outcome:** No external API integration — reasoned declaration, no coverage matrix.

## Why the detector fired

The single signal was:

> `(surface)` / `api` — "La API ficticia desapareció: `grep -cE 'IOLClient\(|get_portfolio' packages/iol-client/README.md` imprime `0`."

That sentence is an acceptance criterion from 30-04 asserting that a **fictitious**
API description was removed from the README. The token `API` matched the noun list;
the phase scope contains no integration verb bound to a new service.

## No external API integration: this closure adds no new surface

Phase 30 (and this gap closure, plans 30-05 / 30-06) operates entirely on an
**already-integrated** client:

- `iol-client` has integrated `api.invertironline.com` since Phase 3. Its endpoint
  surface — `get_quote`, `get_historical_quotes`, `get_instruments`,
  `get_instruments_by_type`, `login`, `refresh` — was enumerated and built then.
- Phase 30 changed **return types** (dict → typed model) on the four existing
  endpoints. It added zero endpoints.
- The gap closure changes (a) an input-validation guard inside an existing parser
  (`parse_get_instruments_by_type_response`) and (b) which payload the local
  verification harness feeds its drift probes. Neither touches the set of upstream
  operations the client can perform.

No capability of `api.invertironline.com` becomes newly reachable or newly
unreachable as a result of these plans. There is therefore no INTEGRATE/OPT-OUT
decision to record: the coverage question was settled in Phase 3 and is
unchanged.

## Where the real coverage question lives

The milestone's live-verification coverage for `iol-client` is tracked by
`main_iol.py`'s 15 named probes and by `.planning/verification/iol-client-findings.md`,
not by a per-phase coverage matrix. Phase 33 (live strict verification) is the
phase that re-audits that surface against the live service — which is precisely
why CR-01 (the drift probes going blind) is a blocker for this closure rather
than a deferrable warning.
