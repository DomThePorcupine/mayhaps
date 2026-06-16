from datetime import datetime as _datetime
from typing import Callable


def parse_date(fmt: str) -> Callable[[str], _datetime | None]:
    """Return a step that parses a string into a datetime using *fmt*.

    Returns ``None`` if the string does not match the format.

    Example::

        compose("2024-01-15", parse_date("%Y-%m-%d"))
        # → datetime(2024, 1, 15, 0, 0)
    """

    def _parse(value: str) -> _datetime | None:
        try:
            return _datetime.strptime(value, fmt)
        except ValueError:
            return None

    return _parse


def future(value: _datetime) -> _datetime | None:
    """Pass through *value* if it is strictly in the future, else ``None``."""
    return value if value > _datetime.now() else None


def past(value: _datetime) -> _datetime | None:
    """Pass through *value* if it is strictly in the past, else ``None``."""
    return value if value < _datetime.now() else None


def in_range(start: _datetime, end: _datetime) -> Callable[[_datetime], _datetime | None]:
    """Return a step that passes through *value* if ``start <= value <= end``.

    Example::

        compose(dt, in_range(start_dt, end_dt))
    """

    def _in_range(value: _datetime) -> _datetime | None:
        return value if start <= value <= end else None

    return _in_range
