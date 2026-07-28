# 001a — ámbito round-trip (SPIKE-006, D-RIGOR-02 items 1/2/3/4/5/6/7/9)

The genuinely-new core of SPIKE-006: a suite of **pure** libcst `CSTTransformer`
subclasses + an **impure** driver that transforms the un-migrated ámbito `aio.py`
into a candidate sync `client.py`, then runs the GO-determining gate.

## Layout

```
transformers/                      # pure CSTNode→CSTNode subclasses (item-9 unit)
  async_to_sync.py                 # strip async/await; rename AsyncClient→Client, _atransport→_transport, aclose→close, __aenter__→__enter__, …
  import_normalizer.py             # sort the `from ambito_financiero_client import …` alias list (item-4 I001)
  docstring_localizer.py           # SimpleString value rewrite: asincrónico→sincrónico, AsyncClient→Client, strip `await `
  import_direction_normalizer.py   # strip a self-import ONLY when the name is locally defined (config frozenset from driver); else retain (Q1)
  suppressors.py                   # RemovalSentinel: `import warnings`, WR-07 ResourceWarning block, prior_http_client assign, `"aclose"` __all__ entry
  test_transformers.py             # TDD behavior + item-9 purity assertions (CI-excluded; run explicitly)
experiment.py                      # impure driver: parse aio.py → passes → module.body scope edits → @generated marker → emit → item-1 diff + item-2 B8 + item-9 purity
output/client_generated.py         # the generated sync transport shell (item-1 subject)
diff_vs_current_client.txt         # item-1 baseline vs CURRENT client.py (SPIKE-005 diff is stale — Pitfall 1)
run_log.txt                        # per-item captured transcript
FINDING.md                         # per-item 1/2/3/4/5/6/7/9 verdicts + Q1 content-absence instrumentation
```

## Run (ephemeral libcst — D-05, never added to dev deps)

```bash
# driver (emit + item-1/2/9 smoke)
uv run --with 'libcst>=1.8.0,<2' python \
  .planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/experiment.py

# transformer unit + purity tests
uv run --with 'libcst>=1.8.0,<2' python -m pytest \
  .planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/transformers/test_transformers.py -q
```

## Integrity guardrails (D-02, D-03, D-04)

- `aio.py` is the SOLE source and is **read-only** — never edited.
- `client.py` is the byte-identity ORACLE — **never** read as a content donor.
- The two content-absent-from-source regions (`_validate_max_retries` def, `load_dotenv`
  import+call) cannot be synthesized by any pure transform of `aio.py` alone. The residual
  divergence they cause is the honest item-1/item-6 evidence — an honest FAIL is a valid,
  guaranteed deliverable (D-04/D-08), never softened.
- `_raise_for_response = _core.raise_for_response` is emitted verbatim (B8 / Pitfall 4).
