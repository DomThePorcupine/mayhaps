import httpx2 as httpx
import pytest

from mayhaps import MayhapsError, Pipeline
from mayhaps.httpx import HttpxErr, check
from mayhaps.result import HttpErr, Ok


def test_check_returns_ok_for_2xx() -> None:
    response = httpx.Response(200, content=b"ok")
    assert check(response) == Ok(response)


def test_check_returns_ok_for_all_2xx_codes() -> None:
    for status in (200, 201, 204, 299):
        response = httpx.Response(status, content=b"")
        assert isinstance(check(response), Ok)


def test_check_returns_httpx_err_for_4xx() -> None:
    response = httpx.Response(404, content=b"not found")
    result = check(response)
    assert isinstance(result, HttpxErr)
    assert result.status == 404
    assert result.response is response


def test_check_returns_httpx_err_for_5xx() -> None:
    response = httpx.Response(500, content=b"internal error")
    result = check(response)
    assert isinstance(result, HttpxErr)
    assert result.status == 500


def test_httpx_err_detail_is_response_text() -> None:
    response = httpx.Response(400, content=b"bad request")
    result = check(response)
    assert isinstance(result, HttpxErr)
    assert result.detail == "bad request"


def test_httpx_err_is_http_err() -> None:
    response = httpx.Response(403, content=b"forbidden")
    result = check(response)
    assert isinstance(result, HttpErr)


def test_check_as_pipeline_step_passes_through_on_success() -> None:
    response = httpx.Response(200, content=b"ok")
    assert Pipeline(response).then(check).run() is response


def test_check_as_pipeline_step_short_circuits_on_error() -> None:
    response = httpx.Response(401, content=b"unauthorized")
    with pytest.raises(MayhapsError) as exc_info:
        Pipeline(response).then(check).run()
    assert exc_info.value.status == 401
    assert exc_info.value.detail == "unauthorized"
