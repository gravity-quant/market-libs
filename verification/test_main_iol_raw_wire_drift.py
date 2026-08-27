"""CR-01 — lock de regresión: los probes de drift de ``main_iol.py`` leen el wire crudo.

Cierra el gap registrado como **truth 6** de ``30-VERIFICATION.md`` ("los probes
que comparan formas siguen siendo no-vacuos... y por lo tanto siguen
discriminando"). Antes de este fix ``probe_schema_snapshot`` y
``probe_field_type_map`` recibían ``_as_wire(modelo)`` — una proyección del
modelo vía ``dataclasses.asdict``. Para cuando el modelo existe, el walker de la
Phase 29 ya coercionó cada campo no-opcional a su tipo declarado y descartó cada
clave del wire que ningún campo declara, así que ``schema_of(_as_wire(modelo))``
es una función constante de la **declaración** del modelo, no del wire.

Falsificación que este archivo codifica, verificada empíricamente dos veces
(code review + verificación de fase) contra el baseline committeado real
``.planning/verification/schemas/iol-client/get-quote.json``:

- ``ultimoPrecio`` float→str  — detectada sobre el wire crudo, invisible por proyección.
- clave ``simbolo`` agregada  — detectada sobre el wire crudo, invisible por proyección.
- clave ``montoOperado`` quitada — detectada sobre el wire crudo, invisible por proyección.

Los siete tests son **offline**: sin red, sin credenciales, sin ``httpx_mock``.
Ejercitan los probes directamente contra un ``raw_wire`` sintético y un
directorio de schemas temporal sembrado desde el baseline committeado real. El
cuerpo sintético limpio se **deriva** del bloque ``schema`` del baseline (no se
transcribe), de modo que el test sigue al baseline en vez de derivar de él.

Nota sobre el gate: ``verification/`` está en ``testpaths`` (``pyproject.toml``
raíz), así que ``uv run pytest verification -q`` colecta este archivo
localmente, pero el job ``test`` del CI corre **por paquete** y no lo colecta.
Es una propiedad pre-existente de todos los ``verification/test_main_*.py`` y no
es de este plan cambiarla: el gate es local / suite completa, no CI.

Sección 8 — CR-01 (mitad post-cierre): un cuerpo capturado como ``null`` es un
insumo que **sí llegó**, no una captura que falló. ``_capture_raw_wire`` declara
y honra el contrato de dejar **ausente** del dict al endpoint cuya captura
levantó; los consumidores descartaban esa distinción preguntando por el valor en
vez de preguntarle al dict si tiene la clave. Estos casos la fijan en ambas
direcciones: la pertenencia de la clave es a la vez lo que gatea cada chequeo y
lo que construye el detalle del PASS, de modo que un endpoint nombrado como
chequeado es siempre uno cuyo cuerpo se inspeccionó de verdad, y una captura
genuinamente ausente sigue ruteando a skip en vez de a finding.

Sección 9 — CR-01 (BLOCKER, 30-VERIFICATION.md 2026-08-21 + 30-REVIEW.md
CR-01): un finding es un artefacto durable, versionado en git. La excepción que
llega al handler de captura de ``_capture_raw_wire`` lleva el body de error
upstream adentro de su propio mensaje, porque ``_core.raise_for_response`` lo
pone ahí para beneficio del consumidor — no para el reporte. El driver debe
reportar, por lo tanto, sólo la clase de la excepción y su status code, y
detenerse ahí.
"""

from __future__ import annotations

import ast
import datetime as dt
import json
import re
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import main_iol
import pytest

from iol_client import Client, Cotizacion
from verification import findings as findings_module
from verification.schema import schema_of

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BASELINE_PATH = (
    _REPO_ROOT / ".planning" / "verification" / "schemas" / "iol-client" / "get-quote.json"
)
_BASELINE_DIR = _BASELINE_PATH.parent
_BASE_URL = "https://api.test"
_TODAY = dt.date(2026, 6, 8)

# Los cuatro baselines committeados, por nombre de función del driver. Sembrar
# los cuatro es load-bearing para la sección 8 (ver ``tmp_schema_all``).
_SCHEMA_BASELINE_NAMES: dict[str, str] = {
    "get_quote": "get-quote.json",
    "get_historical_quotes": "get-historical-quotes.json",
    "get_instruments": "get-instruments.json",
    "get_instruments_by_type": "get-instruments-by-type.json",
}

