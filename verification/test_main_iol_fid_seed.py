"""D-16 / D-24 — ``main_iol.py`` seedea su allocator de fids desde el findings file.

``verification/test_findings_fid_seed.py`` ya fija el modo de falla genérico a
nivel del **helper** (``max_existing_fid``). Lo que faltaba —y lo que este
archivo cierra— es el binding a nivel **driver**: nada asertaba que
``main_iol.py`` llame al seed, así que el helper podía existir, estar probado y
seguir sin usarse.

Modo de falla concreto (30-VERIFICATION.md cuarto ciclo, truth 7 / 30-REVIEW.md
CR-01). ``main_iol._fid_counter`` arranca en ``0`` en cada proceso y ``_next_fid``
sólo incrementa. El artefacto durable ``.planning/verification/iol-client-findings.md``
ya lleva ``F-01`` (SHAPE, **OPEN**, arrastrado por el operador desde la Phase 17)
y ``F-02`` (AUTH, **FIXED**, con triage humano escrito a mano). En la próxima
corrida viva:

- el primer finding emitido toma ``fid=F-01``; como su status registrado ES
  ``OPEN``, ``append_finding`` **no** corta y **reescribe el bloque de detalle de
  F-01 en el lugar** con contenido ajeno — el triage del operador se pierde;
- el segundo toma ``fid=F-02``; como su status registrado **no** es ``OPEN``, el
  short-circuit lo convierte en un no-op **silencioso**, mientras ``main()``
  igual lo cuenta en ``FINDING=N`` y el ``SUMMARY`` reporta éxito.

El driver hermano ``main_market_data.py`` ya resuelve esto (``_seed_fid_counter``
definido en 267, llamado en 3221 inmediatamente después de ``write_findings``).
Este archivo pide la misma forma para ``main_iol.py`` y la deja bajo un lock AST
para que un seed definido-pero-no-llamado (o llamado fuera de orden) falle acá.

Los tests son **offline**: sin red, sin credenciales, sin ``.env``, sin
``httpx_mock``. Todo ``Client`` se construye sobre ``httpx.MockTransport`` con un
token ya fresco, así que la capa de auth nunca emite una request.
"""

from __future__ import annotations

import ast
import time
from collections.abc import Callable
from pathlib import Path

import httpx
import main_iol
import pytest

from iol_client import Client
from verification import findings as findings_module
from verification.findings import append_finding, findings_path, max_existing_fid

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER_PATH = _REPO_ROOT / "main_iol.py"
_BASE_URL = "https://api.test"

# Título que sólo puede provenir del triage humano ya committeado: su
# supervivencia (o su desaparición) es la evidencia de si F-01 fue reescrito.
_OPERATOR_TITLE = "missing assumed key `simbolo` in get_quote"

# Título que el probe real emite para un 500 (``probe_get_quote_sync``, rama
# ``IOLAPIError``). Se lee del driver por constante para que un rename allá no
# vuelva vacuos los asserts de acá sin avisar.
_PROBE_TITLE = "get_quote_sync recibió APIError inesperado"


