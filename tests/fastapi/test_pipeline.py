import pytest
from fastapi import HTTPException

from mayhaps.fastapi import HttpErr, HttpPipeline, Ok


def test_pipeline_threads_ok_values() -> None:
    def double(x: int) -> Ok[int]: return Ok(x * 2)
    def add_one(x: int) -> Ok[int]: return Ok(x + 1)

    assert HttpPipeline(3).then(double).then(add_one).run() == 7


def test_pipeline_no_steps() -> None:
    assert HttpPipeline(42).run() == 42


def test_pipeline_raises_http_exception_on_http_err() -> None:
    def always_err(x: int) -> HttpErr: return HttpErr("not found", status=404)

    with pytest.raises(HTTPException) as exc_info:
        HttpPipeline(1).then(always_err).run()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "not found"


def test_pipeline_raises_500_on_plain_err() -> None:
    from mayhaps.result import Err

    def always_err(x: int) -> Err: return Err("something went wrong")

    with pytest.raises(HTTPException) as exc_info:
        HttpPipeline(1).then(always_err).run()

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "something went wrong"


def test_pipeline_short_circuits_on_first_err() -> None:
    called: list[str] = []

    def first(x: int) -> Ok[int] | HttpErr:
        called.append("first")
        return HttpErr("forbidden", status=403)

    def second(x: int) -> Ok[int]:
        called.append("second")
        return Ok(x)

    with pytest.raises(HTTPException):
        HttpPipeline(1).then(first).then(second).run()

    assert called == ["first"]


def test_pipeline_raises_correct_status_from_each_step() -> None:
    def fetch(x: int) -> Ok[int]: return Ok(x)
    def check(x: int) -> HttpErr: return HttpErr("unprocessable", status=422)

    with pytest.raises(HTTPException) as exc_info:
        HttpPipeline(1).then(fetch).then(check).run()

    assert exc_info.value.status_code == 422


def test_pipeline_converts_db_err_using_status_map() -> None:
    from mayhaps.result import DbErr, DbErrKind

    cases = [
        (DbErrKind.NOT_FOUND, 404),
        (DbErrKind.CONFLICT, 409),
        (DbErrKind.PERMISSION_DENIED, 403),
        (DbErrKind.INVALID, 422),
    ]
    for kind, expected_status in cases:
        def step(x: int, k: DbErrKind = kind) -> DbErr:
            return DbErr("oops", kind=k)

        with pytest.raises(HTTPException) as exc_info:
            HttpPipeline(1).then(step).run()

        assert exc_info.value.status_code == expected_status


def test_require_plain_string_raises_400() -> None:
    with pytest.raises(HTTPException) as exc_info:
        HttpPipeline(0).require(lambda x: x > 0, "must be positive").run()
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "must be positive"


def test_require_http_err_uses_provided_status() -> None:
    with pytest.raises(HTTPException) as exc_info:
        HttpPipeline(0).require(lambda x: x > 0, HttpErr("forbidden", status=403)).run()
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


def test_require_passes_through_when_predicate_holds() -> None:
    result = HttpPipeline(5).require(lambda x: x > 0, "must be positive").run()
    assert result == 5


def test_pipeline_threads_different_types() -> None:
    def to_str(x: int) -> Ok[str]: return Ok(str(x))
    def append_bang(x: str) -> Ok[str]: return Ok(x + "!")

    assert HttpPipeline(42).then(to_str).then(append_bang).run() == "42!"


def test_ok_or_unwraps_non_none_value() -> None:
    assert HttpPipeline("hello").ok_or(HttpErr("missing", status=400)).run() == "hello"


def test_ok_or_raises_http_exception_on_none() -> None:
    with pytest.raises(HTTPException) as exc_info:
        HttpPipeline(None).ok_or(HttpErr("missing", status=400)).run()
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "missing"


def test_ok_or_preserves_pipeline_type_for_chaining() -> None:
    def append_bang(x: str) -> Ok[str]: return Ok(x + "!")

    result = HttpPipeline("hi").ok_or(HttpErr("missing", status=400)).then(append_bang).run()
    assert result == "hi!"
