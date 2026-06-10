from dataclasses import dataclass, field


@dataclass
class Ok[T]:
    value: T


@dataclass
class Err:
    detail: str


@dataclass
class HttpErr(Err):
    status: int = field(kw_only=True)


class MayhapsError(Exception):
    def __init__(self, detail: str, *, status: int | None = None) -> None:
        self.detail = detail
        self.status = status
        super().__init__(detail)