# ---------------------------------------------------------------------------
# Fixtures — tres cinturones independientes contra tocar artefactos reales
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Aísla el findings dir, el token cache en disco y el state del driver.

    Espeja ``verification/test_main_iol_exception_redaction.py``. ``_FINDINGS_DIR``
    repuntado a ``tmp_path`` impide que un ``append_finding`` real —que acá corre
    de verdad, a propósito— alcance ``.planning/verification/``.
    ``IOL_TOKEN_CACHE_PATH`` repuntado impide que un ``Client`` de test lea,
    pise o borre el cache de refresh token real del operador (30-09 deviación 1).
    """
    monkeypatch.setattr(findings_module, "_FINDINGS_DIR", tmp_path)
    monkeypatch.setenv("IOL_TOKEN_CACHE_PATH", str(tmp_path / "token-cache.json"))
    monkeypatch.setattr(main_iol, "_fid_counter", 0)
    monkeypatch.setattr(main_iol, "_auth_failed", False)
    monkeypatch.setattr(main_iol, "_auth_failure_reason", "")


# ---------------------------------------------------------------------------
# Helpers — la forma real de un archivo triageado + un cliente offline
# ---------------------------------------------------------------------------


def _add_finding(fid: str, *, title: str, promote_to_fixed: bool) -> None:
    """Agrega ``fid`` al findings file de ``iol-client``, opcionalmente promovido a FIXED.

    Reusa la forma de ``verification/test_findings_fid_seed.py::_add_promoted_finding``
    (append como OPEN y luego reescritura del row del índice + la línea meta del
    detalle) en vez de escribir markdown a mano: así el archivo de fixture pasa
    por el mismo serializador que el driver real ejercita.
    """
    append_finding(
        main_iol._PKG,
        fid=fid,
        class_="SHAPE",
        surface="both",
        status="OPEN",
        title=title,
        expected=f"expected {fid}",
        actual=f"actual {fid}",
        diff=f"diff {fid}",
    )
    if not promote_to_fixed:
        return
    path = findings_path(main_iol._PKG)
    text = path.read_text(encoding="utf-8")
    text = text.replace(f"| {fid} | SHAPE | both | OPEN |", f"| {fid} | SHAPE | both | FIXED |")
    text = text.replace(
        "**Class:** `SHAPE` . **Surface:** `both` . **Status:** `OPEN`",
        "**Class:** `SHAPE` . **Surface:** `both` . **Status:** `FIXED`",
    )
    path.write_text(text, encoding="utf-8")


def _seed_committed_findings_shape() -> None:
    """Reproduce el estado committeado real: F-01 OPEN (operador) + F-02 FIXED."""
    _add_finding("F-01", title=_OPERATOR_TITLE, promote_to_fixed=False)
    _add_finding(
        "F-02", title="_token_expires_at no se renovó tras refresh path", promote_to_fixed=True
    )


def _mock_client(handler: Callable[[httpx.Request], httpx.Response]) -> Client:
    """``Client`` sobre ``httpx.MockTransport`` con token pre-sembrado (offline)."""
    inner = httpx.Client(transport=httpx.MockTransport(handler), base_url=_BASE_URL)
    return Client(
        base_url=_BASE_URL,
        username="u",
        password="p",
        token="tok-de-prueba",
        token_expires_at=time.time() + 3600,
        http_client=inner,
    )


def _handler_500(request: httpx.Request) -> httpx.Response:
    del request
    return httpx.Response(500, text='{"mensaje": "error de servidor"}')


def _findings_text() -> str:
    return findings_path(main_iol._PKG).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Contrato del seed
# ---------------------------------------------------------------------------


def test_seed_raises_the_counter_above_every_recorded_fid() -> None:
    """Con F-01/F-02 registrados, el próximo fid emitido es ``F-03``."""
    _seed_committed_findings_shape()

    main_iol._seed_fid_counter()

    assert main_iol._fid_counter == 2
    assert main_iol._next_fid() == "F-03"


def test_seed_leaves_a_fresh_checkout_starting_at_f_01(tmp_path: Path) -> None:
    """Primer run: sin archivo de findings el seed es un no-op y el primer fid es ``F-01``.

    Pinnea que el fix no rompe un checkout limpio — el modo en que un seed mal
    escrito (levantar ante archivo ausente) rompería a todo consumidor nuevo.
    """
    assert not findings_path(main_iol._PKG).exists()
    assert not any(tmp_path.iterdir())

    main_iol._seed_fid_counter()

    assert main_iol._fid_counter == 0
    assert main_iol._next_fid() == "F-01"


# ---------------------------------------------------------------------------
# 2. Integridad del entregable, extremo a extremo, por un probe real
# ---------------------------------------------------------------------------


def test_seeded_run_files_new_findings_above_the_committed_ones() -> None:
    """El entregable completo: dos findings nuevos aterrizan como F-03 y F-04.

    ``append_finding`` NO está stubbeado — el real corre y escribe en ``tmp_path``,
    así que lo que se aserta es el archivo resultante y no una lista de kwargs
    interceptados.
    """
    _seed_committed_findings_shape()
    main_iol._seed_fid_counter()

    with _mock_client(_handler_500) as client:
        first, _ = main_iol.probe_get_quote_sync(client)
    with _mock_client(_handler_500) as client:
        second, _ = main_iol.probe_get_quote_sync(client)

    assert first.status == "FINDING"
    assert second.status == "FINDING"

    text = _findings_text()
    assert f"### F-03 -- {_PROBE_TITLE}" in text, text
    assert f"### F-04 -- {_PROBE_TITLE}" in text, text
    assert _OPERATOR_TITLE in text, "el bloque de detalle de F-01 (OPEN) fue reescrito"
    assert f"### F-01 -- {_OPERATOR_TITLE}" in text, text
    assert max_existing_fid(main_iol._PKG) == 4


def test_unseeded_run_clobbers_f01_and_silently_drops_the_second_finding() -> None:
    """No-vacuidad del caso anterior: sin el seed, el daño exacto que el BLOCKER describe.

    Sin este caso, el test de arriba pasaría igual contra un driver que seedeara
    por accidente (o cuyo archivo de fixture estuviera vacío). Acá el seed se
    saltea deliberadamente y se aserta el resultado destructivo:

    - ``F-01`` está OPEN, así que ``append_finding`` NO corta y **reescribe** su
      bloque: el título del operador desaparece;
    - ``F-02`` está FIXED, así que el segundo write se traga en silencio;
    - y sin embargo **ambos** probes devuelven ``FINDING``, que es lo que
      ``main()`` cuenta para el ``SUMMARY``.
    """
    _seed_committed_findings_shape()
    # Seed deliberadamente NO llamado; el contador queda en 0 (fixture).
    assert main_iol._fid_counter == 0

    with _mock_client(_handler_500) as client:
        first, _ = main_iol.probe_get_quote_sync(client)
    with _mock_client(_handler_500) as client:
        second, _ = main_iol.probe_get_quote_sync(client)

    assert first.status == "FINDING"
    assert second.status == "FINDING"

    text = _findings_text()
    assert _OPERATOR_TITLE not in text, (
        "se esperaba que el write ingenuo reescribiera F-01 (OPEN) en el lugar"
    )
    assert f"### F-01 -- {_PROBE_TITLE}" in text, text
    assert f"### F-02 -- {_PROBE_TITLE}" not in text, (
        "se esperaba que el segundo write fuera tragado por el short-circuit de status no-OPEN"
    )
    assert max_existing_fid(main_iol._PKG) == 2


# ---------------------------------------------------------------------------
# 3. Lock de wiring por AST — un seed definido pero no llamado falla acá
# ---------------------------------------------------------------------------


def _main_function_def() -> ast.FunctionDef:
    """El ``FunctionDef`` module-level de ``main`` en ``main_iol.py``."""
    tree = ast.parse(_DRIVER_PATH.read_text(encoding="utf-8"))
    defs = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"]
    assert len(defs) == 1, f"se esperaba exactamente un main() module-level, hay {len(defs)}"
    return defs[0]


def _call_linenos(scope: ast.AST, predicate: Callable[[str], bool]) -> list[int]:
    """Líneas de toda ``ast.Call`` dentro de ``scope`` cuyo nombre satisface ``predicate``."""
    linenos: list[int] = []
    for node in ast.walk(scope):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if isinstance(name, str) and predicate(name):
            linenos.append(node.lineno)
    return linenos


def test_main_calls_the_seed_between_the_bootstrap_and_the_first_probe() -> None:
    """El lock: ``_seed_fid_counter()`` existe DENTRO de ``main()`` y en el orden correcto.

    Un seed definido pero nunca llamado —la forma exacta del gap que este plan
    cierra, sólo que un paso más adelante— falla acá, igual que uno llamado antes
    del bootstrap del archivo o después del primer probe.
    """
    main_def = _main_function_def()

    seed_lines = _call_linenos(main_def, lambda n: n == "_seed_fid_counter")
    bootstrap_lines = _call_linenos(main_def, lambda n: n == "write_findings")
    probe_lines = _call_linenos(main_def, lambda n: n.startswith("probe_"))

    assert len(seed_lines) == 1, f"se esperaba exactamente un _seed_fid_counter(), hay {seed_lines}"
    assert len(bootstrap_lines) == 1, f"se esperaba un write_findings(), hay {bootstrap_lines}"
    assert probe_lines, "main() no llama a ningún probe_*; el lock de orden sería vacuo"

    assert bootstrap_lines[0] < seed_lines[0], (
        "el seed debe correr DESPUÉS del bootstrap del findings file: "
        f"write_findings@{bootstrap_lines[0]} vs _seed_fid_counter@{seed_lines[0]}"
    )
    assert seed_lines[0] < min(probe_lines), (
        "el seed debe correr ANTES del primer probe: "
        f"_seed_fid_counter@{seed_lines[0]} vs primer probe_*@{min(probe_lines)}"
    )
