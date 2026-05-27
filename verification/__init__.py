"""Harness de verificación en vivo (módulo de raíz del repo, no publicable).

Este paquete reúne las utilidades genéricas que las fases 2-5 usan para
ejercitar los clientes contra las APIs reales de forma segura:

- :mod:`verification.schema` — ``schema_of``: snapshot de claves + tipos (D-12).
- :mod:`verification.capture` — ``capture``: vuelca payloads crudos al staging
  gitignored ``.planning/verification/captures/`` (HARN-06/D-11).
- :mod:`verification.anonymize` — ``Denylist`` + ``anonymize``: reemplazo de PII
  que preserva el formato (HARN-06/D-10).
- :mod:`verification.findings` — helper de plantilla de hallazgos (HARN-05).

No es un miembro del workspace uv ni un paquete publicable: vive en la raíz del
repo y se importa porque la raíz está en ``sys.path`` (Patrón 1). No tiene
``pyproject.toml`` ni se registra en ``[tool.uv.workspace] members``.
"""

from __future__ import annotations

from verification.capture import capture
from verification.schema import schema_of

__all__ = [
    "capture",
    "schema_of",
]
