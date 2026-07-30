"""Runner agregado del harness de verificación en vivo (HARN-01 / D-14).

Corre los cinco drivers ``main_*.py`` —uno por paquete— y reporta un resumen
agregado RAN/SKIPPED/FAILED. Nunca se detiene ante un SKIPPED ni ante un driver
que falle: captura el resultado de cada uno y continúa con el siguiente (D-14).

Uso::

    uv run python main_verify.py

Cada driver se ejecuta en su propio subproceso vía
``uv run --package <pkg> python main_<name>.py`` (RESEARCH Open Question 1),
lo que aísla el estado singleton de módulo de cada cliente y permite que cada
driver haga ``sys.exit(0)`` ante credenciales faltantes sin afectar al runner.

El runner imprime sólo la clasificación por paquete (RAN / SKIPPED), nunca el
stdout crudo del hijo: un driver podría haber impreso un payload que reflejara
una credencial, así que re-emitirlo verbatim sería un leak (T-01-14 / HARN-03).
"""

from __future__ import annotations

import re
import subprocess

# (paquete uv, script driver). Los cuatro paquetes verificables del alcance más
# wallets (stub) — el runner los corre todos y reporta su estado.
_DRIVERS: list[tuple[str, str]] = [
    ("iol-client", "main_iol.py"),
    ("higyrus-client", "main_higyrus.py"),
    ("matriz-client", "main_matriz.py"),
    ("ambito-financiero-client", "main_ambito_financiero.py"),
    ("wallets-client", "main_wallets.py"),
    ("market-data-client", "main_market_data.py"),
]

# La línea del env-gate tiene forma `SKIPPED <pkg>: missing ...` (con dos puntos);
# la del mutation gate es `SKIPPED (mutating, guard off)` (sin dos puntos). Sólo la
# primera significa que el driver NO corrió por credenciales faltantes: clasificar
# por el prefijo genérico `SKIPPED ` confundiría una corrida matriz exitosa con un
# SKIP (WR-01).
_ENV_SKIP = re.compile(r"^SKIPPED \S.*:")


def _run_driver(package: str, script: str) -> str:
    """Corre un driver en subproceso y clasifica su resultado.

    Devuelve:

    - ``"SKIPPED"`` si el stdout del hijo contiene la línea del env-gate
      ``SKIPPED <pkg>: ...`` (credenciales faltantes);
    - ``"FAILED"`` si el driver corrió pero terminó con código != 0 sin SKIP de
      credenciales (crash, traceback, auth no manejado), o si el subproceso no
      pudo lanzarse (WR-02);
    - ``"RAN"`` en caso contrario.

    Nunca lanza ni se detiene: captura cualquier fallo del hijo y lo clasifica —
    el runner siempre continúa con el próximo paquete (D-14).
    """
    try:
        result = subprocess.run(
            ["uv", "run", "--package", package, "python", script],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        # No se pudo lanzar el subproceso (uv ausente, etc.): es un fallo duro, no
        # un SKIP de credenciales. No detener el lote.
        print(f"   no se pudo ejecutar: {type(exc).__name__}")
        return "FAILED"

    # Clasificación por la línea verbatim del env-gate; NO se re-emite el stdout
    # crudo del hijo (podría reflejar una credencial). La línea del mutation gate
    # (`SKIPPED (mutating, guard off)`, sin dos puntos) NO cuenta como SKIP (WR-01).
    for line in result.stdout.splitlines():
        if _ENV_SKIP.match(line):
            return "SKIPPED"
    if result.returncode != 0:
        return "FAILED"
    return "RAN"


def main() -> None:
    print("== verificación agregada (RAN/SKIPPED/FAILED por paquete) ==")
    results: list[tuple[str, str]] = []
    for package, script in _DRIVERS:
        status = _run_driver(package, script)
        # Sólo el estado por paquete; nunca el payload completo del hijo.
        print(f"{status:<8} {package}")
        results.append((package, status))

    ran = sum(1 for _, s in results if s == "RAN")
    skipped = sum(1 for _, s in results if s == "SKIPPED")
    failed = sum(1 for _, s in results if s == "FAILED")
    print("== resumen ==")
    print(f"RAN: {ran}  SKIPPED: {skipped}  FAILED: {failed}  (total: {len(results)})")


if __name__ == "__main__":
    main()
