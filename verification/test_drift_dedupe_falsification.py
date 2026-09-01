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

Sujeto de los arms de runtime: ``main_market_data._write_schema_snapshot`` y
``main_higyrus._write_or_check_schema``.

**Por qué este archivo además lleva locks por AST (arms 4 y 5, plan 45-03).**
Los arms de runtime cubren 2 de los 7 sitios de drift de D-02. Los otros 5 no
tienen un sujeto de runtime barato (viven detrás de probes con clientes en vivo),
y el invariante que más fácil se rompe en ellos —el ORDEN de la guarda respecto
de ``_next_fid()`` (D-03) y la FORMA del no-op— es puramente estructural. El
guardián natural, ``verification/test_finding_count_consistency.py`` (P-3), NO
sirve para eso: es un property test con un allocator local que **no importa ni
parsea ningún driver**, así que es verde con el orden viejo y verde con el orden
nuevo, incapaz de distinguirlos (``45-RESEARCH.md`` Pitfall B). El peso de D-03
lo lleva este archivo, sobre los 5 drivers, por AST.

**Y por qué la forma del no-op necesita su propio lock.** Los 7 sitios NO son
homogéneos en contrato de retorno: uno devuelve ``None`` (``return`` desnudo),
tres devuelven ``tuple[str, str]``, uno devuelve ``ProbeResult`` y dos son ramas
inline de un bucle que acumula ``finding_fids`` (no-op = ``continue`` sin
``append``). Un fix copy-paste rompe al menos tres: un ``return`` desnudo en un
helper anotado ``-> tuple[str, str]`` devuelve ``None`` y su caller hace
``status, detail = ...`` — un ``TypeError`` que voltea el run entero (T-45-12).
El arm 5 es lo que impide que el próximo editor los uniforme.

Aislamiento: las fixtures monkeypatchean ``verification.findings._FINDINGS_DIR``
(y el ``_SCHEMA_DIR``/``_SCHEMA_FILES`` del driver) a ``tmp_path``. Ningún test
toca ``.planning/verification/``: un test de dedupe que escribiera en los
findings committeados corrompería exactamente el artefacto que esta fase está
limpiando. El gate de aceptación grepea
``git status --porcelain .planning/verification/`` después de correr el archivo.

Este archivo corre desde la lista explícita del job ``lint`` en
``.github/workflows/ci.yml`` (lo enrola el plan 45-05), por la misma razón que
los otros guards de ``verification/``: el job ``test`` pasa paths explícitos que
pisan ``testpaths``, así que ``verification/`` nunca corre ahí.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from types import ModuleType
from typing import Any

import main_ambito_financiero
import main_higyrus
import main_iol
import main_market_data
import main_matriz
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


# ---------------------------------------------------------------------------
# Arms 4 y 5 — locks por AST sobre los 7 sitios de drift de D-02 (plan 45-03)
# ---------------------------------------------------------------------------

# Tabla declarativa: qué esperamos encontrar en cada driver.
#
# La cuenta de sitios es un piso Y un techo: si algún día alguien agrega un sitio
# de drift SIN guarda, el assert de reparto se pone rojo y lo destapa antes de que
# vuelva a inflar el ledger. Si alguien borra una guarda, también.
#
# Las formas de no-op se declaran como MULTICONJUNTO (lista ordenada al comparar),
# a propósito: el orden dentro del archivo no es parte del contrato, la
# composición sí. `main_iol` es el único con más de una forma porque sus 3 sitios
# viven en dos funciones con contratos de retorno distintos.
_BARE_RETURN = "return-desnudo"
_TUPLE_PASS = 'return-tupla-("PASS", …)'
_PROBE_RESULT_PASS = 'return-ProbeResult(…, "PASS", …)'
_CONTINUE = "continue"

_EXPECTED_SITES: dict[str, tuple[int, list[str]]] = {
    # driver: (cantidad de sitios de drift, formas de no-op esperadas)
    "main_market_data": (1, [_BARE_RETURN]),
    "main_iol": (3, [_CONTINUE, _CONTINUE, _TUPLE_PASS]),
    "main_higyrus": (1, [_TUPLE_PASS]),
    "main_matriz": (1, [_TUPLE_PASS]),
    "main_ambito_financiero": (1, [_PROBE_RESULT_PASS]),
}

_DRIVERS: dict[str, ModuleType] = {
    "main_market_data": main_market_data,
    "main_iol": main_iol,
    "main_higyrus": main_higyrus,
    "main_matriz": main_matriz,
    "main_ambito_financiero": main_ambito_financiero,
}

# Total esperado sobre los 5 drivers. D-02 nombra 7 sitios; ni uno más ni uno menos.
_TOTAL_DRIFT_SITES = 7


