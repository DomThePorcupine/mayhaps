import os
from typing import Any, Callable


def get(name: str) -> Callable[[Any], str | None]:
    """Step factory: read a single env var, ignoring the pipeline input.

    Returns the variable's value if set and non-empty, else None.
    """
    def step(_: Any) -> str | None:
        value = os.environ.get(name)
        return value if value else None
    return step


def load(*names: str) -> Callable[[Any], dict[str, str] | None]:
    """Step factory: read multiple env vars at once, ignoring the pipeline input.

    Returns a dict mapping each name to its value if all are set and non-empty,
    else None.
    """
    def step(_: Any) -> dict[str, str] | None:
        result: dict[str, str] = {}
        for name in names:
            value = os.environ.get(name)
            if not value:
                return None
            result[name] = value
        return result
    return step
