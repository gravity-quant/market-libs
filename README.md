# market-libs

Monorepo Python con clientes HTTP (sync y async) para servicios financieros argentinos.

## Paquetes

| Paquete | Servicio | Estado |
| ------- | -------- | ------ |
| [`higyrus-client`](packages/higyrus-client) | Higyrus | Alpha |
| [`wallets-client`](packages/wallets-client) | Wallets | Alpha |
| [`matriz-client`](packages/matriz-client) | Matriz | Alpha |
| [`iol-client`](packages/iol-client) | Invertir Online (IOL) | Alpha |
| [`ambito-financiero-client`](packages/ambito-financiero-client) | Ámbito Financiero | Alpha |

Cada paquete es **independiente**: sin dependencias internas entre ellos, se puede instalar y publicar por separado.

## Setup

Requiere [uv](https://docs.astral.sh/uv/) y Python 3.12+.

```bash
# Sincronizar el workspace completo (instala todos los paquetes en modo editable
# + dev-dependencies compartidas: ruff, mypy, pytest, pre-commit)
uv sync --all-packages --all-extras --dev

# Activar pre-commit
uv run pre-commit install
```

## Comandos comunes

```bash
# Lint + format (todo el monorepo)
uv run ruff check .
uv run ruff format .

# Type check (todo el monorepo)
uv run mypy

# Correr todos los tests
uv run pytest

# Tests de un paquete específico
uv run pytest packages/iol-client

# Coverage de un paquete
uv run pytest packages/iol-client \
    --cov=packages/iol-client/src --cov-report=term-missing

# Ejecutar algo dentro del entorno de un paquete específico
uv run --package iol-client python -c "from iol_client import IOLClient"

# Build de un paquete (genera wheel + sdist en dist/)
uv build --package iol-client
```

## Estructura

```
market-libs/
├── pyproject.toml              # Workspace root: configs de ruff/mypy/pytest, dev-deps
├── uv.lock                     # Lockfile único del workspace
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml    # Lint + typecheck + matriz de tests por paquete
└── packages/
    └── <name>-client/
        ├── pyproject.toml      # Metadatos y deps propias del paquete
        ├── README.md
        ├── src/<name>_client/
        │   ├── __init__.py     # Re-exports públicos
        │   ├── client.py       # Cliente sincrónico
        │   ├── async_client.py # Cliente asincrónico
        │   ├── exceptions.py
        │   └── py.typed        # Marca el paquete como tipado (PEP 561)
        └── tests/
            ├── conftest.py
            ├── test_client.py
            └── test_async_client.py
```

## Agregar un paquete nuevo

1. Copiar uno existente: `cp -R packages/iol-client packages/foo-client`.
2. Renombrar el directorio del módulo: `mv packages/foo-client/src/iol_client packages/foo-client/src/foo_client`.
3. Reemplazar las referencias `iol`/`IOL`/`Invertir Online` por las del nuevo servicio (en `pyproject.toml`, `README.md`, y los `.py`).
4. Agregar el paquete a la matriz de tests en `.github/workflows/ci.yml`.
5. `uv sync --all-packages` para registrarlo en el workspace.

> El workspace ya descubre `packages/*` automáticamente; no hace falta listar cada paquete en el `pyproject.toml` raíz, salvo en `[tool.uv.sources]` si querés permitir que un paquete dependa de otro del workspace.

## Distribución

Por ahora cada paquete está marcado como **Alpha** y no se publica. Cuando se decida el destino:

- **PyPI privado**: agregar `[[tool.uv.index]]` al pyproject raíz y `uv publish --index <name>`.
- **PyPI público**: `uv build --package <name> && uv publish` desde un workflow de release.
- **Sólo git**: instalable con `pip install "iol-client @ git+ssh://git@github.com/.../market-libs.git#subdirectory=packages/iol-client"`.
