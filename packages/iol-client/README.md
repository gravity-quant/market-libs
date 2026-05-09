# iol-client

Cliente HTTP (sync y async) para la API de [Invertir Online (IOL)](https://www.invertironline.com/).

## Instalación

```bash
uv add iol-client
# o, dentro del workspace:
uv sync
```

## Uso

### Sync

```python
from iol_client import IOLClient

with IOLClient(token="...") as client:
    portfolio = client.get_portfolio()
```

### Async

```python
from iol_client import AsyncIOLClient

async with AsyncIOLClient(token="...") as client:
    portfolio = await client.get_portfolio()
```

## Desarrollo

```bash
# Tests sólo de este paquete
uv run --package iol-client pytest packages/iol-client

# Lint
uv run ruff check packages/iol-client

# Type checking
uv run mypy packages/iol-client
```
