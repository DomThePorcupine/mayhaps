import re
from typing import Callable


def non_empty(value: str) -> str | None:
    return value if value.strip() else None


def strip(value: str) -> str | None:
    stripped = value.strip()
    return stripped if stripped else None


def matches(pattern: str | re.Pattern[str]) -> Callable[[str], str | None]:
    compiled = re.compile(pattern) if isinstance(pattern, str) else pattern

    def _matches(value: str) -> str | None:
        return value if compiled.fullmatch(value) else None

    return _matches
