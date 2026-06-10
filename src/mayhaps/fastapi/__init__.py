from dataclasses import dataclass
from typing import Callable, cast

from fastapi import HTTPException


@dataclass
class Ok[T]:
    value: T


@dataclass
class Err:
    status: int
    detail: str


class Pipeline[T]:
    def __init__(self, value: T) -> None:
        self._state: Ok[T] | Err = Ok(value)

    def then[U](self, fn: Callable[[T], Ok[U] | Err]) -> "Pipeline[U]":
        if isinstance(self._state, Err):
            return cast("Pipeline[U]", self)
        result = fn(self._state.value)
        p: Pipeline[U] = object.__new__(Pipeline)
        p._state = result
        return p

    def run(self) -> T:
        if isinstance(self._state, Err):
            raise HTTPException(status_code=self._state.status, detail=self._state.detail)
        return self._state.value
