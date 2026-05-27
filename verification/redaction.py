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

__all__ = ["redact", "safe_print"]


def redact(value: str | None, *, keep: int = 4) -> str:
    """Devuelve sólo un prefijo + elipsis para un valor sensible."""
    if not value:
        return "<empty>"  # nunca echar "" ni producir un "…" pelado
    if len(value) <= keep:
        return "…"  # demasiado corto para mostrar un prefijo de forma segura
    return f"{value[:keep]}…"


def safe_print(text: str, secrets: list[str]) -> None:
    """Imprime ``text`` enmascarando cualquier valor de credencial conocido."""
    masked = text
    for secret in secrets:
        # Saltar vacíos/cortos: replace("", marker) inserta el marcador entre
        # cada caracter (bug verificado concourse #4656).
        if secret and len(secret) >= 4:
            # Marcador deliberado con guillemets (no ASCII a propósito: no colisiona
            # con `<`/`>` que puedan aparecer en payloads reales).
            masked = masked.replace(secret, "‹REDACTED›")  # noqa: RUF001
    print(masked)
