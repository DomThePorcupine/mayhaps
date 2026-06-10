import pytest

from mayhaps import Err, HttpErr, MayhapsError, Ok, Pipeline


def test_pipeline_threads_ok_values() -> None:
    def double(x: int) -> Ok[int]: return Ok(x * 2)
    def add_one(x: int) -> Ok[int]: return Ok(x + 1)

    assert Pipeline(3).then(double).then(add_one).run() == 7


def test_pipeline_no_steps() -> None:
    assert Pipeline(42).run() == 42


def test_pipeline_raises_mayhaps_error_on_err() -> None:
    def always_err(x: int) -> Err: return Err("something went wrong")

    with pytest.raises(MayhapsError) as exc_info:
        Pipeline(1).then(always_err).run()

    assert exc_info.value.detail == "something went wrong"
    assert exc_info.value.status is None


def test_pipeline_preserves_status_from_http_err() -> None:
    def always_err(x: int) -> HttpErr: return HttpErr("not found", status=404)

    with pytest.raises(MayhapsError) as exc_info:
        Pipeline(1).then(always_err).run()

    assert exc_info.value.detail == "not found"
    assert exc_info.value.status == 404


def test_pipeline_short_circuits_on_first_err() -> None:
    called: list[str] = []

    def first(x: int) -> Ok[int] | Err:
        called.append("first")
        return Err("stop")

    def second(x: int) -> Ok[int]:
        called.append("second")
        return Ok(x)

    with pytest.raises(MayhapsError):
        Pipeline(1).then(first).then(second).run()

    assert called == ["first"]


def test_pipeline_threads_different_types() -> None:
    def to_str(x: int) -> Ok[str]: return Ok(str(x))
    def append_bang(x: str) -> Ok[str]: return Ok(x + "!")

    assert Pipeline(42).then(to_str).then(append_bang).run() == "42!"


def test_map_transforms_value() -> None:
    assert Pipeline(21).map(lambda x: x * 2).run() == 42


def test_map_changes_type() -> None:
    assert Pipeline(42).map(str).run() == "42"


def test_map_skips_on_err() -> None:
    called = False

    def always_err(x: int) -> Err: return Err("stop")
    def side_effect(x: int) -> str:
        nonlocal called
        called = True
        return str(x)

    with pytest.raises(MayhapsError):
        Pipeline(1).then(always_err).map(side_effect).run()

    assert not called


def test_map_chains_with_then() -> None:
    def double(x: int) -> Ok[int]: return Ok(x * 2)

    assert Pipeline(3).then(double).map(str).run() == "6"


def test_tap_runs_side_effect() -> None:
    seen: list[int] = []
    assert Pipeline(42).tap(seen.append).run() == 42
    assert seen == [42]


def test_tap_skips_on_err() -> None:
    called = False

    def always_err(x: int) -> Err: return Err("stop")
    def side_effect(x: int) -> None:
        nonlocal called
        called = True

    with pytest.raises(MayhapsError):
        Pipeline(1).then(always_err).tap(side_effect).run()

    assert not called


def test_tap_chains_with_then_and_map() -> None:
    seen: list[int] = []

    def double(x: int) -> Ok[int]: return Ok(x * 2)

    assert Pipeline(3).then(double).tap(seen.append).map(str).run() == "6"
    assert seen == [6]


def test_pipeline_error_message_matches_exception_str() -> None:
    def always_err(x: int) -> Err: return Err("oops")

    with pytest.raises(MayhapsError) as exc_info:
        Pipeline(1).then(always_err).run()

    assert str(exc_info.value) == "oops"