def _title_literal(call: ast.Call) -> str | None:
    """Partes literales del kwarg ``title`` de un ``append_finding``.

    Devuelve ``None`` si la llamada no lleva ``title``. Para un f-string
    concatena sólo sus tramos constantes (``f"type drift on \\`{key}\\`"`` →
    ``"type drift on `` in ..."``), que es todo lo que hace falta para clasificar.
    """
    for keyword in call.keywords:
        if keyword.arg != "title":
            continue
        value = keyword.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return value.value
        if isinstance(value, ast.JoinedStr):
            return "".join(
                part.value
                for part in value.values
                if isinstance(part, ast.Constant) and isinstance(part.value, str)
            )
    return None


def _is_drift_title(title: str) -> bool:
    """¿El título corresponde a uno de los 7 sitios de D-02?

    Normalizar a minúsculas es necesario, no cosmético: ``main_market_data``
    escribe ``"schema drift en …"`` con ``s`` minúscula y los otros cuatro
    ``"Schema drift en …"`` con mayúscula. Sin el ``lower()`` el censo daría 3 y
    los 4 drivers restantes quedarían fuera del lock sin que nada se pusiera rojo.
    """
    low = title.lower()
    return "schema drift en" in low or "type drift on" in low


def _calls_named(node: ast.AST, name: str) -> list[ast.Call]:
    """Todas las llamadas a ``name`` dentro de ``node``."""
    return [
        sub
        for sub in ast.walk(node)
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == name
    ]


def _drift_sites(tree: ast.AST) -> list[ast.Call]:
    """Los ``append_finding`` de drift del árbol, ordenados por línea."""
    sites = [
        call
        for call in _calls_named(tree, "append_finding")
        if (title := _title_literal(call)) is not None and _is_drift_title(title)
    ]
    return sorted(sites, key=lambda call: call.lineno)


def _dedupe_guards(tree: ast.AST) -> list[ast.If]:
    """Los ``if <local> in _seen_drift_keys:`` del árbol, ordenados por línea.

    Se exige que el ``if`` tenga por test un ``ast.Compare`` con ``In`` cuyo
    comparador sea el ``Name`` ``_seen_drift_keys``. El lado izquierdo tiene que
    ser un local ligado y NO un literal: ``test_main_matriz_skip_line_shape.py``
    (enrolado en CI) marca como ofensa cualquier ``In`` con un literal string a la
    izquierda, y no conviene tener dos convenciones para la misma forma.
    """
    guards = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and len(node.test.ops) == 1
        and isinstance(node.test.ops[0], ast.In)
        and any(
            isinstance(cmp_, ast.Name) and cmp_.id == "_seen_drift_keys"
            for cmp_ in node.test.comparators
        )
    ]
    return sorted(guards, key=lambda node: node.lineno)


def _no_op_shape(guard: ast.If) -> str:
    """Clasifica el cuerpo del no-op de una guarda en una de las 4 formas."""
    last = guard.body[-1]
    if isinstance(last, ast.Continue):
        return _CONTINUE
    if isinstance(last, ast.Return):
        if last.value is None:
            return _BARE_RETURN
        if (
            isinstance(last.value, ast.Tuple)
            and last.value.elts
            and isinstance(last.value.elts[0], ast.Constant)
            and last.value.elts[0].value == "PASS"
        ):
            return _TUPLE_PASS
        if (
            isinstance(last.value, ast.Call)
            and isinstance(last.value.func, ast.Name)
            and last.value.func.id == "ProbeResult"
            and len(last.value.args) >= 2
            and isinstance(last.value.args[1], ast.Constant)
            and last.value.args[1].value == "PASS"
        ):
            return _PROBE_RESULT_PASS
    return f"desconocida ({ast.dump(last)[:80]}…)"


def _tree(module: ModuleType) -> ast.AST:
    assert module.__file__ is not None
    return ast.parse(Path(module.__file__).read_text(encoding="utf-8"))


