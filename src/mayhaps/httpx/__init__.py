import httpx2 as httpx

from mayhaps.result import HttpErr, Ok

__all__ = ["HttpxErr", "check"]


class HttpxErr(HttpErr):
    """Pipeline error wrapping a non-2xx httpx response.

    Extends HttpErr so HttpPipeline maps the status code correctly.
    The original response is available as .response for body inspection.
    """

    def __init__(self, response: httpx.Response) -> None:
        super().__init__(detail=response.text, status=response.status_code)
        self.response = response


def check(response: httpx.Response) -> Ok[httpx.Response] | HttpxErr:
    """Return Ok if the response is 2xx, otherwise HttpxErr."""
    return Ok(response) if response.is_success else HttpxErr(response)
