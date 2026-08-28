# Phase 32: Gates de homogeneidad + D-16 - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-25
**Phase:** 32-gates-de-homogeneidad-d-16
**Mode:** assumptions
**Areas analyzed:** Alcance real de D-16, Gate AST de superficie, Test de paridad sync/async,
Roster explícito (wallets + `_PACKAGES`)

## Assumptions Presented

### Alcance real de D-16
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Sólo mypy `files` tiene un gap real; import-linter y ci.yml loop ya reconciliados | Confident | `pyproject.toml:97,149-156,182-187`; `ci.yml:37-38,95`; `uv run lint-imports` verde hoy |
| La única pieza real faltante es una prueba RED del contrato import-linter | Likely | grep de `lint-imports`/`importlinter` sobre código no-planning: cero test files |

### Gate AST de superficie
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| El gate debe entrar a métodos de clases exportadas, no sólo funciones de módulo | Confident | Barrido runtime: 0 funciones de módulo con `Any`/`dict[str,Any]`, 9 métodos `to_dict()` |
| Raíz inyectable (`root: Path`) en vez de `REPO_ROOT` module-level | Likely | Los 2 gates cross-package existentes no tienen tests, precisamente por esto |
| Step nuevo del job `lint`, no job de CI nuevo | Likely | D-12 de `31-CONTEXT.md` vs. `ROADMAP.md:25` ("job de CI nuevo") — contradicción explícita |

### Test de paridad sync/async
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| No puede comparar por `__all__` (ausente en mitad de los paquetes) | Confident | 4/6 `client.py` y 3/6 `aio.py` sin `__all__` — `[] == []` pasaría vacuo |
| El test encuentra drift real día uno: `market_data_client.aio.configure` sin `http_client` | Confident (hallazgo) / Likely (fix) | `client.py:762-775` vs `aio.py:776-788,797-798` (docstring afirma paridad falsa) |
| 6 archivos delgados in-package + helper compartido en la raíz | Likely | `pythonpath=["."]`, "Patrón 1" ya usado por 8 archivos |
| Lower bounds literales por paquete, wallets=1 casi-vacuo | Likely | Conteo medido: ambito 2/3, iol 6/7, higyrus 7/8, matriz 22/23, market-data 19/20, wallets 1/2 |

### Roster explícito (wallets + `_PACKAGES`)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| wallets excluido de `root_packages` por razón estructural (sin `_core.py`) | Confident | `packages/wallets-client/src/wallets_client/` — 7 módulos, ninguno `_core.py`/`_state.py`/etc. |
| `_PACKAGES` de `verification/test_public_surface.py` se mantiene, sólo comentario | Confident | `verification/` nunca corre en CI; cobertura real ya in-package (`test_public_surface_market_data.py`) |
| Scope del criterio 4 limitado a las 4 listas nombradas, ~6 otros rosters fuera de scope | Confident | Enumerados en D-12 de CONTEXT.md |

## Corrections Made

No corrections — all assumptions confirmed as presented ("Sí, proceder").

## External Research

No aplica — fase stdlib-only (`ast`, `pathlib`, `inspect`, `typing.get_type_hints`) sobre
herramientas ya presentes en el lockfile (mypy 1.13, import-linter). El agente analizador verificó
empíricamente que `get_type_hints()` resuelve sin fallos sobre los 12 módulos `client.py`/`aio.py`
y que `lint-imports` corre verde hoy — sin incógnitas de versión ni de ecosistema.
