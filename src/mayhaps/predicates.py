from typing import Callable, TypeVar

from .result import Err, Ok

T = TypeVar("T")


def when(predicate: Callable[[T], bool]) -> Callable[[T], T | None]:
    def _when(value: T) -> T | None:
        return value if predicate(value) else None
    return _when


def require_field[M, V, E: Err](
    getter: Callable[[M], V | None],
    err: E,
) -> Callable[[M], Ok[V] | E]:
    def step(value: M) -> Ok[V] | E:
        field = getter(value)
        return Ok(field) if field is not None else err
    return step


def ok_or[T, E: Err](value: T | None, err: E) -> Ok[T] | E:
    return Ok(value) if value is not None else err
