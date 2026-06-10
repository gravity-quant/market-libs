# Phase 2: Ámbito Verification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 02-mbito-verification
**Areas discussed:** Driver structure & output, Live tests vs driver-only, Anti-bot probe safety, Schema snapshot location & format, AMB-02 detection tactic, Date selection, Drift detection on re-runs, Redaction usage in driver

---

## Driver Structure & Output

### ¿Cómo se organizan los probes dentro de main_ambito_financiero.py?
| Option | Description | Selected |
|--------|-------------|----------|
| Sub-funciones nombradas por probe | Cada probe es una función al tope (probe_happy_sync, etc.), main() las invoca. Composable, escala a Phases 3-5. | ✓ |
| Lineal inline en main() | Plano dentro de main(). Simple para 6 probes, no escala. | |
| Cada probe en script separado | scripts/probe_*.py. Rompe el patrón "un driver por paquete". | |

**Notes:** Marca el patrón para Phases 3-5 con muchos más endpoints.

### ¿Qué formato emite el driver a stdout?
| Option | Description | Selected |
|--------|-------------|----------|
| Plain text una línea por probe + summary final | Verbatim `PROBE <name>: PASS/FAIL/SKIPPED/FINDING`. Compatible con main_verify.py. | ✓ |
| JSON estructurado | Fácil parse pero ilegible y rompe el scan de líneas de main_verify.py. | |
| Plain text + bloque markdown final | Duplica el findings file. | |

### ¿Cómo se escribe `.planning/verification/ambito-findings.md` durante el run?
| Option | Description | Selected |
|--------|-------------|----------|
| Driver lo auto-genera con verification.findings | Llama write_findings() y append_finding() (D-10) por hallazgo. | ✓ |
| Solo imprime stdout; humano escribe a mano | Rompe el plumbing ya construido. | |
| .json intermedio renderizado luego | Doble paso innecesario. | |

### ¿Qué hace el driver cuando un probe encuentra una discrepancia?
| Option | Description | Selected |
|--------|-------------|----------|
| Continúa todos los probes; exit 0 salvo crash | Verificación exhaustiva en un solo run. Los hallazgos son output esperado. | ✓ |
| Continúa pero exit != 0 si hubo CONFIRMED | Mezcla "hallazgos" con "error de proceso"; CI no corre vivo. | |
| Fail-fast en el primer error | Rompe la verificación exhaustiva. | |

---

## Live Tests vs Driver-Only

### ¿Phase 2 escribe tests `@pytest.mark.live` propios de Ámbito, o queda todo en el driver?
| Option | Description | Selected |
|--------|-------------|----------|
| Driver-only para verificación; tests pytest solo mockeados | main_*.py hace todos los probes vivos; tests bajo packages/ son solo mockeados. | ✓ |
| Driver + set mínimo de @pytest.mark.live | Cobertura duplicada parcial. | |
| Tests @pytest.mark.live cubren todo; driver solo orquesta | Rompe con D-01 de Phase 1 (driver es el vehículo). | |

### Para cada bug FIXED, ¿cuántos tests de regresión mockeados se escriben?
| Option | Description | Selected |
|--------|-------------|----------|
| Uno por superficie: test_client.py + test_async_client.py | Mirror del fix; consistente con la convención dual sync/async. | ✓ |
| Uno solo combinado parametrizado | Rompe la separación test_client/test_async_client. | |
| Solo en la superficie observada | Pierde el principio "todo fix se espeja". | |

### ¿Qué identificador va en `Regression: ... (issue #NNN)`?
| Option | Description | Selected |
|--------|-------------|----------|
| ID del finding (`finding F-01`) | Findings file es la fuente de verdad; no depende de tracker externo. | ✓ |
| Issue # real de GitHub | Más ceremonia para repo de uso interno. | |
| Ambos: finding F-01 + GH #42 | Doble fuente. | |

### ¿Agrega tests mockeados NUEVOS que codifiquen invariantes verificadas en vivo?
| Option | Description | Selected |
|--------|-------------|----------|
| Sí, agregar tests que codifiquen lo verificado en vivo | URL exacta, shape, parse_ar_decimal, NoDataError. Lock-in contra drift futuro. | ✓ |
| Solo regresiones por bug FIXED | Pierde la oportunidad de blindar invariantes. | |
| Reemplazar tests existentes con derivados de fixtures vivos | Más pipeline para poco beneficio. | |

