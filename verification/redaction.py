"""Redacción de credenciales con defensa en profundidad (HARN-03, D-13).

Dos capas:

- ``redact(value)`` — primera defensa en el sitio del print: devuelve sólo un
  prefijo corto + elipsis de un valor sensible; el valor completo nunca es
  alcanzable desde el retorno.
- ``safe_print(text, secrets)`` — segunda defensa: enmascara cualquier credencial
  conocida (de >= 4 caracteres) que aparezca en cualquier parte del texto, de modo
  que un leak vía un ``print`` accidental de un dict crudo quede cubierto de forma
  estructural y no por disciplina.

Nunca imprimir un global de credencial como par nombre+valor.
"""

from __future__ import annotations

import re

__all__ = ["redact", "safe_print"]

# Marcador deliberado con guillemets (no ASCII a propósito: no colisiona con los
# `<`/`>` que puedan aparecer en payloads reales).
_REDACTED = "‹REDACTED›"  # noqa: RUF001

# Defensa por patrón: enmascara un token Bearer reflejado por el servicio aunque
# NO esté en la lista exacta de `secrets` o sea más corto que el umbral de
# longitud (WR-03 — no depender sólo de la lista de secretos conocidos). El
# charset cubre tokens base64url/JWT (``A-Za-z0-9._~+/=-``) y se detiene en el
# delimitador (comilla, llave, espacio), sin tragarse el cierre del contenedor.
_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", re.IGNORECASE)


def redact(value: str | None, *, keep: int = 4) -> str:
    """Devuelve sólo un prefijo + elipsis para un valor sensible."""
    if not value:
        return "<empty>"  # nunca echar "" ni producir un "…" pelado
    if len(value) <= keep:
        return "…"  # demasiado corto para mostrar un prefijo de forma segura
    return f"{value[:keep]}…"


def safe_print(text: str, secrets: list[str]) -> None:
    """Imprime ``text`` enmascarando credenciales conocidas y tokens Bearer.

    Dos pasadas de defensa en profundidad:

    1. Reemplaza cada valor de ``secrets`` (de >= 4 caracteres) que aparezca en
       cualquier parte del texto. El umbral evita el bug ``replace("", marker)``
       (Pitfall 3) y el ruido de enmascarar secretos triviales.
    2. Enmascara cualquier ``Bearer <token>`` reflejado, aunque el token no esté
       en ``secrets`` o sea más corto que el umbral (WR-03).
    """
    masked = text
    for secret in secrets:
        # Saltar vacíos/cortos: replace("", marker) inserta el marcador entre
        # cada caracter (bug verificado concourse #4656).
        if secret and len(secret) >= 4:
            masked = masked.replace(secret, _REDACTED)
    masked = _BEARER.sub(rf"\1{_REDACTED}", masked)
    print(masked)
