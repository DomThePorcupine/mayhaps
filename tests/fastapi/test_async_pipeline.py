"""Tests for AsyncHttpPipeline[T]."""

import asyncio

import pytest
from fastapi import HTTPException

from mayhaps.fastapi import AsyncHttpPipeline, HttpErr, Ok
from mayhaps.result import DbErr, DbErrKind, Err


# ---------------------------------------------------------------------------
# Basic success path
# ---------------------------------------------------------------------------

def test_threads_ok_values() -> None:
    async def double(x: int) -> Ok[int]: return Ok(x * 2)
    async def add_one(x: int) -> Ok[int]: return Ok(x + 1)

    result = asyncio.run(AsyncHttpPipeline(3).then(double).then(add_one).run())
    assert result == 7


def test_no_steps() -> None:
    assert asyncio.run(AsyncHttpPipeline(42).run()) == 42


# ---------------------------------------------------------------------------
# Error mapping → HTTPException
# ---------------------------------------------------------------------------

def test_raises_http_exception_on_http_err() -> None:
    def always_err(x: int) -> HttpErr: return HttpErr("not found", status=404)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(AsyncHttpPipeline(1).then(always_err).run())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "not found"


def test_raises_500_on_plain_err() -> None:
    def always_err(x: int) -> Err: return Err("something went wrong")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(AsyncHttpPipeline(1).then(always_err).run())

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "something went wrong"


def test_async_step_raises_http_exception() -> None:
    async def always_err(x: int) -> HttpErr: return HttpErr("forbidden", status=403)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(AsyncHttpPipeline(1).then(always_err).run())

    assert exc_info.value.status_code == 403


def test_converts_db_err_using_status_map() -> None:
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
            asyncio.run(AsyncHttpPipeline(1).then(step).run())

        assert exc_info.value.status_code == expected_status


# ---------------------------------------------------------------------------
# Short-circuit behaviour
# ---------------------------------------------------------------------------

def test_short_circuits_on_first_err() -> None:
    called: list[str] = []

    async def first(x: int) -> Ok[int] | HttpErr:
        called.append("first")
        return HttpErr("forbidden", status=403)

    async def second(x: int) -> Ok[int]:
        called.append("second")
        return Ok(x)

    with pytest.raises(HTTPException):
        asyncio.run(AsyncHttpPipeline(1).then(first).then(second).run())

    assert called == ["first"]


# ---------------------------------------------------------------------------
# require
# ---------------------------------------------------------------------------

def test_require_plain_string_raises_400() -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(AsyncHttpPipeline(0).require(lambda x: x > 0, "must be positive").run())
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "must be positive"


def test_require_http_err_uses_provided_status() -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            AsyncHttpPipeline(0)
            .require(lambda x: x > 0, HttpErr("forbidden", status=403))
            .run()
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


def test_require_passes_through_when_predicate_holds() -> None:
    result = asyncio.run(
        AsyncHttpPipeline(5).require(lambda x: x > 0, "must be positive").run()
    )
    assert result == 5


def test_require_after_async_step_raises_400() -> None:
    async def fetch(x: int) -> Ok[int]: return Ok(x - 10)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            AsyncHttpPipeline(5)
            .then(fetch)                             # → Ok(-5)
            .require(lambda x: x > 0, "negative")   # fails → 400
            .run()
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "negative"


# ---------------------------------------------------------------------------
# tap and map
# ---------------------------------------------------------------------------

def test_async_tap_runs_and_passes_through() -> None:
    seen: list[int] = []

    async def record(x: int) -> None:
        seen.append(x)

    result = asyncio.run(AsyncHttpPipeline(42).tap(record).run())
    assert result == 42
    assert seen == [42]


def test_map_transforms_value() -> None:
    result = asyncio.run(AsyncHttpPipeline(21).map(lambda x: x * 2).run())
    assert result == 42


def test_mixed_sync_async_chain() -> None:
    def sync_double(x: int) -> Ok[int]: return Ok(x * 2)

    async def async_str(x: int) -> Ok[str]: return Ok(str(x))

    result = asyncio.run(
        AsyncHttpPipeline(5)
        .then(sync_double)   # → 10
        .then(async_str)     # → "10"
        .map(lambda s: s + "!")
        .run()
    )
    assert result == "10!"


# ---------------------------------------------------------------------------
# Type annotation: confirm return type is AsyncHttpPipeline (cast check)
# ---------------------------------------------------------------------------

def test_then_returns_async_http_pipeline_type() -> None:
    async def step(x: int) -> Ok[int]: return Ok(x)

    p = AsyncHttpPipeline(1).then(step)
    assert isinstance(p, AsyncHttpPipeline)


def test_tap_returns_async_http_pipeline_type() -> None:
    p = AsyncHttpPipeline(1).tap(lambda x: None)
    assert isinstance(p, AsyncHttpPipeline)


def test_map_returns_async_http_pipeline_type() -> None:
    p = AsyncHttpPipeline(1).map(str)
    assert isinstance(p, AsyncHttpPipeline)
