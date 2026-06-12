from sqlalchemy.orm import Session

from mayhaps.result import DbErr, DbErrKind, Ok
from mayhaps.sqlalchemy import fetch_by, fetch_by_id, flush, require, require_absent, save

from .db import User, alice, bob, session  # noqa: F401


# --- fetch_by_id -------------------------------------------------------------

def test_fetch_by_id_returns_ok_when_found(session: Session, alice: User) -> None:
    result = fetch_by_id(User, session)(alice.id)
    assert result == Ok(alice)


def test_fetch_by_id_returns_not_found_err_when_missing(session: Session) -> None:
    result = fetch_by_id(User, session)(999)
    assert result == DbErr("User not found", kind=DbErrKind.NOT_FOUND)


def test_fetch_by_id_custom_detail(session: Session) -> None:
    result = fetch_by_id(User, session, detail="No such user")(999)
    assert result == DbErr("No such user", kind=DbErrKind.NOT_FOUND)


# --- fetch_by ----------------------------------------------------------------

def test_fetch_by_returns_ok_when_found(session: Session, alice: User) -> None:
    result = fetch_by(User, session, User.email)(alice.email)
    assert result == Ok(alice)


def test_fetch_by_returns_not_found_err_when_missing(session: Session) -> None:
    result = fetch_by(User, session, User.email)("nobody@example.com")
    assert result == DbErr("User not found", kind=DbErrKind.NOT_FOUND)


def test_fetch_by_custom_detail(session: Session) -> None:
    result = fetch_by(User, session, User.email, detail="Email not registered")("x@x.com")
    assert result == DbErr("Email not registered", kind=DbErrKind.NOT_FOUND)


# --- require -----------------------------------------------------------------

def test_require_passes_through_when_predicate_holds(session: Session, alice: User) -> None:
    def is_active(u: User) -> bool:
        return u.is_active
    step = require(is_active, kind=DbErrKind.INVALID, detail="Inactive")
    assert step(alice) == Ok(alice)


def test_require_returns_err_when_predicate_fails(session: Session, bob: User) -> None:
    def is_active(u: User) -> bool:
        return u.is_active
    step = require(is_active, kind=DbErrKind.INVALID, detail="User is deactivated")
    assert step(bob) == DbErr("User is deactivated", kind=DbErrKind.INVALID)


def test_require_uses_provided_kind(session: Session, alice: User) -> None:
    def is_carol(u: User) -> bool:
        return u.name == "Carol"
    step = require(is_carol, kind=DbErrKind.PERMISSION_DENIED, detail="Wrong user")
    result = step(alice)
    assert result == DbErr("Wrong user", kind=DbErrKind.PERMISSION_DENIED)


# --- require_absent ----------------------------------------------------------

def test_require_absent_passes_through_when_not_found(session: Session) -> None:
    result = require_absent(User, session, User.email)("new@example.com")
    assert result == Ok("new@example.com")


def test_require_absent_returns_conflict_err_when_exists(session: Session, alice: User) -> None:
    result = require_absent(User, session, User.email)(alice.email)
    assert result == DbErr("Already exists", kind=DbErrKind.CONFLICT)


def test_require_absent_custom_detail(session: Session, alice: User) -> None:
    result = require_absent(User, session, User.email, detail="Email taken")(alice.email)
    assert result == DbErr("Email taken", kind=DbErrKind.CONFLICT)


# --- flush -------------------------------------------------------------------

def test_flush_passes_through_object(session: Session, alice: User) -> None:
    result = flush(session)(alice)
    assert result == Ok(alice)


def test_flush_persists_mutations(session: Session, alice: User) -> None:
    alice.name = "Updated"
    flush(session)(alice)
    session.expire(alice)
    assert alice.name == "Updated"


# --- save --------------------------------------------------------------------

def test_save_adds_and_returns_object(session: Session) -> None:
    user = User(name="Carol", email="carol@example.com", is_active=True)
    result = save(session)(user)
    assert result == Ok(user)
    assert session.get(User, user.id) is user


def test_save_returns_conflict_err_on_integrity_error(session: Session, alice: User) -> None:
    duplicate = User(name="Dup", email=alice.email, is_active=True)
    result = save(session)(duplicate)
    assert result == DbErr("Conflict", kind=DbErrKind.CONFLICT)


def test_save_custom_conflict_detail(session: Session, alice: User) -> None:
    duplicate = User(name="Dup", email=alice.email, is_active=True)
    result = save(session, conflict_detail="Email already registered")(duplicate)
    assert result == DbErr("Email already registered", kind=DbErrKind.CONFLICT)
