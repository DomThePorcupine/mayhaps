from typing import Callable, cast

from fastapi import HTTPException

from mayhaps.pipeline import Pipeline
from mayhaps.result import DbErr, DbErrKind, Err, HttpErr, Ok

__all__ = ["DbErr", "DbErrKind", "HttpErr", "HttpPipeline", "Ok", "Err"]

_DB_STATUS_MAP: dict[DbErrKind, int] = {
    DbErrKind.NOT_FOUND: 404,
    DbErrKind.CONFLICT: 409,
    DbErrKind.PERMISSION_DENIED: 403,
    DbErrKind.INVALID: 422,
}


class HttpPipeline[T](Pipeline[T]):
    def _make_error(self, err: Err) -> Exception:
        if isinstance(err, HttpErr):
            return HTTPException(status_code=err.status, detail=err.detail)
        if isinstance(err, DbErr):
            return HTTPException(status_code=_DB_STATUS_MAP.get(err.kind, 500), detail=err.detail)
        return HTTPException(status_code=500, detail=err.detail)

    def require(  # type: ignore[override]  # intentional: HttpPipeline narrows err to its own domain
        self, predicate: Callable[[T], bool], err: str | HttpErr
    ) -> "HttpPipeline[T]":
        resolved = HttpErr(err, status=400) if isinstance(err, str) else err
        return cast("HttpPipeline[T]", super().require(predicate, resolved))
