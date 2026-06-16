import inspect
from typing import Any, Awaitable, Callable, cast

from .result import DbErr, Err, HttpErr, MayhapsError, Ok

_UNSET = object()


class AsyncPipeline[T]:
    """Pipeline with async/await support.

    Steps are collected lazily and executed when ``await pipeline.run()`` is called.
    Each step may be sync or async — both are accepted by `then`, `tap`, and `map`.

    Example::

        result = await (
            AsyncPipeline(user_id)
            .then(fetch_user)          # async Ok[User] | Err
            .require(lambda u: u.is_active, Err("inactive"))
            .tap(notify)               # async side-effect
            .map(lambda u: u.name)
        ).run()
    """

    def __init__(self, value: T) -> None:
        self._initial: T = value
        self._steps: list[tuple[str, Any]] = []
        self._executed: bool = False
        self._state: Ok[Any] | Err = Ok(value)  # populated after run()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_error(self, err: Err) -> Exception:
        status = err.status if isinstance(err, HttpErr) else None
        kind = err.kind if isinstance(err, DbErr) else None
        return MayhapsError(err.detail, status=status, kind=kind)

    async def _execute(self) -> None:
        """Run all collected steps in order, updating ``_state``."""
        state: Ok[Any] | Err = Ok(self._initial)
        for kind, payload in self._steps:
            if isinstance(state, Err):
                break
            if kind == "then":
                fn = payload
                raw = fn(state.value)
                if inspect.iscoroutine(raw):
                    raw = await raw
                state = raw  # Ok[...] | Err
            elif kind == "require":
                predicate, err = payload
                if not predicate(state.value):
                    state = err
            elif kind == "tap":
                fn = payload
                raw = fn(state.value)
                if inspect.iscoroutine(raw):
                    await raw
                # state unchanged
            elif kind == "map":
                fn = payload
                state = Ok(fn(state.value))
        self._state = state
        self._executed = True

    # ------------------------------------------------------------------
    # Fluent API (lazy — no execution yet)
    # ------------------------------------------------------------------

    def then[U](
        self,
        fn: Callable[[T], Awaitable[Ok[U] | Err] | Ok[U] | Err],
    ) -> "AsyncPipeline[U]":
        """Append a step that returns ``Ok[U] | Err`` (sync or async)."""
        self._steps.append(("then", fn))
        return cast("AsyncPipeline[U]", self)

    def require(self, predicate: Callable[[T], bool], err: Err) -> "AsyncPipeline[T]":
        """Append a guard: short-circuits with *err* if *predicate* returns False."""
        self._steps.append(("require", (predicate, err)))
        return self

    def tap(self, fn: Callable[[T], Awaitable[None] | None]) -> "AsyncPipeline[T]":
        """Append a side-effect step (sync or async); the value passes through unchanged."""
        self._steps.append(("tap", fn))
        return self

    def map[U](self, fn: Callable[[T], U]) -> "AsyncPipeline[U]":
        """Append a plain transform; the result is wrapped in Ok automatically."""
        self._steps.append(("map", fn))
        return cast("AsyncPipeline[U]", self)

    # ------------------------------------------------------------------
    # Terminal methods
    # ------------------------------------------------------------------

    def result(self) -> Ok[T] | Err:
        """Return the current ``Ok[T] | Err`` state.

        Raises ``RuntimeError`` if called before ``await run()``.
        """
        if not self._executed:
            raise RuntimeError(
                "AsyncPipeline.result() called before run(). "
                "Use `await pipeline.run()` to execute the pipeline first."
            )
        return self._state  # type: ignore[return-value]

    async def run(self) -> T:
        """Execute all steps and return the final value, or raise ``MayhapsError``."""
        await self._execute()
        if isinstance(self._state, Err):
            raise self._make_error(self._state)
        return self._state.value  # type: ignore[return-value]
