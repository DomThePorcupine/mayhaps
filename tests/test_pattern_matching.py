"""Demonstrate structural pattern matching with mayhaps result types.

Pipeline.result() returns Ok[T] | Err (or a concrete Err subtype). Since all
result types are dataclasses, Python 3.10+ match/case works on them directly —
no adapter code needed.

Patterns shown here:
  - Basic Ok vs Err dispatch
  - Binding inner values inside the pattern
  - Narrowing to concrete subtypes (HttpErr, DbErr, ValidationErr)
  - Exhaustiveness guard with assert_never
  - Using match in place of isinstance chains
"""

from typing import assert_never

from mayhaps.pipeline import Pipeline
from mayhaps.result import DbErr, DbErrKind, Err, HttpErr, Ok, ValidationErr


# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------

def _ok(v: int) -> Ok[int] | Err:
    return Ok(v)

def _err(_: int) -> Ok[int] | Err:
    return Err("oops")

def _http_err(_: int) -> Ok[int] | Err:
    return HttpErr("not found", status=404)

def _db_not_found(_: int) -> Ok[int] | Err:
    return DbErr("row missing", kind=DbErrKind.NOT_FOUND)

def _db_conflict(_: int) -> Ok[int] | Err:
    return DbErr("already exists", kind=DbErrKind.CONFLICT)

def _validation_err(_: int) -> Ok[int] | Err:
    return ValidationErr("validation failed", fields=["name", "age"])


# ---------------------------------------------------------------------------
# Basic Ok / Err dispatch
# ---------------------------------------------------------------------------

def test_match_ok_extracts_value() -> None:
    result = Pipeline(21).map(lambda x: x * 2).result()

    match result:
        case Ok(value=v):
            assert v == 42
        case Err():
            raise AssertionError("expected Ok")


def test_match_err_extracts_detail() -> None:
    result = Pipeline(1).then(_err).result()

    match result:
        case Ok():
            raise AssertionError("expected Err")
        case Err(detail=msg):
            assert msg == "oops"


# ---------------------------------------------------------------------------
# Binding values inline
# ---------------------------------------------------------------------------

def test_match_binds_value_in_pattern() -> None:
    results = [Pipeline(i).then(_ok).result() for i in range(5)]
    extracted = []

    for r in results:
        match r:
            case Ok(value=v):
                extracted.append(v)
            case Err():
                pass

    assert extracted == list(range(5))


# ---------------------------------------------------------------------------
# Narrowing to concrete Err subtypes
# ---------------------------------------------------------------------------

def test_match_http_err_captures_status() -> None:
    result = Pipeline(1).then(_http_err).result()

    match result:
        case Ok():
            raise AssertionError
        case HttpErr(detail=msg, status=code):
            assert code == 404
            assert msg == "not found"
        case Err():
            raise AssertionError("expected HttpErr")


def test_match_db_err_captures_kind() -> None:
    result = Pipeline(1).then(_db_not_found).result()

    match result:
        case Ok():
            raise AssertionError
        case DbErr(kind=DbErrKind.NOT_FOUND):
            pass  # correct
        case DbErr(kind=DbErrKind.CONFLICT):
            raise AssertionError("wrong kind")
        case Err():
            raise AssertionError("expected DbErr")


def test_match_validation_err_captures_fields() -> None:
    result = Pipeline(1).then(_validation_err).result()

    match result:
        case Ok():
            raise AssertionError
        case ValidationErr(fields=fields):
            assert "name" in fields
            assert "age" in fields
        case Err():
            raise AssertionError("expected ValidationErr")


# ---------------------------------------------------------------------------
# Full dispatch table (all subtypes)
# ---------------------------------------------------------------------------

def _classify(result: Ok[int] | Err) -> str:
    match result:
        case Ok(value=v):
            return f"ok:{v}"
        case HttpErr(status=code):
            return f"http:{code}"
        case DbErr(kind=DbErrKind.NOT_FOUND):
            return "db:not_found"
        case DbErr(kind=DbErrKind.CONFLICT):
            return "db:conflict"
        case ValidationErr(fields=fields):
            return f"validation:{','.join(fields)}"
        case Err(detail=msg):
            return f"err:{msg}"
        case _ as unreachable:
            assert_never(unreachable)


def test_dispatch_ok() -> None:
    assert _classify(Ok(7)) == "ok:7"

def test_dispatch_http_err() -> None:
    assert _classify(HttpErr("x", status=403)) == "http:403"

def test_dispatch_db_not_found() -> None:
    assert _classify(DbErr("x", kind=DbErrKind.NOT_FOUND)) == "db:not_found"

def test_dispatch_db_conflict() -> None:
    assert _classify(DbErr("x", kind=DbErrKind.CONFLICT)) == "db:conflict"

def test_dispatch_validation_err() -> None:
    assert _classify(ValidationErr("x", fields=["a", "b"])) == "validation:a,b"

def test_dispatch_plain_err() -> None:
    assert _classify(Err("boom")) == "err:boom"


# ---------------------------------------------------------------------------
# match beats isinstance chains: same logic, cleaner syntax
# ---------------------------------------------------------------------------

def _http_status_isinstance(result: Ok[int] | Err) -> int:
    """The isinstance-chain version — verbose, easy to mis-order."""
    if isinstance(result, Ok):
        return 200
    if isinstance(result, HttpErr):
        return result.status
    if isinstance(result, DbErr):
        statuses = {
            DbErrKind.NOT_FOUND: 404,
            DbErrKind.CONFLICT: 409,
            DbErrKind.PERMISSION_DENIED: 403,
            DbErrKind.INVALID: 422,
        }
        return statuses.get(result.kind, 500)
    if isinstance(result, ValidationErr):
        return 422
    return 500


def _http_status_match(result: Ok[int] | Err) -> int:
    """The match version — order-independent for non-overlapping cases."""
    match result:
        case Ok():
            return 200
        case HttpErr(status=code):
            return code
        case DbErr(kind=DbErrKind.NOT_FOUND):
            return 404
        case DbErr(kind=DbErrKind.CONFLICT):
            return 409
        case DbErr(kind=DbErrKind.PERMISSION_DENIED):
            return 403
        case DbErr(kind=DbErrKind.INVALID) | ValidationErr():
            return 422
        case _:
            return 500


def test_isinstance_and_match_agree() -> None:
    cases: list[Ok[int] | Err] = [
        Ok(1),
        HttpErr("x", status=403),
        DbErr("x", kind=DbErrKind.NOT_FOUND),
        DbErr("x", kind=DbErrKind.CONFLICT),
        DbErr("x", kind=DbErrKind.PERMISSION_DENIED),
        DbErr("x", kind=DbErrKind.INVALID),
        ValidationErr("x", fields=["f"]),
        Err("plain"),
    ]
    for case in cases:
        assert _http_status_isinstance(case) == _http_status_match(case), repr(case)
