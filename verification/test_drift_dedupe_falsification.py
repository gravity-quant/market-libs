"""D-04: falsificación del dedupe de schema drift — colapso Y no-colapso, juntos.

HARN-01 hace que el driver deje de escribir un bloque ``### F-`` por cada pase
sobre la MISMA divergencia de schema. El mecanismo (D-01 ENMENDADA) es una guarda
intra-proceso con clave ``(client_function, digest)``: dentro de un proceso, la
superficie sync y la superficie async comparan contra el MISMO baseline y
producen el MISMO schema, así que emitían dos bloques idénticos por la misma
divergencia (22 bloques medidos para 11 divergencias reales).

Este archivo prueba las DOS mitades del contrato, porque sólo una de ellas es una
propiedad de seguridad:

- **Qué SÍ debe colapsar** (arm ``collapse``): la misma divergencia repetida
  dentro de un proceso escribe UN solo bloque.
- **Qué NO debe colapsar** (arm ``does_not_collapse``): una divergencia distinta
  sobre el mismo endpoint no debe colapsar — un schema distinto sobre
  ``get_health`` sigue escribiendo un bloque nuevo, porque su digest es otro.

Sin el segundo arm, este archivo probaría **supresión**, no dedupe: un ``return``
incondicional en el sitio de drift pasaría el primer arm con honores mientras se
traga toda divergencia posterior. El modelo de amenaza de este proyecto es
exactamente ése — "una divergencia real que nunca llega a un humano"
(``PITFALLS.md`` Pitfall 9: *any test named 'dedupe' that only asserts the
collapse and not the non-collapse*). El arm de no-colapso es el control primario
de la fase; el de colapso es la mejora.

El tercer arm (``fid_not_burned``) cubre D-03: el no-op del dedupe se decide
ANTES de ``_next_fid()``, así que un bloque no escrito tampoco consume un fid. Si
el fid se quemara, el driver reportaría en su línea SUMMARY un censo mayor que el
que su propio artefacto contiene — la misma pérdida silenciosa que P-3
(``verification/test_finding_count_consistency.py``) pinea para el allocator sin
seedear. P-3 NO puede detectar esta variante: es un property test con su propio
allocator local y no importa ningún driver, así que el peso de D-03 lo lleva este
archivo.

Sujeto: ``main_market_data._write_schema_snapshot`` — el único de los 7 sitios de
drift de D-02 que puede duplicar dentro de un mismo proceso, y por lo tanto el
único donde estos arms de runtime tienen sujeto real (``45-RESEARCH.md``
Hallazgo 2).

Aislamiento: la fixture monkeypatchea ``verification.findings._FINDINGS_DIR`` (y
el ``_SCHEMA_DIR`` del driver) a ``tmp_path``. Ningún test toca
``.planning/verification/``: un test de dedupe que escribiera en los findings
committeados corrompería exactamente el artefacto que esta fase está limpiando.
El gate de aceptación grepea ``git status --porcelain .planning/verification/``
después de correr el archivo.

Este archivo corre desde la lista explícita del job ``lint`` en
``.github/workflows/ci.yml`` (lo enrola el plan 45-05), por la misma razón que
los otros guards de ``verification/``: el job ``test`` pasa paths explícitos que
pisan ``testpaths``, así que ``verification/`` nunca corre ahí.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import main_market_data
import pytest

import verification.findings
from verification import schema_of

_PKG = "market-data-client"
_BASE_URL = "https://market-data-develop.bbsa.com.ar/api"
_CLIENT_FUNCTION = "get_health"
_ENDPOINT = "/health"

# Un bloque de detalle por finding escrito: `### F-NN -- <título>`. Copiado de
# `verification/test_finding_count_consistency.py:52` a propósito: ambos archivos
# cuentan la MISMA unidad (bloques realmente escritos, no llamadas).
_DETAIL_HEADER_RE = re.compile(r"^### F-", re.MULTILINE)

# El baseline committeado. Los tres payloads de abajo DIFIEREN de él, si no el
# helper saldría por la rama "sin drift" (`committed.get("schema") == actual`) y
# los arms medirían otra cosa.
_BASELINE_PAYLOAD: dict[str, Any] = {"status": "ok", "uptime": 1.0}

# Divergencia #1: `uptime` pasa de float a int.
_PAYLOAD_A: dict[str, Any] = {"status": "ok", "uptime": 1}

# Divergencia #2 sobre el MISMO endpoint: forma distinta (clave nueva) ⇒ digest
# distinto. Es el sujeto del arm de no-colapso.
_PAYLOAD_B: dict[str, Any] = {"status": "ok", "uptime": 1, "build": "abc123"}


@pytest.fixture
def findings_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Findings file aislado + baseline de schema que YA difiere de los payloads.

    ``monkeypatch`` deshace cada ``setattr`` en su propio teardown, así que el
    estado de proceso del driver (``_fid_counter``, ``_seen_drift_keys``) queda
    restaurado y los tests no se contaminan entre sí.
    """
    monkeypatch.setattr(verification.findings, "_FINDINGS_DIR", tmp_path)

    schema_dir = tmp_path / "schemas" / _PKG
    schema_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(main_market_data, "_SCHEMA_DIR", schema_dir)
    # El driver arma la ruta como `_SCHEMA_DIR / f"{client_function...}.json"` en
    # tiempo de llamada, así que patchear el directorio alcanza.
    (schema_dir / f"{_CLIENT_FUNCTION.replace('_', '-')}.json").write_text(
        json.dumps(
            {
                "endpoint": _ENDPOINT,
                "client_function": _CLIENT_FUNCTION,
                "captured_at": "2026-01-01T00:00:00+00:00",
                "base_url": _BASE_URL,
                "schema": schema_of(_BASELINE_PAYLOAD),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(main_market_data, "_fid_counter", 0)
    assert hasattr(main_market_data, "_seen_drift_keys"), (
        "main_market_data no expone `_seen_drift_keys`: la guarda de dedupe "
        "intra-proceso de HARN-01 (D-01 ENMENDADA) todavía no existe en el "
        "driver. Es el artefacto que la Task 2 de 45-02 entrega; hasta entonces "
        "este archivo está RED por diseño."
    )
    # Sin `raising=False` a propósito: el día que alguien borre el set del
    # driver, el assert de arriba tiene que ponerse rojo en vez de recrearlo.
    monkeypatch.setattr(main_market_data, "_seen_drift_keys", set())

    return tmp_path / f"{_PKG}-findings.md"


def _count_blocks(path: Path) -> int:
    """Bloques ``### F-`` escritos; 0 si el archivo todavía no existe."""
    if not path.exists():
        return 0
    return len(_DETAIL_HEADER_RE.findall(path.read_text("utf-8")))


def _drift(*, raw: Any, surface: str) -> None:
    """Invoca el sitio de drift del driver con un payload que difiere del baseline."""
    main_market_data._write_schema_snapshot(
        endpoint=_ENDPOINT,
        client_function=_CLIENT_FUNCTION,
        raw=raw,
        base_url=_BASE_URL,
        surface=surface,
    )


def test_same_drift_on_both_surfaces_collapses_to_one_block(findings_file: Path) -> None:
    """Arm (a): la MISMA divergencia vista por sync y por async escribe 1 bloque.

    Es la duplicación medida (22 bloques → 11): el baseline se elige sólo por
    ``client_function``, así que ambas superficies producen el mismo
    ``actual_schema`` y por lo tanto el mismo digest.
    """
    before = _count_blocks(findings_file)

    _drift(raw=_PAYLOAD_A, surface="sync")
    _drift(raw=_PAYLOAD_A, surface="async")

    new_blocks = _count_blocks(findings_file) - before
    assert new_blocks == 1, (
        f"la misma divergencia sobre {_CLIENT_FUNCTION} escribió {new_blocks} "
        f"bloques nuevos en vez de 1: la guarda de dedupe intra-proceso no corrió. "
        f"2 bloques es el status quo que HARN-01 existe para eliminar — el ledger "
        f"reporta el doble de divergencias de las que realmente hay."
    )


def test_distinct_drift_on_same_endpoint_does_not_collapse(findings_file: Path) -> None:
    """Arm (b), FALSIFICACIÓN: dos divergencias distintas ⇒ 2 bloques.

    Sin este arm el archivo probaría supresión y no dedupe. Es el control de
    seguridad primario de la fase (T-45-05).
    """
    before = _count_blocks(findings_file)

    _drift(raw=_PAYLOAD_A, surface="sync")
    _drift(raw=_PAYLOAD_B, surface="async")

    new_blocks = _count_blocks(findings_file) - before
    assert new_blocks == 2, (
        f"dos divergencias DISTINTAS sobre {_CLIENT_FUNCTION} escribieron "
        f"{new_blocks} bloques nuevos en vez de 2. 1 bloque significa que el "
        f"mecanismo se tragó una divergencia real: eso es pérdida de censo, no "
        f"dedupe. La clave tiene que incluir el digest del contenido "
        f"(D-01 ENMENDADA), no sólo el nombre de la función."
    )


def test_dedupe_no_op_leaves_the_fid_not_burned(findings_file: Path) -> None:
    """Arm (c), D-03: el no-op del dedupe no consume un fid.

    La fixture deja ``_fid_counter`` en 0; las dos llamadas del arm (a) tienen
    que dejarlo en 1, no en 2.
    """
    assert main_market_data._fid_counter == 0, (
        "la fixture no reseteó `_fid_counter`; el arm mediría un delta sobre un "
        "estado heredado de otro test."
    )

    _drift(raw=_PAYLOAD_A, surface="sync")
    _drift(raw=_PAYLOAD_A, surface="async")

    assert main_market_data._fid_counter == 1, (
        f"`_fid_counter` quedó en {main_market_data._fid_counter} tras un solo "
        f"bloque escrito: el no-op del dedupe quemó un fid. D-03 exige que "
        f"`_next_fid()` se llame DESPUÉS de la decisión de dedupe — si no, el "
        f"driver reporta en su SUMMARY un censo mayor que el que escribió, que es "
        f"exactamente la pérdida silenciosa que P-3 pinea para el allocator sin "
        f"seedear."
    )
