from typing import Callable, TypeVar

T = TypeVar("T")


def first(value: list[T]) -> T | None:
    return value[0] if value else None


def find(predicate: Callable[[T], bool]) -> Callable[[list[T]], T | None]:
    def _find(value: list[T]) -> T | None:
        return next((item for item in value if predicate(item)), None)

    return _find


def non_empty(value: list[T]) -> list[T] | None:
    return value if value else None