### ¿Dónde viven los tests mockeados nuevos + regresiones?
| Option | Description | Selected |
|--------|-------------|----------|
| Append a test_client.py + test_async_client.py con sección delimitada | `# ------ Verified live (Phase 2) ------` y `# ------ Regressions ------`. Consistente con TESTING.md. | ✓ |
| Archivos nuevos test_*_verified.py | Aisla Phase 2 pero rompe el patrón "un test_client.py por superficie". | |
| Un solo test_invariants.py parametrizado | Rompe la separación sync/async por archivo. | |

### Idempotencia del driver al re-correr.
| Option | Description | Selected |
|--------|-------------|----------|
| Phase 2 extiende verification.findings con append_finding() | Helper idempotente por fid; convergen runs sin pisar status humanos. | ✓ |
| Write-once: solo crea skeleton + emite markdown a stdout | Más manual, no extiende el plumbing. | |
| Overwrite siempre | Pierde historial y status humanos. | |

### ¿Cómo maneja el driver el lifecycle del cliente async (aio)?
| Option | Description | Selected |
|--------|-------------|----------|
| Un solo asyncio.run(_async_main()) al final | Un solo event loop, cliente compartido, aclose() final. | ✓ |
| asyncio.run() por probe async | Anti-pattern: mismo aio state a través de múltiples event loops. | |
| Loop manual: new_event_loop + run_until_complete | Boilerplate sin beneficio. | |

---

## Anti-Bot Probe Safety (AMB-06)

### ¿El probe anti-bot corre por default o es opt-in?
| Option | Description | Selected |
|--------|-------------|----------|
| Opt-in via env var `VERIFY_ANTIBOT=1` | Mismo patrón que VERIFY_MUTATING. Evita acumular 403s en runs repetidos. | ✓ |
| Default ON | Cada run dispara una llamada con UA inválida. | |
| Opt-in via flag CLI `--antibot` | Requiere parsear sys.argv; env var compone con main_verify.py. | |

### Posición del probe anti-bot en la secuencia del driver.
| Option | Description | Selected |
|--------|-------------|----------|
| Último probe | Si trigger ban, los probes anteriores ya emitieron resultados. | ✓ |
| Primero | Si triggerea ban, el resto del run viene con 403s espurios. | |
| Después de happy_sync, antes del resto | Sin razón fuerte. | |

### Estructura de safety para evitar loops / retries.
| Option | Description | Selected |
|--------|-------------|----------|
| One-shot estructural sin retry ni sleep | Una sola llamada; sin reintentos. | ✓ |
| One-shot + sleep cooldown 30s | No hay probes posteriores; sleep no aporta. | |
| Hasta N=3 intentos con backoff | Exactamente lo que el requirement prohíbe. | |

### ¿Cómo aisla el cambio de UA del cliente?
| Option | Description | Selected |
|--------|-------------|----------|
| configure(BAD_UA) + try/finally con configure(GOOD_UA) | Ejercita la API real del cliente; restaura aun si crashea. | ✓ |
| httpx.Client propio del driver | Ya no se verifica el cliente del paquete. | |
| No restaurar | Higiene rota. | |

### ¿Qué User-Agent inválida usa el probe?
| Option | Description | Selected |
|--------|-------------|----------|
| Default de httpx (`python-httpx/{version}`) | El caso citado en el docstring del cliente. | ✓ |
| Cadena arbitraria 'FakeBot/1.0' | AMB-06 pide reproducir el 403, no caracterizar el filtro. | |
| User-Agent vacío | Más ceremonia para igual resultado. | |

### Cobertura: ¿sync, async, o ambos?
| Option | Description | Selected |
|--------|-------------|----------|
| Solo sync | Defensa es del servidor; una sola llamada alcanza para AMB-06. | ✓ |
| Sync + async | Duplica exposición del IP; paridad ya verificable por code-read. | |
| Solo async | Sin razón. | |

### Si la respuesta NO es 403, ¿qué hace el probe?
| Option | Description | Selected |
|--------|-------------|----------|
| Registrar OPEN ANTI-BOT con respuesta real | Cada caso (200/429/timeout) es información distinta. | ✓ |
| Marcar directamente CONFIRMED | Asume mal: una sola observación no confirma. | |
| Re-lanzar con cooldown | Viola one-shot estructural. | |

---

## Schema Snapshot (DRIFT-01)

### Ubicación del snapshot committeable.
| Option | Description | Selected |
|--------|-------------|----------|
| `.planning/verification/schemas/<pkg>/<slug>.json` | Coherente con `<pkg>-findings.md` y `captures/`. | ✓ |
| `verification/schemas/<pkg>/<slug>.json` | Mezcla código y artefactos. | |
| `packages/<pkg>/tests/fixtures/schemas/<slug>.json` | Entra al artefacto distribuible. | |

