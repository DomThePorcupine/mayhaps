from typing import Callable


def positive(value: int | float) -> int | float | None:
    return value if value > 0 else None


def non_negative(value: int | float) -> int | float | None:
    return value if value >= 0 else None


def clamp(minimum: int | float, maximum: int | float) -> Callable[[int | float], int | float | None]:
    def _clamp(value: int | float) -> int | float | None:
        return value if minimum <= value <= maximum else None
    return _clamp
