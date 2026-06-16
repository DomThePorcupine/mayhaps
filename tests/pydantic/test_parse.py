from pydantic import BaseModel

from mayhaps.pipeline import Pipeline
from mayhaps.pydantic import parse
from mayhaps.result import Err, Ok


class User(BaseModel):
    name: str
    age: int


# --- parse (direct step) -----------------------------------------------------

def test_parse_returns_ok_on_valid_data() -> None:
    step = parse(User)
    result = step({"name": "Alice", "age": 30})
    assert result == Ok(User(name="Alice", age=30))


def test_parse_returns_err_on_missing_field() -> None:
    step = parse(User)
    result = step({"name": "Alice"})
    assert isinstance(result, Err)
    assert "age" in result.detail


def test_parse_returns_err_on_wrong_type() -> None:
    step = parse(User)
    result = step({"name": "Alice", "age": "not-a-number"})
    assert isinstance(result, Err)
    assert "age" in result.detail


def test_parse_returns_err_on_empty_dict() -> None:
    step = parse(User)
    result = step({})
    assert isinstance(result, Err)


# --- integration with Pipeline.then() ----------------------------------------

def test_pipeline_parse_success() -> None:
    value = Pipeline({"name": "Alice", "age": 30}).then(parse(User)).run()
    assert value == User(name="Alice", age=30)


def test_pipeline_parse_failure_short_circuits() -> None:
    result = Pipeline({"name": "Alice"}).then(parse(User)).result()
    assert isinstance(result, Err)
    assert "age" in result.detail


def test_pipeline_short_circuits_before_parse() -> None:
    """If the pipeline already holds an Err, parse is never called."""
    called = False

    def never_called(data: dict) -> Ok[User] | Err:
        nonlocal called
        called = True
        return parse(User)(data)

    result = (
        Pipeline({"name": "Bob", "age": 25})
        .then(lambda d: Err("upstream failure"))
        .then(never_called)
        .result()
    )
    assert isinstance(result, Err)
    assert result.detail == "upstream failure"
    assert not called


def test_pipeline_chained_after_parse() -> None:
    """Successful parse can be followed by further pipeline steps."""
    result = (
        Pipeline({"name": "  Alice  ", "age": 42})
        .then(parse(User))
        .map(lambda u: u.name.strip())
        .result()
    )
    assert result == Ok("  Alice  ".strip())


# --- error message format ----------------------------------------------------

def test_err_detail_contains_all_missing_fields() -> None:
    class Full(BaseModel):
        x: int
        y: int
        z: int

    result = parse(Full)({})
    assert isinstance(result, Err)
    for field in ("x", "y", "z"):
        assert field in result.detail
