from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mayhaps.result import HttpErr, Ok


def fetch_by_id[M](
    model: type[M],
    session: Session,
    *,
    status: int = 404,
    detail: str | None = None,
) -> Callable[[int], Ok[M] | HttpErr]:
    """Step factory: look up a row by primary key."""
    def step(pk: int) -> Ok[M] | HttpErr:
        instance = session.get(model, pk)
        return Ok(instance) if instance is not None else HttpErr(detail or f"{model.__name__} not found", status=status)
    return step


def fetch_by[M](
    model: type[M],
    session: Session,
    column: Any,
    *,
    status: int = 404,
    detail: str | None = None,
) -> Callable[[Any], Ok[M] | HttpErr]:
    """Step factory: look up a row by an arbitrary column value."""
    def step(value: Any) -> Ok[M] | HttpErr:
        instance = session.scalars(select(model).where(column == value)).first()
        return Ok(instance) if instance is not None else HttpErr(detail or f"{model.__name__} not found", status=status)
    return step


def require[M](
    predicate: Callable[[M], bool],
    *,
    status: int,
    detail: str,
) -> Callable[[M], Ok[M] | HttpErr]:
    """Step factory: pass through if predicate holds, otherwise short-circuit."""
    def step(value: M) -> Ok[M] | HttpErr:
        return Ok(value) if predicate(value) else HttpErr(detail, status=status)
    return step


def require_absent(
    model: type,
    session: Session,
    column: Any,
    *,
    status: int = 409,
    detail: str | None = None,
) -> Callable[[Any], Ok[Any] | HttpErr]:
    """Step factory: pass through if no row matches column == value, otherwise short-circuit.

    Useful for uniqueness checks before creating a record.
    """
    def step(value: Any) -> Ok[Any] | HttpErr:
        exists = session.scalars(select(model).where(column == value)).first()
        return HttpErr(detail or "Already exists", status=status) if exists is not None else Ok(value)
    return step


def save[M](
    session: Session,
    *,
    conflict_detail: str | None = None,
) -> Callable[[M], Ok[M] | HttpErr]:
    """Step factory: add the object to the session and flush.

    Returns the same object on success. Converts IntegrityError to HttpErr(409).
    """
    def step(obj: M) -> Ok[M] | HttpErr:
        try:
            session.add(obj)
            session.flush()
            return Ok(obj)
        except IntegrityError:
            session.rollback()
            return HttpErr(conflict_detail or "Conflict", status=409)
    return step