# Los tres endpoints que ``probe_field_type_map`` field-mapea. ``get_instruments``
# no está: el probe 12 no lo examina en ninguna línea (no tiene ``_ASSUMED_*``);
# su cobertura de drift la aporta el baseline del probe 13.
_FIELD_MAPPED_ENDPOINTS = (
    "get_quote",
    "get_historical_quotes",
    "get_instruments_by_type",
)

# Valor representativo por nombre de tipo declarado en el baseline. Deliberadamente
# NO tiene default: un nombre de tipo desconocido levanta ``KeyError`` en vez de
# degradar silenciosamente el fixture (que es exactamente el modo de falla que
# este archivo existe para prohibir).
_TYPE_SAMPLES: dict[str, Any] = {
    "float": 1.0,
    "int": 1,
    "str": "x",
    "bool": True,
    "NoneType": None,
}

# Las tres clases de drift de la tabla CR-01 (30-REVIEW.md).
_DRIFT_LABELS = (
    "type_drift_ultimoPrecio",
    "added_key_simbolo",
    "removed_key_montoOperado",
)

# Sección 9 (CR-01, BLOCKER) — token que no puede aparecer por accidente en
# ningún texto de finding, así que su presencia es prueba inequívoca de que un
# body cruzó la frontera hacia el reporte durable.
_WIRE_BODY_MARKER = "ZZ-MARCADOR-DE-CUERPO-DE-WIRE-ZZ"


# ---------------------------------------------------------------------------
# Fixture material — derivado del baseline committeado, nunca transcripto
# ---------------------------------------------------------------------------


def _baseline_schema() -> dict[str, Any]:
    """Bloque ``schema`` del baseline committeado real de ``get_quote``."""
    envelope = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
    schema: dict[str, Any] = envelope["schema"]
    return schema


def _value_for(declared: Any) -> Any:
    """Mapea una declaración de ``schema_of`` a un valor representativo."""
    if isinstance(declared, list):
        return [_value_for(declared[0])] if declared else []
    if isinstance(declared, dict):
        return {k: _value_for(v) for k, v in declared.items()}
    return _TYPE_SAMPLES[declared]


def _clean_body() -> dict[str, Any]:
    """Cuerpo crudo sintético cuyo ``schema_of`` reproduce el baseline exacto."""
    return {k: _value_for(v) for k, v in _baseline_schema().items()}


def _mutated(label: str) -> dict[str, Any]:
    """Aplica una de las tres mutaciones CR-01 sobre el cuerpo limpio."""
    body = _clean_body()
    if label == "type_drift_ultimoPrecio":
        body["ultimoPrecio"] = "1234,50"
    elif label == "added_key_simbolo":
        body["simbolo"] = "GGAL"
    elif label == "removed_key_montoOperado":
        del body["montoOperado"]
    else:  # pragma: no cover - guardia de fixture
        raise AssertionError(f"unknown mutation label {label!r}")
    return body


def _null_wire() -> dict[str, Any]:
    """Los cuatro endpoints capturados, cada uno con cuerpo JSON nulo.

    Deliberadamente NO es una etiqueta más de ``_DRIFT_LABELS`` ni una rama de
    ``_mutated``: aquél helper aplica una mutación **sobre un dict** y está
    anotado como tal. Un cuerpo nulo no es la mutación de un dict, es el
    reemplazo del cuerpo entero, y plegarlo ahí arrastraría el caso al canario de
    la sección 7, cuyo sujeto son las tres mutaciones ciegas a la proyección.
    """
    wire: dict[str, Any] = {name: None for name in _SCHEMA_BASELINE_NAMES}
    return wire


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Aísla el findings dir y resetea el state module-level del driver."""
    monkeypatch.setattr(findings_module, "_FINDINGS_DIR", tmp_path)
    monkeypatch.setattr(main_iol, "_auth_failed", False)
    monkeypatch.setattr(main_iol, "_auth_failure_reason", "")
    monkeypatch.setattr(main_iol, "_fid_counter", 0)


@pytest.fixture
def client() -> Iterator[Client]:
    """Un ``Client`` construido con credenciales dummy — nunca toca ``.env``.

    Se construye explícito en vez de mutar el singleton vía
    ``iol_client.configure(...)``: los probes bajo test reciben la instancia
    threadeada, así que la configuración global no aporta nada y su mutación
    filtraría ``base_url`` a otros tests de la misma sesión.
    """
    instance = Client(base_url=_BASE_URL, username="u", password="p")
    yield instance
    instance.close()


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Intercepta ``append_finding`` y devuelve la lista de llamadas."""
    calls: list[dict[str, Any]] = []

    def _spy(pkg: str, **kwargs: Any) -> Path:
        calls.append({"pkg": pkg, **kwargs})
        return Path("unused")

    monkeypatch.setattr(main_iol, "append_finding", _spy)
    return calls


