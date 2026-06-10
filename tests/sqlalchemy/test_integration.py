"""
Integration tests for mayhaps.sqlalchemy helpers wired into Pipeline and HttpPipeline.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from mayhaps import MayhapsError, Pipeline
from mayhaps.fastapi import HttpPipeline
from mayhaps.result import DbErrKind
from mayhaps.sqlalchemy import fetch_by, fetch_by_id, require, require_absent, save

from .db import User, alice, bob, session  # noqa: F401


# --- core Pipeline + MayhapsError --------------------------------------------

def test_full_pipeline_returns_value(session: Session, alice: User) -> None:
    result = (
        Pipeline(alice.id)
        .then(fetch_by_id(User, session))
        .then(require(lambda u: u.is_active, kind=DbErrKind.INVALID, detail="Inactive"))
        .run()
    )
    assert result is alice


def test_full_pipeline_raises_mayhaps_error_on_not_found(session: Session) -> None:
    with pytest.raises(MayhapsError) as exc_info:
        Pipeline(999).then(fetch_by_id(User, session)).run()

    assert exc_info.value.detail == "User not found"
    assert exc_info.value.kind == DbErrKind.NOT_FOUND


def test_full_pipeline_raises_mayhaps_error_on_failed_guard(session: Session, bob: User) -> None:
    with pytest.raises(MayhapsError) as exc_info:
        (
            Pipeline(bob.id)
            .then(fetch_by_id(User, session))
            .then(require(lambda u: u.is_active, kind=DbErrKind.INVALID, detail="User is deactivated"))
            .run()
        )

    assert exc_info.value.detail == "User is deactivated"
    assert exc_info.value.kind == DbErrKind.INVALID


# --- HttpPipeline auto-converts DbErr → HTTPException ------------------------

def test_http_pipeline_returns_value(session: Session, alice: User) -> None:
    result = (
        HttpPipeline(alice.id)
        .then(fetch_by_id(User, session))
        .then(require(lambda u: u.is_active, kind=DbErrKind.INVALID, detail="Inactive"))
        .run()
    )
    assert result is alice


def test_http_pipeline_maps_not_found_to_404(session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        HttpPipeline(999).then(fetch_by_id(User, session)).run()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


def test_http_pipeline_maps_invalid_to_422(session: Session, bob: User) -> None:
    with pytest.raises(HTTPException) as exc_info:
        (
            HttpPipeline(bob.id)
            .then(fetch_by_id(User, session))
            .then(require(lambda u: u.is_active, kind=DbErrKind.INVALID, detail="User is deactivated"))
            .run()
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "User is deactivated"


def test_http_pipeline_maps_permission_denied_to_403(session: Session, alice: User) -> None:
    with pytest.raises(HTTPException) as exc_info:
        (
            HttpPipeline(alice.id)
            .then(fetch_by_id(User, session))
            .then(require(lambda u: u.name == "Bob", kind=DbErrKind.PERMISSION_DENIED, detail="Forbidden"))
            .run()
        )

    assert exc_info.value.status_code == 403


# --- create flow (require_absent + save) -------------------------------------

def test_create_flow_succeeds(session: Session) -> None:
    from mayhaps import Ok

    def make_user(email: str) -> Ok[User]:
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


def test_create_flow_maps_conflict_to_409(session: Session, alice: User) -> None:
    from mayhaps import Ok

    def make_user(email: str) -> Ok[User]:
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
    result = HttpPipeline(alice.email).then(fetch_by(User, session, User.email)).run()
    assert result is alice


def test_fetch_by_maps_not_found_to_404(session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        HttpPipeline("nobody@example.com").then(fetch_by(User, session, User.email)).run()

    assert exc_info.value.status_code == 404
