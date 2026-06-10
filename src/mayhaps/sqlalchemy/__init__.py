from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mayhaps.result import DbErr, DbErrKind, Ok


def fetch_by_id[M](
    model: type[M],
    session: Session,
    *,
    detail: str | None = None,
) -> Callable[[int], Ok[M] | DbErr]:
    """Step factory: look up a row by primary key."""
    def step(pk: int) -> Ok[M] | DbErr:
        instance = session.get(model, pk)
        return Ok(instance) if instance is not None else DbErr(detail or f"{model.__name__} not found", kind=DbErrKind.NOT_FOUND)
    return step


def fetch_by[M](
    model: type[M],
    session: Session,
    column: Any,
    *,
    detail: str | None = None,
) -> Callable[[Any], Ok[M] | DbErr]:
    """Step factory: look up a row by an arbitrary column value."""
    def step(value: Any) -> Ok[M] | DbErr:
        instance = session.scalars(select(model).where(column == value)).first()
        return Ok(instance) if instance is not None else DbErr(detail or f"{model.__name__} not found", kind=DbErrKind.NOT_FOUND)
    return step


def require[M](
    predicate: Callable[[M], bool],
    *,
    kind: DbErrKind,
    detail: str,
) -> Callable[[M], Ok[M] | DbErr]:
    """Step factory: pass through if predicate holds, otherwise short-circuit."""
    def step(value: M) -> Ok[M] | DbErr:
        return Ok(value) if predicate(value) else DbErr(detail, kind=kind)
    return step


def require_absent(
    model: type,
    session: Session,
    column: Any,
    *,
    detail: str | None = None,
) -> Callable[[Any], Ok[Any] | DbErr]:
    """Step factory: pass through if no row matches column == value, otherwise short-circuit.

    Useful for uniqueness checks before creating a record.
    """
    def step(value: Any) -> Ok[Any] | DbErr:
        exists = session.scalars(select(model).where(column == value)).first()
        return DbErr(detail or "Already exists", kind=DbErrKind.CONFLICT) if exists is not None else Ok(value)
    return step


def save[M](
    session: Session,
    *,
    conflict_detail: str | None = None,
) -> Callable[[M], Ok[M] | DbErr]:
    """Step factory: add the object to the session and flush.

    Returns the same object on success. Converts IntegrityError to DbErr(CONFLICT).
    """
    def step(obj: M) -> Ok[M] | DbErr:
        try:
            session.add(obj)
            session.flush()
            return Ok(obj)
        except IntegrityError:
            session.rollback()
            return DbErr(conflict_detail or "Conflict", kind=DbErrKind.CONFLICT)
    return step