@pytest.fixture
def tmp_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Copia el baseline committeado a ``tmp_path`` y apunta el driver ahí.

    Ningún artefacto committeado se escribe durante estos tests; la copia es la
    que se compara byte a byte contra el fuente para probar D-25.
    """
    dest_dir = tmp_path / "schemas"
    dest_dir.mkdir()
    target = dest_dir / _BASELINE_PATH.name
    target.write_bytes(_BASELINE_PATH.read_bytes())
    monkeypatch.setattr(main_iol, "_SCHEMA_DIR", dest_dir)
    monkeypatch.setattr(main_iol, "_SCHEMA_FILES", {"get_quote": target})
    return target


@pytest.fixture
def tmp_schema_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Copia los CUATRO baselines committeados a ``tmp_path`` y apunta el driver ahí.

    Sembrar los cuatro es load-bearing, no prolijidad. ``_write_or_check_schema``
    toma su rama de **escritura** cuando el archivo de baseline no existe:
    registra la forma observada como nueva verdad de referencia y devuelve PASS.
    Con un baseline faltante, un caso de cuerpo nulo pasaría por la razón
    equivocada y además dejaría escrito en tmp un baseline envenenado
    (``"schema": "NoneType"``) — el riesgo T-30-07-03, contenido acá.

    Devuelve el mapeo ``func_name -> copia`` para que los tests puedan asertar
    que las copias quedaron byte-idénticas (D-25: el drift jamás sobreescribe).
    """
    dest_dir = tmp_path / "schemas-all"
    dest_dir.mkdir()
    mapping: dict[str, Path] = {}
    for func_name, file_name in _SCHEMA_BASELINE_NAMES.items():
        target = dest_dir / file_name
        target.write_bytes((_BASELINE_DIR / file_name).read_bytes())
        mapping[func_name] = target
    monkeypatch.setattr(main_iol, "_SCHEMA_DIR", dest_dir)
    monkeypatch.setattr(main_iol, "_SCHEMA_FILES", mapping)
    return mapping


# ---------------------------------------------------------------------------
# 1. Pass-through — el lock de reversión
# ---------------------------------------------------------------------------


