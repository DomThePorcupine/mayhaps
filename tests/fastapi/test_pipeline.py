import pytest
from fastapi import HTTPException

from mayhaps.fastapi import Err, Ok, Pipeline


def test_pipeline_threads_ok_values() -> None:
    def double(x: int) -> Ok[int]: return Ok(x * 2)
    def add_one(x: int) -> Ok[int]: return Ok(x + 1)

    assert Pipeline(3).then(double).then(add_one).run() == 7


def test_pipeline_no_steps() -> None:
    assert Pipeline(42).run() == 42


def test_pipeline_raises_on_err() -> None:
    def always_err(x: int) -> Err: return Err(404, "not found")

    with pytest.raises(HTTPException) as exc_info:
        Pipeline(1).then(always_err).run()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "not found"


def test_pipeline_short_circuits_on_first_err() -> None:
    called: list[str] = []

    def first(x: int) -> Ok[int] | Err:
        called.append("first")
        return Err(403, "forbidden")

    def second(x: int) -> Ok[int]:
        called.append("second")
        return Ok(x)

    with pytest.raises(HTTPException):
        Pipeline(1).then(first).then(second).run()

    assert called == ["first"]


def test_pipeline_raises_correct_status_from_each_step() -> None:
    def fetch(x: int) -> Ok[int]: return Ok(x)
    def check(x: int) -> Err: return Err(422, "unprocessable")

    with pytest.raises(HTTPException) as exc_info:
        Pipeline(1).then(fetch).then(check).run()

    assert exc_info.value.status_code == 422


def test_pipeline_threads_different_types() -> None:
    def to_str(x: int) -> Ok[str]: return Ok(str(x))
    def append_bang(x: str) -> Ok[str]: return Ok(x + "!")

    assert Pipeline(42).then(to_str).then(append_bang).run() == "42!"
