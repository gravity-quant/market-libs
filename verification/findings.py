"""Helper de archivo de hallazgos clasificados (HARN-05/D-07/08/09/D-10).

El entregable primario es la plantilla documentada
``.planning/verification/FINDINGS-TEMPLATE.md``; este módulo es un helper de
conveniencia que renderiza el esqueleto de encabezado + índice para iniciar un
archivo de hallazgos por paquete en ``.planning/verification/<pkg>-findings.md``,
y además permite agregar/actualizar findings de forma idempotente vía
``append_finding`` (D-10) sin pisar status promovidos por humano.

Clases fijas (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA,
ANTI-BOT. Ciclo de estados (D-08): OPEN -> CONFIRMED -> FIXED, más terminales
EXPECTED/NO-FIX. No hay campo de severidad.

Uso::

    from verification.findings import new_findings, write_findings, append_finding

    write_findings("higyrus")   # crea .planning/verification/higyrus-findings.md
    append_finding(              # agrega F-01 al index + sección detalle
        "higyrus",
        fid="F-01",
        class_="SHAPE",
        surface="sync",
        status="OPEN",
        title="campo X faltante",
        expected="cliente espera X",
        actual="API devuelve sin X",
        diff="key X ausente",
    )

Idempotencia (D-10): re-llamada con mismo ``fid`` actualiza el row; si el
status existente NO es OPEN (CONFIRMED/FIXED/EXPECTED/NO-FIX = status humano
promovido), el finding NO se toca. El ART block del header (Timestamp,
base URL, market_hours) se refresca en cada call.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "FINDING_CLASSES",
    "STATUS_LIFECYCLE",
    "append_finding",
    "findings_path",
    "new_findings",
    "write_findings",
]

# Raíz del repo = el directorio que contiene el paquete ``verification/``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_FINDINGS_DIR = _REPO_ROOT / ".planning" / "verification"

# Slug de paquete: lower-kebab-case con primer char alfanumérico. Acota
# ``findings_path`` para que no resuelva fuera de ``_FINDINGS_DIR`` (WR-04 —
# path traversal). Coincide con la convención de nombres de paquete del repo.
_PKG_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _validate_pkg_slug(pkg: str) -> None:
    """Rechaza slugs de paquete inválidos (WR-04 — defensa contra path traversal).

    El validador es estricto: lower-kebab-case con primer char alfanumérico.
    Coincide con los nombres de paquete del repo (``ambito-financiero-client``,
    ``iol-client``, etc.) y bloquea ``../``, separadores de path, mayúsculas,
    espacios, etc.
    """
    if not isinstance(pkg, str) or not _PKG_SLUG_RE.fullmatch(pkg):
        raise ValueError(f"invalid pkg slug: {pkg!r}; debe coincidir con r'^[a-z0-9][a-z0-9-]*$'")


# Clases fijas de hallazgos (D-09) — orden documentado.
FINDING_CLASSES: tuple[str, ...] = (
    "SHAPE",
    "AUTH",
    "ERROR-MAP",
    "PARAM",
    "SYNC-ASYNC-DRIFT",
    "NO-DATA",
    "ANTI-BOT",
)

# Ciclo de estados (D-08) — sin campo de severidad.
STATUS_LIFECYCLE: tuple[str, ...] = ("OPEN", "CONFIRMED", "FIXED", "EXPECTED", "NO-FIX")

# Phase 11 HARN-07 — markers HTML-comment que delimitan la zona auto-gestionada
# del archivo de findings. Contenido ARRIBA del BEGIN o ABAJO del END es
# operator-owned y sobrevive verbatim los re-runs.
_AUTO_BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED -->"
_AUTO_END_MARKER = "<!-- END AUTO-GENERATED -->"


def findings_path(pkg: str) -> Path:
    """Ruta del archivo de hallazgos para ``pkg``: ``.planning/verification/<pkg>-findings.md``.

    Valida ``pkg`` contra :data:`_PKG_SLUG_RE` (WR-04): rechaza inputs que
    permitirían path traversal (``../etc/passwd``) o caracteres de path.
    """
    _validate_pkg_slug(pkg)
    return _FINDINGS_DIR / f"{pkg}-findings.md"


def new_findings(pkg: str) -> str:
    """Renderiza el esqueleto (encabezado ART + índice vacío) de un archivo de hallazgos.

    Phase 11 HARN-07: el ``## Index`` queda envuelto por los markers
    ``<!-- BEGIN AUTO-GENERATED -->`` / ``<!-- END AUTO-GENERATED -->`` que
    delimitan la zona auto-gestionada del archivo. Cualquier contenido que el
    operador inserte ARRIBA del BEGIN o ABAJO del END sobrevive verbatim los
    re-runs de :func:`append_finding`.
    """
    _validate_pkg_slug(pkg)
    classes = ", ".join(FINDING_CLASSES)
    lifecycle = " -> ".join(("OPEN", "CONFIRMED", "FIXED")) + " (+ terminal EXPECTED/NO-FIX)"
    return (
        f"# Findings: {pkg}-client\n"
        "\n"
        "## Run Context (ART)\n"
        "- Timestamp: <ISO-8601>\n"
        "- Resolved base URL / env: <url> (<remarkets|prod|public>)\n"
        "- Market hours note: <abierto|cerrado — afecta paths sesión-dependientes>\n"
        "\n"
        f"<!-- Clases (D-09): {classes} -->\n"
        f"<!-- Estados (D-08): {lifecycle}. Sin campo de severidad. -->\n"
        "\n"
        f"{_AUTO_BEGIN_MARKER}\n"
        "## Index\n"
        "| ID | Class | Surface | Status |\n"
        "|----|-------|---------|--------|\n"
        f"{_AUTO_END_MARKER}\n"
    )


def write_findings(pkg: str, *, overwrite: bool = False) -> Path:
    """Crea ``.planning/verification/<pkg>-findings.md`` con el esqueleto y devuelve la ruta.

    Si el archivo ya existe y ``overwrite`` es ``False``, no lo sobreescribe.
    """
    _FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
    path = findings_path(pkg)
    if path.exists() and not overwrite:
        return path
    path.write_text(new_findings(pkg), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# append_finding (D-10) — internals
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Finding:
    """Modelo interno de un finding parseado/serializable."""

    fid: str
    class_: str
    surface: str
    status: str
    title: str
    expected: str
    actual: str
    diff: str
    regression: str | None = None


@dataclass(slots=True)
class _ParsedFile:
    """Resultado de parsear un findings file existente.

    Phase 11 HARN-07: ``operator_prefix`` y ``operator_suffix`` capturan las
    líneas (preservando el orden) ARRIBA del marker ``BEGIN AUTO-GENERATED``
    y ABAJO del marker ``END AUTO-GENERATED`` respectivamente. Estas líneas se
    re-emiten verbatim al re-serializar.
    """

    findings: list[_Finding] = field(default_factory=list)
    art: dict[str, str] = field(default_factory=dict)
    operator_prefix: list[str] = field(default_factory=list)
    operator_suffix: list[str] = field(default_factory=list)


# Regex para la fila del índice: `| F-NN | CLASS | SURFACE | STATUS |`.
_INDEX_ROW_RE = re.compile(
    r"^\|\s*(?P<fid>F-[^|]+?)\s*\|\s*(?P<class_>[^|]+?)\s*\|"
    r"\s*(?P<surface>[^|]+?)\s*\|\s*(?P<status>[^|]+?)\s*\|\s*$"
)
# Header de detalle: `### F-NN -- <título>`.
_DETAIL_HEADER_RE = re.compile(r"^###\s+(?P<fid>F-[^\s]+)\s+--\s+(?P<title>.*?)\s*$")
# Línea Class/Surface/Status del detalle.
_DETAIL_META_RE = re.compile(
    r"^\*\*Class:\*\*\s+`(?P<class_>[^`]+)`\s+\.\s+"
    r"\*\*Surface:\*\*\s+`(?P<surface>[^`]+)`\s+\.\s+"
    r"\*\*Status:\*\*\s+`(?P<status>[^`]+)`\s*$"
)
# Bullet `- **<Label>:** <valor>`.
_DETAIL_BULLET_RE = re.compile(r"^- \*\*(?P<label>[^:]+):\*\*\s*(?P<value>.*)$")

# Regex para refrescar in-place las 3 líneas del ART block sin re-serializar
# el archivo completo (CR-01 — preserva prosa/bullets/notas que añade un humano
# al promover un finding a CONFIRMED/FIXED/EXPECTED/NO-FIX).
_ART_TIMESTAMP_RE = re.compile(r"^- Timestamp:.*$", re.MULTILINE)
_ART_BASEURL_RE = re.compile(r"^- Resolved base URL / env:.*$", re.MULTILINE)
_ART_MARKET_RE = re.compile(r"^- Market hours note:.*$", re.MULTILINE)


def _replace_art_block(text: str, art: dict[str, str]) -> str:
    """Reemplaza in-place las 3 líneas del ART block preservando el resto del archivo.

    Usado por :func:`append_finding` en la preservation path (status humano
    promovido) para evitar el round-trip lossy de :func:`_serialize_findings`,
    que sólo conoce los bullets canónicos (Expected/Actual/Diff/Regression) y
    descartaría cualquier prosa libre, bullets extra (``- **Notes:**``,
    ``- **Repro:**``) o párrafos de triage que un humano añadió al promover
    un finding.

    Si una línea del ART no existe en ``text`` (archivo malformado o editado
    manualmente), el reemplazo es no-op para esa key.
    """
    timestamp = art.get("Timestamp")
    if timestamp is not None:
        text = _ART_TIMESTAMP_RE.sub(f"- Timestamp: {timestamp}", text, count=1)
    base_url = art.get("Resolved base URL / env")
    if base_url is not None:
        text = _ART_BASEURL_RE.sub(f"- Resolved base URL / env: {base_url}", text, count=1)
    market_hours = art.get("Market hours note")
    if market_hours is not None:
        text = _ART_MARKET_RE.sub(f"- Market hours note: {market_hours}", text, count=1)
    return text


def _parse_findings(text: str) -> _ParsedFile:
    """Parsea un findings file existente a modelo interno.

    Estrategia: line-scan en dos pasadas estructurales —
    (1) ART block (líneas que empiezan con ``- Timestamp:`` etc. dentro de
        ``## Run Context (ART)``);
    (2) Tabla ``## Index`` para descubrir IDs + status canónico;
    (3) Sección ``## Detalle por hallazgo`` con un ``### F-NN -- <título>``
        por finding; los bullets ``- **Expected:**`` etc. siguen al header.

    Phase 11 HARN-07 — 3-zone parsing:
    El archivo se divide en tres zonas según los markers HTML-comment:

    - **Operator prefix**: líneas ARRIBA del ``<!-- BEGIN AUTO-GENERATED -->``.
      Capturadas verbatim en :attr:`_ParsedFile.operator_prefix` (incluye
      header del paquete, ART block, comentarios de clases/estados).
    - **Auto-zone**: líneas entre BEGIN y END markers — donde corre el
      parser de Index + Detalle.
    - **Operator suffix**: líneas ABAJO del ``<!-- END AUTO-GENERATED -->``.
      Capturadas verbatim en :attr:`_ParsedFile.operator_suffix` (incluye
      sección Cycle Closure y cualquier nota operator-added).

    Back-compat: archivos SIN markers (baseline PRE-migration) se parsean
    como si toda la zona fuese auto-zone (los markers se asumen "implícitos");
    ``operator_prefix`` y ``operator_suffix`` quedan vacíos. La detección se
    hace pre-loop chequeando presencia del marker BEGIN.

    El parser es tolerante: si una sección falta, devuelve valores por
    defecto. Si una fila no matchea el regex, se ignora silenciosamente.
    """
    lines = text.splitlines()

    # Pre-scan: detectar si el archivo ya tiene markers. Si no los tiene,
    # tratamos TODO el contenido como auto-zone (back-compat para baseline
    # PRE-migration files).
    has_markers = _AUTO_BEGIN_MARKER in text and _AUTO_END_MARKER in text

    art: dict[str, str] = {}
    # Estado de scan.
    in_art = False
    in_index = False
    detail_meta: dict[str, dict[str, str]] = {}  # fid -> meta dict
    detail_titles: dict[str, str] = {}  # fid -> title (del header del detalle)
    index_status: dict[str, str] = {}  # fid -> status visto en el índice
    index_class: dict[str, str] = {}
    index_surface: dict[str, str] = {}
    # Para parsing del detalle: cuando estamos dentro de un ### F-NN block,
    # tracking del fid actual y de los bullets vistos.
    current_fid: str | None = None
    bullets_by_fid: dict[str, dict[str, str]] = {}
    insertion_order: list[str] = []

    # Phase 11 HARN-07 — zone state machine.
    # Cuando ``has_markers`` es False, ``in_auto_zone`` arranca True y las dos
    # listas de operador quedan vacías (back-compat). Cuando hay markers,
    # in_auto_zone arranca False y se activa al ver BEGIN.
    in_auto_zone = not has_markers
    seen_end = False
    operator_prefix: list[str] = []
    operator_suffix: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip("\r")

        # Zone transitions (HARN-07). El marker MUST ser una línea entera para
        # transitionar; matches parciales o markers en strings rotos quedan
        # como contenido normal.
        if line == _AUTO_BEGIN_MARKER:
            in_auto_zone = True
            # El marker en sí no se preserva en prefix/suffix — se re-emite
            # por _serialize_findings.
            continue
        if line == _AUTO_END_MARKER:
            in_auto_zone = False
            seen_end = True
            continue

        if has_markers and not in_auto_zone:
            # Operator territory — capturar verbatim (preservar raw_line con
            # CR si existía, aunque ya se hizo rstrip; usamos line).
            if seen_end:
                operator_suffix.append(line)
            else:
                operator_prefix.append(line)
            continue

        # ART section start/end
        if line.startswith("## Run Context (ART)"):
            in_art = True
            in_index = False
            current_fid = None
            continue
        if line.startswith("## Index"):
            in_art = False
            in_index = True
            current_fid = None
            continue
        if line.startswith(("## Detalle por hallazgo", "## ")):
            in_art = False
            in_index = False
            if not line.startswith("## Detalle por hallazgo"):
                current_fid = None
            continue

        if in_art:
            if line.startswith("- Timestamp:"):
                art["Timestamp"] = line[len("- Timestamp:") :].strip()
            elif line.startswith("- Resolved base URL / env:"):
                art["Resolved base URL / env"] = line[len("- Resolved base URL / env:") :].strip()
            elif line.startswith("- Market hours note:"):
                art["Market hours note"] = line[len("- Market hours note:") :].strip()
            continue

        if in_index:
            m = _INDEX_ROW_RE.match(line)
            if m is None:
                continue
            fid = m.group("fid").strip()
            # Saltar la fila header `| ID | Class | Surface | Status |` (no es F-NN).
            if not fid.startswith("F-"):
                continue
            index_class[fid] = m.group("class_").strip()
            index_surface[fid] = m.group("surface").strip()
            index_status[fid] = m.group("status").strip()
            if fid not in insertion_order:
                insertion_order.append(fid)
            continue

        # Fuera de Index/ART: estamos en zona de detalle.
        detail_match = _DETAIL_HEADER_RE.match(line)
        if detail_match is not None:
            current_fid = detail_match.group("fid").strip()
            detail_titles[current_fid] = detail_match.group("title").strip()
            bullets_by_fid.setdefault(current_fid, {})
            if current_fid not in insertion_order:
                insertion_order.append(current_fid)
            continue

        if current_fid is not None:
            meta_match = _DETAIL_META_RE.match(line)
            if meta_match is not None:
                detail_meta[current_fid] = {
                    "class_": meta_match.group("class_").strip(),
                    "surface": meta_match.group("surface").strip(),
                    "status": meta_match.group("status").strip(),
                }
                continue
            bullet_match = _DETAIL_BULLET_RE.match(line)
            if bullet_match is not None:
                label = bullet_match.group("label").strip()
                value = bullet_match.group("value").strip()
                bullets_by_fid.setdefault(current_fid, {})[label] = value
                continue

    # Reconciliar: el status canónico viene del Index (es lo que el humano
    # edita primero). Si el Index discrepa del detalle, gana el Index.
    findings: list[_Finding] = []
    for fid in insertion_order:
        # class_/surface/status: prefer Index; fallback al detalle.
        class_ = index_class.get(fid) or detail_meta.get(fid, {}).get("class_", "")
        surface = index_surface.get(fid) or detail_meta.get(fid, {}).get("surface", "")
        status = index_status.get(fid) or detail_meta.get(fid, {}).get("status", "")
        title = detail_titles.get(fid, "")
        bullets = bullets_by_fid.get(fid, {})
        expected = bullets.get("Expected", "")
        actual = bullets.get("Actual", "")
        diff = bullets.get("Diff", "")
        regression_raw = bullets.get("Regression")
        regression: str | None = regression_raw if regression_raw else None
        findings.append(
            _Finding(
                fid=fid,
                class_=class_,
                surface=surface,
                status=status,
                title=title,
                expected=expected,
                actual=actual,
                diff=diff,
                regression=regression,
            )
        )

    return _ParsedFile(
        findings=findings,
        art=art,
        operator_prefix=operator_prefix,
        operator_suffix=operator_suffix,
    )


def _serialize_findings(
    pkg: str,
    findings: list[_Finding],
    art: dict[str, str],
    *,
    prefix: list[str] | None = None,
    suffix: list[str] | None = None,
) -> str:
    """Re-renderiza el archivo entero desde el modelo interno.

    Estructura: header del paquete + ART block (con valores resueltos) +
    comentarios HTML de clases/estados + marker ``<!-- BEGIN AUTO-GENERATED -->`` +
    tabla ``## Index`` + sección ``## Detalle por hallazgo`` + marker
    ``<!-- END AUTO-GENERATED -->``.

    Phase 11 HARN-07: cuando ``prefix`` y/o ``suffix`` se proveen (vienen del
    ``_ParsedFile.operator_prefix``/``operator_suffix``), reemplazan el header +
    ART block emitido por defecto (``prefix``) y se añaden al final del archivo
    (``suffix``), preservando el contenido operator-owned verbatim. Los markers
    BEGIN/END siempre se emiten (contrato HARN-07).
    """
    classes = ", ".join(FINDING_CLASSES)
    lifecycle = " -> ".join(("OPEN", "CONFIRMED", "FIXED")) + " (+ terminal EXPECTED/NO-FIX)"

    timestamp = art.get("Timestamp", "<ISO-8601>")
    base_url = art.get(
        "Resolved base URL / env",
        "<url> (<remarkets|prod|public>)",
    )
    market_hours = art.get(
        "Market hours note",
        "<abierto|cerrado — afecta paths sesión-dependientes>",
    )

    out: list[str] = []
    if prefix:
        # Operator-owned prefix preserva el header + ART block + clases/estados
        # comments + cualquier prosa adicional que el operador haya inyectado
        # arriba del BEGIN marker. Re-emitimos verbatim.
        out.extend(prefix)
    else:
        out.append(f"# Findings: {pkg}-client")
        out.append("")
        out.append("## Run Context (ART)")
        out.append(f"- Timestamp: {timestamp}")
        out.append(f"- Resolved base URL / env: {base_url}")
        out.append(f"- Market hours note: {market_hours}")
        out.append("")
    # Clases/estados comments — sólo se emiten si NO había prefix operator-owned
    # (cuando prefix viene del parsed file, esos comments ya están dentro del
    # prefix verbatim).
    if not prefix:
        out.append(f"<!-- Clases (D-09): {classes} -->")
        out.append(f"<!-- Estados (D-08): {lifecycle}. Sin campo de severidad. -->")
        out.append("")
    # HARN-07: marker BEGIN delimita el inicio de la auto-zone.
    out.append(_AUTO_BEGIN_MARKER)
    out.append("## Index")
    out.append("| ID | Class | Surface | Status |")
    out.append("|----|-------|---------|--------|")
    for f in findings:
        out.append(f"| {f.fid} | {f.class_} | {f.surface} | {f.status} |")

    if findings:
        out.append("")
        out.append("## Detalle por hallazgo")
        for f in findings:
            out.append("")
            out.append(f"### {f.fid} -- {f.title}")
            out.append("")
            out.append(
                f"**Class:** `{f.class_}` . **Surface:** `{f.surface}` . **Status:** `{f.status}`"
            )
            out.append("")
            out.append(f"- **Expected:** {f.expected}")
            out.append(f"- **Actual:** {f.actual}")
            out.append(f"- **Diff:** {f.diff}")
            if f.regression is not None:
                out.append(f"- **Regression:** {f.regression}")

    # HARN-07: marker END delimita el fin de la auto-zone.
    out.append(_AUTO_END_MARKER)

    # Operator-owned suffix — preservado verbatim después del END marker.
    if suffix:
        out.extend(suffix)

    return "\n".join(out) + "\n"


def append_finding(
    pkg: str,
    *,
    fid: str,
    class_: str,
    surface: str,
    status: str,
    title: str,
    expected: str,
    actual: str,
    diff: str,
    regression: str | None = None,
    base_url: str | None = None,
    market_hours: str | None = None,
    idempotent_by_title: bool = False,
) -> Path:
    """Agrega o actualiza un finding ``fid`` en ``<pkg>-findings.md`` (D-10).

    Invariantes:

    - Si el archivo no existe, lo crea con el esqueleto vía
      :func:`write_findings`.
    - Idempotente por ``fid``: re-llamada con mismo ``fid`` actualiza la
      entrada existente (sin duplicar la fila del Index).
    - **Preservación de status humano** (Pitfall 1 / D-10): si el ``fid``
      existe con status promovido por humano (CONFIRMED/FIXED/EXPECTED/NO-FIX),
      el finding NO se toca — solo el ART block se refresca.
    - ``class_`` debe estar en :data:`FINDING_CLASSES`; ``status`` en
      :data:`STATUS_LIFECYCLE` — ``ValueError`` si no.
    - El ART block (``Timestamp``, ``Resolved base URL / env``,
      ``Market hours note``) se refresca en cada call. ``Timestamp`` se
      regenera como UTC ISO-8601 actual. ``base_url`` y ``market_hours``
      se reemplazan solo si se pasan como argumento.

    Phase 11 HARN-08/10 — ``idempotent_by_title``:

    - Cuando ``idempotent_by_title=True``, ANTES de la guard de preservation
      por status humano, se busca si **algún** finding existente tiene el
      mismo ``title``. Si lo hay, el call se considera no-op (solo se
      refresca el ART block) y se retorna sin modificar el finding existente
      ni añadir uno nuevo. Esto cierra HARN-08 (content-addressed dedupe
      cross-driver — terminales EXPECTED/NO-FIX no se duplican aunque el
      driver use un ``_next_fid()`` distinto cada run) y HARN-10 (matriz
      ``D-MATZ-27`` EXPECTED terminal dedupe en un solo run).
    - Default ``False`` preserva el comportamiento legacy fid-based.

    Devuelve el :class:`Path` al archivo escrito.
    """
    if class_ not in FINDING_CLASSES:
        raise ValueError(f"class_={class_!r} no está en FINDING_CLASSES={FINDING_CLASSES!r}")
    if status not in STATUS_LIFECYCLE:
        raise ValueError(f"status={status!r} no está en STATUS_LIFECYCLE={STATUS_LIFECYCLE!r}")
    # CR-02: invariante de single-line title. El header `### F-NN -- <título>`
    # y el round-trip via regex no manejan saltos de línea; un title con `\n`
    # se truncaría silenciosamente en la primera línea durante la próxima
    # llamada. Falla temprano con un mensaje accionable.
    if "\n" in title or "\r" in title:
        raise ValueError(f"title debe ser una sola línea; recibido {title!r} (CR-02 invariant)")

    path = findings_path(pkg)
    if not path.exists():
        write_findings(pkg)

    text = path.read_text(encoding="utf-8")
    parsed = _parse_findings(text)
    findings_list = parsed.findings
    art = parsed.art

    # Refrescar ART block siempre — incluso si solo se preserva un status humano,
    # el run actual queda registrado en el header.
    art["Timestamp"] = dt.datetime.now(dt.UTC).isoformat()
    if base_url is not None:
        art["Resolved base URL / env"] = base_url
    if market_hours is not None:
        art["Market hours note"] = market_hours

    existing = {f.fid: f for f in findings_list}

    # HARN-08/10 — content-addressed dedupe by title (opt-in via kwarg).
    # Si ya existe un finding con el mismo title, el call es no-op excepto por
    # el refresh del ART block (preserva el finding original byte-identical —
    # title preservado, fid original preservado, fields preservados).
    if idempotent_by_title:
        for existing_finding in findings_list:
            if existing_finding.title == title:
                path.write_text(_replace_art_block(text, art), encoding="utf-8")
                return path

    # CR-01: Preservación de status promovido por humano. Si ya existe un
    # finding con status != OPEN, NO re-serializamos el archivo (eso
    # descartaría prosa libre, bullets extra como ``**Notes:**``/``**Repro:**``,
    # y párrafos de triage que el humano añadió). En su lugar, sólo
    # refrescamos las 3 líneas del ART block in-place sobre el texto original.
    if fid in existing and existing[fid].status != "OPEN":
        path.write_text(_replace_art_block(text, art), encoding="utf-8")
        return path

    new = _Finding(
        fid=fid,
        class_=class_,
        surface=surface,
        status=status,
        title=title,
        expected=expected,
        actual=actual,
        diff=diff,
        regression=regression,
    )
    if fid in existing:
        findings_list = [new if f.fid == fid else f for f in findings_list]
    else:
        findings_list.append(new)

    path.write_text(
        _serialize_findings(
            pkg,
            findings_list,
            art,
            prefix=parsed.operator_prefix,
            suffix=parsed.operator_suffix,
        ),
        encoding="utf-8",
    )
    return path