def test_probe_schema_snapshot_passes_raw_wire_through_unmodified(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El payload que llega a ``_write_or_check_schema`` es el wire crudo, intacto.

    El cuerpo lleva una clave que ningún campo de ``Cotizacion`` declara y omite
    una que sí declara. Si alguien reinstala una proyección del modelo acá, la
    clave extra desaparece y aparece un cero tipado: este test falla.
    """
    captured: dict[str, Any] = {}

    def _spy(
        func_name: str,
        endpoint_template: str,
        sample_params: dict[str, Any],
        raw_payload: Any,
        base_url: str,
    ) -> tuple[str, str]:
        del endpoint_template, sample_params, base_url
        captured[func_name] = raw_payload
        return ("PASS", "spy")

    monkeypatch.setattr(main_iol, "_write_or_check_schema", _spy)

    body = _clean_body()
    body["claveQueNingunCampoDeclara"] = "presente"
    del body["descripcionTitulo"]  # campo declarado por Cotizacion, ausente del wire

    main_iol.probe_schema_snapshot(client, _TODAY, {"get_quote": body})

    assert captured["get_quote"] == body
    assert "claveQueNingunCampoDeclara" in captured["get_quote"]
    assert "descripcionTitulo" not in captured["get_quote"]


# ---------------------------------------------------------------------------
# 2-3. Las dos direcciones: detecta drift, y no lo inventa
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label", _DRIFT_LABELS)
def test_probe_schema_snapshot_detects_type_drift_added_key_and_removed_key(
    label: str,
    client: Client,
    tmp_schema: Path,
    recorded: list[dict[str, Any]],
) -> None:
    """Las tres clases de drift CR-01 producen SHAPE finding, sin sobreescribir (D-25)."""
    before = tmp_schema.read_bytes()

    result = main_iol.probe_schema_snapshot(client, _TODAY, {"get_quote": _mutated(label)})

    assert result.status == "FINDING", f"{label}: {result!r}"
    assert any(call["class_"] == "SHAPE" and "get_quote" in call["title"] for call in recorded), (
        f"{label}: sin finding SHAPE; recorded={recorded!r}"
    )
    assert tmp_schema.read_bytes() == before, f"{label}: D-25 violado — baseline sobreescrito"


def test_probe_schema_snapshot_passes_on_unmutated_body(
    client: Client,
    tmp_schema: Path,
    recorded: list[dict[str, Any]],
) -> None:
    """Un cuerpo sin mutar produce PASS y cero findings: el probe discrimina en ambas direcciones."""
    body = _clean_body()
    assert schema_of(body) == _baseline_schema(), (
        "el cuerpo sintético derivado ya no reproduce el baseline committeado"
    )
    before = tmp_schema.read_bytes()

    result = main_iol.probe_schema_snapshot(client, _TODAY, {"get_quote": body})

    assert result.status == "PASS", repr(result)
    assert recorded == []
    assert tmp_schema.read_bytes() == before


# ---------------------------------------------------------------------------
# 4-5. probe_field_type_map: rama de type-drift viva + anti-vacuidad
# ---------------------------------------------------------------------------


def test_probe_field_type_map_detects_raw_type_drift(
    client: Client,
    recorded: list[dict[str, Any]],
) -> None:
    """``ultimoPrecio`` como string produce type-drift finding.

    Es la rama que CR-01 probó muerta: una proyección del modelo garantiza que
    llegue un ``float`` al chequeo, cualquiera haya sido el wire.
    """
    result = main_iol.probe_field_type_map(
        client,
        {"get_quote": _mutated("type_drift_ultimoPrecio")},
        [],
    )

    assert result.status == "FINDING", repr(result)
    assert any(
        "type drift" in call["title"] and "ultimoPrecio" in call["title"] for call in recorded
    ), f"sin finding de type drift sobre ultimoPrecio; recorded={recorded!r}"


def test_probe_field_type_map_reports_finding_when_capture_failed(
    client: Client,
) -> None:
    """Una captura fallida NUNCA reporta PASS: los fids de captura siembran el resultado."""
    result = main_iol.probe_field_type_map(client, {}, ["F-01"])

    assert result.status == "FINDING", repr(result)


# ---------------------------------------------------------------------------
# 6. WR-02 como invariante permanente
# ---------------------------------------------------------------------------


def test_assumed_quote_fields_are_all_present_in_committed_baseline() -> None:
    """Toda clave asumida debe estar sostenida por el corpus committeado.

    WR-02 expresado como invariante en vez de como borrado puntual: una clave
    asumida que el baseline no registra emitiría en cada corrida viva un finding
    SHAPE OPEN que ningún cambio upstream puede cerrar. Falla acá, offline, en
    vez de entrenar al operador a ignorar el archivo de findings.
    """
    schema = _baseline_schema()
    unsupported = [k for k in main_iol._ASSUMED_QUOTE_FIELDS if k not in schema]
    assert not unsupported, f"claves asumidas ausentes del baseline: {unsupported}"

    mismatched = {
        k: (declared, schema[k])
        for k, declared in main_iol._ASSUMED_QUOTE_FIELDS.items()
        if schema[k] != declared
    }
    assert not mismatched, f"tipo asumido != tipo del baseline: {mismatched}"


# ---------------------------------------------------------------------------
# 7. El canario: la ceguera de la proyección, hecha permanente
# ---------------------------------------------------------------------------


def test_model_projection_is_blind_to_all_three_drift_classes() -> None:
    """La proyección del modelo no distingue ninguna de las tres mutaciones.

    Es la falsificación propia del verificador, vuelta permanente. Documenta por
    qué el wire crudo es **requerido** y no meramente preferible. Este test pasa
    ya contra el código pre-fix — asserta la ceguera que hoy existe, no la
    corrección. Si algún día el decoder empieza a preservar claves no declaradas,
    este test falla ruidosamente y el fundamento debe revisarse: ése es el
    resultado correcto, no una carga de mantenimiento.
    """
    clean_projection = schema_of(Cotizacion.from_api(_clean_body()).to_dict())
    for label in _DRIFT_LABELS:
        mutated_projection = schema_of(Cotizacion.from_api(_mutated(label)).to_dict())
        assert mutated_projection == clean_projection, (
            f"{label}: la proyección del modelo YA distingue esta mutación — "
            "revisar el fundamento de CR-01"
        )


# ---------------------------------------------------------------------------
# 8. Cuerpo nulo capturado: un insumo que llegó, no una captura que falló
# ---------------------------------------------------------------------------


def test_probe_field_type_map_treats_captured_null_body_as_shape_defect(
    client: Client,
    recorded: list[dict[str, Any]],
) -> None:
    """Los cuatro endpoints con cuerpo nulo producen FINDING, jamás PASS.

    ``capture_fids`` va vacío a propósito: la siembra anti-vacuidad garantizaría
    FINDING por sí sola y enmascararía qué es lo que este caso prueba.

    Son **tres** findings, no cuatro: el probe 12 field-mapea exactamente
    ``get_quote``, ``get_historical_quotes`` y ``get_instruments_by_type``.
    ``get_instruments`` no aparece en ninguna de sus líneas — su cobertura de
    drift la aporta la comparación contra baseline del probe 13.
    """
    result = main_iol.probe_field_type_map(client, _null_wire(), [])

    assert result.status == "FINDING", repr(result)
    shape = [call for call in recorded if call["class_"] == "SHAPE"]
    assert len(shape) == 3, f"esperados 3 findings SHAPE; recorded={recorded!r}"
    for name in _FIELD_MAPPED_ENDPOINTS:
        assert any(name in call["title"] for call in shape), (
            f"ningún finding SHAPE nombra {name}; recorded={recorded!r}"
        )
    assert any("NoneType" in call["actual"] for call in shape), (
        f"ningún finding reporta el tipo observado NoneType — el cuerpo nulo se "
        f"salteó en vez de inspeccionarse; recorded={recorded!r}"
    )


def test_probe_schema_snapshot_treats_captured_null_body_as_shape_defect(
    client: Client,
    tmp_schema_all: dict[str, Path],
    recorded: list[dict[str, Any]],
) -> None:
    """``schema_of`` de un cuerpo nulo difiere de los cuatro baselines committeados."""
    before = {name: path.read_bytes() for name, path in tmp_schema_all.items()}

    result = main_iol.probe_schema_snapshot(client, _TODAY, _null_wire())

    assert result.status == "FINDING", repr(result)
    shape = [call for call in recorded if call["class_"] == "SHAPE"]
    assert len(shape) == 4, f"esperados 4 findings SHAPE; recorded={recorded!r}"
    # Igualdad exacta de títulos, nunca substring: ``Schema drift en
    # get_instruments`` es prefijo de ``Schema drift en get_instruments_by_type``
    # y un chequeo por pertenencia daría verde con tres findings.
    assert {call["title"] for call in shape} == {
        f"Schema drift en {name}" for name in tmp_schema_all
    }, f"títulos={sorted(call['title'] for call in shape)!r}"
    for name, path in tmp_schema_all.items():
        assert path.read_bytes() == before[name], f"D-25 violado — baseline {name} sobreescrito"


def test_a_single_null_bodied_endpoint_is_enough_for_both_probes(
    client: Client,
    tmp_schema: Path,
    recorded: list[dict[str, Any]],
) -> None:
    """La reproducción mínima de 30-REVIEW.md: un solo endpoint con cuerpo nulo."""
    single: dict[str, Any] = {"get_quote": None}

    field_map = main_iol.probe_field_type_map(client, single, [])
    assert field_map.status == "FINDING", repr(field_map)
    assert [call for call in recorded if call["class_"] == "SHAPE"], (
        f"probe 12 no emitió SHAPE sobre un cuerpo nulo; recorded={recorded!r}"
    )

    recorded.clear()
    snapshot = main_iol.probe_schema_snapshot(client, _TODAY, single)
    assert snapshot.status == "FINDING", repr(snapshot)
    assert [call for call in recorded if call["class_"] == "SHAPE"], (
        f"probe 13 no emitió SHAPE sobre un cuerpo nulo; recorded={recorded!r}"
    )
    assert tmp_schema.read_bytes(), "el baseline copiado debe seguir existiendo"


def test_absent_capture_is_still_distinguishable_from_a_null_body(
    client: Client,
    tmp_schema_all: dict[str, Path],
    recorded: list[dict[str, Any]],
) -> None:
    """La otra dirección: una captura genuinamente ausente sigue ruteando a skip.

    Invariante permanente, no un caso RED: pasa tanto antes como después del
    fix de este plan. Existe para que el fix no pueda satisfacerse
    convirtiendo todo skip en finding — ausencia y cuerpo nulo deben quedar
    distinguibles en ambos sentidos.

    La mitad ``probe_field_type_map`` queda exactamente como estaba (su
    ``PASS`` + aserción exacta de detalle es correcta — el probe 12 SÍ recibe
    ``capture_fids`` y una lista vacía legítimamente produce PASS). La mitad
    ``probe_schema_snapshot`` cambió (WR-02, ver el comentario sobre la
    aserción de status abajo).
    """
    field_map = main_iol.probe_field_type_map(client, {}, [])
    assert field_map.status == "PASS", repr(field_map)
    assert field_map.detail == "0 endpoints checked (ninguno), no drift"

    snapshot = main_iol.probe_schema_snapshot(client, _TODAY, {})
    # WR-02: desigualdad, no igualdad con "PASS". La propiedad que este test
    # posee de verdad es que la ausencia rutea a SKIP y jamás fabrica un
    # finding; si el status agregado en una falla de captura TOTAL termina
    # siendo "PASS" o "SKIPPED" es el tema de un defecto separado y todavía
    # abierto (probe 13 no recibe capture_fids para su propia siembra
    # anti-vacuidad, a diferencia del probe 12). Pinear "PASS" cementaría ese
    # defecto; la desigualdad sobrevive a los dos arreglos futuros propuestos
    # (threadear capture_fids al probe 13, o devolver "SKIPPED" cuando
    # written y matched están ambos vacíos).
    assert snapshot.status != "FINDING", repr(snapshot)
    skipped_match = re.search(r"skipped=(\[[^\]]*\])", snapshot.detail)
    assert skipped_match is not None, f"detail no matchea skipped=[...]: {snapshot.detail!r}"
    skipped_names = ast.literal_eval(skipped_match.group(1))
    assert set(skipped_names) == set(tmp_schema_all), (
        f"skipped={skipped_names!r} tmp_schema_all={sorted(tmp_schema_all)!r}"
    )

    assert recorded == [], f"la ausencia no debe emitir findings; recorded={recorded!r}"


def _names_in_pass_detail(detail: str) -> set[str]:
    """Parsea el detalle PASS de ``probe_field_type_map`` en un set exacto de nombres.

    Asertar que el match tuvo éxito, en vez de degradar silenciosamente a un
    set vacío, es lo que hace que un futuro cambio de formato del detalle
    falle ruidosamente acá en vez de disfrazarse de un ``vacio`` falso.
    """
    match = re.fullmatch(r"(\d+) endpoints checked \((.*)\), no drift", detail)
    assert match is not None, f"el detalle no matchea el formato esperado: {detail!r}"
    names = match.group(2)
    if names == "ninguno":
        return set()
    return set(names.split(", "))


@pytest.mark.parametrize(
    ("raw_wire", "expected_checked"),
    [
        pytest.param({}, set(), id="vacio"),
        pytest.param({"get_quote": _clean_body()}, {"get_quote"}, id="solo_get_quote"),
        # Una serie histórica vacía SÍ se nombra como chequeada, y está bien: su
        # forma top-level se validó y no tiene filas que field-mapear, lo que el
        # comentario del propio probe clasifica como cardinalidad, no como forma.
        pytest.param(
            {"get_quote": _clean_body(), "get_historical_quotes": []},
            {"get_quote", "get_historical_quotes"},
            id="quote_mas_serie_vacia",
        ),
        # ``get_instruments`` llega capturado pero el probe 12 no lo field-mapea:
        # esta entrada antes no asertaba NADA, porque ``get_instruments`` no es
        # miembro de ``_FIELD_MAPPED_ENDPOINTS`` y por lo tanto no podía aparecer
        # en la comprensión vieja de ningún modo.
        pytest.param({"get_instruments": _clean_body()}, set(), id="endpoint_no_field_mapeado"),
    ],
)
def test_probe_field_type_map_pass_detail_names_exactly_the_inspected_endpoints(
    raw_wire: dict[str, Any],
    expected_checked: set[str],
    client: Client,
    recorded: list[dict[str, Any]],
) -> None:
    """El detalle de PASS nombra exactamente el conjunto que un lector independiente espera.

    WR-01: la versión anterior de este test re-derivaba, con una comprensión
    sobre ``raw_wire``, la misma pertenencia de clave que el propio probe usa
    para construir el detalle — así que sostenía para cualquier input,
    incluido el PASS patológico pre-fix que su docstring decía prohibir. Ese
    caso patológico (un PASS nombrando tres endpoints sin haber inspeccionado
    ninguno, sobre un cuerpo capturado null) lo bloquea
    ``test_probe_field_type_map_treats_captured_null_body_as_shape_defect``
    (sección 8), no este test: acá ``expected_checked`` es un literal
    independiente por caso, no derivado de ``raw_wire``, y por eso el test
    PUEDE fallar.

    Limitación registrada a propósito: este test observa lo que el probe
    NOMBRA, no lo que INSPECCIONÓ de verdad. Ambos coinciden sólo porque el
    gate del probe y su predicado de detalle son la misma expresión desde
    30-07 — y es la sección 8 la que sostiene esa igualdad.
    """
    result = main_iol.probe_field_type_map(client, raw_wire, [])

    assert result.status == "PASS", f"{result!r}; recorded={recorded!r}"
    assert _names_in_pass_detail(result.detail) == expected_checked, (
        f"detail={result.detail!r} expected_checked={expected_checked!r}"
    )
    assert recorded == [], f"un PASS no debería emitir findings; recorded={recorded!r}"


# ---------------------------------------------------------------------------
# 9. CR-01 (BLOCKER) — un capture failure jamás filtra el body upstream
# ---------------------------------------------------------------------------
#
# Los cuatro nombres de endpoint field-mapeados por ``_capture_raw_wire``, en
# el mismo orden spec (D-IOL-5) en que la función emite sus HTTP calls.
_CAPTURE_ENDPOINT_NAMES = (
    "get_quote",
    "get_historical_quotes",
    "get_instruments",
    "get_instruments_by_type",
)


def _mock_client(handler: Callable[[httpx.Request], httpx.Response]) -> Client:
    """Construye un ``Client`` sobre un ``httpx.MockTransport``, token pre-sembrado.

    ``token=`` + ``token_expires_at=`` en el futuro hacen que
    ``_core.token_is_fresh`` devuelva ``True``, así que ``_ensure_token`` NUNCA
    dispara una request de auth: el test queda offline y determinístico, y
    además ningún valor de credencial llega jamás al transport.
    ``username``/``password`` son dummy y nunca se leen porque el token ya
    está fresco. El ``Client`` es un context manager: al cerrarse cierra
    también el ``httpx.Client`` inyectado, porque ambos comparten el mismo
    objeto vía ``self._state.http_client``.
    """
    inner = httpx.Client(transport=httpx.MockTransport(handler), base_url=_BASE_URL)
    return Client(
        base_url=_BASE_URL,
        username="u",
        password="p",
        token="tok-de-prueba",
        token_expires_at=time.time() + 3600,
        http_client=inner,
    )


def _error_body_with_marker() -> str:
    """Body de error con forma real de IOL, con el marker en posición de cuenta."""
    return json.dumps({"cuenta": f"{_WIRE_BODY_MARKER}-cuenta-999999", "detalle": "boom"})


def _handler_500_with_marker(request: httpx.Request) -> httpx.Response:
    del request
    return httpx.Response(500, text=_error_body_with_marker())


def _handler_connect_error(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError(_WIRE_BODY_MARKER, request=request)


def _handler_partial_failure(request: httpx.Request) -> httpx.Response:
    """``get_quote`` responde 200 limpio; los otros tres, 500 con el marker.

    El discriminador es ``endswith("/Cotizacion")`` exacto, no una substring:
    el path de ``get_quote`` (``.../Titulos/GGAL/Cotizacion``) es un prefijo
    estricto del path de ``get_historical_quotes``
    (``.../Cotizacion/seriehistorica/...``), así que una substring test
    clasificaría mal ese segundo endpoint como éxito.
    """
    if request.url.path.endswith("/Cotizacion"):
        return httpx.Response(200, json=_clean_body())
    return httpx.Response(500, text=_error_body_with_marker())


def _offending_kwargs(recorded: list[dict[str, Any]]) -> list[tuple[int, str]]:
    """(índice de llamada, nombre de kwarg) para todo par cuyo valor lleve el marker.

    Coerciona cada valor con ``str()`` antes de buscar el marker, para que un
    kwarg no-string no pueda esconderlo. Compartido por los tests de esta
    sección para que el mensaje de falla sea uniforme y diagnosticable desde
    la salida de pytest sola.
    """
    return [
        (i, key)
        for i, call in enumerate(recorded)
        for key, value in call.items()
        if _WIRE_BODY_MARKER in str(value)
    ]


def test_capture_failure_finding_never_carries_the_upstream_response_body(
    recorded: list[dict[str, Any]],
) -> None:
    """Un marker plantado en el body de un 500 no aparece en NINGÚN kwarg registrado.

    Maneja los cuatro endpoints spec y falla si el marker aparece en
    cualquier lugar de cualquier finding — no sólo en ``actual`` — porque el
    invariante que CR-01 cierra es sobre el registro completo, no sobre un
    campo puntual.
    """
    with _mock_client(_handler_500_with_marker) as client:
        raw_by_endpoint, capture_fids = main_iol._capture_raw_wire(client, _TODAY)

    assert raw_by_endpoint == {}
    assert len(capture_fids) == 4
    assert len(recorded) == 4
    assert all(call["class_"] == "ERROR-MAP" for call in recorded), repr(recorded)

    offenders = _offending_kwargs(recorded)
    assert offenders == [], f"marker filtrado en (índice de llamada, kwarg): {offenders}"


def test_capture_failure_finding_reports_only_the_exception_type_and_status_code(
    recorded: list[dict[str, Any]],
) -> None:
    """``actual`` reporta exactamente ``IOLAPIError status_code=500`` — igualdad exacta.

    Una comparación por substring pasaría con un string que además llevara el
    body; la exactitud es el punto.
    """
    with _mock_client(_handler_500_with_marker) as client:
        main_iol._capture_raw_wire(client, _TODAY)

    assert len(recorded) == 4
    assert all(call["actual"] == "IOLAPIError status_code=500" for call in recorded), repr(recorded)
    assert all(call["diff"] == "type=IOLAPIError" for call in recorded), repr(recorded)
    titles = {call["title"] for call in recorded}
    assert titles == {
        f"captura de wire crudo falló en {name}" for name in _CAPTURE_ENDPOINT_NAMES
    }, f"titles={titles!r}"


def test_capture_failure_without_a_status_code_reports_the_type_and_none(
    recorded: list[dict[str, Any]],
) -> None:
    """Una falla de transporte (sin response, sin ``status_code``) reporta ``...=None``.

    Prueba que el fix lee el status code defensivamente en vez de asumir que
    toda excepción que llega al handler es un ``IOLAPIError``.
    """
    with _mock_client(_handler_connect_error) as client:
        raw_by_endpoint, capture_fids = main_iol._capture_raw_wire(client, _TODAY)

    assert raw_by_endpoint == {}
    assert len(capture_fids) == 4
    assert len(recorded) == 4
    assert all(call["actual"] == "ConnectError status_code=None" for call in recorded), repr(
        recorded
    )

    offenders = _offending_kwargs(recorded)
    assert offenders == [], f"marker filtrado en (índice de llamada, kwarg): {offenders}"


def test_capture_failure_leaves_the_endpoint_absent_and_still_returns_its_fid(
    recorded: list[dict[str, Any]],
) -> None:
    """Invariante permanente (verde antes y después del fix).

    Un endpoint fallido queda AUSENTE del dict devuelto, nunca
    presente-con-null, y el fid list tiene longitud 4 y coincide en orden con
    los ``fid`` registrados — la siembra anti-vacuidad del probe 12 depende de
    esto y la redacción no debe perturbarlo.
    """
    with _mock_client(_handler_500_with_marker) as client:
        raw_by_endpoint, capture_fids = main_iol._capture_raw_wire(client, _TODAY)

    assert raw_by_endpoint == {}
    assert len(capture_fids) == 4
    assert capture_fids == [call["fid"] for call in recorded]


def test_a_partial_capture_failure_redacts_only_the_failed_endpoints(
    recorded: list[dict[str, Any]],
) -> None:
    """Un endpoint exitoso se guarda verbatim; los otros tres se redactan sin excepción."""
    with _mock_client(_handler_partial_failure) as client:
        raw_by_endpoint, capture_fids = main_iol._capture_raw_wire(client, _TODAY)

    assert set(raw_by_endpoint) == {"get_quote"}
    assert raw_by_endpoint["get_quote"] == _clean_body()
    assert len(capture_fids) == 3
    assert len(recorded) == 3

    offenders = _offending_kwargs(recorded)
    assert offenders == [], f"marker filtrado en (índice de llamada, kwarg): {offenders}"
