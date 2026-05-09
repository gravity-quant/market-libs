# wallets-client

Cliente HTTP (sync y async) para la API de [Wallets](https://example.com/).

## Instalación

```bash
uv add wallets-client
# o, dentro del workspace:
uv sync
```

## Uso

### Sync

```python
from wallets_client import WalletsClient

with WalletsClient(token="...") as client:
    portfolio = client.get_portfolio()
```

### Async

```python
from wallets_client import AsyncWalletsClient

async with AsyncWalletsClient(token="...") as client:
    portfolio = await client.get_portfolio()
```

## Desarrollo

```bash
# Tests sólo de este paquete
uv run --package wallets-client pytest packages/wallets-client

# Lint
uv run ruff check packages/wallets-client

# Type checking
uv run mypy packages/wallets-client
```
