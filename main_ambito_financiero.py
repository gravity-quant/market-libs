"""Smoke test del paquete `ambito-financiero-client`.

Uso::

    uv run --package ambito-financiero-client python main_ambito_financiero.py

No requiere credenciales: la API pública de Ámbito no usa auth.
"""

from __future__ import annotations

import datetime as dt

import ambito_financiero_client as ambito


def _last_business_day(today: dt.date) -> dt.date:
    """Lunes->viernes anterior; cualquier otro día -> el día previo."""
    d = today - dt.timedelta(days=1)
    while d.weekday() >= 5:  # 5 = sábado, 6 = domingo
        d -= dt.timedelta(days=1)
    return d


def main() -> None:
    print(f"ambito_financiero_client v{ambito.__version__}")

    fecha = _last_business_day(dt.date.today())
    print(f"-> get_dollar_banco_nacion({fecha.isoformat()})")
    try:
        precio = ambito.get_dollar_banco_nacion(fecha)
        print(f"   USD/ARS (Banco Nación, vendedor): {precio}")
    except ambito.AmbitoFinancieroNoDataError as exc:
        print(f"   sin datos para esa fecha: {exc}")


if __name__ == "__main__":
    main()
