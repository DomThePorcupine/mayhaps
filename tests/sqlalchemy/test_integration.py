"""
Integration tests for mayhaps.sqlalchemy helpers wired into Pipeline and HttpPipeline.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from mayhaps import MayhapsError, Pipeline
from mayhaps.fastapi import HttpPipeline
from mayhaps.sqlalchemy import fetch_by, fetch_by_id, require, require_absent, save

from .db import Post, User, alice, bob, session  # noqa: F401


# --- core Pipeline + MayhapsError --------------------------------------------

def test_full_pipeline_returns_value(session: Session, alice: User) -> None:
    result = (
        Pipeline(alice.id)
        .then(fetch_by_id(User, session))
        .then(require(lambda u: u.is_active, status=422, detail="Inactive"))
        .run()
    )
    assert result is alice


def test_full_pipeline_raises_mayhaps_error_on_not_found(session: Session) -> None:
    with pytest.raises(MayhapsError) as exc_info:
        Pipeline(999).then(fetch_by_id(User, session)).run()

    assert exc_info.value.detail == "User not found"
    assert exc_info.value.status == 404


def test_full_pipeline_raises_mayhaps_error_on_failed_guard(session: Session, bob: User) -> None:
    with pytest.raises(MayhapsError) as exc_info:
        (
            Pipeline(bob.id)
            .then(fetch_by_id(User, session))
            .then(require(lambda u: u.is_active, status=422, detail="User is deactivated"))
            .run()
        )

    assert exc_info.value.detail == "User is deactivated"
    assert exc_info.value.status == 422


# --- HttpPipeline + HTTPException --------------------------------------------

def test_http_pipeline_returns_value(session: Session, alice: User) -> None:
    result = (
        HttpPipeline(alice.id)
        .then(fetch_by_id(User, session))
        .then(require(lambda u: u.is_active, status=422, detail="Inactive"))
        .run()
    )
    assert result is alice


def test_http_pipeline_raises_http_exception_on_not_found(session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        HttpPipeline(999).then(fetch_by_id(User, session)).run()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


def test_http_pipeline_raises_http_exception_on_failed_guard(session: Session, bob: User) -> None:
    with pytest.raises(HTTPException) as exc_info:
        (
            HttpPipeline(bob.id)
            .then(fetch_by_id(User, session))
            .then(require(lambda u: u.is_active, status=422, detail="User is deactivated"))
            .run()
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "User is deactivated"


# --- create flow (require_absent + save) -------------------------------------

def test_create_flow_succeeds(session: Session) -> None:
    def make_user(email: str) -> "Ok[User]":
        from mayhaps import Ok
        return Ok(User(name="Carol", email=email, is_active=True))

    user = (
        HttpPipeline("carol@example.com")
        .then(require_absent(User, session, User.email, detail="Email taken"))
        .then(make_user)
        .then(save(session))
        .run()
    )
    assert user.email == "carol@example.com"
    assert user.id is not None


def test_create_flow_fails_on_duplicate(session: Session, alice: User) -> None:
    def make_user(email: str) -> "Ok[User]":
        from mayhaps import Ok
        return Ok(User(name="Dup", email=email, is_active=True))

    with pytest.raises(HTTPException) as exc_info:
        (
            HttpPipeline(alice.email)
            .then(require_absent(User, session, User.email, detail="Email taken"))
            .then(make_user)
            .then(save(session))
            .run()
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Email taken"


# --- fetch_by ----------------------------------------------------------------

def test_fetch_by_in_pipeline(session: Session, alice: User) -> None:
    result = (
        HttpPipeline(alice.email)
        .then(fetch_by(User, session, User.email))
        .run()
    )
    assert result is alice


def test_fetch_by_raises_on_missing(session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        HttpPipeline("nobody@example.com").then(fetch_by(User, session, User.email)).run()

    assert exc_info.value.status_code == 404
