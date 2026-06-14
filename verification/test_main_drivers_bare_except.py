"""CR-06 -- main_*.py drivers MUST NOT use bare ``except:`` or ``except Exception:``.

Bare exception handlers swallow KeyboardInterrupt-adjacent failures (well,
``except Exception`` no, pero ``except:`` si) y -- mas importante en el harness
de verificacion -- hide the root cause of WHY un probe fallo. Cuando el
``append_finding(..., title=f"... unexpected {type(exc).__name__}", ...)`` es
el unico signal disponible, narrowing al tipo especifico (httpx.HTTPError,
PrimaryAPIError, HigyrusAPIError, etc.) garantiza que la diagnostica refleje
la categoria real del fallo en vez de un blanket ``Exception``.

Scope: ``main_matriz.py`` y ``main_higyrus.py`` (los 2 drivers con mas probes
y los 2 citados explicitamente en el code-review concerns CR-06). Los otros 2
drivers (``main_iol.py``, ``main_ambito_financiero.py``) NO estan en scope
de CR-06 en Phase 11 y se cubriran en v1.2 si surge un concern equivalente.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVERS = ["main_matriz.py", "main_higyrus.py"]


@pytest.mark.parametrize("driver", _DRIVERS)
def test_no_bare_except_in_driver(driver: str) -> None:
    """AST walk: cero ``except:`` bare AND cero ``except Exception:`` bare.

    Permite ``except (A, B):`` tuples, ``except A:`` con A != Exception, y
    ``except Exception as exc:`` SOLO si esta inmediatamente seguido por
    ``raise`` (re-raise legitimate) -- pero por simplicidad y consistencia
    con el contrato CR-06, rechazamos TODOS los ``except Exception`` en estos
    drivers (la unica excepcion legitima seria un ``re-raise``, y no usamos
    ese patron en main_*.py).
    """
    tree = ast.parse((_REPO_ROOT / driver).read_text(encoding="utf-8"))
    bare_sites: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            # ``except:`` bare -- siempre prohibido (captura SystemExit + KeyboardInterrupt).
            bare_sites.append((node.lineno, "<bare except:>"))
            continue
        if isinstance(node.type, ast.Name) and node.type.id == "Exception":
            # ``except Exception:`` o ``except Exception as exc:``.
            bare_sites.append((node.lineno, "except Exception"))
    assert not bare_sites, (
        f"{driver} has {len(bare_sites)} bare-except site(s): {bare_sites}"
    )
