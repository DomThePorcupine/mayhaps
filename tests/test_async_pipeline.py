"""Tests for AsyncPipeline[T]."""

import asyncio

import pytest

from mayhaps import AsyncPipeline, Err, HttpErr, MayhapsError, Ok


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def adouble(x: int) -> Ok[int]:
    return Ok(x * 2)


async def aadd_one(x: int) -> Ok[int]:
    return Ok(x + 1)


async def aalways_err(x: int) -> Err:
    return Err("async error")


# ---------------------------------------------------------------------------
# Sync steps work (same behaviour as Pipeline)
# ---------------------------------------------------------------------------

def test_sync_steps_thread_ok_values() -> None:
    def double(x: int) -> Ok[int]: return Ok(x * 2)
    def add_one(x: int) -> Ok[int]: return Ok(x + 1)

    result = asyncio.run(AsyncPipeline(3).then(double).then(add_one).run())
    assert result == 7


def test_no_steps() -> None:
    assert asyncio.run(AsyncPipeline(42).run()) == 42


def test_sync_err_raises_mayhaps_error() -> None:
    def always_err(x: int) -> Err: return Err("oops")

    with pytest.raises(MayhapsError) as exc_info:
        asyncio.run(AsyncPipeline(1).then(always_err).run())

    assert exc_info.value.detail == "oops"
    assert exc_info.value.status is None


def test_sync_http_err_preserves_status() -> None:
    def always_err(x: int) -> HttpErr: return HttpErr("not found", status=404)

    with pytest.raises(MayhapsError) as exc_info:
        asyncio.run(AsyncPipeline(1).then(always_err).run())

    assert exc_info.value.detail == "not found"
    assert exc_info.value.status == 404


def test_sync_short_circuit_on_err() -> None:
    called: list[str] = []

    def first(x: int) -> Ok[int] | Err:
        called.append("first")
        return Err("stop")

    def second(x: int) -> Ok[int]:
        called.append("second")
        return Ok(x)

    with pytest.raises(MayhapsError):
        asyncio.run(AsyncPipeline(1).then(first).then(second).run())

    assert called == ["first"]


# ---------------------------------------------------------------------------
# Async steps
# ---------------------------------------------------------------------------

def test_async_steps_thread_ok_values() -> None:
    result = asyncio.run(AsyncPipeline(3).then(adouble).then(aadd_one).run())
    assert result == 7


def test_async_err_raises_mayhaps_error() -> None:
    with pytest.raises(MayhapsError) as exc_info:
        asyncio.run(AsyncPipeline(1).then(aalways_err).run())

    assert exc_info.value.detail == "async error"


def test_async_short_circuit_on_err() -> None:
    called: list[str] = []

    async def first(x: int) -> Ok[int] | Err:
        called.append("first")
        return Err("stop")

    async def second(x: int) -> Ok[int]:
        called.append("second")
        return Ok(x)

    with pytest.raises(MayhapsError):
        asyncio.run(AsyncPipeline(1).then(first).then(second).run())

    assert called == ["first"]


# ---------------------------------------------------------------------------
# Mixed sync + async steps
# ---------------------------------------------------------------------------

def test_mixed_sync_async_steps() -> None:
    def sync_double(x: int) -> Ok[int]: return Ok(x * 2)

    async def async_add_one(x: int) -> Ok[int]: return Ok(x + 1)

    def sync_to_str(x: int) -> Ok[str]: return Ok(str(x))

    result = asyncio.run(
        AsyncPipeline(3)
        .then(sync_double)       # sync  → 6
        .then(async_add_one)     # async → 7
        .then(sync_to_str)       # sync  → "7"
        .run()
    )
    assert result == "7"


def test_mixed_short_circuit_at_async_step() -> None:
    called: list[str] = []

    def sync_ok(x: int) -> Ok[int]:
        called.append("sync")
        return Ok(x)

    async def async_err(x: int) -> Err:
        called.append("async")
        return Err("async stop")

    def sync_after(x: int) -> Ok[int]:
        called.append("after")
        return Ok(x)

    with pytest.raises(MayhapsError):
        asyncio.run(AsyncPipeline(1).then(sync_ok).then(async_err).then(sync_after).run())

    assert called == ["sync", "async"]


# ---------------------------------------------------------------------------
# require guard
# ---------------------------------------------------------------------------

def test_require_passes_when_predicate_holds() -> None:
    result = asyncio.run(
        AsyncPipeline(4).require(lambda x: x % 2 == 0, Err("must be even")).run()
    )
    assert result == 4


def test_require_short_circuits_when_predicate_fails() -> None:
    with pytest.raises(MayhapsError) as exc_info:
        asyncio.run(
            AsyncPipeline(3).require(lambda x: x % 2 == 0, Err("must be even")).run()
        )
    assert exc_info.value.detail == "must be even"


