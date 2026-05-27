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
- :mod:`verification.findings` — ``new_findings`` / ``write_findings``: plantilla
  de hallazgos (HARN-05).

No es un miembro del workspace uv ni un paquete publicable: vive en la raíz del
repo y se importa porque la raíz está en ``sys.path`` (Patrón 1). No tiene
``pyproject.toml`` ni se registra en ``[tool.uv.workspace] members`` (D-05).
"""

from __future__ import annotations

from verification.anonymize import Denylist, anonymize
from verification.capture import capture
from verification.env_gate import require_env
from verification.findings import new_findings, write_findings
from verification.mutation_gate import mutating_allowed
from verification.redaction import redact, safe_print
from verification.schema import schema_of

__all__ = [
    "Denylist",
    "anonymize",
    "capture",
    "mutating_allowed",
    "new_findings",
    "redact",
    "require_env",
    "safe_print",
    "schema_of",
    "write_findings",
]
