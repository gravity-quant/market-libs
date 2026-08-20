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
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import main_iol
import pytest

from iol_client import Client, Cotizacion
from verification import findings as findings_module
from verification.schema import schema_of

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BASELINE_PATH = (
    _REPO_ROOT / ".planning" / "verification" / "schemas" / "iol-client" / "get-quote.json"
)
_BASE_URL = "https://api.test"
_TODAY = dt.date(2026, 6, 8)

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
