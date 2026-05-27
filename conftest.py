from __future__ import annotations

import sys
from pathlib import Path

# Hace importable el paquete de tooling `verification/` (raíz del repo) bajo
# pytest --import-mode=importlib, que no agrega el rootdir a sys.path.
sys.path.insert(0, str(Path(__file__).parent))
