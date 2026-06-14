---
status: complete
phase: 11-harness-hardening-code-review-close-out-live-re-verification
source:
  - 11-01-SUMMARY.md
  - 11-02-SUMMARY.md
  - 11-03-SUMMARY.md
started: 2026-06-14T12:08:49Z
updated: 2026-06-14T12:14:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test — pytest aggregate verde desde shell limpia
expected: Correr `uv run pytest -q` desde shell limpia. Debe reportar `907 passed, 1 deselected`.
result: pass
verified_by: user

### 2. HARN-07 — Markers BEGIN/END en los 4 findings.md
expected: Correr `grep -c "BEGIN AUTO-GENERATED" .planning/verification/*-findings.md` y `grep -c "END AUTO-GENERATED" .planning/verification/*-findings.md`. Los 4 archivos (ambito-financiero, iol, higyrus, matriz) deben tener exactamente 1 BEGIN y 1 END cada uno.
result: pass
verified_by: claude
evidence: |
  4 files × 1 BEGIN + 4 files × 1 END:
  ambito-financiero-client-findings.md:1, higyrus-client-findings.md:1,
  iol-client-findings.md:1, matriz-client-findings.md:1

### 3. HARN-08 — Dedupe content-addressed por title en los 4 drivers
expected: Correr `grep -n "idempotent_by_title=True" main_*.py`. Debe aparecer al menos 1 vez en cada driver: main_matriz.py (D-MATZ-27 EXPECTED, HARN-10), main_iol.py (auth_401 EXPECTED), main_higyrus.py (auth_401 EXPECTED), main_ambito_financiero.py (antibot EXPECTED).
result: pass
verified_by: claude
evidence: |
  main_iol.py:1449, main_higyrus.py:2061, main_matriz.py:2212, main_ambito_financiero.py:604 —
  4/4 drivers con el kwarg adoptado (líneas ligeramente desplazadas respecto al SUMMARY por
  comentarios añadidos).

### 4. HARN-09 — Operator content sobrevive cross-run en iol-client-findings.md
expected: Inspeccionar `.planning/verification/iol-client-findings.md`. Debajo del marcador `<!-- END AUTO-GENERATED -->` deben aparecer los bullets operator-añadidos para F-02 — al menos: Classification (PROBE_STALE), Rationale (PEP 562 shadowing), Resolution (INT-01 idiom), Operator signoff (sebadlf, 2026-06-14).
result: pass
verified_by: claude
evidence: |
  Debajo del marcador END están presentes:
  - Classification: PROBE_STALE (not a client bug)
  - Rationale: PEP 562 shadowing — referencia explícita a `_get_default()._state.token_expires_at`
  - Resolution: INT-01 idiom aplicado en `main_iol.py:1289` durante Plan 11-03 Task 3
  - Regression: `main_iol.py` re-run post-fix → PASS=13, F-02 ya no surgió
  - Operator signoff: sebadlf, 2026-06-14
  Además, la sección `## Cycle Closure` (operator-curated) está preservada byte-identical.

### 5. CR-07 — event_hooks thread-safety en higyrus
expected: Correr `uv run pytest packages/higyrus-client/tests/test_event_hooks_thread_safety.py -q`. Debe reportar `3 passed`.
result: pass
verified_by: claude
evidence: "3 passed in 0.03s"

### 6. CR-06 — AST guard contra bare `except Exception` en main drivers
expected: Correr `uv run pytest verification/test_main_drivers_bare_except.py -q`. Debe reportar `2 passed`.
result: pass
verified_by: claude
evidence: "2 passed in 0.04s"

### 7. CR-04/02/01 — main_matriz harness fixes (15 cases)
expected: Correr `uv run pytest verification/test_main_matriz_first_dict.py verification/test_main_matriz_login_fail_uniformity.py verification/test_main_matriz_schema_snapshot_alignment.py -q`. Debe reportar `10 passed` (5 CR-04 + 2 CR-02 + 3 CR-01).
result: pass
verified_by: claude
evidence: "10 passed in 4.32s"

### 8. CR-08 — Ruff check + format + mypy gates clean
expected: 3 comandos: `uv run ruff check .` → "All checks passed!"; `uv run ruff format --check .` → "148 files already formatted"; `uv run mypy` → "Success: no issues found in 50 source files".
result: pass
verified_by: claude
evidence: |
  ruff check: "All checks passed!"
  ruff format: "148 files already formatted"
  mypy strict: "Success: no issues found in 50 source files"

### 9. iol F-02 — INT-01 idiom aplicado en main_iol.py:1289
expected: Inspeccionar la línea 1289 de main_iol.py. Debe decir `iol_client.client._get_default()._state.token_expires_at = 0.0` (idiom INT-01), NO `iol_client.client._token_expires_at = 0.0`.
result: pass
verified_by: claude
evidence: |
  El fix está en main_iol.py:1294 (línea desplazada por comentarios INT-01 documentando el
  patrón; SUMMARY mencionaba 1289 en el commit). Línea exacta:
  `iol_client.client._get_default()._state.token_expires_at = 0.0`
  NOTA: existe otra ocurrencia en línea 1427 (probe `auth_401`) con el patrón viejo
  `iol_client.client._token_expires_at = 0.0`, pero ese probe NO lee la variable post-`login()`,
  por lo que el shadowing no produce el bug F-02. No es un latente — el SUMMARY no lo flagged
  como issue y la operación intencional es resetear el token antes de un login() forzado.

### 10. import-linter contracts (Phase 7 carry-forward)
expected: Correr `uv run lint-imports`. Debe reportar `Contracts: 4 kept, 0 broken`.
result: pass
verified_by: claude
evidence: |
  "Contracts: 4 kept, 0 broken." (ambito/higyrus/iol/matriz _core sin importar transport)

### 11. Findings append-only + dedupe regression tests (HARN-07/08/09/10)
expected: Correr `uv run pytest verification/test_findings_append_only.py verification/test_findings_dedupe_by_title.py -q`. Debe reportar `16 passed`.
result: pass
verified_by: claude
evidence: "16 passed in 0.03s"

### 12. LIVE-01 — 11-VALIDATION.md aprobado por operator
expected: Frontmatter de `11-VALIDATION.md` con status=approved, nyquist_compliant=true, phase_status=ready_for_close, operator_signoff_by=sebadlf, 4 dispositions pobladas. iol específicamente: `F-02 FIXED — PROBE_STALE inline fix (main_iol.py:1289 INT-01 idiom); re-run PASS`.
result: pass
verified_by: claude
evidence: |
  status: approved
  nyquist_compliant: true
  phase_status: ready_for_close
  operator_signoff_by: sebadlf (Sebastián de la Fuente)
  operator_signoff_date: 2026-06-14
  operator_dispositions:
    ambito: no_new_findings
    iol: F-02 FIXED — PROBE_STALE inline fix (main_iol.py:1289 INT-01 idiom); re-run PASS
    higyrus: no_new_findings
    matriz: no_new_findings

## Summary

total: 12
passed: 12
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none — all tests pass]
