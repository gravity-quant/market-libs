"""Volcado de payload crudo al staging gitignored (HARN-06/D-11).

``capture`` escribe el payload *crudo* (con la PII real tal como vino de la API)
EXCLUSIVAMENTE bajo ``.planning/verification/captures/``, que está en
``.gitignore``: el payload crudo nunca puede entrar a git por construcción.

Esta es la primera etapa del pipeline de dos fases (D-11):

    captura cruda -> captures/ (gitignored) -> anonymize -> revisión humana
    -> fixture committeable bajo packages/<pkg>/tests/

``capture`` NO anonimiza: la anonimización es una etapa separada
(:func:`verification.anonymize.anonymize`).

Uso::

    from verification.capture import capture

    path = capture("ambito", "dollar", payload)   # .../captures/ambito-dollar.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = ["capture", "captures_dir"]

# Raíz del repo = el directorio que contiene el paquete ``verification/``.
# Se resuelve respecto de la ubicación de este módulo, no del cwd, para que
# la ruta del staging sea estable sin importar desde dónde se invoque.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_CAPTURES_DIR = _REPO_ROOT / ".planning" / "verification" / "captures"


def captures_dir() -> Path:
    """Devuelve la ruta del staging gitignored ``.planning/verification/captures/``."""
    return _CAPTURES_DIR


def capture(pkg: str, endpoint: str, payload: Any) -> Path:
    """Vuelca un payload crudo a ``captures/<pkg>-<endpoint>.json`` y devuelve la ruta.

    El payload crudo (con PII real) aterriza ÚNICAMENTE en el staging gitignored.
    No anonimiza: la anonimización es una etapa posterior y separada.
    """
    _CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    path = _CAPTURES_DIR / f"{pkg}-{endpoint}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
