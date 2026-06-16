from typing import Callable, TypeVar, cast, overload

from .result import DbErr, Err, HttpErr, MayhapsError, Ok

_V = TypeVar("_V")


class Pipeline[T]:
    def __init__(self, value: T) -> None:
        self._state: Ok[T] | Err = Ok(value)

    def _make_error(self, err: Err) -> Exception:
        status = err.status if isinstance(err, HttpErr) else None
        kind = err.kind if isinstance(err, DbErr) else None
        return MayhapsError(err.detail, status=status, kind=kind)

    def then[U](self, fn: Callable[[T], Ok[U] | Err]) -> "Pipeline[U]":
        if isinstance(self._state, Err):
            return cast("Pipeline[U]", self)
        result = fn(self._state.value)
        p: Pipeline[U] = object.__new__(type(self))  # pyright: ignore[reportAssignmentType]
        p._state = result
        return p

    def require(self, predicate: Callable[[T], bool], err: Err) -> "Pipeline[T]":
        if isinstance(self._state, Err):
            return self
        p: Pipeline[T] = object.__new__(type(self))  # pyright: ignore[reportAssignmentType]
        p._state = self._state if predicate(self._state.value) else err
        return p

    def tap(self, fn: Callable[[T], None]) -> "Pipeline[T]":
        if isinstance(self._state, Err):
            return self
        fn(self._state.value)
        return self

    def map[U](self, fn: Callable[[T], U]) -> "Pipeline[U]":
        if isinstance(self._state, Err):
            return cast("Pipeline[U]", self)
        p: Pipeline[U] = object.__new__(type(self))  # pyright: ignore[reportAssignmentType]
        p._state = Ok(fn(self._state.value))
        return p

    @overload
    def ok_or(self: "Pipeline[_V | None]", err: Err) -> "Pipeline[_V]": ...
    @overload
    def ok_or(self: "Pipeline[_V]", err: Err) -> "Pipeline[_V]": ...
    def ok_or(self, err: Err) -> "Pipeline":
        """Unwrap T | None → T, short-circuiting with err if the value is None."""
        if isinstance(self._state, Err):
            return cast("Pipeline", self)
        p: Pipeline = object.__new__(type(self))
        p._state = Ok(self._state.value) if self._state.value is not None else err
        return p

    def result(self) -> Ok[T] | Err:
        return self._state

    def run(self) -> T:
        if isinstance(self._state, Err):
            raise self._make_error(self._state)
        return self._state.value
