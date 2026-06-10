from fastapi import HTTPException

from mayhaps.pipeline import Pipeline
from mayhaps.result import Err, HttpErr, Ok

__all__ = ["HttpErr", "HttpPipeline", "Ok", "Err"]


class HttpPipeline[T](Pipeline[T]):
    def _make_error(self, err: Err) -> Exception:
        if isinstance(err, HttpErr):
            return HTTPException(status_code=err.status, detail=err.detail)
        return HTTPException(status_code=500, detail=err.detail)
