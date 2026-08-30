"""Harness de verificación en vivo (módulo de raíz del repo, NO publicable).

Este paquete vive en la raíz del monorepo y agrupa los helpers genéricos del
harness de verificación que las fases 2-5 usan para ejercitar los clientes
contra las APIs reales de forma segura:

- :mod:`verification.redaction` — ``redact`` / ``safe_print``: nunca exponen un
  secreto completo en logs ni reportes (HARN-03).
- :mod:`verification.env_gate` — ``require_env``: salta limpio (sin lanzar) si
  faltan credenciales (HARN-01/D-15).
- :mod:`verification.mutation_gate` — ``mutating_allowed``: doble compuerta para
  operaciones que mutan estado en la API real (HARN-02/D-16).
- :mod:`verification.schema` — ``schema_of``: snapshot de claves + tipos (D-12).
- :mod:`verification.capture` — ``capture``: vuelca payloads crudos al staging
  gitignored ``.planning/verification/captures/`` (HARN-06/D-11).
- :mod:`verification.anonymize` — ``Denylist`` + ``anonymize``: reemplazo de PII
  que preserva el formato (HARN-06/D-10).
- :mod:`verification.findings` — ``new_findings`` / ``write_findings`` /
  ``append_finding``: plantilla de hallazgos + append idempotente por fid,
  preservando status humano CONFIRMED/FIXED/EXPECTED/NO-FIX (HARN-05/D-10).
- :mod:`verification.divergences` — ``DivergenceHandler`` / ``divergence_capture``
  / ``probe_context`` / ``endpoint_scope``: puente del record de decode de seis
  claves a un finding ``SHAPE``, con el endpoint y la superficie que el record no
  lleva viajando por ``ContextVar`` (LIVE-TYP-01, D-01/D-02).
- :mod:`verification.run_evidence` — ``write_run_evidence`` / ``read_run_evidence``
  / ``run_evidence_path`` / ``probes_executed``: sobre de evidencia de corrida por
  paquete. Persiste los MIEMBROS de ``DivergenceHandler.seen`` (no sólo su conteo)
  y el número de probes ejecutados, que es el predicado de no-vacuidad del cierre
  de ciclo (Phase 39, D-09/D-10).

No es un miembro del workspace uv ni un paquete publicable: vive en la raíz del
repo y se importa porque la raíz está en ``sys.path`` (Patrón 1). No tiene
``pyproject.toml`` ni se registra en ``[tool.uv.workspace] members`` (D-05).
"""

from __future__ import annotations

from verification.anonymize import Denylist, anonymize
from verification.capture import capture
from verification.divergences import (
    DivergenceHandler,
    divergence_capture,
    endpoint_scope,
    probe_context,
)
from verification.env_gate import require_env
from verification.findings import append_finding, new_findings, write_findings
from verification.mutation_gate import mutating_allowed
from verification.redaction import redact, safe_print
from verification.run_evidence import (
    probes_executed,
    read_run_evidence,
    run_evidence_path,
    write_run_evidence,
)
from verification.safemodel_diff import diff_safemodel_bidirectional
from verification.schema import schema_of

__all__ = [
    "Denylist",
    "DivergenceHandler",
    "anonymize",
    "append_finding",
    "capture",
    "diff_safemodel_bidirectional",
    "divergence_capture",
    "endpoint_scope",
    "mutating_allowed",
    "new_findings",
    "probe_context",
    "probes_executed",
    "read_run_evidence",
    "redact",
    "require_env",
    "run_evidence_path",
    "safe_print",
    "schema_of",
    "write_findings",
    "write_run_evidence",
]