def test_require_skips_on_prior_err() -> None:
    called = False

    def always_err(x: int) -> Err: return Err("stop")

    def predicate(x: int) -> bool:
        nonlocal called
        called = True
        return True

    with pytest.raises(MayhapsError):
        asyncio.run(AsyncPipeline(1).then(always_err).require(predicate, Err("never")).run())

    assert not called


def test_require_after_async_step() -> None:
    async def fetch(x: int) -> Ok[int]: return Ok(x + 10)

    result = asyncio.run(
        AsyncPipeline(5).then(fetch).require(lambda x: x > 10, Err("too small")).run()
    )
    assert result == 15


# ---------------------------------------------------------------------------
# tap (sync and async)
# ---------------------------------------------------------------------------

def test_sync_tap_runs_side_effect() -> None:
    seen: list[int] = []
    result = asyncio.run(AsyncPipeline(42).tap(seen.append).run())
    assert result == 42
    assert seen == [42]


def test_async_tap_runs_side_effect() -> None:
    seen: list[int] = []

    async def record(x: int) -> None:
        seen.append(x)

    result = asyncio.run(AsyncPipeline(42).tap(record).run())
    assert result == 42
    assert seen == [42]


def test_tap_skips_on_err() -> None:
    called = False

    def always_err(x: int) -> Err: return Err("stop")

    def side_effect(x: int) -> None:
        nonlocal called
        called = True

    with pytest.raises(MayhapsError):
        asyncio.run(AsyncPipeline(1).then(always_err).tap(side_effect).run())

    assert not called


def test_async_tap_skips_on_err() -> None:
    called = False

    def always_err(x: int) -> Err: return Err("stop")

    async def async_side_effect(x: int) -> None:
        nonlocal called
        called = True

    with pytest.raises(MayhapsError):
        asyncio.run(AsyncPipeline(1).then(always_err).tap(async_side_effect).run())

    assert not called


def test_tap_does_not_change_value() -> None:
    seen: list[int] = []

    async def double(x: int) -> Ok[int]: return Ok(x * 2)

    result = asyncio.run(
        AsyncPipeline(5).then(double).tap(seen.append).map(str).run()
    )
    assert result == "10"
    assert seen == [10]


# ---------------------------------------------------------------------------
# map
# ---------------------------------------------------------------------------

def test_map_transforms_value() -> None:
    assert asyncio.run(AsyncPipeline(21).map(lambda x: x * 2).run()) == 42


def test_map_changes_type() -> None:
    assert asyncio.run(AsyncPipeline(42).map(str).run()) == "42"


def test_map_skips_on_err() -> None:
    called = False

    def always_err(x: int) -> Err: return Err("stop")

    def transform(x: int) -> str:
        nonlocal called
        called = True
        return str(x)

    with pytest.raises(MayhapsError):
        asyncio.run(AsyncPipeline(1).then(always_err).map(transform).run())

    assert not called


def test_map_chains_with_async_then() -> None:
    async def double(x: int) -> Ok[int]: return Ok(x * 2)

    result = asyncio.run(AsyncPipeline(3).then(double).map(str).run())
    assert result == "6"


# ---------------------------------------------------------------------------
# result() method
# ---------------------------------------------------------------------------

def test_result_raises_before_run() -> None:
    p = AsyncPipeline(42)
    with pytest.raises(RuntimeError, match="run\\(\\)"):
        p.result()


def test_result_returns_ok_after_successful_run() -> None:
    async def go() -> Ok[int] | Err:
        p = AsyncPipeline(42)
        await p.run()
        return p.result()

    assert asyncio.run(go()) == Ok(42)


def test_result_returns_err_after_failed_run() -> None:
    def always_err(x: int) -> Err: return Err("failure")

    async def go() -> Ok[int] | Err:
        p = AsyncPipeline(1).then(always_err)
        try:
            await p.run()
        except MayhapsError:
            pass
        return p.result()

    assert asyncio.run(go()) == Err("failure")


# ---------------------------------------------------------------------------
# Type-changing chains
# ---------------------------------------------------------------------------

def test_chain_changes_type_through_async_steps() -> None:
    async def to_str(x: int) -> Ok[str]: return Ok(str(x))
    async def append_bang(x: str) -> Ok[str]: return Ok(x + "!")

    result = asyncio.run(AsyncPipeline(42).then(to_str).then(append_bang).run())
    assert result == "42!"


def test_error_message_matches_exception_str() -> None:
    def always_err(x: int) -> Err: return Err("oops")

    with pytest.raises(MayhapsError) as exc_info:
        asyncio.run(AsyncPipeline(1).then(always_err).run())

    assert str(exc_info.value) == "oops"