### Slug del snapshot (filename).
| Option | Description | Selected |
|--------|-------------|----------|
| Nombre de función del cliente: `get-dollar-banco-nacion.json` | Estable; refleja el comportamiento público. | ✓ |
| Slug del endpoint REST | Menos claro si dos funciones lo usan. | |
| Combinado | Ruidoso; endpoint cabe en metadata. | |

### Formato del archivo.
| Option | Description | Selected |
|--------|-------------|----------|
| JSON con wrapper de metadata + schema | Diff-friendly, traceable a corrida concreta. | ✓ |
| JSON puro (schema_of crudo) | Literal huérfano, sin trazabilidad. | |
| JSON + sidecar README.md | Duplicación. | |

### Estrategia de historia.
| Option | Description | Selected |
|--------|-------------|----------|
| Un solo archivo current; git history es la historia | Sin proliferación; git diff cubre el histórico. | ✓ |
| Snapshots timestamped acumulativos | Acumula files a perpetuidad. | |
| Current + dir histórico separado | Doble plumbing redundante. | |

---

## AMB-02 — ×100 Corruption Detection

### ¿Cómo detecta el probe la corrupción potencial?
| Option | Description | Selected |
|--------|-------------|----------|
| Doble check: estructural (separadores) + sanity de rango | Estructural detecta cambio de formato; rango detecta corrupción de magnitud. | ✓ |
| Solo estructural | No detecta `'1.415'` (entero) que también rompería. | |
| Solo sanity de rango | No detecta cambios de formato con valor que pasa rango. | |

---

## Date Selection

### Estrategia de selección de fechas.
| Option | Description | Selected |
|--------|-------------|----------|
| Derivado de today + helpers determinísticos | Cada run se mueve con el calendario; sin anchors hardcoded. | ✓ |
| Anchors fijos hardcoded | Reproducible pero pierde frescura. | |
| Mezcla anchors + derivados | Pierde la simplicidad de un solo patrón. | |

---

## Drift Detection on Re-runs

### ¿Qué hace el driver cuando schema_of difiere del snapshot committeado?
| Option | Description | Selected |
|--------|-------------|----------|
| Emite finding SHAPE OPEN + NO sobreescribe | Máxima visibilidad; humano decide aceptar el drift. | ✓ |
| Emite finding SHAPE OPEN + sobreescribe | Pierde snapshot anterior en disco. | |
| Sobreescribe sin emitir finding | Drift silencioso; rompe DRIFT-01. | |

---

## Redaction Usage in Driver

### Ámbito no tiene credenciales. ¿safe_print por uniformidad o print directo?
| Option | Description | Selected |
|--------|-------------|----------|
| safe_print con `secrets=()` por uniformidad | Mismo patrón cross-paquetes; Phases 3-5 reusan con su lista de secrets. | ✓ |
| print directo | Rompe uniformidad. | |
| Wrapper local `_log()` | Indirección sin valor. | |

---

## Claude's Discretion

- Nombres exactos de las sub-funciones probe más allá de las convenciones citadas (D-01).
- Texto exacto de las líneas de status a stdout más allá de los verbatim heredados de Phase 1.
- Estructura interna de `append_finding` (parser tactic del markdown, dedup por `fid`, lugar exacto del insert).
- Bounds finales del sanity de rango plausible en D-23 (100/100000 son draft).
- Convención de filename de snapshot cuando un endpoint sea compartido por dos funciones del cliente (no aplica en Phase 2).
- Schema exacto (keys, order, naming) del JSON envelope de D-21.
- Fecha futura para `probe_no_data` (D-24 sugiere `today + 60d`).
- Mecánica del `--accept-drift` o equivalente en D-25 (env var, flag, edición manual).
- Si `append_finding` modifica o no el ART block del header en cada call.

---

## Deferred Ideas

- Anonymize() para el payload de Ámbito (FX = info pública, sin PII; el pipeline se ejercita en pleno en Phases 3-5).
- `@pytest.mark.live` tests para Ámbito (marker registrado en Phase 1, disponible para uso futuro; Phase 2 elige driver-only).
- DRIFT-02 (informe final + cierre per-package) anclado a Phase 5.
- Mecánica de `--accept-drift` (Phase 2 implementa el flujo "detectar + no pisar + emitir finding").
- Refactor a clase Client por instancia / dedup sync-async (Out of Scope del ciclo).
- Disparar 403/429/5xx en vivo con loops (anti-feature explícita).
