import pytest
from mayhaps import compose, ok_or, require_field, when
from mayhaps.fastapi import HttpErr, HttpPipeline
from mayhaps.result import DbErr, DbErrKind


def test_when_passes():
    assert compose(4, when(lambda n: n % 2 == 0)) == 4


def test_when_rejects():
    assert compose(3, when(lambda n: n % 2 == 0)) is None


def test_when_with_named_predicate():
    def is_weekday(day: str) -> bool:
        return day in {"Mon", "Tue", "Wed", "Thu", "Fri"}

    assert compose("Mon", when(is_weekday)) == "Mon"
    assert compose("Sat", when(is_weekday)) is None


def test_when_none_input():
    assert compose(None, when(lambda n: True)) is None


class _Order:
    def __init__(self, path: str | None) -> None:
        self.path = path


def test_require_field_present():
    order = _Order(path="s3/key/doc.pdf")
    result = HttpPipeline(order).then(require_field(lambda o: o.path, HttpErr("not found", status=404))).run()
    assert result == "s3/key/doc.pdf"


def test_require_field_none_raises():
    from fastapi import HTTPException
    order = _Order(path=None)
    with pytest.raises(HTTPException) as exc_info:
        HttpPipeline(order).then(require_field(lambda o: o.path, HttpErr("not found", status=404))).run()
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "not found"


def test_require_field_with_db_err():
    from mayhaps.result import Ok

    def get_path(o: _Order) -> str | None:
        return o.path

    order = _Order(path=None)
    err = DbErr("missing", kind=DbErrKind.NOT_FOUND)
    step = require_field(get_path, err)
    assert step(order) == err


def test_require_field_passes_through_value():
    from mayhaps.result import Ok

    def get_path(o: _Order) -> str | None:
        return o.path

    order = _Order(path="some/path")
    step = require_field(get_path, DbErr("missing", kind=DbErrKind.NOT_FOUND))
    assert step(order) == Ok("some/path")


def test_ok_or_with_value():
    from mayhaps.result import Ok
    assert ok_or("hello", DbErr("missing", kind=DbErrKind.NOT_FOUND)) == Ok("hello")


def test_ok_or_with_none():
    err = DbErr("missing", kind=DbErrKind.NOT_FOUND)
    assert ok_or(None, err) == err


def test_ok_or_in_pipeline():
    from mayhaps.result import Ok

    data: dict[str, str] = {"a": "found"}
    result = (
        HttpPipeline("a")
        .then(lambda k: ok_or(data.get(k), HttpErr("not found", status=404)))
        .run()
    )
    assert result == "found"


def test_ok_or_in_pipeline_miss():
    from fastapi import HTTPException

    data: dict[str, str] = {}
    with pytest.raises(HTTPException) as exc_info:
        (
            HttpPipeline("a")
            .then(lambda k: ok_or(data.get(k), HttpErr("not found", status=404)))
            .run()
        )
    assert exc_info.value.status_code == 404