def test_the_seven_drift_sites_decide_dedupe_before_burning_a_fid() -> None:
    """Arm 4 (AST, D-03): los 7 sitios consultan la guarda ANTES de ``_next_fid()``.

    Para cada sitio se toma el ``_next_fid()`` de mayor línea estrictamente menor
    que la del ``append_finding`` —ése es el fid que ese sitio quema— y se exige
    que la guarda que le corresponde esté por encima. El emparejamiento es una
    biyección ordenada por línea dentro de cada archivo: sin ella, en
    ``main_iol`` (3 sitios en el mismo módulo) la guarda de un sitio "cubriría" a
    otro por el mero hecho de ser anterior en el archivo.
    """
    census: dict[str, int] = {}
    violations: list[str] = []

    for name, module in _DRIVERS.items():
        tree = _tree(module)
        sites = _drift_sites(tree)
        guards = _dedupe_guards(tree)
        census[name] = len(sites)

        expected_count, _ = _EXPECTED_SITES[name]
        if len(sites) != expected_count:
            violations.append(
                f"{name}.py: {len(sites)} sitios de drift, se esperaban {expected_count}. "
                "Un sitio de drift NUEVO sin guarda vuelve a inflar el ledger (HARN-01); "
                "un sitio de menos significa que alguien lo borró sin actualizar la tabla."
            )
            continue
        if len(guards) != len(sites):
            violations.append(
                f"{name}.py: {len(guards)} guardas `in _seen_drift_keys` para "
                f"{len(sites)} sitios de drift. Sin la igualdad, la guarda de un sitio "
                "'cubre' a otro por ser simplemente anterior en el archivo y un sitio "
                "queda de hecho sin dedupe."
            )
            continue

        all_fids = sorted(call.lineno for call in _calls_named(tree, "_next_fid"))
        for guard, site in zip(guards, sites, strict=True):
            preceding = [lineno for lineno in all_fids if lineno < site.lineno]
            if not preceding:
                violations.append(
                    f"{name}.py:{site.lineno}: el sitio de drift no tiene ningún "
                    "`_next_fid()` por encima; el emparejamiento guarda↔fid no aplica."
                )
                continue
            fid_lineno = preceding[-1]
            if not guard.lineno < fid_lineno < site.lineno:
                violations.append(
                    f"{name}.py: guarda en línea {guard.lineno}, `_next_fid()` en "
                    f"{fid_lineno}, `append_finding` en {site.lineno} — el orden exigido "
                    "es guarda < fid < finding. Con el fid arriba de la guarda, el no-op "
                    "quema un número y el driver reporta un censo mayor que el que "
                    "escribió (D-03)."
                )

    assert sum(census.values()) == _TOTAL_DRIFT_SITES, (
        f"censo de sitios de drift = {census} (total {sum(census.values())}), "
        f"D-02 nombra {_TOTAL_DRIFT_SITES}. Un sitio nuevo sin guarda vuelve a inflar "
        "el ledger: agregarlo a `_EXPECTED_SITES` es deliberado, no automático."
    )
    assert violations == [], "\n".join(violations)


def test_each_dedupe_no_op_matches_its_own_return_contract() -> None:
    """Arm 5 (AST, T-45-12): el no-op de cada guarda respeta SU contrato de retorno.

    Los 7 sitios no son homogéneos y un fix copy-paste rompe al menos tres. El
    hazard concreto: un ``return`` desnudo dentro de un helper anotado
    ``-> tuple[str, str]`` devuelve ``None``, y su caller hace
    ``status, detail = _write_or_check_schema(...)`` — un ``TypeError`` que
    voltea la corrida entera en vez de dedupear un bloque.

    Además exige que el cuerpo del no-op no llame a ``_next_fid`` ni a
    ``append_finding``: un no-op que emite algo no es un no-op.
    """
    violations: list[str] = []

    for name, module in _DRIVERS.items():
        tree = _tree(module)
        guards = _dedupe_guards(tree)
        _, expected_shapes = _EXPECTED_SITES[name]

        observed_shapes = sorted(_no_op_shape(guard) for guard in guards)
        if observed_shapes != sorted(expected_shapes):
            violations.append(
                f"{name}.py: formas de no-op {observed_shapes}, se esperaban "
                f"{sorted(expected_shapes)}. Un `return` desnudo en un helper que "
                "declara `tuple[str, str]` devuelve `None` y su caller desempaqueta "
                "una tupla; un `return` desnudo donde el caller espera un "
                "`ProbeResult` es el mismo hazard. Uniformar los 7 no-ops rompe al "
                "menos tres sitios (T-45-12)."
            )

        for guard in guards:
            for emitter in ("_next_fid", "append_finding"):
                emitting = [
                    call.lineno for stmt in guard.body for call in _calls_named(stmt, emitter)
                ]
                if emitting:
                    violations.append(
                        f"{name}.py: el cuerpo del no-op de la guarda en línea "
                        f"{guard.lineno} llama a `{emitter}` (línea(s) {emitting}). "
                        "Un no-op que emite algo no es un no-op: consume un fid o "
                        "escribe el bloque que la guarda decidió no escribir."
                    )

    assert violations == [], "\n".join(violations)


# ---------------------------------------------------------------------------
# Arm 6 — contrato de tupla en runtime (main_higyrus, plan 45-03)
# ---------------------------------------------------------------------------

