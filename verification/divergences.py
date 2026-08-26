"""Puente record-de-decode -> finding ``SHAPE`` para LIVE-TYP-01 (D-01/D-02).

Éste es el mecanismo del criterio 1 de la Phase 33: un ``logging.Handler`` que
traduce el record congelado de seis claves que emite ``<pkg>._decode._emit`` a
una llamada de :func:`verification.findings.append_finding`, más los dos
``ContextVar`` (endpoint + superficie) que son el transporte de D-02 — el
contexto que el record NO lleva y que el harness sí conoce.

El módulo es stdlib-only y NO importa ningún ``*_client``: se engancha por el
nombre del logger, nunca por el paquete. Tampoco toca el logger RAÍZ — sólo los
cinco ``getLogger("<pkg>")`` nombrados (eso está guardado tres veces: las reglas
``LOG`` de ruff, el grep ``lint-logging`` de CI y
``verification/test_logging_root_unchanged.py``). El nombre punteado del logger
raíz no aparece en este archivo ni siquiera en prosa: el criterio de aceptación
del plan lo grepea, y una mención en un comentario se lee igual que una
referencia en el código (precedente de la Phase 32, plan 32-02).

Tres endurecimientos, cada uno cerrando un canal de pérdida silenciosa medido en
``33-RESEARCH.md``. No son opcionales: un falso limpio es exactamente lo que este
milestone existe para eliminar.

- **P-1** — ``logging.getLogger("<pkg>")`` está en NOTSET, así que su nivel
  efectivo es el ``WARNING`` de root y todo record INFO (la especie ``extra``, 32
  de los 96 del piso ratificado) se descarta ANTES de que corra ningún handler.
  :func:`divergence_capture` sube el nivel a ``INFO`` y lo restaura al salir.
- **P-2** — ``_decode._emit`` corre la emisión entera dentro de un
  ``contextlib.suppress(Exception)`` (lock 9), así que una excepción del handler
  se pierde sin rastro. :meth:`DivergenceHandler.emit` envuelve TODO su cuerpo y
  tallya la falla en ``self.errors``, que el driver imprime como número.
- **P-3** — el allocator de fids del driver tiene que estar seedeado por encima
  de lo ya committeado; eso lo resuelve cada ``main_*.py`` con su propio
  ``_seed_fid_counter()`` y se inyecta acá vía ``next_fid``.

Privacidad (prohibición P-01 / T-33-01 / lock 11): ``title``, ``expected``,
``actual`` y ``diff`` se componen ÚNICAMENTE con las seis claves del record más
el endpoint y la superficie que este módulo mismo bindeó. Nunca con un valor del
wire — el archivo de findings es un artefacto git-committeado y público para
siempre. La ruta de campo tampoco se re-deriva: ``_decode._safe_key`` ya la
sanitizó aguas arriba.

Uso::

    from verification.divergences import PACKAGE_LOGGERS, divergence_capture, probe_context

    @probe_context(endpoint="/api/health", surface="sync")
    def probe_get_health_sync(client): ...

    with divergence_capture(PACKAGE_LOGGERS, next_fid=lambda slug: _next_fid()) as handler:
        probe_get_health_sync(client)
    print(f"divergencias={len(handler.seen)} handler_errors={len(handler.errors)}")
"""

from __future__ import annotations

import contextlib
import contextvars
import functools
import inspect
import logging
from collections.abc import Callable, Iterator, Sequence
from typing import Any, TypeVar, cast

from verification import findings as _findings

__all__ = [
    "PACKAGE_LOGGERS",
    "DivergenceHandler",
    "divergence_capture",
    "endpoint_scope",
    "probe_context",
]

_F = TypeVar("_F", bound=Callable[..., Any])

# ---------------------------------------------------------------------------
# Transporte de D-02: el contexto que el record de seis claves no lleva
# ---------------------------------------------------------------------------

# Module-private a propósito: son un canal del harness, NUNCA una clave del
# registro de ``_decode.py`` (que se mantiene byte-verbatim en las cinco copias).
# El default ``"-"`` es lo que un record emitido fuera de todo probe debe leer.
_ENDPOINT: contextvars.ContextVar[str] = contextvars.ContextVar("gsd_probe_endpoint", default="-")
_SURFACE: contextvars.ContextVar[str] = contextvars.ContextVar("gsd_probe_surface", default="-")

# Los cinco literales ``_LOGGER_NAME`` verificados en cada ``_decode.py``.
PACKAGE_LOGGERS: tuple[str, ...] = (
    "ambito_financiero_client",
    "higyrus_client",
    "iol_client",
    "market_data_client",
    "matriz_client",
)

