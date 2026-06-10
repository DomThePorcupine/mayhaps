from typing import Callable, cast

from .result import Err, HttpErr, MayhapsError, Ok


class Pipeline[T]:
    def __init__(self, value: T) -> None:
        self._state: Ok[T] | Err = Ok(value)

    def _make_error(self, err: Err) -> Exception:
        status = err.status if isinstance(err, HttpErr) else None
        return MayhapsError(err.detail, status=status)

    def then[U](self, fn: Callable[[T], Ok[U] | Err]) -> "Pipeline[U]":
        if isinstance(self._state, Err):
            return cast("Pipeline[U]", self)
        result = fn(self._state.value)
        p: Pipeline[U] = object.__new__(type(self))
        p._state = result
        return p

    def run(self) -> T:
        if isinstance(self._state, Err):
            raise self._make_error(self._state)
        return self._state.value
