---
phase: 41
kind: audit-contract
created: 2026-08-31
audited_commit_sha: 37a83fe693a303a551f4374f48fe6fc5521804f7
audit_baseline_head: 6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5
frozen_tree_verified: true
---

# Phase 41 — Contrato de auditoría

> Documento autoritativo de la fase. Los cinco planes de la Wave 2 (41-02..41-06) y el plan de
> cierre (41-07) **no toman decisiones de formato ni de disposición**: las toman de aquí. Un
> ejecutor de la Wave 2 debe poder producir su artefacto leyendo sólo este archivo más su propio
> `{N}-VALIDATION.md`.

---

## 1. Identidad del árbol auditado

La auditoría retroactiva de las fases 35–39 sólo tiene valor si el árbol de fuente que se
re-ejecuta hoy es **el mismo** que shipeó en v1.7. Si fuente de v1.8 aterrizara antes de que las
cinco disposiciones queden escritas, cada evidencia `VERIFIED-NOW` estaría atribuida al árbol
equivocado y el criterio 1 del ROADMAP quedaría no re-verificable por terceros.

### 1.1 Los dos SHA de atribución

| Clave | Valor | Cómo se obtuvo |
|-------|-------|----------------|
| `audited_commit_sha` | `37a83fe693a303a551f4374f48fe6fc5521804f7` | `git rev-parse v1.7^{commit}` |
| `audit_baseline_head` | `6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5` | `git rev-parse HEAD` (sesión de auditoría, 2026-08-31) |
| `frozen_tree_verified` | `true` | `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → **exit 0** |

**`audited_commit_sha` es el commit, no el objeto-tag.** `v1.7` es un tag **anotado**
(`git cat-file -t v1.7` → `tag`), de modo que `git rev-parse v1.7` a secas devuelve el *objeto-tag*
(`c4dc6ea…`), no el commit. Declarar ese valor en los cinco artefactos haría el criterio 1 no
re-verificable por cualquiera que re-corriese la comprobación. **La única forma admitida de
resolver el tag en esta fase es `git rev-parse v1.7^{commit}`.** Si el valor resuelto difiere de
`37a83fe693a303a551f4374f48fe6fc5521804f7`, el plan **aborta**: toda la medición de
`41-RESEARCH.md` queda invalidada y hay que re-medir.

**`audit_baseline_head` se captura una sola vez, aquí, y se copia literal.** El HEAD se mueve con
cada commit de la fase; si cada plan lo re-capturase, los seis artefactos declararían seis valores
distintos y el conjunto sería ilegible. Los planes 41-02..41-07 **copian** el literal de esta
tabla, no lo re-derivan.

### 1.2 La prueba de identidad del árbol

```bash
git diff --quiet v1.7 HEAD -- . ':(exclude).planning'
# exit code: 0   ← ejecutado 2026-08-31 en la sesión de auditoría
```

El pathspec de exclusión `':(exclude).planning'` es **obligatorio**: `.planning/` churnea
legítimamente durante toda la fase (cada commit de auditoría escribe ahí), y sin excluirlo la
prueba fallaría siempre y por una razón irrelevante. Lo que la prueba afirma es exactamente:
*ningún byte de fuente de producto, de `.github/`, de `tools/`, de `verification/` ni de
`packages/` cambió entre el tag `v1.7` y el HEAD de esta sesión.*

Si el comando sale distinto de 0 en cualquier momento de la fase: **ABORTAR**. Significa que fuente
de v1.8 aterrizó antes de que la auditoría cerrara, lo que invalida la atribución entera. No se
continúa, y no se "documenta la excepción": la excepción no existe, la fase se re-planifica contra
un árbol nuevo.

### 1.3 Criterio 1 es un invariante continuo, no un gate de una sola vez

Esta comprobación **no** se corre una vez al principio y se olvida. Se re-verifica:

1. Al inicio de **cada** plan de la Wave 2 (41-02, 41-03, 41-04, 41-05, 41-06), antes de escribir.
2. Al final de **cada** tarea de la Wave 2, como parte de su bloque `<verify><automated>`.
3. Otra vez en el cierre (41-07), como parte del gate de contención de alcance.

El motivo: la Wave 2 corre en paralelo con el resto de la vida del repo. La ventana en la que un
commit de fuente puede colarse no es el instante inicial, es toda la duración de la fase.

### 1.4 Versiones de herramienta medidas en esta sesión

Todas las evidencias `VERIFIED-NOW` de las fases 35–39 se producen con estas versiones. Se declaran
para que un tercero pueda reproducir la corrida, y porque **hay bookkeeping stale que nombrar**.

| Herramienta | Versión medida (2026-08-31) | Comando |
|-------------|-----------------------------|---------|
| `uv` | 0.11.3 (45da18ac3 2026-04-01 aarch64-apple-darwin) | `uv --version` |
| `pytest` (vía uv) | 9.0.3 | `uv run pytest --version` |
| `mypy` | 1.20.2 (compiled: yes) | `uv run mypy --version` |
| `ruff` | 0.15.12 | `uv run ruff --version` |
| `git` | 2.39.5 (Apple Git-154) | `git --version` |
| `node` | v24.15.0 | `node --version` |

**Hallazgo de bookkeeping a nombrar, no a corregir en silencio:** la tabla `## Test Infrastructure`
de `35-VALIDATION.md` declara **pytest 8.3**. El real es **9.0.3**. Esa fila es stale desde antes de
esta fase. Se **nombra** en la sección `### Hallazgos de bookkeeping` del artefacto de la Phase 35
(§5, bloque 6); no se reescribe la tabla histórica sin dejar constancia del cambio. El mismo trato
aplica a cualquier otra versión stale que aparezca en los cinco archivos.

### 1.5 Estado de partida del árbol de locks

Medido en esta sesión, y usado como línea base del criterio 4 (D-08: se esperan **cero** archivos
de test nuevos):

| Medida | Valor de partida | Comando |
|--------|------------------|---------|
| Archivos `verification/test_*.py` | **52** | `ls verification/test_*.py \| wc -l` |
| De ésos, enrolados en el allowlist de CI | **12** | `ci.yml:81-92` |
| `git status --porcelain verification/` | vacío | — |

Los tres valores deben ser idénticos al cierre de la fase (41-07 los re-mide). Un 53 sería la señal
de que la contingencia de D-08 se disparó.
