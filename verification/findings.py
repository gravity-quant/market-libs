"""Helper de archivo de hallazgos clasificados (HARN-05/D-07/08/09).

El entregable primario es la plantilla documentada
``.planning/verification/FINDINGS-TEMPLATE.md``; este módulo es un helper de
conveniencia que renderiza el esqueleto de encabezado + índice para iniciar un
archivo de hallazgos por paquete en ``.planning/verification/<pkg>-findings.md``.

Clases fijas (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA,
ANTI-BOT. Ciclo de estados (D-08): OPEN -> CONFIRMED -> FIXED, más terminales
EXPECTED/NO-FIX. No hay campo de severidad.

Uso::

    from verification.findings import new_findings, write_findings

    write_findings("higyrus")   # crea .planning/verification/higyrus-findings.md
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["FINDING_CLASSES", "STATUS_LIFECYCLE", "findings_path", "new_findings", "write_findings"]

# Raíz del repo = el directorio que contiene el paquete ``verification/``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_FINDINGS_DIR = _REPO_ROOT / ".planning" / "verification"

# Clases fijas de hallazgos (D-09) — orden documentado.
FINDING_CLASSES: tuple[str, ...] = (
    "SHAPE",
    "AUTH",
    "ERROR-MAP",
    "PARAM",
    "SYNC-ASYNC-DRIFT",
    "NO-DATA",
    "ANTI-BOT",
)

# Ciclo de estados (D-08) — sin campo de severidad.
STATUS_LIFECYCLE: tuple[str, ...] = ("OPEN", "CONFIRMED", "FIXED", "EXPECTED", "NO-FIX")


def findings_path(pkg: str) -> Path:
    """Ruta del archivo de hallazgos para ``pkg``: ``.planning/verification/<pkg>-findings.md``."""
    return _FINDINGS_DIR / f"{pkg}-findings.md"


def new_findings(pkg: str) -> str:
    """Renderiza el esqueleto (encabezado ART + índice vacío) de un archivo de hallazgos."""
    classes = ", ".join(FINDING_CLASSES)
    lifecycle = " -> ".join(("OPEN", "CONFIRMED", "FIXED")) + " (+ terminal EXPECTED/NO-FIX)"
    return (
        f"# Findings: {pkg}-client\n"
        "\n"
        "## Run Context (ART)\n"
        "- Timestamp: <ISO-8601>\n"
        "- Resolved base URL / env: <url> (<remarkets|prod|public>)\n"
        "- Market hours note: <abierto|cerrado — afecta paths sesión-dependientes>\n"
        "\n"
        f"<!-- Clases (D-09): {classes} -->\n"
        f"<!-- Estados (D-08): {lifecycle}. Sin campo de severidad. -->\n"
        "\n"
        "## Index\n"
        "| ID | Class | Surface | Status |\n"
        "|----|-------|---------|--------|\n"
    )


def write_findings(pkg: str, *, overwrite: bool = False) -> Path:
    """Crea ``.planning/verification/<pkg>-findings.md`` con el esqueleto y devuelve la ruta.

    Si el archivo ya existe y ``overwrite`` es ``False``, no lo sobreescribe.
    """
    _FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
    path = findings_path(pkg)
    if path.exists() and not overwrite:
        return path
    path.write_text(new_findings(pkg), encoding="utf-8")
    return path
