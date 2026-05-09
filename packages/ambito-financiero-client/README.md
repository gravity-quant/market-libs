# ambito-financiero-client

Cliente HTTP (sync y async) para la API de [Ámbito Financiero](https://example.com/).

## Instalación

```bash
uv add ambito-financiero-client
# o, dentro del workspace:
uv sync
```

## Uso

### Sync

```python
from ambito_financiero_client import AmbitoFinancieroClient

with AmbitoFinancieroClient(token="...") as client:
    portfolio = client.get_portfolio()
```

### Async

```python
from ambito_financiero_client import AsyncAmbitoFinancieroClient

async with AsyncAmbitoFinancieroClient(token="...") as client:
    portfolio = await client.get_portfolio()
```

## Desarrollo

```bash
# Tests sólo de este paquete
uv run --package ambito-financiero-client pytest packages/ambito-financiero-client

# Lint
uv run ruff check packages/ambito-financiero-client

# Type checking
uv run mypy packages/ambito-financiero-client
```
