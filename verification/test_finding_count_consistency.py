"""P-3: la cantidad de fids emitidos tiene que igualar la de bloques ``### F-`` nuevos.

El modo de falla que este archivo pinea es silencioso y se lee como éxito.
``append_finding`` preserva todo finding cuyo status ya fue promovido fuera de
``OPEN`` (``CONFIRMED``/``FIXED``/``EXPECTED``/``NO-FIX``): re-llamarlo con ese
mismo fid refresca el ART block y **retorna sin escribir nada**. Es el
comportamiento correcto — protege la prosa de triage humana — pero convierte un
allocator de fids sin seedear en una pérdida de censo sin rastro: el driver
arranca en ``F-01``, choca contra los fids terminales que ya viven en el archivo,
cada choque es un no-op, y sin embargo el driver sigue contando esas llamadas y
reporta ``FINDING=N`` como si las hubiera escrito. El run pierde su entregable
creyendo que tuvo éxito.

Por eso ``max_existing_fid`` existe y por eso los cinco drivers llaman a
``_seed_fid_counter()`` antes del primer probe. Este archivo prueba que la
propiedad se sostiene, y —lo que importa más— prueba que la aserción **detecta**
su violación:

- ``test_emitted_fid_count_matches_new_finding_blocks`` es el arm seedeado: N fids
  emitidos, N bloques nuevos.
- ``test_unseeded_allocator_silently_loses_findings`` es el control fail-first:
  con el MISMO archivo y el MISMO N, un allocator sin seedear produce **menos**
  bloques que fids. Sin este control, el arm seedeado pasaría igual sobre un
  findings file vacío y no probaría nada: no habría fid terminal contra el cual
  chocar, así que la ausencia de choques no sería evidencia de que el seed
  funciona.

Aislamiento: ambos tests monkeypatchean ``verification.findings._FINDINGS_DIR`` a
``tmp_path``. Ningún test toca los archivos committeados de
``.planning/verification/`` — el gate de aceptación de 33-05 grepea
``git status --porcelain .planning/verification/`` después de correrlos.

``_write_or_check_schema`` de los drivers también llama a ``_next_fid()`` cuando
detecta drift de snapshot, así que comparte exactamente este hazard y queda
cubierto por la misma propiedad.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest

import verification.findings
from verification.findings import append_finding, max_existing_fid

_PKG = "higyrus-client"

# Un bloque de detalle por finding escrito: `### F-NN -- <título>`.
_DETAIL_HEADER_RE = re.compile(r"^### F-", re.MULTILINE)

# Cuántos fids emite cada arm. Cualquier N >= 2 sirve; 4 deja margen para que la
# diferencia del arm sin seedear sea visible y no un off-by-one ambiguo.
_EMISSIONS = 4


@pytest.fixture
def seeded_findings_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Findings file con un ``F-01`` NO-``OPEN`` — el fid contra el que se choca.

    ``EXPECTED`` es terminal, así que ``append_finding`` va a preservarlo y
    descartar en silencio cualquier re-emisión de ``F-01``. Es la condición
    exacta que los cinco drivers tienen en producción: sus findings files ya
    cargan fids triageados de ciclos anteriores.

    ``monkeypatch`` deshace el ``setattr`` en su propio teardown, así que el
    fixture no necesita uno propio (de ahí el ``return`` y no un ``yield``).
    """
    monkeypatch.setattr(verification.findings, "_FINDINGS_DIR", tmp_path)
    append_finding(
        _PKG,
        fid="F-01",
        class_="SHAPE",
        surface="sync",
        status="EXPECTED",
        title="finding terminal preexistente",
        expected="-",
        actual="-",
        diff="-",
    )
    return tmp_path / f"{_PKG}-findings.md"


def _emit(allocator: Callable[[], str], n: int) -> int:
    """Emite ``n`` findings distintos usando ``allocator`` y devuelve ``n``.

    Cada título es único, así que ningún descarte puede atribuirse al dedupe por
    título: el único mecanismo capaz de tragarse una escritura acá es el
    short-circuit por status no-``OPEN``.
    """
    for i in range(n):
        append_finding(
            _PKG,
            fid=allocator(),
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title=f"Modelo.campo_{i}: missing (declared=str, observed=NoneType) [sync]",
            expected="str",
            actual="NoneType",
            diff=f"endpoint=/api/probe/{i}",
        )
    return n


def _make_allocator(start: int) -> Callable[[], str]:
    """Allocator de fids equivalente al ``_next_fid()`` de los drivers."""
    counter = {"n": start}

    def _next_fid() -> str:
        counter["n"] += 1
        return f"F-{counter['n']:02d}"

    return _next_fid


def test_emitted_fid_count_matches_new_finding_blocks(seeded_findings_file: Path) -> None:
    """Con el allocator seedeado, N fids emitidos producen N bloques nuevos.

    Es la propiedad que 33-05 asevera por paquete después de cada corrida en vivo:
    si los dos números no coinciden, el censo reportado es más grande que el
    censo escrito y la diferencia se perdió sin error.
    """
    blocks_before = len(_DETAIL_HEADER_RE.findall(seeded_findings_file.read_text("utf-8")))

    seed = max_existing_fid(_PKG)
    assert seed == 1, (
        f"max_existing_fid devolvió {seed}; el fixture escribió F-01, así que el "
        f"seed tiene que ser 1. Un 0 acá significaría que el scan no ve el bloque y "
        f"el resto del test mediría otra cosa."
    )

    emitted = _emit(_make_allocator(seed), _EMISSIONS)

    blocks_after = len(_DETAIL_HEADER_RE.findall(seeded_findings_file.read_text("utf-8")))
    new_blocks = blocks_after - blocks_before

    assert new_blocks == emitted, (
        f"se emitieron {emitted} fids y se escribieron {new_blocks} bloques nuevos. "
        f"La diferencia son findings que el driver contó en su línea SUMMARY y que "
        f"append_finding descartó por el short-circuit de status no-OPEN: el run "
        f"reporta un censo que su propio artefacto no contiene (P-3)."
    )


def test_unseeded_allocator_silently_loses_findings(seeded_findings_file: Path) -> None:
    """Control fail-first: sin seedear, se escriben MENOS bloques que fids emitidos.

    Este test es lo que hace no-vacuo al anterior. Prueba dos cosas a la vez: que
    la pérdida es real y medible, y que es **silenciosa** — ``append_finding`` no
    levanta, no devuelve un booleano y no deja rastro del descarte, así que el
    único signal disponible es justamente la comparación de conteos.
    """
    blocks_before = len(_DETAIL_HEADER_RE.findall(seeded_findings_file.read_text("utf-8")))

    # start=0 -> el primer fid es F-01, que ya existe como EXPECTED (terminal).
    emitted = _emit(_make_allocator(0), _EMISSIONS)

    blocks_after = len(_DETAIL_HEADER_RE.findall(seeded_findings_file.read_text("utf-8")))
    new_blocks = blocks_after - blocks_before

    assert new_blocks < emitted, (
        f"el allocator SIN seedear escribió {new_blocks} bloques sobre {emitted} fids "
        f"emitidos, es decir no perdió ninguno. Si esto pasa, el fixture dejó de "
        f"colocar un fid terminal en el camino del allocator y el arm seedeado "
        f"quedó probando una tautología."
    )
    assert new_blocks == emitted - 1, (
        f"se esperaba exactamente una pérdida (la colisión con F-01) y hubo "
        f"{emitted - new_blocks}. Un número distinto significa que el mecanismo de "
        f"descarte no es el que este test cree estar midiendo."
    )
