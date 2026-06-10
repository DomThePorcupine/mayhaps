"""
Integration tests for mayhaps.fastapi.HttpPipeline against a real FastAPI app.

Covers happy paths, each HttpErr status code, short-circuit behaviour, and
exception edge cases (unexpected raises, HTTPException raised directly inside
a step).
"""

from mayhaps.fastapi import HttpErr, HttpPipeline, Ok

from .server import USERS, User, app, client


# --- happy path --------------------------------------------------------------

def test_get_user_returns_200() -> None:
    response = client.get("/users/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Alice"}


def test_get_profile_returns_200() -> None:
    response = client.get("/users/1/profile")
    assert response.status_code == 200
    assert response.json() == {"bio": "Engineer"}


# --- HttpErr status codes ----------------------------------------------------

def test_user_not_found_returns_404() -> None:
    response = client.get("/users/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_wrong_org_returns_403() -> None:
    response = client.get("/users/3")
    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


def test_deactivated_user_returns_422() -> None:
    response = client.get("/users/2")
    assert response.status_code == 422
    assert response.json()["detail"] == "User is deactivated"


def test_missing_profile_returns_404() -> None:
    USERS[4] = User(id=4, name="Dave", org_id=10, is_active=True)
    try:
        response = client.get("/users/4/profile")
        assert response.status_code == 404
        assert response.json()["detail"] == "Profile not found"
    finally:
        del USERS[4]


# --- short-circuit behaviour -------------------------------------------------

def test_short_circuit_does_not_call_later_steps() -> None:
    called: list[str] = []

    @app.get("/short-circuit-test")
    def short_circuit_route() -> dict[str, str]:
        def step_a(x: int) -> Ok[int] | HttpErr:
            called.append("a")
            return HttpErr("stop here", status=404)

        def step_b(x: int) -> Ok[int] | HttpErr:
            called.append("b")
            return Ok(x)

        HttpPipeline(1).then(step_a).then(step_b).run()
        return {}

    client.get("/short-circuit-test")
    assert called == ["a"]


def test_error_in_last_step_still_raises() -> None:
    USERS[5] = User(id=5, name="Eve", org_id=10, is_active=True)
    try:
        response = client.get("/users/5/profile")
        assert response.status_code == 404
    finally:
        del USERS[5]


# --- exception edge cases ----------------------------------------------------

def test_unexpected_exception_in_step_returns_500() -> None:
    response = client.get("/users/1/explode")
    assert response.status_code == 500


def test_http_exception_raised_directly_in_step_is_respected() -> None:
    response = client.get("/users/1/http-exception")
    assert response.status_code == 503
    assert response.json()["detail"] == "upstream unavailable"


def test_http_err_with_arbitrary_status_code_is_forwarded() -> None:
    @app.get("/teapot")
    def teapot_route() -> dict[str, str]:
        def brew(x: int) -> Ok[int] | HttpErr:
            return HttpErr("I'm a teapot", status=418)

        HttpPipeline(1).then(brew).run()
        return {}

    response = client.get("/teapot")
    assert response.status_code == 418
    assert response.json()["detail"] == "I'm a teapot"
