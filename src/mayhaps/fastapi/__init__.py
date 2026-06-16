from typing import Callable, cast, override

from fastapi import HTTPException

from mayhaps.fastapi.async_pipeline import AsyncHttpPipeline
from mayhaps.pipeline import Pipeline
from mayhaps.result import DbErr, DbErrKind, Err, HttpErr, Ok, ValidationErr

__all__ = ["AsyncHttpPipeline", "DbErr", "DbErrKind", "HttpErr", "HttpPipeline", "Ok", "Err", "ValidationErr"]

_DB_STATUS_MAP: dict[DbErrKind, int] = {
    DbErrKind.NOT_FOUND: 404,
    DbErrKind.CONFLICT: 409,
    DbErrKind.PERMISSION_DENIED: 403,
    DbErrKind.INVALID: 422,
}


class HttpPipeline[T](Pipeline[T]):
    """Pipeline for FastAPI endpoints that raises HTTPException on failure.

    Build a chain of steps with .then(), .require(), .tap(), and .map(), then
    call .run() to execute. Any failing step short-circuits the rest and raises
    HTTPException directly — no try/except needed in the endpoint.

    Error mapping:
      - HttpErr(detail, status=N)  → HTTPException(status_code=N)
      - DbErr(kind=NOT_FOUND)      → 404
      - DbErr(kind=CONFLICT)       → 409
      - DbErr(kind=PERMISSION_DENIED) → 403
      - DbErr(kind=INVALID)        → 422
      - plain Err                  → 500

    .require(predicate, err) guards the current value. If the predicate returns
    False, the pipeline short-circuits and .run() raises HTTPException. Pass a
    plain string as err to get a 400; pass HttpErr(..., status=N) for any other
    status code.

    Example:
        (
            HttpPipeline(user_id)
            .then(Users.get_by_id(db))           # 404 if missing
            .require(lambda u: u.is_active, "User is deactivated")  # 400
            .tap(lambda u: u.activate())
            .then(flush(db))
        ).run()
    """

    def _make_error(self, err: Err) -> Exception:
        if isinstance(err, HttpErr):
            return HTTPException(status_code=err.status, detail=err.detail)
        if isinstance(err, DbErr):
            return HTTPException(status_code=_DB_STATUS_MAP.get(err.kind, 500), detail=err.detail)
        if isinstance(err, ValidationErr):
            return HTTPException(status_code=422, detail=err.detail)
        return HTTPException(status_code=500, detail=err.detail)

    @override
    def then[U](self, fn: Callable[[T], Ok[U] | Err]) -> "HttpPipeline[U]":
        """Apply fn to the current value, advancing the pipeline or short-circuiting on Err."""
        return cast("HttpPipeline[U]", super().then(fn))

    @override
    def tap(self, fn: Callable[[T], None]) -> "HttpPipeline[T]":
        """Call fn for side effects (e.g. mutation) without changing the pipeline value."""
        return cast("HttpPipeline[T]", super().tap(fn))

    @override
    def map[U](self, fn: Callable[[T], U]) -> "HttpPipeline[U]":
        """Transform the current value with a plain function that cannot fail."""
        return cast("HttpPipeline[U]", super().map(fn))

    def require(  # type: ignore[override]  # intentional: HttpPipeline narrows err to its own domain
        self, predicate: Callable[[T], bool], err: str | HttpErr
    ) -> "HttpPipeline[T]":
        """Guard the current value. Raises 400 for a plain string, or the given HttpErr status."""
        resolved = HttpErr(err, status=400) if isinstance(err, str) else err
        return cast("HttpPipeline[T]", super().require(predicate, resolved))
