from typing import Callable, TypeVar

T = TypeVar("T")


def when(predicate: Callable[[T], bool]) -> Callable[[T], T | None]:
    def _when(value: T) -> T | None:
        return value if predicate(value) else None
    return _when
