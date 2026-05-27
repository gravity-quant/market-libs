"""Tooling de verificación en vivo a nivel de repo (NO publicable).

Este paquete vive en la raíz del monorepo y agrupa los helpers del harness de
verificación (redaction, env_gate, mutation_gate, findings, capture, anonymize,
schema). NO es un paquete distribuible ni un miembro del workspace de uv (D-05):
no tiene ``pyproject.toml`` ni se construye como wheel. Se importa por estar en
``sys.path`` cuando corren los drivers ``main_*.py`` y la suite de pytest.

El barrel de re-exports se define más adelante (plan 03, wiring del driver); por
ahora este módulo es sólo un marcador de paquete, sin re-exports.
"""

from __future__ import annotations