_HIGYRUS_PKG = "higyrus-client"
_HIGYRUS_BASE_URL = "https://example.invalid"
_HIGYRUS_ENDPOINT = "/api/v1/health"


@pytest.fixture
def higyrus_findings_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
    """Findings + baseline aislados para ``main_higyrus._write_or_check_schema``.

    ``_SCHEMA_FILES`` se construye en tiempo de import con rutas ABSOLUTAS bajo
    ``.planning/verification/schemas/``, así que patchear sólo ``_SCHEMA_DIR`` no
    alcanza: hay que reemplazar también el dict, o el helper escribiría sobre el
    baseline committeado.
    """
    monkeypatch.setattr(verification.findings, "_FINDINGS_DIR", tmp_path)

    schema_dir = tmp_path / "schemas" / _HIGYRUS_PKG
    schema_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(main_higyrus, "_SCHEMA_DIR", schema_dir)

    func = next(iter(main_higyrus._SCHEMA_FILES))
    schema_file = schema_dir / f"{func.replace('_', '-')}.json"
    schema_file.write_text(
        json.dumps(
            {
                "endpoint": _HIGYRUS_ENDPOINT,
                "client_function": func,
                "captured_at": "2026-01-01T00:00:00+00:00",
                "base_url": _HIGYRUS_BASE_URL,
                "sample_params": {},
                "schema": schema_of(_BASELINE_PAYLOAD),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(main_higyrus, "_SCHEMA_FILES", {func: schema_file})

    monkeypatch.setattr(main_higyrus, "_fid_counter", 0)
    assert hasattr(main_higyrus, "_seen_drift_keys"), (
        "main_higyrus no expone `_seen_drift_keys`: la guarda de dedupe de HARN-01 "
        "todavía no existe en este driver (Task 2 del plan 45-03)."
    )
    monkeypatch.setattr(main_higyrus, "_seen_drift_keys", set())

    return tmp_path / f"{_HIGYRUS_PKG}-findings.md", func


def test_higyrus_dedupe_no_op_returns_a_tuple_the_caller_can_unpack(
    higyrus_findings_file: tuple[Path, str],
) -> None:
    """Arm 6 (runtime): el no-op de higyrus devuelve una tupla, no ``None``.

    Es el sitio con contrato ``tuple[str, str]``, el que un fix copy-paste del
    ``return`` desnudo de ``main_market_data`` habría roto. El caller hace
    ``status, detail = ...`` y después ``elif detail.startswith("escrito")``, así
    que el detalle del no-op tampoco puede empezar con ``escrito``: lo contaría
    como baseline recién escrito y el probe reportaría un ``written=[...]`` falso.
    """
    findings_path, func = higyrus_findings_file
    before = _count_blocks(findings_path)

    first = main_higyrus._write_or_check_schema(
        func, _HIGYRUS_ENDPOINT, {}, _PAYLOAD_A, _HIGYRUS_BASE_URL
    )
    second = main_higyrus._write_or_check_schema(
        func, _HIGYRUS_ENDPOINT, {}, _PAYLOAD_A, _HIGYRUS_BASE_URL
    )

    status_1, detail_1 = first
    status_2, detail_2 = second

    assert status_1 == "FINDING", (
        f"la primera pasada devolvió {first!r}: el payload de test no produjo drift "
        f"contra el baseline de la fixture, así que el arm no tiene sujeto."
    )
    assert "|" in detail_1, (
        f"el detalle FINDING {detail_1!r} no lleva la barra: el caller hace "
        f"`fid, fname = detail.split('|', 1)` y reventaría con un ValueError."
    )
    assert status_2 == "PASS", (
        f"la segunda pasada de la MISMA divergencia devolvió {second!r}: la guarda "
        f"de dedupe no corrió y el ledger vuelve a llevar dos bloques por una."
    )
    assert not detail_2.startswith("escrito"), (
        f"el detalle del no-op es {detail_2!r} y empieza con 'escrito': el caller "
        f"lo clasificaría como baseline recién escrito (`elif "
        f"detail.startswith('escrito')`) y el probe reportaría un `written=[...]` "
        f"que nunca ocurrió."
    )

    new_blocks = _count_blocks(findings_path) - before
    assert new_blocks == 1, (
        f"la misma divergencia sobre {func} escribió {new_blocks} bloques nuevos en "
        f"vez de 1: la guarda de dedupe de main_higyrus no corrió."
    )
    assert main_higyrus._fid_counter == 1, (
        f"`_fid_counter` quedó en {main_higyrus._fid_counter} tras un solo bloque "
        f"escrito: el no-op quemó un fid. D-03 exige la guarda ARRIBA de "
        f"`_next_fid()`."
    )
