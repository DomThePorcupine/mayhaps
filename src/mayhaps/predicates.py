from typing import Callable, TypeVar

from .result import Err, Ok

T = TypeVar("T")


def when(predicate: Callable[[T], bool]) -> Callable[[T], T | None]:
    def _when(value: T) -> T | None:
        return value if predicate(value) else None
    return _when


def require_field[M, V](
    getter: Callable[[M], V | None],
    err: Err,
) -> Callable[[M], Ok[V] | Err]:
    def step(value: M) -> Ok[V] | Err:
        field = getter(value)
        return Ok(field) if field is not None else err
    return step


def ok_or[T](value: T | None, err: Err) -> Ok[T] | Err:
    return Ok(value) if value is not None else err
