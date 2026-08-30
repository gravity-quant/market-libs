# Quick Task 260614-r1x: mypy-precommit-v1.1-techdebt — Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Origin:** Deferred from Phase 12 pre-gate per `12-SUMMARY.md` (line 222, "Quick-tasks to create AFTER this phase closes")

## Task Boundary

Cerrar la tech debt de CI (mypy + pre-commit) heredada de v1.1 y de Phase 08, de modo que `pre-commit run --all-files` quede VERDE antes del próximo phase planning kickoff. Esto satisface la directriz operador-emitida en `12-SUMMARY.md`: *"v1.2 phases start from a CI-clean baseline"*.

## Scope (locked — decided 2026-06-14)

**Scope elegido: A+B+C+D — CI-green total** (vs. strict scope solo A+B).

### Bucket A — v1.1 mypy tech debt en tests (6 errores)

`packages/matriz-client/tests/test_core.py`:
- L375: remover `# type: ignore[list-item]` (unused — mypy drift)
- L376: remover `# type: ignore[list-item]` (unused)
- L377: remover `# type: ignore[list-item]` (unused)

`packages/matriz-client/tests/test_async_auth.py`:
- L223–224: corregir error `attr-defined` — `Module "matriz_client.aio" does not explicitly export attribute "_raise_for_response"` (B8 identity test failing under mypy strict)
- L245: remover `# type: ignore[attr-defined]` (unused)

### Bucket B — ruff format pendiente (1 archivo, documentado por operador)

- `verification/test_retry_401_reauth.py`: aplicar `ruff format`

### Bucket C — ruff format pendiente residual (11 archivos, no documentados pero detectados en baseline)

Aplicar `uv run ruff format` (o `pre-commit run ruff-format --all-files`) sobre los 11 archivos restantes que retornan `Would reformat` en `ruff format --check .`:
- `packages/matriz-client/tests/test_async_mutations.py`
- `packages/matriz-client/tests/test_atransport.py`
- `packages/matriz-client/tests/test_transport.py`
- `verification/test_async_configure_resource_warning.py`
- `verification/test_findings_append_only.py`
- `verification/test_findings_dedupe_by_title.py`
- `verification/test_logging_no_token_leak.py`
- `verification/test_main_matriz_login_fail_uniformity.py`
- `verification/test_main_matriz_schema_snapshot_alignment.py`
- `verification/test_matriz_sweep_snapshot.py`
- `verification/test_phase06_nyquist_gaps.py`

### Bucket D — pre-commit `mypy` hook no encuentra `tenacity` (Phase 08 tech debt)

`tenacity` está declarado en cada `packages/*/pyproject.toml` desde commit `273891b` (Phase 08), pero el hook `mypy` en `.pre-commit-config.yaml` corre en su venv aislado SIN `tenacity` instalado, generando 8 errores `import-not-found` (`_transport.py` + `_atransport.py` de los 4 paquetes).

Fix: añadir `tenacity>=9.1.0,<10` al bloque `additional_dependencies` del hook `mypy` en `.pre-commit-config.yaml`.

## Implementation Decisions

### `_raise_for_response` re-export fix (decisión operador)

**Elegido:** añadir `"_raise_for_response"` al `__all__` de `packages/matriz-client/src/matriz_client/aio.py` (línea 94).

Justificación: el `from matriz_client._core import raise_for_response as _raise_for_response` ya intenta declaración explícita (línea 61), pero mypy strict considera privado todo símbolo con prefijo `_` salvo que aparezca en `__all__`. Agregarlo allí es PEP-562-conforme y conserva la simetría con `client.py` (que ya lo expone como assignment de módulo, lo cual no dispara `implicit_reexport`).

Alternativas descartadas:
- `# type: ignore[attr-defined]` en los tests → suprime síntoma, deja la regresión latente.
- Re-export como `from ._core import raise_for_response as _raise_for_response` (lo que ya hay) → no resuelve por sí solo (la prueba de aquí abajo).

### Worktree isolation (decisión operador)

**Elegido:** sí, con merge-back manual.

El executor corre con `isolation="worktree"` (default GSD). Tras retorno, el orquestador aplica el workaround documentado en `memory/feedback_worktree_merge_workaround.md`: `git worktree remove --force` + `rm -rf` del path si quedó residuo + `git merge --ff-only worktree-agent-<id>` desde main (NO usar `gsd-sdk query worktree.cleanup-wave` que falla por hooks copy-back).

### Out-of-scope (explícito)

- NO migrar lógica de retry, NO tocar transport o atransport runtime — solo configuración del hook.
- NO bumpear versiones de paquete (CHANGELOG no se modifica).
- NO mover los errores fuera del scope listado (cualquier `Would reformat` o mypy error que aparezca en archivos no listados debe surfacearse, no auto-corregirse).
- NO actualizar `uv.lock` ni dependencias runtime.

## Canonical References

- `.planning/phases/12-codegen-spike/12-SUMMARY.md` (líneas 30–45, 160–195, 220–230) — origen del defer
- `.planning/phases/12-codegen-spike/12-01-SUMMARY.md` (líneas 117–135) — caveat pre-gate original
- `.planning/phases/12-codegen-spike/12-03-SUMMARY.md` (líneas 320–330) — confirmación NO-GO close-out
- `~/.claude/projects/-Users-sebadlf-development-becerra-market-libs/memory/feedback_worktree_merge_workaround.md` — workaround merge-back

## Verification gate (acceptance)

Tras commit del executor + commit de docs del orquestador:

```bash
uv run pre-commit run --all-files
# debe retornar exit 0 (todos los hooks PASS o "Skipped")

uv run ruff check .
# debe retornar 0 errors

uv run ruff format --check .
# debe retornar "X files already formatted" (0 diffs)

uv run mypy --strict packages/matriz-client/tests/test_core.py \
                     packages/matriz-client/tests/test_async_auth.py
# debe retornar "Success: no issues found"
```

Si CUALQUIERA de los 4 retorna non-zero, el quick-task NO está completo.
