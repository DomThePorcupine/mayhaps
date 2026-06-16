from typing import Awaitable, Callable, TypeVar, cast, overload, override

from fastapi import HTTPException

from mayhaps.async_pipeline import AsyncPipeline
from mayhaps.result import DbErr, DbErrKind, Err, HttpErr, Ok

_V = TypeVar("_V")

_DB_STATUS_MAP: dict[DbErrKind, int] = {
    DbErrKind.NOT_FOUND: 404,
    DbErrKind.CONFLICT: 409,
    DbErrKind.PERMISSION_DENIED: 403,
    DbErrKind.INVALID: 422,
}


class AsyncHttpPipeline[T](AsyncPipeline[T]):
    """Async pipeline for FastAPI endpoints that raises ``HTTPException`` on failure.

    Identical to ``AsyncPipeline`` in usage, but any failing step raises
    ``HTTPException`` instead of ``MayhapsError`` when ``await run()`` is called.

    Error mapping:
      - ``HttpErr(detail, status=N)``    → ``HTTPException(status_code=N)``
      - ``DbErr(kind=NOT_FOUND)``        → 404
      - ``DbErr(kind=CONFLICT)``         → 409
      - ``DbErr(kind=PERMISSION_DENIED)``→ 403
      - ``DbErr(kind=INVALID)``          → 422
      - plain ``Err``                    → 500

    ``require(predicate, err)`` accepts a plain string as *err* (→ 400) or an
    ``HttpErr`` for any other status.

    Example::

        result = await (
            AsyncHttpPipeline(user_id)
            .then(fetch_user)                                    # async, returns Ok[User] | DbErr
            .require(lambda u: u.is_active, "User is inactive") # 400 on failure
            .tap(send_notification)                              # async side-effect
            .map(lambda u: u.name)
        ).run()
    """

    def _make_error(self, err: Err) -> Exception:
        if isinstance(err, HttpErr):
            return HTTPException(status_code=err.status, detail=err.detail)
        if isinstance(err, DbErr):
            return HTTPException(status_code=_DB_STATUS_MAP.get(err.kind, 500), detail=err.detail)
        return HTTPException(status_code=500, detail=err.detail)

    @override
    def then[U](
        self,
        fn: Callable[[T], Awaitable[Ok[U] | Err] | Ok[U] | Err],
    ) -> "AsyncHttpPipeline[U]":
        """Append a step that returns ``Ok[U] | Err`` (sync or async)."""
        return cast("AsyncHttpPipeline[U]", super().then(fn))

    @override
    def tap(self, fn: Callable[[T], Awaitable[None] | None]) -> "AsyncHttpPipeline[T]":
        """Append a side-effect step (sync or async); the value passes through unchanged."""
        return cast("AsyncHttpPipeline[T]", super().tap(fn))

    @override
    def map[U](self, fn: Callable[[T], U]) -> "AsyncHttpPipeline[U]":
        """Append a plain transform; the result is wrapped in Ok automatically."""
        return cast("AsyncHttpPipeline[U]", super().map(fn))

    @overload  # type: ignore[override]
    def ok_or(self: "AsyncHttpPipeline[_V | None]", err: Err) -> "AsyncHttpPipeline[_V]": ...
    @overload
    def ok_or(self: "AsyncHttpPipeline[_V]", err: Err) -> "AsyncHttpPipeline[_V]": ...
    def ok_or(self, err: Err) -> "AsyncHttpPipeline":
        """Unwrap T | None → T, short-circuiting with err if the value is None."""
        return cast("AsyncHttpPipeline", super().ok_or(err))

    def require(  # type: ignore[override]  # intentional: narrows err to HttpPipeline domain
        self, predicate: Callable[[T], bool], err: str | HttpErr
    ) -> "AsyncHttpPipeline[T]":
        """Guard the current value. Raises 400 for a plain string, or the given HttpErr status."""
        resolved = HttpErr(err, status=400) if isinstance(err, str) else err
        return cast("AsyncHttpPipeline[T]", super().require(predicate, resolved))
