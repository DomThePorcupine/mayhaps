from dataclasses import dataclass, field
from enum import Enum


@dataclass
class Ok[T]:
    value: T


@dataclass
class Err:
    detail: str


@dataclass
class HttpErr(Err):
    status: int = field(kw_only=True)


class DbErrKind(str, Enum):
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    PERMISSION_DENIED = "permission_denied"
    INVALID = "invalid"


@dataclass
class DbErr(Err):
    kind: DbErrKind = field(kw_only=True)


class MayhapsError(Exception):
    def __init__(self, detail: str, *, status: int | None = None, kind: DbErrKind | None = None) -> None:
        self.detail = detail
        self.status = status
        self.kind = kind
        super().__init__(detail)