# Nombre de logger -> slug del archivo de findings. ``findings._PKG_SLUG_RE``
# (WR-04) rechaza cualquier otra cosa, y ese ``ValueError`` lo tragaría el
# ``suppress`` de ``_emit`` (P-2). El guard de path-traversal vive allá y NO se
# reimplementa acá (T-33-06): este mapa sólo pasa los cinco literales.
_SLUG_BY_LOGGER: dict[str, str] = {
    "ambito_financiero_client": "ambito-financiero-client",
    "higyrus_client": "higyrus-client",
    "iol_client": "iol-client",
    "market_data_client": "market-data-client",
    "matriz_client": "matriz-client",
}


# ---------------------------------------------------------------------------
# El handler
# ---------------------------------------------------------------------------


class DivergenceHandler(logging.Handler):
    """Traduce el record de seis claves a un finding ``SHAPE``. JAMÁS levanta (P-2).

    Atributos públicos:

    ``seen``
        Set de 4-tuplas ``(slug, model, field_path, kind)``. Es **la unidad del
        censo**: el único número directamente comparable con los pisos de
        ``29-SIZING.md`` sin traducción, porque ambas corridas emiten el mismo
        record por el mismo walker con el mismo triple de dedupe (D-06, locks 1
        y 5). El conteo de findings NO lo es — con la superficie embebida en el
        título hay aproximadamente dos findings por triple.
    ``errors``
        Lista de ``"<TipoDeExcepción>: <mensaje>"``, una por falla del sink. Un
        pipeline de logging que puede fallar de forma invisible no sirve como
        registro de auditoría (T-33-04): el driver imprime ``len(errors)``.
    """

    def __init__(self, next_fid: Callable[[str], str]) -> None:
        # ``level=INFO`` admite también la especie ``extra``, que ``_emit``
        # manda por ``_LOGGER.info`` (lock 4: el crecimiento del vendor es
        # informativo, no un defecto).
        super().__init__(level=logging.INFO)
        self._next_fid = next_fid
        self.seen: set[tuple[str, str, str, str]] = set()
        self.errors: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Mapea un record de divergencia a un finding. Absorbe toda falla (P-2)."""
        try:
            slug = _SLUG_BY_LOGGER.get(str(getattr(record, "package", "")))
            kind = getattr(record, "divergence", None)
            if slug is None or kind is None:
                # Un record ajeno sobre el mismo logger no es nuestro. Hoy los
                # cinco paquetes no loguean nada más en este nivel, pero el
                # consumidor puede haber enganchado el logger para otra cosa.
                return
            # Las cuatro lecturas restantes del contrato de seis claves. El
            # ``type: ignore`` es inevitable y está documentado (P-9): son
            # atributos que ``Logger.makeRecord`` inyecta desde ``extra``, así
            # que no existen en la clase ``LogRecord`` que mypy conoce.
            model = str(record.model)  # type: ignore[attr-defined]
            path = str(record.field_path)  # type: ignore[attr-defined]
            declared = str(record.declared_type)  # type: ignore[attr-defined]
            observed = str(record.observed_type)  # type: ignore[attr-defined]
            kind = str(kind)

            surface = _SURFACE.get()
            endpoint = _ENDPOINT.get()

            # ANTES del sink: la unidad del censo tiene que sobrevivir una falla
            # de escritura, o un archivo de findings caído se leería como un
            # censo más chico en vez de como un error.
            self.seen.add((slug, model, path, kind))

            _findings.append_finding(
                slug,
                fid=self._next_fid(slug),
                class_="SHAPE",
                surface=surface,
                status="OPEN",
                # Determinístico y portador de identidad: este string ES la
                # clave de dedupe cross-run (33-01-SUMMARY.md, selección
                # ``surface-in-title-write-new``).
                title=f"{model}{path}: {kind} (declared={declared}, observed={observed}) [{surface}]",
                expected=f"model declares {declared}",
                actual=f"wire sent {observed}",
                diff=f"{declared} -> {observed} at {model}{path} via {endpoint}",
                idempotent_by_title=True,
            )
        except Exception as exc:
            # NUNCA propagar: ``_decode._emit`` corre dentro de un
            # ``contextlib.suppress(Exception)`` y un raise acá se pierde sin
            # rastro. ``handleError`` solo no alcanza — escribe a stderr y se
            # pierde en el scrollback de un driver de 3000 líneas.
            self.errors.append(f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Instalación (cierra P-1)
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def divergence_capture(
    logger_names: Sequence[str], *, next_fid: Callable[[str], str]
) -> Iterator[DivergenceHandler]:
    """Adjunta el handler a cada logger y SUBE SU NIVEL. Restaura ambos al salir.

    ``INFO`` y no ``DEBUG``: los cinco paquetes no tienen ni un solo call site
    ``_LOGGER.info`` / ``_LOGGER.debug`` fuera del stream de divergencias, así
    que ``INFO`` admite exactamente la señal y nada más. ``DEBUG`` además
    admitiría los records de request de ``_transport.py``, que son sensibles a
    redacción y sepultarían la señal.

    Nunca toca el logger raíz. Restaurar el nivel y el set de handlers es lo
    que impide secuestrar la configuración de logging del consumidor (T-33-05).
    """
    handler = DivergenceHandler(next_fid)
    restore: list[tuple[logging.Logger, int]] = []
    try:
        for name in logger_names:
            logger = logging.getLogger(name)
            restore.append((logger, logger.level))
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)
        yield handler
    finally:
        for logger, level in restore:
            logger.removeHandler(handler)
            logger.setLevel(level)


# ---------------------------------------------------------------------------
# Binding de contexto (resuelve D-02 y P-5)
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def endpoint_scope(endpoint: str) -> Iterator[None]:
    """Re-bindea SÓLO el endpoint dentro de un probe (P-5).

    Para los probes que golpean más de un endpoint bajo una sola superficie
    (p.ej. ``main_market_data.py::probe_health_sync``, que llama ``get_health()``
    y ``get_health_feed()``): sin esto las divergencias del segundo endpoint se
    atribuirían al primero.
    """
    token = _ENDPOINT.set(endpoint)
    try:
        yield
    finally:
        _ENDPOINT.reset(token)


def probe_context(
    endpoint: str,
    surface: str,
    *,
    decode_error: type[BaseException] | None = None,
    on_decode_error: Callable[[str, str, BaseException], Any] | None = None,
) -> Callable[[_F], _F]:
    """Decorador que bindea endpoint+superficie alrededor de un probe (D-02).

    El handler lee los ``ContextVar`` en tiempo de ``emit``: ``logging`` despacha
    los handlers sincrónicamente en el frame que emite, así que ve el binding del
    caller. Los probes async de los cinco drivers se esperan secuencialmente
    dentro de un único ``asyncio.run`` (sin ``gather``, sin ``TaskGroup``), así
    que ``set``/``reset`` dentro de una corrutina es correcto.

    ``decode_error`` / ``on_decode_error`` son el seam por el cual el driver
    aporta su propio ``<Pkg>DecodeError`` y su propio fallback con forma de
    ``ProbeResult``: la clase de excepción difiere por paquete y este módulo no
    importa ningún ``*_client``. Cuando se suministran, el wrapper intercepta esa
    excepción y devuelve, sin tocarlo, lo que ``on_decode_error(nombre_del_probe,
    surface, exc)`` retorne.
    """

    def deco(fn: _F) -> _F:
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                ep_token = _ENDPOINT.set(endpoint)
                sf_token = _SURFACE.set(surface)
                try:
                    return await fn(*args, **kwargs)
                except _catchable(decode_error) as exc:
                    if on_decode_error is None:
                        raise
                    return on_decode_error(fn.__name__, surface, exc)
                finally:
                    _ENDPOINT.reset(ep_token)
                    _SURFACE.reset(sf_token)

            return cast("_F", async_wrapper)

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            ep_token = _ENDPOINT.set(endpoint)
            sf_token = _SURFACE.set(surface)
            try:
                return fn(*args, **kwargs)
            except _catchable(decode_error) as exc:
                if on_decode_error is None:
                    raise
                return on_decode_error(fn.__name__, surface, exc)
            finally:
                _ENDPOINT.reset(ep_token)
                _SURFACE.reset(sf_token)

        return cast("_F", sync_wrapper)

    return deco


class _NeverRaised(BaseException):
    """Centinela inatrapable: nada la levanta jamás.

    Permite escribir UNA sola forma de wrapper en vez de dos por superficie
    (con y sin rama de decode). Cuando el driver no declara ``decode_error``, la
    cláusula ``except`` queda tipada contra esta clase y por construcción nunca
    matchea.
    """


def _catchable(decode_error: type[BaseException] | None) -> type[BaseException]:
    """Devuelve la clase que la cláusula ``except`` del wrapper debe mirar."""
    return _NeverRaised if decode_error is None else decode_error
